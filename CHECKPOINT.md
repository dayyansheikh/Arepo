# CHECKPOINT.md — Arepo

_Single source of truth for "where are we, exactly." Updated at the end of every phase.
Older history is preserved in git; this file tracks the **Master Final Refinement**._

## Latest: Complete short-horizon universe (branch `arepo-complete-short-horizon-universe`)

Safety tag before this pass: **`arepo-before-complete-short-horizon-universe`**. DB backed up +
fully preserved (historical cohort intact: 60 entries / 19 directional / 10 public / 9 shadow / 120
forwards). Docs: `docs/complete-universe-discovery-audit.md`, `docs/complete-universe-and-signal-lab.md`.

**Why the old cohort was 60 (proved):** `config.discovery_limit=60` (single unpaginated `/events`
page) + `screen_universe(universe_limit=60)` + `enrich_markets` `subset[:60]`. Three 60-caps, zero
pagination. Previous discovery was TRUNCATED, not complete. Real universe is >4000 active markets.

DONE + tested:
- **§2 complete pagination**: `GammaClient.paginate_markets` follows every offset page to genuine
  exhaustion; records pages/raw/unique/offset-progression; detects non-progression + the upstream
  422 offset cap (Gamma caps offset at 2100, keyset non-functional) + emergency guard; `complete`
  flag is loud (never silently complete). 11 mock-transport tests.
- **§3-5 eligibility + buckets + scan**: backend 30-day gate before scoring; non-overlapping buckets
  (0-6h/6-24h/1-7d/7-30d + all_0_30d) with frozen `time_remaining_hours`; complete-scan service scores
  EVERY eligible market, ranks per bucket + overall 30d; top ten is a display flag over the full set.
- **§7-9 append-only + refresh + trajectory**: additive `discovery_scan_runs`/`discovery_signal_
  snapshots`/`discovery_scan_locks` (never overwrite; unique scan+market+token); refresh CLI with
  advisory lease + stale recovery; trajectory (New/Strengthening/Weakening/Stable/Reversed/Stale)
  with predeclared 0.02 stability threshold. 11 discovery tests.
- **§10-11,22 Signal Lab**: rebuilt signals-first (explanation collapsed), scan-status strip, "Top 10
  shown from N eligible markets", bucket + scope controls, server-computed trajectory on cards. 10
  vitest + 8 Playwright.
- **§19 API**: `/api/scan/status|signals|market/{id}/history` (server-side truth, idempotent).
- **§20 scheduler**: `arepo-signal-refresh` cron every 5 min (measured ~15-32s/scan) in render.yaml.
- **§23 real acceptance**: real live scan = 21 pages / 2100 raw / 181 eligible-30d / 83 directional /
  ~15-32s / pagination incomplete (offset cap, honest). TWO real refreshes recorded into the real DB
  (362 snapshots) proving append-only; 181 markets in both scans feed trajectory.
- Gates: backend **399 pass** + ruff clean; frontend tsc/lint clean, **68 vitest**, build 15 routes,
  **Playwright 77 passed**. Historical cohort unchanged. NOT deployed, NOT merged.

Forward-looking (documented, not fully wired): §13-18 future cohort freeze from the complete scan +
freeze-to-close collection + the four-question Replay matrix over bucket cohorts (kept separate so the
historical cohort is never modified; the existing prospective Replay already separates short-term
movement from final resolution and supports closing-window selection).

## (superseded) Prospective Replay refinement (branch `arepo-prospective-replay-refinement`)

Safety tag before this pass: **`arepo-before-prospective-replay-refinement`**. DB backed up
(`backend/astrolabe.db.backup-before-prospective-replay-refinement-*`) and fully preserved: 1 real 6h
cohort, 60 entries, 120 forward obs intact (universe 60 / directional 19 / public 10 / shadow 9).
Product, evaluation-display and Replay refinement only; no model/threshold/confidence/RP/eligibility/
baseline/ablation/walk-forward/edge/frozen-value change. See `docs/prospective-replay-refinement.md`.

