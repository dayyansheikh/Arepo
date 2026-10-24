# ruff: noqa: E501
"""Input-coverage monitor (DESIGN_V1 section 31): is every feature family still being filled?

A silent upstream break (a stream that stops, an API field that disappears, a sweep that writes no books) leaves NaN or
zero columns. The models still predict, so nothing fails, but days of prospective scores are spent on a broken input.
This module compares the newest capture's per-column coverage with the median of the previous ``TRAIL`` captures and
reports alerts. It reads only the engine's own write-once features / aux tables (never labels, predictions or scores),
so it carries no outcome information and changes no model, feature or score. Its output is a rewritable view
(``state/input_health.json``) with the per-capture cache next to it (``state/input_health_cache.json``; every table it
summarises is write-once, so a cached entry never goes stale).
"""

from __future__ import annotations

import json
import math

import numpy as np

from astrolabe.signal_engine import aux as A
from astrolabe.signal_engine import features as F
from astrolabe.signal_engine import store as S

SCHEMA = "se-input-health-v1"
TRAIL = 12  # previous captures compared against (one day of 2 h slots)
MIN_TRAIL = 4  # fewer usable earlier captures: the column is not judged ("short_history")
DROP_RATIO = 0.5  # finite share below half the trailing median: "drop"
MIN_MEDIAN = 0.02  # the drop and all-zero rules need a trailing median share of at least 2%
UNIVERSE_RATIO = 0.7  # eligible rows below 70% of the trailing median: "universe"
PENDING_S = 4 * 3600.0  # an aux table still missing this long after the capture start is "missing" (else "pending")
# constant within a capture by construction (calendar), so an all-zero capture (Monday, 00:xx) is normal
NO_ZERO_RULE = frozenset({"sp_dow", "sp_hour"})
SOURCE_FAMILIES = tuple(F.FAMILY_COLUMNS)
FAMILIES = (*SOURCE_FAMILIES, *A.AUX_FAMILIES)


def _cols(fam: str) -> list[str]:
    return F.FAMILY_COLUMNS[fam] if fam in F.FAMILY_COLUMNS else A.AUX_COLUMNS[fam]


def _shares(df, cols: list[str]) -> dict[str, list[float]]:
    """Per column: [finite share, finite-and-nonzero share]."""
    out = {}
    for c in cols:
        if c not in df.columns or not len(df):
            continue
        v = df[c].to_numpy(float)
        fin = np.isfinite(v)
        out[c] = [round(float(fin.mean()), 6), round(float((fin & (v != 0)).mean()), 6)]
    return out


def capture_summary(paths: S.Paths, meta: dict) -> dict:
    """Coverage of one capture: eligible rows, and per family either the column shares or None (no table yet)."""
    cid = meta["capture_id"]
    f = S.read_parquet(paths.features(cid), F.ALL_FEATURES)
    fams: dict[str, dict | None] = {fam: _shares(f, F.FAMILY_COLUMNS[fam]) for fam in SOURCE_FAMILIES}
    for fam, cols in A.AUX_COLUMNS.items():
        p = A.aux_path(paths, fam, cid)
        fams[fam] = _shares(S.read_parquet(p, cols), cols) if p.exists() else None
    return {"capture_id": cid, "slot": int(meta["slot"]), "started_utc": meta["started_utc"],
            "n_features": int(meta.get("n_features", len(f))), "families": fams}


def _median(xs: list[float]) -> float | None:
    return float(np.median(xs)) if xs else None


