# Limitations

Astrolabe is a research and screening instrument, not a trading system or a source of
investment advice. This page states its limitations plainly, without hedging, so a reader can
calibrate exactly how much weight any number from this tool deserves.

## What implied probability is (and is not)

A contract's price is treated as an approximate implied probability, but it is a
**risk-neutral, spread- and fee-contaminated estimate**, not a calibrated real-world forecast.
It can be biased by liquidity conditions, limits to arbitrage, and market sentiment, and it
says nothing about the time value of money or resolution-timing risk. The "normalized" view
(outcome probabilities scaled to sum to 1) removes the book's overround artifact but does not
remove these deeper biases. See `docs/methodology.md` §1.

## Signals are screening heuristics, not proof of anything

Every signal Astrolabe computes – movement z-score, volatility spike, book imbalance, spread
widening, depth shift, and the composite anomaly score – flags behaviour that is
**statistically unusual relative to a market's own recent history**. That is all it claims:

- It is **not evidence of insider trading** or any other misconduct.
- It is **not a profitability claim** or a trading recommendation.
- It is **not validated predictive alpha** – no live, out-of-sample performance evaluation
  has been run against real trading outcomes.

A high anomaly score means "worth investigating further," never "acted upon."

## The backtest uses a synthetic dataset

The only backtest Astrolabe runs (`GET /api/replay/backtest`) is against the **committed,
deterministic, synthetic replay dataset** (`backend/astrolabe/replay/dataset/scenario.json`)
– three fictional markets with hand-planted momentum-continuation and spike-and-revert
episodes, generated with a fixed seed. It is explicitly labelled as synthetic in the dataset's
own metadata (`"disclaimer": "Synthetic data. Not real Polymarket data. For demonstration
only."`). The observed `hit_rate=0.625`, `false_positive_rate=0.125` on a `sample_size=16`
describe how the signal behaves on **this specific constructed scenario**, illustrating that
the backtest machinery is look-ahead-safe and functioning – they say **nothing about how the
signal would perform on real, live Polymarket markets**, and must not be read as a
performance or profitability claim.

Further caveats on the backtest itself:

- **Small sample.** 16 total signal events, 14 evaluable – far too few to draw a statistically
  reliable conclusion even about the synthetic dataset's own dynamics.
- **No survivorship correction.** Markets that "close" within the dataset are not
  repopulated; a real live universe has continuous market entry/exit that this does not model.
- **No transaction costs.** No fees, slippage, or spread-crossing cost is modelled anywhere in
  the backtest – it measures directional follow-through only, not net-of-cost P&L.
- **Directional hit-rate ≠ alpha.** "Followed through" means the price moved past a threshold
  in the signalled direction within the horizon; it does not account for entry/exit
  feasibility, position sizing, or risk.

## Anomaly weights, caps, and windows are assumptions

The composite anomaly score's component weights (`unusual_return: 0.35`,
`volume_acceleration: 0.20`, `book_imbalance: 0.15`, `spread_change: 0.15`,
`depth_change: 0.15`), saturation caps (e.g. `|z|=4` fully saturates the return component),
and the rolling windows used throughout (20-observation volatility/z-score window, 4
-observation movement window, 5-frame backtest horizon, etc.) are **documented assumptions**,
set by inspection during development – not values fit to labelled outcome data. A production
deployment intending to act on these scores would need to re-derive them empirically. See
`docs/methodology.md` §9–10 for the full parameter tables.

## Live coverage depends on Polymarket's public API

Live mode calls Polymarket's public Gamma and CLOB REST endpoints directly, with no
credentials. This means:

- Coverage, availability, and latency depend entirely on Polymarket's public API uptime and
  behaviour, which Astrolabe does not control.
- Confirmed rate limits apply (per `docs/research-notes.md`): `/book` 1500/10s, `/books`
  500/10s, `/price` 1500/10s, `/midpoint` 1500/10s, `/prices-history` 1000/10s, Gamma general
  4000/10s (Cloudflare, IP-based, sliding window). Astrolabe's discovery is bounded
  (`DISCOVERY_LIMIT`, default 60) and its overview enrichment is capped
  (`OVERVIEW_ENRICH = 15` markets deep-fetched per overview request) specifically to stay well
  under these limits, but a busy deployment or an aggressive operator override could still hit
  them.
