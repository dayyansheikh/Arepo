# CHECKPOINT.md — Astrolabe

_Single source of truth for "where are we, exactly." Updated after each wave._

## Current phase
**Phase 2 — Repository scaffolding + typed domain contract** (Phase 1 research/naming done).

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
