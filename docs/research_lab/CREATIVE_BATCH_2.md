# Creative batch 2 (CB2): weather favourites, ladder dominance within and across events, placeholder-member gate

`evidence_role: exploratory_historical` (W screen and holdout) / `exploratory_dev` (L/X/P snapshot development) /
`prospective` (W stage P, L/X replication; data after the freeze) | status: **DRAFT design, not frozen, no challenger
review yet.** Last updated 2026-10-16 00:31 UTC+1.

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
| 1 | **CB2-F** data | ladder list, extract additions, `h6_weather` backfill and seal | none | n/a | n/a | q0040, q0041, q0043, q0044 | 3 + 6-8 h network wall | 1.0 GB |
| 2 | **CB2-W** weather favourites (CH27) | the top-priced temperature bucket resolves YES more often than its ask implies | W1, W2 (economic), W3 (mechanism) | `h6_weather` SCREEN half | `h6_weather` HOLDOUT half, then stage P on captures | q0045, q0047, q0049 | 1.5 | 1.2 GB |
| 3 | **CB2-L** ladder dominance (CH12, CH13) | executable monotonicity violations persist 2h within events (L1) and across events (X1); cross-event violations are more common (X2) | L1, X1 (economic), X2 (mechanism) | extract `ladders/`, captures before `T2_dev_end` | extract `ladders/`, captures in `[T2_rep_start, T2_rep_end)` | q0042, q0046, q0048 | 1.0 | 1.0 GB |
| 4 | **CB2-P** placeholder members (CH10) | a never-traded member's resting quote is executable against its sibling-implied value | gate only (0); P1 only if the gate passes | CB1 extract `negrisk/`, dev | same, rep window | q0042, q0050 | 0.3 | 0.8 GB |

**Why this order.** The `h6_weather` fetch is network-bound (about 68k requests) and must be sealed before the W screen.
The ladder list and the ladder-table backfill must run before raw captures from 2026-10-11 become deletable under the
approved retention (deletion may start about 18 October; release copies remain). W has the largest samples and a short
hold (1-3 days). L/X are cheap but may prove too rare to test. P is a formal gate expected to close CH10.

### 0.1 Selection (pre-design census, 2026-10-15 23:00-23:30Z)

