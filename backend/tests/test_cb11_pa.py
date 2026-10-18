# ruff: noqa: E501
"""CB11-P / CB11-A tests (offline; synthetic fixtures and fake transports; no network)."""

from __future__ import annotations

import gzip
import json
import math
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb8_common as cm
from astrolabe.research_lab import cb11_a as att
from astrolabe.research_lab import cb11_common as c11
from astrolabe.research_lab import cb11_p as pol
from astrolabe.research_lab import cb11_pa as pa
from astrolabe.research_lab import h5_seal
from astrolabe.research_lab import history_backfill as hb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_cb11  # noqa: E402

NOSLEEP = {"sleep": lambda s: None}
H = 3600.0
D = 86400.0


def ep(d: str) -> float:
    return cm.ep(d + "T00:00:00Z")


def iso(e: float) -> str:
    return datetime.fromtimestamp(e, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(argv, capsys):
    code = run_cb11.main(argv)
    out = capsys.readouterr().out.strip().splitlines()
    return code, (json.loads(out[-1]) if out else {})


def _keys(tmp: Path, rows=(("1", "1", "99", "", ""),)) -> Path:
    keys = tmp / "creative_batch11" / "exclusion_keys.csv.gz"
    keys.parent.mkdir(parents=True, exist_ok=True)
    keys.write_bytes(hb._gz_csv_bytes(["market_id", "found", "event_ids", "neg_risk_market_id", "series_ids"], [list(r) for r in rows]))
    (keys.parent / "exclusion_report.json").write_text(json.dumps({"keys_sha256": h5_seal.sha256_file(keys), "disjointness": "verified", "c1_t5_status": "retrieved"}))
    return keys


def _smoke(tmp: Path, ok=True, **over) -> Path:
    p = tmp / "smoke.json"
    crit = {k: ok for k in ("gamma_pol_paging", "prices_history", "data_api_reach", "wiki_summary", "wiki_lag")}
    crit.update(over)
    p.write_text(json.dumps({"smoke_version": c11.SMOKE_VERSION, "criteria": crit}))
    return p


def _jr(obj, status=200):
    return status, json.dumps(obj).encode(), {}


# =====================================================================================================================================
# Gamma parser, guards, flags
# =====================================================================================================================================

FORBIDDEN_FIXTURE = {"id": "1", "conditionId": "0xc1", "question": "Will Ann Lee win the election on March 5, 2026?", "slug": "s", "outcomes": '["Yes","No"]', "clobTokenIds": '["a","b"]',
                     "startDate": "2025-01-01T00:00:00Z", "endDate": "2026-03-05T00:00:00Z", "createdAt": "2024-12-01T00:00:00Z", "negRisk": True, "negRiskMarketID": "nr1",
                     "events": [{"id": "e1", "title": "Election", "endDate": "2026-03-05T00:00:00Z", "series": [{"id": "s1"}], "tags": [{"id": 2}]}], "feeSchedule": {"rate": 0.04},
                     "closedTime": "2026-03-06T00:00:00Z", "outcomePrices": '["1","0"]', "umaResolutionStatus": "resolved", "lastTradePrice": 0.77, "bestBid": 0.7, "bestAsk": 0.8,
                     "volumeNum": 123456.0, "volume": "999", "liquidity": "5", "oneDayPriceChange": 0.1, "description": "SECRETDESC", "umaResolutionStatuses": "[]"}


def test_pa_row_keeps_only_the_whitelist_and_guarded_fields_are_separate(tmp_path):
    r = pa.pa_row(FORBIDDEN_FIXTURE)
    pa.assert_pa_whitelisted(r)
    assert set(r) == set(pa.PA_COLUMNS) and r["token0"] == "a" and r["event_ids"] == "e1" and r["series_ids"] == "s1" and r["tag_ids"] == "2" and r["fee_rate"] == 0.04
    text = json.dumps(r, default=str)
    for bad in ("0.77", "123456", "SECRETDESC", "resolved", "outcomePrices", "closedTime"):
        assert bad not in text
    g = pa.pa_guarded(FORBIDDEN_FIXTURE)
    assert g["uma_status"] == "resolved" and g["closed_epoch"] == ep("2026-03-06")
    with pytest.raises(c11.Refused):
        pa.assert_pa_whitelisted({**r, "closedTime": "x"})
    assert pa.pa_row({**FORBIDDEN_FIXTURE, "outcomes": '["Yes","No","Maybe"]'}) is None
    assert pa.pa_row({**FORBIDDEN_FIXTURE, "clobTokenIds": '["a"]'}) is None


def test_frame_record_stores_no_forbidden_field_and_routes_guarded(tmp_path):
    m = {**FORBIDDEN_FIXTURE, "startDate": "2025-06-01T00:00:00Z", "endDate": "2025-12-01T00:00:00Z", "events": [{"id": "e1", "title": "X", "endDate": "2025-12-01T00:00:00Z", "tags": [{"id": 2}]}]}
    rec = pol.frame_record(m, "pol", ep("2025-11-24"), ep("2025-12-01") + 7 * D)
    assert rec is not None
    flat = json.dumps(rec["r"]) + json.dumps(rec["f"])
    for bad in ("outcomePrices", "0.77", "SECRETDESC", "resolved", "123456", "umaResolution"):
        assert bad not in flat
    assert set(rec["g"]) == {"market_id", "outcome_prices", "uma_status", "closed_epoch", "late_close"}
    assert rec["r"]["open_90"] == 1  # closedTime 2026-03-06 > t_90
    # life below 60 d, or end outside the window, is dropped locally
    assert pol.frame_record({**m, "startDate": "2025-11-01T00:00:00Z"}, "pol", ep("2025-11-24"), ep("2025-12-08")) is None
    assert pol.frame_record(m, "pol", ep("2026-01-01"), ep("2026-01-08")) is None


def test_named_dates_edit_detected_election_and_late_close():
    end = ep("2025-12-31")
    assert pol.named_dates("by December 31, 2025", end) == [end]
    assert pol.named_dates("on Dec 31", end) == [end]
    assert pol.named_dates("by 2026-01-05 or so", end) == [ep("2026-01-05")]
    assert not pol.edit_detected(end, math.nan, "Will X happen by December 31, 2025?", "")
    assert pol.edit_detected(end + 3 * D, math.nan, "Will X happen by December 31, 2025?", "")  # named date 3 d from endDate
    assert not pol.edit_detected(end + D, math.nan, "Will X happen by December 31, 2025?", "")  # exactly 1 day: not more than 1 day
    assert pol.edit_detected(end, end + 2 * D, "Q", "T")  # market vs event endDate differ by > 1 day
    assert not pol.edit_detected(end, end + D, "Q", "T")
    e24 = ep("2024-11-05")
    assert pol.election_2024(e24, "Will Harris win?", "x")
    assert pol.election_2024(e24, "Who wins the 2024 Presidential election?", "t")
    assert not pol.election_2024(e24, "Will the 2024 Olympics be cancelled?", "t")  # 2024 alone is not enough
    assert not pol.election_2024(ep("2025-06-01"), "Will Trump win?", "t")  # outside the scheduled-end window
    assert pol.election_2024(ep("2025-01-31") + 5 * H, "Will Vance win?", "t")  # window inclusive of 2025-01-31
    assert pol.late_close(end, end + 7 * D + 1) and not pol.late_close(end, end + 7 * D) and not pol.late_close(end, math.nan)


# =====================================================================================================================================
# prices-history point rule, labels, favourite
# =====================================================================================================================================


def test_price_point_uses_stamp_plus_600_strictly_before_t_and_24h_age():
    t = 1_000_000.0
    hist = [{"t": t - 600 - 1, "p": 0.6}, {"t": t - 600, "p": 0.7}, {"t": t - 10, "p": 0.9}]
    price, n, nd = pol.price_point(hist, t)
    assert price == 0.6  # the point at t - 600 is not yet known (stamp + 600 == t is not < t); t - 601 is
    assert n == 1 and nd == 1
    price2, _, _ = pol.price_point([{"t": t - 700, "p": 0.55}, {"t": t - 650, "p": 0.56}], t)
    assert price2 == 0.56
    stale = pol.price_point([{"t": t - 86400 - 1, "p": 0.6}], t)[0]
    assert math.isnan(stale)  # age > 24 h
    assert pol.price_point([{"t": t - 86400, "p": 0.6}], t)[0] == 0.6  # age exactly 24 h is allowed
    assert math.isnan(pol.price_point([], t)[0])
    pts = [{"t": t - 7 * D + 100 + i * 3600, "p": 0.5 + (0.01 if i % 2 else 0.0)} for i in range(10)]
    assert pol.price_point(pts, t)[2] == 2  # distinct values in the 7-day window
    pts2 = [{"t": t - 8 * D, "p": 0.4}, {"t": t - 7 * D - 700, "p": 0.41}, {"t": t - 1000, "p": 0.5}, {"t": t - 300, "p": 0.9}]
    assert pol.price_point(pts2, t)[2] == 1  # only the one point inside [t - 7 d, t) (stamp + 600) counts


def test_unit_labels_and_favourite_orientation():
    t = 1_000_000_000.0
    assert pol.unit_label(t - 6 * D, t, 1, 0.7, 5) == pol.LABEL_NOT_LISTED
    assert pol.unit_label(t - 7 * D, t, 1, 0.7, 5) == pol.LABEL_OK  # startDate <= t - 7 d
    assert pol.unit_label(t - 30 * D, t, 0, 0.7, 5) == pol.LABEL_CLOSED
    assert pol.unit_label(t - 30 * D, t, "", 0.7, 5) == pol.LABEL_NO_CLOSE
    assert pol.unit_label(t - 30 * D, t, 1, math.nan, 0) == pol.LABEL_NO_PRICE
    assert pol.unit_label(t - 30 * D, t, 1, 0.7, 1) == pol.LABEL_INACTIVE
    assert pol.fav_of(0.5) == (0, 0.5)  # a tie goes to outcome 0
    assert pol.fav_of(0.3) == (1, 0.7) and pol.fav_of(0.8) == (0, 0.8)
    assert pol.in_band({"p_f": 0.60}) and pol.in_band({"p_f": 0.85}) and not pol.in_band({"p_f": 0.8501}) and not pol.in_band({"p_f": 0.5999})
    assert pol.y_fav("[\"1\",\"0\"]", 0) == (1.0, "clean") and pol.y_fav("[\"1\",\"0\"]", 1) == (0.0, "clean")
    assert pol.y_fav("[\"0.5\",\"0.5\"]", 0) == (0.5, "fifty")
    assert pol.y_fav("[\"0.62\",\"0.38\"]", 0) == (0.5, "unclean") and pol.y_fav("[\"0.62\",\"0.38\"]", 0, 0.0) == (0.0, "unclean")
    assert pol.y_fav("garbage", 0)[1] == "unclean"
    assert pol.split_of(ep("2025-12-31") + 86399) == "screen" and pol.split_of(ep("2026-01-01")) == "holdout" and pol.split_of(ep("2026-09-01")) is None


def test_walk_window_prefilter_and_split_until_uncapped():
    calls = []

    def tr(url, params):
        calls.append(params)
        a = cm.ep(params["end_date_min"])
        b = cm.ep(params["end_date_max"])
        n = 2500 if b - a > 3 * 86400 else 10  # a window longer than 3 days is "capped" (2,500 rows)
        rows = [{"id": str(i)} for i in range(params["offset"], min(n, params["offset"] + params["limit"]))]
        return _jr(rows)

    lim = hb.Limiter(tr, rps=1000.0, sleep=lambda s: None)
    acc = {"batches": [], "splits": 0, "windows": 0, "failed_windows": 0, "capped_kept": 0}
    a = int(ep("2025-03-03"))
    pol.walk_window(lim, {"closed": "true", "tag_id": 2}, a, a + 7 * 86400, acc)
    assert acc["splits"] >= 1 and acc["windows"] >= 2 and acc["capped_kept"] == 0
    first = calls[0]
    assert cm.ep(first["start_date_max"]) == a - 53 * D  # window start - 53 d
    # not split: the capped window keeps its first 2,000 rows (offset cap) and is counted
    calls.clear()
    acc2 = {"batches": [], "splits": 0, "windows": 0, "failed_windows": 0, "capped_kept": 0}
    pol.walk_window(lim, {"closed": "true"}, a, a + 7 * 86400, acc2, split=False)
    assert acc2["splits"] == 0 and acc2["capped_kept"] == 1 and len(acc2["batches"]) == 2000
    # a failed request makes the window failed, never "capped"
    lim2 = hb.Limiter(lambda u, p: (500, b"", {}), rps=1000.0, sleep=lambda s: None)
    acc3 = {"batches": [], "splits": 0, "windows": 0, "failed_windows": 0, "capped_kept": 0}
    pol.walk_window(lim2, {"closed": "true"}, a, a + 7 * 86400, acc3)
    assert acc3["failed_windows"] == 1 and acc3["capped_kept"] == 0


# =====================================================================================================================================
# fake world for the P fetch jobs
# =====================================================================================================================================


def gamma_market(i, end, *, politics, life_d=120, closed_off=D, event=None, uma="resolved", prices='["1","0"]'):
    start = end - life_d * D
    return {"id": str(i), "conditionId": f"0xc{i}", "question": f"Will thing {'abcdefghij'[i % 10]} happen?", "slug": f"q{i}", "outcomes": '["Yes","No"]', "clobTokenIds": json.dumps([f"t0_{i}", f"t1_{i}"]),
            "startDate": iso(start), "createdAt": iso(start - D), "endDate": iso(end), "negRisk": False, "events": [{"id": event or f"ev{i}", "title": f"Event {event or i}", "endDate": iso(end)}],
            "feeType": "politics_fees" if politics else "culture_fees", "feeSchedule": {"rate": 0.04}, "closedTime": iso(end + closed_off), "outcomePrices": prices, "umaResolutionStatus": uma,
            "volumeNum": 50000.0, "_pol": politics}


class PolWorld:
    def __init__(self, windows, n_per=40, seed=3):
        rng = random.Random(seed)
        self.markets = []
        self.windows = windows
        i = 100
        for a, b in windows:
            for _ in range(n_per):
                for politics in (True, False):
                    end = a + rng.random() * (b - a - 1)
                    kw = {}
                    if i % 13 == 0:
                        kw["closed_off"] = -80 * D  # closes 80 d before the end: open at t_90, closed before t_60 and t_30
                    self.markets.append(gamma_market(i, end, politics=politics, event=f"ev{i // 3}", **kw))
                    i += 1
        self.by_token = {m["clobTokenIds"].split('"')[1]: m for m in self.markets}
        self.by_cid = {m["conditionId"]: m for m in self.markets}
        self.requests = {"gamma": 0, "clob": 0, "data": 0}

    def __call__(self, url, params):
        if url == hb.GAMMA_MARKETS:
            self.requests["gamma"] += 1
            lo, hi = cm.ep(params["end_date_min"]), cm.ep(params["end_date_max"])
            smax = cm.ep(params["start_date_max"]) if "start_date_max" in params else math.inf
            rows = [m for m in self.markets if lo <= cm.ep(m["endDate"]) <= hi and cm.ep(m["startDate"]) <= smax and (("tag_id" not in params) or m["_pol"])]
            rows = sorted(rows, key=lambda m: int(m["id"]))[params["offset"]: params["offset"] + params["limit"]]
            return _jr([{k: v for k, v in m.items() if k != "_pol"} for m in rows])
        if url == hb.CLOB_PRICES:
            self.requests["clob"] += 1
            m = self.by_token[params["market"]]
            mid = int(m["id"])
            if mid % 11 == 0:
                return _jr({"history": []})
            base = 0.55 + (mid % 30) / 100.0
            t0, t1 = params["startTs"], params["endTs"]
            pts = [{"t": int(t), "p": round(base + (0.0 if mid % 7 == 0 else 0.01 * ((t // 1800) % 3)), 4)} for t in range(int(t0), int(t1), 1800)]
            return _jr({"history": pts})
        if url == hb.DATA_TRADES:
            self.requests["data"] += 1
            m = self.by_cid[params["market"]]
            end = cm.ep(m["endDate"])
            trades = [{"timestamp": int(end - 100 * D + k * 3 * D), "outcomeIndex": 0, "price": 0.6 + (k % 5) * 0.01, "size": 10.0 + k, "transactionHash": f"0x{m['id']}_{k}"} for k in range(34)]
            trades.sort(key=lambda x: -x["timestamp"])
            return _jr(trades[params["offset"]: params["offset"] + params["limit"]])
        return 404, b"", {}


WINDOWS = [(int(ep("2025-03-03")), int(ep("2025-03-10"))), (int(ep("2025-06-02")), int(ep("2025-06-09"))), (int(ep("2026-03-02")), int(ep("2026-03-09"))), (int(ep("2026-05-04")), int(ep("2026-05-11")))]


@pytest.fixture()
def pworld(tmp_path):
    return PolWorld(WINDOWS)


@pytest.fixture()
def pframe(tmp_path, pworld):
    hist = tmp_path / "history"
    m = pol.pol_frame(hist, pworld, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, windows=WINDOWS, data_dumps=None, **NOSLEEP)
    assert m["status"] == pol.FRAME_STATUS, m
    return {"hist": hist, "rdir": hist / pol.RUN, "world": pworld, "tmp": tmp_path}


def test_pol_frame_files_split_guards_and_write_once(pframe):
    rdir = pframe["rdir"]
    scr = pol.read_frame(rdir, "screen", job="census")
    assert scr and all(float(r["end_epoch"]) < ep("2026-01-01") for r in scr)
    hold = [dict(r) for r in c11.read_csv_gz(rdir / "holdout" / "frame_hold.csv.gz")]
    assert hold and all(float(r["end_epoch"]) >= ep("2026-01-01") for r in hold)
    assert {r["group"] for r in scr} == {"pol", "ctl"}
    # the frame, flags and listing files carry no outcome-adjacent column
    for fn in ("frame.csv.gz", "flags.csv.gz"):
        with gzip.open(rdir / fn, "rt") as fh:
            hdr = fh.readline()
        assert "outcome" not in hdr and "uma" not in hdr and "closed" not in hdr and "late_close" not in hdr
    g = {r["market_id"]: r for r in pol.open_p_guarded(rdir / "outcomes_guarded.csv.gz", "screen-P")}
    assert set(g) == {r["market_id"] for r in scr}
    # open-at-t_h booleans: markets that close 80 d before the end are closed before t_60 / t_30
    early = [r for r in scr if int(r["market_id"]) % 13 == 0]
    assert early and all(r["open_90"] == "1" and r["open_60"] == "0" and r["open_30"] == "0" for r in early)
    # re-run is a no-op (complete is sticky)
    n0 = sum(pframe["world"].requests.values())
    m2 = pol.pol_frame(pframe["hist"], pframe["world"], rules_sha="r" * 64, smoke_path=_smoke(pframe["tmp"]), exclusion_keys_path=_keys(pframe["tmp"]), now=1.8e9, windows=WINDOWS, **NOSLEEP)
    assert m2["status"] == pol.FRAME_STATUS and sum(pframe["world"].requests.values()) == n0


def test_holdout_guards_for_frame_origins_and_outcomes(pframe):
    rdir = pframe["rdir"]
    for job in ("census", "screen-P", "refused"):
        with pytest.raises(c11.Refused):
            pol.read_frame(rdir, "holdout", job=job)
        with pytest.raises(c11.Refused):
            pol.open_p_guarded(rdir / "holdout" / "outcomes_guarded_hold.csv.gz", job)
    with pytest.raises(c11.Refused):
        pol.load_origins(rdir, "holdout", job="screen-P")
    assert pol.read_frame(rdir, "holdout", job="rep-P")
    with pytest.raises(c11.Refused):
        pol.open_p_guarded(rdir / "outcomes_guarded.csv.gz", "census")  # a census job never opens a guarded file
    assert pol.holdout_counts(rdir)["n_markets"] > 0


def test_pol_frame_stalls_on_smoke_failure_and_unverified_keys(tmp_path, pworld):
    hist = tmp_path / "history"
    m = pol.pol_frame(hist, pworld, rules_sha="r" * 64, smoke_path=_smoke(tmp_path, ok=True, prices_history=False), exclusion_keys_path=_keys(tmp_path), now=1.8e9, windows=WINDOWS, **NOSLEEP)
    assert m["status"] == c11.STALL_NOT_RUN_SOURCE and sum(pworld.requests.values()) == 0
    hist2 = tmp_path / "h2"
    keys = _keys(tmp_path)
    rep = json.loads((keys.parent / "exclusion_report.json").read_text())
    rep["disjointness"] = c11.UNVERIFIED
    (keys.parent / "exclusion_report.json").write_text(json.dumps(rep))
    m2 = pol.pol_frame(hist2, pworld, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=keys, now=1.8e9, windows=WINDOWS, **NOSLEEP)
    assert m2["status"] == c11.STALL_DISJOINTNESS


def test_pol_frame_disk_headroom_is_pending(tmp_path, pworld):
    dd = tmp_path / "dd"
    dd.mkdir()
    with pytest.raises(c11.NotNow):
        pol.pol_frame(tmp_path / "history", pworld, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, windows=WINDOWS, data_dumps=dd,
                      data_dumps_cap_gb=0.0000001, free_fn=lambda p: 100 * 1024**3, **NOSLEEP)
    with pytest.raises(c11.NotNow):
        pol.pol_frame(tmp_path / "history", pworld, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, windows=WINDOWS, data_dumps=dd,
                      free_fn=lambda p: 4 * 1024**3, **NOSLEEP)


def test_pol_frame_key_drops_exclude_ids_and_events(tmp_path, pworld):
    keys = _keys(tmp_path, rows=(("100", "1", "", "", ""), ("101", "1", "ev34", "", "")))
    m = pol.pol_frame(tmp_path / "history", pworld, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=keys, now=1.8e9, windows=WINDOWS, **NOSLEEP)
    assert m["status"] == pol.FRAME_STATUS
    ids = {r["market_id"] for r in c11.read_csv_gz(tmp_path / "history" / pol.RUN / "frame.csv.gz")}
    assert "100" not in ids and not any(pworld_m["id"] in ids for pworld_m in pworld.markets if pworld_m["events"][0]["id"] == "ev34")


def test_assemble_is_deterministic_and_caps_per_event(pworld):
    recs = [pol.frame_record({k: v for k, v in m.items() if k != "_pol"}, "pol" if m["_pol"] else "ctl", 0, 4e9) for m in pworld.markets]
    recs = [r for r in recs if r]
    # put 9 markets into one event: the per-event cap keeps 4
    for r in recs[:9]:
        r["r"]["event_id"] = r["r"]["event_ids"] = "evBIG"
        r["r"]["group"] = "pol"
    a1, rep1 = pol.assemble(recs, set(), {"event": set(), "neg_risk_market": set(), "series": set()})
    a2, rep2 = pol.assemble(list(reversed(recs)), set(), {"event": set(), "neg_risk_market": set(), "series": set()})
    ids = lambda a: {k: [x["r"]["market_id"] for x in v] for k, v in a.items()}  # noqa: E731
    assert ids(a1) == ids(a2) and rep1["sampled"] == rep2["sampled"]
    assert sum(1 for k, v in a1.items() for x in v if k[0] == "pol" and x["event_key"] == "evBIG") <= pol.MAX_PER_EVENT
    assert rep1["per_event_capped_out"]["pol"] >= 5
    assert all(pol.split_of(float(x["r"]["end_epoch"])) == k[1] for k, v in a1.items() for x in v)


@pytest.fixture()
def pprices(pframe):
    m = pol.pol_prices(pframe["hist"], pframe["world"], rules_sha="r" * 64, now=1.8e9, smoke_path=_smoke(pframe["tmp"]), data_dumps=None, **NOSLEEP)
    assert m["status"] == pol.PRICES_STATUS, m
    return pframe


def test_pol_prices_labels_requests_and_reach(pprices):
    rdir, world = pprices["rdir"], pprices["world"]
    org = pol.load_origins(rdir, "screen", job="census")
    fm = {r["market_id"]: r for r in pol.read_frame(rdir, "screen", job="census")}
    labs = {(o["market_id"], int(o["h"])): o["label"] for o in org}
    ids = [m for m in fm if int(m) % 13 == 0 and int(m) % 11 != 0]
    assert ids and all(labs[(m, 90)] == pol.LABEL_OK or labs[(m, 90)] == pol.LABEL_INACTIVE for m in ids)
    assert all(labs[(m, 60)] == pol.LABEL_CLOSED and labs[(m, 30)] == pol.LABEL_CLOSED for m in ids)
    nop = [m for m in fm if int(m) % 11 == 0 and int(m) % 13 != 0]
    assert nop and all(labs[(m, 90)] == pol.LABEL_NO_PRICE for m in nop)
    flat = [m for m in fm if int(m) % 7 == 0 and int(m) % 11 != 0 and int(m) % 13 != 0]
    assert flat and all(labs[(m, 90)] == pol.LABEL_INACTIVE for m in flat)  # a flat series is "inactive (proxy)"
    # the price is the outcome-0 token price known before t_h
    ok = [o for o in org if o["label"] == pol.LABEL_OK][0]
    assert 0.5 <= float(ok["p"]) <= 0.9
    # one price request per eligible unit; Data API only for politics SCREEN markets
    n_units = sum(1 for o in org if o["label"] in pol.ELIGIBLE_LABELS) + sum(1 for o in pol.load_origins(rdir, "holdout", job="rep-P") if o["label"] in pol.ELIGIBLE_LABELS)
    assert world.requests["clob"] == n_units
    reach = pol.load_reach(rdir)
    pol_ids = {m for m, r in fm.items() if r["group"] == "pol"}
    assert {m for m, r in reach.items() if r["status"] == "ok"} <= pol_ids and any(r["status"] == "ok" for r in reach.values())
    assert all(r["status"] == "not_requested" for m, r in reach.items() if m not in pol_ids)
    tx = pol.tx_loader_for(rdir)(next(m for m, r in reach.items() if r["status"] == "ok"))
    assert tx is not None and len(tx[0]) > 0
    # a finished fetch is sticky
    n0 = sum(world.requests.values())
    m2 = pol.pol_prices(pprices["hist"], world, rules_sha="r" * 64, now=1.8e9, **NOSLEEP)
    assert m2["status"] == pol.PRICES_STATUS and sum(world.requests.values()) == n0


def test_pol_prices_waits_for_frame_and_stops_on_budget(tmp_path, pworld):
    with pytest.raises(c11.NotNow):
        pol.pol_prices(tmp_path / "history", pworld, rules_sha="r" * 64, now=1.8e9, **NOSLEEP)
    hist = tmp_path / "history"
    pol.pol_frame(hist, pworld, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, windows=WINDOWS, **NOSLEEP)
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 3

    m = pol.pol_prices(hist, pworld, rules_sha="r" * 64, now=1.8e9, should_stop=stop, **NOSLEEP)
    assert m["status"] == "in_progress" and m["complete"] is False  # resumable chunk
    m2 = pol.pol_prices(hist, pworld, rules_sha="r" * 64, now=1.8e9, **NOSLEEP)
    assert m2["status"] == pol.PRICES_STATUS


def test_pol_prices_disk_budget_exit_state(pframe):
    m = pol.pol_prices(pframe["hist"], pframe["world"], rules_sha="r" * 64, now=1.8e9, disk_cap=1, data_dumps=None, **NOSLEEP)
    assert m["status"] == cm.DISK_BUDGET_TOKEN
    m2 = pol.pol_prices(pframe["hist"], pframe["world"], rules_sha="r" * 64, now=1.8e9, **NOSLEEP)
    assert m2["status"] == cm.DISK_BUDGET_TOKEN  # sticky, never retried


def test_census_p_counts_only_and_never_opens_a_guarded_file(pprices, monkeypatch):
    rdir = pprices["rdir"]
    for fn in ("outcomes_guarded.csv.gz", "holdout/outcomes_guarded_hold.csv.gz"):
        (rdir / fn).write_bytes(b"not a gzip file")  # a census path that opened it would crash
    called = []
    monkeypatch.setattr(pol, "open_p_guarded", lambda *a, **k: called.append(a))
    doc = pol.census_p(rdir, n_draws=5, n_inner=5)
    assert not called and doc["counts_only"] is True
    flat = json.dumps(doc, default=str)
    for bad in pol.CENSUS_FORBIDDEN:
        assert f'"{bad}"' not in flat
    assert doc["GP"]["pass"] is False and doc["label_P1"].startswith("not testable (GP") and doc["p_runs"] is False
    assert set(doc["labels"]) <= {pol.LABEL_OK, pol.LABEL_INACTIVE, pol.LABEL_NO_PRICE, pol.LABEL_NOT_LISTED, pol.LABEL_CLOSED, pol.LABEL_NO_CLOSE, pol.LABEL_FAILED}
    assert doc["flags"]["late_close_flag"].startswith("guarded")
    # with relaxed thresholds the same census reaches the coverage audit and GPP
    monkeypatch.setattr(pol, "GP", {"markets": 5, "events": 3, "weeks": 2})
    d2 = pol.census_p(rdir, n_draws=5, n_inner=5)
    assert d2["GP"]["pass"] is True and d2["coverage_audit"]["share"] > 0.9 and "mde" in d2["GPP"]


# =====================================================================================================================================
# P statistics on synthetic units
# =====================================================================================================================================


def synth_p_units(n_markets=500, excess=0.10, seed=5, group="pol"):
    rng = random.Random(seed)
    units = []
    for m in range(n_markets):
        end = ep("2024-07-08") + rng.random() * (ep("2025-12-20") - ep("2024-07-08"))
        ev = f"e{m // 2}"
        y_u = rng.random()
        p0 = rng.uniform(0.62, 0.84)
        y = 1.0 if y_u < min(p0 + excess, 0.999) else 0.0
        for h in (90, 60, 30):
            units.append({"market_id": f"m{m}", "group": group, "event": ev, "week": pa.iso_week_of(end), "month": pa.month_of(end), "end": end, "h": h, "t_h": end - h * D, "p": p0, "k": 0,
                          "p_f": p0, "label": "ok", "n_distinct": 5, "fee_rate": 0.04, "edit": 0, "elec": 0, "late": 0, "closed": end + 3 * D, "Y": y, "Y_worst": y, "ystat": "clean", "uma": "resolved"})
    return units


def test_p1_advances_on_a_strong_calibration_excess_and_not_on_calibrated_outcomes():
    pos = pol.p1_stat(synth_p_units(excess=0.10), synth_p_units(excess=0.0, seed=9, group="ctl"), ext={"t5_absent": False}, n_draws=20)
    assert pos["core_ok"] and pos["mean"] > 0.05 and pos["label"] == "L1, hindsight end date"
    assert pos["concentration_ok"] and pos["robustness"]["ok"] and pos["without_top5_ok"] and pos["placebo"]["holds"]
    assert pos["advance"] is True
    assert pos["attribution_control"]["politics_specific"] is True  # control mean ~0
    neg = pol.p1_stat(synth_p_units(excess=0.0, seed=6), synth_p_units(excess=0.0, seed=9, group="ctl"), ext={"t5_absent": False}, n_draws=20)
    assert neg["advance"] is False and neg["core_ok"] is False


def test_p1_floor_not_met_when_effect_below_3c_and_not_testable_when_tiny():
    small = pol.p1_stat(synth_p_units(n_markets=2500, excess=0.02, seed=7), [], ext={"t5_absent": False}, n_draws=5, placebo=False)
    assert small["core_ok"] is False and small["advance"] is False  # below the +3.0c floor whatever the p
    tiny = pol.p1_stat(synth_p_units(n_markets=20), [], ext={"t5_absent": False}, n_draws=5)
    assert tiny["testable"] is False and tiny["p"] == 1.0 and tiny["advance"] is False


def test_p1_t5_absent_adds_a_binding_check_and_worst_case_outcomes_bind():
    us = synth_p_units(excess=0.10)
    r = pol.p1_stat(us, [], ext={"t5_absent": True}, n_draws=5, placebo=False)
    assert "exclude_t5_window" in r["robustness"] and r["robustness"]["exclude_t5_window"]["binding"]
    # unclean markets scored Y = 0 (worst case) that flip the sign remove the advance
    bad = [{**u, "Y_worst": 0.0} for u in us]
    r2 = pol.p1_stat(bad, [], ext={"t5_absent": False}, n_draws=5, placebo=False)
    assert r2["robustness"]["unclean_as_zero"]["ok"] is False and r2["robustness"]["ok"] is False and r2["advance"] is False


def test_election_concentration_drops_the_largest_week_and_event():
    us = synth_p_units(excess=0.0, seed=11)
    # all the excess sits in one ISO week: dropping it removes the effect
    wk = us[0]["week"]
    for u in us:
        if u["week"] == wk:
            u["Y"] = 1.0
    mk = pol.market_means(pol.with_excess([u for u in us if pol.in_band(u)]))
    masks = pol.drop_masks(mk)
    assert set(masks) == {"week_by_count", "week_by_excess", "event_by_count", "event_by_excess"}
    weeks = np.array([m["week"] for m in mk])
    assert not masks["week_by_excess"][weeks == wk].any() or masks["week_by_excess"].sum() < len(mk)
    assert all(mask.sum() >= len(mk) - 40 for mask in masks.values())  # one cluster out, not many


def test_p2_arithmetic_entry_at_earliest_unit_declared_ask_fee_and_r_ann():
    u = {"market_id": "m1", "event": "e1", "week": "2025-W01", "end": ep("2025-01-06"), "h": 90, "t_h": ep("2025-01-06") - 90 * D, "p_f": 0.70, "fee_rate": 0.0, "Y": 1.0, "closed": ep("2025-01-06") - 60 * D,
         "edit": 0, "late": 0, "elec": 0}
    later = {**u, "h": 30, "p_f": 0.80, "t_h": ep("2025-01-06") - 30 * D}
    e = pol.p2_entries([later, u])
    assert len(e) == 1 and e[0]["h"] == 90  # earliest unit: 90 d
    a = 0.70 + 0.015
    fee = 0.04 * a * (1 - a)  # r = max(feeSchedule.rate, 0.04) = 0.04
    assert e[0]["a"] == pytest.approx(a) and e[0]["fee"] == pytest.approx(fee) and e[0]["net"] == pytest.approx(1.0 - a - fee)
    assert e[0]["hold_d"] == pytest.approx(30.0)  # t_h to closedTime
    assert pol.r_ann(e) == pytest.approx(365.0 * e[0]["net"] / (a * 30.0))
    e2 = pol.p2_entries([{**u, "closed": u["t_h"] + 0.2 * D}])
    assert pol.r_ann(e2) == pytest.approx(365.0 * e2[0]["net"] / (e2[0]["a"] * 1.0))  # max(d, 1)
    assert pol.p2_entries([u], half_spread=0.025)[0]["a"] == pytest.approx(0.725)
    assert pol.fee_r(0.0) == 0.04 and pol.fee_r(0.07) == 0.07 and pol.fee_r(math.nan) == 0.04


def test_p2_floors_robustness_and_annualised_excess():
    us = synth_p_units(n_markets=600, excess=0.15, seed=21)
    r = pol.p2_stat(us, ext={})
    assert r["testable"] and r["net_mean"] > 0.02 and r["r_ann_excess"] == pytest.approx(r["r_ann"] - 0.045)
    assert r["floors"]["net"] and r["floors"]["p"] and r["advance"] is True
    r0 = pol.p2_stat(synth_p_units(n_markets=600, excess=0.0, seed=22), ext={})
    assert r0["advance"] is False


def test_gpp_arithmetic_determinism_and_gate():
    us = synth_p_units(n_markets=300, seed=31)
    g1 = pol.gpp(us, n_draws=20, n_inner=20)
    g2 = pol.gpp(us, n_draws=20, n_inner=20)
    assert g1 == g2 and g1["seed"] == c11.SEED_GPP == 11120
    assert g1["sd_p"] == max(g1["sd_across_draws"], g1["mean_se_event"], g1["mean_se_week"])
    assert g1["mde"] == pytest.approx(pa.MDE_Z * 1.2 * g1["sd_p"]) and pa.MDE_Z == pytest.approx(2.326 + 0.842)
    assert g1["pass"] == (g1["mde"] <= 0.06)
    assert pol.gpp(us[:6])["pass"] is False  # too few units
    assert pol.GPP_MAX_MDE == 0.06 and pol.GPP_LOADINGS == (0.2, 0.4, 0.4)


def test_copula_shares_the_week_factor_across_events_and_one_z_per_market():
    # many events in one week: a shared week factor makes their calibrated outcomes positively correlated; with loadings 0 it would not
    n = 4000
    week_code = np.zeros(n, int)
    event_code = np.arange(n)
    unit_mk = np.arange(n)
    pf = np.full(n, 0.5)
    rng = np.random.default_rng(0)
    means = [pol.copula_pstar(week_code, event_code, unit_mk, pf, rng).mean() for _ in range(60)]
    assert np.std(means) > 0.03  # a common shock moves the whole week's hit rate (independent: sd ~ 0.008)
    # one Z per market shared across horizons: a market's three units get identical Y*
    e = pol.copula_pstar(np.zeros(2, int), np.arange(2), np.array([0, 0, 0, 1, 1, 1]), np.full(6, 0.5), np.random.default_rng(1))
    assert len(e) == 2


def test_p1_placebo_is_seeded_and_judged_on_p_only():
    us = [u for u in synth_p_units(n_markets=300, seed=41) if pol.in_band(u)]
    a = pol.p1_placebo(us, n_draws=15)
    b = pol.p1_placebo(us, n_draws=15)
    assert a == b and a["n_draws"] == 15 and "shared week factor" in a["note"]
    assert c11.PLACEBO_SEEDS["P1_copula"] == 11102


def test_availability_share_rule():
    org = [{"market_id": "m", "label": x} for x in ["ok"] * 5 + ["no_price"] * 5 + ["not_listed"] * 3 + ["closed_before_t"] * 2]
    av = pol.availability(org, "pol", {"m"})
    assert av["eligible"] == 10 and av["share"] == 0.5 and av["ok"] is False  # < 60%: not testable (availability)
    org2 = org + [{"market_id": "m", "label": "inactive_proxy"}] * 4
    assert pol.availability(org2, "pol", {"m"})["ok"] is True


def test_screen_p_returns_counted_labels_without_opening_guarded_files(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(pol, "open_p_guarded", lambda *a, **k: opened.append(a))
    res = pol.screen_p(tmp_path, {"P": {"label_P1": "not run (power)", "label_P2": "not run (power)"}})
    assert res["P1"]["p"] == 1.0 and res["P1"]["testable"] is False and res["P2"]["verdict"] == "not run (power)" and not opened


# =====================================================================================================================================
# seal, rules, freeze, runner
# =====================================================================================================================================


def test_pa_rules_file_roundtrip_hash_mismatch_and_independent_of_w_rules(tmp_path):
    f = tmp_path / "pa_rules.json"
    pa.write_pa_rules(f)
    sha = pa.verify_pa_rules(f, require_committed=False)
    doc = json.loads(f.read_text())
    assert doc["rules_sha256"] == sha and set(doc["declared"]) == {"cb11_p", "cb11_a"} and pa.write_pa_rules(f) == f
    assert doc["declared"]["cb11_p"]["gates"]["GPP"]["max_mde"] == 0.06 and doc["declared"]["cb11_a"]["gates"]["GA"]["spike"] == 200
    assert any(k.startswith("cb11_p.") for k in doc["func_sources_sha256"]) and any(k.endswith("cluster_p_week") for k in doc["func_sources_sha256"])
    bad = tmp_path / "bad.json"
    d2 = dict(doc)
    d2["declared"] = {**doc["declared"], "cb11_p": {**doc["declared"]["cb11_p"], "band": [0.5, 0.9]}}
    bad.write_text(json.dumps(d2))
    with pytest.raises(c11.Refused):
        pa.verify_pa_rules(bad, require_committed=False)
    with pytest.raises(c11.Refused):
        pa.verify_pa_rules(tmp_path / "missing.json", require_committed=False)
    # the W rules hash does not move when P/A exist: cb11_common's rule modules are untouched
    assert c11.RULE_MODULES == ("cb11_w", "cb11_smoke")
    assert callable(pa.PA_RULE_FUNCS) and len(pa.PA_RULE_FUNCS()) > 100


def test_pa_freeze_part_is_separate_and_must_match(tmp_path):
    part = pa.freeze_part_pa()
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"W": {"x": 1}, "PA": part}))
    assert pa.require_freeze_pa(spec, require_committed=False) == part["declaration_sha256"]
    spec.write_text(json.dumps({"W": {"x": 1}, "PA": {**part, "declaration_sha256": "0" * 64}}))
    with pytest.raises(c11.Refused):
        pa.require_freeze_pa(spec, require_committed=False)
    spec.write_text(json.dumps({"W": {"x": 1}}))
    with pytest.raises(c11.Refused):
        pa.require_freeze_pa(spec, require_committed=False)
    # W freezes without any P/A declaration
    spec.write_text(json.dumps({"W": {"x": 1}}))
    assert c11.require_freeze("W", spec, require_committed=False)


def test_stage2_k_pa_does_not_depend_on_w_results(tmp_path):
    with pytest.raises(c11.NotNow):
        pa.stage2_k_pa(tmp_path, None)
    assert pa.stage2_k_pa(tmp_path, 3) == 3
    with pytest.raises(c11.Refused):
        pa.stage2_k_pa(tmp_path, 0)
    for n, adv in (("results_W.json", ["W1"]), ("results_P.json", ["P1", "P2"]), ("results_A.json", [])):
        (tmp_path / n).write_text(json.dumps({t: {"advance": True} for t in adv}))
    assert pa.stage2_k_pa(tmp_path, None) == 3
    with pytest.raises(c11.Refused):
        pa.stage2_k_pa(tmp_path, 2)


def test_seal_p_requires_complete_fetch_and_seals_once(pprices):
    seals = pprices["tmp"] / "seals"
    rdir = pprices["rdir"]
    out = c11.seal_holdout(rdir, family="pol", statuses=(pol.PRICES_STATUS,), copy_name=pol.SEAL_COPY_NAME, rows=pol.seal_rows(rdir), rules_sha="r" * 64, seals_dir=seals, is_committed=lambda p: True)
    assert out["status"] == "pol_sealed" and (seals / pol.SEAL_COPY_NAME).exists()
    doc = c11.verify_holdout_seal(rdir, pol.SEAL_COPY_NAME, seals)
    assert doc["n_holdout_files"] >= 3  # frame_hold, flags_hold, outcomes_guarded_hold, origins
    again = c11.seal_holdout(rdir, family="pol", statuses=(pol.PRICES_STATUS,), copy_name=pol.SEAL_COPY_NAME, rows=[], rules_sha="r" * 64, seals_dir=seals)
    assert again["already_sealed"] is True
    (rdir / "holdout" / "origins.csv.gz").write_bytes(b"tampered")
    with pytest.raises(c11.Refused):
        c11.verify_holdout_seal(rdir, pol.SEAL_COPY_NAME, seals)
    with pytest.raises(c11.Refused):
        pol.rep_p(rdir, {"P": {}}, ("P1",), 1, seals_dir=seals)  # rep refuses a tampered holdout before reading it


def test_rep_p_runs_on_a_verified_seal_and_logs_access(pprices, monkeypatch):
    seals = pprices["tmp"] / "seals"
    rdir = pprices["rdir"]
    c11.seal_holdout(rdir, family="pol", statuses=(pol.PRICES_STATUS,), copy_name=pol.SEAL_COPY_NAME, rows=pol.seal_rows(rdir), rules_sha="r" * 64, seals_dir=seals, is_committed=lambda p: True)
    out = pol.rep_p(rdir, {"P": {"c1_t5_status": "absent"}}, ("P1", "P2"), 2, n_draws=3, seals_dir=seals)
    assert out["label"].startswith("possibly touched holdout") and out["stage2_alpha_over_k"] == pytest.approx(0.025)
    assert out["P1_rep"]["testable"] is False and out["P2_rep"]["stage2_pass_alpha_over_k"] is False  # tiny synthetic holdout
    log = (rdir / c11.ACCESS_LOG).read_text().splitlines()
    assert json.loads(log[-1])["job"] == "rep-P"


def test_runner_declared_arguments_and_pending_exit_codes(tmp_path, capsys):
    base = ["--allow-uncommitted-rules", "--standalone", "--history-root", (tmp_path / "history").as_posix()]
    pa_rules = tmp_path / "pa_rules.json"
    code, out = _run(["rules-pa", "--path", pa_rules.as_posix()], capsys)
    assert code == 0 and len(out["rules_sha256"]) == 64
    pr = ["--pa-rules", pa_rules.as_posix()]
    code, out = _run(["pol-prices", *base, *pr, "--disk-cap-gb", "0.5"], capsys)
    assert code == 2 and "declaration" in out["refused"]
    code, out = _run(["attn-data", *base, *pr, "--wiki-rps", "5"], capsys)
    assert code == 2 and "wiki_rps" in out["refused"]
    code, out = _run(["pol-frame", *base, *pr, "--rps", "9"], capsys)
    assert code == 2
    code, out = _run(["pol-prices", *base, *pr, "--smoke", _smoke(tmp_path).as_posix(), "--data-dumps", tmp_path.as_posix()], capsys)
    assert code == 75 and "pending" in out["science"]  # q0225 not finished: pending (exit 75)
    code, out = _run(["pol-frame", *base, "--pa-rules", (tmp_path / "none.json").as_posix()], capsys)
    assert code == 2 and "P/A rules file" in out["refused"]  # a missing rules file is a refusal


def test_runner_screen_and_rep_refuse_before_the_pa_freeze_and_need_pins(tmp_path, capsys):
    pa_rules = tmp_path / "pa_rules.json"
    pa.write_pa_rules(pa_rules)
    root = (tmp_path / "creative_batch11").as_posix()
    base = ["--pa-rules", pa_rules.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", root, "--history-root", (tmp_path / "history").as_posix()]
    for fam in ("P", "A"):
        for cmd in ("screen", "rep"):
            code, out = _run([cmd, "--family", fam, *base, "--freeze-spec", (tmp_path / "none.json").as_posix()], capsys)
            assert code == 2 and "freeze" in out["refused"]
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"W": {}, "PA": pa.freeze_part_pa()}))
    code, out = _run(["screen", "--family", "P", *base, "--freeze-spec", spec.as_posix()], capsys)
    assert code == 75  # census_PA.json missing: pending
    code, out = _run(["rep", "--family", "P", *base, "--freeze-spec", spec.as_posix()], capsys)
    assert code == 75  # Stage-2 k not fixed (no --stage2-k, no Stage-1 files): pending, not coupled to W
    code, out = _run(["rep", "--family", "A", *base, "--freeze-spec", spec.as_posix(), "--stage2-k", "2"], capsys)
    assert code == 75 and "results_A.json" in out["tempfail"]
    Path(root).mkdir(parents=True, exist_ok=True)
    (Path(root) / "results_A.json").write_text(json.dumps({"A1": {"advance": True}}))
    code, out = _run(["rep", "--family", "A", *base, "--freeze-spec", spec.as_posix(), "--stage2-k", "2"], capsys)
    assert code == 2 and "--results-sha256" in out["refused"]
    code, out = _run(["rep", "--family", "A", *base, "--freeze-spec", spec.as_posix(), "--stage2-k", "2", "--results-sha256", "0" * 64], capsys)
    assert code == 2 and "stays closed" in out["refused"]


def test_runner_census_pa_pending_until_fetches_complete_and_write_once(tmp_path, capsys):
    pa_rules = tmp_path / "pa_rules.json"
    pa.write_pa_rules(pa_rules)
    hist = tmp_path / "history"
    (hist / pol.RUN).mkdir(parents=True)
    (hist / pol.RUN / "manifest.json").write_text(json.dumps({"complete": False, "status": "in_progress"}))
    base = ["--pa-rules", pa_rules.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", (tmp_path / "creative_batch11").as_posix(), "--history-root", hist.as_posix()]
    code, out = _run(["census", "--family", "P,A", *base], capsys)
    assert code == 75 and "pending" in out["science"]
    assert not (tmp_path / "creative_batch11" / "census_PA.json").exists()


# =====================================================================================================================================
# A: entity rule, pageview rules, units
# =====================================================================================================================================


def test_entity_candidate_and_stop_list_are_frozen_and_case_insensitive():
    assert att.entity_candidate("Will Zorbab Corp release a product?", "") == "Zorbab Corp"
    assert att.entity_candidate("Will the IPO happen in March?", "") == ""
    assert att.entity_candidate("Will Invasion begin?", "") == ""
    assert att.entity_candidate("Will it rain?", "") == ""
    assert {"ipo", "invasion", "election", "ceasefire", "recession", "march", "monday", "will"} <= set(att.STOP_LIST)
    assert list(att.STOP_LIST) == sorted(att.STOP_LIST)


def pv_series(x_day, base=100, today=100, first=-40, missing=()):
    s = {}
    for d in range(x_day + first, x_day + 1):
        s[d] = base
    s[x_day] = today
    for d in missing:
        s.pop(x_day + d, None)
    return s


def test_pv_attention_rules_median_presence_history_and_zero_median():
    x = att.day_int(ep("2026-06-10"))
    first = x - 40
    r = att.pv_attention(pv_series(x, today=250), x, first)
    assert r["A"] == pytest.approx(2.5) and r["base"] == 100
    assert att.pv_attention(pv_series(x, today=250, missing=(-8,)), x, first) is None  # a missing day: unavailable, never filled
    assert att.pv_attention(pv_series(x, today=250, missing=(-3,)), x, first) is None
    assert att.pv_attention(pv_series(x, base=49, today=250), x, first) is None  # baseline < 50
    assert att.pv_attention(pv_series(x, base=50, today=250), x, first) is not None  # baseline = 50 passes
    assert att.pv_attention(pv_series(x, base=0, today=250), x, first) is None  # zero median: no division
    assert att.pv_attention(pv_series(x, today=250), x, x - 29) is None  # first non-zero day only 29 days before X
    assert att.pv_attention(pv_series(x, today=250), x, x - 30) is not None
    assert att.pv_attention(pv_series(x, today=250), x, None) is None
    # the median, not the mean, is the baseline
    s = pv_series(x, base=100, today=300)
    s[x - 1] = 100000
    assert att.pv_attention(s, x, first)["A"] == pytest.approx(3.0)
    assert att.cell_of(2.0) == "spike" and att.cell_of(1.99) == "middle" and att.cell_of(1.25) == "quiet" and att.cell_of(1.2501) == "middle" and att.cell_of(1.5, 1.5) == "spike"


def test_lag_attention_uses_days_x15_to_x7_and_the_same_rules():
    x = att.day_int(ep("2026-06-20"))
    s = {d: 100 for d in range(x - 60, x + 1)}
    s[x - 7] = 400
    assert att.lag_attention(s, x, x - 60) == pytest.approx(4.0)
    del s[x - 15]
    assert math.isnan(att.lag_attention(s, x, x - 60))  # a missing day in X-15..X-7
    s2 = {d: 100 for d in range(x - 60, x + 1)}
    assert math.isnan(att.lag_attention(s2, x, (x - 7) - 29))  # history measured from X - 7


def test_pageview_publication_rule_48h_at_the_day_boundary():
    x = att.day_int(ep("2026-06-10"))
    origin = att.day_epoch(x) + 3 * D
    assert att.pageview_usable(x, origin) and not att.pageview_usable(x, origin - 1)
    assert att.pageview_usable(x - 1, origin) and not att.pageview_usable(x + 1, origin)


def test_vwap_before_is_strictly_before_and_falls_back_six_hours():
    ts = np.array([100.0, 200.0, 300.0])
    tx = (ts, np.array([0.2, 0.4, 0.9]), np.array([1.0, 3.0, 1.0]))
    assert pa.vwap_before(tx, 300.0, 250.0, 1000.0) == pytest.approx((0.2 * 1 + 0.4 * 3) / 4)  # the print at 300 is not before 300
    assert pa.vwap_before(tx, 10_000.0, 100.0, 20_000.0) == 0.9  # nothing in the last 100 s: last print within the fallback
    assert math.isnan(pa.vwap_before(tx, 100.0))
    assert math.isnan(pa.vwap_before(tx, 100_000.0, 100.0, 1000.0))
    assert math.isnan(pa.vwap_before(None, 1.0))


def test_block_of_and_three_day_blocks():
    t0 = ep("2026-04-13")
    assert att.block_of(t0) == 0 and att.block_of(t0 + 3 * D - 1) == 0 and att.block_of(t0 + 3 * D) == 1 and att.block_of(t0 - 1) == -1


def frame_row(i, *, split="screen", stratum="vol", title="T", start="2026-04-01", end="2026-09-28", close=math.nan, event=None):
    return {"market_id": str(i), "event_key": event or f"e{i}", "stratum": stratum, "w_inv": 2.0 if stratum == "vol" else 5.0, "start_epoch": ep(start), "end_epoch": ep(end), "close_epoch": close,
            "fee_rate": 0.05, "title": title, "split": split}


def test_candidate_units_have_no_forward_values_and_apply_the_unit_rules():
    x0 = att.day_int(ep("2026-06-10"))
    series = {d: 100 for d in range(x0 - 60, x0 + 20)}
    series[x0] = 400
    # transactions: P_end(X-1) = 0.50, P_end(X) = 0.56 (VWAP in the hour before midnight)
    xs = att.day_epoch(x0)
    tx = (np.array([xs - 600, xs + D - 600, xs + 4 * D]), np.array([0.50, 0.56, 0.9]), np.array([10.0, 10.0, 10.0]))
    frame = [frame_row(1, title="T"), frame_row(2, title="T", start="2026-06-05")]  # listed < 8 d before X for market 2
    units, cnt = att.candidate_units(frame, {"T": series}, lambda mid: tx)
    mine = [u for u in units if u["x_day"] == x0]
    assert [u["market_id"] for u in mine] == ["1"]
    u = mine[0]
    assert u["A"] == pytest.approx(4.0) and u["cell"] == "spike" and u["M"] == pytest.approx(0.06) and u["big"] is True
    assert u["t"] == xs + 3 * D
    assert not (set(u) & {"p_t", "p48", "p24", "C", "C24", "dir", "early", "notional"})  # no forward value before attach_targets
    assert cnt["not_listed"] > 0
    # scheduled end < t + 72 h or already closed at t: not a unit
    f2 = [frame_row(3, title="T", end="2026-06-14"), frame_row(4, title="T", close=xs + 2 * D)]
    u2, c2 = att.candidate_units(f2, {"T": series}, lambda mid: tx)
    assert not [u for u in u2 if u["x_day"] == x0] and c2["end_or_open_condition"] > 0


def test_attach_targets_marks_early_close_and_causal_marks():
    x0 = att.day_int(ep("2026-06-10"))
    t = att.day_epoch(x0) + 3 * D
    tx = (np.array([t - 100, t + 10 * H, t + 47 * H, t + 49 * H]), np.array([0.5, 0.6, 0.65, 0.99]), np.array([1.0, 1.0, 1.0, 1.0]))
    u = {"market_id": "1", "event": "e", "stratum": "vol", "w_inv": 2.0, "x_day": x0, "x_date": "2026-06-10", "month": "2026-06", "t": t, "A": 3.0, "cell": "spike", "M": -0.05, "big": True,
         "A_lag": math.nan, "fee_rate": 0.05, "close": math.nan, "end": t + 30 * D, "block": 1}
    r = att.attach_targets([u], lambda mid: tx)[0]
    assert r["p_t"] == 0.5 and r["p48"] == pytest.approx(0.65)  # the print at t + 49 h is after the mark
    assert r["dir"] == -1.0 and r["C"] == pytest.approx(-1.0 * (0.65 - 0.5)) and r["early"] is False
    early = att.attach_targets([{**u, "close": t + 20 * H}], lambda mid: tx)[0]
    assert early["early"] is True and early["p48"] == pytest.approx(0.6)  # last transaction before the close
    assert math.isnan(att.attach_targets([{**u, "close": t + 5 * H}], lambda mid: tx)[0]["p48"])  # no transaction in [t, close)
    assert att.mde(1000, 200) == pytest.approx(3.168 * 0.08 * math.sqrt(1 / 200 + 1 / 1000) * 1.3)
    assert att.mde(1000) == pytest.approx(3.168 * 0.08 * math.sqrt(1 / 1000) * 1.3) and math.isnan(att.mde(0))


def a_units(n=1800, effect=0.03, seed=2, notional=5000.0):
    rng = random.Random(seed)
    x_lo = att.day_int(ep("2026-04-10"))
    out = []
    for i in range(n):
        x = x_lo + rng.randrange(0, 168)
        cell = rng.choice(["quiet"] * 6 + ["spike"] * 2 + ["middle"])
        a = {"quiet": 1.0, "spike": 3.0, "middle": 1.6}[cell]
        c = rng.gauss(0, 0.05) + (effect if cell == "quiet" else 0.0)
        d = 1.0 if rng.random() < 0.5 else -1.0
        pt = 0.5
        t = att.day_epoch(x) + 3 * D
        out.append({"market_id": f"m{i % 700}", "event": f"e{i % 450}", "stratum": "vol" if i % 5 else "novol", "w_inv": 2.0 if i % 5 else 6.0, "x_day": x, "x_date": pa.day_of(att.day_epoch(x)),
                    "month": pa.month_of(att.day_epoch(x)), "t": t, "A": a, "M": 0.05 * d, "big": True, "A_lag": a * (1.0 if rng.random() < 0.5 else 1.3), "fee_rate": 0.05, "close": math.nan,
                    "end": t + 40 * D, "block": att.block_of(t), "p_t": pt, "p48": pt + d * c, "p24": pt + d * c * 0.8, "early": False, "notional": notional, "dir": d, "C": c, "C24": c * 0.8})
    return out


def test_a1_advances_on_a_quiet_minus_spike_continuation_and_not_on_noise():
    r = att.a1_stat(a_units(effect=0.03), n_draws=100)
    assert r["testable"] and r["delta"] > 0.015 and r["core_ok"] and r["placebo"]["holds"]
    assert set(r["ways"]) == {"event", "day", "block"}  # three cluster ways; p is their max
    assert r["p"] == max(w["p"] for w in r["ways"].values())
    assert r["robustness"]["ok"], r["robustness"]
    assert r["advance"] is True
    assert r["robustness"]["causal_volume"]["n_units"] > 0
    n = att.a1_stat(a_units(effect=0.0, seed=4), n_draws=5, placebo=False)
    assert n["advance"] is False
    low = a_units(effect=0.03)
    r2 = att.a1_stat([{**u, "notional": 10.0} for u in low], n_draws=5, placebo=False)
    assert r2["robustness"]["causal_volume"]["ok"] is False and r2["advance"] is False  # the causal-volume check binds
    assert att.a1_stat(a_units(n=30), n_draws=3)["testable"] is False


def test_a1_floor_and_label_swap_placebo_within_day():
    r = att.a1_stat(a_units(effect=0.004, n=4000, seed=8), n_draws=5, placebo=False)
    assert r["core_ok"] is False and r["advance"] is False  # below the 1.0c floor
    us = att.sel(a_units(n=600, effect=0.0, seed=3))
    p = att.label_swap_placebo(us, n_draws=10)
    assert p["n_draws"] == 10 and "within day X" in p["note"] and p["n_units"] > 0 and att.label_swap_placebo(us, n_draws=10) == p
    assert c11.PLACEBO_SEEDS["A1_labelswap"] == 11103


def test_a2_arithmetic_token_terms_fee_both_legs_and_robustness():
    u = {"dir": 1.0, "p_t": 0.40, "p48": 0.46, "fee_rate": 0.0}
    e, x = 0.415, 0.445
    fee = 0.05 * e * (1 - e) + 0.05 * x * (1 - x)  # r = max(fee, 0.05) on both legs
    assert att.a2_net(u, half_spread=0.015) == pytest.approx(x - e - fee)
    d = {**u, "dir": -1.0}  # follow a down move: buy NO at (1 - P(t)) + 1.5c, sell at (1 - P(t+48h)) - 1.5c
    e2, x2 = 0.60 + 0.015, 0.54 - 0.015
    assert att.a2_net(d, half_spread=0.015) == pytest.approx(x2 - e2 - 0.05 * e2 * (1 - e2) - 0.05 * x2 * (1 - x2))
    assert att.a2_net(u, half_spread=0.015, fade=True) < att.a2_net(u, half_spread=0.015)
    assert att.fee_a(0.0) == 0.05 and att.fee_a(0.07) == 0.07
    r = att.a2_stat(a_units(effect=0.10, n=2500))
    assert r["testable"] and r["net_mean"] > 0.01 and r["robustness"]["half_spread_2c"]["net_mean"] < r["net_mean"]
    assert r["advance"] is True and r["reported_fade_spike"]["n"] > 0
    assert att.a2_stat(a_units(effect=0.0, n=2500, seed=12))["advance"] is False


def test_availability_by_arm_and_screen_labels_without_opening_data(tmp_path):
    av = att._availability([{**u, "C": (math.nan if i % 2 else u["C"])} for i, u in enumerate(a_units(n=300))])
    assert av["ok"] is False and av["share"] < 0.6 and set(av["by_arm"]) == {"spike", "quiet"}
    res = att.screen_a(tmp_path, {"A": {"label_A1": "not testable (entity map)"}})
    assert res["A1"]["p"] == 1.0 and res["A2"]["testable"] is False


# =====================================================================================================================================
# A fetch jobs with fake transports
# =====================================================================================================================================


def zname(i):
    return "Zorb" + chr(97 + i % 26) + chr(97 + (i // 26) % 26) + " Corp"


class AttnWorld:
    def __init__(self, n=24):
        self.markets = []
        for i in range(n):
            end = ep("2026-06-01") + (i % 2) * D + 3600 * (i % 10)
            m = gamma_market(5000 + i, end, politics=False, life_d=55, event=f"ev{i // 2}")
            m["question"] = f"Will {zname(i)} announce a plan?"
            m["volumeNum"] = 20000.0 if i % 4 else 100.0
            m["feeType"] = "culture_fees"
            m["events"][0]["title"] = f"{zname(i)} news"
            self.markets.append(m)
        self.by_cid = {m["conditionId"]: m for m in self.markets}
        self.n = {"gamma": 0, "data": 0}
        self.wn = {"summary": 0, "pv": 0}

    def __call__(self, url, params):
        if url == hb.GAMMA_MARKETS:
            self.n["gamma"] += 1
            lo, hi = cm.ep(params["end_date_min"]), cm.ep(params["end_date_max"])
            assert "volume_num_min" not in params  # no volume filter in the walk
            rows = [m for m in self.markets if lo <= cm.ep(m["endDate"]) <= hi]
            rows = sorted(rows, key=lambda m: int(m["id"]))[params["offset"]: params["offset"] + params["limit"]]
            return _jr([{k: v for k, v in m.items() if k != "_pol"} for m in rows])
        if url == hb.DATA_TRADES:
            self.n["data"] += 1
            m = self.by_cid[params["market"]]
            end = cm.ep(m["endDate"])
            trades = [{"timestamp": int(end - 40 * D + k * 6 * H), "outcomeIndex": 0, "price": 0.5, "size": 5.0, "transactionHash": f"0x{m['id']}_{k}"} for k in range(100)]
            trades.sort(key=lambda x: -x["timestamp"])
            return _jr(trades[params["offset"]: params["offset"] + params["limit"]])
        return 404, b"", {}

    def wiki(self, url, params):
        if url.startswith(att.WIKI_SUMMARY):
            self.wn["summary"] += 1
            name = url[len(att.WIKI_SUMMARY):]
            if name.startswith("Zorbzz"):
                return 404, b"{}", {}
            return 200, json.dumps({"type": "standard", "title": name.replace("_", " "), "titles": {"canonical": name}, "description": "a company"}).encode(), {}
        if url.startswith(att.WIKI_PAGEVIEWS):
            self.wn["pv"] += 1
            days = []
            d = datetime(2026, 1, 1, tzinfo=UTC)
            for k in range(273):
                days.append({"timestamp": (d.replace(day=1) if False else datetime.fromtimestamp(d.timestamp() + k * D, UTC)).strftime("%Y%m%d00"), "views": 100 + (k % 7)})
            return 200, json.dumps({"items": days}).encode(), {}
        return 404, b"", {}


@pytest.fixture()
def aframe(tmp_path):
    w = AttnWorld()
    hist = tmp_path / "history"
    m = att.attn_frame(hist, w, w.wiki, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, days=["2026-06-01", "2026-06-02"], data_dumps=None, **NOSLEEP)
    assert m["status"] == att.FRAME_STATUS, m
    return {"hist": hist, "rdir": hist / att.RUN, "world": w, "tmp": tmp_path}


def test_attn_frame_strata_split_audit_and_no_volume_filter(aframe):
    rdir = aframe["rdir"]
    scr = att.read_frame(rdir, "screen", job="census")
    hold = list(c11.read_csv_gz(rdir / "holdout" / "frame_hold.csv.gz"))
    allr = scr + hold
    assert len(allr) == 24 and {r["stratum"] for r in allr} == {"vol", "novol"}  # the novol stratum comes from the same walk
    assert all(r["title"].startswith("Zorb") for r in allr)
    # the event-hash split keeps an event's markets together
    ev_split: dict[str, set] = {}
    for r in scr:
        ev_split.setdefault(r["event_key"], set()).add("screen")
    for r in hold:
        ev_split.setdefault(r["event_key"], set()).add("holdout")
    assert all(len(v) == 1 for v in ev_split.values())
    sp = json.loads((rdir / "split.json").read_text())["report"]["strata"]
    assert sp["vol"]["sampled"] + sp["novol"]["sampled"] == 24 and sp["vol"]["w_inv"] > 0
    with pytest.raises(c11.Refused):
        att.read_frame(rdir, "holdout", job="screen-A")
    assert (rdir / "audit_sample.csv").exists() and att.audit_ids_of(rdir) <= {r["market_id"] for r in scr}
    # volumeNum is stored only as the boolean
    hdr = gzip.open(rdir / "frame.csv.gz", "rt").readline()
    assert "vol_ok" in hdr and "volume" not in hdr.replace("vol_ok", "")


def test_attn_frame_wikipedia_404_fails_the_entity_rule_and_event_cap(tmp_path):
    w = AttnWorld(n=6)
    for m in w.markets:
        m["events"][0]["id"] = "evSAME"
    hist = tmp_path / "history"
    m = att.attn_frame(hist, w, w.wiki, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, days=["2026-06-01", "2026-06-02"], **NOSLEEP)
    assert m["status"] == att.FRAME_STATUS
    n = sum(1 for sp in ("frame.csv.gz", "holdout/frame_hold.csv.gz") for _ in c11.read_csv_gz(hist / att.RUN / sp))
    assert n == att.MAX_PER_EVENT  # at most 3 per event


def test_attn_frame_smoke_stall_and_resume(tmp_path):
    w = AttnWorld(n=6)
    hist = tmp_path / "history"
    m = att.attn_frame(hist, w, w.wiki, rules_sha="r" * 64, smoke_path=_smoke(tmp_path, wiki_lag=False), exclusion_keys_path=_keys(tmp_path), now=1.8e9, days=["2026-06-01"], **NOSLEEP)
    assert m["status"] == c11.STALL_NOT_RUN_SOURCE and w.n["gamma"] == 0
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 1

    h2 = tmp_path / "h2"
    m1 = att.attn_frame(h2, w, w.wiki, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, days=["2026-06-01", "2026-06-02"], should_stop=stop, **NOSLEEP)
    assert m1["status"] == "in_progress"
    m2 = att.attn_frame(h2, w, w.wiki, rules_sha="r" * 64, smoke_path=_smoke(tmp_path), exclusion_keys_path=_keys(tmp_path), now=1.8e9, days=["2026-06-01", "2026-06-02"], **NOSLEEP)
    assert m2["status"] == att.FRAME_STATUS


def write_labels(path: Path, ids, ok_share=1.0):
    ids = sorted(ids)
    path.write_text("market_id,label\n" + "\n".join(f"{m},{1 if i < ok_share * len(ids) else 0}" for i, m in enumerate(ids)) + "\n")


def test_attn_data_waits_for_labels_with_idle_heartbeat_then_fetches(aframe):
    w, hist, tmp = aframe["world"], aframe["hist"], aframe["tmp"]
    labels = tmp / "labels.csv"
    r1 = att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9, labels_path=labels, **NOSLEEP)
    assert r1["status"] == "idle_heartbeat" and w.n["data"] == 0  # first call: heartbeat (exit 0 resets the queue's tempfail count)
    with pytest.raises(c11.NotNow):
        att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9 + 60, labels_path=labels, **NOSLEEP)
    write_labels(labels, att.audit_ids_of(aframe["rdir"]) | {"extra"})
    with pytest.raises(c11.Refused):
        att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9, labels_path=labels, **NOSLEEP)  # labels must cover exactly the audit sample
    write_labels(labels, att.audit_ids_of(aframe["rdir"]))
    with pytest.raises(c11.Refused):
        att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9, labels_path=labels, is_committed=lambda p: False, **NOSLEEP)
    m = att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9, labels_path=labels, is_committed=lambda p: True, data_dumps=None, **NOSLEEP)
    assert m["status"] == att.DATA_STATUS, m
    rdir = aframe["rdir"]
    pv = att.load_pageviews(rdir, "screen", job="census")
    assert pv and all(len(v) == 273 for v in pv.values())
    mk = att.load_markets(rdir)
    assert len(mk) == 24 and all(r["status"] == "ok" for r in mk.values())
    with pytest.raises(c11.Refused):
        att.load_pageviews(rdir, "holdout", job="screen-A")
    with pytest.raises(c11.Refused):
        att.tx_loader(rdir, "holdout", job="census")
    # transactions are aggregated by hash and carry no side / wallet / hash column
    some = next(rdir.glob("screen/*.tx.csv.gz"))
    assert gzip.open(some, "rt").readline().strip() == "ts,price,size"


def test_attn_data_disk_headroom_is_pending_and_disk_budget_state(aframe):
    w, hist, tmp = aframe["world"], aframe["hist"], aframe["tmp"]
    labels = tmp / "labels.csv"
    write_labels(labels, att.audit_ids_of(aframe["rdir"]))
    dd = tmp / "dd"
    dd.mkdir()
    with pytest.raises(c11.NotNow):
        att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9, labels_path=labels, data_dumps=dd, free_fn=lambda p: 4 * 1024**3, **NOSLEEP)
    m = att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9, labels_path=labels, disk_cap=1, **NOSLEEP)
    assert m["status"] == cm.DISK_BUDGET_TOKEN