- Replay is now **prospective-only**: reconstructed + synthetic tabs removed from the public page
  (infra kept internally for tests); legacy `?replay=` values normalise to the prospective page and
  the stale param is stripped.
- Rebuilt around: cohort cadence + freeze selectors (only cadences with real cohorts; six-hour
  cohort described as six-hourly, never weekly), evaluation horizon (1h/6h/24h/7d/final; pending when
  no stored observation), frozen time-to-close filter (6h/24h/7d/30d/all, using frozen
  `time_remaining_hours`), and a scope control (public vs all-directional incl shadow).
- "Did the market move as expected?" section: headline "Of 19 directional calls, 4 moved as
  expected, 4 moved against the call and 11 did not change"; movement coverage; labelled
  hit-rate-among-moved "50% (4 of 8)"; public 2/2/6, shadow 2/2/5, combined 4/4/11 splits.
- Market-by-market table with frozen rank, midpoint movement, executable (after costs) shown
  separately, frozen time-to-close, colour-independent result labels + tooltip. Final resolution kept
  separate (pending for this unresolved cohort).
- New typed server-side endpoints: `GET /api/research/replay/cohorts` +
  `/api/research/replay/cohort/{id}` (deterministic, idempotent; excessively-late cohorts excluded).
- Scheduler (`render.yaml`) already had correct 6h/daily/weekly research freeze crons + 20-min
  forward collector; recorded, left unchanged. Not deployed.
- Gates: backend **376 pass** + ruff clean; frontend tsc/lint clean, **58 vitest**, build 15 routes,
  **Playwright 85 passed** (real Chromium + real backend + preserved DB). Acceptance numbers verified
  in the real browser. Localhost: stopped the two stale dev PIDs from the previous run (backend
  93205, frontend 99230/99231), started clean backend:8000 + frontend:3000. NOT deployed, NOT merged.

## (superseded) Final runtime acceptance fix — COMPLETE (branch `arepo-final-runtime-acceptance-fix`)

Safety tag before this pass: **`arepo-before-final-runtime-acceptance-fix`**. All 8 acceptance items
Pass (see `docs/FINAL_RUNTIME_ACCEPTANCE.md`). Real-browser verified, not just unit tests.
- Popover: capped max-width applied BEFORE getBoundingClientRect measure → reveal width == measured
  width; visualViewport-aware; clamped ≥12px; right edge at 574px = 562 (= 574−12).
- Overflow 632→574 at 574px: TopBar wrap, SignalItem link truncate, sr-only table→div; scoped clip on
  synthetic-demo subtree only (not a global mask).
- Action row: badge own item, 12.8px gap, 32px padded toggle, 8px wrap.
- Replay: real 6h cohort primary + banner (frozen 01:24:13Z / scheduled 00:00Z / 84min late);
  synthetic moved to its own tab; `?replay=prospective` → real research.
- Market routes: geist error was stale `.next`; clean build+dev proven; `dev:clean` added.
- API polling: single shared backoff poller; no console flood; auto-recovers.
- Tests: backend pytest 359 + ruff clean; frontend tsc/lint clean, vitest 40, build clean; Playwright
  **79 passed**. DB preserved (60-market 6h cohort intact). Deployment NOT triggered.

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

**Final pre-deployment repair & launch readiness (branch
`arepo-final-predeployment-launch-readiness`, safety tag
`arepo-before-final-predeployment-launch-readiness`).** Preserves all edge-research work from 5e2ce9f.
Gates: **backend 351 pass, ruff clean; frontend tsc/lint clean, 37 vitest, build 16/16.** DB at
schema v3.

DONE + committed:
- §2/§3 BLOCKING schema failure fixed: additive metadata-diff migrator (`storage/migrate.py` +
  `migrate_cli.py`), SQLite+Postgres, idempotent, schema_migrations version, preflight, bootstrap
  auto-migrates. Real DB migrated 0→3; the blocked 6h freeze now works. 5 migration tests.
