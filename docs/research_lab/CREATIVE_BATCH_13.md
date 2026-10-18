# Creative batch 13 (CB13): maker toxicity by resolution class, barrier-versus-terminal confusion

`evidence_role: exploratory_dev` (CB13-T Stage 1, on worn live captures and monitor prints) / `prospective`
(CB13-T Stage 2, on a later live window that does not exist yet at drafting) / `exploratory_historical` (CB13-R Stage
1; Stage 2 on a sealed later historical holdout) | status: **DRAFT (pre-challenger). Nothing frozen, nothing queued, no
code.** Drafted 2026-10-18 21:15 UTC+1 (2026-10-18T20:15Z) at HEAD `ee0bc96`. Nothing was fetched or written for CB13
beyond the read-only host probes and the 19 counts-only keyless GETs of §0.3. **No CB13 quantity was computed:** no
mark-out, forward price, mid change, slope, net, touch outcome or resolution.

This file turns two round-6 ideas from `CREATIVE_HYPOTHESES_2026-10-20.md` (CH128, rank 1; CH118, rank 2) into
declared, falsifiable tests. It also records why CH119 (rank 4) is not a test in this batch: its population census
fails (§0.4). It follows `CREATIVE_BATCH_12.md` (CB12) and `CREATIVE_BATCH_11.md` (CB11) in structure and rules. "As
CB12 §x" means that rule applies unchanged, including its challenger-round fixes and the CB11 and CB10 rules it cites.
CB4 amendment A-C1 and the CB10 §2.3 small-G rule govern the time cluster ways.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded or declared prices.
- Test tables bind only once the CB13 declaration hash is committed (`model_specs/cb13_v1.json`, the CB13 freeze). That
  needs a `science-reviewer` challenger round (§8) and a code-against-design freeze check first. The rules (frames,
  windows, labeller, splits, exclusion rules, clocks, stored fields, model constants) are fixed in
  `seals/cb13_rules.json` before the first CB13 job (q0270). **Both files are hashed per part (`common`, `T`, `R`)**, so
  T can freeze and screen without waiting for R's data, and no rule of one part changes after the other part's read
  (CB11 freeze-check fix B1).
- **Lanes.** CB13-T needs **no network at all**: it runs on files already on the Oracle host, on the `cpu` lane, while
  the `net` lane is busy with CB11 (priorities 25-29) and CB12 (20-24) fetches. CB13-R needs keyless fetches, and its
  `net` jobs have **priority 15-19, below every CB6-CB12 job**. No CB13 object is bound to the 2026-10-22T00:00Z
  `T_seal` lane.
- **Queue ids q0270-q0299, one id per job, no letter suffixes.** Checked at drafting: `queue/jobs/` and
  `queue/drafts/` hold nothing above q0239. CB12 reserved q0240-q0269. Specs are drafts **in this document only** (§4).
  Nothing is created under `queue/` until code, tests and the freeze check exist.
- **Naming.** Historical fetch roots `history/h13_touch` and `history/h13_binance`; outputs under
  `research_lab/creative_batch13/`. CB13-T writes no `history/` root, because it fetches nothing.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB13-T** maker toxicity by resolution class (CH128) | a paper maker resting at the recorded touch and filled by a ≥ $1k taker print loses less to adverse selection in markets settled by a public statistic or an asset path (LOW) than in unscheduled-news markets (NEWS), by ≥ 0.5c per filled share at 2 h (T1). In LOW, the 2 h mid-marked maker net stays positive (T2, ≥ +0.25c) | T1 (class contrast), T2 (LOW sign) | **host files only**: live large-trade monitor prints and complete-universe captures, SCREEN window `[2026-10-12, 2026-10-16)` | the same stores, HOLDOUT window `[2026-10-21, 2026-10-26)`, sealed, event-disjoint from SCREEN; the T3 economic check at recorded touches | q0270-q0275 |
| 2 | **CB13-R** barrier-versus-terminal confusion (CH118) | in closed crypto "reach / dip to $B" ladders settled on Binance 1-minute highs and lows, the driftless reflection-principle touch probability predicts resolution beyond the price (R1, slope ≥ 0.30) | R1 (slope) | fresh `h13_touch` (Gamma frame, CLOB `prices-history`) and fresh `h13_binance` (public 1-minute archive); window ends `[2024-11-01, 2026-04-01)` | the same fetch, sealed HOLDOUT window ends `[2026-04-01, 2026-10-01)`; R2 (modelled-cost economic) only there | q0276-q0283 |
| - | CH119 inclusive-threshold atom | not a test: the census fails (§0.4) | none | | | next batch |

**Counted: 3 fixed (T1, T2, R1) + up to 5 conditional (T1-rep, T2-rep, T3, R1-rep, R2) = 3-8** (§2.5). The budget is
fixed now. No CB13 test is added after any CB13 read.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0270 | `cb13_smoke` (counts only; §CB13-S) | T, R | after `seals/cb13_rules.json` and smoke code exist (`cpu` lane, ≤ 30 requests) |
| q0271 | `cb13_t_frame` (T exclusion keys; SCREEN fill table, features only, labels applied; no mark) | T | after q0270 PASS and the labeller audit (§CB13-T) is committed |
| q0272 | `cb13_census_T` (counts only; gates GT, GL, GTP; MDEs) | T | after q0271 |
| q0273 | `cb13_screen_T` (T1, T2 Stage 1; gate GTI) | T | after the T freeze |
| q0274 | `cb13_t_holdout` (HOLDOUT seal: source-file sha256; HOLDOUT fill table and raw mark-quote table to `holdout/`; counts only) | T | not before 2026-10-26T08:00Z |
| q0275 | `cb13_rep_T` (T1-rep, T2-rep, T3 on the sealed HOLDOUT) | T | only if T1 or T2 advanced; after the seal copy is committed |
| q0276 | `cb13_exclusion_keys` (CB11 q0221 key file + every set since, including CB12 frames + seal copies; barrier-overlap list) | R | after q0270 PASS and CB11 q0221 complete |
| q0277 | `cb13_touch_frame` (Gamma tag-21 date walk, barrier templates, rule parser, split, outcomes to guarded files, cross-check against the 2026-10-12 pull) | R | after q0276 |
| q0278 | `cb13_touch_prices` (`prices-history` fidelity 60, 14-day chunks; HOLDOUT to `holdout/`) | R | after q0277 |
| q0279 | `cb13_binance` (data.binance.vision monthly 1m spot klines, CHECKSUM-verified; HOLDOUT months to `holdout/`) | R | after q0277 (needs the parsed asset list) |
| q0280 | `cb13_seal_R` (HOLDOUT listings sha256; seal copy; seal-time drops) | R | after q0278 and q0279 |
| q0281 | `cb13_census_R` (counts only; gates GR, GRP; MDEs) | R | after q0280 and the seal copy |
| q0282 | `cb13_screen_R` (R1 Stage 1) | R | after the R freeze |
| q0283 | `cb13_rep_R` (R1-rep and R2 on the sealed HOLDOUT) | R | only if R1 advanced |
| q0284-q0299 | reserved | - | - |

### 0.2 Selection and scope

**Ranking rule.** As CB12 §0.2, with this brief's preferences: (a) screens on data **already on the Oracle host**, run
on the `cpu` lane while CB11 holds the `net` lane; (b) round-6 rank; (c) side-free and wallet-free designs. CB9-S0 has
not reported on the Data API `side` field, so **no CB13 statistic reads `side`**.

**What the drafting session read or computed (2026-10-18T19:00-20:15Z).**
- Committed documents: CLAUDE.md, AGENTS.md; round 6 §0 (facts), §2 (CH118, CH119, CH128), §3 (ranking, screen
  sketches, registration notes); CB12 §0-§8 (template); CB11 and CB10 rules as cited by CB12; the date tables and §1.3
  lists of CB1-CB7 and CB10; the E004-E007 and E011 registrations and the host-move deviation entry; the ledger tail
  (cumulative count, binding nulls); `ECONOMIC_CONDITIONS_STUDY.md` (maker and taker conventions);
  `EXECUTION_COSTS.md` (spreads by price band); `LIVE_TRADE_MONITOR.md`; `COLLECTION_HOST.md`;
  `SCREENING_BATCH_2.md` (SEALED-H4); `seals/j4r_window.json`, `seals/cb1_t_rep_start.json`; the monitor's frozen
  rule list (`detector_specs/FROZEN.json`: five `uf_*` rules).
- Prior-work search: no AREPO test has used **resolution class** as the unit of maker adverse selection. The 95
  economic cells and SB2-J2 pooled classes. CB3-B (selective maker) filters by print size, life stage and round-trip
  flow, not by class. No test has used a barrier (touch) payoff, the reflection principle or the Binance highs and
  lows. CB10-D anchors **terminal** "above $K on date" ladders with Deribit, CB8-B the terminal minutes of Up/Down
  dailies, and CB9-P equity Up/Down dailies with Pyth. All three are disjoint from R's templates (§1.3).
- `battery2.cumulative_count()` (`battery2-count-v1`) = **1,181** on the committed `trials.jsonl` at HEAD `ee0bc96`.
  The file last changed at `fec1b04`, and the working copy is identical. The host union step runs before every counting
  CB13 job and records the post-union value.

**Three round-6 premises corrected by the probes (they shape this design).**
1. **CB8-B's Binance archive does not exist.** CB8's q0165 is still a draft. No Binance file exists on the host
   (`history/`, `history_sources/`, `creative_batch8/`) or on the Mac. CB13-R therefore needs its own small keyless
   fetch (q0279, about 0.2 GB of zips). R is not a host-only screen.
2. **Capture rows hold no question text and no `resolutionSource`, `automaticallyResolved`, `secondsDelay` or
   `gameStartTime`.** CH128's field-based classifier cannot run on captures. Every monitor print, however, carries the
   market `title` and `slug`, and the capture sidecar carries `fee_type`, `fee_category` and `series_slugs`. The T
   labeller uses only those point-in-time fields (§CB13-T). No metadata fetch is needed.
3. **The monitor's alerts use the five frozen `uf_*` rules**, not `sm_learned`. `sm_learned_v2` is E011's detector on
   complete-universe captures. Both streams are untouched by CB13 (§1.3).

### 0.3 Feasibility probes (counts only; read-only host probes + 19 keyless GETs; nothing stored)

Host probes ran over `ssh oracle` as `nice -n 19` streaming Python one-liners and `ls`/`du`/`wc`. **Nothing was
written, moved or deleted on the host. `~/arepo/run/queue` was not touched.** Peak probe memory was under 150 MB with
about 4.3 GB available. Keyless GETs ran from the Mac (scripts in `/tmp/cb13probe/`, not committed),
`User-Agent: arepo-research-probe`, paced at ≥ 0.8 s. **No outcome, resolution, wallet or volume of any market was
printed. No forward price, mid change or mark-out was computed.** Disclosed feature exposure: rows H6-H8 read SCREEN
prints' prices against the preceding capture touch, to count fills, crossing shares and spread quartiles. Row H10
decoded each object of `poly_markets.json` in memory and kept only the question, event title, end month, the presence
of `closed_time` and description booleans. Its `outcome_prices` and `volume` fields were decoded but discarded unread:
not printed, not aggregated.

