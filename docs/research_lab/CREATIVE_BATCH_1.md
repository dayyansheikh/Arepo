# Creative batch 1 (CB1): resolution carry, ladder NO carry, longshot ask-selling, neg-risk set asymmetry, genesis window

`evidence_role: exploratory_historical` (h2 screens, h5 replication) / `exploratory_dev` (snapshot development) /
`prospective` (stage-P parts declared here, data after the freeze) | status: **DRAFT design, not frozen, not reviewed.**
Last updated 2026-10-15 21:00 UTC+1.

This file turns five ideas from `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01, CH05, CH17, CH09, CH22) into declared,
falsifiable development tests, plus one new historical backfill (`h5_cb1`) for frozen replication.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades; every P&L below is a paper rule at modelled or recorded prices.
- These are **economic (carry) hypotheses**. The primary quantity is **net P&L per share** at executable prices after
  fees and the relevant one-leg spread (plus its annualised form and the wrong-side tail), not R² or log loss. A
  mechanism test (does the mispricing exist at all) is labelled "mechanism" and is never read as profitability.
- Every test table becomes binding only when its declaration hash is committed after an accepting `science-reviewer`
  pass (standing rule). Wording, populations, floors and gates may change before the freeze; after it, any change is a
  recorded deviation.
- Queue specs (§4) are drafts. None is committed to `queue/jobs/` by this document.

**Evidence ladder for every CB1 hypothesis (coordinator decision 1).** Screen → independent replication with frozen
definitions → only then a prospective registration with an economic check at executable (recorded) prices. CH05 skips
the screen because its effect was already seen (§CB1-B). Forecasting improvement and profitability are kept separate.

## 0. Summary and ranking

Ranked by expected information per unit of calendar time (the network fetch and the snapshot calendar are the
bottlenecks, not CPU).

| Rank | Job | Hypothesis | Primary tests (≤ 3) | Screen data | Replication data | Queue ids | CPU-h (est.) | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 1 | **CB1-F** h5_cb1 backfill + seal | (data for A, B, C, E) | none (data job) | n/a | n/a | q0016, q0017, q0018 | 0.5 CPU, 6-8 h wall (network) | 0.8 GB |
| 2 | **CB1-A** Decided-but-unresolved carry (CH01) | buy the ≥ 0.95 side after the scheduled end, hold to resolution | A1, A2 | `h2_main` | `h5_cb1` | q0019, q0020, q0024 | 1.5 | 1.5 GB |
| 3 | **CB1-D** Neg-risk set asymmetry (CH09) | sum of asks < 1 persists, sum of bids > 1 does not | D1 (mechanism), D2 | snapshots before `T_dev_end` | snapshots in `[T_rep_start, T_rep_end)` | q0022, q0027 | 1.0 + 2.0 | 2.0 GB |
| 4 | **CB1-B** Near-rung NO carry (CH05) | NO on the earliest live rung, hold to deadline | B1, B2 (mechanism), B3 (stage P) | none (effect already seen in IF-H2) | `h5_cb1_ladders` (pre-IF-H2 ladders); prospective rungs | q0023, q0028 | 0.5 | 1.0 GB |
| 5 | **CB1-C** Longshot ask-selling to resolution (CH17) | resting ask on the ≤ 0.10 side, hold to resolution | C1, C2 | `h2_main` + pmxt book table (q0003) | `h5_cb1` + h5 pmxt books (conditional build) | q0021, q0025, q0026 | 1.0 (+ 8-11 h book build) | 1.5 GB |
| 6 | **CB1-E** Genesis window (CH22) | NO on the affirmative side 24h after listing | E1, E2 (mechanism), E3 | `h2_main` (+ question text) | `h5_cb1` | q0019, q0020, q0024 | 1.0 | 1.5 GB |

**Why this order.**
- The h5 fetch is network-bound (about 73k requests at ≤ 4 rps, yielding to collector passes). It must be fetched and
  sealed before any CB1 screen result exists, so it starts first.
- CB1-A has the largest population on existing data and the clearest mechanism (capital lock after the event).
- CB1-D runs on snapshots that are already collected; its replication window is calendar-bound (3 weeks after freeze).
- CB1-B is cheap but under-powered on history (MDE about the size of IF-H2's descriptive gap); its decisive data are
  prospective rungs that resolve by year-end.
- CB1-C waits for the h2 pmxt book table (q0002/q0003) and has a large MDE (few queue-rule fills).
- CB1-E has a cheap screen but a large MDE on h2.

**Not in this batch:** CH02/CH03 (need a Polygon log scanner), CH10 (placeholder members; next structural batch),
CH16 (sidecar window still short), CH27, CH13. No maker full-set accumulation for CH09 (needs continuous member
trades; see §CB1-D).

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB1 | Evidence ceiling |
|---|---|---|---|
| `history/h2_main` (3,200 sampled markets, 1,759 in the 2h panel; raw 10-min prices and trades for all sampled) | r0-r4 ML, HB1 (PX1-PX6 incl. PX3/PX4 resolution excess, the pooled -7c resolution-excess observation), surprise detector, SB2 J1/J3/J7 | **Screen** for CB1-A, CB1-C, CB1-E. Worn far beyond its revision budget; every CB1 result on it is "beyond budget", L1 at most. Disclosed in each results file | L1 |
| `history_sources/book_features` (pmxt, 6h grid, h2 panel pairs, outcome-0 token, 2026-04-13 to 08-10 minus 06-12..06-17) | ECONOMIC_CONDITIONS part B (h1 books), r4_book, SB2 J3 | CB1-C screen books (after q0003); secondary real-book asks for CB1-A/E on the covered subset | L1 |
| `history/h5_cb1` (**new**, §CB1-F) | none | **Frozen-definition replication** for CB1-A, CB1-C (with h5 books), CB1-E. Read only after the CB1 freeze, and only for tests that advanced | L2-dev |
| `history/h5_cb1_ladders` (**new**, §CB1-F) | none | **Frozen-definition replication** for CB1-B (B1, B2): ladders from events never walked by IF-H2 | L2-dev |
| `if_h2/` ladder universe and panel (1,432 ladders, 1,249 with panel rows) | IF-H2 r0 (null timing signal; descriptive -5.2c near-rung resolution excess) | **Exclusion list only** (event ids, rung ids). Not a CB1 screen: the -5.2c was already seen | none |
| Complete-universe snapshots, sidecar, book sweeps, trade samples | E001-E007, E011 (live, scored after 2026-11-11), flow_screen, SB2 J4/J5 | CB1-D development (captures `< T_dev_end`) and replication (captures in `[T_rep_start, T_rep_end)`); stage-P data for every hypothesis (captures after the matching registration). Read-only; E011 inputs and analysis untouched; hypotheses differ | L1 (dev) / L2-dev (rep) |
| `history/h3_power` | HB1-R, h3_replication, SB2 J2/J6/J8 (reads 4-6) | **Not used.** Retired from replication use after SB2 (Ledger M3). No CB1 code path may open it; the runner refuses the run id | - |
| `history/h4_seal` (to be built ≥ 2026-11-16, `T_seal` 2026-10-22) | reserved for SB2 confirmation | **Not used by CB1.** Its build command must add `h5_cb1,h5_cb1_ladders` to `--exclude-runs` (§CB1-F) | - |
| `history/h1_first` | pilot | Not used (only in `--exclude-runs`) | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T_draft` | 2026-10-15T20:00Z | This draft. No CB1 quantity has been computed on any dataset |
| `T_dev_end` | **2026-10-17T00:00Z** | Snapshot development uses captures with `capture_start_utc < T_dev_end` only. CB1-D dev starts at 2026-10-11T12:00Z (first sidecar capture), so about 5.5 days and about 66 complete captures |
| `T_rep_start` | **max(2026-10-19T00:00Z, first complete capture ≥ CB1 freeze commit time + 2h)** | Replication and stage-P snapshot data begin here. Captures in `[T_dev_end, T_rep_start)` are unused by CB1 (buffer for review and freeze) |
| `T_rep_end` | **2026-11-09T00:00Z** | End of the CB1-D replication window (3 weeks, about 250 captures) |
| `T_fetch` | request clock of the h5 frame fetch (expected 2026-10-16/17) | h5 data end; recorded in the h5 manifest (`request_clock_now`) |
| `T_censor` | `T_fetch` (h5) / h2 `request_clock_now` (h2) | Administrative censoring for hold-to-resolution rules |
| `T_rung_out` | **2027-01-07T00:00Z** | Outcome read for prospective CB1-B rungs (deadlines ≤ 2026-12-31) |

### 1.3 Sealed and untouched data (named)

- **SEALED-H5.** `h5_cb1` and `h5_cb1_ladders` are fetched and sealed (manifest + per-file sha256 + listing sha256,
  §CB1-F) **before any CB1 screen job runs**. The seal record is committed to the repo
  (`docs/research_lab/seals/h5_cb1_SEAL.json`, new path) before the first CB1 screen spec is committed. Every CB1
  replication run verifies the listing hash and refuses on mismatch. No CB1 job reads h5 outcome columns
  (`outcome_prices`, `uma_status`) before the CB1 freeze commit; the census (§2.9) reads none from h5 at all.