- §4 atomic freeze (explicit rollback) + incomplete-cohort detect/repair + `research-repair`. Tests.
- §5 honest universe degradation: exclusion funnel + assess_universe guard (reject/degrade) +
  cohort excluded_markets/degraded columns + status exposure. Tests.
- §6/§7/§8 frontend: viewport-aware portal Popover primitive (MetricHelp+TagChip) + overflow-x:clip
  + action-row spacing. 16 pure positioning tests; live-verified (portal/fixed/inside-viewport/no
  overflow) + screenshot.
- §11 hosting decision (Render+Supabase+Vercel primary); §12 keep separate crons (orchestrator
  fallback only); §13 render.yaml preDeployCommand migrate + scripts (preflight/verify/health) +
  deployment docs; §15 production-equivalent dry run PASSES headless.
- §9 local acceptance doc; §16 exact 39-step USER_DEPLOYMENT_CHECKLIST; §17 goal refined.
- §18 reviewers COMPLETE (2 independent subagents): production-architecture+provenance = CLEAN
  (1 LOW doc fix); DB/migration+operational-adversary = 6 findings (3 CRITICAL, 2 MAJOR, 1 MODERATE)
  ALL FIXED + tested (web-tier now migrates via init_storage; repair TOCTOU guarded; concurrent
  upgrade advisory-locked + duplicate-tolerant; single model list; callable JSON defaults rendered;
  concurrent-freeze graceful). CRITICAL-1 verified live (API logs "storage initialised (schema
  current)"). Reviews: docs/predeploy-architecture-review.md, docs/predeploy-db-adversary-review.md.

Final gates: **backend 355 pass, ruff clean; frontend tsc/lint clean, 37 vitest, build 16/16.**
Branch pushed (HEAD 5d355c2). All completion-gate items met.

**Exact next action:** NONE local. The user follows docs/USER_DEPLOYMENT_CHECKLIST.md (Supabase +
Render blueprint + env group + Vercel) to deploy; the release command migrates and the crons then
collect real prospective evidence automatically with no browser.

## (superseded) Current phase

**Edge-research infrastructure (branch `arepo-edge-research-infrastructure`, safety tag
`arepo-before-edge-research-infrastructure`).** Building the measurement engine that freezes real
prospective predictions before outcomes and measures them after execution costs. Preserves all
fixes from 14729d7. Gates: **backend 338 pass, ruff clean; frontend tsc/lint clean, 21 vitest,
build 16/16.** Baseline `docs/edge-research-infrastructure-baseline.md`; goal
`docs/EDGE_RESEARCH_GOAL.md`.

DONE + committed (not yet pushed at this checkpoint — push next):
- Research schema (`research_models.py`): `research_cohorts` (unique cadence,cutoff),
  `research_entries` (FULL universe, roles, all cut-off fields incl RP + per-family directions +
  walk-forward partition), `research_forward_observations` (rich, causal), `research_revisions`.
- Engine (`research_engine.py`): cadence snap, 5-class classification, full-universe role
  assignment, idempotent freeze; `screen_universe` live. Outcomes (`research_tracking.py`):
  causal 1h/6h/24h/7d collection with the predates-freeze guard; resolution upsert; backlog.
- Execution (`execution.py`): depth-aware slippage + spread + fees; midpoint vs executable.
- Analysis (`research_analysis.py`, `research_predictors.py`): 10 baselines incl OB-only/flow-only/
  no-momentum, 9 ablation variants, edge_verdict (10 criteria, conservative). Walk-forward
  (`research_walk_forward.py`) + calibration guard (`research_calibration.py`).
- Service + CLI + API (`research_service.py`, `research_cli.py`, `api/routes/research.py`):
  `/api/research/status|horizon/{h}|edge`; CLI `research-freeze --cadence`, `research-forward`,
  `research-resolve`, `research-status`. Frontend Replay "Edge-research status" section.