def test_census_a_counts_only_never_attaches_targets_and_gates(aframe, monkeypatch):
    w, hist, tmp = aframe["world"], aframe["hist"], aframe["tmp"]
    labels = tmp / "labels.csv"
    write_labels(labels, att.audit_ids_of(aframe["rdir"]), ok_share=0.75)
    att.attn_data(hist, w, w.wiki, rules_sha="r" * 64, now=1.8e9, labels_path=labels, is_committed=lambda p: True, **NOSLEEP)

    def boom(*a, **k):
        raise AssertionError("the census must not attach forward values")

    monkeypatch.setattr(att, "attach_targets", boom)
    doc = att.census_a(aframe["rdir"], labels, is_committed=lambda p: True)
    assert doc["counts_only"] and doc["GA0"]["pass"] is False and doc["GA0"]["precision"] < 0.80
    assert doc["label_A1"] == "not testable (entity map)" and doc["a_runs"] is False
    flat = json.dumps(doc, default=str)
    for bad in att.CENSUS_FORBIDDEN:
        assert f'"{bad}"' not in flat
    write_labels(labels, att.audit_ids_of(aframe["rdir"]), ok_share=0.80)
    d2 = att.census_a(aframe["rdir"], labels, is_committed=lambda p: True)
    assert d2["GA0"]["pass"] is True and d2["label_A1"].startswith("not testable (GA")  # a tiny fixture cannot meet GA
    assert d2["coverage_audit"]["share"] == 1.0 and "A1" in d2["mde"]
    missing = att.census_a(aframe["rdir"], tmp / "nolabels.csv")
    assert missing["GA0"]["pass"] is False and missing["GA0"]["error"].startswith("audit labels")


