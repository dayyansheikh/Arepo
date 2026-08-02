# Research Notes — Polymarket public data & prediction-market conventions

> Primary source of truth: official Polymarket documentation (`https://docs.polymarket.com`)
> and direct probing of the public endpoints. All endpoint shapes below were **verified by
> live requests on 2026-08-02** unless marked *(pending confirmation)*.

## 1. Hosts (verified reachable, HTTP 200)

| Purpose            | Base URL                                             | Verified |
|--------------------|------------------------------------------------------|----------|
| Gamma API (meta)   | `https://gamma-api.polymarket.com`                   | ✅ 200   |
| CLOB REST          | `https://clob.polymarket.com`                        | ✅ 200   |
| CLOB market WS     | `wss://ws-subscriptions-clob.polymarket.com/ws/market` | via research agent |
| Docs index         | `https://docs.polymarket.com/llms.txt`               | ✅ 200   |

Public data requires **no** credentials, wallet or private key. This project uses only
read-only public endpoints and never authenticates, never trades, never submits orders.

## 2. Gamma API — discovery & metadata (verified shapes)

### `GET /markets` → **JSON array** of market objects
Useful query params observed: `limit`, `active=true`, `closed=false`, `order=<field>`,
`ascending=<bool>` (e.g. `order=volume24hr&ascending=false`).

Verified fields on a market object (subset, real sample):
```
id: "559651"                       # string
question: "Xi Jinping out before 2027?"
conditionId: "0xa467...743b7"      # condition id (hex)
slug: "xi-jinping-out-before-2027"
outcomes: "[\"Yes\", \"No\"]"          # ⚠ JSON-ENCODED STRING, not array
outcomePrices: "[\"0.0455\", \"0.9545\"]"  # ⚠ JSON-ENCODED STRING of price strings
clobTokenIds: "[\"55115...\", \"19108...\"]" # ⚠ JSON-ENCODED STRING of token-id strings
volume: "11651725.98"              # string number
volume24hr: 18620.39               # number
liquidity: "272830.84"             # string number
liquidityNum / volumeNum: number
active: true, closed: false, archived: false, restricted: true
enableOrderBook: true              # only these have a live CLOB book
orderPriceMinTickSize: 0.001       # tick size
orderMinSize: 5
endDate / startDate: ISO-8601 UTC strings
```
**Key gotcha:** `outcomes`, `outcomePrices`, `clobTokenIds` are **strings containing JSON
arrays** and must be `json.loads`-parsed during normalization. Number-ish fields arrive as
strings *and* as `...Num` numbers inconsistently — normalization must coerce defensively.

### `GET /events` → JSON array of event objects
Event object keys (verified): `id, ticker, slug, title, description, startDate, endDate,
active, closed, archived, liquidity, volume, volume24hr, openInterest, enableOrderBook,
negRisk, markets[], tags[]`. Each event nests a `markets` array (verified: 4 markets on the
sampled event) and a `tags` array — this is the route to **sport/category** filtering.

## 3. CLOB REST — market data (verified shapes)

All keyed by `token_id` (a CLOB asset id = one outcome token; from Gamma `clobTokenIds`).

### `GET /book?token_id=<id>` (verified)
```json
{ "market": "0x..cond", "asset_id": "5511...", "timestamp": "...", "hash": "...",
  "bids": [ {"price":"0.01","size":"2275481.12"}, {"price":"0.02","size":"160059.17"} ],
  "asks": [ {"price":"0.99","size":"66760.15"}, {"price":"0.98","size":"8084.08"} ],
  "min_order_size": "...", "tick_size": "0.001", "neg_risk": false,
  "last_trade_price": "..." }
```
⚠ `price`/`size` are **strings**. ⚠ Ordering is NOT guaranteed to be best-first — observed
`bids` ascending by price (0.01, 0.02, …). Normalization must sort: **best bid = max price,
best ask = min price**. Handle empty `bids`/`asks`.

### `GET /midpoint?token_id=<id>` → `{"mid":"0.195"}` (verified)
### `GET /price?token_id=<id>&side=buy|sell` → `{"price":"0.19"}` (verified)
### `GET /spread?token_id=<id>` → `{"spread":"0.01"}` (verified)
### `GET /prices-history?market=<token_id>&interval=<1d|1w|1m|max>&fidelity=<minutes>` (verified)
```json
{ "history": [ {"t": 1785595806, "p": 0.245}, {"t": 1785596406, "p": 0.245} ] }
```
⚠ Note the param is named `market` but takes a **token_id**. `t` = unix seconds (UTC),
`p` = price (number). Sampled 145 points for `interval=1d, fidelity=10`.

