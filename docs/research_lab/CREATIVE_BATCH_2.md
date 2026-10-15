# Creative batch 2 (CB2): weather favourites, ladder dominance within and across events, placeholder-member gate

`evidence_role: exploratory_historical` (W screen and holdout) / `exploratory_dev` (L/X/P snapshot development) /
`prospective` (W stage P, L/X replication; data after the freeze) | status: **DRAFT design, not frozen; challenger
round 1 ACCEPT_WITH_REQUIRED_CHANGES, all required changes applied (see the two sections at the end).** Last updated
2026-10-16 00:49 UTC+1.

This file turns CH27, CH12, CH13 and CH10 from `CREATIVE_HYPOTHESES_2026-10-15.md` into declared, falsifiable tests, and
records why CH06, CH15 and CH16 are not tested now. It follows `CREATIVE_BATCH_1.md` (CB1) in structure and rules:
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades; every P&L is a paper rule at modelled or recorded prices.
- The primary quantity of the economic tests is net P&L per share (or per pair) at executable prices after fees, with
  `R_ann` and capacity beside it. Mechanism tests are labelled as such and are never read as profitability.
- Test tables bind only once the CB2 declaration hash is committed (`model_specs/cb2_v1.json`, the CB2 freeze).
- Queue specs (§5) are drafts; none is committed to `queue/jobs/` by this document.
- **Where CB2 says "as CB1 §x"**, the CB1 rule applies unchanged, including its challenger-round fixes.

## 0. Summary, selection and ranking

| Rank | Job | Hypothesis | Tests (counted) | Screen / dev data | Replication / prospective data | Queue ids | CPU-h | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 1 | **CB2-F** data | ladder list, extract additions, `h6_weather` backfill and seal | none | n/a | n/a | q0040, q0041, q0043, q0044 | 3 + 6-9 h network wall | 1.0 GB |
| 2 | **CB2-W** weather favourites (CH27) | the top-priced temperature bucket resolves YES more often than its ask implies | W2 (economic), W3 (mechanism); W1 reported only (not counted) | `h6_weather` SCREEN block (earlier end dates) | `h6_weather` HOLDOUT block (latest end dates), then stage P on captures | q0045, q0047, q0049 | 1.5 | 1.2 GB |
| 3 | **CB2-L** ladder dominance (CH12, CH13) | executable monotonicity violations persist 2h within events (L1) and across events (X1); cross-event touch violations are more common (X2) | L1, X1 (economic), X2 (mechanism) | extract `ladder_candidates/` filtered by the ladder list, captures before `T2_dev_end` | extract `ladders/`, captures in `[T2_rep_start, T2_rep_end)` | q0042, q0046, q0048 | 1.0 | 1.0 GB |
| 4 | **CB2-P** placeholder members (CH10) | a never-traded member's resting quote is executable against its sibling-implied value | counts-only gate (0); no P1 in CB2 | CB1 extract `negrisk/`, dev | none in CB2 | q0042 | 0.1 | 0.8 GB |

**Why this order.** The `h6_weather` fetch is network-bound (about 70-86k requests, §2.8) and must be sealed before the
W screen. The text-free ladder-candidate backfill must run before raw captures from 2026-10-11 become deletable under
the approved retention (deletion may start about 18 October; release copies remain); it no longer waits for the ladder
list. W has the largest samples and a short hold (1-3 days). L/X are cheap but may prove too rare to test. P is a
counts-only gate expected to close CH10; a P1 test would need its own later design.

### 0.1 Selection (pre-design census, 2026-10-15 23:00-23:30Z)

The drafting session ran read-only counts on 6 complete captures on the host (`snapshots/`, touch, `volume_num`,
`last_trade_price`, fee and tick fields; **no outcome was read**), plus 10 public Gamma requests for weather event counts
and 20 for question text. These counts shaped inclusion and are disclosed here; the coordinator may log them as one
`cb2_descriptive` line (counts 0).

**Outcome exposure of the drafting census (challenger item 10).** The weather-count requests listed **closed** weather
events ending 8-11 October 2026, and Gamma event responses carry `outcomePrices`. The drafting session took counts only,
but the payloads were in hand. Therefore every event with `end_at` in **[2026-10-08T00:00Z, 2026-10-12T00:00Z)** is
excluded from `h6_weather` (frame rule, counted, in the declaration hash). The per-month rates quoted below for Oct 2025,
Jan 2026 and May-Aug 2026 also came from Gamma event listings whose exact day windows were not recorded in this file;
the same exposure may apply to a few days in those months. That residual is disclosed, not removable (the days are
unknown). It can affect at most a few hundred of about 15,000 frame events, and no per-event outcome was printed or
kept. The 20 question-text requests concerned the 10 L/X proxy pairs (open, non-weather markets).
A further read-only count on 2026-10-15T23:40Z (one capture, `series_slugs` of weather-category rows, no prices or
outcomes) found 49 distinct temperature-series cities (45 "lowest" series plus 4 "daily-weather"-only cities). It was
used for the small-G rule (§2.3) and the city→timezone table (§CB2-W).

