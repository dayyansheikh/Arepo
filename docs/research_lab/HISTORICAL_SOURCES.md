# Free historical sources for exploratory ML (2026-10-11)

Evidence role: `exploratory_historical`. Everything here is development data only: never prospective
confirmation, never a sealed holdout by itself. Data rights are out of scope by standing decision; licence
notes are recorded only. Code: `backend/astrolabe/research_lab/history_sources.py`, tests
`backend/tests/unit/test_research_lab_history_sources.py`, pilot `backend/scripts/pilot_history_sources.py`.
Pilot output (hashed ids only): `data-dumps/research_lab/history_sources/` (about 235 MB of 1 GB cap).

## Verdicts

| Source | Free, no key | Verdict |
|---|---|---|
| pmxt v2 hourly parquet (`r2v2.pmxt.dev`) | yes | **Use for books.** Works, range-readable, market-sorted |
| Hugging Face mirror `Joseph3222/polymarket-orderbook` | yes | Fallback and 1-minute L2 rollup; also covers v1 era; not tested here |
| Data API `/activity?user=` | yes | **Use for wallet history.** Works, ascending sort, time window |
| Data API `/trades?user=`, `/closed-positions` | yes | Not causal as-of (closed-positions is current state) |
| Goldsky Polymarket subgraphs (orderbook, activity, pnl) | n/a | **Dead.** Return `ENDPOINT_DEPRECATED`: paused after the V2 migration, "stale and incorrect" |
| Goldsky Edge Data API (`/polymarket/activity`, `/positions`) | no | **Skipped.** Needs an `x-api-key`; unauthenticated calls get HTTP 402 (x402 payment, 0.005 USDC) |
| `archive.pmxt.dev` landing page | - | Unreachable from here (no response); file URLs on `r2v2` work directly |

## (a) pmxt v2 order books

- **URL:** `https://r2v2.pmxt.dev/polymarket_orderbook_YYYY-MM-DDTHH.parquet`, one file per UTC hour,
  HEAD gives size, `Range` requests return 206.
- **Coverage:** v2 from 2026-04-13 (full market coverage); v1 (before 04-13) about half of markets. Stops
  2026-08-10T00 (the loader refuses later times). Gap 2026-06-12 to 06-17. 5-15% of hours missing or corrupt.
  CLOB V2 switch about 2026-04-28 11:00 UTC; fee step 07-10; tick change 07-02 (regime flags needed).
- **Format:** about 0.48 GB/hour (about 11 GB/day), 79 row groups, about 82.7M rows in the probed hour
  (2026-08-01T12). Columns: `timestamp_received`, `timestamp`, `market` (condition id), `event_type`
  (`book`, `price_change`, `last_trade_price`, `tick_size_change`), `asset_id`, `bids`/`asks` JSON strings,
  `price`, `size` (new absolute level total on `price_change`), `side`, `best_bid`, `best_ask`,
  `fee_rate_bps`, `transaction_hash`, tick sizes.
- **Clocks:** both. `timestamp` is the venue clock; `timestamp_received` is the collector receipt clock
  (receive minus venue lag p50 about 0.12 s per the earlier audit). The loader excludes any event with
  EITHER clock after t. No sequence numbers, so within-millisecond order is file order and naive replay
  gives crossed books (flagged in `crossed`, state `crossed`).
- **Granularity:** event stream, so a book at any t is the last `book` event plus later `price_change`s.
  Illiquid tokens often have no event in the hour, so the loader falls back to one earlier hour.
- **Licence note:** CC BY 4.0 per the mirror; pmxt's own terms unverified; credit pmxt.
- **Size/cost:** files are sorted by `market`, so passing `condition_ids` prunes row groups by market
  min/max. Pilot: 20 tokens at 2026-08-01T12:30, 13 of 159 row groups, 30 range requests, 91 MB, 16-19 s
  (two hours read because of lookback). Without condition ids only weak `asset_id` stats exist and
  nearly a full hour (0.5 GB per hour) is read: always pass condition ids (Gamma gives them).
- **Result:** 18 two-sided, 2 one-sided, 0 crossed, 0 no-book. Snapshot age (t minus last applied event)
  median 29 min, max 44 min: illiquid tokens are stale, so keep `receipt_ts_ms` as a staleness feature.
