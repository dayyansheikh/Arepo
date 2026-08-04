# Deployment

## Status of this document

**Docker startup and public deployment were not executed in the build environment.** The
machine used to build Astrolabe had no Docker daemon and no `gh`/`vercel` CLI or authenticated
hosting account available. The Dockerfiles, `docker-compose.yml`, and the guidance below are
authored to specification and validated by inspection (reviewed line-by-line against the
actual `Settings`/`.env.example`/package files), but `docker compose up` and any live hosting
push have **not** been run. The operator running this project must execute those steps and
verify them independently. No live URL is claimed anywhere in this repository's docs.

What **was** verified in the build environment: the non-Docker local path (`uvicorn` +
`next dev`), described in `README.md`.

---

## Environment variables (backend)

Source of truth: `backend/.env.example` and `backend/astrolabe/config.py` (`Settings`, loaded
via `pydantic-settings` from environment variables / a `.env` file; every field has a
sensible default, none are required).

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` \| `production` |
| `LOG_LEVEL` | `INFO` | Standard Python logging level names |
| `LOG_JSON` | `false` | `true` emits single-line structured JSON logs (recommended in production) |
| `GAMMA_BASE_URL` | `https://gamma-api.polymarket.com` | Public, read-only, no credentials |
| `CLOB_BASE_URL` | `https://clob.polymarket.com` | Public, read-only, no credentials |
| `CLOB_WS_URL` | `wss://ws-subscriptions-clob.polymarket.com/ws/market` | Public market channel |
| `HTTP_TIMEOUT_SECONDS` | `10` | Per-request timeout for Gamma/CLOB REST clients |
| `WS_STALE_SECONDS` | `30` | No message for this long ⇒ treat the WS session as stale and reconnect |
| `WS_PING_INTERVAL_SECONDS` | `10` | Client sends the plain-text frame `PING` on this interval |
| `STALE_AFTER_SECONDS` | `60` | Data older than this is flagged stale in the quality model |
| `DEFAULT_MODE` | `live` | `live` \| `cached` \| `replay` – used when a request omits `?mode=` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./astrolabe.db` | See "Database configuration" below |
| `API_HOST` | `0.0.0.0` | Bind address for uvicorn |
| `API_PORT` | `8000` | Bind port for uvicorn |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed origins |
| `DISCOVERY_LIMIT` | `60` | Max markets/events fetched per discovery call (politeness to public APIs) |
| `POLL_INTERVAL_SECONDS` | `15` | Interval for the standalone ingestion pipeline's poll loop |

Not shown but present in `Settings`: `app_name`, `http_max_retries`, `http_user_agent`,
`ws_reconnect_base_seconds`, `ws_reconnect_max_seconds` – all have working defaults and rarely
need overriding.

No API key, wallet, or private key is ever required – Astrolabe only calls Polymarket's
public, unauthenticated read endpoints.

## Environment variables (frontend)

Source of truth: `frontend/.env.example`.

| Variable | Default | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | Base URL the **browser** calls directly; baked into the client bundle at build time (Next.js `NEXT_PUBLIC_*` convention) |

Because this value is baked in at build time, changing it after building the frontend
requires a rebuild (`npm run build` or rebuilding the Docker image with a different
`--build-arg NEXT_PUBLIC_API_BASE=...`).

## CORS

`api/app.py` configures `CORSMiddleware` with:

- `allow_origins` = `Settings.cors_origin_list` (parsed from `CORS_ORIGINS`, comma-separated)
- `allow_credentials = False`
- `allow_methods = ["GET", "OPTIONS"]`
- `allow_headers = ["*"]`

Set `CORS_ORIGINS` to the frontend's actual deployed origin(s) in production (e.g.
`https://astrolabe.example.com`); the default `http://localhost:3000` only works for local
development.

## Health checks

- **Backend liveness:** `GET /health` – returns `{"status": "ok", "app", "environment",
  "time"}`. Both `backend/Dockerfile` (`HEALTHCHECK`) and `docker-compose.yml`
  (`healthcheck:`) poll this endpoint every 30s with a 5s timeout and 3 retries; the frontend
  service in compose has `depends_on: backend: condition: service_healthy`, so it won't start
  until the backend reports healthy.
- **Data-mode health:** `GET /api/status` – reports the currently resolved mode plus REST and
  WebSocket `SourceHealth` (state, last success, last error). Useful as an operational signal
  distinct from process liveness.

## Database configuration

Default: **SQLite** via `aiosqlite`, `DATABASE_URL=sqlite+aiosqlite:///./astrolabe.db`
(a file-based DB local to the backend process; the Docker Compose file mounts this on a named
volume, `astrolabe_data`, at `/data`). No setup is required – `storage/db.py` creates all
tables idempotently on startup (`init_db`, called from the FastAPI `lifespan` hook).

