# DECISIONS.md — Astrolabe / Arepo

An append-only log of significant engineering and product decisions, with reasoning.
Newest entries at the top of each section.

---

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
