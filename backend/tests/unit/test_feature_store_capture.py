"""Synthetic transport only; live probes are explicit separate operator actions."""

import asyncio
import json
import uuid
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store import capture
from astrolabe.feature_store.capture import (
    Budget,
    CaptureJournal,
    diagnostic_summary,
    finish_parse,
    verify_capture,
)


class Stream(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk


def journal(tmp_path, body=b'{"price":0.123456789012345678900,"id":123456789012345678901}',
            *, status=200, headers=None, budget=Budget()):
    async def handler(request):
        return httpx.Response(status, stream=Stream([body]), headers=headers)

    return CaptureJournal(tmp_path.resolve() / ("fs2_capture_" + uuid.uuid4().hex),
                          transport=httpx.MockTransport(handler), budget=budget)


async def fetch(store):
    return await store.fetch("coinbase.btc_usd.ticker", {})


@pytest.mark.asyncio
async def test_capture_preserves_bytes_exact_decimal_and_id_before_parse(tmp_path):
    store = journal(tmp_path)
    result = await fetch(store)
    assert result["parsed"]["value"] == {
        "price": {"$decimal": "0.123456789012345678900"}, "id": 123456789012345678901,
    }
    assert result["receipt"]["capture_kind"] == "synthetic"
    assert result["receipt"]["clock_error_bound_ms"] is None
    assert result["raw_ack"]["durable_ack"]["utc"] <= result["parsed"]["parsed_at"]["utc"]
    assert result["parsed"]["parsed_at"]["utc"] <= result["parsed_ack"]["durable_ack"]["utc"]
    original = {p.name: p.read_bytes() for p in Path(result["folder"]).iterdir()}
    assert finish_parse(Path(result["folder"])) == result
    assert original == {p.name: p.read_bytes() for p in Path(result["folder"]).iterdir()}
    assert diagnostic_summary(result)["research_admitted"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [b'{"x":NaN}', b'{"x":1,"x":2}', b'not json', b'\xff'])
async def test_invalid_json_is_preserved_not_empty_success(tmp_path, raw):
    result = await fetch(journal(tmp_path, raw))
    assert result["raw"] == raw
    assert result["parsed"]["parse_error"] == "invalid_json"
    assert result["parsed"]["value"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [301, 403, 429, 503])
async def test_http_failure_no_follow_or_retry(tmp_path, status):
    store = journal(tmp_path, status=status, headers={"location": "https://example.com/private"})
    result = await fetch(store)
    assert store.count == 1
    assert result["parsed"]["parse_error"] == "http_non_success"
    assert result["receipt"]["status"] == status


@pytest.mark.asyncio
async def test_byte_limit_preserves_partial_transport_and_blocks_more(tmp_path):
    store = journal(tmp_path, b"abcdefghijkl", budget=Budget(total_bytes=5))
    result = await fetch(store)
    assert result["raw"] == b"abcde"
    assert result["parsed"]["parse_error"] == "byte_budget_exceeded"
    with pytest.raises(ValueError, match="budget"):
        await fetch(store)


@pytest.mark.asyncio
async def test_transport_failure_preserves_attempt(tmp_path):
    async def handler(request):
        return httpx.Response(200, stream=Stream([b'{"x":', httpx.ReadError("secret")]))

    store = CaptureJournal(tmp_path.resolve() / "fs2_capture_gap",
                           transport=httpx.MockTransport(handler))
    result = await fetch(store)
    assert result["raw"] == b'{"x":'
    assert result["parsed"]["parse_error"] == "ReadError"
    assert "secret" not in json.dumps(result["receipt"])


@pytest.mark.asyncio
async def test_corruption_or_torn_receipt_refused(tmp_path):
    result = await fetch(journal(tmp_path))
    folder = Path(result["folder"])
    (folder / "raw.bin").write_bytes(b"different")  # deliberate fixture corruption
    with pytest.raises(ValueError, match="integrity"):
        verify_capture(folder)


@pytest.mark.asyncio
async def test_crash_after_raw_ack_recovers_with_new_parse_clock(tmp_path, monkeypatch):
    store = journal(tmp_path)
    original = capture.finish_parse
    monkeypatch.setattr(capture, "finish_parse", lambda folder: (_ for _ in ()).throw(
        RuntimeError("crash before parse")))
    with pytest.raises(RuntimeError):
        await fetch(store)
    folder = next(p for p in store.root.iterdir() if p.is_dir())
    old = verify_capture(folder, raw_only=True)
    monkeypatch.setattr(capture, "finish_parse", original)
    monkeypatch.setattr(capture, "_CLOCK_SESSION", str(uuid.uuid4()))
    result = finish_parse(folder)
    assert result["receipt"] == old["receipt"]
    assert result["parsed"]["parsed_at"]["clock_session_id"] != (
        result["receipt"]["first_received"]["clock_session_id"])


@pytest.mark.asyncio
async def test_fsync_failure_never_acknowledged_or_overwritten(tmp_path, monkeypatch):
    store = journal(tmp_path)
    original = capture._write_once

    def fail_ack(path, content):
        if path.name == "parsed_ack.json":
            raise OSError("disk unavailable")
        original(path, content)

    monkeypatch.setattr(capture, "_write_once", fail_ack)
    with pytest.raises(OSError):
        await fetch(store)
    folder = next(p for p in store.root.iterdir() if p.is_dir())
    assert (folder / "parsed.json").exists()
    with pytest.raises(ValueError, match="partial parse"):
        finish_parse(folder)
    with pytest.raises(FileExistsError):
        capture._write_once(folder / "raw.bin", b"replacement")


@pytest.mark.asyncio
async def test_request_time_and_parameter_bounds(tmp_path, monkeypatch):
    store = journal(tmp_path, budget=Budget(requests=1))
    with pytest.raises(ValueError):
        await store.fetch("gamma.markets", {"limit": 100, "active": "true", "closed": "false"})
    with pytest.raises(ValueError):
        await store.fetch("coinbase.btc_usd.ticker", {"api_key": "not allowed"})
    assert store.count == 0
    await fetch(store)
    with pytest.raises(ValueError, match="budget"):
        await fetch(store)
    second = journal(tmp_path)
    monkeypatch.setattr(second, "started", second.started - 100)
    with pytest.raises(ValueError, match="time budget"):
        await fetch(second)


@pytest.mark.asyncio
async def test_parent_link_and_new_receipt_for_each_request(tmp_path):
    store = journal(tmp_path)
    first = await fetch(store)
    second = await store.fetch("coinbase.btc_usd.ticker", {},
                               previous_capture_id=first["receipt"]["capture_id"])
    assert second["receipt"]["receipt_ordinal"] == 2
    assert second["receipt"]["first_received"] != first["receipt"]["first_received"]
    with pytest.raises(ValueError):
        await store.fetch("coinbase.btc_usd.ticker", {}, previous_capture_id="../secret")


@pytest.mark.asyncio
async def test_clock_regression_retained_and_refused(tmp_path, monkeypatch):
    store = journal(tmp_path)
    original = capture._clock
    calls = 0

    def regress():
        nonlocal calls
        calls += 1
        value = original()
        if calls > 2:
            value["utc"] = "2000-01-01T00:00:00.000000Z"
        return value

    monkeypatch.setattr(capture, "_clock", regress)
    with pytest.raises(ValueError, match="clock regression"):
        await fetch(store)
    folder = next(p for p in store.root.iterdir() if p.is_dir())
    assert (folder / "raw.bin").exists()
    assert not (folder / "parsed.json").exists()


def test_directory_and_budget_guards(tmp_path):
    with pytest.raises(ValueError):
        CaptureJournal(Path("relative/fs2_capture_bad"))
    with pytest.raises(ValueError):
        Budget(requests=11)
    with pytest.raises(ValueError):
        Budget(total_bytes=True)


@pytest.mark.asyncio
async def test_cursor_requires_parent_scope_and_progress(tmp_path):
    store = journal(tmp_path, b'{"data":[],"pagination":{"has_more":true,"next_cursor":"a"}}')
    params = {"limit": 2, "taker_only": "true"}
    first = await store.fetch("data.v2.trades", params)
    parent = first["receipt"]["capture_id"]
    with pytest.raises(ValueError, match="prior page"):
        await store.fetch("data.v2.trades", {**params, "cursor": "a"})
    with pytest.raises(ValueError, match="scope"):
        await store.fetch("data.v2.trades", {**params, "limit": 3, "cursor": "a"},
                          previous_capture_id=parent)
    with pytest.raises(ValueError, match="progress"):
        await store.fetch("data.v2.trades", {**params, "cursor": "invented"},
                          previous_capture_id=parent)
    second = await store.fetch("data.v2.trades", {**params, "cursor": "a"},
                               previous_capture_id=parent)
    with pytest.raises(ValueError, match="progress"):
        await store.fetch("data.v2.trades", {**params, "cursor": "a"},
                          previous_capture_id=second["receipt"]["capture_id"])
    assert store.count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_stream_deadline_and_cancellation_preserve_partial(tmp_path, cancel):
    received = asyncio.Event()

    class WaitingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"partial":'
            received.set()
            await asyncio.Event().wait()

    async def handler(request):
        return httpx.Response(200, stream=WaitingStream())

    store = CaptureJournal(tmp_path.resolve() / "fs2_capture_deadline",
                           transport=httpx.MockTransport(handler),
                           budget=Budget(seconds_per_request=1))
    task = asyncio.create_task(fetch(store))
    await received.wait()
    if cancel:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        await task
    folder = next(p for p in store.root.iterdir() if p.is_dir())
    result = verify_capture(folder)
    assert result["raw"] == b'{"partial":'
    assert result["parsed"]["parse_error"] == ("cancelled" if cancel else "TimeoutError")


@pytest.mark.asyncio
async def test_actual_fsync_failure_retains_unacknowledged_raw(tmp_path, monkeypatch):
    store = journal(tmp_path)
    original = capture.os.fsync
    count = 0

    def fail_second(fd):
        nonlocal count
        count += 1
        if count == 2:  # first = new capture directory; second = raw file
            raise OSError("synthetic fsync failure")
        original(fd)

    monkeypatch.setattr(capture.os, "fsync", fail_second)
    with pytest.raises(OSError):
        await fetch(store)
    folder = next(p for p in store.root.iterdir() if p.is_dir())
    assert (folder / "raw.bin").exists()
    assert not (folder / "raw_ack.json").exists()
    with pytest.raises(FileNotFoundError):
        finish_parse(folder)


@pytest.mark.asyncio
async def test_session_mismatch_and_symlink_refused(tmp_path):
    store = journal(tmp_path)
    result = await fetch(store)
    folder = Path(result["folder"])
    alias = store.root / str(uuid.uuid4())
    alias.symlink_to(folder, target_is_directory=True)
    with pytest.raises(ValueError, match="canonical"):
        verify_capture(alias)
    (store.root / "session.json").write_text('{}')
    with pytest.raises(ValueError, match="session integrity"):
        verify_capture(folder)
