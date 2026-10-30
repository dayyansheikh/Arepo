# ruff: noqa: E501
"""CB17 rules part ``C`` (docs/research_lab/CREATIVE_BATCH_17.md section CB17-C, 11.3): mint share (CH150). Within an event, does a member's 2 h move continue more after a
transfer-heavy interval than after a mint-heavy one?

Declarations and small pure definitions only (frames, estimators and the runner are window code, pinned at the code freeze). Filled from q0402 (``pre_census_C.json``, sha256
``442e99da…``) by part ``pre``'s rule: the selected strata level (2: ``|dm_int|`` {0.5-1c, > 1c}; worn share 0.7773). Nothing numeric from q0402 is carried over except the level: the
trailing tercile cut points are per event and in-window (``[lookback floor, k)``; REP_8: ``[S_8 + 7 d, k)``), as declared. Eligibility uses captures ``k - 1`` and ``k`` only; capture
``k + 1`` is read only for the target and its availability (an unavailable mark is never an exclusion).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from . import cb13_t as t13
from . import cb17_common as c17
from . import cb17_pre as pre
from . import cb17_wcommon as w

Refused = c17.Refused

C_VERSION = "cb17-C-v1"

# ---- filled from q0402 (section 11.3) ----------------------------------------------------------------------------------------------------------------
STRATA_LEVEL_C = 2
STRATA_WORN_SHARES = {"level0": 0.11602254428341385, "level1": 0.5000805152979066, "level2": 0.7772946859903381, "fallback": False, "denominator": 12420, "merge_reported": 7470}
LEVEL_SOURCE = {"job": "q0402", "file": "creative_batch17/pre_census_C.json", "sha256": "442e99da3a7f806b05a76fa9de4e6a52bb8ded5516ff1ae2c67092a46812797d"}

# ---- intervals, states and marks (section CB17-C) ----------------------------------------------------------------------------------------------------
CLASS_TRANSFER, CLASS_MINT, CLASS_MERGE = pre.CLASS_TRANSFER, pre.CLASS_MINT, pre.CLASS_MERGE
MARK_GAP_S = pre.CAP_GAP_S  # capture k + 1 consecutive: last-page receipts 100-140 min after capture k
MARK_OK = "ok"
MARK_REASONS = ("capture missing", "member closed", "one-sided", "wide", "extreme mid")
UNAVAILABLE_MARK = "unavailable (mark)"
THIN_HISTORY = "thin history"
EXCLUSIONS = ("sports", "arm 1 (REP)", "interval gap outside 100-140 min", "OI or volume missing", "not traded (dV <= 0)", "member closed at k-1 or k", "member closing within 3 h of k",
              "no qualifying member", "thin history", "election night", "dropped: key", "unavailable (lookback floor)")

# ---- worst case (binding robustness) -----------------------------------------------------------------------------------------------------------------
WORST_Q = {CLASS_TRANSFER: 5.0, CLASS_MINT: 95.0, CLASS_MERGE: 95.0}  # every unavailable member at the bound adverse to the hypothesis

# ---- gates -------------------------------------------------------------------------------------------------------------------------------------------
GCU_MIN = 0.70  # OI changed in >= 70% of traded non-sports event-intervals in SCREEN_8
GC_EVENTS_MIN = 600  # arm-0 events with at least one unit having >= 6 prior traded intervals
GC_UNITS_MIN = 10000

# ---- robustness, attribution, econ -------------------------------------------------------------------------------------------------------------------
TOP_DV_EXCLUDE_SHARE = 0.01
C1_ROBUSTNESS = ("unavailable-mark worst case", "OI-lag variant r_lag = (OI_k - OI_k-1) / (vol_k-1 - vol_k-2)", "whole-window terciles leaving k and k + 1 out", "single-market events alone",
                 "non-neg-risk events alone", "4 h continuation (k + 2)", "exclude the top 1% of dV", "top-5 drops", "leave-one-day-out")
C1_ATTRIBUTION = ("C_pre", "|dm_int| band", "dV tercile", "mean member spread", "log event liquidity", "moving members", "UTC 6 h band")
ECON_MIN_FILLS = 300
ECON_MIN_EVENTS = 60


# =====================================================================================================================================================
# definitions
# =====================================================================================================================================================


def interval_ok(gap_s: float) -> bool:
    """Consecutive complete captures k - 1, k with last-page received_utc gap in [100, 140] min (inclusive)."""
    return bool(math.isfinite(gap_s) and pre.CAP_GAP_S[0] <= gap_s <= pre.CAP_GAP_S[1])


def r_state(oi0: float, oi1: float, v0: float, v1: float) -> tuple[float, float] | None:
    """``(r, dV)`` with ``r = (OI_k - OI_k-1) / dV``, ``dV = vol_k - vol_k-1``; None when a value is missing or the event did not trade (``dV <= 0``)."""
    if not all(math.isfinite(x) for x in (oi0, oi1, v0, v1)):
        return None
    dv = v1 - v0
    if dv <= 0:
        return None
    return (oi1 - oi0) / dv, dv


def member_mid(bid: float, ask: float) -> float:
    """An eligible member mid: two-sided, spread <= 10c, mid in [0.03, 0.97]; else nan (part pre's capture-state rule)."""
    if not t13.two_sided(bid, ask) or ask - bid > pre.MAX_SPREAD + 1e-12:
        return math.nan
    m = (ask + bid) / 2.0
    return m if pre.MID_RANGE[0] <= m <= pre.MID_RANGE[1] else math.nan


def qualifying_moves(members: Sequence[str], mid0: dict, mid1: dict) -> list[tuple[str, float]]:
    """Members with eligible mids at k - 1 and k and ``|dm_int| >= 0.5c``: ``[(market, dm_int cents)]``."""
    out = []
    for m in members:
        a, b = mid0.get(m, math.nan), mid1.get(m, math.nan)
        if math.isfinite(a) and math.isfinite(b) and abs(b - a) * 100.0 >= pre.MIN_MOVE_C - 1e-9:
            out.append((m, (b - a) * 100.0))
    return out


def classify(r: float, prior_r: Sequence[float]) -> str | None:
    """Trailing tercile class of ``r_k`` against the event's EARLIER traded intervals only (the caller never passes r_k or later): mint-heavy above the upper cut, merge-heavy below the
    lower, transfer between (inclusive); None ("thin history") with fewer than 6 prior."""
    cuts = pre.trailing_cuts(list(prior_r))
    return None if cuts is None else pre.c_class(r, cuts)


def continuation(dm_int_c: float, m_k: float, m_k1: float) -> float:
    """``C_j = sign(dm_int,j) x 100 x (m_j,k+1 - m_j,k)`` cents."""
    if not (math.isfinite(dm_int_c) and math.isfinite(m_k) and math.isfinite(m_k1)) or dm_int_c == 0:
        return math.nan
    return (1.0 if dm_int_c > 0 else -1.0) * 100.0 * (m_k1 - m_k)


def mark_reason(capture_ok: bool, row: dict | None) -> str | None:
    """None if member j's k + 1 mark is available, else the reason (capture missing, member closed, one-sided, wide, extreme mid). Row keys: bid, ask, closed."""
    if not capture_ok or row is None:
        return "capture missing"
    if row.get("closed"):
        return "member closed"
    b, a = row.get("bid", math.nan), row.get("ask", math.nan)
    if not t13.two_sided(b, a):
        return "one-sided"
    if a - b > pre.MAX_SPREAD + 1e-12:
        return "wide"
    m = (a + b) / 2.0
    if not pre.MID_RANGE[0] <= m <= pre.MID_RANGE[1]:
        return "extreme mid"
    return None


def onesided_adverse(dm_int_c: float, m_k: float, row: dict | None, cls: str = CLASS_TRANSFER) -> float:
    """Where a one-sided k + 1 quote exists, the continuation at the touch adverse to the HYPOTHESIS (O11 ruling, symmetric by class): transfer units (high continuation is the hypothesis)
    take the touch adverse to continuation (an up move, dm > 0, at the bid; a down move at the ask); mint-heavy and merge-heavy units (high continuation is hypothesis-adverse) take the touch
    favourable to continuation (an up move at the ask, a down move at the bid); nan where that side is absent."""
    if row is None or not math.isfinite(dm_int_c) or dm_int_c == 0:
        return math.nan
    b, a = row.get("bid", math.nan), row.get("ask", math.nan)
    if cls == CLASS_TRANSFER:
        px = b if dm_int_c > 0 else a
    else:
        px = a if dm_int_c > 0 else b
    if not (math.isfinite(px) and 0 < px < 1):
        return math.nan
    return continuation(dm_int_c, m_k, px)


def worst_member(cls: str, available_C: np.ndarray, onesided_value: float = math.nan) -> float:
    """The bound adverse to the hypothesis for an unavailable member: transfer units min(5th percentile of available member C, touch C), mint-heavy and merge-heavy max(95th percentile,
    touch C), where touch C is ``onesided_adverse`` for the class (a one-sided k + 1 quote; nan otherwise)."""
    v = np.asarray(available_C, float)
    v = v[np.isfinite(v)]
    if not v.size:
        return math.nan
    b = float(np.percentile(v, WORST_Q[cls]))
    if math.isfinite(onesided_value):
        b = min(b, onesided_value) if cls == CLASS_TRANSFER else max(b, onesided_value)
    return b


def whole_window_class(r_k: float, event_rs_except_k_k1: Sequence[float]) -> str | None:
    """Robustness: whole-window terciles of the event's traded intervals leaving intervals k and k + 1 out (features only); needs >= 6 values."""
    cuts = pre.trailing_cuts(list(event_rs_except_k_k1))
    return None if cuts is None else pre.c_class(r_k, cuts)


def r_lag(oi0: float, oi1: float, v_km2: float, v_km1: float) -> float:
    """OI-lag variant: ``(OI_k - OI_k-1) / (vol_k-1 - vol_k-2)`` (both known at k); nan when not defined."""
    if not all(math.isfinite(x) for x in (oi0, oi1, v_km2, v_km1)) or v_km1 - v_km2 <= 0:
        return math.nan
    return (oi1 - oi0) / (v_km1 - v_km2)


def stratum_c(u: dict) -> tuple:
    """Composition-guard stratum at the SELECTED level 2 (``|dm_int|`` {0.5-1c, > 1c}; ``u['abs_dm_c']`` = the mean |dm_int| over the qualifying members, part pre C_ABS_DM_RULE)."""
    return pre.stratum("C", STRATA_LEVEL_C, u)


def gate_gcu(oi_changed: int, traded: int) -> dict:
    s = oi_changed / traded if traded else 0.0
    ok = s >= GCU_MIN
    return {"share": s, "traded": int(traded), "pass": bool(ok), "label": None if ok else w.NOT_TESTABLE_FIELD}


def gate_gc(events_with_6_prior: int, units_with_6_prior: int) -> dict:
    ok = events_with_6_prior >= GC_EVENTS_MIN and units_with_6_prior >= GC_UNITS_MIN
    return {"events": int(events_with_6_prior), "units": int(units_with_6_prior), "pass": bool(ok), "label": None if ok else w.NOT_TESTABLE_POP}


def declared() -> dict:
    return {"version": C_VERSION, "strata": {"level": STRATA_LEVEL_C, "worn_shares": STRATA_WORN_SHARES, "source": LEVEL_SOURCE, "ladder": pre.LADDERS["C"]["levels"],
                                             "informativeness": pre.INFORMATIVENESS["three_class"], "abs_dm_rule": pre.C_ABS_DM_RULE, "window_rule": w.INFORMATIVE_MIN},
            "units": "(event, interval k) for non-sports arm-0 events in SCREEN_8 (arm-1 in REP_8); decision time = capture k's last-page received_utc",
            "eligibility": "captures k - 1, k consecutive and complete (gap 100-140 min); event OI and volume present in both; dV > 0; no member closed at k - 1 or k; no member end_date <= k + 3 h; "
                           ">= 1 qualifying member (eligible mids at k - 1 and k, |dm_int| >= 0.5c); nothing about k + 1",
            "state": {"r": "(OI_k - OI_k-1) / dV", "classes": pre.C_TRAILING_RECIPE, "min_prior": pre.TRAILING_MIN_PRIOR,
                      "trailing_window": {"screen": "[lookback floor, k)", "rep": "[S_8 + 7 d, k) of the arm-1 event, read as features"}, "dv_stratum": "the same prior intervals"},
            "target": {"C": "sign(dm_int) x 100 x (m_k+1 - m_k) cents per qualifying member; unit value = mean over members with an available mark",
                       "available": "capture k + 1 consecutive (gap 100-140 min) and the member row two-sided, spread <= 10c, mid in [0.03, 0.97], closed false",
                       "unavailable": f"'{UNAVAILABLE_MARK}' by class and reason {list(MARK_REASONS)}; never an exclusion; 60% availability rule",
                       "worst_case": "every unavailable member at the adverse bound (transfer min(p5, touch-C); mint-heavy and merge-heavy max(p95, touch-C), of available member C; touch-C is the one-sided k + 1 touch adverse to the hypothesis by class: adverse to continuation for transfer, favourable to continuation for mint / merge); sign kept"},
            "C1": {"estimator": "OLS of C on transfer and merge indicators (mint-heavy baseline) with event FE; coefficient on transfer; one-sided > 0; floor +0.5c",
                   "seeds": {"composition": w.SEEDS["C1_composition"], "calibration": w.SEEDS["C1_calibration"]},
                   "calibration": "circular shift of the class within event over its intervals in time order", "pre_interval": "C_pre = sign(dm_int) x (m_k-1 - m_k-2) on the classes; must not pass p < 0.01",
                   "attribution": list(C1_ATTRIBUTION), "robustness": list(C1_ROBUSTNESS), "top_dv_exclude": TOP_DV_EXCLUDE_SHARE},
            "gates": {"GCU": GCU_MIN, "GC": {"events": GC_EVENTS_MIN, "units": GC_UNITS_MIN}, "GCP": "C1's estimator on C_pre, SEs only; MDE > 1.0c -> not run (power)"},
            "econ": {"C1-econ": "REP_8 fills (CB13-T touch-consistent, pins) in arm-1 events with tau in (capture k, capture k + 1] after a classified interval: within-event difference of the CB13-T3 "
                                "round-trip net, after-transfer minus after-mint-heavy; primary <= -0.5c, after-transfer net <= -1.0c; p = max",
                     "minimum": f">= {ECON_MIN_FILLS} fills per class in >= {ECON_MIN_EVENTS} events, else not run (power)"},
            "taker_line": "C1 follow of transfer-interval moves at the decision capture ask/bid, exit at the adverse touch 2-4 h later; reported with the q0403 cell; never counted"}