- `render.yaml`: 4 research crons (freeze 6h/daily/weekly at boundaries + forward every 20 min).
- Tests: 27 research tests incl end-to-end dry run + causal guard. Docs: baseline, goal,
  architecture-review, requirement-traceability, end-to-end-dry-run, dayyan-review.
- Live dry run (throwaway DB): froze 3 cadences from the real 60-market universe; API serves real
  status; edge = NOT supported (minimum sample not met). Reviewers (quant/ablation/walk-forward,
  provenance/execution, adversarial) running.

Reviewers complete (3 subagents: quant/ablation/walk-forward, provenance/execution, adversarial) +
provenance/execution + Dayyan functional. All confirmed critical/major findings FIXED (execution
zero-depth, no_change baseline, walk-forward read-path enforcement, thresholds fail-safe, cross-
cadence dedup, provenance immutability, executable-sample gate, and the honest beats-momentum-by-
construction note). Branch PUSHED (HEAD f775d67). Deployment handoff in
`docs/edge-research-deployment-handoff.md`. Final gates: backend 339 pass, ruff clean; frontend
tsc/lint clean, 21 vitest, build 16/16.

**Exact next action:** none local. The user follows `docs/edge-research-deployment-handoff.md` to
create Supabase Postgres + Render, set env vars, enable the 4 research crons, and run the first
freeze at a 6h boundary; then real prospective evidence accumulates automatically. Edge stays
not-supported until the predeclared minimum sample exists (and, given direction==momentum, a
directional edge over momentum needs a future model change, documented honestly).

## (superseded) Current phase

**Signal Intelligence & Replay functional validation (branch
`arepo-signal-replay-functional-validation`, safety tag
`arepo-before-signal-replay-functional-validation`).** Independent reviewers A–G run; Opus
synthesised; confirmed fixes implemented, re-reviewed and accepted. Gates: **backend 320 pass, ruff
clean; frontend tsc/lint clean, 21 vitest, `next build` 16/16**. Baseline in
`docs/signal-replay-functional-baseline.md`; acceptance in `docs/DAYYAN_SIGNAL_REPLAY_ACCEPTANCE.md`.

Confirmed + fixed (committed + pushed): D-SR1 one reliability confidence on every surface (Signal
Lab, Market Detail incl. per-outcome cards, Board), no 100% (D-SR6 cap 0.95); D-SR2 flat-aware
evaluation across reconstructed Replay AND the prospective cohort pipeline (flat ≠ miss); D-SR3
z-score materiality floor; D-SR4 reconstructed reproducibility (UTC-day snap) + hard-survivorship
honesty + `/cohorts/latest` excludes synthetic; D-SR5 momentum-agreement diagnostic + honest
Brier/log-loss N/A. Corrected volume_acceleration (live-available, warms up; restored to
completeness). Reviewer docs: signal-replay-quant-review, replay-point-in-time-data-matrix,
signal-system-implementation-review, signal-replay-adversarial-review (+ re-review),
signal-replay-final-qa (accept-with-minor, minors fixed), dayyan-signal-replay-review,
replay-trust-review; plus signal-component-register, synthetic-replay-decision,
signal-replay-cross-surface-contract (+ test_cross_surface.py). DECISIONS D-SR1..D-SR6.

**Exact next action:** none required for the pass. Optional future work: accumulate prospective
cohorts via the weekly freeze (needs the backend cron over weeks); manual zoom checks; deployment
when accounts exist. If resumed, read this file + AREPO_SIGNAL_REPLAY_FUNCTIONAL_VALIDATION_PROMPT.md.

## (superseded) Current phase

**Final local implementation (branch `arepo-final-local-implementation`).** Gates: backend 309
pass, ruff clean; frontend tsc/lint clean, 21 vitest, build compiled. Browser-verified against a
running backend(:8012)+frontend(:3012). Acceptance in `docs/DAYYAN_FINAL_LOCAL_ACCEPTANCE.md`.

