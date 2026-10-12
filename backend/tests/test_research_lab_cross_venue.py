"""Unit tests for the cross-venue (Polymarket vs Kalshi) exploratory study module."""

from __future__ import annotations

import math

import numpy as np

from astrolabe.research_lab import cross_venue as cv

DAY = 86400


def test_tokenize_numbers_and_months():
    w, n = cv.tokenize("Will the Fed cut rates by 25 bps in Sept 2026? Above $150,000 or 4.50%")
    assert {"150000", "25", "2026", "4.5"} <= n
    assert "september" in w and "will" not in w and "the" not in w
    assert cv.tokenize("Bitcoin above 150k")[1] == frozenset({"150000"})
    assert (
        cv.tokenize("Unemployment rate in Mar 2026")[0]
        == cv.tokenize("unemployment rate march 2026")[0]
    )


def _k(t, title, close="2026-03-10T00:00:00Z", sub=""):
    return {
        "ticker": t,
        "event_ticker": "E-" + t,
        "title": title,
        "yes_sub": sub,
        "close_time": close,
        "result": "yes",
    }


def _p(i, q, end="2026-03-10T05:00:00Z", outcomes=("Yes", "No")):
    return {
        "market_id": i,
        "event_id": "ev" + i,
        "question": q,
        "item": "",
        "outcomes": list(outcomes),
        "end": end,
        "closed_time": "",
        "outcome_prices": '["1","0"]',
    }


def test_match_accepts_exact_and_rejects_mismatches():
    k = [
        _k("K1", "Will Bitcoin reach $150,000 in March 2026?"),
        _k("K2", "Will Bitcoin reach $160,000 in March 2026?"),
        _k("K3", "Will Anthony Albanese win the election?", close="2026-03-10T00:00:00Z"),
    ]
    p = [
        _p("P1", "Will Bitcoin reach $150,000 in March 2026?"),
        _p("P2", "Will Bitcoin reach $150,000 in March 2026?", end="2026-05-10T00:00:00Z"),
        _p("P3", "Will Anthony Albanese win the election?", outcomes=("Albanese", "Dutton")),
    ]
    got = {(m.k_ticker, m.p_market_id) for m in cv.match_markets(k, p)}
    # K2 differs in number, P2 differs in date by 2 months, P3 is not Yes/No
    assert got == {("K1", "P1")}


def test_match_drops_ambiguous_ties():
    k = [_k("K1", "Will Alice win the March 2026 mayoral election in Springfield?")]
    p = [
        _p("P1", "Will Alice win the March 2026 mayoral election in Springfield?"),
        _p("P2", "Will Alice win the March 2026 mayoral election in Springfield?"),
    ]
    assert cv.match_markets(k, p) == []


def test_parse_k_candles_live_and_historical_fields():
    live = {
        "end_period_ts": 120,
        "yes_bid": {"close_dollars": "0.40"},
        "yes_ask": {"close_dollars": "0.44"},
        "price": {"close_dollars": "0.42"},
        "volume_fp": "3.00",
    }
    hist = {
        "end_period_ts": 60,
        "yes_bid": {"close": "0.30"},
        "yes_ask": {"close": "0.34"},
        "price": {"close": "0.32"},
        "volume": "5.00",
    }
    a = cv.parse_k_candles([live, hist])
    assert a[:, 0].tolist() == [60.0, 120.0]
    assert a[1].tolist() == [120.0, 0.40, 0.44, 0.42, 3.0]
    assert a[0, 1] == 0.30


def test_k_mid_requires_two_sided_tight_quote():
    c = np.array(
        [
            [60, 0.0, 0.05, 0.03, 0],
            [120, 0.40, 0.44, 0.42, 1],
            [180, 0.30, 0.60, 0.4, 1],
            [240, 0.50, 1.0, 0.5, 1],
        ],
        dtype=float,
    )
    ts, mid, spr = cv.k_mid_series(c)
    assert ts.tolist() == [120.0] and abs(mid[0] - 0.42) < 1e-12 and abs(spr[0] - 0.04) < 1e-12


def test_asof_point_in_time_lag_and_age():
    ts = np.array([1000.0, 2000.0])
    t = np.array([1500.0, 1600.0, 2599.0, 2600.0, 9000.0])
    # lag 600: the point stamped 1000 is usable only from 1600; the one at 2000 from 2600
    idx = cv.asof_index(ts, t, 600.0, 3600.0)
    assert idx.tolist() == [-1, 0, 0, 1, -1]


