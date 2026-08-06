# Final deployment plan

Primary architecture (see `docs/final-hosting-decision.md`): **Render** (Starter web + Cron Jobs) +
**Supabase PostgreSQL** (transaction pooler) + **Vercel** frontend + custom domain `arepo.dsheikh.cc`.

## Components

| Component | Config | Command |
| --- | --- | --- |
| Database | Supabase Postgres, transaction pooler (6543) | migrator: `python -m astrolabe.storage.migrate_cli upgrade` |
| API | Render web (`render.yaml` service `arepo-api`, rootDir `backend`) | build `pip install -r requirements.txt && pip install -e .`; **release** `migrate_cli upgrade`; start `uvicorn astrolabe.api.app:app --host 0.0.0.0 --port $PORT` |
| Health | `/health` (Render healthCheckPath) | — |
| Research status | `/api/research/status` | — |
| Crons | 11 Render Cron Jobs | see `docs/FINAL_SCHEDULED_JOBS.md` |
| Frontend | Vercel, rootDir `frontend`, `NEXT_PUBLIC_API_BASE` | `next build` |

## Order of operations

1. Migrate/merge to `main`, tag `arepo-edge-research-live`.
2. Create Supabase project; get the pooler `DATABASE_URL`.
3. Deploy the Render blueprint (`render.yaml`); the **release command migrates the schema** before
   the API serves traffic.
4. Enter environment variables (`docs/FINAL_ENVIRONMENT_VARIABLES.md`) in a shared Environment Group.
5. Verify: `scripts/verify_production.sh` (health, status, synthetic exclusion).
6. Enable the cron jobs; run the first freeze manually at a 6h boundary.
7. Deploy the frontend on Vercel; set `NEXT_PUBLIC_API_BASE`; connect the domain; update `CORS_ORIGINS`.
8. Run the production acceptance test (`docs/FINAL_PRODUCTION_ACCEPTANCE.md`).

## Guarantees

- Migrations run as an explicit release step and do not depend on the web server being awake.
- Collectors connect to the database directly; no browser is required.
- The schema is Postgres-portable (tested); indexes exist on cohort/entry/forward query columns
  (`market_id`, `cohort_id`, `entry_id`, unique keys).
- Cohort freezes are atomic; incomplete cohorts are never exposed; synthetic data is excluded.

The exact click-by-click steps for the user are in `docs/USER_DEPLOYMENT_CHECKLIST.md` and the final
report.