**Postgres** (for a real deployment): set

```
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/<database>
```

and **install the `asyncpg` driver**, which is **not** in `backend/requirements.txt` by
default (the default requirements target the SQLite/`aiosqlite` path only):

```bash
pip install asyncpg
```

`storage/models.py` uses only portable SQLAlchemy column types (`JSON`, `DateTime(timezone=
True)`, `Float`, `String`, `Boolean` – no SQLite-only types), so the same schema works
against Postgres without modification once the driver is installed and the URL is set.

If storage/cache initialization fails for any reason (bad URL, unreachable DB, missing
driver), the backend does **not** crash – `api/deps.py` catches the exception, logs a
warning, and the service simply serves `live`/`replay` with `cached` mode reported as
unavailable (`CachedSource.available() == False`).

## Build / start commands

### Backend (Python host – e.g. Render, Railway, Fly.io, a VM)

```bash
cd backend
pip install -r requirements.txt
# For Postgres in production, also: pip install asyncpg
uvicorn astrolabe.api.app:app --host 0.0.0.0 --port 8000
```

Or via the provided Dockerfile (`backend/Dockerfile`): builds a `python:3.11-slim` image,
installs `requirements.txt`, copies the `astrolabe` package, runs as a non-root user (`astro`,
uid 10001), exposes `8000`, and starts with the same `uvicorn` command above.

### Frontend (Vercel or any Node host)

```bash
cd frontend
npm install
npm run build
npm start
```

