import json

import numpy as np
import pandas as pd

from astrolabe.research_lab import case_catalogue as cc

KEY = b"k" * 64
NEWS = 1_700_000_000 - 1_700_000_000 % 3600 + 20 * 86400


def _trades(rows):
    return pd.DataFrame(rows, columns=["ts", "side", "size", "price", "outcome_index",
                                       "wallet_hash", "trade_key", "large_pass_only"])


def _quiet_market(w0, news, burst_h=None, burst_wallet="new", burst_usdc=5000.0):
    rows, k = [], 0
    for h in range(w0, news + 86400, 3600):
        rows.append([h + 60, "BUY", 20.0, 0.1, 0, f"old{h % 7}", f"t{k}", 0])
        k += 1
        if burst_h is not None and h == burst_h:
            rows.append([h + 120, "BUY", burst_usdc / 0.1, 0.1, 0, burst_wallet, f"t{k}", 0])
            k += 1
    return _trades(rows)


def _prices(w0, w1, jump_at):
    ts = np.arange(w0, w1, 600)
    return pd.DataFrame({"ts": ts, "p0": np.where(ts >= jump_at, 0.95, 0.1)})


def test_robust_z_uses_only_trailing_hours():
    x = np.array([1.0] * 60 + [100.0] + [1.0] * 5)
    z = cc.robust_z(x, floor=1.0)
    assert np.isnan(z[:48]).all()
    assert z[60] > 50
    # the spike enters the baseline later but cannot affect earlier hours
    z2 = cc.robust_z(np.array([1.0] * 60 + [1.0] + [1.0] * 5), floor=1.0)
    np.testing.assert_allclose(z[:60], z2[:60])


def test_onset_found_before_news_with_lead_and_prices():
    w0, w1 = NEWS - 14 * 86400, NEWS + 86400
    burst = NEWS - 5 * 3600
    tr = _quiet_market(w0, NEWS, burst_h=burst)
    ft = {f"old{i}": w0 - 400 * 86400 for i in range(7)}
    ft["new"] = burst - 3600  # first ever trade one hour earlier: a new wallet
    df = cc.hourly_features(tr, _prices(w0, w1, NEWS), ft, w0, w1, w0, w0)
    res = cc.unusual_onset(df, NEWS)
    assert res["onset_ts"] == burst
    assert res["lead_h"] == 5.0
    assert res["p_at_onset"] == 0.1 and res["p_post_news_6h"] == 0.95
    assert res["background_flag_rate"] == 0.0
    row = df.loc[df["hour"] == burst].iloc[0]
    assert row["new_share"] > 0.9 and row["top_share"] > 0.9


def test_no_onset_in_quiet_market_and_uncovered_hours_are_missing():
    w0, w1 = NEWS - 14 * 86400, NEWS + 86400
    tr = _quiet_market(w0, NEWS)
    cov = NEWS - 2 * 86400
    df = cc.hourly_features(tr, _prices(w0, w1, NEWS), {}, w0, w1, cov, w0)
    assert df.loc[df["hour"] < cov, "notional"].isna().all()
    assert (df.loc[df["hour"] >= cov, "notional"] > 0).all()
    res = cc.unusual_onset(df, NEWS)
    assert res["onset_ts"] is None
    assert res["pre_hours_scored"] == 0  # only 48h of coverage: no 48h baseline before news-72h
    assert res["background_hours_scored"] == 0


def test_flow_sign_and_disagreement():
    w0 = NEWS - 3 * 3600
    tr = _trades([[w0 + 10, "SELL", 100.0, 0.5, 1, "a", "x1", 0],   # towards outcome 0
                  [w0 + 20, "BUY", 100.0, 0.5, 1, "b", "x2", 0]])   # towards outcome 1
    df = cc.hourly_features(tr, _prices(w0 - 3600, NEWS, NEWS), {}, w0, NEWS, w0, w0)
    assert df.loc[0, "yes_flow"] == 0.0 and df.loc[0, "notional"] == 100.0


def test_first_move_ts():
    p = _prices(NEWS - 3 * 86400, NEWS + 86400, NEWS - 1800)
    assert cc.first_move_ts(p, NEWS) == NEWS - 1800


def test_coverage_from():
    assert cc.coverage_from(100, {"truncated": False, "incomplete_windows": []}) == 100
    assert cc.coverage_from(100, {"truncated": False, "incomplete_windows": [[150, 160]]}) == 161
    assert cc.coverage_from(100, {"truncated": True, "oldest_ts": 500}) == 500