The drafting session ran read-only counts on 6 complete captures on the host (`snapshots/`, touch, `volume_num`,
`last_trade_price`, fee and tick fields; **no outcome was read**), plus 10 public Gamma requests for weather event counts
and 20 for question text. These counts shaped inclusion and are disclosed here; the coordinator may log them as one
`cb2_descriptive` line (counts 0).

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
| `history/h6_weather` (**new**, §CB2-F): temperature events ending 2025-06-01 to before `min(T_fetch6 − 3d, 2026-10-22)`, all buckets | none | SCREEN half: W Stage 1. HOLDOUT half (sealed): W Stage 2, read once, advanced tests only | L1 / L2-dev |
| CB1 extract `negrisk/`, `event_members` (+ new `event_text`) | CB1-D, CB1-A descriptive | W stage P (weather events are neg-risk); P gate and P1 | L1 (dev) / stage P |
| CB2 extract `ladders/` (**new**, §4.3) | none | L/X dev and replication | L1 / L2-dev |
| Raw complete captures, sweeps (host) | E-series, SB2, CB1 | read only by the extractor (pass step and one backfill) and by q0040 (one capture per day, market ids and fee fields only) | - |
| `h2_main`, `h1_first`, `h3_power` | many | **not read**, except their market-id lists to exclude events from `h6_weather` (the CH27 seed, C1, came from h2/h3 weather rows) | - |
| `h5_cb1`, `h5_cb1_ladders` | reserved by CB1 | **not read by any CB2 code path** (§1.3) | - |
| `h4_seal` | reserved by SB2 | not read; no frozen parameter changes (§1.3) | - |
| IF-H2 ladder universe | IF-H2 | `if_h2` deadline parser and stem rule are reused as code; its data are not read | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T2_draft` | 2026-10-15T23:31Z | First draft. Only the §0.1 census (counts, no outcomes) has been computed |
| `T2_dev_start` | 2026-10-11T12:00Z | First sidecar capture (as CB1) |
| `T2_dev_end` | **2026-10-24T00:00Z** | L/X dev and the P gate use captures with `capture_start_utc < T2_dev_end` (about 12.5 days, about 150 captures) |
| `T2_rep_start` | **max(2026-10-26T00:00Z, first complete capture ≥ CB2 freeze commit + 2h)** | L/X replication, P1 and W stage P use only data from here |
| `T2_rep_end` | `T2_rep_start` + 28 d | End of the L/X and P1 window (about 330 captures) |
| `T2_W_end` | `T2_rep_start` + 56 d | W stage P: events with origin `end_at − 24h ≥ T2_rep_start` and `end_at < T2_W_end` |
| `T2_W_out` | `T2_W_end` + 7 d | W stage-P outcome read; still unresolved: censored (§CB2-W) |
| `T2_L_out` | `T2_rep_end` + 30 d | Realised-payoff read for L/X pairs |
| `T_fetch6` | request clock of q0043 | `h6_weather` data end; events must have `end_at < min(T_fetch6 − 3d, 2026-10-22T00:00Z)` |

### 1.3 Sealed and untouched data (named)

- **h5_cb1 and h5_cb1_ladders are avoided entirely.** The CB2 runner refuses run ids `h3_power`, `h4_seal`, `h5_cb1`
  and `h5_cb1_ladders`. CB1's one-read-per-family rule is unaffected. Disclosed overlap: `h5_cb1` samples weather
  markets, so a few `h6_weather` events may contain h5 markets. CB2 does not open h5 to remove them; CB1 tests no
  pre-end favourite in [0.30, 0.95) (A1 is post-end, A2 needs ≥ 0.95, E1 buys NO at listing + 24h).
- **SEALED-H6.** `h6_weather` is split by `sha256("cb2-h6-split|" + event_id)` parity into SCREEN and HOLDOUT before
  any analysis. Both halves are sealed (`h5_seal` machinery, generalised) before q0045. The screen refuses HOLDOUT ids;
  the HOLDOUT is read once, after the freeze, only for W tests that advanced; every read is logged in `ACCESS_LOG.jsonl`.
  No job reads `outcome_prices` before the freeze (census guard as CB1 §2.9).
- **h4_seal unchanged.** `h6_weather` stops before 2026-10-22 (`T_seal`), so it is information-disjoint from SEALED-H4
  analyses (origins ≥ `T_seal`), exactly as CB1 §1.3 argued for h5.
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
| Weather historical ask (W) | `a = min(p + h_W(p), 0.999)`, `h_W(p) = max(h(p), 2.0c)` (CB1 band table `h`; the census median favourite spread was 3.9c). Binding sensitivity `+0.75c`. A dev descriptive of recorded favourite half-spreads by band (captures before `T2_dev_end`, no outcomes) is reported, never used to change `h_W` |
| Recorded ask (W stage P, L/X, P) | Gamma `best_ask` of the token bought; NO side `1 − best_bid`. Depth-checked variant: the pass's first sweep with `ask_size_1 ≥ 5` (or `bid_size_1 ≥ 5` for a NO leg) |
| Ladder pair (L/X) | `C = (a_YES + f(a_YES)) + (a_NO + f(a_NO))`. Structural minimum payoff 1 (§CB2-L); `net = 1 − C`; capital `K = C`; hold to the later scheduled deadline |
| Hold days | to Gamma `closed_time` of the position (W, P1), or to the parsed later deadline (L/X); floor `max(d, 1)` |

### 2.2 Clocks

As CB1 §2.2. History price points usable from stamp + 600 s and at most 2h old. Snapshot features come from the origin
capture; execution prices come from the **next** complete capture with a gap in [1.5, 3] h (as CB1-D), never the origin
one. Trade conditions follow the CB1 truncation rule (known true, otherwise unavailable, never 0; exclusions counted by
outcome with a worst-case bound). Anchors are scheduled facts (`end_at`, parsed deadlines), never `closed_time`.

### 2.3 Uncertainty and decision rule

- Unweighted means are primary. One-sided p = max over the declared cluster ways of CR1 (normal z of the intercept, HB1
  rule); CI by a 2,000-draw cluster bootstrap (seed 216).
  - W: one unit per event; clusters = **end date (UTC day)** and **city**; p = max(day-clustered, city-clustered).
  - L/X: one unit per trigger (L1, X1) or per pair-capture (X2); clusters = ladder (stem group) and ladder × capture
    day.
  - Snapshot dev windows: leave-one-day-out sign stability binding (as CB1 §2.3).
- Testability: ≥ 30 clusters in each declared way and ≥ 100 units; otherwise "not testable" (p = 1, still counted).
- **Stage 1** (W on SCREEN; L/X on dev): advance iff one-sided p < 0.01 in the declared direction, the §2.4 floor is met,
  `R_ann` ≥ 10% for economic tests, the break-even placebo is calibrated (§2.6) and the binding robustness holds. BY
  label (q = 0.10, `battery2.cumulative_count()`) attached as triage only.
- **Stage 2** (W HOLDOUT; L/X replication on SEALED-P; P1): Holm at α = 0.05 one-sided over **all CB2 tests reaching
  Stage 2** (k ≤ 7). Tests finishing early are reported against Bonferroni α/k with k fixed when Stage 1 ends; the final
  batch Holm can only add passes. A pass is "development-replicated (L2-dev)".
- **Stage P** (W only, declared now because weather data accrue at about 100 events a day): run only for W tests that
  passed Stage 2; its own Holm family at α = 0.05; recorded asks with next-capture latency. This is the only CB2 path to
  a confirmation claim and it is itself the economic check.

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| W1, W2 | economic | net ≥ +1.0c per share and `R_ann` ≥ 10% |
| W3 | mechanism | favourite resolution excess ≥ +1.0c |
| L1, X1 | economic | net ≥ +0.50c per pair and `R_ann` ≥ 10% |
| X2 | mechanism | incidence difference ≥ +1.0 percentage point of pair-captures |
| P1 | economic | net ≥ +2.0c per share and `R_ann` ≥ 10% |

### 2.5 Counting (M3 rule)

- Every primary test writes one `trials.jsonl` line via `provenance.append_trial` (kinds `cb2_test`, `cb2_replication`,
  `cb2_prospective`), and each run writes one `ml_explain` count line (`source: "creative_batch_2:<job>"`, `n_tests`).
- New `battery2.KIND_RULES` entries: those three EXCLUDE ("counted by the matching `creative_batch_2:*` count line");
  `cb2_descriptive` EXCLUDE (no inference); seals reuse `history_seal_declaration`. If the CB1 implementation's kind
  names differ from CB1's text (`cb1_structural*` in `cb1_structural.py`), CB2 mirrors whatever is in `KIND_RULES` at
  the freeze; a unit test runs the counter on the real `trials.jsonl`.
- Placebo lines `evidence_role: "placebo"`, count 0. Cumulative count at drafting: about 921 (916 before SB2-J4, plus
  its 5; ledger), plus automatic `flow_screen` lines on the host; the run-time value is recorded in each results file.
- The P gate and all census outputs are `cb2_descriptive` (no outcome read, no inference).

### 2.6 Placebos and robustness

- **Break-even placebo** (W1, W2, P1; as CB1 §2.8): `Y ~ Bern(min(a + f(a), 1))`, 200 draws, full gate; advance rate
  must be ≤ 1.5%. W3 uses `Y ~ Bern(p)`.
- **Capture-order permutation within pair** (L1, X1; as CB1-D): replace the execution capture by a random other capture
  of the same pair; 200 draws; no advance expected.
- **Type-label permutation** (X2): permute "cross"/"within" labels across ladders within fee category; 200 draws.
- **Binding robustness for any advance or pass:** (i) `+0.75c` on every bought leg keeps net > 0; (ii) the test still
  meets p < α and its floor without the top 5 clusters by absolute contribution, in **each** declared way (W: dates
  and cities; L/X: ladders); (iii) the unweighted estimate and the cluster-equal-weighted estimate (W: city; L/X:
  ladder) agree in sign (h6 is a uniform sample, so design weights are constant).
- Reported, not binding: sign by month and by band, `+1c` cost, worst-case outcome coding, truncation bounds, depth-
  checked variants, the `end_at` sensitivity (drop events or pairs resolved more than 7 days after the scheduled date).

### 2.7 Pre-freeze census (q0042; counts only)

Outcome columns are dropped by guard before population code runs. It produces: W SCREEN population and cluster counts
by band and origin (no prices beyond the eligibility band); the recorded weather half-spread descriptive; the L/X
grouper audit (§CB2-L), pair-capture and trigger counts per ladder type; the P gate counts. Floors are never revised
from the census. **The W title regex and the L/X grouper rules are hashed into the declaration before q0040 or q0043
read any question text.**

### 2.8 Compute and stop rules

- Queue worker, one job at a time, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`; never two
  multi-GB jobs at once.
