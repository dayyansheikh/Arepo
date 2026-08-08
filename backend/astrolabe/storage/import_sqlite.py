"""Safe one-time SQLite -> PostgreSQL data import (master prompt §10 / Phase 4).

Copies the genuine local SQLite database into a production Postgres database WITHOUT recomputing,
"fixing" or fabricating anything. The source is opened READ-ONLY. Every value — primary keys, FKs,
keys, timestamps, nulls, frozen research values, calculation versions and provenance — is carried
across verbatim; the only transformation is coercing SQLite's naive datetimes to UTC-aware instants,
because the whole application already treats stored times as UTC (and Postgres ``timestamptz``
requires it). No numbers are re-derived.

Design:
* **read-only source** — opened with ``?mode=ro`` so an import can never mutate the genuine DB;
* **dry-run** — ``--dry-run`` reports source row counts and the plan, writes nothing;
* **idempotent** — rows are inserted with ``ON CONFLICT (pk) DO NOTHING`` (Postgres), so a re-run
  adds only what is missing and never duplicates; ``--require-empty`` instead refuses to touch a
  destination that already holds data;
* **transactional** — each table copies inside a transaction; a failure rolls that table back;
* **verified** — after import it reconciles per-table counts and checks known cohort invariants,
  and FAILS (non-zero) if reconciliation does not match, so a broken import cannot pass silently.

No credentials live in code: the destination URL comes from ``--dest`` or ``$DATABASE_URL`` / an env
var you pass; the source path from ``--source``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import DateTime, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import create_async_engine

from .db import Base
from .migrate import _load_all_models, upgrade

_load_all_models()  # ensure Base.metadata holds the COMPLETE schema before we iterate tables


def _sqlite_ro_url(path: str) -> str:
    """A read-only aiosqlite URL for ``path`` (URI mode so the file is never opened writable)."""
    return f"sqlite+aiosqlite:///file:{path}?mode=ro&uri=true"


def _coerce_row(table, row: dict) -> dict:
    """Carry values verbatim, coercing only naive datetimes to UTC-aware (see module docstring)."""
    out = dict(row)
    for col in table.columns:
        if isinstance(col.type, DateTime):
            v = out.get(col.name)
            if isinstance(v, datetime) and v.tzinfo is None:
                out[col.name] = v.replace(tzinfo=UTC)
    return out


async def _count(engine, table) -> int:
    """Row count, or 0 if the table does not exist in this database (e.g. a source that predates a
    later additive table). A missing source table simply has nothing to import."""
    from sqlalchemy.exc import OperationalError, ProgrammingError
    try:
        async with engine.connect() as conn:
            return int(await conn.scalar(select(func.count()).select_from(table)) or 0)
    except (OperationalError, ProgrammingError):
        return 0


async def import_all(
    *, source_path: str, dest_url: str, dry_run: bool = False, require_empty: bool = False,
    batch_size: int = 500,
) -> dict:
    """Import every table from the SQLite file into the destination DB. Returns a report dict."""
    src = create_async_engine(_sqlite_ro_url(source_path), future=True)
    dst = create_async_engine(dest_url, future=True)
    is_pg = dst.dialect.name == "postgresql"
    report: dict = {"dry_run": dry_run, "destination_dialect": dst.dialect.name, "tables": {}}
    try:
        if not dry_run:
            await upgrade(dst)  # ensure the destination schema exists and is current

        tables = list(Base.metadata.sorted_tables)  # FK-dependency order for inserts
        for table in tables:
            src_rows = await _count(src, table)
            # Query real destination counts even in dry-run so an operator sees whether the real run
            # would be refused by --require-empty (dry-run previously reported dest as 0 and could
            # not warn about a non-empty destination).
            dst_before = await _count(dst, table)
            entry = {"source_rows": src_rows, "dest_rows_before": dst_before}

            if dry_run:
                entry["would_insert"] = src_rows
                if require_empty and dst_before > 0:
                    entry["would_refuse"] = True
                    report["would_refuse"] = True
                report["tables"][table.name] = entry
                continue

            if src_rows == 0:
                entry["inserted"] = 0
                entry["dest_rows_after"] = dst_before
                report["tables"][table.name] = entry
                continue

            if require_empty and dst_before > 0:
                raise RuntimeError(
                    f"destination table {table.name!r} already has {dst_before} rows and "
                    f"--require-empty was set; refusing to import into a non-empty destination"
                )

            # Read all source rows, then insert in batches with PK-conflict tolerance (idempotent).
            async with src.connect() as sconn:
                rows = [dict(m) for m in (await sconn.execute(select(table))).mappings().all()]
            inserted = 0
            async with dst.begin() as dconn:
                for i in range(0, len(rows), batch_size):
                    chunk = [_coerce_row(table, r) for r in rows[i:i + batch_size]]
                    if not chunk:
                        continue
                    if is_pg:
                        stmt = pg_insert(table).values(chunk)
                        pk_cols = [c.name for c in table.primary_key.columns]
                        stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols) if pk_cols \
                            else stmt
                        result = await dconn.execute(stmt)
                    else:
                        # SQLite parity for idempotency: OR IGNORE skips PK-conflict rows on re-run.
                        result = await dconn.execute(insert(table).prefix_with("OR IGNORE"), chunk)
                    inserted += result.rowcount if result.rowcount and result.rowcount > 0 else 0
            entry["inserted"] = inserted
            entry["dest_rows_after"] = await _count(dst, table)
            report["tables"][table.name] = entry

        # Fix Postgres identity sequences so future inserts don't collide with imported PKs.
        if not dry_run and is_pg:
            report["sequences_reset"] = await _reset_sequences(dst, tables)

        report["reconciliation"] = await _reconcile(src, dst, tables, dry_run=dry_run)
    finally:
        await src.dispose()
        await dst.dispose()
    return report


async def _reset_sequences(engine, tables) -> list[str]:
    from sqlalchemy import text
    reset: list[str] = []
    async with engine.begin() as conn:
        for table in tables:
            pk = list(table.primary_key.columns)
            if len(pk) != 1 or not pk[0].autoincrement:
                continue
            col = pk[0].name
            await conn.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{table.name}', '{col}'), "
                f"COALESCE((SELECT MAX({col}) FROM {table.name}), 1), true)"
            ))
            reset.append(table.name)
    return reset


async def _reconcile(src, dst, tables, *, dry_run: bool) -> dict:
    """Per-table count reconciliation + known cohort invariants. ``ok`` False means DO NOT trust."""
    mismatches: list[str] = []
    counts: dict[str, dict] = {}
    for table in tables:
        s = await _count(src, table)
        d = 0 if dry_run else await _count(dst, table)
        counts[table.name] = {"source": s, "dest": d}
        # The contract is "no SOURCE row was lost", i.e. dest >= source. dest > source is legitimate
        # and expected on an idempotent re-import into a LIVE database (the scheduler has added
        # production rows), so it is not a mismatch. Exact equality for a first import is guaranteed
        # instead by --require-empty (refuses a non-empty destination up front).
        if not dry_run and d < s:
            mismatches.append(f"{table.name}: dest {d} < source {s}")

    invariants: list[dict] = []
    if not dry_run:
        # Every FROZEN cohort must keep entry_count == universe_size in the destination (the same
        # invariant the repair path enforces); a violation means entries were lost in transit.
        from ..evaluation.research_models import ResearchCohortRow, ResearchEntryRow
        async with dst.connect() as conn:
            cohorts = (await conn.execute(
                select(ResearchCohortRow.id, ResearchCohortRow.universe_size,
                       ResearchCohortRow.frozen, ResearchCohortRow.cadence)
            )).all()
            for cid, universe_size, frozen, cadence in cohorts:
                n = int(await conn.scalar(
                    select(func.count(ResearchEntryRow.id)).where(ResearchEntryRow.cohort_id == cid)
                ) or 0)
                ok = (not frozen) or (n == universe_size)
                invariants.append({"cohort_id": cid, "cadence": cadence, "frozen": frozen,
                                   "universe_size": universe_size, "entries": n, "ok": ok})
                if not ok:
                    mismatches.append(
                        f"cohort {cid}: entries {n} != universe_size {universe_size}")

    return {"ok": not mismatches, "counts": counts, "cohort_invariants": invariants,
            "mismatches": mismatches}


async def _run(args: argparse.Namespace) -> int:
    import os
    dest = args.dest or os.environ.get("DATABASE_URL", "")
    if not dest:
        print("error: no destination; pass --dest or set DATABASE_URL")
        return 2
    if "sqlite" in dest and not args.allow_sqlite_dest:
        print("error: destination looks like SQLite; this tool imports INTO Postgres. Pass "
              "--allow-sqlite-dest only for tests.")
        return 2
    try:
        report = await import_all(
            source_path=args.source, dest_url=dest, dry_run=args.dry_run,
            require_empty=args.require_empty,
        )
    except RuntimeError as exc:
        print(f"IMPORT REFUSED: {exc}")
        return 1
    print(json.dumps(report, indent=2, default=str))
    recon = report.get("reconciliation", {})
    if not args.dry_run and not recon.get("ok", False):
        print("RECONCILIATION FAILED — destination is NOT trustworthy; see mismatches above.")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="astrolabe.storage.import_sqlite", description=__doc__)
    p.add_argument("--source", required=True, help="path to the source SQLite .db file (read-only)")
    p.add_argument("--dest", default=None, help="destination SQLAlchemy URL (else $DATABASE_URL)")
    p.add_argument("--dry-run", action="store_true", help="report the plan; write nothing")
    p.add_argument("--require-empty", action="store_true",
                   help="refuse if any destination table already has rows (vs idempotent upsert)")
    p.add_argument("--allow-sqlite-dest", action="store_true",
                   help="permit a SQLite destination (tests only)")
    return p


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
