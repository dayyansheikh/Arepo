# ruff: noqa: E501
"""CB3 ``quote_state/`` extractor (docs/research_lab/CREATIVE_BATCH_3.md §4.3.1; challenger items 10, 12).

Data-only: copies quote fields exactly as stored, computes no statistic. Read-only on snapshots and
sweeps; writes only under its own root ``data-dumps/research_lab/cb3_extract/`` (own manifest, own lock).
Membership of capture c = binary markets E001-tight at c or at any of the 4 previous complete captures
(``bounce_decomp.h_tight_mask``), plus ``<capture_id>.ids.csv.gz`` listing every binary market of c.

Reuses (imports, does not copy) the helpers of ``creative_batch1`` (some are private by name; imported
anyway and that file is not edited) and ``forecast.list_complete_captures``.
"""

from __future__ import annotations

import gzip
import io
import json
import shutil
import subprocess
import tempfile
import time
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import forecast
from .bounce_decomp import h_tight_mask
from .creative_batch1 import (  # noqa: PLC2701 - private helpers reused on purpose (do not edit that file)
    ExtractLocked,
    _atomic_write_json,
    _dir_gb,
    _lock,
    _ts,
    sha256_stream,
    sweep_index,
    utc_now,
    write_csv_gz,
)

EXTRACTOR_VERSION = "cb3-quote-state-v2"
SCHEMA_VERSION = 2  # v2: as-of columns (asof_end_date, asof_created_at, asof_fee_*) + fees_enabled; v1 had end_date/created_at/fee_*
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "book_sweeps"
DATA_DUMPS = forecast.ROOT / "data-dumps"
CB3_ROOT = DATA_DUMPS / "research_lab" / "cb3_extract"
T3_A_DEV_END = "2026-10-15T21:00:00Z"  # backfill upper bound; T_J4R starts after it and is never read by q0060
N_PREV = 4
DEFAULT_BUDGET_S = 420.0
MODES = ("backfill", "all-new")

ROW_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "binary",
    "best_bid", "best_ask", "spread", "last_trade_price", "volume_num", "volume24hr", "chg_1d", "closed",
    "active", "asof_end_date", "tight", "tight_mask_prev4",
    "accepting_orders", "fees_enabled", "asof_created_at", "asof_fee_type", "asof_fee_category",
    "asof_fee_schedule", "neg_risk_id", "parent_event_ids", "series_slugs",
]  # asof_* = the value stored at that capture (never a later one); blank = unavailable (freeze-check fixes 5, 6)
SWEEP_FIELDS = ["batch_receipt_utc", "state", "best_bid", "best_ask", "bid_size_1", "ask_size_1",
                "depth_bid_1c", "depth_ask_1c"]
SWEEP_COLUMNS = [f"s{k}_{f}" for k in (1, 2) for f in SWEEP_FIELDS]
ALL_COLUMNS = [*ROW_COLUMNS, *SWEEP_COLUMNS]
DATA_DUMPS_HARD_CAP_GB = 12.0  # host data-dumps ceiling that output + scratch must fit under (fix 1)
PER_CAPTURE_GB = 0.005  # projection: about 3-4 MB rows + 0.5 MB ids per capture, rounded up
CATALOGUE_DIR = forecast.ROOT / "docs" / "research_lab" / "data_catalogue"
_ROWS_WANT = ["received_utc", "market_id", "condition_id", "event_id", "binary", "best_bid", "best_ask",
              "spread", "last_trade_price", "volume24hr", "chg_1d", "closed", "active", "end_date"]  # end_date -> asof_end_date
# sidecar source column(s) per output column (first present wins)
_EXT_MAP = {"volume_num": ["volume_num"], "accepting_orders": ["accepting_orders"],
            "fees_enabled": ["fees_enabled"], "asof_created_at": ["created_at"],
            "asof_fee_type": ["fee_type"], "asof_fee_category": ["fee_category"],
            "asof_fee_schedule": ["fee_schedule"], "neg_risk_id": ["neg_risk_id", "neg_risk_market_id"],
            "parent_event_ids": ["parent_event_ids"], "series_slugs": ["series_slugs"]}


class VersionMismatch(RuntimeError):
    """The cb3_extract manifest was written by another extractor version (a new version needs a new root)."""


