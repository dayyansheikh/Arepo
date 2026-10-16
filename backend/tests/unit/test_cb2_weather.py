# ruff: noqa: E501
"""CB2-W (weather favourites): fixtures only, no network, no real data. See CREATIVE_BATCH_2.md section 4.4."""

from __future__ import annotations

import argparse
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import battery2, h5_seal, provenance
from astrolabe.research_lab import cb2_weather as w
from astrolabe.research_lab import history_backfill as hb

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC).timestamp()
KEY = b"k" * 32


def ep(s: str) -> float:
    return w.parse_when(s)


# ------------------------------------------------------------------------------- text rules
def test_temp_re_fixtures():
    p = w.parse_title("Highest temperature in NYC on October 8?")
    assert p == {"direction": "Highest", "city": "nyc", "title_date": "October 8"}
    p = w.parse_title("Lowest temperature in Mexico City on March 3, 2026?")
    assert p["city"] == "mexico-city" and p["direction"] == "Lowest" and p["title_date"] == "March 3, 2026"
    for bad in ("Will it snow in NYC on October 8?", "Precipitation in Seattle in October?",
                "Number of tornadoes in 2026", "Highest temperature in NYC on October 8", None,
                "highest temperature in NYC on October 8?"):
        assert w.parse_title(bad) is None


def test_text_rules_file_matches_code_and_is_in_declaration():
    doc = json.loads(w.TEXT_RULES_FILE.read_text())
    assert doc == {"temp_re_sha256": w.TEMP_RE_SHA256, "tz_table_sha256": w.TZ_TABLE_SHA256}
    d = w.declaration_weather()
    assert d["temp_re"]["pattern"] == w.TEMP_RE and d["temp_re"]["sha256"] == w.TEMP_RE_SHA256
    assert d["tz_table"]["table"] == w.TZ_TABLE and d["tz_table"]["sha256"] == w.TZ_TABLE_SHA256
    assert len(w.TZ_TABLE) == 49
    assert w.declaration_sha256_weather() == w.declaration_sha256_weather()


def test_declaration_hash_changes_with_regex_and_tz(monkeypatch):
    base = w.declaration_sha256_weather()
    monkeypatch.setattr(w, "TEMP_RE", w.TEMP_RE + "x")
    assert w.declaration_sha256_weather() != base
    monkeypatch.setattr(w, "TEMP_RE", r"^(Highest|Lowest) temperature in (.+?) on (.+?)\?$")
    assert w.declaration_sha256_weather() == base
    monkeypatch.setitem(w.TZ_TABLE, "nowhere", "UTC")
    assert w.declaration_sha256_weather() != base


def test_require_text_rules_refuses_mismatch(tmp_path):
    p = tmp_path / "rules.json"
    with pytest.raises(w.Refused, match="not found"):
        w.require_text_rules(p, require_committed=False)
    p.write_text(json.dumps({"temp_re_sha256": "0", "tz_table_sha256": w.TZ_TABLE_SHA256}))
    with pytest.raises(w.Refused, match="mismatch"):
        w.require_text_rules(p, require_committed=False)
    p.write_text(json.dumps(w.text_rules_doc()))
    w.require_text_rules(p, require_committed=False)
    with pytest.raises(w.Refused, match="not committed"):
        w.require_text_rules(p, require_committed=True)


def test_runner_refuses_sealed_run_ids():
    for rid in ("h5_cb1", "h5_cb1_ladders", "h3_power", "h4_seal"):
        with pytest.raises(w.Refused):
            w.refuse_run_id(rid)
    assert w.refuse_run_id("h6_weather") == "h6_weather"


# ------------------------------------------------------------------------------- local_class
def _t(local_str: str, zone: str) -> float:
    from zoneinfo import ZoneInfo

    return datetime.strptime(local_str, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(zone)).timestamp()


def test_local_class_us_europe_asia_highest_and_lowest():
    # boundaries, Highest
    assert w.local_class("nyc", "Highest", "2026-10-08", _t("2026-10-08 11:59", "America/New_York")) == "pre"
    assert w.local_class("nyc", "Highest", "2026-10-08", _t("2026-10-08 12:00", "America/New_York")) == "during"
    assert w.local_class("nyc", "Highest", "2026-10-08", _t("2026-10-08 15:59", "America/New_York")) == "during"
    assert w.local_class("nyc", "Highest", "2026-10-08", _t("2026-10-08 16:00", "America/New_York")) == "post"
    # Lowest
    assert w.local_class("paris", "Lowest", "2026-10-08", _t("2026-10-08 04:59", "Europe/Paris")) == "pre"
    assert w.local_class("paris", "Lowest", "2026-10-08", _t("2026-10-08 05:00", "Europe/Paris")) == "during"
    assert w.local_class("paris", "Lowest", "2026-10-08", _t("2026-10-08 09:00", "Europe/Paris")) == "post"
    # East Asia execution 08:00Z = 17:00 Tokyo: post-extreme for Highest, Lowest
    ts = datetime(2026, 10, 8, 8, 0, tzinfo=UTC).timestamp()
    assert w.local_class("tokyo", "Highest", "2026-10-08", ts) == "post"
    assert w.local_class("tokyo", "Lowest", "2026-10-08", ts) == "post"
    # Chicago 08:00Z = 03:00 local: pre for both
    assert w.local_class("chicago", "Highest", "2026-10-08", ts) == "pre"
    assert w.local_class("chicago", "Lowest", "2026-10-08", ts) == "pre"
    # a later local date is post-extreme; an earlier one is pre; unknown city/date
    assert w.local_class("tokyo", "Highest", "2026-10-07", ts) == "post"
    assert w.local_class("chicago", "Highest", "2026-10-09", ts) == "pre"
    assert w.local_class("atlantis", "Highest", "2026-10-08", ts) == "tz_unknown"
    assert w.local_class("nyc", "Highest", None, ts) == "date_unknown"


def test_title_date_year_inference():
    e = ep("2026-01-02T12:00:00Z")
    assert w.parse_title_date("December 31", e) == "2025-12-31"
    assert w.parse_title_date("January 2", e) == "2026-01-02"
    assert w.parse_title_date("October 8, 2025", e) == "2025-10-08"
    assert w.parse_title_date("not a date", e) is None


# ------------------------------------------------------------------------------- split
def _ev(eid, city, day, hh=12, direction="Highest", title_date=None):
    end = ep(f"{day}T{hh:02d}:00:00Z")
    td = title_date or datetime.fromisoformat(day).strftime("%B ") + str(datetime.fromisoformat(day).day)
    return {"event_id": str(eid), "city": city, "end_epoch": end, "title_date": td,
            "title_date_iso": datetime.fromisoformat(day).date().isoformat()}


def _events(n_days=100, cities=("nyc", "london", "tokyo")):
    out, i = [], 0
    d0 = datetime(2026, 1, 1, tzinfo=UTC)
    for k in range(n_days):
        day = (d0 + timedelta(days=k)).strftime("%Y-%m-%d")
        for c in cities:
            for dr in ("Highest", "Lowest"):
                out.append({**_ev(i, c, day), "direction": dr})
                i += 1
    return out


def test_split_deterministic_disjoint_and_fraction():
    evs = _events()
    a, b = w.split_h6(evs), w.split_h6(list(reversed(evs)))
    assert a == b
    s, h, e = set(a["screen"]), set(a["holdout"]), set(a["embargo"])
    assert not (s & h) and not (s & e) and not (h & e) and len(s | h | e) == len(evs)
    assert len(h) <= 0.40 * len(evs)
    assert len(h) > 0.35 * len(evs)  # smallest date: the HOLDOUT is as large as the rule allows
    assert len(e) == 2 * 6  # two embargo days, 3 cities x 2 directions
    d = datetime.fromisoformat(a["d_split"]).date()
    keyd = {e_["event_id"]: datetime.fromtimestamp(e_["end_epoch"], UTC).date() for e_ in evs}
    assert all(keyd[i] >= d for i in h) and all(keyd[i] < d - timedelta(days=2) for i in s)


def test_split_keeps_city_day_events_together_even_with_different_end_times():
    evs = _events(30)
    # Lowest event of each city-day ends 18 hours later, crossing midnight into the next UTC date
    for e in evs:
        if e["direction"] == "Lowest":
            e["end_epoch"] += 18 * 3600
    sp = w.split_h6(evs)
    half = {i: "s" for i in sp["screen"]} | {i: "h" for i in sp["holdout"]} | {i: "e" for i in sp["embargo"]}
    by = {}
    for e in evs:
        by.setdefault((e["city"], e["title_date_iso"]), set()).add(half[e["event_id"]])
    assert all(len(v) == 1 for v in by.values())


def test_split_uses_only_end_city_and_title_date():
    evs = _events(40)
    slim = [{k: e[k] for k in ("event_id", "city", "end_epoch", "title_date", "title_date_iso")} for e in evs]
    assert w.split_h6(slim) == w.split_h6(evs)
    # unparsed title date: falls back to raw text and end year
    slim2 = [{**e, "title_date_iso": None} for e in slim]
    assert w.split_h6(slim2)["d_split"] == w.split_h6(evs)["d_split"]


