# ruff: noqa: E501
"""CB3 family B and the shared paper maker (docs/research_lab/CREATIVE_BATCH_3.md §4.4)."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2, economics, provenance
from astrolabe.research_lab import cb3_common as C
from astrolabe.research_lab import cb3_declaration as D
from astrolabe.research_lab import cb3_maker as M

H = 3600.0
T = 1_760_000_000.0


def prints(rows):
    """rows: (ts, side, outcome, price, size[, wallet])"""
    df = pd.DataFrame([{"ts": r[0], "side": r[1], "outcome_index": r[2], "price": r[3], "size": r[4], "wallet_hash": r[5] if len(r) > 5 else f"w{i}",
                        "trade_key": f"k{i}"} for i, r in enumerate(rows)])
    return M.prints_arrays(df)


# --- fills ---------------------------------------------------------------------------------------------


def test_queue_fill_needs_displayed_size_plus_own_and_excludes_print_at_t():
    pr = prints([(T, "SELL", 0, 0.48, 100.0), (T + 10, "SELL", 0, 0.48, 10.0), (T + 20, "SELL", 0, 0.48, 10.0)])
    st = M.quote_fills(pr, T, "bid", 0.48, 20.0)
    assert st["queue"] == (0, math.nan) or st["queue"][0] == 0  # 20 shares after t < 20 + 5; the 100-share print AT t is excluded
    assert st["touch"][0] == 1
    pr2 = prints([(T + 10, "SELL", 0, 0.48, 10.0), (T + 20, "SELL", 0, 0.47, 10.0), (T + 30, "SELL", 0, 0.48, 5.0)])
    st2 = M.quote_fills(pr2, T, "bid", 0.48, 20.0)
    assert st2["queue"] == (1, T + 30)


def test_fills_convert_outcome_one_prints_and_use_the_correct_side():
    # BUY of outcome 1 at 0.52 is a taker SELL of outcome 0 at 0.48: fills our bid at 0.48, not our ask
    pr = prints([(T + 5, "BUY", 1, 0.52, 50.0)])
    assert M.quote_fills(pr, T, "bid", 0.48, 0.0)["queue"][0] == 1
    assert M.quote_fills(pr, T, "ask", 0.52, 0.0)["queue"][0] == 0
    # SELL of outcome 1 at 0.48 is a taker BUY of outcome 0 at 0.52: fills our ask
    pr = prints([(T + 5, "SELL", 1, 0.48, 50.0)])
    assert M.quote_fills(pr, T, "ask", 0.52, 0.0)["queue"] == (1, T + 5)


def test_truncated_history_gives_unavailable_not_unfilled():
    pr = prints([(T + 500, "SELL", 0, 0.60, 1.0)])
    assert M.quote_fills(pr, T, "bid", 0.48, 0.0, truncated=True, oldest_ts=T + 400)["queue"][0] == -1
    assert M.quote_fills(pr, T, "bid", 0.48, 0.0, truncated=True, oldest_ts=T - 100)["queue"][0] == 0
    assert M.quote_fills(pr, T, "bid", 0.48, 0.0)["queue"][0] == 0


# --- taker orders and large-order flag --------------------------------------------------------------------


def test_taker_order_aggregation_groups_same_ts_wallet_side_outcome():
    pr = prints([(T, "BUY", 0, 0.5, 10.0, "a"), (T, "BUY", 0, 0.6, 10.0, "a"), (T, "BUY", 0, 0.5, 4.0, "b"), (T + 1, "SELL", 1, 0.4, 5.0, "a")])
    o = M.taker_orders(pr)
    assert len(o) == 3
    assert o[o["wallet"] == "a"].iloc[0]["notional"] == pytest.approx(11.0)
    assert o[(o["wallet"] == "a") & (o["ts"] == T + 1)].iloc[0]["n_prints"] == 1


def test_large_flag_needs_50_prior_orders_uses_strictly_earlier_and_is_not_its_own_trigger():
    ts = np.arange(1.0, 61.0)
    notional = np.arange(1.0, 61.0)
    notional[-1] = 1000.0
    f = M.large_order_flags(ts, notional)
    assert np.isnan(f[:50]).all()  # fewer than 50 prior orders: unclassified
    assert not np.isnan(f[50]) and f[-1] == 1.0
    # same-timestamp orders never count as prior: 60 orders all at the same ts -> all unclassified
    assert np.isnan(M.large_order_flags(np.full(60, 5.0), np.arange(60.0))).all()
    # the order is compared with the percentile of the PREVIOUS orders only (adding itself would change the cut)
    assert f[-1] == 1.0


def _market_prints(n_pre=60, big_ago=None, fill_big=False):
    rows = [(T - 20 * H + 600.0 * i, "BUY", 0, 0.5, 10.0 + i % 5) for i in range(n_pre)]
    if big_ago is not None:
        rows.append((T + 3000.0 - big_ago, "BUY", 0, 0.5, 5000.0))
    rows.append((T + 3000.0, "SELL", 0, 0.48, 5000.0 if fill_big else 30.0))
    return prints(rows)


def _opp(**kw):
    d = dict(opp_id="m@1", market_id="m", event="e", dep="d", cat="other", t=T, bid=0.48, ask=0.52, bid_size=10.0, ask_size=10.0,
             created=T - 40 * 86400.0, end=T + 20 * 86400.0)
    d.update(kw)
    return M.Opp(**d)


def test_post_flag_excludes_the_filling_order_and_sees_earlier_large_orders():
    marks = M.HistoryMarks(np.array([T + 3000 + 7 * H - 3000.0]), np.array([0.5]))
    pr = _market_prints(big_ago=900.0)
    row, fills, _ = M.evaluate_opportunity(_opp(), pr, pr, marks)
    f = [x for x in fills if x["rule"] == "queue" and x["side"] == "bid"]
    assert row["classifiable"] and len(f) == 1 and f[0]["post"] == 1.0  # a large print 15 minutes before the fill
    pr = _market_prints(big_ago=None, fill_big=True)
    _row, fills, _ = M.evaluate_opportunity(_opp(), pr, pr, marks)
    f = [x for x in fills if x["rule"] == "queue" and x["side"] == "bid"]
    assert f[0]["post"] == 0.0  # the filling order is large but is never its own trigger


def test_classifiability_requires_visible_orders_before_t_and_t_cancel_is_first_large_after_posting():
    pr = _market_prints(n_pre=10, big_ago=900.0)
    row, _f, _ = M.evaluate_opportunity(_opp(), pr, pr, None)
    assert row["classifiable"] is False
    pr = _market_prints(n_pre=60, big_ago=900.0)
    row, _f, larges = M.evaluate_opportunity(_opp(), pr, pr, None)
    assert row["t_cancel"] == pytest.approx(T + 2100.0) and (T + 2100.0) in larges


# --- life fraction ----------------------------------------------------------------------------------------


def test_life_fraction_from_scheduled_end_clipped_and_nan_without_anchors():
    assert M.life_fraction(50.0, 0.0, 100.0) == pytest.approx(0.5)
    assert M.life_fraction(500.0, 0.0, 100.0) == 1.0 and M.life_fraction(-5.0, 0.0, 100.0) == 0.0
    assert math.isnan(M.life_fraction(1.0, math.nan, 100.0)) and math.isnan(M.life_fraction(1.0, 0.0, 0.0))
    import inspect

    assert "close" not in " ".join(inspect.signature(M.life_fraction).parameters)  # closed_time is never an anchor
    assert not hasattr(M.Opp(opp_id="x", market_id="m", event="e", dep="d", cat="c", t=0, bid=0.4, ask=0.5, bid_size=1, ask_size=1), "close")


# --- round-trip share --------------------------------------------------------------------------------------


def _rt_prints(extra_rt=True, n_other=20, span=20 * H):
    rows = []
    for i in range(n_other):
        rows.append((T - 5 * H + i * 60.0, "BUY", 0, 0.5, 10.0, f"o{i}"))
    if extra_rt:
        for k, side in enumerate(["BUY", "SELL", "BUY", "SELL"]):
            rows.append((T - 3 * H + k * 600.0, side, 0, 0.5, 10.0, "rt"))
    rows.append((T - span, "BUY", 0, 0.5, 1.0, "old"))
    return prints(rows)


def test_round_trip_four_trades_both_signs_ten_percent_rule():
    vis = M.visible_prints(_rt_prints(), T)
    rt = M.round_trip_share(vis, T)
    assert rt == pytest.approx(40.0 * 0.5 / (24 * 10.0 * 0.5))  # 4 prints x 10 x 0.5 over 24 prints x 10 x 0.5
    # three trades only -> not a round-tripper
    rows = [(T - 5 * H + i * 60.0, "BUY", 0, 0.5, 10.0, f"o{i}") for i in range(20)]
    rows += [(T - 3 * H, "BUY", 0, 0.5, 10.0, "x"), (T - 3 * H + 60, "SELL", 0, 0.5, 10.0, "x"), (T - 3 * H + 120, "BUY", 0, 0.5, 10.0, "x"), (T - 25 * H, "BUY", 0, 0.5, 1.0, "old")]
    assert M.round_trip_share(M.visible_prints(prints(rows), T), T) == 0.0
    # both signs but net 25% of gross -> not a round-tripper
    rows = [(T - 5 * H + i * 60.0, "BUY", 0, 0.5, 10.0, f"o{i}") for i in range(20)]
    rows += [(T - 3 * H + k * 60, s, 0, 0.5, z, "y") for k, (s, z) in enumerate([("BUY", 10.0), ("BUY", 10.0), ("SELL", 10.0), ("BUY", 10.0), ("SELL", 4.0)])]
    rows.append((T - 25 * H, "BUY", 0, 0.5, 1.0, "old"))
    assert M.round_trip_share(M.visible_prints(prints(rows), T), T) == 0.0


def test_round_trip_undefined_below_20_prints_or_without_window_coverage():
    rows = [(T - 3 * H + k * 600.0, s, 0, 0.5, 10.0, "rt") for k, s in enumerate(["BUY", "SELL", "BUY", "SELL"])] + [(T - 25 * H, "BUY", 0, 0.5, 1.0, "old")]
    assert math.isnan(M.round_trip_share(M.visible_prints(prints(rows), T), T))  # 4 prints in the last 6h
    # 500 visible prints that do not reach back 24h -> unavailable
    rows = [(T - 5 * H + i * 30.0, "BUY", 0, 0.5, 1.0, f"o{i}") for i in range(500)]
    assert math.isnan(M.round_trip_share(M.visible_prints(prints(rows), T), T))
    # a truncated market whose oldest print is inside the 24h window -> unavailable
    rows = [(T - 5 * H + i * 30.0, "BUY", 0, 0.5, 1.0, f"o{i}") for i in range(100)]
    assert math.isnan(M.round_trip_share(M.visible_prints(prints(rows), T), T, truncated=True, oldest_ts=T - 5 * H))


# --- union / visibility --------------------------------------------------------------------------------------


def test_pre_print_at_or_after_t_dropped_and_duplicate_counts_once_and_500_visibility():
    pre = prints([(T - 10, "BUY", 0, 0.5, 1.0), (T + 5, "BUY", 0, 0.5, 2.0)])  # the pre/ print at T+5 is after t: dropped
    post = prints([(T + 20, "SELL", 0, 0.5, 3.0), (T - 5, "SELL", 0, 0.5, 9.0)])  # post/ print before t: dropped
    u = M.prints_union(pre, post, T)
    assert list(u["ts"]) == [T - 10, T + 20]
    both = prints([(T + 20, "SELL", 0, 0.5, 3.0)])
    again = M.prints_union(M.prints_union(pre, both, T), both, T)
    assert list(again["ts"]).count(T + 20) == 1
    many = prints([(T - 1000 + i, "BUY", 0, 0.5, 1.0) for i in range(700)])
    assert len(M.visible_prints(many, T)["ts"]) == 500 and M.visible_prints(many, T)["ts"][0] == T - 1000 + 200


# --- marks ---------------------------------------------------------------------------------------------------


def test_history_mark_uses_600s_lag_and_ignores_later_prices():
    ts = np.array([T, T + 600, T + 1200, T + 7 * H])
    vals = np.array([0.40, 0.45, 0.50, 0.99])
    hm = M.HistoryMarks(ts, vals)
    m, _, _ = hm.mark(T + 1200.0, 0.0, 0.0)
    assert m == pytest.approx(0.40)  # stamp + 600 s must be strictly before t: the T+600 point is not yet usable at T+1200
    assert hm.mark(T + 1201.0, 0.0, 0.0)[0] == pytest.approx(0.45)
    m6, _, _ = hm.mark(T, 6 * H, 0.0)
    assert m6 == pytest.approx(0.50) or math.isnan(m6)  # the 0.99 stamped at T+7h is after the mark time and ignored
    assert m6 != pytest.approx(0.99)


def test_prospective_mark_tight_rule_next_pass_within_4h_and_worst_case():
    recv = np.array([T + 6 * H + 60, T + 8 * H, T + 11 * H])
    sm = M.SweepMarks(recv, np.array([0.10, 0.50, 0.30]), np.array([0.90, 0.54, 0.34]))
    m, b, a = sm.mark(T, 6 * H)
    assert m == pytest.approx(0.52) and (b, a) == (0.50, 0.54)  # first pass is wide; the next within 4h is tight
    sm2 = M.SweepMarks(np.array([T + 6 * H + 60, T + 12 * H]), np.array([0.10, 0.50]), np.array([0.90, 0.54]))
    assert math.isnan(sm2.mark(T, 6 * H)[0])  # nothing tight within 4h of t_fill + 6h
    fb, fa = sm2.last_before(T + 6 * H, 0.0, T)
    assert (fb, fa) == (0.10, 0.90)
    assert M.worst_case_mo("bid", 0.48, fb, fa) == pytest.approx(0.10 - 0.48)
    assert M.worst_case_mo("bid", 0.48, math.nan, math.nan) == pytest.approx(-0.48)  # no mark at all: total loss
    assert M.worst_case_mo("ask", 0.52, math.nan, math.nan) == pytest.approx(-0.48)


def test_mark_out_signs():
    assert M.mark_out("bid", 0.48, 0.50) == pytest.approx(0.02) and M.mark_out("ask", 0.52, 0.50) == pytest.approx(0.02)
    assert M.mark_out("bid", 0.48, 0.45) == pytest.approx(-0.03)


# --- rebate / fees ---------------------------------------------------------------------------------------------


def test_rebate_by_category_unknown_zero_geopolitics_zero_and_halved():
    p = 0.5
    assert M.rebate_per_share(p, "crypto") == pytest.approx(0.20 * 0.07 * 0.25)
    assert M.rebate_per_share(p, "politics") == pytest.approx(0.25 * 0.04 * 0.25)
    assert M.rebate_per_share(p, "geopolitics") == 0.0
    assert M.rebate_per_share(p, None) == 0.0 and M.rebate_per_share(p, "zzz") == 0.0 and M.rebate_per_share(p, float("nan")) == 0.0
    assert M.rebate_per_share(p, "crypto", halved=True) == pytest.approx(0.5 * M.rebate_per_share(p, "crypto"))
    assert economics.REBATE_SHARE["geopolitics"] == 0.0 and D.MAKER["maker_fee"] == 0.0
    assert M.rebate_per_share(p, "crypto", fee_schedule='{"rate": 0.09, "exponent": 1}', prospective=True) == pytest.approx(0.20 * 0.09 * 0.25)


def test_rewards_never_enter_net_and_net_is_mo_plus_rebate():
    marks = M.HistoryMarks(np.array([T + 3000 + 6 * H - 700.0]), np.array([0.50]))
    pr = _market_prints()
    _row, fills, _ = M.evaluate_opportunity(_opp(cat="crypto"), pr, pr, marks)
    f = [x for x in fills if x["rule"] == "queue" and x["side"] == "bid"][0]
    assert f["net6"] == pytest.approx(f["mo6"] + f["rebate"]) and f["mo6"] == pytest.approx(0.50 - 0.48)
    assert not any("reward" in k for k in f)


# --- estimator and placebos ------------------------------------------------------------------------------------


def _fills_frame(n_mkt=120, k=10, seed=1, beta=0.0, between=0.0, ptype="post"):
    rng = np.random.default_rng(seed)
    rows = []
    for m in range(n_mkt):
        p_m = rng.uniform(0.2, 0.8)
        mu_m = between * (p_m - 0.5)
        for j in range(k):
            x = float(rng.random() < p_m)
            rows.append({"market_id": f"m{m}", "event": f"e{m % 60}", "dep": f"d{m % 60}", "day": f"d{(m + j) % 28}", "week": f"w{j % 5}",
                         "t_fill": 1e9 + j * 3600.0 + m, "post": x, "lf": rng.random(), "net6": mu_m + beta * x + rng.normal(0, 0.01),
                         "spread": 0.04, "depth_own": 50.0 + m, "abs_chg_24h": 0.01, "price_band": 2, "side": "bid" if j % 2 else "ask", "cat": "other",
                         "mid": 0.5})
    return pd.DataFrame(rows)


def test_expanding_slope_is_zero_on_a_between_market_association_but_pooled_is_not():
    f = _fills_frame(between=0.5, beta=0.0)
    r = M.mech_test(f, "post", tid="B1", ways=["event", "dep"], n_boot=0)
    assert r["testable"] and abs(r["beta"]) < 0.006
    assert abs(r["pooled_beta"]) > 0.05  # the pooled slope picks up the market-level association
    assert r["within_between"]["between"] is not None and abs(r["within_between"]["between"]) > 0.1


def test_expanding_slope_recovers_a_within_market_effect_unshrunk():
    f = _fills_frame(n_mkt=70, k=40, between=0.0, beta=-0.01)
    r = M.mech_test(f, "post", tid="B1", ways=["event", "dep"], n_boot=0)
    assert -0.0115 < r["beta"] < -0.0085 and r["p"] < 0.01
    assert M.keeps_sign_and_floor(r["beta"], D.B_FLOORS["B1"], -1)


def test_week_fixed_effects_absorb_a_common_time_trend_in_b3():
    rng = np.random.default_rng(5)
    rows = []
    for m in range(120):
        span = rng.uniform(15, 40) * 7 * 86400.0
        for w in range(10):
            tf = w * 7 * 86400.0 + rng.uniform(0, 3 * 86400.0)
            rows.append({"market_id": f"m{m}", "event": f"e{m % 60}", "dep": f"d{m % 60}", "day": f"d{(m + w) % 28}", "week": f"w{w}", "t_fill": tf,
                         "lf": tf / span, "net6": -0.02 * w + rng.normal(0, 0.005), "spread": 0.04, "depth_own": 50.0 + m, "abs_chg_24h": 0.01,
                         "price_band": 2, "side": "bid", "cat": "other"})
    f = pd.DataFrame(rows)
    no_fe = M.mech_test(f, "lf", tid="B3", ways=["event", "dep"], n_boot=0, week_fe=False)
    fe = M.mech_test(f, "lf", tid="B3", ways=["event", "dep"], n_boot=0, week_fe=True)
    assert no_fe["beta"] < -0.05 and abs(fe["beta"]) < 0.3 * abs(no_fe["beta"])


def test_circular_shift_keeps_each_markets_large_order_count_and_permutation_keeps_multiset():
    f = _fills_frame(n_mkt=20, k=6)
    lt = {f"m{m}": np.sort(np.random.default_rng(m).uniform(1e9, 1e9 + 30 * 86400, 7)) for m in range(20)}
    spans = {f"m{m}": (1e9, 1e9 + 30 * 86400.0) for m in range(20)}
    out = M.placebo_circular_shift(f, lt, spans, seed=3)
    assert len(out) == len(f) and set(out["post"].unique()) <= {0.0, 1.0}
    assert (out["t_fill"] == f["t_fill"]).all() and (out["net6"] == f["net6"]).all()  # fills and fill prints untouched
    # the shifted stream has the same number of large orders per market (a circular shift is a bijection)
    for m in range(20):
        lo, hi = spans[f"m{m}"]
        sh = np.mod(lt[f"m{m}"] - lo + 5 * 86400.0, hi - lo)
        assert len(np.unique(sh)) == len(lt[f"m{m}"])
    perm = M.placebo_permute_within_market(f, "lf", seed=4)
    for _m, g in f.groupby("market_id"):
        assert sorted(g["lf"]) == sorted(perm.loc[g.index, "lf"])
    assert not (perm["lf"].to_numpy() == f["lf"].to_numpy()).all()


def test_mech_test_with_placebo_reports_status():
    f = _fills_frame(between=0.0, beta=-0.01)
    r = M.mech_test(f, "lf", tid="B3", ways=["event", "dep"], n_boot=0, draws=4, placebo_fn=lambda d, s: M.placebo_permute_within_market(d, "lf", s))
    assert r["placebo"]["n_draws"] == 4 and "placebo_status" in r and r["T_draft"] is not None
    adv = M.mech_advance(r, "B3", D.ALPHA_STAGE1, {})
    assert adv["advance"] is False  # lf carries no effect in this world (floor / p)


# --- economics: filters, improvement rule, brackets -----------------------------------------------------------


def _econ(n=600, seed=2, late_loss=-0.03, base=0.006, touch_sign=1.0, half_reb=0.0015, unavail_wc=None):
    """Opportunities with a bid and an ask; late-life (lf >= 0.90) quotes lose ``late_loss`` per fill, others earn ``base``."""
    rng = np.random.default_rng(seed)
    orows, frows = [], []
    for i in range(n):
        late = rng.random() < 0.3
        lf = rng.uniform(0.91, 1.0) if late else rng.uniform(0.0, 0.89)
        o = {"opp_id": f"o{i}", "market_id": f"m{i % 150}", "event": f"e{i % 90}", "dep": f"d{i % 90}", "cat": "other", "t": 1e9 + i * 7200.0,
             "spread_band": i % 3, "price_band": i % 2, "activity_tercile": i % 3, "depth_both": float(10 + i % 40), "lf_t": lf, "rt": rng.random(),
             "classifiable": True, "cancel_offset": math.nan, "bid_size": 20.0, "ask_size": 20.0,
             "day": f"d{i % 28}"}
        for rule in M.RULES:
            for side in M.SIDES:
                filled = rng.random() < 0.3
                o[f"{rule}_{side}_status"] = 1 if filled else 0
                o[f"{rule}_{side}_tfill"] = o["t"] + 600.0 if filled else math.nan
                o[f"{rule}_{side}_wc_mo"] = math.nan
                if filled:
                    mean = (late_loss if late else base) * (touch_sign if rule == "touch" else 1.0)
                    net = mean + rng.normal(0, 0.01)
                    frows.append({"opp_id": o["opp_id"], "market_id": o["market_id"], "event": o["event"], "dep": o["dep"], "day": o["day"], "cat": "other",
                                  "side": side, "rule": rule, "t": o["t"], "t_fill": o["t"] + 600.0, "price": 0.5, "net6": net, "net6_half": net - half_reb,
                                  "mark_unavailable": False, "wc_mo": -0.5, "mo6": net})
        orows.append(o)
    opps = pd.DataFrame(orows)
    if unavail_wc is not None:
        idx = opps.index[: n // 5]
        opps.loc[idx, "queue_bid_status"] = -1
        opps.loc[idx, "queue_bid_wc_mo"] = unavail_wc
    return opps, pd.DataFrame(frows)


def test_b4_removes_late_life_quotes_and_passes_the_improvement_rule():
    opps, fills = _econ()
    r = M.econ_test(opps, fills, "B4", cuts=None, stage=1, draws=50, n_boot=0, ways=["event", "dep"])
    assert r["testable"] and r["effect"] > 0.0025 and r["ev_per_quote"] > 0
    assert r["improvement"]["passes"] and r["advance"], r.get("fail")


def test_b4_filter_equal_to_u_fails_the_improvement_rule():
    opps, fills = _econ(late_loss=0.006)
    opps["lf_t"] = 0.1  # nothing is removed: the filtered maker IS U
    r = M.econ_test(opps, fills, "B4", cuts=None, stage=1, draws=50, n_boot=0, ways=["event", "dep"])
    assert r["improvement"]["improvement"] == pytest.approx(0.0) and r["improvement"]["passes"] is False and r["advance"] is False


def test_fixed_u_denominator_and_removed_quotes_stay_in_it():
    opps, fills = _econ()
    pop = opps[M.population(opps, "B4")].reset_index(drop=True)
    wide = M.fill_wide(pop, fills, "queue")
    inf = np.full(len(pop), np.inf)
    ev_all = M.ev_per_opp(wide, inf).sum() / len(pop)
    off, keep = M.real_filter(pop, "B4", None)
    ev_f = M.ev_per_opp(wide, off, keep).sum() / len(pop)
    removed = M.ev_per_opp(wide, inf, ~keep).sum() / len(pop)
    assert ev_f == pytest.approx(ev_all - removed)  # the removed quotes contribute 0 to the numerator, stay in the denominator


def test_random_filters_act_in_the_filters_own_units():
    keys = np.array(["a"] * 6 + ["b"] * 4)
    real = np.array([1, 1, 0, 0, 0, 0, 1, 0, 0, 0], bool)
    for s in range(5):
        m = M.draw_same_count(keys, real, np.random.default_rng(s))
        assert m[:6].sum() == 2 and m[6:].sum() == 1  # same number per stratum
    # B6 selects only among RT-defined opportunities; B4 population needs LF; B2 population needs classifiable markets
    opps, _ = _econ(n=50)
    opps.loc[:9, "rt"] = np.nan
    opps.loc[10:19, "lf_t"] = np.nan
    opps.loc[20:29, "classifiable"] = False
    assert M.population(opps, "B6").sum() == 40 and M.population(opps, "B4").sum() == 40 and M.population(opps, "B2").sum() == 40


def test_b2_random_cancellations_cancel_the_same_number_at_real_offsets():
    opps, fills = _econ(n=400)
    rng = np.random.default_rng(9)
    canc = rng.random(len(opps)) < 0.4
    opps["cancel_offset"] = np.where(canc, rng.uniform(100, 5000, len(opps)), np.nan)
    pop = opps.reset_index(drop=True)
    wide = M.fill_wide(pop, fills, "queue")
    r = M.improvement_rule(pop, wide, "B2", None, draws=30, pct=95.0)
    assert r["testable"] and r["n_draws"] == 30 and r["random_threshold"] >= r["random_mean"] - 1e-12
    off, keep = M.real_filter(pop, "B2", None)
    assert np.isfinite(off).sum() == canc.sum() and keep.all()


def _adv(opps, fills, **kw):
    return M.econ_test(opps, fills, "B4", cuts=None, stage=1, draws=50, n_boot=0, ways=["event", "dep"], **kw)


def test_touch_rule_sign_can_block_a_pass():
    opps, fills = _econ(touch_sign=-1.0)
    r = _adv(opps, fills)
    assert r["effect"] > 0.0025 and "robust:touch_rule_sign" in r["fail"] and r["advance"] is False


def test_rebate_halved_floor_can_block_a_pass():
    opps, fills = _econ(base=0.004, half_reb=0.002)
    r = _adv(opps, fills)
    assert r["effect"] >= 0.0025 and r["brackets"]["rebate_half_mean"] < 0.0025 and "robust:rebate_halved" in r["fail"]


def test_residual_unavailable_worst_case_can_block_a_pass():
    opps, fills = _econ(base=0.006)
    ok = _adv(opps, fills)
    assert "robust:worst_case_unavailable" not in ok["fail"]
    opps2, fills2 = _econ(base=0.006, unavail_wc=-0.5)
    r = _adv(opps2, fills2)
    assert r["brackets"]["worst_case_added"] > 0 and "robust:worst_case_unavailable" in r["fail"] and r["advance"] is False


def test_u_baseline_reports_fill_rate_and_ev_per_quote():
    opps, fills = _econ(n=200)
    f = fills.copy()
    u = M.u_baseline(opps.assign(price_band=0, spread_band=0), f)
    assert u["n_quotes"] == 200 and 0.2 < u["fill_rate_per_side"] < 0.4 and "by_side" in u


# --- declaration, guards, counting ---------------------------------------------------------------------------


def test_declaration_hash_covers_every_rule_and_changes_with_a_floor(monkeypatch):
    h0 = D.declaration_sha256()
    assert h0 == D.declaration_sha256() and len(h0) == 64
    blob = json.dumps(D.declaration_blob(), default=float)
    for needle in ("A1", "B6", "T3_A_dev_end", "expanding-past", "rt_min_prints", "seeds", "refused_run_ids", "CATEGORY_SCOPE".lower(), "category_scope"):
        assert needle in blob, needle
    monkeypatch.setitem(D.B_FLOORS, "B2", 0.01)
    assert D.declaration_sha256() != h0


def test_require_declaration_refuses_missing_or_mismatching_spec(tmp_path):
    with pytest.raises(D.DeclarationError):
        D.require_declaration(tmp_path / "nope.json")
    p = tmp_path / "cb3_v1.json"
    p.write_text(json.dumps({"declaration_sha256": "0" * 64}))
    with pytest.raises(D.DeclarationError, match="mismatch"):
        D.require_declaration(p, require_committed=False)
    p.write_text(json.dumps({"declaration_sha256": D.declaration_sha256()}))
    assert D.require_declaration(p, require_committed=False) == D.declaration_sha256()
    with pytest.raises(D.DeclarationError, match="not committed"):
        D.require_declaration(p, require_committed=True)


def test_rep_pin_floor_and_stage_time_gates(tmp_path):
    pin = tmp_path / "pin.json"
    with pytest.raises(D.WindowError):
        D.pin_rep_start("abcdef1", "2026-10-26T00:00:00Z", pin)
    D.pin_rep_start("abcdef1", "2026-10-27T00:00:00Z", pin)
    with pytest.raises(D.WindowError):
        D.pin_rep_start("abcdef1", "2026-10-28T00:00:00Z", pin)  # pinned once
    from datetime import UTC, datetime

    with pytest.raises(D.TooEarly):
        D.check_stage_allowed("replicate", datetime(2026, 11, 24, 6, tzinfo=UTC), pin)
    D.check_stage_allowed("replicate", datetime(2026, 11, 24, 13, tzinfo=UTC), pin)
    with pytest.raises(D.TooEarly):
        D.check_stage_allowed("stagep", datetime(2026, 12, 22, 6, tzinfo=UTC), pin)


def test_kind_rules_contain_cb3_kinds_and_counter_runs_on_the_real_trials_file(tmp_path):
    for k in D.TRIAL_KINDS:
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE
    real = battery2.cumulative_count()
    assert real["total"] > 0
    tp = tmp_path / "trials.jsonl"
    C.log_trials("B", {"B1": {"p": 0.2, "effect": 0.0, "n": 5}, "B2": {"p": 0.3, "n": 5}}, kind=D.KIND_TEST, role="exploratory_historical", dataset="h2_main",
                 results_path="r.json", results_sha256="s" * 8, decl_sha="d" * 8, placebo={"B1": {"n_draws": 20, "status": "read"}},
                 descriptive={"U": {"n": 1}}, trials_path=tp)
    recs = [json.loads(line) for line in tp.read_text().splitlines()]
    kinds = [r["kind"] for r in recs if r.get("evidence_role") != "placebo"]
    assert any(r.get("evidence_role") == "placebo" for r in recs)
    assert kinds.count("cb3_test") == 2 and kinds.count("cb3_descriptive") == 1 and kinds.count("ml_explain") == 1
    c = battery2.cumulative_count(tp)
    assert c["total"] == 2  # only the ml_explain n_tests counts; placebo and descriptive lines count 0
    assert provenance.TRIALS_PATH != tp


def test_results_are_never_overwritten(tmp_path):
    p = tmp_path / "S1_B" / "results.json"
    C.write_new(p, {"a": 1})
    with pytest.raises(FileExistsError):
        C.write_new(p, {"a": 2})


def test_slope_and_mean_tests_gate_on_cluster_counts_and_small_g_day_way():
    v = np.random.default_rng(0).normal(0.01, 0.01, 400)
    ways = {"event": np.arange(400) % 40, "dep": np.arange(400) % 40, "day": np.arange(400) % 20}
    ok = C.mean_test(v, ways, small_g_ways=("day",), n_boot=0)
    assert ok["testable"]  # 20 day clusters pass the small-G minimum (15) though they fail the >= 30 rule
    few = C.mean_test(v, {**ways, "day": np.arange(400) % 10}, small_g_ways=("day",), n_boot=0)
    assert few["testable"] is False and few["p"] == 1.0
    strict = C.mean_test(v, ways, n_boot=0)
    assert strict["testable"] is False  # without the small-G rule the day way would need 30


# --- history pipeline and runner (B) --------------------------------------------------------------------------


def _history_run(tmp_path, n_mkt=60, seed=4):
    import gzip as gz
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    rng = np.random.default_rng(seed)
    run = tmp_path / "history" / "h2_main"
    (run / "prices").mkdir(parents=True)
    (run / "trades").mkdir(parents=True)
    base = 1_760_000_000.0
    (run / "manifest.json").write_text(json.dumps({"request_clock_now": "2026-10-15T00:00:00Z", "lookback_days": 400}))
    frame, prog, books = [], [], []
    for m in range(n_mkt):
        mid = f"m{m}"
        frame.append({"market_id": mid, "token0": f"a{m}", "token1": f"b{m}", "event_id": f"e{m % 40}", "created_at": "2025-06-01T00:00:00Z", "start_epoch": base - 90 * 86400,
                      "end_epoch": base + 60 * 86400.0, "close_epoch": "", "closed": 0, "fee_category": "politics" if m % 3 else "crypto"})
        prog.append(json.dumps({"market_id": mid, "status": "done", "trades_truncated": False}))
        ts = np.arange(base - 40 * H, base + 3 * 86400.0, 600.0)
        rows = []
        for i, t in enumerate(ts):
            buy = rng.random() < 0.5
            rows.append({"ts": t, "side": "BUY" if buy else "SELL", "size": float(rng.integers(2, 30)), "price": 0.52 if buy else 0.48, "outcome_index": 0,
                         "wallet_hash": f"w{rng.integers(0, 12)}", "trade_key": f"{m}-{i}"})
        pd.DataFrame(rows).to_csv(run / "trades" / f"{mid}.csv.gz", index=False, compression="gzip")
        pd.DataFrame({"t": np.arange(base - 3 * 86400.0, base + 4 * 86400.0, 600.0), "p": 0.5 + rng.normal(0, 0.003, 1008)}).to_csv(run / "prices" / f"{mid}.csv.gz", index=False, compression="gzip")
        for k in range(6):
            books.append({"market_id": mid, "origin_ts": base + k * 6 * H, "state": "two_sided", "sw_best_bid": 0.48, "sw_best_ask": 0.52, "sw_bid_size_1": 5.0, "sw_ask_size_1": 5.0,
                          "sw_book_age_s": 100.0})
    with gz.open(run / "sample.csv.gz", "wt", newline="") as fh:
        pd.DataFrame(frame).to_csv(fh, index=False)
    (run / "progress.jsonl").write_text("\n".join(prog) + "\n")
    bpath = tmp_path / "book_features.csv.gz"
    pd.DataFrame(books).to_csv(bpath, index=False, compression="gzip")
    return run, bpath


def test_history_census_is_counts_only_and_never_touches_marks(tmp_path, monkeypatch):
    run, bpath = _history_run(tmp_path)

    def boom(*a, **k):
        raise AssertionError("the census must not build or read marks")

    monkeypatch.setattr(M.HistoryMarks, "mark", boom)
    monkeypatch.setattr(M.HistoryMarks, "last_before", boom)
    c = M.census_history(run, bpath)
    assert c["n_quote_opportunities_all"] > 100 and c["fills"]["queue_bid"]["filled"] > 0
    assert c["frozen_cuts_proposal"]["activity_tercile_cuts"] is not None
    text = json.dumps(c)
    for bad in ("net6", "mo6", "mark6", "ev_per_quote", "mean_net"):
        assert bad not in text
    with pytest.raises(D.Cb3Error):
        M.assert_no_marks(pd.DataFrame({"mark6": [1.0]}))
    with pytest.raises(D.Cb3Error):
        M.assert_no_marks(pd.DataFrame({"m_T": [1.0]}))


def test_history_screen_runs_end_to_end_and_reports_all_six_tests(tmp_path):
    run, bpath = _history_run(tmp_path)
    cuts = {"rt_top_decile_cut": 0.2, "activity_tercile_cuts": [20.0, 60.0]}
    res = M.screen_history(run, bpath, cuts, n_boot=0, placebo_draws=3, random_draws=10)
    assert set(res["tests"]) == {"B1", "B2", "B3", "B4", "B5", "B6"}
    assert res["descriptive"]["U_non_sports"]["n_quotes"] > 100
    for tid in ("B1", "B3", "B5"):
        t = res["tests"][tid]
        assert "advance" in t and ("placebo" in t or not t.get("testable"))
    assert all(isinstance(t.get("advance"), bool) for t in res["tests"].values())


def test_runner_B_screen_needs_frozen_cuts_and_logs_six_tests(tmp_path):
    import run_cb3

    run, bpath = _history_run(tmp_path)
    spec = tmp_path / "cb3_v1.json"
    spec.write_text(json.dumps({"declaration_sha256": D.declaration_sha256()}))
    args = ["screen", "--family", "B", "--history-root", str(run.parent), "--books", str(bpath), "--out-root", str(tmp_path / "out"), "--trials", str(tmp_path / "t.jsonl"),
            "--spec", str(spec), "--n-boot", "0", "--placebo-draws", "2", "--random-filter-draws", "5"]
    assert run_cb3.main(args) == run_cb3.REFUSED_EXIT  # the committed spec carries no frozen cuts
    spec.write_text(json.dumps({"declaration_sha256": D.declaration_sha256(), "frozen_cuts": {"rt_top_decile_cut": 0.2, "activity_tercile_cuts": [20.0, 60.0]}}))
    assert run_cb3.main(args) == 0
    recs = [json.loads(line) for line in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert sorted(r["preset"] for r in recs if r["kind"] == "cb3_test" and r["evidence_role"] != "placebo") == ["B1", "B2", "B3", "B4", "B5", "B6"]
    assert [r["n_tests"] for r in recs if r["kind"] == "ml_explain"] == [6]
    assert run_cb3.main(args) == run_cb3.REFUSED_EXIT  # never overwritten


def test_runner_census_B_writes_counts_and_refuses_reserved_runs(tmp_path):
    import run_cb3

    run, bpath = _history_run(tmp_path)
    args = ["census", "--family", "B", "--history-root", str(run.parent), "--books", str(bpath), "--out-root", str(tmp_path / "out"), "--trials", str(tmp_path / "t.jsonl")]
    assert run_cb3.main(args) == 0
    assert json.loads((tmp_path / "out" / "census.json").read_text())["B"]["n_quote_opportunities_all"] > 100
    assert run_cb3.main([*args, "--run-id", "h3_power"]) == run_cb3.REFUSED_EXIT


def test_batch_holm_over_the_stage2_family_and_expected_family():
    s1a = {"tests": {"A1": {"advance": True}, "A2": {"advance": False}}}
    s1b = {"tests": {"B1": {"advance": False, "entry_exception_stage2": True}, "B2": {"advance": True}, "B3": {"advance": False}}}
    exp = C.stage2_expected(s1a, s1b)
    assert exp == ["A1", "A3", "B1", "B2"]
    docs = [("S2_A", {"tests": {"A1": {"p": 0.001, "advance": True}}}), ("S2_B", {"tests": {"B1": {"p": 0.2, "advance": True}, "B2": {"p": 0.004, "advance": True}}})]
    bh = C.batch_holm(docs, exp)
    assert bh["m"] == 4 and bh["missing_stage2_counted_p1"] == ["A3"] and bh["replicated"] == ["A1", "B2"]
    with pytest.raises(D.Cb3Error):
        C.batch_holm([("x", {"tests": {"B6": {"p": 0.1}}})], exp)


# --- prospective pipeline -----------------------------------------------------------------------------------


def _prospective_world(tmp_path, n_mkt=4, n_cap=8):
    import gzip as gz

    from astrolabe.research_lab import cb3_quote_vacuum as V

    t0 = D.epoch("2026-10-27T00:00:00Z")
    frames = []
    for c in range(n_cap):
        st = t0 + c * 2 * H
        rows = []
        for m in range(n_mkt):
            rows.append({"market_id": f"m{m}", "condition_id": f"c{m}", "event_id": f"e{m}", "best_bid": "0.48", "best_ask": "0.52", "spread": "0.04", "last_trade_price": "0.5",
                         "volume_num": "100", "closed": "False", "accepting_orders": "True", "end_date": "2026-12-31T00:00:00Z", "created_at": "2026-09-01T00:00:00Z",
                         "fee_category": "politics", "fee_schedule": "",
                         "s1_batch_receipt_utc": D.iso(st + 600), "s1_best_bid": "0.48", "s1_best_ask": "0.52", "s1_bid_size_1": "5", "s1_ask_size_1": "5"})
        frames.append((f"c{c:03d}", st, pd.DataFrame(rows), None))
    P = V.panel_from_frames(frames)
    fu = tmp_path / "fu"
    rng = np.random.default_rng(1)
    for c in range(1, n_cap):
        d = fu / f"c{c:03d}"
        prev_t = t0 + (c - 1) * 2 * H + 600
        pre, post = [], []
        for m in range(n_mkt):
            for i in range(80):
                pre.append({"market_id": f"m{m}", "condition_id": f"c{m}", "ts": prev_t - 30 * 60 - i * 300, "side": "BUY" if rng.random() < 0.5 else "SELL", "outcome_index": 0,
                            "asset": "a", "size": 5.0, "price": 0.5, "wallet_hash": f"w{i % 7}"})
            for i in range(40):
                buy = rng.random() < 0.5
                post.append({"market_id": f"m{m}", "condition_id": f"c{m}", "ts": prev_t + 60 + i * 150, "side": "BUY" if buy else "SELL", "price": 0.52 if buy else 0.48, "size": 6.0,
                             "outcome_index": 0, "asset": "a", "tx_hash": f"0x{i}", "wallet_hash": f"w{i % 7}"})
        (d / "pre").mkdir(parents=True)
        (d / "post").mkdir(parents=True)
        pd.DataFrame(pre).to_csv(d / "pre" / "wallets.csv.gz", index=False, compression="gzip")
        pd.DataFrame(post).to_csv(d / "post" / "trades.csv.gz", index=False, compression="gzip")
        req = prev_t + 10 * H
        (d / "plan.json").write_text(json.dumps({"frac": 0.5, "inclusion_float": {f"m{m}": 0.25 for m in range(n_mkt)}}))
        (d / "manifest.json").write_text(json.dumps({"state": "complete"}))
        (d / "meta.json").write_text(json.dumps({"requests": 8, "n_429": 0, "markets": {f"post:m{m}": {"status": "ok", "request_epoch": req, "page_cap": False, "oldest_ts": None} for m in range(n_mkt)}}))
    _ = gz
    return P, M.FollowupReader(fu), fu


def test_build_prospective_uses_first_sweep_origin_pre_before_t_post_after_and_later_sweeps_for_marks(tmp_path):
    P, reader, _fu = _prospective_world(tmp_path)
    u = M.build_prospective(P, reader)
    opps, fills = u["opps"], u["fills"]
    assert len(opps) == 7 * 4 and u["diag"]["kept"] == 28
    assert (opps["t"] == P.mat["s1_recv"][0, :7].repeat(4).reshape(7, 4)[:, 0].repeat(4)).all() or opps["t"].nunique() == 7  # t = the first-sweep receipt of each pass
    assert opps["classifiable"].all() and opps["w"].iloc[0] == pytest.approx(1.0 / (0.25 * 0.5))
    q = fills[(fills["rule"] == "queue") & fills["mark6"].notna()]
    assert len(q) > 0
    assert (q["mark6"] == 0.5).all()  # later first sweeps are tight 0.48/0.52
    assert ((q["t_fill"] - q["t"]) > 0).all()
    # nothing from the future pass leaks into the pre-origin features: a pre print at or after t is dropped
    assert (opps["activity"] > 0).all()


def test_prospective_census_is_counts_only_and_states_stage2_mde(tmp_path):
    P, reader, fu = _prospective_world(tmp_path)
    c = M.census_prospective(P, reader, followup_root=fu, qs_root=tmp_path / "qs")
    assert c["n_quote_opportunities"] == 28 and c["followup_requests"] == 7 * 8 and c["passes_missing_followup"] == 0
    assert c["stage2_mde"]["B2_B4_mde"] > 0 and c["stage2_mde"]["design_effect"] >= 1.0
    for bad in ("net6", "mo6", "mark6", "mean_net"):
        assert bad not in json.dumps(c)


def test_screen_prospective_returns_stage2_structure_with_small_g_day_way(tmp_path):
    P, reader, _fu = _prospective_world(tmp_path)
    cuts = {"rt_top_decile_cut": 0.2, "activity_tercile_cuts": [10.0, 40.0]}
    res = M.screen_prospective(P, reader, cuts, ["B1", "B2", "B3", "B4", "B5", "B6"], stage=2, n_boot=0, placebo_draws=2, random_draws=5)
    assert set(res["tests"]) == {"B1", "B2", "B3", "B4", "B5", "B6"} and res["stage"] == 2
    assert all(t.get("advance") is False for t in res["tests"].values())  # 28 quotes: far below the testability floors
