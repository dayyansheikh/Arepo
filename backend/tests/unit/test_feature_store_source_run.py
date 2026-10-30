"""Synthetic fault injection; never evidence of prospective market observations."""

import json
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from astrolabe.feature_store import _PACKAGE_FILES, source_parsers
from astrolabe.feature_store.admission import AdmissionError
from astrolabe.feature_store.build_identity import verified_build
from astrolabe.feature_store.capture import _digest, _json_bytes
from astrolabe.feature_store.migrations import local_engine, upgrade
from astrolabe.feature_store.models import MODEL_BY_ENTITY
from astrolabe.feature_store.repository import append_batch, index_source_run
from astrolabe.feature_store.source_run import SourceRun, read_source_run
from astrolabe.feature_store.types import utc_datetime
from tests.unit.test_feature_store_source_bridge import BODY, captured


def mock_transport(root, status=200):
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield BODY

    def handler(request):
        # The durable policy must exist before even the synthetic request is handled.
        assert (root / "run_ack.json").is_file()
        return httpx.Response(status, stream=Stream())

    return httpx.MockTransport(handler)


@pytest.fixture
async def url(tmp_path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'fs2_test_source_run.sqlite'}"
    await upgrade(url)
    return url


@pytest.mark.asyncio
async def test_primary_journal_index_cutoff_and_synthetic_separation(tmp_path, url):
    root = tmp_path.resolve() / "fs2_capture_measurement"
    run = SourceRun(root, transport=mock_transport(root))
    rows = await run.fetch("clob.book", {"token_id": "1"})
    observation = next(row for kind, row in rows if kind == "source_observation")
    assert all(row["provenance_class"] == "synthetic" for _, row in rows)
    assert observation["available_to_model_at"] == observation["recorded_at"]
    assert (observation["first_received_at"] <= observation["ingested_at"]
            <= observation["parsed_at"] <= observation["available_to_model_at"])
    assert observation["source_event_at"] is None
    assert observation["first_available_at"] is None
    assert not [r for kind, r in read_source_run(
        root, cutoff=observation["available_to_model_at"] - timedelta(microseconds=1)
    ) if kind == "source_observation"]
    assert read_source_run(root, cutoff=observation["available_to_model_at"]) == rows
    indexed, receipt = await index_source_run(url, root)
    assert indexed == rows
    from datetime import datetime

    assert utc_datetime(datetime.fromisoformat(
        receipt["index_committed_ack"]["utc"]
    )) > observation["recorded_at"]
    assert (await index_source_run(url, root))[0] == indexed
    assert len(list(root.glob("index_*.json"))) == 2
    engine = local_engine(url)
    try:
        async with engine.connect() as conn:
            table = MODEL_BY_ENTITY["source_observation"].__table__
            assert (await conn.execute(select(func.count()).select_from(table))).scalar() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_old_diagnostic_cannot_be_adopted_or_boolean_promoted(tmp_path, url):
    diagnostic = await captured(tmp_path)
    root = Path(diagnostic["folder"]).parent
    with pytest.raises(FileExistsError):
        SourceRun(root)
    with pytest.raises(FileNotFoundError):
        await index_source_run(url, root)
    with pytest.raises(AdmissionError, match="generic transaction"):
        await append_batch(url, [("source_observation", {"provenance_class": "prospective"})])
    with pytest.raises(TypeError):
        SourceRun(tmp_path / "fs2_capture_fake", prospective=True)


@pytest.mark.asyncio
async def test_torn_admission_retained_and_read_never_reconstructs(tmp_path, url, monkeypatch):
    root = tmp_path.resolve() / "fs2_capture_torn"
    run = SourceRun(root, transport=mock_transport(root))
    original = Path.open

    def fail_ack(path, *args, **kwargs):
        if path.name == "admission_ack.json":
            raise OSError("synthetic admission persistence failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_ack)
    with pytest.raises(OSError):
        await run.fetch("clob.book", {"token_id": "1"})
    monkeypatch.setattr(Path, "open", original)
    folder = next(p for p in root.iterdir() if p.is_dir())
    before = {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}
    with pytest.raises(FileNotFoundError):
        await index_source_run(url, root)
    assert before == {p: p.read_bytes() for p in folder.rglob("*") if p.is_file()}


@pytest.mark.asyncio
async def test_commit_succeeds_but_index_receipt_fails_then_retry(tmp_path, url, monkeypatch):
    root = tmp_path.resolve() / "fs2_capture_index_retry"
    run = SourceRun(root, transport=mock_transport(root))
    rows = await run.fetch("clob.book", {"token_id": "1"})
    original = Path.open

    def fail_index(path, *args, **kwargs):
        if path.name.startswith("index_"):
            raise OSError("synthetic disk failure after SQL commit")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_index)
    with pytest.raises(OSError):
        await index_source_run(url, root)
    monkeypatch.setattr(Path, "open", original)
    assert (await index_source_run(url, root))[0] == rows
    assert read_source_run(root) == rows