PASS (committed + pushed): §3 critical routing (IDs 2694364/2822017 open in any mode; canonical
`LiveSource.get_market` + `market_detail` fallback; ?mode= context; rich MarketRouteError; doc +
5 tests); §4/§5 footer-follows-content + compact error card; §8 full-width nav; §9 title exactly
"Arepo"; §6/§7 Signal Lab directional filter+sort (URL) + direction-in-words (arrangeSignals +7
vitest); §10 hidden-scrollbar Learn menu; §11 auth one-viewport + nav-style wordmark (PNG removed);
§2 baselines (added current-implied + price-only) + reconciliation doc; §18 Replay data-status
endpoint+section; §19 Replay default = reconstructed "last week's opportunities" (no stale
synthetic); §16 cut-off persists in URL.

NOW ALSO PASS (committed + pushed since): §14 Replay point-in-time RP-at-cut-off + close-date +
time-remaining per row; §16 closing-soon lens (URL ?closing=); §13 docs/replay-product-review.md;
§20 prospective/reconstructed/synthetic definitions block. All Replay items §12-20 complete.

ONE PARTIAL remaining: §21 zoom checks at 80/90/110/125/150% - the browser tooling cannot change
page zoom, so this needs a manual pass (100% verified; shell uses vh/flex + fluid width that scale
with zoom).

BLOCKED: §23 deployment (Vercel/Render/Supabase/Resend) - not started by design until local
acceptance fully passes; external accounts required. This is the next phase.

**Exact next action:** a human manual zoom check at 80-150% (§21), then begin deployment (§23)
following docs/deployment.md when the external accounts are created.

## (superseded) Current phase

**Final local implementation (branch `arepo-final-local-implementation`, tag
`arepo-before-final-local-implementation`).** Browser-verified against a running backend+frontend.

DONE + committed + pushed:
- §3 CRITICAL routing bug fixed: `LiveSource.get_market(id)` + canonical fallback in
  `market_detail` so any valid market opens regardless of mode; IDs 2694364/2822017 verified;
  frontend ?mode= context + rich MarketRouteError card; docs/market-routing-investigation.md;
  5 hermetic tests (8f7b31f, 935ceee).
- §4/§5/§8/§9: footer follows content (removed main flex-1), full-width nav, tab title exactly
  "Arepo"; browser-verified gap-below-footer=0 (33ba7df).
- §6/§7: Signal Lab directional-status filter + sort (URL-persisted, no 40+/70+); direction in
  words; arrangeSignals + 7 vitest (5ce2e26).

State: backend 308 pass, ruff clean; frontend tsc/lint/build clean, 21 vitest. Servers running
on :8012 (backend, DEFAULT_MODE=replay, CORS 3012) and :3012 (frontend).

TODO (no external accounts needed): §2 report reconciliation (baselines: add current-implied +
price-only; canonical replay table; component-availability report; edge-wording audit); §10-11
Learn menus hidden-scrollbar + auth one-viewport (§11 says use nav-style wordmark, NOT the
black-bg PNG); §12-20 Replay (default "last week's opportunities" with point-in-time fields;
requested baselines; closing-soon lens URL; Replay data-status section; fix stale synthetic
cohort date -> Demo; mode definitions); §21 docs/DAYYAN_FINAL_LOCAL_ACCEPTANCE.md; §22 tests;
§23 final report.

**Exact next action:** §2.1 add current-implied + price-only baselines to evaluation/replay_stats.py
(order-book-only cannot be reconstructed historically - document why), then §19 synthetic-date fix
and §18 Replay data-status.

## (superseded) Current phase

**Final gap-closure (branch `arepo-final-gap-closure`, from tag `arepo-before-final-gap-closure`
@ 3de24b3). COMPLETE for all locally-achievable work; deployment Blocked on external accounts.**

Gates: backend **303 pass**, ruff clean, idempotent bootstrap; frontend tsc + lint clean, **14
vitest**, production build compiled. Baseline in `docs/final-gap-baseline.md`; Dayyan acceptance in
`docs/DAYYAN_ACCEPTANCE.md` (no Fail; deployment items Blocked with exact steps).

