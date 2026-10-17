# ruff: noqa: E501
"""CB9-K / CB9-D (cb9_kd): frame filters and split, the pmxt row-group reader on a constructed parquet, origin / minute states with the 13Z lookback, the
D next-transaction VWAP (sweep with a dust fill, the u + 1 s start, the 10-minute limit), GK counted after the skew cut, the route gate both ways,
HOLDOUT refusal, the census receiving no target, and an end-to-end frame -> books -> seal -> census -> screen run. Mocked HTTP and in-memory parquet only."""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from astrolabe.research_lab import battery2
from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb9_common as c9
from astrolabe.research_lab import cb9_kd as kd
from astrolabe.research_lab import history_backfill as hb
from tests.unit._cb8_fakes import Api, nosleep, print_row
from tests.unit._cb8_updown_fakes import PmxtFake

NOW = c9.T_SEAL_EPOCH + 3600.0
KEY = b"k" * 64
FP = cm.key_fingerprint(KEY)


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


# ---- fixtures ---------------------------------------------------------------------------------------------------------------------------------------


def gm(mid: int, *, start: str = "2026-05-01T00:00:00Z", end: str = "2026-05-04T00:00:00Z", event: str | None = None, vol: float = 20000.0, q: str | None = None,
       fee: str = "politics_fees", src: str = "https://www.ap.org", aug: bool = False, series: tuple = (), min_size=5, tick="0.01") -> dict:
    return {"id": str(mid), "conditionId": f"0xc{mid}", "clobTokenIds": json.dumps([f"t{mid}a", f"t{mid}b"]), "createdAt": start, "startDate": start, "endDate": end,
            "closed": True, "closedTime": end, "question": q or f"Will candidate {mid} win the vote?", "slug": f"m-{mid}", "feeType": fee, "volumeNum": vol,
            "liquidityNum": 1000.0 + mid, "outcomes": '["Yes","No"]', "outcomePrices": '["1","0"]', "negRisk": False, "negRiskAugmented": aug, "resolutionSource": src,
            "orderMinSize": min_size, "orderPriceMinTickSize": tick,
            "events": [{"id": event or f"E{mid}", "title": f"Event {event or mid}", "series": [{"id": s} for s in series]}]}


def write_keys(d: Path, ids: list[str], events: list[str], disjointness: str = "verified") -> Path:
    d.mkdir(parents=True, exist_ok=True)
    p = d / "exclusion_keys.csv.gz"
    p.write_bytes(hb._gz_csv_bytes(["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"],
                                   [[i, "1", e, "", ""] for i, e in zip(ids, events, strict=True)]))
    from astrolabe.research_lab import h5_seal

    (d / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(p), "disjointness": disjointness}))
    return p


TS = pa.timestamp("ms", "UTC")
COLS = ["timestamp_received", "timestamp", "market", "event_type", "asset_id", "bids", "asks", "price", "size", "side", "new_tick_size", "fee_rate_bps", "transaction_hash"]


def pev(market: str, asset: str, et: str, v_ms: int, r_ms: int | None = None, *, bids=None, asks=None, price=None, size=None, side=None, tick=None, fee=700.0, tx=None) -> dict:
    return {"timestamp_received": v_ms + 5 if r_ms is None else r_ms, "timestamp": v_ms, "market": market, "event_type": et, "asset_id": asset,
            "bids": json.dumps(bids) if bids is not None else None, "asks": json.dumps(asks) if asks is not None else None, "price": price, "size": size, "side": side,
            "new_tick_size": tick, "fee_rate_bps": fee, "transaction_hash": tx}


def parquet_kd(events: list[dict], row_group_size: int = 3) -> bytes:
    events = sorted(events, key=lambda e: e["market"])
    types = {"timestamp_received": TS, "timestamp": TS, "price": pa.float64(), "size": pa.float64(), "fee_rate_bps": pa.float64()}
    cols = {c: pa.array([e[c] for e in events], type=types.get(c, pa.string())) for c in COLS}
    buf = io.BytesIO()
    pq.write_table(pa.table(cols), buf, row_group_size=row_group_size)
    return buf.getvalue()


def ms(day: str, hh: int, mm: int = 0, ss: int = 0) -> int:
    return int(datetime(*datetime.strptime(day, "%Y-%m-%d").timetuple()[:3], hh, mm, ss, tzinfo=UTC).timestamp() * 1000)


def book_events(mid: int, day: str) -> tuple[list[dict], list[dict]]:
    """(13Z events, 14Z events) of one market-day: the 13Z snapshot carries a dust ask (3 shares < orderMinSize 5); 14Z removes it, prints a trade, re-adds dust."""
    c, a, b = f"0xc{mid}", f"t{mid}a", f"t{mid}b"
    e13 = [pev(c, a, "book", ms(day, 13, 30), bids=[["0.40", "100"], ["0.39", "50"]], asks=[["0.45", "3"], ["0.46", "80"]]),
           pev(c, b, "book", ms(day, 13, 30), bids=[["0.54", "80"], ["0.55", "3"]], asks=[["0.60", "100"], ["0.61", "50"]])]
    e14 = [pev(c, a, "price_change", ms(day, 14, 10), price=0.45, size=0.0, side="SELL"),
           pev(c, a, "last_trade_price", ms(day, 14, 15), price=0.46, size=10.0, side="BUY", tx=f"0xltp{mid}"),
           pev(c, a, "price_change", ms(day, 14, 30), price=0.44, size=2.0, side="SELL"),
           pev(c, b, "price_change", ms(day, 14, 30), price=0.56, size=2.0, side="BUY")]
    return e13, e14