def test_split_edge_cases():
    assert w.split_h6([])["d_split"] is None
    one = [_ev(1, "nyc", "2026-03-03")]
    sp = w.split_h6(one)
    assert sp["holdout"] == [] and sp["embargo"] == ["1"] and sp["screen"] == []


# ------------------------------------------------------------------------------- fake Gamma / CLOB / Data
class FakeNet:
    """Scripted Gamma events + CLOB prices + Data trades. Events: dict id -> raw."""

    def __init__(self, events: list[dict], cap_rows: int | None = None, trade_rows: int = 3,
                 trade_base: int = 1_700_000_000):
        self.events = events
        self.calls: list[tuple[str, dict]] = []
        self.cap_rows = cap_rows  # if set, every window returns this many rows (forces the cap)
        self.trade_rows = trade_rows
        self.trade_base = trade_base
        self.status_429_for = 0

    def __call__(self, url, params):
        self.calls.append((url, dict(params) if isinstance(params, dict) else list(params)))
        if self.status_429_for > 0:
            self.status_429_for -= 1
            return 429, b"", {"Retry-After": "0"}
        if url == w.GAMMA_EVENTS:
            p = dict(params)
            closed = p["closed"] == "true"
            a = w.parse_when(p["end_date_min"])
            b = w.parse_when(p["end_date_max"])
            rows = [e for e in self.events if bool(e["closed"]) == closed and a <= w._parse_end(e["endDate"]) <= b]
            if self.cap_rows:
                rows = rows * self.cap_rows
            off, lim = int(p["offset"]), int(p["limit"])
            return 200, json.dumps(rows[off:off + lim]).encode(), {}
        if url == hb.CLOB_PRICES:
            tok = params["market"]
            a, b = int(params["startTs"]), int(params["endTs"])
            base = 0.4 + (int(tok[-1]) % 5) * 0.1 if tok[-1].isdigit() else 0.3
            pts = [{"t": t, "p": base} for t in range(a, b, 600)]
            return 200, json.dumps({"history": pts}).encode(), {}
        if url == hb.DATA_TRADES:
            if int(params["offset"]) > 0:
                return 200, b"[]", {}
            rows = [{"timestamp": self.trade_base + i, "side": "BUY", "size": 1, "price": 0.5, "outcomeIndex": 0,
                     "proxyWallet": "0x1", "transactionHash": f"h{params['market']}{i}", "asset": "a"}
                    for i in range(self.trade_rows)]
            return 200, json.dumps(rows).encode(), {}
        return 404, b"[]", {}


def gev(eid, day, city="NYC", direction="Highest", nm=5, closed=True, neg=True, title=None, hh=12):
    end = f"{day}T{hh:02d}:00:00Z"
    ms = []
    for j in range(nm):
        mid = f"{eid}{j}"
        ms.append({"id": mid, "conditionId": f"c{mid}", "clobTokenIds": json.dumps([f"tok{mid}", f"tn{mid}"]),
                   "groupItemTitle": f"{60 + j}F", "negRisk": neg, "outcomePrices": json.dumps(["1", "0"] if j == 2 else ["0", "1"]),
                   "closed": closed, "closedTime": end})
    return {"id": str(eid), "title": title or f"{direction} temperature in {city} on {datetime.fromisoformat(day).strftime('%B')} {datetime.fromisoformat(day).day}?",
            "endDate": end, "negRisk": neg, "closed": closed, "markets": ms}


def fetch_kw(tmp_path, net, **kw):
    base = dict(n_events=100, seed="s", end_from="2026-09-01", end_before="2026-10-22T00:00Z",
                census_ex=w.T_CENSUS_EX, exclude_runs=[], h5_seal_copies=[], rps=1000.0, key=KEY,
                now=NOW, sleep=lambda s: None, live_check=None, wall_clock=lambda: NOW,
                cap_at="2026-10-22T00:00Z", disk_cap=50 * 1024**2)
    base.update(kw)
    return w.weather_fetch(tmp_path, "h6_weather", net, **base)


def scenario():
    evs = [gev(1, "2026-09-10"), gev(2, "2026-09-10", direction="Lowest"), gev(3, "2026-09-11", city="London"),
           gev(4, "2026-10-09"),  # census day
           gev(5, "2026-09-12", title="Will it snow in NYC on September 12?"),
           gev(6, "2026-09-13", nm=3), gev(7, "2026-09-13", neg=False),
           gev(8, "2026-09-14", closed=False),  # open at fetch: kept, censored
           gev(9, "2026-10-14"),  # end_at >= T_fetch - 3d: outside the end window
           gev(10, "2026-09-15"), gev(11, "2026-08-01")]  # before end_from
    return evs


# ------------------------------------------------------------------------------- frame / walk
def test_frame_rules_each_counted(tmp_path):
    net = FakeNet(scenario())
    hist_dir = tmp_path / "h2_main"
    hist_dir.mkdir()
    import pandas as pd

    pd.DataFrame({"market_id": ["100"]}).to_csv(hist_dir / "sample.csv.gz", index=False)  # event 10 member 100
    h5 = tmp_path / "h5_cb1_SEAL.json"
    h5.write_text(json.dumps({"files": {"prices/30.csv.gz": "x", "trades/31.csv.gz": "y", "manifest.json": "z"}}))
    m = fetch_kw(tmp_path, net, exclude_runs=["h2_main"], h5_seal_copies=[h5])
    fr = m["frame_report"]
    assert fr["census_ex"] == 1 and fr["not_temperature_title"] == 1 and fr["member_count"] == 1
    assert fr["not_neg_risk"] == 1 and fr["history_sample_overlap"] == 1 and fr["h5_overlap"] == 1
    assert fr["closed_true_events"] >= 1 and fr["closed_false_events"] == 1
    assert fr["kept"] == 3 and fr["kept_closed_false"] == 1  # events 1, 2 and the open event 8
    ids = {e["event_id"] for e in w.load_jsonl_gz(tmp_path / "h6_weather" / "events.jsonl.gz")}
    assert ids == {"1", "2", "8"}  # closed=false kept as censored
    assert not ids & {"4", "5", "6", "7", "9", "10", "11"}


def test_events_file_has_no_outcomes_and_guarded_file_has(tmp_path):
    net = FakeNet(scenario())
    fetch_kw(tmp_path, net)
    rdir = tmp_path / "h6_weather"
    txt = (rdir / "events.jsonl.gz").read_bytes()
    import gzip

    body = gzip.decompress(txt).decode()
    for col in w.OUTCOME_COLUMNS + ("outcomePrices", "closedTime"):
        assert col not in body
    import pandas as pd

    g = pd.read_csv(rdir / w.OUTCOME_FILE, dtype=str)
    assert {"market_id", "outcome_prices", "closed_time"} <= set(g.columns) and len(g) > 0
    for f in (rdir / "prices").iterdir():
        assert "outcome" not in f.read_bytes().decode("latin1")


def test_walk_closed_false_and_capped_window_dropped():
    evs = [gev(1, "2026-09-10"), gev(2, "2026-09-10", closed=False)]
    lim = hb.Limiter(FakeNet(evs), rps=1000.0, sleep=lambda s: None, live_check=None)
    start, end = datetime(2026, 9, 7, tzinfo=UTC), datetime(2026, 9, 14, tzinfo=UTC)
    got, rep = w.walk_weather_events(lim, start, end)
    assert set(got) == {"1", "2"} and got["2"]["closed_mode"] is False and rep["closed_false_events"] == 1
    assert rep["windows_dropped_capped"] == 0
    # a window that is capped at every size is split to 1 day, then dropped and counted
    capped = FakeNet(evs, cap_rows=2100)  # every non-empty window returns 2,100 rows: the offset cap is hit
    lim2 = hb.Limiter(capped, rps=1000.0, sleep=lambda s: None, live_check=None)
    got2, rep2 = w.walk_weather_events(lim2, datetime(2026, 9, 9, tzinfo=UTC),
                                       datetime(2026, 9, 11, tzinfo=UTC), modes=(True,))
    assert rep2["windows_dropped_capped"] >= 1 and rep2["split"] >= 1 and got2 == {}
    assert rep2["rows_in_dropped_windows"] > 0 and rep2["dropped_capped_by_day"]


def test_sample_is_seeded_and_order_independent():
    evs = [{"event_id": str(i)} for i in range(50)]
    a = w.draw_sample(evs, 10, "x")
    assert a == w.draw_sample(list(reversed(evs)), 10, "x") and a != w.draw_sample(evs, 10, "y")


