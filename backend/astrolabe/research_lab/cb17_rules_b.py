# ruff: noqa: E501
"""CB17 rules part ``B`` (docs/research_lab/CREATIVE_BATCH_17.md section CB17-B, 11.2): the book's own clocks. B1 book age (CH146), B2 the breathing book (CH147).

Declarations and small pure definitions only (the frame builder, estimators and the runner are window code, pinned at the code freeze). Filled from q0401 (``pre_census_B.json``,
sha256 ``c3b8ae1b…``) by part ``pre``'s rules, as the design said: the GLOBAL activity and imbalance tercile cut points (verbatim, float32 values; never recomputed on SCREEN_8 or REP_8)
and the selected strata levels (B1 = 2 after the fallback, B2 = 1). Everything else is section CB17-B's text: eligibility (decision sweep and earlier rows only), the age state, the 2 h
excursion beyond the touch (adverse movement only, not a maker net), the shift state ``x`` and its SCREEN_8-frozen ``SD_x``, the 2 h / 6 h sweep marks, the capture mark, the no-mark
worst case, the gates GBT / GBA / GBS / GB1P / GB2P, the robustness list and the econ rules B1-econ / B2-econ.
"""

from __future__ import annotations

import math

import numpy as np

from . import cb17_common as c17
from . import cb17_pre as pre
from . import cb17_wcommon as w

Refused = c17.Refused

B_VERSION = "cb17-B-v1"

# ---- frozen from q0401 (section 11.2) ----------------------------------------------------------------------------------------------------------------
ACTIVITY_CUTS_C = (0.0, 0.10000000149011612)  # cut_points.activity_terciles_c, verbatim
IMBALANCE_CUTS = (-0.021718762814998627, 0.4006465971469879)  # cut_points.imbalance_terciles, verbatim
CUTS_SOURCE = {"job": "q0401", "file": "creative_batch17/pre_census_B.json", "sha256": "c3b8ae1b0f8d0bb7b54126193371e479c9175078591ebd46bb990d36ef063a1a", "units": 545355, "b2_units": 481657,
               "recipe": [pre.B_ACTIVITY_RECIPE, pre.B_IMBALANCE_RECIPE]}
FEATURE_DTYPE = "float32"  # q0401 stored activity and imbalance as float32; the window casts both before comparing (O6)
STRATA_LEVEL = {"B1": 2, "B2": 1}
STRATA_WORN_SHARES = {"B1": {"level0": 0.02970675244228269, "level1": 0.052776312733728785, "level2": 0.08632473623781028, "fallback": True},
                      "B2": {"level0": 0.3341880217665268, "level1": 0.6029747309807602, "level2": 0.6733505378308631, "fallback": False}}
SD_X_WORN_REPORTED = 0.08671511  # reported only: SD_x is the pooled SD over SCREEN_8 units, frozen for REP_8

# ---- states, targets and marks (section CB17-B) ------------------------------------------------------------------------------------------------------
STATE_OLD, STATE_FRESH, STATE_MID, STATE_ANOMALY = "old", "fresh", "mid", "clock anomaly"
MARK_2H_S = pre.MARK_WINDOW_S  # [t + 110, t + 130] min: the token's first sweep of the first pass with receipt there
MARK_6H_S = (350 * 60.0, 370 * 60.0)  # robustness
CAPTURE_MARK_S = (2 * 3600.0, 4 * 3600.0)  # the CB13 capture mark: first complete capture with last-page received_utc >= t + 2 h, usable iff <= t + 4 h
MARK_OK, NO_MARK, WIDE_MARK, TICK_CHANGE = "ok", "no mark", "wide mark", "tick change"
EXCLUSIONS = ("clock anomaly", "not two-sided", "wide or extreme", "end too near", "no previous pass", "split pass", "sports", "arm 1 (REP)", "election night", "dropped: key",
              "unavailable (lookback floor)", "touch changed (B2)", "no depth (B2)")
NO_MARK_RULE = ("eligibility uses the decision sweep and earlier rows only; a token absent from the mark pass or one-sided there is 'no mark' (availability, counted by state bin); "
                "a mark spread > 10c is 'wide mark' (counted; worst case); a tick size different at the mark is 'tick change' (excluded and counted, as declared; O9)")

