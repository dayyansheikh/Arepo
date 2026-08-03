# API Reference

Base URL (local): `http://localhost:8000`. Interactive OpenAPI/Swagger UI is served at
**`/docs`** (and the raw schema at `/openapi.json`) whenever the backend is running.

All endpoints are `GET`-only, read-only, and require no authentication (Astrolabe holds no
credentials and never trades). CORS is restricted to the configured `CORS_ORIGINS` (see
`docs/deployment.md`); only `GET`/`OPTIONS` are allowed cross-origin.

## The `mode` query parameter

Every data-bearing endpoint accepts an optional `mode` query parameter:

| Value | Meaning |
|---|---|
| `live` | Real-time public Polymarket Gamma + CLOB REST |
| `cached` | Most recently ingested snapshot from local storage |
| `replay` | Committed, deterministic synthetic demo dataset |

If omitted, the server's configured default is used (`DEFAULT_MODE`, `live` by default), with
automatic fallback live → cached → replay on failure (see `docs/architecture.md`,
"Fallback behaviour"). The mode actually served is always reported in the response's
`status` field (or as the top-level body for `/api/status`) – never assumed from the request.

## The `DataStatus` envelope

Every list/overview/detail/signals response includes a `status: DataStatus` object:

```json
{
  "mode": "live",
  "rest": {
    "name": "clob_rest",
    "state": "connected",
    "last_success": "2026-08-02T18:04:11.203Z",
    "last_error": null,
    "latency_ms": null
  },
  "websocket": {
    "name": "clob_ws",
    "state": "unknown",
    "last_success": null,
    "last_error": null,
    "latency_ms": null
  },
  "last_update": "2026-08-02T18:04:11.203Z",
  "data_age_seconds": 2.4,
  "degradation_reason": null,
  "generated_at": "2026-08-02T18:04:13.601Z"
}
```

`degradation_reason` is `null` when serving the requested (or default) mode cleanly, and a
human-readable string (e.g. `"live unavailable (UpstreamUnavailable); using cache"`) whenever
a fallback occurred.

---

## `GET /health`

Liveness probe. No query parameters.

```json
{
  "status": "ok",
  "app": "Astrolabe",
  "environment": "development",
  "time": "2026-08-02T18:04:13.601Z"
}
```

## `GET /api/meta`

Static application metadata for the frontend. No query parameters.

```json
{
  "app": "Astrolabe",
  "environment": "development",
  "default_mode": "live",
  "modes": ["live", "cached", "replay"],
  "disclaimer": "Astrolabe is a read-only research tool over public Polymarket data. It does not place trades. Signals flag statistically unusual behaviour for investigation and are not evidence of insider activity, nor a claim of profitability."
}
```

## `GET /api/status`

Current resolved data mode and source health, with no market data attached.

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `mode` | string | server default | `live` \| `cached` \| `replay` |

**Response:** a `DataStatus` object (see above), returned directly as the response body.

## `GET /api/overview`

The dashboard: top movers, most active, highest volume, widest spreads, and recent signals.

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `mode` | string | server default | `live` \| `cached` \| `replay` |

**Response shape** (`OverviewResponse`):

```json
{
  "top_movers": [ /* MarketCard[] */ ],
  "most_active": [ /* MarketCard[] */ ],
  "highest_volume": [ /* MarketCard[] */ ],
  "widest_spreads": [ /* MarketCard[] */ ],
  "recent_signals": [ /* Signal[] */ ],
  "status": { /* DataStatus */ }
}
```

`MarketCard` shape:

```json
{
  "id": "559651",
  "question": "Xi Jinping out before 2027?",
  "slug": "xi-jinping-out-before-2027",
  "category": "Politics",
  "status": "active",
  "tags": ["Politics", "China"],
  "volume": 11651725.98,
  "volume_24hr": 18620.39,
  "liquidity": 272830.84,
  "end_date": "2026-12-31T00:00:00+00:00",
  "top_probability": 0.0455,
  "top_outcome": "Yes",
  "spread": 0.01,
  "abs_movement": 0.006,
  "signal_strength": 0.42
}
```

## `GET /api/markets`

