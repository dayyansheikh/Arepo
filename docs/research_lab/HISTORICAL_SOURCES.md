# Free historical sources for exploratory ML (2026-10-11)

Evidence role `exploratory_historical`: development data only. Licence notes are recorded, rights are out
of scope by standing decision. Code: `backend/astrolabe/research_lab/history_sources.py`, tests
`backend/tests/unit/test_research_lab_history_sources.py`, pilot `backend/scripts/pilot_history_sources.py`.
Outputs (hashed ids only): `data-dumps/research_lab/history_sources/` (about 244 MB of the 1 GB cap).

## Verdicts

| Source | Free, no key | Verdict |
|---|---|---|
| pmxt v2 hourly parquet (`r2v2.pmxt.dev`) | yes | **Use for books.** Works, range-readable, market-sorted |
| Hugging Face mirror `Joseph3222/polymarket-orderbook` | yes | Fallback and 1-minute L2 rollup; also covers v1 era; not tested here |
| Data API `/activity?user=` | yes | **Use for wallet history.** Works, ascending sort, time window |
| Goldsky Polymarket subgraphs (orderbook, activity, pnl) | n/a | **Dead.** Return `ENDPOINT_DEPRECATED`: paused after the V2 migration, "stale and incorrect" |
| Goldsky Edge Data API (`/polymarket/activity`, `/positions`) | no | **Skipped.** Needs an `x-api-key`; unauthenticated calls get HTTP 402 (x402 payment, 0.005 USDC) |

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
- **Size/cost:** files are sorted by `market`, so passing `condition_ids` prunes row groups by market
  min/max. Pilot: 20 tokens at 2026-08-01T12:30, 13 of 159 row groups, 30 range requests, 91 MB, 16-19 s
  (two hours read because of lookback). Without condition ids only weak `asset_id` stats exist and
  nearly a full hour (0.5 GB per hour) is read: always pass condition ids (Gamma gives them).
- **Result:** 18 two-sided, 2 one-sided, 0 crossed, 0 no-book. Snapshot age (t minus last applied event)
  median 29 min, max 44 min: illiquid tokens are stale, so keep `receipt_ts_ms` as a staleness feature.
- **Output shape:** `book_sweep.ROW_COLUMNS` plus `condition_id`, `receipt_ts_ms`, `venue_ts_ms`,
  `crossed`, `source`; `market_id` empty (joined later). Event-reconstructed, no sweep lag. CC BY 4.0
  per the mirror; pmxt's own terms unverified.

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
- **Left-censoring:** history starts when the Data API starts indexing a wallet; record coverage start.
- **Cost and limits (pilot, 200 wallets from the most recent global trades, as-of their trade time):**
  no throttling seen (30 parallel probes all HTTP 200, no 429, no rate-limit headers); we ran at 0.25 s
  spacing (at most 4 req/s) with backoff on 429/5xx. Latency p50 0.39 s, p95 0.78 s. 4,496 requests,
  22.5 per wallet, 0 errors, 235 MB of cache for 200 wallets (about 1 MB per heavy wallet).
- **Skew:** a recent global-trade sample is bot-dominated (median 17,485 prior trades; 135 of 200 hit the
  60-request cap, so counts are lower bounds while first-trade time stays exact; none was new). Cost is
  driven by wallet activity. For new-wallet features use `first_trade()` (1 request, exact).
- **Privacy:** raw addresses reach `WalletHistory` only as request parameters; the HMAC key is
  `~/.arepo/wallet_hash_key` (`wallet_sidecar.hash_wallet`). Caches and manifests hold hashes, timestamps
  and USDC sizes only; error text never contains URLs. Nothing labels a wallet as informed.

## Historical features for the history ML run (2026-10-12)

Runner: `backend/scripts/run_history_features.py {books|wallets|finalize}`; heavy steps wait for
`arepo_pass.sh` and for swap headroom (`heavy_gate`), one step at a time.

