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

### Known note
- Full `pytest` discovery hangs *only while the WS agent is mid-writing* its test file; run
  targeted files until S3 lands, then run the full suite.

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