def prints_for(mid: int, day: str) -> list[dict]:
    t = int(kd.origin_epoch(day))
    cid = f"0xc{mid}"
    return [print_row(cid, t - 3 * 3600, side="BUY", price=0.42, size=10.0), print_row(cid, t - 2 * 3600, side="SELL", price=0.41, size=20.0),
            print_row(cid, t - 3600, idx=1, side="BUY", price=0.57, size=5.0),
            print_row(cid, t + 600, side="SELL", price=0.40, size=200.0), print_row(cid, t + 900, side="BUY", price=0.47, size=200.0),
            print_row(cid, t + 31 * 60, side="BUY", price=0.46, size=10.0, tx="0xsweep" + str(mid) + day),
            print_row(cid, t + int(5.5 * 3600), side="BUY", price=0.50, size=5.0), print_row(cid, t + 6 * 3600, side="SELL", price=0.48, size=5.0),
            print_row(cid, t + 8 * 3600, side="BUY", price=0.99, size=5.0)]  # outside the window: never fetched


# ---- constants, frame, split --------------------------------------------------------------------------------------------------------------------------


def test_x6_scaling_pinned_to_hb2_and_rules_doc_builds():
    assert kd.X6_SD == battery2.X6_SD and kd.X6_CLIP == battery2.X6_CLIP
    d = c9.rules_doc("kd")
    assert d["rules_version"] == "cb9-kd-rules-v1" and d["declared"]["split"]["seed"] == "arepo-cb9-kd-split"
    assert "kd_state" in " ".join(d["func_sources_sha256"]) and "cb8_common.hash_wallet" not in d["declared"]["frame"]["stored_fields"]
    assert "outcome_prices" not in kd.FRAME_COLUMNS and "outcomePrices" not in kd.FRAME_COLUMNS


def test_window_days_skip_pmxt_gap_and_market_days_need_the_mark_inside_life():
    days = kd.window_days()
    assert days[0] == "2026-04-13" and days[-1] == "2026-08-09" and "2026-06-12" not in days and "2026-06-17" not in days and "2026-06-18" in days
    r = kd.kd_row(gm(1, start="2026-05-01T14:00:00Z", end="2026-05-03T21:00:00Z"))
    assert kd.market_days(r) == ["2026-05-01", "2026-05-02", "2026-05-03"]
    r2 = kd.kd_row(gm(2, start="2026-05-01T14:00:01Z", end="2026-05-03T20:59:59Z"))
    assert kd.market_days(r2) == ["2026-05-02"]


def test_frame_filters_and_no_outcome_fields():
    rows = {k: kd.kd_row(m) for k, m in {
        "ok": gm(1), "short": gm(2, end="2026-05-03T00:00:00Z"), "vol": gm(3, vol=9999.0), "aug": gm(4, aug=True), "weather": gm(5, fee="weather_fees"),
        "updown": gm(6, q="Bitcoin Up or Down on May 2?"), "pyth": gm(7, src="https://pythdata.app/explore/NVDA"), "late": gm(8, start="2026-08-08T00:00:00Z", end="2026-09-01T00:00:00Z")}.items()}
    reasons = {k: kd.frame_reason(r) for k, r in rows.items()}
    assert reasons == {"ok": None, "short": "overlap_below_min", "vol": "volume_below_min", "aug": "neg_risk_augmented", "weather": "weather", "updown": "crypto_updown",
                       "pyth": "pyth", "late": "overlap_below_min"}
    assert rows["ok"]["order_min_size"] == 5.0 and rows["ok"]["tick_size"] == 0.01 and "outcome_prices" not in rows["ok"]


def test_assemble_drops_caps_per_event_and_split_is_deterministic_by_event():
    frame = [kd.kd_row(gm(i, event="BIG")) for i in range(1, 6)] + [kd.kd_row(gm(i)) for i in range(10, 30)]
    frame.append(kd.kd_row(gm(99)))
    frame.append(kd.kd_row(gm(98, event="EX")))
    s1, rep = kd.assemble_kd(frame, {"99"}, {"event": {"EX"}, "neg_risk_market": set(), "series": set()}, n=1000)
    s2, _ = kd.assemble_kd(list(reversed(frame)), {"99"}, {"event": {"EX"}, "neg_risk_market": set(), "series": set()}, n=1000)
    assert [r["market_id"] for r in s1] == [r["market_id"] for r in s2] and [r["split"] for r in s1] == [r["split"] for r in s2]
    assert rep["drops"] == {"kept": 25, "id": 1, "key": 1} and rep["capped_out_per_event"] == 2
    assert sum(1 for r in s1 if r["event_key"] == "BIG") == 3
    assert len({r["split"] for r in s1 if r["event_key"] == "BIG"}) == 1  # the split unit is the event
    for r in s1:
        h = int(__import__("hashlib").sha256(f"arepo-cb9-kd-split|{r['event_key']}".encode()).hexdigest(), 16) % 2
        assert r["split"] == ("holdout" if h else "screen")
    assert {r["split"] for r in s1} == {"screen", "holdout"}