def judge(latest: dict, trail: list[dict], now: float) -> dict:
    """Alerts for the newest capture against the earlier ones (pure; the rules are the module constants)."""
    alerts: list[dict] = []
    families: dict[str, dict] = {}
    n_med = _median([t["n_features"] for t in trail])
    universe = {"latest": latest["n_features"], "median": n_med, "status": "ok"}
    if n_med and latest["n_features"] < UNIVERSE_RATIO * n_med:
        universe["status"] = "universe"
        alerts.append({"family": "universe", "rule": "universe", "latest": latest["n_features"], "median": n_med})
    # missed 2 h slots in the trailing day: the look-back columns (2 h / 6 h / 24 h changes, run lengths) of the next
    # captures are NaN or reset, so a gap explains most column alerts that follow it
    seen = {t["slot"] for t in trail}
    gaps = [k for k in range(max(latest["slot"] - TRAIL, min(seen, default=latest["slot"])), latest["slot"]) if k not in seen]
    if trail and gaps:
        alerts.append({"family": "captures", "rule": "capture_gap", "missing_slots": len(gaps),
                       "first_missing_utc": S.iso_s(S.slot_time(gaps[0]))})
    age = now - S.epoch(latest["started_utc"])
    for fam in FAMILIES:
        cur = latest["families"].get(fam)
        prev = [t["families"][fam] for t in trail if t["families"].get(fam) is not None]
        if cur is None:
            st = "pending" if not math.isfinite(age) or age < PENDING_S else "missing"
            if st == "missing" and prev:  # a family that never had a table is not an alert (not yet built)
                alerts.append({"family": fam, "rule": "missing"})
            families[fam] = {"status": st}
            continue
        if len(prev) < MIN_TRAIL:
            families[fam] = {"status": "short_history", "trail": len(prev)}
            continue
        bad = []
        cov_now, cov_med = [], []
        for c in _cols(fam):
            if c not in cur:
                continue
            fin, nz = cur[c]
            mf = _median([p[c][0] for p in prev if c in p])
            mz = _median([p[c][1] for p in prev if c in p])
            if mf is None:
                continue
            cov_now.append(fin)
            cov_med.append(mf)
            if mf > 0 and fin == 0:
                bad.append({"column": c, "rule": "absent", "latest": fin, "median": mf})
            elif mf >= MIN_MEDIAN and fin < DROP_RATIO * mf:
                bad.append({"column": c, "rule": "drop", "latest": fin, "median": mf})
            elif c not in NO_ZERO_RULE and mz is not None and mz >= MIN_MEDIAN and fin > 0 and nz == 0:
                bad.append({"column": c, "rule": "all_zero", "latest": nz, "median": mz})
        families[fam] = {"status": "alert" if bad else "ok",
                         "coverage": round(max(cov_now), 4) if cov_now else None,
                         "median": round(max(cov_med), 4) if cov_med else None}
        if bad:
            families[fam]["columns"] = bad
            alerts.extend({"family": fam, **b} for b in bad)
    return {"universe": universe, "families": families, "alerts": alerts, "missing_slots": len(gaps) if trail else None}


def run(paths: S.Paths, now: float | None = None, write: bool = True) -> dict:
    """Summarise the newest ``TRAIL + 1`` captures (cached) and judge the newest one."""
    now = S.now_ts() if now is None else now
    d = paths.sub("meta")
    metas = []
    for p in sorted(d.glob("*.json"))[-(TRAIL + 1):] if d.exists() else []:
        try:
            metas.append(json.loads(p.read_text()))
        except (OSError, ValueError):
            continue
    if not metas:
        return {"schema": SCHEMA, "at": S.iso_s(now), "status": "no_captures", "alerts": []}
    cache_p = paths.sub("state", "input_health_cache.json")
    try:
        cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    except (OSError, ValueError):
        cache = {}
    summaries = []
    for m in metas:
        s = cache.get(m["capture_id"])
        # an entry with a pending aux table is recomputed (that table may exist now); complete entries never change
        if s is None or any(v is None for v in s["families"].values()) or set(s["families"]) != set(FAMILIES):
            if not paths.features(m["capture_id"]).exists():
                continue
            s = capture_summary(paths, m)
        summaries.append(s)
    if not summaries:
        return {"schema": SCHEMA, "at": S.iso_s(now), "status": "no_captures", "alerts": []}
    latest, trail = summaries[-1], summaries[:-1]
    j = judge(latest, trail, now)
    out = {"schema": SCHEMA, "at": S.iso_s(now), "capture_id": latest["capture_id"], "trail": len(trail),
           "status": "alert" if j["alerts"] else "ok", "n_alerts": len(j["alerts"]), **j,
           "note": "Input coverage only (features and aux tables): no labels, predictions or scores are read."}
    if write:
        S.replace_json(cache_p, {s["capture_id"]: s for s in summaries})
        S.replace_json(paths.sub("state", "input_health.json"), out)
    return out


def read(paths: S.Paths) -> dict | None:
    """The last written view, compacted for the dashboard (status, alert list, per-family status)."""
    p = paths.sub("state", "input_health.json")
    try:
        h = json.loads(p.read_text()) if p.exists() else None
    except (OSError, ValueError):
        return None
    if not h or h.get("schema") != SCHEMA:
        return None
    return {"at": h.get("at"), "capture_id": h.get("capture_id"), "status": h.get("status"),
            "n_alerts": h.get("n_alerts", 0), "alerts": (h.get("alerts") or [])[:20],
            "families": {k: v.get("status") for k, v in (h.get("families") or {}).items()},
            "universe": h.get("universe")}
