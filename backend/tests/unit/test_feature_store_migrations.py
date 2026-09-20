"""Non-production migration tests: a schema check must never become a repair."""

import csv
from pathlib import Path

import pytest
from sqlalchemy import insert, inspect, select, text
from sqlalchemy.exc import DBAPIError

from astrolabe.feature_store import migrations
from astrolabe.feature_store.models import MODEL_BY_ENTITY, FeatureStoreBase
from astrolabe.feature_store.schema import FIELD_SPECS


@pytest.fixture
def local_url(tmp_path):
    return f"sqlite+aiosqlite:///{tmp_path / 'fs2_test_migrations.sqlite'}"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://localhost:5432/fs2_test_example",
        "postgresql+asyncpg://remote.example:55432/fs2_test_example",
        "postgresql+asyncpg://localhost:55432/production",
        "postgresql+asyncpg://localhost:55432/fs2_test_example?host=remote.example",
        "sqlite+aiosqlite:////Users/production/fs2_test_example.sqlite",
        "sqlite+aiosqlite:////tmp/production.sqlite",
        "mysql://localhost/fs2_test_example",
    ],
)
def test_refuses_unsafe_target_before_engine_creation(url, monkeypatch):
    def never_connect(*args, **kwargs):
        pytest.fail("unsafe target reached engine creation")

    monkeypatch.setattr(migrations, "create_async_engine", never_connect)
    with pytest.raises(migrations.MigrationRefused):
        migrations.local_engine(url)


def test_catalogue_model_and_pinned_schema_parity():
    catalogue = (
        Path(__file__).resolve().parents[3] / "docs/architecture/FEATURE_STORE_V2_FIELDS.csv"
    )
    with catalogue.open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(MODEL_BY_ENTITY) == 21
    for entity, specs in FIELD_SPECS.items():
        table = MODEL_BY_ENTITY[entity].__table__
        expected = {
            r["field"]: r
            for r in rows
            if r["entity"] == entity and r["storage"] != "derived_as_of_view"
        }
        assert set(table.columns.keys()) == set(expected) == set(specs)
        for field, spec in specs.items():
            col = table.c[field]
            assert col.nullable == (spec["nullable"] == "true")
            assert spec["type"] == expected[field]["type"]
            assert spec["reference"] == expected[field]["reference"]
            assert {fk.target_fullname for fk in col.foreign_keys} == (
                {"fs2_" + spec["reference"]} if spec["reference"] else set()
            )


async def test_check_is_read_only_then_upgrade_is_idempotent(local_url):
    engine = migrations.local_engine(local_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE TABLE v1_evidence (id INTEGER PRIMARY KEY, payload TEXT)")
            )
            await conn.execute(text("INSERT INTO v1_evidence VALUES (1, :p)"), {"p": "1.2300/null"})
        assert (await migrations.check(local_url))["ledger_present"] is False
        async with engine.connect() as conn:
            assert await conn.run_sync(lambda c: inspect(c).get_table_names()) == ["v1_evidence"]
        assert (await migrations.upgrade(local_url))["created"] is True
        assert (await migrations.upgrade(local_url))["created"] is False
        result = await migrations.check(local_url)
        assert result["current"], result
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT * FROM v1_evidence"))).all() == [
                (1, "1.2300/null")
            ]
    finally:
        await engine.dispose()


async def test_failed_creation_rolls_back_all_ddl(local_url, monkeypatch):
    def fail_after_tables(conn):
        raise RuntimeError("injected after schema creation")

    monkeypatch.setattr(migrations, "_install_guards", fail_after_tables)
    with pytest.raises(RuntimeError, match="injected"):
        await migrations.upgrade(local_url)
    engine = migrations.local_engine(local_url)
    try:
        async with engine.connect() as conn:
            assert await conn.run_sync(lambda c: inspect(c).get_table_names()) == []
    finally:
        await engine.dispose()


async def test_partial_schema_is_not_silently_repaired(local_url):
    engine = migrations.local_engine(local_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE fs2_unknown (id TEXT)"))
        with pytest.raises(migrations.MigrationRefused, match="partial"):
            await migrations.upgrade(local_url)
    finally:
        await engine.dispose()


async def test_guard_drift_is_detected_and_not_repaired(local_url):
    await migrations.upgrade(local_url)
    engine = migrations.local_engine(local_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TRIGGER fs2_artifact_manifest_no_update"))
        assert not (await migrations.check(local_url))["current"]
        with pytest.raises(migrations.MigrationRefused, match="incompatible"):
            await migrations.upgrade(local_url)
    finally:
        await engine.dispose()


async def test_direct_sql_update_delete_and_replace_cannot_change_evidence(local_url):
    from datetime import UTC, datetime

    await migrations.upgrade(local_url)
    table = MODEL_BY_ENTITY["artifact_manifest"].__table__
    row = dict(
        id="a" * 64,
        content_hash="b" * 64,
        manifest_kind="fixture",
        payload={},
        available_at=datetime.now(UTC),
        recorded_at=datetime.now(UTC),
        schema_version="fixture",
        provenance_class="synthetic",
        missing_fields={},
    )
    engine = migrations.local_engine(local_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(insert(table).values(**row))
        for statement in (
            "UPDATE fs2_artifact_manifest SET manifest_kind='changed'",
            "DELETE FROM fs2_artifact_manifest",
            "INSERT OR REPLACE INTO fs2_artifact_manifest SELECT * FROM fs2_artifact_manifest",
        ):
            with pytest.raises(DBAPIError, match="immutable"):
                async with engine.begin() as conn:
                    await conn.execute(text(statement))
        async with engine.connect() as conn:
            assert (await conn.execute(select(table.c.manifest_kind))).scalar_one() == "fixture"
    finally:
        await engine.dispose()


def test_metadata_isolated_from_v1():
    from astrolabe.storage.db import Base
    from astrolabe.storage.migrate import _load_all_models

    _load_all_models()
    assert not set(Base.metadata.tables) & set(FeatureStoreBase.metadata.tables)
    assert not any(name.startswith("fs2_") for name in Base.metadata.tables)