def test_sports_stratum_capped_at_15_percent():
    rows = [kd.kd_row(gm(i, fee="sports_fees", q=f"Team {i} vs Team X")) for i in range(1, 61)] + [kd.kd_row(gm(i)) for i in range(100, 140)]
    sample, rep = kd.kd_sample(rows, n=40)
    n_sp = sum(1 for r in sample if r["group"] == "sports")
    assert n_sp == 6 and rep["n_sports"] == 6 and len(sample) == 40  # 60% of the pool, capped at floor(0.15 x 40)


# ---- pmxt reader and states ---------------------------------------------------------------------------------------------------------------------


def test_reader_on_tiny_parquet_prunes_row_groups_keeps_tx_and_applies_both_clocks():
    day = "2026-05-01"
    t0 = ms(day, 14)
    evs = [pev("0xa", "TA", "book", t0 + 1000, bids=[["0.1", "10"]], asks=[["0.2", "10"]]),
           pev("0xa", "TA", "last_trade_price", t0 + 2000, price=0.2, size=5.0, side="BUY", tx="0xdeadbeef"),
           pev("0xa", "TA", "price_change", t0 + 3000, r_ms=t0 + 3600 * 1000 + 1, price=0.2, size=0.0, side="SELL"),  # received after the cut
           pev("0xb", "TB", "book", t0 + 1000, bids=[["0.5", "10"]], asks=[["0.6", "10"]]),
           pev("0xz", "TZ", "book", t0 + 1000, bids=[["0.5", "10"]], asks=[["0.6", "10"]]),
           pev("0xz", "TZ", "book", t0 + 2000, bids=[["0.5", "10"]], asks=[["0.6", "10"]]),
           pev("0xz", "TZ", "book", t0 + 3000, bids=[["0.5", "10"]], asks=[["0.6", "10"]])]
    pm = PmxtFake()
    pm.files[f"{day}T14"] = parquet_kd(evs, row_group_size=3)
    ev, info = kd.read_events_kd(datetime(2026, 5, 1, 14, tzinfo=UTC), {"TA": "0xa"}, fetch=pm.fetch, size_fn=pm.size_fn, cut_ms=t0 + 3600 * 1000)
    assert [e["et"] for e in ev["TA"]] == ["book", "last_trade_price"] and ev["TA"][1]["tx"] == "0xdeadbeef"
    assert info["row_groups_total"] == 3 and info["row_groups_read"] == 1 and info["bytes"] > 0
    with pytest.raises(Exception) as ex:
        kd.read_events_kd(datetime(2026, 5, 1, 15, tzinfo=UTC), {"TA": "0xa"}, fetch=pm.fetch, size_fn=pm.size_fn, cut_ms=t0)
    assert type(ex.value).__name__ == "HourMissing"


def test_state_fresh_3600_cut_levels_usd_variant_and_crossed():
    t = ms("2026-05-01", 14)
    book = {"et": "book", "v": t - 3600 * 1000, "r": t - 3600 * 1000, "bids": json.dumps([["0.15", "6"], ["0.14", "100"]]), "asks": json.dumps([["0.20", "4"], ["0.21", "50"]]),
            "price": None, "size": None, "side": None, "tick": None, "fee": 700.0}
    s = kd.kd_state([book], t, min_size=5.0)
    assert s["fresh"] and s["best_bid"] == 0.15 and s["ask_size"] == 4.0 and s["cut_ask"] == 0.21 and s["cut_bid"] == 0.15
    assert s["cut_bid_usd"] == 0.14 and s["cut_ask_usd"] == 0.21  # 6 x 0.15 = 0.90 < $1: the variant skips it
    stale = kd.kd_state([{**book, "v": t - 3600 * 1000 - 1, "r": t - 3600 * 1000 - 1}], t, min_size=5.0)
    assert not stale["fresh"] and stale["has_book"]
    late = kd.kd_state([{**book, "r": t + 1}], t)
    assert not late["has_book"] and late["book_status"] == "no_events"
    pc = {"et": "price_change", "v": t - 10, "r": t - 5, "price": 0.22, "size": 10.0, "side": "BUY", "bids": None, "asks": None, "tick": None, "fee": None}
    cr = kd.kd_state([book, pc], t)
    assert cr["crossed"] and cr["best_bid"] == 0.22  # reported, never repaired
    tk = {"et": "tick_size_change", "v": t - 20, "r": t - 20, "tick": "0.001", "bids": None, "asks": None, "price": None, "size": None, "side": None, "fee": None}
    assert kd.kd_state([book, tk], t)["tick"] == "0.001"


