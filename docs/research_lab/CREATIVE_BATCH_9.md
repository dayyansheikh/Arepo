# Creative batch 9 (CB9): trade-direction truth, hourly-anchored Pyth dailies, flow-skewed maker, dust midpoint

`evidence_role: methods` (CB9-S, CB9-D) / `exploratory_historical` (CB9-P Stage 1, CB9-K on pmxt books 2026-04-13 to
08-10) / `prospective` (CB9-P Stage 2, post-freeze sessions) | status: **DRAFT design, not frozen; challenger review
required.** Drafted 2026-10-17 11:05 UTC+1 (2026-10-17T10:05Z) by the CB9 design pass. Nothing has been fetched for
CB9 beyond the 45 counts-only feasibility requests in §0.3. No CB9 quantity has been computed.

This file turns four round-4 ideas from `CREATIVE_HYPOTHESES_2026-10-18.md` (CH79, CH83/CH84 merged, CH92, CH80) into
declared, falsifiable tests, and records why the other round-4 ideas are not in this batch. It follows
`CREATIVE_BATCH_8.md` (CB8) and `CREATIVE_BATCH_7.md` (CB7) in structure and rules. "As CB8 §x" means that rule applies
unchanged, including its challenger-round fixes; CB4 amendment A-C1 governs the day cluster way.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices.
- Test tables bind only once the CB9 declaration hash is committed (`model_specs/cb9_v1.json`, the CB9 freeze), after a
  `science-reviewer` challenger round (§8). **One exception:** the CB9-S audit collection rules (sample frame, seeds,
  match rule, truth rules, endpoint and topic pins), which must be fixed before the first receipt is requested, are
  fixed by this document and hashed into `seals/cb9_sign_rules.json` before q0181 is committed. The audit *statistic*
  (agreement) is computed only after the freeze (q0190).
- **`T_seal` congestion.** Nothing CB9 enters the `net` lane before 2026-10-22T00:00Z; CB6/CB7/h7 `T_seal`-bound fetches
  and CB8's post-`T_seal` jobs keep priority. Before `T_seal` only q0180 (smoke, about 80 requests) and q0181 (audit
  stage A, about 2,700 requests) may run, both on the `cpu` lane at ≤ 2 rps.
- **Queue ids q0180-q0199, one id per job, no letter suffixes** (checked free in `queue/jobs/` and `queue/drafts/` at
  drafting; q0177-q0179 stay reserved for CB8). Specs are drafts **in this document only** (§4); no file is created
  under `queue/` until code, tests and the freeze check exist.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB9-S** trade-direction truth (CH79) | the Data API `side` of a taker print disagrees with the on-chain taker side often enough (agreement `q` < 0.90) to attenuate every AREPO flow coefficient; if so, the on-chain-signed flow slope is ≥ 1.5x the feed-signed slope (S1) | S0 (measurement, fixed); S1 (conditional on S0) | fresh print samples + public Polygon receipts (Oct 2026, Feb-Apr 2026, May-Aug 2026) | none (methods; S1 is single-stage, ceiling L1) | q0180-q0182, q0188, q0190, q0193, q0194 |
| 2 | **CB9-P** hourly-anchored Pyth equity dailies (CH83a + CH84, merged and narrowed) | in Pyth-settled equity "Up or Down" dailies, a frozen lognormal digital anchored on the last public hourly bar (a) identifies asks that pay after fees when held to settlement (P1, taker), and (b) a maker quoting around that anchor beats the same maker quoting around the book mid (P2) | P1 (economic), P2 (economic contrast) | pmxt books, all usable sessions 2026-04-13..08-10 | prospective post-freeze sessions (30) | q0183, q0184, q0191, q0195, q0196, q0198 |
| 3 | **CB9-K** flow-skewed maker in the F4/F5 cells (CH92) | in the replicated high-volatility / wide-spread cells, a touch maker skewed one tick in the direction of the frozen 6h flow feature earns more per filled share at a 6h mark than the unskewed maker (K1) | K1 (economic contrast, with route gate) | pmxt books (14Z origins) + Data API prints, SCREEN events | the same fetch, sealed HOLDOUT events | q0185-q0187, q0189, q0192, q0197 |
| 4 | **CB9-D** dust-anchored midpoint (CH80, route 1 only) | when a best level is dust (< 5 shares or < $1), the next print lies closer to the size-cutoff mid than to the displayed mid (D1); methods consequence for every mid-based target | D1 (methods mechanism) | the K pmxt hours (same markets, no extra ingress), SCREEN events | sealed HOLDOUT events | shares q0185-q0187, q0189, q0192, q0197 |
| - | CB9-F data | smoke, exclusion keys, frames, books, prints, receipts, seals | none | | | q0180-q0189, q0193, q0195, q0198 |

**Counted: 5 fixed (S0, P1, P2, K1, D1) + up to 5 conditional (S1, P1-rep, P2-rep, K1-rep, D1-rep) = 5-10** (§2.5).

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0180 | `cb9_smoke` (counts only: RPC endpoints and topic pins on 20 receipts per exchange era; Yahoo hourly bar shape out of window; Pyth frame paging; pmxt HEADs) | F | after smoke code and `seals/cb9_sign_rules.json` exist (cpu lane; may run before `T_seal`) |
| q0181 | `cb9_sign_audit_A` (S0 strata a and c: fresh print samples, receipts, per-print classes; **no agreement computed**) | S | after the q0180 PASS (cpu lane; may run before `T_seal`) |
| q0182 | `cb9_exclusion_keys` (CB8 q0164 keys plus every seal copy committed since: h7_cb4_*, h8_*, h9_flow, CB8 updown frame and holdout listing, CB8 holders frame) | F | after `T_seal`, q0164, q0166, q0168 |
| q0183 | `cb9_pyth_frame` (Gamma frame of Pyth equity Up/Down dailies; rule-text flags; Yahoo hourly and daily bars; outcomes to the guarded file) | P | after q0182 |
| q0184 | `cb9_pyth_books` (pmxt states at the three checkpoints; Data API prints in the 5-minute quote windows) | P | after q0183 |
| q0185 | `cb9_kd_frame` (Gamma frame for K/D, key drops, seeded event split SCREEN/HOLDOUT, sample of 1,000 markets) | K, D | after q0182 |
| q0186 | `cb9_kd_books` (pmxt hour 14Z of every window day for the K/D markets; book events kept for D; prints `[t − 6 h, t + 7 h]`; HOLDOUT written sealed) | K, D | after q0185 |
| q0187 | `cb9_kd_seal` (HOLDOUT listing sha256, seal copy) | K, D | after q0186 |
| q0188 | `cb9_sign_audit_B` (S0 stratum b: 1,000 SCREEN K/D prints, receipts, pmxt feed side by tx hash) | S | after q0187 |
| q0189 | `cb9_census` (counts only, all families; MDEs; gates GP, GK, GD, S0 match counts) | all | after q0184, q0187, q0188 |
| q0190 | `cb9_screen_S0` (agreement and the S0 verdict) | S | after the CB9 freeze |
| q0191 | `cb9_screen_P` (P1, P2, Stage 1) | P | after the CB9 freeze |
| q0192 | `cb9_screen_KD` (K1, D1, Stage 1) | K, D | after the CB9 freeze |
| q0193 | `cb9_sign_fetch_h10` (S1 data: `h10_sign` prints and receipts) | S | only if S0 verdict = "material noise" |
| q0194 | `cb9_screen_S1` (S1) | S | after q0193 |
| q0195 | `cb9_pyth_live` (P Stage 2 prospective collection: checkpoint books, prints, bars; 30 sessions) | P | only if P1 or P2 advanced; first session ≥ freeze + 1 day |
| q0196 | `cb9_rep_P` (P1-rep, P2-rep) | P | after q0195 completes |
| q0197 | `cb9_rep_KD` (K1-rep, D1-rep on HOLDOUT events) | K, D | only if K1 or D1 advanced |
| q0198 | `cb9_halfday_poll` (CH83c descriptive: 2026-11-27 and 2026-12-24 half sessions; uncounted) | P | after its rules hash; before 2026-11-27T17:00Z |
| q0199 | reserved | | |

### 0.2 Selection and scope

**Ranking rule.** Value of information x feasibility within about a week on data AREPO holds or can fetch keyless,
with no dependence on the pre-`T_seal` `net` lane. Methods results that re-scale earlier findings were preferred,
because they change the reading of many tests at once (mission §10, questions 2 and 9).

**What the drafting session read or computed (2026-10-17T09:30-10:05Z).**
- Committed documents: CLAUDE.md, AGENTS.md, the mission file, round 4 (§0-§4), CB8 §0-§2 and CB8-B, CB7-X, the queue
  README, the ledger tail, HB1 §1, SCREENING_BATCH_2 (F4/F5 rows), HISTORICAL_SOURCES §a, the data catalogue README.
- Code (read only): `trade_sample.parse_trades` keeps `transactionHash` (raw kept 3 days); the live monitor keeps only
  `tx16` (16 hex characters, not enough to fetch a receipt); `history_backfill` stores `trade_key` (a sha256 of the tx
  hash and other fields), not the hash. **No stored AREPO table can be audited without a fresh print fetch.** Every
  current print fetcher uses `takerOnly=true`.
- `battery2.cumulative_count()` on the Mac working tree (`battery2-count-v1`) = **1,131** at 2026-10-17T10:00Z. The
  ledger's CB1-D line records 1,106 under its own prose count; the counter value is the larger and is used as the lower
  bound here (§2.5).
- Host state (`scripts/oracle/queue_status.sh`, read only, 2026-10-17T09:52Z): `/` 36 GB, 8.7 GB free; data-dumps
  **12 GB**; MemAvailable about 4.1 GB; running q0084 (CB4 pmxt pilot) and q0102 (CB5); h7 fetches q0081/q0082 queued for
  the `net` lane; collector and monitors healthy.

### 0.3 Feasibility probes (counts only, 45 requests, nothing stored)

Scripts lived in `/tmp/cb9probe_scripts/` (not committed); no output file was written in the repo or in data-dumps.
No price, outcome price, volume or print side from the Data API was printed. 35 requests were keyless GETs; **10 were
read-only JSON-RPC `eth_getTransactionReceipt` POSTs to public Polygon endpoints** (no key, no state change; disclosed
because the brief named GET requests).

