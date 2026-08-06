# TASKS.md — Arepo

Legend: `[ ]` todo · `[~]` in progress · `[x]` done & verified · `[!]` blocked

## Final pre-deployment repair & launch readiness (branch `arepo-final-predeployment-launch-readiness`)
- [x] §1 baseline (docs/final-predeployment-baseline.md)
- [x] §2/§3 schema failure fixed: additive SQLite+Postgres migrator + preflight + tests + docs
- [x] §4 atomic freeze + partial-cohort detect/repair + tests
- [x] §5 unavailable-token exclusion funnel + degradation guard + status + tests
- [x] §6/§7/§8 popover primitive + overflow removal + action-row spacing + tests (live-verified)
- [x] §9 local acceptance (docs/FINAL_PREDEPLOYMENT_LOCAL_ACCEPTANCE.md); §10 full test gate green
- [x] §11 hosting decision; §12 orchestrator assessment (keep separate crons)
- [x] §13 render.yaml release migrate + scripts + deployment docs
- [x] §14/§15 Postgres-portable schema + production-equivalent dry run (passes headless)
- [x] §16 USER_DEPLOYMENT_CHECKLIST (39 steps); §17 goal refined
- [~] §18 reviewers (architecture+provenance CLEAN; DB/adversary running); fix confirmed findings
- [ ] push branch; §20 final report
- [!] external deployment (Supabase/Render/Vercel accounts) - user performs via the checklist

## Edge-research infrastructure (branch `arepo-edge-research-infrastructure`)
- [x] §1 safe start: baseline, goal, tag, branch
- [x] §2 freeze every directional signal + roles (full universe); §4 complete cut-off snapshot incl RP
- [x] §3 6h/daily/weekly immutable cohorts, idempotent, unique key + model/calc version
- [x] §5 outcomes 1h/6h/24h/7d + resolution; rich forward fields; causal predates-freeze guard
- [x] §6 depth-aware executable cost model (spread/slippage/fees); midpoint vs executable
- [x] §7 repricing vs resolution separated; no directional-as-probability
- [x] §8 baselines incl order-book-only/trade-flow-only/full-without-momentum (per-family dirs frozen)
- [x] §9 deterministic feature-ablation framework (9 variants)
- [x] §10 walk-forward partitions + no-leakage guardrail + windows
- [x] §11 calibration guard (Brier/log-loss only with a probability + min sample)
- [x] §12 synthetic isolated from all real performance
- [x] §13 research-status API + Replay surface (real stored numbers, honest empty state)
- [x] §14 edge acceptance criteria (10) + conservative verdict
- [x] §15 tests (27 research tests; 338 total); §17B end-to-end dry run (deterministic + live)
- [x] §17A architecture review + requirement traceability
- [x] §3/§17C render.yaml research crons (freeze 6h/daily/weekly + forward)
- [~] §16 reviewers (provenance/execution done: clean + 2 LOW; quant + adversarial running)
- [ ] fix confirmed critical/major reviewer findings; push branch
- [ ] §17E deployment handoff + §20 final report
- [!] deployment (Render/Supabase) - Blocked on external accounts; mechanism verified headless