def test_day_books_lookback_states_minutes_ltp_and_source_unavailable():
    day = "2026-05-01"
    e13, e14 = book_events(1, day)
    pm = PmxtFake()
    pm.files[f"{day}T13"] = parquet_kd(e13)
    pm.files[f"{day}T14"] = parquet_kd(e14)
    mk1 = {**kd.kd_row(gm(1)), "market_id": "1"}
    mk2 = {**kd.kd_row(gm(2)), "market_id": "2"}  # no event in either hour: source unavailable
    o, mi, lt, minfo, hinfo = kd.day_books(day, [mk1, mk2], fetch=pm.fetch, size_fn=pm.size_fn)
    assert hinfo["lookback_status"] == "read" and hinfo["lookback_tokens"] == 4
    o1 = {r[2]: r for r in o if r[0] == "1"}
    col = {c: i for i, c in enumerate(kd.ORIGIN_COLUMNS)}
    assert o1[0][col["best_ask"]] == 0.45 and o1[0][col["ask_size"]] == 3.0 and o1[0][col["fresh"]] == 1 and o1[0][col["lookback"]] == "read"
    mc = {c: i for i, c in enumerate(kd.MINUTE_COLUMNS)}
    m0 = {r[mc["minute"]]: r for r in mi if r[0] == "1" and r[2] == 0}
    assert len(m0) == 60 and m0[5][mc["best_ask"]] == 0.45 and m0[5][mc["cut_ask"]] == 0.46
    assert m0[15][mc["best_ask"]] == 0.46  # the dust level was removed at 14:10
    assert m0[31][mc["best_ask"]] == 0.44 and m0[31][mc["ask_size"]] == 2.0 and m0[31][mc["cut_ask"]] == 0.46
    assert lt == [["1", day, 0, "t1a", ms(day, 14, 15), ms(day, 14, 15) + 5, 0.46, 10.0, "BUY", "0xltp1"]]
    assert minfo["1"]["books_status"] == "ok" and minfo["1"]["n_events_span"] == 4 and minfo["2"]["books_status"] == "source_unavailable"


# ---- K pieces -----------------------------------------------------------------------------------------------------------------------------------


def test_quote_prices_skew_and_depth():
    assert kd.quote_prices(0.40, 0.45, 0.01, 0) == (0.40, 0.45)
    assert kd.quote_prices(0.40, 0.45, 0.01, 1) == (0.41, 0.46)
    assert kd.quote_prices(0.40, 0.45, 0.01, -1) == (0.39, 0.44)
    assert kd.quote_prices(0.40, 0.41, 0.01, 1) == (0.40, 0.42)  # an improving bid that would touch the ask stays at the touch
    assert kd.quote_prices(0.40, 0.41, 0.01, -1) == (0.39, 0.41)
    assert kd.quote_prices(0.97, 0.99, 0.01, 1) == (0.98, 0.99)  # the ask stays <= 1 - tick
    assert kd.level_depth([[0.40, 100.0], [0.39, 50.0]], 0.41, "bid") == 0.0 and kd.level_depth([[0.40, 100.0]], 0.40, "bid") == 100.0
    full = [[round(0.40 - 0.01 * i, 2), 10.0] for i in range(10)]
    assert kd.level_depth(full, 0.20, "bid") == math.inf


def _arr(rows):
    return kd._print_arrays([{"ts": r[0], "idx": r[1], "price": r[2], "size": r[3], "yes_price": r[2] if r[1] == 0 else 1 - r[2], "yes_side": r[4], "tx": r[5], "api_rank": r[6]}
                             for r in rows])


def test_fill_rules_queue_through_and_mark():
    t = 1_000_000.0
    a = _arr([(t, 0, 0.40, 500.0, -1, "x0", 9), (t + 10, 0, 0.40, 120.0, -1, "x1", 8), (t + 20, 0, 0.39, 40.0, -1, "x2", 7), (t + 5 * 3600, 0, 0.50, 1.0, 1, "x3", 6),
              (t + 6 * 3600, 0, 0.46, 1.0, -1, "x4", 5)])
    assert kd._fill(a, t, "bid", 0.40, 100.0) is True  # at or through after t: 120 + 40 = 160 >= depth 100 + own 50
    assert kd._fill(a, t, "bid", 0.40, 200.0) is False  # the 500 shares exactly at t are not in the window: 160 < 250
    assert kd._fill(a, t, "bid", 0.40, 100.0, t_from=t + 15) is False  # latency: only the 40 shares after t + 15
    assert kd._fill(a, t, "bid", 0.40, 0.0, rule="through") is False  # only 40 shares strictly through
    assert kd._fill(_arr([(t + 1, 0, 0.30, 60.0, -1, "y", 0)]), t, "bid", 0.40, 0.0, rule="through") is True
    assert kd.mark_value(a, t) == pytest.approx(0.48)
    assert math.isnan(kd.mark_value(_arr([(t + 5 * 3600, 0, 0.5, 1.0, 1, "z", 0)]), t))  # both sides required


def test_route_gate_both_ways():
    # origin A: one fill at +2c (net +1c per posted share); origin B: two fills at -1.5c (net -1.5c); origin C: no fill (net 0)
    mS, fS, net = np.array([2.0, -1.5, 0.0]), np.array([True, True, False]), np.array([1.0, -1.5, 0.0])
    g = kd.route_gate(mS, fS, net)
    assert g["skewed_per_filled_share_c"] == pytest.approx(0.25) and g["skewed_net_per_origin_c"] < 0 and g["pass"] is False  # wins per fill, loses per origin
    g2 = kd.route_gate(np.array([2.0, -0.5, 0.0]), fS, np.array([2.0, -0.5, 0.0]) / 2)
    assert g2["pass"] is True
    g3 = kd.route_gate(np.array([-1.0, 0.5, 0.0]), fS, np.array([1.0, 1.0, 0.0]))
    assert g3["pass"] is False  # per origin positive but per filled share not


