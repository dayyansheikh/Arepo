# Historical sources verification, batch A (sources 1-3 + official endpoints), written 2026-10-11 after the crash

Written by the resumed subagent from in-context findings; no sha256 were recorded and all sample files were lost with /tmp.

## Report A: historical Polymarket sources (written from in-context findings after the crash; no files written)

**Manifest caveat:** I never computed sha256 for any download. The crash happened before that step, so **no hashes exist.** All the files below are deleted. Sizes come from HEAD requests or `ls`.

| File (deleted) | URL | Bytes | sha256 |
|---|---|---|---|
| data_quality.parquet | huggingface.co/datasets/DineshKumar8399/polymarket-orderbook-dataset/resolve/3030329b…/data_quality.parquet | 2,231 | not recorded |
| labels.parquet | same base | 743,684 | not recorded |
| markets.parquet | same base | 3,781,074 | not recorded |
| watch_quotes.parquet | same base | 8,169,867 | not recorded |
| quotes/dt=2026-08-01/data_0.parquet | same base | 2,041,037 | not recorded |
| pmxt rg40 extract (footer plus row group 40 of 2026-08-01T12, about 5.27 MB fetched) | r2v2.pmxt.dev/polymarket_orderbook_2026-08-01T12.parquet (full file 477,191,092) | ~5.3 MB | not recorded |
| marketlens ufc-330-2026-08-16/ (69 parquet files, markets.csv, snapshots.csv, README) | github.com/marketlenstrade/polymarket-historical-data (sparse clone) | 5.1 MB | not recorded |

### 1. DineshKumar8399/polymarket-orderbook-dataset — NOT-USABLE for AREPO
- **Licence:** the repo LICENSE and NOTICE say CC BY 4.0 (author "Dinesh Gopalakrishnan"), which allows commercial use and redistribution with attribution. Whether the venue's terms allow recording and redistributing this data is UNVERIFIED.
- **Venue (critical):** this is **Polymarket US** (the CFTC exchange at gateway.polymarket.us), not global Polymarket. Slugs look like `asc-mlb-wsh-lad-2026-09-04-pos-1pt5`. The gateway resolves that slug to market id 602766, and Gamma returns `[]` for it. The README only ever says "a prediction market".
- **Provenance:** the author's own poller. A "broad sweep" took top of book about every 2 minutes, and a "watchlist" polled about 12 active markets every 20 seconds.
- **Size:** the parquet files are not in git. Hugging Face holds 70 files, 222,992,191 bytes in total, with 62 daily quote partitions of 0.8–4.1 MB each. Daily GitHub release tarballs are about 200 MB.
- **Schema:** `quotes` has ts, slug, category, bid, ask, mid, spread, volume24hr, segment. `watch_quotes` adds `last_traded`. `labels` has slug, y and source. `markets` has slug, question, category, n_snaps, first_ts and last_ts.
- **Verified coverage:** markets has 314,123 slugs (310,000+ are sports). The repo description claims "237M obs / 164,709 markets" but the README claims "484M / 314,123", so the two contradict each other. The 2026-08-01 partition has 4,499,483 rows across 20,178 slugs.
  - That day has only 360 distinct timestamps, with poll gaps of 122–129 seconds. 360 polls at about 2 minutes covers only about 12 hours, so roughly half the day is missing.
  - **Rows per poll are capped at 12,400–12,500**, which looks like a pagination ceiling. Each poll is therefore an incomplete slice of the universe.
  - On that day 1,180,047 rows have both bid and ask null, and `volume24hr` is 100% null.
  - Labels: 187,094 in total, of which 169,458 come from the API and 17,636 are "convergence" labels inferred from price.
  - Watch-feed gaps: 07-17 to 07-22, 07-23 16:19 to 07-24 05:00, and 08-01 08:57 to 19:31.
- **Clock:** one timestamp per poll, in whole seconds with microsecond 0, from the collector. There is no exchange timestamp.
- **Identity:** slug only. There is no condition_id or token_id.
- **Verdict:** wrong venue, top of book only, an incomplete capped universe, missing hours, and no Polymarket keys.

### 2. pmxt archive v2 — LIMITED, but the most AREPO-compatible
- **Docs:** archive.pmxt.dev timed out and refused connections from here, so the docs page went unread. The following comes from a search snippet and is UNVERIFIED: free, no credentials, CLOB WebSocket market channel, stored in Cloudflare R2, recording from 2026-04-13T19 UTC, and v1 missed about 50% of markets. **The licence and terms are UNVERIFIED.**
- **Access:** files are at `https://r2v2.pmxt.dev/polymarket_orderbook_YYYY-MM-DDTHH.parquet`, one per UTC hour. Requests need a curl-like User-Agent, or they get a 403.
- **Coverage I verified with HEAD requests:**
  - Hourly files exist from 2026-04-13T19 through **2026-08-10T00**.
  - Every later hour I probed returns 404: 08-10T01 onward, 08-11 to 08-20, 09-01, 09-15, 09-25, 10-01, 10-05, 10-09 and 10-10. The bucket appears to have stopped or moved, which is UNVERIFIED.
  - Over 07-04 to 08-10T00 there are 889 hourly files with **no missing hour**. Sizes range from 49 MB to 687 MB, median 467 MB, which is about 11 GB a day. The 49 MB hour (07-28T08) suggests a partial outage.