| Idea | Decision | Reason (numbers from the census unless stated) |
|---|---|---|
| **CH27** weather favourites | **include (W)** | 300-330 open weather events per capture, mostly 11-bucket temperature events; about 95-100 end per day (Gamma: 2/day in Oct 2025, 8/day Jan 2026, 60/day May-Aug 2026, 100/day Oct 2026). At 12-36h before `end_date` the favourite mid is mostly 0.30-0.60, median favourite spread 3.9c, 80% of favourites traded. Almost all are neg-risk (Gamma: 294 of 301 closed 8-11 Oct). `h2_main` holds only 173 sampled weather markets in 134 events (mostly one bucket per event), so a historical screen needs a whole-event backfill (`h6_weather`, §CB2-F). |
| **CH12** within-ladder dominance | **include (L1)** | IF-H2 counted 1,338 open rungs in 622 ladder events on 2026-10-12. A text-free proxy (non-neg-risk, non-sports, non-weather events with ≥ 2 end dates) gave 35-49 pairs per capture with `bid(D1) > ask(D2)`, but a text check of 10 of them found **none genuine**: all were survival ladders ("ceasefire continues through D", where falling prices are correct) or point-date markets ("on D"). The true incidence is unknown, so a direction-aware text grouper is required and testability is decided by the census. |
| **CH13** cross-event implied CDF | **include, reduced (X1, X2)** | Only date ladders across events (the same grouper with the single-event restriction lifted). Strike ladders and nomination/presidency templates need further text rules and are excluded from CB2. |
| **CH10** placeholder members | **include as a gate (P)** | "Never traded" must be `volume_num` missing or 0 **and** `last_trade_price` empty (the sidecar leaves `volume_num` blank, not 0, for 259 of 260 such members). Setups (exactly one never-traded member, all others traded and two-sided): 98-135 per capture, but gap ≥ 3c in only 1-2 per capture, and **2 unique setups across 6 captures in 3.3 days** (one persisted through all 6). A generalised bound version (a never-traded member's bid above `1 − Σ traded bids` by ≥ 3c) found 0 in 4 captures. CH10's own kill rule (< 2 setups/day with gap > 5c) is expected to trigger; the census also did not yet exclude augmented events, so these counts are upper bounds. |
| CH06 hazard residual | **defer** | The IF-H2 panel has no trades, so the "trade before t" rule (T5-DEV) cannot be met on it. The only trade-bearing ladder history is `h5_cb1_ladders`, CB1-B's sole replication set; its near/far rung outcomes are mechanically linked to CH06's residual. CB2 does not open it (§1.3). Path: a pre-2024 ladder backfill or prospective rungs, after CB1-B's verdict. |
| CH15 tick regime | **exclude (premise false)** | The tick is 0.001 for every market with mid < 0.04 (15,835/15,835) or > 0.96 (1,435/1,435) and 0.01 for 131,910 of 144,056 mid-band markets. The coarse regime is the middle, not the extremes, so "a 0.97 ask on a 0.985 fair value" cannot occur. A restated version (sticky fine tick in the mid band after an excursion) selects on the path and has no money route. |
| CH16 reward per adverse selection | **defer; preserve data** | 18,800 reward-enabled markets per capture. The test needs per-market fills over 7-day windows and level-by-level qualifying depth. Trade samples cover 2,000 rotating markets for 1h per pass (raw kept 3 days); sweeps store only the best level and 1c/5c aggregates. Optional data-only `rewards/` extract table (§4.3) so a later design has a window. |
| Non-convertible bucket overround | drop | Considered for weather (sum of bids up to 1 + fees in 9-10 events per capture). Weather events are neg-risk, so this is CB1-D's over-priced state, already tested. |
| CH11, CH08 (not ranked) | not testable | 32 "Other" markets in the whole open universe (CH11). `updated_at` changes in bulk (130,921 markets within one hour), so CH08 phase 1 would be noise. |

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB2 | Evidence ceiling |
|---|---|---|---|
| `history/h6_weather` (**new**, §CB2-F): temperature events ending 2025-06-01 to before `min(T_fetch6 − 3d, 2026-10-22)`, all buckets, minus the census days 2026-10-08 to 2026-10-11 | none | SCREEN block (earlier end dates): W Stage 1. HOLDOUT block (latest end dates, sealed): W Stage 2, read once, advanced tests only | L1 / L2-dev |
| CB1 extract `negrisk/`, `event_members` (+ new `event_text`) | CB1-D, CB1-A descriptive | W stage P (weather events are neg-risk); P gate (counts only) | L1 (dev) / stage P |
| CB2 extract `ladder_candidates/` (dev backfill) and `ladders/` (live, list-filtered) (**new**, §4.3) | none | L/X dev and replication | L1 / L2-dev |
| Raw complete captures, sweeps (host) | E-series, SB2, CB1 | read only by the extractor (pass step and one backfill) and by q0040 (one capture per day, market ids and fee fields only) | - |
| `h2_main`, `h1_first`, `h3_power` | many | **not read**, except their market-id lists to exclude events from `h6_weather` (the CH27 seed, C1, came from h2/h3 weather rows) | - |
| `h5_cb1`, `h5_cb1_ladders` | reserved by CB1 | **not read by any CB2 code path** (§1.3); only the committed seal copy `docs/research_lab/seals/h5_cb1_SEAL.json` is read, for market ids in its file table | - |
| `h4_seal` | reserved by SB2 | not read; no frozen parameter changes (§1.3) | - |
| IF-H2 ladder universe | IF-H2 | `if_h2` deadline parser and stem rule are reused as code; its data are not read | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T2_draft` | 2026-10-15T23:31Z | First draft. Only the §0.1 census (counts, no outcomes) has been computed |
| `T2_dev_start` | 2026-10-11T12:00Z | First sidecar capture (as CB1) |
| `T2_dev_end` | **2026-10-24T00:00Z** | L/X dev and the P gate use captures with `capture_start_utc < T2_dev_end` (about 12.5 days, about 150 captures) |
| `T2_rep_start` | **max(2026-10-26T00:00Z, first complete capture ≥ CB2 freeze commit + 2h)** | L/X replication and W stage P use only data from here |
| `T2_rep_end` | `T2_rep_start` + 28 d | End of the L/X window (about 330 captures) |
| `T2_W_end` | `T2_rep_start` + 56 d | W stage P: events with origin `end_at − 24h ≥ T2_rep_start` and `end_at < T2_W_end` |
| `T2_W_out` | `T2_W_end` + 7 d | W stage-P outcome read; still unresolved: censored (§CB2-W) |
| `T2_L_out` | `T2_rep_end` + 30 d | Realised-payoff read for L/X pairs |
| `T_fetch6` | request clock of q0043 | `h6_weather` data end; events must have `end_at < min(T_fetch6 − 3d, 2026-10-22T00:00Z)` |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 seal boundary. Every h6 price and trade row is capped at `min(T_fetch6, T_seal)` |
| `T_census_ex` | [2026-10-08T00:00Z, 2026-10-12T00:00Z) | `end_at` range excluded from h6 (drafting-census outcome exposure, §0.1) |
| `D_split` | rule, computed at q0044 | First HOLDOUT end date (§1.3); recorded in the seal before any outcome read |

### 1.3 Sealed and untouched data (named)

- **h5_cb1 and h5_cb1_ladders are avoided entirely.** The CB2 runner refuses run ids `h3_power`, `h4_seal`, `h5_cb1`
  and `h5_cb1_ladders`. CB1's one-read-per-family rule is unaffected. `h5_cb1` samples weather markets, so some
  `h6_weather` events may contain h5 markets. CB2 removes them without opening h5. q0043 reads only the committed seal
  copy `docs/research_lab/seals/h5_cb1_SEAL.json`. It takes market ids from the file names in that copy's file table
  (`prices/<market_id>.csv.gz`), reads ids only, and excludes and counts every h6 event with a member in that set.
  q0043 refuses to start until that copy is committed. (CB1 also tests no pre-end favourite in [0.30, 0.95).)
- **SEALED-H6 (time-ordered split; challenger item 2).** The earlier hash-parity split was not independent: the two
  halves shared dates and cities, and the Highest and Lowest events of one city-day could fall in different halves.
  `h6_weather` is now split **by end date** before any analysis:
  - S = the sampled events after all frame exclusions (§CB2-W population; censored events included).
  - Group key k(e) = the UTC date of the earliest `end_at` among the events with the same city and the same title date
    as e. So every event of one city-day shares a key.
  - `D_split` = the smallest UTC date d such that |{e ∈ S : k(e) ≥ d}| ≤ 0.40 |S|.
  - **HOLDOUT** = {k ≥ `D_split`}, the latest block (about 40% of events).
  - **Embargo** = {`D_split` − 2d ≤ k < `D_split`}, dropped from both halves and counted.
  - **SCREEN** = {k < `D_split` − 2d}.
  - Every event of a city-day is in the same half by construction.
  - `D_split` is computed by q0044 only from `end_at`, city and title date in `events.jsonl`. The outcome file is not
    opened. The value is written to `SEAL.json` and the committed seal copy before q0045.
  - Both halves are sealed (`h5_seal` machinery, generalised) before q0045. The screen refuses HOLDOUT and embargo ids.
    The HOLDOUT is read once, after the freeze, only for W tests that advanced. Every read is logged in
    `ACCESS_LOG.jsonl`. No job reads `outcome_prices` before the freeze (census guard as CB1 §2.9).
  - **Residual dependence, stated plainly.** The halves are adjacent in time and differ in regime:
    - season: the SCREEN spans about June 2025 to August 2026, while the HOLDOUT is about late August to mid-October 2026,
      one late-summer/autumn block;
    - city mix: cities added recently appear mostly in the HOLDOUT;
    - market maturity: liquidity and fees.
    A 2-day embargo removes only the shortest weather persistence. A HOLDOUT failure may therefore reflect a regime
    change and not noise, and a HOLDOUT pass is out-of-time but not out-of-season-cycle. Stage P (late October to
    December 2026) follows the HOLDOUT in time and is retained as the confirmation stage.
- **Results outside sealed directories (challenger item 1; CB1 freeze-fix 3).** q0045 and q0047 write to
  `research_lab/creative_batch2/W_screen/` and `research_lab/creative_batch2/W_holdout/`. Nothing is written inside
  `history/h6_weather/` after the seal except `ACCESS_LOG.jsonl` appends (outside the listing), so `verify_seal` stays
  valid.
- **h4_seal unchanged (challenger item 3; CB1 freeze-fixes 2 and 4 restated).**
  - **Fix 2 (cap).** Every h6 price point and trade row is capped at `min(T_fetch6, T_seal)`. Rows at or after the
    cap are dropped and their count is written to the manifest per market. q0043 refuses to start a new chunk at or
    after `T_seal`.
  - **Fix 4 (frame rules in code).** The declared frame rules are implemented and unit-tested, not only declared:
    - `end_at < min(T_fetch6 − 3d, T_seal)`;
    - the `T_census_ex` exclusion;
    - the h1/h2/h3 and h5 id exclusions;
    - the closed=false walk (§4.1);
    - a capped window is excluded entirely.
    Each rule has a count in the manifest.
  - Only with both fixes is `h6_weather` information-disjoint from SEALED-H4 analyses (origins ≥ `T_seal`), as CB1
    §1.3 argued for h5.
  - Disclosed separately: **W stage P overlaps SEALED-H4's period** (both use time after `T_seal`). Stage P reads only
    live extract captures and Gamma outcomes, never h4 data. Its population (temperature-event favourites) and
    statistics differ from SB2's frozen tests. The overlap is in calendar time, not in data files.
- **SEALED-P (CB2).** Every capture, sweep and extract row at or after `T2_rep_start`, used only under the committed CB2
  declaration. These captures overlap CB1's replication window (to 2026-11-09) and E011's window; the hypotheses,
  statistics and tables differ, and no CB2 job touches E011 or CB1 analysis inputs. Disclosed.

## 2. Common rules (deltas from CB1 §2)

### 2.1 Costs

As CB1 §2.1 (fee `r·a·(1 − a)` per taker leg with the sidecar schedule and `fee_policy="conservative"`; weather 0.05 in
history; maker fee 0; rebates only as an optimistic secondary; payout from Gamma `outcomePrices`; `R_ann` capital-time
ratio; capacity beside every `R_ann`). Additions:

| Item | Rule |
|---|---|
| Weather historical ask (W) | `a = min(p + h_W(p), 0.999)` with `p = p_fav(t + 2h)` (execution latency matched to stage P, §2.2), `h_W(p) = max(h(p), 2.0c)` (CB1 band table `h`; the census median favourite spread was 3.9c). Binding sensitivity `+0.75c`. A dev descriptive of recorded favourite half-spreads by band (captures before `T2_dev_end`, no outcomes) is reported, never used to change `h_W` |
| Recorded ask (W stage P, L/X) | Gamma `best_ask` of the token bought; NO side `1 − best_bid`. Depth-checked variant: the pass's first sweep with `ask_size_1 ≥ 5` (or `bid_size_1 ≥ 5` for a NO leg) |
| Ladder pair (L/X) | `C = (a_YES + f(a_YES)) + (a_NO + f(a_NO))`. Structural minimum payoff 1 (§CB2-L); `net = 1 − C`; capital `K = C`; hold to the later scheduled deadline |
| Hold days | to Gamma `closed_time` of the position (W), or to the parsed later deadline (L/X); floor `max(d, 1)` |

### 2.2 Clocks

As CB1 §2.2. History price points usable from stamp + 600 s and at most 2h old. Snapshot features come from the origin
capture; execution prices come from the **next** complete capture with a gap in [1.5, 3] h (as CB1-D), never the origin
one. **History (W) mirrors this latency:** the favourite is chosen from prices usable at t, and execution uses the
favourite's as-of price usable at `t + 2h` (no usable point → no trade, net 0, kept in the denominator, counted).
Trade conditions follow the CB1 truncation rule (known true, otherwise unavailable, never 0; exclusions counted by
outcome with a worst-case bound). Anchors are scheduled facts (`end_at`, parsed deadlines), never `closed_time`.

### 2.3 Uncertainty and decision rule

- Unweighted means are primary. One-sided p = max over the declared cluster ways of CR1 (normal z of the intercept, HB1
  rule); CI by a 2,000-draw cluster bootstrap (seed 216).
  - W: one unit per event; clusters = **end date (UTC day)** and **city**; p = max(day-clustered, city-clustered). The W
    bootstrap CI resamples whole **end-date weeks** (weekly block bootstrap), for real data and placebos alike.
  - L1, X1: one unit per trigger; clusters = ladder (stem group) and ladder × capture day. X2: one unit per ladder
    (§CB2-L), stratified by fee category.
  - Snapshot dev windows: leave-one-day-out sign stability binding (as CB1 §2.3).
- **Small-G rule (W; declared before the census; challenger item 5).** Let G be the number of clusters in a declared
  way, counted in the half being tested.
  - G ≥ 30: CR1 with the normal reference, as above.
  - 15 ≤ G < 30: that way uses CR2 (Bell-McCaffrey) standard errors with the t(G − 1) reference. A wild-cluster
    restricted bootstrap (Webb six-point weights, 9,999 draws, seed 216) is run beside it, and the larger of the two
    p-values is used for that way.
  - G < 15 in either way: the test is **"not testable"** (p = 1, still counted).
  - The day way will have hundreds of clusters. The city way is the binding one: 49 cities in the latest capture
    (§0.1), and fewer in early SCREEN months.
- Testability otherwise: ≥ 100 units, and for L/X ≥ 30 clusters in each declared way (X2: ≥ 30 cross and ≥ 30 within
  ladders in the retained strata). Otherwise "not testable" (p = 1, still counted).
- **Stage 1** (W on SCREEN; L/X on dev): advance iff one-sided p < 0.01 in the declared direction, the §2.4 floor is met,
  `R_ann` ≥ 10% for economic tests, the break-even placebo is calibrated (§2.6) and the binding robustness holds. BY
  label (q = 0.10, `battery2.cumulative_count()`) attached as triage only.
- **Stage 2** (W HOLDOUT; L/X replication on SEALED-P): Holm at α = 0.05 one-sided over **all CB2 tests reaching Stage
  2**. The candidates are W2, W3, L1, X1 and X2, so k ≤ 5. Tests finishing early are reported against Bonferroni α/k,
  with k fixed when Stage 1 ends; the final batch Holm can only add passes. A pass is "development-replicated (L2-dev)".
- **Stage P** (W only, declared now because weather data accrue at about 100 events a day): run only for W2 and W3 if
  they passed Stage 2; its own Holm family at α = 0.05 (k ≤ 2); recorded asks with next-capture latency. This is the
  only CB2 path to a confirmation claim, and for W2 it is itself the economic check. W1 is never tested at any stage.

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| W2 | economic | net ≥ +1.0c per share and `R_ann` ≥ 10% |
| W3 | mechanism | favourite resolution excess ≥ +1.0c |
| L1, X1 | economic | net ≥ +0.50c per pair and `R_ann` ≥ 10% |
| X2 | mechanism | stratified difference in ladder-level touch-violation rate ≥ +1.0 percentage point |

W1 (reported only) has no floor and no gate.

### 2.5 Counting (M3 rule)

- Every primary test writes one `trials.jsonl` line via `provenance.append_trial` (kinds `cb2_test`, `cb2_replication`,
  `cb2_prospective`), and each run writes one `ml_explain` count line (`source: "creative_batch_2:<job>"`, `n_tests`).
- New `battery2.KIND_RULES` entries: those three EXCLUDE ("counted by the matching `creative_batch_2:*` count line");
  `cb2_descriptive` EXCLUDE (no inference); seals reuse `history_seal_declaration`. If the CB1 implementation's kind
  names differ from CB1's text (`cb1_structural*` in `cb1_structural.py`), CB2 mirrors whatever is in `KIND_RULES` at
  the freeze; a unit test runs the counter on the real `trials.jsonl`.
- Placebo lines `evidence_role: "placebo"`, count 0. Cumulative count at drafting: about 921 (916 before SB2-J4, plus
  its 5; ledger), plus automatic `flow_screen` lines on the host; the run-time value is recorded in each results file.
- The P gate, all census outputs and W1 (at every stage) are `cb2_descriptive` (no inference; W1 is not counted).

### 2.6 Placebos and robustness

- **Break-even placebo** (W2; as CB1 §2.8): `Y ~ Bern(min(a + f(a), 1))`, 200 draws, full gate; advance rate must be
  ≤ 1.5%. W3 uses `Y ~ Bern(p_fav(t + 2h))`. The gate in each draw uses the same cluster p-values and the weekly block
  bootstrap as the real data.
- **Capture-order persistence diagnostic** (L1, X1; challenger item 8). Replace the execution capture by a random other
  capture of the same pair (200 draws) and report the distribution of the resulting mean net. This is **a persistence
  diagnostic, not a null**. It shows whether the c' result is specific to the 2h follow-up or just reflects pairs that
  are always "violated". It does not calibrate the gate and cannot detect misgrouping, because a misgrouped pair's
  fake violation persists in every capture. **Misgrouping is guarded only by the grouper audit gate and the
  realised-payoff gate** (§CB2-L).
- **Within-stratum label permutation** (X2; matched to its estimator, challenger item 7): permute "cross"/"within"
  labels across ladders **within the same fee-category strata the estimator uses**, recompute the stratified estimator,
  200 draws as a placebo (advance rate ≤ 1.5%), plus the 2,000-draw permutation p used in the X2 p-value (§CB2-L).
- **Binding robustness for any advance or pass:**
  - (i) `+0.75c` on every bought leg keeps net > 0.
  - (ii) The test still meets p < α and its floor without the top 5 clusters by absolute contribution, in **each**
    declared way (W: dates and cities; L/X: ladders).
  - (iii) The unweighted estimate and the cluster-equal-weighted estimate (W: city; L/X: ladder) agree in sign. h6 is a
    uniform sample, so its design weights are constant.
  - (iv) W2 and W3: the trade-truncation worst case (§CB2-W) keeps the estimate > 0.
- Reported, not binding: sign by month and by band, `+1c` cost, worst-case outcome coding, depth-checked variants, the
  `end_at` sensitivity (drop events or pairs resolved more than 7 days after the scheduled date).

### 2.7 Pre-freeze census (q0042; counts only)

Outcome columns are dropped by guard before population code runs. It produces:
- W SCREEN population and cluster counts (days, cities, G per way for the small-G rule) by band and origin, with no
  prices beyond the eligibility band;
- frame exclusion counts (census days, h1-h5 ids, capped windows, closed=false events, rows dropped by the
  `min(T_fetch6, T_seal)` cap, truncated favourites);
- the W2 local-time class counts (§CB2-W);
- the recorded weather half-spread descriptive;
- the L/X grouper audit (§CB2-L), with pair-capture and trigger counts per ladder type and X2 stratum sizes;
- the P gate counts.
Floors are never revised from the census. **The W title regex, the city→timezone table and the L/X grouper rules are
hashed into the declaration before q0040 or q0043 read any question text.** The timezone table may be extended once, at
the census and before the freeze, for frame cities missing from it. The extension uses city names only, and the zone
is the city's standard IANA zone.

### 2.8 Compute and stop rules

- Queue worker, one job at a time, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`; never two
  multi-GB jobs at once.
- Priorities: CB2 analysis ≤ 50 (below CB1's 52 and every SB2 job); the extract backfill q0041 at 62 (it preserves data
  before possible deletion, as q0030); the h6 fetch and seal at 59 (after CB1's h5 fetch at 61 and below q0002's 60).
- 15 CPU-hour cap per family. A job failing twice for the same non-transient reason stops and is recorded.
- A null is "not detected at MDE x", never "absent". No re-screen of a failed CB2 test with altered bands, offsets,
  floors or populations, on any data.
- **Disk guard:** q0043 refuses to start while host `data-dumps` exceeds 10 GB (cap 12 GB), and caps itself at 0.30 GB.
  q0041 refuses while `data-dumps` exceeds 10.5 GB and caps itself at 0.25 GB.
- **Network etiquette and collector health (challenger item 11).** Every CB2 network job uses the shared `Limiter`
  (`history_backfill.py`). It yields while the live collector pass holds its lock, and it backs off on 429/5xx with
  `Retry-After` honoured, otherwise exponential from 2 s, capped at 60 s, `MAX_RETRIES` attempts.
  - **429 stop.** If more than 1% of requests in any rolling 10 minutes are 429, the job halves its rps for the rest of
    the chunk. If more than 50 429s occur in one chunk, the chunk ends (resumable, logged as transient).
  - **Collector-health stop.** Before each chunk and every 10 minutes, the job reads the newest capture directory's
    manifest (metadata only). It ends the chunk ("paused_collector_health", transient, not a failure) if:
    - the newest complete capture started more than 2h45m ago (cadence 2h); or
    - the latest pass's manifest is incomplete while no pass holds the lock.
    It resumes only on a later queue run once the collector is healthy.
- **Request estimate, re-made honestly** (q0043, 5,000 events):
  - walk: about 300-600 Gamma pages, covering closed=true and closed=false and window splits;
  - prices: one 78h `prices-history` request per bucket, mean about 11 buckets, so about 55k;
  - trades: the Data API returns up to 10,000 newest-first rows per request with no deeper pagination (offset cap). For
    2-4 distinct top-2 buckets per event, at 1 request plus at most 1 retry-page, that is about 15-30k.
  - **Total about 70-86k requests**: about 5-6 h of pure request time at 4 rps, and 6-9 h of wall time with yields and
    back-off.

---

## 3. Jobs

### CB2-W: Weather favourites (CH27)

**Question.** In multi-bucket temperature events, does the top-priced bucket resolve YES more often than its price, by
enough that buying it at the ask six hours before the scheduled end (W2; executed about 2h later) and holding to
resolution pays after costs, and is the favourite underpriced one day before (W3)? The one-day economic version (W1)
is reported only.

**Why new / overlap.** C1 (descriptive) reported a weather calibration slope of 1.52 [1.14, 2.24] at 1d on h2/h3 rows;
it is the seed and is excluded (h1/h2/h3 events dropped). T5-DEV used price-only resolution features without a
category model. CB1-A/E touch weather markets in different populations (§1.3). The forecast-model version (NWS or
archived model forecasts) is a different, later hypothesis that needs a collector.

**Population (frozen).**
- Event title matches `TEMP_RE = r"^(Highest|Lowest) temperature in (.+?) on (.+?)\?$"` (flags: none); city = group 2,
  normalised to a slug (lowercase, spaces to hyphens); title date = group 3. 4 to 25 member buckets; neg-risk. Events
  not matching (snow, precipitation, tornadoes) are excluded.
- **Frame (challenger items 4 and 10).** The walk covers both closed=true and **closed=false** weather events with
  `end_at` in the window (§4.1). Frame exclusions, each counted:
  - `end_at` in `T_census_ex`;
  - any member in h1/h2/h3 samples or in the h5 seal listing (§1.3);
  - a walk window that still caps at 1 day.
  Events still open at `T_fetch6`, or closed without a valid single-winner payout, stay in the frame and the sample.
  They are **censored/anomalous**: excluded from the primary mean, counted in the payout-anomaly share and coded as
  losses in the worst case. So the sample is not selected on resolution.
- `end_at` = the event's Gamma `endDate` (mostly 12:00 UTC of the measurement date; the local measurement day differs
  by city, disclosed). Origins: W1 and W3 at `t = end_at − 24h`; W2 at `t = end_at − 6h`.
