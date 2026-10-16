# Creative batch 1 (CB1): resolution carry, ladder NO carry, longshot ask-selling, neg-risk set asymmetry, genesis window

`evidence_role: exploratory_historical` (h2 screens, h5 replication) / `exploratory_dev` (snapshot development) /
`prospective` (stage-P parts declared here, data after the freeze) | status: **DRAFT design, not frozen; challenger round
1 required changes applied (response at the end; single response round, no further review loop).** Last updated
2026-10-15 21:24 UTC+1.

This file turns five ideas from `CREATIVE_HYPOTHESES_2026-10-15.md` (CH01, CH05, CH17, CH09, CH22) into declared,
falsifiable development tests, plus one new historical backfill (`h5_cb1`) for frozen replication and one small
incremental snapshot extractor.
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades; every P&L below is a paper rule at modelled or recorded prices.
- These are **economic (carry) hypotheses**. The primary quantity is **net P&L per share** at executable prices after
  fees and the relevant one-leg spread (plus its annualised form, the wrong-side tail and capacity), not R² or log loss.
  A mechanism test (does the mispricing exist at all) is labelled "mechanism" and is never read as profitability.
- Every test table becomes binding only when its declaration hash is committed (the CB1 freeze). Wording may be
  edited before then; after it, any change is a recorded deviation.
- Queue specs (§4) are drafts. None is committed to `queue/jobs/` by this document.

**Evidence ladder for every CB1 hypothesis.** Screen → independent replication with frozen definitions → only then a
prospective registration with an economic check at executable (recorded) prices. CH05 skips the screen because its
effect was already seen (§CB1-B). Forecasting improvement and profitability are kept separate.

## 0. Summary and ranking

Ranked by expected information per unit of calendar time (the network fetch and the snapshot calendar are the
bottlenecks, not CPU).

| Rank | Job | Hypothesis | Primary tests (≤ 3) | Screen data | Replication data | Queue ids | CPU-h (est.) | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 1 | **CB1-F** h5_cb1 backfill + seal; CB1 extractor | (data for A, B, C, D, E) | none (data jobs) | n/a | n/a | q0016, q0017, q0018, q0030; pass step | 0.5 CPU, 7-9 h wall (network) | 0.8 GB |
| 2 | **CB1-A** Decided-but-unresolved carry (CH01) | buy the 0.95-0.99 side after the scheduled end, hold to resolution | A1, A2 | `h2_main` | `h5_cb1` | q0019, q0020, q0024 | 1.5 | 1.5 GB |
| 3 | **CB1-D** Neg-risk set asymmetry (CH09) | sum of asks < 1 persists, sum of bids > 1 does not | D1 (mechanism), D2 | CB1 extract, captures before `T_dev_end` | CB1 extract, captures in `[T_rep_start, T_rep_end)` | q0022, q0027 | 0.3 + 0.5 | 1.0 GB |
| 4 | **CB1-B** Near-rung NO carry (CH05) | NO on the earliest live rung, hold to deadline | B1, B2 (mechanism), B3 (stage P) | none (effect already seen in IF-H2) | `h5_cb1_ladders` (pre-IF-H2 ladders); prospective rungs | q0023, q0028, q0029 | 0.5 | 1.0 GB |
| 5 | **CB1-C** Longshot ask-selling to resolution (CH17) | resting ask on the ≤ 0.10 side, hold to resolution | C1, C2 | `h2_main` + pmxt book table (q0003) | `h5_cb1` + h5 pmxt books (conditional build) | q0021, q0025, q0026 | 1.0 (+ 8-11 h book build) | 1.5 GB |
| 6 | **CB1-E** Genesis window (CH22) | NO on the affirmative side 24h after listing | E1, E2 (mechanism), E3 | `h2_main` (+ question text) | `h5_cb1` | q0019, q0020, q0024 | 1.0 | 1.5 GB |

**Why this order.**
- The h5 fetch is network-bound (about 85k requests at ≤ 4 rps, yielding to collector passes). It must be fetched and
  sealed before any CB1 screen result exists, so it starts first.
- The CB1 extractor must start now. Raw snapshots older than 8 days become deletable under the approved retention once
  the snapshot gate clears, and a 3-week raw replication window would not fit under the 12 GB cap.
