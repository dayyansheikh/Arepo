# ruff: noqa: E501, UP031, UP032, UP015, UP004, UP028  (stdlib-only, Python 3.6-compatible: used by the host-side archive scripts)
"""Data catalogue: which archived file belongs to which test or experiment.

Pure functions, standard library only (scripts load this file by path on a Python 3.6 host).

* ``DIR_EXPERIMENTS`` maps each data directory under ``data-dumps/research_lab/`` to the experiments
  whose code reads or writes it. It was derived from the readers in ``backend/astrolabe/research_lab``
  and ``backend/scripts`` (see the comment above each entry) and the ids in
  ``docs/research_lab/EXPERIMENT_LEDGER.md``.
* ``classify(path)`` turns an archive member path into catalogue fields.
* ``matches(row, ...)`` is the shared selector used by ``restore_from_archive.py``.

The catalogue only labels files. It never decides what is evidence and never changes a hash.
"""

import fnmatch
import json
import os
import re

RL = "data-dumps/research_lab/"

# dir -> experiment ids. Basis (readers, 2026-10-15):
DIR_EXPERIMENTS = {
    # forecast.list_complete_captures: E002 (forecast.py), E004/E005/E006 (e004.qualifying_captures), E007 and
    # FLOW-SCREEN (flow_screen.build_sample_pairs reads source+target rows.csv.gz), E011 (surprise_snapshot
    # load_capture), E003 (e003.build_panel reads the snapshot of a sweep), L1 (leadlag_screen).
    "snapshots": ["E002", "E003", "E004", "E005", "E006", "E007", "E011", "FLOW-SCREEN", "L1"],
    # forecast.predict writes one forecast file per snapshot; E002 scores it, E004 uses the frozen spec.
    "forecasts": ["E002", "E004"],
    # book_sweep.py writes; e003.py reads series; D118/D120 design estimates and execution_cost_breakeven read.
    "book_sweeps": ["E003", "D118", "D120", "EXEC-COSTS"],
    # trade_sample.py writes; flow_screen.build_sample_pairs and e007.dev_pairs/build_confirmation read.
    "trade_samples": ["E007", "FLOW-SCREEN"],
    "flow_screen": ["FLOW-SCREEN"],
    # live_trade_monitor.py (+ LIVE_TRADE_MONITOR.md): trades, scores, alerts, outcomes.
    "live_trades": ["LIVE-TRADE-MONITOR"],
    # cross_venue.py / run_cross_venue.py: historical Kalshi-Polymarket study that fixes the E009/E010 models.
    "cross_venue": ["E009", "E010", "CROSS-VENUE-STUDY"],
    # cross_venue_live.py (E009) and cross_venue_live_e010.py (E010) share this stream.
    "cross_venue_live": ["E009", "E010"],
    # surprise_snapshot.py: E011 rolling series, alerts, scores, outcomes.
    "surprise_live": ["E011"],
    "e001": ["E001"],
    "e002": ["E002"],
    "e003": ["E003"],
    "e004": ["E004"],
    "e005": ["E005"],
    "e006": ["E006"],
    "e007": ["E007"],
    # history_backfill.py / history_sources.py / run_event_study / battery / ml_*: development studies.
    "history": ["HB1", "HB1-R", "T5-DEV", "IF-H2-DEV", "ML-DEV", "EVENT-STUDY"],
    "history_sources": ["HB1", "HB1-R", "ML-DEV"],
    "resolution_dev": ["T5-DEV"],
    "if_h2": ["IF-H2-DEV"],
    "large_trade_census": ["LARGE-TRADE-CENSUS"],
    "case_studies": ["CASE-STUDIES"],
    "external_news": ["EXTERNAL-NEWS"],
    "event_study": ["EVENT-STUDY"],
    "ml_cache": ["ML-DEV"],
    "calibration": ["C1"],
    # run_dev_screen.py / run_comparison.py (M1 comparison pipeline, dev screens), leadlag_screen.py (L1),
    # run_surprise_moves.py (SURPRISE_MOVE_DETECTOR.md), convert_snapshot_columnar.py (storage trial).
    "comparisons": ["M1-COMPARISONS"],
    "leadlag_screen": ["L1"],
    "dev_snapshots_v2": ["E001", "L1"],
    "surprise_moves": ["SURPRISE-MOVES-DEV"],
    "surprise_moves_h3": ["SURPRISE-MOVES-DEV"],
    "columnar_trial": ["STORAGE-TRIAL"],
    "phase3_evidence_capsules": ["PHASE3-FS2"],
    "_ops": ["OPS"],
}

