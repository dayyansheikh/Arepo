# Historical data for AREPO model development: handoff (2026-10-11)

**Status: DEVELOPMENT DATA ONLY.** No prospective evidence, no edge claim, and no production change. Nothing was purchased or signed up for.

**Inputs:**
- [report_a_sources.md](report_a_sources.md): sources 1–3 and the official endpoints.
- [report_b_sources.md](report_b_sources.md): sources 4–5 plus extra sources.
- [demo/](demo/): the script, its result, and sha256 manifests.

## 1. Answers

1. **Do useful historical datasets exist?** Yes, for development. No free source gives a complete-universe book history that has sequence numbers, receive clocks and verified licensing. Every source would need its own audit before it could stand in for AREPO's own capture.

2. **Which source is best?**

   | Rank | Source | Use | Why | Blocker |
   |---|---|---|---|---|
   | 1 | **pmxt v2** (`r2v2.pmxt.dev`, hourly parquet; mirror `Joseph3222/polymarket-orderbook` on Hugging Face, CC BY 4.0) | book and flow features | AREPO keys (`market` = condition_id, `asset_id` = token_id). Both clocks: receive − exchange lag p50 123 ms, p99 284 ms, none negative, which is consistent with live websocket capture. Full-depth `book` events, `price_change` deltas and trade prints with tx hash. Hourly files were continuous over 07-04 to 08-10 | Licence UNVERIFIED on pmxt itself (the mirror states CC BY 4.0). Origin bucket ends **2026-08-10T00**. About **11 GB/day**. v1 period (before 04-13) covers about 50% of markets. Universe completeness of subscriptions is unverified |
   | 2 | **vgregoire/polymarket-users** (Hugging Face, CC BY 4.0; Akey, Grégoire, Harvie & Martineau 2026, SSRN 6443103) | trade-flow and wallet features | On-chain `OrderFilled` fills for **all markets**, 2022-11-11 to 2026-03-29, with maker/taker wallets, Gamma `market_id`/`event_id` and token id. A typical 2025 day is 6 MB | Block time to 1 s. No log_index, so intra-block order is lost. `winner` and `category` sit on every row (leakage; drop at load). Polymarket-derived fields remain under Polymarket's terms |
   | 3 | **trentmkelly/polymarket_historical_data** (Hugging Face, CC BY 4.0, rev `122205f`) | demo, pipeline testing | Live REST snapshots about every 5 min with full depth. Both clocks. External crypto prices with raw receipts. Still updating (07-23 to now) | **Vendor filter: top 100 markets by recent volume.** 1,395 distinct markets passed through in 5 days. Not AREPO's population |
   | – | polyorderbooks (Zenodo/Hugging Face, CC BY 4.0) | depth-code test fixtures only | Clean live 1 s L2 | Crypto up/down markets only, resolved only, 3–4 days. Winner label on every row |
   | ✗ | DineshKumar8399 | not usable | Wrong venue (**Polymarket US**). About 12.4k rows per poll cap. About half the day missing. No condition or token ids | — |
   | ✗ | marketlenstrade sample | not usable | Resolved-only. `keep_complete()` drops gappy markets (survivorship). Trade-aligned compaction loses intermediate books | — |
   | ✗ | institute.polymarket.com | not a dataset | A guide to the public APIs | — |
   | ✗ | CLOB `/prices-history` | not point-in-time | Server-resampled single price `{t,p}`; empty for some resolved markets with `interval=max`. A retrospective backfill | — |

   Data API `/v2/trades` (cursor, 300 req/10 s) is a valid on-chain-anchored source for recent trades. v1 offset stops at 10,000.

