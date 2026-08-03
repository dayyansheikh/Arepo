# CHECKPOINT.md — Arepo

_Single source of truth for "where are we, exactly." Updated at the end of every phase.
Older history is preserved in git; this file tracks the **Master Final Refinement**._

## Recovery / resume

Branch: `arepo-master-final`. Safety tag before this effort: **`arepo-ui-v1`**
(also `astrolabe-baseline`). To resume, send `carry on`: read
`AREPO_MASTER_FINAL_PROMPT.md`, this file, `TASKS.md`, `DECISIONS.md`, then continue
from **Exact next action** below.

### Rollback
`git reset --hard arepo-ui-v1` restores the pre-refinement stable build. Never
delete that tag. Never rewrite history.

---

## Baseline (recorded 2026-08-03, start of Master Final Refinement)

- Backend: **128 tests pass**, `ruff check` clean.
- Frontend: `tsc --noEmit` clean, `next lint` clean, `next build` clean (10/10 routes).
- Working tree clean at start.
- Brand assets inspected: wordmark is a wide-tracked, all-caps, geometric monoline
  sans (perfect-circle O, triangular A apex, Futura-like). Display-font decision:
  **Jost** (OFL, Futura revival) via `next/font/google`, uppercase + wide tracking,
  documented as an approximation. Logo is a 5×5 grid "A" chevron, red-on-black.

## Stack facts

- Backend: FastAPI + SQLAlchemy 2.0 async (SQLite default, Postgres-compatible),
  pytest. No Alembic yet (uses `create_all`); migrations to be added for the cohort
  system. venv at `backend/.venv`; run tests with
  `cd backend && source .venv/bin/activate && python -m pytest -q`.
- Frontend: Next.js 14 app router, Tailwind, Geist Sans/Mono via `geist`, Recharts,
  KaTeX. **No frontend test runner** (tsc + lint + build are the gates). Light-only
  identity. Tokens in `tailwind.config.ts` + `globals.css` + `lib/theme.ts`.

## Current phase

**Phase 0 complete** (baseline verified, recovery scaffolding, stable checkpoint).
Starting **Phase 1 — Foundation & UI polish**.

## Completed work (verified)
- Phase 0: baseline tests/build recorded; recovery files written.

## In-flight
- (none)

## Exact next action
1. Phase 1 foundation (Opus-owned shared files): display font (Jost) tokens, body
   text size bump, heading hierarchy, neutral information panel, nav presence,
   status labels (API / Live feed / Updated), logo readability.
2. Fan out non-overlapping Sonnet subagents: chart repair, Markets categories/sports,
   Signal Lab terminology, Methodology readability, metadata fallbacks.
3. Run tsc + lint + build; commit Phase 1; update this file, TASKS.md, DECISIONS.md.

## Known failures / unresolved
- (none)