def test_rep_a_refuses_unverified_seal_and_seals_p_a_pending(aframe):
    with pytest.raises(c11.Refused):
        att.rep_a(aframe["rdir"], {"A": {}}, ("A1",), 2, seals_dir=aframe["tmp"] / "seals")
    assert att.seal_rows(aframe["rdir"]) is not None


def test_results_are_write_once_and_log_counts_one_test_per_family(tmp_path):
    p = tmp_path / "results_P.json"
    c11.write_results_once(p, {"P1": {"p": 0.5}})
    with pytest.raises(c11.Refused):
        c11.write_results_once(p, {"P1": {"p": 0.1}})
    tp = tmp_path / "trials.jsonl"
    for fam, tid in (("P", "P1"), ("A", "A2")):
        c11.log_test(fam, tid, {"p": 0.2, "testable": False, "advance": False}, trials_path=tp)
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    counts = [x for x in lines if x["kind"] == "ml_explain"]
    assert [c["source"] for c in counts] == ["creative_batch_11:P", "creative_batch_11:A"] and all(c["n_tests"] == 1 for c in counts)
    assert all(x["p"] == 1.0 for x in lines if x["kind"] == "cb11_test")  # a test behind a failed gate is counted with p = 1


def test_batch_holm_over_six_with_p_and_a_names_and_unknown_names_refused():
    r = c11.batch_holm_label({"P1": 0.0005, "A1": 0.02, "W1": 0.001})
    assert r["k"] == 6 and r["tests"]["P1"]["reject"] is True and r["tests"]["A1"]["reject"] is False and set(r["not_run_as_p1"]) == {"W2", "P2", "A2"}
    with pytest.raises(c11.Refused):
        c11.batch_holm_label({"P3": 0.1})


