# Creative batch 11 (CB11): proposer clocks, political long-horizon underconfidence, attention without news

`evidence_role: exploratory_historical` (CB11-W, CB11-P, CB11-A Stage 1 and Stage 2, all on rows before 2026-10-01) /
`prospective` (Stage P registrations, post-freeze only) | status: **DRAFT-REVISED after challenger round 1; code and
code-against-design freeze check next; not frozen.** Drafted 2026-10-17 20:50 UTC+1 (2026-10-17T19:50Z) by the CB11
design pass (`8b376d7`); round-1 response 2026-10-17 21:04 UTC+1 (§9-§10). Every round-1 change tightens or clarifies;
no floor, threshold, gate, alpha or cap was relaxed. Nothing has been fetched for CB11 beyond the 32 counts-only
feasibility requests in §0.3. No CB11 quantity has been computed: no wait, no outcome, no price excess, no continuation.

This file turns three round-4 ideas from `CREATIVE_HYPOTHESES_2026-10-18.md` (CH85, CH88, CH97) into declared,
falsifiable tests, and records why the other round-4 ideas the brief named (CH81, CH86, CH94, CH95, CH96, CH98) are not
in this batch. It follows `CREATIVE_BATCH_10.md` (CB10) and `CREATIVE_BATCH_9.md` (CB9) in structure and rules. "As
CB10 §x" means that rule applies unchanged, including its challenger-round fixes; CB4 amendment A-C1 governs the day
cluster way.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades. Every P&L is a paper rule at recorded or declared prices.
- Test tables bind only once the CB11 declaration hash is committed (`model_specs/cb11_v1.json`, the CB11 freeze), after
  a `science-reviewer` challenger round (§8) and a code-against-design freeze check. The fetch rules (frames, seeds,
  splits, exclusion rules, entity rule, origin clocks, stored fields) are fixed in `seals/cb11_rules.json` before the
  first CB11 data request (q0221).
- **Designed to run before `T_seal`.** Unlike CB8-CB10, no CB11 object is bound to the 2026-10-22T00:00Z `T_seal` lane.
  CB11-W's Stage 1 reads only files already on the host (§1.1); CB11-P and CB11-A need small keyless fetches that may
  use the `net` lane while it is idle. Every CB11 `net` job has priority 25-29, **below every CB6-CB10 job and every
  `T_seal`-bound fetch** (q0081/q0082 h7, q0120b), so it starts only when nothing of theirs is runnable. If code or the
  freeze slips past `T_seal`, CB11 jobs queue behind CB6-CB10 with no rule change. No CB11 historical row lies at or
  after `T11_hist_end` = 2026-10-01T00:00Z, so CB11 never touches the J4-R window `[10-16, 10-21)`.
- **Queue ids q0220-q0239, one id per job, no letter suffixes** (checked free in `queue/jobs/` and `queue/drafts/` at
  drafting). Specs are drafts **in this document only** (§4). Nothing is created under `queue/` until code, tests and
  the freeze check exist.

## 0. Summary, selection and scope

| Rank | Family | Hypothesis | Counted tests | Stage 1 data | Stage 2 data | Queue ids |
|---|---|---|---|---|---|---|
| 1 | **CB11-W** whitelisted-proposer clocks (CH85) | after a market's scheduled end, the wait until it closes (proposal by one of 37 whitelisted proposers + 2 h liveness) is forecastable from schedule features known at the end (hour, weekday, placeholder end, category, recent category lag) at least 20% better than a category-median baseline and 10% better than a rolling recent-lag baseline (W1, round 1); restricting the decided carry to predicted waits ≤ 6 h pays after fees, the tail and a 60 s entry latency, in a capacity-capped capital pool (W2) | W1 (forecast), W2 (economic) | **host frames already on disk** (`h2_main`, `h3_power` `frame.csv.gz`, metadata only) + a censoring count and a small Data API print fetch | the same frames' sealed later window (W1-rep) + sealed print sample (W2-rep) | q0220-q0224, q0231, q0232, q0235 |
| 2 | **CB11-P** political long-horizon underconfidence carry (CH88) | in politics-tagged binary markets, the favourite priced 0.60-0.85 at 30, 60 or 90 days before the scheduled end resolves YES more often than priced (P1, mean excess ≥ 3c); buying it at a declared ask and holding to resolution pays after fees (P2) | P1 (calibration excess), P2 (economic) | fresh `h11_pol` fetch (Gamma, CLOB `prices-history`, Data API), scheduled ends `[2024-07-01, 2026-01-01)` | the same fetch, sealed later ends `[2026-01-01, 2026-09-01)` | q0220, q0221, q0225, q0226, q0230-q0231, q0233, q0236 |
| 3 | **CB11-A** attention without news (CH97, Wikipedia pageviews) | among markets that moved ≥ 3c on day X, moves made **without** a pageview spike of the market's named entity continue more over the next 48 h (from the first moment day X's pageviews are public) than moves made **with** one (A1, contrast ≥ 1c); a taker following the quiet moves earns after costs (A2) | A1 (mechanism contrast), A2 (economic) | fresh `h11_attn` fetch (Gamma, Wikipedia summary and pageviews, Data API), SCREEN events, days `[2026-04-10, 2026-09-24]` | the same fetch, sealed HOLDOUT events | q0220, q0221, q0227, q0229-q0231, q0234, q0237 |
| - | CB11-F data | smoke, exclusion keys, frames, prints, prices, pageviews, seals, census | none | | | q0220-q0231 |

**Counted: 6 fixed (W1, W2, P1, P2, A1, A2) + up to 6 conditional (W1-rep, W2-rep, P1-rep, P2-rep, A1-rep, A2-rep) =
6-12** (§2.5). Budget fixed now; no CB11 test is added after any CB11 read.

### 0.1 Queue id mapping (one id per job)

| Id | Job | Family | Earliest commit |
|---|---|---|---|
| q0220 | `cb11_smoke` (counts only: frame files and column whitelist; Gamma politics paging on 2 out-of-window weeks; `prices-history` at 90 d on 2 out-of-window markets; Data API newest-first reach on 2 out-of-window markets; Wikipedia summary and pageviews on 3 fixed articles with a last-published-day check; Managed OOV2 address pin attempt) | F | after `seals/cb11_rules.json` and smoke code exist (`cpu` lane, ≤ 40 requests) |
| q0221 | `cb11_exclusion_keys` (ids of every sampled or sealed set on the host + committed seal copies; Gamma lookups for missing event/series keys) | F | after q0220 PASS |
| q0222 | `cb11_w_frame` (W units from the two frames: whitelisted columns, key drops, splits, features; W_hold listing sha256; outcomes to the guarded file) | W | after q0221 (`cpu` lane, no network) |
| q0223 | `cb11_w_prints` (Data API newest-first prints for the seeded W2 SCREEN and HOLDOUT samples, aggregated to transactions in `[t − 6 h, t + 6 h)`; HOLDOUT written sealed) | W | after q0222 |
| q0224 | `cb11_w_censoring` (round 1 item 2: one Gamma `closed=false` count per seeded frame window, ≤ 300 requests; censored share for gate GWC) | W | after q0222 |
| q0225 | `cb11_pol_frame` (Gamma frame of politics and control markets, whitelisted fields, key drops, seeded samples, out-of-time split; outcomes guarded) | P | after q0221 |
| q0226 | `cb11_pol_prices` (CLOB `prices-history` per market x horizon; Data API activity check; HOLDOUT written sealed) | P | after q0225 |
| q0227 | `cb11_attn_frame` (Gamma frame, entity rule, Wikipedia summary types, seeded sample, event split, audit sample file) | A | after q0221 |
| q0228 | reserved (the entity-map audit is a repo step by a `science-reviewer` agent, §CB11-A; no queue job) | A | - |
| q0229 | `cb11_attn_data` (pageviews per canonical title; Data API prints aggregated to transactions; HOLDOUT written sealed) | A | after q0227 and the committed audit labels |
| q0230 | `cb11_seal` (W2 prints HOLDOUT listing sha256; seal copy; seal-time drops; re-check b2: W seals alone) | W | after q0223 |
| q0231 | `cb11_census_W` (counts only; gates GWC, GW, GW2; W2 coverage audit; MDEs; round 1: per-family census) | W | after q0222, q0223, q0224 and q0230 (W seal) |
| q0232 | `cb11_screen_W` (W1, W2 Stage 1) | W | after the CB11 freeze |
| q0233 | `cb11_screen_P` (P1, P2 Stage 1) | P | after the CB11 freeze |
| q0234 | `cb11_screen_A` (A1, A2 Stage 1) | A | after the CB11 freeze |
| q0235 | `cb11_rep_W` (W1-rep, W2-rep on sealed W_hold) | W | only if W1 or W2 advanced |
| q0236 | `cb11_rep_P` (P1-rep, P2-rep on sealed HOLDOUT ends) | P | only if P1 or P2 advanced |
| q0237 | `cb11_rep_A` (A1-rep, A2-rep on sealed HOLDOUT events) | A | only if A1 or A2 advanced |
| q0238 | `cb11_seal_PA` (P and A HOLDOUT listings sha256; seal copies; seal-time drops; re-check b2). The uncounted W on-chain proposer variant (only if q0220 pins the Managed OOV2 address) lost this id and takes a new one if it is ever run | P, A | after q0226, q0229 |
| q0239 | `cb11_census_PA` (counts only; gates GP, GPP, GA0, GA; coverage audits; MDEs; new in round 1) | P, A | after q0226, q0229 and q0238 (P and A seals) |

### 0.2 Selection and scope

**Ranking rule.** As CB10 §0.2 (value of information x feasibility within about a week on keyless data), plus two
CB11-specific preferences from the brief: (a) originality and a plausible money mechanism, (b) a SCREEN stage that can
run **before** 2026-10-22 on data already on the host or fetchable now, because the queue is starving until `T_seal`.
Families that depend on the Data API `side` field (whose truth CB9-S0 audits only after `T_seal`) or on wallet identity
(null repeatedly) were ranked down.

**What the drafting session read or computed (2026-10-17T18:50-19:50Z).**
- Committed documents: CLAUDE.md, AGENTS.md, round 4 (§0-§4, CH81, CH85-CH88, CH94-CH98), CB10 §0-§8, CB9 §0, the
  queue README, the ledger tail, `HISTORICAL_ML_DEV.md` (frame and endpoint facts), `EXTERNAL_NEWS.md` (GDELT verdict,
  pageviews fallback), `RESOLUTION_DEV_STUDY.md` §1, the calibration study C1 ledger entry, CB1 §2.3 (tail gate) and
  the CB1-A census/result lines.
- Prior-work search: `grep` of `CREATIVE_BATCH_*.md` and `EXPERIMENT_LEDGER.md` for CH81, CH85, CH86, CH88, CH94-CH98
  finds only drop or "not considered" lines (CB9 §0.4, CB10 §0.4); no CB, E, HB or SB test has used the post-end wait
  (`closedTime − endDate`) as a target, Wikipedia pageviews as a feature, or politics x 30-90-day origins. Overlaps with
  earlier objects are disclosed per family (§CB11-W, §CB11-P, §CB11-A).
- Code (read only): `external_news.derive_query` (entity rule), `fetch_pageviews` (PIT rule: day D usable from D + 36 h),
  `cb9_sign.keccak256` (topic hashing for the probe).
- `battery2.cumulative_count()` on the Mac working tree (`battery2-count-v1`) = **1,156** at 2026-10-17T19:5xZ. The
  latest ledger entry stating a cumulative count (CB10 draft) says 1,141. **Round 1:** the committed
  `docs/research_lab/trials.jsonl` at `e721331` (unioned with the host since `15ec365`) gives **1,156** at
  2026-10-17T20:04Z; this is the count used in §2.5. The host union step runs before every counting CB11 job and
  records the post-union value.
- **Disclosed drafting read (round 1 item 2).** The host counts below read the frames' `closed` and `uma_status`
  columns in aggregate (the 96% `resolved` share). No per-unit status was linked to any wait, outcome or price; from
  round 1 on, `uma_status` is a guarded column (§1.4).
- Host state (read only, 19:4xZ): no queue job running; 9 queued, 2 in `retry_wait` (q0120b, q0180); `/` 89 GB with
  **58 GB free**; data-dumps **16 GiB** (convention cap 40); MemAvailable about 4.4 GB. History runs on disk: `h1_first`
  (64 MB), `h2_main` (403 MB), `h3_power` (657 MB), `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_era`,
  `h7_cb4_series`, `h8_geo`, `h8_tail`, `h8_tail_b`, `h8_text`. Complete-universe snapshots: 83 captures, 4.8 GB.

**Host counts (no external request; metadata columns only; no outcome, price or wait computed).**
- `h2_main/frame.csv.gz` 254,379 rows, `h3_power/frame.csv.gz` 276,378 rows; both carry `end_epoch`, `close_epoch`,
  `start_epoch`, `fee_category`, `neg_risk`, `event_id`, `uma_status` (h3 also `question`, `topic`). Rows closed after
  their scheduled end with the end in `[2025-10-01, 2026-10-01)`: **307,658 distinct markets** (15,888 in both frames);
  excluding sports and crypto, about 26k (h2, by `fee_category`) and 46k (h3, by `topic`, ends from 2025-09-01). `uma_status` is `resolved` for 96% of rows.
- h3 frame, politics topic with scheduled life ≥ 60 days: 427 markets in 56 events (the frame is a 6.25% time sample
  of end dates, so this is not the universe; probe 5 is).
- h3 frame, non-sports, non-crypto, non-weather questions with end ≥ 2026-04-01: 9,768; `derive_query` returns an
  entity for 98.7%; 1,938 distinct first entities.

### 0.3 Feasibility probes (counts only, 32 requests, nothing stored)

Scripts lived in `/tmp/cb11probe/` (not committed); no output was written in the repo or in data-dumps. No outcome,
outcome price, print price, wait or volume value was computed or printed, with one disclosed exception: probe 1
printed the `endDate`, `closedTime` and `umaEndDate` strings of two markets ending 2026-09-10 as a field-format check.
Scheduled ends on 2026-09-10 and 2026-09-11 (probes 1 and 3) are therefore **excluded from every CB11 unit set by
rule** (§1.2; they already lie outside W_hold). All GETs carried `User-Agent: arepo-research-probe`; 4 requests were
read-only JSON-RPC POSTs to public Polygon endpoints.

| # | Request(s) | Finding |
|---|---|---|
| 1 | 1 Gamma `/markets?closed=true&limit=3&end_date_min=2026-09-10T00:00Z&end_date_max=2026-09-10T23:59Z&volume_num_min=50000` | 78 keys per market, including `questionID`, `resolvedBy`, `umaEndDate`, `umaResolutionStatus`, `umaResolutionStatuses` (a history list), `closedTime`, `automaticallyResolved`, `umaBond` (500), `umaReward` (5). In both printed markets `closedTime` equals `umaEndDate` to the second: **Gamma's close time is the UMA settlement time** (proposal + liveness), so the post-end wait is readable without the chain |
| 2 | 1 `eth_blockNumber` + 3 `eth_getLogs` (topic `ProposePrice(address,address,bytes32,uint256,bytes,int256,uint256,address)`, no address) on `polygon.drpc.org` (2,000 and 200 blocks) and `polygon-bor-rpc.publicnode.com` (1,000 blocks) | drpc 400 ("ranges over 10000 blocks are not supported on free plan" even for 200 blocks); publicnode refuses topic-only filters ("specify an address"). **The on-chain proposer identity needs the Managed OOV2 contract address pinned first.** W does not depend on it (row 1); the chain decode is an uncounted variant (q0224) |
| 3 | 1 Gamma `/markets?closed=true&limit=100`, ends 2026-09-11, volume ≥ $5k | `resolvedBy` takes **2 distinct values** in 100 markets (top share 0.67): it names the adapter contract, not the proposer. `automaticallyResolved` true in 100/100; `umaEndDate` present in 100/100 |
| 4 | 1 Gamma `/tags/slug/politics` + 3 `/markets?closed=true&tag_id=2&limit=500` (Nov 2025, Mar 2026, Jun 2026) | politics tag id **2**; the server caps `limit` at **100** per page |
| 5 | 10 Gamma pages `/markets?closed=true&tag_id=2&end_date_min=2026-03-01&end_date_max=2026-04-01&limit=100&offset=0..900` | **≥ 1,000 closed politics markets ending in March 2026** (the 10-page probe cap was hit), **≥ 510 with scheduled life ≥ 60 days in ≥ 166 events** (280 events overall). A politics frame over 18 months is several thousand long-life markets (§CB11-P power) |
| 6 | 12 Wikimedia `per-article/en.wikipedia/all-access/user/<title>/daily/2026090100/2026101700` for 12 seeded entities from the h3 frame count above | 6 x 200 (45 days each), 4 x 404, **2 x 429** (rate limit after about 10 unpaced requests). Latest published day at 19:5xZ on 10-17 was **2026-10-15**: day 10-16 was still unpublished **≥ 19.8 h after its end**, so `fetch_pageviews`' 12 h lag assumption is contradicted (§2.2 uses 48 h). Two of the six hits were generic articles ("Invasion", "IPO"): the entity map needs a type filter and an audit (§CB11-A) |

