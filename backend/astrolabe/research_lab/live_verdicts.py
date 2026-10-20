"""Mechanical verdicts for E009/E010 (and a consistency check for E011) from the FROZEN
``analyze`` outputs. No statistic is computed here: every number is read from the analysis JSON
and compared with the thresholds written in EXPERIMENT_LEDGER.md (E009 "Verdicts", E010
"Verdicts (per horizon, after Holm)", E011 "Verdicts"). See
docs/research_lab/LIVE_TESTS_READINESS_2026-10-19.md, addendum A2.

E009 "dk1 slope" = ``horizons["20"]["slope_dp_on_dk1"]`` (the simple slope of dP(20 min) on dk1).
The registration names the partial slope explicitly wherever it means it ("the partial slope on
dk1 given the frozen M0 prediction"; "the partial-slope CI"), so the unqualified "dk1 slope" is
the simple one, at the primary horizon.
"""

from __future__ import annotations

import math

SUPPORTED = "Supported (exploratory, prospective)"
E009_MIN_CLUSTERS, E009_MIN_ORIGINS = 20, 5000
E010_MIN_CLUSTERS, E010_MIN_ORIGINS = 20, 2000
E011_MIN_EPISODES, E011_MIN_CLUSTERS = 30, 10
ALPHA = 0.05


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def economics(pnl: dict | None) -> str:
    """'covers taker costs (paper)' only at the trade/cluster minimum with mean > 0, p < 0.05."""
    if not pnl or pnl.get("status") != "ok":
        return "not shown"
    if _f(pnl.get("mean_pnl_per_share")) > 0 and _f(pnl.get("p_one_sided")) < ALPHA:
        return "covers taker costs (paper)"
    return "not shown"


def verdict_e009(res: dict) -> dict:
    h = res.get("horizons", {}).get("20", {})
    used = {k: h.get(k) for k in ("status", "n_clusters", "n_origins", "rel_mse_gain",
                                  "p_one_sided", "ci", "slope_dp_on_dk1", "partial_slope_ci")}
    if (h.get("status") != "ok" or _f(h.get("n_clusters")) < E009_MIN_CLUSTERS
            or _f(h.get("n_origins")) < E009_MIN_ORIGINS):
        v = "Unavailable"
    elif (_f(h["rel_mse_gain"]) > 0 and _f(h["p_one_sided"]) < ALPHA
          and _f(h["slope_dp_on_dk1"]) > 0):
        v = SUPPORTED
    elif _f(h["ci"][1]) < 0:
        v = ("Contradicted: lead present, frozen scale miscalibrated"
             if _f(h["partial_slope_ci"][0]) > 0 else "Contradicted")
    else:
        v = "Inconclusive"
    return {"experiment": "E009", "verdict": v,
            "economics": economics(res.get("executable_pnl")), "fields_used": used}


def verdict_e010(res: dict) -> dict:
    out = {"experiment": "E010", "horizons": {}, "holm_m1": res.get("holm_m1"), "notes": []}
    unavailable = []
    for hk in ("60", "360"):
        h = res.get("horizons", {}).get(hk, {})
        padj = _f((res.get("holm_m1") or {}).get(hk, 1.0))
        if (h.get("status") != "ok" or _f(h.get("n_clusters")) < E010_MIN_CLUSTERS
                or _f(h.get("n_origins")) < E010_MIN_ORIGINS):
            v = "Unavailable"
            unavailable.append(hk)
        elif padj < ALPHA and _f(h["rel_mse_gain_m1"]) > 0:
            v = SUPPORTED
        elif _f(h["ci_m1"][1]) < 0:
            v = "Contradicted"
        else:
            v = "Inconclusive"
        out["horizons"][hk] = {
            "verdict": v, "holm_p": padj, "economics": economics(h.get("executable_pnl")),
            "fields_used": {k: h.get(k) for k in ("status", "n_clusters", "n_origins",
                                                   "rel_mse_gain_m1", "p_one_sided_m1", "ci_m1")}}
    for hk in unavailable:
        if res.get("horizons", {}).get(hk, {}).get("status") == "ok":
            out["notes"].append(
                f"horizon {hk} is Unavailable by the registered minimum but entered the frozen "
                "Holm with its own p (the code gives p = 1 only below 2 clusters); the reviewer "
                "states which reading of 'a horizon without a test' applies before reporting")
    return out


def verdict_e011(res: dict) -> dict:
    """Re-derives E011's verdict from its own output and checks it equals the frozen code's."""
    n_ep, n_cl = _f(res.get("n_episodes_analysed")), _f(res.get("n_clusters"))
    if n_ep < E011_MIN_EPISODES or n_cl < E011_MIN_CLUSTERS or res.get("p_one_sided") is None:
        v = "Unavailable"
    elif _f(res["p_one_sided"]) < ALPHA and _f(res["excess_mean"]) > 0:
        v = SUPPORTED
    elif _f((res.get("excess_ci95") or [None, None])[1]) < 0:
        v = "Contradicted"
    else:
        v = "Inconclusive"
    return {"experiment": "E011", "verdict": v, "frozen_code_verdict": res.get("verdict"),
            "consistent": v == res.get("verdict")}
