# ruff: noqa: E501
"""O-rulings (2026-10-20): O9 tick change as an availability status, O11 symmetric one-sided worst case, O1 amended (signable population binds). Synthetic data only."""

from __future__ import annotations

import math

import numpy as np

from astrolabe.research_lab import cb13_t as t13
from astrolabe.research_lab import cb17_b as fb
from astrolabe.research_lab import cb17_e as fe
from astrolabe.research_lab import cb17_rules_b as rb
from astrolabe.research_lab import cb17_rules_c as rc
from astrolabe.research_lab import cb17_rules_e as re_


def _d():
    n = 12
    state = np.array([0, 1, 1, 0, 2, 1, 0, 1, 0, 1, 2, 0])
    st1 = np.array([fb.ST_OK, fb.ST_TICK, fb.ST_NO, fb.ST_TICK, fb.ST_OK, fb.ST_WIDE, fb.ST_OK, fb.ST_OK, fb.ST_TICK, fb.ST_OK, fb.ST_TICK, fb.ST_NO])
    excl2 = np.array([fb.B2_OK] * 10 + [fb.B2_NO_S2, fb.B2_OK])
    st2 = np.array([fb.ST_OK, fb.ST_OK, fb.ST_TICK, fb.ST_WIDE, fb.ST_TICK, fb.ST_OK, fb.ST_NO, fb.ST_OK, fb.ST_OK, fb.ST_TICK, fb.ST_OK, fb.ST_OK])
    x = np.array([1.0, -1.0, 0.0, 2.0, math.nan, 1.0, -2.0, 1.0, 0.5, 0.2, 1.0, -1.0])
    return {"tok": np.arange(n), "state": state, "st2_1": st1, "excl2": excl2, "st2_2": st2, "x": x}


def test_o9_tick_change_is_an_availability_status_and_the_other_index_sets_are_exactly_unchanged():
    D = _d()
    old1 = (D["state"] <= 1) & (D["st2_1"] != fb.ST_TICK)  # the pre-O9 B1 sample (placebo, composition guard, attribution, census, 6 h / capture robustness)
    old2 = (D["excl2"] == fb.B2_OK) & np.isfinite(D["x"]) & (D["st2_2"] != fb.ST_TICK)
    assert np.array_equal(fb.b1_core(D), old1) and np.array_equal(fb.b2_core(D), old2)
    # the availability denominator now carries the tick-change units; nothing else changes
    e1, e2 = fb.b1_sample(D), fb.b2_sample(D)
    assert np.array_equal(e1 & ~old1, (D["state"] <= 1) & (D["st2_1"] == fb.ST_TICK)) and (e1 & ~old1).any()
    assert np.array_equal(e2 & ~old2, (D["excl2"] == fb.B2_OK) & np.isfinite(D["x"]) & (D["st2_2"] == fb.ST_TICK)) and (e2 & ~old2).any()
    # the primary sample is ST_OK only, so it equals the pre-O9 primary set
    assert np.array_equal(e1 & (D["st2_1"] == fb.ST_OK), old1 & (D["st2_1"] == fb.ST_OK)) and np.array_equal(e2 & (D["st2_2"] == fb.ST_OK), old2 & (D["st2_2"] == fb.ST_OK))
    # the no-mark worst-case set takes the tick-change units in
    nm = e1 & np.isin(D["st2_1"], (fb.ST_NO, fb.ST_WIDE, fb.ST_TICK))
    assert (nm & (D["st2_1"] == fb.ST_TICK)).any()


def test_o9_declared_text_says_availability_status():
    assert "availability status" in rb.NO_MARK_RULE and "worst case" in rb.NO_MARK_RULE and "excluded and counted" not in rb.NO_MARK_RULE
    assert rb.mark_status({"tick": 0.01}, {"two_sided": True, "bid": 0.4, "ask": 0.45, "tick": 0.001}) == rb.TICK_CHANGE


def test_o11_worst_case_is_symmetric_by_class():
    C = np.arange(-50, 51, dtype=float)
    # transfer: touch adverse to continuation (up move at the bid), min(p5, touch-C)
    t = rc.onesided_adverse(1.0, 0.50, {"bid": 0.48, "ask": math.nan}, rc.CLASS_TRANSFER)
    assert math.isclose(t, -2.0) and rc.worst_member(rc.CLASS_TRANSFER, C, t) == -45.0 and rc.worst_member(rc.CLASS_TRANSFER, C, -60.0) == -60.0
    # mint / merge: touch favourable to continuation (up move at the ask), max(p95, touch-C)
    m = rc.onesided_adverse(1.0, 0.50, {"bid": math.nan, "ask": 0.53}, rc.CLASS_MINT)
    assert math.isclose(m, 3.0) and rc.worst_member(rc.CLASS_MINT, C, m) == 45.0 and rc.worst_member(rc.CLASS_MERGE, C, 60.0) == 60.0
    dn = rc.onesided_adverse(-1.0, 0.50, {"bid": 0.46, "ask": math.nan}, rc.CLASS_MERGE)  # a down move: the bid is the touch favourable to continuation
    assert math.isclose(dn, 4.0)
    # the opposite side absent -> no touch value, the percentile bound stands
    assert math.isnan(rc.onesided_adverse(1.0, 0.50, {"bid": 0.48, "ask": math.nan}, rc.CLASS_MINT)) and math.isnan(rc.onesided_adverse(1.0, 0.50, {"bid": math.nan, "ask": 0.53}, rc.CLASS_TRANSFER))
    assert "favourable to continuation" in rc.declared()["target"]["worst_case"]


def _rows(n_signable: int, n_unsignable: int):
    rows = []
    for i in range(n_signable + n_unsignable):
        sig = i < n_signable
        for part, age in (("a", 2.0), ("b", 72.0)):  # each market prints on its first day and on days 2-7
            tau = 1_800_000_000.0 + i * 60.0 + (0 if part == "a" else 3 * 86400.0)
            rows.append({"label": "UNSCHEDULED-NEWS", "tau": tau, "created_epoch": tau - age * 3600.0, "status": t13.SCREEN_STATUS_FILL if sig else "no touch", "condition_id": f"c{i}", "event_id": f"E{i}",
                         "d": 1, "mid0": 0.5, "prev_mid": 0.49, "path_key": f"p{i}", "market_id": f"m{i}", "block": 0, "cash": 100.0, "P": 0.5, "fee_type": "x"})
    return {"rows": rows, "status_counts": {}, "transactions": len(rows)}


def test_o1_amended_reentry_counts_bind_on_the_signable_population_and_all_counts_are_reported_only():
    cen = fe.census(_rows(100, 500))  # 600 markets, 600 first-day transactions overall, only 100 signable
    assert cen["first_day_transactions_non_sports"] == {"all": 600, "signable": 100}
    r = cen["reentry"]
    assert r["first_day_transactions"] == 100 and r["markets_first_and_later"] == 100 and r["pass"] is False  # binding view: 100 < 400
    rep = cen["reentry_all_transactions_reported_only"]
    assert rep["first_day_transactions"] == 600 and rep["markets_first_and_later"] == 600 and rep["binding"] is False
    big = fe.census(_rows(450, 0))
    assert big["reentry"]["first_day_transactions"] == 450 and big["reentry"]["markets_first_and_later"] == 450
    assert "signable" in re_.declared()["populations"]["counts"] and "REPORTED ONLY" in re_.declared()["populations"]["reported_only"]
