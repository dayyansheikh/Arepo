"""Synthetic encoded wire bodies; no public source requests or research admission."""

import asyncio
import gzip
import json
import uuid
from pathlib import Path

import httpx
import pytest

from astrolabe.feature_store import capture
from astrolabe.feature_store.capture import (
    Budget,
    CaptureJournal,
    _digest,
    _json_bytes,
    finish_parse,
    json_payload,
    verify_capture,
)
from tests.unit.test_feature_store_capture import Stream


def compress(raw):
    return gzip.compress(raw, mtime=0)


def store(tmp_path, wire, *, encoding="gzip", enabled=True, budget=Budget(), status=200):
    def handler(request):
        assert request.headers["accept-encoding"] == ("gzip" if enabled else "identity")
        return httpx.Response(status, headers={"content-encoding": encoding}, stream=Stream([wire]))

    return CaptureJournal(
        tmp_path.resolve() / ("fs2_capture_" + uuid.uuid4().hex),
        transport=httpx.MockTransport(handler),
        budget=budget,
        reuse_connections=True,
        accept_gzip=enabled,
    )


async def fetch(journal):
    return await journal.fetch("gamma.markets.keyset", {"limit": 100, "closed": "false"})


async def test_wire_bytes_exact_numbers_and_derived_hashes_remain_distinct(tmp_path):
    raw = b'{"x":0.123456789012345678900,"id":123456789012345678901,"z":-0.00}'
    wire = compress(raw)
    journal = store(tmp_path, wire)
    async with journal.connection_scope():
        result = await fetch(journal)
    assert result["raw"] == wire
    assert json_payload(result) == raw
    assert result["receipt"]["raw_bytes"] == len(wire)
    assert result["receipt"]["raw_hash"] == _digest(wire)
    assert result["parsed"]["schema_version"] == "fs2-parsed-v2"
    assert result["parsed"]["decoded_hash"] == _digest(raw)
    assert (
        result["parsed"]["decoded_bytes"] == result["parsed"]["decoded_budget_charge"] == len(raw)
    )
    assert journal.bytes == len(wire) and journal.decoded_bytes == len(raw)
    assert result["parsed"]["value"] == {
        "x": {"$decimal": "0.123456789012345678900"},
        "id": 123456789012345678901,
        "z": {"$decimal": "-0.00"},
    }
    assert result["raw_ack"]["durable_ack"]["utc"] <= result["parsed"]["parsed_at"]["utc"]
    folder = Path(result["folder"])
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert finish_parse(folder) == result
    assert before == {p.name: p.read_bytes() for p in folder.iterdir()}


@pytest.mark.parametrize(
    "wire",
    [
        compress(b"{}")[:-2],
        b"not gzip",
        compress(b"{}") + b"trailing",
        compress(b"{}") + compress(b"{}"),
        compress(b"{}")[:-8] + b"\x00" * 8,
    ],
)
async def test_invalid_encoded_bodies_preserved_and_never_empty_success(tmp_path, wire):
    journal = store(tmp_path, wire)
    async with journal.connection_scope():
        result = await fetch(journal)
    assert result["raw"] == wire
    assert result["parsed"]["parse_error"] == "invalid_content_encoding"
    assert result["parsed"]["value"] is None
    assert result["parsed"]["decoded_bytes"] is None
    assert result["parsed"]["decoded_hash"] is None
    assert result["parsed"]["decoded_budget_charge"] == journal.budget.bytes_per_response


async def test_expansion_and_independent_session_limit(tmp_path):
    raw = b'"' + b"a" * 68 + b'"'
    journal = store(
        tmp_path, compress(raw), budget=Budget(requests=3, bytes_per_response=100, total_bytes=120)
    )
    async with journal.connection_scope():
        first = await fetch(journal)
        second = await fetch(journal)
        assert first["parsed"]["decoded_bytes"] == 70
        assert second["receipt"]["decoded_budget_before"] == 70
        assert second["receipt"]["decoded_byte_limit"] == 50
        assert second["parsed"]["parse_error"] == "decoded_byte_budget_exceeded"
        assert second["parsed"]["decoded_bytes"] is None
        assert second["parsed"]["decoded_budget_charge"] == 50
        assert journal.bytes < 120 and journal.decoded_bytes == 120
        with pytest.raises(ValueError, match="decoded session byte budget"):
            await fetch(journal)
    assert journal.count == 2


