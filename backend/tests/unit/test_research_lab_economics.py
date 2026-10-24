"""Execution-cost model tests (paper only, no network)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import compare
from astrolabe.research_lab import economics as ec

SCHED = '{"exponent":1,"rate":0.05,"rebateRate":0.15,"takerOnly":true}'


def _book(**kw):
    b = dict(best_bid=0.48, best_ask=0.52, bid_size_1=10.0, ask_size_1=10.0, depth_bid_1c=12.0,
             depth_ask_1c=12.0, depth_bid_5c=30.0, depth_ask_5c=30.0, tick_size=0.01,
             min_order_size=5.0, state="two_sided")
    b.update(kw)
    return b


def test_fee_formula_and_rounding():
    assert ec.taker_fee(100, 0.5, 0.05) == pytest.approx(1.25)
    assert ec.taker_fee(1, 0.5, 0.07) == pytest.approx(0.0175)
    assert ec.taker_fee(1, 0.0001, 0.05) == 0.0  # below 1e-5 rounds to zero
    assert math.isnan(ec.taker_fee(5, 0.5, math.nan))


def test_fee_spec_cases():
    s = ec.fee_spec(SCHED, 1, "sports")
    assert (s.rate, s.flag, s.cross_check) == (0.05, "ok", "match")
    low = ec.fee_spec(SCHED.replace("0.05", "0.03"), 1, "sports")
    assert low.cross_check == "schedule_below_docs"
    assert ec.fee_spec(None, 0, "unknown").rate == 0.0
    assert ec.fee_spec(None, 0, "unknown").flag == "disabled"
    u = ec.fee_spec(None, 1, "sports")
    assert math.isnan(u.rate) and u.flag == "unknown_schedule"
    assert ec.fee_spec("not json", None, None).flag == "unknown_fees_enabled"
    assert ec.fee_spec(float("nan"), 1, "crypto").flag == "unknown_schedule"
    assert ec.fee_spec('{"exponent":1,"rate":0,"rebateRate":0}', 1, "other:zero_fees").rate == 0.0
    assert ec.resolve_rate(u, "max_if_unknown") == 0.07
    assert math.isnan(ec.resolve_rate(u, "schedule"))
    assert ec.resolve_rate(low, "conservative") == 0.05


def test_sweep_levels_and_vwap():
    b = _book()
    assert ec.side_levels(b, "buy0") == [(0.52, 10.0), (0.53, 2.0), (0.57, 18.0)]
    assert ec.side_levels(b, "sell0") == [(0.48, 10.0), (0.47, 2.0), (0.43, 18.0)]
    assert ec.side_levels(b, "buy1")[0] == pytest.approx((0.52, 10.0))  # 1 - 0.48
    f = ec.sweep_fill(b, "buy0", 5, rate=0.05)
    assert f.vwap == pytest.approx(0.52) and f.impact_cost == 0 and not f.depth_exhausted
    assert f.half_spread_cost == pytest.approx(5 * 0.02)
    assert f.fee == pytest.approx(round(5 * 0.05 * 0.52 * 0.48, 5))
    f = ec.sweep_fill(b, "buy0", 12, rate=0.05)
    assert f.vwap == pytest.approx((10 * 0.52 + 2 * 0.53) / 12)
    assert f.impact_cost == pytest.approx(12 * (f.vwap - 0.52))
    f = ec.sweep_fill(b, "buy0", 40, rate=0.05)
    assert f.depth_exhausted and f.filled == 30 and "depth_exhausted" in f.flags


def test_exact_levels_and_tick_and_min_size():
    b = _book(levels_asks=[(0.55, 3), (0.52, 4)])
    assert [p for p, _ in ec.side_levels(b, "buy0")] == [0.52, 0.55]
    t = _book(best_ask=0.5, tick_size=0.1, ask_size_1=1, depth_ask_1c=4, depth_ask_5c=4)
    assert ec.side_levels(t, "buy0")[1][0] == pytest.approx(0.6)  # 0.51 rounds UP to tick
    assert "below_order_min_size" in ec.sweep_fill(_book(), "buy0", 2).flags
    assert ec.min_size(_book(min_order_size=None)) == 1.0
    assert ec.min_size(_book(min_order_size=15)) == 15.0


def test_one_sided_and_empty():
    f = ec.sweep_fill(_book(best_bid=None, bid_size_1=None), "sell0", 5, rate=0.05)
    assert f.filled == 0 and f.depth_exhausted
    f = ec.sweep_fill(_book(best_bid=None), "buy0", 5, rate=0.05)
    assert math.isnan(f.half_spread_cost) and "one_sided_no_mid" in f.flags


def _row(p_up, p_down, en=None, ex=None, **kw):
    r = {"p_up": p_up, "p_down": p_down, "fee_schedule": SCHED, "fees_enabled": 1,
         "fee_category": "sports"}
    for k, v in (en or _book()).items():
        r["en_" + k] = v
    for k, v in (ex or _book(best_bid=0.58, best_ask=0.62)).items():
        r["ex_" + k] = v
    r.update(kw)
    return r


def test_paper_trade_long_and_short():
    t = ec.paper_trade(_row(0.6, 0.2), 0.1)
    assert t["traded"] and t["direction"] == 1
    fee_in = round(5 * 0.05 * 0.52 * 0.48, 5)
    fee_out = round(5 * 0.05 * 0.58 * 0.42, 5)
    assert t["pnl"] == pytest.approx(5 * 0.58 - 5 * 0.52 - fee_in - fee_out)
    s = ec.paper_trade(_row(0.1, 0.6, ex=_book(best_bid=0.38, best_ask=0.42)), 0.1)
    # buy outcome 1 at 1-0.48=0.52, sell at 1-0.42=0.58
    assert s["direction"] == -1 and s["pnl"] == pytest.approx(5 * 0.06 - fee_in - fee_out)
    assert ec.paper_trade(_row(0.4, 0.35), 0.1)["status"] == "no_signal"


def test_paper_trade_gates_and_sensitivity():
    small = _book(ask_size_1=3, depth_ask_1c=3, depth_ask_5c=3)
    assert ec.paper_trade(_row(0.6, 0.2, en=small), .1)["status"] == "entry_top_size"
    assert ec.paper_trade(_row(0.6, 0.2, en=_book(best_ask=None, ask_size_1=None)),
                          .1)["status"] == "no_entry_book"
    r = _row(0.6, 0.2)
    r["ex_best_bid"] = r["ex_best_ask"] = None
    assert ec.paper_trade(r, .1)["status"] == "no_exit"
    g = ec.paper_trade(_row(0.6, 0.2, gx_best_bid=0.55, gx_best_ask=0.6), .1, exit_mode="gamma_bid")
    assert g["traded"] and g["exit_cash"] == pytest.approx(2.75)
    # thin exit book -> unfilled shares valued at 0, flagged
    ex = _book(best_bid=0.58, bid_size_1=2, depth_bid_1c=2, depth_bid_5c=2)
    t = ec.paper_trade(_row(0.6, 0.2, ex=ex), .1)
    assert t["exit_depth_exhausted"] and t["exit_cash"] == pytest.approx(2 * 0.58)


def test_unknown_fee_uses_max_rate():
    t = ec.paper_trade(_row(0.6, 0.2, fee_schedule=None), 0.1)
    assert t["fee_flag"] == "unknown_schedule"
    assert t["fee_entry"] == pytest.approx(round(5 * 0.07 * 0.52 * 0.48, 5))
    z = ec.paper_trade(_row(0.6, 0.2, fee_schedule=None, fees_enabled=0), 0.1)
    assert z["fee_entry"] == 0.0


def test_boot_ratio_matches_paired_bootstrap_draws():
    rng = np.random.default_rng(1)
    c = np.repeat(np.arange(40), 5)
    num = rng.normal(0.02, 0.1, 200)
    den = np.ones(200)
    r = ec.boot_ratio(c, num, den)
    assert r["mean"] == pytest.approx(num.mean())
    pb = compare.paired_bootstrap(c, {"den": den, "neg": -num}, "den")
    assert r["ci95_two_sided"][0] == pytest.approx(pb["models"]["neg"][0] - 1)
    assert r["lower_5pct"] > r["ci95_two_sided"][0]  # one-sided 5th >= two-sided 2.5th


def _frame(pnls, clusters):
    return pd.DataFrame({"traded": [True] * len(pnls), "pnl": pnls}), np.asarray(clusters)


def test_h2a_decisions():
    rng = np.random.default_rng(2)
    pnl = rng.normal(0.3, 0.2, 300)
    f, c = _frame(pnl, np.repeat(np.arange(60), 5))
    r = ec.h2a(f, {"fixture": c, "season": c % 20})
    assert r["testable"] and r["reject"]
    f, c = _frame(rng.normal(-0.3, 0.2, 300), np.repeat(np.arange(60), 5))
    assert not ec.h2a(f, {"a": c})["reject"]
    f, c = _frame(pnl[:20], np.arange(20))  # < 30 trades
    r = ec.h2a(f, {"a": c})
    assert not r["testable"] and not r["reject"]
    f, c = _frame(pnl[:60], np.repeat(np.arange(5), 12))  # < 10 clusters
    assert not ec.h2a(f, {"a": c})["testable"]
    # must hold under EVERY definition: one cluster makes its CI degenerate-wide/untestable
    f, c = _frame(pnl, np.repeat(np.arange(60), 5))
    r = ec.h2a(f, {"fine": c, "one": np.zeros(300, int)})
    assert not r["testable"] and not r["reject"]


def test_h2b_paired():
    rng = np.random.default_rng(3)
    n = 400
    cl = np.repeat(np.arange(80), 5)
    f = pd.DataFrame({"traded": rng.random(n) < .5, "pnl": rng.normal(0.4, 0.2, n)})
    m = pd.DataFrame({"traded": rng.random(n) < .5, "pnl": rng.normal(0.0, 0.2, n)})
    assert ec.h2b(f, m, {"a": cl})["reject"]
    assert not ec.h2b(m, f, {"a": cl})["reject"]
    with pytest.raises(ValueError):
        ec.h2b(f, m.iloc[1:], {"a": cl})


def test_breakeven_monotone():
    spec = ec.fee_spec(SCHED, 1, "sports")
    tight = ec.round_trip_cost(_book(best_bid=0.49, best_ask=0.51), spec)
    wide = ec.round_trip_cost(_book(best_bid=0.45, best_ask=0.55), spec)
    assert tight["ok"] and wide["cost_ps"] > tight["cost_ps"]
    assert tight["spread_ps"] == pytest.approx(0.02)
    be = ec.breakeven(0.02, 0.5)
    assert be["delta_prob"] == 0.02
    assert be["delta_logloss"] == pytest.approx(0.02**2 / (2 * .25), rel=0.05)
    assert not ec.round_trip_cost(_book(best_bid=None, bid_size_1=None), spec)["ok"]


def test_breakeven_table_regimes():
    one = dict(_book(), market_id="a", liquidity=5000, fee_category="sports",
               fee_schedule=SCHED, fees_enabled=1)
    two = dict(_book(state="one_sided"), market_id="b", liquidity=None, fee_category=None,
               fee_schedule=None, fees_enabled=None)
    t = ec.breakeven_table(pd.DataFrame([one, two]))
    assert list(t["ok"]) == [True, False]
    assert t.loc[0, "liq_band"] == "1k-10k" and t.loc[0, "price_band"] == "0.20-0.80"
    s = ec.regime_summary(t[t["ok"]], "fee_category")
    assert s.loc[0, "cost_med"] > 0.04  # 4c spread plus fees
