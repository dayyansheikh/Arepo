"""Collector tests with a fake transport (no network)."""

from __future__ import annotations

import csv
import gzip
import json

import pytest

from astrolabe.research_lab import collector
from astrolabe.research_lab.extract import COLUMNS, market_row, parse_num

LIMIT = collector.PARAMS["limit"]


def mk(i: int) -> dict:
    return {
        "id": str(i), "conditionId": f"0x{i}", "closed": False, "active": True,
        "outcomes": '["Yes","No"]', "bestBid": "0.4", "bestAsk": 0.45,
        "spread": {"$decimal": "0.05"},
        "lastTradePrice": "0.42", "oneHourPriceChange": -0.01, "liquidity": "1000.5",
        "volume24hr": 12, "endDate": "2027-01-01T00:00:00Z", "updatedAt": "2026-10-10T00:00:00Z",
        "events": [{"id": 77}],
    }


def page(ids, cursor=None) -> bytes:
    body: dict = {"markets": [mk(i) for i in ids]}
    if cursor is not None:
        body["next_cursor"] = cursor
    return json.dumps(body).encode()


class Fake:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, params):
        self.calls.append(dict(params))
        r = self.responses.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


def run(tmp_path, responses, **kw):
    fake = Fake(responses)
    sleeps: list[float] = []
    m = collector.collect(
        tmp_path, transport=fake, sleep=sleeps.append, commit="abc", **kw
    )
    return m, fake, sleeps


def full(start, cursor):
    return (200, page(range(start, start + LIMIT), cursor), {})


def test_paginates_to_exhaustion_and_passes_cursors(tmp_path):
    m, fake, _ = run(tmp_path, [full(0, "c1"), full(100, "c2"), (200, page([200, 201]), {})])
    assert m["state"] == "complete"
    assert (m["request_count"], m["page_count"], m["row_count"]) == (3, 3, 202)
    assert [c.get("after_cursor") for c in fake.calls] == [None, "c1", "c2"]
    assert all(c["closed"] == "false" and c["limit"] == LIMIT for c in fake.calls)
    assert len(m["pages"]) == 3 and len(m["pages"][0]["sha256"]) == 64
    out = tmp_path / m["capture_id"]
    assert (out / "rows.csv.gz").exists() and (out / "manifest.json").exists()
    assert not (out / "raw").exists()
    assert not list(tmp_path.glob(".tmp_*"))
    with gzip.open(out / "rows.csv.gz", "rt") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0])[: len(COLUMNS)] == COLUMNS and rows[0]["page_index"] == "0"


def test_retry_backoff_on_429_then_success(tmp_path):
    m, fake, sleeps = run(tmp_path, [(429, b"", {}), (503, b"", {}), (200, page([1]), {})])
    assert m["state"] == "complete" and m["request_count"] == 3 and m["retry_count"] == 2
    assert sleeps[:2] == [1.0, 2.0]


def test_retry_exhaustion_is_incomplete_with_manifest(tmp_path):
    m, _, _ = run(tmp_path, [(429, b"", {})] * 6)
    assert m["state"].startswith("incomplete:retry_exhausted")
    assert (tmp_path / m["capture_id"] / "manifest.json").exists()


def test_incomplete_on_request_cap(tmp_path):
    m, _, _ = run(tmp_path, [full(0, "c1"), full(100, "c2"), full(200, "c3")], max_requests=2)
    assert m["state"] == "incomplete:request_cap" and m["page_count"] == 2


def test_incomplete_on_time_cap(tmp_path):
    ticks = iter(range(0, 10000, 1000))
    m, _, _ = run(tmp_path, [full(0, "c1"), full(100, "c2")], monotonic=lambda: next(ticks))
    assert m["state"] == "incomplete:time_cap"


def test_protocol_violations_are_incomplete(tmp_path):
    # full page without cursor is not proof of exhaustion
    m, _, _ = run(tmp_path, [(200, page(range(LIMIT)), {})])
    assert m["state"].startswith("incomplete:protocol")
    # cursor cycle
    m, _, _ = run(tmp_path, [full(0, "c1"), full(100, "c1"), full(200, "c1")])
    assert m["state"] == "incomplete:cursor_cycle"
    # short page that still advertises a cursor
    m, _, _ = run(tmp_path, [(200, page([1, 2], "c9"), {})])
    assert m["state"].startswith("incomplete:protocol")


def test_non_retryable_status(tmp_path):
    m, _, _ = run(tmp_path, [(404, b"", {})])
    assert m["state"] == "incomplete:http_404"


def test_receipt_clock_monotonic(tmp_path):
    times = iter(["2026-10-10T00:00:05.000000Z", "2026-10-10T00:00:06.000000Z",
                  "2026-10-10T00:00:04.000000Z", "2026-10-10T00:00:07.000000Z",
                  "2026-10-10T00:00:08.000000Z", "2026-10-10T00:00:09.000000Z"])
    m, _, _ = run(tmp_path, [full(0, "c1"), (200, page([300]), {})], now=lambda: next(times))
    rec = [p["received_utc"] for p in m["pages"]]
    assert rec == sorted(rec)


def test_row_parity_with_extract_market_row(tmp_path):
    m, _, _ = run(tmp_path, [(200, page([5]), {})])
    with gzip.open(tmp_path / m["capture_id"] / "rows.csv.gz", "rt") as fh:
        got = next(csv.DictReader(fh))
    want = market_row(mk(5), m["capture_id"], m["started_utc"], m["pages"][0]["received_utc"])
    for k in COLUMNS:
        if k in {"capture_start_utc", "received_utc"}:
            continue
        v = want[k]
        assert got[k] == ("" if v is None else str(v)), k
    assert got["spread"] == "0.05" and got["best_ask"] == "0.45"
    assert got["received_utc"] == m["pages"][0]["received_utc"]


