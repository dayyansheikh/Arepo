# AREPO data and storage architecture review

Read-only review, 2026-10-10. Labels used throughout:
- **OBS** means measured by me, with the file path given.
- **REP** means taken from docs or from the brief.
- **EST** means my own estimate, with the reasoning shown.

All paths are relative to `data-dumps/` unless stated otherwise.

## 1. Verified measurements

**Disk.** `df` shows 228 GiB total with **8.6 GiB free (96%)** (OBS). That is *lower* than the checkpoint's "about 11.8 GB", and D116's reservation is 13.31 GB. `tmutil destinationinfo` reports "No destinations configured" (OBS), so there is no Time Machine backup. `/data-dumps/` is git-ignored, and the branch is 3 commits ahead of origin (OBS).

**`data-dumps/` total: 21 GB allocated vs about 33.5 GB logical** (OBS, `du -sk` vs `du -skA`). Four captures are already transparently compressed with APFS/HFS compression (ls flag `compressed`):

| Capture | Logical | Allocated | Ratio |
|---|---|---|---|
| `fs2_capture_f1f8…` | 3,485 MB | 554 MB | 6.3x |
| `fs2_capture_a785…` | 3,604 MB | 567 MB | 6.4x |
| `fs2_capture_cb25…` | 4,030 MB | 631 MB | 6.4x |
| `fs2_capture_8297…` | 4,058 MB | 635 MB | 6.4x |

About **17.7 GB of allocated space is still uncompressed**:
- `0da4` (D088, kept as canonical): 3.6 GB
- `eaec`: 2.6 GB
- `e9d0` (D114 frame): 2.6 GB
- `3a4f`: 1.5 GB
- 8 `fs2_selection_panel_*` dirs: about 6.4 GB
- `fs2_selection_56ff…`: 0.55 GB
- `95cb`, `8e6a`, `ff7f`: 1.0 GB together

**Inside an fs2 capture** (OBS, per-file-type tally over all page dirs). Each Gamma page (100 markets) is a directory holding:
- `raw.bin`: the exact response body, about 580–730 KB of JSON. It is gzip only in `e9d0`, where it is about 57 KB, so gzip gives about 10x.
- `parsed.json`: about 105% of raw.
- `frame_page.json`: about 40% of raw.
- `receipt.json`: about 2.1 KB of clocks, headers, hashes and source contract.
- 3 ack files.

So about **58% of every capture's logical bytes are deterministic derivatives of `raw.bin`**. For example, `0da4` is raw 1,525 MB + parsed 1,591 MB + frame 615 MB. Selection panels are a further full-frame set of `projection.json` files, about 353 KB per page (OBS, `fs2_selection_panel_gzip_pilot_20261010_1/pages/*`). These too are derivatives of the frames.

**Compact universe snapshots** (`research_lab/snapshots/*`; all OBS from manifest plus `gzip -dc | wc`):

| capture | rows | duration | rows.csv.gz | decoded csv | raw Gamma bytes fetched (not kept) |
|---|---|---|---|---|---|
| 20261010T192208Z | 276,706 | 7m07s | 15.48 MB (no token col) | n/a | 1,785.5 MB |
| 20261010T193535Z | 275,906 | 6m42s | 27.73 MB | n/a | 1,781.2 MB |
| 20261010T204959Z | 272,660 | 11m44s | 27.44 MB | 93.6 MB | 1,762.8 MB |

- "276k markets in 7 min" is OBS for the first capture only. The third capture took 11m44s.
- "16 MB snapshot" is OBS only for the first capture, which lacked `clob_token_id_0`. Current captures are **27.4 MB, about 100 B/market**. The single 78-digit token-id column costs about 12 MB per snapshot.
- 2,727–2,768 sequential requests, 0 retries.
- Each manifest is 1.2 MB, mostly opaque cursors.

**Book sweeps** (`research_lab/book_sweeps/*`, OBS):
- 43,420 books in 79.5–81.6 s for the first 3 sweeps, and 42,386 books in 116–141 s for the last 3. So "43k in 80 s" is OBS for the first series only.
- 424–435 POST `/books` requests per sweep.
- rows.csv.gz is 4.25–4.35 MB per sweep (decoded 11.5 MB), about **100 B/book**.
- Decoded raw response is **58.1–59.0 MB/sweep, about 1.37 KB/book, not kept** (`keep_raw: false`).
- Mean **32.8 price levels per book** (max 318). 42,369 books are two-sided, 16 one-sided and 1 empty.
- Only the outcome-0 token of E001-eligible markets is swept (endDate unknown or more than 3h ahead). That is about 15.5% of the 273k "open" universe.