def test_align_pair_grid_and_point_in_time():
    ps = [(0, 0.5), (600, 0.52), (3000, 0.6)]
    kc = np.array([[60 * i, 0.50, 0.54, 0.5, 0] for i in range(1, 100)], dtype=float)
    g = cv.align_pair(ps, kc, 0, 3600)
    assert g["t"].tolist() == [600.0 * i for i in range(7)]
    assert np.isnan(g["p"][0])  # the point stamped 0 is usable only from 600
    assert g["p"][1] == 0.5 and g["p"][2] == 0.52
    assert g["p"][5] == 0.52  # the point stamped 3000 is not yet usable at 3000
    assert g["p"][6] == 0.6
    assert np.isnan(g["k"][0])  # no Kalshi candle has ended by t=0
    assert abs(g["k"][3] - 0.52) < 1e-12 and abs(g["kspr"][3] - 0.04) < 1e-12


def _series(cluster, p, k, kspr=0.02):
    n = len(p)
    return cv.PairSeries(
        f"pair-{cluster}",
        cluster,
        {"t": np.arange(n) * cv.GRID_S + 1e9, "p": p, "k": k, "kspr": np.full(n, kspr)},
    )


def _rw(rng, n, vol=0.006, start=0.5):
    x = np.cumsum(rng.normal(0, vol, n)) + start
    return np.clip(x, 0.1, 0.9)


def test_leadlag_detects_kalshi_leading():
    rng = np.random.default_rng(1)
    pairs = []
    for i in range(30):
        k = _rw(rng, 800)
        p = np.concatenate([[k[0]] * 2, k[:-2]]) + rng.normal(0, 0.001, 800)  # P lags K by 2 steps
        pairs.append(_series(f"c{i}", p, k))
    r = cv.leadlag(pairs, n_boot=300)["lags_min"]
    assert r[20]["K_to_P"] > 0.7 and r[20]["asym"] > 0.5
    assert r[20]["asym_ci"][0] > 0 and r[20]["p_two_sided"] < 0.05
    assert abs(r[10]["asym"]) < 0.2 + 0.5  # lag 1 carries no deterministic structure
    assert abs(r[0]["K_to_P"]) < 0.1


def test_leadlag_null_is_symmetric():
    rng = np.random.default_rng(2)
    pairs = [_series(f"c{i}", _rw(rng, 800), _rw(rng, 800)) for i in range(30)]
    r = cv.leadlag(pairs, n_boot=300)["lags_min"]
    assert all(abs(v["asym"]) < 0.1 for v in r.values())


def test_granger_oos_gap_helps_when_p_chases_k_and_not_under_null():
    rng = np.random.default_rng(3)
    pairs = []
    for i in range(40):
        k = _rw(rng, 1500, vol=0.004)
        p = np.empty(1500)
        p[0] = k[0]
        for s in range(1, 1500):  # error-correction toward K plus noise
            p[s] = p[s - 1] + 0.5 * (k[s - 1] - p[s - 1]) + rng.normal(0, 0.002)
        pairs.append(_series(f"c{i}", np.clip(p, 0.1, 0.9), k))
    r = cv.granger_oos(pairs, 1, "gap", n_boot=300)
    assert r["status"] == "ok" and r["rel_mse_gain"] > 0.2 and r["ci"][0] > 0
    assert r["p_one_sided"] < 0.01 and r["blocks_positive"] == len(r["blocks"]) == 3
    null = [_series(f"n{i}", _rw(rng, 1500, 0.004), _rw(rng, 1500, 0.004)) for i in range(40)]
    n = cv.granger_oos(null, 1, "gap", n_boot=300)
    assert n["ci"][0] < 0.005 and abs(n["rel_mse_gain"]) < 0.05


def test_granger_training_never_sees_the_test_block():
    rng = np.random.default_rng(4)
    pairs = [_series(f"c{i}", _rw(rng, 600), _rw(rng, 600)) for i in range(10)]
    t = np.concatenate([p.g["t"] for p in pairs])
    r = cv.granger_oos(pairs, 6, "gap", n_boot=50)
    assert r["status"] == "ok" and len(r["blocks"]) == 3 and t.size > 0