@pytest.mark.parametrize(
    "enabled,encoding,expected",
    [
        (False, "gzip", "unsupported_content_encoding"),
        (True, "br", "unsupported_content_encoding"),
        (True, "identity", None),
    ],
)
async def test_default_refusal_and_explicit_identity_fallback(
    tmp_path, enabled, encoding, expected
):
    raw = b'{"x":1.00}'
    journal = store(
        tmp_path,
        raw if encoding == "identity" else compress(raw),
        enabled=enabled,
        encoding=encoding,
    )
    async with journal.connection_scope():
        result = await fetch(journal)
    assert result["parsed"]["parse_error"] == expected
    if enabled and expected is None:
        assert result["parsed"]["decoded_hash"] == result["receipt"]["raw_hash"]
    if not enabled:
        assert result["receipt"]["schema_version"] == "fs2-receipt-v2"
        assert "decoded_bytes" not in result["parsed"]


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b"\xff"])
async def test_decoded_invalid_json_keeps_actual_decoded_size(tmp_path, raw):
    journal = store(tmp_path, compress(raw))
    async with journal.connection_scope():
        result = await fetch(journal)
    assert result["parsed"]["parse_error"] == "invalid_json"
    assert result["parsed"]["decoded_hash"] == _digest(raw)
    assert result["parsed"]["decoded_budget_charge"] == len(raw)


async def test_gzip_is_opt_in_and_gamma_only(tmp_path):
    with pytest.raises(ValueError, match="opt-in"):
        CaptureJournal(tmp_path / "fs2_capture_invalid", accept_gzip=True)
    assert not (tmp_path / "fs2_capture_invalid").exists()
    journal = store(tmp_path, compress(b"{}"))
    async with journal.connection_scope():
        with pytest.raises(ValueError, match="restricted"):
            await journal.fetch("coinbase.btc_usd.ticker", {})
    assert journal.count == 0


async def test_crash_before_decompression_retains_wire_and_recovers_new_parse(
    tmp_path, monkeypatch
):
    raw = b'{"x":1.00}'
    journal = store(tmp_path, compress(raw))
    original = capture.finish_parse
    monkeypatch.setattr(
        capture,
        "finish_parse",
        lambda folder: (_ for _ in ()).throw(RuntimeError("crash before decompression")),
    )
    async with journal.connection_scope():
        with pytest.raises(RuntimeError):
            await fetch(journal)
    folder = next(p for p in journal.root.iterdir() if p.is_dir())
    base = verify_capture(folder, raw_only=True)
    assert base["raw"] == compress(raw)
    assert journal.decoded_bytes == journal.budget.bytes_per_response
    monkeypatch.setattr(capture, "finish_parse", original)
    monkeypatch.setattr(capture, "_CLOCK_SESSION", str(uuid.uuid4()))
    result = finish_parse(folder)
    assert json_payload(result) == raw
    assert result["receipt"] == base["receipt"]
    assert (
        result["parsed"]["parsed_at"]["clock_session_id"]
        != (base["receipt"]["first_received"]["clock_session_id"])
    )


async def test_cancelled_compressed_attempt_keeps_partial_wire(tmp_path):
    class CancelledStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"partial gzip"
            raise asyncio.CancelledError

    journal = CaptureJournal(
        tmp_path.resolve() / "fs2_capture_cancelled",
        accept_gzip=True,
        reuse_connections=True,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"content-encoding": "gzip"}, stream=CancelledStream()
            )
        ),
    )
    async with journal.connection_scope():
        with pytest.raises(asyncio.CancelledError):
            await fetch(journal)
    result = verify_capture(next(p for p in journal.root.iterdir() if p.is_dir()))
    assert result["raw"] == b"partial gzip"
    assert result["parsed"]["parse_error"] == "cancelled"
    assert result["parsed"]["decoded_bytes"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("decoded_hash", "0" * 64),
        ("decoded_bytes", 999),
        ("decoded_budget_charge", 0),
        ("schema_version", "fs2-parsed-v1"),
    ],
)
async def test_rehashed_decoded_metadata_tampering_refused(tmp_path, field, value):
    journal = store(tmp_path, compress(b"{}"))
    async with journal.connection_scope():
        result = await fetch(journal)
    folder = Path(result["folder"])
    parsed = result["parsed"]
    parsed[field] = value
    data = _json_bytes(parsed)
    (folder / "parsed.json").write_bytes(data)
    ack = json.loads((folder / "parsed_ack.json").read_bytes())
    ack["parsed_hash"] = _digest(data)
    (folder / "parsed_ack.json").write_bytes(_json_bytes(ack))
    with pytest.raises(ValueError, match="decoded capture evidence"):
        verify_capture(folder)


