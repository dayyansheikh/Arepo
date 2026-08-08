# DECISIONS.md — Astrolabe / Arepo

An append-only log of significant engineering and product decisions, with reasoning.
Newest entries at the top of each section.

---

## Free-production deployment (branch `arepo-free-production-v1`)

### D-DEP1. GitHub Actions runs the scheduled compute, not Render cron (deviation from the starting hypothesis)
The starting architecture suggested Render for the API and implied Render cron for scheduling. Render
cron jobs are a **paid** feature, so keeping them breaks the £0 requirement. Decision: a single
idempotent **tick** (`python -m astrolabe.scheduler.tick`) runs on **GitHub Actions** (free & unlimited
for public repos), and Render hosts only the free API web service that serves persisted results.
Evidence: the capacity audit measured a complete scan at 269–302 s with ~250–400 MB peak RSS, which
does not fit comfortably inside Render Free's 512 MB / request budget — so heavy work belongs on
Actions runners (7 GB, no request timeout) regardless of cost. The API never rebuilds the universe in a
user request. **Cost impact:** £0 (vs paid Render crons). **Reliability impact:** Actions cron drifts
5–30 min, so the tick is delay-tolerant and decides due work itself; a DB lease + idempotent jobs make
late/duplicate/missed ticks safe. **Limitation:** free unlimited Actions requires a **public** repo.

### D-DEP2. One due-work tick, not many fixed-schedule jobs
Instead of ~13 fixed cron entries, the application decides what is due each wake: refresh (if the
latest complete scan is stale), causally-due cohort freezes, forward/preclose/resolve collection, and
daily retention/backup. Freezes are gated causally — a cadence period is frozen only once a complete
scan exists **at/after** its boundary, and never fabricated with look-ahead; if a whole period elapses
with no in-window complete scan it is honestly left unfrozen. All underlying collectors already existed
and are reused verbatim (no research logic duplicated in YAML). Bookkeeping lives in a bounded
`scheduler_state` table (one row/job) that also powers `/admin/health`.

### D-DEP3. Storage: Postgres hot window + bounded category-C retention; permanent research never pruned
Measured growth (audit §3): category-C high-frequency scan history is the visible bulk but is a
**rolling window** — every live surface needs ≤ 6 h (trajectory) / ≤ 200 rows-per-market
(market-detail), so a 2-day hot window fully preserves functionality. Retention prunes category-C rows
older than the window and **never** prunes a scan referenced by a frozen cohort, the latest complete
scan, or any permanent (A) / account (D) data. The real long-term driver is **permanent research**
(~12 MB/day from ~5 full-universe cohort freezes), giving a 500 MB free-Postgres safe lifetime of
**≈ 3–5 weeks** as-is. This is stated honestly rather than hand-waved: extend via lower cohort cadence
(~3 months), a compressed cold archive, or a paid Postgres tier.

### D-DEP4. Cold archive is pluggable and default-OFF, with an archive-before-delete invariant
R2/object storage is **not** added by default (the audit shows Postgres-only works for the measured
lifetime, and it needs external credentials). Instead a pluggable archive interface exists
(`""`=prune-only, `local`=compressed JSONL, `r2`=S3-compatible), default off. When enabled, each pruned
scan is archived + checksum-verified **before** its rows are deleted; an archive failure **retains** the
source (never delete-before-archive). This keeps the simplest safe design now and a lossless-indefinite
path later, both £0. **Rollback impact:** archived data is recoverable via manifest + checksum.