def test_contrast_delta_method_mean_equals_estimate():
    mS, fS = np.array([1.0, 3.0, 0.0, 0.0]), np.array([True, True, False, False])
    mU, fU = np.array([0.0, 1.0, 2.0, 0.0]), np.array([False, True, True, False])
    est, v = kd.contrast(mS, fS, mU, fU)
    assert est == pytest.approx(2.0 - 1.5) and v.mean() == pytest.approx(est)


def _unit(i: int, x6: float, *, cell: bool = True, filled: bool = True, mark: bool = True, event: str | None = None) -> dict:
    t = kd.origin_epoch("2026-05-01") + 86400 * (i % 30)
    post = []
    if filled:
        post += [{"ts": t + 60, "idx": 0, "price": 0.30, "size": 500.0, "yes_price": 0.30, "yes_side": -1, "tx": f"a{i}", "api_rank": 3}]
    if mark:
        post += [{"ts": t + 5.5 * 3600, "idx": 0, "price": 0.5, "size": 1.0, "yes_price": 0.5, "yes_side": 1, "tx": f"b{i}", "api_rank": 2},
                 {"ts": t + 6 * 3600, "idx": 0, "price": 0.5, "size": 1.0, "yes_price": 0.5, "yes_side": -1, "tx": f"c{i}", "api_rank": 1}]
    o = {"best_bid": "0.40", "best_ask": "0.45", "tick": "0.01", "bids_top": "[[0.4,100.0]]", "asks_top": "[[0.45,100.0]]", "fee_bps": "0"}
    return {"market_id": str(i), "day": f"d{i}", "month": "2026-05", "event": event or f"E{i}", "t": t, "origin": o, "prints_ok": True, "post": kd.CountOnlyPosts(post),
            "_feat": {"eligible": True, "x6": x6, "rv": 1.0 if cell else -9.0, "spr": 0.05}, "fee_category": "politics", "minutes": [], "min_size": 5.0}


def test_gk_is_counted_after_the_skew_cut(monkeypatch):
    monkeypatch.setitem(kd.GK, "cell_origins", 3)
    monkeypatch.setitem(kd.GK, "filled_origins_per_type", 1)
    monkeypatch.setitem(kd.GK, "events", 1)
    monkeypatch.setitem(kd.GK, "days", 1)
    units = [_unit(1, 0.9), _unit(2, -0.8), _unit(3, 0.1), _unit(4, -0.05), _unit(5, 0.9, cell=False)]
    cuts = {"rv": 0.0, "spr": 1.0, "x6_abs": 0.5}
    n = kd.k_census_counts(units, cuts)
    assert n["cell"] == 4 and n["after_cut"] == 2 and n["no_skew_excluded"] == 2
    assert n["gate_gk"]["cell_origins"] is False and n["gate_gk"]["pass"] is False  # 4 cell origins before the cut would have passed (>= 3)
    n2 = kd.k_census_counts(units + [_unit(6, 0.7)], cuts)
    assert n2["after_cut_mark_available"] == 3 and n2["gate_gk"]["pass"] is True
    n3 = kd.k_census_counts([_unit(7, 0.9, mark=False), _unit(8, 0.9), _unit(9, -0.9)], cuts)
    assert n3["after_cut"] == 3 and n3["after_cut_mark_available"] == 2 and n3["gate_gk"]["pass"] is False  # GK counts the units entering K1 (with a mark)


def test_k_cuts_from_features_only():
    feats = [{"eligible": True, "x6": x, "rv": r, "spr": s} for x, r, s in ((0.1, 1.0, 0.01), (-0.5, 2.0, 0.02), (0.9, 3.0, 0.03), (0.2, math.nan, 0.10))] + [
        {"eligible": False, "x6": 5.0, "rv": 99.0, "spr": 9.0}]
    c = kd.k_cuts(feats)
    assert c["rv"] == pytest.approx(np.quantile([1.0, 2.0, 3.0], 2 / 3)) and c["spr"] == pytest.approx(np.quantile([0.01, 0.02, 0.03, 0.10], 2 / 3))
    cell = [f for f in feats if kd.in_cell(f, c)]
    assert c["x6_abs"] == pytest.approx(np.median([abs(f["x6"]) for f in cell]))


# ---- D pieces -----------------------------------------------------------------------------------------------------------------------------------