- Priorities: CB2 analysis ≤ 50 (below CB1's 52 and every SB2 job); the extract backfill q0041 at 62 (it preserves data
  before possible deletion, as q0030); the h6 fetch and seal at 59 (after CB1's h5 fetch at 61 and below q0002's 60).
- 15 CPU-hour cap per family. A job failing twice for the same non-transient reason stops and is recorded.
- A null is "not detected at MDE x", never "absent". No re-screen of a failed CB2 test with altered bands, offsets,
  floors or populations, on any data.
- **Disk guard:** q0043 refuses to start while host `data-dumps` exceeds 10 GB (cap 12 GB), and caps itself at 0.30 GB.

---

## 3. Jobs

### CB2-W: Weather favourites (CH27)

**Question.** In multi-bucket temperature events, does the top-priced bucket resolve YES more often than its price, by
enough that buying it at the ask one day (W1) or six hours (W2) before the scheduled end and holding to resolution pays
after costs?

**Why new / overlap.** C1 (descriptive) reported a weather calibration slope of 1.52 [1.14, 2.24] at 1d on h2/h3 rows;
it is the seed and is excluded (h1/h2/h3 events dropped). T5-DEV used price-only resolution features without a
category model. CB1-A/E touch weather markets in different populations (§1.3). The forecast-model version (NWS or
archived model forecasts) is a different, later hypothesis that needs a collector.