- **Output shape:** `book_sweep.ROW_COLUMNS` (via `book_sweep.parse_book`) plus `condition_id`,
  `receipt_ts_ms`, `venue_ts_ms`, `crossed`, `source`. `market_id` is empty (Gamma id is not in pmxt);
  `batch_receipt_utc` is the receipt clock of the last applied event, not a sweep batch time.
  Differences from live sweeps: no sweep lag, ms clocks, event-reconstructed (not REST) books.

## (b) Wallet history from Data API `/activity`

- **Query:** `GET https://data-api.polymarket.com/activity?user=<addr>&sortBy=TIMESTAMP&sortDirection=ASC
  &start=&end=&limit=500&offset=`. Returns TRADE, REDEEM and other activity with block-time `timestamp`
  (seconds), `side`, `usdcSize`, `transactionHash`. `start`/`end` are inclusive.
- **First-ever trade time:** the first row of an ascending query: 1 request, exact. With `end = t - 1` it
  is causal (only activity before t). Empty result means no prior activity (a new wallet) at t.
- **Prior trade count and volume:** pages of 500. The API rejects `offset > 5000`, so the loader slides
  the `start` window to the last timestamp and de-duplicates by a hashed event fingerprint.
- **PnL:** no causal PnL is available. `closed-positions` and `positions` are current-state (leak the
  future). The module returns a cash-flow proxy `sell + redeem - buy` before t, which counts open
  positions as losses: a descriptive feature, not skill. Proper realised PnL needs per-market resolution
  times from our own labels (matured before t) joined to the fills; not built.
- **Left-censoring:** history starts when the Data API starts indexing a wallet; coverage start must be
  recorded, as the programme doc already requires for F03/F04. Wallets may rotate or use several
  proxy addresses.
- **Cost and limits (pilot, 200 wallets from the most recent global trades, as-of their trade time):**
  no throttling seen (30 parallel probes all HTTP 200, no 429, no rate-limit headers); we ran at 0.25 s
  spacing (at most 4 req/s) with backoff on 429/5xx. Latency p50 0.39 s, p95 0.78 s. 4,496 requests,
  22.5 per wallet, 0 errors, 235 MB of cache for 200 wallets (about 1 MB per heavy wallet).
- **Skew:** a global recent-trade sample is bot-dominated: median 17,485 prior trades, 135 of 200 hit
  the 60-request cap (`truncated`: counts and volume are lower bounds, first-trade time still exact),
  and none was new. Cost is therefore driven by wallet activity, not by the number of wallets. For
  new-wallet features the useful call is `max_requests=2` (about 2 requests, exact first trade, count
  capped at 1,000): about 0.8 s per wallet. Full counts for a market-maker cost up to 60 requests (about 40 s).
- **Privacy:** callers pass the raw address to `WalletHistory.lookup` only; the key is
  `~/.arepo/wallet_hash_key` via `wallet_sidecar.hash_wallet` (lower-cased). Cache files are named by hash
  and hold only timestamps, types, sides, USDC sizes and a 12-hex event fingerprint. Error text never
  contains URLs. The pilot manifest holds hashes only. No labelling of any wallet as informed.

## Politeness and priority

`RateLimiter` default 0.25 s between requests, retry-after honoured, backoff capped at 30 s, optional
`gate` called before each request. The pilot gate waits while `arepo_pass.sh` runs (live prospective
collection has priority); the first pilot attempt was paused externally for that reason. Disk cap check
(`check_disk_cap`, 1 GB) runs before each cache write.

## Recommendation

1. Books: pmxt v2 through `load_book_snapshots(t, tokens, condition_ids=...)`, only for 2026-04-29 12:00
   to 2026-08-09 (post-V2, post-gap care for 06-12..06-17), as development data. Reduce on the fly and
   never store raw hours.
2. Wallets: Data API `/activity` with as-of `end=t-1`, with `max_requests` set per use: 2 for
   first-seen/new-wallet features, higher for counts. Treat counts as lower bounds when `truncated`.
3. Do not use the Goldsky subgraphs (dead) or the Goldsky Edge API (paid). The Hugging Face
   `vgregoire/polymarket-users` fills (to 2026-03-29, maker and taker wallets, all markets) remain the
   only bulk free source for wallet history across many markets; not tested here.
4. Open: pmxt subscription completeness is unaudited; Data API wallet coverage start is unknown; a
   representative (non-bot) wallet sample is needed before sizing a full backfill.
