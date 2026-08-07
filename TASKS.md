# TASKS.md — Arepo

Legend: `[ ]` todo · `[~]` in progress · `[x]` done & verified · `[!]` blocked

## Final short-horizon completion (branch `arepo-final-short-horizon-completion`)
- [x] §10-11 due-horizon collection: terminal closed-before-horizon observation (no live post-close
      fetch); `closed_before_horizon` count; closed/awaiting/resolved/invalid kept distinct; +1 timing test
- [x] genuine forward collector run so the 6h horizon reconciles (denominator identity holds: 16+13+1+50=80)
- [x] Replay results-first: `lib/replay-ux.ts` + rewritten `app/replay/page.tsx`; horizon tabs
      [1h][6h][24h][7d][To close][Resolved]; auto newest-evaluable cohort; pending labelled; closing
      pills + scope [Opportunities][All signals][Research comparison]; research panels only under
      Research comparison; cohort mechanics collapsed; concise rows + View details; no six-zero cards
- [x] Replay tests: 15 vitest (replay-ux) + 10 Playwright (results-first, pending, scope, To-close/Resolved)
- [x] cards: human-readable Priority/Confidence/Evidence via accessible `InfoChip` (hover/focus/tap tooltip)
- [x] evidence friendly labels (price/order_book/trade_flow/wallet_concentration/timing); no raw keys shown
- [x] concentration family described neutrally — no wallet-identity / fresh-wallet claim
- [x] suppress per-card Stale/Fresh clutter (`cardTrajectoryLabel`); keep full staleness on market detail
- [x] remove "Also shown in Opportunities" badge; fix double-period in Opportunity strength sentence
- [x] fix real Playwright failures: `liveSignalMarketId` helper targets a live signal market; expand the
      per-signal breakdown; exclude `signal-detail-toggle` from popover triggers; click only visible ones
- [x] gate: backend 415 pytest + ruff; frontend tsc/lint + 86 vitest + build 16 routes; Playwright 104
- [x] real Chromium sweep: Opportunities / Signal Lab / Replay / market detail / sign-in (footer correct)
- [x] verify historical cohort preserved (60/19/10/9/120) + DB intact (cohort 1 untouched; cohort 2 = scan)
- [ ] commit + push to `arepo-final-short-horizon-completion` (no merge to main, no deploy)

## (superseded) Complete short-horizon universe (branch `arepo-complete-short-horizon-universe`)
- [x] safe start: DB backup + tag `arepo-before-complete-short-horizon-universe` + branch; DB preserved
- [x] §1 audit: proved 60 = discovery_limit=60 + screen_universe(60) + [:60], zero pagination (docs)
- [x] §2 complete offset pagination + fail-loud incompleteness + 11 mock tests (no stop at full page 1)
- [x] §3 backend 30-day eligibility gate before scoring; §4 non-overlapping buckets + cumulative windows
- [x] §5 complete-scan service: analyse EVERY eligible market; per-bucket + overall 30d ranking
- [x] §6 scopes: full eligible / all directional / public top ten / shadow (top ten display-only)
- [x] §7 refresh CLI: idempotent, advisory lease, stale recovery, funnel status; 5-min cadence measured
- [x] §8 append-only discovery_scan_runs/signal_snapshots/scan_locks (never overwrite; additive migration)
- [x] §9 trajectory + predeclared 0.02 stability threshold; New/Strengthening/Weakening/Stable/Reversed/Stale
- [x] §10-11 Signal Lab signals-first + scan status + "Top 10 shown from N" + bucket/scope + trajectory
- [x] §19 API /api/scan/status|signals|market/{id}/history (server-side truth, idempotent)
- [x] §20 scheduler: arepo-signal-refresh cron every 5 min in render.yaml (measured duration)
- [x] §21 backend tests (pagination 11 + discovery 11 + scan routes 2)
- [x] §22 frontend/browser: 10 vitest + 8 Playwright (signals-first, top-10-from-N, scope, trajectory, overflow)
- [x] §23 real acceptance: 21 pages/2100 raw/181 eligible/83 directional; TWO real refreshes append-only
- [x] §25 gate: backend 399 + ruff; frontend tsc/lint/68 vitest/build 15; Playwright 77; cohort unchanged
- [x] §26 docs (audit + methodology + CHECKPOINT/TASKS/DECISIONS/FINAL_STATUS); §27 commit + push
- [~] §13-18 future cohort freeze from complete scan + freeze-to-close + 4-question Replay matrix
      (forward-looking; complete-scan foundation built; kept separate so historical cohort unchanged)

