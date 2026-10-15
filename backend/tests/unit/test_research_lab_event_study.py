"""Event-study plumbing tests: fake transport only, no network."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from astrolabe.research_lab import event_study as es
from astrolabe.research_lab import history_backfill as hb

KEY = b"k" * 32
H = 3600


def _lim(transport):
    return hb.Limiter(transport, rps=1e9, sleep=lambda s: None, live_check=None)


def _trades(rows):
    df = pd.DataFrame(rows, columns=["ts", "side", "size", "price", "outcome_index",
                                     "wallet_hash"])
    df["trade_key"] = [f"k{i}" for i in range(len(df))]
    return df


def _flat_prices(t0, t1, p=0.1, step=600):
    ts = np.arange(t0, t1, step, dtype=float)
    return ts, np.full(len(ts), p)


def test_trailing_z_uses_only_prior_values():
    x = np.array([1.0, 1.0, 1.0, 1.0, 10.0, 1.0])
    z = es.trailing_z(x, n_prior=4, min_prior=3)
    assert np.isnan(z[:3]).all()
    assert z[3] == 0.0
    assert z[4] > 50  # sd floored at 0.1 * mean
    z2 = es.trailing_z(np.r_[x[:4], 10.0, 1e6], n_prior=4, min_prior=3)
    assert z2[4] == z[4]  # a later value never changes an earlier z


def test_prepare_trades_sign_and_wallet_age():
    tr = _trades([[100, "BUY", 10, 0.2, 0, "a"], [200, "SELL", 5, 0.7, 1, "b"],
                  [300, "BUY", 4, 0.6, 1, "c"]])
    p = es.prepare_trades(tr, {"a": {"first_trade_ts": 100 - 2 * 86400}, "b": None})
    assert list(p["sgn"]) == [1, 1, -1]  # BUY yes, SELL no -> toward yes; BUY no -> toward no
    assert np.allclose(p["notional"], [2.0, 3.5, 2.4])
    assert p["wallet_age_days"].iloc[0] == 2.0
    assert np.isnan(p["wallet_age_days"].iloc[1:]).all()


def test_bin_features_causal_and_flags():
    base = 10 * 86400
    rows = [[base - 3 * 86400 + k * H, "BUY", 10, 0.1, 0, f"w{k % 3}"] for k in range(48)]
    rows += [[base + 10, "BUY", 1000, 0.1, 0, "new"], [base + H, "BUY", 1, 0.1, 0, "late"]]
    ft = {"new": {"first_trade_ts": base}, **{f"w{k}": {"first_trade_ts": 0} for k in range(3)}}
    tr = es.prepare_trades(_trades(rows), ft)
    pts, pv = _flat_prices(base - 4 * 86400, base + 2 * 86400)
    df = es.bin_features(tr, pts, pv, base - 86400, base + 2 * H, bin_s=H)
    r = df.set_index("bin_start").loc[base]
    assert r["t"] == base + H
    assert r["max_trade"] == 100.0  # the trade at exactly t = base + H is excluded
    assert r["nw_share_7d"] == 1.0 and r["nw_cov"] == 1.0
    assert r["flow_against_price"] == 1.0 and r["flagged_side_price_open"] == 0.1
    assert r["traded_before_t"] == 1.0
    # trailing 7d window starts before the coverage start -> NaN trailing features
    df2 = es.bin_features(tr, pts, pv, base - 86400, base + 2 * H, bin_s=H,
                          covered_from=base - 3 * 86400)
    assert np.isnan(df2.set_index("bin_start").loc[base, "max_trade_over_trail7d"])
    # later trades never change earlier rows
    tr_more = es.prepare_trades(_trades(rows + [[base + 5 * H, "SELL", 9e5, 0.1, 0, "x"]]), ft)
    df3 = es.bin_features(tr_more, pts, pv, base - 86400, base + 2 * H, bin_s=H)
    pd.testing.assert_frame_equal(df, df3)


def test_forward_excursion_and_crossing():
    ts = np.arange(0, 20 * H, 600, dtype=float)
    p = np.where(ts < 5 * H, 0.1, 0.35)
    mv, lead = es.forward_excursion(ts, p, np.array([3600.0, 3600.0]), np.array([0.1, 0.1]),
                                    np.array([1.0, -1.0]), 6 * H)
    assert np.isclose(mv[0], 0.25) and lead[0] == 4 * H
    assert np.isclose(mv[1], 0.0)
    mv2, _ = es.forward_excursion(ts, p, np.array([19 * H]), np.array([0.35]), np.array([1.0]),
                                  72 * H)
    assert np.isnan(mv2[0])  # no extrapolation past the series
    assert es.first_crossing(ts, p, 3600.0, 0.1, 1.0, 0.10, 6 * H) == 4 * H


def test_large_move_episodes():
    ts = np.arange(0, 10 * 86400, H, dtype=float)
    p = np.full(len(ts), 0.2)
    p[ts >= 2 * 86400] = 0.5
    p[ts >= 6 * 86400] = 0.25
    eps = es.large_move_episodes(ts, p, 0.20, 3 * 86400)
    assert [e["direction"] for e in eps] == [1, -1]
    assert eps[0]["end_ts"] == 2 * 86400


def test_cluster_bootstrap_mean():
    v = np.array([1, 1, 0, 0, np.nan])
    c = np.array(["a", "a", "b", "b", "c"])
    r = es.cluster_bootstrap_mean(v, c, n_boot=200, seed=1)
    assert r["mean"] == 0.5 and r["clusters"] == 2 and r["n"] == 4
    assert 0 <= r["lo"] <= r["hi"] <= 1


def test_apply_detector_requires_traded_and_no_nan():
    spec = es.DetectorSpec(min_max_trade_usdc=100, min_max_trade_over_trail7d=0.1,
                           min_new_wallet_share_7d=0.5, min_z_volume=3,
                           max_flagged_side_price=0.35, min_abs_flow_imb=0.5)
    good = dict(traded_before_t=1.0, max_trade=500.0, max_trade_over_trail7d=0.5,
                nw_share_7d=0.9, z_volume=4.0, flagged_side_price_open=0.1, flow_imb=0.9)
    df = pd.DataFrame([good, {**good, "traded_before_t": 0.0}, {**good, "nw_share_7d": np.nan},
                       {**good, "flagged_side_price_open": 0.6}])
    assert list(es.apply_detector(df, spec)) == [True, False, False, False]


class FakeTrades:
    """Data API /trades fake that honours start/end and the offset cap."""

    def __init__(self, n, honour=True):
        self.data = [{"timestamp": 1000 + i, "side": "BUY", "size": 1, "price": 0.5,
                      "outcomeIndex": 0, "proxyWallet": f"0xW{i % 7}", "asset": "a",
                      "transactionHash": f"h{i}"} for i in range(n)]
        self.honour, self.calls = honour, []

    def __call__(self, url, params):
        self.calls.append(dict(params))
        if params["offset"] > hb.TRADE_OFFSET_CAP:
            return 400, b'{"error":"max offset"}', {}
        d = self.data
        if self.honour and "start" in params:
            d = [t for t in d if params["start"] <= t["timestamp"] <= params["end"]]
        d = sorted(d, key=lambda t: -t["timestamp"])
        o, lim = params["offset"], params["limit"]
        return 200, json.dumps(d[o:o + lim]).encode(), {}


def test_fetch_trades_full_splits_windows_past_cap():
    fake = FakeTrades(25000)
    rows, st, addrs = es.fetch_trades_full(_lim(fake), "0xc", KEY, 0, 10**6, ("start", "end"))
    assert st["n"] == 25000 and not st["incomplete_windows"]
    assert addrs == {}
    assert all(not r[5].startswith("0x") for r in rows)  # hashed only
    rows2, st2, _ = es.fetch_trades_full(_lim(FakeTrades(25000)), "0xc", KEY, 0, 10**6, None)
    assert st2["truncated"] and st2["n"] == 11000


def test_first_trade_lookups_cache_has_no_addresses(tmp_path):
    def fake(url, params):
        assert url == es.DATA_ACTIVITY and params["sortDirection"] == "ASC"
        return 200, json.dumps([{"timestamp": 500}]).encode(), {}

    p = tmp_path / "ft.jsonl"
    addr = "0xABCDEF0000000000000000000000000000000001"
    h = hb.wallet_hash(KEY, addr)
    r = es.first_trade_lookups(_lim(fake), {h: (addr, 900)}, p)
    assert r["lookups_ok"] == 1
    text = p.read_text()
    assert addr.lower() not in text.lower() and h in text
    r2 = es.first_trade_lookups(_lim(fake), {h: (addr, 1200)}, p)
    assert r2["cached"] == 1 and r2["lookups_ok"] == 0


def test_price_onset_and_describe_case():
    ts = np.arange(0, 5 * 86400, 600, dtype=float)
    p = np.where(ts < 4 * 86400, 0.07, 0.5)
    on = es.price_onset(ts, p, 0.10, 86400)
    assert on == 4 * 86400
    df = pd.DataFrame({"t": np.arange(H, 5 * 86400, H)})
    df["z_volume"] = 0.0
    df.loc[df["t"] == on - 2 * H, "z_volume"] = 4.0
    df.loc[df["t"] == 10 * H, "z_volume"] = 6.0  # earlier in the market's own history
    r = es.describe_case(df, on, pre_h=24)
    m = r["metrics"]["z_volume"]
    assert m["z>=3"]["lead_h"] == 2.0 and m["z>=3"]["earlier_bins_exceeding"] == 1
    assert m["z>=5"]["first_t"] is None