| # | Probe | Finding |
|---|---|---|
| H1 | `ls` of `research_lab/` and `live_trades/`; `du`; `free`; `df` | `live_trades/` holds `trades-20261012..18.jsonl` (daily by receipt), `alerts.jsonl`, `outcomes.jsonl`, `scores-*.jsonl`, `wallets.jsonl`, `stats.jsonl`, `state.json` (327 MB); `snapshots/` 5.6 GB, `book_sweeps/` 866 MB, `trade_samples/` 876 MB; data-dumps 15 GB; root 89 GB with 57 GB free; MemAvailable about 4,335 MB |
| H2 | `wc -l` per trades file; key names of one line | 7,242 / 10,380 / 9,971 / 10,522 / 8,836 / 13,621 / 10,642 prints (10-12..10-18). 35 keys, including `ts` (venue), `recv_ts`, `condition_id`, `token_id`, `outcome_index`, `price`, `size`, `cash`, `tx16`, `title`, `slug`, `ctx_*` (Gamma context fetched **after** receipt) and the forbidden `side`, `wallet_hash`, `wallet_*` |
| H3 | per-file counts | about 1,400-2,700 markets and 600-1,100 events a day; median receipt lag 450-541 s; `ctx_status` ok for 70-96%; venue spans are continuous from 2026-10-12T01:30Z (monitor outage 10-14 00:00-10:47Z per the ledger deviation, partly back-paged) |
| H4 | capture layout | 95 capture dirs (10-10..10-18), each with `manifest.json`, `rows.csv.gz` (27 columns: touch, `received_utc`, ids, `end_date`, `liquidity`, ...), `rows_ext.csv.gz` (sidecar: `fee_type`, `fee_category`, `taker_base_fee`, `fee_schedule`, `series_slugs`, `created_at`, `order_price_min_tick_size`, `rewards_*`, ...); 274,036 market objects in the 10-15T12:31Z capture; **no question text, `description`, `resolutionSource` or `gameStartTime`** |
| H5 | complete captures by day (manifest `state`) | 10-12: 12, 10-13: 12, **10-14: 6** (pre-cutover outage), 10-15: 12, 10-16: 12, 10-17: 12, 10-18: 10 by 18:31Z |
| H6 | SCREEN prints (`ts` in `[10-12, 10-16)`, files 10-12..10-15 only) by `ctx_category` | **38,115 prints**, 37,617 (transaction, market) units, 6,042 markets, 2,139 event ids; by day 7,841 / 9,790 / 10,044 / 10,440. Sports 26,509 (70%); no category (unenriched) 6,518; crypto 1,251; politics 1,139; economics 763; culture 272; finance 246; weather 133; tech 128; mentions 55; geopolitics slugs about 300 |
| H7 | the same prints against the latest **book-sweep** touch of the token | sweeps (2 per pass, 54,080 token rows, a sample of tokens) lack most printed tokens ("no touch" for about half of the sports prints and for 846 of 1,251 crypto prints): **sweeps are rejected as the touch source** and kept for depth only (reported) |
| H8 | the same prints against the latest **complete-capture** row of the market (44 captures from 10-11T20Z) | by touch age at the print (≤ 20 min / 20-60 / 60-120 / > 120), crossing (price at or beyond the touch) vs inside: crypto 213 / 340 / 536 / 53 crossing, 54 inside, 42 no row or one-sided; econ+finance 254 / 278 / 327 / 107, 25 inside; politics+geo 383 / 640 / 964 / 78, 112 inside; other 79 / 169 / 264 / 18; unenriched 739 / 1,284 / 1,940 / 1,739; sports 5,212 / 7,499 / 10,629 / 1,738. **Prints crossing a touch aged ≤ 60 min: non-sports enriched about 2,360 in about 520 events, unenriched about 2,020, sports about 12,700.** Thirteen or fourteen of 16 six-hour blocks hold fills. Spread at the fill, p25/p50/p75: 0.2-1.0 / 1.0 / 1.0-2.0c |
| H9 | search for a Binance archive (`find -iname '*binance*'`, `*kline*`, host and Mac) | none (premise 1 above) |
| H10 | streaming census of `cross_venue/poly_markets.json` (the 2026-10-12 Gamma pull, a filtered set of closed markets; CB12-X pins it for `endDate`) | 148,384 markets (148,370 closed), ends 2025-10..2026-10. **Crypto barrier ("reach / hit / dip to", not "above ... on"): 3,948 markets in 501 events**, 3,946 with "Binance" and all with high/low wording in the description. By end month: 2025-10 119, 11 243, 12 301, 2026-01 227, 02 275, 03 253, 04 478, 05 434, 06 460, 07 301, 08 300, 09 348, 10 203. **Race form ("before"): 23 markets in 5 events.** Non-crypto barrier 778 / 87 events. Terminal crypto ("above / below ... on") 8,556 / 1,496. Inclusive wording ("or higher / or more / at least"): temperature 648 markets (648 events), earthquake 74 (20), votes 34 (23), Rotten Tomatoes 16 (7), macro 13 (13), box office 9, approval 1, chart 1 |
| H11 | `du -sh data-dumps`, `df /` | 15 GB; 57 GB free |

| # | Keyless request(s) | Finding |
|---|---|---|
| 1 | Gamma `/tags/slug/crypto` (1) | tag id **21** |
| 2-4 | Gamma `/events?closed=true&tag_id=21&end_date_min/max` for May 2025, Aug 2025 and May 2026, ≤ 3 pages of 100 each (9) | every window hit the 300-event probe cap (crypto Up/Down events dominate), so these are lower bounds: barrier events / markets 5 / 57, 7 / 98, 11 / 151. **Barrier ladders exist before the 2026-10-12 pull's window** (a frame needs the full date walk, not the capped search) |
| 5 | `/public-search?q=what price will bitcoin hit&events_status=closed&limit_per_type=20` (1) | 20 events, ends 2024-11..2027-01; digit-masked title templates "What price will Bitcoin hit October ##-##?" (weekly), "... in <Month>?" (monthly), "... by March ##?", "... in ####?" (yearly), "... September ##-October #?" |
| 6-9 | data.binance.vision HEAD of `{BTC,ETH,SOL,XRP}USDT-1m-2025-10.zip`, GET of the BTC `.CHECKSUM` (5) | all 200; 1.9-2.2 MB per symbol-month; CHECKSUM 88 bytes |
| 10 | `/public-search?q=what price will bitcoin hit october&events_status=closed` (1) | 10 of 20 events end in `[2026-10-01, 2026-10-18)` (outside every R window) |
| 11 | Gamma `/events/<id>` for one of them (end 2026-10-12) (1) | 21 members, `negRisk` false; member templates "Will Bitcoin reach $# October #-#?" and "Will Bitcoin dip to $# October #-#?"; description flags: Binance, 1-minute candle, "High", ET, BTC/USDT, "immediately" all true; `resolutionSource` set; listed less than 7 days before the end |
| 12 | CLOB `prices-history?market=<token>&startTs=<end−14d>&endTs=<end>&fidelity=60` on one member (1) | 200, 164 rows (row count only) |

Request total: **19** GETs (1 + 9 + 1 + 5 + 1 + 1 + 1), under the 20 cap.

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH128** toxicity by class | **include (T), priority, `cpu` lane** | Host-only (H1-H8); the first measurement of *where* the maker's loss comes from, the one number that has blocked every economic route (0 of 95 cells; maker cells -0.2 to -2.6c with a free exit). The labeller is frozen before any mark-out. Honest weaknesses: 4 SCREEN days, 70% sports, and a 2 h capture cadence (§7) |
| **CH118** barrier confusion | **include (R), historical, `net` lane behind CB11/CB12** | 3,948 closed crypto barrier markets in 501 events in the 2026-10-12 pull alone (H10), more before 2025-10 (rows 2-4). The outcome is a public function of Binance 1-minute highs and lows, the source the rules name (H10, row 11). Needs a Binance fetch (premise 1) and CLOB history. **The race arm is dropped**: 23 markets in 5 events, below CH118's own 30-market threshold. **The cross-horizon implied-σ test is reported, uncounted** (k stays small; it reads the same units) |
| **CH119** inclusive-threshold atom | **next batch, not CB13** | The census on host question texts fails. The only large inclusive population is temperature top buckets (648 markets), which are weather markets owned by CB2-W (`h6_weather` sealed, Stage P running). Earthquakes (74) sit inside CB12-E's frame (tags 103038/100184, ends 2024-09..2026-10), so the disjointness the idea requires removes them all. What remains (votes 34, Rotten Tomatoes 16, macro 13, box office 9, others 2: about 74 markets in about 50 events) is below CH119's own kill rule (≥ 60 units with atom ≥ 3 pp) and below ≥ 100 units / ≥ 30 clusters. Re-entry: (a) a temperature arm on ladders listed after CB2-W's Stage-P window, with a written disjointness argument; (b) an earthquake arm after CB12-E's Stage 2 closes; (c) a fresh date walk if it finds ≥ 300 non-weather inclusive markets |
| CH123, CH121, CH125, CH120, CH127 (ranks 3, 5-8) | not in CB13 | Each needs a fresh `net` fetch or collector (revisions API, transcripts, Wayback, Clerk XML, trackers), which this brief deprioritises while CB11/CB12 hold the `net` lane. CH121 also overlaps CB12-M (mention baskets) and should wait for its result. Re-entry: CB14 |

**Sports and categories.** `CB13_SPORTS_IN_PRIMARY = false` (a parameter, as CB8-CB12; sports inclusion is the user's
open decision). The T labeller's SPORTS-FEED class (70% of prints) is computed and **reported, uncounted**. A counted
sports arm would be a later registration, never a change to CB13-T. R is crypto only. Category stays a parameter.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB13 | Evidence ceiling |
|---|---|---|---|
| `live_trades/trades-YYYYMMDD.jsonl` (host; the live large-trade monitor, `takerOnly=true`, cash ≥ $1,000, since 2026-10-12T01:30Z) | collection tooling (`prospective_unregistered`); the monitor's own `uf_*` alerts | **T units**: the paper maker's fills. Whitelisted fields only (§1.4) | SCREEN L1 (dev); HOLDOUT L2 (later live window, sealed) |
| `snapshots/<capture>/rows.csv.gz` and `rows_ext.csv.gz` (host; complete-universe 2 h captures) | E001-E007, E011, SB2-J4/J4-R, CB1-CB7 dev and Stage-2 windows | **T touch** (the paper quote), **T mark quotes**, labeller sidecar fields. Whitelisted columns only | as above |
| `book_sweeps/` (host) | E003, CB3 | depth at the touch for the reported capacity only; never a T statistic | - |
| `history/h13_touch` (**new**, q0277/q0278): crypto barrier events and members (whitelisted fields), parsed rule windows, `prices-history` at fidelity 60; Gamma outcomes only in guarded files (`outcomes_guarded_screen.csv.gz`, `holdout/outcomes_guarded_holdout.csv.gz`) | none | R1, R1-rep, R2 | L1 / L2 (sealed later ends) |
| `history/h13_binance` (**new**, q0279): Binance spot 1m klines (open time, high, low, close) per asset-month, 2024-09..2026-09, CHECKSUM-verified; months ≥ 2026-04 in `holdout/` | none (CB8-B's q0165 never ran) | R features (spot, σ) and the R outcome (touch) | as above |
| `cross_venue/poly_markets.json` (host, 2026-10-12 pull; CB12-X pins it) | cross-venue study; CB12-X (`endDate` only) | **R frame completeness cross-check only**: market ids and questions of barrier templates, field-restricted streaming reader; `outcome_prices` and `volume` never parsed | - |
| `surprise_live/` (E011), `cross_venue_live/` (E009/E010), `e001/`-`e007/`, `forecasts/`, `flow_screen/`, `trade_samples/`; `live_trades/{alerts,outcomes,wallets,stats}.jsonl`, `scores-*.jsonl`, `state.json` | registered experiments and the monitor's alert stream | **never opened by any CB13 path** (runner refuses; unit-tested) | - |
| `h1_first`, `h2_main`, `h3_power`; `h4_seal` (not yet built); `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_*`, `h8_*` (incl. `h8_tail_b`), `h9_flow`, `h10_*`, `h11_*`, `h12_*`; every `cb*_extract/`, `cb3_followup/`, `cb6_followup/`, `creative_batch1..12/` | worn, retired, sealed or batch-owned | **not read**, except id (and, for T, timestamp) columns for exclusion keys through a field-restricted accessor | - |

**Reuse disclosure (T).** SCREEN `[10-12, 10-16)` lies inside the worn capture windows of SB2-J4 (captures before
10-15T21:00Z), CB3-A dev, CB1-D dev, CB2/CB4/CB5/CB6 dev and E011's registered window (from 10-13T14:00Z). T's
statistic (class-split maker mark-out at the recorded touch after a ≥ $1k print) has been computed by none of them:
J4 decomposed the 2 h *reversal of `chg_1h`*, E004 tests the same reversal, E007 the flow continuation (scored once on
2026-10-12 from its 12 earlier periods), and CB3-B filters by state, not class. Label: **"L1, worn captures, new
statistic"**. The HOLDOUT window holds data that do not exist at drafting and is analysed under a frozen plan.

**Reuse disclosure (R).** No AREPO test has sampled barrier ladders. The broad h2/h3 panels, h5 and the CB frames may
hold individual barrier markets. They are removed by key, with the overlap rule of §1.3.

### 1.2 Dates (declared; UTC unless ET is stated)

| Name | Value | Meaning |
|---|---|---|
| `T13_draft` | 2026-10-18T20:15Z | this draft; no CB13 quantity computed |
| `T13_T_screen` | fills with venue time `τ ∈ [2026-10-12T00:00Z, 2026-10-16T00:00Z)` | T Stage 1. **Every touch and mark capture must start before 2026-10-16T00:00Z** (a fill whose 2 h mark capture starts later is "excluded (J4-R boundary)", counted) |
| J4-R window | `[2026-10-16T00:00Z, 2026-10-21T00:00Z)` (`seals/j4r_window.json`; the end can only move forward, and T follows it) | **No CB13 path reads any capture, sweep or print timed inside it** (as CB3 §1.2 and CB6 §1.2) |
| `T13_T_hold` | fills with `τ ∈ [2026-10-21T00:00Z, 2026-10-26T00:00Z)`; touch and mark captures start in `[2026-10-20T22:00Z, 2026-10-26T00:00Z)` | T Stage 2 (prospective at drafting). It ends before CB2's earliest Stage-2 capture start (`max(10-26, freeze + 2 h)`), CB3/CB4 (≥ 10-27), CB5 (≥ 10-29), CB6/CB7 (≥ 10-30). If J4-R's end moves later, `T13_T_hold` starts at the new end with the same end date, and the census records the shortening |
| `T13_T_seal` | 2026-10-26T08:00Z (earliest q0274 start) | every HOLDOUT trades file is complete (daily by receipt; prints arrive about 8 min late) and every mark capture exists |
| `T13_hist_end` | 2026-10-01T00:00Z | no R row (rule-window end, price point, kline used in a feature or outcome, resolution) at or after it |
| R SCREEN / HOLDOUT | event `endDate` in `[2024-11-01, 2026-04-01)` / `[2026-04-01, 2026-10-01)`, sealed | out-of-time split. **R HOLDOUT units also need checkpoint `t ≥ 2026-04-01T00:00Z`**: earlier checkpoints of HOLDOUT events are dropped and counted, so the two splits share no calendar |
| R checkpoints | daily 00:00Z from `max(window start, listing + 1 h)` to `window end − 1 h` | §CB13-R |
| R σ window | Binance 5-minute log returns in `[t − 30 d, t)` | the kline archive starts 2024-09-01 for the 30 days before the first SCREEN checkpoint |
| `T_seal` | 2026-10-22T00:00Z | not binding for CB13 (no CB13 historical row reaches it; R's rows end before 2026-10-01). See §1.3 for SEALED-H4 |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb13.py` refuses every root in the last two rows of §1.1 (field-restricted id/timestamp
  readers excepted). It writes only under `research_lab/creative_batch13/`, `history/h13_touch/` and
  `history/h13_binance/`. The T reader refuses any capture, sweep or print timed in the J4-R window, and any
  `T13_T_hold` row unless the T Stage-1 result file and `seals/cb13_t_holdout_SEAL.json` are committed and their
  hashes verify. The R reader refuses `holdout/` paths in every census and screen.
- **E011 (registered window `[2026-10-13T14:00Z, 2026-11-10)`, analysed once after 2026-11-11T13:00Z).** Both T
  windows lie inside it, and T reads the same complete-universe captures E011 scores. **Why T does not contaminate
  E011.** (1) The hypothesis is different. E011 asks whether the frozen `sm_learned_v2` score selects markets followed
  by surprise moves more often than matched controls; T asks whether maker mark-outs differ by resolution class.
  (2) T never opens `surprise_live/` (alerts, passes, outcomes). It never computes the detector score, the stage-1
  pre-score, the surprise labels (`hit_6h`, `sharp_any_6h`) or `fwd_move_*` for any E011 line, and never conditions
  on or joins to alert, candidate or control status. (3) E011's analysis is frozen code run once, so no E011 choice is
  left that a T result could inform. (4) No T output defines an E011 subgroup, stratum or reading, and the E011 report
  may not cite T. (5) T reads captures read-only, so E011's inputs stay bit-identical. Residual overlap, disclosed:
  T computes 2 h and 6 h forward capture-mid changes after fills, and some fill markets are E011 alerts or controls.
- **E004, E005, E006 (registered, pre-outcome) and E007 (scored 2026-10-12).** T never opens `e00*/`. It never computes
  a `chg_1h`-conditioned move, an arbitrage-band deviation or a signed-share continuation, and no T output defines
  their subgroups. Overlap: forward capture-mid moves on the same captures, as above.
- **E009/E010 (`cross_venue_live/`, to 2026-11-03).** No CB13 path opens `cross_venue_live/`. R reads only
  `cross_venue/poly_markets.json` (the 2026-10-12 historical file, written before E009's registration), for barrier
  ids and questions. T and R define no E009/E010 subgroup.
- **The live monitor's alert stream.** `alerts.jsonl`, `scores-*.jsonl`, `outcomes.jsonl` and `wallets.jsonl` (five
  frozen `uf_*` rules, `prospective_unregistered`) are never opened. T reads `trades-*.jsonl` through a field
  whitelist (§1.4).
- **SEALED-P (CB1-D replication captures from 2026-10-19) and the other batches' live windows (disclosed, as CB5
  §1.3).** `T13_T_hold` overlaps CB1-D's SEALED-P window (neg-risk sums within one event), CB3's dev window
  `[max(T3_fu_start, 10-21), 10-25)`, CB2/CB4/CB5 dev windows and CB6's second dev block `[10-21, 10-28)`. T never
  opens their extract or follow-up tables. Its hypothesis differs from every one of them. CB1-D is frozen, so T cannot
  change its tests. **CB3's dev window is counts-only by CB3's own rule** (no mark-out computed on it), to keep CB3's
  freeze blind. T's HOLDOUT mark-outs there are computed only after 10-26, and CB3's freeze-check record must state
  whether a T result existed at its freeze. The challenger may instead require q0275 to wait for CB3's freeze (§7).