## Prospective Replay refinement (branch `arepo-prospective-replay-refinement`)
- [x] safe start: DB backup + safety tag `arepo-before-prospective-replay-refinement` + branch; DB preserved
- [x] §1 Replay prospective-only: removed reconstructed + synthetic public tabs; legacy `?replay=` normalised
- [x] §2/§3 cohort cadence + freeze selectors (real cadences only) + horizon (1h/6h/24h/7d/final, pending honest)
- [x] §4 frozen time-to-close filter (6h/24h/7d/30d/all) from `time_remaining_hours`; never current TTC
- [x] §5 top-ten by frozen rank within filtered subset; never padded; public vs all-directional scope
- [x] §6 "Did the market move as expected?" headline + coverage + labelled hit-rate-among-moved + public/shadow split
- [x] §7 market-by-market table with intuitive labels + tooltip; links to market detail; mobile-readable
- [x] §8 midpoint movement shown separately from executable (after costs); honest unavailable
- [x] §9 corrected stale copy (dynamic cadence wording; removed "tracking has not started"; browser-does-not-collect)
- [x] §10 timing banner: scheduled cut-off / actually frozen / lateness / evaluation origin
- [x] §11 typed server-side endpoints `/api/research/replay/cohorts` + `/cohort/{id}`; deterministic + tested
- [x] §12 scheduler: 6h/daily/weekly research freeze crons + forward collector already correct; recorded, unchanged
- [x] §13 localhost: stopped exact stale dev PIDs; clean backend:8000 + frontend:3000; documented
- [x] §15 tests: 17 backend (15 replay + 2 route), 18 frontend vitest, 12 Playwright specs
- [x] §16 gate: backend 376 + ruff; frontend tsc/lint/58 vitest/build 15; Playwright 85; real 6h cohort verified
- [x] §17 docs (this file + CHECKPOINT/DECISIONS/FINAL_STATUS + docs/prospective-replay-refinement.md)
- [x] §18 commit + push branch (no merge to main, no deploy)

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

## Final runtime acceptance fix (branch `arepo-final-runtime-acceptance-fix`)
Safety tag `arepo-before-final-runtime-acceptance-fix`. Real-browser fixes for failures that passed unit tests.
- [x] §1 Popover: cap max-width BEFORE getBoundingClientRect measurement (measure==reveal width), visualViewport-aware, ≥12px clamp, two-pass, max-width min(22rem,100dvw−24px)
- [x] §2 Real browser tests: Playwright, 7 viewports incl. 574×900 repro; assert from bounding rects; screenshots on failure — 79 passed
- [x] §3 Overflow root causes fixed (TopBar wrap, sr-only table→div wrapper, SignalItem link truncate); scoped clip only on synthetic demo subtree; 632→574 at 574px
- [x] §4 Deliberate action row: badge own item, fixed 12px+ gap (12.8 measured), padded 32px toggle, wraps at 8px
- [x] §5 Replay real 6h cohort primary; banner (actual freeze/scheduled/84min late); counts/roles/horizons/edge/calibration/model-limitation; legacy ?replay=prospective→real
- [x] §6 vendor-chunks/geist.js = stale .next; clean build+dev proven; `clean`/`dev:clean`/`build:clean` scripts; route smoke tests
- [x] §7 Shared backoff status poller (dedup, abort-on-unmount, visibility-pause, auto-recover); one disconnected chip; no flood; no unhandled rejections
- [x] §8 docs/FINAL_RUNTIME_ACCEPTANCE.md + screenshots + before/after rects; no item Fail
- [x] §9 Gate: backend pytest 359 / ruff clean; frontend tsc / lint / vitest 40 / build clean; browser 79
- [x] §10 Docs updated; DB preserved; committed + pushed (deployment NOT triggered)