- **Schema (from the 08-01T12 footer: 82,705,648 rows, 79 row groups, Arrow 24):** timestamp_received, timestamp (both ms UTC), market (66-character hex condition_id), event_type, asset_id (token_id), bids/asks (JSON full-depth arrays on `book` events), price, size, side, best_bid, best_ask, fee_rate_bps, transaction_hash, old_tick_size, new_tick_size.
- **Row group 40 sample (1,048,576 rows):**
  - Event mix: price_change 1,047,054, book 1,002, last_trade_price 492, tick_size_change 28.
  - It covers 1,012 markets and 2,022 assets. Whole-file distinct market counts are UNVERIFIED because that scan never finished.
  - Book snapshots carry a median of 38 levels (maximum 172).
  - Receive minus exchange lag: p1 28 ms, p50 123 ms, p99 284 ms, maximum 189 s, none negative. **This is consistent with live capture rather than reconstruction.**
  - Trades carry a transaction hash. I confirmed condition 0x7df5… and token 8811… against Data API `/v2/trades`.
- **Biases:** there are no wallets (they can be joined from the Data API). Completeness of WebSocket subscriptions, meaning universe coverage, is UNVERIFIED. Book state between snapshots has to be rebuilt from price_change deltas. Files are very large for our disk.
- **Verdict:** usable for development on 2026-04-13 to 2026-08-10 if the licence and completeness check out. There is no data after August 10.

### 3. marketlenstrade/polymarket-historical-data — LIMITED (illustration only)
- **Licence and provenance:** LICENSE is CC BY 4.0, attributed to "Marketlens, https://marketlens.trade". The vendor says it has recorded every order-book update since 2026-03-01. The repo is a 7-event sample built by `tools/build.py` with SDK 1.8.3. The full archive needs an API key, which is out of bounds.
- **Verified sample (ufc-330):** 69 markets and 118,566 rows: delta 81,290, snapshot 24,724, trade 12,552, and 72 reseed snapshots. These match the README.
- **Schema:** event_type, t (int64 ms), price, size, side, trade_id, is_reseed, bids, asks. `markets.csv` has the vendor UUID market_id, **condition_id**, outcomes, winning_outcome, times, volume and data_start/end. `snapshots.csv` has derived top-of-book and depth figures.
- **Clocks and identity:**
  - There is **one clock** (`t`), and it is undocumented whether it is the exchange or receive time.
  - There is no token_id per row, so which outcome a file covers is not explicit.
  - trade_id is a vendor id, not a transaction hash, and there are no wallets.
- **Biases:**
  - "Trade-aligned compact" format: book changes between trades are folded together, so intermediate book states are lost.
  - Chapters were selected by **resolution date**, so the sample is resolved markets only.
  - `keep_complete()` **deletes any market with a gap of more than 5 minutes between snapshots**, which is survivorship selection.
  - Anomaly (UNVERIFIED): two snapshots 14 seconds apart show very different depth (0.57 bid size 64,276 versus 3,000).
- **Verdict:** a small curated sample. It cannot support universe-level or causal work.

### 4. Official endpoints
- **CLOB `GET https://clob.polymarket.com/prices-history`:**
  - Parameters: `market` (token_id), `startTs`, `endTs`, `interval` (the docs list max, all, 1m, 1d and 6h among others), and `fidelity` in minutes (default 1).
  - The response is `{history:[{t,p}]}`: a single price per point, with no bid, ask or size.
  - My probe of one hour on 2026-08-01 for token 8811… returned points about every 57–72 seconds, all p = 0.9885.
  - **`interval=max` returned an empty history for the same resolved market.** Retention or behaviour on closed markets is uncertain.
  - It is a server-side sampled series fetched retrospectively. Whether p is the mid or the last trade, and whether past values ever get revised, is UNVERIFIED. Treat it as a resampled backfill, not as point-in-time quotes.
- **Data API:**
  - v1 `/trades` uses limit/offset, and **offset stops at 10,000 rows**. v2 `/v2/trades` is cursor-only and takes `condition` (not `market`). Neither needs authentication.
  - Fields observed: proxy_wallet, side, token_id, condition_id, size, price, timestamp (seconds), title, slug, event_slug, outcome, outcome_index, name, pseudonym, transaction_hash.
  - Rate limits: `/trades` 200 per 10 s, `/v2/trades` 300 per 10 s, CLOB general 15,000 per 10 s, Gamma `/markets` 300 per 10 s. The specific limit for prices-history was not captured.
  - Gamma market listing uses keyset pagination (`after_cursor`; offset is rejected). I did not probe closed markets.
- **Verdict:** trades are fine as an on-chain-anchored record. Prices-history is only a coarse, retrospective, last-or-mid line.

### Overall
None of the three can substitute for AREPO's own prospective capture. pmxt v2 is the only candidate with AREPO keys and both clocks. It needs a licence check and a completeness audit, and it covers April 13 to August 10 only.

