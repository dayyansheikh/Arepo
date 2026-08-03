# TASKS.md — Arepo Master Final Refinement

Legend: `[ ]` todo · `[~]` in progress · `[x]` done & verified · `[!]` blocked
Prior redesign + original build tasks are complete; history is in git and older
`TASKS.md` revisions. This file now tracks the **Master Final Refinement**.

## Phase 0 — Safety
- [x] Confirm branch `arepo-master-final` + clean tree
- [x] Record baseline: backend 128 pass/ruff clean; FE tsc/lint/build clean (10/10)
- [x] Confirm safety tag `arepo-ui-v1` exists
- [x] Inspect brand assets; choose display font (Jost, approximation)
- [x] Write recovery scaffolding (CHECKPOINT/TASKS/DECISIONS)

## Phase 1 — Foundation & UI polish
- [ ] Display heading font (Jost) tokens; interface = Geist
- [ ] Body text size bump; heading weight/contrast; bold section titles
- [ ] Navigation presence, logo/wordmark readability, active/hover/mobile
- [ ] Neutral information panel (replace pale-red DisclaimerBanner)
- [ ] Status labels REST/WS/age → API / Live feed / Updated (+ tooltips, states)
- [ ] Chart repair: visible strokes/points for sparse data + limited-history note
- [ ] Unknown / "Parent for derivative" metadata fallbacks
- [ ] Markets filters: real categories, Sports grouping, competitions, empty states
- [ ] Signal Lab terminology (Unusual market activity, Data coverage, Lookback, components)
- [ ] Methodology readability
- [ ] Market detail readability + progressive disclosure
- [ ] Tests: category/sports extraction, chart row-building, normalize fallbacks

## Phase 2 — Prospective evaluation engine (backend)
- [ ] Schema + migrations: signal_snapshots, weekly_cohorts, cohort_entries,
      ranking_audit, forward_price_observations, market_resolutions,
      evaluation_results, calculation_versions
- [ ] Provisional weekly top-ten ranking (in-week replacement of lowest)
- [ ] Weekly freeze (immutability) + tie-breaking + audit trail
- [ ] Forward price collection (1h/24h/7d/close)
- [ ] Resolution tracking
- [ ] Portfolio simulation (fixed stake, fees, spread)
- [ ] Idempotent CLI commands (rank/freeze/forward/resolve)
- [ ] Typed API endpoints (weeks/summary/entries/forward/resolutions/portfolio/provenance)
- [ ] 13 required evaluation tests

## Phase 3 — Replay redesign (frontend)
- [ ] Replay page consumes cohort API; week picker; provisional vs frozen
- [ ] Price-movement vs final-resolution views; pending/correct/incorrect
- [ ] Portfolio assumptions; plain summary with denominator + pending + horizon
- [ ] Provenance / synthetic-vs-real separation

## Phase 4 — QA, a11y, docs, packaging
- [ ] Accessibility pass (contrast, focus, keyboard, non-colour cues, reduced motion)
- [ ] Independent Sonnet reviews per phase + fixes
- [ ] Browser visual checks + screenshots
- [ ] Docs: README, architecture, methodology, API, deployment, limitations,
      brand-system, portfolio-report, FINAL_STATUS
- [ ] Submission ZIP

## Blocked (external authorization only)
- [!] `docker compose up` — no Docker daemon in environment
- [!] Public deployment / paid scheduler activation — requires user's account auth