class WindowError(ValueError):
    """The requested backfill window would read captures at/after T3_A_dev_end (T_J4R)."""


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=forecast.ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _read_str(path: Path, want: list[str]) -> pd.DataFrame:
    """Read ``want`` columns as raw strings (blank kept blank, float formatting kept); absent -> blank."""
    head = list(pd.read_csv(path, nrows=0).columns)
    df = pd.read_csv(path, usecols=[c for c in want if c in head], dtype=str, keep_default_na=False)
    for c in want:
        if c not in df.columns:
            df[c] = ""
    return df


def _num(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s.replace("", np.nan), errors="coerce").to_numpy(float)


def _binary_rows(path: Path) -> pd.DataFrame:
    """Binary markets of a capture's rows.csv.gz, first receipt per market_id (the collector's dedup)."""
    df = _read_str(forecast.require_local(path), _ROWS_WANT)
    df = df[_num(df["binary"]) == 1].drop_duplicates("market_id")
    df = df.rename(columns={"end_date": "asof_end_date"})
    return df.reset_index(drop=True)


def tight_flags(df: pd.DataFrame) -> np.ndarray:
    return np.asarray(h_tight_mask(_num(df["best_bid"]), _num(df["best_ask"]), _num(df["spread"])), dtype=bool)


def _tight_ids(cap: dict, cache: OrderedDict) -> frozenset[str] | None:
    """E001-tight binary ids of ``cap`` (None if its rows file is gone from the host). Cached."""
    cid = cap["capture_id"]
    if cid in cache:
        cache.move_to_end(cid)
        return cache[cid]
    try:
        df = _binary_rows(Path(cap["dir"]) / "rows.csv.gz")
        val: frozenset[str] | None = frozenset(df.loc[tight_flags(df), "market_id"])
    except forecast.ArchivedDataError:
        val = None
    cache[cid] = val
    while len(cache) > N_PREV + 3:
        cache.popitem(last=False)
    return val


