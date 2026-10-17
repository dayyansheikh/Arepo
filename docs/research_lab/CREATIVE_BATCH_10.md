# Creative batch 10 (CB10): option-implied anchor for crypto strike ladders, round-level break reversals

`evidence_role: exploratory_historical` (CB10-D Stage 1 on a fresh crypto-ladder fetch; CB10-B Stage 1 on a fresh print
fetch, SCREEN events) / `prospective` (CB10-D Stage 2, post-freeze resolution dates) | status: **DRAFT; not challenged,
not frozen; next: `science-reviewer` challenger round 1.** Drafted 2026-10-17 15:48 UTC+1 (2026-10-17T14:48Z) by the
CB10 design pass. Nothing has been fetched for CB10 beyond the 33 counts-only feasibility requests in §0.3. No CB10
quantity has been computed.

This file turns two round-4 ideas from `CREATIVE_HYPOTHESES_2026-10-18.md` (CH89, CH93) into declared, falsifiable
tests. It records why the other ideas the brief named (CH82, CH87, CH90, CH91) are not in this batch. It follows
`CREATIVE_BATCH_9.md` (CB9) and `CREATIVE_BATCH_8.md` (CB8) in structure and rules. "As CB9 §x" means that rule applies
unchanged, including its challenger-round fixes; CB4 amendment A-C1 governs the day cluster way.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded prices.
- Test tables bind only once the CB10 declaration hash is committed (`model_specs/cb10_v1.json`, the CB10 freeze), after
  a `science-reviewer` challenger round (§8) and a code-against-design freeze check. The fetch rules (frames, seeds,
  splits, exclusion rules, origin clocks, stored fields) are fixed in `seals/cb10_rules.json` before the first CB10 data
  request (q0201).
