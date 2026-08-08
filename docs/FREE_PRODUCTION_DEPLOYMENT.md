# Arepo — Free Production Deployment Guide

_Follow these steps **in order** after the code-preparation branch (`arepo-free-production-v1`) is
merged/deployed. Written for a non-technical owner: do exactly what each step says. Where a value must
be copied from a provider dashboard, the step says exactly where it comes from. Nothing here creates
paid resources._

**Architecture (all genuinely free):**

```
  Vercel (Next.js frontend)  ─HTTPS→  Render (FastAPI API, free)  ─→  Supabase Postgres (free)
                                                                          ▲
  GitHub Actions (scheduled tick + backup) ──── same Arepo Python code ───┘
```

- **Vercel Hobby** hosts the website and serves `arepo.dsheikh.cc`.
- **Render Free** runs the API. It only serves already-computed results; it never does the heavy scan.
- **Supabase Free Postgres** is the durable database.
- **GitHub Actions** runs the scheduled work (the "tick") and the daily backup — this replaces Render's
  **paid** cron jobs, keeping the whole system £0.
- **Resend** sends account/alert emails.

> **One important requirement:** GitHub Actions is free and unlimited only for **public** repositories.
> A private repo gets 2,000 minutes/month, which the frequent scan exceeds. So either make the repo
> public, or accept a much lower scan frequency. See the capacity audit for the numbers.

Estimated monthly cost: **£0** (see "Costs & limits" at the end). Expected safe database lifetime on
the free tier: **≈ 3–5 weeks** at the current cohort cadence before you must either lower the cadence,
enable the cold archive, or upgrade Postgres — all explained in step 12 and PRODUCTION_ROLLBACK.md.

---

## Before you start — accounts you will create

1. GitHub account (you already have the repo).
2. Supabase account — https://supabase.com
3. Render account — https://render.com
4. Vercel account — https://vercel.com
5. Resend account — https://resend.com
6. (Optional, later) Cloudflare account for R2 cold archive — only if the audit's lifetime is too short.

Sign up for each with the same email. Do **not** enter any card details; every step below stays on a
free plan.

---

## Step 1 — Create the production Postgres (Supabase)

1. Supabase → **New project**. Name it `arepo`. Choose a region near your users. Set a strong database
   password and **save it** (you will paste it into Render and GitHub, never into code).
2. Wait for the project to finish provisioning.
3. Open **Project Settings → Database → Connection string**. You need two forms:
   - **Transaction pooler** URL (host contains `pooler`, port `6543`) — for the API and the tick.
   - **Direct connection** URL (port `5432`) — for backups (pg_dump).
4. Convert each to the async driver Arepo uses by changing the scheme to `postgresql+asyncpg://`:
   - `postgresql://USER:PASSWORD@HOST:6543/postgres` → `postgresql+asyncpg://USER:PASSWORD@HOST:6543/postgres`
   - Keep the direct (`:5432`) one as plain `postgresql://…` for pg_dump (backup).
5. Keep both strings handy for the next steps. **These are secrets.**

> Supabase free projects **pause after 7 days with no requests**. Arepo's API and the every-5-minute
> tick both touch the database, so in normal operation it will not pause. If you ever pause the tick
> for over a week, resume the project from the Supabase dashboard.

## Step 2 — Deploy the API (Render)

1. Render → **New → Blueprint**, connect your GitHub, pick the Arepo repo and the branch you deploy
   from. Render reads `render.yaml` and proposes the `arepo-api` web service. (There are **no** cron
   services — that is intentional; scheduling is on GitHub Actions.)
2. When prompted for the environment variables marked "sync:false", set:
   - `DATABASE_URL` = the **transaction pooler** async URL from Step 1.4 (secret).
   - `AUTH_SECRET` = a strong random string ≥ 32 characters (generate one; secret).
   - `ADMIN_TOKEN` = a strong random string (secret; guards `/admin/health`).
   - `APP_BASE_URL` = your future frontend URL, e.g. `https://arepo.dsheikh.cc` (public).
   - `CORS_ORIGINS` = your frontend origin(s), e.g. `https://arepo.dsheikh.cc,https://arepo.vercel.app`
     (public). **Never** `*`.
   - `ALERT_EMAIL_ENABLED` = `false` for now (you enable email in Step 9).
   - `ALERT_SENDER`, `RESEND_API_KEY` = leave blank for now.
3. Deploy. The `preDeployCommand` runs the schema migration automatically before the app serves.
4. When it's live, note the API URL Render gives you, e.g. `https://arepo-api.onrender.com`.

## Step 3 — Verify the API + database

Open these in a browser (replace the host with your Render URL):