- Upstream schema drift or missing fields are absorbed defensively by the normalization layer
  (a malformed record is dropped or coerced, not raised), which means degraded-but-not-crashed
  behaviour is possible: a market with unparseable fields simply does not appear, with no
  separate "some data was silently dropped" indicator beyond server logs.

## Docker and public deployment were not executed here

The Dockerfiles and `docker-compose.yml` are authored to specification and validated by
inspection, but `docker compose up` was **not run** in the environment used to build
Astrolabe (no Docker daemon was available), and no public hosting deployment has been
performed (no `gh`/`vercel` CLI or authenticated hosting account was available). See
`docs/deployment.md` for exact build/start commands the operator should run and verify. The
only path actually exercised end-to-end during development is the non-Docker local path
(`uvicorn` + `next dev`).

## Volume-based inputs are limited in live mode

The composite anomaly score's `volume_acceleration` component compares recent incremental
volume against an earlier baseline, computed from a per-token volume history
(`_volume_deltas` in `analytics/backtest.py`; `_volume_acceleration` in `service/enrich.py`).
Polymarket's CLOB REST surface does not expose a **per-token time series of volume** the way
it exposes price history – `LiveSource.get_token_data` in `service/sources.py` therefore
returns an empty `volumes` list in live mode, so `volume_acceleration` is `None` and that
component is simply excluded from the composite score's weighted average (renormalized over
the remaining components) for any live-mode signal. Volume acceleration is fully available in
`cached` mode, where the ingestion pipeline stores successive market-level volume snapshots
over time, and in `replay` mode, where the dataset carries a synthetic per-frame volume
series by construction.

## Data-quality thresholds are calibrated by inspection, not fit

The confidence-penalty thresholds (20-observation "ideal" history, 10% "wide" relative
spread, 100-unit "thin" depth floor, 60-second staleness threshold) are reasonable defaults
chosen by inspection during development, not values derived from labelled data about what
actually constitutes unreliable liquidity or a stale reading on Polymarket specifically. A
different market's typical profile (e.g. a very large, very liquid market vs. a niche,
thinly-traded one) may warrant different floors than the single global set used here.

## Prospective evaluation: no real historical cohorts exist yet

The weekly cohort evaluation system (`docs/methodology.md` §12) tracks signals prospectively:
it records what Arepo would genuinely have selected at the time, freezes the selection weekly,
and evaluates it forward. There is no reconstructed historical snapshot store on this machine,
so **prospective tracking begins at the first genuine `rank --mode live` run** on a given
deployment, not before. No earlier cohort is invented or backfilled. Until that first run (and
until a week has actually elapsed since freezing), `GET /api/cohorts/weeks` and
`GET /api/cohorts/provenance` correctly report an empty or near-empty history. The only cohort
that exists on this machine at the time of writing is the labelled synthetic demonstration
cohort (see below); it is not a claim of real performance.

## The market resolution check is best-effort, not a settlement feed

`MarketService.market_resolution` infers a market's outcome from its own discovery metadata: a
market counts as resolved only once it is closed (or resolved) *and* exactly one outcome sits
at an extreme price (≥ 0.99). This is a heuristic over the same public metadata used elsewhere
in the product, not a connection to a canonical settlement or oracle feed. It can under-report
(a genuinely resolved market that has not settled to an extreme price in the observed metadata
stays "unresolved") and, in principle, could misread an unusual pricing pattern as a
resolution. Resolutions recorded this way are never overwritten once marked resolved, so a
wrong early read would persist; no such case has been observed, but none has been ruled out
either.

## Sport and competition metadata do not survive the cached-mode round-trip

The Markets page's sport and competition facets (`GET /api/markets/facets`) are derived
correctly in live and replay mode. In cached mode, the storage round-trip does not currently
persist the sport/competition fields the way it persists category: a known, accepted gap
noted during the categories work in `CHECKPOINT.md`. A market cached and later served from
`cached` mode may therefore show its category correctly while its sport/competition grouping
is unavailable, even though the same market shows both correctly under `live`.

## The hypothetical portfolio is a simulation, not advice

The Replay page's portfolio figures (stake, allocated total, realised/unrealised/pending
value, completed return) are a simulation over recorded entry prices, quoted spreads and later
observed prices. They assume a fixed stake, a fill that crosses half the quoted spread, and a
configurable fee (default zero): see `docs/methodology.md` §12. This is not real trading,
not a record of executed orders, and not evidence of future profitability. It is not
investment advice.

