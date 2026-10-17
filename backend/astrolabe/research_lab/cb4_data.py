# ruff: noqa: E501
"""CB4 data jobs (docs/research_lab/CREATIVE_BATCH_4.md CB4-F, sections 1.3, 2.8, 2.10, 4.2, 4.3, 5).

Part 1: the ``closewin/`` + ``departures/`` extract from complete live captures (q0080).
Part 2: the ``h7_cb4_era`` and ``h7_cb4_series`` fetches (q0081, q0082) and their seals (q0083).
Data-only: copies fields exactly as stored, computes no statistic. Read-only on snapshots and sweeps;
writes only under its own root ``data-dumps/research_lab/cb4_extract/`` (own manifest, own lock). A capture
whose raw files are gone from the host is read from the verified release copy, one capture at a time
(scratch deleted before the next batch, peak transient <= ``scratch_cap_bytes`` = 0.2 GB); a capture with
no usable copy is recorded as missing, never reconstructed, and the run continues.

Reuses (imports, does not copy) helpers of ``creative_batch1`` (some private by name; that file is not
edited) and ``forecast.list_complete_captures``.
"""

from __future__ import annotations

import bisect
import gzip
import hashlib
import inspect
import io
import json
import math
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import forecast, h5_seal
from . import history_backfill as hb
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

CLOSEWIN_VERSION = "cb4-closewin-v2"  # v2 = freeze-check fixes 1-4 (1/0 flags, ext_present, sidecar version)
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
    "sweep_best_bid", "sweep_best_ask", "sweep_bid_size_1", "sweep_ask_size_1", "ext_present",
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


def flag_off(v: Any) -> bool:
    """True when a sidecar boolean is false. The sidecar writes ``accepting_orders`` as 1/0 (``extract._flag``);
    'false'/'False'/'0'/'0.0' are all false; blank, 1/true/anything else is not (freeze-check fix 1)."""
    t = str(v).strip().lower()
    return t in ("0", "0.0", "false", "f", "no")


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
    ext_present = df["market_id"].isin(ext.index).to_numpy()
    for c in _EXT_WANT[1:]:
        df[c] = df[c].fillna("")
    df["ext_present"] = np.where(ext_present, "1", "0")
    start = _ts(capture_start)
    end = _dt(df["end_date"])
    created = _dt(df["created_at"])
    lo, hi = pd.Timestamp(start - timedelta(hours=WINDOW_BEFORE_H)), pd.Timestamp(start + timedelta(hours=WINDOW_AFTER_H))
    in_win = ((end >= lo) & (end <= hi)).to_numpy()
    acc_false = df["accepting_orders"].map(flag_off).to_numpy(dtype=bool) & ext_present
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
        "sweep_found": sweep_found, "n_rows_without_sidecar": int((~ext_present).sum()),
        "n_selected_without_sidecar": int((~ext_present & keep).sum()),
    }
    facts.update(_sidecar_facts(Path(ext_path)))
    return out, listing, facts


def _sidecar_facts(ext_path: Path) -> dict:
    """``ext_version`` / ``sidecar_status`` of the capture's ``ext_manifest.json`` (beside rows_ext.csv.gz), if present."""
    mp = Path(ext_path).with_name("ext_manifest.json")
    try:
        m = json.loads(mp.read_text())
    except (OSError, ValueError):
        return {"ext_version": None, "sidecar_status": None}
    return {"ext_version": m.get("ext_version"), "sidecar_status": m.get("sidecar_status")}


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

    def snapshot_dirs(self) -> dict[str, str]:
        """{capture dir name: start ISO} of every snapshot capture dir the catalogue knows (time parsed from the
        dir name ``YYYYmmddTHHMMSSZ_hash``)."""
        rx = re.compile(r"data-dumps/research_lab/snapshots/(\d{8}T\d{6}Z_[0-9a-f]+)/")
        out: dict[str, str] = {}
        for path in [*self.files, *(pre for pre, _t in self.groups)]:
            m = rx.search(path)
            if m and m.group(1) not in out:
                t = datetime.strptime(m.group(1)[:16], "%Y%m%dT%H%M%SZ")
                out[m.group(1)] = t.strftime("%Y-%m-%dT%H:%M:%SZ")
        return out

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
    The previous batch is deleted before a new one is restored, and everything is deleted by ``cleanup``.
    A restore call is retried (``retries`` attempts, ``backoff_s`` * attempt apart) before ``ReleaseUnavailable``
    is raised; the caller then stops the run and leaves the capture pending (it is never marked missing for a
    transient failure). A genuine problem is returned as a reason: ``no_release_copy``, ``release_copy_too_large``,
    ``release_hash_mismatch``, ``release_file_missing_after_restore``."""

    def __init__(self, scratch: Path, *, catalogue: Catalogue | None = None, cap_bytes: int = SCRATCH_CAP_BYTES,
                 restore: Callable[[str, list[str], Path], bool] | None = None, retries: int = 3,
                 backoff_s: float = 60.0, sleep: Callable[[float], None] = time.sleep):
        self.scratch = Path(scratch)
        self.cat = catalogue if catalogue is not None else Catalogue()
        self.cap_bytes = int(cap_bytes)
        self.restore = restore if restore is not None else _restore_with_script
        self.retries, self.backoff_s, self.sleep = max(1, int(retries)), backoff_s, sleep
        self.batch: dict[str, dict] = {}  # cid -> {'rows','ext','sweep'[,'manifest']}
        self.reasons: dict[str, str] = {}  # cid -> reason of a batch member that did not verify
        self.restores = 0
        self.restore_retries = 0

    @staticmethod
    def archive_paths(cap_dir_name: str, sweep_dir_name: str | None, with_manifest: bool = False) -> dict[str, str]:
        base = f"data-dumps/research_lab/snapshots/{cap_dir_name}"
        p = {"rows": f"{base}/rows.csv.gz", "ext": f"{base}/rows_ext.csv.gz"}
        if with_manifest:
            p["manifest"] = f"{base}/manifest.json"
        if sweep_dir_name:
            p["sweep"] = f"data-dumps/research_lab/book_sweeps/{sweep_dir_name}/rows.csv.gz"
        return p

    def _plan(self, cap: dict, sweep_dir: Path | None) -> tuple[dict[str, str], int] | None:
        paths = self.archive_paths(Path(cap["dir"]).name, Path(sweep_dir).name if sweep_dir else None,
                                   bool(cap.get("release_only")))
        size = 0
        for key in ("rows", "ext", "manifest"):
            if key not in paths:
                continue
            hit = self.cat.find(paths[key])
            if hit is None:
                return None  # no release copy known for a required file
            size += hit[1] or (UNKNOWN_CAPTURE_BYTES // 2 if key != "manifest" else 0)
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
        self.reasons = {}

    def _restore_retry(self, tag: str, globs: list[str]) -> bool:
        for attempt in range(1, self.retries + 1):
            self.restores += 1
            if self.restore(tag, globs, self.scratch):
                return True
            self.restore_retries += 1
            if attempt < self.retries:
                self.sleep(self.backoff_s * attempt)
        return False

    def ensure(self, cap: dict, sweep_dir: Path | None, upcoming: list[tuple[dict, Path | None]]
               ) -> tuple[dict | None, str | None]:
        """(local scratch paths, None) for ``cap``, or (None, reason). Raises ``ReleaseUnavailable`` when the
        restore keeps failing. ``upcoming`` = the following captures, in processing order, that are also gone
        from the host (candidates for the same restore call)."""
        cid = cap["capture_id"]
        if cid in self.batch:
            return self.batch[cid], None
        if cid in self.reasons:
            return None, self.reasons[cid]
        plan = self._plan(cap, sweep_dir)
        if plan is None:
            return None, "no_release_copy"
        if plan[1] > self.cap_bytes:
            return None, "release_copy_too_large"  # a single capture larger than the scratch cap is never restored
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
        expect: dict[str, str | None] = {}
        for _c, paths in wanted:
            for ap in paths.values():
                tag, _b, sha = self.cat.find(ap)  # type: ignore[misc]
                by_tag.setdefault(tag, []).append(ap)
                expect[ap] = sha
        self.scratch.mkdir(parents=True, exist_ok=True)
        for tag, globs in by_tag.items():
            if not self._restore_retry(tag, sorted(set(globs))):
                self.cleanup()
                raise ReleaseUnavailable(f"restore of {tag} failed after {self.retries} attempts")
        for c2, paths in wanted:
            files: dict[str, Path] = {}
            reason = None
            for key, ap in paths.items():
                local = self.scratch / ap
                if not local.is_file():
                    reason = "release_file_missing_after_restore"
                    break
                if expect[ap] and sha256_stream(local) != expect[ap]:
                    reason = "release_hash_mismatch"
                    break
                files[key] = local
            if reason:
                self.reasons[c2["capture_id"]] = reason
            else:
                self.batch[c2["capture_id"]] = files
        return self.batch.get(cid), self.reasons.get(cid)


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


RELEASE_UNAVAILABLE_STOP = 5  # consecutive unavailable release copies that end a run (outage guard)


def run_closewin(
    snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT, root: Path = CB4_ROOT, *,
    mode: str, since: str | None = T4_DEV_START, before: str | None = None, budget_s: float = DEFAULT_BUDGET_S,
    clock: Callable[[], float] = time.monotonic, now: Callable[[], str] = utc_now,
    disk_cap_gb: float | None = None, data_dumps: Path | None = None, data_dumps_max_gb: float | None = None,
    retry_missing: bool = False, dir_gb: Callable[[Path], float] = _dir_gb, git_commit: str | None = None,
    release: ReleaseCopies | None = None, catalogue: Catalogue | None = None,
    scratch_gb: float = SCRATCH_CAP_BYTES / 1e9,
) -> dict:
    """Extract ``closewin/`` and ``departures/`` for every complete capture in ``[since, before)`` not yet
    extracted, oldest first (so the previous capture's ``closewin`` exists when ``departures`` is built).

    backfill: reports ``backfill_complete`` (plus ``n_release_unavailable`` and the recovery command); all-new: the live
    pass step (wired after CB4 closewin in the collection pass; retries ``missing`` captures). Stops at the budget,
    at ``disk_cap_gb`` of the written tables, and refuses (``stopped='refused_data_dumps_over_cap'``) only on
    real headroom: ``data_dumps`` size + the output still allowed (``disk_cap_gb`` minus what is written, 0.4
    by default) + the scratch (0.2 with ``release``) above ``data_dumps_max_gb`` (the 12 GB cap); repeated
    between captures. Idempotent by capture_id. Captures that exist only in the release catalogue (no host
    manifest) are added to the list (``release_only``); without ``release`` they are recorded
    ``no_host_manifest``. A capture whose raw files are gone and that has no verified release copy is recorded
    as ``missing`` with the true reason and the run continues; a restore failure (after retries) is recorded
    ``missing`` / ``release_unavailable`` and the run continues, stopping only after RELEASE_UNAVAILABLE_STOP in a row. ``release`` (backfill with ``--release-stream``) restores missing
    captures from the release copies into a scratch directory that never exceeds its cap."""
    if mode not in MODES:
        raise ValueError(mode)
    snapshot_root, sweep_root, root = Path(snapshot_root), Path(sweep_root), Path(root)
    res: dict[str, Any] = {"cb4_closewin": CLOSEWIN_VERSION, "mode": mode, "written": 0, "missing": 0,
                           "from_release": 0, "stopped": None}

    out_allow = disk_cap_gb if disk_cap_gb is not None else 0.40

    def over_dumps(written_gb: float = 0.0) -> bool:
        if data_dumps_max_gb is None or data_dumps is None:
            return False
        need = dir_gb(Path(data_dumps)) + max(0.0, out_allow - written_gb) + (scratch_gb if release is not None else 0.0)
        return need > data_dumps_max_gb

    if over_dumps():
        res.update(stopped="refused_data_dumps_over_cap", remaining=None, backfill_complete=False)
        return res
    gc = git_commit if git_commit is not None else _git_commit()
    with _lock(root):
        man = _load_manifest(root)
        caps = forecast.list_complete_captures(snapshot_root)
        if catalogue is not None:  # captures that exist only in a release (no host manifest)
            have = {c["capture_id"] for c in caps} | {Path(c["dir"]).name for c in caps}
            for name, st in catalogue.snapshot_dirs().items():
                if name not in have:
                    caps.append({"capture_id": name, "started_utc": st, "_start": _ts(st), "dir": str(snapshot_root / name),
                                 "release_only": True, "state": "complete"})
            caps.sort(key=lambda c: c["_start"])
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
        consec_unavail = 0
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
                if over_dumps(used):
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
                            files, reason = release.ensure(cap, sw_dir, upcoming)
                        except ReleaseUnavailable:
                            # Recorded as missing (counted; retried by --retry-missing and by every all-new pass) and the walk continues, so one
                            # unreachable release (e.g. a capture only in the separate val ledger) cannot stall every later capture. A run of
                            # RELEASE_UNAVAILABLE_STOP consecutive failures is a real outage: stop, so a network fault never relabels the backlog.
                            res["restore_retries"] = release.restore_retries
                            consec_unavail += 1
                            files, reason = None, "release_unavailable"
                            if consec_unavail >= RELEASE_UNAVAILABLE_STOP:
                                man["captures"][cid] = {"capture_id": cid, "capture_start_utc": start, "status": "missing", "reason": reason,
                                                        "release_only": bool(cap.get("release_only")), "extractor_version": CLOSEWIN_VERSION,
                                                        "written_utc": now(), "mode": mode}
                                res["missing"] += 1
                                _atomic_write_json(root / "manifest.json", man)
                                res["stopped"] = "release_unavailable"
                                break
                        else:
                            consec_unavail = 0
                        if files is not None and cap.get("release_only"):
                            try:
                                mstate = json.loads(Path(files["manifest"]).read_text()).get("state")
                            except (OSError, ValueError):
                                mstate = None
                            if mstate != "complete":
                                files, reason = None, "release_manifest_not_complete"
                    if files is None:
                        prior = (man["captures"].get(cid) or {}).get("reason")
                        if release is None and prior == "release_unavailable":
                            reason = reason or "release_unavailable"  # no release stream this pass: never relabel the earlier outage (fix 11)
                        reason = reason or ("no_host_manifest" if cap.get("release_only") else "archived_no_release_copy")
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
                                            "reason": reason or "archived_no_release_copy", "release_only": bool(cap.get("release_only")),
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
        res["n_release_only"] = sum(1 for _i, c in window if c.get("release_only"))
        res["n_missing_total"] = sum(1 for e in man["captures"].values() if e.get("status") == "missing")
        res["max_capture_s"] = round(slowest, 2)
        res["backfill_complete"] = bool(mode == "backfill" and res["remaining"] == 0 and res["stopped"] is None)
        res["n_release_unavailable"] = sum(1 for e in man["captures"].values()
                                           if e.get("status") == "missing" and e.get("reason") == "release_unavailable")
        if res["n_release_unavailable"]:
            res["recovery_command"] = "run_cb4.py closewin --backfill-from <since> --retry-missing --release-stream"
        res["elapsed_s"] = round(clock() - t0, 2)
    return res


def read_closewin(root: Path, capture_id: str, *, departures: bool = False) -> pd.DataFrame:
    """Raw-string frame of one capture's closewin (or departures) file."""
    p = Path(root) / ("departures" if departures else "closewin") / f"{capture_id}.csv.gz"
    return pd.read_csv(p, dtype=str, keep_default_na=False)


# =====================================================================================================
# Part 2: h7_cb4_era / h7_cb4_series fetches (q0081, q0082) and seals (q0083)
# =====================================================================================================

FETCH_VERSION = "h7-cb4-fetch-v1"
ERA_RUN_ID = "h7_cb4_era"
SERIES_RUN_ID = "h7_cb4_series"
H7_RUN_IDS = h5_seal.H7_RUN_IDS
REFUSED_RUN_IDS = ("h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather")
REFUSED_ROOTS = ("cb1_extract", "cb2_extract")
T_SEAL = "2026-10-22T00:00:00Z"
T_SEAL_EPOCH = hb.T_SEAL_EPOCH
DAY = 86400.0
HOUR = 3600.0
HIST_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "history"
SEALS_DIR = h5_seal.SEALS_DIR
SERIES_RULES_FILE = SEALS_DIR / "cb4_series_rules.json"
H5_SEAL_COPY = "h5_cb1_SEAL.json"
OUTCOME_FILE = "outcomes_guarded.csv.gz"
NOT_RUN_FILE = "NOT_RUN_DEADLINE.json"
ERA_COMPLETE_TOKEN = "era_fetch_complete"
SERIES_COMPLETE_TOKEN = "series_fetch_complete"
NOT_RUN_TOKEN = "not_run_deadline"
MAX_ITEM_ATTEMPTS = 3
DATA_DUMPS_FETCH_CAP_GB = 10.0  # every h7 fetch refuses to start while data-dumps exceeds this (cap 12 GB)

# ---- CH53 (era) declaration ----------------------------------------------------------------------------
ERA_SEED = "arepo-h7-era"
ERA_PER_CELL = 800
ERA_PERIODS = (("P0", "2025-12-01", "2026-02-18"), ("P1", "2026-02-25", "2026-03-30"), ("P2", "2026-04-06", "2026-04-28"))
ERA_ORIGIN_H = 72
ERA_MIN_LIFE_D = 4
ERA_PRICE_LOOKBACK_D = 8  # prices [end - 72h - 8d, end + 1d]
ERA_PRICE_LEAD_D = 1
ERA_MAX_TRADES = 10000
FRAME_WINDOWS_PER_DAY = 6
FRAME_WINDOW_MINUTES = 15
FRAME_PAGES_PER_WINDOW = 20
FRAME_MAIN_COLUMNS = ["market_id", "condition_id", "token0", "token1", "event_id", "fee_category", "created_at",
                      "start_at", "end_at", "start_epoch", "end_epoch", "neg_risk", "weather_title", "group", "period"]
OUTCOME_FIELDS = ["status", "closed", "closed_time", "close_epoch", "uma_status", "outcome_prices", "liquidity", "volume"]
ERA_OUTCOME_COLUMNS = ["market_id", *OUTCOME_FIELDS]

# ---- CH50 (series) declaration -----------------------------------------------------------------------
SERIES_SEED = "arepo-h7-series"
SERIES_N = 400
SERIES_N_SPORTS = 60
SERIES_MEMBERS = 31
SERIES_ROLL_FROM = "2025-10-01"
SERIES_WALK_FROM = "2025-09-24"
SERIES_ROLL_TO_MARGIN_D = 3
SERIES_WALK_AFTER_D = 2
SERIES_WINDOW_MIN_S = 3600  # a capped walk window is halved down to this width, then dropped and counted
SERIES_WALK_BASE_DAYS = 7
CADENCE_BOUNDS = {"daily": (20 * HOUR, 28 * HOUR), "weekly": (6 * DAY, 8 * DAY), "monthly": (27 * DAY, 32 * DAY)}
HORIZONS = {"daily": {"M_h": 3.0, "V_end_h": 12.0}, "weekly": {"M_h": 6.0, "V_end_h": 48.0},
            "monthly": {"M_h": 6.0, "V_end_h": 48.0}}
SUCC_CREATED_LAG_H = 1.0
PRICE_PRE_H = 3.0  # successor prices [t0' - 3h, V_end + 2h]
PRICE_POST_H = 2.0
PSEUDO_GAP_H = 6.0
PRED_PRICE_H = 3.0  # winning predecessor token prices [t0 - 3h, t0 + 3h] (publicity check)
PRED_TRADES = 1000  # one trade page of the winning predecessor market
WIN_PRICE = 0.99
SPLIT_HOLDOUT_FRAC = 0.40
SPLIT_EMBARGO_D = 3

SERIES_OUTCOME_COLUMNS = ["unit_id", "pred_event_id", "pred_winner_key", "pred_closed_time", "pred_outcome_prices",
                          "side_market_id", "side_token_index", "pred_market_id", "pred_token_index"]


class Cb4Error(RuntimeError):
    """Base class for refusals."""


EXIT_TEMPFAIL = 75  # EX_TEMPFAIL: "not now"; scripts/oracle/queue_worker.py waits and retries (not an attempt)


class Refused(Cb4Error):
    """A guard refused to run. ``code`` is the process exit status (2, or 75 for a transient precondition)."""

    def __init__(self, msg: str = "", *, code: int = 2) -> None:
        super().__init__(msg)
        self.code = code


def _ep(s: str) -> float:
    """UTC epoch from ``YYYY-MM-DD``, ``YYYY-MM-DDTHH:MMZ`` or ``YYYY-MM-DDTHH:MM:SSZ``."""
    s = str(s).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC).timestamp()
        except ValueError:
            pass
    raise ValueError(f"unparseable time {s!r}")


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(v: Any) -> float | None:
    """Epoch of an ISO-ish timestamp string (Gamma uses ``2026-01-01T00:00:00Z``, ``2026-01-01 00:00:00+00`` ...)."""
    if v in (None, ""):
        return None
    try:
        s = str(v).strip().replace(" ", "T").replace("Z", "+00:00")
        if re.search(r"[+-]\d\d$", s):
            s += ":00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.timestamp()
    except ValueError:
        return None