def test_next_tx_vwap_over_a_sweep_with_a_dust_fill_u_plus_1_and_10_minutes():
    u = 2_000_000.0
    a = _arr([(u, 0, 0.30, 50.0, 1, "0xatu", 9),  # at u itself: excluded (the u + 1 s start)
              (u + 1, 0, 0.44, 2.0, 1, "0xsweep", 8), (u + 1, 0, 0.46, 10.0, 1, "0xsweep", 7), (u + 1, 0, 0.47, 8.0, 1, "0xsweep", 6),  # sweep incl. a 2-share dust fill
              (u + 1, 1, 0.50, 99.0, -1, "0xsweep", 5),  # the same transaction on the other token: not on this token
              (u + 30, 0, 0.10, 100.0, -1, "0xlater", 4)])
    nt = kd.next_tx(a, u)
    assert nt["tx"] == "0xsweep" and nt["n_prints"] == 3 and nt["size"] == 20.0
    assert nt["vwap"] == pytest.approx((0.44 * 2 + 0.46 * 10 + 0.47 * 8) / 20.0) and nt["last"] == 0.47  # newest in API order = lowest rank
    assert kd.next_tx(_arr([(u + 600, 0, 0.4, 1.0, 1, "0xedge", 0)]), u)["tx"] == "0xedge"
    assert kd.next_tx(_arr([(u + 601, 0, 0.4, 1.0, 1, "0xlate", 0)]), u) is None  # 10-minute limit
    # the dust unit statistic uses P (VWAP), never the side
    flipped = _arr([(u + 1, 0, 0.44, 2.0, -1, "0xs", 2), (u + 1, 0, 0.46, 10.0, 1, "0xs", 1)])
    assert kd.next_tx(flipped, u)["vwap"] == pytest.approx((0.44 * 2 + 0.46 * 10) / 12)


def _minute(k: int, *, bs=100.0, asz=3.0, bb=0.40, ba=0.45, cb=0.40, ca=0.46, ok=True) -> dict:
    return {"minute": str(k), "u_ms": str(1_000_000_000 + k * 60000), "has_book": "1" if ok else "0", "fresh": "1", "crossed": "0", "best_bid": str(bb), "best_ask": str(ba),
            "bid_size": str(bs), "ask_size": str(asz), "cut_bid": str(cb), "cut_ask": str(ca), "cut_bid_usd": str(cb), "cut_ask_usd": str(ca)}


def test_dust_units_one_per_episode_per_five_minutes_and_share_rule():
    mins = [_minute(k) for k in range(1, 13)] + [_minute(13, asz=50.0)] + [_minute(14)]
    du, c = kd.dust_units({"min_size": 5.0, "minutes": mins})
    assert [x["minute"] for x in du] == [1, 6, 11, 14] and c["dust_minutes"] == 13 and c["two_sided_minutes"] == 14
    assert du[0]["m_d"] == pytest.approx(0.425) and du[0]["m_c"] == pytest.approx(0.43)
    _, c2 = kd.dust_units({"min_size": math.nan, "minutes": mins})
    assert c2["min_size_missing"] == 1  # a market without orderMinSize is unavailable, counted
    low = [_minute(1, bs=6.0, asz=6.0, bb=0.10, ba=0.12)]  # 6 shares x 0.10 < $1: dust only under the share-or-$1 variant
    assert kd.dust_units({"min_size": 5.0, "minutes": low})[1]["dust_minutes"] == 0 and kd.dust_units({"min_size": 5.0, "minutes": low}, usd=True)[1]["dust_minutes"] == 1


# ---- guards ---------------------------------------------------------------------------------------------------------------------------------------


def test_holdout_refusal_outside_rep_and_guarded_files_only_in_screen_rep(tmp_path):
    for job in ("screen", "census", "books"):
        with pytest.raises(c9.Refused):
            kd._guard_split("holdout", job)
        with pytest.raises(c9.Refused):
            kd.load_units(tmp_path, "holdout", job=job)
    kd._guard_split("holdout", "rep")
    with pytest.raises(c9.Refused):
        kd._guard_post("census")
    kd._guard_post("screen")
    with pytest.raises(c9.Refused):
        kd.stage1_recorded(tmp_path / "missing.json", tmp_path / "trials.jsonl")
    (tmp_path / "r.json").write_text(json.dumps({"results_sha256": "abc", "K1": {"advance": False}, "D1": {"advance": False}}))
    with pytest.raises(c9.Refused, match="HOLDOUT stays sealed"):
        kd.stage1_recorded(tmp_path / "r.json", tmp_path / "trials.jsonl")
    (tmp_path / "r2.json").write_text(json.dumps({"results_sha256": "abc", "K1": {"advance": True}, "D1": {"advance": False}}))
    with pytest.raises(c9.Refused, match="no trials line"):
        kd.stage1_recorded(tmp_path / "r2.json", tmp_path / "trials.jsonl")
    (tmp_path / "trials.jsonl").write_text(json.dumps({"kind": "cb9_test", "hypothesis": "K1", "results_sha256": "abc", "advance": True}) + "\n")
    assert kd.stage1_recorded(tmp_path / "r2.json", tmp_path / "trials.jsonl") == {"K1": True, "D1": False}


def test_count_only_posts_exposes_no_prices():
    t = 1_000_000.0
    c = kd.CountOnlyPosts([{"ts": t + 60, "idx": 0, "price": 0.3, "size": 500.0, "yes_price": 0.3, "yes_side": -1, "tx": "a", "api_rank": 0}])
    assert isinstance(c.quote_filled(t, "bid", 0.40, 0.0), bool) and isinstance(c.mark_available(t), bool) and isinstance(c.next_tx_exists(t), bool)
    assert isinstance(c.n_between(t, t + 3600), int)
    assert not hasattr(c, "__dict__") and [m for m in dir(c) if not m.startswith("_")] == ["mark_available", "n_between", "next_tx_exists", "quote_filled"]


