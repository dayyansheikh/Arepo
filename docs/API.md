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
`status` field (or as the top-level body for `/api/status`) — never assumed from the request.

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
for `live` mode — fast discovery-metadata only).

**Query parameters:**

| Name | Type | Default | Notes |
|---|---|---|---|
| `search` | string | — | Case-insensitive substring match against the question |
| `category` | string | — | Exact match (case-insensitive) |
| `status` | string | — | Exact match, e.g. `active` \| `closed` \| `archived` \| `resolved` \| `unknown` |
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
  "why_it_matters": "Clusters of unusual return, volume, imbalance and liquidity shifts can precede or accompany genuine repricing — worth investigating, not proof of anything.",
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
    "Deterministic synthetic demo dataset — results do not generalise to live markets.",
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
  midpoint, missing book side, etc.) — this is deliberate, not a bug; see
  `docs/methodology.md` for exactly when each value is `null`.
- `data_quality` is one of `good` \| `limited` \| `poor` \| `unavailable`.