Search / filter / sort / paginate the market list (compact cards, no per-token network fetch
for `live` mode – fast discovery-metadata only).

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `search` | string | – | Case-insensitive substring match against the question |
| `category` | string | – | Exact match (case-insensitive) |
| `status` | string | – | Exact match, e.g. `active` \| `closed` \| `archived` \| `resolved` \| `unknown` |
| `sort` | string | `volume` | One of `volume` \| `volume_24hr` \| `liquidity` \| `end_date` |
| `limit` | integer | `50` | `1`–`200` |
| `offset` | integer | `0` | ≥ `0` |
| `mode` | string | server default | `live` \| `cached` \| `replay` |

**Response shape** (`MarketListResponse`):

```json
{
  "markets": [ /* MarketCard[] */ ],
  "total": 47,
  "limit": 50,
  "offset": 0,
  "status": { /* DataStatus */ }
}
```

## `GET /api/markets/{market_id}`

Full detail for one market: outcomes with per-outcome analytics, price history, and signals.

**Path parameters:** `market_id` (string, required).

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `mode` | string | server default | `live` \| `cached` \| `replay` |

**Errors:** `404` with `{"detail": "market not found"}` if `market_id` does not resolve in
the active mode.

**Response shape** (`MarketDetailResponse`):

```json
{
  "market": {
    "id": "559651",
    "question": "Xi Jinping out before 2027?",
    "slug": "xi-jinping-out-before-2027",
    "description": "This market will resolve...",
    "category": "Politics",
    "status": "active",
    "tags": ["Politics", "China"],
    "volume": 11651725.98,
    "volume_24hr": 18620.39,
    "liquidity": 272830.84,
    "tick_size": 0.001,
    "end_date": "2026-12-31T00:00:00+00:00",
    "outcomes": [
      {
        "name": "Yes",
        "token_id": "55115...",
        "implied_probability": 0.0455,
        "implied_probability_normalized": 0.0453,
        "best_bid": 0.04,
        "best_ask": 0.05,
        "midpoint": 0.045,
        "spread": 0.01,
        "relative_spread": 0.222,
        "book_imbalance": 0.31,
        "near_mid_depth": 4820.5,
        "volume": 11651725.98,
        "rolling_volatility": 0.006,
        "movement_1h": 0.003,
        "zscore": 1.42,
        "signal_strength": 0.28,
        "data_quality": "good",
        "confidence": 0.26
      }
    ],
    "price_history": {
      "55115...": [ {"t": "2026-08-02T10:00:00+00:00", "p": 0.041}, {"t": "2026-08-02T10:10:00+00:00", "p": 0.045} ]
    },
    "signals": [ /* Signal[] */ ],
    "limitations": "Implied probabilities are spread/fee-contaminated risk-neutral estimates. Signals are screening heuristics, not evidence of insider activity or profit.",
    "data_source": "live"
  },
  "status": { /* DataStatus */ }
}
```

## `GET /api/signals`

The ranked list of current composite-anomaly signals across the enriched market set.

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `limit` | integer | `25` | `1`–`100` |
| `mode` | string | server default | `live` \| `cached` \| `replay` |

**Response shape** (`SignalsResponse`):

```json
{
  "signals": [ /* Signal[] */ ],
  "status": { /* DataStatus */ }
}
```

`Signal` shape (used in `overview.recent_signals`, `markets/{id}.signals`, and
`signals.signals`):

```json
{
  "kind": "composite_anomaly",
  "token_id": "55115...",
  "market_id": "559651",
  "value": 0.42,
  "strength": 0.42,
  "direction": "up",
  "detected": "Recent behaviour is statistically unusual versus this market's own history (components: unusual_return, book_imbalance).",
  "method": "Weighted mean of normalised components (|return z-score|, volume acceleration, book imbalance, spread change, depth change), each saturating at a documented cap; weights renormalised over available components. See docs/methodology.md.",
  "why_it_matters": "Clusters of unusual return, volume, imbalance and liquidity shifts can precede or accompany genuine repricing – worth investigating, not proof of anything.",
  "limitations": "Screening heuristic only. Not evidence of insider activity; not a profit signal. Sensitive to the chosen weights, caps and windows, which are assumptions.",
  "components": [
    {
      "name": "unusual_return",
      "raw_value": 1.42,
      "normalized_value": 0.355,
      "weight": 0.35,
      "explanation": "|rolling z-score of additive returns|"
    }
  ],
  "data_quality": "good",
  "confidence": 0.39,
  "window": "34 obs",
  "computed_at": "2026-08-02T18:04:11.203Z"
}
```

## `GET /api/replay/backtest`