# Top-level data-dumps/fs2_* directories are Phase 3 (D082-D120) pilots; they keep their original outcomes.
FS2_EXPERIMENTS = ["PHASE3-FS2"]

EXPERIMENT_LABELS = {
    "E001": "Snapshot repricing baselines (complete, exploratory)",
    "E002": "Prospective 1h-reversal confirmation (complete)",
    "E003": "Book imbalance / microprice (complete, exploratory)",
    "E004": "12-period prospective reversal + execution check (registered)",
    "E005": "Neg-risk arbitrage-band deviation (registered)",
    "E006": "Reversal moderation by liquidity / time-to-end (registered)",
    "E007": "Order-flow continuation in trade-active markets (registered)",
    "E009": "Live Kalshi 10-min move -> Polymarket 20-min move (registered, ends 2026-11-03)",
    "E010": "Live cleaned-set model, 1h and 6h horizons (registered, ends 2026-11-03)",
    "E011": "Live frozen surprise-move detector on complete snapshots (registered, ends 2026-11-10)",
    "FLOW-SCREEN": "Unusual-flow screen run every pass (exploratory)",
    "L1": "Related-market lead-lag screen (development)",
    "C1": "Calibration study (development)",
    "HB1": "Hypothesis battery 1 (development)",
    "HB1-R": "Hypothesis battery 1 replication (development)",
    "T5-DEV": "Resolution forecasting vs recalibrated price (development)",
    "IF-H2-DEV": "Deadline-ladder study (development, null)",
    "ML-DEV": "Historical ML development (HISTORICAL_ML_DEV.md)",
    "EVENT-STUDY": "Event study (development)",
    "D118": "D118 control-pairing design estimates",
    "D120": "D120 pairing design estimates",
    "EXEC-COSTS": "Execution-cost break-even study",
    "CROSS-VENUE-STUDY": "Historical Kalshi-Polymarket study (CROSS_VENUE_STUDY.md)",
    "LIVE-TRADE-MONITOR": "Live large-trade / wallet monitor (LIVE_TRADE_MONITOR.md)",
    "LARGE-TRADE-CENSUS": "Large-trade census (development)",
    "CASE-STUDIES": "Case studies (development)",
    "EXTERNAL-NEWS": "External news pilot (development)",
    "M1-COMPARISONS": "Reusable comparison pipeline outputs (Methods note M1)",
    "SURPRISE-MOVES-DEV": "Surprise-move detector development (SURPRISE_MOVE_DETECTOR.md)",
    "STORAGE-TRIAL": "Columnar snapshot storage trial (not evidence)",
    "OPS": "Operational files (not evidence)",
    "PHASE3-FS2": "Phase 3 fs2 pilot runs D082-D120 (closed; original outcomes kept)",
}

_CAP = re.compile(r"(\d{8}T\d{6}Z)_([0-9a-f]{8})")
_STAMP = re.compile(r"(\d{8}T\d{6}Z)")
_DAY = re.compile(r"(?:^|[-_/])(\d{8})(?=[._/]|$)")


def _iso(stamp):
    return "%s-%s-%sT%s:%s:%sZ" % (stamp[0:4], stamp[4:6], stamp[6:8], stamp[9:11], stamp[11:13], stamp[13:15])


def dir_of(path):
    """('research_lab' dir name | top-level data-dumps dir name | '') for an archive member path."""
    if path.startswith(RL):
        return path[len(RL):].split("/", 1)[0]
    if path.startswith("data-dumps/"):
        return path.split("/")[1] if path.count("/") >= 2 else ""
    return ""


def experiments_for(path):
    d = dir_of(path)
    if path.startswith(RL):
        return list(DIR_EXPERIMENTS.get(d, []))
    if d.startswith("fs2_capture_"):
        return ["E001"]  # EXPERIMENT_LEDGER.md E001: "Local Gamma full-universe captures under data-dumps/fs2_capture_*"
    if d.startswith("fs2_"):
        return list(FS2_EXPERIMENTS)
    return list(DIR_EXPERIMENTS.get(d, [])) if d in ("_ops", "phase3_evidence_capsules") else []


