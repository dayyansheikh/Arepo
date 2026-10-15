# ruff: noqa: E501
from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from astrolabe.research_lab import history_sources as hs
from astrolabe.research_lab import wallet_sidecar

ADDR = "0xAbC0000000000000000000000000000000000001"
KEY = b"k" * 32


def _ev(et, r, v=None, **kw):
    return {"event_type": et, "receipt_ms": r, "venue_ms": v or r, **kw}


def test_rebuild_book_applies_absolute_price_changes():
    b = hs.rebuild_book([
        _ev("price_change", 1, price=Decimal("0.4"), size=Decimal("5"), side="BUY"),  # before book
        _ev("book", 2, bids='[["0.40","10"],["0.39","5"]]', asks='[["0.45","7"]]'),
        _ev("price_change", 3, price=Decimal("0.40"), size=Decimal("0"), side="BUY"),
        _ev("price_change", 4, price=Decimal("0.44"), size=Decimal("3"), side="SELL"),
        _ev("tick_size_change", 5, new_tick_size=Decimal("0.001")),
    ])
    assert [x["price"] for x in b["bids"]] == ["0.39"]
    assert [x["price"] for x in b["asks"]] == ["0.44", "0.45"]
    assert b["tick_size"] == "0.001" and b["receipt_ms"] == 4
    assert hs.rebuild_book([_ev("price_change", 1, price=Decimal("0.4"), size=1, side="BUY")]) is None


def test_book_row_shape_and_crossed():
    book = {"bids": [{"price": "0.5", "size": "10"}], "asks": [{"price": "0.5", "size": "4"}],
            "tick_size": None, "receipt_ms": 1_000, "venue_ms": 900}
    row = hs.book_row("s", "0xc", "tok", book)
    assert set(hs.book_sweep.ROW_COLUMNS) <= set(row)
    assert row["crossed"] is True and row["state"] == "crossed"
    assert hs.book_row("s", "c", "t", None)["state"] == "no_book"


def _parquet_bytes(rows):
    sch = pa.schema([("timestamp_received", pa.timestamp("ms", "UTC")), ("timestamp", pa.timestamp("ms", "UTC")),
                     ("market", pa.string()), ("event_type", pa.string()), ("asset_id", pa.string()),
                     ("bids", pa.string()), ("asks", pa.string()), ("price", pa.decimal128(9, 4)),
                     ("size", pa.decimal128(18, 6)), ("side", pa.string()),
                     ("new_tick_size", pa.decimal128(9, 4))])
    cols = {n: [r.get(n) for r in rows] for n in sch.names}
    buf = io.BytesIO()
    pq.write_table(pa.table(cols, schema=sch), buf, row_group_size=2)
    return buf.getvalue()


def _t(h, m, s=0):
    return datetime(2026, 8, 1, h, m, s, tzinfo=UTC)


def test_load_book_snapshots_is_causal_and_prunes():
    d = Decimal
    rows = [
        dict(timestamp_received=_t(12, 1), timestamp=_t(12, 1), market="0xa", event_type="book",
             asset_id="111", bids='[["0.40","10"]]', asks='[["0.60","10"]]'),
        dict(timestamp_received=_t(12, 10), timestamp=_t(12, 10), market="0xa", event_type="price_change",
             asset_id="111", price=d("0.41"), size=d("2"), side="BUY"),
        dict(timestamp_received=_t(12, 40), timestamp=_t(12, 40), market="0xa", event_type="price_change",
             asset_id="111", price=d("0.59"), size=d("9"), side="BUY"),  # after t: must be ignored
        dict(timestamp_received=_t(12, 2), timestamp=_t(12, 2), market="0xb", event_type="book",
             asset_id="999", bids='[["0.1","1"]]', asks='[["0.2","1"]]'),
        dict(timestamp_received=_t(12, 5), timestamp=_t(11, 59), market="0xb", event_type="book",
             asset_id="222", bids='[["0.1","1"]]', asks='[["0.9","1"]]'),
    ]
    data = _parquet_bytes(sorted(rows, key=lambda r: r["asset_id"]))
    urls = []

    def fetch(url, a, b):
        urls.append(url)
        return data[a: b + 1]

    st: dict = {}
    out = hs.load_book_snapshots(_t(12, 30), ["111", "222", "333"], fetch=fetch,
                                 size_fn=lambda u: len(data), lookback_hours=0, stats=st)
    by = {r["token_id"]: r for r in out}
    assert by["111"]["best_bid"] == 0.41 and by["111"]["condition_id"] == "0xa"
    assert by["111"]["receipt_ts_ms"] == int(_t(12, 10).timestamp() * 1000)
    assert by["222"]["state"] == "two_sided"
    assert by["333"]["state"] == "no_book"
    assert st["row_groups_read"] < st["row_groups_total"]  # asset_id stats pruned the "999" group
    assert all("2026-08-01T12" in u for u in urls)


