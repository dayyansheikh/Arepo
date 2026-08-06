# Database migration guide

## Mechanism

`astrolabe/storage/migrate.py` is a small, generic, additive migrator. It diffs the live database
against the complete SQLAlchemy ORM metadata (all model modules are imported in `_load_all_models`)
and:

1. `create_all` for any table the ORM defines but the database lacks;
2. `ALTER TABLE ... ADD COLUMN` for any column the ORM defines but an existing table lacks, rendered
   with the column's own type compiled for the active dialect (SQLite or PostgreSQL);
3. records the schema version in a `schema_migrations` table.

Old rows receive `NULL` (nullable columns) or the column's declared default, with one honest
exception: a **callable** default is only rendered for the container factories `list`/`dict` (as
`'[]'` / `'{}'`, which are constant and portable). A time/uuid callable default (e.g. `utcnow`,
`uuid4`) produces a different value per row, so it is NOT frozen into one literal — such a column is
added nullable and legacy rows read `NULL` for it. This never fabricates a historical value. A
`NOT NULL` column with no default is likewise added nullable so the migration cannot fail on
existing rows. (New rows always get the ORM default; only pre-existing rows are affected.)

## Commands

```
python -m astrolabe.storage.migrate_cli upgrade    # apply (idempotent, safe to rerun)
python -m astrolabe.storage.migrate_cli check      # print current vs expected version; exit 1 if behind
python -m astrolabe.storage.migrate_cli preflight  # exit 1 with an actionable message if behind (no changes)
```

`AUTO_MIGRATE` (default `true`): the CLIs and startup call `upgrade` automatically. Set
`AUTO_MIGRATE=false` in production to require an explicit migrate step; the bootstrap then runs
`preflight(auto_migrate=False)` and fails fast instead of altering the schema implicitly.

## Why not Alembic (decision)

The app has always used `create_all`, and every schema change to date is purely additive (new
tables, new nullable columns). The single real failure was that `create_all` never ALTERs an
existing table. A focused metadata-diff migrator fixes exactly that, runs from collector CLIs and a
startup preflight (not just a web request), needs no migration-script authoring for additive changes,
and behaves identically on SQLite and PostgreSQL. A conventional tool (Alembic) can be layered on
later if a **non-additive** change (drop/rename/type change) is ever required; this migrator
deliberately does not attempt those, so it can never destroy data.

## SQLite vs PostgreSQL

- Column types are compiled per dialect, so `ADD COLUMN` uses valid SQL on both.
- `test_migration.py::test_postgresql_ddl_compiles_for_research_tables` compiles the research-table
  DDL for the PostgreSQL dialect and asserts no SQLite-only construct (e.g. `AUTOINCREMENT`).
- The migrator uses plain `ALTER TABLE ADD COLUMN`, supported identically by both; it never uses a
  SQLite-only pragma or a Postgres-only feature.

## Bumping the version

When the ORM gains tables/columns, bump `SCHEMA_VERSION` and add a `SCHEMA_VERSION_NOTES` entry. The
actual migration is metadata-driven, so the number documents intent; `check` compares it and the
column diff to decide whether the schema is current.