**What the compact snapshot keeps** (`research_lab/extract.py` COLUMNS):
- ids: market, condition, event, token0
- `closed`/`active`/`binary`
- best bid/ask, spread, last trade, chg 1h/1d/1w, liquidity, volume24hr
- end_date, `updated_at`
- page receipt clock and page index
- neg-risk fields (added in 19d7bd3, so absent from existing snapshots)

**What it discards.** A Gamma market object has 73 keys (OBS, `e9d0` page 0). The snapshot drops:
- `events`: 3.65 KB/market, the embedded parent event repeated for every member. This is about 57% of raw bytes.
- `description`, `question`, `outcomes`, `outcomePrices`, token1/`positionIds`
- fees: `feeSchedule`, `makerBaseFee`, `takerBaseFee`
- rewards: `rewardsMinSize`, `rewardsMaxSpread`
- `orderPriceMinTickSize`, `orderMinSize`, `acceptingOrders`, `createdAt`/`startDate`, `gameStartTime`, `secondsDelay`, `umaResolutionStatuses`, `competitive`, `liquidityClob`, etc.

**What the book sweep keeps and drops** (`book_sweep.py` ROW_COLUMNS). It keeps:
- best bid/ask
- top sizes
- depth within 1c/5c on each side
- level counts
- `book_timestamp` and `book_hash` (source clocks preserved)
- tick, min size
- batch receipt clock

It drops all individual levels.

**Exactness gap (OBS).** `parse_num` converts Gamma `{"$decimal": …}` values to float. For example, `volume24hr` is written as `39023.76833499999`. Raw bodies are not kept, so the recorded page sha256 can never be re-verified, and the source decimal strings are gone. This is harmless for features. However, it fails stage 4 ("source strings exact") of `docs/architecture/V2_MIGRATION_AND_ARCHIVE.md` if these snapshots ever become canonical evidence.

**Universe growth (OBS, `research_lab/e001/manifest.json`).** 236,618 (Oct 3) → 235,224 (Oct 5) → 267,180 (Oct 8) → 273,075 (Oct 10 07:51) → 276,706 (Oct 10 19:22) → 272,660 (20:49). That is +15% in a week, but in a step and not smooth.

**Columnar test.** pyarrow and duckdb are *not installed*; zstd is. Method: one zstd stream per column, in memory, as a Parquet-like proxy. Nothing was written except a 1 KB script.

| file | csv.gz | row zstd-19 | columnar zstd-19 | of which ids | columnar without id columns |
|---|---|---|---|---|---|
| snapshot 204959Z | 27.44 MB | 23.26 MB | 20.51 MB | token 9.33 + condition 8.97 = **18.3 MB (89%)** | **about 2.2 MB** |
| sweep 210603Z | 4.25 MB | 3.81 MB | 3.32 MB | token 1.39 MB, book_hash 0.89 MB | about 1.9 MB |

The format change alone (csv.gz → Parquet/zstd) is worth only about 25%. **The 10x win is normalisation:** keep the 66- and 78-character identifiers in a dimension table keyed by int32 and store per-observation only `market_id`/`token_idx` plus values.

**Whole-directory compressibility** (tar | zstd -19 --long, 10-page samples, OBS):

| Sample | Before | After | Ratio |
|---|---|---|---|
| `0da4` | 14.78 MB | 0.51 MB | **29x** |
| `e9d0` (raw already gz) | 10.35 MB | 0.88 MB | 11.8x |
| panel projections | 3.51 MB | 0.31 MB | 11.3x |

The ratio is high because parsed/frame duplicate the raw content.

**EST full offsite archive of all of `data-dumps/`: about 2 GB**:
- 23.9 GB raw-JSON captures / 29 ≈ 0.82 GB
- `e9d0` 2.57 / 11.8 ≈ 0.22 GB
- 6.6 GB of panels / 11.3 ≈ 0.58 GB
- research_lab ≈ 0.33 GB (already compressed)

## 2. Growth model

**Assumptions:**
- Flat N = 273k open markets, with about 43k book-eligible outcome-0 tokens.
- High-growth case: the universe doubles yearly. Cumulative volume is then ×1.44 flat over 1 yr and ×3.37 flat over 3 yr (∫2^t dt).
- Days per period: 30 / 182 / 365 / 1,095.