# ---- worst case (finding 4, binding robustness) ------------------------------------------------------------------------------------------------------
WORST_FRESH_Q = 95.0  # B1: no-mark / wide-mark units with no capture mark: old L = 0, fresh the 95th percentile of available fresh-bin L
WORST_B2_Q = {"pos": 5.0, "neg": 95.0}  # B2: x > 0 the 5th, x < 0 the 95th percentile of available dm; x = 0 gets 0

# ---- gates (section CB17-B) --------------------------------------------------------------------------------------------------------------------------
GBT_SAME_MIN = 0.99  # hash unchanged => stamp unchanged
GBT_CHANGED_MIN = 0.95  # hash changed => stamp changed
GBA_BIN_SHARE_MIN = 0.05
GBA_TOKENS_MIN = 1000
GBA_EVENTS_MIN = 300
GBS_SHIFT_SHARE_MIN = 0.20
GBS_UNITS_MIN = 50000
GBS_EVENTS_MIN = 300

# ---- robustness and labels ---------------------------------------------------------------------------------------------------------------------------
OLD_CUT_ALTS_S = (300.0, 1800.0)  # fresh fixed at < 60 s
AGE_EXCLUDE_ABOVE_S = 3600.0
MID_ROBUST = (0.10, 0.90)
CONCENTRATION_TOP = 5
CONCENTRATION_SHARE = 0.30
LABEL_B1 = "adverse movement only; not a maker net and not a maker loss"
LABEL_CONCENTRATED = "concentrated"
B1_ROBUSTNESS = ("no-mark worst case", "capture mark", "old cut 300 s", "old cut 1800 s", "exclude a > 3600 s", "ask-crossing component", "bid-crossing component", "relative L / (a0 - b0)",
                 "decision mid in [0.10, 0.90]", "6 h mark", "top-5 drops", "leave-one-day-out")
B2_ROBUSTNESS = ("no-mark worst case", "s != 0 only", "no monitor print in the market between the two sweeps", "unchanged touch sizes", "capture mark", "6 h mark", "top-5 drops",
                 "leave-one-day-out")
B1_ATTRIBUTION = ("spread band", "activity", "log liquidity", "volume24hr band", "reward programme present", "n_levels band", "UTC 6 h band", "decision mid band", "hash changed since the previous pass",
                  "touch grain (sub-cent or not)")
B2_ATTRIBUTION = ("dm_pre", "imbalance level", "spread band", "n_levels change", "touch-size change", "activity", "UTC 6 h band")

# ---- econ (Stage 2, REP_8 arm-1 events; fill source under branch T = CB13-T touch-consistent fills by pin) -------------------------------------------
ECON_B1_SWEEP_LOOKBACK_S = 1800.0  # the token's LATEST sweep with receipt in [tau - 30 min, tau) gives the book age at the fill (O10)
ECON_B2_HORIZON_S = 7200.0  # fills with tau in (t, t + 2 h] after the most recent pass with |x| >= SD_x (O10)
ECON_MIN_FILLS = 300
ECON_MIN_EVENTS = 60


# =====================================================================================================================================================
# definitions
# =====================================================================================================================================================


def f32(x: float) -> float:
    """The float32 value q0401 stored (activity, imbalance), as a Python float."""
    return float(np.float32(x)) if math.isfinite(float(x)) else math.nan


def book_age_s(receipt_epoch: float, book_timestamp_ms: float) -> float:
    """``a = batch_receipt_utc - book_timestamp / 1000`` (seconds)."""
    r, b = float(receipt_epoch), float(book_timestamp_ms)
    return r - b / 1000.0 if math.isfinite(r) and math.isfinite(b) else math.nan


def age_state(a: float, old_cut_s: float = pre.OLD_AGE_S) -> str:
    """``a < -5 s`` (or no stamp) clock anomaly; ``a < 60 s`` fresh; ``a >= old_cut`` (600 s) old; otherwise mid (reported only)."""
    if not math.isfinite(a) or a < pre.AGE_BIN_EDGES_S[0]:
        return STATE_ANOMALY
    if a < pre.FRESH_AGE_S:
        return STATE_FRESH
    if a >= old_cut_s:
        return STATE_OLD
    return STATE_MID


def activity_c(mid_now: float, mid_prev_pass: float) -> float:
    """Pre-decision activity ``|dm|`` (cents) from the previous pass's first sweep to the decision sweep."""
    return abs(mid_now - mid_prev_pass) * 100.0 if math.isfinite(mid_now) and math.isfinite(mid_prev_pass) else math.nan


def activity_tercile(act_c: float) -> int:
    return pre.tercile_of(f32(act_c), ACTIVITY_CUTS_C)