_ACTIVE = re.compile(r"^active_snapshots/(\d{8}T\d{6}Z)/(.*)$")


def classify(path):
    """Catalogue fields for one member path (no I/O). Point-in-time copies of live logs
    (``active_snapshots/<stamp>/<original path>``, archive_rotate.py --include-active) are classified by their
    original path and flagged ``active_snapshot``; capture_time_utc is the copy time."""
    am = _ACTIVE.match(path)
    if am:
        out = classify(am.group(2))
        out.update({"path": path, "active_snapshot": True, "original_path": am.group(2),
                    "capture_id": None, "capture_time_utc": _iso(am.group(1))})
        return out
    out = {"path": path, "dir": dir_of(path), "capture_id": None, "capture_time_utc": None,
           "date_utc": None, "experiments": experiments_for(path)}
    m = _CAP.search(path)
    if m:
        out["capture_id"] = m.group(0)
        out["capture_time_utc"] = _iso(m.group(1))
        return out
    m = _STAMP.search(path)
    if m:
        out["capture_time_utc"] = _iso(m.group(1))
        return out
    m = _DAY.search(os.path.basename(path)) or _DAY.search(path)
    if m and m.group(1)[:2] == "20":
        s = m.group(1)
        out["date_utc"] = "%s-%s-%s" % (s[0:4], s[4:6], s[6:8])
    return out


def build_rows(tag, files, sizes=None, source=None):
    """One catalogue row per file: {release, path, dir, capture_id, capture_time_utc, bytes, sha256, experiments}."""
    rows = []
    for p in sorted(files):
        r = classify(p)
        r["release"] = tag
        r["sha256"] = files[p]
        r["bytes"] = None if sizes is None else sizes.get(p)
        if source:
            r["source"] = source
        rows.append(r)
    return rows


def group_key(path):
    """Group (capture-folder level) key used for very large releases."""
    parts = path.split("/")
    n = 4 if path.startswith(RL) else 2
    return "/".join(parts[:n]) if len(parts) > n else "/".join(parts[:-1]) or path


def build_group_rows(tag, files, source=None):
    """Compact rows (one per capture folder) for releases too large for a per-file catalogue in git."""
    import hashlib

    groups = {}
    for p in sorted(files):
        groups.setdefault(group_key(p), []).append(p)
    rows = []
    for k in sorted(groups):
        members = groups[k]
        h = hashlib.sha256()
        for p in members:
            h.update(("%s  %s\n" % (files[p], p)).encode())
        r = classify(members[0])
        r.update({"release": tag, "path": None, "path_prefix": k + "/", "n_files": len(members),
                  "listing_sha256": h.hexdigest(), "bytes": None, "granularity": "group"})
        r["dir"] = dir_of(members[0])
        if r["capture_id"] and r["capture_id"] not in k:
            r["capture_id"] = r["capture_time_utc"] = None
        if source:
            r["source"] = source
        rows.append(r)
    return rows


def dump_jsonl(rows):
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def load_jsonl(path):
    rows = []
    with open(path) as fh:
        for ln in fh:
            if ln.strip():
                rows.append(json.loads(ln))
    return rows


def matches(row, experiment=None, dirs=None, since=None, until=None, globs=None):
    """Shared selector. since/until are ISO prefixes ('2026-10-14' or '2026-10-14T06:00:00Z') compared with the
    row's capture time (or its date). Rows with no time are excluded when since/until is given."""
    if experiment and experiment not in (row.get("experiments") or []):
        return False
    if dirs and row.get("dir") not in dirs:
        return False
    if since or until:
        t = row.get("capture_time_utc") or row.get("date_utc")
        if not t:
            return False
        if since and t[: len(since)] < since:
            return False
        if until and t[: len(until)] > until:
            return False
    if globs:
        names = [row.get("path") or row.get("path_prefix") or ""]
        if not any(fnmatch.fnmatch(n, g) or fnmatch.fnmatch(n.rstrip("/"), g) for n in names for g in globs):
            return False
    return True
