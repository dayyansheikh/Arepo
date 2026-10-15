# Historical sources verification, batch B (2026-10-10 ~23:11 UTC+1)

Recovered verbatim from the subagent transcript after the crash. The sample files listed in the manifest lived in /tmp and were LOST in the crash; checksums remain valid identifiers for re-download. Note: this agent exceeded its 150 MB download budget (~320 MB transferred).

# Historical dataset verification, batch B (2026-10-10 22:11 UTC)

I verified sources 4 and 5, plus 4 extra free sources I found and checked myself. No sign-ups, keys or payments were used.

**Report file not written.** The harness blocked writing report files from this subagent. The full report is below; save it to `hist/report_b.md` if you need it on disk.

**Budget breach.** I transferred about 320 MB against the ~150 MB limit:
- **Becker archive:** I asked for a 16 MB range of `s3.jbecker.dev/data.tar.zst`, but 241 MB arrived before the command timed out. I extracted two sample files and deleted the partial archive.
- **Joseph3222 footer:** reading the metadata of one day file over HTTP ranges pulled 56 MB, because the file has 18,170 row groups. Nothing was saved from that read.

Disk currently used by `hist/b/` is 25 MB. pyarrow and numpy 2 are installed in `hist/pylib`, which takes 164 MB of disk.

## 4. polyorderbooks.com/polymarket-data-download
- **Licence and terms:**
  - The Zenodo, Hugging Face and Kaggle releases are CC BY 4.0: commercial use and modification allowed, attribution required.
  - The full archive needs an API key from a free account. Its plan terms are not public, so I did not use it.
  - Kaggle also needs an account.
- **How it was collected** (from the Zenodo record):
  - A PolyOrderbooks collector on the Polymarket websocket book feed writes a row whenever a book changes.
  - Every 60 s it re-reads the full book over REST, because the delta stream has no sequence numbers.
  - Markets were drawn at random from those that resolved, so the release is a sample.
  - About 1 M rows from an earlier collector setup were left out.
- **What I verified:**
  - **Hugging Face dataset:** `polyorderbooks/polymarket-crypto-5min-l2` has 8 parquet files totalling 9.9 MB. `doge.parquet` has 19,883 rows, 44 markets and 88 tokens, covering 2026-08-23 09:04–12:45 UTC.
  - **Zenodo record 22084977** (concept DOI 22084114): 3 parquet files, 45 MB. The md5 of `updown_4h.parquet` matches the record. It has 489,941 rows, 69 markets, 138 tokens and 8 coins, covering 2026-08-21 03:56 to 2026-08-24 12:00.
- **Fields:**
  - Identity and labels: `market_slug`, `coin`, `contract_length`, `token_id`, `outcome`, `winner`, `is_winning_outcome`.
  - Time: `market_end_at`, `captured_at`, `seconds_to_close`.
  - Book: full bid and ask price/size lists, `best_bid`, `best_ask`, and a `crossed` flag.
- **Timestamps:**
  - The only clock is `captured_at`, the collector's receive time.
  - It has microsecond type but every value is a whole second (0 rows have a sub-second part).
  - There is no exchange timestamp, book hash or raw message.
- **Evidence of live capture:**
  - Books are not forward-filled: only 1.1% of consecutive books per token are identical (5,513 of 489,803).
  - The two outcome books mirror each other: Up best bid + Down best ask = 1.00 in 99% of paired snapshots.
  - Crossed books are 1.50% of rows in the 4h file and 1.33% in doge, and they are flagged.
  - Depth is the full ladder: median 97 levels in the 4h file and 28 in doge.
- **Gaps:**
  - "1-second" is a target, not a guarantee: in doge, 18% of gaps are 2 s or longer.
  - The 4h file has 64 gaps over 300 s, up to 7,203 s. They cluster in time (for example 12 tokens at once on 2026-08-22 around 11:00), which looks like collector outages.
- **Identity:** token_id and slug are present. There is no conditionId and no event id.
- **Biases:**
  - Coverage is crypto up/down markets only, resolved markets only, over 3–4 days.
  - The winning outcome is on every row, which is a direct leakage risk for AREPO.
  - The free release is a teaser: 805 markets, against 1.16 M claimed for the paid/API archive.
  - There are no trades.
- **Verdict: LIMITED.** These are real live L2 captures and good for developing depth and imbalance code and test fixtures. They tell us nothing about the general Polymarket universe.

## 5. institute.polymarket.com/data
- WebFetch got a 403; curl got a 200.
- The page is a researcher guide (dated 2026-07-24) to the public Gamma, CLOB and Data APIs.
- It has no downloadable dataset, no archive and no licence beyond links to the docs.
- Its only time-series route is `clob /prices-history`, which is a resampled after-the-fact backfill.
- **Verdict: NOT-USABLE as a dataset.** It is only useful as a glossary of identifiers (conditionId, token_id, proxyWallet, slug).

## Additional sources