def test_load_book_snapshots_rejects_after_archive_end():
    with pytest.raises(ValueError):
        hs.load_book_snapshots(datetime(2026, 8, 11, tzinfo=UTC), ["1"], fetch=lambda *a: b"",
                               size_fn=lambda u: 0)


# --- wallet history ---------------------------------------------------------------------


class FakeApi:
    def __init__(self, events, fail_first=0):
        self.events, self.calls, self.fail = events, [], fail_first

    def __call__(self, path, params):
        self.calls.append(dict(params))
        if self.fail:
            self.fail -= 1
            return 429, None, {"retry-after": "0"}
        ev = sorted(self.events, key=lambda e: e["timestamp"])
        lo, hi = params.get("start", 0), params["end"]
        sel = [e for e in ev if lo <= e["timestamp"] <= hi]
        o, n = params["offset"], params["limit"]
        return 200, sel[o: o + n], {}


def _events(n, t0=1000, step=10):
    return [{"timestamp": t0 + i * step, "type": "TRADE", "side": "BUY" if i % 2 == 0 else "SELL",
             "usdcSize": 2.0, "transactionHash": f"0x{i}", "asset": "a", "size": 1} for i in range(n)]


def _wh(tmp_path, api, **kw):
    return hs.WalletHistory(tmp_path / "cache", key=KEY, get=api,
                            limiter=hs.RateLimiter(0, sleep=lambda s: None), sleep=lambda s: None, **kw)


def test_lookup_is_as_of_and_hashes_wallet(tmp_path):
    api = FakeApi(_events(10) + [{"timestamp": 5000, "type": "REDEEM", "usdcSize": 7.0,
                                  "transactionHash": "0xr", "asset": "a", "size": 1}])
    wh = _wh(tmp_path, api)
    r = wh.lookup(ADDR, 1050)  # events at 1000..1040 strictly before
    assert r["wallet_hash"] == wallet_sidecar.hash_wallet(KEY, ADDR.lower())
    assert r["first_trade_ts"] == 1000 and r["n_prior_trades"] == 5
    assert r["prior_volume_usdc"] == 10.0 and r["prior_redeem_usdc"] == 0.0 and r["covered"]
    assert all(c["end"] <= 1049 for c in api.calls)  # never asks beyond as-of
    r2 = wh.lookup(ADDR, 6000)
    assert r2["n_prior_trades"] == 10 and r2["prior_redeem_usdc"] == 7.0


def test_cache_reuse_and_no_raw_address_on_disk(tmp_path):
    api = FakeApi(_events(4))
    wh = _wh(tmp_path, api)
    wh.lookup(ADDR, 2000)
    n = len(api.calls)
    wh.lookup(ADDR, 1500)  # earlier as-of served from cache
    assert len(api.calls) == n
    blob = "".join(p.read_text() for p in (tmp_path / "cache").iterdir())
    assert ADDR.lower()[2:] not in blob.lower() and "0x" not in blob.lower().replace("0xabc", "")
    assert [p.name for p in (tmp_path / "cache").iterdir()] == [
        wallet_sidecar.hash_wallet(KEY, ADDR) + ".json"]


