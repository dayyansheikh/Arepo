# ruff: noqa: E501
from __future__ import annotations

import gzip
import itertools
import json
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import wallet_skill as ws
from astrolabe.research_lab import wallet_skill_dev as wd

DAY = 86400.0


def _tr(rows):
    """rows: (market_id, ts, wallet, side, outcome_index, price, size)."""
    df = pd.DataFrame(rows, columns=["market_id", "ts", "wallet_hash", "side", "outcome_index", "price", "size"])
    return ws.normalise_trades(df)


def _res(rows):
    """rows: (market_id, pay0, known_ts)."""
    return pd.DataFrame([(m, p, 1.0 - p, k, k - ws.RES_LAG_S) for m, p, k in rows],
                        columns=["market_id", "pay0", "pay1", "known_ts", "close_ts"])


def _synthetic(seed=0, n_markets=60, n_wallets=25, n_trades=2500, days=40):
    rng = np.random.default_rng(seed)
    close = rng.uniform(5, days, n_markets) * DAY
    rows = []
    for _ in range(n_trades):
        m = int(rng.integers(n_markets))
        rows.append((m, float(rng.uniform(0, close[m])), f"w{rng.integers(n_wallets)}", rng.choice(["BUY", "SELL"]),
                     int(rng.integers(2)), float(rng.uniform(0.02, 0.98)), float(rng.uniform(1, 500))))
    pay = rng.choice([0.0, 1.0, 0.5], n_markets, p=[0.45, 0.45, 0.1])
    known = close + rng.uniform(0, 3, n_markets) * DAY
    res = pd.DataFrame({"market_id": np.arange(n_markets), "pay0": pay, "pay1": 1 - pay, "known_ts": known, "close_ts": close})
    return _tr(rows), res


# ---------------------------------------------------------------------------------------------- accounting


def test_position_accounting_by_hand():
    t = _tr([(1, 10, "a", "BUY", 0, 0.3, 10),   # wins: +7, cost 3
             (1, 11, "a", "SELL", 1, 0.6, 5),   # outcome 1 loses: +3, cost 2
             (2, 12, "a", "BUY", 1, 0.8, 10),   # loses: -8, cost 8
             (3, 13, "a", "BUY", 0, 0.5, 4)])   # 50/50 split: 0, cost 2
    res = _res([(1, 1.0, 100), (2, 1.0, 100), (3, 0.5, 100)])
    p = ws.build_profiles_batch(t, res, 101).loc["a"]
    assert p["n_pos"] == 3 and p["n_trades"] == 4
    assert p["pnl"] == pytest.approx(7 + 3 - 8 + 0)
    assert p["cost"] == pytest.approx(3 + 2 + 8 + 2)
    assert p["q"] == pytest.approx(10 ** 2 + 8 ** 2 + 0)
    assert p["skill_z"] == pytest.approx(2 / math.sqrt(164))
    assert p["hit_rate"] == pytest.approx(1 / 3)
    # market 1: shares 15, cost 5 -> implied 1/3 ; market 2: 0.8 ; market 3: 0.5
    assert p["implied_rate"] == pytest.approx((5 / 15 + 0.8 + 0.5) / 3)
    assert p["calib_excess"] == pytest.approx((10 / 15 - 8 / 10 + 0) / 3)
    assert p["skill_score"] == pytest.approx(p["skill_z"] * math.sqrt(3 / 13))
    assert not p["eligible"]


def test_payouts_from_prices():
    assert ws.payouts_from_prices('["1", "0"]') == (1.0, 0.0)
    assert ws.payouts_from_prices(["0", "1"]) == (0.0, 1.0)
    assert ws.payouts_from_prices('["0.5", "0.5"]') == (0.5, 0.5)
    assert ws.payouts_from_prices('["0.0005", "0.9995"]') is None
    assert ws.payouts_from_prices("nan") is None


