# Screening batch 2 (SB2): conditional flow, liquidity regimes, related markets, bounce, interactions

`evidence_role: exploratory_historical` (history jobs) / `exploratory_dev` (prospective-snapshot jobs) | status: **DRAFT
design, not frozen**. Last updated 2026-10-15 19:54 UTC+1.

This file is the design for the next batch of development screens. It answers mission §10 questions Q2-Q6
(`AUTONOMOUS_PROGRAMME_MISSION_2026-10-15.md`).
- Nothing here is prospective confirmation, an edge claim, a calibration claim or a profitability claim.
- Every hypothesis table below becomes binding only when its code declaration hash is committed. Each family needs
  an accepting `science-reviewer` pass before that commit (standing rule). Wording, hypotheses, gates and families may
  change before the freeze. After the freeze, any change is a recorded deviation.
- Queue specs are drafts for `docs/research_lab/queue/jobs/`. None is deployed by this document.

## 0. Summary and ranking

Ranked by expected information gain per compute hour (1 OCPU, about 3 GB usable RAM). The order of execution can
differ: the runnable-now job goes first while the code for the others is written.

| Rank | Job | Question | Data | Queue ids | Status | CPU-h (est.) | Peak RAM (est.) |
|---|---|---|---|---|---|---|---|
| 1 | **J4** Bounce decomposition of the 2h reversal on prospective snapshots | Q5 | Complete-universe snapshots up to run time | q0006 | needs code (small) | 1.0 | 1.5 GB |
| 2 | **J1** HB2: when does flow predict, and does liquidity moderate other signals (h2 screen) | Q2, Q3, Q4, Q6 | `h2_main` battery features + trades | q0007, q0008 | needs code (medium) | 2.5 | 2.0 GB |
| 3 | **J2** HB2-R: frozen replication of J1 on `h3_power` | Q2, Q3 | `h3_power` battery features + trades | q0009, q0010 | needs code (shares J1's) | 2.0 | 2.0 GB |
| 4 | **J5** Sibling lead-lag (L1 family) re-screen on the 2h snapshot cadence | Q4 | Complete-universe snapshots up to run time | q0005 | **runnable now** | 1.5-3 | 2.6 GB (risk) |
| 5 | **J3** Book-mid bounce decomposition and depth-conditional flow (pmxt) | Q5, Q3 | `h2_main` features + pmxt book table (q0003) | q0011 | needs code (shares J4's) | 0.5 | 1.5 GB |
| 6 | **J7** ML regime and interaction validation, r5 (h2) | Q3, Q6 | `h2_main` panels | q0012 | needs code (medium) | 4-6 | 2.0 GB |
| 7 | **J8** Frozen replication of J7 on `h3_power` | Q3, Q6 | `h3_power` panels | q0013 | needs code (shares J7's) | 3-4 | 2.5 GB |
| 8 | **J6** Stale-follower sibling diffusion: h3 sibling fetch and frozen replication (conditional) | Q4 | `h3_power` + public Gamma/CLOB | q0014, q0015 | needs code (small) | 2.5 (mostly network) | 0.8 GB |

**Why this order.**
- J4 is cheap and settles a mechanism question outright (is the E002/E004 reversal last-trade bounce, one-sided quote
  refill, or genuine mean reversion of the book mid?).
- J1 and J2 are the core of Q2 and Q3. J1 is only a screen on worn data, so it is worth little without J2.
- J5 needs no code and powers up an inconclusive result (L1 MDE about 0.012), but its prior is weak (E005 not
  supported, XM3-XM6 null).
- J3 is cheap but blocked behind the long q0002/q0003 book build.
- J7 and J8 are the most expensive and answer Q6 at model level.
- J6 runs only if a J1 cross-market hypothesis advances (low prior).

**Not in this batch** (already answered, or out of scope):
- Q1 (wallets): wallet-age nulls were re-tested in HB1-R.
- r4_book: q0004, already queued.
- Cost conditions: the 95-cell economics study.
- IF-H2 ladders: dedicated null study.
- The book-family ablation: r4_book.

## 1. Data policy

### 1.1 Roles of each dataset

| Dataset | Prior use | Role in SB2 | Evidence ceiling |
|---|---|---|---|
| `history/h2_main` (420,937 origins, 1,759 markets) | r0-r3 ML, HB1 (72 tests, discovery before / judgement after 2026-07-01), surprise detector, r4_book pending | **Screening (discovery and judgement)** with HB1's split and embargo. Far beyond the per-window budget of 3 revisions (FDP §3); every SB2 result on it is labelled "beyond budget", L1 at most | L1 |
| `history/h3_power` (582,587 origins, 5,112 markets, disjoint from h1/h2, same calendar) | h3_replication (ML, seeded 2,138-market subset), HB1-R (all primary rows, 21 frozen tests), surprise-detector replication | **Frozen-definition replication only.** No discovery, no re-estimation of signs, scalings, cuts, thresholds or hyperparameters on h3. This is the source's 4th read, disclosed as such. A pass makes a hypothesis "development-replicated" (L2 candidate); it never confirms | L2-dev |
| `history/h1_first` (pilot) | Pilot backfill; source of the first pmxt book table | Not used: pilot data, already inspected, possible market overlap with h2 | none |
| `history_sources/book_features` (pmxt, 6h grid, 2026-04-13 to 08-10 minus 06-12..06-17) | HB1 MI8-MI10, LQ1-LQ4 (small n); r4_book pending | J3 only, on the q0003 table. h2-only, so no replication exists; L1 at most | L1 |
| `history_sources/new_wallets`, `wallet_cache` | HB1, HB1-R, r2 | Not used (Q1 out of scope) | - |
| `ml_cache` | MC1 development cache | Not used | - |
| Prospective snapshots / book sweeps / trade samples captured **before the job's run time** | E001-E007 (scored and complete), E011 (live, scored after 2026-11-11), flow_screen (automatic) | Development data for J4 and J5. These jobs never alter E011 inputs or its frozen analysis, and the hypotheses differ. Disclosed | L1 |

### 1.2 Data kept untouched for later confirmation (named)

- **SEALED-P (prospective):** every complete-universe snapshot, book sweep and trade sample captured **after the
  registration commit** of any candidate that comes out of this batch. This is the E-series rule: no SB2 job reads it
  for that candidate.
- **SEALED-H4 (historical, new markets and new calendar):** `history/h4_seal`, not yet collected.
  - It is to be built no earlier than **2026-11-16** with
    `backfill_history.py run --run-id h4_seal --seed arepo-h4-seal --exclude-runs h1_first,h2_main,h3_power --lookback-days 35`,
    then `panel`.
  - Analyses on it may use only origins `t >= T_seal`, where `T_seal` is the commit time of this file's freeze. Every
    origin therefore postdates every SB2 declaration.
  - Read rules: no SB2 job may read it. At most one read per registered candidate family, and at most three reads
    programme-wide (FDP §3).
  - Its manifest records the seal and a sha256 of the panels before any read.
  - Collecting it is a later queue job, not part of this batch, because its data do not exist yet.

There is no untouched historical sample today: h2 and h3 cover the same calendar and both have been read for flow.
Any candidate's confirmation must come from SEALED-P (registration) or SEALED-H4.

## 2. Common rules for every SB2 job

- **Baselines.**
  - Beta-style screens use HB1's control set C0 (logit mid, distance from 0.5, 1h/1d/1w changes with missing flags,
    own previous 2h change), plus the main effect of every moderator.
  - Model-level screens use **M2v** (LightGBM on the 16 M0v columns) and the same-learner rule: M2F against M2v, and
    ablation ΔLL against the M0v columns, never against the logistic M0v (r1 placebo diagnosis).
  - Interactions are judged against the free GBM with the pair forbidden (interaction constraints).
  - Snapshot screens use E004's frozen reversal ridge (`chg_1h`, coefficient -0.331610) and the E001 B3 set.
- **Clocks.** HB1 §2 applies unchanged.
  - Price points are usable from stamp + 600 s.
  - Trade windows are price-aligned (`ts < s_last`).
  - Truncated windows are NaN, never 0.
  - pmxt events need both clocks `<= t`.
  - Snapshot features come from the origin capture (and the previous capture), never the target capture.
- **Uncertainty.**
  - History beta tests: p = max(event-clustered CR1, two-way event × UTC-day), from the normal z. The CI is a 2,000-draw
    event-cluster bootstrap (HB1 `beta_test`).
  - Snapshot tests: event-clustered and two-way event × capture-period. With only about 5 calendar days, day-level
    shocks cannot be clustered; this is disclosed and reported as a leave-one-day-out jackknife range.
  - ML: conservative CI over event and dep_group clusters (`ml_explain`).
- **Two-stage decision rule for history families (J1 → J2, J7 → J8).**
  - **Stage 1 (h2 judgement):** one-sided in the discovery sign, with HB1 testability thresholds. A test **advances**
    if p < 0.01. The programme's triage label "screen-positive (L1)" is still attached by cumulative BY (q = 0.10).
  - **Stage 2 (h3, frozen):** Holm at α = 0.05 over the advanced set, one-sided in the h2 direction.
  - **"Development-replicated"** means passing Stage 2 with the same sign. Nothing weaker is reported as a finding.
  - Rationale: with a cumulative denominator above 650, BY needs z ≈ 4.1 (p ≈ 2e-5), which on h2 alone rules out
    every moderation smaller than about the size of the main effect. The independent-markets replication with Holm
    controls the family-wise error of what gets carried forward. This rule needs reviewer acceptance at freeze.
- **Counting.**
  - Every test is one `trials.jsonl` line via `provenance.append_trial` (kind per job below, `evidence_role`,
    `revision`, `provenance.run_provenance`, results-file `sha256_file`).
  - Each run also writes one `ml_explain` count line (`source: "screening_batch_2:<job>"`, `n_tests`) so both existing
    counters see it.
  - Placebo lines carry `evidence_role: "placebo"` and count 0.
- **Count defect to fix in J1's code.** `battery.prior_test_count()` skips the `ml_explain` line with
  `source == "hypothesis_battery_1"`. HB1's 72 tests are therefore missing from later recounts. The local recount gives
  598, the corrected value is 670, and the host has more automatic `flow_screen` lines.
  - SB2 uses a new `battery2.cumulative_count()`: every non-placebo `ml_explain` `n_tests` (all sources) plus one per
    non-placebo line of `battery.PRIOR_KIND_ONE` kinds.
  - The value at run time is recorded in each results file.
- **Placebos.**
  - Each history family is run once more on globally permuted targets (HB1's calibration placebo: expect about 5% of
    p < 0.05 and no advance).
  - ML jobs keep the r1 global-shuffle gate and the leak positive control.
  - Snapshot jobs add a capture-order permutation of targets within event (break the time link).
- **Robustness on advanced or replicated tests.**
  - Sign in each month and each fee category.
  - Flow windows ending 30 minutes earlier (`features_shift30`).
  - Without the 66 events shared by h2 and h3.
  - Sample-weighted (h3 `sample_weight`) as a secondary.
- **Economics.** Only for replicated directional hypotheses, using HB1 §6's paper rule restricted to the favourable
  moderator tercile. It is always labelled "optimistic, not tradable".
- **Compute.**
  - Jobs run under the queue worker: nice 19, one at a time, `MemAvailable >= mem_mb + 1200`, address cap 2 ×
    `mem_mb`.
  - `run_ml_history.heavy_lock` already falls back on Linux (`memory_pressure` absent gives 100%).
  - Never two multi-GB jobs at once (memory rule).
  - Short jobs get priority above q0002 (60), so they slot between its 150-minute resumable chunks.
- **General stop rules.**
  - Each family has a 15 CPU-hour cap per batch.
  - A family whose Stage-2 replication rate is below 50%, or zero, is not re-screened on historical data.
  - A job failing twice for the same non-transient reason stops and is recorded; gates are never loosened.
  - A null is reported with its MDE: "not detected at MDE x", never "absent".

## 3. Jobs

### J1: HB2 screen on `h2_main` (q0007 features, q0008 run)

**Question.**
- When is market-level taker flow predictive (Q2: liquidity, breadth, size, time to resolution, volatility, spread,
  absorption)?
- Does liquidity change which non-flow signals matter (Q3)?
- Do related markets lead stale followers (Q4)?
- These are simple pre-declared interactions that a single indicator misses (Q6).

**Why this is not a re-run.**
- HB1 established flow continuation (FL1-FL10) and three moderators: quiet (IX3), longshot (PX6) and near-end (IX4,
  binary 72h, null p 0.017). HB1-R replicated FL2/FL3/FL6/IX3/PX6.
- None of the moderators below was tested, except F3 and F6, which are partial re-tests:
  - **F3** replaces IX4's 72h dummy (about 4% of flow rows) with a continuous time-to-end moderator over the full range.
  - **F6** drops IX2's top-1 wallet factor, which WA4 showed is redundant with total imbalance, and tests price
    absorption alone.
- X1-X3 condition the null sibling averages (XM3-XM6, E005, L1) on a stale own market, which is where diffusion
  theory predicts the effect would concentrate.

**Data.**
- `h2_main/battery1/features.parquet` (on host) plus new columns.
- Split: HB1's (discovery `t + 24h <= 2026-07-01`, judgement `t >= 2026-07-02`).
- Primary rows: `traded_before_t != 0`.

**Notation.**
- `x6` = `f_imb_6h` with HB1's frozen FL2 scaling (clip [-1, 1] / 0.8578).
- `x24` = `f_imb_24h` (FL3 scaling).
- `z(.)` = standardised with h2 **discovery** mean and SD within the population, frozen into the spec.
- `L` = log1p(`f_N_24h`) (24h notional: cross-sectional liquidity).
- `K` = log1p(`f_n_6h`) (6h trade count).
- `TTE` = `ml_log_hours_to_end` (look-ahead flag inherited).
- `RV` = log(`ml_rv_1d` + 1e-4).
- `SPR` = `f_spread_proxy`.
- `U` = 1[sign(`x6`) × `f_chg_6h` <= 0] (flow not yet reflected in the 6h price change).
- `S2` = 1[`f_n_2h` == 0 and |`ml_own_dmid_prev`| < 0.005].
- `S24` = 1[`f_n_24h` == 0 and |`ml_chg_1d`| < 0.005].
- Interaction features are products of the scaled flow and `z(m)`. The effect unit is cents per SD of flow per SD of
  the moderator.

| ID | Q | Target, h | Population | Tested term | Controls (besides C0) | Prior |
|---|---|---|---|---|---|---|
| F1 | Q2/Q3 | d, 6h | `n6h` | `x6 · z(L)` | `x6`, `z(L)` | discovery sign |
| F2 | Q2 | d, 6h | `n6h` | `x6 · z(K)` | `x6`, `z(K)` | + (HB1 C2 caveat: slope comes from multi-trade windows) |
| F3 | Q2 | d, 6h | `n6h` and TTE known | `x6 · z(TTE)` | `x6`, `z(TTE)` | - (more continuation near resolution); partial re-test of IX4 |
| F4 | Q2 | d, 6h | `n6h` | `x6 · z(RV)` | `x6`, `z(RV)` | discovery sign |
| F5 | Q2/Q3 | d, 6h | `n6h`, `SPR` defined | `x6 · z(SPR)` | `x6`, `z(SPR)` | discovery sign |
| F6 | Q2 | d, 6h | `n6h`, `f_chg_6h` defined | `x6 · U` (raw) | `x6`, `U` | + (unabsorbed flow continues more); partial re-test of IX2 |
| F7 | Q2 | d, 6h | `n6h`, both defined | `x_big6` (SD-scaled, new) | `x_rest6` (SD-scaled, new) | + (large-for-this-market trades carry information) |
| F8 | Q2/Q3 | d, 24h | `n24h` | `x24 · z(L)` | `x24`, `z(L)` | discovery sign |
| L1 | Q3 | d, 24h | `all` | `ml_chg_1d · z(L)` | `z(L)` | discovery sign |
| L2 | Q3 | d, 24h | `all` | `f_longshot · z(L)` | `f_longshot`, `z(L)` (C0M) | discovery sign (is PX1 an illiquidity effect?) |
| X1 | Q4 | d, 2h | `nr_sib2` | `f_sib_nr_d2h · S2` | `f_sib_nr_d2h`, `S2` | - |
| X2 | Q4 | d, 2h | `co_sib2` | `f_sib_d2h · S2` | `f_sib_d2h`, `S2` | + |
| X3 | Q4 | d, 24h | `nr_sib24` | `f_sib_nr_d24h · S24` | `f_sib_nr_d24h`, `S24` | - |

New feature for F7, computed causally per market from `trades/<market>.csv.gz` with `battery.Trades` semantics:
- `q80(trade)` = 80th percentile of USDC notional over the market's trades in the 30 days strictly before the trade.
  It needs at least 20 prior trades, otherwise the trade is unclassified.
- `x_big6` = sum(sgn·n) / sum(n) over price-aligned 6h trades with n >= q80. `x_rest6` is the same for the others.
- The 30-minute-shifted variant is built too.

**Family, counting, MDE.**
- One family of **13** tests: one `history_battery2` line each, plus one `ml_explain` count line (n_tests = 13).
- The global-permutation placebo is logged as placebo.
- MDE: HB1's FL2 judgement SE is about 0.06c per SD and FL3's about 0.07c. An interaction with a unit-SD moderator has an
  SE of about 0.07-0.09c. At the Stage-1 gate (one-sided p < 0.01) the 80%-power MDE is therefore about **0.22-0.28c per
  SD per SD**, roughly 2/3 of the main flow effect per SD of moderator. Smaller moderation cannot be detected here.
  X-family power is low (HB1 XM3: 201 judgement events).

**Compute.**
- q0007: one pass over 1,759 markets' trades (about 875k trades) for the new columns plus shift30, and joins. About
  40 min, 1.5 GB.
- q0008: 13 tests × 2,000 bootstraps plus a 200-draw placebo plus robustness on advanced tests. About 1.5-2 h, 2 GB.

**Code needed** (implementer; not implemented here):
- `backend/astrolabe/research_lab/battery2.py`:
  - `size_features(run_dir, base, shift_s=0.0) -> DataFrame` (`market_id`, `t_i`, `x_big6`, `x_rest6`,
    `n_classified_6h`).
  - `derive2(d, spec) -> DataFrame` (moderators, `U`, `S2`, `S24`, interaction terms). It reads only origin-side
    columns; a guard rejects any target column.
  - `fit_spec(d_h2) -> dict`: discovery-only z means and SDs, F7 SD, discovery signs. Written to
    `model_specs/hb2_v1.json` with `spec_sha256`.
  - `HYPOTHESES2` (as `battery.Hyp`) and `declaration_sha256()`.
  - `POP_RULES2`, extending `battery.POP_RULES`.
  - `run_all2(d, spec, n_boot, threads, y_perm_seed=None)`, reusing `battery.run_beta` / `beta_test`.
  - `cumulative_count()` (§2).
  - `replicate(d_h3, spec, advanced)` (Holm, weighted secondary, without-shared-events secondary).
  - `log_trials(...)`.
- `backend/scripts/run_hypothesis_battery2.py {features,dryrun,run,replicate,siblings} --run-id {h2_main,h3_power}
  [--from h2_main] [--n-boot N] [--threads N] [--rps R]`.
  - `run` refuses unless the committed `hb2_v1.json` hash equals the declaration hash.
  - Outputs go to `history/<run>/battery2/`; results files are never overwritten.
- Tests in `backend/tests/unit/test_research_lab_battery2.py`:
  - `q80` uses only strictly earlier trades (a planted large trade never classifies itself).
  - Shifted windows end 30 min earlier.
  - `derive2` rejects target columns.
  - The declaration hash is stable and changes when a hypothesis changes.
  - `fit_spec` uses discovery rows only (judgement rows perturbed → spec unchanged).
  - `replicate` applies frozen cuts and signs unchanged.
  - Corrected `cumulative_count` on a fixture `trials.jsonl` includes HB1-style lines.
  - On permuted targets, p-values are roughly uniform (smoke).
- Before the freeze: a dry run on about 50 markets with globally permuted targets (HB1 §10 discipline).

**Stop rule.**
- If no F or L test advances, the h3 runs for those families are skipped and the conclusion is "flow continuation is not
  materially moderated by these variables at MDE about 2/3 of the main effect". No further historical flow-moderator
  batteries; flow work continues prospectively only (E007 family).
- If no X test advances, J6 auto-skips.

### J2: HB2-R, frozen replication on `h3_power` (q0009 features, q0010 replicate)

**Question:** do the J1 tests that advanced replicate on independent markets?

**Treatment of h3 (4th read):**
- Definitions, signs, scalings, z-parameters and cuts come from `hb2_v1.json` (h2 discovery) unchanged.
- All h3 primary rows are used, all dates (as HB1-R).
- Secondaries: pre- and post-2026-07-01 windows; without the 66 shared events; `sample_weight`.

**Family:** Holm at 0.05 over the advanced F and L tests (X tests replicate in J6). The verdict is
"development-replicated" or not.

**Counting:** one `history_battery2_replication` line per test plus a count line. The non-advanced tests are **not**
run on h3; this saves budget and avoids an undeclared second discovery.

**Power:** h3's flow tests use 2,100 events against h2's 425, but the slope SE is similar (FL2 h3 about 0.07c). With
Holm over k ≤ 5, the MDE is about 0.22-0.25c per SD per SD.

**Compute:**
- q0009 `size_features` on 5,112 markets: about 1 h, 2 GB.
- q0010: about 45 min, 2 GB.

**Code:** shared with J1 (`replicate`, the h3 path of `features`).

**Stop rule:**
- Zero replicated: close Q2/Q3 historical moderation (§2).
- At least one replicated: write a registration draft for a prospective test on trade samples (E007-type population,
  SEALED-P), with a reviewer pass. Run the paper cost check in the favourable tercile.

### J3: Book-mid bounce decomposition and depth-conditional flow, pmxt (q0011, after q0003)

**Question:**
- Q5: is the series reversal (HB1 MI2/MI6; E004) bounce or measurement, or a reversal of the book mid itself?
- Q3: is flow continuation stronger relative to book depth?

**Why this is not a re-run:**
- HB1's book tests (MI8-MI10, LQ1-LQ4) were underpowered on the h1-era table (3,243 judgement rows; LQ1 and LQ4
  untestable) and never used the **book mid as the target**.
- r4_book is an ablation of book levels, not this decomposition.

**Data:**
- `h2_main` primary rows on the 6h grid inside the pmxt window.
- They need two-sided, non-crossed books at `t-6h`, `t` and `t+6h` from the q0003 `book_features.csv.gz`.
- `bm` = (best bid + best ask)/2; `s` = panel series mid; `e_t` = `s_t - bm_t` (series minus book).
- `Δbm_prev` = `bm_t - bm_{t-6h}`.
- `w` = |Δask − Δbid| / (|Δask| + |Δbid|) over `[t-6h, t]` (1 = one side moved; 0 = parallel shift; 0 with a flag
  if neither moved).
- HB1's split (discovery for signs and z-scales, judgement for tests).

| ID | Target (6h) | Tested term | Controls | Prior | Reading |
|---|---|---|---|---|---|
| B1 | book-mid change | `Δbm_prev` | C0 (with `bm` level) | - | genuine book-mid reversal |
| B2 | series change (panel `dmid`) | `e_t` | `Δbm_prev`, C0 | - | series catches up to the book (measurement artefact) |
| B3 | book-mid change | `e_t` | `Δbm_prev`, C0 | two-sided | series leads the book (trade information) or not |
| B4 | book-mid change | `Δbm_prev · w` | `Δbm_prev`, `w` | - | one-sided quote moves refill (liquidity), parallel moves persist |
| D1 | series change | `x6 · z(log1p depth5c)` | `x6`, `z(log1p depth5c)` | discovery sign | flow continuation vs book depth |
| D2 | book-mid change | `Σsgn·n_6h / (depth5c + 100)` (SD-scaled) | `x6` | + | flow pressure relative to depth |

**Family:**
- Holm at 0.05 over B1-B4: the bounce verdict, judged on h2 judgement rows. There is no replication data, so the
  ceiling is L1.
- D1 and D2 use J1's Stage-1 gate. They are reported L1-only, because h3 has no books.
- Six tests, kind `book_decomp`, plus a count line.

**Verdict map (declared):**
- **Measurement/bounce:** B2 rejects with B1 not rejecting, and the B1 CI excludes E004-scale reversal (a slope of
  about -0.2).
- **Quote refill:** B1 rejects with B4 rejecting.
- **Book-mid mean reversion:** B1 rejects with B4 not rejecting.
- Otherwise inconclusive, with the MDE stated.

**Power:**
- Unknown until q0003 lands. If the table covers about 40% of the pmxt-window origins, expect about 10-20k judgement
  rows in 200-400 events.
- The verdict is declared "unavailable" below 2,000 rows or 100 events.

**Compute:** about 0.5 h, 1.5 GB.

**Code:** `bounce_decomp.build_book_triples(features_path, book_table, panel_6h)` and `book_tests(...)`, in the same
module as J4; see J4 for tests.

**Stop rule:** J3 and J4 together close Q5. No further bounce screens. A maker-side (passive) capture study would need
its own design.

### J4: Bounce decomposition of the 2h reversal on prospective snapshots (q0006)

**Question (Q5):** E004 confirmed (prospectively) that Gamma `chg_1h` predicts a reversal of the next ~2h Gamma mid
(slope -0.226). Is that last-trade bounce, one-sided quote refill, or mean reversion of the book mid?

**Why new:**
- E004 and E006 tested the reversal and its moderators.
- Nobody has decomposed the reversal by where the last trade sat in the spread, or by which side of the quote moved.
- `chg_1h` is Gamma's `oneHourPriceChange`, whose price basis is not documented.

**Data:**
- Complete captures in `research_lab/snapshots` up to run time: 59 capture directories on the host at 2026-10-15
  18:52Z, about 57 consecutive pairs.
- Triples `(h, i, j)` of consecutive complete captures with gap(h, i) in [1.5, 3] h.
- E001 pair semantics (`panel.build_pair`) for eligibility and target (`dmid` = Gamma mid change i → j).
- Features from `i`:
  - `chg_1h`, spread;
  - `b_pos` = clip((`last_trade_price` − mid) / (spread/2), −1, 1) (where the last trade sat; NaN if spread ≤ 0 or no
    LTP);
  - `liquidity`.
- From `h`: `Δbm_prev` = mid_i − mid_h; `Δbid`, `Δask`; `w` as in J3.

| ID | Tested term (target `dmid`, next capture) | Controls | Prior | Reading |
|---|---|---|---|---|
| P1 | `Δbm_prev` | spread, `b_pos` | - | the book mid itself reverses over ~2h |
| P2 | `b_pos` | `Δbm_prev`, `chg_1h`, spread | two-sided | last-trade position predicts the mid (+: flow/inventory; 0: pure bounce) |
| P3 | `Δbm_prev · w` | `Δbm_prev`, `w` | - | one-sided quote moves revert more (refill) |
| P4 | `chg_1h` | `Δbm_prev`, `b_pos`, spread | - | the E004 reversal survives once book-mid change and bounce position are controlled |

Also reported (descriptive, not tested):
- Attenuation 1 − γ_full / γ_alone of the `chg_1h` coefficient.
- Regression of `chg_1h` on (ltp_i − ltp_h) and (mid_i − mid_h), which reveals `oneHourPriceChange`'s basis.
- The far-touch version of P1 (target: bid change after a past ask-led fall), to tie it to E004's touch-to-touch loss.

**Family:** Holm at 0.05 over P1-P4. Kind `bounce_decomp`, plus a count line (n_tests = 4).

**Uncertainty:** event-clustered and two-way event × period, with p = max. The leave-one-day-out range (5 days) is
reported.

**Placebo:** targets permuted across captures within market (time link broken).

**Power:** about 2.4M pairs in about 20k event clusters. E004's slope SE was about 0.015 on 11 periods, so here it is
about 0.007 or better. Interactions are well powered.

**Compute:** triple build reads each capture (30 MB gz, about 295k rows) once with only the needed columns, three in
memory at a time. About 30 min to build plus 20 min of tests, about 1.5 GB.

**Code:**
- `backend/astrolabe/research_lab/bounce_decomp.py`:
  - `build_snapshot_triples(snapshot_root, until_utc=None, log=None) -> (DataFrame, counts)`;
  - `build_book_triples(...)` (J3);
  - `snapshot_tests(df, n_boot, seed)`;
  - `book_tests(df, spec, n_boot, seed)`;
  - `holm(...)`;
  - `log_trials(...)`.
- `backend/scripts/run_bounce_decomp.py {snapshots,book} --tag T [--run-id h2_main] [--n-boot N]`. Writes
  `data-dumps/research_lab/bounce_decomp/<run_id>/results.json` and refuses to overwrite.
- Tests in `backend/tests/unit/test_research_lab_bounce_decomp.py`:
  - Origin-only guard: no column of capture `j` enters features.
  - Triples skip gaps outside [1.5, 3] h.
  - `b_pos` clipping and NaN handling.
  - Synthetic pure-measurement world: the series reverts, the book mid does not → B2 negative, B1 about 0.
  - Synthetic one-sided-withdrawal-and-refill world → P3/B4 negative.
  - Synthetic random walk → all about 0.
  - Holm ordering.

**Stop rule:** as J3 (Q5 closes after J3 and J4).

### J5: Sibling lead-lag re-screen on the 2h snapshot cadence (q0005, runnable now)

**Question (Q4):** do the other markets of an event (liquidity-weighted `chg_1h`, L1) or the neg-risk group's sum
change (L3) predict a market's next-snapshot move beyond the reversal ridge?

**Justification for re-running a screen that was not significant:**
- The declared recommendation of `leadlag-62d593a402` says L1 "needs a same-horizon, fixed-cadence frame (2h snapshots)
  and about 3x the clusters (MDE about 0.012 now)".
- The host now holds about 57 consecutive 2h captures and no development captures (those stay on the Mac, so
  `build_all` skips them). That gives homogeneous horizons and about 4x the periods.
- The family, code, drafting rule and seed are unchanged.

**Disclosed overlap:** about 10 of the 57 periods (2026-10-10/11) were in the earlier run. A fresh-periods-only summary
is reported descriptively from `per_period_vs_R`.

**Family:** 4 variants × 2 configurations = 8 `leadlag_screen` lines (counted 1 each by the declared rule). The decision
uses the module's declared drafting rule (pooled ΔR² CI above 0 **and** at least 75% positive periods).

**MDE:** if per-period variance dominates, as before, about 0.012 × sqrt(14/57) ≈ 0.006.

**Compute:**
- Pairs for 57 periods: about 2.5M rows. One ridge walk-forward and 1,000 event-cluster bootstraps per variant and
  configuration.
- Estimated 1.5-3 h at 2.0-2.6 GB peak. Memory is the risk: the pairs frame keeps string ids.
- On OOM the job fails cleanly (results are written only at the end). The fix is a small `--captures-since/--until`
  flag, which needs code.

**Stop rule:**
- Drafting rule not met at MDE ≤ 0.006, together with no X test advancing in J1: retire the Polymarket-internal
  related-market family (E005, L1, XM, X). Cross-venue (E009/E010) continues.
- Met: one candidate. A registration needs fresh captures (SEALED-P) and a design for the dependence between pairs in
  the same event.

### J6: Stale-follower diffusion, h3 replication (q0014 fetch, q0015 replicate; conditional)

**Question (Q4):** do the X1-X3 tests that advanced on h2 replicate on h3?

**Precondition:**
- At least one X test advanced in J1.
- The fetch script reads `history/h2_main/battery2/results_hb2.json` and exits 0 with `skipped: no X advanced` if not.

**Data:**
- Gamma `/events` metadata for h3 events (about 2,700) and CLOB `prices-history` for neg-risk and co-event siblings
  over each sampled market's traded span plus 8 days.
- HB1's sibling rules (2-25-member non-augmented neg-risk events).
- About 9-10k tokens and about 20k requests at 4 req/s, yielding to the collector pass. About 1.5-2 h of network.

**Then:** sibling columns only (`battery.Siblings.features`) are merged into h3's battery2 table. Frozen X definitions,
Holm over the advanced X tests. Kind `history_battery2_replication`.

**Code:**
- `run_hypothesis_battery2.py siblings --run-id h3_power` (meta + siblings + columns; resumable, request-capped). It
  reuses `battery_data.fetch_event_meta` and `fetch_sibling_prices` with output under `h3_power/battery2/`.
- `replicate --family X`.
- Tests: the gate skips cleanly; sibling columns are as-of (`s + 600 < t`, at most 2h old) on a fixture.

**Stop rule:** no X replicates → retire the family (with J5's verdict).

### J7: ML regime and interaction validation, revision `r5_regime_ix` on `h2_main` (q0012)

**Question:**
- Q3 at model level: in which liquidity, time-to-resolution, trade-activity or price-extremity regimes does the full
  model beat the M0v-feature model?
- Q6: do learned pairwise interactions add out-of-sample value that the tree model cannot get without them?

**Why new:**
- r0-r3 measured families pooled over all rows.
- `ml_explain.regime_study`, `interaction_study` and `interaction_validation` exist and are tested but have never been
  run on history.
- `DECLARED_REGIMES` uses `ml_log1p_liq` (Gamma liquidity), which is NaN on history, so a history regime set is needed.

**Cells:** the two cells that replicated on h3 in `h3_replication`: **direction 2h** and **up-vs-down 6h**. The other
cells are skipped to save budget and avoid fishing.

**Design:**
- Existing r1 folds, M0v, families, global-shuffle gate and leak control.
- The ablation's full and baseline out-of-fold predictions are retained.
- Discovery = the first half of the test blocks; judgement = the later half (`later_ok`).
- Regimes, declared in code before the run (12 levels):
  - `liquidity_hist`: `ml_tf_log_notional_24h` terciles, cut on discovery rows;
  - `time_to_resolution`: `ml_log_hours_to_end` edges at 24h, 7d, 30d;
  - `trade_active`: `ml_tf_n_2h > 0`;
  - `price_extremity`: `mid_i` edges 0.1, 0.9.
- Interactions: the top 10 pairs by Friedman H² on discovery out-of-fold rows (features of M0v + flow), validated on
  judgement blocks by constrained versus free GBM.

**Family and counting:** `regime_study` cells (12 × 2 = 24) and `interaction_validation` pairs (10 × 2 = 20), with BY
over the cumulative count as `ml_explain` does. That is 44 tests, logged by the existing `ablation_trial` /
`provenance.append_trial` path with `revision: r5_regime_ix`.

**Stage-1 advance:** a cell or pair "demonstrated" on judgement blocks, or with one-sided p < 0.01 and the early sign
agreeing.

**Compute** (LightGBM single-thread, about 100k rows, 18 folds):
- Ablation plus placebos as r1 for 2 cells: about 1.5 h.
- Friedman H on discovery fold models: about 0.5 h.
- Interaction validation (10 pairs × about 9 judgement folds × constrained refits): about 1.5 h.
- Total about 4-6 h, 2 GB.

**Code** (`backend/scripts/run_ml_history.py`):
- New flags:
  - `--cells direction:1,updown:3` (restrict target kinds per horizon);
  - `--regimes`;
  - `--interactions N`;
  - `--discover-frac 0.5`;
  - `--frozen-from <results.json>` (J8).
- `ablate` keeps `_full_oof` and `_baseline_oof` when needed.
- Add `HISTORY_REGIMES` (in `ml_explain` next to `DECLARED_REGIMES`, with its own `regime_declaration_hash`).
  Discovery-only quantile cuts are stored in the results.
- Tests in `backend/tests/test_research_lab_ml_explain.py` style:
  - A planted interaction that acts only in the high-liquidity tercile is demonstrated in that cell on judgement
    blocks.
  - No planted effect gives no demonstration.
  - Tercile cuts depend on discovery rows only.
  - `--cells` runs only the declared cells.
  - `--frozen-from` reads pairs and cells exactly and does no discovery.

**Stop rule:** nothing advances → J8 exits 0 ("nothing to replicate"), and Q6 is closed for historical data ("no
regime or pairwise interaction beyond what M2F already uses").

### J8: Frozen replication of J7 on `h3_power` (q0013)

**Design:**
- `--frozen-from` the J7 results: the same 2 cells, the same regime definitions, and h2 discovery cuts applied
  unchanged.
- Advanced interaction pairs are judged on **all** h3 folds (no discovery on h3).
- Holm at 0.05 over the advanced set; weighted secondary (`sample_weight`).
- Uses the h3_replication subset (seed 7, 250k rows, the same 2,138 markets: a re-read, disclosed).
- Revision `h3_r5_rep`.

**Compute:** about 3-4 h, 2.5 GB.

**Code:** shared with J7.

**Stop rule:** zero replicated → close Q6 (historical). At least one replicated → a candidate interaction for an
MC1-style prospective registration (SEALED-P), after a challenger pass.

## 4. Draft queue specs

Paths follow `queue/README.md`: `argv[0]` is under `backend/scripts/`, and `cwd` is `backend`. Specs marked **needs
code** must not be committed to `queue/jobs/` until their code, tests and (for declared families) the reviewed freeze
commit exist.

### q0005 (runnable now)
```json
{
 "id": "q0005_leadlag_snap2h",
 "title": "SB2-J5: sibling lead-lag (L1 family) re-screen on 2h complete-universe snapshots",
 "family": "cross_market",
 "priority": 70,
 "expected_value": "Q4: powers up the inconclusive L1 screen (MDE 0.012 -> ~0.006) on a homogeneous 2h cadence; decides whether to retire Polymarket-internal related-market work",
 "data": ["research_lab/snapshots (complete captures up to run time; dev_snapshots_v2 absent on host)"],
 "resources": {"mem_mb": 2600, "cpu": 1},
 "depends_on": [],
 "argv": ["scripts/run_leadlag_screen.py", "--tag", "sb2-snap2h", "--n-boot", "1000", "--seed", "116"],
 "timeout_s": 21600,
 "max_retries": 1,
 "outputs": ["data-dumps/research_lab/leadlag_screen/leadlag-sb2-snap2h/results.json", "docs/research_lab/trials.jsonl (8 leadlag_screen lines)"],
 "next_action": "Claude session: apply the declared drafting rule, report the fresh-periods-only summary, ledger entry; retire or register per SCREENING_BATCH_2.md J5",
 "notes": "DEVELOPMENT; disclosed overlap with ~10 periods of leadlag-62d593a402; shares capture data with E011 (different hypothesis, its analysis untouched). Results written only at the end, so a retry after OOM is safe."
}
```

### q0006 (needs code: `bounce_decomp.py`, `run_bounce_decomp.py`)
```json
{
 "id": "q0006_bounce_snapshots",
 "title": "SB2-J4: bounce / quote-refill decomposition of the 2h reversal on prospective snapshots",
 "family": "microstructure",
 "priority": 72,
 "expected_value": "Q5: decides whether the E002/E004 reversal is last-trade bounce, one-sided quote refill or book-mid mean reversion",
 "data": ["research_lab/snapshots (complete captures up to run time)"],
 "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": [],
 "argv": ["scripts/run_bounce_decomp.py", "snapshots", "--tag", "sb2-snap", "--n-boot", "2000"],
 "timeout_s": 10800,
 "max_retries": 2,
 "outputs": ["data-dumps/research_lab/bounce_decomp/bounce-sb2-snap/results.json", "docs/research_lab/trials.jsonl (4 bounce_decomp lines + 1 ml_explain count line)"],
 "next_action": "Claude session: apply the J3/J4 verdict map, ledger entry; challenger pass if a mechanism claim is made",
 "notes": "exploratory_dev; Holm over P1-P4; leave-one-day-out range reported"
}
```

### q0007, q0008 (needs code: `battery2.py`, `run_hypothesis_battery2.py`; q0008 also needs the reviewed freeze commit)
```json
{
 "id": "q0007_hb2_features_h2",
 "title": "SB2-J1a: HB2 extension features on h2_main (relative-size flow, shift30)",
 "family": "flow",
 "priority": 68,
 "expected_value": "input for the HB2 screen (Q2/Q3/Q4)",
 "data": ["history/h2_main (trades, prices, panel)", "history/h2_main/battery1/features.parquet"],
 "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": [],
 "argv": ["scripts/run_hypothesis_battery2.py", "features", "--run-id", "h2_main"],
 "timeout_s": 10800,
 "max_retries": 2,
 "outputs": ["data-dumps/research_lab/history/h2_main/battery2/features2.parquet", "data-dumps/research_lab/history/h2_main/battery2/features2_shift30.parquet"],
 "next_action": "q0008",
 "notes": "no targets read"
}
```
```json
{
 "id": "q0008_hb2_run_h2",
 "title": "SB2-J1b: HB2 declared screen on h2_main (13 tests, Stage-1 gate, BY label, placebo)",
 "family": "flow",
 "priority": 68,
 "expected_value": "Q2/Q3/Q4/Q6: which moderators of flow and liquidity advance to frozen replication",
 "data": ["history/h2_main/battery1/features.parquet", "history/h2_main/battery2/features2*.parquet", "backend/astrolabe/research_lab/model_specs/hb2_v1.json"],
 "resources": {"mem_mb": 2000, "cpu": 1},
 "depends_on": ["q0007_hb2_features_h2"],
 "argv": ["scripts/run_hypothesis_battery2.py", "run", "--run-id", "h2_main", "--n-boot", "2000", "--threads", "1"],
 "timeout_s": 14400,
 "max_retries": 1,
 "outputs": ["data-dumps/research_lab/history/h2_main/battery2/results_hb2.json", "docs/research_lab/trials.jsonl (13 history_battery2 lines + count line + placebo lines)"],
 "next_action": "Claude session: record results; if F/L advanced, q0009-q0010 proceed; if X advanced, q0014-q0015",
 "notes": "refuses to run unless the committed hb2_v1.json hash equals the code's declaration hash; beyond the h2 revision budget, L1 only"
}
```

### q0009, q0010 (needs code: shared with J1)
```json
{
 "id": "q0009_hb2_features_h3",
 "title": "SB2-J2a: HB2 extension features on h3_power",
 "family": "flow",
 "priority": 66,
 "expected_value": "input for frozen replication",
 "data": ["history/h3_power (trades, prices, panel)", "history/h3_power/battery1_rep/features.parquet"],
 "resources": {"mem_mb": 2000, "cpu": 1},
 "depends_on": ["q0008_hb2_run_h2"],
 "argv": ["scripts/run_hypothesis_battery2.py", "features", "--run-id", "h3_power"],
 "timeout_s": 14400,
 "max_retries": 2,
 "outputs": ["data-dumps/research_lab/history/h3_power/battery2/features2*.parquet"],
 "next_action": "q0010",
 "notes": "exits 0 without work if results_hb2.json lists no advanced F/L test"
}
```
```json
{
 "id": "q0010_hb2_replicate_h3",
 "title": "SB2-J2b: frozen replication of advanced HB2 tests on h3_power (Holm)",
 "family": "flow",
 "priority": 66,
 "expected_value": "Q2/Q3: development-replicated or not; gate for any prospective registration",
 "data": ["history/h3_power/battery1_rep/features.parquet", "history/h3_power/battery2/features2*.parquet", "model_specs/hb2_v1.json", "history/h2_main/battery2/results_hb2.json"],
 "resources": {"mem_mb": 2000, "cpu": 1},
 "depends_on": ["q0009_hb2_features_h3"],
 "argv": ["scripts/run_hypothesis_battery2.py", "replicate", "--run-id", "h3_power", "--from", "h2_main", "--family", "F,L", "--n-boot", "2000"],
 "timeout_s": 10800,
 "max_retries": 1,
 "outputs": ["data-dumps/research_lab/history/h3_power/battery2/results_hb2_replication.json", "docs/research_lab/trials.jsonl"],
 "next_action": "Claude session: verdicts, costs in favourable tercile, ledger; registration draft only for replicated tests",
 "notes": "4th read of h3_power; frozen signs, scalings and cuts; weighted and without-66-shared-events secondaries"
}
```

### q0011 (needs code: shared with J4; waits for the book table)
```json
{
 "id": "q0011_book_bounce_depth_h2",
 "title": "SB2-J3: book-mid bounce decomposition (B1-B4) and depth-conditional flow (D1-D2) on h2 pmxt rows",
 "family": "microstructure",
 "priority": 58,
 "expected_value": "Q5 with true book-mid targets on history; Q3 depth moderation",
 "data": ["history/h2_main panel_H6h + battery features", "history_sources/book_features/book_features.csv.gz"],
 "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0003_books_finalize"],
 "argv": ["scripts/run_bounce_decomp.py", "book", "--run-id", "h2_main", "--tag", "sb2-book", "--n-boot", "2000"],
 "timeout_s": 7200,
 "max_retries": 1,
 "outputs": ["data-dumps/research_lab/bounce_decomp/bounce-sb2-book/results.json", "docs/research_lab/trials.jsonl (6 book_decomp lines + count line)"],
 "next_action": "Claude session: combine with J4 into the Q5 verdict; close the bounce family",
 "notes": "verdict 'unavailable' below 2,000 judgement rows or 100 events; h2-only, L1 ceiling"
}
```

### q0012, q0013 (needs code: `run_ml_history.py` flags, `HISTORY_REGIMES`)
```json
{
 "id": "q0012_ml_r5_regime_ix_h2",
 "title": "SB2-J7: ML regime study and interaction validation (r5_regime_ix) on h2_main, 2 cells",
 "family": "modelling",
 "priority": 56,
 "expected_value": "Q3/Q6 at model level: regimes where flow-augmented GBM beats M0v features; interactions beyond free-tree learning",
 "data": ["history/h2_main panel_H2h, panel_H6h"],
 "resources": {"mem_mb": 2000, "cpu": 1},
 "depends_on": [],
 "argv": ["scripts/run_ml_history.py", "--run-id", "h2_main", "--max-rows", "150000", "--horizons", "1,3", "--cells", "direction:1,updown:3", "--n-boot-ablation", "10000", "--regimes", "--interactions", "10", "--discover-frac", "0.5", "--revision", "r5_regime_ix"],
 "timeout_s": 43200,
 "max_retries": 1,
 "outputs": ["data-dumps/research_lab/history/h2_main/ml_history_results_r5_regime_ix.json", "docs/research_lab/trials.jsonl (ml_fit/ml_score/ml_explain lines, revision r5_regime_ix)"],
 "next_action": "q0013 (exits 0 if nothing advanced); Claude session: HISTORICAL_ML_DEV.md section",
 "notes": "beyond h2 revision budget; same subset, folds, seeds and 6-config grid as r1; do not run concurrently with q0004 (queue serialises)"
}
```
```json
{
 "id": "q0013_ml_r5_rep_h3",
 "title": "SB2-J8: frozen replication of r5 regimes/interactions on h3_power",
 "family": "modelling",
 "priority": 54,
 "expected_value": "Q6/Q7: whether any regime or interaction replicates on new markets",
 "data": ["history/h3_power panel_H2h, panel_H6h", "history/h2_main/ml_history_results_r5_regime_ix.json"],
 "resources": {"mem_mb": 2500, "cpu": 1},
 "depends_on": ["q0012_ml_r5_regime_ix_h2"],
 "argv": ["scripts/run_ml_history.py", "--run-id", "h3_power", "--max-rows", "250000", "--horizons", "1,3", "--cells", "direction:1,updown:3", "--n-boot-ablation", "10000", "--frozen-from", "../data-dumps/research_lab/history/h2_main/ml_history_results_r5_regime_ix.json", "--revision", "h3_r5_rep"],
 "timeout_s": 43200,
 "max_retries": 1,
 "outputs": ["data-dumps/research_lab/history/h3_power/ml_history_results_h3_r5_rep.json", "docs/research_lab/trials.jsonl"],
 "next_action": "Claude session: Holm verdicts; challenger pass before any registration draft",
 "notes": "no discovery on h3; re-read of the h3_replication subset (seed 7), disclosed"
}
```

### q0014, q0015 (needs code: `battery2` siblings path; conditional)
```json
{
 "id": "q0014_h3_siblings_fetch",
 "title": "SB2-J6a: Gamma event metadata + sibling price series for h3_power (only if an X test advanced)",
 "family": "cross_market",
 "priority": 50,
 "expected_value": "enables frozen replication of stale-follower diffusion (Q4)",
 "data": ["history/h3_power/sample.csv.gz", "history/h2_main/battery2/results_hb2.json"],
 "resources": {"mem_mb": 800, "cpu": 1, "network": "gamma-api.polymarket.com, clob.polymarket.com"},
 "depends_on": ["q0008_hb2_run_h2"],
 "argv": ["scripts/run_hypothesis_battery2.py", "siblings", "--run-id", "h3_power", "--rps", "4"],
 "timeout_s": 14400,
 "max_retries": 3,
 "outputs": ["data-dumps/research_lab/history/h3_power/battery2/{events_meta.jsonl.gz,siblings/,sibling_columns.parquet}"],
 "next_action": "q0015",
 "notes": "exits 0 'skipped: no X advanced' otherwise; resumable; yields to the collector pass (live_check); no outcomes stored"
}
```
```json
{
 "id": "q0015_hb2x_replicate_h3",
 "title": "SB2-J6b: frozen replication of advanced X tests on h3_power (Holm)",
 "family": "cross_market",
 "priority": 50,
 "expected_value": "Q4 on history: replicate or retire stale-follower diffusion",
 "data": ["h3_power battery features + sibling_columns", "model_specs/hb2_v1.json"],
 "resources": {"mem_mb": 1500, "cpu": 1},
 "depends_on": ["q0014_h3_siblings_fetch", "q0009_hb2_features_h3"],
 "argv": ["scripts/run_hypothesis_battery2.py", "replicate", "--run-id", "h3_power", "--from", "h2_main", "--family", "X", "--n-boot", "2000"],
 "timeout_s": 7200,
 "max_retries": 1,
 "outputs": ["data-dumps/research_lab/history/h3_power/battery2/results_hb2_replication_x.json", "docs/research_lab/trials.jsonl"],
 "next_action": "Claude session: combine with J5 into the Q4 verdict",
 "notes": "exits 0 if no X advanced"
}
```

## 5. Test budget

| Job | Tests counted | Kind(s) |
|---|---|---|
| J5 | 8 | `leadlag_screen` |
| J4 | 4 | `bounce_decomp` + count line |
| J1 | 13 | `history_battery2` + count line |
| J2 | ≤ 10 (advanced F/L only) | `history_battery2_replication` + count line |
| J3 | 6 | `book_decomp` + count line |
| J7 | 44 | `ml_explain` (regime cells, pairs) |
| J8 | ≤ 44 (advanced only) | `ml_explain` |
| J6 | ≤ 3 | `history_battery2_replication` |
| **Total** | **about 80-130** | |

The cumulative count is about 670 now (corrected local recount; the host is higher because of automatic `flow_screen`
lines). After this batch it will be about 750-800. The automatic `flow_screen` lines, about 50 per day, inflate the BY
denominator for every later screen. That is a governance question for the coordinator; this batch only records it.

## 6. Main scientific risks

1. **Series semantics.**
   - Every history target is the mid-like `prices-history` series. A flow moderator can be a moderator of the series'
     lag behind trades (r3), not of the market.
   - J3 (book-mid targets) and J4 (Gamma mids) are the only checks. A replicated F/L effect stays "flow–series
     continuation" until a prospective Gamma/book-mid test.
2. **Worn data.**
   - h2 is far over its revision budget, and the flow family has been seen several times there.
   - h3 shares the calendar, so market-wide shocks replicate too. Replication on h3 is not a new time period.
   - Only SEALED-P and SEALED-H4 can confirm.
3. **Collinear moderators.** Liquidity, trade count, the spread proxy and volatility are strongly correlated (F1, F2,
   F4, F5, F8). Several may advance for one underlying reason. Interpret them jointly; do not register more than one per
   mechanism.
4. **Power.** The MDE is about 2/3 of the main flow effect per SD of moderator, so modest moderation is invisible. X
   (neg-risk siblings), D (pmxt rows) and J3 may be underpowered, and a null there is not absence.
5. **Look-ahead and coverage.**
   - `hours_to_end` uses the end date listed at fetch time (F3, `time_to_resolution` regime).
   - The pmxt `no_book` state correlates with illiquidity, so book-row samples skew liquid.
   - Trade truncation makes busy windows NaN.
6. **Snapshot jobs.**
   - About 5 calendar days, so day-level shocks cannot be clustered (jackknife range only).
   - They share captures with E011 (different hypothesis, analysis untouched).
   - `oneHourPriceChange`'s basis is unknown.
   - J5 may hit memory limits.
7. **ML selection.**
   - Friedman H rankings are unstable.
   - Tercile cuts and discovery blocks are single choices.
   - Interaction "value" against a constrained GBM can reflect the constraint's cost rather than a real interaction.
     J8's frozen replication is the guard.
8. **Counting.** The HB1 undercount in `battery.prior_test_count()` must be fixed in the new counter, or the BY labels
   of this batch are anti-conservative.

## 7. Next actions

1. Deploy **q0005** (runnable now) with the next deploy. It slots between q0002 chunks (priority 70 above 60).
2. Delegate to `implementer`, in this order:
   - `bounce_decomp.py` with `run_bounce_decomp.py` and tests (J4, J3);
   - `battery2.py` with `run_hypothesis_battery2.py` and tests (J1, J2, J6);
   - the `run_ml_history.py` flags and `HISTORY_REGIMES` (J7, J8).
3. For each declared family (J1, J3, J4, J7): dry run on permuted targets, then a `science-reviewer` pass on this file's
   family section, then commit the declaration hash and spec. Only then commit the matching queue specs and deploy.
4. After results: ledger entries, study-doc sections, verdicts against the stop rules in §2-§3, and the dashboard.

---

## Challenger review, round 1 (science-reviewer, 2026-10-15 ~19:05Z): ACCEPT_WITH_REQUIRED_CHANGES

This draft is NOT frozen. Every required change below must be applied, and noted as addressed, before any batch-2 code is
written or any batch-2 job is queued. After that comes one response round (mission §6): reject, revise or proceed.
Do not start an endless review loop.

### Required changes
1. **Cumulative test count.** `battery.py:1269` skips `source=="hypothesis_battery_1"`. The local recount is 598 + 72 = 670.
   - The proposed counter still omits these non-placebo kinds:
     - `econ_conditions_*` (n_tests 95);
     - `history_cross_venue` (82 lines);
     - `surprise_detector` (46);
     - `history_battery_posthoc` (5);
     - `history_resolution_dev`;
     - `history_case_*`.
   - `ml_explain.prior_ml_explain_tests()` returns 212, because 165 unsourced lines carry only `m_tests` (`provenance.py:92-97`).
   - Fix: list every non-placebo trial kind with its contribution, or exclude it with a written reason. Pass the same total as
     `prior_tests` into `regime_study` and `interaction_validation` (J7). Add a unit test against the real `trials.jsonl` kinds.
2. **J7/J8.** The cells were chosen on h3 results (`HISTORICAL_ML_DEV.md:262-264`) and are then "replicated" on the same h3 subset
   (seed 7, 2,138 markets). Choose the cells from h2 results only, or report J8 as non-independent.
3. **J7 regime tests do not answer Q3.** `regime_study` (`ml_explain.py:843-870`) tests the full model against the baseline within
   each regime, so cells pass by construction. Declare tests of differences between regimes instead.
4. **J4 cannot separate genuine reversion from Gamma quote noise.** P1 regresses `mid_j−mid_i` on `mid_i−mid_h`, and a
   transient error in `mid_i` gives P1 < 0 either way. Fix: measure the mid at i independently (a CLOB book sweep at the same
   time), or relabel P1. Do not "close Q5" on J4.
5. **J4 needs a declared P1-P4 verdict map.** "0 = pure bounce" needs an equivalence bound, not just failure to reject.
6. **J4 rests on about 5 calendar days.** Make the leave-one-day-out sign agreement binding (for example, all 5 days).
7. **J4 `b_pos`:** Gamma `last_trade_price` has no timestamp. Restrict to markets with recent trades, or report how many rows
   are affected as a limitation.
8. **Disclose overlaps with earlier work:**
   - F1/F8 overlap IX3 (`battery.py:2220`);
   - L1 duplicates E001 B3 `chg1d_x_logliq` (`panel.py:28`);
   - J4 overlaps HB1 C3 (MI2/MI6, `HYPOTHESIS_BATTERY_1.md:563-571`), E006 H1 and the B3 feature `ltp_minus_mid`.
   - The claim "none tested except F3, F6" is false.
9. **F3 and the `time_to_resolution` regime use the end date at fetch time (look-ahead).** Add a declared sensitivity that
   drops markets whose `closed_time` is well before `end_at` (`history_backfill.py:341`).
10. **h3 reads.** J2, J6 and J8 are reads 4, 5 and 6. Reconcile this with the FDP ≤3-reads rule (`FEATURE_DISCOVERY_PROGRAMME.md` §3).
11. **J5:**
    - add a gap filter, because `build_all` has none (`leadlag_screen.py:341`): the 10h outage and the 0.1-3.4h periods
      from 10-10/11 enter;
    - the √(14/57) MDE scaling assumes independent periods;
    - L3 met the rule with ΔR² ≈ 0.0002, so declare a materiality floor before running.
12. **Small fixes:**
    - J2 power: Holm with k≤5, while §5 allows ≤10.
    - The MDE is about 70-90% of FL2, not 2/3.
    - The J3 −0.2 benchmark mixes horizons.
    - Make `T_seal` unambiguous when families freeze separately.
    - Pick the "favourable tercile" on h2 only.
    - The F7 30-day `q80` needs full lookback coverage.

### Optional
- Add a ledger methods note for the two-stage rule (Stage-1 p<0.01, then Holm on h3).
- Report counts where J3's target is unavailable, by liquidity.

### Could not verify (host-side)
- The 59 captures.
- The host `trials.jsonl` count.
- Whether `MemAvailable` reaches 3.8 GB for q0005.
- The CPU-hour estimates.
