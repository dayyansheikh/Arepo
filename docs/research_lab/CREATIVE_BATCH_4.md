# Creative batch 4 (CB4): rule mechanics and natural experiments (pre-close dump, series roll, taker tiers, fee rollout)

`evidence_role: exploratory_dev` (CH46 dev on live captures) / `exploratory_historical` (CH50 screen and holdout,
CH52 and CH53 measurements) / `prospective` (CH46 replication; data after the freeze) | status: **DRAFT design, not
frozen, awaiting challenger round 1.** Last updated 2026-10-16 05:24 UTC+1.

This file turns CH46, CH50, CH52 and CH53 from `CREATIVE_HYPOTHESES_2026-10-16.md` into declared, falsifiable tests. It
follows `CREATIVE_BATCH_1.md` (CB1) and `CREATIVE_BATCH_2.md` (CB2) in structure and rules:
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim. AREPO never
  trades; every P&L is a paper rule at modelled or recorded prices.
- CB4 has **two kinds of work, counted separately** (§2.5):
  - **Routes** (CH46, CH50): money-route hypotheses with screen, frozen replication and an economic check. The primary
    quantity of an economic test is net P&L per filled share at executable prices after fees, with `R_ann` and
    capacity beside it.
  - **Measurements** (CH52, CH53): natural experiments on venue rules. They have no money route. Their results feed the
    shared cost model by a declared, one-directional rule (§2.9). They are never read as edge.
- Test tables bind only once the CB4 declaration hash is committed (`model_specs/cb4_v1.json`, the CB4 freeze).
- Queue specs (§5) are drafts. None is committed to `queue/jobs/` by this document.
- **Where CB4 says "as CB1 §x" or "as CB2 §x"**, that rule applies unchanged, including its challenger-round and
  freeze-check fixes.
- **No overlap with CB3.** CB3 (`CREATIVE_BATCH_3.md`, being drafted) covers the maker hypotheses CH35 and CH39-CH41.
  CB4 defines no maker presence filter, no farmer-wallet rule (CH41) and no quote-vacuum state (CH35). CH53's E2 is an
  era measurement of maker mark-outs that CB3 may consume (§2.9). It is not a CB3 test.

## 0. Summary, selection and ranking

| Rank | Job | Hypothesis | Tests (counted) | Dev / screen data | Replication / prospective data | Queue ids | CPU-h | Peak RAM |
|---|---|---|---|---|---|---|---|---|
| 1 | **CB4-F** data | `cb4_extract/closewin` (live + backfill), `h7_cb4_era` and `h7_cb4_series` backfills and seals, pmxt power pilot, dev-flip trades | none | n/a | n/a | q0080-q0086, q0089 | 3 + 8-12 h network wall | 1.5 GB |
| 2 | **CB4-N** taker-tier natural experiment (CH52) | after 2026-05-28 the fee band that only high-tier takers can harvest became rarer and shorter-lived | N1, N2 (measurement) | pmxt hourly L2 books, neg-risk events, 2026-04-30 to 07-02 | none (single-stage measurement, §2.3) | q0084, q0087 | 1-3 + 4-11 h network wall | 1.5 GB |
| 3 | **CB4-E** fee-rollout natural experiment (CH53) | after the taker-fee rollout, flow continuation per unit and maker adverse selection per print rose | E1, E2 (measurement) | `h7_cb4_era` (new) | none (single-stage measurement) | q0081, q0088 | 1.0 | 1.2 GB |
| 4 | **CB4-C** pre-close liquidity dump (CH46) | sell prints in the last 2h before a scheduled order stop are at a discount to the payout, and a resting bid there earns it | C1 (mechanism), C2 (economic) | live captures 2026-10-11T12:00Z to `T4_dev_end` via `closewin`, post-hoc Data API trades | live captures in `[T4_rep_start, T4_rep_end)` | q0080, q0085, q0090, q0093 | 0.5 | 1.0 GB |
| 5 | **CB4-S** series roll flow (CH50) | after a series member resolves, the next member's rolled-into side is bid up and reverts; a maker ask into the roll pays after a taker exit | S2 (mechanism), S3 (economic); S1 reported only | `h7_cb4_series` SCREEN block (earlier roll dates) | `h7_cb4_series` HOLDOUT block (latest roll dates) | q0082, q0083, q0091, q0092 | 1.0 | 1.2 GB |

**Why this order.**
- The `closewin` backfill must run first: CH46's dev window starts 2026-10-11T12:00Z, and raw captures older than 8 days
  become deletable under the approved retention (from about 18-19 October). Release copies remain, but downloading
  them costs about 70 MB per capture (§7 risk 8, open question 6).
- CH52 and CH53 run before the route screens. They change the cost assumptions of everything else (§2.9), and CH50's
  binding era rule (§CB4-S) depends on CH53's verdict.
- CH46 has the cheapest data (already being collected) but is calendar-bound: its dev outcomes resolve days after the
  flips, and its replication is prospective.
- CH50 needs a whole-series backfill; it has the largest historical sample of the two routes.

### 0.1 Selection and scope

No census was run for this draft. No CB4 quantity has been computed on any dataset, and the drafting session read no
capture, book, trade or outcome. The counts below come from existing documents only.

| Idea | Decision | Reason |
|---|---|---|
| **CH52** taker tiers | **include (N), measurement** | pmxt v2 hourly books cover 2026-04-13 to 08-10 with full market coverage, so the 05-28 launch is inside the window. The CLOB V2 switch (about 04-28 11:00Z), the tick change (07-02), the fee step (07-10) and the 06-12..06-17 gap are known regime dates (`HISTORICAL_SOURCES.md` §a) and are excluded by window rules. Ladders are dropped from CB4: the CB2 census found a text-free ladder proxy entirely misgrouped, and a text grouper over the April-July universe would need tens of thousands of text fetches. Neg-risk sums are text-free and structural. |
| **CH53** fee rollout | **include (E), measurement, on a new sample** | CH53 proposed `h2_main`. It is rejected for this purpose: (i) h2 trades are newest-first with a 10,000 cap, so a market's early trades are more often missing the longer it traded afterwards, which differs by era; (ii) the CB1 freeze-check fix 1 found h2 price coverage misses `[created, end + 1d]` for 367 of 414 active and 755 of 2,786 closed units, again era-dependent; (iii) h2's frame starts at closed markets ending after about 2026-01-14, so the no-fee period is thin. A purpose-built era sample with fetch windows anchored on each market's own scheduled end in the period avoids all three (§CB4-F). |
| **CH46** pre-close dump | **include (C)** | The sidecar has `accepting_orders` and `uma_resolution_statuses` since 2026-10-11T12:00Z. No historical store records the flip, and a historical proxy would need `closed_time` to define the population (forbidden as an anchor, CB1 §2.2). So CH46 is live-only. Trades are fetched post hoc: trading stops at the flip, so the Data API's newest-first page holds exactly the final window (truncation only above 10,000 trades in the last 26h, counted). No collector change is needed. |
| **CH50** series roll | **include (S), on a new sample** | `h2_main` is a random market sample: two consecutive members of one series are rarely both in it. `h3_power` is retired from replication; `h5_cb1` is sealed for CB1; `h6_weather` (the only whole-series store) is sealed for CB2-W. So a new series-complete backfill is needed (`h7_cb4_series`). Weather is excluded from it (§1.3). |
| CH47, CH48, CH49, CH51 | not in CB4 | CH47 needs a Polygon log scan; CH48 needs rule text for sports (scope undecided); CH49 needs frozen calendars per ladder family; CH51 needs per-series calibration families and would reuse `h7_cb4_series` outcomes, which CB4 keeps for CH50 only. Each needs its own batch. |
| CH54 | not in CB4 | builder-code scan of `OrderFilled` events (Polygon); cost class 3. |

**Sports.** The category scope is the user's decision. CB4 keeps it a parameter (`CB4_SPORTS_IN_PRIMARY = false`):
- CH46 and CH50 exclude sports from their primary tests and report a sports stratum (not counted), as CB1-A did.
- CH52 reports sports neg-risk events as a stratum (not counted).
- CH53 **uses sports markets as a comparison arm** of its staggered design (sports fees started 2026-02-18, the others
  2026-03-30). This uses sports data as a control. It is not a decision to bring sports into scope.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in CB4 | Evidence ceiling |
|---|---|---|---|
| Raw complete captures + sidecar + book sweeps (host, release copies) | E-series, SB2, CB1, CB2 | read only by the extractor (new table `closewin/`, live pass step plus one backfill, §4.3) | - |
| `cb4_extract/closewin/`, `cb4_extract/departures/` (**new**) | none | CH46 dev (captures `< T4_dev_end`) and replication (`[T4_rep_start, T4_rep_end)`) | L1 (dev) / L2-dev (rep) |
| Data API trades for flip markets (post hoc, **new**, `cb4/flip_trades/`) | none | CH46 prints in the final and baseline windows | as above |
| pmxt v2 hourly archive (`r2v2.pmxt.dev`, range reads) | ECONOMIC_CONDITIONS part B, r4_book (h2 pairs), SB2 J3, CB1-C | CH52 measurement on **neg-risk event members** (not the h2 pairs), 2026-04-30 to 07-02; CH52 power pilot on 2026-07-12 to 08-10 (outside the analysis window) | measurement |
| `history/h7_cb4_era` (**new**, §CB4-F) | none | CH53 measurement (single stage) | measurement |
| `history/h7_cb4_series` (**new**, §CB4-F) | none | CH50 SCREEN block (earlier roll dates) and HOLDOUT block (latest roll dates, sealed) | L1 / L2-dev |
| `h1_first`, `h2_main`, `h3_power` | many | **not read**, except their market-id lists to exclude markets from the h7 fetches | - |
| `h5_cb1`, `h5_cb1_ladders` | reserved by CB1 | **not read**; only the committed seal copy `docs/research_lab/seals/h5_cb1_SEAL.json` is read, for market ids in its file table (exclusion) | - |
| `h6_weather` | reserved by CB2-W | **not read**; the weather category is excluded from every CB4 population (§1.3) | - |
| `h4_seal` | reserved by SB2 | not read; no frozen parameter changes (§1.3) | - |
| `cb1_extract/`, `cb2_extract/` tables | CB1, CB2 | **not read by any CB4 code path** (they are CB1/CB2 analysis inputs; CB4 extracts its own table) | - |
| IF-H2 ladder universe | IF-H2, CB1/CB2 exclusion lists | not used (ladders dropped from CH52) | - |
| E009/E010 live poller | sealed until 2026-11-03 | not used | - |

### 1.2 Dates (declared; UTC)