def test_normalise_drops_invalid_rows():
    t = _tr([(1, 1, "a", "BUY", 0, 0.5, 1), (1, 1, "a", "HOLD", 0, 0.5, 1), (1, 1, "a", "BUY", 2, 0.5, 1),
             (1, 1, "a", "BUY", 0, 1.0, 1), (1, 1, None, "BUY", 0, 0.5, 1), (1, 1, "a", "SELL", 1, 0.5, 0)])
    assert len(t) == 1


# ---------------------------------------------------------------------------------------------- sign randomisation


def test_sign_flip_exact_matches_brute_force():
    x = np.array([3.0, -1.0, 2.0, 0.5, -0.25, 4.0])
    s = x.sum()
    brute = np.mean([np.dot(e, x) >= s - 1e-12 for e in itertools.product((-1, 1), repeat=len(x))])
    assert ws.sign_flip_pvalue(x) == pytest.approx(brute)


def test_sign_flip_monte_carlo_close_to_exact_and_variance_is_q():
    rng = np.random.default_rng(1)
    x = rng.normal(0.3, 1.0, 14)
    exact = ws.sign_flip_pvalue(x)
    mc = ws.sign_flip_pvalue(x, n_perm=40000, seed=3, exact_max=0)
    assert mc == pytest.approx(exact, abs=0.01)
    e = rng.integers(0, 2, size=(200000, len(x))) * 2 - 1
    sstar = e @ x
    assert sstar.mean() == pytest.approx(0.0, abs=0.02 * math.sqrt((x ** 2).sum()))
    assert sstar.var() == pytest.approx((x ** 2).sum(), rel=0.02)


def test_sign_flip_null_is_calibrated():
    """Under a true null (symmetric P&L), P(p < 0.05) is about 0.05 (or below: the test is conservative when discrete)."""
    rng = np.random.default_rng(7)
    ps = [ws.sign_flip_pvalue(rng.normal(0, 1, 30) * rng.uniform(0.1, 5, 30), n_perm=999, seed=i) for i in range(300)]
    assert np.mean(np.array(ps) < 0.05) < 0.09


def test_skilled_set_top_decile_and_positive_z():
    prof = pd.DataFrame({"n_pos": [10] * 20 + [2], "skill_score": list(np.linspace(-2, 3, 20)) + [9.0],
                         "skill_z": list(np.linspace(-2, 3, 20)) + [9.0]}, index=[f"w{i}" for i in range(21)])
    prof["eligible"] = prof["n_pos"] >= ws.MIN_POS
    sk, thr = ws.skilled_set(prof, 0.10)
    assert "w20" not in sk  # ineligible (2 positions) even with the top score
    assert sk == {"w18", "w19"}
    prof["skill_z"] = -1.0
    assert ws.skilled_set(prof)[0] == set()


# ---------------------------------------------------------------------------------------------- no look-ahead


def test_profiles_at_t_ignore_later_outcomes_and_trades():
    t, res = _synthetic(seed=2)
    T = 20 * DAY
    p0 = ws.build_profiles_batch(t, res, T)
    # change every outcome known at or after T and add trades after T: profiles at T must not move
    res2 = res.copy()
    late = res2["known_ts"] >= T
    res2.loc[late, "pay0"] = 1 - res2.loc[late, "pay0"]
    res2.loc[late, "pay1"] = 1 - res2["pay0"]
    extra = _tr([(int(m), T + 5, "w0", "BUY", 0, 0.1, 1e6) for m in range(10)])
    p1 = ws.build_profiles_batch(pd.concat([t, extra], ignore_index=True), res2, T)
    pd.testing.assert_frame_equal(p0.sort_index(), p1.sort_index())
    # the builder refuses to advance past ingested trades (they could not have been received by T) ...
    b = ws.ProfileBuilder()
    b.add_trades(pd.concat([t, extra], ignore_index=True))
    b.add_resolutions(res2)
    with pytest.raises(ValueError):
        b.advance_to(T)
    # ... and, fed causally (trades before T, then later outcomes flipped), agrees with the batch reference
    b = ws.ProfileBuilder()
    b.add_trades(t[t["ts"] < T])
    b.add_resolutions(res2)
    b.advance_to(T)
    pd.testing.assert_frame_equal(b.snapshot().sort_index()[p0.columns], p0.sort_index(), check_dtype=False)
    # the history-study mode (all trades precede their market's close) is also unaffected by later outcomes
    open_m = set(res2.loc[res2["known_ts"] >= T, "market_id"])
    b = ws.ProfileBuilder()
    b.add_trades(pd.concat([t, extra[extra["market_id"].isin(open_m)]], ignore_index=True))
    b.add_resolutions(res2)
    b.advance_to(T, allow_future_trades=True)
    pd.testing.assert_frame_equal(b.snapshot().sort_index()[p0.columns], p0.sort_index(), check_dtype=False)


