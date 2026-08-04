# Final production architecture (spec §15)

A single, coherent production architecture. There is **one** authentication system (native
FastAPI Users in Postgres); Supabase is used **only** as the managed Postgres database, not for
auth. No competing auth configuration exists in the code.

## Components
| Concern | Choice | Notes |
| --- | --- | --- |
| Frontend host | **Vercel** (Next.js 14 app router) | `vercel.json`; Root Directory `frontend` |
| Backend host | **Render** (FastAPI + Uvicorn) | `render.yaml` web service, health `/health` |
| Scheduler | **Render cron jobs** | 7 UTC crons in `render.yaml` |
| Production database | **Supabase Postgres** | schema is Postgres-compatible; SQLite is dev-only |
| Authentication | **Native FastAPI Users**, stored in Postgres | argon2 hashing, JWT in a secure cookie |
| Email | **Resend** | verification, reset, research alerts via the provider-neutral engine |
| Persistent storage | Postgres (users, prefs, saved markets, alerts, cohorts, snapshots) | idempotent bootstrap |

Native auth was kept deliberately (spec §15, DECISIONS P3): it needs one datastore, runs offline
for local dev, and delegates all password/crypto to vetted libraries. **Supabase Auth is not
used** and must not be added alongside it.

## Authentication implementation
- `fastapi-users` (SQLAlchemy adapter). Endpoints under `/api/auth/*` and `/api/users/me`.
- Password hashing: argon2 (`pwdlib`). Sessions: JWT in a secure, httpOnly cookie.
- Flows: sign-up, email verification (required before login), sign-in, sign-out, current-user,
  password reset, preferences, saved markets, account deletion, expired/invalid session handling.
- Per-user data isolation enforced in the data-access layer; per-IP rate limiter on auth endpoints.

## Environment variables
| Variable | Where | Public/Secret | Purpose |
| --- | --- | --- | --- |
| `AUTH_SECRET` | Render | **secret** | JWT signing (>= 32 bytes) |
| `DATABASE_URL` | Render | **secret** | Supabase Postgres (transaction pooler URL) |
| `APP_BASE_URL` | Render | public | Frontend origin; builds verification/reset links |
| `CORS_ORIGINS` | Render | public | Explicit allow-list of frontend origins |
| `AUTH_COOKIE_SECURE` | Render | public | `true` in production |
| `ALERT_EMAIL_ENABLED` | Render | public | master switch for external email |
| `ALERT_PROVIDER` | Render | public | `resend` in production |
| `ALERT_SENDER` | Render | public | a **verified** Resend sender |
| `RESEND_API_KEY` | Render | **secret** | Resend API key |
| `NEXT_PUBLIC_API_BASE` | Vercel | public | the Render backend URL (Preview + Production) |

No secret is committed. `backend/.env.example` documents every variable.

## Cookie strategy, CORS, redirects, verification/reset links
- **Cookie:** JWT in an httpOnly cookie, `SameSite=lax`, `Secure` in production. If the frontend
  and backend are on **different registrable domains**, set `SameSite=none; Secure` (the code
  defaults to `lax`, which works when the frontend proxies the API under the same site). The
  simplest robust setup serves the API under the apex domain (`api.arepo.app` + `arepo.app`) so
  `lax` suffices.
- **CORS:** an explicit allow-list (`CORS_ORIGINS`); credentials are enabled, so `*` is never used.
- **Redirects / links:** verification (`/verify?token=`) and password-reset (`/reset?token=`) links
  are built from `APP_BASE_URL` and point at the frontend, which calls the backend to complete the
  action. In local dev the console email sink logs the links.

## Database connection mode
Use the Supabase **transaction pooler** (port 6543, `?pgbouncer=true`) for the Render web runtime
(many short-lived connections), and the **direct** connection (5432) only for one-off DDL/migration
runs. `postgresql+asyncpg://…` (asyncpg is a runtime dependency). Migrations are idempotent
(`init_db`/`create_all` at startup and in each cron's bootstrap); indexes are declared on the hot
columns (user id, market id, timestamps, `minute_bucket`).

## Scheduler (Render cron, UTC)
microstructure snapshots (5 min), Opportunity snapshot (daily 00:10), cohort rank (hourly),
weekly freeze (Sun 23:59), forward prices (hourly), resolutions (6h), user alerts (hourly). All
idempotent; none depends on a browser or a developer's laptop.

## Dead configuration
None to delete: there is no second auth system, and `docker-compose.yml`/`Dockerfile` remain valid
for local/self-hosting. The only "Supabase" mentions in code are doc comments explaining why native
auth is used instead of Supabase Auth.