def test_parse_num_plain_and_wrapped():
    assert parse_num("0.5") == 0.5 and parse_num(3) == 3.0
    assert parse_num({"$decimal": "0.96"}) == 0.96 and parse_num(None) is None
    assert parse_num("") is None and parse_num(True) is None


def test_duplicates_counted_and_keep_raw(tmp_path):
    m, _, _ = run(tmp_path, [full(0, "c1"), (200, page([0, 150]), {})], keep_raw=True)
    assert m["duplicates"] == 1 and m["row_count"] == 101
    assert (tmp_path / m["capture_id"] / "raw" / "page_00001.json.gz").exists()


def test_atomic_output_on_exception(tmp_path):
    fake = Fake([full(0, "c1"), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        collector.collect(tmp_path, transport=fake, sleep=lambda s: None, commit="x")
    dirs = [d for d in tmp_path.iterdir()]
    assert len(dirs) == 1 and not dirs[0].name.startswith(".tmp_")
    man = json.loads((dirs[0] / "manifest.json").read_text())
    assert man["state"].startswith("incomplete:exception") and man["page_count"] == 1


class Server:
    """Fake keyset server over ids 0..n-1; cursor ``k<i>`` encodes the last market key."""

    def __init__(self, n, blocked=(), html=True):
        self.n, self.blocked, self.html = n, set(blocked), html
        self.calls: list[dict] = []

    def __call__(self, params):
        self.calls.append(dict(params))
        cur = params.get("after_cursor")
        if cur in self.blocked:
            if self.html:
                return 403, b"<html>Attention Required! | Cloudflare</html>", {
                    "content-type": "text/html"}
            return 403, b'{"error":"forbidden"}', {"content-type": "application/json"}
        start = 0 if cur is None else int(cur[1:]) + 1
        ids = list(range(start, min(self.n, start + params["limit"])))
        nxt = f"k{ids[-1]}" if len(ids) == params["limit"] else None
        return 200, page(ids, nxt), {}


def run_server(tmp_path, server, **kw):
    m = collector.collect(tmp_path, transport=server, sleep=lambda s: None, commit="c", **kw)
    with gzip.open(tmp_path / m["capture_id"] / "rows.csv.gz", "rt") as fh:
        got = sorted(int(r["market_id"]) for r in csv.DictReader(fh))
    return m, got


def test_blocked_cursor_detour_completes_full_set(tmp_path):
    srv = Server(450, blocked={"k199"})
    m, got = run_server(tmp_path, srv)
    assert m["state"] == "complete" and got == list(range(450))
    assert m["collector_version"] == "universe-snapshot-v2"
    (d,) = m["blocked_cursor_detours"]
    assert d["blocked_cursor"] == "k199" and len(d["blocked_cursor_sha256"]) == 64
    assert d["reduced_limit"] == 99 and d["overlap_rows"] == 99 and d["tries"] == [99]
    assert m["duplicates"] == 100  # 99 in the detour page + id 199 again
    assert [(c.get("after_cursor"), c["limit"]) for c in srv.calls][:5] == [
        (None, 100), ("k99", 100), ("k199", 100), ("k99", 99), ("k198", 100)]
    assert m["pages"][2]["limit_requested"] == 99 and "limit_requested" not in m["pages"][0]
    assert m["request_count"] == len(srv.calls)


def test_detour_on_first_page_continuation_and_terminal_with_mixed_limits(tmp_path):
    # final short page requested after a detour must be judged against limit 100
    srv = Server(250, blocked={"k99"})
    m, got = run_server(tmp_path, srv)
    assert m["state"] == "complete" and got == list(range(250))
    assert m["blocked_cursor_detours"][0]["overlap_rows"] == 99  # previous cursor None: restart
    assert srv.calls[2] == {**srv.calls[0], "limit": 99}


def test_terminal_page_uses_requested_limit(tmp_path):
    # a 99-limit detour page holding 99 markets without cursor is not proof of exhaustion
    srv = Server(199, blocked={"k99"})
    srv.__class__ = type("S2", (Server,), {})
    base = Server.__call__

    def call(self, params):
        status, body, headers = base(self, params)
        if params["limit"] == 99 and status == 200:
            payload = json.loads(body)
            payload.pop("next_cursor", None)
            body = json.dumps(payload).encode()
        return status, body, headers

    srv.__class__.__call__ = call
    m, _ = run_server(tmp_path, srv)
    assert m["state"].startswith("incomplete:protocol")


def test_repeated_blocks_exhaust_tries(tmp_path):
    class Always(Server):
        def __call__(self, params):
            s, b, h = super().__call__(params)
            if params["limit"] != 100 and s == 200:  # every detour yields another blocked cursor
                b = page(range(5, 5 + params["limit"]), f"kBAD{params['limit']}")
            return s, b, h

    srv = Always(450, blocked={"k199", *(f"kBAD{i}" for i in range(80, 100))})
    m, _ = run_server(tmp_path, srv)
    assert m["state"] == "incomplete:http_403"
    assert [c["limit"] for c in srv.calls if c["limit"] != 100] == list(range(99, 89, -1))


def test_non_html_403_is_incomplete_without_detour(tmp_path):
    srv = Server(450, blocked={"k199"}, html=False)
    m, _ = run_server(tmp_path, srv)
    assert m["state"] == "incomplete:http_403" and m["blocked_cursor_detours"] == []
    assert len(srv.calls) == 3


def test_detour_counts_against_request_cap(tmp_path):
    m, _ = run_server(tmp_path, Server(450, blocked={"k199"}), max_requests=4)
    assert m["state"] == "incomplete:request_cap" and m["request_count"] == 4
