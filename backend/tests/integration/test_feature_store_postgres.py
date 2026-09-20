"""Opt-in real PostgreSQL tests. Starts and stops its own disposable loopback cluster.

Set AREPO_FS2_POSTGRES_BIN to a local PostgreSQL bin directory. No application database
settings, existing cluster, network installer or service manager are used.
"""

import os
import secrets
import socket
import subprocess
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import insert, inspect, select, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from astrolabe.feature_store import migrations
from astrolabe.feature_store.models import MODEL_BY_ENTITY


@pytest.fixture(scope="module")
def postgres_url(tmp_path_factory):
    configured = os.environ.get("AREPO_FS2_POSTGRES_BIN")
    if not configured:
        pytest.skip("set AREPO_FS2_POSTGRES_BIN for disposable PostgreSQL integration")
    binaries = Path(configured)
    assert (binaries / "initdb").is_file(), "explicit PostgreSQL binaries unavailable"
    root = tmp_path_factory.mktemp("fs2_test_postgres")
    password = secrets.token_hex(24)
    pwfile = root / "password"
    pwfile.write_text(password)
    pwfile.chmod(0o600)
    data = root / "data"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    def run(command, *, env=None):
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=60)
        assert result.returncode == 0, result.stderr

    run(
        [
            str(binaries / "initdb"),
            "-D",
            str(data),
            "-U",
            "fs2_test_owner",
            "--auth=scram-sha-256",
            "--pwfile",
            str(pwfile),
            "--encoding=UTF8",
            "--no-locale",
        ]
    )
    try:
        run(
            [
                str(binaries / "pg_ctl"),
                "-D",
                str(data),
                "-l",
                str(root / "postgres.log"),
                "-o",
                f"-h 127.0.0.1 -p {port} -c unix_socket_directories=''",
                "-w",
                "start",
            ]
        )
        run(
            [
                str(binaries / "createdb"),
                "-h",
                "127.0.0.1",
                "-p",
                str(port),
                "-U",
                "fs2_test_owner",
                "fs2_test_store",
            ],
            env={**os.environ, "PGPASSWORD": password},
        )
        yield URL.create(
            "postgresql+asyncpg",
            username="fs2_test_owner",
            password=password,
            host="127.0.0.1",
            port=port,
            database="fs2_test_store",
        )
    finally:
        # Startup can time out after the daemon starts; still stop only this test cluster.
        status = subprocess.run(
            [str(binaries / "pg_ctl"), "-D", str(data), "status"], capture_output=True, timeout=10
        )
        if status.returncode == 0:
            run([str(binaries / "pg_ctl"), "-D", str(data), "-m", "immediate", "-w", "stop"])
        pwfile.unlink()