- **`T_seal` congestion.** Nothing CB10 enters the `net` lane before 2026-10-22T00:00Z. CB6/CB7/h7 `T_seal`-bound fetches
  and the post-`T_seal` jobs of CB8 and CB9 keep priority (CB10 priorities 30-35, below CB9's 36-47). Before `T_seal` only
  q0200 (smoke, at most 60 requests, `cpu` lane, ≤ 1 rps) may run. **CB10 has no early poller** (§0.4: the one idea that
  needed one, CH82, is dropped); D's prospective collection starts after the freeze by design.
- **Queue ids q0200-q0219, one id per job, no letter suffixes** (checked free in `queue/jobs/` and `queue/drafts/` at
  drafting). Specs are drafts **in this document only** (§4). Nothing is created under `queue/` until code, tests and the
  freeze check exist.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB10-D** option-implied anchor for crypto strike ladders (CH89) | in BTC and ETH daily "above $K on date" ladders, a frozen smile-adjusted digital probability read from Deribit option trades in the 2 h before the origin predicts the resolution excess `Y − p` beyond the Polymarket price `p` (D1, slope > 0); prospectively, buying the side the anchor favours by ≥ 4c after fees at the recorded ask pays (D2) | D1 (forecasting, fixed); D1-rep, D2 (conditional on D1) | fresh ladder frame + Data API prints + Deribit history, resolution dates `[2025-10-01, 2026-04-13) ∪ [2026-08-11, 2026-10-01)` | post-freeze resolution dates (56), CLOB books at origins | q0201-q0203, q0207, q0208, q0210, q0211 |
| 2 | **CB10-B** round-level break reversals (CH93) | after a print-confirmed first crossing in 24 h of 0.10/0.25/0.50/0.75/0.90, transactions in the next 10 min revert by 2 h more than after first crossings of pseudo-levels `L ± 0.03` (B1, contrast); a paper maker one cent beyond the level against the break, filled only by trade-through, earns > 0 net per filled share at the 2 h mark (B2, economic) | B1, B2 (fixed); B1-rep, B2-rep (conditional) | fresh print fetch `h10_brk`, SCREEN events, prints `[2026-04-01, 2026-10-01)` | the same fetch, sealed HOLDOUT events | q0201, q0204-q0207, q0209, q0212 |
| - | CB10-F data | smoke, exclusion keys, frames, prints, Deribit trades, seal, census | none | | | q0200-q0207 |

**Counted: 3 fixed (D1, B1, B2) + up to 4 conditional (D1-rep, D2, B1-rep, B2-rep) = 3-7** (§2.5). Budget fixed now; no
CB10 test is added after any CB10 read.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0200 | `cb10_smoke` (counts only: Deribit history paging on 2 out-of-window hours; ladder series paging on 2 out-of-window dates; Data API newest-first cap on 2 out-of-window markets; rule-text flags on 2 live ladder events) | F | after `seals/cb10_rules.json` and smoke code exist (`cpu` lane; may run before `T_seal`) |
| q0201 | `cb10_exclusion_keys` (CB9 q0182 keys + ids of the CB9 P and K/D frames + every seal copy committed since q0182) | F | after `T_seal`, q0182, q0183, q0185 |
| q0202 | `cb10_dlad_frame` (Gamma frame of BTC/ETH daily strike ladders, rule-text flags, series-date exclusion; Data API prints → origin rows; outcomes to the guarded file) | D | after q0201 |
| q0203 | `cb10_deribit_trades` (Deribit option trades `[t − 120 min, t)` per origin time and currency; perpetual hourly bars for the attribution placebo; settlement index to a guarded file) | D | with q0202 |
| q0204 | `cb10_brk_frame` (Gamma frame, key drops, seeded 1,400 markets, event split SCREEN/HOLDOUT `arepo-cb10-brk-split`) | B | after q0201 |
| q0205 | `cb10_brk_prints` (newest-first prints per market, aggregated to transactions at fetch; HOLDOUT written sealed) | B | after q0204 |
| q0206 | `cb10_brk_seal` (HOLDOUT listing sha256, seal-time drops, seal copy) | B | after q0205 |
| q0207 | `cb10_census` (counts only, D and B; gates GD, GB, GB2; MDEs; coverage audits) | all | after q0202, q0203, q0206 |
| q0208 | `cb10_screen_D` (D1, Stage 1) | D | after the CB10 freeze |
| q0209 | `cb10_screen_B` (B1, B2, Stage 1 on SCREEN events) | B | after the CB10 freeze |
| q0210 | `cb10_dlad_live` (D Stage 2 prospective collection: ladder frame, CLOB books and Deribit trades at origins; 56 resolution dates) | D | only if D1 advanced; first origin ≥ freeze + 1 day |
| q0211 | `cb10_rep_D` (D1-rep, D2) | D | after q0210 completes + 2 days |
| q0212 | `cb10_rep_B` (B1-rep, B2-rep on sealed HOLDOUT events) | B | only if B1 or B2 advanced |
| q0213-q0219 | reserved | | |

### 0.2 Selection and scope

**Ranking rule.** As CB9 §0.2: value of information x feasibility within about a week on keyless data, with no
dependence on the pre-`T_seal` `net` lane, plus two CB10-specific constraints: (a) the host data-dumps is near its cap,
so every job must be small (≤ 0.1 GB output, no pmxt ingress), and (b) nothing in CB10 should depend on CB9-S's
verdict on the Data API `side` field (both CB10 families are side-free by construction, §2.2).

**What the drafting session read or computed (2026-10-17T13:30-14:48Z).**
- Committed documents: CLAUDE.md, AGENTS.md, the mission file, the queue README, CB9 (whole), CB8 §0 and §2, CB5 §0
  (CB5-L's object), round 4 (§0, CH82, CH87-CH93, §3-§5), the ledger tail, the checkpoint disk notes.
- Code (read only): `history_backfill` probe notes: Data API `/trades` is newest-first, `limit` ≤ 10,000, `offset` ≤
  10,000 (so at most the newest 20,000 prints per market are reachable); Gamma `/markets` offset caps near 2,100.
- `battery2.cumulative_count()` on the Mac working tree (`battery2-count-v1`) = **1,141** at 2026-10-17T14:45Z (the
  working-tree `trials.jsonl` carries uncommitted lines from another session; a lower bound; the host union step runs
  before every counting CB10 job and records the post-union value).
- Host state (checkpoint, 14:30Z): data-dumps **13.1 GiB**, about +1.1 GB/day; root free about 7.5 GB against the 4 GB
  free-disk guard; collector cap 16 GiB, so the free-disk guard binds first (about 10-20/21 without rotation).

### 0.3 Feasibility probes (counts only, 33 requests, nothing stored)

Scripts lived in `/tmp/cb10probe/` (not committed); no output was written in the repo or in data-dumps. No Polymarket
outcome, outcome price, print price or volume value was printed. Deribit `iv` values were not printed (field presence
and row counts only). 32 requests were keyless GETs to public APIs; 1 was the public Combos OpenAPI document.

| # | Request(s) | Finding |
|---|---|---|
| 1 | 2 Deribit `get_volatility_index_data` (BTC DVOL, 3600 s, 2026-08-11..13 and 2026-05-01..03) | 49 hourly rows each, keyless, with continuation. DVOL is a 30-day ATM index; **not used** as the anchor (no smile, wrong tenor); kept as a reported variant only |
| 2 | 2 `history.deribit.com get_last_trades_by_currency_and_time` (BTC options, 1 h at 2026-09-01T10Z and 2026-05-01T10Z) | 342 and 370 trades, `has_more` false; fields include **`iv`, `mark_price`, `index_price`**, `instrument_name`, `timestamp`, `amount`. A historical, keyless, trade-time implied-vol sample exists |
| 3 | 1 ETH options, 1 h at 2026-01-15T15Z | 428 trades over 12 expiries (dailies 16/19 Jan, weekly 23 Jan, monthlies), `iv` on all 428. History reaches at least January 2026 |
| 4 | 1 Deribit live `get_book_summary_by_currency` (BTC options) | 938 instruments, 408 KB, fields incl. `mark_iv`, `bid_price`, `ask_price`, `underlying_price`. Live-only: used for a Stage-2 reported variant, never in Stage 1 |
| 5 | 1 Deribit `get_tradingview_chart_data` (BTC-PERPETUAL, 60 min, 2026-01-05..04-13) | 2,353 hourly bars (complete). Feeds the realised-vol attribution placebo |
| 6 | 1 Gamma `public-search` "Bitcoin above on" (closed events) | Daily ladders: series `btc-multi-strikes-weekly`, **11 strikes per event, not neg-risk**, `endDate` 16:00Z (EDT) / 17:00Z (EST) = 12:00 ET. Hourly ladders (`bitcoin-multi-strikes-hourly`, 10-20 strikes) exist and are **out of scope** (§0.4) |
| 7 | 1 Gamma event (2026-08-20 BTC ladder: rule text and fee fields only) | `startDate` = `endDate` − 7 days; rule text names the **Binance BTC/USDT 1-minute candle, 12:00 ET, close**; `resolutionSource` Binance; `feeSchedule {rate 0.07, takerOnly, rebateRate 0.2}`; `orderMinSize` 5; tick 0.001 |
| 8 | 3 Gamma `/series` (BTC, ETH slugs) | `btc-multi-strikes-weekly` and `ethereum-multi-strikes-weekly` exist; `/series` returns only the 11 latest events, so the frame must walk closed events by end date (q0202) |
| 9 | 3 Gamma events by slug (2025-11-14 BTC, 2026-01-15 BTC, 2026-08-20 ETH) | 2025-11-14 BTC ladder exists (11 strikes, listed 2025-11-07); the 2026-01-15 slug form is not found (slug formats vary; the frame walks by end date, never by slug); ETH 2026-08-20 exists (11 strikes) |
| 10 | 3 Data API `/trades` (one mid-ladder strike: latest 500; a `start`/`end` window; `offset` 3500) | 500 prints span 1.4 days near expiry (about 350 prints a day on a mid strike, so ≤ 20,000 newest prints cover a 7-day life). The `start`/`end` window returned 0 rows: **`/trades` is not windowed by time**; CB10 pages newest-first and filters locally (as `history_backfill`) |
| 11 | 6 pages of the Combos catalogue `GET /v1/rfq/combo-markets` + 2 `limit` checks + 2 Gamma look-ups + the OpenAPI document | **The catalogue lists combo-eligible leg markets, not combos.** Each item is one ordinary market (`condition_id` found on Gamma; its `title` is the market question; one sample was a geopolitics market) with that market's own `outcome_prices` and `volume`, ordered by volume. The OpenAPI tag reads "Public catalog of markets that can be used as combo legs". There is no public combo price, combo volume or leg-popularity field. 6,000 of the first 6,000 items had 2 position ids (YES/NO); 98% carried a `sports` tag |
| 12 | 2 Gamma closed markets (volume ≥ $10k, ends 2026-09-01..03 and 09-15..17; description text only) | Of 155 non-crypto, non-sports-like markets: 54 mention "credible reporting", but **53 of those 54 also name an official source** (the report clause is a fallback inside official-source rules); 98 are official-only. A clean report-vs-official class needs a primary-standard parser that has not been validated (§0.4, CH87) |

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH89** Deribit anchor for crypto strike ladders | **include (D), priority** | CB9 dropped it because Deribit's keyless chart history covers only recently expired options. Probes 2-3 overturn that: the history endpoint serves **every option trade with its `iv` and `index_price`**, keyless, back to at least January 2026, so a strike-specific implied-vol anchor can be built at any past origin. The ladder population is large and regular (2 assets x 11 strikes a day, listed 7 days ahead). The calendar is chosen to avoid CB8-B's crypto weeks (§1.2). CH30 (Black-Scholes on spot) was never tested; D's attribution placebo separates the option information from the spot-plus-realised-vol part (§2.6) |
| **CH93** stop-cascade fades with the pseudo-level placebo | **include (B)** | Cheapest print-based test in round 4. CB9 deferred CH93-CH98 because they need the Data API `side` field that CB9-S audits. B is written **side-free**: crossings, reversals and fills use transaction price, size and time only (§2.2), so it does not wait for S0. The pseudo-level contrast separates a round-level effect from generic post-move reversal (E004/J4 bounce, HB1 reversal moderators) |
| CH82 Combos | **dropped (data premise fails)** | Probe 11: the public catalogue is a list of leg markets with their own prices; no combo price, combo volume or leg popularity is public. Combo quotes and RFQs need L2 authentication (round 4 §4). None of CH82's three measurables (combo premium, leg popularity, hedge flow after combo volume increments) can be computed keyless. Also sports-dominated (98% of leg markets), and sports scope is the user's open decision. Re-entry: a public combo-level price or volume feed, or a separately designed, verified on-chain decoder of Exchange v3 combo fills (a CH85-scale Polygon log scan) |
| CH87 reporting-standard premium | dropped | (a) CB9's re-entry condition ("after CB7-S reports") is not met; CH87 is a sibling 7-day rules-text carry on the same object as CB7-S. (b) Probe 12: the report clause is almost always a fallback inside official-source rules (53 of 54), so the two classes are not separable by the round-4 regex; a primary-standard parser would need a hand-audited validation first. (c) `h8_text` took the whole filtered pool from 2025-04-01 onward, so a key-disjoint fresh pool is thin. Re-entry: after CB7-S reports, with a primary-standard parser audited on ≥ 200 hand-labelled texts |
| CH90 nowcast anchor for macro buckets | dropped | Its own kill rule needs ≥ 40 resolvable releases; the free nowcasts cover CPI/PCE monthly (Cleveland Fed) and GDP quarterly (GDPNow), about 30 releases since economics buckets became common, all one cluster each. It fails its census by construction today. Re-entry: after about 12 more months of releases |
| CH91 Manifold anchor | dropped | Needs a frozen title matcher with a hand audit of every pair; round 4 expects 100-300 pairs, so the slope MDE (about 0.25 at best) exceeds any useful floor, and capacity is tiny (information, not money). Not cheap |
| CH89 hourly-ladder variant | out of scope | Horizons under a day bring the anchor into the latency game that CB8-B (Binance terminal minutes) studies; options add little at a 1-h tenor beyond spot |
| CH81, CH85, CH86, CH88, CH94-CH98 | not considered for CB10 | outside the brief's priority list; reasons in CB9 §0.4 stand (CH94-CH96 also need the audited `side` field) |

**Sports and categories.** `CB10_SPORTS_IN_PRIMARY = false` (a parameter, as CB8/CB9). In B, sports markets are sampled
into a reported, uncounted stratum (≤ 15% of the frame). B's category scope is a parameter `CB10_B_CATEGORIES` (default:
every category not excluded below). D's object is crypto by construction (the anchor exists only for assets with a
listed option market); `CB10_D_ASSETS = {BTC, ETH}` is a parameter (SOL/XRP options are thin on Deribit and are not in
the primary). Weather, crypto Up/Down (`CB1_UPDOWN_RE`), Pyth dailies and all crypto strike ladders are excluded from B.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB10 | Evidence ceiling |
|---|---|---|---|
| `history/h10_dlad` (**new**, q0202): Gamma frame of BTC and ETH daily "above $K on date" ladders (series `btc-multi-strikes-weekly`, `ethereum-multi-strikes-weekly`), resolution dates in the D window; per-origin print rows (last transaction price and time before `t`, transaction counts in `[t − 6 h, t)`); outcomes only in `outcomes_guarded.csv.gz` | none (CB2-L excluded strike ladders; CB5-L's families are timing questions; CB8-B is Up/Down) | D1 Stage 1 | L1 |
| `history/h10_dlad/deribit/` (**new**, q0203): Deribit option trades in `[t − 120 min, t)` for each origin time and currency (fields: timestamp, instrument, `iv`, `index_price`, amount); BTC/ETH-PERPETUAL hourly bars over `[t − 7 d, t)`; the Deribit index at each resolution minute in `settle_index_guarded.csv.gz` | none | D anchor, attribution placebo, source check | - |
| Post-freeze D collection (**new, conditional**, q0210): ladder frame, CLOB `/book` of both tokens of every strike at each origin (receipt-timed), Deribit trades of the 2 h before each origin fetched at the origin, Deribit live book summary (variant) | none | D1-rep, D2 | L2 (out-of-time, post-freeze) |
| `history/h10_brk` (**new**, q0204/q0205): seeded 1,400 binary markets with scheduled end in `[2026-04-08, 2026-10-01)`, ≤ 3 per event, split by event; newest-first Data API prints aggregated to transactions at fetch (YES-terms VWAP, size, time; no wallet, no side, no hash stored); prints kept only with time in `[2026-04-01, 2026-10-01)` | none | B Stage 1 (SCREEN events), Stage 2 (HOLDOUT, sealed) | L1 / L2 (sealed holdout) |
| `h1_first`, `h2_main`, `h3_power` | worn; h3 retired | **not read**, except their sha256-pinned `sample.csv.gz` id lists for exclusion | - |
| `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`, `h7_cb4_series`, `h8_tail`(`_b`), `h8_text`, `h8_geo`, `h9_flow`, `h10_sign`, CB5 fetches, CB8-B frame/holdout, CB8-H holders, CB9 P and K/D data, `cross_venue/` C1 legs | SB2, CB1-CB9 | **not read** (runner refuses). Committed seal copies, listings and CB9 frame id lists read for **ids only** | - |
| `cb1_extract/`..`cb9` extract tables, `cb3_followup/`, `cb6_followup/`, `live_trades/`, `trade_samples/`, `cross_venue_live/`, `surprise_live/`, live captures | CB1-CB9, monitor, E-series | **never read by any CB10 code path** | - |

### 1.2 Dates (declared; UTC unless ET is stated)

| Name | Value | Meaning |
|---|---|---|
| `T10_draft` | 2026-10-17T14:48Z | this draft; no CB10 quantity computed |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 boundary. No CB10 `net`-lane job before it; no CB10 historical row at or after it |
| `T10_hist_end` | 2026-10-01T00:00Z | no historical CB10 row (print, Deribit trade, resolution) at or after it; keeps clear of the J4-R window `[10-16, 10-21)` and S0a `[10-01, 10-15)` |
| D window (Stage 1) | resolution dates `d ∈ [2025-10-01, 2026-04-13) ∪ [2026-08-11, 2026-10-01)` | **excludes `[2026-04-13, 2026-08-11)`**, CB8-B's crypto calendar (ISO weeks 16-32, every week SCREEN or HOLDOUT) and the pmxt window. Dates before the series' first event simply have no units (census counts) |
| D origins | `t = 12:00 ET` on `d − 5` and `d − 2` (16:00Z in EDT, 17:00Z in EST) | resolution `T = d 12:00 ET` (the settlement candle's close at 12:01 ET is immaterial at these horizons) |
| B window | transactions with time in `[2026-04-01, 2026-10-01)`; markets with scheduled end in `[2026-04-08, 2026-10-01)` | same calendar as CB9-K/D, HB2 and CB8; markets disjoint by key (§1.3) |
| B split | Gamma event SCREEN/HOLDOUT 50/50 by a seeded hash (`arepo-cb10-brk-split`) | at frame time, before any print read |
| `T10_D2_start` | the first resolution date whose `d − 5` origin is ≥ max(CB10 freeze commit, the D1 Stage-1 result commit) + 1 day | D Stage 2 begins |
| `T10_D2_end` | `T10_D2_start` + 56 resolution dates (calendar days; every day has a ladder) | q0211 after `T10_D2_end` + 2 days |
| `T10_D2_collect_max` | `T10_D2_start` + 80 calendar days | freeze-slip rule as CB9: if 56 dates cannot complete, D-rep and D2 are "not run (collection)", counted |

### 1.3 Sealed and untouched data (named)

- **Refused run ids and roots.** `run_cb10.py` refuses every root in the last three rows of §1.1. It writes only under
  `research_lab/creative_batch10/`, `history/h10_dlad/` and `history/h10_brk/`.
- **Exclusion keys (q0201).** CB9 q0182's key file (sha256-pinned) plus, by Gamma id lookup (≤ 50 ids per request,
  `closed=true` retry, parse guard keeping ids and keys only), every id in the CB9 P frame, the CB9 K/D frame (SCREEN and
  HOLDOUT ids from the frame file, not the sealed data) and every seal copy committed since q0182. Keys = Gamma event id,
  `negRiskMarketID`, series id. A frame or seal copy not yet committed is "absent at q0201" (recorded). **Seal-time drops**
  at q0206 re-read every seal copy committed by then, including CB9's `h10_sign` listing if it exists (as CB8 §1.3). If
  more than 2% of exclusion ids lack metadata, disjointness is "unverified" and D1, B1, B2 are "not testable", counted.
- **Series-date exclusion for D (a declared deviation, for the challenger).** The standard series-key rule would drop
  an entire daily ladder series if any prior sample ever held one strike from it (h2_main is a broad random panel, so
  this is likely). Each ladder date is its own Gamma event with its own outcome, and no prior AREPO test has used a
  Deribit anchor. D therefore drops by market id, event id and `negRiskMarketID` as usual, and replaces the series key
  with a **series-date key**: a D event is dropped if any market of the same series in any exclusion source has a
  resolution date within ±1 day of it (adjacent dates share most of the BTC path). Dropped events are counted by source.
  If more than 30% of D-window ladder events are dropped, D1 is labelled "population thinned by exclusions" (reported,
  not a gate).
- **CB8-B.** No CB10 path reads crypto Up/Down markets, Binance data, pmxt files or any date in
  `[2026-04-13, 2026-08-11)` for D. B excludes crypto Up/Down and every crypto strike ladder.
- **CB9.** B's markets are key-disjoint from CB9-K/D and CB9-P (q0201). CB10 never reads CB9 data, receipts or verdicts.
  B is side-free, so S0's verdict changes no B computation or label. D uses print price and time only.
- **SEALED-B (HOLDOUT events).** q0205 writes HOLDOUT transaction files into `creative_batch10/brk/holdout/` with a
  listing sha256. Seal copy `seals/cb10_brk_holdout_SEAL.json` committed by q0206 before q0207. The census reads HOLDOUT
  file and event counts only. No CB10 path opens a HOLDOUT file before B1 or B2 advanced and its Stage-1 result is
  committed.
- **Outcome guard (D).** Gamma `outcomePrices` go only to `outcomes_guarded.csv.gz`; the Deribit index at resolution
  goes only to `settle_index_guarded.csv.gz`. Both are opened only by q0208/q0211 (unit test). B has no outcome: its
  target is a later transaction price (a print-based mark, as CB9-K).
- **J4-R window and `T_seal`.** No CB10 historical row lies in `[2026-10-16, 2026-10-21)` or at/after `T10_hist_end`.

### 1.4 Rules files

- `seals/cb10_rules.json` (before q0200/q0201) fixes: the D frame rule (series slugs, question regex
  `^Will the price of (Bitcoin|Ethereum) be above \$([\d,]+) on ([A-Z][a-z]+ \d{1,2})\?$`, rule-text flags written from a
  live out-of-window event at rules time: "Binance", "BTC/USDT" or "ETH/USDT", "1 minute", "12:00", "ET", "close"),
  the series-date exclusion, origin clocks, the freshness rule, the IV-fit rule and its constants, the anchor formula,
  the D2 edge threshold; B's frame, sample size, seeds, split, levels and pseudo-levels, episode rules, marks and maker
  rule; the census gates; the smoke criteria.
- Fetchers refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any D or B read.**
- No wallet field is read or stored by any CB10 job (no HMAC key is needed).

## 2. Common rules (deltas from CB9 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| D1 | none (forecasting test against the last transaction price) |
| D2 | buy the anchor-favoured token at the **recorded** CLOB best ask `a` at the origin; taker fee `f(a) = r·a·(1 − a)`, `r = max(Gamma feeSchedule.rate at frame time, 0.07)` (crypto, probe 7); held to resolution; no rebate |
| B1 | none (mechanism contrast on transaction prices) |
| B2 | resting maker, fee 0; **no rebate** in the primary; the rebate version (`0.2 · r · p(1 − p)` per filled share at the recorded rate) is reported |
| Binding cost robustness | D2: +0.5c on `a`. B2: the latency rule (§2.6 (vi)) and the trade-through fill rule (already primary) |

### 2.2 Clocks

- **Deribit.** Venue `timestamp` (ms). A trade is usable at `t` iff its timestamp < `t`. Perpetual hourly bar `[o, o + 1 h)`
  usable iff `o + 1 h ≤ t`. The settlement index (guarded) is the `index_price` of the last BTC (ETH) option trade at or
  before `T`, used only by the source check.
- **Data API prints.** Venue `timestamp` (s). Prints are aggregated **by transaction hash at fetch** into one row per
  (market, transaction): YES-terms VWAP (outcome-1 prints mapped to `1 − price`), total size, time. The hash is then
  discarded. A condition at `t` uses transactions with time < `t`. **No CB10 statistic uses the `side` field.**
- **CLOB books (D Stage 2).** Receipt time; a book is the state at its receipt time; crossed books ineligible, never
  repaired.
- `closedTime` is never a population condition or an anchor.

### 2.3 Uncertainty and decision rule

As CB9 §2.3 (unweighted primary; one-sided p = max over declared cluster ways; 2,000-draw cluster bootstrap, **seed
1010**; small-G rule; A-C1 day way; top-5 drops; ≥ 100 units and ≥ 30 clusters for testability; "unknown" never counts as
met). Cluster ways: **D** resolution date (BTC and ETH of the same date in one cluster) and asset x resolution date. **B**
Gamma event and UTC day of the break.

- **Stage 1 (D1, B1, B2).** Advance iff one-sided p < 0.01, the §2.4 floor is met, and every binding placebo, robustness
  check and gate holds. Batch-Holm label (one-sided α = 0.01, **k1 = 3**, fixed) reported; BY label (q = 0.10 over
  `battery2.cumulative_count()` at the run) triage only.
- **Stage 2 (D1-rep, D2, B1-rep, B2-rep).** One Holm at one-sided α = 0.05 over every CB10 test reaching Stage 2, each in
  its Stage-1 direction (D2 in its declared direction, net > 0); k fixed when the last Stage-1 result is final; early
  finishers judged at α/k. Labels: B1-rep, B2-rep "sealed same-calendar holdout replication (L2)"; D1-rep "out-of-time
  replication on post-freeze resolution dates (L2)"; D2 "prospective economic check at recorded asks (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| D1 | forecasting | slope `β̂ ≥ 0.30` of `Y − p` on `q − p` |
| D2 | economic | net ≥ +1.0c per share after fee |
| B1 | mechanism contrast | real-level minus pseudo-level mean reversal ≥ +0.5c |
| B2 | economic | net ≥ +1.0c per filled share at the 2 h mark; route gate: net per posted episode (100 shares posted, unfilled = 0) > 0 |

### 2.5 Counting (M3 rule)

- Kinds `cb10_test` (Stage 1), `cb10_replication` (Stage 2, including D2), `cb10_descriptive` (EXCLUDE: census, gates,
  strata, the DVOL and flat-smile variants, the cascade-intensity descriptive, every reported variant); placebo lines
  count 0. Count lines `creative_batch_10:D`, `:B` (`n_tests`). New `battery2.KIND_RULES` entries as CB9 §2.5; unknown
  kinds raise.
- **Cumulative count at drafting: 1,141** (§0.2; lower bound).
- **CB10 adds 3 fixed tests (D1, B1, B2) and up to 4 conditional ones (D1-rep and D2, triggered by a D1 advance; B1-rep,
  B2-rep, each triggered by its own Stage-1 advance).** Budget: 3-7.
- Tests behind a failed or unknown gate (smoke, disjointness, GD, GB, GB2, source check, coverage audit) are "not
  testable" or "not run" (p = 1) and are **still counted**. Conditional tests count only if their trigger fires; a
  triggered test that cannot run is counted with p = 1.

### 2.6 Placebos and robustness

Design rule as CB9 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 10101-10106.

- **D1 gap sign-flip calibration (binding).** The sign of `q − p` is flipped by one coin per resolution date (shared by
  every unit of that date). *Alternative guarded:* about 200 strongly dependent dates (all strikes of a ladder settle on
  one price) make the clustered p anti-conservative.
- **D1 option attribution (binding for crediting "option-implied information").** `q_RV`: the same digital with σ =
  the 7-day realised volatility of the perpetual's hourly log returns over `[t − 7 d, t)` (annualised, flat smile, same
  `S`). Joint OLS of `Y − p` on `(q − p)` and `(q_RV − p)`, same clusters. Credit "option-implied anchor" only if the
  joint coefficient on `(q − p)` is ≥ half its solo value. A failure leaves an advance standing, labelled "a
  spot-plus-realised-vol digital explains it (CH30-type); options add nothing measurable".
- **D1 spot-staleness control (binding robustness).** `q'` uses `S` = the `index_price` of the last Deribit trade at or
  before the time of the Polymarket transaction that set `p` (not at `t`). D1 on `q'` keeps the sign and ≥ half the
  magnitude. *Alternative:* the Polymarket price lags a spot move in the 30 minutes before `t`; that is CB8-B's latency
  object, not CH89's distributional one.
- **B1 real/pseudo label swap calibration (binding).** Within each Gamma event, the real and pseudo labels of all its
  episodes are swapped with probability 1/2 (one coin per event; the day way uses one coin per UTC day). *Alternative:*
  episodes of one event share a price path, so the clustered p of a contrast can be anti-conservative.
- **B2 pseudo-level attribution (binding for crediting a "stop-cascade route").** `B2_pseudo`: the identical maker at
  pseudo-level breaks (quote one cent beyond the pseudo-level). Credit "stop-cascade route" only if `B2 − B2_pseudo ≥
  B2 / 2`. A failure leaves an advance standing, labelled "a generic post-crossing maker, not a round-level route".
- **B cascade descriptive (labelling only).** Transactions and volume in `(t_b, t_b + 10 min]` after real vs pseudo breaks.
  If the real/pseudo volume ratio is < 1.2, a B1 advance is labelled "round-level reversal without a measurable cascade"
  (CH93's mechanism not shown).

**Binding robustness for any advance or pass:** (i) D2: the +0.5c cost robustness keeps net > 0; B: the 30-min mark keeps
the sign and ≥ half the magnitude; (ii) p threshold and floor hold without the top 5 clusters of each way; (iii)
unweighted and size-weighted estimates agree in sign (D by transaction size at `p`, capped at 2,000 shares; B by 10-min
transaction volume; B2 by filled shares); (iv) sign by period: D in both sub-windows (2025-10..2026-04 and 2026-08..09)
and for each asset separately; B in ≥ two thirds of months with ≥ 200 episodes; (v) unavailable units: D units without a
fresh transaction or an IV fit are excluded and counted, and D1 is "not testable (source)" if fewer than 60% of eligible
units are available; B episodes without a 2 h mark are scored at −1c (the declared worst case; B2 fills without a mark at −1c per filled share); (vi) latency: D
uses `p` from a transaction within 10 min of `t` instead of 30 min; B2 quotes post at `t_b + 120 s` instead of `+ 60 s`;
each keeps the sign and ≥ half the magnitude.

### 2.7 Pre-freeze census (counts only; q0207)

Outcome guard first; field-restricted accessors; a unit test asserts that no census path receives `Y`, the settlement
index, a 2 h mark or a fill P&L. **No slope, net, reversal or contrast is computed.** Features (`p`, `q`, `q_RV`, levels,
crossing times) and fill **counts** may be computed.
- **D.** Ladder events and markets by asset and month; rule-text failures; exclusion drops by source (market id, event id,
  series-date); origins; origins with a fresh transaction (30 min and 10 min); origins with an IV fit (two-sided smile,
  ATM-only fallback, none); expiry distance distribution; units with `0.05 ≤ p ≤ 0.95`; distribution of `|q − p|` (share
  ≥ 0.04); `cor(q − p, q_RV − p)` (feature-only, sizes the attribution placebo's power). **Gate GD:** ≥ 1,500 D1 units in ≥
  100 resolution dates, each asset ≥ 30% of units, and ≥ 200 units with a Deribit expiry within 3 days of `T` (CH89 kill
  3). Fail → D1 "not testable", counted.
- **B.** Frame, key drops, SCREEN/HOLDOUT markets and events; truncated markets (newest-first cap reached before the window
  start); real and pseudo episodes after the mutual-exclusion rule; episodes with a 10-min transaction and a 2 h mark;
  real/pseudo B2 quotes filled (count only). **Gate GB:** ≥ 1,000 real and ≥ 1,000 pseudo SCREEN episodes, ≥ 100 events,
  ≥ 60 UTC days. **Gate GB2:** ≥ 300 filled real-level B2 episodes. Fail → the test is "not testable", counted.
- **Coverage audit (B).** Share of SCREEN markets whose reachable print history covers their whole in-window life
  (newest-first cap not reached). **PASS iff ≥ 80%.** Labels as CB9 §2.7: audit FAIL → B "not testable (source
  limited)"; a GB fail reads "no opportunity" ("round-level breaks are rare") only if the audit passed.
- MDEs are recomputed from these counts and are never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collector. Queue rules as CB9 §2.8 (one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 x `mem_mb`, 02:45-05:30 UTC blackout for `mem_mb ≥ 500`). **No pmxt
  ingress anywhere in CB10.** All readers stream (one market or one origin at a time); peak RAM ≤ 0.8 GB.
- **Before `T_seal`.** Only q0200 (≤ 60 requests: about 8 Deribit history, about 30 Gamma/Data API, a few live Gamma
  events; `cpu` lane, ≤ 1 rps, under 3 minutes, with the collector yield). Disclosed overlap: at most 1 rps added to a
  running `net`-lane job's rate for under 3 minutes (as CB9 q0180).
- **After `T_seal`** (`net` lane, priorities 30-35, behind every CB6-CB9 job):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0201 | exclusion keys (increment over q0182) | about 300 Gamma | ≤ 0.005 GB |
  | q0202 | D frame + prints | about 350 Gamma + about 4,500 Data API (≤ 2 pages per market, about 4,400 markets at most), about 45 min at 2 rps | ≤ 0.01 GB |
  | q0203 | Deribit trades + perpetual bars | about 1,000 Deribit history (2 currencies x about 400 origin times x 1-2 pages) + about 20 chart requests | ≤ 0.02 GB |
  | q0204 | B frame + split | about 1,000 Gamma (one-day `end_date` windows, paged) | ≤ 0.005 GB |
  | q0205 | B prints → transactions | about 2,000 Data API (1-2 pages per market), about 20 min at 2 rps | ≤ 0.06 GB |
  | q0206 | B seal | about 50 Gamma | ≤ 0.001 GB |
  | q0210 | D Stage 2 (conditional) | about 110 requests per origin day (88 CLOB `/book`, about 10 Gamma, about 6 Deribit, 2 book summaries), 56-60 days, `cpu` lane at ≤ 1 rps | ≤ 0.01 GB |

- **Disk guard.** Every CB10 data job declares `--disk-cap-gb` (its output cap, all ≤ 0.06 GB) and
  `--data-dumps-cap-gb 14` (current convention), and exits **75** if data-dumps + its cap > 14 GiB **or** root free disk −
  its cap < 4.5 GB (the 4 GB collector guard plus 0.5 GB margin). CB10 output caps total **≤ 0.12 GB**. The precondition
  never changes retention.
- **Network etiquette.** Shared `Limiter` per process, yield to the live collector, 429 / `Retry-After` back-off, stop on
  repeated 429, collector-health stop. Deribit ≤ 2 rps (used by no other AREPO job). CLOB ≤ 1 rps in Stage 2.
- **Stop rules.** 5 CPU-hours per family. A job that fails twice for the same non-transient reason stops and is
  recorded. A null is "not detected at MDE x". **No re-screen of a failed CB10 test** with altered levels, pseudo-levels,
  marks, horizons, origins, freshness rules, IV-fit rules, edge thresholds, windows or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2) → separate prospective confirmation (Stage P) →
economic validation at recorded prices.
- **Stage P-D.** The D2 rule on a fresh post-Stage-2 window with depth-aware fills (size at the ask, partial fills) and
  the live Deribit chain (mark IVs) as a pre-registered alternative anchor.
- **Stage P-B.** The B2 maker on the live print stream with sweep-recorded books (queue position known at the quote).

---

## 3. Tests

### CB10-D: Option-implied anchor for crypto strike ladders (CH89)

**Question.** In BTC and ETH daily "above $K on date" ladders, does the Deribit option market's digital probability that
the price finishes above `K` predict the resolution excess `Y − p` beyond the Polymarket price `p`? Prospectively, does
buying the side the anchor favours at the recorded ask pay after fees?

**Mechanism.** Deribit is the deepest crypto option venue; its smile prices the whole distribution of the price at each
expiry. A Polymarket strike ladder is a retail CDF of the same quantity priced by a different crowd, with a 7% fee
coefficient that stops takers from closing small gaps. If the two disagree, the professional market is the better
prior; the known bias of risk-neutral tails (variance premium) is a level effect that the slope test tolerates.

**Population (q0202; frozen; no outcome or price used).**
1. Gamma closed events of the two series with `endDate` = `d` 16:00Z (EDT) or 17:00Z (EST) for `d` in the D window,
   walked by one-day `end_date` windows (never by slug, probe 9); paged.
2. Each market: question matches the frozen regex with the asset name, two outcomes, not neg-risk, description contains
   every frozen flag (§1.4), `startDate` ≤ `d − 5` 12:00 ET.
3. Exclusion: market id, event id, `negRiskMarketID`, series-date key (§1.3).

**Polymarket price (causal).** For each market and origin `t`: `p` = YES-terms VWAP of the last transaction with time in
`[t − 30 min, t)` (fresh rule; else unavailable, counted). Units with `p < 0.05` or `p > 0.95` are excluded (a
feature-only cut, counted). `Y` from the guarded Gamma outcome.

**Anchor (frozen now; no fitting to outcomes).**
- Trades: Deribit option trades of the asset with timestamp in `[t − 120 min, t)`; `S` = `index_price` of the last one.
  For each expiry `e` (08:00Z), log-moneyness `m = ln(K_opt / S)`, `τ_e` in years (ACT/365).
- Smile per expiry: weighted least squares of `iv` (decimal) on `m` over trades with `|m| ≤ 0.15`, weights = amount; needs
  ≥ 6 trades with ≥ 2 on each side of `m = 0`; gives `σ_e(m) = a_e + b_e m`. Else ATM fallback: `σ_e` = median `iv` of
  trades with `|m| ≤ 0.05` (≥ 3 trades), `b_e = 0` (flagged). Else expiry unusable.
- Interpolation to `T`: the nearest usable expiries `e1 ≤ T < e2` with both within 3 days of `T`: total variance
  `w(K) = σ_e(m_K)² τ_e` interpolated linearly in time, `b` interpolated linearly; if only one side exists within 3 days,
  flat σ from that expiry. None → unavailable, counted.
- Digital (zero rates, forward = `S`, disclosed): `σ = sqrt(w / τ_T)`, `d1 = (ln(S/K) + σ²τ_T/2)/(σ√τ_T)`, `d2 = d1 −
  σ√τ_T`, **`q = Φ(d2) − (S/K) · φ(d1) · √τ_T · b`** (the digital `−∂C/∂K` of the undiscounted call: the smile-slope
  term is `−S φ(d1) √τ · ∂σ/∂K` with `∂σ/∂K = b/K` at `F = S`), clipped to [0.001, 0.999].
- Basis disclosed: Deribit's index (USD, multi-venue) vs Binance BTC/USDT at 12:00 ET (a few basis points; strike spacing
  is about 1.5-3% of the price); no variance-premium haircut in the primary (the `σ x 0.9` version and the DVOL-flat
  version are reported).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **D1** | forecasting | market-origin with `p`, `q` (Stage 1: D window; Stage 2: post-freeze dates) | OLS slope `β` of `Y − p` on `q − p` (with intercept), unweighted | > 0 |