- CB1-A has the largest population on existing data and the clearest mechanism (capital lock after the event).
- CB1-D runs on captures that are already collected; its replication window is calendar-bound (3 weeks after freeze).
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
| `history/h2_main` (3,200 sampled markets, 1,759 in the 2h panel; raw 10-min prices and trades for all sampled) | r0-r4 ML, HB1 (PX1-PX6, including PX3/PX4 resolution excess, the pooled -7c resolution-excess observation), surprise detector, SB2 J1/J3/J7 | **Screen** for CB1-A, CB1-C, CB1-E. Worn far beyond its revision budget: every CB1 result on it is labelled "beyond budget", L1 at most, disclosed in each results file | L1 |
| `history_sources/book_features` (pmxt, 6h grid, h2 panel pairs, outcome-0 token, 2026-04-13 to 08-10 minus 06-12..06-17) | ECONOMIC_CONDITIONS part B (h1 books), r4_book, SB2 J3 | CB1-C screen books (after q0003). Secondary real-book asks for CB1-A/E on the covered subset | L1 |
| `history/h5_cb1` (**new**, §CB1-F) | none | **Frozen-definition replication** for CB1-A, CB1-C (with h5 books) and CB1-E. Read only after the CB1 freeze, only for tests that advanced; every read logged | L2-dev |
| `history/h5_cb1_ladders` (**new**, §CB1-F) | none | **Frozen-definition replication** for CB1-B (B1, B2): ladders from events never walked by IF-H2 | L2-dev |
| `if_h2/` ladder universe and panel (1,432 ladders; 1,249 with panel rows) | IF-H2 r0 (null timing signal; descriptive -5.2c near-rung resolution excess) | **Exclusion list only** (event ids, rung ids). Not a CB1 screen: the -5.2c was already seen | none |
| `research_lab/cb1_extract/` (**new**, §2.11) | none | Compact per-capture tables (neg-risk member touches, near-rung state, post-end touches) cut from complete captures by the pass-step extractor. Sole input of CB1-D dev/rep and B3 | L1 (dev) / L2-dev (rep) / stage P |
| Complete-universe snapshots, sidecar, book sweeps, trade samples (raw) | E001-E007, E011 (live, scored after 2026-11-11), flow_screen, SB2 J4/J5 | Read only by the extractor (each new capture, plus a one-off backfill of dev captures from 2026-10-11T12:00Z) and by the CB1-A recorded-ask descriptive. Read-only; E011 inputs and analysis untouched; hypotheses differ | - |
| `history/h3_power` | HB1-R, h3_replication, SB2 J2/J6/J8 (reads 4-6) | **Not used.** Retired from replication use after SB2 (Ledger M3). No CB1 code path may open it; the runner refuses the run id | - |
| `history/h4_seal` (built ≥ 2026-11-16, `T_seal` 2026-10-22) | reserved for SB2 confirmation | **Not used by CB1. No change to its frozen parameters** (§1.3) | - |
| `history/h1_first` | pilot | Not used (only in `--exclude-runs`) | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T_draft` | 2026-10-15T20:00Z | First draft. No CB1 quantity has been computed on any dataset |
| `T_dev_end` | **2026-10-17T00:00Z** | Snapshot development uses captures with `capture_start_utc < T_dev_end` only. CB1-D dev starts at 2026-10-11T12:00Z (first sidecar capture), giving about 5.5 days and about 66 complete captures |
| `T_rep_start` | **max(2026-10-19T00:00Z, first complete capture ≥ CB1 freeze commit time + 2h)** | Replication and stage-P snapshot data begin here. Captures in `[T_dev_end, T_rep_start)` are extracted but unused by CB1 (buffer for review and freeze) |
| `T_rep_end` | **2026-11-09T00:00Z** | End of the CB1-D replication window (3 weeks, about 250 captures) |
| `T_fetch` | request clock of the h5 frame fetch (expected 2026-10-16/17) | h5 data end; recorded in the h5 manifest (`request_clock_now`). Necessarily before `T_seal` = 2026-10-22 |
| `T_censor` | `T_fetch` (h5) / h2 `request_clock_now` (h2) | Administrative censoring for hold-to-resolution rules |
| `T_rung_out` | **2027-01-07T00:00Z** | First outcome read for prospective CB1-B rungs (deadlines ≤ 2026-12-31) |
| `T_censor_B3` | **2027-01-31T00:00Z** | Final outcome read for B3. Rungs still unresolved then (UMA lag) are censored (§CB1-B) |

### 1.3 Sealed and untouched data (named)

- **SEALED-H5.**
  - `h5_cb1` and `h5_cb1_ladders` are fetched and sealed (manifest, per-file sha256 and listing sha256; §CB1-F)
    **before any CB1 screen job runs**.
  - The seal record is committed to the repo (`docs/research_lab/seals/h5_cb1_SEAL.json`, new path) before the first
    CB1 screen spec is committed.
  - Every CB1 h5 reader verifies the listing hash (refusing on mismatch) and appends to an access log
    (`history/h5_cb1*/ACCESS_LOG.jsonl`: UTC time, job id, git commit, files or globs read, declaration hash).
  - No CB1 job reads h5 outcome columns (`outcome_prices`, `uma_status`) before the CB1 freeze commit. The census
    (§2.9) reads nothing from h5.
- **SEALED-P (CB1).** Every snapshot, sweep, sidecar row, trade sample and extract row captured at or after
  `T_rep_start`. CB1-D replication and every stage-P test use only these, and only under a committed declaration.
- **h4_seal is unchanged.**
  - h5 holds no information after `T_fetch`, and `T_fetch` < `T_seal` = 2026-10-22. SEALED-H4 analyses use only
    origins ≥ `T_seal`.
  - A market may appear in both h5 (data up to `T_fetch`) and h4_seal (origins after `T_seal`). Their information sets
    are disjoint, so no frozen SB2 parameter changes.
  - Disclosed: such a market's identity and pre-`T_fetch` path were seen by CB1.

There is no unworn historical calendar left for the populations CB1 needs: h5 contains new markets on a partly new
calendar (lookback to 2025-07), not a new market regime. Confirmation needs SEALED-P.

## 2. Common rules for every CB1 job

### 2.1 Cost conventions (paper; `EXECUTION_COSTS.md`, `economics.py`)

| Item | Rule |
|---|---|
| Taker fee | `f(a) = r · a · (1 − a)` per share on each taker leg. **`r`:** the sidecar `fee_schedule` where a capture has it (snapshots ≥ 2026-10-11T12:00Z), with `fee_policy="conservative"` (max of schedule and docs). In history, the docs table by `fee_category`: crypto 0.07; sports, economics, culture, weather and other 0.05; finance, politics, mentions and tech 0.04; geopolitics 0; unknown or null 0.07. Current rates are applied to all past dates (conservative: fees were lower or absent earlier). |
| Maker fee / rebate | Maker fee 0. Rebates are not counted in primary results; the rebate (category share of the counterparty fee, pro rata) is an optimistic secondary only. |
| Historical ask (no book) | `a_hat = p + h(p)`, with `p` the as-of series price of the side bought. Half-spread `h` by the side's price band (2026-10-11 sweep): < 0.05: 2.05c; 0.05-0.20: 1.50c; 0.20-0.80: 1.10c; 0.80-0.95: 1.50c; ≥ 0.95: 1.25c. Capped at 0.999. **Binding** cost sensitivity: `h + 0.75c` (the mean history-series vs pmxt-book gap). |
| Genesis ask (CB1-E only) | `h_gen(p) = max(h(p), 2.5c)` (early books are wide; IMDEA). |
| Recorded ask (snapshots) | Gamma `best_ask` of the side bought (outcome-1 ask = `1 − best_bid` of outcome 0). A book-sweep `best_ask` with `ask_size_1 ≥ 5` is the depth-checked variant where the token is sweep-eligible. |
| pmxt ask | `sw_best_ask` (outcome 0) or `1 − sw_best_bid` (outcome 1), two-sided state, both clocks ≤ t. |
| Payout `Y` | From Gamma `outcomePrices` of the closed market: 1, 0 or 0.5 (50-50). A closed market with a missing or unparseable outcome is excluded and counted; worst-case sensitivity counts it as the losing side. |
| Long carry P&L (one leg) | `net = Y_side − a − f(a)`; capital `K = a + f(a)`. |
| Short cheap side (maker) | `net = a_c − Y_c`; capital `K = 1 − a_c`; maker fee 0. |
| Full set (CB1-D) | `net = 1 − Σ_j (a_j + f(a_j))`; capital `K = Σ_j (a_j + f(a_j))`. |
| Censoring | A position still unresolved at `T_censor` is marked at the last as-of price of the side held minus `h` and minus the exit fee (long), or plus `h` (short cheap-side buy-back), and flagged. Origins are restricted to `t ≤ T_censor − 60d`, so censoring affects only positions open more than 60 days. Sensitivities: censored at 0 and at 1. |
| Hold days | `d = (resolution time − entry time)/86400`, where resolution time = Gamma `closed_time` (outcome side). It is used only to end the hold and for clustering, never as an anchor or a population condition. Floor `max(d, 1)`. |
| Annualised | Capital-time ratio `R_ann = 365 · Σ_i net_i / Σ_i K_i max(d_i, 1)`. Not risk-adjusted. |
| Capacity | Reported next to every `R_ann`: qualifying opportunities per week (units / calendar weeks spanned) × median executable depth (shares at the ask: pmxt or sweep `ask_size_1` where recorded, else "unknown"), plus the implied $ per week at the point estimate. |

### 2.2 Clocks and trade availability

- History price points are usable from stamp + 600 s (10-min fidelity) or stamp + 3600 s (hourly ladder series), at
  most 2h old (12h for hourly ladder series); otherwise there is no origin. Trades: venue `ts < t` for origin
  conditions.
- Origins are on fixed UTC grids (2h for CB1-A, 6h for CB1-B/C) or at fixed offsets from `created_at` (CB1-E).
  `created_at` and `end_at` are scheduled or creation facts. **No anchor uses `closed_time`.**
- Membership "open at t" is `created_at ≤ t < closed_time` (a fact observable at t).
- `end_at` is Gamma `endDate` at fetch time; it may have been edited (look-ahead risk, SB2 item 9). Declared
  sensitivity for any test that conditions on `end_at`: drop markets whose `closed_time` is more than 30 days after
  `end_at`. The prospective snapshot `end_date` (stage P) is the clean version.
- pmxt events need both clocks ≤ t. Snapshot features come from the origin capture. Execution prices for latency tests
  come from the next capture, never the origin one.
- **Trade truncation (challenger item 1).**
  - Trades are fetched newest-first and capped (`history_backfill.py:13-14, 692-729`), so for a truncated market
    (`trades_truncated` true) nothing is known before `trades_oldest_ts`.
  - A trade condition over a window that starts before `trades_oldest_ts` in a truncated market is **known true** if
    the stored trades already satisfy it, and otherwise **unavailable** (never 0, as in the panel code at
    `:1269-1275`).
  - A unit whose condition is unavailable is excluded.
  - For "first qualifying origin" rules: if any earlier candidate origin of the market had an unavailable condition, the
    market is excluded, because its "first" cannot be determined.
  - Truncation depends on later trading volume (the future), so every job reports excluded units **by outcome `Y`**,
    with declared worst-case bounds per job (CB1-A, B, C, E).

### 2.3 Uncertainty

- Unit estimates are **unweighted** means (primary; §2.6). One-sided p = max(event-clustered CR1, two-way event ×
  resolution-week CR1), from the normal z of the intercept (HB1 `beta_test` rule). Resolution week = ISO week of
  `closed_time` (or of the censoring mark). Ladders: ladder event × deadline week. CB1-D: event × capture day.
- CI: 2,000-draw event-cluster percentile bootstrap (seed 116).
- **Testability.**
  - ≥ 30 event clusters and ≥ 100 units (origins, fills or triggers); otherwise "not testable" (p = 1, still counted).
  - Rare-loss carries (A, C) additionally need **≥ 10 losing event clusters** for the z-test to be used. Below that,
    only the exact bound in the next bullet decides.
- **Tail gate (challenger item 3b).** For carries whose loss is a rare event (A: favourite loses; C: longshot wins):
  - `π` = share of units on the losing side. Break-even `π* = 1 − mean(a + f)` (A) or `π* = mean(a_c)` (C).
  - The **upper** bound on `π` is one-sided at the stage's α (99% at Stage 1, 95% at Stage 2) and cluster-aware:
    Wilson on `n_eff = n / deff` (design effect from the event-cluster bootstrap of the losing share). When there are
    fewer than 10 losing event clusters, use the exact Clopper-Pearson bound on event-level losses (an event counts as
    losing if any of its units loses), with the event count as `n`.
  - A test may advance or pass only if the upper bound is `< π* − floor` (equivalently, net ≥ the floor at the
    tail-adverse bound).
  - "Killed in category": in a fee category with ≥ 100 markets, the one-sided **lower** bound on `π` (same α and
    construction) exceeds `π*`.
- Snapshot dev (≈ 5.5 days): day-level shocks cannot be clustered, so a leave-one-day-out jackknife is binding. Every
  leave-one-day-out estimate must keep the declared sign for a test to advance.
- **Sensitivity (reported, not binding):** frame-window clustering. The h2 and h5 frames sample (day × 15-minute slot)
  windows, so units are additionally clustered by frame window (PSU) as a two-way sensitivity.

### 2.4 Decision rule

- **Stage 1 (screen).** A test **advances** only if all of these hold:
  - (a) one-sided p < 0.01 in the declared economic direction (net > 0, or the declared mechanism sign);
  - (b) its point estimate meets the materiality floor in §2.5;
  - (c) for economic tests, the `R_ann` point estimate ≥ 10%;
  - (d) the tail gate (§2.3), where applicable;
  - (e) the binding robustness checks (§2.8).

  The cumulative BY label (q = 0.10, `battery2.cumulative_count()`) is attached as triage only.
- **Stage 2 (replication, frozen).** Holm at α = 0.05, one-sided, over **all CB1 tests that reach Stage 2** (advanced
  A/C/D/E tests plus B1 and B2, which enter directly). A pass also requires the same sign, the §2.5 floors met by the
  point estimate, the tail gate at 95% and the binding robustness checks. Only this is reported as
  "development-replicated" (L2-dev).
- **Stage P (prospective).** Declared per hypothesis in its own registration after Stage 2, except B3 (§CB1-B), which
  is declared here because its data only exist after the freeze. Stage P is the only path to a confirmation claim. It
  always includes the economic check at recorded asks.

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

- **Primary estimates are unweighted everywhere** (comparable with HB1/SB2).
- Design-weighted estimates are a declared secondary:
  - h5: stored `sample_weight`;
  - h2: weights derived from its manifest (`sample_report.strata` sizes over `allocation`: `N_s / n_s`), code
    `h2_design_weights()`;
  - snapshots and ladders: weight 1.
- Weighted and unweighted must agree in sign for any advance or pass (binding, §2.8).
- One unit per market (CB1-A, CB1-E), per rung (CB1-B), per (market, origin) order (CB1-C, with a market-equal-weight
  secondary), per event-capture or trigger (CB1-D).

### 2.7 Counting (M3 rule)

- Every primary test writes one `trials.jsonl` line via `provenance.append_trial`, with `evidence_role`, `revision`,
  `provenance.run_provenance`, the results-file `sha256_file` and `declaration_sha256`.
  - Kind `cb1_test` (screen), `cb1_replication` (Stage 2) or `cb1_prospective` (stage P).
- Each run also writes one `ml_explain` count line (`source: "creative_batch_1:<job>"`, `n_tests`), so both counters see
  it.
- New `KIND_RULES` entries in `battery2.py` (listed under code needed, §CB1-A):
  - `cb1_test`, `cb1_replication`, `cb1_prospective`: EXCLUDE ("per-test lines; counted by the n_tests of the matching
    `creative_batch_1:*` ml_explain line");
  - `cb1_descriptive`: EXCLUDE ("descriptive output, no inference, never used for a decision");
  - `history_seal_declaration`: EXCLUDE ("data seal; no test").
  - Unknown kinds still raise. A unit test runs the counter against the real `trials.jsonl`.
- Placebo lines carry `evidence_role: "placebo"` and count 0. The cumulative total at run time is recorded in each
  results file.

### 2.8 Placebos and robustness

- **Break-even placebo (every carry test: A1, A2, B1, B3, C1, C2, E1, E3; challenger item 3a).**
  - Replace `Y` by Bernoulli draws at break-even: long side `Y ~ Bern(min(a + f(a), 1))`; short cheap side
    `Y_c ~ Bern(a_c)`. Expected net is then exactly 0.
  - Rerun the full test (gate, floor, tail gate) over 200 draws. The advance rate must be **≤ 1.5%**, otherwise the
    test's inference is declared miscalibrated and it cannot advance.
  - This replaces the calibrated-price placebo, which could not fail, and the global permutation, which is not a null
    for mean tests (HB1 PX3/PX4 lesson).
- CB1-B: far-rung contrast (B2). CB1-C: filled vs unfilled orders (PX1 check). CB1-D: capture-order permutation within
  event (D2). CB1-E: sports genesis origins and mature origins (descriptive comparators).
- **Binding robustness for any advance or pass (challenger item 9):**
  - (i) the cost sensitivity `h + 0.75c` (recorded-ask tests: +0.75c on every bought leg) keeps net > 0;
  - (ii) the test still meets p < α and its floor without the top 5 events by absolute contribution;
  - (iii) weighted and unweighted estimates agree in sign.
- **Reported, not binding:**
  - sign by calendar month and by fee category (not binding: rare-tail carries flip sign in thin months by construction);
  - +1c cost;
  - worst-case outcome coding (50-50 and missing as losing);
  - censoring at 0 and at 1;
  - truncation worst-case bounds (§2.2);
  - real-book (pmxt) asks on the covered subset (A, E);
  - without IF-H2-universe rungs (A);
  - frame-window PSU clustering;
  - the `end_at` sensitivity.

### 2.9 Pre-freeze census (counts only)

- Before the freeze, q0019 computes on `h2_main` only: population counts, cluster counts and price-band histograms for
  A1, A2, E1, E2 and E3 (and the C1/C2 order counts once q0003 exists).
- Truncation exclusions are counted, but not by outcome.
- A guard drops the outcome columns (`outcome_prices`, `uma_status`) before the population code runs.
- Purpose: confirm testability and the MDEs below. The floors in §2.5 are not revised from the census.
- h5 is not opened before the freeze except to compute its seal.
- **The E3 text-rule hash (§CB1-E) is committed before q0019 reads any h2 question text.**

### 2.10 Compute and general stop rules

- Queue worker, one job at a time, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`.
- Priorities:
  - CB1 analysis jobs: ≤ 52 (below every SB2 job);
  - the h5 fetch and seal: 61 (above q0002's 60 so they slot between book chunks; below SB2's 67-72);
  - the one-off extractor backfill (q0030): 62 (it preserves data before possible deletion).
- 15 CPU-hour cap per family per batch. A job failing twice for the same non-transient reason stops and is recorded;
  gates and floors are never loosened.
- A null is reported with its MDE ("not detected at MDE x"), never as absence.
- No re-screen of a failed CB1 hypothesis on h2 or h5 with altered bands, floors, holds or populations.

### 2.11 Snapshot inputs: retention, disk and the CB1 extractor (challenger item 6)

**Problem.**
- Raw complete captures are about 67 MB each. Under the user-approved retention (`data_catalogue/RETENTION.md`;
  rules in `scripts/oracle/archive_retention.json`), host snapshots older than 8 days and sweeps older than 3 days are
  deletable once the snapshot gate clears, and only after a verified release copy exists.
- CB1-D rep on raw captures would need about 250 × 67 MB ≈ 17 GB, which exceeds the 12 GB host cap.

**Decision: a small incremental extractor.** New script `backend/scripts/run_cb1_extract.py` (module
`creative_batch1.extract`). On each run it appends, for every complete capture not yet extracted (idempotent by
`capture_id`), compact tables under `data-dumps/research_lab/cb1_extract/`:
- **`negrisk/<capture_id>.csv.gz`.** One row per member of every neg-risk event: `capture_id`, `capture_start_utc`,
  `received_utc`, `neg_risk_market_id`, `event_id`, `market_id`, `clob_token_id_0`, `best_bid`, `best_ask`, `spread`,
  `last_trade_price`, `closed`, `active`, `accepting_orders`, `neg_risk_other`, `event_neg_risk_augmented`,
  `volume_num`, `fee_schedule`, `fee_category`, `end_date`. The two sweeps of the same pass add `sw1_best_ask`,
  `sw1_ask_size_1`, `sw2_best_ask`, `sw2_ask_size_1` (blank if not swept).
- **`event_members.csv.gz`.** The event's full member count from Gamma `/events/{id}` (metadata only). Fetched once per
  new `neg_risk_market_id` and cached, refreshed weekly; at most 300 requests per run at 2 rps.
- **`rungs/<capture_id>.csv.gz`.** Only after the B3 rung list exists (q0029). For each listed rung: touch, `closed`,
  `accepting_orders`, `last_trade_price` and `end_date`.
- **`postend/<capture_id>.csv.gz`.** Markets with `end_date ≤ capture time`, not closed, and favourite touch price
  ≥ 0.95: touch, `last_trade_price`, `accepting_orders` and fee fields (CB1-A recorded-ask descriptive and its future
  stage P).
- **`manifest.json`.** Per capture: source capture sha256 (rows and rows_ext), row counts, extractor version and git
  commit, and the time of extraction.

Expected size: a few MB per day (about 0.1-0.2 GB over the batch).

**Host pass step.** Inserted in `scripts/oracle/arepo_pass.sh` inside the `if ... state=complete` block, as its last
line (after the E011 score line):

```
  timeout 600 nice -n 10 $PY scripts/run_cb1_extract.py --all-new --rps 2 --max-requests 300 2>&1 | tail -1 || true   # CB1 extract (CREATIVE_BATCH_1.md §2.11)
```

- It can never fail the pass: `|| true`, a 10-minute timeout (host owner's limit, with peak RSS ≤ 500 MB; the script
  self-limits below both), and the next steps (E004/E007 status) run regardless.
- It reads only captures already written; it never touches E011's or any frozen experiment's inputs.
- **Backfill now:** q0030 runs `run_cb1_extract.py --backfill-from 2026-10-11T12:00Z` once on the captures already
  present, before any deletion can affect them.

