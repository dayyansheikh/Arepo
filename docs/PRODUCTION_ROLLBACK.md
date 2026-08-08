# Arepo — Production Rollback & Recovery

_Two independent things that must never be conflated (master prompt §14):_

1. **Code rollback** — putting the application code back to a known-good version. This must **not**
   erase the production research data collected after deployment.
2. **Data recovery** — restoring the database from a verified backup. Only done when data is genuinely
   lost or corrupted, never as a side effect of a code rollback.

---

## 0. Known-good code version

- Safety tag: **`arepo-verified-predeploy-2026-08-08`** (the verified build immediately before this
  deployment pass). It is never moved, rewritten or deleted.
- Deployment branch: `arepo-free-production-v1`.

Confirm at any time:
```
git rev-list -n1 arepo-verified-predeploy-2026-08-08
git tag -n1 arepo-verified-predeploy-2026-08-08
```

---

## 1. Code rollback (does NOT touch production data)

Code and data are decoupled: the app is stateless; all state lives in Supabase Postgres. Rolling code
back therefore leaves every cohort, observation and account intact.

### Roll back the API (Render)
- **Fast:** Render dashboard → `arepo-api` → **Deploys** → pick the last good deploy → **Redeploy**.
- **From git:** point the Render service at the safety tag/commit, or:
  ```
  git checkout arepo-verified-predeploy-2026-08-08
  # deploy this ref (Render redeploys the connected branch/commit)
  ```
- The `preDeployCommand` runs the schema migration, which is **additive and idempotent** — an older
  app version simply ignores columns/tables it doesn't know about. Rolling **forward** again re-adds
  nothing. (If you ever roll back to a version with an *older schema*, do not run a destructive
  down-migration; the extra columns/tables are harmless.)

### Roll back the frontend (Vercel)
- Vercel dashboard → Project → **Deployments** → pick the previous deployment → **Promote to
  Production**. Instant; no data involved.

### Roll back the scheduler (GitHub Actions)
- The workflows live in git. Checking out the safety tag reverts them. If a bad tick is running,
  disable the `arepo-scheduler-tick` workflow (Actions → the workflow → **⋯ → Disable workflow**)
  until the code is fixed. Because every job is idempotent, pausing and resuming loses nothing except
  the ticks that didn't run (the next tick catches up where causally valid).

**Key guarantee:** none of the above deletes or rewrites a frozen cohort, observation, resolution or
account. Failure handling and rollback never alter frozen historical results.

---

## 2. Data recovery (only when genuinely required)

### Backups
- **What:** a daily `pg_dump` of the whole production database, gzip-compressed, integrity-checked,
  uploaded as a GitHub Actions artifact (`arepo-db-backup`, 90-day retention). Runs at 03:40 UTC.
- **Where:** GitHub → Actions → `arepo-db-backup` → the run → Artifacts. (Optionally also Cloudflare R2
  if you enable it — same dump.)
- **Cadence / verification:** daily; the workflow fails loudly if the dump is missing or suspiciously
  small, and `gzip -t` verifies the archive before upload.
- **Schema/version association:** each dump is a full snapshot including `schema_migrations` and
  `calculation_versions`, so a restored database carries its own schema + calculation-version context.

### When to restore
Only when data is genuinely lost/corrupted (e.g. an accidental mass delete, a provider incident). A
code bug is fixed by a **code rollback**, not a data restore.

### Restore procedure
1. Download the chosen `arepo-db-backup` artifact and unzip to `arepo-backup-<stamp>.sql`.
2. Create a **fresh** Supabase project (do not overwrite the live one until you've verified the
   restore). Get its **direct** (`:5432`) connection string.
3. Restore:
   ```
   gunzip -c arepo-backup-<stamp>.sql.gz | psql "postgresql://USER:PASSWORD@HOST:5432/postgres"
   ```
4. **Verify before switching traffic:**
   - Point a local checkout's `DATABASE_URL` at the restored DB and run
     `python -m astrolabe.storage.migrate_cli check` → schema current.
   - `python -m astrolabe.scheduler.tick status` → `db_healthy: true`, expected latest cohort, sane
     counts.
   - Spot-check a known cohort's `entries == universe_size`.
5. Switch `DATABASE_URL` (Render + GitHub secrets) to the restored database and redeploy the API.

### Integrity & security
- Backups contain personal data (accounts) — treat the artifacts as sensitive; GitHub artifacts are
  private to the repo. Rotate `AUTH_SECRET`/`ADMIN_TOKEN` only if a backup is exposed.
- Never commit a dump to Git.

---

## 3. Storage running out (before the free cap)

`/admin/health` → `storage.level` moves `ok → warn (80%) → critical (92%)` well before the 500 MB hard
cap, so the database never silently fills. When it reaches `warn`, choose one (all lossless for frozen
research):

1. **Lower cohort cadence** — freeze daily + weekly instead of every 6h (set
   `RESEARCH_FREEZE_CADENCES=daily,weekly`). Cuts permanent growth ~2.5×, extending lifetime to ~3
   months. Existing cohorts are untouched.
2. **Enable the cold archive** — set `ARCHIVE_BACKEND=r2` (or `local`) with credentials. The retention
   pass then archives category-C history (compressed + checksummed) **before** deleting it; an archive
   failure retains the source. Keeps Postgres small effectively indefinitely.
3. **Upgrade Postgres** — Supabase Pro (8 GB, $25/mo) for ~18 months of headroom.

Retention only ever prunes **category-C high-frequency scan history** (older than the hot window) and
**never** a scan referenced by a frozen cohort, the latest complete scan, or any permanent research /
account data. See `docs/PRODUCTION_CAPACITY_AUDIT.md` for the data-class definitions.

---

## 4. What is permanent vs recoverable-only

- **Permanent (never auto-deleted):** cohorts, cohort entries, frozen signal values/ranks, forward /
  freeze-to-close / resolution observations, evaluation results, ranking audit, calculation versions,
  accounts, alerts.
- **Rolling / prunable (category-C):** `discovery_signal_snapshots`, `microstructure_snapshots` older
  than the retention window (archived first if an archive is configured).
- **Operational (overwritten):** cache/latest-state tables.
