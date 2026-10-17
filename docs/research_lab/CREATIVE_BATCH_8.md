# Creative batch 8 (CB8): Binance terminal minutes, worked-order footprints, concentrated-holder exits

`evidence_role: exploratory_historical` (CH76 on pmxt books of daily crypto Up/Down markets, 2026-04-13 to 08-10; CH69 on
the fresh `h9_flow` print fetch, May-September 2026) / `prospective` (CH70, on `/holders` snapshots collected from
2026-10-21 onwards) | status: **REVISED after challenger round 1 (ACCEPT_WITH_REQUIRED_CHANGES); not frozen.** Drafted 2026-10-17 06:45 UTC+1;
round-1 response 2026-10-17 (§9). Every change tightens or discloses; no alpha, floor, cap or threshold was relaxed.

This file turns CH76, CH69 and CH70 from `CREATIVE_HYPOTHESES_2026-10-17.md` (round 3) into declared, falsifiable tests,
and records why the other eight remaining round-3 ideas (CH62, CH64, CH65, CH68, CH72, CH74, CH75, CH78) are not in this
batch. It follows `CREATIVE_BATCH_7.md` (CB7) and `CREATIVE_BATCH_6.md` (CB6) in structure and rules. "As CB7 §x" means
that rule applies unchanged, including its challenger-round fixes; CB4's amendment A-C1 governs the day cluster way.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices.
- Test tables bind only once the CB8 declaration hash is committed (`model_specs/cb8_v1.json`, the CB8 freeze). **One
  exception:** the CH70 collection rules (§CB8-H "Collection"), which must be fixed before the first `/holders` snapshot,
  are fixed by this document and hashed into `seals/cb8_holders_rules.json` before q0162 is committed.
- **No dependence on the `T_seal` fetch window.** Every CB8 historical row predates 2026-10-01, so no CB8 fetch is
  `T_seal`-bound and none competes for the `net` lane before 2026-10-22. The only CB8 jobs that may run before `T_seal`
  are the CH70 holders smoke and the CH70 prospective collection (cpu lane, ≤ 2 rps, < 500 MB, about 30 min a day).
- Queue specs are drafts in `queue/drafts/` (§4). **CB8 uses q0160-q0176, one id per job, no letter suffixes;
  q0177-q0179 are reserved** for CB8 renumbering (checked free in `queue/jobs/` and `queue/drafts/` at drafting).

## 0. Summary, selection and scope