def refuse_run_id(run_id: str, allowed: tuple[str, ...] | None = None) -> str:
    if run_id in REFUSED_RUN_IDS:
        raise Refused(f"run id {run_id!r} is sealed or belongs to another batch; CB4 refuses it")
    if allowed is not None and run_id not in allowed:
        raise Refused(f"this command writes only {allowed}, not {run_id!r}")
    return run_id


def refuse_path(path: Path) -> Path:
    """CB4 never opens ``cb1_extract/`` or ``cb2_extract/`` (section 1.3)."""
    if any(part in REFUSED_ROOTS for part in Path(path).parts):
        raise Refused(f"path {path} is under a CB1/CB2 extract root; CB4 refuses it")
    return Path(path)


def _csv_list(v) -> list[str]:
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def declaration_h7() -> dict:
    """Everything the two fetches declare (hashed into the manifests)."""
    return {
        "version": FETCH_VERSION, "t_seal": T_SEAL,
        "era": {"seed": ERA_SEED, "per_cell": ERA_PER_CELL, "periods": [list(p) for p in ERA_PERIODS],
                "origin_window_h": ERA_ORIGIN_H, "min_life_d": ERA_MIN_LIFE_D,
                "price_window": [ERA_PRICE_LOOKBACK_D, ERA_PRICE_LEAD_D], "max_trades": ERA_MAX_TRADES,
                "frame": [FRAME_WINDOWS_PER_DAY, FRAME_WINDOW_MINUTES, FRAME_PAGES_PER_WINDOW]},
        "series": {"seed": SERIES_SEED, "n": SERIES_N, "n_sports": SERIES_N_SPORTS, "members": SERIES_MEMBERS,
                   "roll_from": SERIES_ROLL_FROM, "walk_from": SERIES_WALK_FROM,
                   "cadence_bounds_s": CADENCE_BOUNDS, "horizons": HORIZONS, "succ_created_lag_h": SUCC_CREATED_LAG_H,
                   "price_h": [PRICE_PRE_H, PRICE_POST_H, PSEUDO_GAP_H], "split": [SPLIT_HOLDOUT_FRAC, SPLIT_EMBARGO_D]},
    }


def declaration_sha256_h7() -> str:
    return _sha(declaration_h7())


# ---- text rules (weather exclusion reuses CB2's TEMP_RE; imported lazily, cb2_weather is not edited) -------------


def _cb2w():
    from . import cb2_weather  # noqa: PLC0415 - heavy (scipy); only the fetch/seal commands need it

    return cb2_weather


def is_weather_text(*texts: str | None) -> bool:
    w = _cb2w()
    rx = re.compile(w.TEMP_RE, w.TEMP_RE_FLAGS)
    return any(t and rx.match(str(t)) for t in texts)


def is_weather_market(fee_cat: str | None, *texts: str | None) -> bool:
    """Section 1.3: ``fee_category == 'weather'`` or a title matching CB2's ``TEMP_RE``."""
    return (fee_cat or "") == "weather" or is_weather_text(*texts)


def norm_label(s: Any) -> str:
    """Normalised label: lowercase, whitespace and punctuation collapsed to single spaces."""
    return re.sub(r"[^0-9a-z]+", " ", str(s or "").lower()).strip()


# ---- series rules (hashed and committed before q0082 reads any event title or groupItemTitle) --------------------


def cadence_class(end_epochs: list[float]) -> str | None:
    """Cadence from the median gap between consecutive member end dates only: daily [20h, 28h], weekly [6d, 8d],
    monthly [27d, 32d]; anything else (sub-daily, irregular, fewer than two members) is None."""
    xs = sorted(end_epochs)
    if len(xs) < 2:
        return None
    med = statistics.median([b - a for a, b in zip(xs, xs[1:], strict=False)])
    for name, (lo, hi) in CADENCE_BOUNDS.items():
        if lo <= med <= hi:
            return name
    return None


def horizon_for(cadence: str) -> tuple[float, float]:
    """(move window M hours, V_end hours) after t0."""
    h = HORIZONS[cadence]
    return h["M_h"], h["V_end_h"]


def pick_successor(members: list[dict], pred_idx: int, t0: float) -> tuple[int | None, bool]:
    """Successor of ``members[pred_idx]`` (members sorted by end): the member with the smallest end date greater
    than the predecessor's with ``created_epoch <= t0 - 1h``. Returns (index, skipped) where ``skipped`` is true
    when it is not the immediate next member."""
    pred_end = members[pred_idx]["end_epoch"]
    for j in range(pred_idx + 1, len(members)):
        m = members[j]
        if m["end_epoch"] > pred_end and m["created_epoch"] is not None and m["created_epoch"] <= t0 - SUCC_CREATED_LAG_H * HOUR:
            return j, j != pred_idx + 1
    return None, False


def _price_pair(prices: Any) -> list[float] | None:
    try:
        v = json.loads(prices) if isinstance(prices, str) else prices
        return [float(x) for x in v] if isinstance(v, list) and v else None
    except (ValueError, TypeError):
        return None


def winner_of(pred: dict, guarded: dict) -> tuple[str, float, str | None] | None:
    """(winner key, t0 epoch, winning outcome label or None) of a resolved predecessor event, or None.

    Single-market event: the outcome label whose price is >= 0.99 while the others are <= 0.01 (the key is the
    normalised label). Multi-market event: exactly one member whose first (Yes) price is >= 0.99 and no other
    above 0.01 (the key is the normalised ``groupItemTitle``). ``t0`` is that market's ``closedTime``. Anything
    else (50-50, void, not closed, no closed time) returns None."""
    gmk = {g["market_id"]: g for g in guarded.get("markets", [])}
    ms = pred["markets"]
    if len(ms) == 1:
        g = gmk.get(ms[0]["market_id"])
        pr = _price_pair(g.get("outcome_prices")) if g else None
        labels = ms[0].get("outcomes") or []
        if not g or not pr or len(pr) != len(labels) or not g.get("closed"):
            return None
        win = [i for i, p in enumerate(pr) if p >= WIN_PRICE]
        if len(win) != 1 or any(p > 1 - WIN_PRICE for i, p in enumerate(pr) if i != win[0]):
            return None
        t0 = _parse_ts(g.get("closed_time"))
        return (norm_label(labels[win[0]]), t0, labels[win[0]]) if t0 is not None else None
    wins = []
    for m in ms:
        g = gmk.get(m["market_id"])
        pr = _price_pair(g.get("outcome_prices")) if g else None
        if not g or not pr or not g.get("closed"):
            return None
        if pr[0] >= WIN_PRICE:
            wins.append((m, g))
        elif pr[0] > 1 - WIN_PRICE:
            return None
    if len(wins) != 1:
        return None
    t0 = _parse_ts(wins[0][1].get("closed_time"))
    return (norm_label(wins[0][0].get("group_title")), t0, None) if t0 is not None else None


def match_side(succ: dict, pred: dict, key: str) -> tuple[str, int] | None:
    """(market_id, token index) of the successor token that was rolled into, or None (unit excluded, counted).
    Binary-member events: the token with the same outcome label as the predecessor's winner. Multi-member events:
    token 0 (Yes) of the successor member whose normalised ``groupItemTitle`` equals the predecessor winner's."""
    if len(succ["markets"]) == 1 and len(pred["markets"]) == 1:
        m = succ["markets"][0]
        labs = [norm_label(x) for x in (m.get("outcomes") or [])]
        return (m["market_id"], labs.index(key)) if key in labs and len(labs) == 2 else None
    if len(succ["markets"]) > 1 and len(pred["markets"]) > 1:
        hits = [m for m in succ["markets"] if norm_label(m.get("group_title")) == key and key]
        return (hits[0]["market_id"], 0) if len(hits) == 1 else None
    return None


def winner_market(pred: dict, guarded: dict) -> tuple[str, int] | None:
    """(market_id, token index) of the predecessor's WINNING token: binary-member event -> its single market and the
    winning outcome index; multi-member event -> the winning member's Yes token (index 0). None as ``winner_of``."""
    w = winner_of(pred, guarded)
    if w is None:
        return None
    ms = pred["markets"]
    if len(ms) == 1:
        labels = [norm_label(x) for x in (ms[0].get("outcomes") or [])]
        return (ms[0]["market_id"], labels.index(w[0])) if w[0] in labels else None
    hits = [m for m in ms if norm_label(m.get("group_title")) == w[0]]
    return (hits[0]["market_id"], 0) if len(hits) == 1 else None


RULE_TEXT = (
    "CB4-S series rules (CREATIVE_BATCH_4.md CB4-S). Series are found from event listings (series on events, "
    "closed=false then true, end dates from the walk start to R_to + 2 d). Cadence from the median gap of member "
    "endDates only: daily [20h,28h], weekly [6d,8d], monthly [27d,32d], else excluded. Weather = fee_category weather "
    "or CB2 TEMP_RE on a title. Sports series = modal fee_category in the committed group-S decision. Series sample: "
    "square-root allocation over cadence x modal fee_category (hb.allocate), rank sha256(seed|series). Block: up to "
    "members-1 consecutive predecessors with endDate in [R_from, R_to], start sha256(seed|series|block) mod range. "
    "t0 = closedTime of the single winning market (price >= 0.99, others <= 0.01). Successor = smallest later "
    "endDate with createdAt <= t0 - 1h. Side: binary-member events by normalised outcome label; multi-member events "
    "by normalised groupItemTitle (exact), else the unit is excluded. Horizons: daily M=3h V_end=12h; weekly and "
    "monthly M=6h V_end=48h. Fetch window = union over origins t0 and t0_alt = endDate(pred)+1h of "
    "[o' - 3h, o + V_end + 2h] with o' = o - V_end - 6h, plus the winning predecessor token and one trade page "
    "around t0 for the publicity check. R_from = 2025-10-01 (earliest allowed roll time t0). R_to = "
    "min(T_fetch7 - 3 d, T_seal) - 2 d (latest allowed roll time t0; T_fetch7 = the series fetch's own clock, "
    "T_seal = the sealing time), so the event walk ends at R_to + 2 d.")


def series_roll_to(now_epoch: float, t_seal_epoch: float) -> float:
    """CREATIVE_BATCH_4.md R_to = min(T_fetch7 - 3 d, T_seal) - 2 d (epoch seconds); hashed in ``series_rules_doc``."""
    return min(now_epoch - SERIES_ROLL_TO_MARGIN_D * DAY, t_seal_epoch) - 2 * DAY


