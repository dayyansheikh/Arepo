# ruff: noqa: E501
"""Reward-parameter collector: paging, write-once, failure state (fake transport, no network)."""

from __future__ import annotations

import gzip
import hashlib
import json

import pytest

from astrolabe.research_lab import reward_params_collector as rpc


def fake_fetch(pages_native=3, fail_on=None):
    calls = []

    def f(url, params):
        calls.append(dict(params))
        if params.get("sponsored") == "true":
            return 200, {"data": [{"condition_id": "0xs", "sponsored_daily_rate": 1.5}], "next_cursor": "LTE="}
        cur = params.get("next_cursor")
        i = 0 if cur is None else int(cur)
        if fail_on is not None and i == fail_on:
            return 503, None
        nxt = "LTE=" if i + 1 >= pages_native else str(i + 1)
        return 200, {"data": [{"condition_id": f"0x{i}{k}", "rewards_config": [{"rate_per_day": 1}]} for k in range(2)],
                     "next_cursor": nxt, "limit": 500, "count": 2}

    f.calls = calls
    return f


def test_walk_feed_pages_until_last_cursor():
    f = fake_fetch(3)
    recs, st = rpc.walk_feed(f, {}, sleep=lambda s: None)
    assert st["complete"] and st["pages"] == 3 and len(recs) == 6
    assert [c.get("next_cursor") for c in f.calls] == [None, "1", "2"]


def test_walk_feed_page_cap_and_failure():
    recs, st = rpc.walk_feed(fake_fetch(10), {}, max_pages=2, sleep=lambda s: None)
    assert not st["complete"] and "page cap" in st["error"] and len(recs) == 4
    recs, st = rpc.walk_feed(fake_fetch(3, fail_on=1), {}, max_retries=1, sleep=lambda s: None)
    assert not st["complete"] and st["error"].startswith("HTTP 503") and len(recs) == 2 and st["requests"] == 3


def test_capture_write_once_and_manifest(tmp_path):
    man = rpc.capture(tmp_path, fake_fetch(2), capture_id="20261021T000000Z_abcd", sleep=lambda s: None)
    d = tmp_path / "20261021T000000Z_abcd"
    assert man["state"] == "complete" and man["markets_native"] == 4 and man["markets_sponsored"] == 1
    data = (d / "rows.jsonl.gz").read_bytes()
    assert hashlib.sha256(data).hexdigest() == man["rows_sha256"]
    lines = [json.loads(x) for x in gzip.decompress(data).decode().splitlines()]
    assert {x["feed"] for x in lines} == {"native", "sponsored"} and len(lines) == 5
    assert json.loads((d / "manifest.json").read_text())["capture_id"] == "20261021T000000Z_abcd"
    with pytest.raises(FileExistsError):
        rpc.capture(tmp_path, fake_fetch(2), capture_id="20261021T000000Z_abcd", sleep=lambda s: None)
    assert not list(tmp_path.glob(".*partial"))


def test_capture_failed_state_is_kept(tmp_path):
    man = rpc.capture(tmp_path, fake_fetch(3, fail_on=2), capture_id="c1", sleep=lambda s: None)
    assert man["state"] == "failed" and man["markets_native"] == 4
    assert (tmp_path / "c1" / "manifest.json").exists()