def test_error_correction_identifies_the_mover():
    rng = np.random.default_rng(5)
    pairs = []
    for i in range(30):
        n = 1200
        k = _rw(rng, n, 0.003)
        p = np.empty(n)
        p[0] = k[0]
        for s in range(1, n):
            p[s] = p[s - 1] + 0.3 * (k[s - 1] - p[s - 1]) + rng.normal(0, 0.002)
        pairs.append(_series(f"c{i}", np.clip(p, 0.1, 0.9), k))
    r = cv.error_correction(pairs, 1, n_boot=300)
    assert r["beta_P"] > 0.2 and r["beta_P_ci"][0] > 0.1
    assert abs(r["beta_K"]) < 0.1 and r["p_beta_P"] < 0.01


def test_jump_leadership_kalshi_first():
    n = 200
    k = np.full(n, 0.40)
    p = np.full(n, 0.40)
    for j in range(50, 60):
        k[j:] = 0.40 + 0.12 * min(1.0, (j - 49) / 3)  # K jumps within 3 steps
    p[53:] = 0.52  # P follows three steps later
    pairs = [_series("c0", p.copy(), k.copy()), _series("c1", p.copy(), k.copy())]
    ev = cv.jump_events(pairs[0])
    assert len(ev) >= 1 and all(e["lead"] > 0 for e in ev)
    r = cv.jump_leadership(pairs, n_boot=200)
    assert r["mean_lead_steps"] > 0 and r["counts"]["P_first"] == 0


def test_half_life_recovers_ar1():
    rng = np.random.default_rng(6)
    phi = 0.8
    pairs = []
    for i in range(30):
        g = np.zeros(1500)
        for s in range(1, 1500):
            g[s] = phi * g[s - 1] + rng.normal(0, 0.01)
        p = np.full(1500, 0.5)
        pairs.append(_series(f"c{i}", p, p + g))
    r = cv.half_life(pairs, n_boot=200)
    assert abs(r["phi_all"] - phi) < 0.03
    assert abs(r["half_life_min_all"] - math.log(0.5) / math.log(phi) * 10) < 5


def test_by_across_matches_manual_computation():
    out = cv.by_across({"a": 0.001, "b": 0.01, "c": 0.5})
    c = 1 + 1 / 2 + 1 / 3
    assert abs(out["a"]["p_by"] - min(0.001 * 3 * c / 1, 0.01 * 3 * c / 2, 0.5 * 3 * c / 3)) < 1e-12
    assert out["a"]["pass_by"] and not out["c"]["pass_by"]


def test_economics_costs_remove_small_gaps():
    n = 300
    p = np.full(n, 0.5)
    k = p + 0.01  # 1c gap, below 1c K half-spread + 1c PM half-spread
    big = p + 0.10
    r = cv.economics(
        [_series("a", p, k), _series("b", p, big)], pm_half_spreads=(0.01,), pm_fee_rates=(0.05,)
    )
    s = r["scenarios"][0]
    assert 0.45 < s["share_steps_net_positive"] < 0.55
    assert s["pairs_with_persistent_positive"] == 1


def test_match_rejects_conflict_words_on_one_side():
    k = [
        _k(
            "K1",
            "Will the margin of victory for Lula in round one of the 2026 vote be over 5 points?",
        )
    ]
    p = [_p("P1", "Will Lula win round one of the 2026 vote over 5 points?")]
    assert cv.match_markets(k, p) == []
    k2 = [_k("K2", "Will Lula win round one of the 2026 vote over 5 points?")]
    assert len(cv.match_markets(k2, p)) == 1


def test_select_pairs_caps_deterministically_by_ticker_only():
    rows = [{"k_ticker": f"T{i}", "k_cat": "Sports" if i % 2 else "Politics"} for i in range(20)]
    a = cv.select_pairs(rows, {"Sports": 3}, "s")
    b = cv.select_pairs(list(reversed(rows)), {"Sports": 3}, "s")
    assert a == b and sum(r["k_cat"] == "Sports" for r in a) == 3
    assert sum(r["k_cat"] == "Politics" for r in a) == 10


def test_align_pm_lag_zero_uses_point_at_its_own_stamp():
    ps = [(600, 0.5)]
    kc = np.array([[60.0, 0.4, 0.44, 0.4, 0.0]])
    g0 = cv.align_pair(ps, kc, 0, 1200, pm_lag_s=0.0)
    g6 = cv.align_pair(ps, kc, 0, 1200)
    assert g0["p"][1] == 0.5 and np.isnan(g6["p"][1]) and g6["p"][2] == 0.5