**Population (frozen).**
- Event title matches `TEMP_RE = r"^(Highest|Lowest) temperature in (.+?) on (.+?)\?$"` (flags: none); city = group 2.
  4 to 25 member buckets; neg-risk. Events not matching (snow, precipitation, tornadoes) are excluded.
- `end_at` = the event's Gamma `endDate` (mostly 12:00 UTC of the measurement date; the local measurement day differs
  by city, disclosed). Origins: W1 and W3 at `t = end_at − 24h`; W2 at `t = end_at − 6h`.
- History: each bucket's as-of price `p_j(t)` (10-min series, usable from stamp + 600 s, ≤ 2h old). The event is
  excluded (counted) if more than one bucket lacks a usable point. Favourite = highest `p_j(t)`; ties to the lower
  market id.
- Stage P: origin capture c = the last complete extracted capture with start in `(t − 2h, t]`; favourite = highest
  two-sided mid at c; the event must be member-complete (`event_members`) with all members open and accepting orders.
- Eligibility of the favourite: `0.30 ≤ p_fav < 0.95` (band chosen from the census price distribution, no outcomes);
  at least one trade before t (history: stored trades with the truncation rule; stage P: `volume_num > 0` and
  `last_trade_price` present).
- One unit per event and origin.

**Pricing.** History: `a = min(p_fav + h_W(p_fav), 0.999)` at t. Stage P: the favourite token's `best_ask` at the next
capture c' (gap 1.5-3h); no ask at c' → no trade, net 0, kept in the denominator.

| ID | Kind | Origin | Statistic | Direction |
|---|---|---|---|---|
| **W1** | economic | `end_at − 24h` | mean `net = Y_fav − a − f(a)` (cents/share) | > 0 |
| **W2** | economic | `end_at − 6h` | same | > 0 |
| **W3** | mechanism | `end_at − 24h` | mean `Y_fav − p_fav` (history) / `Y_fav − mid_fav(c)` (stage P) | > 0 |

**Declared checks.**
- **Payout anomalies:** share of events whose bucket payouts do not sum to 1 (void, 50-50, multiple winners). Above 2%
  the verdict carries "payout-anomaly sensitive"; worst-case coding counts anomalies as losses.
- **Censoring (stage P):** events unresolved at `T2_W_out` are valued at the last extracted favourite bid and flagged;
  sensitivities at 0 and 1; above 5% censored the verdict carries "resolution-lag sensitive".
- **Descriptive comparators (`cb2_descriptive`):** the second-ranked bucket's excess (spreading predicts it negative);
  highest vs lowest temperature events; by band 0.30-0.45 / 0.45-0.60 / 0.60-0.95; capacity (stage P sweep depth).
- **Truncation worst case:** excluded events added as losers at their ask.

**Family, counting, MDE.**
- Stage 1: 3 `cb2_test` lines plus the count line `creative_batch_2:W`; break-even placebo lines for W1/W2, Bern(p)
  for W3.
- Sample: q0043 samples 5,000 eligible events, about 2,500 per half. With title, band and trade filters (about 0.97 ×
  0.80 × 0.90) about 1,750 units per half per origin. Per-event SD ≈ 0.48 (p ≈ 0.55), so SE ≈ 1.15c × √1.3 (date
  design effect, assumed) ≈ 1.3c.
  - Stage 1 MDE (z 2.33 + 0.84) ≈ **4.2c**; HOLDOUT MDE ≈ 3.3c (k = 1) to 4.3c (k = 7).
  - Stage P (8 weeks, about 100 events a day, about 3,900 units): SE ≈ 0.77c × √1.5 ≈ 0.94c, MDE ≈ **2.3-2.8c**.
- Envelope: the C1 slope implies a gross favourite excess of about +2.6c at p = 0.55 and +9c at p = 0.75, against a
  one-leg cost of about 3c (2c half-spread, 1.2c fee at 0.5). Most −24h favourites sit at 0.40-0.60, so the expected
  net mean is about 0 to +1.5c, **below every MDE**. W3 (gross, about +3-4c) is the realistic detection target; W2 has
  higher-priced favourites and a larger envelope. A null is "not detected at MDE ≈ 4c (screen) / 2.5c (stage P)".

