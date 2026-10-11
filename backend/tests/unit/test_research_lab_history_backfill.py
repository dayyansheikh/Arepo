"""History backfill tests: fake transport only, no network."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import history_backfill as hb

NOW = 1_790_000_000.0
KEY = b"k" * 32


def _market(i: int, closed: bool = True, vol: float = 5000.0, fee: str | None = "sports_fees"):
    end = NOW - 20 * 86400
    return {
        "id": str(i), "conditionId": f"0xc{i}", "clobTokenIds": json.dumps([f"t{i}a", f"t{i}b"]),
        "closed": closed, "feeType": fee, "volumeNum": vol, "liquidityNum": 100.0,
        "startDate": "2026-08-01T00:00:00Z", "createdAt": "2026-08-01T00:00:00Z",
        "endDate": pd.Timestamp(end, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closedTime": "2026-09-20 00:00:00+00", "events": [{"id": f"e{i % 3}"}],
    }


def _wallet(i):
    return f"0xABCDEF{i:034d}"


class Fake:
    def __init__(self, markets):
        self.markets, self.calls = markets, []

    def __call__(self, url, params):
        self.calls.append((url, dict(params)))
        if url == hb.GAMMA_MARKETS:
            off = params.get("offset", 0)
            batch = self.markets if off == 0 else []
            if params.get("closed") == "false":
                batch = []
            return 200, json.dumps(batch).encode(), {}
        if url == hb.CLOB_PRICES:
            a, b = params["startTs"], params["endTs"]
            pts = [{"t": t, "p": 0.4 + 0.1 * np.sin(t / 40000)} for t in range(int(a), int(b), 600)]
            return 200, json.dumps({"history": pts}).encode(), {}
        if url == hb.DATA_TRADES:
            off = params["offset"]
            n = 1500
            rows = [{"proxyWallet": _wallet(k % 7), "side": "BUY" if k % 2 else "SELL",
                     "size": 10.0, "price": 0.4, "timestamp": int(NOW - 21 * 86400 - k * 600),
                     "outcomeIndex": 0, "transactionHash": f"0x{k}", "asset": "a",
                     "name": "SECRETNAME"} for k in range(n)]
            return 200, json.dumps(rows[off: off + params["limit"]]).encode(), {}
        return 404, b"", {}


def _run(tmp_path, fake=None, **kw):
    fake = fake or Fake([_market(i) for i in range(1, 6)])
    m = hb.run(tmp_path, "r1", fake, n_markets=3, key=KEY, now=NOW, sleep=lambda s: None,
               lookback_days=2, live_check=None, **kw)
    return fake, m


def test_wallet_hash_matches_live_sidecar():
    from astrolabe.research_lab.wallet_sidecar import hash_wallet

    assert hb.wallet_hash(KEY, "0xAB") == hash_wallet(KEY, "0xab") == hb.wallet_hash(KEY, "0xab")
    assert hb.wallet_hash(KEY, "0xab") != hb.wallet_hash(b"z" * 32, "0xab")
    assert len(hb.wallet_hash(KEY, "0xab")) == 64


def test_run_stores_no_raw_wallet_or_name(tmp_path):
    _, m = _run(tmp_path)
    assert m["provenance"] == "EXPLORATORY_HISTORICAL"
    assert m["evidence_role"] == "exploratory_historical"
    blob = b"".join(p.read_bytes() for p in tmp_path.rglob("trades/*.csv.gz"))
    import gzip

    txt = b"".join(gzip.decompress(p.read_bytes()) for p in tmp_path.rglob("trades/*.csv.gz"))
    assert blob and b"ABCDEF" not in txt and b"abcdef" not in txt and b"SECRETNAME" not in txt
    assert m["counts"]["markets_done"] == 3
    assert m["counts"]["trades_truncated_markets"] == 0


def test_rate_limit_and_backoff():
    sleeps = []
    seq = iter([429, 429, 200])

    def tr(url, params):
        s = next(seq)
        return s, b"[]" if s == 200 else b"", {}

    t = [0.0]
    lim = hb.Limiter(tr, rps=5, sleep=lambda s: (sleeps.append(s), t.__setitem__(0, t[0] + s)),
                     clock=lambda: t[0])
    assert lim.get("u", {}) == (200, [])
    assert lim.throttled == 2 and sleeps[0] == 1.0 and 2.0 in sleeps  # exponential backoff
    for _ in range(3):
        lim.transport = lambda u, p: (200, b"[]", {})
        lim.get("u", {})
    # consecutive requests are at least 0.2 s apart on the injected clock
    assert t[0] >= 0.2 * 3


def test_resume_skips_finished(tmp_path):
    fake, _ = _run(tmp_path)
    n1 = len(fake.calls)
    fake2 = Fake([])
    m = hb.run(tmp_path, "r1", fake2, n_markets=3, key=KEY, now=NOW, sleep=lambda s: None,
               live_check=None)
    assert fake2.calls == [] and m["counts"]["markets_done"] == 3 and n1 > 0


def test_disk_cap_stops_cleanly(tmp_path):
    fake = Fake([_market(i) for i in range(1, 6)])
    m = hb.run(tmp_path, "r1", fake, n_markets=3, key=KEY, now=NOW, sleep=lambda s: None,
               lookback_days=2, disk_cap=3000, live_check=None)
    assert m["stopped"] and m["counts"]["markets_done"] < 3
    assert hb.DiskBudget(tmp_path).scan() < 3000 + 10**7


def test_sample_seeded_and_category_policy():
    frame = [hb.frame_row(_market(i, closed=i % 2 == 0, vol=10 ** (3 + i % 3),
                                  fee=("crypto_fees" if i % 4 else "sports_fees")))
             for i in range(1, 80)]
    a, rep = hb.draw_sample(frame, 20, "s1")
    b, _ = hb.draw_sample(frame, 20, "s1")
    c, _ = hb.draw_sample(frame, 20, "s2")
    assert [r["market_id"] for r in a] == [r["market_id"] for r in b] and len(a) == 20
    assert [r["market_id"] for r in a] != [r["market_id"] for r in c]
    assert {r["status"] for r in a} == {"closed", "active"}  # closed and active both present
    assert not any("vol" in k for k in a[0]["stratum"].split("|"))
    inc, _ = hb.draw_sample(frame, 10, "s1", categories=["sports"], category_mode="include")
    assert inc and all(r["fee_category"] == "sports" for r in inc)
    with pytest.raises(ValueError):
        hb.draw_sample(frame, 10, "s1", category_mode="include")
    assert hb.frame_row({**_market(1), "clobTokenIds": '["a","b","c"]'}) is None


def _series(n_days=4, step=600, t0=1_780_000_000.0):
    ts = np.arange(t0, t0 + n_days * 86400, step, dtype=float)
    vals = 0.5 + 0.2 * np.sin(ts / 30000)
    return ts, vals


T0 = 1_780_000_000.0


def _mkt(**kw):
    r = hb.frame_row(_market(1, closed=False))
    r.update(created_at=pd.Timestamp(T0 - 86400, unit="s", tz="UTC").isoformat(),
             start_epoch=T0 - 86400, close_epoch=float("nan"), closed=0, status="active")
    return {**r, "stratum": "x", **kw}


def test_panel_grid_labels_and_no_lookahead():
    ts, vals = _series()
    df = hb.market_panel(_mkt(), ts, vals, None, True, 6, "r1")
    assert (df["provenance"] == "EXPLORATORY_HISTORICAL").all()
    assert (df["evidence_role"] == "exploratory_historical").all()
    assert (df["t_i"] % hb.GRID_S == 0).all()
    ok = df[df["target_available"]]
    assert np.allclose(ok["t_j"] - ok["t_i"], 6 * 3600)
    # target is the series value at/before t+H, origin value at/before t
    i = np.searchsorted(ts + hb.POINT_LAG_S, ok["t_j"].iloc[0], side="left") - 1
    assert ok["mid_j"].iloc[0] == vals[i]
    assert df["ml_sw_best_bid" if "ml_sw_best_bid" in df else "ml_spread"].isna().all()
    assert df["ml_log1p_liq"].isna().all()


def test_features_do_not_change_when_future_series_changes():
    ts, vals = _series()
    base = hb.market_panel(_mkt(), ts, vals, None, True, 2, "r1")
    cut = base["t_i"].iloc[10]
    v2 = vals.copy()
    v2[ts > cut] += 0.07  # alter everything after the origin
    alt = hb.market_panel(_mkt(), ts, v2, None, True, 2, "r1")
    f = [c for c in base.columns if c.startswith("ml_") and not c.startswith("ml_log_hours")]
    a = base[base["t_i"] <= cut].set_index("t_i")[f]
    b = alt[alt["t_i"] <= cut].set_index("t_i")[f]
    # the origin at t == cut sees points <= cut only (unchanged); later origins differ legitimately
    pd.testing.assert_frame_equal(a.loc[: cut], b.loc[: cut])


def test_trade_flow_strictly_before_origin_and_coverage():
    ts, vals = _series()
    t_or = ts[0] + 2 * 86400
    t_or = np.ceil(t_or / hb.GRID_S) * hb.GRID_S
    tr = pd.DataFrame({"ts": [t_or - 100, t_or, t_or + 50], "side": ["BUY"] * 3,
                       "size": [10.0, 99.0, 99.0], "price": [0.5] * 3,
                       "outcome_index": [0] * 3, "wallet_hash": ["a", "b", "c"],
                       "trade_key": ["1", "2", "3"]})
    df = hb.market_panel(_mkt(), ts, vals, tr, False, 2, "r1")
    row = df[df["t_i"] == t_or].iloc[0]
    assert row["ml_tf_n_2h"] == 1 and row["ml_tf_signed_vol_2h"] == 10.0  # ts == t excluded
    assert row["ml_tf_n_wallets_2h"] == 1
    # truncated history: windows reaching before the oldest fetched trade are NaN, not 0
    tr = pd.concat([tr, tr.iloc[:1].assign(ts=t_or - 10 * 3600, trade_key="0")])
    df2 = hb.market_panel(_mkt(), ts, vals, tr, True, 2, "r1")
    r2 = df2[df2["t_i"] == t_or].iloc[0]
    assert np.isnan(r2["ml_tf_n_24h"]) and r2["ml_tf_n_2h"] == 1
    # complete history with no trades: zero flow
    empty = tr.iloc[0:0]
    df3 = hb.market_panel(_mkt(), ts, vals, empty, False, 2, "r1")
    assert (df3["ml_tf_n_2h"] == 0).all()


def test_build_panel_end_to_end(tmp_path):
    _run(tmp_path)
    s = hb.build_panel(tmp_path / "r1")
    assert s["provenance"] == "EXPLORATORY_HISTORICAL"
    for h in (2, 6, 24):
        df = pd.read_csv(tmp_path / "r1" / f"panel_H{h}h.csv.gz")
        assert (df["provenance"] == "EXPLORATORY_HISTORICAL").all()
        assert (df["horizon_target_h"] == h).all()


def test_interval_end_shift_point_not_usable_until_lag_elapsed():
    ts, vals = _series()
    base = hb.market_panel(_mkt(), ts, vals, None, True, 2, "r1")
    t = float(base["t_i"].iloc[20])
    # a point stamped within POINT_LAG_S before the origin may be an interval that ends after t
    v2 = vals.copy()
    near = (ts > t - hb.POINT_LAG_S) & (ts < t)
    assert near.any()
    v2[near] += 0.2
    alt = hb.market_panel(_mkt(), ts, v2, None, True, 2, "r1")
    a = base[base["t_i"] == t].iloc[0]
    b = alt[alt["t_i"] == t].iloc[0]
    for c in ("mid_i", "ml_logit_mid", "ml_chg_1h", "ml_own_dmid_prev"):
        assert a[c] == b[c]
    # a point stamped exactly at the origin is never used either
    v3 = vals.copy()
    v3[ts == t] += 0.2
    c3 = hb.market_panel(_mkt(), ts, v3, None, True, 2, "r1")
    assert c3[c3["t_i"] == t].iloc[0]["mid_i"] == a["mid_i"]
    # a point older than the lag is used
    k = np.searchsorted(ts, t - hb.POINT_LAG_S - 1, side="right") - 1
    assert a["mid_i"] == vals[k]


def test_open_at_t_membership():
    ts, vals = _series()
    created = ts[0] + 2 * 86400
    close = ts[0] + 3 * 86400
    df = hb.market_panel(_mkt(created_at=pd.Timestamp(created, unit="s", tz="UTC").isoformat(),
                              closed=1, close_epoch=close, status="closed"),
                         ts, vals, None, True, 2, "r1")
    assert len(df) and (df["t_i"] >= created).all() and (df["t_i"] < close).all()
    # market with no createdAt/startDate cannot be placed in time: no rows
    assert not len(hb.market_panel(_mkt(created_at="", start_epoch=float("nan")), ts, vals,
                                   None, True, 2, "r1"))
    # active market: no upper bound
    act = hb.market_panel(_mkt(), ts, vals, None, True, 2, "r1")
    assert act["t_i"].max() > close


def test_no_end_of_life_or_static_metadata_features():
    ts, vals = _series()
    a = hb.market_panel(_mkt(), ts, vals, None, True, 2, "r1")
    b = hb.market_panel(_mkt(liquidity=9e9, volume=9e9, neg_risk=1, end_epoch=ts[0] + 1.0,
                             fee_category="other:x"), ts, vals, None, True, 2, "r1")
    feat = [c for c in a.columns if c.startswith("ml_")]
    pd.testing.assert_frame_equal(a[feat], b[feat])
    for c in ("ml_log1p_liq", "ml_log1p_vol24", "ml_turnover", "ml_volume_num", "ml_neg_risk",
              "ml_log_hours_to_end", "ml_end_unknown", "ml_spread", "ml_tick_size"):
        assert a[c].isna().all()


def test_never_under_snapshots(tmp_path):
    with pytest.raises(ValueError):
        hb.run(tmp_path / "snapshots", "r1", Fake([]), key=KEY, now=NOW, live_check=None)


def test_frame_windows_seeded_random_and_report():
    f1 = Fake([_market(i) for i in range(1, 6)])
    f2 = Fake([_market(i) for i in range(1, 6)])
    lim1 = hb.Limiter(f1, sleep=lambda s: None)
    lim2 = hb.Limiter(f2, sleep=lambda s: None)
    rows, rep = hb.fetch_frame(lim1, NOW, lookback_days=3, seed="a", windows_per_day=4)
    hb.fetch_frame(lim2, NOW, lookback_days=3, seed="a", windows_per_day=4)
    assert [c[1] for c in f1.calls] == [c[1] for c in f2.calls]  # same seed, same windows
    assert all("volume_num_min" not in c[1] for c in f1.calls)  # no final-volume filter
    assert rep["volume_floor"] is None and rep["excludes"] and len(rows) == 5
    _, rep2 = hb.fetch_frame(hb.Limiter(Fake([]), sleep=lambda s: None), NOW, lookback_days=1,
                             min_volume=1000, seed="a")
    assert rep2["volume_floor_label"] == "SEPARATE SUB-FRAME"


def test_wallet_features_causal_and_new_wallet_burn_in():
    ts, vals = _series(n_days=40)
    t_or = float(np.ceil((ts[0] + 30 * 86400) / hb.GRID_S) * hb.GRID_S)
    rows = []
    # wallet "old" trades early; wallet "new" first trades 1h before the origin; "late" after it
    for w, tt, sz in (("00" * 16, ts[0] + 3600, 5.0), ("00" * 16, t_or - 7000, 5.0),
                      ("11" * 16, t_or - 3600, 50.0), ("22" * 16, t_or + 10, 999.0)):
        rows.append([tt, "BUY", sz, 0.5, 0, w, f"k{tt}{w[:2]}"])
    tr = pd.DataFrame(rows, columns=hb.TRADE_COLUMNS)
    fsi = hb.FirstSeen.from_trades(tr)
    df = hb.market_panel(_mkt(), ts, vals, tr, False, 2, "r1", first_seen=fsi)
    row = df[df["t_i"] == t_or].iloc[0]
    assert row["ml_tf_n_wallets_2h"] == 2 and row["ml_wlt_new_n_2h"] == 1  # 'late' excluded
    assert row["ml_wlt_new_n_24h"] == 1 and row["ml_wlt_new_share_24h"] == 0.5
    assert abs(row["ml_wlt_hhi_24h"] - ((5 / 55) ** 2 + (50 / 55) ** 2)) < 1e-9
    assert row["ml_tf_large_2h"] == 50.0 / (55.0 / 2)  # max size / mean size over 24h
    # burn-in: an origin within 14 days of the first-seen sample start has no 'new' features
    early = df[df["t_i"] < fsi.g0 + hb.FIRST_SEEN_BURN_IN_S + 86400]
    assert len(early) and early["ml_wlt_new_n_24h"].isna().all()
    # the wallet features at t_or do not depend on trades at/after t_or
    tr2 = tr.copy()
    tr2.loc[3, "size"] = 1.0
    df2 = hb.market_panel(_mkt(), ts, vals, tr2, False, 2, "r1",
                          first_seen=hb.FirstSeen.from_trades(tr2))
    r2 = df2[df2["t_i"] == t_or].iloc[0]
    for c in hb.WLT_NAMES + hb.TF_NAMES:
        assert (np.isnan(row[c]) and np.isnan(r2[c])) or row[c] == r2[c]


def test_yield_to_live_collector():
    state = iter([True, True, False])
    slept = []
    w = hb.yield_to_live(lambda: next(state), slept.append)
    assert slept == [30.0, 30.0] and w == 60.0
    calls = []

    def tr(url, params):
        calls.append(1)
        return 200, b"[]", {}

    t = [0.0]
    flags = iter([True, False])
    lim = hb.Limiter(tr, sleep=lambda s: t.__setitem__(0, t[0] + s), clock=lambda: t[0],
                     live_check=lambda: next(flags))
    lim.get("u", {})
    assert lim.yielded_s == 30.0 and calls


def test_frame_resumable_after_interrupt(tmp_path):
    part = tmp_path / "p.jsonl"
    stops = iter([False, False, True])
    mk = lambda: hb.Limiter(Fake([_market(i) for i in range(1, 4)]), sleep=lambda s: None)  # noqa: E731
    with pytest.raises(hb.FrameInterrupted):
        hb.fetch_frame(mk(), NOW, lookback_days=4, windows_per_day=2, partial_path=part,
                       should_stop=lambda: next(stops))
    assert len(part.read_text().splitlines()) == 2
    f2 = Fake([_market(i) for i in range(1, 4)])
    rows, rep = hb.fetch_frame(hb.Limiter(f2, sleep=lambda s: None), NOW, lookback_days=4,
                               windows_per_day=2, partial_path=part)
    assert len(rows) == 3 and len(part.read_text().splitlines()) == 5
    assert rep["windows"]["closed"] == 10  # 5 days x 2 windows, 2 resumed from disk


def test_live_pass_matcher_ignores_watchers():
    assert hb._is_pass_command("/bin/bash /x/y/arepo_pass.sh --once")
    assert hb._is_pass_command("bash arepo_pass.sh")
    assert not hb._is_pass_command("/bin/zsh -c eval 'pgrep -f arepo_pass.sh; sleep 1'")
    assert not hb._is_pass_command("pgrep -f arepo_pass.sh")
    assert not hb._is_pass_command("python other.py")


def test_traded_before_t_and_unchanged_since_listing():
    ts, _ = _series(n_days=4)
    vals = np.full(len(ts), 0.5)
    vals[ts >= ts[0] + 2 * 86400] += 0.1  # price first moves after two days
    t_tr = ts[0] + 2.5 * 86400
    tr = pd.DataFrame([[t_tr, "BUY", 5.0, 0.6, 0, "a" * 32, "k"]], columns=hb.TRADE_COLUMNS)
    mk = _mkt(start_epoch=ts[0])
    df = hb.market_panel(mk, ts, vals, tr, False, 2, "r1")
    early, late = df[df["t_i"] < t_tr], df[df["t_i"] > t_tr]
    assert (early["traded_before_t"] == 0).all() and (late["traded_before_t"] == 1).all()
    pre = df[df["t_i"] < ts[0] + 2 * 86400]
    post = df[df["t_i"] > ts[0] + 2 * 86400 + 1200]
    assert (pre["price_unchanged_since_listing"] == 1).all()
    assert (post["price_unchanged_since_listing"] == 0).all()
    # truncated history: no known earlier trade -> unknown, not 0
    dt = hb.market_panel(mk, ts, vals, tr, True, 2, "r1")
    assert dt[dt["t_i"] < t_tr]["traded_before_t"].isna().all()
    # series not starting at listing: unchanged flag undefined
    d2 = hb.market_panel(_mkt(start_epoch=ts[0] - 10 * 86400), ts, vals, tr, False, 2, "r1")
    assert d2["price_unchanged_since_listing"].isna().all()
    # trade exactly at t is not "before t"
    tr2 = tr.assign(ts=float(df["t_i"].iloc[5]))
    d3 = hb.market_panel(mk, ts, vals, tr2, False, 2, "r1")
    assert d3.iloc[5]["traded_before_t"] == 0 and d3.iloc[6]["traded_before_t"] == 1