Done + committed + pushed:
- §3 broken "Full definition" link removed (105f5d7).
- §8 confidence penalised for missing components; live max 1.00→0.80, %100 10%→0% (d16bd43).
- §9 microstructure series wired into the LIVE path (was 0/40); honest reasons; `/diagnostics`;
  audit doc (3ade25f, f2897a7).
- §5 replay regression investigated (inconclusive both ways); `replay_stats` + tests (c4ef4ae).
- §6/§7 Replay funnel + baselines + top-5 + 5 cut-offs + inconclusive banner (78dce65, e48f4eb).
- §11 How It Works left-nav (shared SectionMenu) + smaller cards; Methodology too (468f7ed).
- §12 sign-in/up/reset brand showcase with the supplied wordmark (3469584).
- §14 data-consistency checks + invariant guard (b17518b).
- §10 URL-state helpers extracted + 6 vitest (1cb8a43).
- §13/§4 shared directional gate; Signal Lab qualify/why (7b6ea73).
- §2/§15/§18 review docs, final architecture, Dayyan acceptance (b32a9e8).

Blocked (external accounts only, exact steps in docs/deployment.md + final report): §16 live
Vercel + Render deployment, production login/email/schedules, live URLs. All deployment CODE and
config (render.yaml, vercel.json, Resend provider, crons) is done.

**Exact next action if resumed:** nothing local remains; on the user creating Supabase/Render/
Vercel/Resend accounts, follow docs/deployment.md to deploy and run the §16 end-to-end production
test. Optional future research (not blockers): outcome-based confidence calibration curve,
immutable historical universe, resolution-target baselines (see docs/quant-final-review.md).

## (superseded) Current phase

**Final gap-closure (branch `arepo-final-gap-closure`, from tag `arepo-before-final-gap-closure`
@ 3de24b3).** Baseline in `docs/final-gap-baseline.md`.

DONE + committed + pushed (backend 296 pass, ruff clean; frontend tsc/lint/build clean, vitest 8):
- §1 baseline recorded.
- §9 (commits 3ade25f, f2897a7): wired the microstructure snapshot series into the LIVE enrich
  path (was 0/40 present; now ~12/16 once a series accumulates); honest missing-component reasons
  in Signal Lab (no bare dashes); `GET /api/opportunity/diagnostics`; `docs/component-availability-audit.md`.
- §8 (d16bd43): confidence now falls when microstructure components are missing (component
  completeness factor). Live before/after: max 1.00→0.80, %==100% 10%→0%, median 0.76→0.52. Tests.