- `https://arepo-api.onrender.com/health` → should return `{"status":"ok", …}`.
- `https://arepo-api.onrender.com/admin/health` with header `X-Admin-Token: <your ADMIN_TOKEN>`
  (use a REST client, or `curl -H "X-Admin-Token: …" …/admin/health`) → returns the health snapshot
  with `"db_healthy": true`. If it returns 404, `ADMIN_TOKEN` isn't set; if 401, the token is wrong.

At this point the database is empty (no scans yet). That's expected — you import your existing data next.

## Step 4 — Migrate your existing data (SQLite → Postgres)

This copies your genuine local research database into Supabase **without changing any values**. Run it
from your Mac (it reads your local `backend/astrolabe.db` read-only).

1. In `backend/`, with your local virtualenv active, first do a **dry run** (writes nothing):
   ```
   python -m astrolabe.storage.import_sqlite \
     --source ./astrolabe.db \
     --dest "postgresql+asyncpg://USER:PASSWORD@HOST:6543/postgres" \
     --dry-run
   ```
   Read the printed table plan: it lists how many rows each table would import.
2. **Review reconciliation expectations.** You should see your real cohorts and their entry counts
   (e.g. the historical 60-entry cohort and the 1382-entry complete-scan cohort).
3. Run the **real import** (idempotent; safe to re-run). Use `--require-empty` the first time so it
   refuses if the destination unexpectedly already has data:
   ```
   python -m astrolabe.storage.import_sqlite \
     --source ./astrolabe.db \
     --dest "postgresql+asyncpg://USER:PASSWORD@HOST:6543/postgres" \
     --require-empty
   ```