Runs the look-ahead-safe anomaly-signal backtest over the committed replay dataset. Always
runs against the replay dataset (not subject to `mode`).

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `strength_threshold` | float | `0.30` | `0.0`–`1.0`; minimum composite strength to count as a signal |
| `move_threshold` | float | `0.02` | `0.0`–`1.0`; minimum probability-point move counted as a "hit" |
| `horizon` | integer | `5` | `1`–`40`; frames ahead evaluated |

**Response shape** (`BacktestResponse`):

```json
{
  "strength_threshold": 0.30,
  "move_threshold": 0.02,
  "horizon": 5,
  "zscore_window": 20,
  "min_history": 8,
  "sample_size": 16,
  "evaluated": 14,
  "missing_observations": 2,
  "hit_rate": 0.625,
  "false_positive_rate": 0.125,
  "avg_forward_move_directional": 0.018,
  "avg_abs_forward_move": 0.024,
  "events": [
    {
      "market_id": "90001",
      "token_id": "90001-yes",
      "frame": 18,
      "strength": 0.41,
      "zscore": 2.1,
      "direction": "up",
      "entry_price": 0.52,
      "forward_price": 0.57,
      "forward_move": 0.05,
      "followed_through": true
    }
  ],
  "assumptions": [
    "Signal fires when composite anomaly strength >= 0.3.",
    "A 'hit' means price moved >= 0.02 (probability points) in the signalled direction within 5 frames.",
    "Signal generation uses frames 0..i; evaluation uses frames i+1..i+H only.",
    "No transaction costs, slippage or fees are modelled; this is not a P&L simulation."
  ],
  "limitations": [
    "Deterministic synthetic demo dataset – results do not generalise to live markets.",
    "Small sample; no survivorship correction (markets that closed are not repopulated).",
    "Directional 'hit rate' measures follow-through only, NOT profitability or alpha."
  ],
  "dataset_meta": {
    "description": "Deterministic demo scenario for Astrolabe replay/backtest...",
    "disclaimer": "Synthetic data. Not real Polymarket data. For demonstration only.",
    "generated_anchor": "2026-01-15T12:00:00+00:00",
    "n_frames": 48,
    "seed": 42,
    "step_seconds": 60
  }
}
```

## `GET /api/markets/facets`

Distinct real filter values (categories, sports, competitions, statuses) for the Markets page
filter controls, built dynamically from the currently normalised market set. Every list
contains only values genuinely present in the data; nothing is invented, and there is no
placeholder such as `Unknown`: a grouping that is genuinely absent simply does not appear (or
the whole list is empty).

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `mode` | string | server default | `live` \| `cached` \| `replay` |

**Response shape** (`MarketFacetsResponse`):

```json
{
  "categories": ["Politics", "Crypto", "Sports"],
  "sports": ["Basketball", "Football"],
  "competitions": ["NBA", "Premier League"],
  "statuses": ["active", "closed"]
}
```

---

## Prospective cohort evaluation (`/api/cohorts/*`)

The weekly cohort evaluation system (see `docs/methodology.md` §12) exposes typed,
backend-computed responses so the frontend never derives evaluation truth (rankings,
correctness, portfolio values) from loose client state. **These endpoints are read-only.**
Ranking, freezing, forward-price collection, resolution checking and evaluation all run via
the scheduler CLI (`python -m astrolabe.evaluation.cli ...`, see `docs/deployment.md`), never
through the API. Response shapes are the Pydantic models in
`backend/astrolabe/evaluation/schemas.py`.

### `GET /api/cohorts/weeks`

Every recorded cohort week, newest first. Empty before the first `rank`/`freeze` run.

**Response shape** (`list[CohortWeek]`):

```json
[
  {
    "iso_year": 2026,
    "iso_week": 31,
    "label": "2026-W31",
    "week_start": "2026-07-27T00:00:00+00:00",
    "cutoff_at": "2026-08-02T23:59:59+00:00",
    "frozen": true,
    "frozen_at": "2026-08-02T23:59:59+00:00",
    "provenance_class": "prospective",
    "actual_size": 7,
    "target_size": 10
  }
]
```

### `GET /api/cohorts/provenance`

Data provenance: when real prospective tracking began, and how many weeks exist in each
provenance class. Always returns `200`, even with zero cohorts recorded.

**Response shape** (`ProvenanceOut`):

```json
{
  "calculation_version": "arepo-eval-1",
  "first_prospective_week": null,
  "prospective_weeks": 0,
  "reconstructed_weeks": 0,
  "synthetic_weeks": 1,
  "note": "Prospective cohorts are real signals frozen at the weekly cut-off and tracked forward. Synthetic cohorts are clearly-labelled demonstrations and are never mixed into prospective statistics."
}
```