| **D2** | economic (Stage 2 only) | traded market-origin: on some token `q_tok − a − f(a) ≥ 0.04` and size at `a` ≥ 5 shares (if both, the larger edge) | mean `Y_tok − a − f(a)`, cents per share | > 0 |

**Source check.** On units with `|ln(S_T/K)| > 0.5%` (`S_T` from the guarded settlement index), the index-implied outcome
vs the Gamma outcome: disagreement > 2% of market-dates → D "not testable (source)", counted. Disagreeing units stay in,
with the Gamma outcome (what pays).

**Reported (descriptive).** Log-loss and Brier of `q` and of `p`; calibration of `q` alone; `β` by moneyness tercile,
days to resolution (5 vs 2) and asset; the directional excess `E[(Y − p) · sign(q − p)]` on units with `|q − p| ≥ 0.04`;
the DVOL-flat, flat-smile and `σ x 0.9` variants.

**MDE (assumptions; census replaces).** About 210 resolution dates with ladders in the D window (the series existed by
2025-11; earlier dates have none), 2 assets x 11 strikes x 2 origins = 44 candidate units per date. About 40% survive
freshness and the price band, giving about 3,700 units. All strikes of a ladder settle on one price, so the effective
sample is about 4 units per date (about 850). With `SD(Y − p)` about 0.38 and `SD(q − p)` 0.04-0.06, `SE(β)` is about
0.27-0.40 and **the D1 MDE is about 0.85-1.25** in slope units (one-sided 0.01, 80% power). Stated plainly: D1 can detect
only an anchor that is close to the right price (`β` near 1); a real `β` of 0.3-0.8 reads "not detected at MDE x". The
0.30 floor binds only if the MDE turns out smaller. Stage 2 (56 dates) has an MDE of about 1.5-2 and is a sign-level
replication. **D2** (Stage 2): perhaps 20-30% of about 1,200 Stage-2 units trade; with day clustering the MDE is about
6-9c per share. Both detect only large effects.