async def test_postgres_migration_precision_security_and_preservation(postgres_url, tmp_path):
    # Failure before guards must roll back PostgreSQL DDL, just as on SQLite.
    engine = migrations.local_engine(postgres_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE TABLE v1_evidence (id BIGINT, value DOUBLE PRECISION, data JSON)")
            )
            await conn.execute(
                text(
                    "INSERT INTO v1_evidence VALUES (1, 0.12345678901234567, CAST(:data AS JSON))"
                ),
                {"data": '{"a":null}'},
            )
            await conn.execute(text("CREATE ROLE anon NOLOGIN"))
            await conn.execute(text("CREATE ROLE authenticated NOLOGIN"))
            await conn.execute(text("CREATE ROLE service_role NOLOGIN BYPASSRLS"))
            before = (
                await conn.execute(
                    text("SELECT id, float8send(value), data::text FROM v1_evidence")
                )
            ).all()
        assert not (await migrations.check(postgres_url))["ledger_present"]
        with pytest.raises(RuntimeError, match="injected"):
            async with engine.begin() as conn:
                await conn.run_sync(migrations._upgrade_sync)
                raise RuntimeError("injected before commit")
        async with engine.connect() as conn:
            assert await conn.run_sync(lambda c: inspect(c).get_table_names()) == ["v1_evidence"]
        assert (await migrations.upgrade(postgres_url))["created"]
        assert not (await migrations.upgrade(postgres_url))["created"]
        result = await migrations.check(postgres_url)
        assert result["current"], result
        async with engine.connect() as conn:
            assert (
                await conn.execute(
                    text("SELECT id, float8send(value), data::text FROM v1_evidence")
                )
            ).all() == before
            for role in ("anon", "authenticated", "service_role"):
                allowed = await conn.execute(
                    text("SELECT has_table_privilege(:role, 'fs2_source_observation', 'SELECT')"),
                    {"role": role},
                )
                assert allowed.scalar_one() is False

        table = MODEL_BY_ENTITY["artifact_manifest"].__table__
        at = datetime(2026, 9, 20, 7, 2, 1, 123456, tzinfo=UTC)
        async with engine.begin() as conn:
            await conn.execute(
                insert(table).values(
                    id="a" * 64,
                    content_hash="b" * 64,
                    manifest_kind="sampling",
                    payload={},
                    available_at=at,
                    recorded_at=at,
                    schema_version="fixture",
                    provenance_class="synthetic",
                    missing_fields={},
                )
            )
            got = (await conn.execute(select(table.c.recorded_at))).scalar_one()
            assert got == at and got.tzinfo == UTC
        for statement in (
            "UPDATE fs2_artifact_manifest SET manifest_kind='changed'",
            "DELETE FROM fs2_artifact_manifest",
            "TRUNCATE fs2_artifact_manifest CASCADE",
        ):
            with pytest.raises(DBAPIError, match="immutable"):
                async with engine.begin() as conn:
                    await conn.execute(text(statement))

        # Primitive adapter test independent of derived-record admission fixtures.
        from sqlalchemy import Column, Integer, MetaData, Table

        from astrolabe.feature_store.types import ExactDecimal, UnsignedIntegerText

        meta = MetaData()
        values = Table(
            "exact_fixture",
            meta,
            Column("id", Integer, primary_key=True),
            Column("amount", ExactDecimal()),
            Column("token", UnsignedIntegerText(256)),
        )
        async with engine.begin() as conn:
            await conn.run_sync(meta.create_all)
            raw = "-0.123456789012345678901234567890000"
            await conn.execute(insert(values).values(amount=raw, token=str(2**256 - 1)))
            got = (await conn.execute(select(values))).one()
            assert got.amount.as_tuple() == Decimal(raw).as_tuple()
            assert got.token == str(2**256 - 1)

        # Execute the actual immutable writer/causal graph, not only compiled DDL.
        import asyncio

        from astrolabe.feature_store.repository import PayloadConflict, append_batch
        from tests.unit.test_feature_store_causality import graph
        from tests.unit.test_feature_store_repository import AT, registry

        rows, feature, _ = graph()
        batch = [*rows, ("feature_value", feature)]
        first = await append_batch(postgres_url, batch, fixture_clock=AT)
        assert await append_batch(postgres_url, batch, fixture_clock=AT) == first
        concurrent = [("source_registry", registry(source_id="fixture:concurrent"))]
        results = await asyncio.gather(
            *[append_batch(postgres_url, concurrent, fixture_clock=AT) for _ in range(2)]
        )
        assert results[0] == results[1]
        clocked = registry(source_id="fixture:clocked", provenance_class="reconstructed")
        clocked.pop("recorded_at")
        clocked_results = await asyncio.gather(
            *[append_batch(postgres_url, [("source_registry", clocked)]) for _ in range(2)]
        )
        assert clocked_results[0] == clocked_results[1]
        with pytest.raises(PayloadConflict):
            await append_batch(
                postgres_url,
                [
                    (
                        "source_registry",
                        registry(
                            source_id="fixture:concurrent",
                            endpoint="https://example.invalid/changed",
                        ),
                    )
                ],
                fixture_clock=AT,
            )

        # Actual receipt-to-store bridge on PostgreSQL, including immutable retry.
        from astrolabe.feature_store.source_bridge import import_diagnostic_capture
        from tests.unit.test_feature_store_source_bridge import captured

        capture = await captured(tmp_path)
        imported = await import_diagnostic_capture(postgres_url, capture["folder"])
        assert imported["observation"]["provenance_class"] == "synthetic"
        assert await import_diagnostic_capture(postgres_url, capture["folder"]) == imported

        # Changing privileges without changing column names must be detected.
        async with engine.begin() as conn:
            await conn.execute(text("GRANT SELECT ON fs2_source_observation TO anon"))
        drift = await migrations.check(postgres_url)
        assert not drift["current"] and any("drifted" in error for error in drift["errors"])
        with pytest.raises(migrations.MigrationRefused, match="incompatible"):
            await migrations.upgrade(postgres_url)
        with pytest.raises(ValueError, match="guarded local schema"):
            await import_diagnostic_capture(postgres_url, capture["folder"])
    finally:
        await engine.dispose()
