# ruff: noqa: E501
"""Prospective public-data streams (docs/research_lab/NEW_STREAMS_2026-10-19.md): parsing, change-only log,
idempotency, crash safety, disk guard and rate limit. No network."""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import pytest

from astrolabe.research_lab.streams import common, espn_odds, gamma_rules, predictit, smarkets
from astrolabe.research_lab.streams.common import (
    ChangeLog,
    DiskGuard,
    FetchError,
    Http,
    NotNow,
    PollResult,
    Throttle,
    run_stream,
)

T0 = 1_792_450_000.0  # 2026-10-19T... UTC


class Clock:
    def __init__(self, t: float = T0):
        self.t = t
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def mono(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s


def lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def free_ok(_p):
    return 50 * 10**9


def du_small(_p):
    return 1024**3


# ---- throttle / http --------------------------------------------------------------------------------------------


def test_throttle_spaces_requests():
    c = Clock()
    th = Throttle(2.0, c.mono, c.sleep)
    for _ in range(4):
        th.wait()
    assert c.sleeps == [0.5, 0.5, 0.5]


def test_throttle_rejects_nonpositive_rps():
    with pytest.raises(ValueError):
        Throttle(0)


def test_http_retries_429_with_retry_after_then_succeeds():
    c = Clock()
    calls = []

    def tr(url, headers, timeout):
        calls.append(url)
        assert "arepo-research" in headers["User-Agent"]
        return (429, {"retry-after": "7"}, b"") if len(calls) == 1 else (200, {}, b'{"ok": 1}')

    h = Http(transport=tr, rps=1.0, clock=c, mono=c.mono, sleep=c.sleep)
    assert h.get_json("https://x/y", {"a": 1}, tag="t") == {"ok": 1}
    assert calls[0] == "https://x/y?a=1" and h.requests == 2
    assert 7.0 in c.sleeps
    assert [f["status"] for f in h.fetches] == [429, 200] and "sha256" in h.fetches[1]


def test_http_non_retry_status_raises_and_budget_stops():
    c = Clock()
    h = Http(transport=lambda u, hd, t: (404, {}, b"no"), clock=c, mono=c.mono, sleep=c.sleep)
    with pytest.raises(FetchError, match="HTTP 404"):
        h.get_json("https://x")
    h2 = Http(transport=lambda u, hd, t: (503, {}, b""), budget_s=5, clock=c, mono=c.mono, sleep=c.sleep)
    with pytest.raises(FetchError):
        h2.get_json("https://x")
    assert h2.requests <= 2  # backoff 2 s then 8 s > budget


def test_http_transport_error_is_retried_then_fails():
    c = Clock()

    def tr(u, hd, t):
        raise FetchError("transport: timeout")

    h = Http(transport=tr, max_attempts=2, clock=c, mono=c.mono, sleep=c.sleep)
    with pytest.raises(FetchError, match="gave up"):
        h.get_json("https://x")
    assert h.requests == 2


# ---- disk guard -------------------------------------------------------------------------------------------------


def test_disk_guard_free_disk_cap_and_stream_cap(tmp_path):
    dd = tmp_path / "dd"
    sdir = dd / "research_lab" / "s"
    sdir.mkdir(parents=True)
    g = DiskGuard(dd, sdir, cap_gb=40, free_min_gb=4, stream_cap_gb=0.001, free_fn=free_ok, du_fn=du_small)
    assert g.check(1000)["free_gb"] == 50.0
    with pytest.raises(NotNow, match="free disk"):
        DiskGuard(dd, sdir, free_fn=lambda p: 4 * 10**9 + 10, du_fn=du_small).check(1000)
    with pytest.raises(NotNow, match="cap 40"):
        DiskGuard(dd, sdir, free_fn=free_ok, du_fn=lambda p: 40 * 1024**3, du_ttl_s=0).check(1000)
    (sdir / "20261019.jsonl").write_bytes(b"x" * 2_000_000)
    with pytest.raises(NotNow, match="stream cap"):
        DiskGuard(dd, sdir, stream_cap_gb=0.001, free_fn=free_ok, du_fn=du_small).check(0)


def test_disk_guard_caches_du(tmp_path):
    dd = tmp_path / "dd"
    sdir = dd / "s"
    sdir.mkdir(parents=True)
    c = Clock()
    n = []

    def du(p):
        n.append(1)
        return 5

    g = DiskGuard(dd, sdir, free_fn=free_ok, du_fn=du, clock=c, du_ttl_s=900)
    g.check(0)
    g.check(0)
    assert len(n) == 1
    c.t += 901
    g.check(0)
    assert len(n) == 2


# ---- change log -------------------------------------------------------------------------------------------------


def test_changelog_new_changed_unchanged_gone_checkpoint(tmp_path):
    c = Clock()
    log = ChangeLog(tmp_path, "s", checkpoint_s=3600, clock=c)
    s1 = log.commit("A", c.t, PollResult({"k:1": {"v": 1}, "k:2": {"v": 2}}, scopes=("k:",)))
    assert (s1["n_new"], s1["n_changed"]) == (2, 0)
    c.t += 60
    log = ChangeLog(tmp_path, "s", checkpoint_s=3600, clock=c)  # fresh process: state from disk
    s2 = log.commit("B", c.t, PollResult({"k:1": {"v": 9}}, scopes=("k:",)))
    assert (s2["n_new"], s2["n_changed"], s2["n_gone"], s2["n_checkpoint"]) == (0, 1, 1, 0)
    c.t += 60
    s3 = log.commit("C", c.t, PollResult({"k:1": {"v": 9}}, scopes=("k:",)))
    assert s3["n_changed"] + s3["n_new"] + s3["n_checkpoint"] == 0
    c.t += 3600
    s4 = log.commit("D", c.t, PollResult({"k:1": {"v": 9}}, scopes=("k:",)))
    assert s4["n_checkpoint"] == 1
    rows = lines(log.day_path(T0))
    kinds = [r["kind"] for r in rows]
    assert kinds == ["row", "row", "poll", "row", "gone", "poll", "poll", "row", "poll"]
    assert rows[-1]["slot"] == "D" and rows[-2]["reason"] == "checkpoint"


def test_changelog_src_ts_does_not_enter_hash(tmp_path):
    c = Clock()
    log = ChangeLog(tmp_path, "s", 3600, clock=c)
    log.commit("A", c.t, PollResult({"m:1": {"v": 1}}, src_ts={"m:1": "t1"}))
    c.t += 60
    s = log.commit("B", c.t, PollResult({"m:1": {"v": 1}}, src_ts={"m:1": "t2"}))
    assert s["n_changed"] == 0
    assert lines(log.day_path(T0))[0]["src_ts"] == "t1"


def test_changelog_hash_checkpoint_and_new_day_file(tmp_path):
    c = Clock()
    log = ChangeLog(tmp_path, "s", 86400, hash_checkpoint=True, clock=c)
    log.commit("A", c.t, PollResult({"m:1": {"description": "long text"}}))
    c.t += 86400  # next UTC day: new file -> every observed key is checkpointed
    s = log.commit("B", c.t, PollResult({"m:1": {"description": "long text"}}))
    assert s["new_file"] and s["n_checkpoint"] == 1
    day2 = lines(log.day_path(c.t))
    assert day2[0]["kind"] == "hash" and "data" not in day2[0]


def test_changelog_corrupt_state_rewrites_everything(tmp_path):
    c = Clock()
    log = ChangeLog(tmp_path, "s", 3600, clock=c)
    log.commit("A", c.t, PollResult({"k:1": {"v": 1}}))
    (tmp_path / common.STATE_FILE).write_text("{not json")
    c.t += 60
    log2 = ChangeLog(tmp_path, "s", 3600, clock=c)
    s = log2.commit("B", c.t, PollResult({"k:1": {"v": 1}}))
    assert s["state_reset"] and s["n_new"] == 1  # unknown -> written in full again, never silently skipped


def test_changelog_repairs_torn_tail_and_slot_idempotency_survives_state_loss(tmp_path):
    c = Clock()
    log = ChangeLog(tmp_path, "s", 3600, clock=c)
    log.commit("A", c.t, PollResult({"k:1": {"v": 1}}))
    p = log.day_path(c.t)
    with open(p, "a") as fh:
        fh.write('{"kind":"row","slot":"B","key":"k:2"')  # crash mid-write: torn line, no commit
    (tmp_path / common.STATE_FILE).unlink()
    log2 = ChangeLog(tmp_path, "s", 3600, clock=c)
    assert log2.already_done("A", c.t)  # recovered from the day file's commit lines
    assert not log2.already_done("B", c.t)  # torn rows have no commit
    log2.commit("B", c.t, PollResult({"k:2": {"v": 2}}))
    raw = p.read_text().splitlines()
    assert raw[2] == '{"kind":"row","slot":"B","key":"k:2"'  # torn line isolated, not merged
    assert json.loads(raw[-1])["kind"] == "poll" and json.loads(raw[-1])["slot"] == "B"


def test_changelog_fail_writes_gap_line_only(tmp_path):
    c = Clock()
    log = ChangeLog(tmp_path, "s", 3600, clock=c)
    log.fail("A", c.t, "HTTP 503")
    rows = lines(log.day_path(c.t))
    assert rows == [{**rows[0], "kind": "poll", "ok": False, "error": "HTTP 503"}]
    assert not log.already_done("A", c.t)  # a failed slot may be retried


# ---- runner -----------------------------------------------------------------------------------------------------

PI_PAYLOAD = {"markets": [{"id": 7589, "name": "House seats?", "shortName": "House", "image": "x.jpg",
                           "url": "https://u", "status": "Open", "timeStamp": "2026-10-19T17:51:30.1",
                           "contracts": [{"id": 28361, "name": "192 or fewer", "shortName": "192", "status": "Open",
                                          "dateEnd": "NA", "image": "y", "lastTradePrice": 0.32, "bestBuyYesCost": 0.33,
                                          "bestBuyNoCost": 0.69, "bestSellYesCost": 0.31, "bestSellNoCost": 0.67,
                                          "lastClosePrice": 0.33, "displayOrder": 0}]}]}


def pi_transport(payload):
    def tr(url, headers, timeout):
        assert url == predictit.URL
        return 200, {}, json.dumps(payload).encode()
    return tr


def test_run_stream_predictit_end_to_end_and_idempotent(tmp_path):
    c = Clock()
    kw = dict(transport=pi_transport(PI_PAYLOAD), clock=c, sleep=c.sleep, mono=c.mono, free_fn=free_ok, du_fn=du_small)
    code, s = run_stream(predictit.SPEC, tmp_path, **kw)
    assert code == 0 and s["status"] == "committed" and s["n_new"] == 2 and s["requests"] == 1
    code, s = run_stream(predictit.SPEC, tmp_path, **kw)
    assert code == 0 and s["status"] == "slot_done"
    c.t += 60
    p2 = json.loads(json.dumps(PI_PAYLOAD))
    p2["markets"][0]["contracts"][0]["bestBuyYesCost"] = 0.34
    p2["markets"][0]["timeStamp"] = "2026-10-19T17:52:30.1"
    code, s = run_stream(predictit.SPEC, tmp_path, **{**kw, "transport": pi_transport(p2)})
    assert s["n_changed"] == 1 and s["n_new"] == 0  # the timestamp alone is not a change
    f = tmp_path / "research_lab" / "stream_predictit"
    rows = lines(next(f.glob("2026*.jsonl")))
    c_rows = [r for r in rows if r.get("key") == "c:28361"]
    assert [r["data"]["buy_yes"] for r in c_rows] == [0.33, 0.34]
    assert "image" not in json.dumps(rows)


def test_run_stream_headroom_refusal_writes_nothing(tmp_path):
    c = Clock()
    code, s = run_stream(predictit.SPEC, tmp_path, transport=pi_transport(PI_PAYLOAD), clock=c, sleep=c.sleep,
                         free_fn=lambda p: 10**9, du_fn=du_small)
    assert code == common.EX_TEMPFAIL and s["status"] == "headroom"
    assert not list((tmp_path / "research_lab" / "stream_predictit").glob("*.jsonl"))


def test_run_stream_failure_records_gap_and_exit_1(tmp_path):
    c = Clock()
    code, s = run_stream(predictit.SPEC, tmp_path, transport=lambda u, h, t: (500, {}, b""), clock=c,
                         sleep=c.sleep, free_fn=free_ok, du_fn=du_small)
    assert code == 1 and s["status"] == "failed"
    rows = lines(next((tmp_path / "research_lab" / "stream_predictit").glob("*.jsonl")))
    assert len(rows) == 1 and rows[0]["ok"] is False and len(rows[0]["fetches"]) == 3


def test_run_stream_busy_lock(tmp_path):
    import fcntl
    sdir = tmp_path / "research_lab" / "stream_predictit"
    sdir.mkdir(parents=True)
    with open(sdir / common.LOCK_FILE, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        code, s = run_stream(predictit.SPEC, tmp_path, transport=pi_transport(PI_PAYLOAD), free_fn=free_ok,
                             du_fn=du_small)
    assert code == 0 and s["status"] == "busy"


# ---- parsers ----------------------------------------------------------------------------------------------------


def test_predictit_parse_rejects_bad_payload():
    with pytest.raises(FetchError):
        predictit.parse({"oops": 1})
    with pytest.raises(FetchError):
        predictit.parse({"markets": []})
    r = predictit.parse(PI_PAYLOAD)
    assert r.items["c:28361"]["sell_yes"] == 0.31 and r.src_ts["m:7589"] == "2026-10-19T17:51:30.1"
    assert r.scopes == ("m:", "c:")


def smarkets_transport(log):
    ev = {"events": [{"id": "44136686", "name": "2028 Presidential Election Winner", "type": "politics",
                      "state": "upcoming", "full_slug": "/politics/us"}], "pagination": {"next_page": None}}
    mk = {"markets": [{"id": "83359513", "event_id": "44136686", "name": "Winner", "state": "open"},
                      {"id": "1", "event_id": "44136686", "name": "Old", "state": "settled"}]}
    ct = {"contracts": [{"id": "236572813", "market_id": "83359513", "name": "AOC", "state_or_outcome": "open"}]}
    q = {"236572813": {"bids": [{"price": 1754, "quantity": 5}, {"price": 1700, "quantity": 1},
                                {"price": 1600, "quantity": 1}, {"price": 1500, "quantity": 1}],
                       "offers": [{"price": 1818, "quantity": 2}]}}
    lep = {"last_executed_prices": {"83359513": [{"contract_id": "236572813", "last_executed_price": "17.9",
                                                  "timestamp": "2026-10-18T18:35:03Z"}]}}
    vol = {"volumes": [{"market_id": "83359513", "volume": 271402}]}

    def tr(url, headers, timeout):
        log.append(url)
        if "/events/?" in url:
            body = ev
        elif "/events/" in url and url.endswith("/markets/"):
            body = mk
        elif url.endswith("/contracts/"):
            body = ct
        elif url.endswith("/quotes/"):
            body = q
        elif url.endswith("/last_executed_prices/"):
            body = lep
        elif url.endswith("/volumes/"):
            body = vol
        else:
            raise AssertionError(url)
        return 200, {}, json.dumps(body).encode()
    return tr


def test_smarkets_poll_catalogue_then_quotes_only_and_rate_limit(tmp_path):
    c = Clock()
    urls: list[str] = []
    kw = dict(transport=smarkets_transport(urls), clock=c, sleep=c.sleep, mono=c.mono, free_fn=free_ok, du_fn=du_small)
    code, s = run_stream(smarkets.SPEC, tmp_path, **kw)
    assert code == 0 and s["n_new"] == 4  # ev, mk (settled market dropped), ct, q
    assert not any("/markets/1," in u or u.endswith("/markets/1/quotes/") for u in urls)
    assert all(x >= 1.0 - 1e-9 for x in c.sleeps)  # 1 rps: every request waited >= 1 s after the previous one
    n_first = len(urls)
    rows = lines(next((tmp_path / "research_lab" / "stream_smarkets").glob("*.jsonl")))
    q = next(r for r in rows if r.get("key") == "q:236572813")["data"]
    assert q["bids"] == [[1754, 5], [1700, 1], [1600, 1]] and q["last"] == "17.9" and q["market_id"] == "83359513"
    c.t += 300
    code, s = run_stream(smarkets.SPEC, tmp_path, **kw)
    assert code == 0 and s["n_gone"] == 0  # catalogue keys not observed on a quotes-only poll are not "gone"
    assert len(urls) - n_first == 2  # quotes + last executed prices only
    c.t += 3600
    run_stream(smarkets.SPEC, tmp_path, **kw)
    assert any("/events/?" in u for u in urls[n_first + 2:])  # hourly catalogue refresh


ESPN_BOARD = {"events": [{"id": "401", "name": "A at B", "date": "2026-10-20T00:15Z", "competitions": [{
    "date": "2026-10-20T00:15Z",
    "status": {"period": 0, "displayClock": "0:00", "type": {"state": "pre", "completed": False, "shortDetail": "8:15 PM"}},
    "competitors": [{"id": "25", "homeAway": "home", "score": "0", "team": {"abbreviation": "SF", "logo": "l"}},
                    {"id": "28", "homeAway": "away", "score": "0", "team": {"abbreviation": "WSH"}}],
    "odds": [{"provider": {"id": "100", "name": "DraftKings", "logos": [{"href": "h"}]}, "details": "SF -7.5",
              "overUnder": 52.5, "spread": -7.5,
              "homeTeamOdds": {"favorite": True, "favoriteAtOpen": True, "team": {"abbreviation": "SF"}},
              "awayTeamOdds": {"favorite": False, "favoriteAtOpen": False},
              "moneyline": {"displayName": "Moneyline", "home": {"close": {"odds": "-395", "link": {"href": "dk"}},
                                                                  "open": {"odds": "-250"}},
                            "away": {"close": {"odds": "+310"}, "open": {"odds": "+205"}}},
              "pointSpread": {"home": {"close": {"line": "-7.5", "odds": "-102", "link": {}}}},
              "total": {"over": {"open": {"line": "o51.5", "odds": "-110"}}}}]}]}]}


def test_espn_parse_compacts_odds_and_drops_links():
    items = espn_odds.parse_board("football/nfl", ESPN_BOARD)
    g = items["g:football/nfl:401"]
    o = g["odds"][0]
    assert o["moneyline"] == {"home": {"close": {"odds": "-395"}, "open": {"odds": "-250"}},
                              "away": {"close": {"odds": "+310"}, "open": {"odds": "+205"}}}
    assert o["point_spread"]["home"]["close"] == {"line": "-7.5", "odds": "-102"}
    assert o["provider"] == "DraftKings" and o["home_fav_open"] is True
    assert g["competitors"][0] == {"id": "25", "home_away": "home", "abbr": "SF", "score": "0"}
    blob = json.dumps(items)
    assert "href" not in blob and "logo" not in blob


def test_espn_poll_one_league_failing_keeps_others():
    c = Clock()

    def tr(url, headers, timeout):
        return (200, {}, json.dumps(ESPN_BOARD).encode()) if "nfl" in url else (404, {}, b"")

    h = Http(transport=tr, clock=c, mono=c.mono, sleep=c.sleep)
    r = espn_odds.poll(h, {}, leagues={"football/nfl": {}, "hockey/nhl": {}})
    assert list(r.items) == ["g:football/nfl:401"] and r.meta["failed"][0]["league"] == "hockey/nhl"
    assert r.scopes == ()
    h2 = Http(transport=lambda u, hd, t: (404, {}, b""), clock=c, mono=c.mono, sleep=c.sleep)
    with pytest.raises(FetchError):
        espn_odds.poll(h2, {}, leagues={"hockey/nhl": {}})


def make_capture(root: Path, cid: str, rows: list[tuple[str, str, str]], state: str = "complete") -> None:
    d = root / cid
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": state}))
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["capture_id", "market_id", "closed", "volume24hr", "updated_at"])
        for mid, closed, vol in rows:
            w.writerow([cid, mid, closed, vol, "x"])


def test_gamma_frame_latest_complete_capture_and_order(tmp_path):
    snaps = tmp_path / "research_lab" / "snapshots"
    make_capture(snaps, "20261019T183101Z_48fb645a", [("1", "False", "5")])
    make_capture(snaps, "20261019T203102Z_22a57dc7", [("2", "False", "10"), ("3", "True", "99"), ("4", "False", "0"),
                                                     ("5", "False", "10"), ("6", "False", "50")])
    make_capture(snaps, "20261019T223101Z_aaaaaaaa", [("9", "False", "1")], state="partial")
    cid, p = gamma_rules.latest_complete_capture(snaps)
    assert cid == "20261019T203102Z_22a57dc7"
    assert gamma_rules.build_frame(p / "rows.csv.gz") == ["6", "2", "5"]  # vol desc, id asc; closed and 0 dropped


def test_gamma_poll_batches_top_and_full(tmp_path):
    snaps = tmp_path / "research_lab" / "snapshots"
    make_capture(snaps, "20261019T203102Z_22a57dc7", [(str(i), "False", str(200 - i)) for i in range(1, 121)])
    c = Clock()
    asked: list[list[str]] = []

    def tr(url, headers, timeout):
        from urllib.parse import parse_qs, urlparse
        ids = parse_qs(urlparse(url).query)["id"]
        asked.append(ids)
        out = [{"id": i, "question": f"Q{i}?", "description": "rules", "outcomes": '["Yes","No"]',
                "outcomePrices": '["0.4","0.6"]', "bestBid": 0.4,
                "events": [{"id": "e1", "title": "E", "description": "event rules", "volume": 5}]}
               for i in ids if i != "7"]
        return 200, {}, json.dumps(out).encode()

    h = Http(transport=tr, rps=2.0, clock=c, mono=c.mono, sleep=c.sleep)
    r = gamma_rules.poll(h, {}, t0=T0, data_dumps=tmp_path, top=60, full=False)
    assert [len(a) for a in asked] == [50, 10] and r.meta["missing"] == 1 and r.meta["frame_size"] == 120
    m = r.items["m:1"]
    assert m["description"] == "rules" and m["event_ids"] == ["e1"]
    assert "outcomePrices" not in json.dumps(r.items) and "bestBid" not in json.dumps(r.items)
    assert r.items["e:e1"] == {"title": "E", "description": "event rules", "resolutionSource": None,
                               "endDate": None, "startDate": None}
    asked.clear()
    r2 = gamma_rules.poll(h, r.extra_state, t0=T0, data_dumps=tmp_path, full=True)
    assert sum(len(a) for a in asked) == 120 and r2.meta["frame_rebuilt"] is False


def test_gamma_poll_without_capture_is_pending(tmp_path):
    h = Http(transport=lambda u, hd, t: (200, {}, b"[]"))
    with pytest.raises(NotNow):
        gamma_rules.poll(h, {}, t0=T0, data_dumps=tmp_path)


def test_gamma_rule_edit_is_logged_as_changed_with_full_text(tmp_path):
    c = Clock()
    log = ChangeLog(tmp_path, "gamma_rules", 86400, hash_checkpoint=True, clock=c)
    log.commit("A", c.t, PollResult(gamma_rules.market_items([{"id": 1, "description": "v1", "events": []}])))
    c.t += 3600
    s = log.commit("B", c.t, PollResult(gamma_rules.market_items([{"id": 1, "description": "v1 + clarification",
                                                                    "events": []}])))
    assert s["n_changed"] == 1
    last = [r for r in lines(log.day_path(T0)) if r["kind"] == "row"][-1]
    assert last["reason"] == "changed" and last["data"]["description"] == "v1 + clarification"


def test_run_stream_script_specs_registered():
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_stream", Path(__file__).resolve().parents[2] / "scripts" / "run_stream.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert set(mod.SPECS) == {"predictit", "smarkets", "espn_odds", "gamma_rules"}
    assert all(s.dirname.startswith("stream_") for s in mod.SPECS.values())
