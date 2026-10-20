# ruff: noqa: E501
"""CB17 part ``pre`` rules (docs/research_lab/CREATIVE_BATCH_17.md section 10.4, items 1-6; section 1.4, 2.6, 2.7, CB17-A branch rule). Pure, outcome-free functions and declared constants.

Everything the four counts-only pre-censuses (q0400-q0403) decide by rule is fixed HERE, before q0400 runs:
1. worn inputs (paths, dates, the 2026-10-16T00:00Z cut-off, field whitelists: ``side`` for q0400's agreement count only, ``recv_ts`` for q0403 only);
2. the branch rule (overall agreement >= 97% with Wilson 95% lower bound >= 0.95 and n >= 800, and >= 97% in every touch-age band, price band and class with n >= 100; pass = branch S,
   otherwise branch T and family A is withdrawn uncounted) and the GAS rule text for SCREEN_8 (a window gate, not implemented as a job now);
3. the strata ladders (A, B1, B2, C), the informativeness definitions (binary, continuous, C's three-class rule) and the level-selection rule (finest level with worn-data share >= 60%, else 2);
4. the cut-point rules (B: global activity and imbalance tercile cut points fixed once from worn units; C: trailing terciles from at least 6 earlier traded intervals only);
5. the planning-SE recipe (SEs only, never a point estimate of any outcome proxy; ``MDE = 3.80 x SE``);
6. the cost-map grid (q0403: $1,000 and $5,000, depth bands 1c / 5c, fee rule).
The census I/O lives in ``cb17_census`` (also part ``pre``). Nothing here reads a mark, an outcome, a wallet or a later capture.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Sequence

import numpy as np

from . import cb17_common as c17

Refused = c17.Refused

# ---- item 2: the branch rule (CB17-A "Fill source and the branch rule"; findings 7, ruling 2) --------------------------------------------------------
AGREE_MIN_PCT = 97  # integer percent: k * 100 >= 97 * n (no float edge)
WILSON_Z = 1.959964  # 95% two-sided
WILSON_LOWER_MIN = 0.95
AGREE_N_MIN = 800
CELL_N_MIN = 100  # a band / class cell with n >= 100 must itself reach 97%; smaller cells are reported only
TOUCH_AGE_BANDS_S = ((0.0, 1200.0), (1200.0, 3600.0))  # 0-20 and 20-60 minutes: [lo, hi), the last band closed at 3600
TOUCH_AGE_BAND_NAMES = ("0-20min", "20-60min")
P_BAND_EDGES = (0.03, 0.20, 0.80, 0.97)  # [0.03, 0.20), [0.20, 0.80], (0.80, 0.97]
P_BAND_NAMES = ("P[0.03,0.20)", "P[0.20,0.80]", "P(0.80,0.97]")
BRANCH_S, BRANCH_T = "S", "T"
BRANCH_T_CONSEQUENCE = "family A is withdrawn uncounted before its part commit (CB15-L precedent); part A is never committed; q0407 builds E features only"
GAS_RULE_TEXT = ("GAS (signing gate; binding under branch S; window job q0408, NOT implemented in part pre): on SCREEN_8's touch-consistent subset (CB13-T's rule by pin) the same agreement rule must hold "
                 "(overall >= 97% with Wilson 95% lower bound >= 0.95 and n >= 800, and >= 97% in every touch-age band, price band and class with n >= 100); both the Data API side and the "
                 "touch-derived side are features, no mark is read; otherwise A1 is 'not testable (signing)', counted")
SIDE_BUY, SIDE_SELL = "BUY", "SELL"
SIDE_USE = ("q0400 reads the Data API side for two things only: the agreement count of the branch rule and the sign of the side-signed (S) population it builds for the strata shares and "
            "planning SEs; no other CB17 job reads it (section 1.4 whitelists)")
AGREEMENT_BASE = ("the base of the agreement rule is every non-sports CB13-T SCREEN fill that resolves to one traded token and one transaction (probe P1: 971); a fill whose resolved prints carry no "
                  "single BUY/SELL side counts as NON-agreement overall and in every cell (section 2.3: unknown never counts as met)")
# probe P1 (section 0.3): q0400 must reproduce these counts on the worn files before the branch is recorded
P1_EXPECTED = {"fills": 2931, "token_resolved": 2715, "ambiguous_transaction": 216, "non_sports": 1006, "non_sports_resolved": 971, "open": 676, "close": 295}
P1_NEXT_ACTION = "a mismatch is investigated, never adjusted; the branch is not recorded until it matches or the difference is explained"
SUPERSEDES = {"31656d5d388bf1df34358dfa7eec8e197ee5c39ce84ebc97d558be27615f6e0f": "second part-pre seal (de5c553a), replaced before any CB17 census ran, after the re-check: a P1 mismatch now nulls the branch fields and fails the job (exit 2); a blank side among a fill's prints is missing; rerun rule and q0403 lag disclosure",
              "c186fdcdf0b48fc073f19d2912adf2c29aa7de5af58a1bb0f37cdf0dbda27f8d": "first part-pre seal (cadaaf19), replaced before any CB17 census ran, after the freeze check: A informativeness on both-label cells, "
              "side-agreement base including unsigned fills, P1 reproduction flag, P1-faithful print reader, E later = 1-7 d, B clock-anomaly exclusion, path-key ways for S, disclosures"}

# ---- item 3: strata ladders, informativeness, level selection (section 2.6; finding 2) ----------------------------------------------------------------
SELECT_SHARE_MIN = 0.60  # finest level whose worn-data informativeness share is >= 60%, else level 2
WINDOW_SHARE_MIN = 0.50  # the window's own rule (unchanged by this selection)
SIZE_BAND_EDGES_USD = (2500.0, 10000.0)  # < $2.5k, $2.5-10k, >= $10k
SPREAD_BAND_EDGES = (0.01, 0.02, 0.05)  # <= 1c, (1,2], (2,5], > 5c  (price units)
SPREAD_2BAND_EDGE = 0.02  # <= 2c, > 2c
ABS_DM_BAND_EDGES_C = (1.0, 3.0)  # C: |dm_int| 0.5-1c, 1-3c, > 3c (cents)
ABS_DM_2BAND_EDGE_C = 1.0  # C level 2: 0.5-1c, > 1c
MOVING_BANDS = (1, 2)  # moving members {1, >= 2}
LADDERS = {
    "A": {"unit": "market x d", "label": "open", "kind": "binary",
          "levels": {0: "P band(3) x size band(3) x UTC 6h band(4) x spread band(4) = 144", 1: "P band(3) x spread {<=2c, >2c} = 6", 2: "P band(3)"}},
    "B1": {"unit": "token", "label": "old vs fresh", "kind": "binary",
           "levels": {0: "UTC 6h band(4) x spread band(4) x activity tercile(3) x reward programme(2) = 96", 1: "activity tercile(3) x UTC 12h band(2) x spread {<=2c, >2c} = 12", 2: "activity tercile(3)"}},
    "B2": {"unit": "token", "label": "x (continuous)", "kind": "continuous",
           "levels": {0: "UTC 6h band(4) x spread band(4) x activity tercile(3) x imbalance tercile(3) = 144", 1: "activity tercile(3) x imbalance tercile(3) = 9", 2: "imbalance tercile(3)"}},
    "C": {"unit": "event", "label": "transfer / mint-heavy / merge-heavy", "kind": "three_class",
          "levels": {0: "UTC 6h band(4) x |dm_int| band(3) x trailing dV tercile(3) x moving members {1, >=2}(2) = 72", 1: "|dm_int| band(3) x trailing dV 2-band(2) = 6", 2: "|dm_int| {0.5-1c, >1c} = 2"}},
}
INFORMATIVENESS = {
    "binary": "numerator = units in (unit x stratum) cells holding both labels; denominator = all units of the test (A: the units of A1, i.e. units in (market x d) cells holding both labels; B1: all old / fresh units)",
    "continuous": "numerator = units in (unit x stratum) cells with >= 2 units and x not constant in the cell; denominator = all B2 units",
    "three_class": "numerator = transfer and mint-heavy units in cells holding at least one transfer and one mint-heavy unit; denominator = all transfer and mint-heavy units (merge-heavy units are reported, not in the share)",
    "selection": "the finest level (0 finest) whose worn-data share >= 60%; if none, level 2 and the window's 50% rule binds; A's share is computed on the selected branch's population",
}
CLASS_TRANSFER, CLASS_MINT, CLASS_MERGE = "transfer", "mint", "merge"
C_ABS_DM_RULE = ("section 2.6 leaves open which member's |dm_int| places a multi-member event-interval in a band: part pre declares the MEAN of |dm_int| over the unit's qualifying members "
                 "(|dm_int| >= 0.5c), the same quantity at every level; the window part C may restate it but not change it")
IMBALANCE_AT = "second sweep"  # B2 imbalance (B5 - A5) / D1: depths of the pass's second sweep, D1 from the first sweep

# ---- item 4: cut-point rules (finding 6) ---------------------------------------------------------------------------------------------------------
TERCILE_QUANTILES = (1.0 / 3.0, 2.0 / 3.0)  # numpy 'linear' quantiles; a value <= the lower cut is tercile 0, <= the upper cut tercile 1, else 2
TRAILING_MIN_PRIOR = 6  # C: at least 6 earlier traded intervals, else "thin history"
B_ACTIVITY_RECIPE = "activity = pre-decision |dm| (cents) from the previous pass's first sweep to the decision sweep; global cut points (terciles) over worn non-sports eligible units; frozen in part B; never recomputed"
B_IMBALANCE_RECIPE = "imbalance = (B5 - A5) / D1 at the second sweep, D1 = depth_bid_5c + depth_ask_5c of the first sweep; global tercile cut points over worn non-sports touch-unchanged units; frozen in part B"
C_TRAILING_RECIPE = "cut points are the event's own terciles of r (and of dV) over its earlier traded intervals in the window; r_k, r_(k+1) and later never enter; fewer than 6 prior -> thin history, excluded and counted"

# ---- item 5: the planning-SE recipe (SEs only) --------------------------------------------------------------------------------------------------
SE_RECIPE = ("fixed-effect OLS of the pre-outcome proxy on the family's label/state, demeaned within the declared unit; cluster-robust CR1 sandwich per way; the written number is the SE of the "
             "tested coefficient, the max over ways with G >= 15 (CR2 / wild bootstrap belong to the window part); no point estimate of any proxy is returned or written; MDE = 3.80 x SE")
SE_G_MIN = 15
POWER_MDE_MAX_C = 1.0  # window power gate (2 x the 0.5c floor): reported as a flag, never a decision here
PROXIES = {"A": "pre-fill move d x (touch-capture mid - mid of the capture before it), cents", "E": "same, first-day versus later within market",
           "B1": "L_pre: excursion beyond the touch of two passes earlier, evaluated at the mid one pass earlier, on old vs fresh today",
           "B2": "dm_pre: previous pass's first-sweep mid to the decision mid, cents, on x / SD_x",
           "C": "C_pre = sign(dm_int) x (m_(k-1) - m_(k-2)), cents, on the transfer and merge indicators"}

# ---- item 6: the cost-map grid (q0403) ----------------------------------------------------------------------------------------------------------
COST_SIZES_USD = (1000.0, 5000.0)
COST_DEPTH_BANDS_C = (1, 5)  # the sweep's depth_*_1c / depth_*_5c share sums within 1c / 5c of the best level
LIQ_BAND_EDGES_USD = (10000.0, 100000.0)
FEE_UNKNOWN_RATE = 0.07  # max_if_unknown
COST_HIST_STEP_C = 0.1
COST_HIST_MAX_C = 100.0
COST_RECIPE = ("entry at the ask walked to the far edge of the lowest depth band that holds the position (1c band: ask + 1c; 5c band: ask + 5c; otherwise not executable within 5c), exit at the bid walked "
               "the same way; round-trip cost per share = (entry - exit) in cents plus the taker fee r x p x (1 - p) on both legs; an upper bound (EXECUTION_COSTS execution model)")
LAG_HIST_STEP_S = 60.0
LAG_HIST_MAX_S = 86400.0
LAG_THRESHOLDS_S = (300.0, 540.0, 7200.0)
LEVEL_BAND_EDGES = (4, 10)  # CH149: n_bid_levels + n_ask_levels <= 4, 5-10, > 10
ROUND_SIZE_MULTIPLE = 10.0  # CH148 inputs: a touch size is "round" iff both touch sizes are multiples of 10 shares
AGE_BIN_EDGES_S = (-5.0, 60.0, 600.0, 3600.0)  # <-5 clock anomaly, <60 fresh, 60-600, 600-3600, >3600
OLD_AGE_S, FRESH_AGE_S = 600.0, 60.0
PASS_GAP_S = 1800.0  # two consecutive sweeps whose start stamps are < 30 min apart form a pass
SPLIT_PASS_S = 300.0
MARK_WINDOW_S = (6600.0, 7800.0)  # the 2 h mark pass: first sweep with receipt in [t + 110, t + 130] min
PREV_PASS_MAX_GAP_S = 9000.0  # the previous pass must lie within 150 min
CAP_GAP_S = (6000.0, 8400.0)  # C: consecutive captures with last-page receipts 100-140 min apart
MEMBER_END_BUFFER_S = 3 * 3600.0
B_END_BUFFER_S = 4 * 3600.0
MAX_SPREAD = 0.10
MID_RANGE = (0.03, 0.97)
TOUCH_AGE_MAX_S = {"T": 3600.0, "S": 8100.0}  # branch T: 60 min (CB13-T rule); branch S: 135 min
MIN_MOVE_C = 0.5  # C qualifying member: |dm_int| >= 0.5c
FIRST_DAY_S = 86400.0

CENSUS_JOBS = {"q0400": "pre-census A/E", "q0401": "pre-census B", "q0402": "pre-census C", "q0403": "cost and lag map"}
SMOKE_NEEDS = ()


# =====================================================================================================================================================
# bands
# =====================================================================================================================================================


def p_band(p: float) -> int | None:
    """0: [0.03, 0.20), 1: [0.20, 0.80], 2: (0.80, 0.97]; None outside [0.03, 0.97]."""
    if not math.isfinite(p):
        return None
    if 0.03 <= p < 0.20:
        return 0
    if 0.20 <= p <= 0.80:
        return 1
    if 0.80 < p <= 0.97:
        return 2
    return None


def touch_age_band(age_s: float) -> int | None:
    if not math.isfinite(age_s) or age_s < 0:
        return None
    if age_s < TOUCH_AGE_BANDS_S[0][1]:
        return 0
    if age_s <= TOUCH_AGE_BANDS_S[1][1]:
        return 1
    return None


def size_band(usd: float) -> int:
    return 0 if usd < SIZE_BAND_EDGES_USD[0] else 1 if usd < SIZE_BAND_EDGES_USD[1] else 2


def spread_band(spread: float) -> int:
    """<= 1c, (1, 2], (2, 5], > 5c (price units; a tiny tolerance keeps float noise such as 0.020000000000000018 in the 1-2c band)."""
    s = spread - 1e-12
    return 0 if s <= SPREAD_BAND_EDGES[0] else 1 if s <= SPREAD_BAND_EDGES[1] else 2 if s <= SPREAD_BAND_EDGES[2] else 3


def spread_2band(spread: float) -> int:
    return 0 if spread - 1e-12 <= SPREAD_2BAND_EDGE else 1


def abs_dm_band(abs_dm_c: float) -> int:
    x = abs_dm_c - 1e-9  # float noise from mid differences x 100
    return 0 if x <= ABS_DM_BAND_EDGES_C[0] else 1 if x <= ABS_DM_BAND_EDGES_C[1] else 2


def abs_dm_2band(abs_dm_c: float) -> int:
    return 0 if abs_dm_c - 1e-9 <= ABS_DM_2BAND_EDGE_C else 1


def liq_band(liq: float) -> int | None:
    if not math.isfinite(liq):
        return None
    return 0 if liq < LIQ_BAND_EDGES_USD[0] else 1 if liq < LIQ_BAND_EDGES_USD[1] else 2


# =====================================================================================================================================================
# item 2: the branch rule
# =====================================================================================================================================================


def p1_reproduction(observed: dict) -> dict:
    """Compare q0400's fill-resolution counts with probe P1's (section 0.3). ``matches`` is the flag the branch depends on: the branch is recorded only when it is True (or the difference is explained)."""
    diffs = {k: {"expected": v, "observed": observed.get(k)} for k, v in P1_EXPECTED.items() if observed.get(k) != v}
    return {"expected": dict(P1_EXPECTED), "observed": dict(observed), "matches": not diffs, "differences": diffs, "next_action": P1_NEXT_ACTION,
            "flag": "P1 REPRODUCED" if not diffs else "P1 MISMATCH: investigate, do not adjust; the branch is not recorded"}


def wilson_lower(k: int, n: int, z: float = WILSON_Z) -> float:
    """Wilson score lower bound of a proportion k / n (0.0 for n = 0)."""
    if n <= 0:
        return 0.0
    ph = k / n
    den = 1.0 + z * z / n
    centre = ph + z * z / (2.0 * n)
    half = z * math.sqrt(ph * (1.0 - ph) / n + z * z / (4.0 * n * n))
    return (centre - half) / den


def agreement_rule(overall: dict, cells: dict[str, dict[str, dict]]) -> dict:
    """The side-agreement rule shared by the branch decision (q0400, worn CB13-T SCREEN fills) and GAS (SCREEN_8). ``overall`` = {n, k}; ``cells`` = {dimension: {cell name: {n, k}}} with the
    dimensions touch_age, p_band and class. Passes iff n >= 800, k/n >= 97% (exact integer test), Wilson lower bound >= 0.95, and EVERY cell with n >= 100 has k/n >= 97%; cells with n < 100
    are reported only. Missing or empty inputs fail."""
    n, k = int(overall.get("n", 0)), int(overall.get("k", 0))
    reasons: list[str] = []
    wl = wilson_lower(k, n)
    if n < AGREE_N_MIN:
        reasons.append(f"overall n {n} < {AGREE_N_MIN}")
    if n == 0 or k * 100 < AGREE_MIN_PCT * n:
        reasons.append(f"overall agreement {k}/{n} below {AGREE_MIN_PCT}%")
    if wl < WILSON_LOWER_MIN:
        reasons.append(f"Wilson lower bound {wl:.4f} < {WILSON_LOWER_MIN}")
    cell_out: dict[str, dict] = {}
    for dim in sorted(cells):
        for name in sorted(cells[dim]):
            c = cells[dim][name]
            cn, ck = int(c.get("n", 0)), int(c.get("k", 0))
            binding = cn >= CELL_N_MIN
            ok = (ck * 100 >= AGREE_MIN_PCT * cn) if binding else None
            cell_out[f"{dim}:{name}"] = {"n": cn, "agree": ck, "binding": binding, "ok": ok}
            if binding and not ok:
                reasons.append(f"cell {dim}:{name} agreement {ck}/{cn} below {AGREE_MIN_PCT}%")
    return {"pass": not reasons, "reasons": reasons, "overall": {"n": n, "agree": k, "wilson_lower": round(wl, 6)}, "cells": cell_out}


def branch_decision(overall: dict | None, cells: dict[str, dict[str, dict]] | None) -> dict:
    """q0400's branch: S iff the agreement rule passes, else T (family A withdrawn uncounted). A measurement that did not run (None) is branch T."""
    if overall is None or cells is None:
        return {"branch": BRANCH_T, "pass": False, "reasons": ["agreement measurement did not run"], "consequence": BRANCH_T_CONSEQUENCE}
    rule = agreement_rule(overall, cells)
    return {"branch": BRANCH_S if rule["pass"] else BRANCH_T, **rule, "consequence": None if rule["pass"] else BRANCH_T_CONSEQUENCE}


