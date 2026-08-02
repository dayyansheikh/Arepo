# CHECKPOINT.md — Astrolabe

_Single source of truth for "where are we, exactly." Updated after each wave._

## Current phase
**Phases 3–5 in progress** — ingestion, replay/analytics landed; storage + WS in flight.

### Verified milestones (Opus-run, not agent claims)
- Spine boots; `/health` OK. 2 spine tests.
- Analytics core: 11 tests w/ hand-derived values (z=1.5, vol=0.01, imbalance=30/270). ruff clean.
- Ingestion (Gamma+CLOB REST + normalize): 53 tests; **also smoke-verified on a real live
  Gamma market** (JSON-string parsing, Yes/No pairing, ACTIVE status). `/markets/{id}`=200 live.
- Replay + backtest: deterministic dataset (3 mkts/144 frames), look-ahead-safe backtest
  (sample 16, hit-rate 0.625, fp-rate 0.125); 6 tests incl. prefix look-ahead property.
- **72 tests pass in my own run** (excluding the in-flight WS test); ruff clean repo-wide.
- Commits: scaffold → analytics → ingestion+replay+backtest.

### Backend complete + verified (Opus-run)
- WebSocket client (resilient, deduped) — read + 11 tests pass.
- Storage (SQLAlchemy async, SQLite/Postgres) — 13 tests; greenlet added to deps.
- Service brain (live/cached/replay + fallback) — 8 tests; DataStatus never mislabels mode.
- FastAPI routes (overview/markets/detail/signals/status/meta/replay) — 10 tests; booted a
  real uvicorn server, all endpoints 200, /docs serves, X-Response-Time header present.
- Ingestion pipeline — 2 tests + **real live ingest** (7 markets, 14 book snapshots) then
  CACHED read verified. Robustness fix: 404/4xx mapped to typed errors (no httpx leak).
- **All three modes verified against real Polymarket**: LIVE (16 real markets, real books,
  imbalance ±0.962, z over 145 pts), CACHED (real ingest round-trip), REPLAY (deterministic).
- **121 tests pass; ruff clean repo-wide.** 6 commits.

### In flight (background agents)
- Frontend build (Next.js/TS/Tailwind) against the API contract.
- Independent adversarial backend review (findings to triage).

### Remaining
- Fold review findings; Docker/compose + deploy configs; docs set + Mermaid; PDF report;
  packaging script + ZIP; FINAL_STATUS + demo script. Docker exec + public deploy remain
  blocked (no daemon / no host auth).

## Completed work (verified)
- Read `CLAUDE.md` + `PROJECT_SPEC.md` in full.
- Environment audited: Python **3.11.2**, Node **v20.20.0**, npm 10.8.2, git 2.39.
  **No Docker daemon**, **no `gh`/`vercel` CLI** on this machine (recorded as constraints).
- Verified live API schemas by direct HTTP requests (Gamma `/markets`,`/events`; CLOB
  `/book`,`/midpoint`,`/price`,`/spread`,`/prices-history`) — all HTTP 200. See
  `docs/research-notes.md`.
- Product named **Astrolabe** with due-diligence recorded in `DECISIONS.md`.
- Fresh git repo `Projects/astrolabe` initialised; directory tree created.
- Tracking files created: `TASKS.md`, `CHECKPOINT.md`, `DECISIONS.md`, `docs/research-notes.md`.

## Exact commands run so far
- `curl` probes against gamma-api / clob.polymarket.com (schema verification).
- `git init` in `Projects/astrolabe`.
- Directory skeleton via `mkdir -p`.

## Verified test results
- None yet (no code under test yet).

## Unresolved defects
- None yet.

## In-flight
- Background Sonnet research agent confirming the CLOB **WebSocket** protocol from primary docs.

## Deployment status
- Not started. Docker exec + public deploy are **blocked** on missing tooling / user auth
  (see `DECISIONS.md` A5). Configs will be authored and inspection-validated.

## Exact next action
1. Write typed domain models (`backend/astrolabe/domain/{models,enums}.py`) — the shared
   contract for all subagents.
2. Write config + structured logging + FastAPI app skeleton + `/health`.
3. Set up Python venv, install backend deps, get an empty app to boot + a first passing test.
4. Fold in the WS research report; then fan out Sonnet agents for clients/analytics/frontend.
