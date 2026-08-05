# Schema failure investigation

## Reproduced failure

```
$ python -m astrolabe.evaluation.research_cli research-freeze --cadence 6h
sqlite3.OperationalError: no such column: research_entries.momentum_direction
```

The ORM SELECT listed `momentum_direction`, `orderbook_direction`, `tradeflow_direction` against a
`research_entries` table that had only 34 of the current 37 columns.

## Root cause (confirmed)

1. `research_entries` was first created by `create_all()` during an earlier edge-research run, when
   the ORM had 34 columns.
2. The per-family direction columns (`momentum_direction`, `orderbook_direction`,
   `tradeflow_direction`) were added to the ORM **in code** in a later commit.
3. `create_all()` creates missing TABLES but **never ALTERs an existing table**, so those three
   columns were never added to the already-existing `research_entries`.
4. The freeze's first `add_entry` issued a SELECT including the new columns → `no such column`.
5. This is a generic class of failure for any additive column on any pre-existing table, and it
   **would also affect PostgreSQL** after the first deploy if the ORM later gained a column, because
   the production bootstrap used the same bare `create_all`.

Confirmed sub-questions from the prompt:

- create_all created the table in an earlier schema: **yes**.
- later ORM changes added columns only in code: **yes** (the 3 per-family directions).
- create_all did not alter the existing table: **yes**, by design.
- the failed freeze created an incomplete cohort before entry insertion failed: **no** — the freeze
  commits once at the end, so the flushed-but-uncommitted cohort rolled back; the DB showed 0
  research cohorts. (Atomicity is still made explicit and tested in this pass, prompt section 4.)
- other ORM columns also absent: **only those 3** (verified by the metadata diff; `check` reported
  exactly them).
- same defect could affect PostgreSQL: **yes**, now prevented by the migrator + preflight.

## Fix

An additive, metadata-driven migrator (`astrolabe/storage/migrate.py`) that diffs the live database
against the complete ORM metadata and issues `ALTER TABLE ... ADD COLUMN` for any missing column,
plus `create_all` for any missing table, records a schema version, and exposes explicit `upgrade` /
`check` / `preflight` entry points. The bootstrap now runs it (or the fail-fast preflight when
`AUTO_MIGRATE=false`) so a missing column can never surface halfway through a freeze. Verified on the
real `astrolabe.db`: 0 → v2, 3 columns added, rows preserved, idempotent. See
`docs/database-migration-guide.md`.

## Last-resort local reset (documented, not used)

Because no real prospective evidence exists yet, a developer MAY reset a corrupt local database with
`rm backend/astrolabe.db && python -m astrolabe.storage.migrate_cli upgrade`. This is a last resort
for local development only; the migration path above is the supported mechanism and the only one
used for production.