- History: each bucket's as-of price `p_j(t)` (10-min series, usable from stamp + 600 s, ≤ 2h old). The event is
  excluded (counted) if more than one bucket lacks a usable point. Favourite = highest `p_j(t)`; ties to the lower
  market id. Execution uses `p_fav(t + 2h)` (§2.2).
- Stage P: origin capture c = the last complete extracted capture with start in `(t − 2h, t]`; favourite = highest
  two-sided mid at c; the event must be member-complete (`event_members`) with all members open and accepting orders.
- Eligibility of the favourite: `0.30 ≤ p_fav(t) < 0.95` (band chosen from the census price distribution, no outcomes);
  at least one trade before t (history: stored trades with the truncation rule; stage P: `volume_num > 0` and
  `last_trade_price` present).
- One unit per event and origin.

**Trade truncation is outcome-dependent (challenger item 3).** Trades are fetched newest-first, at most 10,000 per
bucket. No time-window pagination is used, because the Data API offers none past its offset cap; this design keeps
newest-first and binds the bound instead. The winning bucket trades heavily as it converges after t, so it is the more
likely to be truncated with its oldest stored trade after t. The trade condition is:
- **known true** if any stored trade is before t;
- **unavailable** if the bucket is truncated and its oldest stored trade is at or after t;
- false otherwise.
Unavailable favourites are excluded and **reported by `Y`**. In the **worst case** they are added back as losers
(`Y = 0`, net `−a − f(a)` for W2, `−p_fav(t + 2h)` for W3). This worst case is **binding** (§2.6 (iv)): W2 or W3 cannot
advance or pass unless it stays > 0.

