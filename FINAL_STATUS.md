# FINAL_STATUS

## Production deployment + multi-agent final scrutiny (branch `arepo-free-production-v1`)

_Governing spec: `AREPO_PRODUCTION_DEPLOYMENT_FINAL_MASTER_PROMPT.md`. Safety tag
`arepo-verified-predeploy-2026-08-08` (= `8a6a1ae`) untouched; local DB + backups untouched; all
staging/benchmarks ran on a COPY DB._

**Multi-agent scrutiny.** 8 parallel Sonnet reviewers were launched; all were terminated by a session
usage limit before writing reports. The Opus lead then conducted the eight-dimension review directly
(stated in `docs/final-review/00-review-method.md`) — reports 01–08 + `FINAL_REVIEW_SYNTHESIS.md`. No
Critical/launch-blocking defect. Verdict **ship-with-fixes**.

**Verdicts:** quant/research — *technically legitimate but evidentially immature* (2 cohorts; 73%
unavailable at 1h/6h; **no edge claimed, correctly**). security — *ship*, no High/Critical. reliability
— *ship-with-fixes* (document Supabase 7-day idle pause + Actions jitter; no logic defects).
data-integrity — *ship-with-fixes* (added migration value-verification). UI — *startup→production-quality*.
beginner — usable; fixed Strength-not-probability copy. market-user — useful curated scanner; wants the
long-term selected-vs-wider scoreboard. portfolio — *strong, upper-tier graduate project; avoid edge
claims*.

**Fixes made because of the reviews:**
- **Cadence 6h → daily,weekly** (D-DEP7): a sample-independence decision (6h re-froze the same ~1,400
  markets 4×/day → dependent pseudo-replication). Prospective only; existing cohorts untouched. Free
  hot-Postgres lifetime ~3–5 wk → **~4 months**.
- **Migration per-record value verification** (D-DEP8, spec §10): `import_sqlite._verify_values` fails
  reconciliation on any missing/mismatched immutable value (not just counts). +1 regression test.
- **Beginner honesty:** "Strength is a signal-intensity score, not a probability of being correct"
  (`metrics.ts` + `StrengthMeter` title).
- **Deferred (documented, no evidence lost):** long-term Replay aggregate summary (D-DEP9) — retention
  never deletes cohorts/observations, so all detail stays hot ~4 months; specified with the
  market-dedup invariant for when cohorts approach archive age.

**Acceptance gate:** backend **439 pytest + ruff clean**; frontend **tsc/lint clean, 86 vitest, build
15 routes**; Playwright **103/104** on the 2-day-old staging snapshot — the 1 failure
(`replay.spec.ts:46`) requires a *future-due* horizon that a stale cohort can't present; re-running
against a freshly-dated cohort (copy DB) **passes → effectively 104/104**. No test/code weakened.

**Not done (needs Dayyan):** the live cloud deployment (Supabase/Render/Vercel/GitHub secrets/Resend/
domain) + live migration/scheduler/provider acceptance — external accounts + secret placement. Guide:
`docs/FREE_PRODUCTION_DEPLOYMENT.md`.

---

## Free-production deployment prep (branch `arepo-free-production-v1`)

_A deployment/infrastructure/persistence pass — **no product redesign**, no signal formula / threshold
/ confidence / Research Priority / eligibility / frozen value changed. The verified baseline tag
`arepo-verified-predeploy-2026-08-08` is untouched (= HEAD before this pass). No merge to main, no
external infrastructure deployed, local `backend/astrolabe.db` and backups untouched._

**Architecture chosen** (deviating from the starting hypothesis where measured evidence supported it):
Vercel (frontend) → Render Free (API, serves persisted results only) → Supabase Postgres; and
**GitHub Actions** running one idempotent tick for all scheduled compute + a daily pg_dump backup —
replacing Render's **paid** cron jobs to keep the system £0. Evidence: a complete scan measures
269–302 s / ~250–400 MB peak, which does not fit comfortably in Render Free (512 MB), so heavy work
belongs on Actions runners; the API never rebuilds the universe in a request.

**What shipped this pass:**
- `astrolabe/scheduler/` — idempotent due-work tick (`tick.py`), DB lease + state (`state.py`,
  `models.py`), category-C retention + storage-health (`retention.py`), pluggable archive (`archive.py`).