**Reader rules.**
- Every CB1 snapshot or extract reader takes `--snapshot-root`, `--sweep-root` and `--extract-root` (as the leadlag,
  bounce and flow_screen runners do since a9aa07a).
- It fails loudly on a listed but missing file.
- It reads a **frozen capture-id list with sha256**:
  - the dev list is written by q0030 for captures already present, completed at the first run after `T_dev_end`, and
    committed before q0022 runs;
  - the rep list is written at `T_rep_end` and committed before q0027 runs.
- Captures missing from the extract (pass skipped, extractor timed out) are counted, never silently dropped. They may be
  re-extracted from the archive release if the release copy exists.

**Retention gate note (stated here only; `RETENTION.md` is owned by another session).**
- CB1 needs raw snapshots only until they have been extracted. The CB1 readers of raw captures are:
  - `run_cb1_extract.py` (new captures each pass; q0030 backfill from 2026-10-11T12:00Z);
  - the CB1-A recorded-ask descriptive (dev window, via the extract).
- Once q0030 is done, CB1 places no requirement on the deferred `snapshots/` and `book_sweeps/` rules, provided each
  pass's extractor runs before the 3-day sweep and 8-day snapshot deletion ages, which it does by construction.

---

## 3. Jobs

### CB1-A: Decided-but-unresolved carry (CH01)

**Question.** After a market's scheduled end, while it still trades at 0.95-0.99 awaiting resolution, does buying the
favoured side at the ask and holding to redemption earn more than the wrong-side tail plus costs, at a rate worth the
locked capital?

**Redesign for causality.** The creative draft's population ("first time ≥ 0.97 at least 2h before `closed_time`")
conditions on the future close. CB1 replaces it:
- **Origins.** Origins are on the fixed 2h UTC grid. "Decided-but-unresolved" is defined by scheduled and past facts
  only: the scheduled end has passed (`t ≥ end_at`) and the market kept trading after it (≥ 1 trade in
  `[end_at, t)`).
- **Unit.** The first qualifying origin per market, found by scanning forward from listing. The wait to resolution is
  measured forward from `t` and is never used to select.
- **Active markets** are in both frames (h2 and h5), so the population is not conditioned on having resolved.
  Unresolved positions are censored (§2.1).
- **Window.** A1 uses `t ∈ [end_at, end_at + 24h)`. This is forced by h2's price series, which ends at
  `min(close, end_at) + 1d` (`history_backfill.price_window`). h5 fetches past it (§CB1-F), but the same 24h window is
  kept so the definitions are identical.
- **A2 scheduled life.** A2 is restricted to scheduled life `end_at − created_at ≤ 100 days` (the same rule as E;
  challenger item 2). Then the 120-day price window covers the whole pre-end life whatever the close, so A2's origins no
  longer depend on `closed_time` through `price_window` (`:643-658`).
- **Sports.** Sports are excluded from A1's primary (optional item adopted). Sports `end_at` is game time, so in-play
  trading is not "decided". Sports A1 is reported separately (descriptive, `cb1_descriptive`).

**Why new / overlap.**
- PX4 (resolution excess at mid ≥ 0.85, not significant, 61 judgement events) and PX2 (favourite 24h drift; replicated on
  h2, not on h3) are mid-based, not executable, have no hold rule and do not use the scheduled end. C1 is descriptive
  (0.994 priced → 1.000 realised at 1d).
- HB1's incidental pooled -7c resolution excess on resolved traded h2 rows was seen. It concerns all price levels and
  is not a CB1 population, but A2 overlaps PX4's region. Disclosed.
- Near-certain IF-H2 ladder rungs can enter A2 (deadline markets near their end). Robustness check (reported): without
  IF-H2-universe rungs.

**Data.**
- Screen: `h2_main` raw `prices/<id>.csv.gz` (token 0, 10-min fidelity) and `trades/<id>.csv.gz` for all 3,200 sampled
  markets (not the 2h panel, whose origins stop at 0.98). Frame columns used: `end_at`, `closed_time`, `created_at`,
  `fee_category`, `event_id`, `outcome_prices`, `status`, `trades_truncated`, `trades_oldest_ts`.
- Replication: the same files in `h5_cb1`.
- Stage P: CB1 extract `postend/` tables ≥ `T_rep_start` (Gamma touch, `end_date`, `accepting_orders`, `fee_schedule`),
  plus Gamma outcomes.

**Notation.**
- `p0` = as-of token-0 price. The favourite side `s` is token 0 if `p0 ≥ 0.5`, else token 1 with `p_s = 1 − p0`.
- `a = min(p_s + h(p_s), 0.999)` (h = 1.25c in the ≥ 0.95 band).
- Window and censoring as §2.1. Origins require `t ≤ T_censor − 60d`.
- Truncation as §2.2: an unavailable trade condition at the selected or any earlier candidate origin excludes the
  market.

| ID | Kind | Population (first qualifying 2h origin per market) | Hold | Statistic | Direction |
|---|---|---|---|---|---|
| **A1** | economic | `fee_category ≠ sports`; `end_at ≤ t < end_at + 24h`; open at t; `0.95 ≤ p_s ≤ 0.99`; ≥ 1 trade before `end_at`; ≥ 1 trade in `[end_at, t)` | to resolution (censored at `T_censor`) | mean `net = Y_s − a − f(a)` (cents/share) | > 0 |
| **A2** | economic | scheduled life `end_at − created_at ≤ 100d`; `end_at ≤ T_fetch + 400d`; `t < end_at − 24h`; open at t; `0.95 ≤ p_s ≤ 0.99`; ≥ 1 trade in `[t − 7d, t)` | to resolution (censored) | same | > 0 |

**Gates and declared checks.**
- **Tail gate (§2.3):** `π` = share with `Y_s = 0` (50-50 reported separately); `π* = 1 − mean(a + f)`; one-sided upper
  bound at the stage's α must be `< π* − 0.003`. "Killed in category" by the one-sided lower bound.
- **Testability:** at least 10 losing event clusters for the z-test; otherwise the exact bound alone decides.
- **Truncation worst case:** excluded markets are reported by outcome (`Y_s` = 1, 0, 0.5, unresolved). Bound: A1 and
  A2 recomputed with every excluded market added as a loser at its own ask (or at the median ask if no origin can be
  formed). This is reported; if the bound flips the sign, the verdict carries "truncation-sensitive".