**Book features** (`history_sources/book_features/book_features.csv.gz`, loader `load_book_features`).
Join keys: `market_id` (str, Gamma id) and `origin_ts` (float epoch s = panel `t_i`), 6h grid, outcome-0
token, pmxt window minus the 06-12..06-17 gap. Run on `h1_first` only: `h2_main`'s panel appeared after
the run (43,902 pairs); progress is per origin, so adding it needs a per-pair resume first. Columns: `sw_*` raw (as
`ml_panel.SW_COLUMNS`), `ml_sw_*` computed by ml_panel's own functions, `state`, `crossed`,
`receipt_ts_ms`, `venue_ts_ms`, `evidence_role`. Both clocks must be at or before `origin_ts`; an origin on
the hour reads the previous hour's file. `sw_book_age_s` is origin minus the last applied event's venue
time (not a sweep batch lag). Crossed books give NaN features.
- Coverage: 52 of 448 origins (11.6%), spread by a stride-7 order over the whole window, 2,420 of 22,969
  (market, origin) pairs, 172 markets. States: 1,190 two-sided, 50 one-sided, 4 crossed, 1,176 no_book
  (no `book` event within 1 hour lookback; illiquid tokens, NaN not 0). Median spread 0.034.
- Cost: 28.2 GB streamed, 10,856 range requests, 4,907 s (94 s and about 540 MB per origin; row-group
  pruning is weak because 50 markets per origin touch about half the market-sorted row groups). Full
  coverage would be about 11 h and 240 GB; the output is 2 MB. Raw hours are never stored.
- Use as a subsample of origins (missingness is by origin, not by market). `no_book` is informative about
  illiquidity but also about lookback length; do not treat it as 0 depth.

**New-wallet features** (`new_wallets/new_wallet_features_{h1_first,h2_main}.csv.gz`, loader
`load_new_wallet_features`; same join keys, all panel rows). The backfill trades keep
only wallet hashes, which cannot be inverted, so the runner re-reads `/trades?market=` transiently,
re-hashes with the same key, and discards the addresses. Per wallet one `/activity` request
(`type=TRADE`, ascending, `limit=1`, `end` = the wallet's earliest stored trade time): exact first trade,
causal by construction (1 request instead of the 2 allowed). Cache `first_trade.jsonl` holds hashes only.
- Features over trades in [t-24h, t): `nw_n_trades_24h`, `nw_cov_vol_24h` (volume share with a known
  first trade), `nw_share_new{1,7,30}d`, `nw_n_new{1,7,30}d`. A trade counts as new at N days when
  `trade_ts - first_trade_ts < N days`. NaN when covered volume is zero or a truncated trade history does
  not reach the window start.
- Coverage: 9,621 wallets looked up (cap 20,000; 0 errors; 9,634 requests; p50 0.08 s; 4,200 s budget,
  about 2.3 lookups/s). Trade pass scanned 330 panel markets (491 requests) before the budget split. h1: of
  179,794 rows 81,557 have trades in the window, 57,141 a share, median covered volume 0.40, means new1d
  0.003, new7d 0.021, new30d 0.096. h2: 420,937 rows (1,759 markets), 120,364 with trades, 80,643 with a
  share, median coverage 0.45. Shares are lower-coverage proxies; rerun `wallets` to extend (resumable).
- Left-censoring: first trade is as seen by the Data API (Polymarket proxy wallets only).

## Politeness and priority

`RateLimiter` spaces requests by 0.25 s, honours retry-after, caps backoff at 30 s and takes a `gate`
(pilot and runner wait while `arepo_pass.sh` runs). `check_disk_cap` enforces the 1 GB cap on every write.

## Recommendation

1. Books: pmxt v2 via `load_book_snapshots(t, tokens, condition_ids=...)`, development data only; reduce
   on the fly. Full origin coverage costs hours per panel: extend by resuming, not by loosening lookback.
2. Wallets: Data API `/activity` (`first_trade`, or `lookup` for counts). Goldsky subgraphs are dead and the
   Edge API is paid. `vgregoire/polymarket-users` (to 2026-03-29, maker and taker wallets) stays the only
   bulk free fill source; untested here.
3. Open: pmxt subscription completeness is unaudited; Data API coverage start is unknown.
