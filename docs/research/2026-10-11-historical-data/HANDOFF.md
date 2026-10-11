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
- Features are registered **in memory** through `features.register`, so the label guard applies. The run goes through unchanged `compare.run_comparison` (code sha in `demo/tk_demo_result.json`, git `4a96f31`).
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

**Reading (development only).** The large 1h reversal E001 found (about +0.037) is **not visible** in this liquid top-100 population at a 1h horizon. Book imbalance adds nothing here either. This is consistent with the main team's reversal-moderation screen (`features_dev.py`: reversal × spread and × liquidity), which tests whether the reversal lives in illiquid, wide-spread markets. It is a direction for development, not a finding.

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

| Source | Development window | Sealed holdout (untouched) | Embargo / notes |
|---|---|---|---|
| pmxt v2 | 2026-04-13T19 to 2026-06-11 | **2026-06-18 to 2026-07-31** | The 06-12 to 06-17 gap is the embargo. Exclude 08-01 to 08-10 (inspected). The holdout's contents have never been read; only the 07-04 to 07-31 file sizes were probed |
| vgregoire trades | 2022-11-11 to 2025-12-31 | **2026-01-01 to 2026-03-29** | Only one 2026 file size was probed |
| trentmkelly | 2026-07-23 to 2026-09-21 | **2026-09-22 to 2026-10-10** | Only 09-15 to 09-19 was read |

**Rules:**
- Drop holdout origins whose label window crosses into the holdout.
- One holdout read per frozen, registered spec, logged in `trials.jsonl`.
- A historical-holdout pass is described as "historical out-of-sample (third-party data)". It is **never** described as prospective confirmation.

## 5. What can start now, and what needs prospective collection

**Can start now** (development):
- Feature and code development on pmxt book and trade data, and on vgregoire flow and wallet data.
- Running the main team's reversal-moderation screen on a second, independent historical population.
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
   - It refuses holdout-window timestamps unless given a registered spec hash.
   - Features are versioned `hist-<source>-v0`.
   - The adapter reuses `columnar.py` and the `[research]` pyarrow extra.
3. **First run.** One pmxt development day at about 11 GB, **streamed and reduced on the fly** to 5-minute book summaries plus 1-minute trade aggregates, about 50–100 MB per day. Never store raw hours, never read remote parquet whole, and cap RSS (`/usr/bin/time -l`). Then run the reversal-moderation screen on it as a second development population.
4. **Event ids.**
   - **trentmkelly:** join Gamma event ids by `market_id`.
   - **pmxt:** join neg-risk group membership by condition_id.
   - Then cluster by event.
5. **Rights.** A human reads the pmxt terms and Polymarket's terms before any use beyond private research.

**Memory note.** During the 2026-10-10 session, a verification subagent ran pyarrow scans over HTTP ranges on 0.5–9 GB remote parquet files shortly before the Mac's memory-exhaustion crash. It may have contributed. All future historical work must stream bounded row groups with a measured RSS ceiling.