def imbalance_tercile(imb: float) -> int:
    return pre.tercile_of(f32(imb), IMBALANCE_CUTS)


def excursion_L(b0: float, a0: float, m_h: float) -> float:
    """B1's target, the 2 h excursion beyond the touch: ``L = 100 [max(0, m_h - a0) + max(0, b0 - m_h)]`` cents (adverse movement only)."""
    if not (math.isfinite(b0) and math.isfinite(a0) and math.isfinite(m_h)):
        return math.nan
    return 100.0 * (max(0.0, m_h - a0) + max(0.0, b0 - m_h))


def shift_state(s1: dict, s2: dict) -> dict | None:
    """B2's state for one pass: None unless ``best_bid`` and ``best_ask`` are identical (as recorded strings) in both sweeps. ``s = [(A5 - A1) - (B5 - B1)]_2 - [(A5 - A1) - (B5 - B1)]_1``
    (shares), ``x = -s / D1`` clipped to [-1, 1] with ``D1`` the first sweep's ``depth_bid_5c + depth_ask_5c``; ``s = 0`` stays in (``x = 0``). The imbalance level is
    ``(B5 - A5) / D1`` at the SECOND sweep (part pre ``IMBALANCE_AT``). Keys of s1 / s2: bid_s, ask_s, db1, db5, da1, da5."""
    if s1["bid_s"] != s2["bid_s"] or s1["ask_s"] != s2["ask_s"]:
        return None
    sa = (s2["da5"] - s2["da1"]) - (s1["da5"] - s1["da1"])
    sb = (s2["db5"] - s2["db1"]) - (s1["db5"] - s1["db1"])
    s = sa - sb
    d1 = s1["db5"] + s1["da5"]
    if not (math.isfinite(s) and math.isfinite(d1) and d1 > 0):
        return {"s": s, "x": math.nan, "imb": math.nan, "ok": False}
    return {"s": s, "x": max(-1.0, min(1.0, -s / d1)), "imb": (s2["db5"] - s2["da5"]) / d1, "ok": True}


def stratum_b(family: str, u: dict) -> tuple:
    """The composition-guard stratum at the SELECTED level (B1 level 2, B2 level 1); ``u`` carries ts, spread, act (tercile), reward and (B2) imb (tercile)."""
    if family not in STRATA_LEVEL:
        raise Refused(f"unknown B family {family!r}")
    return pre.stratum(family, STRATA_LEVEL[family], u)


def mark_status(dec: dict, mk: dict | None) -> str:
    """The 2 h (or 6 h) sweep mark of an eligible decision: absent or one-sided -> no mark; spread > 10c -> wide mark; tick size different from the decision -> tick change; else ok."""
    if mk is None or not mk.get("two_sided"):
        return NO_MARK
    if mk["ask"] - mk["bid"] > pre.MAX_SPREAD + 1e-12:
        return WIDE_MARK
    t0, t1 = dec.get("tick"), mk.get("tick")
    if t0 is not None and t1 is not None and math.isfinite(t0) and math.isfinite(t1) and abs(t0 - t1) > 1e-12:
        return TICK_CHANGE
    return MARK_OK


def worst_b1(is_old: bool, fresh_available_L: np.ndarray) -> float:
    """B1's adverse bound for a no-mark / wide-mark unit with no capture mark: old units L = 0 (the minimum), fresh units the 95th percentile of available fresh-bin L."""
    if is_old:
        return 0.0
    v = np.asarray(fresh_available_L, float)
    v = v[np.isfinite(v)]
    return float(np.percentile(v, WORST_FRESH_Q)) if v.size else math.nan


def worst_b2(x: float, available_dm: np.ndarray) -> float:
    """B2's adverse bound: x > 0 the 5th percentile, x < 0 the 95th percentile of available dm, x = 0 gets 0."""
    if x == 0:
        return 0.0
    v = np.asarray(available_dm, float)
    v = v[np.isfinite(v)]
    if not v.size:
        return math.nan
    return float(np.percentile(v, WORST_B2_Q["pos"] if x > 0 else WORST_B2_Q["neg"]))


