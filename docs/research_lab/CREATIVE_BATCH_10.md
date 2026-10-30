# Creative batch 10 (CB10): option-implied anchor for crypto strike ladders, round-level break reversals

`evidence_role: exploratory_historical` (CB10-D Stage 1 on a fresh crypto-ladder fetch; CB10-B Stage 1 on a fresh print
fetch, SCREEN events) / `prospective` (CB10-D Stage 2, post-freeze resolution dates) | status: **DRAFT-REVISED after challenger round 1; not
frozen; next: code, then the code-against-design freeze check.** Drafted 2026-10-17 15:48 UTC+1 (2026-10-17T14:48Z) by
the CB10 design pass (`19ae522`); round-1 response 2026-10-17 16:01 UTC+1 (§9-§10). Every round-1 change tightens or
discloses; no floor, threshold, gate, alpha or cap was relaxed. One reviewer suggestion changes the D calendar (D now
spans CB8-B's weeks, with the written argument in §1.3). Nothing has been fetched for CB10 beyond the 33 counts-only
feasibility requests in §0.3. No CB10 quantity has been computed.

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
- **Disk waits are "pending" (round 1 item 14).** The host data-dumps is near its cap. Every post-`T_seal` CB10 data job
  may exit 75 repeatedly until archive rotation frees space. A job waiting on exit 75 is **"pending"**, never "not run"
  and never a test outcome; no date, window or rule moves because of the wait. Every date in §6 is conditional on
  rotation. (Stage-2 origins are time-critical and are the one exception: a missed origin is "unavailable (host disk)",
  counted, §CB10-D Stage 2.)
- **Queue ids q0200-q0219, one id per job, no letter suffixes** (checked free in `queue/jobs/` and `queue/drafts/` at
  drafting). Specs are drafts **in this document only** (§4). Nothing is created under `queue/` until code, tests and the
  freeze check exist.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB10-D** option-implied anchor for crypto strike ladders (CH89) | in BTC and ETH daily "above $K on date" ladders, a frozen smile-adjusted digital probability read from Deribit option trades in the 2 h before the origin predicts the resolution excess `Y − p` beyond the Polymarket price, with the regressor's price `p_reg` taken from an earlier, separate transaction (D1, slope > 0; run only if the census power gate passes, §2.7); prospectively, buying the side the anchor favours by ≥ 4c after fees at the recorded ask pays (D2) | D1 (forecasting, fixed); D1-rep, D2 (conditional on D1) | fresh ladder frame + Data API prints + Deribit history, resolution dates `[2025-10-01, 2026-10-01)` (round 1: CB8-B's weeks included, §1.3) | post-freeze resolution dates (56), CLOB books at origins | q0201-q0203, q0207, q0208, q0210, q0211 |