**Stage 2 (registered only if D1 advanced).** q0210 at each origin (12:00 ET, receipt-timed): the live ladder frame
(Gamma, frozen rule), CLOB `/book` of both tokens of every strike of the two ladders whose `d − 5` or `d − 2` origin this
is, Deribit option trades of `[t − 120 min, t)` (fetched at `t`, same endpoint as Stage 1), and the live book summary
(variant). `p` for D1-rep = the last Data API transaction in `[t − 30 min, t)` (prints fetched after the origin, filtered
to time < `t`); D2 uses the recorded asks. Definitions, anchor, thresholds and gates identical. A failed origin fetch is
"unavailable (source)", counted, never refilled; > 20% unavailable origins → D1-rep and D2 "not testable (source
unavailable)", counted.

**Leakage.** Deribit trades strictly before `t`; Polymarket transactions strictly before `t` within 30 min; strikes from
the question text; `Y` and the settlement index guarded; no constant is fitted on any Polymarket data; the window avoids
CB8-B's calendar.

**What kills CH89.** GD fails; D1 not detected at MDE or below floor; the sign-flip placebo advances; the spot-staleness
control fails (labelled "latency, not distribution"); the option attribution fails (labelled CH30-type); D1-rep fails out
of time; D2 net ≤ 0 or below floor.