@pytest.mark.asyncio
async def test_failed_response_retained_without_runtime_verified_registry(tmp_path):
    root = tmp_path.resolve() / "fs2_capture_failure"
    run = SourceRun(root, transport=mock_transport(root, 429))
    rows = await run.fetch("clob.book", {"token_id": "1"})
    assert next(r for k, r in rows if k == "source_observation")["missing_reason"] == "rate_limited"
    assert all(r["access_state"] == "documented_only"
               for k, r in rows if k == "source_registry")


@pytest.mark.asyncio
async def test_admission_clock_tampering_is_refused_even_with_rehashed_ack(tmp_path):
    root = tmp_path.resolve() / "fs2_capture_clock"
    run = SourceRun(root, transport=mock_transport(root))
    await run.fetch("clob.book", {"token_id": "1"})
    folder = next(p for p in root.iterdir() if p.is_dir())
    file = folder / "admission.json"
    facts = json.loads(file.read_bytes())
    facts["ready_at"]["utc"] = "2000-01-01T00:00:00.000000Z"
    file.write_bytes(_json_bytes(facts))  # synthetic corruption; never mutate real evidence
    ack_file = folder / "admission_ack.json"
    ack = json.loads(ack_file.read_bytes())
    ack["payload_hash"] = _digest(file.read_bytes())
    ack_file.write_bytes(_json_bytes(ack))
    with pytest.raises(ValueError, match="chronology"):
        read_source_run(root)


def test_changed_build_or_loaded_parser_refused(tmp_path, monkeypatch):
    verified_build()
    monkeypatch.setitem(_PACKAGE_FILES, "types.py", "0" * 64)
    with pytest.raises(ValueError, match="changed on disk"):
        SourceRun(tmp_path.resolve() / "fs2_capture_bad_build")
    monkeypatch.undo()
    monkeypatch.setattr(source_parsers, "clob_book", lambda *args: {})
    with pytest.raises(ValueError, match="loaded measurement code"):
        verified_build()
    assert not (tmp_path / "fs2_capture_bad_build").exists()


@pytest.mark.asyncio
async def test_policy_refusal_before_any_request_and_remote_index_refusal(tmp_path):
    root = tmp_path.resolve() / "fs2_capture_policy"
    run = SourceRun(root, transport=mock_transport(root))
    with pytest.raises(ValueError, match="outside predeclared"):
        await run.fetch("coinbase.btc_usd.ticker", {})
    assert not any(p.is_dir() for p in root.iterdir())
    with pytest.raises(ValueError):
        await index_source_run("postgresql+asyncpg://remote.example/production", root)


@pytest.mark.asyncio
async def test_index_failure_rolls_back_without_losing_primary_facts(tmp_path, url, monkeypatch):
    from sqlalchemy.ext.asyncio import AsyncConnection

    root = tmp_path.resolve() / "fs2_capture_rollback"
    run = SourceRun(root, transport=mock_transport(root))
    rows = await run.fetch("clob.book", {"token_id": "1"})
    original = AsyncConnection.execute

    async def interrupted(conn, statement, *args, **kwargs):
        if (getattr(statement, "is_insert", False)
                and statement.table.name == "fs2_source_observation"):
            raise RuntimeError("synthetic index interruption")
        return await original(conn, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncConnection, "execute", interrupted)
    with pytest.raises(RuntimeError, match="index interruption"):
        await index_source_run(url, root)
    monkeypatch.setattr(AsyncConnection, "execute", original)
    engine = local_engine(url)
    try:
        async with engine.connect() as conn:
            table = MODEL_BY_ENTITY["source_registry"].__table__
            assert (await conn.execute(select(func.count()).select_from(table))).scalar() == 0
    finally:
        await engine.dispose()
    assert read_source_run(root) == rows
    assert not list(root.glob("index_*.json"))
    assert (await index_source_run(url, root))[0] == rows


@pytest.mark.asyncio
async def test_missing_source_parse_is_not_recreated_by_read(tmp_path):
    root = tmp_path.resolve() / "fs2_capture_read_only"
    run = SourceRun(root, transport=mock_transport(root))
    await run.fetch("clob.book", {"token_id": "1"})
    folder = next(p for p in root.iterdir() if p.is_dir())
    parsed = next(folder.glob("source_parse_*"))
    # Synthetic loss simulation; preserve the displaced bytes too.
    parsed.rename(tmp_path / "displaced_parse")
    with pytest.raises(ValueError, match="read cannot reconstruct"):
        read_source_run(root)
    assert not parsed.exists()


@pytest.mark.asyncio
async def test_preserved_copy_keeps_original_identity_clocks_and_numerical_bytes(tmp_path):
    import shutil

    root = tmp_path.resolve() / "fs2_capture_original"
    run = SourceRun(root, transport=mock_transport(root))
    rows = await run.fetch("clob.book", {"token_id": "1"})
    restored = tmp_path.resolve() / "fs2_capture_restored"
    shutil.copytree(root, restored)
    assert read_source_run(restored) == rows
    # This checks a complete local journal copy only, not the full archive-equivalence gate.
