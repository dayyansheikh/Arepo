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

**Opportunity Intelligence & Alerting pass STARTING** (branch `arepo-opportunity-alerts`,
from the pushed `arepo-signal-refinement` at 77ec2b3). Data verified: trade-level + wallet
data available read-only via `data-api.polymarket.com/trades` (see DECISIONS O2).
Architecture chosen (DECISIONS O1): Opportunity Board as home, Explore Markets retained,
Signal Lab as deep analysis. Building: trade-flow/wallet/timing indicators + evidence
families, Research Priority score, Opportunity Board (backend+frontend), full-universe
search repair + company/ticker aliases, daily immutable snapshot, provider-neutral email
alerts (console sink default, external disabled). Recovery: previous branch pushed; roll
back within this branch with git; `arepo-ui-v1` tag still the deep safety point.

## (previous) Current phase

**Signal & Historical Refinement pass COMPLETE** (branch `arepo-signal-refinement`, from
the completed Master Final Refinement at 76f0db2; recovery tag `arepo-ui-v1` still valid).
All ten workstreams delivered, browser-verified, and committed: nav (non-scrolling),
wordmark "A" favicon, larger logo, footer credit, truthful status chip, Signal Lab
("Composite anomaly" + purpose + market linking + "How this may be used"), signal-engine
rebalance (price features 0.60 vs imbalance 0.12 + book-only ceiling with material floor),
chart timeline ranges (1H/6H/24H/7D/All), order-book explainer repair, and the historical
reconstructed retrospective (`/api/historical/screen` + Replay tab, causal no-look-ahead).

Independent Sonnet review run over the pass; two defects found and FIXED + regression-tested
(see DECISIONS S7): causal historical selection (price at cut-off, not today) and the
book-only ceiling requiring material price context. A fresh independent-subagent review was
blocked by the account monthly spend limit.

Final verified state: backend **193 tests pass**, ruff clean, migration bootstrap idempotent;
frontend `tsc`/`lint`/`build` clean (10/10 routes), **8 vitest**. All seven surfaces
browser-verified against a live backend. Docs updated (methodology §9/§9a, API, limitations,
brand-system, README, FINAL_STATUS). Next action: commit + push to origin.

---

## (previous) Master Final Refinement

**All phases complete (1 to 4), verified and committed.** Independent Sonnet review
run over the full branch: it confirmed every truthfulness guarantee is genuinely
enforced (no hindsight, frozen immutability, idempotency, provenance separation, all
13 required tests non-vacuous, genuine chart root-cause fix, no em dashes in product
text) and found one MAJOR defect (forward-price collection lost a horizon on a
transient failure), which was fixed and regression-tested (backend now 175 pass).

Final verified state: backend **175 tests pass**, ruff clean; frontend `tsc`/`lint`/
`build` clean (10/10 routes), **8 vitest** pass. Browser-verified all seven surfaces
against a live backend + seeded synthetic cohort: display font, grid logo, neutral
panels, API/Live feed/Updated labels, the chart fix (visible lines + real time axis),
Markets facets, Signal Lab terminology, and the Replay cohort UI (week picker, two
views, portfolio, provenance). Fresh screenshots in `docs/screenshots/arepo-*.jpg`.

### Phase 3 delivered
Replay page rebuilt around the cohort API (week picker, price-movement vs final-
resolution views, per-signal verdicts, hypothetical portfolio, provenance notice;
the deterministic backtest preserved as a labelled demonstration).

### Phase 4 delivered
QA + em-dash removal + status-state fix; accessibility (non-colour cues, focus ring,
reduced motion, chart alt-table); independent review + fix; full docs refresh
(README, architecture, methodology, API, deployment, limitations, brand-system,
portfolio-report, FINAL_STATUS); grid-mark favicon; submission packaging.

Real prospective cohorts begin at the first `python -m astrolabe.evaluation.cli rank
--mode live` run (none yet; the visible cohort is the labelled synthetic demo).

### Phase 2 delivered (backend, 174 tests pass / ruff clean)
- `backend/astrolabe/evaluation/`: constants, errors, ORM models (8 entities),
  ranking (eligibility/tie-break/week-bounds), snapshots (immutable, entry price =
  signal-time midpoint), repository (frozen-immutability guards + idempotent upserts),
  engine (provisional top-10 + replace-lowest + anti-concentration + freeze),
  tracking (forward prices/resolutions/evaluation), portfolio (pure simulation),
  service (read + runner), schemas (typed API), migrations (idempotent bootstrap),
  cli (`python -m astrolabe.evaluation.cli` rank/freeze/forward/resolve/evaluate/
  seed-synthetic/status), seed (labelled synthetic demo).
- API: `/api/cohorts/weeks|provenance|latest|{year}/{week}` (router in app.py;
  eval tables registered at startup via deps.init_storage).
- 19 evaluation tests in `tests/unit/test_evaluation.py` cover all 13 required
  guarantees. Verified end-to-end: seeded synthetic cohort (2026-W28, 3 entries),
  all 4 endpoints 200, portfolio computed.
- DB: default `backend/astrolabe.db` (gitignored). Seed with
  `python -m astrolabe.evaluation.cli seed-synthetic`. Env var is `DATABASE_URL`.
  Real prospective cohorts begin at first `... cli rank --mode live` run.

## Completed work (verified)
- Phase 0: baseline recorded; recovery files written.
- Phase 1 (committed 85886e7 + follow-up): display font Jost vendored via
  next/font/local; body-size bump (root 17px); PageHeader/SectionTitle; nav presence
  + active underline; faithful grid-logo SVG + AREPO wordmark; neutral info panel;
  amber DegradationBanner; API/Live feed/Updated status labels; chart repair
  (frontend buildChart + backend timestamp fix, 8 vitest + 3 pytest regression);
  category/sport/competition facets (`/api/markets/facets`, 24 tests) wired into
  Markets page (Sport/Competition filters, empty states); Signal Lab terminology
  (Unusual market activity, Data coverage, Lookback, friendly component names,
  technical detail disclosures); Methodology/How-It-Works readability + neutral
  callouts; market-detail + overview bold section titles.
- Verified integrated: backend 155 pass/ruff clean; frontend tsc/lint/build 10/10 +
  8 vitest.

## In-flight
- Phase 2 evaluation engine: models/repository/ranking/snapshots written; still to do:
  engine.py (rank+freeze orchestration), forward.py (forward prices/resolution/
  portfolio), schemas.py, service.py, API routes, migration + CLI scripts, tests.

## Exact next action
1. Finish `evaluation/engine.py` (provisional ranking + freeze orchestration).
2. forward-price/resolution/portfolio, typed schemas, service, API routes.
3. Migration bootstrap + idempotent CLI scripts (rank/freeze/forward/resolve).
4. Write the 13 required evaluation tests; run backend suite; commit Phase 2.

## Known failures / unresolved
- Storage round-trip for sport/competition not persisted in cached mode (category is);
  acceptable, noted by categories subagent.
- signal-labels metrics.ts "Learn more" links point to nearest existing methodology
  anchors (signal-strength/confidence), not bespoke anchors.
