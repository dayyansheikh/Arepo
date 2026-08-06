# Gamma keyset runtime investigation (prompt A2)

_Real, redacted evidence gathered against `https://gamma-api.polymarket.com` on branch
`arepo-final-short-horizon-completion` (environment clock 2026-08-06). Cursors are truncated._

## Exact prior failure

The previous pass concluded keyset "does not advance". The root cause was the **request parameter
name**, not the endpoint or the wrapper. The earlier code sent the returned `next_cursor` back under
the names `next_cursor`, `cursor`, `start_cursor`, `after` and `start`. Gamma's keyset endpoints
ignore all of those and return page one again, so IDs never advanced. The correct parameter is
**`after_cursor`**. The response wrapper (`{ "$schema", "markets"|"events", "next_cursor" }`) and the
endpoint were already correct; only the cursor parameter name was wrong. Additionally the earlier
pass used the unbounded offset endpoint (capped at 2100) instead of the bounded keyset endpoints
with `end_date_min`/`end_date_max`, so it only ever saw the first 2100 global records.

## Endpoints and cursor contract used now

- `GET /markets/keyset` (primary)
- `GET /events/keyset` (independent verification, nested markets extracted)

Contract: first request omits `after_cursor`; each subsequent request sends the previous
response's `next_cursor` as `after_cursor`; stop when `next_cursor` is absent. `offset` is never
sent to keyset endpoints.

## Evidence: request path and parameters

```
GET /markets/keyset?limit=100&active=true&closed=false
    &end_date_min=2026-08-06T...Z&end_date_max=2026-09-05T...Z
```

- response top-level keys: `['$schema', 'markets', 'next_cursor']`
- first item count: `100`
- first `next_cursor`: `CAw6iHno50Y6HFTV...`

Second request adds the cursor:

```
GET /markets/keyset?limit=100&active=true&closed=false&end_date_min=...&end_date_max=...
    &after_cursor=CAw6iHno50Y6HFTV...
```

- second item count: `100`
- overlap with first page (by market id): `0`  => **IDs advanced**
- second `next_cursor`: `k1uHIlaZTmuLTQzy...` (different) => **cursor advanced**

## Termination behaviour

- Bounded tight windows terminate cleanly with `next_cursor` absent. Measured:
  - next 6h window: 50 pages, 4904 markets, terminated (no cursor).
  - 6-24h window: 72 pages, 7148 markets, terminated (no cursor).
- The full bounded 30-day `/markets/keyset` scan terminated normally at **1100 pages / 109,900
  unique markets** in ~88s (no repeated cursor, no failed page).
- `/events/keyset` (bounded, 30 days) returned 137 pages; extracting nested markets yielded 111,687
  unique markets.

## Date bounds are honoured on keyset

Every market returned under the bounded query had an `endDate` inside the window (a 3000-market
sample: 3000 within 30 days, 0 outside). By contrast the legacy offset `/markets` endpoint ignored
`end_date_min`/`end_date_max` and hard-capped at offset 2100, which is why the previous pass could
not reach the within-30-day band from either end.

## Failure handling

- A repeated cursor (`next_cursor` seen before) => scan marked incomplete with a reason.
- A page fetch that exhausts bounded retries (typed `UpstreamUnavailable`/`RateLimited`) => scan
  marked incomplete with the endpoint and page.
- An emergency page guard (5000) => incomplete, never a silent partial universe.

## Reconciliation (prompt A3), real numbers

A complete bounded scan reconciled the two official paths:

| metric | value |
| --- | --- |
| primary unique (`/markets/keyset`) | 109,900 |
| verification unique (`/events/keyset` nested) | 111,687 |
| overlap | 108,533 |
| only-primary | 1,367 |
| only-verification | 3,154 |
| deterministic union | 113,054 |
| identity conflicts | 0 |

The safe deterministic union (113,054) is used; no market returned by one official path is silently
discarded. `complete=true` only when both paths terminated normally and reconciled.

## Windowed fallback (prompt A4)

Because keyset now advances and terminates, the primary path is complete and the windowed fallback
does not fire in normal operation. It remains implemented: if a keyset path is ever incomplete, the
30-day range is scanned as the half-open UTC windows `[0,6) [6,24) [24,72) [72,168) [168,336)
[336,504) [504,720)` hours, and any incomplete window is recursively bisected to a 15-minute floor
before the scan is declared incomplete. This is exercised by the backend tests with a synthetic
transport (a window that caps until bisected).