| # | Request(s) | Finding |
|---|---|---|
| 1 | Data API `/trades?limit=4&takerOnly=true` (1) + 5 receipts on three public endpoints | Rows carry `transactionHash`, `side`, `asset`, `outcomeIndex`, `proxyWallet`. Receipts reachable on `polygon-bor-rpc.publicnode.com`, `polygon.drpc.org`, `1rpc.io/matic`. **No log carries the v1 `OrderFilled` topic**: current fills come from two new exchange contracts |
| 2 | 1 Data API + 2 receipts, word-shape only | The new contracts `0xe111180000d2663c0091e4f400237545b87b996b` and `0xe2222d279d744050d28e00520010520000310f59` emit, by local keccak match, `OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)` (topic `0xd543adfd…`), `OrdersMatched(bytes32,address,uint8,uint256,uint256,uint256)` (`0x174b3811…`) and `FeeCharged(address,uint256)` (`0x55bb3cad…`). The v2 events carry an explicit **`uint8 side`** and a single `tokenId`; the taker `OrdersMatched` tokenId equals the print's `asset`; one maker fill in a minting match carries the complementary token. Only the on-chain enum value was seen, never compared with the Data API side |
| 3 | 2 Gamma + 2 Data API + 3 receipts (one 403) | 2026-04-20 fill: v1 events (`OrderFilled` `0xd0a08e8c…`, `OrdersMatched` `0x63bf4d16…`) on the neg-risk exchange (`0xc5d563…`). 2026-07-20 fill: v2 events on `0xe2222d…`. publicnode returned 403 for the April receipt; drpc served both eras |
| 4 | 10 Gamma (closed markets, `endDate` in `[d 19:59Z, d 20:01Z]`, paged) | Pyth equity dailies: **17 Up/Down markets on 06-22, 19 on 08-03 (fully paged), ≥ 17 on 04-20 (first page only)** (Airbnb, Amazon, Apple, Coinbase, EWY, Google, Meta, Micron, Microsoft, NVIDIA, Netflix, Opendoor, Palantir, Robinhood, Rocket Lab, SPY, Tesla; plus "SPY Opens" and SpaceX on 08-03), and strike ("close above $X") markets: 11 in 1 event on 06-22, 46 on 08-03. None is neg-risk. Gamma's page limit is 100 (paging needed). At 21:00Z on 07-15, ≥ 26 Pyth markets on the first page (not classified). At 20:00Z on 04-20 the first page also held Chainlink- (11) and Binance-sourced (7) markets; at 15:00Z on 07-15, none |
| 5 | 1 Gamma (out-of-window 2026-09-15 NVIDIA market, text and fee fields) | Rule text: Up iff the Pyth "Close" of the final regular-session minute is above the prior trading day's; equal → 50-50; no regular-session trade → 50-50; fallbacks (last valid Pyth price, then the primary exchange's official close); split-adjusted. `feeSchedule {rate 0.04, takerOnly, rebateRate 0.25}`; `orderMinSize` 5; `rewardsMinSize` 20; `rewardsMaxSpread` 4.5c; `startDate` the previous day 12:00Z |
| 6 | 9 Pyth requests (Benchmarks TradingView history, price_feeds, updates; Hermes historical and latest) + 2 pythdata.app pages | **Pyth price paths are not keyless.** TradingView history 404 (BTC control too); Benchmarks `updates/price` 401; Hermes historical and latest 401. Only feed metadata (`price_feeds`, with `schedule`) is keyless. The explorer page loads Pyth Pro (`pyth.dourolabs.app`, "trialPeriodDays 14") |
| 7 | 2 Yahoo chart requests (NVDA, out of window) | Hourly bars keyless (8 rows on 2026-03-02); **1-minute bars 32 days back refused (422)**. A minute path for April-August 2026 is not available keyless |
| 8 | 1 docs page (liquidity rewards) | Reward scoring uses a **"size-cutoff-adjusted midpoint"**; orders below `rewardsMinSize` do not score. CH80's route 2 (reward quotes centred on the dust mid) is therefore dead before any data (§0.4) |

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH79** trade-direction truth | **include (S), priority** | Cheapest, highest-value question in round 4. Probe 2 shows the on-chain record since the CLOB V2 switch carries an explicit `side` enum per order fill, so the truth is decodable from public receipts without keys or a subgraph. Designed as a measurement with a stated decision rule; the likely answer (the Data API is built from the same events) closes the attenuation hypothesis for about 2,700 requests. The WebSocket-feed side (Dubach's object) is measured too, through pmxt `last_trade_price` |
| **CH84** model-anchored maker | **include (P), narrowed to P2** | Disjoint from CB8-B by construction (equities, Pyth; CB8-B is crypto, Binance). The minute path the idea needs is not keyless (probes 6-7), so the maker is quoted only in the 5 minutes after each public hourly bar, where the anchor is fresh. The Chainlink-hourly and 15-minute crypto variants are dropped (below) |
| **CH83** Pyth dailies | **include (P), (a) generalised to P1; (b) dropped; (c) descriptive** | (a) becomes an hourly-checkpoint model-vs-ask taker test (10:32, 12:32, 15:32 ET) because the first public anchor is the 10:30 bar. (b) terminal minutes need the minute path: not testable historically; no counted prospective version (the live Pyth feed is keyed too). (c) the two half sessions are polled live as an uncounted descriptive (q0198) |
| **CH92** flow-skewed maker | **include (K)** | The maker dual of the only replicated flow result (HB2-R F4/F5). Runs on one fresh pmxt pull disjoint from every prior pmxt population, with K's 6h horizon matching F4/F5's target. Its interpretation depends on S0 (side quality), which is why both are in one batch |
| **CH80** dust midpoint | **include (D), route 1 only** | Free on K's pmxt hours. Route 2 dies on the docs fact (probe 8). Route 1 is a methods filter for every mid-based target (J4, J5, E004, Gamma-mid panels) |
| CH82 Combos | dropped | Sports-only today and `CB9_SPORTS_IN_PRIMARY = false` (sports scope is the user's open decision); catalogue prices may be indicative; no history, so a test needs weeks of polling. Re-entry: Combos in a non-sports category, or a user decision on sports |
| CH89 Deribit anchor for crypto ladders | dropped | Deribit's keyless history gives hourly bars only for recently expired options (round-4 probe: 85 bars over 7 days), so no historical join over the pmxt window; crypto ladders are CB5-L's object (sealed to CB5) and share CB8-B's calendar. Re-entry: after CB5-L reports, as a prospective poller |
| CH87 reporting-standard premium | dropped | Needs CB7's live `textorig` table, which CB7-S uses for a sibling text-class test; testing a second text classifier on it now forks CB7's features. Hold-to-resolution carries need weeks of resolutions. Re-entry: after CB7-S reports |
| CH84 Chainlink hourly / 15-minute crypto variants | dropped | Calendar overlap with CB8-B's sealed HOLDOUT weeks on the same assets; the 20:00Z probe shows Binance- and Chainlink-settled crypto markets mixed, so settlement-source parsing is unverified; sub-second competition. Re-entry: after CB8-B reports |
| CH81 joint events | dropped | Census floor (≥ 10 rule-identical joint events with both marginals) very likely fails today (3 seen); descriptive at best |
| CH85 proposer clocks | dropped (next in line) | A Polygon log scan of about 3,000 requests is feasible, but its carry needs fresh decided markets with weeks of resolutions and the CB1 tail gate; the `net` lane is full until after `T_seal` |
| CH86 tick-change vacuums | dropped | Event-driven pmxt hours give unpredictable ingress (a few hundred events a month scattered over hours); CB9 already spends about 130 GB of pmxt ingress |
| CH88 political underconfidence carry | dropped | Week-to-month holds; literature prior; clusters by resolution week are few within any CB9 window |
| CH90, CH91 nowcast and Manifold anchors | dropped | Each needs a new poller and a frozen matcher; few release clusters (CH90) or few matched questions (CH91) within weeks |
| CH93-CH98 flow-identity signatures | dropped for CB9 | They need fresh print fetches whose side quality is exactly what S0 measures; drafting them after S0 avoids building six detectors on a possibly mis-signed field. CH93 (pseudo-level placebo) is the first candidate for CB10 |

**Sports and weather.** As CB8: `CB9_SPORTS_IN_PRIMARY = false`. Sports is a sampled, reported, uncounted stratum in K
and D; S measures every category (a measurement of a data field, not an effect) and reports sports separately. Weather
is excluded from K and D (`h6_weather` and its live stage are never touched). Crypto Up/Down markets (`CB1_UPDOWN_RE`)
and Pyth dailies (`resolutionSource` host `pythdata.app`) are excluded from K and D.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB9 | Evidence ceiling |
|---|---|---|---|
| Data API taker prints, **S0a**: 250 markets, `[2026-10-01, 2026-10-15)` (**new**, q0181) | none | S0 stratum a (current exchange era; E007's era) | methods |
| Data API taker prints, **S0c**: 250 markets, `[2026-02-01, 2026-04-27)` (**new**, q0181; v1 exchange era; HB1/HB2 era) | none | S0 stratum c | methods |
| Public Polygon receipts (`eth_getTransactionReceipt`, keyless, endpoint list pinned) for S0 and S1 prints (**new**) | none (CB6-N plans logs, not receipts) | on-chain truth side | - |
| pmxt v2 hour 14Z of every window day, range reads by the K/D condition ids (**new**, q0186) | ECONOMIC_CONDITIONS B, r4_book, J3, CB1-C, CB4-N, CB8-B (other markets) | K Stage 1 (SCREEN events) and Stage 2 (HOLDOUT, sealed); D the same; S0b's pmxt feed side | L1 / L2 (sealed holdout) |
| Data API prints `[t − 6 h, t + 7 h]` for K/D market-days (**new**, q0186) | none | K flow feature, fills and 6h marks; S0b sample | as above |
| Gamma frame of Pyth equity Up/Down dailies 2026-04-13..08-10 (**new**, q0183; ids, tokens, question, `resolutionSource`, description flags and sha256, `endDate`, `startDate`; outcomes only in `outcomes_guarded.csv.gz`) | the §0.3 counts | P population | - |
| Yahoo chart hourly bars (regular session) and daily closes for the frame tickers, 2026-02-01..08-10 (**new**, q0183) | none | P anchor `S_t`, strike proxy `K_d`, σ; source check | - |
| pmxt hours 14Z, 16Z, 19Z of P sessions, range reads by ≤ 25 condition ids a day (**new**, q0184) | none | P1, P2 Stage 1 | L1 |
| Prospective P sessions after the freeze (**new**, q0195; CLOB `/book` at checkpoints, prints, bars) | none | P1-rep, P2-rep | L2 (out-of-time, post-freeze) |
| `history/h10_sign` (**new, conditional**, q0193): 1,200 markets, one 72-h window each in `[2026-05-01, 2026-10-01)`, all taker prints, receipts | none | S1 | L1 |
| `h1_first`, `h2_main`, `h3_power` | worn; h3 retired | **not read**, except their sha256-pinned `sample.csv.gz` id lists for exclusion | - |
| `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, `h8_tail`, `h8_text`, `h8_geo`, `h9_flow`, CB5 fetches, CB8-B frame/holdout, CB8-H holders, `cross_venue/` C1 legs | SB2, CB1-CB8 | **not read** (runner refuses). Committed seal copies and listings read for **ids only** | - |
| `cb1_extract/`..`cb8` extract tables, `cb3_followup/`, `cb6_followup/`, `live_trades/`, `trade_samples/`, `cross_venue_live/`, `surprise_live/` | CB1-CB8, monitor, E007, E009-E011 | **never read by any CB9 code path** | - |

### 1.2 Dates (declared; UTC unless ET is stated)

| Name | Value | Meaning |
|---|---|---|
| `T9_draft` | 2026-10-17T10:05Z | this draft; no CB9 quantity computed |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 boundary. **No CB9 fetch is bound to it.** No CB9 historical row lies at or after it; P Stage 2 rows are CB9's own post-freeze collection, never h4 data |
| `T9_hist_end` | 2026-10-01T00:00Z | `h10_sign` rows end before it |
| S0a window | `[2026-10-01, 2026-10-15)` | ends before the J4-R window (`[10-16, 10-21)`, `seals/j4r_window.json`) |
| S0c window | `[2026-02-01, 2026-04-27)` | v1 exchange era (CLOB V2 switch about 2026-04-28 11:00Z) |
| K/D and P days | `d ∈ [2026-04-13, 2026-08-10)` minus the pmxt gap `[06-12, 06-18)`; P uses NYSE full sessions only (about 78) | all in EDT |
| P checkpoints | 10:32, 12:32, 15:32 ET = 14:32Z, 16:32Z, 19:32Z (EDT); prospective sessions after 2026-11-01 use EST (+1 h in UTC) | bar end + 120 s |
| K/D origin | `t = d 14:00Z` (10:00 EDT) | one origin per market-day |
| K/D split | Gamma event SCREEN/HOLDOUT 50/50 by a seeded hash (`arepo-cb9-kd-split`) | at frame time, before any pmxt or print read |
| `T9_P2_start` | the first full NYSE session ≥ CB9 freeze commit + 1 day | P Stage 2 begins |
| `T9_P2_end` | `T9_P2_start` + 30 full sessions (half sessions and holidays skipped, counted) | collection ends; q0196 after `T9_P2_end` + 2 days |
| `T9_P2_collect_max` | `T9_P2_start` + 63 calendar days | freeze-slip rule as CB8: if 30 sessions cannot complete, P-rep is "not run (collection)", counted |
| Half sessions | 2026-11-27, 2026-12-24 (13:00 ET close) | q0198 descriptive only |

### 1.3 Sealed and untouched data (named)

- **Refused run ids and roots.** `run_cb9.py` refuses every root in the last three rows of §1.1. It writes only under
  `research_lab/creative_batch9/` and `history/h10_sign/`.
- **Exclusion keys (q0182).** CB8 q0164's key file (sha256-pinned) plus, by Gamma id lookup (≤ 50 ids per request,
  `closed=true` retry, parse guard keeping ids and keys only), every id in seal copies committed since q0164: h7_cb4_era,
  h7_cb4_series, h8_tail, h8_text, h8_geo, h9_flow (SCREEN and HOLDOUT listings), the CB8 updown frame and its HOLDOUT
  listing, the CB8-H holders frame. Keys = Gamma event id, `negRiskMarketID`, series id. A seal copy not yet committed is
  "absent at q0182"; **seal-time drops** at q0187 re-read every seal copy committed by then (as CB8 §1.3). If more than
  2% of exclusion ids lack metadata, disjointness is "unverified" and K1, D1, P1, P2 are "not testable", counted.
- **S0 and the seals.** S0 reads only public prints and receipts and computes no price, mark-out or outcome statistic.
  S0a (`[10-01, 10-15)`) lies after every CB historical window and before J4-R; its markets may overlap CB3-CB7
  prospective tables and the E-series calendar. CB9 reads none of their tables, and a side-agreement rate cannot reveal
  their statistics (disclosed as CB8 §1.3 for H). S0c drops markets by the CB7 q0141 exclusion keys (committed, 20,913
  ids) plus the committed seal copies at q0181's start; S0b is drawn from K's SCREEN prints, already disjoint.
- **E007.** E007 consumes the Data API side. An S0 verdict is a measurement caveat that E007's eventual report may cite;
  E007's protocol, data, sample and scoring are unchanged, and no CB9 path reads `trade_samples/`.
- **SEALED-KD (HOLDOUT events).** q0186 writes HOLDOUT book states, book events and prints into
  `creative_batch9/kd/holdout/` with a listing sha256; seal copy `seals/cb9_kd_holdout_SEAL.json` committed by q0187
  before q0188/q0189. The census reads HOLDOUT file and event counts only. No CB9 path opens a HOLDOUT file before K1 or
  D1 advanced and its Stage-1 result is committed.
- **Outcome guard (P).** Gamma `outcomePrices` go only to `outcomes_guarded.csv.gz`. Yahoo daily closes for settlement
  days go only to `closes_settle_guarded.csv.gz`; the feature file holds bars with end ≤ the checkpoint and `K_d`.
  Disclosed: consecutive daily closes determine the outcome; no CB9 code path compares them outside the analysis job
  (unit test), and the census writes counts only.
- **CB8-B.** No CB9 path reads crypto markets, Binance data or the 15Z pmxt hour. P reads equity markets at 14Z, 16Z,
  19Z; K/D read hour 14Z for non-crypto markets. Reading other condition ids from the same public pmxt files is not a
  read of CB8's sealed units (disclosed).
- **J4-R window and `T_seal`.** No CB9 historical row lies in `[2026-10-16, 2026-10-21)` or at/after `T_seal`.

### 1.4 Rules files

- `seals/cb9_sign_rules.json` (before q0180/q0181) fixes the S0 frames, sample sizes and seeds (`arepo-cb9-s0a`,
  `arepo-cb9-s0c`, `arepo-cb9-s0b`), the per-market print cap (4), the endpoint list and fallback order, the contract
  address and topic pins (§CB9-S), the match rule, the truth rules T1/T2, the fill-type classes and the smoke criteria.
  Every exchange address is pinned from Polymarket's published contracts list at rules-file time and cross-checked
  against the probe observations; the topics are the keccak values in §CB9-S.
- `seals/cb9_rules.json` (before q0182-q0186) fixes: P's question and description regexes, ticker map, checkpoint rule,
  σ rule, edge threshold, quote width and size; K/D's frame, sample sizes, seeds, split, origin, skew, fill, mark and
  dust rules; the census gates.
- Fetchers refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any S, P, K or D read.**
- **HMAC key continuity.** As CB8 §1.4: q0181, q0186, q0188 and q0193 hash `proxyWallet` in memory through the strict
  loader (never creates a key), pin `wallet_key_fingerprint`, refuse on mismatch. The raw address is compared with the
  receipt's `takerOrderMaker` in memory only and never written.

## 2. Common rules (deltas from CB8 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| P1 | buy the model-favoured token at the **recorded** pmxt best ask `a`; taker fee `f(a) = r·a·(1 − a)` with `r = max(recorded fee_rate_bps/10^4 at t, 0.04)` (finance, `feeSchedule` probe 5); held to settlement (hours) |
| P2 | resting maker, fee 0; **no rebate** in the primary (conservative); the version with `0.25 · 0.04 · p(1 − p)` per filled share is reported |
| K1 | resting maker, fee 0; no rebate in the primary; rebate version reported (`economics.REBATE_SHARE`, recorded rate) |
| D1 | none (methods) |
| Binding cost robustness | P1: +0.5c on `a`. P2 and K1: the trade-through fill rule (worst-case queue position; §2.6) |

### 2.2 Clocks

- **pmxt.** As CB8 §2.2: an event is used at `t` iff both clocks are ≤ `t`; crossed states ineligible, never repaired.
- **Data API prints.** Venue `timestamp`; a condition at `t` uses prints with `ts < t`.
- **Yahoo bars.** An hourly bar `[o, e)` is usable at `t` iff `e + 120 s ≤ t`. Daily close of day `d − 1` usable from
  `d 00:00Z`.
- **Receipts.** Block timestamp is diagnostic only; S matches by transaction hash, never by time.
- `closedTime` is never a population condition or an anchor.

### 2.3 Uncertainty and decision rule

As CB8 §2.3 (unweighted primary; one-sided p = max over declared cluster ways; 2,000-draw cluster bootstrap, seed 919;
small-G rule; A-C1 day way; top-5 drops of events and of days; ≥ 100 units and ≥ 30 clusters for testability; "unknown"
never counts as met). Cluster ways: **P** UTC session day and market (ticker); **K** Gamma event and UTC day; **D**
market x day and UTC day; **S** market (S0) and Gamma event (S1).

- **S0** is a measurement with a pre-stated decision rule (§CB9-S); it is counted but not in the Holm family.
- **Stage 1 (P1, P2, K1, D1; S1 if run).** Advance iff one-sided p < 0.01, the §2.4 floor is met, and every binding
  placebo, robustness check and gate holds. Batch-Holm label (one-sided α = 0.01, k1 = 4, or 5 with S1) reported; BY
  label (q = 0.10 over `battery2.cumulative_count()` at the run) as triage only.
- **Stage 2 (P1-rep, P2-rep, K1-rep, D1-rep).** One Holm at one-sided α = 0.05 over all CB9 tests reaching Stage 2, each
  in its Stage-1 direction; k fixed when the last Stage-1 result is final; early finishers judged at α/k. Labels: K1-rep,
  D1-rep "sealed same-calendar holdout replication (L2)"; P1-rep, P2-rep "out-of-time replication on post-freeze sessions
  (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| S0 | measurement | decision bands (§CB9-S): near-truth `q̂ ≥ 0.97`; material noise `q̂ < 0.90` |
| S1 | methods | ratio `R̂ ≥ 1.5` |
| P1 | economic | net ≥ +1.0c per share after fee |
| P2 | economic contrast | model-centred minus mid-centred ≥ +0.3c per posted share; route gate: model-centred net per posted share > 0 |
| K1 | economic contrast | skewed minus unskewed ≥ +0.5c per filled share; route gate: skewed net per filled share > 0 |
| D1 | methods | mean absolute-error gain ≥ +0.5c |

### 2.5 Counting (M3 rule)

- Kinds `cb9_test` (Stage 1), `cb9_replication` (Stage 2), `cb9_descriptive` (EXCLUDE: census, gates, strata, the S0
  feed-side column, the P strike stratum, q0198, every reported variant), placebo lines count 0. Count lines
  `creative_batch_9:S`, `:P`, `:K`, `:D` (`n_tests`). New `battery2.KIND_RULES` entries as CB8 §2.5; unknown kinds raise.
- **Cumulative count at drafting: 1,131** (`battery2.cumulative_count()`, Mac working tree, 2026-10-17T10:00Z; lower
  bound; the host union step runs before every counting CB9 job and records the post-union value).
- **CB9 adds 5 fixed tests (S0, P1, P2, K1, D1) and up to 5 conditional ones (S1, P1-rep, P2-rep, K1-rep, D1-rep).**
- Tests behind a failed or unknown gate (smoke, disjointness, GP, GK, GD, source checks, the S0 gates) are "not
  testable" or "not run" (p = 1) and are **still counted**. Conditional tests count only if their trigger fires; a
  triggered test that cannot run is counted with p = 1.

### 2.6 Placebos and robustness

Design rule as CB8 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 9191-9197.

- **P1 break-even calibration (binding).** `Y' = 1{U_d < a + f(a)}`, one uniform per session day shared by every unit
  of that day (comonotone across tickers and checkpoints; equities share a market factor). *Alternative guarded:* CR1
  p-values anti-conservative with ~78 strongly dependent days.
- **P1 anchor attribution (binding for crediting the public path).** P1_stale: identical rule with `S_t` from the bar
  one hour older (σ and `K_d` unchanged). Credit "public-path anchor" only if `P1 − P1_stale ≥ |P1| / 2`; a failure
  leaves an advance standing, labelled "a favourite/longshot pattern the anchor's timing does not explain".
- **P2 label-swap calibration (binding).** Within each quote-origin the model/mid labels are swapped with probability
  1/2, one draw per session day applied to every origin of the day. *Alternative:* shared settlement outcomes across a
  day's quotes make the clustered p anti-conservative.
- **K1 skew-sign calibration (binding).** The skew direction is replaced by a random sign, one draw per market x day,
  200 draws. *Alternative:* skewed quotes differ mechanically from the touch (price improvement changes fill sets), so a
  contrast can arise without any flow information.
- **K1 cell attribution (binding for crediting F4/F5).** K1_rest: the same contrast in origins outside both cells.
  Credit "F4/F5 moderation" only if `K1 − K1_rest ≥ |K1| / 2`; a failure leaves an advance labelled "skew helps in every
  cell".
- **D1 next-print shuffle calibration (binding).** Within each market x day, next-print prices are permuted across dust
  units (J4-R increment-shuffle analogue). *Alternative:* within-day level drift makes either mid "closer" by chance.

**Binding robustness for any advance or pass:** (i) the §2.1 cost robustness keeps the sign and ≥ half the magnitude
(P1 keeps net > 0); (ii) p threshold and floor hold without the top 5 clusters of each way; (iii) unweighted and
size-weighted estimates agree in sign (P1 by ask depth capped at 2,000 shares; K1 by filled shares; D1 by next-print
size); (iv) sign by month in ≥ two thirds of months with ≥ 30 units (P), ≥ 300 fills (K), ≥ 500 units (D); (v) the
declared worst case for unavailable units keeps the sign and p threshold (P: unavailable checkpoints scored as the
worst observed unit of that day; K: unavailable marks scored at −1 tick per filled share; D: units without a next print
excluded, counted); (vi) latency: P units and quotes start at bar end + 300 s instead of + 120 s; K fills only from
`t + 60 s`; each keeps the sign and ≥ half the magnitude.

### 2.7 Pre-freeze census (counts only; q0189)

Outcome guard first; field-restricted accessors; a unit test asserts that no census path receives a target, mark, fill
price or truth side. **No agreement, net, contrast or mark-out is computed.**
- **S0.** Prints sampled, receipts fetched, receipt failures by endpoint, matched-exactly-once share, T1/T2 availability
  (not agreement), fill-type counts, era counts. **Gate GS:** match rate ≥ 90% and ≥ 300 matched prints in each
  stratum; else that stratum is "not testable (source)".
- **P.** Frame counts by ticker; rule-text failures; key drops; sessions lost to pmxt gaps or Yahoo gaps; eligible
  checkpoints; units with model edge ≥ 5c on either side (a feature-only count: model value and ask, no outcome);
  quote-origins; print counts in quote windows. **Gate GP:** ≥ 300 P1 units, ≥ 40 session days, ≥ 15 tickers; ≥ 1,500
  P2 quote-origins with ≥ 100 fills of either quote. Fail → the test is "not testable", counted.
- **K.** Frame, key drops, SCREEN/HOLDOUT market and event counts; origins with a two-sided fresh book; the F4/F5 cell
  cut points computed **from feature values only** on SCREEN origins (frozen in the census output); origins in the
  cell; quote fills by rule (count only); marks available. **Gate GK:** ≥ 2,000 cell origins, ≥ 300 fills of each
  quote type, ≥ 60 events, ≥ 30 days.
- **D.** Two-sided market-minutes; dust-state share; dust units with a next print within 10 minutes. **Gate GD:** dust
  share ≥ 5% of two-sided market-minutes and ≥ 1,000 dust units in ≥ 100 market-days (CH80 kill 1). Fail → D1 "not
  testable (no dust state)", counted.
- MDEs are recomputed from these counts and are never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collector. Queue rules as CB8 §2.8 (one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 x `mem_mb`, 02:45-05:30 UTC blackout for `mem_mb ≥ 500`, exit 75 on
  headroom). Never two multi-GB jobs at once. pmxt jobs read **one row group at a time with column projection** and
  never materialise an hour file (the q0084 MemoryError lesson); peak RAM ≤ 1.5 GB.
- **Before `T_seal`.** Only q0180 (about 80 requests) and q0181 (about 2,700 requests: 500 Data API, about 100 Gamma,
  about 2,000 receipts; about 25 min at ≤ 2 rps, mem ≤ 300 MB), both `cpu` lane. **Nothing CB9 enters the `net` lane
  before 2026-10-22.**
- **After `T_seal`** (`net` lane, priorities 36-43, behind CB7 q0146, CB4 pmxt jobs and CB8 q0161-q0167):

  | Job | Work | Ingress / wall | Stored |
  |---|---|---|---|
  | q0182 | exclusion keys | about 400 Gamma requests | ≤ 0.01 GB |
  | q0183 | P frame + bars | about 300 Gamma + about 50 Yahoo requests | ≤ 0.01 GB |
  | q0184 | P books + prints | pmxt about 234 hours x ≤ 25 condition ids (≤ 24% of row groups) **ingress cap 40 GB**; about 4,700 print requests; about 1.5-2.5 h | ≤ 0.02 GB |
  | q0185 | K/D frame | about 1,200 Gamma requests | ≤ 0.01 GB |
  | q0186 | K/D books + prints | pmxt hour 14Z of about 111 days, all row groups touched (markets spread across the sort key), 13Z lookback only for tokens with no 14Z event: **ingress cap 90 GB**, days in seeded order so a cap truncates evenly (unprocessed days unavailable, counted); about 12,000 print requests at ≤ 4 rps; about 3-5 h in 85-min chunks; mem ≤ 1.5 GB | ≤ 0.15 GB |
  | q0188 | S0b receipts | about 1,000 receipts | ≤ 0.01 GB |
  | q0193 | S1 (conditional) | about 1,300 Gamma + about 2,500 print requests + ≤ 20,000 receipts (about 3 h at 2 rps) | ≤ 0.05 GB |
  | q0195 | P Stage 2 (conditional) | about 150 requests per session x 30 sessions, `cpu` lane | ≤ 0.01 GB |
  | q0198 | half-day poll | about 3,500 requests per half day, `cpu` lane | ≤ 0.01 GB |

- **Disk guard.** Every CB9 data job exits 75 when data-dumps + its output cap > **13 GB** (current convention). Data-dumps
  is **12 GB** today, so CB9 jobs may wait on the nightly archive rotation; the precondition never changes retention.
  CB9 output caps total ≤ 0.3 GB.
- **Network etiquette.** Shared `Limiter`, yield to the live collector, 429 / `Retry-After` back-off, stop on repeated
  429, collector-health stop. Polygon RPC ≤ 2 rps, pinned endpoint order (drpc, 1rpc, publicnode), a receipt is
  "unavailable" after every endpoint failed twice (counted). Yahoo ≤ 1 rps.
- **Stop rules.** 10 CPU-hours per family. A job that fails twice for the same non-transient reason stops and is
  recorded. A null is "not detected at MDE x". **No re-screen of a failed CB9 test** with altered checkpoints, edge
  thresholds, widths, skews, cells, horizons, dust thresholds, windows or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2) → separate prospective confirmation (Stage P) →
economic validation at recorded prices.
- **S** has no Stage P: it is a methods measurement. A "material noise" verdict produces methods note M4 (re-stated flow
  ceilings) and, through S1, an input to every later flow design.
- **Stage P-P.** A receipt-timed checkpoint poller with a keyless real-time anchor; if only hourly anchors remain
  keyless, Stage P keeps the hourly design.
- **Stage P-K.** The skew rule live on sweep-recorded books and the print stream.
- **Stage P-D.** One field (touch size) added to the sweep row under a separately reviewed collector change; never
  bundled with CB9.

---

## 3. Tests

### CB9-S: Trade-direction truth audit (CH79)

**Question.** How often does the Data API's taker `side` (with `asset` / `outcomeIndex`) give the same YES-terms sign as
the taker order recorded on chain? If agreement is low, how much larger is the flow-continuation slope when flow is
signed from the chain?

**Mechanism and why it matters.** Every AREPO flow result (E007, HB1 FL family +0.3 to +0.6c per SD, HB2-R F4/F5) signs
flow with the Data API side. Under symmetric misclassification with accuracy `q`, a slope is attenuated by about
`2q − 1`; Dubach (2026) reports about 59-62% agreement for the public *feed*. If the Data API is that noisy, true effects
could be several times the measured ones (CH79). The probe (§0.3) makes the most likely answer visible in advance: since
CLOB V2 the exchange logs an explicit side per taker order, and the Data API is probably indexed from those logs, so
agreement is probably near 1. That is still worth 2,700 requests: it either closes CH79 or re-scales every flow test.

**On-chain truth (fixed now).**
- Pins (re-verified at rules-file time): v1 era `OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)`
  `0xd0a08e8c493f9c94f29311604c9de1b4e8c8d4c06bd0c789af57f2d65bfec0f6`, `OrdersMatched(bytes32,address,uint256,uint256,uint256,uint256)`
  `0x63bf4d16b7fa898ef4c4b2b6d90fd201e9c56313b65638af6088d149d2ce956c`, on the CTF Exchange and Neg-Risk CTF Exchange
  (addresses pinned from Polymarket's contracts list; probe saw `0xc5d563…`). v2 era
  `OrderFilled(bytes32,address,address,uint8,uint256,uint256,uint256,uint256,bytes32,bytes32)`
  `0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee` and `OrdersMatched(bytes32,address,uint8,uint256,uint256,uint256)`
  `0x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c` on `0xe111180000d2663c0091e4f400237545b87b996b` and
  `0xe2222d279d744050d28e00520010520000310f59`; Conditional Tokens ERC-1155 `0x4d97dcd97ec945f40cf65f87097ace5ea0476045`.
- **Match.** A print matches the receipt's `OrdersMatched` log whose `takerOrderMaker` equals the print's `proxyWallet`
  (compared in memory) and whose token is the print's `asset` or its complement; if several, the one whose share
  amount equals `size` within 1e-6; zero or several remaining → "unmatched" (counted).
- **T1 (event-declared).** v2: the `side` enum of the matched `OrdersMatched`, decoded with the enum mapping from the
  published v2 source, and its `tokenId`. v1: BUY of `takerAssetId` if `makerAssetId = 0` (collateral), else SELL of
  `makerAssetId`.
- **T2 (asset-flow, independent of the enum).** The ERC-1155 `TransferSingle`/`TransferBatch` logs of the Conditional
  Tokens contract in the same receipt: the taker wallet (or the exchange on its behalf, as pinned) receiving the token →
  BUY of that token; sending → SELL.
- **Source gate.** T1 = T2 on ≥ 99% of matched prints where both exist; else S0 "not testable (on-chain truth
  ambiguous)", counted.
- **YES-terms sign.** `+1` for BUY of outcome 0 or SELL of outcome 1, `−1` otherwise (the `trade_sample._sign`
  convention). **Primary agreement `A_yes`** = Data API sign = T1 sign. Token-terms agreement `A_tok` (side and asset
  both equal) is reported.
- **Fill type** from the receipt: normal (maker fills on the same token), mint (complementary BUYs with
  `PositionSplit`), merge (complementary SELLs with `PositionsMerge`), mixed.

**Samples (fixed now; seeds in the rules file).**
- **S0a** (current era): Gamma frame of markets with `startDate < 10-15`, scheduled `endDate ≥ 10-01`, Gamma volume ≥
  $1k; seeded 250 markets (≤ 3 per event); one windowed `/trades?market&start&end&takerOnly=true` request series per
  market over `[10-01, 10-15)` (≤ 5 pages); 4 prints per market by seeded draw → 1,000 prints.
- **S0c** (v1 era): the same over `[02-01, 04-27)` with CB7 keys and committed seal copies dropped → 1,000 prints.
- **S0b** (pmxt era, May-Aug): 1,000 prints drawn (≤ 4 per market) from K's SCREEN prints; each also matched by
  transaction hash and asset to a pmxt `last_trade_price` event, whose `side` is the **feed-side** column (descriptive:
  Dubach's object).
- Stored per print: hashed wallet, market id, tx hash, asset, Data API side and outcome index, size, price band label,
  liquidity tercile, era, T1, T2, fill type, match status, pmxt feed side (S0b). No price, mark or outcome.

**Statistic and decision rule (S0, per stratum and pooled).** `q̂` = share of matched prints with `A_yes = 1`; Wilson
99% interval; market-clustered bootstrap reported.

| Verdict | Condition | Consequence |
|---|---|---|
| **near-truth** | `q̂ ≥ 0.97` and Wilson lower bound ≥ 0.95 in every stratum passing GS | CH79's attenuation route closed; flow results stand as measured; S1 not run (not counted) |
| **minor noise** | otherwise, with `q̂ ≥ 0.90` and worst-case `q_wc ≥ 0.85` in every stratum | ceiling re-scaling ≤ `1/(2·0.90 − 1)` = 1.25x, too small to make a taker flow route material (it needs about 5x, CH79); methods note only; S1 not run |
| **material noise** | `q̂ < 0.90` or `q_wc < 0.85` in any stratum passing GS | methods note M4 (ceilings re-stated by `1/(2q̂ − 1)` as an upper bound under symmetric noise, labelled as such); S1 runs for that era |

`q_wc` scores unmatched prints as disagreements. Reported: `q̂` by liquidity tercile, price band, fill type, sports
stratum; `A_tok`; the feed-side agreement in S0b; the share of disagreements that are mint/merge fills.

**S1 (conditional): does on-chain signing raise the flow slope?**
- Data `h10_sign` (q0193): 1,200 markets disjoint by keys (including h9_flow), one seeded 72-h window each in the
  material-noise era within `[2026-05-01, 2026-10-01)` (or `[02-01, 04-27)` if only S0c triggered), all taker prints;
  receipts for every print in windows taken whole in seeded order until 20,000 prints (whole windows only).
- Units: 2h grid origins with ≥ 3 prints in `[t − 6 h, t)`. `x_api`, `x_chain` = 6h notional imbalance in YES terms,
  clipped to [−1, 1], **raw (no SD scaling)**, computed on identical prints; `d_6h` = last print price (YES terms) before
  `t + 6 h` minus last print before `t`, each within 30 minutes of its anchor, else unavailable.
- Statistic `R = β_chain / β_api` from two OLS fits `d = α + β x` on identical units; event-clustered bootstrap of the
  ratio. **S1 passes** iff `R̂ ≥ 1.5` and one-sided p (bootstrap share of `R ≤ 1`) < 0.01. Reported: `β_chain` in cents
  per unit flow at 6h (an economic reading against the 1.8c liquid round trip, not a route test).
- **MDE (assumption; census replaces).** With about 8,000 usable origins in about 900 events and `β_api` at about 4 SE
  (HB1 FL2 scale), the paired fits correlate strongly (ρ ≥ 0.8), so a ratio of about 1.5 is resolvable from 1.

**Leakage.** None for S0 (no outcome, no price target). S1 uses prints before `t` for features, print prices only for
targets, fresh markets only; E007, HB1 and HB2 rows are never re-read.

**What kills CH79.** S0 near-truth or minor noise; or S1 `R̂ < 1.5`.

### CB9-P: Hourly-anchored Pyth equity dailies (CH83a generalised + CH84 narrowed)

**Question.** In Pyth-settled equity "Up or Down" dailies, (P1) does buying the token a frozen digital model favours by
≥ 5c over its recorded ask, held to settlement, pay after fees? (P2) Does a maker quoting ±1c around the model value
for 5 minutes after each public hourly bar earn more per posted share than the same maker quoting around the book mid?

**Mechanism.** The payoff is a digital option on a public price; its fair value at any time is a function of the price
now, the strike (previous close), the time left and intraday volatility. Retail prices it by feel; the crowd is six
months old. The model's only enemy is latency and σ error, not private information (CH84). The hourly bar is the
coarsest public anchor; if the book is off by ≥ 5c after a fresh hourly print, the mispricing is not a speed game.

**Population (q0183; frozen; no outcome, price or volume used).**
1. Gamma closed markets with `endDate` in `[d 19:59Z, d 20:01Z]` for each full NYSE session `d` in the window (paged).
2. `resolutionSource` host `pythdata.app` with path `Equity.US.<T>/USD`; question matches
   `^(.+) \(([A-Z]{1,5})\) Up or Down on [A-Z][a-z]+ \d{1,2}\??$` with group 2 = `<T>`; two outcomes; not neg-risk.
   "SPY Opens" and strike ("close above") markets are excluded from the primary (strike markets: reported stratum).
3. Description contains all frozen flags (written from the out-of-window 2026-09-15 text, probe 5): Pyth "Close" of the
   final regular-session minute; "most recent prior trading day"; the 50-50 equality clause; the no-trade clause.
4. Exclusion ids and keys dropped; the ticker exists in the Yahoo bars for every window session (else the ticker is
   unavailable, counted).

**Features (causal).** At checkpoint `t` (bar end + 120 s): `S_t` = close of the latest usable hourly bar; `K_d` =
Yahoo daily close of the prior session (proxy for the Pyth final-minute close); `σ` = SD of regular-session hourly log
returns over the prior 20 sessions (overnight gaps excluded; ≥ 100 returns, else unavailable), per hour; `τ` = hours to
16:00 ET; `fair_Up = Φ(ln(S_t/K_d) / (σ√τ))`, `fair_Down = 1 − fair_Up`. Model fixed now; no drift, no fitting.

**Book (pmxt at `t`, fresh as CB8-B: latest event ≥ `t − 120 s`; crossed ineligible).** Best bid, ask, sizes, tick,
`fee_rate_bps` for both tokens.

**P1 units.** (market-day, checkpoint) with features and a fresh book; **traded** iff on some token
`fair − a − f(a) ≥ 0.05` and the size at `a` ≥ 5 shares (if both, the larger edge). `net = Y − a − f(a)` per share,
`Y` from the guarded Gamma outcome (0.5 on 50-50).

**P2 units.** Every (market-day, checkpoint) with a fresh two-sided book. Two paper quote pairs on the Up token, 20
shares each side (`rewardsMinSize`), live `[t, t + 300 s]`: model-centred `bid = floor_tick(fair_Up − 0.01)`, `ask =
ceil_tick(fair_Up + 0.01)`; mid-centred the same around the book mid; each capped passive (bid ≤ best ask − tick, ask ≥
best bid + tick). Fills by `cb3_maker.quote_fills` with the queue rule (`cb1_history.queue_fill`), counting
complementary prints in Up terms (taker BUY Down at ≥ `1 − bid` fills the Up bid). P&L per fill = `Y − p` (bought Up) or
`p − Y` (sold Up), held to settlement. Statistic per quote-origin = (model P&L − mid P&L) / 40 posted shares.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **P1** | economic | traded checkpoint (Stage 2: post-freeze sessions) | mean `Y − a − f(a)`, cents per share | > 0 |
| **P2** | economic contrast | quote-origin | mean (model − mid) P&L per posted share, cents | > 0 |

**Source check.** Yahoo-implied direction (`close_d` vs `K_d`, guarded) vs the Gamma outcome on days with |return| >
0.1%: disagreement > 2% of market-days → P "not testable (source)", counted. Disagreeing units stay in the P&L with the
Gamma outcome (what pays).

**Gates.** GP (§2.7); floors §2.4; P2 kill if either quote's fill rate < 2% of quote-origins (CH84 kill 2) or if the
share of model-quote losses on fills within 60 s of a ≥ 1σ(5-min) move cannot be computed (no minute path; reported as
"latency tail not measurable"), which leaves P2 standing but labelled.

**MDE (assumptions; census replaces).** About 78 sessions x 18 markets x 3 checkpoints ≈ 4,200 checkpoints; perhaps
15-30% traded. With per-share SD about 45c and a within-day correlation of 0.15-0.3, the day-clustered SE is about
2.2-3c: **P1 MDE about 7-10c**. P2: about 4,000 quote-origins, per-origin SD about 15c, day-clustered: **MDE about 2c
per posted share**. Both detect only large effects (CH83's claimed 5-15c is the target); smaller real residuals are
"not detected at MDE x".

**Stage 2 (registered only if P1 or P2 advanced).** q0195 records, for 30 full sessions from `T9_P2_start`, the CLOB
`/book` of every frame-rule market at each checkpoint (receipt-timed), all prints of the quote windows (after the
session), Yahoo hourly bars (after the session). Identical definitions, model, thresholds, widths, gates. CLOB books
replace pmxt (receipt clock only; disclosed).

**Half sessions (q0198, descriptive, uncounted).** On 2026-11-27 and 2026-12-24 the regular session ends 13:00 ET while
`endDate` stays 16:00 ET (to be confirmed per market from the frozen text and `endDate`). From 13:05 to 16:00 ET, every
minute: the book of each frame-rule market; Yahoo 1-minute bars of the day fetched after the close (available for
recent days). Reported: any ask < 0.97 on the side the 13:00 close already decided, its size and duration. A null on
both days is a two-day descriptive, not a test.

**Leakage.** Bars usable only after `e + 120 s`; σ from prior sessions; `K_d` from the prior session; settlement closes
guarded; Yahoo vs Pyth basis of cents (the 5c edge threshold and the source check bound it); no CB8-B data.

**What kills the family.** GP fails; P1 net ≤ 0 or below floor; the stale-anchor attribution fails (P1 labelled, not
credited); P2 contrast CI includes 0 at MDE, fill rate < 2%, or the route gate fails ("mid quoting loses less, no
route"); Stage 2 fails out of time.

### CB9-K: Flow-skewed touch maker in the F4/F5 cells (CH92)

**Question.** At origins in the high-volatility or wide-spread cells, does a touch maker who shifts both quotes one tick
in the direction of the frozen 6h flow feature earn more per filled share at a 6h mark than the same maker unskewed,
and is the skewed maker net-positive?

**Mechanism.** HB2-R replicated flow continuation conditional on volatility (F4, ratio 1.59) and spread (F5, 1.27),
gross about 1c per trade in the favourable tercile, net taker −2.5c and about −0.4c even at half-spread without fees. A
maker who leans with the flow is filled more by the side that will be wrong and less by the side that will be right, so
the continuation becomes a maker gain instead of an adverse-selection cost.

**Population and sampling (q0185; frozen).** Gamma markets with scheduled life overlapping the window by ≥ 3 days,
Gamma volume ≥ $10k (end-of-life field; a disclosed look-ahead in selection, not outcome), two outcomes, not neg-risk
augmented, non-weather, not crypto Up/Down, not Pyth; key drops; ≤ 3 markets per event; seeded 1,000 markets; event
split SCREEN/HOLDOUT 50/50 before any read. Sports markets sampled into a reported stratum (≤ 15%).

**Origin, book and features.** `t = d 14:00Z` for each market-day in the window; pmxt state of outcome-0 token at `t`
(fresh: latest event ≥ `t − 3,600 s`; crossed or one-sided ineligible). Features from prints with `ts < t`:
`x6` = HB2's frozen definition (`f_imb_6h` notional imbalance in YES terms, clip [−1, 1] / 0.8578); `RV` = log of the
1-day realised volatility of print prices (+1e-4) (the h2 `ml_rv_1d` analogue on prints); `SPR` = the pmxt touch spread
at `t`. Cell = `RV` ≥ its SCREEN top-tercile cut **or** `SPR` ≥ its top-tercile cut (cuts from feature values only, frozen
in the census). Skew direction `s = sign(x6)` where `|x6|` ≥ its SCREEN median (feature-only cut), else no skew (origin
excluded from K1, counted).

**Quotes (live `[t, t + 2 h]`, 50 shares each side).** Unskewed: bid at best bid, ask at best ask. Skewed (`s = +1`): bid
at best bid + 1 tick (if still < best ask, else best bid), ask at best ask + 1 tick; mirrored for `s = −1`. Fills by
`cb3_maker.quote_fills`, queue rule, complementary prints in YES terms. Mark `M` = midpoint of the last taker-BUY and last
taker-SELL print prices (YES terms) in `[t + 5 h, t + 7 h]`, both required, else the origin's fills are unavailable.
Mark-out per filled share: bid `M − p`, ask `p − M`.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **K1** | economic contrast | cell origin (SCREEN events; Stage 2: HOLDOUT events) | mean mark-out per filled share, skewed minus unskewed (fill-weighted within origin, origins equally weighted), cents | > 0 |

**Binding route gate.** The skewed maker's mean mark-out per filled share in the cell > 0 at the point estimate; else
"skew helps, but the maker still loses: no route". If the unskewed maker alone is ≥ +0.5c with p < 0.01, the verdict is
"CB3-B's maker result; skew not needed" (CH92 kill 2), whatever K1.

**Fill realism.** Hourly-resolution queue position is uncertain (ECONOMIC_CONDITIONS part B). Binding: the
trade-through rule (fills only from prints strictly through the quote) keeps the sign and ≥ half the magnitude. The
fill rate of each quote type is reported; a quote never filled counts 0 shares (it does not enter per-filled-share means
but enters the per-posted-share version, reported).

**MDE (assumptions).** About 800 markets x about 15 origin days ≈ 12,000 origins; about 55% in the cell; fill rate about
15% per side → about 2,000 filled origins per quote type in about 300 SCREEN events; mark-out SD about 4c per filled
share; contrast SE about 0.15c → **MDE about 0.5c**, at the floor. S0's verdict labels K1: under "material noise" K1 is
reported as "measured with noisy sides" (an attenuated test).

**Leakage.** Features from prints before `t`; cut points feature-only; marks from print prices after `t + 5 h`; the
skew is never re-tuned (one tick, frozen); HOLDOUT sealed. **Known decay:** F4/F5 fell to 40-55% in HB2-R's post-split
half; a null may be decay, not absence (reported).

**What kills CH92.** GK fails; K1 not detected at MDE; skew-sign placebo advances; cell attribution fails (labelled);
route gate fails; K1-rep fails on HOLDOUT.

### CB9-D: Dust-anchored midpoint (CH80, route 1)

**Question.** When a best level is dust, is the next print closer to the size-cutoff mid than to the displayed mid, by
how much, and how common is the state?

**Mechanism.** New orders need `orderMinSize` (5 shares) but partial fills leave smaller residuals; the displayed best
bid/ask ignores size, so the Gamma mid, `oneHourPriceChange` and AREPO's mid targets can be set by an order no one can
trade against. Reward scoring already uses a size-cutoff-adjusted mid (probe 8), so the reward route is closed; the
methods route remains.

**Units (K/D markets, pmxt hour 14Z, both tokens).** Market-minute ends `u ∈ [14:01Z, 15:00Z]` with a two-sided fresh
book. Dust state: best bid or best ask level with size < 5 shares or size x price < $1. Displayed mid `m_d` = (best bid +
best ask)/2; size-cutoff mid `m_c` = mid of the best bid and best ask among levels with size ≥ 5 shares and notional ≥
$1 (unavailable if either side has none). Next print `P` = first pmxt `last_trade_price` of the token after `u` within 10
minutes (else unavailable). One unit per market-minute; at most one unit per dust episode per 5 minutes (the first).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **D1** | methods mechanism | dust unit (SCREEN events; Stage 2: HOLDOUT events) | mean `|P − m_d| − |P − m_c|`, cents | > 0 |

**Reported (descriptive).** Dust share of two-sided market-minutes by liquidity tercile and price band; the share of
displayed-mid changes within the hour caused by a dust level appearing or disappearing; `|m_d − m_c|` distribution.

**MDE (assumption).** Thousands of dust units in hundreds of market-days; **MDE about 0.2c**; the floor (0.5c) binds.
The statistic is partly mechanical (a market order sweeps dust); its value is the size of the methods correction and
the state frequency, which is why D1 is labelled methods, not economic.

**What kills CH80.** GD fails (dust < 5% of two-sided market-minutes: "dust is rare, no correction needed"); D1 below
floor or not detected; the shuffle placebo advances.

### CB9-F: Data jobs

q0180 smoke (PASS needs: ≥ 18 of 20 receipts per era decoded with the pinned topics and T1 = T2; Yahoo hourly bars for
an out-of-window session with 7 regular-session bars; Gamma paging returns stable counts on two out-of-window days; pmxt
HEADs 200 for three window hours). q0181/q0188 audit samples. q0182 keys. q0183-q0184 P frame, bars, books, prints.
q0185-q0187 K/D frame, books, prints, seal. q0189 census. q0193 conditional S1 fetch. q0195/q0198 prospective P
collections. Every data job writes a manifest (file sha256, request counts, failures, fingerprint, data-dumps size and
margin).

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` is under `backend/scripts/`, `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check; analysis
jobs also need the CB9 freeze. All `family` = `creative_batch_9`.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0180 | cpu | 47 | about 80 req, < 5 min, mem 200 | - | sign rules file + smoke code reviewed |
| q0181 | cpu | 46 | about 2,700 req, about 25 min, mem 300, ≤ 0.01 GB | q0180 | q0180 PASS |
| q0182 | net | 43 | about 400 req | q0164, q0166, q0168 | after `T_seal` |
| q0183 | net | 42 | about 350 req, ≤ 0.01 GB | q0182 | with q0182 |
| q0184 | net | 40 | pmxt ≤ 40 GB, about 4,700 req, mem 1,500, ≤ 0.02 GB | q0183 | with q0183 |
| q0185 | net | 42 | about 1,200 req, ≤ 0.01 GB | q0182 | with q0182 |
| q0186 | net | 39 | pmxt ≤ 90 GB, about 12,000 req, mem 1,500, ≤ 0.15 GB | q0185 | with q0185 |
| q0187 | cpu | 39 | light | q0186 | with q0186 |
| q0188 | net | 38 | about 1,000 receipts, mem 300 | q0187 | with q0187 |
| q0189 | cpu | 37 | ≤ 1.2 GB | q0181, q0184, q0187, q0188 | after the seal copy is committed |
| q0190-q0192 | cpu | 36 | ≤ 1.5 GB | q0189 | after the CB9 freeze |
| q0193-q0194 | net / cpu | 36 | ≤ 20,000 receipts / ≤ 1 GB | q0190 | only on "material noise" |
| q0195 | cpu | 44 | about 150 req/session, rolling | q0191 | only if P1 or P2 advanced |
| q0196 | cpu | 36 | ≤ 0.5 GB | q0195 | after `T9_P2_end` + 2 d |
| q0197 | cpu | 36 | ≤ 1.5 GB | q0192 | only if K1 or D1 advanced |
| q0198 | cpu | 45 | about 3,500 req per half day | - | half-day rules hash committed before 2026-11-27 |

```json
{"id": "q0180_cb9_smoke", "title": "CB9: smoke (20 receipts per exchange era decoded with pinned topics, T1 = T2; Yahoo hourly bar shape out of window; Pyth frame paging on 2 out-of-window days; pmxt HEADs); counts only", "family": "creative_batch_9", "priority": 47, "expected_value": "go/no-go for every CB9 source", "data": ["public Polygon JSON-RPC (keyless)", "public Data API, Gamma", "Yahoo chart (hourly, out of window)", "pmxt HEAD"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "cpu", "network": "polygon-rpc, data-api, gamma-api, yahoo, r2v2.pmxt.dev"}, "depends_on": [], "argv": ["scripts/run_cb9.py", "smoke", "--rules", "../docs/research_lab/seals/cb9_sign_rules.json", "--rps", "2"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch9/smoke.json", "trials.jsonl (cb9_descriptive)"], "next_action": "PASS: q0181; FAIL of the receipt part: S0 not run (source), counted", "notes": "CREATIVE_BATCH_9.md CB9-F. DRAFT. May run before T_seal (cpu lane). Prints counts only."}
{"id": "q0181_cb9_sign_audit_A", "title": "CB9-S: S0a [2026-10-01,10-15) and S0c [2026-02-01,04-27) print samples (250 markets x 4 prints each), receipts, T1/T2, fill type; no agreement computed", "family": "creative_batch_9", "priority": 46, "expected_value": "S0 data for the side-flag measurement", "data": ["public Gamma, Data API windowed trades", "public Polygon JSON-RPC receipts", "creative_batch7/exclusion_keys (ids only)"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, data-api, polygon-rpc"}, "depends_on": ["q0180_cb9_smoke"], "argv": ["scripts/run_cb9.py", "sign-audit", "--strata", "a,c", "--rules", "../docs/research_lab/seals/cb9_sign_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "13"], "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch9/sign/{s0a,s0c}/{prints_classes.csv.gz,manifest.json}"], "next_action": "q0189 census (counts); agreement only in q0190 after the freeze", "notes": "DRAFT. cpu lane before T_seal; raw proxyWallet compared with takerOrderMaker in memory only; HMAC strict loader."}
{"id": "q0182_cb9_exclusion_keys", "title": "CB9: exclusion keys = CB8 q0164 keys + ids/keys of seal copies committed since (h7_cb4_*, h8_*, h9_flow, CB8 updown frame/holdout, CB8-H frame)", "family": "creative_batch_9", "priority": 43, "expected_value": "disjointness of P, K, D", "data": ["creative_batch8/exclusion_keys.csv.gz", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0164_cb8_exclusion_keys", "q0166_cb8_updown_books", "q0168_h9_flow_seal"], "argv": ["scripts/run_cb9.py", "exclusion-keys", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "13"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch9/exclusion_keys.csv.gz", "manifest.json"], "next_action": "q0183, q0185", "notes": "DRAFT. After T_seal. >2% missing metadata -> disjointness unverified (P, K, D not testable, counted)."}
{"id": "q0183_cb9_pyth_frame", "title": "CB9-P: Gamma frame of Pyth equity Up/Down dailies ending 20:00Z on full NYSE sessions 2026-04-13..08-07 (minus pmxt gap), frozen regexes and text flags, key drops; Yahoo hourly + daily bars 2026-02-01..08-10; outcomes and settlement closes to guarded files", "family": "creative_batch_9", "priority": 42, "expected_value": "P population and anchors", "data": ["public Gamma", "Yahoo chart hourly/daily", "creative_batch9/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, yahoo"}, "depends_on": ["q0182_cb9_exclusion_keys"], "argv": ["scripts/run_cb9.py", "pyth-frame", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "13"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch9/pyth_frame/{frame.csv.gz,bars_pre.csv.gz,strikes.csv.gz,closes_settle_guarded.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0184", "notes": "DRAFT. No code path compares consecutive closes outside q0191."}
{"id": "q0184_cb9_pyth_books", "title": "CB9-P: pmxt states at 14:32Z/16:32Z/19:32Z checkpoints (fresh rule) and Data API prints in [t, t+300 s] for frame markets", "family": "creative_batch_9", "priority": 40, "expected_value": "P1/P2 Stage 1 inputs", "data": ["pmxt v2 hourly files (range reads by <= 25 condition ids)", "public Data API windowed trades"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "net", "network": "r2v2.pmxt.dev, data-api"}, "depends_on": ["q0183_cb9_pyth_frame"], "argv": ["scripts/run_cb9.py", "pyth-books", "--ingress-cap-gb", "40", "--rps", "2", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "13", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["research_lab/creative_batch9/pyth/{states.csv.gz,prints.csv.gz,manifest.json}"], "next_action": "q0189", "notes": "DRAFT. Row-group streaming, column projection. Resumable per session.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"(pyth_books_complete|ingress_cap_reached)\""}}
{"id": "q0185_cb9_kd_frame", "title": "CB9-K/D: Gamma frame (life overlap >= 3 d, volume >= $10k, non-weather, non-crypto-updown, non-Pyth), key drops, <= 3 per event, seeded 1,000 markets, event split SCREEN/HOLDOUT (arepo-cb9-kd-split)", "family": "creative_batch_9", "priority": 42, "expected_value": "K/D population and split", "data": ["public Gamma", "creative_batch9/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0182_cb9_exclusion_keys"], "argv": ["scripts/run_cb9.py", "kd-frame", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "13"], "timeout_s": 3000, "max_retries": 2, "outputs": ["research_lab/creative_batch9/kd_frame/{frame.csv.gz,split.json,manifest.json}"], "next_action": "q0186", "notes": "DRAFT. Split written before any pmxt or print read."}
{"id": "q0186_cb9_kd_books", "title": "CB9-K/D: pmxt hour 14Z (13Z lookback only when needed) of every window day for frame markets: origin states, all book and last_trade_price events of the hour; Data API prints [t-6h, t+7h]; HOLDOUT written to holdout/", "family": "creative_batch_9", "priority": 39, "expected_value": "K1/D1 inputs, S0b sample", "data": ["pmxt v2 hourly files", "public Data API windowed trades"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "net", "network": "r2v2.pmxt.dev, data-api"}, "depends_on": ["q0185_cb9_kd_frame"], "argv": ["scripts/run_cb9.py", "kd-books", "--ingress-cap-gb", "90", "--rps", "4", "--disk-cap-gb", "0.15", "--data-dumps-cap-gb", "13", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["research_lab/creative_batch9/kd/{screen,holdout}/...", "manifest.json"], "next_action": "q0187", "notes": "DRAFT. Days in seeded order; cap truncates evenly; never two multi-GB jobs at once.", "repeat": {"max_runs": 10, "until_log_regex": "\"status\": \"(kd_books_complete|ingress_cap_reached)\""}}
{"id": "q0187_cb9_kd_seal", "title": "CB9-K/D: HOLDOUT listing sha256, seal-time drops vs seal copies committed by now, seal copy seals/cb9_kd_holdout_SEAL.json", "family": "creative_batch_9", "priority": 39, "expected_value": "sealed holdout", "data": ["creative_batch9/kd/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api (light)"}, "depends_on": ["q0186_cb9_kd_books"], "argv": ["scripts/run_cb9.py", "kd-seal", "--rps", "2"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch9/kd/holdout_SEAL.json"], "next_action": "commit the seal copy; q0188", "notes": "DRAFT. Sealed files never edited; drops recorded as DROPPED_* blocks."}
{"id": "q0188_cb9_sign_audit_B", "title": "CB9-S: S0b 1,000 SCREEN K/D prints (<= 4 per market), receipts, T1/T2, fill type, pmxt last_trade_price feed side by tx hash", "family": "creative_batch_9", "priority": 38, "expected_value": "S0 pmxt-era stratum and the feed-side column", "data": ["creative_batch9/kd/screen prints", "public Polygon JSON-RPC receipts"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "polygon-rpc"}, "depends_on": ["q0187_cb9_kd_seal"], "argv": ["scripts/run_cb9.py", "sign-audit", "--strata", "b", "--rules", "../docs/research_lab/seals/cb9_sign_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "13"], "timeout_s": 3000, "max_retries": 2, "outputs": ["research_lab/creative_batch9/sign/s0b/{prints_classes.csv.gz,manifest.json}"], "next_action": "q0189", "notes": "DRAFT. No HOLDOUT print is sampled."}
{"id": "q0189_cb9_census", "title": "CB9: pre-freeze census, counts only (S0 match/availability, GP, GK, GD, cell cut points from features only, MDEs)", "family": "creative_batch_9", "priority": 37, "expected_value": "gates and MDEs before the freeze", "data": ["creative_batch9/* (SCREEN only; HOLDOUT file and event counts)"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0181_cb9_sign_audit_A", "q0184_cb9_pyth_books", "q0187_cb9_kd_seal", "q0188_cb9_sign_audit_B"], "argv": ["scripts/run_cb9.py", "census"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/census.json", "trials.jsonl (cb9_descriptive)"], "next_action": "science-reviewer freeze check, then model_specs/cb9_v1.json", "notes": "DRAFT. Outcome guard; no agreement, net, contrast or mark-out computed."}
{"id": "q0190_cb9_screen_S0", "title": "CB9-S: S0 agreement per stratum, Wilson 99%, verdict (near-truth / minor noise / material noise)", "family": "creative_batch_9", "priority": 36, "expected_value": "methods verdict for every flow result", "data": ["creative_batch9/sign/*"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0189_cb9_census"], "argv": ["scripts/run_cb9.py", "screen", "--family", "S0"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_S0.json", "trials.jsonl (cb9_test + creative_batch_9:S)"], "next_action": "material noise: commit q0193/q0194; else none", "notes": "DRAFT. Refuses before the CB9 freeze hash."}
{"id": "q0191_cb9_screen_P", "title": "CB9-P: P1 and P2 Stage 1 with placebos and binding robustness", "family": "creative_batch_9", "priority": 36, "expected_value": "P verdicts", "data": ["creative_batch9/pyth*/ (guarded files opened here only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0189_cb9_census"], "argv": ["scripts/run_cb9.py", "screen", "--family", "P"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_P.json", "trials.jsonl (cb9_test + creative_batch_9:P)"], "next_action": "advanced: commit q0195", "notes": "DRAFT."}
{"id": "q0192_cb9_screen_KD", "title": "CB9-K/D: K1 and D1 Stage 1 on SCREEN events with placebos and binding robustness", "family": "creative_batch_9", "priority": 36, "expected_value": "K and D verdicts", "data": ["creative_batch9/kd/screen/"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0189_cb9_census"], "argv": ["scripts/run_cb9.py", "screen", "--family", "KD"], "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_KD.json", "trials.jsonl (cb9_test + creative_batch_9:K, :D)"], "next_action": "advanced: commit q0197", "notes": "DRAFT. Refuses to open holdout/."}
{"id": "q0193_cb9_sign_fetch_h10", "title": "CB9-S1: h10_sign fetch (1,200 markets, one seeded 72-h window each in the triggered era before 2026-10-01; all taker prints; receipts up to 20,000 prints, whole windows)", "family": "creative_batch_9", "priority": 36, "expected_value": "S1 data (conditional)", "data": ["public Gamma, Data API", "public Polygon JSON-RPC", "creative_batch9/exclusion_keys.csv.gz"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "net", "network": "gamma-api, data-api, polygon-rpc"}, "depends_on": ["q0190_cb9_screen_S0"], "argv": ["scripts/run_cb9.py", "sign-fetch", "--rps", "2", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "13", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h10_sign/{sample.csv.gz,prints/,receipts_classes.csv.gz,manifest.json}"], "next_action": "q0194", "notes": "DRAFT. Commit only on the S0 'material noise' verdict.", "repeat": {"max_runs": 4, "until_log_regex": "\"status\": \"sign_fetch_complete\""}}
{"id": "q0194_cb9_screen_S1", "title": "CB9-S1: ratio of on-chain-signed to API-signed 6h flow slope on identical units", "family": "creative_batch_9", "priority": 36, "expected_value": "re-scaled flow ceiling", "data": ["history/h10_sign/"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0193_cb9_sign_fetch_h10"], "argv": ["scripts/run_cb9.py", "screen", "--family", "S1"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_S1.json", "trials.jsonl (cb9_test)"], "next_action": "methods note M4", "notes": "DRAFT."}
{"id": "q0195_cb9_pyth_live", "title": "CB9-P Stage 2: 30 full sessions from T9_P2_start; CLOB /book of frame-rule markets at each checkpoint (receipt-timed); prints of quote windows and Yahoo hourly bars after each session", "family": "creative_batch_9", "priority": 44, "expected_value": "out-of-time P replication data", "data": ["public Gamma, CLOB /book, Data API, Yahoo"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, data-api, yahoo"}, "depends_on": ["q0191_cb9_screen_P"], "argv": ["scripts/run_cb9.py", "pyth-live", "--sessions", "30", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "13"], "timeout_s": 3000, "max_retries": 3, "outputs": ["research_lab/creative_batch9/pyth_live/<session>/..."], "next_action": "q0196 after T9_P2_end + 2 d", "notes": "DRAFT. Only if P1 or P2 advanced. Checkpoints in ET (EST after 2026-11-01)."}
{"id": "q0196_cb9_rep_P", "title": "CB9-P: P1-rep and P2-rep on post-freeze sessions", "family": "creative_batch_9", "priority": 36, "expected_value": "L2 verdict", "data": ["creative_batch9/pyth_live/"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0195_cb9_pyth_live"], "argv": ["scripts/run_cb9.py", "rep", "--family", "P"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_P_rep.json", "trials.jsonl (cb9_replication)"], "next_action": "pass: Stage P-P registration draft", "notes": "DRAFT."}
{"id": "q0197_cb9_rep_KD", "title": "CB9-K/D: K1-rep and/or D1-rep on sealed HOLDOUT events", "family": "creative_batch_9", "priority": 36, "expected_value": "L2 verdict", "data": ["creative_batch9/kd/holdout/"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0192_cb9_screen_KD"], "argv": ["scripts/run_cb9.py", "rep", "--family", "KD"], "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_KD_rep.json", "trials.jsonl (cb9_replication)"], "next_action": "pass: Stage P-K/P-D drafts", "notes": "DRAFT. Only for advanced tests; verifies the seal hash first."}
{"id": "q0198_cb9_halfday_poll", "title": "CB9-P descriptive: 2026-11-27 and 2026-12-24 half sessions, books every minute 13:05-16:00 ET for frame-rule markets; Yahoo 1-minute bars after the close; uncounted", "family": "creative_batch_9", "priority": 45, "expected_value": "CH83c descriptive", "data": ["public Gamma, CLOB /book, Yahoo"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, yahoo"}, "depends_on": [], "argv": ["scripts/run_cb9.py", "halfday-poll", "--days", "2026-11-27,2026-12-24", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "13"], "timeout_s": 12600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/halfday/<day>/..."], "next_action": "report as cb9_descriptive", "notes": "DRAFT. Rules hash committed before 2026-11-27."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb9_sign.py`: keyless RPC client (endpoint list, ≤ 2 rps, fallback), receipt decoder
  for v1 and v2 topics, match rule, T1/T2, fill types, sample frames; a local keccak helper or a pinned topic table.
- `cb9_pyth.py`: frame regexes and text flags, Yahoo bar fetch and usable-at rule, σ, model value, P1 units, P2 quotes
  (reusing `cb3_maker.quote_fills`), guarded files.
- `cb9_kd.py`: frame and split, pmxt row-group streaming reader (reusing `cb8_books`), K features, cells, skew, quotes,
  marks; D dust states and units.
- `backend/scripts/run_cb9.py` with subcommands as §4; refused-roots list; disk and ingress guards; exit 75 on headroom.
- Tests (`test_cb9_sign.py`, `test_cb9_pyth.py`, `test_cb9_kd.py`, `test_run_cb9.py`): topic hashes against the
  pinned values; decoder on fixture receipts of both eras (constructed, not live); T1 = T2 on fixtures; match ambiguity;
  model value and usable-at rule; no census path receives a target; guarded-file access only in screen jobs; holdout
  refusal; HMAC strict loader; `battery2` kinds.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| S0 | 1 | `cb9_test` + `creative_batch_9:S` | decision bands (§CB9-S), not Holm |
| Stage 1: P1, P2, K1, D1 | 4 | `cb9_test` + `:P` (2), `:K`, `:D` | p < 0.01 each; batch-Holm label (α 0.01, k1 4); BY triage |
| S1 (conditional) | ≤ 1 | `cb9_test` + `:S` | `R̂ ≥ 1.5`, p < 0.01 |
| Stage 2: P1-rep, P2-rep, K1-rep, D1-rep | ≤ 4 | `cb9_replication` | one Holm, one-sided α 0.05 |
| Census, gates, descriptives, feed-side, strike stratum, half days | 0 | `cb9_descriptive` | - |
| **Total** | **5 fixed + ≤ 5 conditional = 5-10** | | cumulative ≥ 1,131 at drafting → ≥ 1,136-1,141 plus CB6-CB8 |

**Host compute.** About 4-6 CPU-hours at nice 19; peak RAM 1.5 GB (pmxt readers, K/D screen).
**Network.** Before `T_seal`: about 2,800 requests on the `cpu` lane. After: about 21,000 API requests, about 1,000-21,000
receipts, ≤ 130 GB pmxt ingress (two capped jobs, serial). **Disk.** ≤ 0.3 GB.

## 7. Main scientific risks

1. **S0 is probably "near-truth".** The v2 exchange logs the side explicitly and the Data API probably indexes those
   logs; S0 then closes CH79 cheaply. The informative residue is the pmxt feed column (Dubach's object) and the v1 era
   (S0c), where the side is derived from asset ids and complementary fills are common.
2. **Match rule failures.** Operator batching, proxy versus signer addresses or multi-order transactions can push the
   match rate under 90% (GS fail, "not testable (source)"), which is a data answer, not a null.
3. **P's anchor is coarse and not the settlement source.** Yahoo hourly bars and the official close stand in for Pyth's
   minute candles (the Pyth path is keyed, probe 6). Real bots use real-time feeds; an hourly anchor can only find large
   mispricings (MDE 7-10c). The Yahoo endpoint is unofficial; a smoke or frame failure makes P "not testable (source)".
4. **Day dependence in P.** Equity dailies share a market factor; about 78 sessions are the effective sample. The
   comonotone break-even placebo guards p-values; a pass with few days is still fragile.
5. **K's fill realism and decay.** One hourly-resolution origin per day, queue position uncertain (binding trade-through
   bracket), and F4/F5 decayed to 40-55% in HB2-R's post-split half. The per-filled-share contrast can be driven by fill
   selection; the skew-sign placebo is the guard.
6. **D is partly mechanical.** A market order sweeps dust by construction; D1's value is the size and frequency of the
   correction, labelled methods.
7. **Queue and disk.** Data-dumps is 12 GB against a 13 GB guard; CB9 data jobs may wait on archive rotation. CB9's
   pmxt jobs (≤ 130 GB ingress) queue behind CB4 and CB8 pmxt work; the K/D screen may slip beyond a week (no rule
   changes; dates are fixed by events, not by deadlines).
8. **Forking across families.** S0's verdict changes how K is labelled, not how K is computed (frozen sides from the
   Data API); no family's rule depends on another family's outcome.

## 8. Next actions

1. **Challenger review** (`science-reviewer`, one round, one response) of this draft: the S0 decision bands, the match
   and truth rules, the Yahoo anchor substitution, K's per-filled-share primary and cells, D's mechanical component, the
   counting.
2. Write `seals/cb9_sign_rules.json` (pins re-verified from Polymarket's contracts list and the v2 source for the side
   enum mapping), smoke code, `cb9_sign.py` and tests; commit q0180, then q0181 on the `cpu` lane before `T_seal`.
3. After `T_seal` and CB8's q0164/q0166/q0168: `seals/cb9_rules.json`, P/K/D code and tests, freeze check, q0182-q0188.
4. Census q0189 → freeze `model_specs/cb9_v1.json` → q0190-q0192 → conditional jobs by the stated triggers.
5. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.