- `astrolabe/storage/import_sqlite.py` — read-only, dry-run, idempotent, self-reconciling SQLite→Postgres
  importer (fails non-zero unless per-table counts + every frozen cohort's `entries==universe_size` match).
- `.github/workflows/scheduler.yml` + `backup.yml`; `render.yaml` now free API-only (no paid crons).
- `/admin/health` (token-guarded observability); `Settings.production_issues()` startup validation.
- Frontend restrained cold-start "Connecting to Arepo data…" (`useAsync` + `ErrorState`); status poller
  path unchanged.
- Docs: `PRODUCTION_CAPACITY_AUDIT.md`, `FREE_PRODUCTION_DEPLOYMENT.md`, `PRODUCTION_ROLLBACK.md`;
  `DECISIONS.md` D-DEP1..6.

**Storage reality (measured, honest):** category-C scan history is a bounded rolling window (2 days
fully preserves trajectory ≤6h + market-detail ≤200 rows/market). The real long-term driver is
permanent research (~12 MB/day). **Free 500 MB Postgres safe lifetime ≈ 3–5 weeks** as-is; extend via
lower cohort cadence (~3 months), compressed R2 cold archive (indefinite, lossless), or Supabase Pro.
Storage health warns at 80%/92% so the DB never silently fills.

**Verification (this environment):** backend **436 pytest pass + ruff clean** (1 pre-existing flaky
timing assertion in `test_api.py` passes on re-run, unrelated to this pass); frontend **tsc + lint
clean, 86 vitest, production build 15 routes**; **Playwright 53 passed / 0 failed** against the real
backend (copy DB) incl. both disconnected-API recovery specs. SQLite→Postgres importer validated
SQLite→SQLite end-to-end (a live
Postgres is unavailable in this environment; the PG paths are covered by DDL-portability + dry-run/
reconcile in the deploy guide — a known limitation).

**Next external step (user):** follow `docs/FREE_PRODUCTION_DEPLOYMENT.md` from Step 1 (create Supabase).

---

## Final short-horizon completion (branch `arepo-final-short-horizon-completion`)

_Verified in this environment: backend **415 tests pass**, ruff clean; frontend tsc/lint clean, **86
vitest**, production build **16 routes**; **Playwright 104 passed** against the real backend (:8000)
and the preserved local database (:3000). Manually verified in Chromium (Opportunities, Signal Lab,
Replay, market detail, sign-in). Historical cohort preserved exactly: 60 entries / 19 directional (10
public + 9 shadow) / 120 forward observations._

This pass finishes the product around the complete short-horizon universe without changing any signal
formula, threshold, confidence, Research Priority, evidence family, eligibility rule or frozen value,
and without touching the historical cohort.

**Honest short-horizon lifecycle (§10-11).** The forward collector no longer leaves a market that
closed before its horizon came due ambiguously "pending". When the market's close precedes both the
horizon target and the collection time, `collect_due_forward` records a *terminal* closed-before-horizon
observation with **no live post-close fetch** (freeze-to-close is then the correct evaluation), and
reports it via a new `closed_before_horizon` count. Closed-awaiting-resolution, Resolved, Invalid and
Cancelled stay distinct from pending. A new timing test proves no live fetch fires for a closed market
and that terminal closed observations carry no midpoint. The genuine collector was run so the 6h
horizon reconciles exactly (denominator identity: expected + against + no-change + pending/unavailable
= total; real 6h Opportunities-scope cohort = 16 + 13 + 1 + 50 = 80).

**Replay, results-first.** Replay answers one question — "How did Arepo's past signals perform?" —
within seconds: the big Moved-as-expected / Moved-against / No-change / Pending-unavailable counts and
a plain "X% of markets that moved went in Arepo's recorded direction" sentence come first; controls
come second. Horizon is a single click on segmented tabs `[1h][6h][24h][7d][To close][Resolved]`, with
due-but-uncollected horizons labelled "· pending" and the newest cohort that has evaluable results
auto-selected. A closing-window pill row and an `[Opportunities][All signals][Research comparison]`
scope control replace the old dropdowns; the public/shadow research panels appear only under Research
comparison. Cohort mechanics are collapsed behind "Previous cohorts", each market is a concise row with
a "View details" disclosure, and the six-zero-cards pending state is gone. Freeze-to-close, final
resolution, executable performance and signal evolution remain separate. Two typed deterministic
server endpoints back it; all replay logic is unit-tested (`lib/replay-ux.ts`).

**Cards a new user can read.** Opportunities and Signal Lab cards now carry human-readable Priority
(High/Medium/Low), Confidence and Evidence chips through a shared accessible `InfoChip` that opens a
plain-English tooltip on hover, focus or tap. Evidence families are shown as friendly labels (Price
behaviour, Order-book pressure, Trade activity, Concentrated trading, Trade timing) — never the raw
`order_book` / `trade_flow` keys — and only evidence the backend genuinely computes is exposed. The
trade-concentration family is described neutrally with no wallet-identity or fresh-wallet claim. Only
genuine movement trajectory labels appear on cards; per-card Stale/Fresh clutter and the "Also shown
in Opportunities" badge are removed, while full staleness detail is preserved on the market-detail
history where it is genuinely informative (progressive disclosure, no functionality removed).

**Real Playwright fixes.** The `action-spacing` and `popover` acceptance specs were failing because
they navigated to a hardcoded market that had since closed and stopped rendering the components. They
now resolve a live market with signals at runtime, expand the collapsed per-signal breakdown, exclude
the non-tooltip detail toggle from the popover-trigger selector, and only click visible triggers —
fixing the real product/target problem, not relaxing the assertions. Not deployed; not merged to
`main`. Details in `CHECKPOINT.md`, `DECISIONS.md`, `TASKS.md`.

---

## Complete short-horizon universe (branch `arepo-complete-short-horizon-universe`)

_Verified in this environment: backend **399 tests pass**, ruff clean; frontend tsc/lint clean, **68
vitest**, production build 15 routes; **Playwright 77 passed** against the real backend (:8000) and
the preserved local database (:3000)._

The core correction: Arepo no longer scans only the first 60 markets. **Proved** the old cohort's 60
came from three compounding hard caps (`discovery_limit=60` on a single unpaginated `/events` page,
`screen_universe(universe_limit=60)`, and an `enrich_markets` `[:60]` slice) with no pagination at
all, so previous discovery was truncated (`docs/complete-universe-discovery-audit.md`). This pass adds
real, verifiable offset pagination that follows every page until the upstream signals completion and
**fails loudly** when it cannot (the live Gamma offset path caps at 2100 and keyset is non-functional,
so a real scan honestly reports incomplete rather than pretending). A backend 30-day eligibility gate
runs before scoring, every eligible market is assigned to a non-overlapping closing-time bucket, and
the complete eligible universe is analysed and ranked per bucket and overall; the public top ten is a
display flag over the preserved full universe. Immutable append-only snapshots
(`discovery_scan_runs`/`discovery_signal_snapshots`/`discovery_scan_locks`), an idempotent 5-minute
refresh command with an advisory lease, and a signal-strength trajectory (predeclared 0.02 stability
threshold; never probability language) complete the pipeline. Signal Lab was rebuilt signals-first
with the scan status, "Top 10 shown from N eligible markets", closing-universe and scope controls and
server-computed trajectory. A real live scan discovered 21 pages / 2100 raw / 181 eligible within 30
days / 83 directional in ~15-32s, and TWO real refreshes recorded into the preserved database (362
append-only snapshots) prove earlier snapshots are never overwritten. No signal formula, threshold,
confidence, Research Priority, evidence-family, baseline, ablation, walk-forward, edge criterion or
frozen value changed, and the historical 60-market cohort (60/19/10/9 + 120 forwards) is untouched.
Forward-looking and documented (not fully wired): future cohort freeze from the complete scan,
freeze-to-close collection, and the four-question Replay matrix over bucket cohorts. Not deployed; not
merged to `main`. Details in `docs/complete-universe-and-signal-lab.md`.

---

## Prospective Replay refinement (branch `arepo-prospective-replay-refinement`)

_Verified in this environment: backend **376 tests pass**, ruff clean; frontend tsc/lint clean, **58
vitest**, production build 15 routes; **Playwright 85 passed** against the real backend (:8000) and
the preserved local database (:3000). The real six-hour cohort's stored results were confirmed in the
real browser: public 2 expected / 2 against / 6 flat; shadow 2 / 2 / 5; combined 4 / 4 / 11._

The public Replay product is now prospective-only: real predictions genuinely frozen before later
prices became known. The reconstructed-analysis and synthetic-demonstration tabs were removed from
the public page (the underlying infrastructure is kept for internal use and tests); legacy `?replay=`
values normalise to the prospective page. The page was rebuilt around choosing a real frozen cohort
(cadence + freeze), an evaluation horizon (1h/6h/24h/7d/final, honestly pending when uncollected) and
a frozen time-to-close window (6h/24h/7d/30d/all), with a public-vs-all-directional scope control. A
prominent "Did the market move as expected?" section leads with the full count and never a
flat-excluding hit rate; where a hit rate is shown it is labelled "among markets that moved: 50% (4
of 8)". The market-by-market table shows frozen rank, midpoint movement, executable result (after
costs) separately, frozen time-to-close and colour-independent result labels; final resolution is
kept separate. Two typed, deterministic, server-side endpoints back it
(`/api/research/replay/cohorts` and `/cohort/{id}`). No directional logic, threshold, confidence,
Research Priority, eligibility, baseline, ablation, walk-forward, edge criterion or frozen value was
changed, and the database (1 real 6h cohort, 60 entries, 120 forward observations) is fully
preserved. The `render.yaml` research freeze/forward crons for all three cadences were already
correct and left unchanged. Not deployed; not merged to `main`. Details in
`docs/prospective-replay-refinement.md`.

