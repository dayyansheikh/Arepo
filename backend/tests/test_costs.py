# ruff: noqa: E501
"""Unit and property tests for the paper execution-cost model (astrolabe.research_lab.costs).

Property tests use seeded random draws (no extra dependency): each property is checked on a few
thousand random books / quotes."""

from __future__ import annotations

import math
import random

import pytest

from astrolabe.research_lab import costs, economics

N_PROP = 2000


# --- fee tables ---------------------------------------------------------------------------------


def test_fee_tables_match_economics():
    assert costs.CATEGORY_TAKER_RATE == economics.DOCS_CATEGORY_RATE
    assert costs.CATEGORY_REBATE_SHARE == economics.REBATE_SHARE
    assert costs.MAX_TAKER_RATE == economics.MAX_DOCS_RATE == 0.07


def test_taker_rate_policies():
    assert costs.taker_rate("politics") == 0.04
    assert costs.taker_rate("politics:us-election") == 0.04
    assert costs.taker_rate("sports", schedule_rate=0.03) == 0.05  # conservative: max(schedule, docs)
    assert costs.taker_rate("sports", schedule_rate=0.03, policy="schedule") == 0.03
    assert costs.taker_rate("sports", schedule_rate=0.03, policy="docs") == 0.05
    assert costs.taker_rate("crypto", fees_enabled=False) == 0.0
    assert costs.taker_rate(None) == 0.07  # unknown is never 0
    assert costs.taker_rate("no-such-category", policy="schedule") == 0.07
    assert costs.taker_rate("geopolitics") == 0.0
    with pytest.raises(ValueError):
        costs.taker_rate("politics", policy="cheap")


def test_taker_fee_matches_docs_example():
    # docs example: 100 shares at 0.50, crypto 0.07 -> 1.75 USDC; 0.04 -> 1.00 USDC
    assert 100 * costs.taker_fee_ps(0.5, 0.07) == pytest.approx(1.75)
    assert 100 * costs.taker_fee_ps(0.5, 0.04) == pytest.approx(1.00)
    # agrees with economics.taker_fee (which rounds the order fee to 5 dp)
    for p in (0.03, 0.2, 0.5, 0.77, 0.99):
        assert economics.taker_fee(100, p, 0.05) == pytest.approx(100 * costs.taker_fee_ps(p, 0.05), abs=1e-5)


def test_maker_rebate():
    fee = costs.taker_fee_ps(0.5, 0.04)
    assert costs.maker_rebate_ps(0.5, "politics") == pytest.approx(0.25 * fee * costs.REBATE_POOL_HAIRCUT)
    assert costs.maker_rebate_ps(0.5, "politics", pool_haircut=1.0) == pytest.approx(0.25 * fee)
    assert costs.maker_rebate_ps(0.5, None) == 0.0
    assert costs.maker_rebate_ps(0.5, "geopolitics") == 0.0
    assert costs.maker_rebate_ps(0.5, "sports", rate=0.03, rebate_share=0.25, pool_haircut=1.0) == pytest.approx(
        0.25 * 0.03 * 0.25)


def test_fee_properties():
    rng = random.Random(1)
    for _ in range(N_PROP):
        p, r = rng.random(), rng.choice(list(costs.CATEGORY_TAKER_RATE.values()))
        f = costs.taker_fee_ps(p, r)
        assert 0.0 <= f <= r / 4 + 1e-15  # peak at p = 0.5
        assert f == pytest.approx(costs.taker_fee_ps(1 - p, r))  # symmetric
        assert costs.maker_rebate_ps(p, "politics") <= costs.taker_fee_ps(p, 0.04)


# --- book walk -----------------------------------------------------------------------------------


def test_levels_from_summary_matches_economics():
    book = {"best_bid": 0.57, "best_ask": 0.59, "bid_size_1": 84.0, "ask_size_1": 89.0,
            "depth_bid_1c": 420.5, "depth_ask_1c": 404.1, "depth_bid_5c": 2011.72, "depth_ask_5c": 1677.26,
            "tick_size": 0.01}
    la = costs.levels_from_summary(0.59, 89.0, 404.1, 1677.26, lift_asks=True, tick=0.01)
    lb = costs.levels_from_summary(0.57, 84.0, 420.5, 2011.72, lift_asks=False, tick=0.01)
    assert la == pytest.approx(economics.side_levels(book, "buy0"))
    assert lb == pytest.approx(economics.side_levels(book, "sell0"))
    assert la[0] == (0.59, 89.0) and la[1][0] == pytest.approx(0.60) and la[2][0] == pytest.approx(0.64)
    assert costs.levels_from_summary(math.nan, 5.0, lift_asks=True) == []
    assert costs.levels_from_summary(0.5, 0.0, lift_asks=True) == []


