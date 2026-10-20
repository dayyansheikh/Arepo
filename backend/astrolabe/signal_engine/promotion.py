# ruff: noqa: E501
"""Pre-declared promotion rule ``se-promotion-v1`` (DESIGN_V1.md section 6). Changing any constant here is a new rule
version, declared in the design doc before it is used; it is never tuned to make a challenger pass.

A challenger replaces the champion only if ALL hold on the day's prospective leaderboard (evidence_role prospective):

1. not embargoed, and at least ``MIN_DAYS`` distinct UTC origin days of paired primary-target scores in the
   ``WINDOW_D``-day window, its first prospective prediction at least ``MIN_DAYS`` days old;
2. primary target (dir_2h) mean per-row log-loss gain over the champion (``ll_champion - ll_challenger``) with an
   event-clustered bootstrap CI at level ``1 - 0.05 / K`` (Bonferroni over the K challengers evaluated that day)
   whose lower bound is > 0;
3. the daily mean gain is positive on at least ``MIN_POSITIVE_DAY_SHARE`` of the scored days;
4. calibration not materially worse on the primary target: |slope - 1| <= champion's + ``CAL_SLOPE_TOL`` and
   |intercept| <= champion's + ``CAL_INT_TOL``;
5. no secondary target with a significant loss (95% CI upper bound of the gain < 0, judged only with >= 50 clusters);
6. coverage (share of eligible rows with an on-time prediction) >= champion's - ``COVERAGE_TOL``;
7. at least ``COOLDOWN_D`` days since the last promotion.
Ties: the largest lower bound wins. Promotions are appended to ``champion/history.jsonl``; nothing is ever removed.
"""

from __future__ import annotations

import math

from . import config as C
from . import scoring as SC
from . import specs as SP
from . import store as S

RULE_VERSION = "se-promotion-v1"
WINDOW_D = 28
MIN_DAYS = 14
FAMILY_ALPHA = 0.05
MIN_POSITIVE_DAY_SHARE = 2 / 3
CAL_SLOPE_TOL = 0.10
CAL_INT_TOL = 0.05
SECONDARY_MIN_CLUSTERS = 50
COVERAGE_TOL = 0.01
COOLDOWN_D = 7


def first_prediction_ts(paths: S.Paths, model_id: str) -> float:
    for r in S.read_logs(paths, "predictions"):
        if r.get("model_id") == model_id:
            return S.epoch(r["written_utc"])
    return math.inf


def evaluate(agg: SC.Agg, reg: dict, champion: str, now: float, history: list[dict], first_pred: dict[str, float]) -> dict:
    end_day = S.day_of(now)
    days = SC.window_days(agg.days(), end_day, WINDOW_D)
    champ_m = SC.metrics(agg, C.PRIMARY_TARGET, champion, days)
    last_promo = max((S.epoch(h["at"]) for h in history if h.get("event") == "promotion"), default=-math.inf)
    cands = [m for m in SP.active_models(reg) if m != champion and not SP.embargo_of(reg["models"][m], now)]
    K = max(1, len(cands))
    level = 1 - FAMILY_ALPHA / K
    out = {"rule": RULE_VERSION, "at": S.iso(now), "champion": champion, "K": K, "level": level, "checks": {}, "promote": None}
    if champ_m is None:
        out["reason"] = "champion has no prospective scores"
        return out
    passing = []
    for mid in cands:
        chk: dict = {}
        g = SC.gain(agg, C.PRIMARY_TARGET, mid, WINDOW_D, level=level)
        mt = SC.metrics(agg, C.PRIMARY_TARGET, mid, days)
        chk["days"] = 0 if g is None else g["n_days"]
        chk["age_days"] = (now - first_pred.get(mid, math.inf)) / 86400.0
        chk["c1_days"] = g is not None and g["n_days"] >= MIN_DAYS and chk["age_days"] >= MIN_DAYS
        chk["gain"] = g
        chk["c2_ci"] = g is not None and math.isfinite(g["lo"]) and g["lo"] > 0
        chk["c3_days_positive"] = g is not None and g["n_days"] > 0 and g["days_positive"] / g["n_days"] >= MIN_POSITIVE_DAY_SHARE
        if mt is not None and all(math.isfinite(x) for x in (mt["cal_slope"], mt["cal_intercept"], champ_m["cal_slope"], champ_m["cal_intercept"])):
            chk["c4_calibration"] = (abs(mt["cal_slope"] - 1) <= abs(champ_m["cal_slope"] - 1) + CAL_SLOPE_TOL
                                     and abs(mt["cal_intercept"]) <= abs(champ_m["cal_intercept"]) + CAL_INT_TOL)
        else:
            chk["c4_calibration"] = False
        sec_ok = True
        for t in C.TARGETS:
            if t == C.PRIMARY_TARGET or t not in reg["models"][mid]["targets"]:
                continue
            gs = SC.gain(agg, t, mid, WINDOW_D, level=0.95)
            if gs and gs["n_clusters"] >= SECONDARY_MIN_CLUSTERS and math.isfinite(gs["hi"]) and gs["hi"] < 0:
                sec_ok = False
        chk["c5_secondary"] = sec_ok
        chk["c6_coverage"] = mt is not None and mt["coverage"] >= champ_m["coverage"] - COVERAGE_TOL
        chk["c7_cooldown"] = (now - last_promo) / 86400.0 >= COOLDOWN_D
        chk["pass"] = all(chk[k] for k in ("c1_days", "c2_ci", "c3_days_positive", "c4_calibration", "c5_secondary",
                                           "c6_coverage", "c7_cooldown"))
        out["checks"][mid] = chk
        if chk["pass"]:
            passing.append((g["lo"], mid))
    if passing:
        out["promote"] = max(passing)[1]
    return out


def apply(paths: S.Paths, decision: dict, reg: dict) -> dict | None:
    """Append the promotion (if any) to the champion history. Returns the history row."""
    new = decision.get("promote")
    if not new:
        return None
    row = {"event": "promotion", "at": decision["at"], "champion": new, "previous": decision["champion"],
           "rule": RULE_VERSION, "spec_sha256": reg["models"][new]["_sha256"],
           "evidence": {"gain": decision["checks"][new]["gain"], "level": decision["level"], "K": decision["K"]}}
    SP.append_champion(paths, row)
    return row