- **SEALED-P (CB1).** Every snapshot, sweep, sidecar row and trade sample captured at or after `T_rep_start`. CB1-D
  replication and every stage-P test use only these, and only under a committed declaration.

There is no unworn historical calendar left for the populations CB1 needs: h5 is new markets on a partly new calendar
(lookback to 2025-07), not a new market regime. Confirmation needs SEALED-P.

## 2. Common rules for every CB1 job

### 2.1 Cost conventions (paper; `EXECUTION_COSTS.md`, `economics.py`)

| Item | Rule |
|---|---|
| Taker fee | `f(a) = r · a · (1 − a)` per share on each taker leg. `r`: sidecar `fee_schedule` where a capture has it (snapshots ≥ 2026-10-11T12:00Z), with `fee_policy="conservative"` (max of schedule and docs). History: docs table by `fee_category` (crypto 0.07; sports, economics, culture, weather, other 0.05; finance, politics, mentions, tech 0.04; geopolitics 0); unknown or null category 0.07. Current rates are applied to all past dates (conservative: fees were lower or absent earlier). |
| Maker fee / rebate | 0 / not counted in primary results. Rebate (category share of the counterparty fee, pro rata) is an optimistic secondary only. |
| Historical ask (no book) | `a_hat = p + h(p)`, `p` the as-of series price of the side bought. Half-spread `h` by the side's price band from the 2026-10-11 sweep: < 0.05: 2.05c; 0.05-0.20: 1.50c; 0.20-0.80: 1.10c; 0.80-0.95: 1.50c; ≥ 0.95: 1.25c. Capped at 0.999. Declared sensitivity: `h + 0.75c` (the mean history-series vs pmxt-book gap). |
| Genesis ask (CB1-E only) | `h_gen(p) = max(h(p), 2.5c)` (early books are wide; IMDEA). |
| Recorded ask (snapshots) | Gamma `best_ask` of the side bought (outcome-1 ask = `1 − best_bid` of outcome 0). Book-sweep `best_ask` with `ask_size_1 ≥ 5` as a depth-checked secondary where the token is sweep-eligible. |
| pmxt ask | `sw_best_ask` (outcome 0) or `1 − sw_best_bid` (outcome 1), two-sided state, both clocks ≤ t. |
| Payout `Y` | From Gamma `outcomePrices` of the closed market: 1, 0, or 0.5 (50-50). Closed with missing/unparseable outcome: excluded and counted; worst-case sensitivity counts it as the losing side. |
| Long carry P&L (one leg) | `net = Y_side − a − f(a)`; capital `K = a + f(a)`. |
| Short cheap side (maker) | `net = a_c − Y_c`; capital `K = 1 − a_c`; maker fee 0. |
| Full set (CB1-D) | `net = 1 − Σ_j (a_j + f(a_j))`; capital `K = Σ_j (a_j + f(a_j))`. |
| Censoring | A position still unresolved at `T_censor` is marked at the last as-of price of the side held minus `h` and minus the exit fee (long), or plus `h` (short cheap side buy-back), and flagged. Origins are restricted to `t ≤ T_censor − 60d` so censoring affects only positions open > 60 days. Sensitivities: censored at 0 and at 1. |
| Hold days | `d = (resolution time − entry time)/86400`, resolution time = Gamma `closed_time` (outcome side; used only to end the hold and for clustering, never as an anchor or a population condition). Floor `max(d, 1)`. |
| Annualised | Capital-time ratio `R_ann = 365 · Σ_i w_i net_i / Σ_i w_i K_i max(d_i, 1)`. Not risk-adjusted. |

### 2.2 Clocks

- History price points are usable from stamp + 600 s (10-min fidelity) or stamp + 3600 s (hourly ladder series), at
  most 2h old (12h for hourly ladder series); otherwise no origin. Trades: venue `ts < t` for origin conditions.
- Origins are on fixed UTC grids (2h for CB1-A, 6h for CB1-B/C) or at fixed offsets from `created_at` (CB1-E).
  `created_at` and `end_at` are scheduled/creation facts. **No anchor uses `closed_time`.**
- Membership "open at t" is `created_at ≤ t < closed_time` (a fact observable at t).
- `end_at` is Gamma `endDate` at fetch time; it may have been edited (look-ahead risk, SB2 item 9). Declared
  sensitivity for any test that conditions on `end_at`: drop markets whose `closed_time` is more than 30 days after
  `end_at` (long post-end gaps most often reflect a placeholder or edited end date), and report the prospective
  snapshot `end_date` as the clean version (stage P).
- pmxt events need both clocks ≤ t. Snapshot features come from the origin capture; execution prices for latency tests
  come from the next capture, never the origin one.

### 2.3 Uncertainty

- Unit estimates are design-weighted means (§2.6). One-sided p = max(event-clustered CR1, two-way event ×
  resolution-week CR1) from the normal z of the weighted intercept (HB1 `beta_test` rule). Resolution week = ISO week
  of `closed_time` (or of the censoring mark). Ladders: ladder event × deadline week. CB1-D: event × capture day.
- CI: 2,000-draw event-cluster percentile bootstrap (seed 116).
- Testability: ≥ 30 event clusters and ≥ 100 units (origins, fills or triggers), else "not testable" (p = 1, still
  counted).
- Wrong-side rate: Wilson 95% interval per fee category with ≥ 100 markets.
- Snapshot dev (≈ 5.5 days): day-level shocks cannot be clustered; a leave-one-day-out jackknife is binding (every
  leave-one-day-out estimate must keep the declared sign for a test to advance).

### 2.4 Decision rule (coordinator decision 8)

- **Stage 1 (screen).** A test **advances** only if (a) one-sided p < 0.01 in the declared economic direction
  (net > 0, or the declared mechanism sign) **and** (b) its point estimate meets the materiality floor in §2.5 **and**
  (c) for economic tests, `R_ann` point estimate ≥ 10%. The cumulative BY label (q = 0.10, `battery2.cumulative_count()`)
  is attached as triage only.
- **Stage 2 (replication, frozen).** Holm at α = 0.05, one-sided, over **all CB1 tests that reach Stage 2** (advanced
  A/C/D/E tests plus B1 and B2, which enter directly), with the same sign **and** the floors in §2.5 met by the point
  estimate. Only this is "development-replicated" (L2-dev).
- **Stage P (prospective).** Declared per hypothesis in its own registration after Stage 2, except B3 (§CB1-B), which
  is declared here because its data only exist after the freeze. Stage P is the only path to a confirmation claim, and
  it always includes the economic check at recorded asks.

### 2.5 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| A1, A2 | economic | net ≥ +0.30c per share and `R_ann` ≥ 10% |
| B1 | economic | net ≥ +1.0c per share and `R_ann` ≥ 10% |
| B2 | mechanism | near − far net difference ≥ +1.0c |
| B3 | economic (stage P) | net ≥ +1.0c per share and `R_ann` ≥ 10% |
| C1, C2 | economic | net ≥ +0.50c per filled share and `R_ann` ≥ 10% |
| D1 | mechanism | incidence difference ≥ +1.0 percentage point of event-captures |
| D2 | economic | net ≥ +0.50c per trigger (per $1 set) and `R_ann` ≥ 10% (scheduled-end hold) |
| E1, E3 | economic | net ≥ +1.0c per share and `R_ann` ≥ 10% |
| E2 | mechanism | 7-day YES drift ≤ −0.50c |

### 2.6 Weights and units

- Design weights: h5 `sample_weight` (inverse inclusion probability, stored). h2 has none stored; weights are derived
  from its manifest (`sample_report.strata` sizes over `allocation`: `N_s / n_s`), code `h2_design_weights()`.
  Snapshots and ladders: weight 1. Unweighted estimates are a declared secondary; a sign disagreement is reported and
  blocks a positive verdict.
- One unit per market (CB1-A, CB1-E), per rung (CB1-B), per (market, origin) order (CB1-C, with a market-equal-weight
  secondary), per event-capture (CB1-D).

### 2.7 Counting (M3 rule)

- Every primary test writes one `trials.jsonl` line via `provenance.append_trial`: kind `cb1_test` (screen) or
  `cb1_replication` (Stage 2) or `cb1_prospective` (stage P), with `evidence_role`, `revision`,
  `provenance.run_provenance`, results-file `sha256_file`, `declaration_sha256`.