- §3 (105f5d7): removed the broken "Full definition" tag link (anchors trade-flow/wallet-
  concentration/trade-timing don't exist); verified all 18 MetricHelp links resolve.
- §5 (c4ef4ae): `docs/replay-regression-investigation.md` (both samples are inconclusive noise,
  keep causal behaviour); `evaluation/replay_stats.py` (sample_verdict, Wilson CI, causal
  baselines) + 6 tests.

IN PROGRESS / NEXT (no external account needed): §6 Replay top-5 + funnel + baselines wired into
the screen response and the Replay page; §4/§13 unified gates + Signal Lab qualify/why fields;
§14 data-consistency checks; §10 filter browser tests; §11 How It Works left-nav; §12 sign-in
brand showcase (design-assets/brand/AREPO Typeface (word).png); §15 final-production-architecture
doc; §16-17 deployment; §2 quant+beginner review docs; §18 Dayyan acceptance retest; §20 report.

**Exact next action:** wire momentum_direction + reconstruction funnel + baseline comparison
(replay_stats) into `evaluation/historical.py` HistoricalScreen and the `/api/historical/screen`
response, then rebuild the Replay page (top-5, funnel, modes, inconclusive labels).

## (superseded) Current phase

**Directional Evidence, Replay & Deployment (branch `arepo-directional-evidence-deployment`,
from the completed `arepo-product-simplification`; safety tag `arepo-pre-directional-evidence`).**

Read `research-references/deep-research-report.md` in full (Opus + independent Sonnet reviewer)
before any model change. Progress by spec section:

DONE and committed/pushed (backend 286 tests pass, ruff clean; frontend tsc/lint/build clean):
- §2 research paper audit -> `docs/research-paper-evidence-audit.md` (adopted vs deferred).
- §3 directional-rarity diagnosis -> `docs/directional-diagnosis.md`; root cause is data
  availability (flat 30-min windows -> zero-variance z-score), not thresholds.
- §3/§6 model fixes: z-score scored against a baseline EXCLUDING the current obs (with a signed
  `flat_baseline_move` so flat-then-jump yields a directional reading); confidence redesigned as
  estimated reliability = data_quality x evidence corroboration (no more 100% spike). (DECISIONS
  D2-D4.) `movement_1h` renamed `recent_movement` (report: mislabelled).
- §4 selective Opportunity Board: `view` = directional (default) | strongest | inconclusive | all;
  honest "screened N; M directional" counts + note; Explore keeps the neutral universe.
- §7 missing components: microstructure snapshot store + pure change functions + idempotent
  collection + enrich wiring + a test proving each component can move the composite; a UTC cron
  collects the series. Historical stays price-only.
- §9 filter persistence: `useUrlState`; board (view/horizon) and all markets filters + search live
  in the URL, restored on Back/Forward/refresh/shared links.
- §10 market model view gate unified with the backend evidence rule.
- §16-20 deployment prepared: Resend provider (§18), `render.yaml` (web + 7 UTC crons, §19),
  `vercel.json`, asyncpg, `docs/deployment.md` (Supabase pooler, cross-site cookies, Resend limits,
  deployed e2e checklist). Stops at external-account creation; no secrets committed.

DEFERRED (not started; no external account needed — resume here on "carry on", in priority order):
1. §12-13 Replay redesign: default "had I followed Arepo's top five qualifying views at the time"
   with time-of-signal evidence; Top 10/15 for research; baseline comparisons (no-change, price-
   only, momentum, order-book-only, implied) with Brier/log loss; honest no-edge reporting. (Note:
   provenance separation §11 and no-look-ahead already hold from prior work; this is the UX + the
   baseline-evaluation harness for §5.)
2. §8 data-consistency warnings (contradictory end_date / close state / resolution).
3. §14 How It Works left-nav redesign (like Methodology).
4. §15 sign-in / brand page using design-assets/brand/AREPO Typeface (word).png (preserve the red
   mark under the A); remove "Why Arepo" from result pages.
5. §5 full baseline metrics table + operating-point doc (coverage, precision by band, FPR, Brier);
   depends on the §13 harness.
6. Browser tests for filter restoration (§9/§21) - no browser-test harness in repo yet.
7. §7 follow-up: thread the snapshot-derived `changes` into the live board-build enrich path (the
   infra + cron are done; board build does not yet read the series per token).

**Exact next action:** implement §12-13 Replay Top-5 + baseline-comparison harness (backend
evaluation baselines + frontend Replay default), which also yields the §5 metrics. Then §8, §14,
§15. Commit each; push; then update FINAL_STATUS and the final report.

## (superseded) Current phase

**Product Simplification, Accounts & Decision-Support (branch `arepo-product-simplification`,
from pushed `arepo-opportunity-alerts`). ALL 7 PHASES COMPLETE and committed.**

Phases 5-7 added since the notes below: Phase 5 (32f0cd3) per-user verified/opted-in alerts on
top of a quality floor + user-dry-run CLI + 10 tests; Phase 6 (c731fa3) board
stale-while-revalidate cache (warm hit ~2ms vs ~6.1s cold build) + 4 tests + docs/performance.md;
Phase 7 (523285e) docs (authentication, accounts-privacy, methodology §9c/§9d, API, README,
FINAL_STATUS, limitations) and live-verified price-only historical reconstruction. Final state:
backend 268 tests pass, ruff clean, idempotent bootstrap; frontend tsc/lint/build clean (16
routes). Post-implementation review done (§17): market-detail Current-model-view lead added
(a34d3ab); two genuine review findings fixed (stale confidence docstring, TagChip ARIA) in
7c562c8; the review's alerts/cache FAILs were against a stale checkout and are false (both are
implemented and tested). Brand story confirmed in How It Works (Learn), not on result pages (§4).
PASS COMPLETE; final push done.

