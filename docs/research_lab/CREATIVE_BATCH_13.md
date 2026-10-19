# Creative batch 13 (CB13): maker toxicity by resolution class, barrier-versus-terminal confusion

`evidence_role: exploratory_dev` (CB13-T Stage 1, on worn live captures and monitor prints) / `prospective`
(CB13-T Stage 2, on a later live window that does not exist yet at drafting) / `exploratory_historical` (CB13-R Stage
1; Stage 2 on a sealed later historical holdout) | status: **DRAFT-REVISED after challenger round 1 (CB13-T REVISE,
CB13-R REVISE; all 14 items adopted, 3 with a stated modification, none rejected; §9-§10). Nothing frozen, nothing
queued, no code.** Drafted 2026-10-18 21:15 UTC+1 (2026-10-18T20:15Z) on parent `ee0bc96` and committed as `98a00e6`;
round-1 response 2026-10-18 21:33 UTC+1 (2026-10-18T20:33Z). Every round-1 change tightens or clarifies; no floor,
threshold, gate, alpha or cap was relaxed. Nothing was fetched or written for CB13 beyond the read-only host probes and
the 19 counts-only keyless GETs of §0.3. **No CB13 quantity was computed:** no mark-out, forward price, mid change,
slope, net, touch outcome or resolution.

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
| 1 | **CB13-T** maker toxicity by resolution class (CH128) | the maker filled by a ≥ $1k taker print (fill at the print's own maker-adverse price, side read from a touch-consistent price) loses less to adverse selection in markets settled by a public statistic or an asset path (LOW) than in unscheduled-news markets (NEWS), by ≥ 0.5c per filled share at the 2-4 h mark (T1). In LOW, the 2-4 h mid-marked maker net stays positive (T2, ≥ +0.25c) | T1 (class contrast), T2 (LOW sign) | **host files only**: live large-trade monitor prints and complete-universe captures, SCREEN window `[2026-10-12, 2026-10-16)` | the same stores, HOLDOUT window `[2026-10-21, 2026-10-26)` (adjacent window, same regime), sealed, event-disjoint from SCREEN, analysed only after CB3's freeze; the T3 economic check at recorded prices | q0270-q0275 |
| 2 | **CB13-R** barrier-versus-terminal confusion (CH118) | in closed **weekly** crypto "reach / dip to $B" ladders settled on Binance 1-minute highs and lows, the driftless reflection-principle touch probability predicts resolution beyond the price (R1, slope ≥ 0.30); monthly, yearly and "by" templates counted in the census only (round 1 item 5) | R1 (slope) | fresh `h13_touch` (Gamma frame, CLOB `prices-history`) and fresh `h13_binance` (public 1-minute archive); window ends `[2024-11-01, 2026-04-01)`; a pre-fetch component gate before the prices fetch | the same fetch, sealed HOLDOUT window ends `[2026-04-01, 2026-10-01)`; R2 (modelled-cost economic) only there | q0276-q0285 |
| - | CH119 inclusive-threshold atom | not a test: the census fails (§0.4) | none | | | next batch |

**Counted: 3 fixed (T1, T2, R1) + up to 5 conditional (T1-rep, T2-rep, T3, R1-rep, R2) = 3-8** (§2.5). The budget is
fixed now. No CB13 test is added after any CB13 read.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0270 | `cb13_smoke_T` (counts only, no network; §CB13-S) | T | after `seals/cb13_rules.json` and smoke code exist (`cpu` lane) |
| q0271 | `cb13_t_frame` (T exclusion keys; SCREEN fill table, features only, labels applied; no mark) | T | after q0270 PASS and the labeller audit (§CB13-T) is committed |
| q0272 | `cb13_census_T` (counts only; gates GT, GL, GTP; MDEs) | T | after q0271 |
| q0273 | `cb13_screen_T` (T1, T2 Stage 1; gate GTI) | T | after the T freeze |
| q0274 | `cb13_t_holdout` (HOLDOUT seal: source-file sha256; HOLDOUT fill table and raw mark-quote table to `holdout/`; counts only) | T | not before 2026-10-26T08:00Z |
| q0275 | `cb13_rep_T` (T1-rep, T2-rep, T3 on the sealed HOLDOUT; GTI on SCREEN + HOLDOUT pairs) | T | only if T1 or T2 advanced; after the seal copy **and CB3's freeze commit** (round 1 item 3) |
| q0276 | `cb13_exclusion_keys` (CB11 q0221 key file + every set since, including CB12 frames + seal copies; barrier-overlap list) | R | after q0285 PASS and CB11 q0221 complete |
| q0277 | `cb13_touch_frame` (Gamma tag-21 date walk, barrier templates, rule parser, split, outcomes to guarded files, cross-check against the 2026-10-12 pull) | R | after q0276 |
| q0278 | `cb13_touch_prices` (`prices-history` fidelity 60, 14-day chunks; HOLDOUT to `holdout/`) | R | only after q0284 PASS |
| q0279 | `cb13_binance` (data.binance.vision monthly 1m spot zips, CHECKSUM-verified, kept as verified bytes; from the frame's earliest window start − 30 d; HOLDOUT months to `holdout/`) | R | after q0277 (needs the parsed asset list and earliest `T0`) |
| q0280 | `cb13_seal_R` (HOLDOUT listings sha256; seal copy; seal-time drops) | R | after q0278 and q0279 |
| q0281 | `cb13_census_R` (counts only; gates GR, GRP; MDEs) | R | after q0280 and the seal copy |
| q0282 | `cb13_screen_R` (R1 Stage 1) | R | after the R freeze |
| q0283 | `cb13_rep_R` (R1-rep and R2 on the sealed HOLDOUT) | R | only if R1 advanced |
| q0284 | `cb13_r_pregate` (counts only: SCREEN window components of the primary weekly template with ≥ 1 undecided unit and kline coverage; gate GRC) | R | after q0277 and q0279; q0278 is committed only on PASS (round 1 item 7) |
| q0285 | `cb13_smoke_R` (≤ 30 requests; §CB13-S) | R | after the R rules part and smoke code exist (`net` lane; round 1 item 11) |
| q0286-q0299 | reserved | - | - |

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
- **Count note (2026-10-18 21:36Z, coordinator; CB14 challenger finding):** the 1,181 below was correct at `ee0bc96`
  but is stale: the host union at `647549c` added 40 counted `flow_screen` lines (1,221 at HEAD then), and the host
  keeps adding about 55-60 such lines a day. Every CB13 counting job therefore records the value at its run, after
  the union; the projections below are historical and are not used.
- `battery2.cumulative_count()` (`battery2-count-v1`) = **1,181** on the committed `trials.jsonl` at `ee0bc96` (the draft's
  parent; re-verified 1,181 at the round-1 response).
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
| H10 | streaming census of `cross_venue/poly_markets.json` (the 2026-10-12 Gamma pull, a filtered set of closed markets; CB12-X pins it for `endDate`) | 148,384 markets (148,370 closed), ends 2025-10..2026-10. **Crypto barrier ("reach / hit / dip to", not "above ... on"): 3,948 markets in 501 events**, 3,946 with "Binance" and all with high/low wording in the description. By end month: 2025-10 119, 11 243, 12 301, 2026-01 227, 02 275, 03 253, 04 478, 05 434, 06 460, 07 301, 08 300, 09 348, 10 203 (these sum to 3,942; the other 6 markets have no `end` value in the pull, round 1 item 12). **Race form ("before"): 23 markets in 5 events.** Non-crypto barrier 778 / 87 events. Terminal crypto ("above / below ... on") 8,556 / 1,496. Inclusive wording ("or higher / or more / at least"): temperature 648 markets (648 events), earthquake 74 (20), votes 34 (23), Rotten Tomatoes 16 (7), macro 13 (13), box office 9, approval 1, chart 1 |
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
| **CH118** barrier confusion | **include (R), historical, `net` lane behind CB11/CB12** | 3,948 closed crypto barrier markets in 501 events in the 2026-10-12 pull alone (H10), more before 2025-10 (rows 2-4). The outcome is a public function of Binance 1-minute highs and lows, the source the rules name (H10, row 11). Needs a Binance fetch (premise 1) and CLOB history. **The race arm is dropped**: 23 markets in 5 events, below CH118's own 30-market threshold. **The cross-horizon implied-σ test is reported, uncounted** (k stays small; it reads the same units). **Round 1 item 5: the primary is the weekly template only** (non-overlapping same-asset windows, so window components are about asset × week); monthly, yearly and "by" templates are counted in the census only (no prices fetched), because weeks that straddle a month end chain every monthly window of an asset into one component, which would leave about one cluster per asset |
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
| `T13_T_screen` | fills with venue time `τ ∈ [2026-10-12T00:00Z, 2026-10-16T00:00Z)` | T Stage 1. **Every touch and mark capture must start before `t_j4r_start` = 2026-10-16T00:00Z** (a fill whose mark capture starts later is "excluded (J4-R boundary)", counted) |
| J4-R window | `[2026-10-16T00:00Z, 2026-10-21T00:00Z)` (`seals/j4r_window.json`; the end can only move forward, and T follows it) | **No CB13 path reads any capture, sweep or print timed inside it** (as CB3 §1.2 and CB6 §1.2) |
| `T13_T_hold` | fills with `τ ∈ [t_j4r_end, 2026-10-26T00:00Z)` (`t_j4r_end` = 2026-10-21T00:00Z while `final` is false); **touch and mark captures must start in `[t_j4r_end, 2026-10-26T00:00Z)`** (round 1 item 2: the draft's 10-20T22:00Z start lay inside J4-R). Fills before the first capture at or after `t_j4r_end` (about 00:31Z) have no eligible touch and are counted, never back-filled | T Stage 2, label **"adjacent window, same regime"** (round 1 item 14). It ends before CB2's earliest Stage-2 capture start (`max(10-26, freeze + 2 h)`), CB3/CB4 (≥ 10-27), CB5 (≥ 10-29), CB6/CB7 (≥ 10-30). If J4-R's end moves later, `T13_T_hold` starts at the new end with the same end date, and the census records the shortening |
| `T13_T_seal` | 2026-10-26T08:00Z (earliest q0274 start) | every HOLDOUT trades file is complete (daily by receipt; prints arrive about 8 min late) and every mark capture before 2026-10-26T00:00Z exists |
| `T13_T_rep` | the later of the q0274 seal-copy commit and **CB3's freeze commit** (`model_specs/cb3_v1.json`) | earliest q0275 start (round 1 item 3). If CB3 is recorded in the ledger as stopped or withdrawn without a freeze, that ledger record replaces the freeze commit |
| `T13_hist_end` | 2026-10-01T00:00Z | no R row (rule-window end, price point, kline used in a feature or outcome, resolution) at or after it |
| R SCREEN / HOLDOUT | event `endDate` in `[2024-11-01, 2026-04-01)` / `[2026-04-01, 2026-10-01)`, sealed | out-of-time split. **R HOLDOUT units also need checkpoint `t ≥ 2026-04-01T00:00Z`**: earlier checkpoints of HOLDOUT events are dropped and counted, so the two splits share no calendar |
| R checkpoints | daily 00:00Z from `max(window start, listing + 1 h)` to `window end − 1 h` | §CB13-R |
| R kline range | from the first month containing `min(T0) − 30 d` over **every primary frame event** (round 1 item 6; the census-only templates have no units) to 2026-09 | σ needs `[t − 30 d, t)`; the decided-rung rule needs klines from each window start `T0`. A unit without full coverage of `[min(T0, t − 30 d), t)` is "unavailable (no klines)", counted, never assumed undecided |
| R σ window | Binance 5-minute log returns in `[t − 30 d, t)` | §CB13-R |
| `T_seal` | 2026-10-22T00:00Z | not binding for CB13 (no CB13 historical row reaches it; R's rows end before 2026-10-01). See §1.3 for SEALED-H4 |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb13.py` refuses every root in the last two rows of §1.1 (field-restricted id/timestamp
  readers excepted). It writes only under `research_lab/creative_batch13/`, `history/h13_touch/` and
  `history/h13_binance/`. The T reader refuses any capture, sweep or print timed in the J4-R window, and any
  `T13_T_hold` row unless the T Stage-1 result file and `seals/cb13_t_holdout_SEAL.json` are committed and their
  hashes verify **and CB3's freeze commit (or its ledger stop record) exists** (`T13_T_rep`). The R reader refuses `holdout/` paths in every census and screen.
- **E011 (registered window `[2026-10-13T14:00Z, 2026-11-10)`, analysed once after 2026-11-11T13:00Z).** Both T
  windows lie inside it, and T reads the same complete-universe captures E011 scores. **Why T does not contaminate
  E011.** (1) The hypothesis is different. E011 asks whether the frozen `sm_learned_v2` score selects markets followed
  by surprise moves more often than matched controls; T asks whether maker mark-outs differ by resolution class.
  (2) T never opens `surprise_live/` (alerts, passes, outcomes). It never computes the detector score, the stage-1
  pre-score, the surprise labels (`hit_6h`, `sharp_any_6h`) or `fwd_move_*` for any E011 line, and never conditions
  on or joins to alert, candidate or control status. (3) E011's analysis is frozen code run once, so no E011 choice is
  left that a T result could inform. (4) No T output defines an E011 subgroup, stratum or reading, and the E011 report
  may not cite T. (5) T reads captures read-only, so E011's inputs stay bit-identical. Residual overlap, disclosed:
  T computes 2-4 h and 6-8 h forward capture-mid changes after fills, and some fill markets are E011 alerts or
  controls. **No T output is stratified by E011 alert, candidate or control status** (round 1 ruling on §7 risk 6).
- **E004, E005, E006 (registered, pre-outcome) and E007 (scored 2026-10-12).** T never opens `e00*/` and never parses
  `chg_1h` (from captures or from `ctx_chg_1h`). It never computes a `chg_1h`-conditioned move, an arbitrage-band deviation or a signed-share continuation, and no T output defines
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
  freeze blind, and T's HOLDOUT maker mark-outs on those days are the quantity closest to CB3-B's. **Round 1 item 3
  (ruling, adopted): q0275, the only job that computes a HOLDOUT mark-out, waits for CB3's freeze commit**
  (`T13_T_rep`). q0274 (seal and features, no mark-out) may run earlier. CB3's freeze-check record also states whether
  T's Stage-1 SCREEN result existed at its freeze (SCREEN lies outside CB3's dev window).
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
  capture's `rows.csv.gz` and `rows_ext.csv.gz` for captures starting in `[t_j4r_end, 10-26T00:00Z)` (round 1 item 2). It writes the
  HOLDOUT fill table (features only) and the raw mark-quote table (bid and ask at each mark capture; no mark-out
  computed) to `creative_batch13/t_holdout/`, with listing sha256. The seal copy `seals/cb13_t_holdout_SEAL.json` is
  committed before q0275. **Source files may later be archived and deleted from the host under the capsule-first
  policy.** If so, q0275 restores them byte for byte with `restore_from_archive.py` and verifies the sealed hashes, and
  never re-derives a missing file.
- **Outcome guards.** T has no resolution outcome (mark-outs are price-based; T3 exits at a recorded touch). The
  HOLDOUT mark-quote table is read only by q0275. R: Gamma
  `outcomePrices` and `umaResolutionStatus(es)` go only to the guarded files. **R's primary outcome is computed from the
  Binance klines by the frozen rule parser, never read from Gamma** (CB9-P's guard). Gamma outcomes are opened only by
  q0282 (the agreement audit) and q0283 (R2 pays what the venue paid). Census paths read klines only before each
  unit's checkpoint `t` (a guarded kline accessor; unit-tested).

### 1.4 Rules files

- `seals/cb13_rules.json` (before q0270), hashed per part:
  - **`common`**: refused roots, the J4-R pin, seeds, bootstrap, the small-G rule, Holm/BY settings, disk guards and
    smoke criteria.
  - **`T`**: windows, the touch, the print-anchored fill and touch-consistency rules, the stale-touch variant, the mark
    rules and labels (2-4 h, 6-8 h), age limits, the path key, exclusions and their sources, the
    **labeller (class definitions, precedence, every regex and vocabulary list, the sports list, the audit protocol
    and seeds)**, LOW/NEWS membership, cluster ways, gates, placebo strata, the T3 exit rule and fee policy.
  - **`R`**: tag id 21, the barrier title and member templates, the excluded terminal and Up/Down templates, the
    description flags, the rule-window parser (written from out-of-window events, ends in `[2026-10-01, 2026-10-18)`),
    the asset map, **the primary (weekly) vs reported template classes**, the window-component rule, the windows and
    split, checkpoints, the price rules, the σ rule, the touch formula, decided-rung and price-band rules, the GRP
    nesting (one latent per asset × window × direction) and loadings, gate GRC, R2's band half-spreads and fee policy,
    the Binance symbol list and the month-range rule (from `min(T0) − 30 d`), the kline usability rule and the
    timestamp-unit rule (milliseconds before 2025-01-01, microseconds from 2025-01-01 in the spot archive; detected by
    magnitude and unit-tested).
- `model_specs/cb13_v1.json` (the freeze) is likewise hashed in parts T and R. A job pins only the part hashes it needs.
- Jobs refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any T mark, R outcome or R
  price.** The labeller may be revised **once** before the T freeze, and only on the labeller audit (titles only, §CB13-T).
- **Field whitelists.** *Monitor prints:* `ts, condition_id, token_id, outcome_index, price, size, cash, title, slug,
  ctx_event_id, ctx_market_id, ctx_category, ctx_fee_type`, plus `tx16` in memory only, for transaction aggregation
  (never written). **`ctx_event_id`, `ctx_market_id`, `ctx_category` and `ctx_fee_type` are Gamma context fetched after
  receipt; they are declared static market attributes (ids and fee category do not change over a market's life) and
  are used only as labels and keys, never as a price-time feature** (round 1 item 9). **Not parsed:** `side`, `key`, `recv_ts`, `wallet_*`, and every other `ctx_*` (post-receipt
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
| T3 (Stage 2) | maker entry at the **recorded print's** maker-adverse price `P` (the primary fill, §CB13-T; maker fee 0, no rebate); exit as a taker at the **recorded** adverse touch of the 2-4 h mark capture (bought → sell at `bid_h`; sold → buy at `ask_h`); taker fee `r·x(1 − x)` on the exit, `r` = the market's sidecar fee rate, policy `max_if_unknown` (unknown → 0.07, as `ECONOMIC_CONDITIONS_STUDY.md`); size ≤ 100 shares; displayed depth unknown in captures (sweep depth reported where the market was swept) |
| R2 (Stage 2, modelled) | buy the model-favoured token at `a = p_t + hs(p_t)` (YES) or `a = 1 − p_t + hs(1 − p_t)` (NO), `hs` = half the band median spread of `EXECUTION_COSTS.md` (bands < 0.05, 0.05-0.20, 0.20-0.80, 0.80-0.95, ≥ 0.95 → 2.05, 1.5, 1.1, 1.5, 1.25c); taker fee `r·a(1 − a)`, `r = max(feeSchedule.rate, 0.07)` (crypto); held to resolution; **paid on the Gamma resolution** (what the venue paid, as CB12-E2/O2) |
| Binding cost robustness | T3: +0.5c on the exit keeps net > 0. R2: +1.0c on `a` keeps net > 0 |

R2 uses declared, not recorded, quotes (no historical books without pmxt). It is a "modelled-cost economic check (L1/L2
on the sealed window)". Recorded asks enter only in Stage P-R (§2.9). T3 is at recorded prints and touches.

### 2.2 Clocks

- **Monitor prints.** Venue `ts` (s) is the fill time `τ`. Prints with the same `tx16` and `condition_id` are
  aggregated in memory into one transaction (YES-terms VWAP, total size, and the **minimum and maximum YES-terms fill
  price**, needed for the maker-adverse fill price); the hash is discarded. YES terms: a print on
  outcome index 1 at `x` is a YES print at `1 − x`. Receipt time is not used: T replays a resting quote, it does not
  act on the monitor.
- **Capture touch and marks.** Each capture row has its own `received_utc` (a capture takes about 6 min). The **touch**
  for a fill at `τ` is the market's row in the latest complete capture with `received_utc < τ`. **Touch age** =
  `τ − received_utc`. The **mark** at nominal horizon `h` is the market's row in the first complete capture with
  `received_utc ≥ τ + h`, usable iff `received_utc ≤ τ + h + 2 h` (else "no mark (capture gap)", counted; the 10-14
  outage is the main case). **The realised horizon is therefore 2-4 h for the "2 h" mark and 6-8 h for the "6 h" mark,
  and every line is labelled "2-4 h" or "6-8 h"** (round 1 item 10); the realised horizon is reported per class. Gamma's `best_bid`/`best_ask` are the touch. Crossed or one-sided rows are ineligible and never repaired.
- **CLOB `prices-history` (R).** As CB12 §2.2: a point at fidelity 60 is usable from stamp + 3,600 s. `p_t` = the last
  usable point before `t` with age ≤ 6 h; `p_reg` = the last usable point before `t − 6 h` with age ≤ 24 h, a
  different point from `p_t`. Either missing → "unavailable (no price)", counted.
- **Binance klines (R).** A 1m candle `[o, o + 60 s)` is usable at `t` iff `o + 65 s ≤ t` (CB8 §2.2). `S_t` = the close
  of the last usable candle. Klines are parsed from the verified zips in **float64**, never float32, so `high ≥ B`
  cannot flip at equality (round 1 item 8). The touch outcome over `[t, T]` uses candles with `o ∈ [t, T)` (the rule's window end
  `T`, ET-converted by the frozen parser) and reads `high` (reach) or `low` (dip). Only screen and rep paths may open
  candles at or after `t` (guarded accessor).
- `closedTime` is never a population condition, origin or feature.

### 2.3 Uncertainty and decision rule

As CB12 §2.3: unweighted primary; one-sided p = the max over the declared cluster ways; 2,000-draw cluster bootstrap,
**seed 1313**; small-G rule as CB10 §2.3 (G ≥ 30 CR1; 15-29 CR2 with t(G − 1) and the Webb wild bootstrap, 9,999
draws; G < 15 the way leaves the max and its leave-one-cluster-out sign rule binds, as A-C1); top-5 drops; ≥ 100 units
and ≥ 30 clusters in the event way for testability; "unknown" never counts as met (one declared deviation: GTI, §CB13-T).
- **Cluster ways.** **T:** Gamma event (CR1; G ≈ 100-300 per class); **path key × 6-hour block** (round 1 item 4;
  the path key is the underlying asset from the frozen asset map for PATH-SETTLED markets, else the first sidecar
  `series_slugs` entry, else the Gamma event; fills sharing one spot path in one block form one cluster, which the
  event way alone treats as independent; G in the hundreds); **6-hour block** of `τ` (UTC 00/06/12/18, the cohort
  cadence; G_SCREEN ≤ 16, so CR2 if ≥ 15, else it leaves the max and leave-one-block-out binds). p = the max over
  every way in the max. **UTC day** (G = 4 in SCREEN, 5 in HOLDOUT: never in the max). **Leave-one-day-out is binding
  and must keep one-sided p < 0.05 and the sign in every leave-one-out sample** (round 1 item 4; stricter than the
  sign-only A-C1 rule). **R:** Gamma event; ISO week of the checkpoint (one crypto path per week; G ≈ 70 SCREEN,
  26 HOLDOUT); asset × ISO week; **window component** (round 1 item 5: the connected components of the graph whose
  nodes are primary R events and whose edges join two events of the same asset with overlapping rule windows, in any
  direction). With the weekly-only primary, a component is about one asset-week. `Y` is constant across a market's
  checkpoints, so the market, not the unit, is the smallest independent object; p = the max over all four ways.
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
| T1 | mechanism contrast | `D = M̄_LOW,2-4h − M̄_NEWS,2-4h ≥ +0.5c` per filled share (CH128's class-difference floor) |
| T2 | maker sign (mid-marked, upper bound) | `M̄_LOW,2-4h ≥ +0.25c` per filled share (half of the 0.5c median half-spread at the fill, H8: the maker keeps at least half the spread after adverse selection) |
| T3 (Stage 2) | economic, recorded prints and touches | net ≥ +0.5c per filled share after the exit fee |
| R1 | forecasting | slope `β̂ ≥ 0.30` of `Y − p_t` on `q_touch − p_reg` (CH118's floor) |
| R2 (Stage 2) | economic, modelled cost | net ≥ +1.0c per share after fee (CH118's floor) |

### 2.5 Counting (M3 rule)

- Kinds **`cb13_test`** (Stage-1 per-test lines), **`cb13_replication`** (Stage 2, including T3 and R2) and
  **`cb13_descriptive`** (EXCLUDE). Descriptive lines cover the smoke, censuses, gates, the labeller audit, class
  strata including SPORTS-FEED and SCHEDULED-EVENT, the stale-touch, one-per-side, all-prints and size-weighted T
  variants, capacity, the 6-8 h readings, the GRC pregate counts, the cross-horizon implied-σ comparison, R's reach/dip and asset strata, and the Binance-Gamma agreement
  audit. Per-test lines count 0 themselves. **The tests are the `n_tests` of the `ml_explain` count lines** (as CB11
  and CB12); placebo lines count 0. New `battery2.KIND_RULES` entries mirror CB12's; unknown kinds raise.
- **Count lines and `n_tests`:** `creative_batch_13:T` **2** (T1, T2); `creative_batch_13:R` **1** (R1). Replication
  lines `creative_batch_13:<family>:rep` carry `n_tests` = that family's triggered Stage-2 tests (T ≤ 3: T1-rep, T2-rep,
  T3; R ≤ 2: R1-rep, R2).
- **Triggers.** T1-rep iff T1 advanced; T2-rep and T3 iff T2 advanced; R1-rep and R2 iff R1 advanced.
- **Cumulative count: 1,181** (committed `trials.jsonl`, verified at `ee0bc96` and at the round-1 response, `battery2-count-v1`; the host-unioned value
  is recorded by every counting job).
- **CB13 adds 3 fixed tests and up to 5 conditional ones. Budget: 3-8**, so the cumulative count becomes 1,184-1,189,
  plus whatever CB6-CB12 add first.
- Tests behind a failed or unknown gate (smoke, disjointness, GL, GT, GTP, GTI, GR, GRC, GRP, the Stage-2 population
  minimums, availability) are "not testable" or "not run" (p = 1) and are **still counted**. A job waiting on exit 75
  is "pending" and produces no line. Conditional tests count only if their trigger fires; a triggered test that cannot
  run is counted with p = 1.

### 2.6 Placebos and robustness (common)

Design rule as CB12 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 13101-13120.
Common binding robustness for any advance: (i) the declared cost robustness (§2.1) for economic tests; (ii) the p
threshold and the floor hold without the top 5 clusters of each way; (iii) sign by period (T: leave-one-day-out with
p < 0.05 in every leave-one-out sample, §2.3; R: each SCREEN half by window end); (iv) unavailable units are excluded and counted by label, never imputed. A test whose
available share of eligible units is < 60% is "not testable (availability)".

### 2.7 Pre-freeze census (counts only; q0272 for T, q0281 for R)

Outcome guards first; field-restricted accessors. A unit test asserts that no census path receives a mark quote, a
capture row received after any fill's `τ`, a kline at or after any unit's `t`, a Gamma outcome or a later price used
as a target. Features (touches, fill sides, spreads, labels, `q`, `p`, horizons) and unit counts may be computed.
- **T.** Prints and transactions by day, label and fee category; key drops by source; transactions by touch age band
  and by touch position (inside the spread; **touch-consistent**, `a0 ≤ P ≤ a0 + s0` or `b0 − s0 ≤ P ≤ b0`; beyond the
  band, "inconsistent with touch (drift)"), by class (round 1 item 1); first-per-side collapse (reported); fills by
  class, event, path key × 6 h block, 6 h block and day; spread and price bands;
  time-to-scheduled-end bands; excluded units by label ("J4-R boundary", "scheduled end within 3 h", "one-sided",
  "no row"); depth from sweeps (reported). **Gate GT:** ≥ 500 SCREEN LOW fills in ≥ 60 events and ≥ 500 SCREEN NEWS
  fills in ≥ 60 events (CH128's 500-fill class floor), else T1 "not testable (population)", and T2 also if LOW fails.
  **Gate GL (labeller audit):** §CB13-T. **Power gate GTP (feature-only; as CB12 GFP).** Each T test's own estimator and
  cluster ways (including path key × 6 h block) run on a **pre-fill proxy outcome**: the move of the capture mid from
  the capture before the touch capture to the touch capture, signed by the maker direction. It has the variance and
  dependence of a 2-4 h mid move and contains no post-fill information. Only the clustered SEs are written (the max over ways); no proxy point
  estimate is written to any output (unit-tested). `MDE = (z_0.99 + z_0.80) x 1.2 x SE`. **T1 is "not run (power)" if
  MDE > 1.0c, T2 if MDE > 0.5c (2 x floor, as CB12-F), counted.**
- **R.** Events and markets by template (weekly primary; monthly, "by", yearly census-only), asset, direction and end
  month; window components of the primary (count, size distribution, G per way); parser
  failures; flag failures; key and overlap drops by source (plus the full series-rule counterfactual); the
  poly_markets cross-check (share of its post-2025-10 barrier ids the frame found); eligible (market, checkpoint) units
  by label ("decided", "before window start", "unavailable (no price)", "outside [0.03, 0.97]"); `q − p_reg`
  distributions (features, klines before `t` only); "unavailable (no klines)" units; HOLDOUT market and event counts
  only. **Gate GR:** ≥ 300 SCREEN primary markets with units in ≥ 60 events, ≥ 30 ISO weeks **and ≥ 30 window
  components** (the GRC count is re-checked here after price availability); parser failures ≤ 10% of markets; ≥ 95% of markets carry the
  Binance 1-minute high/low flags (else R1 "not testable (basis)"); the frame finds ≥ 98% of the poly_markets barrier
  ids in its window, any template (else "not testable (frame completeness)"). **Power gate GRP (feature-only; round 1
  item 5: one latent per market, nested rungs).** For each (asset `a`, rule window `w`, direction `d`) one latent
  `Z_{a,w,d} = s_d·(√0.5·W_{a,w} + √0.2·X_{wk}) + √0.3·e_{a,w,d}`, where `W_{a,w}` is the shared path factor of that
  asset-window, `X_{wk}` a cross-asset ISO-week factor, `s_d = +1` for reach and −1 for dip (one path pushes the two
  directions oppositely), and the loadings are declared. Every rung `i` of that (asset, window, direction) gets
  `Y*_i = 1{Φ(Z_{a,w,d}) > 1 − p_i}` with `p_i` its price at its **first** eligible checkpoint. So `Y*` is one value per
  market, constant across its checkpoints, and nested across strikes (a far rung touches only if every nearer rung
  does, whenever prices are monotone in the strike). 500 draws (seed 13123). `MDE_R1 = (z_0.99 + z_0.80) x 1.2 x max(SD(β̂*), mean SE per way)`. **If `MDE_R1 > 0.60` (2 x floor), R1 is
  "not run (power)", counted, and R1-rep and R2 are not triggered.**
- MDEs are recomputed from these counts and never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collectors. Queue rules as CB12 §2.8: one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 x `mem_mb`, and a 02:45-05:30 UTC blackout for `mem_mb ≥ 500`. **T jobs
  also avoid the collector pass**: they start only outside `:31-:55` of even hours, or yield to the pass lock. No pmxt
  ingress. Every reader streams one capture, one market or one asset-month at a time. `mem_mb` ≤ 800 everywhere.
  **800 is justified** for q0271/q0274 (one capture's 274,000 rows read with column whitelists into pandas, filtered
  to printed markets, about 150 MB, plus the fill table) and q0282/q0283 (two years of 1m klines for one asset as
  float64, about 40 MB, plus about 30,000 units and 2,000 bootstrap draws on cluster-level sufficient statistics).
- **Network** (`net` lane, priorities 15-19; ≤ 2 rps Polymarket, ≤ 1 rps Binance; T has none):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0270 | T smoke (`cpu` lane, **no network**; round 1 item 11) | 0 | 0.001 GB |
  | q0285 | R smoke (`net` lane) | ≤ 30, < 5 min | 0.001 GB |
  | q0276 | R exclusion keys (increment over CB11 q0221) | ≤ 600 Gamma, ≤ 6 min | ≤ 0.01 GB |
  | q0277 | R frame: Gamma `/events?closed=true&tag_id=21` in one-day `end_date` windows over `[2024-11-01, 2026-10-01)` (about 700 days; crypto Up/Down events dominate the tag, about 5-10 pages a day), barrier templates kept at parse; series lookups | ≤ 8,000, ≤ 70 min | ≤ 0.01 GB |
  | q0279 | Binance: monthly 1m spot zips + `.CHECKSUM` for each parsed asset (BTC, ETH, SOL, XRP; any other parsed asset with a Binance spot USDT pair), from the month of `min(T0) − 30 d` over primary events (about 2024-09) to 2026-09; **zips kept as verified original bytes** (sha256 in the manifest), parsed in float64 at use (round 1 item 8) | ≤ 600, ≤ 12 min at 1 rps | ≤ 0.3 GB (zips) |
  | q0284 | R pre-fetch gate GRC (`cpu` lane, counts only, no network) | 0 | 0.001 GB |
  | q0278 | R prices, **weekly primary members only, and only after GRC PASS** (round 1 items 5, 7): per member `ceil(span / 14 d)` bounded `prices-history` requests at fidelity 60, span = [max(`createdAt`, window start − 1 d), window end], so 1 request for a weekly member; planning about 6,000-9,000 members; the exact Σ is computed by q0277 from frame fields (counts only) and recorded before q0278 is committed | ≤ 12,000 (planning about 6,000-9,000), ≤ 1.7 h | ≤ 0.03 GB |

  Historical `net` total **≤ about 21,000 requests (planning about 14,000-18,000), about 2-3 h of `net` lane at 2
  rps**; if GRC fails, only q0276, q0277 and q0279 run (≤ about 9,000 requests),
  behind CB11's about 10-11 h and CB12's about 6-10 h. **A fetch that has not completed (its `*_complete` status absent)
  is "pending" and is never analysed partially.**
- **Disk guard.** Every CB13 data job declares `--disk-cap-gb` and `--data-dumps-cap-gb 40`, and exits **75** if
  data-dumps + its cap > 40 GiB **or** root free disk − its cap < 4.5 GB. CB13 output caps total **≤ 0.4 GB** (T ≤ 0.05,
  R ≤ 0.35). Exit-75 waits are "pending" (CB10 §2.8 rule). CB13 never deletes or moves host data. If T's source
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
  spread `s0` is ≤ 10c, **touch age ≤ 60 min**, and the market's capture `end_date` is ≥ `τ + 3 h` (so a 2-4 h mark
  can exist before the scheduled end).
- **Fill anchor (round 1 item 1, adopted).** The draft filled a paper quote at the stale touch `q` and read the side
  from where the print landed relative to that touch. Most such "crossings" were book drift since the capture, so
  `d ≈ −sign(drift)`, and `d·(mid_h − q)` subtracted the drift before any post-fill adverse selection. That bias is
  largest in PATH-SETTLED markets, so it biased T1 and T2 against LOW. **The primary fill is now the print itself:**
  every large taker transaction is a real maker fill. The touch only signs it, and only where the print is consistent
  with the touch:
  - with the transaction's YES-terms fill prices `[P_min, P_max]` and touch `(b0, a0)`: if `a0 ≤ P_min` and
    `P_max ≤ a0 + s0`, the transaction lifted the ask, so the maker sold YES (`d = −1`) at the **maker-adverse price
    within the transaction**, `P = P_min` (the lowest price any maker in it sold at);
  - if `b0 − s0 ≤ P_min` and `P_max ≤ b0`, the transaction hit the bid, so the maker bought YES (`d = +1`) at
    `P = P_max`;
  - `b0 < P < a0` (inside the spread): no fill, counted. Any other position ("inconsistent with touch (drift)":
    beyond `a0 + s0` or `b0 − s0`, or straddling the touch) is excluded and counted by class. Its share is a reported
    staleness diagnostic.
- **Every touch-consistent transaction is a unit**, because each is a distinct real maker fill. One-fill-per-side-per-
  pass and all-prints variants are reported. Dependence is handled by the event and path key × 6 h block ways (§2.3).
- **Stale-touch variant (reported, uncounted):** the draft's paper quote at `q = a0` or `b0` with the side read
  against the touch, kept so that the size of the staleness bias can be seen.
- **Size:** each fill is one unit (unweighted per filled share). Size-weighted results are reported.

**Labeller (frozen in part T before q0271; no outcome, mark or price is an input).** Inputs per market: the print's
`title` (the market question) and `slug`, `ctx_category` and `ctx_fee_type` where present (static attributes, §1.4),
and the touch capture's sidecar `fee_type`, `fee_category` and `series_slugs`. Classes, applied in this precedence:
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
- **Gate GL (audit, blind).** After q0270, a seeded sample of 200 SCREEN markets is labelled by an independent
  `science-reviewer` pass from `title` and `slug` alone, under the written definitions, with no labeller output and
  no price. The sample is stratified by label, plus **a sports-adjacent stratum** (round 1 ruling on §7 risk 3:
  non-game sports titles such as transfers, signings, coaching changes, awards, MVP and draft picks, found by a frozen
  keyword list, at least 30 of the 200; seed 13121). **PASS** iff the agreement on {LOW, NEWS, other} is ≥ 85% and
  ≥ 80% within each of LOW and NEWS. One revision is allowed on FAIL, re-audited on a fresh 200 with the same strata
  (seed 13122). A second FAIL → T1 and T2 "not testable (labeller)", counted. The audit file is committed before
  q0271, and the labeller hash is final from then.

**Mark-out.** For a fill with maker direction `d` at price `P`: `M_h = d·(mid_h − P)` cents per share, `mid_h` the
mark-capture mid (§2.2). The primary is the "2 h" mark, **realised 2-4 h** (labelled so). `M_h > 0` iff the maker's
price beat the later mid, so the realised spread exceeded the adverse selection (CH128's sign condition, now measured
from the actual fill price). A mark row whose spread is > 10c is "wide mark", counted; it enters the worst-case check
below. A market that closes before its mark is "closed before mark", counted, with the binding worst case.

**T1 (class contrast).** `D = M̄_LOW,2-4h − M̄_NEWS,2-4h` (fill-level means), one-sided > 0, floor 0.5c; p = max over
the event, path key × 6 h block and 6 h block ways (§2.3). Leave-one-day-out must keep p < 0.05 and the sign.
- **Binding pre-fill placebo.** The same statistic with the pre-fill move in place of `M`: the move from the capture
  before the touch capture to the touch capture, signed by `d`. It must not pass p < 0.01. *Alternative guarded:*
  class-specific trend or momentum in the SCREEN days (a crypto drift week) read as toxicity. The touch-to-print gap,
  which this placebo does not cover, is removed by the print anchor and the touch-consistency band (item 1).
- **Binding composition placebo.** Class labels are permuted across events within strata of (touch spread band x
  touch mid band x time-to-end band: < 1 d, 1-7 d, > 7 d); 200 draws (seed 13101). *Alternative guarded:* the contrast
  comes from spread, price or horizon composition rather than class.
- **Robustness (binding).** Each of the following keeps the sign:
  - touch age ≤ 20 min;
  - the 6-8 h mark;
  - the **adverse-touch mark** (`mid_h` replaced by `ask_h` for maker sells and `bid_h` for maker buys, with every
    wide-mark and closed-before-mark unit included at its adverse touch or worst case);
  - excluding transactions ≥ $10,000;
  - each fill side (maker sells, maker buys);
  - event-weighted means;
  - a staleness-share control: the attribution regression below plus the class's "inconsistent with touch" share.

  Also top-5 drops by event and by block, and leave-one-day-out (p < 0.05).
- **Attribution (binding for the label "class effect").** OLS of `M_2-4h` on the LOW and NEWS indicators plus touch
  spread band, touch mid band, time-to-end band, transaction size band, touch age band and log capture liquidity.
  Credit "class effect" only if the LOW − NEWS coefficient keeps ≥ half of `D`; otherwise the label is "composition,
  not class".
- **Reported (uncounted).** Per-class `M̄` at 2-4 h and 6-8 h, including SPORTS-FEED and SCHEDULED-EVENT, which says
  where the economics studies' losses sit; the stale-touch, one-per-side and all-prints variants; the per-class share
  of transactions inconsistent with the touch; reward-band (`clob_rewards` present) vs not; capacity (sweep depth at
  the touch where swept).

**T2 (maker sign in LOW).** `M̄_LOW,2-4h`, one-sided > 0, floor +0.25c; label "mid-marked maker net, upper bound (free
exit), L1". p and the leave-one-day-out rule as T1.
- **Binding sign-flip calibration.** One coin per event flips `d`; 200 draws (seed 13102). *Alternative guarded:*
  within-event and within-block dependence makes the clustered p anti-conservative.
- **Binding pre-fill placebo** as in T1, applied to `M̄_LOW`.
- **Robustness (binding).**
  - Touch age ≤ 20 min keeps the sign.
  - The 6-8 h mark keeps the sign and ≥ half.
  - Each LOW component (PATH-SETTLED, PUBLIC-STATISTIC) with ≥ 200 fills keeps the sign.
  - The **worst case** keeps p < 0.01 and the floor: wide-mark units at the adverse touch, and closed-before-mark units
    at `d·(Y_adv − P)` with `Y_adv` the adverse extreme 0 or 1.
  - Excluding transactions ≥ $10,000, top-5 drops and leave-one-day-out (p < 0.05).

**Gate GTI (cadence informativeness; CH128's kill, computed in q0273 before T1/T2 are read).** It uses fills with a
later monitor print in the same market in `[τ + 2 h − 30 min, τ + 2 h + 30 min]`. The print-based move is
`d·(VWAP_later − P)`, measured **from the fill print `P`, not from a stale touch** (round 1 item 1). On pairs where both
moves are nonzero, its sign must agree with the sign of `mid_2-4h − P` in > 70% of pairs. FAIL → T1 and T2 "not
testable (cadence)", counted. **Declared deviation (accepted by the round-1 ruling, conditional on item 1):** with
fewer than 200 evaluable SCREEN pairs, the gate is "not evaluable" at Stage 1 and every T line carries the label
"cadence informativeness unverified (n < 200)". **At Stage 2, GTI is evaluated on SCREEN + HOLDOUT pairs pooled; T3
requires a GTI PASS there** (with < 200 pooled pairs, T3 is "not testable (cadence)", counted).

**Power (planning; GTP decides).** H8 counted the draft's crossing rule, not the touch-consistency band, so the new
counts are known only at the census. Before the band and exclusions, SCREEN has about 1,100-1,500 LOW fills (crypto
553, econ+finance 532, plus labelled PUBLIC-STATISTIC from the unenriched prints) and about 700-1,000 NEWS fills. The
band removes the drift crossings, probably a large share in PATH-SETTLED; dropping first-per-side adds back the
repeat prints. G_event is about 230 (LOW) and 190 (NEWS), with 14-16 six-hour blocks. Assume an SD of `M_2-4h` of
about 3c and a design effect of 2-3 once the path key × block way enters. Then `SE(D) ≈ 0.18-0.22c`, so **MDE_T1 ≈
0.7-0.85c** against the 0.5c floor, and `SE(M̄_LOW) ≈ 0.12-0.15c`, so **MDE_T2 ≈ 0.45-0.55c** against 0.25c. Both
floors sit below the MDE. T2 may hit the GTP cut (0.5c), and GT may fail on NEWS (500 fills); both outcomes are
counted.

**Stage 2 (conditional; q0274, q0275).** On `T13_T_hold` (label "adjacent window, same regime"), with the same frozen
rules and labeller, **event-disjoint**: HOLDOUT drops every Gamma event with a SCREEN fill, counted by class. If more
than 40% of HOLDOUT LOW or NEWS fills are dropped, the lines carry the label "HOLDOUT thinned by event overlap", and a
variant keeping them is reported. Each Stage-2 test needs ≥ 500 fills of each class it uses in ≥ 60 events, else "not
run (power)", counted. **q0275 starts only at `T13_T_rep`, after CB3's freeze commit** (round 1 item 3).
- **T1-rep, T2-rep**: the Stage-1 statistic, placebos and robustness.
- **T3 (economic at recorded prices; triggered by T2; needs the pooled GTI PASS).** LOW fills; `net = d·(x_exit − P) −
  r·x_exit(1 − x_exit)`, with `P` the recorded fill print and `x_exit` the adverse touch of the 2-4 h mark capture
  (§2.1). One-sided > 0, floor +0.5c, robustness +0.5c on the exit. Expected to be hard: the exit pays a half-spread
  and a fee against the maker's realised spread, which is why it is the honest recorded-price check. A pass would need
  adverse selection well below the realised spread in LOW.

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
- **Primary template: weekly only (round 1 item 5, adopted with modification).** Events whose parsed window is ≤ 8
  days (titles "<Month> d-d" and "<Month> d-<Month> d") form the primary. Consecutive weekly windows of one asset do
  not overlap, so window components are about one asset-week. Monthly ("in <Month>"), yearly ("in <YYYY>") and "by
  <date>" events are **counted in the census only, with no prices fetched**. The reviewer offered dropping yearly and
  long "by" templates; monthly windows are dropped too, because weekly windows that straddle a month end ("September
  ##-October #", probe row 5) join consecutive monthly windows. With monthly events in the primary, every asset's
  windows would merge into one component, which is the "one cluster per asset" case.
- **Units:** (market, daily 00:00Z checkpoint `t`) with `T0 ≤ t ≤ T − 1 h`, listed ≥ 1 h before `t`, `p_t ∈ [0.03,
  0.97]` and `p_reg` available. The unit must be **not decided**: no touch in `[T0, t)` on the klines, which requires
  kline coverage of `[min(T0, t − 30 d), t)`. Without that coverage the unit is "unavailable (no klines)", counted,
  never assumed undecided (round 1 item 6). Decided units are counted. Weighting: **each market weight 1, split over its
  units** (`Y` is one value per market). The unit-weighted result is reported.
- **Anchor (frozen; no fitting to outcomes).** `σ_t` = the annualised SD of Binance 5-minute log returns of the asset in
  `[t − 30 d, t)` (×√105,120). `τ` = `(T − t)` in years. `q_touch = min(1, 2·(1 − Φ(|ln(B/S_t)| / (σ_t√τ))))`.
  `q_term = 1 − Φ(|ln(B/S_t)| / (σ_t√τ))` is used for the attribution only.
- **Outcome (computed, guarded).** `Y = 1` iff a candle with open in `[t, T)` has `high ≥ B` (reach) or `low ≤ B`
  (dip), compared in float64. The Gamma outcome is used only for the agreement audit (< 97% agreement → the label
  "settlement basis") and for R2's payoff.
- **Gate GRC (pre-fetch component gate, q0284; round 1 item 7).** It runs after the frame (q0277) and the klines
  (q0279), before the prices fetch. It uses frame fields and klines before each checkpoint only, with no price and no
  outcome. It counts SCREEN primary window components that hold ≥ 1 market with ≥ 1 listed, undecided, kline-covered
  checkpoint. **If fewer than 30 such components exist, R1 is "not testable (dependence)", counted, and q0278 (about
  6,000-9,000 requests) is never committed.**

**R1 (forecasting).** The market-weighted OLS slope `β̂` of `(Y − p_t)` on `(q_touch − p_reg)` over SCREEN units,
one-sided > 0, floor 0.30; p = max over the event, ISO-week, asset-week and **window-component** ways (§2.3). The
regressor uses `p_reg` (6 h earlier, a different price point), so `p_t`'s own noise never enters it (CB10's
shared-noise rule).
- **Binding sign-flip calibration.** One coin per window component flips `(q_touch − p_reg)`; 200 draws (seed 13103).
  *Alternative guarded:* the common path within a component makes the clustered p anti-conservative.
- **Binding stale-price check (round 1 item 13: joint fit).** Define `q_spot = q_touch(S_t) − q_touch(S_{t−6h}) +
  p_reg`: `p_reg` moved by the 6 h Binance return through the touch formula. A joint OLS of `(Y − p_t)` on
  `(q_touch − p_reg)` and `(q_spot − p_reg)` must keep the `q_touch` coefficient at ≥ half its solo value with
  one-sided p < 0.05 (max over ways). Otherwise R1 cannot advance, and the label is "price lags spot". *Alternative
  guarded:* the price simply lags the spot, and any spot anchor would "predict" `Y − p`.
- **Attribution (binding for the label "barrier-versus-terminal confusion").** Joint OLS of `(Y − p_t)` on the
  reflection gap `g = q_touch − q_term` and on `(q_term − p_reg)`. Credit the label only if the coefficient on `g` is
  ≥ 0.30 and ≥ half of R1's `β̂`. Otherwise the label is "volatility anchor, not barrier confusion".
- **Robustness (binding).** Each keeps the sign: reach and dip separately; BTC alone; `σ_t` x 0.8 and x 1.2;
  drift-adjusted `q` (trailing 30 d mean log return); each SCREEN half by window end; units with ≥ 1 hourly price
  change in `[t − 6 h, t)`; the Gamma outcome in place of the Binance outcome. Also top-5 drops by event, week and
  component.
- **Reported (uncounted).** The cross-horizon test: the crowd-implied σ (σ solving `q_touch = p_t`) by time-to-end
  bucket within the weekly window (< 2 d, 2-4 d, > 4 d). CH118 predicts higher implied σ at short horizons. Also the
  slope by asset and distance band (`|ln(B/S)|/(σ√τ)` terciles); the share of units with `|q_touch − p_t| ≥ 5c`; and
  the Binance-Gamma agreement.

**Power (planning; GRP decides).** The draft's 0.45-0.5 planning MDE assumed independent events, which round 1 item 5
rules out. The weekly-only SCREEN covers about 74 ISO weeks (2024-11..2026-03), with weekly ladders on 2-4 assets. That
gives about 150-300 window components, but the cross-asset ISO-week way has only about 74 clusters. With SD(`Y − p`)
about 0.38 and SD(`q_touch − p_reg`) about 0.10, treating a component as one independent draw gives `SE(β̂) ≈ 0.22-0.3`,
so **MDE_R1 ≈ 0.85-1.15**. Reach/dip opposition inside a component can lower this toward about 0.5-0.6, because one
path shock moves the two directions oppositely. GRP's nested simulation measures exactly that. **R1 is likely to be
"not run (power)" (counted).** GRC stops the prices fetch earlier if the components are too few. This is R's main
risk (§7).

**Stage 2 (conditional; q0283).** On the sealed HOLDOUT: weekly primary events ending in `[2026-04-01, 2026-10-01)`,
checkpoints ≥ 2026-04-01. **R1-rep** uses the same rules and needs ≥ 30 HOLDOUT components, else "not run (power)",
counted. **R2** is the modelled-cost economic check (§2.1): one entry per market, at the first eligible checkpoint with
`q_touch − a_YES ≥ 5c` (buy YES) or `(1 − q_touch) − a_NO ≥ 5c` (buy NO), held to resolution: `net = Y^G − a − fee`.
One-sided > 0, floor +1.0c, robustness +1.0c on `a`; clustered with the same four ways. **Binding placebo:** the same
rule with `q_touch` replaced by `p_reg` must not pass p < 0.01. **R2 power:** SD(net) is about 0.4 per market and the
component way binds, so `MDE ≈ 10-15c` against the 1.0c floor. R2 therefore applies the GRP rule at q0283: if
`MDE_R2 > 2.0c`, R2 is "not run (power)", counted. A real R money test needs Stage P-R at recorded asks.

### CB13-S and data jobs

- **q0270 T smoke** (`cpu` lane, **no network**; round 1 item 11). PASS needs:
  - the rules part hashes;
  - the refusals on fixtures: J4-R-window captures, sweeps and prints (both edges); `T13_T_hold` rows before the seal;
    HOLDOUT mark quotes before `T13_T_rep`; `surprise_live/`, `cross_venue_live/`, `e00*/`, `trade_samples/`; the
    monitor's `alerts`, `scores`, `outcomes` and `wallets` files; every forbidden field (`side`, `wallet_*`,
    `ctx_chg_1h`, `chg_1h`, `uma_resolution_statuses`);
  - the capture-print join on two SCREEN captures, which reproduces probe H8's touch-age and crossing counts for the
    prints between them and reports the touch-consistency band counts;
  - the labeller on fixtures and on all SCREEN titles, with UNKNOWN ≤ 5% (counts only).
- **q0285 R smoke** (`net` lane, ≤ 30 requests). PASS needs:
  - the R refusals (klines at or after `t` and `holdout/` paths in census mode; `outcomePrices` outside the guarded
    files);
  - the tag-21 one-day walk on two out-of-window days (ends in `[2026-10-02, 2026-10-16]`) finds the barrier events that
    public search finds;
  - the rule parser and flags work on 3 out-of-window weekly barrier events (window, `B`, direction, asset; parse
    success recorded);
  - `prices-history` with explicit bounds on 2 out-of-window members;
  - one Binance month from 2024 and one from 2025 (HEAD + CHECKSUM + parse) confirm the millisecond-to-microsecond
    timestamp change at 2025-01-01 (round 1 item 8).

  Any failure → the dependent family is "not testable (source)", counted. No rule is re-fitted.
- **Labeller audit** (GL, between q0270 and q0271; a `science-reviewer` pass on 200 titles including the
  sports-adjacent stratum, no prices). The audit file is `creative_batch13/labeller_audit.json`, committed with its
  seed and sample ids.
- Every data job writes a manifest (file sha256, request counts, failures, data-dumps size and margin, free disk) and a
  `*_complete` status.

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`. `argv[0]` is under `backend/scripts/`, and `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check. Analysis
jobs also need their family's freeze. All `family` = `creative_batch_13`. Priorities: `cpu` 19 for T and 16-18 for R;
`net` 15-17 (below CB12's 20-24 and CB11's 25-29).

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0270 | cpu | 19 | **no network**, < 10 min, mem 400 | - | T rules part + smoke code reviewed |
| q0271 | cpu | 19 | no network, ≤ 40 min, mem 800 | q0270, labeller audit | after GL PASS is committed |
| q0272 | cpu | 19 | ≤ 15 min, mem 400 | q0271 | with q0271 |
| q0273 | cpu | 19 | ≤ 30 min, mem 500 | q0272, T freeze | after the T freeze |
| q0274 | cpu | 19 | no network, ≤ 50 min, mem 800 | q0273 committed (any result) | not before 2026-10-26T08:00Z |
| q0275 | cpu | 18 | ≤ 30 min, mem 500 | q0274 seal copy, CB3 freeze commit | only if T1 or T2 advanced; not before `T13_T_rep` |
| q0285 | net | 17 | ≤ 30 req at ≤ 1 rps, < 5 min, mem 400 | - | R rules part + smoke code reviewed |
| q0276 | net | 17 | ≤ 600 req, ≤ 6 min, mem 500 | q0285, CB11 q0221 | with q0285's PASS |
| q0277 | net | 16 | ≤ 8,000 req, ≤ 70 min, mem 400 | q0276 | with q0276 |
| q0279 | net | 16 | ≤ 600 req at 1 rps, ≤ 12 min, mem 400 | q0277 | with q0277 |
| q0284 | cpu | 17 | no network, ≤ 15 min, mem 600 | q0277, q0279 | with q0279 |
| q0278 | net | 15 | ≤ 12,000 req (Σ from q0277's manifest), ≤ 1.7 h, mem 300 | q0284 PASS | only after q0284 PASS and q0277's request Σ is recorded |
| q0280 | cpu | 17 | light, mem 300 | q0278, q0279 | as the fetches complete |
| q0281 | cpu | 17 | ≤ 30 min, mem 600 | q0280 seal copy | after the R seal copy is committed |
| q0282 | cpu | 16 | ≤ 1 CPU-h, mem 800 | q0281, R freeze | after the R freeze |
| q0283 | cpu | 16 | ≤ 1 CPU-h, mem 800 | q0282 | only if R1 advanced |

```json
{"id": "q0270_cb13_smoke_T", "title": "CB13-T smoke, no network (common + T rules part hashes; refusals: J4-R window at both edges, T HOLDOUT before seal, HOLDOUT mark quotes before T13_T_rep, surprise_live, cross_venue_live, e00*, trade_samples, monitor alerts/scores/outcomes/wallets, forbidden fields side/wallet_*/ctx_chg_1h/chg_1h/uma; capture-print join reproduces probe H8 on 2 SCREEN captures and reports touch-consistency band counts; labeller UNKNOWN <= 5% on SCREEN titles); counts only", "family": "creative_batch_13", "priority": 19, "expected_value": "go/no-go for every CB13 source", "data": ["live_trades/trades-202610{12..15}.jsonl (whitelisted fields)", "snapshots/ (2 SCREEN captures, whitelisted columns)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": [], "argv": ["scripts/run_cb13.py", "smoke", "--part", "T", "--rules", "../docs/research_lab/seals/cb13_rules.json"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch13/smoke_T.json", "trials.jsonl (cb13_descriptive)"], "next_action": "PASS: labeller audit (GL); FAIL: T not testable (source), counted", "notes": "CREATIVE_BATCH_13.md CB13-S. DRAFT. No network (round 1 item 11). No side, wallet or hash stored. Starts outside :31-:55 of even hours."}
{"id": "q0271_cb13_t_frame", "title": "CB13-T: exclusion keys (ids + timestamps of sealed historical sets with rows in T windows, field-restricted) and SCREEN fill table: transactions in [2026-10-12, 2026-10-16) with min/max fill price, touch from the latest complete capture row (age <= 60 min, two-sided, mid in [0.03,0.97], spread <= 10c, end >= tau+3h); print-anchored fill at the maker-adverse price, side from the touch-consistency band [a0, a0+s0] / [b0-s0, b0] (inside and inconsistent counted); stale-touch variant fields; path key; frozen labeller; features only, no mark", "family": "creative_batch_13", "priority": 19, "expected_value": "T SCREEN population", "data": ["live_trades/trades-202610{12..15}.jsonl (whitelist)", "snapshots/<captures starting 2026-10-11T20Z..2026-10-16T00Z>/rows.csv.gz, rows_ext.csv.gz (whitelist)", "history/{h5_cb1,h5_cb1_ladders,h7_cb4_era,h7_cb4_series,h8_tail,h8_tail_b,h8_text,h8_geo} (id + timestamp columns only)", "creative_batch13/labeller_audit.json"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0270_cb13_smoke_T"], "argv": ["scripts/run_cb13.py", "t-frame", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--split", "screen", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch13/t_screen/{fills.csv.gz,labels.csv.gz,t_exclusion_keys.csv.gz,manifest.json}"], "next_action": "q0272", "notes": "DRAFT. Refuses any capture/print in the J4-R window or T HOLDOUT window, and any mark capture (no forward row is read). Restores archived captures byte-for-byte if deleted from the host. mem 800 justified (section 2.8)."}
{"id": "q0272_cb13_census_T", "title": "CB13-T census, counts only: prints/transactions by day, label, fee category; key drops by source; transactions by touch-age band and touch position (inside / consistent / inconsistent with touch) by class; one-per-side collapse (reported); by class, event, path key x 6h block, 6h block, day; spread/mid/time-to-end bands; exclusion labels; sweep depth (reported); gates GT and GL; GTP clustered SEs on the pre-fill proxy (no point estimate written); MDEs", "family": "creative_batch_13", "priority": 19, "expected_value": "T gates and MDEs before the freeze", "data": ["creative_batch13/t_screen/", "snapshots/ (touch and pre-touch captures only, whitelist)", "book_sweeps/ (depth columns, reported)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0271_cb13_t_frame"], "argv": ["scripts/run_cb13.py", "census", "--family", "T"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch13/census_T.json", "trials.jsonl (cb13_descriptive)"], "next_action": "science-reviewer freeze check (T part)", "notes": "DRAFT. No mark capture opened; no M, D or net computed."}
{"id": "q0273_cb13_screen_T", "title": "CB13-T: gate GTI (print-based move from P), then T1 (LOW - NEWS 2-4 h mark-out from the fill print; event, path key x 6h block and 6h block ways; pre-fill and composition placebos; age<=20m, 6-8 h, adverse-touch mark, >=$10k, side, event-weighted, staleness-share, top-5, leave-one-day-out p<0.05; attribution) and T2 (LOW mid-marked maker net; sign-flip and pre-fill placebos; age, 6-8 h, components, worst-case robustness) on SCREEN", "family": "creative_batch_13", "priority": 19, "expected_value": "T verdicts and the class map", "data": ["creative_batch13/t_screen/", "snapshots/ (mark captures starting before 2026-10-16T00:00Z only)", "live_trades/trades-202610{12..15}.jsonl (GTI print-based moves)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0272_cb13_census_T"], "argv": ["scripts/run_cb13.py", "screen", "--family", "T"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_T.json", "trials.jsonl (cb13_test + creative_batch_13:T n_tests=2)"], "next_action": "commit results; advanced: q0275 after the q0274 seal and CB3's freeze", "notes": "DRAFT. Refuses before the T freeze hash; refuses unless GT, GL, GTP passed (else counted lines). Every line labelled 'L1, worn captures, new statistic'; T2 also 'upper bound (free exit)'."}
{"id": "q0274_cb13_t_holdout", "title": "CB13-T HOLDOUT seal: sha256 of trades-2026102{1..6}.jsonl and rows/rows_ext of captures starting [t_j4r_end, 2026-10-26T00Z); HOLDOUT fill table (features, frozen labeller and fill rules, SCREEN events dropped, counted) and raw mark-quote table (bid/ask at mark captures, no mark-out computed) to t_holdout/; re-read exclusion sets; counts only; seal copy", "family": "creative_batch_13", "priority": 19, "expected_value": "sealed T HOLDOUT", "data": ["live_trades/trades-2026102{1..6}.jsonl (whitelist)", "snapshots/ (HOLDOUT captures, whitelist)", "creative_batch13/t_screen/fills.csv.gz (event ids only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0273_cb13_screen_T"], "argv": ["scripts/run_cb13.py", "t-holdout", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--not-before", "2026-10-26T08:00:00Z", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch13/t_holdout/{fills.csv.gz,mark_quotes.csv.gz,manifest.json}", "research_lab/creative_batch13/t_holdout_SEAL.json"], "next_action": "commit seals/cb13_t_holdout_SEAL.json; q0275 if triggered", "notes": "DRAFT. Exits 75 (pending) before 2026-10-26T08:00Z. Writes no M. Refuses any capture starting before t_j4r_end (round 1 item 2); if J4-R's end has moved, the window starts at the new end (recorded). May run before CB3's freeze (no mark-out)."}
{"id": "q0275_cb13_rep_T", "title": "CB13-T Stage 2 on the sealed HOLDOUT (adjacent window, same regime): T1-rep (if T1 advanced), T2-rep and T3 recorded-price round trip (entry at the fill print, taker exit at the 2-4 h adverse touch, sidecar fee, +0.5c robustness; needs pooled SCREEN+HOLDOUT GTI PASS) (if T2 advanced); >= 500 fills per class used in >= 60 events else not run (power)", "family": "creative_batch_13", "priority": 18, "expected_value": "L2 verdicts", "data": ["creative_batch13/t_holdout/ (seal hash verified first; sources restored from archive if needed)", "creative_batch13/t_screen/ (GTI pooling)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0274_cb13_t_holdout"], "argv": ["scripts/run_cb13.py", "rep", "--family", "T"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_T_rep.json", "trials.jsonl (cb13_replication + creative_batch_13:T:rep)"], "next_action": "pass: Stage P-T registration draft", "notes": "DRAFT. Refuses before T13_T_rep = max(seal copy commit, CB3 freeze commit or its ledger stop record) (round 1 item 3). Only for triggered tests; alpha/5 if early, full Stage-2 Holm once."}
{"id": "q0285_cb13_smoke_R", "title": "CB13-R smoke (R rules part hash; refusals: klines >= t and holdout/ in census mode, outcomePrices outside guarded files; tag-21 one-day walk on 2 out-of-window days; rule parser and flags on 3 out-of-window weekly barrier events; prices-history bounds on 2; Binance HEAD+CHECKSUM+parse for one 2024 and one 2025 month, ms->us timestamp change); counts only", "family": "creative_batch_13", "priority": 17, "expected_value": "go/no-go for every CB13 source", "data": ["public Gamma, CLOB prices-history", "data.binance.vision"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, clob, data.binance.vision"}, "depends_on": [], "argv": ["scripts/run_cb13.py", "smoke", "--part", "R", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch13/smoke_R.json", "trials.jsonl (cb13_descriptive)"], "next_action": "PASS: q0276; FAIL: R1 not testable (source), counted", "notes": "CREATIVE_BATCH_13.md CB13-S. DRAFT. <= 30 requests (round 1 item 11)."}
{"id": "q0276_cb13_exclusion_keys", "title": "CB13-R: exclusion keys = CB11 q0221 key file + id columns of h9_flow, h10_*, h11_*, every CB12 frame (h12_say, h12_quake, h12_prints, live frames), CB8/CB9 frames + seal copies; Gamma lookups for missing event/negRisk/series keys; barrier-overlap list by asset and window", "family": "creative_batch_13", "priority": 17, "expected_value": "disjointness of R", "data": ["creative_batch11/exclusion_keys.csv.gz", "history/*/ (id columns only)", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0285_cb13_smoke_R", "q0221_cb11_exclusion_keys"], "argv": ["scripts/run_cb13.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch13/exclusion_keys.csv.gz", "manifest.json (absent_at_q0276 list)"], "next_action": "q0277", "notes": "DRAFT. >2% missing metadata -> disjointness unverified (R1 not testable, counted). Exit 75 on headroom = pending."}
{"id": "q0277_cb13_touch_frame", "title": "CB13-R: Gamma closed events tag_id=21, one-day end_date windows over [2024-11-01, 2026-10-01); frozen barrier templates (terminal and Up/Down excluded, counted); primary = weekly windows (<= 8 d), monthly/yearly/by counted only; members, strike, direction, asset; rule-window parser and flags; key + same-asset overlap drops; window components; out-of-time split at 2026-04-01; Gamma outcomes to SCREEN and HOLDOUT guarded files; completeness cross-check vs poly_markets.json barrier ids (ids/questions only); min(T0) for the kline range; q0278 request sum (weekly members only)", "family": "creative_batch_13", "priority": 16, "expected_value": "R population and split", "data": ["public Gamma", "creative_batch13/exclusion_keys.csv.gz", "cross_venue/poly_markets.json (ids and questions only, streaming)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0276_cb13_exclusion_keys"], "argv": ["scripts/run_cb13.py", "touch-frame", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h13_touch/{events.csv.gz,members.csv.gz,rules_parsed.csv.gz,split.json,outcomes_guarded_screen.csv.gz,manifest.json}", "history/h13_touch/holdout/outcomes_guarded_holdout.csv.gz"], "next_action": "q0279, then q0284", "notes": "DRAFT. No price read. Capped day windows split until uncapped (counted). outcome_prices/volume of poly_markets.json never parsed."}
{"id": "q0279_cb13_binance", "title": "CB13-R: data.binance.vision monthly spot 1m kline zips + .CHECKSUM for the parsed assets (BTC, ETH, SOL, XRP and any other parsed USDT pair), from the month of min(T0) - 30 d over primary events to 2026-09; verified original zips kept (sha256), parsed in float64 at use; ms/us timestamp units detected; months >= 2026-04 to holdout/", "family": "creative_batch_13", "priority": 16, "expected_value": "R spot, sigma and touch outcomes", "data": ["data.binance.vision (public archive)", "history/h13_touch/members.csv.gz (asset list)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "data.binance.vision"}, "depends_on": ["q0277_cb13_touch_frame"], "argv": ["scripts/run_cb13.py", "binance", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "1", "--disk-cap-gb", "0.3", "--data-dumps-cap-gb", "40"], "timeout_s": 1800, "max_retries": 2, "outputs": ["history/h13_binance/{screen,holdout}/<SYM>-1m-<YYYY-MM>.zip", "manifest.json"], "next_action": "q0284", "notes": "DRAFT. <= 600 requests. Range from q0277's min(T0) (round 1 item 6). A CHECKSUM mismatch is retried once, then the month is 'unavailable (source)'; units needing it are 'unavailable (no klines)', counted."}
{"id": "q0284_cb13_r_pregate", "title": "CB13-R pre-fetch gate GRC, counts only, no network: SCREEN primary window components holding >= 1 market with >= 1 listed, undecided, kline-covered checkpoint (frame fields and klines before t only; no price, no outcome); < 30 -> R1 not testable (dependence), counted, and q0278 is never committed", "family": "creative_batch_13", "priority": 17, "expected_value": "saves about 6,000-9,000 net requests if R cannot be clustered", "data": ["history/h13_touch/{events,members,rules_parsed}.csv.gz (no guarded file)", "history/h13_binance/screen (guarded accessor: klines < t)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0277_cb13_touch_frame", "q0279_cb13_binance"], "argv": ["scripts/run_cb13.py", "pregate", "--family", "R"], "timeout_s": 1800, "max_retries": 1, "outputs": ["research_lab/creative_batch13/pregate_R.json", "trials.jsonl (cb13_descriptive; or the counted not-testable R1 line)"], "next_action": "PASS: commit q0278; FAIL: R1 counted not testable (dependence)", "notes": "DRAFT. Round 1 item 7."}
{"id": "q0278_cb13_touch_prices", "title": "CB13-R: CLOB prices-history per weekly primary barrier member, fidelity 60 in <= 14-day bounded chunks over [max(createdAt, window start - 1 d), window end]; a point is usable from stamp + 3600 s; HOLDOUT rows to holdout/", "family": "creative_batch_13", "priority": 15, "expected_value": "R prices", "data": ["public CLOB prices-history", "history/h13_touch/members.csv.gz"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "net", "network": "clob"}, "depends_on": ["q0284_cb13_r_pregate"], "argv": ["scripts/run_cb13.py", "touch-prices", "--rules", "../docs/research_lab/seals/cb13_rules.json", "--rps", "2", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h13_touch/{screen,holdout}/prices.csv.gz", "manifest.json"], "next_action": "q0280", "notes": "DRAFT. Committed only after q0284 PASS (round 1 item 7). <= 12,000 requests = sum of ceil(span/14 d) over weekly members from q0277's manifest (planning 6,000-9,000). Resumable; incomplete = pending.", "repeat": {"max_runs": 4, "until_log_regex": "\"status\": \"touch_prices_complete\""}}
{"id": "q0280_cb13_seal_R", "title": "CB13-R: HOLDOUT listings sha256 (h13_touch/holdout incl. outcomes_guarded_holdout, h13_binance/holdout); seal-time drops vs every seal copy and frame committed by now (incl. CB12 frames absent at q0276); seal copy seals/cb13_touch_holdout_SEAL.json", "family": "creative_batch_13", "priority": 17, "expected_value": "sealed R HOLDOUT", "data": ["history/h13_touch/holdout/", "history/h13_binance/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0278_cb13_touch_prices", "q0279_cb13_binance"], "argv": ["scripts/run_cb13.py", "seal", "--family", "R"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch13/holdout_SEAL_R.json"], "next_action": "commit the seal copy; q0281", "notes": "DRAFT. Sealed files never edited; drops recorded as DROPPED_* blocks."}
{"id": "q0281_cb13_census_R", "title": "CB13-R census, counts only: events/markets by template (weekly primary; monthly, yearly, by census-only), asset, direction, end month; window components; parser and flag failures; key, overlap and full-series counterfactual drops; poly_markets completeness; units by label incl. unavailable (no klines); q_touch - p_reg distribution (klines before t only); HOLDOUT counts only; gates GR (incl. >= 30 components), GRP (one nested latent per asset x window x direction, price-calibrated at the first checkpoint); MDEs", "family": "creative_batch_13", "priority": 17, "expected_value": "R gates and MDEs before the freeze", "data": ["history/h13_touch/screen (no guarded file; HOLDOUT counts only)", "history/h13_binance/screen (guarded accessor: klines < t)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0280_cb13_seal_R"], "argv": ["scripts/run_cb13.py", "census", "--family", "R"], "timeout_s": 2400, "max_retries": 1, "outputs": ["research_lab/creative_batch13/census_R.json", "trials.jsonl (cb13_descriptive)"], "next_action": "science-reviewer freeze check (R part)", "notes": "DRAFT. No Y, slope or net computed. Refuses on an incomplete manifest."}
{"id": "q0282_cb13_screen_R", "title": "CB13-R: R1 (market-weighted slope of Y - p_t on q_touch - p_reg, weekly primary, Binance outcome in float64; event/ISO-week/asset-week/window-component ways; component sign-flip placebo; joint stale-price check; reflection-gap attribution; reach/dip, BTC, sigma x0.8/x1.2, drift, halves, active, Gamma-outcome, top-5 robustness; Binance-Gamma agreement audit; cross-horizon implied sigma reported)", "family": "creative_batch_13", "priority": 16, "expected_value": "R1 verdict", "data": ["history/h13_touch/screen + outcomes_guarded_screen.csv.gz (opened here)", "history/h13_binance/screen"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0281_cb13_census_R"], "argv": ["scripts/run_cb13.py", "screen", "--family", "R"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_R.json", "trials.jsonl (cb13_test + creative_batch_13:R n_tests=1)"], "next_action": "advanced: q0283", "notes": "DRAFT. Refuses before the R freeze hash, on any holdout/ path, and unless GR and GRP passed (else counted lines)."}
{"id": "q0283_cb13_rep_R", "title": "CB13-R Stage 2 on the sealed HOLDOUT: R1-rep (>= 30 HOLDOUT components) and R2 (modelled-cost hold-to-resolution, 5c filter, band half-spread + 0.07 fee, Gamma payoff; p_reg placebo; +1c robustness; four cluster ways; MDE_R2 > 2c -> not run (power))", "family": "creative_batch_13", "priority": 16, "expected_value": "L2 verdicts", "data": ["history/h13_touch/holdout + holdout/outcomes_guarded_holdout.csv.gz", "history/h13_binance/{screen,holdout} (seal hash verified first)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0282_cb13_screen_R"], "argv": ["scripts/run_cb13.py", "rep", "--family", "R"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch13/results_R_rep.json", "trials.jsonl (cb13_replication + creative_batch_13:R:rep)"], "next_action": "pass: Stage P-R registration draft (recorded asks)", "notes": "DRAFT. Only if R1 advanced."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb13_common.py`: reuse `cb12_common`/`cb11_common`, covering:
  - refused roots, the J4-R pin, disk and free-disk guards with cap 40, exit 75, manifests, `*_complete` status;
  - the cluster bootstrap with the small-G rule, the leave-one-cluster-out rule (sign, and p < 0.05 where declared),
    Holm/BY helpers and per-part rules hashing;
  - the field-whitelist readers for monitor prints, capture rows and sidecar;
  - the archive-restore hook with hash verification.
- `cb13_tox.py`:
  - transaction aggregation (`tx16` in memory; VWAP, `P_min`, `P_max`) and YES-terms conversion;
  - the capture touch index (latest row per market before `τ`, streamed one capture at a time) and touch eligibility;
  - **the print-anchored fill with the touch-consistency band and the maker-adverse price**, the stale-touch variant
    and the path key;
  - the frozen labeller and its audit sampler (with the sports-adjacent stratum);
  - T exclusion keys (id and timestamp accessor);
  - mark lookup, refusing captures in the J4-R window, HOLDOUT marks before `T13_T_rep`, and recording realised
    horizons;
  - `M_h`; T1/T2 with placebos (pre-fill, composition permutation, sign-flip), robustness and attribution;
  - GTI (from `P`; pooled at Stage 2), GTP, the HOLDOUT extractor and seal, T1-rep/T2-rep/T3.
- `cb13_touch.py`:
  - the tag-21 one-day walker (split until uncapped), barrier and terminal templates, and the **weekly-primary
    classifier**;
  - the rule-window parser (ET → UTC, DST), flags, asset map, overlap exclusion and **window components**;
  - the poly_markets streaming id reader and the `prices-history` client (14-day chunks);
  - the Binance archive client (CHECKSUM, verified zips kept, float64 parse, ms/µs timestamp detection, range from
    `min(T0) − 30 d`) and the guarded kline accessor;
  - σ, `q_touch`/`q_term`, decided-rung detection with kline coverage, and the outcome evaluator;
  - GRC; R1 with placebos, the joint stale-price check and attribution; GRP (nested latents); R2.
- `backend/scripts/run_cb13.py` with the §4 subcommands (`smoke --part T|R`, `pregate`); refuses analysis before the
  family's freeze hash.
- Tests (`test_cb13_tox.py`, `test_cb13_touch.py`, `test_run_cb13.py`). They cover:
  - whitelist fixtures with every forbidden field, and the refused roots and files;
  - J4-R refusals at both edges (a HOLDOUT capture at `t_j4r_end − 1 s` refused), and the moving-end rule;
  - T: the HOLDOUT refusal before the seal, and the mark refusal before `T13_T_rep` (no CB3 freeze fixture → refuse);
    touch selection by `received_utc < τ` (equality excluded); the age boundary at 60 and 20 min; YES conversion for
    outcome index 1; **the touch-consistency band edges** (`P = a0` and `P = a0 + s0` fill, `a0 + s0 + tick` is
    "inconsistent", a transaction straddling `a0` is inconsistent); the maker-adverse price (`P_min` for sells,
    `P_max` for buys); the path key fallback order; the mark-capture rule, the 2-4 h and 6-8 h labels and the 2 h
    usability cap; the scheduled-end ≥ `τ + 3 h` rule; the labeller precedence on fixtures (sports before path, path
    before public-statistic, the fallback to NEWS); GTP writing no point estimate; leave-one-day-out p < 0.05;
  - R: a census path refusing klines ≥ `t`; kline usability at `o + 65 s`; float64 equality at `high = B`; the
    millisecond and microsecond archive timestamps; "unavailable (no klines)" when coverage starts after `T0`;
    decided-rung detection; the touch formula at known values (`q_touch = 2·q_term` in the limit, cap at 1); ET window
    parsing across 2025-11-02 and 2026-03-08 DST; terminal and Up/Down templates rejected; weekly vs monthly
    classification, including straddling weeks; components on weekly-inside-monthly fixtures; GRP's nested latent (one
    `Y*` per market, monotone in strike); GRC stopping q0278; HOLDOUT checkpoints before 2026-04-01 dropped;
  - `battery2` kinds and k1 = 3 fixed; the α/5 early rule in Stage 2.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: T1, T2, R1 | **3** | `cb13_test` + count lines `:T` (2), `:R` (1) | p < 0.01, floor, binding placebos and robustness, batch Holm (one-sided α 0.05, k1 = 3 fixed); counted with p = 1 if a gate (including GRC), audit or smoke check fails |
| Stage 2: T1-rep, T2-rep, T3, R1-rep, R2 (each only if triggered) | ≤ 5 | `cb13_replication` + `:<family>:rep` | one Holm over CB13 Stage 2, one-sided α 0.05 (early finishers at α/5) |
| Smoke, labeller audit, pregate counts, census, gates, strata, variants, descriptives | 0 | `cb13_descriptive` | - |
| **Total** | **3 fixed + ≤ 5 conditional = 3-8 (unchanged by round 1)** | | cumulative 1,181 (verified) → 1,184-1,189, plus whatever CB6-CB12 add first |

**Host compute.** Under 4 CPU-hours at nice 19 in total. T takes under about 1.5 h: the frame streams about 50
captures (probe H8's join over 44 captures took about 1 min wall), and the screen bootstraps on about 3,000-20,000 fills
with four cluster ways. R takes under about 2 h, with 2,000 bootstrap draws and 200 placebo draws on market-level
sufficient statistics, and GRP's 500 draws. Peak RAM 0.8 GB. **Network.** T none. R is ≤ about 21,000 requests
(planning about 14,000-18,000; about 2-3 h of `net` lane at 2 rps), or ≤ about 9,000 if GRC stops it. **Disk.**
≤ 0.4 GB.

**Dates (estimates).** Code, the labeller audit and the T freeze check about 2026-10-19/20. **T runs before `T_seal`
on the `cpu` lane** while CB11 holds the `net` lane: q0270 → GL → q0271/q0272 → T freeze → q0273, about 10-20/21. The
T HOLDOUT seal is on or after 10-26T08:00Z. q0275 follows CB3's freeze commit, so it may wait well past 10-26; the
seal makes that wait safe. R's `net` jobs follow CB11's (about 10-11 h) and CB12's (about 6-10 h), so about
10-21..23. GRC can stop R before the prices fetch. The R census, freeze and screen follow with no rule change if the
lane slips.

## 7. Main scientific risks (for the challenger)

1. **T's SCREEN is four days.** The 6 h block way has at most 16 clusters, so it leaves the max or runs under CR2.
   The path key × block way (round 1 item 4) carries the spot-path dependence instead. Leave-one-day-out must keep
   p < 0.05. GT (500 fills per class) may fail on NEWS, in which case T1 is counted as not testable (ruling: correct).
2. **Cadence.** The print anchor (round 1 item 1) removes the stale-touch drift from `M`. The touch now only signs the
   print, inside a one-spread band. The marks are still 2-4 h and 6-8 h captures. GTI is measured from `P`; with
   n < 200 it is "not evaluable" at Stage 1 (accepted), and pooled at Stage 2, where T3 requires it to pass.
3. **The labeller is text-based** (no `resolutionSource` or `gameStartTime`). The guard is the blind 200-title audit,
   which now includes a sports-adjacent stratum (ruling), with one revision allowed.
4. **Composition** (accepted). The composition placebo and the binding attribution, now with a touch-age band and a
   staleness-share control, decide the label.
5. **T2 is an upper bound** (accepted; the +0.25c floor stands). T3, at recorded prints and touches, is the economic
   check and is expected to fail.
6. **Shared windows** (accepted, with item 3). E011, E004-E006 and E009/E010 are untouched by construction. q0275
   waits for CB3's freeze. HOLDOUT captures start at or after `t_j4r_end`.
7. **R is probably underpowered.** The weekly-only primary and the window-component way make the dependence honest,
   and the planning MDE (about 0.85-1.15 without reach/dip opposition) exceeds the 0.60 cut. R1 may be "not run
   (power)". GRC stops the 6,000-9,000-request prices fetch if fewer than 30 components exist. R2's MDE (about 10-15c)
   leaves the money question to Stage P-R.
8. **R's model is approximate** (accepted, with drift and σ as binding robustness; the terminal and Up/Down overlap
   deviation is accepted).
9. **CH119 is not tested,** by its own census (§0.4).

## 8. Next actions

1. Round 1 is answered (§9-§10). Next review: the code-against-design freeze check (`science-reviewer`) once code
   exists. It may reopen any round-1 item. The modifications stay open to it: the weekly-only R primary, which also
   drops monthly; CB3's ledger stop record as an alternative to its freeze; and every touch-consistent print being a
   unit.
2. Write `seals/cb13_rules.json` (parts `common`, `T`, `R`), the modules and tests of §5 and `run_cb13.py`
   (implementer); then the freeze check.
3. T order: q0270 (cpu, no network) → labeller audit GL → q0271 → q0272 → T freeze → q0273, all on the `cpu` lane
   before `T_seal` if possible. Then q0274 on or after 2026-10-26T08:00Z, and q0275 only if triggered and after CB3's
   freeze.
4. R order: q0285 (net smoke) → q0276 behind CB11 q0221 → q0277 → q0279 → q0284 (GRC) → q0278 only on PASS → q0280
   seal → q0281 census → R freeze → q0282 → q0283 if triggered.
5. CB14 adds CB13's frame ids (T fill markets and events; R barrier events) to its exclusion keys. CH119 and ranks 3
   and 5-8 are candidates for CB14 (§0.4).
6. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.

## 9. Challenger review, round 1 (science-reviewer, 2026-10-18)

**Verdicts: CB13-T REVISE, CB13-R REVISE.** 7 blocking and 7 non-blocking items, plus rulings on the §7 risks.

**Main challenge (T).** The draft's paper fill measured staleness, not toxicity. `q` was a capture touch up to 60 min
old, and the side was inferred from where the print landed against that stale touch. So most crossings were book
drift after the capture and `d ≈ −sign(drift)`, and `M_h = d·(mid_h − q)` subtracted the drift magnitude before any
post-fill adverse selection. The bias is largest in PATH-SETTLED markets, which biases T1/T2 against LOW and distorts
the class split. In H8 only 54 of about 1,200 crypto prints were inside the touch. The pre-fill placebo covers the 2 h
before the touch capture, not the touch-to-print gap. GTI partly agrees by construction, since both of its moves start
from the same `q`.

**Blocking.**
1. **T fill anchor.** The primary fill must be the print itself, at the maker-adverse print price within the
   transaction. Keep only prints consistent with the touch (`a0 ≤ P ≤ a0 + s0`, mirrored for buys); exclude and count
   the rest. Keep the stale-touch `M` as reported. Measure GTI from `P`, not `q`.
2. **T HOLDOUT overlaps J4-R.** Captures from 2026-10-20T22:00Z lie inside J4-R `[10-16, 10-21)`
   (`seals/j4r_window.json`, `final` false), which violates the draft's own refusal rule. Captures must start at or
   after `t_j4r_end`.
3. **CB3 hold.** CB3's dev window `[10-21, 10-25)` is counts-only to keep CB3's freeze blind, and T HOLDOUT maker
   mark-outs on those days are the closest quantity to CB3-B's. Ruling: q0275 waits for the CB3 freeze commit; q0274
   (seal, no mark-out) may run earlier.
4. **T time dependence.** Crypto PATH-SETTLED fills in one block share one spot path, so the event way is
   anti-conservative, and with 13-14 filled blocks the block way drops out of the max. Add an (underlying or series ×
   6 h block) way to the max. Leave-one-day-out must keep p < 0.05, not just the sign.
5. **R dependence.** `Y` is constant across a market's checkpoints, and weekly, monthly and yearly ladders on one asset
   share one path, so the event and ISO-week ways are anti-conservative (as CB12 item 2). Add a way of connected
   components of overlapping same-asset windows. Either drop yearly and long "by" templates from the primary, or accept
   one cluster per asset. GRP draws `ε` per unit; it must be one latent per market, with nested rungs (one uniform per
   asset × window × direction).
6. **R kline coverage.** The archive started at 2024-09, but "decided" needs klines from each window start `T0`. Fetch
   from the frame's `min(T0) − 30 d`, else "unavailable (no klines)", never assume undecided.
7. **R pre-fetch gate.** After q0277 and q0279, count SCREEN components, and stop before q0278 (about 12,000-16,000
   requests) if fewer than 30.

**Non-blocking.**
8. Store klines in float64, or keep the verified zips (about 0.2 GB): float32 can flip `high ≥ B` at equality. Binance
   spot archives use microsecond timestamps from 2025-01-01; unit-test this.
9. Declare `ctx_category`, `ctx_fee_type` and `ctx_event_id` as static attributes fetched after receipt.
10. The "2 h" mark is really 2-4 h and the "6 h" mark 6-8 h; label them so.
11. Split the q0270 smoke: T with no network on the `cpu` lane, R on the `net` lane.
12. The header's HEAD `ee0bc96` should be `98a00e6`. The monthly sums give 3,942, not 3,948.
13. Stale-price placebo: fit `q_touch` and `q_spot` jointly.
14. Label the T HOLDOUT "adjacent window, same regime".

**Rulings on §7 risks.**
- (1) The 4-day SCREEN is accepted with item 4. GT probably fails on NEWS, and counting T1 as not testable is correct.
- (2) The GTI deviation is accepted only after item 1. Stage 2 evaluates GTI on SCREEN + HOLDOUT pairs, and T3 needs a
  GTI pass.
- (3) The labeller is accepted; add sports-adjacent titles (transfers, awards) to the audit strata.
- (4) Composition is accepted.
- (5) T2 as an upper bound is accepted, and the +0.25c floor stands.
- (6) E011 is acceptable (frozen code, T never opens `surprise_live/`, no T output stratified by alert status).
  E004-E006 are acceptable (T never parses `chg_1h`). E009/E010 are acceptable (T and R never open
  `cross_venue_live/`). CB3: see item 3.
- (7) R power: the 0.45-0.5 planning MDE assumes independent events, which item 5 rules out. R1 may be "not run
  (power)", and item 7 saves the net lane.
- (8) The reflection model is accepted, with drift and σ as binding robustness. The terminal and Up/Down overlap
  deviation is accepted.

## 10. Response to challenger round 1 (2026-10-18T20:33Z)

No CB13 quantity has been computed, so every change below was made blind. None relaxes a floor, threshold, gate, alpha
or cap. k stays **3 fixed + ≤ 5 conditional = 3-8**, and the cumulative count stays **1,181** (verified), becoming
1,184-1,189.

| Item | Decision | Where | What changed |
|---|---|---|---|
| 1 fill anchor | **Adopted, with one stated modification** | §CB13-T population, mark-out, T1/T2, GTI; §2.1; §2.7; §5 | The primary fill is the print, at the maker-adverse price within the transaction (`P_min` for maker sells, `P_max` for buys). Only touch-consistent transactions count (`a0 ≤ P_min`, `P_max ≤ a0 + s0`; mirrored); inside and inconsistent ones are excluded and counted by class. The stale-touch `M` is reported. GTI is measured from `P`. T3 enters at `P`. **Modification:** every touch-consistent transaction is a unit; first-per-side becomes a reported variant. Justification: once the fill is the real print, each print is a distinct real maker fill. The draft's one-per-pass rule modelled a single paper quote, which no longer exists. Dependence among repeat prints is handled by the event and path key × block ways (item 4), not by discarding fills. The census reports both counts |
| 2 HOLDOUT vs J4-R | **Adopted** | §1.2, §1.3 SEALED-T, q0274 | Touch and mark captures must start at or after `t_j4r_end`. Fills before the first such capture are counted, not back-filled. The window still follows a moved J4-R end |
| 3 CB3 hold | **Adopted, with one stated modification** | §1.2 `T13_T_rep`, §1.3, q0275 | q0275 waits for CB3's freeze commit; q0274 may run earlier. **Modification:** if CB3 is recorded in the ledger as stopped or withdrawn without a freeze, that record lifts the hold. Justification: the hold exists to keep CB3's freeze blind, and a stopped CB3 has no freeze to protect. Without this, an abandoned CB3 would hold T's replication forever with no scientific gain. The freeze check may strike it |
| 4 T dependence | **Adopted** | §2.3, §2.6, T1/T2, §2.7 GTP | Path key (underlying from the asset map, else series slug, else event) × 6 h block way added to the max. Leave-one-day-out must keep p < 0.05 and the sign. GTP uses the same ways |
| 5 R dependence | **Adopted, with one stated modification** | §0.4, §2.3, §CB13-R, GRP, §4 | Window-component way added to the max (four ways), and the sign-flip placebo moves to components. GRP uses one latent per (asset, window, direction): one `Y*` per market, nested in strike, priced at the first checkpoint. **Modification:** the reviewer offered dropping yearly and long "by" templates; monthly is dropped too, so the **primary is weekly only** (≤ 8-day windows). Justification: weekly windows that straddle month ends (probe row 5) join consecutive monthly windows, so a primary with monthly events still collapses to one component per asset. Monthly, yearly and "by" events are counted in the census only, with no prices fetched. This narrows the population and costs power, so it is a tightening |
| 6 kline coverage | **Adopted** | §1.2, §CB13-R units, q0279 | Klines are fetched from the month of `min(T0) − 30 d` over primary events. A unit without coverage of `[min(T0, t − 30 d), t)` is "unavailable (no klines)", counted, never assumed undecided |
| 7 pre-fetch gate | **Adopted** | §0.1, §CB13-R, q0284, q0278 | New q0284 (`cpu`, counts only): GRC counts SCREEN primary components with ≥ 1 listed, undecided, kline-covered checkpoint. Below 30, R1 is "not testable (dependence)", counted, and q0278 is never committed. q0279 now runs before q0278 |
| 8 kline precision | **Adopted** | §2.2, q0279, tests | Verified original zips are kept (sha256; ≤ 0.3 GB cap) and parsed in float64 at use. Millisecond and microsecond timestamps are detected by magnitude, and the R smoke checks one 2024 and one 2025 month |
| 9 static ctx fields | **Adopted** | §1.4 | `ctx_event_id`, `ctx_market_id`, `ctx_category` and `ctx_fee_type` are declared static attributes fetched after receipt, used as labels and keys only |
| 10 horizon labels | **Adopted** | §2.2, §2.4, T1/T2, jobs | Labels are "2-4 h" and "6-8 h", and the realised horizon is reported per class |
| 11 split smoke | **Adopted** | §0.1, §CB13-S, §4 | q0270 is the T smoke (`cpu`, no network); new q0285 is the R smoke (`net`, ≤ 30 requests) |
| 12 header and sums | **Adopted** | header, H10 | The header names parent `ee0bc96` and draft commit `98a00e6`. H10: the monthly counts sum to 3,942; the other 6 markets have no `end` value in the pull |
| 13 joint stale-price fit | **Adopted (binding)** | R1 | Joint OLS of `(Y − p_t)` on `(q_touch − p_reg)` and `(q_spot − p_reg)`. The `q_touch` coefficient must keep ≥ half its solo value with p < 0.05, or R1 cannot advance ("price lags spot") |
| 14 HOLDOUT label | **Adopted** | §1.2, §0, T Stage 2, q0275 | The label is "adjacent window, same regime" |
| Ruling (2) | **Adopted** | GTI, T3 | Stage 2 pools SCREEN + HOLDOUT GTI pairs; T3 needs a GTI pass (with < 200 pooled pairs, T3 is "not testable (cadence)", counted) |
| Ruling (3) | **Adopted** | GL | Sports-adjacent stratum (transfers, signings, coaching, awards, MVP, draft), ≥ 30 of the 200 |
| Ruling (6) | **Adopted** | §1.3 | Stated explicitly: no T output is stratified by E011 alert, candidate or control status; T never parses `chg_1h` |
| Ruling (7) | **Adopted** | §CB13-R power, §7 | Planning MDE restated as about 0.85-1.15 without reach/dip opposition; R1 is expected to be "not run (power)" unless GRP finds otherwise |

**Rejected:** none.

## 11. Code freeze check round 1 (2026-10-19) and fixes

The science-reviewer's code-against-design check of commit fef4066 returned **revise** (22 defects; T screen, T rep and the R seal NO_GO). All fixes make the code match this design, or
declare a deviation that only tightens (no floor, gate, alpha or cap is relaxed). Trial counts are recorded by the code at run time (`battery2.cumulative_count()`); the 1,181 / 1,221 references
above are historical.

| # | Defect | Status | Where |
|---|---|---|---|
| 1 | T1 composition placebo `KeyError` for events outside the T1 index | fixed (`perm.get(e)`; mixed-dataset test) | `cb13_t.composition_placebo` |
| 2 | 60% availability rule (§2.6 iv) unused | fixed: T1, T2, T3, R1, R2 return "not testable (availability)" below 0.60 | `cb13_common.availability`, `cb13_t.*_test`, `cb13_r.unit_availability`, `r2_test` |
| 3 | Smoke FAIL wrote no counted line | fixed: counted once (T1+T2 n=2; R1 n=1), smoke file is write-once | `run_cb13.cmd_smoke` |
| 4 | Holm non-strict (`c9.holm`) | fixed: `c12.holm` | `cb13_common.holm` |
| 5 | Unverified-disjointness stall never counted | fixed: pregate writes the counted R1 p = 1 line once (and screen-R does not count it again) | `run_cb13.cmd_pregate`, `cmd_screen` |
| 6 | UNKNOWN > 5% did not fail GL | fixed in census and screen-T ("not testable (labeller)") | `cb13_t.census_t`, `screen_t` |
| 7 | "population thinned by exclusions" label never set; pooled share | fixed: per class (LOW, NEWS), set by the census | `cb13_t.thin_label`, `census_t`, `frame_report` |
| 8 | Staleness-share control; top-5 drops lacked path key x block | fixed: event-level "inconsistent with touch" share in the attribution regression; top-5 by event, path key x block, block | `cb13_t.attribution`, `analyse` |
| 9 | HOLDOUT omitted `trades-20261026.jsonl` | fixed in both readers and the q0274 seal list | `cb13_t.trade_files` |
| 10 | Exclusion keys dropped ids of files with no timestamp; unbounded scan | fixed: only ids with a stored timestamp inside a T window; files without a timestamp column are counted, not used; scan is resumable and budgeted | `cb13_t.t_exclusion_keys`, `ScanUnfinished` |
| 11 | T Stage 2 lines had role `exploratory_dev` | fixed: `prospective` (the count line keeps a validated role) | `run_cb13.rep_t`, `cb13_common.log_family` |
| 12 | Queue drafts | fixed: q0280 lane `net`, mem 500; q0278 mem 500; q0276 mem 1200, `--budget-min 34`, timeout 2700, repeat 60; q0274 spec `not_before`; placeholders refuse with exit 2; q0277 regex matches `disjointness_unverified` | `queue/drafts/q0274-q0283` |
| 13 | CB3 stop regex liftable by quoting the design | fixed: committed `seals/cb3_stop.json` with `cb3_stop` equal to `CB3_STOPPED_WITHOUT_FREEZE` | `cb13_common.cb3_hold_lifted` |
| 14 | Stage-2 Holm per family | fixed: family step is information only; `run_cb13.py stage2-final` runs ONE strict Holm over all triggered CB13 Stage-2 tests, write-once, adds passes only | `cb13_common.stage2_final`, `run_cb13.cmd_stage2_final` |
| 15 | T smoke join checked accounting only | **declared**: the join is recomputed independently (H8 rule on raw capture rows) and must match the frame's counts; H8's original totals (44 captures, probe script not committed) are not reproduced numerically. The check is stricter than accounting; no gate is relaxed | `cb13_t.smoke_offline` |
| 16 | q0274 ran with a provisional J4-R pin | fixed: `final` must be true (exit 75 otherwise) | `run_cb13.cmd_t_holdout` |
| 17 | Freeze not tied to the rules | fixed: the freeze entry must pin the verified rules sha (T also the LABELLER sha) | `cb13_common.require_freeze` |
| 18 | R primary ignored the 8-day cap | fixed (`window_is_weekly`; longer windows are census-only) | `cb13_r.is_primary`, `classify_status` |
| 19 | R parser / labeller deviations | labeller fixed to the design (crypto category alone no longer makes PATH-SETTLED; audit keywords follow §3: transfers, signings, coaching, awards, MVP, draft). **Declared**: the window is parsed from the title and cross-checked with `endDate` (not from the description; a mismatch of the last date or T is a parser failure), and the description must also carry an ET marker (an extra flag). Both only tighten | `cb13_label.py`, `cb13_r.parse_weekly_window`, `desc_flags` |
| 20 | Gamma outcomes in an unguarded partial | fixed: outcomes go to guarded partial files per split; `frame_partial.jsonl` holds none | `cb13_r.touch_frame` |
| 21 | `hourly_change` used points not usable at t | fixed: only points with stamp + 3,600 s < t | `cb13_r.build_units` |
| 22 | "settlement basis" label missing on R1 | fixed (agreement < 97%) | `cb13_r.attach_basis_label` |
| smoke | R smoke could fail vacuously | fixed: bounded out-of-window pick search (four queries, days 2026-10-02..16, at most 5 walk days, 30-request cap kept) | `cb13_r.smoke_online` |

**New rules part sha256 (seals/cb13_rules.json, regenerated before any freeze; the old file was never pinned):**
- common `4553488ed29ece7b71acad8bb4c8646728e5897c3650218410583d813f373c52`
- LABELLER `6801e2150d4a772b61523aa1ed1548b485255f12099fb52c1154afe6b22cfa0c`
- T `5e0dc8948bb03e611f0da047dcfb110a8a1714c3f653726e15478425ea8483cd`
- R `5695fb5a2ffd2643a4f25418c052eef67c8bc57a412cff5e685154fa690d8279`

Not yet done: a queue draft for `stage2-final` (no q-id reserved), and a focused re-check by the science-reviewer.

### 11.x Verify-round fixes A-E (2026-10-19)

No threshold, floor, alpha or gate changes. The rules were resealed (no job other than the two smokes, which carry no rules sha, had used the T / R rules).

- **A.** Stage 2 decides p only by the strict early alpha / 5 rule or the final CB13-wide Holm (section 2.3, "can only add passes"). Each test now records `checks_ok` = every binding check except the primary p gate (floor, block rule, placebos, robustness, LOO, top-5; for T3 also the +0.5c exit robustness). `advance` (Stage 1) is unchanged: `p < alpha` and `checks_ok`. `stage2_pass_alpha_over_k` = `checks_ok` and p < alpha / 5; `stage2-final` pass = `checks_ok` and (early or Holm reject). A Holm-only pass (for example p 0.02, k2 = 2) is therefore possible; a failing binding check always blocks.
- **B.** A counted failed smoke (T or R) or a failed / stalled R pregate makes the family terminal: `census` returns "stalled" (exit 0), `screen` writes a write-once `results_<family>.json` with the not-testable label (nothing counted twice) instead of waiting for a census, and `stage2-final` treats the family as not triggered (it refuses with "nothing to finalise" if no family triggered).
- **C.** Drafts q0271 (`--budget-min 35`) and q0274 (`--budget-min 45`) carry `repeat` (max_runs 20, until `t_frame_complete` / `t_holdout_complete`); the runner honours `--budget-min` (resumable `ScanUnfinished`).
- **D.** T3 (section 2.2, "size <= 100 shares"): the modelled maker position is `min(print size, 100)` shares. A filter on the printed size would empty the test (prints are >= $1k, normally > 100 shares), and net is per filled share, so the clip leaves the statistic unchanged; `t3_test` records `position` (max shares, number clipped, mean position). Declared reading of the design line.
- **E.** The common part now pins the source sha256 of the shared helpers the rules call: `c12.holm`, `c12.known_lag_s`, `c12.mde`, `c12.cluster_se_mean`, `c12.parse_iso`, `c12.iso_week_of`, `c10.cluster_p`, `c10.cluster_p_d`, `c10.slope_pseudo`, `c10.placebo_advance_rate` (`shared_helper_sources_sha256`).

**Rules part sha256 after the verify round (supersede the list above):**
- common `62e90149ba7e3f282d9876626d51667fd40a559da16b813e03c431f5084ef014`
- LABELLER `1e515bb410598ed7ebc5f6f722b77554acd22d6d9a7548365ba74780c843c780`
- T `05acfff64e218405c225296764b29ead071248753d171a86211582d21d707042`
- R `27ddbc2efa6a5ffdb1125baed9181b0026165491b1ce7b360b71ba8039d82802`

**Focused re-check of A-E (science-reviewer, 2026-10-19, ACCEPT_WITH_FIXES).** A-D accepted (D's reading
`min(print size, 100)` accepted). E completed: `SHARED_HELPERS` now also pins `c10.leave_one_out_sign`,
`cb2_weather.small_g_pvalue` (the p engine behind `cluster_p` / `cluster_p_d`), `c9.top_k_drop_mask` and the selection
helpers `c12.load_exclusion_keys`, `exclusion_stage`, `lookup_keys_closed_first`, `load_drops`, `read_id_set`. Resealed
before any labeller audit sample was drawn: common `62e90149…`, LABELLER `1e515bb4…`, T `05acfff6…`, R `27ddbc2e…`
(the hashes above were updated in place). q0276 now depends on q0221b (CB11's amended exclusion-key job). A failed T smoke
stops at `t-frame` (exit 2) after its counted line, so the census/screen terminal paths are reached only by direct calls;
this is harmless (the count is already written and stage2-final skips the family).

### 11.y Smoke v1 defects and smoke v2 (2026-10-19; engineering gate, outcome-blind, counts only)

Both v1 smokes ran on the host and failed (`smoke_T.json` 05:32Z, `smoke_R.json` 07:30Z, git `4b2afbf`); each wrote its
counted "not testable (source)" line (T1+T2, R1). Review of the failed criteria against the code and the host files
found smoke code defects, not source limitations. Precedent for superseding an engineering FAIL by disclosure: CB7
q0140b, CB8-H smoke v3, CB9 smoke v2, CB12 A6. No threshold, floor, alpha, gate, cap, test count or analysis rule
changes.

- **T, `t_capture_print_join` (defect).** The join took the first two SCREEN captures. The SCREEN capture range starts
  at 2026-10-11T20Z (touches for the first prints), so these were 20261011T203106Z and 20261011T223104Z, both before
  the 2026-10-12T00Z print window: 0 prints between them (`n_prints_between` 0, empty H8 tables), a vacuous failure.
  The other T criteria passed (labeller UNKNOWN 0 of 37,106 transactions). **Fix:** the join uses the first consecutive
  capture pair inside the SCREEN print window (`cb13_t.smoke_capture_pair`) and records the capture ids. A read-only
  host dry run on 20261012T003103Z / 20261012T023105Z gave 422 prints between them, identical index and independent
  H8 tables, and accounting 422 = 422.
- **R, `r_walk_finds_search`, `r_rule_parser`, `r_prices_history` (defect).** The four undated public-search queries
  ("what price will bitcoin hit", ...) are relevance-ranked; their top 20 held no event ending in 2026-10-02..16
  (probe: the Bitcoin query returns monthly, yearly and current-week events). The walk, the parser and prices-history
  never ran (4 requests in all): three vacuous failures. A latent second defect: the walk window of end +- 1 h holds
  more than 300 tag-21 events (5- and 15-minute Up/Down) and would have paged past the 30-request cap. **Fix:** four
  **dated** queries naming the weekly titles that end on the declared walk days ("October 5-11" for 10-12, "September
  28-October 4" for 10-05; Bitcoin, then Ethereum) and a walk window of end +- 60 s (probe: 42 events, one request
  per day, all four weekly barrier events present). The Binance and guard criteria passed in v1 and are re-run
  unchanged.
- **Disclosed expectation for `r_rule_parser` (not a fix).** Probing the 8 weekly events ending 10-05 and 10-12, every
  event has 7-9 late-added members whose description reads "from the creation of this market through 11:59 PM ET"
  with an unquoted High/Low, so the frozen `desc_flags` "High"/"Low" flag fails for them and the event-level
  `flags_ok` is 0. The frozen flag rule is **not** changed here; v2 reports, per parsed event, the member count, members
  passing every flag and the missing flags (counts only). If v2 fails on this criterion, it is a genuine source/rule
  finding (creation-anchored member windows) that needs a science-reviewer ruling before any R design change; under
  the current rules it would also fail gate GR's 95% flag share.
- **Mechanics.** `run_cb13.py smoke --part T|R --supersedes default` refuses unless the v1 file exists and failed,
  writes `smoke_<part>_v2.json` (write-once, with v1's path, sha256 and failed criteria) and leaves v1 untouched. A
  failed v2 writes no second counted line (v1 already counted the family). Every job reads `smoke_<part>_v2.json` when
  it exists (else v1). **The v1 counted lines stay in `trials.jsonl`**: if v2 passes and the family runs, its tests are
  counted again by the screen (an over-count of 2 for T and 1 for R; conservative for multiplicity, never rewritten).
  Drafts: `q0270b_cb13_smoke_T_v2`, `q0285b_cb13_smoke_R_v2`; q0271 depends on q0270b and q0276 on q0285b (q0276 also
  pins the final CB11 key file from q0221b, sha256 `c8a1d64b1dd3f83d376b3809ba5db72b12e751fa825d6ad483854b8136b6d304`).

**Rules part sha256 after the smoke v1 fixes (supersede the 11.x list; common and LABELLER unchanged):**
- common `62e90149ba7e3f282d9876626d51667fd40a559da16b813e03c431f5084ef014`
- LABELLER `1e515bb410598ed7ebc5f6f722b77554acd22d6d9a7548365ba74780c843c780`
- T `f72683f5a5c315552fd6b8defc00613b6eb19c82224bb52477188bb4ddbd90d3`
- R `32bbd825843b43a93652d6d04e2a2c4a4fa3caabb9d9044ac8cb406dabf68cff`

### 11.z Member-level flags and creation-anchored members (2026-10-19; design amendment, pre-data)

The science-reviewer returned **NO_GO** on the first R smoke v2 draft (11.y): its `r_rule_parser` criterion, and the
frame, applied the description flags at event level. Declared **before q0277 (the R frame) and before the R smoke v2
run**. No R outcome, price, kline-derived unit or census count had been read when it was written (the only R data seen
are the v1 smoke counts and the 11.y probes of 8 out-of-window event descriptions).

- **(A) Flags are evaluated per member, as the design states.** The population paragraph (§CB13-R population) defines
  the flags as a member requirement ("Each member must be binary, with a parsed strike ... All frozen flags must be
  present"), and gate GR counts **markets** ("≥ 95% of markets carry the Binance 1-minute high/low flags"). The code
  required every member of an event to pass (`flags_ok = all(...)`), dropped the whole event when one member failed,
  and counted GR's flag share as all-or-none per event. That was a code-versus-design defect. Now a member failing a
  frozen flag is dropped and counted (`n_flag_fail`); an event is dropped for flags (`dropped:flags`) only if no member
  passes; GR's flag share counts members.
- **(B) Creation-anchored members are excluded and counted.** Late-added members state "from the creation of this
  market through 11:59 PM ET on the last day": their rule window is `[createdAt, T]`, not the title window. Deviation 19
  derives the window from the title, so for these members "not decided" and Y would be computed over the wrong window.
  They are **excluded by a fixed description-only rule** (`CREATION_ANCHOR_RE`, `(?i)\bfrom\s+the\s+creation\s+of\s+this\s+market\b`),
  applied before the flags and counted (`n_creation_anchored`), like race-form members. An event whose every member is
  creation-anchored is `dropped:creation_anchored`. They are **not** rescued by relaxing the quoted "High"/"Low" flag:
  the window problem holds whatever the quoting.
- **Disclosed consequences.** Late strikes are listed in response to price moves (strikes the price approaches), so
  this exclusion shifts the population mix towards the strikes listed at the start. In the 11.y probe, 56 of 168 members
  (33%) of the 8 weekly events were creation-anchored; every non-anchored member passed every flag. The census
  reports GR's flag share both ways: the **binding** `flags_share` over the members that are not creation-anchored,
  and `flags_share_incl_creation_anchored` (flags as evaluated on all parsed members), with `creation_anchored_members`
  and `creation_anchored_share`. The GR threshold (0.95), every other gate, floor and alpha are unchanged.
- **This amendment decides gate GR's basis check.** In the probe every creation-anchored member also fails the flags
  (unquoted High/Low), so the flag share including them is 112 / 168 = 0.667 < 0.95: without the exclusion R would
  fail GR ("not testable (basis)"). The exclusion is justified independently of that outcome by the window argument in
  (B): a creation-anchored member's rule window is `[createdAt, T]`, so the title-derived window would compute "not
  decided" and Y over the wrong interval whatever its flags say.
- **Scope of R1.** Because late strikes are excluded, **R1's conclusions apply only to strikes listed when the rule
  window opens** (the members whose rule window is the title window), not to strikes added during the window.
- **Known residual (reported, counts only).** The census reports KEPT members whose `created_epoch` is after their
  event's parsed window start (`late_kept_members`: all kept events and the primary; also counted at more than 1 h
  after it). This catches creation-anchored wording the fixed rule may miss. It is reported only and never used to
  select. The census also sums the member counters of the HOLDOUT events (`holdout_counts.member_flags`, counts only).
- **Smoke v2 criterion `r_rule_parser`.** Every parsed weekly event parses (window, B, direction, asset) and keeps at
  least one member. Across the parsed events, the non-anchored member flag share must be at least `GR_FLAGS_MIN` (0.95);
  this is the gate's threshold applied early. **It is a stated relaxation of the v1 criterion**, which required 100% of
  all members of every event to pass; it now follows the design's GR basis (≥ 95% of the members that are not
  creation-anchored). The smoke reports per event the parsed,
  creation-anchored, flag-failing and kept members and the missing flags (counts only).
- **If this amendment is rejected,** R stays "not testable (source)", counted (v1's line already stands).

Code: `cb13_r.parse_event` (member-level flags, creation-anchor exclusion, event counters `n_members_parsed`,
`n_creation_anchored`, `n_flag_fail`, `n_flags_pass_all` in `EVENT_COLUMNS`), `classify_status`, `census_r` (GR shares),
`smoke_online`, `declared()`; tests in `test_cb13.py`.

**Rules part sha256 after 11.z (supersede the 11.y list; common, LABELLER and T unchanged, so the promoted q0270b is
unaffected):**
- common `62e90149ba7e3f282d9876626d51667fd40a559da16b813e03c431f5084ef014`
- LABELLER `1e515bb410598ed7ebc5f6f722b77554acd22d6d9a7548365ba74780c843c780`
- T `f72683f5a5c315552fd6b8defc00613b6eb19c82224bb52477188bb4ddbd90d3`
- R `7d05b00d276e52097f637939202d79178b3e87c5490d65cbe1a8dcf76009304f`

**After the 11.z review fixes (2026-10-19; `member_flag_counts`, `late_kept_members`, HOLDOUT member counters; the promoted q0285b was built on R `7d05b00d…`, whose smoke code is unchanged):**
R `919070246add0ef76100a9d375c1c16b18c15fa817e2be9492bd9fc03f1775f7` (common, LABELLER, T unchanged).

### 11.r Labeller revision 1 of 1 (2026-10-19; written after the round 1 FAIL and before round 2)

Round 1 of gate GL (seed 13121; records in `docs/research_lab/audits/cb13_gl/`) **failed**: overall 0.91; LOW 0.98 /
0.90; NEWS 0.75 of the labeller's 60 / 0.94 of the reviewer's 48 (each group needs ≥ 0.80 both ways). The design
allows **one** revision before the T freeze, written from the class definitions (§CB13-T "Labeller"), followed by a
fresh round 2 (seed 13122, same strata, a new blind reviewer). A second FAIL makes T1 and T2 "not testable
(labeller)", counted. This is that revision. Its inputs were the class definitions and the titles-only
disagreement list. It is not tuned to individual titles: every rule is a general form that a definition names. No
price, mark or outcome was read. A false-positive check ran on question texts of `cross_venue/poly_markets.json`
(questions only, the source the design names for writing the labeller).

Rules added (`cb13_label.py`; precedence unchanged: SPORTS-FEED > PATH-SETTLED > PUBLIC-STATISTIC > SCHEDULED-EVENT >
UNSCHEDULED-NEWS):
- **PUBLIC-STATISTIC (`PUBLIC_R1_RE`)**, from "macro releases ...; box office; review and chart scores; post or tweet
  counts". The macro list gains PPI / producer prices, the consumer price index (spelled out), core inflation, JOLTS
  and job openings, ADP, initial and continuing claims, trade balance / deficit / surplus, industrial production,
  durable goods, and the release forms YoY / MoM / QoQ (year- and month-over-month). **Post counts:** a number or a
  range followed within three words by "posts" or "tweets". **Box office:** "grossing" forms (top, highest). **Chart
  ranks:** "#n song / album / single / artist", "top song / album / ...", "most streamed", "number one song".
- **SCHEDULED-EVENT (`SCHEDULED_R1_RE`)**, from "award shows" and "Fed/FOMC and central-bank decisions". Award shows:
  "at the [year] ... Awards", the Game Awards, BAFTA, VMA, Brit Awards, Cannes / Palme d'Or, the Booker and Nobel
  prizes (all announced at a set date). Central banks: policy-rate names (key, policy, bank, cash, repo, benchmark,
  refinancing, deposit, target, federal / fed funds rate), "central bank", "monetary policy" and named central banks
  (ECB, BoE, BoJ, BoC, RBA, RBNZ, RBI, SNB, PBoC, Riksbank, Norges Bank, Bundesbank, Bank of England / Japan / Canada /
  Russia / Korea / Mexico / Brazil / Turkey / Israel / Thailand). Their rate is set at scheduled meetings, so a rate
  level at a date is decided by those meetings.
- **SCHEDULED-EVENT (`NEXT_OFFICE_RE`)**, from "elections ... nominations ... votes with a scheduled time": "the next
  <Prime Minister | President | Chancellor | Premier | Chief Minister | First Minister | Minister-President | Taoiseach
  | Mayor | Governor | Speaker of the House>". The holder of such an office is chosen by a general election, an
  investiture vote or a party leadership vote. **Guard against resignation-driven questions:** the rule does not apply
  when the title carries a deadline ("by", "before") or a removal trigger (resign, ousted, removed, impeach, "out as",
  no-confidence, death). Those titles ask *when* a change happens, which is the UNSCHEDULED-NEWS form "will X happen by
  <date>". A generic "next PM" rule without this guard was rejected for that reason. **Known imprecision:** offices
  filled by appointment (for example France's Prime Minister) also match. They are nominations in the definition's
  sense, but their timing can be unscheduled.

Deliberately **not** changed:
- "Republican Senate odds hit 45%": these are Polymarket's own odds, not a published statistic.
- LeBron retirement and Phillies manager: SPORTS-FEED via the sidecar's sports fee type; the reviewer saw titles only.
- "Anthropic's valuation hit $5.0T": the title alone classifies as UNSCHEDULED-NEWS (no asset list matches it). The
  PATH label came from the market's fee type (`crypto_fees*` / `finance_prices_fees`), which the written PATH-SETTLED
  definition makes sufficient on its own. Overriding a definition for one market is outside a vocabulary revision.
- Every threshold, the strata, the seeds, the 5% UNKNOWN rule and the audit protocol.

False-positive check (130,328 historical questions; counts of titles that only the new rules move): PUBLIC_R1 291
(post-count ranges, grossing ranks), SCHEDULED_R1 157 (central-bank meetings, award shows), NEXT_OFFICE 167 (elected
heads of government and mayors; appointed offices as disclosed). Only the rules part LABELLER changes. Part T
hashes `cb13_t` only and pins the labeller through the freeze's `labeller_rules_sha256` and the audit file's
`labeller_sha256`, so the T sha is unchanged. The round 2 sample is drawn with the revised labeller. Its sha is final
from the round 2 audit file onwards.

**Rules part sha256 after 11.r:** LABELLER `95cde0ab70a3845977933a5a13ed2f65263eb903f86ca9da93a90924948d79b9`
(was `1e515bb4…`). common `62e90149…`, T `f72683f5…` and R `91907024…` are unchanged.

### 11.t T screen computes no outcome when no T test is testable (2026-10-19; pre-outcome amendment, before the T freeze)

Before this amendment `screen` (q0273) loaded the post-fill mark quotes, built the outcome dataset, ran GTI and wrote the
`reported` block (per-class mean mark-outs, size-weighted, reward-band and stale-touch means) even when the census gates
had already made every T test untestable. That exposed outcome-bearing numbers for tests that are only counted with
p = 1. **Change (information exposure only; no threshold, formula, gate or label text changed):**
- `cb13_t.census_gate_whys` decides the T1 / T2 gate labels from the counts-only census alone, with the existing
  precedence: GL (labeller) first, then GT ("not testable (population)"), then GTP ("not run (power)"), as §2.7 and
  §CB13-T already state (GT is a census count; T2 also fails when LOW fails GT).
- `cb13_t.screen_t_gate_fail`: when both T1 and T2 are untestable by those gates, the screen writes only the two counted
  terminal lines (p = 1, the census-determined label, `est` null, `n` 0, `advanced` empty) and a descriptive
  `outcome_exposure` record (`mark_index_opened`, `mark_quotes_read`, `outcome_dataset_built`, `gti_run`,
  `reported_written` all false). It never opens fills, prints or the mark index, never builds the dataset, never runs
  GTI (which needs outcome-adjacent prints) and never writes `reported`, `gti` or any mean or estimate field. The runner
  logs one descriptive line `creative_batch_13:screen_T_no_mark_index` (counts 0).
- When at least one test is testable (for example LOW passes and NEWS fails, so T2 only), the full screen runs as
  before, including GTI and `reported`. A GTI cadence failure there still sets "not testable (cadence)" for the tests
  that were testable; a labeller failure is always decided first.
- `freeze-part --part T` also prints record-only `common_rules_sha256` and the T census sha256 (canonical object and file
  bytes, when `census_T.json` exists). Neither is read for any decision.
- Tests: GT-fail screen with the fills, print, pin and mark readers patched to raise (never called); no `reported`,
  `gti`, mean or estimate field; exactly the two counted lines with the population label; precedence unit test.

**Rules part sha256 after 11.t:** T `33bd165b490fb2233ef1fc892b0727a92c17462a88d48acd40af0d375840948b` (was `f72683f5…`).
common `62e90149…`, LABELLER `95cde0ab…` and R `91907024…` are unchanged. q0273 (draft and job), q0274 and q0275 drafts
re-pinned (hash tokens only). Jobs q0270b, q0271 and q0272 still carry the old T token in their notes; they verify the
rules file against the code, not the note.

**11.t disclosure (2026-10-19, coordinator, from the FREEZE_OK re-check).** Before 11.t the screen checked GTI (cadence)
before population, so a GTI failure would have labelled the T tests "not testable (cadence)"; §11.t's "no label
changed" is accurate only for this census (GTI never ran). p = 1 either way.