def build_capture(cap: dict, prev: list[dict], sweeps: dict[int, Path] | None, tight_cache: OrderedDict
                  ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Rows, ids and manifest facts for one capture. ``prev`` = up to 4 preceding complete captures
    (oldest first). Raises ``ArchivedDataError`` when the capture's own rows file is gone."""
    cid, start = cap["capture_id"], cap["started_utc"]
    cdir = Path(cap["dir"])
    df = _binary_rows(cdir / "rows.csv.gz")
    tight = tight_flags(df)
    prev_sets = [_tight_ids(p, tight_cache) for p in prev]
    n_missing_prev = sum(s is None for s in prev_sets) + (N_PREV - len(prev))
    ids = df["market_id"]
    # 4-bit string, oldest first; '?' where the predecessor is not available (fewer than 4, or rows gone)
    in_prev = np.zeros(len(df), dtype=bool)
    mask = pd.Series("?" * (N_PREV - len(prev)), index=df.index)
    for s in prev_sets:
        if s is None:
            mask = mask + "?"
        else:
            m = ids.isin(s)
            in_prev |= m.to_numpy()
            mask = mask + m.map({True: "1", False: "0"})
    keep = tight | in_prev
    out = df[keep].copy()
    out["capture_id"], out["capture_start_utc"] = cid, start
    out["tight"] = pd.Series(tight, index=df.index)[keep].astype(int).astype(str)
    out["tight_mask_prev4"] = mask[keep]
    out.index = pd.Index(out["market_id"].to_numpy())

    ext_p = cdir / "rows_ext.csv.gz"
    ext_found = ext_p.exists()
    for col in _EXT_MAP:
        out[col] = ""
    if ext_found:
        head = list(pd.read_csv(ext_p, nrows=0).columns)
        want = sorted({"market_id", *(c for srcs in _EXT_MAP.values() for c in srcs)})
        ext = _read_str(ext_p, want).drop_duplicates("market_id").set_index("market_id")
        ext = ext[ext.index.isin(out.index)]
        for col, srcs in _EXT_MAP.items():
            src = next((s for s in srcs if s in head), None)
            if src is not None and len(ext):
                out.loc[ext.index, col] = ext[src]
    src_hash: dict[str, str] = {"rows": sha256_stream(cdir / "rows.csv.gz")}
    if ext_found:
        src_hash["rows_ext"] = sha256_stream(ext_p)

    n_found = 0
    for k in (0, 1):
        for f in SWEEP_FIELDS:
            out[f"s{k + 1}_{f}"] = ""
        d = (sweeps or {}).get(k)
        if d is None:
            continue
        p = Path(d) / "rows.csv.gz"
        try:
            forecast.require_local(p)
        except forecast.ArchivedDataError:
            continue  # sweep rows archived: sweep columns blank, counted via n_sweeps_found
        sw = _read_str(p, ["market_id", *SWEEP_FIELDS]).drop_duplicates("market_id").set_index("market_id")
        sw = sw[sw.index.isin(out.index)]
        for f in SWEEP_FIELDS:
            out.loc[sw.index, f"s{k + 1}_{f}"] = sw[f]
        src_hash[f"sweep_{k + 1}"] = sha256_stream(p)
        n_found += 1

    rows = out.sort_values("market_id").reset_index(drop=True)[ALL_COLUMNS]
    ids_df = pd.DataFrame({"market_id": sorted(ids)})
    facts = {"n_rows": int(len(rows)), "n_ids": int(len(ids_df)), "n_tight": int(tight.sum()),
             "n_sweeps_found": n_found, "membership_complete": bool(n_missing_prev == 0),
             "source_sha256": src_hash}
    return rows, ids_df, facts


def _load_manifest(root: Path) -> dict:
    p = Path(root) / "manifest.json"
    if p.exists():
        man = json.loads(p.read_text())
        if man.get("extractor_version") != EXTRACTOR_VERSION:
            raise VersionMismatch(f"{p}: {man.get('extractor_version')!r} != {EXTRACTOR_VERSION!r}; use a new root")
        return man
    return {"extractor_version": EXTRACTOR_VERSION, "captures": {}}


def catalogue_snapshot_captures(catalogue_dir: Path = CATALOGUE_DIR) -> dict[str, str]:
    """``capture_id -> capture_time_utc`` of every snapshot capture listed in the data catalogue (releases)."""
    out: dict[str, str] = {}
    for f in sorted(Path(catalogue_dir).glob("*.jsonl")):
        with open(f) as fh:
            for line in fh:
                if '"snapshots"' not in line:
                    continue
                r = json.loads(line)
                if r.get("dir") == "snapshots" and r.get("capture_id") and r.get("capture_time_utc"):
                    out[r["capture_id"]] = r["capture_time_utc"]
    return out


def universe(snapshot_root: Path, catalogue: dict[str, str]) -> list[dict]:
    """All complete captures in start order: host complete manifests plus release-only captures (catalogued but
    no manifest on this host). A release-only capture is a placeholder (``release_only``, no files) so that the
    4-predecessor window of its neighbours keeps its position ('?' in ``tight_mask_prev4``)."""
    caps = forecast.list_complete_captures(snapshot_root)
    have = {c["capture_id"] for c in caps}
    for p in Path(snapshot_root).glob("*/manifest.json"):  # host manifests that are not complete: not complete captures
        have.add(p.parent.name)
    for cid, t in catalogue.items():
        if cid not in have:
            caps.append({"capture_id": cid, "started_utc": t, "state": "complete", "dir": str(Path(snapshot_root) / cid),
                         "_start": _ts(t), "release_only": True})
    return sorted(caps, key=lambda c: c["_start"])


def completeness(caps: list[dict], man: dict, before: str) -> dict:
    """Every complete capture before ``before`` must be extracted or missing-with-reason in the manifest."""
    hi = _ts(before)
    ents = man["captures"]
    n_ext = n_miss = 0
    reasons: dict[str, int] = {}
    unaccounted: list[str] = []
    for c in caps:
        if c["_start"] >= hi:
            continue
        e = ents.get(c["capture_id"])
        if e is None:
            unaccounted.append(c["capture_id"])
        elif e.get("status") == "extracted":
            n_ext += 1
        elif e.get("status") == "missing" and e.get("reason"):
            n_miss += 1
            reasons[e["reason"]] = reasons.get(e["reason"], 0) + 1
        else:
            unaccounted.append(c["capture_id"])
    return {"before": before, "n_universe": n_ext + n_miss + len(unaccounted), "n_extracted": n_ext, "n_missing": n_miss,
            "missing_by_reason": reasons, "n_unaccounted": len(unaccounted), "unaccounted": unaccounted[:20],
            "complete": not unaccounted}


def restore_capture_via_release(cap: dict) -> tuple[Path, Path] | None:
    """Restore one snapshot capture's files from its release into a fresh scratch dir
    (backend/scripts/restore_from_archive.py; needs gh + zstd + network). Returns ``(capture_dir, scratch_root)``
    (the caller removes ``scratch_root`` after the capture) or None. One capture at a time."""
    scratch = Path(tempfile.mkdtemp(prefix="cb3_restore_"))
    script = forecast.ROOT / "backend" / "scripts" / "restore_from_archive.py"
    glob = f"data-dumps/research_lab/snapshots/{cap['capture_id']}/*"
    try:
        r = subprocess.run(["python3", str(script), "--dir", "snapshots", "--path-glob", glob, "--dest", str(scratch)],
                           capture_output=True, text=True, timeout=3600)
    except (OSError, subprocess.SubprocessError):
        return None
    d = Path(scratch) / "data-dumps" / "research_lab" / "snapshots" / cap["capture_id"]
    if r.returncode == 0 and (d / "manifest.json").exists():
        return d, scratch
    shutil.rmtree(scratch, ignore_errors=True)
    return None


def run(
    snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT, root: Path = CB3_ROOT, *,
    mode: str, since: str | None = None, before: str | None = None, budget_s: float = DEFAULT_BUDGET_S,
    clock: Callable[[], float] = time.monotonic, now: Callable[[], str] = utc_now,
    disk_cap_gb: float | None = None, data_dumps: Path | None = None,
    data_dumps_cap_gb: float | None = None, scratch_gb: float = 0.0,
    retry_missing: bool = False, dir_gb: Callable[[Path], float] = _dir_gb, git_commit: str | None = None,
    catalogue: dict[str, str] | None = None, restore: Callable[[dict], tuple[Path, Path] | None] | None = None,
) -> dict:
    """Extract ``quote_state/`` for every complete capture in ``[since, before)`` not yet extracted.

    backfill: oldest first, ``before`` is required and must be <= T3_A_dev_end (T_J4R captures are never read).
    all-new: newest first, no bound (live copying).

    Disk (freeze-check fix 1): refuse (``stopped='refused_no_headroom'``) only when the host cannot take the work:
    ``dir_gb(data_dumps) + projected output + scratch_gb > data_dumps_cap_gb`` where projected output =
    min(``disk_cap_gb`` - used, remaining captures x PER_CAPTURE_GB). The check is repeated between captures.
    There is no fixed trigger below the cap. ``disk_cap`` (own root full) stops with ``stopped='disk_cap'``.

    Backfill completeness (fix 2): ``completeness`` is computed over every complete capture before ``before``
    (host manifests AND release-only catalogue captures). A release-only capture is restored one at a time via
    ``restore`` when given, else recorded ``missing`` with reason ``no_host_manifest``; a host capture whose rows
    are gone is ``missing`` with reason ``rows_archived`` (or restored). ``backfill_complete`` is true only when
    nothing is unaccounted for and the run was not stopped."""
    if mode not in MODES:
        raise ValueError(mode)
    if mode == "backfill":
        if before is None:
            raise WindowError("backfill needs an exclusive upper bound")
        if _ts(before) > _ts(T3_A_DEV_END):
            raise WindowError(f"backfill bound {before} is after T3_A_dev_end {T3_A_DEV_END}")
    snapshot_root, sweep_root, root = Path(snapshot_root), Path(sweep_root), Path(root)
    res: dict[str, Any] = {"cb3_quote_state": EXTRACTOR_VERSION, "mode": mode, "written": 0, "missing": 0,
                           "restored": 0, "stopped": None}
    gc = git_commit if git_commit is not None else _git_commit()
    with _lock(root):
        man = _load_manifest(root)
        caps = universe(snapshot_root, catalogue if catalogue is not None else
                        (catalogue_snapshot_captures() if mode == "backfill" else {}))
        lo = _ts(since) if since else None
        hi = _ts(before) if before else None
        window = [(i, c) for i, c in enumerate(caps)
                  if (lo is None or c["_start"] >= lo) and (hi is None or c["_start"] < hi)]
        retry = retry_missing or restore is not None

        def todo_now() -> list[tuple[int, dict]]:
            out = []
            for i, c in window:
                ent = man["captures"].get(c["capture_id"])
                if ent is None or (ent.get("status") == "missing" and (retry or mode == "all-new")):
                    out.append((i, c))
            return out[::-1] if mode == "all-new" else out

        def short_on_headroom(n_todo: int, used: float) -> bool:
            if data_dumps_cap_gb is None or data_dumps is None:
                return False
            proj = n_todo * PER_CAPTURE_GB
            if disk_cap_gb is not None:
                proj = min(proj, max(disk_cap_gb - used, 0.0))
            return dir_gb(Path(data_dumps)) + proj + scratch_gb > data_dumps_cap_gb

        todo = todo_now()
        used = dir_gb(root) if disk_cap_gb is not None else 0.0
        if short_on_headroom(len(todo), used):
            res.update(stopped="refused_no_headroom", remaining=len(todo), backfill_complete=False)
            return res
        sidx = sweep_index(sweep_root) if todo else {}
        cache: OrderedDict = OrderedDict()
        slowest, t0 = 0.0, clock()
        deadline = t0 + budget_s
        for n, (i, cap) in enumerate(todo):
            if clock() + 1.3 * slowest > deadline:
                res["stopped"] = "budget"
                break
            if disk_cap_gb is not None and used >= disk_cap_gb:
                res["stopped"] = "disk_cap"
                break
            if short_on_headroom(len(todo) - n, used):
                res["stopped"] = "no_headroom"
                break
            c0 = clock()
            cid = cap["capture_id"]
            cap_used, scratch, scratch_root = cap, None, None
            reason = "no_host_manifest" if cap.get("release_only") else "rows_archived"
            if restore is not None:
                try:
                    got_r = restore(cap)
                except Exception:
                    got_r = None
                scratch, scratch_root = got_r if got_r else (None, None)
                if scratch is not None:
                    cap_used = {**cap, "dir": str(scratch), "release_only": False}
                    mf = json.loads((Path(scratch) / "manifest.json").read_text())
                    if mf.get("state") != "complete":  # not a complete capture: not part of the universe
                        reason, cap_used = "restored_not_complete", None
                    elif not (Path(scratch) / "rows.csv.gz").exists():
                        cap_used = None
            elif cap.get("release_only"):
                cap_used = None
            try:
                if cap_used is None:
                    raise forecast.ArchivedDataError(cid)
                rows, ids_df, facts = build_capture(cap_used, caps[max(0, i - N_PREV):i], sidx.get(cid), cache)
            except forecast.ArchivedDataError:
                man["captures"][cid] = {"capture_id": cid, "capture_start_utc": cap["started_utc"],
                                        "status": "missing", "reason": reason,
                                        "extractor_version": EXTRACTOR_VERSION, "written_utc": now(), "mode": mode}
                res["missing"] += 1
            else:
                qdir = root / "quote_state"
                f_rows, f_ids = qdir / f"{cid}.csv.gz", qdir / f"{cid}.ids.csv.gz"
                write_csv_gz(f_rows, rows, ALL_COLUMNS)
                write_csv_gz(f_ids, ids_df, ["market_id"])
                man["captures"][cid] = {
                    "capture_id": cid, "capture_start_utc": cap["started_utc"], "status": "extracted",
                    "extractor_version": EXTRACTOR_VERSION, "schema_version": SCHEMA_VERSION, "git_commit": gc,
                    **facts, "restored": scratch is not None,
                    "sha256": {"csv": sha256_stream(f_rows), "ids": sha256_stream(f_ids)},
                    "written_utc": now(), "mode": mode}
                res["written"] += 1
                res["restored"] += scratch is not None
                if disk_cap_gb is not None:
                    used = dir_gb(root)
            if scratch_root is not None:
                shutil.rmtree(scratch_root, ignore_errors=True)
            _atomic_write_json(root / "manifest.json", man)  # manifest last, after both files exist
            slowest = max(slowest, clock() - c0)
        res["remaining"] = len([1 for i, c in window if man["captures"].get(c["capture_id"]) is None])
        if before is not None:
            res["completeness"] = completeness(caps, man, before)
            man["completeness"] = {**res["completeness"], "checked_utc": now()}
            _atomic_write_json(root / "manifest.json", man)
        res["max_capture_s"] = round(slowest, 2)
        res["backfill_complete"] = bool(mode == "backfill" and res["stopped"] is None
                                        and res["completeness"]["complete"])
        res["elapsed_s"] = round(clock() - t0, 2)
    return res


def read_quote_state(root: Path, capture_id: str, *, ids: bool = False, usecols=None) -> pd.DataFrame:
    """Raw-string frame of one capture's rows (or ids) file. The gz is streamed into the parser (no whole-file string);
    ``usecols`` (names or a predicate) restricts the columns parsed, values are unchanged."""
    p = Path(root) / "quote_state" / f"{capture_id}{'.ids' if ids else ''}.csv.gz"
    with gzip.open(p, "rt", newline="") as fh:
        return pd.read_csv(fh, dtype=str, keep_default_na=False, usecols=usecols)


__all__ = ["ALL_COLUMNS", "SCHEMA_VERSION", "completeness", "restore_capture_via_release", "universe", "CB3_ROOT", "EXTRACTOR_VERSION", "ExtractLocked", "T3_A_DEV_END", "VersionMismatch",
           "WindowError", "build_capture", "read_quote_state", "run"]
