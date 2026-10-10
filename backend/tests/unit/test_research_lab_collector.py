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