Unit costs:
- **Compact snapshot:** 27.4 MB today (OBS). Normalised Parquet/zstd about 2.5 MB (EST, from the 2.2 MB measured plus `updated_at`/flags overhead). Add a market-dimension delta of about 70 B × new markets, roughly 0.4 MB/day.
- **Book sweep summary:** 4.25 MB (OBS), or about 1.9 MB normalised.
- **Full-depth L2:** 1.39M levels/sweep. Stored as sorted per-book price-level arrays (price as uint16 ticks, size as int64 micro-units), at about 3–5 B/level after zstd. That is **about 6 MB/sweep including summary (EST ±50%)**. Raw JSON gz would be about 7–10 MB (EST, from 58 MB at 6–8x).

| Strategy (flat N) | per day | 1 mo | 6 mo | 1 yr | 3 yr |
|---|---|---|---|---|---|
| (a) compact csv.gz, 6h | 4×27.4 = 110 MB | 3.3 GB | 20 GB | 40 GB | 120 GB |
| (a) compact csv.gz, 1h | 658 MB | 20 GB | 120 GB | 240 GB | 720 GB |
| (a) compact csv.gz, 15m | 2.63 GB | 79 GB | 479 GB | 960 GB | 2.9 TB |
| (a) normalised, 6h | 10 MB | 0.3 GB | 1.8 GB | 3.7 GB | 11 GB |
| (a) normalised, 1h | 60 MB | 1.8 GB | 11 GB | 22 GB | 66 GB |
| (a) normalised, 15m | 240 MB | 7.2 GB | 44 GB | 88 GB | 263 GB |
| (b) full L2 43k books, 6h | 24 MB | 0.7 GB | 4.4 GB | 8.8 GB | 26 GB |
| (b) full L2, 1h | 144 MB | 4.3 GB | 26 GB | 53 GB | 158 GB |
| (b) full L2, 15m | 576 MB | 17 GB | 105 GB | 210 GB | 631 GB |
| (c) 2k mkts full depth @5m (576k books/d × 140 B) | 81 MB | 2.4 GB | 15 GB | 30 GB | 88 GB |
| (c) 5k @5m | 202 MB | 6 GB | 37 GB | 74 GB | 221 GB |
| (c) 2k @1m | 403 MB | 12 GB | 73 GB | 147 GB | 441 GB |
| (c) 5k @1m | 1.0 GB | 30 GB | 183 GB | 368 GB | 1.1 TB |
| (d) trades, 1M/day × 50 B normalised | 50 MB | 1.5 GB | 9 GB | 18 GB | 55 GB |
| (e) event-triggered: 200 triggers/d × 120 snaps × 5 tokens × 140 B | 17 MB | 0.5 GB | 3 GB | 6 GB | 18 GB |

Notes on the table:
- **(c)** uses 140 B/book-snapshot, the conservative full-snapshot figure. Sorting the partition by (token, time) and delta-encoding levels would plausibly cut this by 3–10x (EST).
- **(d)** volume is highly uncertain: I assume 0.3–1.5M trades/day. The 50 B/trade includes a 32 B incompressible tx hash. Raw Data-API JSON is about 600–900 B/trade (about 100 B gz).
- **Feasibility.** A full universe pass takes 6.7–11.7 min (OBS), so **15-min universe snapshots are not operationally credible**: no slack, and about 11k Gamma requests/hour. Intra-snapshot skew is already up to 12 min, and the per-page receipt clocks must be used. Book sweeps take 80–140 s, so 15-min sweeps are feasible on time but untested against rate limits.
- **Headline.** At 8.6 GiB free, the *current* csv.gz format at 6h fills the disk in about 78 days, and at 1h in about 13 days. Normalised 6h snapshots plus 6h full L2 cost about 34 MB/day, or **about 12.5 GB/yr flat (about 18 GB/yr at 2x growth)**.

## 3. Format and storage roles

- **Parquet + zstd (level 3 for writes, 9–19 for cold):** the analytic format for all new observation families. One immutable file per capture or sweep, plus a sidecar manifest (sha256 of the file and of the source page hashes).
  - Use exact types. Prices go in as `DECIMAL`/scaled int64 parsed from the source *string*, not float. This closes the stage-4 gap.
  - Clocks go in as int64 µs with explicit semantics columns.
  - Dictionary-encode `state` and side.
- **Dimension tables (Parquet, SCD-2):**
  - `dim_token` (int32 ↔ 78-digit id, outcome index)
  - `dim_market` (market_id, condition_id, token0/1 idx, event_id, neg-risk ids, static-attribute hash, valid_from_capture)
  - `dim_event` (title, tags, series)

  Write a row only when the hash changes.