## Synthetic demonstration data is kept out of real statistics, but is present

To demonstrate that the cohort machinery (selection, freeze, forward tracking, resolution,
portfolio valuation) functions end-to-end before any real prospective cohort has accumulated a
tracked week, this deployment can be seeded with a clearly labelled synthetic cohort
(`python -m astrolabe.evaluation.cli seed-synthetic`, `provenance_class = "synthetic"`). The
Replay page marks any non-prospective cohort with a visible "Synthetic demonstration" badge
and the `GET /api/cohorts/provenance` endpoint reports synthetic weeks as a distinct count.
Synthetic cohorts are never included when aggregating real prospective statistics, but a
reader should not mistake their presence in the week picker for real recorded performance.

## No test-count or coverage claims beyond what was verified

174 backend tests pass and the backend is ruff-clean, and 8 frontend vitest tests pass, all
verified in this environment while writing this documentation (see `FINAL_STATUS.md` for exact
commands and output). No test-coverage percentage is claimed (none was measured).

---

## Signal & Historical Refinement: honest data-availability notes

### The live signal is often a capped book-only reading
Most prediction markets sit still for most of their life. When a market has not genuinely
moved recently, its three price-behaviour features are absent or near-zero, so the composite
anomaly score falls back to whatever order-book features are available and is capped at 0.5 by
the book-only ceiling (see `docs/methodology.md` §9). A strong score, by construction, requires
real recent price movement. This means the live Signal Lab frequently shows moderate,
book-only readings rather than strong anomalies, which is truthful: strong anomalies are
genuinely rare at any given moment.

### The discoverable universe is dominated by pinned long-shots
The markets discoverable through the public Gamma endpoint are, at the time of writing,
overwhelmingly long-shot 2028-election outcomes pinned near 0 (for example "Will [famous name]
win the 2028 nomination?"). These do not move, so they carry no price-behaviour signal. Genuine
near-mid, moving markets exist but are a minority and are not the highest-volume names. The
product deliberately prefers near-mid markets for enrichment, but strong live signals remain
rare simply because few markets are anomalous right now.

### Historical retrospective: real data, but a biased sample
Historical price history is dense and real (verified: most liquid markets return hundreds to
thousands of timestamped points spanning weeks). The reconstruction itself has no look-ahead:
the signal uses only pre-cutoff history and selection never uses today's price (see
`docs/methodology.md` §9a). Its limitations are, honestly:
- **Survivorship bias.** The universe is markets still discoverable now with enough history;
  markets that have since closed or were removed are structurally excluded.
- **Price-only reconstruction.** Historical order books are not available, so the reconstructed
  signal uses price-behaviour features only.
- **Small qualifying sets.** Because few markets are anomalous at any past cut-off, a run often
  reconstructs only a handful of signals rather than a full fifteen, and reports the actual
  number. The forward outcomes are honestly mixed (the signal is a screening heuristic, not a
  predictor) and are never a claim of profitability.

### Chart timeline ranges
`1h`/`6h`/`24h` fetch fine 1-minute resolution; `7d` uses a start/end window; `all` uses the
full history at 30-minute resolution. Ranges longer than a market's age are hidden. A very
quiet market can still show a near-flat line over any range, which is the real data.

---

## Opportunity intelligence: data provenance, privacy and interpretation limits

**Data provenance.** Indicators are computed from public, read-only Polymarket data only: Gamma
market metadata and public search, the CLOB order book and price history, and the public Data
API trade feed (`/trades`). Nothing private or non-public is used, and no order is ever placed.

**Wallet privacy and neutrality.** Trade data includes public proxy-wallet addresses. Arepo
uses them only for neutral aggregate measures (concentration shares, distinct-wallet counts,
activity breadth). It never labels a wallet insider, suspicious, fake or manipulated, never
profiles an individual, and never asserts intent. "Limited activity history" means only that a
wallet is active in few other markets, as an aggregate share of flow.

**Interpretation limits.** The Research Priority score ranks how much a market deserves a look;
it is not expected profit, not a probability of a move, and not advice. Alerts give a research
interpretation, never buy/sell/stake instructions or a profit promise. Trade-flow indicators
need Live mode and enough recent trades; below the minimum sample they do not fire. Historical
order books are not retained, so spread/depth-change components are usually absent. Most markets
are calm most of the time, so strong multi-family opportunities are rare, which is truthful.