def series_rules_doc() -> dict:
    """Hash of the cadence bounds, horizons, constants and the SOURCE of every function that turns event text and
    outcome records into series, units, sides and windows (the rules are committed before any event text is read,
    CREATIVE_BATCH_4.md section 2.7; CB2 fix 1 standard) plus the readable rule text."""
    from astrolabe.research_panel import pairing  # noqa: PLC0415

    w = _cb2w()
    funcs = (cadence_class, horizon_for, pick_successor, winner_of, winner_market, match_side, norm_label, slim_event,
             assemble_units, _modal, _price_pair, _parse_ts, is_weather_text, is_weather_market, fetch_unit_series,
             union_window, pairing.fee_category, hb.allocate, hb._rank, _json_list, walk_series_events, _history_ids,
             _h5_ids, with_ladders_copy, series_roll_to)
    src = "\n".join(inspect.getsource(f) for f in funcs)
    consts = {"SUCC_CREATED_LAG_H": SUCC_CREATED_LAG_H, "PRICE_PRE_H": PRICE_PRE_H, "PRICE_POST_H": PRICE_POST_H,
              "PSEUDO_GAP_H": PSEUDO_GAP_H, "WIN_PRICE": WIN_PRICE, "SERIES_WINDOW_MIN_S": SERIES_WINDOW_MIN_S,
              "SERIES_WALK_BASE_DAYS": SERIES_WALK_BASE_DAYS, "SERIES_ROLL_FROM": SERIES_ROLL_FROM,
              "DAY": DAY, "SERIES_WALK_FROM": SERIES_WALK_FROM,
              "SERIES_ROLL_TO_MARGIN_D": SERIES_ROLL_TO_MARGIN_D, "SERIES_WALK_AFTER_D": SERIES_WALK_AFTER_D,
              "PRED_PRICE_H": PRED_PRICE_H, "PRED_TRADES": PRED_TRADES, "TEMP_RE": w.TEMP_RE, "TEMP_RE_FLAGS": w.TEMP_RE_FLAGS}
    return {"cadence_bounds_sha256": _sha(CADENCE_BOUNDS), "horizons_sha256": _sha(HORIZONS),
            "constants": consts, "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
            "rule_text": RULE_TEXT, "rule_text_sha256": hashlib.sha256(RULE_TEXT.encode()).hexdigest()}


