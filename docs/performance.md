# Performance notes

Measured before optimising (spec §13). All numbers are from this machine; treat them as
relative, not absolute.

## Baseline: the Opportunity Board was the bottleneck

The board endpoint rebuilt the whole board on every request. One live build:

| Metric | Value |
| --- | --- |
| Wall-clock (live, top 30, universe 40) | **6.13 s** |
| Upstream requests per build | **202** (160 CLOB order-book/price/spread + 40 Data-API trades + 2 Gamma) |

Within a build the per-market work is already fanned out with `asyncio.gather`, so the cost is
dominated by the sheer number of upstream calls, not by serial waiting. Rebuilding that on every
page load is what made the default page feel slow.

## Change: stale-while-revalidate cache for the board

`astrolabe/opportunity/cache.py` adds a small async SWR cache, wired into
`GET /api/opportunity/board`:

- **fresh** (< 90 s): serve the cached board, no rebuild.
- **stale** (90 s to 15 min): serve the cached board immediately and refresh once in the
  background.
- **expired / missing**: build synchronously (the caller waits once). A per-key lock means
  concurrent misses trigger a single build, not a stampede.

The response carries `Cache-Control: public, max-age=60, stale-while-revalidate=300` and an
`X-Board-Cache: hit|stale|miss` header. A stale board is **real** data a couple of minutes old
(labelled by its own `generated_at` and the header), never fabricated.

### After

| Path | Latency | Upstream requests |
| --- | --- | --- |
| Cold miss (live) | ~6.1 s (unchanged, once) | 202 |
| Warm hit | **~2 ms** | 0 |
| Cold miss (replay, deterministic endpoint test) | 79 ms | 0 |
| Warm hit (replay) | **2 ms** (39x faster) | 0 |

So the first viewer after a cache expiry still pays the build cost, but every subsequent viewer
within the window is served in single-digit milliseconds, and staleness is bounded and
disclosed.

## Other measures already in place

- The daily immutable snapshot (`/api/opportunity/snapshot/{date}`) is a cheap DB read.
- Frontend routes are statically prerendered where possible; advanced market detail is behind
  progressive-disclosure `details`/`summary` so it renders lazily.

## Known remaining work (not yet done)

- Cancellation of superseded full-universe searches on the Explore page (debounced today; an
  `AbortController` would drop out-of-order responses).
- Reducing the 160 CLOB calls per board build by batching where the public API allows it.
- Lazy-loading the charting/KaTeX bundle on the market-detail route (largest first-load JS).