def gate_gbt(hash_same: int, hash_same_stamp_same: int, hash_changed: int, hash_changed_stamp_changed: int) -> dict:
    """GBT (field semantics): hash unchanged => stamp unchanged in >= 99% and hash changed => stamp changed in >= 95% of SCREEN_8 intra-pass pairs; else B1 not testable."""
    a = hash_same_stamp_same / hash_same if hash_same else None
    b = hash_changed_stamp_changed / hash_changed if hash_changed else None
    ok = a is not None and b is not None and a >= GBT_SAME_MIN and b >= GBT_CHANGED_MIN
    return {"same_share": a, "changed_share": b, "pass": bool(ok), "label": None if ok else w.NOT_TESTABLE_SEMANTICS}


def gate_gba(n_old: int, n_fresh: int, n_eligible: int, tokens_both: int, events_both: int) -> dict:
    """GBA (population): old and fresh each >= 5% of eligible units; >= 1,000 arm-0 tokens holding both bins; >= 300 events among them."""
    so = n_old / n_eligible if n_eligible else 0.0
    sf = n_fresh / n_eligible if n_eligible else 0.0
    ok = so >= GBA_BIN_SHARE_MIN and sf >= GBA_BIN_SHARE_MIN and tokens_both >= GBA_TOKENS_MIN and events_both >= GBA_EVENTS_MIN
    return {"old_share": so, "fresh_share": sf, "tokens_both": int(tokens_both), "events_both": int(events_both), "pass": bool(ok), "label": None if ok else w.NOT_TESTABLE_POP}


def gate_gbs(n_touch_unchanged: int, n_shifted: int, events_shifted: int) -> dict:
    """GBS (population): among eligible touch-unchanged pairs s != 0 in >= 20%; >= 50,000 units with s != 0 in >= 300 events."""
    sh = n_shifted / n_touch_unchanged if n_touch_unchanged else 0.0
    ok = sh >= GBS_SHIFT_SHARE_MIN and n_shifted >= GBS_UNITS_MIN and events_shifted >= GBS_EVENTS_MIN
    return {"shifted_share": sh, "shifted_units": int(n_shifted), "events": int(events_shifted), "pass": bool(ok), "label": None if ok else w.NOT_TESTABLE_POP}


def concentration_share(x: np.ndarray, events: np.ndarray) -> float:
    """Share of sum(x^2) carried by the top 5 events (B2's concentration label at > 30%)."""
    x2 = np.asarray(x, float) ** 2
    ev = np.asarray(events)
    tot = float(x2.sum())
    if tot <= 0:
        return 0.0
    _, codes = np.unique(ev, return_inverse=True)
    sums = np.sort(np.bincount(codes, weights=x2))[::-1]
    return float(sums[:CONCENTRATION_TOP].sum() / tot)


def econ_b1_bin(age_at_latest_sweep: float) -> str | None:
    """B1-econ: a fill into an old book (a >= 600 s) or a fresh one (a < 60 s) at the token's latest sweep in [tau - 30 min, tau); otherwise not in the contrast."""
    st = age_state(age_at_latest_sweep)
    return st if st in (STATE_OLD, STATE_FRESH) else None


def econ_b2_abandoned(x_recent: float, sd_x: float, d: int) -> bool | None:
    """B2-econ: after the most recent pass with |x| >= SD_x (t < tau <= t + 2 h), the fill is abandoned-side iff the maker sold YES when x > 0 (d = -1) or bought YES when x < 0
    (d = +1); None when no such pass."""
    if not (math.isfinite(x_recent) and math.isfinite(sd_x) and sd_x > 0 and abs(x_recent) >= sd_x):
        return None
    return bool((x_recent > 0 and d == -1) or (x_recent < 0 and d == 1))