def test_rank_wallets_pre_news_only_and_capped():
    tr = [[10, "BUY", 100.0, 0.5, 0, "a", "k1"], [20, "BUY", 10.0, 0.5, 0, "b", "k2"],
          [30, "BUY", 1000.0, 0.5, 0, "c", "k3"], [5, "BUY", 1.0, 0.5, 0, "a", "k0"]]
    addr = {"a": "0xA", "b": "0xB", "c": "0xC"}
    out = cc.rank_wallets(sorted(tr), addr, news_ts=25, cap=1)
    assert out == {"a": ("0xA", 5)}  # c traded only after the news


def test_registry_roundtrip(tmp_path):
    c = cc.CaseSpec("c1", "awards", "polymarket", "e", "2025-10-10T09:00:00Z", "announcement",
                    0.1, "official_probe", "r", ["slug-a"], "Yes",
                    [cc.Source("https://x", "Outlet", "news")])
    p = tmp_path / "reg.json"
    p.write_text(cc.registry_json([c]))
    (back,) = cc.load_registry(p)
    assert back == c and back.news_ts == 1760086800
    assert json.loads(p.read_text())["evidence_role"] == "exploratory_historical"


def test_binom_sf():
    assert cc.binom_sf(0, 10, 0.1) == 1.0
    assert abs(cc.binom_sf(1, 10, 0.1) - (1 - 0.9**10)) < 1e-12
    assert cc.binom_sf(3, 10, 0.0) == 0.0


def _pts(t0, n, jump_at=None, lo=0.3, hi=0.6):
    return [(t0 + i * 600, hi if (jump_at is not None and t0 + i * 600 >= jump_at) else lo)
            for i in range(n)]


def test_first_large_move_and_classification():
    t0 = NEWS - 15 * 86400
    close = t0 + 15 * 86400
    jump = t0 + 10 * 86400
    pts = _pts(t0, 15 * 144, jump_at=jump)
    assert cc.first_large_move(pts) == jump
    band = cc.price_band(0.3)
    assert cc.classify_candidate(pts, close, band) == ("quiet_move", jump, "ok")
    flat = _pts(t0, 15 * 144)
    assert cc.classify_candidate(flat, close, band) == ("quiet_nomove", close - 86400, "ok")
    assert cc.classify_candidate(flat, close, cc.price_band(0.02))[2] == "price band mismatch"


def test_small_move_is_not_large():
    t0 = NEWS - 3 * 86400
    pts = _pts(t0, 3 * 144, jump_at=t0 + 2 * 86400, lo=0.30, hi=0.39)
    assert cc.first_large_move(pts) is None


def test_panel_first_seen_takes_earliest():
    tr = pd.DataFrame({"wallet_hash": ["a" * 64, "b" * 64], "ts": [100.0, 200.0]})
    fs = cc.panel_first_seen([tr], {"b" * 64: 50})
    np.testing.assert_allclose(fs.lookup(np.array(["a" * 64, "b" * 64, "c" * 64])),
                               [100.0, 50.0, np.nan])


def test_market_rows_smoke():
    w0 = NEWS - 5 * 86400
    prices = pd.DataFrame({"ts": np.arange(w0, NEWS + 86400, 600)})
    prices["p0"] = np.where(prices["ts"] >= NEWS, 0.9, 0.2)
    tr = _trades([[w0 + 3600 * i, "BUY", 10.0, 0.2, 0, f"{i % 3:064x}", f"k{i}", 0]
                  for i in range(100)]).drop(columns="large_pass_only")
    fr = {k: "" for k in cc.hb.FRAME_COLUMNS}
    fr.update({"market_id": "m1", "condition_id": "c", "token0": "1", "token1": "2",
               "event_id": "e1", "fee_category": "x", "status": "closed", "liquidity": 0,
               "volume": 5e4, "created_at": "2020-01-01T00:00:00Z", "start_epoch": 0,
               "end_epoch": NEWS + 86400, "close_epoch": NEWS + 86400, "closed": 1})
    rows = cc.market_rows(fr, prices, tr, cc.panel_first_seen([tr], {}), "run")
    assert set(rows["horizon_target_h"].unique()) == {2.0, 6.0, 24.0}
    from astrolabe.research_lab import detector_eval as de
    rows["news_ts"] = float(NEWS)
    rows["control_group"] = "case"
    p = de.normalise_panel(rows, "history")
    assert {"fwd_move_24h", "imb_s", "news_ts", "control_group"} <= set(p.columns)
    assert p["traded_before_t"].eq(1.0).any()