## Signal Intelligence & Replay functional validation (branch `arepo-signal-replay-functional-validation`)
- [x] §1 safety tag + branch + baseline (docs/signal-replay-functional-baseline.md)
- [x] §2 independent reviewers A–G run; docs produced; Opus synthesis in DECISIONS D-SR1..D-SR6
- [x] §6/§17 one reliability confidence on every surface incl. Market Detail outcome cards; cap 0.95, no 100%
- [x] §10/§11 flat-aware evaluation (flat ≠ miss) in reconstructed Replay AND prospective cohort pipeline
- [x] §4 z-score materiality floor; volume_acceleration corrected (live-available, in completeness)
- [x] §9/§16 reconstructed reproducibility (UTC-day snap) + hard-survivorship honesty
- [x] §8 synthetic decision doc; /cohorts/latest excludes synthetic (verified 404)
- [x] §12/§13 momentum-agreement diagnostic; Brier/log-loss honestly N/A (not fabricated)
- [x] §4/§8/§17 component register, synthetic decision, cross-surface contract (+ test_cross_surface.py)
- [x] §17/§18 identifier routing test parametrised over 2694364 AND 2822017
- [x] §21 tests: flat, confidence ceiling, cross-surface, materiality floor (backend 320 pass)
- [x] §22 acceptance (docs/DAYYAN_SIGNAL_REPLAY_ACCEPTANCE.md); §23 reviewers re-run (F′, G accept)
- [ ] manual zoom check 80-150% (tooling can't change page zoom)
- [ ] accumulate prospective cohorts via the backend weekly freeze (needs cron over weeks)
- [!] deployment - Blocked on external accounts, by design (not requested this session)

## Final local implementation (branch `arepo-final-local-implementation`)
- [x] §1 baseline; §2 report reconciliation (added current-implied + price-only baselines)
- [x] §3 CRITICAL routing bug (canonical resolution; IDs 2694364/2822017 open in any mode); doc + 5 tests
- [x] §4/§5 blank routes / footer-follows-content / compact error card
- [x] §6/§7 Signal Lab directional filter + sort (URL); direction in words
- [x] §8 full-width nav; §9 tab title exactly "Arepo"
- [x] §10 hidden-scrollbar shared Learn menu
- [x] §11 auth one-viewport + nav-style wordmark (PNG removed)
- [x] §12-20 Replay: default "last week's opportunities"; funnel; six baselines; point-in-time RP +
      close-date + time-remaining; closing-soon lens (URL); data-status; synthetic-date fix;
      definitions; docs/replay-product-review.md
- [x] §21 acceptance doc (docs/DAYYAN_FINAL_LOCAL_ACCEPTANCE.md); §22 gates (backend 309, frontend 21 vitest)
- [ ] §21 manual zoom check 80-150% (tooling can't change page zoom)
- [!] §23 deployment (Vercel/Render/Supabase/Resend) - Blocked on external accounts, by design

## Final gap-closure (branch `arepo-final-gap-closure`)
- [x] §1 baseline (docs/final-gap-baseline.md); §2 reviews (quant/beginner/Dayyan acceptance)
- [x] §3 remove broken Full definition; verify all help links resolve
- [x] §4 directional coverage disclosed; shared gate across surfaces
- [x] §5 replay regression investigation + regression/stats tests
- [x] §6 Replay top-5, funnel, baselines, more cut-offs, inconclusive labels
- [x] §7 Replay modes (prospective/reconstructed/synthetic) badged, never mixed
- [x] §8 confidence distribution + missing-component penalty + tests (no 100% spike)
- [x] §9 wire microstructure components live; honest reasons; diagnostics; audit doc
- [x] §10 URL filter-state helpers + vitest
- [x] §11 How It Works left-nav (shared SectionMenu) + smaller cards; Methodology too
- [x] §12 Why Arepo -> sign-in/up/reset brand showcase with supplied wordmark
- [x] §13 Signal Lab qualify/why (shared gate); Yes/No consolidated
- [x] §14 data-consistency checks + invariant guard
- [x] §15 docs/final-production-architecture.md (single coherent architecture)
- [x] §19 full gate run (backend 303, frontend tsc/lint/14 vitest, build)
- [!] §16/§17 live deployment (Vercel/Render/Supabase/Resend) - Blocked on external accounts
- [!] §16 production login/email/schedules + live URLs - Blocked on external accounts
- [ ] §20 final report (delivered in chat)

## Directional Evidence, Replay & Deployment (branch `arepo-directional-evidence-deployment`)
- [x] §2 read research report in full; docs/research-paper-evidence-audit.md (adopted vs deferred)
- [x] §3 directional-rarity diagnosis (docs/directional-diagnosis.md); root cause = data, not thresholds
- [x] §3/§6 z-score baseline exclusion + flat_baseline_move; confidence = reliability (no 100% spike)
- [x] §6 rename movement_1h -> recent_movement
- [x] §4 selective board (directional/strongest/inconclusive/all) + screened/qualify counts
- [x] §7 microstructure snapshot store + change features + idempotent collect + composite-contribution test
- [x] §9 URL filter persistence (board + markets) via useUrlState
- [x] §10 unify market model-view directional gate with backend rule
- [x] §16-20 deployment prep: Resend provider, render.yaml (+7 UTC crons), vercel.json, asyncpg, docs
- [ ] §12-13 Replay Top-5 default + baseline comparisons (no-change/price-only/momentum/book/implied) + Brier/log loss
- [ ] §5 baseline metrics table + operating-point doc (depends on §13 harness)
- [ ] §8 data-consistency warnings (end_date / close / resolution contradictions)
- [ ] §14 How It Works left-nav redesign
- [ ] §15 sign-in / brand page (wordmark, red mark under A); remove Why Arepo from result pages
- [ ] §9/§21 browser tests for filter restoration (no harness yet)
- [ ] §7 follow-up: thread snapshot changes into the live board-build enrich path

## Product Simplification, Accounts & Decision-Support (branch `arepo-product-simplification`)
- [x] Phase 1: two Sonnet product reviews (beginner + quant) + synthesis (DECISIONS P0-P3)
- [x] Phase 1: statistical-integrity fixes (decouple confidence/strength; wire freshness;
      drop unimplemented cross_market family)
- [x] Phase 2: computed statistical hypothesis (backend, insufficient-evidence state) on cards
- [x] Phase 2: Opportunity card redesign (lead with hypothesis + direction; demote score to
      labelled chip; N independent lines of evidence)
- [x] Phase 2: accessible TagChip popover (plain definition, why it matters, family, method link)
- [x] Phase 2: time-to-close filter (24h/3d/7d/all); nav renamed (Opportunities, Explore)
- [x] Phase 2: Signal Lab consolidated to one signal per market (no duplicate Yes/No)
- [x] Phase 3: accounts backend (fastapi-users: register/verify/login/logout/reset; argon2;
      JWT cookie); schema (users, alert_preferences, saved_markets, alert_deliveries,
      account_deletions); per-user isolation; rate limiting; .env.example; 10 tests
- [x] Phase 4: accounts frontend (signup/signin/forgot/reset/verify/account + alert settings);
      auth context; verification link visible via console sink; live lifecycle smoke passed
- [x] Phase 5: connect alert engine to per-user verified/opted-in preferences (+ 10 tests)
- [x] Phase 6: performance profiling + board stale-while-revalidate cache (6.1s->~2ms; 4 tests)
- [x] Phase 7: Replay historical price-only reconstruction verified live; docs; review; push
- [x] Market detail: leads with "Current model view" hypothesis + progressive disclosure (§6)
- [x] Brand/origin story confirmed in How It Works (Learn), not on technical result pages (§4)
- [x] Post-implementation review (§17): 2 genuine findings fixed (stale docstring, TagChip ARIA);
      stale-checkout FAILs on alerts/cache were false (both exist and are tested)

## Opportunity Intelligence & Alerting pass (branch `arepo-opportunity-alerts`)
- [x] Confirm branch + prior branch pushed; investigate trade/wallet data (DECISIONS O2)
- [x] Choose information architecture (DECISIONS O1)
- [x] Data API client (trades, wallet history) + robustness
- [x] Flow/wallet/timing indicators: large relative trade, consensus-opposing flow,
      late large trade, concentrated flow, clustered trades, limited activity history
- [x] Evidence-family model + Research Priority score (fixed weights, >=2 family rule)
- [x] Tags with tooltip/explanation/methodology link/timestamp/data-quality
- [x] Opportunity Board backend (top-30) + frontend (new home) + nav restructure
- [x] Explore Markets (rename) retained
- [x] Search repair: full-universe discovery + company/ticker alias layer (Microsoft/MSFT)
- [x] Daily immutable snapshot (top-30) + idempotency
- [x] Email alerts: provider-neutral, console sink, disabled external, dedup/cooldown/
      history/retry/failure-log/disable/test-mode; eligibility + wording
- [x] Tests (indicators, evidence families, search, snapshot immutability, alert
      eligibility/wording/dedup/cooldown/provider-failure/no-secrets/no-look-ahead)
- [x] Full QA, independent review + fixes, docs, push

## Signal & Historical Refinement pass (branch `arepo-signal-refinement`)
- [x] Investigate historical data availability (dense/real; see DECISIONS S1)
- [x] Navigation: remove horizontal scroll, spread items, stable full-width desktop
- [x] Logo slightly larger everywhere; wordmark + grid symbol integration
- [x] Favicon = stylised "A" from wordmark, wired correctly
- [x] Status chip: keep truthful states only (API + Updated-when-known), no Unknown
- [x] Signal Lab: rename to "Composite anomaly"; purpose header; link to markets;
      "How this may be used" section; clearer IA
- [x] Signal engine: rebalance composite across standardized features (no imbalance
      dominance, no overfitting); document components/weights/evidence/safeguards; tests
- [x] Market detail: chart timeline ranges (1H/6H/24H/7D/All, only sensible ones);
      reuse advanced-data style for other technical sections
- [x] Order-book explainer panel: repair diagram, labels, colours, interactivity
- [x] Historical reconstructed retrospective (top-15), separated provenance; tests
- [x] Footer credit: Designed and created by Dayyan Sheikh / dayyansheikh.work@gmail.com
- [x] QA: backend tests, frontend tsc/lint/build/vitest, browser checks, screenshots
- [x] Independent review + fixes (causal selection, material floor); docs update; report

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