### D-DEP5. Data migration copies verbatim and self-reconciles; no recompute
The SQLite→Postgres importer opens the source **read-only**, copies every value unchanged (only naive
datetimes are coerced to UTC-aware for `timestamptz`), preserves PKs/FKs/nulls/frozen values, is
idempotent (`ON CONFLICT DO NOTHING` / `INSERT OR IGNORE`), and **fails non-zero** if reconciliation
(per-table counts + every frozen cohort's `entries == universe_size`) doesn't match. It never
recomputes or "fixes" historical observations. `--require-empty` refuses a non-empty destination for a
first import.

### D-DEP6. Detailed diagnostics behind a token; user pages stay clean
`/health` stays a bare liveness probe; the rich production/research snapshot (latest scan + age,
scheduler job state, latest cohort + scheduled-vs-actual freeze timing, storage growth + quota level)
is served from `/admin/health` guarded by `ADMIN_TOKEN` (404 when unset). The frontend keeps its
existing freshness/“delayed refresh” messaging and adds a restrained **“Connecting to Arepo data…”**
cold-start state (no per-card stale/fresh clutter) so a free-host wake-up reads as calm, not broken.

---

## Final short-horizon completion (branch `arepo-final-short-horizon-completion`)

### D-FC6. A market that closed before its horizon is terminal, never perpetually pending (§11)
When `collect_due_forward` reaches a due horizon whose market has already closed, it records a terminal
closed-before-horizon observation (`midpoint=None`, an explanatory `unavailable_reason`) and does **not**
issue a live quote fetch — a post-close price is not a genuine forward, and freeze-to-close is the
correct evaluation for those markets. This removes the "pending forever" state that made the 6h horizon
look stuck. The collector returns `closed_before_horizon` so the funnel is auditable, and closed /
awaiting-resolution / resolved / invalid stay distinct states rather than collapsing into "pending".

### D-FC5. Replay leads with results; every control is one click and progressively disclosed (final UX)
The public Replay page is built around one question ("How did Arepo's past signals perform?"). The
count-first performance block and a plain movers sentence render before any control, the newest cohort
with evaluable results is auto-selected so the page never opens on six zero cards, and horizon/closing/
scope are segmented tabs + pills instead of dropdowns. Cohort mechanics collapse behind "Previous
cohorts" and the public-vs-shadow research panels live only under a "Research comparison" scope, so a
new user sees performance immediately while every prior capability stays reachable. Pure decision logic
lives in `lib/replay-ux.ts` and is unit-tested; the page only renders what it returns.

### D-FC4. Evidence is shown in plain language, and the concentration family makes no identity claim
Public cards map raw evidence-family keys to human labels (`friendlyEvidence` / `EVIDENCE_LABELS`):
price→"Price behaviour", order_book→"Order-book pressure", trade_flow→"Trade activity", timing→"Trade
timing", wallet_concentration→"Concentrated trading". The raw keys never appear publicly, and the
concentration label is described as volume being concentrated rather than broad, explicitly "not a claim
about who traded" — Arepo computes concentration from public trades and makes no wallet-identity or
fresh-wallet claim, so the copy must not imply one. Only families the backend actually computed are shown.

### D-FC3. Freshness is page-level; movement is per-card (no Stale/Fresh clutter on cards)
Signal cards show only genuine movement trajectory labels (`cardTrajectoryLabel` returns a label solely
for New/Strengthening/Weakening/Stable/Direction-reversed). Data-freshness states (Stale / Refresh
delayed) are suppressed on cards because they are a property of the whole scan, not of one signal, and
belong to the page-level freshness badge. The full staleness detail is kept on the market-detail signal
history, where a signal that has not refreshed is genuinely informative — hidden progressively, not
removed.

### D-FC2. Priority/Confidence/Evidence chips are accessible and self-explaining
Each chip is a shared `InfoChip` over the viewport-aware Popover primitive: it opens a plain-English
tooltip on hover, focus and tap, closes on Escape/blur, and is a real button with aria-expanded /
aria-controls. Research Priority is banded to High/Medium/Low with a tooltip stating it is "not a
probability or a profit estimate"; Confidence is described as data quality, "never a probability". This
lets a first-time user understand each term in place without leaving the page.

### D-FC1. Market-detail acceptance targets a live signal market, not a hardcoded id
`action-spacing` and `popover` specs previously navigated to a hardcoded market that had since closed,
so the SignalItem rows and MetricHelp popovers no longer rendered and the specs timed out. They now
resolve a live market with signals at runtime (`liveSignalMarketId`), expand the collapsed per-signal
breakdown so the rows exist, exclude the non-tooltip `signal-detail-toggle` from the popover-trigger
selector, and click only visible triggers. This fixes the real target/product problem rather than
weakening the geometry and spacing assertions, which are unchanged.

## (superseded) Complete short-horizon universe (branch `arepo-complete-short-horizon-universe`)

### D-CU4. An incomplete scan fails loudly and never becomes a valid-looking cohort (prompt §2, §20)
`paginate_markets` sets `complete=False` with a reason on any offset cap, non-progression, retry
exhaustion or emergency-guard trip; the scan still records what it reached but its `status` and
`pagination_complete` say so. On this live Gamma deployment the offset path caps at 2100 and keyset
does not advance, so a real scan honestly reports incomplete rather than pretending 2100 is the whole
universe. A future cohort freeze must refuse or degrade on an incomplete scan.

### D-CU3. Top ten is a display flag, never a slice before analysis (prompt §5, §6)
The scan scores every eligible market, ranks each bucket over ALL its directional markets plus an
overall 30-day rank, and stores `public_top_ten`/`shadow_directional` flags. The public UI shows ten
per bucket with "Top 10 shown from N eligible markets"; the full universe is analysed, ranked and
preserved. A real scan analysed 181 eligible / 83 directional versus the old 60/19.

### D-CU2. Append-only snapshots in new tables; the model is unchanged (prompt §7, §8)
New `discovery_scan_runs`/`discovery_signal_snapshots`/`discovery_scan_locks` tables are additive; a
refresh only INSERTS (unique per scan+market+token) and never overwrites. This is a history +
interpretation layer over the EXISTING signal model (no formula/threshold/confidence/RP change). The
signal-strength trajectory reports only a score change, never a probability, accuracy or profit claim;
its 0.02 stability threshold is predeclared from score precision, not tuned to outcomes.

### D-CU1. The 60-market cohort was a triple hard cap with zero pagination (prompt §1)
Proved: `discovery_limit=60` (one `/events` page) + `screen_universe(universe_limit=60)` +
`enrich_markets` `subset[:60]`. Discovery never paginated. The fix adds real offset pagination, a
backend 30-day eligibility gate before scoring, and complete analysis of the eligible universe, so
ten is only ever a display limit. The existing historical 60-market cohort is left untouched.

---

## Prospective Replay refinement (branch `arepo-prospective-replay-refinement`)

### D-PR4. Replay product "no price change" is a distinct threshold from the edge materiality floor
The Replay movement classification answers a plainer question than the edge hit-rate: "did the stored
midpoint move at all in Arepo's direction?" so it uses `REPLAY_MOVE_EPS = 1e-6` (a float-comparison
guard), NOT the `FLAT_EPS = 0.01` materiality floor. With the 0.01 floor the real public set reads
0/0/10; with the product threshold it reads the authoritative 2/2/6 (smallest real move 0.004). The
0.01 floor is left untouched for every edge/baseline/calibration number; the two are deliberately
separate questions, documented in `research_replay.py` and the methodology.

### D-PR3. Server owns the evaluation truth; the Replay frontend only renders it (prompt §11)
`research_replay.py` computes every result state, aggregate count, movement coverage and executable
result. The React page derives nothing important from client assumptions; `lib/replay.ts` only
formats and selects (labels, copy, default cohort), unit-tested in isolation. This keeps the
displayed truth deterministic and testable and prevents a loose client rule from disagreeing with the
backend.

### D-PR2. Public Replay is prospective-only; reconstructed/synthetic stay internal (prompt §1)
The reconstructed screen, synthetic seed and deterministic backtest are removed from the public
Replay page but kept in the codebase for internal use and automated tests (not deleted). Legacy
`?replay=` values normalise to the single prospective page and the stale param is stripped, so no
removed mode can ever be displayed. Replay now means exactly: real predictions genuinely frozen
before later prices became known.

### D-PR1. Cadence, horizon and closing window are three independent axes (prompt §2-4)
Cohort cadence (six-hourly/daily/weekly, read from the stored `cadence` string so a manual six-hour
cohort is never called weekly), evaluation horizon (1h/6h/24h/7d/final, marked pending unless a
stored observation exists) and the frozen time-to-close filter (using `time_remaining_hours` at
freeze, never the current TTC) are separate selectors. Excessively-late cohorts are excluded from the
selectable list, matching the existing excessive-lateness rule (unchanged). One cohort never
demonstrates edge; the product answers only the descriptive movement question.