def require_series_rules(path: Path = SERIES_RULES_FILE, *, require_committed: bool = True) -> None:
    path = Path(path)
    if not path.exists():
        raise Refused(f"series-rule file {path} not found; refusing to read series event text")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise Refused(f"series-rule file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise Refused(f"series-rule file {path} unreadable") from exc
    if doc != series_rules_doc():
        raise Refused(f"series-rule hash mismatch: file {doc} != code {series_rules_doc()}")


AMENDMENT_FILE = SEALS_DIR / "h7_cb4_group_s_amendment.json"
ERA_FRAME_TOKEN = "era_frame_complete"
SERIES_FRAME_TOKEN = "series_frame_complete"


def require_group_s_amendment(path: Path, kind: str, frame_report_path: Path, *, require_committed: bool = True
                              ) -> tuple[str, ...]:
    """The committed decision that defines group S (era) / the sports series stratum (series), made after the frame
    stage reported the fee-category counts per period (fix 8). Sampling refuses until the file exists, is committed,
    has ``decision`` in {as_declared, amended}, a non-empty ``sports_fee_categories`` list (``["sports"]`` exactly
    for ``as_declared``) and carries ``<kind>_frame_report_sha256`` equal to this run's ``frame_report.json`` hash.
    This session creates no amendment. Returns the sports fee categories."""
    path = Path(path)
    if not path.exists():
        raise Refused(f"group-S amendment {path} not found; sampling waits for a reviewed, committed decision "
                      f"(review {Path(frame_report_path).name} first)")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise Refused(f"group-S amendment {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise Refused(f"group-S amendment {path} unreadable") from exc
    cats = doc.get("sports_fee_categories")
    if doc.get("decision") not in ("as_declared", "amended") or not isinstance(cats, list) or not cats \
            or not all(isinstance(c, str) and c for c in cats):
        raise Refused("group-S amendment needs decision as_declared|amended and a non-empty sports_fee_categories list")
    if doc["decision"] == "as_declared" and cats != ["sports"]:
        raise Refused("decision as_declared requires sports_fee_categories == ['sports']")
    want = h5_seal.sha256_file(Path(frame_report_path))
    if doc.get(f"{kind}_frame_report_sha256") != want:
        raise Refused(f"group-S amendment does not match this {kind} frame report ({kind}_frame_report_sha256 != {want})")
    return tuple(cats)


def write_series_rules(path: Path = SERIES_RULES_FILE) -> Path:
    """Write the rule hashes (a Claude session commits the file before q0082 can run). Never overwrites a
    different file."""
    path = Path(path)
    data = json.dumps(series_rules_doc(), indent=1, sort_keys=True) + "\n"
    if path.exists() and json.loads(path.read_text()) != series_rules_doc():
        raise Refused(f"{path} exists with different content; a rule file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    return path


# ---- shared guards ---------------------------------------------------------------------------------------------


H5_LADDERS_SEAL_COPY = "h5_cb1_ladders_SEAL.json"


def with_ladders_copy(paths: list[Path]) -> list[Path]:
    """The h5 copy plus its sibling ``h5_cb1_ladders_SEAL.json`` (both are exclusion sets; fix 14)."""
    out = [Path(p) for p in paths]
    for p in list(out):
        if p.name == H5_SEAL_COPY and (p.with_name(H5_LADDERS_SEAL_COPY) not in out):
            out.append(p.with_name(H5_LADDERS_SEAL_COPY))
    return out


def require_h5_seal_copy(paths: list[Path], *, require_committed: bool = True) -> None:
    """Both fetches refuse until the committed ``seals/h5_cb1_SEAL.json`` and ``h5_cb1_ladders_SEAL.json`` exist
    (challenger item 11, fix 14)."""
    if not any(Path(p).name == H5_SEAL_COPY for p in paths):
        raise Refused(f"--exclude-seal-ids must include the committed {H5_SEAL_COPY}")
    for p in with_ladders_copy(paths):
        if not Path(p).exists():
            raise Refused(f"committed seal copy {p} is missing; run q0018 and commit it first")
        if require_committed:
            from . import cb1_history  # noqa: PLC0415

            if not cb1_history.spec_committed(Path(p)):
                raise Refused(f"seal copy {p} is not committed (or differs from HEAD)")


def require_data_dumps_room(data_dumps: Path, cap_gb: float = DATA_DUMPS_FETCH_CAP_GB) -> None:
    used = _cb2w().dir_size(Path(data_dumps)) / 1024**3
    if used > cap_gb:
        raise Refused(f"data-dumps is {used:.2f} GB (> {cap_gb} GB); refusing to start", code=EXIT_TEMPFAIL)


def _gz_jsonl_bytes(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for r in rows:
            gz.write((json.dumps(r, sort_keys=True, default=float) + "\n").encode())
    return buf.getvalue()


def _load_jsonl_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _frame_csv_bytes(header: list[str], rows: list[dict]) -> bytes:
    return hb._gz_csv_bytes(header, ([r.get(c, "") for c in header] for r in rows))


# ---- the resumable fetch session ---------------------------------------------------------------------------


class FetchRun:
    """One chunk of a resumable h7 fetch: limiter with 429 back-off and collector-health pause, disk budget,
    pinned request clock ``T_fetch7``, manifest writer, progress log and the stop checks (budget, T_seal,
    429 chunk limit, collector health). Mirrors ``cb2_weather.weather_fetch`` (imports its policy classes)."""

    def __init__(self, root: Path, run_id: str, transport: hb.Transport, *, kind: str, params: dict, rps: float,
                 disk_cap: int, budget_min: float | None, now: float | None, sleep: Callable[[float], None],
                 live_check: Callable[[], bool] | None, wall_clock: Callable[[], float], t_seal_epoch: float,
                 snapshot_root: Path | None, health_every_s: float, health_check: Callable[[float], tuple[bool, str]] | None,
                 cap_at: str, key: bytes | None):
        w = _cb2w()
        self.root, self.run_id, self.kind, self.params = Path(root), run_id, kind, params
        self.rdir = self.root / run_id
        self.wall_clock, self.t_seal_epoch = wall_clock, t_seal_epoch
        self.rdir.mkdir(parents=True, exist_ok=True)
        t = time.time() if now is None else now
        self.now = hb.pin_request_clock(self.rdir, t)  # one T_fetch7 across resumed chunks
        self.cap_epoch = min(self.now, _ep(cap_at), t_seal_epoch)
        self.t_start = time.time()
        self.budget_s = None if not budget_min else budget_min * 60.0
        self.budget = hb.DiskBudget(self.rdir, disk_cap)
        self.disk_cap = disk_cap
        self.pol = w.RatePolicy(transport, clock=wall_clock)
        self.lim = hb.Limiter(self.pol, rps=min(rps, 4.0), sleep=sleep, live_check=live_check)
        self.pol.limiter = self.lim
        self.rps = min(rps, 4.0)
        self.key = key if key is not None else hb.load_or_create_key()
        self.snapshot_root, self.health_every_s, self.health_check = snapshot_root, health_every_s, health_check
        self.last_health = -1e18
        self.mpath = self.rdir / "manifest.json"
        self.prior = json.loads(self.mpath.read_text()) if self.mpath.exists() else {}
        self.counts: dict[str, int] = {}
        self.budget_min = budget_min

    # -- stop checks
    def out_of_budget(self) -> bool:
        return self.budget_s is not None and time.time() - self.t_start >= self.budget_s

    def unhealthy(self) -> str | None:
        if self.health_check is None and self.snapshot_root is None:
            return None
        if self.wall_clock() - self.last_health < self.health_every_s:
            return None
        self.last_health = self.wall_clock()
        w = _cb2w()
        ok, why = self.health_check(self.wall_clock()) if self.health_check else w.collector_healthy(
            Path(self.snapshot_root), self.wall_clock())  # type: ignore[arg-type]
        return None if ok else f"paused_collector_health: {why}"

    def stop_reason(self, should_stop: Callable[[], bool] | None = None) -> str | None:
        if should_stop is not None and should_stop():
            return "should_stop"
        if self.out_of_budget():
            return "budget reached"
        if self.wall_clock() >= self.t_seal_epoch:
            return "t_seal_passed"
        if self.pol.over_limit:
            return "paused_429_chunk_limit"
        return self.unhealthy()

    # -- manifest
    def manifest(self, stopped: str | None, extra: dict | None = None) -> dict:
        m = {
            "provenance": hb.PROVENANCE, "evidence_role": hb.EVIDENCE_ROLE, "version": FETCH_VERSION,
            "run_id": self.run_id, "kind": self.kind,
            "purpose": "CB4 data (exploratory_historical); never prospective, not an edge claim",
            "git_commit": hb._git_commit(), "declaration_sha256": declaration_sha256_h7(),
            "params": {**self.params, "cap_utc": _iso(self.cap_epoch), "max_rps": self.rps,
                       "disk_cap_bytes": self.disk_cap, "budget_min": self.budget_min},
            "started_utc": self.prior.get("started_utc", _iso(self.t_start)), "updated_utc": _iso(time.time()),
            "request_clock_now": self.prior.get("request_clock_now", _iso(self.now)),
            "requests": {"total_this_session": self.lim.requests, "retries": self.lim.retries,
                         "http_429": self.pol.n429, "yielded_to_live_s": self.lim.yielded_s,
                         "rps_halved": self.pol.halved},
            "stopped": stopped, "disk_bytes": self.budget.scan(),
            "elapsed_s_this_session": round(time.time() - self.t_start, 1), "counts": dict(self.counts),
            **(extra or {}),
        }
        m.setdefault("complete", False)
        self.budget.cap += 10**7  # manifest bookkeeping must stay writable at the cap
        self.budget.write(self.mpath, json.dumps(m, indent=1, sort_keys=True, default=float).encode())
        return m

    # -- progress
    def read_progress(self, key_name: str) -> dict[str, dict]:
        done: dict[str, dict] = {}
        p = self.rdir / "progress.jsonl"
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    prev = done.get(rec[key_name])
                    if prev is not None and prev["status"] == "done":
                        continue
                    rec["attempts"] = (prev or {}).get("attempts", 0) + (rec["status"] != "done")
                    done[rec[key_name]] = rec
        return done

    def append_progress(self, rec: dict) -> None:
        with (self.rdir / "progress.jsonl").open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True, default=float) + "\n")


def mark_not_run(rdir: Path, run_id: str, reason: str, now: float | None = None) -> dict:
    """Record a run that was incomplete at T_seal: a marker file and ``stopped = not_run_deadline`` in the manifest.
    The run is never sealed, analysed or refetched; the cap is not moved."""
    rdir = Path(rdir)
    rdir.mkdir(parents=True, exist_ok=True)
    mp = rdir / "manifest.json"
    man = json.loads(mp.read_text()) if mp.exists() else {"run_id": run_id}
    man.update(stopped=NOT_RUN_TOKEN, complete=False, not_run_reason=reason, not_run_utc=_iso(time.time() if now is None else now))
    mp.write_text(json.dumps(man, indent=1, sort_keys=True, default=float))
    (rdir / NOT_RUN_FILE).write_text(json.dumps(
        {"run_id": run_id, "status": NOT_RUN_TOKEN, "reason": reason, "utc": man["not_run_utc"],
         "rule": "CREATIVE_BATCH_4.md 1.3: incomplete at T_seal -> not run, recorded; no seal, no analysis, no refetch; "
                 "dependent tests are recorded 'not run (deadline)' with p = 1"}, indent=1, sort_keys=True))
    return man


def _fetch_items(fr: FetchRun, items: list[dict], key_name: str, fetch_one: Callable[[dict], dict],
                 tally: Callable[[dict], None], should_stop: Callable[[], bool] | None, extra: dict,
                 *, checkpoint_every: int = 200) -> tuple[str | None, int]:
    """Fetch ``items`` in the given order, skipping finished ones; appends ``progress.jsonl``. Returns
    (stopped reason or None, number still pending)."""
    done = fr.read_progress(key_name)
    for rec in done.values():
        if rec["status"] == "done":
            tally(rec)
    stopped, since = None, 0
    for it in items:
        k = it[key_name]
        prev = done.get(k)
        if prev and (prev["status"] == "done" or prev.get("attempts", 0) >= MAX_ITEM_ATTEMPTS):
            continue
        why = fr.stop_reason(should_stop)
        if why:
            stopped = why
            break
        try:
            rec = fetch_one(it)
            rec["fetched_utc"] = _iso(time.time())
            tally(rec)
        except OSError as exc:
            stopped = f"disk_budget: {exc}"
            break
        except (RuntimeError, KeyError, TypeError, ValueError) as exc:
            rec = {key_name: k, "status": "failed", "error": str(exc)[:200], "fetched_utc": _iso(time.time())}
        fr.append_progress(rec)
        done[k] = {**rec, "attempts": (prev or {}).get("attempts", 0) + (rec["status"] != "done")}
        since += 1
        if since >= checkpoint_every:
            since = 0
            fr.manifest("in_progress", extra)
    pending = [it for it in items if not (done.get(it[key_name]) and (
        done[it[key_name]]["status"] == "done" or done[it[key_name]].get("attempts", 0) >= MAX_ITEM_ATTEMPTS))]
    fr.counts["items_failed"] = sum(1 for r in done.values() if r["status"] != "done")
    return stopped, len(pending)


def _guard_start(root: Path, run_id: str, wall_clock: Callable[[], float], t_seal_epoch: float, token: str) -> dict | None:
    """Common start gate. Returns a result dict when the call must not fetch, else None."""
    rdir = Path(root) / run_id
    if (rdir / h5_seal.SEAL_NAME).exists():
        raise Refused(f"{run_id} is sealed; the fetch never touches a sealed run")
    mp = rdir / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if (rdir / NOT_RUN_FILE).exists() or prior.get("stopped") == NOT_RUN_TOKEN:
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    if prior.get("complete") is True and prior.get("stopped") is None:
        return {"stopped": None, "status": token, "complete": True, "counts": prior.get("counts")}
    if wall_clock() >= t_seal_epoch:
        mark_not_run(rdir, run_id, "incomplete at T_seal (no new chunk at or after 2026-10-22T00:00Z)")
        return {"stopped": NOT_RUN_TOKEN, "status": NOT_RUN_TOKEN, "complete": False}
    return None


class ApiError(RuntimeError):
    """A request that did not return 200 (a failed request is a failed item, never an empty result; fix 9)."""


def fetch_prices_strict(lim: hb.Limiter, token: str, start: int, end: int) -> list[tuple[int, float]]:
    """Like ``hb.fetch_prices`` but a non-200 reply raises :class:`ApiError` (``hb.fetch_prices`` ignores it and
    would write an empty price file for a failed request). ``hb`` is not changed (h5 behaviour untouched)."""
    pts: dict[int, float] = {}
    a, step = start, hb.WINDOW_DAYS * 86400
    while a < end:
        b = min(a + step, end)
        status, data = lim.get(hb.CLOB_PRICES, {"market": token, "startTs": a, "endTs": b, "fidelity": hb.FIDELITY_MIN})
        if status != 200 or not isinstance(data, dict):
            raise ApiError(f"prices-history status {status}")
        for h in data.get("history") or []:
            pts[int(h["t"])] = float(h["p"])
        a = b
    return sorted(pts.items())


def fetch_trades_strict(lim: hb.Limiter, condition_id: str, key: bytes, max_trades: int, ts_cap: float | None = None
                        ) -> tuple[list[list], dict]:
    """Newest-first pages like ``hb.fetch_trades`` (wallets keyed-hashed, rows after ``ts_cap`` dropped and counted)
    but a non-200 page raises :class:`ApiError`; ``truncated`` means only that our own or the API's offset cap was hit."""
    rows: dict[str, list] = {}
    dropped, off, pages, truncated = 0, 0, 0, False
    cap = min(max_trades, hb.TRADE_OFFSET_CAP + hb.TRADE_PAGE)
    while off < cap:
        status, data = lim.get(hb.DATA_TRADES, {"market": condition_id, "limit": hb.TRADE_PAGE, "offset": off})
        pages += 1
        if status != 200 or not isinstance(data, list):
            raise ApiError(f"trades status {status} at offset {off}")
        for t in data:
            try:
                if ts_cap is not None and int(t["timestamp"]) > ts_cap:
                    dropped += 1
                    continue
                tk = hb.trade_key(t)
                rows[tk] = [int(t["timestamp"]), str(t["side"]), float(t["size"]), float(t["price"]), int(t["outcomeIndex"]),
                            hb.wallet_hash(key, str(t.get("proxyWallet", ""))), tk]
            except (KeyError, TypeError, ValueError):
                continue
        if len(data) < hb.TRADE_PAGE:
            break
        off += hb.TRADE_PAGE
    else:
        truncated = True
    out = sorted(rows.values(), key=lambda x: (x[0], x[6]))
    return out, {"pages": pages, "n": len(out), "truncated": truncated, "oldest_ts": out[0][0] if out else None,
                 "dropped_post_cap": dropped if ts_cap is not None else None}


def _fetch_prices_capped(lim: hb.Limiter, token: str, a: int, b: int, cap_epoch: float) -> tuple[list[tuple[int, float]], int]:
    pts = fetch_prices_strict(lim, token, a, b)
    keep = [(t, p) for t, p in pts if t < cap_epoch]
    return keep, len(pts) - len(keep)


# ---- CH53 era fetch (q0081) ------------------------------------------------------------------------------------


def parse_periods(spec: str | list | tuple) -> list[tuple[str, float, float]]:
    """``"2025-12-01/2026-02-18,..."`` -> ``[("P0", a_epoch, b_epoch), ...]`` (half-open, UTC)."""
    parts = _csv_list(spec) if isinstance(spec, str) else [f"{a}/{b}" for _n, a, b in spec]
    out = []
    for i, p in enumerate(parts):
        a, b = p.split("/")
        out.append((f"P{i}", _ep(a), _ep(b)))
    return out


def era_days(periods: list[tuple[str, float, float]]) -> list[date]:
    days: list[date] = []
    for _n, a, b in periods:
        t = a
        while t < b:
            days.append(datetime.fromtimestamp(t, UTC).date())
            t += DAY
    return days


def _main_row(r: dict) -> dict:
    """The non-outcome columns of a ``frame_row`` plus a text-derived weather flag (no text is stored)."""
    out = {c: r.get(c, "") for c in FRAME_MAIN_COLUMNS if c not in ("group", "period", "weather_title")}
    out["weather_title"] = int(is_weather_text(r.get("question"), r.get("event_title")))
    return out


def _outcome_row(r: dict) -> dict:
    return {"market_id": r["market_id"], **{c: r.get(c, "") for c in OUTCOME_FIELDS}}


def _paged_strict(lim: hb.Limiter, params: dict, max_rows: int) -> tuple[list[dict], bool, bool]:
    """(rows, capped, failed) of one /markets window by offset. A failed request is ``failed`` and is never read as
    "capped" (``hb._paged(error_is_capped=True)`` conflates them; fix 9)."""
    out: list[dict] = []
    off = 0
    while True:
        try:
            status, data = lim.get(hb.GAMMA_MARKETS, {**params, "limit": hb.GAMMA_PAGE, "offset": off})
        except RuntimeError:
            return out, False, True
        if status != 200 or not isinstance(data, list):
            return out, False, True
        out.extend(data)
        if len(data) < hb.GAMMA_PAGE:
            return out, False, False
        off += hb.GAMMA_PAGE
        if off >= max_rows:
            return out, True, False


MAX_DAY_ATTEMPTS = 3


def walk_era_frame(lim: hb.Limiter, days: list[date], seed: str, modes: tuple[bool, ...], *, rdir: Path,
                   should_stop: Callable[[], bool] | None = None, windows_per_day: int = FRAME_WINDOWS_PER_DAY,
                   window_minutes: int = FRAME_WINDOW_MINUTES, pages_per_window: int = FRAME_PAGES_PER_WINDOW,
                   ) -> tuple[list[dict], dict[str, dict], dict, str | None]:
    """The h2 frame method (``frame-v2-random-windows``) restricted to the period days: per day, ``windows_per_day``
    seeded ``window_minutes`` windows on ``end_date``, each walked with ``closed=false`` first, then ``closed=true``
    (a market that closes between the two walks is seen by the second), ``pages_per_window`` pages; a window still
    capped is dropped whole and counted as capped. A window with a FAILED request is counted separately
    (``windows_failed``); the day is not recorded and is retried by the next chunk, and only after
    ``MAX_DAY_ATTEMPTS`` failed attempts is it recorded with its failed windows counted. Resumable per day through
    ``frame_partial.jsonl`` (non-outcome columns) and ``frame_partial_guarded.jsonl`` (outcome columns).
    Returns (rows, outcomes, report, stopped)."""
    rows: dict[str, dict] = {}
    outs: dict[str, dict] = {}
    rep: dict = {"frame_version": hb.FRAME_VERSION, "windows_per_day": windows_per_day, "window_minutes": window_minutes,
                 "pages_per_window": pages_per_window, "modes": [bool(m) for m in modes], "days": len(days),
                 "windows": {"closed": 0, "active": 0}, "windows_dropped_capped": {"closed": 0, "active": 0},
                 "windows_failed": 0, "days_with_failed_windows": [], "rows_in_dropped_windows": 0,
                 "dropped_capped_by_day": {}, "raw": 0, "non_binary_or_invalid": 0, "duplicates": 0}
    pp, pg, pf = rdir / "frame_partial.jsonl", rdir / "frame_partial_guarded.jsonl", rdir / "frame_fail.jsonl"
    done_days: set[str] = set()
    fails: dict[str, int] = {}
    if pf.exists():
        for line in pf.read_text().splitlines():
            if line.strip():
                k = json.loads(line)["day"]
                fails[k] = fails.get(k, 0) + 1
    if pp.exists():
        guarded_by_day: dict[str, list] = {}
        if pg.exists():
            for line in pg.read_text().splitlines():
                if line.strip():
                    g = json.loads(line)
                    guarded_by_day[g["day"]] = g["outs"]
        for line in pp.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["day"] not in guarded_by_day:  # a day is complete only when both files hold it
                continue
            done_days.add(rec["day"])
            for r in rec["rows"]:
                rows[r["market_id"]] = r
            for o in guarded_by_day[rec["day"]]:
                outs[o["market_id"]] = o
            for k in ("closed", "active"):
                rep["windows"][k] += rec["windows"][k]
                rep["windows_dropped_capped"][k] += rec["dropped"][k]
            rep["rows_in_dropped_windows"] += rec["dropped_rows"]
            if any(rec["dropped"].values()):
                rep["dropped_capped_by_day"][rec["day"]] = rec["dropped"]
            if rec.get("failed_windows"):
                rep["windows_failed"] += rec["failed_windows"]
                rep["days_with_failed_windows"].append(rec["day"])
            rep["raw"] += rec["raw"]
            rep["non_binary_or_invalid"] += rec["invalid"]
            rep["duplicates"] += rec["dups"]
    slots = 1440 // window_minutes
    f = "%Y-%m-%dT%H:%M:%SZ"
    for day in days:
        dkey = f"{day:%Y-%m-%d}"
        if dkey in done_days:
            continue
        if should_stop is not None and should_stop():
            return list(rows.values()), outs, rep, "frame_paused"
        rng = random.Random(f"{seed}|{dkey}")
        picks = sorted(rng.sample(range(slots), min(windows_per_day, slots)))
        d0 = datetime(day.year, day.month, day.day, tzinfo=UTC)
        new_rows: list[dict] = []
        new_outs: list[dict] = []
        seen_day: set[str] = set()
        win = {"closed": 0, "active": 0}
        dropped = {"closed": 0, "active": 0}
        dropped_rows = raw = invalid = dups = failed_windows = 0
        for mode in sorted(set(modes), key=bool):  # closed=false first
            kind = "closed" if mode else "active"
            for k in picks:
                a = d0 + timedelta(minutes=k * window_minutes)
                b = a + timedelta(minutes=window_minutes)
                p = {"order": "id", "ascending": "true", "closed": "true" if mode else "false",
                     "end_date_min": a.strftime(f), "end_date_max": b.strftime(f)}
                batch, capped, failed = _paged_strict(lim, p, pages_per_window * hb.GAMMA_PAGE)
                if failed:
                    failed_windows += 1
                    continue
                win[kind] += 1
                if capped:
                    dropped[kind] += 1
                    dropped_rows += len(batch)
                    continue
                for m in batch:
                    raw += 1
                    r = hb.frame_row(m, with_text=True)
                    if r is None:
                        invalid += 1
                    elif r["market_id"] in rows or r["market_id"] in seen_day:
                        dups += 1
                    else:
                        seen_day.add(r["market_id"])
                        new_rows.append(_main_row(r))
                        new_outs.append(_outcome_row(r))
        if failed_windows and fails.get(dkey, 0) + 1 < MAX_DAY_ATTEMPTS:
            with pf.open("a") as fh:
                fh.write(json.dumps({"day": dkey, "failed_windows": failed_windows}) + "\n")
            return list(rows.values()), outs, rep, f"walk_failed_window: {dkey}"
        # outcomes first, rows last: a day counts as done only when both lines exist
        with pg.open("a") as fh:
            fh.write(json.dumps({"day": dkey, "outs": new_outs}, default=float) + "\n")
        with pp.open("a") as fh:
            fh.write(json.dumps({"day": dkey, "rows": new_rows, "windows": win, "dropped": dropped,
                                 "dropped_rows": dropped_rows, "raw": raw, "invalid": invalid, "dups": dups,
                                 "failed_windows": failed_windows}, default=float) + "\n")
        for r in new_rows:
            rows[r["market_id"]] = r
        for o in new_outs:
            outs[o["market_id"]] = o
        for k2 in ("closed", "active"):
            rep["windows"][k2] += win[k2]
            rep["windows_dropped_capped"][k2] += dropped[k2]
        rep["rows_in_dropped_windows"] += dropped_rows
        if any(dropped.values()):
            rep["dropped_capped_by_day"][dkey] = dropped
        if failed_windows:
            rep["windows_failed"] += failed_windows
            rep["days_with_failed_windows"].append(dkey)
        rep["raw"] += raw
        rep["non_binary_or_invalid"] += invalid
        rep["duplicates"] += dups
    return list(rows.values()), outs, rep, None


def era_period_of(end_epoch: float, periods: list[tuple[str, float, float]]) -> str | None:
    for n, a, b in periods:
        if a <= end_epoch < b:
            return n
    return None


def apply_era_rules(rows: list[dict], periods: list[tuple[str, float, float]], *, history_ids: set[str], h5_ids: set[str],
                    origin_h: float = ERA_ORIGIN_H, min_life_d: float = ERA_MIN_LIFE_D,
                    sports_cats: tuple[str, ...] | None = None) -> tuple[list[dict], dict]:
    """Frame rules (CB4-E), each counted, first rule that fires: ``no_end_date``, ``weather``,
    ``history_sample_overlap`` (h1/h2/h3), ``h5_overlap``, ``outside_periods``, ``life_unknown``,
    ``life_lt_min`` (``created_at <= endDate - 4d`` fails), ``origin_window_outside_period``
    (``[end - 72h, end)`` not entirely inside the period). Adds ``period``; ``group`` (S / O) only when
    ``sports_cats`` is given (the frame stage leaves it blank: the S definition is decided after the category counts
    per period are reviewed, fix 8). ``kept_by_period_category`` is the table that review reads."""
    counts = {"frame_in": len(rows), "no_end_date": 0, "weather": 0, "history_sample_overlap": 0, "h5_overlap": 0,
              "outside_periods": 0, "life_unknown": 0, "life_lt_min": 0, "origin_window_outside_period": 0, "kept": 0,
              "kept_by_cell": {}, "kept_by_period_category": {}}
    kept = []
    bounds = {n: (a, b) for n, a, b in periods}
    for r in sorted(rows, key=lambda x: x["market_id"]):
        end = r.get("end_epoch")
        if end in (None, "") or (isinstance(end, float) and math.isnan(end)):
            counts["no_end_date"] += 1
            continue
        end = float(end)
        if int(r.get("weather_title") or 0) or (r.get("fee_category") or "") == "weather":
            counts["weather"] += 1
            continue
        if r["market_id"] in history_ids:
            counts["history_sample_overlap"] += 1
            continue
        if r["market_id"] in h5_ids:
            counts["h5_overlap"] += 1
            continue
        p = era_period_of(end, periods)
        if p is None:
            counts["outside_periods"] += 1
            continue
        created = _parse_ts(r.get("created_at"))
        if created is None:
            counts["life_unknown"] += 1
            continue
        if created > end - min_life_d * DAY:
            counts["life_lt_min"] += 1
            continue
        if end - origin_h * HOUR < bounds[p][0]:
            counts["origin_window_outside_period"] += 1
            continue
        g = "" if sports_cats is None else ("S" if (r.get("fee_category") or "") in sports_cats else "O")
        kept.append({**r, "group": g, "period": p})
        counts["kept"] += 1
        pc = f"{p}|{r.get('fee_category') or ''}"
        counts["kept_by_period_category"][pc] = counts["kept_by_period_category"].get(pc, 0) + 1
        if g:
            counts["kept_by_cell"][f"{g}|{p}"] = counts["kept_by_cell"].get(f"{g}|{p}", 0) + 1
    return kept, counts


def draw_era_sample(frame: list[dict], per_cell: int, seed: str) -> tuple[list[dict], dict]:
    """Seeded square-root allocation over ``fee_category x creation month`` inside each group x period cell;
    ``per_cell`` markets per cell (all of a smaller cell). Within a stratum the order is sha256(seed|market_id)."""
    cells: dict[str, list[dict]] = {}
    for r in frame:
        cells.setdefault(f"{r['group']}|{r['period']}", []).append(r)
    out: list[dict] = []
    rep: dict = {"seed": seed, "per_cell": per_cell, "cells": {}}
    for cell in sorted(cells):
        strata: dict[str, list[dict]] = {}
        for r in cells[cell]:
            strata.setdefault(f"{r.get('fee_category') or 'unknown'}|{str(r.get('created_at') or '')[:7] or 'unknown'}", []).append(r)
        sizes = {k: len(v) for k, v in strata.items()}
        alloc = hb.allocate(sizes, per_cell)
        n = 0
        for k in sorted(strata):
            pick = sorted(strata[k], key=lambda r: hb._rank(seed, r["market_id"]))[: alloc[k]]
            for r in pick:
                out.append({**r, "stratum": f"{cell}|{k}", "stratum_size": sizes[k], "stratum_alloc": alloc[k],
                            "inclusion_prob": alloc[k] / sizes[k]})
            n += len(pick)
        rep["cells"][cell] = {"eligible": len(cells[cell]), "sampled": n, "shortfall": max(0, per_cell - n)}
    return out, rep


def fetch_era_market(lim: hb.Limiter, r: dict, key: bytes, rdir: Path, budget: hb.DiskBudget, *, cap_epoch: float,
                     max_trades: int = ERA_MAX_TRADES) -> dict:
    """Prices of the YES token over ``[end - 72h - 8d, end + 1d]`` (anchored on the scheduled ``endDate`` only, so
    coverage does not depend on how late the market closed) and trades newest first (<= ``max_trades``). Rows at or
    after ``cap_epoch`` are dropped and counted."""
    end = float(r["end_epoch"])
    a = int(end - ERA_ORIGIN_H * HOUR - ERA_PRICE_LOOKBACK_D * DAY)
    b = int(min(end + ERA_PRICE_LEAD_D * DAY, cap_epoch))
    mid = r["market_id"]
    pts, dropped = _fetch_prices_capped(lim, r["token0"], a, b, cap_epoch) if b > a else ([], 0)
    trades, tst = fetch_trades_strict(lim, r["condition_id"], key, max_trades, ts_cap=cap_epoch - 1)
    budget.write(Path(rdir) / "prices" / f"{mid}.csv.gz", hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in pts)))
    budget.write(Path(rdir) / "trades" / f"{mid}.csv.gz", hb._gz_csv_bytes(hb.TRADE_COLUMNS, trades))
    return {"market_id": mid, "status": "done", "price_points": len(pts), "dropped_price_rows_post_cap": dropped,
            "window": [a, b], "trades": tst["n"], "trades_truncated": bool(tst["truncated"]),
            "trades_oldest_ts": tst["oldest_ts"], "dropped_trades_post_cap": tst["dropped_post_cap"] or 0,
            "group": r["group"], "period": r["period"]}