def test_new_wallet_and_retry_backoff(tmp_path):
    api = FakeApi([], fail_first=2)
    r = _wh(tmp_path, api).lookup(ADDR, 10_000)
    assert r["first_trade_ts"] is None and r["n_prior_trades"] == 0 and len(api.calls) == 3


def test_paging_slides_window_past_offset_cap(tmp_path):
    api = FakeApi(_events(6000, step=1))
    r = _wh(tmp_path, api).lookup(ADDR, 10_000_000)
    assert r["n_prior_trades"] == 6000 and not r["truncated"]
    assert max(c["offset"] for c in api.calls) <= 4500


def test_truncation_flag(tmp_path):
    api = FakeApi(_events(1500, step=1))
    r = _wh(tmp_path, api, max_events=1000).lookup(ADDR, 10_000_000)
    assert r["truncated"] and r["first_trade_ts"] == 1000 and r["n_prior_trades"] >= 1000


def test_errors_do_not_leak_address(tmp_path):
    def bad(path, params):
        return 400, None, {}

    with pytest.raises(hs.SourceError) as e:
        _wh(tmp_path, bad).lookup(ADDR, 10)
    assert ADDR.lower() not in str(e.value).lower()


def test_manifest_role(tmp_path):
    p = hs.write_manifest(tmp_path, "m", {"x": 1})
    assert json.loads(p.read_text())["evidence_role"] == "exploratory_historical"


def test_same_second_burst_terminates_as_truncated(tmp_path):
    api = FakeApi(_events(6000, step=0))
    r = _wh(tmp_path, api).lookup(ADDR, 10_000)
    assert r["truncated"] and len(api.calls) <= 60


def test_market_stats_pruning_with_condition_ids():
    d = Decimal
    rows = []
    for i, m in enumerate(["0xa1", "0xa2", "0xb1", "0xb2", "0xc1", "0xc2"]):
        rows.append(dict(timestamp_received=_t(12, 1), timestamp=_t(12, 1), market=m, event_type="book",
                         asset_id=f"9{i}", bids='[["0.3","1"]]', asks='[["0.4","1"]]'))
        rows.append(dict(timestamp_received=_t(12, 2), timestamp=_t(12, 2), market=m,
                         event_type="price_change", asset_id=f"9{i}", price=d("0.31"), size=d("1"),
                         side="BUY"))
    data = _parquet_bytes(rows)  # market-sorted, 6 row groups of 2
    st: dict = {}
    out = hs.load_book_snapshots(_t(12, 30), ["94"], fetch=lambda u, a, b: data[a: b + 1],
                                 size_fn=lambda u: len(data), lookback_hours=0, stats=st,
                                 condition_ids={"94": "0xc1"})
    assert out[0]["best_bid"] == 0.31 and st["row_groups_read"] <= 2


# --- historical features ----------------------------------------------------------------------


def test_origin_window_and_pairs(tmp_path):
    import pandas as pd

    ts = lambda s: datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp()  # noqa: E731
    assert hs.origin_in_window(ts("2026-05-01T06:00:00"))
    assert not hs.origin_in_window(ts("2026-06-14T06:00:00"))  # outage days
    assert not hs.origin_in_window(ts("2026-08-10T00:00:00"))
    assert not hs.origin_in_window(ts("2026-04-13T12:00:00"))
    p = tmp_path / "panel.csv"
    pd.DataFrame({"market_id": ["1", "1", "2", "3"],
                  "t_i": [ts("2026-05-01T06:00:00"), ts("2026-05-01T08:00:00"),
                          ts("2026-05-01T06:00:00"), ts("2026-06-14T06:00:00")]}).to_csv(p, index=False)
    assert hs.panel_pairs([p]) == {ts("2026-05-01T06:00:00"): {"1", "2"}}