def test_outcome_known_exactly_at_t_is_excluded():
    t = _tr([(1, 10, "a", "BUY", 0, 0.5, 1)])
    res = _res([(1, 1.0, 100.0)])
    assert len(ws.build_profiles_batch(t, res, 100.0)) == 0
    assert len(ws.build_profiles_batch(t, res, 100.0001)) == 1
    b = ws.ProfileBuilder()
    b.add_trades(t)
    b.add_resolutions(res)
    assert b.advance_to(100.0) == 0
    assert b.advance_to(100.5) == 1
    with pytest.raises(ValueError):
        b.advance_to(50.0)


def test_market_features_use_only_trades_before_cut():
    t = _tr([(1, 100, "s", "BUY", 0, 0.5, 10), (1, 199, "s", "BUY", 0, 0.5, 10), (1, 200, "s", "SELL", 0, 0.5, 1000)])
    o = pd.DataFrame({"market_id": [1], "t_cut": [200.0]})
    f = ws.market_features(t, o, {"s"}, pd.Series({"s": 2.0}))
    assert f.loc[0, "ws_net1h"] == pytest.approx(1.0)  # the print AT the cut is excluded
    t2 = pd.concat([t, _tr([(1, 250, "s", "SELL", 0, 0.5, 10 ** 6)])], ignore_index=True)
    f2 = ws.market_features(t2, o, {"s"}, pd.Series({"s": 2.0}))
    pd.testing.assert_frame_equal(f, f2)


# ---------------------------------------------------------------------------------------------- incremental = batch


@pytest.mark.parametrize("seed", [0, 1, 5])
def test_incremental_daily_equals_batch(seed):
    t, res = _synthetic(seed=seed)
    b = ws.ProfileBuilder()
    for d in range(1, 46):
        D = d * DAY
        b.add_trades(t[(t["ts"] >= D - DAY) & (t["ts"] < D)])  # the day's trades arrive at its end
        b.add_resolutions(res[(res["known_ts"] >= D - DAY) & (res["known_ts"] < D)])  # outcomes arrive when known
        b.advance_to(D)
        if d % 9 == 0 or d == 45:
            inc = b.snapshot().sort_index()
            bat = ws.build_profiles_batch(t, res, D).sort_index()
            assert list(inc.index) == list(bat.index)
            for c in ("n_pos", "n_trades", "pnl", "q", "cost", "hits", "implied", "edge", "skill_z", "skill_score", "ppd", "calib_shr"):
                np.testing.assert_allclose(inc[c].to_numpy(float), bat[c].to_numpy(float), rtol=1e-9, atol=1e-9)


def test_builder_save_load_roundtrip(tmp_path):
    t, res = _synthetic(seed=4)
    b = ws.ProfileBuilder()
    b.add_trades(t[t["ts"] < 15 * DAY])
    b.add_resolutions(res)
    b.advance_to(15 * DAY)
    b.save(tmp_path / "st")
    c = ws.ProfileBuilder.load(tmp_path / "st")
    for x in (b, c):
        x.add_trades(t[t["ts"] >= 15 * DAY])
        x.advance_to(40 * DAY)
    pd.testing.assert_frame_equal(b.snapshot().sort_index(), c.snapshot().sort_index(), check_dtype=False)