**Verdict map.**
- W1 or W2 passes Stage 2 and stage P with the binding robustness → "prospectively supported weather-favourite carry".
  It already includes the economic check at recorded asks with latency, depth reported.
- W3 replicated, W1/W2 not → "favourite underpricing exists, not tradable after one-leg costs at MDE" (a forecasting
  fact; the maker or forecast-model routes would need their own designs).
- No Stage-1 advance → HOLDOUT unopened, stage P not analysed, CH27 price-only closed at MDE.

**Compute.** Screen: one pass over about 2,500 events' prices (about 15 min, 1.2 GB) plus 2,000 bootstrap and 3 × 200
placebo draws (about 30 min). HOLDOUT the same. Stage P: about 3,200 Gamma outcome requests at T2_W_out (about 15 min
at 4 rps) plus 15 min of analysis.

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
  Refreshed weekly additively; each version hashed, and a rung enters the extract only from the first capture after its
  version's `listed_utc`.
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
| **X2** | mechanism | eligible pair-capture | mean violation indicator (`1 − C(c) > 0`), cross minus within | > 0 |

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
  1.3-1.9c. X2: per-ladder incidence SD ≈ 0.1 with about 600 within- and an unknown number of cross-event ladders; at
  100 cross ladders SE ≈ 1.1 pp, dev MDE ≈ 3.5 pp, rep ≈ 2.5 pp.

**Verdict map.**
- L1 or X1 replicated with both gates → "executable ladder dominance persists 2h (L2-dev)"; a stage-P registration at
  sweep-checked depth would follow, reporting capacity.
- X2 only → "cross-event violations more common, not capturable at 2h latency" (maker route needs continuous books).
- Census: too rare → CH12/CH13 closed "not testable: n triggers from m ladders"; no further work.

**Compute.** q0040 about 1,500 Gamma requests (about 15 min at 2 rps) plus 13 capture reads (about 15 min). q0041
backfill about 150 captures × 1 min ≈ 2.5 CPU-h at nice 19, 1 GB. Dev analysis 10 min; rep 30 min.

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
- **If it passes:** P1 on `[T2_rep_start, T2_rep_end)`: buy the cheap side of u at c' (YES at `ask_u` when
  `fair − ask_u ≥ 5c`; NO at `1 − bid_u` when `bid_u − fair ≥ 5c`), hold to resolution; only events with scheduled
  `end_date ≤ T2_rep_end + 45d`; unresolved at `T2_rep_end + 60d` censored as W. One `cb2_replication` test.

---

## 4. Code needed

### 4.1 Modules

- `backend/astrolabe/research_lab/cb2_weather.py`
  - `walk_weather_events(start, end, limiter)`: Gamma `/events?tag_slug=weather&closed=true` by 7-day end-date windows
    (split while capped); `TEMP_RE` filter; h1/h2/h3 market-id exclusion; seeded sample (`arepo-h6-weather`, 5,000);
    split by the §1.3 hash; outcome fields written to a separate guarded file.
  - `fetch_event_prices(event, ...)`: CLOB prices-history per bucket token, fidelity 10, `[end_at − 72h, end_at + 6h]`;
    trades (≤ 10,000, newest first, truncation flags) for the buckets ranked 1-2 at either origin.
  - `favourite_origin(event, t)`, `weather_unit(...)`, `w_tests(...)`, `stagep_units(extract, event_text, ...)`,
    `fetch_outcomes(...)` (reuse `cb1_structural.fetch_outcomes`).