### 0.4 Selection decisions

| Idea | Decision | Reason |
|---|---|---|
| **CH85** whitelisted-proposer clocks | **include (W), priority** | Original (the whitelist since Aug 2025 turns the wait into a modelled object; no AREPO test has used the wait as a target), keyless, and **Stage 1 runs on frames already on the host** (probe 1: `closedTime` = UMA settlement time; host counts: tens of thousands of non-sports markets open at their scheduled end inside the whitelist era). CB9 dropped it because its carry "needs fresh decided markets"; W2 gets them from a small print fetch on the frames' markets. Overlap disclosed: CB1-A1 (post-end decided carry) was "not testable" (57 units, counted p = 1), not a null; CB1-A2 (pre-end 0.95-0.99 favourites, −1.05c) is a different object |
| **CH88** political long-horizon underconfidence | **include (P)** | The most direct money mechanism in the list (a one-leg favourite carry) with an external prior (Le 2026). Disjoint from every prior calibration object: C1 (1 d and 7 d, all categories, politics too small, 30 d unusable), PX4 (mid ≥ 0.85 at 24 h), CB1-A2 (0.95-0.99), T5 (1-7 d). CB9's "few resolution-week clusters" reason is overcome by an 18-month window (probe 5). Originality is low (N 2) and is stated |
| **CH97** attention without news | **include (A)** | The only round-4 idea that brings a new **external information source** (never tested in AREPO; GDELT failed as a source, `EXTERNAL_NEWS.md`), which is the programme's core question. Side-free and wallet-free by design. Honest weakness: pageviews publish ≥ 20 h after the day ends (probe 6), so the feature acts 2-3 days after the attention day, which shrinks the money route; A is therefore written as a moderation-of-drift test with a taker economic check, not as the same-day maker filter CH97 imagined (§CB11-A) |
| CH81 joint-event implied correlation | dropped | No new justification since CB9: the census floor (≥ 10 rule-identical joint events with both marginals listed) is very likely unmet (3 seen); a 2x2 with three free parameters gives a descriptive at best. Re-entry: a census over ≥ 3 weeks of captures showing ≥ 10 qualifying events |
| CH86 tick-change vacuums | dropped | Needs event-located pmxt L2 hours (+1/+30 min depth); 2 h captures cannot see a 30-minute recovery, and pmxt ingress competes with CB9's q0186 (180 GB) after `T_seal`. Re-entry: reuse of CB9-K/D pmxt hours if the census shows ≥ 200 tick changes inside them, or a live per-market tick monitor |
| CH94 account-exit sweeps | dropped | Needs the Data API `side` field (sells) and wallet identity; CB9-S0 has not reported, and wallet-based effects have been null repeatedly (WA1-WA8, r2 wallet age, Q1). Re-entry: after S0, with its measured agreement |
| CH95 theme-basket buys | dropped | Same `side` dependence; a wallet-family idea (WA nulls); the frozen theme map plus case-catalogue exclusion needs a hand audit; no fetch-free version |
| CH96 funding-path class | dropped | Wallet-family (age nulls three times), needs a frozen public label list for exchange and bridge addresses and on-chain reads per wallet (C 3); maker step-aside value is small |
| CH98 redemption-cash days | dropped | Captures with `open_interest` exist only since 10-11, and 10-16..10-21 is the sealed J4-R window, so about 5 usable days; the unit is a category-day, so power is nil now. Re-entry: after ≥ 90 days of sidecar captures (about 2027-01) |

