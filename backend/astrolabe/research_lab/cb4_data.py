# ruff: noqa: E501
"""CB4 data jobs (docs/research_lab/CREATIVE_BATCH_4.md CB4-F, sections 1.3, 2.8, 2.10, 4.2, 4.3, 5).

Part 1 (this commit): the ``closewin/`` + ``departures/`` extract from complete live captures (q0080).
Data-only: copies fields exactly as stored, computes no statistic. Read-only on snapshots and sweeps;
writes only under its own root ``data-dumps/research_lab/cb4_extract/`` (own manifest, own lock). A capture
whose raw files are gone from the host is read from the verified release copy, one capture at a time
(scratch deleted before the next batch, peak transient <= ``scratch_cap_bytes`` = 0.2 GB); a capture with
no usable copy is recorded as missing, never reconstructed, and the run continues.

Reuses (imports, does not copy) helpers of ``creative_batch1`` (some private by name; that file is not
edited) and ``forecast.list_complete_captures``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import forecast
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

# =====================================================================================================
# Part 1: closewin / departures extractor (q0080)
# =====================================================================================================

CLOSEWIN_VERSION = "cb4-closewin-v1"
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "book_sweeps"
DATA_DUMPS = forecast.ROOT / "data-dumps"
CB4_ROOT = DATA_DUMPS / "research_lab" / "cb4_extract"
CATALOGUE_DIR = forecast.ROOT / "docs" / "research_lab" / "data_catalogue"
RESTORE_SCRIPT = forecast.ROOT / "backend" / "scripts" / "restore_from_archive.py"
T4_DEV_START = "2026-10-11T12:00:00Z"  # first sidecar capture (CB4 section 1.2)
DEFAULT_BUDGET_S = 420.0  # all-new: well inside the pass line's 600 s
WINDOW_BEFORE_H = 72  # end_date in [capture_start - 72h, capture_start + 30h]
WINDOW_AFTER_H = 30
MIN_LIFE_H = 24  # scheduled life >= 1 day: created_at <= end_date - 24h
SCRATCH_CAP_BYTES = 200_000_000  # peak transient of the release stream (section 2.10)
UNKNOWN_CAPTURE_BYTES = 70_000_000  # planning size of a capture whose catalogue row has no byte count
MODES = ("backfill", "all-new")

CLOSEWIN_COLUMNS = [
    "capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id",
    "clob_token_id_0", "clob_token_id_1", "best_bid", "best_ask", "spread", "last_trade_price", "closed",
    "active", "accepting_orders", "end_date", "created_at", "uma_resolution_statuses", "volume_num",
    "fee_schedule", "fee_category", "neg_risk_market_id", "series_slugs",
    "sweep_best_bid", "sweep_best_ask", "sweep_bid_size_1", "sweep_ask_size_1",
]
DEPARTURE_COLUMNS = ["market_id", "last_seen_capture_id"]
_ROWS_WANT = ["received_utc", "market_id", "condition_id", "event_id", "best_bid", "best_ask", "spread",
              "last_trade_price", "closed", "active", "end_date"]
_EXT_WANT = ["market_id", "clob_token_id_0", "clob_token_id_1", "accepting_orders", "created_at",
             "uma_resolution_statuses", "volume_num", "fee_schedule", "fee_category", "neg_risk_market_id",
             "series_slugs"]
_SWEEP_FIELDS = ["best_bid", "best_ask", "bid_size_1", "ask_size_1"]


class VersionMismatch(RuntimeError):
    """The cb4_extract manifest was written by another extractor version (a new version needs a new root)."""


class ReleaseUnavailable(RuntimeError):
    """The release copy of a capture could not be restored or did not verify."""


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


def _dt(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.replace("", np.nan), utc=True, errors="coerce", format="ISO8601")


def build_capture(rows_path: Path, ext_path: Path, sweep_path: Path | None, capture_id: str,
                  capture_start: str) -> tuple[pd.DataFrame, set[str], dict]:
    """One capture's ``closewin`` rows, the complete listing's market ids, and manifest facts.

    Selection (CB4 section CB4-C): first receipt per market_id; ``end_date`` in
    ``[start - 72h, start + 30h]`` or ``accepting_orders`` false; scheduled life >= 1 day
    (``created_at <= end_date - 24h``). A row whose ``end_date`` or ``created_at`` cannot be parsed
    cannot be tested against the life rule: it is kept (an extract preserves, analysis re-applies the rule)
    and counted. Raises ``ArchivedDataError`` when rows or sidecar are not on this host."""
    forecast.require_local(rows_path)
    forecast.require_local(ext_path)
    rows = _read_str(Path(rows_path), _ROWS_WANT).drop_duplicates("market_id").reset_index(drop=True)
    ext = _read_str(Path(ext_path), _EXT_WANT).drop_duplicates("market_id").set_index("market_id")
    listing = set(rows["market_id"])
    df = rows.join(ext, on="market_id")
    for c in _EXT_WANT[1:]:
        df[c] = df[c].fillna("")
    start = _ts(capture_start)
    end = _dt(df["end_date"])
    created = _dt(df["created_at"])
    lo, hi = pd.Timestamp(start - timedelta(hours=WINDOW_BEFORE_H)), pd.Timestamp(start + timedelta(hours=WINDOW_AFTER_H))
    in_win = ((end >= lo) & (end <= hi)).to_numpy()
    acc_false = (df["accepting_orders"].str.strip().str.lower() == "false").to_numpy()
    unknown_life = (end.isna() | created.isna()).to_numpy()
    life_ok = ((created <= end - pd.Timedelta(hours=MIN_LIFE_H)).to_numpy()) | unknown_life
    keep = (in_win | acc_false) & life_ok
    out = df[keep].copy()
    out["capture_id"], out["capture_start_utc"] = capture_id, capture_start
    out.index = pd.Index(out["market_id"].to_numpy())
    for f in _SWEEP_FIELDS:
        out[f"sweep_{f}"] = ""
    sweep_found = False
    if sweep_path is not None and Path(sweep_path).exists():
        sw = _read_str(Path(sweep_path), ["market_id", *_SWEEP_FIELDS]).drop_duplicates("market_id").set_index("market_id")
        sw = sw[sw.index.isin(out.index)]
        for f in _SWEEP_FIELDS:
            out.loc[sw.index, f"sweep_{f}"] = sw[f]
        sweep_found = True
    out = out.sort_values("market_id").reset_index(drop=True)[CLOSEWIN_COLUMNS]
    facts = {
        "n_listing": len(listing), "n_rows": int(len(out)), "n_in_window": int((in_win & keep).sum()),
        "n_accepting_false": int((acc_false & keep).sum()),
        "n_life_unknown_kept": int((unknown_life & keep).sum()),
        "n_dropped_life_lt_1d": int(((in_win | acc_false) & ~life_ok).sum()),
        "sweep_found": sweep_found,
    }
    return out, listing, facts


# ---- release copies (streamed, one capture's worth of scratch at a time) ---------------------------------


class Catalogue:
    """Index of ``docs/research_lab/data_catalogue/<tag>.jsonl``: archive path -> (tag, bytes, sha256)."""

    def __init__(self, directory: Path = CATALOGUE_DIR):
        self.files: dict[str, tuple[str, int | None, str | None]] = {}
        self.groups: list[tuple[str, str]] = []  # (path_prefix, tag): Mac-era releases (no per-file bytes)
        d = Path(directory)
        for p in sorted(d.glob("*.jsonl")) if d.exists() else []:
            for line in p.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                tag = r.get("release") or p.stem
                if r.get("granularity") == "group":
                    self.groups.append((str(r.get("path_prefix", "")), tag))
                elif r.get("path"):
                    self.files[r["path"]] = (tag, r.get("bytes"), r.get("sha256"))

    def find(self, path: str) -> tuple[str, int | None, str | None] | None:
        if path in self.files:
            return self.files[path]
        for pre, tag in self.groups:
            if pre and path.startswith(pre):
                return tag, None, None
        return None


def _restore_with_script(tag: str, globs: list[str], dest: Path) -> bool:
    """Default restorer: ``restore_from_archive.py`` (streams the release, re-hashes every restored file
    against files.sha256, exits non-zero on any mismatch). The parts are one zstd stream, so this reads the
    whole release once per call."""
    cmd = [sys.executable, str(RESTORE_SCRIPT), "--tag", tag, "--dest", str(dest)]
    for g in globs:
        cmd += ["--path-glob", g]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=4 * 3600)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


class ReleaseCopies:
    """Restores the raw files of captures that are gone from the host into a scratch directory.

    ``ensure`` restores a batch (the requested capture plus the following ones that fit under
    ``cap_bytes`` by catalogue size, at least the requested one) with ONE call per release tag, because the
    release is a single stream and a call reads all of it; extraction still happens one capture at a time.
    The previous batch is deleted before a new one is restored, and everything is deleted by ``cleanup``."""

    def __init__(self, scratch: Path, *, catalogue: Catalogue | None = None, cap_bytes: int = SCRATCH_CAP_BYTES,
                 restore: Callable[[str, list[str], Path], bool] | None = None):
        self.scratch = Path(scratch)
        self.cat = catalogue if catalogue is not None else Catalogue()
        self.cap_bytes = int(cap_bytes)
        self.restore = restore if restore is not None else _restore_with_script
        self.batch: dict[str, dict] = {}  # cid -> {'rows','ext','sweep'}
        self.failures = 0
        self.restores = 0

    @staticmethod
    def archive_paths(cap_dir_name: str, sweep_dir_name: str | None) -> dict[str, str]:
        base = f"data-dumps/research_lab/snapshots/{cap_dir_name}"
        p = {"rows": f"{base}/rows.csv.gz", "ext": f"{base}/rows_ext.csv.gz"}
        if sweep_dir_name:
            p["sweep"] = f"data-dumps/research_lab/book_sweeps/{sweep_dir_name}/rows.csv.gz"
        return p

    def _plan(self, cap: dict, sweep_dir: Path | None) -> tuple[dict[str, str], int] | None:
        paths = self.archive_paths(Path(cap["dir"]).name, Path(sweep_dir).name if sweep_dir else None)
        size = 0
        for key in ("rows", "ext"):
            hit = self.cat.find(paths[key])
            if hit is None:
                return None  # no release copy known for a required file
            size += hit[1] or UNKNOWN_CAPTURE_BYTES // 2
        if "sweep" in paths:
            hit = self.cat.find(paths["sweep"])
            if hit is None:
                paths.pop("sweep")
            else:
                size += hit[1] or UNKNOWN_CAPTURE_BYTES // 4
        return paths, size

    def cleanup(self) -> None:
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.batch = {}

    def ensure(self, cap: dict, sweep_dir: Path | None, upcoming: list[tuple[dict, Path | None]]) -> dict | None:
        """Local scratch paths for ``cap`` (rows, ext, optional sweep), or None when there is no verified
        release copy. ``upcoming`` = the following captures, in processing order, that are also gone from
        the host (candidates for the same restore call)."""
        cid = cap["capture_id"]
        if cid in self.batch:
            return self.batch[cid]
        plan = self._plan(cap, sweep_dir)
        if plan is None:
            return None
        if plan[1] > self.cap_bytes:
            return None  # a single capture larger than the scratch cap is never restored
        self.cleanup()
        wanted: list[tuple[dict, dict[str, str]]] = [(cap, plan[0])]
        total = plan[1]
        for c2, sw2 in upcoming:
            p2 = self._plan(c2, sw2)
            if p2 is None or total + p2[1] > self.cap_bytes:
                continue
            wanted.append((c2, p2[0]))
            total += p2[1]
        by_tag: dict[str, list[str]] = {}
        expect: dict[str, tuple[str, str, str | None]] = {}
        for _c, paths in wanted:
            for key, ap in paths.items():
                tag, _b, sha = self.cat.find(ap)  # type: ignore[misc]
                by_tag.setdefault(tag, []).append(ap)
                expect[ap] = (tag, key, sha)
        self.scratch.mkdir(parents=True, exist_ok=True)
        for tag, globs in by_tag.items():
            self.restores += 1
            if not self.restore(tag, sorted(set(globs)), self.scratch):
                self.failures += 1
                self.cleanup()
                raise ReleaseUnavailable(f"restore of {tag} failed")
        self.failures = 0
        for c2, paths in wanted:
            files: dict[str, Path] = {}
            ok = True
            for key, ap in paths.items():
                local = self.scratch / ap
                tag, _k, sha = expect[ap]
                if not local.is_file() or (sha and sha256_stream(local) != sha):
                    ok = False
                    break
                files[key] = local
            if ok:
                self.batch[c2["capture_id"]] = files
        return self.batch.get(cid)


# ---- driver --------------------------------------------------------------------------------------------


def _load_manifest(root: Path) -> dict:
    p = Path(root) / "manifest.json"
    if p.exists():
        man = json.loads(p.read_text())
        if man.get("extractor_version") != CLOSEWIN_VERSION:
            raise VersionMismatch(f"{p}: {man.get('extractor_version')!r} != {CLOSEWIN_VERSION!r}; use a new root")
        return man
    return {"extractor_version": CLOSEWIN_VERSION, "captures": {}}


def _used_gb(root: Path, dir_gb: Callable[[Path], float]) -> float:
    return dir_gb(Path(root) / "closewin") + dir_gb(Path(root) / "departures")


def _is_local(cap: dict) -> bool:
    d = Path(cap["dir"])
    return (d / "rows.csv.gz").exists() and (d / "rows_ext.csv.gz").exists()


def run_closewin(
    snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT, root: Path = CB4_ROOT, *,
    mode: str, since: str | None = T4_DEV_START, before: str | None = None, budget_s: float = DEFAULT_BUDGET_S,
    clock: Callable[[], float] = time.monotonic, now: Callable[[], str] = utc_now,
    disk_cap_gb: float | None = None, data_dumps: Path | None = None, data_dumps_max_gb: float | None = None,
    retry_missing: bool = False, dir_gb: Callable[[Path], float] = _dir_gb, git_commit: str | None = None,
    release: ReleaseCopies | None = None,
) -> dict:
    """Extract ``closewin/`` and ``departures/`` for every complete capture in ``[since, before)`` not yet
    extracted, oldest first (so the previous capture's ``closewin`` exists when ``departures`` is built).

    backfill: reports ``backfill_complete``; all-new: the live pass step (not wired yet). Stops at the budget,
    at ``disk_cap_gb`` of the written tables, and refuses (``stopped='refused_data_dumps_over_cap'``) while
    ``data_dumps`` exceeds ``data_dumps_max_gb``; that check is repeated between captures. Idempotent by
    capture_id. A capture whose raw files are gone and that has no verified release copy is recorded as
    ``missing`` and the run continues. ``release`` (backfill with ``--release-stream``) restores missing
    captures from the release copies into a scratch directory that never exceeds its cap."""
    if mode not in MODES:
        raise ValueError(mode)
    snapshot_root, sweep_root, root = Path(snapshot_root), Path(sweep_root), Path(root)
    res: dict[str, Any] = {"cb4_closewin": CLOSEWIN_VERSION, "mode": mode, "written": 0, "missing": 0,
                           "from_release": 0, "stopped": None}

    def over_dumps() -> bool:
        return data_dumps_max_gb is not None and data_dumps is not None and dir_gb(Path(data_dumps)) > data_dumps_max_gb

    if over_dumps():
        res.update(stopped="refused_data_dumps_over_cap", remaining=None, backfill_complete=False)
        return res
    gc = git_commit if git_commit is not None else _git_commit()
    with _lock(root):
        man = _load_manifest(root)
        caps = forecast.list_complete_captures(snapshot_root)
        lo = _ts(since) if since else None
        hi = _ts(before) if before else None
        window = [(i, c) for i, c in enumerate(caps)
                  if (lo is None or c["_start"] >= lo) and (hi is None or c["_start"] < hi)]

        def todo_now() -> list[tuple[int, dict]]:
            out = []
            for i, c in window:
                ent = man["captures"].get(c["capture_id"])
                if ent is None or (ent.get("status") == "missing" and (retry_missing or mode == "all-new")):
                    out.append((i, c))
            return out

        todo = todo_now()
        sidx = sweep_index(sweep_root) if todo else {}
        used = _used_gb(root, dir_gb) if disk_cap_gb is not None else 0.0
        slowest, t0 = 0.0, clock()
        deadline = t0 + budget_s

        def first_sweep(cid: str) -> Path | None:
            d = sidx.get(cid) or {}
            return Path(d[min(d)]) if d else None

        try:
            for n, (i, cap) in enumerate(todo):
                if clock() + 1.3 * slowest > deadline:
                    res["stopped"] = "budget"
                    break
                if disk_cap_gb is not None and used >= disk_cap_gb:
                    res["stopped"] = "disk_cap"
                    break
                if over_dumps():
                    res["stopped"] = "data_dumps_over_cap"
                    break
                c0 = clock()
                cid, start = cap["capture_id"], cap["started_utc"]
                cdir = Path(cap["dir"])
                sw_dir = first_sweep(cid)
                source, reason = "host", None
                rows_p, ext_p = cdir / "rows.csv.gz", cdir / "rows_ext.csv.gz"
                sw_p = (sw_dir / "rows.csv.gz") if sw_dir is not None else None
                if not _is_local(cap):
                    files = None
                    if release is not None:
                        upcoming = [(c2, first_sweep(c2["capture_id"])) for _j, c2 in todo[n + 1:] if not _is_local(c2)]
                        try:
                            files = release.ensure(cap, sw_dir, upcoming)
                        except ReleaseUnavailable:
                            if release.failures >= 2:
                                res["stopped"] = "release_unavailable"
                                break
                            files = None
                            reason = "release_restore_failed"
                    if files is None:
                        reason = reason or "archived_no_release_copy"
                    else:
                        rows_p, ext_p, sw_p = files["rows"], files["ext"], files.get("sweep")
                        source = "release"
                try:
                    if reason is not None:
                        raise forecast.ArchivedDataError(reason)
                    out, listing, facts = build_capture(rows_p, ext_p, sw_p, cid, start)
                    src_hash = {"rows": sha256_stream(rows_p), "rows_ext": sha256_stream(ext_p)}
                    if facts["sweep_found"] and sw_p is not None:
                        src_hash["sweep_1"] = sha256_stream(sw_p)
                except forecast.ArchivedDataError:
                    man["captures"][cid] = {"capture_id": cid, "capture_start_utc": start, "status": "missing",
                                            "reason": reason or "archived_no_release_copy",
                                            "extractor_version": CLOSEWIN_VERSION, "written_utc": now(), "mode": mode}
                    res["missing"] += 1
                else:
                    # departures: previous complete capture's closewin ids vs this capture's complete listing
                    prev = caps[i - 1] if i > 0 else None
                    prev_ent = man["captures"].get(prev["capture_id"]) if prev is not None else None
                    dep_status, dep_df = "no_previous_capture", None
                    if prev is not None:
                        pf = Path(root) / "closewin" / f"{prev['capture_id']}.csv.gz"
                        if prev_ent and prev_ent.get("status") == "extracted" and pf.exists():
                            pids = _read_str(pf, ["market_id"])["market_id"]
                            gone = sorted(set(pids) - listing)
                            dep_df = pd.DataFrame({"market_id": gone, "last_seen_capture_id": prev["capture_id"]})
                            dep_status = "ok"
                        else:
                            dep_status = "previous_closewin_unavailable"
                    f_cw = root / "closewin" / f"{cid}.csv.gz"
                    write_csv_gz(f_cw, out, CLOSEWIN_COLUMNS)
                    sha = {"closewin": sha256_stream(f_cw)}
                    if dep_df is not None:
                        f_dp = root / "departures" / f"{cid}.csv.gz"
                        write_csv_gz(f_dp, dep_df, DEPARTURE_COLUMNS)
                        sha["departures"] = sha256_stream(f_dp)
                    man["captures"][cid] = {
                        "capture_id": cid, "capture_start_utc": start, "status": "extracted", "source": source,
                        "extractor_version": CLOSEWIN_VERSION, "git_commit": gc, **facts,
                        "departures_status": dep_status, "n_departures": None if dep_df is None else int(len(dep_df)),
                        "previous_capture_id": prev["capture_id"] if prev is not None else None,
                        "source_sha256": src_hash, "sha256": sha, "written_utc": now(), "mode": mode}
                    res["written"] += 1
                    res["from_release"] += int(source == "release")
                    if disk_cap_gb is not None:
                        used = _used_gb(root, dir_gb)
                _atomic_write_json(root / "manifest.json", man)  # manifest last, after the table files exist
                slowest = max(slowest, clock() - c0)
        finally:
            if release is not None:
                release.cleanup()
        res["remaining"] = len([1 for _i, c in window if man["captures"].get(c["capture_id"]) is None])
        res["n_missing_total"] = sum(1 for e in man["captures"].values() if e.get("status") == "missing")
        res["max_capture_s"] = round(slowest, 2)
        res["backfill_complete"] = bool(mode == "backfill" and res["remaining"] == 0 and res["stopped"] is None)
        res["elapsed_s"] = round(clock() - t0, 2)
    return res


def read_closewin(root: Path, capture_id: str, *, departures: bool = False) -> pd.DataFrame:
    """Raw-string frame of one capture's closewin (or departures) file."""
    p = Path(root) / ("departures" if departures else "closewin") / f"{capture_id}.csv.gz"
    return pd.read_csv(p, dtype=str, keep_default_na=False)


__all__ = ["CB4_ROOT", "CLOSEWIN_COLUMNS", "CLOSEWIN_VERSION", "Catalogue", "ExtractLocked", "ReleaseCopies",
           "ReleaseUnavailable", "VersionMismatch", "build_capture", "read_closewin", "run_closewin"]