- **Wait distribution:** median and p90 of `d`, the censored share, and a Kaplan-Meier curve for the wait.
- **Capacity** (§2.1).
- **Sub-band ≥ 0.97** (the creative's band): a sub-band reversal is reported, not tested.
- **Recorded-ask gap** (descriptive, from the dev extract `< T_dev_end`): for post-end markets, Gamma `best_ask` minus
  `last_trade_price + 1.25c`. This checks the historical `a_hat` and is logged as `cb1_descriptive`.

**Family, counting, MDE.**
- 2 tests (one `cb1_test` line each, plus the `ml_explain` line `creative_batch_1:A`); break-even placebo as placebo
  lines.
- MDE: the per-market `net` SD ≈ `sqrt(π(1 − π))` ≈ 12c at π = 1.5%.
  - h2: expected A1 n ≈ 200-400 non-sports markets (census to confirm), so SE ≈ 0.65c and Stage-1 MDE
    (z 2.33 + 0.84) ≈ **2.0c**. A2 n ≈ 500-800 after the life rule, MDE ≈ 1.4c.
  - h5 (7,000 markets): A1 n ≈ 900-1,300, SE ≈ 0.35c, Stage-2 MDE ≈ 0.9c (k = 1) to 1.2c (k = 11).
- The creative envelope (net ≈ 0.6c at a 1% tail) is **below every MDE**. Only a near-zero tail or a deeper discount can
  pass. A null means "not detected at MDE ≈ 2c (h2) / 1c (h5)".

**Verdict map.**
- **Development-replicated.** A1 or A2 advances and replicates (Holm, floors, tail gate, binding robustness) →
  "development-replicated carry (L2-dev)". Next: a stage-P registration on post-end extract markets with
  `accepting_orders = true`, at the recorded `best_ask` (sweep depth where eligible), with outcomes from Gamma, over at
  least 8 weeks.
- **Inconclusive.** A positive, significant mean that fails the tail gate → "inconclusive (tail not bounded)".
- **Killed in a category.** In any category with ≥ 100 markets where the tail lower bound exceeds `π*`.
- **Not detected.** No advance → "not detected at MDE". CH01 closes on history, with prospective measurement only.

**Compute.** One pass over 3,200 markets' prices and trades, about 25 min, 1.2 GB. Bootstrap 2 × 2,000 plus placebo
200 × 2, about 40 min. h5: about 1 h.

**Code needed.**
- `backend/astrolabe/research_lab/creative_batch1.py`:
  - `cost_model` (§2.1);
  - `trade_condition(trades, meta, window, k)` returning True, False or Unavailable (§2.2);
  - `favourite_origins(prices, trades, frame_row, rule)` returning the first qualifying origin per market, with
    truncation exclusion;
  - `carry_pnl(origin, outcome, close, censor)`;
  - `h2_design_weights(manifest)`;
  - `cluster_test(df, cluster_cols)` (max-of-two-ways rule plus bootstrap);
  - `tail_bound(losses, clusters, alpha, side)` (Wilson on `n/deff`, exact event-level fallback);
  - `breakeven_placebo`;
  - `capacity`;
  - `HYPOTHESES_CB1` and `declaration_sha256()` (covers every population, floor, gate, text rule and date in this file);
  - `log_trials`;
  - an outcome-column guard for census mode;
  - `h5_access_log(job, files)`.
- `battery2.KIND_RULES`: add `cb1_test`, `cb1_replication`, `cb1_prospective`, `cb1_descriptive` and
  `history_seal_declaration` (§2.7), with a test against the real `trials.jsonl`.
- Runner `backend/scripts/run_creative_batch1.py
  {h2-text,census,screen,replicate,ladders-fetch,rung-list,ladders,snapshots,seal,verify-seal} --family A|B|C|D|E`.
  - It refuses `--run-id h3_power`.
  - The **declaration-hash guard** (the committed `model_specs/cb1_v1.json` hash must equal the code's) applies to
    `screen`, `replicate`, `ladders` (q0023 and B3) and `snapshots --window dev|rep`.
  - h5 readers call `verify-seal` and append to the access log.
  - Results files are never overwritten.

**Tests** (`backend/tests/unit/test_research_lab_creative_batch1.py`):
- The first qualifying origin uses only data ≤ t. A planted post-t price spike does not move it, and `closed_time`
  changes do not change origin selection except through "open at t".
- A truncated market with t before `trades_oldest_ts` gives Unavailable (not 0), and an earlier unavailable candidate
  excludes the market.
- Price-point lag of 600 s.
- Censoring marks at the last as-of price and flags the row.
- The fee and half-spread tables match `economics.py`.
- `R_ann` ratio arithmetic on a fixture.
- Break-even placebo data give an advance rate of about 1% or less (smoke).
- The tail bound gives a correct Clopper-Pearson value on a fixture.
- The census guard rejects outcome columns.
- The access log is appended on every h5 read.

**Stop rule.** No A test advances → no h5 read for A.

### CB1-B: Near-rung NO carry on deadline ladders (CH05)

**Question.** Does buying NO on the earliest live rung of a "by date" ladder and holding to its deadline earn the
near-rung YES overpricing after costs, on ladders IF-H2 never saw?

**Why no screen.** IF-H2 r0 reported, descriptively, payout − `v1` = −5.2c [−6.3, −4.1] for closed near rungs. Any
test on IF-H2's own rungs would re-read the observation that generated the hypothesis. CB1-B goes straight to
replication on ladder-disjoint data:
- **R1 (historical):** `h5_cb1_ladders`, events with Gamma `start_date` 2024-01-01 to 2025-05-31. IF-H2 walked
  2025-06-01 onwards, so these ladders were never grouped by IF-H2. Guard: drop any ladder whose event id or any rung
  id is in the IF-H2 universe, or any of whose rungs is in the h1/h2/h3 samples.
- **R2 (prospective, stage P):** rungs of ladders from a Gamma `/events` walk (metadata only, start date 2024-01-01 to
  `T_rep_start`) whose deadline falls in `[T_rep_start + 2d, 2026-12-31]`.
  - The rung list is produced by q0029 at `T_rep_start`, before any of its outcomes exist.
  - Its sha256 is committed to the repo (`docs/research_lab/seals/cb1_b3_rung_list.json`) before the extractor starts
    recording rung state.
  - Ladders listed after `T_rep_start` are not added.

**Overlap.** IF-H2 (timing signal null; the resolution-excess line is the seed), TI4 (longshot decay near scheduled
end, null, ladders untestable on h2), PX3 (longshots, null), CH06 (level residual; not tested here).

**Data.**
- R1: `ladder-grouper-v1` unchanged (`if_h2.group_ladders`, deadline parse, stem rule, single-event ladders, no neg-risk
  month buckets).
  - Rung prices: hourly fidelity in 14-day windows (IF-H2 parity).
  - Data API trades per rung (new: IF-H2 had none), with the truncation flags.
  - Gamma `outcomePrices`, `closed_time` and `fee_category` per rung.
- R2: CB1 extract `rungs/` tables from captures ≥ `T_rep_start`, plus Gamma outcomes read at `T_rung_out` and re-read
  daily until `T_censor_B3`.

**Population (both R1 and R2).** At origin t (6h grid for R1; each complete extracted capture for R2):
- The near rung is the earliest-deadline rung with ≥ 2 days to its deadline, open at t.
- `0.05 ≤ v1 ≤ 0.60` and `v1 ≤ v2 + 0.01` (consistent ladder; IF-H2 rule).
- ≥ 1 trade on the near rung before t:
  - R1: stored trades, with the truncation rule of §2.2;
  - R2: `last_trade_price` present and sidecar `volume_num > 0`.
- **Unit:** the first eligible origin per rung (one origin per rung), held to the rung's resolution.
- NO price `n1 = 1 − v1`.
  - R1 ask: `a_NO = min(n1 + max(h(n1), 1c), 0.999)`.
  - R2 ask: `a_NO = 1 − best_bid` (recorded), with sweep depth as the depth-checked variant.

| ID | Kind | Data | Statistic | Direction |
|---|---|---|---|---|
| **B1** | economic | R1, all eligible near rungs | mean `net = Y_NO − a_NO − f(a_NO)` per share | > 0 |
| **B2** | mechanism (far-rung contrast) | R1, origins of B1 where the far rung (next deadline) is valid (`0.02 ≤ v2 ≤ 0.97`, trade before t) | paired mean `net_near − net_far` (the far rung's NO bought at the same origin, held to its own resolution) | > 0 |
| **B3** | economic, **stage P** (declared now; data after freeze) | R2 | mean `net` per share at the recorded ask | > 0 |

**B3 censoring (challenger item 7).**
- `T_censor_B3` = 2027-01-31T00:00Z. A rung whose deadline has passed but which is still unresolved then (UMA lag,
  dispute) is censored.
- Censored rungs are valued at the last extracted NO bid (`1 − best_ask` of YES) and flagged. Sensitivities value them
  at 0 (NO loses) and at 1.
- If more than 10% of B3 rungs are censored, the B3 verdict carries "resolution-lag sensitive".

**B3 secondaries.**
- B3 without IF-H2-universe ladders, i.e. only ladders whose event `start_date` is outside [2025-06-01, 2026-10-10].
- The depth-checked variant.

**Truncation worst case (R1).** Excluded rungs are reported by outcome. Bound: B1 with every excluded rung added as a
NO loser at its ask.

**Listing-survivorship check (declared, gating).**
- At B3 analysis, re-walk Gamma `/events` for R2's start-date range. Report the share of R2 rungs (seen live in the
  extract) that the walk does not return, and their NO net against the returned rungs.
- If ≥ 10% are missing **and** the missing rungs' YES rate differs from the returned rungs' by more than 5 points, R1
  and IF-H2's −5.2c are labelled "listing-survivorship biased", and B1 cannot support a positive verdict on its own.
- Secondary for R1: the calendar-disjoint subset (origins before 2025-09-01, IF-H2's grid start).

**Family, counting, MDE.**
- B1 and B2 enter the CB1 Stage-2 Holm family directly (2 `cb1_replication` lines plus a count line).
- B3 is its own one-test stage-P family (one-sided α = 0.05; a `cb1_prospective` line plus a count line), analysed at
  `T_censor_B3`.
- MDE: the per-rung NO payout SD ≈ 40c at `v1` ≈ 0.2. Rungs within a ladder are correlated, so the effective n is about
  the number of ladders.
  - R1 expected 500-900 ladders (probe first, §CB1-F): SE ≈ 1.5c, so B1 MDE ≈ 3.7c (k = 1) to 5.2c (k = 11).
  - IF-H2's 5.2c gross gap is about 3.5c net after the NO-side half-spread and fee, so B1 has at best about 50% power
    for an effect of IF-H2's size.
  - R2 expected 300-500 ladders with near-rung deadlines by year-end: B3 MDE ≈ 5c.
- A null is "not detected at MDE ≈ 4-5c", which does not refute IF-H2's descriptive estimate.

**Verdict map.**
- B1 and B2 replicated, and B3 passes with a clean survivorship check → "near-rung NO carry prospectively supported,
  imminence-specific". This is the strongest CB1 outcome; an economic stage-P check is built in.
- B1 replicated, B2 not → "ladder YES overpricing, not imminence-specific". The far rung becomes an equal candidate and
  needs its own registration.
- B1 not replicated, B3 passes → "inconclusive" (the two disagree; no claim).
- B1 not replicated, B3 fails → CH05 closed. IF-H2's −5.2c stays a descriptive, survivorship-caveated observation.

**Compute.**
- R1 fetch: part of CB1-F (q0017). Analysis: about 20 min, 1.0 GB.
- q0029 (rung list): about 3,500 requests, 30 min.
- B3 analysis after `T_censor_B3`: about 15 min.

**Code needed** (`creative_batch1.py`):
- `ladders_fetch(...)`: `if_h2.discover` over a date range → `group_ladders` → exclusion guards → hourly prices, rung
  trades and truncation flags (resumable, request-capped, `--budget-min`).
- `near_rung_origins(...)` and `ladder_pnl(...)`.
- `rung_list(as_of)`: writes `rung_list.json` and its sha256.
- `prospective_rungs(extract, rung_list)`.
- `survivorship_check(...)`.

**Tests:**
- Near-rung selection never uses a rung's resolution: a planted early close of a later rung does not change the near
  rung before that close.
- The exclusion guards drop ladders sharing any id with IF-H2 or h1/h2/h3.
- Deadline parse parity with `if_h2` on fixtures.
- One origin per rung.
- The rung list is immutable after its hash is written (a re-run refuses).
- Censoring at `T_censor_B3`.

**Stop rule.** If the R1 probe (§CB1-F) shows fewer than 300 usable ladders, B1 and B2 are recorded as "not testable"
(counted, p = 1), and CH05 rests on B3 alone.

### CB1-C: Longshot ask-selling held to resolution (CH17)

**Question.** Does a resting ask at the touch on the ≤ 0.10 side, filled by lottery buyers and held to resolution,
earn the captured half-spread (plus any favourite-longshot premium) net of adverse selection?

**Overlap.**
- PX1 is the main threat: longshot rows drift **up** +0.48c over 24h (replicated on h3 at +0.73c). If that drift is
  information, the resting seller is adversely selected.
- PX3 (resolution excess −2.2c, not significant) and PX6.
- ECONOMIC_CONDITIONS part B: signal-driven passive orders on h1 books lost 1-7c to adverse selection over 2h exits.
- New here: no signal (unconditional liquidity provision), the cheap side only, and hold to resolution (no exit leg).

**Data.**
- Screen: the q0003 pmxt table for `h2_main` (6h grid, panel pairs, so the token-0 price is in [0.02, 0.98]),
  `h2_main` trades for fills (with truncation flags) and Gamma outcomes. **Depends on q0003.**
- Replication: h5, decided below.

**Replication decision.** CB1-C replicates on **h5_cb1 with a pmxt book build restricted to CB1-C-eligible pairs**. The
build runs only if C1 or C2 advances.
- Cost: about 450 6h origins in the pmxt window at about 60-90 s each (h1 measured 94 s and 540 MB streamed per
  origin). That is **8-11 h** of nice-19 runtime in 150-minute chunks and about 150-250 GB streamed (ingress, not
  stored). 1.5 GB RAM; the output is under 10 MB.
- Why not prospective only: current collection cannot detect prospective fills. Trade samples cover 2,000 markets for
  one hour per 2h pass, so the queue position over a 6h order life cannot be reconstructed. Longshot resolutions also
  take weeks to months.
- A prospective stage P therefore needs a collector extension (continuous trades for a sampled set of longshot markets
  plus their sweep books), designed only after Stage 2.

**Order rule.** At each 6h origin t with a two-sided book (both clocks ≤ t):
- **Eligibility.**
  - The longshot side `c` is token 0 if `p0 ≤ 0.5`, else token 1. Its mid `m_c` is in [0.02, 0.10].
  - ≥ 1 trade in `[t − 7d, t)` (§2.2 truncation rule).
  - `t ≤ T_censor − 60d`.
- **Order.** A 5-share ask resting at `a_c`, the longshot's best ask (token 0: `sw_best_ask`; token 1:
  `1 − sw_best_bid`).
  - Queue ahead `Q0` = the displayed size at that level (`sw_ask_size_1`, or `sw_bid_size_1` for token 1).
  - Life `[t, t + 6h)`.
- **Fill (queue rule).** Cumulative taker volume buying side `c` at a price ≥ `a_c` within the life reaches `Q0 + 5`.
  - Buying `c` means a BUY of `c` at ≥ `a_c`, or a SELL of the other token at ≤ `1 − a_c` (data-API taker side).
  - All-or-nothing. The fill time is the completing trade's `ts`.
- **Untruncated trades** are required over the life (`trades_oldest_ts ≤ t`). An order whose life starts before
  `trades_oldest_ts` in a truncated market is excluded, counted by outcome, and enters the **worst-case bound as a
  filled loser** (`net = a_c − 1`).
- **P&L per filled share:** `net = a_c − Y_c`, `K = 1 − a_c`, held from fill to resolution.

| ID | Kind | Population | Statistic | Direction |
|---|---|---|---|---|
| **C1** | economic | filled orders, `fee_category ≠ sports` | unweighted mean net per filled share (market-equal-weight and design-weighted as secondaries) | > 0 |
| **C2** | economic | filled orders, `fee_category = sports` | same | > 0 |

**Tail gate and testability (§2.3).**
- `π` = share of filled orders whose longshot wins; `π* = mean(a_c)`. The upper bound must be `< π* − 0.005`.
- The z-test needs ≥ 10 winning-longshot event clusters; otherwise the exact event-level bound decides.

**PX1 adverse-selection check (declared, gating; decided by an upper bound, challenger item 8).** For C1 and C2:
1. Decomposition `net = (a_c − m_c) + (m_c − Y_c)`: captured half-spread plus resolution excess at the order mid.
2. `Δ_drift` = mean 24h post-fill drift `m_c(t_fill + 24h) − m_c(t)` of filled orders minus that of unfilled orders.
3. C1 recomputed separately for origins with prior-24h longshot change ≥ 0 and < 0 (reported).

**"PX1 clean" is an absence verdict, so it needs a bound.**
- The upper one-sided bound of `Δ_drift` must be **below** the mean captured half-spread `mean(a_c − m_c)` of filled
  orders. The bound is the hull of the bootstrap 95% upper limit and `Δ̂ + z · max SE` (z = 2.33 at Stage 1, 1.645 at
  Stage 2; max over event-clustered and two-way SE), as in SB2 freeze fix 2.
- Otherwise the verdict is capped at "inconclusive: adverse selection not excluded", even if C1 passes.

Also reported (secondary): the touch and through fill rules, the net per attempted order (fill rate × net), the
rebate-optimistic variant, and capacity (fills per week × 5 shares, and the depth at the touch).

**Family, counting, MDE.**
- 2 tests (`cb1_test` plus the count line `creative_batch_1:C`); break-even placebo.
- h2 expectation: orders ≈ 4-6k; queue fills ≈ 300-550 in ≈ 100-200 events. The per-fill SD is ≈ 22c at a 5% win
  rate, so SE ≈ 1.8c and the Stage-1 **MDE ≈ 5.7c** (creative envelope +2c).
- h5 (about 3× the pmxt-window markets): MDE ≈ 3.3c.
- CB1-C can detect only a large premium. A null is "not detected at MDE ≈ 6c".

**Verdict map.**
- C1 replicated with the PX1 check clean → "development-replicated passive longshot carry (L2-dev)". Stage P needs the
  collector extension (a separate design with a user-visible cost).
- C2 only → the same for sports; the category-scope decision stays open (user).
- Neither advances → CH17 closed on history at MDE.

**Code needed:**
- `creative_batch1.longshot_orders(book_rows, trades, frame)` and `queue_fill(...)` (reuse the `econ_conditions_maker`
  fill logic and outcome-0 conversion).
- `px1_bound(...)`.
- `run_history_features.py books --run-id h5_cb1 --pair-filter cb1_longshot` (needs `backfill_history.py panel
  --run-id h5_cb1` first).

**Tests:**
- The queue rule needs `Q0 + 5`; a print below `a_c` never fills.
- Token-1 mirroring.
- A truncated-trades window gives an excluded order that enters the worst-case bound as a filled loser.
- Post-fill drift uses only `t_fill + 24h` points.
- The PX1 bound is the hull of the two constructions.

**Stop rule.** No C advance → no h5 book build (saves 8-11 h).

### CB1-D: Asymmetric neg-risk deviations (CH09)

**Question (mechanism).** Because "sum of YES bids > 1" is instantly arbitrageable by conversion while "sum of YES asks
< 1" pays only at resolution, is the under-priced state more common than the over-priced one?

**Question (economic).** Is the under-priced set still buyable at a profit about 2h after it is observed?

**Overlap.**
- E005/XM1/XM2 (mid-sum deviation as a drift predictor: not supported), L3 (negligible R²) and SB2 J5 (lead-lag on the
  same captures).
- None of them used touch-level `Σ ask` vs `Σ bid`, asymmetry, fees or a set purchase.
- E011 shares the source captures; CB1 reads them only through the extract, and E011's analysis is untouched.

**Data.** CB1 extract `negrisk/` and `event_members` tables (§2.11).
- **Dev:** captures in `[2026-10-11T12:00Z, T_dev_end)`, ≈ 66 captures, backfilled by q0030 from raw captures still on
  the host.
- **Rep:** captures in `[T_rep_start, T_rep_end)`, ≈ 250 captures.
- Both read frozen capture-id lists with sha256; missing captures are counted.

**Event-capture eligibility (challenger item 4).** Group rows by `neg_risk_market_id` within a capture.
- `event_neg_risk_augmented` is false, and `neg_risk_other` is false for all members.
- **Member completeness.** The visible member count (open plus resolved members in the capture) must equal the event's
  member count from `event_members` (Gamma event metadata).
- **Every unresolved member must be open:** `closed` false, `active` true and `accepting_orders` true. An event is
  **ineligible** if any member is closed without final `outcomePrices` at c, `active = false`, or
  `accepting_orders = false`.
- Members resolved NO (closed, final outcome 0) are excluded from the sums, contributing 0. An event with a member
  resolved YES is ineligible.
- 2-25 open members, each with `0 < best_bid < best_ask < 1` and sidecar `volume_num > 0`.

**Definitions.**
- `S_ask = Σ_j ask_j − 1` and `S_bid = Σ_j bid_j − 1`; `U = 1[S_ask ≤ −0.02]` and `O = 1[S_bid ≥ +0.02]`.
- Set cost with fees `C = Σ_j (ask_j + f(ask_j))`, with `r` from each member's sidecar schedule (conservative policy).
- **Trigger** at capture c: `C(c) ≤ 0.995`.
- **Execution** at the next complete capture c' with a gap in [1.5, 3] h:
  - `C_exec = C(c')`, provided membership is unchanged and every member is still eligible;
  - otherwise no trade (net 0, kept in the denominator).
- **P&L:** `net = 1 − C_exec` per trigger, using the structural payoff of 1 per complete set. `R_ann` uses the event's
  scheduled `end_date` at c as the hold.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **D1** | mechanism | eligible event-capture | mean of `U − O` (difference in incidence) | > 0 |
| **D2** | economic | trigger | mean `net` per trigger (cents per $1 set), executed at the next capture | > 0 |

**Binding gates on D2 (in addition to §2.4).**
- **Realised payouts (challenger item 4).** On the subset of triggered events resolved by the analysis date, D2 is
  recomputed with realised payouts (sum over members of the final `outcomePrices`, per set). This version must have the
  **same sign** as the structural one.
- **Payout anomalies.** The share of resolved triggered events that are **not single-winner** (void, 50-50, no winner,
  multiple winners) must be **≤ 2%** (declared ceiling). If the resolved subset has fewer than 30 events, D2 is capped at
  "inconclusive (payoff unverified)".
- **Depth (challenger item 5).** Report the share of triggers for which every member has sweep data with
  `ask_size_1 ≥ 5`. On that subset, D2 is recomputed at sweep asks (execution at the next pass's first sweep) and must
  agree in sign. If the depth-checked subset has fewer than 30 event clusters, D2 is capped at "inconclusive (depth
  unverified)".

Declared extras (not counted; `cb1_descriptive`):
- persistence half-lives of `U` and `O` runs;
- incidence by fee category (the creative's ordering prediction crypto > sports > politics > geopolitics);
- capacity (triggers per week × the minimum member depth).

**Placebo.** D2 with the next-capture prices replaced by those of a random other capture of the same event
(capture-order permutation within event, 200 draws). There is no persistence, so mean net ≤ 0 and nothing advances.

**Family, counting, MDE.**
- Dev: 2 tests (`cb1_test` plus the count line `creative_batch_1:D`). Rep: advanced tests only (`cb1_replication`).
- Leave-one-day-out sign agreement is binding in dev.
- D1: about 500-800 eligible events with per-event incidence SD ≈ 0.1, so MDE ≈ 1.3 pp (dev) and ≈ 0.8 pp (rep).
- D2: per-trigger SD ≈ 3c in an expected 50-150 trigger events (dev), so MDE ≈ 1.0-1.3c (dev) and ≈ 0.6c (rep).
- If triggers come from fewer than 30 events, D2 is "not testable", and that is itself the economic answer: the state
  is too rare.

**Verdict map.**
- D1 only (replicated) → "asymmetry exists, not capturable at 2h latency". The maker route (resting bids on all members)
  needs continuous member trade capture (a collector extension; next structural batch).
- D2 replicated with all the gates above → a stage-P registration at sweep-checked depth over a later window
  (≥ 4 weeks), reporting capacity.
- Neither → CH09 closed at MDE.

**Compute.** Extract-based: dev about 10 min, rep about 30 min, under 1 GB. The extractor costs about 1-2 min per pass.

**Code needed:**
- `creative_batch1.extract` and `run_cb1_extract.py` (§2.11).
- `negrisk_event_captures(extract)`, `member_complete`, `set_cost`, `next_capture_pairs` (gap filter, as SB2 J5 item 11),
  `realised_set_payout` and `negrisk_tests`.
- Runner `snapshots --family D --window dev|rep`, with the declaration-hash guard. It refuses `rep` before `T_rep_end`,
  refuses captures outside the frozen list, and fails on a listed but missing file.

**Tests:**
- Augmented and "Other" events are excluded.
- A member that is closed without an outcome, inactive or not accepting orders makes the event ineligible.
- A member-count mismatch makes the event ineligible.
- A member missing an ask at c' gives no trade.
- Fees are summed per leg.
- The window guard rejects a capture at `T_dev_end`.
- The gap filter drops a 10h-outage pair.
- The extractor is idempotent by `capture_id` and a pass-step failure returns 0.

**Stop rule.** If D1 and D2 both fail dev, there is no rep run (the rep spec is not committed).

### CB1-E: Genesis window (CH22)

**Question.** In the first 24h after listing, is the affirmative (YES) side of non-sports questions overpriced enough
that buying NO at the ask and holding to resolution pays after costs?

**Overlap.**
- MS1 (market age → |move|, mature origins; it hurt out of sample) and PX1 (longshots drift up on mature markets; a
  different population).
- No AREPO panel has origins in the first day: the ML panel starts one day after the first price.
- The listing-period price points exist in h2 only for markets whose fetched window starts at listing (see the
  population rules).

**Data.**
- Screen: `h2_main` raw prices and trades, plus question text and outcome labels fetched for the 3,200 sampled markets
  (q0019; about 160 Gamma requests). h2 was not run in power mode, so it has no text.
- Replication: `h5_cb1` (text and outcomes stored; `--head-days 8` guarantees listing-period prices).
- **Disclosure:** question text is read at fetch time (h2 text at q0019, h5 at `T_fetch`). Polymarket edits descriptions
  and sometimes questions after listing, so the text may differ from what traders saw at t.

**Population.**
- `outcomes` = ["Yes", "No"]; YES is the "Yes" token. `fee_category ≠ sports`.
- **Scheduled life** `end_at − created_at ≤ 100 days`, and `end_at ≤ T_fetch + 400d` (frame completeness, challenger item
  11). Scheduled life is a scheduled fact: it makes h2's 120-day price window cover the listing for every included
  market whatever its actual close, so inclusion does not depend on early resolution.
- ≥ 3 trades in `[created_at, t)`. In a truncated market where `created_at` precedes `trades_oldest_ts` and the stored
  trades do not already show 3, the condition is unavailable and the market is excluded and counted by outcome (§2.2).
- Origin `t = created_at + 24h` (primary; +6h and +12h secondary). As-of YES price `p_Y ∈ [0.05, 0.80]`.
- Open at t; `t ≤ T_censor − 60d`.
- One unit per market.

**Pricing.** NO is bought at `a = min((1 − p_Y) + h_gen(1 − p_Y), 0.999)` and held to resolution (censored):
`net = Y_NO − a − f(a)`.

**Sensational rule (frozen; challenger item 12).** Applied to the question text only, both patterns required. The
declaration hash covers the exact pattern strings and flags below; the hash is committed before q0019 reads any h2 text.

```
NAME_RE = r"(?<=[a-z0-9,;:'\"\)]\s)[A-Z][a-zA-Z'\.\-]+(?:\s(?:[A-Z][a-zA-Z'\.\-]+))+"   # flags: none
VERB_RE = r"\b(arrest\w*|indict\w*|resign\w*|impeach\w*|invade[sd]?|invasion|attack\w*|strike[sd]?|assassinat\w*|convict\w*|jail\w*|prison\w*|fired|removed|ousted|coup|martial law|nuclear|war|collapse[sd]?|default\w*|crash\w*|hack\w*|sanction\w*|ban|bans|banned|die|dies|died|death|killed|out as)\b"   # flags: re.IGNORECASE
sensational(q) = bool(re.search(NAME_RE, q)) and bool(re.search(VERB_RE, q, re.IGNORECASE))
```

`NAME_RE` requires a capitalised run of at least two words preceded by a lowercase letter, digit or punctuation and a
space, so a capitalised word at the start of the question does not count. Known false positives (two-word capitalised
non-persons such as "Supreme Court") are accepted as part of the frozen rule.

| ID | Kind | Population | Statistic | Direction |
|---|---|---|---|---|
| **E1** | economic | all eligible non-sports Yes/No markets, origin +24h | unweighted mean `net` per NO share | > 0 |
| **E2** | mechanism | same | unweighted mean 7-day YES drift `p_Y(t + 7d) − p_Y(t)` (payout if closed earlier) | < 0 |
| **E3** | economic | E1 ∩ sensational | unweighted mean `net` | > 0 |

**Declared comparators (descriptive).**
- Sports Yes/No genesis origins (expected null).
- The same markets at age ≥ 30 days (mature drift; survivorship disclosed).
- PX1/PX2 levels.

**Truncation worst case.** Excluded markets are reported by outcome. Bound: E1 and E3 with every excluded market added
as a NO loser at its ask.

**Declared robustness (reported; the creative's kill test).** On the pmxt-covered subset, replace `p_Y` and `a` by the
first two-sided book at or after the origin (≤ 1h). If E1 or E2 loses sign there → "artefact of the first-trade price".

**Family, counting, MDE.**
- 3 tests (`cb1_test` plus the count line `creative_batch_1:E`); break-even placebo for E1 and E3.
- h2: ≈ 200-400 eligible markets. E1 SE ≈ 2.3c, so the Stage-1 **MDE ≈ 7c** (envelope 3-5c gross, about 1-2c net).
  E2 SD ≈ 8c, so its MDE ≈ 1.5c.
- h5 (non-sports weighted ×1.5 in sampling): E1 n ≈ 800-1,200, MDE ≈ 3.5-4.5c.
- E2 is the realistic h2 detection target; E1 on h2 can catch only a large effect.

**Verdict map.**
- E1 (or E3) replicated with the binding robustness → "development-replicated genesis carry". Stage P on new listings
  in the extract (a new-listing table is to be added to the extractor at registration), at recorded asks, over at least
  8 weeks.
- E2 replicated, E1 not → "genesis overpricing exists, not tradable after costs at MDE" (a forecasting-side fact, not
  profit).
- None → CH22 closed at MDE.

**Code needed:**
- `creative_batch1.h2_text_fetch`: Gamma `/markets?id=` in batches of 20, metadata only, written to
  `h2_main/cb1/text.csv.gz`.
- `genesis_origins`, `sensational()` (patterns above, hash in the declaration) and `drift_7d`.

**Tests:**
- The scheduled-life rule uses `end_at` and `created_at` only.
- A trade at `t + 1s` does not count.
- A truncated market before `trades_oldest_ts` is unavailable.
- `sensational()` gives the frozen fixture outputs, including the sentence-start exclusion.
- The genesis half-spread floor is 2.5c.

**Stop rule.** No E advance → no h5 read for E.

### CB1-F: The `h5_cb1` and `h5_cb1_ladders` backfills, and the seal

**Purpose.** Market-disjoint historical replication data for CB1-A, CB1-C and CB1-E (`h5_cb1`), and ladder-disjoint
data for CB1-B (`h5_cb1_ladders`). Both are fetched and sealed before any CB1 screen result exists.

**h5_cb1 (markets).** Final command (new options marked *):

```
python scripts/backfill_history.py run --run-id h5_cb1 --seed arepo-h5-cb1 \
  --exclude-runs h1_first,h2_main,h3_power --n-markets 7000 --lookback-days 450 \
  --closed-future-days 400* --pages-per-window 20* --strata-profile cb1* --max-days 120 \
  --head-days 8* --price-end close_or_end_max* --max-trades 10000 --rps 4 --anchored-live-check \
  --disk-cap-gb 0.62 --budget-scope run --checkpoint-every 200 --budget-min 150*
```

**Frame.** `frame-v2-random-windows`, 6 random 15-minute windows per day.
- Closed markets by `end_date`, over the last 450 days **and the next 400 days** (`--closed-future-days`). Without the
  forward walk, markets resolved early with a future `endDate` are absent, which would bias A2 and any early-YES rung.
- Active markets by `start_date` over the last 450 days.
- **Capped windows (challenger item 11).** `fetch_frame` keeps only the lowest ids of a capped window (`:393-394`), and
  `inclusion_prob` ignores this.
  - `--pages-per-window 20` reads up to 2,000 rows per window, the Gamma offset cap.
  - **A window that still caps is excluded entirely** (all its rows are dropped before sampling) and counted per kind
    and day in the frame report.
  - The inclusion probability then refers to the uncapped windows. Busy windows (mostly crypto bursts) are
    under-represented, which is disclosed with the excluded-window count.
- **Completeness rule.** CB1-A/E use only markets with `created_at ≥ T_fetch − 450d` and `end_at ≤ T_fetch + 400d`. For
  these the frame is complete up to the random-window sampling and the capped-window exclusion. A long-unresolved
  market created inside the lookback is in the active walk.

**Sample.** `--strata-profile cb1`: strata `status × topic × creation month` (as in power mode), with creation-known
weights:
- crypto "Up or Down" questions × 0.25 (they resolve automatically within minutes and dominate the frame);
- other non-sports × 1.5;
- sports × 1.0.
- Allocation is proportional over status. `inclusion_prob` and `sample_weight` are stored.
- **No price-, volume- or outcome-based oversampling.** Near-certain, longshot and ladder status are path or outcome
  attributes; using them would make inclusion depend on the path.
- Question, event title, slug, topic and **`outcomes`** (a new frame column) are stored.

**Prices.**
- `--price-end close_or_end_max`: the tail window ends at `max(close, end_at) + 1d`, so post-end waits are covered.
- `--head-days 8`: one extra window `[start, start + 8d]` when the tail window does not reach the listing.

**Trades.** Up to 10,000 per market (the API offset cap). `trades_truncated` and `trades_oldest_ts` are recorded per
market (they drive §2.2).

**Expected size and requests.**
- **Disk ≈ 0.53 GB** (cap 0.62 GB): 7,000 markets at ≈ 75 KB each (h2 was 202 MB for 3,200 markets at max-trades
  5,000).
- Frame: (450 + 400) days × 6 windows. ≈ 1.8 pages per uncapped closed window, plus up to 20 pages for windows that
  would have capped at 3 (≈ 23% of closed windows in h2), plus ≈ 3k for active. **≈ 24k requests.**
- Markets: ≈ 6 requests per market (3 price windows, 1 head window, 1.5 trade pages). **≈ 42k requests.**
- **≈ 66k requests in total.**

**h5_cb1_ladders.**
- Command: `run_creative_batch1.py ladders-fetch --run-id h5_cb1_ladders --start 2024-01-01 --end 2025-05-31
  --exclude-runs h1_first,h2_main,h3_power --exclude-ifh2 <if_h2 ladder file> --rps 4 --disk-cap-gb 0.15
  --budget-min 150`.
- Steps:
  1. Gamma `/events` walk by start date in 7-day windows (split while capped; tag 102127 excluded).
  2. `ladder-grouper-v1`.
  3. The exclusion guards (§CB1-B).
  4. Per rung: hourly prices over the rung's life (14-day windows), trades (≤ 10,000, with truncation flags) and
     outcome metadata.
- **Probe first:** 20 random 2024 rungs. If fewer than 80% return price points, stop and record (B1/B2 become not
  testable; CB1-B rests on B3).
- **Expected:** 500-900 ladders, ≈ 3,000 rungs, **≈ 19k requests** (≈ 1.5k walk, 12k price, 5k trade) and
  **≈ 0.1 GB**.

**Totals and cost.**
- **≈ 85k requests at ≤ 4 rps.** That is ≈ 5.9 h of request time and ≈ 7-9 h wall, including collector yields
  (`live_check`, about 18 minutes per 2h pass) and retries: 3-4 chunks of 150 minutes.
- **Disk ≈ 0.63 GB**, with hard caps of 0.62 + 0.15 = 0.77 GB (≤ the 0.8 GB budget).
- Host `data-dumps` is about 7 GB against the 12 GB cap and grows about 1 GB/day until snapshot deletion resumes under
  the approved retention, so h5 brings the cap date forward by about 0.7 days. The pass guard pauses collection rather
  than exceeding the cap, and the fetch is resumable.
- After the seal, h5 is archived to an `arepo-data` release by the existing process (owned by another session).
- RAM ≈ 0.6-0.8 GB. CPU use is low (network-bound).

**Seal (q0018).** `run_creative_batch1.py seal --run-id h5_cb1,h5_cb1_ladders` writes `SEAL.json` in each run dir:
- sorted per-file sha256 and the listing sha256;
- file count and total bytes;
- the manifests' request clocks;
- the capped-window exclusion counts;
- the git commit and the seal time.

It appends one `history_seal_declaration` trial line and creates an empty `ACCESS_LOG.jsonl`. The coordinator commits a
copy as `docs/research_lab/seals/h5_cb1_SEAL.json` before any CB1 screen spec (q0020-q0022) is committed. Every h5
reader calls `verify-seal`.

**Ordering guarantee.**
- q0020-q0022 depend on q0018 in the queue.
- The runner's `screen` refuses to start unless the committed seal file exists.
- The h5 fetch parameters above are fixed by this document and contain nothing that depends on any CB1 result.

**Read rules.**
- h5 is read at most once per CB1 hypothesis family (CB1-A, CB1-C, CB1-E), with frozen definitions only, plus B1/B2 for
  the ladders.
- No discovery, and no re-estimation of bands, floors or rules on h5.
- Every read is logged in `ACCESS_LOG.jsonl`. After CB1, h5's replication role is recorded in the ledger (one read per
  family).

**h4_seal.** Unchanged (§1.3): h5's data end at `T_fetch` < `T_seal`, so the two are information-disjoint without
changing a frozen SB2 parameter.

**Code needed** (`history_backfill.py`, `backfill_history.py`):
- `--closed-future-days N`: forward closed walk, same seeded window scheme.
- `--pages-per-window N`: passed through to `fetch_frame`; capped windows are dropped entirely and counted.
- `--strata-profile cb1`: the weights above; implies text columns.
- The `outcomes` frame column.
- `--head-days`.
- `--price-end {min,close_or_end_max}`: the default `min` keeps h1-h3 behaviour.
- `--budget-min`: a wall-clock stop between markets; resumable; exits 0 with "budget reached".

Tests:
- The forward walk uses the same seeded windows.
- A capped window is dropped and counted, and no row from it enters the sample.
- The `cb1` weights are creation-known (no volume or outcome field is read).
- `head_days` adds exactly one window.
- `close_or_end_max` extends only closed markets.
- `--budget-min` stops cleanly and resumes.
- Seal and verify-seal round-trip; a modified file fails verification.
- The access log is appended on read.

---

## 4. Draft queue specs

Paths follow `queue/README.md`: `argv[0]` is under `backend/scripts/`, and `cwd` is `backend`.
- **No spec may be committed until its code and tests exist.** Test jobs also need the reviewed CB1 freeze commit.
- q0016-q0018 and q0030 need only their code.

```json
{"id": "q0016_h5_cb1_fetch", "title": "CB1-F: h5_cb1 market backfill (disjoint from h1/h2/h3; cb1 strata profile)",
 "family": "history_data", "priority": 61,
 "expected_value": "sealed replication data for CB1-A/C/E; calendar is the bottleneck",
 "data": ["public Gamma/CLOB/Data API"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api, clob, data-api"},
 "depends_on": [],
 "argv": ["scripts/backfill_history.py", "run", "--run-id", "h5_cb1", "--seed", "arepo-h5-cb1", "--exclude-runs", "h1_first,h2_main,h3_power", "--n-markets", "7000", "--lookback-days", "450", "--closed-future-days", "400", "--pages-per-window", "20", "--strata-profile", "cb1", "--max-days", "120", "--head-days", "8", "--price-end", "close_or_end_max", "--max-trades", "10000", "--rps", "4", "--anchored-live-check", "--disk-cap-gb", "0.62", "--budget-scope", "run", "--checkpoint-every", "200", "--budget-min", "150"],
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
{"id": "q0018_h5_cb1_seal", "title": "CB1-F: seal h5_cb1 + h5_cb1_ladders (per-file sha256, listing hash, trial line, access log)",
 "family": "history_data", "priority": 61, "expected_value": "fixes h5 before any CB1 screen result exists",
 "data": ["history/h5_cb1", "history/h5_cb1_ladders"], "resources": {"mem_mb": 300, "cpu": 1},
 "depends_on": ["q0016_h5_cb1_fetch", "q0017_h5_cb1_ladders_fetch"],
 "argv": ["scripts/run_creative_batch1.py", "seal", "--run-id", "h5_cb1,h5_cb1_ladders"],
 "timeout_s": 1800, "max_retries": 1, "outputs": ["history/h5_cb1*/SEAL.json", "history/h5_cb1*/ACCESS_LOG.jsonl", "trials.jsonl (1 history_seal_declaration)"],
 "next_action": "Claude session: commit docs/research_lab/seals/h5_cb1_SEAL.json; then commit q0020-q0022", "notes": ""}
```
```json
{"id": "q0030_cb1_extract_backfill", "title": "CB1: one-off extract of complete captures from 2026-10-11T12:00Z (before possible deletion)",
 "family": "creative_batch_1", "priority": 62, "expected_value": "preserves CB1-D dev inputs in MBs; writes the dev capture-id list",
 "data": ["research_lab/snapshots + rows_ext + book_sweeps present on host"], "resources": {"mem_mb": 1000, "cpu": 1, "network": "gamma-api (event member counts)"},
 "depends_on": [], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-11T12:00Z", "--rps", "2", "--max-requests", "3000"],
 "timeout_s": 7200, "max_retries": 2, "outputs": ["data-dumps/research_lab/cb1_extract/{negrisk,postend}/, event_members.csv.gz, manifest.json, capture_lists/dev.json"],
 "next_action": "pass step takes over (arepo_pass.sh line in CREATIVE_BATCH_1.md §2.11)", "notes": "idempotent by capture_id; read-only on snapshots; missing captures counted"}
```
```json
{"id": "q0019_cb1_h2_text_census", "title": "CB1: h2_main question/outcome text fetch + population census (no outcome columns)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "testability and MDEs before freeze",
 "data": ["history/h2_main (frame, prices, trades)", "Gamma /markets metadata"], "resources": {"mem_mb": 1500, "cpu": 1, "network": "gamma-api"},
 "depends_on": [], "argv": ["scripts/run_creative_batch1.py", "census", "--run-id", "h2_main", "--fetch-text", "--rps", "4"],
 "timeout_s": 5400, "max_retries": 2, "outputs": ["history/h2_main/cb1/{text.csv.gz,census.json}"],
 "next_action": "Claude session: insert census counts into CREATIVE_BATCH_1.md; freeze", "notes": "refuses unless the E3 text-rule hash is committed; outcome columns dropped by guard; floors not revised from census"}
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
{"id": "q0021_cb1_screen_h2_C", "title": "CB1-C: longshot ask-selling screen on h2_main pmxt books (C1, C2; PX1 bound)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "passive longshot carry screen",
 "data": ["history_sources/book_features/book_features.csv.gz (q0003)", "history/h2_main trades/frame"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0003_books_finalize", "q0018_h5_cb1_seal"],
 "argv": ["scripts/run_creative_batch1.py", "screen", "--run-id", "h2_main", "--family", "C", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["history/h2_main/cb1/results_cb1_C.json", "trials.jsonl"],
 "next_action": "if C advanced: q0025 then q0026", "notes": "declaration-hash guard"}
```
```json
{"id": "q0022_cb1_snap_dev_D", "title": "CB1-D: neg-risk asymmetry dev screen on extracted captures before T_dev_end (D1, D2)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "mechanism + 2h-latency set carry",
 "data": ["research_lab/cb1_extract (frozen dev capture list, 2026-10-11T12:00Z <= capture < 2026-10-17T00:00Z)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": ["q0018_h5_cb1_seal", "q0030_cb1_extract_backfill"],
 "argv": ["scripts/run_creative_batch1.py", "snapshots", "--family", "D", "--window", "dev", "--extract-root", "../data-dumps/research_lab/cb1_extract", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch1/D_dev/results.json", "trials.jsonl"],
 "next_action": "if advanced: commit q0027 spec after T_rep_end", "notes": "E011 untouched; leave-one-day-out binding; declaration-hash guard"}
```
```json
{"id": "q0023_cb1_ladders_B", "title": "CB1-B: frozen B1/B2 on h5_cb1_ladders (enter Stage-2 Holm directly)",
 "family": "creative_batch_1", "priority": 50, "expected_value": "near-rung NO carry on IF-H2-disjoint ladders",
 "data": ["history/h5_cb1_ladders (sealed)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": ["q0018_h5_cb1_seal"],
 "argv": ["scripts/run_creative_batch1.py", "ladders", "--run-id", "h5_cb1_ladders", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["history/h5_cb1_ladders/cb1/results_B.json", "trials.jsonl (2 cb1_replication + count)"],
 "next_action": "Claude session: hold p-values for the batch Holm (§2.4)", "notes": "verify-seal; access log; declaration-hash guard"}
```
```json
{"id": "q0024_cb1_replicate_h5_AE", "title": "CB1-A/E: frozen replication of advanced tests on h5_cb1",
 "family": "creative_batch_1", "priority": 50, "expected_value": "development replication (Holm over the CB1 Stage-2 set)",
 "data": ["history/h5_cb1 (sealed)", "results_cb1_AE.json"], "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0020_cb1_screen_h2_AE"],
 "argv": ["scripts/run_creative_batch1.py", "replicate", "--run-id", "h5_cb1", "--from", "h2_main", "--family", "A,E", "--n-boot", "2000"],
 "timeout_s": 10800, "max_retries": 1, "outputs": ["history/h5_cb1/cb1/results_cb1_AE_rep.json", "trials.jsonl"],
 "next_action": "Claude session: batch Holm, verdicts, ledger", "notes": "exits 0 'nothing advanced' if empty; verify-seal; access log"}
```
```json
{"id": "q0025_h5_books_C", "title": "CB1-C: h5_cb1 panel + pmxt books for CB1-C-eligible pairs (conditional)",
 "family": "creative_batch_1", "priority": 48, "expected_value": "enables C replication",
 "data": ["history/h5_cb1", "pmxt v2 hourly (range reads)"], "resources": {"mem_mb": 1500, "cpu": 1, "network": "r2v2.pmxt.dev"},
 "depends_on": ["q0021_cb1_screen_h2_C"],
 "argv": ["scripts/run_history_features.py", "books", "--run-id", "h5_cb1", "--pair-filter", "cb1_longshot", "--budget-min", "150"],
 "timeout_s": 16200, "max_retries": 3, "repeat": {"max_runs": 8, "until_log_regex": "\"pairs_done_total\": (\\d+), \"pairs_total\": \\1,"},
 "outputs": ["history_sources/book_features_h5_cb1/"], "next_action": "q0026", "notes": "exits 0 'skipped: no C advanced'; builds the h5 panel first; reads no outcomes; access log"}
```
```json
{"id": "q0026_cb1_replicate_h5_C", "title": "CB1-C: frozen replication on h5_cb1 books",
 "family": "creative_batch_1", "priority": 48, "expected_value": "C replication", "data": ["h5 books + trades"],
 "resources": {"mem_mb": 1500, "cpu": 1}, "depends_on": ["q0025_h5_books_C"],
 "argv": ["scripts/run_creative_batch1.py", "replicate", "--run-id", "h5_cb1", "--from", "h2_main", "--family", "C", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["history/h5_cb1/cb1/results_cb1_C_rep.json", "trials.jsonl"], "next_action": "batch Holm", "notes": "verify-seal; access log"}
```
```json
{"id": "q0027_cb1_snap_rep_D", "title": "CB1-D: frozen replication on extracted captures in [T_rep_start, T_rep_end)",
 "family": "creative_batch_1", "priority": 50, "expected_value": "D replication (prospective captures)",
 "data": ["research_lab/cb1_extract (frozen rep capture list)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": ["q0022_cb1_snap_dev_D"],
 "argv": ["scripts/run_creative_batch1.py", "snapshots", "--family", "D", "--window", "rep", "--extract-root", "../data-dumps/research_lab/cb1_extract", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch1/D_rep/results.json", "trials.jsonl"],
 "next_action": "batch Holm", "notes": "commit this spec only after 2026-11-09T00:00Z and after the rep capture list + sha256 are committed; runner refuses earlier; declaration-hash guard"}
```
```json
{"id": "q0029_cb1_b3_rung_list", "title": "CB1-B: freeze the B3 prospective rung list at T_rep_start (metadata only, no outcomes exist)",
 "family": "creative_batch_1", "priority": 52, "expected_value": "fixes R2 before any outcome; enables extractor rung tables",
 "data": ["Gamma /events walk 2024-01-01..T_rep_start (metadata)", "if_h2 ladder file (for the secondary flag)"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api"},
 "depends_on": [], "argv": ["scripts/run_creative_batch1.py", "rung-list", "--as-of", "T_rep_start", "--deadline-max", "2026-12-31", "--rps", "4"],
 "timeout_s": 5400, "max_retries": 2, "outputs": ["data-dumps/research_lab/cb1_extract/rung_list.json (+ .sha256)"],
 "next_action": "Claude session: commit docs/research_lab/seals/cb1_b3_rung_list.json (sha256) before the next pass extracts rungs", "notes": "commit this spec only after the CB1 freeze; refuses to overwrite an existing list"}
```
```json
{"id": "q0028_cb1_rungs_prospective_B3", "title": "CB1-B: B3 prospective rungs + listing-survivorship check",
 "family": "creative_batch_1", "priority": 50, "expected_value": "stage-P near-rung NO carry",
 "data": ["cb1_extract/rungs (frozen rung list, captures >= T_rep_start)", "Gamma events walk (metadata)", "Gamma outcomes"], "resources": {"mem_mb": 1000, "cpu": 1, "network": "gamma-api"},
 "depends_on": ["q0029_cb1_b3_rung_list"], "argv": ["scripts/run_creative_batch1.py", "ladders", "--prospective", "--extract-root", "../data-dumps/research_lab/cb1_extract", "--rps", "4", "--n-boot", "2000"],
 "timeout_s": 10800, "max_retries": 2, "outputs": ["research_lab/creative_batch1/B3/results.json", "trials.jsonl (1 cb1_prospective + count)"],
 "next_action": "verdict per CB1-B map", "notes": "commit only after T_censor_B3 = 2027-01-31; rung-list sha256 verified; declaration-hash guard"}
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

- The local cumulative count was 906 on 2026-10-15 (Ledger M3). SB2 adds 59-99, plus the automatic `flow_screen` lines.
- CB1 uses the run-time `battery2.cumulative_count()` value for BY triage labels only.
- The Stage-2 Holm family is the CB1 Stage-2 set (k ≤ 11).

## 6. Main scientific risks

1. **Power.** Every historical MDE is at or above the creative envelopes: A ≈ 1-2c, B ≈ 4-5c, C ≈ 3-6c, E1 ≈ 4-7c.
   - Most nulls will read "not detected at MDE", not "absent".
   - The tail-dominated carries (A, C) are decided by rare wrong-side outcomes. The cluster-aware tail gate, the
     ≥ 10-losing-cluster rule and the top-5-event robustness are therefore binding.
2. **Modelled asks.** History has no book outside the pmxt window.
   - The series price is mid-like, with an unverified stamp convention (mean gap to pmxt ≈ 0.75c, hence the binding
     +0.75c).
   - Band half-spreads come from one 2026-10-11 sweep, and genesis books are wider.
   - Positive history results are capped at "development" until stage P re-prices them at recorded asks.
3. **`end_at` look-ahead (A1).** "Past the scheduled end" uses the end date at fetch time, which may have been edited.
   Only stage P (the extract's `end_date` at capture) is clean.
4. **Survivorship and frame.**
   - The Gamma frame lacks long-lived active markets created before the lookback. A and E restrict to markets created
     inside it with `end_at ≤ T_fetch + 400d`.
   - h2 has no forward closed walk, so markets resolved early with a future `endDate` are missing from the h2 A2
     screen. Those are mostly early "decided" outcomes, so the omitted markets would have carried winning favourites
     *and* short holds. **The h2 A2 bias is plausibly positive in net and strongly positive in `R_ann`** (challenger
     item 2); only h5 (forward walk) is free of it.
   - Capped Gamma windows are excluded in h5 (busy windows under-represented, counted).
   - Ladder listing survivorship affects B (checked prospectively).
   - Trade truncation selects on future volume (§2.2; worst-case bounds reported).
5. **Fee regime.** Current fee rates are applied to periods with lower or no fees. This is conservative for P&L, but it
   means market behaviour under the current fees is untested before stage P.
6. **Dependence.** Hold-to-resolution positions overlap in calendar time.
   - Clustering is event × resolution week, with frame-window PSU as a sensitivity.
   - A market-wide resolution shock (an oracle policy change, mass 50-50) would hit every carry together.
   - The UMA/oracle regime can change (CH01-CH03 family risk).
7. **Snapshot inputs.**
   - CB1-D dev covers about 5.5 days, so day shocks cannot be clustered; the jackknife is binding. Replication covers 3
     weeks.
   - Raw captures are deletable after 8 days under the approved retention, and a raw rep window would not fit under
     the cap. CB1 therefore relies on the extractor (§2.11).
   - A pass that skips or an extractor timeout loses that capture for CB1 unless the archive release has it. Losses
     are counted.
   - The event member count comes from Gamma metadata fetched at extraction, not at capture time (disclosed; refreshed
     weekly).
8. **h2 wear.** h2 has been read many times, and PX1-PX4 and the pooled −7c resolution excess are known there. The A2, C
   and E screens on h2 are therefore not naive; only h5 replication and stage P count.
9. **Disk and calendar.** h5 uses about 0.63 GB on a host close to its cap date. The fetch can be paused by the pass
   guard (it is resumable). The extractor adds only MBs.

## 7. Next actions

1. Delegate to `implementer`:
   - the backfill options, `ladders-fetch`, `seal`/`verify-seal`, the access log and their tests;
   - `run_cb1_extract.py` and its tests.

   Then commit q0016-q0018 and q0030, and add the extractor line to `arepo_pass.sh` (§2.11). Deploy.
2. Delegate `creative_batch1.py` and `run_creative_batch1.py` with tests (§3), including the `KIND_RULES` entries.
   Commit the E3 text-rule hash, then run q0019 (h2 text and census, no outcomes) and insert the counts and MDEs.
3. Commit the declaration hash (`model_specs/cb1_v1.json`); this is the **CB1 freeze**. `T_rep_start` follows from it.
   There is no further challenger round (this was the single response round), but the freeze check of code against
   design remains.
4. After q0018: commit the seal copy, then commit q0020-q0023 (q0021 waits for q0003). Commit q0029 after the freeze,
   and commit its rung-list hash at `T_rep_start`.
5. Results: ledger entries, the batch Holm once all Stage-2 inputs exist, verdicts against the maps in §3, and the
   dashboard. Commit q0027 after 2026-11-09 (with the rep capture list) and q0028 after 2027-01-31.

## Results: h2_main development screen (2026-10-16)

Runs q0019 (census), q0020 (A, E), q0021 (C) on `h2_main` and q0023 (B, ladder probe on `h5_cb1_ladders`) on the
Oracle host. All are EXPLORATORY_HISTORICAL, L1 at most (h2 is worn beyond its revision budget, §6 risk 8). Declared
thresholds, floors and gates (§2.4, §2.5, §2.8) are unchanged and were applied as written. Declaration sha256 of the
screens: `58e203bb...` (B: `c9a2ec8d...`). Results files are on the host under
`data-dumps/research_lab/creative_batch1/` (`history/h2_main/results_cb1_AE.json`, `results_cb1_C.json`,
`census.json`; `B_r1/results_B.json`).

**Census (q0019, counts only):** A1 57 units / 51 event clusters; A2 348 / 281; E1-E3 0 units, because 2,886 of 3,200
h2 markets have no question text (A: 0 missing).

| Test | n / clusters | Estimate (net per share) | p (one-sided) | Placebo | Gate | Why |
|---|---|---|---|---|---|---|
| A1 | 57 / 51 | -4.00c (descriptive) | 1.0 | none | not testable | below the 100-unit floor (§2.3); counted, p = 1 |
| A2 | 348 / 281 | -1.05c, event-boot 95% CI [-2.96c, +0.64c]; `R_ann` -32.7% | 0.912 | skipped (gate not met) | no advance | fails p, floor (0.30c), `R_ann`, tail gate (11 losing clusters, bound 6.2% vs pi* 2.1%) and robustness (cost +0.75c: -1.66c; without top-5 events mean +0.35c but p 0.31) |
| E1 | 0 / 0 | n/a | 1.0 | none | not testable | no text units |
| E2 | 0 / 0 | n/a | 1.0 | none | not testable | no text units |
| E3 | 0 / 0 | n/a | 1.0 | none | not testable | no text units |
| C1 | 224 orders / 62 events | -3.84c per filled share, event-boot CI [-12.0c, +3.4c] | 0.907 | skipped (gate not met) | no advance | fails p, floor (0.50c), `R_ann` (-55.7%), tail gate (7 losing clusters, exact bound 26.8%) and robustness; PX1 not clean; capped "adverse selection not excluded" |
| C2 | 126 orders / 11 events | -2.54c (descriptive) | 1.0 | none | not testable | fewer than 30 event clusters (§2.3); counted, p = 1 |
| B1 | 52 usable ladders | none | 1.0 | none | not testable | stop rule (§CB1-B): fewer than 300 usable ladders |
| B2 | 52 usable ladders | none | 1.0 | none | not testable | same |

Notes that do not change any gate:
- A2: the h2 frame omits early-resolved markets with a future `endDate` (§6 risk 4), so its bias is plausibly positive,
  yet the point estimate is negative. The three truncated winners (`excluded_by_outcome` win 3) do not flip the sign.
  Reported subgroups (category, month, price band) are not binding; none was used for selection.
- A1 sports (n = 12, mean +1.4c) is descriptive only (`end_at` is game time).
- C1: fill rate 6.8% of attempted orders (210 filled of 3,150); decomposition captured half-spread +0.91c, resolution
  excess -4.75c. The without-top-5-events sensitivity is positive (+4.6c) but the declared tail and p conditions still
  fail, and it is a robustness check, not a result. The p-condition uses the exact event-level bound (fewer than 10
  losing clusters).
- E: a 6h-offset secondary has n = 3 (+22.3c); that is not evidence.
- The break-even placebo (§2.8) was not run for any test because no test met the gate (`placebo.n_draws = 0`, "skipped:
  gate not met (cannot advance)"). Only a test that reaches the gate gets its placebo, so no miscalibration finding exists
  for A2 or C1 in either direction.

**Decision:** no A, C or E test advanced (`advanced: []` in both result files); B1 and B2 are not testable. Therefore
no h5 replication run (q0024 for A/E, q0025/q0026 for C) is spent for these tests, and `h5_cb1` (listing sha
`a510e1c5...`) and `h5_cb1_ladders` (`d11064...`) stay sealed and unread by any outcome analysis. The seal copies are in
`docs/research_lab/seals/`. All nulls here read "not detected at the screen's MDE" (§6 risk 1), not "absent". E is
untestable on h2 because of missing text, not because of a negative result; E1-E3 cannot be tested without a new
declared text source or on h5 (a design change that needs its own review; nothing was run).

**Test count (M3):** 9 tests counted (A 2, E 3, C 2, B 2; `ml_explain` lines `creative_batch_1:A|E|C|B`; kinds
`cb1_history` x7 and `cb1_structural_replication` x2, plus one `cb1_history_descriptive` census line that counts 0). The
BY triage count at run time was 1,085-1,092. The "12 fixed" budget (§5) therefore stands at 9 used, with D1, D2 and B3
(3) still to come. Stage-2 Holm family: B1 and B2 only (§2.4), both p = 1.

**Still open in CB1:**
- CB1-D: dev freeze/screen (q0022) after `T_dev_end` 2026-10-17T00:00Z; replication (q0027) after 2026-11-09.
- B3 rung list (q0029) at `T_rep_start` (not before 2026-10-19T00:00Z); B3 results q0028 after 2027-01-31.
- Stage-2 batch Holm only has B1 and B2 (not testable); no A/C/E Stage-2 inputs exist.

## Open questions (draft round; resolved by challenger round 1)

1. B3 declared before its data and run in parallel with B1/B2: **kept**, with a rung list frozen and hashed at
   `T_rep_start`, a defined censoring rule and a non-IF-H2 secondary.
2. Tail and adverse-selection gates: **kept as gates** (not counted tests), made one-sided, cluster-aware and
   bound-based.
3. Weighting: **unweighted primary** everywhere; design-weighted secondary; sign agreement binding.
4. A1 24h post-end window: **kept** (identical on h2 and h5); sports excluded from the A1 primary.
5. Sampling profile and 7,000 markets: **kept**; capped windows excluded rather than truncated.
6. CB1-D payoff: structural payoff primary, with **realised-payout sign agreement and a ≤ 2% non-single-winner ceiling
   binding**.

---

## Challenger review, round 1 (science-reviewer, 2026-10-15): ACCEPT_WITH_REQUIRED_CHANGES

Condensed. [D] marks a coordinator decision.

1. **Trade truncation selects on the future.** Trades are fetched newest-first and capped. Conditions needing trades
   before t must be "unavailable" (not 0) for truncated markets before their oldest stored trade. Count exclusions by
   outcome; for C, excluded orders count as filled losers in a worst-case bound; for A2 and E, report exclusions by
   outcome.
2. **A2 origins depend on `closed_time` via `price_window`.** [D] Restrict A2 to scheduled life ≤ 100d on h2 and h5
   (as E). Fix §6.4: the h2 A2 bias is plausibly positive.
3. **Rare-event inference.**
   - (a) The placebo must draw at break-even (`Bern(a + f)`), with an advance rate ≤ 1.5%; the calibrated placebo
     cannot fail.
   - (b) The tail gate must be one-sided at the stage's α and cluster-aware (event-level bound or Wilson on `n/deff`);
     the same for "killed in category".
   - (c) A is testable only with ≥ 10 losing event clusters; otherwise the exact bound decides.
4. **CB1-D payoff.** An event is ineligible if any unresolved member is not open, and the visible member count must equal
   the event's. The realised-payout D2 is binding (same sign), with a declared ceiling on non-single-winner events.
5. **D2 depth.** D2 prices at Gamma `best_ask` without size. The depth-checked sweep variant must agree in sign, and the
   share of triggers with sweep data is reported.
6. **Snapshot retention and disk.** Old snapshots are deleted after 8 days, and the D rep window would need about 17 GB
   (> the 12 GB cap).
   - Readers take root flags, fail loudly on missing files and read frozen capture lists with sha256.
   - [D] Add an incremental extractor in the 2h pass (`|| true`, timeout) and extract dev captures now.
   - Name the CB1 readers for the retention gate.
7. **B3.** Define `T_censor` and a rule for unresolved rungs; give the R2 rung-list job a queue id and commit its sha256
   at `T_rep_start`; add a non-IF-H2 secondary; extend the declaration-hash guard to `ladders` and
   `snapshots --window rep`.
8. **"PX1 clean" is an absence verdict.** Decide it with the upper one-sided bound (hull of bootstrap and z·max SE).
   [D] Unweighted primary everywhere; weighted secondary.
9. **Binding robustness.** [D] Binding: +0.75c cost, without the top 5 events, weighted/unweighted sign agreement.
   Everything else is reported only (per-month signs are not binding for rare-tail carries).
10. [D] Drop the h4_seal amendment: h5 ends at `T_fetch` < `T_seal`, so the two are information-disjoint.
11. **h5 frame completeness.** Restrict A2/E to `end_at ≤ T_fetch + 400d`. [D] Set `pages_per_window` so that windows do
    not cap, and exclude and count any that still cap.
12. **E3.** Write the frozen regex into the declaration and hash it before q0019 reads h2 text. Disclose possible text
    edits since listing.

Optional, all adopted [D]:
- sports excluded from the A1 primary;
- frame-window PSU clustering as a sensitivity;
- capacity next to `R_ann`;
- an h5 access log;
- the `KIND_RULES` entries listed under code needed.

## Response to challenger round 1 (coordinator via drafting session, 2026-10-15 ~20:24Z)

All required and optional items applied. This is the single response round; there is no further review loop.

| Item | Change |
|---|---|
| 1 | New §2.2 truncation rule: known-true / unavailable, never 0, and an unavailable earlier candidate excludes "first origin" markets. Exclusions are counted by `Y`. Worst-case bounds: A and E add excluded markets as losers (reported); C adds excluded orders as filled losers; B1 adds excluded rungs as NO losers. Tests added. |
| 2 | A2 restricted to scheduled life ≤ 100d (and `end_at ≤ T_fetch + 400d`); the rationale is in CB1-A. §6.4 now states the h2 A2 bias is plausibly positive (net) and strongly positive (`R_ann`). |
| 3a | The calibrated placebo is replaced by the break-even placebo (`Bern(a + f)`, short side `Bern(a_c)`), with an advance rate ≤ 1.5% binding (§2.8). |
| 3b | §2.3 tail gate: one-sided at 99% (Stage 1) / 95% (Stage 2), Wilson on `n/deff` or the exact event-level bound. Advance needs upper bound < `π* − floor`; "killed in category" uses the lower bound. Applied to A and, by the same logic, C. |
| 3c | A (and C) need ≥ 10 losing event clusters for the z-test; otherwise the exact bound alone decides (§2.3, CB1-A, CB1-C). |
| 4 | CB1-D eligibility: every unresolved member open (`closed` false, `active`, `accepting_orders`), member count equal to the Gamma event count (extractor `event_members`), a YES-resolved member makes the event ineligible. Realised-payout D2 sign agreement binding, non-single-winner ceiling ≤ 2%, < 30 resolved events gives "inconclusive". |
| 5 | Depth-checked D2 (every member swept with `ask_size_1 ≥ 5`, execution at the next pass's sweep) must agree in sign; the sweep-available share is reported; < 30 clusters gives "inconclusive (depth unverified)". |
| 6 | New §2.11: `run_cb1_extract.py` (tables, sizes, manifest), the exact `arepo_pass.sh` line, q0030 backfill from 2026-10-11T12:00Z, root flags, fail-loud missing files, frozen dev/rep capture lists with sha256, and the CB1 raw readers named for the retention gate. D dev/rep, B3 and the A descriptive now read the extract. |
| 7 | `T_censor_B3` = 2027-01-31 with daily re-reads from `T_rung_out`; unresolved rungs are marked at the last NO bid, with 0/1 sensitivities and a "resolution-lag sensitive" flag above 10%. q0029 rung list, with its sha256 committed at `T_rep_start` before outcomes exist. R2 walk from 2024-01-01 with a non-IF-H2 secondary. Declaration-hash guard extended to `ladders` (q0023, q0028) and `snapshots --window dev|rep`. |
| 8 | "PX1 clean" decided by the upper one-sided bound (hull of bootstrap and z·max SE) < captured half-spread. Unweighted primary everywhere (§2.3, §2.6, CB1-A/C/E tables), design-weighted secondary. |
| 9 | §2.8: binding = +0.75c, without the top 5 events, weighted/unweighted sign; everything else is reported. §2.4 and the verdict maps refer to it. |
| 10 | h4_seal amendment removed (§1.1, §1.3, CB1-F, §7). Information-disjointness stated (`T_fetch` < `T_seal`). |
| 11 | A2/E restricted to `end_at ≤ T_fetch + 400d`. `--pages-per-window 20` (the Gamma offset cap), with any window that still caps excluded entirely and counted. The request estimate rises to ≈ 85k (≈ 7-9 h wall). |
| 12 | `NAME_RE`/`VERB_RE` written out in CB1-E and covered by the declaration hash, committed before q0019 reads text (q0019 refuses otherwise). Disclosure of post-listing text edits added. |
| Optional | Sports excluded from the A1 primary (reported separately); frame-window PSU clustering as a sensitivity; capacity reported next to every `R_ann` (§2.1); h5 `ACCESS_LOG.jsonl`; `KIND_RULES` entries in the code-needed list. |

---

## Freeze check (science-reviewer, 2026-10-15 ~23:25Z): code against the design
Code: extractor 11054c9/519df70, h5 fetch/seal 70603b4, A/C/E 9fd5378, D/B 3bdd985, KIND_RULES 8e42536. 124 tests pass.
**Verdict: ACCEPT_WITH_REQUIRED_FIXES for all four components.** q0016/q0017 held behind gate q0033 until fixes 1-2.

Required fixes:
1. **URGENT.** h5 price window anchored at max(close, end)+1d and 120 d back, so A1/A2 origin coverage depended on how late a
   market closed (the long-wait, tail-risk markets). Fix: union of the `min`, head and post-end windows, plus an
   invariance test. The same flaw affects h2 active markets, so the claim at the h2 coverage line in §CB1-F is false for
   them. The affected h2 units are counted and disclosed (`cb1_h5.py count-h2-coverage`), not refetched.
   **Counted (q0034, 2026-10-16T00:26Z, request clock 2026-10-11T23:00:33Z):** h2_main units whose price coverage misses
   [created, end + 1d]: **active 367 of 414** (miss the end anchor 367; 2 without an end date) and **closed 755 of 2,786**
   (miss the full interval; 730 miss the end anchor). The h2 screens q0020/q0021 read only the coverage that exists; origins
   outside it are counted as missing, never filled. The h2 A1/A2 cohort therefore under-represents long-wait markets
   (most active units and about a quarter of closed units); h5 (fix 1) does not have this flaw.
2. Trades not capped at T_fetch. Cap them and count the dropped rows; refuse new h5 chunks after T_seal.
3. `replicate` wrote into the sealed h5 directory, which would break `verify_seal`. Write outside it.
4. The completeness rule `created_at ≥ T_fetch − lookback` was not implemented.
5. The tail gate counted censored units as non-losers. Exclude them, and report a censored-as-loser bound.
6. Units with no as-of origin price were dropped silently. Count them by status.
7. The declared missing-outcome-as-losing worst case was not computed.
8. `replicated` came from a per-run Holm. Mark it provisional, and script the batch-wide Holm over all Stage-2 tests.
9. `t_rep_start` was a free CLI value. Pin it in a committed file (freeze commit + 2h).
10. The non-single-winner share was computed per trigger. Compute it per event.
11. `event_members` was overwritten on each refresh. Make it append-only.
12. Seal copy format: one file per run, `docs/research_lab/seals/<run_id>_SEAL.json`, with a top-level `listing_sha256`.
13. `fetch-outcomes-D` must require the committed declaration first.

Accepted deviations:
- The kinds `cb1_history*`/`cb1_structural*` and the spec `cb1_history_v1.json`, provided both declarations are committed in one freeze commit.
- The per-run Holm (with fix 8).
- An R1 fee of 0.07 (conservative).
- B, A, C and E results stored outside the sealed directories.
- D events with a closed member ineligible.
- B3 stays blocked until a `rungs/` extractor is live, which must be before T_rep_start or the B3 data are lost.

### CB1-D dev freeze (coordinator, 2026-10-16 23:07Z)
- Dev capture list frozen on the host after `T_dev_end` (`run_cb1_extract.py --freeze-list dev --until 2026-10-17T00:00Z`): **60 captures**
  from 2026-10-11T12:00Z, 0 missing from the extract, `final: true`, sha256 `967a0cb0887656f416adb419bef61667915b0d78933fc176aadc0541d618623e`.
  The doc's ≈ 66 assumed no outage; the passes lost in the 10-14 Mac outage are absent (operational deviation already in the ledger).
- Committed copy: `docs/research_lab/seals/cb1_dev_capture_list.json`.
- Queue: `q0022a_cb1_fetch_outcomes_D_dev` (net lane; the analysis date for the realised-payout gate is this fetch, fixed before any D outcome
  was read), then `q0022_cb1_snap_dev_D` (the §5 draft argv named a non-existent `run_creative_batch1.py`; the runner is `run_cb1_structural.py`).
