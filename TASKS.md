# TASKS.md — Arepo

Legend: `[ ]` todo · `[~]` in progress · `[x]` done & verified · `[!]` blocked

## Signal & Historical Refinement pass (branch `arepo-signal-refinement`)
- [x] Investigate historical data availability (dense/real; see DECISIONS S1)
- [ ] Navigation: remove horizontal scroll, spread items, stable full-width desktop
- [ ] Logo slightly larger everywhere; wordmark + grid symbol integration
- [ ] Favicon = stylised "A" from wordmark, wired correctly
- [ ] Status chip: keep truthful states only (API + Updated-when-known), no Unknown
- [ ] Signal Lab: rename to "Composite anomaly"; purpose header; link to markets;
      "How this may be used" section; clearer IA
- [ ] Signal engine: rebalance composite across standardized features (no imbalance
      dominance, no overfitting); document components/weights/evidence/safeguards; tests
- [ ] Market detail: chart timeline ranges (1H/6H/24H/7D/All, only sensible ones);
      reuse advanced-data style for other technical sections
- [ ] Order-book explainer panel: repair diagram, labels, colours, interactivity
- [ ] Historical reconstructed retrospective (top-15), separated provenance; tests
- [ ] Footer credit: Designed and created by Dayyan Sheikh / dayyansheikh.work@gmail.com
- [ ] QA: backend tests, frontend tsc/lint/build/vitest, browser checks, screenshots
- [ ] Independent review + fixes; docs update; report

---

## (previous) Master Final Refinement
Prior redesign + original build tasks are complete; history is in git.

## Phase 0 — Safety
- [x] Confirm branch `arepo-master-final` + clean tree
- [x] Record baseline: backend 128 pass/ruff clean; FE tsc/lint/build clean (10/10)
- [x] Confirm safety tag `arepo-ui-v1` exists
- [x] Inspect brand assets; choose display font (Jost, approximation)
- [x] Write recovery scaffolding (CHECKPOINT/TASKS/DECISIONS)

## Phase 1 — Foundation & UI polish
- [x] Display heading font (Jost) tokens; interface = Geist
- [x] Body text size bump; heading weight/contrast; bold section titles
- [x] Navigation presence, logo/wordmark readability, active/hover/mobile
- [x] Neutral information panel (replace pale-red DisclaimerBanner)
- [x] Status labels REST/WS/age → API / Live feed / Updated (+ tooltips, states)
- [x] Chart repair: visible strokes/points for sparse data + limited-history note
- [x] Unknown / "Parent for derivative" metadata fallbacks
- [x] Markets filters: real categories, Sports grouping, competitions, empty states
- [x] Signal Lab terminology (Unusual market activity, Data coverage, Lookback, components)
- [x] Methodology readability
- [x] Market detail readability + progressive disclosure
- [x] Tests: category/sports extraction, chart row-building, normalize fallbacks

## Phase 2 — Prospective evaluation engine (backend)
- [x] Schema + migrations: signal_snapshots, weekly_cohorts, cohort_entries,
      ranking_audit, forward_price_observations, market_resolutions,
      evaluation_results, calculation_versions
- [x] Provisional weekly top-ten ranking (in-week replacement of lowest)
- [x] Weekly freeze (immutability) + tie-breaking + audit trail
- [x] Forward price collection (1h/24h/7d/close)
- [x] Resolution tracking
- [x] Portfolio simulation (fixed stake, fees, spread)
- [x] Idempotent CLI commands (rank/freeze/forward/resolve)
- [x] Typed API endpoints (weeks/summary/entries/forward/resolutions/portfolio/provenance)
- [x] 13 required evaluation tests

## Phase 3 — Replay redesign (frontend)
- [x] Replay page consumes cohort API; week picker; provisional vs frozen
- [x] Price-movement vs final-resolution views; pending/correct/incorrect
- [x] Portfolio assumptions; plain summary with denominator + pending + horizon
- [x] Provenance / synthetic-vs-real separation

## Phase 4 — QA, a11y, docs, packaging
- [x] Accessibility pass (contrast, focus, keyboard, non-colour cues, reduced motion)
- [x] Independent Sonnet reviews per phase + fixes
- [x] Browser visual checks + screenshots
- [x] Docs: README, architecture, methodology, API, deployment, limitations,
      brand-system, portfolio-report, FINAL_STATUS
- [x] Submission ZIP

## Blocked (external authorization only)
- [!] `docker compose up` — no Docker daemon in environment
- [!] Public deployment / paid scheduler activation — requires user's account auth