### CB10-B: Round-level break reversals (CH93)

**Question.** After the first print-confirmed crossing in 24 h of a round level, do the transactions of the next 10
minutes revert by 2 h more than after first crossings of nearby pseudo-levels? Does a maker quote one cent beyond the
level, against the break, earn after the reversal?

**Mechanism.** Polymarket has no native stops; copy, alert and "sell if below X" tools default to round prices, and retail
anchors at round numbers. A break of 0.50 then triggers price-driven, uninformed market orders in the break direction,
which revert. Generic post-move reversal (bid-ask bounce, E004/J4, HB1's reversal moderators) applies equally to
pseudo-levels, so **the real-minus-pseudo contrast is the test**.

**Population and sampling (q0204; frozen).** Gamma closed binary markets with scheduled end in `[2026-04-08,
2026-10-01)`, scheduled life overlapping `[2026-04-01, 2026-10-01)` by ≥ 3 days, Gamma volume ≥ $10k (end-of-life
field; a disclosed look-ahead in selection, not outcome), two outcomes; not weather, not crypto Up/Down, not any crypto
strike ladder, not Pyth; key drops (q0201); ≤ 3 markets per event; seeded 1,400 markets (`arepo-cb10-brk-sample`); event
split SCREEN/HOLDOUT before any print read. Sports sampled into a reported stratum (≤ 15%), not in the primary.

**Transactions (q0205).** Newest-first `/trades` pages (`limit` 10,000, `offset` ≤ 10,000), aggregated by transaction
hash at fetch into (time, YES-terms VWAP, size); kept only within the window. A market whose cap is reached before the
window start has its covered span recorded; episodes need their whole `[t_b − 24 h, t_b + 2 h]` inside the covered span.

**Episodes (frozen now).**
- Real levels `R = {0.10, 0.25, 0.50, 0.75, 0.90}`; pseudo-levels `Q = {L − 0.03, L + 0.03 : L ∈ R}` = {0.07, 0.13, 0.22,
  0.28, 0.47, 0.53, 0.72, 0.78, 0.87, 0.93}.
- A **down-break** of level `L` at transaction `j`: previous transaction price `≥ L` and `p_j < L`; an **up-break**:
  previous `≤ L` and `p_j > L`. Direction `s = +1` (down) or `−1` (up).
- Eligible iff: no crossing of `L` in either direction in `[t_j − 24 h, t_j)`; ≥ 3 transactions in `[t_j − 24 h, t_j)`;
  no earlier eligible episode of the same type (real or pseudo) in the same market within 2 h before `t_j`.
- **Mutual exclusion.** A real and a pseudo episode in the same market within 60 minutes of each other are both dropped
  (counted): one move crossing 0.50 and 0.47 is not two independent observations, and keeping either would bias the
  contrast.
- `VWAP10` = size-weighted price of transactions in `(t_b, t_b + 10 min]` (the break transaction itself excluded); none →
  "no follow-through" (counted; reported as the cascade descriptive, not a unit).
- Mark `M2h` = last transaction at or before `t_b + 2 h`, if its time is ≥ `t_b + 90 min`; else unavailable (worst case
  §2.6 (v)).
- **Reversal** `R_e = s · (M2h − VWAP10)`, cents (positive = the price moved back toward the side of the level it broke
  from).

**Maker rule (B2).** At each eligible episode with follow-through: paper quote of 100 shares posted at `t_b + 60 s`, live
until `t_b + 10 min`: down-break → bid at `L − 0.01`; up-break → ask at `L + 0.01` (one cent, a valid price under either
venue tick size, 0.01 or 0.001; Gamma's end-of-life tick field is not used). **Filled only by trade-through:** a
transaction strictly below the bid (strictly above the ask) in the live interval; fill price = the quote; full size.
Mark-out per filled share: bid `M2h − (L − 0.01)`, ask `(L + 0.01) − M2h`.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **B1** | mechanism contrast | eligible episode with `VWAP10` (SCREEN events; Stage 2: HOLDOUT) | mean `R_e` over real-level episodes minus mean over pseudo-level episodes, cents | > 0 |
| **B2** | economic | filled real-level maker episode (SCREEN; Stage 2: HOLDOUT) | mean mark-out per filled share, cents; route gate: mean per posted episode (unfilled = 0, per 100 posted shares) > 0 | > 0 |

**Reported (descriptive).** `R_e` by level and direction; reversal at 30 min; the cascade descriptive (transactions and
volume in the 10 minutes after real vs pseudo breaks); the B2 fill rate; the rebate version; per-level B2.

**MDE (assumptions; census replaces).** About 700 SCREEN markets in about 230 events, about 40 active days each, about 0.1
eligible real-level episodes per market-day after the exclusions: about 2,800 real and about 4,500 pseudo SCREEN episodes.
With `SD(R_e)` about 4c and an event design effect of about 3, the contrast SE is about 0.2c and **the B1 MDE is about
0.6-0.7c** (floor 0.5c). B2: about 25-35% fill under trade-through (about 800 filled episodes), mark-out SD about 5c, **MDE
about 0.9-1.1c** (floor 1.0c). Both are near their floors; a real 0.5c contrast may read "not detected at MDE 0.65c".

**Leakage.** Episode detection uses transactions up to `t_b`; the mark uses later transactions only (a print-based target,
no outcome); levels, pseudo-levels, windows and the maker rule are fixed now and never re-tuned; HOLDOUT sealed. Same
calendar as HB2, CB8 and CB9-K/D (markets disjoint by key): a B result is not out-of-time evidence. Breaks that coincide
with news are in both arms; news-driven real breaks that continue make B1 conservative.

**What kills CH93.** GB or the coverage audit fails; B1 not detected or below floor; the label-swap placebo advances; B2
below floor, route gate fails ("reversal exists but the maker still loses: no route"), or the pseudo attribution fails
(labelled generic); B1-rep / B2-rep fail on HOLDOUT.

### CB10-F: Data jobs

q0200 smoke (PASS needs: Deribit history paging returns the same trade count on two repeat requests for two out-of-window
hours (2026-10-02T10Z, 2026-10-03T16Z) with `iv` and `index_price` on ≥ 99% of rows; the ladder frame walker finds both
series' events for two out-of-window dates with 11 strikes each and every rule flag present; the question regex parses
every strike; the Data API newest-first paging reaches the oldest print of two out-of-window ladder markets; the
transaction aggregation yields one row per hash on a fixture. Any failure → the dependent family "not testable (source)",
counted; no rule is re-fitted). q0201 keys. q0202-q0203 D frame, prints and Deribit data. q0204-q0206 B frame, prints,
seal. q0207 census. q0210 conditional D Stage 2. Every data job writes a manifest (file sha256, request counts, failures,
data-dumps size and margin, free disk).

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` is under `backend/scripts/`, `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check; analysis
jobs also need the CB10 freeze. All `family` = `creative_batch_10`.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0200 | cpu | 35 | ≤ 60 req at ≤ 1 rps, < 5 min, mem 200 | - | rules file + smoke code reviewed (may run before `T_seal`) |
| q0201 | net | 34 | about 300 req, ≤ 0.005 GB | q0182, q0183, q0185 | after `T_seal` and q0200 PASS |
| q0202 | net | 33 | about 4,850 req, mem 400, ≤ 0.01 GB | q0201 | with q0201 |
| q0203 | net | 33 | about 1,020 req, mem 400, ≤ 0.02 GB | q0202 | with q0202 |
| q0204 | net | 33 | about 1,000 req, ≤ 0.005 GB | q0201 | with q0201 |
| q0205 | net | 32 | about 2,000 req, mem 600, ≤ 0.06 GB | q0204 | with q0204 |
| q0206 | cpu | 32 | light | q0205 | with q0205 |
| q0207 | cpu | 31 | ≤ 0.8 GB | q0202, q0203, q0206 | after the seal copy is committed |
| q0208-q0209 | cpu | 30 | ≤ 0.8 GB | q0207 | after the CB10 freeze |
| q0210 | cpu | 35 | about 110 req/day at ≤ 1 rps, rolling | q0208 | only if D1 advanced |
| q0211 | cpu | 30 | ≤ 0.5 GB | q0210 | after `T10_D2_end` + 2 d |
| q0212 | cpu | 30 | ≤ 0.8 GB | q0209 | only if B1 or B2 advanced |

```json
{"id": "q0200_cb10_smoke", "title": "CB10: smoke (Deribit history paging + iv/index_price presence on 2 out-of-window hours; ladder frame walker, rule flags and strike regex on 2 out-of-window dates; Data API newest-first paging to the oldest print on 2 out-of-window ladder markets; transaction aggregation fixture); counts only", "family": "creative_batch_10", "priority": 35, "expected_value": "go/no-go for every CB10 source", "data": ["Deribit public history", "public Gamma, Data API"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "cpu", "network": "history.deribit.com, gamma-api, data-api"}, "depends_on": [], "argv": ["scripts/run_cb10.py", "smoke", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch10/smoke.json", "trials.jsonl (cb10_descriptive)"], "next_action": "PASS: q0201 after T_seal; FAIL: dependent family not testable (source), counted", "notes": "CREATIVE_BATCH_10.md CB10-F. DRAFT. May run before T_seal (cpu lane, <= 60 requests). Prints counts only."}
{"id": "q0201_cb10_exclusion_keys", "title": "CB10: exclusion keys = CB9 q0182 keys + CB9 P and K/D frame ids + seal copies committed since q0182; series-date keys for the two ladder series", "family": "creative_batch_10", "priority": 34, "expected_value": "disjointness of D and B", "data": ["creative_batch9/exclusion_keys.csv.gz", "creative_batch9 frame id lists", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0182_cb9_exclusion_keys", "q0183_cb9_pyth_frame", "q0185_cb9_kd_frame"], "argv": ["scripts/run_cb10.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "14"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch10/exclusion_keys.csv.gz", "manifest.json"], "next_action": "q0202, q0204", "notes": "DRAFT. After T_seal. >2% missing metadata -> disjointness unverified (D1, B1, B2 not testable, counted). Exit 75 on data-dumps or free-disk headroom."}
{"id": "q0202_cb10_dlad_frame", "title": "CB10-D: Gamma frame of BTC/ETH daily 'above $K on date' ladders (resolution dates [2025-10-01,2026-04-13) U [2026-08-11,2026-10-01)), rule flags, series-date exclusion; Data API newest-first prints -> per-origin last transaction in [t-30min,t) and counts; outcomes to the guarded file", "family": "creative_batch_10", "priority": 33, "expected_value": "D population and Polymarket prices at origins", "data": ["public Gamma, Data API", "creative_batch10/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, data-api"}, "depends_on": ["q0201_cb10_exclusion_keys"], "argv": ["scripts/run_cb10.py", "dlad-frame", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "14", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h10_dlad/{frame.csv.gz,origins.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0203", "notes": "DRAFT. No print stored beyond origin rows; no side or wallet read.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"dlad_frame_complete\""}}
{"id": "q0203_cb10_deribit_trades", "title": "CB10-D: Deribit option trades [t-120min, t) per origin time and currency (timestamp, instrument, iv, index_price, amount); BTC/ETH-PERPETUAL hourly bars [t-7d, t); settlement index at each resolution minute to the guarded file", "family": "creative_batch_10", "priority": 33, "expected_value": "D anchor and attribution inputs", "data": ["history.deribit.com public (keyless)", "www.deribit.com public chart data"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "history.deribit.com, www.deribit.com"}, "depends_on": ["q0202_cb10_dlad_frame"], "argv": ["scripts/run_cb10.py", "deribit-trades", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "14"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h10_dlad/deribit/{trades.csv.gz,perp_bars.csv.gz,settle_index_guarded.csv.gz,manifest.json}"], "next_action": "q0207", "notes": "DRAFT. Origin times from q0202's frame only; no Polymarket field read."}
{"id": "q0204_cb10_brk_frame", "title": "CB10-B: Gamma frame (closed binary, scheduled end [2026-04-08,2026-10-01), life overlap >= 3 d, volume >= $10k, not weather/crypto Up-Down/crypto ladders/Pyth), key drops, <= 3 per event, seeded 1,400 markets, event split SCREEN/HOLDOUT (arepo-cb10-brk-split)", "family": "creative_batch_10", "priority": 33, "expected_value": "B population and split", "data": ["public Gamma", "creative_batch10/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0201_cb10_exclusion_keys"], "argv": ["scripts/run_cb10.py", "brk-frame", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "14"], "timeout_s": 3000, "max_retries": 2, "outputs": ["history/h10_brk/{frame.csv.gz,split.json,manifest.json}"], "next_action": "q0205", "notes": "DRAFT. Split written before any print read. Sports stratum <= 15%, reported, not primary."}
{"id": "q0205_cb10_brk_prints", "title": "CB10-B: newest-first Data API prints per market (limit 10000, offset <= 10000), aggregated by transaction hash at fetch to (time, YES-terms VWAP, size), window [2026-04-01,2026-10-01); covered span recorded; HOLDOUT written to holdout/", "family": "creative_batch_10", "priority": 32, "expected_value": "B1/B2 inputs", "data": ["public Data API"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "net", "network": "data-api"}, "depends_on": ["q0204_cb10_brk_frame"], "argv": ["scripts/run_cb10.py", "brk-prints", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.06", "--data-dumps-cap-gb", "14", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h10_brk/{screen,holdout}/tx.csv.gz", "manifest.json"], "next_action": "q0206", "notes": "DRAFT. No side, wallet or hash stored. One market in memory at a time.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"brk_prints_complete\""}}
{"id": "q0206_cb10_brk_seal", "title": "CB10-B: HOLDOUT listing sha256, seal-time drops vs seal copies committed by now (incl. CB9 h10_sign if present), seal copy seals/cb10_brk_holdout_SEAL.json", "family": "creative_batch_10", "priority": 32, "expected_value": "sealed holdout", "data": ["history/h10_brk/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api (light)"}, "depends_on": ["q0205_cb10_brk_prints"], "argv": ["scripts/run_cb10.py", "brk-seal", "--rps", "2"], "timeout_s": 1800, "max_retries": 2, "outputs": ["history/h10_brk/holdout_SEAL.json"], "next_action": "commit the seal copy; q0207", "notes": "DRAFT. Sealed files never edited; drops recorded as DROPPED_* blocks."}
{"id": "q0207_cb10_census", "title": "CB10: pre-freeze census, counts only (GD, GB, GB2, B coverage audit, feature-only gap and q/q_RV correlation counts, MDEs)", "family": "creative_batch_10", "priority": 31, "expected_value": "gates and MDEs before the freeze", "data": ["history/h10_dlad (no guarded file)", "history/h10_brk/screen (HOLDOUT file and event counts only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0202_cb10_dlad_frame", "q0203_cb10_deribit_trades", "q0206_cb10_brk_seal"], "argv": ["scripts/run_cb10.py", "census"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/census.json", "trials.jsonl (cb10_descriptive)"], "next_action": "science-reviewer freeze check, then model_specs/cb10_v1.json", "notes": "DRAFT. Outcome guard; no slope, net, reversal or contrast computed."}
{"id": "q0208_cb10_screen_D", "title": "CB10-D: D1 Stage 1 with sign-flip placebo, option attribution, spot-staleness control and binding robustness", "family": "creative_batch_10", "priority": 30, "expected_value": "D verdict", "data": ["history/h10_dlad (guarded files opened here only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0207_cb10_census"], "argv": ["scripts/run_cb10.py", "screen", "--family", "D"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/results_D.json", "trials.jsonl (cb10_test + creative_batch_10:D)"], "next_action": "advanced: commit q0210", "notes": "DRAFT. Refuses before the CB10 freeze hash."}
{"id": "q0209_cb10_screen_B", "title": "CB10-B: B1 and B2 Stage 1 on SCREEN events with label-swap placebo, pseudo attribution and binding robustness", "family": "creative_batch_10", "priority": 30, "expected_value": "B verdicts", "data": ["history/h10_brk/screen/"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0207_cb10_census"], "argv": ["scripts/run_cb10.py", "screen", "--family", "B"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/results_B.json", "trials.jsonl (cb10_test + creative_batch_10:B)"], "next_action": "advanced: commit q0212", "notes": "DRAFT. Refuses to open holdout/."}
{"id": "q0210_cb10_dlad_live", "title": "CB10-D Stage 2: 56 post-freeze resolution dates; at each 12:00 ET origin (receipt-timed) the ladder frame, CLOB /book of both tokens of every strike, Deribit trades [t-120min,t), Deribit live book summary (variant); prints fetched after each origin", "family": "creative_batch_10", "priority": 35, "expected_value": "out-of-time D replication and D2 economic data", "data": ["public Gamma, CLOB /book, Data API", "Deribit public"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, data-api, deribit"}, "depends_on": ["q0208_cb10_screen_D"], "argv": ["scripts/run_cb10.py", "dlad-live", "--dates", "56", "--rps", "1", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "14"], "timeout_s": 3000, "max_retries": 3, "outputs": ["research_lab/creative_batch10/dlad_live/<origin_date>/..."], "next_action": "q0211 after T10_D2_end + 2 d", "notes": "DRAFT. Only if D1 advanced. Origins in ET (EST from 2026-11-01). Failed origins unavailable (source), never refilled; > 20% unavailable -> D1-rep and D2 not testable (source unavailable). Logs any concurrent net-lane job."}
{"id": "q0211_cb10_rep_D", "title": "CB10-D: D1-rep (slope) and D2 (economic at recorded asks) on post-freeze resolution dates", "family": "creative_batch_10", "priority": 30, "expected_value": "L2 verdicts", "data": ["research_lab/creative_batch10/dlad_live/"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0210_cb10_dlad_live"], "argv": ["scripts/run_cb10.py", "rep", "--family", "D"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/results_D_rep.json", "trials.jsonl (cb10_replication)"], "next_action": "pass: Stage P-D registration draft", "notes": "DRAFT."}
{"id": "q0212_cb10_rep_B", "title": "CB10-B: B1-rep and/or B2-rep on sealed HOLDOUT events", "family": "creative_batch_10", "priority": 30, "expected_value": "L2 verdicts", "data": ["history/h10_brk/holdout/"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0209_cb10_screen_B"], "argv": ["scripts/run_cb10.py", "rep", "--family", "B"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/results_B_rep.json", "trials.jsonl (cb10_replication)"], "next_action": "pass: Stage P-B draft", "notes": "DRAFT. Only for advanced tests; verifies the seal hash first."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb10_dlad.py`: ladder frame walker (one-day `end_date` windows, both series), question
  regex and rule flags, series-date exclusion, origin clock in ET, freshness rule, Deribit history client (paging by
  `has_more`, ≤ 2 rps), smile fit and ATM fallback, total-variance interpolation, the digital with the smile-slope term,
  `q_RV`, `q'`, D1 and D2 statistics, guarded-file access.
- `backend/astrolabe/research_lab/cb10_brk.py`: frame and split, newest-first print pager with local window filter and
  covered-span record, transaction aggregation (YES terms, hash discarded), episode detector (real and pseudo levels,
  24 h first-crossing, 2 h same-type spacing, 60-minute mutual exclusion), `VWAP10`, `M2h`, trade-through maker, B1/B2.
- Reuse: `cb9_common` (refused roots, disk and free-disk guards, exit 75, manifests, cluster bootstrap and small-G rule)
  where its interface fits; `history_backfill.Limiter` and `live_pass_or_lock()`.
- `backend/scripts/run_cb10.py` with subcommands as §4; refuses analysis before the freeze hash and `net` work before
  `T_seal`.
- Tests (`test_cb10_dlad.py`, `test_cb10_brk.py`, `test_run_cb10.py`): the digital against a numerical call-spread
  derivative on a synthetic linear smile (tolerance 1e-4); interpolation at and between expiries; the ATM fallback and
  the 3-day rule; ET origin clock across 2026-11-01; freshness boundaries (`t − 30 min` inclusive, `t` exclusive); the
  series-date rule (±1 day); transaction aggregation with outcome-1 prints; episode detection on synthetic paths (first
  crossing, 24 h memory, mutual exclusion, equality at the level is not a crossing); trade-through fills (a print at the
  quote does not fill); no census path receives `Y`, the settlement index, `M2h` or a fill P&L; holdout refusal; guarded
  files opened only by screen/rep jobs; `battery2` kinds; batch-Holm k1 = 3 fixed.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: D1, B1, B2 | 3 | `cb10_test` + `:D`, `:B` (2) | p < 0.01 each; batch-Holm label (α 0.01, k1 = 3 fixed); BY triage |
| Stage 2: D1-rep, D2 (if D1 advanced) | ≤ 2 | `cb10_replication` | one Holm over CB10 Stage 2, one-sided α 0.05 |
| Stage 2: B1-rep, B2-rep (each if its Stage 1 advanced) | ≤ 2 | `cb10_replication` | as above |
| Census, gates, descriptives, variants, cascade descriptive | 0 | `cb10_descriptive` | - |
| **Total** | **3 fixed + ≤ 4 conditional = 3-7** | | cumulative ≥ 1,141 at drafting → ≥ 1,144-1,148 plus CB6-CB9 |

**Host compute.** Under 2 CPU-hours at nice 19; peak RAM 0.8 GB. **Network.** Before `T_seal`: ≤ 60 requests (q0200,
`cpu` lane). After: about 9,200 requests on the `net` lane (about 5,000 Data API, about 2,700 Gamma, about 1,050 Deribit;
no pmxt). Conditional Stage 2: about 110 requests a day for about 60 days on the `cpu` lane at ≤ 1 rps. **Disk.** ≤ 0.12 GB
in total, no job above 0.06 GB.

**Earliest dates (estimates, not commitments).** q0200: after its code and rules file, about 2026-10-19/20 (`cpu` lane,
before `T_seal`). q0201-q0206: after `T_seal` and CB9's q0182/q0183/q0185; realistically 2026-10-23 to 10-27, behind the
CB6-CB9 `net` queue. Census and freeze about 10-28; Stage 1 results about 10-29. D Stage 2 (if triggered): first
resolution date about 11-04, `T10_D2_end` about 12-30, q0211 about 2027-01-01. B Stage 2 (if triggered): days after
Stage 1.

## 7. Main scientific risks

1. **D1 power is low.** All strikes of one ladder settle on one price, so about 210 dates carry the information; the MDE
   (about 0.85-1.25 in slope) means D1 detects only an anchor close to the right price. A null is "not detected", not
   "options carry no information".
2. **Trade-time IVs are a noisy smile.** Two hours of trades (about 700 BTC, fewer ETH) spread over a dozen expiries give a
   few points per near expiry; the linear smile and the ATM fallback are crude, and weekend hours are thin. The smile-slope
   term can be unstable when `b` is poorly fitted. Both are frozen, and the flat-smile variant is reported.
3. **Spot latency masquerading as option information.** Any digital uses spot now. The spot-staleness control and the
   option attribution placebo are the guards; a failure of either is labelled, and only "option-implied information"
   with both passed would be CH89's claim.
4. **Series-date exclusion is a declared deviation** from the series-key rule (§1.3). If the challenger rejects it, D's
   population may collapse to "not testable (exclusions)", counted.
5. **B's breaks are partly mechanical.** The bid-ask bounce and post-move reversal appear in both arms; the contrast
   removes them only if pseudo-level breaks are comparable moves. The 60-minute mutual exclusion removes moves that cross
   both, which favours smaller moves in both arms (disclosed). Real levels are also where resting depth sits (CH20), so a
   "reversal" may be depth absorbing the cascade rather than a fade opportunity; B2 tests the money route directly.
6. **B2 fill realism.** Trade-through fills are conservative on count but adverse in selection (fills only on deeper
   moves); queue position is unknown. Full 100-share fills are assumed on a trade-through print of any size (disclosed;
   the size-weighted check (iii) is the guard).
7. **Truncated histories.** The Data API reaches only the newest 20,000 prints; the busiest markets lose early history. The
   coverage audit (≥ 80%) and the covered-span rule keep truncation from becoming "no break".
8. **Same calendar.** B shares April-September 2026 with HB2, CB8 and CB9-K/D (markets disjoint by key); B-rep on HOLDOUT
   is same-calendar (L2), not out-of-time.
9. **Queue and disk.** CB10 sits behind CB6-CB9 in the `net` lane, and data-dumps is near its cap (13.1 GiB, about +1.1
   GB/day). CB10's total output is small (≤ 0.12 GB), but jobs may wait on exit 75 until archive rotation frees space; no
   rule changes because of waiting.

## 8. Next actions

1. **Challenger review round 1** (`science-reviewer`): one challenge, one response, then the code-against-design freeze
   check. Items flagged for the reviewer: the series-date exclusion (§1.3), the smile-slope digital and IV-fit rules
   (§CB10-D), the 60-minute mutual exclusion and pseudo-level choice (§CB10-B), D1's power (§7 risk 1).
2. Write `seals/cb10_rules.json`, `cb10_dlad.py`, `cb10_brk.py`, `run_cb10.py` and tests; freeze check; commit q0200
   (`cpu` lane, may run before `T_seal`), then q0201-q0206 after `T_seal` and CB9's q0182/q0183/q0185.
3. Census q0207 → freeze `model_specs/cb10_v1.json` → q0208/q0209 → conditional jobs by the stated triggers.
4. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.
