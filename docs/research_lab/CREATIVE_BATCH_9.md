# Creative batch 9 (CB9): trade-direction truth, hourly-anchored Pyth dailies, flow-skewed maker, dust midpoint

`evidence_role: methods` (CB9-S, CB9-D) / `exploratory_historical` (CB9-P Stage 1, CB9-K on pmxt books 2026-04-13 to
08-10) / `prospective` (CB9-P Stage 2, post-freeze sessions) | status: **DRAFT-REVISED after challenger round 1; not
frozen; next: code, then code-against-design freeze check.** Drafted 2026-10-17 11:05 UTC+1 (2026-10-17T10:05Z) by the
CB9 design pass (`00dd145`); round-1 response 2026-10-17 (§9-§10). Every round-1 change tightens or discloses; no floor,
threshold or gate was relaxed. Nothing has been fetched for CB9 beyond the 45 counts-only feasibility requests in §0.3.
No CB9 quantity has been computed.

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
  and CB8's post-`T_seal` jobs keep priority. Before `T_seal` only q0180 (smoke, about 80 requests, `cpu` lane, ≤ 1 rps)
  may run. **q0181 (audit stage A, about 2,700 requests) moved to the `net` lane after `T_seal`** (round 1, should-change:
  `history_backfill.Limiter` paces per process only, so a `cpu`-lane fetch would add to a `net`-lane job's rate; §2.8).
- **Queue ids q0180-q0199, one id per job, no letter suffixes** (checked free in `queue/jobs/` and `queue/drafts/` at
  drafting; q0177-q0179 stay reserved for CB8). Specs are drafts **in this document only** (§4); no file is created
  under `queue/` until code, tests and the freeze check exist.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB9-S** trade-direction truth (CH79) | the Data API `side` of a taker print disagrees with the on-chain taker side often enough (agreement `q` < 0.90) to attenuate every AREPO flow coefficient; if so, the on-chain-signed flow slope is ≥ 1.5x the feed-signed slope (S1) | S0 (measurement, fixed); S1 (conditional on S0) | fresh print samples + public Polygon receipts (Oct 2026, Feb-Apr 2026, May-Aug 2026) | none (methods; S1 is single-stage, ceiling L1) | q0180-q0182, q0188, q0190, q0193, q0194 |
| 2 | **CB9-P** hourly-anchored Pyth equity dailies (CH83a + CH84, merged and narrowed) | in Pyth-settled equity "Up or Down" dailies, a frozen lognormal digital anchored on the last public hourly bar (a) identifies asks that pay after fees when held to settlement (P1, taker), and (b) a maker quoting around that anchor beats the same maker quoting around the book mid (P2) | P1 (economic), P2 (economic contrast) | pmxt books, all usable sessions 2026-04-13..08-10 | prospective post-freeze sessions (30) | q0183, q0184, q0191, q0195, q0196, q0198 |
| 3 | **CB9-K** flow-skewed maker in the F4/F5 cells (CH92) | in the replicated high-volatility / wide-spread cells, a touch maker skewed one tick in the direction of the frozen 6h flow feature earns more per filled share at a 6h mark than the unskewed maker (K1) | K1 (economic contrast, with route gate) | pmxt books (14Z origins) + Data API prints, SCREEN events | the same fetch, sealed HOLDOUT events | q0185-q0187, q0189, q0192, q0197 |
| 4 | **CB9-D** dust-anchored midpoint (CH80, route 1 only) | when a best level is dust (< 5 shares, `orderMinSize`; round 1), the next transaction's VWAP lies closer to the size-cutoff mid than to the displayed mid (D1); methods consequence for every mid-based target | D1 (methods mechanism) | the K pmxt hours (same markets, no extra ingress), SCREEN events | sealed HOLDOUT events | shares q0185-q0187, q0189, q0192, q0197 |
| - | CB9-F data | smoke, exclusion keys, frames, books, prints, receipts, seals | none | | | q0180-q0189, q0193, q0195, q0198 |

**Counted: 5 fixed (S0, P1, P2, K1, D1) + up to 5 conditional (S1, P1-rep, P2-rep, K1-rep, D1-rep) = 5-10** (§2.5).

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0180 | `cb9_smoke` (counts only: RPC endpoints and topic pins on 20 receipts per exchange era; Yahoo hourly bar shape out of window; Pyth frame paging; pmxt HEADs) | F | after smoke code and `seals/cb9_sign_rules.json` exist (cpu lane; may run before `T_seal`) |
| q0181 | `cb9_sign_audit_A` (S0 strata a and c: fresh print samples, receipts, per-print classes; **no agreement computed**) | S | after the q0180 PASS and after `T_seal` (`net` lane; round 1) |
| q0182 | `cb9_exclusion_keys` (CB8 q0164 keys plus every seal copy committed since: h7_cb4_*, h8_*, h9_flow, CB8 updown frame and holdout listing, CB8 holders frame) | F | after `T_seal`, q0164, q0166, q0168 |
| q0183 | `cb9_pyth_frame` (Gamma frame of Pyth equity Up/Down dailies; rule-text flags; Yahoo hourly and daily bars; outcomes to the guarded file) | P | after q0182 |
| q0184 | `cb9_pyth_books` (pmxt states at the three checkpoints; Data API prints in the 5-minute quote windows) | P | after q0183 |
| q0185 | `cb9_kd_frame` (Gamma frame for K/D, key drops, seeded event split SCREEN/HOLDOUT, sample of 1,000 markets) | K, D | after q0182 |
| q0186 | `cb9_kd_books` (pmxt hour 14Z of every window day for the K/D markets; book events kept for D; prints `[t − 6 h, t + 7 h]`; HOLDOUT written sealed) | K, D | after q0185 |
| q0187 | `cb9_kd_seal` (HOLDOUT listing sha256, seal copy) | K, D | after q0186 |
| q0188 | `cb9_sign_audit_B` (S0 stratum b: 1,000 SCREEN K/D prints, receipts, pmxt feed side by tx hash) | S | after q0187 |
| q0189 | `cb9_census` (counts only, all families; MDEs; gates GP, GK, GD, S0 match counts; pmxt coverage audits) | all | after q0181, q0184, q0187, q0188 |
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
- `battery2.cumulative_count()` on the Mac working tree (`battery2-count-v1`) = **1,131** at 2026-10-17T10:00Z. This
  is the count (§2.5). The 1,106 in the ledger is an old CB1-D note written at that time, not a competing count (round
  1). Commit `e5cfb3a` made the `design_change` trial kind count 0 (EXCLUDE), so `cumulative_count()` no longer fails
  closed on the CB6 A-T1 line; 1,131 is the value after that fix.
- Host state (`scripts/oracle/queue_status.sh`, read only, 2026-10-17T09:52Z): `/` 36 GB, 8.7 GB free; data-dumps
  **12.5 GB**; MemAvailable about 4.1 GB; running q0084 (CB4 pmxt pilot) and q0102 (CB5); h7 fetches q0081/q0082 queued for
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
| Data API taker prints, **S0a**: 250 markets, `[2026-10-01, 2026-10-15)` (**new**, q0181) | none | S0 stratum a (current exchange era; informs **E007**) | methods |
| Data API taker prints, **S0c**: 250 markets, `[2026-02-01, 2026-04-27)` (**new**, q0181; v1 exchange era) | none | S0 stratum c (informs **no existing result**; a v1-era measurement for later designs) | methods |
| Public Polygon receipts (`eth_getTransactionReceipt`, keyless, endpoint list pinned) for S0 and S1 prints (**new**) | none (CB6-N plans logs, not receipts) | on-chain truth side | - |
| pmxt v2 hour 14Z of every window day, range reads by the K/D condition ids (**new**, q0186) | ECONOMIC_CONDITIONS B, r4_book, J3, CB1-C, CB4-N, CB8-B (other markets) | K Stage 1 (SCREEN events) and Stage 2 (HOLDOUT, sealed); D the same; S0b's pmxt feed side (S0b informs **HB1, HB2 and K**) | L1 / L2 (sealed holdout) |
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
- **Yahoo bars (pinned, round 1 item 1).** A Yahoo hourly row's `timestamp` is the **bar start** `o`. Its end is
  `e = min(o + 60 min, 16:00 ET)` (13:00 ET on half sessions). Rows with `o < 09:30 ET` or `o ≥ 16:00 ET` are dropped, and so
  are zero-length or closing rows (`e ≤ o`, or a row stamped at 16:00 ET). A full session has exactly **7** regular bars:
  09:30, 10:30, ..., 14:30 (60 min each) and 15:30 (30 min). A session with any other count after the drop is
  "bars unavailable" for that ticker-day, counted, never repaired. The probe's 8 rows were 7 bars plus such a row. A bar
  `[o, e)` is usable at `t` iff `e + 120 s ≤ t`. So the 10:32 checkpoint uses the 09:30 bar, 12:32 uses 11:30, and 15:32 uses
  14:30. A daily close of day `d − 1` is usable from `d 00:00Z`.
- **Bars in Stage 2.** q0195 fetches Yahoo at each checkpoint and records the receipt time. `S_t` is the latest bar in
  that response that is usable at the receipt time. Bars fetched after the session are **diagnostic only** (a
  bar-revision count) and never enter a feature.
- **Receipts.** Block timestamp is diagnostic only; S matches by transaction hash, never by time.
- `closedTime` is never a population condition or an anchor.

### 2.3 Uncertainty and decision rule

As CB8 §2.3 (unweighted primary; one-sided p = max over declared cluster ways; 2,000-draw cluster bootstrap, seed 919;
small-G rule; A-C1 day way; top-5 drops of events and of days; ≥ 100 units and ≥ 30 clusters for testability; "unknown"
never counts as met). Cluster ways: **P** UTC session day and market (ticker); **K** Gamma event and UTC day; **D**
market x day and UTC day; **S** market (S0) and Gamma event (S1). The P ticker way has about 18 clusters, so it always runs under
the small-G rule (15 ≤ G < 30: CR2 with t(G − 1) and the wild-cluster bootstrap, the larger p; G < 15: not testable, p = 1) (M12).

- **S0** is a measurement with a pre-stated decision rule (§CB9-S); it is counted but not in the Holm family.
- **Stage 1 (P1, P2, K1, D1; S1 if run).** Advance iff one-sided p < 0.01, the §2.4 floor is met, and every binding
  placebo, robustness check and gate holds. A batch-Holm label (one-sided α = 0.01, **k1 = 5 whatever S0's verdict**;
  round 1 should-change: S1 holds its slot even when it is not run, so k1 never depends on a CB9 result) is reported.
  A BY label (q = 0.10 over `battery2.cumulative_count()` at the run) is triage only.
- **Stage 2 (P1-rep, P2-rep, K1-rep, D1-rep).** One Holm at one-sided α = 0.05 over all CB9 tests reaching Stage 2, each
  in its Stage-1 direction; k fixed when the last Stage-1 result is final; early finishers judged at α/k. Labels: K1-rep,
  D1-rep "sealed same-calendar holdout replication (L2)"; P1-rep, P2-rep "out-of-time replication on post-freeze sessions
  (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| S0 | measurement | decision bands (§CB9-S): near-truth `q̂ ≥ 0.97`; material noise `q̂ < 0.90` |
| S1 | methods | ratio `R̂ ≥ 1.5` **and** the event-cluster bootstrap one-sided 99% lower bound of `R` > 1.5 (round 1 item 4) |
| P1 | economic | net ≥ +1.0c per share after fee |
| P2 | economic contrast | model-centred minus mid-centred ≥ +0.3c per posted share; route gate: model-centred net per posted share > 0 |
| K1 | economic contrast | skewed minus unskewed ≥ +0.5c per filled share; route gate: skewed net per filled share > 0 **and** skewed net per origin (per 100 posted shares) > 0 (round 1 item 5) |
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
- **D1 next-print shuffle calibration (binding).** Within each market x day, next-transaction VWAPs (§CB9-D) are
  permuted across dust units (J4-R increment-shuffle analogue). *Alternative:* within-day level drift makes either mid
  "closer" by chance.

**Binding robustness for any advance or pass:** (i) the §2.1 cost robustness keeps the sign and ≥ half the magnitude
(P1 keeps net > 0); (ii) p threshold and floor hold without the top 5 clusters of each way; (iii) unweighted and
size-weighted estimates agree in sign (P1 by ask depth capped at 2,000 shares; K1 by filled shares; D1 by next-transaction
size); (iv) sign by month in ≥ two thirds of months with ≥ 30 units (P), ≥ 300 fills (K), ≥ 500 units (D); (v) the
declared worst case for unavailable units keeps the sign and p threshold (P: unavailable checkpoints scored as the
worst observed unit of that day; K: unavailable marks scored at −1 tick per filled share; D: units without a next transaction
excluded, counted); (vi) latency: P units and quotes start at bar end + 300 s instead of + 120 s; K fills only from
`t + 60 s`; each keeps the sign and ≥ half the magnitude.

### 2.7 Pre-freeze census (counts only; q0189)

Outcome guard first; field-restricted accessors; a unit test asserts that no census path receives a target, mark, fill
price or truth side. **No agreement, net, contrast or mark-out is computed.**
- **S0.** Prints sampled, receipts fetched, receipt failures by endpoint, matched-exactly-once share, T1/T2 availability
  (not agreement), fill-type counts, era counts, matched markets per stratum. **Gate GS (per stratum):** match rate ≥
  90% and ≥ 300 matched prints in that stratum. A stratum failing GS is "not testable (source)", and the results it
  informs (§CB9-S era map) stay **"unverified"**. It never takes another stratum's verdict (round 1 item 3).
- **P.** Frame counts by ticker; rule-text failures; key drops; sessions lost to pmxt gaps or Yahoo gaps; eligible
  checkpoints; units with model edge ≥ 5c on either side (a feature-only count: model value and ask, no outcome);
  quote-origins; print counts in quote windows; the P pmxt coverage audit (below). **Gate GP:** ≥ 300 P1 units, ≥ 40
  session days, ≥ 15 tickers; ≥ 1,500 P2 quote-origins with ≥ 100 fills of either quote. Fail → the test is "not
  testable", counted, labelled as for K/D below.
- **K.** Frame, key drops, SCREEN/HOLDOUT market and event counts; origins with a two-sided fresh book; the F4/F5 cell
  cut points computed **from feature values only** on SCREEN origins (frozen in the census output); origins in the
  cell; origins passing the median-`|x6|` skew cut; quote fills by rule (count only); marks available; the K/D pmxt
  coverage audit (below). **Gate GK, counted after the skew cut** (on the units that enter K1; round 1 item 5): ≥ 2,000
  cell origins, ≥ 300 filled origins of each quote type, ≥ 60 events, ≥ 30 days. All SCREEN only. Disclosed: the §CB9-K
  assumptions give about 1,650 cell origins after the cut, so **GK may fail**. The gate is not lowered; a fail is "not
  testable", counted.
- **D.** Two-sided market-minutes; dust-state share (share rule, §CB9-D); dust units with a next transaction within 10
  minutes. **Gate GD:** dust share ≥ 5% of two-sided market-minutes and ≥ 1,000 dust units in ≥ 100 market-days. Fail
  → D1 "not testable (no dust state)", counted, under the label rule below. *Disclosed (round 1):* CH80's kill 1 was
  stated on market-**hours**; GD uses market-**minutes**, the D1 unit. The minute share is never larger than the share
  of market-hours with any dust minute, so GD is the stricter of the two. The hour share is reported.
- **pmxt coverage audits (round 1 should-change; CB8 §CB8-B audit adopted, counts only, no extra ingress).** For P, the
  audit takes every (market, quote window) with ≥ 1 Data API print in the window. For K/D, it takes every (market, day)
  with ≥ 1 Data API print in `[14:00Z, 15:00Z)`. It then counts whether pmxt shows any event for that condition id in
  the same span. **PASS iff ≥ 90%** for each of P and K/D. Conditioning on a print (a print always makes a
  `last_trade_price` event) keeps a quiet market from reading as missing coverage. This is a deviation from CB8's
  separate 13Z hour; it reads no new hours. Labels, kept distinct and counted:
  - audit FAIL → that family "not testable (source unavailable)";
  - a unit whose span had a print but no pmxt event → **"source unavailable"**, never "no trade" and never "stale";
  - a unit with neither a print nor a fresh book → "no fresh book";
  - a GP, GK or GD fail reads "no opportunity" (P: "no mispricing at the hourly scale"; K: "too few cell fills"; D:
    "dust is rare") only if the audit passed **and** ≥ 80% of SCREEN units are source-available. Otherwise it reads
    "not testable (source unavailable)".
- MDEs are recomputed from these counts and are never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collector. Queue rules as CB8 §2.8 (one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 x `mem_mb`, 02:45-05:30 UTC blackout for `mem_mb ≥ 500`, exit 75 on
  headroom). Never two multi-GB jobs at once. pmxt jobs read **one row group at a time with column projection** and
  never materialise an hour file (the q0084 MemoryError lesson); peak RAM ≤ 1.5 GB.
- **Before `T_seal`.** Only q0180 (about 80 requests: about 40 receipts, about 20 Data API and Gamma, 2 Yahoo, a few
  pmxt HEADs; `cpu` lane at ≤ 1 rps, under 3 min). **Nothing CB9 enters the `net` lane before 2026-10-22.**
- **Rate limiter (round 1 should-change, checked in code).** `history_backfill.Limiter` paces requests **within one
  process** only (an in-memory last-request clock). It yields to the live collector through `live_pass_or_lock()`
  (collector flock or pass command line), but it is **not shared** with other queue jobs. A `cpu`-lane fetch would
  therefore add its rate to a `net`-lane job hitting the same host. So:
  - **q0181** (about 2,700 requests: about 500 Data API, about 100 Gamma, about 2,000 receipts; about 25 min at ≤ 2
    rps, mem ≤ 300 MB) moves to the **`net` lane after `T_seal`**. There it never runs concurrently with another
    `net`-lane fetch.
  - **q0180** stays on the `cpu` lane. It sends at most about 20 Data API/Gamma requests at ≤ 1 rps and uses the
    collector yield, so its worst-case overlap with a `net`-lane job is that job's rate + 1 rps for under a minute
    (disclosed).
  - **q0195 and q0198** (prospective P, `cpu` lane) hit the Data API, Gamma and CLOB at checkpoint times and cannot wait
    for the lane. They run at ≤ 1 rps with the collector yield, and the combined rate is disclosed in their manifests (each
    records any `net`-lane job running during its requests).
  - Polygon RPC (receipts) is used by no other AREPO job.
- **After `T_seal`** (`net` lane, priorities 36-43, behind CB7 q0146, CB4 pmxt jobs and CB8 q0161-q0167):

  | Job | Work | Ingress / wall | Stored |
  |---|---|---|---|
  | q0181 | S0a/S0c samples + receipts (moved from `cpu`, round 1) | about 600 Data API/Gamma + about 2,000 receipts | ≤ 0.01 GB |
  | q0182 | exclusion keys | about 400 Gamma requests | ≤ 0.01 GB |
  | q0183 | P frame + bars | about 300 Gamma + about 50 Yahoo requests | ≤ 0.01 GB |
  | q0184 | P books + prints | pmxt about 234 hours x ≤ 25 condition ids (≤ 24% of row groups) **ingress cap 40 GB**; about 4,700 print requests; about 1.5-2.5 h | ≤ 0.02 GB |
  | q0185 | K/D frame | about 1,200 Gamma requests | ≤ 0.01 GB |
  | q0186 | K/D books + prints | pmxt hour 14Z of about 111 days, all row groups touched (markets spread across the sort key), 13Z lookback only for tokens with no 14Z event: **ingress cap 180 GB** (M8; was 90), days in seeded order so a cap truncates evenly (unprocessed days unavailable, counted); about 12,000 print requests at ≤ 4 rps; about 3-5 h in 85-min chunks; mem ≤ 1.5 GB | ≤ 0.15 GB |
  | q0188 | S0b receipts | about 1,000 receipts | ≤ 0.01 GB |
  | q0193 | S1 (conditional) | about 1,300 Gamma + about 2,500 print requests + ≤ 20,000 receipts (about 3 h at 2 rps) | ≤ 0.05 GB |
  | q0195 | P Stage 2 (conditional) | about 150 requests per session x 30 sessions, `cpu` lane | ≤ 0.01 GB |
  | q0198 | half-day poll | about 3,500 requests per half day, `cpu` lane | ≤ 0.01 GB |

- **Disk guard (amended 2026-10-17 after the freeze check; M6, then the enlarged host disk).** Every CB9 data job exits 75 when
  data-dumps + its output cap > **40 GB** (`--data-dumps-cap-gb 40`, the code default; was 14 under M6). Host: boot volume 100 GB
  (root 89 GB, about 60 GB free), collector cap 45 GiB; the 4 GB free-disk guards are unchanged. The precondition never changes retention.
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

**Era map (pre-stated, round 1 item 3).** Each stratum informs only the results from its own era:

| Stratum | Era | Informs |
|---|---|---|
| S0a | v2 exchange, `[2026-10-01, 10-15)` | **E007** |
| S0b | v2 exchange, pmxt window May-Aug 2026 | **HB1, HB2 (incl. HB2-R F4/F5) and CB9-K** |
| S0c | v1 exchange, `[2026-02-01, 04-27)` | **no existing result** (v1-era measurement for later designs) |

Disclosed: the HB window starts 2026-04-13, so its first two weeks are v1-era. S0c covers that exchange era but not
that calendar, so it is not read across to HB1/HB2.

**Statistic and decision rule (S0, per stratum).** `q̂` = share of matched prints with `A_yes = 1`. **Lower bound
`q_LB` (round 1 item 3: market-cluster, not print-level):** the 0.5th percentile of a 2,000-draw market-cluster
bootstrap (seed 919; markets resampled with their up to 4 prints). Because a bootstrap of an all-agree sample is
degenerate at 1, `q_LB` is the **minimum** of that percentile and a Wilson 99% lower bound computed on **markets**
(`n` = matched markets, successes = `n·q̂`). The print-level Wilson interval is reported only. Each stratum that passes
GS gets its own verdict. A stratum failing GS is "not testable (source)", and its mapped results are **"unverified"**.
No stratum ever takes another stratum's verdict.

| Verdict (per stratum passing GS) | Condition | Consequence for that stratum's mapped results |
|---|---|---|
| **near-truth** | `q̂ ≥ 0.97` and `q_LB ≥ 0.95` | CH79's attenuation route closed for that era. **Narrowed (round 1):** the Data API `side` field is accurate in that era. S0 does **not** audit AREPO's own signing code (the side-to-YES mapping in `history_backfill`/h2 and their stored rows), so this says nothing about a coding error there. S1 is not run for that era |
| **minor noise** | otherwise, with `q̂ ≥ 0.90` and `q_wc ≥ 0.85` | ceiling re-scaling ≤ `1/(2·0.90 − 1)` = 1.25x, too small to make a taker flow route material (it needs about 5x, CH79); methods note only; S1 not run for that era. If `q̂ ≥ 0.97` but `q_LB < 0.95` only because there are few matched markets, the label is "minor noise or better (bound limited by n)" |
| **material noise** | `q̂ < 0.90` or `q_wc < 0.85` | methods note M4 for that era's results (ceilings re-stated by `1/(2q̂ − 1)` as an upper bound under symmetric noise, labelled as such); S1 runs for that era |

`q_wc` scores unmatched prints as disagreements. A pooled `q̂` over the strata passing GS is reported as a descriptive
figure only; it carries no verdict. Also reported: `q̂` by liquidity tercile, price band, fill type and sports stratum;
**notional-weighted agreement** (prints weighted by `size × price`, round 1 should-change); `A_tok`; the feed-side
agreement in S0b; and the share of disagreements that are mint/merge fills.

**S1 (conditional): does on-chain signing raise the flow slope?**
- Data `h10_sign` (q0193): 1,200 markets, one seeded 72-h window each in the material-noise era within `[2026-05-01,
  2026-10-01)` (or `[02-01, 04-27)` if only S0c triggered), all taker prints. Receipts are fetched for every print in
  windows taken whole in seeded order, until 20,000 prints (whole windows only). **Disjointness (round 1 item 4):** the
  markets are disjoint by the q0182 keys (event, `negRiskMarketID`, series) from h9_flow and every other sealed or worn
  run, **and from every CB9 market**: the K/D frame (SCREEN **and** HOLDOUT), the P frame (all Pyth markets), and the
  S0a/S0b/S0c samples. The frames exist before q0193 (q0183, q0185 and q0187 precede it).
- Units: 2h grid origins with ≥ 3 prints in `[t − 6 h, t)`. `x_api`, `x_chain` = 6h notional imbalance in YES terms,
  clipped to [−1, 1], **raw (no SD scaling)**, computed on identical prints; `d_6h` = last print price (YES terms) before
  `t + 6 h` minus last print before `t`, each within 30 minutes of its anchor, else unavailable.
- Statistic `R = β_chain / β_api` from two OLS fits `d = α + β x` on identical units; 2,000-draw event-clustered
  bootstrap of the ratio (seed 919). A draw with `β_api ≤ 0` counts as `R ≤ 1.5`. **S1 passes (restored, round 1
  item 4; the source idea's kill rule "ratio CI includes 1.5")** iff `R̂ ≥ 1.5` **and** the one-sided 99% lower bound
  (1st percentile of the draws) is > 1.5. Equivalently, p = bootstrap share of `R ≤ 1.5` < 0.01. The share of `R ≤ 1`
  is reported. `β_chain` is reported in cents per unit flow at 6h (an economic reading against the 1.8c liquid round
  trip, not a route test).
- **MDE (assumption; census replaces).** About 8,000 usable origins in about 900 events, `β_api` at about 4 SE (HB1 FL2
  scale), and paired-fit correlation ρ about 0.8. Then `SD(log R)` is about 0.17-0.19, and the lower bound clears 1.5
  only for **`R` about 2.4 or more**, i.e. symmetric-noise `q` ≲ 0.71. Stated plainly: S1 can pass only under strong
  attenuation. A material-noise `q` in 0.75-0.90 triggers S1, but S1 then reads "not detected at MDE `R` ≈ 2.4".

**Leakage.** None for S0 (no outcome, no price target). S1 uses prints before `t` for features, print prices only for
targets, fresh markets only; E007, HB1 and HB2 rows are never re-read.

**What kills CH79.** S0 near-truth or minor noise in every stratum passing GS (strata failing GS leave their results
"unverified", not killed); or S1 fails its pass rule (lower bound ≤ 1.5).

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

**Features (causal).** At checkpoint `t` (bar end + 120 s, bar clock pinned in §2.2): `S_t` = close of the latest
usable hourly bar; `K_d` =
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

**MDE (assumptions; census replaces; restated in round 1, item 7).** About 78 sessions x 18 markets x 3
checkpoints ≈ 4,200 checkpoints; perhaps 15-30% traded. The units are far from independent:
- the three checkpoints of a market-day share one outcome `Y`, so the effective unit is the market-day;
- equities share a market factor, so `Y` correlates across tickers within a day (assumed 0.3-0.5).

With per-share SD about 45c, about 10-15 traded market-days per traded session and about 60-78 traded sessions, the
day-mean SD is about 28-32c, and the day-clustered SE is about 3.3-4.5c. **P1 MDE is about 10-15c.** P2: about 4,000
quote-origins, but the model and mid quotes of an origin, and all origins of a market-day, settle on the same `Y`.
Clustered by day, the **P2 MDE is about 2-4c per posted share**. Both detect only large effects (CH83's claimed 5-15c
sits at or below the P1 MDE). Smaller real residuals are "not detected at MDE x".

**Stage 2 (registered only if P1 or P2 advanced).** For 30 full sessions from `T9_P2_start`, q0195 records:
- at each checkpoint, receipt-timed: the CLOB `/book` of every frame-rule market, and **a Yahoo hourly-bar fetch** (bar
  clock §2.2). `S_t` comes from that response;
- before 09:30 ET each session, a receipt-timed Yahoo fetch of the prior 20 sessions' hourly bars (for σ) and of the
  prior daily close (`K_d`);
- after the session: all prints of the quote windows, and the session's Yahoo bars again, **diagnostic only** (a bar-revision
  count; never a feature).

Definitions, model, thresholds, widths and gates are identical. CLOB books replace pmxt (receipt clock only;
disclosed).
- **Yahoo failing part-way (round 1 should-change).** A checkpoint whose Yahoo fetch fails after retries, or returns no
  usable bar by the checkpoint, is **"unavailable (source)"**, counted, and never filled. There is **no substitute
  source** (no other vendor, no post-session bar, no CLOB-implied value). A session whose σ/`K_d` fetch fails has all
  three checkpoints unavailable. Unavailable sessions **count toward the 30** (never replaced, collection never
  extended beyond `T9_P2_end`). If more than 20% of Stage-2 checkpoints are unavailable, P-rep is "not testable
  (source unavailable)", counted. The binding worst case (§2.6 (v)) scores unavailable checkpoints as the worst observed
  unit of that day.

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
6-h realised volatility of print prices on a 600 s grid (+1e-4), over the fetched `[t − 6 h, t)` prints (amended at the freeze
check, ruling (d); an analogue of h2's `ml_rv_1d`, not that variable); `SPR` = the pmxt touch spread
at `t`. Cell = `RV` ≥ its SCREEN top-tercile cut **or** `SPR` ≥ its top-tercile cut (cuts from feature values only, frozen
in the census). Skew direction `s = sign(x6)` where `|x6|` ≥ its SCREEN median (feature-only cut), else no skew (origin
excluded from K1, counted).

**Disclosures (round 1 should-changes).**
- **Same calendar as HB2.** K's window (2026-04-13..08-10) is HB2's calendar. Only the markets are disjoint (q0182
  keys). A K1 result is not out-of-time evidence for F4/F5, and a common-calendar regime would affect both.
- **RV and SPR are redefinitions, not F4/F5's variables.** F4 conditioned on h2's `ml_rv_1d` (from h2 price history)
  and F5 on the book-feature spread on the 6h grid. K uses print-based 1-day RV and the pmxt touch spread at `t`, with
  tercile cuts from K's own SCREEN origins. The cells are **analogues** of F4/F5. "F4/F5 moderation" credit (§2.6)
  means moderation in these analogue cells, not a replication of the HB2-R cells.
- **Fills and marks depend on the Data API side.** `x6`, the quote fills (taker side decides which quote a print
  fills) and the mark `M` (last taker-BUY and taker-SELL prices) all use the Data API `side`. S0b (the same era and the
  same markets' prints) measures that field. Under an S0b verdict of "material noise" or "unverified", K1 carries that
  label.

**Quotes (live `[t, t + 2 h]`, 50 shares each side).** Unskewed: bid at best bid, ask at best ask. Skewed (`s = +1`): bid
at best bid + 1 tick (if still < best ask, else best bid), ask at best ask + 1 tick; mirrored for `s = −1`. Fills by
`cb3_maker.quote_fills`, queue rule, complementary prints in YES terms. Mark `M` = midpoint of the last taker-BUY and last
taker-SELL print prices (YES terms) in `[t + 5 h, t + 7 h]`, both required, else the origin's fills are unavailable.
Mark-out per filled share: bid `M − p`, ask `p − M`.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **K1** | economic contrast | cell origin (SCREEN events; Stage 2: HOLDOUT events) | mean mark-out per filled share, skewed minus unskewed (fill-weighted within origin, origins equally weighted), cents | > 0 |

**Binding route gate (tightened, round 1 item 5).** At the point estimate, the skewed maker in the cell must have
**both** (a) mean mark-out per filled share > 0 **and** (b) mean net per origin > 0. In (b) each origin's total
mark-out P&L is divided by its 100 posted shares, unfilled quotes count 0, and origins are equally weighted, so a
skew that wins per fill but fills rarely cannot pass on (a) alone. Otherwise the label is "skew helps, but the maker
still loses: no route". If the unskewed maker alone is ≥ +0.5c with p < 0.01, the verdict is
"CB3-B's maker result; skew not needed" (CH92 kill 2), whatever K1.

**Fill realism.** Hourly-resolution queue position is uncertain (ECONOMIC_CONDITIONS part B). Binding: the
trade-through rule (fills only from prints strictly through the quote) keeps the sign and ≥ half the magnitude. The
fill rate of each quote type is reported; a quote never filled counts 0 shares (it does not enter per-filled-share means
but enters the per-posted-share version, reported).

**MDE (assumptions; restated in round 1, item 5; SCREEN units only, after the skew cut).** About 500 SCREEN
markets (about 150 events) x about 12 usable origin days ≈ 6,000 SCREEN origins. About 55% are in the cell (about
3,300), and about half pass the median-`|x6|` skew cut (about 1,650). With a fill rate of about 30% of origins per
quote type (either side), that is **about 500 filled origins per quote type**. Mark-out SD is about 4c per filled
share, and the two quote types' fill sets overlap only partly. The event-clustered contrast SE is about 0.3-0.4c, so the
**MDE is about 1c**, twice the 0.5c floor. K1 can detect only a contrast of about ≥ 1c. A real 0.5-1c contrast reads
"not detected at MDE 1c". The floor is unchanged. GK is counted after the cut (§2.7) and may fail at these numbers.
S0b's verdict labels K1: under "material noise" K1 is reported as "measured with noisy sides" (an attenuated test).

**Leakage.** Features from prints before `t`; cut points feature-only; marks from print prices after `t + 5 h`; the
skew is never re-tuned (one tick, frozen); HOLDOUT sealed. **Known decay:** F4/F5 fell to 40-55% in HB2-R's post-split
half; a null may be decay, not absence (reported).

**What kills CH92.** GK fails; K1 not detected at MDE; skew-sign placebo advances; cell attribution fails (labelled);
route gate fails; K1-rep fails on HOLDOUT.

### CB9-D: Dust-anchored midpoint (CH80, route 1)

**Question.** When a best level is dust, is the next transaction's price closer to the size-cutoff mid than to the
displayed mid, by how much, and how common is the state?

**Mechanism.** New orders need `orderMinSize` (5 shares) but partial fills leave smaller residuals; the displayed best
bid/ask ignores size, so the Gamma mid, `oneHourPriceChange` and AREPO's mid targets can be set by an order no one can
trade against. Reward scoring already uses a size-cutoff-adjusted mid (probe 8), so the reward route is closed; the
methods route remains.

**Units (K/D markets, pmxt hour 14Z, both tokens).** Market-minute ends `u ∈ [14:01Z, 15:00Z]` with a two-sided
fresh book.
- **Dust state (share rule primary, round 1 should-change).** A best bid or best ask level with size < the market's
  recorded `orderMinSize` (5 shares in every probed market; a market without the field is unavailable, counted). The
  draft's extra "< $1 notional" clause is **dropped from the primary**: it flagged legal 5-share orders below 0.20
  (5 x 0.19 = 0.95), so it would have counted ordinary low-price books as dust. The share-or-$1 version is reported
  as a variant.
- Displayed mid `m_d` = (best bid + best ask)/2. Size-cutoff mid `m_c` = the mid of the best bid and best ask among
  levels with size ≥ `orderMinSize` (unavailable if either side has none).
- **Next transaction `P` (pinned, round 1 item 6).** Take the Data API taker prints of the token (already fetched,
  `[t − 6 h, t + 7 h]`; each carries `transactionHash`). The next transaction is the first transaction hash with any
  print at `ts ≥ u + 1 s` and `ts ≤ u + 600 s` (the one-second step keeps a print from `u`'s own second out). `P` =
  the **size-weighted VWAP of all of that transaction's prints on the token**, aggregated by hash before any
  comparison. So a dust fill inside a sweep enters with its share weight and cannot decide the sign by itself. The
  transaction's last-fill price is a reported variant, never primary. No transaction in 10 minutes → unavailable,
  counted. `P` uses price, size, time and hash only, never `side`.
- One unit per market-minute; at most one unit per dust episode per 5 minutes (the first).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **D1** | methods mechanism | dust unit (SCREEN events; Stage 2: HOLDOUT events) | mean `|P − m_d| − |P − m_c|`, cents | > 0 |

**Reported (descriptive).** Dust share of two-sided market-minutes by liquidity tercile and price band; the share of
displayed-mid changes within the hour caused by a dust level appearing or disappearing; `|m_d − m_c|` distribution.

**MDE (assumption).** Thousands of dust units in hundreds of market-days; **MDE about 0.2c**; the floor (0.5c) binds.
The statistic is partly mechanical (a market order sweeps dust); its value is the size of the methods correction and
the state frequency, which is why D1 is labelled methods, not economic.

**What AREPO changes (pre-stated, round 1 item 6).**
- **D1 passes** (Stage 1 advance and D1-rep pass): methods note **M5**. Every later design with a mid-based target or
  feature (J4/J5 successors, E-series mid targets, Gamma-mid panels) must declare either the size-cutoff mid or a
  dust-state exclusion, with the M5 effect size as the reference. Existing results are **not** re-run, relabelled or
  re-scored. A report citing a displayed-mid target from the pmxt era carries an "M5 dust caveat" with the measured
  dust share. Stage P-D (a touch-size field in the sweep row) is proposed under a separately reviewed collector change.
- **D1 advances but D1-rep fails, or D1 fails or is not detected:** no correction. Displayed mids stay the standard.
  The dust share and `|m_d − m_c|` distribution are reported as descriptives, and CH80 route 1 is closed.
- **GD fails with the coverage audit passed:** "dust is rare, no correction needed" (CH80 closed). With the audit
  failed: "not testable (source unavailable)", and no methods consequence.

**What kills CH80.** GD fails (dust < 5% of two-sided market-minutes: "dust is rare, no correction needed"); D1 below
floor or not detected; the shuffle placebo advances.

### CB9-F: Data jobs

q0180 smoke (PASS needs: ≥ 18 of 20 receipts per era decoded with the pinned topics and T1 = T2; **Yahoo bar clock
(round 1 item 1):** for two out-of-window full sessions of one ticker (NVDA), after the §2.2 drop exactly 7 bars remain,
the first bar's start is 09:30 ET, the first bar's open equals Yahoo's daily open within 0.2%, the last bar's close
equals Yahoo's daily close within 0.2%, and the dropped rows are recorded by count. Any failure → P "not testable
(source)", counted; the bar rule is never re-fitted. Gamma paging returns stable counts on two out-of-window days;
pmxt HEADs 200 for three window hours). q0181/q0188 audit samples. q0182 keys. q0183-q0184 P frame, bars, books, prints.
q0185-q0187 K/D frame, books, prints, seal. q0189 census. q0193 conditional S1 fetch. q0195/q0198 prospective P
collections. Every data job writes a manifest (file sha256, request counts, failures, fingerprint, data-dumps size and
margin).

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` is under `backend/scripts/`, `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check; analysis
jobs also need the CB9 freeze. All `family` = `creative_batch_9`.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0180 | cpu | 47 | about 80 req at ≤ 1 rps, < 5 min, mem 200 | - | sign rules file + smoke code reviewed |
| q0181 | net | 43 | about 2,700 req, about 25 min, mem 300, ≤ 0.01 GB | q0180 | q0180 PASS and after `T_seal` (round 1) |
| q0182 | net | 43 | about 400 req | q0164, q0166, q0168 | after `T_seal` |
| q0183 | net | 42 | about 350 req, ≤ 0.01 GB | q0182 | with q0182 |
| q0184 | net | 40 | pmxt ≤ 40 GB, about 4,700 req, mem 1,500, ≤ 0.02 GB | q0183 | with q0183 |
| q0185 | net | 42 | about 1,200 req, ≤ 0.01 GB | q0182 | with q0182 |
| q0186 | net | 39 | pmxt ≤ 180 GB (M8), about 12,000 req, mem 1,500, ≤ 0.15 GB | q0185 | with q0185 |
| q0187 | cpu | 39 | light | q0186 | with q0186 |
| q0188 | net | 38 | about 1,000 receipts, mem 300 | q0187 | with q0187 |
| q0189 | cpu | 37 | ≤ 1.2 GB | q0181, q0184, q0187, q0188 | after the seal copy is committed |
| q0190-q0192 | cpu | 36 | ≤ 1.5 GB | q0189 | after the CB9 freeze |
| q0193-q0194 | net / cpu | 36 | ≤ 20,000 receipts / ≤ 1 GB | q0190 | only on "material noise" |
| q0195 | cpu | 44 | about 150 req/session at ≤ 1 rps, rolling | q0191 | only if P1 or P2 advanced |
| q0196 | cpu | 36 | ≤ 0.5 GB | q0195 | after `T9_P2_end` + 2 d |
| q0197 | cpu | 36 | ≤ 1.5 GB | q0192 | only if K1 or D1 advanced |
| q0198 | cpu | 45 | about 3,500 req per half day | - | half-day rules hash committed before 2026-11-27 |

```json
{"id": "q0180_cb9_smoke", "title": "CB9: smoke (20 receipts per exchange era decoded with pinned topics, T1 = T2; Yahoo bar clock: 7 regular bars after the drop, first open and last close vs daily open/close within 0.2%, 2 out-of-window sessions; Pyth frame paging on 2 out-of-window days; pmxt HEADs); counts only", "family": "creative_batch_9", "priority": 47, "expected_value": "go/no-go for every CB9 source", "data": ["public Polygon JSON-RPC (keyless)", "public Data API, Gamma", "Yahoo chart (hourly, out of window)", "pmxt HEAD"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "cpu", "network": "polygon-rpc, data-api, gamma-api, yahoo, r2v2.pmxt.dev"}, "depends_on": [], "argv": ["scripts/run_cb9.py", "smoke", "--rules", "../docs/research_lab/seals/cb9_sign_rules_v3.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch9/smoke.json", "trials.jsonl (cb9_descriptive)"], "next_action": "PASS: q0181; FAIL of the receipt part: S0 not run (source), counted", "notes": "CREATIVE_BATCH_9.md CB9-F. DRAFT. May run before T_seal (cpu lane). Prints counts only."}
{"id": "q0181_cb9_sign_audit_A", "title": "CB9-S: S0a [2026-10-01,10-15) and S0c [2026-02-01,04-27) print samples (250 markets x 4 prints each), receipts, T1/T2, fill type; no agreement computed", "family": "creative_batch_9", "priority": 43, "expected_value": "S0 data for the side-flag measurement", "data": ["public Gamma, Data API windowed trades", "public Polygon JSON-RPC receipts", "creative_batch7/exclusion_keys (ids only)"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "gamma-api, data-api, polygon-rpc"}, "depends_on": ["q0180b_cb9_smoke_v2"], "argv": ["scripts/run_cb9.py", "sign-audit", "--strata", "a,c", "--rules", "../docs/research_lab/seals/cb9_sign_rules_v5.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch9/sign/{s0a,s0c}/{prints_classes.csv.gz,manifest.json}"], "next_action": "q0189 census (counts); agreement only in q0190 after the freeze", "notes": "DRAFT. Needs the q0180b smoke v2 result (creative_batch9/smoke_v2.json). net lane, commit after T_seal (round 1: Limiter is per-process, not shared with net-lane jobs); raw proxyWallet compared with takerOrderMaker in memory only; HMAC strict loader."}
{"id": "q0182_cb9_exclusion_keys", "title": "CB9: exclusion keys = CB8 q0164 keys + ids/keys of seal copies committed since (h7_cb4_*, h8_*, h9_flow, CB8 updown frame/holdout, CB8-H frame)", "family": "creative_batch_9", "priority": 43, "expected_value": "disjointness of P, K, D", "data": ["creative_batch8/exclusion_keys.csv.gz", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0164_cb8_exclusion_keys", "q0166_cb8_updown_books", "q0168_h9_flow_seal"], "argv": ["scripts/run_cb9.py", "exclusion-keys", "--cb8-keys-sha256", "TODO-COORDINATOR-q0164-sha256", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch9/exclusion_keys.csv.gz", "manifest.json"], "next_action": "q0183, q0185", "notes": "DRAFT. After T_seal. PLACEHOLDER: the argument TODO-COORDINATOR-q0164-sha256 must be replaced by the pinned sha256 of q0164 exclusion_keys.csv.gz at promotion (a non-hash token makes the job refuse). >2% missing metadata -> disjointness unverified (P, K, D not testable, counted)."}
{"id": "q0183_cb9_pyth_frame", "title": "CB9-P: Gamma frame of Pyth equity Up/Down dailies ending 20:00Z on full NYSE sessions 2026-04-13..08-07 (minus pmxt gap), frozen regexes and text flags, key drops; Yahoo hourly + daily bars 2026-02-01..08-10; outcomes and settlement closes to guarded files", "family": "creative_batch_9", "priority": 42, "expected_value": "P population and anchors", "data": ["public Gamma", "Yahoo chart hourly/daily", "creative_batch9/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, yahoo"}, "depends_on": ["q0182_cb9_exclusion_keys"], "argv": ["scripts/run_cb9.py", "pyth-frame", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch9/pyth_frame/{frame.csv.gz,bars_pre.csv.gz,strikes.csv.gz,closes_settle_guarded.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0184", "notes": "DRAFT. No code path compares consecutive closes outside q0191."}
{"id": "q0184_cb9_pyth_books", "title": "CB9-P: pmxt states at 14:32Z/16:32Z/19:32Z checkpoints (fresh rule) and Data API prints in [t, t+300 s] for frame markets", "family": "creative_batch_9", "priority": 40, "expected_value": "P1/P2 Stage 1 inputs", "data": ["pmxt v2 hourly files (range reads by <= 25 condition ids)", "public Data API windowed trades"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "net", "network": "r2v2.pmxt.dev, data-api"}, "depends_on": ["q0183_cb9_pyth_frame"], "argv": ["scripts/run_cb9.py", "pyth-books", "--ingress-cap-gb", "40", "--rps", "2", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "40", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["research_lab/creative_batch9/pyth/{states.csv.gz,prints.csv.gz,manifest.json}"], "next_action": "q0189", "notes": "DRAFT. Row-group streaming, column projection. Resumable per session.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"(pyth_books_complete|ingress_cap_reached)\""}}
{"id": "q0185_cb9_kd_frame", "title": "CB9-K/D: Gamma frame (life overlap >= 3 d, volume >= $10k, non-weather, non-crypto-updown, non-Pyth), key drops, <= 3 per event, seeded 1,000 markets, event split SCREEN/HOLDOUT (arepo-cb9-kd-split)", "family": "creative_batch_9", "priority": 42, "expected_value": "K/D population and split", "data": ["public Gamma", "creative_batch9/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0182_cb9_exclusion_keys"], "argv": ["scripts/run_cb9.py", "kd-frame", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 3000, "max_retries": 2, "outputs": ["research_lab/creative_batch9/kd_frame/{frame.csv.gz,split.json,manifest.json}"], "next_action": "q0186", "notes": "DRAFT. Split written before any pmxt or print read."}
{"id": "q0186_cb9_kd_books", "title": "CB9-K/D: pmxt hour 14Z (13Z lookback only when needed) of every window day for frame markets: origin states, all book and last_trade_price events of the hour; Data API prints [t-6h, t+7h]; HOLDOUT written to holdout/", "family": "creative_batch_9", "priority": 39, "expected_value": "K1/D1 inputs, S0b sample", "data": ["pmxt v2 hourly files", "public Data API windowed trades"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "net", "network": "r2v2.pmxt.dev, data-api"}, "depends_on": ["q0185_cb9_kd_frame"], "argv": ["scripts/run_cb9.py", "kd-books", "--ingress-cap-gb", "180", "--rps", "4", "--disk-cap-gb", "0.15", "--data-dumps-cap-gb", "40", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["research_lab/creative_batch9/kd/{screen,holdout}/...", "manifest.json"], "next_action": "q0187", "notes": "DRAFT. Days in seeded order; cap truncates evenly; never two multi-GB jobs at once.", "repeat": {"max_runs": 14, "until_log_regex": "\"status\": \"(kd_books_complete|ingress_cap_reached)\""}}
{"id": "q0187_cb9_kd_seal", "title": "CB9-K/D: HOLDOUT listing sha256, seal-time drops vs seal copies committed by now, seal copy seals/cb9_kd_holdout_SEAL.json", "family": "creative_batch_9", "priority": 39, "expected_value": "sealed holdout", "data": ["creative_batch9/kd/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api (light)"}, "depends_on": ["q0186_cb9_kd_books"], "argv": ["scripts/run_cb9.py", "kd-seal", "--rps", "2"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch9/kd/holdout_SEAL.json"], "next_action": "commit the seal copy; q0188", "notes": "DRAFT. Sealed files never edited; drops recorded as DROPPED_* blocks."}
{"id": "q0188_cb9_sign_audit_B", "title": "CB9-S: S0b 1,000 SCREEN K/D prints (<= 4 per market), receipts, T1/T2, fill type, pmxt last_trade_price feed side by tx hash", "family": "creative_batch_9", "priority": 38, "expected_value": "S0 pmxt-era stratum and the feed-side column", "data": ["creative_batch9/kd/screen prints", "public Polygon JSON-RPC receipts"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "polygon-rpc"}, "depends_on": ["q0187_cb9_kd_seal"], "argv": ["scripts/run_cb9.py", "sign-audit", "--strata", "b", "--rules", "../docs/research_lab/seals/cb9_sign_rules_v5.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 3000, "max_retries": 2, "outputs": ["research_lab/creative_batch9/sign/s0b/{prints_classes.csv.gz,manifest.json}"], "next_action": "q0189", "notes": "DRAFT. No HOLDOUT print is sampled."}
{"id": "q0189_cb9_census", "title": "CB9: pre-freeze census, counts only (S0 match/availability, GP, GK, GD, cell cut points from features only, MDEs)", "family": "creative_batch_9", "priority": 37, "expected_value": "gates and MDEs before the freeze", "data": ["creative_batch9/* (SCREEN only; HOLDOUT file and event counts)"], "resources": {"mem_mb": 1200, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0181_cb9_sign_audit_A", "q0184_cb9_pyth_books", "q0187_cb9_kd_seal", "q0188_cb9_sign_audit_B"], "argv": ["scripts/run_cb9.py", "census"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/census.json", "trials.jsonl (cb9_descriptive)"], "next_action": "science-reviewer freeze check, then model_specs/cb9_v1.json", "notes": "DRAFT. Outcome guard; no agreement, net, contrast or mark-out computed."}
{"id": "q0190_cb9_screen_S0", "title": "CB9-S: S0 agreement per stratum, q_LB = min(market-cluster bootstrap 0.5th pct, market-level Wilson 99%), per-stratum verdict (near-truth / minor noise / material noise; GS fail -> unverified), notional-weighted agreement reported", "family": "creative_batch_9", "priority": 36, "expected_value": "methods verdict for every flow result", "data": ["creative_batch9/sign/*"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0189_cb9_census"], "argv": ["scripts/run_cb9.py", "screen", "--family", "S0"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_S0.json", "trials.jsonl (cb9_test + creative_batch_9:S)"], "next_action": "material noise: commit q0193/q0194; else none", "notes": "DRAFT. Refuses before the CB9 freeze hash."}
{"id": "q0191_cb9_screen_P", "title": "CB9-P: P1 and P2 Stage 1 with placebos and binding robustness", "family": "creative_batch_9", "priority": 36, "expected_value": "P verdicts", "data": ["creative_batch9/pyth*/ (guarded files opened here only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0189_cb9_census"], "argv": ["scripts/run_cb9.py", "screen", "--family", "P"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_P.json", "trials.jsonl (cb9_test + creative_batch_9:P)"], "next_action": "advanced: commit q0195", "notes": "DRAFT."}
{"id": "q0192_cb9_screen_KD", "title": "CB9-K/D: K1 and D1 Stage 1 on SCREEN events with placebos and binding robustness", "family": "creative_batch_9", "priority": 36, "expected_value": "K and D verdicts", "data": ["creative_batch9/kd/screen/"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0189_cb9_census"], "argv": ["scripts/run_cb9.py", "screen", "--family", "KD"], "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_KD.json", "trials.jsonl (cb9_test + creative_batch_9:K, :D)"], "next_action": "advanced: commit q0197", "notes": "DRAFT. Refuses to open holdout/."}
{"id": "q0193_cb9_sign_fetch_h10", "title": "CB9-S1: h10_sign fetch (1,200 markets, one seeded 72-h window each in the triggered era before 2026-10-01; all taker prints; receipts up to 20,000 prints, whole windows)", "family": "creative_batch_9", "priority": 36, "expected_value": "S1 data (conditional)", "data": ["public Gamma, Data API", "public Polygon JSON-RPC", "creative_batch9/exclusion_keys.csv.gz"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "net", "network": "gamma-api, data-api, polygon-rpc"}, "depends_on": ["q0190_cb9_screen_S0"], "argv": ["scripts/run_cb9.py", "sign-fetch", "--rps", "2", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h10_sign/{sample.csv.gz,prints/,receipts_classes.csv.gz,manifest.json}"], "next_action": "q0194", "notes": "DRAFT. Commit only on an S0 'material noise' verdict. Excludes by q0182 keys h9_flow, every sealed/worn run, the CB9 K/D frame (SCREEN and HOLDOUT), the P frame and the S0 samples (round 1).", "repeat": {"max_runs": 4, "until_log_regex": "\"status\": \"sign_fetch_complete\""}}
{"id": "q0194_cb9_screen_S1", "title": "CB9-S1: ratio of on-chain-signed to API-signed 6h flow slope on identical units; pass iff R >= 1.5 and the event-cluster one-sided 99% lower bound > 1.5", "family": "creative_batch_9", "priority": 36, "expected_value": "re-scaled flow ceiling", "data": ["history/h10_sign/"], "resources": {"mem_mb": 1000, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0193_cb9_sign_fetch_h10"], "argv": ["scripts/run_cb9.py", "screen", "--family", "S1"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_S1.json", "trials.jsonl (cb9_test)"], "next_action": "methods note M4", "notes": "DRAFT."}
{"id": "q0195_cb9_pyth_live", "title": "CB9-P Stage 2: 30 full sessions from T9_P2_start; CLOB /book of frame-rule markets at each checkpoint (receipt-timed); prints of quote windows and Yahoo hourly bars after each session", "family": "creative_batch_9", "priority": 44, "expected_value": "out-of-time P replication data", "data": ["public Gamma, CLOB /book, Data API, Yahoo"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, data-api, yahoo"}, "depends_on": ["q0191_cb9_screen_P"], "argv": ["scripts/run_cb9.py", "pyth-live", "--sessions", "30", "--rps", "1", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 3000, "max_retries": 3, "outputs": ["research_lab/creative_batch9/pyth_live/<session>/...", "pyth_live/COMPLETE.json"], "next_action": "q0196 after T9_P2_end + 2 d", "notes": "DRAFT. Only if P1 or P2 advanced. Checkpoints in ET (EST after 2026-11-01). Yahoo fetched at each checkpoint (receipt time recorded); post-session bars diagnostic only; failed checkpoints unavailable (source), no substitute, count toward the 30; > 20% unavailable -> P-rep not testable (source unavailable). Re-check fix 3: before 08:00 ET of the first session minus 35 min it exits 75 at once (idle heartbeat every 10 h); a step due within 35 min is waited for inside the run (queue re-runs come every ~30 min, the checkpoint window is 10 min); completion prints status pyth_live_complete and writes COMPLETE.json (rep-P requires it).", "repeat": {"max_runs": 2400, "until_log_regex": "\"status\": \"pyth_live_complete\""}}
{"id": "q0196_cb9_rep_P", "title": "CB9-P: P1-rep and P2-rep on post-freeze sessions", "family": "creative_batch_9", "priority": 36, "expected_value": "L2 verdict", "data": ["creative_batch9/pyth_live/"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0195_cb9_pyth_live"], "argv": ["scripts/run_cb9.py", "rep", "--family", "P"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_P_rep.json", "trials.jsonl (cb9_replication)"], "next_action": "pass: Stage P-P registration draft", "notes": "DRAFT. Re-check fix 4: exits 75 (nothing written, no trial line) until pyth_live/COMPLETE.json exists, now >= last session end + 2 d and every session outcome is final."}
{"id": "q0197_cb9_rep_KD", "title": "CB9-K/D: K1-rep and/or D1-rep on sealed HOLDOUT events", "family": "creative_batch_9", "priority": 36, "expected_value": "L2 verdict", "data": ["creative_batch9/kd/holdout/"], "resources": {"mem_mb": 1500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0191_cb9_screen_P", "q0192_cb9_screen_KD"], "argv": ["scripts/run_cb9.py", "rep", "--family", "KD"], "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch9/results_KD_rep.json", "trials.jsonl (cb9_replication)"], "next_action": "pass: Stage P-K/P-D drafts", "notes": "DRAFT. Depends on q0191 too (re-check d): the Stage-2 k needs results_P.json and results_KD.json. Only for advanced tests; verifies the seal hash first."}
{"id": "q0198_cb9_halfday_poll", "title": "CB9-P descriptive: 2026-11-27 and 2026-12-24 half sessions, books every minute 13:05-16:00 ET for frame-rule markets; Yahoo 1-minute bars after the close; uncounted", "family": "creative_batch_9", "priority": 45, "expected_value": "CH83c descriptive", "data": ["public Gamma, CLOB /book, Yahoo"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, yahoo"}, "depends_on": [], "argv": ["scripts/run_cb9.py", "halfday-poll", "--days", "2026-11-27,2026-12-24", "--rps", "1", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 14400, "max_retries": 1, "outputs": ["research_lab/creative_batch9/halfday/<day>/..."], "next_action": "report as cb9_descriptive", "notes": "DRAFT. Rules hash committed before 2026-11-27. Re-check a: one run polls a whole half session (waits for 13:05 ET when within 35 min, every minute to 16:00 ET, then Yahoo 1-minute bars per ticker once; DONE.json per day; a window passed unseen is missed_window, never back-filled); before that exit 75 (idle heartbeat every 10 h); prints halfday_day_done per day and halfday_complete at the end.", "repeat": {"max_runs": 250, "until_log_regex": "\"status\": \"halfday_complete\""}}
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
- **Round-1 additions.**
  - `cb9_pyth`: the Yahoo bar parser (start stamp, end = min(start + 60 min, 16:00 ET), drop rule, 7-bar check, half
    session at 13:00 ET) on a fixture with an 8th closing row; the smoke open/close check; Stage-2 receipt-time `S_t`
    with post-session bars diagnostic-only; the Yahoo partial-failure rule (no substitute, counts toward 30, > 20% →
    not testable).
  - `cb9_sign`: the per-stratum verdict with the era map; GS fail → "unverified", never inherited; `q_LB` = min(market
    bootstrap, market-level Wilson) including the all-agree case; notional-weighted agreement. S1: the h10 exclusion
    list includes the K/D SCREEN/HOLDOUT, P and S0 ids; the pass rule with lower bound > 1.5, where `β_api ≤ 0` draws
    count as failures.
  - `cb9_kd`: GK counted after the skew cut; the route gate on both per filled share and per origin; dust by
    `orderMinSize` (the $1 variant reported); the next transaction by hash with VWAP (a sweep fixture with a dust fill),
    the `u + 1 s` start and the 10-minute limit.
  - Coverage audits (P and K/D, conditioned on prints) and the label rule ("source unavailable" / "no fresh book" / "no
    opportunity").
  - Runner: batch-Holm k1 = 5 fixed; q0181 refuses before `T_seal`.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| S0 | 1 | `cb9_test` + `creative_batch_9:S` | decision bands (§CB9-S), not Holm |
| Stage 1: P1, P2, K1, D1 | 4 | `cb9_test` + `:P` (2), `:K`, `:D` | p < 0.01 each; batch-Holm label (α 0.01, k1 = 5 fixed, S1's slot held whatever S0; round 1); BY triage |
| S1 (conditional) | ≤ 1 | `cb9_test` + `:S` | `R̂ ≥ 1.5` and one-sided 99% lower bound > 1.5 (round 1) |
| Stage 2: P1-rep, P2-rep, K1-rep, D1-rep | ≤ 4 | `cb9_replication` | one Holm, one-sided α 0.05 |
| Census, gates, descriptives, feed-side, strike stratum, half days | 0 | `cb9_descriptive` | - |
| **Total** | **5 fixed + ≤ 5 conditional = 5-10** | | cumulative ≥ 1,131 at drafting → ≥ 1,136-1,141 plus CB6-CB8 |

**Host compute.** About 4-6 CPU-hours at nice 19; peak RAM 1.5 GB (pmxt readers, K/D screen).
**Network.** Before `T_seal`: about 80 requests (q0180) on the `cpu` lane. After: about 21,600 API requests on the `net`
lane (q0181 included), about 3,000-23,000 receipts, ≤ 220 GB pmxt ingress (two capped jobs, serial; q0186 cap 180 GB after M8). **Disk.** ≤ 0.3 GB.

## 7. Main scientific risks

1. **S0 is probably "near-truth".** The v2 exchange logs the side explicitly and the Data API probably indexes those
   logs; S0 then closes CH79 cheaply. The informative residue is the pmxt feed column (Dubach's object) and the v1 era
   (S0c), where the side is derived from asset ids and complementary fills are common.
2. **Match rule failures.** Operator batching, proxy versus signer addresses or multi-order transactions can push the
   match rate under 90% (GS fail, "not testable (source)"), which is a data answer, not a null.
3. **P's anchor is coarse and not the settlement source.** Yahoo hourly bars and the official close stand in for Pyth's
   minute candles (the Pyth path is keyed, probe 6). Real bots use real-time feeds; an hourly anchor can only find large
   mispricings (P1 MDE about 10-15c after the round-1 restatement). The Yahoo endpoint is unofficial; a smoke or frame failure makes P "not testable (source)".
4. **Day dependence in P.** Equity dailies share a market factor, and the three checkpoints of a market-day share
   `Y`. About 78 sessions are the effective sample. The comonotone break-even placebo guards p-values; a pass with few
   days is still fragile.
5. **K's fill realism and decay.** One hourly-resolution origin per day, queue position uncertain (binding trade-through
   bracket), and F4/F5 decayed to 40-55% in HB2-R's post-split half. The per-filled-share contrast can be driven by fill
   selection; the skew-sign placebo and the per-origin route gate are the guards. SCREEN-only power gives an MDE of
   about 1c (twice the floor), and GK, counted after the skew cut, may fail. Same calendar as HB2; the cells are
   analogues, not F4/F5's variables.
6. **D is partly mechanical.** A market order sweeps dust by construction; D1's value is the size and frequency of the
   correction, labelled methods.
7. **Queue and disk.** The data-dumps guard is 40 GB after the host disk was enlarged (§2.8); the 4 GB free-disk guards still bind. CB9's
   pmxt jobs (≤ 220 GB ingress after M8) queue behind CB4 and CB8 pmxt work; the K/D screen may slip beyond a week (no rule
   changes; dates are fixed by events, not by deadlines).
8. **Forking across families.** S0b's verdict changes how K is labelled, not how K is computed (frozen sides from the
   Data API); no family's rule depends on another family's outcome; batch-Holm k1 = 5 is fixed whatever S0 says.
9. **S1 power.** With the restored lower-bound rule, S1 can pass only for `R` ≳ 2.4 (`q` ≲ 0.71). Moderate material
   noise triggers S1 but leaves it "not detected at MDE"; M4's re-stated ceilings still apply as upper bounds.

## 8. Next actions

1. **Challenger review: done** (round 1, §9-§10; one challenge, one response, no second round).
2. Write `seals/cb9_sign_rules.json` (pins re-verified from Polymarket's contracts list and the v2 source for the side
   enum mapping; the §2.2 Yahoo bar clock and smoke criteria), smoke code, `cb9_sign.py` and tests. Then the
   **code-against-design freeze check** (`science-reviewer`). Commit q0180 (`cpu` lane, may run before `T_seal`), then
   q0181 on the `net` lane after `T_seal`.
3. After `T_seal` and CB8's q0164/q0166/q0168: `seals/cb9_rules.json`, P/K/D code and tests, freeze check, q0182-q0188.
4. Census q0189 → freeze `model_specs/cb9_v1.json` → q0190-q0192 → conditional jobs by the stated triggers.
5. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.

## 9. Challenger review, round 1 (science-reviewer, 2026-10-17)

One `science-reviewer` pass on the committed draft `00dd145`. **Verdict: every family ACCEPT_WITH_REQUIRED_CHANGES;
overall ACCEPT_WITH_REQUIRED_CHANGES.** Items, recorded in substance:

**Counter.** 1,131 is right. The 1,106 in the ledger is an old CB1-D note, not a competing count, and the draft (§0.2)
presented it as a disagreement. The `KIND_RULES` blocker (`cumulative_count()` failing closed on the `design_change`
kind) is already fixed in `e5cfb3a` (`design_change` counts 0).

**Required changes.**
1. **P, Yahoo bar clock.** Pin it: timestamp = bar start; end = min(start + 60 min, 16:00 ET); drop closing and
   zero-length rows. The smoke checks this on an out-of-window session against Yahoo's daily open/close (the probe saw 8
   hourly rows where 7 regular-session bars were expected). Stage 2 must fetch Yahoo at each checkpoint and record the
   receipt time; post-session bars are diagnostic only.
2. **Counter blocker.** Done in `e5cfb3a`.
3. **S0 eras and decision.** Pre-state the mapping: E007 → S0a; HB1/HB2/K → S0b; S0c informs no existing result. A
   stratum failing gate GS leaves its result "unverified" and never takes another stratum's verdict (fix "every stratum
   passing GS"). Decide on a market-cluster bootstrap lower bound, not a print-level Wilson bound (4 prints per market).
   Narrow "flow results stand as measured": S0 audits the API `side` field, not the signing in `history_backfill`/h2.
4. **S1.** `h10_sign` must also exclude the CB9 K/D SCREEN and HOLDOUT markets and the P markets, not just h9_flow.
   Restore a pass rule with a lower bound above 1.5 (the source idea's kill rule "ratio CI includes 1.5"), or justify
   in writing.
5. **K.** Restate the MDE using SCREEN-only units after the median-`|x6|` skew cut (about 500 filled origins per quote
   type, MDE about 1c against the 0.5c floor). Say whether gate GK counts before or after the cut. Also require net > 0
   per posted share or per origin, not only per filled share.
6. **D1.** Pin "next print": aggregate by transaction hash, with transaction VWAP or last fill pre-stated, so a dust
   fill in a sweep cannot decide the sign mechanically. Pre-state what AREPO changes on pass and on fail.
7. **P1 MDE.** The three checkpoints of a market-day share `Y`, and equities share a market factor. Restate the MDE
   realistically (about 10-15c).

**Should-changes.**
- q0181 sends about 2,700 network requests on the `cpu` lane. Disclose this and confirm that the rate limiter is shared
  across processes with `net`-lane jobs and the collector (check `history_backfill.Limiter` / `live_pass_or_lock`), or
  move the job to `net`.
- Fix batch-Holm k1 = 5 regardless of S0.
- Adopt CB8's pmxt coverage audit and the "source unavailable" vs "no opportunity" labels for P and K/D.
- K: disclose the same calendar as HB2 (disjoint markets only), the RV and SPR redefinitions vs F4/F5, and that fills
  and marks depend on the Data API side.
- D: justify the "< $1" dust rule (it flags legal 5-share orders below 0.20) or make the share-size rule primary.
  Disclose that GD changed from market-hours to market-minutes.
- P Stage 2: a rule for Yahoo failing part-way (unavailable sessions counted, no substitute source).
- S0: report notional-weighted agreement.
- Data-dumps is 12.5 GB, not 12.

## 10. Response to challenger round 1 (2026-10-17)

Every item is applied in the design text above. No floor, threshold, gate, alpha or cap was relaxed; the changes
tighten (S0 bound, S1 pass rule, K route gate, GK counting, k1) or disclose.

| Item | Change | Sections |
|---|---|---|
| Counter | §0.2 now states 1,131 as the count. The 1,106 is identified as an old CB1-D ledger note, not a competing count. The `e5cfb3a` fix (`design_change` counts 0) is recorded | §0.2; §2.5 |
| R1 Yahoo clock | Bar clock pinned: start stamp; `e = min(o + 60 min, 16:00 ET)` (13:00 on half sessions); pre-open, closing and zero-length rows dropped; exactly 7 bars per full session, else "bars unavailable", counted. Checkpoints map to the 09:30/11:30/14:30 bars. The smoke checks two out-of-window NVDA sessions: 7 bars, and first open and last close within 0.2% of the daily open and close. Failure → P "not testable (source)". Stage 2 fetches Yahoo at each checkpoint with the receipt time (plus a receipt-timed pre-session σ/`K_d` fetch); post-session bars are diagnostic only | §2.2; §CB9-P features, Stage 2; §CB9-F; q0180, q0195; §5 |
| R2 Counter blocker | Recorded as fixed in `e5cfb3a`; no CB9 change needed | §0.2 |
| R3 S0 eras | Era map pre-stated (S0a → E007; S0b → HB1, HB2, K; S0c → no existing result; HB's v1-era first two weeks disclosed). Verdicts are per stratum. A GS fail → "not testable (source)", with mapped results "unverified", never inherited; the pooled `q̂` is descriptive only. Decision bound `q_LB` = min(market-cluster bootstrap 0.5th percentile, market-level Wilson 99%); the minimum guards the degenerate all-agree bootstrap, and the print-level Wilson is reported only. "Stand as measured" narrowed to "the API `side` field is accurate in that era; AREPO's own signing code is not audited" | §1.1; §2.7 S0; §CB9-S era map, decision table, kills; q0190 |
| R4 S1 | `h10_sign` excludes, by q0182 keys, h9_flow, every sealed or worn run, **the K/D frame (SCREEN and HOLDOUT), the P frame and the S0 samples**. Pass rule restored: `R̂ ≥ 1.5` **and** the event-cluster one-sided 99% lower bound > 1.5 (draws with `β_api ≤ 0` count as failures). The MDE is restated honestly: a pass needs `R` ≈ 2.4 or more | §2.4; §CB9-S S1, kills; §6; §7 risk 9; q0193, q0194 |
| R5 K | MDE restated on SCREEN units after the skew cut: about 1,650 cell origins, about 500 filled origins per quote type, **MDE about 1c** against the unchanged 0.5c floor. **GK is counted after the cut** (stricter; disclosed that it may fail at these numbers; not lowered). Route gate: the skewed maker needs net > 0 per filled share **and** per origin (per 100 posted shares, unfilled = 0) | §2.4; §2.7 K; §CB9-K route gate, MDE; §7 risk 5 |
| R6 D1 | The next transaction is pinned to the first Data API transaction hash at `ts ∈ [u + 1 s, u + 600 s]`; `P` = **VWAP of all that transaction's prints on the token** (primary; last fill is a variant). Side is never used. Pre-stated consequences: on a pass (Stage 1 and D1-rep), methods note M5: later designs declare a size-cutoff mid or a dust exclusion, existing results are not re-run, a citation caveat is added, and Stage P-D is proposed separately. On a fail: no correction; displayed mids stay the standard; CH80 route 1 closed | §CB9-D units, consequences; §2.6; §5 |
| R7 P1 MDE | Restated with the shared `Y` across checkpoints and the cross-ticker market factor: **P1 MDE about 10-15c**; P2 MDE about 2-4c per posted share (day-clustered, shared `Y`) | §CB9-P MDE; §7 risks 3-4 |
| S q0181 rate | Checked in code: `history_backfill.Limiter` paces within one process only. It yields to the collector via `live_pass_or_lock()` but is not shared with other queue jobs. **q0181 moved to the `net` lane after `T_seal`** (priority 43). q0180 stays on `cpu` at ≤ 1 rps (about 20 API requests; overlap disclosed). q0195/q0198 run at ≤ 1 rps and log any concurrent `net` job | header; §0.1; §2.8; §4; q0180, q0181, q0195, q0198 |
| S Holm k1 | k1 = 5 fixed, whatever S0's verdict | §2.3; §6 |
| S coverage audit | CB8's audit adopted for P and K/D, conditioned on Data API prints in the same span (a deviation from CB8's separate 13Z hour: no new ingress, and quiet markets are not misread as missing). PASS ≥ 90%. Labels: "source unavailable", "no fresh book", and "no opportunity" (the last only with the audit passed and ≥ 80% of SCREEN units source-available) | §2.7 |
| S K disclosures | Same calendar as HB2 (disjoint markets only); RV/SPR are analogues, not F4/F5's variables, so the credit is "moderation in analogue cells"; `x6`, fills and marks use the Data API side, so K1 carries S0b's label | §CB9-K disclosures; §7 risk 5 |
| S D dust rule | Share rule primary (`size < orderMinSize`). The $1 clause is dropped from the primary, with the reason (it flags legal 5-share orders below 0.20); the share-or-$1 version is reported. The GD market-minutes vs CH80's market-hours change is disclosed (minutes is the stricter; the hour share is reported) | §CB9-D units; §2.7 D; §0 table |
| S P Stage 2 Yahoo | Failed checkpoints are "unavailable (source)", with no substitute source. A failed σ/`K_d` fetch loses the whole session. Unavailable sessions count toward the 30 and are never replaced. More than 20% unavailable → P-rep "not testable (source unavailable)" | §CB9-P Stage 2; q0195 |
| S S0 weighting | Notional-weighted agreement reported | §CB9-S; q0190 |
| S data-dumps | 12.5 GB | §0.2; §2.8; §7 risk 7 |

**Effect on counts and power.** k is unchanged: **5 fixed (S0, P1, P2, K1, D1) + up to 5 conditional = 5-10**;
batch-Holm k1 = 5. MDEs: P1 about 10-15c (was 7-10c), P2 about 2-4c, K1 about 1c (was 0.5c), D1 about 0.2c
(unchanged), S1 `R` ≈ 2.4. No floor moved. Request totals: q0181's about 2,700 move from the pre-`T_seal` `cpu` lane to the
post-`T_seal` `net` lane.

This is the single response round; the next review is the code-against-design freeze check.

## 11. Implementation notes (2026-10-17; appended, design text above unchanged)

**Commits.** `e07d867` (`cb9_common.py`, `battery2.KIND_RULES` cb9 kinds), `388862e` (`cb9_sign.py`, `cb9_pyth.py`, `scripts/run_cb9.py`, tests
`test_cb9_sign.py`, `test_cb9_pyth.py`, `test_run_cb9.py`), `f7ee838` (rules files). K/D: `cb9_kd.py` + `test_cb9_kd.py` (`7402a81`, `59e7432`).
Draft spec: `queue/drafts/q0180_cb9_smoke.json` (nothing in `queue/jobs/`).

**Rules files (written from code at `388862e`; wallet_key_fingerprint `80ce5e81a539a570`, the CB8 key).**

| File | file sha256 | rules_sha256 |
|---|---|---|
| `seals/cb9_sign_rules.json` (`cb9-sign-rules-v1`) | `69f98882fe1a0c4d41e912ee16715a784ac8e7f718d5c12ec25679ca238a21cf` | `2372d7cf0ca68b0d6502910712d58ffea9254db32caa62c654b536a76c6e816a` |
| `seals/cb9_rules.json` (`cb9-rules-v1`: P, q0182 keys, census gates) | `c3b4e3c93967eadc6998e89e6429ce35f482f72ad7fa7b452d549fda66f142ad` | `d88d5272a44e89e7454779015147dc5861132e41d4bdbba09db78b456ffff4e1` |
| `seals/cb9_kd_rules.json` (`cb9-kd-rules-v1`) | `e1fa5d6472640421e5c7df90ba58977d51c8c2e200269d281e932a3de881f4e4` | `d10ed7317ac0611d749b6dbcafe5dfef277fbc95da782ee37039b4f2e11f6f0f` |

The local Keccak-256 reproduces all four full topic pins of §CB9-S and the `FeeCharged` prefix; the sign rules file records every computed topic.

**Deviations and open items for the code-against-design freeze check.**
1. Rules files: K/D rules are a separate file (`cb9_kd_rules.json`), not part of `cb9_rules.json` (§1.4); the Yahoo bar clock and smoke
   functions are hashed into both the sign and the P rules files.
2. Contract addresses: v1 exchanges, neg-risk adapter and CTF pinned from memory of Polymarket's published list; v2 exchanges from probe 2-3.
   v2 `Side` enum pinned BUY = 0, SELL = 1; v2 indexed layout = the leading `len(topics) - 1` parameters; v2 share amount = taker amount on BUY,
   maker amount on SELL. None was re-verified against the published list / v2 source in this session (no network). The q0180 smoke
   (T1 = T2 on >= 18 of 20 receipts per era) fails rather than misreads if any is wrong; a wrong pin needs a v2 rules file.
3. P rule-text flags were written from the probe-5 summary and the committed Pyth monthly text, not from the full 2026-09-15 Up/Down text.
   `CREATIVE_HYPOTHESES_2026-10-18` says "exactly equal resolves Down" while probe 5 says "equal -> 50-50"; the design freezes the 50-50
   equality clause, so a Down-on-equal text leaves the frame (counted). Verify the flags before q0183.
4. Design-silent choices (conservative): S0 markets with a capped print window are unavailable, no replacement market; sampled markets with < 4
   prints contribute what they have; liquidity tercile = Gamma volume terciles over the stratum's sample; price bands <0.10 / 0.10-0.30 /
   0.30-0.70 / 0.70-0.90 / >=0.90; S0c drops by the CB7 key file plus seal-copy ids (no key lookup for seal ids); `q_wc` and the GS match rate count
   receipt-unavailable prints as unmatched; the source gate compares side and token; S0 rows store `notional` (size x price) for the round-1
   notional-weighted agreement although §CB9-S lists no price field.
5. S0b draws only from SCREEN pre-origin prints (`*.prints_pre.csv.gz`; the guarded post-origin files are not opened). The pmxt `last_trade_price`
   files cover hour 14Z (13Z lookback), so the feed-side column will be mostly blank. Reading post-origin prints (column-restricted) would fill it;
   that needs a reviewer decision.
6. P choices: sigma uses the six one-hour returns of bars 09:30-14:30 (the 30-minute last bar is never read); the stale anchor at 10:32 is the prior
   session's 14:30 bar; q0184 reads the previous pmxt hour for tokens without a book snapshot by the checkpoint (as CB8-B); the P2 queue depth is the
   resting size at the quote's own level; the trade-through rule needs >= 20 shares strictly through; P2 size weights are filled shares; GP's P2
   fill condition is >= 100 fills for EACH quote type; NYSE 2026 holidays and half sessions are a pinned list.
7. q0181/q0182/q0183/q0184 refuse (exit 2) before `T_seal`; q0180 is not `T_seal`-bound. `--data-dumps-cap-gb` defaults to 12.5 (the specs pass 13).
8. P-rep trial lines carry `evidence_role` `exploratory_historical` with `data_role` `prospective_post_freeze`; the provenance role list has no
   non-confirmation prospective role.
9. q0197 (`rep --family KD` -> `rep-kd`) needs `--stage2-k`, which the §4 draft argv lacks. `screen --family KD` dispatches to `screen-kd`.
10. Batch-Holm is a separate `stage1-label` subcommand over P1, P2, K1, D1, S1 (k1 = 5; not run / not testable -> p = 1).

### 11.1 Freeze check (2026-10-17) and its fixes

Verdicts: q0180 GO_WITH_CONDITIONS (M1-M3 first, the smoke result is write-once); data side NO_GO until M4-M8 and a focused re-check;
analysis side NO_GO until M9-M12. Fixes in this file's code (`7375a86`; K/D parts by implementer B in `cb9_kd.py`):

| Item | Fix |
|---|---|
| M1 | `smoke_receipts` records matched and T1 = T2 counts per pinned exchange address (both v1 and both v2 addresses); `exchanges_exercised` reported |
| M2 | more than 2 unavailable receipts in an era -> NotNow (exit 75, nothing written); unavailable is never a FAIL |
| M3 | `smoke_gamma_paging` records `parse_market` reason counts and the equality-clause sentence of out-of-window primary markets |
| M4 | equality and no-trade flags must hold within one sentence (`[^.]`); old-version texts excluded with their own reasons (`rounded to`, open price); test with an "equal -> Down" sentence followed by the no-trade 50-50 sentence |
| M5 | stall vocabulary (`cb9_common.write_stall` / `stall_of`, header of `run_cb9.py`): `not_run_source`, `disjointness_unverified`, `upstream_not_testable`; terminal, exit 0, labelled; the census copies the label; screens log p = 1. sign-audit stalls only the failed stratum; pyth-frame / pyth-books stall on their smoke criteria and on an upstream stall. h10_sign drops every `pythdata.app` market by rule, so a stalled P frame cannot leak into S1 |
| M6 | `--data-dumps-cap-gb` default 14, every draft passes 14 (§2.8 amended) |
| M9 | q0195 fetches outcomes after settlement (Gamma by id, from close + 6 h, hourly, final when all resolved or after 7 days; unresolved counted) into `<session>/outcomes_guarded.csv.gz`, opened only by rep-P |
| M10 | one Stage-2 rule for both families (`cb9_common.STAGE2_RULE`): k derived by `stage2_k` from `results_P.json` + `results_KD.json` (NotNow until both are final); each test judged when it finishes at alpha/k (strict), in its Stage-1 direction, with the §2.4 floor, the binding placebo and the binding robustness checks at that threshold (§2.6 "any advance or pass"); the Holm step-down over final Stage-2 p values is a label (`stage2-label`). `check_stage2_k` refuses an explicit k that differs (rep-kd) |
| M11 | `cmd_screen` / `cmd_rep` results are write-once (`write_results_once`); a re-run refuses before any trial line |
| M12 | §2.3: the P ticker way runs under the small-G rule |

**Rulings (recorded).** (a) Accepted, with M1. (b) Fact checked by the coordinator with one keyless Gamma request (out of window):
current Pyth equity dailies (e.g. `nvda-up-or-down-on-october-16-2026`) say "If the two specified closing prices are exactly equal,
this market will resolve 50-50. Closing prices will be used exactly as published by Pyth, without rounding." and separately
"If NVIDIA (NVDA) does not trade at all during the regular session, the market will resolve 50-50." The comparison is the Pyth
1-minute "Close" of the final regular-session minute vs the most recent prior trading day's close. Older 2025 versions used the
official NASDAQ close vs the open, or close vs prior close rounded to the cent; the frame classifies them out (old-version reasons or
missing flags). §11 item 3's discrepancy is resolved in favour of the design's 50-50 clause. (c) Guarded post-origin prints are not
opened; kd_books stores the 13Z-lookback `last_trade_price` events it already reads, so S0b feed sides exist for prints in
[13Z, 14Z); prints elsewhere are `not_measured`, unmatched ones in that hour `unmatched`. (d) K keeps the 6-h RV on the 600 s grid;
§CB9-K amended. (e) See B's change in `cb9_kd.py`, which records the decision. (f) Accepted; GD on market-minutes is the stricter
gate (disclosed in §2.7). (g), (h) Accepted. (i) Superseded by M10. (j) Accepted: P-rep lines keep `data_role`
`prospective_post_freeze`, label EXPLORATORY. §11 item 7 is superseded by M6 (default 14).

**Rules v2 (written from code at `7375a86`; v1 files kept, superseded, never rewritten).**

| File | file sha256 | rules_sha256 |
|---|---|---|
| `seals/cb9_sign_rules_v2.json` (`cb9-sign-rules-v2`) | `0ad8ed62b5223aa7f64ed8b7c8a5f6d7e27e980f5b43a5861648728f33b44713` | `3864ae5acbeac4bd4579ea39713cedf3efafbe26b7cadfb6a3b1544ad3689999` |
| `seals/cb9_rules_v2.json` (`cb9-rules-v2`) | `2775e79e390d4fb3dafc2108ce969ed321f0975fdf8cc94ec9bb9a1f2c4ca5a5` | `70a4884bed06d0aa451f6d710185e8fea62139ebd145ff6b22d779c2ce65c141` |
| `seals/cb9_kd_rules_v2.json` (`cb9-kd-rules-v2`) | superseded before commit by the cap change below; see the next table | |

**Rules after the cap convention change (written from code at `737cbc0`, `cb9_kd.py` as in B's `c142d4a`).** The data-dumps cap default is a
hashed rules field, so moving it from 14 to 40 superseded the sign / P v2 files (kept, never rewritten) before any job used them.

| File | file sha256 | rules_sha256 |
|---|---|---|
| `seals/cb9_sign_rules_v3.json` (`cb9-sign-rules-v3`) | `6b6327fc600647185202a68a3dc11d0947496a5c7f503d14363d05fa8b1f4239` | `b938aeae62462cf85e0a6435f4186da8f519ad318957ea43937ebf93d21bd389` |
| `seals/cb9_rules_v3.json` (`cb9-rules-v3`) | `551417ee2345e6751f8e9e3fda7384e18cccc28747e10678a9b241708a7cb9ae` | `4f1b4856df68cb33dd6f8629aef166c6006b7902f2b4390a297c7ced6b1c2aad` |
| `seals/cb9_kd_rules_v2.json` (`cb9-kd-rules-v2`) | `e2b3cb9e8904f891133e5e56541071bb6c8a0131448affbf61a6f656a2885969` | `8ee7bf366a013a87eae5a061fba788ebbbacc5945940df5de1e57510256886a1` |

**K/D fixes (implementer B, `c142d4a`).**
- **M7.** The K/D frame includes open and long-dated markets: separate closed and open walks, with an end-date tail window to 2100 and
  `start_date_max` set to 2026-08-07. Only data at or before t enters a feature, and no outcome is read.
- **M8.** The q0186 ingress cap rises from 90 to 180 GB. The origin, 14:00:00Z, is the first instant of hour 14Z, so nearly every token
  needs the 13Z lookback, about 2x ingress per day (roughly 1-1.6 GB/day over about 113 days). pmxt reads are streamed one row group at a
  time and not stored; outputs stay within the 0.15 GB cap, and Oracle ingress is unmetered. Under 90 GB, only about 56-94 of 113 days
  would be read (50-83%), so GK (≥ 2,000) would almost surely fail. Even at full coverage the design's own estimate is about 1,650, so GK
  may fail regardless; this is disclosed and not lowered. Expected wall time is about 6-10 h in 85-minute chunks. No gate, floor or output
  cap changed. q0186 draft: `--ingress-cap-gb 180`, repeat `max_runs` 14.
- **M5 (K/D).** kd-frame stalls before any request on an unverified q0182 report (`disjointness_unverified`); kd-books copies a frame stall
  as `upstream_not_testable` or stalls `not_run_source` on a failed smoke `pmxt_heads`; exit 0, sticky; kd-seal passes it on; the census and
  screen-kd carry the label and log K1 / D1 with p = 1.
- **M10 (K/D).** rep-kd derives k with `cb9_common.stage2_k`; `--stage2-k` is optional and must match (refusal otherwise); the shared
  Stage-2 rule applies.
- **M11 (K/D).** screen-kd and rep-kd results are write-once; no second count line.
- **Ruling (c) format.** The 13Z `last_trade_price` events go in the same `*.ltp.csv.gz` files with the same columns; 13Z rows have `v_ms`
  before 14:00Z, and only tokens whose 13Z hour was read have them. S0b reads them through the existing `*.ltp.csv.gz` glob.
- **Cap convention.** Every CB9 draft and the code default use `--data-dumps-cap-gb 40` (§2.8); free-disk guards unchanged.

### 11.2 Focused re-check (2026-10-17) and its fixes

Verdicts (`science-reviewer`, focused re-check of the freeze-check fixes): **data side GO_WITH_CONDITIONS**; **analysis side GO_WITH_CONDITIONS** for
q0189-q0194 and q0197; **NO_GO for q0195 and q0196 before the fixes below**. No threshold, floor, gate or formula changed.

| Item | Fix | Commit |
|---|---|---|
| MUST 1 | q0182 draft passes `--cb8-keys-sha256 TODO-COORDINATOR-q0164-sha256`, a placeholder that is not a hash (the job refuses on it); **the coordinator must replace it with the pinned sha256 of q0164's `exclusion_keys.csv.gz` at promotion** | this docs commit |
| MUST 2 | `sign_audit` stratum b checks the upstream K/D stall first (`kd_upstream_stall`: kd-frame, then kd-books) and writes a `upstream_not_testable` manifest copying the K/D label (exit 0, sticky: a re-run returns the stall without reading the smoke or any input); `kd_s0b_input` raises `UpstreamStall` before opening any K/D file (no more `FileNotFoundError` / `dropped_ids` refusal on a stalled layout); tests for both stalled runs, the sticky re-run and the input-callable path | `146d6b9` |
| MUST 3 | q0195: draft gets `repeat {max_runs 2400, until_log_regex "status": "pyth_live_complete"}` (the CLI already printed that status; it now also writes `pyth_live/COMPLETE.json`); before `T9_P2_start` 08:00 ET minus 35 min the job exits 75 at once (`cb8_common.idle`: idle heartbeat every 10 h so the 48-tempfail cap never trips). Because queue re-runs come about every 30 min and a checkpoint window is 10 min, a run now sleeps until a step that falls due within 35 min (`wait_until_due`), so no checkpoint is missed by queue granularity | `146d6b9` |
| MUST 4 | `rep_p_doc` raises NotNow (exit 75, nothing written, no trial line) until `COMPLETE.json` exists, now >= last session end + 2 d, and every collected session's outcomes are final; a pending session is never scored "unavailable (source)" | `146d6b9` |
| a | q0198: one run now polls a whole half session (wait for 13:05 ET when within 35 min, a tick per minute to 16:00 ET, then **Yahoo 1-minute bars per ticker once after the close**, `DONE.json` per day; a window passed unseen is `missed_window`, never back-filled); exit 75 with the idle heartbeat before then; prints `halfday_day_done` / `halfday_complete`; draft has `repeat` (max_runs 250: about 100 + 65 idle heartbeats plus day runs) and `timeout_s` 14400 (was 12600: wait up to 32 min + 175 min poll) | `146d6b9` |
| b | `feed_label` labels a 13Z print `not_measured` when the origin row's `lookback` for (market, day, outcome index) is not `read` (`unmatched` only where the hour was read and no event matched); test through `kd_s0b_input` on a small layout | `146d6b9` |
| c | `pyth_frame` returns an existing stall manifest first (sticky), so a re-run after `disjointness_unverified` can no longer overwrite it with `pyth_frame_complete`; test | `146d6b9` |
| d | q0197 `depends_on` adds q0191 (the Stage-2 k needs `results_P.json` and `results_KD.json`) | this docs commit |
| e | see M7 disclosure below | this docs commit |
| f | see CB8 failure action below | this docs commit |

**M7 disclosure (e).** For open (and long-dated) markets the Gamma `volume` used in the frame filter and in the S0b liquidity terciles is the
**fetch-time** value, not the value at the origin: selection carries extra look-ahead (volume accrued after the origin and up to the fetch date can admit
a market that was below $10k at the origin). Closed markets carry the end-of-life value (already disclosed). Neither enters a feature, a sizing rule or an
outcome; the disclosure applies to every K/D and S0b result and is stated with them. Nothing was changed.

**If CB8 q0164 / q0166 / q0168 fail (f).** q0182 is gated on all three by `depends_on` and the queue starts a job only when every dependency is `done`, so a failed
dependency leaves q0182 and its dependants queued forever (they never run on it). Manual action by the coordinator: (1) read the CB8 job log and manifest of the failed job; (2) a transient failure is
re-queued through the queue's normal retry or a new job id (same code, same inputs; never a changed rule); (3) if the CB8 output can no longer be
produced (source gone, rules refused), record the fact in the ledger and treat the dependent CB9 jobs as `not run (source)`: P, K, D and S1 are then
**not testable, counted**, and the S0 audit (q0181, q0188 through q0187) runs on its own because it does not depend on q0182. A q0182 over a substitute key file
needs a new job id, a written scientific justification and a `science-reviewer` pass; the exclusion keys are never reconstructed or relaxed to proceed.

**Deployment caveat.** The sign rules hash changed (S0b stall check, feed label) and the P rules hash changed (`pyth_frame`); the already-queued
`q0180_cb9_smoke` job stays on `seals/cb9_sign_rules_v3.json` (untouched) and verifies against the code that the host runs. **Deploy this commit range to
the collection host only after q0180 has finished** (its result is write-once), or the v3 file will refuse against the new code (exit 2, nothing written).
Every later draft uses v4 (sign) or the default v4 (P). The K/D rules hash is unchanged (`cb9_kd_rules_v2.json` verifies against current code).

**Rules v4 (written from committed code at `29bdb1f`; v1-v3 files kept, never rewritten; wallet_key_fingerprint `80ce5e81a539a570`).**

| File | file sha256 | rules_sha256 |
|---|---|---|
| `seals/cb9_sign_rules_v4.json` (`cb9-sign-rules-v4`) | `4d4bd717f42b8acf70e09039ff43d4d2c37a924893d1d091f7dbb630e8947e3f` | `881fd325c30718af7d85ad9765fee84eb85fa0b6e8f88f824a09e0ae2514c669` |
| `seals/cb9_rules_v4.json` (`cb9-rules-v4`) | `231af4ac4b26f953a0b863b5ef80c50b49ef73065dcaa79d1107e61f35010df4` | `e851cbfe54e6547c0449bdd42361eca1a83c2ff15d15f9c7330f1b968336e072` |
| `seals/cb9_kd_rules_v2.json` (unchanged) | `e2b3cb9e8904f891133e5e56541071bb6c8a0131448affbf61a6f656a2885969` | `8ee7bf366a013a87eae5a061fba788ebbbacc5945940df5de1e57510256886a1` |

Commits: code and tests `146d6b9`; rules-version bump `29bdb1f`; rules files `32eff50`. Drafts changed (section 4): q0181, q0182, q0188, q0195, q0196, q0197, q0198
(q0180 unchanged; the drafts of q0181 onward live only in this document, none is in `queue/drafts/` or `queue/jobs/`).

### 11.3 Smoke v1 result and smoke v2 (2026-10-17)

**Smoke v1 (q0180, `seals/cb9_sign_rules_v3.json`, finished 19:58Z, result `creative_batch9/smoke.json`, kept, write-once).** Criteria: `gamma_paging`,
`pmxt_heads`, `topic_pins`, `yahoo_clock` true; `receipts_v1` false and `receipts_v2` false. The receipt section: v1 era 8 receipts, 8 matched, 8 with T1 = T2,
0 unavailable; v2 era 18 receipts, 18 matched, 18 with T1 = T2, 0 unavailable; RPC 26 requests, 0 failures.

**Why it failed.** The source worked (every receipt decoded and matched, T1 = T2 on every one, no unavailable receipt, no RPC failure). The pass rule needs at
least 20 receipts and at least 18 with matched T1 = T2; v1 drew a fixed 10 markets x 2 prints per era, so at most 20 receipts were possible and any market with
fewer than 2 prints (or two prints sharing a transaction) left the era below 20. That is a sampling defect of the smoke, not evidence about the source. The v1
result is not deleted or edited and the v1 criteria values stay as recorded; it is superseded by this disclosure.

**Smoke v2 (`SMOKE_VERSION = "cb9-smoke-v2"`, seed `arepo-cb9-smoke-v2`, a fresh draw, result `creative_batch9/smoke_v2.json`, write-once on its own path).**
Only the drawing changed: markets are taken in the same seeded order (Gamma closed markets ending on the pinned day, volume >= $10k) one at a time until 20
distinct receipts (distinct by transaction hash; repeats counted in `n_duplicate_tx`) are collected, up to `SMOKE_MAX_MARKETS_PER_ERA = 40`. If Gamma returns fewer
eligible markets or the cap is reached with fewer than 20 receipts the era fails as before; `n_markets_tried` is recorded. The pass rule is unchanged (>= 20
receipts, >= 18 with matched T1 = T2), as are the per-exchange counts (M1) and the rule that more than 2 unavailable receipts means NotNow, nothing written (M2).
No threshold, gate or formula changed. Every downstream reader (`sign-audit`, `pyth-frame`, `pyth-books`, `kd-books`) now defaults to `smoke_v2.json` and
accepts only `cb9-smoke-v2` (a v1 file is a refusal). The smoke v2 job is `queue/drafts/q0180b_cb9_smoke_v2.json`; q0181 depends on it. The queued q0180
job was a v1 smoke and is not re-run.

**Rules v5 (written from committed code at `6713379`; v1-v4 files kept; wallet_key_fingerprint `80ce5e81a539a570`).** The P rules and K/D rules hashes are
unchanged (`cb9_rules_v4.json` and `cb9_kd_rules_v2.json` still verify against current code).

| File | file sha256 | rules_sha256 |
|---|---|---|
| `seals/cb9_sign_rules_v5.json` (`cb9-sign-rules-v5`) | `4cd2de5d90ae03dbdd70f95b55beb6853b235c868f50601ffcbb0073cfbf8597` | `b60a87efc2e22d32086988582f674599ad8fae1520cf8a0c4abb06aeb2c10742` |
| `seals/cb9_rules_v4.json` (unchanged) | `231af4ac4b26f953a0b863b5ef80c50b49ef73065dcaa79d1107e61f35010df4` | `e851cbfe54e6547c0449bdd42361eca1a83c2ff15d15f9c7330f1b968336e072` |
| `seals/cb9_kd_rules_v2.json` (unchanged) | `e2b3cb9e8904f891133e5e56541071bb6c8a0131448affbf61a6f656a2885969` | `8ee7bf366a013a87eae5a061fba788ebbbacc5945940df5de1e57510256886a1` |

Commits: code and tests `6713379`; rules file `e95bb94`. Drafts changed (section 4): q0181 (rules v5, depends on q0180b), q0188 (rules v5); new draft file
`queue/drafts/q0180b_cb9_smoke_v2.json`. Deployment: deploy this commit range to the collection host before q0180b runs (the v3 file refuses against the new code).