- **Raw receipts:**
  - Keep a **change-only raw store**: the gz raw market object is written only when its static-attribute hash changes, plus all new markets. At about 430 B/market gz (OBS: `e9d0` raw.bin total 117 MB / 273k), 5k new plus about 10k changed per day comes to about 6.5 MB/day (EST).
  - Keep a **weekly full raw frame** as an audit anchor (about 117 MB gz, or less with zstd --long), about 0.5 GB/month.
  - Turn on `keep_raw` for book sweeps at the cadence chosen for full L2, rather than inventing a normalised L2 parser now. 58 MB at 6–8x is about 7–10 MB/sweep.
  - Normalised columns are derived and rebuildable. Raw is the evidence.
- **DuckDB:** zero-server query engine over the Parquet tree, both locally and over object storage. Install pyarrow + duckdb in the venv; neither is present.
- **SQLite:** keep for small operational ledgers (run registry, manifests index, scheduler state). It is not for bulk observations.
- **Supabase Postgres (500 MB):** serving only, for latest-snapshot summaries, registrations, frozen cohort/prediction rows and dashboard aggregates. In Postgres, one 273k-row snapshot is about 50–60 MB with row overhead (EST), so research bulk would exhaust it within about 10 snapshots. **Never the research store.**
- **Object storage (R2/B2/S3):** the offsite archive tier for Parquet and raw tar.zst.
  - R2: 10 GB free, no egress.
  - B2: 10 GB free.
  - S3 would cost egress. Choosing or signing up for any provider is a user decision.
- **Time-series DBs (Timescale/QuestDB/Influx):** not justified. The workload is batch, append-once, and analysed offline. A TSDB adds a server and migration risk for no causal or provenance gain.
- **Partitioning:** `family=<snapshot|book_l2|book_top|trades|trigger>/date=YYYY-MM-DD/capture_id=<id>/part-0.parquet`. Sort books by (token_idx, side, price). Roll daily files into monthly cold archives only as *additional* copies; never rewrite the originals.

## 4. Future-feature recoverability

| Feature family | Current compact snapshot plus summary sweep | Full L2 @6h | Targeted 1–5 min L2 / WS deltas | Trades | Recoverable later? |
|---|---|---|---|---|---|
| Top-of-book, spread, momentum | yes | yes | yes | n/a | Partially, via coarse CLOB price history (assumption) |
| Depth-weighted imbalance | only 1c/5c bands | any weighting | yes | n/a | **No.** Books are ephemeral. |
| Book shape (slope, gaps, convexity) | level counts only | yes | yes | n/a | **No** |
| Queue/cancel dynamics | no | no (6h too coarse) | yes | needed to split cancels from fills | **No** |
| Trade-flow toxicity (VPIN, Kyle λ, signed volume) | no | no | partial | yes | **Likely yes**: fills are on-chain (CTF Exchange events) and in the Data API. Backfill depth is an unverified assumption. |
| Cross-market / neg-risk consistency | yes at snapshot cadence (new neg-risk columns), with up to 12 min page skew | yes | yes for the panel | helps | Only as-known at snapshot time |
| Category, tags, fees, rewards, game start | **dropped** | n/a | n/a | n/a | **As-known versions lost.** Gamma returns only *current* metadata. |
| Wallet features | no | no | no | proxyWallet in trades | Trades yes (on-chain). Holder snapshots: no. |

The cheapest representation that keeps these options open:
1. Full-depth L2 for all eligible books at 6h, as raw gz (about 24–40 MB/day).
2. Normalised top-of-book universe at 1h (60 MB/day).
3. A preregistered targeted panel at 1–5 min.
4. The SCD-2 dimension plus change-only raw Gamma objects, which preserve as-known metadata cheaply.

Trades can be deferred *if* a one-off bounded probe confirms backfill depth.

## 5. Tiered retention

- **T0 canonical / protected:**
  - What it covers:
    - frozen protocols and EVIDENCE JSONs
    - the 4.4 MB `phase3_evidence_capsules`, the *only* record of 1.82 GB of retired runs
    - the D082/D088 (`0da4`)/D094/D097/D114 (`e9d0`) frames
    - E002 frozen forecasts (`research_lab/forecasts`)
    - snapshots or sweeps used as prospective inputs
  - Allowed reduction: none, except exact-byte transparent compression (D099 script). It is lossless and needs the user's storage session.
  - Loss: none.
- **T1 exploratory:**
  - What it covers: research_lab snapshots and sweeps, pilots that are not canonical.
  - Keep originals.
  - Write *new* collections natively as Parquet, after a one-time equivalence test against the CSV writer.
  - Do not convert old files in place: the manifests hash raw pages, not the CSVs.