def _tally_era(counts: dict[str, int]) -> Callable[[dict], None]:
    def tally(rec: dict) -> None:
        if rec["status"] != "done":
            return
        counts["items_done"] = counts.get("items_done", 0) + 1
        counts["price_rows"] = counts.get("price_rows", 0) + rec["price_points"]
        counts["price_rows_dropped_post_cap"] = counts.get("price_rows_dropped_post_cap", 0) + rec["dropped_price_rows_post_cap"]
        counts["trade_rows"] = counts.get("trade_rows", 0) + rec["trades"]
        counts["trade_rows_dropped_post_cap"] = counts.get("trade_rows_dropped_post_cap", 0) + rec["dropped_trades_post_cap"]
        counts["trades_truncated_markets"] = counts.get("trades_truncated_markets", 0) + int(rec["trades_truncated"])

    return tally


def _read_era_frame(path: Path) -> list[dict]:
    df = pd.read_csv(path, dtype={"market_id": str, "token0": str, "token1": str, "event_id": str}, keep_default_na=False)
    rows = df.to_dict("records")
    for r in rows:
        r["end_epoch"] = float(r["end_epoch"])
        r["weather_title"] = int(r["weather_title"] or 0)
    return rows


def era_fetch(
    root: Path, run_id: str, transport: hb.Transport, *, seed: str = ERA_SEED, per_cell: int = ERA_PER_CELL,
    periods: list[tuple[str, float, float]] | None = None, exclude_runs: list[str] | None = None,
    h5_seal_copies: list[Path] | None = None, walk_closed: tuple[bool, ...] = (True, False),
    cap_at: str = T_SEAL, rps: float = 4.0, disk_cap: int = int(0.20 * 1024**3), budget_min: float | None = None,
    max_trades: int = ERA_MAX_TRADES, key: bytes | None = None, now: float | None = None,
    sleep: Callable[[float], None] = time.sleep, live_check: Callable[[], bool] | None = hb.live_pass_or_lock,
    should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] = time.time,
    t_seal_epoch: float = T_SEAL_EPOCH, snapshot_root: Path | None = None, health_every_s: float = 600.0,
    health_check: Callable[[float], tuple[bool, str]] | None = None, pages_per_window: int = FRAME_PAGES_PER_WINDOW,
    windows_per_day: int = FRAME_WINDOWS_PER_DAY, window_minutes: int = FRAME_WINDOW_MINUTES,
    stage: str = "all", amendment_file: Path = AMENDMENT_FILE, require_committed: bool = True,
) -> dict:
    """Stage ``frame``: period days (seeded 15-minute windows) -> rules -> ``frame.csv.gz`` + ``frame_report.json``
    (fee-category counts per period) and STOP (status ``era_frame_complete``). Stage ``all``: the frame (if absent),
    then, once the committed group-S amendment matches the frame report (fix 8), the seeded sample (written once) and the
    per-market prices and trades. Refuses new chunks at or after ``t_seal_epoch`` (an incomplete run is then marked
    ``not_run_deadline``). Every price and trade row at or after ``min(T_fetch7, T_seal)`` is dropped and counted; a
    failed request fails the market (never an empty file). Outcome columns go only to ``outcomes_guarded.csv.gz``.
    Ends a chunk as transient on collector health or after 50 HTTP 429s."""
    root = Path(root)
    refuse_run_id(run_id, (ERA_RUN_ID,))
    early = _guard_start(root, run_id, wall_clock, t_seal_epoch, ERA_COMPLETE_TOKEN)
    if early is not None:
        return early
    periods = periods or parse_periods(ERA_PERIODS)
    hist = _history_ids(root, exclude_runs or [])  # a missing exclusion sample is a refusal, not a disk error
    fr = FetchRun(root, run_id, transport, kind="era", params={
        "seed": seed, "per_cell": per_cell, "periods": [[n, _iso(a), _iso(b)] for n, a, b in periods],
        "origin_window_h": ERA_ORIGIN_H, "min_life_d": ERA_MIN_LIFE_D, "exclude_runs": exclude_runs or [],
        "walk_closed": list(walk_closed), "max_trades": max_trades, "pages_per_window": pages_per_window,
        "windows_per_day": windows_per_day, "window_minutes": window_minutes, "stage": stage},
        rps=rps, disk_cap=disk_cap, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
        wall_clock=wall_clock, t_seal_epoch=t_seal_epoch, snapshot_root=snapshot_root, health_every_s=health_every_s,
        health_check=health_check, cap_at=cap_at, key=key)
    why = fr.unhealthy()
    if why:
        return fr.manifest(why, {"transient": True})
    rdir = fr.rdir
    fpath, frpath, spath = rdir / "frame.csv.gz", rdir / "frame_report.json", rdir / "sample.csv.gz"
    try:
        if not frpath.exists():
            h5 = _h5_ids(h5_seal_copies)
            why_stop: list[str] = []

            def walk_stop() -> bool:
                r = fr.stop_reason(should_stop)
                if r:
                    why_stop.append(r)
                return bool(r)

            rows, outs, walk_rep, stopped = walk_era_frame(
                fr.lim, era_days(periods), seed, walk_closed, rdir=rdir, pages_per_window=pages_per_window,
                windows_per_day=windows_per_day, window_minutes=window_minutes, should_stop=walk_stop)
            if stopped:
                transient = bool(why_stop and why_stop[-1].startswith("paused")) or stopped.startswith("walk_failed")
                return fr.manifest(why_stop[-1] if why_stop else stopped, {"transient": transient, "walk_report": walk_rep})
            eligible, rule_counts = apply_era_rules(rows, periods, history_ids=hist, h5_ids=h5)
            frame_rep = {**walk_rep, "rules": rule_counts, "history_ids": len(hist), "h5_ids": len(h5),
                         "n_eligible": len(eligible), "fee_category_counts_eligible": _count_by(eligible, "fee_category")}
            ids = {r["market_id"] for r in eligible}
            fr.budget.write(rdir / OUTCOME_FILE, _frame_csv_bytes(ERA_OUTCOME_COLUMNS, [outs[m] for m in sorted(ids) if m in outs]))
            fr.budget.write(fpath, _frame_csv_bytes(FRAME_MAIN_COLUMNS, eligible))
            fr.budget.write(frpath, json.dumps(frame_rep, indent=1, sort_keys=True, default=float).encode())  # last: marks the frame
            for tmp in (rdir / "frame_partial.jsonl", rdir / "frame_partial_guarded.jsonl", rdir / "frame_fail.jsonl"):
                tmp.unlink(missing_ok=True)
        frame_rep = json.loads(frpath.read_text())
        if stage == "frame":
            m = fr.manifest("frame_complete", {"frame_report": frame_rep, "frame_complete": True})
            m["status"] = ERA_FRAME_TOKEN
            return m
        if not spath.exists():
            cats = require_group_s_amendment(amendment_file, "era", frpath, require_committed=require_committed)
            frame = _read_era_frame(fpath)
            for r in frame:
                r["group"] = "S" if (r.get("fee_category") or "") in cats else "O"
            sample, samp_rep = draw_era_sample(frame, per_cell, seed)
            frame_rep = {**frame_rep, "sports_fee_categories": list(cats), "sample": samp_rep, "n_sample": len(sample)}
            fr.budget.write(rdir / "sample_report.json", json.dumps(frame_rep["sample"], indent=1, sort_keys=True, default=float).encode())
            hdr = [*FRAME_MAIN_COLUMNS, "stratum", "stratum_size", "stratum_alloc", "inclusion_prob"]
            fr.budget.write(spath, _frame_csv_bytes(hdr, sample))  # sample last: its presence marks the sample as drawn
    except Refused:
        raise
    except FileNotFoundError as exc:
        raise Refused(str(exc)) from exc
    except OSError as exc:
        return {"stopped": f"disk_budget: {exc}"}
    except RuntimeError as exc:  # a persistent API failure while walking: transient, the partial days are kept
        return fr.manifest(f"walk_failed: {exc}"[:200], {"transient": True})
    frame_rep = {**json.loads(frpath.read_text()), "sample": json.loads((rdir / "sample_report.json").read_text())}
    sample_rows = _read_era_frame(spath)
    extra = {"frame_report": frame_rep, "n_sample": len(sample_rows)}
    items = sorted(sample_rows, key=lambda r: hb._rank(seed, r["market_id"]))  # seeded-rank order
    stopped, pending = _fetch_items(
        fr, items, "market_id", lambda r: fetch_era_market(fr.lim, r, fr.key, rdir, fr.budget, cap_epoch=fr.cap_epoch,
                                                           max_trades=max_trades), _tally_era(fr.counts), should_stop, extra)
    if stopped is None and pending == 0:
        extra["complete"] = True
        m = fr.manifest(None, extra)
        m["status"] = ERA_COMPLETE_TOKEN
        return m
    return fr.manifest(stopped or "pending", {**extra, "transient": bool(stopped and stopped.startswith("paused"))})


def _history_ids(root: Path, runs: list[str]) -> set[str]:
    """Market ids of the excluded runs' samples. A missing sample is a REFUSAL (never a disk error; fix 10)."""
    for r in runs:
        sp = Path(root) / r / "sample.csv.gz"
        if not sp.exists():
            raise Refused(f"excluded run {r!r} has no {sp}; refusing (disjointness must never silently degrade)")
    return _cb2w().history_sample_ids(root, runs)


def _h5_ids(copies: list[Path] | None) -> set[str]:
    ids: set[str] = set()
    for p in copies or []:
        ids |= _cb2w().seal_ids_from_copy(Path(p))
    return ids