`first_prospective_week` is `null` until the first genuinely prospective cohort has been
recorded; it is never backfilled or estimated.

### `GET /api/cohorts/latest`

The most recently recorded cohort's full detail (summary, entries, portfolio): a convenience
wrapper around the endpoint below using the newest entry from `/api/cohorts/weeks`.

**Errors:** `404` with `{"detail": "No cohorts recorded yet."}` if no cohort has been recorded.

**Response shape:** identical to `GET /api/cohorts/{iso_year}/{iso_week}` below.

### `GET /api/cohorts/{iso_year}/{iso_week}`

One ISO week's full cohort detail: the frozen (or provisional) selection, forward-tracking
observations, both evaluation views, and the hypothetical portfolio.

**Path parameters:** `iso_year` (int), `iso_week` (int).

**Errors:** `404` with `{"detail": "Cohort not found."}` if that week has no cohort.

**Response shape** (`CohortDetail`):

```json
{
  "summary": {
    "week": { "iso_year": 2026, "iso_week": 31, "label": "2026-W31", "frozen": true, "...": "..." },
    "calculation_version": "arepo-eval-1",
    "note": null,
    "selected": 7,
    "moved_expected": 4,
    "moved_against": 2,
    "movement_pending": 1,
    "movement_horizon": "24h",
    "resolved_correct": 0,
    "resolved_incorrect": 0,
    "unresolved": 7,
    "plain_summary": "Arepo selected 7 qualifying signals this week. Of those, 4 later moved in the expected direction, 2 moved against it and 1 remain pending, measured at the 24 hour horizon."
  },
  "entries": [
    {
      "rank": 1,
      "market_id": "559651",
      "token_id": "55115...",
      "condition_id": "0xabc...",
      "event_id": "12345",
      "market_question": "Xi Jinping out before 2027?",
      "outcome_name": "Yes",
      "direction": "up",
      "signal_timestamp": "2026-07-28T09:12:00+00:00",
      "expected_close": "2026-12-31T00:00:00+00:00",
      "strength": 0.42,
      "confidence": 0.39,
      "data_quality": "good",
      "value": 1.42,
      "entry_price": 0.045,
      "best_bid": 0.04,
      "best_ask": 0.05,
      "midpoint": 0.045,
      "spread": 0.01,
      "volume": 11651725.98,
      "near_mid_depth": 4820.5,
      "lookback_size": 145,
      "component_scores": [ /* SignalComponent[] */ ],
      "forward": [
        { "horizon": "1h", "observed_at": "2026-08-02T23:59:59+00:00", "price": 0.048 }
      ],
      "resolution": null,
      "evaluation": {
        "movement_horizon": "24h",
        "raw_prob_movement": 0.006,
        "movement_correct": true,
        "resolved": false,
        "resolution_correct": null,
        "pending": true,
        "hypothetical_value": 102.4
      }
    }
  ],
  "portfolio": {
    "stake_per_signal": 100.0,
    "fee_rate": 0.0,
    "spread_assumption": "Entry crosses 50% of the quoted spread; fees 0.0% of stake per position.",
    "total_allocated": 700.0,
    "realised_value": 0.0,
    "unrealised_value": 410.6,
    "pending_value": 300.0,
    "completed_return": 0.0,
    "completed_positions": 0,
    "pending_positions": 7,
    "positions": [ /* PositionOut[] */ ]
  }
}
```

The example figures above illustrate the shape only; see `docs/methodology.md` §12 for exactly
how each value is computed, and `docs/portfolio-report.md` for the honest position on real
results (no real cohort has completed a tracked week on this deployment yet).

---

## `GET /api/replay/scenario`

Metadata and a market list for the committed replay dataset. No query parameters.

```json
{
  "meta": { "description": "...", "disclaimer": "Synthetic data. Not real Polymarket data. For demonstration only.", "n_frames": 48, "seed": 42, "step_seconds": 60 },
  "markets": [ /* MarketCard[] (from the replay dataset) */ ]
}
```

---

## Field-level notes

- All timestamps are ISO-8601 with UTC offset (`+00:00` or `Z`).
- All probabilities/prices are floats in `[0, 1]`.
- Any numeric field may be `null` when not computable (insufficient history, undefined
  midpoint, missing book side, etc.) – this is deliberate, not a bug; see
  `docs/methodology.md` for exactly when each value is `null`.