### A. Joseph3222/polymarket-orderbook (Hugging Face; a copy of the pmxt archive)
- **Licence:** CC BY 4.0, inherited from pmxt. Attribution to pmxt is required.
- **Content:** raw public websocket events (`book`, `price_change`, `last_trade_price`, `tick_size_change`), collected by pmxt and normalised by the uploader's "polypipe" pipeline.
- **Coverage:**
  - 2026-02-22 to 2026-08-10, 164 day partitions.
  - 2026-06-12 to 06-17 are missing; I confirmed this in the file tree.
  - Before 2026-04-12 (pmxt's v1 archive) only about half of markets are covered. From 2026-04-13 (v2 archive) coverage is claimed to be full.
  - 5–15% of hourly source files are missing.
- **Upstream status:** `archive.pmxt.dev` timed out and `r2v2.pmxt.dev` returned 404, which fits the README's statement that the archive stopped publishing.
- **What I verified** (file footer only, 2026-05-01):
  - The file is 9.14 GB, with 1,820,963,160 events in 18,170 row groups.
  - Schema: `event_ts`, `event_ts_ms`, `condition_id`, `asset_id`, `outcome` (null in v2), `event_type`, `bids_json`/`asks_json`, `price`, `size` (the new absolute size of the level), `side`, `best_bid`/`best_ask`, `transaction_hash` (on trades), tick sizes, `source_archive`.
  - The first row group's statistics span 00:00:00.221 to 00:59:59.747 that day and are v2.
  - The 1-minute rollup is 1.40 GB per day.
- **Clocks:**
  - Timestamps are in milliseconds, but the README says the source had only 1-second resolution.
  - Events in the same millisecond keep file order, and a naive replay gave 10–15% crossed books.
  - There is no separate local receive clock.
- **Verdict: USABLE-FOR-DEV.** It is the only free all-market history of websocket depth and trade prints, with condition_id and token ids. But a day is 8–14 GB, which we cannot store now. It is also a third-party capture with known holes, so it must not count as forward evidence.

### B. trentmkelly/polymarket_historical_data (Hugging Face)
- **Licence:** CC BY 4.0. The collector is `polylake-0.1.0`.
- **Collection:** REST polling roughly every 5 minutes.
  - There are 273 runs on 2026-09-15.
  - Date partitions run from 2026-07-23 to 2026-10-10 (80 days), so it is still being updated.
  - Products: `market_snapshots`, `order_book_depth`, `top_holders`.
- **What I verified** (2 consecutive runs):
  - Each run has 200 rows: exactly 100 markets and 200 tokens. 196 of the 200 tokens appear in both runs.
  - Books are full depth, median 79 levels.
  - Fields: `market_id` (a Gamma id), `asset_id`, `outcome`, `collected_at` (receive time, µs), `source_timestamp` (exchange time, ms), `source_latency_ms`, best bid/ask, `bids_json`/`asks_json`, and `external_prices_json` (Binance tickers).
- **Clocks:**
  - It records both exchange time and receive time, which is good point-in-time practice.
  - Receive time minus exchange time has a median of 3.3 s and a maximum of 96 s, so the exchange timestamp can be stale.
- **Biases:** it keeps only the top 100 markets by recent volume, which is the vendor's filter. There is no conditionId and no trades.
- **Verdict: LIMITED.** The captures are genuinely live, but a top-100 universe breaks AREPO's completeness rule.

### C. vgregoire/polymarket-users (Hugging Face; Akey, Grégoire, Harvie & Martineau 2026, SSRN 6443103)
- **Licence:**
  - CC BY 4.0 covers the authors' processing; cite the paper.
  - Fields that come from the Polymarket API (question, slug, lifecycle timestamps) remain under Polymarket's terms of service.
- **Content:** on-chain CTF Exchange `OrderFilled` events, reconciled to end users, for all markets from 2022-11-11 to 2026-03-29.
- **What I verified** (trades for 2025-06-15, 6.2 MB):
  - 131,203 rows covering 2,285 markets and 3,560 tokens.
  - Columns:
    - `trade_id`: the transaction hash; one transaction can contain several fills.
    - `timestamp`: block time, 1 s precision.
    - `market_id` and `event_id` (Gamma ids), and `prediction_id` (the token id).
    - `price`, `quantity`, `maker_address`, `taker_address`, `taker_bought`.
    - `category` (from the authors' classifier) and `winner`.
  - There is no block number, no log_index and no conditionId.
  - `outcome` is null in 69% of rows.
  - Later days are large: 2026-03-29 is 215 MB.
- **Hazards:** `winner` and the after-the-fact category are on every trade row. Wash trades are flagged in the paper but not filtered out.
- **Verdict: USABLE-FOR-DEV.** It is the best clean free history of trades, wallets and flow across all markets. Drop the leakage columns before use. Order within a block cannot be recovered.

### D. Jon Becker prediction-market-analysis (GitHub, MIT)
- **Archive:** `s3.jbecker.dev/data.tar.zst` is a single 36.0 GB tar, last modified 2026-02-05. Individual files can only be reached by streaming from the start.
- **What I verified** (from a prefix of the archive):
  - Trades are raw `OrderFilled` events: `block_number`, `transaction_hash`, `log_index`, `order_hash`, `maker`, `taker`, maker/taker asset ids, raw amounts, `fee`, and `_contract` (CTF Exchange or NegRisk CTF Exchange).
  - The sample has 10,000 events covering blocks 81,990,766–81,991,048.
  - `timestamp` is null in every row, so trades must be joined to the separate `blocks/` table for times.
  - Markets come from a Gamma snapshot taken 2026-02-03. It includes condition_id, slug and clob_token_ids.
  - `outcome_prices` and `closed` reflect the 2026-02-03 snapshot, so they are after-the-fact values (leakage risk).
- **Licence:** MIT covers the code. No separate licence for the data is stated.
- **Verdict: LIMITED.** The fills are exact on-chain records, and log_index gives true ordering. But the archive is a 36 GB monolith that cannot be partly extracted, it stops at Feb 2026, and times need a block join.

**Listed but not verified:**
- Houroux/polymarket-l2-history: websocket JSONL for markets eligible for liquidity rewards; licence "other".
- TimeSeventeen/Polymarket-v2: daily OrderFilled files, CC BY.
- moose-code/polymarket-onchain-v1: Envio, CC BY, data to Apr 2026.
- SII-WANGZJ/Polymarket_data: no licence tag.

## Sample manifest (files in `hist/b/`)
| file | URL | bytes | sha256 |
|---|---|---|---|
| hf_doge.parquet | huggingface.co/datasets/polyorderbooks/polymarket-crypto-5min-l2/resolve/main/doge.parquet | 581,865 | 69e5bc1697316b270e1a11105d31385fe1f9e63be9ddbc8bb901d39e3d037b32 |
| zen_updown_4h.parquet | zenodo.org/api/records/22084977/files/updown_4h.parquet/content | 14,648,764 | b31a73e7e738b7db0d5a650a8795cd17bc79fcf8aeed74e25b4760eadc50e342 (md5 5a70070f0eda9257d78d5903092fbd34 matches the record) |
| tk_snap_000318.parquet | huggingface.co/datasets/trentmkelly/polymarket_historical_data/resolve/main/data/market_snapshots/date=2026-09-15/20260915T000318Z.parquet | 121,756 | 4130b9cf9a41e396563045b5176dc15569d145e32aeaa8f839e4c07599990d50 |
| tk_snap_000818.parquet | …/date=2026-09-15/20260915T000818Z.parquet | 117,333 | 2d2bbe621f94de0bbd274dd794fd2f7d44b321f45178253269baba3af66c598d |
| vg_trades_2025-06-15.parquet | huggingface.co/datasets/vgregoire/polymarket-users/resolve/main/trades/year=2025/month=06/day=15/data.parquet | 6,177,171 | 5868a3d0ed180f0255db56fcdb4a4a11fe8565bc50c6dcd6890fdf50fae61289 |
| jb/data/polymarket/trades/trades_391390000_391400000.parquet | extracted from the s3.jbecker.dev/data.tar.zst prefix | 1,290,103 | a850fe5aa2372c262fb70d17cd166f85b8438f3f0ab5825eacea48ac4f742ebf |
| jb/data/polymarket/markets/markets_390000_400000.parquet | same | 2,587,261 | f77f75fecd5102050e8faabfd009e6e9d78af9ba3cca4901895dfa7a4508a7fa |
| (deleted) jb_head.tar.zst | s3.jbecker.dev/data.tar.zst (range not enforced) | 241,455,104 | c282bacf30b213081f5ca580a659e118222b4339d06cebe64e7cdaf1135c2c75 |
| (not saved) Joseph3222 footer, 2026-05-01 | huggingface.co/datasets/Joseph3222/polymarket-orderbook/resolve/main/orderbook/date=2026-05-01/data_0.parquet | ~56 MB read via ranges | n/a |

The analysis scripts are in `hist/scripts/`: `pq.py`, `pob.py` and `rpq.py`.

## Ranked shortlist (for development only, never as prospective evidence)
1. **Joseph3222 / pmxt order book:** all markets, websocket depth and trade prints with condition_id and token ids, Feb–Aug 2026. Storage is the blocker: about 8 GB per day, or 1.4 GB per day for the 1-minute rollup.
2. **vgregoire/polymarket-users trades:** on-chain fills for all markets with wallets and block-time precision, 2022 to 2026-03. Drop `winner` and `category`.
3. **polyorderbooks Zenodo:** clean live 1-second L2 with documented defects, crypto up/down markets only. Good for test fixtures and depth-feature code.
4. **trentmkelly:** has both exchange and receive clocks, but only the top 100 markets.
5. **Becker:** exact fills with log_index, but a 36 GB monolith that stops at Feb 2026.

Not usable: institute.polymarket.com, which is a guide, not data.

Across all sources:
- No free source provides a complete-universe book history with sequence numbers and receive clocks.
- Several sources put resolution labels on every row.
- None can replace AREPO's own prospective captures.