4. **Check the reconciliation report** printed at the end: `"reconciliation": { "ok": true, … }` and
   every `cohort_invariants` entry `"ok": true` (each frozen cohort's `entries == universe_size`). If
   `ok` is false, **stop** — the tool exits non-zero and the destination is not trustworthy; do not
   proceed. Re-run after fixing the connection, or ask for help.

## Step 5 — Configure the GitHub Actions scheduler

1. In GitHub → the repo → **Settings → Secrets and variables → Actions → New repository secret**, add:
   - `DATABASE_URL` = the **transaction pooler** async URL (secret).
   - `AUTH_SECRET` = the same value as Render (secret).
   - `APP_BASE_URL` = your frontend URL (public-ish; still store as secret).
   - `ALERT_EMAIL_ENABLED` = `false` for now.
   - `ALERT_SENDER`, `RESEND_API_KEY` = blank for now (set in Step 9).
   - `BACKUP_DATABASE_URL` = the **direct** (`:5432`, plain `postgresql://`) URL for pg_dump (secret).
2. Make sure the repository is **public** (Settings → General → Change visibility) if you want free
   unlimited Actions minutes. If you keep it private, lower the scan frequency later.

## Step 6 — Run ONE manual tick and verify it

Do **not** enable the recurring schedule yet.

1. GitHub → **Actions → arepo-scheduler-tick → Run workflow** (manual dispatch), leave inputs blank.
2. Watch the run. The "Run scheduler tick" step prints a JSON summary; "Health snapshot" prints the
   state. A first tick will run a complete scan (this is the ~5-minute heavy job).
3. Verify:
   - The run succeeded (green).
   - `/admin/health` now shows a recent `latest_complete_scan_at` and `scheduler_jobs.refresh.last_ok = true`.
   - No duplicate/garbage cohort was created (the tick only freezes a cohort when one is causally due).

## Step 7 — Deploy the frontend (Vercel)

1. Vercel → **Add New → Project**, import the Arepo repo.
2. **Root Directory: `frontend`** (Vercel does not read this from `vercel.json` — set it in the UI).
3. Framework: Next.js (auto-detected). Build command `npm run build`, install `npm install` (defaults).
4. **Environment Variables** → add `NEXT_PUBLIC_API_BASE` = your Render API URL from Step 2.4
   (e.g. `https://arepo-api.onrender.com`) for Production (and Preview). This is **public**.
5. Deploy. Note the Vercel URL, e.g. `https://arepo.vercel.app`.

## Step 8 — Smoke-test the core pages

Open the Vercel URL and check:

- **Opportunities** (home) shows ranked signals with an honest denominator.
- **Signal Lab** shows the directional surface and filters.
- **Replay** shows the frozen cohorts and their observations.
- **Market detail** shows signal history for a market.
- **Sign in / sign up** pages load.
- On the very first load after the API has been idle, you may briefly see a restrained
  **"Connecting to Arepo data…"** message while Render wakes up; it should resolve within seconds.

If pages show a CORS error in the browser console, fix `CORS_ORIGINS` on Render (Step 2.2) to include
the exact Vercel origin, and redeploy the API.

## Step 9 — Configure email (Resend)

1. Resend → create an API key. Verify a sender domain/address you control.
2. Set on **both** Render (env vars) and GitHub Actions secrets:
   - `ALERT_PROVIDER` = `resend`
   - `ALERT_SENDER` = your verified sender, e.g. `alerts@dsheikh.cc`
   - `RESEND_API_KEY` = the key (secret)
   - `ALERT_EMAIL_ENABLED` = `true`
3. Redeploy the API. Test registration → you should receive a verification email.

## Step 10 — Connect the domain (`arepo.dsheikh.cc`)

1. Vercel → Project → **Settings → Domains → Add** `arepo.dsheikh.cc`.
2. Vercel shows the exact DNS record to add (a CNAME to Vercel). Add it at your DNS provider for
   `dsheikh.cc`. Wait for it to verify.
3. Set `APP_BASE_URL` (Render + GitHub) to `https://arepo.dsheikh.cc` and `NEXT_PUBLIC_API_BASE`
   stays the Render URL. Make sure `CORS_ORIGINS` includes `https://arepo.dsheikh.cc`. Redeploy the API.

## Step 11 — Enable the recurring schedule

Only now, after Steps 6 and 8 verified a real tick and the site:

1. The scheduler workflow already has a `schedule:` trigger (every 5 minutes). Once the workflow file
   is on your default branch, GitHub runs it automatically — no toggle needed. If you want to be
   conservative, watch the first several runs under **Actions**.
2. Verify over the next hour:
   - New complete scans appear (`latest_complete_scan_age_seconds` stays small).
   - The first **new production cohort** freezes at its cadence boundary, with `scheduled_for` vs
     `frozen_at` timing recorded (small lateness is normal and honest).
   - Its **1h** and then **6h** observations get collected on schedule.

## Step 12 — Verify storage & backup health

- `/admin/health` → `storage.level` should be `ok`. Watch it over the first weeks; when it reaches
  `warn` (80%) act using PRODUCTION_ROLLBACK.md → "Storage running out" (lower cohort cadence, enable
  the R2 cold archive, or upgrade Postgres). It will never silently hit the hard cap.
- GitHub → **Actions → arepo-db-backup** runs daily; confirm the first run succeeded and produced an
  `arepo-db-backup` artifact. This is your data backup (see PRODUCTION_ROLLBACK.md to restore).

---

## Environment variable matrix

| Variable | Frontend (Vercel) | API (Render) | Scheduler (GH Actions) | Secret? | Where it comes from |
|---|:--:|:--:|:--:|:--:|---|
| `NEXT_PUBLIC_API_BASE` | ✅ | — | — | public | Render API URL (Step 2.4) |
| `DATABASE_URL` | — | ✅ | ✅ | **secret** | Supabase pooler URL (Step 1.4) |
| `BACKUP_DATABASE_URL` | — | — | ✅ | **secret** | Supabase **direct** URL (Step 1.4) |
| `AUTH_SECRET` | — | ✅ | ✅ | **secret** | you generate (≥32 chars) |
| `ADMIN_TOKEN` | — | ✅ | — | **secret** | you generate |
| `APP_BASE_URL` | — | ✅ | ✅ | public | your frontend URL |
| `CORS_ORIGINS` | — | ✅ | — | public | your frontend origin(s) |
| `AUTH_COOKIE_SECURE` | — | ✅ (`true`) | — | public | fixed value |
| `ALERT_PROVIDER` | — | ✅ (`resend`) | ✅ | public | fixed value |
| `ALERT_SENDER` | — | ✅ | ✅ | public | your verified Resend sender |
| `RESEND_API_KEY` | — | ✅ | ✅ | **secret** | Resend dashboard (Step 9) |
| `ALERT_EMAIL_ENABLED` | — | ✅ | ✅ | public | `true`/`false` |
| `ENVIRONMENT` | — | ✅ (`production`) | ✅ (`production`) | public | fixed value |

Never commit any secret to Git. The API logs a "production config issue" warning at startup for any
weak secret, wildcard CORS, SQLite DATABASE_URL, or insecure cookie in production.

## Costs & limits (verified 2026-08-08)

- **Vercel Hobby**: free. **Render Free** web service: free (cold-starts after idle — handled by the
  "Connecting…" UI). **Supabase Free**: 500 MB DB, pauses after 7 idle days. **GitHub Actions**: free &
  unlimited for **public** repos (2,000 min/month private). **Resend**: free tier for low volume.
  **Cloudflare R2** (optional archive): 10 GB free, no egress fees.
- **Safe database lifetime** on Supabase Free ≈ **3–5 weeks** at ~5 full-universe cohort freezes/day
  (the permanent research data grows ~12 MB/day). To extend: lower cohort cadence to daily+weekly
  (~3 months), enable the R2 cold archive (effectively indefinite, lossless), or upgrade to Supabase
  Pro (8 GB, $25/mo). See `docs/PRODUCTION_CAPACITY_AUDIT.md`.

## Rollback

See `docs/PRODUCTION_ROLLBACK.md` — it separates **code rollback** (to the safety tag, which does not
touch production data) from **data recovery** (restore from a verified backup only when genuinely
required).
