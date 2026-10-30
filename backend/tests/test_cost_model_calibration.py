# ruff: noqa: E501
"""Tests for scripts/cost_model_calibration.py on small synthetic inputs (no real data)."""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts"))
import cost_model_calibration as cal  # noqa: E402

T0 = 1_792_000_000.0  # an arbitrary UTC epoch


def _iso(t: float) -> str:
    return pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _sweep(t: float, bid=0.40, ask=0.42, qb=50.0, qa=60.0, mid_shift=0.0) -> pd.DataFrame:
    return pd.DataFrame([{"token_id": "tok0", "market_id": "m1", "t": t, "best_bid": bid + mid_shift,
                          "best_ask": ask + mid_shift, "bid_size_1": qb, "ask_size_1": qa, "state": "two_sided"}])


SNAP = pd.DataFrame([{"market_id": "m1", "clob_token_id_0": "tok0", "event_id": "e1", "liquidity": 5000.0,
                      "fee_category": "politics"}])


def _trades(rows):
    return pd.DataFrame(rows, columns=["market_id", "ts", "side", "price", "size", "outcome_index"])


def test_first_of_pairs():
    runs = [(0.0, "a"), (120.0, "b"), (7200.0, "c"), (7300.0, "d"), (14400.0, "e")]
    assert [d for _, d in cal.first_of_pairs(runs)] == ["a", "c", "e"]


def test_schedule_rate_and_flags():
    assert cal.schedule_rate('{"rate":0.03,"exponent":1,"rebateRate":0.25}') == (0.03, 0.25)
    r = cal.schedule_rate(None)
    assert np.isnan(r[0]) and np.isnan(r[1])
    assert cal.fees_flag("1") is True and cal.fees_flag("false") is False and cal.fees_flag(None) is None


def test_maker_rows_queue_and_touch_rules():
    sw = _sweep(T0)
    nxt = _sweep(T0 + 7200, mid_shift=-0.02)  # mid falls 2c: bad for a filled bid
    trades = _trades([
        ("m1", T0 + 100, "SELL", 0.40, 30.0, 0),   # hits the bid at its price: 30 < 50 + 5 queue
        ("m1", T0 + 200, "BUY", 0.60, 30.0, 1),    # outcome-1 buy at 0.60 = outcome-0 sell at 0.40: total 60
        ("m1", T0 + 4000, "BUY", 0.45, 500.0, 0),  # outside the 1 h horizon
        ("m1", T0 - 10, "BUY", 0.42, 1.0, 0),      # before the origin
    ])
    m, cnt = cal.maker_rows(sw, SNAP, trades, nxt, (900.0, 3600.0), own_shares=5.0)
    assert cnt == {"sample_markets_in_origin": 1, "excluded_page_short": 0, "used": 1}
    bid = m[m["side"] == "bid"].iloc[0]
    ask = m[m["side"] == "ask"].iloc[0]
    assert bid["hit_vol_900"] == 60.0 and bid["fill_touch_900"] == 1 and bid["fill_queue_900"] == 1  # 60 >= 55
    assert ask["hit_vol_3600"] == 0.0 and ask["fill_queue_3600"] == 0
    assert bid["realised"] == pytest.approx(0.39 - 0.40)  # mark 0.39 - bid 0.40
    assert ask["realised"] == pytest.approx(0.42 - 0.39)


def test_maker_rows_through_trade_fills_regardless_of_queue():
    sw = _sweep(T0, qb=1e6)
    trades = _trades([("m1", T0 + 50, "SELL", 0.38, 1.0, 0)])  # trades through the bid
    m, _ = cal.maker_rows(sw, SNAP, trades, None, (900.0,), own_shares=5.0)
    assert m[m["side"] == "bid"].iloc[0]["fill_queue_900"] == 1