---

## Directional Evidence, Replay & Deployment pass (branch `arepo-directional-evidence-deployment`)

_Verified in this environment: backend **286 tests pass**, ruff clean, idempotent bootstrap;
frontend tsc/lint/build clean (16 routes). The full research report was read before any model
change (Opus + independent Sonnet reviewer)._

Delivered (spec sections): **§2** research audit doc; **§3/§6** the z-score baseline-exclusion fix
(with a signed `flat_baseline_move` so flat-then-jump yields a directional reading) and confidence
redesigned as an estimated-reliability score that no longer saturates at 100%; **§4** a selective
Opportunity Board (directional-only default + strongest/inconclusive/all views + an honest
"screened N; M directional" line); **§7** a persisted microstructure snapshot store that makes the
three previously-empty change features computable (with a test proving each can contribute) plus a
UTC collection cron; **§9** URL-persisted filters (board + markets) restored on Back/Forward/
refresh/shared links; **§10** a market model-view gate unified with the backend evidence rule;
**§16-20** full Vercel + Render + Supabase + Resend deployment preparation (Resend email provider,
`render.yaml` with seven idempotent UTC crons, `vercel.json`, asyncpg, `docs/deployment.md`),
stopping at external-account creation with no secrets committed.

No component claims alpha; Research Priority remains a labelled heuristic (report §"Strict research
constraint"). Deferred to "carry on" (none require an external account): **§12-13** Replay Top-5
redesign + baseline comparisons and the **§5** operating-point metrics that depend on it; **§8**
data-consistency warnings; **§14** How It Works left-nav; **§15** sign-in/brand page; browser tests
for filter restoration. See `CHECKPOINT.md` for the exact next action.

---

## Product Simplification, Accounts & Decision-Support pass (branch `arepo-product-simplification`)

_Latest pass. Verified in this environment; backend 268 tests pass and ruff clean; frontend
tsc/lint/build clean (15/15 routes)._

Guided by two independent Sonnet reviews (a capable beginner and a prediction-market quant),
synthesised in `DECISIONS.md` P0-P3. What changed:

- **Decision-support redesign.** Every Opportunity card and the board lead with a computed,
  cautious statistical hypothesis (`opportunity/hypothesis.py`) with an honest
  insufficient-evidence state; Research Priority is demoted to a labelled High/Medium/Low chip;
  evidence tags explain themselves in an accessible popover (definition, why it matters, family,
  methodology link). A time-to-close filter (24h/3d/7d/all) focuses on short-term opportunities.
  Signal Lab now shows one signal per market (no duplicate Yes/No).
- **Statistical integrity (from the quant review).** Confidence is decoupled from strength
  (pure data-quality), removing a hidden strength-squared term in Research Priority; the
  freshness penalty is wired through; the declared-but-unimplemented cross-market evidence
  family was removed.
- **Free accounts** (native `fastapi-users`, not Supabase; `DECISIONS.md` P3 and
  `docs/authentication.md`): register, verified-email login, logout, password reset,
  preferences, saved markets, alert history, account deletion. argon2 hashing, JWT httpOnly
  cookie, per-IP rate limiting, per-user data isolation. Runs fully offline (console email sink
  prints the verification link). Verified end-to-end by a live lifecycle smoke test.
- **Per-user alerts.** The alert engine now targets verified, opted-in users, honouring each
  user's thresholds, categories, short-term preference, pause and unsubscribe, on top of a
  user-independent quality floor. Same honest, non-personalised copy with the research
  disclaimer for everyone.
- **Performance.** The Opportunity Board is served through a stale-while-revalidate cache
  (warm hit ~2 ms vs a ~6.1 s / 202-request cold build); `docs/performance.md`.
- **Replay** keeps prospective, reconstructed (price-only, from the official CLOB
  price-history) and synthetic results strictly separate, with no look-ahead (confirmed by the
  quant review and 22 passing historical/provenance tests).

**External setup still required:** a strong `AUTH_SECRET` and (for real email delivery) the
user's own SMTP/provider credentials; nothing is committed. Everything runs and is testable
locally without them.

---

# FINAL_STATUS: Arepo Master Final Refinement

_Truthful final status of the Master Final Refinement (branch `arepo-master-final`, from
safety tag `arepo-ui-v1`). Every claim below was verified by running the code in this
environment; commands and their actual output are given so a reader can reproduce them._

## Project summary

**Arepo** is a read-only prediction-market intelligence platform over public Polymarket data.
It ingests market discovery and order-book data (Gamma API, CLOB REST, CLOB market WebSocket),
normalises it through a strict typed boundary, computes transparent microstructure and
time-series analytics (implied probability, movement, rolling volatility, standardised
z-score, spread/midpoint, order-book imbalance, near-mid depth, a composite anomaly score with
confidence/data-quality), and serves them via a FastAPI backend to a Next.js/TypeScript
frontend. It has three explicit data modes, live, cached, replay, a deterministic
look-ahead-safe backtest over a committed synthetic dataset, and, added in this refinement, a
separate prospective weekly cohort evaluation engine. It never places trades and makes no
profitability claim.

## What this refinement changed

Grouped as requested, with the primary files for each area.

### Brand
- Faithful SVG reconstruction of the supplied 5x5 grid logo (`design-assets/brand/AREPO logo
  (no word).png`): second column and second row red, remaining cells outlined, adapted for the
  light-only identity (`frontend/components/Logo.tsx`).
- Documented that the earlier Phase 1 "convergence mark" concept, recorded in
  `docs/brand-system.md`, was superseded by the grid-mark reconstruction once the supplied
  asset was integrated directly.

### Typography
- Display heading font decision: **Jost** (SIL OFL, a Futura revival), vendored locally as
  static `.woff2` files (`frontend/app/fonts/`) and loaded via `next/font/local`
  (`frontend/app/fonts.ts`), used only for major titles, hero and section-intro headings, in
  uppercase with wide tracking. Documented explicitly as an approximation of the supplied
  wordmark, not an exact match, in `docs/brand-system.md`.
- Interface text and data values stay Geist Sans with tabular numerals throughout.

### Interface
- Navigation presence, active/hover states and logo/wordmark readability improved.
- The pale-red information panel (read as an error) replaced with a neutral information panel;
  Arepo red reserved for active nav, selected controls and genuine signal emphasis.
- Technical status labels (`REST`, `WS`, `age`) replaced with `API`, `Live feed`, `Updated`,
  each with an accessible tooltip and clear states (Connected, Updating, Delayed, Offline, Not
  available in this mode).
- Market detail readability: larger body text, clearer headings, progressive disclosure
  (`Show advanced market data`) for specialist metrics.
- Signal Lab terminology simplified: `Unusual market activity` as the surface label for the
  composite anomaly score, `Data coverage` and `Lookback` in place of raw identifiers,
  friendly component names, technical detail behind a disclosure.
- Methodology and How Arepo Works readability pass: larger text, KaTeX-rendered equations,
  plain-English summary before each formula, worked examples, anchored links from product
  pages.

### Data quality
- Chart repair: fixed timestamp handling so price-history points carry their real timestamps
  (or a synthesised, distinct axis when timestamps are genuinely absent) instead of collapsing
  to one point; visible line strokes and points for sparse data; a stated note when only
  limited history exists.
- Category, sport and competition filters (`GET /api/markets/facets`) built dynamically from
  the normalised market set, with no invented values and no `Unknown` placeholder; empty states
  where no markets match.

### Signals
- Composite anomaly score terminology, hierarchy and disclosures reworked per the brief
  (surface label, plain-English explanation first, technical detail and equations behind
  disclosure).

### Replay
- A new prospective weekly cohort evaluation engine (`backend/astrolabe/evaluation/`, 8 new
  tables, ranking/freeze/forward/resolution/portfolio logic, an idempotent CLI, and 4 new
  read-only API endpoints under `/api/cohorts/*`).
- The Replay page (`frontend/app/replay/page.tsx`) rebuilt to consume the cohort API: week
  picker, price-movement vs final-resolution views, entry-level "why this qualified"
  disclosures, a labelled hypothetical portfolio, and provenance notices distinguishing
  prospective, reconstructed and synthetic cohorts. The prior deterministic signal backtest is
  preserved underneath as a clearly labelled, separate demonstration.

### Accessibility
- Keyboard/touch-operable metric tooltips, a single themed focus ring, non-colour cues paired
  with colour throughout (verdicts, status), chart data alternatives, semantic headings,
  reduced-motion support carried through the refinement.

### Technical quality
- Backend test count grew from the 128-test baseline to **174 tests** (24 category/facet tests,
  3 chart-timestamp regression tests, 19 evaluation-engine tests, plus the pre-existing suite),
  all passing, `ruff` clean.
- Frontend gained a `vitest` unit-test runner (none existed at baseline) with **8 tests**
  covering chart row-building, all passing; `tsc --noEmit`, `next lint` and `next build` all
  clean.

## Migrations added

Eight new SQLAlchemy ORM tables, added to the shared `Base.metadata` (the project uses
`create_all`, not Alembic) and created idempotently by
`backend/astrolabe/evaluation/migrations.py::bootstrap`:

`calculation_versions`, `signal_snapshots`, `weekly_cohorts`, `cohort_entries`,
`ranking_audit`, `forward_price_observations`, `market_resolutions`, `evaluation_results`.

Defined in `backend/astrolabe/evaluation/models.py`. `bootstrap()` is safe to run repeatedly:
`create_all` skips existing tables, and the calculation-version row is upserted, not
duplicated.

## Commands added

`python -m astrolabe.evaluation.cli <command>` (`backend/astrolabe/evaluation/cli.py`), every
command idempotent and safe to run on a schedule:

```
bootstrap            create/verify the evaluation tables and calculation version
rank    [--mode]     update this week's provisional top ten from current signals
freeze  [--at]       freeze the cohort for a week at the cut-off
forward [--mode]     collect any due forward prices for frozen cohorts
resolve [--mode]     record newly-available market resolutions
evaluate             (re)compute the two evaluation views and portfolio values
seed-synthetic       build the labelled synthetic demonstration cohort
status               print the recorded cohort weeks
```

## Tests added

- **24 category/sport/competition facet tests** (`backend/tests/unit/test_categories.py`).
- **3 chart-timestamp regression tests** (`backend/tests/unit/test_service.py`:
  `test_history_points_preserve_real_timestamps`,
  `test_history_points_synthesise_distinct_axis_when_timestamps_absent`,
  `test_history_points_empty_when_no_data`).
- **8 frontend chart `vitest` tests** (`frontend/lib/chart-data.test.ts`).
- **19 evaluation-engine tests** (`backend/tests/unit/test_evaluation.py`), covering the 13
  guarantees required by the brief: provisional rankings keep only the strongest qualifying
  entries; a stronger signal replaces only the current lowest entry; ties are deterministic;
  frozen cohorts cannot be modified; later data cannot change an original ranking; losing
  entries remain stored; unresolved entries remain pending; repeated scheduler runs are
  idempotent; forward observations are not duplicated; resolution updates do not overwrite
  entry data; weekly summaries use correct denominators; simulated returns use only available
  entry information; and prospective, reconstructed and synthetic datasets cannot be mixed
  silently.

## Actual test results (verified in this environment)

```
cd backend && source .venv/bin/activate
python -m pytest -q
# -> 174 passed, 1 warning in 3.46s

ruff check astrolabe tests scripts
# -> All checks passed!
```

```
cd frontend
npx vitest run
# -> Test Files  1 passed (1)
#    Tests  8 passed (8)

npx tsc --noEmit
# -> clean (no output, no type errors)

npm run lint
# -> No ESLint warnings or errors

npm run build
# -> Compiled successfully; 9 routes generated
#    (/, /_not-found, /how-it-works, /icon.svg, /markets, /markets/[id],
#     /methodology, /replay, /signals)
```

Backend: **174 tests pass, ruff clean.** Frontend: **8 vitest tests pass; tsc, lint and
production build all clean.**

## Historical-data limitations

There is no reconstructed historical snapshot store on this machine. No earlier prospective
cohort has been invented or backfilled. The prospective evaluation engine correctly reports an
empty cohort history (`GET /api/cohorts/weeks` returns `[]`, `GET /api/cohorts/provenance`
reports `first_prospective_week: null`) until the first genuine `rank --mode live` run is
performed. A synthetic demonstration cohort can be seeded
(`python -m astrolabe.evaluation.cli seed-synthetic`) purely to prove the machinery works end
to end; it is visibly badged as synthetic wherever it appears and is never counted in real
prospective statistics. See `docs/limitations.md` and `docs/methodology.md` §12.

## First prospective cohort date

**None yet.** Real prospective tracking begins at the first `python -m astrolabe.evaluation.cli
rank --mode live` run on a given deployment; that command has not been run against a live
schedule as part of this refinement, so no real cohort week exists to date. This is stated
plainly rather than estimated or assumed.

## Scheduler status

Idempotent CLI commands for the full workflow (rank, freeze, forward, resolve, evaluate) are
implemented and documented in `docs/deployment.md`, including a worked GitHub Actions cron
example. **No paid or public external scheduler has been activated.** Activating GitHub
Actions, a hosting-provider scheduler, or cron against a real deployment requires the user's
own repository or hosting account and explicit approval; none of that has been done here.

## Manual browser checks still recommended

The following were not re-verified with a live browser session as part of writing this
documentation and should be checked manually before relying on them:

- Visual inspection of the Jost display font rendering against the supplied wordmark at
  various sizes (title, hero, report cover).
- Visual inspection of the reconstructed grid logo at favicon size (16px) and in the nav.
- The Replay page's empty state (no cohorts recorded) versus its populated state once
  `seed-synthetic` has been run, in an actual browser.
- Keyboard-only navigation through the Signal Lab and Replay disclosures, and screen-reader
  labelling of the verdict icons (good/bad/pending) on cohort entries.
- Mobile/narrow-viewport behaviour of the Replay portfolio table and week picker.
- Live-mode end-to-end exercise of the `rank` -> `freeze` -> `forward` -> `resolve` ->
  `evaluate` command sequence against real Polymarket data over an actual elapsed week (this
  cannot be verified faster than real time, by the design of the system itself).

## Deployment status

**Not claimed as deployed.** `docker compose up` and any public hosting push were not executed
in this environment (no Docker daemon, no `gh`/`vercel` CLI, no authenticated hosting account).
See `docs/deployment.md` for the exact commands an operator should run and verify
independently, and the new Scheduler section for how the weekly cohort workflow should be
wired up once a deployment exists.

## Localhost addresses

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000` (interactive docs at `/docs`, health at `/health`)

## Exact local start command

**Non-Docker (verified path):**
```bash
# Backend  (terminal 1)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn astrolabe.api.app:app --reload            # -> http://localhost:8000

# Frontend (terminal 2)
cd frontend && npm install && npm run dev          # -> http://localhost:3000
```

**One command (Docker, authored, not executed here, no daemon in this environment):**
```bash
docker compose up --build
```

## Documentation updated

`README.md`, `docs/architecture.md`, `docs/methodology.md`, `docs/API.md`,
`docs/deployment.md`, `docs/limitations.md`, `docs/brand-system.md`,
`docs/portfolio-report.md`, this file.

---

## Signal & Historical Refinement (branch `arepo-signal-refinement`)

Changelog, grouped:

- **Navigation:** removed horizontal scrolling; desktop links spread across the width in one
  stable row, mobile links wrap; no overflow strip.
- **Brand / favicon:** browser-tab icon is now the wordmark's stylised "A" (white chevron +
  red triangle) on the ink tile; grid symbol enlarged in nav and footer.
- **Status chip:** shows only truthful states, API Connected/Delayed/Offline (green only when
  genuinely connected) plus "Updated Xs ago" when known; removed the always-Unknown live feed
  and the "n/a" age.
- **Signal Lab:** surface label renamed "Composite anomaly"; plain-English purpose; each signal
  links to its market (market_question/outcome_name now on the signal); "How this may be used"
  research section; clearer information architecture.
- **Signal engine:** rebalanced composite across standardized price-behaviour features
  (movement burst, volatility regime added) so it is no longer imbalance-dominated; book-only
  ceiling requires material price context (PRICE_CONTEXT_FLOOR); live history fetch widened to
  the full series at 30-minute resolution so price features have data; enrichment prefers
  near-mid markets. Fixed, documented weights (no overfitting).
- **Chart ranges:** 1H/6H/24H/7D/All on the market-detail chart, only the sensible ones shown.
- **Order-book explainer:** repaired diagram (strong colours, correct labels, a legend for
  bids/asks/midpoint/spread/imbalance, light interactivity).
- **Historical retrospective:** new `/api/historical/screen` and Replay "Historical analysis"
  tab; causal reconstruction (no look-ahead; selection never uses today's price), provenance
  `reconstructed`, survivorship disclosed.
- **Footer:** designer credit (Dayyan Sheikh / dayyansheikh.work@gmail.com).

Independent Sonnet review run over the pass; it confirmed the truthfulness properties
(no look-ahead, provenance separation, imbalance no longer dominating, honest degradation) and
found two real defects, both fixed and regression-tested: (1) the historical near-mid filter
used today's price instead of the price at the cut-off; (2) the book-only ceiling gated on
presence rather than magnitude of a price feature.

Verified test results: backend **193 passed** (ruff clean); frontend tsc/lint/build clean (10/10
routes), 8 vitest. All seven surfaces browser-verified against a live backend.

Data-availability honesty: historical price data is dense and real; strong LIVE signals are
rare because most markets are calm and the discoverable universe is mostly pinned long-shots.
No public deployment or paid scheduler activated (needs the user's account authorisation).

---

## Opportunity Intelligence & Alerting (branch `arepo-opportunity-alerts`)

Chosen information architecture: **Opportunity Board as home** (top-30 by a transparent
Research Priority score), **Explore Markets** retained for broad browsing + full-universe
search, **Signal Lab** as deeper market-linked analysis (DECISIONS O1). No page duplicates
another; every card explains why it appears and links to the market.

Delivered:
- **Indicators (analytics/flow.py):** large relative trade, consensus-opposing flow, clustered
  trades, concentrated flow, limited activity history, late large trade, over real public
  trades (data-api.polymarket.com/trades); market-relative, robust (median/MAD/percentile),
  sample-gated, neutral wallet language.
- **Research Priority + evidence families + tags (opportunity/scoring.py):** fixed documented
  weights, >=2 independent families for high priority, shaped for data quality/liquidity/
  spread/freshness; not called expected profit; prior safeguards preserved.
- **Opportunity Board** (/api/opportunity/board + home page) and **daily immutable snapshot**
  (idempotent CLI + read routes).
- **Search repair** (/api/markets/search) full-universe + company/ticker aliases; Microsoft and
  MSFT both return the 36 real Microsoft markets; honest no-result.
- **Research email alerts** provider-neutral, disabled by default (console sink), eligibility +
  honest wording + dedup/cooldown/history/retry/test-mode; SMTP disabled unless configured.

Verified: backend **236 tests pass**, ruff clean, migrations/bootstrap idempotent; frontend
tsc/lint/build clean (10/10). Browser-verified the Board, nav, and MSFT search. External email
sending remains disabled and requires the user's own provider credentials to enable.