- **SEALED-H4 (SB2; built no earlier than 2026-11-16; origins ≥ `T_seal`).** `T13_T_hold` shares the calendar
  `[10-22, 10-26)` with h4's future origins. T reads no h4 file (none exists) and runs no SB2-candidate analysis. The
  overlap is calendar-only, as for every CB1-CB7 Stage-2 capture window.
- **Historical sealed sets with rows inside T's windows (T exclusion keys, q0271; re-read at q0274).** `h5_cb1` and
  `h5_cb1_ladders` (rows to their fetch clock, about 10-16/17), `h7_cb4_era` and `h7_cb4_series` (to about 10-17),
  `h8_tail`, `h8_tail_b` (fetched to 10-18), `h8_text`, `h8_geo` and any later set whose stored rows reach into a T
  window hold, sealed, the very prints and prices T would read for those markets. **T drops every market id and Gamma
  event id that appears in such a set with any stored timestamp inside a T window.** Ids and timestamps are read
  through a field-restricted accessor, and drops are counted by source. If more than 30% of SCREEN LOW or NEWS fills
  are dropped, T lines carry the label "population thinned by exclusions". A set absent at q0271 is recorded and
  re-read at q0274.
- **Live prospective stages of other batches** (CB10-D q0210, CB12-E q0257, CB12-O q0261, CB9-P Stage 2, CB8-H from
  10-21) may collect in `T13_T_hold`. T never opens their stores and defines none of their subgroups. Their frozen
  tests cannot change. Their markets are not excluded (collection overlap only, as CB12's collectors inside E009's
  window), and the census reports how many HOLDOUT fills fall in markets those stages name, where their frames exist.
- **R exclusion keys (q0276).** Union of: (1) CB11 q0221's `exclusion_keys.csv.gz` (sha256 pinned; q0276 depends on
  its completion); (2) id columns of every sampled or frozen set created since or not in it: `h9_flow`, `h10_sign`,
  `h10_dlad`, `h10_brk`, `h11_*`, **every CB12 frame** (`h12_say`, `h12_quake`, `h12_prints`, and the
  `h12_quake_live`/`h12_opt_live` frames, as CB12 §1.3 requires of CB13), CB8 and CB9 frames; (3) every id in seal
  copies under `docs/research_lab/seals/` committed by then. Keys = market id, Gamma event id, `negRiskMarketID` and
  series id (looked up on Gamma, ≤ 50 ids per request). A frame not yet built is "absent at q0276" (recorded) and
  re-read at the seal-time drops (q0280). If more than 2% of exclusion ids lack metadata, disjointness is "unverified"
  and R1 is "not testable", counted. **CB14 must add CB13's frame ids.**