| Name | Value | Meaning |
|---|---|---|
| `T4_draft` | 2026-10-16T04:15Z | First draft. No CB4 quantity has been computed |
| `T4_dev_start` | 2026-10-11T12:00Z | First sidecar capture (as CB1, CB2) |
| `T4_dev_end` | **2026-10-25T00:00Z** | CH46 dev: flips whose first `accepting_orders = false` capture starts before this (about 13.5 days, about 160 captures) |
| `T4_dev_out` | **2026-11-08T00:00Z** | CH46 dev outcome read (after the freeze). Unresolved at this time: censored (§CB4-C) |
| `T4_rep_start` | **max(2026-10-27T00:00Z, first complete capture ≥ CB4 freeze commit + 2h)**, pinned in a committed file (CB1 freeze-fix 9) | CH46 replication captures begin here |
| `T4_rep_end` | `T4_rep_start` + 28 d | End of the CH46 replication flip window |
| `T4_rep_out` | `T4_rep_end` + 21 d | CH46 replication outcome read |
| `T_seal` | 2026-10-22T00:00Z | SB2's h4 seal boundary. Every `h7_cb4_series` and `h7_cb4_era` row is capped at `min(T_fetch7, T_seal)` |
| `T_fetch7` | request clock of each h7 fetch | h7 data end; pinned in its manifest |
| `D_tier` | 2026-05-28 (launch 05-28/29) | CH52 treatment date. Days 05-28 and 05-29 are excluded from both windows |
| `W_pre_N` | [2026-04-30T00:00Z, 2026-05-28T00:00Z) | CH52 pre window (starts 2 days after the CLOB V2 switch) |
| `W_post_N` | [2026-05-30T00:00Z, 2026-06-12T00:00Z) ∪ [2026-06-18T00:00Z, 2026-07-02T00:00Z) | CH52 post window (pmxt gap and the 07-02 tick change excluded; the 07-10 fee step is after it) |
| `W_pilot_N` | [2026-07-12T00:00Z, 2026-08-10T00:00Z) | CH52 power pilot only (never part of the analysis) |
| `D_fee_S`, `D_fee_O` | 2026-02-18 (sports), 2026-03-30 (all other categories) | CH53 treatment dates (Polymarket docs and the cited rollout analysis; §7 risk 3) |
| `P0`, `P1`, `P2` | [2025-12-01, 2026-02-18), [2026-02-18, 2026-03-30), [2026-03-30, 2026-04-28) | CH53 periods: no fees; sports only; both. P2 ends before the V2 switch |
| `D_pl_E` | 2026-01-15 | CH53 parallel-trends placebo split inside `P0` (CH53's own placebo date) |
| `R_from`, `R_to` | 2025-10-01, `min(T_fetch7 − 3d, T_seal) − 2d` | CH50 roll times `t0` allowed in `h7_cb4_series` |
| `D_split4` | rule, computed at q0083 | First HOLDOUT roll date (§1.3); recorded in the seal before any CB4-S result |

### 1.3 Sealed and untouched data (named)

- **h5_cb1 and h5_cb1_ladders are avoided entirely.** The CB4 runner refuses the run ids `h3_power`, `h4_seal`,
  `h5_cb1`, `h5_cb1_ladders` and `h6_weather`. The h7 fetches read only the committed seal copy
  `docs/research_lab/seals/h5_cb1_SEAL.json`, take market ids from its file table (`prices/<market_id>.csv.gz`), and
  exclude and count every event with a member in that set (as CB2 §1.3).
- **h6_weather and CB2-W (HOLDOUT and stage P) are avoided by category.** The weather category (`fee_category ==
  "weather"`, and any event whose title matches CB2's `TEMP_RE`) is excluded from every CB4 population: CH46 flips,
  CH50 series, CH52 events, CH53 markets. CB4 therefore never reads a weather book, price, trade or outcome, and never
  touches CB2-W's live stage-P population. A weather version of CH46 or CH50 needs its own design after CB2-W's
  verdict.
- **SEALED-H7S (time-ordered split, as CB2 §1.3 SEALED-H6).** `h7_cb4_series` is split **by roll date** before any
  analysis:
  - U = every roll unit after frame exclusions (§CB4-S population), censored units included.
  - `D_split4` = the smallest UTC date d such that |{r ∈ U : date(t0_r) ≥ d}| ≤ 0.40 |U|.
  - **HOLDOUT** = {date(t0) ≥ `D_split4`}; **embargo** = {`D_split4` − 3d ≤ date(t0) < `D_split4`}, dropped from both
    halves and counted (3 days covers the longest declared reversal window, 48h, plus the pseudo-roll offset);
    **SCREEN** = the rest.
  - `D_split4` is computed by q0083 from `t0` dates only. No price, trade or outcome file is opened. The value is
    written to `SEAL.json` and to the committed seal copy before q0091.
  - The screen refuses HOLDOUT and embargo units. The HOLDOUT is read once, after the freeze, only for S tests that
    advanced. Every read is appended to `ACCESS_LOG.jsonl`.
  - **Residual dependence.** The halves share series (a series' early rolls are SCREEN, its late rolls HOLDOUT) and
    differ in calendar regime (the HOLDOUT is about July to mid-October 2026, entirely post-rollout and post-tier; the
    SCREEN contains pre-rollout rolls). A HOLDOUT failure may reflect a regime change. This is the reason for the
    binding era rule in §CB4-S.
- **h7_cb4_era is sealed too** (listing hash before q0088), so its data are fixed before any CH53 result. It has no
  holdout: CH53 is a single-stage measurement (§2.3).
- **Results outside sealed directories (CB1 freeze-fix 3).** Every CB4 result goes to `research_lab/creative_batch4/`.
  Nothing is written inside a sealed h7 run directory after its seal except `ACCESS_LOG.jsonl` appends (outside the
  listing).
- **h4_seal unchanged.**
  - **Cap (CB1 freeze-fix 2).** Every h7 price point and trade row is capped at `min(T_fetch7, T_seal)`. Dropped rows
    are counted per market in the manifest. The fetches refuse to start a new chunk at or after `T_seal`.
  - **Frame rules in code (CB1 freeze-fix 4).** Every declared frame rule is implemented, unit-tested and counted.
  - With both, the h7 runs are information-disjoint from SEALED-H4 analyses (origins ≥ `T_seal`), as CB1 §1.3 argued
    for h5.
  - **Disclosed:** CH46's replication window lies after `T_seal`, so it overlaps SEALED-H4's period in calendar time.
    It reads only CB4's own live extract and Data API trades of flip markets, never h4 data; its population and
    statistics differ from SB2's frozen tests.
- **SEALED-P overlaps (disclosed, as CB2 §1.3).** CH46's dev window [10-11, 10-25) overlaps CB1's SEALED-P (from
  `T_rep_start`, about 10-19, to 11-09) and CB2's dev window; its replication window overlaps CB1's and CB2's
  SEALED-P. CB4 reads raw captures only through its own `closewin` extractor and never opens `cb1_extract/` or
  `cb2_extract/` tables. The hypotheses differ:
  - CB1-A (post-end decided carry) uses markets past their scheduled end. CH46's final window is strictly **before**
    the scheduled end; post-end trades of flip markets are only reported (§CB4-C).
  - CB1-D and CB2-L use neg-risk and ladder touches. CH46 uses no sum or pair state.
- **pmxt overlap (disclosed).** CB1-C (h2 pairs) and possibly CB3 read pmxt books. CH52 reads neg-risk event members
  in its own windows and produces no fills. A market may appear in both. CH52's incidence result for April-July
  neg-risk sums is information about CB1-D's hypothesis on other data; CB1-D is frozen, so this cannot change its tests.

## 2. Common rules (deltas from CB1 §2 and CB2 §2)

### 2.1 Costs

As CB1 §2.1 (taker fee `f(a) = r·a·(1 − a)` per leg; sidecar `fee_schedule` with `fee_policy="conservative"` in live
data; the docs table by `fee_category` in history, current rates applied to all past dates; maker fee 0; rebates only
as an optimistic secondary; payout `Y` from Gamma `outcomePrices`; `R_ann` capital-time ratio; capacity beside every
`R_ann`). Additions:

| Item | Rule |
|---|---|
| CH46 maker bid | Paper bid at the recorded touch (§CB4-C). Maker fee 0, rebate excluded. `net = Y_j − q`, capital `K = q`, hold to resolution |
| CH50 maker ask + taker exit | Short the rolled-into token by a maker ask at `q` (minted set, capital `K = 1 − q`); exit by buying it back as a taker at the modelled ask `a_x = min(p_x + h(p_x), 0.999)` with `p_x` the as-of history price at the exit time and `h` the CB1 band table. `net = q − a_x − f(a_x)`. Binding sensitivity `+0.75c` on `a_x` |
| CH52 structural cost | `F0 = Σ_j r_j·a_j·(1 − a_j)` with `a_j` the 10-share VWAP ask of member j (`economics.sweep_fill`) and `r_j` from the latest pmxt `fee_rate_bps` of that token (else the docs table). Tier-adjusted fee `(1 − ρ)·F0`, `ρ = 0.50` primary (the top tier; third-party figure, unverified), `ρ = 0.25` reported |
| CH53 | no P&L; mark-outs in cents per share |

### 2.2 Clocks

As CB1 §2.2 and CB2 §2.2. In particular:
- History price points are usable from stamp + 600 s and at most 2h old. Trades use venue `ts`; a trade condition at t
  uses trades with `ts < t`. Truncation rule as CB1 §2.2 (known true / unavailable / false; exclusions reported by
  outcome where an outcome exists).
- Snapshot features come from the capture; a flip is bracketed by two consecutive complete captures with a start gap
  in [1.5, 3] h (CB1-D's gap filter). A pair outside that gap is excluded and counted.
- `end_date` in CH46 is the value **recorded in the capture before the flip** (clean, prospective). `closed_time` is used
  only to end a hold, for resolution-week clustering, and as CH50's roll trigger `t0` (a public event at that time,
  §CB4-S). It is never a population condition and never anchors a target window of the unit whose outcome is used.
- pmxt events need both clocks ≤ the state time (loader rule). Crossed books are ineligible states, never repaired.
- **Coverage invariance (CB1 freeze-check fix 1 lesson).** Every h7 fetch window is anchored on a fact that does not
  depend on how late the unit itself closed: CH53 on the market's scheduled `end_at` inside its period; CH50 on the
  predecessor's resolution time `t0`. A unit-level test asserts that every required window is covered, and units that
  lack coverage are counted as missing by reason, never filled.

### 2.3 Uncertainty and decision rule

- Unweighted means are primary. One-sided p (routes) or two-sided p (measurements) = the max over the declared cluster
  ways of CR1 (normal z, HB1 rule). CI by a 2,000-draw cluster bootstrap (seed 416).
- **Small-G rule** as CB2 §2.3 (G ≥ 30: CR1 normal; 15 ≤ G < 30: CR2 with t(G − 1) and a Webb wild-cluster bootstrap,
  9,999 draws, larger p; G < 15 in either way: "not testable", p = 1, still counted).
- Testability otherwise: ≥ 100 units and ≥ 30 clusters in each declared way. Otherwise "not testable" (p = 1, still
  counted).
- **Routes (CH46, CH50).**
  - **Stage 1** (CH46 dev; CH50 SCREEN): advance iff one-sided p < 0.01 in the declared direction, the §2.4 floor is
    met, `R_ann` ≥ 10% for economic tests, the placebo is calibrated (§2.6), the binding robustness holds, and the
    test's attribution rule holds (§CB4-C, §CB4-S). BY label (q = 0.10, `battery2.cumulative_count()`) attached as
    triage only.
  - **Stage 2** (CH46 replication on prospective captures; CH50 HOLDOUT): Holm at α = 0.05 one-sided over **all CB4
    route tests reaching Stage 2** (C1, C2, S2, S3; k ≤ 4). Early finishers are reported against Bonferroni α/k with k
    fixed when Stage 1 ends; the batch Holm can only add passes. A pass is "development-replicated (L2-dev)".
  - **Stage P** is not declared in CB4. A replicated route needs its own registration with recorded depth (sweeps)
    and, for CH46, a live near-close trade stratum.
- **Measurements (CH52, CH53).** One family **M** = {N1, N2, E1, E2}, single stage, Holm at α = 0.05 **two-sided**
  (k = 4). A measurement is **adopted** into the cost register (§2.9) iff it passes Holm, meets its §2.4 floor, its
  in-time placebo does not reject (two-sided p ≥ 0.05; otherwise the label "change not attributable to the rule"
  and no adoption), and the binding robustness holds. **Why single stage:** an adopted measurement can only make a
  cost assumption more conservative or narrow a later design's data window (§2.9 rule R0). A false adoption costs
  power in later tests; it cannot create a false edge. This is the only reason a replication stage is not required,
  and it is an open question for the challenger.

### 2.4 Materiality floors (declared before any run)

| Test | Type | Floor on the point estimate |
|---|---|---|
| C1 | mechanism | final-window seller discount minus baseline ≥ +1.0c |
| C2 | economic | net ≥ +1.0c per filled share and `R_ann` ≥ 10% |
| S2 | mechanism | reversal of the rolled-into side ≥ 0.50c (a fall of at least 0.50c) |
| S3 | economic | net ≥ +0.50c per filled share and `R_ann` ≥ 10% |
| N1 | measurement | \|DiD\| ≥ 0.50 percentage points of eligible event-minutes |
| N2 | measurement | \|DiD\| ≥ 5.0 percentage points of 5-minute persistence |
| E1 | measurement | \|δ\| ≥ 0.10c per pooled SD of flow |
| E2 | measurement | \|δ\| ≥ 0.25c per print |

S1 (reported only) has no floor and no gate.

### 2.5 Counting (M3 rule)

- Every counted test writes one `trials.jsonl` line via `provenance.append_trial`.
  - Routes: kinds `cb4_test` (Stage 1) and `cb4_replication` (Stage 2); count lines `creative_batch_4:C`,
    `creative_batch_4:S` (`ml_explain` kind, `n_tests`).
  - **Measurements: kind `cb4_measurement`; count line `creative_batch_4:M`.** They are counted in the cumulative M3
    total (they are inferential tests) but form their own Holm family and never enter the route Stage-2 Holm. Results
    files, the ledger entry and §6 list them separately from the routes.
  - `cb4_descriptive` (EXCLUDE, no inference): S1, the CH52 residual band map, the CH53 balanced-wallet share, gates,
    census, the pmxt pilot and all reported strata (sports included).
  - Seals reuse `history_seal_declaration`.
- New `battery2.KIND_RULES` entries: `cb4_test`, `cb4_replication`, `cb4_measurement` EXCLUDE ("counted by the matching
  `creative_batch_4:*` count line"); `cb4_descriptive` EXCLUDE. Unknown kinds still raise. A unit test runs the counter
  on the real `trials.jsonl`.
- Placebo lines `evidence_role: "placebo"`, count 0.
- **Cumulative count at drafting:** the ledger's last stated value is 952 before SB2-J7's 27 tests, so about **979**,
  plus automatic `flow_screen` lines and whatever CB1, CB2 and CB3 have logged by run time. The run-time
  `battery2.cumulative_count()` value is recorded in every CB4 results file.
- Tests behind a failed gate (§CB4-C G46, §CB4-S G50) are "not testable" (p = 1) and still counted.

### 2.6 Placebos and robustness

- **CH46.** C1: within-market window-label sign flip (Δ → −Δ per unit at random), 200 draws, advance rate ≤ 1.5%. C2:
  break-even placebo `Y_j ~ Bern(q)` (expected net 0), 200 draws, full gate, advance rate ≤ 1.5%.
- **CH50.** S2: within-unit sign flip of the reversal, 200 draws, advance rate ≤ 1.5%. S3: random-origin placebo
  (`t0` replaced by a seeded uniform time in the successor's covered life, outside `[t0 − 6h, t0 + V_end + 6h]`; 200
  draws; advance rate ≤ 1.5%).
- **CH52.** In-time placebo breaks at **2026-05-14** (pre window only, halves [04-30, 05-14) vs [05-14, 05-28)) and
  **2026-06-18** (post window only, [05-30, 06-12) vs [06-18, 07-02)), same DiD statistic. CH52 suggested 05-07;
  with the window starting 04-30 (after the V2 switch) a 05-07 break leaves one week before it, so the midpoint is
  used. Recorded as a deviation from the idea text, declared before any data.
- **CH53.** Parallel-trends placebo: the same DiD with `P0` split at `D_pl_E` = 2026-01-15 (sports vs others, no fees
  in either half).
- **Binding robustness for any advance, pass or adoption:**
  - (i) routes: `+0.75c` on every bought leg (C2: on `q`; S3: on `a_x`) keeps net > 0;
  - (ii) the test still meets its p threshold and floor without the top 5 clusters by absolute contribution, in each
    declared way;
  - (iii) the unweighted estimate and the cluster-equal-weighted estimate agree in sign;
  - (iv) CH50: the ask-side print series, the sell-side print series and the history price series agree in sign
    (§CB4-S); CH46: the size-weighted and print-equal estimates agree in sign;
  - (v) CH46 and CH50: the truncation worst case (§CB4-C, §CB4-S) keeps the estimate on the declared side.
- Reported, not binding: sign by month and by fee category, `+1c` cost, worst-case outcome coding, the sports strata,
  `ρ = 0.25` (CH52), touch-only gaps (CH52), per-era-SD scaling (CH53).

### 2.7 Pre-freeze census (q0086; counts only)

Outcome columns are dropped by guard before population code runs (CB1 §2.9). No book state, coefficient, mark-out or
price change is computed. It produces:
- **C:** flip counts per week by class (S, E, L, P, N, §CB4-C) and category; observed `uma_resolution_statuses` values;
  units with ≥ 1 sell print in both windows; truncation counts; the trade-side audit (§CB4-C); G46 counts; cluster
  counts (events, resolution weeks are not known before outcomes, so capture weeks are used for the count).
- **S:** series by cadence class and category; roll units; units with print availability at each declared time;
  units with a pseudo-roll origin; G per way (series, series × week) for the small-G rule; G50 counts; the
  rolled-into-member match rate for multi-member events (counts only, not split by side).
- **E:** markets, judgement rows and prints per cell (group × period, and the `P0` halves); event and day cluster
  counts; truncation counts per cell; the predicted MDEs by the declared scaling (§CB4-E).
- **N:** eligible events per sampled hour from metadata; missing or corrupt pmxt hours (HEAD checks only); the hour
  count `H` from the pilot rule (§CB4-N).
Floors are never revised from the census. **The CH50 member-matching rule and the cadence rule are hashed into the
declaration before q0082 reads any event title or `groupItemTitle`.** The `uma_resolution_statuses` exclusion set may
be extended once, at the census and before the freeze, by status strings only.

### 2.8 Compute, network and stop rules

- Queue worker, one job per lane, nice 19, `MemAvailable ≥ mem_mb + 1200`, address cap 2 × `mem_mb`; never two
  multi-GB jobs at once. pmxt jobs use the `net` lane (as q0002); the API fetches use the default lane.
- **Priorities ≤ 48** (below every CB1, CB2 and CB3 job): the `closewin` backfill 48, the h7 fetches and seals 47-46,
  the pilot and flip-trade fetch 45, the census 44, measurements 43, route screens and replications 42. CB4 pmxt jobs
  therefore wait for q0002 (priority 60) in the `net` lane.
- 15 CPU-hour cap per family. A job failing twice for the same non-transient reason stops and is recorded.
- A null is "not detected at MDE x", never "absent". No re-screen of a failed CB4 test with altered windows, bands,
  floors, horizons or populations, on any data.
- **Disk guard:** every h7 fetch refuses to start while host `data-dumps` exceeds 10 GB (cap 12 GB); caps
  `h7_cb4_era` 0.20 GB and `h7_cb4_series` 0.40 GB; the `closewin` backfill refuses above 10.5 GB and caps itself at
  0.40 GB. pmxt jobs stream and store only derived minute states (tens of MB).
- **Network etiquette and collector health:** as CB2 §2.8 (shared `Limiter`, live-collector yield, 429 and
  `Retry-After` back-off, 429 stop, collector-health stop). pmxt range reads use the existing `RangeFetch` with the same
  collector-health stop, and at most one hour file in flight.

### 2.9 How CH52 and CH53 feed the cost model used by CB1-CB3 (and CB4)

**Artefact.** q0089 writes `backend/astrolabe/research_lab/model_specs/cost_regimes_v1.json` once, after N and E are
done and family M's Holm is computed. It is committed with its sha256, and read through a new
`economics.cost_regime(date, fee_category)` accessor. Fields:
- `fee_eras`: `{sports: 2026-02-18, other: 2026-03-30}`, `tier_launch: 2026-05-28`, and the excluded regime dates.
- Per measurement (N1, N2, E1, E2): point estimate, two-sided 95% CI, Holm p, floor met, placebo p, **`adopted`**.
- `a_AS` (cents per filled share): the upper 95% bound of E2's δ if E2 is adopted with a positive sign (adverse
  selection rose after the rollout); otherwise 0.
- `era_rule`: `"post_rollout_or_interaction"` if E1 or E2 is adopted; otherwise `"pooled_allowed"`.
- `band_map`: the CH52 post-window residual map by category (share of eligible event-minutes in each band, KM median
  duration, 5-minute persistence, median touch depth and implied $ per week), with `ρ` and the margin used.

**Rules.**
- **R0 (one direction only).** A CB4 measurement can never lower a cost, raise an incidence assumed in a gate, or change
  a floor, threshold, window or verdict of a frozen test. It can only (a) add a cost term, (b) narrow the data window
  of a later design, or (c) inform the power planning of a later design. Any other use needs a new registration with a
  written scientific justification and challenger review.
- **R1 (era window; from E1, E2).** If `era_rule = post_rollout_or_interaction`, every flow-signal or maker mark-out
  design frozen after the register is committed must either estimate on post-rollout data only (sports from
  2026-02-25, the others from 2026-04-06, i.e. 7 days after each start) or include a declared era interaction.
  Pooled estimates spanning the rollout are labelled "era-mixed". If not adopted, pooled windows are allowed, and the
  design states "era difference not detected at MDE x (CB4-E)".
- **R2 (maker adverse-selection term; from E2).** Any maker P&L computed from fills before the rollout date of its
  category is reduced by `a_AS` cents per filled share. Fills after the rollout are unchanged (they already carry
  post-rollout adverse selection).
- **R3 (structural taker routes; from N1, N2 and the band map).** AREPO is a tier-0 taker, so its own fee is
  unchanged: the binding cost stays `F0` (CB1 §2.1). What changes is the competition. In structural registrations
  frozen after the register:
  - the band map supplies the planning incidence and persistence for MDEs (never a gate or a threshold);
  - if N1 is adopted with a negative sign, the gap band `((1 − ρ)·F0, F0]` is labelled **"maker-only after
    2026-05-28"**, and a taker structural route may not claim it in its envelope;
  - a tier sensitivity (net at `(1 − ρ)·F0`, `ρ` = 0.25 and 0.50) is reported, never binding.
- **R4 (historical taker fees).** Unchanged: current rates on all past dates (conservative, CB1 §2.1).

**What this means for each consumer.**

| Consumer | Current cost assumption | What CB4-M can change, and how |
|---|---|---|
| CB1-A, CB1-E (h2 screens, h5 replication: taker one leg) | CB1 §2.1 | Nothing binding (R0). One post-freeze **reported** deviation line per test: the estimate split by fee era (sports 02-18, others 03-30), labelled non-binding |
| CB1-C (longshot ask-selling, maker fills in the pmxt window) | maker fee 0, h2 prints in 04-13..08-10 | Nothing: every pmxt-window fill is post-rollout, so R2 does not apply. R3's tier sensitivity does not apply (maker) |
| CB1-D, CB2-L/X (structural taker legs, executed at the next capture) | tier-0 fee, recorded asks | Nothing binding (frozen; their c' execution already measures post-tier persistence directly). The band map and the "maker-only" label enter their verdict text as context, and any later stage-P registration under R3 |
| CB1-B, CB2-W | taker one leg | Nothing binding. CB2-W's SCREEN spans the weather fee start (03-30): one reported, non-binding deviation line by era |
| **CB3** (CH35, CH39-CH41 maker designs) | its own maker cost (rebate share, mark-outs) | **R1 and R2 bind if CB3 is frozen after the register is committed.** If CB3 freezes first, R1/R2 enter its results only as reported, labelled deviation lines (R0), and its later stage-P registrations must apply them. The band map is CB3's capacity prior for any maker structural route |
| CB4-S (CH50; SCREEN contains pre-rollout rolls) | §2.1 | **Declared now:** if `era_rule = post_rollout_or_interaction`, S2 and S3 may advance or pass only if the post-rollout subset (rolls after their category's rollout + 7 d) has the declared sign; and S3's pre-rollout fills carry `−a_AS` (R2). q0091 depends on q0089 so this is known before the screen |
| CB4-C (CH46; live, all post-rollout and post-tier) | §2.1 | Nothing (all fills post-rollout) |
| Flow family (HB2-R, J-series, multi-signal ML, E007) | pooled windows across the rollout | R1 for any registration frozen after the register; past results keep their labels |

---

## 3. Jobs

### CB4-N: Taker-rebate tiers as a natural experiment on harvestable neg-risk gaps (CH52), measurement

**Question.** After the seven-tier taker-rebate programme started on 2026-05-28/29, did executable sum-of-asks gaps
in neg-risk events that a top-tier taker could harvest, but a tier-0 taker could not, become rarer (N1) and shorter
lived (N2), relative to gaps that nobody can harvest as a taker?

**Why new / overlap.** CB1-D tests persistence of sum-of-asks states at a 2h latency on live captures (Oct-Nov). No
AREPO work has used minute-level books for structural states or a dated rule change. CH34 (round 1) proposed the fee
band; CH52 tests whether the band moved.

**Population (frozen).**
- Gamma events walked with `closed=true` and `closed=false` whose `endDate` ≥ 2026-04-30 and `startDate` <
  2026-07-02 (1-day windows split while capped; a window still capped is excluded and counted). Kept: `negRisk` true,
  `negRiskAugmented` false, no member with the "Other" placeholder flag (CB1-D rule), 2 to 10 members, every member
  with a condition id and both token ids. Excluded and counted: weather (§1.3); sports kept as a reported stratum
  (`CB4_SPORTS_IN_PRIMARY = false`).
- **Event open over hour h:** every member has `createdAt ≤ h − 1h` and none has `closedTime ≤ h + 1h`. (The second
  condition is a membership rule over the hour, as CB1's "open at t"; it uses no price or outcome.)
- **Hours (seeded `arepo-cb4-pmxt`):** for each day in `W_pre_N` and `W_post_N`, k hours, one drawn uniformly in each
  of k equal blocks of the UTC day (k = 3 for H = 168, 4.5 → alternating 4/5 for H = 252, 6 for H = 336; §MDE). A
  missing or corrupt pmxt hour is lost and counted, never replaced.
- **Events per hour:** from the events open over h, a seeded rank draw of up to 15 events with at most 90 members in
  total. The draw uses only metadata (ids, member counts), never book data.

**State definitions (minute m = 0..59 of hour h; state = the book at the end of the minute, both clocks ≤ that time).**
- Member j is eligible if its YES book is two-sided, not crossed, and its last applied event is ≤ 60 min old (receipt
  clock). The event-minute is eligible if every member is.
- `a_j` = 10-share VWAP ask of member j's YES token (`economics.sweep_fill`); fewer than 10 shares on the ask side →
  member ineligible for that minute.
- `G = 1 − Σ_j a_j`; `F0` as §2.1; margin `μ = 0.5c`.
- Bands: **hi** `G − F0 > μ` (tier-0 taker profitable); **mid** `G − (1 − ρ)F0 > μ` and `G − F0 ≤ μ` (profitable only
  for a top-tier taker); **lo** `G > μ` and `G − (1 − ρ)F0 ≤ μ` (no taker profits; maker-only). `ρ = 0.50`.
- Unit: an **event-hour** with ≥ 30 eligible minutes. `I_b` = its share of eligible minutes in band b.
- **Onsets:** minute m ≤ 54 where the state "mid or hi" is false at m − 1 and true at m, both eligible. `P5` = 1 if the
  state is true at m + 5 (eligible), 0 if false; ineligible at m + 5 → dropped and counted. Same for "lo" onsets.
  Per event-hour, `P5_mh` and `P5_lo` are the means over its onsets.

| ID | Kind | Unit | Statistic | Expected sign |
|---|---|---|---|---|
| **N1** | measurement | event-hour | `[Ī_mid(post) − Ī_mid(pre)] − [Ī_lo(post) − Ī_lo(pre)]` | < 0 (tested two-sided) |
| **N2** | measurement | event-hour with ≥ 1 onset of the type | `[P̄5_mh(post) − P̄5_mh(pre)] − [P̄5_lo(post) − P̄5_lo(pre)]` | < 0 (tested two-sided) |

- **Why the lo band is the control.** The tier rebate cannot make a lo-band gap profitable to any taker, so a summer
  liquidity trend that moves all gaps appears in both bands, while the tier channel moves only mid. The control is
  imperfect if makers changed behaviour at the same date (disclosed).
- **Estimator.** Stacked regression with two rows per event-hour (band mid and lo): `I = α + β1·post + β2·mid +
  β3·post×mid + ε`; N1 = β3. Same for N2 with onset rows. p = the max over clusters event and calendar day (CR1,
  two-sided). CI by the 2,000-draw event-cluster bootstrap.
- **Descriptive (`cb4_descriptive`):** the post-window **residual band map** by category (incidence, KM median duration
  right-censored at the hour end, `P5`, median `min_j` ask depth at onset, implied $ per week); the simple
  before/after of each band; the sum-of-bids side (`Σ b_j − 1 − F0_bid`) by band; touch-only gaps; `ρ = 0.25`; the
  sports stratum; the share of minutes lost to crossed or stale books.

**Power pilot and MDE (q0084, outside the analysis window).**
- 24 seeded hours from `W_pilot_N` (after the tick change and the fee step; never analysed) give base rates and SDs of
  `I_mid`, `I_lo`, `P5`, the eligible-minute rate, and the read cost per hour.
- **Frozen rule for H:** the smallest H ∈ {168, 252, 336} whose predicted N1 MDE (two-sided Holm first step α = 0.0125,
  80% power, design effect from the pilot's event clustering, at least 1.5) is ≤ 1.0 percentage point. If 336 does not
  reach it, H = 336 and the result states its MDE. H is written to the census before the freeze.
- Prior arithmetic (to be replaced by the pilot): about 15 event-hours per hour, so 2,520 (H = 168) to 5,040 (H = 336)
  event-hours; with SD(I) about 0.10 and design effect 2, the DiD SE is about 0.8 pp (H = 168) to 0.56 pp (H = 336), so
  the N1 MDE is about 2.7 pp to 1.9 pp. **If the mid band holds only 1-3% of minutes, N1 can detect a disappearance of
  the band but not a halving.** That is the honest expectation.

**Verdict map.**
- N1 or N2 adopted (Holm, floor, placebos null, robustness) with a negative sign → "tiers narrowed the top-tier band
  (measurement)"; R3's maker-only label applies.
- Change detected but a placebo rejects → "change not attributable to the tier launch"; no adoption; the band map is
  still published.
- Neither → "no tier effect detected at MDE x"; the band map is pooled over both windows for planning.

**Compute.** Per hour read: about 0.2-0.3 GB of range reads (about 70 row groups for about 90 condition ids; the 20-token
pilot read 91 MB, 13 of 159 groups) plus a fallback hour for stale tokens on about 30% of hours; about 1-2 min CPU to
parse and replay. H = 168: about 45-65 GB ingress, 4-6 h wall; H = 336: about 90-130 GB, 8-11 h wall, in resumable
150-minute chunks, `net` lane, 1.5 GB. Pilot: 24 hours, about 6-9 GB, under 1 h. Ingress is free on the host; the
pmxt host's rate behaviour is measured by the pilot.

**Stop rule.** If the pilot shows fewer than 5 eligible events per hour on average, or more than 30% of hours missing,
N1 and N2 are "not testable" (p = 1, counted) and only the band map is published from what was read.

### CB4-E: Fee rollout as a staggered natural experiment on flow informativeness and maker adverse selection (CH53), measurement

**Question.** When taker fees started (sports 2026-02-18, the other categories 2026-03-30), did 6h flow continuation
per unit of signed flow rise (E1), and did adverse selection against makers per print rise (E2)?

**Why new / overlap.** HB1 (FL2: +0.318c per SD [+0.216, +0.441] on 33,042 judgement rows in 425 clusters), HB1-R, HB2
and SB2 J7 pooled windows across the rollout. No AREPO test has split by fee era. The Columbia wash estimate is
pre-fee. CB3 may model maker mark-outs; CB4-E only measures their era change.

**Population (`h7_cb4_era`, frozen frame).**
- Frame: Gamma closed binary markets with `endDate` in `P0 ∪ P1 ∪ P2`, by the h2 frame method (`frame-v2-random-windows`:
  6 seeded 15-minute windows per day, `--pages-per-window 20`, a window still capped excluded and counted), walked with
  `closed=true` and `closed=false` (a market still open at `T_fetch7` with an end in the window stays in the frame and
  is censored for outcome-based secondaries only).
- Kept: scheduled life ≥ 2 days (`createdAt ≤ endDate − 2d`, so the first origin after the 1-day lag exists). Excluded
  and counted: weather; any market in h1/h2/h3 samples; any market in the h5 seal listing.
- Group g: **S** = sports (`fee_category == "sports"`), **O** = all other non-weather categories. Period p = the period
  containing `endDate`.
- Sample: seeded (`arepo-h7-era`) square-root allocation over g × p × `fee_category` × creation month; **800 markets
  per g × p cell, 4,800 in total**.
- Fetch windows (coverage invariance, §2.2): prices `[max(createdAt, start(p) − 8d), endDate + 1d]` in ≤ 14-day
  requests; trades newest-first ≤ 10,000 (the market ends in the period, so later trading is short; truncation is
  counted per cell).
- Origins: the 2h UTC grid within `[max(createdAt + 1d, start(p)), min(endDate, end(p)))`. An origin is in the period
  that contains it; markets contribute only inside their own period.

**Definitions (HB1 FL2 specification, reused from `battery.py`; HB1's judgement-row filter).**
- E1 target: `d, 6h` (history-price change over 6h); feature `f_imb_6h`, **standardised by the pooled SD over all
  cells** (so a change in flow variance after wash removal shows as a change in the per-unit slope, which is CH53's
  claim); controls C0, with cell-specific intercepts.
- E2: for each print i (trade `ts` in the period, history price usable at `ts + 2h`), the maker mark-out in YES terms:
  `m_i = s_i·(p(ts + 2h) − price_i^YES)` in cents, `s_i = +1` if the maker bought YES (taker sold YES or bought NO),
  `−1` otherwise (HB1's signed-flow rule, `_trade_flow`). Adverse selection `AS = −m`. Print-equal mean per cell.
- Cell estimates `β_{g,p}` (E1, OLS) and `AS_{g,p}` (E2, means).

| ID | Kind | Statistic | Expected sign |
|---|---|---|---|
| **E1** | measurement | `δ = (δ_S + δ_O)/2`, with `δ_S = (β_{S,P1} − β_{S,P0}) − (β_{O,P1} − β_{O,P0})` (sports treated, others untreated) and `δ_O = (β_{O,P2} − β_{O,P1}) − (β_{S,P2} − β_{S,P1})` (others treated, sports already treated) | > 0 (tested two-sided) |
| **E2** | measurement | the same two-cohort DiD of `AS_{g,p}` | > 0 (tested two-sided) |

- **Estimator.** One stacked regression per test with g × p cell interactions (E1: the flow slope interacted; E2: cell
  means of `AS`), δ as the declared linear combination; p = the max over clusters event and calendar day (CR1,
  two-sided); CI by the 2,000-draw event-cluster bootstrap resampling events within cells.
- **Treatment check (reported).** pmxt v2 starts 2026-04-13: the share of non-sports tokens with `fee_rate_bps > 0` in
  04-13..04-27 confirms that P2 is treated. No source confirms the pre-period state per market; treatment is by
  documented date (intent-to-treat).
- **Descriptive (`cb4_descriptive`):** the simple before/after per group; `δ_S` and `δ_O` separately; per-era-SD
  scaling; the 2h mark-out to resolution (secondary, outcome-based, censored markets flagged); the **balanced-wallet
  share** of notional per cell (wallet hashes with ≥ 4 trades in a market and \|net shares\| ≤ 5% of gross; a
  descriptive of wash-like activity defined here, **not** CH41's farmer rule).

**MDE (scaled from HB1 FL2, to be replaced by the census row counts).** FL2's SE was about 0.057c per SD on 33,042 rows.
At about 8,000 judgement rows per cell (4,800 markets, short in-period lives), a cell SE is about 0.12c; δ_S and δ_O
each combine four cells and share two, so SE(δ) is about 0.17-0.23c. **MDE (two-sided Holm first step α = 0.0125, 80%
power) about 0.6-0.8c per SD, against a pooled slope of about 0.32c.** E1 can therefore detect only a change larger
than about a doubling. E2: print SD of the 2h mark-out about 4c, effective clusters about 2,000 per cell, so SE(δ)
about 0.18c and **MDE about 0.6c per print**. Doubling the sample (9,600 markets, about 35k requests) would cut both
by about 30%; this is open question 2.

**Confounds (stated).**
- Composition: P0 contains the holiday period and the NFL season end; P1/P2 contain college basketball's tournament.
  The DiD removes common shocks, not group-specific season effects. The `P0` placebo tests differential trends only
  inside P0.
- April 2026 sports reward pools (over $5M; start date not pinned) may change sports maker behaviour inside P2, which
  is the control arm of `δ_O`. `δ_O` is therefore reported with the non-sports-only before/after (P1 → P2) beside it.
- The fee schedule changed again on 07-10 and the V2 switch is 04-28: both are outside P0-P2.

**Verdict map.** E1 or E2 adopted → `era_rule = post_rollout_or_interaction` (R1), and E2 sets `a_AS` (R2). The
parallel-trends placebo rejects → "era change not separable from a differential trend"; no adoption. Neither →
"no era change detected at MDE x"; pooled windows allowed with that statement.

**Compute.** Fetch (q0081): walk about 2-5k Gamma pages (666 windows), prices about 7k requests, trades about 6k; about
15-18k requests, about 2-3 h wall at ≤ 4 rps; about 0.15 GB. Analysis (q0088): panel build plus two stacked
regressions, 2,000 bootstrap draws and placebos, about 1 CPU-h, 1.2 GB.

**Stop rule.** If any g × p cell has fewer than 30 event clusters or 1,000 judgement rows, E1 and E2 are "not testable"
(p = 1, counted).

### CB4-C: Pre-close liquidity dump before `accepting_orders` flips (CH46)

**Question.** In markets whose order book shuts at the scheduled time while resolution is still pending, do sellers in
the final two hours before the scheduled end sell at a larger discount to the eventual payout than the same market's
sellers 24 hours earlier (C1), and does a resting bid at the recorded touch, filled only on a trade-through, earn a
positive net held to resolution (C2)?

**Why new / overlap.** CB1-A tests the post-end decided carry (after the scheduled end). HB2 F3 found flow continuation
stronger near resolution (taker side). No AREPO test has used the order-stop flag.

**Live extract (`cb4_extract/closewin/`, §4.3).** For every complete capture: each market with `end_date` in
`[capture_start − 72h, capture_start + 30h]` or `accepting_orders` false, with scheduled life ≥ 1 day
(`created_at ≤ end_date − 24h`); and `departures/`: markets present in the previous capture's `closewin` and absent
from this capture's complete listing.

**Flip classes (frozen; consecutive complete captures `c_k`, `c_{k+1}` with a start gap in [1.5, 3] h).**
- **Flip:** `accepting_orders(c_k)` true, `accepting_orders(c_{k+1})` false, market still listed at `c_{k+1}` with
  `closed` false.
- `e` = `end_date` recorded at `c_k`.
- **UMA-clear:** `uma_resolution_statuses` at `c_{k+1}` contains none of {`proposed`, `disputed`, `resolved`} (exact
  tokens; extendable once at the census). Empty or missing counts as clear only if the field exists in that capture's
  sidecar version; otherwise "unknown", excluded and counted.
- **Class S (scheduled, primary):** UMA-clear and `e ∈ (start(c_k) − 2h, start(c_{k+1})]`.
- **Class E (early):** `e > start(c_{k+1})`. The door shut before the schedule; probably outcome-driven (information,
  not a dump). Excluded; reported.
- **Class L (late):** `e ≤ start(c_k) − 2h`. A post-end flip (CB1-A territory). Excluded; reported.
- **Class P:** not UMA-clear. Excluded; reported.
- **Class N (control, door never shut before close):** accepting orders at `c_k`, UMA-clear at `c_k`, `e ∈
  (start(c_k) − 2h, start(c_{k+1})]`, and in `departures` at `c_{k+1}` (left the listing while still accepting).
- Excluded and counted: weather (§1.3); sports kept as a reported stratum; a market that flips more than once (its
  first class-S flip is used; reopenings are counted and kept, since reopening is a real risk of the strategy).
- One unit per market (its first qualifying flip).

**Prints (post hoc).** After `T4_dev_end` (dev) and `T4_rep_end` (rep), q0085/q0093 fetch Data API trades for every
class S, N, E and L market (newest first, ≤ 10,000). Trading stops at the flip, so the newest page holds the final
window. A market whose oldest stored trade is after `e − 26h` and that is truncated has an **unavailable** baseline
(CB1 truncation rule): excluded and reported by `Y`; worst case below.
- **Trade-side audit (pre-freeze gate, census).** The analysis needs "taker sold token j". It uses HB1's convention
  (`side`, `outcome_index`). In the census, for dev prints within 10 minutes of a capture, the share of `SELL` prints at
  or below that capture's mid of the same token must be ≥ 80%. Otherwise CB4-C stops before the freeze ("side
  convention unverified") and is recorded.

**Windows (scheduled, from `e`).** Final `W_F = [e − 2h, e)`; baseline `W_B = [e − 26h, e − 24h)`. Prints in
`[e, flip)` (post-end, before the door shut) are reported only.

**Definitions.**
- Seller discount of a sell print i on token j: `d_i = Y_j − p_i` (what the maker bid earned at the print price).
- `D_F(m)`, `D_B(m)` = print-equal means over sell prints in `W_F`, `W_B`. A unit needs ≥ 1 sell print in each.
- **C1 statistic:** `Δ(m) = D_F(m) − D_B(m)`; mean over class-S units.
- **C2 paper bid.** For each token j of a class-S market: `q_j` = the recorded best bid of j (YES: `best_bid`; NO:
  `1 − best_ask`) at the last complete capture starting at or before `e − 2h − 10 min` and at most 2h earlier; posted at
  `τ0 = e − 2h`; **filled at `q_j` only on a trade-through**: the first taker-sell print on j at a price strictly below
  `q_j` in `[τ0, e)`. Paper size 10 shares; fill rate reported. `net = Y_j − q_j` per filled share; `K = q_j`; hold to
  `closed_time`. The optimistic variant (fill at any sell print ≤ `q_j`) is reported.
- Outcomes are read once, at `T4_dev_out` (dev) and `T4_rep_out` (rep), into a guarded file (`fetch_outcomes`, reused
  from `cb1_structural`). Still unresolved: censored, valued at the last recorded bid of the side held and flagged;
  sensitivities at 0 and 1; above 5% censored the verdict carries "resolution-lag sensitive". 50-50 pays 0.5.

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| **C1** | mechanism | class-S market with sell prints in both windows | mean `Δ(m)` (cents) | > 0 |
| **C2** | economic | filled paper bid (market, token) | mean `net = Y_j − q_j` per filled share | > 0 |

**Attribution rule (binding for crediting CH46).** C1 is also computed on class N. CH46 is credited only if the class-S
estimate exceeds the class-N estimate (point estimates). Otherwise an advance or pass is labelled "late-life seller
discount, not the order stop" and needs its own design to be claimed. Rising adverse selection into the end works
against C1; that is part of the test, not a defect.

**Gate G46 (census, counts only).** At least 50 class-S units per week with sell prints in both windows, from at least
30 events, averaged over the dev window (CH46's own kill rule). Fail → C1 and C2 "not testable" (p = 1, counted),
CH46 closed "a curiosity: x units per week".

**Clustering.** One-sided p = the max over event and resolution week (ISO week of `closed_time` or of the censoring
mark). Dev also uses the leave-one-day-out sign rule over flip days (CB1 §2.3, binding at Stage 1).

**Truncation worst case (binding, §2.6 (v)).** Units with an unavailable baseline are added back with `Δ` = the 10th
percentile of observed `Δ`; C2 tokens whose final window is unavailable are added as filled losers (`net = −q_j`).

**MDE (census replaces this).** With SD(Δ) about 0.20 and design effect 1.3: at 100 units per week, dev (about 2 weeks)
SE ≈ 1.6c, **Stage-1 MDE ≈ 5.1c**; rep (4 weeks) SE ≈ 1.1c, **MDE ≈ 2.8c (k = 1) to 3.5c (k = 4)**. At 300 per week,
about 3.0c and 1.6-2.0c. The idea's envelope is a 2-5c discount, so CH46 is decided by the flip incidence. C2's
per-share SD is larger (about 0.35 for prices in 0.2-0.8), so C2's MDE is about 1.7 times C1's at equal fills.

**Economic check.** C2 is the economic test at a recorded touch with conservative fills and a hold to resolution.
`R_ann` and capacity (fills per week × median sweep `bid_size_1` where swept) are reported. A replicated C2 still needs
a stage-P registration with sweep depth and a near-close trade stratum before any claim.

**What would kill CH46.** G46 fails; C1 or C2 not detected at MDE; C1 positive but class N as large (late-life effect,
not the door); the truncation worst case flips the sign; or the side audit fails.

**Verdict map.**
- C1 and C2 replicated with attribution → "development-replicated pre-close dump carry (L2-dev)"; stage P next.
- C1 replicated, C2 not → "dump discount exists, not capturable by a trade-through bid at MDE".
- G46 fails → closed as a curiosity.

**Compute.** Extract: seconds per pass, about 0.3-0.5 MB per capture. Trades: one request per class S/N/E/L market
(expected 1-5k per window, under 30 min at 4 rps). Outcomes: Gamma `/markets?id=` in batches of 20. Analysis: minutes.

**Stop rule.** No C advance at dev → the rep trade fetch and analysis (q0093) are not committed.

### CB4-S: Series roll flow after a predecessor resolves (CH50)

**Question.** When a member of a recurring series resolves, does the next member's rolled-into side (the side that won
the predecessor) fall back over the following hours (S2, after S1's initial move), and does a maker ask posted into
the roll, exited later as a taker, pay after costs (S3)?

**Why new / overlap.** No AREPO store holds consecutive series members except `h6_weather` (sealed, excluded). CH51
(series calibration) is not in CB4. HB1/HB2 flow tests are pooled over markets and blind to series.

**Population (`h7_cb4_series`, frozen frame; rules hashed before any text is read).**
- **Series frame.** Gamma series reachable from event listings (`series` on events walked with `closed=true` and
  `closed=false`, end dates from 2025-09-24 to `R_to` + 2 d), or from the `/series` endpoint if q0082's probe finds it
  usable (the probe records endpoint facts; outcome fields are dropped by guard at parse time and never written).
- **Cadence rule (end dates only):** the median gap between consecutive member `endDate`s in the series: **daily**
  [20h, 28h], **weekly** [6d, 8d], **monthly** [27d, 32d]; anything else (sub-daily, irregular) is excluded and counted.
- Excluded and counted: weather; any event with a member in h1/h2/h3 samples, in the h5 seal listing or in the
  `h7_cb4_era` listing (fetched first). Sports series form a reported stratum (at most 60 series, not counted).
- **Sample:** up to 400 non-sports series, seeded (`arepo-h7-series`), square-root allocation over cadence × modal
  `fee_category`; per series a seeded block of up to 31 consecutive members with roll times `t0` in [`R_from`,
  `R_to`] (so up to 30 rolls per series; daily series cannot dominate).
- **Roll unit r = (series, predecessor e_k, successor e_{k+1}).** e_{k+1} is the member with the smallest `endDate`
  greater than e_k's, with `createdAt ≤ t0 − 1h`. `t0` = the predecessor's winning market's `closedTime` (the public
  resolution moment; sensitivity origin `endDate(e_k) + 1h`, reported).
- **Rolled-into side.** Binary-member events: the successor's token with the same outcome label as the predecessor's
  winner (Yes or No). Multi-member events: YES of the successor member whose normalised `groupItemTitle` (lowercase,
  whitespace and punctuation collapsed) equals the predecessor winner's; no exact match → unit excluded and counted. A
  predecessor without a single winner (50-50, void) → excluded and counted.
- **Horizons by cadence (declared):** daily: move window `M = (t0, t0 + 3h]`, `V_end = t0 + 12h`; weekly and monthly:
  `M = (t0, t0 + 6h]`, `V_end = t0 + 48h`. A unit needs the successor's `endDate ≥ V_end + 2h`.
- **Fetch window (coverage invariance).** Successor prices `[t0' − 3h, V_end + 2h]` (≤ 14 days, one request), with the
  pseudo-roll origin `t0' = t0 − (V_end − t0) − 6h`; successor trades newest first ≤ 10,000; predecessor metadata and
  outcome (needed to define the side). Rows capped at `min(T_fetch7, T_seal)`.

**Prices (three declared series of the rolled-into token, trades mapped to that token as `p` or `1 − p`).**
- **Ask-side print series (primary):** `P_A(τ)` = VWAP of taker-buy prints on the rolled-into token in `[τ − 60 min, τ)`;
  unavailable if none. Same-side prints avoid the bid-ask bounce that a mixed VWAP would create when rollers buy.
- Sell-side print series `P_B(τ)` (taker sells) and the history price `p(τ)` (usable rule): binding sign agreement.
- Truncation: a successor truncated with its oldest stored trade after `t0' − 3h` has unavailable prints (counted; the
  history-price series still exists and is the worst-case check below).

**Definitions.**
- S1 move (reported only): `P_A(t0 + |M|) − P_A(t0)`.
- **S2 reversal:** `v_r = P_A(V_end) − P_A(t0 + |M|)`; the test is on `−v_r` (a fall). Under a martingale null `E[v_r] =
  0` for any side fixed by information at t0, so no baseline is needed for calibration.
- **Pseudo-roll attribution (binding for crediting CH50).** The same `v` at `t0'` (before the predecessor resolved,
  same side). CH50 is credited only if `mean(−v_r) − mean(−v_{t0'})` ≥ half of `mean(−v_r)`; otherwise an advance or
  pass is labelled "generic drift of the winning side, not the roll".
- **S3 paper maker ask:** posted at `t0 + 10 min` at `q = min(p(t0) + h(p(t0)) + 1c, 0.99)` (modelled ask + 1c, from the
  history price usable at t0); **filled at q only on a trade-through**: a taker-buy print on the token at a price
  strictly above q in `(t0 + 10 min, t0 + |M|]`. Exit: buy back at `V_end` at `a_x` (§2.1). `net = q − a_x − f(a_x)`,
  `K = 1 − q`, hold `max((V_end − fill time)/1d, 1)`. Hold-to-resolution `q − Y_succ` reported (outcome-based,
  secondary).

| ID | Kind | Unit | Statistic | Direction |
|---|---|---|---|---|
| S1 | **reported only** (`cb4_descriptive`) | roll | mean move of the rolled-into side over M | none |
| **S2** | mechanism | roll with `P_A` at `t0 + |M|` and `V_end` | mean `−v_r` (cents) | > 0 |
| **S3** | economic | filled paper ask | mean `net` per filled share | > 0 |

**Era rule (declared now, from §2.9).** If CB4-M adopts `era_rule = post_rollout_or_interaction`, S2 and S3 may advance
or pass only if the post-rollout subset (rolls with `t0` after their category's rollout + 7 d) has the declared sign,
and S3's pre-rollout fills carry `−a_AS` per share. q0091 depends on q0089 for this reason.

**Clustering.** One-sided p = the max over series and series × ISO week of `t0`. The small-G rule (§2.3) applies to the
series way in each half.

**Truncation worst case (binding).** Units with unavailable prints are added back using the history-price series for
`v` (with the J4 caveat: a wide-state displaced mid); the estimate must stay > 0.

**Gate G50 (census, counts only).** At least 30 non-sports series and 300 SCREEN units with `P_A` available at both
times. Fail → S2 and S3 "not testable" (p = 1, counted).

**MDE (census replaces this).** About 400 series × up to 30 rolls; after exclusions (match rate, horizons, print
availability about 50-60%) about 2,000-3,000 units; SCREEN about 60% after the split. With SD(v) about 6-8c and a series
design effect about 2: SCREEN SE ≈ 0.3c, **Stage-1 MDE ≈ 1.0c**; HOLDOUT SE ≈ 0.4c, **MDE ≈ 1.0c (k = 1) to 1.3c
(k = 4)**. S3: fill rate perhaps 20-40%, per-fill SD about 7c, so **Stage-1 MDE ≈ 1.5c**. The idea's envelope is a
1-3c transient on the rolled-into side, of which a maker ask captures part, while the taker exit costs about 1.1c
half-spread plus a fee of about 1c at mid prices plus the binding 0.75c. **S3 is expected to fail its cost check unless
the transient is near the top of the envelope.**

**Economic check.** S3 (modelled exit, binding +0.75c). A replicated S3 needs a stage-P registration on live captures
at recorded asks before any claim.

**What would kill CH50.** G50 fails; S2 not detected at MDE; S2 present but the pseudo-roll as large (drift, not roll);
the print series disagree in sign; S3 ≤ 0 after the binding cost; or the era rule fails (the effect exists only before
the fee rollout, i.e. it was wash or farming flow).

**Verdict map.**
- S2 and S3 replicated with attribution → "development-replicated roll transient with a maker route (L2-dev)"; stage P.
- S2 replicated, S3 not → "roll transient exists, not capturable after a taker exit at MDE"; a maker-exit design would
  need continuous books.
- S2 not detected → "roll flow not detected at MDE x" (a roll that does not revert is informative, as CH50 notes).

**Compute.** q0082: series discovery about 1-2k Gamma pages; about 12,400 members: metadata and outcomes in batches of
20 (about 700 requests), one successor price request and one or two trade requests per roll (about 25-30k); **about
30-35k requests, about 2.5 h of pure request time at 4 rps, 3.5-5 h wall**; about 0.3 GB. Screen and holdout: about 15
min each plus bootstrap and placebos, 1.2 GB.

**Stop rule.** No S advance → the HOLDOUT is not opened.

### CB4-F: Data jobs

- **`closewin` extractor (live and backfill).** §4.3. The backfill (q0080) reads raw captures on the host, else release
  copies (download about 70 MB per capture; about 80 captures for 10-11 to 10-18 if retention has already removed them,
  about 5-6 GB transient, deleted after extraction).
- **`h7_cb4_era` fetch (q0081)** and **`h7_cb4_series` fetch (q0082)**, then **seals (q0083)**: listing hashes for both
  runs, `D_split4` for the series run, trial lines (`history_seal_declaration`), committed seal copies
  `docs/research_lab/seals/h7_cb4_era_SEAL.json` and `h7_cb4_series_SEAL.json` with top-level `listing_sha256` (CB1
  freeze-fix 12).
- **pmxt pilot (q0084)** and **dev flip trades (q0085)** feed the census (q0086).

---

## 4. Code needed

### 4.1 Modules

- `backend/astrolabe/research_lab/cb4_measure.py`
  - CH52: `walk_negrisk_events(start, end, limiter)` (closed true and false, window splitting, every exclusion
    counted), `open_over_hour(...)`, `sample_hours(seed, days, k)`, `sample_events(hour, events, seed, max_events=15,
    max_members=90)`, `replay_minutes(hour, condition_ids, token_ids, fetch)` (built on
    `history_sources.rebuild_book` and `load_book_snapshots`' clock rules; one-hour fallback; crossed and stale flags),
    `event_minute_states(...)` (VWAP asks, `G`, `F0`, bands, `ρ`, `μ`), `onsets_p5(...)`, `n_tests(...)` (stacked DiD,
    two-way clusters, bootstrap), `in_time_placebos(...)`, `band_map(...)`, `pilot_power(...)` with the frozen H rule.
  - CH53: `era_frame(...)` (wraps `history_backfill.fetch_frame` with the period windows and exclusions),
    `era_fetch_windows(...)` (coverage invariance), `era_panel(...)` (HB1 FL2 features via `battery`/`battery_data`,
    pooled-SD standardisation), `markouts(...)`, `two_cohort_did(...)`, `parallel_trends_placebo(...)`,
    `balanced_wallet_share(...)`.
  - `commit_register(...)`: family-M Holm, adoption rule, writes `model_specs/cost_regimes_v1.json` and its sha256.
- `backend/astrolabe/research_lab/cb4_rules.py`
  - CH46: `flip_pairs(closewin, departures)` (gap filter), `flip_class(...)` (S, E, L, P, N, unknown), `fetch_flip_trades`
    (wraps `history_backfill.fetch_trades`), `side_audit(...)`, `window_prints(...)`, `c1_units`, `c2_paper_bids`
    (trade-through and optimistic fills), `truncation_worst_case_c`, `c_tests`, `g46_gate`.
  - CH50: `discover_series(...)`, `cadence_class(end_dates)`, `series_sample(...)`, `roll_units(...)`,
    `rolled_into_side(...)` (hashed matching rule), `print_series(trades, side, kind)` (`P_A`, `P_B`), `s_units`,
    `pseudo_roll(...)`, `s3_paper_asks(...)`, `era_subset_rule(...)`, `truncation_worst_case_s`, `s_tests`,
    `g50_gate`, `split_h7s(units)` (the §1.3 rule; uses `t0` only).
- `economics.py`: `cost_regime(date, fee_category)` reading the committed register (absent register → the CB1 §2.1
  defaults, flagged).
- Shared statistics are **imported, not copied**: CB1/CB2 cost helpers (`leg_rate`, `half_spread`, `docs_fee`), the
  cluster gate (generalised to two-sided), bootstrap, small-G p-value (CB2), break-even placebo, LODO, capacity,
  `log_trials`, census guard, `fetch_outcomes`.
- `HYPOTHESES_CB4` and `declaration_sha256()` covering every population, class rule, window, band, margin, `ρ`, floor,
  gate, date, the split rule, the H rule, the cadence and matching rules and the §2.9 register rules.

### 4.2 Runner

`backend/scripts/run_cb4.py {era-fetch,series-fetch,seal,verify-seal,pilot,flip-trades,census,measure-N,measure-E,
measure-commit,fetch-outcomes,screen,replicate} --family C|S|N|E`.
- Refuses run ids `h3_power`, `h4_seal`, `h5_cb1`, `h5_cb1_ladders`, `h6_weather`, and any path under `cb1_extract/` or
  `cb2_extract/`.
- Declaration-hash guard (committed `model_specs/cb4_v1.json` must equal the code's hash) on `measure-*`, `screen`,
  `replicate` and `fetch-outcomes`.
- `screen --family S` refuses until `cost_regimes_v1.json` is committed; `replicate --family S` refuses before the
  freeze and logs every HOLDOUT read; `fetch-outcomes --family C --window dev` refuses before `T4_dev_out` and `--window
  rep` before `T4_rep_out`; `T4_rep_start` is read from its pinned committed file.
- `era-fetch` and `series-fetch` refuse until `docs/research_lab/seals/h5_cb1_SEAL.json` is committed, and at or after
  `T_seal`; `series-fetch` also refuses until the `h7_cb4_era` listing exists and the matching-rule hash is committed.
- Results are never overwritten and never written inside a sealed run directory (`research_lab/creative_batch4/...`).
- Generalise `h5_seal.ALLOWED_RUN_IDS` with the two h7 ids rather than duplicating seal code.

### 4.3 Extractor addition (`creative_batch1.py`, version `cb1-extract-v3`; no change to `arepo_pass.sh`)

- Own root `research_lab/cb4_extract/` and manifest. CB1 and CB2 tables stay byte-identical (test).
- `closewin/<capture_id>.csv.gz`: `capture_id, capture_start_utc, received_utc, market_id, condition_id, event_id,
  clob_token_id_0, clob_token_id_1, best_bid, best_ask, spread, last_trade_price, closed, active, accepting_orders,
  end_date, created_at, uma_resolution_statuses, volume_num, fee_schedule, fee_category, neg_risk_market_id,
  series_slugs` plus first-sweep `best_bid, best_ask, bid_size_1, ask_size_1` (blank if not swept). Selection as
  §CB4-C. Expected about 5-15k rows, 0.3-0.5 MB per capture (to be measured by the backfill).
- `departures/<capture_id>.csv.gz`: `market_id, last_seen_capture_id` for markets in the previous `closewin` and absent
  from this capture's listing.
- The 10-minute and 500 MB pass limits still hold. **Coordination:** if CB3 adds extractor tables, both go into
  `cb1-extract-v3` in one change, each under its own root.

### 4.4 Tests (`backend/tests/unit/test_cb4_measure.py`, `test_cb4_rules.py`)

- CH52: band classification on fixture books (hi, mid, lo at `ρ` 0.5 and 0.25, margin); 10-share VWAP with thin asks
  makes the member ineligible; crossed and stale books are ineligible; events with any ineligible member give an
  ineligible minute; onset and `P5` with an ineligible m + 5 dropped; the stacked DiD equals the four-mean formula; the
  event and hour draws use metadata only (a planted book change does not alter them); missing hours are counted, not
  replaced; the window rules exclude 05-28, 05-29, the pmxt gap and anything at or after 07-02; the pilot H rule.
- CH53: the period of an origin; the coverage-invariance assertion (a later `closedTime` does not change the fetch
  window); pooled-SD standardisation; the two-cohort DiD weights on a synthetic panel with a known δ; the maker sign for
  YES and NO prints; the `P0` placebo split; exclusions (weather, h1-h3, h5 listing) each counted.
- CH46: class S/E/L/P/N on fixture capture pairs, including a missing UMA field (unknown) and a gap outside [1.5, 3] h;
  `e` taken from `c_k`, not `c_{k+1}`; windows from `e`, not from the flip; the trade-through fill (a print at `q` does
  not fill; strictly below does); the optimistic variant; truncated baseline → unavailable, reported by `Y`; the worst
  case can block an advance; the side audit threshold; G46; the class-N attribution rule.
- CH50: the cadence rule; successor choice (`createdAt ≤ t0 − 1h`); binary and multi-member side rules (no match →
  excluded); horizons by cadence; `P_A` uses buys only and maps NO trades; the pseudo-roll offset does not overlap the
  roll window; the trade-through ask fill; the exit cost with `+0.75c`; the split is deterministic, disjoint, embargoes
  3 days and opens no price or outcome file; the era subset rule switches on only when the register says so.
- Runner: refusals (run ids, extract roots, before freeze, before out-dates, before the register); writes outside sealed
  directories; `verify_seal` passes after screen and holdout; `KIND_RULES` holds the CB4 kinds and the counter runs on
  the real `trials.jsonl`; `cost_regimes_v1.json` cannot be written unless family M is complete.

---

## 5. Draft queue specs

Paths follow `queue/README.md` (`argv[0]` under `backend/scripts/`, `cwd` `backend`). No spec is committed before its
code and tests exist; analysis jobs also need the reviewed CB4 freeze commit.

```json
{"id": "q0080_cb4_closewin_backfill", "title": "CB4-C: closewin/ + departures/ extract from complete captures since 2026-10-11T12:00Z (host raw, else release copies)",
 "family": "creative_batch_4", "priority": 48, "expected_value": "preserves CH46 dev inputs before raw captures are deleted",
 "data": ["research_lab/snapshots + rows_ext + book_sweeps (host, else release copies)"], "resources": {"mem_mb": 1000, "cpu": 1},
 "depends_on": [], "argv": ["scripts/run_cb1_extract.py", "--backfill-from", "2026-10-11T12:00Z", "--tables", "closewin,departures", "--budget-min", "150", "--disk-cap-gb", "0.40"],
 "timeout_s": 10800, "max_retries": 2, "repeat": {"max_runs": 4, "until_log_regex": "backfill_complete"},
 "outputs": ["data-dumps/research_lab/cb4_extract/{closewin/,departures/,manifest.json}"], "next_action": "pass step continues (extractor v3)",
 "notes": "idempotent by capture_id; CB1/CB2 tables untouched; release downloads deleted after extraction; refuses while data-dumps > 10.5 GB; priority below CB1-CB3 by instruction (see open question 6)"}
```
```json
{"id": "q0081_h7_cb4_era_fetch", "title": "CB4-E: h7_cb4_era backfill (4,800 closed binary markets ending in P0/P1/P2, sports vs other; prices + trades, period-anchored windows)",
 "family": "history_data", "priority": 47, "expected_value": "era-pure sample for the fee-rollout measurement",
 "data": ["public Gamma/CLOB/Data API", "h1/h2/h3 sample ids (exclusion)", "docs/research_lab/seals/h5_cb1_SEAL.json file table (ids only)"], "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api, clob, data-api"},
 "depends_on": [], "argv": ["scripts/run_cb4.py", "era-fetch", "--run-id", "h7_cb4_era", "--seed", "arepo-h7-era", "--per-cell", "800", "--periods", "2025-12-01,2026-02-18,2026-03-30,2026-04-28", "--exclude-runs", "h1_first,h2_main,h3_power", "--exclude-seal-ids", "../docs/research_lab/seals/h5_cb1_SEAL.json", "--exclude-categories", "weather", "--walk-closed", "true,false", "--cap-at", "2026-10-22T00:00Z", "--rps", "4", "--disk-cap-gb", "0.20", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 3, "repeat": {"max_runs": 3, "until_log_regex": "era_fetch_complete"},
 "outputs": ["data-dumps/research_lab/history/h7_cb4_era/{frame,prices/,trades/,outcomes_guarded.csv.gz,manifest.json}"], "next_action": "q0082, q0083",
 "notes": "about 15-18k requests, 2-3 h wall; 429 back-off and collector-health pause; rows capped at min(T_fetch7, T_seal); refuses while data-dumps > 10 GB; resumable"}
```
```json
{"id": "q0082_h7_cb4_series_fetch", "title": "CB4-S: h7_cb4_series backfill (series probe + discovery, <= 400 non-sports and <= 60 sports series, <= 31 consecutive members each; successor prices/trades anchored at t0)",
 "family": "history_data", "priority": 46, "expected_value": "series-complete roll units for the CH50 screen and holdout",
 "data": ["public Gamma/CLOB/Data API", "h1/h2/h3 ids, h5 seal listing ids, h7_cb4_era listing (exclusion)"], "resources": {"mem_mb": 900, "cpu": 1, "network": "gamma-api, clob, data-api"},
 "depends_on": ["q0081_h7_cb4_era_fetch"], "argv": ["scripts/run_cb4.py", "series-fetch", "--run-id", "h7_cb4_series", "--seed", "arepo-h7-series", "--n-series", "400", "--n-sports-series", "60", "--members-per-series", "31", "--roll-from", "2025-10-01", "--exclude-runs", "h1_first,h2_main,h3_power,h7_cb4_era", "--exclude-seal-ids", "../docs/research_lab/seals/h5_cb1_SEAL.json", "--exclude-categories", "weather", "--cap-at", "2026-10-22T00:00Z", "--rps", "4", "--disk-cap-gb", "0.40", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 3, "repeat": {"max_runs": 4, "until_log_regex": "series_fetch_complete"},
 "outputs": ["data-dumps/research_lab/history/h7_cb4_series/{series.jsonl.gz,units.jsonl.gz,prices/,trades/,outcomes_guarded.csv.gz,probe.json,manifest.json}"], "next_action": "q0083",
 "notes": "about 30-35k requests, 3.5-5 h wall; refuses until the matching/cadence rule hash is committed; outcome fields dropped by guard in the probe; rows capped at min(T_fetch7, T_seal); resumable"}
```
```json
{"id": "q0083_h7_cb4_seal", "title": "CB4-F: seal h7_cb4_era and h7_cb4_series (listing hashes; D_split4 time-ordered split with 3-day embargo; trial lines; access logs)",
 "family": "history_data", "priority": 46, "expected_value": "fixes both h7 runs before any CB4 result exists",
 "data": ["history/h7_cb4_era", "history/h7_cb4_series"], "resources": {"mem_mb": 400, "cpu": 1}, "depends_on": ["q0081_h7_cb4_era_fetch", "q0082_h7_cb4_series_fetch"],
 "argv": ["scripts/run_cb4.py", "seal", "--run-ids", "h7_cb4_era,h7_cb4_series"], "timeout_s": 1800, "max_retries": 1,
 "outputs": ["history/h7_cb4_*/{SEAL.json,ACCESS_LOG.jsonl}", "trials.jsonl (2 history_seal_declaration)"],
 "next_action": "Claude session: commit docs/research_lab/seals/h7_cb4_era_SEAL.json and h7_cb4_series_SEAL.json (with D_split4)", "notes": "split uses t0 dates only; no price, trade or outcome file opened"}
```
```json
{"id": "q0084_cb4_pmxt_pilot", "title": "CB4-N: power pilot on 24 seeded pmxt hours in 2026-07-12..08-10 (outside the analysis window): base rates, SDs, read cost, H rule",
 "family": "creative_batch_4", "priority": 45, "expected_value": "sets H for the CH52 measurement without looking at its windows",
 "data": ["pmxt v2 hourly archive (range reads)", "Gamma neg-risk event metadata"], "resources": {"mem_mb": 1500, "cpu": 1, "network": "r2v2.pmxt.dev, gamma-api", "lane": "net"},
 "depends_on": [], "argv": ["scripts/run_cb4.py", "pilot", "--family", "N", "--from", "2026-07-12T00:00Z", "--to", "2026-08-10T00:00Z", "--hours", "24", "--seed", "arepo-cb4-pmxt-pilot"],
 "timeout_s": 7200, "max_retries": 2, "outputs": ["research_lab/creative_batch4/N_pilot/pilot.json"],
 "next_action": "q0086 census reads H", "notes": "cb4_descriptive only; never analyses W_pre_N or W_post_N; streams, stores minute states only"}
```
```json
{"id": "q0085_cb4_flip_trades_dev", "title": "CB4-C: Data API trades for dev-window flip markets (classes S, N, E, L; newest first, <= 10,000)",
 "family": "creative_batch_4", "priority": 45, "expected_value": "final- and baseline-window prints for the CH46 census and dev screen",
 "data": ["cb4_extract closewin/departures (< T4_dev_end)", "public Data API trades"], "resources": {"mem_mb": 600, "cpu": 1, "network": "data-api"},
 "depends_on": ["q0080_cb4_closewin_backfill"], "argv": ["scripts/run_cb4.py", "flip-trades", "--window", "dev", "--extract-root", "../data-dumps/research_lab/cb4_extract", "--rps", "4"],
 "timeout_s": 7200, "max_retries": 2, "outputs": ["research_lab/creative_batch4/flip_trades/dev/", "manifest.json"],
 "next_action": "q0086", "notes": "commit after T4_dev_end; no outcome fields; truncation flags kept"}
```
```json
{"id": "q0086_cb4_census", "title": "CB4: pre-freeze census (C flip classes + G46 + side audit; S units + G per way + G50; E rows/clusters per cell + MDEs; N eligible events/hours + H; no outcomes)",
 "family": "creative_batch_4", "priority": 44, "expected_value": "testability, MDEs, gates and H before the freeze",
 "data": ["cb4_extract (< T4_dev_end)", "flip_trades/dev", "h7_cb4_era and h7_cb4_series SCREEN (no outcome file)", "N_pilot"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0083_h7_cb4_seal", "q0084_cb4_pmxt_pilot", "q0085_cb4_flip_trades_dev"], "argv": ["scripts/run_cb4.py", "census", "--family", "C,S,E,N"],
 "timeout_s": 3600, "max_retries": 1, "outputs": ["research_lab/creative_batch4/census.json"],
 "next_action": "Claude session: insert counts, gates, side audit and H into CREATIVE_BATCH_4.md; freeze", "notes": "outcome guard; floors not revised from the census"}
```
```json
{"id": "q0087_cb4_measure_N", "title": "CB4-N: taker-tier measurement on pmxt neg-risk books (N1, N2; in-time placebos; residual band map)",
 "family": "creative_batch_4", "priority": 43, "expected_value": "whether the top-tier-only gap band shrank after 2026-05-28; the band map for the cost register",
 "data": ["pmxt v2 hourly archive (W_pre_N, W_post_N; H seeded hours)", "Gamma neg-risk metadata", "model_specs/cb4_v1.json"], "resources": {"mem_mb": 1500, "cpu": 1, "network": "r2v2.pmxt.dev", "lane": "net"},
 "depends_on": ["q0086_cb4_census"], "argv": ["scripts/run_cb4.py", "measure-N", "--hours-from-census", "--n-boot", "2000", "--budget-min", "150"],
 "timeout_s": 10800, "max_retries": 3, "repeat": {"max_runs": 6, "until_log_regex": "measure_N_complete"},
 "outputs": ["research_lab/creative_batch4/N/{states.csv.gz,results.json}", "trials.jsonl (2 cb4_measurement + placebo + descriptive)"],
 "next_action": "q0089", "notes": "commit after the CB4 freeze; 45-130 GB ingress depending on H; resumable by hour; collector-health stop"}
```
```json
{"id": "q0088_cb4_measure_E", "title": "CB4-E: fee-rollout measurement on h7_cb4_era (E1 flow slope DiD, E2 maker mark-out DiD; P0 parallel-trends placebo)",
 "family": "creative_batch_4", "priority": 43, "expected_value": "whether flow and maker costs changed with the fee rollout; R1/R2 inputs",
 "data": ["history/h7_cb4_era (sealed)", "model_specs/cb4_v1.json"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0086_cb4_census"], "argv": ["scripts/run_cb4.py", "measure-E", "--run-id", "h7_cb4_era", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 1, "outputs": ["research_lab/creative_batch4/E/results.json", "trials.jsonl (2 cb4_measurement + placebo + descriptive)"],
 "next_action": "q0089", "notes": "commit after the CB4 freeze; verify-seal; declaration-hash guard"}
```
```json
{"id": "q0089_cb4_measure_commit", "title": "CB4-M: family-M Holm, adoption rule, write model_specs/cost_regimes_v1.json + count line",
 "family": "creative_batch_4", "priority": 43, "expected_value": "the cost register consumed by CB1-CB4 under rules R0-R4",
 "data": ["creative_batch4/N/results.json", "creative_batch4/E/results.json"], "resources": {"mem_mb": 300, "cpu": 1},
 "depends_on": ["q0087_cb4_measure_N", "q0088_cb4_measure_E"], "argv": ["scripts/run_cb4.py", "measure-commit"],
 "timeout_s": 900, "max_retries": 1, "outputs": ["backend/astrolabe/research_lab/model_specs/cost_regimes_v1.json (+ .sha256)", "trials.jsonl (creative_batch_4:M count line, n_tests 4)"],
 "next_action": "Claude session: commit the register; ledger; deviation lines for frozen CB1-CB3 tests (reported only)", "notes": "refuses unless N and E results both exist"}
```
```json
{"id": "q0090_cb4_screen_C_dev", "title": "CB4-C: dev screen (C1, C2; class-N attribution; placebos) on flips before T4_dev_end, outcomes read at T4_dev_out",
 "family": "creative_batch_4", "priority": 42, "expected_value": "whether CH46 advances to the prospective replication",
 "data": ["cb4_extract (frozen dev capture list + sha256)", "flip_trades/dev", "Gamma outcomes (guarded)"], "resources": {"mem_mb": 1000, "cpu": 1, "network": "gamma-api"},
 "depends_on": ["q0086_cb4_census"], "argv": ["scripts/run_cb4.py", "screen", "--family", "C", "--window", "dev", "--extract-root", "../data-dumps/research_lab/cb4_extract", "--rps", "4", "--n-boot", "2000"],
 "timeout_s": 3600, "max_retries": 2, "outputs": ["research_lab/creative_batch4/C_dev/results.json", "trials.jsonl (2 cb4_test + count + placebo)"],
 "next_action": "if advanced: commit q0093 after T4_rep_out", "notes": "commit after the freeze and after T4_dev_out; LODO binding; exits 0 'not testable' if G46 fails"}
```
```json
{"id": "q0091_cb4_screen_S", "title": "CB4-S: screen on h7_cb4_series SCREEN (S2, S3; S1 reported; pseudo-roll attribution; era rule)",
 "family": "creative_batch_4", "priority": 42, "expected_value": "which roll tests advance to the holdout",
 "data": ["history/h7_cb4_series SCREEN (sealed)", "model_specs/cb4_v1.json", "model_specs/cost_regimes_v1.json"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0086_cb4_census", "q0089_cb4_measure_commit"], "argv": ["scripts/run_cb4.py", "screen", "--family", "S", "--run-id", "h7_cb4_series", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch4/S_screen/results.json", "trials.jsonl (2 cb4_test + count + placebo + 1 cb4_descriptive)"],
 "next_action": "q0092 for advanced tests", "notes": "commit after the freeze; refuses HOLDOUT/embargo units; verify-seal; refuses until the register is committed"}
```
```json
{"id": "q0092_cb4_holdout_S", "title": "CB4-S: frozen replication of advanced S tests on h7_cb4_series HOLDOUT",
 "family": "creative_batch_4", "priority": 42, "expected_value": "development replication (Holm over the CB4 route Stage-2 set)",
 "data": ["history/h7_cb4_series HOLDOUT (sealed)", "creative_batch4/S_screen/results.json"], "resources": {"mem_mb": 1200, "cpu": 1},
 "depends_on": ["q0091_cb4_screen_S"], "argv": ["scripts/run_cb4.py", "replicate", "--family", "S", "--run-id", "h7_cb4_series", "--n-boot", "2000"],
 "timeout_s": 5400, "max_retries": 1, "outputs": ["research_lab/creative_batch4/S_holdout/results.json", "trials.jsonl"],
 "next_action": "Bonferroni interim; batch Holm with C rep", "notes": "exits 0 'nothing advanced'; one HOLDOUT read, logged"}
```
```json
{"id": "q0093_cb4_rep_C", "title": "CB4-C: prospective replication on flips in [T4_rep_start, T4_rep_end) (trades fetched post hoc; outcomes at T4_rep_out)",
 "family": "creative_batch_4", "priority": 42, "expected_value": "CH46 replication on data after the freeze",
 "data": ["cb4_extract (frozen rep capture list + sha256)", "public Data API trades", "Gamma outcomes (guarded)"], "resources": {"mem_mb": 1000, "cpu": 1, "network": "data-api, gamma-api"},
 "depends_on": ["q0090_cb4_screen_C_dev"], "argv": ["scripts/run_cb4.py", "replicate", "--family", "C", "--window", "rep", "--extract-root", "../data-dumps/research_lab/cb4_extract", "--rps", "4", "--n-boot", "2000"],
 "timeout_s": 7200, "max_retries": 2, "outputs": ["research_lab/creative_batch4/C_rep/results.json", "trials.jsonl"],
 "next_action": "batch Holm over the CB4 route Stage-2 set; ledger", "notes": "commit after T4_rep_out with the rep capture list; runner refuses earlier; exits 0 'nothing advanced'"}
```

## 6. Test budget and compute

| Job | Tests counted | Kind(s) | Family |
|---|---|---|---|
| **Measurements** N1, N2 (CH52), E1, E2 (CH53) | **4** | `cb4_measurement` + count line `creative_batch_4:M` (`n_tests: 4`) | **M**: own Holm, two-sided α = 0.05, single stage; never in the route Holm |
| Routes, Stage 1: C1, C2 (CH46 dev), S2, S3 (CH50 SCREEN) | 4 | `cb4_test` + count lines | each gated alone at one-sided p < 0.01; BY triage |
| Routes, Stage 2 (advanced only) | ≤ 4 | `cb4_replication` + count lines | one Holm, one-sided α = 0.05, k ≤ 4 |
| S1, band map, balanced-wallet share, gates, census, pilot, strata, seals | 0 | `cb4_descriptive`, `history_seal_declaration` | - |
| **Total** | **8 fixed (4 measurement + 4 route) + up to 4 conditional = 8-12** | | |

**Host compute.**
- About 4-7 CPU-hours at nice 19 (pmxt parsing is the largest). Peak memory 1.5 GB (pmxt jobs, `net` lane).
- Network wall: `h7_cb4_era` 2-3 h, `h7_cb4_series` 3.5-5 h (together about 45-55k requests at ≤ 4 rps); pmxt pilot
  under 1 h; pmxt measurement 4-11 h (45-130 GB ingress, set by H); flip trades and outcomes under 1 h per window.
- Disk: h7 runs about 0.45 GB; `closewin` about 0.3-0.5 MB per capture (about 0.35 GB over dev plus rep); pmxt minute
  states tens of MB; transient release downloads of about 5-6 GB only if the backfill runs after retention removed raw
  captures (deleted after extraction, under the disk guard).

## 7. Main scientific risks

1. **Power, everywhere.** E1 detects only a change above about a doubling of the flow slope; E2 about 0.6c per print;
   N1 about 1.9-2.7 pp before the pilot, against a mid band that may hold 1-3% of minutes; CH46 depends on an unknown
   flip incidence (MDE 2.8-5c at 100 units a week); S3 is expected to fail its cost check. Most nulls will read "not
   detected at MDE".
2. **Natural-experiment confounds.** CH52: summer liquidity trends (handled by the lo-band DiD), maker reaction at the
   same date (not handled), a third-party top-tier figure (`ρ = 0.50`, unverified). CH53: group-specific seasons (NFL
   end, college basketball), April sports reward pools inside P2, and treatment dates known from documents rather than
   per-market fee records before 04-13. The placebos test only part of this.
3. **Treatment dates.** 2026-02-18 and 2026-03-30 come from the Polymarket fee docs and a third-party rollout analysis
   (`CREATIVE_HYPOTHESES_2026-10-16.md` §5). If the true dates differ by days, the 7-day buffers of R1 absorb it; if by
   weeks, CB4-E is mis-timed (the P2 treatment check catches only the post state).
4. **pmxt replay quality.** No sequence numbers (crossed books), 5-15% missing hours, stale illiquid tokens, an
   unaudited subscription completeness. Crossed and stale minutes are ineligible, which may select toward liquid
   events; the lost-minute share is reported.
5. **Trade conventions.** CH46 and CH50 need the taker side. HB1's convention is used and audited once (CH46's side
   audit); a wrong convention flips signs.
6. **Truncation.** Newest-first trades with a 10,000 cap: benign for CH46 (trading stops at the flip), possibly
   outcome-adjacent for CH50 successors and era-dependent in history (the reason h2 was rejected for CH53). Worst cases
   are binding for the routes; counts per cell are reported for CH53.
7. **Selection rules from Gamma metadata.** CH46's classes depend on the recorded `end_date` and the UMA status strings;
   CH50 on series membership, `closedTime` semantics (unverified: market close or resolution) and an exact
   `groupItemTitle` match; the member counts of augmented events are excluded, not modelled.
8. **Calendar and disk.** The `closewin` backfill at priority ≤ 48 may run after raw captures from 10-11 to 10-18 are
   deleted; release copies then cost about 5-6 GB of downloads. CH46 replication outcomes arrive about 7 weeks after
   the freeze. The pmxt jobs wait for q0002 in the `net` lane.
9. **Misuse of the register.** A measurement used to lower a cost would be a back door to passing. R0 forbids it; the
   runner writes the register only after family M is complete; the register cannot change any frozen test.
10. **Overlaps.** Calendar overlaps with CB1/CB2 SEALED-P and SEALED-H4 (disclosed, §1.3); market overlaps with CB1-A
    (post-end) and CB1-D (neg-risk) are on different windows and statistics; CB3 is not touched.

## 8. Next actions

1. Challenger round 1 (`science-reviewer`) on this draft; one response round, as in CB1 and CB2.
2. Delegate to `implementer`: extractor v3 tables (`closewin`, `departures`), `cb4_measure.py`, `cb4_rules.py`,
   `run_cb4.py`, `economics.cost_regime`, seal generalisation, `KIND_RULES`, tests (§4). Commit the cadence and
   matching-rule hash before q0082 reads text.
3. Commit and run q0080 as soon as the extractor is deployed (urgent: raw-capture deletion). Then q0081, q0084; then
   q0082 and q0083.
4. After `T4_dev_end`: q0085, then the q0086 census; insert counts, gates, the side audit and H here; freeze
   (`model_specs/cb4_v1.json`); pin `T4_rep_start`.
5. Then q0087 and q0088, q0089 (commit the register), q0091 (needs the register), q0092 for advanced S tests; q0090
   after `T4_dev_out`; q0093 after `T4_rep_out`.

**Open questions for the challenger.**
1. **Single-stage measurements.** Is the one-directional adoption rule (R0) enough to justify no replication stage for
   N1, N2, E1, E2, or should E have a second sample (for example a frozen re-run on a disjoint era sample)?
2. **CH53 sample size.** 4,800 markets gives an E1 MDE of about 0.6-0.8c per SD (a doubling). Double it to 9,600 (about
   35k requests, 4-5 h wall), or accept and say so?
3. **CH52 control and parameters.** Is the lo band a valid control for liquidity trends, given makers may also react
   on 05-28? Is `ρ = 0.50` (third-party) acceptable as the primary band edge, with 0.25 reported? Is the 10-share VWAP
   the right executability size?
4. **CH46 definitions.** Class S by the recorded `end_date` bracket; windows anchored on `e`, not on the flip; class N
   as the attribution control; the trade-through fill at a touch up to 2h old. Is class N a fair "no door" control
   when many class-N markets resolve at once?
5. **CH50 definitions.** Ask-side print series as primary; the martingale argument for testing S2 against zero with a
   pseudo-roll attribution rule instead of a random-time baseline; exact `groupItemTitle` matching; cadence-specific
   horizons.
6. **Priority of q0080.** The instruction places every CB4 job at ≤ 48, below CB1-CB3. The `closewin` backfill
   preserves data before deletion, which CB1 (q0030) and CB2 (q0041) ran at 62. Should the coordinator raise q0080, or
   accept release-copy downloads (about 5-6 GB transient)?
7. **Sports as a control arm** in CH53 while the user's sports scope is undecided: acceptable as a measurement control?

---

## Challenger review, round 1

Pending (`science-reviewer`).

## Response to challenger round 1

Pending.