def test_spread_order_covers_window():
    o = [float(i) for i in range(30)]
    first = hs.spread_origin_order(o)[:5]
    assert first == [0.0, 7.0, 14.0, 21.0, 28.0] and sorted(hs.spread_origin_order(o)) == o


def test_sw_row_nan_for_crossed_and_age():
    ok = hs.book_row("s", "c", "t", {"bids": [{"price": "0.4", "size": "1"}],
                                      "asks": [{"price": "0.5", "size": "1"}],
                                      "tick_size": None, "receipt_ms": 9_000, "venue_ms": 8_000})
    r = hs.sw_row(ok, 10.0)
    assert r["sw_best_bid"] == 0.4 and r["sw_book_age_s"] == 2.0
    bad = hs.book_row("s", "c", "t", {"bids": [{"price": "0.5", "size": "1"}],
                                       "asks": [{"price": "0.4", "size": "1"}],
                                       "tick_size": None, "receipt_ms": 1, "venue_ms": 1})
    assert bad["crossed"] and all(v != v for v in hs.sw_row(bad, 10.0).values())


def test_book_feature_run_end_to_end(tmp_path):
    d = Decimal
    t0 = datetime(2026, 5, 1, 6, tzinfo=UTC).timestamp()
    prev = datetime(2026, 5, 1, 5, 30, tzinfo=UTC)
    after = datetime(2026, 5, 1, 6, 0, 1, tzinfo=UTC)
    rows = [
        dict(timestamp_received=prev, timestamp=prev, market="0xa", event_type="book", asset_id="111",
             bids='[["0.40","10"]]', asks='[["0.44","30"]]'),
        dict(timestamp_received=after, timestamp=after, market="0xa", event_type="price_change",
             asset_id="111", price=d("0.43"), size=d("5"), side="BUY"),  # after the origin
    ]
    data = _parquet_bytes(rows)
    seen = []

    def fetch(u, a, b):
        seen.append(u)
        return data[a: b + 1]

    run = hs.BookFeatureRun(tmp_path, {t0: {"7"}}, {"7": ("0xa", "111")}, fetch=fetch,
                            size_fn=lambda u: len(data), lookback_hours=0)
    s = run.run(60)
    assert s["origins_done_total"] == 1 and "2026-05-01T05" in seen[0]  # the previous hour's file
    assert hs.BookFeatureRun(tmp_path, {t0: {"7"}}, {"7": ("0xa", "111")}).run(60)["origins_done_this_run"] == 0
    out = hs.load_book_features(hs.finalize_book_features(tmp_path))
    r = out.iloc[0]
    assert r.market_id == "7" and r.origin_ts == t0 and r.sw_best_bid == 0.40  # after-origin ignored
    assert r.ml_sw_spread == pytest.approx(0.04) and r.evidence_role == "exploratory_historical"


def test_first_trade_one_request_and_hashed(tmp_path):
    api = FakeApi(_events(5))
    wh = _wh(tmp_path, api)
    r = wh.first_trade(ADDR, 1020)
    assert r["first_trade_ts"] == 1000 and len(api.calls) == 1 and api.calls[0]["limit"] == 1
    assert ADDR.lower() not in json.dumps(r)
    assert wh.first_trade(ADDR, 10)["first_trade_ts"] is None