---

## Edge-research infrastructure (branch `arepo-edge-research-infrastructure`)

### D-ER5. Executable cost model is a declared assumption, not a fitted value (prompt §6)
Depth-aware slippage = `SLIPPAGE_COEFF(0.5) * stake/near_mid_depth`, capped at `SLIPPAGE_CAP(0.10)`,
charged on entry AND exit, plus half-spread crossing each side and `FEE_RATE(0)`. These are declared
up front, not tuned to outcomes. Missing depth stays missing (executable performance unavailable, no
infinite-liquidity assumption). A favourable midpoint move smaller than costs is never counted as
practical edge.

### D-ER4. Forward observations never backfill a horizon that predates the freeze (causal, prompt §5)
The entry prices are captured at `frozen_at`. A horizon whose target time is before `frozen_at`
cannot be a genuine forward measurement, so `collect_due_forward` records it terminal-invalid
(`midpoint=None` + reason) rather than filling it with a current price. In production the freeze
crons fire at each cadence boundary, so `frozen_at ≈ cut-off` and every horizon is in the future.
This was found by actually running the live path (not trusting the report); it prevents a subtle
look-ahead artefact when a freeze runs mid-period.

### D-ER3. Additive research schema, not a rewrite of the weekly cohort tables (prompt §3)
New `research_cohorts`/`research_entries`/`research_forward_observations`/`research_revisions` tables
sit alongside the existing weekly-cohort tables, so no prior data or test is disturbed and the
migration is a pure `create_all` add. `(cadence, cutoff_at)` is the unique cohort key; entries are
unique per `(cohort, market, token)`; forward per `(entry, horizon)`. Only Postgres-portable column
types are used. Immutability is enforced in the repository; corrections go to `research_revisions`.

### D-ER2. Freeze the FULL universe with explicit roles, not the public top-10 (prompt §2)
The public product still shows the top selections, but research freezes every screened market with a
role (`public_selection` / `shadow_directional` / `observation` / `abstention_control`). This lets
the research test whether ranking, confidence, Research Priority, stricter selection and abstention
add value, none of which is possible if the sample is truncated to the visible ten. Live dry run:
60-market universe frozen, ~10 public + ~2-3 shadow + ~10 observation + ~37 abstention per cadence.

### D-ER1. Per-family directions frozen at the cut-off so baselines/ablation are truly prospective (§8/§9)
`momentum_direction` (z-score sign), `orderbook_direction` (imbalance sign) and `tradeflow_direction`
(net flow sign) are computed and frozen on every entry. This is what makes order-book-only,
trade-flow-only and full-without-momentum genuine PROSPECTIVE baselines (the reconstructed screen
could not have them). It also makes the central finding mechanical and honest: because Arepo's
direction IS the z-score sign, momentum, price-only and Arepo share a direction by construction, and
the ablation is built to expose that rather than assert Arepo adds value. Conclusions stay
inconclusive until a real prospective sample exists; no threshold was changed to flatter results.

---

## Signal Intelligence & Replay functional validation (branch `arepo-signal-replay-functional-validation`)

Independent reviewers (quant, provenance, implementation, adversarial) audited the running system;
Opus synthesised. Conflict priority per spec §2: causal validity > statistical honesty > functional
usefulness > consistency > reliability > simplicity > performance > aesthetics. **No threshold,
sample, cut-off or eligibility rule was changed to improve a reported result.** Every change below
was decided on principle before, or independently of, its effect on any metric.