def declared() -> dict:
    return {"version": B_VERSION, "cut_points": {"activity_c": list(ACTIVITY_CUTS_C), "imbalance": list(IMBALANCE_CUTS), "source": CUTS_SOURCE, "dtype": FEATURE_DTYPE,
                                                 "assignment": "value <= lower -> 0; <= upper -> 1; else 2 (part pre tercile_of)", "frozen": "never recomputed on SCREEN_8 or REP_8"},
            "strata": {"levels": STRATA_LEVEL, "worn_shares": STRATA_WORN_SHARES, "ladders": {k: pre.LADDERS[k]["levels"] for k in ("B1", "B2")},
                       "informativeness": {"B1": pre.INFORMATIVENESS["binary"], "B2": pre.INFORMATIVENESS["continuous"]}, "window_rule": w.INFORMATIVE_MIN},
            "units": "(token, pass) for outcome-0 tokens in the sweep universe of arm-0 events (SCREEN_8) / arm-1 events (REP_8), non-sports by the sidecar rule; binary; end unknown or > 3 h",
            "eligibility": {"decision": "two-sided, spread <= 10c, mid in [0.03, 0.97], sidecar end_date >= t + 4 h, a previous pass within 150 min (activity), decision sweep and earlier rows only",
                            "pass": "two consecutive sweep directories < 30 min apart; a token pair > 5 min apart is split pass", "t": {"B1": "first sweep's batch_receipt_utc", "B2": "second sweep's batch_receipt_utc"},
                            "clock": "a < -5 s clock anomaly, excluded and counted", "exclusions": list(EXCLUSIONS)},
            "B1": {"state": "old iff a >= 600 s; fresh iff a < 60 s; 60-600 s reported only", "target": "L = 100 [max(0, m_h - a0) + max(0, b0 - m_h)] cents", "label": LABEL_B1,
                   "estimator": "OLS of L on old with token FE; one-sided > 0; floor +0.5c", "seeds": {"composition": w.SEEDS["B1_composition"], "calibration": w.SEEDS["B1_calibration"]},
                   "pre_period": "L_pre from the touch two passes earlier and the mid one pass earlier, on today's old; must not pass p < 0.01 in the hypothesised direction",
                   "attribution": list(B1_ATTRIBUTION), "robustness": list(B1_ROBUSTNESS), "old_cut_alts_s": list(OLD_CUT_ALTS_S)},
            "B2": {"state": "x = -s / D1 clipped to [-1, 1]; units with identical best_bid and best_ask in both sweeps; s = 0 kept", "target": "dm = 100 (m_h - m_0) cents",
                   "estimator": "OLS of dm on x / SD_x with token FE; one-sided > 0; floor +0.5c per SD", "sd_x": "pooled SD over SCREEN_8 units, written to the SCREEN_8 result, frozen for REP_8",
                   "seeds": {"composition": w.SEEDS["B2_composition"], "calibration": w.SEEDS["B2_calibration"]},
                   "pre_sweep": "dm_pre (previous pass's first-sweep mid -> m_0) on x: must not pass p < 0.01 in the hypothesised direction (binding, ruling 5)",
                   "attribution": list(B2_ATTRIBUTION), "robustness": list(B2_ROBUSTNESS), "concentration": f"top {CONCENTRATION_TOP} events > {CONCENTRATION_SHARE} of sum x^2 -> '{LABEL_CONCENTRATED}'"},
            "marks": {"2h_s": list(MARK_2H_S), "6h_s": list(MARK_6H_S), "capture_s": list(CAPTURE_MARK_S), "no_mark": NO_MARK_RULE,
                      "worst_case": {"B1": f"capture mark first; else old L = 0, fresh p{WORST_FRESH_Q:g} of available fresh L", "B2": f"capture mark first; else x > 0 p{WORST_B2_Q['pos']:g}, x < 0 p{WORST_B2_Q['neg']:g} of available dm, x = 0 -> 0"}},
            "gates": {"GBT": {"same_min": GBT_SAME_MIN, "changed_min": GBT_CHANGED_MIN}, "GBA": {"bin_share_min": GBA_BIN_SHARE_MIN, "tokens_min": GBA_TOKENS_MIN, "events_min": GBA_EVENTS_MIN},
                      "GBS": {"shift_share_min": GBS_SHIFT_SHARE_MIN, "units_min": GBS_UNITS_MIN, "events_min": GBS_EVENTS_MIN},
                      "GB1P": "B1's estimator on L_pre, SEs only; MDE > 1.0c -> not run (power)", "GB2P": "B2's estimator on dm_pre, SEs only; MDE > 1.0c per SD -> not run (power)"},
            "econ": {"B1-econ": "within-market difference of the CB13-T3 round-trip net, old minus fresh, at the token's latest sweep in [tau - 30 min, tau); primary <= -0.5c, old-book net <= -1.0c; p = max",
                     "B2-econ": "fills with tau in (t, t + 2 h] after the most recent pass with |x| >= SD_x; abandoned-side minus the market's other REP_8 fills; primary <= -0.5c, abandoned net <= -1.0c; p = max",
                     "minimum": f">= {ECON_MIN_FILLS} fills per bin in >= {ECON_MIN_EVENTS} events, else not run (power)", "fill_source": "branch T: CB13-T touch-consistent fills (pins)"},
            "taker_line": "B2 follow at the decision ask/bid, exit at the adverse touch 2-4 h later; reported with the q0403 cell; never counted"}