def test_screen_pa_writes_once_and_logs_counted_lines(tmp_path, capsys):
    pa_rules = tmp_path / "pa_rules.json"
    pa.write_pa_rules(pa_rules)
    root = tmp_path / "creative_batch11"
    hist = tmp_path / "history"
    root.mkdir(parents=True)
    (hist / pol.RUN).mkdir(parents=True)
    # a stalled fetch (declared end state) carries its label into counted not-testable lines
    c11.write_stall(hist / pol.RUN, c11.STALL_NOT_RUN_SOURCE, "smoke", "not testable (source)")
    (root / "census_PA.json").write_text(json.dumps({"P": {"label_P1": "not testable (source)", "label_P2": "not testable (source)"}, "A": {}}))
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"W": {}, "PA": pa.freeze_part_pa()}))
    tp = tmp_path / "trials.jsonl"
    argv = ["screen", "--family", "P", "--pa-rules", pa_rules.as_posix(), "--allow-uncommitted-rules", "--standalone", "--root", root.as_posix(), "--history-root", hist.as_posix(),
            "--freeze-spec", spec.as_posix(), "--trials-path", tp.as_posix()]
    code, out = _run(argv, capsys)
    assert code == 0 and out["status"] == "screen_P_complete" and out["P1"]["p"] == 1.0
    lines = [json.loads(x) for x in tp.read_text().splitlines()]
    assert sum(1 for x in lines if x["kind"] == "ml_explain") == 2 and all(x["source"] == "creative_batch_11:P" for x in lines if x["kind"] == "ml_explain")
    code, out = _run(argv, capsys)
    assert code == 2 and "exists" in out["refused"] or "write-once" in out["refused"] or "already" in out["refused"]
    code, out = _run(["stage1-label", "--root", root.as_posix(), "--standalone", "--allow-uncommitted-rules"], capsys)
    assert code == 0 and out["batch_holm"]["k"] == 6 and "P1" in out["batch_holm"]["not_run_as_p1"]


def test_totals_of_declared_output_caps_stay_within_the_family_budget():
    caps = [run_cb11.DECLARED_DISK_CAP_GB[k] for k in ("exclusion-keys", "w-frame", "w-prints", "w-censoring", "pol-frame", "pol-prices", "attn-frame", "attn-data")]
    assert sum(caps) <= c11.TOTAL_OUTPUT_CAP_GB + 0.01 and run_cb11.DECLARED_DISK_CAP_GB["attn-data"] == 0.12
