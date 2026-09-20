"""Explicit local-only v2 migrations. No inherited settings, startup hooks or backfill."""

from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.schema import AddConstraint, CreateIndex, CreateTable

from .models import FeatureStoreBase
from .types import canonical_json

VERSION = 1
LEDGER = "fs2_schema_migrations"
LOCAL_DB = re.compile(r"fs2_test_[a-z0-9_]+\Z")


class MigrationRefused(ValueError):
    pass


def validate_local_url(url: str) -> None:
    """Fail before connection creation. Local proxying to production is never authorised."""
    parsed = make_url(url)
    if parsed.query:
        raise MigrationRefused("connection query overrides are not permitted")
    if parsed.drivername == "sqlite+aiosqlite":
        if parsed.database == ":memory:":
            return
        declared_path = Path(parsed.database or "")
        if not declared_path.is_absolute():
            raise MigrationRefused("SQLite fixture path must be absolute")
        path = declared_path.resolve()
        if not path.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise MigrationRefused(
                "SQLite must be a disposable file under the OS temporary directory"
            )
        if not LOCAL_DB.fullmatch(path.stem):
            raise MigrationRefused("SQLite fixture name must begin fs2_test_")
        return
    if parsed.drivername == "postgresql+asyncpg":
        if parsed.host not in {"127.0.0.1", "::1", "localhost"}:
            raise MigrationRefused("PostgreSQL must be an explicit local test cluster")
        if parsed.port is None or parsed.port == 5432:
            raise MigrationRefused("use an explicit nondefault test-cluster port")
        if not LOCAL_DB.fullmatch(parsed.database or ""):
            raise MigrationRefused("PostgreSQL database name must begin fs2_test_")
        return
    raise MigrationRefused(
        "only explicit disposable SQLite or local PostgreSQL targets are supported"
    )