# =====================================================================================================================================================
# item 3: strata, informativeness, level selection
# =====================================================================================================================================================


def stratum(family: str, level: int, u: dict) -> tuple:
    """The stratum key of a unit at a ladder level. Unit features (all pre-outcome): A p, size_usd, ts, spread; B1 ts, spread, act (0-2), reward (0/1); B2 ts, spread, act, imb (0-2);
    C ts, abs_dm_c, dv_tercile (0-2), dv_above (0/1), n_moving."""
    if level not in (0, 1, 2):
        raise Refused(f"strata level {level!r}: one of 0, 1, 2")
    if family == "A":
        pb = p_band(u["p"])
        return (pb, size_band(u["size_usd"]), c17.band6(u["ts"]), spread_band(u["spread"])) if level == 0 else (pb, spread_2band(u["spread"])) if level == 1 else (pb,)
    if family == "B1":
        return (c17.band6(u["ts"]), spread_band(u["spread"]), u["act"], u["reward"]) if level == 0 else (u["act"], c17.utc_hour(u["ts"]) // 12, spread_2band(u["spread"])) if level == 1 else (u["act"],)
    if family == "B2":
        return (c17.band6(u["ts"]), spread_band(u["spread"]), u["act"], u["imb"]) if level == 0 else (u["act"], u["imb"]) if level == 1 else (u["imb"],)
    if family == "C":
        mv = 1 if u["n_moving"] <= 1 else 2
        return (c17.band6(u["ts"]), abs_dm_band(u["abs_dm_c"]), u["dv_tercile"], mv) if level == 0 else (abs_dm_band(u["abs_dm_c"]), u["dv_above"]) if level == 1 else (abs_dm_2band(u["abs_dm_c"]),)
    raise Refused(f"unknown family {family!r}")


def informativeness_binary(units: Iterable[tuple]) -> dict:
    """Units (cell key, label in {0, 1}); share = units in cells holding both labels / all units. One dict entry per cell (count << 2 | label mask) keeps memory flat."""
    cells: dict = {}
    for cell, lab in units:
        v = cells.get(cell, 0)
        cells[cell] = ((v >> 2) + 1) << 2 | (v & 3) | (2 if int(lab) else 1)
    total = sum(v >> 2 for v in cells.values())
    num_ = sum(v >> 2 for v in cells.values() if (v & 3) == 3)
    return {"numerator": num_, "denominator": total, "share": (num_ / total) if total else None}


def informativeness_continuous(units: Iterable[tuple]) -> dict:
    """Units (cell key, x); share = units in cells with >= 2 units and x not constant / all units."""
    cells: dict = {}
    for cell, x in units:
        x = float(x)
        c = cells.get(cell)
        cells[cell] = (1, x, x) if c is None else (c[0] + 1, min(c[1], x), max(c[2], x))
    total = sum(c[0] for c in cells.values())
    num_ = sum(c[0] for c in cells.values() if c[0] >= 2 and c[2] > c[1])
    return {"numerator": num_, "denominator": total, "share": (num_ / total) if total else None}


def informativeness_three_class(units: Iterable[tuple]) -> dict:
    """Units (cell key, class in {transfer, mint, merge}); the tested contrast is transfer versus mint-heavy: numerator = transfer and mint units in cells holding at least one of each,
    denominator = all transfer and mint units; merge-heavy units are counted and reported, outside the share."""
    cls: dict = {}
    merge = 0
    for cell, c in units:
        if c == CLASS_MERGE:
            merge += 1
            continue
        t = cls.get(cell, (0, 0))
        cls[cell] = (t[0] + 1, t[1]) if c == CLASS_TRANSFER else (t[0], t[1] + 1)
    den = sum(a + b for a, b in cls.values())
    num_ = sum(a + b for a, b in cls.values() if a > 0 and b > 0)
    return {"numerator": num_, "denominator": den, "share": (num_ / den) if den else None, "merge_units_reported": merge}


def informativeness(family: str, units: Iterable[tuple]) -> dict:
    kind = LADDERS[family]["kind"]
    return informativeness_binary(units) if kind == "binary" else informativeness_continuous(units) if kind == "continuous" else informativeness_three_class(units)


def select_level(shares: dict) -> dict:
    """The finest level (0 finest) whose worn-data share is >= 60%; if none (or a level has no share), level 2 and the window's 50% rule binds as declared."""
    for lv in (0, 1, 2):
        s = shares.get(lv)
        if s is not None and s >= SELECT_SHARE_MIN:
            return {"selected_level": lv, "reason": f"level {lv} share {s:.4f} >= {SELECT_SHARE_MIN}", "fallback": False}
    return {"selected_level": 2, "reason": f"no level reaches {SELECT_SHARE_MIN}; level 2 and the window's {WINDOW_SHARE_MIN} rule binds", "fallback": True}


def level_report(family: str, units, cell_of: Callable[[dict], object], label_of: Callable[[dict], object]) -> dict:
    """Informativeness share at levels 0, 1, 2 (features only) and the selected level. ``units`` is a sequence of feature dicts or a zero-argument callable returning a fresh iterable of
    them (so a large frame is never held as dicts); the cell key is (cell_of(u), stratum)."""
    shares: dict[int, float | None] = {}
    detail: dict[str, dict] = {}
    for lv in (0, 1, 2):
        it = units() if callable(units) else units
        res = informativeness(family, ((((cell_of(u), stratum(family, lv, u))), label_of(u)) for u in it))
        shares[lv] = res["share"]
        detail[f"level{lv}"] = res
    return {"family": family, "levels": detail, **select_level(shares)}


# =====================================================================================================================================================
# item 4: cut points
# =====================================================================================================================================================


def tercile_cuts(values: Iterable[float]) -> tuple[float, float] | None:
    """Global tercile cut points (numpy 'linear' quantiles) of finite values, or None when fewer than 3 values."""
    v = np.asarray([x for x in values if math.isfinite(x)], dtype=float)
    if v.size < 3:
        return None
    lo, hi = np.quantile(v, TERCILE_QUANTILES)
    return float(lo), float(hi)


def tercile_of(x: float, cuts: tuple[float, float]) -> int:
    return 0 if x <= cuts[0] else 1 if x <= cuts[1] else 2


def trailing_cuts(prior_values: Sequence[float]) -> tuple[float, float] | None:
    """C: terciles over an event's EARLIER traded intervals only (the caller never passes r_k or later); None ("thin history") with fewer than 6 prior."""
    pv = [x for x in prior_values if math.isfinite(x)]
    if len(pv) < TRAILING_MIN_PRIOR:
        return None
    return tercile_cuts(pv)


def c_class(r: float, cuts: tuple[float, float]) -> str:
    """mint-heavy above the upper cut, merge-heavy below the lower cut, transfer between (inclusive)."""
    return CLASS_MINT if r > cuts[1] else CLASS_MERGE if r < cuts[0] else CLASS_TRANSFER


def trailing_dv(prior_dv: Sequence[float], dv: float) -> tuple[int, int] | None:
    """(trailing dV tercile 0-2, above-trailing-median flag) of ``dv`` against the event's prior dV values (needs >= 6 prior)."""
    cuts = trailing_cuts(prior_dv)
    if cuts is None:
        return None
    med = float(np.median([x for x in prior_dv if math.isfinite(x)]))
    return tercile_of(dv, cuts), int(dv > med)


# =====================================================================================================================================================
# item 5: the planning-SE recipe (SEs only)
# =====================================================================================================================================================


def _demean(v: np.ndarray, g: np.ndarray, ng: int) -> np.ndarray:
    cnt = np.bincount(g, minlength=ng).astype(float)
    cnt[cnt == 0] = 1.0
    if v.ndim == 1:
        return v - (np.bincount(g, weights=v, minlength=ng) / cnt)[g]
    out = np.empty_like(v)
    for j in range(v.shape[1]):
        out[:, j] = v[:, j] - (np.bincount(g, weights=v[:, j], minlength=ng) / cnt)[g]
    return out


def _codes(a: Sequence) -> tuple[np.ndarray, int]:
    u = {k: i for i, k in enumerate(dict.fromkeys(a))}
    return np.fromiter((u[k] for k in a), dtype=np.int64, count=len(a)), len(u)


def fe_cluster_se(y: Sequence[float], x: Sequence[Sequence[float]] | Sequence[float], fe: Sequence, ways: dict[str, Sequence], *, coef: int = 0) -> dict:
    """SE of coefficient ``coef`` in a fixed-effect OLS of ``y`` on ``x`` (fe = the unit identifier demeaned out), CR1 cluster-robust per way. Returns SEs, cluster counts and the MDE ONLY:
    the fitted coefficient is used internally and never returned (unit-tested: no point estimate of any proxy leaves this function). A way with fewer than ``SE_G_MIN`` clusters is
    reported but kept out of the max."""
    yv = np.asarray(y, dtype=float)
    X = np.asarray(x, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    ok = np.isfinite(yv) & np.all(np.isfinite(X), axis=1)
    fe_l = [f for f, o in zip(fe, ok, strict=True) if o]
    yv, X = yv[ok], X[ok]
    n = int(yv.size)
    out: dict = {"n": n, "se": None, "mde": None, "se_by_way": {}, "g_by_way": {}, "recipe": "cb17-planning-se-v1"}
    if n < 3:
        return out
    g, ng = _codes(fe_l)
    yd, Xd = _demean(yv, g, ng), _demean(X, g, ng)
    xtx = Xd.T @ Xd
    if np.linalg.matrix_rank(xtx) < X.shape[1]:
        return {**out, "note": "rank deficient after fixed effects (no within-unit variation)"}
    inv = np.linalg.inv(xtx)
    e = yd - Xd @ (inv @ (Xd.T @ yd))
    k = X.shape[1]
    ses: dict[str, float] = {}
    for way, cl in ways.items():
        cl_l = [c for c, o in zip(cl, ok, strict=True) if o]
        cg, gn = _codes(cl_l)
        out["g_by_way"][way] = gn
        if gn < 2:
            continue
        scores = Xd * e[:, None]
        sums = np.zeros((gn, k))
        for j in range(k):
            sums[:, j] = np.bincount(cg, weights=scores[:, j], minlength=gn)
        meat = sums.T @ sums
        corr = (gn / (gn - 1.0)) * ((n - 1.0) / max(n - ng - k + 1.0, 1.0))
        v = corr * (inv @ meat @ inv)
        ses[way] = float(math.sqrt(max(v[coef, coef], 0.0)))
    out["se_by_way"] = {w: round(s, 6) for w, s in ses.items()}
    counted = {w: s for w, s in ses.items() if out["g_by_way"][w] >= SE_G_MIN}
    if counted:
        se = max(counted.values())
        out["se"] = round(se, 6)
        out["mde"] = round(c17.MDE_FACTOR * se, 6)
        out["mde_over_power_gate"] = bool(c17.MDE_FACTOR * se > POWER_MDE_MAX_C)
    else:
        out["note"] = f"no way has G >= {SE_G_MIN}"
    return out


# =====================================================================================================================================================
# item 6: the cost-map recipe
# =====================================================================================================================================================


def walk_edge(shares: float, d1: float, d5: float) -> float | None:
    """The far edge (price units) of the lowest depth band that holds ``shares``; None if the position does not fit within 5c."""
    if not (math.isfinite(shares) and shares > 0):
        return None
    if math.isfinite(d1) and shares <= d1:
        return COST_DEPTH_BANDS_C[0] / 100.0
    if math.isfinite(d5) and shares <= d5:
        return COST_DEPTH_BANDS_C[1] / 100.0
    return None


def round_trip_cost_c(bid: float, ask: float, d_ask_1c: float, d_ask_5c: float, d_bid_1c: float, d_bid_5c: float, usd: float, fee_rate: float) -> float | None:
    """Upper-bound executable round trip per share, cents (COST_RECIPE); None when not executable within the 5c band on either side or on a crossed / one-sided book."""
    if not (math.isfinite(bid) and math.isfinite(ask) and 0.0 < bid < ask < 1.0):
        return None
    shares = usd / ask
    e_in, e_out = walk_edge(shares, d_ask_1c, d_ask_5c), walk_edge(shares, d_bid_1c, d_bid_5c)
    if e_in is None or e_out is None:
        return None
    p_in, p_out = min(ask + e_in, 0.999), max(bid - e_out, 0.001)
    r = fee_rate if math.isfinite(fee_rate) and fee_rate >= 0 else FEE_UNKNOWN_RATE
    return 100.0 * ((p_in - p_out) + r * p_in * (1.0 - p_in) + r * p_out * (1.0 - p_out))


class Hist:
    """Fixed-bin histogram with exact-to-the-bin quantiles (streaming; no value list is kept)."""

    def __init__(self, step: float, vmax: float):
        self.step, self.vmax = step, vmax
        self.bins = np.zeros(int(vmax / step) + 2, dtype=np.int64)
        self.n = 0

    def add(self, v: float) -> None:
        if not math.isfinite(v):
            return
        i = int(min(max(v, 0.0), self.vmax + self.step) / self.step)
        self.bins[min(i, self.bins.size - 1)] += 1
        self.n += 1

    def quantile(self, q: float) -> float | None:
        if self.n == 0:
            return None
        c = np.cumsum(self.bins)
        i = int(np.searchsorted(c, q * self.n, side="left"))
        return round(min(i, self.bins.size - 1) * self.step, 6)

    def share_gt(self, v: float) -> float | None:
        if self.n == 0:
            return None
        i = int(v / self.step)
        return round(float(self.bins[i + 1 :].sum()) / self.n, 6)

    def summary(self) -> dict:
        return {"n": self.n, "p25": self.quantile(0.25), "median": self.quantile(0.5), "p75": self.quantile(0.75), "p90": self.quantile(0.9)}


def declared() -> dict:
    return {"item_1_worn_inputs": {"cb13_t_screen": ["creative_batch13/t_screen/fills.csv.gz", "creative_batch13/t_screen/labels.csv.gz"], "monitor": "live_trades/trades-2026101{2..5}.jsonl",
                                   "sweeps": "book_sweeps/<stamp> with start in [2026-10-12, 2026-10-16)", "captures": "snapshots/<stamp> with start in [2026-10-11T22Z, 2026-10-16) (q0400 touch lookback) / [2026-10-12, 2026-10-16)",
                                   "created_at_captures": ["20261012T003103Z_2df48d64", "20261015T223102Z_2eae9aa6"], "cutoff": c17.CENSUS_CUTOFF},
            "item_2_branch_rule": {"agree_min_pct": AGREE_MIN_PCT, "wilson_lower_min": WILSON_LOWER_MIN, "n_min": AGREE_N_MIN, "cell_n_min": CELL_N_MIN, "bands": {"touch_age": list(TOUCH_AGE_BAND_NAMES), "p": list(P_BAND_NAMES), "class": "LABELLER class"},
                                   "pass": BRANCH_S, "fail_or_not_run": BRANCH_T, "consequence_T": BRANCH_T_CONSEQUENCE, "gas": GAS_RULE_TEXT},
            "item_2_wording": {"side_use": SIDE_USE, "agreement_base": AGREEMENT_BASE, "p1_expected": P1_EXPECTED, "p1_next_action": P1_NEXT_ACTION},
            "disclosures": {"static_index": "end_date, liquidity, sports flag, reward, fee fields and series slug come from the FIRST worn capture carrying the market (CB13 load_quote_index precedent), not the capture at the decision",
                            "created_at_unknown": "first-day age uses created_at of two pinned captures (2026-10-12T00:31:03Z and 2026-10-15T22:31:02Z); a market created after the first and gone before the second has no created_at and is counted 'unknown' (a bias against newly created, short-lived markets)",
                            "s_planning_se_path_key": "S units carry CB13's path key where derivable from the print alone (the underlying of a PATH-SETTLED title, else 'event:<event id>'); the sidecar first-series-slug branch of CB13's key is not read by q0400 (series_slugs is not loaded), a declared deviation; SEs only",
                            "s_pre_fill_gap": "the S pre-fill proxy uses the capture before the touch capture whatever its age (no gap limit), as CB13-T's prev_mid does; SEs only",
                            "first_day_bins": "first day = age < 24 h; later = 1-7 d; > 7 d, negative and unknown ages are in neither group",
                            "b_clock_anomaly": "B units with a book age < -5 s or no stamp are excluded from the units, the cut points and B2 and counted (section 2.2)"},
            "rerun_rule": ("after a P1 mismatch the result is written with branch fields null and the job exits 2 (failed, investigated, never retried blindly); once the difference is explained a rerun writes "
                           "to a NEW declared output path (e.g. pre_census_A_v2.json) with --supersedes <earlier file>; the earlier file is kept and its sha256 recorded (CB13 smoke_R_v2 precedent)"),
            "q0403_lag_population": "the receipt-lag population includes prints with no usable price or size (the reader keeps them since the P1 fix); lag needs only ts and recv_ts, so this adds counts and no bias",
            "partly_missing_side": "a fill (or transaction) with any blank or unknown side among its prints is 'missing': non-agreement, and not signed in the S population (section 2.3, the conservative reading)",
            "supersedes": SUPERSEDES,
            "item_3_strata": {"ladders": {k: v["levels"] for k, v in LADDERS.items()}, "informativeness": INFORMATIVENESS, "c_abs_dm_rule": C_ABS_DM_RULE, "select_share_min": SELECT_SHARE_MIN, "window_share_min": WINDOW_SHARE_MIN},
            "item_4_cut_points": {"b_activity": B_ACTIVITY_RECIPE, "b_imbalance": B_IMBALANCE_RECIPE, "c_trailing": C_TRAILING_RECIPE, "min_prior": TRAILING_MIN_PRIOR},
            "item_5_planning_se": {"recipe": SE_RECIPE, "proxies": PROXIES, "ways": "A/E: event, path key x 6h block, 6h block; B/C: event, first series slug (else event) x 6h block, 6h block, UTC hour"},
            "item_6_cost_map": {"sizes_usd": list(COST_SIZES_USD), "depth_bands_c": list(COST_DEPTH_BANDS_C), "liq_band_edges_usd": list(LIQ_BAND_EDGES_USD), "recipe": COST_RECIPE, "fee_unknown_rate": FEE_UNKNOWN_RATE},
            "jobs": dict(CENSUS_JOBS), "counts_only": True, "no_outcome": "no mark, outcome, resolution, wallet or later capture is read; the only post-decision field is static created_at"}