async def test_http_failure_and_torn_parse_never_admitted(tmp_path, monkeypatch):
    journal = store(tmp_path, compress(b"{}"), status=503)
    async with journal.connection_scope():
        result = await fetch(journal)
    assert result["parsed"]["parse_error"] == "http_non_success"
    assert result["parsed"]["decoded_bytes"] is None
    other = store(tmp_path, compress(b"{}"))
    write = capture._write_once

    def fail_ack(path, data):
        if path.name == "parsed_ack.json":
            raise OSError("synthetic disk failure")
        write(path, data)

    monkeypatch.setattr(capture, "_write_once", fail_ack)
    async with other.connection_scope():
        with pytest.raises(OSError):
            await fetch(other)
    folder = next(p for p in other.root.iterdir() if p.is_dir())
    with pytest.raises(ValueError, match="partial parse"):
        finish_parse(folder)
    assert verify_capture(folder, raw_only=True)["raw"] == compress(b"{}")


async def test_wire_limit_remains_independent_of_decoded_limit(tmp_path):
    wire = compress(bytes(range(256)))
    journal = store(tmp_path, wire, budget=Budget(bytes_per_response=64, total_bytes=128))
    async with journal.connection_scope():
        result = await fetch(journal)
    assert result["raw"] == wire[:64]
    assert (
        result["receipt"]["transport_error"]
        == result["parsed"]["parse_error"]
        == ("byte_budget_exceeded")
    )
    assert result["parsed"]["decoded_bytes"] is None
    assert journal.bytes == journal.decoded_bytes == 64


@pytest.mark.parametrize("change", ["source", "header", "limit", "before", "version", "session"])
async def test_encoded_scope_and_session_cannot_be_rehashed_into_admission(tmp_path, change):
    journal = store(tmp_path, compress(b"{}"))
    async with journal.connection_scope():
        result = await fetch(journal)
    folder = Path(result["folder"])
    receipt = result["receipt"]
    if change == "source":
        receipt["source_id"] = "coinbase.btc_usd.ticker"
    elif change == "header":
        receipt["request"]["headers"]["Accept-Encoding"] = "identity"
    elif change == "limit":
        receipt["decoded_byte_limit"] += 1
    elif change == "before":
        receipt["decoded_budget_before"] = -1
    elif change == "version":
        receipt["schema_version"] = "fs2-receipt-v2"
    else:
        session = json.loads((journal.root / "session.json").read_bytes())
        session["http_payload_policy"]["version"] = "unbounded"
        data = _json_bytes(session)
        (journal.root / "session.json").write_bytes(data)
        receipt["session_hash"] = _digest(data)
    data = _json_bytes(receipt)
    (folder / "receipt.json").write_bytes(data)
    ack = result["raw_ack"]
    ack["receipt_hash"] = _digest(data)
    (folder / "raw_ack.json").write_bytes(_json_bytes(ack))
    with pytest.raises(ValueError, match="(scope/reservation|payload version|payload policy)"):
        verify_capture(folder, raw_only=True)


@pytest.mark.parametrize("enabled", [False, True])
async def test_representation_metadata_is_opt_in_and_excludes_private_headers(tmp_path, enabled):
    extra = {
        "content-length": "2",
        "etag": '"v1"',
        "age": "250",
        "cf-cache-status": "HIT",
        "vary": "Accept-Encoding",
    }

    def handler(request):
        return httpx.Response(
            200,
            headers={**extra, "content-type": "application/json", "set-cookie": "private=excluded"},
            stream=Stream([b"{}"]),
        )

    journal = CaptureJournal(
        tmp_path.resolve() / "fs2_capture_headers",
        transport=httpx.MockTransport(handler),
        reuse_connections=True,
        accept_gzip=enabled,
    )
    async with journal.connection_scope():
        result = await fetch(journal)
    expected = {"content-type": "application/json", **(extra if enabled else {})}
    assert result["receipt"]["headers"] == expected
    assert verify_capture(Path(result["folder"]))["receipt"]["headers"] == expected