# ---- end to end: frame -> books -> seal -> census -> screen ---------------------------------------------------------------------------------------------


@pytest.fixture()
def run(tmp_path):
    api = Api()
    mids = list(range(1, 9))
    for i in mids:
        api.gamma[str(i)] = gm(i)
    api.gamma["50"] = gm(50, fee="weather_fees")
    api.gamma["51"] = gm(51, q="Ethereum Up or Down on May 2?")
    api.gamma["52"] = gm(52, src="https://pythdata.app/x")
    api.gamma["53"] = gm(53)  # excluded by id
    keys = write_keys(tmp_path / "keys", ["53"], [""])
    root = tmp_path / "creative_batch9"
    days = ["2026-05-01", "2026-05-02", "2026-05-03"]
    pm = PmxtFake()
    for d in days:
        e13, e14 = [], []
        for i in mids:
            a, b = book_events(i, d)
            e13 += a
            e14 += b
            api.trades.setdefault(f"0xc{i}", []).extend(prints_for(i, d))
        pm.files[f"{d}T13"] = parquet_kd(e13, row_group_size=4)
        pm.files[f"{d}T14"] = parquet_kd(e14, row_group_size=4)
    return {"api": api, "keys": keys, "root": root, "pm": pm, "seals": tmp_path / "seals", "days": days, "mids": mids}


def _frame_books_seal(run):
    m = kd.kd_frame(run["root"], run["api"], rules_sha="r" * 64, exclusion_keys_path=run["keys"], now=NOW, sleep=nosleep)
    assert m["status"] == kd.FRAME_COMPLETE, m
    b = kd.kd_books(run["root"], run["api"], rules_sha="r" * 64, key=KEY, fp=FP, fetch=run["pm"].fetch, size_fn=run["pm"].size_fn, now=NOW, sleep=nosleep)
    assert b["status"] == kd.BOOKS_COMPLETE, b
    s = kd.kd_seal(run["root"], rules_sha="r" * 64, seals_dir=run["seals"])
    assert s["status"] == kd.SEAL_STATUS
    return m, b, s


def test_refuses_before_t_seal_and_on_refused_root(run, tmp_path):
    with pytest.raises(c9.Refused, match="T_seal"):
        kd.kd_frame(run["root"], run["api"], rules_sha="r", exclusion_keys_path=run["keys"], now=c9.T_SEAL_EPOCH - 1, sleep=nosleep)
    with pytest.raises(c9.Refused):
        kd.kd_frame(tmp_path / "creative_batch8", run["api"], rules_sha="r", exclusion_keys_path=run["keys"], now=NOW, sleep=nosleep)
    with pytest.raises(c9.Refused):
        kd.kd_books(run["root"], run["api"], rules_sha="r", key=KEY, fp=FP, fetch=run["pm"].fetch, size_fn=run["pm"].size_fn, now=NOW, sleep=nosleep)  # no frame yet


def test_end_to_end_frame_books_seal_census_screen(run, monkeypatch):
    _frame_books_seal(run)
    root = run["root"]
    sample = kd.read_sample(root / kd.FRAME_RUN)
    assert sorted(int(r["market_id"]) for r in sample) == run["mids"]  # weather, updown, Pyth and the excluded id are gone
    split = {r["market_id"]: r["split"] for r in sample}
    assert set(split.values()) == {"screen", "holdout"}
    rdir = root / kd.BOOKS_RUN
    for sp in ("screen", "holdout"):
        rows = list(csv.DictReader(io.TextIOWrapper(gzip.open(rdir / sp / f"2026-05-01{kd.PRINTS_PRE_SUFFIX}"), encoding="utf-8")))
        assert rows and {split[r["market_id"]] for r in rows} == {sp}
        assert all(int(r["ts"]) < kd.origin_epoch("2026-05-01") for r in rows) and all(len(r["wallet_hash"]) == 32 and "RAW" not in r["wallet_hash"] for r in rows)
        post = list(csv.DictReader(io.TextIOWrapper(gzip.open(rdir / sp / f"2026-05-01{kd.PRINTS_POST_SUFFIX}"), encoding="utf-8")))
        assert post and all(int(r["ts"]) >= kd.origin_epoch("2026-05-01") for r in post) and not any(float(r["price"]) == 0.99 for r in post)
    seal = json.loads((rdir / kd.SEAL_NAME).read_text())
    assert (run["seals"] / kd.SEAL_COPY_NAME).read_bytes() == (rdir / kd.SEAL_NAME).read_bytes()
    assert all(k.startswith("holdout/") for k in seal["files"]) and seal["drops"]["disjointness"] == "verified"
    kd.verify_holdout_seal(rdir, run["seals"])
    # the census never computes a mark-out, a contrast or a next-transaction price
    for name in ("quote_result", "_quote_result", "k1_stat", "contrast", "_d_rows", "d1_stat", "k1_analysis", "d1_analysis"):
        monkeypatch.setattr(kd, name, lambda *a, _n=name, **k: (_ for _ in ()).throw(AssertionError(f"census called {_n}")))
    census = kd.kd_census_doc(root)
    monkeypatch.undo()
    flat = json.dumps(census)
    for bad in ("mo_c", "markout", "vwap", "net_c", "effect", "\"P\"", "mark_value"):
        assert bad not in flat
    assert census["counts_only"] and census["split"]["holdout"]["markets"] == sum(1 for v in split.values() if v == "holdout")
    assert census["audit"]["pass"] is True and census["audit"]["n_pairs"] > 0
    assert census["d"]["dust_minutes"] > 0 and census["k"]["cuts"]["spr_top_tercile"] == pytest.approx(0.05)
    assert census["k"]["label"] == "no opportunity: too few cell fills" and census["d"]["label"] == "no opportunity: dust is rare, no correction needed"
    # the screen opens only screen/ (an access to holdout/ would be logged)
    doc = kd.screen_kd_doc(root, {"kd": census}, n_draws=2)
    assert doc["K1"]["testable"] is False and doc["K1"]["p"] == 1.0 and doc["D1"]["verdict"].startswith("no opportunity")
    assert not (rdir / kd.ACCESS_LOG).read_text().strip()
    # with the gates forced open, the analysis runs end to end on SCREEN (tiny data: not testable for clusters, never an advance)
    open_census = json.loads(json.dumps(census))
    open_census["k"]["label"] = None
    open_census["d"]["label"] = None
    doc2 = kd.screen_kd_doc(root, {"kd": open_census}, n_draws=2)
    assert doc2["D1"]["n_units"] > 0 and doc2["D1"]["advance"] is False and doc2["K1"]["advance"] is False
    with pytest.raises(c9.Refused, match="cut points"):
        bad = json.loads(json.dumps(census))
        bad["k"]["cuts"]["spr_top_tercile"] = 0.5
        kd.screen_kd_doc(root, {"kd": bad}, n_draws=2)


