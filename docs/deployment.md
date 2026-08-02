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
| `DEFAULT_MODE` | `live` | `live` \| `cached` \| `replay` — used when a request omits `?mode=` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./astrolabe.db` | See "Database configuration" below |
| `API_HOST` | `0.0.0.0` | Bind address for uvicorn |
| `API_PORT` | `8000` | Bind port for uvicorn |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed origins |
| `DISCOVERY_LIMIT` | `60` | Max markets/events fetched per discovery call (politeness to public APIs) |
| `POLL_INTERVAL_SECONDS` | `15` | Interval for the standalone ingestion pipeline's poll loop |

Not shown but present in `Settings`: `app_name`, `http_max_retries`, `http_user_agent`,
`ws_reconnect_base_seconds`, `ws_reconnect_max_seconds` — all have working defaults and rarely
need overriding.

No API key, wallet, or private key is ever required — Astrolabe only calls Polymarket's
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

- **Backend liveness:** `GET /health` — returns `{"status": "ok", "app", "environment",
  "time"}`. Both `backend/Dockerfile` (`HEALTHCHECK`) and `docker-compose.yml`
  (`healthcheck:`) poll this endpoint every 30s with a 5s timeout and 3 retries; the frontend
  service in compose has `depends_on: backend: condition: service_healthy`, so it won't start
  until the backend reports healthy.
- **Data-mode health:** `GET /api/status` — reports the currently resolved mode plus REST and
  WebSocket `SourceHealth` (state, last success, last error). Useful as an operational signal
  distinct from process liveness.

## Database configuration

Default: **SQLite** via `aiosqlite`, `DATABASE_URL=sqlite+aiosqlite:///./astrolabe.db`
(a file-based DB local to the backend process; the Docker Compose file mounts this on a named
volume, `astrolabe_data`, at `/data`). No setup is required — `storage/db.py` creates all
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
True)`, `Float`, `String`, `Boolean` — no SQLite-only types), so the same schema works
against Postgres without modification once the driver is installed and the URL is set.

If storage/cache initialization fails for any reason (bad URL, unreachable DB, missing
driver), the backend does **not** crash — `api/deps.py` catches the exception, logs a
warning, and the service simply serves `live`/`replay` with `cached` mode reported as
unavailable (`CachedSource.available() == False`).

## Build / start commands

### Backend (Python host — e.g. Render, Railway, Fly.io, a VM)

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
above, this command has not been executed in the build environment — it is provided
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
  fall back to REST polling — **the WS client itself never calls REST**; it only reports its
  own connection state.
- Duplicate `book`/`price_change`/`last_trade_price` events are deduped via a bounded LRU set
  keyed on event type + asset id + hash + timestamp.

In the current API surface, live-mode order books are read via **CLOB REST**
(`GET /book`) at request time rather than a live WS-fed cache; the WebSocket client exists,
is unit-tested, and is intended for a longer-running ingestion/streaming process (see
`ingest/pipeline.py` and the `run_forever` polling loop) rather than being wired directly into
the request path of every `/api/*` call in this build.

## Fallback behaviour in production

Regardless of hosting, the mode-fallback chain described in `docs/architecture.md` applies:
`live` requests fall back to `cached` (if a populated cache exists) and finally to `replay`
(always available, bundled in the image). Operators should run the standalone ingestion
script (`python backend/scripts/ingest.py` for one cycle, or `python backend/scripts/
ingest.py --loop` to poll continuously on `POLL_INTERVAL_SECONDS`) on a schedule if they want
a meaningful `cached` fallback tier in production; without it, `cached` mode will report
`available() == False` and any fallback skips straight to `replay`.