**Sports and categories.** `CB11_SPORTS_IN_PRIMARY = false` (a parameter, as CB8-CB10). In W, sports and crypto
(`fee_category` sports / crypto, which includes Chainlink-settled Up/Down markets) are reported, uncounted strata. P is
politics by construction; its control set excludes sports, crypto and weather. A excludes sports, crypto, weather, Pyth
dailies, crypto strike ladders and Up/Down markets (tags plus `CB1_UPDOWN_RE`). Category stays a parameter.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB11 | Evidence ceiling |
|---|---|---|---|
| `history/h2_main/frame.csv.gz`, `history/h3_power/frame.csv.gz` (on host; sha256 pinned in the rules file) | sampling frames of the worn h2 and retired h3 runs; **their sampled markets** were screened (ML, HB1, HB1-R, CB1); the wait target was never computed | **W1, W2 population (metadata columns only)**; `outcome_prices` and `uma_status` routed to a guarded file used only by W2 (round 1 item 2) | L1 (reused frame, fresh target; disclosed) |
| `history/h11_wprints` (**new**, q0223): transactions `[t − 6 h, t + 6 h)` for 4,000 SCREEN + 3,000 HOLDOUT W markets | none | W2 entry prices | L1 / L2 (sealed later window) |
| `history/h11_pol` (**new**, q0225/q0226): politics and control frames, per-(market, horizon) `prices-history` value, activity flags; outcomes in `outcomes_guarded.csv.gz` | none (key-disjoint from every sampled set, §1.3) | P1, P2 | L1 / L2 (sealed later ends) |
| `history/h11_attn` (**new**, q0227/q0229): frame, entity map (title, type, description), daily pageviews, transactions (YES-terms VWAP, size, time) | none | A1, A2 | L1 / L2 (sealed holdout events) |
| `h1_first`, `h2_main`, `h3_power` panels, prices, trades, results | worn / retired | **not read**, except their market-id lists for exclusion | - |
| `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, `h7_cb4_*`, `h8_tail`(`_b`), `h8_text`, `h8_geo`, CB8-CB10 data, `cross_venue/` | sealed or batch-owned | **not read** (runner refuses), except id columns for exclusion keys | - |
| `snapshots/`, `trade_samples/`, `live_trades/`, `book_sweeps/`, all `cb*_extract/` tables | live stores, E-series, CB1-CB8 | **never read by any CB11 Stage 1 or Stage 2 path** (Stage P may name them in its own registration) | - |

**Reuse disclosure (W).** W reads two frames that earlier runs sampled from. Only metadata columns are read; the
markets those runs actually sampled (and every other sampled or sealed set) are dropped by key (§1.3). No earlier test
read a wait, and no W feature is an earlier test's output. The reuse is counted in the sense of the M3 rule: W1 and W2
are new tests on a reused frame, labelled "reused frame, fresh target" in every result line.

### 1.2 Dates (declared; UTC unless stated)

| Name | Value | Meaning |
|---|---|---|
| `T11_draft` | 2026-10-17T19:50Z | this draft; no CB11 quantity computed |
| `T11_hist_end` | 2026-10-01T00:00Z | no CB11 historical row (end, transaction, pageview day, resolution) at or after it |
| `T_seal` | 2026-10-22T00:00Z | not binding for CB11 (§0 header); CB11 `net` jobs yield to every `T_seal`-bound job |
| W_fit | scheduled end `[2025-10-01, 2026-02-08)` | W1 model and baseline fit; every fit target is determined (capped at 21 d) by 2026-03-01 |
| W_screen | scheduled end `[2026-03-01, 2026-07-01)` | W1 and W2 Stage 1 |
| W_hold | scheduled end `[2026-07-01, 2026-09-10)`, sealed | W1-rep (model refit on ends `[2025-10-01, 2026-06-09)`), W2-rep. Ends after 09-10 are unused: frames were fetched from 2026-10-11, and a market still open then would be missing (selection on the target) |
| W excluded dates | ends on 2026-09-10 and 2026-09-11 | probe rows 1 and 3 touched those dates (already outside W_hold) |
| P SCREEN | scheduled end `[2024-07-01, 2026-01-01)` | P1, P2 Stage 1 |
| P HOLDOUT | scheduled end `[2026-01-01, 2026-09-01)`, sealed | P1-rep, P2-rep (out-of-time) |
| P origins | `t_h = end − h`, `h ∈ {30, 60, 90}` days, at the scheduled end's clock time | price from `prices-history` |
| A window | attention days `X ∈ [2026-04-10, 2026-09-24]`; transactions in `[2026-04-01, 2026-10-01)`; pageviews in `[2026-01-01, 2026-10-01)` (round 1 item 9: 30-day history rule) | SCREEN / HOLDOUT by Gamma event hash `arepo-cb11-attn-split`, 50/50, at frame time |
| A origin | `t = X + 3 d 00:00Z` (day X's pageviews usable 48 h after the day ends, §2.2) | target window `[t, t + 48 h)` |

### 1.3 Sealed and untouched data (named)

- **Refused roots.** `run_cb11.py` refuses every root in the last three rows of §1.1 (except id-column readers for keys,
  which use a field-restricted accessor). It writes only under `research_lab/creative_batch11/`, `history/h11_wprints/`,
  `history/h11_pol/` and `history/h11_attn/`.
- **Exclusion keys (q0221).** Union of: (1) `h8_tail_b/exclusion_keys.csv.gz` (the latest committed-era key file on the
  host, sha256 pinned); (2) market ids of every **sampled** set on the host: `h1_first`, `h2_main` and `h3_power` sampled
  markets (their panel/prices market lists), `h5_cb1/sample.csv.gz`, `h5_cb1_ladders` events, `h6_weather` events,
  `h7_cb4_era`/`h7_cb4_series` frames (these frames are the sampled weather sets), `h8_tail`, `h8_tail_b`
  `sample.csv.gz`, `h8_text` and `h8_geo` frames (whole filtered pools), CB8 frames present in `creative_batch8/`; (3)
  every id in seal copies under `docs/research_lab/seals/` (including `h5_cb1_SEAL.json`, `h5_cb1_ladders_SEAL.json`);
  (4) **mandatory (round 1 item 5):** the calibration C1 sample (ends `[2026-07-13, 2026-10-04)`) and the T5 frame
  (`RESOLUTION_DEV_STUDY.md`, ends `[2025-10-11, 2026-10-04)`, 314 politics markets with outcomes seen), from their
  `sample_plan.json.gz`/`frame/` files in the `arepo-data` release. If either id list cannot be retrieved: P1-rep and
  P2-rep are labelled **"possibly touched holdout (L1, not L2)"**, A's HOLDOUT likewise if its window overlaps, and P1
  gains a binding robustness check excluding SCREEN ends in `[2025-10-11, 2026-01-01)` (the T5 overlap). Keys = market id, Gamma
  event id, `negRiskMarketID`, series id (looked up on Gamma, ≤ 50 ids per request, where a source lacks them). CB9 and
  CB10 frames do not exist yet ("absent at q0221"); **CB9/CB10 exclusion builds must add CB11's frame ids** (stated for
  their q0182/q0201 increments). If more than 2% of exclusion ids lack metadata, disjointness is "unverified" and P and A
  are "not testable", counted.
- **W key rule (a declared deviation, for the challenger; amended in §11 N2: the frames carry no `negRiskMarketID`, so W drops by market id and event id only).** W does not drop by
  series id. Sampled sets cover many daily series (weather, sports, esports), so the series rule would drop most
  scheduled classes, and the proposer schedule of a series is the mechanism W measures, not leakage: no prior test read a
  wait. The series-rule drops are not computable from the frames (§11 N2).
- **SEALED-W (W_hold).** q0222 writes the W_hold unit ids (no target) and the listing sha256; seal copy
  `seals/cb11_w_hold_SEAL.json` committed before q0231. The W loader refuses frame rows with end ≥ 2026-07-01 except in
  q0235, which verifies the seal first. W2 HOLDOUT transactions go to `h11_wprints/holdout/` (sealed by q0230).
- **SEALED-P, SEALED-A.** HOLDOUT files written to `holdout/` subdirectories with listing sha256s; seal copies
  `seals/cb11_pol_holdout_SEAL.json`, `seals/cb11_attn_holdout_SEAL.json` committed by q0230 before q0231. The census
  reads HOLDOUT file and unit counts only.
- **Outcome guards.** W: the frame's `outcome_prices` **and `uma_status`** (round 1 item 2; CB1 guarded it as an outcome
  column) → `h11_wprints/outcomes_guarded.csv.gz`, opened only by q0232 (W2) and q0235. P: Gamma `outcomePrices` and
  `umaResolutionStatus` → `h11_pol/outcomes_guarded.csv.gz`, opened only by q0233/q0236. A has no outcome
  (its target is a later transaction price). W1's target (the wait) is not an outcome of the market, but it is the test
  target: no census path computes it (unit test).
- **CB8-CB10 objects.** CB11 reads none of their data or verdicts. P and A share the 2024-2026 calendar with HB1/HB2,
  CB7-CB10 (markets disjoint by key); W shares frames with the h2/h3 runs (disclosed above).

### 1.4 Rules files

- `seals/cb11_rules.json` (v2, before q0220/q0221) is hashed in **parts** (§11 B1): part W (common + smoke + W) now; P and A rules in their own file `seals/cb11_pa_rules.json`, fixed before the first P/A request. The file fixes (W part): frame sha256s and the W column whitelist; W windows, cap, feature
  definitions and model hyperparameters; W2 sample seeds, entry rule and costs; the P frame rule (tag id 2, life,
  windows, control rule, per-event cap), horizons, band and costs; the A frame rule, entity rule (the `derive_query`
  source sha256, the stop list, the summary-type rule), pageview ratio rule, thresholds, origin clock and costs; split
  seeds; census gates; smoke criteria.
- Fetchers refuse (exit 2) on a hash mismatch. **No rule is computed from, or revised after, any W, P or A read.**
- No wallet field is read or stored by any CB11 job (no HMAC key is needed). No `side` field is read.
- **Field whitelists (as CB10 §1.4).** W reads only `market_id, event_id, fee_category, neg_risk, start_epoch,
  end_epoch, close_epoch, closed, token0, token1, condition_id` from the frames, plus `outcome_prices` and `uma_status`
  through the guarded accessor only (round 1 item 2). `closed` is used only to keep every closed row (no status filter). P and A Gamma parsers keep only `id, conditionId, question, slug, clobTokenIds, outcomes
  (labels), startDate, createdAt, endDate, closedTime` (P: for the hold length only, in the guarded file), `negRisk,
  negRiskMarketID`, event ids, series ids, tag ids, `feeSchedule`; A additionally keeps a boolean `vol_ok`
  (`volumeNum ≥ 10,000`, the number not stored). A unit test feeds a fixture with every forbidden field and asserts the
  parsed row, file and log contain none of them.

## 2. Common rules (deltas from CB10 §2)

### 2.1 Costs

| Test | Price and cost rule |
|---|---|
| W1, P1, A1 | none (forecast, calibration and mechanism tests) |
| W2 | taker entry at the token price of the **next transaction at or after `τ + 60 s`** (round 1 item 6; `τ` = the triggering transaction) + a declared half-spread `h_W = 0.5c`, capped at 1.0; fee `r·c(1 − c)`, `r` = the round-4 docs rate of the market's fee category (politics, finance, tech 0.04; economics, culture, weather, unknown 0.05; geopolitics 0; `other:zero_fees` 0), or the frame's fee field if larger; hold to the close + 1 h redemption lag; no rebate |
| P2 | taker entry at `a = p_f + 1.5c` (half of a 3.0c spread, the upper mid-band round-4 median); fee `r·a(1 − a)`, `r = max(feeSchedule.rate, 0.04)`; hold to resolution |
| A2 | taker entry at `P(t) ± 1.5c` in the move direction, exit at `P(t + 48 h) ∓ 1.5c`; taker fee at entry and exit at `r = max(feeSchedule.rate, 0.05)` |
| Binding cost robustness | W2: `h_W = 1.0c`; P2: half-spread 2.5c; A2: half-spread 2.0c per side. Each keeps net > 0 |

Every economic number in CB11 Stage 1 uses **declared, not recorded** spreads (historical books are not available
without pmxt), so W2, P2 and A2 are "modelled-cost economic checks (L1)"; recorded asks enter only in Stage P (§2.9).

### 2.2 Clocks

- **Frames (W).** `end_epoch` (scheduled end), `close_epoch` (Gamma `closedTime` = UMA settlement, probe 1). "Open at
  `t`" means `close_epoch > t`, a fact visible at `t`. `close_epoch` is otherwise used only as W1's target and as the
  hold end in W2/P2, never as a population condition, origin or feature.
- **Data API prints.** Venue `timestamp` (s), aggregated by transaction hash at fetch into (time, YES-terms VWAP, size);
  the hash is discarded. A condition at `t` uses transactions with time < `t`. **No CB11 statistic uses `side`.**
- **CLOB `prices-history`.** A point is known from stamp + 600 s (h2 rule); the price at `t` is the last point with stamp
  + 600 s < `t` and age ≤ 24 h, else "unavailable (no price)".
- **Wikimedia pageviews.** Daily stamps `YYYYMMDD00`. Day X is usable at `t ≥ X + 1 d + 48 h`. The 48 h is declared from
  probe 6 (day 10-16 unpublished ≥ 19.8 h after its end) with margin; the smoke records the last published day at its
  run time and **fails** if that day is more than 48 h old (the rule would then be too short). If the smoke fails on
  this check, the lag moves to 72 h before the freeze (outcome-blind; recorded) and A's origin to `X + 4 d`.

### 2.3 Uncertainty and decision rule

As CB10 §2.3 (unweighted primary; one-sided p = max over declared cluster ways; 2,000-draw cluster bootstrap, **seed
1111**; small-G rule; A-C1 day way; top-5 drops; ≥ 100 units and ≥ 30 clusters for testability; "unknown" never counts
as met). Cluster ways: **W** UTC date of the scheduled end and Gamma event; **P** Gamma event (a neg-risk event is one
cluster) and ISO week of the scheduled end (small-G rule as CB10 for the week way); **A** Gamma event, UTC day X and
(round 1 item 10) **3-day blocks of the origin `t`** (block = ⌊(t − 2026-04-13T00Z) / 3 d⌋), because consecutive
days' 48 h target windows overlap.
- **Stage 1 (W1, W2, P1, P2, A1, A2).** Advance iff one-sided p < 0.01, the §2.4 floor is met, and every binding
  placebo, robustness check and gate holds. Batch-Holm label (one-sided α = 0.01, **k1 = 6**, fixed) reported; BY label
  (q = 0.10 over `battery2.cumulative_count()` at the run) triage only.
- **Stage 2 (reps).** One Holm at one-sided α = 0.05 over every CB11 test reaching Stage 2, each in its Stage-1
  direction; k fixed when the last Stage-1 result is final; early finishers judged at α/k. Labels: W1-rep, W2-rep
  "out-of-time replication on a sealed later window (L2)"; P1-rep, P2-rep likewise; A1-rep, A2-rep "sealed same-calendar
  holdout replication (L2)".
- **Stage P** is a separate registration for any survivor (§2.9).

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| W1 | forecast | relative MAE improvement `R_B0 = 1 − MAE_model / MAE_B0 ≥ 0.20` on log-hours (CH85's kill rule) **and** (round 1 item 7) `R_B1 = 1 − MAE_model / MAE_B1 ≥ 0.10` against the rolling recent-lag baseline B1, each with one-sided p < 0.01 |
| W2 | economic | net ≥ +0.30c per share (CB1-A floor) **and** `R_ann_h ≥ 10%` (§CB11-W) **and** (round 1 item 6) the capacity-capped single-pool simulation's annualised return in excess of a 4.5% risk-free rate ≥ 10%, and the CB1 §2.3 tail gate at the stage's α with floor 0.003 |
| P1 | calibration excess | mean favourite excess `Ē ≥ +3.0c` |
| P2 | economic | net ≥ +2.0c per share after fee **and** `R_ann − 4.5% ≥ 10%` (CB1 definition, days; excess over a 4.5% risk-free rate, round 1 optional item adopted) |
| A1 | mechanism contrast | `Δ ≥ +1.0c` (quiet minus spike continuation) |
| A2 | economic | net ≥ +1.0c per share after both legs' costs |

### 2.5 Counting (M3 rule)

- Kinds `cb11_test` (Stage 1), `cb11_replication` (Stage 2), `cb11_descriptive` (EXCLUDE: smoke, census, gates, strata,
  variants, the on-chain proposer variant, the unconditional continuation mean, the logistic calibration slope); placebo
  lines count 0. Count lines `creative_batch_11:W`, `:P`, `:A` (`n_tests`). New `battery2.KIND_RULES` entries as CB10
  §2.5; unknown kinds raise.
- **Cumulative count: 1,156** from the committed `trials.jsonl` at `e721331` (host-unioned; round 1). The draft's
  1,141 was the CB10 draft's ledger figure, now superseded.
- **CB11 adds 6 fixed tests (W1, W2, P1, P2, A1, A2) and up to 6 conditional ones (each `-rep`, triggered by its own
  Stage-1 advance).** Budget: 6-12.
- Tests behind a failed or unknown gate (smoke, disjointness, GWC, GW, GW2, GP, GPP, GA0, GA, coverage audits) are "not
  testable" or "not run" (p = 1) and are **still counted**. A job waiting on exit 75 is "pending" and produces no line.

### 2.6 Placebos and robustness (common)

Design rule as CB10 §2.6: every binding placebo names the alternative under which the test would advance; calibration
placebos are judged on the p threshold alone (floors off); 200 draws; **advance rate ≤ 1.5%**. Seeds 11101-11112.
Family-specific placebos, attributions and robustness checks are in §3. Common binding robustness for any advance:
(i) the declared cost robustness (§2.1) for economic tests; (ii) p threshold and floor hold without the top 5 clusters
of each way; (iii) sign by period (W: each calendar month of the window; P: each half of the SCREEN window; A: ≥ two
thirds of months with ≥ 100 units); (iv) unavailable units are excluded and counted by label, never imputed; a test
whose available share of eligible units is < 60% is "not testable (availability)".

### 2.7 Pre-freeze census (counts only; q0231 for W, q0239 for P and A, round 1)

Outcome guards first; field-restricted accessors; a unit test asserts that no census path receives a wait (W1 target),
an outcome, a 48 h mark or a P&L. Features may be computed.
- **W.** Units by window, category, **frame source by window** (round 1 optional item) and end-hour; key drops by source
  (the series-rule drops are not computable, §11 N2); open-at-end share (no `uma_status` read: guarded, round 1 item 2).
  **Gate GWC (censoring, round 1 item 2):** q0224 draws a seeded 300 of the frames' 15-minute windows whose ends fall in
  W_fit ∪ W_screen ∪ W_hold (windows from the frames' `frame_partial` records), and counts with one Gamma `closed=false`
  query per window the markets with `endDate` in that window still open at query time. Censored share = Σ open / (Σ open
  + Σ frame closed rows in the same windows), per window set, with a window-bootstrap one-sided upper 95% bound (2,000
  draws, seed 11121). **If the upper bound exceeds 2% in W_screen (or in W_hold for the reps), W1 and W2 (resp. the
  reps) are "not testable (censoring)", counted.** (Sampling 300 windows instead of all about 4,000 keeps the count
  cheap; gating on the upper bound rather than the point estimate makes the sampled gate at least as strict.) W2 sample: markets with a covered print span over `[t − 6 h, t + 60
  min]`, decided units (entry rule satisfied; counts only), units in arm S (model predictions are features of the fit
  window, so S membership may be counted). **Gate GW:** ≥ 5,000 W_screen primary units over ≥ 90 end-dates and ≥ 6 fee
  categories with ≥ 200 W_fit units. **Gate GW2:** ≥ 300 decided S units in ≥ 100 events and ≥ 60 end-dates. **W2
  coverage audit:** ≥ 90% of sampled markets have prints reachable over `[t − 6 h, t + 60 min]`; FAIL → W2 "not testable
  (source limited)".
- **P.** Frame counts by month and event; key drops by source (T5 and C1 drops shown separately); eligible (market,
  horizon) units by label ("not listed", "closed before t", "unavailable (no price)", "inactive (proxy)"); units in band
  by horizon; markets with a P unit; events and ISO weeks; units flagged by the end-date rules and the election keyword
  list (§CB11-P); the liquidity stratum (terciles of the pre-origin proxy count, reported). **Gate GP:** ≥ 800 SCREEN
  markets with a P unit in ≥ 250 events and ≥ 40 ISO weeks. **P coverage audit:** ≥ 90% of eligible (market, horizon)
  units have a price (source availability). **Power gate GPP (feature-only, as CB10 GDP; round 1 item 4):** simulated
  outcomes `Y*_m = 1{Φ(Z_m) < p_f}` with `Z_m = √0.2 · W_week + √0.4 · V_event + √0.4 · ε_m` (`W_week` one standard
  normal per scheduled-end ISO week, shared by every event of that week; `V_event` one per event; `ε_m` per market; one
  `Z_m` shared across the market's horizons; loadings declared). 500 draws (seed 11120). On each draw the event-way and
  week-way cluster-bootstrap SEs of `Ē*` are computed (200 inner draws); `SD_P = max(SD(Ē*) across draws, mean event-way
  SE, mean week-way SE)` and `MDE_P1 = (z_0.99 + z_0.80) x 1.2 x SD_P`. **If `MDE_P1 > 6.0c`, P1 and P2 are "not run
  (power)", counted with p = 1.**
- **A.** Frame, entity availability (summary `standard`, pageviews present), units by cell (spike/middle/quiet x
  big/small move), events, days, SCREEN/HOLDOUT. **Gate GA0 (entity audit):** precision ≥ 80% on the 200 blind-labelled
  pairs (§CB11-A); FAIL → A1, A2 "not testable (entity map)". **Gate GA:** ≥ 1,000 quiet and ≥ 200 spike big-move
  SCREEN units in ≥ 150 events and ≥ 60 days, and ≥ 50% of frame markets with an available entity (after the round-1
  pageview rules: baseline median ≥ 50, all 9 days present, first non-zero view ≥ 30 days before X). **A coverage
  audit:** ≥ 90% of SCREEN markets have prints reachable over their in-window life; **print-coverage failures and
  pageview-unavailable units are reported by arm** (spike / quiet / middle; round 1 item 10).
- MDEs are recomputed from these counts and never used to change a floor, window or threshold.

### 2.8 Compute, network, disk and stop rules

- **Host.** 1 OCPU, about 5.6 GiB RAM shared with the collector. Queue rules as CB10 §2.8 (one job per lane, nice 19,
  `MemAvailable ≥ mem_mb + 1200`, address cap 2 x `mem_mb`, 02:45-05:30 UTC blackout for `mem_mb ≥ 500`). **No pmxt
  ingress.** Frame readers stream with `csv` (W's two frames together are about 530k rows, under 0.6 GB in memory at
  peak if held as typed arrays; the W job declares `mem_mb` 900).
- **Network** (`net` lane, priorities 25-29; ≤ 2 rps Polymarket, ≤ 1 rps Wikimedia with a descriptive User-Agent):

  | Job | Work | Requests / wall | Stored (cap) |
  |---|---|---|---|
  | q0220 | smoke | ≤ 40 | 0.001 GB |
  | q0221 | exclusion keys (Gamma lookups only for ids lacking keys; C1/T5 id lists from the release) | ≤ 400 | ≤ 0.01 GB |
  | q0223 | W2 prints, 7,000 markets, up to 4 pages each (§11 N3) | ≤ 28,000, ≤ 4 h | ≤ 0.03 GB |
  | q0224 | W censoring count: `closed=false` (gate) + `closed=true` (diagnostic) per window, ≤ 5 pages each (§11 N1/N3) | ≤ 3,000, ≤ 25 min per chunk | ≤ 0.001 GB |
  | q0225 | P frames (weekly end windows, `tag_id=2` and the control walk with `start_date_max` filters; capped windows split) | ≤ 4,000 | ≤ 0.01 GB |
  | q0226 | P prices: **10,500 markets** (4,000 + 3,000 politics, 2,000 + 1,500 control; round 1 item 11) x 3 horizons, one `[t_h − 7 d, t_h]` request each (price and activity proxy) = 31,500; Data API ≤ 2 pages for the 4,000 politics SCREEN markets (print-price robustness and the verified-activity variant) ≤ 8,000 | ≤ 39,500, ≤ 5.5 h | ≤ 0.03 GB |
  | q0227 | A frame (no volume filter in the walk) + Wikipedia summaries (one per distinct entity) | about 1,500 Gamma + ≤ 3,000 Wikipedia | ≤ 0.01 GB |
  | q0229 | A pageviews (one per canonical title, `[2026-01-01, 2026-10-01)`) + prints (4,000 markets, ≤ 2 pages) | ≤ 3,000 Wikimedia (≤ 50 min) + ≤ 8,000 Data API | ≤ 0.12 GB |

  Total ≤ about 91,000 requests after §11 (q0223 28,000 and q0224 3,000 replace 14,000 and 300; before: ≤ about 74,000; round 1 item 11; the draft's 35,000 for q0226 omitted the HOLDOUT and control caps and
  the activity pages). **A fetch that has not completed (its `*_complete` status absent) is "pending" and is never
  analysed partially**: the census and every screen refuse on an incomplete manifest.

- **Disk guard.** Every CB11 data job declares `--disk-cap-gb` (its output cap) and `--data-dumps-cap-gb 40` (current
  convention), and exits **75** if data-dumps + its cap > 40 GiB **or** root free disk − its cap < 4.5 GB. CB11 output
  caps total **≤ 0.25 GB** (round 1). Exit-75 waits are "pending", as CB10 §2.8.
- **Network etiquette.** Shared `Limiter` per process, collector yield, 429 / `Retry-After` back-off, stop on repeated
  429 (probe 6 saw 429 from Wikimedia after about 10 unpaced requests), collector-health stop.
- **Stop rules.** 5 CPU-hours per family. A job that fails twice for the same non-transient reason stops and is
  recorded. A null is "not detected at MDE x". **No re-screen of a failed CB11 test** with altered windows, features,
  model settings, caps, horizons, bands, thresholds, lags, entity rules or populations, on any data.

### 2.9 Funnel and Stage P

Screen (Stage 1) → gates, placebos, robustness → replication (Stage 2, out-of-time for W and P) → separate prospective
confirmation (Stage P) → economic validation at recorded prices.
- **Stage P-W.** Scheduled ends after the Stage P freeze; the frozen W1 model; W2 entries at the **recorded** best ask
  from the collector's book sweeps or a CLOB `/book` read at `t + 5 min`, depth recorded; closes read from Gamma after
  the fact.
- **Stage P-P.** Politics origins after the freeze from the complete-universe 2 h captures (recorded touch at the
  origin, no new collector), with horizons anchored on the **end date recorded in the capture at the origin** (round 1
  item 3), never on a later edited `endDate`; resolution months later; the P2 rule at the recorded ask.
- **Stage P-A.** Attention days after the freeze; pageviews fetched **at** `t` from the live API (the publication lag is
  then physical, not declared); prints after `t + 48 h`.

---

## 3. Tests

### CB11-W: Whitelisted-proposer clocks (CH85)

**Question.** After a market's scheduled end, how long until it closes? Is that wait forecastable from schedule
features known at the end, and does a decided carry restricted to short predicted waits pay at an hourly capital-time
rate?

**Mechanism.** Since August 2025 only 37 whitelisted addresses can propose outcomes on Polymarket's managed oracle;
liveness is a fixed 2 h. The variable part of the wait is when the proposers' bots or operators act, which plausibly
depends on hour, weekday, market class and recent workload. A carry entered when a proposal is due ties capital for
about 3 h; entered at the wrong hour, for a day or more, for the same 0.5-3c. Who pays: nobody directly; the carry
earns by turning capital over. The money claim is capital efficiency, not information.

**Prior work.** CB1-A1 (decided after the scheduled end, h2) was "not testable" (57 units, counted p = 1; descriptive
−4.00c on mid-like prices); CB1-A2 (0.95-0.99 favourites before the end) was null (−1.05c, `R_ann` −32.7%). W2 differs
from A1 by population size (frames), by transaction-based entries, and by the hourly capital-time measure that A1's
`max(d, 1)` day floor erased. No test has forecast the wait.

**Population (q0222; frozen).** Union of the two frames by `market_id` (the h3 row kept when both exist; field
disagreements counted), `closed` = 1 **whatever its (guarded) `uma_status`** (round 1 item 2), two tokens, scheduled end in W_fit ∪ W_screen ∪ W_hold,
**open at its scheduled end** (`close_epoch > end_epoch`, visible at `t = end_epoch`), not on the excluded dates, key
drops (W rule, §1.3). Primary excludes `fee_category` sports and crypto (reported strata). Disclosed: the frames contain
closed markets whose end fell in 6 random 15-minute windows per day (`HISTORICAL_ML_DEV.md`), so W is a time-stratified
sample of scheduled ends; markets unresolved at frame fetch are absent (right-censoring, measured and gated by GWC, §2.7).

**Target.** `L = ln(min(max(close_epoch − end_epoch, 60 s), 21 d) / 1 h)`, log-hours, capped at 21 days (the cap keeps
every W_fit target determined by 2026-03-01, before W_screen begins).

**Features at `t = end_epoch` (frozen).** f1 end hour in America/New_York (24 levels); f2 weekday in New York (7);
f3 placeholder flag (end time exactly 00:00:00Z, the date-only `endDate` convention); f4 `fee_category` (levels with
< 200 W_fit units pooled to `rare`); f5 `neg_risk`; f6 ln scheduled life in days; f7 the rolling median of `L` over
frame units of the same `fee_category` (all categories, all strata) with `end_epoch ∈ [t − 14 d, t)` **and**
`close_epoch < t` (NaN if fewer than 20). f7 is the "recent proposer lag" feature; it uses only closes visible at `t`.

**Model (frozen).** `sklearn.ensemble.HistGradientBoostingRegressor(loss="absolute_error", learning_rate=0.05,
max_iter=400, max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=1.0, categorical_features=[f1, f2, f4],
early_stopping=False, random_state=1111)`, fitted once on W_fit primary units (sklearn version pinned in the rules).
**Baseline B0:** the W_fit median of `L` per `fee_category` (CH85's category-median baseline). **Baseline B1 (round 1
item 7):** the unit's own f7 (the rolling 14-day per-category median of closes visible at `t`), falling back to B0 where
f7 is NaN (the fallback share is reported).

**W1 (forecast).** `R_B0 = 1 − MAE(L, L̂_model) / MAE(L, L̂_B0)` and `R_B1 = 1 − MAE(L, L̂_model) / MAE(L, L̂_B1)` over
W_screen primary units. **Advance needs both** (round 1 item 7): one-sided p < 0.01 for `R_B0 > 0` with `R̂_B0 ≥ 0.20`,
**and** one-sided p < 0.01 for `R_B1 > 0` with `R̂_B1 ≥ 0.10`; p from the cluster bootstrap (end-date and event ways;
the max). A model that only tracks recent category lag does not advance.
- **Binding calibration placebo (target permutation within category x month; round 1 item 8, mapping specified).** On
  each draw, within every `fee_category` x calendar month of W_screen, the observed `L` values are randomly permuted
  across the units of that cell (a uniform random bijection of units onto the cell's `L` values; predictions, B0 and B1
  fixed); `R_B0`, `R_B1` and their p recomputed with the same clusters; 200 draws (seed 11101); the test "advances" on a
  draw if both p thresholds hold; **advance rate ≤ 1.5%**. *Alternative guarded:* a forecast that only reproduces the
  category-month composition, or clustered p-values that are anti-conservative under within-cell dependence.
- **Attribution (binding for the label "proposer clock"; the advance stands without it).** (a) Schedule share: refit
  without f1-f3; credit the clock only if `R_full − R_noSched ≥ 0.10`; else "the wait is forecastable from category and
  recent lag, not from the clock". (b) Decided units: on W2's decided SCREEN units, `R ≥ 0.10`; else "skill comes from
  undecided markets (event timing), not proposer timing".
- **Robustness (binding).** `R ≥ 0.10` in each calendar month of W_screen; without the top-5 end-dates and top-5 events;
  `R ≥ 0.10` on hours (MAE of `min(wait, 21 d)` in hours); `R ≥ 0.10` on h2-only and h3-only rows.

**W2 (economic, decided carry with short predicted waits).**
- **Sample (q0222, metadata only, before any print).** Seeded 4,000 W_screen primary markets (`arepo-cb11-w-sample`) and
  3,000 W_hold markets (`arepo-cb11-w-hold`), ≤ 3 per event.
- **Prints (q0223).** Newest-first `/trades` pages (`limit` 1,000) until a page's oldest print is before `t − 6 h` (or
  the cap); transactions kept in `[t − 6 h, t + 6 h)`; covered span recorded.
- **Decided trigger and entry (round 1 item 6: latency).** The trigger is the first transaction in `[t + 5 min, t + 60
  min)` with YES-terms VWAP `v ≥ 0.95` (YES decided) or `v ≤ 0.05` (NO decided); its time is `τ`. A trigger whose token
  price + `h_W` exceeds 0.995 is "no carry room" (decided at `τ`, counted, not entered). **Execution:** the next
  transaction at or after `τ + 60 s`; entry price `c` = that transaction's token price (YES-terms `v'`, or `1 − v'`) +
  `h_W`, capped at 1.0, whatever its level; entry time `τ_e`. No transaction in `[τ + 60 s, close)` → "unfilled"
  (counted; scored 0 per trigger, excluded from per-share means). No trigger → "not decided by t + 60 min" (counted, not
  in W2).
- **Payoff.** `Y_k ∈ {1, 0, 0.5}` (guarded); `net = Y_k − c − r·c(1 − c)`; hold `H = (close_epoch − τ_e)/3600 + 1`
  hours; `R_ann_h = 8760 · Σ net / Σ c · max(H, 2)`. **Declared deviation from CB1's `R_ann`:** the day floor `max(d,
  1)` would make every sub-day hold identical, erasing the quantity W studies; the 2 h floor equals the liveness.
  **Disputed and unresolved units (round 1 item 2)** stay in W2 with their guarded outcome (50-50 → 0.5; a unit without
  a clean outcome vector is scored `Y_k = 0`, the worst case, in the primary).
- **Capacity-capped pool simulation (round 1 item 6; binding gate, §2.4).** A single pool of $10,000 (declared; $1,000
  and $100,000 reported) starts at the first W_screen end; S units are taken in chronological order of `τ_e`; each buys
  `min(free cash / c, q_i)` shares, where `q_i` is the **recorded capacity**: the summed size of transactions on token k
  in `[τ + 60 s, τ + 60 min)` (no more than was actually traded); cash returns at `close_epoch + 1 h` with `Y_k` per
  share. Reported: the pool's annualised return, its excess over a 4.5% risk-free rate (the gate: ≥ 10%), $ P&L per
  month, mean utilisation and the share of S units skipped for lack of cash.
- **Prior disclosed with every W2 line (round 1 optional item):** CB1-A1 (post-end decided carry on h2, 57 units) was
  "not testable" with a descriptive −4.00c per share on mid-like prices.
- **Arm S.** Decided SCREEN units whose W1 prediction (the W_fit model) is `exp(L̂) ≤ 6 h`.
- **Statistic.** Mean `net` per share over S, one-sided > 0; floors per §2.4; CB1 tail gate on S (`π` = share with
  `Y_k = 0`, `π* = 1 − mean(c + f)`).
- **Attribution (binding for the label "the clock adds value").** `R_ann_h(S) ≥ 1.5 x R_ann_h(all decided)` and
  `net(S) ≥ net(all decided) − 0.1c`; else "the carry, not the clock".
- **Robustness (binding).** `h_W = 1.0c` keeps net > 0; trigger window `[t + 5, t + 30 min)` keeps the sign;
  capital-time floor 6 h keeps `R_ann_h ≥ 10%`; top-5 cluster drops; **worst case for status (round 1 item 2):** every
  unit whose guarded `uma_status` is not `resolved`, or whose status history shows a dispute, scored `Y_k = 0`, keeps net
  > 0 and the tail gate. Reported: capacity (shares in qualifying transactions in the
  entry window, median per unit), the sports stratum, the losing-share by category ("killed in category" as CB1).

**Power (MDE estimates, restated by the census).** W1: about 15-25k W_screen primary units over about 120 end-dates;
the bootstrap SD of `R` is likely 0.01-0.02, so the MDE is about 0.03-0.06 and **the 0.20 floor binds**, not power. W2:
if 40-60% of sampled markets are decided in the first hour and 30-50% of those are predicted short, S holds about
500-1,200 units; with a tail-driven SD of about 12c per unit and a design effect of 2, the MDE is about **1.5-2.4c per
share**, so W2 detects only carries netting ≥ about 2c; the gross on a 0.97-0.99 entry is 1-3c. W2 is therefore a
strong filter, and its likeliest honest outcome is "not detected at MDE 2c".

**Stage 2 (conditional).** W1-rep: refit model and baseline on ends `[2025-10-01, 2026-06-09)`, evaluate on sealed
W_hold; W2-rep: the W2 rule on the sealed W_hold print sample with the refit model. Same floors, Holm per §2.3.

**Uncounted variant (q0238; moved from q0224 in round 1).** If q0220 pins the Managed OOV2 contract address (from a public UMA deployment file or
one known proposal receipt), `ProposePrice` logs for W_screen are decoded to proposal times and hashed proposers; the
report gives proposal lag vs liveness shares and the proposer count. Never a gate, never a feature in W1.

### CB11-P: Political long-horizon underconfidence carry (CH88)

**Question.** In politics markets 30-90 days before the scheduled end, does the favourite priced 0.60-0.85 resolve
YES more often than its price, by enough to pay for a one-leg hold?

**Mechanism.** Compression toward 0.5 at long horizons (Le 2026 reports persistent political underconfidence, primarily
on Kalshi, "replicating" on Polymarket; a prior, not a result here): abstention by informed traders far from the event,
retail appetite for contrarian political bets, and capital lock that deters arbitrage. Who pays: buyers of the political
underdog. Why it persists: months-long holds and a modest annualised return.

**Prior work.** C1 (1 d: slope 1.07, no favourite-longshot pattern; politics 72 units, too small; 7 d weighted slope
1.34 unstable; 30 d unusable at 31 units), PX4 (mid ≥ 0.85, n.s.), CB1-A2 (0.95-0.99, null), T5 (1-7 d model vs
recalibrated price). P's cell (politics x 30-90 d x 0.60-0.85) is untested. P is not a re-screen of any of them.

**Population (q0225; frozen).** Gamma closed markets with tag id 2 (market or event tags), scheduled end in P SCREEN ∪
P HOLDOUT, two outcomes, scheduled life (`endDate − startDate`, `createdAt` if `startDate` missing) ≥ 60 days,
**no resolution-status or outcome-cleanliness filter** (round 1 optional item adopted: removing voided or unclean
markets is post-origin selection; status and outcomes are guarded; a clean vector gives `Y ∈ {0, 1}`, 50-50 gives 0.5,
and an unresolved, voided or unclean market is scored `Y_f = 0.5` (the venue's void convention) in the primary, counted,
with a binding worst-case check), not tagged sports, crypto or weather; key drops (full rule); ≤ 4 markets per event (seeded `arepo-cb11-pol-cap`); all remaining
markets up to 4,000 SCREEN and 3,000 HOLDOUT (seeded if more). **Control:** the same rule without the politics tag and
excluding sports, crypto, weather tags; up to 2,000 SCREEN and 1,500 HOLDOUT. Walk: weekly `end_date` windows with
`start_date_max = window start − 53 d` (server-side prefilter; exact life filter local), `limit` 100, offset ≤ 2,000
(capped windows are split in half until uncapped; counted).

**Units.** For each market and `h ∈ {30, 60, 90}` d: eligible iff `startDate ≤ t_h − 7 d` and open at `t_h` (Gamma
`closedTime > t_h`, visible at `t_h`). One `prices-history` request per unit over `[t_h − 7 d, t_h]` (fidelity 10, §2.2)
gives the price `p` of the outcome-0 token (last point with stamp + 600 s < `t_h`, age ≤ 24 h) **and the causal
activity proxy (round 1 item 1):** the unit is "active" iff the series takes **≥ 2 distinct values** among points with
stamp + 600 s in `[t_h − 7 d, t_h)`; otherwise "inactive (proxy)" (excluded, counted). **No primary condition uses Data
API page reach** (which depends on trading after `t_h` and drops the busiest markets). The Data API check (≥ 1
transaction in `[t_h − 7 d, t_h)` within ≤ 2 newest-first pages) is a reported **variant** on the reachable subset only.
Favourite `f` = the token with price `p_f = max(p, 1 − p)`; a **P unit** has `p_f ∈ [0.60, 0.85]`.
- **End-date hindsight (round 1 item 3).** Horizons are anchored on the Gamma `endDate` as fetched, which may be the
  final edited value. Every P1/P2 result carries the label **"L1, hindsight end date"**. Flags (frame time, rules
  frozen): `late_close` = `closedTime > endDate + 7 d`; `edit_detected` = the market's `endDate` differs by > 1 day from
  its event's `endDate`, or the question or event title names an explicit calendar date (frozen regex) more than 1 day
  from `endDate`. A binding robustness check excludes every flagged market. Stage P-P anchors on end dates recorded at
  the origin (§2.9).
- **2024 US general election (round 1 item 4).** A frozen keyword rule (rules file, hashed before any read) flags events
  whose scheduled end is in `[2024-10-01, 2025-01-31]` and whose title matches `2024` together with any of `president`,
  `presidential`, `electoral`, `popular vote`, `Senate`, `House`, `governor`, `swing state`, or any of `Harris`, `Walz`,
  `Vance`, `Trump` (case-insensitive). Flagged events are excluded in a binding robustness check.

**P1 (calibration excess).** `E = Y_f − p_f`; market value `Ē_m` = mean over its P units (each market weight 1); `Ē` =
mean over markets; one-sided > 0; floor +3.0c.
- **Binding calibration placebo.** Outcomes replaced by `Y*` from the GPP copula with the **shared week factor**
  (round 1 item 4: `Z_m = √0.2 · W_week + √0.4 · V_event + √0.4 · ε_m`, §2.7); 200 draws (seed 11102). *Alternative
  guarded:* within-event dependence and common shocks across events resolving in the same week (election nights) make
  the clustered p anti-conservative.
- **Election concentration (binding; CH88's kill).** Without the single largest scheduled-end ISO week and, separately,
  without the single largest event: p < 0.01 holds and `Ē ≥ 1.5c`.
- **Attribution (binding for the label "politics-specific").** The control's `Ē_C` by the same rule; the label needs
  `Ē − Ē_C ≥ 1.5c`; otherwise "long-horizon favourite underpricing, not political" (the advance and the money claim stand).
- **Robustness (binding).** Each horizon alone keeps the sign; print-based price (last transaction in `[t_h − 24 h,
  t_h)`, on the subset where ≤ 2 pages reach it) keeps the sign and ≥ half; band `[0.55, 0.90]` keeps the sign; each
  SCREEN half (2024-07..2025-03, 2025-04..2025-12) keeps the sign; **round 1:** excluding `late_close` and
  `edit_detected` markets keeps p < 0.01 and `Ē ≥ 1.5c` (item 3); excluding the 2024-election events keeps p < 0.01 and
  `Ē ≥ 1.5c` (item 4); unresolved/voided/unclean markets scored `Y_f = 0` keeps the sign (optional item); if the T5
  ids were not retrievable, excluding SCREEN ends in `[2025-10-11, 2026-01-01)` keeps the sign (item 5). Reported: the
  logistic calibration slope (politics vs control; slope > 1 is Le's "underconfidence"), the Data-API-verified activity
  variant, the **liquidity stratum** (terciles of the number of distinct `prices-history` values in `[t_h − 7 d, t_h)`;
  round 1 optional item), the counts of unresolved/voided/unclean markets.

**P2 (economic).** One entry per market at its **earliest** P unit (90, else 60, else 30 days), at `a = p_f + 1.5c`,
fee `r·a(1 − a)`, held to resolution: `net = Y_f − a − fee`; `R_ann = 365 · Σ net / Σ a · max(d, 1)` with `d` the days
from `t_h` to `closedTime` (hold length only). Floors per §2.4 (`R_ann` in excess of 4.5%, round 1); binding
robustness: half-spread 2.5c keeps net > 0, and the flag and election exclusions above keep net > 0.
Reported: net by horizon (CH88 expects the 30-day cell not to clear), the share of markets resolving before their
scheduled end, the annualised figure by horizon.

**Power.** Probe 5 implies several hundred long-life politics markets per month in 2026 and fewer in 2024-25. If
SCREEN yields about 1,000-1,500 markets with a P unit in about 400-600 events and about 75 ISO weeks, with per-market SD
about 43c and a design effect of 2-3, the MDE on `Ē` is about **4.5-7c** (floor 3c). P detects an effect of the size
round 4 sketched (a 0.70 favourite that is really 0.78) and not a 3-point compression. The GPP gate (6.0c) is fixed now.
**Round 1:** with the shared week factor and the max-of-ways SD (item 4), the MDE is likely at the upper end of this
range or above it, so "not run (power)" is a live outcome; the 6.0c threshold is unchanged.

**Stage 2 (conditional).** P1-rep, P2-rep on sealed HOLDOUT ends `[2026-01-01, 2026-09-01)` (out-of-time; the 2026
primaries season), same rules.

### CB11-A: Attention without news (CH97)

**Question.** Among markets that moved ≥ 3c on day X, do moves made without a spike in public attention to the market's
named entity continue more over the following days than moves made with one?

**Mechanism.** Public attention and public information are correlated but distinct. A move that coincides with a
pageview spike was made by a crowd that has just noticed; it is more likely to overshoot and revert. A move without any
rise in attention was made by a few traders with information the public has not looked at; it is more likely to keep
drifting as the information diffuses. Who pays: in the quiet cell, the late sellers into the drift; in the spike cell,
the attention-driven buyers. **Timing reality:** the pageviews of day X are public only about a day after it ends (probe
6), so the earliest the feature can act is `X + 3 d` under the declared 48 h rule. A therefore tests a slow drift, and
CH97's same-day maker filter is out of reach historically (re-entry: Stage P-A with live fetches, or Wikimedia hourly
dumps).

**Prior work.** E004/J4 bounce and the HB1 reversal moderators study unconditional post-move reversal; **A does not
re-test it** (the unconditional mean continuation is reported only, uncounted). GDELT news counts failed as a source
(throttling, lag, relevance); no pageview feature has ever been tested.

**Population (q0227; frozen).** Gamma closed binary markets, scheduled end in `[2026-04-20, 2026-10-01)`, scheduled life
overlapping `[2026-04-10, 2026-09-28)` by ≥ 10 days, `vol_ok` (end-of-life volume ≥ $10k; a disclosed look-ahead in
selection, shared by both arms, as CB10-B), not sports/crypto/weather/Pyth/strike ladders/Up-Down, key drops (full rule),
≤ 3 per event, **entity rule passed**; seeded 3,000 markets (`arepo-cb11-attn-sample`); event-hash split before any
pageview or print read. **Round 1 item 10:** the frame walk applies no volume filter; `vol_ok` is a stored boolean.
Besides the 3,000 `vol_ok` markets, a seeded **1,000-market robustness stratum** is drawn from the entity-passing
markets **without** `vol_ok` (`arepo-cb11-attn-novol`), split by the same event hash; it enters only the causal-volume
robustness check below.

**Entity rule (frozen).** `e = derive_query(question, event_title).entities[0]` (source sha256 pinned); rejected if `e`
(case-insensitive) is in a frozen stop list written at rules time (months, weekdays, the existing `_GENERIC_CAP`, and
generic nouns such as "IPO", "Invasion", "Election", "Ceasefire", "Recession"; the list is hashed, and written without
reading any A target). Wikipedia REST `page/summary/<title>` (keyless) must return `type = "standard"` (redirects followed;
the canonical title is used for pageviews); the title and the short `description` are stored. **Audit (gate GA0):** a
seeded 200-market SCREEN sample of (question, canonical title, description) is blind-labelled "the article is the
market's subject / not" by a `science-reviewer` agent; labels are committed before q0229; precision ≥ 80% or A is "not
testable (entity map)".

**Units.** Market-day `X ∈ [2026-04-10, 2026-09-24]` with: listed ≥ 8 d before X; **pageview rules (round 1 item 9):**
all 9 days `X − 8 .. X` present in the series (a missing day makes the unit "unavailable (pageviews)", never filled),
baseline `median(views(X − 8 .. X − 1)) ≥ 50` views/day, and the series' first non-zero day ≥ 30 days before X (the
series is fetched from 2026-01-01, so an article created or first viewed later is not used before it has 30 days of
history; this removes entities that exist only because of the event); `P_end(X)` and `P_end(X − 1)` available (`P_end(d)` = VWAP of transactions in the 60 min before `d + 1` 00:00Z,
else the last transaction in the 6 h before, else unavailable); scheduled end ≥ `t + 72 h`; open at `t`.
- `A_X = views(X) / median(views(X − 8 .. X − 1))` (the baseline rule above makes the median ≥ 50); **spike** `A ≥ 2.0`, **quiet** `A ≤ 1.25`,
  middle reported only.
- `M = P_end(X) − P_end(X − 1)`; **big move** `|M| ≥ 0.03`.
- Origin `t = X + 3 d 00:00Z`; `P(s)` = VWAP of transactions in `[s − 60 min, s)`, else the last in `[s − 6 h, s)`,
  else unavailable. Target `C = sign(M) · (P(t + 48 h) − P(t))`. If the market closes before `t + 48 h`, the mark is the
  last transaction before the close (counted; excluded in a robustness check).

**A1 (mechanism contrast).** `Δ = mean C(big, quiet) − mean C(big, spike)` over SCREEN units, one-sided > 0; floor 1.0c.
- **Binding calibration placebo (label swap).** Within each day X, the spike/quiet labels of big-move units are
  permuted; 200 draws. *Alternative guarded:* units of one day share news and market-wide moves, making the clustered p
  anti-conservative.
- **Attribution (binding for the label "same-day attention").** Lagged attention `A_lag = views(X − 7) / median(views(X
  − 15 .. X − 8))`, same thresholds, pageview rules (applied to days `X − 15 .. X − 7`) and statistic; units lacking
  lagged data drop from this check only (counted); credit only if `Δ − Δ_lag ≥ 0.5c`; else "an entity-type trait (spiky
  entities), not day attention".
- **Robustness (binding).** Spike thresholds 1.5 and 3.0 keep the sign; `|M| ≥ 0.05` keeps the sign; mark at `t + 24 h`
  keeps the sign and ≥ half; early-closed units excluded keeps the sign; top-5 cluster drops; month rule (§2.6);
  **causal volume instead of `vol_ok` (round 1 item 10):** on SCREEN units from both strata (`vol_ok` and the
  robustness stratum) whose traded notional in `[X − 7 d, X)` (prints) is ≥ $2,000, each weighted by the inverse
  sampling fraction of its stratum, Δ keeps the sign and ≥ half. The p-value of A1 is the max over the three cluster
  ways (event, day X, 3-day blocks of `t`; §2.3).
  Stated, not tested: reverse causality (a Polymarket move causing pageviews) would put informed moves into the spike
  cell, which makes Δ conservative.

**A2 (economic).** In quiet big-move SCREEN units, buy the token in the move's direction at `P(t) + 1.5c` (token terms)
plus fee and sell at `P(t + 48 h) − 1.5c` minus fee; mean net per share, one-sided > 0; floor 1.0c; binding robustness
2.0c per side. Reported, uncounted: a side-free fade in spike units (entry against the move at `P(t) ∓ 1.5c`).

**Power.** If about 1,500 SCREEN-and-HOLDOUT markets pass the entity rule (probe 6 hit rate 6/10 before the type
filter) with about 20 usable days each, SCREEN has about 15,000 market-days, about 1,500 big moves, of which perhaps
55% quiet and 10% spike: about 800 and 150. That would fail GA's 200-spike minimum; GA is kept and the census decides.
With 1,000 quiet and 200 spike units, SD(C) about 8c and a design effect of 1.7, `MDE_A1 ≈ 3.17 x 8 x √(1/200 + 1/1000)
x 1.3 ≈ 2.6c` and `MDE_A2 ≈ 1.1c`. **A is the least powered family**; if GA fails, A1 and A2 are "not testable",
counted, with re-entry by Stage P-A on a larger prospective window. **Round 1:** the ≥ 50 views/day baseline, the
complete-9-day and the 30-day-history rules remove low-traffic and event-born entities, so unit counts fall further;
the spike minimum of GA (200) is unchanged and is now the likeliest gate to fail.

**Stage 2 (conditional).** A1-rep, A2-rep on sealed HOLDOUT events (same calendar, L2).

### CB11-F: Data jobs

q0220 smoke (PASS needs: both frames match their pinned sha256 and carry every whitelisted column; the W loader refuses
end ≥ 2026-07-01 and never yields `outcome_prices` outside the guarded accessor (fixture); Gamma `tag_id=2` paging on
two out-of-window weeks (2024-05) returns ≤ 100 per page with stable counts on repeat; `prices-history` returns a point
within 24 h of `end − 90 d` for 2 out-of-window markets; the Data API newest-first reach is recorded on 2 out-of-window
markets; Wikipedia summary returns `type` for 3 fixed articles (`Xi_Jinping`, `NATO`, `Federal_Reserve`) and the
pageviews' last published day is ≤ 48 h old (§2.2); an attempt to pin the Managed OOV2 address is recorded (pass or
not, it gates only q0224). Any failure → the dependent family "not testable (source)", counted; no rule is re-fitted).
q0221 keys; q0222 W units and W_hold seal listing; q0223 W prints; q0224 W censoring count; q0225-q0226 P; q0227, q0229 A; q0230 seals; q0231 (W) and q0239 (P, A)
census. Every data job writes a manifest (file sha256, request counts, failures, data-dumps size and margin, free disk).

## 4. Jobs (draft specs; JSON in this document only)

Fields follow `queue/README.md`; `argv[0]` is under `backend/scripts/`, `cwd` is `backend`. **None is written to
`queue/jobs/` or `queue/drafts/`** before its code and tests exist and pass a `science-reviewer` freeze check; analysis
jobs also need the CB11 freeze. All `family` = `creative_batch_11`. Round 1: q0224 is the censoring count (the on-chain
variant moved to q0238); the census is split per family (q0231 W, q0239 P and A) so that W can screen before `T_seal`;
budgets recomputed (item 11); every fetch writes a `*_complete` status and the census refuses incomplete manifests.

| Id | Lane | Priority | Size / time | Depends on | Commit when |
|---|---|---|---|---|---|
| q0220 | cpu | 29 | ≤ 40 req at ≤ 1 rps, < 5 min, mem 200 | - | rules file + smoke code reviewed |
| q0221 | net | 29 | ≤ 400 req, ≤ 0.01 GB | q0220 | with q0220's PASS |
| q0222 | cpu | 28 | no network, mem 900, ≤ 0.02 GB | q0221 | with q0221 |
| q0223 | net | 28 | ≤ 28,000 req (§11), mem 400, ≤ 0.03 GB, ≤ 4 h | q0222 | with q0222 |
| q0224 | net | 28 | ≤ 3,000 req (§11), ≤ 0.001 GB, ≤ 25 min per chunk | q0222 | with q0222 |
| q0225 | net | 27 | ≤ 4,000 req, ≤ 0.01 GB | q0221 | with q0221 |
| q0226 | net | 27 | ≤ 39,500 req, mem 400, ≤ 0.03 GB, ≤ 5.5 h | q0225 | with q0225 |
| q0227 | net | 26 | ≤ 4,500 req, ≤ 0.01 GB | q0221 | with q0221 |
| q0229 | net | 26 | ≤ 11,000 req, mem 500, ≤ 0.12 GB | q0227 | after the audit labels are committed |
| q0230 | cpu | 26 | light | q0223 (W2 holdout), q0226, q0229 | per family as its fetch completes |
| q0231 | cpu | 25 | ≤ 0.9 GB | q0222, q0223, q0224, W seal copies | after `seals/cb11_w_hold_SEAL.json` and the W2 holdout seal are committed |
| q0239 | cpu | 25 | ≤ 0.9 GB | q0230 | after the P and A seal copies are committed |
| q0232 | cpu | 25 | ≤ 0.9 GB | q0231 | after the CB11 freeze |
| q0233, q0234 | cpu | 25 | ≤ 0.9 GB | q0239 | after the CB11 freeze |
| q0235-q0237 | cpu | 25 | ≤ 0.9 GB | q0232 / q0233 / q0234 | only if the family's Stage 1 advanced |

```json
{"id": "q0220_cb11_smoke", "title": "CB11: smoke (frame sha256 and column whitelist; W loader refusal and guarded outcome_prices/uma_status fixture; Gamma tag_id=2 paging on 2 out-of-window weeks; prices-history over [end-97d, end-90d] on 2 out-of-window markets; Data API newest-first reach on 2 out-of-window markets; Wikipedia summary type on 3 fixed articles; pageviews last-published-day <= 48 h; Gamma closed=false count on 1 frame window; Managed OOV2 address pin attempt); counts only", "family": "creative_batch_11", "priority": 29, "expected_value": "go/no-go for every CB11 source", "data": ["history/h2_main/frame.csv.gz", "history/h3_power/frame.csv.gz", "public Gamma, CLOB prices-history, Data API", "Wikipedia REST, Wikimedia pageviews"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "cpu", "network": "gamma-api, clob, data-api, en.wikipedia.org, wikimedia.org, polygon rpc"}, "depends_on": [], "argv": ["scripts/run_cb11.py", "smoke", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "1"], "timeout_s": 1200, "max_retries": 1, "outputs": ["research_lab/creative_batch11/smoke.json", "trials.jsonl (cb11_descriptive)"], "next_action": "PASS: q0221; FAIL: dependent family not testable (source), counted", "notes": "CREATIVE_BATCH_11.md CB11-F. DRAFT-REVISED round 1. <= 40 requests. Prints counts only."}
{"id": "q0221_cb11_exclusion_keys", "title": "CB11: exclusion keys = h8_tail_b key file + market ids of every sampled set on the host (h1/h2/h3 samples, h5, h6, h7, h8 sets, CB8 frames) + committed seal copies + MANDATORY C1 sample and T5 frame ids from the arepo-data release; Gamma lookups for missing event/negRisk/series keys", "family": "creative_batch_11", "priority": 29, "expected_value": "disjointness of W, P and A", "data": ["history/*/ (id columns only)", "docs/research_lab/seals/*", "arepo-data release: calibration-c1-20261011 sample_plan, resdev-t5-20261011b frame", "public Gamma (ids)"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "gamma-api, github release download"}, "depends_on": ["q0220_cb11_smoke"], "argv": ["scripts/run_cb11.py", "exclusion-keys", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 2400, "max_retries": 2, "outputs": ["research_lab/creative_batch11/exclusion_keys.csv.gz", "manifest.json (c1_t5_status: retrieved | absent)"], "next_action": "q0222, q0225, q0227", "notes": "DRAFT-REVISED round 1 (item 5). C1/T5 absent -> P reps labelled 'possibly touched holdout (L1)' and the T5-window robustness binds. >2% missing metadata -> disjointness unverified (P, A not testable, counted). Exit 75 on headroom = pending."}
{"id": "q0222_cb11_w_frame", "title": "CB11-W: W units from h2_main + h3_power frames (whitelisted columns; every closed row open at its scheduled end, NO uma_status filter; W key rule; windows W_fit/W_screen/W_hold; excluded dates 2026-09-10/11), features f1-f7 and B1, W2 seeded samples (4,000 SCREEN, 3,000 HOLDOUT, <= 3 per event), W_hold listing sha256, seeded 300 frame windows for q0224; outcome_prices and uma_status to the guarded file", "family": "creative_batch_11", "priority": 28, "expected_value": "W population, features and seal", "data": ["history/h2_main/frame.csv.gz", "history/h3_power/frame.csv.gz", "creative_batch11/exclusion_keys.csv.gz"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0221_cb11_exclusion_keys"], "argv": ["scripts/run_cb11.py", "w-frame", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--disk-cap-gb", "0.02", "--data-dumps-cap-gb", "40"], "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch11/w/{units.csv.gz,w2_sample.csv.gz,censor_windows.csv,w_hold_listing.json,manifest.json}", "history/h11_wprints/outcomes_guarded.csv.gz"], "next_action": "commit seals/cb11_w_hold_SEAL.json; q0223, q0224", "notes": "DRAFT-REVISED round 1 (item 2). No wait computed; uma_status never read outside the guarded accessor. No network."}
{"id": "q0223_cb11_w_prints", "title": "CB11-W: Data API newest-first prints (limit 1000, pages until oldest < t-6h or cap) for the W2 SCREEN and HOLDOUT samples, aggregated by transaction hash to (time, YES-terms VWAP, size) in [t-6h, t+6h); covered span; HOLDOUT written to holdout/", "family": "creative_batch_11", "priority": 28, "expected_value": "W2 triggers, latency-delayed entries and recorded capacity", "data": ["public Data API", "creative_batch11/w/w2_sample.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "data-api"}, "depends_on": ["q0222_cb11_w_frame"], "argv": ["scripts/run_cb11.py", "w-prints", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "2", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40", "--budget-min", "85"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h11_wprints/{screen,holdout}/tx.csv.gz", "manifest.json"], "next_action": "q0230 (W2 holdout seal); q0231", "notes": "DRAFT-REVISED round 1 (items 6, 11: <= 14,000 requests). No side, wallet or hash stored. Incomplete = pending, never analysed.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"w_prints_complete\""}}
{"id": "q0224_cb11_w_censoring", "title": "CB11-W: right-censoring count, one Gamma closed=false query per seeded frame window (300) with the window's end_date bounds; censored share per window set for gate GWC (> 2% -> W not testable (censoring))", "family": "creative_batch_11", "priority": 28, "expected_value": "gate GWC", "data": ["public Gamma", "creative_batch11/w/censor_windows.csv"], "resources": {"mem_mb": 200, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0222_cb11_w_frame"], "argv": ["scripts/run_cb11.py", "w-censoring", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "2", "--disk-cap-gb", "0.001", "--data-dumps-cap-gb", "40"], "timeout_s": 900, "max_retries": 2, "outputs": ["research_lab/creative_batch11/w/censoring.json"], "next_action": "q0231", "notes": "DRAFT, new in round 1 (item 2). Counts only; no market field beyond ids and endDate stored."}
{"id": "q0225_cb11_pol_frame", "title": "CB11-P: Gamma frames (politics tag_id=2 and control), closed, scheduled end [2024-07-01,2026-09-01), life >= 60 d, NO status/cleanliness filter, not sports/crypto/weather, full key drops (C1/T5 mandatory), <= 4 per event, samples (politics 4,000 SCREEN / 3,000 HOLDOUT; control 2,000 / 1,500), out-of-time split at 2026-01-01; late_close / edit_detected / 2024-election flags; outcomes, umaResolutionStatus and closedTime to the guarded file", "family": "creative_batch_11", "priority": 27, "expected_value": "P population and flags", "data": ["public Gamma", "creative_batch11/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api"}, "depends_on": ["q0221_cb11_exclusion_keys"], "argv": ["scripts/run_cb11.py", "pol-frame", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "2", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h11_pol/{frame.csv.gz,split.json,flags.csv.gz,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0226", "notes": "DRAFT-REVISED round 1 (items 3, 4, 5, optional). late_close uses closedTime only to set a robustness flag (guarded until q0233). Capped windows split until uncapped (counted).", "repeat": {"max_runs": 2, "until_log_regex": "\"status\": \"pol_frame_complete\""}}
{"id": "q0226_cb11_pol_prices", "title": "CB11-P: 10,500 markets x 3 horizons: CLOB prices-history [t_h-7d, t_h] fidelity 10 (price = last point with stamp+600s < t_h, age <= 24h; activity proxy = >= 2 distinct values in [t_h-7d, t_h)); Data API <= 2 newest-first pages for the 4,000 politics SCREEN markets (print-price robustness, verified-activity variant); HOLDOUT rows written to holdout/", "family": "creative_batch_11", "priority": 27, "expected_value": "P1/P2 prices and causal eligibility", "data": ["public CLOB prices-history, Data API", "history/h11_pol/frame.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "clob, data-api"}, "depends_on": ["q0225_cb11_pol_frame"], "argv": ["scripts/run_cb11.py", "pol-prices", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "2", "--disk-cap-gb", "0.03", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h11_pol/{screen,holdout}/origins.csv.gz", "manifest.json"], "next_action": "q0230", "notes": "DRAFT-REVISED round 1 (items 1, 11: <= 39,500 requests, about 5.5 h). No outcome read. Resumable; incomplete = pending, never analysed partially.", "repeat": {"max_runs": 5, "until_log_regex": "\"status\": \"pol_prices_complete\""}}
{"id": "q0227_cb11_attn_frame", "title": "CB11-A: Gamma frame (closed binary, scheduled end [2026-04-20,2026-10-01), life overlap >= 10 d, NO volume filter in the walk, vol_ok stored, not sports/crypto/weather/Pyth/ladders/Up-Down, full key drops, <= 3 per event), frozen entity rule + Wikipedia page/summary type (standard only, canonical title, description), seeded 3,000 vol_ok markets + 1,000 non-vol_ok robustness stratum, event split SCREEN/HOLDOUT (arepo-cb11-attn-split), seeded 200-pair audit file", "family": "creative_batch_11", "priority": 26, "expected_value": "A population, entity map, audit file", "data": ["public Gamma", "Wikipedia REST page/summary", "creative_batch11/exclusion_keys.csv.gz"], "resources": {"mem_mb": 400, "cpu": 1, "lane": "net", "network": "gamma-api, en.wikipedia.org"}, "depends_on": ["q0221_cb11_exclusion_keys"], "argv": ["scripts/run_cb11.py", "attn-frame", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "2", "--wiki-rps", "1", "--disk-cap-gb", "0.01", "--data-dumps-cap-gb", "40"], "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h11_attn/{frame.csv.gz,entities.csv.gz,split.json,audit_sample.csv,manifest.json}"], "next_action": "commit audit_sample.csv; science-reviewer blind labels committed; then q0229", "notes": "DRAFT-REVISED round 1 (item 10). No pageview or print read before the split and the audit file exist."}
{"id": "q0229_cb11_attn_data", "title": "CB11-A: daily pageviews per canonical title [2026-01-01, 2026-10-01) (all-access/user, <= 1 rps); Data API newest-first prints (<= 2 pages) for 4,000 markets aggregated to transactions in [2026-04-01, 2026-10-01); covered span; HOLDOUT to holdout/", "family": "creative_batch_11", "priority": 26, "expected_value": "A1/A2 inputs incl. causal pre-X volume", "data": ["Wikimedia pageviews REST", "public Data API", "history/h11_attn/frame.csv.gz"], "resources": {"mem_mb": 500, "cpu": 1, "lane": "net", "network": "wikimedia.org, data-api"}, "depends_on": ["q0227_cb11_attn_frame"], "argv": ["scripts/run_cb11.py", "attn-data", "--rules", "../docs/research_lab/seals/cb11_rules.json", "--rps", "2", "--wiki-rps", "1", "--disk-cap-gb", "0.12", "--data-dumps-cap-gb", "40", "--budget-min", "110"], "timeout_s": 7200, "max_retries": 2, "outputs": ["history/h11_attn/{screen,holdout}/{pageviews.csv.gz,tx.csv.gz}", "manifest.json"], "next_action": "q0230", "notes": "DRAFT-REVISED round 1 (items 9, 10, 11: <= 11,000 requests). Refuses unless the committed audit labels exist. Missing pageview days stored as absent, never filled. No side, wallet or hash stored.", "repeat": {"max_runs": 3, "until_log_regex": "\"status\": \"attn_data_complete\""}}
{"id": "q0230_cb11_seal", "title": "CB11: HOLDOUT listings sha256 for W2 prints, P and A (per family, as each fetch completes); seal-time drops vs seal copies committed by now; seal copies seals/cb11_{wprints,pol,attn}_holdout_SEAL.json", "family": "creative_batch_11", "priority": 26, "expected_value": "sealed holdouts", "data": ["history/h11_wprints/holdout/", "history/h11_pol/holdout/", "history/h11_attn/holdout/"], "resources": {"mem_mb": 300, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0223_cb11_w_prints"], "argv": ["scripts/run_cb11.py", "seal", "--family", "auto"], "timeout_s": 1800, "max_retries": 2, "outputs": ["research_lab/creative_batch11/holdout_SEAL_<family>.json"], "next_action": "commit the seal copies; q0231 (W) / q0239 (P, A)", "notes": "DRAFT-REVISED round 1. Seals each family whose fetch manifest is complete; exits 75 (pending) for families still fetching and re-runs. Sealed files never edited; drops recorded as DROPPED_* blocks.", "repeat": {"max_runs": 6, "until_log_regex": "\"status\": \"seal_all_complete\""}}
{"id": "q0231_cb11_census_W", "title": "CB11-W census, counts only (W units by window/category/frame source/end hour; GWC censoring gate; GW, GW2; W2 coverage audit; triggers and S-arm counts; MDEs)", "family": "creative_batch_11", "priority": 25, "expected_value": "W gates and MDEs before the freeze", "data": ["creative_batch11/w (no target, no guarded file)", "creative_batch11/w/censoring.json", "history/h11_wprints/screen"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0222_cb11_w_frame", "q0223_cb11_w_prints", "q0224_cb11_w_censoring", "q0230_cb11_seal"], "argv": ["scripts/run_cb11.py", "census", "--family", "W"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch11/census_W.json", "trials.jsonl (cb11_descriptive)"], "next_action": "science-reviewer freeze check, then model_specs/cb11_v1.json (W part may freeze first)", "notes": "DRAFT-REVISED round 1 (per-family census so W can screen before T_seal). No wait, outcome, status or net computed. Refuses on an incomplete manifest."}
{"id": "q0232_cb11_screen_W", "title": "CB11-W: W1 (frozen HGB vs B0 and B1; both p < 0.01, R_B0 >= 0.20, R_B1 >= 0.10; category x month target permutation placebo; attribution; robustness) and W2 (decided carry, entry at the next transaction >= tau+60s, arm S predicted wait <= 6 h; hourly capital-time; capacity-capped $10k pool, excess over 4.5% >= 10%; tail gate; worst-case status; CB1-A1 prior disclosed) on W_screen", "family": "creative_batch_11", "priority": 25, "expected_value": "W verdicts", "data": ["creative_batch11/w", "history/h11_wprints/screen + outcomes_guarded (opened here)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0231_cb11_census_W"], "argv": ["scripts/run_cb11.py", "screen", "--family", "W"], "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch11/results_W.json", "trials.jsonl (cb11_test + creative_batch_11:W)"], "next_action": "advanced: commit q0235", "notes": "DRAFT-REVISED round 1 (items 2, 6, 7, 8). Refuses before the CB11 freeze hash, on any W_hold row, and if GWC failed (writes the counted not-testable lines)."}
{"id": "q0239_cb11_census_PA", "title": "CB11-P and CB11-A census, counts only (P labels with the causal activity proxy, flags, GP, P coverage audit, GPP with the shared week factor and max-of-ways SD; A entity availability under the round-1 pageview rules, GA0 from committed audit labels, GA, coverage audit and failures by arm; MDEs)", "family": "creative_batch_11", "priority": 25, "expected_value": "P and A gates and MDEs before the freeze", "data": ["history/h11_pol/screen (no guarded file)", "history/h11_attn/screen (HOLDOUT counts only)"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0226_cb11_pol_prices", "q0229_cb11_attn_data", "q0230_cb11_seal"], "argv": ["scripts/run_cb11.py", "census", "--family", "P,A"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch11/census_PA.json", "trials.jsonl (cb11_descriptive)"], "next_action": "science-reviewer freeze check (P, A part)", "notes": "DRAFT, new id in round 1 (was part of q0231). No outcome, excess, continuation or net computed. Refuses on an incomplete manifest."}
{"id": "q0233_cb11_screen_P", "title": "CB11-P: P1 (mean favourite excess; week-factor calibrated-outcome placebo; election concentration; control attribution; end-date, 2024-election, worst-case-outcome and T5 robustness) and P2 (earliest-horizon entry, declared ask, R_ann excess over 4.5%) on P SCREEN", "family": "creative_batch_11", "priority": 25, "expected_value": "P verdicts", "data": ["history/h11_pol/screen + outcomes_guarded (opened here)"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0239_cb11_census_PA"], "argv": ["scripts/run_cb11.py", "screen", "--family", "P"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch11/results_P.json", "trials.jsonl (cb11_test + creative_batch_11:P)"], "next_action": "advanced: commit q0236", "notes": "DRAFT-REVISED round 1 (items 1, 3, 4, 5). Every result labelled 'L1, hindsight end date'. Refuses unless GP, GPP and the P coverage audit passed (else writes the counted not-run/not-testable lines)."}
{"id": "q0234_cb11_screen_A", "title": "CB11-A: A1 (quiet minus spike continuation; p = max over event, day X and 3-day blocks of t; label-swap placebo; lagged-attention attribution; causal-volume robustness) and A2 (taker follow in quiet big moves, declared costs) on SCREEN events", "family": "creative_batch_11", "priority": 25, "expected_value": "A verdicts", "data": ["history/h11_attn/screen"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0239_cb11_census_PA"], "argv": ["scripts/run_cb11.py", "screen", "--family", "A"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch11/results_A.json", "trials.jsonl (cb11_test + creative_batch_11:A)"], "next_action": "advanced: commit q0237", "notes": "DRAFT-REVISED round 1 (items 9, 10). Refuses to open holdout/; refuses unless GA0, GA and the A coverage audit passed (else counted lines)."}
{"id": "q0235_cb11_rep_W", "title": "CB11-W: W1-rep (refit on ends [2025-10-01,2026-06-09)) and/or W2-rep on sealed W_hold; GWC on W_hold must pass", "family": "creative_batch_11", "priority": 25, "expected_value": "L2 verdicts", "data": ["creative_batch11/w (W_hold rows)", "history/h11_wprints/holdout"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0232_cb11_screen_W"], "argv": ["scripts/run_cb11.py", "rep", "--family", "W"], "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch11/results_W_rep.json", "trials.jsonl (cb11_replication)"], "next_action": "pass: Stage P-W registration draft", "notes": "DRAFT-REVISED round 1. Only for advanced tests; verifies the seal hashes first."}
{"id": "q0236_cb11_rep_P", "title": "CB11-P: P1-rep and/or P2-rep on sealed HOLDOUT ends [2026-01-01,2026-09-01) (label 'possibly touched holdout (L1)' if the C1/T5 ids were absent)", "family": "creative_batch_11", "priority": 25, "expected_value": "L2 verdicts", "data": ["history/h11_pol/holdout"], "resources": {"mem_mb": 600, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0233_cb11_screen_P"], "argv": ["scripts/run_cb11.py", "rep", "--family", "P"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch11/results_P_rep.json", "trials.jsonl (cb11_replication)"], "next_action": "pass: Stage P-P registration draft", "notes": "DRAFT-REVISED round 1 (item 5)."}
{"id": "q0237_cb11_rep_A", "title": "CB11-A: A1-rep and/or A2-rep on sealed HOLDOUT events", "family": "creative_batch_11", "priority": 25, "expected_value": "L2 verdicts", "data": ["history/h11_attn/holdout"], "resources": {"mem_mb": 900, "cpu": 1, "lane": "cpu"}, "depends_on": ["q0234_cb11_screen_A"], "argv": ["scripts/run_cb11.py", "rep", "--family", "A"], "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch11/results_A_rep.json", "trials.jsonl (cb11_replication)"], "next_action": "pass: Stage P-A registration draft", "notes": "DRAFT."}
```

## 5. Code needed (not written by this document)

- `backend/astrolabe/research_lab/cb11_wait.py`: field-restricted frame reader (whitelist, refusal of end ≥ 2026-07-01
  outside rep, guarded `outcome_prices` accessor), union and key drops, features f1-f7 (New York clock across DST
  changes; f7 causal rolling median), the frozen HGB fit and baseline, `R` with cluster bootstrap, day-block permutation,
  attribution refits; W2 transaction aggregation, decided-entry rule, `R_ann_h`, tail gate (reuse CB1 code), S arm.
- `backend/astrolabe/research_lab/cb11_pol.py`: politics and control frame walker (weekly windows, `start_date_max`
  prefilter, split-until-uncapped), whitelist parser, life and outcome rules, `prices-history` point rule, activity
  check, favourite orientation, P1/P2, the GPP and placebo copula simulation, election-concentration drops.
- `backend/astrolabe/research_lab/cb11_attn.py`: frame, entity rule (imports `external_news.derive_query`; stop list;
  summary-type client), audit-sample writer, pageview fetcher (reusing `fetch_pageviews`' URL rule with the 48 h lag and
  ≤ 1 rps), transaction aggregation (shared with W), `P_end`, `A_X`, `M`, `C`, A1/A2, label-swap placebo, lagged
  attribution.
- Reuse: `cb9_common`/`cb10_common` (refused roots, disk and free-disk guards with cap 40, exit 75, manifests, cluster
  bootstrap and small-G rule) where the interface fits; `history_backfill.Limiter`, `live_pass_or_lock()`.
- `backend/scripts/run_cb11.py` with subcommands as §4; refuses analysis before the freeze hash.
- Tests (`test_cb11_wait.py`, `test_cb11_pol.py`, `test_cb11_attn.py`, `test_run_cb11.py`): whitelist fixtures with
  every forbidden field; the W_hold refusal; f7 uses no close at or after `t`; f1/f2 across 2026-03-08 and 2026-11-01;
  the 21 d cap and the W_fit determination date; the decided-entry boundaries (`t + 5 min` inclusive, `t + 60 min`
  exclusive, `v = 0.95` qualifies); `R_ann_h` floor; the `prices-history` point rule (stamp + 600 s strictly before
  `t`); favourite orientation at `p = 0.5`; the 48 h pageview rule at day boundaries; `A_X` with a zero median; the
  label-swap within day; no census path receives a wait, outcome, mark or P&L; holdout refusals; guarded files opened only
  by screen/rep; `battery2` kinds; batch-Holm k1 = 6 fixed.

- **Round-1 additions.** `cb11_wait`: guarded `uma_status`; no status filter; `w-censoring` (seeded windows, `closed=false`
  counts, GWC); B1 and the two-baseline decision; the category x month target permutation; trigger/execution split with
  the `τ + 60 s` next-transaction rule and the "unfilled" label; recorded capacity `q_i`; the chronological
  capacity-capped pool ($1k/$10k/$100k; excess over 4.5%); the worst-case status check. `cb11_pol`: the `[t_h − 7 d,
  t_h]` request with the distinct-values activity proxy; `late_close`/`edit_detected` flags (frozen date regex); the
  frozen 2024-election keyword rule; the week-factor copula and max-of-ways SD in GPP and the placebo; `Y_f = 0.5` for
  unclean outcomes with the worst-case check; `R_ann − 4.5%`; the liquidity stratum. `cb11_attn`: pageviews from
  2026-01-01, the complete-9-day, median ≥ 50 and 30-day-history rules; the non-`vol_ok` stratum and inverse-fraction
  weights; pre-X print notional; the 3-day-block cluster way; coverage failures by arm. Runner: per-family census
  (`--family W`, `--family P,A`); every screen and census refuses an incomplete fetch manifest. Tests for each.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Decision |
|---|---|---|---|
| Stage 1: W1, W2, P1, P2, A1, A2 | 6 | `cb11_test` + `:W`, `:P`, `:A` (3) | p < 0.01 each; batch-Holm label (α 0.01, k1 = 6 fixed); BY triage. Counted with p = 1 if a gate or audit fails |
| Stage 2: each `-rep` (if its Stage 1 advanced) | ≤ 6 | `cb11_replication` | one Holm over CB11 Stage 2, one-sided α 0.05 |
| Smoke, census, gates, strata, variants, descriptives | 0 | `cb11_descriptive` | - |
| **Total** | **6 fixed + ≤ 6 conditional = 6-12 (unchanged in round 1)** | | cumulative 1,156 (committed, host-unioned) → ≥ 1,162-1,168 plus CB6-CB10 |

**Host compute.** Under 3 CPU-hours at nice 19 (W1 fit and 200-draw placebos about 40 CPU-minutes; GPP and P placebos
about 15 plus the round-1 week-factor GPP about 15; A about 20; W2 pool simulation under 1); peak RAM 0.9 GB.
**Network (round 1 item 11).** ≤ about 74,000 requests in total (≤ about 66,000 Polymarket, mostly P's `prices-history`;
≤ about 6,000 Wikimedia/Wikipedia), about 10-11 h of `net`-lane wall time at 2 rps (Wikimedia at 1 rps). **Disk.** ≤ 0.25 GB.

**Dates (estimates).** Code and the freeze check about 2026-10-18/19. W can then run end to end on the `cpu` lane plus
two short `net` jobs (q0224 ≤ 5 min, q0223 ≤ 2 h), so **W1 and W2 can still screen by about 10-20/21, before
`T_seal`** (round 1 adds no W fetch beyond q0224). The census (q0231) depends on every family's seal, so for W to screen
early the census runs per family (`census --family W`, same gates; a family's census never reads another family's
files). P and A fetches need about 8-9 h of the idle `net` lane on about 10-19..21; their census, freeze and screens
follow if the lane stays idle, otherwise after the `T_seal`-bound jobs, with no rule change.

## 7. Main scientific risks

1. **W measures schedule, not proposers.** A large share of the wait's predictability may come from `endDate`
   conventions (date-only placeholders, game times) rather than proposer timing. The schedule and decided-unit
   attributions decide the label; the advance and the capital-time claim do not depend on it. Without the on-chain
   variant, proposal lag and liveness are not separated.
2. **W2's gross is tiny and the tail decides.** Entries at 0.95-0.995 gross 0.5-5c; one wrong "decided" unit loses about
   97c. The tail gate and an MDE of about 2c mean W2 can only pass a carry much better than CB1-A suggested. Entries are
   transaction prices plus a declared half-spread, not recorded asks (L1).
3. **Reused frames.** W's population comes from frames whose sampled markets were screened (dropped by key); the frames'
   window sampling and fetch dates shape the population (ends after 09-10 excluded). Disclosed and labelled.
4. **P is cluster-limited and literature-led.** Elections concentrate outcomes in a few weeks and events; the MDE (about
   4.5-7c) detects only a large compression, and the GPP gate may stop P before it runs. The price is `prices-history`
   (mid-like), and P2's ask is declared; both are disclosed L1 limits, removed only in Stage P-P.
5. **A's timing and entity map.** The 48 h publication rule puts the feature 3 days after the attention day, so A can only
   find a slow drift. Entity matching is crude (probe 6: generic hits); the type filter and the 80% precision audit are
   the guards. GA may fail on the spike count (power estimate about 150-200 spike units).
6. **Look-ahead in A's selection.** The end-of-life volume filter keeps markets that became active (as CB10-B), shared by
   both arms.
7. **Same calendar.** A's HOLDOUT is same-calendar (L2); W and P replications are out-of-time. P and A share April-
   September 2026 with HB2, CB8-CB10 (markets disjoint by key; later batches must add CB11's ids to their keys).
8. **Queue.** CB11 `net` jobs yield to every `T_seal`-bound job; if those run first, P and A slip past 10-22 with no rule
   change.

## 8. Next actions

1. **Challenger review: done** (round 1, §9-§10; one challenge, one response, no second round).
2. Write `seals/cb11_rules.json`, `cb11_wait.py`, `cb11_pol.py`, `cb11_attn.py`, `run_cb11.py` and
   tests (implementer). Then the **code-against-design freeze check** (`science-reviewer`). Commit q0220, then
   q0221-q0224 (W first: it is the only family that can finish Stage 1 before `T_seal` for certain), then q0225-q0230.
3. Census q0231 (W) → freeze of the W part of `model_specs/cb11_v1.json` → q0232; census q0239 (P, A) → P/A freeze →
   q0233, q0234; conditional jobs by the stated triggers. One declaration file; the W and P/A parts are hashed
   separately so the W freeze never waits on P/A data, and no rule of either part changes after the other's read.
4. CB9/CB10 exclusion increments (q0182/q0201) add CB11's frame ids (note for their owners).
5. Ledger lines for every counted result; checkpoint and plain-English dashboard updated by the orchestrator.

## 9. Challenger review, round 1 (science-reviewer, 2026-10-17)

Verdict: **ACCEPT_WITH_REQUIRED_CHANGES** for W, P and A. Faithful summary of the items:

**Required.**
1. **P activity filter is post-origin.** Reaching `t_h − 7 d` within ≤ 2 newest-first Data API pages depends on how much
   trading happened after `t_h`, and the 10,000 offset cap drops the busiest markets. No primary condition may use page
   reach; use a causal proxy (`prices-history` changes in `[t_h − 7 d, t_h)`) or no filter; the verified subset becomes a
   variant.
2. **W `uma_status`/`closed` are outcome-adjacent.** CB1 guarded `uma_status` as an outcome column, and the draft read
   its mix (96%). Move it to the guarded file; W1 keeps every closed row whatever its status; before the freeze, count
   the right-censored share with a cheap Gamma `closed=false` query per window, > 2% → W1 "not testable (censoring)";
   W2 includes disputed units, with a worst-case `Y = 0` robustness check.
3. **P horizons anchor on the final, possibly edited `endDate`.** Add a binding robustness check excluding `closedTime >
   endDate + 7 d` and detectable edits; label the cell L1 "hindsight end date"; Stage P-P uses end dates recorded at the
   origin.
4. **P MDE and placebo ignore common shocks.** Add a shared week/election factor to the copula; compute `MDE_P1` from the
   larger SD across the two cluster ways; add a binding robustness check excluding events linked to the 2024 US general
   election (frozen keyword list).
5. **P holdout contamination.** The T5 frame (`RESOLUTION_DEV_STUDY.md` lines 20-25; 314 politics markets, outcomes
   seen) overlaps SCREEN and HOLDOUT. The T5 and C1 exclusion is mandatory; if the ids cannot be retrieved, label HOLDOUT
   "possibly touched".
6. **W2 enters at the triggering print (no latency)**, and the 10% annualised floor does not bind in practice. Enter at
   the next transaction at or after `τ + 60 s`; add a chronological single-pool simulation capped by recorded capacity,
   report $/month, and gate on it or declare 10% non-binding.
7. **W1 baseline too weak.** Advance needs `R ≥ 0.20` vs B0 **and** `R ≥ 0.10` vs B1, the per-category rolling f7
   median.
8. **W1 placebo ill-defined** (day-block reassignment across days of different sizes). Specify the mapping, or permute
   targets within category x month.
9. **A entity hindsight.** Require a baseline median ≥ 50 views/day, all 9 days present, and a first non-zero view ≥ 30
   days before X; missing days are "unavailable", never filled.
10. **A overlapping targets and look-ahead.** Add a third cluster way of 3-day blocks of `t`; add a binding robustness
    check replacing `vol_ok` (look-ahead) with pre-X traded volume from prints; report print-coverage failures by arm.
11. **Budget inconsistent.** q0226 said about 8,500 markets but the caps add to 10,500; 3 horizons plus ≤ 2 pages gives
    about 52-95k requests, not 35k in 4 x 110 min. Recompute; an incomplete fetch is "pending", never analysed partially.

**Optional (adopt where cheap).** P `R_ann` as an excess over a 4-5% risk-free rate; count voided/unclean-outcome markets
(removing them is post-origin selection); a P liquidity stratum; report W's frame-source mix by window; disclose the
CB1-A1 −4.00c prior next to every W2 line.

**Also.** State the cumulative count from the committed, host-unioned `trials.jsonl`, not the 1,141 / 1,156 pair.

## 10. Response to challenger round 1 (2026-10-17)

Every required item is adopted; two are implemented in a stated, stricter form (items 2 and 10); nothing is rejected.
No floor, threshold, gate, alpha, cap or test count was relaxed (6 fixed + ≤ 6 conditional, unchanged).

| Item | Response | Where |
|---|---|---|
| 1 | **Adopted.** One `prices-history` request per unit now spans `[t_h − 7 d, t_h]`; "active" iff the series takes ≥ 2 distinct values among points known before `t_h` (causal; no extra requests). No primary condition uses Data API reach; the verified-activity check is a reported variant on the reachable subset. Caveat stated: `prices-history` is mid-like, so the proxy can count quote changes without trades (a looser filter, which keeps more units rather than selecting on future trading) | §CB11-P Units, §2.7, q0226 |
| 2 | **Adopted, gate made stricter.** `uma_status` is guarded (W and P); W1 and W2 keep every closed row; the drafting read of the 96% mix is disclosed (§0.2). Censoring: q0224 counts `closed=false` markets in a seeded 300 of the frames' windows (≤ 300 requests) instead of every window (about 4,000); to compensate, gate GWC fails on the **one-sided upper 95% bound** > 2%, not the point estimate. GWC binds W1 and W2 (the reviewer named W1; W2 draws on the same frames). W2 keeps disputed units (unclean outcome → `Y = 0` in the primary) and adds the worst-case status check | §1.3, §1.4, §2.7, §CB11-W, q0222, q0224 |
| 3 | **Adopted.** `late_close` (`closedTime > endDate + 7 d`) and `edit_detected` (market vs event `endDate` > 1 day apart, or an explicit date in the question/title > 1 day from `endDate`, frozen regex) flags; a binding exclusion check (p < 0.01 and `Ē ≥ 1.5c`); every P result labelled "L1, hindsight end date"; Stage P-P anchors on capture-recorded end dates | §CB11-P, §2.9, q0225 |
| 4 | **Adopted.** Copula `Z_m = √0.2 · W_week + √0.4 · V_event + √0.4 · ε_m` (loadings declared) in GPP and the binding placebo; `MDE_P1` uses the max of the across-draw SD and the mean event-way and week-way SEs; a frozen 2024-election keyword rule with a binding exclusion check. The 6.0c GPP threshold is unchanged; "not run (power)" is now more likely and is said so | §2.7, §CB11-P |
| 5 | **Adopted.** C1 and T5 ids are a mandatory exclusion source; if absent, P reps are labelled "possibly touched holdout (L1, not L2)" and a binding SCREEN robustness check drops ends in the T5 overlap `[2025-10-11, 2026-01-01)` | §1.3, q0221, q0236 |
| 6 | **Adopted, gate chosen.** Trigger at `τ`, execution at the next transaction at or after `τ + 60 s` (unfilled → counted, 0 per trigger). A chronological single-pool simulation ($10,000 declared; $1k and $100k reported) caps each purchase at the recorded traded size in `[τ + 60 s, τ + 60 min)`, reports $/month, and **gates**: its annualised return in excess of 4.5% must be ≥ 10%, in addition to (not instead of) `R_ann_h ≥ 10%` | §2.1, §2.4, §CB11-W, q0232 |
| 7 | **Adopted, with p for both.** B1 = the unit's f7 (B0 fallback where NaN, share reported). Advance needs one-sided p < 0.01 and the floor for **each** of `R_B0 ≥ 0.20` and `R_B1 ≥ 0.10` | §2.4, §CB11-W |
| 8 | **Adopted (the reviewer's second option).** Unit-level permutation of `L` within each `fee_category` x calendar month, predictions and baselines fixed, both p thresholds re-applied; advance rate ≤ 1.5% over 200 draws | §CB11-W |
| 9 | **Adopted.** Pageviews fetched from 2026-01-01; all of `X − 8 .. X` present, baseline median ≥ 50, first non-zero day ≥ 30 days before X; missing days "unavailable (pageviews)", never filled; the lagged check uses the same rules on its own days | §1.2, §CB11-A, q0229 |
| 10 | **Adopted; the volume check needed a new stratum.** Third cluster way (3-day blocks of `t`), p = max over three ways. A robustness check confined to `vol_ok` markets cannot remove a look-ahead that selected them, so the frame walk now applies no volume filter and a seeded 1,000-market non-`vol_ok` stratum is drawn before any read; the binding check uses both strata with causal pre-X print notional ≥ $2,000 and inverse-sampling-fraction weights. Coverage failures and pageview-unavailable units reported by arm | §2.3, §2.7, §CB11-A, q0227, q0229 |
| 11 | **Adopted.** q0226 recomputed for 10,500 markets: 31,500 `prices-history` requests (price and proxy in one) + ≤ 8,000 Data API pages (politics SCREEN only, for the print-price robustness and the variant) = ≤ 39,500, about 5.5 h, `max_runs` 5 x 110 min. All jobs: total ≤ about 74,000 requests, about 10-11 h of `net` lane. Every fetch writes a `*_complete` status; census and screens refuse an incomplete manifest ("pending", never partial) | §2.8, §4, §6 |
| Optional: risk-free | **Adopted** for P2 (`R_ann − 4.5% ≥ 10%`) and W2's pool gate | §2.4 |
| Optional: unclean outcomes | **Adopted.** No status/cleanliness filter in P's frame; unresolved, voided or unclean markets scored `Y_f = 0.5` (venue void convention), counted, with a binding worst-case `Y_f = 0` check | §CB11-P |
| Optional: liquidity stratum | **Adopted** (reported): terciles of the pre-origin distinct-value count | §CB11-P, §2.7 |
| Optional: frame-source mix | **Adopted** (census, by window) | §2.7 |
| Optional: CB1-A1 prior | **Adopted** next to every W2 line | §CB11-W |
| Count | **1,156** from the committed `trials.jsonl` at `e721331` (host-unioned since `15ec365`) | §0.2, §2.5, §6 |

**One structural clarification (not requested).** The single census q0231 depended on every family's seal, which
would have held W behind P and A's 8-9 h of fetching. It is split by family (q0231 W, q0239 P and A; same gates, a
family's census never reads another family's files), and the W and P/A parts of `model_specs/cb11_v1.json` are hashed
separately, so W can still freeze and screen before `T_seal`. Nothing about any test changes.

## 11. Code-against-design freeze-check fixes (2026-10-18)

The `science-reviewer` code-against-design freeze check of the W and smoke code (2026-10-18) found ten blocking and nine non-blocking items. Every change
below tightens or clarifies; no floor, threshold, gate, alpha or cap was relaxed. Where the table says "design", the text above is amended accordingly.

| Item | Change | File |
|---|---|---|
| B1 | **Declared amendment of §1.4.** The rules file is v2 and hashed in parts: part W (common + smoke + W rule functions) now; P and A rules in a separate `seals/cb11_pa_rules.json` fixed before the **first P/A request** (not before q0220/q0221). Justification: W and P/A fetch disjoint data, and W jobs verify only part W, so adding P/A code or rules can neither alter a W rule nor refuse a pending W job. W verification imports no P/A module. Shared functions stay in part W | `cb11_common.py` (`rules_part_doc`, `verify_rules(part=)`), `seals/cb11_rules.json` |
| B2 | q0221 and q0224 (and q0223's regex) get `repeat` blocks ending on their completion status (q0221: `exclusion_keys_complete` or `disjointness_unverified`; stalls end the repeat), because in-progress chunks exit 0 | drafts q0221, q0223, q0224 |
| B3 | C1/T5 id lists are mandatory in code: q0221 exits 75 (pending, nothing written) while either is unstaged; `--allow-absent-c1-t5` records them absent permanently and is never in a draft | `cb11_common.exclusion_keys`, `run_cb11.py` |
| B4 | `h2_main` and `h3_power` `sample.csv.gz` are mandatory and sha256-pinned: absent, unset pin or mismatch is a refusal (exit 2). Pins are `TODO-COORDINATOR` until the coordinator fills `H2_SAMPLE_SHA256` / `H3_SAMPLE_SHA256` from a read-only `sha256sum` on the host and regenerates the rules (and the sha in the drafts) before q0220 | `cb11_common.py` |
| B5 | W2 excludes markets whose print span is not covered (`status` ok, `covered` 1, not truncated) and counts them `unavailable`; the census does the same; availability below 60% is "not testable (availability)" (§2.6(iv)). `oldest_ts` is recorded, not used as an extra exclusion (a thin market's whole history can be newer than `t − 6 h`) | `cb11_w.py` |
| B6 | GW2 and the S count use **filled** units (entry rule satisfied); `no_room` and unfilled are reported as triggered, not decided. The census cannot see the close, so it stands in the end of the stored span (`t + 6 h`) | `cb11_w.census_w` |
| B7 | Binding W2 robustness: mean net > 0 in every calendar month of the evaluated window (a month without an S unit is not met) | `cb11_w.w2_robustness` |
| B8 | Alpha is a parameter. Stage 1: p < 0.01 strict. Stage 2: p ≤ 0.05/k inclusive and no other p gate (floors unchanged). The Stage-2 placebo is judged at min(0.05/k, 0.01), never looser than Stage 1's calibration level (a placebo at 0.05 would exceed the 1.5% cap even for a calibrated test) | `cb11_w.py` |
| B9 | The pool return is annualised over the evaluated window: W_screen 122 d (Stage 1), W_hold 71 d (Stage 2) | `cb11_w.w2_stat` |
| B10 | Unverified disjointness stalls P and A only (§1.3); W proceeds, the state is recorded in the frame report and census | `cb11_w.w_frame` |
| N1 | A censoring window capped at 5 pages fails its set's GWC (a lower-bound count cannot confirm the bound; this can be harsh in dense windows and is accepted). A set with < 60% available windows also fails. A `closed=true` count per window (diagnostic `frame_to_gamma_closed`) closes the frame-to-query gap | `cb11_w.py` |
| N2 | Undeclared deviations now declared. (a) **W key rule: market id and event id only**: the frames carry no `negRiskMarketID`. (b) **Series rule drops are "not computable"** (no series id in the frames), so the §2.7 census cannot report them; §1.3 and §2.7 amended. (c) **Capacity is not split by token**: the size is the hash-aggregated total in `[τ + 60 s, τ + 60 min)` (both tokens), which can overstate the recorded capacity of token k; reported as such. (d) `takerOnly=true` on the Data API (one print per taker order). (e) **§2.1 "or the frame's fee field if larger" is dropped**: the W column whitelist has no fee field; the category rate alone applies. (f) The pool buys at `c + fee` per share (design: `c`), which is stricter | `cb11_w.py` |
| N3 | Budgets: q0223 allows up to 4 pages × 7,000 markets = 28,000 requests (about 3.9 h at 2 rps, 5 chunks of 85 min; design ≤ 14,000); q0224 up to 2 queries × 5 pages × 300 windows = 3,000 (design ≤ 300); total ≤ about 91,000 (tables §2.8 and §4 amended) | drafts q0223, q0224 |
| N4 | The "h3-only" robustness subset excludes rows present in both frames (and "h2-only" likewise) | `cb11_w.w1_robustness` |
| N5 | The census verifies the rules; screen and rep re-check the fetch manifests and file hashes; seal copies must be tracked and identical to HEAD (`spec_committed`); results record the W freeze-part hash and the census sha256 | `run_cb11.py`, `cb11_common.verify_holdout_seal`, `cb11_w.verify_hold_seal` |
| N6 | W1 MDE recomputed from the census end-date count (0.02 × √(120 / end-dates) × (z₀.₉₉ + z₀.₈₀)); the BY label and `battery2.cumulative_count()` are recorded in `results_W.json`; the pool utilisation is time-weighted invested cost over the pool; the sports/crypto stratum is reported for W1 (descriptive, `units_nonprimary.csv.gz`) and "killed in category" (losing share by category) for W2. There is no W2 sports stratum: the W2 sample is primary markets only | `cb11_w.py`, `run_cb11.py` |
| N7 | q0235 depends only on `results_W.json`: the Stage-2 k counts the family's advances plus every test of a family whose Stage-1 result is not yet final as advancing (`assumed_pending`), so α/k is at least as strict as the final one and is not loosened later. Amends §2.3 "k fixed when the last Stage-1 result is final" for early finishers | `cb11_common.stage2_k` |
| N8 | Gate on the censoring-window reconstruction: if fewer than 99% of a frame's closed rows (ends in the W windows) fall in the reconstructed 15-minute windows, q0222 stalls with "not testable (censoring windows)" | `cb11_w.w_frame` |
| N9 | "unfilled" splits into `unfilled_no_trade_before_close` (the stored span reaches the close) and `unfilled_outside_window` (the close lies beyond `t + 6 h`); both are counted, excluded from per-share means and from decided | `cb11_w.decide_and_enter` |

### Re-check amendments (2026-10-18, science-reviewer ACCEPT_WITH_FIXES)

| ID | Amendment | Where |
|---|---|---|
| R-b1 | Seal-time `DROPPED_*` rows are never analysed: `rep_w` drops them from the W1 hold units and the W2 sample; `read_frame` / `load_origins` of P and A exclude them for the HOLDOUT (`cb11_common.dropped_market_ids`). Verify-round: on a sealed run `dropped_market_ids` refuses (exit 2) if `drops.csv.gz` is missing or its sha256 differs from `drops.drops_sha256` in the seal (the file is outside `holdout/`, so the listing hash does not cover it). `seal_w` now computes W drops over every W1 hold unit (`units_hold.csv.gz`) plus the W2 hold sample, deduplicated by market id (ids and event ids only), so W1 hold markets outside the W2 sample are checked against later seal copies too | `cb11_w.rep_w`, `cb11_p`, `cb11_a`, `run_cb11.seal_w` |
| R-b2 | W seals alone (q0230, `--family W`); P and A seal in q0238 (`--family P,A`); q0231 depends on q0230 only, q0239 on q0238; both seal jobs are on the `net` lane with network gamma-api (one net job at a time, 2 rps) | drafts q0230, q0231, q0238, q0239 |
| R-c1 | q0227 and q0229 (and q0225, q0226) repeat until their completion status or a terminal stall | drafts |
| R-c2 | A used-up Wikipedia budget (3,000) or 3 consecutive Wikipedia-error resumes without a new cached summary ends q0227 in the terminal counted "not testable (source)" stall (`wiki_pauses.jsonl`); q0229 and the census see the stall | `cb11_a.attn_frame` |
| R-d1 | `--stage2-k` for P / A is refused below the conservative own-family count (`stage2_k(own=...)`) while the other Stage-1 results are missing | `cb11_pa.stage2_k_pa` |
| R-d3 | The P/A screen re-checks the fetch manifest, file hashes and the committed holdout seal; P/A results record the P/A freeze-part and census sha256; the P/A census records the P/A rules sha | `run_cb11.py` |
| R-B6 | `w2_units` counts only filled units as decided (no_room and unfilled are triggered, counted, not decided) | `cb11_w.w2_units` |
| R-B8 | P and A Stage 2 judge p <= alpha / k inclusive (as W); Stage 1 stays p < alpha | `cb11_p`, `cb11_a`, `cb11_common.p_ok` |
| R-F | `open_30/60/90` leave the P frame (separate `opens.csv.gz`, census-forbidden, read only by the fetch); the A frame's `close_epoch` leaves the frame file (`closes.csv.gz`, merged by `read_frame`). Verify-round: `read_frame` attaches `close_epoch` for every job including the census; the census uses it ONLY for the open-at-t count (no close mark, outcome or net is computed in the census), and `close_epoch` is deliberately not in `CENSUS_FORBIDDEN`. A missing `closes*.csv.gz` is a refusal, not an empty fallback. Census HOLDOUT N (A): excludes seal-time drops when the seal exists, else labelled `UPPER BOUND`; W census HOLD counts are frame-time listing counts, labelled `UPPER BOUND` with the seal-time dropped-market count alongside | `cb11_p`, `cb11_a`, `cb11_w` |
| R-pin | `H2_SAMPLE_SHA256` / `H3_SAMPLE_SHA256` filled (host `sha256sum`, 2026-10-18); rules regenerated | `cb11_common` |

Open for the coordinator: stage the C1/T5 id lists (B3). (The two sample pins (B4) and the rules and draft shas were filled on 2026-10-18.)

### 11.1 Smoke amendment (q0220, 2026-10-18; engineering gate, outcome-blind, counts only)

q0220 never wrote a result (parked on the host). Review of the smoke code against CB11-F found two defects and one design-versus-code mismatch; none changes an analysis threshold, floor, formula or gate.

- **Picks.** The paging criterion keeps its two 2024-05 weeks unchanged, but those weeks contain no market with life >= 100 d, so the `prices-history` and Data API criteria would have failed vacuously (`per: {}`) and made P, W2 and A "not testable (source)" for a sampling artefact. The 2 picks now come from a separate deterministic out-of-window search: one-week windows going back from 2024-06-24 (all ends before P's earliest SCREEN end), one Gamma request per week, at most 8, stopping when 2 markets with life >= 100 d, two tokens and a condition id are found; picks are ranked by the seeded hash as before. If the bounded search finds fewer than 2, the criteria fail with the explicit reason `no_picks` (counted), never a silent empty `per`.
- **wiki_lag.** Design section 2.2 says: if the last published pageviews day is more than 48 h old, "the lag moves to 72 h before the freeze (outcome-blind; recorded) and A's origin to `X + 4 d`". The code had `wiki_lag` inside A's needs (so a fail stalled A "not testable (source)") and in the overall `pass`. Now: A needs `wiki_summary`, `wiki_pageviews` (the endpoint returned a newest day at all) and `data_api_reach`; `wiki_lag` is recorded but not part of the overall pass; q0227 reads the smoke (`smoke_origin_lag_days`) and stores `origin_lag_days` (3, or 4 after a `wiki_lag` fail) in `split.json`; the census, screen and rep use it (`candidate_units(..., lag_days)`; usable at `X + 1 d + 72 h`). The live probe (last day 20261015, 69 h after the day end) therefore moves A to the 72 h lag and the `X + 4 d` origin, as designed.
- Rules files `cb11_rules.json` (part W) and `cb11_pa_rules.json` were regenerated (no job had used them).
- **wiki_lag ceiling (review fix).** The 72 h fallback is itself a rule that can be too short. A new criterion `wiki_lag_ceiling` (newest published day at most 72 h after its end) is in A's needs and in the overall pass: if the newest day is older than 72 h at the smoke, A is "not testable (source)", counted, and no origin lag is applied. The fallback lag (4 d) applies only when `wiki_lag` failed and the ceiling held. No later A data job re-measures the newest published day, so the smoke is the only check. (The live probe, 69 h, passes the ceiling.) Rules part W and `cb11_pa_rules.json` regenerated again.

### 11.2 q0221 id sources and key reuse (amendment q0221b, 2026-10-19; engineering, outcome-blind, ids and keys only)

q0221 (exclusion keys) never completed: two 40-min timeouts, then an error at 01:33Z on 10-19 and a stop; it is parked on the host.
Review against §1.3 found the code did not match the design:

- **Wrong series source.** The code read `h7_cb4_series/walk_events.jsonl.gz` (the whole series event walk: 3,956,874 market ids)
  instead of the *sampled* unit frame. §1.3 excludes markets of every SAMPLED set; the walk is a discovery listing, not a sample.
  The source is now `h7_cb4_series/units.jsonl.gz` (13,657 market ids of the 1,922 sampled units). JSONL readers take market ids
  only from the top-level lists `markets`, `pred_markets`, `succ_markets`; every id must match `^[0-9]{1,10}$` (a Gamma market id),
  otherwise the run refuses.
- **Keys not reused.** The code looked up every id on Gamma even when a source already carried its keys (80,044 batches against the
  declared <= 400 requests, and a 70 MB partial against the 0.01 GB cap). Keys now come first from the `h8_tail_b` base key file and
  from CSV sources that carry `event_ids` / `neg_risk_market_id` / `series_ids` (rows with a non-empty `event_ids`; event and series
  ids united across sources, the first non-empty negRiskMarketID kept). Only the remaining ids are looked up (closed-first, 50 per
  request, resumable).
- **Declared request deviation.** A read-only host count on 2026-10-19 gives 504,314 new ids: 338,680 keyed from sources and 165,634
  looked up, i.e. 3,313 batches (3,313 to at most 6,626 requests with the not-closed retry; about 30-60 min at 2 rps). This exceeds the
  design's <= 400 estimate, which assumed every source carried keys; the CB1-CB4 sets, the seal copies and the C1/T5 lists carry none
  or only event ids. The request budget is an engineering limit, not a scientific gate.
- **Storage.** The partial is one compact gzip member per batch, charged to the unchanged 0.01 GB cap (about 2.6 MB), plus about
  2.4 MB of keys. A stored batch that does not match the current id list is a refusal.
- **Superseded run.** The run id is `exclusion_run11b`. q0221's partial `creative_batch11/exclusion_run11/` is kept untouched, and the
  code refuses to read, modify or use it (it is in the forbidden-run list).
- Unchanged: the W key rule (market id and event id), the mandatory C1/T5 lists (B3, never `--allow-absent-c1-t5`), the mandatory
  pinned h2/h3 samples (B4), the 2% missing-metadata rule (> 2% means disjointness unverified: P and A not testable, counted; W
  proceeds), every gate, floor, alpha and population. The q0220 smoke PASS stays valid (smoke code byte-identical; consumers check
  only the smoke version and criteria).
- **Review (science-reviewer, 2026-10-19, ACCEPT_WITH_FIXES).** (1) Where two sources disagree on a market's `negRiskMarketID`, the
  market is looked up on Gamma instead of reusing either source value (`_merge_keys` returns the conflicting ids; their count is
  `neg_risk_market_id_conflicts` in the report). (2) Source keys are snapshots taken when each source was fetched: a series id added to
  a market later would appear in a Gamma lookup but not in the reused keys. Event ids do not change, so the W rule (market and event id)
  is unaffected; only the P/A series rule could miss such a late series link, a known and accepted limitation.
- Rules part W regenerated: `6d3f1613d74431eb53de888e5dec83bac8f8c0eb516348d05a33919bb8582a33` (was `2d2bb169…`; an intermediate
  uncommitted `547ae308…` was never used); q0222-q0231 and the
  q0232/q0235 drafts carry the new sha and q0222 depends on q0221b. Tests: `tests/test_run_cb11.py` (q0221b block).

### 11.3 W censoring-window reconstruction used half-open windows (q0222 defect, 2026-10-19; engineering, outcome-blind, counts only)

q0222 stalled W as "not testable (censoring windows)" in 26 s: the N8 check found only 59.2% (h2_main) and 57.4% (h3_power) of
the frames' closed rows inside the reconstructed 15-minute windows. A read-only host check showed this is a code defect, not a
source limitation:

- The frames were built by `hb.fetch_frame` with Gamma `end_date_min = a`, `end_date_max = b`, and Gamma treats both bounds as
  inclusive; the q0224 count (`count_in_window`, "endDate in [a, b]") uses the same query. `cb11_w` instead tested the windows as
  half-open `[a, b)` (N8 match and `closed_rows_per_window`).
- Every unmatched closed row (h2_main 81,574 of 199,868; h3_power 94,273 of 221,169 in [W_fit start, W_hold end)) has `end_epoch`
  exactly equal to a reconstructed window's end `b` whose following quarter hour was not drawn (minute % 15 = 0, second 0), in every
  month and category (sports, crypto, unknown, weather, finance, ...). Markets end on round quarter hours, so the boundary carries
  about 40% of the rows. With `[a, b]` both frames match 100%; the seeds, window draws, lookback and request clocks were right.
- Fix: `cb11_w.in_frame_windows` and `closed_rows_per_window` use `[a, b]`, the walk's own convention (adjacent windows share only
  an endpoint). The N8 floor (0.99), the GWC gate (2% upper bound), the 300-window sample and every other rule are unchanged. Tests:
  `test_n8_window_membership_is_closed_at_both_ends_like_the_gamma_walk`, `test_n8_frame_completes_at_the_default_floor_when_rows_sit_on_window_ends`
  (the old rule reproduces the host stall on the same fixture).
- No W wait, outcome, print or net was ever read (q0222 stalled before writing any unit file; q0223/q0224/q0230/q0231 only copied
  the label). The q0222-q0231 outputs (`creative_batch11/w`, `w_censoring`, `census_W.json`, `history/h11_wprints`) keep their
  stall and are never rewritten; the v2 chain writes `w_b`, `w_censoring_b`, `census_W_b.json` and `history/h11_wprints_b`.
  The earlier "not testable (censoring windows)" label is a defect outcome, not a counted W result.
- Drafts (not promoted): q0222b, q0223b, q0224b, q0230b, q0231b (same argv and graph on the new ids); q0232/q0235 now wait on
  q0231b. Rules part W regenerated: `7734729d70a3f681db8562c7706abfa73b522b683c561f3a6f6adcf896c64e9d` (was `6d3f1613…`;
  changed sources: `w_frame`, `closed_rows_per_window`, new `in_frame_windows`; common `output_roots` now names `h11_wprints_b`).
  Before q0223b runs, the CB12-CB15 exclusion and refusal lists that name `h11_wprints` must also name `h11_wprints_b`.

### 11.4 q0227 MemoryError, replaced by q0227b (2026-10-19; engineering, no rule change)

q0227 (A frame) failed three times with `MemoryError` after 269-664 s under the worker's address cap (2 x mem_mb = 800 MB).
`walk_day` held every raw Gamma market of a day (about 8,000-13,000 objects of about 10 KB each in Python) before filtering, and a
capped parent window's 2,000-row batch stayed referenced through the split recursion; the baseline address space was already about
400 MB (imports about 264 MB plus the 525,227-id exclusion keys). Measured on 2026-04-29 (11,106 raw markets): traced peak 250 MB,
RSS 480 MB. Fix: each uncapped window is reduced to its `attn_record` rows at once (same markets, order and raw count), a capped
window's batch is released before recursing, and the assembly pass streams the per-day records (traced peak 64 MB, RSS 265 MB on
the same day). mem_mb 400 -> 600 for the assembly step (honest worst case about 0.8 GB address space). The 9 walk days already in
`h11_attn/frame_partial.jsonl.gz` are resumed (their rows are identical under the fix). The `repeat` block (re-check c1) is kept.
P/A rules regenerated: `125386f2a25492010bdc24aad219ba7c8b7b5e1a99eae9b370042a29475b1c50` (was `2d48bd73…`; only `cb11_a.walk_day`
and `cb11_a.attn_frame` changed). q0225/q0226 ran under `2d48bd73…` (their code paths are unchanged); q0229, q0238, q0239 and the
q0233/q0234/q0236/q0237 drafts carry the new sha; q0229 depends on q0227b. Test: `test_walk_day_keeps_only_filtered_rows_with_bounded_memory`.