| 2 | **CB10-B** round-level break reversals (CH93) | after a print-confirmed first crossing in 24 h of 0.10/0.25/0.50/0.75/0.90, transactions in the next 10 min revert by 2 h more than after first crossings of their own pseudo-levels `L ± 0.03` (B1, per-pair contrast); a paper maker one cent beyond the level against the break, filled only by trade-through, earns > 0 net per filled share at the 2 h mark after a declared exit cost (B2, economic) | B1, B2 (fixed); B1-rep, B2-rep (conditional) | fresh print fetch `h10_brk`, SCREEN events, prints `[2026-04-01, 2026-10-01)` | the same fetch, sealed HOLDOUT events | q0201, q0204-q0207, q0209, q0212 |
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
| q0210 | `cb10_dlad_live` (D Stage 2 prospective collection by per-origin cron runs outside the queue lanes, round 1: ladder frame, CLOB books and Deribit trades at origins; 56 resolution dates) | D | only if D1 advanced; first origin ≥ freeze + 1 day |
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
  before every counting CB10 job and records the post-union value). **Round 1: 1,146** at 2026-10-17T15:01Z (same
  working tree; the reviewer's figure); this is the count used in §2.5.
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

#### 0.3.1 Probe requests as sent (round 1 should-change: the reviewer could not see `/tmp`)

All GETs carried `User-Agent: arepo-research-probe`, 30-60 s timeouts, no key. `ms(x)` is Unix milliseconds of the UTC
instant `x`; `ts(x)` Unix seconds. Each script printed only status, row counts, field names and the text flags shown.

| # | Exact request (host + path + query) | Printed |
|---|---|---|
| 1 | `www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&start_timestamp=ms(2026-08-11)&end_timestamp=ms(2026-08-13)&resolution=3600`; same for 2026-05-01..05-03 | status, `len(result.data)`, columns, `continuation` key present |
| 2-3 | `history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time?currency=BTC&kind=option&start_timestamp=ms(T)&end_timestamp=ms(T)+3600000&count=1000` for T = 2026-09-01T10:00Z and 2026-05-01T10:00Z; `currency=ETH`, window 2026-01-15T15:00-16:00Z | status, `len(trades)`, `has_more`, sorted field names; ETH: expiry token counts from `instrument_name`, count of rows with `iv` not null |
| 4 | `www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option` | status, instrument count, KB, field names |
| 5 | `www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name=BTC-PERPETUAL&start_timestamp=ms(2026-01-05)&end_timestamp=ms(2026-04-13)&resolution=60` | status, `len(ticks)` |
| 6 | `gamma-api.polymarket.com/public-search?q=Bitcoin%20above%20on&events_status=closed&limit_per_type=20` | per event: slug, market count, `negRisk`, `endDate`, series slug |
| 7 | `gamma-api.polymarket.com/events?slug=bitcoin-above-on-august-20-2026` | start/end, market count; booleans for "Binance", "BTC/USDT", "12:00", "1 minute", "close" in the first market's description; `resolutionSource`, `feeSchedule`, `orderMinSize`, `orderPriceMinTickSize`, the first question text |
| 8 | `gamma-api.polymarket.com/series?slug=` `btc-multi-strikes-weekly`, `eth-multi-strikes-weekly`, `ethereum-multi-strikes-weekly` | status, `len(events)` |
| 9 | `gamma-api.polymarket.com/events?slug=` `bitcoin-above-on-january-15-2026`, `bitcoin-above-on-november-14`, `ethereum-above-on-august-20-2026` | found / not found, market count, start, end, series slugs |
| 10 | `data-api.polymarket.com/trades?market=<cid of strike 6 of the 2026-08-20 BTC ladder>&limit=500&takerOnly=true`; the same with `start=ts(2026-08-15T15:00Z)&end=ts(2026-08-15T16:00Z)`; the same with `offset=3500` | row count; span in days (max − min timestamp); rows inside the window; row count at offset 3500 |
| 11 | `combos-rfq-api.polymarket.com/v1/rfq/combo-markets` (6 pages by `cursor`), `?limit=3`, `?limit=1`; `gamma-api.polymarket.com/markets?clob_token_ids=<position_ids[0]>` and `?condition_ids=<condition_id>`; `docs.polymarket.com/api-spec/combos-rfq-openapi.yaml` | page count, bytes, item keys, `len(position_ids)` distribution, tag counts, `pending` counts, distinct position ids; one item's title, slug, outcomes; Gamma hit counts; token-set equality (false); OpenAPI path and tag descriptions |
| 12 | `gamma-api.polymarket.com/markets?closed=true&limit=100&end_date_min=2026-09-01&end_date_max=2026-09-03&volume_num_min=10000`; same for 09-15..09-17 | counts of regex classes on `description` (report: `consensus of credible reporting` or `credible report`; official: `\bofficial\b` or `as published by` or `according to (the )?[A-Z]`, case-insensitive), after dropping crypto-like and sports-like questions |

**Deribit expiries at `d − 5` (round 1 question).** The probes show dailies 1 and 4 days ahead and Friday weeklies on
2026-01-15 (probe 3); they did not measure how far ahead dailies are listed. Every resolution weekday except **Monday**
lies within 3 days of a Friday 08:00Z weekly (Monday 12:00 ET is 3 d 8 h after the prior Friday and 4 d 16 h before the
next), so at `d − 5` a Monday resolution has an anchor only if a daily within 3 days was already listed and traded in the
2-h window. Unverified; the smoke and the census count IV-fit availability by origin and resolution weekday (§2.7), and
Monday units without an expiry are "unavailable (source: Deribit)" under the §2.7 coverage audit, never refilled.

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH89** Deribit anchor for crypto strike ladders | **include (D), priority** | CB9 dropped it because Deribit's keyless chart history covers only recently expired options. Probes 2-3 overturn that: the history endpoint serves **every option trade with its `iv` and `index_price`**, keyless, back to at least January 2026, so a strike-specific implied-vol anchor can be built at any past origin. The ladder population is large and regular (2 assets x 11 strikes a day, listed 7 days ahead). Round 1: the calendar includes CB8-B's weeks, with a written argument that D reads none of CB8-B's sealed objects (§1.3). CH30 (Black-Scholes on spot) was never tested; D's attribution placebo separates the option information from the spot-plus-realised-vol part (§2.6) |
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
| `history/h10_dlad` (**new**, q0202): Gamma frame of BTC and ETH daily "above $K on date" ladders (series `btc-multi-strikes-weekly`, `ethereum-multi-strikes-weekly`), resolution dates in the D window; per-origin print rows (the transaction setting `p`, the separate earlier transaction setting `p_reg`, the last transaction before `t` of any age, transaction counts in `[t − 6 h, t)`, the covered span of the newest-first pages); outcomes only in `outcomes_guarded.csv.gz` | none (CB2-L excluded strike ladders; CB5-L's families are timing questions; CB8-B is Up/Down) | D1 Stage 1 | L1 |
| `history/h10_dlad/deribit/` (**new**, q0203): Deribit option trades in `[t − 120 min, t)` for each origin time and currency (fields: timestamp, instrument, `iv`, `index_price`, amount, and the presence flags of `block_trade_id`, `combo_id`/`combo_trade_id` and `liquidation`); BTC/ETH-PERPETUAL hourly bars over `[t − 7 d, t)`; the Deribit index at each resolution minute in `settle_index_guarded.csv.gz` | none | D anchor, attribution placebo, source check | - |
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
| D window (Stage 1) | resolution dates `d ∈ [2025-10-01, 2026-10-01)` | **round 1 (reviewer suggestion, adopted):** the draft's gap `[2026-04-13, 2026-08-11)` is removed, with the written argument in §1.3. This also removes item 2's calendar breach (the draft's `d − 5` origins, Deribit windows and 7-day perpetual bars for `d` in 08-11..08-22 reached into the gap). Every D read now lies in `[d − 12 d, d 12:00 ET]` with `d < 2026-10-01`, so in `[2025-09-19, 2026-10-01)`. Dates before the series' first event have no units (census counts) |
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
  not a gate). The census also reports the drops the **full series-key rule** would have made, beside the ±1-day rule
  (round 1 suggestion), so the reviewer can see the deviation's size before the freeze.
- **CB8-B (round 1: D spans CB8-B's weeks; written argument).** CB8-B seals, for its HOLDOUT weeks, the **daily
  crypto Up/Down markets' pmxt book states, their prints and its Binance 1-minute kline features**
  (`creative_batch8/` holdout files, seal copy). D reads none of them: no Up/Down market (the D frame regex admits only
  "above $K on date" questions, and q0201's keys drop any CB8 frame market), no Binance data, no pmxt file. D's units are
  different markets (strike ladders), at a different horizon (2-5 days, not the last 5 minutes), with a different anchor
  (Deribit option trades). Nothing D computes can reveal or condition a CB8-B HOLDOUT statistic, and CB8-B's rules are
  fixed in its committed rules file. The residual link is the shared BTC/ETH price path: a D1 result and a CB8-B result
  in the same weeks are **not independent evidence** about crypto markets (disclosed; the CB9 precedent for "other
  condition ids in the same public source" applies). Why adopt: the gap removed about 120 of about 330 resolution dates
  and about a quarter of the ISO weeks, which by itself put D1's MDE above the §2.7 power gate (about 20% larger MDE).
  B still excludes crypto Up/Down and every crypto strike ladder.
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
- **Gamma field whitelist (round 1 item 6).** Closed Gamma markets carry end-of-life and post-resolution fields
  (`lastTradePrice`, `bestBid`, `bestAsk`, `spread`, `oneDayPriceChange` and siblings, `umaResolutionStatus(es)`,
  `closedTime`, `outcomePrices`, `volume*`, `liquidity*`). The q0202 and q0204 parsers keep **only** these keys, dropped at
  parse before anything is written or logged:
  - **D (q0202):** `id`, `conditionId`, `question`, `slug`, `clobTokenIds`, `outcomes` (labels), `startDate`, `endDate`,
    `negRisk`, `negRiskMarketID`, event ids, series ids and slugs, `resolutionSource`, `feeSchedule`, `orderMinSize`, and
    the description's sha256 and frozen flag booleans (the text itself is not stored). `outcomePrices` is routed, by a
    separate accessor, only to `outcomes_guarded.csv.gz`.
  - **B (q0204):** the same keys, with `feeSchedule` used for B2's exit fee, and a boolean
    `vol_ok` computed in memory from `volumeNum ≥ 10,000` (the number is not stored); **no outcome field at all** (B has
    no outcome).
  - A unit test feeds a fixture market carrying every forbidden field and asserts that the parsed row, the written file
    and the log contain none of them (and that `outcomePrices` reaches only the guarded file in D).
- **Deribit units (round 1 item 15).** Deribit's `iv` is in **percent**; the smile fit uses `iv / 100`. Moneyness uses
  **each trade's own `index_price`**: `m = ln(K_opt / index_price_trade)`; the strike's moneyness at the origin uses `S`
  (§CB10-D). The smoke fails if fewer than 99% of trade rows have `1 ≤ iv ≤ 400` (percent) or `index_price > 0`.

## 2. Common rules (deltas from CB9 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| D1 | none (forecasting test against the last transaction price) |
| D2 | buy the anchor-favoured token at the **recorded** CLOB best ask `a` at the origin; taker fee `f(a) = r·a·(1 − a)`, `r = max(Gamma feeSchedule.rate at frame time, 0.07)` (crypto, probe 7); held to resolution; no rebate |
| B1 | none (mechanism contrast on transaction prices) |
| B2 | resting maker entry, fee 0; **no rebate** in the primary (the rebate version, `0.2 · r · p(1 − p)` per filled share at the recorded rate, is reported). **Exit cost (round 1 item 11):** the position is closed as a taker at the 2 h mark, so each filled share pays `c_exit = r_B · M2h · (1 − M2h) + 0.015`: the taker fee at the mark, with `r_B` = the market's `feeSchedule.rate` at frame time (0.05 if the field is absent, the highest non-crypto docs rate; conservative), plus a fixed half-spread of 1.5c (about half the round-4 median spread across price bands, 2.2-4.1c). Hold-to-resolution is not used (B has no outcome guard by design) |
| Binding cost robustness | D2: +0.5c on `a`. B2: half-spread 2.0c instead of 1.5c keeps net > 0; the latency rule (§2.6 (vi)) and the trade-through fill rule (already primary) |

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
met). Cluster ways: **D** resolution date (BTC and ETH of the same date in one cluster), asset x resolution date, and
**ISO week of the resolution date** (round 1 item 3; adjacent dates share most of the price path and the crowd's
regime). **B** Gamma event and UTC day of the break.
- **Small-G rule for the D week way (round 1 item 3).** Stage 1 has about 45-52 ISO weeks with ladders after the round-1
  calendar change (about 30 had the gap stayed): G ≥ 30 → CR1; 15 ≤ G < 30 → CR2 with t(G − 1) and Webb wild bootstrap
  (9,999 draws); G < 15 → the week way leaves the max and the leave-one-week-out sign rule binds (A-C1 analogue). Stage 2
  (56 dates, 8-9 weeks) is always in the last case: D1-rep and D2 use the date and asset-date ways, and every
  leave-one-week-out estimate must keep the sign.

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
| D1 | forecasting | slope `β̂ ≥ 0.30` of `Y − p` on `q − p_reg` (round 1 item 1) |
| D2 | economic | net ≥ +1.0c per share after fee |
| B1 | mechanism contrast | weighted per-pair contrast (real `L` minus its own `L ± 0.03`, round 1 item 7) ≥ +0.5c |
| B2 | economic | net ≥ +1.0c per filled share at the 2 h mark **after the exit cost** (§2.1, round 1 item 11); route gate: net per eligible episode (per 100 intended shares; not-posted and unfilled = 0, round 1 item 9) > 0 |

### 2.5 Counting (M3 rule)

- Kinds `cb10_test` (Stage 1), `cb10_replication` (Stage 2, including D2), `cb10_descriptive` (EXCLUDE: census, gates,
  strata, the DVOL and flat-smile variants, the cascade-intensity descriptive, every reported variant); placebo lines
  count 0. Count lines `creative_batch_10:D`, `:B` (`n_tests`). New `battery2.KIND_RULES` entries as CB9 §2.5; unknown
  kinds raise.
- **Cumulative count: 1,146** at the round-1 response (§0.2; 1,141 at drafting; lower bound).
- **CB10 adds 3 fixed tests (D1, B1, B2) and up to 4 conditional ones (D1-rep and D2, triggered by a D1 advance; B1-rep,
  B2-rep, each triggered by its own Stage-1 advance).** Budget: 3-7.
- Tests behind a failed or unknown gate (smoke, disjointness, GD, the D power gate GDP, GB, GB2, source check, coverage
  audits) are "not testable" or "not run" (p = 1) and are **still counted**. A job waiting on exit 75 is "pending" and
  produces no line (§0 header). Conditional tests count only if their trigger fires; a
  triggered test that cannot run is counted with p = 1.

### 2.6 Placebos and robustness

Design rule as CB9 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 10101-10106.

- **D1 shared-noise design (round 1 item 1, in the statistic, not a placebo).** If the same transaction price `p`
  appeared in both `Y − p` and `q − p`, its noise `e` (bounce, small-print error) would bias the slope upward by about
  `var(e)/var(q − p)` (the reviewer's estimate 0.03-0.14), which no sign-flip catches. D1's regressor therefore uses
  `p_reg`, the price of an **earlier, separate transaction** (§CB10-D), and the target keeps `p`. Bid-ask bounce makes the
  noise of consecutive transactions negatively correlated, so any residual bias is downward (conservative; disclosed).
- **D1 independent-price placebo (binding, round 1 item 1, belt and braces).** `q` is replaced by `p_alt`, the price of a
  third Polymarket transaction (the last one in `[t − 180 min, t_reg − 5 min)`, distinct from both). Under the
  alternative "the slope is a microstructure artefact of comparing Polymarket prices", `p_alt − p_reg` would "predict"
  `Y − p`. Binding: D1 credits the anchor only if the `p_alt` slope fails the p threshold **and** `β̂(q) − β̂(p_alt) ≥
  0.30` (the D1 floor, applied to the difference). Units lacking `p_alt` are dropped from this placebo only (counted).
- **D1 gap sign-flip calibration (binding).** The sign of `q − p_reg` is flipped by one coin per ISO week (shared by
  every unit of that week; the date-way version uses one coin per date). *Alternative guarded:* a few hundred strongly
  dependent dates in about 50 weeks make the clustered p anti-conservative.
- **D1 option attribution (binding for crediting "option-implied information").** `q_RV`: the same digital with σ =
  the 7-day realised volatility of the perpetual's hourly log returns over `[t − 7 d, t)` (annualised, flat smile, same
  `S`). Joint OLS of `Y − p` on `(q − p_reg)` and `(q_RV − p_reg)`, same clusters. Credit "option-implied anchor" only if
  the joint coefficient on `(q − p_reg)` is ≥ half its solo value. A failure leaves an advance standing, labelled "a
  spot-plus-realised-vol digital explains it (CH30-type); options add nothing measurable". **If the census finds
  `cor(q − p_reg, q_RV − p_reg) > 0.9`** (feature-only, round 1 suggestion), the attribution is declared now to read "not
  identifiable" and no option credit can be given.
- **D1 spot-staleness control (binding robustness).** `q'` uses `S` = the `index_price` of the last Deribit trade at or
  before the time of the Polymarket transaction that set `p_reg` (not at `t`). D1 on `q'` keeps the sign and ≥ half the
  magnitude. *Alternative:* the Polymarket price lags a spot move in the 30 minutes before `t`; that is CB8-B's latency
  object, not CH89's distributional one.
- **B1 real/pseudo label swap calibration (binding).** Within each Gamma event, the real and pseudo labels of all its
  episodes are swapped with probability 1/2 (one coin per event; the day way uses one coin per UTC day); the per-pair
  statistic and its frozen weights are recomputed on the swapped labels. *Alternative:*
  episodes of one event share a price path, so the clustered p of a contrast can be anti-conservative.
- **B2 pseudo-level attribution (binding for crediting a "stop-cascade route").** `B2_pseudo`: the identical maker
  (same posting, crossing, fill-size and exit-cost rules) at pseudo-level breaks (quote one cent beyond the pseudo-level). Credit "stop-cascade route" only if `B2 − B2_pseudo ≥
  B2 / 2`. A failure leaves an advance standing, labelled "a generic post-crossing maker, not a round-level route".
- **B cascade descriptive (labelling only).** Transactions and volume in `(t_b, t_b + 10 min]` after real vs pseudo breaks.
  If the real/pseudo volume ratio is < 1.2, a B1 advance is labelled "round-level reversal without a measurable cascade"
  (CH93's mechanism not shown).

**Binding robustness for any advance or pass:** (i) D2: the +0.5c cost robustness keeps net > 0; B: the 30-min mark keeps
the sign and ≥ half the magnitude; (ii) p threshold and floor hold without the top 5 clusters of each way; (iii)
unweighted and size-weighted estimates agree in sign (D by transaction size at `p`, capped at 2,000 shares; B by 10-min
transaction volume; B2 by filled shares); (iv) sign by period: D in each of the three calendar thirds (2025-10..2026-01, 2026-02..05, 2026-06..09) and for each
asset separately; B in ≥ two thirds of months with ≥ 200 episodes; (v) unavailable units (round 1 item 5): D's eligibility, labels, 60% availability rule and coverage audit are in §2.7;
unavailable D units are excluded and counted, never imputed. **B missing marks (round 1 item 8):** the primary excludes
episodes without a 2 h mark (counted by arm and level); binding: the **worst case for the contrast** (missing real
episodes scored `R_e = −1c`, missing pseudo episodes `+1c`) keeps the sign and the p threshold; B2 fills without a mark
are scored at −1c per filled share before the exit cost; (vi) latency: D
uses `p` from a transaction within 10 min of `t` instead of 30 min (`p_reg` unchanged in its rule); B2 quotes post at `t_b + 120 s` instead of `+ 60 s`;
each keeps the sign and ≥ half the magnitude.

### 2.7 Pre-freeze census (counts only; q0207)

Outcome guard first; field-restricted accessors; a unit test asserts that no census path receives `Y`, the settlement
index, a 2 h mark or a fill P&L. **No slope, net, reversal or contrast is computed.** Features (`p`, `q`, `q_RV`, levels,
crossing times) and fill **counts** may be computed.
- **D eligibility and labels (round 1 item 5; declared before freshness).** An **eligible D unit** is a (frame market,
  origin) whose market was listed by the origin and whose **last transaction before `t` of any age**, inside the covered
  span, has YES price in `[0.05, 0.95]`. Eligibility uses no freshness rule, no Deribit data and no `Y`. Each eligible unit
  is then either available or carries exactly one label, checked in this order:
  1. **"unavailable (source: Data API truncation)"**: `t − 180 min` lies before the oldest reachable print of the market
     (the newest-first cap was reached), so freshness cannot be judged;
  2. **"unavailable (source: Deribit)"**: the Deribit fetch for that origin failed after retries, or no usable expiry
     within 3 days of `T` (§CB10-D), or the smoke-range check failed for its rows;
  3. **"inactive (no fresh trade)"**: no transaction in `[t − 30 min, t)`, or no separate earlier transaction for
     `p_reg` (§CB10-D). This is a market property, not a source failure.
  Eligible markets with no transaction at all before `t` are counted as "never traded by t" and are not eligible.
- **D availability rule (kept at 60%).** D1 is "not testable" if fewer than 60% of eligible units are available; the label
  is "(source unavailable)" if source labels (1-2) are the larger share of the missing units, else "(inactivity)".
- **D coverage audit (new, round 1 item 5).** Source-available share = eligible units without label 1 or 2 / eligible
  units. **PASS iff ≥ 90%** (the CB8/CB9 precedent). FAIL → D1 "not testable (source unavailable)", counted, whatever
  the 60% rule says.
- **D counts.** Ladder events and markets by asset and month; rule-text failures; exclusion drops by source (market id,
  event id, series-date) and the drops the full series-key rule would have made; eligible units and each label's count
  by asset, origin (`d − 5`, `d − 2`) and resolution weekday; IV fits (two-sided smile, ATM-only fallback, none) and the
  trades excluded as block, combo or liquidation; expiry distance distribution; distribution of `|q − p_reg|` (share ≥
  0.04) and `SD(q − p_reg)`; `cor(q − p_reg, q_RV − p_reg)` (> 0.9 → attribution "not identifiable", §2.6). **Gate
  GD:** ≥ 1,500 available D1 units in ≥ 100 resolution dates and ≥ 30 ISO weeks, each asset ≥ 30% of units, and ≥ 200
  units with a Deribit expiry within 3 days of `T` (CH89 kill 3). Fail → D1 "not testable", counted.
- **D power gate GDP (round 1 item 4; feature-only, declared now).** The census simulates outcomes from the Polymarket
  prices themselves, never from `Y` or `q`: for each asset x resolution date one uniform `U` (BTC and ETH uniforms of a
  date joined by a Gaussian copula with ρ = 0.8, declared), and every strike's simulated outcome `Y*_k = 1{U < p̄_k}`,
  where `p̄_k` is the mean of the market's available `p` over its origins (a monotone, ladder-consistent draw whose
  per-unit variance is `p̄(1 − p̄)`, the reviewer's variance proxy). On each of 500 draws (seed 10107) it computes the
  D1 estimator `β̂*` on the real features (`q − p_reg`, all D1 units). `MDE_D1 = (z_0.99 + z_0.80) x 1.2 x SD(β̂*)`, where
  1.2 is a declared inflation for cross-date and within-week dependence the draw does not model. **If `MDE_D1 > 1.0`,
  D1 is "not run (power)", counted with p = 1**, D1-rep and D2 are not triggered, and the record states the MDE. The
  threshold is fixed now and never moved. The census writes `SD(β̂*)` and `MDE_D1`; no `Y` is read.
  - **Re-entry route if GDP fails (written now).** A separately registered prospective design, CB10-D-P: the q0210
    collection machinery run without a Stage-1 dependency, on BTC and ETH daily ladders plus every other asset with both
    a Polymarket daily strike ladder and a Deribit option market (SOL and XRP linear options, if their trade counts pass
    the same IV-fit rule in a feature-only pre-check), with the D1 statistic, the same anchor and `p_reg` rules, and a
    sample size set by the same GDP proxy to reach `MDE ≤ 0.5`. It needs its own challenger round and freeze; no Stage-1
    D data are re-used in it.
- **B.** Frame, key drops, SCREEN/HOLDOUT markets and events; truncated markets (newest-first cap reached before the window
  start); real and pseudo episodes after the mutual-exclusion rule, by level pair; episodes with a 10-min transaction and
  with a 2 h mark, by arm and pair (counts only); B2 quotes not posted (would cross), posted and filled (count only), and
  filled shares after the transaction-size cap. **B1 weights frozen here (round 1 item 7):** `w_L = n_L / Σ n`, with `n_L`
  the count of eligible real-level SCREEN episodes with follow-through at level `L` (counts only, before any mark is
  read). **Gate GB:** ≥ 1,000 real and ≥ 1,000 pseudo SCREEN episodes, ≥ 100 events, ≥ 60 UTC days, and every pair with
  `w_L > 0` has ≥ 30 real and ≥ 30 pseudo episodes (a pair failing this gets `w_L = 0`, counted). **Gate GB2:** ≥ 300
  filled real-level B2 episodes. Fail → the test is "not testable", counted.
- **Coverage audit (B).** Share of SCREEN markets whose reachable print history covers their whole in-window life
  (newest-first cap not reached). **PASS iff ≥ 90%** (round 1 item 12: raised from 80% to the CB8/CB9 precedent). Labels
  as CB9 §2.7: audit FAIL → B "not testable (source limited)"; a GB fail reads "no opportunity" ("round-level breaks are
  rare") only if the audit passed.
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
  | q0202 | D frame + prints | about 750 Gamma (one-day windows over 365 days) + about 8,000 Data API (≤ 2 pages per market, about 7,300 markets after the round-1 calendar), about 75 min at 2 rps | ≤ 0.01 GB |
  | q0203 | Deribit trades + perpetual bars | about 1,100 Deribit history (2 currencies x about 370 origin days x 1-2 pages) + about 200 for the pre-window haircut data + about 20 chart requests | ≤ 0.02 GB |
  | q0204 | B frame + split | about 1,000 Gamma (one-day `end_date` windows, paged) | ≤ 0.005 GB |
  | q0205 | B prints → transactions | about 2,000 Data API (1-2 pages per market), about 20 min at 2 rps | ≤ 0.06 GB |
  | q0206 | B seal | about 50 Gamma | ≤ 0.001 GB |
  | q0210 | D Stage 2 (conditional) | about 110 requests per origin day (88 CLOB `/book`, about 10 Gamma, about 6 Deribit, 2 book summaries), 56-60 days, **one short cron-run per origin outside the queue lanes** (round 1 item 13, §CB10-D Stage 2) at ≤ 1 rps, ≤ 5 min, mem ≤ 300 MB | ≤ 0.01 GB |

- **Disk guard.** Every CB10 data job declares `--disk-cap-gb` (its output cap, all ≤ 0.06 GB) and
  `--data-dumps-cap-gb 14` (current convention), and exits **75** if data-dumps + its cap > 14 GiB **or** root free disk −
  its cap < 4.5 GB (the 4 GB collector guard plus 0.5 GB margin). CB10 output caps total **≤ 0.12 GB**. The precondition
  never changes retention. **Exit-75 waits are "pending" (round 1 item 14):** the queue keeps the job in `retry_wait`
  (30 min, up to 48 consecutive tempfails); after 48 the job becomes `failed` in the queue and is re-queued under a new id
  (as CB8-H's q0160b precedent), still "pending" for science, never "not run". Only the time-critical Stage-2 origins
  turn a disk refusal into a counted "unavailable (host disk)" unit.
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
the price finishes above `K` predict the resolution excess `Y − p` beyond the Polymarket price? Prospectively, does
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

**Polymarket prices (causal; round 1 item 1).** For each eligible unit (§2.7) and origin `t`:
- `p` (target price) = YES-terms VWAP of the last transaction with time in `[t − 30 min, t)`, at time `t_p`;
- `p_reg` (regressor price) = YES-terms VWAP of the last **other** transaction with time in `[t − 180 min, t_p − 5 min)`,
  at time `t_reg`. The two are distinct transactions at least 5 minutes apart, so `p`'s own noise never enters the
  regressor;
- either missing → "inactive (no fresh trade)", counted (§2.7). The price band `[0.05, 0.95]` is applied at eligibility
  (last transaction before `t` of any age, §2.7), not to `p`, so freshness cannot select on price.
`Y` from the guarded Gamma outcome.

**Anchor (frozen now; no fitting to outcomes).**
- Trades: Deribit option trades of the asset with timestamp in `[t − 120 min, t)`, **excluding block trades, combo legs
  and liquidations** (rows carrying `block_trade_id`, `combo_id` or `combo_trade_id`, or a `liquidation` flag; round 1
  suggestion; the variant with them is reported). `S` = `index_price` of the last remaining trade. For each trade,
  log-moneyness `m = ln(K_opt / index_price_trade)` with **its own** index price (round 1 item 15); `iv_dec = iv / 100`
  (Deribit reports percent). `τ_e` in years (ACT/365) from `t` to expiry `e` (08:00Z).
- Smile per expiry: weighted least squares of `iv_dec` on `m` over trades with `|m| ≤ 0.15`, weights = amount; needs
  ≥ 6 trades with ≥ 2 on each side of `m = 0`; gives `σ_e(m) = a_e + b_e m`. Else ATM fallback: `σ_e` = median `iv` of
  trades with `|m| ≤ 0.05` (≥ 3 trades), `b_e = 0` (flagged). Else expiry unusable. At the strike, `m_K = ln(K / S)`.
- Interpolation to `T`: the nearest usable expiries `e1 ≤ T < e2` with both within 3 days of `T`: total variance
  `w(K) = σ_e(m_K)² τ_e` interpolated linearly in time, `b` interpolated linearly; if only one side exists within 3 days,
  flat σ from that expiry. None → unavailable, counted.
- Digital (zero rates, forward = `S`, disclosed): `σ = sqrt(w / τ_T)`, `d1 = (ln(S/K) + σ²τ_T/2)/(σ√τ_T)`, `d2 = d1 −
  σ√τ_T`, **`q = Φ(d2) − (S/K) · φ(d1) · √τ_T · b`** (the digital `−∂C/∂K` of the undiscounted call: the smile-slope
  term is `−S φ(d1) √τ · ∂σ/∂K` with `∂σ/∂K = b/K` at `F = S`), clipped to [0.001, 0.999].
- Basis disclosed: Deribit's index (USD, multi-venue) vs Binance BTC/USDT at 12:00 ET (a few basis points; strike spacing
  is about 1.5-3% of the price).
- **No variance-premium haircut in the primary (round 1 suggestion, declined with reasons).** The hypothesis's object is
  the risk-neutral digital; a haircut is a second fitted constant whose estimation window and method would add a fork.
  A haircut rescales how far `q` sits from 0.5; that changes the slope's scale but cannot create a slope where the
  unhaircut anchor has none. Reported variant: `σ x (1 − h)`, with `h = 1 − median(RV_7d / ATM IV_7d)` computed **only**
  from Deribit data in `[2025-07-01, 2025-10-01)` (before every D origin), frozen in the census output; no Polymarket
  field enters `h`. The DVOL-flat version is also reported.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **D1** | forecasting | available D unit with `p`, `p_reg`, `q` (Stage 1: D window; Stage 2: post-freeze dates) | OLS slope `β` of `Y − p` on `q − p_reg` (with intercept), unweighted; run only if GD, GDP and the D coverage audit pass | > 0 |
| **D2** | economic (Stage 2 only) | traded market-origin: on some token `q_tok − a − f(a) ≥ 0.04` and size at `a` ≥ 5 shares (if both, the larger edge) | mean `Y_tok − a − f(a)`, cents per share | > 0 |

**Source check.** On units with `|ln(S_T/K)| > 0.5%` (`S_T` from the guarded settlement index), the index-implied outcome
vs the Gamma outcome: disagreement > 2% of market-dates → D "not testable (source)", counted. Disagreeing units stay in,
with the Gamma outcome (what pays).

**Reported (descriptive).** Log-loss and Brier of `q` and of `p`; calibration of `q` alone; `β` by moneyness tercile,
days to resolution (5 vs 2) and asset; the directional excess `E[(Y − p) · sign(q − p_reg)]` on units with
`|q − p_reg| ≥ 0.04`; the same-transaction slope (`Y − p` on `q − p`, the draft's statistic, descriptive only, to show the
shared-noise bias); the DVOL-flat, flat-smile, with-block/combo and `σ x (1 − h)` variants.

**MDE (assumptions, restated in round 1; the census GDP proxy replaces them and decides).** About 330 resolution dates
with ladders in the round-1 window (the series existed by 2025-11; earlier dates have none), in about 47 ISO weeks; 2
assets x 11 strikes x 2 origins = 44 candidate units per date. About 35% are eligible and available with both `p` and
`p_reg` (about 5,000 units). All strikes of a ladder settle on one price, so the effective sample is about 4 units per date
(about 1,300). With `SD(Y − p)` about 0.38, `SD(q − p_reg)` 0.04-0.06 and a 1.2 week-way inflation, `SE(β)` is about
0.21-0.32 and **the D1 MDE is about 0.65-1.0** in slope units (one-sided 0.01, 80% power). Had the CB8-B gap stayed
(about 210 dates, about 30 weeks), it would be about 0.8-1.25. **GDP (MDE ≤ 1.0) is therefore borderline:** if `SD(q −
p_reg)` is near 0.04 or availability is lower than assumed, D1 is "not run (power)", counted with p = 1, and the re-entry
route of §2.7 applies. If it runs, D1 can detect only an anchor close to the right price (`β` near 1); a real `β` of
0.3-0.7 reads "not detected at MDE x", and the 0.30 floor binds only if the MDE turns out smaller. Stage 2 (56 dates,
8-9 weeks, leave-one-week-out rule) has an MDE of about 1.5-2 and is a sign-level replication. **D2** (Stage 2): perhaps
20-30% of about 1,200 Stage-2 units trade; with date clustering the MDE is about 6-9c per share. Both detect only large
effects.

**Stage 2 (registered only if D1 advanced).** At each origin (12:00 ET, receipt-timed): the live ladder frame (Gamma,
frozen rule), CLOB `/book` of both tokens of every strike of the two ladders whose `d − 5` or `d − 2` origin this is,
Deribit option trades of `[t − 120 min, t)` (same endpoint as Stage 1, filtered by trade time), and the live book summary
(variant). `p` and `p_reg` for D1-rep follow the Stage-1 rules (prints fetched after the origin, filtered to time < `t`);
D2 uses the recorded asks. Definitions, anchor, thresholds and gates identical.
- **Scheduling (round 1 item 13).** The queue runs one job per lane, so a 56-day job would block a lane and still could
  not guarantee 12:00 ET. Stage 2 therefore does **not** run as a queue job. q0210 names this collection; after the D1
  advance is committed, a reviewed repo commit adds two cron lines to `scripts/oracle/crontab.txt` (deployed by
  `scripts/oracle/deploy.sh`, as every host change): `0 16 * * *` and `0 17 * * *` UTC, each calling `run_cb10.py dlad-live --origin auto`,
  which acts only when that minute is 12:00 in America/New_York (the DST check in code; the other line exits 0). Each
  run takes ≤ 5 minutes, ≤ 1 rps, mem ≤ 300 MB, outside the lanes (like the collector), with the collector yield and the
  disk guard; it records any lane job running beside it. It exits 0 without requests after `T10_D2_end` (or
  `T10_D2_collect_max`), and the lines are removed by the next commit. The 02:45-05:30 UTC blackout is not touched (origins are at 16/17Z).
- **Origin labels (counted, all toward the 20% rule).** An origin's book and Deribit fetch must complete with every
  receipt time in `[t, t + 10 min]`; otherwise:
  - **"unavailable (scheduling)"**: the run did not start, or did not finish within 10 minutes (host down, cron missed,
    overrun);
  - **"unavailable (host disk)"**: the run exited 75 on the disk guard;
  - **"unavailable (source)"**: an API failed after retries.
  None is refilled or replaced, and unavailable origins count toward the 56 dates. If more than 20% of Stage-2 origins
  carry any of the three labels, D1-rep and D2 are "not testable" with the dominant label, counted.

**Leakage.** Deribit trades strictly before `t`; Polymarket transactions strictly before `t` (`p` within 30 min, `p_reg`
within 180 min); eligibility from the last transaction before `t`; strikes from the question text; `Y` and the settlement
index guarded; no constant is fitted on any Polymarket data (the reported haircut uses pre-window Deribit data only);
D reads no CB8-B object (§1.3).

**What kills CH89.** GD, GDP or the D coverage audit fails ("not testable" / "not run (power)", counted); D1 not detected
at MDE or below floor; the sign-flip placebo advances; the independent-price placebo fails; the spot-staleness
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
field; a disclosed look-ahead in selection, not outcome: it keeps markets that ended up active, which over-represents
markets with many crossings and may favour news-driven moves; both arms share it), two outcomes; not weather, not crypto Up/Down, not any crypto
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
- Mark `M2h` = last transaction at or before `t_b + 2 h`, if its time is ≥ `t_b + 90 min`; else unavailable: excluded
  from the primary, counted by arm and level, and scored by the binding worst case for the contrast (real −1c, pseudo
  +1c; §2.6 (v), round 1 item 8).
- **Reversal** `R_e = s · (M2h − VWAP10)`, cents (positive = the price moved back toward the side of the level it broke
  from).

**B1 statistic (round 1 item 7: per pair, frozen weights).** For each real level `L`, `C_L` = mean `R_e` over its real
episodes minus mean `R_e` over the episodes of **its own** pseudo-levels `L − 0.03` and `L + 0.03` (pooled). `B1 = Σ_L
w_L · C_L`, with `w_L` frozen in the census from real-episode counts (§2.7), so a pair never borrows a contrast from
another price band. The cluster bootstrap resamples whole events (or days) and recomputes every `C_L` with the frozen
`w_L`.

**Maker rule (B2).** For each eligible real-level episode with follow-through (the **eligible episodes**, B2's route
denominator):
- **Posting (round 1 item 9).** At `t_b + 60 s` the paper quote is down-break → bid at `L − 0.01`, up-break → ask at
  `L + 0.01` (one cent, a valid price under either venue tick size, 0.01 or 0.001; Gamma's end-of-life tick field is not
  used), 100 shares, live until `t_b + 10 min`. If the **last transaction at or before `t_b + 60 s` is at or through the
  quote** (price ≤ `L − 0.01` for a bid, ≥ `L + 0.01` for an ask), the quote would cross or join a market already
  trading there: the episode is **"not posted"** (counted; P&L 0 in the route denominator, absent from the per-filled-share
  mean). The not-posted share is reported by level.
- **Fills (trade-through only; size cap, round 1 item 10).** Each transaction strictly below the bid (strictly above the
  ask) in the live interval fills `min(remaining, that transaction's size)` shares at the quote price; fills accumulate up
  to 100 shares. A transaction at the quote price fills nothing.
- **Mark-out and exit (round 1 item 11).** Per filled share: bid `M2h − (L − 0.01) − c_exit`, ask `(L + 0.01) − M2h −
  c_exit`, with `c_exit` from §2.1 (taker fee at `M2h` plus a 1.5c half-spread).
- **B2 statistic.** Mean net per filled share (fill-weighted within episode, filled episodes equally weighted). **Route
  gate:** mean over all eligible episodes of (total net P&L / 100 intended shares), with not-posted and unfilled episodes
  scored 0, > 0.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **B1** | mechanism contrast | eligible episode with `VWAP10` (SCREEN events; Stage 2: HOLDOUT) | `Σ_L w_L · C_L`: per real level, mean `R_e` minus the mean over its own `L ± 0.03` episodes; census-frozen weights; cents | > 0 |
| **B2** | economic | filled real-level maker episode (SCREEN; Stage 2: HOLDOUT) | mean net per filled share after `c_exit`, cents; route gate: mean net per eligible episode (per 100 intended shares; not-posted and unfilled = 0) > 0 | > 0 |

**Reported (descriptive).** `R_e` by level and direction; reversal at 30 min; the cascade descriptive (transactions and
volume in the 10 minutes after real vs pseudo breaks); per-pair `C_L` and the unweighted pooled contrast; missing-mark
shares by arm; the B2 not-posted share, fill rate and filled shares; B2 gross (before `c_exit`); the rebate version;
per-level B2.

**MDE (assumptions; restated in round 1; census replaces).** About 700 SCREEN markets in about 230 events, about 40 active
days each, about 0.1 eligible real-level episodes per market-day after the exclusions: about 2,800 real and about 4,500
pseudo SCREEN episodes. With `SD(R_e)` about 4c and an event design effect of about 3, the per-pair contrast (each pair
uses only its own pseudo episodes, about 900 per pair at the heaviest weights) has an SE of about 0.22-0.25c, so **the B1
MDE is about 0.7-0.8c** (floor 0.5c; was 0.6-0.7c pooled). B2: perhaps 15-25% of eligible episodes not posted, and
25-35% of posted quotes filled under trade-through, give about 550-700 filled episodes; mark-out SD about 5c, **MDE about
1.0-1.2c** on the net (floor 1.0c). The exit cost (about 1.5c plus a fee of up to 1.25c at 0.50) is a level shift, not
extra noise, so B2 needs a gross mark-out of about 3.5-4c to clear its floor. Both are at or above their floors; a real
0.5c contrast reads "not detected at MDE 0.75c".

**Leakage.** Episode detection uses transactions up to `t_b`; the mark uses later transactions only (a print-based target,
no outcome); levels, pseudo-levels, windows and the maker rule are fixed now and never re-tuned; HOLDOUT sealed. Same
calendar as HB2, CB8 and CB9-K/D (markets disjoint by key): a B result is not out-of-time evidence. Breaks that coincide
with news are in both arms; news-driven real breaks that continue make B1 conservative. **Disclosed (round 1
suggestion):** pseudo-levels 0.47/0.53 (and the others) sit two to three cents from round levels where resting depth
gathers (CH20), so pseudo breaks can also hit round-level depth, which shrinks the contrast (conservative for B1); the
mutual-exclusion rule removes only episodes within 60 minutes of each other.

**What kills CH93.** GB, GB2 or the coverage audit (≥ 90%) fails; the worst-case missing-mark check fails; B1 not detected or below floor; the label-swap placebo advances; B2
below floor, route gate fails ("reversal exists but the maker still loses: no route"), or the pseudo attribution fails
(labelled generic); B1-rep / B2-rep fail on HOLDOUT.

### CB10-F: Data jobs

q0200 smoke (PASS needs: Deribit history paging returns the same trade count on two repeat requests for two out-of-window
hours (2026-10-02T10Z, 2026-10-03T16Z) with `iv` and `index_price` on ≥ 99% of rows, and ≥ 99% of rows with `1 ≤ iv ≤
400` (percent) and `index_price > 0` (round 1 item 15); the count of trades flagged block, combo or liquidation (counts
only); the ladder frame walker finds both
series' events for two out-of-window dates with 11 strikes each and every rule flag present; the question regex parses
every strike; the Data API newest-first paging reaches the oldest print of two out-of-window ladder markets; the
transaction aggregation yields one row per hash on a fixture; the Gamma whitelist parser applied to two live closed
markets keeps only whitelisted keys (round 1 item 6). Any failure → the dependent family "not testable (source)",
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
| q0202 | net | 33 | about 8,750 req, mem 400, ≤ 0.01 GB | q0201 | with q0201 |
| q0203 | net | 33 | about 1,320 req, mem 400, ≤ 0.02 GB | q0202 | with q0202 |
| q0204 | net | 33 | about 1,000 req, ≤ 0.005 GB | q0201 | with q0201 |
| q0205 | net | 32 | about 2,000 req, mem 600, ≤ 0.06 GB | q0204 | with q0204 |
| q0206 | cpu | 32 | light | q0205 | with q0205 |
| q0207 | cpu | 31 | ≤ 0.8 GB | q0202, q0203, q0206 | after the seal copy is committed |
| q0208-q0209 | cpu | 30 | ≤ 0.8 GB | q0207 | after the CB10 freeze |
| q0210 | none (cron) | - | about 110 req per origin day at ≤ 1 rps, ≤ 5 min per run | q0208 | only if D1 advanced; cron lines committed and deployed then |
| q0211 | cpu | 30 | ≤ 0.5 GB | q0210 | after `T10_D2_end` + 2 d |
| q0212 | cpu | 30 | ≤ 0.8 GB | q0209 | only if B1 or B2 advanced |

```json
{"id": "q0200_cb10_smoke", "title": "CB10: smoke (Deribit history paging + iv/index_price presence on 2 out-of-window hours; ladder frame walker, rule flags and strike regex on 2 out-of-window dates; iv percent range 1-400 on >= 99% of rows; Gamma whitelist parser on 2 live closed markets; Data API newest-first paging to the oldest print on 2 out-of-window ladder markets; transaction aggregation fixture); counts only", "family": "creative_batch_10", "priority": 35, "expected_value": "go/no-go for every CB10 source", "data": ["Deribit public history", "public Gamma, Data API"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "cpu", "network": "history.deribit.com, gamma-api, data-api"}, "depends_on": [], "argv": ["scripts/run_cb10.py", "smoke", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch10/smoke.json", "trials.jsonl (cb10_descriptive)"], "next_action": "PASS: q0201 after T_seal; FAIL: dependent family not testable (source), counted", "notes": "CREATIVE_BATCH_10.md CB10-F. DRAFT. May run before T_seal (cpu lane, <= 60 requests). Prints counts only."}
{"id": "q0201_cb10_exclusion_keys", "title": "CB10: exclusion keys = CB9 q0182 keys + CB9 P and K/D frame ids + seal copies committed since q0182; series-date keys for the two ladder series", "family": "creative_batch_10", "priority": 34, "expected_value": "disjointness of D and B", "data": ["creative_batch9/exclusion_keys.csv.gz", "creative_batch9 frame id lists", "docs/research_lab/seals/*", "public Gamma (ids)"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0182_cb9_exclusion_keys", "q0183_cb9_pyth_frame", "q0185_cb9_kd_frame"], "argv": ["scripts/run_cb10.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "14"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch10/exclusion_keys.csv.gz", "manifest.json"], "next_action": "q0202, q0204", "notes": "DRAFT. After T_seal. >2% missing metadata -> disjointness unverified (D1, B1, B2 not testable, counted). Exit 75 on data-dumps or free-disk headroom."}
{"id": "q0202_cb10_dlad_frame", "title": "CB10-D: Gamma frame of BTC/ETH daily 'above $K on date' ladders (resolution dates [2025-10-01,2026-10-01), round 1), whitelisted fields, rule flags, series-date exclusion; Data API newest-first prints -> per-origin p (last transaction in [t-30min,t)), p_reg (separate earlier transaction in [t-180min, t_p-5min)), last transaction of any age, covered span; outcomes to the guarded file", "family": "creative_batch_10", "priority": 33, "expected_value": "D population and Polymarket prices at origins", "data": ["public Gamma, Data API", "creative_batch10/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, data-api"}, "depends_on": ["q0201_cb10_exclusion_keys"], "argv": ["scripts/run_cb10.py", "dlad-frame", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "14", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h10_dlad/{frame.csv.gz,origins.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0203", "notes": "DRAFT. No print stored beyond origin rows; no side or wallet read. Gamma whitelist (round 1 item 6). Exit 75 = pending.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"dlad_frame_complete\""}}
{"id": "q0203_cb10_deribit_trades", "title": "CB10-D: Deribit option trades [t-120min, t) per origin time and currency (timestamp, instrument, iv in percent, index_price, amount, block/combo/liquidation flags); pre-window [2025-07-01,2025-10-01) ATM IV and perpetual bars for the reported haircut; BTC/ETH-PERPETUAL hourly bars [t-7d, t); settlement index at each resolution minute to the guarded file", "family": "creative_batch_10", "priority": 33, "expected_value": "D anchor and attribution inputs", "data": ["history.deribit.com public (keyless)", "www.deribit.com public chart data"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "history.deribit.com, www.deribit.com"}, "depends_on": ["q0202_cb10_dlad_frame"], "argv": ["scripts/run_cb10.py", "deribit-trades", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "14"], "timeout_s": 3600, "max_retries": 2, "outputs": ["history/h10_dlad/deribit/{trades.csv.gz,perp_bars.csv.gz,settle_index_guarded.csv.gz,manifest.json}"], "next_action": "q0207", "notes": "DRAFT. Origin times from q0202's frame only; no Polymarket field read."}
{"id": "q0204_cb10_brk_frame", "title": "CB10-B: Gamma frame (whitelisted fields, no outcome field; closed binary, scheduled end [2026-04-08,2026-10-01), life overlap >= 3 d, volume >= $10k, not weather/crypto Up-Down/crypto ladders/Pyth), key drops, <= 3 per event, seeded 1,400 markets, event split SCREEN/HOLDOUT (arepo-cb10-brk-split)", "family": "creative_batch_10", "priority": 33, "expected_value": "B population and split", "data": ["public Gamma", "creative_batch10/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0201_cb10_exclusion_keys"], "argv": ["scripts/run_cb10.py", "brk-frame", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.005", "--data-dumps-cap-gb", "14"], "timeout_s": 3000, "max_retries": 2, "outputs": ["history/h10_brk/{frame.csv.gz,split.json,manifest.json}"], "next_action": "q0205", "notes": "DRAFT. Split written before any print read. Sports stratum <= 15%, reported, not primary."}
{"id": "q0205_cb10_brk_prints", "title": "CB10-B: newest-first Data API prints per market (limit 10000, offset <= 10000), aggregated by transaction hash at fetch to (time, YES-terms VWAP, size), window [2026-04-01,2026-10-01); covered span recorded; HOLDOUT written to holdout/", "family": "creative_batch_10", "priority": 32, "expected_value": "B1/B2 inputs", "data": ["public Data API"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "net", "network": "data-api"}, "depends_on": ["q0204_cb10_brk_frame"], "argv": ["scripts/run_cb10.py", "brk-prints", "--rules", "../docs/research_lab/seals/cb10_rules.json", "--rps", "2", "--disk-cap-gb", "0.06", "--data-dumps-cap-gb", "14", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h10_brk/{screen,holdout}/tx.csv.gz", "manifest.json"], "next_action": "q0206", "notes": "DRAFT. No side, wallet or hash stored. One market in memory at a time.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"brk_prints_complete\""}}
{"id": "q0206_cb10_brk_seal", "title": "CB10-B: HOLDOUT listing sha256, seal-time drops vs seal copies committed by now (incl. CB9 h10_sign if present), seal copy seals/cb10_brk_holdout_SEAL.json", "family": "creative_batch_10", "priority": 32, "expected_value": "sealed holdout", "data": ["history/h10_brk/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu", "network": "gamma-api (light)"}, "depends_on": ["q0205_cb10_brk_prints"], "argv": ["scripts/run_cb10.py", "brk-seal", "--rps", "2"], "timeout_s": 1800, "max_retries": 2, "outputs": ["history/h10_brk/holdout_SEAL.json"], "next_action": "commit the seal copy; q0207", "notes": "DRAFT. Sealed files never edited; drops recorded as DROPPED_* blocks."}
{"id": "q0207_cb10_census", "title": "CB10: pre-freeze census, counts only (D eligibility and labels, D coverage audit >= 90%, GD, power gate GDP (feature-only simulated outcomes from p, MDE <= 1.0), GB, GB2, frozen B1 weights, B coverage audit >= 90%, feature-only gap and q/q_RV correlation, series-key comparison, MDEs)", "family": "creative_batch_10", "priority": 31, "expected_value": "gates and MDEs before the freeze", "data": ["history/h10_dlad (no guarded file)", "history/h10_brk/screen (HOLDOUT file and event counts only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0202_cb10_dlad_frame", "q0203_cb10_deribit_trades", "q0206_cb10_brk_seal"], "argv": ["scripts/run_cb10.py", "census"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/census.json", "trials.jsonl (cb10_descriptive)"], "next_action": "science-reviewer freeze check, then model_specs/cb10_v1.json", "notes": "DRAFT. Outcome guard; no slope, net, reversal or contrast computed."}
{"id": "q0208_cb10_screen_D", "title": "CB10-D: D1 Stage 1 (Y - p on q - p_reg; date, asset-date and ISO-week ways) with week sign-flip and independent-price placebos, option attribution, spot-staleness control and binding robustness; refuses unless GD, GDP and the D coverage audit passed (else writes the counted not-run/not-testable line)", "family": "creative_batch_10", "priority": 30, "expected_value": "D verdict", "data": ["history/h10_dlad (guarded files opened here only)"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0207_cb10_census"], "argv": ["scripts/run_cb10.py", "screen", "--family", "D"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/results_D.json", "trials.jsonl (cb10_test + creative_batch_10:D)"], "next_action": "advanced: commit q0210", "notes": "DRAFT. Refuses before the CB10 freeze hash."}
{"id": "q0209_cb10_screen_B", "title": "CB10-B: B1 (per-pair, census-frozen weights) and B2 (not-posted rule, size-capped trade-through fills, exit cost) Stage 1 on SCREEN events with label-swap placebo, pseudo attribution, worst-case missing marks and binding robustness", "family": "creative_batch_10", "priority": 30, "expected_value": "B verdicts", "data": ["history/h10_brk/screen/"], "resources": {"mem_mb": 800, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0207_cb10_census"], "argv": ["scripts/run_cb10.py", "screen", "--family", "B"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch10/results_B.json", "trials.jsonl (cb10_test + creative_batch_10:B)"], "next_action": "advanced: commit q0212", "notes": "DRAFT. Refuses to open holdout/."}
{"id": "q0210_cb10_dlad_live", "title": "CB10-D Stage 2: 56 post-freeze resolution dates; per 12:00 ET origin, a cron-run (outside the queue lanes) records receipt-timed the ladder frame, CLOB /book of both tokens of every strike, Deribit trades [t-120min,t) and the live book summary (variant); prints fetched after each origin", "family": "creative_batch_10", "priority": 35, "expected_value": "out-of-time D replication and D2 economic data", "data": ["public Gamma, CLOB /book, Data API", "Deribit public"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "none (cron, round 1 item 13)", "network": "gamma-api, clob, data-api, deribit"}, "depends_on": ["q0208_cb10_screen_D"], "argv": ["scripts/run_cb10.py", "dlad-live", "--origin", "auto", "--rps", "1", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "14"], "timeout_s": 300, "max_retries": 0, "outputs": ["research_lab/creative_batch10/dlad_live/<origin_date>/..."], "next_action": "q0211 after T10_D2_end + 2 d", "notes": "DRAFT. Not a queue job: two cron lines (0 16 and 0 17 UTC; acts only at 12:00 America/New_York) committed to scripts/oracle/crontab.txt and deployed only if D1 advanced. Every receipt in [t, t+10 min] or the origin is unavailable (scheduling / host disk / source), never refilled; > 20% unavailable -> D1-rep and D2 not testable, counted. Logs any concurrent lane job."}
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

- **Round-1 additions.**
  - `cb10_dlad`: `p` and `p_reg` (distinct transactions, ≥ 5 min apart, windows `[t − 30 min, t)` and `[t − 180 min,
    t_p − 5 min)`) and `p_alt` for the placebo; eligibility from the last transaction of any age with the price band;
    the three unavailable labels in their fixed order; the 60% rule with the dominant-label naming; the D coverage audit
    (≥ 90%); the GDP simulation (ladder-consistent `Y* = 1{U < p̄}`, copula ρ = 0.8, 500 draws, inflation 1.2, threshold
    1.0) on a fixture where the answer is known; the ISO-week way with the small-G rule and the leave-one-week-out sign
    rule; `iv / 100` and per-trade moneyness; block/combo/liquidation exclusion; the pre-window haircut constant; the
    Gamma whitelist parser with the forbidden-field fixture (item 6).
  - `cb10_brk`: per-pair `C_L` with census-frozen weights and the ≥ 30/30 pair rule; worst-case missing marks (real −1c,
    pseudo +1c); the not-posted rule (last transaction at or through the quote at `t_b + 60 s`); size-capped trade-through
    fills; `c_exit`; the route gate over eligible episodes; the B coverage audit at 90%.
  - Stage 2 runner `dlad-live --origin auto`: the America/New_York 12:00 check on both cron minutes across 2026-11-01;
    the `[t, t + 10 min]` receipt rule; the three origin labels; exit 0 after `T10_D2_end`.
  - Runner: exit 75 recorded as "pending" (no trials line); GDP/GD/audit failures write the counted p = 1 line.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: D1, B1, B2 | 3 | `cb10_test` + `:D`, `:B` (2) | p < 0.01 each; batch-Holm label (α 0.01, k1 = 3 fixed); BY triage. D1 counted with p = 1 if GD, GDP or the D coverage audit fails |
| Stage 2: D1-rep, D2 (if D1 advanced) | ≤ 2 | `cb10_replication` | one Holm over CB10 Stage 2, one-sided α 0.05 |
| Stage 2: B1-rep, B2-rep (each if its Stage 1 advanced) | ≤ 2 | `cb10_replication` | as above |
| Census, gates, descriptives, variants, cascade descriptive | 0 | `cb10_descriptive` | - |
| **Total** | **3 fixed + ≤ 4 conditional = 3-7 (unchanged in round 1)** | | cumulative ≥ 1,146 at the round-1 response → ≥ 1,149-1,153 plus CB6-CB9 |

**Host compute.** Under 2 CPU-hours at nice 19 (the GDP simulation adds about 10 CPU-minutes); peak RAM 0.8 GB.
**Network.** Before `T_seal`: ≤ 60 requests (q0200, `cpu` lane). After: about 14,000 requests on the `net` lane (about
10,000 Data API, most for the longer D window, about 2,700 Gamma, about 1,300 Deribit including the pre-window haircut
data; no pmxt), about 2 h of wall time at 2 rps in total. Conditional Stage 2: about 110 requests per origin day for about 60 days, in per-origin cron runs outside the lanes
at ≤ 1 rps. **Disk.** ≤ 0.12 GB in total, no job above 0.06 GB.

**Dates (estimates, conditional on archive rotation; round 1 item 14).** q0200: after its code and rules file, about
2026-10-19/20 (`cpu` lane, before `T_seal`; ≤ 60 requests and ≤ 0.001 GB). q0201-q0206: after `T_seal` and CB9's
q0182/q0183/q0185, **and after rotation frees disk** (until then they are "pending" on exit 75). With rotation by about
10-22, about 10-23 to 10-27; otherwise later, with no rule change. Census, freeze and Stage 1 follow by about 1-2 days.
D Stage 2 (if triggered): first resolution date about 6 days after the D1 result, `T10_D2_end` 56 dates later, q0211 2
days after that. B Stage 2 (if triggered): days after Stage 1.

## 7. Main scientific risks

1. **D1 may not run (power).** All strikes of one ladder settle on one price, so about 330 dates in about 47 weeks carry
   the information. The restated MDE is about 0.65-1.0 against the GDP threshold of 1.0, so D1 may be "not run (power)",
   counted with p = 1, with the written re-entry route (§2.7). If it runs, it detects only an anchor close to the right
   price.
2. **Trade-time IVs are a noisy smile.** Two hours of trades (about 700 BTC, fewer ETH) spread over a dozen expiries give a
   few points per near expiry; the linear smile and the ATM fallback are crude, and weekend hours are thin. The smile-slope
   term can be unstable when `b` is poorly fitted. Both are frozen; the flat-smile and with-block/combo variants are
   reported. Monday resolutions at `d − 5` may lack an expiry within 3 days (§0.3.1).
3. **Spot latency or microstructure masquerading as option information.** The separate-transaction regressor removes
   the shared-noise bias; the independent-price placebo, the spot-staleness control and the option attribution are the
   remaining guards. Only an advance passing all of them would support CH89's claim; `cor(q − p_reg, q_RV − p_reg) > 0.9`
   makes the attribution "not identifiable".
4. **Declared deviations.** The series-date exclusion (§1.3) replaces the series-key rule for D (the census reports both),
   and D now spans CB8-B's weeks (written argument, §1.3). A D1 result and a CB8-B result in those weeks are not
   independent evidence about crypto markets.
5. **B's breaks are partly mechanical.** The bid-ask bounce and post-move reversal appear in both arms; the per-pair
   contrast removes them only if pseudo-level breaks are comparable moves. The 60-minute mutual exclusion removes moves
   that cross both, which favours smaller moves in both arms. Pseudo-levels can sit in round-level resting depth (CH20),
   which shrinks the contrast (conservative). The end-of-life ≥ $10k volume filter selects markets that became active.
6. **B2 fill realism.** Trade-through fills are conservative on count but adverse in selection (fills only on deeper
   moves); queue position is unknown. Fills are capped at each trade-through transaction's size, quotes that would cross
   are not posted, and the exit pays a fee and a fixed 1.5c half-spread; real exits may cost more in thin books (the
   2.0c robustness is the guard).
7. **Truncated histories.** The Data API reaches only the newest 20,000 prints; the busiest markets lose early history.
   The coverage audits (≥ 90% for both D and B) and the covered-span rule keep truncation from reading as "no trade" or "no
   break".
8. **Same calendar.** B shares April-September 2026 with HB2, CB8 and CB9-K/D (markets disjoint by key); B-rep on HOLDOUT
   is same-calendar (L2), not out-of-time.
9. **Queue, disk and Stage-2 scheduling.** CB10 sits behind CB6-CB9 in the `net` lane, and data-dumps is near its cap
   (13.1 GiB, about +1.1 GB/day); jobs are "pending" on exit 75 until rotation. Stage 2 depends on cron runs at 12:00 ET
   on a single small host: missed origins are counted as unavailable (scheduling), and more than 20% makes D1-rep and D2
   "not testable", counted.

## 8. Next actions

1. **Challenger review: done** (round 1, §9-§10; one challenge, one response, no second round).
2. Write `seals/cb10_rules.json` (whitelists, IV units, eligibility, GDP constants, B1 pair rule, B2 posting/fill/exit
   rules), `cb10_dlad.py`, `cb10_brk.py`, `run_cb10.py` and tests. Then the **code-against-design freeze check**
   (`science-reviewer`). Commit q0200 (`cpu` lane, may run before `T_seal`), then q0201-q0206 after `T_seal`, CB9's
   q0182/q0183/q0185 and disk headroom.
3. Census q0207 (GD, GDP, audits, B1 weights) → freeze `model_specs/cb10_v1.json` → q0208/q0209 → conditional jobs by the
   stated triggers (Stage-2 cron lines only after a committed D1 advance).
4. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.

## 9. Challenger review, round 1 (science-reviewer, 2026-10-17)

One `science-reviewer` pass on the committed draft `19ae522`. **Verdict: both families ACCEPT_WITH_REQUIRED_CHANGES.**
Items, recorded in substance:

**Required changes.**
1. D1 shares last-trade noise in `Y − p` and `q − p`, a positive bias of about `var(e)/var(q − p)` ≈ 0.03-0.14 that the
   sign-flip placebo cannot catch. Take the regressor's Polymarket price from an earlier, separate trade, or add a binding
   placebo with an independent Polymarket price in place of `q` and judge D1 against it.
2. D breaks its own calendar rule: `d − 5` origins, Deribit trades for `d` = 08-11..08-15 and the 7-day perpetual bars
   reach into `[04-13, 08-11)`. Start at `d ≥ 2026-08-23` or reword with a written justification.
3. D clustering: add an ISO-week cluster way, apply the small-G rule (about 30 weeks), restate the MDE.
4. Declare now a feature-only census power gate (variance proxy `p(1 − p)`, no `Y`). If MDE > 1.0, D1 is "not run
   (power)", counted p = 1, with a written re-entry route for an adequately powered prospective design; or justify
   running it regardless.
5. §2.6(v) 60% availability: define "eligible" before freshness; separate labels for no fresh trade (inactivity), Data
   API newest-first truncation (source) and Deribit failure / no IV fit (source); add a D coverage audit.
6. Whitelist the Gamma fields for the q0202/q0204 frames (closed markets carry `lastTradePrice`, `bestBid`/`bestAsk`,
   `umaResolutionStatus`, `closedTime`) and require a unit test.
7. B1: real `L` minus its own `L ± 0.03` per pair, weighted by pre-declared real-episode counts.
8. Missing 2 h mark: real −1c and pseudo +1c (worst case for the contrast), or exclude plus a binding balance check on
   missingness.
9. B2: if the last trade before `t_b + 60 s` is already through `L − 0.01` (mirror for up), the quote would cross.
   Declare it "not posted" and define how it enters the route denominator.
10. B2's size guard is vacuous with fixed 100-share fills: cap each fill at the trade-through transaction size.
11. B2 exit cost: subtract a declared exit cost (taker fee at `M2h` plus a fixed half-spread), or make hold-to-resolution
    the primary.
12. B coverage audit 80% → 90% (CB8/CB9 precedent), or a written justification.
13. D Stage 2 timing: one job per lane, and q0210 is a 56-day time-critical `cpu` job. Declare how 12:00 ET origins are
    guaranteed, with labels unavailable (scheduling) / (host disk, exit 75) / (source), all counted toward the 20% rule.
14. Disk: post-`T_seal` jobs will exit 75 until rotation frees space. State that exit-75 waits are "pending", never "not
    run", and make the 10-23..10-27 schedule conditional.
15. Deribit `iv` is in percent: pin the conversion to decimal plus a smoke range check. Compute moneyness with each
    trade's own `index_price`.

**Suggestions (adopt or decline with reasons).** Exclude block trades and combo legs from the smile fit, or report a
variant without them; if `cor(q − p, q_RV − p) > 0.9` in the census, the attribution reads "not identifiable"; the census
reports drops under ±1 day vs the full series-key rule; the CH89 variance-premium haircut frozen from pre-sample data, or
a justified omission; disclose that pseudo-levels may sit in round-level resting depth and the selection effect of the
end-of-life ≥ $10k volume filter; counter now 1,146; optionally extend D into the CB8 calendar with a written argument
(CB8-B seals Up/Down klines and books, not BTC paths), which cuts the MDE about 20%. Also commit the §0.3 probe scripts'
essentials into the doc (the reviewer could not verify the `/tmp` probes), and say whether Deribit lists daily expiries
far enough ahead for the `d − 5` origins.

## 10. Response to challenger round 1 (2026-10-17)

Every required item is applied in the design text above. No floor, threshold, gate, alpha or cap was relaxed; the
changes tighten (separate-transaction regressor plus an extra binding placebo, a week cluster way, a new power gate, a new
D coverage audit, B coverage 80% → 90%, worst-case missing marks, not-posted quotes, size-capped fills, an exit cost) or
disclose. The one design widening, D's calendar, was the reviewer's suggestion and comes with a written argument.

| Item | Change | Sections |
|---|---|---|
| R1 shared noise | Regressor `q − p_reg`, with `p_reg` from a separate transaction ≥ 5 min before `p`'s, in `[t − 180 min, t_p − 5 min)`; target keeps `p`. Residual bounce correlation is negative (conservative, disclosed). **Also** the binding independent-price placebo: `p_alt` (a third transaction) in place of `q`; D1 credits the anchor only if the `p_alt` slope fails the p threshold and `β̂(q) − β̂(p_alt) ≥ 0.30`. The same-transaction slope is reported only | §2.4; §2.6; §CB10-D prices, table, reported; q0202, q0208 |
| R2 calendar | Adopted the reviewer's suggestion instead of the 08-23 start: the D window is `[2025-10-01, 2026-10-01)` with the written argument that D reads no CB8-B sealed object (Up/Down books, prints, Binance klines); every D read lies in `[d − 12 d, d]`, before `T10_hist_end`. The common-path dependence is disclosed | §0; §1.2; §1.3; §7 risk 4 |
| R3 week way | ISO week of `d` added as a third D cluster way; small-G rule (CR1 at G ≥ 30, CR2 + Webb at 15-29, leave-one-week-out sign rule below 15; Stage 2 is always in the last case). Sign-flip placebo now flips by week. MDE restated: about 0.65-1.0 (was 0.85-1.25 on the gapped calendar without the week way) | §2.3; §2.6; §CB10-D MDE |
| R4 power gate | **GDP** declared: feature-only simulated outcomes `Y* = 1{U < p̄}` (one uniform per asset-date, BTC/ETH copula ρ = 0.8), 500 draws of the D1 estimator on the real features, `MDE = 3.17 x 1.2 x SD(β̂*)`; **MDE > 1.0 → D1 "not run (power)", counted p = 1**; re-entry route written (a separately registered prospective CB10-D-P with more assets, sized to MDE ≤ 0.5, no Stage-1 data re-used). Not run regardless of power is not argued | §2.7; §2.5; §CB10-D MDE, kills; §6; §7 risk 1 |
| R5 eligibility and labels | Eligible = listed market-origin whose last transaction before `t` (any age, covered span) is in `[0.05, 0.95]`, before freshness. Labels in fixed order: source (Data API truncation), source (Deribit: failed fetch, no expiry within 3 days, range-check failure), inactive (no fresh trade or no separate earlier trade). The 60% rule kept, named by the dominant missing reason. New **D coverage audit ≥ 90%** source-available | §2.7; §2.6 (v); §CB10-D prices |
| R6 field whitelist | Explicit key whitelists for q0202 and q0204; forbidden fields (`lastTradePrice`, `bestBid`/`bestAsk`, `spread`, price changes, `umaResolutionStatus(es)`, `closedTime`, `volume*`, `liquidity*`, and `outcomePrices` except D's guarded route) dropped at parse; B keeps only a `vol_ok` boolean; unit test with a forbidden-field fixture; smoke applies the parser to two live markets | §1.4; §CB10-F; §5; q0202, q0204 |
| R7 B1 per pair | `B1 = Σ_L w_L C_L`, `C_L` = real `L` minus its own `L ± 0.03`; weights frozen in the census from real-episode counts; a pair with < 30 real or < 30 pseudo episodes gets weight 0 (counted); label-swap placebo recomputes with frozen weights. B1 MDE restated about 0.7-0.8c | §2.4; §2.6; §2.7; §CB10-B; q0209 |
| R8 missing marks | Primary excludes (counted by arm and level); **binding** worst case for the contrast (real −1c, pseudo +1c) keeps the sign and the p threshold | §2.6 (v); §CB10-B episodes |
| R9 crossing quote | "Not posted" if the last transaction at or before `t_b + 60 s` is at or through the quote; counted; scored 0 in the route denominator (all eligible episodes, per 100 intended shares); absent from the per-filled-share mean; share reported | §2.4; §CB10-B maker rule |
| R10 fill size | Each trade-through transaction fills `min(remaining, its size)`, accumulating to at most 100 shares; a print at the quote fills nothing. The size-weighted robustness is now informative | §CB10-B maker rule; §7 risk 6 |
| R11 exit cost | `c_exit = r_B · M2h(1 − M2h) + 1.5c` per filled share (`r_B` = recorded `feeSchedule.rate`, 0.05 if absent); primary net after `c_exit`; binding robustness with a 2.0c half-spread. Hold-to-resolution not used (B has no outcome guard). B2 MDE restated about 1.0-1.2c on the net; a gross of about 3.5-4c is needed to clear the 1.0c floor | §2.1; §2.4; §CB10-B; §7 risk 6 |
| R12 B audit | 80% → **90%** | §2.7; §7 risk 7 |
| R13 Stage-2 timing | Stage 2 is not a lane job: after a committed D1 advance, two cron lines (16:00Z and 17:00Z, acting only at 12:00 America/New_York) run `dlad-live --origin auto` for ≤ 5 min at ≤ 1 rps; receipts must fall in `[t, t + 10 min]`; labels unavailable (scheduling) / (host disk) / (source), never refilled, all counted toward the 20% rule | §2.8; §CB10-D Stage 2; q0210 |
| R14 disk waits | Exit-75 waits are "pending", never "not run"; 48-tempfail queue failures are re-queued under a new id, still pending; only Stage-2 origins turn a disk refusal into a counted unavailable unit; all dates conditional on rotation | header; §2.5; §2.8; §6 |
| R15 IV units | `iv / 100` pinned; moneyness with each trade's own `index_price`; smoke FAIL if < 99% of rows have `1 ≤ iv ≤ 400` and `index_price > 0` | §1.4; §CB10-D anchor; §CB10-F; q0200 |
| S block/combo | **Adopted:** block trades, combo legs and liquidations excluded from the smile fit; the variant with them is reported; counts in the census | §CB10-D anchor; §2.7 |
| S attribution identifiability | **Adopted:** census `cor(q − p_reg, q_RV − p_reg) > 0.9` → attribution "not identifiable", no option credit | §2.6; §2.7 |
| S series-key comparison | **Adopted:** the census reports the full series-key rule's drops beside the ±1-day rule | §1.3; §2.7 |
| S variance premium | **Declined for the primary, with reasons** (no second fitted constant in the hypothesis's own object; a haircut rescales the slope but cannot create one); **adopted as a reported variant** with `h` frozen from Deribit-only data in `[2025-07-01, 2025-10-01)` | §CB10-D anchor |
| S disclosures | **Adopted:** pseudo-levels in round-level resting depth (conservative for B1) and the end-of-life volume filter's selection | §CB10-B population, leakage; §7 risk 5 |
| S counter | **Adopted:** 1,146 (Mac working tree, 2026-10-17T15:01Z) | §0.2; §2.5; §6 |
| S CB8 calendar | **Adopted** (see R2); D gains about 120 dates and about 17 weeks; without it D1 would very likely fail GDP | §1.2; §1.3; §CB10-D MDE |
| S probe essentials | **Adopted:** §0.3.1 lists every probe request (host, path, query) and what was printed | §0.3.1 |
| S Deribit expiries at `d − 5` | **Answered:** not verified by the probes; every resolution weekday except Monday is within 3 days of a Friday weekly; Monday units depend on listed dailies; the census counts IV-fit availability by weekday, and missing ones are "unavailable (source: Deribit)" under the coverage audit | §0.3.1; §2.7; §7 risk 2 |

**Effect on counts and power.** k is unchanged: **3 fixed (D1, B1, B2) + up to 4 conditional = 3-7**; batch-Holm k1 =
3. MDEs: D1 about 0.65-1.0 in slope (GDP decides whether it runs; floor 0.30), B1 about 0.7-0.8c (was 0.6-0.7c; floor
0.5c), B2 about 1.0-1.2c on the net after the exit cost (was 0.9-1.1c gross; floor 1.0c). No floor moved. Requests: about
14,000 `net`-lane requests after `T_seal` (was about 9,200; the longer D window); disk ≤ 0.12 GB unchanged.

This is the single response round; the next review is the code-against-design freeze check.

## 11. Implementation notes (2026-10-17; appended, design text above unchanged)

**Commits.** `c439a1d` (`cb10_common.py`, `cb10_dlad.py`, `cb10_brk.py`, `scripts/run_cb10.py`, `battery2.KIND_RULES` cb10 kinds, tests
`test_cb10_dlad.py` 50, `test_cb10_brk.py` 27, `test_run_cb10.py` 27: 104 offline tests plus 1 conditional skip), `997b7d0` (test lint), `77feb26`
(rules file). Draft specs `queue/drafts/q0200_cb10_smoke.json` .. `q0212_cb10_rep_B.json` (13 files; nothing in `queue/jobs/`). The code was written
by a previous implementer session and left uncommitted; this pass checked it against the revised design (round-1 response applied), found no formula,
threshold or gate that departs from the design text, added the tests and committed.

**Rules file (written from code at `c439a1d`).**

| File | file sha256 | rules_sha256 |
|---|---|---|
| `seals/cb10_rules.json` (`cb10-rules-v1`: D and B declarations, common rules, hashed function sources, disk/exit constants) | `e0c181e694216c5fd95018087d66d050980b559b834a6d235fc57d7a06917e7c` | `2db70d9ad3e25fd431746478b21d96afdc8ccfe2b920418ae6e677dead5030bd` |

`funcs_sha256` `d81403f5d08c9ac6665dfb7db3cb983e92175606b3b3e6241ef376bd4fbaab1a`. The runner verifies the file against the code and refuses on a mismatch
(exit 2); `write_rules` never rewrites an existing different file. A change to any hashed function or declared constant needs a new rules file.

**Deviations from the design text (code matches the design except as listed; for the freeze check).**
1. `--data-dumps-cap-gb` defaults to 40 (the 2026-10-17 ops convention after the host disk was enlarged; §2.8 text says 14). Every draft passes 40. The
   cap is a hashed rules field. The free-disk guard (4.5 GB after the job's cap) is unchanged.
2. `exclusion-keys` requires `--cb9-keys-sha256` (the pinned sha256 of CB9 q0182's `exclusion_keys.csv.gz`), which the §4 draft argv omitted; the q0201 draft
   carries `FILL_...` placeholders for it and for the two `--extra-pin` CB9 frame id lists. They must be filled when q0182/q0183/q0185 have finished.
3. Coverage-audit denominator (design silent): an origin whose market has no transaction before `t` while the Data API cap was reached
   ("undeterminable (Data API truncation)") is counted in the D audit denominator as source-missing (conservative); it is not an eligible unit and is
   reported separately.
4. Testability needs at least 100 units and at least 30 clusters in the finest declared way (the design's "≥ 30 clusters" applied to the largest cluster
   count among the declared ways); the D week way follows §2.3's small-G rule (CR1 / CR2 + Webb / leave-one-week-out).
5. D1's independent-price placebo takes the smaller of the two differences `β̂(q) − β̂(p_alt)` (full sample and the sub-sample having `p_alt`), i.e. the
   stricter reading of "applied to the difference".
6. `RV_MIN_RETURNS = 150` of the 167 hourly returns for `q_RV` (design silent); units without `q_RV` stay in D1 and drop only from the attribution.
7. The haircut constant `h` pools both assets over `[2025-07-01, 2025-10-01)`; reported variant only.
8. B's 30-minute robustness mark is the last transaction at or before `t_b + 30 min` with time ≥ `t_b + 22.5 min` (the 2 h rule's 75% scaled).
9. The Stage-2 outcome sweep (`outcome_sweep`, run inside each `dlad-live` tick) and the 2-day grace after `T10_D2_end` are implementation choices for
   getting guarded outcomes; the sweep writes only guarded files.
10. Stage-2 `rep` trial lines carry `data_role` `prospective_post_freeze` with `evidence_role` `exploratory_historical` (as CB9 item 8).

**Open items for the freeze check.** (a) Fill the q0201 placeholders. (b) `scripts/oracle/crontab.txt` is not touched here: the two cron lines for q0210 are
added only after a D1 advance (§CB10-D Stage 2). (c) Deribit history paging, `iv` percent range and the ladder rule-text flags are verified only by q0200
(no network was used in this pass); the flags were written from live out-of-window events at rules time (`dl.FLAG_SOURCE`). (d) GDP and the D coverage
audit decide whether D1 runs; their thresholds are the design's and untouched. (e) Tests use synthetic fixtures; no real Polymarket, Deribit or
Gamma payload was exercised.

**Tests (what they cover).** Rules-file determinism, tamper and no-overwrite; refused roots, run ids and reads; net-lane jobs refuse before `T_seal` and
smoke does not; declared-argument refusals; disk guard exit 75 (data-dumps cap and free-disk) including through the CLI; missing smoke / census
inputs; freeze, trigger and write-once refusals; `dlad-live` ET clock across 2026-11-01 and exit 0 after `T10_D2_end`; the digital against a numerical
call-spread derivative, interpolation, the 3-day rule and the ATM fallback; per-trade moneyness, percent iv, block/combo/liquidation exclusion and the
`< t` rule; `p`, `p_reg` (separate earlier transaction, ≥ 5 min apart) and `p_alt` windows with boundaries; label order; the series-date ±1-day rule;
transaction aggregation; the Gamma whitelist (forbidden-field fixture, end-to-end `dlad_frame` run on a fake transport: no forbidden field, wallet,
side or hash in any written file; `outcomePrices` only in the guarded file); census no-outcome guard, 60% / 90% rules, GD, GDP on fixtures with known
answers; D1 regressor and target prices, independent-price placebo (binding), attribution, staleness; B level tables, episode detection (first crossing,
equality, 24 h memory, spacing, mutual exclusion, span), VWAP10 / M2h, maker not-posted / trade-through / size cap / exit cost, frozen per-pair
weights, GB / GB2 / audit, label-swap placebo, worst-case missing marks, cascade label, B2 route gate and pseudo attribution; HOLDOUT refusal; the
MDE > 1.0 gate writing the counted p = 1 line; batch-Holm k1 = 3; trial lines counted through `battery2`.

## 12. Freeze check (2026-10-17) and fixes

Independent code-against-design check by `science-reviewer` of the CB10 implementation. Verdicts: q0200 GO_WITH_CONDITIONS, data jobs
GO_WITH_CONDITIONS, analysis NO_GO until the fixes below. All fixes are in the code commit `ac24e68`; the rules file is regenerated as
`seals/cb10_rules_v2.json` (v1 `cb10_rules.json` is kept unchanged and superseded). No threshold, floor or formula was changed other than as stated.

### 12.1 Amendment (design change, 2026-10-17): mutual exclusion is backward-looking only

**What changed.** §3 (CB10-B) says the 60-minute real/pseudo mutual exclusion drops both members of a pair. The implementation now drops only the
LATER episode of each real/pseudo pair within 60 minutes (the earlier one is kept); simultaneous crossings (same timestamp) are still both dropped.

**Written scientific justification.** The old rule looked ahead: a real break was removed when a pseudo crossing followed it within 60 minutes. A real
break that continues by >= 3c (the pseudo level sits 3c from the round level) therefore crossed a pseudo level and was dropped, which selects
AGAINST continuation among real episodes. The pseudo arm has no symmetric loss (a pseudo crossing followed by a real crossing is dropped only in
the sense that real continuation is not required there), so the selection was asymmetric between arms and biased B1 (and the real arm of B2)
upward (reversal looks larger when continuations are removed). The label-swap placebo cannot detect it because it permutes labels after selection.
A backward-looking rule uses only information available at the episode time (is there an earlier episode of the other arm in the previous 60
minutes?), so selection is causal and symmetric. Regression tests: `test_mutual_exclusion_is_backward_looking_keeps_continuing_real_break`
(the continuing real break is kept; the old condition holds for it; a pseudo crossing earlier than a real one drops the later real episode).

### 12.2 Other fixes

| # | Fix |
|---|---|
| 2 | Stage-2 `k` counts tests triggered, not advances: a D1 advance triggers D1-rep and D2 and adds 2; B1 and B2 add 1 each (`STAGE2_TESTS_PER_ADVANCE`). The Stage-2 alpha is `0.05 / k`; D1 alone gives k = 2. Tests: `test_stage2_k_d1_advance_counts_two_tests`, `test_stage2_k_is_derived_and_fixed`. |
| 3 | Independent-price placebo requires `testable` for the `p_alt` subsample (design §2.3: unknown never counts as met). An untestable placebo means D1 cannot advance (binding). Test: `test_d1_untestable_independent_price_placebo_cannot_advance`. |
| 4 | D2 +0.5c robustness applies to the SAME trades (same token, recorded ask + 0.5c, fee recomputed; no re-selection by the 0.04 edge filter): `d2_trade_same`. Test: `test_d2_cost_robustness_applies_to_same_trade_without_reselection`. |
| 5 | `--d1-result-commit-epoch` is required for `dlad-live` (argparse) and for the D `rep` window (`_stage2_window` refuses without it); no fallback to the results file's `written_epoch`. q0210/q0211 drafts carry the placeholder `TODO-COORDINATOR-d1-commit-epoch`. Test: `test_d1_result_commit_epoch_is_required_no_written_epoch_fallback`. |
| 6 | q0202 per-item failure cap (`MAX_ITEM_ATTEMPTS` = 3, mirroring `brk_prints`) for the per-date Gamma frame, the series-date lookup and the per-market prints; a capped unit is labelled unavailable (source) and never retried (date: no rows, `unavailable_source` reason; lookup: all candidates missing, which stalls as disjointness unverified; prints: no origin rows, `unavailable_source`). Test: `test_dlad_frame_per_date_failure_cap_marks_unavailable`. |
| 7 | Drafts: q0201, q0203, q0204 gained `repeat` blocks (completion or declared stall status); q0211 depends on the queue job q0208 (q0210 is a cron line) with the in-code NotNow gate (T10_D2_end + 2 d); q0212 also depends on q0208. |
| 8 | A network give-up in the smoke (`TransientApiError`, raised for failed ladder / live-flag windows) exits 75 NotNow and writes nothing instead of a permanent write-once FAIL. A capped window remains a definitive failure. Test: `test_smoke_network_give_up_is_exit_75_and_writes_nothing`. |

### 12.3 Should-fix items

- **Truncation label.** The truncation label ("unavailable (source: Data API truncation)") depends on post-t trading (whether the oldest reachable print
  is older than t - 180 min) and so is not independent of the outcome path; its share is capped at 10% by the 90% coverage audit (§2.7). The census
  now reports eligible and truncated counts by moneyness tercile of the strike (`truncation_by_moneyness`).
- **D1-rep and leave-one-week-out.** A D1-rep that fails the leave-one-week-out sign rule is labelled "not replicated (leave-one-week-out sign rule
  failed)", not "not testable".
- **Sports stratum.** The sports stratum (excluded from primary, `CB10_SPORTS_IN_PRIMARY = false`) is reported descriptively: the census gives
  sports market counts by split (`sports_stratum`); no sports test is run.
- **B1 weights.** B1 weights `w_L = n_L / sum n` are NOT renormalised after a pair is zeroed (< 30 real or < 30 pseudo episodes); this is
  conservative (it shrinks the weighted statistic) and is a design statement as implemented, as already stated in the census text.
- **B replication guard.** `rep --family B` requires `--b-results-sha256`, the sha256 of the committed Stage-1 `results_B.json`, and refuses (HOLDOUT
  stays closed) on a mismatch. The q0212 draft carries the placeholder `TODO-COORDINATOR-sha256-of-committed-results_B.json`.
- **Comment fix.** The `cb10_common.py` disk comment said 14 GiB; the convention is 40 GiB (ops-only per `36d908f`).

### 12.4 Reviewer rulings recorded

| Item | Ruling |
|---|---|
| Audit denominator (undeterminable truncation units count as source-unavailable) | Accepted: conservative; recorded in §2.7 |
| `RV_MIN_RETURNS = 150` | Accepted |
| Stricter placebo reading (unknown is not met) | Accepted, with fix 3 |
| 30-minute mark | Accepted |
| Stage-2 trial-line roles | Accepted |
| Data-dumps cap 40 | Accepted as ops-only per `36d908f` (the design text's 14 is unchanged) |
| >= 30 clusters testability | Accepted |

### 12.5 Hashes (2026-10-17)

- Code commit `ac24e68`; rules commit `f26cb7a`.
- `seals/cb10_rules_v2.json`: file sha256 `5ee0ea230de279dfe11f8d1d29c520ede3a50da0bb06db2b15c9f4e19fc40c8c`; `rules_sha256`
  `d422cc701b1494fcaa1cb1c67df3e82ed1eba8a1cde90a884aedf3438237b093`; `funcs_sha256`
  `aff1f1c8d0c0561ee725c6476978d9bf2473ea2dffc8aad0a319e1a67b2e4ee8`. (v1 `rules_sha256` `2db70d9a...` is superseded.)
- Source files at `ac24e68` (sha256): `cb10_common.py` `3f2fc805...c250c`, `cb10_dlad.py` `357d70f4...c0c7`, `cb10_brk.py` `0c48bef7...d53d`,
  `scripts/run_cb10.py` `d3e0e8f7...5af`.
- Drafts q0200..q0212 now reference `cb10_rules_v2.json`; placeholders for the coordinator: `TODO-COORDINATOR-d1-commit-epoch` (q0210, q0211),
  `TODO-COORDINATOR-sha256-of-committed-results_B.json` (q0212), and the q0201 FILL_ pins.

**Open items.** The design text still says 14 GiB (ops convention 40); §2.7 text to be amended with the audit-denominator ruling at the next
design edit; the D-census sports and truncation reports are counts only.
