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


# Tables our own schema-creation / app-startup seeds with a baseline row (not real research data),
# so a freshly-migrated destination is not literally empty. ``--clean`` may wipe these before
# importing an exact copy of the source; data in ANY OTHER table is treated as real and refused.
_BASELINE_SEED_TABLES = {"calculation_versions"}


async def _clean_destination(dst, tables) -> dict:
    """Empty the destination ORM tables so the import is a byte-exact copy of the source.

    SAFETY: refuses if any non-baseline table already holds data, so this can NEVER wipe a populated
    production database — only a fresh, migration-seeded one (the initial-import case).
    """
    real_nonempty = []
    for t in tables:
        if t.name in _BASELINE_SEED_TABLES:
            continue
        if await _count(dst, t) > 0:
            real_nonempty.append(t.name)
    if real_nonempty:
        raise RuntimeError(
            f"--clean refused: destination already contains data in {real_nonempty}; it is not a "
            "fresh/baseline-only database, so refusing to wipe it. Use a fresh database for the "
            "initial import."
        )
    async with dst.begin() as conn:
        for t in reversed(tables):  # children before parents (reverse FK-dependency order)
            await conn.execute(t.delete().execution_options(synchronize_session=False))
    return {"cleaned_tables": len(tables)}


async def import_all(
    *, source_path: str, dest_url: str, dry_run: bool = False, require_empty: bool = False,
    clean: bool = False, batch_size: int = 500,
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

        if clean and not dry_run:
            # Wipe migration-seeded baseline rows so the destination matches the source exactly and
            # value-verification passes on a database our own migration pre-seeded (e.g.
            # calculation_versions), while refusing to touch a destination that holds real data.
            report["clean"] = await _clean_destination(dst, tables)
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


def _integer_pk_column(table) -> str | None:
    """Name of the table's single INTEGER primary-key column, else None.

    Only integer PKs are backed by a sequence in Postgres. ``Column.autoincrement`` defaults to the
    truthy string ``"auto"`` even for a text PK (e.g. ``calculation_versions.version``), so it must
    NOT be used to decide this — checking the column TYPE is the correct test. BigInteger subclasses
    Integer, so it is covered.
    """
    from sqlalchemy import Integer
    pk = list(table.primary_key.columns)
    if len(pk) == 1 and isinstance(pk[0].type, Integer):
        return pk[0].name
    return None


async def _reset_sequences(engine, tables) -> list[str]:
    """Advance each imported integer-PK sequence past the imported max, so later app inserts don't
    collide with imported primary keys. Skips text/composite PKs and any column with no backing
    sequence."""
    from sqlalchemy import text
    reset: list[str] = []
    async with engine.begin() as conn:
        for table in tables:
            col = _integer_pk_column(table)
            if col is None:
                continue
            seq = await conn.scalar(
                text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": table.name, "c": col})
            if not seq:  # integer PK with no serial/identity sequence (nothing to reset)
                continue
            await conn.execute(text(
                f"SELECT setval('{seq}', "
                f"COALESCE((SELECT MAX({col}) FROM {table.name}), 1), true)"))
            reset.append(table.name)
    return reset


def _norm_value(col, value):
    """Canonicalise one column value for cross-database equality (see _verify_values)."""
    if value is None:
        return None
    if isinstance(col.type, DateTime) and isinstance(value, datetime):
        v = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return v.astimezone(UTC).isoformat()
    if isinstance(value, (dict, list)):
        import json
        return json.dumps(value, sort_keys=True, default=str)
    if isinstance(value, datetime):  # a datetime in a non-DateTime column (defensive)
        v = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return v.astimezone(UTC).isoformat()
    return value


def _pk_key(table, row: dict):
    return tuple(row[c.name] for c in table.primary_key.columns)


async def _verify_values(src, dst, tables) -> dict:
    """Verify that EVERY source record exists in the destination with identical immutable values.

    Spec §10: destination growth (later production rows) must not hide a corrupted imported source
    row. Counts alone can't catch a same-PK-different-content row (ON CONFLICT DO NOTHING would keep
    the pre-existing dest row). This copies verbatim, so every source row must have a byte-equal
    destination row (datetimes normalised to UTC, JSON canonicalised) on the source's columns.
    Returns per-table checked/missing/value_mismatch counts + capped examples; ``ok`` is overall.
    """
    per_table: dict[str, dict] = {}
    examples: list[str] = []
    total_checked = total_missing = total_diff = 0
    for table in tables:
        cols = list(table.columns)
        if not list(table.primary_key.columns):
            continue
        async with src.connect() as sconn:
            src_rows = [dict(m) for m in (await sconn.execute(select(table))).mappings().all()]
        if not src_rows:
            continue
        async with dst.connect() as dconn:
            dst_index = {
                _pk_key(table, dict(m)): dict(m)
                for m in (await dconn.execute(select(table))).mappings().all()
            }
        checked = missing = diff = 0
        for s in src_rows:
            checked += 1
            d = dst_index.get(_pk_key(table, s))
            if d is None:
                missing += 1
                if len(examples) < 20:
                    examples.append(f"{table.name} pk={_pk_key(table, s)}: MISSING in dest")
                continue
            for c in cols:
                if _norm_value(c, s.get(c.name)) != _norm_value(c, d.get(c.name)):
                    diff += 1
                    if len(examples) < 20:
                        examples.append(
                            f"{table.name} pk={_pk_key(table, s)} col={c.name}: "
                            f"source={s.get(c.name)!r} != dest={d.get(c.name)!r}")
                    break
        per_table[table.name] = {"checked": checked, "missing": missing, "value_mismatch": diff}
        total_checked += checked
        total_missing += missing
        total_diff += diff
    return {
        "ok": total_missing == 0 and total_diff == 0,
        "checked_rows": total_checked,
        "missing_rows": total_missing,
        "value_mismatch_rows": total_diff,
        "per_table": per_table,
        "examples": examples,
    }


async def _reconcile(src, dst, tables, *, dry_run: bool) -> dict:
    """Per-table count reconciliation + cohort invariants + per-record value verification.

    ``ok`` False means DO NOT trust the destination.
    """
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

    # Per-record immutable-value verification (spec §10): every source row must exist in the
    # destination with identical values. This is what makes destination growth safe — extra
    # production rows can never hide a corrupted imported source row.
    values = {"ok": True, "checked_rows": 0} if dry_run else await _verify_values(src, dst, tables)
    if not values["ok"]:
        mismatches.append(
            f"value verification failed: {values['missing_rows']} missing + "
            f"{values['value_mismatch_rows']} value-mismatch rows (see examples)")

    return {"ok": not mismatches, "counts": counts, "cohort_invariants": invariants,
            "value_verification": values, "mismatches": mismatches}


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
            require_empty=args.require_empty, clean=args.clean,
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
    p.add_argument("--clean", action="store_true",
                   help="empty the destination's migration-seeded baseline rows first so the "
                        "import exactly copies the source; refuses if a real-data table is "
                        "non-empty (safe for the initial import into a fresh database)")
    p.add_argument("--allow-sqlite-dest", action="store_true",
                   help="permit a SQLite destination (tests only)")
    return p


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
