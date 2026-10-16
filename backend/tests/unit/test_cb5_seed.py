# ruff: noqa: E501
"""CB5-G seed-anchor reversion (astrolabe.research_lab.cb5_seed)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import cb5_seed as s

L0 = 1_760_000_000.0
H = 3600.0


def trades(rows):
    """rows: (ts, side, size, price, outcome_index)."""
    return pd.DataFrame(rows, columns=["ts", "side", "size", "price", "outcome_index"]).assign(wallet_hash="", trade_key="k")


def rec(**kw):
    r = {"market_id": "m1", "event_id": "e1", "fee_category": "politics", "created": L0, "end": L0 + 20 * 86400, "close": math.nan, "y0": math.nan, "negrisk_members": 0, "stratum": "s"}
    r.update(kw)
    return r


def series(points):
    ts = np.array([p[0] for p in points], float)
    return ts, np.array([p[1] for p in points], float)


def basic_market(**kw):
    """Seed 0.40 two hours before the first trade; first-day trades near 0.50; entry and exit prints exist."""
    ts, vals = series([(L0 + 600, 0.40), (L0 + 3 * H, 0.50), (L0 + 25 * H, 0.52), (L0 + 31 * H, 0.52), (L0 + 66 * H, 0.46), (L0 + 72 * H, 0.46)])
    tr = trades([
        (L0 + 2 * H, "BUY", 10, 0.50, 0), (L0 + 3 * H, "BUY", 10, 0.51, 0), (L0 + 10 * H, "SELL", 10, 0.49, 0),
        (L0 + 25 * H, "BUY", 10, 0.52, 0), (L0 + 68 * H, "BUY", 10, 0.47, 0), (L0 + 69 * H, "SELL", 10, 0.46, 0),
    ])
    return rec(**kw), ts, vals, tr


# ---- seed definition ----------------------------------------------------------------------------------------------------


def test_seed_plus_600_rule_and_latest_point():
    t_ft = L0 + 5 * H
    ts, vals = series([(t_ft - 540, 0.7), (t_ft - 600, 0.4), (L0 - 700, 0.9), (L0 - 600, 0.3)])
    st, sv = s.seed_points(ts, vals, t_ft, L0)
    assert set(sv) == {0.4, 0.3}  # 9 min before the first trade is out, 10 min before is in; L - 600 is in, L - 700 is out
    sd = s.seed(ts, vals, t_ft, L0)
    assert sd["sigma"] == 0.4 and sd["n"] == 2  # latest usable point
    assert s.seed(*series([(t_ft - 300, 0.5)]), t_ft, L0) is None


def test_template_tolerance():
    assert s.is_template_seed(0.50049) and not s.is_template_seed(0.5006) and s.is_template_seed(0.4996)


def test_token_mapping_and_sides():
    tr = trades([(1, "BUY", 1, 0.6, 0), (2, "SELL", 1, 0.6, 0), (3, "BUY", 1, 0.3, 1), (4, "SELL", 1, 0.3, 1)])
    m = s.map_token0(tr)
    assert list(m["p0"]) == [0.6, 0.6, 0.7, 0.7]
    assert list(m["ask_side"]) == [True, False, False, True]  # token0 BUY, token1 SELL are ask side
    assert list(m["bid_side"]) == [False, True, True, False]


def test_window_count_is_integer_only():
    tr = trades([(1, "BUY", 5, 0.6, 0), (2, "SELL", 7, 0.7, 0)])
    n = s.window_count(tr, 0, 10)
    assert isinstance(n, int) and n == 2


# ---- units, windows, exclusions -----------------------------------------------------------------------------------------


def test_unit_built_and_feature_target_windows_disjoint():
    r, ts, vals, tr = basic_market()
    u, why, _ = s.g_unit(r, ts, vals, tr, False, None, stage="rep")
    assert why == "ok" and u["sigma"] == 0.40
    assert u["d"] == pytest.approx(u["vwap1"] - 0.40)
    # a planted shock in the last feature hour changes VWAP1 but not the entry price E
    tr2 = pd.concat([tr, trades([(L0 + 23.5 * H, "BUY", 1000, 0.90, 0)])], ignore_index=True)
    u2, _, _ = s.g_unit(r, ts, vals, tr2, False, None, stage="rep")
    assert u2["E"] == u["E"] and u2["vwap1"] != u["vwap1"]


def test_truncated_before_L_is_unavailable_and_h2_clock_rule():
    r, ts, vals, tr = basic_market()
    u, why, tu = s.g_unit(r, ts, vals, tr, True, L0 + 5 * H, stage="rep")
    assert u is None and why == "trades_truncated_before_L"
    u, why, _ = s.g_unit(r, ts, vals, tr, True, L0 - 10, stage="rep")  # history known to reach L
    assert why == "ok"
    u, why, _ = s.g_unit(r, ts, vals, tr, False, None, stage="h2", clock=L0 + 4 * 86400)  # L + 4d + 1h > clock
    assert why == "after_h2_clock"
    u, why, _ = s.g_unit(r, ts, vals, tr, False, None, stage="h2", clock=L0 + 5 * 86400)
    assert why == "ok"


def test_early_resolution_pays_out_and_inclusion_unchanged():
    r, ts, vals, tr = basic_market()
    u0, why0, _ = s.g_unit(r, ts, vals, tr, False, None, stage="rep")
    r2 = {**r, "close": L0 + 60 * H, "y0": 1.0}
    u1, why1, _ = s.g_unit(r2, ts, vals, tr, False, None, stage="rep")
    assert why0 == why1 == "ok" and u1["early_close"] and u1["X"] == 1.0 and u0["X"] != 1.0


def test_population_exclusions():
    r, ts, vals, tr = basic_market()
    assert s.g_unit({**r, "fee_category": "weather"}, ts, vals, tr, False, None, stage="rep")[1] == "weather"
    assert s.g_unit({**r, "negrisk_members": 5}, ts, vals, tr, False, None, stage="rep")[1] == "negrisk_multi"
    assert s.g_unit({**r, "end": L0 + 3 * 86400}, ts, vals, tr, False, None, stage="rep")[1] == "life_lt_4d"
    few = tr.iloc[[0, 1]]
    assert s.g_unit(r, ts, vals, few, False, None, stage="rep")[1] == "lt3_trades"
    ts2, vals2 = series([(L0 + 3 * H, 0.5)])  # no point before the first trade
    assert s.g_unit(r, ts2, vals2, tr, False, None, stage="rep")[1] == "no_seed"


# ---- G2 -----------------------------------------------------------------------------------------------------------------


def _g2_df(print_price, d=0.10, created=None):
    r, ts, vals, tr = basic_market(created=created or L0)
    u, _, _ = s.g_unit(r, ts, vals, tr, False, None, stage="rep")
    u = {**u, "d": d, "p_t1": 0.52, "p_t3": 0.46, "informative": True}
    q_ask = min(0.52 + max(0.0, 0.0) + 0.0, 0.99)
    assert q_ask
    u["ask_prints"] = pd.DataFrame({"ts": [L0 + 26 * H], "p0": [print_price]})
    u["bid_prints"] = pd.DataFrame({"ts": [], "p0": []})
    return pd.DataFrame([u])


def test_g2_trade_through_strict_and_binding_cost():
    from astrolabe.research_lab import cost_regimes

    rg = cost_regimes.cost_regime("2026-10-12", "politics", 0.52)
    q = min(0.52 + s.h_gen(0.52, rg) + 0.01, 0.99)
    at = s.g2_orders(_g2_df(q))
    assert not at["filled"].iloc[0]  # a print AT q does not fill
    beyond = s.g2_orders(_g2_df(q + 0.001))
    assert beyond["filled"].iloc[0] and math.isfinite(beyond["net"].iloc[0])
    bound = s.g2_orders(_g2_df(q + 0.001), bind=s.BIND_COST)
    assert bound["net"].iloc[0] < beyond["net"].iloc[0] - 0.0074  # +0.75c worse exit (plus its fee)


def test_g2_adverse_selection_only_before_rollout(tmp_path, monkeypatch):
    from astrolabe.research_lab import cost_regimes

    reg = tmp_path / "reg.json"
    reg.write_text('{"version": "cost-regimes-v1", "a_AS_cents": 1.0, "fee_rate_add": 0.0, "half_spread_add": 0.0, "era_rule": "pooled_allowed"}')
    monkeypatch.setattr(cost_regimes, "REGISTER_PATH", reg)
    pre_ts = 1_740_000_000.0  # 2025-02: before the rollout
    rg_pre = cost_regimes.cost_regime("2025-02-20", "politics", 0.5)
    rg_post = cost_regimes.cost_regime("2026-10-12", "politics", 0.5)
    assert rg_pre["a_as_cents"] == 1.0 and rg_post["a_as_cents"] == 0.0
    assert pre_ts < L0


# ---- G1 estimators and placebos ----------------------------------------------------------------------------------------


def fixture_units(n=600, *, anchoring=0.0, level=0.0, group=0.0, template_share=0.0, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    gshift = {}
    for i in range(n):
        v = rng.uniform(0.2, 0.8)
        tpl = rng.random() < template_share
        wk = f"2026-W{(i % 12) + 1:02d}"
        cat = ("politics", "crypto")[i % 2]
        sig = 0.5 if tpl else rng.uniform(0.2, 0.8)
        key = (wk, cat)
        if group and key not in gshift:
            gshift[key] = rng.normal(0, 0.12)
        if group:
            sig = float(np.clip(0.5 + gshift[key] + rng.normal(0, 0.02), 0.05, 0.95)) if not tpl else 0.5
        d = v - sig
        y = -anchoring * (0 if tpl else d) - level * (v - 0.5) + rng.normal(0, 0.05)
        if group:
            y += 0.6 * gshift[key]
        rows.append({"market_id": f"m{i}", "event": f"e{i}", "listing_date": f"2026-10-{(i % 40) + 1:02d}", "iso_week": wk, "fee_category": cat, "sigma": sig,
                     "vwap1": v, "d": d, "y": y, "informative": not tpl, "template": tpl, "sports": False, "stratum": f"st{i % 4}"})
    return pd.DataFrame(rows)


def test_placebo_level_controlled_calibrated_raw_not_under_pure_level_reversion():
    df = fixture_units(level=0.8)
    inf = s.primary(df)
    assert s.stage1_advance_g1(s.g1_slope(inf, n_boot=0))  # level reversion alone makes the raw slope "advance"
    assert not s.stage1_advance_g1(s.g1_level_controlled(inf, n_boot=0))
    pl = s.seed_permutation_placebo(inf, n_draws=60)
    assert pl["advance_rate_level_controlled"] <= s.PLACEBO_MAX_RATE and pl["ok"]
    assert pl["advance_rate_raw"] > 0.5  # a raw-slope placebo would reject true anchoring and also advance here


def test_placebo_stays_calibrated_with_real_anchoring_and_level_reversion():
    df = fixture_units(anchoring=0.5, level=0.4, seed=3)
    inf = s.primary(df)
    assert s.stage1_advance_g1(s.g1_level_controlled(inf, n_boot=0))
    pl = s.seed_permutation_placebo(inf, n_draws=60)
    assert pl["ok"]


def test_placebo_can_fail_when_seeds_carry_group_information():
    """A fixture with no own-seed anchoring but group-level seed structure shared within fee_category x week: permuting inside
    the group does not break the link, so the calibration fails (it can fail)."""
    df = fixture_units(group=1.0, seed=11)
    inf = s.primary(df)
    pl = s.seed_permutation_placebo(inf, n_draws=60)
    assert pl["advance_rate_level_controlled"] > s.PLACEBO_MAX_RATE and not pl["ok"]


def test_template_stratum_blocks_pure_level_reversion_and_credits_anchoring():
    pure = fixture_units(level=0.8, template_share=0.25, seed=5)
    inf = s.primary(pure)
    b_inf = s.g1_slope(inf, n_boot=0)["beta"]
    res = s.template_stratum(pure, b_inf)
    assert res["status"] == "generic_first_day_reversal" and not res["credited"]
    anch = fixture_units(anchoring=0.5, level=0.3, template_share=0.25, seed=5)
    b2 = s.g1_slope(s.primary(anch), n_boot=0)["beta"]
    res2 = s.template_stratum(anch, b2)
    assert res2["status"] == "credited" and res2["credited"]
    few = fixture_units(level=0.8, template_share=0.02, seed=5)
    assert s.template_stratum(few, -0.3)["status"] == "unverified"  # < 50 template units: attribution unverified


def test_stratum_adjusted_uses_strata_and_carry_rule():
    df = s.primary(fixture_units(anchoring=0.5, seed=2))
    adj = s.g1_stratum_adjusted(df)
    assert adj["testable"] and adj["beta"] < 0
    assert s.carry_rule(True, {"testable": False, "size_only": True, "mean": 0.01})["carried"]
    assert not s.carry_rule(True, {"testable": False, "size_only": True, "mean": -0.01})["carried"]
    assert not s.carry_rule(True, {"testable": True, "size_only": False, "mean": 0.01})["carried"]
    assert not s.carry_rule(False, {"testable": False, "size_only": True, "mean": 0.01})["carried"]


# ---- census guard and gates ---------------------------------------------------------------------------------------------


def test_census_trim_drops_target_window_prices_and_rows():
    r, ts, vals, tr = basic_market()
    tts, tvals, ttr, bound = s.trim_census(ts, vals, tr, L0)
    assert bound == min(L0 + 2 * H + H, L0 + 24 * H)
    assert tts.max() <= bound and ttr["ts"].max() <= bound
    facts = s.census_market(r, ts, vals, tr)
    assert facts["valid_seed"] and facts["sigma"] == 0.40 and not facts["echo"]


def test_seed_echo_share_and_book_agreement():
    echo = s.seed_echo_share([{"valid_seed": True, "echo": True}] * 6 + [{"valid_seed": True, "echo": False}] * 4)
    assert echo["stop"]
    ok = [{"sigma": 0.45, "t_ft": 100.0, "first_seen_ts": 50.0, "bid": 0.43, "ask": 0.47}] * 60
    assert s.seed_book_agreement(ok)["status"] == "pass"
    bad = [{"sigma": 0.20, "t_ft": 100.0, "first_seen_ts": 50.0, "bid": 0.43, "ask": 0.47}] * 60
    assert s.seed_book_agreement(bad)["status"] == "fail"
    # only markets first seen BEFORE the first trade with a tight two-sided touch are checkable
    late = [{"sigma": 0.45, "t_ft": 100.0, "first_seen_ts": 150.0, "bid": 0.43, "ask": 0.47}] * 60
    wide = [{"sigma": 0.45, "t_ft": 100.0, "first_seen_ts": 50.0, "bid": 0.30, "ask": 0.60}] * 60
    assert s.seed_book_agreement(late)["status"] == "unverified" and s.seed_book_agreement(wide)["n_checkable"] == 0


def test_g56_gate_and_side_audit():
    df = s.primary(fixture_units(n=200))
    g = s.g56_gate(df)
    assert g["ok"] and g["n_units"] == 200
    assert not s.g56_gate(df.head(50))["ok"]
    r, ts, vals, tr = basic_market()
    good = s.side_audit_day0([(ts, vals, tr, L0)])
    assert isinstance(good["ok"], bool)
