"""E011 descriptive supplement: the registered secondary outputs that the frozen
``surprise_snapshot.analyze`` does not print (EXPERIMENT_LEDGER § E011 "Secondary (descriptive)":
(c) 2 h label, (d) |move| rates for controls too, (e) sports vs non-sports, (f) control_match
composition, (g) passes missed and request/timing statistics).

Pre-declared 2026-10-20, before any E011 outcome was looked at (readiness audit). Descriptive
only: no p-value here enters a verdict, nothing is added to the multiplicity count, and the
primary and verdict come only from ``surprise_snapshot.analyze``. Episodes are formed exactly as
``analyze`` forms them (same window filter, same head rule, same drops); a test pins the equality.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import surprise_snapshot as ss

SEED = 20261015  # descriptive CIs only
PASS_GRID_S = 7200.0
SLOT_TOL_S = 1800.0


def _episode_rows(root: Path, t0: float, t1: float):
    alerts = {a["alert_id"]: a for a in ss.read_jsonl(root / "alerts.jsonl")
              if a.get("type") == "alert" and t0 <= float(a.get("capture_t", a["t"])) < t1
              and a.get("evidence_role") == "prospective_confirmation"}
    controls: dict[str, list[dict]] = {}
    for c in ss.read_jsonl(root / "alerts.jsonl"):
        if c.get("type") == "control" and c["control_for"] in alerts:
            controls.setdefault(c["control_for"], []).append(c)
    lab = {o["alert_id"]: o for o in ss.read_jsonl(root / "outcomes.jsonl")
           if o.get("what") == "label" and o.get("status") == "evaluated"}
    heads, last = [], {}
    for a in sorted(alerts.values(), key=lambda a: (a["market_id"], a["t"])):
        m = a["market_id"]
        if m not in last or a["t"] - last[m] >= 86400.0:
            heads.append(a)
        last[m] = a["t"]
    rows = []
    for a in heads:
        la = lab.get(a["alert_id"])
        cs = [lab.get(c["alert_id"]) for c in controls.get(a["alert_id"], [])]
        cs = [c for c in cs if c is not None]
        if la is None or not cs:
            continue

        def absrate(o, k):
            v = o.get(k)
            return np.nan if v is None else float(abs(v) >= 0.15)

        rows.append({
            "cluster": ss._cluster_id(a), "fee": a.get("fee_category"),
            "hit2": float(la["hit_2h"]), "ctrl2": float(np.mean([c["hit_2h"] for c in cs])),
            "a6": absrate(la, "fwd_move_6h"), "c6": np.nanmean([absrate(c, "fwd_move_6h")
                                                                for c in cs]),
            "a24": absrate(la, "fwd_move_24h"), "c24": np.nanmean([absrate(c, "fwd_move_24h")
                                                                   for c in cs]),
            "hit": float(la["hit_6h"]), "ctrl": float(np.mean([c["hit_6h"] for c in cs]))})
    return alerts, controls, heads, pd.DataFrame(rows)


def _excess(df: pd.DataFrame, a: str, c: str, n_boot: int) -> dict:
    from .ml_explain import cluster_boot

    if df.empty:
        return {"n": 0, "rate_alert": None, "rate_control": None, "excess_mean": None,
                "ci95": [None, None]}
    d = df[a].to_numpy(float) - df[c].to_numpy(float)
    b = cluster_boot(d, df["cluster"].to_numpy(), n_boot=n_boot, seed=SEED)
    return {"n": int(np.isfinite(d).sum()), "rate_alert": float(np.nanmean(df[a])),
            "rate_control": float(np.nanmean(df[c])), "excess_mean": b["mean"],
            "ci95": b["ci"]}


def supplement(root: Path = ss.ROOT, *, start_utc: str = ss.REGISTERED_UTC,
               end_utc: str = ss.END_UTC, n_boot: int = 2000) -> dict:
    root = Path(root)
    t0, t1 = ss._epoch(start_utc), ss._epoch(end_utc)
    alerts, controls, heads, df = _episode_rows(root, t0, t1)
    ctrl_lines = [c for cs in controls.values() for c in cs]
    comp = pd.Series([c.get("control_match", "missing") for c in ctrl_lines],
                     dtype=object).value_counts()
    shortfall = sum(1 for x in ss.read_jsonl(root / "alerts.jsonl")
                    if x.get("type") == "control_shortfall" and x.get("alert_id") in alerts)
    # (g) passes: slots on the 2 h grid of the first window capture, until END
    caps = sorted({float(a["capture_t"]) for a in alerts.values()})
    passes = [p for p in ss.read_jsonl(root / "passes.jsonl") if t0 <= float(p["t"]) < t1]
    missed, slots = [], []
    if caps:
        s = caps[0]
        while s < t1:
            slots.append(s)
            s += PASS_GRID_S
        missed = [ss.utc_iso(x) for x in slots
                  if not any(abs(c - x) <= SLOT_TOL_S for c in caps)]

    def q(key):
        v = np.array([float(p[key]) for p in passes if p.get(key) is not None], float)
        return ({"median": float(np.median(v)), "max": float(v.max()), "n": int(len(v))}
                if len(v) else None)

    sports = df[df["fee"] == "sports"] if not df.empty else df
    other = df[df["fee"] != "sports"] if not df.empty else df
    return {
        "declared": "descriptive supplement, no verdict role (surprise_supplement.py)",
        "window": [start_utc, end_utc],
        "n_episodes": len(heads), "n_episodes_analysed": int(len(df)),
        "c_label_2h": _excess(df, "hit2", "ctrl2", n_boot),
        "d_abs_move_ge_0.15": {"6h": _excess(df, "a6", "c6", n_boot),
                               "24h": _excess(df, "a24", "c24", n_boot)},
        "e_sports_vs_non_sports": {"sports": _excess(sports, "hit", "ctrl", n_boot),
                                   "non_sports": _excess(other, "hit", "ctrl", n_boot)},
        "f_control_match": {"lines": {str(k): int(v) for k, v in comp.items()},
                            "control_shortfall_lines": shortfall},
        "g_passes": {"slots": len(slots), "captures_with_alerts": len(caps),
                     "missed_slots": missed, "passes_logged": len(passes),
                     "status": pd.Series([p.get("status") for p in passes],
                                         dtype=object).value_counts().to_dict(),
                     "requests": q("requests"), "seconds": q("seconds"),
                     "n_eligible": q("n_eligible")},
    }