def test_maker_rows_excludes_short_trade_page():
    sw = _sweep(T0)
    rows = [("m1", T0 + 10 + i, "SELL", 0.40, 1.0, 0) for i in range(cal.TRADE_PAGE)]
    m, cnt = cal.maker_rows(sw, SNAP, _trades(rows), None, (900.0,), own_shares=5.0)
    assert cnt["excluded_page_short"] == 1 and len(m) == 0


def test_fit_lomax_recovers_shape():
    rng = np.random.default_rng(0)
    q = rng.uniform(0, 500, 4000)
    p = (1 + (q + 5) / 4.0) ** -0.3
    df = pd.DataFrame({"queue_ahead": q, "fill_queue_3600": (rng.random(4000) < p).astype(int)})
    sc, al = cal.fit_lomax(df, 3600, 5.0)
    pred = (1 + (q + 5) / sc) ** -al
    assert abs(pred.mean() - p.mean()) < 0.02


def test_cluster_boot():
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"x": [1, 0, 1, 0], "event_id": ["a", "a", "b", "c"]})
    r = cal.cluster_boot(df, "x", None, rng)
    assert r["est"] == 0.5 and r["clusters"] == 3 and r["ci95"][0] <= 0.5 <= r["ci95"][1]


def test_main_refuses_output_inside_data_root(tmp_path):
    root = tmp_path / "research_lab"
    (root / "book_sweeps").mkdir(parents=True)
    rc = cal.main(["--data-root", str(root), "--start", "2026-10-12T00:00:00Z", "--end", "2026-10-13T00:00:00Z",
                   "--out", str(root / "out")])
    assert rc == 2 and not (root / "out").exists()


def test_main_end_to_end_synthetic(tmp_path):
    root = tmp_path / "research_lab"
    t = cal.parse_name_ts("20261012T004000Z")
    for name, tt, shift in (("20261012T004000Z_aaaaaaaa", t, 0.0), ("20261012T024000Z_bbbbbbbb", t + 7200, -0.01)):
        d = root / "book_sweeps" / name
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"state": "complete", "snapshot_id": "S1"}))
        rows = pd.DataFrame([{"token_id": "tok0", "market_id": "m1", "batch_receipt_utc": _iso(tt),
                              "book_timestamp": int(tt * 1000) - 5000, "best_bid": 0.40 + shift,
                              "best_ask": 0.42 + shift, "bid_size_1": 50.0, "ask_size_1": 60.0,
                              "depth_bid_1c": 100.0, "depth_ask_1c": 120.0, "depth_bid_5c": 400.0,
                              "depth_ask_5c": 500.0, "tick_size": 0.01, "min_order_size": 5, "state": "two_sided"}])
        with gzip.open(d / "rows.csv.gz", "wt") as fh:
            rows.to_csv(fh, index=False)
    s = root / "snapshots" / "S1"
    s.mkdir(parents=True)
    with gzip.open(s / "rows.csv.gz", "wt") as fh:
        pd.DataFrame([{"market_id": "m1", "clob_token_id_0": "tok0", "event_id": "e1", "liquidity": 5000.0,
                       "volume24hr": 10.0}]).to_csv(fh, index=False)
    ts = root / "trade_samples" / "20261012T024400Z_cccccccc"
    ts.mkdir(parents=True)
    with gzip.open(ts / "trades.csv.gz", "wt") as fh:
        _trades([("m1", t + 100, "SELL", 0.40, 80.0, 0)]).to_csv(fh, index=False)
    out = tmp_path / "out"
    rc = cal.main(["--data-root", str(root), "--start", "2026-10-12T00:00:00Z", "--end", "2026-10-12T02:00:00Z",
                   "--out", str(out), "--book-every", "1"])
    assert rc == 0
    summ = json.loads((out / "summary.json").read_text())
    assert summ["books"]["all"]["n"] == 1
    assert summ["maker"]["all"]["all"]["orders"] == 2
    assert summ["maker"]["all"]["all"]["fill_queue_900"]["est"] == 0.5
    assert summ["inputs"][0]["trade_sample"] == "20261012T024400Z_cccccccc"
