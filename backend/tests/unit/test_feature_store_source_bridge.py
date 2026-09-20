import asyncio
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from astrolabe.feature_store import source_bridge
from astrolabe.feature_store.capture import CaptureJournal, verify_capture
from astrolabe.feature_store.migrations import local_engine, upgrade
from astrolabe.feature_store.models import MODEL_BY_ENTITY
from astrolabe.feature_store.source_bridge import import_diagnostic_capture, source_parse_artifact

BODY = (b'{"market":"0x' + b'a' * 64 + b'","asset_id":"1","timestamp":"1789923844641",'
        b'"bids":[{"price":"0.123456789012345678900","size":"1.000"}],"asks":[]}')


async def captured(tmp_path, *, status=200, body=BODY, source="clob.book", params=None):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield body

    async def handler(request):
        return httpx.Response(status, stream=Stream())

    journal = CaptureJournal(tmp_path.resolve() / "fs2_capture_bridge",
                             transport=httpx.MockTransport(handler))
    return await journal.fetch(source, params if params is not None else {"token_id": "1"})


@pytest.fixture
async def url(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'fs2_test_bridge.sqlite'}"
    await upgrade(url)
    return url


@pytest.mark.asyncio
async def test_import_preserves_clocks_values_and_cannot_promote_synthetic(tmp_path, url):
    capture = await captured(tmp_path)
    folder = Path(capture["folder"])
    result = await import_diagnostic_capture(url, folder)
    row = result["observation"]
    assert row["provenance_class"] == "synthetic"
    assert result["registry"]["rights_evidence"]["model_feature_admission"] is False
    assert result["verification"]["access_state"] == "runtime_verified"
    assert result["verification"]["verified_observation_id"] == row["id"]
    assert row["first_received_at"].isoformat().replace('+00:00', 'Z') == (
        capture["receipt"]["first_received"]["utc"])
    assert row["source_event_at"] is None
    assert row["missing_fields"]["source_event_at"] == "not_requested"
    _, parsed, ack, _ = source_parse_artifact(folder)
    assert parsed["result"]["value"]["bids"][0]["price"] == {
        "$decimal": "0.123456789012345678900"}
    assert row["parsed_at"] >= source_bridge._time(capture["parsed_ack"]["durable_ack"])
    assert row["available_to_model_at"] >= source_bridge._time(ack["durable_ack"])
    assert await import_diagnostic_capture(url, folder) == result
    assert verify_capture(folder)["raw"] == BODY


@pytest.mark.asyncio
async def test_retry_after_observation_commit_finishes_registry_without_duplicate(tmp_path, url,
                                                                               monkeypatch):
    capture = await captured(tmp_path)
    original = source_bridge.append_batch
    calls = 0

    async def interrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("crash before registry verification")
        return await original(*args, **kwargs)

    monkeypatch.setattr(source_bridge, "append_batch", interrupted)
    with pytest.raises(RuntimeError):
        await import_diagnostic_capture(url, capture["folder"])
    monkeypatch.setattr(source_bridge, "append_batch", original)
    result = await import_diagnostic_capture(url, capture["folder"])
    assert result["verification"] is not None
    engine = local_engine(url)
    try:
        async with engine.connect() as connection:
            for entity, count in [("source_registry", 2), ("source_observation", 1)]:
                table = MODEL_BY_ENTITY[entity].__table__
                actual = (
                    await connection.execute(select(func.count()).select_from(table))
                ).scalar()
                assert actual == count
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("status,body,reason", [(403, b'{}', "permission_denied"),
                                               (429, b'{}', "rate_limited"),
                                               (503, b'{}', "source_error"),
                                               (200, b'{}', "invalid")])
async def test_failed_capture_does_not_verify_runtime(tmp_path, url, status, body, reason):
    capture = await captured(tmp_path, status=status, body=body)
    result = await import_diagnostic_capture(url, capture["folder"])
    assert result["verification"] is None
    assert result["observation"]["missing_reason"] == reason


@pytest.mark.asyncio
async def test_torn_source_parse_refused_and_remote_target_rejected_first(tmp_path, url,
                                                                       monkeypatch):
    capture = await captured(tmp_path)
    folder = Path(capture["folder"])
    with pytest.raises(ValueError):
        await import_diagnostic_capture("postgresql+asyncpg://example.com/production", folder)
    assert not list(folder.glob('source_parse_*'))
    original = source_bridge._write_once

    def fail_ack(path, content):
        if path.name == "ack.json":
            raise OSError("synthetic disk failure")
        original(path, content)

    monkeypatch.setattr(source_bridge, "_write_once", fail_ack)
    with pytest.raises(OSError):
        await import_diagnostic_capture(url, folder)
    monkeypatch.setattr(source_bridge, "_write_once", original)
    with pytest.raises(FileNotFoundError):
        await import_diagnostic_capture(url, folder)
    assert verify_capture(folder)["raw"] == BODY


@pytest.mark.asyncio
async def test_concurrent_complete_imports_are_idempotent(tmp_path, url):
    capture = await captured(tmp_path)
    source_parse_artifact(capture["folder"])
    a, b = await asyncio.gather(import_diagnostic_capture(url, capture["folder"]),
                                import_diagnostic_capture(url, capture["folder"]))
    assert a == b


@pytest.mark.asyncio
async def test_changed_source_parser_cannot_silently_reinterpret_capture(
    tmp_path, url, monkeypatch,
):
    from dataclasses import replace

    from astrolabe.feature_store.sources import SOURCES

    capture = await captured(tmp_path)
    monkeypatch.setitem(
        SOURCES, "clob.book", replace(SOURCES["clob.book"], parser_version="future-v2"),
    )
    with pytest.raises(ValueError, match="no current-parser substitution"):
        await import_diagnostic_capture(url, capture["folder"])
    assert not list(Path(capture["folder"]).glob('source_parse_*'))