def test_walk_shares_and_notional():
    lv = [(0.50, 10.0), (0.51, 10.0), (0.55, 100.0)]
    w = costs.walk(lv, shares=15)
    assert w.filled_shares == 15 and not w.exhausted
    assert w.cash == pytest.approx(10 * 0.50 + 5 * 0.51)
    assert w.impact_ps == pytest.approx(w.vwap - 0.50)
    w2 = costs.walk(lv, notional=5.0)
    assert w2.filled_shares == pytest.approx(10.0) and w2.impact_ps == pytest.approx(0.0)
    w3 = costs.walk(lv, notional=1e6)
    assert w3.exhausted and w3.filled_shares == pytest.approx(120.0)
    assert costs.walk([], shares=5).exhausted
    with pytest.raises(ValueError):
        costs.walk(lv)
    with pytest.raises(ValueError):
        costs.walk(lv, shares=1, notional=1)
    assert costs.depth_notional_within(lv, 0.01) == pytest.approx(10 * 0.50 + 10 * 0.51)


def _random_ask_book(rng: random.Random):
    best = round(rng.uniform(0.02, 0.9), 2)
    s1 = rng.uniform(1, 500)
    d1 = s1 + rng.choice([0.0, rng.uniform(0, 2000)])
    d5 = d1 + rng.choice([0.0, rng.uniform(0, 5000)])
    return best, costs.levels_from_summary(best, s1, d1, d5, lift_asks=True, tick=0.01)


def test_walk_properties():
    rng = random.Random(7)
    for _ in range(N_PROP):
        best, lv = _random_ask_book(rng)
        a, b = sorted((rng.uniform(0.5, 3000), rng.uniform(0.5, 3000)))
        wa, wb = costs.walk(lv, notional=a), costs.walk(lv, notional=b)
        # cost per share never falls with size; vwap stays between touch and worst level
        if not wb.exhausted:
            assert wb.vwap >= wa.vwap - 1e-12
            assert best - 1e-12 <= wb.vwap <= wb.worst + 1e-12
        # never fills more than the book shows, never spends more than asked
        assert wb.filled_shares <= sum(s for _, s in lv) + 1e-9
        assert wb.cash <= b + 1e-9
        assert wa.impact_ps >= -1e-12


# --- taker legs and round trips -------------------------------------------------------------------


def test_taker_leg_components():
    lv = [(0.52, 100.0)]
    leg = costs.taker_leg(lv, 0.51, shares=10, rate=0.04)
    assert leg.half_spread_ps == pytest.approx(0.01)
    assert leg.impact_ps == pytest.approx(0.0)
    assert leg.fee_ps == pytest.approx(0.04 * 0.52 * 0.48)
    assert leg.total_ps == pytest.approx(0.01 + 0.04 * 0.52 * 0.48)
    assert costs.taker_leg([], 0.5, shares=5).exhausted


def test_staleness_haircut():
    assert costs.staleness_haircut_ps(0, 0.02) == 0.0
    assert costs.staleness_haircut_ps(3600, 0.02) == pytest.approx(0.4 * 0.02)
    assert costs.staleness_haircut_ps(900, 0.02) == pytest.approx(0.4 * 0.02 * 0.5)


def test_round_trip_from_quote():
    rt = costs.round_trip_from_quote(0.5, 0.02, 0.04)
    assert rt["half_spread_ps"] == pytest.approx(0.02)
    assert rt["fee_ps"] == pytest.approx(costs.taker_fee_ps(0.51, 0.04) + costs.taker_fee_ps(0.49, 0.04))
    rr = costs.round_trip_from_quote(0.5, 0.02, 0.04, exit_mode="resolution")
    assert rr["total_ps"] < rt["total_ps"]
    assert rr["half_spread_ps"] == pytest.approx(0.01)
    with pytest.raises(ValueError):
        costs.round_trip_from_quote(0.5, 0.02, 0.04, exit_mode="maker")


def test_round_trip_properties():
    rng = random.Random(11)
    for _ in range(N_PROP):
        mid, spr = rng.uniform(0.05, 0.95), rng.uniform(0.0, 0.08)
        r = rng.choice([0.0, 0.04, 0.05, 0.07])
        rt = costs.round_trip_from_quote(mid, spr, r)
        assert rt["total_ps"] >= spr - 1e-12  # never below the spread
        assert costs.round_trip_from_quote(mid, spr + 0.01, r)["total_ps"] > rt["total_ps"] - 1e-12
        assert costs.round_trip_from_quote(mid, spr, r + 0.01)["total_ps"] >= rt["total_ps"]


# --- maker ------------------------------------------------------------------------------------------


def test_fill_probability_properties():
    rng = random.Random(3)
    for _ in range(N_PROP):
        pa, sc, al = rng.random(), rng.uniform(0.5, 100), rng.uniform(0.01, 3)
        q1, q2 = sorted((rng.uniform(0, 1e5), rng.uniform(0, 1e5)))
        p1 = costs.fill_probability(q1, 5, pa, sc, al)
        p2 = costs.fill_probability(q2, 5, pa, sc, al)
        assert 0.0 <= p2 <= p1 <= pa + 1e-12  # longer queue never fills more often
    assert costs.fill_probability(0, 0, 0.3, 5.0, 0.0) == pytest.approx(0.3)
    assert costs.fill_probability(10, 5, 0.0, 5.0, 0.3) == 0.0
    assert costs.fill_probability(10, 5, 0.5, 5.0, 1.0) == pytest.approx(0.5 / 4.0)