# ------------------------------------------------------------------------------- fetch: cap, T_seal, health, 429
def test_prices_and_trades_at_or_after_cap_are_dropped_and_counted(tmp_path):
    net = FakeNet([gev(1, "2026-09-10")])
    cap = ep("2026-09-10T00:00:00Z")  # inside the price window [end-72h, end+6h]
    m = fetch_kw(tmp_path, net, cap_at="2026-09-10T00:00Z", census_ex=w.T_CENSUS_EX)
    rec = [json.loads(x) for x in (tmp_path / "h6_weather" / "progress.jsonl").read_text().splitlines()][0]
    assert any(mm["dropped_price_rows_post_cap"] > 0 for mm in rec["markets"].values())
    import pandas as pd

    for f in (tmp_path / "h6_weather" / "prices").iterdir():
        d = pd.read_csv(f)
        assert (d["t"] < cap).all()
    assert m["counts"]["price_rows_dropped_post_cap"] > 0
    # trades: all fake trades are timestamped 2023 (< cap), so none is dropped here; test the cap with ts_cap
    rows, st = hb.fetch_trades(hb.Limiter(FakeNet([]), rps=1000.0, sleep=lambda s: None, live_check=None),
                               "c", KEY, 100, ts_cap=1_700_000_000)
    assert [r[0] for r in rows] == [1_700_000_000] and st["dropped_post_cap"] == 2


def test_trade_rows_at_cap_are_dropped(tmp_path):
    net = FakeNet([gev(1, "2026-09-10")], trade_base=int(NOW) - 1)  # ts = cap-1 (kept), cap, cap+1 (dropped)
    fetch_kw(tmp_path, net)
    recs = [json.loads(x) for x in (tmp_path / "h6_weather" / "progress.jsonl").read_text().splitlines()]
    tr = [mm["trades"] for mm in recs[0]["markets"].values() if mm["trades"]]
    assert tr and all(t["n"] == 1 and t["dropped_post_cap"] == 2 for t in tr)


def test_weather_fetch_refuses_at_or_after_t_seal(tmp_path):
    net = FakeNet(scenario())
    m = fetch_kw(tmp_path, net, wall_clock=lambda: w.T_SEAL_EPOCH)
    assert m["stopped"] == "t_seal_passed" and not net.calls
    # mid-chunk passage stops before the next event
    ticks = iter([NOW, NOW, NOW, NOW, NOW] + [w.T_SEAL_EPOCH] * 1000)
    m2 = fetch_kw(tmp_path / "b", FakeNet(scenario()), wall_clock=lambda: next(ticks))
    assert m2["stopped"] == "t_seal_passed" or m2["counts"]["events_done"] < 3


def test_fetch_is_resumable_and_complete(tmp_path):
    net = FakeNet(scenario())
    def two_done():
        pf = tmp_path / "h6_weather" / "progress.jsonl"
        return pf.exists() and len(pf.read_text().splitlines()) >= 2

    m1 = fetch_kw(tmp_path, net, should_stop=two_done)
    assert m1["stopped"] == "should_stop" and m1["counts"]["events_done"] == 2
    n_before = len(net.calls)
    m2 = fetch_kw(tmp_path, net)
    assert m2.get("token") == w.COMPLETE_TOKEN and m2["counts"]["events_done"] == m2["n_events_sample"]
    assert len(net.calls) > n_before
    m3 = fetch_kw(tmp_path, net)  # idempotent: nothing left to fetch
    assert m3.get("token") == w.COMPLETE_TOKEN
    # trades only for the buckets ranked 1-2 at either origin
    tr = list((tmp_path / "h6_weather" / "trades").iterdir())
    pr = list((tmp_path / "h6_weather" / "prices").iterdir())
    assert 0 < len(tr) < len(pr)