Batch endpoints (`/books`, `/prices`, `/midpoints` via POST) — *(to be confirmed by research
agent; single-token endpoints are sufficient for the core slice.)*

## 4. CLOB market WebSocket — **confirmed against official AsyncAPI + docs**
Sources: `docs.polymarket.com/asyncapi.json`, `/api-reference/wss/market.md`,
`/market-data/realtime-data.md` (fetched 2026-08-02, verbatim).

- **URL:** `wss://ws-subscriptions-clob.polymarket.com/ws/market`
- **Subscribe message** (send on open):
  ```json
  {"assets_ids": ["<token_id>", "<token_id>"], "type": "market"}
  ```
  Field is `assets_ids` (**plural, with `s`** — not `asset_ids`). Optional: `initial_dump`
  (bool, default `true` → server sends a `book` snapshot on subscribe), `level` (1/2/3,
  default 2). Dynamic (un)subscribe without reconnect: `{"operation":"subscribe"|"unsubscribe",
  "assets_ids":[...]}`.
- **Event discriminator:** `event_type` (string). Core market-channel events:
  - `book` — full snapshot: `{event_type, asset_id, market, bids[], asks[], timestamp, hash}`;
    `bids`/`asks` are `{price:str, size:str}`. (`timestamp` is a **string of unix ms**.)
  - `price_change` — delta: `{event_type, market, price_changes[], timestamp}` where each
    change is `{asset_id, price, size, side("BUY"/"SELL"), hash, best_bid?, best_ask?}`.
    **`size == "0"` means that price level was removed.**
  - `last_trade_price` — `{event_type, asset_id, market, price, size, side, timestamp, ...}`.
  - `tick_size_change` — `{event_type, asset_id, market, old_tick_size, new_tick_size, timestamp}`.
  - (`best_bid_ask`, `new_market`, `market_resolved` exist only when `custom_feature_enabled:true`
    — **not used** by Astrolabe; we keep the default minimal subscription.)
- **Heartbeat:** client sends the **plain-text frame `"PING"` every 10s**; server replies
  `"PONG"`. Not JSON. Missing PONGs / no messages for `ws_stale_seconds` ⇒ treat as stale.
- **Dedup:** each `book`/`price_change` carries a `hash`; combined with `event_type`+`timestamp`
  this is the natural dedup key for duplicate-message protection.

## 4b. Confirmed REST rate limits (Cloudflare, IP-based, sliding window)
`/book` 1500/10s · `/books` 500/10s · `/price` 1500/10s · `/midpoint` 1500/10s ·
`/prices-history` 1000/10s · Gamma general 4000/10s. No documented WS connection cap.
⇒ Astrolabe polls politely (`poll_interval_seconds`, bounded discovery) and prefers WS for
live updates. Batch endpoints available: `POST /books`, `POST /batch-prices-history` (≤20).

> ⚠ **Docs-vs-reality discrepancy (important):** the OpenAPI spec documents `GET /midpoint`
> returning `{"mid_price": "..."}`, but the **live endpoint returns `{"mid": "..."}`**
> (directly observed). Normalization accepts **either** key. Treat direct probes as ground
> truth where docs and live behaviour diverge.

## 5. Prediction-market conventions & UX observations (competitive scan)

General conventions common across public prediction-market and financial-analytics UIs
(surveyed broadly, no single product used as a design reference):
- A binary contract's price ≈ market-**implied probability** of the event, in [0,1]. Caveat:
  it is a risk-neutral, fee/spread-contaminated estimate, not a calibrated forecast.
- Users want: fast discovery (search + category/sport filters), a compact per-market view
  (probability, recent movement, volume, spread/depth), and a sense of *data freshness*.
- Common weak patterns to avoid: presenting a single price with no uncertainty/liquidity
  context; conflating stale/cached data with live; opaque "signal" scores with no explanation.
- Opportunity this project targets: **transparent, explainable microstructure signals**
  (movement z-score, order-book imbalance, spread/depth changes) with explicit data-quality
  and confidence, plus deterministic replay so every signal can be re-examined.

## 6. Ethical / correctness boundaries (enforced in product wording)
- Never describe an anomaly as proof of insider trading — only "statistically unusual behaviour
  worth investigating."
- Never claim profitability, predictive alpha, or validated accuracy.
- Never present cached/replay data as live.

_Last updated: 2026-08-02. WS section and batch-endpoint section pending the research agent's
primary-source confirmation._
