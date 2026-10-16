# ruff: noqa: E501
"""CB2-W (weather favourites): fixtures only, no network, no real data. See CREATIVE_BATCH_2.md section 4.4."""

from __future__ import annotations

import argparse
import json
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