- Each run also writes one `ml_explain` count line (`source: "creative_batch_1:<job>"`, `n_tests`), so both counters see
  it. New `KIND_RULES` entries in `battery2.py`: `cb1_test`, `cb1_replication`, `cb1_prospective` = EXCLUDE ("per-test
  lines; counted by the n_tests of the matching `creative_batch_1:*` ml_explain line"); `cb1_descriptive` = EXCLUDE
  ("descriptive output, no inference, never used for a decision"); `history_seal_declaration` = EXCLUDE ("data seal; no
  test"). Unknown kinds still raise. A unit test runs the counter against the real `trials.jsonl`.
- Placebo lines carry `evidence_role: "placebo"` and count 0. The cumulative total at run time is recorded in each
  results file.

### 2.8 Placebos and robustness

- **Calibrated-price placebo (every carry test: A1, A2, B1, B3, C1, C2, E1, E3).** Replace `Y` by Bernoulli draws with
  probability equal to the origin's as-of price of the side (200 draws), rerun the full test. Under it the expected net
  is −(spread + fee) < 0, so the advance rate must be ≤ 1%. This replaces the global permutation, which is not a null
  for mean tests (HB1 PX3/PX4 lesson).
- CB1-B: far-rung contrast (B2). CB1-C: filled vs unfilled orders (PX1 check). CB1-D: capture-order permutation within
  event (breaks persistence; D2). CB1-E: sports genesis origins and mature origins (descriptive comparators).
- **Robustness on any advanced or replicated test:** sign in each calendar month and fee category; cost sensitivity
  (`h + 0.75c`, and +1c); without the top 5 events by absolute contribution; weighted vs unweighted; worst-case outcome
  coding (50-50 and missing as losing); censoring at 0 and 1; real-book (pmxt) asks on the covered subset (A, E);
  without IF-H2-universe rungs (A).

### 2.9 Pre-freeze census (counts only)

Before the freeze, q0019 computes on `h2_main` only: population counts, cluster counts and price-band histograms for
A1, A2, E1, E2, E3 (and the C1/C2 order counts once q0003 exists), with outcome columns (`outcome_prices`, `uma_status`)
dropped by a guard before the population code runs. Purpose: confirm testability and the MDEs below. The floors in
§2.5 are not revised from the census. h5 is not opened before the freeze except to compute its seal.

### 2.10 Compute and general stop rules

- Queue worker, one job at a time, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`. CB1 analysis jobs
  have priority ≤ 52 (below every SB2 job); the h5 fetch has priority 61 (above q0002's 60 so it slots between book
  chunks; below SB2's 67-72).
- 15 CPU-hour cap per family per batch. A job failing twice for the same non-transient reason stops and is recorded;
  gates and floors are never loosened.
- A null is reported with its MDE ("not detected at MDE x"), never as absence.
- No re-screen of a failed CB1 hypothesis on h2 or h5 with altered bands, floors, holds or populations.

---

## 3. Jobs

### CB1-A: Decided-but-unresolved carry (CH01)

**Question.** After a market's scheduled end, while it still trades at 0.95-0.99 awaiting resolution, does buying the
favoured side at the ask and holding to redemption earn more than the wrong-side tail plus costs, at a rate worth the
locked capital?

**Redesign for causality (coordinator decision 7).** The creative draft's population ("first time ≥ 0.97 at least 2h
before `closed_time`") conditions on the future close. CB1 replaces it:
- Origins are on the fixed 2h UTC grid. "Decided-but-unresolved" is defined by scheduled and past facts only: the
  scheduled end has passed (`t ≥ end_at`) and the market kept trading after it (≥ 1 trade in `[end_at, t)`).
- The unit is the **first qualifying origin** per market, found by scanning forward from listing. The wait to
  resolution is measured forward from `t`, never used to select.
- Active markets are in both frames (h2 and h5) so the population is not conditioned on having resolved; unresolved
  positions are censored (§2.1).
- The window `t ∈ [end_at, end_at + 24h)` is forced by data: h2's price series ends at `min(close, end_at) + 1d`
  (`history_backfill.price_window`). h5 fetches past it (§CB1-F), and the same 24h window is kept for identical
  definitions.

**Why new / overlap.**
- PX4 (resolution excess at mid ≥ 0.85, not significant, 61 judgement events) and PX2 (favourite 24h drift, replicated on
  h2 but not on h3) are mid-based, not executable, have no hold rule and do not use the scheduled end. C1 is descriptive
  (0.994 priced → 1.000 realised at 1d).
- HB1's incidental pooled -7c resolution excess on resolved traded h2 rows was seen. It concerns all price levels and
  is not a CB1 population, but A2 overlaps PX4's region. Disclosed.
- Near-certain IF-H2 ladder rungs can enter A2 (deadline markets near their end). Robustness check: without
  IF-H2-universe rungs.

**Data.**
- Screen: `h2_main` raw `prices/<id>.csv.gz` (token 0, 10-min fidelity) and `trades/<id>.csv.gz` for all 3,200
  sampled markets (not the 2h panel, whose origins stop at 0.98). Frame columns: `end_at`, `closed_time`, `created_at`,
  `fee_category`, `event_id`, `outcome_prices`, `status`.
- Replication: the same files in `h5_cb1`.
- Stage P: snapshots ≥ `T_rep_start` (Gamma touch, `end_date`, sidecar `accepting_orders`, `fee_schedule`) + Gamma
  outcomes.

**Notation.** `p0` = as-of token-0 price; favourite side `s` = token 0 if `p0 ≥ 0.5`, else token 1 with `p_s = 1 − p0`.
`a = min(p_s + h(p_s), 0.999)` (h = 1.25c in the ≥ 0.95 band). Window and censoring as §2.1. Origins require
`t ≤ T_censor − 60d`.

| ID | Kind | Population (first qualifying 2h origin per market) | Hold | Statistic | Direction |
|---|---|---|---|---|---|
| **A1** | economic | `end_at ≤ t < end_at + 24h`; open at t; `0.95 ≤ p_s ≤ 0.99`; ≥ 1 trade before `end_at`; ≥ 1 trade in `[end_at, t)` | to resolution (censored at `T_censor`) | weighted mean `net = Y_s − a − f(a)` (cents/share) | > 0 |
| **A2** | economic | `t < end_at − 24h`; open at t; `0.95 ≤ p_s ≤ 0.99`; ≥ 1 trade in `[t − 7d, t)` | to resolution (censored) | same | > 0 |

Declared checks (not counted as tests; they gate a positive verdict):
- **Wrong-side tail.** `π̂` = weighted share with `Y_s = 0` (50-50 reported separately), with Wilson CI per fee category
  with ≥ 100 markets. Break-even `π* = 1 − mean(a + f)`.
- **Wait distribution.** Median and p90 of `d` and the censored share; Kaplan-Meier curve for the wait.
- **Sub-band ≥ 0.97** (the creative's band). A sub-band reversal is reported, not tested.
- **Recorded-ask gap (descriptive, dev snapshots `< T_dev_end`).** For post-end markets in snapshots, Gamma
  `best_ask` minus `last_trade_price + 1.25c`. This checks the historical `a_hat` and is logged as `cb1_descriptive`.

**Family, counting, MDE.**
- 2 tests (one `cb1_test` line each + `ml_explain` line `creative_batch_1:A`); calibrated placebo as placebo lines.
- MDE: per-market `net` SD ≈ `sqrt(π(1 − π))` ≈ 12c at π = 1.5%.
  - h2 expected A1 n ≈ 250-450 markets (census to confirm): SE ≈ 0.6c, Stage-1 MDE (z 2.33 + 0.84) ≈ **1.9c**.
  - A2 n ≈ 600-1,000: MDE ≈ 1.3c.
  - h5 (7,000 markets): A1 n ≈ 1,000-1,500, SE ≈ 0.35c, Stage-2 MDE ≈ 0.9c (k = 1) to 1.2c (k = 11).
- The creative envelope (net ≈ 0.6c at a 1% tail) is **below every MDE**. Only a tail rate near 0 or a deeper discount
  can pass. A null means "not detected at MDE ≈ 2c (h2) / 1c (h5)".

**Verdict map.**
- A1 or A2 advances and replicates (Holm, floors, robustness §2.8, unweighted sign agrees, tail check below) →
  "development-replicated carry (L2-dev)". Next: stage-P registration on post-end snapshot markets with
  `accepting_orders = true` at the recorded `best_ask` (sweep depth where eligible), outcomes from Gamma, at least 8
  weeks.
- A positive mean whose Wilson upper bound for `π` exceeds `π*` in the pooled sample → "inconclusive (tail not
  bounded)", whatever the p-value.
- In any category with ≥ 100 markets where the Wilson lower bound for `π` exceeds `π*` → "killed in that category".
- No advance → "not detected at MDE"; CH01 closes on history, with prospective measurement only.

**Compute.** One pass over 3,200 markets' prices and trades, about 25 min, 1.2 GB. Bootstrap 2 × 2,000 plus placebo
200 × 2: about 30 min. h5: about 1 h.

**Code needed.**
- `backend/astrolabe/research_lab/creative_batch1.py`:
  - `cost_model` (§2.1);
  - `favourite_origins(prices, trades, frame_row, rule)` returning the first qualifying origin per market;
  - `carry_pnl(origin, outcome, close, censor)`;
  - `h2_design_weights(manifest)`;
  - `cluster_test(df, w, cluster_cols)` (max-of-two-ways rule plus bootstrap);
  - `wilson`;
  - `calibrated_placebo`;
  - `HYPOTHESES_CB1`, `declaration_sha256()`, `log_trials`.
  - An outcome-column guard for census mode.
- Runner `backend/scripts/run_creative_batch1.py {h2-text,census,screen,replicate,snapshots,ladders-fetch,ladders,seal,verify-seal} --family A|B|C|D|E`.
  It refuses `--run-id h3_power`, refuses `replicate` without a matching committed declaration hash and verified
  SEALED-H5, and never overwrites a results file.

**Tests** (`backend/tests/unit/test_research_lab_creative_batch1.py`):
- The first qualifying origin uses only data ≤ t: a planted post-t price spike does not move it, and `closed_time`
  changes do not change origin selection except through "open at t".
- Price-point lag of 600 s.
- Censoring marks at the last as-of price and flags the row.
- Fee and half-spread tables match `economics.py`.
- `R_ann` ratio arithmetic on a fixture.
- On calibrated placebo data, the advance rate is near 0 (smoke).
- The census guard rejects outcome columns.

**Stop rule.** No A test advances → no h5 read for A.

### CB1-B: Near-rung NO carry on deadline ladders (CH05)

**Question.** Does buying NO on the earliest live rung of a "by date" ladder and holding to its deadline earn the
near-rung YES overpricing after costs, on ladders IF-H2 never saw?

**Why no screen (coordinator decision 5).** IF-H2 r0 reported, descriptively, payout − `v1` = −5.2c [−6.3, −4.1] for
closed near rungs. Any test on IF-H2's own rungs would re-read the observation that generated the hypothesis. CB1-B goes
straight to replication on ladder-disjoint data:
- **R1 (historical):** `h5_cb1_ladders`, events with Gamma `start_date` 2024-01-01 to 2025-05-31. IF-H2 walked
  2025-06-01 onwards, so these ladders were never grouped by IF-H2. Guard: drop any ladder whose event id or any rung id is in
  the IF-H2 universe, or whose any rung is in the h1/h2/h3 samples.
- **R2 (prospective, stage P):** rungs of ladders seen live in snapshots whose deadline falls in
  `[T_rep_start + 2d, 2026-12-31]`.

**Overlap.** IF-H2 (timing signal null; the resolution-excess line is the seed), TI4 (longshot decay near scheduled
end, null, ladders untestable on h2), PX3 (longshots, null), CH06 (level residual; not tested here).

**Data.**
- R1: `ladder-grouper-v1` unchanged (`if_h2.group_ladders`, deadline parse, stem rule, single-event ladders, no neg-risk
  month buckets).
- Rung prices: hourly fidelity in 14-day windows (IF-H2 parity), plus Data API trades per rung (new: IF-H2 had none).
  Gamma `outcomePrices`, `closed_time`, `fee_category` per rung.
- R2: a fresh Gamma `/events` walk (metadata only, start_date 2025-06-01 to `T_rep_start`) grouped by the same grouper.
  Near-rung state per capture from snapshots ≥ `T_rep_start`.

**Population (both R1 and R2).** At origin t (6h grid for R1; each complete capture for R2):
- The near rung is the earliest-deadline rung with ≥ 2 days to its deadline, open at t.
- `0.05 ≤ v1 ≤ 0.60`, `v1 ≤ v2 + 0.01` (consistent ladder; IF-H2 rule).
- ≥ 1 trade on the near rung before t.
- **Unit:** the first eligible origin per rung (one origin per rung), held to the rung's resolution.

NO price is `n1 = 1 − v1`:
- **R1 ask:** `a_NO = min(n1 + max(h(n1), 1c), 0.999)`.
- **R2 ask:** `a_NO = 1 − best_bid` (recorded), with sweep depth as a secondary.

| ID | Kind | Data | Statistic | Direction |
|---|---|---|---|---|
| **B1** | economic | R1, all eligible near rungs | mean `net = Y_NO − a_NO − f(a_NO)` per share | > 0 |
| **B2** | mechanism (far-rung contrast) | R1, origins of B1 where the far rung (next deadline) is valid (`0.02 ≤ v2 ≤ 0.97`, trade before t) | paired mean `net_near − net_far` (far rung's NO bought at the same origin, held to its own resolution) | > 0 |
| **B3** | economic, **stage P** (declared now; data after freeze) | R2 | mean `net` per share, recorded ask | > 0 |

**Listing-survivorship check (declared, gating).**
- At B3 analysis, re-walk Gamma `/events` for R2's start-date range. Report the share of R2 rungs (seen live in
  snapshots) that the walk does not return, and their NO net against returned rungs.
- If ≥ 10% are missing and the missing rungs' YES rate differs from the returned rungs' by more than 5 points, R1 and
  IF-H2's −5.2c are labelled "listing-survivorship biased", and B1 cannot support a positive verdict on its own.
- Secondary for R1: the calendar-disjoint subset (origins before 2025-09-01, IF-H2's grid start).

**Family, counting, MDE.**
- B1 and B2 enter the CB1 Stage-2 Holm family directly (2 `cb1_replication` lines + count line).
- B3 is its own one-test stage-P family (one-sided α = 0.05; `cb1_prospective` line + count line), analysed after
  `T_rung_out`.
- MDE: per-rung NO payout SD ≈ 40c at `v1` ≈ 0.2. Rungs within a ladder are correlated, so effective n ≈ ladders.
  - R1 expected 500-900 ladders (probe first, §CB1-F): SE ≈ 1.5c, so B1 MDE ≈ 3.7c (k = 1) to 5.2c (k = 11).
  - IF-H2's gross gap of 5.2c becomes net ≈ 3.5c after the NO-side half-spread and fee, so B1 has at best about 50%
    power for an effect of IF-H2's size.
  - R2 expected 300-500 ladders with near-rung deadlines by year-end: B3 MDE ≈ 5c.
- A null is "not detected at MDE ≈ 4-5c", which does not refute IF-H2's descriptive estimate.

**Verdict map.**
- B1 and B2 replicated and B3 passes with the survivorship check clean → "near-rung NO carry prospectively supported,
  imminence-specific" (the strongest CB1 outcome; an economic stage-P check is already built in).
- B1 replicated, B2 not → "ladder YES overpricing, not imminence-specific". The far rung becomes an equal candidate and
  needs its own registration.
- B1 not replicated, B3 passes → "inconclusive" (the two disagree; no claim).
- B1 not replicated, B3 fails → CH05 closed; IF-H2's −5.2c stays a descriptive, survivorship-caveated observation.

**Compute.** R1 fetch is part of CB1-F (q0017). Analysis about 20 min, 1.0 GB. R2: the events walk (about 3,500
requests, 30 min) at `T_rep_start`, plus the analysis after `T_rung_out`.

**Code needed.**
- `creative_batch1.ladders_fetch(...)`: `if_h2.discover` over a date range, then `group_ladders`, then exclusion
  guards, then hourly prices and rung trades (resumable, request-capped, `--budget-min`).
- `near_rung_origins(...)`, `ladder_pnl(...)`.
- `prospective_rungs(snapshot_captures, ladders)`.
- `survivorship_check(...)`.

**Tests:**
- Near-rung selection never uses a rung's resolution: a planted early close of a later rung does not change the near
  rung before that close.
- Exclusion guards drop ladders sharing any id with IF-H2 or h1/h2/h3.
- Deadline parse parity with `if_h2` on fixtures.
- One origin per rung.

**Stop rule.** If the R1 probe (§CB1-F) shows < 300 usable ladders, B1/B2 are recorded as "not testable" (counted,
p = 1) and CH05 rests on B3 alone.

### CB1-C: Longshot ask-selling held to resolution (CH17)

**Question.** Does a resting ask at the touch on the ≤ 0.10 side, filled by lottery buyers and held to resolution,
earn the captured half-spread (plus any favourite-longshot premium) net of adverse selection?

**Overlap.** PX1 (longshot rows drift **up** +0.48c/24h; replicated on h3 at +0.73c) is the main threat: if that drift is
information, the resting seller is adversely selected. PX3 (resolution excess −2.2c, not significant), PX6, and
ECONOMIC_CONDITIONS part B (signal-driven passive orders on h1 books lost 1-7c to adverse selection over 2h exits).
New here: no signal (unconditional liquidity provision), the cheap side only, hold to resolution (no exit leg).

**Data.**
- Screen: the q0003 pmxt table for `h2_main` (6h grid, panel pairs, so token-0 price in [0.02, 0.98]), `h2_main`
  trades for fills, Gamma outcomes. **Depends on q0003.**
- Replication: decision below.

**Replication decision (coordinator decision 6).** CB1-C replicates on **h5_cb1 with a pmxt book build restricted to
CB1-C-eligible pairs**, run only if C1 or C2 advances.

Cost of the build:
- About 450 6h origins in the pmxt window at about 60-90 s each (the h1 measurement was 94 s and 540 MB streamed per
  origin): **8-11 h** of nice-19 runtime in 150-minute chunks, about 150-250 GB streamed (ingress, not stored).
- 1.5 GB RAM; output under 10 MB.

Why not prospective only:
- Prospective fill detection is not possible with current collection. Trade samples cover 2,000 markets for one hour per
  2h pass, so the queue position over a 6h order life cannot be reconstructed.
- Longshot resolutions take weeks to months.

A prospective stage P therefore needs a collector extension (continuous trades for a sampled set of longshot markets
plus their sweep books). It is designed only after Stage 2.

**Order rule.** At each 6h origin t with a two-sided book (both clocks ≤ t):
- The longshot side `c` is token 0 if `p0 ≤ 0.5`, else token 1. Its mid `m_c ∈ [0.02, 0.10]`.
- Require ≥ 1 trade in `[t − 7d, t)` and `t ≤ T_censor − 60d`.
- Rest a 5-share ask at `a_c` = the longshot's best ask (token 0: `sw_best_ask`; token 1: `1 − sw_best_bid`).
- Queue ahead `Q0` = displayed size at that level (`sw_ask_size_1`, or `sw_bid_size_1` for token 1). Life `[t, t + 6h)`.
- **Fill (queue rule):** cumulative taker volume buying side `c` at a price ≥ `a_c` within the life reaches `Q0 + 5`.
  - Buying `c` means a BUY of `c` at ≥ `a_c`, or a SELL of the other token at ≤ `1 − a_c` (data-API taker side).
  - All-or-nothing; fill time is the completing trade's `ts`.
- Requires untruncated trades over the life (`trades_oldest_ts ≤ t`).
- **P&L per filled share:** `net = a_c − Y_c`, `K = 1 − a_c`, held from fill to resolution.

| ID | Kind | Population | Statistic | Direction |
|---|---|---|---|---|
| **C1** | economic | filled orders, `fee_category ≠ sports` | mean net per filled share (unweighted over orders; market-equal-weight secondary) | > 0 |
| **C2** | economic | filled orders, `fee_category = sports` | same | > 0 |

**PX1 adverse-selection check (declared, gating).** For C1 and C2 report:
1. The decomposition `net = (a_c − m_c) + (m_c − Y_c)`, i.e. captured half-spread plus resolution excess at the order
   mid.
2. The 24h post-fill drift `m_c(t_fill + 24h) − m_c(t)` for filled orders minus the same for unfilled orders, with CI.
3. C1 recomputed separately for origins with prior-24h longshot change ≥ 0 and < 0.

If (2)'s point estimate exceeds the mean captured half-spread, the verdict is capped at "inconclusive: adverse
selection" even when C1 passes. Also reported: the touch and through fill rules, the net per attempted order (fill
rate × net), and the rebate-optimistic variant (all secondary).

**Family, counting, MDE.**
- 2 tests (`cb1_test` + count line `creative_batch_1:C`); calibrated placebo.
- Expected h2 orders ≈ 4-6k, queue fills ≈ 300-550 in ≈ 100-200 events. Per-fill SD ≈ 22c at a 5% win rate, so
  SE ≈ 1.8c and Stage-1 **MDE ≈ 5.7c**; the creative envelope is +2c.
- h5 (about 3× the pmxt-window markets): MDE ≈ 3.3c.
- CB1-C can only detect a large premium; a null is "not detected at MDE ≈ 6c".

**Verdict map.**
- C1 replicated and the PX1 check is clean → "development-replicated passive longshot carry (L2-dev)". Stage P needs
  the collector extension (separate design and user-visible cost).
- C2 only → the same for sports, with the category-scope decision open (user).
- Neither advances → CH17 closed on history at MDE.

**Code needed:**
- `creative_batch1.longshot_orders(book_rows, trades, frame)` and `queue_fill(...)` (reuse the
  `econ_conditions_maker` fill logic, outcome-0 conversion).
- `run_history_features.py books --run-id h5_cb1 --pair-filter cb1_longshot` (needs `backfill_history.py panel
  --run-id h5_cb1` first).

**Tests:**
- The queue rule needs `Q0 + 5`; a print at a price below `a_c` never fills.
- Token-1 mirroring.
- A truncated-trades window gives no order.
- Post-fill drift uses only `t_fill + 24h` points.

**Stop rule.** No C advance → no h5 book build (saves 8-11 h).

### CB1-D: Asymmetric neg-risk deviations (CH09)

**Question (mechanism).** Because "sum of YES bids > 1" is instantly arbitrageable by conversion while "sum of YES asks
< 1" pays only at resolution, is the under-priced state more common than the over-priced one?

**Question (economic).** Is the under-priced set still buyable at a profit about 2h after it is observed?

**Overlap.** E005/XM1/XM2 (mid-sum deviation as a drift predictor: not supported), L3 (negligible R²), SB2 J5 (lead-lag on
the same captures). None used touch-level `Σ ask` vs `Σ bid`, asymmetry, fees or a set purchase. E011 shares the
captures (read-only; different hypothesis; its analysis untouched).

**Data.**
- Complete captures with sidecar (≥ 2026-10-11T12:00Z).
- **Dev:** `[2026-10-11T12:00Z, T_dev_end)` (≈ 66 captures).
- **Rep:** `[T_rep_start, T_rep_end)` (≈ 250 captures).
- If snapshots have been rotated to the archive, the job restores the listed captures from the release first and checks
  their sha256.

**Event-capture eligibility.** Group rows by `neg_risk_market_id` within a capture:
- `event_neg_risk_augmented` false and `neg_risk_other` false for all members.
- 2-25 open members (`closed` false, `active` true, `accepting_orders` true).
- Every member has `0 < best_bid < best_ask < 1` and sidecar `volume_num > 0`.
- Members already closed are excluded from the sums (resolved-NO members contribute 0). An event with a member resolved
  YES is ineligible.

**Definitions.**
- `S_ask = Σ_j ask_j − 1`, `S_bid = Σ_j bid_j − 1`, `U = 1[S_ask ≤ −0.02]`, `O = 1[S_bid ≥ +0.02]`.
- Set cost with fees `C = Σ_j (ask_j + f(ask_j))`, with `r` from each member's sidecar schedule (conservative policy).
- **Trigger** at capture c: `C(c) ≤ 0.995`.
- **Execution** at the next complete capture c' with gap in [1.5, 3] h: `C_exec = C(c')`, with membership unchanged and
  every member still two-sided. Otherwise no trade (net 0, kept in the denominator).
- **P&L:** payoff 1 per complete set (structural for non-augmented events), so `net = 1 − C_exec` per trigger.
  `R_ann` uses the event's scheduled `end_date` at c as the hold.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **D1** | mechanism | eligible event-capture | mean of `U − O` (difference in incidence) | > 0 |
| **D2** | economic | trigger | mean `net` per trigger (cents per $1 set), executed at the next capture | > 0 |

Declared extras (not counted; `cb1_descriptive`):
- Persistence half-lives of `U` and `O` runs.
- Incidence by fee category (creative ordering prediction crypto > sports > politics > geopolitics).
- The depth-checked D2 variant: every member sweep-eligible with `ask_size_1 ≥ 5`, priced at sweep asks.
- **Payoff audit:** for events resolved by analysis time, the share with not exactly one YES (void, 50-50, multiple
  winners), and D2 recomputed with realised payoffs.

**Placebo.** D2 with the next-capture prices replaced by those of a random other capture of the same event
(capture-order permutation within event, 200 draws): no persistence, so mean net ≤ 0 and no advance.

**Family, counting, MDE.**
- Dev: 2 tests (`cb1_test` + count line `creative_batch_1:D`). Rep: advanced ones only (`cb1_replication`).
- The leave-one-day-out sign rule is binding in dev.
- D1: about 500-800 eligible events, per-event incidence SD ≈ 0.1, so MDE ≈ 1.3 pp (dev) and ≈ 0.8 pp (rep).
- D2: per-trigger SD ≈ 3c in an expected 50-150 trigger events (dev), so MDE ≈ 1.0-1.3c (dev) and ≈ 0.6c (rep).
- If triggers come from fewer than 30 events, D2 is "not testable" (and that is itself the economic answer: the state
  is too rare).

**Verdict map.**
- D1 only (replicated) → "asymmetry exists, not capturable at 2h latency". The maker route (resting bids on all members)
  needs continuous member trade capture (collector extension; next structural batch).
- D2 replicated with a clean payoff audit → stage-P registration at sweep-checked depth with a later window
  (≥ 4 weeks), reporting capacity (sets per week × depth).
- Neither → CH09 closed at MDE.

**Compute.** Dev ≈ 66 captures × 67 MB, read one at a time with neg-risk rows only (≈ 1 GB peak), ≈ 40 min. Rep
≈ 250 captures, ≈ 2 h, 2 GB peak.

**Code needed:**
- `creative_batch1.negrisk_event_captures(capture_dir, sidecar)`, `set_cost`, `next_capture_pairs` (gap filter, as SB2
  J5 item 11), `negrisk_tests`.
- Runner `snapshots --family D --window dev|rep`, which refuses `rep` before `T_rep_end` and refuses captures outside
  the window.

**Tests:**
- Augmented and "Other" events are excluded.
- A member missing an ask at c' gives no trade.
- Fees are summed per leg.
- The window guard rejects a capture at `T_dev_end`.
- The gap filter drops a 10h outage pair.

**Stop rule.** D1 and D2 both fail dev → no rep run (the rep spec is not committed).

### CB1-E: Genesis window (CH22)

**Question.** In the first 24h after listing, is the affirmative (YES) side of non-sports questions overpriced enough
that buying NO at the ask and holding to resolution pays after costs?

**Overlap.** MS1 (market age → |move|, mature origins; hurt out of sample), PX1 (longshots drift up on mature
markets; a different population). No AREPO panel has origins in the first day (the ML panel starts one day after the
first price), so the genesis window is unread. The listing-period price points exist in h2 only for markets whose fetched
window starts at listing (below).

**Data.**
- Screen: `h2_main` raw prices and trades, plus question text and outcome labels fetched for the 3,200 sampled markets
  (q0019; h2 was not run in power mode, so text is absent; about 160 Gamma requests).
- Replication: `h5_cb1` (text and outcomes stored; `--head-days 8` guarantees listing-period prices).

**Population.**
- `outcomes` = ["Yes", "No"], with YES = the "Yes" token; `fee_category ≠ sports`.
- **Scheduled life** `end_at − created_at ≤ 100 days`. This is a scheduled fact. It makes h2's 120-day price window
  cover the listing for every included market, whatever its actual close, so inclusion does not depend on early
  resolution.
- ≥ 3 trades in `[created_at, t)`.
- Origin `t = created_at + 24h` (primary; +6h and +12h secondary). As-of YES price `p_Y ∈ [0.05, 0.80]`.
- Open at t; `t ≤ T_censor − 60d`.
- One unit per market.

**Pricing.** NO bought at `a = min((1 − p_Y) + h_gen(1 − p_Y), 0.999)`, held to resolution (censored), so
`net = Y_NO − a − f(a)`.

**Sensational rule (frozen text rule).** The question contains a token from the frozen list `{arrest, indict, resign,
impeach, invade, invasion, attack, strike, assassinat, convict, jail, prison, fired, removed, ousted, coup, martial
law, nuclear, war, collapse, default, crash, hack, sanction, ban, die, dies, death, killed, out as}` (case-insensitive,
word-start match), **and** a capitalised two-word name not at the sentence start (regex frozen in code). Both are
applied to the question text only.

| ID | Kind | Population | Statistic | Direction |
|---|---|---|---|---|
| **E1** | economic | all eligible non-sports Yes/No markets, origin +24h | weighted mean `net` per NO share | > 0 |
| **E2** | mechanism | same | weighted mean 7-day YES drift `p_Y(t + 7d) − p_Y(t)` (payout if closed earlier) | < 0 |
| **E3** | economic | E1 ∩ sensational | weighted mean `net` | > 0 |

Declared comparators (descriptive):
- Sports Yes/No genesis origins (expected null).
- The same markets at age ≥ 30 days (mature drift; survivorship disclosed).
- PX1/PX2 levels.

Declared robustness (the creative kill test): on the pmxt-covered subset, replace `p_Y` and `a` by the first two-sided
book at or after origin (≤ 1h). If E1/E2 lose sign there → "artefact of the first-trade price".

**Family, counting, MDE.**
- 3 tests (`cb1_test` + count line `creative_batch_1:E`); calibrated placebo for E1/E3.
- h2 eligible ≈ 200-400 markets: E1 SE ≈ 2.3c, so Stage-1 **MDE ≈ 7c** (envelope 3-5c gross, about 1-2c net). E2 SD
  ≈ 8c, so MDE ≈ 1.5c.
- h5 (non-sports weighted ×1.5): E1 n ≈ 800-1,200, MDE ≈ 3.5-4.5c.
- E2 is the realistic h2 detection target. E1 on h2 can only catch a large effect.

**Verdict map.**
- E1 (or E3) replicated with robustness → "development-replicated genesis carry". Stage P on new listings in snapshots
  (sidecar `created_at`), recorded asks, at least 8 weeks.
- E2 replicated, E1 not → "genesis overpricing exists, not tradable after costs at MDE" (a forecasting-side fact, not
  profit).
- None → CH22 closed at MDE.

**Code needed:**
- `creative_batch1.h2_text_fetch` (Gamma `/markets?id=` batches of 20, metadata only, written under
  `h2_main/cb1/text.csv.gz`).
- `genesis_origins`, `sensational()` (frozen list and regex; hash in the declaration), `drift_7d`.

**Tests:**
- The scheduled-life rule uses `end_at`/`created_at` only.
- A trade at `t + 1s` does not count.
- `sensational()` gives frozen fixture outputs.
- The genesis half-spread floor is 2.5c.

**Stop rule.** No E advance → no h5 read for E.

### CB1-F: The `h5_cb1` and `h5_cb1_ladders` backfills, and the seal

**Purpose.** Market-disjoint historical replication data for CB1-A, CB1-C and CB1-E (`h5_cb1`), and ladder-disjoint data
for CB1-B (`h5_cb1_ladders`). Fetched and sealed before any CB1 screen result exists.

**h5_cb1 (markets).** Command (new options marked *):

```
python scripts/backfill_history.py run --run-id h5_cb1 --seed arepo-h5-cb1 \
  --exclude-runs h1_first,h2_main,h3_power --n-markets 7000 --lookback-days 450 \
  --closed-future-days 400* --strata-profile cb1* --max-days 120 --head-days 8* \
  --price-end close_or_end_max* --max-trades 10000 --rps 4 --anchored-live-check \
  --disk-cap-gb 0.62 --budget-scope run --checkpoint-every 200 --budget-min 150*
```

- **Frame.** `frame-v2-random-windows`: 6 random 15-minute windows per day.
  - Closed markets by `end_date` over the last 450 days **and the next 400 days**. `--closed-future-days`: markets
    resolved early with a future `endDate` are otherwise absent, which would bias CB1-A A2 and any early-YES rung.
  - Active markets by `start_date` over the last 450 days.
- **Completeness rule.** CB1-A/E use only markets with `created_at ≥ T_fetch − 450d`, for which the frame is complete
  up to the random-window sampling. A long-unresolved market created inside the lookback is in the active walk.
- **Sample.** `--strata-profile cb1`: strata `status × topic × creation month` (as power mode) with creation-known weights:
  - crypto "Up or Down" questions × 0.25 (they resolve automatically within minutes and dominate the frame);
  - other non-sports × 1.5;
  - sports × 1.0.
  - Proportional over status. `inclusion_prob` and `sample_weight` are stored.
  - **No price-, volume- or outcome-based oversampling** (near-certain, longshot or ladder status are path or outcome
    attributes; using them would make inclusion depend on the path).
  - Question, event title, slug, topic and **`outcomes`** (new frame column) are stored.
- **Prices.**
  - `--price-end close_or_end_max`: the tail window ends at `max(close, end_at) + 1d`, so post-end waits are covered.
  - `--head-days 8`: one extra window `[start, start + 8d]` when the tail window does not reach the listing.
- **Trades.** Up to 10,000 per market (API offset cap); truncation recorded.
- **Expected size.** 7,000 markets at ≈ 75 KB each (h2: 202 MB for 3,200 markets at max-trades 5,000) gives
  **≈ 0.53 GB** (cap 0.62 GB).
- **Requests.**
  - Frame: (450 + 400) days × 6 windows × ≈ 1.8 pages for closed plus ≈ 3k for active, ≈ 12k.
  - Markets: ≈ 6 per market (3 price windows, 1 head window, 1.5 trade pages), ≈ 42k.
  - **≈ 54k requests in total.**

**h5_cb1_ladders.**
- Command: `run_creative_batch1.py ladders-fetch --run-id h5_cb1_ladders --start 2024-01-01 --end 2025-05-31
  --exclude-runs h1_first,h2_main,h3_power --exclude-ifh2 <if_h2 ladder file> --rps 4 --disk-cap-gb 0.15
  --budget-min 150`.
- Gamma `/events` walk by start date in 7-day windows (split while capped; tag 102127 excluded), then
  `ladder-grouper-v1`, then the exclusion guards (§CB1-B).
- Then per rung: hourly prices over the rung's life (14-day windows), trades (≤ 10,000), and outcome metadata.
- **Probe first:** 20 random 2024 rungs. If fewer than 80% return price points, stop and record (B1/B2 become not
  testable; CB1-B rests on B3).
- **Expected:** 500-900 ladders and ≈ 3,000 rungs; ≈ 1.5k walk + 12k price + 5k trade requests, **≈ 19k requests**;
  **≈ 0.1 GB**.

**Totals and cost.**
- **≈ 73k requests at ≤ 4 rps:** ≈ 5.1 h of request time, ≈ 6-8 h wall with collector yields (`live_check`; about 18
  minutes per 2h pass) and retries. That is 3-4 chunks of 150 minutes.
- **Disk ≈ 0.63 GB** (hard caps 0.62 + 0.15 = 0.77 GB ≤ the 0.8 GB budget). Host `data-dumps` is about 7 GB against
  the 12 GB cap and grows about 1 GB/day from snapshots, so h5 moves the cap date forward by about 0.7 days. It must be
  coordinated with the archive rotation (owned by another session). After the seal, h5 is archived to an
  `arepo-data` release by the existing process.
- RAM ≈ 0.6-0.8 GB; CPU low (network-bound).

**Seal (q0018).** `run_creative_batch1.py seal --run-id h5_cb1,h5_cb1_ladders` writes `SEAL.json` in each run dir:
- sorted per-file sha256 and the listing sha256;
- file count and total bytes;
- the manifests' request clocks;
- git commit and seal time.

It appends one `history_seal_declaration` trial line. The coordinator commits a copy as
`docs/research_lab/seals/h5_cb1_SEAL.json` before any CB1 screen spec (q0020-q0022) is committed. `verify-seal` is
called by every h5 reader.

**Ordering guarantee.** q0020-q0022 depend on q0018 in the queue, and the runner's `screen` refuses to start unless
the committed seal file exists. The h5 fetch parameters above are fixed by this draft and contain nothing that depends
on any CB1 result.

**Read rules.** h5 is read at most once per CB1 hypothesis family, with frozen definitions only (CB1-A, CB1-C, CB1-E),
and B1/B2 for the ladders. No discovery, no re-estimation of bands, floors or rules on h5. After CB1, h5's
replication role is recorded in the ledger (one read per family).

**Code needed** (`history_backfill.py`, `backfill_history.py`):
- `--closed-future-days N` (forward closed walk, same window scheme);
- `--strata-profile cb1` (weights above; implies text columns);
- the `outcomes` frame column;
- `--head-days`;
- `--price-end {min,close_or_end_max}` (default `min` keeps h1-h3 behaviour);
- `--budget-min` (wall-clock stop between markets, resumable; exit 0 "budget reached").

Tests:
- The future walk uses the same seeded windows.
- `cb1` weights are creation-known (no volume or outcome field read).
- `head_days` adds exactly one window.
- `close_or_end_max` extends only closed markets.
- `--budget-min` stops cleanly and resumes.
- Seal and verify-seal round trip; a modified file fails verification.

**Amendment to SB2 §1.2 (collection parameter only).** The h4_seal command must use `--exclude-runs
h1_first,h2_main,h3_power,h5_cb1` and also drop `h5_cb1_ladders` rung ids, so SEALED-H4 stays market-disjoint. This
changes no SB2 test.

---

## 4. Draft queue specs

Paths follow `queue/README.md` (`argv[0]` under `backend/scripts/`, `cwd` `backend`). **None may be committed until
its code and tests exist and, for test jobs, the reviewed CB1 freeze commit exists.** q0016-q0018 need code and a
reviewer pass of §1 and §CB1-F only.

```json
{"id": "q0016_h5_cb1_fetch", "title": "CB1-F: h5_cb1 market backfill (disjoint from h1/h2/h3; cb1 strata profile)",
 "family": "history_data", "priority": 61,
 "expected_value": "sealed replication data for CB1-A/C/E; calendar is the bottleneck",
 "data": ["public Gamma/CLOB/Data API"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api, clob, data-api"},
 "depends_on": [],
 "argv": ["scripts/backfill_history.py", "run", "--run-id", "h5_cb1", "--seed", "arepo-h5-cb1", "--exclude-runs", "h1_first,h2_main,h3_power", "--n-markets", "7000", "--lookback-days", "450", "--closed-future-days", "400", "--strata-profile", "cb1", "--max-days", "120", "--head-days", "8", "--price-end", "close_or_end_max", "--max-trades", "10000", "--rps", "4", "--anchored-live-check", "--disk-cap-gb", "0.62", "--budget-scope", "run", "--checkpoint-every", "200", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 3, "repeat": {"max_runs": 8, "until_log_regex": "\"markets_done\": 7000|stopped\": null"},
 "outputs": ["data-dumps/research_lab/history/h5_cb1/{frame,sample}.csv.gz, prices/, trades/, manifest.json"],
 "next_action": "q0017, then q0018", "notes": "no outcomes read by any job before the CB1 freeze; resumable"}
```
```json
{"id": "q0017_h5_cb1_ladders_fetch", "title": "CB1-F: pre-IF-H2 ladder universe (events 2024-01..2025-05), rung prices and trades",
 "family": "history_data", "priority": 61, "expected_value": "ladder-disjoint data for CB1-B B1/B2",
 "data": ["public Gamma events/CLOB/Data API", "if_h2 ladder file (exclusion only)"],
 "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api, clob, data-api"}, "depends_on": [],
 "argv": ["scripts/run_creative_batch1.py", "ladders-fetch", "--run-id", "h5_cb1_ladders", "--start", "2024-01-01", "--end", "2025-05-31", "--exclude-runs", "h1_first,h2_main,h3_power", "--rps", "4", "--disk-cap-gb", "0.15", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 3, "repeat": {"max_runs": 4, "until_log_regex": "ladders_fetch_complete|probe_failed"},
 "outputs": ["data-dumps/research_lab/history/h5_cb1_ladders/{ladders.jsonl.gz,prices/,trades/,manifest.json}"],
 "next_action": "q0018", "notes": "probe of 20 rungs first; exits 0 'probe_failed' if < 80% have prices"}
```
```json
{"id": "q0018_h5_cb1_seal", "title": "CB1-F: seal h5_cb1 + h5_cb1_ladders (per-file sha256, listing hash, trial line)",
 "family": "history_data", "priority": 61, "expected_value": "fixes h5 before any CB1 screen result exists",
 "data": ["history/h5_cb1", "history/h5_cb1_ladders"], "resources": {"mem_mb": 300, "cpu": 1},
 "depends_on": ["q0016_h5_cb1_fetch", "q0017_h5_cb1_ladders_fetch"],
 "argv": ["scripts/run_creative_batch1.py", "seal", "--run-id", "h5_cb1,h5_cb1_ladders"],
 "timeout_s": 1800, "max_retries": 1, "outputs": ["history/h5_cb1*/SEAL.json", "trials.jsonl (1 history_seal_declaration)"],
 "next_action": "Claude session: commit docs/research_lab/seals/h5_cb1_SEAL.json; amend h4_seal exclude list; then commit q0020-q0022", "notes": ""}
```
```json
{"id": "q0019_cb1_h2_text_census", "title": "CB1: h2_main question/outcome text fetch + population census (no outcome columns)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "testability and MDEs before freeze",
 "data": ["history/h2_main (frame, prices, trades)", "Gamma /markets metadata"], "resources": {"mem_mb": 1500, "cpu": 1, "network": "gamma-api"},
 "depends_on": [], "argv": ["scripts/run_creative_batch1.py", "census", "--run-id", "h2_main", "--fetch-text", "--rps", "4"],
 "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h2_main/cb1/{text.csv.gz,census.json}"],
 "next_action": "Claude session: insert census counts into CREATIVE_BATCH_1.md; reviewer pass; freeze", "notes": "outcome columns dropped by guard; floors not revised from census"}
```
```json
{"id": "q0020_cb1_screen_h2_AE", "title": "CB1-A/E: declared screen on h2_main (A1, A2, E1, E2, E3; Stage-1 gate; placebo)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "which carry tests advance to frozen h5 replication",
 "data": ["history/h2_main", "history/h2_main/cb1/text.csv.gz", "model_specs/cb1_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0018_h5_cb1_seal", "q0019_cb1_h2_text_census"],
 "argv": ["scripts/run_creative_batch1.py", "screen", "--run-id", "h2_main", "--family", "A,E", "--n-boot", "2000"],
 "timeout_s": 10800, "max_retries": 1, "outputs": ["history/h2_main/cb1/results_cb1_AE.json", "trials.jsonl (5 cb1_test + count line + placebo)"],
 "next_action": "Claude session: record; q0024 for advanced tests", "notes": "refuses without committed seal and declaration hash; L1 beyond budget"}
```
```json
{"id": "q0021_cb1_screen_h2_C", "title": "CB1-C: longshot ask-selling screen on h2_main pmxt books (C1, C2; PX1 check)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "passive longshot carry screen",
 "data": ["history_sources/book_features/book_features.csv.gz (q0003)", "history/h2_main trades/frame"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0003_books_finalize", "q0018_h5_cb1_seal"],
 "argv": ["scripts/run_creative_batch1.py", "screen", "--run-id", "h2_main", "--family", "C", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["history/h2_main/cb1/results_cb1_C.json", "trials.jsonl"],
 "next_action": "if C advanced: q0025 then q0026", "notes": ""}
```
```json
{"id": "q0022_cb1_snap_dev_D", "title": "CB1-D: neg-risk asymmetry dev screen on captures before T_dev_end (D1, D2)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "mechanism + 2h-latency set carry",
 "data": ["research_lab/snapshots + sidecar, 2026-10-11T12:00Z <= capture < 2026-10-17T00:00Z"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0018_h5_cb1_seal"],
 "argv": ["scripts/run_creative_batch1.py", "snapshots", "--family", "D", "--window", "dev", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch1/D_dev/results.json", "trials.jsonl"],
 "next_action": "if advanced: commit q0027 spec after T_rep_end", "notes": "E011 untouched; leave-one-day-out binding"}
```
```json
{"id": "q0023_cb1_ladders_B", "title": "CB1-B: frozen B1/B2 on h5_cb1_ladders (enter Stage-2 Holm directly)",
 "family": "creative_batch_1", "priority": 50, "expected_value": "near-rung NO carry on IF-H2-disjoint ladders",
 "data": ["history/h5_cb1_ladders (sealed)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": ["q0018_h5_cb1_seal"],
 "argv": ["scripts/run_creative_batch1.py", "ladders", "--run-id", "h5_cb1_ladders", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["history/h5_cb1_ladders/cb1/results_B.json", "trials.jsonl (2 cb1_replication + count)"],
 "next_action": "Claude session: hold p-values for the batch Holm (§2.4)", "notes": "verify-seal; declaration hash"}
```
```json
{"id": "q0024_cb1_replicate_h5_AE", "title": "CB1-A/E: frozen replication of advanced tests on h5_cb1",
 "family": "creative_batch_1", "priority": 50, "expected_value": "development replication (Holm over the CB1 Stage-2 set)",
 "data": ["history/h5_cb1 (sealed)", "results_cb1_AE.json"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0020_cb1_screen_h2_AE"],
 "argv": ["scripts/run_creative_batch1.py", "replicate", "--run-id", "h5_cb1", "--from", "h2_main", "--family", "A,E", "--n-boot", "2000"],
 "timeout_s": 10800, "max_retries": 1, "outputs": ["history/h5_cb1/cb1/results_cb1_AE_rep.json", "trials.jsonl"],
 "next_action": "Claude session: batch Holm, verdicts, ledger", "notes": "exits 0 'nothing advanced' if empty"}
```
```json
{"id": "q0025_h5_books_C", "title": "CB1-C: h5_cb1 panel + pmxt books for CB1-C-eligible pairs (conditional)",
 "family": "creative_batch_1", "priority": 48, "expected_value": "enables C replication",
 "data": ["history/h5_cb1", "pmxt v2 hourly (range reads)"], "resources": {"mem_mb": 1500, "cpu": 1, "network": "r2v2.pmxt.dev"},
 "depends_on": ["q0021_cb1_screen_h2_C"],
 "argv": ["scripts/run_history_features.py", "books", "--run-id", "h5_cb1", "--pair-filter", "cb1_longshot", "--budget-min", "150"],
 "timeout_s": 16200, "max_retries": 3, "repeat": {"max_runs": 8, "until_log_regex": "\"pairs_done_total\": (\\d+), \"pairs_total\": \\1,"},
 "outputs": ["history_sources/book_features_h5_cb1/"], "next_action": "q0026", "notes": "exits 0 'skipped: no C advanced'; needs h5 panel first (same job prepends it)"}
```
```json
{"id": "q0026_cb1_replicate_h5_C", "title": "CB1-C: frozen replication on h5_cb1 books",
 "family": "creative_batch_1", "priority": 48, "expected_value": "C replication", "data": ["h5 books + trades"],
 "resources": {"mem_mb": 1500, "cpu": 1}, "depends_on": ["q0025_h5_books_C"],
 "argv": ["scripts/run_creative_batch1.py", "replicate", "--run-id", "h5_cb1", "--from", "h2_main", "--family", "C", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["history/h5_cb1/cb1/results_cb1_C_rep.json", "trials.jsonl"], "next_action": "batch Holm", "notes": ""}
```
```json
{"id": "q0027_cb1_snap_rep_D", "title": "CB1-D: frozen replication on captures in [T_rep_start, T_rep_end)",
 "family": "creative_batch_1", "priority": 50, "expected_value": "D replication (prospective captures)",
 "data": ["snapshots + sidecar in the rep window"], "resources": {"mem_mb": 2000, "cpu": 1},
 "depends_on": ["q0022_cb1_snap_dev_D"],
 "argv": ["scripts/run_creative_batch1.py", "snapshots", "--family", "D", "--window", "rep", "--n-boot", "2000"],
 "timeout_s": 14400, "max_retries": 1, "outputs": ["research_lab/creative_batch1/D_rep/results.json", "trials.jsonl"],
 "next_action": "batch Holm", "notes": "commit this spec only after 2026-11-09T00:00Z; runner refuses earlier"}
```
```json
{"id": "q0028_cb1_rungs_prospective_B3", "title": "CB1-B: B3 prospective rungs + listing-survivorship check",
 "family": "creative_batch_1", "priority": 50, "expected_value": "stage-P near-rung NO carry",
 "data": ["snapshots >= T_rep_start", "Gamma events walk (metadata)", "Gamma outcomes"], "resources": {"mem_mb": 1500, "cpu": 1, "network": "gamma-api"},
 "depends_on": [], "argv": ["scripts/run_creative_batch1.py", "ladders", "--prospective", "--rps", "4", "--n-boot", "2000"],
 "timeout_s": 10800, "max_retries": 2, "outputs": ["research_lab/creative_batch1/B3/results.json", "trials.jsonl (1 cb1_prospective + count)"],
 "next_action": "verdict per CB1-B map", "notes": "commit only after 2027-01-07; the rung list is frozen from the events walk at T_rep_start (a separate small job, not results)"}
```

## 5. Test budget

| Job | Tests counted | Kind(s) |
|---|---|---|
| CB1-A screen | 2 | `cb1_test` + count line |
| CB1-E screen | 3 | `cb1_test` + count line |
| CB1-C screen | 2 | `cb1_test` + count line |
| CB1-D dev | 2 | `cb1_test` + count line |
| CB1-B (direct to Stage 2) | 2 | `cb1_replication` + count line |
| Stage-2 replications (A, C, D, E) | ≤ 9 (advanced only) | `cb1_replication` + count lines |
| B3 (stage P) | 1 | `cb1_prospective` + count line |
| Seal, census, descriptive lines | 0 | `history_seal_declaration`, `cb1_descriptive` |
| **Total** | **12 fixed + up to 9 conditional (12-21)** | |

The local cumulative count was 906 on 2026-10-15 (Ledger M3); SB2 adds 59-99, plus automatic `flow_screen` lines. CB1
uses the run-time `battery2.cumulative_count()` value for BY triage labels only. The Stage-2 Holm family is the CB1
Stage-2 set (k ≤ 11).

## 6. Main scientific risks

1. **Power.** Every historical MDE (A ≈ 1-2c, B ≈ 4-5c, C ≈ 3-6c, E1 ≈ 4-7c) is at or above the creative envelopes.
   Most nulls will read "not detected at MDE", not "absent". The tail-dominated carries (A, C) are decided by rare
   wrong-side outcomes, so a few events can swing them (top-5-event robustness is binding).
2. **Modelled asks.** History has no book outside the pmxt window. The series price is mid-like with an unverified
   stamp convention (mean gap to pmxt ≈ 0.75c). Band half-spreads come from one 2026-10-11 sweep, and genesis books
   are wider. Positive history results are capped at "development" until stage P re-prices at recorded asks.
3. **`end_at` look-ahead (A1).** "Past the scheduled end" uses the end date at fetch time, which may have been edited.
   Only stage P (snapshot `end_date` at capture) is clean.
4. **Survivorship.**
   - The Gamma frame lacks long-lived active markets created before the lookback (A and E restrict to created inside
     it).
   - Early-resolved markets with a future `endDate` (fixed by `--closed-future-days` in h5 only; h2 lacks them, which
     biases the h2 A2 screen, direction unknown, disclosed).
   - Ladder listing survivorship (B; checked prospectively).
5. **Fee regime.** Current fee rates are applied to periods with lower or no fees. This is conservative for P&L, but
   it means market behaviour under the current fees is untested before stage P.
6. **Dependence.** Hold-to-resolution positions overlap in calendar time. Clustering is event × resolution week, but a
   market-wide resolution shock (oracle policy change, mass 50-50) would hit every carry together. The UMA/oracle regime
   can change (CH01-CH03 family risk).
7. **Snapshot window.** CB1-D dev is about 5.5 days, so day shocks cannot be clustered (jackknife binding).
   Replication is 3 weeks. Captures may need restoring from the archive if rotation lands first.
8. **h2 wear.** h2 has been read many times. PX1-PX4 and the pooled −7c resolution excess are known there, so A2, C and
   E screens on h2 are not naive. Only h5 replication and stage P count.
9. **Disk and calendar.** h5 uses about 0.63 GB of a host already near its cap date. If the archive rotation is
   delayed, the fetch may be paused by the pass guard (resumable).

## 7. Next actions

1. `science-reviewer` pass on §1 and §CB1-F (data design only), so the h5 fetch can start. Then delegate the backfill
   options, `ladders-fetch`, `seal`/`verify-seal` and tests to `implementer`, and commit q0016-q0018 (priority 61).
2. Delegate `creative_batch1.py` and `run_creative_batch1.py` with tests (§3). Run q0019 (h2 text + census, no
   outcomes) and insert the counts and MDEs.
3. Full `science-reviewer` pass on this file. Apply the required changes, then commit the declaration hash
   (`model_specs/cb1_v1.json`) = **CB1 freeze**. `T_rep_start` follows from it.
4. After q0018: commit the seal copy, amend the h4_seal exclude list (SB2 §1.2 text, collection parameter only), and
   commit q0020-q0023 (q0021 waits for q0003).
5. Results: ledger entries, batch Holm after all Stage-2 inputs exist, verdicts against §3 maps, dashboard. Commit q0027
   after 2026-11-09 and q0028 after 2027-01-07.

## Open questions for the reviewer

1. Is B3 (stage-P, declared before its data exist and run in parallel with the B1/B2 replication) acceptable, or must
   it wait for B1 to replicate? Calendar argument: the rungs resolve by year-end either way.
2. Are the declared tail and adverse-selection gates (CB1-A Wilson vs break-even; CB1-C PX1 drift vs half-spread) the
   right binding form, or should they be counted tests?
3. Design-weighted primaries (h2 weights derived from its manifest; h5 stored) against unweighted primaries for
   comparability with HB1/SB2.
4. Is the A1 24h post-end window (forced by h2's price window) acceptable, or should A1 be h5-only with a wider window
   (then without a screen)?
5. The `cb1` strata profile weights (crypto up/down × 0.25, non-sports × 1.5) and 7,000 markets: enough for the stated
   MDEs within the 0.8 GB budget?
6. Should CB1-D's payoff be the structural 1 (with an audit) or realised payouts only (fewer resolved events by the
   analysis date)?