- **Series and overlap rule for R (declared deviation, for the challenger).** Barrier ladders run as weekly, monthly
  and yearly series, and one asset path resolves every overlapping event. The series-key rule would drop whole series
  if any prior sample held one event; plain id drops would keep events whose path a prior sample already saw. R
  therefore drops by market, event and `negRiskMarketID`, and drops **every R event whose rule window overlaps the
  window of any excluded barrier event of the same asset** (as CB12-E's overlap rule). It does *not* apply the overlap
  rule to excluded terminal or Up/Down events (CB10-D's "above $K on date" ladders, CB8-B and CB9-P Up/Down dailies):
  those markets have daily members, so overlap would drop every R event. Their payoffs are terminal, not path-settled.
  R reads no CB8, CB9 or CB10 data, and R's code never evaluates a terminal "close vs strike" or Up/Down settlement
  comparison on the klines. Those markets are excluded by key and by template regex. The census reports the drops the
  full series rule would have made. If more than 30% of R events are dropped, R lines carry the label "population
  thinned by exclusions".
- **Binance klines and other batches' outcomes (disclosed).** The public BTC/ETH/SOL/XRP path determines CB8-B's (Up/Down)
  and CB10-D's (terminal ladder) outcomes on the same days. R stores klines, but no R path computes a 12:00 ET candle
  comparison, a daily close vs a ladder strike, or any per-day quantity that equals those outcomes. R writes only
  touch indicators for R's own rules. The information is public; the guard is that no R output can stand in for a
  sealed CB8-B or CB10-D result.
- **SEALED-R (R HOLDOUT).** HOLDOUT `prices-history` rows, HOLDOUT guarded outcomes and Binance months ≥ 2026-04 are
  written to `holdout/` subdirectories with listing sha256s. The seal copy `seals/cb13_touch_holdout_SEAL.json` is
  committed by q0280 before the census. The census reads HOLDOUT counts only (market and event counts from frame
  fields; no HOLDOUT feature, because HOLDOUT features need sealed klines). No CB13 path opens a HOLDOUT file before
  R1's Stage-1 result is committed and q0283 is triggered. q0283 verifies the seal hash first.
- **SEALED-T (T HOLDOUT).** q0274 hashes every source file in `T13_T_hold`: each `trades-2026102{1..6}.jsonl` and each
  capture's `rows.csv.gz` and `rows_ext.csv.gz` for captures starting in `[10-20T22:00Z, 10-26T00:00Z)`. It writes the
  HOLDOUT fill table (features only) and the raw mark-quote table (bid and ask at each mark capture; no mark-out
  computed) to `creative_batch13/t_holdout/`, with listing sha256. The seal copy `seals/cb13_t_holdout_SEAL.json` is
  committed before q0275. **Source files may later be archived and deleted from the host under the capsule-first
  policy.** If so, q0275 restores them byte for byte with `restore_from_archive.py` and verifies the sealed hashes, and
  never re-derives a missing file.
- **Outcome guards.** T has no resolution outcome (mark-outs are price-based; T3 exits at a recorded touch). R: Gamma
  `outcomePrices` and `umaResolutionStatus(es)` go only to the guarded files. **R's primary outcome is computed from the
  Binance klines by the frozen rule parser, never read from Gamma** (CB9-P's guard). Gamma outcomes are opened only by
  q0282 (the agreement audit) and q0283 (R2 pays what the venue paid). Census paths read klines only before each
  unit's checkpoint `t` (a guarded kline accessor; unit-tested).

### 1.4 Rules files

- `seals/cb13_rules.json` (before q0270), hashed per part:
  - **`common`**: refused roots, the J4-R pin, seeds, bootstrap, the small-G rule, Holm/BY settings, disk guards and
    smoke criteria.
  - **`T`**: windows, the touch, fill, first-crossing and mark rules, age limits, exclusions and their sources, the
    **labeller (class definitions, precedence, every regex and vocabulary list, the sports list, the audit protocol
    and seeds)**, LOW/NEWS membership, cluster ways, gates, placebo strata, the T3 exit rule and fee policy.
  - **`R`**: tag id 21, the barrier title and member templates, the excluded terminal and Up/Down templates, the
    description flags, the rule-window parser (written from out-of-window events, ends in `[2026-10-01, 2026-10-18)`),
    the asset map, the windows and split, checkpoints, the price rules, the σ rule, the touch formula, decided-rung
    and price-band rules, the GRP loadings, R2's band half-spreads and fee policy, the Binance symbol/month list, and
    the kline usability rule.
- `model_specs/cb13_v1.json` (the freeze) is likewise hashed in parts T and R. A job pins only the part hashes it needs.
- Jobs refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any T mark, R outcome or R
  price.** The labeller may be revised **once** before the T freeze, and only on the labeller audit (titles only, §CB13-T).
- **Field whitelists.** *Monitor prints:* `ts, condition_id, token_id, outcome_index, price, size, cash, title, slug,
  ctx_event_id, ctx_market_id, ctx_category, ctx_fee_type`, plus `tx16` in memory only, for transaction aggregation
  (never written). **Not parsed:** `side`, `key`, `recv_ts`, `wallet_*`, and every other `ctx_*` (post-receipt
  context, including `ctx_chg_1h`). *Capture rows:* `capture_id, capture_start_utc, received_utc, market_id,
  condition_id, event_id, closed, active, binary, best_bid, best_ask, liquidity, end_date, clob_token_id_0, neg_risk,
  neg_risk_market_id`. **Not parsed:** `chg_1h/1d/1w`, `last_trade_price`, `volume24hr`. *Sidecar:* `fee_type,
  fee_category, fees_enabled, taker_base_fee, fee_schedule, series_slugs, event_ids, created_at,
  order_price_min_tick_size, rewards_min_size, rewards_max_spread, clob_rewards, accepting_orders`. **Not parsed:**
  `uma_resolution_statuses`, `open_interest`, `volume_num`. *Gamma (R):* as CB12 §1.4 (ids, question, slug,
  `clobTokenIds`, outcome labels, `startDate`, `createdAt`, `endDate`, `negRisk`, `negRiskMarketID`, event ids, series
  ids, tag ids, `feeSchedule`, `resolutionSource` host, the `description` sha256 plus frozen flag booleans and the
  parsed window, strike and direction). `outcomePrices`, `umaResolutionStatus(es)` and `closedTime` reach only the
  guarded files. A unit test feeds fixtures carrying every forbidden field and asserts that no parsed row, file or log
  contains them.

## 2. Common rules (deltas from CB12 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| T1, T2, R1 | none charged (mechanism, mid-marked maker net, forecasting). T2's quantity *is* a maker's net per filled share at a free mid exit: an **upper bound**, labelled so in every line |
| T3 (Stage 2) | paper maker entry at the **recorded** touch (maker fee 0, no rebate); exit as a taker at the **recorded** adverse touch of the 2 h mark capture (bought → sell at `bid_h`; sold → buy at `ask_h`); taker fee `r·x(1 − x)` on the exit, `r` = the market's sidecar fee rate, policy `max_if_unknown` (unknown → 0.07, as `ECONOMIC_CONDITIONS_STUDY.md`); size ≤ 100 shares; displayed depth unknown in captures (sweep depth reported where the market was swept) |
| R2 (Stage 2, modelled) | buy the model-favoured token at `a = p_t + hs(p_t)` (YES) or `a = 1 − p_t + hs(1 − p_t)` (NO), `hs` = half the band median spread of `EXECUTION_COSTS.md` (bands < 0.05, 0.05-0.20, 0.20-0.80, 0.80-0.95, ≥ 0.95 → 2.05, 1.5, 1.1, 1.5, 1.25c); taker fee `r·a(1 − a)`, `r = max(feeSchedule.rate, 0.07)` (crypto); held to resolution; **paid on the Gamma resolution** (what the venue paid, as CB12-E2/O2) |
| Binding cost robustness | T3: +0.5c on the exit keeps net > 0. R2: +1.0c on `a` keeps net > 0 |

R2 uses declared, not recorded, quotes (no historical books without pmxt). It is a "modelled-cost economic check (L1/L2
on the sealed window)". Recorded asks enter only in Stage P-R (§2.9). T3 is at recorded touches.

### 2.2 Clocks

- **Monitor prints.** Venue `ts` (s) is the fill time `τ`. Prints with the same `tx16` and `condition_id` are
  aggregated in memory into one transaction (YES-terms VWAP, total size); the hash is discarded. YES terms: a print on
  outcome index 1 at `x` is a YES print at `1 − x`. Receipt time is not used: T replays a resting quote, it does not
  act on the monitor.
- **Capture touch and marks.** Each capture row has its own `received_utc` (a capture takes about 6 min). The **touch**
  for a fill at `τ` is the market's row in the latest complete capture with `received_utc < τ`. **Touch age** =
  `τ − received_utc`. The **mark** at horizon `h` is the market's row in the first complete capture with `received_utc
  ≥ τ + h`, usable iff `received_utc ≤ τ + h + 2 h` (else "no mark (capture gap)", counted; the 10-14 outage is the
  main case). Gamma's `best_bid`/`best_ask` are the touch. Crossed or one-sided rows are ineligible and never repaired.
- **CLOB `prices-history` (R).** As CB12 §2.2: a point at fidelity 60 is usable from stamp + 3,600 s. `p_t` = the last
  usable point before `t` with age ≤ 6 h; `p_reg` = the last usable point before `t − 6 h` with age ≤ 24 h, a
  different point from `p_t`. Either missing → "unavailable (no price)", counted.
- **Binance klines (R).** A 1m candle `[o, o + 60 s)` is usable at `t` iff `o + 65 s ≤ t` (CB8 §2.2). `S_t` = the close
  of the last usable candle. The touch outcome over `[t, T]` uses candles with `o ∈ [t, T)` (the rule's window end
  `T`, ET-converted by the frozen parser) and reads `high` (reach) or `low` (dip). Only screen and rep paths may open
  candles at or after `t` (guarded accessor).
- `closedTime` is never a population condition, origin or feature.

### 2.3 Uncertainty and decision rule

As CB12 §2.3: unweighted primary; one-sided p = the max over the declared cluster ways; 2,000-draw cluster bootstrap,
**seed 1313**; small-G rule as CB10 §2.3 (G ≥ 30 CR1; 15-29 CR2 with t(G − 1) and the Webb wild bootstrap, 9,999
draws; G < 15 the way leaves the max and its leave-one-cluster-out sign rule binds, as A-C1); top-5 drops; ≥ 100 units
and ≥ 30 clusters in the event way for testability; "unknown" never counts as met (one declared deviation: GTI, §CB13-T).
- **Cluster ways.** **T:** Gamma event (CR1; G ≈ 100-300 per class); **6-hour block** of `τ` (UTC 00/06/12/18,
  the cohort cadence; G_SCREEN ≤ 16, so CR2 if ≥ 15, else leave-one-block-out). The 6 h block is longer than the 2 h
  mark, so adjacent blocks share little. **UTC day** (G = 4 in SCREEN, 5 in HOLDOUT: never in the max; the
  leave-one-day-out sign rule is always binding). **R:** Gamma event; ISO week of the checkpoint (one crypto path per
  week; G ≈ 70 SCREEN, 26 HOLDOUT); asset × ISO week.
- **Stage 1 (3 tests).** Advance iff one-sided p < 0.01, the §2.4 floor is met, and every binding placebo, robustness
  check and gate holds, **and** the test passes a batch Holm step-down at one-sided α = 0.05 over k1 = 3 (fixed). Holm's
  first step is α/3 = 0.0167, so any p < 0.01 passes it. The Holm step is stated for completeness and can never
  withdraw an advance. BY label (q = 0.10 over `battery2.cumulative_count()` at the run) is triage only.
- **Stage 2.** One Holm at one-sided α = 0.05 over every CB13 test reaching Stage 2, each in its Stage-1 direction (T3
  and R2 in the declared direction, net > 0). A test that finishes before k2 is known is judged against **α/5** (k = 5,
  the largest possible Stage-2 count: Holm's first step, never withdrawn). Once every triggered test is final, the full
  Holm over the actual k2 is applied once and can only add passes. Labels: T1-rep, T2-rep "later live window
  replication, event-disjoint (L2)"; T3 "recorded-touch round trip (L2)"; R1-rep "out-of-time replication on a sealed
  later window (L2)"; R2 "modelled-cost economic check on the sealed window (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| T1 | mechanism contrast | `D = M̄_LOW,2h − M̄_NEWS,2h ≥ +0.5c` per filled share (CH128's class-difference floor) |
| T2 | maker sign (mid-marked, upper bound) | `M̄_LOW,2h ≥ +0.25c` per filled share (half of the 0.5c median half-spread at the fill, H8: the maker keeps at least half the spread after adverse selection) |
| T3 (Stage 2) | economic, recorded touches | net ≥ +0.5c per filled share after the exit fee |
| R1 | forecasting | slope `β̂ ≥ 0.30` of `Y − p_t` on `q_touch − p_reg` (CH118's floor) |
| R2 (Stage 2) | economic, modelled cost | net ≥ +1.0c per share after fee (CH118's floor) |

### 2.5 Counting (M3 rule)

- Kinds **`cb13_test`** (Stage-1 per-test lines), **`cb13_replication`** (Stage 2, including T3 and R2) and
  **`cb13_descriptive`** (EXCLUDE). Descriptive lines cover the smoke, censuses, gates, the labeller audit, class
  strata including SPORTS-FEED and SCHEDULED-EVENT, the all-prints and size-weighted T variants, capacity, the 6 h
  readings, the cross-horizon implied-σ comparison, R's reach/dip and asset strata, and the Binance-Gamma agreement
  audit. Per-test lines count 0 themselves. **The tests are the `n_tests` of the `ml_explain` count lines** (as CB11
  and CB12); placebo lines count 0. New `battery2.KIND_RULES` entries mirror CB12's; unknown kinds raise.
- **Count lines and `n_tests`:** `creative_batch_13:T` **2** (T1, T2); `creative_batch_13:R` **1** (R1). Replication
  lines `creative_batch_13:<family>:rep` carry `n_tests` = that family's triggered Stage-2 tests (T ≤ 3: T1-rep, T2-rep,
  T3; R ≤ 2: R1-rep, R2).
- **Triggers.** T1-rep iff T1 advanced; T2-rep and T3 iff T2 advanced; R1-rep and R2 iff R1 advanced.
- **Cumulative count: 1,181** (committed `trials.jsonl` at HEAD `ee0bc96`, `battery2-count-v1`; the host-unioned value
  is recorded by every counting job).
- **CB13 adds 3 fixed tests and up to 5 conditional ones. Budget: 3-8**, so the cumulative count becomes 1,184-1,189,
  plus whatever CB6-CB12 add first.
- Tests behind a failed or unknown gate (smoke, disjointness, GL, GT, GTP, GTI, GR, GRP, the Stage-2 population
  minimums, availability) are "not testable" or "not run" (p = 1) and are **still counted**. A job waiting on exit 75
  is "pending" and produces no line. Conditional tests count only if their trigger fires; a triggered test that cannot
  run is counted with p = 1.

### 2.6 Placebos and robustness (common)

Design rule as CB12 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 13101-13120.
Common binding robustness for any advance: (i) the declared cost robustness (§2.1) for economic tests; (ii) the p
threshold and the floor hold without the top 5 clusters of each way; (iii) sign by period (T: leave-one-day-out; R:
each SCREEN half by window end); (iv) unavailable units are excluded and counted by label, never imputed. A test whose
available share of eligible units is < 60% is "not testable (availability)".

### 2.7 Pre-freeze census (counts only; q0272 for T, q0281 for R)

Outcome guards first; field-restricted accessors. A unit test asserts that no census path receives a mark quote, a
capture row received after any fill's `τ`, a kline at or after any unit's `t`, a Gamma outcome or a later price used
as a target. Features (touches, fill sides, spreads, labels, `q`, `p`, horizons) and unit counts may be computed.
- **T.** Prints and transactions by day, label and fee category; key drops by source; fills by touch age band,
  crossing vs inside, first-crossing collapse; fills by class, event, 6 h block and day; spread and price bands;
  time-to-scheduled-end bands; excluded units by label ("J4-R boundary", "scheduled end within 3 h", "one-sided",
  "no row"); depth from sweeps (reported). **Gate GT:** ≥ 500 SCREEN LOW fills in ≥ 60 events and ≥ 500 SCREEN NEWS
  fills in ≥ 60 events (CH128's 500-fill class floor), else T1 "not testable (population)", and T2 also if LOW fails.
  **Gate GL (labeller audit):** §CB13-T. **Power gate GTP (feature-only; as CB12 GFP).** Each T test's own estimator and
  cluster ways run on a **pre-fill proxy outcome**: the move of the capture mid from the capture before the touch
  capture to the touch capture, signed by the maker direction. It has the variance and dependence of a 2 h mid move
  and contains no post-fill information. Only the clustered SEs are written (the max over ways); no proxy point
  estimate is written to any output (unit-tested). `MDE = (z_0.99 + z_0.80) x 1.2 x SE`. **T1 is "not run (power)" if
  MDE > 1.0c, T2 if MDE > 0.5c (2 x floor, as CB12-F), counted.**
- **R.** Events and markets by template (weekly, monthly, "by", yearly), asset, direction and end month; parser
  failures; flag failures; key and overlap drops by source (plus the full series-rule counterfactual); the
  poly_markets cross-check (share of its post-2025-10 barrier ids the frame found); eligible (market, checkpoint) units
  by label ("decided", "before window start", "unavailable (no price)", "outside [0.03, 0.97]"); `q − p_reg`
  distributions (features, klines before `t` only); HOLDOUT market and event counts only. **Gate GR:** ≥ 300 SCREEN
  markets with units in ≥ 60 events and ≥ 30 ISO weeks; parser failures ≤ 10% of markets; ≥ 95% of markets carry the
  Binance 1-minute high/low flags (else R1 "not testable (basis)"); the frame finds ≥ 98% of the poly_markets barrier
  ids in its window (else "not testable (frame completeness)"). **Power gate GRP (feature-only).** Simulated outcomes
  calibrated to the prices: `Y*_i = 1{Φ(Z_i) < p_t,i}`, `Z_i = s_i·(√0.4·W_{a,w} + √0.2·X_w) + √0.4·ε_i`. Here
  `W_{a,w}` is a shared asset-week factor, `X_w` a cross-asset week factor, and `s_i = +1` for reach and −1 for dip
  rungs (one path pushes reach and dip rungs in opposite directions); the loadings are declared. 500 draws (seed
  13123). `MDE_R1 = (z_0.99 + z_0.80) x 1.2 x max(SD(β̂*), mean SE per way)`. **If `MDE_R1 > 0.60` (2 x floor), R1 is
  "not run (power)", counted, and R1-rep and R2 are not triggered.**
- MDEs are recomputed from these counts and never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collectors. Queue rules as CB12 §2.8: one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 x `mem_mb`, and a 02:45-05:30 UTC blackout for `mem_mb ≥ 500`. **T jobs
  also avoid the collector pass**: they start only outside `:31-:55` of even hours, or yield to the pass lock. No pmxt
  ingress. Every reader streams one capture, one market or one asset-month at a time. `mem_mb` ≤ 800 everywhere.
  **800 is justified** for q0271/q0274 (one capture's 274,000 rows read with column whitelists into pandas, filtered
  to printed markets, about 150 MB, plus the fill table) and q0282/q0283 (two years of 1m klines for one asset as
  float32, about 20 MB, plus about 30,000 units and 2,000 bootstrap draws on cluster-level sufficient statistics).
- **Network** (`net` lane, priorities 15-19; ≤ 2 rps Polymarket, ≤ 1 rps Binance; T has none):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0270 | smoke (`cpu` lane) | ≤ 30, < 5 min | 0.001 GB |
  | q0276 | R exclusion keys (increment over CB11 q0221) | ≤ 600 Gamma, ≤ 6 min | ≤ 0.01 GB |
  | q0277 | R frame: Gamma `/events?closed=true&tag_id=21` in one-day `end_date` windows over `[2024-11-01, 2026-10-01)` (about 700 days; crypto Up/Down events dominate the tag, about 5-10 pages a day), barrier templates kept at parse; series lookups | ≤ 8,000, ≤ 70 min | ≤ 0.01 GB |
  | q0278 | R prices: per member `ceil(span / 14 d)` bounded `prices-history` requests at fidelity 60, span = [max(`createdAt`, window start − 1 d), window end]; planning about 6,000-8,000 members (3,948 after 2025-10 in the pull alone) x 1-3 requests, yearly ladders up to 27; the exact Σ is computed by q0277 from frame fields (counts only) and recorded before q0278 is committed | ≤ 25,000 (planning about 12,000-16,000), ≤ 3.5 h | ≤ 0.05 GB |
  | q0279 | Binance: monthly 1m spot zips + `.CHECKSUM` for each parsed asset (BTC, ETH, SOL, XRP; any other parsed asset with a Binance spot USDT pair), 2024-09..2026-09 (25 months); zips parsed in memory and discarded | ≤ 400, ≤ 10 min at 1 rps | ≤ 0.2 GB (npz) |

  Historical `net` total **≤ about 34,000 requests (planning about 22,000), about 3-5 h of `net` lane at 2 rps**,
  behind CB11's about 10-11 h and CB12's about 6-10 h. **A fetch that has not completed (its `*_complete` status absent)
  is "pending" and is never analysed partially.**
- **Disk guard.** Every CB13 data job declares `--disk-cap-gb` and `--data-dumps-cap-gb 40`, and exits **75** if
  data-dumps + its cap > 40 GiB **or** root free disk − its cap < 4.5 GB. CB13 output caps total **≤ 0.35 GB** (T ≤ 0.05,
  R ≤ 0.3). Exit-75 waits are "pending" (CB10 §2.8 rule). CB13 never deletes or moves host data. If T's source
  captures are archived and deleted before q0271 or q0274 runs, the job restores them with `restore_from_archive.py`
  and verifies the archived hash first. Nothing is re-derived.
- **Network etiquette.** As CB12 §2.8 (shared `Limiter`, collector yield, 429 / `Retry-After` back-off, stop on
  repeated 429, collector-health stop; descriptive User-Agent for Binance at ≤ 1 rps).
- **Stop rules.** 5 CPU-hours per family. A job that fails twice for the same non-transient reason stops and is
  recorded. A null is "not detected at MDE x". **No re-screen of a failed CB13 test** with altered classes, labeller
  rules, LOW/NEWS membership, touch or mark rules, age limits, horizons, windows, templates, σ rules, formulas, price
  rules, cutoffs or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2: a later live window for T; a sealed later
historical window for R) → separate prospective confirmation (Stage P) → economic validation at recorded prices with
fees, spread and depth.
- **Stage P-T.** Fresh live windows after CB3's Stage-2 window closes (about 2026-11-24), with the touch read **at the
  print** (a CLOB `/book` read triggered by the monitor's receipt, queue position unknown and disclosed) instead of
  the 2 h capture, depth recorded, and the class map frozen from CB13. The economic test is a passive two-sided paper
  maker in LOW markets only, with passive and taker exits both reported.
- **Stage P-R.** Barrier ladders listed after the Stage P freeze; a daily 00:00Z CLOB `/book` read of every rung
  (recorded asks, depth); R2's rule at recorded asks; outcome from the live Binance REST klines as served.

---

## 3. Tests

### CB13-T: Maker toxicity by resolution class (CH128)

**Question.** When a large taker print fills a resting quote at the touch, does the quote's adverse selection depend on
how the market resolves? Is it small enough in public-statistic and path-settled markets for a maker there to keep
part of the spread?

**Mechanism.** Information that hurts a maker arrives differently by class. In public-statistic markets it arrives on
a schedule everyone sees, so a maker can step aside. In path-settled markets it is the spot price, which a maker with
the feed already holds. In unscheduled-news markets it comes as a print from someone who read the wire first. The
economics studies pooled classes, so their -0.2 to -3.7c is a class average. If the losses sit in NEWS, the maker route
is a class choice, not a dead end. Who pays in LOW: retail and the reward bots' hedges. Why it persists: reward bots
quote by reward band, not by class.

**Prior work.** ECONOMIC_CONDITIONS part B (passive entry: filled orders move against the maker 1-7c; best cell
-0.21c with a free mark exit), SB2-J2 (net taker about -2.5c), CB3-B (presence filters by state), CH16, CH40, CH43,
CH63. None used the class axis. T is not a re-screen of any of them.

**Population (q0271; frozen).** Monitor prints with venue time in `T13_T_screen`, aggregated to transactions;
binary markets; market and event key drops (§1.3).
- **Touch eligibility:** the touch row is two-sided (`0 < bid < ask < 1`), the touch mid lies in `[0.03, 0.97]`, the
  spread is ≤ 10c, **touch age ≤ 60 min**, and the market's capture `end_date` is ≥ `τ + 3 h` (so a 2 h mark can exist
  before the scheduled end).
- **Paper fill (side-free):** with YES-terms transaction price `P` and touch `(b0, a0)`: `P ≥ a0` → the maker sold YES
  at `a0` (`d = −1`); `P ≤ b0` → the maker bought YES at `b0` (`d = +1`); `b0 < P < a0` → no fill (counted; 2-12% of
  prints per group, H8).
- **One resting quote per side per pass:** for each (market, touch capture, side), only the **first** crossing
  transaction after the touch row is a fill. That is the paper maker's single quote at the recorded touch; later prints
  in the pass are reported in the all-prints variant. Fill price = the touch quote (`a0` or `b0`), never the print
  price (conservative when the print traded through).
- **Size:** each fill is one unit (unweighted per filled share). Size-weighted results are reported.

**Labeller (frozen in part T before q0271; no outcome, mark or price is an input).** Inputs per market: the print's
`title` (the market question) and `slug`, `ctx_category` and `ctx_fee_type` where present, and the touch capture's
sidecar `fee_type`, `fee_category` and `series_slugs`. Classes, applied in this precedence:
1. **SPORTS-FEED**: a sports fee type or category (`sports_fees*`), a frozen sports series or slug list, or the frozen
   sports title regex (CB12 §0.4's list plus "vs.", "O/U", spread and moneyline forms). Reported, uncounted.
2. **PATH-SETTLED**: an asset term (frozen crypto, equity, index, commodity and FX lists) together with a price form
   ("Up or Down", above/below, reach/hit/dip, "price of", "close at/above", "between $"); or fee type
   `crypto_fees*`/`finance_prices_fees`.
3. **PUBLIC-STATISTIC**: a published number from a named statistical source (macro releases: CPI, inflation,
   unemployment, payrolls, GDP, jobless claims; temperature and precipitation; earthquake counts and magnitudes; box
   office; review and chart scores; post or tweet counts; poll and approval numbers); or `weather_fees`. Earthquake
   markets stay in this class (CB12-E is historical before 2026-10-01 plus its own live collector, §1.3).
4. **SCHEDULED-EVENT**: an event with a public date (elections, primaries, nominations, debates, award shows, Fed/FOMC
   and central-bank decisions, earnings, court rulings with a set date, speeches and mention markets, launches and
   votes with a scheduled time); or `mentions_fees`. Reported, uncounted.
5. **UNSCHEDULED-NEWS**: every other non-sports market, mostly "will X happen by <date>" (resign, out as, ceasefire,
   strike, invade, deal, release, indictment, announcement, death).
6. **UNKNOWN**: no title and no sidecar row. Excluded and counted (> 5% of SCREEN fills → GL fails).

**LOW = PATH-SETTLED ∪ PUBLIC-STATISTIC; NEWS = UNSCHEDULED-NEWS** (declared now, from CH128's prediction).
- **Writing the labeller.** Regexes and lists are written from the class definitions above, from the fee vocabulary
  (H6) and from question texts of `cross_venue/poly_markets.json` markets ending before 2026-10-01. Those markets are
  never T units, and the field-restricted reader takes questions only. No SCREEN or HOLDOUT price, touch or mark is
  used.
- **Gate GL (audit, blind).** After q0270, a seeded sample of 200 SCREEN markets, stratified by label (seed 13121), is
  labelled by an independent `science-reviewer` pass from `title` and `slug` alone, under the written definitions, with
  no labeller output and no price. **PASS** iff the agreement on {LOW, NEWS, other} is ≥ 85% and ≥ 80% within each of
  LOW and NEWS. One revision is allowed on FAIL, re-audited on a fresh 200 (seed 13122). A second FAIL → T1 and T2 "not
  testable (labeller)", counted. The audit file is committed before q0271, and the labeller hash is final from then.

**Mark-out.** For a fill with maker direction `d` and quote `q`: `M_h = d·(mid_h − q)` cents per share, `mid_h` the
mark-capture mid (§2.2), `h = 2 h` primary. Decomposition: `M_h = s0/2 − AS_h`, with `AS_h = −d·(mid_h − mid0)` the
adverse selection. So `M_h > 0` iff adverse selection stays below the half-spread (CH128's sign condition). A mark row
whose spread is > 10c is "wide mark", counted; it enters the worst-case check below. A market that closes before its
mark is "closed before mark", counted, with the binding worst case.

**T1 (class contrast).** `D = M̄_LOW,2h − M̄_NEWS,2h` (fill-level means), one-sided > 0, floor 0.5c; p = max over the
event and 6 h block ways (§2.3), with the leave-one-day-out sign rule binding.
- **Binding pre-fill placebo.** The same statistic with the pre-fill move (from the capture before the touch capture
  to the touch capture, signed by `d`) in place of `M`. It must not pass p < 0.01. *Alternative guarded:* class-specific
  trend or momentum in the SCREEN days (a crypto drift week) read as toxicity.
- **Binding composition placebo.** Class labels are permuted across events within strata of (touch spread band x
  touch mid band x time-to-end band: < 1 d, 1-7 d, > 7 d); 200 draws (seed 13101). *Alternative guarded:* the contrast
  comes from spread, price or horizon composition rather than class.
- **Robustness (binding).** Touch age ≤ 20 min keeps the sign. The 6 h horizon keeps the sign. The **adverse-touch mark**
  (`mid_h` replaced by `ask_h` for maker sells and `bid_h` for maker buys, every wide-mark and closed-before-mark unit
  included at its adverse touch or worst case) keeps the sign. Excluding transactions ≥ $10,000 keeps the sign. Each
  fill side (maker sells, maker buys) keeps the sign. Event-weighted means keep the sign. Top-5 drops by event and by
  block; leave-one-day-out.
- **Attribution (binding for the label "class effect").** OLS of `M_2h` on the LOW and NEWS indicators plus touch
  spread band, touch mid band, time-to-end band, transaction size band and log capture liquidity. Credit "class
  effect" only if the LOW − NEWS coefficient keeps ≥ half of `D`; otherwise the label is "composition, not class".
- **Reported (uncounted).** Per-class `M̄` at 2 h and 6 h, including SPORTS-FEED and SCHEDULED-EVENT, which says
  where the economics studies' losses sit; the all-prints variant; reward-band (`clob_rewards` present) vs not; capacity
  (sweep depth at the touch where swept).

**T2 (maker sign in LOW).** `M̄_LOW,2h`, one-sided > 0, floor +0.25c; label "mid-marked maker net, upper bound (free
exit), L1".
- **Binding sign-flip calibration.** One coin per event flips `d`; 200 draws (seed 13102). *Alternative guarded:*
  within-event and within-block dependence makes the clustered p anti-conservative.
- **Binding pre-fill placebo** as in T1, applied to `M̄_LOW`.
- **Robustness (binding).** Touch age ≤ 20 min keeps the sign. The 6 h horizon keeps the sign and ≥ half. Each LOW
  component (PATH-SETTLED, PUBLIC-STATISTIC) with ≥ 200 fills keeps the sign. The **worst case** (wide-mark units at
  the adverse touch; closed-before-mark units at `d·(Y_adv − q)` with `Y_adv` the adverse extreme 0 or 1) keeps p <
  0.01 and the floor. Excluding transactions ≥ $10,000; top-5 drops; leave-one-day-out.

**Gate GTI (cadence informativeness; CH128's kill, computed in q0273 before T1/T2 are read).** On fills with a later
monitor print in the same market in `[τ + 2 h − 30 min, τ + 2 h + 30 min]`, the sign of the print-based move
(`d`-signed, from the touch quote to the YES-terms VWAP of those prints) agrees with the sign of `mid_2h − q` in
> 70% of pairs where both are nonzero. FAIL → T1 and T2 "not testable (cadence)", counted. **Declared deviation:** with
fewer than 200 evaluable pairs, the gate is "not evaluable" and every T line carries the label "cadence informativeness
unverified (n < 200)", rather than "unknown = not met". Monitor prints are sparse, so the challenger should rule on
this.

**Power (planning; GTP decides).** From H8, SCREEN fills within 60 min: about 1,100-1,500 LOW (crypto 553,
econ+finance 532, plus labelled PUBLIC-STATISTIC from the unenriched prints) and about 700-1,000 NEWS before the
first-crossing collapse and exclusions; G_event about 230 (LOW) and 190 (NEWS); 14-16 six-hour blocks. With an SD of
`M_2h` of about 3c and an event design effect of 2: `SE(D) ≈ 0.18c` → **MDE_T1 ≈ 0.7c** against the 0.5c floor;
`SE(M̄_LOW) ≈ 0.12c` → **MDE_T2 ≈ 0.45c** against 0.25c. Both floors sit below the MDE, so T detects only about 0.7c
and 0.45c or more. The first-crossing collapse and the block way can raise both MDEs past the GTP cuts. GT may fail
on NEWS (500 fills) and is reported as such.

**Stage 2 (conditional; q0274, q0275).** On `T13_T_hold`, with the same frozen rules and labeller, **event-disjoint**:
HOLDOUT drops every Gamma event with a SCREEN fill (counted by class). If more than 40% of HOLDOUT LOW or NEWS fills
are dropped, the lines carry the label "HOLDOUT thinned by event overlap", and a variant keeping them is reported. Each
Stage-2 test needs ≥ 500 fills of each class it uses in ≥ 60 events, else "not run (power)", counted.
- **T1-rep, T2-rep**: the Stage-1 statistic, placebos and robustness.
- **T3 (economic at recorded touches; triggered by T2).** LOW fills; `net = d·(x_exit − q) − r·x_exit(1 − x_exit)`,
  with `x_exit` the adverse touch of the 2 h mark capture (§2.1). One-sided > 0, floor +0.5c, robustness +0.5c on the
  exit. Expected to be hard: the exit pays a half-spread and a fee against a maker's half-spread, which is why it is
  the honest recorded-price check. A pass would need adverse selection well below zero in LOW.

### CB13-R: Barrier-versus-terminal confusion in "reach / dip to" ladders (CH118)

**Question.** In closed crypto barrier ladders ("Will Bitcoin reach / dip to $B <window>?", settled on any Binance
1-minute high or low in the window), does the driftless reflection-principle touch probability predict resolution
beyond the market price?

**Mechanism.** For a driftless log-diffusion, `P(touch B by T) = 2·(1 − Φ(|ln(B/S)| / (σ√τ)))`, about twice the
terminal probability for far strikes. If the crowd prices barrier rungs with the terminal intuition of the daily
"above $K" ladders, far-strike YES is underpriced in both directions. Who pays: retail buying near strikes and reward
bots centred on the mid. Why it persists: the UI's "chance" invites terminal reading, and no bot seen so far prices
touch probabilities (CB10-D anchors terminal ladders only).

**Prior work.** CH89/CB10-D (terminal, Deribit), CH76/CB8-B (terminal minutes), CH30 (15-minute digital). R reads no
CB8, CB9 or CB10 data and shares no market (§1.3).

**Population (q0277; frozen).** Gamma closed events under tag 21, with `endDate` in R SCREEN ∪ R HOLDOUT, found by the
one-day date walk (not the capped search). Event title matches the frozen barrier template (`^What price will
(<asset>) hit .+\?$`), or a member question matches `^Will (<asset>) (reach|hit|dip to) \$[\d,.]+k? .+\?$`. The frozen
terminal templates ("above / below ___ on", "Up or Down") are excluded and counted. Each member must be binary, with a
parsed strike `B` and direction (reach: up-barrier on `high`; dip: down-barrier on `low`). The rule window `[T0, T]` is
parsed from the description in ET. All frozen flags must be present: Binance, the 1-minute candle, High (reach) or Low
(dip), and a USDT pair matching the asset map. Key and overlap drops follow §1.3. Race-form members ("before") are
excluded and counted (23 in the pull, H10).
- **Units:** (market, daily 00:00Z checkpoint `t`) with `T0 ≤ t ≤ T − 1 h`, listed ≥ 1 h before `t`, **not decided**
  (no touch in `[T0, t)` on the klines; decided units are counted), `p_t ∈ [0.03, 0.97]`, `p_reg` available.
  Weighting: **each market weight 1, split over its units**, so yearly ladders with about 300 checkpoints do not
  dominate. The unit-weighted result is reported.
- **Anchor (frozen; no fitting to outcomes).** `σ_t` = the annualised SD of Binance 5-minute log returns of the asset in
  `[t − 30 d, t)` (×√105,120). `τ` = `(T − t)` in years. `q_touch = min(1, 2·(1 − Φ(|ln(B/S_t)| / (σ_t√τ))))`.
  `q_term = 1 − Φ(|ln(B/S_t)| / (σ_t√τ))` is used for the attribution only.
- **Outcome (computed, guarded).** `Y = 1` iff a candle with open in `[t, T)` has `high ≥ B` (reach) or `low ≤ B`
  (dip). The Gamma outcome is used only for the agreement audit (< 97% agreement → the label "settlement basis") and
  for R2's payoff.

**R1 (forecasting).** The market-weighted OLS slope `β̂` of `(Y − p_t)` on `(q_touch − p_reg)` over SCREEN units,
one-sided > 0, floor 0.30; p = max over the event, ISO-week and asset-week ways. The regressor uses `p_reg` (6 h
earlier, a different price point), so `p_t`'s own noise never enters it (CB10's shared-noise rule).
- **Binding sign-flip calibration.** One coin per ISO week flips `(q_touch − p_reg)`; 200 draws (seed 13103).
  *Alternative guarded:* the common weekly path makes the clustered p anti-conservative.
- **Binding stale-price placebo.** The same slope with `q_touch` replaced by `q_spot` = `p_reg` moved by the
  6 h Binance return through the touch formula's delta (`q_spot = q_touch(S_t) − q_touch(S_{t−6h}) + p_reg`). It must
  not pass p < 0.01 with a larger slope than R1. *Alternative guarded:* the price simply lags the spot, and any spot
  anchor would "predict" `Y − p`.
- **Attribution (binding for the label "barrier-versus-terminal confusion").** Joint OLS of `(Y − p_t)` on the
  reflection gap `g = q_touch − q_term` and on `(q_term − p_reg)`. Credit the label only if the coefficient on `g` is
  ≥ 0.30 and ≥ half of R1's `β̂`. Otherwise the label is "volatility anchor, not barrier confusion".
- **Robustness (binding).** Reach and dip separately keep the sign. BTC alone keeps the sign. `σ_t` x 0.8 and x 1.2 each
  keep the sign. Drift-adjusted `q` (trailing 30 d mean log return) keeps the sign. Each SCREEN half by window end
  keeps the sign. Units with ≥ 1 hourly price change in `[t − 6 h, t)` keep the sign. The Gamma outcome in place of the
  Binance outcome keeps the sign. Top-5 drops by event and by week.
- **Reported (uncounted).** The cross-horizon test: the crowd-implied σ (σ solving `q_touch = p_t`) by horizon bucket
  (< 3 d, 3-10 d, > 10 d). CH118 predicts higher implied σ at short horizons. Also the slope by template, asset and
  distance band (`|ln(B/S)|/(σ√τ)` terciles); the share of units with `|q_touch − p_t| ≥ 5c`; and the Binance-Gamma
  agreement.

**Power (planning; GRP decides).** The pull alone holds 1,418 SCREEN-window markets (ends 2025-10..2026-03), and the
date walk adds 2024-11..2025-09 (rows 2-4 show ladders there), so SCREEN is about 2,500-3,500 markets in about 300-450
events over about 70 ISO weeks. With SD(`Y − p`) about 0.38 and SD(`q_touch − p_reg`) about 0.10: if reach/dip
opposition lets the event way bind (about 300-450 events), `SE(β̂) ≈ 0.12` → **MDE_R1 ≈ 0.45-0.5** against the 0.30
floor. If the week factor binds (about 70 weeks x 2 main assets), `SE ≈ 0.3` → **MDE ≈ 1.2**, and GRP stops R1
("not run (power)", counted). This is R's main risk (§7).

**Stage 2 (conditional; q0283).** On the sealed HOLDOUT (ends `[2026-04-01, 2026-10-01)`, checkpoints ≥ 2026-04-01;
2,321 markets in the pull): **R1-rep** (same rules) and **R2** (modelled-cost economic, §2.1). R2 takes one entry per
market, at the first eligible checkpoint with `q_touch − a_YES ≥ 5c` (buy YES) or `(1 − q_touch) − a_NO ≥ 5c` (buy NO),
held to resolution: `net = Y^G − a − fee`. One-sided > 0, floor +1.0c, robustness +1.0c on `a`. **Binding placebo:**
the same rule with `q_touch` replaced by `p_reg` must not pass p < 0.01. **R2 power:** SD(net) about 0.4 per market;
with about 1,000 entries and a design effect of 5, `MDE ≈ 11c` against the 1.0c floor. R2 therefore applies the GRP
rule at q0283: if `MDE_R2 > 2.0c`, R2 is "not run (power)", counted. A real R money test needs Stage P-R at recorded
asks.

### CB13-S and data jobs

- **q0270 smoke** (PASS needs):
  - the rules part hashes;
  - the refusals on fixtures: J4-R-window captures, sweeps and prints; `T13_T_hold` rows before the seal;
    `surprise_live/`, `cross_venue_live/`, `e00*/`, `trade_samples/`; the monitor's `alerts`, `scores`, `outcomes` and
    `wallets` files; every forbidden field (`side`, `wallet_*`, `ctx_chg_1h`, `uma_resolution_statuses`,
    `outcomePrices`); klines at or after `t` and R `holdout/` paths in census mode;
  - **T:** the capture-print join on two SCREEN captures reproduces probe H8's touch-age and crossing counts for the
    prints between them, and the labeller runs on fixtures and on all SCREEN titles with UNKNOWN ≤ 5% (counts only);
  - **R:** the tag-21 one-day walk on two out-of-window days (ends in `[2026-10-02, 2026-10-16]`) finds the barrier
    events that public search finds; the rule parser and flags on 3 out-of-window barrier events (window, `B`,
    direction, asset; parse success recorded); `prices-history` with explicit bounds on 2 out-of-window members; one
    Binance month HEAD + CHECKSUM.

  Any failure → the dependent family is "not testable (source)", counted. No rule is re-fitted.
- **Labeller audit** (GL, between q0270 and q0271; a `science-reviewer` pass on 200 titles, no prices). The audit file
  is `creative_batch13/labeller_audit.json`, committed with its seed and sample ids.
- Every data job writes a manifest (file sha256, request counts, failures, data-dumps size and margin, free disk) and a
  `*_complete` status.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`. `argv[0]` is under `backend/scripts/`, and `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check. Analysis
jobs also need their family's freeze. All `family` = `creative_batch_13`. Priorities: `cpu` 19 for T and 16-18 for R;
`net` 15-17 (below CB12's 20-24 and CB11's 25-29).

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0270 | cpu | 19 | ≤ 30 req at ≤ 1 rps, < 10 min, mem 400 | - | rules file + smoke code reviewed |
| q0271 | cpu | 19 | no network, ≤ 40 min, mem 800 | q0270, labeller audit | after GL PASS is committed |
| q0272 | cpu | 19 | ≤ 15 min, mem 400 | q0271 | with q0271 |
| q0273 | cpu | 19 | ≤ 30 min, mem 500 | q0272, T freeze | after the T freeze |
| q0274 | cpu | 19 | no network, ≤ 50 min, mem 800 | q0273 committed (any result) | not before 2026-10-26T08:00Z |
| q0275 | cpu | 18 | ≤ 30 min, mem 500 | q0274 seal copy | only if T1 or T2 advanced |
| q0276 | net | 17 | ≤ 600 req, ≤ 6 min, mem 500 | q0270, CB11 q0221 | with q0270's PASS |
| q0277 | net | 16 | ≤ 8,000 req, ≤ 70 min, mem 400 | q0276 | with q0276 |
| q0278 | net | 15 | ≤ 25,000 req (Σ from q0277's manifest), ≤ 3.5 h, mem 300 | q0277 | after q0277's request Σ is recorded |
| q0279 | net | 15 | ≤ 400 req at 1 rps, ≤ 10 min, mem 400 | q0277 | with q0277 |
| q0280 | cpu | 17 | light, mem 300 | q0278, q0279 | as the fetches complete |
| q0281 | cpu | 17 | ≤ 30 min, mem 600 | q0280 seal copy | after the R seal copy is committed |
| q0282 | cpu | 16 | ≤ 1 CPU-h, mem 800 | q0281, R freeze | after the R freeze |
| q0283 | cpu | 16 | ≤ 1 CPU-h, mem 800 | q0282 | only if R1 advanced |

```json
{"id": "q0270_cb13_smoke", "title": "CB13: smoke (rules part hashes; refusals: J4-R window, T HOLDOUT before seal, surprise_live, cross_venue_live, e00*, trade_samples, monitor alerts/scores/outcomes/wallets, forbidden fields side/wallet_*/ctx_chg_1h/uma/outcomePrices, klines >= t and R holdout in census mode; T capture-print join reproduces probe H8 on 2 SCREEN captures; labeller UNKNOWN <= 5% on SCREEN titles; R tag-21 one-day walk on 2 out-of-window days, rule parser on 3 out-of-window barrier events, prices-history bounds on 2, one Binance HEAD+CHECKSUM); counts only", "family": "creative_batch_13", "priority": 19, "expected_value": "go/no-go for every CB13 source", "data": ["live_trades/trades-202610{12..15}.jsonl (whitelisted fields)", "snapshots/ (2 SCREEN captures, whitelisted columns)", "public Gamma, CLOB prices-history", "data.binance.vision"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, data.binance.vision"}, "depends_on": [], "argv": ["scripts/run_cb13.py", "smoke", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch13/smoke.json", "trials.jsonl (cb13_descriptive)"], "next_action": "PASS: labeller audit (GL), q0276; FAIL: dependent family not testable (source), counted", "notes": "CREATIVE_BATCH_13.md CB13-S. DRAFT. <= 30 requests. No side, wallet or hash stored. Starts outside :31-:55 of even hours."}
{"id": "q0271_cb13_t_frame", "title": "CB13-T: exclusion keys (ids + timestamps of sealed historical sets with rows in T windows, field-restricted) and SCREEN fill table: transactions in [2026-10-12, 2026-10-16), touch from the latest complete capture row (age <= 60 min, two-sided, mid in [0.03,0.97], spread <= 10c, end >= tau+3h), side-free paper fill, first crossing per (market, capture, side), frozen labeller; features only, no mark", "family": "creative_batch_13", "priority": 19, "expected_value": "T SCREEN population", "data": ["live_trades/trades-202610{12..15}.jsonl (whitelist)", "snapshots/<captures starting 2026-10-11T20Z..2026-10-16T00Z>/rows.csv.gz, rows_ext.csv.gz (whitelist)", "history/{h5_cb1,h5_cb1_ladders,h7_cb4_era,h7_cb4_series,h8_tail,h8_tail_b,h8_text,h8_geo} (id + timestamp columns only)", "creative_batch13/labeller_audit.json"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0270_cb13_smoke"], "argv": ["scripts/run_cb13.py", "t-frame", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--split", "screen", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch13/t_screen/{fills.csv.gz,labels.csv.gz,t_exclusion_keys.csv.gz,manifest.json}"], "next_action": "q0272", "notes": "DRAFT. Refuses any capture/print in the J4-R window or T HOLDOUT window, and any mark capture (no forward row is read). Restores archived captures byte-for-byte if deleted from the host. mem 800 justified (section 2.8)."}
{"id": "q0272_cb13_census_T", "title": "CB13-T census, counts only: prints/transactions by day, label, fee category; key drops by source; fills by touch-age band, crossing vs inside, first-crossing collapse; by class, event, 6h block, day; spread/mid/time-to-end bands; exclusion labels; sweep depth (reported); gates GT and GL; GTP clustered SEs on the pre-fill proxy (no point estimate written); MDEs", "family": "creative_batch_13", "priority": 19, "expected_value": "T gates and MDEs before the freeze", "data": ["creative_batch13/t_screen/", "snapshots/ (touch and pre-touch captures only, whitelist)", "book_sweeps/ (depth columns, reported)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0271_cb13_t_frame"], "argv": ["scripts/run_cb13.py", "census", "--family", "T"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch13/census_T.json", "trials.jsonl (cb13_descriptive)"], "next_action": "science-reviewer freeze check (T part)", "notes": "DRAFT. No mark capture opened; no M, D or net computed."}
{"id": "q0273_cb13_screen_T", "title": "CB13-T: gate GTI, then T1 (LOW - NEWS 2h mark-out; pre-fill and composition placebos; age<=20m, 6h, adverse-touch mark, >=$10k, side, event-weighted, top-5, leave-one-day-out robustness; attribution) and T2 (LOW mid-marked maker net; sign-flip and pre-fill placebos; age, 6h, components, worst-case robustness) on SCREEN", "family": "creative_batch_13", "priority": 19, "expected_value": "T verdicts and the class map", "data": ["creative_batch13/t_screen/", "snapshots/ (mark captures starting before 2026-10-16T00:00Z only)", "live_trades/trades-202610{12..15}.jsonl (GTI print-based moves)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0272_cb13_census_T"], "argv": ["scripts/run_cb13.py", "screen", "--family", "T"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_T.json", "trials.jsonl (cb13_test + creative_batch_13:T n_tests=2)"], "next_action": "commit results; advanced: q0275 after the q0274 seal", "notes": "DRAFT. Refuses before the T freeze hash; refuses unless GT, GL, GTP passed (else counted lines). Every line labelled 'L1, worn captures, new statistic'; T2 also 'upper bound (free exit)'."}
{"id": "q0274_cb13_t_holdout", "title": "CB13-T HOLDOUT seal: sha256 of trades-2026102{1..6}.jsonl and rows/rows_ext of captures starting [2026-10-20T22Z, 2026-10-26T00Z); HOLDOUT fill table (features, frozen labeller, SCREEN events dropped, counted) and raw mark-quote table (bid/ask at mark captures, no mark-out computed) to t_holdout/; re-read exclusion sets; counts only; seal copy", "family": "creative_batch_13", "priority": 19, "expected_value": "sealed T HOLDOUT", "data": ["live_trades/trades-2026102{1..6}.jsonl (whitelist)", "snapshots/ (HOLDOUT captures, whitelist)", "creative_batch13/t_screen/fills.csv.gz (event ids only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0273_cb13_screen_T"], "argv": ["scripts/run_cb13.py", "t-holdout", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--not-before", "2026-10-26T08:00:00Z", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch13/t_holdout/{fills.csv.gz,mark_quotes.csv.gz,manifest.json}", "research_lab/creative_batch13/t_holdout_SEAL.json"], "next_action": "commit seals/cb13_t_holdout_SEAL.json; q0275 if triggered", "notes": "DRAFT. Exits 75 (pending) before 2026-10-26T08:00Z. Writes no M. If J4-R's end has moved, the window starts at the new end (recorded)."}
{"id": "q0275_cb13_rep_T", "title": "CB13-T Stage 2 on the sealed HOLDOUT: T1-rep (if T1 advanced), T2-rep and T3 recorded-touch round trip (passive entry, taker exit at the 2h adverse touch, sidecar fee, +0.5c robustness) (if T2 advanced); >= 500 fills per class used in >= 60 events else not run (power)", "family": "creative_batch_13", "priority": 18, "expected_value": "L2 verdicts", "data": ["creative_batch13/t_holdout/ (seal hash verified first; sources restored from archive if needed)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0274_cb13_t_holdout"], "argv": ["scripts/run_cb13.py", "rep", "--family", "T"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_T_rep.json", "trials.jsonl (cb13_replication + creative_batch_13:T:rep)"], "next_action": "pass: Stage P-T registration draft", "notes": "DRAFT. Only for triggered tests; alpha/5 if early, full Stage-2 Holm once."}
{"id": "q0276_cb13_exclusion_keys", "title": "CB13-R: exclusion keys = CB11 q0221 key file + id columns of h9_flow, h10_*, h11_*, every CB12 frame (h12_say, h12_quake, h12_prints, live frames), CB8/CB9 frames + seal copies; Gamma lookups for missing event/negRisk/series keys; barrier-overlap list by asset and window", "family": "creative_batch_13", "priority": 17, "expected_value": "disjointness of R", "data": ["creative_batch11/exclusion_keys.csv.gz", "history/*/ (id columns only)", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0270_cb13_smoke", "q0221_cb11_exclusion_keys"], "argv": ["scripts/run_cb13.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch13/exclusion_keys.csv.gz", "manifest.json (absent_at_q0276 list)"], "next_action": "q0277", "notes": "DRAFT. >2% missing metadata -> disjointness unverified (R1 not testable, counted). Exit 75 on headroom = pending."}
{"id": "q0277_cb13_touch_frame", "title": "CB13-R: Gamma closed events tag_id=21, one-day end_date windows over [2024-11-01, 2026-10-01); frozen barrier templates (terminal and Up/Down templates excluded, counted); members, strike, direction, asset; rule-window parser and flags; key + same-asset overlap drops; out-of-time split at 2026-04-01; Gamma outcomes to SCREEN and HOLDOUT guarded files; completeness cross-check vs poly_markets.json barrier ids (ids/questions only); q0278 request sum", "family": "creative_batch_13", "priority": 16, "expected_value": "R population and split", "data": ["public Gamma", "creative_batch13/exclusion_keys.csv.gz", "cross_venue/poly_markets.json (ids and questions only, streaming)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0276_cb13_exclusion_keys"], "argv": ["scripts/run_cb13.py", "touch-frame", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h13_touch/{events.csv.gz,members.csv.gz,rules_parsed.csv.gz,split.json,outcomes_guarded_screen.csv.gz,manifest.json}", "history/h13_touch/holdout/outcomes_guarded_holdout.csv.gz"], "next_action": "q0278, q0279", "notes": "DRAFT. No price read. Capped day windows split until uncapped (counted). outcome_prices/volume of poly_markets.json never parsed."}
{"id": "q0278_cb13_touch_prices", "title": "CB13-R: CLOB prices-history per barrier member, fidelity 60 in <= 14-day bounded chunks over [max(createdAt, window start - 1 d), window end]; a point is usable from stamp + 3600 s; HOLDOUT rows to holdout/", "family": "creative_batch_13", "priority": 15, "expected_value": "R prices", "data": ["public CLOB prices-history", "history/h13_touch/members.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "clob"}, "depends_on": ["q0277_cb13_touch_frame"], "argv": ["scripts/run_cb13.py", "touch-prices", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "2", "--disk-cap-gb", "0.05", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h13_touch/{screen,holdout}/prices.csv.gz", "manifest.json"], "next_action": "q0280", "notes": "DRAFT. <= 25,000 requests = sum of ceil(span/14 d) from q0277's manifest (planning 12,000-16,000). Resumable; incomplete = pending.", "repeat": {"max_runs": 4, "until_log_regex": "\"status\": \"touch_prices_complete\""}}
{"id": "q0279_cb13_binance", "title": "CB13-R: data.binance.vision monthly spot 1m klines + .CHECKSUM for the parsed assets (BTC, ETH, SOL, XRP and any other parsed USDT pair), 2024-09..2026-09; verified, parsed in memory to float32 (open time, high, low, close) npz per asset-month; months >= 2026-04 to holdout/", "family": "creative_batch_13", "priority": 15, "expected_value": "R spot, sigma and touch outcomes", "data": ["data.binance.vision (public archive)", "history/h13_touch/members.csv.gz (asset list)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "data.binance.vision"}, "depends_on": ["q0277_cb13_touch_frame"], "argv": ["scripts/run_cb13.py", "binance", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "1", "--disk-cap-gb", "0.2", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["history/h13_binance/{screen,holdout}/<SYM>-<YYYY-MM>.npz", "manifest.json"], "next_action": "q0280", "notes": "DRAFT. <= 400 requests. A CHECKSUM mismatch is retried once, then the month is 'unavailable (source)'; units needing it are counted unavailable."}
{"id": "q0280_cb13_seal_R", "title": "CB13-R: HOLDOUT listings sha256 (h13_touch/holdout incl. outcomes_guarded_holdout, h13_binance/holdout); seal-time drops vs every seal copy and frame committed by now (incl. CB12 frames absent at q0276); seal copy seals/cb13_touch_holdout_SEAL.json", "family": "creative_batch_13", "priority": 17, "expected_value": "sealed R HOLDOUT", "data": ["history/h13_touch/holdout/", "history/h13_binance/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0278_cb13_touch_prices", "q0279_cb13_binance"], "argv": ["scripts/run_cb13.py", "seal", "--family", "R"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch13/holdout_SEAL_R.json"], "next_action": "commit the seal copy; q0281", "notes": "DRAFT. Sealed files never edited; drops recorded as DROPPED_* blocks."}
{"id": "q0281_cb13_census_R", "title": "CB13-R census, counts only: events/markets by template, asset, direction, end month; parser and flag failures; key, overlap and full-series counterfactual drops; poly_markets completeness; units by label; q_touch - p_reg distribution (klines before t only); HOLDOUT counts only; gates GR, GRP (simulated price-calibrated outcomes with asset-week and week factors, reach/dip opposite loadings); MDEs", "family": "creative_batch_13", "priority": 17, "expected_value": "R gates and MDEs before the freeze", "data": ["history/h13_touch/screen (no guarded file; HOLDOUT counts only)", "history/h13_binance/screen (guarded accessor: klines < t)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0280_cb13_seal_R"], "argv": ["scripts/run_cb13.py", "census", "--family", "R"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch13/census_R.json", "trials.jsonl (cb13_descriptive)"], "next_action": "science-reviewer freeze check (R part)", "notes": "DRAFT. No Y, slope or net computed. Refuses on an incomplete manifest."}
{"id": "q0282_cb13_screen_R", "title": "CB13-R: R1 (market-weighted slope of Y - p_t on q_touch - p_reg, Binance outcome; event/week/asset-week ways; week sign-flip and stale-price placebos; reflection-gap attribution; reach/dip, BTC, sigma x0.8/x1.2, drift, halves, active, Gamma-outcome, top-5 robustness; Binance-Gamma agreement audit; cross-horizon implied sigma reported)", "family": "creative_batch_13", "priority": 16, "expected_value": "R1 verdict", "data": ["history/h13_touch/screen + outcomes_guarded_screen.csv.gz (opened here)", "history/h13_binance/screen"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0281_cb13_census_R"], "argv": ["scripts/run_cb13.py", "screen", "--family", "R"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_R.json", "trials.jsonl (cb13_test + creative_batch_13:R n_tests=1)"], "next_action": "advanced: q0283", "notes": "DRAFT. Refuses before the R freeze hash, on any holdout/ path, and unless GR and GRP passed (else counted lines)."}
{"id": "q0283_cb13_rep_R", "title": "CB13-R Stage 2 on the sealed HOLDOUT: R1-rep and R2 (modelled-cost hold-to-resolution, 5c filter, band half-spread + 0.07 fee, Gamma payoff; p_reg placebo; +1c robustness; MDE_R2 > 2c -> not run (power))", "family": "creative_batch_13", "priority": 16, "expected_value": "L2 verdicts", "data": ["history/h13_touch/holdout + holdout/outcomes_guarded_holdout.csv.gz", "history/h13_binance/{screen,holdout} (seal hash verified first)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0282_cb13_screen_R"], "argv": ["scripts/run_cb13.py", "rep", "--family", "R"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_R_rep.json", "trials.jsonl (cb13_replication + creative_batch_13:R:rep)"], "next_action": "pass: Stage P-R registration draft (recorded asks)", "notes": "DRAFT. Only if R1 advanced."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb13_common.py`: reuse `cb12_common`/`cb11_common` (refused roots, the J4-R pin,
  disk and free-disk guards with cap 40, exit 75, manifests, `*_complete` status, cluster bootstrap with the small-G
  rule and the leave-one-cluster-out sign rule, Holm/BY helpers, per-part rules hashing); the field-whitelist readers
  for monitor prints, capture rows and sidecar; the archive-restore hook with hash verification.
- `cb13_tox.py`: transaction aggregation (`tx16` in memory), YES-terms conversion, the capture touch index (latest row
  per market before `τ`, streamed one capture at a time), touch eligibility, the side-free fill and first-crossing rule,
  the frozen labeller and its audit sampler, T exclusion keys (id and timestamp accessor), mark lookup (refusing
  captures in the J4-R window and before the seal), `M_h`, T1/T2 with placebos (pre-fill, composition permutation,
  sign-flip), robustness, attribution, GTI, GTP, the HOLDOUT extractor and seal, T1-rep/T2-rep/T3.
- `cb13_touch.py`: tag-21 one-day walker (split until uncapped), barrier and terminal templates, rule-window parser (ET
  → UTC, DST), flags, asset map, overlap exclusion, the poly_markets streaming id reader, `prices-history` client
  (14-day chunks), the Binance archive client (CHECKSUM, in-memory parse, float32 npz), the guarded kline accessor, σ,
  `q_touch`/`q_term`, decided-rung detection, the outcome evaluator, R1 with placebos and attribution, GRP, R2.
- `backend/scripts/run_cb13.py` with the §4 subcommands; refuses analysis before the family's freeze hash.
- Tests (`test_cb13_tox.py`, `test_cb13_touch.py`, `test_run_cb13.py`). They cover:
  - whitelist fixtures with every forbidden field, and the refused roots and files;
  - J4-R refusals at both edges, and the moving-end rule;
  - T: the HOLDOUT refusal before the seal; touch selection by `received_utc < τ` (equality excluded); the age
    boundary at 60 and 20 min; YES conversion for outcome index 1; crossing at equality (`P = a0` fills, `a0 − tick`
    does not); first-crossing per side; the mark-capture rule and the 2 h usability cap; the scheduled-end ≥ `τ + 3 h`
    rule; the labeller precedence on fixtures (sports before path, path before public-statistic, the fallback to NEWS);
    GTP writing no point estimate;
  - R: a census path refusing klines ≥ `t`; kline usability at `o + 65 s`; decided-rung detection; the touch formula at
    known values (`q_touch = 2·q_term` in the limit, cap at 1); ET window parsing across 2025-11-02 and 2026-03-08 DST;
    terminal and Up/Down templates rejected; the overlap rule on weekly-inside-monthly fixtures; HOLDOUT checkpoints
    before 2026-04-01 dropped;
  - `battery2` kinds and k1 = 3 fixed; the α/5 early rule in Stage 2.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: T1, T2, R1 | **3** | `cb13_test` + count lines `:T` (2), `:R` (1) | p < 0.01, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 3 fixed); counted with p = 1 if a gate, audit or smoke check fails |
| Stage 2: T1-rep, T2-rep, T3, R1-rep, R2 (each only if triggered) | ≤ 5 | `cb13_replication` + `:<family>:rep` | one Holm over CB13 Stage 2, one-sided α 0.05 (early finishers at α/5) |
| Smoke, labeller audit, census, gates, strata, variants, descriptives | 0 | `cb13_descriptive` | - |
| **Total** | **3 fixed + ≤ 5 conditional = 3-8** | | cumulative 1,181 → 1,184-1,189, plus whatever CB6-CB12 add first |

**Host compute.** Under 4 CPU-hours at nice 19 in total. T is under about 1.5 h: the frame streams about 50 captures
(probe H8's join over 44 captures took about 1 min wall), and the screen bootstraps on about 3,000-20,000 fills. R is
under about 2 h, with 2,000 bootstrap draws and 200 placebo draws on market-level sufficient statistics, and GRP's 500
draws. Peak RAM 0.8 GB. **Network.** T none; R ≤ about 34,000 requests (planning about 22,000; about 3-5 h of `net`
lane at 2 rps). **Disk.** ≤ 0.35 GB.

**Dates (estimates).** Code, the labeller audit and the T freeze check about 2026-10-19/20. **T runs before `T_seal`
on the `cpu` lane** while CB11 holds the `net` lane: q0270 → GL → q0271/q0272 → T freeze → q0273 about 10-20/21. The T
HOLDOUT seal is on or after 10-26T08:00Z, and q0275 follows within a day if triggered. R's `net` jobs (about 3-5 h)
follow CB11's (about 10-11 h) and CB12's (about 6-10 h), so about 10-21..23. The R census, freeze and screen follow
with no rule change if the lane slips.

## 7. Main scientific risks (for the challenger)

1. **T's SCREEN is four days.** The 6 h block way has at most 16 clusters (CR2 or leave-one-block-out) and the day way
   only 4 (leave-one-day-out binding). One news-heavy or crypto-trend day can carry a class contrast. The pre-fill
   placebo and the day rule are the guards. GT (500 fills per class) may fail on NEWS, in which case T1 is counted
   as not testable. The HOLDOUT adds five days.
2. **The 2 h capture cadence.** The paper touch is up to 60 min old, so some "fills" are stale-quote fills, which
   biases maker results downward (conservative for T2, ambiguous for T1 if staleness differs by class). The 20-minute
   robustness and GTI are the guards. The GTI "not evaluable" deviation (n < 200) should be ruled on.
3. **The labeller is text-based.** It has no `resolutionSource` or `gameStartTime` (premise 2), and class boundaries
   (Fed decisions, election results, temperature) are judgement calls frozen in regexes. The blind 200-title audit with
   one allowed revision is the guard. LOW is a declared union, chosen from CH128's prediction before any mark.
4. **Composition.** LOW markets are tighter, shorter-dated and more often path-settled dailies. The composition placebo
   and the binding attribution decide the label "class effect" vs "composition". A T1 advance with "composition" is
   still informative for maker design but is not CH128's mechanism.
5. **T2 is an upper bound.** It marks at a free mid exit. T3 (recorded-touch round trip) is the economic check, and it
   is expected to fail, since a taker exit costs a half-spread plus a fee. A T2 pass alone is never an economic result.
6. **Shared windows.** T overlaps E011, E004-E006, CB1-D SEALED-P, CB3's counts-only dev window, CB6's dev block, and
   SEALED-H4's calendar (§1.3). The argument is a different hypothesis, never opening their stores, no subgroup
   definitions, and their frozen state. The open choice is whether q0275 must also wait for CB3's freeze. Sealed
   historical sets with rows in T windows are excluded by key.
7. **R's power rests on reach/dip opposition.** One Binance path resolves every overlapping rung. If the week factor
   binds, GRP stops R1 (MDE about 1.2 vs the 0.60 cut). The stale-price placebo and the reflection-gap attribution
   separate "barrier confusion" from "price lags spot". R2's historical MDE (about 11c) means R's money question needs
   Stage P-R at recorded asks.
8. **R's model is approximate.** It is driftless, has no jumps, and uses one 30-day σ. The rules use 1-minute candle
   highs and lows, which is close to continuous monitoring. Drift and σ sensitivities are binding robustness checks.
   The klines also determine CB8-B's and CB10-D's outcomes on the same days; no R path computes those quantities
   (§1.3).
9. **CH119 is not tested,** by its own census. The decision and the re-entry routes are in §0.4.

## 8. Next actions

1. `science-reviewer` challenger round 1 on this draft. Points left open for it: the GTI deviation; the CB3-freeze hold
   for q0275; the R overlap-rule deviation for terminal and Up/Down events; GT's 500-fill floor; the 6 h block way;
   T2's +0.25c floor.
2. Write `seals/cb13_rules.json` (parts `common`, `T`, `R`), the modules and tests of §5 and `run_cb13.py`
   (implementer); then the code-against-design freeze check (`science-reviewer`).
3. Order: q0270 (cpu) → labeller audit GL → q0271 → q0272 → T freeze → q0273, all on the `cpu` lane before
   `T_seal` if possible; q0274 on or after 2026-10-26T08:00Z; q0275 if triggered. R: q0276 behind CB11 q0221, then
   q0277-q0279 behind CB11/CB12 on the `net` lane, q0280 seal, q0281 census, R freeze, q0282, q0283 if triggered.
4. CB14 adds CB13's frame ids (T fill markets and events; R barrier events) to its exclusion keys. CH119 and ranks 3
   and 5-8 are candidates for CB14 (§0.4).
5. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.