3. **AREPO features and models supported** (via the existing `compare.run_comparison`, with no new framework):

   | Features / models | pmxt v2 | Trades (vgregoire) | trentmkelly |
   |---|---|---|---|
   | B0, B1h/B1 (own-history mid momentum), B2 | yes (mid from books) | trade-price only (bid-ask bounce) | yes |
   | spread, book imbalance, depth shape, microprice | yes, full depth | no | yes, full depth at 5 min |
   | trade flow (signed volume, count, size, wallet concentration) | prints, no wallet (join Data API) | **yes** | no |
   | E001 Gamma context (liquidity, volume24hr, end date, oneHourPriceChange) | no (needs a Gamma join; as-of metadata unavailable) | partly (lifecycle times) | no |
   | neg-risk cross-market (E005, dev screen item 6) | yes if group membership joined (condition_id) | yes (event_id) | no |
   | resolution outcomes | join from Gamma | `winner` (label use only) | no |

## 2. Demonstration (reproducible, exploratory)

**Data:**
- 437 trentmkelly snapshot files, every 3rd run, 2026-09-15 to 09-19, 48 MB.
- Each file is sha256-verified against the publisher's LFS oid; all 437 match (`demo/sample_manifest_sha256.txt`).

**Script:** `demo/tk_demo.py` (sha256 `ec12b6c1…`).
- Builds AREPO pair frames with the E001 eligibility rules: two-sided, spread ≤ 0.10, mid in [0.02, 0.98].
- Target: mid at the first snapshot at least 1h after the origin, within 20 min. Origin and target use the **receive** clock.
- Features come from the asset's own earlier snapshots only:
  - `h_chg_1h`, `h_chg_1d`, each with a missing flag;
  - `h_skip_1h_15m` (mid change from t−1h to t−15m, so it does not share the origin mid's quote noise);
  - `book_imbalance` within 5c.
- Features are registered **in memory** through `features.register`. That is a name-level label guard only; the causality of the `h_*` columns rests on the `at_offset` code, which was reviewed and found to contain no look-ahead. The run goes through unchanged `compare.run_comparison` (code sha in `demo/tk_demo_result.json`, git `4a96f31`).
- Runtime 14.5 s, peak RSS 0.45 GB.

**Sample:**
- 21,930 pairs, 670 markets, 5 daily periods (4 test periods).
- 3,598 eligible origins had no target.
- Horizon p5–p95: 1.03–1.26 h.
- The source has no event id, so clustering is by **market**. That understates dependence, so the intervals are too narrow.

**Pooled R²_oos vs B0** (95% CI):

| Model | R²_oos | 95% CI |
|---|---|---|
| B1h_hist | +0.0032 | −0.0066 to 0.0132 |
| B1skip | +0.0070 | 0.0013 to 0.0135 |
| B2_hist | +0.0022 | −0.0070 to 0.0120 |
| B2_hist_book − B2_hist | −0.00007 | −0.0003 to 0.0001 |

- **Per-period B1skip:** the CI lies above 0 in 1 of 4 periods. By E001's rule this is *inconclusive*.

**Data diagnostics:**
- 16% of books were crossed or one-sided.
- Receive − exchange time: p50 4.5 s, p99 739 s, max 5,982 s. Exchange timestamps are often stale, so the receive clock must be the origin clock.
- Run spacing: median 16 min (sample stride), maximum 31 min.

**Reading (development only; revised after challenger review).**
- At a 1h horizon, in a top-100 vendor population, own-history 1h change gives no clear gain (B1h +0.003, CI includes 0).
- **This does not test E001.** E001 used Gamma `oneHourPriceChange` at next-capture horizons of about 5–70h.
- A 1h-to-15m skip-change model is positive pooled (CI +0.0013 to +0.0135) but positive in only 1 of 4 periods. That is inconclusive, and the CIs are anti-conservative under market clustering, with no time-block inference.
- Book imbalance adds about 0 (−0.00007, CI −0.0003 to +0.0001).
- No fitted coefficient sign is reported, so "reversal" is not shown.
- Nothing here bears on liquidity moderation of E001.

**Selection note.** The 3,598 origins without a valid target include pairs whose j snapshot was crossed even when a valid snapshot existed within tolerance. That is volatility-correlated selection. Whether `collected_at` is stamped per row or per run is unverified.

## 3. Scientific limitations

- **Selection bias.**
  - pmxt's subscription universe is unaudited.
  - trentmkelly is the top 100 by volume.
  - Every source was chosen after we saw summary statistics (dataset-selection bias). Results do not generalise to AREPO's universe.
- **Clock and timing.**
  - pmxt timestamps are 1 s at source (millisecond fields), with no sequence numbers. Naive delta replay gives crossed books, so books must be rebuilt from `book` snapshots with deltas applied within the same hour.
  - Trades carry block time only, with no intra-block order.
- **No as-of metadata.** Gamma serves current metadata. Fees, tags, end-date revisions and liquidity at the time cannot be recovered for history, so E001 context features cannot be replicated faithfully.
- **Labels on rows.** vgregoire (`winner`, `category`) and polyorderbooks (`winner`) put outcomes on every row. They must be dropped at load and reattached only as labels.
- **Inspected periods are development forever.** Samples already looked at:
  - trentmkelly 09-15 to 09-19;
  - vgregoire 2025-06-15;
  - pmxt 2026-08-01T12 row group 40;
  - polyorderbooks 08-21 to 08-24;
  - HEAD/size probes of other periods (metadata only).
- **Rights.** CC BY 4.0 requires attribution. pmxt's own terms and Polymarket's terms over derived fields are unverified. Keep everything private and do not redistribute raw data.

## 4. Sealed historical holdouts (define BEFORE any use; disclose that the sources were chosen post hoc)

These windows were revised after the challenger review. They count as "defined before use" only from the commit that contains this text.

| Source | Development window | Embargo | Sealed holdout | Notes |
|---|---|---|---|---|
| pmxt v2 | 2026-04-13T19 to 2026-06-04 | 2026-06-05 to 2026-06-17 (includes the 06-12 to 06-17 gap) | **2026-06-18 to 2026-07-31T23:59**, labels t_j ≤ 07-31T23:59 | 08-01 to 08-10 was inspected, so it is excluded. Of the holdout, only the 07-04 to 07-31 file sizes were probed |
| vgregoire trades | 2022-11-11 to 2025-12-24 | 2025-12-25 to 2026-01-07 | **2026-01-08 to 2026-03-29** | Only one 2026 file size was probed |
| trentmkelly | 2026-07-23 to 2026-10-04 | 2026-10-05 to 2026-10-11 | **2026-10-12 onward**, read only at a pinned revision with the per-file LFS-oid manifest recorded at registration | The earlier 09-22 to 10-10 window was **withdrawn**: AREPO's own E001 captures (2026-09-20 to 10-10) already cover that period's price paths, so it is not untouched |

**Rules:**
- **Embargo** must be at least the maximum label horizon plus the maximum feature lookback, and never under 7 days. Drop development origins with t_j ≥ embargo start. Drop holdout origins with t_j > holdout end.
- **Resolution-labelled analyses** split by market resolution date. Markets active in both windows are reported separately as a market-disjoint sensitivity check.
- **Read budget: at most 3 holdout reads per source, fixed now.**
  - Every read, including failures, is logged in `trials.jsonl` and reported with a multiplicity adjustment.
  - A spec written after any holdout read on that source is labelled *post-holdout*.
- **Labelling:** "historical out-of-sample (third-party data) on a post-hoc-selected, vendor-filtered population, possibly in a different regime; transport to AREPO's universe not assumed". It is **never** described as prospective confirmation.
- **Gaps:** holdout gaps stay missing. No interpolation.

**Regime stratification (declared 2026-10-11, before any holdout read; windows unchanged).** Based on `../2026-10-11-market-structure/POLYMARKET_REGIME_TIMELINE.md`:
- **On-chain trades.** Development is almost entirely fee-free, while the holdout (2026-01-08 to 03-29) is entirely in the new fee era. Every holdout result is reported stratified into (a) fee-free markets excluding short-duration crypto up/down and (b) fee-enabled or short-duration crypto markets. Stratum (a) is primary.
- **pmxt.** The development window straddles CLOB V2 (2026-04-28 ~11:00 UTC). Development comparisons use only post-V2 data from 2026-04-29T12:00 (a 24h buffer). Pre-V2 data from 04-13 to 04-28 is a separate exploratory slice. In the holdout, sports markets cross the 07-02 tick change (World Cup) and the 07-10 fee step, so holdout results are reported for non-sports (primary) and sports separately.
- **All sources.** Short-duration crypto markets carry an indicator and are analysed separately, never pooled into the primary population.

## 5. What can start now, and what needs prospective collection

**Can start now** (development):
- Feature and code development on pmxt book and trade data, and on vgregoire flow and wallet data.
- Running the main team's reversal-moderation screen on a second, independent historical population. Match E001's horizons (about 5–70h) and its Gamma change definition where possible; the demo did not.
- Estimating the per-day variance of R²_oos across many independent days. This feeds the main team's new MDE calculator (Methods note M2). The pmxt development window gives about 55 days, against the about 10 days AREPO has of its own.
- Regime exploration.
- Depth, flow and microstructure feature prototypes.

**Needs months of fresh prospective collection:**
- Any confirmation (E00x-style).
- As-of metadata context features.
- Effects in the full AREPO universe, including illiquid markets the vendors filter out.
- Anything after the sources end: pmxt stops at 08-10; trades stop at 03-29.
- Execution and fill realism.
- Calibrated forecast track records.

## 6. Smallest integration path for the main team

1. **Register the holdouts first.** Commit section 4 to `docs/research_lab/EXPERIMENT_LEDGER.md` as a dated methods note, before downloading any holdout-window file.
2. **Add one adapter**, `research_lab/hist_sources.py` (about 150 lines). It converts a source into the existing pair-frame contract: `market_id`, `event_id`, `period`, `t_i`, `t_j`, `dmid`, `horizon_h` and origin columns, matching `demo/tk_demo.py`.
   - Its manifest records source, revision/URL, file sha256s (pmxt: compute on download; Hugging Face: the LFS oid), licence, clock used and `evidence_role="development"`.
   - **Holdout guard:** at the download/URL level, not at parse. It refuses holdout-window files unless the spec hash appears in committed `trials.jsonl` with its read not yet consumed and the source's read budget not exhausted. The read record is appended before data is returned.
   - **Registry isolation:**
     - Never register features on import, nor from the research_lab `__init__` or `run_dev_screen`.
     - Prefix every feature name `hist_<source>_` and never reuse AREPO column names (`chg_1h`, `spread`, `bid_depth`).
     - Write pair frames to a separate output directory.
     - Add a test that importing `run_dev_screen` leaves the REGISTRY family sets unchanged.
   - **Clustering:** when a source has no event id, `event_id` is null and `cluster_level="market"` is recorded. Never use `event_id = market_id` as the demo does.
   - Features are versioned `hist-<source>-v0`.
   - The adapter reuses `columnar.py` and the `[research]` pyarrow extra.
   - Coordinate any ledger or `trials.jsonl` writes with the session that owns them; never interleave edits.
3. **First run.** One pmxt development day at about 11 GB, **streamed and reduced on the fly** to 5-minute book summaries plus 1-minute trade aggregates, about 50–100 MB per day. Never store raw hours, never read remote parquet whole, and cap RSS (`/usr/bin/time -l`). Then run the reversal-moderation screen on it as a second development population.
4. **Event ids.**
   - **trentmkelly:** join Gamma event ids by `market_id`.
   - **pmxt:** join neg-risk group membership by condition_id.
   - Then cluster by event.
5. **Rights.** A human reads the pmxt terms and Polymarket's terms before any use beyond private research.

**Memory note.** During the 2026-10-10 session, a verification subagent ran pyarrow scans over HTTP ranges on 0.5–9 GB remote parquet files shortly before the Mac's memory-exhaustion crash. It may have contributed. All future historical work must stream bounded row groups with a measured RSS ceiling.