def _count_by(rows: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[str(r.get(key) or "")] = out.get(str(r.get(key) or ""), 0) + 1
    return dict(sorted(out.items()))


# ---- CH50 series fetch (q0082) -----------------------------------------------------------------------------------

GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
GAMMA_SERIES = "https://gamma-api.polymarket.com/series"
PROBE_DROP_KEYS = ("outcomePrices", "outcomes", "closed", "closedTime", "umaResolutionStatus", "umaResolutionStatuses",
                   "resolved", "winner", "resolvedBy", "resolutionSource")


def _json_list(v: Any) -> list:
    if isinstance(v, list):
        return v
    try:
        x = json.loads(v) if isinstance(v, str) else None
        return x if isinstance(x, list) else []
    except ValueError:
        return []


def slim_event(e: dict, mode: bool) -> tuple[dict, dict] | None:
    """(slim non-outcome event record, guarded outcome record) of a Gamma event, or None without an end date.
    The slim record keeps ids, end/creation times, series membership, per-market tokens, outcome LABELS,
    ``groupItemTitle`` and ``fee_category``; no text is stored (the weather flag is computed from it)."""
    end = _parse_ts(e.get("endDate"))
    ms = [m for m in (e.get("markets") or []) if isinstance(m, dict)]
    if end is None or not ms:
        return None
    markets, gmarkets = [], []
    for m in ms:
        toks = _json_list(m.get("clobTokenIds"))
        markets.append({
            "market_id": str(m.get("id")), "condition_id": m.get("conditionId"),
            "token0": str(toks[0]) if len(toks) > 0 else None, "token1": str(toks[1]) if len(toks) > 1 else None,
            "group_title": m.get("groupItemTitle"), "outcomes": [str(x) for x in _json_list(m.get("outcomes"))],
            "created_epoch": _parse_ts(m.get("createdAt")), "fee_category": hb.fee_category(m.get("feeType")),
            "neg_risk": int(bool(m.get("negRisk")))})
        gmarkets.append({"market_id": str(m.get("id")), "outcome_prices": m.get("outcomePrices"),
                         "closed": bool(m.get("closed")), "closed_time": m.get("closedTime") or ""})
    created = _parse_ts(e.get("createdAt"))
    if created is None:
        cs = [x["created_epoch"] for x in markets if x["created_epoch"] is not None]
        created = min(cs) if cs else None
    series = [{"id": str(s.get("id")), "slug": s.get("slug")} for s in (e.get("series") or []) if isinstance(s, dict) and s.get("id") is not None]
    slim = {"event_id": str(e.get("id")), "end_epoch": end, "created_epoch": created, "series": series,
            "weather_title": int(is_weather_text(e.get("title"), *[m.get("question") for m in ms])),
            "n_markets": len(markets), "markets": markets, "closed_mode": bool(mode)}
    return slim, {"event_id": slim["event_id"], "event_closed": bool(e.get("closed")), "markets": gmarkets}


def walk_series_events(lim: hb.Limiter, start: float, end: float, modes: tuple[bool, ...], *, rdir: Path,
                       should_stop: Callable[[], bool] | None = None, base_days: int = SERIES_WALK_BASE_DAYS,
                       min_width_s: int = SERIES_WINDOW_MIN_S) -> tuple[dict[str, dict], dict[str, dict], dict, str | None]:
    """Walk Gamma ``/events`` over ``end_date`` windows for each ``closed`` mode (false first), keep only events that
    belong to a series. A window that reaches the offset cap is halved (down to ``min_width_s``); one still capped
    at that width is dropped and counted. Resumable per base window of ``base_days`` days through
    ``walk_partial.jsonl`` (slim non-outcome records) and ``walk_partial_guarded.jsonl`` (outcome records); a base
    window with a failed request is not recorded and is retried by the next chunk (recorded as failed after 3)."""
    events: dict[str, dict] = {}
    guarded: dict[str, dict] = {}
    rep: dict = {"modes": [bool(m) for m in modes], "base_windows": 0, "requests": 0, "splits": 0, "windows_dropped_capped": 0,
                 "rows_in_dropped_windows": 0, "events_seen": 0, "events_no_series": 0, "events_no_end_or_markets": 0,
                 "events_kept": 0, "base_windows_failed": 0, "failed_windows": []}
    pp, pg = rdir / "walk_partial.jsonl", rdir / "walk_partial_guarded.jsonl"
    done: set[tuple[bool, str]] = set()
    fails: dict[tuple[bool, str], int] = {}
    gby: dict[tuple[bool, str], list] = {}
    if pg.exists():
        for line in pg.read_text().splitlines():
            if line.strip():
                g = json.loads(line)
                gby[(g["mode"], g["a"])] = g["guarded"]
    if pp.exists():
        for line in pp.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            k = (rec["mode"], rec["a"])
            if rec.get("fail"):
                fails[k] = fails.get(k, 0) + 1
                continue
            if k not in gby:
                continue
            done.add(k)
            for ev in rec["events"]:
                events.setdefault(ev["event_id"], ev)
            for g in gby[k]:
                guarded.setdefault(g["event_id"], g)
            for f in ("requests", "splits", "windows_dropped_capped", "rows_in_dropped_windows", "events_seen",
                      "events_no_series", "events_no_end_or_markets"):
                rep[f] += rec["rep"].get(f, 0)
            rep["base_windows"] += 1
    for mode in sorted(set(modes), key=bool):  # closed=false BEFORE closed=true
        t = start
        while t < end:
            a, b = t, min(t + base_days * DAY, end)
            t += base_days * DAY
            k = (bool(mode), _iso(a))
            if k in done:
                continue
            if fails.get(k, 0) >= 3:
                rep["base_windows_failed"] += 1
                rep["failed_windows"].append([bool(mode), _iso(a), _iso(b)])
                done.add(k)
                continue
            if should_stop is not None and should_stop():
                return events, guarded, rep, "walk_paused"
            wrep = {"requests": 0, "splits": 0, "windows_dropped_capped": 0, "rows_in_dropped_windows": 0, "events_seen": 0,
                    "events_no_series": 0, "events_no_end_or_markets": 0}
            new_slim: list[dict] = []
            new_g: list[dict] = []
            stack = [(a, b)]
            failed = False
            while stack:
                x, y = stack.pop(0)
                rows: list[dict] = []
                capped, off = False, 0
                while True:
                    try:
                        status, data = lim.get(GAMMA_EVENTS, {"closed": "true" if mode else "false", "end_date_min": _iso(x),
                                                               "end_date_max": _iso(y), "limit": 100, "offset": off})
                    except RuntimeError:
                        status, data = 599, None
                    wrep["requests"] += 1
                    if status != 200 or not isinstance(data, list):
                        failed = True
                        break
                    rows.extend(data)
                    if len(data) < 100:
                        break
                    off += 100
                    if off >= hb.GAMMA_OFFSET_CAP:
                        capped = True
                        break
                if failed:
                    break
                if capped and (y - x) > min_width_s:
                    mid = x + math.floor((y - x) / 2)
                    stack[:0] = [(x, mid), (mid, y)]
                    wrep["splits"] += 1
                    continue
                if capped:
                    wrep["windows_dropped_capped"] += 1
                    wrep["rows_in_dropped_windows"] += len(rows)
                    continue
                for e in rows:
                    wrep["events_seen"] += 1
                    if not e.get("series"):
                        wrep["events_no_series"] += 1
                        continue
                    sg = slim_event(e, mode)
                    if sg is None:
                        wrep["events_no_end_or_markets"] += 1
                        continue
                    new_slim.append(sg[0])
                    new_g.append(sg[1])
            if failed:
                with pp.open("a") as fh:
                    fh.write(json.dumps({"mode": bool(mode), "a": _iso(a), "fail": True}) + "\n")
                rep["requests"] += wrep["requests"]
                return events, guarded, rep, f"walk_failed_window: closed={mode} {_iso(a)}"
            # dedupe within the window, then record guarded first and slim last (slim marks the window done)
            seen_e: set[str] = set()
            uslim = [s for s in new_slim if not (s["event_id"] in seen_e or seen_e.add(s["event_id"]))]
            ug = [g for g in new_g if g["event_id"] in seen_e]
            with pg.open("a") as fh:
                fh.write(json.dumps({"mode": bool(mode), "a": _iso(a), "guarded": ug}, default=float) + "\n")
            with pp.open("a") as fh:
                fh.write(json.dumps({"mode": bool(mode), "a": _iso(a), "events": uslim, "rep": wrep}, default=float) + "\n")
            for s in uslim:
                events.setdefault(s["event_id"], s)
            for g in ug:
                guarded.setdefault(g["event_id"], g)
            for f in wrep:
                rep[f] += wrep[f]
            rep["base_windows"] += 1
            done.add(k)
    rep["events_kept"] = len(events)
    return events, guarded, rep, None


def probe_series_endpoint(lim: hb.Limiter) -> dict:
    """Facts about ``GET /series`` (usable or not). Outcome-like fields are dropped by guard at parse time and never
    written. The walk itself always goes through the event listings, so the probe changes no data."""
    try:
        status, data = lim.get(GAMMA_SERIES, {"limit": 3})
    except RuntimeError as exc:
        return {"endpoint": GAMMA_SERIES, "error": str(exc)[:200], "usable": False}
    keys: list[str] = []
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = sorted(k for k in data[0] if k not in PROBE_DROP_KEYS)
    return {"endpoint": GAMMA_SERIES, "status": status, "is_list": isinstance(data, list),
            "n": len(data) if isinstance(data, list) else None, "item_keys_without_outcome_fields": keys,
            "dropped_by_guard": list(PROBE_DROP_KEYS), "usable": bool(status == 200 and isinstance(data, list) and data and "id" in keys)}


def _modal(vals: list[str]) -> str:
    c: dict[str, int] = {}
    for v in vals:
        c[v] = c.get(v, 0) + 1
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if c else "unknown"


def assemble_units(events: dict[str, dict], guarded: dict[str, dict], *, seed: str, n_series: int, n_sports: int,
                   members: int, r_from: float, r_to: float, history_ids: set[str], h5_ids: set[str],
                   sports_cats: tuple[str, ...] = ("sports",)) -> dict:
    """Series table, seeded series sample, 31-member blocks and roll units (CB4-S population), every exclusion counted.
    Selection of series and blocks uses end dates, fee categories and series ids only (no outcome). ``t0`` and the
    rolled-into side come from the predecessor's outcome record and are returned in ``outcome_rows`` (guarded)."""
    by_series: dict[str, list[dict]] = {}
    sinfo: dict[str, dict] = {}
    for ev in events.values():
        for s in ev["series"]:
            by_series.setdefault(s["id"], []).append(ev)
            sinfo.setdefault(s["id"], {"slug": s.get("slug")})
    rep: dict = {"series_total": len(by_series), "series_cadence_excluded": 0, "series_weather_excluded": 0,
                 "series_lt_2_members": 0, "series_eligible": 0, "series_sampled_non_sports": 0, "series_sampled_sports": 0,
                 "units_candidate": 0, "unit_drops": {}, "units": 0, "units_succ_skipped": 0}

    def drop(reason: str) -> None:
        rep["unit_drops"][reason] = rep["unit_drops"].get(reason, 0) + 1

    table: dict[str, dict] = {}
    for sid, evs in by_series.items():
        ms = sorted({e["event_id"]: e for e in evs}.values(), key=lambda e: (e["end_epoch"], e["event_id"]))
        modal = _modal([m["fee_category"] for e in ms for m in e["markets"]])
        if len(ms) < 2:
            rep["series_lt_2_members"] += 1
            continue
        if modal == "weather" or any(e["weather_title"] for e in ms):
            rep["series_weather_excluded"] += 1
            continue
        cad = cadence_class([e["end_epoch"] for e in ms])
        if cad is None:
            rep["series_cadence_excluded"] += 1
            continue
        table[sid] = {"series_id": sid, "slug": sinfo[sid]["slug"], "cadence": cad, "modal_fee_category": modal,
                      "sports": modal in sports_cats, "n_members": len(ms), "members": ms}
    rep["series_eligible"] = len(table)
    non_sports = {k: v for k, v in table.items() if not v["sports"]}
    sports = {k: v for k, v in table.items() if v["sports"]}
    strata: dict[str, list[str]] = {}
    for sid, v in non_sports.items():
        strata.setdefault(f"{v['cadence']}|{v['modal_fee_category']}", []).append(sid)
    alloc = hb.allocate({k: len(v) for k, v in strata.items()}, n_series)
    chosen: list[str] = []
    for k in sorted(strata):
        chosen += sorted(strata[k], key=lambda s: hb._rank(seed, s))[: alloc[k]]
    sports_chosen = sorted(sports, key=lambda s: hb._rank(seed, s))[:n_sports]
    rep["series_sampled_non_sports"], rep["series_sampled_sports"] = len(chosen), len(sports_chosen)
    rep["series_strata"] = {k: {"size": len(v), "alloc": alloc[k]} for k, v in sorted(strata.items())}

    def excluded(ev: dict) -> str | None:
        if ev["weather_title"] or any(m["fee_category"] == "weather" for m in ev["markets"]):
            return "weather"
        mids = {m["market_id"] for m in ev["markets"]}
        if mids & history_ids:
            return "history_sample_overlap"
        if mids & h5_ids:
            return "h5_overlap"
        return None

    series_rows, units, outcome_rows = [], [], []
    for sid in sorted(chosen + sports_chosen):
        v = table[sid]
        ms = v["members"]
        cand = [i for i in range(len(ms) - 1) if r_from <= ms[i]["end_epoch"] <= r_to]
        if len(cand) > members - 1:
            start = int(hashlib.sha256(f"{seed}|{sid}|block".encode()).hexdigest(), 16) % (len(cand) - (members - 1) + 1)
            cand = cand[start: start + members - 1]
        series_rows.append({k: v[k] for k in ("series_id", "slug", "cadence", "modal_fee_category", "sports", "n_members")}
                           | {"n_pred_candidates": len(cand), "stratum": f"{v['cadence']}|{v['modal_fee_category']}"})
        for i in cand:
            pred = ms[i]
            rep["units_candidate"] += 1
            ex = excluded(pred)
            if ex:
                drop(f"excluded_event_{ex}")
                continue
            w = winner_of(pred, guarded.get(pred["event_id"], {}))
            if w is None:
                drop("no_single_winner_or_t0")
                continue
            key, t0, _label = w
            if not (r_from <= t0 <= r_to):
                drop("t0_outside_range")
                continue
            j, skipped = pick_successor(ms, i, t0)
            if j is None:
                drop("no_successor")
                continue
            succ = ms[j]
            ex = excluded(succ)
            if ex:
                drop(f"excluded_event_{ex}")
                continue
            m_h, v_h = horizon_for(v["cadence"])
            if succ["end_epoch"] < t0 + v_h * HOUR + 2 * HOUR:
                drop("succ_short_life")
                continue
            side = match_side(succ, pred, key)
            if side is None:
                drop("no_side_match")
                continue
            wm = winner_market(pred, guarded[pred["event_id"]])
            if wm is None:
                drop("no_winner_market")
                continue
            uid = f"{sid}:{pred['event_id']}:{succ['event_id']}"
            units.append({
                "unit_id": uid, "series_id": sid, "series_slug": v["slug"], "cadence": v["cadence"],
                "modal_fee_category": v["modal_fee_category"], "sports": v["sports"], "pred_event_id": pred["event_id"],
                "succ_event_id": succ["event_id"], "pred_end_epoch": pred["end_epoch"], "succ_end_epoch": succ["end_epoch"],
                "t0_epoch": t0, "t0_date": datetime.fromtimestamp(t0, UTC).date().isoformat(),
                "succ_created_epoch": succ["created_epoch"], "succ_skipped": skipped, "M_h": m_h, "V_end_h": v_h,
                "pred_market_ids": [m["market_id"] for m in pred["markets"]],
                "pred_markets": [{k: m[k] for k in ("market_id", "condition_id", "token0", "token1")} for m in pred["markets"]],
                "succ_markets": [{k: m[k] for k in ("market_id", "condition_id", "token0", "token1")} for m in succ["markets"]]})
            outcome_rows.append({
                "unit_id": uid, "pred_event_id": pred["event_id"], "pred_winner_key": key,
                "pred_closed_time": next((g["closed_time"] for g in guarded[pred["event_id"]]["markets"] if g["closed_time"]), ""),
                "pred_outcome_prices": json.dumps([g["outcome_prices"] for g in guarded[pred["event_id"]]["markets"]]),
                "side_market_id": side[0], "side_token_index": side[1],
                "pred_market_id": wm[0], "pred_token_index": wm[1]})
            rep["units"] += 1
            rep["units_succ_skipped"] += int(skipped)
    # events shared by units of more than one series are counted (dependence between series)
    users: dict[str, set[str]] = {}
    for u in units:
        for ev in (u["pred_event_id"], u["succ_event_id"]):
            users.setdefault(ev, set()).add(u["series_id"])
    rep["events_shared_across_series"] = sum(1 for v in users.values() if len(v) > 1)
    rep["units_in_shared_events"] = sum(1 for u in units if len(users[u["pred_event_id"]]) > 1 or len(users[u["succ_event_id"]]) > 1)
    return {"series": series_rows, "units": units, "outcomes": outcome_rows, "report": rep}


def union_window(t0: float, t0_alt: float, v_end_h: float) -> tuple[int, int, list[tuple[float, float]]]:
    """Union of the required price windows ``[o' - 3h, o + V_end + 2h]`` (``o' = o - V_end - 6h``, the pseudo-roll
    origin) over the two origins ``t0`` and ``t0_alt = endDate(pred) + 1h`` (section 2.2 coverage invariance)."""
    spans = []
    for o in (t0, t0_alt):
        v = o + v_end_h * HOUR
        spans.append((o - (v - o) - PSEUDO_GAP_H * HOUR - PRICE_PRE_H * HOUR, v + PRICE_POST_H * HOUR))
    return int(min(a for a, _ in spans)), int(max(b for _, b in spans)), spans


def fetch_unit_series(lim: hb.Limiter, unit: dict, side: dict, key: bytes, rdir: Path, budget: hb.DiskBudget, *,
                      cap_epoch: float, max_trades: int = ERA_MAX_TRADES) -> dict:
    """Successor prices of the rolled-into token over the union window of both origins and the side market's trades
    (newest first, <= ``max_trades``), plus the winning predecessor token's prices ``[t0 - 3h, t0 + 3h]`` and one
    trade page of the predecessor market (for the pre-freeze ``t0`` publicity check). Rows at or after ``cap_epoch``
    are dropped and counted; ``covers_t0`` / ``covers_alt`` assert that each origin's required window is inside
    what was fetched (a window cut by the cap is reported, never silently accepted)."""
    t0 = float(unit["t0_epoch"])
    t0_alt = float(unit["pred_end_epoch"]) + HOUR
    a, b0, spans = union_window(t0, t0_alt, float(unit["V_end_h"]))
    b = int(min(b0, cap_epoch))
    mk = next(m for m in unit["succ_markets"] if m["market_id"] == str(side["side_market_id"]))
    token = mk["token1"] if int(side["side_token_index"]) == 1 else mk["token0"]
    name = f"{mk['market_id']}__{unit['pred_event_id']}"
    pts, dropped = _fetch_prices_capped(lim, token, a, b, cap_epoch) if b > a else ([], 0)
    trades, tst = fetch_trades_strict(lim, mk["condition_id"], key, max_trades, ts_cap=cap_epoch - 1)
    budget.write(Path(rdir) / "prices" / f"{name}.csv.gz", hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in pts)))
    budget.write(Path(rdir) / "trades" / f"{name}.csv.gz", hb._gz_csv_bytes(hb.TRADE_COLUMNS, trades))
    pm = next(m for m in unit["pred_markets"] if m["market_id"] == str(side["pred_market_id"]))
    ptoken = pm["token1"] if int(side["pred_token_index"]) == 1 else pm["token0"]
    pa, pb = int(t0 - PRED_PRICE_H * HOUR), int(min(t0 + PRED_PRICE_H * HOUR, cap_epoch))
    ppts, pdropped = _fetch_prices_capped(lim, ptoken, pa, pb, cap_epoch) if pb > pa else ([], 0)
    ptr, ptst = fetch_trades_strict(lim, pm["condition_id"], key, PRED_TRADES, ts_cap=cap_epoch - 1)
    pname = f"{pm['market_id']}__{unit['pred_event_id']}"
    budget.write(Path(rdir) / "pred_prices" / f"{pname}.csv.gz", hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in ppts)))
    budget.write(Path(rdir) / "pred_trades" / f"{pname}.csv.gz", hb._gz_csv_bytes(hb.TRADE_COLUMNS, ptr))
    return {"unit_id": unit["unit_id"], "status": "done", "file": name, "pred_file": pname, "window": [a, b],
            "required_spans": [[int(x), int(y)] for x, y in spans],
            "covers_t0": bool(a <= spans[0][0] and b >= spans[0][1]), "covers_alt": bool(a <= spans[1][0] and b >= spans[1][1]),
            "price_points": len(pts), "dropped_price_rows_post_cap": dropped, "trades": tst["n"],
            "trades_truncated": bool(tst["truncated"]), "trades_oldest_ts": tst["oldest_ts"],
            "dropped_trades_post_cap": tst["dropped_post_cap"] or 0, "cadence": unit["cadence"],
            "pred": {"price_points": len(ppts), "dropped_price_rows_post_cap": pdropped, "trades": ptst["n"],
                     "trades_truncated": bool(ptst["truncated"]), "window": [pa, pb]}}