Set `NEXT_PUBLIC_API_BASE` to the deployed backend's public URL **before** `npm run build`
(Vercel: set it as a project environment variable so it's present at build time). The
provided `frontend/Dockerfile` builds with `next build` (`node:20-slim`, multi-stage,
non-root `astro` user) and starts with `npm start` on port `3000`; it accepts
`NEXT_PUBLIC_API_BASE` as both a build `ARG` and a runtime `ENV`.

### One-command local stack

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:3000`, `NEXT_PUBLIC_API_BASE` wired to
`http://localhost:8000` for both the frontend build and its runtime environment. As stated
above, this command has not been executed in the build environment – it is provided
ready-to-run for the operator.

## WebSocket constraints

The CLOB market-channel WebSocket client (`clients/clob_ws.py`) implements the confirmed wire
protocol from `docs/research-notes.md`:

- Connects to `wss://ws-subscriptions-clob.polymarket.com/ws/market` and subscribes with
  `{"assets_ids": [...], "type": "market"}` on open.
- Sends the plain-text frame `"PING"` every `WS_PING_INTERVAL_SECONDS` (default 10s); the
  server replies `"PONG"`.
- If no message arrives within `WS_STALE_SECONDS` (default 30s), the session is treated as
  stale and the client reconnects with bounded exponential backoff
  (`ws_reconnect_base_seconds` → `ws_reconnect_max_seconds`, default 1s → 30s).
- After `degraded_after_failures` (default 5) consecutive connect/session failures, the
  client's state becomes `DEGRADED` and an `on_degraded` callback fires once, so a caller can
  fall back to REST polling – **the WS client itself never calls REST**; it only reports its
  own connection state.
- Duplicate `book`/`price_change`/`last_trade_price` events are deduped via a bounded LRU set
  keyed on event type + asset id + hash + timestamp.

In the current API surface, live-mode order books are read via **CLOB REST**
(`GET /book`) at request time rather than a live WS-fed cache; the WebSocket client exists,
is unit-tested, and is intended for a longer-running ingestion/streaming process (see
`ingest/pipeline.py` and the `run_forever` polling loop) rather than being wired directly into
the request path of every `/api/*` call in this build.

## Scheduler (weekly cohort evaluation)

The prospective cohort evaluation system (`docs/methodology.md` §12) is driven entirely by
idempotent CLI commands, not by any request made through a browser:

```bash
cd backend && source .venv/bin/activate
python -m astrolabe.evaluation.cli bootstrap        # create/verify the evaluation tables
python -m astrolabe.evaluation.cli rank              # update this week's provisional top ten
python -m astrolabe.evaluation.cli freeze            # freeze the current week's cohort at cut-off
python -m astrolabe.evaluation.cli forward            # collect any due forward prices
python -m astrolabe.evaluation.cli resolve            # record newly-available resolutions
python -m astrolabe.evaluation.cli evaluate           # recompute the two evaluation views + portfolio
python -m astrolabe.evaluation.cli seed-synthetic     # build the labelled synthetic demo cohort
python -m astrolabe.evaluation.cli status              # print recorded cohort weeks
```

Every command is safe to run repeatedly: `rank` converges to the same selection given the same
inputs, `freeze` is a no-op once a cohort is already frozen, `forward` observations are unique
per `(entry, horizon)`, and `resolve`/`evaluate` upsert rather than duplicate. This is what
makes the workflow scheduler-friendly: none of it needs the browser to stay open, and any of
the standard options works:

- a hosting provider's own scheduled-job feature (e.g. Render Cron Jobs, Railway Cron),
- **GitHub Actions**, using a scheduled workflow that checks out the repository and runs the
  CLI against the deployed `DATABASE_URL`, or
- a plain **cron** entry on a VM that already runs the backend.

An example GitHub Actions workflow (`.github/workflows/cohort-schedule.yml`), ranking hourly,
freezing at the Sunday UTC cut-off, and running forward/resolve/evaluate daily:

```yaml
name: cohort-schedule
on:
  schedule:
    - cron: "0 * * * *"        # rank: hourly
    - cron: "59 23 * * 0"      # freeze: Sunday 23:59 UTC
    - cron: "30 0 * * *"       # forward + resolve + evaluate: daily
  workflow_dispatch: {}
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - name: rank
        working-directory: backend
        run: python -m astrolabe.evaluation.cli rank
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
      - name: freeze
        working-directory: backend
        run: python -m astrolabe.evaluation.cli freeze
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
      - name: forward-resolve-evaluate
        working-directory: backend
        run: |
          python -m astrolabe.evaluation.cli forward
          python -m astrolabe.evaluation.cli resolve
          python -m astrolabe.evaluation.cli evaluate
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

A single workflow file with three cron triggers cannot itself select which job body runs for
which trigger, so a real deployment should either split this into three workflow files (one
per cadence) or gate each step on `github.event.schedule`. The snippet above is illustrative
of the commands and cadence, not a drop-in file: an operator wiring this up should adapt it to
their actual hosting/database setup.

**No paid or public external scheduler has been activated for this project.** GitHub Actions,
a hosting-provider scheduler, or cron are all viable and the commands above work with any of
them, but activating one requires the user's own repository/hosting account and explicit
approval; nothing here has been switched on.

The database is selected by the standard `DATABASE_URL` environment variable (see
"Environment variables (backend)" above), defaulting to local SQLite
(`sqlite+aiosqlite:///./astrolabe.db`). The scheduler and the API server must point at the
same database for the Replay page to see what the scheduler produced.

## Fallback behaviour in production

Regardless of hosting, the mode-fallback chain described in `docs/architecture.md` applies:
`live` requests fall back to `cached` (if a populated cache exists) and finally to `replay`
(always available, bundled in the image). Operators should run the standalone ingestion
script (`python backend/scripts/ingest.py` for one cycle, or `python backend/scripts/
ingest.py --loop` to poll continuously on `POLL_INTERVAL_SECONDS`) on a schedule if they want
a meaningful `cached` fallback tier in production; without it, `cached` mode will report
`available() == False` and any fallback skips straight to `replay`.

---

# Production deployment: Vercel + Render + Supabase + Resend (spec §16-20)

This is the production architecture selected in the spec. All application code and configuration
is in the repo; the steps that require **creating an external account or setting a secret** are
called out and must be done by the user. No secret is committed.

## Architecture

| Concern | Service | Why |
|---|---|---|
| Next.js frontend | **Vercel** | First-class Next.js hosting, Preview + Production envs |
| FastAPI backend + cron | **Render** | Long-running ASGI service and native scheduled jobs (`render.yaml`) |
| Postgres | **Supabase** | Managed Postgres; the schema is already Postgres-compatible |
| Email | **Resend** | Verification, reset and alert email via the provider-neutral engine |

Native authentication (`fastapi-users`) is kept (spec §16): there is no reason to replace it, and
it runs identically on Postgres.

## 1. Database: Supabase Postgres (§17)

- Create a Supabase project (**user action**). Copy the connection string.
- Use the **transaction pooler** connection URL for the backend web runtime (port 6543,
  `?pgbouncer=true`). Rationale: Render web dynos open many short-lived connections, and Supabase's
  transaction pooler is designed for exactly that, avoiding exhausting the direct-connection limit.
  Use the **direct** connection (port 5432) only for one-off migration/DDL runs. Set it as
  `DATABASE_URL` on Render (format `postgresql+asyncpg://...`). SQLAlchemy async + asyncpg is used.
- Migrations: table creation is idempotent (`init_db` / `create_all`, run at startup and by each
  cron's `bootstrap`). Indexes are declared on the hot columns (user id, market id, timestamps,
  `minute_bucket`). For a managed migration step, run
  `python -c "import asyncio; from astrolabe.storage.db import make_engine, init_db; from astrolabe.api import deps; asyncio.run(init_db(make_engine()))"`
  against the direct URL before first boot.

## 2. Backend: Render (§20)

`render.yaml` (repo root) provisions the `arepo-api` web service and the UTC cron jobs. Key
settings: `rootDir: backend`, build `pip install -r requirements.txt && pip install -e .`, start
`uvicorn astrolabe.api.app:app --host 0.0.0.0 --port $PORT`, health check `/health`.

Set these in the Render dashboard (marked `sync:false`, **user action**): `AUTH_SECRET` (strong,
`python -c "import secrets; print(secrets.token_urlsafe(48))"`), `DATABASE_URL` (Supabase pooler),
`APP_BASE_URL` (the Vercel URL), `CORS_ORIGINS` (the Vercel origins), `ALERT_EMAIL_ENABLED`,
`ALERT_SENDER`, `RESEND_API_KEY`. `ENVIRONMENT=production` and `AUTH_COOKIE_SECURE=true` are set
in the blueprint. The app logs a warning if `AUTH_SECRET` is left at its dev default in production.

## 3. Frontend: Vercel (§20)

- Import the repo in Vercel (**user action**) and set the project **Root Directory to `frontend`**
  (Vercel reads this from the dashboard, not `vercel.json`). `vercel.json` pins the Next.js
  framework and build.
- Env vars: `NEXT_PUBLIC_API_BASE` = the Render backend URL (e.g. `https://arepo-api.onrender.com`)
  for **both** Preview and Production. There are no `localhost` references in shipped code (the API
  base falls back to localhost only when the variable is unset, for local dev).

## 4. Cross-origin cookies (§17)

Frontend (`*.vercel.app`) and backend (`*.onrender.com`) are different sites, so the auth cookie
must be `SameSite=None; Secure` in production for the browser to send it cross-site. Set
`AUTH_COOKIE_SECURE=true` (done in `render.yaml`); if you keep the two on different registrable
domains, also set the cookie `SameSite=none` (the code uses `lax` by default, which works when the
frontend proxies the API under the same site). The simplest robust setup is to serve the API under
the same apex domain (e.g. `api.arepo.app` + `arepo.app`) so `SameSite=lax` suffices. CORS is an
explicit allow-list (`CORS_ORIGINS`); credentials are enabled, so `*` is never used.

## 5. Email: Resend (§18)

`ALERT_PROVIDER=resend` selects `ResendProvider` (HTTPS `api.resend.com/emails`, plain-text with an
HTML fallback, retries + failure logging via the alert service). Set `RESEND_API_KEY` and a
verified `ALERT_SENDER`. **Sending to arbitrary registered users requires a verified custom
domain** in Resend; the test sender is limited to the account owner's own address. Verification and
password-reset email flow through the same engine, so once Resend is configured the whole account
lifecycle sends real mail; until then the console sink logs the links (local dev).

## 6. Scheduled jobs (§19)

All defined in `render.yaml` as UTC crons, all idempotent, none dependent on any browser or a
developer's laptop:

| Job | Schedule (UTC) | Command |
|---|---|---|
| Microstructure snapshots (§7) | every 5 min | `python -m astrolabe.ingest.microstructure_cli collect --mode live` |
| Opportunity snapshot | 00:10 daily | `python -m astrolabe.opportunity.cli snapshot --mode live` |
| Cohort ranking | hourly | `python -m astrolabe.evaluation.cli rank --mode live` |
| Weekly cohort freeze | Sun 23:59 | `python -m astrolabe.evaluation.cli freeze` |
| Forward prices | hourly | `python -m astrolabe.evaluation.cli forward` |
| Resolutions | every 6h | `python -m astrolabe.evaluation.cli resolve` |
| Alert evaluation | hourly | `python -m astrolabe.alerts.cli user-dry-run --mode live` |

The alert job is a no-op until `ALERT_EMAIL_ENABLED=true`; switch it from `user-dry-run` to a real
send command once Resend and a verified domain are in place.

## 7. Deployed end-to-end tests (§20)

After the user completes the account steps, verify **outside localhost**: public pages load;
sign-up sends a verification email (Resend); verify link works; sign-in; password reset; account
preferences persist; saved markets; the directional Opportunity Board renders with the
screened/qualify line; a market model view; filter state survives Back/refresh/shared links;
Signal Lab; Replay; an alert email (test sender); mobile layout; logout; account deletion.
Deployment is not complete until these pass.

## External setup still required (the stopping point)

1. Create the **Supabase** project and copy the pooler `DATABASE_URL`.
2. Create the **Render** account, connect the repo (`render.yaml` auto-detected), set the
   `sync:false` secrets.
3. Create the **Vercel** project, set Root Directory `frontend` and `NEXT_PUBLIC_API_BASE`.
4. Create the **Resend** account, verify a sender/domain, set `RESEND_API_KEY`.

All of these require the user's own credentials and are the point at which autonomous work stops.
