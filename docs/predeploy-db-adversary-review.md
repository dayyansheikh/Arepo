# Predeploy DB/migration + operational adversary review

Reviewer: independent database/migration + operational-adversary pass over the
`arepo-final-predeployment-launch-readiness` branch's schema-migration repair and cohort-freeze
hardening. All findings below were reproduced with runnable scripts against the actual code (not
just read), unless marked "by inspection".

**Bottom line**

- The migration is **NOT safely wired into the live web server**. `astrolabe/storage/migrate.py`
  (the new upgrade/preflight/AUTO_MIGRATE machinery) is only ever invoked from CLI entry points.
  The FastAPI app's own startup path (`api/deps.py::init_storage()` → `storage/db.py::init_db()`)
  still calls bare `create_all`, reproducing the exact "columns never get ALTERed onto an existing
  table" failure this whole effort was meant to close — for the process that actually serves
  `/api/research/status`. See CRITICAL-1.
- Given the CLIs are used and run before the web tier, `upgrade()` is correct and portable on
  SQLite and Postgres for the cases exercised by the tests (adds every missing column, compiles
  valid dialect-specific DDL, is idempotent once current). But it is **not safe under concurrency**
  during an actual migration (two instances/jobs racing to migrate a behind schema at once) — see
  CRITICAL-3.
- An incomplete/duplicate cohort **can** become visible evidence: not via the unique constraint
  (which holds), but via a reproduced TOCTOU bug in `repair_incomplete()`/`delete_cohort()` that
  can **delete a legitimately-just-frozen, complete cohort** — see CRITICAL-2. This is the opposite
  of "duplicate/incomplete evidence leaking in," but it is worse: silent, irreversible loss of valid
  frozen research evidence.

---

## CRITICAL-1 — the web app never runs the migrator; docs overstate what happens at boot

`backend/astrolabe/api/app.py:33` → `backend/astrolabe/api/deps.py:36-49` (`init_storage`) calls
`storage/db.py:48-52` (`init_db`, plain `Base.metadata.create_all`). It never imports or calls
`storage/migrate.py`'s `upgrade`/`preflight`, and never reads `AUTO_MIGRATE`. The only place that
does is `evaluation/migrations.py::bootstrap()`, which is imported/called exclusively from CLIs
(`research_cli.py`, `evaluation/cli.py`, `alerts/cli.py`, `opportunity/cli.py`,
`ingest/microstructure_cli.py`) — never from `api/app.py`.

Reproduced: built a prior `research_entries` table (missing `momentum_direction` and 16 other
columns, matching the exact historical failure), ran `init_db()` (what `init_storage()` actually
calls) against it, then checked the schema:

```
schema current after web-app-style init_storage()/init_db()? False
missing_columns: ['research_entries.rank', ... 'momentum_direction', 'orderbook_direction',
'tradeflow_direction', ... 'expected_close', 'time_remaining_hours']
```

`docs/database-migration-guide.md:26-27` claims "the CLIs **and startup** call `upgrade`
automatically" and `docs/production-migration-runbook.md:22-27` calls startup auto-migrate
"belt-and-suspenders" protection "even if the release step is skipped." Neither is true for the
FastAPI process. If the release/pre-deploy `migrate_cli upgrade` step is ever skipped or races the
web tier's own deploy, and a collector CLI hasn't run yet, the web server will boot against a stale
schema and any endpoint touching a new column (e.g. `/api/research/status`) 500s until a collector
cron happens to run `bootstrap()`.

**Fix**: call `evaluation.migrations.bootstrap(engine)` (or `storage.migrate.preflight`) from
`api/deps.py::init_storage()` instead of (or in addition to) bare `init_db()`, so the web tier gets
the same ALTER-COLUMN + AUTO_MIGRATE-gated behavior as every CLI. Also reconcile the two
independently-maintained "import every model module" lists (see MAJOR-4).

## CRITICAL-2 — `repair_incomplete()` can delete a valid, frozen, complete cohort

`backend/astrolabe/evaluation/research_repository.py:308-321` (`repair_incomplete`) takes a
snapshot via `incomplete_cohorts()` (lines 228-246), decides `not row["frozen"]` from that stale
snapshot, then calls `delete_cohort(row["id"])` (lines 248-258). `delete_cohort` performs no
re-check of `frozen` at delete time — it unconditionally deletes entries, forward rows and the
cohort by id.

If a legitimate freeze retry (`freeze_from_inputs`) completes and commits the *same* previously
"incomplete" cohort between the snapshot read and the delete, `repair_incomplete` deletes it anyway
— destroying real, frozen, complete evidence. Reproduced end-to-end:

```
incomplete snapshot: [{'id': 1, ... 'frozen': False, 'universe_size': 0, 'entries': 0, ...}]
concurrent freeze result: {..., 'frozen': True, 'already_frozen': False, 'universe_size': 1, ...}
cohorts remaining after repair: 0 []
```

The cohort was fully frozen with 1 real entry immediately before `delete_cohort` ran, and is gone
afterward. This directly contradicts the documented guarantee ("frozen evidence is immutable...
valid frozen cohorts are never included, so a repair can act only on genuinely broken rows").

**Fix**: make the delete conditional and atomic on current state, not the stale snapshot — either
(a) re-`session.get(ResearchCohortRow, id)` immediately before deleting and abort/skip if
`cohort.frozen` is now `True`, or (b) better, issue a single `DELETE ... WHERE id = :id AND frozen
= false` and check the affected row count, so a concurrently-completed freeze can never lose the
race. Combine with a `SELECT ... FOR UPDATE` (or equivalent) if repair and freeze can genuinely run
as separate concurrent processes against Postgres in production.

## CRITICAL-3 — concurrent `upgrade()` during an actual migration crashes (unhandled), both dialects

`backend/astrolabe/storage/migrate.py:127-139` (`_upgrade_sync`): `create_all` and the per-column
`ALTER TABLE ADD COLUMN` loop are check-then-act with no existence guard at the SQL level (no `IF
NOT EXISTS` for tables/columns) and no advisory lock. Reproduced two engines calling `upgrade()`
concurrently against the *same* behind-schema SQLite DB:

```
OperationalError: table markets already exists
[SQL: CREATE TABLE markets ( ... )]
```

(the other coroutine's `upgrade()` succeeded, `from_version: 0, to_version: 3`). On Postgres this
manifests as `DuplicateTable`/`DuplicateColumn` and aborts the whole transaction. Once the schema is
already current, concurrent `upgrade()` calls are safe (confirmed empty-diff no-op), so the danger
window is specifically the moment of an actual version bump — i.e. exactly when multiple new-version
instances/replicas or overlapping cron collector jobs are most likely to boot simultaneously against
the same DB, which is the default `AUTO_MIGRATE=true` startup path documented as the norm.
`_ensure_version_table`'s `CREATE TABLE IF NOT EXISTS` (migrate.py:59-65) is comparatively safer but
does not protect the `create_all`/`ADD COLUMN` steps that run before it on each connection.

**Fix**: wrap `_upgrade_sync` in a Postgres advisory lock (`pg_advisory_xact_lock`) keyed on a fixed
id, held for the duration of the transaction, so only one migrator proceeds at a time; SQLite can
serialize via `BEGIN IMMEDIATE` or a filesystem lock. At minimum, catch
`DuplicateTable`/`DuplicateColumn`/`OperationalError("already exists")` in `upgrade()` and treat as
"another migrator won, re-check" rather than letting it crash the caller.

## MAJOR-4 — two different, both-incomplete "import every model" lists

`storage/migrate.py:30-44` (`_load_all_models`) imports accounts, evaluation.models,
evaluation.research_models, ingest.microstructure_store, opportunity.snapshot_models, storage.models
— but **not** `astrolabe.alerts.models` (`alert_history` table).
`api/deps.py:36-49` (`init_storage`) imports accounts, **alerts**, evaluation.models,
ingest.microstructure_store, opportunity.snapshot_models — but **not** `evaluation.research_models`
or `storage.models` (cache).

Neither list is the authoritative "every ORM module" the `_load_all_models` docstring promises. In
the CLI path (which is the one that actually calls `upgrade`), `alert_history` gaining a column in
the future would be silently skipped by the migrator unless something else in that process's import
graph happens to pull in `alerts.models` first (fragile, call-order-dependent — exactly what the
docstring says this function exists to prevent).

**Fix**: define the "all model modules" import list exactly once (e.g. in `storage/migrate.py`) and
have `api/deps.py::init_storage()` reuse it (or better, call `bootstrap()`/`upgrade()` directly per
CRITICAL-1, which already imports the correct set).

## MAJOR-5 — `_add_column_sql` silently drops callable defaults, contradicting its own documented guarantee

`backend/astrolabe/storage/migrate.py:100-124`, specifically the `elif col.default is not None and
getattr(col.default, "is_scalar", False)` branch (117-120): only *scalar* Python-side defaults get a
`DEFAULT` clause. Any column declared with a **callable** default — `default=list`, `default=dict`,
`default=utcnow`, `default=uuid4` — gets no `DEFAULT` clause at all, so legacy rows read back as
`NULL` from the ORM even though the column is `nullable=False` with a declared default. Confirmed:

```
SQLITE: ALTER TABLE research_entries ADD COLUMN evidence_families JSON
default: CallableColumnDefault(<function list at ...>) is_scalar: False
```

This pattern is common in this codebase today: `markets.tags`/`outcomes`, `opportunity_entries.
families`/`tags`, `research_entries.evidence_families`/`component_scores`/
`component_availability`/`intended_horizons`, `research_revisions.detail`,
`signal_snapshots`/`cohort_entries.component_scores`, plus `default=utcnow` timestamp columns and
`users.id` (`default=uuid4`). Both `storage/migrate.py`'s own docstring ("adds old-row columns as
nullable / with the column's declared default") and `docs/database-migration-guide.md:14-16` ("Old
rows receive NULL ... or the column's declared default") are literally false for this whole class of
column. Not currently exploited by any read path (the one existing consumer,
`research_service.py:42`, already guards with `or ()`), but it is a landmine for the next additive
JSON/list-default column — a future `for x in row.tags` or `row.component_availability.get(...)`
on a legacy row would raise `TypeError`/`AttributeError` in production, not at migration time.

**Fix**: evaluate callable defaults (`col.default.arg()` when not scalar, guarding for
context-taking defaults) and render a literal `DEFAULT` from the result, or explicitly document this
as an accepted exception and remove the incorrect "declared default" language from both the
docstring and the guide.

## MODERATE-6 — concurrent freeze race: no duplicate cohort, but an unhandled crash for the loser

`research_repository.py:87-104` (`get_or_create_cohort`) + `research_engine.py:290-296`: two
concurrent `freeze_from_inputs` calls for the same `(cadence, cutoff_at)` never produce a duplicate
cohort — the unique constraint holds. Reproduced with `asyncio.gather` on two sessions: one run
freezes cleanly, the other raises `sqlite3.IntegrityError: UNIQUE constraint failed:
research_cohorts.cadence, research_cohorts.cutoff_at` uncaught, propagating out of
`freeze_from_inputs` (this happens before the `try/except` that wraps entry insertion, so it isn't
caught by the atomicity fix either — though no partial data is left behind since flush-without-commit
rolls back with the session). Final state: exactly one cohort, correctly frozen — so this is not a
correctness bug, but it means an overlapping cron run or a manual re-run racing the scheduled job
crashes ungracefully instead of detecting "already frozen" and exiting 0.

**Fix**: catch `IntegrityError` around `get_or_create_cohort`, rollback, and re-`get_cohort` (the
winner's committed row will now be visible) before proceeding, so a race degrades to the normal
already-frozen no-op path instead of a stack trace.

## Confirmed safe (no fix needed)

- Forward observations cannot be recorded before their horizon elapses (`research_tracking.py:89-90`
  `if now < target: continue`) and cannot be backfilled predating the freeze (`:78-88`, causal guard
  vs. `frozen_at`) — both by inspection and consistent with the existing degradation/atomicity tests.
- `freeze_from_inputs` atomicity: a mid-freeze exception leaves **zero** visible cohort or entries
  (single commit at the end, explicit rollback on error) — confirmed by the existing
  `test_research_atomicity.py` tests, which pass.
- Universe-degradation rejection (`assess_universe`) creates **no cohort row at all** on reject —
  the decision is computed before `get_or_create_cohort` is ever called.
- `/api/research/status` and the edge verdict (`research_service.py`) only read
  `list_cohorts(provenance="prospective", frozen=True)` — never-frozen/incomplete cohorts are
  excluded by construction from every stat except the `incomplete_cohorts` monitoring counter itself.
  (Frozen-but-mismatched "anomaly" cohorts, which `repair_incomplete` correctly never deletes, would
  still contribute to these numbers if one ever existed — none currently do per the tests — worth a
  future look but not exercised here.)
- No secret/credential exposure found in migrate.py/migrate_cli.py/migrations.py error paths or logs.
- Postgres DDL for all model modules compiles cleanly (`ddl_preview`); no SQLite-only construct
  (`AUTOINCREMENT`) leaks into the Postgres dialect output; all research/account/eval column types
  used are portable (`String`, `Integer`, `Float`, `Boolean`, `JSON`, `DateTime(timezone=True)`).

## Test run

```
cd backend && python -m pytest tests/unit/test_migration.py tests/unit/test_research_atomicity.py \
  tests/unit/test_research_degradation.py -q
12 passed
```

All 12 pass — none of them exercise CRITICAL-1, CRITICAL-2, CRITICAL-3, MAJOR-4 or MAJOR-5; those
were only found by reading `api/app.py`/`api/deps.py` end-to-end and by writing adversarial
concurrency/ordering repros outside the existing suite.