- **T2 reconstructable derived:**
  - What it covers: `parsed.json`/`frame_page.json` (58% of capture bytes), panel `projection.json` (about 6.6 GB logical), `e001/snapshots.csv.gz` (83 MB), `dev_snapshots_v2` (151 MB).
  - Loss if retired: the stored output of the parser as it ran historically. Regeneration needs pinned code and environment, and the original-code verification becomes "re-derivation", not the historical result.
  - Only for non-canonical runs, capsule-first, with explicit approval.
- **T3 redundant bulk:**
  - What it covers: uncompressed physical copies of all the above.
  - About 17.7 GB allocated is reclaimable to about 3 GB by transparent compression (EST, from the 6.4x ratio OBS). That is about 15 GB freed with zero logical change, against the checkpoint plan's 4.1 GB from 6 dirs.
  - Including `0da4`/`e9d0`/`3a4f` and the panels requires the user's storage-session decision, because they are canonical or unresolved.

Every *cadence* reduction is permanent for book and queue features, because there is no historical source. Metadata reductions lose as-known versions. Trade reductions are probably recoverable.

## 6. Backup

**The risk is immediate and concentrated:**
- one SSD, 96% full
- no Time Machine
- `data-dumps/` git-ignored
- capsules that are the sole remaining record of retired data
- D114 unresolved frame
- 3 unpushed commits holding protocol and scorer work

A disk failure today would lose canonical evidence irrecoverably. The near-full disk is a separate threat: a filling disk makes collections fail or go incomplete, and blocks D116 (13.3 GB needed vs 8.6 GiB free).

**Minimum viable backup** (sizes only; destination is the user's choice):
1. **Now, about 0.4 GB:**
   - `phase3_evidence_capsules` (4.4 MB)
   - all `receipt.json`/acks/reports/manifests (about 50 MB, EST)
   - `research_lab/` (330 MB)
   - `git push` of the 3 commits

   Any personal cloud drive or USB stick works.
2. **Soon, about 2 GB:** stream all of `data-dumps/` as `tar | zstd -T0 -12…-19 --long=27 | <external drive or object store>`.
   - This creates no local temp files, which matters on a full disk.
   - The ~2 GB size is EST from the 29x / 11.8x / 11.3x samples.
   - Verify by restore-and-hash at the destination against the D099-style manifest.
   - APFS compression is not carried by tar, so the logical 33.5 GB is the input size. It fits a 10 GB free object-storage tier or a 32 GB USB drive.
3. **Ongoing:** about 34 MB/day under the recommended plan. A nightly incremental of new capture dirs is enough.

## 7. Top 5 recommendations

1. **Make an offsite backup of capsules, manifests and `research_lab`, then a full tar.zst of `data-dumps` (about 2 GB EST).** *Useful now.* This is the single largest risk reduction per byte. It needs the user to pick a destination.
2. **Normalise identifiers in the compact snapshot and sweep writers** (int `market_id`/`token_idx` plus dimension tables), and write Parquet+zstd with exact decimal parsing. This gives about 11x smaller snapshots (27.4 → about 2.5 MB) and closes the float-exactness gap. Install pyarrow and duckdb. *Prepare next.* Freeze the format before E002/E004 depend on more snapshots.
3. **Extend the exact-byte transparent compression to all uncompressed dirs**, about 15 GB reclaimable losslessly, after (1) and with a user storage session. This unblocks D116 without deleting anything. *Useful now* (user decision).
4. **Turn on full-depth L2 (`keep_raw` gz) for book sweeps at 6h, plus change-only raw Gamma objects and a weekly full raw anchor.** These are the cheapest way to keep book-shape, imbalance and as-known-metadata options, which can never be backfilled. It costs about 30–45 MB/day. *Prepare next.*
5. **Defer trade and wallet collection and high-cadence (1–5 min) panels until a preregistered hypothesis needs them.** First run one bounded probe of Data-API and on-chain backfill depth. 15-min universe snapshots should be avoided as infeasible. *Defer.*

**The three assumptions I am least sure of:**
1. **Full-depth L2 at about 6 MB/sweep (3–5 B/level).** It is untested because no raw book bodies were kept. Raw gz could be 7–10 MB.
2. **Trades and wallets can be backfilled later from the Data API or on-chain fills with adequate timestamps, and volume is about 1M trades/day.** Both are unverified. If backfill is shallow, trades move from "defer" to "collect now".
3. **About 2 GB for a whole-`data-dumps` tar.zst.** This is extrapolated from 10-page samples. Pages with large descriptions, or the 128 MB `--long` window, could change it by about 2x. The universe-growth case (2x/year) is also a guess, extrapolated from a single +15% week.