**Pricing.** History: `a = min(p_fav(t + 2h) + h_W, 0.999)`; no usable point at `t + 2h` → no trade, net 0, kept.
Stage P: the favourite token's `best_ask` at the next capture c' (gap 1.5-3h); no ask at c' → no trade, net 0, kept in
the denominator. The **execution rate** (share of units traded) is reported for history and stage P, and stage-P
MDEs are divided by it.

| ID | Kind | Origin | Statistic | Direction |
|---|---|---|---|---|
| W1 | **reported only** (`cb2_descriptive`, not counted, no gate) | `end_at − 24h` | mean `net = Y_fav − a − f(a)` (cents/share) | none |
| **W2** | economic | `end_at − 6h` (execution about `end_at − 4h`) | mean `net = Y_fav − a − f(a)` | > 0 |
| **W3** | mechanism | `end_at − 24h` | mean `Y_fav − p_fav(t + 2h)` (history) / `Y_fav − mid_fav(c')` (stage P) | > 0 |

**W2 local-time split (challenger item 6).** At `end_at − 6h` the local daily extreme may already have been observed,
so a W2 effect could be decided-but-unresolved carry, not CH27. The city→timezone table is frozen here, keyed by
city slug, and covered by the declaration hash:
- America/New_York: atlanta, miami, nyc.
- America/Chicago: austin, chicago, dallas, houston.
- America/Denver: denver.
- America/Los_Angeles: los-angeles, san-francisco, seattle.
- America/Toronto: toronto.
- America/Mexico_City: mexico-city.
- America/Panama: panama.
- America/Sao_Paulo: sao-paulo.
- America/Argentina/Buenos_Aires: buenos-aires.
- Europe/London: london.
- Europe/Amsterdam: amsterdam.
- Europe/Paris: paris.
- Europe/Madrid: madrid.
- Europe/Rome: milan.
- Europe/Berlin: munich.
- Europe/Warsaw: warsaw.
- Europe/Helsinki: helsinki.
- Europe/Istanbul: ankara, istanbul.
- Europe/Moscow: moscow.
- Asia/Jerusalem: tel-aviv.
- Asia/Riyadh: jeddah.
- Asia/Karachi: karachi.
- Asia/Kolkata: lucknow.
- Asia/Shanghai: beijing, chengdu, chongqing, guangzhou, qingdao, shanghai, shenzhen, wuhan.
- Asia/Hong_Kong: hong-kong.
- Asia/Taipei: taipei.
- Asia/Seoul: busan, seoul.
- Asia/Tokyo: tokyo.
- Asia/Manila: manila.
- Asia/Kuala_Lumpur: kuala-lumpur.
- Asia/Singapore: singapore.
- Africa/Johannesburg: cape-town.
- Pacific/Auckland: wellington.

The table may be extended once at the census (§2.7). A unit whose city is not in the table is "tz-unknown" and counted.

The local time is taken at the **execution** time (`t + 2h`) on the local measurement date (the title date). Each W2
unit is classed by that local time:
- **Highest:** *pre-extreme* before 12:00; *during* 12:00-16:00; *post-extreme* from 16:00.
- **Lowest:** *pre-extreme* before 05:00; *during* 05:00-09:00; *post-extreme* from 09:00.
- A unit whose execution falls on a later local date is post-extreme.

W2 is tested on all units as declared, and its estimate is reported by class. **The verdict may credit CH27 only if the
pre-extreme subset has a positive estimate that is at least half the full-sample estimate.** Otherwise a W2 pass is
labelled "decided-but-unresolved carry (resolution lag), not CH27". It is still reported, but it is a different
mechanism and needs its own design to be claimed. W3 (execution about 22h before `end_at`) is classed and reported
the same way, for transparency only (not binding). The census reports how many −24h units are not pre-extreme.

**Declared checks.**
- **Payout anomalies:** share of events whose bucket payouts do not sum to 1 (void, 50-50, multiple winners), plus
  events still open at `T_fetch6` (history) or `T2_W_out` (stage P). Above 2% the verdict carries "payout-anomaly
  sensitive"; worst-case coding counts anomalies as losses.
- **Censoring (stage P):** events unresolved at `T2_W_out` are valued at the last extracted favourite bid and flagged;
  sensitivities at 0 and 1; above 5% censored the verdict carries "resolution-lag sensitive".
- **Descriptive comparators (`cb2_descriptive`):** W1; the second-ranked bucket's excess (spreading predicts it
  negative); highest vs lowest temperature events; by band 0.30-0.45 / 0.45-0.60 / 0.60-0.95; capacity (stage P sweep
  depth); the execution rate.
- **Truncation worst case:** as above, binding for W2 and W3.

**Family, counting, MDE (recomputed for the time-ordered split).**
- Stage 1: 2 `cb2_test` lines (W2, W3) plus the count line `creative_batch_2:W` (`n_tests: 2`). Break-even placebo lines
  for W2, and `Bern(p_fav(t + 2h))` placebo lines for W3. W1 is one `cb2_descriptive` line.
- Sample:
  - q0043 samples 5,000 frame events.
  - The 2-day embargo drops about 40-50 of them. That leaves SCREEN ≈ 2,950 and HOLDOUT ≈ 2,000 events (≤ 40% by
    rule).
  - The title, band, trade and `t + 2h` filters keep about 0.97 × 0.80 × 0.90 × 0.98 ≈ 0.68 of events. That gives about
    **2,000 SCREEN units** and **1,350 HOLDOUT units** per origin.
  - Per-event SD ≈ 0.48 (p ≈ 0.55), and the date design effect is assumed to be 1.3. That gives SE ≈ 1.07c × √1.3 ≈
    1.22c (SCREEN) and SE ≈ 1.31c × √1.3 ≈ 1.49c (HOLDOUT).
  - **Stage 1 MDE** (z 2.33 + 0.84) ≈ **3.9c**.
  - **HOLDOUT MDE** ≈ **3.7c** (k = 1, z 1.645 + 0.84) to **4.7c** (k = 5, Holm first step α = 0.01).
  - The HOLDOUT has about 50 end dates in one season, so its real design effect may exceed 1.3. If the city way falls
    under the small-G rule, the t(G − 1) reference raises these MDEs by about 5-10%.
  - **Stage P** (8 weeks, about 100 events a day, about 5,600 events and about 3,900 units): SE ≈ 0.77c × √1.5 ≈
    0.94c. MDE ≈ **2.3c** (k = 1) to **2.6c** (k = 2), divided by the execution rate.
- Envelope: the C1 slope implies a gross favourite excess of about +2.6c at p = 0.55 and +9c at p = 0.75, against a
  one-leg cost of about 3c (2c half-spread, 1.2c fee at 0.5). Most −24h favourites sit at 0.40-0.60, so a −24h economic
  net mean (W1, reported only) would be about 0 to +1.5c, below every MDE. W3 (gross, about +3-4c) is the realistic
  detection target. W2 has higher-priced favourites and a larger envelope, but part of that may be the resolution-lag
  carry the local-time rule separates. A null is "not detected at MDE ≈ 3.9c (screen) / 2.5c (stage P)".

**Verdict map.**
- W2 passes Stage 2 and stage P with the binding robustness, and the pre-extreme rule holds → "prospectively supported
  weather-favourite carry". It already includes the economic check at recorded asks with latency, depth reported. If
  the pre-extreme rule fails → "resolution-lag carry, not CH27".
- W3 replicated, W2 not → "favourite underpricing exists, not tradable after one-leg costs at MDE" (a forecasting fact;
  the maker or forecast-model routes would need their own designs).
- No Stage-1 advance → HOLDOUT unopened, stage P not analysed, CH27 price-only closed at MDE.

**Compute.** Screen: one pass over about 2,950 events' prices (about 15-20 min, 1.2 GB), plus 2,000 bootstrap draws,
2 × 200 placebo draws, and wild-cluster draws if the small-G rule applies (about 30-40 min). HOLDOUT about the same.
Stage P: one Gamma `/events?id=` outcome request per eligible event at `T2_W_out`. That is about 3,900 requests (about
16 min at 4 rps, plus retries), which replaces the draft's 3,200; that figure was inconsistent with its own estimate of
about 3,900 units. Analysis takes about 15 min.

**Stop rule.** No W advance → no HOLDOUT read and no stage-P analysis.

### CB2-L: Ladder dominance within events (CH12) and across events (CH13)

**Question (economic).** When two rungs of a monotone date ladder violate the logical order at the touch, is the
two-leg position still buyable at a structural profit about 2h later, within events (L1) and across events (X1)?

**Question (mechanism, CH13).** Are cross-event violations more frequent than within-event ones (X2), because no page
shows the separate events together?

**Overlap.** XM8 (violation → drift; untestable on h2), IF-H2's `v1 ≤ v2 + 0.01` exclusion rule (mids, never traded),
CB1-D (neg-risk sums; ladders are not neg-risk). No AREPO test has used touch-level ladder inequalities.

**Ladder list (q0040; frozen rules `ladder-grouper-v2`, hashed before any text is read).**
- Universe: non-sports, non-weather, non-neg-risk markets open in the 12:31Z capture of each day from `T2_dev_start`
  plus the latest capture; question text and description fetched from Gamma `/markets?id=` (metadata only).
- **Version rule (challenger item 9).**
  - **v1** (the first q0040 run) applies **retrospectively** to every dev capture from `T2_dev_start`. The dev backfill
    (`ladder_candidates/`, q0041) is filtered by v1 at analysis time.
  - Disclosed: v1's question text and descriptions are read at q0040 time, **after** the dev captures they classify.
    Edits to the text since those captures (as CB1 item 12), and markets that closed before q0040, are possible. Dev
    grouping therefore uses later text, which is a look-ahead in the frame but not in prices or outcomes.
  - **v2 and later** (weekly additive refreshes, each hashed) apply **prospectively only**: a rung added by version
    v ≥ 2 enters the extract from the first capture after that version's `listed_utc`.
  - The replication window (≥ `T2_rep_start`) uses only versions whose `listed_utc` precedes each capture.