def local_engine(url: str) -> AsyncEngine:
    validate_local_url(url)
    engine = create_async_engine(url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def configure_sqlite(connection, _record):
            # Explicit BEGIN makes DDL transactional on sqlite3's legacy transaction mode.
            connection.isolation_level = None
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA recursive_triggers=ON")
            cursor.close()

        @event.listens_for(engine.sync_engine, "begin")
        def begin_sqlite(connection):
            connection.exec_driver_sql("BEGIN")

    return engine


def ddl_preview(dialect_name: str) -> list[str]:
    from sqlalchemy.dialects import postgresql, sqlite

    dialect = {"postgresql": postgresql.dialect(), "sqlite": sqlite.dialect()}[dialect_name]
    statements = [
        str(CreateTable(t).compile(dialect=dialect))
        for t in FeatureStoreBase.metadata.sorted_tables
    ]
    statements.extend(
        str(CreateIndex(i).compile(dialect=dialect))
        for t in FeatureStoreBase.metadata.sorted_tables
        for i in sorted(t.indexes, key=lambda item: item.name)
    )
    if dialect_name == "postgresql":
        statements.extend(
            str(AddConstraint(fk).compile(dialect=dialect))
            for table in FeatureStoreBase.metadata.sorted_tables
            for fk in sorted(table.foreign_key_constraints, key=lambda item: str(item.columns))
            if fk.use_alter
        )
    return statements


def schema_hash(dialect_name: str) -> str:
    return hashlib.sha256(
        canonical_json(
            {"ddl": ddl_preview(dialect_name), "guard_contract": "immutable-private-v1"}
        ).encode()
    ).hexdigest()


def installed_hash(conn) -> str:
    """Fingerprint actual constraints, indexes, triggers and privileges after installation.

    This is a local drift detector, not protection against an owner rewriting the ledger.
    No pg_catalog OIDs or changing statistics enter the fingerprint.
    """
    inspector = inspect(conn)
    existing = set(inspector.get_table_names())
    state = {}
    for name in sorted(set(FeatureStoreBase.metadata.tables) | {LEDGER}):
        if name not in existing:
            state[name] = None
            continue
        columns = inspector.get_columns(name)
        for column in columns:
            column["type"] = str(column["type"].compile(dialect=conn.dialect))
        table = {
            "columns": columns,
            "pk": inspector.get_pk_constraint(name),
            "foreign_keys": sorted(inspector.get_foreign_keys(name), key=canonical_json),
            "unique": sorted(inspector.get_unique_constraints(name), key=canonical_json),
            "checks": sorted(inspector.get_check_constraints(name), key=canonical_json),
            "indexes": sorted(inspector.get_indexes(name), key=canonical_json),
        }
        if conn.dialect.name == "sqlite":
            table["triggers"] = [
                list(row)
                for row in conn.execute(
                    text(
                        "SELECT name, sql FROM sqlite_master WHERE type='trigger' "
                        "AND tbl_name=:name ORDER BY name"
                    ),
                    {"name": name},
                )
            ]
        else:
            table["security"] = list(
                conn.execute(
                    text(
                        "SELECT relrowsecurity, relforcerowsecurity, relacl::text "
                        "FROM pg_class WHERE oid=to_regclass(:name)"
                    ),
                    {"name": name},
                ).one()
            )
            table["policies"] = [
                list(row)
                for row in conn.execute(
                    text(
                        "SELECT polname, polcmd::text, polpermissive, polroles::text, "
                        "pg_get_expr(polqual, polrelid), pg_get_expr(polwithcheck, polrelid) "
                        "FROM pg_policy WHERE polrelid=to_regclass(:name) ORDER BY polname"
                    ),
                    {"name": name},
                )
            ]
            table["triggers"] = [
                list(row)
                for row in conn.execute(
                    text(
                        "SELECT tgname, tgenabled::text, pg_get_triggerdef(oid) FROM pg_trigger "
                        "WHERE tgrelid=to_regclass(:name) AND NOT tgisinternal ORDER BY tgname"
                    ),
                    {"name": name},
                )
            ]
        state[name] = table
    if conn.dialect.name == "postgresql":
        state["guard_function"] = [
            list(row)
            for row in conn.execute(
                text(
                    "SELECT pg_get_functiondef(oid), proacl::text FROM pg_proc "
                    "WHERE oid=to_regprocedure('fs2_reject_mutation()')"
                )
            )
        ]
    return hashlib.sha256(canonical_json(state).encode()).hexdigest()


def _check_sync(conn) -> dict:
    inspector = inspect(conn)
    existing = set(inspector.get_table_names())
    expected = {t.name for t in FeatureStoreBase.metadata.tables.values()}
    missing = sorted(expected - existing)
    errors = []
    for table in FeatureStoreBase.metadata.tables.values():
        if table.name not in existing:
            continue
        actual = {c["name"]: c for c in inspector.get_columns(table.name)}
        if set(actual) != set(table.columns.keys()):
            errors.append(f"{table.name}: columns differ")
        for col in table.columns:
            if col.name not in actual:
                continue
            got = actual[col.name]
            if bool(got["nullable"]) != col.nullable and not col.primary_key:
                errors.append(f"{table.name}.{col.name}: nullability differs")
            intended = str(col.type.compile(dialect=conn.dialect)).upper()
            observed = str(got["type"].compile(dialect=conn.dialect)).upper()
            if intended != observed:
                errors.append(f"{table.name}.{col.name}: type differs")
    if LEDGER not in existing:
        return {
            "current": False,
            "version": None,
            "missing_tables": missing,
            "errors": errors,
            "ledger_present": False,
        }
    ledger_columns = {col["name"] for col in inspector.get_columns(LEDGER)}
    if ledger_columns != {"version", "schema_hash", "installed_hash", "applied_at"}:
        return {
            "current": False,
            "version": None,
            "missing_tables": missing,
            "errors": [*errors, "incompatible migration ledger"],
            "ledger_present": True,
        }
    version = conn.execute(text(f"SELECT version, schema_hash, installed_hash FROM {LEDGER}")).all()
    wanted_hash = schema_hash(conn.dialect.name)
    if len(version) != 1 or version[0][0] != VERSION or version[0][1] != wanted_hash:
        errors.append("migration ledger version/checksum differs")
    if len(version) == 1 and version[0][2] != installed_hash(conn):
        errors.append("installed constraints, indexes, guards or privileges have drifted")
    if any(name.startswith("fs2_") and name not in expected | {LEDGER} for name in existing):
        errors.append("unexpected v2 tables")
    for table in sorted(expected & existing):
        if conn.dialect.name == "sqlite":
            triggers = set(
                conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=:table"),
                    {"table": table},
                ).scalars()
            )
            if not {f"{table}_no_update", f"{table}_no_delete"}.issubset(triggers):
                errors.append(f"{table}: immutability guards missing")
        else:
            state = conn.execute(
                text("SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:table)"),
                {"table": table},
            ).scalar()
            if state is not True:
                errors.append(f"{table}: RLS missing")
            triggers = set(
                conn.execute(
                    text(
                        "SELECT tgname FROM pg_trigger WHERE tgrelid=to_regclass(:table) "
                        "AND NOT tgisinternal AND tgenabled='O'"
                    ),
                    {"table": table},
                ).scalars()
            )
            if not {f"{table}_immutable", f"{table}_no_truncate"}.issubset(triggers):
                errors.append(f"{table}: immutability guard missing")
    return {
        "current": not missing and not errors,
        "version": version[-1][0] if version else None,
        "missing_tables": missing,
        "errors": errors,
        "ledger_present": True,
    }


