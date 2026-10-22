# ruff: noqa: E501
"""CB7 q0146 (``xv-prints``) and q0147 (``census``): astrolabe.research_lab.cb7_xv / cb7_census and scripts/run_cb7.py
(docs/research_lab/CREATIVE_BATCH_7.md CB7-X, CB7-F, section 2.7). Everything runs against fakes: no network, no host data."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb7_census as cc
from astrolabe.research_lab import cb7_common as cm
from astrolabe.research_lab import cb7_seal as cs
from astrolabe.research_lab import cb7_xv as xv
from astrolabe.research_lab import history_backfill as hb
from tests.unit import test_cb7_fetch as tf

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_cb7 as script  # noqa: E402

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC).timestamp()
WIN_START = datetime(2026, 6, 1, 6, tzinfo=UTC).timestamp()
WIN_END = datetime(2026, 6, 3, 12, tzinfo=UTC).timestamp()
D1, D2, D3 = "2026-06-01", "2026-06-02", "2026-06-03"
DAY0 = {D1: datetime(2026, 6, 1, tzinfo=UTC).timestamp(), D2: datetime(2026, 6, 2, tzinfo=UTC).timestamp(), D3: datetime(2026, 6, 3, tzinfo=UTC).timestamp()}


def trade(ts, *, side="BUY", idx=0, price=0.40, size=1.0):
    return {"timestamp": int(ts), "side": side, "size": size, "price": price, "outcomeIndex": idx, "proxyWallet": "0xwalletsecret",
            "transactionHash": "0xhash", "asset": "tok"}


def day_rows(day, n, base=6):
    """n rows inside the UTC day (spread over distinct seconds, after 06:00 on the first day)."""
    d0 = DAY0[day] + (base * 3600 if day == D1 else 0)
    return [trade(d0 + i % 40000, price=0.30 + (i % 50) / 1000) for i in range(n)]


class FakeTrades:
    """Data /trades with offset paging (newest first) and Gamma /markets by id; any other URL is a bug."""

    def __init__(self, rows=None, *, fail_cids=(), gamma=None):
        self.rows = rows or {}
        self.fail_cids = set(fail_cids)
        self.gamma = gamma or {}
        self.log: list[dict] = []

    def __call__(self, url, params):
        if url.endswith("/markets"):
            ids = [str(x) for x in params["id"]]
            return 200, json.dumps([{"id": i, "conditionId": self.gamma[i], "outcomes": '["Yes","No"]', "events": [{"title": "t"}]} for i in ids if i in self.gamma]).encode(), {}
        assert url == hb.DATA_TRADES, url
        self.log.append(dict(params))
        assert params["takerOnly"] == "true" and int(params["limit"]) == 1000
        cid = params["market"]
        if cid in self.fail_cids:
            return 500, b"", {}
        rs = [x for x in self.rows.get(cid, []) if int(params["start"]) <= x["timestamp"] <= int(params["end"])]
        rs.sort(key=lambda x: -x["timestamp"])
        off = int(params["offset"])
        return 200, json.dumps(rs[off:off + 1000]).encode(), {}


def leg(key="KX-A", cid="cA", **kw):
    return {"pair_key": key, "p_market_id": f"m{key}", "p_event_id": f"E{key}", "k_cat": "Politics", "condition_id": cid,
            "win_start": WIN_START, "win_end": WIN_END, "token0": "tok", **kw}


def fetch(tmp, api, legs, **kw):
    base = {"now": NOW, "sleep": lambda s: None, "live_check": None, "wall_clock": lambda: NOW + 3600, "cap_at": "2026-10-22T00:00Z"}
    base.update(kw)
    return xv.xv_prints_fetch(tmp / "creative_batch7", api, legs=legs, **base)


def run_to_end(tmp, api, legs, limit=10, **kw):
    for _ in range(limit):
        m = fetch(tmp, api, legs, **kw)
        if m.get("status") not in (None, "in_progress"):
            return m
    raise AssertionError("no terminal state")


def rd_gz(path):
    return list(cm.read_csv_gz(path))


# ---- fetch: print mapping, pages, capped day ----------------------------------------------------------------------------------------


def test_map_trade_row_yes_terms_and_matches_origin_prints_mapping():
    cases = [(0, "BUY", 0.40, 0.40, 1), (0, "SELL", 0.40, 0.40, -1), (1, "SELL", 0.30, 0.70, 1), (1, "BUY", 0.30, 0.70, -1)]
    for idx, side, p, yes, ask in cases:
        r = xv.map_trade_row(trade(1000, side=side, idx=idx, price=p))
        assert r == [1000, pytest.approx(yes), 1.0, ask]
    assert xv.map_trade_row({"timestamp": 1, "side": "HOLD", "size": 1, "price": 0.5, "outcomeIndex": 0}) is None
    assert xv.map_trade_row({"timestamp": "x"}) is None
    # identical to the CB7 origin_prints mapping on the same rows
    api = lambda url, params: (200, json.dumps([trade(500, side=s, idx=i, price=0.3) for i, s in ((0, "BUY"), (1, "SELL"), (1, "BUY"))]).encode(), {})  # noqa: E731
    lim = hb.Limiter(api, rps=100, sleep=lambda s: None, live_check=None)
    rows, _ = cm.origin_prints(lim, "c", 1000)
    assert sorted([r[0], r[1], r[3]] for r in rows) == sorted([r[0], r[1], r[3]] for r in (xv.map_trade_row(trade(500, side=s, idx=i, price=0.3)) for i, s in ((0, "BUY"), (1, "SELL"), (1, "BUY"))))


def test_day_segments_clip_to_window_and_cap():
    segs = xv.day_segments(WIN_START, WIN_END, NOW)
    assert [s[0] for s in segs] == [D1, D2, D3] and segs[0][1] == int(WIN_START) and segs[-1][2] == int(WIN_END)
    assert [s[0] for s in xv.day_segments(WIN_START, WIN_END, DAY0[D2])] == [D1]  # nothing at or after the cap
    assert xv.day_segments(WIN_START, WIN_START, NOW) == []


def test_fetch_pages_capped_day_unavailable_and_never_filled(tmp_path):
    rows = day_rows(D1, 2500) + day_rows(D2, 10000) + day_rows(D3, 9000)  # D1: 3 pages; D2: exactly the cap; D3: 9 full pages then an empty one
    api = FakeTrades({"cA": rows})
    m = run_to_end(tmp_path, api, [leg()])
    assert m["status"] == xv.XV_COMPLETE and m["complete"] is True
    days = {r["day"]: r for r in rd_gz(tmp_path / "creative_batch7" / "xv_prints" / "days.csv.gz")}
    assert days[D1]["status"] == "done" and days[D1]["n_pages"] == "3" and days[D1]["n_stored"] == "2500"
    assert days[D2]["status"] == "capped" and days[D2]["capped"] == "1" and days[D2]["n_pages"] == "10" and days[D2]["n_stored"] == "0"
    assert days[D3]["status"] == "done" and days[D3]["n_pages"] == "10" and days[D3]["n_stored"] == "9000"  # the 10th page is empty: not capped
    d2_reqs = [p for p in api.log if int(p["start"]) == int(DAY0[D2])]
    assert len(d2_reqs) == 10 and max(int(p["offset"]) for p in d2_reqs) == 9000  # never an 11th page, never a fill
    stored = rd_gz(tmp_path / "creative_batch7" / "xv_prints" / "prints" / "KX-A.csv.gz")
    assert len(stored) == 2500 + 9000
    d2_lo, d2_hi = DAY0[D2], DAY0[D2] + 86400
    assert not [r for r in stored if d2_lo <= float(r["ts"]) < d2_hi]  # a capped day contributes no print at all
    assert m["counts"]["days_capped"] == 1


def test_fetch_stores_no_wallet_and_only_declared_columns(tmp_path):
    api = FakeTrades({"cA": day_rows(D1, 5)})
    run_to_end(tmp_path, api, [leg()])
    out = tmp_path / "creative_batch7" / "xv_prints"
    for f in out.rglob("*"):
        if f.is_file():
            raw = f.read_bytes()
            if f.suffix == ".gz":
                raw = gzip.decompress(raw)
            assert b"0xwalletsecret" not in raw and b"0xhash" not in raw, f
    rows = rd_gz(out / "prints" / "KX-A.csv.gz")
    assert list(rows[0]) == xv.PRINT_FILE_COLUMNS == ["pair_key", "ts", "side", "yes_price", "size"]


def test_fetch_resumable_identical_to_uninterrupted(tmp_path):
    rows = day_rows(D1, 1500) + day_rows(D2, 300) + day_rows(D3, 50)
    legs = [leg("KX-A", "cA"), leg("KX-B", "cB")]
    full = FakeTrades({"cA": rows, "cB": rows[:400]})
    run_to_end(tmp_path / "full", full, legs)
    a = FakeTrades({"cA": rows, "cB": rows[:400]})
    calls = {"n": 0}

    def stop_after_two_items():
        calls["n"] += 1
        return calls["n"] > 2

    m1 = fetch(tmp_path / "res", a, legs, should_stop=stop_after_two_items)
    assert m1["status"] == "in_progress" and not m1.get("complete")
    n_first = len(a.log)
    m2 = run_to_end(tmp_path / "res", a, legs)
    assert m2["status"] == xv.XV_COMPLETE
    assert len(a.log) == len(full.log)  # finished pair-days are never requested again
    assert n_first < len(a.log)
    fa, fb = tmp_path / "full" / "creative_batch7" / "xv_prints", tmp_path / "res" / "creative_batch7" / "xv_prints"
    for rel in ("days.csv.gz", "prints/KX-A.csv.gz", "prints/KX-B.csv.gz", "legs.csv.gz"):
        assert gzip.decompress((fa / rel).read_bytes()) == gzip.decompress((fb / rel).read_bytes()), rel
    again = fetch(tmp_path / "res", a, legs)  # terminal state is sticky: no request
    assert again["status"] == xv.XV_COMPLETE and len(a.log) == len(full.log)


def test_fetch_failed_request_is_a_failed_item_not_an_empty_day(tmp_path):
    api = FakeTrades({"cA": day_rows(D1, 10), "cB": day_rows(D1, 10)}, fail_cids={"cB"})
    m = run_to_end(tmp_path, api, [leg("KX-A", "cA"), leg("KX-B", "cB")], limit=12)
    assert m["status"] == xv.XV_COMPLETE and m["days_failed_final"] == 3  # all three days of cB failed finally
    days = rd_gz(tmp_path / "creative_batch7" / "xv_prints" / "days.csv.gz")
    assert {r["status"] for r in days if r["pair_key"] == "KX-B"} == {"failed"} and {r["failed"] for r in days if r["pair_key"] == "KX-B"} == {"1"}
    assert not (tmp_path / "creative_batch7" / "xv_prints" / "prints" / "KX-B.csv.gz").exists()


def test_fetch_cap_drops_rows_after_cap_and_does_not_request_later_days(tmp_path):
    rows = day_rows(D1, 20) + day_rows(D2, 20)
    api = FakeTrades({"cA": rows})
    m = run_to_end(tmp_path, api, [leg()], cap_at="2026-06-02T00:00Z")
    assert m["status"] == xv.XV_COMPLETE
    assert {int(p["start"]) for p in api.log} == {int(WIN_START)}  # only the first day lies before the cap
    stored = rd_gz(tmp_path / "creative_batch7" / "xv_prints" / "prints" / "KX-A.csv.gz")
    assert len(stored) == 20 and max(float(r["ts"]) for r in stored) <= datetime(2026, 6, 2, tzinfo=UTC).timestamp()


def test_fetch_resolves_blank_condition_ids_by_gamma_and_skips_unresolved(tmp_path):
    api = FakeTrades({"cA": day_rows(D1, 5)}, gamma={"mKX-A": "cA"})
    m = run_to_end(tmp_path, api, [leg("KX-A", ""), leg("KX-Z", "")])
    assert m["status"] == xv.XV_COMPLETE and m["legs_without_condition_id"] == 1 and m["counts"]["condition_ids_resolved_by_gamma"] == 1
    assert {p["market"] for p in api.log} == {"cA"}


def test_fetch_refusals_declaration_roots_run_id_and_headroom(tmp_path):
    api = FakeTrades()
    with pytest.raises(cm.Refused, match="day_pages"):
        fetch(tmp_path, api, [leg()], day_pages=9)
    with pytest.raises(cm.Refused, match="refused"):
        xv.xv_prints_fetch(tmp_path / "cross_venue_live", api, legs=[leg()], now=NOW)
    with pytest.raises(cm.Refused, match="writes only"):
        fetch(tmp_path, api, [leg()], run_id="h8_text")
    big = tmp_path / "dd"
    big.mkdir()
    (big / "f").write_bytes(b"x" * 1024)
    with pytest.raises(cm.NotNow, match="headroom"):
        fetch(tmp_path, api, [leg()], data_dumps=big, data_dumps_cap_gb=0.0001, disk_cap=int(0.25 * 1024**3))
    assert api.log == []


def test_fetch_disk_budget_is_declared_end_state(tmp_path):
    api = FakeTrades({"cA": day_rows(D1, 800)})
    m = fetch(tmp_path, api, [leg()], disk_cap=2000)
    assert m["status"] == cm.DISK_BUDGET_TOKEN
    assert fetch(tmp_path, api, [leg()], disk_cap=2000)["status"] == cm.DISK_BUDGET_TOKEN


def test_fetch_is_not_t_seal_bound(tmp_path):
    api = FakeTrades({"cA": day_rows(D1, 5)})
    m = run_to_end(tmp_path, api, [leg()], wall_clock=lambda: datetime(2026, 11, 5, tzinfo=UTC).timestamp(), now=datetime(2026, 11, 5, tzinfo=UTC).timestamp())
    assert m["status"] == xv.XV_COMPLETE


# ---- X definitions --------------------------------------------------------------------------------------------------------------


def candles(spec):
    """spec: list of (end_ts, bid, ask)."""
    return np.array([[t, b, a, np.nan, 1.0] for t, b, a in spec], float)


def test_kalshi_validity_age_and_no_fallback():
    assert xv.valid_mid(0.49, 0.51) == pytest.approx(0.50)
    assert xv.valid_mid(0.40, 0.51) is None  # spread 11c > 10c
    assert xv.valid_mid(0.0, 0.05) is None and xv.valid_mid(0.5, 0.5) is None and xv.valid_mid(0.5, 1.0) is None
    assert xv.valid_mid(0.01, 0.03) is None  # mid 0.02 outside [0.03, 0.97]
    km = xv.KalshiMid(candles([(60, 0.49, 0.51), (120, 0.30, 0.60)]))  # the latest candle is invalid (spread 30c)
    assert km.at(120) is None and km.at(150) is None  # no fall-back to the older valid candle
    assert km.at(100) == pytest.approx(0.50)
    one = xv.KalshiMid(candles([(60, 0.49, 0.51)]))
    assert one.at(60 + 300) == pytest.approx(0.50) and one.at(60 + 301) is None  # age > 5 min is invalid


def step_candles(t0, n=60, lo=(0.49, 0.51), hi=(0.51, 0.53)):
    """minute candles from t0 - 1800 .. t0 + n*60; mid 0.50 before t0, 0.52 from t0."""
    return candles([(t0 + 60 * i, *(lo if t0 + 60 * i < t0 else hi)) for i in range(-30, n)])


def test_move_events_and_skip_windows_merged():
    t0 = 6000.0
    km = xv.KalshiMid(step_candles(t0))
    up, down = xv.move_events(km)
    assert down == [] and up[0] == t0 and up[-1] == t0 + 540  # mid(tau) - mid(tau - 600) = +2c for tau in [t0, t0 + 600)
    assert xv.skip_windows(up) == [(t0 + 120, t0 + 540 + 120 + 1200)]  # merged into one window [tau + 120, tau + 1320)
    assert xv.skip_windows([0.0, 1200.0]) == [(120.0, 2520.0)]  # touching windows join
    assert xv.skip_windows([0.0, 1201.0]) == [(120.0, 1320.0), (1321.0, 2521.0)]
    km2 = xv.KalshiMid(candles([(60 * i, 0.495 - (i >= 20) * 0.02, 0.515 - (i >= 20) * 0.02) for i in range(0, 40)]))
    u2, d2 = xv.move_events(km2)
    assert u2 == [] and d2 and d2[0] == 1200.0  # a -2c step is a down event
    km3 = xv.KalshiMid(candles([(60 * i, 0.495, 0.515) if i < 20 else (60 * i, 0.4995 + 0.0, 0.5195) for i in range(0, 40)]))
    assert xv.move_events(km3) == ([], [])  # +0.4c is below the 1c threshold


def test_in_skip_boundaries():
    taus = [1000.0]
    assert not xv.in_skip(taus, 1119.99) and xv.in_skip(taus, 1120.0) and xv.in_skip(taus, 2319.99) and not xv.in_skip(taus, 2320.0)


def test_classify_prints_sets_sides_exclusions():
    t0 = 6000.0
    km = xv.KalshiMid(step_candles(t0, n=400))
    up, down = xv.move_events(km)
    ps_ts = np.arange(0, 40000, 600.0)
    ps_px = np.full(len(ps_ts), 0.5)
    s_in = t0 + 700  # inside the up window [t0 + 120, t0 + 1860)
    prints = [(s_in, 1), (s_in + 10, -1), (t0 + 50, 1), (t0 + 8000, 1)]
    res = xv.classify_prints(prints, up, down, km, ps_ts, ps_px)
    assert (res["S"], res["Sp"], res["N"], res["n_prints"]) == (1, 1, 2, 4)  # ask-side in up-skip is S; bid-side in up-skip is S'
    assert res["s_ts"] == [s_in] and res["s_window"][0][0] == "up"
    # unusable: polymarket price outside [3%, 97%] at s
    res2 = xv.classify_prints([(s_in, 1)], up, down, km, ps_ts, np.full(len(ps_ts), 0.99))
    assert res2["excluded_unusable"] == 1 and res2["S"] == 0
    # both states: a down event overlapping the up window excludes the print
    res3 = xv.classify_prints([(s_in, 1)], up, [t0 + 500.0], km, ps_ts, ps_px)
    assert res3["excluded_both_states"] == 1 and res3["S"] == 0
    # down-skip: bid-side is S
    res4 = xv.classify_prints([(s_in, -1), (s_in, 1)], [], [t0 + 560.0], km, ps_ts, ps_px)
    assert (res4["S"], res4["Sp"]) == (1, 1) and res4["s_window"][0][0] == "down"


# ---- census: statistics ---------------------------------------------------------------------------------------------------------


def test_icc_cell_demean_and_deff():
    y = [1, 1, 1, 5, 5, 5, 9, 9, 9, 1, 1, 1]
    g = ["a"] * 3 + ["b"] * 3 + ["c"] * 3 + ["d"] * 3
    assert cc.icc_oneway([float(v) for v in y], g) == pytest.approx(1.0)
    assert cc.icc_oneway([1.0, 2.0, 3.0, 4.0], ["a", "b", "c", "d"]) != cc.icc_oneway([1.0, 2.0, 3.0, 4.0], ["a", "b", "c", "d"])  # nan: no within df
    rng = np.random.default_rng(1)
    z = list(rng.normal(size=4000))
    assert cc.icc_oneway(z, [str(i % 400) for i in range(4000)]) < 0.1
    assert cc.cell_demean([1.0, 3.0, 10.0], ["a", "a", "b"]) == [-1.0, 1.0, 0.0]
    d = cc.deff_text_only([float(v) for v in y], {"w1": g, "w2": [str(i) for i in range(12)]})
    assert d["ways"]["w1"]["deff"] == pytest.approx(1 + (3 - 1) * 1.0) and d["deff_s"] is None  # w2 has no within df: an unknown way -> no deff
    d2 = cc.deff_text_only([float(v) for v in y], {"w1": g})
    assert d2["deff_s"] == pytest.approx(3.0)


def test_cell_band_edges():
    assert cc.cell_band(0.05) == "[0.05,0.25)" and cc.cell_band(0.25) == "[0.25,0.50)" and cc.cell_band(0.95) == "[0.75,0.95]" and cc.cell_band(0.951) is None
    assert cc.cell_band(0.0499) is None


def test_assert_counts_only_refuses_forbidden_keys():
    cc.assert_counts_only({"a": {"b": [1, {"c": 2}]}, "eligible_units": 3, "expected_yes_sum_m": 2.5})
    for bad in ({"x": {"outcome_prices": 1}}, {"markout_mean": 1}, {"s": [{"beta": 1}]}, {"yes_rate": 0.1}, {"y": {"log_loss": 1}}):
        with pytest.raises(cm.Refused):
            cc.assert_counts_only(bad)


# ---- census: h_geo ----------------------------------------------------------------------------------------------------------------


def write_capture(snaps: Path, name: str, rows, state="complete"):
    d = snaps / name
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"capture_id": name, "state": state, "started_utc": "x"}))
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["received_utc", "market_id", "best_bid", "best_ask", "closed"])
        for mid, bid, ask, _fee in rows:
            w.writerow(["t", mid, bid, ask, "false"])
    with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["market_id", "fee_category"])
        for mid, _b, _a, fee in rows:
            w.writerow([mid, fee])


def test_h_geo_median_half_spread_filters_and_window(tmp_path):
    snaps = tmp_path / "snapshots"
    after = datetime(2026, 10, 26, tzinfo=UTC).timestamp()
    write_capture(snaps, "20261022T030000Z_aaaa1111", [("g1", 0.04, 0.06, "geopolitics"), ("g2", 0.03, 0.09, "geopolitics"), ("p1", 0.04, 0.06, "politics"),
                                                       ("g3", 0.20, 0.30, "geopolitics"), ("g4", 0.0, 0.05, "geopolitics"), ("g5", 0.06, 0.04, "geopolitics")])
    write_capture(snaps, "20261023T030000Z_bbbb2222", [("g1", 0.04, 0.08, "geopolitics"), ("g1", 0.01, 0.99, "geopolitics")])  # duplicate row for g1: first receipt wins
    write_capture(snaps, "20261024T030000Z_cccc3333", [("g1", 0.01, 0.30, "geopolitics")], state="partial")  # not complete
    write_capture(snaps, "20261021T230000Z_dddd4444", [("g1", 0.01, 0.30, "geopolitics")])  # before the window
    write_capture(snaps, "20261025T000000Z_eeee5555", [("g1", 0.01, 0.30, "geopolitics")])  # at the end (exclusive)
    res = cc.measure_h_geo(snaps, wall_clock=lambda: after)
    assert res["complete_captures"] == 2 and res["observations"] == 3 and res["markets"] == 2
    assert res["median_half_spread_pooled"] == pytest.approx(0.02)  # half-spreads 0.01, 0.03, 0.02
    assert res["median_half_spread_by_market"] == pytest.approx(0.0225)  # g1 -> median(0.01, 0.02) = 0.015, g2 -> 0.03 -> median of the two = 0.0225
    assert res["h_geo_binding"] == pytest.approx(0.0225)  # the larger of the two medians binds
    with pytest.raises(cm.NotNow, match="not closed"):
        cc.measure_h_geo(snaps, wall_clock=lambda: datetime(2026, 10, 24, 12, tzinfo=UTC).timestamp())
    with pytest.raises(cm.Refused):
        cc.measure_h_geo(tmp_path / "elsewhere", wall_clock=lambda: after)
    assert cc.measure_h_geo(snaps, window=("2026-10-30T00:00:00Z", "2026-10-31T00:00:00Z"), wall_clock=lambda: after + 20 * 86400)["status"] == "unavailable"


# ---- census on sealed fixtures --------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sealed(tmp_path_factory):
    w = tf.World(tmp_path_factory.mktemp("cw"))
    w.keys()
    assert w.geo()["status"] == cm.GEO_COMPLETE and w.text()["status"] == cm.TEXT_COMPLETE
    tail_id = tf.rd(w.tdir / "sample.csv.gz")[0]["market_id"]
    tf.write_seal_copy(w.seals / "h8_tail_SEAL.json", [tail_id])
    (w.root / "h8_tail").mkdir(parents=True, exist_ok=True)
    shutil.copy(w.seals / "h8_tail_SEAL.json", w.root / "h8_tail" / "SEAL.json")
    for h in ("h7_cb4_era", "h7_cb4_series"):
        (w.seals / f"{h}_NOT_RUN.json").write_text("{}")
    trials = w.tmp / "seal_trials.jsonl"
    cs.seal_cb7(w.root, cm.GEO_RUN_ID, transport=w.api, seals_dir=w.seals, trials_path=trials, sleep=lambda s: None)
    cs.seal_cb7(w.root, cm.TEXT_RUN_ID, transport=w.api, seals_dir=w.seals, trials_path=trials, sleep=lambda s: None)
    w.tail_id = tail_id
    return w


def census(w, fams, tmp, *, name="census.json", **kw):
    snaps = w.tmp / "snapshots"
    base = dict(root=w.root, seals_dir=w.seals, cb7_dir=tmp / "cb7", cv_root=tmp / "cv", snapshot_root=snaps, rules_path=w.rules, require_committed=False,
                wall_clock=lambda: datetime(2026, 10, 26, tzinfo=UTC).timestamp(), trials_path=tmp / "trials.jsonl", out=tmp / "cb7" / name, pins=w.pins)
    base.update(kw)
    return cc.run_census(fams, **base)


def test_census_sg_counts_only_no_forbidden_files_and_write_once(sealed, tmp_path, monkeypatch):
    w = sealed
    opened: list[str] = []
    real = gzip.open
    monkeypatch.setattr(cc.gzip, "open", lambda p, *a, **k: (opened.append(Path(p).name), real(p, *a, **k))[1])
    res = census(w, ["S", "G"], tmp_path)
    monkeypatch.undo()
    assert not {"outcomes_guarded.csv.gz", "origin_prints.csv.gz"} & set(opened), opened
    assert {"sample.csv.gz", "origin_prices.csv.gz", "drops.csv.gz"} <= set(opened)
    s, g = res["S"], res["G"]
    cc.assert_counts_only(res)
    prices = {r["market_id"]: r for r in tf.rd(w.tdir / "origin_prices.csv.gz")}
    drops = {r["market_id"] for r in tf.rd(w.tdir / "drops.csv.gz")}
    assert w.tail_id in drops
    n_elig = sum(1 for m, r in prices.items() if r["eligible"] == "1" and m not in drops)
    assert s["eligible_units_all_topics"] == n_elig > 0
    assert s["n_sample_after_seal_drops"] == len(tf.rd(w.tdir / "sample.csv.gz")) - len(drops)
    assert s["seal_drops"]["DROPPED_SEALED_RUNS"] == 1
    assert s["gate_GS"]["GS"] is False and s["gate_GS"]["units"]["met"] is False  # a small fixture never meets the floors
    assert s["within_cell_sd_c"]["n_denominator"] is not None and s["within_cell_sd_c"]["n_denominator"] >= 0
    assert (s["text_only_design_effect"]["deff_s"] is None) == (s["s1_mde_per_marker_cents"] is None)  # an unknown deff gives no MDE
    assert s["closed_time"]["eligible_units_closed_before_t7"] >= 0 and s["descriptions_longer_than_4000"]["count"] >= 1
    assert set(s["marker_prevalence"]) == {f"m{i}" for i in range(1, 8)}
    assert g["eligible_units"] > 0 and set(g["eligible_by_origin"]) == {"30", "14", "7"}
    assert g["eligible_units"] == sum(v["eligible_units"] for v in g["eligible_by_origin"].values())
    assert g["expected_yes_sum_m"] == pytest.approx(0.06 * g["eligible_units"], rel=0.05)  # prices only: no outcome
    assert g["tag_only_share"]["frame"]["tagged_markets"] > 0 and g["event_clusters"] >= 1 and g["theme_clusters"] >= 1
    assert g["gate_GG"]["GG"] is False and g["h_geo"]["status"] == "unavailable"
    on_disk = json.loads((tmp_path / "cb7" / "census.json").read_text())
    assert on_disk["S"]["eligible_units_all_topics"] == n_elig
    assert "creative_batch_7:census" in (tmp_path / "trials.jsonl").read_text() and '"cb7_descriptive"' in (tmp_path / "trials.jsonl").read_text()
    with pytest.raises(cm.Refused, match="write-once"):
        census(w, ["S"], tmp_path)
    assert (w.tdir / "ACCESS_LOG.jsonl").read_text().count("q0147_cb7_census") >= 1
    census(w, ["S"], tmp_path, name="again.json")  # the access log does not break the seal check


def test_census_seal_sha_mismatch_refuses_for_each_run(sealed, tmp_path):
    w = sealed
    for run in ("h8_text", "h8_geo", "h8_tail"):
        host = w.root / run / "SEAL.json"
        orig = host.read_bytes()
        host.write_bytes(orig + b" ")
        try:
            with pytest.raises(cm.Refused, match="sha256"):
                census(w, ["S"], tmp_path, name=f"{run}.json")
        finally:
            host.write_bytes(orig)
    assert not list((tmp_path / "cb7").glob("*.json")) if (tmp_path / "cb7").exists() else True


def test_census_refuses_missing_host_seal_unknown_family_and_no_terminal_record(sealed, tmp_path):
    w = sealed
    host = w.root / "h8_tail" / "SEAL.json"
    orig = host.read_bytes()
    host.unlink()
    try:
        with pytest.raises(cm.Refused, match="host copy"):
            census(w, ["S"], tmp_path)
    finally:
        host.write_bytes(orig)
    with pytest.raises(cm.Refused, match="family"):
        census(w, ["Q"], tmp_path)
    committed = w.seals / "h8_geo_SEAL.json"
    keep = committed.read_bytes()
    committed.unlink()
    try:
        with pytest.raises(cm.Refused, match="no committed seal"):
            census(w, ["S"], tmp_path)
        (w.root / "h8_geo" / cm.NOT_RUN_FILE).write_text("{}")  # a recorded not-run terminal state lets the other families proceed
        res = census(w, ["G"], tmp_path, name="notrun.json")
        assert res["G"] == {"status": "not_run"}
    finally:
        committed.write_bytes(keep)
        (w.root / "h8_geo" / cm.NOT_RUN_FILE).unlink(missing_ok=True)


def test_census_g_waits_for_the_h_geo_window(sealed, tmp_path):
    with pytest.raises(cm.NotNow, match="not closed"):
        census(sealed, ["G"], tmp_path, wall_clock=lambda: datetime(2026, 10, 24, tzinfo=UTC).timestamp())
    assert not (tmp_path / "cb7" / "census.json").exists()


# ---- census X on a synthetic study ----------------------------------------------------------------------------------------------


def make_x_world(tmp, *, xv_complete=True):
    t0 = datetime(2026, 6, 2, 12, tzinfo=UTC).timestamp()
    cv = tmp / "cv"
    (cv / "series").mkdir(parents=True)
    kc = step_candles(t0, n=400)
    for key in ("KX-A", "KX-S"):
        ps = np.array([[t, 0.5] for t in np.arange(WIN_START, WIN_END, 600.0)])
        np.savez_compressed(cv / "series" / f"{key}.npz", ps=ps, kc=kc, win=np.array([WIN_START, WIN_END]))
    s_ts = t0 + 700
    pa = [trade(s_ts, side="BUY", idx=0), trade(s_ts + 5, side="SELL", idx=0), trade(t0 + 50, side="BUY"), trade(t0 + 9000, side="BUY"), trade(s_ts + 30, side="SELL", idx=1)]
    legs = [leg("KX-A", "cA", p_event_id="EVA"), leg("KX-S", "cS", p_event_id="EVS", k_cat="Sports")]
    api = FakeTrades({"cA": pa, "cS": pa})
    if xv_complete:
        run_to_end(tmp, api, legs)
    return cv, tmp / "creative_batch7" / "xv_prints"


def test_census_x_counts_sets_clusters_and_sports_split(tmp_path):
    cv, xvd = make_x_world(tmp_path)
    r = cc.census_x(xvd, cv)
    # per pair: S = ask-side in the up window (BUY YES at s, SELL NO at s + 30 is ask-side too) = 2; S' = the bid-side SELL YES = 1; N = 2
    assert r["print_classes"]["nonsports"] == {"n_prints": 5, "excluded_both_states": 0, "excluded_unusable": 0, "S": 2, "Sp": 1, "N": 2}
    assert r["print_classes"]["sports"]["S"] == 2 and r["print_classes"]["all"]["S"] == 4
    assert r["pairs"] == 2 and r["pairs_nonsports"] == 1 and r["capped_days"] == 0 and r["prints_per_pair"]["total"] == 10
    assert r["kalshi_move_events"]["nonsports"]["up"] > 0 and r["kalshi_move_events"]["nonsports"]["down"] == 0
    assert r["s_clusters"]["nonsports"] == {"events": 1, "utc_dates": 1, "skip_windows": 1}
    assert r["gate_GX"]["GX"] is False and r["gate_GX"]["s_prints"]["value"] == 2
    cc.assert_counts_only(r)


def test_census_x_not_now_until_prints_are_complete(tmp_path):
    cv, xvd = make_x_world(tmp_path, xv_complete=False)
    with pytest.raises(cm.NotNow, match="xv_prints"):
        cc.census_x(xvd, cv)
    with pytest.raises(cm.Refused):
        cc.census_x(tmp_path / "cross_venue_live" / "xv_prints", cv)


def test_census_x_reads_only_pair_ts_side_columns(tmp_path, monkeypatch):
    cv, xvd = make_x_world(tmp_path)
    seen_cols: list[tuple[str, ...]] = []
    real = cc.read_cols
    monkeypatch.setattr(cc, "read_cols", lambda p, wanted, **k: (seen_cols.append(tuple(wanted)), real(p, wanted, **k))[1])
    cc.census_x(xvd, cv)
    flat = {c for cols in seen_cols for c in cols}
    assert flat <= {"pair_key", "status", "ts", "side"} and "yes_price" not in flat and "size" not in flat


# ---- runner ----------------------------------------------------------------------------------------------------------------------


def test_runner_xv_prints_refusals_and_status_line(tmp_path, capsys, monkeypatch):
    base = ["xv-prints", "--disk-cap-gb", "0.25", "--standalone", "--out-root", str(tmp_path / "o"), "--data-dumps", str(tmp_path)]
    assert script.main([*base, "--day-pages", "9"]) == 2
    assert script.main([*base, "--set", "C2"]) == 2
    assert script.main([*base, "--cap-at", "2026-10-30T00:00Z"]) == 2
    assert "arguments differ" in capsys.readouterr().out
    legs = tmp_path / "legs.json"
    legs.write_text(json.dumps([leg()]))
    monkeypatch.setattr(hb, "httpx_transport", lambda: FakeTrades({"cA": day_rows(D1, 5)}))
    rc = script.main([*base, "--legs", str(legs), "--budget-min", "5"])
    out = capsys.readouterr().out
    assert rc == 0 and re.search(r"\"status\": \"xv_prints_complete\"", out), out


def test_runner_queue_drafts_q0146_q0147_parse():
    drafts = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / "drafts"
    files = sorted(drafts.glob("q014[67]_*.json"))
    if len(files) < 2:
        pytest.skip("drafts not present")
    ap = script.build_parser()
    for f in files:
        spec = json.loads(f.read_text())
        a = ap.parse_args(spec["argv"][1:])
        if spec["argv"][1] == "xv-prints":
            assert a.set == "C1" and a.day_pages == 10 and a.cap_at == "2026-10-22T00:00Z" and a.rps == 4 and a.disk_cap_gb == 0.25 and a.data_dumps_cap_gb == 40 and a.budget_min == 60
            assert re.search(spec["repeat"]["until_log_regex"], '{"status": "xv_prints_complete"}') and spec["resources"]["lane"] == "net"
        else:
            assert a.family == "S,G,X" and spec["resources"]["lane"] == "cpu"


def test_runner_census_refusals_and_tempfail(sealed, tmp_path, capsys, monkeypatch):
    w = sealed
    common = ["census", "--root", str(w.root), "--seals-dir", str(w.seals), "--data-dumps", str(tmp_path), "--rules", str(w.rules), "--allow-uncommitted-rules",
              "--snapshot-root", str(w.tmp / "snapshots"), "--trials-path", str(tmp_path / "t.jsonl"), "--cv-root", str(tmp_path / "cv")]
    assert script.main([*common, "--family", "Z"]) == 2
    host = w.root / "h8_text" / "SEAL.json"
    orig = host.read_bytes()
    host.write_bytes(orig + b"0")
    try:
        assert script.main([*common, "--family", "S"]) == 2
    finally:
        host.write_bytes(orig)
    assert "sha256" in capsys.readouterr().out
    (w.tmp / "snapshots").mkdir(exist_ok=True)
    import time as _t

    monkeypatch.setattr(_t, "time", lambda: datetime(2026, 10, 24, tzinfo=UTC).timestamp())
    monkeypatch.setattr(cm, "verify_rules", lambda *a, **k: "rules-sha")
    assert script.main([*common, "--family", "G"]) == 75
    assert hashlib.sha256(orig).hexdigest() == hashlib.sha256(host.read_bytes()).hexdigest()