def test_deduper_counts_overlapping_samples_once():
    a = _tr([(1, 10, "x", "BUY", 0, 0.5, 1), (1, 20, "y", "BUY", 0, 0.5, 2), (1, 20, "z", "SELL", 1, 0.4, 3)])
    b = _tr([(1, 20, "y", "BUY", 0, 0.5, 2), (1, 20, "z", "SELL", 1, 0.4, 3), (1, 20, "q", "BUY", 1, 0.4, 3),
             (1, 30, "x", "BUY", 0, 0.5, 1), (2, 5, "x", "BUY", 0, 0.5, 1)])
    dd = ws.TradeDeduper()
    assert len(dd.new_only(a)) == 3
    nb = dd.new_only(b)
    assert len(nb) == 3 and set(nb["wallet"]) == {"q", "x"}
    assert len(dd.new_only(b)) == 0


# ---------------------------------------------------------------------------------------------- market features


def test_market_features_signs_windows_and_counts():
    T = 100000.0
    t = _tr([(1, T - 30 * 60, "s1", "BUY", 0, 0.30, 100),     # skilled, +, long shot, notional 30
             (1, T - 2 * 3600, "s2", "SELL", 0, 0.60, 50),    # skilled, -, notional 30 (6h, 24h)
             (1, T - 10 * 3600, "s1", "BUY", 1, 0.20, 50),    # skilled, toward outcome 1 = -, long shot, notional 10
             (1, T - 20 * 60, "u", "BUY", 0, 0.50, 40),       # unskilled +, notional 20
             (1, T - 30 * 3600, "s1", "BUY", 0, 0.5, 1000),   # outside 24h
             (2, T - 60, "u", "BUY", 0, 0.5, 2)])
    o = pd.DataFrame({"market_id": [1, 2, 3], "t_cut": [T, T, T], "covered_from": [-np.inf, -np.inf, T - 7200]})
    sc = pd.Series({"s1": 2.0, "s2": 5.0, "u": -1.0})
    f = ws.market_features(t, o, {"s1", "s2"}, sc, eligible={"s1", "s2", "u"})
    r = f.loc[0]
    assert r["ws_net1h"] == pytest.approx(30 / 50)
    assert r["gen_net1h"] == pytest.approx(50 / 50)
    assert r["ws_net6h"] == pytest.approx((30 - 30) / 80)
    assert r["ws_net24h"] == pytest.approx((30 - 30 - 10) / 90)
    assert r["gen_net24h"] == pytest.approx((30 - 30 - 10 + 20) / 90)
    assert r["ws_share24"] == pytest.approx(70 / 90)
    assert r["ws_ls24"] == pytest.approx((30 - 10) / 90)
    assert r["ws_nskill24"] == pytest.approx(math.log1p(1))  # s1 buys; s2 only sells
    assert r["ws_zflow24"] == pytest.approx((2 * 30 - 3 * 30 - 2 * 10 - 1 * 20) / 90)  # s2 clipped to 3
    assert r["ws_cov24"] == pytest.approx(1.0)
    assert f.loc[1, "ws_net24h"] == 0.0 and f.loc[1, "gen_net24h"] == 1.0
    # market 3: no trades; 1 h window covered (0), 6 h / 24 h windows start before covered_from (NaN)
    assert f.loc[2, "ws_net1h"] == 0.0 and np.isnan(f.loc[2, "ws_net6h"]) and np.isnan(f.loc[2, "ws_net24h"])


