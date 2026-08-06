"""Additive schema migration for SQLite (development) and PostgreSQL (production).

Why not Alembic (documented decision, see docs/database-migration-guide.md): the app has always
bootstrapped with ``create_all`` and every schema change to date is purely ADDITIVE (new tables,
new nullable columns). The one real failure this repair addresses is that ``create_all`` creates
new TABLES but never ALTERs an existing table, so columns added in code after a table was first
created are silently absent (e.g. ``research_entries.momentum_direction``). A focused, generic
migrator that diffs the live database against the full ORM metadata and issues
``ALTER TABLE ... ADD COLUMN`` for anything missing fixes exactly that class of failure, runs from
the collector CLIs and a startup preflight (not only a web request), and works identically on
SQLite and PostgreSQL. It is safe to run once and harmless to rerun. A conventional migration tool
can be layered on later if a non-additive change (drop/rename/type-change) is ever required.

Guarantees: preserves existing rows; never drops a populated table; adds old-row columns as
nullable / with the column's declared default (never inventing historical evidence); records a
schema version; and provides explicit upgrade, current-version and preflight entry points.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.schema import CreateTable

from .db import Base, make_engine


def _load_all_models() -> None:
    """Import every ORM module so ``Base.metadata`` holds the COMPLETE current schema.

    The migrator diffs against this metadata, so a table missing from it would be silently skipped;
    importing them all here makes the diff exhaustive regardless of call site.
    """
    from ..accounts import models as _accounts  # noqa: F401
    from ..alerts import models as _alerts  # noqa: F401  (alert_history etc.)
    from ..evaluation import models as _eval  # noqa: F401
    from ..evaluation import research_models as _research  # noqa: F401
    from ..ingest import microstructure_store as _micro  # noqa: F401
    from ..opportunity import snapshot_models as _snap  # noqa: F401
    from . import models as _cache  # noqa: F401


_load_all_models()

# Bump whenever the ORM gains tables/columns. This is a monotonic marker recorded in
# ``schema_migrations``; the actual work is metadata-driven so the number is documentation, not a
# script selector.
SCHEMA_VERSION = 4
SCHEMA_VERSION_NOTES = {
    1: "initial create_all schema",
    2: "research per-family directions (momentum/orderbook/tradeflow) + edge-research tables",
    3: "research_cohorts.excluded_markets + degraded (universe degradation)",
    4: "research_cohorts.evaluation_origin_at + lateness_seconds + late + excessively_late "
       "(prospective-timestamp causal-origin audit)",
}

_VERSION_TABLE = "schema_migrations"


def _ensure_version_table(conn: Connection) -> None:
    conn.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {_VERSION_TABLE} "
            "(version INTEGER NOT NULL, applied_at VARCHAR NOT NULL)"
        )
    )


def _read_version(conn: Connection) -> int:
    _ensure_version_table(conn)
    row = conn.execute(text(f"SELECT MAX(version) FROM {_VERSION_TABLE}")).scalar()
    return int(row) if row is not None else 0


def _set_version(conn: Connection, version: int) -> None:
    _ensure_version_table(conn)
    conn.execute(
        text(f"INSERT INTO {_VERSION_TABLE} (version, applied_at) VALUES (:v, :a)"),
        {"v": version, "a": datetime.now(UTC).isoformat()},
    )


def _missing_columns(conn: Connection) -> list[tuple[str, str]]:
    """(table, column) pairs present in the ORM metadata but absent from the live database.

    Only considers tables that already exist (new tables are handled by ``create_all``).
    """
    insp = inspect(conn)
    existing_tables = set(insp.get_table_names())
    missing: list[tuple[str, str]] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        db_cols = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in db_cols:
                missing.append((table.name, col.name))
    return missing


def _add_column_sql(conn: Connection, table_name: str, column_name: str) -> str:
    """Render a dialect-correct ``ALTER TABLE ADD COLUMN`` for one ORM column.

    Old rows receive NULL (nullable columns) or the column's declared server_default / literal
    default; a NOT NULL column with no default is added as nullable at the DB level so the migration
    cannot fail on existing rows and no fake value is invented.
    """
    table = Base.metadata.tables[table_name]
    col = table.columns[column_name]
    dialect = conn.dialect
    coltype = col.type.compile(dialect=dialect)
    parts = [f"ADD COLUMN {column_name} {coltype}"]
    default_clause = ""
    if col.server_default is not None:
        # server_default.arg may be a text() clause or a literal.
        arg = getattr(col.server_default, "arg", None)
        default_clause = f" DEFAULT {getattr(arg, 'text', arg)}"
    elif col.default is not None and getattr(col.default, "is_scalar", False):
        val = col.default.arg
        literal = f"'{val}'" if isinstance(val, str) else str(val)
        default_clause = f" DEFAULT {literal}"
    elif col.default is not None and getattr(col.default, "is_callable", False):
        # Callable defaults (default=list / dict / utcnow / uuid4). SQLAlchemy WRAPS the callable,
        # we detect the constant container factories by INVOKING it: an empty list/dict yields a
        # portable static DEFAULT ('[]' / '{}'). Time/uuid callables produce a different value per
        # row and must NOT be frozen into one literal, so those columns are added nullable and old
        # rows read NULL (documented in docs/database-migration-guide.md). Closes the JSON/list
        # landmine (DB review MAJOR-5) without inventing a fake per-row value.
        try:
            produced = col.default.arg(None)  # wrapped callable accepts a context arg
        except Exception:  # noqa: BLE001 - a context-dependent default cannot be evaluated here
            produced = object()
        if isinstance(produced, list) and not produced:
            default_clause = " DEFAULT '[]'"
        elif isinstance(produced, dict) and not produced:
            default_clause = " DEFAULT '{}'"
    parts[0] += default_clause
    # Never add a hard NOT NULL to a table with existing rows and no default: keep it nullable so
    # the migration is safe and honest (no fabricated values).
    return f"ALTER TABLE {table_name} {parts[0]}"


# A fixed key for the Postgres advisory lock that serialises concurrent migrators.
_MIGRATION_LOCK_KEY = 917238


def _is_already_exists(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "already exists" in msg or "duplicate column" in msg or "duplicate_column" in msg


def _upgrade_sync(conn: Connection) -> dict:
    # Serialise concurrent migrators (multiple web replicas or overlapping cron jobs booting against
    # a behind schema at once) so only ONE performs the actual DDL. On Postgres a transaction-scoped
    # advisory lock does this cleanly; the loser waits, then finds nothing missing (a no-op). On
    # SQLite the write transaction already serialises; the duplicate-error tolerance below is the
    # belt-and-suspenders for both dialects (DB review CRITICAL-3).
    if conn.dialect.name == "postgresql":
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _MIGRATION_LOCK_KEY})

    # 1. Create any brand-new tables (create_all skips existing; tolerate a concurrent creator).
    try:
        Base.metadata.create_all(conn)
    except (OperationalError, IntegrityError, ProgrammingError) as exc:
        if not _is_already_exists(exc):
            raise
    # 2. Add any columns the ORM has but the existing tables lack (tolerate a concurrent adder).
    added: list[str] = []
    for table_name, column_name in _missing_columns(conn):
        try:
            conn.execute(text(_add_column_sql(conn, table_name, column_name)))
            added.append(f"{table_name}.{column_name}")
        except (OperationalError, ProgrammingError) as exc:
            if not _is_already_exists(exc):
                raise
    # 3. Record the schema version if we advanced it.
    before = _read_version(conn)
    if before < SCHEMA_VERSION:
        _set_version(conn, SCHEMA_VERSION)
    return {"from_version": before, "to_version": SCHEMA_VERSION, "columns_added": added}


def _check_sync(conn: Connection) -> dict:
    missing = _missing_columns(conn)
    insp = inspect(conn)
    existing = set(insp.get_table_names())
    missing_tables = [t.name for t in Base.metadata.sorted_tables if t.name not in existing]
    version = _read_version(conn)
    return {
        "current": not missing and not missing_tables and version >= SCHEMA_VERSION,
        "schema_version": version,
        "expected_version": SCHEMA_VERSION,
        "missing_columns": [f"{t}.{c}" for t, c in missing],
        "missing_tables": missing_tables,
    }


async def upgrade(engine: AsyncEngine | None = None) -> dict:
    """Apply the additive migration. Idempotent: a second run adds nothing and returns []."""
    eng = engine or make_engine()
    async with eng.begin() as conn:
        return await conn.run_sync(_upgrade_sync)


async def check(engine: AsyncEngine | None = None) -> dict:
    """Report whether the live schema matches the current ORM (no side effects)."""
    eng = engine or make_engine()
    async with eng.connect() as conn:
        return await conn.run_sync(_check_sync)


class OutdatedSchemaError(RuntimeError):
    """Raised by the preflight when the schema is behind the ORM and auto-migrate is off."""


async def preflight(engine: AsyncEngine | None = None, *, auto_migrate: bool = True) -> dict:
    """Ensure the schema is current BEFORE any cohort work.

    With ``auto_migrate`` (the default for CLIs and startup), it upgrades in place. With
    ``auto_migrate=False`` it raises an actionable :class:`OutdatedSchemaError` instead of letting a
    low-level missing-column error surface halfway through a cohort freeze.
    """
    status = await check(engine)
    if status["current"]:
        return status
    if auto_migrate:
        result = await upgrade(engine)
        after = await check(engine)
        after["migrated"] = result
        return after
    raise OutdatedSchemaError(
        "Database schema is outdated. Missing "
        f"columns={status['missing_columns']} tables={status['missing_tables']}. "
        "Run `python -m astrolabe.storage.migrate_cli upgrade` (or enable AUTO_MIGRATE) before "
        "freezing cohorts."
    )


def ddl_preview(dialect_name: str = "postgresql") -> list[str]:
    """Return the CREATE TABLE DDL the ORM would emit for a dialect (used by portability tests)."""
    from sqlalchemy.dialects import postgresql, sqlite

    dialect = {"postgresql": postgresql.dialect(), "sqlite": sqlite.dialect()}[dialect_name]
    return [str(CreateTable(t).compile(dialect=dialect)) for t in Base.metadata.sorted_tables]