def series_frame_counts(events: dict[str, dict]) -> dict:
    """Series by cadence x modal fee_category (end dates and fee categories only), read by the group-S review."""
    by: dict[str, list[dict]] = {}
    for ev in events.values():
        for sr in ev["series"]:
            by.setdefault(sr["id"], []).append(ev)
    cells: dict[str, int] = {}
    n = 0
    for evs in by.values():
        ms = sorted({e["event_id"]: e for e in evs}.values(), key=lambda e: (e["end_epoch"], e["event_id"]))
        if len(ms) < 2:
            continue
        cad = cadence_class([e["end_epoch"] for e in ms]) or "other"
        modal = _modal([m["fee_category"] for e in ms for m in e["markets"]])
        cells[f"{cad}|{modal}"] = cells.get(f"{cad}|{modal}", 0) + 1
        n += 1
    return {"series_ge_2_members": n, "series_by_cadence_category": dict(sorted(cells.items()))}


def series_fetch(
    root: Path, run_id: str, transport: hb.Transport, *, seed: str = SERIES_SEED, n_series: int = SERIES_N,
    n_sports: int = SERIES_N_SPORTS, members: int = SERIES_MEMBERS, roll_from: str = SERIES_ROLL_FROM,
    walk_from: str = SERIES_WALK_FROM, exclude_runs: list[str] | None = None, h5_seal_copies: list[Path] | None = None,
    walk_closed: tuple[bool, ...] = (True, False), cap_at: str = T_SEAL, rps: float = 4.0,
    disk_cap: int = int(0.40 * 1024**3), budget_min: float | None = None, max_trades: int = ERA_MAX_TRADES,
    key: bytes | None = None, now: float | None = None, sleep: Callable[[float], None] = time.sleep,
    live_check: Callable[[], bool] | None = hb.live_pass_or_lock, should_stop: Callable[[], bool] | None = None,
    wall_clock: Callable[[], float] = time.time, t_seal_epoch: float = T_SEAL_EPOCH, snapshot_root: Path | None = None,
    health_every_s: float = 600.0, health_check: Callable[[float], tuple[bool, str]] | None = None,
    walk_base_days: int = SERIES_WALK_BASE_DAYS, min_width_s: int = SERIES_WINDOW_MIN_S,
    stage: str = "all", amendment_file: Path = AMENDMENT_FILE, require_committed: bool = True,
) -> dict:
    """Stage ``frame``: probe -> event walk (series events only) -> ``walk_events.jsonl.gz`` + ``frame_report.json``
    (series by cadence x modal fee category) and STOP (``series_frame_complete``). Stage ``all``: the frame (if absent),
    then, once the committed group-S amendment matches the frame report, the series table, seeded sample, blocks and
    roll units (written once), then per-unit successor prices and trades (union window of both origins) plus the
    winning predecessor's prices and one trade page. Same stop rules, cap, failed-request and outcome-guard rules as
    :func:`era_fetch`."""
    root = Path(root)
    refuse_run_id(run_id, (SERIES_RUN_ID,))
    early = _guard_start(root, run_id, wall_clock, t_seal_epoch, SERIES_COMPLETE_TOKEN)
    if early is not None:
        return early
    hist = _history_ids(root, exclude_runs or [])
    fr = FetchRun(root, run_id, transport, kind="series", params={
        "seed": seed, "n_series": n_series, "n_sports": n_sports, "members": members, "roll_from": roll_from,
        "walk_from": walk_from, "exclude_runs": exclude_runs or [], "walk_closed": list(walk_closed),
        "max_trades": max_trades, "series_rules": series_rules_doc(), "stage": stage},
        rps=rps, disk_cap=disk_cap, budget_min=budget_min, now=now, sleep=sleep, live_check=live_check,
        wall_clock=wall_clock, t_seal_epoch=t_seal_epoch, snapshot_root=snapshot_root, health_every_s=health_every_s,
        health_check=health_check, cap_at=cap_at, key=key)
    why = fr.unhealthy()
    if why:
        return fr.manifest(why, {"transient": True})
    rdir = fr.rdir
    upath, frpath = rdir / "units.jsonl.gz", rdir / "frame_report.json"
    wpath, wgpath = rdir / "walk_events.jsonl.gz", rdir / "walk_guarded.jsonl.gz"
    r_from = _ep(roll_from)
    r_to = series_roll_to(fr.now, t_seal_epoch)
    try:
        if not frpath.exists():
            if not (rdir / "probe.json").exists():
                fr.budget.write(rdir / "probe.json", json.dumps(probe_series_endpoint(fr.lim), indent=1, sort_keys=True).encode())
            why_stop: list[str] = []

            def walk_stop() -> bool:
                r = fr.stop_reason(should_stop)
                if r:
                    why_stop.append(r)
                return bool(r)

            # memory-bounded walk (cb4_walk_lean): same rules/partial format/result as the pinned walk_series_events
            from .cb4_walk_lean import walk_series_events_lean  # noqa: PLC0415

            store, walk_rep, stopped = walk_series_events_lean(
                fr.lim, _ep(walk_from), r_to + SERIES_WALK_AFTER_D * DAY, walk_closed, rdir=rdir,
                should_stop=walk_stop, base_days=walk_base_days, min_width_s=min_width_s)
            if stopped:
                return fr.manifest(why_stop[-1] if why_stop else stopped,
                                   {"transient": bool(why_stop and why_stop[-1].startswith("paused")) or stopped.startswith("walk_failed"),
                                    "walk_report": walk_rep})
            if walk_rep["base_windows_failed"]:  # an incomplete frame is never written (and so never sampled)
                return fr.manifest(f"walk_failed_windows: {walk_rep['base_windows_failed']}", {"transient": False, "walk_report": walk_rep})
            frame_rep = {"walk": walk_rep, **store.frame_counts(), "r_from": _iso(r_from), "r_to": _iso(r_to),
                         "walk_to": _iso(r_to + SERIES_WALK_AFTER_D * DAY)}
            store.write_guarded(fr.budget, wgpath)
            store.write_events(fr.budget, wpath)
            fr.budget.write(frpath, json.dumps(frame_rep, indent=1, sort_keys=True, default=float).encode())  # last: marks the frame
            del store
            for tmp in (rdir / "walk_partial.jsonl", rdir / "walk_partial_guarded.jsonl"):
                tmp.unlink(missing_ok=True)
        frame_rep = json.loads(frpath.read_text())
        if stage == "frame":
            m = fr.manifest("frame_complete", {"frame_report": frame_rep, "frame_complete": True})
            m["status"] = SERIES_FRAME_TOKEN
            return m
        if not upath.exists():
            cats = require_group_s_amendment(amendment_file, "series", frpath, require_committed=require_committed)
            h5 = _h5_ids(h5_seal_copies)
            # memory-bounded assembly (cb4_walk_lean): the pinned assemble_units on stubs plus the full events of the sampled series only
            from .cb4_walk_lean import assemble_units_lean  # noqa: PLC0415

            asm = assemble_units_lean(wpath, wgpath, seed=seed, n_series=n_series, n_sports=n_sports, members=members,
                                 r_from=r_from, r_to=r_to, history_ids=hist, h5_ids=h5, sports_cats=cats)
            urep = {**asm["report"], "history_ids": len(hist), "h5_ids": len(h5), "sports_fee_categories": list(cats)}
            # outcomes first, units last: the units file marks the unit frame as complete
            fr.budget.write(rdir / OUTCOME_FILE, _frame_csv_bytes(SERIES_OUTCOME_COLUMNS, asm["outcomes"]))
            fr.budget.write(rdir / "series.jsonl.gz", _gz_jsonl_bytes(asm["series"]))
            fr.budget.write(rdir / "units_report.json", json.dumps(urep, indent=1, sort_keys=True, default=float).encode())
            fr.budget.write(upath, _gz_jsonl_bytes(asm["units"]))
    except Refused:
        raise
    except FileNotFoundError as exc:
        raise Refused(str(exc)) from exc
    except OSError as exc:
        return {"stopped": f"disk_budget: {exc}"}
    frame_rep = {**json.loads(frpath.read_text()), "units": json.loads((rdir / "units_report.json").read_text())}
    units = _load_jsonl_gz(upath)
    side_by = {r["unit_id"]: r for r in pd.read_csv(rdir / OUTCOME_FILE, dtype=str, keep_default_na=False).to_dict("records")}
    extra = {"frame_report": frame_rep, "n_units": len(units)}
    items = sorted(units, key=lambda u: hb._rank(seed, u["unit_id"]))
    stopped, pending = _fetch_items(
        fr, items, "unit_id", lambda u: fetch_unit_series(fr.lim, u, side_by[u["unit_id"]], fr.key, rdir, fr.budget,
                                                         cap_epoch=fr.cap_epoch, max_trades=max_trades),
        _tally_era(fr.counts), should_stop, extra)
    if stopped is None and pending == 0:
        extra["complete"] = True
        m = fr.manifest(None, extra)
        m["status"] = SERIES_COMPLETE_TOKEN
        return m
    return fr.manifest(stopped or "pending", {**extra, "transient": bool(stopped and stopped.startswith("paused"))})


# ---- seals (q0083) -----------------------------------------------------------------------------------------------


def split_h7s(units: list[dict]) -> dict:
    """SEALED-H7S (CB4 section 1.3). ``D_split4`` = the smallest UTC date d such that |{r : date(t0) >= d}| <= 0.40 |U|;
    HOLDOUT = date(t0) >= D_split4; embargo = D_split4 - 3d <= date(t0) < D_split4 (dropped from both halves);
    SCREEN = the rest. Reads only ``unit_id`` and ``t0_epoch``/``t0_date`` (no price, trade or outcome file)."""
    n = len(units)
    if n == 0:
        return {"d_split4": None, "screen": [], "holdout": [], "embargo": [], "n": 0}
    dates = {u["unit_id"]: datetime.fromtimestamp(float(u["t0_epoch"]), UTC).date() for u in units}
    ds = sorted(dates.values())
    lo, hi = ds[0], ds[-1] + timedelta(days=1)
    d_split, d = hi, lo
    while d <= hi:
        if len(ds) - bisect.bisect_left(ds, d) <= SPLIT_HOLDOUT_FRAC * n + 1e-9:
            d_split = d
            break
        d += timedelta(days=1)
    emb_lo = d_split - timedelta(days=SPLIT_EMBARGO_D)
    screen, holdout, embargo = [], [], []
    for u in units:
        k = dates[u["unit_id"]]
        (holdout if k >= d_split else embargo if k >= emb_lo else screen).append(u["unit_id"])
    return {"d_split4": d_split.isoformat(), "screen": sorted(screen), "holdout": sorted(holdout),
            "embargo": sorted(embargo), "n": n}


def drop_era_overlap(units: list[dict], era_market_ids: set[str]) -> tuple[list[dict], list[str]]:
    """Units with any predecessor or successor market in the ``h7_cb4_era`` listing are dropped, by id (counted)."""
    kept: list[dict] = []
    dropped: list[str] = []
    for u in units:
        mids = set(u["pred_market_ids"]) | {m["market_id"] for m in u["succ_markets"]}
        if mids & era_market_ids:
            dropped.append(u["unit_id"])
        else:
            kept.append(u)
    return kept, sorted(dropped)


def ids_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(str(i) for i in ids)).encode()).hexdigest()


def split_record(sp: dict, *, n_before: int, dropped: list[str], units_sha: str, era_listing_sha: str | None) -> dict:
    return {
        "rule": "time-ordered by roll date t0 (section 1.3); 3-day embargo dropped from both halves",
        "d_split": sp["d_split4"], "d_split4": sp["d_split4"], "embargo_days": SPLIT_EMBARGO_D,
        "holdout_frac_max": SPLIT_HOLDOUT_FRAC, "n_units_before_overlap_drop": n_before,
        "n_dropped_era_overlap": len(dropped), "dropped_era_overlap_ids_sha256": ids_sha256(dropped),
        "n_universe": sp["n"], "n_screen": len(sp["screen"]), "n_holdout": len(sp["holdout"]),
        "n_embargo": len(sp["embargo"]), "screen_ids_sha256": ids_sha256(sp["screen"]),
        "holdout_ids_sha256": ids_sha256(sp["holdout"]), "embargo_ids_sha256": ids_sha256(sp["embargo"]),
        "units_file_sha256": units_sha, "era_listing_sha256": era_listing_sha,
        "inputs": "t0 dates and market ids (units.jsonl.gz, era sample.csv.gz ids); no price, trade or outcome file was opened",
        "declaration_sha256": declaration_sha256_h7()}


def _era_market_ids(era_dir: Path) -> set[str] | None:
    sp = Path(era_dir) / "sample.csv.gz"
    if not sp.exists() or (Path(era_dir) / NOT_RUN_FILE).exists():
        return None
    return set(pd.read_csv(sp, usecols=["market_id"], dtype=str).market_id)


def run_state(rdir: Path, wall_clock: Callable[[], float] = time.time, t_seal_epoch: float = T_SEAL_EPOCH) -> str:
    """``complete`` | ``not_run`` | ``unfinished`` (an unfinished run at or after T_seal is marked ``not_run`` here)."""
    rdir = Path(rdir)
    mp = rdir / "manifest.json"
    if (rdir / NOT_RUN_FILE).exists():
        return "not_run"
    if not mp.exists():
        if wall_clock() >= t_seal_epoch:
            mark_not_run(rdir, rdir.name, "never started; T_seal passed")
            return "not_run"
        return "unfinished"
    man = json.loads(mp.read_text())
    if man.get("stopped") == NOT_RUN_TOKEN:
        return "not_run"
    if man.get("complete") is True and not man.get("stopped"):
        return "complete"
    if wall_clock() >= t_seal_epoch:
        mark_not_run(rdir, rdir.name, "incomplete at T_seal")
        return "not_run"
    return "unfinished"


def write_not_run_record(rdir: Path, seals_dir: Path | None = None) -> Path:
    """``docs/research_lab/seals/<run_id>_NOT_RUN.json`` (a Claude session commits it). Never rewritten."""
    rdir = Path(rdir)
    marker = json.loads((rdir / NOT_RUN_FILE).read_text())
    man = json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}
    dest = Path(SEALS_DIR if seals_dir is None else seals_dir) / f"{rdir.name}_NOT_RUN.json"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps({**marker, "counts_at_deadline": man.get("counts"), "dependent_tests":
                                    "recorded 'not run (deadline)' with p = 1 and still counted (CB4 section 1.3)"},
                                   indent=1, sort_keys=True))
    return dest