- `backend/astrolabe/research_lab/cb2_structural.py`
  - `fetch_question_text(ids, limiter)`, `parse_direction(question)`, `ladder_grouper_v2(...)`, `ladder_list(...)` with
    versioned sha256, `audit_sample(...)`.
  - `pair_states(extract)`, `pair_cost`, `next_capture_pairs` (reuse CB1's gap filter), `realised_pair_payoff`,
    `lx_tests`, `placeholder_gate`, `p1_test`.
- Shared statistics are **imported from CB1 code, not copied**: cost model, `trade_condition`, cluster test (generalised
  to arbitrary cluster ways), bootstrap, break-even placebo, capacity, `log_trials`, census guard.
- `HYPOTHESES_CB2` and `declaration_sha256()` covering every population, regex, grouper rule, band, floor, gate and
  date in this file.

### 4.2 Runner

`backend/scripts/run_cb2.py {ladder-list,census,weather-fetch,seal,verify-seal,screen,replicate,snapshots,stagep}
--family W|L|P`. Refuses run ids `h3_power`, `h4_seal`, `h5_cb1`, `h5_cb1_ladders`. Declaration-hash guard (committed
`model_specs/cb2_v1.json` must equal the code's hash) on `screen`, `replicate`, `snapshots` and `stagep`; `replicate
--family W` refuses before the freeze and logs every HOLDOUT read; `snapshots --window rep` refuses before
`T2_rep_end`; `stagep` refuses before `T2_W_out`. Results files are never overwritten. Generalise `h5_seal` (run-id
allowlist plus `h6_weather`) and `scripts/cb1_h5.py seal` rather than duplicating them.

### 4.3 Extractor additions (`creative_batch1.py`, version `cb1-extract-v2`; no change to `arepo_pass.sh`)

- `cb2_extract/ladders/<capture_id>.csv.gz` (own root and manifest), written only when `cb2_extract/ladder_list.json`
  exists: for every listed rung,
  `capture_id, capture_start_utc, received_utc, market_id, event_id, best_bid, best_ask, last_trade_price, closed,
  active, accepting_orders, end_date, volume_num, fee_schedule, fee_category` plus first-sweep `best_bid, best_ask,
  bid_size_1, ask_size_1` (blank if not swept). About 2,000-3,000 rows, about 0.1 MB per capture.
- `event_text.csv.gz`: event `title`, `slug` and member `groupItemTitle` for each neg-risk event, taken from the same
  `/events/{id}` response the extractor already fetches for `event_members` (no extra requests). Needed for `TEMP_RE`
  in stage P; text is read at first extraction (about listing time), disclosed.
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
- The SCREEN/HOLDOUT split is deterministic and disjoint; the screen refuses a HOLDOUT id; HOLDOUT reads are logged.
- The census guard drops outcome columns; the h6 fetch writes outcomes to a separate file.
- `h_W` floor of 2.0c and the `+0.75c` sensitivity; weather fee 0.05 in history.
- `parse_direction`: "by" → INC, "through/until/continues through" → DEC, "on D" and "in October" → excluded; the
  ceasefire and "on date" pairs from §0.1 as fixtures (they must not form violations).
- INC and DEC pair payoffs are ≥ 1 in all three outcome states; fees summed per leg.
- Next-capture execution with the gap filter; a 10h-outage pair is dropped; a rung closed at c' gives no trade.
- Cross-event grouping requires equal masked descriptions.
- The ladder-list version rule: a rung listed after a capture is absent from that capture's extract.
- Placeholder definition: blank `volume_num` with an empty last trade is "never traded"; a blank `volume_num` with a
  last trade is not.
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
 "next_action": "q0041", "notes": "refuses unless the grouper-rule hash is committed; no prices or outcomes read"}
```
```json
{"id": "q0041_cb2_extract_backfill", "title": "CB2: one-off ladders/ + event_text extract from complete captures since 2026-10-11T12:00Z",
 "family": "creative_batch_2", "priority": 62, "expected_value": "preserves L/X dev inputs before raw captures become deletable",
 "data": ["research_lab/snapshots + rows_ext + book_sweeps present on host (else release copies)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": ["q0040_cb2_ladder_list"], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-11T12:00Z", "--tables", "ladders,event_text", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 2, "repeat": {"max_runs": 3, "until_log_regex": "backfill_complete"},
 "outputs": ["cb2_extract/ladders/", "cb1_extract/event_text.csv.gz", "manifest.json"], "next_action": "pass step continues (extractor v2)", "notes": "idempotent by capture_id; CB1 tables untouched; missing captures counted"}
```
```json
{"id": "q0042_cb2_census", "title": "CB2: pre-freeze census (W SCREEN counts, weather half-spreads, L/X audit + trigger counts, P gate counts; no outcomes)",
 "family": "creative_batch_2", "priority": 50, "expected_value": "testability, MDEs and the CH10 gate before the freeze",
 "data": ["h6_weather SCREEN (no outcome file)", "cb1_extract negrisk/event_members/event_text (< T2_dev_end)", "cb2_extract ladders/"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0041_cb2_extract_backfill", "q0044_h6_weather_seal"], "argv": ["scripts/run_cb2.py", "census", "--family", "W,L,P"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch2/census.json"],
 "next_action": "Claude session: insert counts, audit result and P gate into CREATIVE_BATCH_2.md; challenger; freeze", "notes": "commit after T2_dev_end; outcome guard; floors not revised from census"}
```
```json
{"id": "q0043_h6_weather_fetch", "title": "CB2-F: h6_weather backfill (5,000 temperature events, all buckets, prices + top-2 trades)",
 "family": "history_data", "priority": 59, "expected_value": "fresh whole-event weather history for the W screen and holdout",
 "data": ["public Gamma events/CLOB/Data API", "h1/h2/h3 sample market ids (exclusion only)"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api, clob, data-api"},
 "depends_on": [], "argv": ["scripts/run_cb2.py", "weather-fetch", "--run-id", "h6_weather", "--seed", "arepo-h6-weather", "--n-events", "5000", "--end-from", "2025-06-01", "--end-before", "2026-10-22T00:00Z", "--exclude-runs", "h1_first,h2_main,h3_power", "--rps", "4", "--disk-cap-gb", "0.30", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 3, "repeat": {"max_runs": 5, "until_log_regex": "weather_fetch_complete"},
 "outputs": ["data-dumps/research_lab/history/h6_weather/{events.jsonl.gz,prices/,trades/,outcomes_guarded.csv.gz,manifest.json}"],
 "next_action": "q0044", "notes": "about 68k requests; refuses while data-dumps > 10 GB; end_at also < T_fetch6 - 3d; resumable"}
```
```json
{"id": "q0044_h6_weather_seal", "title": "CB2-F: split + seal h6_weather (SCREEN/HOLDOUT listing hashes, trial line, access log)",
 "family": "history_data", "priority": 59, "expected_value": "fixes h6 before any W result exists",
 "data": ["history/h6_weather"], "resources": {"mem_mb": 300, "cpu": 1}, "depends_on": ["q0043_h6_weather_fetch"],
 "argv": ["scripts/run_cb2.py", "seal", "--run-id", "h6_weather"], "timeout_s": 1800, "max_retries": 1,
 "outputs": ["history/h6_weather/{SEAL.json,ACCESS_LOG.jsonl}", "trials.jsonl (1 history_seal_declaration)"],
 "next_action": "Claude session: commit docs/research_lab/seals/h6_weather_SEAL.json", "notes": ""}
```
```json
{"id": "q0045_cb2_screen_W", "title": "CB2-W: declared screen on h6_weather SCREEN (W1, W2, W3; Stage-1 gate; placebos)",
 "family": "creative_batch_2", "priority": 50, "expected_value": "which weather tests advance to the holdout",
 "data": ["history/h6_weather SCREEN (sealed)", "model_specs/cb2_v1.json"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0042_cb2_census"], "argv": ["scripts/run_cb2.py", "screen", "--run-id", "h6_weather", "--family", "W", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["history/h6_weather/cb2/results_W.json", "trials.jsonl (3 cb2_test + count + placebo)"],
 "next_action": "q0047 for advanced tests", "notes": "commit only after the CB2 freeze; verify-seal; declaration-hash guard"}
```
```json
{"id": "q0046_cb2_snap_dev_LX", "title": "CB2-L: ladder dominance dev screen on extracted captures before T2_dev_end (L1, X1, X2)",
 "family": "creative_batch_2", "priority": 50, "expected_value": "2h-latency ladder pair carry; cross vs within incidence",
 "data": ["cb2_extract/ladders (frozen dev capture list)", "ladder_list versions"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": ["q0042_cb2_census"], "argv": ["scripts/run_cb2.py", "snapshots", "--family", "L", "--window", "dev", "--extract-root", "../data-dumps/research_lab/cb2_extract", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch2/L_dev/results.json", "trials.jsonl"],
 "next_action": "if advanced: commit q0048 after T2_rep_end", "notes": "LODO binding; declaration-hash guard; exits 0 'not testable' with counts"}
```
```json
{"id": "q0047_cb2_holdout_W", "title": "CB2-W: frozen replication of advanced W tests on h6_weather HOLDOUT",
 "family": "creative_batch_2", "priority": 50, "expected_value": "development replication (Holm over the CB2 Stage-2 set)",
 "data": ["history/h6_weather HOLDOUT (sealed)", "results_W.json"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0045_cb2_screen_W"], "argv": ["scripts/run_cb2.py", "replicate", "--run-id", "h6_weather", "--family", "W", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["history/h6_weather/cb2/results_W_holdout.json", "trials.jsonl"],
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
 "next_action": "verdict per CB2-W map; ledger", "notes": "commit after T2_W_out; exits 0 'nothing replicated' if Stage 2 empty"}
```
```json
{"id": "q0050_cb2_rep_P1", "title": "CB2-P: P1 placeholder-quote carry on [T2_rep_start, T2_rep_end) (only if the gate passed)",
 "family": "creative_batch_2", "priority": 48, "expected_value": "CH10 economic test", "data": ["cb1_extract negrisk/event_members (rep)", "Gamma outcomes"],
 "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api"}, "depends_on": ["q0042_cb2_census"],
 "argv": ["scripts/run_cb2.py", "snapshots", "--family", "P", "--window", "rep", "--extract-root", "../data-dumps/research_lab/cb1_extract", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch2/P_rep/results.json", "trials.jsonl"],
 "next_action": "batch Holm", "notes": "commit only if the census gate passed, after T2_rep_end + 60d; otherwise never"}
```

## 6. Test budget and compute

| Job | Tests counted | Kind(s) |
|---|---|---|
| W screen | 3 | `cb2_test` + count line |
| L/X dev | 3 | `cb2_test` + count line |
| P gate, census, seal, descriptives | 0 | `cb2_descriptive`, `history_seal_declaration` |
| Stage 2 (W holdout ≤ 3, L/X rep ≤ 3, P1 ≤ 1) | ≤ 7 | `cb2_replication` + count lines |
| W stage P | ≤ 3 | `cb2_prospective` + count line |
| **Total** | **6 fixed + up to 10 conditional (6-16)** | |

**Host compute.** About 5-7 CPU-hours in total at nice 19 (q0041 backfill 2.5 h is the largest), peak 1.2 GB, plus
6-8 h of network-bound wall time for q0043 (about 68k requests at ≤ 4 rps in 150-minute resumable chunks, about 0.25 GB
disk) and about 5k further Gamma requests across q0040, q0048, q0049. The extractor additions add seconds and about
0.1 MB per pass.

## 7. Main scientific risks

1. **Power.** The W net envelope (about 0 to +1.5c on the declared band) is below every W MDE (about 4c screen, 2.5c
   stage P). Expect "not detected at MDE" for W1, with W3 the realistic detection. L/X may be "not testable"; P is
   expected to fail its gate.
2. **Ladder text rules.** Direction and stem errors create fake violations (the §0.1 proxy was entirely such errors).
   The audit gate, the excluded "on D" phrasing and the masked-description guard address this; residual misgrouping
   biases L1/X1 upward, which the realised-payoff gate would expose late (`T2_L_out`).
3. **Modelled weather asks.** History has no weather books. `h_W` = 2c is from one census capture; the binding `+0.75c`
   and stage P at recorded asks with latency are the defences. History selects the favourite on the same price it
   trades at; stage P removes this with next-capture execution.
4. **`end_at` semantics.** Weather `endDate` is a template time (usually 12:00 UTC of the measurement date), so −24h
   and −6h fall at different local hours by city. City clustering and the top-5-cities robustness address
   concentration; the local-time heterogeneity is disclosed, not modelled.
5. **Dependence.** Weather outcomes may correlate across cities on one date (regional weather systems), hence the
   max-of-two-ways rule with ≥ 30 day clusters; the assumed design effects (1.3, 1.5) are unverified until the census.
6. **Survivorship and frame.** The Gamma weather tag walk misses untagged events (disclosed). Events with an unparsable
   title are excluded by rule. Ladder listing survivorship is limited to the daily-capture universe (L/X use only
   markets seen open live).
7. **Overlap with CB1.** Shared captures (CB1-D, B3, A descriptive) and possible shared h5 weather markets are
   disclosed in §1.3; the statistics and populations are disjoint, and no CB2 code path opens h5.
8. **Calendar and disk.** The dev window needs raw captures from 2026-10-11; if retention deletes them before q0041,
   release copies are used (download cost). The host is near its 12 GB cap until snapshot retention is active; q0043
   waits under its disk guard.

## 8. Next actions

1. Challenger review (`science-reviewer`) of this draft; one response round, as CB1.
2. Delegate to `implementer`: `cb2_weather.py`, `cb2_structural.py`, `run_cb2.py`, extractor v2 tables, seal
   generalisation, `KIND_RULES`, tests (§4). Commit the `TEMP_RE` and grouper-rule hashes before q0040/q0043 read text.
3. Commit and run q0040, q0041 (urgent: before raw-capture deletion), then q0043 and q0044 once disk allows.
4. After `T2_dev_end`: q0042 census, insert counts and the audit result here, then the CB2 freeze (`model_specs/
   cb2_v1.json`); `T2_rep_start` follows from it.
5. Then q0045 and q0046; q0047 for advanced W tests; q0048 after `T2_rep_end`; q0049 after `T2_W_out`; q0050 only if
   the P gate passed.

**Open questions for the challenger.**
1. Is the HOLDOUT half worth the screen power it costs (MDE 4.2c vs about 3.4c on all 5,000 events), given that stage P
   follows anyway?
2. Is execution at the next capture with "no trade = net 0 kept" the right convention for W stage P, where the
   favourite may change between captures?
3. Should X2 compare incidence per pair-capture (declared) or per ladder (fewer, more independent units)?

**User decisions.** None required to proceed. Two dependencies are already open with the user: snapshot retention
activation (about 17-18 October) governs both the dev-window raw captures and the disk room for q0043. Sports remain
outside CB2; the category scope stays a parameter.