Original phases 1-4 notes:

Done and verified:
- Phase 1 (commit f587fb0): two Sonnet reviews (beginner + quant) synthesised in DECISIONS
  P0-P3; statistical-integrity fixes (confidence decoupled from strength; freshness penalty
  wired through; unimplemented cross_market family removed).
- Phase 2 (82435fb): computed statistical hypothesis with honest insufficient-evidence state;
  Opportunity cards lead with the hypothesis + direction and demote Research Priority to a
  labelled chip; accessible TagChip popovers; time-to-close filter; Signal Lab consolidated to
  one signal per market (no duplicate Yes/No); nav renamed.
- Phase 3 (8c72096): accounts backend, native fastapi-users (DECISIONS P3, NOT Supabase).
  Register/verify/login(verified-only)/logout/reset; argon2 + JWT httpOnly cookie; schema
  users/alert_preferences/saved_markets/alert_deliveries/account_deletions; per-user isolation;
  per-IP rate limiter; .env.example; 10 tests. Runs fully offline (console email sink).
- Phase 4 (e6f8c64): accounts frontend (signup/signin/forgot/reset/verify/account with alert
  settings), auth context, verification link visible via console sink. Live lifecycle smoke
  passed: register -> verify -> login -> me -> prefs -> save -> delete -> 401.

State: backend **254 tests pass**, ruff clean; frontend tsc/lint/build clean (15/15 routes).
New backend deps: fastapi-users[sqlalchemy], pwdlib[argon2], pyjwt (pinned in pyproject +
requirements). AUTH_SECRET has a dev default and MUST be set in production; external email stays
disabled (console sink) until provider creds are configured.

**Exact next action (Phase 5):** connect the existing alert engine (`astrolabe/alerts/service.py`)
to per-user preferences: only verified + opted-in users, honouring min Research Priority, min
confidence, categories, short-term/max-hours, pause, unsubscribe, global disable; write per-user
`alert_deliveries`; dedup + cooldown + retry; correct disclaimer, no personalised advice. Add
tests (§16 Alerts). Then Phase 6 (performance: cache the 6.13s/202-request board build) and
Phase 7 (Replay price-only reconstruction via CLOB /prices-history + docs + push).

## (superseded) Current phase

**Opportunity Intelligence & Alerting pass COMPLETE** (branch `arepo-opportunity-alerts`,
from the pushed `arepo-signal-refinement` at 77ec2b3). Delivered and verified: trade-flow/
wallet/timing indicators (analytics/flow.py) over the public Data API `/trades`; Research
Priority score + evidence families + tags (opportunity/scoring.py); Opportunity Board
(/api/opportunity/board + home page) with Explore Markets retained + Signal Lab deep
analysis (DECISIONS O1); full-universe search + company/ticker aliases (Microsoft/MSFT);
daily immutable snapshot (idempotent CLI + routes); provider-neutral research email alerts
(console sink default, external disabled, dedup/cooldown/history/retry/test-mode).

Verified: backend **236 tests pass**, ruff clean, migrations/bootstrap idempotent; frontend
tsc/lint/build clean (10/10). Browser-verified the Board home, restructured nav, and the
MSFT full-universe search (returns the 36 real Microsoft markets with alias expansion).
Screenshots in docs/screenshots/arepo-opportunity-board.jpg. Docs updated (methodology §9b,
API, limitations + data provenance/privacy, alert-configuration, README, FINAL_STATUS,
architecture). External email sending stays disabled pending the user's provider credentials.

## (previous) Current phase

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