| Rank | Job | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB8-B** Binance terminal minutes (CH76) | in daily crypto "Up or Down" markets, once the Binance spot path makes the outcome near-certain (\|z\| ≥ 3) in the last 5 minutes, buying the favoured side at the **recorded** best ask (≤ 0.99) pays after fees (B1) | B1 (economic) | pmxt books, SCREEN weeks of 2026-04-13..08-10 | pmxt books, sealed HOLDOUT weeks (same markets' family, disjoint days) | q0161, q0164-q0166, q0169, q0170, q0174 |
| 2 | **CB8-W** worked-order footprints (CH69) | after a public two-clip same-wallet, same-side footprint, the same-side fills over the next 10-60 minutes lose money for the resting maker, so stepping aside on that side gains (W1) | W1 (economic) | `h9_flow` (fresh prints with hashed wallets), SCREEN events | `h9_flow` sealed HOLDOUT events | q0161, q0164, q0167-q0169, q0171, q0175 |
| 3 | **CB8-H** concentrated-holder exits (CH70) | a taker sell by the top holder of a token that holds ≥ half of it is cheaper for the maker to buy than a size-matched sell by anyone else in the same market (H1) | H1 (mechanism, with a binding economic route gate) | prospective `/holders` snapshots + Data API prints + complete captures, window 1 | the same collection, window 2 (after the freeze) | q0160, q0162, q0163, q0172, q0173, q0176 |
| - | CB8-F data | smoke, exclusion keys, frames, books, klines, fetch and seal | none | | | q0160-q0168 |

**Counted: 3 fixed (B1, W1, H1) + up to 3 conditional (B1-rep, W1-rep, H1-rep) = 3-6** (§2.5).

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0160 | `cb8_holders_smoke` (20 live markets, `/holders` shape and limit; counts only) | H | after the smoke code and `seals/cb8_holders_rules.json` exist (may run before `T_seal`; cpu lane) |
| q0161 | `cb8_smoke` (Data API paging and windows on worn 2026 markets; Binance archive checksums outside the B window; pmxt HEADs; counts only) | F | after `T_seal` |
| q0162 | `cb8_holders_snap` (rolling daily `/holders` snapshot, prospective) | H | after the q0160 PASS and a collector freeze check; first snapshot ≥ 2026-10-21T06:00Z |
| q0163 | `cb8_holders_prints` (rolling: windowed prints and capture marks for snapshot market-days ≥ 28 h old) | H | with q0162 |
| q0164 | `cb8_exclusion_keys` (ids and event / neg-risk / series keys of every prior sample and seal copy) | F | after `T_seal` |
| q0165 | `cb8_updown_frame` (Gamma frame of daily Up/Down markets; rule-text checks; SCREEN/HOLDOUT week split; Binance 1m archive with outcome guard) | B | after q0161 PASS, q0164 |
| q0166 | `cb8_updown_books` (pmxt book states at the checkpoints; last-15-minute prints; HOLDOUT sealed) | B | after q0165 |
| q0167 | `h9_flow_fetch` (fresh market sample, 72-h windows, all taker prints with hashed wallets; HOLDOUT events sealed) | W | after q0161 PASS, q0164 |
| q0168 | `h9_flow_seal` | W | after q0167 |
| q0169 | `cb8_census_BW` (counts only; B SCREEN only) | B, W | after q0166, q0168 |
| q0170 | `cb8_screen_B` (B1, Stage 1) | B | after the CB8 freeze |
| q0171 | `cb8_screen_W` (W1, Stage 1) | W | after the CB8 freeze |
| q0172 | `cb8_census_H` (counts only, window 1) | H | after `T8_H1_end` + 30 h |
| q0173 | `cb8_screen_H` (H1, Stage 1) | H | after the CB8 freeze and q0172 |
| q0174 | `cb8_rep_B` (B1-rep, HOLDOUT weeks) | B | only if B1 advanced |
| q0175 | `cb8_rep_W` (W1-rep, HOLDOUT events) | W | only if W1 advanced |
| q0176 | `cb8_rep_H` (H1-rep, window 2) | H | only if H1 advanced; after `T8_H2_end` + 30 h |

### 0.2 Selection and scope

**Ranking rule.** Expected value if true × prior plausibility × honest testability on data AREPO has or can fetch
cheaply, **with no dependence on the pre-`T_seal` fetch window**. External public-source joins and mechanical flow were
preferred.

**What the drafting session read or computed (2026-10-17T05:00-05:45Z).**
- Committed documents and code. `battery2.cumulative_count()` = **1,121** (§2.5). `scripts/oracle/queue_status.sh`
  (read-only): host data-dumps 9.9 GB, 8.5 GB free on `/`, `net` lane held by the `T_seal`-bound h6/h7 fetches.
- **One count-only Gamma probe** (keyless, metadata only), with closed markets whose `endDate` lies in
  `[d 15:59Z, d 16:01Z]` for each day `d` in `[2026-04-13, 2026-08-10)`, paged:
  - **825 daily "<Asset> Up or Down on <Month> <d>?" markets** on 118 of 118 days (6-7 a day): Bitcoin, Ethereum,
    Solana, XRP, Dogecoin and HYPE (118 each) and BNB (117). No window hit the offset cap; none is neg-risk.
  - All 825 descriptions match four regex flags: Binance; 1-minute candle; "12:00 ET"; 50-50 tie.
  - On three probe days, `resolutionSource` is Binance **spot** `/trade/<SYM>_USDT` for six assets and Binance
    **USDⓈ-M futures** `/futures/HYPEUSDT` for HYPE.
  - No price, outcome price, volume or closing field was printed or stored.
- **Binance reachability (keyless; dates outside the B window):**
  - `data.binance.vision` monthly 1m spot archives answer HEAD 200 with a `.CHECKSUM` file. Example:
    `BTCUSDT-1m-2026-03.zip`, 2.2 MB.
  - A spot `HYPEUSDT` archive does not exist (404), which is consistent with HYPE settling on futures.
  - `data-api.binance.vision/api/v3/klines` returned 3 rows for 2026-03-01.
  - No candle inside the B window was read: those candles determine B's outcomes.

| Idea | Decision | Reason |
|---|---|---|
| **CH76** Binance terminal minutes | **include (B), priority** | This is the cleanest external join in round 3. The outcome is a public function of a keyless source (Binance 1m candles, checksummed archive). The settlement convention is in every market's rule text (probe above). pmxt v2 holds **recorded books at the minute** for 2026-04-13 to 08-10 (`HISTORICAL_SOURCES.md` §a), so the economic check uses recorded asks, depth and fee rates, not modelled prices or CLOB history (CB6 lesson). n is about 825 market-days. Low novelty: it measures what bots leave, not whether the mechanism exists |
| **CH69** worked-order footprints | **include (W)** | Mechanical flow, testable on a fresh print fetch. Prints are a permanent public record and carry the proxy wallet, hashed in memory (`wallet_sidecar`). The fetch runs after `T_seal` with rows before 2026-10-01. The design is made **causal**: the trigger is the second clip, which a maker sees in real time, and the economic statistic mirrors CB7-X1 with a public footprint in place of a Kalshi move. The idea's "sequence" definition used future clips and is kept only as a reported descriptive |
| **CH70** concentrated holders | **include (H), prospective** | `/holders` is keyless (round-3 probe) but current-state only, so the test can only be prospective, which is allowed ("prospective collection from now on"). This is the second mechanical-flow test. The primary is narrowed to the one statistic with an economic reading: exit prints versus size-matched other sells. The presence-filter descriptives (wide states, pre-close dumps) are reported only. Power is the risk (§CB8-H MDE) |
| CH62 calendar-decided NO carry | dropped | CB1-A1 (post-end decided carry) had 57 units, below its floor. CH62's population (single markets still open more than 24 h after their own parsed deadline, with NO ask < 0.99) is a narrower sibling. Its pre-end version lives in ladders, which CB1-B could not test (52 usable ladders) and B3 already declares for fresh rungs. The tail it must avoid (late-reported events, clarifications that extend the deadline) is CB6-T's object. Re-entry: after CB6-T reports, and only if a counts-only capture census shows ≥ 300 post-deadline open single markets in 3 weeks |
| CH64 rule-divergence twins | dropped | Census-first, with no count yet. It needs both legs' rules text and a frozen ordering classifier. The cross-venue audit's 9 of 341 wording mismatches suggests twins within one venue are rare. Re-entry: once CB7's `textorig` table (text as of first sighting) has run ≥ 2 weeks, a twin census is cheap |
| CH65 ex-ante dispute predictor | dropped | Disputes are a few percent of proposals, so about 2,000 proposals are needed. The sidecar's `uma_resolution_statuses` began on 10-11 and its dispute count is unmeasured. The historical route (OptimisticOracle logs over keyless RPC) is a large `net` job. It is a cost filter, not a route. Re-entry: ≥ 50 disputes observed in the sidecar |
| CH68 post-redemption redeployment | dropped | AREPO never stores raw wallets (HMAC by design), so monitor and sample wallets cannot be re-queried on `/activity`. The 9,621-wallet cache comes from `h1_first` wallets (a worn sample) and sits in a 6.5 GB single-stream release. Destination predictability needs per-wallet pulls with little power per wallet. The mechanism is the weakest of the three flow ideas |
| CH72 fee-valley farming flow | dropped | It overlaps CB6-R (maker in 0.90-0.96 with mark-outs and hold-to-resolution) and CB4's CH41 farmer share. The fee-shape mechanism is confounded: a fee-minimising farmer can trade at any price in zero-fee markets (geopolitics rate 0), so a difference in band shares would not identify the fee mechanism. Its route is CH01's carry, whose tail is CB6-T's object. `h9_flow`'s hashed wallets could support a later descriptive |
| CH74 docket-first | dropped | Keyless access to docket-entry timestamps is not verified (the idea itself notes registration for some CourtListener endpoints), and the brief requires keyless sources. Matched court-outcome markets with a resolving order are well under 50 a year, so the test is descriptive at best and the matching is by hand |
| CH75 first-print bias | dropped | The mechanism is implausible: consensus forecasts already target the first release, so a crowd pricing "the final number" is not the default. The FRED/ALFRED API needs a key. About 300 boundary buckets in about 60 release clusters give an MDE of about 5c |
| CH78 round-strike bump | dropped | It needs a fresh crypto-ladder walk with per-strike prints. CB5-L tests CDF consistency on the same object and is sealed for CB5. "Round versus non-round" is ill-defined in ladders whose strikes are all round multiples, so the definition itself would be a forking path. Re-entry: after CB5-L reports |

**Sports and weather.** As CB7: `CB8_SPORTS_IN_PRIMARY = false`. Sports is a sampled, reported, uncounted stratum in W and
H. Weather is excluded (CB2-W's `h6_weather` and its live stage are never touched). Crypto Up/Down markets are B's
population only; W and H exclude them (`CB1_UPDOWN_RE`).

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB8 | Evidence ceiling |
|---|---|---|---|
| pmxt v2 hourly event files (`r2v2.pmxt.dev`), hour 15Z (14Z lookback only when needed) of B days, range reads by the day's Up/Down condition ids | ECONOMIC_CONDITIONS B, r4_book, J3, CB1-C (h2 pairs), CB4-N (neg-risk members, 04-30..07-02), ML-dev book features (h1) | **B Stage 1 (SCREEN weeks) and Stage 2 (HOLDOUT weeks)**. Daily Up/Down markets are in none of those populations (not neg-risk; any h1/h2 ids are dropped by key) | Stage 1 L1; Stage 2 sealed holdout (L2) |
| Binance public archive `data.binance.vision`: spot 1m klines for BTC, ETH, SOL, XRP, DOGE and BNB (USDT) and USDⓈ-M futures 1m `HYPEUSDT`, months 2026-04..08 (**new**, q0165) | none | B features (spot path, strike, σ) and the outcome cross-check. Settlement candles go to the guarded file only | - |
| Gamma frame of daily Up/Down markets (**new**, q0165; ids, tokens, question, `resolutionSource`, description flags and sha256, `endDate`, `createdAt`, `closedTime` as status; outcomes only in `outcomes_guarded.csv.gz`) | the 2026-10-17 count probe (counts only) | B population | - |
| Data API taker prints of B market-days in `[t_end − 15 min, t_end + 2 min]` (**new**, q0166) | none | B fill-realism descriptive only | - |
| `history/h9_flow` (**new**, q0167): about 1,800 markets (1,500 non-sports + 300 sports), one 72-h window each in `[2026-05-01, 2026-10-01)`, every taker print with an HMAC wallet hash | none | **W Stage 1 (SCREEN events) and Stage 2 (HOLDOUT events, sealed)** | L1 / L2 (sealed holdout) |
| `research_lab/creative_batch8/holders/` (**new**, q0162/q0163): daily `/holders` top-20 per token (hashed wallets, amounts), windowed taker prints of snapshot market-days (hashed wallets), capture marks | none | **H Stage 1 (window 1) and Stage 2 (window 2, after the freeze)** | L1 / L2 (out-of-time, post-freeze) |
| Complete captures (host), read only by q0163 for the touch of snapshot markets in `[h, h + 30 h]` | E-series, SB2, CB1-CB7 | H marks and the OI field | - |
| `cross_venue_live/` (E009/E010), `surprise_live/` (E011) | registered experiments | **never read** (runner refuses the roots) | - |
| `h1_first`, `h2_main`, `h3_power` | worn, h3 retired | **not read**, except their sha256-pinned `sample.csv.gz` id lists, which feed the exclusion keys | - |
| `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, `h8_tail`, `h8_text`, `h8_geo`, CB5 fetches, `cross_venue/` C1 legs | SB2, CB1-CB7 | **not read** (runner refuses). Committed seal copies and listings are read for **ids only** (exclusion) | - |
| `cb1_extract/` .. `cb7_extract/`, `cb3_followup/`, `cb6_followup/`, `live_trades/`, `trade_samples/` | CB1-CB7, monitor, E007 | **not read by any CB8 code path** | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T8_draft` | 2026-10-17T05:45Z | first draft; no CB8 quantity computed (probes in §0.2 are counts only) |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 seal boundary. **No CB8 fetch is bound to it.** B rows end 2026-08-10; W rows end before `T8_hist_end`; H data are prospective |
| `T8_hist_end` | 2026-10-01T00:00Z | every `h9_flow` print has `ts < T8_hist_end` (frame `end_at < T8_hist_end`); before every live CB window and every SEALED-H4 origin |
| B days | `d ∈ [2026-04-13, 2026-08-10)` minus the pmxt gap `[06-12, 06-18)`; `t_end(d) = d 16:00:00Z` (12:00 EDT; every B day is in EDT) | settlement candle opens at `t_end`, closes at `t_end + 60 s` |
| B split | ISO weeks 16-32, paired (16,17), (18,19) … (30,31); in each pair one week is SCREEN and one HOLDOUT by a seeded coin (`arepo-cb8-updown-split`); week 32 by its own coin | written into the rules file before any pmxt or kline read |
| W split | Gamma events of the `h9_flow` sample, SCREEN/HOLDOUT 50/50 by a seeded hash of the event id (`arepo-h9-split`) | at sampling, before any print request |
| `T8_H1_start` | the first complete capture ≥ **max(2026-10-21T06:00Z, q0162 deployment + 2 h)**, pinned in a committed file | first H snapshot (after the J4-R window, `seals/j4r_window.json`) |
| `T8_H1_end` | `T8_H1_start` + 21 d | end of H window 1 |
| `T8_H2_start` | **max(`T8_H1_end`, CB8 freeze commit + 2 h)** | H window 2 begins only after the freeze. Snapshots between the windows are collected, never analysed (counted) |
| `T8_H2_end` | `T8_H2_start` + 21 d | collection stops at `T8_H2_end` + 30 h |
| `T8_H_collect_max` | `T8_H1_start` + 63 d (pinned with `T8_H1_start`) | **freeze-slip rule (round 1, should-change):** q0162/q0163 never collect after this date. If `T8_H2_start + 21 d > T8_H_collect_max` (the freeze slipped by more than 3 weeks after `T8_H1_end`), window 2 cannot complete: H1-rep is **"not run (freeze slip)", counted** if H1 advanced. The window is never shortened or extended |

### 1.3 Sealed and untouched data (named)

- **Refused run ids and roots.** `run_cb8.py` refuses `h1_first`, `h2_main`, `h3_power`, `h4_seal`, `h5_cb1`,
  `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, `h8_tail`, `h8_text`, `h8_geo`, every CB5 history run, every
  path under `cb1_extract/` to `cb7_extract/`, `cb3_followup/`, `cb6_followup/`, `cross_venue/`, `cross_venue_live/`,
  `surprise_live/`, `live_trades/` and `trade_samples/`. It writes only under `research_lab/creative_batch8/` and
  `history/h9_flow/`.
- **Exclusion keys (q0164).** The keys cover every Gamma event id, `negRiskMarketID` and series id of every market id
  found in the following, all sha256-pinned in the manifest:
  - the h1/h2/h3 `sample.csv.gz` id lists;
  - every committed seal copy under `docs/research_lab/seals/` (h5, h5_ladders, h6, h7, h8_tail, h8_text, h8_geo, as
    committed at q0164's start);
  - every CB5 sample listing;
  - the C1 Polymarket legs (`cross_venue/matches.json`).

  Keys come from a Gamma id lookup (≤ 50 ids per request, `closed=true` retry, parse guard that keeps ids and keys
  only). A seal copy that is not yet committed (a fetch that is still running, or `not_run_deadline`) is recorded as
  "absent at q0164". Queue ids are terminal once done, so q0164 does not re-run. Instead, **seal-time drops** apply: the
  final stage of q0166 (B HOLDOUT seal) and q0168 (`h9_flow` seal) re-read every seal copy committed by then. They drop
  by id **and** by key (light Gamma lookup by id, ≤ 2 rps, same parse guard), recording `DROPPED_*` blocks; sealed files
  are never edited. If more than 2% of exclusion ids lack metadata, disjointness is "unverified", and W1 and B1 are "not
  testable" (p = 1, counted).
- **Drops.** B and W frame markets that share an id or key with the exclusion set are removed **before** the split and
  before sampling, counted by key type. H is prospective (markets live after 2026-10-21) and needs no historical
  exclusion. Its markets may overlap live CB3-CB7 populations in calendar time. CB8 reads none of their tables, and H's
  statistic (holder-exit mark-out contrast) cannot reveal theirs (disclosed, as CB7 §1.3 SEALED-P).
- **SEALED-B (HOLDOUT weeks).** q0166 writes the HOLDOUT book states, prints and kline features into
  `creative_batch8/updown/holdout/` with a listing sha256. Seal copy: `seals/cb8_updown_holdout_SEAL.json`, committed
  before q0169. The census reads SCREEN units only, plus HOLDOUT **file and day counts**. No CB8 path opens a HOLDOUT file
  before B1 advanced and its Stage-1 result is committed.
- **SEALED-H9 (W HOLDOUT events).** Same rule: `history/h9_flow/holdout/`, `seals/h9_flow_SEAL.json` committed before
  q0169. The census reads HOLDOUT file and event counts only, never HOLDOUT prints.
- **Outcome guard (B).** Gamma `outcomePrices` go only to `outcomes_guarded.csv.gz`. Binance **settlement candles** (the
  1m candle opening at `t_end(d)`) go only to `klines_settle_guarded.csv.gz`. The feature file holds candles with
  `open_time < t_end(d)` and the strike `K_d` (the settlement close of day `d − 1`).
  - **Disclosed:** consecutive strikes `K_d`, `K_{d+1}` determine day `d`'s outcome. No CB8 code path compares
    consecutive strikes (unit test), and the census writes counts only. A crypto day's noon-to-noon direction is
    public knowledge, so the guard protects the code path, not a secret.
- **E009/E010/E011.** Never opened. No CB8 statistic uses a Kalshi series. H reads complete captures from
  2026-10-21 onwards, inside E011's calendar window (to 2026-11-10), for a different statistic. CB8 reads none of E011's
  files or outputs (disclosed).
- **h4_seal unchanged.** No CB8 row lies at or after `T_seal` except H's prospective data, which are CB8's own collection
  and never h4 data (as CB4-C to CB7, disclosed).
- **J4-R window.** No CB8 row lies in `[2026-10-16, 2026-10-21)`: B ends 08-10, W before 10-01, and H starts ≥ 10-21T06:00Z.

### 1.4 Rules files

- `seals/cb8_holders_rules.json` (before q0160/q0162) fixes the H collection frame, sample sizes and seeds, the
  `/holders` request form, the print window, the mark rule and the concentration rule. It carries a `rules_sha256` and
  the source hash of every rule function.
- `seals/cb8_rules.json` (before q0161/q0164-q0167) fixes:
  - B: the question and description regexes, the `resolutionSource` parser, the symbol map, the week split and its
    seed, the checkpoints, the z rule, the buy cap, and the freshness and depth rules;
  - W: the `h9_flow` frame, the sample sizes, the per-event cap, the window rule, the seeds, the split, the clip, trigger,
    skip and mark rules;
  - the smoke criteria.

  Fetchers refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any B, W or H read.**
- **HMAC key continuity (round 1, item 6).**
  - Both rules files pin `wallet_key_fingerprint` = the first 16 hex characters of
    `HMAC-SHA256(key, "arepo-cb8-wallet-key-fingerprint-v1")`, computed once on the host from the existing
    `~/.arepo/wallet_hash_key`. The fingerprint is not the key.
  - Every CB8 job that hashes wallets (q0160, q0162, q0163, q0167) loads the key through a **strict loader** that
    **refuses (exit 2) if the key file is missing, unreadable or mode-unsafe**. It **never creates a key**:
    `wallet_sidecar.load_or_create_key` would silently create a new one and break every join.
  - The job recomputes the fingerprint and refuses on mismatch. It writes the fingerprint into its manifest.
  - Census and analysis refuse any CB8 file whose manifest fingerprint differs from the pin. H's holder-to-print join is
    valid only within one fingerprint.

## 2. Common rules (deltas from CB7 §2 and CB4 A-C1)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| B1 | buy the favoured token at the **recorded** pmxt best ask `a` at the checkpoint; taker fee `f(a) = r·a·(1 − a)`, `r = max(fee_rate_bps/10^4 of that token's latest pmxt event ≤ t, economics.DOCS_CATEGORY_RATE["crypto"] = 0.07)`. Taking the max means no fee era (the 07-10 fee step, or a fee-free period) can make B cheaper than the docs rate; the recorded-rate version is reported. `net = Y_fav − a − f(a)` per share; held to settlement (minutes) |
| W1 | resting maker, fee 0. Per filled share, mark-out at a recorded print price **plus the rebate the skip forgoes**: `ρ_cat · r_cat · p(1 − p)` for prints on or after 2026-03-30, else 0 (as CB7-X1; makes W1 harder to pass) |
| H1 | resting maker who bought from the sell, fee 0. Contrast of mark-outs at recorded print prices; **no rebate** in the primary or the route gate (conservative); the with-rebate version is reported |
| Binding cost robustness | B1: +0.75c on `a`. W1: the alternative mark (§CB8-W). H1: the next-but-one capture as the mark (§CB8-H) |

### 2.2 Clocks

- **Binance.** A 1m candle `[o, o + 60 s)` is usable at `t` iff `o + 65 s ≤ t` (5-s publication allowance). The
  settlement candle opens at `t_end`.
- **pmxt.** An event is used at `t` iff both `timestamp` and `timestamp_received` are ≤ `t` (loader rule). Crossed
  states are ineligible and never repaired.
- **Data API prints.** Venue `timestamp`. A condition at `t` uses prints with `ts < t`.
- **`/holders`.** The snapshot time `h` is the request-sent time, and the response is taken as holdings at `h`. API lag
  versus the chain is unknown; it is disclosed, and the smoke records response timing.
- **Captures.** Their own `received_utc`.
- `closedTime` is never a population condition or an anchor (status field only, as CB7 §2.2).

### 2.3 Uncertainty and decision rule

As CB7 §2.3, with CB4 amendment A-C1 for the day way:
- Unweighted estimates are primary.
- One-sided p = the max over the declared cluster ways.
- CI by 2,000-draw cluster bootstrap (seed 818).
- Small-G rule: G ≥ 30 CR1; 15 ≤ G < 30 CR2 with t(G − 1) and Webb wild bootstrap (9,999 draws).
- An event or wallet way with G < 15 → "not testable", p = 1, counted.
- **Day way under A-C1:** it enters the max iff G_day ≥ 15. Otherwise the leave-one-day-out sign rule binds.
- The top-5 robustness drops the 5 largest events and, separately, the 5 largest days.
- Testability otherwise needs ≥ 100 units and ≥ 30 clusters in the event way.
- An "unknown", "unverified" or "inconclusive" gate never counts as met.

Cluster ways: **B** market-day (the event; each daily market is its own event) and UTC day. **W** Gamma event, UTC day of
the print, and trigger wallet hash. **H** Gamma event, UTC day of the exit, and holder wallet hash.

- **Stage 1 (B1, W1, H1).** Advance iff all of these hold:
  - one-sided p < 0.01;
  - the §2.4 floor is met;
  - every binding placebo, robustness check and gate holds.

  A BY label (q = 0.10 over `battery2.cumulative_count()`) is attached as triage only. A Stage-1 batch-Holm label
  (one-sided α = 0.01, k1 = 3) is reported.
- **Stage 2 (B1-rep, W1-rep, H1-rep).** Holm at one-sided α = 0.05 over all CB8 tests reaching Stage 2 (k ≤ 3), each in
  its Stage-1 direction. k is fixed when the last Stage-1 result is final; early finishers are judged against α/k.
  Floor, binding robustness and placebos as Stage 1.
  - Labels: B1-rep and W1-rep pass = "sealed same-calendar holdout replication (L2)". H1-rep pass = "out-of-time
    replication on post-freeze data (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| B1 | economic | net ≥ +0.5c per share bought **and** the day-unit tail gate (§CB8-B), which at about 56 traded days requires a mean margin of about ≥ 8.4c |
| W1 | economic | mean mark-out of the skipped fills (plus forgone rebate) ≤ −0.5c per share; route gate on kept fills (§CB8-W) |
| H1 | mechanism + economic gate | contrast ≥ +0.5c per share; route gate: exits' own mean mark-out ≥ +0.5c (§CB8-H) |

### 2.5 Counting (M3 rule)

- Every counted test writes one `trials.jsonl` line via `provenance.append_trial`:
  - kinds `cb8_test` (Stage 1) and `cb8_replication` (Stage 2);
  - `ml_explain` count lines `creative_batch_8:B`, `creative_batch_8:W` and `creative_batch_8:H` (`n_tests`);
  - `cb8_descriptive` (EXCLUDE) for the census, gates, strata, the continuation and reversal descriptives, the presence
    filters and every reported variant;
  - placebo lines `evidence_role: "placebo"`, count 0.
- New `battery2.KIND_RULES` entries: `cb8_test` and `cb8_replication` EXCLUDE ("counted by the matching
  `creative_batch_8:*` count line"), and `cb8_descriptive` EXCLUDE. Unknown kinds still raise. A unit test runs the
  counter on the real `trials.jsonl`.
- **Cumulative count at drafting.** `battery2.cumulative_count()` on the Mac working tree (`battery2-count-v1`) returned
  **1,121** at 2026-10-17T05:40Z. This is a lower bound: the host appends its own lines, and CB6/CB7 lines are still to
  come. Every counting CB8 run first runs the host union step (`union_jsonl.py`) and records the post-union value.
- **CB8 adds 3 fixed tests (B1, W1, H1) and up to 3 conditional ones (B1-rep, W1-rep, H1-rep): 3-6 tests.**
- Tests behind a failed or unknown gate (GB, GW, GH, the smoke, disjointness, the source checks) are "not testable" or
  "not run" (p = 1) and are **still counted**.

### 2.6 Placebos and robustness

Design rule as CB7 §2.6. Every binding placebo names the alternative under which the test would advance. Calibration
placebos are judged on the p threshold alone (floors off). Seeds 8181-8186.

- **B1 break-even calibration placebo (binding).**
  - Construction: traded units kept; `Y' = 1{U_d < a + f(a)}`, with **one uniform per UTC day shared by every unit of
    that day** (comonotone across assets and checkpoints: the strongest within-day dependence). The expected net is 0.
  - Run: B1's p condition and the tail gate on 200 draws (seed 8181); **advance rate ≤ 1.5%**.
  - *Alternative guarded:* with a rare-loss payoff, CR1 p-values and the tail bound are anti-conservative at the
    realised number of losing days.
- **B1 certainty attribution (binding for crediting the Binance join).**
  - B1_low: the same rule on units with \|z\| ∈ [1, 3), buying the **market favourite** (the token with the higher
    mid) at its ask ≤ 0.99.
  - "Binance certainty" is credited only if `B1 − B1_low ≥ |B1| / 2`.
  - *Alternative:* the gain is a terminal favourite-longshot bias that the price alone identifies.
  - A failure leaves an advance standing, labelled "terminal favourite bias, not a Binance lead".
- **W1 time-shift calibration placebo (binding).**
  - Construction: per market, trigger times are shifted circularly within its 72-h window by an offset uniform in
    `[6 h, 66 h]`, independently per market and draw. Skip windows keep their lengths.
  - Run: W1 on 200 draws (seed 8182), p only; **≤ 1.5%**.
  - *Alternative:* burst-shaped windows share one future mark across many prints, so the clustered p is
    anti-conservative.
- **W1 wallet attribution (binding for crediting "footprint").**
  - W1_pseudo: triggers from **pseudo-pairs**, two consecutive same-side clips by *different* wallets that meet the
    same gap, size and notional rules. Skip windows run as W1 but extend on any same-side clip.
  - "Worked-order footprint" is credited only if `W1 − W1_pseudo ≤ −|W1| / 2`.
  - A failure leaves an advance standing, labelled "post-burst fills adverse whoever trades: a burst rule, not a
    footprint rule".
- **H1 matched-pair label-shuffle calibration placebo (binding).**
  - Construction: within each matched (exit, control) pair, the labels are swapped with probability 1/2; one draw per
    **holder × market-day** block applies to every pair in the block.
  - Run: H1's p condition on 200 draws (seed 8183), floor off; **≤ 1.5%**.
  - *Alternative:* one holder's many clips share marks, so the clustered p is anti-conservative.
- **H1 concentration attribution (binding for crediting "concentration").**
  - H1_low: the same contrast for rank-1 exits with `c < 0.2`.
  - Credited only if `H1 − H1_low ≥ |H1| / 2`.
  - A failure leaves an advance standing, labelled "top-holder exits are cheap whatever the concentration".

**Binding robustness for any advance or pass:**
- (i) The cost robustness of §2.1 keeps the sign. B1 keeps net > 0. W1 and H1 keep the sign and at least half the
  magnitude.
- (ii) The test still meets its p threshold and floor without the top 5 event clusters, and separately without the
  top 5 days, by absolute contribution (A-C1 point 4).
- (iii) Unweighted and size-weighted estimates agree in sign: B by depth at the ask, capped at 2,000 shares; W and H by
  print size.
- (iv) **Sign by month.** The estimate has the declared sign in ≥ two thirds of months with ≥ 30 units (B), ≥ 500
  skipped prints (W), or ≥ 50 pairs (H; H windows span 2 months, so this check is reported, not binding).
- (v) The declared worst case for unavailable units keeps the sign and the p threshold.
- (vi) **Latency.**
  - B (round 1, item 4): the unit fills at `a* = max(a_t, a_{t+10 s})` only if the state at `t + 10 s` still offers ≥ 5
    shares at prices ≤ `a*` and `a* ≤ 0.99`; otherwise it does not fill in this check (counted).
  - W: reaction 300 s instead of 60 s.
  - H: exits counted only from `h + 15 min`.
  - Each keeps the sign and ≥ half the magnitude, and B also keeps the tail gate.
- (vii) **B only.** Excluding HYPE (futures source) keeps the sign and p threshold. σ from 30 instead of 60 candles
  keeps the sign and ≥ half the magnitude.

Reported, not binding:
- B: per checkpoint and per asset; at `t_end − 10 min`; with \|z\| ≥ 2 and \|z\| ≥ 4; recorded-rate fees; opportunity
  rate (traded / eligible); median depth; paper dollars per day at the recorded depth; fill realism (share of traded
  units with a taker BUY print of the favoured token at price ≤ `a` in `[t, t + 60 s]`).
- W: continuation probability; post-run reversal R; lead-implied split (spread captured versus drift, as CB7-X); the
  sports stratum; 1-h horizon.
- H: c-tercile table; with-rebate version; exits by rank-2..3 holders; wide-state frequency and pre-close dump size by
  concentration tercile (the idea's presence-filter targets); sports stratum.

### 2.7 Pre-freeze census (counts only; q0169 for B and W, q0172 for H)

An outcome guard drops outcome fields before population code runs, each family gets a field-restricted accessor, and a
unit test asserts that no census path receives a target field. **No net, mark-out, contrast or outcome is computed.**

- **B (SCREEN only; HOLDOUT file and day counts only).**
  - Frame counts by asset; rule-text failures; key drops; days lost to the gap or to missing or corrupt hours.
  - Eligible units by checkpoint and \|z\| bin; fresh, crossed and halted-book counts; traded units (ask ≤ 0.99, depth ≥
    5 shares); days and market-days with ≥ 1 traded unit; median depth.
  - Binance–Gamma **status** consistency: the share of markets with `closed = true`. Outcome agreement is checked only at
    analysis.
  - The B1 MDE from these counts.
  - The pmxt coverage audit result (q0166 stage 1). Source-unavailable market-days by asset and week.
  - **Gate GB:** ≥ 100 traded units, ≥ 50 market-days and ≥ 15 days with a traded unit (SCREEN). On failure, B1 is "not
    testable", counted, labelled as follows (round 1, item 3):
    - with the audit PASS and ≥ 80% of SCREEN market-days source-available: "no terminal opportunity at the minute
      scale", a descriptive answer to CH76;
    - otherwise: "source unavailable".
  - The number of traded days, and the margin the day-unit tail gate would require at that count (a function of n only,
    no outcome).
- **W (SCREEN; HOLDOUT file and event counts only).**
  - Frame, filter and key-drop counts; capped days; prints per market-day.
  - Triggers, skip windows, S, S′ and N print counts; two-sided mark availability at +2 h; event, day and
    trigger-wallet clusters.
  - The W1 MDE.
  - **Gate GW:** ≥ 2,000 S prints with a mark, ≥ 300 skip windows, and ≥ 30 events, 30 days and 30 trigger wallets.
- **H (window 1 at `T8_H1_end` + 30 h).**
  - Snapshots per day; markets with `c ≥ 0.5`; rank-1 exits; exits with a matched control and both marks; events,
    days and holders.
  - OI-inconsistency share (`OI < Σ top-20`); missed days.
  - The H1 MDE.
  - **Gate GH:** ≥ 150 matched exits with marks, ≥ 50 events, ≥ 15 days and ≥ 30 holders. Fail → H1 "not testable",
    counted. **No window extension.**
- MDEs are recomputed from these counts and are never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collector. Queue rules as CB7 §2.8: one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, an address cap of 2 × `mem_mb`, and the 02:45-05:30 UTC blackout for `mem_mb ≥ 500`.
  Never two multi-GB jobs at once; none of CB8's is multi-GB.
- **Before `T_seal`.** Only two CB8 jobs may run, both on the `cpu` lane:
  - q0160 (about 20 requests);
  - q0162/q0163 once deployed: about 1,800 `/holders` plus about 2,500 print requests a day at ≤ 2 rps, about 35 min a
    day, mem ≤ 500 MB.

  **Nothing CB8 enters the `net` lane before 2026-10-22.**
- **After `T_seal` (`net` lane, priorities 44-50, behind CB7's q0146 and CB4's pmxt jobs where those are queued).**

  | Job | Work | Ingress / wall | Stored |
  |---|---|---|---|
  | q0161 | smoke | about 60 requests | - |
  | q0164 | exclusion keys | about 1,000 requests | ≤ 0.01 GB |
  | q0165 | frame | about 1,300 Gamma requests | ≤ 0.01 GB |
  | q0165 | Binance archive | 35 monthly zips (6 spot symbols + HYPE futures × 5 months), about 80 MB, `.CHECKSUM`-verified, parsed in memory | ≤ 0.02 GB |
  | q0166 | pmxt | about 111 days × hour 15Z (14Z lookback only when a token has no event before the checkpoint), range reads by ≤ 7 condition ids; about 0.5 GB ingress per hour read (`HISTORICAL_SOURCES.md`, CB4 §2.8). **Ingress cap 90 GB**, including about 10 GB for the round-1 coverage audit (hour 13Z of 20 seeded days, counts only, first stage); days processed in a seeded order alternating SCREEN and HOLDOUT, so a cap truncates both evenly (unprocessed days unavailable, counted). About 2-4 h wall in 85-min chunks, mem ≤ 1.5 GB | ≤ 0.02 GB |
  | q0166 | prints | about 825 print requests | (included above) |
  | q0167 | `h9_flow` | about 700 Gamma frame requests + about 10k print requests (1,800 markets × about 3.1 days × about 1.8 pages) ≈ 50 min at 4 rps | ≤ 0.15 GB |
- **Disk guard.** Every CB8 data job exits 75 when data-dumps + its output cap > 12.5 GB (as CB6/CB7). CB8 output caps
  total ≤ 0.4 GB:

  | Output | Cap |
  |---|---|
  | holders | 0.20 GB |
  | `h9_flow` | 0.15 GB |
  | updown | 0.04 GB |
  | other | 0.01 GB |

  Each data-job commit records the data-dumps size and the margin. The precondition never changes retention.
- **Network etiquette.** As CB7: shared `Limiter`, yield to the live collector, 429 / `Retry-After` back-off, stop on
  repeated 429, collector-health stop. pmxt range reads use the existing `RangeFetch`. Binance archive requests ≤ 2 rps.
- **Stop rules.** 10 CPU-hours per family. A job that fails twice for the same non-transient reason stops and is
  recorded. A null is "not detected at MDE x". **No re-screen of a failed CB8 test** with altered checkpoints, z
  thresholds, caps, trigger rules, windows, horizons, concentration thresholds or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → selection by gates, placebos and robustness → replication (Stage 2) → separate prospective
confirmation (Stage P) → economic validation at recorded prices.
- **Stage P-B.** A receipt-timed terminal poller: the books of the day's Up/Down markets every 10 s from
  `t_end − 10 min`, plus the Binance REST klines. B1's rule is applied in real time at recorded asks. For 2026-11-02 to
  2027-03-08, `t_end` is 17:00Z (EST).
- **Stage P-W.** The trigger rule run live on the Data API print stream with a paper touch maker on the sweep-recorded
  book.
- **Stage P-H.** A third holders window under its own registration, using a sweep-recorded bid for the maker.

---

## 3. Tests

### CB8-B: Terminal-minute certainty in Binance-settled daily Up/Down markets (CH76)

**Question.** In the last five minutes before the 12:00 ET settlement candle opens, when the Binance spot path already
makes one side near-certain, does the recorded Polymarket ask on that side leave a gain after fees for a taker who buys
it and holds to settlement?

**Mechanism.** The payoff is a digital option on a public price, seconds to minutes from expiry. Reward and
market-making bots quote around the last mid. A stale ask on the near-certain side is free money until someone takes it.
The settlement convention may also be misread: the 12:00 candle's close is known only at 12:01:00 ET. The test measures
what was left, not whether bots compete.

**Why new / overlap.** CH30 (lifetime Black-Scholes value) was never tested. Binance has never been joined to Polymarket in
AREPO. The `CROSS_VENUE_STUDY.md` lead method (lagged 10-minute change correlation) measures a lead over a market's life;
here the payoff is deterministic at a known clock, so a threshold rule at recorded asks is the direct economic test. No
CB1-CB7 population contains daily Up/Down markets (CB6/CB7 exclude them explicitly).

**Population and frozen selection rules (q0165; no outcome, price or volume used).**
1. Gamma closed markets with `endDate` in `[d 15:59Z, d 16:01Z]` for each B day.
2. The question matches `^(Bitcoin|Ethereum|Solana|XRP|Dogecoin|HYPE|BNB) Up or Down on [A-Z][a-z]+ \d{1,2}\??$`, with
   two outcomes.
3. The description contains all four frozen flags: Binance; 1-minute candle; `12:00` and `ET`; the 50-50 tie rule.
3a. **Strike clause (round 1, item 5).** Both frozen regexes must match:
    - `UP_RE`: `resolve to "Up" if the "Close" price for the Binance 1 minute candle for ([A-Z]+/USDT) ([A-Z][a-z]{2} \d{1,2} '\d{2}) 12:00 in the ET timezone \(noon\) is lower than the final "Close" price for the ([A-Z][a-z]{2} \d{1,2} '\d{2}) 12:00 ET candle`;
    - `DOWN_RE`: the same with "Down" and "higher".

    Their captured groups must be identical (symbol, strike date, settlement date), and the dates must parse to
    **strike date = d − 1** and **settlement date = d**. Failures are excluded and counted.
    - The regex was written from the rule text of an out-of-window market (Bitcoin, 2026-03-02).
    - A counts-only check on the 825 window markets matched 825 of 825 (script
      `probes/cb8_design_20261017/updown_strike_clause_probe.py`; description text only, no price or outcome field).
4. `resolutionSource` parses to a Binance spot pair (`/trade/<SYM>_USDT`) or a USDⓈ-M future (`/futures/<SYM>USDT`),
   and the symbol matches the asset map. Failures are excluded and counted.
5. Exclusion ids and keys are dropped.
6. Days with the pmxt hour 15Z missing or corrupt are unavailable for all their markets (counted, never replaced).

**Declared features (Binance, causal).**
- `K_d`: the close of the 1m candle opening at `t_end(d − 1)` (yesterday's settlement close, the strike).
- `S_t`: the close of the latest candle usable at `t`.
- `σ_t`: the SD of the 1m log returns of the 60 candles ending at that candle; ≥ 55 present, else the unit is unavailable.
- `m`: the number of 1m returns still to come up to the settlement candle's close, `(t_end + 60 − close(latest usable))/60`.
- `z_t = ln(S_t / K_d) / (σ_t·√m)`. The favoured side is Up if `z_t > 0`, Down if `z_t < 0`.
- Checkpoints `t ∈ {t_end − 300 s, t_end − 120 s, t_end − 60 s}`; `t_end − 600 s` is reported only.

**Book at `t` (pmxt).** The reconstructed state of the favoured token:
- best ask `a`, its size, size within 1c, best bid, tick size, `fee_rate_bps`, and the venue time of its latest event;
- **fresh** iff the token's latest event (any type) has a venue timestamp ≥ `t − 120 s`;
- **halted** iff no event after `t_end − 600 s` and no ask (reported);
- crossed → ineligible.

**Units.**
- (market-day, checkpoint) is eligible iff the features are available, \|z_t\| ≥ 3, and the book is fresh and not crossed.
- **Traded** iff `a ≤ 0.99` and the size at `a` ≥ 5 shares (the buy cap is a price rule fixed now: ≥ 1c gross per
  share before fees).
- Eligible units with `a > 0.99` or no ask are "no trade" (counted; the opportunity rate is reported).

**Target.**
- `Y_fav` from the **Gamma official outcome** (guarded): 1 if the favoured side won, 0 if it lost, 0.5 on a 50-50
  resolution.
- **Source check (round 1, item 2):** the Binance-computed outcome, comparing the settlement candle's close with
  `K_d`.
  - **Diagnostic only.** Units that disagree **stay in the P&L** with the Gamma official outcome, which is what pays.
    They are counted and listed.
  - Disagreement on more than 2% of market-days → B "not testable (source)".

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **B1** | economic | traded unit (SCREEN weeks; Stage 2: HOLDOUT weeks) | mean `Y_fav − a − f(a)`, cents per share, unweighted | > 0 |

**Gates.**
- Floor: net ≥ +0.5c.
- **Tail gate (binding; round 1 item 1: redefined in day units, kept binding).**
  - The unit is the **traded day**. The day's paper book buys one share at each of its traded units.
    - `W_d` = the day's gain if nothing loses: `Σ_u (1 − a_u − f(a_u))`.
    - `L_d` = the day's loss if everything loses: `Σ_u (a_u + f(a_u))`.
    - All of the day's units are assumed to lose together on a losing day (worst case, below).
  - `q_U` = the one-sided 99% Clopper-Pearson upper bound of the share of traded days with ≥ 1 losing unit (n = traded
    days, k = losing days).
  - The gate requires `mean_d(W_d)·(1 − q_U) − mean_d(L_d)·q_U ≥ 0`, with `mean_d` over all traded days. Both terms are
    per-day amounts in the same units, so probability and payoff now refer to the same unit (the draft mixed a per-day
    probability with per-unit payoffs).
  - **Why the day, decided data-blind.** Reversals in the last minutes are driven by a common crypto price shock, and
    1-minute returns of BTC, ETH and the other assets are strongly correlated. So the seven markets and three checkpoints
    of a day are not independent trials, and a bound on market-days would treat one shock as many. A bound that is
    independent of the distribution (Hoeffding or empirical Bernstein on day P&L) is looser still at n ≈ 56. No bound in
    market-day units was adopted.
  - **Consequence, stated plainly.** With about 56 traded days per stage, `q_U` = 0.079 at zero losing days, 0.113 at one
    and 0.142 at two. Because `W_d / L_d` ≈ (mean margin)/(mean `a + f`), the gate needs a **mean gross margin
    `1 − a − f(a)` of about 8.4c per share with no losing day, about 12.5c with one and about 16c with two** (at
    `a + f ≈ 0.985`). This makes B1 a test of **gross terminal staleness only**: it can pass only if the asks recorded
    when the outcome is near-certain sit around ≤ 0.91 on average. A real 1-3c residual cannot pass in 56 days, whatever
    its p. Showing one needs Stage P's day count (about 300 days: about 1.5c at zero losing days). Alpha, the floor and
    the buy cap are unchanged.
- p < 0.01 (Stage 1) with the §2.3 ways (market-day; day under A-C1).
- Placebos and robustness as §2.6.
- Sign by month: binding with ≥ 30 traded units per month.

**MDE (assumptions; the census replaces them).**
- Per stage, about 56 days × 7 assets × 3 checkpoints ≈ 1,180 units, of which about 1,000 are available.
- \|z\| ≥ 3 holds for most of them: with daily moves of 2-3% and remaining σ about 0.1-0.2%, roughly 80%.
- The traded share `f_tr` is unknown.
- Checkpoints of one market-day share the outcome, so the effective n is about the traded market-days.
- With a reversal rate near 1%, the net SD per market-day is about 10c and the day-way deff about 1.5. The MDE (one-sided
  α 0.01, power 0.8) is then **about 2.1c at f_tr = 1 and about 3c at f_tr = 0.5**.

**Binding constraint (round 1, item 1).** The day-unit tail gate dominates the p-based MDE. At about 56 traded days, B1
can advance only if the mean margin is **≥ about 8.4c per share** (more with any losing day). A 0.5-3c residual is
reported as "below the tail-gate requirement", not as evidence.

**Costs by era.** The pmxt window includes the CLOB V2 switch (about 04-28), the tick change (07-02) and the fee step
(07-10). Fees use the conservative max of recorded and docs rates on every date. Strata before and after 07-02 are
reported, not binding: both stages span them because of the alternating-week split.

**Leakage.**
- `z` uses candles usable before `t` only. The strike is yesterday's public close.
- Outcomes and settlement candles are guarded. The book uses events with both clocks ≤ `t`.
- The week split is seeded before any read.
- `endDate`/`t_end` is fixed by the market template (daily noon ET), so no early-resolution look-ahead exists. A market
  whose `endDate` is not 16:00Z on its day is not in the frame.

**Stage 2 (HOLDOUT weeks).** Identical rule, checkpoints, cap, gates (including the day-unit tail gate at the HOLDOUT
day count), ways and placebos. It opens only after B1 advanced and its Stage-1 result is committed.
- **Disclosure (round 1, should-change).** The alternating-week holdout is a **selection guard only**. It shares the
  calendar, the regimes and the bot population with SCREEN and protects against choosing the rule on the data. It is not
  an out-of-time or regime check; Stage P-B is.

**pmxt coverage audit (round 1, item 3; first stage of q0166; counts only).**
- pmxt subscription completeness is unaudited (`HISTORICAL_SOURCES.md` §open 3). Before any checkpoint extraction,
  q0166 reads hour **13Z** (a non-checkpoint hour) for 20 seeded B days (10 SCREEN, 10 HOLDOUT; seed
  `arepo-cb8-pmxt-audit`) and counts, per (market, day), whether the market's condition id has **any** event.
- **PASS iff ≥ 90% of (market, day) pairs are present.**
  - FAIL → B "not testable (source unavailable)", counted. q0166 stops, and no checkpoint is extracted.
- In the extraction itself, a market-day whose condition id has no event in 14Z-15Z is **"source unavailable"**: its own
  label, counted, never "no trade".
- GB's "no opportunity" reading applies only if the audit passed **and** ≥ 80% of SCREEN market-days are source-available.
  Otherwise a GB fail reads "not testable (source unavailable)".
- Ingress for the audit is about 10 GB; the q0166 cap is raised to 90 GB (the audit counts toward it).

**What would kill CH76.**
- GB fails with source coverage met: no fresh ask ≤ 0.99 in the last 5 minutes, "no minute-scale opportunity at
  recorded books". A coverage failure is "source unavailable" instead, never "bots price it".
- B1 not detected.
- The tail gate fails. At about 56 days this happens whenever the mean margin is below about 8.4c, even with a
  significant mean: the verdict is "below the tail-gate requirement".
- The break-even placebo advances.
- The effect needs the top five days.
- The 10-s latency check removes it.
- B1-rep fails.

**Verdict map.**
- B1 and B1-rep pass, with the attribution credited → "Binance-certain terminal asks left a gain after fees on held-out
  days (L2)" → Stage P-B.
- Attribution fails → "terminal favourite bias".
- GB fails with coverage met → "no minute-scale opportunity at recorded books", reported as the CH76 answer.
- Coverage fails → "not testable (source unavailable)".
- Significant positive mean but the tail gate fails → "below the tail-gate requirement at n ≈ 56 days" → a candidate for
  a Stage P design with enough days, not an advance.

**Stop rule.** B1 not advanced → q0174 is not committed.

### CB8-W: Worked-order footprints and the maker who steps aside (CH69)

**Question.** After a public footprint of a worked order (two same-wallet, same-side clips a few minutes apart), do the
same-side fills over the following 10-60 minutes lose money for the resting maker, net of the spread captured? If so, a
maker who pulls that side when the second clip prints gains on each skipped share.

**Mechanism.** A large order worked in clips is flow with a known direction and an unknown remaining size. Each further
clip lifts the ask (or hits the bid) the resting maker posted. If the impact persists, the maker's fills during the order
are adverse even when the order is uninformed about the outcome. Polymarket has no hidden orders, so the footprint is
public in `/trades` within seconds.

**Why new / overlap.**
- HB2 F7 (large-for-market prints) replicated poorly. That is consistent with large prints mixing informed jumps and
  worked orders.
- CB7-X is the same economic statistic with a Kalshi trigger; CB6-N uses multi-member same-wallet sells (conversion
  dumps); CB3/CB4 maker tests condition on quote states.
- W's trigger is a single-market same-wallet footprint. This differs from CB6-N's multi-member pattern (a CB6-N episode
  has ≥ 3 members within 120 s, so the pairs can coincide only by chance; disclosed).

**Data (q0167, `h9_flow`; fresh, rows `< T8_hist_end`).**
- **Frame:** a Gamma closed walk with `volume_num_min = 50000` and `end_at ∈ [2026-05-08, 2026-10-01)`. The frame keeps
  markets that are binary, scheduled life ≥ 10 d, not weather, not crypto Up/Down (`CB1_UPDOWN_RE`). Exclusion
  ids/keys are dropped.
- **Ex-post selection (round 1, should-change; disclosed).** `closed` and lifetime `volumeNum ≥ $50k` are known only
  after the window. The frame therefore over-represents markets that later became busy, possibly because of news after
  the window. W1's statistic uses no outcome, but a window just before a later volume surge may carry more informed flow.
  - **Reported stratum (not binding):** W1 on windows ending ≥ 14 d before `end_at`, where the selection is furthest from
    the window.
  - The census reports its counts, and the verdict notes any sign difference.
- **Window:** `w0` uniform (seeded by market id, `arepo-h9-window`) in
  `[max(created_at + 1 d, 2026-05-01), min(end_at − 4 d, 2026-09-27) − 72 h]`. Markets with an empty range leave the
  frame (metadata only, counted).
- **Sample:** ≤ 2 markets per event (seeded by market id), then 1,500 non-sports and 300 sports (reported stratum),
  stratified by fee category, with the split written per event before any print request.
- **Prints:** all taker prints in `[w0, w0 + 74.5 h)`, one request series per UTC day,
  `/trades?market=<cid>&start&end&takerOnly=true&limit=1000&offset`, ≤ 10 pages. A day that hits the cap is
  **unavailable** (its prints, triggers and marks excluded, counted).
- **Stored:** market id, event id, `ts`, side in YES terms (+1 ask-side, −1 bid-side), YES price, size, and the HMAC
  wallet hash (`wallet_sidecar.hash_wallet` with the **strict key loader and pinned fingerprint**, §1.4; the raw address
  exists only in memory). No outcome is fetched; W needs none.

**Definitions (fixed now; all causal at the maker's decision time).**
- **Clip:** prints by one wallet hash on one side of one market within 2 s of each other, merged (size summed, VWAP
  price).
- **Trigger:** clip `c2` of wallet `w` such that a clip `c1` of `w` on the same side exists with:
  - `20 s ≤ ts(c2) − ts(c1) ≤ 600 s`;
  - `0.5 ≤ size(c2)/size(c1) ≤ 2`;
  - both notionals ≥ $50;
  - no same-side clip of `w` in `[ts(c1) − 600 s, ts(c1))`, so `c1` starts a run;
  - no opposite-side clip of `w` in `[ts(c1) − 1,800 s, ts(c2)]`.
- **Reaction time:** `τ = ts(c2) + 60 s`.
- **Skip window:** `[τ, e)`, where `e` starts at `τ + 600 s` and is extended to `ts(c_k) + 600 s` by each further
  same-side clip `c_k` of `w` before the current `e`, capped at `τ + 3,600 s`.
- Overlapping same-side windows merge. A print inside windows of both sides is excluded (counted).
- **Sets:** S = same-side prints (any wallet) inside skip windows, i.e. the fills the step-aside rule forgoes. S′ = the
  opposite side in the same windows. N = prints outside every window in the same market windows.
- **Usable print:** YES price in `[0.03, 0.97]`.
- **Mark** `M(u)`: the midpoint of the ask-side VWAP and the bid-side VWAP of prints in `[u − 900 s, u + 900 s]`,
  **excluding the trigger wallet(s)** of the print's window. Both sides are required; otherwise the unit is unavailable.
- **Maker mark-out per share at 2 h:** ask-side `p − M(s + 7,200)`; bid-side `M(s + 7,200) − p`. Add the forgone rebate
  (§2.1).
- **Alternative mark (robustness (i)):** the same two-sided mark at `s + 3,600` and at `s + 10,800`, averaged.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **W1** | economic | print in S (non-sports; SCREEN events; Stage 2: HOLDOUT events) | mean resting-maker mark-out at 2 h plus forgone rebate (cents per share), unweighted | < 0 |

**Gates.**
- Floor: W1 ≤ −0.5c.
- **Route gate (binding at the point estimate):** the mean mark-out over N ∪ S′ (the fills the stepping-aside maker
  keeps) is ≥ 0. Otherwise the verdict is "skipping helps, but the maker still loses: no route".
- p < 0.01 with ways event, day (A-C1) and trigger wallet.
- Placebos and robustness as §2.6.

**What the statistic is and is not.** As CB7-X1: every print fills some resting order at its price. Without books, the
maker is "any resting order at that price", not the touch maker specifically (disclosed). The mark-out already nets the
spread captured, so W1 < 0 means exactly "the skip gains".

**Reported descriptives (not counted).**
- Continuation: the share of triggers with ≥ 1 further same-side clip of `w` within 10 min, versus pseudo-pair triggers.
- The idea's sequence (≥ 4 clips, inter-arrival and size CV < 0.5), and the reversal after its last clip,
  `R = d·(M(e_last + 2 h) − M(e_last + 15 min))`. These use future clips and are **never** a selection rule for W1.

**MDE (assumptions; the census replaces them).**
- Per stage about 750 non-sports markets, about 2,250 market-days, and about 2 triggers per market-day: about 4,500
  windows and about 13,000 S prints in about 500 events.
- With a between-event SD of event means of about 2c and the day and wallet ways, SE ≈ 0.15c, so the **MDE ≈ 0.5c**,
  near the floor.

**Leakage.**
- The trigger and the extension use only clips before each moment; marks use later prints.
- The window start is seeded from metadata; no outcome is fetched.
- Hashed wallets are never identified. One entity may use many proxy wallets; that biases toward missing footprints,
  not toward the hypothesis.

**Stage 2 (HOLDOUT events).** Identical. It opens only after W1 advanced and its Stage-1 result is committed.

**What would kill CH69.**
- GW fails.
- W1 not detected.
- The time-shift placebo advances.
- The route gate fails.
- The effect needs the top five events or days.
- The 300-s latency removes it.
- W1-rep fails.

**Verdict map.**
- W1 and W1-rep pass, with the wallet attribution credited → "stepping aside after a public two-clip footprint avoided
  adverse fills on held-out events (L2)" → Stage P-W.
- Attribution fails → "a burst rule".
- Route gate fails → "protective only".

**Stop rule.** W1 not advanced → q0175 is not committed.

### CB8-H: Concentrated-holder exits as uninformed flow (CH70)

**Question.** In a market where one wallet holds at least half of a token, is a taker sell of that token by that wallet
cheaper for the resting maker to buy than a size-matched sell of the same token by someone else in the same market and
day? And does the maker who buys such exits gain after the spread?

**Mechanism.** A concentrated holder must exit through a thin book or hold to resolution. Their exit is driven by
position size, not by news, so it pushes the price without information and the price recovers. Other sellers in the same
market include informed ones. The ratio is public at any time via `/holders`.

**Why new / overlap.** `/holders` has never been collected by AREPO. CB4-C (pre-close dumps) and CB3 (quote vacuums) are
the presence-filter consumers. Their tables are not read; their targets appear here only as reported descriptives on
CB8's own data.

**Collection (fixed now; `seals/cb8_holders_rules.json`; q0162 and q0163; prospective from `T8_H1_start`).**
- **Snapshot (q0162, once per UTC day).**
  - Frame: the latest complete capture at run time (≤ 2.5 h old, else the day is "missed", counted). Markets that are
    binary, have `accepting_orders` true and sidecar `open_interest` ≥ 1,000, and are not weather or crypto Up/Down.
  - Sample: 1,500 non-sports and 300 sports, seeded per day (`arepo-cb8-holders-<date>`, seed written before the first
    request), stratified by OI tercile (cut points from that capture).
  - Request: `GET data-api /holders?market=<conditionId>&limit=20`, at ≤ 2 rps.
  - Stored: snapshot time `h`, market, token index, rank, HMAC wallet hash, amount, and the capture's OI and touch. The
    raw wallet exists only in memory.
- **Prints and marks (q0163, for snapshot market-days at ≥ `h + 28 h`).**
  - Taker prints in `[h, h + 26 h]` via `/trades?market&start&end&takerOnly=true&limit=1000&offset`, ≤ 5 pages; a capped
    market-day is unavailable (counted).
  - Stored: all prints (hashed wallets, rank flag) of market-days with `c ≥ 0.5` on either token, and prints by top-5
    holders in the other market-days.
  - Marks: the YES best bid/ask of each stored market at every complete capture in `[h, h + 30 h]`. These are read on
    the host while the captures are retained (8 days).
- **Concentration:** `c_j = amount_1(j) / max(OI, Σ top-20 amounts of j)`, bounded by 1 and conservative. The share of
  market-days where `OI < Σ top-20` is reported.

**Definitions (bind at the freeze).**
- **Exit:** a taker SELL of token `j` by the rank-1 holder of `j` at snapshot `h`, with `ts ∈ (h + 60 s, h + 24 h]`
  and `c_j ≥ 0.5`. Prints at token price in `[0.03, 0.97]` only.
- **Matched control:** the taker SELL of token `j` in the same market nearest in time within ±6 h of the exit. Its
  wallet is not among the top-5 holders of either token, and its size is within 0.5×-2× of the exit's (else 0.25×-4×;
  else none, and the exit is excluded, counted). Matching is without replacement, in exit time order.
- **Mark** `M_j(u)`: the token-`j` mid at the first complete capture with `received_utc ∈ [u, u + 2.5 h]` and spread ≤ 5c
  at that capture; else unavailable.
- **Maker mark-out** of a sell print `x`: `mo(x) = M_j(ts_x + 2 h) − p_x` (the maker bought `j` at `p_x`).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **H1** | mechanism, economic route gate | matched (exit, control) pair, non-sports, window 1 (Stage 2: window 2) | mean `mo(exit) − mo(control)`, cents per share, unweighted | > 0 |

**Gates.**
- Floor: H1 ≥ +0.5c.
- **Route gate (binding at the point estimate):** the mean `mo(exit)` ≥ +0.5c (no rebate). Otherwise the verdict is
  "exits are less adverse than other sells, but buying them does not pay: no route".
- **Route reading (round 1, should-change).** A maker cannot target an exit: the bid must already be resting when the
  holder sells. So even a full pass supports only a **presence filter** ("rest bids in markets whose top holder owns
  ≥ half of a token"). It is not a standalone trading route. The economic value of the filter would need a Stage P-H
  design with sweep-recorded bids and a fill model.
- p < 0.01 with ways event, day (A-C1) and holder.
- Placebos and robustness as §2.6.

**MDE (assumptions; the census replaces them).**
- Per window about 21 × 1,500 = 31,500 market-days, of which about 25% are concentrated.
- A rank-1 sell in 24 h happens in about 3-4% of those: about 250-300 exits, about 175-200 with a control and both marks,
  in about 100-150 events.
- With an SD of the paired difference about 6c and deff about 2, the **MDE ≈ 2c**.

H1 detects only a strong effect. That is accepted only because the collection is cheap and keyless, and GH stops it
honestly.

**Leakage.**
- `c` is computed at `h`, before every exit, from a snapshot and a capture ≤ `h`.
- Exits come strictly after `h + 60 s`. Marks come later.
- The holder is identified only by an HMAC hash.
- `/holders` semantics are undocumented: its limit, its freshness, and whether `proxyWallet` matches the print's wallet
  field. The smoke checks shape and limit, and the census reports how many rank-1 hashes ever appear among print wallets.
  If none does in window 1, H is "not testable (source)".

**Stage 2 (window 2, after the freeze).** Identical. Committed only if H1 advanced.

**What would kill CH70.**
- GH fails.
- The hashes never join.
- H1 not detected.
- The label-shuffle placebo advances.
- The route gate fails.
- H1-rep fails out of time.

**Verdict map.**
- H1 and H1-rep pass, with concentration credited and the route gate met → "concentrated-holder exits were cheaper to
  buy than other sells, out of time (L2): a candidate **presence filter** for makers" → Stage P-H. This is not a route
  claim.
- Otherwise CH70 is closed at the MDE.

**Stop rule.** H1 not advanced → q0176 is not committed. Collection stops at `T8_H2_end` + 30 h in any case.

### CB8-F: Data jobs

- **Holders smoke (q0160, counts only, cpu lane, may run before `T_seal`).** 20 markets drawn (seed `arepo-cb8-hsmoke`)
  from the latest capture's H frame. Criteria fixed now:
  - (a) HTTP 200 for ≥ 19 of 20;
  - (b) every response groups rows by token, with `outcomeIndex` ∈ {0, 1}, numeric `amount` ≥ 0 and `proxyWallet`
    present (hashed in memory, never stored);
  - (c) at most 20 rows per token, with the observed maximum recorded;
  - (d) the response time is recorded;
  - (e) **OI units (round 1, should-change):** for each smoke market, the Gamma `openInterest` and the capture's
    `open_interest` are recorded next to `Σ top-20 amounts` per token. The ratios are recorded (counts and ratios only).
    - If `Σ top-20 > 1.05 × OI` for more than half the smoke markets, OI is labelled "units unverified". `c` then
      effectively becomes the share of the top 20 through the declared `max(OI, Σ top-20)`. That formula is unchanged
      either way.
    - The label is carried into H's verdict;
  - (f) the strict key loader finds the key, and its fingerprint equals the pin (§1.4); otherwise FAIL.

  It writes `creative_batch8/holders_smoke.json`. FAIL on (a), (b) or (f) → q0162/q0163 are not committed and H is "not run
  (source)", counted.
- **CB8 smoke (q0161, counts only, after `T_seal`).**
  - (a) **Data API paging.** The pool is 20 worn markets: h1/h2/h3 exclusion ids looked up on Gamma by id (≤ 4
    requests; parse guard keeps `end_at`, `created_at`, `volumeNum`). It keeps closed markets with `end_at` in
    2026-05..09, lifetime volume ≥ $50,000 and life ≥ 10 d, **so that the W frame's own rules apply to the pool** (the CB6
    smoke lesson). The first 20 in seed order are used.
    - Requests: one paged day `[end_at − 5 d, end_at − 4 d)` each, at `limit=1000`.
    - PASS iff all of these hold:
      - every row lies within bounds;
      - rows are newest-first;
      - no duplicate fingerprint across pages;
      - ≥ 14 of 20 return ≥ 1 print;
      - ≤ 2 of 20 hit the 10-page cap.
  - (b) **Binance.** `.CHECKSUM` matches for `BTCUSDT-1m-2026-03` (spot) and `HYPEUSDT-1m-2026-03` (futures/um), both
    outside the B window.
  - (c) **pmxt.** HEAD returns a size for 3 seeded B-window 15Z hour files.

  It writes `creative_batch8/smoke.json`. FAIL (a) → q0167 is not committed and W is "not run (source)". FAIL (b) or
  (c) → q0165/q0166 are not committed and B is "not run (source)". Both are counted. A source change is a design change
  needing review.
- **Exclusion keys (q0164)**, **frame and klines (q0165)**, **books and prints (q0166)**, **`h9_flow` fetch and seal (q0167,
  q0168)**: as above. Each is resumable and budgeted, exits 75 on headroom, and writes no outcome outside a guarded file.
  Stage order for q0167: rules check, exclusion file check, frame walk, filters, key drop, window draw, per-event cap,
  sample, split, then print requests.

---

## 4. Jobs

Draft specs, one file each, in `docs/research_lab/queue/drafts/`. Fields follow `queue/README.md`; `argv[0]` is under
`backend/scripts/` and `cwd` is `backend`. **None is committed to `queue/jobs/`** before its code and tests exist and pass
a `science-reviewer` freeze check. Analysis jobs also need the CB8 freeze.

| Id | File | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|---|
| q0160 | `q0160_cb8_holders_smoke.json` | cpu | 55 | about 20 req, < 2 min, mem 200 | - | holders rules file + smoke code reviewed |
| q0161 | `q0161_cb8_smoke.json` | net | 50 | about 60 req, < 5 min | - | after `T_seal` |
| q0162 | `q0162_cb8_holders_snap.json` | cpu | 52 | about 1,800 req/day at 2 rps, about 15 min/day, ≤ 0.08 GB total, mem 400; rolling | q0160 | q0160 PASS + collector freeze check; before 2026-10-21T06:00Z if possible |
| q0163 | `q0163_cb8_holders_prints.json` | cpu | 51 | about 2,500 req/day, about 20 min/day, ≤ 0.12 GB total, mem 450; rolling | q0160 | with q0162 |
| q0164 | `q0164_cb8_exclusion_keys.json` | net | 49 | about 1,000 req, about 8 min | q0161 | after `T_seal` (later seal copies handled by seal-time drops in q0166/q0168) |
| q0165 | `q0165_cb8_updown_frame.json` | net | 48 | about 1,300 Gamma req + 35 archive files (about 80 MB), ≤ 0.03 GB | q0161, q0164 | after the q0161 PASS |
| q0166 | `q0166_cb8_updown_books.json` | net | 46 | pmxt ingress ≤ 90 GB (coverage audit first), about 2-4 h wall (85-min chunks), about 825 print req, ≤ 0.02 GB, mem 1,500 | q0165 | with q0165 |
| q0167 | `q0167_h9_flow_fetch.json` | net | 47 | about 10.7k req, about 50 min at 4 rps, ≤ 0.15 GB, mem 800 | q0161, q0164 | after the q0161 PASS |
| q0168 | `q0168_h9_flow_seal.json` | cpu | 45 | light | q0167 | with q0167 |
| q0169 | `q0169_cb8_census_BW.json` | cpu | 40 | ≤ 1.2 GB | q0166, q0168 | after both seal copies are committed |
| q0170 | `q0170_cb8_screen_B.json` | cpu | 38 | ≤ 0.8 GB | q0169 | after the CB8 freeze |
| q0171 | `q0171_cb8_screen_W.json` | cpu | 38 | ≤ 1.5 GB | q0169 | after the CB8 freeze |
| q0172 | `q0172_cb8_census_H.json` | cpu | 40 | ≤ 0.6 GB | q0163 | refuses before `T8_H1_end` + 30 h |
| q0173 | `q0173_cb8_screen_H.json` | cpu | 38 | ≤ 0.6 GB | q0172 | after the CB8 freeze and the committed GH result |
| q0174 | `q0174_cb8_rep_B.json` | cpu | 38 | ≤ 0.8 GB | q0170 | only if B1 advanced |
| q0175 | `q0175_cb8_rep_W.json` | cpu | 38 | ≤ 1.5 GB | q0171 | only if W1 advanced |
| q0176 | `q0176_cb8_rep_H.json` | cpu | 38 | ≤ 0.6 GB | q0173 | only if H1 advanced; refuses before `T8_H2_end` + 30 h |
| q0177-q0179 | reserved | | | | | |

## 5. Code needed (not written by this document)

### 5.1 Modules

- **`backend/astrolabe/research_lab/cb8_updown.py` (CH76).**
  - Rules: `RULES` (hashed against `seals/cb8_rules.json`), `parse_updown(question, description, resolution_source)` →
    asset, symbol, venue (spot or um) or a failure reason, `week_split(seed)`, `t_end(d)`.
  - Binance: `binance_month(symbol, venue, yyyymm)` (download, `.CHECKSUM` verify, parse in memory),
    `split_klines(df, days)` → features (open < `t_end`) and the guarded settlement candles, `strike(d)`,
    `z_features(klines, t, t_end, n_sigma=60)`.
  - Books: `pmxt_states(day, condition_ids, checkpoints)` built on `history_sources.load_book_snapshots` / `RangeFetch`.
    It returns per token and checkpoint: best ask/bid, size at best, size within 1c, tick, `fee_rate_bps`, last event
    time, crossed and halted flags. Day-level ingress accounting and the 90 GB cap. `coverage_audit(days, condition_ids, hour=13)` (counts only; the first stage; FAIL stops).
  - Prints: `terminal_prints(cid, t_end)` (no wallet stored).
  - Analysis: `b_units(...)`, `b1_net(units, fee_rule)`, `tail_gate(...)`, `breakeven_placebo(...)` (per-day
    comonotone), `certainty_attribution(...)`, `source_check(...)` (Binance versus Gamma outcome).
- **`backend/astrolabe/research_lab/cb8_flow.py` (CH69).**
  - Fetch: `flow_frame(...)`, `draw_window(market, seed)`, `flow_fetch(...)` (paged days, capped day → unavailable,
    `wallet_sidecar.hash_wallet` in memory, split before print requests, HOLDOUT to its own root), `flow_seal(...)`.
  - Analysis: `clips(prints)`, `triggers(clips)`, `skip_windows(triggers, clips, lag, base, cap)`,
    `sets(prints, windows)`, `two_sided_mark(prints, u, half_width, exclude)`, `w1(...)`, `route_gate(...)`,
    `time_shift_placebo(...)`, `pseudo_pairs(...)`, `continuation(...)`, `sequence_reversal(...)` (descriptive).
- **`backend/astrolabe/research_lab/cb8_holders.py` (CH70).**
  - Collection: `holders_frame(capture, rules)`, `holders_snap(...)` (seeded sample, `/holders` at ≤ 2 rps, hash in memory,
    idempotent per UTC day), `holders_prints(...)` (windowed prints, rank flags, the storage rule) and
    `capture_marks(...)`.
  - Analysis: `concentration(...)`, `exits(...)`, `match_controls(...)`, `mo(...)`, `h1(...)`, `label_shuffle(...)`,
    `concentration_attribution(...)`, `presence_tables(...)` (descriptive).
- **`backend/astrolabe/research_lab/cb8_common.py` (round 1, item 6):** `load_wallet_key_strict(path, pinned_fp)`
  reads `~/.arepo/wallet_hash_key` (or `AREPO_WALLET_HASH_KEY_PATH`) without creating it. It checks mode 600, computes
  `key_fingerprint(key)` (HMAC-SHA256 of `"arepo-cb8-wallet-key-fingerprint-v1"`, first 16 hex characters) and raises
  on mismatch. Also `hash_wallet` re-export, `windowed_prints(cid, start, end, day_pages)` (paged, capped day →
  unavailable, newest-first check, fingerprint dedupe), and `rules(path)` (hash check).
- **`backend/astrolabe/research_lab/cb8_declaration.py`:** `HYPOTHESES_CB8` and `declaration_sha256()` over every
  population rule, regex, checkpoint, threshold, cap, window, horizon, seed, date, floor, gate and the source of every rule
  function and UPPER_CASE constant read at call time (as CB5-CB7).
- **Shared statistics are imported, not copied:** CB1 cluster p / bootstrap / small-G helpers, the A-C1 day-way logic
  (`cb4_rules`), `economics.DOCS_CATEGORY_RATE` / `REBATE_SHARE` / `taker_fee`, `history_backfill.cb1_topic` /
  `CB1_UPDOWN_RE` / `Limiter`, `cb2_weather.TEMP_RE`, the census guard, `provenance.append_trial` and
  `wallet_sidecar.hash_wallet`.

### 5.2 Runner

`backend/scripts/run_cb8.py {rules,holders-smoke,smoke,holders-snap,holders-prints,exclusion-keys,updown-frame,
updown-books,flow-fetch,flow-seal,census,screen,replicate,verify-seal} --family B|W|H`.
- It refuses the run ids and roots of §1.3 and writes only under `research_lab/creative_batch8/` and `history/h9_flow/`.
- Wallet-hashing commands (`holders-smoke`, `holders-snap`, `holders-prints`, `flow-fetch`) load the key only through
  `cb8_common.load_wallet_key_strict()`. It never creates a key, and it refuses (exit 2) on a missing key or a fingerprint
  mismatch; the fingerprint goes into every manifest.
- Fetchers refuse unless the rules hash matches, every exclusion file matches its pin, and the smoke records PASS under
  the same hash. They exit 75 on headroom. There is no Mac or standalone mode (as CB7).
- The declaration-hash guard applies to `census`, `screen` and `replicate`.
  - `replicate --family B|W` refuses without a committed Stage-1 file showing the test advanced.
  - `replicate --family H` also refuses before `T8_H2_end` + 30 h.
  - `census --family H` refuses before `T8_H1_end` + 30 h.
- Every counting command runs the `trials.jsonl` union first and records the post-union count. Results are never
  overwritten.

### 5.3 Tests (`test_cb8_updown.py`, `test_cb8_flow.py`, `test_cb8_holders.py`, `test_run_cb8.py`)

- **Updown.**
  - Question and description regexes on fixtures; the `resolutionSource` parser (spot versus futures).
  - The strike-clause regexes `UP_RE` and `DOWN_RE`: mirror groups equal; strike date = d − 1 and settlement date = d.
    Failure fixtures for a wrong date, an "Up" clause with "higher", and a missing clause.
  - Week split deterministic from the seed and fixed before reads.
  - Kline usability: a candle at `o + 64 s` is not usable, at `o + 65 s` it is. σ needs ≥ 55 candles. `m` is correct at
    each checkpoint.
  - Settlement candles appear only in the guarded file. No function compares consecutive strikes (AST or path test).
  - pmxt states use both clocks ≤ `t`; freshness 120 s; crossed is ineligible; the cap is `a ≤ 0.99` with size ≥ 5.
  - The fee uses the max of the recorded and docs rates. Ties pay 0.5.
  - The day-unit tail gate (`W_d`, `L_d` per day; the Clopper-Pearson bound on days) on fixtures with 0, 1 and 5
    losing days. It reproduces the required margin of about 8.4c at n = 56 with k = 0. The break-even placebo advances
    about 1% on a no-effect fixture with heavy within-day dependence.
  - The source check keeps disagreeing units in the P&L with the Gamma outcome, and > 2% → not testable.
  - The latency fill is `max(a_t, a_{t+10})` with ≥ 5 shares at ≤ `a*` at `t + 10 s`.
  - The coverage audit labels "source unavailable" separately from "no trade".
- **Flow.**
  - Clips merge within 2 s. The trigger gap is enforced (19 s no, 20 s yes, 601 s no), as are the size ratio, the $50
    notional and the run-start and opposite-side rules.
  - The skip window extends on further clips and is capped at 60 min, and uses no clip after the moment.
  - A capped day → its triggers and prints are unavailable.
  - The mark excludes the trigger wallet and needs both sides.
  - On a fixture where impact persists, S marks out negative. The pseudo-pair attribution fails on a wallet-free burst
    fixture.
  - No raw wallet anywhere on disk (scan). The split is written before print requests. HOLDOUT files are refused before
    the Stage-1 file exists.
- **Key continuity (all wallet-hashing jobs).**
  - `load_wallet_key_strict` refuses on a missing key and never creates one (a test runs with an empty HOME and asserts
    no file is written).
  - A fingerprint mismatch → exit 2. The fingerprint is in every manifest. Census and analysis refuse mixed
    fingerprints.
- **Holders.**
  - The frame, the seeded sample and the seed written before requests.
  - Smoke (e): OI ratios recorded; the "units unverified" label rule.
  - `T8_H_collect_max` stops collection; a freeze slip → H1-rep "not run (freeze slip)".
  - Idempotent per UTC day; a missed day is recorded.
  - Hashing only. `c` uses `max(OI, Σ top-20)`. Exits are after `h + 60 s`.
  - Controls exclude top-5 wallets and respect the size bands without replacement.
  - The mark spread ≤ 5c within 2.5 h. The label shuffle is block-wise.
  - The storage rule (c ≥ 0.5 market-days in full, top-5 prints elsewhere). The disk cap.
- **Runner.**
  - Refusals (run ids, roots, rules hash, pins, smoke, freeze, Stage-1 files, dates).
  - `KIND_RULES` has the CB8 kinds, and the counter runs on the real `trials.jsonl`.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: B1, W1, H1 | 3 | `cb8_test` + `creative_batch_8:B`, `:W`, `:H` (1 each) | each p < 0.01; batch-Holm label (α 0.01, k1 3); BY triage |
| Stage 2: B1-rep, W1-rep, H1-rep (registered only) | ≤ 3 | `cb8_replication` + count lines | one Holm, one-sided α = 0.05, k ≤ 3 |
| Census, gates, smoke, strata, descriptives, variants | 0 | `cb8_descriptive` | - |
| **Total** | **3 fixed + ≤ 3 conditional = 3-6** | | cumulative ≥ 1,121 at drafting → ≥ 1,124-1,127 plus CB6/CB7 |

**Host compute.** About 3-4 CPU-hours at nice 19 in total; peak RAM 1.5 GB (B books, W screen).

**Network.**
- Before `T_seal`: H collection only, cpu lane, about 4.3k requests a day.
- After `T_seal`: about 14k API requests, about 80 MB of Binance archives, and ≤ 90 GB of pmxt range-read ingress.

**Disk.** ≤ 0.4 GB across all CB8 outputs.

## 7. Main scientific risks

1. **Bots and the day count (B).** The most likely CH76 answer is "no fresh ask ≤ 0.99 with \|z\| ≥ 3": a GB fail,
   honestly reported (or "source unavailable" if the pmxt coverage audit fails). If opportunities exist, the binding
   limit is the day-unit tail gate. With about 56 independent days per stage, B1 can pass only with a mean margin of
   about ≥ 8.4c. Smaller real residuals are reported as "below the tail-gate requirement" and need Stage P's day count.
2. **pmxt reconstruction (B).**
   - Event-stream books have no sequence numbers, so crossed states occur. Illiquid tokens look stale.
   - The freshness rule (120 s) and the crossed exclusion bind. Trading may halt before `t_end`; halted units are
     counted and reported.
   - 5-15% of hours are missing; such days are lost, never replaced.
   - Ingress is about 0.5 GB per hour read, so the 90 GB cap may truncate days. That is even across the split, and the
     day order is seeded.
3. **HYPE settles on futures (B).** It has a different venue and archive; the robustness check without HYPE binds.
4. **Source agreement (B).** Binance archive closes must reproduce Gamma outcomes. Above 2% disagreement → not
   testable. Ties are 50-50 by rule.
5. **Print-only fills (W).**
   - No books: the maker is "a resting order at that price".
   - The two-sided print mark may be unavailable in thinner markets. The frame's $50k volume floor reduces this, the
     census reports it, and the worst case binds.
   - The 10-page day cap drops the busiest market-days, which biases toward less active markets (disclosed, counted).
6. **Wallet identity (W, H).** Proxy wallets: one entity with many wallets hides footprints and splits holdings. This
   biases toward the null. The `/holders` `proxyWallet` and the print wallet must hash to the same value. H is "not
   testable (source)" if they never join.
7. **Power and calendar (H).** The MDE is about 2c, and the windows run to about early December. GH is the honest stop.
   Capture marks (2-hourly, spread ≤ 5c) lose wide concentrated markets, and the census reports how many.
8. **Shared calendar (H).** E011 (to 11-10) and CB3-CB7 live windows overlap. CB8 never opens their files.
9. **Same-calendar holdouts (B, W).** Holdouts share the calendar and regimes with the screens, so they guard against
   selection, not against regime change. Stage P guards against regime change.

## 8. Next actions

1. **Challenger review: done** (round 1, §9; one challenge, one response, no second round).
2. **Implementer, first (prospective H collection; the only CB8 work that benefits from starting before `T_seal`).**
   Code list:
   - `backend/astrolabe/research_lab/cb8_common.py`: `load_wallet_key_strict`, `key_fingerprint`, `rules` (hash check),
     `windowed_prints` (paged `/trades` with start/end, `takerOnly`, ≤ N pages, capped day → unavailable, bounds and
     newest-first checks, fingerprint dedupe, wallet hashed in memory).
   - `backend/astrolabe/research_lab/cb8_holders.py` collection side:
     - `holders_frame(capture, rules)` (binary, `accepting_orders`, OI ≥ 1,000, not weather or Up/Down, sports flag,
       OI terciles);
     - `holders_sample(frame, date, seed)` (seed written before requests);
     - `fetch_holders(cid, limit=20)`;
     - `holders_snap(...)` (idempotent per UTC day, "missed" day record, stop at `T8_H_collect_max`, exit 75 on
       headroom, disk cap 0.08 GB);
     - `holders_prints(...)` (snapshot days ≥ `h + 28 h`, `windowed_prints` over `[h, h + 26 h]` with ≤ 5 pages, rank
       flags, the storage rule: full prints when `c ≥ 0.5`, top-5 prints otherwise);
     - `capture_marks(...)` (YES touch of stored markets at complete captures in `[h, h + 30 h]`, read within the 8-day
       retention);
     - `concentration(...)`;
     - `holders_smoke(...)` (criteria (a)-(f), including the OI ratios and the key-fingerprint check).
   - `seals/cb8_holders_rules.json`, generated by `run_cb8.py rules --family H`: frame, sizes, seeds, request form,
     windows, storage rule, mark rule, the concentration formula, `T8_H_collect_max` rule, smoke criteria,
     `wallet_key_fingerprint`, `rules_sha256` and the source hash of every rule function.
   - `backend/scripts/run_cb8.py rules | holders-smoke | holders-snap | holders-prints` (refusals of §5.2; the manifest
     records the fingerprint and the rules hash).
   - Tests: `test_cb8_common.py` (strict loader never creates a key; fingerprint mismatch → exit 2; paging, bounds and
     dedupe on fixtures) and `test_cb8_holders.py` (collection items of §5.3).

   Then a `science-reviewer` collector freeze check. Commit q0160, and on a PASS commit q0162/q0163, aiming at the first
   snapshot ≥ 2026-10-21T06:00Z (pin `T8_H1_start` and `T8_H_collect_max`). Late code only shifts `T8_H1_start`.
3. **Implementer, second (before 10-22, code only; no network).**
   - W fetch first (q0167/q0168): `cb8_flow.py` `flow_frame`, `draw_window`, `per_event_cap`, `flow_sample`,
     `event_split`, `flow_fetch` (via `cb8_common.windowed_prints` with ≤ 10 day pages and the strict key, SCREEN and
     HOLDOUT roots, exit 75, resumable 85-min chunks, `--cap-at` 2026-10-01), and `flow_seal` (seal-time drops by id and
     key, listing sha256, `DROPPED_*` blocks, `ACCESS_LOG`).
   - The smoke and exclusion keys (q0161/q0164): `run_cb8.py smoke | exclusion-keys`.
   - B fetch (q0165/q0166): `cb8_updown.py` `parse_updown` with `UP_RE`/`DOWN_RE`, `week_split`, `binance_month`,
     `split_klines`, `coverage_audit`, `pmxt_states` and `terminal_prints`.
   - `seals/cb8_rules.json` and the fetch-side tests, then a fetcher freeze check.
4. **After `T_seal`.**
   - Commit q0161 and q0164; then on a PASS commit q0165-q0168.
   - Commit the seal copies and run q0169.
   - Insert the counts and gates here.
   - Implementer for the analysis code; `science-reviewer` freeze check; freeze (`model_specs/cb8_v1.json`).
   - Run q0170 and q0171.
5. **After `T8_H1_end` + 30 h.** q0172 (GH), then q0173. Commit q0174-q0176 only for advanced tests.

## 9. Challenger round 1 and response (2026-10-17)

One `science-reviewer` pass on the committed draft `acd39f2`: **ACCEPT_WITH_REQUIRED_CHANGES**. This is the single
response round; then proceed. Every change tightens or discloses. No alpha, floor, buy cap, threshold or gate was
relaxed.

### 9.1 Required changes

| # | Finding | Resolution | Where |
|---|---|---|---|
| 1 | The tail gate mixed units: a per-day loss probability against per-unit payoffs. At about 56 traded days the 99% Clopper-Pearson bound with zero losing days is 0.079, so about 8.5c of gross margin is needed | **Kept binding and made unit-consistent**, decided data-blind. The gate is now on **day P&L**: `mean_d(W_d)(1 − q_U) − mean_d(L_d) q_U ≥ 0`, with `W_d`/`L_d` the day's total win and worst-case total loss and `q_U` the bound on losing days. **Justification:** terminal reversals come from common crypto shocks, so the day is the independent unit. Market-day units would count one shock seven times, and distribution-free bounds are looser at n ≈ 56. **Stated plainly:** B1 can pass only with a mean margin of about ≥ 8.4c per share (about 12.5c with one losing day, about 16c with two). A 1-3c residual is reported as "below the tail-gate requirement" and belongs to Stage P (about 1.5c at about 300 days) | §CB8-B gates, MDE, kill list, verdict map; §2.4; §2.7; §5.3; §7 risk 1 |
| 2 | The source check excluded Binance-versus-official disagreement units | **Disagreeing units stay in the P&L with the Gamma official outcome.** Disagreement is diagnostic only. The > 2% "not testable (source)" gate stays | §CB8-B target; §5.3 |
| 3 | pmxt coverage is unaudited | **Count-only coverage audit**, the first stage of q0166: hour 13Z of 20 seeded days (10 SCREEN, 10 HOLDOUT), with PASS iff ≥ 90% of (market, day) pairs show an event. FAIL → "not testable (source unavailable)". Market-days without events in 14Z-15Z get their own "source unavailable" label. A GB fail reads "no opportunity" only with the audit PASS and ≥ 80% coverage. The ingress cap rises from 80 to 90 GB to pay for the audit (a cost cap, not a statistical threshold) | §CB8-B audit; §2.7; §2.8; §5.1; q0166 |
| 4 | Latency robustness | B fills at `max(a_t, a_{t+10 s})` only if ≥ 5 shares at ≤ that price remain at `t + 10 s` (and ≤ 0.99); it must keep the sign, half the magnitude and the tail gate | §2.6 (vi); §5.3 |
| 5 | The strike was not verified from the rule text | Frozen `UP_RE`/`DOWN_RE` strike-clause regexes: mirrored groups, strike date = d − 1, settlement date = d; failures excluded and counted. A counts-only check matched 825 of 825 (`probes/cb8_design_20261017/updown_strike_clause_probe.py`) | §CB8-B population 3a; §5.3 |
| 6 | HMAC key continuity (`load_or_create_key` would silently create a key) | `wallet_key_fingerprint` (HMAC of a fixed constant) is pinned in both rules files and every manifest. `cb8_common.load_wallet_key_strict` never creates a key and refuses on a missing key or a mismatch. Smoke criterion (f). Census and analysis refuse mixed fingerprints | §1.4; §CB8-W data; §CB8-F; §5.1-5.3; q0160, q0162, q0163, q0167 |

### 9.2 Should-changes

| Finding | Resolution |
|---|---|
| q0162 freeze slip | `T8_H_collect_max = T8_H1_start + 63 d`. If window 2 cannot complete by then, H1-rep is "not run (freeze slip)", counted. Windows are never shortened or extended |
| W frame ex-post selection (`closed`, lifetime volume ≥ $50k) | Disclosed. A reported stratum covers windows ending ≥ 14 d before `end_at` |
| H route | Reframed: even a full pass supports a **presence filter** only, not a standalone route (a maker cannot target an exit) |
| OI units | q0160 criterion (e) records Gamma `openInterest`, capture OI and `Σ top-20`. "Units unverified" if `Σ top-20 > 1.05 OI` in more than half the smoke markets. The `c` formula is unchanged |
| Alternating-week holdout | Disclosed as a selection guard only; Stage P-B is the out-of-time and regime check |

### 9.3 Effect on counts and power

k is unchanged: **3 fixed (B1, W1, H1) + up to 3 conditional = 3-6.**
- **B1:** the p-based MDE (about 2-3c) is no longer the binding limit. The day-unit tail gate requires a mean margin of
  about ≥ 8.4c at about 56 traded days with no losing day.
- **W1 and H1:** MDEs unchanged (about 0.5c and about 2c).
- **pmxt ingress cap:** 80 → 90 GB.

