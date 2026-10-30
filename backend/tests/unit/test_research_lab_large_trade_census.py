"""Large-trade census tests: fake transport only, no network."""

from __future__ import annotations

import json

from astrolabe.research_lab import history_backfill as hb
from astrolabe.research_lab import large_trade_census as ltc

KEY = b"k" * 32


class FakeV2:
    def __init__(self, n, page=1000):
        self.rows = [{"timestamp": 10_000 - i, "condition_id": f"0xc{i % 3}",
                      "token_id": f"t{i % 3}",
                      "side": "BUY", "outcome_index": i % 2, "price": 0.1, "size": 10000,
                      "proxy_wallet": f"0xABC{i % 5:037d}", "transaction_hash": f"0x{i:064x}",
                      "slug": f"s{i % 3}", "event_slug": "e", "title": "T", "outcome": "Yes",
                      "name": "SECRETNAME", "bio": "SECRETBIO"} for i in range(n)]
        self.page = page

    def __call__(self, url, params):
        assert url == ltc.V2_TRADES and params["filterType"] == "CASH"
        start = int(params.get("cursor") or 0)
        data = self.rows[start:start + self.page]
        nxt = str(start + self.page) if start + self.page < len(self.rows) else None
        return 200, json.dumps({"data": data, "pagination": {"next_cursor": nxt}}).encode(), {}


def _lim(t):
    return hb.Limiter(t, rps=1e9, sleep=lambda s: None, live_check=None)


def test_pull_census_stops_resumes_and_hashes(tmp_path):
    fake = FakeV2(3500)
    p = ltc.pull_census(tmp_path, _lim(fake), KEY, min_cash=500, stop_ts=10_000 - 2500,
                        pages_per_chunk=1)
    assert p["done"] and p["end_reason"] == "stop_ts reached"
    df = ltc.load_census(tmp_path)
    assert len(df) == 3000 and df["ts"].is_monotonic_increasing
    import gzip

    text = "".join(gzip.decompress(f.read_bytes()).decode()
                   for f in (tmp_path / "chunks").glob("*"))
    assert "0xabc" not in text.lower() and "SECRET" not in text
    assert df["wallet_hash"].str.len().eq(64).all()
    meta = (tmp_path / "markets.jsonl").read_text()
    assert "SECRET" not in meta and "0xABC" not in meta
    assert ltc.load_market_meta(tmp_path)["0xc0"]["slug"] == "s0"
    # resume: a finished run does nothing
    again = ltc.pull_census(tmp_path, _lim(fake), KEY, min_cash=500, stop_ts=0)
    assert again["pages"] == p["pages"]


def test_pull_census_interrupt_then_resume(tmp_path):
    fake = FakeV2(2500)
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 2

    p1 = ltc.pull_census(tmp_path, _lim(fake), KEY, min_cash=500, stop_ts=0, pages_per_chunk=1,
                         should_stop=stop)
    assert not p1["done"] and p1["rows"] == 2000
    p2 = ltc.pull_census(tmp_path, _lim(fake), KEY, min_cash=500, stop_ts=0, pages_per_chunk=1)
    assert p2["done"] and len(ltc.load_census(tmp_path)) == 2500


class FakeV1:
    """v1 /trades fake: market list + start/end honoured, offset cap enforced."""

    def __init__(self, n):
        self.rows = [{"timestamp": 1000 + i, "conditionId": f"0xc{i % 4}", "asset": "a",
                      "side": "BUY", "outcomeIndex": 0, "price": 0.1, "size": 10000,
                      "proxyWallet": f"0xW{i % 9:039d}", "transactionHash": f"0x{i:064x}",
                      "slug": "s", "eventSlug": "e", "title": "T", "outcome": "Yes"}
                     for i in range(n)]

    def __call__(self, url, params):
        if params["offset"] > hb.TRADE_OFFSET_CAP:
            return 400, b'{"error":"cap"}', {}
        ms = set(params["market"].split(","))
        d = [t for t in self.rows if t["conditionId"] in ms
             and params["start"] <= t["timestamp"] <= params["end"]]
        d.sort(key=lambda t: -t["timestamp"])
        o = params["offset"]
        return 200, json.dumps(d[o:o + params["limit"]]).encode(), {}


def test_census_markets_batches_and_splits(tmp_path):
    import pandas as pd

    fake = FakeV1(30000)
    mk = pd.DataFrame({"condition_id": ["0xc0", "0xc1", "0xc2"], "created_ts": [0.0] * 3,
                       "closed_ts": [float("nan")] * 3, "end_ts": [1e9] * 3})
    rep = ltc.census_markets(_lim(fake), KEY, tmp_path, mk, 0, 10**6, 500, batch=2)
    assert rep["incomplete_windows"] == 0
    df = ltc.load_census(tmp_path)
    assert len(df) == 22500 and set(df["condition_id"]) == {"0xc0", "0xc1", "0xc2"}
    again = ltc.census_markets(_lim(fake), KEY, tmp_path, mk, 0, 10**6, 500, batch=2)
    assert again["batches"] == 0  # resumable


def test_anchored_rows_causal_and_labels():
    import numpy as np
    import pandas as pd

    t = 100 * 86400
    pts = np.arange(t - 30 * 3600, t + 30 * 3600, 600, dtype=float)
    vals = np.where(pts < t + 3600, 0.10, 0.30)
    tr = pd.DataFrame([[t - 3000, "BUY", 20000.0, 0.1, 0, "w1", "k1"],
                       [t - 100, "BUY", 50.0, 0.1, 0, "w2", "k2"],
                       [t, "BUY", 1e6, 0.1, 0, "w3", "k3"]], columns=hb.TRADE_COLUMNS)
    rows = ltc.anchored_rows({"condition_id": "0xc", "event_slug": "e"}, t, tr, t - 86400,
                             pts, vals, None)
    assert [r["horizon_target_h"] for r in rows] == [2.0, 6.0, 24.0]
    r = rows[0]
    assert r["ml_tf_n_2h"] == 2.0  # the print at exactly t is excluded
    assert np.isclose(r["mid_i"], 0.10) and np.isclose(r["y_dmid"], 0.20)
    assert ltc.anchored_rows({"condition_id": "0xc"}, t, tr, t - 86400, pts,
                             np.full(len(pts), 0.99), None) == []  # outside MID_RANGE