- Deadline phrase parsed by the `if_h2` parser. Direction: **INC** for "by D" / "before D" (probability rises with D);
  **DEC** for "through D" / "until D" / "continue(s) through D" (falls with D). "on D", "in <month>" and anything else:
  excluded. Stem = question with the date phrase removed, lowercased, whitespace and punctuation normalised.
- **Within-event ladder (L):** ≥ 2 rungs in one event with the same stem, same direction and distinct deadlines.
- **Cross-event ladder (X):** the same stem and direction across ≥ 2 events, one rung per event, and normalised
  descriptions equal after masking dates (resolution-source guard).
- Pairs: adjacent deadlines `D1 < D2` within a ladder.
- **Grouper audit gate (census, before any statistic):** a random 50 pairs per type plus every pair with an apparent
  gap ≥ 20c are printed with question text and labelled (genuine monotone pair or not). If more than 5% are not
  genuine, the rules are revised and re-hashed before the freeze (no P&L has been computed at that point). The audit is
  recorded in the census file.

**Definitions at capture c** (both rungs open, accepting orders, two-sided, `volume_num > 0`):
- INC violation: `bid(D1) > ask(D2)`. Position: YES on D2 at `ask(D2)` and NO on D1 at `1 − bid(D1)`. Payoff: 1 if the
  event happens by D1 or never by D2, 2 if it happens between them, so ≥ 1.
- DEC violation: `bid(D2) > ask(D1)`. Position: YES on D1 and NO on D2. Payoff ≥ 1 by the mirror argument.
- Trigger: `1 − C(c) ≥ 0.005`. Execution at the next complete capture c' (gap 1.5-3h) at `C(c')` if both rungs are still
  eligible (otherwise no trade, net 0, kept). `net = 1 − C(c')`.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **L1** | economic | trigger, within-event ladders | mean `net` (cents per pair), executed at c' | > 0 |
| **X1** | economic | trigger, cross-event ladders | same | > 0 |
| **X2** | mechanism | ladder (stratified by fee category) | stratified difference of ladder-level touch-violation rates, cross minus within | > 0 |

**X2 estimator (challenger item 7).** The draft compared pair-capture violation rates that included fees, against a
placebo that permuted labels within fee category. That mismatched the estimator: composition and the fee channel
could drive the difference. The replacement:
- **Indicator (fee-free):** a touch violation at capture c, `bid(D1) − ask(D2) > 0` (INC) or `bid(D2) − ask(D1) > 0`
  (DEC). It uses eligible pair-captures as above, with no fee term, so fee schedules cannot create a difference.
- **Unit:** a ladder ℓ. `v_ℓ` = the share of ℓ's eligible pair-captures with a touch violation. Each ladder counts once
  however many pairs or captures it has.
- **Strata:** s = the sidecar `fee_category` of the ladder's rungs (a ladder with mixed categories takes its modal
  one). A stratum is retained only if it has ≥ 1 cross and ≥ 1 within ladder; dropped ladders are counted.
- **Estimator:** `Δ = Σ_s w_s (mean_{cross,s} v − mean_{within,s} v)`, with `w_s` = the stratum's share of retained
  cross ladders.
- **p-value:** the larger of (a) the normal z with the stratified variance `Σ_s w_s² (var_{c,s}/n_{c,s} +
  var_{w,s}/n_{w,s})` and (b) the 2,000-draw within-stratum label permutation of the same `Δ` (seed 216). The placebo
  (§2.6) permutes in the same strata.
- **Residual:** within a category, cross and within ladders may still differ in price level, horizon and rung count.
  X2 is a mechanism comparison of incidence only, never read as tradability.