def test_rep_opens_holdout_only_with_a_verified_seal(run):
    _frame_books_seal(run)
    root = run["root"]
    census = kd.kd_census_doc(root)
    with pytest.raises(c9.Refused, match="stage2-k"):
        kd.rep_kd_doc(root, {"kd": census}, {"K1": True}, stage2_k=0, seals_dir=run["seals"])
    out = kd.rep_kd_doc(root, {"kd": census}, {"D1": True}, stage2_k=2, seals_dir=run["seals"], n_draws=2)
    assert out["alpha"] == pytest.approx(0.025) and "D1_rep" in out and "K1_rep" not in out
    log = (root / kd.BOOKS_RUN / kd.ACCESS_LOG).read_text().strip().splitlines()
    assert log and json.loads(log[-1])["job"] == "rep"
    # a changed HOLDOUT file breaks the seal
    f = next((root / kd.BOOKS_RUN / "holdout").glob("*.ltp.csv.gz"))
    f.write_bytes(f.read_bytes() + b"x")
    with pytest.raises(c9.Refused, match="listing"):
        kd.rep_kd_doc(root, {"kd": census}, {"D1": True}, stage2_k=1, seals_dir=run["seals"])


def test_books_ingress_cap_truncates_days_and_is_counted(run):
    kd.kd_frame(run["root"], run["api"], rules_sha="r", exclusion_keys_path=run["keys"], now=NOW, sleep=nosleep)
    b = kd.kd_books(run["root"], run["api"], rules_sha="r", key=KEY, fp=FP, fetch=run["pm"].fetch, size_fn=run["pm"].size_fn, now=NOW, sleep=nosleep,
                    ingress_cap_gb=1e-12)
    assert b["status"] == kd.INGRESS_CAP_STATUS and b["complete"] is True
    rows = list(csv.DictReader(io.TextIOWrapper(gzip.open(run["root"] / kd.BOOKS_RUN / "days.csv.gz"), encoding="utf-8")))
    assert sum(r["books_status"] == "ingress_cap" for r in rows) == 2 and sum(r["books_status"] == "ok" for r in rows) == 1  # the first day read, then the cap


def test_runner_registers_subcommands():
    import argparse

    ap = argparse.ArgumentParser()
    kd.add_subparsers(ap.add_subparsers(dest="cmd"))
    for cmd in ("kd-frame", "kd-books", "kd-seal", "screen-kd"):
        ns = ap.parse_args([cmd])
        assert callable(ns.fn)
    ns = ap.parse_args(["rep-kd", "--stage2-k", "2"])
    assert ns.stage2_k == 2 and ns.data_dumps_cap_gb if hasattr(ns, "data_dumps_cap_gb") else True
    assert ap.parse_args(["kd-books"]).data_dumps_cap_gb == 12.5 and ap.parse_args(["kd-books"]).ingress_cap_gb == 90.0


def test_handlers_map_refusals_to_exit_2(tmp_path, capsys):
    import argparse

    ap = argparse.ArgumentParser()
    kd.add_subparsers(ap.add_subparsers(dest="cmd"))
    ns = ap.parse_args(["kd-books", "--disk-cap-gb", "0.2", "--root", str(tmp_path / "creative_batch9")])
    assert ns.fn(ns) == 2 and "declaration" in capsys.readouterr().out
    ns = ap.parse_args(["screen-kd", "--root", str(tmp_path / "creative_batch9"), "--freeze-spec", str(tmp_path / "nope.json")])
    assert ns.fn(ns) == 2