- `data_quality` is one of `good` \| `limited` \| `poor` \| `unavailable`.

---

## Signal & Historical Refinement additions

### `GET /api/markets/{id}` chart timeline range

The market-detail endpoint now accepts an optional `range` query parameter:

`GET /api/markets/{id}?mode=<mode>&range=<1h|6h|24h|7d|all>` (default `all`).

The returned `price_history` is the series for that range, fetched at a resolution suited to
it (fine 1-minute points for short ranges; a start/end window for `7d`; the full history at
30-minute resolution for `all`). Two fields were added to the market object:

- `chart_range`: the active range.
- `available_ranges`: the subset of `["1h","6h","24h","7d","all"]` that makes sense for this
  market. Ranges longer than the market's age are omitted; `all` is always present.

Signals now also carry `market_question` and `outcome_name`, so a signal can name and link to
the market it refers to.

### `GET /api/historical/screen`

The historical reconstructed retrospective (a separate analysis mode, provenance
`reconstructed`; see `docs/methodology.md` §9a). Reconstructs the composite anomaly signal at a
past cut-off using only real price history up to that moment (no look-ahead), ranks the top-N
distinct markets, and scores them against the real later history. Uses live data; can be slow
(fetches full history per candidate market).

Query parameters:

- `days` (1..30, default 7): how many days before now the cut-off sits.
- `limit` (1..60, default 40): how many active markets to scan (chosen by recent 24h trading
  volume, never by price).
- `top_n` (1..25, default 15).

Response (`HistoricalScreen`):

```json
{
  "provenance_class": "reconstructed",
  "as_of": "2026-07-27T12:00:00+00:00",
  "top_n": 15,
  "universe_considered": 80,
  "eligible": 3,
  "selected": 3,
  "moved_expected_24h": 1,
  "moved_against_24h": 2,
  "pending_24h": 0,
  "entries": [
    {
      "rank": 1,
      "market_id": "…", "token_id": "…",
      "market_question": "…", "outcome_name": "Yes",
      "direction": "up",
      "strength": 0.37, "confidence": 0.30, "data_quality": "good",
      "entry_price": 0.157,            /* the real price AT the cut-off */
      "lookback_points": 1149,
      "components": [ { "name": "movement_abnormality", "normalized_value": 0.42, "weight": 0.20 } ],
      "forward": [ { "horizon": "24h", "price": 0.182, "movement": 0.025 } ],
      "final_price": 0.19, "final_movement": 0.033,
      "direction_correct_24h": true
    }
  ],
  "plain_summary": "Reconstructed the top 3 composite-anomaly signals …",
  "assumptions": [ "…", "…" ],
  "limitations": [ "…survivorship bias…", "…price-only reconstruction…" ]
}
```

Selection is causal: the scan set is chosen by trading activity (not price), and the near-mid
filter is judged on the price at the cut-off, so today's price and later movement cannot change
which markets are considered.

---

## Opportunity intelligence + search additions

### `GET /api/opportunity/board`
The Opportunity Board: markets ranked by a transparent Research Priority score (not expected
profit). Query: `mode`, `top` (default 30), `universe` (candidate markets, default 40).
Response is an `OpportunityBoard` with `cards[]`; each card carries market, outcome, direction,
probability, `research_priority` (0-100), signal strength, confidence, `families[]`,
`n_families`, `high_priority`, `tags[]` (label, family, explanation, methodology_anchor,
data_quality, timestamp), a short explanation, liquidity + `liquidity_quality`, relative spread,
`time_remaining_hours`, data quality and data mode. Trade-flow tags need Live mode.

### `GET /api/opportunity/snapshots` and `GET /api/opportunity/snapshot/{date}`
List the dates for which an immutable daily snapshot exists (newest first), and read one day's
frozen top-N board (spec section 9). A date is written once and never rewritten. Generate with
`python -m astrolabe.opportunity.cli snapshot` (idempotent).

### `GET /api/markets/search`
Full-universe keyword search via Gamma public-search (questions, descriptions, events, tags,
slugs), expanding common company/ticker aliases (e.g. Microsoft <-> MSFT). Query: `q`,
`active_only` (default true), `limit`, `offset`. Response `MarketSearchResponse` includes
`markets[]`, `total`, `expanded_terms[]`, `provenance` and a `note`. An empty result is honest;
Arepo never fabricates a market or shows a stock quote.
