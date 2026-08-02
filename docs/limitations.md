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

Every signal Astrolabe computes — movement z-score, volatility spike, book imbalance, spread
widening, depth shift, and the composite anomaly score — flags behaviour that is
**statistically unusual relative to a market's own recent history**. That is all it claims:

- It is **not evidence of insider trading** or any other misconduct.
- It is **not a profitability claim** or a trading recommendation.
- It is **not validated predictive alpha** — no live, out-of-sample performance evaluation
  has been run against real trading outcomes.

A high anomaly score means "worth investigating further," never "acted upon."

## The backtest uses a synthetic dataset

The only backtest Astrolabe runs (`GET /api/replay/backtest`) is against the **committed,
deterministic, synthetic replay dataset** (`backend/astrolabe/replay/dataset/scenario.json`)
— three fictional markets with hand-planted momentum-continuation and spike-and-revert
episodes, generated with a fixed seed. It is explicitly labelled as synthetic in the dataset's
own metadata (`"disclaimer": "Synthetic data. Not real Polymarket data. For demonstration
only."`). The observed `hit_rate=0.625`, `false_positive_rate=0.125` on a `sample_size=16`
describe how the signal behaves on **this specific constructed scenario**, illustrating that
the backtest machinery is look-ahead-safe and functioning — they say **nothing about how the
signal would perform on real, live Polymarket markets**, and must not be read as a
performance or profitability claim.

Further caveats on the backtest itself:

- **Small sample.** 16 total signal events, 14 evaluable — far too few to draw a statistically
  reliable conclusion even about the synthetic dataset's own dynamics.
- **No survivorship correction.** Markets that "close" within the dataset are not
  repopulated; a real live universe has continuous market entry/exit that this does not model.
- **No transaction costs.** No fees, slippage, or spread-crossing cost is modelled anywhere in
  the backtest — it measures directional follow-through only, not net-of-cost P&L.
- **Directional hit-rate ≠ alpha.** "Followed through" means the price moved past a threshold
  in the signalled direction within the horizon; it does not account for entry/exit
  feasibility, position sizing, or risk.

## Anomaly weights, caps, and windows are assumptions

The composite anomaly score's component weights (`unusual_return: 0.35`,
`volume_acceleration: 0.20`, `book_imbalance: 0.15`, `spread_change: 0.15`,
`depth_change: 0.15`), saturation caps (e.g. `|z|=4` fully saturates the return component),
and the rolling windows used throughout (20-observation volatility/z-score window, 4
-observation movement window, 5-frame backtest horizon, etc.) are **documented assumptions**,
set by inspection during development — not values fit to labelled outcome data. A production
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
it exposes price history — `LiveSource.get_token_data` in `service/sources.py` therefore
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

## No test-count or coverage claims beyond what was verified

121 backend tests pass and the backend is ruff-clean, as verified in the build environment.
No test-coverage percentage is claimed (none was measured), and frontend build/lint were not
independently re-verified as part of writing this documentation.