### D-SR6. Displayed confidence capped below 100% (spec §6; QA + Opus cross-surface check)
Reliability confidence could still reach exactly 1.00 on the Opportunity Board (three families +
full completeness + perfect data quality). §6 says do not display 100% for an estimate, so displayed
reliability is capped at `CONFIDENCE_DISPLAY_CEILING` = 0.95 on every surface. It is an estimate of
how much to trust a reading, not a certain probability. Also completed the confidence unification the
first pass missed: Market Detail's per-outcome cards (`OutcomeView`) were still showing the raw 1.00
data-quality term (adversarial re-review F'#1); they now carry and display `reliability_confidence`.

### D-SR5. Momentum-agreement + Brier honesty (spec §12, §13; quant B#2/B#3)
Arepo's direction is `sign(latest-return z-score)`, close to momentum by construction, so "Arepo vs
momentum" is near-self-referential. Rather than change the signal (which would risk gaming), the
Replay baseline comparison now reports `arepo_momentum_agreement` so the reader sees this directly.
Brier/log loss are **not** computed on the reconstructed directional screen: Arepo emits a
direction, not a calibrated probability, and reconstructed markets rarely resolve; a fabricated
Brier would violate §13. An explicit `probabilistic_metrics_note` says so, and the stale
"Brier framework exists" claim in `docs/quant-final-review.md` was corrected. Brier/log loss are
reserved for the prospective resolution view once a real resolved sample exists.

### D-SR4. Reconstructed Replay reproducibility + survivorship honesty (spec §9, §16; C#1/C#2/F#4/F#5)
The reconstructed cut-off is snapped to the start of the target UTC day, so same-day requests are
reproducible; it remains a live screen (the prospective cohort is the immutable record, stated in
the limitations). The universe is today's still-open markets ranked by today's volume, which HARD-
excludes anything closed/resolved since the cut-off — corrected from the old "mild survivorship"
wording in both the docstring and the user-facing limitations, and named as the main reason the
funnel is so thin. `/api/cohorts/latest` now excludes synthetic cohorts so demo data can never be
served as the current prospective record (F#6).

### D-SR3. z-score materiality floor (spec §4; quant B#9)
Off a perfectly flat baseline the z-score is 0/0; previously any move > 1e-12 emitted the maximal
clipped z (±10), so a 0.1-point blip saturated the strongest composite component. Now a move must be
economically material (≥ `FLAT_BASELINE_MIN_MOVE` = 0.005 probability points) to be called maximally
unusual; below that it abstains. Chosen on the principle that a sub-half-point move is negligible on
a 0–1 scale, not tuned to any outcome.

### D-SR2. Flat forward moves are not directional misses (spec §10, §11; quant B#1, adversarial F#1)
A single shared `classify_directional` (tolerance `FLAT_EPS` = 0.01, the value the no-change baseline
already used) classifies a forward move as correct / incorrect / **flat** / pending, applied
symmetrically to EVERY directional predictor (Arepo, momentum, price-only, current-implied,
always-up/down) AND to the real prospective cohort pipeline (`tracking._movement_correct`,
`CohortSummary.moved_flat`). Flats are excluded from every hit-rate denominator and reported in their
own column, so a market that did not move can never be booked as a miss. This is a predeclared
honesty rule fixed on principle: it moves flats out of BOTH numerator and denominator symmetrically
and does not favour Arepo. Live effect at the 7-day cut-off: the misleading "4 moved against
(Arepo 0/4)" became "2 moved against, 2 flat (Arepo 0/2)"; the apparent no-change advantage was
largely a flat-handling artefact. The adversarial reviewer found the same bug in the real cohort
pipeline; it is fixed and tested there too.

### D-SR1. One confidence definition on every surface (spec §6, §17; quant B#4, impl D#2)
Signal Lab and Market Detail previously displayed the raw data-quality term (`signal.confidence`),
which is 1.00 for every good-data signal, while the Opportunity Board displayed the reliability
confidence for the same signal. Reliability confidence (data quality × evidence corroboration ×
component completeness) is the defensible number, so it is now computed once in the enrich path
(`signal.reliability_confidence` + `signal.n_families`) and displayed on every surface; no surface
shows 100% (capped at `CONFIDENCE_DISPLAY_CEILING` = 0.95, D-SR6). Correction: an earlier revision
of this pass excluded `volume_acceleration` from the completeness set after seeing it at 0% on a
cold start; the running product showed it warming up with the snapshot series and present in every
signal once warm, so it was **restored** to the completeness set — it is a genuine live component,
not dead (see `docs/signal-component-register.md`).
The frontend directional gate now consumes `signal.n_families` so Signal Lab, Market Detail and the
Board apply one identical `has_directional_view` rule. The Board may still read higher when live
trades add a family — the single documented, legitimate exception.

---

## Directional Evidence, Replay & Deployment (branch `arepo-directional-evidence-deployment`)

### D0. Research paper adopted vs deferred (spec §2)
Read `research-references/deep-research-report.md` in full (Opus + independent Sonnet reviewer).
Full audit in `docs/research-paper-evidence-audit.md`. Adopted now (data available, causal,
interpretable, testable): z-score baseline exclusion; confidence as estimated reliability;
logit movement alongside probability-point; abstention + selective directional board; missing-
feature indicators (never missing->zero); Replay baseline comparisons with proper scoring;
Research Priority kept as a labelled heuristic. Deferred as research (needs a point-in-time store
and walk-forward validation not buildable in-session): calibrated hierarchical logistic/beta
calibration, repricing-distribution, liquidity/cost/capacity, and logical-consistency models,
and OFI from a reconstructed live book. No component claims alpha (report line 1123-1125).

### D1. Why directional views are rare (diagnosis, spec §3) — NOT a threshold problem
Full diagnosis in `docs/directional-diagnosis.md`. Root cause is data availability: at 30-min
price fidelity, prediction-market outcomes are frequently flat, so `rolling_zscore` returned
`None` (zero variance), which simultaneously nulled `direction`, starved the price family, and
capped composite strength below the 0.40 floor; the other families need >=15-20 live trades.
The market-detail ModelView was also stricter than the board (strength>=0.40, no family credit).
Fixes are report-consistent, not threshold-lowering (see D2-D4).

### D2. Z-score scored against a baseline that excludes the current observation (report line 736)
`rolling_zscore` now scores the last return against the trailing returns t-L..t^- (excluding the
return being measured), so the baseline is not pulled toward the event. Crucially, a real move
off a *perfectly flat* baseline is reported as a signed clipped extreme (`flat_baseline_move`)
rather than `None`, so a flat-then-jump — the case we most want to detect — now yields a
directional reading. Only a truly unchanged market (flat baseline AND zero last move) abstains.
This improves directional coverage without lowering any threshold. Tests updated; the labelled
synthetic backtest shifted (16->19 samples, hit-rate 0.625->0.526), which is expected and is not
a performance claim.

### D3. Confidence redesigned as an estimated-reliability score (spec §6, report lines 774, 1087-1089)
The old confidence started at 1.0 and only penalised down on data completeness, so any liquid,
fresh, two-sided market displayed exactly 100%. Confidence is now `data_quality x corroboration`:
a single, uncorroborated evidence family is capped near 0.63 even with perfect data; full
reliability requires multiple distinct families AND high data quality. This removes the 100%
spike, produces meaningful variation, is computed only from signal-time evidence (no future
outcomes), and keeps the data-quality band displayed separately. `reliability_confidence` with
saturation/variation/monotonicity tests.

### D4. Direction preserved as genuine, with abstention (spec §3, report line 741)
Direction still comes from computed evidence and can legitimately be `None`; the board stays
selective by directional view (D-C, Phase C) rather than forcing a view. The ModelView gate is
unified with the backend evidence rule (Phase E).

## Product Simplification, Accounts & Decision-Support (branch `arepo-product-simplification`)

### P0. Two independent product reviews (spec §2) — findings that shaped the redesign
Before choosing the redesign, two Sonnet reviewers inspected the live product.

**Reviewer A (capable beginner):** every card leads with a bare number (`73 / prio`,
"Composite anomaly", "signal strength") and defers the explanation to a hover tooltip or a
separate page; tags are unexplained pills (tooltip-only, invisible on touch); `n_families
evidence` renders as "2 evidence"; Signal Lab and market-detail show **both Yes and No as
separate anomalies** for the same price move; Research Priority vs signal strength vs
confidence are three similar-looking scores that are easy to conflate. Biggest advice:
**lead every card with the plain-English "so what" sentence the backend already generates
(`_explain()`), demote the number to a labelled secondary chip.**

**Reviewer B (prediction-market quant):** the blocking defect is `confidence = strength ×
quality.confidence` (`anomaly.py`), which (a) contradicts the product's own copy that
"strength and confidence sit side by side, never blended", and (b) makes Research Priority
**quadratic in strength** in the modal single-family case. Also: a `cross_market` evidence
family was declared but never implemented (overstating breadth to 6 when only 5 exist); the
freshness penalty was dead on the board (`data_age_seconds=None` hardcoded); `card.direction`
is computed but never rendered on the board; the historical-reconstruction path is otherwise
rigorous (no look-ahead in signal construction, causal entry-price selection, clean
provenance separation). Top fix: **decouple confidence from strength.**

### P1. Chosen information architecture (spec §3, §4)
The two reviews converge on one root cause: the product computes good decision-support
explanations but buries them under bare scores. The redesign therefore keeps a lean surface
set and re-sequences each surface to lead with the conclusion:

- **Opportunities** (`/`) — the Board, redesigned so each card leads with a one-sentence
  hypothesis + direction; Research Priority becomes a labelled chip with a low/medium/high
  interpretation; a time-to-close filter (24h / 3 days / 7 days / all) is added.
- **Explore** (`/markets`) — the full searchable universe (retained).
- **Signal Lab** (`/signals`) — consolidated so complementary Yes/No are shown as one price
  event, not two independent opportunities; each signal states direction, horizon, and
  whether it is actionable / observational / inconclusive.
- **Replay** (`/replay`) — prospective + reconstructed (price-only) + synthetic kept strictly
  separate; defaults to the simplest view.
- **Learn** (`/how-it-works`, `/methodology`) — plain then technical; the Arepo brand/origin
  story moves here, out of technical result pages.
- **Account** (`/account`) — sign in/up, alert preferences, saved markets, alert history.

Rejected: a single merged "everything" page (re-creates the wall-of-metrics problem both
reviewers flagged); removing Signal Lab or Replay (spec requires retaining them, and the
quant review found Replay's causal design is the product's strongest asset).

### P2. Statistical-integrity fixes applied first (from Reviewer B), before any UI work
- **Confidence decoupled from strength**: `Signal.confidence` is now `quality.confidence`
  (pure data-quality, independent of anomaly size). This removes the hidden strength² term
  in Research Priority and makes the "strength ≠ confidence" copy actually true.
- **Freshness penalty wired through**: `TokenAnalytics` now carries `data_age_seconds` and
  the Opportunity Board passes it into `score_opportunity`, so stale readings (cached/replay
  modes) are correctly shaped down instead of getting full freshness credit.
- **`cross_market` family removed**: it was declared but never produced. Only the five real
  families (price, trade_flow, order_book, wallet_concentration, timing) are now declared, so
  the "independent evidence families" count matches what the code can actually compute.

### P3. Authentication architecture: native FastAPI (fastapi-users), NOT Supabase (spec §9)
Assessed the existing Next.js + FastAPI + SQLAlchemy-async architecture. Chose
**`fastapi-users` (SQLAlchemy adapter, argon2 hashing, JWT + secure cookie sessions, email
verification + password reset)** integrated into the existing FastAPI backend and database.

Supabase (the spec's strong default) was **rejected** because in this architecture it would:
(1) introduce a **second datastore** alongside the FastAPI-owned SQLAlchemy DB, splitting
user/preferences/alert-history data from the market and alert engine that must foreign-key to
it; (2) **not run offline** — the spec requires the project to remain runnable before external
credentials are configured, but Supabase needs either a cloud project or local Docker
(unavailable in this environment) before anything works; (3) split auth (Supabase) from the
API (FastAPI) across two backends. `fastapi-users` keeps one datastore, one backend, one
session model, runs fully offline with the existing **provider-neutral email engine** sending
verification/reset mail to the console sink, and still delegates **all** password hashing and
token crypto to vetted libraries (argon2-cffi / PyJWT) — satisfying "do not build password
security from scratch". Documented here per spec §9.

---

## Opportunity Intelligence & Alerting (branch `arepo-opportunity-alerts`)

### O1. Information architecture: Opportunity Board as home, Explore Markets retained
Chosen structure (spec §3, close to Option A). The home page (`/`) becomes the
**Opportunity Board**: a focused, selective default answering "which markets deserve
attention today", showing up to the top 30 by a transparent **Research Priority** score,
each card explaining why it appears and linking to the market analysis page. The old
Overview is replaced by the Board (its top-movers/most-active content is superseded and
would duplicate the Board). **Explore Markets** (`/markets`, relabelled) is retained for
broad browsing and the repaired full-universe search. **Signal Lab** stays as the deeper,
market-linked per-signal analysis. No information is duplicated across pages; every signal
links to a real market; every board card explains its appearance. Nav order: Board,
Explore Markets, Signal Lab, Replay, How It Works, Methodology.

### O2. Trade-level and wallet data are available read-only (verified)
`data-api.polymarket.com/trades?market=<conditionId>` returns real trades (proxyWallet,
side, size, price, timestamp, outcome), up to 1000 per call; `/trades?user=<wallet>`
returns a wallet's cross-market history. This genuinely supports the flow, wallet-
concentration, and timing indicators (large relative trade, consensus-opposing flow, late
large trade, concentrated flow, clustered trades, limited public activity history). Where
an indicator's data is thin or absent, it degrades confidence and is labelled, never
fabricated (spec §5). Wallet labels stay neutral ("Limited public activity history"),
never "insider/suspicious/manipulated" (spec §6).

### O3. Evidence families and the high-priority two-family rule
Independent evidence families: price, trade-flow, order-book/liquidity, wallet
concentration, timing, cross-market. The Research Priority score combines standardised,
capped indicators with fixed documented weights (no fitting to outcomes); a high-priority
alert normally requires >= 2 independent families firing (spec §5.5), preserving the prior
causal-selection and book-only safeguards.

### O4. Email is provider-neutral and disabled by default
A provider interface with a console/outbox sink as default; external sending stays disabled
until `ALERT_EMAIL_ENABLED` + provider credentials are configured via env vars (never
hardcoded). Recipient env var prepared for dayyansheikh.work@gmail.com. Dedup, per-market
cooldown, alert history, retry, failure logging, disable control and test mode included.
Alerts are honest, non-personalised research signals, never "buy/sell/stake" (spec §10).

---

## Signal & Historical Refinement (branch `arepo-signal-refinement`)

### S7. Independent-review fixes: causal historical selection + material price-context floor
An independent Sonnet review found two real defects; both fixed and regression-tested.
- **Historical candidate selection was not causal.** The near-mid filter used each market's
  *current* Gamma price, which excludes markets that have since drifted to an extreme (exactly
  the movers a signal should catch) and biases the reported stats. Fix: the scan universe is
  chosen by recent 24h trading volume (a market-activity property, not the outcome), and the
  near-mid gate is judged on the price **at the cut-off** (`entry`, the last pre-cutoff point),
  with `NEAR_MID=(0.1,0.9)` in `evaluation/historical.py`. Missing pre-cutoff history makes a
  candidate ineligible. Proven by `test_current_price_does_not_change_historical_selection`
  and `test_pinned_at_cutoff_excluded_even_if_near_mid_or_moving_later`.
- **Book-only ceiling gated on presence, not magnitude.** A present-but-zero price feature (a
  calm market produces a zero volatility regime every tick) set `has_price_context=True` and
  bypassed the 0.5 cap. Fix: require a price feature whose normalised value exceeds
  `PRICE_CONTEXT_FLOOR=0.05` to lift the ceiling. Proven by
  `test_present_but_zero_price_feature_does_not_bypass_the_cap` and
  `test_material_price_feature_lifts_the_cap`.
Note: a *fresh* independent-subagent review requested in the resume prompt could not be run
because the account hit its monthly spend limit (an external blocker); the earlier independent
review of this same pass did run and its findings are the two fixes above.

### S1. Historical price data IS available and dense (verified by probe)
CLOB `/prices-history` returns real, timestamped history: `interval` in {1h, 6h, 1d,
max} with `fidelity` (minutes/point) controlling resolution. Verified: 1h→60 pts
(1-min), 1d→1441 pts (1-min), max→4446 pts (~10-min over 31 days). **25/25 sampled
liquid markets have >=20 real points**, most hundreds-to-thousands spanning days/weeks.
Therefore both (a) chart timeline ranges and (b) a truthful historical top-15
retrospective are supportable and will be built. `interval=1w` returns 400 (unsupported)
so 7D uses `startTs`/`endTs`. Note: `ClobRestClient.get_prices_history` returns the
`history` list directly (not the wrapping dict).

### S2. Signal Lab surface label -> "Composite anomaly"
Per new brief, "Unusual market activity" weakened the idea. Rename the surface label to
**"Composite anomaly"** (professional, precise); the number stays "Composite anomaly
score" in detail/methodology. Signal Lab gets a plain-English purpose header, links each
signal to its market, and a research-framed "How this may be used" section.

### S3. Status chip simplified to truthful states only
Drop "Live feed" (the CLOB WebSocket is not wired into this read-only deployment, so it
was never truthfully "connected" and always read "Unknown") and drop "Updated n/a".
Keep **API** (Connected/Offline; green only when genuinely connected) and show **Updated
Xs ago** only when the data age is actually known. No visible "Unknown".

### S4. Favicon = the stylised "A" from the wordmark
The browser-tab icon becomes the wordmark's "A": a white chevron/peak with the small red
triangle nested at its base, on the ink tile. The 5x5 grid symbol remains the nav/section
mark (used slightly larger, per brief).

### S5. Composite signal rebalanced across standardized features (no overfitting)
The composite must not be dominated by order-book imbalance. Rebalance to combine
standardized, capped features: return z-score, short-horizon movement abnormality,
rolling-volatility context, spread behaviour, near-mid depth/liquidity change, volume
acceleration, and imbalance, with **fixed, documented weights** (not fitted to outcomes),
robust clipping to bound any single feature's influence, persistence/repeat-firing
awareness, and data-quality gating. Weights and safeguards are documented; features with
insufficient data degrade confidence rather than being faked.

### S6. Historical retrospective is a separate "reconstructed" provenance mode
A historical top-15 screen reconstructs each eligible market's signal at a past timestamp
using only history up to that point (no look-ahead), ranks the top 15, and measures real
forward movement from the actual later history. It is provenance `reconstructed`, shown in
a clearly separated Replay tab, never mixed with prospective or synthetic cohorts.

---

## Master Final Refinement (branch `arepo-master-final`, from tag `arepo-ui-v1`)

### F1. Display heading font = Jost (documented approximation)
The supplied wordmark (`design-assets/brand/AREPO Typeface (word).png`) is a
wide-tracked, all-caps, geometric **monoline** sans: perfect-circle `O`, sharp
triangular `A` apex, uniform stroke weight, generous tracking — unmistakably in the
Futura / geometric-grotesque lineage. No licensed font file ships in the assets, so
an exact match is not claimed. **Jost** (SIL OFL, a Futura revival, loadable via
`next/font/google`) is the closest freely-licensable match; used only for major page
titles, hero and section-intro headings, in uppercase with wide tracking. Interface
text stays **Geist Sans**; data stays tabular Geist. Documented as an approximation
in `docs/brand-system.md` per the brief.

### F2. Prospective evaluation must never fabricate history
Section 14 forbids hindsight selection and invented cohorts. Decision: build the
cohort engine to record only what Arepo genuinely selects at each calculation
timestamp, freeze weekly, and track forward. On this machine there is **no verified
historical snapshot store**, so real prospective cohorts begin at the first genuine
run; any illustrative data is labelled synthetic and is stored in a separate
provenance class that can never be mixed into real statistics. The existing
deterministic backtest (current Replay) is retained as a clearly-labelled
demonstration, not presented as real performance.

### F5. Cohort engine design (entities, entry price, immutability, provenance)
Concrete design for §14/§16/§17, implemented in a new isolated `astrolabe.evaluation`
package (new files, no edits to existing storage/analytics):
- Tables (SQLAlchemy, same `Base.metadata`, Postgres/SQLite-portable): `calculation_versions`,
  `signal_snapshots` (immutable provenance of a signal as computed, with a unique
  `snapshot_ref` hash of identity+timestamp+version), `weekly_cohorts`
  (iso_year/iso_week unique, `cutoff_at` = Sunday 23:59:59 UTC, `frozen`/`frozen_at`,
  `provenance_class` in {prospective, reconstructed, synthetic}), `cohort_entries`
  (denormalised frozen copy of the selected snapshot: rank, entry_price, scores, prices,
  unique (cohort_id, market_id, token_id) to bar duplicate slots), `ranking_audit`
  (append-only add/replace log), `forward_price_observations` (unique (entry_id, horizon)
  to bar duplicates), `market_resolutions` (unique market_id), `evaluation_results`.
- Entry price = midpoint at the signal timestamp when a two-sided book exists, else the
  last traded/implied price; never a later price. Best bid/ask/spread also frozen.
  Portfolio fill assumption: enter by crossing half the spread (buy at midpoint + spread/2),
  fees configurable (default 0), documented as a simulation.
- Provisional ranking: within the live (unfrozen) week keep the top ten by strength; a
  stronger *qualifying* signal replaces only the current lowest; ties broken
  deterministically by (strength desc, confidence desc, data-quality rank desc,
  entry captured_at asc, snapshot_ref asc). Eligibility: valid market status, data
  quality >= limited, valid entry price, strength >= documented threshold.
- Freeze sets `frozen`/`frozen_at`; thereafter entries are never replaced/removed/rescored
  (repository raises on any mutation of a frozen cohort's entries). Fewer than ten
  qualifiers freezes the actual number with a recorded reason.
- Provenance: statistics aggregate `prospective` (and, if explicitly requested,
  `reconstructed`) cohorts only; `synthetic` is never mixed into real performance.
  On this machine there is no historical snapshot store, so prospective tracking begins
  at the first genuine run; the existing deterministic backtest stays a labelled demo.
- Idempotency: rank/freeze/forward/resolve commands are safe to re-run (uniqueness +
  guards), proven by the §17 tests.

### F3. Cohort persistence via SQLAlchemy models + a lightweight migration runner
The project uses `create_all`, not Alembic. Rather than introduce Alembic mid-stream,
add the new cohort tables to the ORM metadata and provide an idempotent, versioned
migration/bootstrap command (`scripts` + a `migrations` module) that creates tables
and records `calculation_versions`. Immutability of frozen entries is enforced in the
repository layer (guard on `frozen_at`) and proven by tests, since SQLite lacks
easy row-level triggers portably.

### F4. Info panel is neutral by default; red reserved for signal/emphasis
The pale-red `DisclaimerBanner` reads as an error. Replaced with a neutral grey
information panel; Arepo red is reserved for selected controls, active nav, and true
signal emphasis, per Sections 6 and 19.

---

## Arepo redesign (branch `arepo-redesign`, from tag `astrolabe-baseline`)

### R7. Light-only identity; inherited auto dark-mode dropped
Every design reference and the brand brief are light-first (red on a warm-white
ground). To keep the identity calm, consistent and credible, Arepo commits to a
single light theme and removes the baseline's `prefers-color-scheme: dark`
overrides. Dark mode was a cosmetic feature, not core functionality or a data
mode, so this preserves the "all functionality and data modes" requirement while
matching every reference exactly.

### R6. Richer Markets filters are client-side over existing fields
The backend `/api/markets` supports `search`, `category`, `status`, `sort` only.
The brief's additional guided filters (signal-strength range, probability range,
time-to-close) are implemented **client-side** over fields already on `MarketCard`,
with honest empty states, and no backend change, per "do not alter backend
behaviour". Category and status go to the API; signal-strength, probability and
time-to-close are filtered client-side; the "signal strength" and "newest" sorts
are also client-side (the API sorts only by volume/liquidity/end_date). Sport and
competition/event-group filters are deliberately **not** surfaced: `MarketCard`
carries no reliable sport or competition field, and the brief is explicit that the
UI must not imply all markets have sports metadata. Free-text search is retained as
a secondary "advanced" control.

### R5. Maths via KaTeX
Equations render with KaTeX (added as a frontend dep), not hand-rolled fraction
markup. Guarantees correct fractions, superscripts/subscripts, Greek and aligned
equations, per the brief's "never display equations as programming text".

### R4. Typography — Geist Sans via next/font, Inter fallback
Per brief preference order. Geist Mono for raw identifiers only. Tabular numerals
on all data.

### R3. Brand direction — modernist restraint, softened
Of the three `_ds` bundles, **modernist** (red-on-white, flat, disciplined) is the
closest to the brief and the primary influence; **industry** and **broadsheet**
are rejected. Modernist's zero-radius / heavy-2px-rule aesthetic is softened to the
brief's restrained radius, subtler borders and calmer spacing. See
`docs/design-reference-audit.md`.

### R2. Accent red `#E50C0E`, used sparingly
Single accent for active nav, primary actions, selected controls and key signals
only. Never carries meaning alone (up/down/good/bad always pair colour with a
sign, arrow or word). Chart primary series = Arepo red; comparison series = neutral
slate. See `docs/brand-system.md`.

### R1. Product rename Astrolabe → Arepo (user-facing only)
User-facing surfaces (nav, titles, metadata, README, report, logo, favicon,
copy) become **Arepo**. Internal Python packages, DB identifiers and API paths keep
`astrolabe` — renaming coupled internals is cosmetic risk with no user benefit, per
the brief. Brand meaning is the Sator-Square connective word; full paragraph in
`docs/brand-system.md`.

---

## D0. Product name and identity

**Decision:** The product is named **Astrolabe**.

**Rationale:**
- An astrolabe is a historical instrument used to *measure the position of celestial
  bodies and to navigate* — a precise, honest metaphor for this project, which fixes a
  prediction market's "position" from its order book and price motion and flags when the
  readings are anomalous. It is an *instrument for reading markets*, not a trading venue.
- Naming due-diligence (web search, 2026-08-02): "Astrolabe" is **not** strongly associated
  with any existing financial, trading or analytics product. Search returns only an
  aerospace company ("Astrolabe Inc", different industry) and unrelated financial-astrology
  apps (which do not use the name). This satisfies the spec requirement to avoid names tied
  to existing financial/trading/analytics products and to avoid confusing similarity.
- Rejected alternatives:
  - **Sextant** — already used by multiple financial firms (Sextant asset-management funds,
    Sextant Capital Solutions). Too close to the finance space.
  - **Plumbline** — muddy; used by consulting / trades-services companies.
  - **Bellwether / Meridian / Vantage / Parallax** — either generic finance terms or tied to
    existing funds/firms (e.g. Parallax Volatility Advisers).
- Identity is intentionally lightweight per the spec ("polished but efficient"): a single
  wordmark, a compact instrument-inspired glyph, one restrained palette, one type pairing.
  See `docs/architecture.md` (design language) and the frontend design tokens.

**Independence:** This is an original codebase built from first principles. It does not
reference, continue, fork or reproduce any prior prediction-market project, and the forbidden
name ("Ripple") appears nowhere in the product, code, docs, branding or wording.

---

## Architecture decisions

### A5. No Docker daemon / no deploy CLI in the build environment
The build machine has **no Docker daemon** and **no `gh`/`vercel` CLI** installed, and no
authenticated hosting account. Consequence: Dockerfiles and `docker-compose.yml` are authored
to spec and validated by inspection, but **`docker compose up` is not executed here**; public
deployment is prepared (configs + docs) but **not performed** — it requires the user's own
hosting authentication, which is an explicit stop-boundary per CLAUDE.md. All status docs state
this truthfully. Local run is verified via the non-Docker path (uvicorn + `next dev`).

### A4. Deterministic replay via a committed dataset + injectable clock
Replay reads a small, version-controlled JSON dataset and drives the *same* analytics code as
live mode through an injectable clock/sequence source. This proves the analytics are pure and
makes backtests reproducible and look-ahead-safe (evaluation data is strictly separated from
signal-generation data by timestamp).

### A3. Three explicit data modes as a first-class enum
`LIVE`, `CACHED`, `REPLAY` are modeled as a domain enum surfaced on every API response envelope
alongside REST state, WebSocket state, last-successful-update and data age. The UI can never
silently present cached/replay data as live because the mode travels with the data.

### A2. Anti-corruption layer: raw third-party JSON never reaches the frontend
Gamma/CLOB responses are normalized into typed Pydantic domain models at the ingestion
boundary (`ingest/normalize.py`). The FastAPI layer serializes only internal domain/API models.
Rationale: Polymarket returns JSON-encoded strings for structured fields (e.g. `outcomes`,
`outcomePrices`, `clobTokenIds` are strings containing JSON arrays; prices/sizes are strings),
schemas drift, and fields are frequently missing — all of which must be absorbed and validated
in one place, not leaked to clients.

### A1. Async Python backend (FastAPI) + Next.js/TS frontend, SQLite→Postgres
Matches the recommended stack. `httpx.AsyncClient` for REST, `websockets` for the CLOB market
channel, SQLAlchemy (async) over SQLite locally with a Postgres-compatible URL for deployment.
Analytics use NumPy/pandas; SciPy only where a specific function justifies it.

_Environment note:_ Python 3.11.2 is used (spec allows "3.12 or another currently supported
version"; 3.11 is current and supported). Node 20 LTS for the frontend.

## Final runtime acceptance fix (branch `arepo-final-runtime-acceptance-fix`)

### R1. Popover: cap width before measuring, not after
The panel was measured (`offsetWidth`) while `max-width` was the default 320px, then revealed with a
larger viewport-capped `max-width`; the wider revealed panel overflowed the right edge because the
clamp had reserved space for only 320px. Decision: compute `popoverMaxWidth(viewport)` =
`min(22rem, viewport−24px)`, apply it to the panel BEFORE the `getBoundingClientRect()` pass, so the
measured width equals the revealed width. Clamp ≥12px inside a `window.visualViewport`-aware viewport
(falling back to document client box), in a second layout-effect pass, hidden until placed. Pure
geometry stays in `lib/popover-position.ts` (unit-tested incl. 574px + visualViewport offset); the
React layer owns measurement/reposition (open/scroll/resize/visualViewport). No fixed offsets.

### R2. Fix overflow at its element sources, not with a global mask
Reproduced with real-browser instrumentation (`e2e/instrument.mjs`, logs selector/classes/width/
transform/min-width/white-space). Three genuine sources fixed at the root: TopBar right cluster made
wrappable (was `shrink-0` ≈306px > 320px viewport); SignalItem market link changed from `inline-flex`
(sized to nowrap text) to width-constrained `flex min-w-0 truncate`; the chart's `.sr-only`
accessible **table** moved into an `.sr-only` **div** (a `<table>` cannot shrink below min-content, so
`width:1px` was ignored and the hidden table widened the document). The one residual was a sub-pixel
1–2px window scroll on the synthetic-**demo** view's wide fixed-min-width tables with NO element-level
offender; contained with a **scoped** `overflow-x-clip` on that synthetic subtree only. The root
`<html>`/`<body>` clip is NOT used as the primary fix (it would make the `scrollWidth<=clientWidth`
test vacuous — the pre-existing `body` clip remains a documented belt-and-suspenders, and the
`overflow.spec.ts` audit self-check proves the assertion can still fail).

### R3. vendor-chunks/geist.js was stale dev output, not a code fault
Confirmed the overnight finding: a clean `rm -rf .next && npm ci && npm run build` succeeds (16 routes
incl. `/markets/[id]`), and a fresh `npm run dev` regenerates `.next/server/vendor-chunks/geist.js`;
both supplied IDs return 200 on direct nav, refresh and Back/Forward. Added `clean`/`dev:clean`/
`build:clean` scripts and route smoke tests; did not redesign the working routes. `geist/font` is
inlined by `next/font` in production, so there is no production vendor chunk to miss.

### R4. One shared, backoff-bounded status poller
`useStatus` previously started one fixed-30s poller per consumer (×2 consumers ×2 StrictMode). Decision:
a single module-level poll loop per data-mode, shared by all subscribers, with exponential backoff
(30s→cap 5min, reset on success), `AbortController` cancellation on the last unsubscribe (no dangling
requests/rejections on navigation), polling paused while the tab is hidden and resumed immediately on
return, and one shared `{status,error}` snapshot so there is exactly one "API disconnected" state.
`getStatus` now accepts an `AbortSignal`; caller-initiated aborts are distinguished from real errors.