def test_maker_defaults_shape():
    tiers = costs.MAKER_DEFAULTS["tiers"]
    assert set(tiers) == set(costs.LIQ_LABELS)
    for t in tiers.values():
        lo, hi = t["p_fill_ci95"]
        assert 0 < lo <= t["p_fill"] <= hi < 1
        assert t["p_fill"] <= t["p_active"]
        lo, hi = t["adverse_selection_ci95"]
        assert lo <= t["adverse_selection_ps"] <= hi
        assert 0 < costs.fill_probability(10, 5, t["p_active"], t["scale_shares"], t["alpha"]) < t["p_active"]


def test_liquidity_tier():
    assert costs.liquidity_tier(None) == "<1k"
    assert costs.liquidity_tier(math.nan) == "<1k"
    assert costs.liquidity_tier(999) == "<1k"
    assert costs.liquidity_tier(1000) == "1k-10k"
    assert costs.liquidity_tier(5e4) == "10k-100k"
    assert costs.liquidity_tier(1e5) == ">=100k"


def test_maker_leg_arithmetic():
    ml = costs.maker_entry(p_fill=0.04, gross_ps=0.01, half_spread_ps=0.013, fill_conditioning_ps=0.02,
                           rebate_ps=0.001, exit_cost_ps=0.017)
    assert ml.net_per_fill_ps == pytest.approx(0.01 + 0.013 - 0.02 + 0.001 - 0.017)
    assert ml.net_per_attempt_ps == pytest.approx(0.04 * ml.net_per_fill_ps)
    be = costs.maker_entry(p_fill=0.04, gross_ps=ml.breakeven_gross_ps, half_spread_ps=0.013,
                           fill_conditioning_ps=0.02, rebate_ps=0.001, exit_cost_ps=0.017)
    assert be.net_per_fill_ps == pytest.approx(0.0, abs=1e-15)


def test_fill_conditioning_scenarios():
    assert costs.fill_conditioning(0.02, "independent") == 0.02
    assert costs.fill_conditioning(0.02) == costs.MAKER_DEFAULTS["flow_fill_conditioning_ps"]
    assert costs.fill_conditioning(0.05) == 0.05
    with pytest.raises(ValueError):
        costs.fill_conditioning(0.02, "free")


# --- cost check ---------------------------------------------------------------------------------------


def test_cost_check_f4_like():
    c = costs.cost_check(0.0094, mid=0.5, spread=0.0268, category="politics", liquidity=5e4)
    rt = costs.round_trip_from_quote(0.5, 0.0268, 0.04)["total_ps"]
    assert c.taker_round_trip_ps == pytest.approx(rt)
    assert c.taker_net_ps == pytest.approx(0.0094 - rt)
    assert c.taker_net_ps < 0 and c.maker_net_per_fill_ps < 0
    assert c.maker_p_fill == costs.MAKER_DEFAULTS["tiers"]["10k-100k"]["p_fill"]
    assert c.maker_net_per_attempt_ps == pytest.approx(c.maker_p_fill * c.maker_net_per_fill_ps)
    assert c.label.startswith("development cost check")
    assert set(c.cents()) >= {"gross_c", "taker_net_c", "maker_net_per_fill_c"}


def test_cost_check_properties():
    rng = random.Random(5)
    cats = [*costs.CATEGORY_TAKER_RATE, None]
    for _ in range(500):
        kw = {"mid": rng.uniform(0.05, 0.95), "spread": rng.uniform(0.001, 0.08), "category": rng.choice(cats),
              "liquidity": rng.choice([10, 5e3, 5e4, 5e5])}
        g = rng.uniform(-0.02, 0.05)
        cons = costs.cost_check(g, **kw)
        opt = costs.cost_check(g, maker_scenario="independent", **kw)
        # conservative is never better than independent; resolution exit never costs more than a taker exit
        assert cons.maker_net_per_fill_ps <= opt.maker_net_per_fill_ps + 1e-12
        res = costs.cost_check(g, maker_exit="resolution", **kw)
        assert res.maker_net_per_fill_ps >= cons.maker_net_per_fill_ps - 1e-12
        assert cons.taker_resolution_cost_ps <= cons.taker_round_trip_ps + 1e-12
        # net is linear in gross with slope 1 (taker) and p_fill (maker per attempt)
        hi = costs.cost_check(g + 0.01, **kw)
        assert hi.taker_net_ps - cons.taker_net_ps == pytest.approx(0.01)
        assert hi.maker_net_per_attempt_ps - cons.maker_net_per_attempt_ps == pytest.approx(0.01 * cons.maker_p_fill)
    with pytest.raises(ValueError):
        costs.cost_check(0.01, mid=0.5, spread=0.02, maker_exit="maker")