async def check(url: str) -> dict:
    """Read-only schema inspection: never creates a version table."""
    validate_local_url(url)
    parsed = make_url(url)
    if (
        parsed.drivername == "sqlite+aiosqlite"
        and parsed.database != ":memory:"
        and not Path(parsed.database).exists()
    ):
        return {
            "current": False,
            "version": None,
            "ledger_present": False,
            "missing_tables": sorted(FeatureStoreBase.metadata.tables),
            "errors": [],
            "database_present": False,
        }
    engine = local_engine(url)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(_check_sync)
    finally:
        await engine.dispose()


def _install_guards(conn) -> None:
    tables = sorted(FeatureStoreBase.metadata.tables)
    if conn.dialect.name == "postgresql":
        conn.execute(
            text("""
            CREATE FUNCTION fs2_reject_mutation() RETURNS trigger
            LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $$
            BEGIN RAISE EXCEPTION 'immutable v2 research record'; END $$
        """)
        )
        conn.execute(text("REVOKE ALL ON FUNCTION fs2_reject_mutation() FROM PUBLIC"))
        roles = set(conn.execute(text("SELECT rolname FROM pg_roles")).scalars())
        for table in tables:
            conn.execute(
                text(
                    f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE "
                    f"ON {table} FOR EACH ROW EXECUTE FUNCTION fs2_reject_mutation()"
                )
            )
            conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            conn.execute(
                text(
                    f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
                    "FOR EACH STATEMENT EXECUTE FUNCTION fs2_reject_mutation()"
                )
            )
            for role in ["PUBLIC", *sorted(roles & {"anon", "authenticated", "service_role"})]:
                conn.execute(text(f"REVOKE ALL ON TABLE {table} FROM {role}"))
    else:
        for table in tables:
            for operation in ("UPDATE", "DELETE"):
                conn.execute(
                    text(
                        f"CREATE TRIGGER {table}_no_{operation.lower()} "
                        f"BEFORE {operation} ON {table} "
                        "BEGIN SELECT RAISE(ABORT, 'immutable v2 research record'); END"
                    )
                )


def _upgrade_sync(conn) -> dict:
    if conn.dialect.name == "postgresql":
        conn.execute(text("SELECT pg_advisory_xact_lock(917239)"))
    current = _check_sync(conn)
    if current["current"]:
        return {"created": False, "version": VERSION}
    existing = set(inspect(conn).get_table_names())
    if any(name.startswith("fs2_") for name in existing):
        raise MigrationRefused("partial or incompatible v2 schema; refusing implicit repair")
    FeatureStoreBase.metadata.create_all(conn)
    _install_guards(conn)
    conn.execute(
        text(
            f"CREATE TABLE {LEDGER} (version INTEGER PRIMARY KEY, "
            "schema_hash VARCHAR(64) NOT NULL, installed_hash VARCHAR(64) NOT NULL, "
            "applied_at VARCHAR(32) NOT NULL)"
        )
    )
    if conn.dialect.name == "postgresql":
        conn.execute(text(f"ALTER TABLE {LEDGER} ENABLE ROW LEVEL SECURITY"))
        roles = set(conn.execute(text("SELECT rolname FROM pg_roles")).scalars())
        for role in ["PUBLIC", *sorted(roles & {"anon", "authenticated", "service_role"})]:
            conn.execute(text(f"REVOKE ALL ON TABLE {LEDGER} FROM {role}"))
    from datetime import UTC, datetime

    conn.execute(
        text(f"INSERT INTO {LEDGER} VALUES (:version, :hash, :installed, :at)"),
        {
            "version": VERSION,
            "hash": schema_hash(conn.dialect.name),
            "installed": installed_hash(conn),
            "at": datetime.now(UTC).isoformat(),
        },
    )
    return {"created": True, "version": VERSION}


async def upgrade(url: str) -> dict:
    """Explicit opt-in, isolated local database only; transaction rolls back failed creation."""
    engine = local_engine(url)
    try:
        async with engine.begin() as conn:
            return await conn.run_sync(_upgrade_sync)
    finally:
        await engine.dispose()