def test_family_features_reads_a_trade_sample(tmp_path):
    T = 1792000000.0
    d = tmp_path / "sample"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"limit": 3}))
    (d / "wallets_manifest.json").write_text(json.dumps({"sidecar_status": "complete"}))
    origin = pd.Timestamp(T, unit="s", tz="UTC").isoformat()
    feats = pd.DataFrame({"market_id": [1, 2], "status": ["ok", "ok"], "origin_utc": [origin, origin], "n_returned": [2, 3]})
    with gzip.open(d / "features.csv.gz", "wt") as fh:
        feats.to_csv(fh, index=False)
    w = pd.DataFrame({"market_id": [1, 1, 2, 2, 2], "ts": [T - 100, T + 5, T - 100, T - 200, T - 4000],
                      "side": ["BUY", "BUY", "SELL", "BUY", "BUY"], "outcome_index": [0, 0, 0, 0, 0],
                      "size": [10, 10, 10, 10, 10], "price": [0.5] * 5, "wallet_hash": ["s", "s", "s", "u", "u"],
                      "condition_id": ["c"] * 5, "asset": ["a"] * 5})
    with gzip.open(d / "wallets.csv.gz", "wt") as fh:
        w.to_csv(fh, index=False)
    snap = ws.snapshot_frame(ws.finish_profiles(pd.DataFrame({"n_pos": [9.0, 9.0], "n_trades": 9.0, "pnl": [5.0, -1.0], "q": [4.0, 4.0],
                                                              "cost": 9.0, "hits": 5.0, "implied": 4.0, "edge": 1.0}, index=pd.Index(["s", "u"], name="wallet"))),
                             as_of=T - 86400, top_frac=0.5)
    f = pd.DataFrame({"market_id": [1, 2, 3]})
    assert ws.family_features(d, f, snap).isna().all().all()  # warm-up: fewer than 200 eligible wallets
    out = ws.family_features(d, f, snap, min_eligible=2)
    assert list(out.columns) == ws.COLUMNS
    assert out.loc[0, "ws_net1h"] == pytest.approx(1.0)  # the trade after the origin is ignored
    assert out.loc[1, "ws_net1h"] == pytest.approx(-0.5)  # full page, but the 1 h window starts after the oldest sampled trade
    assert np.isnan(out.loc[1, "ws_net6h"])  # ... the 6 h window does not
    assert out.loc[2].isna().all()  # market without a sample row: missing, never 0
    assert ws.family_features(None, f, snap, min_eligible=2).isna().all().all()


# ---------------------------------------------------------------------------------------------- dev helpers


def test_cluster_boot_and_holm():
    rng = np.random.default_rng(0)
    v = rng.normal(1.0, 1.0, 400)
    r = wd.cluster_boot_mean(v, np.repeat(np.arange(100), 4), B=400)
    assert r["ci95"][0] < 1.0 < r["ci95"][1] and r["p_one_sided_gt0"] < 0.01 and r["clusters"] == 100
    h = wd.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert h == {"a": 0.03, "c": 0.06, "b": 0.06}


def test_persistence_detects_planted_skill_and_not_noise():
    rng = np.random.default_rng(11)
    rows = []
    for w in range(300):
        edge = 0.25 if w < 30 else 0.0
        for m in range(80):
            p = rng.uniform(0.2, 0.8)
            win = rng.random() < min(0.99, p + edge)
            x = (1.0 - p) if win else -p
            rows.append((f"w{w}", m + 1000 * w, x * 10, x * x * 100, 10 * p, float(win), p, x, (m % 2) * 2e9))
    rp = pd.DataFrame(rows, columns=["wallet", "market_id", "pnl", "q", "cost", "hits", "implied", "edge", "known_ts"])
    rp["n_pos"] = 1.0
    rp["n_trades"] = 1.0
    rp["event_id"] = rp["market_id"]
    out = wd.persistence(rp, split=1e9, end=3e9, B=300, mc_pvalues=False)
    assert out["status"] == "ok" and out["top_decile"]["perm_p_one_sided"] < 0.01
    rp2 = rp.copy()
    rp2["pnl"] = np.where(rng.random(len(rp2)) < 0.5, 1, -1) * rp2["pnl"].abs()  # destroy skill
    out2 = wd.persistence(rp2, split=1e9, end=3e9, B=300, mc_pvalues=False)
    assert out2["top_decile"]["perm_p_one_sided"] > 0.01
