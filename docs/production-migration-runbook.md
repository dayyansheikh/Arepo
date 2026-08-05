# Production migration runbook

Migrations run against PostgreSQL as an explicit step that does not depend on the web server being
awake. Two supported patterns:

## A. Release / pre-deploy command (recommended)

Configure the platform's release phase to run the migrator before the new web version serves
traffic and before any collector job runs:

```
python -m astrolabe.storage.migrate_cli upgrade
```

- Runs against `DATABASE_URL` (the Supabase transaction-pooler URL, asyncpg form).
- Idempotent: safe if the deploy is retried.
- Exit code 0 on success; non-zero if the migration fails (halt the deploy).

On Render this is a `preDeployCommand`; on Cloud Run it is a one-off `Job` run before promoting the
service (see `render.yaml` / `docs/FINAL_SCHEDULED_JOBS.md`).

## B. Startup auto-migrate (default, belt-and-suspenders)

With `AUTO_MIGRATE=true` (default) every CLI and the app bootstrap run `upgrade` on start, so even
if the release step is skipped, the first collector job brings the schema current before any cohort
work. Set `AUTO_MIGRATE=false` to disable this and rely solely on pattern A; the bootstrap then runs
`preflight` and any job aborts with an actionable message if the schema is behind.

## First deploy

1. Create the Supabase project and obtain the pooler `DATABASE_URL`.
2. Run `migrate_cli upgrade` (release command or a one-off shell) → expect
   `{"from_version": 0, "to_version": N, "columns_added": [...]}` (a fresh DB creates all tables).
3. Run `migrate_cli check` → expect `"current": true`.
4. Proceed to the first collector sequence (`docs/USER_DEPLOYMENT_CHECKLIST.md`).

## Verifying

- `python -m astrolabe.storage.migrate_cli check` prints `schema_version`, `expected_version`,
  `missing_columns`, `missing_tables`. Non-zero exit if behind.
- `scripts/check_research_health.sh` calls it as part of the health check.

## Rollback

The migration is additive only: it never drops a table or column, so a rollback of application code
does not require a schema rollback (extra columns are simply unused by older code). If a deploy must
be reverted, revert the code and leave the schema; no data is lost. Never hand-drop research tables
or columns that hold frozen prospective evidence.