def test_collector_health_stale_or_incomplete_pauses_chunk_as_transient(tmp_path):
    snap = tmp_path / "snapshots"

    def mk(name, started, state):
        d = snap / name
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"started_utc": started, "state": state}))

    fresh = datetime.fromtimestamp(NOW - 3600, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale = datetime.fromtimestamp(NOW - 3 * 3600, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    mk("a", fresh, "complete")
    assert w.collector_healthy(snap, NOW, lock_busy=lambda: False) == (True, "ok")
    mk("b", fresh, "incomplete:time_cap")
    ok, why = w.collector_healthy(snap, NOW, lock_busy=lambda: False)
    assert not ok and "incomplete" in why
    assert w.collector_healthy(snap, NOW, lock_busy=lambda: True)[0] is True  # a pass is running
    import shutil

    shutil.rmtree(snap)
    mk("c", stale, "complete")
    ok, why = w.collector_healthy(snap, NOW, lock_busy=lambda: False)
    assert not ok and "2.75" in why
    # the fetch ends the chunk as transient and fetches nothing
    net = FakeNet(scenario())
    m = fetch_kw(tmp_path / "run", net, snapshot_root=snap)
    assert m["stopped"].startswith("paused_collector_health") and m["transient"] is True
    assert not net.calls


def test_429_policy_halves_rps_once_and_ends_chunk_after_50():
    sent = []

    def tr(url, params):
        sent.append(1)
        return (429 if len(sent) % 10 == 0 else 200), b"[]", {"Retry-After": "0"}

    pol = w.RatePolicy(tr, clock=lambda: 1000.0, min_requests=50, chunk_limit=50)
    lim = hb.Limiter(pol, rps=100.0, sleep=lambda s: None, live_check=None)
    pol.limiter = lim
    gap0 = lim.min_gap
    for _ in range(49):
        pol(w.GAMMA_EVENTS, {})
    assert not pol.halved and lim.min_gap == gap0
    pol(w.GAMMA_EVENTS, {})  # 50 requests in the window and 10% are 429
    assert pol.halved and lim.min_gap == 2 * gap0
    for _ in range(60):
        pol(w.GAMMA_EVENTS, {})
    assert lim.min_gap == 2 * gap0  # halved once per chunk
    assert not pol.over_limit  # 11 429s so far
    pol2 = w.RatePolicy(lambda u, p: (429, b"", {}), clock=lambda: 1.0, chunk_limit=50)
    for _ in range(51):
        pol2(w.GAMMA_EVENTS, {})
    assert pol2.over_limit
    # healthy traffic does not halve
    pol3 = w.RatePolicy(lambda u, p: (200, b"", {}), clock=lambda: 1.0)
    pol3.limiter = hb.Limiter(pol3, rps=10.0, sleep=lambda s: None, live_check=None)
    g = pol3.limiter.min_gap
    for _ in range(200):
        pol3(w.GAMMA_EVENTS, {})
    assert pol3.limiter.min_gap == g


# ------------------------------------------------------------------------------- seal / verify / outputs outside
def _sealed_run(tmp_path, n_days=25):
    net = FakeNet([gev(i * 10, (datetime(2026, 9, 1) + timedelta(days=i % n_days)).strftime("%Y-%m-%d"), city=c)
                   for i, c in enumerate(["NYC", "London", "Tokyo"] * n_days)][:n_days * 3 - 2])
    # unique ids: make ids distinct
    m = fetch_kw(tmp_path / "hist", net, end_from="2026-08-30", n_events=500)
    assert m.get("token") == w.COMPLETE_TOKEN, m
    return tmp_path / "hist"


def _ns(**kw):
    return argparse.Namespace(**kw)


def test_seal_records_d_split_without_opening_outcomes_and_verifies(tmp_path, monkeypatch):
    root = _sealed_run(tmp_path)
    import gzip

    import pandas as pd

    touched = []
    real_gz, real_csv = gzip.open, pd.read_csv

    def spy_gz(f, *a, **k):
        touched.append(str(f))
        return real_gz(f, *a, **k)

    def spy_csv(f, *a, **k):
        touched.append(str(f))
        return real_csv(f, *a, **k)

    monkeypatch.setattr(gzip, "open", spy_gz)
    monkeypatch.setattr(pd, "read_csv", spy_csv)
    seals = tmp_path / "seals"
    rc = w.cmd_seal(_ns(run_id="h6_weather", root=str(root), seals_dir=str(seals), trials_path=str(tmp_path / "t.jsonl")))
    monkeypatch.undo()
    assert rc == 0
    assert touched and not any(w.OUTCOME_FILE in p for p in touched)  # only events.jsonl.gz was parsed
    seal = json.loads((root / "h6_weather" / "SEAL.json").read_text())
    sp = seal["split"]
    assert sp["d_split"] and sp["n_screen"] + sp["n_holdout"] + sp["n_embargo"] == sp["n_sample"]
    assert sp["n_holdout"] <= 0.40 * sp["n_sample"] and "outcome file was not opened" in sp["inputs"]
    assert seal["declaration"]["dataset_role"].startswith("CB2-W weather")
    copy = seals / "h6_weather_SEAL.json"
    assert copy.read_bytes() == (root / "h6_weather" / "SEAL.json").read_bytes()
    line = json.loads((tmp_path / "t.jsonl").read_text().splitlines()[-1])
    assert line["kind"] == "history_seal_declaration" and line["source"] == "creative_batch_2:cb2_f_seal"
    assert line["d_split"] == sp["d_split"] and line["n_tests"] == 0
    assert w.cmd_verify_seal(_ns(run_id="h6_weather", root=str(root), seals_dir=str(seals))) == 0
    # a second seal is refused (never rewritten)
    assert w.cmd_seal(_ns(run_id="h6_weather", root=str(root), seals_dir=str(seals), trials_path=str(tmp_path / "t.jsonl"))) == 1
    # tampering with the events file breaks verification
    (root / "h6_weather" / "ACCESS_LOG.jsonl").write_text("x\n")  # outside the listing: still verifies
    assert w.cmd_verify_seal(_ns(run_id="h6_weather", root=str(root), seals_dir=str(seals))) == 0
    (root / "h6_weather" / "extra.txt").write_text("x")
    assert w.cmd_verify_seal(_ns(run_id="h6_weather", root=str(root), seals_dir=str(seals))) == 1


def test_seal_refuses_other_runs_and_unfinished(tmp_path):
    for rid in ("h5_cb1", "h3_power", "h4_seal", "h5_cb1_ladders", "zzz"):
        assert w.cmd_seal(_ns(run_id=rid, root=str(tmp_path), seals_dir=None)) == 1
    # h5 CLI refuses h6 (use run_cb2.py seal) and vice versa for the allowlist
    with pytest.raises(h5_seal.SealError):
        h5_seal.check_run_id("h6_weather", h5_seal.H5_RUN_IDS)
    assert h5_seal.check_run_id("h6_weather") == "h6_weather"
    with pytest.raises(h5_seal.SealError):
        h5_seal.check_run_id("h2_main")
    net = FakeNet(scenario())
    fetch_kw(tmp_path, net, should_stop=lambda: True)
    assert w.cmd_seal(_ns(run_id="h6_weather", root=str(tmp_path), seals_dir=str(tmp_path / "s"))) == 1


def test_h5_seal_default_is_byte_compatible(tmp_path):
    d = tmp_path / "h5x"
    d.mkdir()
    (d / "a.csv.gz").write_bytes(b"x")
    (d / "manifest.json").write_text(json.dumps({"run_id": "h5x", "request_clock_now": "t", "frame_report": {}}))
    s = h5_seal.seal_run(d, trials_path=tmp_path / "t.jsonl")
    assert "split" not in s and s["declaration"]["dataset_role"].startswith("frozen-definition")
    line = json.loads((tmp_path / "t.jsonl").read_text())
    assert line["source"] == "creative_batch_1:cb1_f_seal" and "d_split" not in line


def test_screen_refuses_holdout_and_embargo_ids_and_results_outside_run_dir(tmp_path):
    root = _sealed_run(tmp_path)
    seals = tmp_path / "seals"
    assert w.cmd_seal(_ns(run_id="h6_weather", root=str(root), seals_dir=str(seals), trials_path=str(tmp_path / "t.jsonl"))) == 0
    view = w.open_half(root / "h6_weather", "screen", job="test", seals_dir=seals)
    sp = w.split_h6(w.load_jsonl_gz(root / "h6_weather" / "events.jsonl.gz"))
    assert set(view.event_ids) == set(sp["screen"])
    with pytest.raises(w.Refused):
        view.read_outcomes(set(sp["holdout"][:1]))
    with pytest.raises(w.Refused):
        view.read_outcomes(set(sp["embargo"][:1]))
    out = view.read_outcomes(set(sp["screen"][:3]))
    assert len(out) > 0
    # the read is logged (outside the listing) and the seal still verifies
    log = (root / "h6_weather" / "ACCESS_LOG.jsonl").read_text().splitlines()
    assert any(json.loads(x)["job"] == "test:screen" for x in log)
    w.verify_h6(root / "h6_weather", seals)
    with pytest.raises(w.Refused, match="inside"):
        w.assert_outside_run_dir(root / "h6_weather" / "results.json", root / "h6_weather")
    w.assert_outside_run_dir(tmp_path / "creative_batch2" / "W_screen" / "results.json", root / "h6_weather")


# ------------------------------------------------------------------------------- weather-fetch command refusals
def _fetch_args(tmp_path, **kw):
    seals = tmp_path / "seals"
    seals.mkdir(exist_ok=True)
    rules = seals / "rules.json"
    rules.write_text(json.dumps(w.text_rules_doc()))
    h5 = seals / "h5_cb1_SEAL.json"
    h5.write_text(json.dumps({"files": {"prices/999.csv.gz": "x"}}))
    base = dict(run_id="h6_weather", seed=w.SAMPLE_SEED, n_events=5000, end_from="2025-06-01",
                end_before="2026-10-22T00:00Z", exclude_end="2026-10-08T00:00Z,2026-10-12T00:00Z",
                exclude_runs="", exclude_seal_ids=str(h5), walk_closed="true,false", cap_at="2026-10-22T00:00Z",
                rps=4, disk_cap_gb=0.3, budget_min=None, root=str(tmp_path / "hist"), data_dumps=str(tmp_path / "dd"),
                data_dumps_cap_gb=10.0, snapshot_root=str(tmp_path / "snap"), text_rules_file=str(rules),
                allow_uncommitted=True, transport=FakeNet([]), now=NOW, wall_clock=lambda: NOW,
                sleep=lambda s: None, live_check=lambda: False, key=KEY, health_check=lambda t: (True, "ok"))
    base.update(kw)
    return _ns(**base)


def test_cmd_weather_fetch_refusals(tmp_path, capsys):
    (tmp_path / "dd").mkdir()
    assert w.cmd_weather_fetch(_fetch_args(tmp_path)) == 0
    for bad in (dict(run_id="h5_cb1"), dict(run_id="h3_power"), dict(seed="other"), dict(n_events=10),
                dict(exclude_end="2026-10-08T00:00Z,2026-10-11T00:00Z"), dict(end_from="2025-07-01"),
                dict(cap_at="2026-10-23T00:00Z"), dict(exclude_seal_ids=str(tmp_path / "none" / "h5_cb1_SEAL.json")),
                dict(exclude_seal_ids=""), dict(text_rules_file=str(tmp_path / "missing.json"))):
        assert w.cmd_weather_fetch(_fetch_args(tmp_path, **bad)) == 2, bad
    # changed text rule hash refuses
    rules = tmp_path / "seals" / "bad.json"
    rules.write_text(json.dumps({"temp_re_sha256": "0", "tz_table_sha256": "1"}))
    assert w.cmd_weather_fetch(_fetch_args(tmp_path, text_rules_file=str(rules))) == 2
    # uncommitted seal copy / rules refused when commits are required
    assert w.cmd_weather_fetch(_fetch_args(tmp_path, allow_uncommitted=False)) == 2
    # disk guard
    big = tmp_path / "dd" / "x"
    big.write_bytes(b"0" * 2048)
    assert w.cmd_weather_fetch(_fetch_args(tmp_path, data_dumps_cap_gb=1e-6)) == 2
    # at or after T_seal
    assert w.cmd_weather_fetch(_fetch_args(tmp_path, wall_clock=lambda: w.T_SEAL_EPOCH)) == 0
    out = capsys.readouterr().out
    assert "t_seal_passed" in out


# ------------------------------------------------------------------------------- queue specs, KIND_RULES, counter
def test_queue_specs_h6():
    root = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / "jobs"
    q43 = json.loads((root / "q0043_h6_weather_fetch.json").read_text())
    q44 = json.loads((root / "q0044_h6_weather_seal.json").read_text())
    assert "q0018_h5_cb1_seal" in q43["depends_on"] and "q0018_h5_cb1_seal" in q44["depends_on"]
    assert "q0043_h6_weather_fetch" in q44["depends_on"]
    assert q43["argv"][:2] == ["scripts/run_cb2.py", "weather-fetch"] and q44["argv"][:2] == ["scripts/run_cb2.py", "seal"]
    i = q43["argv"].index("--exclude-end")
    assert q43["argv"][i + 1] == "2026-10-08T00:00Z,2026-10-12T00:00Z"
    assert q43["priority"] == q44["priority"] == 59 and q43["repeat"]["until_log_regex"] == w.COMPLETE_TOKEN
    assert not list(root.glob("q004[5-9]*"))  # no analysis-job specs here


def test_kind_rules_cb2_and_counter_on_real_trials():
    for k in ("cb2_test", "cb2_replication", "cb2_prospective", "cb2_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE and len(battery2.KIND_RULES[k][1]) > 20
    assert battery2.KIND_RULES["history_seal_declaration"][0] == battery2.EXCLUDE
    p = provenance.TRIALS_PATH
    if not p.exists():
        pytest.skip("no trials log")
    r = battery2.cumulative_count(p)  # fails closed on an unknown kind
    assert r["total"] >= 670
    # CB2 lines would not change the total beyond their ml_explain count lines
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        tp = Path(td) / "t.jsonl"
        tp.write_text("".join(json.dumps(x) + "\n" for x in (
            {"kind": "cb2_test", "evidence_role": "exploratory_historical"},
            {"kind": "cb2_replication", "evidence_role": "exploratory_historical"},
            {"kind": "cb2_prospective", "evidence_role": "prospective"},
            {"kind": "cb2_descriptive", "evidence_role": "exploratory_historical"},
            {"kind": "ml_explain", "n_tests": 2, "source": "creative_batch_2:W", "evidence_role": "exploratory_historical"})))
        assert battery2.cumulative_count(tp)["total"] == 2


def test_np_import_sanity():
    assert np.isfinite(0.0)


# =============================================================================================
# Part 2: units, execution, truncation, small-G, gates, screen / replicate / stage P
# =============================================================================================
import pandas as pd  # noqa: E402

T0 = ep("2026-09-10T12:00:00Z")  # a fixed end_at


def _event(eid="e1", end=T0, city="nyc", direction="Highest", n=5, title_date="September 10"):
    return {"event_id": eid, "city": city, "direction": direction, "end_epoch": end, "title_date": title_date,
            "title_date_iso": "2026-09-10", "markets": [{"market_id": f"{eid}m{j}", "condition_id": f"c{j}",
                                                         "token_yes": f"t{j}", "bucket": str(j)} for j in range(n)]}


def _ser(points):
    ts = np.array([p[0] for p in points], float)
    return ts, np.array([p[1] for p in points], float)


def _flat(level, start, stop, step=600):
    return _ser([(t, level) for t in range(int(start), int(stop), step)])


def _book(e, levels, start=None, stop=None):
    start = start if start is not None else e["end_epoch"] - 72 * 3600
    stop = stop if stop is not None else e["end_epoch"] + 6 * 3600
    return {m["market_id"]: _flat(lv, start, stop) for m, lv in zip(e["markets"], levels, strict=True)}


def _with(pair, t_new, p_new):
    ts = np.append(pair[0], t_new)
    vs = np.append(pair[1], p_new)
    o = np.argsort(ts, kind="stable")
    return ts[o], vs[o]


def _trades(e, mids, ts=None, truncated=False):
    ts = ts if ts is not None else [e["end_epoch"] - 80 * 3600]
    return {m["market_id"]: ({"n": len(ts), "truncated": truncated, "oldest_ts": ts[0],
                              "ts": np.array(ts, float), "dropped_post_cap": 0} if m["market_id"] in mids else None)
            for m in e["markets"]}


def test_favourite_uses_only_points_usable_at_t_and_lag_and_ties():
    e = _event()
    t = e["end_epoch"] - 24 * 3600
    ser = _book(e, [0.1, 0.5, 0.2, 0.1, 0.1])
    tr = _trades(e, {"e1m1"})
    u = w.build_units([e], ser, tr, 24.0)
    assert u.loc[0, "fav_id"] == "e1m1" and u.loc[0, "pre"] == "eligible"
    # planted post-t spike on another bucket does not change the favourite or the price used at t
    spike = dict(ser)
    spike["e1m3"] = _with(spike["e1m3"], t + 60, 0.99)
    u2 = w.build_units([e], spike, tr, 24.0)
    assert u2.loc[0, "fav_id"] == "e1m1" and u2.loc[0, "p_fav_t"] == 0.5
    # the 600 s lag: a point stamped t-300 is not usable at t, one stamped t-601 is
    late = dict(ser)
    late["e1m3"] = _with(late["e1m3"], t - 300, 0.9)
    assert w.build_units([e], late, tr, 24.0).loc[0, "fav_id"] == "e1m1"
    ok = dict(ser)
    ok["e1m3"] = _with(ok["e1m3"], t - 601, 0.9)
    assert w.build_units([e], ok, _trades(e, {"e1m3"}), 24.0).loc[0, "fav_id"] == "e1m3"
    # tie -> lower market id
    tie = _book(e, [0.1, 0.5, 0.5, 0.1, 0.1])
    assert w.build_units([e], tie, _trades(e, {"e1m1", "e1m2"}), 24.0).loc[0, "fav_id"] == "e1m1"
    # more than one bucket without a usable point excludes the event; exactly one does not
    one = {k: v for k, v in ser.items() if k != "e1m4"}
    assert w.build_units([e], one, tr, 24.0).loc[0, "pre"] == "eligible"
    two = {k: v for k, v in one.items() if k != "e1m3"}
    r = w.build_units([e], two, tr, 24.0).loc[0]
    assert r["pre"] == "excl_multi_missing" and r["n_missing"] == 2
    # stale points (> 2h old) are not usable
    stale = {k: _flat(v[1][0], e["end_epoch"] - 72 * 3600, t - 3 * 3600) for k, v in ser.items()}
    assert w.build_units([e], stale, tr, 24.0).loc[0, "pre"] == "excl_multi_missing"


def test_band_and_trade_condition_and_truncation_unavailable():
    e = _event()
    t = e["end_epoch"] - 24 * 3600
    for lv, pre in ((0.29, "excl_band"), (0.30, "eligible"), (0.9499, "eligible"), (0.95, "excl_band")):
        u = w.build_units([e], _book(e, [lv, 0.1, 0.1, 0.1, 0.1]), _trades(e, {"e1m0"}), 24.0)
        assert u.loc[0, "pre"] == pre, lv
    ser = _book(e, [0.5, 0.1, 0.1, 0.1, 0.1])
    # no trade before t in a complete fetch: false (excluded)
    assert w.build_units([e], ser, _trades(e, {"e1m0"}, ts=[t + 100]), 24.0).loc[0, "pre"] == "excl_no_trade"
    # truncated with the oldest stored trade at or after t: unavailable (not false)
    r = w.build_units([e], ser, _trades(e, {"e1m0"}, ts=[t + 100], truncated=True), 24.0).loc[0]
    assert r["pre"] == "unavailable" and r["trade_cond"] == "unavailable"
    # truncated but a stored trade before t: known true
    assert w.build_units([e], ser, _trades(e, {"e1m0"}, ts=[t - 100, t + 100], truncated=True), 24.0).loc[0, "pre"] == "eligible"
    # no trade record at all: unavailable, never 0
    assert w.build_units([e], ser, {m["market_id"]: None for m in e["markets"]}, 24.0).loc[0, "pre"] == "unavailable"


def test_execution_at_t_plus_2h_and_missing_point_keeps_unit_with_net_zero():
    e = _event()
    t = e["end_epoch"] - 6 * 3600
    base = _book(e, [0.5, 0.1, 0.1, 0.1, 0.1])
    ts, vs = base["e1m0"]
    # price at t+2h is 0.6; a planted price after t+2h must not change it
    series = dict(base)
    pts = [(x, 0.5) for x in range(int(t - 70 * 3600), int(t + 2 * 3600 - 700), 600)] + [(int(t + 2 * 3600 - 700), 0.6)]
    series["e1m0"] = _ser(pts + [(int(t + 2 * 3600 + 5), 0.99)])
    u = w.build_units([e], series, _trades(e, {"e1m0"}), 6.0).loc[0]
    assert u["executed"] and u["p_exec"] == 0.6
    a, f = w.weather_ask(0.6)
    assert u["a"] == a and u["f"] == f and u["K"] == a + f
    # no usable point at t+2h (series stops at t): the unit is kept, not executed, net 0
    u2 = w.build_units([e], {**base, "e1m0": _flat(0.5, t - 70 * 3600, t - 900)}, _trades(e, {"e1m0"}), 6.0)
    assert u2.loc[0, "pre"] == "eligible" and not u2.loc[0, "executed"]
    d = w.attach_outcomes(u2, {"e1": {"yes": {"e1m0": 1.0}, "status": "resolved", "closed_time": t + 3600}})
    assert d.loc[0, "net"] == 0.0 and d.loc[0, "w3"] == 0.0
    assert len(w.primary_frame(d)) == 1  # kept in the denominator


def test_weather_cost_h_w_floor_and_fee_rate():
    assert w.H_W_FLOOR == 0.02 and w.WEATHER_FEE_RATE == 0.05 and w.COST_SENS == 0.0075
    for p in (0.3, 0.5, 0.7, 0.9):
        assert w.h_w(p) >= 0.02
    assert w.h_w(0.5) == 0.02  # the 1.10c CB1 band is floored at 2.0c
    a, f = w.weather_ask(0.5)
    assert abs(a - 0.52) < 1e-12 and abs(f - 0.05 * a * (1 - a)) < 1e-12
    assert w.weather_ask(0.99)[0] == 0.999


def test_outcome_status_and_worst_case_extra():
    df = pd.DataFrame([
        {"market_id": "a", "event_id": "1", "outcome_prices": '["1","0"]', "closed": "True", "closed_time": "2026-09-10T13:00:00Z"},
        {"market_id": "b", "event_id": "1", "outcome_prices": '["0","1"]', "closed": "True", "closed_time": "2026-09-10T13:00:00Z"},
        {"market_id": "c", "event_id": "2", "outcome_prices": '["0.5","0.5"]', "closed": "True", "closed_time": ""},
        {"market_id": "d", "event_id": "2", "outcome_prices": '["0.5","0.5"]', "closed": "True", "closed_time": ""},
        {"market_id": "e", "event_id": "3", "outcome_prices": '["0","1"]', "closed": "False", "closed_time": ""}])
    o = w.parse_event_outcomes(df)
    assert o["1"]["status"] == "resolved" and o["2"]["status"] == "anomalous" and o["3"]["status"] == "open"


def _synthetic_units(n_ev, win, seed=1, n_city=22, n_days=40):
    """Primary-ready units for the gate tests (no files)."""
    rng = np.random.default_rng(seed)
    cities = list(w.TZ_TABLE)[:n_city]
    rows = []
    for i in range(n_ev):
        d = i % n_days
        end = ep("2026-08-01T12:00:00Z") + d * 86400
        y = float(rng.random() < win)
        a, f = w.weather_ask(0.5)
        rows.append({"event_id": str(i), "city": cities[i % n_city], "day": datetime.fromtimestamp(end, UTC).strftime("%Y-%m-%d"),
                     "week": w.week_label(end), "executed": True, "K": a + f, "a": a, "f": f, "p_exec": 0.5, "Y": y,
                     "net": y - a - f, "w3": y - 0.5, "d": 0.3, "local_class": "pre", "pre": "eligible", "ostatus": "resolved",
                     "band": "0.45-0.60", "direction": "Highest"})
    return pd.DataFrame(rows)


def test_small_g_rule_branches():
    rng = np.random.default_rng(3)
    v = rng.normal(0.05, 0.4, 400)
    cl30 = np.arange(400) % 40
    cl20 = np.arange(400) % 20
    cl14 = np.arange(400) % 14
    r30 = w.small_g_pvalue(v, cl30, n_wild=499)
    assert r30["method"] == "cr1_normal" and r30["G"] == 40
    r20 = w.small_g_pvalue(v, cl20, n_wild=999)
    assert r20["method"] == "cr2_t_and_wild" and r20["G"] == 20
    assert r20["p"] == max(r20["p_cr2_t"], r20["p_wild"]) and 0 < r20["p_wild"] <= 1
    # CR2 + t(19) is more conservative than CR1 + normal
    from scipy.stats import t as tdist

    assert abs(r20["p_cr2_t"] - float(tdist.sf(r20["t_cr2"], 19))) < 1e-12
    r14 = w.small_g_pvalue(v, cl14)
    assert r14["p"] == 1.0 and r14["method"] == "not_testable" and not r14["testable"]
    # the placebo shortcut skips the wild bootstrap when CR2 already fails alpha
    sk = w.small_g_pvalue(-v, cl20, alpha=0.01, n_wild=999)
    assert sk["p_wild"] is None and sk["p"] == sk["p_cr2_t"]
    # a way with G < 15 makes the whole test not testable (p = 1)
    day = np.arange(400) % 40
    city = np.arange(400) % 14
    ct = w.cluster_test_w(v, day, city, day // 7, n_boot=50, n_wild=99)
    assert not ct["testable"] and ct["p"] == 1.0 and ct["G_city"] == 14
    ct2 = w.cluster_test_w(v, day, np.arange(400) % 20, day // 7, n_boot=50, n_wild=99)
    assert ct2["testable"] and ct2["p"] == max(ct2["p_day"], ct2["p_city"]) and len(ct2["ci95_week_boot"]) == 2


def test_gate_advances_on_strong_effect_and_blocks_on_each_condition():
    u = _synthetic_units(600, 0.85)
    spec = w.HYPOTHESES_CB2_W["W2"]
    g = w.w_gate(u, spec, np.array([]), alpha=0.01, n_boot=100, n_wild=499, col="net")
    assert g["advance_core"] and g["mean"] > 0.2 and g["r_ann"] > 0.1
    # null effect fails p and floor
    z = _synthetic_units(600, 0.5200 + 0.0)
    gz = w.w_gate(z, spec, np.array([]), alpha=0.01, n_boot=50, n_wild=99, col="net")
    assert not gz["advance_core"] and "p" in gz["fail"]
    # too few units: not testable
    gs = w.w_gate(u.head(60), spec, np.array([]), alpha=0.01, n_boot=50, n_wild=99, col="net")
    assert not gs["testable"] and gs["fail"] == ["not_testable"]
    # +0.75c: a mean just above the floor but below the cost sensitivity is blocked by the cost check
    low = u.copy()
    low["net"] = low["net"] - low["net"].mean() + 0.0102 + 0.0 * low["net"]
    gl = w.w_gate(low, spec, np.array([]), alpha=0.5, n_boot=20, n_wild=99, col="net")
    assert gl["robustness"]["cost_0.75c_positive"] is True  # 1.02c > 0.75c
    low["net"] = low["net"] - 0.0035
    gl2 = w.w_gate(low, spec, np.array([]), alpha=0.5, n_boot=20, n_wild=99, col="net")
    assert "floor" in gl2["fail"] and gl2["robustness"]["cost_0.75c_positive"] is False or "cost_0.75c" in gl2["fail"]


def test_truncation_worst_case_flips_sign_and_blocks_the_advance():
    u = _synthetic_units(600, 0.62)  # modest positive edge
    spec = w.HYPOTHESES_CB2_W["W2"]
    ok = w.w_gate(u, spec, np.array([]), alpha=0.05, n_boot=20, n_wild=99, col="net")
    assert ok["advance_core"] and ok["robustness"]["worst_case_mean"] > 0
    a, f = w.weather_ask(0.5)
    wc = np.full(400, -(a + f))  # 400 unavailable favourites added back as losers
    bad = w.w_gate(u, spec, wc, alpha=0.05, n_boot=20, n_wild=99, col="net")
    assert bad["robustness"]["worst_case_mean"] < 0 and "worst_case" in bad["fail"] and not bad["advance_core"]
    # worst_case_extra builds exactly those rows from unavailable / anomalous units
    d = u.head(6).copy()
    d["pre"] = ["eligible", "eligible", "unavailable", "unavailable", "excl_band", "eligible"]
    d["ostatus"] = ["resolved", "anomalous", "resolved", "resolved", "resolved", "open"]
    d["executed"] = [True, True, True, False, True, True]
    assert len(w.worst_case_extra(d, "net")) == 4
    wcx = w.worst_case_extra(d, "net")
    assert wcx[0] == -d["K"].iloc[1] and wcx[1] == -d["K"].iloc[2] and wcx[2] == 0.0 and wcx[3] == -d["K"].iloc[5]
    # reported by Y
    d["Y"] = [1.0, np.nan, 1.0, 0.0, 1.0, np.nan]
    assert w.truncation_report(d)["by_Y"] == {"Y1": 1, "Y0": 1, "Y_unknown": 0}


def test_breakeven_placebo_is_calibrated_and_detects_real_edge_rarely():
    u = _synthetic_units(500, 0.5)
    spec = w.HYPOTHESES_CB2_W["W2"]
    pl = w.breakeven_placebo_w(u, spec, np.array([]), alpha=0.01, test="W2", draws=40, n_wild=99)
    assert pl["draws"] == 40 and pl["advance_rate"] <= 0.05  # random Bernoulli at break-even advances ~never
    pl3 = w.breakeven_placebo_w(u, w.HYPOTHESES_CB2_W["W3"], np.array([]), alpha=0.01, test="W3", draws=40, n_wild=99)
    assert pl3["advance_rate"] <= 0.05


def test_credit_rule_pre_extreme_subset():
    u = _synthetic_units(200, 0.8)
    u["local_class"] = ["pre", "post"] * 100
    full = float(u["net"].mean())
    c = w.credit_rule(u, "net", full)
    assert c["credits_ch27"] and "CH27" in c["label_if_pass"]
    u2 = u.copy()
    u2.loc[u2["local_class"] == "pre", "net"] = -0.1
    c2 = w.credit_rule(u2, "net", float(u2["net"].mean()))
    assert not c2["credits_ch27"] and "not CH27" in c2["label_if_pass"]
    u3 = u.copy()
    u3.loc[u3["local_class"] == "pre", "net"] = 0.01  # positive but < half the full estimate
    c3 = w.credit_rule(u3, "net", float(u3["net"].mean()))
    assert c3["pre_mean"] == pytest.approx(0.01) and c3["full_mean"] > 0.02 and not c3["credits_ch27"]


# ------------------------------------------------------------------------------- end-to-end on a synthetic sealed run
def make_run(root: Path, win_prob: float, seed: int = 5, n_city: int = 22, n_days: int = 60) -> Path:
    """A finished, unsealed h6 run directory built from fixtures: the favourite (bucket 2) sits at 0.5 for the
    whole window and wins with probability ``win_prob``."""
    rng = np.random.default_rng(seed)
    rdir = root / "h6_weather"
    (rdir / "prices").mkdir(parents=True)
    (rdir / "trades").mkdir()
    cities = list(w.TZ_TABLE)[:n_city]
    d0 = ep("2026-08-01T12:00:00Z")
    events, outs, prog = [], [], []
    for d in range(n_days):
        for ci, city in enumerate(cities):
            eid = f"{d * 100 + ci}"
            end = d0 + d * 86400
            day = datetime.fromtimestamp(end, UTC)
            ev = {"event_id": eid, "title": f"Highest temperature in {city} on {day:%B} {day.day}?", "direction": "Highest",
                  "city": city, "title_date": f"{day:%B} {day.day}", "title_date_iso": day.date().isoformat(),
                  "end_at": w._iso(end), "end_epoch": end, "n_members": 4,
                  "markets": [{"market_id": f"{eid}{j}", "condition_id": f"c{eid}{j}", "token_yes": f"t{eid}{j}",
                               "bucket": str(j)} for j in range(4)]}
            events.append(ev)
            win = rng.random() < win_prob
            rec = {"event_id": eid, "status": "done", "markets": {}}
            for j, m in enumerate(ev["markets"]):
                lv = 0.5 if j == 2 else 0.1
                pts = [(t, lv) for t in range(int(end - 72 * 3600), int(end + 6 * 3600), 1800)]
                (rdir / "prices" / f"{m['market_id']}.csv.gz").write_bytes(
                    hb._gz_csv_bytes(["t", "p"], ([t, p] for t, p in pts)))
                rec["markets"][m["market_id"]] = {"price_points": len(pts), "dropped_price_rows_post_cap": 0, "trades": None}
                yes = 1.0 if j == (2 if win else 3) else 0.0
                outs.append([m["market_id"], eid, json.dumps([str(yes), str(1 - yes)]), "True", w._iso(end + 3600), "True"])
            if True:
                m2 = ev["markets"][2]["market_id"]
                (rdir / "trades" / f"{m2}.csv.gz").write_bytes(
                    hb._gz_csv_bytes(hb.TRADE_COLUMNS, [[int(end - 90 * 3600), "BUY", 1, 0.5, 0, "w", "k"]]))
                rec["markets"][m2]["trades"] = {"n": 1, "truncated": False, "oldest_ts": int(end - 90 * 3600),
                                                "dropped_post_cap": 0}
            prog.append(rec)
    (rdir / "events.jsonl.gz").write_bytes(w._gz_jsonl_bytes(events))
    (rdir / "progress.jsonl").write_text("".join(json.dumps(r) + "\n" for r in prog))
    hb_ = hb._gz_csv_bytes(["market_id", "event_id", "outcome_prices", "closed", "closed_time", "event_closed"], outs)
    (rdir / w.OUTCOME_FILE).write_bytes(hb_)
    (rdir / "manifest.json").write_text(json.dumps({"run_id": "h6_weather", "complete": True, "stopped": None,
                                                     "request_clock_now": "2026-10-16T12:00:00Z", "frame_report": {}}))
    return rdir


def _spec(tmp_path) -> Path:
    p = tmp_path / "cb2_v1.json"
    p.write_text(json.dumps({"weather_sha256": w.declaration_sha256_weather()}))
    return p


def _run_args(tmp_path, **kw):
    base = dict(run_id="h6_weather", root=str(tmp_path / "hist"), seals_dir=str(tmp_path / "seals"),
                out_root=str(tmp_path / "cb2out"), spec_path=str(_spec(tmp_path)), trials_path=str(tmp_path / "t.jsonl"),
                n_boot=100, n_wild=499, placebo_draws=20, allow_uncommitted=True, k_stage2=5)
    base.update(kw)
    return _ns(**base)


def _sealed(tmp_path, win_prob):
    root = tmp_path / "hist"
    make_run(root, win_prob)
    assert w.cmd_seal(_ns(run_id="h6_weather", root=str(root), seals_dir=str(tmp_path / "seals"),
                          trials_path=str(tmp_path / "t.jsonl"))) == 0
    return root


def test_census_reads_no_outcomes_and_reports_g(tmp_path, monkeypatch, capsys):
    root = _sealed(tmp_path, 0.8)
    touched = []
    real = pd.read_csv

    def spy(f, *a, **k):
        touched.append(str(f))
        return real(f, *a, **k)

    monkeypatch.setattr(pd, "read_csv", spy)
    rc = w.cmd_census_w(_run_args(tmp_path))
    monkeypatch.undo()
    assert rc == 0 and not any(w.OUTCOME_FILE in t for t in touched)
    cen = json.loads(next((tmp_path / "cb2out").glob("census_W*.json")).read_text())
    assert cen["counts_only"] and cen["reads_outcomes"] is False
    o24 = cen["origins"]["24"]
    assert o24["G_city"] == 22 and o24["n_eligible"] > 100 and o24["city_method"] == "cr2_t_and_wild"
    assert "Y" not in json.dumps(cen)
    with pytest.raises(ValueError):
        w.assert_no_outcomes(pd.DataFrame({"net": [1.0]}))
    # census touches the SCREEN block only and logs the read
    log = [json.loads(x) for x in (root / "h6_weather" / "ACCESS_LOG.jsonl").read_text().splitlines()]
    assert log and all(r["job"].startswith("q0042_census:screen") for r in log)
    capsys.readouterr()


def test_screen_requires_declaration_and_writes_outside_sealed_dir(tmp_path, capsys):
    root = _sealed(tmp_path, 0.85)
    assert w.cmd_screen_w(_run_args(tmp_path, spec_path=str(tmp_path / "missing.json"))) == 2
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"weather_sha256": "0" * 64}))
    assert w.cmd_screen_w(_run_args(tmp_path, spec_path=str(bad))) == 2
    assert w.cmd_screen_w(_run_args(tmp_path, allow_uncommitted=False)) == 2  # spec not committed
    assert not (tmp_path / "t.jsonl").read_text().count("cb2_test")
    assert w.cmd_screen_w(_run_args(tmp_path)) == 0
    res_path = tmp_path / "cb2out" / "W_screen" / "results.json"
    res = json.loads(res_path.read_text())
    assert not str(res_path).startswith(str(root / "h6_weather"))
    assert res["tests"]["W2"]["advance"] and res["tests"]["W3"]["advance"]
    assert res["tests"]["W2"]["n"] >= 100 and res["tests"]["W2"]["G_city"] == 22 and res["tests"]["W2"]["method_city"] == "cr2_t_and_wild"
    assert res["descriptive"]["W1"]["n_units"] > 0 and res["half"] == "screen"
    w.verify_h6(root / "h6_weather", tmp_path / "seals")  # seal still valid after the screen
    # never overwritten
    assert w.cmd_screen_w(_run_args(tmp_path)) == 2
    # trial lines: 2 cb2_test + descriptive + placebo lines + one count line with n_tests = 2
    lines = [json.loads(x) for x in (tmp_path / "t.jsonl").read_text().splitlines()]
    kinds = [x["kind"] for x in lines if x.get("evidence_role") != "placebo"]
    assert kinds.count("cb2_test") == 2 and kinds.count("cb2_descriptive") == 1
    cnt = [x for x in lines if x["kind"] == "ml_explain"]
    assert len(cnt) == 1 and cnt[0]["n_tests"] == 2 and cnt[0]["source"] == "creative_batch_2:W"
    assert sum(1 for x in lines if x.get("evidence_role") == "placebo") == 2
    # the screen never opened the holdout or embargo outcome rows
    log = [json.loads(x) for x in (root / "h6_weather" / "ACCESS_LOG.jsonl").read_text().splitlines()]
    assert all(":holdout" not in r["job"] for r in log)
    capsys.readouterr()


def test_replicate_nothing_advanced_never_opens_holdout(tmp_path, capsys):
    root = _sealed(tmp_path, 0.5)  # fair coin: no edge
    assert w.cmd_screen_w(_run_args(tmp_path)) == 0
    scr = json.loads((tmp_path / "cb2out" / "W_screen" / "results.json").read_text())
    assert not any(v["advance"] for v in scr["tests"].values())
    capsys.readouterr()
    assert w.cmd_replicate_w(_run_args(tmp_path)) == 0
    assert "nothing advanced" in capsys.readouterr().out
    log = [json.loads(x) for x in (root / "h6_weather" / "ACCESS_LOG.jsonl").read_text().splitlines()]
    assert all(":holdout" not in r["job"] for r in log) and not (tmp_path / "cb2out" / "W_holdout").exists()


def test_replicate_reads_holdout_once_logs_it_and_keeps_seal_valid(tmp_path, capsys):
    root = _sealed(tmp_path, 0.85)
    assert w.cmd_screen_w(_run_args(tmp_path)) == 0
    assert w.cmd_replicate_w(_run_args(tmp_path, spec_path=str(tmp_path / "missing.json"))) == 2
    assert w.cmd_replicate_w(_run_args(tmp_path)) == 0
    hold = json.loads((tmp_path / "cb2out" / "W_holdout" / "results.json").read_text())
    assert hold["half"] == "holdout" and hold["alpha_bonferroni"] == pytest.approx(0.05 / 5)
    assert set(hold["tests"]) == {"W2", "W3"} and all(t["replicated"] for t in hold["tests"].values())
    log = [json.loads(x) for x in (root / "h6_weather" / "ACCESS_LOG.jsonl").read_text().splitlines()]
    assert sum(1 for r in log if r["job"].startswith("q0047_cb2_holdout_W:holdout")) >= 2
    w.verify_h6(root / "h6_weather", tmp_path / "seals")
    lines = [json.loads(x) for x in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert sum(1 for x in lines if x["kind"] == "cb2_replication" and x.get("evidence_role") != "placebo") == 2
    assert w.cmd_replicate_w(_run_args(tmp_path)) == 2  # the holdout is read once: results are never overwritten
    capsys.readouterr()


def test_runner_hook_names_and_extra_flags():
    for n in ("cmd_weather_fetch", "cmd_seal", "cmd_verify_seal", "cmd_stagep", "cmd_census_w", "cmd_screen_w",
              "cmd_replicate_w", "cmd_census", "cmd_screen", "cmd_replicate"):
        assert callable(getattr(w, n))
    a = _ns(extra=["--seed", "abc", "--n-events", "7", "--disk-cap-gb", "0.1", "--unknown-flag", "1"], run_id=None)
    w.prep_args(a)
    assert a.seed == "abc" and a.n_events == 7 and a.disk_cap_gb == 0.1 and a.run_id == "h6_weather" and a.n_boot == 2000
    b = _ns(seed="keep", extra=["--seed", "other"])
    w.prep_args(b)
    assert b.seed == "keep"  # attributes already set are never overwritten
    spec = w.HYPOTHESES_CB2_W
    assert spec["W1"]["counted"] is False and spec["W2"]["kind"] == "economic" and spec["W3"]["kind"] == "mechanism"
    assert spec["W2"]["floor"] == 0.010 and spec["W3"]["floor"] == 0.010 and spec["W2"]["rann_floor"] == 0.10
    d = w.declaration_weather()
    assert d["dates"]["census_ex"] == list(w.T_CENSUS_EX) and d["split"]["holdout_frac"] == 0.40
    assert d["uncertainty"]["small_g"]["wild_draws"] == 9999


# ------------------------------------------------------------------------------- stage P
def make_extract(root: Path, rep_start: float, *, incomplete_event=False, closed_member=False):
    """One weather event G1 (4 members) on live captures every 2 h; favourite m2 at mid 0.5, ask 0.52."""
    (root / "negrisk").mkdir(parents=True)
    end = rep_start + 3 * 86400 + 12 * 3600
    caps = {}
    cid_i = 0
    t = rep_start - 3 * 3600
    cols = ["capture_id", "capture_start_utc", "received_utc", "neg_risk_market_id", "event_id", "market_id",
            "clob_token_id_0", "best_bid", "best_ask", "spread", "last_trade_price", "closed", "active",
            "accepting_orders", "neg_risk_other", "event_neg_risk_augmented", "volume_num", "fee_schedule",
            "fee_category", "end_date", "fees_enabled", "sw1_best_ask", "sw1_ask_size_1", "sw2_best_ask", "sw2_ask_size_1"]
    while t < end + 6 * 3600:
        cid = f"cap{cid_i:04d}"
        cid_i += 1
        rows = []
        for j in range(4 if not incomplete_event else 3):
            bid, ask = (0.48, 0.52) if j == 2 else (0.08, 0.12)
            rows.append({"capture_id": cid, "capture_start_utc": w._iso(t), "received_utc": w._iso(t), "neg_risk_market_id": "G1",
                         "event_id": "E1", "market_id": f"m{j}", "clob_token_id_0": f"tok{j}", "best_bid": bid, "best_ask": ask,
                         "spread": ask - bid, "last_trade_price": 0.5, "closed": closed_member and j == 0, "active": True,
                         "accepting_orders": True, "neg_risk_other": False, "event_neg_risk_augmented": False,
                         "volume_num": 100.0, "fee_schedule": "", "fee_category": "weather", "end_date": w._iso(end),
                         "fees_enabled": True, "sw1_best_ask": ask, "sw1_ask_size_1": 10.0, "sw2_best_ask": ask,
                         "sw2_ask_size_1": 10.0})
        pd.DataFrame(rows, columns=cols).to_csv(root / "negrisk" / f"{cid}.csv.gz", index=False)
        caps[cid] = {"started_utc": w._iso(t), "status": "written"}
        t += 2 * 3600
    (root / "manifest.json").write_text(json.dumps({"captures": caps}))
    pd.DataFrame([{"neg_risk_market_id": "G1", "event_id": "E1", "member_count": 4, "n_open": 4, "n_closed": 0,
                   "fetched_utc": w._iso(rep_start - 4 * 3600), "http_status": 200}]).to_csv(
        root / "event_members.csv.gz", index=False)
    pd.DataFrame([{"neg_risk_market_id": "G1", "event_id": "E1", "fetched_utc": w._iso(rep_start - 4 * 3600),
                   "title": "Highest temperature in NYC on September 10?", "slug": "x",
                   "member_market_ids": json.dumps(["m0", "m1", "m2", "m3"]), "group_item_titles": "[]"}]).to_csv(
        root / "event_text.csv.gz", index=False)
    return end


def test_stagep_units_recorded_ask_at_next_capture(tmp_path):
    rep = ep("2026-10-26T00:00:00Z")
    end = make_extract(tmp_path / "x", rep)
    u, cnt = w.stagep_units(tmp_path / "x", rep)
    assert cnt["eligible"] == 1 and set(u["origin_h"]) == {24.0, 6.0}
    r6 = u[u["origin_h"] == 6.0].iloc[0]
    assert r6["fav_id"] == "m2" and r6["pre"] == "eligible" and r6["p_fav_t"] == pytest.approx(0.5)
    assert r6["executed"] and r6["a"] == pytest.approx(0.52) and r6["p_exec"] == pytest.approx(0.5)
    assert r6["f"] == pytest.approx(0.05 * 0.52 * 0.48) and r6["depth_ok"]
    assert r6["t"] == end - 6 * 3600 and r6["local_class"] in ("pre", "during", "post")
    # an event with fewer visible members than the as-of count is not member-complete
    make_extract(tmp_path / "y", rep, incomplete_event=True)
    uy, cy = w.stagep_units(tmp_path / "y", rep)
    assert cy["eligible"] == 0 and (uy["pre"] == "excl_not_member_complete").all()
    # a closed member excludes the event
    make_extract(tmp_path / "z", rep, closed_member=True)
    uz, cz = w.stagep_units(tmp_path / "z", rep)
    assert cz["eligible"] == 0 and (uz["pre"] == "excl_not_open_accepting").all()
    # origin before T2_rep_start: out of the window
    assert len(w.stagep_units(tmp_path / "x", rep + 3 * 86400)[0]) == 0


def test_stagep_cmd_refuses_before_t2_w_out_and_when_nothing_replicated(tmp_path, capsys):
    rep = ep("2026-10-26T00:00:00Z")
    make_extract(tmp_path / "x", rep)
    hold = tmp_path / "cb2out" / "W_holdout"
    hold.mkdir(parents=True)
    (hold / "results.json").write_text(json.dumps({"tests": {"W2": {"replicated": False}}}))
    t_out = rep + 63 * 86400

    def go(now, **kw):
        return w.cmd_stagep(_run_args(tmp_path, extract_root=str(tmp_path / "x"), t_rep_start="2026-10-26T00:00Z",
                                      now=w._iso(now), **kw))

    assert go(t_out - 3600) == 2
    assert go(t_out) == 0 and "nothing replicated" in capsys.readouterr().out
    (hold / "results.json").write_text(json.dumps({"tests": {"W2": {"replicated": True}, "W3": {"replicated": False}}}))

    def transport(url, params):
        evs = [{"id": "E1", "markets": [{"id": f"m{j}", "outcomePrices": json.dumps(["1", "0"] if j == 2 else ["0", "1"]),
                                          "closed": True, "closedTime": w._iso(rep + 4 * 86400)} for j in range(4)]}]
        return 200, json.dumps(evs).encode(), {}

    rc = go(t_out + 1, transport=transport, sleep=lambda s: None, live_check=lambda: False, rps=1000.0,
            health_check=lambda t: (True, "ok"))
    assert rc == 0
    res = json.loads((tmp_path / "cb2out" / "W_stageP" / "results.json").read_text())
    assert res["stage"] == "P" and res["evidence_role"] == "prospective_confirmation" and res["k_stage_p"] == 1
    assert res["tests"]["W2"]["testable"] is False  # one event: not testable, never claimed
    assert res["alpha"] == pytest.approx(0.05)
    assert go(t_out + 1, transport=transport) == 2  # never overwritten
    lines = [json.loads(x) for x in (tmp_path / "t.jsonl").read_text().splitlines()]
    assert any(x["kind"] == "cb2_prospective" for x in lines)
    # stage P paused (transient) when the collector is unhealthy
    (tmp_path / "cb2out" / "W_stageP" / "results.json").unlink()
    assert go(t_out + 1, transport=transport, health_check=lambda t: (False, "stale")) == 0
    assert "paused_collector_health" in capsys.readouterr().out


def test_stagep_outcome_censoring_and_anomaly():
    rep = ep("2026-10-26T00:00:00Z")
    u = pd.DataFrame([
        {"event_id": "A", "fav_id": "m2", "last_bid": 0.7, "executed": True, "K": 0.55, "p_exec": 0.5, "pre": "eligible", "exec_start": rep, "depth_ok": True},
        {"event_id": "B", "fav_id": "m2", "last_bid": 0.7, "executed": True, "K": 0.55, "p_exec": 0.5, "pre": "eligible", "exec_start": rep, "depth_ok": True},
        {"event_id": "C", "fav_id": "m2", "last_bid": 0.7, "executed": True, "K": 0.55, "p_exec": 0.5, "pre": "eligible", "exec_start": rep, "depth_ok": True}])
    outs = {"A": {"yes": {"m2": 1.0}, "status": "resolved", "closed_time": rep + 86400.0},
            "B": {"yes": {"m2": 0.5}, "status": "anomalous", "closed_time": math.nan}}
    out, share = w.attach_stagep_outcomes(u, outs)
    assert list(out["ostatus"]) == ["resolved", "anomalous", "censored"]
    assert out.loc[2, "Y"] == 0.7 and share["censored"] == 1 and share["resolution_lag_sensitive"] is True
    prim = w.stagep_primary(out)
    assert set(prim["event_id"]) == {"A", "C"}  # anomalous excluded from the primary; censored flagged, valued at last bid