**Binding gates on L1/X1 (in addition to §2.3).**
- **Realised payoff:** on triggered pairs whose payoff is determined by `T2_L_out` (D1 rung resolved and, if it
  resolved YES for INC / NO for DEC, the D2 rung also resolved), the share with realised payoff < 1 must be ≤ 2%
  (inconsistent resolution is CH13's named risk). Fewer than 30 determined pairs → "inconclusive (payoff unverified)".
- **Depth:** recomputed on triggers whose two legs were swept with size ≥ 5 at the next pass; must agree in sign;
  fewer than 30 ladder clusters → "inconclusive (depth unverified)".
- `R_ann` uses the parsed D2. Long holds make the 10% `R_ann` floor hard to meet for small gaps; that is the economic
  answer, not a defect.

**Family, counting, MDE.**
- Dev: 3 `cb2_test` lines plus the count line `creative_batch_2:L`. Rep: advanced tests only (`cb2_replication`).
- Incidence is unknown (the proxy was contaminated, §0.1). If triggers come from fewer than 30 ladders, L1/X1 are "not
  testable", which is itself the answer: the state is too rare to trade.
- If testable: per-trigger SD ≈ 3c (CB1-D analogue), so with 30-60 ladder clusters SE ≈ 0.4-0.6c and the dev MDE ≈
  1.3-1.9c. X2: per-ladder violation-rate SD ≈ 0.1 with about 600 within- and an unknown number of cross-event
  ladders; at 100 cross ladders, with stratification costing about 10%, SE ≈ 1.2 pp, dev MDE ≈ 3.8 pp, rep ≈ 3.0-3.8
  pp (k = 1-5).
- **Misgrouping.** The persistence diagnostic (§2.6) is not a null and cannot detect misgrouping. The only guards are
  the grouper audit gate and the realised-payoff gate.

**Verdict map.**
- L1 or X1 replicated with both gates → "executable ladder dominance persists 2h (L2-dev)"; a stage-P registration at
  sweep-checked depth would follow, reporting capacity.
- X2 only → "cross-event violations more common, not capturable at 2h latency" (maker route needs continuous books).
- Census: too rare → CH12/CH13 closed "not testable: n triggers from m ladders"; no further work.

**Compute.** q0040 about 1,500 Gamma requests (about 15 min at 2 rps) plus 13 capture reads (about 15 min). q0041
text-free backfill about 150 captures × 1 min ≈ 2.5 CPU-h at nice 19, 1 GB, about 1 MB per capture (≤ 27,000
non-sports rows per capture in the 2026-10-15 22:31Z capture), so about 0.15-0.2 GB on disk. Dev analysis 10 min; rep 30
min.

**Stop rule.** No L/X dev advance → the rep spec is not committed. Audit gate failure after one revision → CB2-L stops
and is recorded.

### CB2-P: Placeholder-member gate (CH10)

**Gate (counts only, on CB1 extract `negrisk/` captures in `[T2_dev_start, T2_dev_end)`).**
- Events eligible as CB1-D (non-augmented, no "Other" member, member-complete, all unresolved members open), 2-25
  members. Never-traded member: `volume_num` missing or 0 **and** `last_trade_price` empty. Setup: exactly one
  never-traded member u; all others traded and two-sided.
- `fair = clip(1 − Σ_traded mid, 0, 1)`; `gap = max(fair − ask_u, bid_u − fair)` over the sides that exist.
- **Gate:** at least 2 unique (event, u) setups per day with `gap ≥ 5c`, averaged over the window, from at least 30
  distinct events. Fail → CH10 closed "not testable: setups too rare (x per day)"; 0 tests counted.
- **If it passes (coordinator decision after challenger round 1):** CB2 contains **no P1 test, no P1 code and no
  q0050**. A pass only records that the state is common enough to study. A P1 economic test would then need its own
  registered design, challenger review and freeze, written after the gate result and before any rep-window capture it
  uses. The gate itself reads no outcome and counts 0 tests.

---

## 4. Code needed

### 4.1 Modules

- `backend/astrolabe/research_lab/cb2_weather.py`
  - `walk_weather_events(start, end, limiter)` (challenger item 4):
    - Walks Gamma `/events?tag_slug=weather` with **both `closed=true` and `closed=false`**, by 7-day end-date windows,
      split down to 1 day while capped. A window still capped at 1 day is excluded and counted.
    - Applies the `TEMP_RE` filter and the frame exclusions: `T_census_ex`, h1/h2/h3 market ids, h5 ids from the file
      table of the committed seal copy, and `end_at < min(T_fetch6 − 3d, T_seal)`.
    - Counts closed=false events, which are kept as censored.
    - Draws the seeded sample (`arepo-h6-weather`, 5,000).
    - Writes outcome fields to a separate guarded file.
    - Every exclusion has a count in the manifest.
  - `split_h6(events)`: the §1.3 time-ordered rule (group key, `D_split`, 2-day embargo); it uses `end_at`, city and title
    date only.
  - `fetch_event_prices(event, ...)`: CLOB prices-history per bucket token, fidelity 10, `[end_at − 72h, end_at + 6h]`;
    trades (≤ 10,000, newest first, truncation flags, oldest stored timestamp) for the buckets ranked 1-2 at either
    origin. **Every price and trade row at or after `min(T_fetch6, T_seal)` is dropped and counted** (CB1 freeze-fix 2).
    The job refuses new chunks at or after `T_seal`.
  - `collector_healthy()` and the 429 policy of §2.8 (wrapping the shared `Limiter`).
  - `favourite_origin(event, t)`, `exec_price(event, fav, t + 2h)`, `local_class(city, title_date, ts)` (frozen
    timezone table), `weather_unit(...)`, `w_tests(...)` (W2, W3; W1 descriptive), `truncation_worst_case(...)`,
    `small_g_pvalue(...)` (CR2 + t(G − 1) and wild-cluster), `stagep_units(extract, event_text, ...)`,
    `fetch_outcomes(...)` (reuse `cb1_structural.fetch_outcomes`).
- `backend/astrolabe/research_lab/cb2_structural.py`
  - `fetch_question_text(ids, limiter)`, `parse_direction(question)`, `ladder_grouper_v2(...)`, `ladder_list(...)` with
    versioned sha256, `audit_sample(...)`.
  - `pair_states(extract)`, `pair_cost`, `next_capture_pairs` (reuse CB1's gap filter), `realised_pair_payoff`,
    `lx_tests`, `x2_stratified(...)` (ladder-level fee-free rates, stratified estimator and matched within-stratum
    permutation), `persistence_diagnostic(...)`, `placeholder_gate` (counts only). No P1 code.
- Shared statistics are **imported from CB1 code, not copied**: cost model, `trade_condition`, cluster test (generalised
  to arbitrary cluster ways), bootstrap, break-even placebo, capacity, `log_trials`, census guard.
- `HYPOTHESES_CB2` and `declaration_sha256()` covering every population, regex, grouper rule, band, floor, gate, date,
  the split rule, the small-G rule, the local-time classes and the city→timezone table in this file.

### 4.2 Runner

`backend/scripts/run_cb2.py {ladder-list,census,weather-fetch,seal,verify-seal,screen,replicate,snapshots,stagep}
--family W|L|P`. Refuses run ids `h3_power`, `h4_seal`, `h5_cb1`, `h5_cb1_ladders`. Declaration-hash guard (committed
`model_specs/cb2_v1.json` must equal the code's hash) on `screen`, `replicate`, `snapshots` and `stagep`; `replicate
--family W` refuses before the freeze and logs every HOLDOUT read; `snapshots --window rep` refuses before
`T2_rep_end`; `stagep` refuses before `T2_W_out`. Results files are never overwritten and are **never written inside
a sealed run directory** (W results go to `research_lab/creative_batch2/W_screen/` and `W_holdout/`). `weather-fetch`
refuses until `docs/research_lab/seals/h5_cb1_SEAL.json` is committed, and at or after `T_seal`. `seal` computes and
records `D_split`. Generalise `h5_seal` (run-id allowlist plus `h6_weather`) and `scripts/cb1_h5.py seal` rather than
duplicating them.

### 4.3 Extractor additions (`creative_batch1.py`, version `cb1-extract-v2`; no change to `arepo_pass.sh`)

- `cb2_extract/ladder_candidates/<capture_id>.csv.gz` (**text-free**, optional item adopted). It covers every
  non-sports, non-weather, non-neg-risk market in captures with start < `T2_dev_end`: the q0041 backfill, plus the
  live pass until `T2_dev_end`. It needs no ladder list and no grouper hash, so the backfill can run before q0040. The
  columns are those of `ladders/` below. About 1 MB per capture. Dev analysis filters it by ladder-list v1.
- `cb2_extract/ladders/<capture_id>.csv.gz` (own root and manifest), written only when `cb2_extract/ladder_list.json`
  exists: for every listed rung,
  `capture_id, capture_start_utc, received_utc, market_id, event_id, best_bid, best_ask, last_trade_price, closed,
  active, accepting_orders, end_date, volume_num, fee_schedule, fee_category` plus first-sweep `best_bid, best_ask,
  bid_size_1, ask_size_1` (blank if not swept). About 2,000-3,000 rows, about 0.1 MB per capture.
- `event_text.csv.gz`: event `title`, `slug` and member `groupItemTitle` for each neg-risk event, taken from the same
  `/events/{id}` response the extractor already fetches for `event_members` (no extra requests). Needed for `TEMP_RE`
  in stage P; text is read at first extraction (about listing time), disclosed. Written by the live extractor only (no
  backfill: stage P uses captures ≥ `T2_rep_start`).
- Optional, data only (CH16 preservation; coordinator decides): `rewards/<date>.csv.gz` from the first capture after
  12:00Z each day: reward-enabled markets' `clob_rewards` (daily rate, start and end), `rewards_max_spread`,
  `rewards_min_size`, `competitive`, touch and sweep depth fields; about 1 MB a day.
- CB1 tables must stay byte-identical (test). The 10-minute and 500 MB pass limits still hold; the ladder filter adds
  seconds.

### 4.4 Tests (`backend/tests/unit/test_cb2_weather.py`, `test_cb2_structural.py`)

- `TEMP_RE` fixtures (match and city capture; snow and precipitation titles rejected); the regex string is in the
  declaration hash.
- Favourite selection uses only points usable at t: a planted post-t spike does not change it; the 600 s lag; the tie
  rule; more than one missing bucket excludes the event.
- The SCREEN/HOLDOUT split:
  - is deterministic and disjoint;
  - puts the Highest and Lowest events of one city-day in the same half;
  - has a `D_split` that leaves ≤ 40% in the HOLDOUT;
  - drops the embargo days from both halves;
  - is computed without opening the outcome file.
  The screen refuses HOLDOUT and embargo ids, and HOLDOUT reads are logged.
- q0045/q0047 outputs land outside `history/h6_weather/`, and `verify_seal` passes after a screen and a holdout run.
- The census guard drops outcome columns; the h6 fetch writes outcomes to a separate file.
- Frame rules:
  - a `T_census_ex` event is excluded;
  - an h5 market id taken from a fixture seal-copy file table excludes its event;
  - closed=false events are walked and kept as censored;
  - a window capped at 1 day is excluded;
  - each rule increments its manifest count.
- Price and trade rows at or after `min(T_fetch6, T_seal)` are dropped and counted; `weather-fetch` refuses at or after
  `T_seal`.
- Truncation:
  - a truncated favourite whose oldest stored trade is after t is unavailable (not false), reported by `Y`;
  - the worst case adds it as a loser;
  - a fixture where the worst case flips the sign blocks the advance.
- Execution at `t + 2h`: a planted price after `t + 2h` does not change `a`; no usable point gives net 0, kept.
- `local_class`: fixtures for a US, a European and an East-Asian city at −6h, for Highest and Lowest; the pre-extreme
  crediting rule.
- Small-G: G = 20 uses CR2 with t(19) and the wild-cluster p; G = 14 gives "not testable".
- 429 policy and collector-health stop: a stale newest capture (> 2h45m) or an incomplete manifest ends the chunk as
  transient.
- `h_W` floor of 2.0c and the `+0.75c` sensitivity; weather fee 0.05 in history.
- `parse_direction`: "by" → INC, "through/until/continues through" → DEC, "on D" and "in October" → excluded; the
  ceasefire and "on date" pairs from §0.1 as fixtures (they must not form violations).
- INC and DEC pair payoffs are ≥ 1 in all three outcome states; fees summed per leg.
- Next-capture execution with the gap filter; a 10h-outage pair is dropped; a rung closed at c' gives no trade.
- Cross-event grouping requires equal masked descriptions.
- The ladder-list version rule: v1 applies to every dev capture from `T2_dev_start`; a rung added by v ≥ 2 is absent
  from captures before that version's `listed_utc`.
- X2: the indicator has no fee term; the estimator uses one value per ladder; the permutation stays within the
  estimator's strata; strata without both types are dropped and counted.
- `ladder_candidates/` needs no ladder list and contains no text column.
- Placeholder definition: blank `volume_num` with an empty last trade is "never traded"; a blank `volume_num` with a
  last trade is not. The gate reads no outcome column.
- The runner refuses `h5_cb1`, `h5_cb1_ladders`, `h3_power`, `h4_seal`; `KIND_RULES` contains the CB2 kinds and the
  counter runs on the real `trials.jsonl`.

---

## 5. Draft queue specs

Paths follow `queue/README.md` (`argv[0]` under `backend/scripts/`, `cwd` `backend`). No spec is committed before its
code and tests exist; test jobs also need the reviewed CB2 freeze commit.

```json
{"id": "q0040_cb2_ladder_list", "title": "CB2-L: direction-aware ladder list (within + cross-event) from daily captures since 2026-10-11T12:00Z (metadata only)",
 "family": "creative_batch_2", "priority": 62, "expected_value": "fixes the L/X rung universe before the backfill; grouper audit sample",
 "data": ["research_lab/snapshots (one capture per day, ids and fee fields)", "Gamma /markets metadata"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api"},
 "depends_on": [], "argv": ["scripts/run_cb2.py", "ladder-list", "--from", "2026-10-11T12:00Z", "--rps", "2", "--max-requests", "3000"],
 "timeout_s": 3600, "max_retries": 2, "outputs": ["data-dumps/research_lab/cb2_extract/ladder_list.json (+ .sha256)", "cb2_extract/audit_sample.json"],
 "next_action": "q0042 after T2_dev_end", "notes": "refuses unless the grouper-rule hash is committed; no prices or outcomes read; v1 applies retrospectively to dev captures (§CB2-L)"}
```
```json
{"id": "q0041_cb2_extract_backfill", "title": "CB2: one-off text-free ladder_candidates/ extract from complete captures since 2026-10-11T12:00Z",
 "family": "creative_batch_2", "priority": 62, "expected_value": "preserves L/X dev inputs before raw captures become deletable, without waiting for the ladder list",
 "data": ["research_lab/snapshots + rows_ext + book_sweeps present on host (else release copies)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": [], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-11T12:00Z", "--tables", "ladder_candidates", "--budget-min", "150", "--disk-cap-gb", "0.25"],
 "timeout_s": 10800, "max_retries": 2, "repeat": {"max_runs": 3, "until_log_regex": "backfill_complete"},
 "outputs": ["cb2_extract/ladder_candidates/", "manifest.json"], "next_action": "pass step continues (extractor v2)", "notes": "idempotent by capture_id; CB1 tables untouched; no text read; missing captures counted; refuses while data-dumps > 10.5 GB"}
```
```json
{"id": "q0042_cb2_census", "title": "CB2: pre-freeze census (W SCREEN counts, G per way, frame exclusions, local-time classes, weather half-spreads, L/X audit + trigger counts + X2 strata, P gate counts; no outcomes)",
 "family": "creative_batch_2", "priority": 50, "expected_value": "testability, MDEs and the CH10 gate before the freeze",
 "data": ["h6_weather SCREEN (no outcome file)", "cb1_extract negrisk/event_members (< T2_dev_end)", "cb2_extract ladder_candidates/ + ladder_list v1"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0040_cb2_ladder_list", "q0041_cb2_extract_backfill", "q0044_h6_weather_seal"], "argv": ["scripts/run_cb2.py", "census", "--family", "W,L,P"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch2/census.json"],
 "next_action": "Claude session: insert counts, audit result and P gate into CREATIVE_BATCH_2.md; challenger; freeze", "notes": "commit after T2_dev_end; outcome guard; floors not revised from census"}
```
```json
{"id": "q0043_h6_weather_fetch", "title": "CB2-F: h6_weather backfill (5,000 temperature events, all buckets, prices + top-2 trades)",
 "family": "history_data", "priority": 59, "expected_value": "fresh whole-event weather history for the W screen and holdout",
 "data": ["public Gamma events/CLOB/Data API", "h1/h2/h3 sample market ids (exclusion only)", "docs/research_lab/seals/h5_cb1_SEAL.json file table (h5 market ids only)"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api, clob, data-api"},
 "depends_on": [], "argv": ["scripts/run_cb2.py", "weather-fetch", "--run-id", "h6_weather", "--seed", "arepo-h6-weather", "--n-events", "5000", "--end-from", "2025-06-01", "--end-before", "2026-10-22T00:00Z", "--exclude-end", "2026-10-08T00:00Z,2026-10-12T00:00Z", "--exclude-runs", "h1_first,h2_main,h3_power", "--exclude-seal-ids", "../docs/research_lab/seals/h5_cb1_SEAL.json", "--walk-closed", "true,false", "--cap-at", "2026-10-22T00:00Z", "--rps", "4", "--disk-cap-gb", "0.30", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 3, "repeat": {"max_runs": 6, "until_log_regex": "weather_fetch_complete"},
 "outputs": ["data-dumps/research_lab/history/h6_weather/{events.jsonl.gz,prices/,trades/,outcomes_guarded.csv.gz,manifest.json}"],
 "next_action": "q0044", "notes": "about 70-86k requests (§2.8); commit only after the h5 seal copy is committed; refuses while data-dumps > 10 GB and at or after T_seal; rows capped at min(T_fetch6, T_seal) with dropped counts; 429 back-off and collector-health pause (transient); end_at also < T_fetch6 - 3d; resumable"}
```
```json
{"id": "q0044_h6_weather_seal", "title": "CB2-F: time-ordered split (D_split rule, 2-day embargo) + seal h6_weather (SCREEN/HOLDOUT listing hashes, D_split, trial line, access log)",
 "family": "history_data", "priority": 59, "expected_value": "fixes h6 before any W result exists",
 "data": ["history/h6_weather"], "resources": {"mem_mb": 300, "cpu": 1}, "depends_on": ["q0043_h6_weather_fetch"],
 "argv": ["scripts/run_cb2.py", "seal", "--run-id", "h6_weather"], "timeout_s": 1800, "max_retries": 1,
 "outputs": ["history/h6_weather/{SEAL.json,ACCESS_LOG.jsonl}", "trials.jsonl (1 history_seal_declaration)"],
 "next_action": "Claude session: commit docs/research_lab/seals/h6_weather_SEAL.json (with D_split)", "notes": "split uses end_at, city and title date only; outcome file not opened"}
```
```json
{"id": "q0045_cb2_screen_W", "title": "CB2-W: declared screen on h6_weather SCREEN (W2, W3 tested; W1 reported only; Stage-1 gate; placebos)",
 "family": "creative_batch_2", "priority": 50, "expected_value": "which weather tests advance to the holdout",
 "data": ["history/h6_weather SCREEN (sealed)", "model_specs/cb2_v1.json"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0042_cb2_census"], "argv": ["scripts/run_cb2.py", "screen", "--run-id", "h6_weather", "--family", "W", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch2/W_screen/results.json", "trials.jsonl (2 cb2_test + count + placebo + 1 cb2_descriptive)"],
 "next_action": "q0047 for advanced tests", "notes": "commit only after the CB2 freeze; verify-seal; declaration-hash guard"}
```
```json
{"id": "q0046_cb2_snap_dev_LX", "title": "CB2-L: ladder dominance dev screen on extracted captures before T2_dev_end (L1, X1, X2)",
 "family": "creative_batch_2", "priority": 50, "expected_value": "2h-latency ladder pair carry; cross vs within incidence",
 "data": ["cb2_extract/ladder_candidates (frozen dev capture list + sha256), filtered by ladder_list v1", "ladder_list versions"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": ["q0042_cb2_census"], "argv": ["scripts/run_cb2.py", "snapshots", "--family", "L", "--window", "dev", "--extract-root", "../data-dumps/research_lab/cb2_extract", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch2/L_dev/results.json", "trials.jsonl"],
 "next_action": "if advanced: commit q0048 after T2_rep_end", "notes": "LODO binding; declaration-hash guard; X2 stratified ladder-level estimator with matched permutation; capture-order persistence diagnostic reported (not a null); exits 0 'not testable' with counts"}
```
```json
{"id": "q0047_cb2_holdout_W", "title": "CB2-W: frozen replication of advanced W tests on h6_weather HOLDOUT",
 "family": "creative_batch_2", "priority": 50, "expected_value": "development replication (Holm over the CB2 Stage-2 set)",
 "data": ["history/h6_weather HOLDOUT (sealed)", "creative_batch2/W_screen/results.json"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0045_cb2_screen_W"], "argv": ["scripts/run_cb2.py", "replicate", "--run-id", "h6_weather", "--family", "W", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch2/W_holdout/results.json", "trials.jsonl"],
 "next_action": "Bonferroni interim; batch Holm later", "notes": "exits 0 'nothing advanced'; one HOLDOUT read, logged"}
```
```json
{"id": "q0048_cb2_snap_rep_LX", "title": "CB2-L: frozen replication on extracted captures in [T2_rep_start, T2_rep_end) + realised-payoff gate",
 "family": "creative_batch_2", "priority": 50, "expected_value": "L/X replication on prospective captures",
 "data": ["cb2_extract/ladders (frozen rep list)", "Gamma outcomes of triggered rungs"], "resources": {"mem_mb": 1000, "cpu": 1, "network": "gamma-api"},
 "depends_on": ["q0046_cb2_snap_dev_LX"], "argv": ["scripts/run_cb2.py", "snapshots", "--family", "L", "--window", "rep", "--extract-root", "../data-dumps/research_lab/cb2_extract", "--rps", "4", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch2/L_rep/results.json", "trials.jsonl"],
 "next_action": "batch Holm; payoff gate final at T2_L_out", "notes": "commit after T2_rep_end with the rep capture list + sha256; runner refuses earlier"}
```
```json
{"id": "q0049_cb2_stageP_W", "title": "CB2-W: stage P on weather events in [T2_rep_start, T2_W_end) at recorded next-capture asks",
 "family": "creative_batch_2", "priority": 50, "expected_value": "prospective economic check of replicated W tests",
 "data": ["cb1_extract negrisk/event_members/event_text (captures >= T2_rep_start)", "Gamma outcomes"], "resources": {"mem_mb": 1000, "cpu": 1, "network": "gamma-api"},
 "depends_on": ["q0047_cb2_holdout_W"], "argv": ["scripts/run_cb2.py", "stagep", "--family", "W", "--extract-root", "../data-dumps/research_lab/cb1_extract", "--rps", "4", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 2, "outputs": ["research_lab/creative_batch2/W_stageP/results.json", "trials.jsonl (cb2_prospective + count)"],
 "next_action": "verdict per CB2-W map; ledger", "notes": "commit after T2_W_out; exits 0 'nothing replicated' if Stage 2 empty; about 3,900 outcome requests (one per eligible event); reports execution rate and W2 local-time classes; 429 back-off and collector-health pause"}
```

There is no q0050. P1 was dropped from CB2 (challenger round 1, coordinator decision). Any P1 needs its own design.

## 6. Test budget and compute

| Job | Tests counted | Kind(s) |
|---|---|---|
| W screen (W2, W3) | 2 | `cb2_test` + count line (`n_tests: 2`) |
| L/X dev (L1, X1, X2) | 3 | `cb2_test` + count line |
| W1 (all stages), P gate, census, seal, descriptives | 0 | `cb2_descriptive`, `history_seal_declaration` |
| Stage 2 (W holdout ≤ 2, L/X rep ≤ 3) | ≤ 5 | `cb2_replication` + count lines |
| W stage P (W2, W3) | ≤ 2 | `cb2_prospective` + count line |
| **Total** | **5 fixed + up to 7 conditional (5-12)** | |

Families:
- **Stage 1:** each test is gated alone at one-sided p < 0.01, with the BY label as triage.
- **Stage 2:** one Holm family at α = 0.05 over every CB2 test reaching it (k ≤ 5).
- **Stage P:** its own Holm family at α = 0.05 (k ≤ 2).

**Host compute.**
- About 5-7 CPU-hours in total at nice 19; the q0041 backfill (2.5 h) is the largest. Peak memory 1.2 GB.
- Plus 6-9 h of network-bound wall time for q0043: about 70-86k requests at ≤ 4 rps, in 150-minute resumable chunks,
  with yields, 429 back-off and collector-health pauses; about 0.25 GB disk.
- About 6k further Gamma requests across q0040, q0048 and q0049 (q0049 alone about 3,900).
- Disk: q0041 adds about 0.15-0.2 GB (`ladder_candidates/`). The extractor additions add seconds and about 1 MB per
  pass until `T2_dev_end`, then about 0.1 MB.

## 7. Main scientific risks

1. **Power.** The −24h net envelope (about 0 to +1.5c) is below every W MDE (about 3.9c screen, 3.7-4.7c holdout,
   2.5c stage P), which is why W1 is reported only. W3 is the realistic detection; W2's larger envelope may partly be
   resolution-lag carry (local-time rule). The time-ordered HOLDOUT is out-of-time and may fail on regime change
   (§1.3). L/X may be "not testable"; P is expected to fail its gate.
2. **Ladder text rules.** Direction and stem errors create fake violations (the §0.1 proxy was entirely such errors).
   The audit gate, the excluded "on D" phrasing and the masked-description guard address this; residual misgrouping
   biases L1/X1 upward, which the realised-payoff gate would expose late (`T2_L_out`). The capture-order persistence
   diagnostic cannot detect it. v1 grouping uses text read after the dev captures (§CB2-L).
3. **Modelled weather asks.** History has no weather books. `h_W` = 2c is from one census capture; the binding `+0.75c`
   and stage P at recorded asks with latency are the defences. History now executes at `p_fav(t + 2h)`, so the
   favourite is no longer traded at the price it was selected on.
4. **`end_at` semantics.** Weather `endDate` is a template time (usually 12:00 UTC of the measurement date), so −24h
   and −6h fall at different local hours by city. For W2 this is handled by the frozen timezone table and the
   pre-extreme crediting rule; elsewhere it is disclosed, not modelled.
5. **Dependence.** Weather outcomes may correlate across cities on one date (regional weather systems), hence the
   max-of-two-ways rule, the weekly block bootstrap and the small-G rule for the city way. The assumed design effects
   (1.3, 1.5) are unverified until the census. The SCREEN/HOLDOUT boundary is a regime boundary (§1.3).
6. **Survivorship and frame.** The Gamma weather tag walk misses untagged events (disclosed). Events with an unparsable
   title are excluded by rule. Still-open events are walked and censored, not dropped. Trade truncation is
   outcome-dependent, and its worst case is binding. Ladder listing survivorship is limited to the daily-capture
   universe (L/X use only markets seen open live).
7. **Overlap with CB1.** Shared captures (CB1-D, B3, A descriptive) and possible shared h5 weather markets are
   disclosed in §1.3; the statistics and populations are disjoint, and no CB2 code path opens h5.
8. **Calendar and disk.** The dev window needs raw captures from 2026-10-11; if retention deletes them before q0041,
   release copies are used (download cost). Host `data-dumps` was 7.3 GB at 2026-10-15T23:40Z and grows about 1 GB a
   day until snapshot retention is active; q0041 and q0043 wait under their disk guards.
9. **Drafting-census exposure.** Events ending 8-11 Oct 2026 are excluded. A residual exposure on a few unrecorded days
   in earlier months is disclosed (§0.1).

## 8. Next actions

1. Challenger round 1 is done and its response is applied (sections below). This is the single response round, as in
   CB1. The next review is the freeze check of code against this design.
2. Delegate to `implementer`: `cb2_weather.py`, `cb2_structural.py`, `run_cb2.py`, extractor v2 tables
   (`ladder_candidates`, `ladders`, `event_text`), seal generalisation with `D_split`, `KIND_RULES`, tests (§4). Commit
   the `TEMP_RE`, timezone-table and grouper-rule hashes before q0040/q0043 read text.
3. Commit and run q0041 at once: it is text-free, urgent before raw-capture deletion, and needs no ladder list. Then
   q0040. Then q0043 and q0044 once disk allows and the h5 seal copy is committed.
4. After `T2_dev_end`: q0042 census, insert counts and the audit result here, then the CB2 freeze (`model_specs/
   cb2_v1.json`); `T2_rep_start` follows from it.
5. Then q0045 and q0046; q0047 for advanced W tests; q0048 after `T2_rep_end`; q0049 after `T2_W_out`. There is no P1
   in CB2.

**Open questions for the challenger (draft round; resolved by round 1).**
1. HOLDOUT worth its cost? Kept, but replaced by a time-ordered split (item 2); stage P retained.
2. Stage-P "no trade = net 0 kept"? Kept, the execution rate is now reported, and history mirrors the 2h latency.
3. X2 per pair-capture or per ladder? Per ladder, stratified (item 7).

**User decisions.** None required to proceed. Two dependencies are already open with the user: snapshot retention
activation (about 17-18 October) governs both the dev-window raw captures and the disk room for q0043. Sports remain
outside CB2; the category scope stays a parameter.

---

## Challenger review, round 1 (science-reviewer, 2026-10-16 ~00:00Z): ACCEPT_WITH_REQUIRED_CHANGES

Condensed. [D] marks a coordinator decision.

1. **Sealed-directory writes.** q0045/q0047 wrote results inside `history/h6_weather/`, which breaks `verify_seal` (CB1
   freeze-fix 3). Write outside it.
2. **The SEALED-H6 hash split is not independent.** The halves share dates and cities, and the Highest and Lowest events
   of one city-day can split. [D] Use a time-ordered split by end date: SCREEN = earlier end dates, HOLDOUT = the
   latest block (about 40% of events). The boundary is a date rule fixed now and computed from the frame before any
   outcome read, with all events of a city-day in one half. Keep stage P. State the residual (seasonal) dependence and
   recompute the MDEs.
3. **h6 fetch caps and truncation.** Restate CB1 freeze-fixes 2 and 4: cap prices and trades at `min(T_fetch6,
   T_seal)`, count dropped rows, and correct the h4-disjointness claim. Newest-first trades with a 10,000 cap can drop
   the winner's pre-t trades in an outcome-dependent way. Either report exclusions by `Y` and keep the worst-case bound
   binding, or fetch oldest-first / by time window; say which.
4. **Frame.** `walk_weather_events` must also walk closed=false events with `end_at` in the window, count them, and
   treat them as censored/anomalous.
5. **Small G.** Before the census, declare: if cities < 30, use CR2 or a wild-cluster bootstrap with t(G − 1); and a
   minimum G below which W is "not testable".
6. **W2 confound.** At `end_at − 6h` the local daily extreme may already be observed (decided-but-unresolved carry).
   Freeze a city→timezone table, report W2 by local time at origin relative to the typical extreme, and do not credit
   CH27 if the effect sits in post-extreme cities.
7. **X2 estimator/placebo mismatch** (composition and fee channel). Use a category-stratified estimator with ladder-level
   means as the unit and a placebo permuting within the same strata, or drop X2.
8. **Capture-order placebo** is a persistence diagnostic, not a null. State that misgrouping is guarded only by the audit
   and the realised-payoff gate.
9. **Ladder-list version rule vs backfill.** State that v1 applies retrospectively to the dev window, and disclose that
   the text was read after those captures.
10. **Drafting-census provenance.** The census queried closed weather events (8-11 Oct) whose responses include
    `outcomePrices`. Exclude events with end dates in that range from h6 (exact range declared).
11. **Network.** Add 429 back-off and a collector-health stop (latest pass incomplete or late). Re-estimate requests with
    trade pagination honestly.

[D] Drops:
- W1 becomes a reported-only descriptive (no test, not counted).
- P1 (CH10) is reduced to a counts-only gate: no P1 code and no q0050 unless the gate passes, and then only through a
  new design.
- Test count, family/Holm definitions, queue specs and compute are updated to match.

Optional:
- execution at `p_fav(t + 2h)` in history to match stage-P latency;
- the stage-P execution rate;
- a weekly block bootstrap for the Bernoulli placebos;
- h5 exclusion via the committed seal listing (ids only);
- a note that stage P overlaps SEALED-H4's period;
- a text-free extract backfill that need not wait for the grouper hash;
- reconciling "3,200 outcome requests" with "about 3,900 units".

## Response to challenger round 1 (coordinator)

All required items, both drops and all optional items are applied. This is the single response round. The next review
is the code-against-design freeze check.

| Item | Change |
|---|---|
| 1 | q0045/q0047 write to `research_lab/creative_batch2/W_screen/` and `W_holdout/`. Only `ACCESS_LOG.jsonl` appends touch the sealed directory, outside the listing. The runner refuses writes inside a sealed run directory (§1.3, §4.2, §5), and a test runs `verify_seal` after the screen and the holdout. |
| 2 | §1.3: time-ordered split. The group key is the earliest `end_at` date of the city-day. `D_split` = the smallest date leaving ≤ 40% of sampled events in the HOLDOUT. A 2-day embargo is dropped from both halves. The split is computed by q0044 from `end_at`, city and title date only, and recorded in the seal before q0045. Stage P is kept. The residual dependence (season, city mix, market maturity, adjacency) is stated, and a HOLDOUT failure may reflect regime change. MDEs recomputed: SCREEN about 2,000 units, MDE ≈ 3.9c; HOLDOUT about 1,350 units, MDE ≈ 3.7c (k = 1) to 4.7c (k = 5); stage P ≈ 2.3-2.6c divided by the execution rate (§CB2-W). |
| 3 | §1.3 and §4.1 restate CB1 freeze-fix 2 (every price and trade row capped at `min(T_fetch6, T_seal)`, dropped rows counted, no new chunk at or after `T_seal`) and fix 4 (every frame rule implemented and tested, with counts). The h4-disjointness claim now rests on both fixes. **Chosen route: keep newest-first trades with the 10,000 cap** (the Data API offers no deeper or time-window pagination). Unavailable favourites are reported by `Y`, and the worst case (added as losers) is **binding** for W2 and W3 (§2.6 (iv), §CB2-W). |
| 4 | The walk covers closed=true and closed=false. Still-open events and events without a valid single-winner payout stay in the frame and the sample. They are censored/anomalous: excluded from the primary, counted in the payout-anomaly share, coded as losses in the worst case (§CB2-W, §4.1). |
| 5 | §2.3 small-G rule, declared before the census. G ≥ 30: CR1 normal. 15 ≤ G < 30: CR2 with t(G − 1), with a wild-cluster restricted bootstrap (Webb, 9,999 draws) beside it, the larger p used. G < 15 in either way: "not testable". A read-only count found 49 temperature cities in the latest capture. |
| 6 | A frozen city→timezone table (49 cities, hashed; extendable once at the census by city name only). W2 units are classed pre-extreme / during / post-extreme by local time at execution on the measurement date (Highest: 12:00/16:00; Lowest: 05:00/09:00). CH27 is credited only if the pre-extreme subset estimate is positive and ≥ half the full estimate; otherwise a pass is labelled "resolution-lag carry, not CH27" (§CB2-W, verdict map). |
| 7 | X2 replaced, not dropped. The indicator is the fee-free touch violation. The unit is a ladder (its violation rate). The estimator is a fee-category-stratified difference weighted by cross-ladder share. p = max(stratified z, 2,000-draw within-stratum permutation), and the placebo permutes in the same strata. The residual composition within strata is disclosed, and X2 is mechanism-only. MDE ≈ 3.8 pp dev (§CB2-L, §2.6). |
| 8 | §2.6: renamed "capture-order persistence diagnostic", not a null, does not calibrate the gate. Misgrouping is guarded only by the audit gate and the realised-payoff gate (§2.6, §CB2-L, §7 risk 2). |
| 9 | §CB2-L version rule: v1 applies retrospectively to all dev captures from `T2_dev_start`; its text is read after those captures (look-ahead in the frame only, disclosed). v ≥ 2 apply prospectively only. Test updated. |
| 10 | `T_census_ex` = `end_at` in [2026-10-08T00:00Z, 2026-10-12T00:00Z), excluded from h6, counted, in the declaration hash (§0.1, §1.2, q0043 `--exclude-end`). The per-month rate queries for earlier months had unrecorded day windows, so their residual exposure is disclosed as unremovable (§0.1, §7 risk 9). |
| 11 | §2.8: the shared `Limiter` with 429/`Retry-After` back-off and live-collector yield. 429 stop: rps halved above 1% in 10 minutes, chunk ends after 50. Collector-health stop: newest complete capture older than 2h45m, or an incomplete latest manifest with no pass running, ends the chunk as transient. Requests re-estimated at about 70-86k (prices about 55k, trades about 15-30k, walk about 300-600); 6-9 h wall. |
| Drops | W1: `cb2_descriptive` at every stage, no floor, no gate, not counted. P: counts-only gate; P1 floor, placebo, code and q0050 removed; a passing gate leads only to a new design. **Tests: 5 fixed (W2, W3, L1, X1, X2) + up to 7 conditional (Stage 2 ≤ 5, stage P ≤ 2) = 5-12** (was 6-16). Stage-2 Holm k ≤ 5; stage-P Holm k ≤ 2 (§2.3, §6). |
| Optional | All adopted. History executes at `p_fav(t + 2h)` (§2.1, §2.2). Stage-P execution rate reported and MDEs divided by it. The W bootstrap and the Bernoulli placebos use a weekly block bootstrap (§2.3, §2.6). h5 ids come from the committed `h5_cb1_SEAL.json` file table, ids only; q0043 waits for that copy (§1.3). The stage-P / SEALED-H4 calendar overlap is noted (§1.3). q0041 is now a text-free `ladder_candidates/` backfill with no dependence on q0040, about 0.15-0.2 GB (§4.3, §5). Outcome requests reconciled at about 3,900, one per eligible event (§CB2-W compute). |