def seal_h7_run(root: Path, run_id: str, *, seals_dir: Path | None = None, trials_path: Path | None = None,
                wall_clock: Callable[[], float] = time.time, t_seal_epoch: float = T_SEAL_EPOCH) -> dict:
    """Seal one finished h7 run. Returns a result dict: ``sealed`` (with the committed copy path), ``already_sealed``
    or ``not_run`` (recorded, never sealed). Raises ``SealError`` for an unfinished run T_seal has not cut."""
    h5_seal.check_run_id(refuse_run_id(run_id), H7_RUN_IDS)
    rdir = Path(root) / run_id
    if not rdir.exists() and wall_clock() < t_seal_epoch:
        raise h5_seal.SealError(f"{run_id}: no run directory")
    if (rdir / h5_seal.SEAL_NAME).exists():
        seal = verify_h7(root, run_id, seals_dir=seals_dir)
        return {"run_id": run_id, "already_sealed": True, "listing_sha256": seal["listing_sha256"]}
    st = run_state(rdir, wall_clock, t_seal_epoch)
    if st == "not_run":
        rec = write_not_run_record(rdir, seals_dir)
        return {"run_id": run_id, "not_run": True, "status": NOT_RUN_TOKEN, "record": str(rec)}
    if st != "complete":
        raise h5_seal.SealError(f"{run_id}: refusing to seal an unfinished run that T_seal has not cut")
    kw = {"trials_path": Path(trials_path)} if trials_path else {}
    if run_id == ERA_RUN_ID:
        man = json.loads((rdir / "manifest.json").read_text())
        rules = (man.get("frame_report") or {}).get("rules") or {}
        extra = {"universe": {"n_markets": man.get("n_sample"), "frame_rules": rules,
                              "cells": ((man.get("frame_report") or {}).get("sample") or {}).get("cells")}}
        seal = h5_seal.seal_run(rdir, declaration_base=h5_seal.DECLARATION_H7_ERA, extra=extra,
                                source="creative_batch_4:cb4_f_seal", **kw)
        rec = None
    else:
        units = _load_jsonl_gz(rdir / "units.jsonl.gz")
        era_dir = Path(root) / ERA_RUN_ID
        era_ids = _era_market_ids(era_dir)
        era_seal = json.loads((era_dir / h5_seal.SEAL_NAME).read_text()) if (era_dir / h5_seal.SEAL_NAME).exists() else {}
        kept, dropped = drop_era_overlap(units, era_ids or set())
        sp = split_h7s(kept)
        if sp["n"] == 0:
            raise h5_seal.SealError(f"{run_id}: no roll units after exclusions; nothing to seal")
        rec = split_record(sp, n_before=len(units), dropped=dropped, units_sha=h5_seal.sha256_file(rdir / "units.jsonl.gz"),
                           era_listing_sha=era_seal.get("listing_sha256"))
        rec["era_listing"] = "present" if era_ids is not None else "absent"
        seal = h5_seal.seal_run(rdir, declaration_base=h5_seal.DECLARATION_H7_SERIES, extra={"split": rec},
                                source="creative_batch_4:cb4_f_seal", **kw)
    copy = h5_seal.write_committed_copy(rdir, Path(seals_dir) if seals_dir else None)
    out = {"run_id": run_id, "sealed": True, "committed_copy": str(copy), "listing_sha256": seal["listing_sha256"],
           "n_files": seal["n_files"]}
    if rec:
        out.update(d_split4=rec["d_split4"], n_universe=rec["n_universe"], n_screen=rec["n_screen"],
                   n_holdout=rec["n_holdout"], n_embargo=rec["n_embargo"], n_dropped_era_overlap=rec["n_dropped_era_overlap"])
    return out


def verify_h7(root: Path, run_id: str, seals_dir: Path | None = None) -> dict:
    """The seal verifies, the committed copy matches, and (series) the recorded split recomputes from ``units.jsonl.gz``
    and the era listing ids."""
    h5_seal.check_run_id(refuse_run_id(run_id), H7_RUN_IDS)
    rdir = Path(root) / run_id
    seal = h5_seal.require_sealed(rdir, h5_seal.committed_seal_path(run_id, seals_dir))
    if run_id == SERIES_RUN_ID:
        units = _load_jsonl_gz(rdir / "units.jsonl.gz")
        era_ids = _era_market_ids(Path(root) / ERA_RUN_ID)
        kept, dropped = drop_era_overlap(units, era_ids or set())
        sp = split_h7s(kept)
        got = seal.get("split") or {}
        for k, v in (("d_split4", sp["d_split4"]), ("n_universe", sp["n"]), ("screen_ids_sha256", ids_sha256(sp["screen"])),
                     ("holdout_ids_sha256", ids_sha256(sp["holdout"])), ("embargo_ids_sha256", ids_sha256(sp["embargo"])),
                     ("dropped_era_overlap_ids_sha256", ids_sha256(dropped))):
            if got.get(k) != v:
                raise h5_seal.SealError(f"{run_id}: recorded split differs from the recomputed split at {k}")
    return seal


# ---- commands (argparse-free: take a namespace; scripts/run_cb4.py parses) ------------------------------------------


def _print(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _fetch_summary(m: dict) -> dict:
    out = {k: m.get(k) for k in ("counts", "requests", "disk_bytes", "stopped", "complete", "transient", "n_sample", "n_units",
                                 "elapsed_s_this_session", "status")}
    out["frame_report"] = m.get("frame_report")
    return out


def cmd_fetch(args, *, require_committed: bool = True, allow_nondeclared: bool = False) -> int:
    """``run_cb4.py fetch --kind era|series`` (aliases ``era-fetch``, ``series-fetch``). Refuses (exit 2) unless: the run
    id is the kind's own and not a refused one; the committed ``h5_cb1_SEAL.json`` exists; (series) the committed
    series-rule file matches this code; the declared arguments are unchanged; ``data-dumps`` is under 10 GB; the
    ``--root`` is not under a CB1/CB2 extract root. At or after T_seal a new chunk is refused and an incomplete run is
    marked ``not_run_deadline`` (exit 0, status printed). Prints one JSON line; ``status`` is ``era_fetch_complete`` /
    ``series_fetch_complete`` / ``not_run_deadline`` when terminal. A budget or transient stop exits 0 and a re-run resumes."""
    g = lambda name, default=None: getattr(args, name, None) if getattr(args, name, None) is not None else default  # noqa: E731
    kind = args.kind
    try:
        if kind not in ("era", "series"):
            raise Refused(f"unknown kind {kind!r}")
        rid = refuse_run_id(g("run_id", ERA_RUN_ID if kind == "era" else SERIES_RUN_ID), (ERA_RUN_ID if kind == "era" else SERIES_RUN_ID,))
        root = refuse_path(Path(g("root", HIST_ROOT)))
        seal_copies = [Path(p) for p in _csv_list(g("exclude_seal_ids", ""))]
        require_h5_seal_copy(seal_copies, require_committed=require_committed)
        seal_copies = with_ladders_copy(seal_copies)
        stage = g("stage", "all")
        if stage not in ("frame", "all"):
            raise Refused(f"unknown stage {stage!r}")
        for r in _csv_list(g("exclude_runs", "")):  # fix 10: a missing exclusion sample is a refusal
            if not (root / r / "sample.csv.gz").exists():
                raise Refused(f"excluded run {r!r} has no {root / r / 'sample.csv.gz'}; refusing")
        if kind == "series":
            require_series_rules(Path(g("series_rules_file", SERIES_RULES_FILE)), require_committed=require_committed)
        if not allow_nondeclared:
            bad = []
            if g("seed", ERA_SEED if kind == "era" else SERIES_SEED) != (ERA_SEED if kind == "era" else SERIES_SEED):
                bad.append("seed")
            if _ep(g("cap_at", T_SEAL)) != T_SEAL_EPOCH:
                bad.append("cap_at")
            if set(_csv_list(g("exclude_categories", "weather"))) != {"weather"}:
                bad.append("exclude_categories")
            if tuple(x.lower() == "true" for x in _csv_list(g("walk_closed", "true,false"))) != (True, False):
                bad.append("walk_closed")
            if kind == "era":
                if int(g("per_cell", ERA_PER_CELL)) != ERA_PER_CELL:
                    bad.append("per_cell")
                if parse_periods(g("periods", ERA_PERIODS)) != parse_periods(ERA_PERIODS):
                    bad.append("periods")
                if float(g("origin_window_h", ERA_ORIGIN_H)) != ERA_ORIGIN_H or float(g("min_life_d", ERA_MIN_LIFE_D)) != ERA_MIN_LIFE_D:
                    bad.append("origin_window_h/min_life_d")
            else:
                if (int(g("n_series", SERIES_N)), int(g("n_sports_series", SERIES_N_SPORTS)), int(g("members_per_series", SERIES_MEMBERS))) != (
                        SERIES_N, SERIES_N_SPORTS, SERIES_MEMBERS):
                    bad.append("n_series/n_sports_series/members_per_series")
                if _ep(g("roll_from", SERIES_ROLL_FROM)) != _ep(SERIES_ROLL_FROM):
                    bad.append("roll_from")
            if bad:
                raise Refused(f"arguments differ from the declaration: {bad}")
        wall_clock = g("wall_clock", time.time)
        # a terminal state needs no room check; a new chunk does
        early = _guard_start(root, rid, wall_clock, T_SEAL_EPOCH, ERA_COMPLETE_TOKEN if kind == "era" else SERIES_COMPLETE_TOKEN)
        if early is not None:
            _print(early)
            return 0
        require_data_dumps_room(Path(g("data_dumps", HIST_ROOT.parent.parent)), float(g("data_dumps_cap_gb", DATA_DUMPS_FETCH_CAP_GB)))
    except (Refused, FileNotFoundError) as exc:
        _print({"refused": str(exc)})
        return getattr(exc, "code", 2)
    kw = {k: getattr(args, k) for k in ("now", "sleep", "wall_clock", "key") if getattr(args, k, None) is not None}
    if getattr(args, "live_check", None) is not None:
        kw["live_check"] = args.live_check
    if getattr(args, "health_check", None) is not None:
        kw["health_check"] = args.health_check
    transport = g("transport") or hb.httpx_transport()
    stage_kw = dict(stage=stage, amendment_file=Path(g("group_s_amendment", AMENDMENT_FILE)), require_committed=require_committed)
    common = dict(exclude_runs=_csv_list(g("exclude_runs", "")), h5_seal_copies=seal_copies,
                  walk_closed=tuple(x.lower() == "true" for x in _csv_list(g("walk_closed", "true,false"))),
                  cap_at=g("cap_at", T_SEAL), rps=float(g("rps", 4.0)), budget_min=g("budget_min"),
                  max_trades=int(g("max_trades", ERA_MAX_TRADES)), snapshot_root=Path(g("snapshot_root", SNAPSHOT_ROOT)), **kw)
    try:
        if kind == "era":
            m = era_fetch(root, rid, transport, seed=g("seed", ERA_SEED), per_cell=int(g("per_cell", ERA_PER_CELL)),
                          periods=parse_periods(g("periods", ERA_PERIODS)), disk_cap=int(float(g("disk_cap_gb", 0.20)) * 1024**3),
                          **stage_kw, **common)
        else:
            m = series_fetch(root, rid, transport, seed=g("seed", SERIES_SEED), n_series=int(g("n_series", SERIES_N)),
                             n_sports=int(g("n_sports_series", SERIES_N_SPORTS)), members=int(g("members_per_series", SERIES_MEMBERS)),
                             roll_from=g("roll_from", SERIES_ROLL_FROM), disk_cap=int(float(g("disk_cap_gb", 0.40)) * 1024**3),
                             **stage_kw, **common)
    except Refused as exc:
        _print({"refused": str(exc)})
        return exc.code
    _print(_fetch_summary(m))
    return 0


def cmd_seal(args) -> int:
    """``run_cb4.py seal --run-ids h7_cb4_era,h7_cb4_series``: era first, then series (era ids are the overlap
    exclusion). A ``not_run_deadline`` run is recorded (never sealed) and the other run is still sealed (exit 0)."""
    rc = 0
    root = Path(getattr(args, "root", None) or HIST_ROOT)
    seals = Path(args.seals_dir) if getattr(args, "seals_dir", None) else None
    trials = getattr(args, "trials_path", None)
    ids = _csv_list(getattr(args, "run_ids", None) or ",".join(H7_RUN_IDS))
    ids = sorted(ids, key=lambda r: (r != ERA_RUN_ID, r))  # era before series
    for rid in ids:
        try:
            _print(seal_h7_run(root, rid, seals_dir=seals, trials_path=Path(trials) if trials else None,
                               wall_clock=getattr(args, "wall_clock", None) or time.time))
        except (h5_seal.SealError, Cb4Error, FileNotFoundError) as exc:
            _print({"run_id": rid, "error": str(exc)})
            rc = 1
    return rc


def cmd_verify_seal(args) -> int:
    rc = 0
    root = Path(getattr(args, "root", None) or HIST_ROOT)
    seals = Path(args.seals_dir) if getattr(args, "seals_dir", None) else None
    for rid in _csv_list(getattr(args, "run_ids", None) or ",".join(H7_RUN_IDS)):
        try:
            if (root / rid / NOT_RUN_FILE).exists():
                _print({"run_id": rid, "verified": True, "status": NOT_RUN_TOKEN})
                continue
            seal = verify_h7(root, rid, seals)
            _print({"run_id": rid, "verified": True, "listing_sha256": seal["listing_sha256"],
                    "d_split4": (seal.get("split") or {}).get("d_split4")})
        except (h5_seal.SealError, Cb4Error, FileNotFoundError) as exc:
            _print({"run_id": rid, "error": str(exc)})
            rc = 1
    return rc


def cmd_series_rules(args) -> int:
    """``run_cb4.py series-rules``: write ``docs/research_lab/seals/cb4_series_rules.json`` (the cadence and matching rule
    hashes). A Claude session commits it before q0082 can run."""
    try:
        path = write_series_rules(Path(getattr(args, "path", None) or SERIES_RULES_FILE))
    except Refused as exc:
        _print({"refused": str(exc)})
        return 2
    _print({"written": str(path), **series_rules_doc()})
    return 0


def cmd_record_deadline(args) -> int:
    """``run_cb4.py record-deadline``: dependency-free recorder for the T_seal rule (fix 11). Before T_seal it prints
    ``{"deadline_recorded": false, "not_yet": ...}`` and exits 0 (no retry is burned; the queue repeat re-runs it).
    At or after T_seal, every h7 run that is neither sealed nor complete is marked ``not_run_deadline`` (marker file,
    manifest, ``seals/<run>_NOT_RUN.json``); runs already sealed or complete (q0083 seals them) are left alone. Prints
    ``"deadline_recorded": true`` and exits 0."""
    wall = getattr(args, "wall_clock", None) or time.time
    if wall() < T_SEAL_EPOCH:
        _print({"deadline_recorded": False, "not_yet": f"before T_seal {T_SEAL}", "now": _iso(wall())})
        return 0
    root = Path(getattr(args, "root", None) or HIST_ROOT)
    seals = Path(args.seals_dir) if getattr(args, "seals_dir", None) else None
    states = {}
    for rid in H7_RUN_IDS:
        rdir = root / rid
        if (rdir / h5_seal.SEAL_NAME).exists():
            states[rid] = "sealed"
            continue
        st = run_state(rdir, wall, T_SEAL_EPOCH)
        if st == "not_run":
            write_not_run_record(rdir, seals)
        states[rid] = st
    _print({"deadline_recorded": True, "states": states})
    return 0


__all__ = ["CB4_ROOT", "CLOSEWIN_COLUMNS", "CLOSEWIN_VERSION", "Catalogue", "ExtractLocked", "ReleaseCopies",
           "ReleaseUnavailable", "VersionMismatch", "build_capture", "read_closewin", "run_closewin"]