def test_new_wallet_features_causal_and_coverage(tmp_path):
    import pandas as pd

    tdir = tmp_path / "trades"
    tdir.mkdir()
    day = 86400
    pd.DataFrame({"ts": [100 * day, 100 * day + 10, 100 * day + 20, 101 * day + 5],
                  "side": "BUY", "size": [10, 10, 10, 100], "price": [0.5] * 4, "outcome_index": 0,
                  "wallet_hash": ["a", "b", "c", "a"], "trade_key": list("wxyz")}
                 ).to_csv(tdir / "m1.csv.gz", index=False)
    pan = tmp_path / "panel.csv"
    pd.DataFrame({"market_id": ["m1", "m1"], "t_i": [100 * day + 3600, 101 * day]}).to_csv(pan, index=False)
    prog = tmp_path / "progress.jsonl"
    prog.write_text(json.dumps({"market_id": "m1", "trades_truncated": False}) + "\n")
    ft = tmp_path / "ft.jsonl"
    ft.write_text("\n".join(json.dumps({"wallet_hash": h, "first_trade_ts": v, "end_ts": 0}) for h, v in
                            [("a", 100 * day), ("b", 50 * day)]) + "\n")  # c unknown
    df = hs.new_wallet_features(pan, tdir, prog, ft).set_index("origin_ts")
    r = df.loc[100 * day + 3600]  # trades 1-3 only (the day-101 trade is in the future)
    assert r.nw_n_trades_24h == 3 and r.nw_cov_vol_24h == pytest.approx(2 / 3)
    assert r.nw_share_new1d == pytest.approx(0.5) and r.nw_n_new1d == 1  # a new, b old
    assert r.nw_share_new30d == pytest.approx(0.5) and r.nw_n_new30d == 1
    r2 = df.loc[101 * day]  # window [100d, 101d): same three trades, strictly before origin
    assert r2.nw_n_trades_24h == 3
    prog.write_text(json.dumps({"market_id": "m1", "trades_truncated": True,
                                "trades_oldest_ts": 100 * day + 500}) + "\n")
    df2 = hs.new_wallet_features(pan, tdir, prog, ft).set_index("origin_ts")
    assert df2.loc[100 * day + 3600].isna()["nw_share_new1d"]  # history does not reach the window start


def test_memory_gate(monkeypatch):
    assert hs.heavy_gate.__defaults__[0] == 15.0
    monkeypatch.setattr(hs, "memory_free_pct", lambda: 36.0)
    from astrolabe.research_lab import history_backfill as hb
    monkeypatch.setattr(hb, "live_pass_running", lambda: False)
    assert hs.heavy_gate(sleep=lambda s: None) == 0.0


def test_fetch_market_wallets_keeps_only_known_hashes():
    class Lim:
        def get(self, url, params):
            return 200, [{"proxyWallet": ADDR, "size": 10, "price": 0.5},
                         {"proxyWallet": "0xother", "size": 1, "price": 0.5}]

    h = wallet_sidecar.hash_wallet(KEY, ADDR)
    out = hs.fetch_market_wallets(Lim(), "0xc", KEY, {h})
    assert list(out) == [h] and out[h] == [ADDR, 5.0]


def test_book_feature_run_resumes_per_pair(tmp_path):
    t0 = datetime(2026, 5, 1, 6, tzinfo=UTC).timestamp()
    prev = datetime(2026, 5, 1, 5, 30, tzinfo=UTC)
    rows = [dict(timestamp_received=prev, timestamp=prev, market=m, event_type="book", asset_id=a,
                 bids='[["0.40","10"]]', asks='[["0.44","30"]]') for m, a in (("0xa", "111"), ("0xb", "222"))]
    data = _parquet_bytes(rows)
    kw = dict(fetch=lambda u, a, b: data[a: b + 1], size_fn=lambda u: len(data), lookback_hours=0)
    tok = {"7": ("0xa", "111"), "8": ("0xb", "222")}
    assert hs.BookFeatureRun(tmp_path, {t0: {"7"}}, tok, **kw).run(60)["rows_this_run"] == 1
    r = hs.BookFeatureRun(tmp_path, {t0: {"7", "8"}}, tok, **kw).run(60)  # a second panel adds market 8
    assert r["rows_this_run"] == 1 and r["pairs_done_total"] == 2
    assert len(hs.load_book_features(hs.finalize_book_features(tmp_path))) == 2
