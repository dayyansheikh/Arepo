# Live tests 4 (LT4): E020-E024, DRAFT pre-registrations

**Status: DRAFT, not registered, nothing counted.** Drafted 2026-10-20 on branch `feat/live-tests-4` from the research tip
`fe54ef20`. E-numbers are provisional; they are assigned at registration. Before registration this needs: the input seal
for the capture censuses, the pre-registration censuses (section 8, counts only, worn pre-window data), a challenger
review (`science-reviewer`) of this file and later of the code, the fixes, the size check at >= 2,000 worlds, the
`SPEC_SHA256` and code-hash pin, the ledger entry (section 12) and the reader's installation. Until the pin exists, every
line the reader writes is `prospective_unregistered` by construction.

This is research tooling. No edge, calibration, profitability or tradability claim exists or is implied. Every count
quoted from round 9/10 probes is a **counts-only development figure on worn data**. Every MDE here is a **planning
estimate** built on stated assumptions, not a measurement.

Source ideas: `CREATIVE_HYPOTHESES_2026-10-24.md` (round 10) top five: CH169, CH170, CH174, CH171, CH173. The design is
built from the start to the LT2 round-1 faults (`LIVE_TESTS_3.md` 1.12) and the LT3 round-1 and freeze-check lessons
(`LIVE_TESTS_3.md` 13), listed in section 1.0. It reuses the LT3 reader and estimator code by import (section 9), and
it never opens the LT2 or LT3 stores.

## 0. Summary

| ID | Idea | Hypothesis (direction) | Population | Primary | Planning MDE (estimate; Holm worst case, k = 5) | Floor |
|---|---|---|---|---|---|---|
| **E020** | CH169 | After a one-sided quote-only 2 h move, the **unmoved** side follows (ratifies) more when the move was an **arrival** (spread narrowed) than a **cancellation** (spread widened) (one-sided, > 0) | non-sports, complete captures | expanding-past demeaned OLS of `r = s · (U_{k+1} − U_k)` on 1[arrival] | **about 0.12-0.17c** (to about 0.3c) | 0.5c |
| **E021** | CH170 | Within a market, a **fresh** traded move (last trade <= 15 min before the capture) continues less over 2 h than a **settled** one (last trade >= 60 min before) (one-sided, < 0) | all categories (sports split reported), active-frame trade samples + captures | expanding-past demeaned OLS of `c` on 1[fresh] | **about 0.29-0.54c** (borderline; census-gated) | 0.5c |
| **E022** | CH174 | Within a market, a traded move made when the **displayed** liquidity is large relative to the executable near-touch depth (a **hollow** book) continues less over the next pass (one-sided, < 0) | non-sports, captures + sweep 1 | expanding-past demeaned OLS of the sweep-to-sweep continuation `c_sw` on `zh`, real depth held fixed | **about 0.08-0.16c per SD** (tercile-equivalent about 0.17-0.34c) | 0.5c (tercile) |
| **E023** | CH171 | 6 h taker flow continues more when more of it was **opening** (BUY) rather than closing (SELL): slope of `x6 · zOP` > 0 | all categories, trade samples + captures | E016-form expanding-past demeaned OLS plus the distant-donor gate | **about 0.0020-0.0036 per SD** (VIF-adjusted; census-gated) | gross 0.5c in the favourable cell |
| **E024** | CH173 | 6 h taker flow continues more when it is **concentrated** in one order: slope of `x6 · zC` > 0, `C` = largest row's notional share | all categories, >= 3 signed rows | as E023, with `x6·zW`, `x6·zH` held fixed | **about 0.0022-0.0046 per SD** (VIF-adjusted; census-gated, may drop) | gross 0.5c |

- **Family:** one Holm family over the k primaries, one-sided, familywise alpha 0.05, separate from E009-E011, LT2
  (E012-E014) and LT3 (E015-E019). **k = 5** if every census gate in section 8 passes; a test whose gate fails is dropped
  *before* registration, uncounted, and k is the number that survive. k is fixed in the spec (`k_tests`) at registration
  and never changes. A primary that is unavailable or fails its gate enters Holm with p = 1.
- **Dropped or narrowed at design (uncounted; section 7):** CH171's two-leg slope difference narrowed to the open-share
  moderator (the two-leg regression is secondary S1); CH174's target moved to the decision-time sweep (the round-10 target
  started before the state was observed) and real depth held fixed; CH170 widened to all categories on the trade-sample
  stream (power; the flow family's convention); CH172, CH177, CH178, CH179, CH175, CH176 not taken (7.2).
- **Window:** whole captures with start in `[REGISTERED_UTC, END_UTC)`, 21 days. Proposed `REGISTERED_UTC =
  2026-10-26T00:00:00Z`, `END_UTC = 2026-11-16T00:00:00Z`. Single analysis on or after `2026-11-17T12:00:00Z`.

## 1. Common rules

### 1.0 Lessons carried over from LT2/LT3 (binding from the first draft)

| # | Lesson (source) | LT4 rule |
|---|---|---|
| L1 | Exact float writes (LT3 freeze fix 1; LT2 fix F: `%.7g`/`%.6g` rounded epochs by 1,000-10,000 s) | `write_once_csv` writes `float_format="%.17g"`; the analysis reads frozen and outcome files with `float_precision="round_trip"`, so values come back exactly (unit test). Reads inside the imported LT3 helpers use pandas' default parser, which can differ by 1 ulp (13.2) |
| L2 | NaN refusals (LT3 fix 2) | a pinned spec with a null **or NaN** census value (`vol24_cap`, any scale, any cut, `k_tests`) is refused; every census gate item that depends on a NaN fails closed |
| L3 | Census input identity (LT3 R1 finding 3) | every census input file is named in a seal with its sha256 (captures and sweeps: `seals/lt4_census_inputs_captures.json`; samples: the LT3 C2 seal, the same 23 samples); the census re-hashes each file and **refuses** a mismatch or an unsealed file |
| L4 | Planning-MDE <= floor gate in every census (LT3 fix 4) | each test's census gate includes its pessimistic planning MDE, recomputed on the census-projected effective counts, at or below the floor (section 8) |
| L5 | Simulated-null gate size (LT3 13.5, fix 3) | `size-check` on the code to be pinned, >= 2,000 worlds per scenario, criterion rate <= 0.05 + 1.645 sqrt(0.0475 / worlds) = 0.058; seven scenarios including the two new ones (continuous-label permutation; donor gate with a correlated true moderator held as a control) |
| L6 | Dry-run guards (LT3 fix 5) | `run --dry-run-start` refuses the live root (exit 2); `allow_late` is refused with a pinned spec; `load_spec` refuses a spec whose dates differ from the module constants |
| L7 | Spec and code pins (LT2 fault 6) | the spec pins `code_sha256` of `live_tests4.py`, `live_tests4_analysis.py` **and the imported `live_tests3.py`, `live_tests3_analysis.py`** (normalised: the `SPEC_SHA256` line excluded); every frozen line carries `spec_sha` and `code_sha` (16 hex of the joint reader hash); the analysis keeps only matching lines and refuses a pinned spec with an unfilled or mismatched map |
| L8 | Per-capture status files (LT2 fault 3, LT3 1.5) | the reader writes its own `series/` and `status/` per capture and a status for every unit at every target, write-once, online; the analysis never needs raw captures, sweeps or samples |
| L9 | Skip-slot targets where bounce contaminates (round 10 lesson 5; LT2/LT3 bounce critiques) | E020's primary reads the **unmoved** side; E021's primary *is* the bounce clock, with the skip-slot target as a binding label; E022's target starts at the decision-time sweep; flow tests keep LT3's early-ending-window label |
| L10 | Clustering (LT2 R1 finding 5; LT3 R1 finding 2) | CR1 on event, two-way event x UTC day and UTC day; **p = max(p_event on t with G_event − 1 df, p_two-way, p_day on t with G_day − 1 df)**; the conservative CI is the hull of the event bootstrap and each of the three Wald intervals |
| L11 | Holm over k, counting once (M3) | one trials line, kind `live_tests4`, `n_tests = k` (fail-closed `battery2.KIND_RULES` entry added; unit test) |
| L12 | Economics never changes a verdict (LT2/LT3 1.10) | paper taker round trips at recorded touches, event-clustered, reported separately; maker routes "gross, no fills" |
| L13 | No both-class inclusion rule (LT2 fault 4) | expanding-past demeaning over all eligible units; both-class counts are census descriptives only |
| L14 | Readers run at the pass cadence (LT3 R1 finding 3; round 10 lesson 6) | trade samples are consumed online (3-day host retention); the reader runs every 20 min |
| L15 | Run lock (LT3 ruling 6) | an internal non-blocking `flock` on `live_tests4/run.lock`; a second reader returns `locked`, exit 75 |

### 1.1 Registration, window, single analysis
- `REGISTERED_UTC` is the first 00:00Z that is **at least 24 h after the LT4 registration commit** (spec pin plus ledger
  entry) **and at least 48 h after LT3's `REGISTERED_UTC`**, never earlier than 2026-10-26T00:00Z. The proposed value is
  **2026-10-26T00:00Z** (LT3 proposes 2026-10-24T00:00Z). If either commit slips, `REGISTERED_UTC` moves to the next
  qualifying 00:00Z, `END_UTC = REGISTERED_UTC + 21 d` and the analysis date `END_UTC + 36 h`. The rule uses no data;
  the move is recorded in the ledger (as LT2 1.1 and LT3 1.1).
- **Window membership is by capture start** (`capture_start_utc`), whole captures in or out. The origin of every unit is
  its own row's `received_utc` (E022: the sweep-1 receipt; section 1.3).
- **Fixed end, no extension.** Round 10's counts-triggered 28-day extension is not adopted (one more researcher degree of
  freedom). Shortfalls are labelled, not extended.
- **One analysis**, once, on or after the analysis date (`run_live_tests4.py analyze` refuses before it; `--out` refuses to
  overwrite). No interim look at any outcome (1.6).
- **Effective start** = max(`REGISTERED_UTC`, the first capture processed by the reader at the pinned commit). The analysis
  keeps only lines whose `spec_sha` and `code_sha` equal the pins and whose role is `prospective_confirmation`.

### 1.2 Streams read (all already written by the host's pass; nothing new is fetched)
- **Complete-universe captures** `snapshots/<id>/rows.csv.gz` (every 2 h at :31; `state=complete` only): LT3's columns plus
  Gamma `liquidity` (E022).
- **Sidecar** `rows_ext.csv.gz`: LT3's columns plus `rewards_min_size`, `rewards_max_spread` (E020 reward flag). A missing
  sidecar sets `sports = −1` (excluded wherever the category is needed), counted.
- **Book sweep 1 of the same pass** `book_sweeps/<id>/` (`series_index` 0): outcome-0 token `best_bid`, `best_ask`,
  `bid_size_1`, `ask_size_1`, `depth_bid_5c`, `depth_ask_5c`, `min_order_size`, `batch_receipt_utc`. E022's state and
  target; E020's and E021's mechanism readings.
- **Active-frame trade sample of the same pass** `trade_samples/<id>/` (`manifest.json`, `features.csv.gz`, `trades.csv.gz`):
  E021, E023, E024. Wallet fields are never read.
- **Not read:** the live large-trade monitor, the cross-venue stream (sealed to 2026-11-03), `surprise_live/` (E011),
  `live_tests2/`, `live_tests3/`, CB8-H holders, CB16/CB17 stores, Gamma outcome fields of any kind.

### 1.3 Clocks, slots and decision times
- **Slots:** as LT3 (`grid0 = 2026-10-01T00:31Z`, 2 h, tolerance 30 min, first complete capture of a slot). "k − 1" and
  "k + h" are slots, not file order. Target slots: k + 1 (2 h), k + 3 (6 h, skip and flow targets).
- **Decision time per test.** E020: capture k's row `received_utc` (states from captures k − 1, k). E021: the trade sample's
  receipt (after capture k); the state uses capture rows k − 1, k and trade rows with `ts < t_k` only, so the state is
  determined by information public at `t_k`. E022: sweep 1 of pass k (`batch_receipt_utc`, minutes after capture k); the
  state uses capture k, k − 1 and sweep 1 of pass k only, **and the target starts at that sweep**. E023/E024: `origin_utc`
  of the sample (the capture row's receipt), trade rows `ts < t` only.
- **Late rule:** a frozen file must be written before its earliest target slot can start (`now < slot time − 60 s`),
  otherwise a `.late` marker is written and the units are lost (counted). At analysis, a line whose `frozen_utc` is not
  strictly before the start of its target capture is excluded and counted. If late-refused origin files exceed 2% of a
  test's origin files, the result carries *late-loss (x%)*.

### 1.4 Shared origin-side eligibility (a move unit at capture k; E020, E021, E022)
Applied in this order, each exclusion counted (LT3's `move_join` and `classify`, imported):
1. `binary == 1`, not closed, active, at k − 1 and k (the series holds only such rows).
2. Two-sided at k − 1 and k (`0 < bid < ask <= 1`).
3. Tight at k − 1 and k: spread (Gamma `spread`, else ask − bid) <= 0.10.
4. `mid_k` in [0.02, 0.98].
5. As-of end date: unknown or > `t` + 3 h.
6. Category from `cb17_census.is_sports_sidecar` on the sidecar of k (sports = −1 if missing). E020 and E022: non-sports
   primaries, sports arm reported uncounted. E021: all categories (section 3), sports split reported.
7. One row per `condition_id` (first in page order).
8. `|x| >= 0.01`, `x = mid_k − mid_{k−1}`; class and geometry by LT3's `classify` (never-traded, traded, ambiguous,
   quote-only; parallel, one-sided, spread-change, same-side-unequal).

### 1.5 Missing data and per-capture status (never imputed)
- At every target, each frozen unit receives exactly one status: `two_sided`, `one_sided`, `closed_flag`, `absent`
  or `capture_missing` (series targets), and for sweep targets `two_sided`, `one_sided`, `absent`, `capture_missing`
  (LT3's `outcome_h`/`outcome_s`, imported). Written write-once, online.
- Only `two_sided` units have a target. Other statuses are counted by class and test.
- **Attrition rule (per test):** with `a_1`, `a_0` the non-`two_sided` shares (excluding `capture_missing`) of the two
  contrasted classes (E022-E024: upper versus lower half of the moderator), if `|a_1 − a_0| > 2` pp the result carries
  *attrition-differential* and Lee-type trimming bounds are reported (LT3's `lee_bounds`). The verdict is not changed.
- A required input missing at the origin (sidecar, sweep, sample, previous slot) produces no unit and is counted
  (`sidecar_missing`, `.nosweep`, `.noprev`, sample absent). A missing moderator or state is NaN (excluded, counted), never 0.

### 1.6 What is not looked at before the analysis date
- No mid, move, target, P&L, regression or plot from `live_tests4/` files, or from in-window captures, sweeps or samples,
  for these hypotheses. Only `run_live_tests4.py ops-stats` may run: file, line, role, class and status counts. It reads no
  price column (enforced by a unit test).
- No change of thresholds, scales, populations, estimators or k after registration. Operational fixes are logged as
  deviations.

### 1.7 Estimators and inference
- **Expanding-past demeaning** (J4-R; LT2 E012/E013, LT3 E015/E016/E018/E019) for all five primaries: every regressor (the
  tested term and every control) minus the mean of the market's strictly earlier units; target raw; the first unit of each
  market drops. No inclusion rule reads later units.
- **Standard errors and p (rule L10):** CR1 on (a) event, (b) two-way event x UTC day of the origin, (c) UTC day. One-sided
  **p = max(p_event with a t reference on G_event − 1 df, p_two-way with a normal reference, p_day with a t reference on
  G_day − 1 df)**. The conservative 95% CI is the hull of a 2,000-draw event bootstrap CI and `beta ± q · SE` for each of
  the three SEs (q = t_{G−1, 0.975} for event and day, 1.96 for two-way). Two-day blocks are reported as a sensitivity for
  the 6 h targets.
- Controls are listed per test; all origin-side and demeaned the same way.

### 1.8 Gates (valid within-unit nulls) and their size
- **E020, E021: label permutation gate** (LT3 `perm_gate`): 200 draws; the class label permuted within market x UTC day,
  target and controls attached; estimator re-run. Passes if `p_perm < 0.05`. Strata with < 4 contrasted units are not
  permuted (counted). A check on the clustered SEs, not a mechanism control.
- **E022: continuous-label permutation gate** (the same function, the term `zh` permuted within market x UTC day).
- **E023, E024: distant-donor gate** (LT3 `donor_gate`): markets with >= 4 usable units; every unit's moderator replaced in
  the interaction and the main effect by a same-market donor's moderator at least 12 h away (6 h flow + 6 h horizon);
  units with < 2 donors keep their own (counted).
- A failed gate gives p = 1 in Holm and the label "SE check failed" (E020-E022) or "within-unit timing not shown"
  (E023, E024).
- **Size check (L5):** `size-check` runs seven scenarios with no effect: binary permutation (iid; persistent market rates),
  continuous permutation (persistent moderator level and AR(1) within market), donor (iid; AR(1) 0.6; life cycle) and donor
  with a correlated true moderator (a control moderator `zA` with a real `x6·zA` effect, the tested moderator correlated 0.4
  with it, `x6·zA` and `zA` in the controls). Criterion: rate <= 0.058 at 2,000 worlds; a failing scenario blocks the pin.

### 1.9 Verdicts and labels (per primary, after Holm over k)
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate in the predicted direction, gate passed.
- **Contradicted:** the conservative 95% CI lies entirely on the other side of 0.
- **Inconclusive:** otherwise. **Unavailable:** below the test's floor counts, or fewer than 10 UTC days with units.
- **Labels (never change a verdict):** *material* (E020/E021 point estimate at or above 0.5c; E022 the tercile contrast
  at or above 0.5c; E023/E024 the gross favourable-cell move at or above 0.5c); *underpowered* (Inconclusive and the
  realised `(t_{G−1, 1−0.05/k} + t_{G−1, 0.8}) · SE_day` above the reference); *attrition-differential*; *late-loss*;
  *coverage-limited* (E021 unclocked-truncated > 2%; E023/E024 truncated > 3%); *series-concentrated* (one series family
  > 50% of a primary's units); per-test mechanism labels.

### 1.10 Economics (separate; never changes a verdict)
- Paper taker round trip per share at the recorded touches, fees on both legs from the origin sidecar
  (`economics.fee_spec`, `resolve_rate(..., "max_if_unknown")`, `rate · (p(1 − p))^exponent`), LT3's `paper_taker` and
  `econ` (event-clustered mean, one-sided p, >= 30 trades in >= 10 events). No depth, queue or latency: optimistic.
- Maker routes: gross mid-to-mid or quote-to-quote move of the cell only, "gross, no fills".
- **Declared in advance:** every AREPO taker cost check has failed (E004 −4.5c touch-to-touch; E007 +0.36c gross against
  about 4.5c; 0 of 95 economic cells positive). "Not shown" is the expected outcome.

### 1.11 Overlaps, dependence and counting
- **Within LT4:** E023 and E024 share every trade sample, origin and target (as E016/E018 did). E020 and E022 read the same
  captures but disjoint classes (quote-only one-sided versus traded). E021 and E022 both contain traded movers, in
  different populations (sampled, all categories; universe, non-sports) and with different states. All in one Holm family;
  never counted as independent confirmations.
- **Against LT2/LT3 primaries (no double count):**

  | LT4 | Closest LT2/LT3 primary | Same data? | Same contrast? | Why not a double count |
  |---|---|---|---|---|
  | E020 | E015 (parallel quote-only vs traded, 2 h `c`) | yes (captures) | no | E020's units are the **one-sided** quote-only class, which E015's primary excludes (its S1 secondary); the target is the unmoved side, not the mid |
  | E021 | E015 | partly (traded movers in the active frame) | no | E015 contrasts traded with parallel; E021 contrasts traded with traded by the last trade's age |
  | E022 | E015 M1 (sweep target) | traded units overlap | no | E022's state (display versus depth) is not an LT2/LT3 variable |
  | E023 | E013 (F4/F5), E016, E018 | yes (trade samples, `x6`, `y6`) | no | a new moderator (open share); `x6·zW`, `x6·zH` are not re-tested |
  | E024 | E016, E018 | yes | no | a new moderator (concentration); W and H interactions are **controls**, and the census drops E024 if `|corr(zC, zW)|` or `|corr(zC, zH)|` > 0.5 |

- **Collection overlap (disclosed):** LT2 (to 2026-11-12), LT3 (to 2026-11-14), E011 (to 2026-11-10), CB-batch SEALED-P
  windows. Different hypotheses, no pooling, no store opened by another test.
- **Counting (M3):** the analysis adds **k counted tests**, one per primary, kind `live_tests4`. Gate draws, secondaries,
  mechanism readings, economics and censuses count 0. The cumulative count is recorded at registration and at analysis.

## 2. E020: arrivals versus cancellations (CH169)

- **Hypothesis and mechanism.** With no trade in the interval (E015's quote-only class), a one-sided quote move is an order
  event: if the spread narrowed, an order **arrived** inside the spread (a patient trader; Rosu 2009; Hollifield, Miller and
  Sandas 2004); if it widened, an order was **cancelled** (a maker withdrawing a free option; Copeland and Galai 1983). The
  unmoved side's makers ratify an arrival (they follow the new order) and ignore a cancellation (the side is re-posted and
  the mid halves back: Roll's bounce). **Direction: D_AC > 0, one-sided.**
- **Unit.** Non-sports market x capture k passing 1.4 with class `quote_only`, geometry `one_sided`, `|x| >= 0.01`.
- **Origin-side filters (in order, counted):** 1.4 items 1-8; tick known at k − 1 and k and equal (a tick-regime flip at
  0.96/0.04 changes the grid; excluded); the moved side identified (`|db| > |da|` → bid moved, else ask moved).
- **Labels (frozen).** `arrival` = `(ask_k − bid_k) < (ask_{k−1} − bid_{k−1}) − 1e-9`; `cancellation` = widened by more than
  1e-9 (a one-sided move with |x| >= 1c always changes the spread by 2|x|). `U` = the **unmoved** side's quote (the ask if
  the bid moved, else the bid). `s = sign(x)`.
- **Target (exact).** `r = s · (U_{k+1} − U_k)`, `U_{k+1}` from the series of the capture in slot k + 1 (Gamma quotes;
  status `two_sided` at k + 1; tightness at k + 1 not required, j-tight a sensitivity). Horizon 2 h. The moving side's own
  return (the bounce) cannot enter `r`.
- **Primary statistic.** Expanding-past demeaned OLS of `r` on `AR = 1[arrival]` over arrivals and cancellations, ordered by
  origin within market, controls: `spread_{k−1}` (the pre-move spread, demeaned within market: how far the book already
  was from its own norm), `log |x|`, logit `mid_k`, `|mid_k − 0.5|`, `log1p volume24hr_k`, log hours-to-end (unknown → 0
  with a flag), reward flag (`rewards_max_spread > 0`). Inference 1.7; seed 20261030. Gate: label permutation (1.8), seed
  20261130.
- **Why `spread_k` is not a control (found in the synthetic test).** For a one-sided move `spread_k − spread_{k−1} = ∓2|x|`
  exactly: the spread change *is* the label. With both spreads (and `|x|`) controlled, the label is nearly collinear with
  the controls (exactly so when `|x|` is constant). The both-spreads model is a reported sensitivity
  (`sensitivity_spread_k_control`). The mechanical spread-reversion channel (an arrival leaves the spread below its norm,
  a cancellation above it, and either can be undone by the unmoved side) is therefore *not* removed by a control; it is
  read by M2 (below) and is question 1 for the challenger.
- **Mechanism readings (pre-declared label rules).** M1: the same estimator with the sweep target `r_sw = s · (U^sw_{k+1} −
  U^sw_k)` (sweep 1 of passes k and k + 1, the CLOB book). If E020 is Supported and M1 is below 50% of D_AC or its one-sided
  p >= 0.05: label **Gamma-quote mechanics**. M2: the skip-slot persistence `r_skip = s · (U_{k+3} − U_{k+1})`. If E020 is
  Supported and M2 is significantly negative (one-sided p < 0.05 for < 0: the unmoved side gives the ratification back):
  label **transient (spread-reversion mechanics)**.
- **Secondaries (descriptive, not counted).** S1 E015's mid target `c = s · (mid_{k+1} − mid_k)` by class; S2 the sized split
  (sweep 1 of pass k: the new touch's size >= 2 x `min_order_size` = a real order, else dust; CH80); S3 reward versus
  non-reward markets; S4 the |x| dose (1-2c, 2-5c, >= 5c); S5 the sports arm; S6 counts by class and side.
- **Planning MDE (estimate).** Source: round 10 fact 2 (P1b, four non-sports intervals on 2026-10-15): about 6,600 one-sided
  non-sports quote-only movers a day, about 138,600 in 21 days. Assumptions: about 70% survive the tick and side filters and
  the first-unit drop (about 97,000); a 40/60 arrival/cancellation split (unprobed; the census replaces it): 38,800 and
  58,200; SD of `r` 3c (round 9/10's one-side 2 h assumption); event design effect 2-3; day factor 1.3-1.5. `SE = 3c ·
  sqrt(1/38,800 + 1/58,200) · sqrt(2..3) · (1.3..1.5)` = 0.036-0.051c; `MDE = (t_{20, 0.99} + t_{20, 0.8}) · SE = 3.388 · SE`
  = **0.12-0.17c**; 0.24c at a 15/85 split and 0.32c with SD 4c. The 0.5c floor binds.
- **Floors (Unavailable):** < 5,000 arrivals, < 5,000 cancellations, < 300 events, < 10 days.
- **Economics.** (a) Reported: taker fade of cancellations with `|x| >= 0.03` (direction −s), entry at the k touch, exit at the
  k + 1 touch, fees both legs, against about 4.5c median (1.8c liquid). (b) Maker: gross `r` by class, "gross, no fills".
- **Missing data.** Sidecar missing → sports −1 (excluded, counted); tick unknown → excluded (counted); previous slot missing
  → `.noprev` (counted); target statuses per 1.5.

## 3. E021: the age of the move (CH170)

- **Hypothesis and mechanism.** A traded 2 h move whose last trade was minutes before the capture still carries the trade's
  displacement of the touch (Roll's bounce has a half-life of minutes); one whose last trade was an hour earlier is what the
  makers left standing after revising. Fresh traded moves continue less (revert more) over the next 2 h than settled ones.
  The opposite reading (Dufour and Engle 2000: short durations carry more information) predicts > 0; the one-sided test
  cannot detect it and it is reported. **Direction: D_FS < 0, one-sided.**
- **Why the bounce is the object here (L9).** The fresh class is the bounce by design. E021 asks *when* the reversal sits,
  which E004/E006/J4 could not see without trade times. The skip-slot target is the binding label that separates "bounce
  timing" from persistence.
- **Unit.** Market x pass k whose market is in the pass's active-frame trade sample (status `ok`), is a `traded` mover at k
  (1.4 with `|x| >= 0.01`) and has at least one trade row with `ts < t_k` in the returned page (`t_k` = the row's
  `received_utc`, the sample's `origin_utc`).
- **Why all categories.** The active sample is a stratified random 2,000-market subsample of the active frame, so the
  traded movers it carries are a fraction of the universe's; with the non-sports subset alone the planning MDE exceeds the
  floor. The trade-sample family (E007, E013, E016, E018) is all categories with sports split; E021 follows it. Category
  is a spec parameter (`e021.population`), the sports and non-sports arms are reported, and the user's sports decision
  stays open.
- **Origin-side filters (in order, counted):** sample status ok; 1.4 items 1-5, 7, 8 at capture k; class `traded`; the page
  holds a row with `ts < t_k` (else, if the page is full, `unclocked_truncated`, else `unclocked_no_prior`); age <= 2 h + 30
  min (else `clock_inconsistent`: Gamma says traded, the page shows no trade in the interval).
- **State (frozen).** `age = t_k − max{ts : ts < t_k}` over the page's rows of the market (any sign; the page is the newest
  rows, contiguous in time, so the newest pre-origin row in the page is the true last trade before `t_k`). **Fresh:** age <=
  900 s; **settled:** age >= 3,600 s; middle reported. `n2h` = rows with `t_k − 7,200 <= ts < t_k`.
- **Target (exact).** `c = sign(x) · (mid_{k+1} − mid_k)` (Gamma mids, status `two_sided` at k + 1). Horizon 2 h.
- **Primary statistic.** Expanding-past demeaned OLS of `c` on `F = 1[fresh]` over fresh and settled units, controls:
  geometry dummies (parallel, one-sided, spread-change; same-side-unequal the base; the anatomy that fresh moves more often
  have), `log |x|`, `spread_k`, logit `mid_k`, `|mid_k − 0.5|`, `log1p volume24hr_{k−1}`, log hours-to-end (+ flag),
  `log1p n2h` (trade intensity mechanically shortens the age). Inference 1.7; seed 20261031. Gate: label permutation, seed
  20261131.
- **Mechanism readings (label rules).** M1: the sweep target `c_sw = sign(x) · (smid_{k+1} − smid_k)` (sweep 1 of passes k and
  k + 1). Gamma's mid at a fresh trade may lag the book. If Supported and M1 below 50% of D_FS or one-sided p >= 0.05: label
  **Gamma-quote mechanics**. M2: the skip-slot target `sign(x) · (mid_{k+3} − mid_{k+1})`. If Supported and M2 is not
  one-sided significant (p >= 0.05) in the same direction: label **bounce timing (reverses within one pass)**. Both
  labels are expected if the bounce reading is right; they are the reading, not a defect.
- **Secondaries.** S1 log age as a continuous dose; S2 within the parallel geometry only (Dufour-Engle reading: displacement
  absent); S3 non-sports and sports arms; S4 the 6 h target; S5 counts by class and the middle band.
- **Planning MDE (estimate).** Sources: P2/P2c (943-1,080 sampled markets a pass with a 6 h row; round 10 fact 3); the
  traded-mover share of sampled markets is **unprobed**. Assume 150-250 traded movers a pass (all categories), 1,800-3,000 a
  day, 37,800-63,000 in 21 days; 95% clocked; 30% fresh and 35% settled (unprobed); 75% survive the first-unit drop:
  fresh 8,000-14,000, settled 9,300-16,500. SD of `c` 4c (LT3 E015 assumption), event DE 2-3, day 1.3-1.5. Then `SE = 4c
  · sqrt(1/n_F + 1/n_S) · sqrt(2..3) · (1.3..1.5)` = 0.085-0.158c and **MDE = 3.388 · SE = 0.29-0.54c** against 0.5c:
  **borderline; the census gate (8) decides.** Declared in advance: E021 may be dropped before registration.
- **Floors (Unavailable):** < 2,000 fresh, < 2,000 settled, < 200 events, < 10 days.
- **Economics.** Reported: taker fade of fresh moves with `|x| >= 0.03`. The decision comes at the sample's receipt, after
  capture k and sweep 1, so the paper entry is at the sweep-1 touch of pass k and the exit at the sweep-1 touch of pass
  k + 1 (optimistic by the minutes between sweep 1 and the sample receipt; disclosed). Maker: gross `c` by class.
- **Missing data.** Sample absent for a pass → no units (counted per pass); sample status not ok → excluded (counted);
  unclocked units excluded and counted by reason; *coverage-limited* if `unclocked_truncated` > 2% of traded sampled movers.

## 4. E022: hollow liquidity (CH174)

- **Hypothesis and mechanism.** Gamma's `liquidity` is the dollar figure the interface shows; sweep 1's near-touch depth is
  what a taker can hit. A book whose displayed liquidity sits far from the touch is hollow; takers who size by the display
  walk thin books and produce impact, not information (Bessembinder, Panayides and Venkataraman 2009; Hendershott and
  Menkveld 2014). Within a market, **given the executable depth**, traded moves made when the book was hollower revert
  more. **Direction: beta(zh) < 0, one-sided.**
- **Unit.** Non-sports market x pass k that is a `traded` mover at capture k (1.4, `|x| >= 0.01`), with sweep 1 of pass k
  two-sided on the outcome-0 token and both 5c depths present, and Gamma `liquidity_k > 0`.
- **State (frozen; decision time = sweep 1's receipt).** `D = depth_bid_5c · sbid_0 + depth_ask_5c · sask_0` (taker notional
  of the outcome-0 book within 5c of each touch, dollars, approximate within 5c of price), `L` = Gamma `liquidity` at
  capture k; `h = clip(1 − D / L, 0, 1)`; `zh = (h − c_h) / s_h` (census scale). The superset share (`L >= D`) is a census
  gate, so `h` measures what it says.
- **Target (exact; leakage fix).** `c_sw = sign(x) · (smid_{k+1} − smid_k)`, `smid` = sweep-1 outcome-0 mid of pass k (the
  decision-time quote) and of pass k + 1 (status `two_sided`). Horizon one pass (about 2 h). Round 10 proposed `c` from the
  capture mid at k, which precedes the sweep that measures `h`: the book could refill or revert between the capture and the
  sweep, and that would enter both state and target. The sweep-to-sweep target starts at the state's own clock.
- **Primary statistic.** Expanding-past demeaned OLS of `c_sw` on `zh` over the units, controls: `log1p D` (real depth held
  fixed: the coefficient is the display's excess, not thinness), sweep spread at pass k, geometry dummies, `log |x|`,
  logit `mid_k`, `|mid_k − 0.5|`, `log1p volume24hr_k`. Inference 1.7; seed 20261101. Gate: continuous-label permutation of
  `zh` within market x UTC day, seed 20261201.
- **Mechanism readings.** M1 (thin-book reading): the same with `log L` in place of `log1p D`; reported, so the display effect
  and the thinness effect are both visible. M2: the skip-slot `sign(x) · (mid_{k+3} − mid_{k+1})`, reported (a transient
  impact reverts within the pass). The material reading T: the same estimator on `1[top h tercile]` versus the bottom
  tercile (census cuts); *material* if its point estimate is at or beyond 0.5c in the predicted direction.
- **Secondaries.** S1 `h` from the 1c depths; S2 reward versus non-reward markets; S3 the sports arm; S4 the Gamma-mid target
  from capture k + 1 (reported with the note that it starts before the decision time).
- **Planning MDE (estimate).** Source: P1 (about 8,900 traded non-sports movers a day, round 10 fact 3), about 186,900 in 21
  days; assume 80% sweep-covered with `L > 0` after the first-unit drop (about 150,000). SD of `c_sw` 4c; event DE 2-3; day
  1.3-1.5; VIF of `zh` given the controls (mainly `log1p D`) 1.5-3 (unprobed; census measures it). Per SD: `SE = 4c /
  sqrt(150,000) · sqrt(2..3) · (1.3..1.5) · sqrt(1.5..3)` = 0.023-0.046c, **MDE = 3.388 · SE = 0.08-0.16c per SD**. Tercile
  contrast about 2.2 SD apart (census measures the gap): **0.17-0.34c** against the 0.5c floor.
- **Floors (Unavailable):** < 20,000 units, < 300 events, < 10 days.
- **Economics.** (a) Reported: taker fade of traded moves with `|x| >= 0.03` in the top `h` tercile, entry at the sweep-1
  touch of pass k (decision time), exit at the sweep-1 touch of pass k + 1, fees both legs; the hurdle is the recorded
  round trip. (b) Maker: gross `c_sw` by `h` tercile, "gross, no fills".
- **Missing data.** Sweep missing for pass k → `.nosweep` (counted); outcome-0 token absent from the sweep, one-sided, or a
  depth missing → excluded (counted); `L` missing or <= 0 → excluded (counted).

## 5. E023: opens versus closes (CH171)

- **Hypothesis and mechanism.** On Polymarket a taker SELL needs the token in hand, so a sell closes (or reduces) a position
  and a buy opens one (round 10 fact 5). Newly opened positions carry the information (Pan and Poteshman 2006); closes are
  liquidity. E013/E016's 6 h flow continuation is stronger when more of the window's flow was opening. **Direction:
  beta(x6 · zOP) > 0, one-sided.**
- **Narrowed from round 10 (7.1).** The round-10 primary was the two-leg slope difference `beta_open − beta_close`. If the
  sign mix is the same in both legs, `o6 ≈ OP · x6` and `s6 ≈ (1 − OP) · x6`, so the `x6 · OP` slope is the same contrast;
  the moderator form keeps LT3's validated distant-donor gate and its size check. The two-leg regression is S1.
- **Unit and population (origin-side only).** As E016: market x active trade sample; status 200; 1.4 items 1-3 and 7 at the
  sample's capture; end date unknown or > `t` + 7 h; `volume24hr_t <= V*` (LT4's own census value: the largest at which the
  6 h truncation share was <= 2%); at least one signed row with `t − 6 h <= ts < t`. All categories (sports split reported).
- **Coverage.** As E016: covered if the page held < 500 rows or its oldest row is at or before `t − 6 h`; truncated units get
  NaN (counted); > 3% truncated → *coverage-limited* and a `V*/2` sensitivity.
- **Features (frozen).** Signed rows only, E007 convention (LT3 `signs`). `x6` as E013 (`clip(imb6, −1, 1) / 0.85782`).
  `OP` = Σ notional of BUY rows / Σ notional of signed rows in `[t − 6 h, t)`; `zOP = (OP − c_OP) / s_OP` (census).
- **Target.** `y6 = mid(slot k + 3) − mid_t` (status `two_sided` at k + 3). Horizon 6 h.
- **Primary statistic.** Expanding-past demeaned OLS of `y6` on `x6 · zOP` with controls `zOP`, LT3 E016's controls (`x6·zN`,
  `zN`, `x6·zSPR`, `zSPR`, `x6·zSize`, `zSize`, `x6·zHTE`, `zHTE`, `x6·zRV`, `zRV`, `x6`, logit mid, `|mid − 0.5|`, Gamma
  `chg_1h/1d/1w` with flags, `dprev` with flag, `hte_missing`, `rv_missing`). `x6·zHTE` matters here: closing flow is
  mechanically larger near the end. Inference 1.7; seed 20261102. Gate: distant donors, seed 20261202.
- **Mechanism reading (label rule).** M1: `x6` and `OP` on a window ending 30 min before `t`; if Supported and M1 below 50% or
  p >= 0.05: **possibly mechanical (stale-mid catch-up)**.
- **Secondaries.** S1 the two-leg regression (`y6` on `o6` with `x6` controlled: the coefficient is `beta_open − beta_close`);
  S2 within opens, the share of BUY notional on outcome 1 (the "bet-against" opener) as a moderator; S3 by category.
- **Planning MDE (estimate).** As E016 (LT3 3): about 250,000 market-samples in 21 days before the `V*` cut in an assumed
  5,000-8,000 events; per-SD interaction SE about 0.00053 (SB2-J2 h3 scaled, x 1.5 for proxy noise and attenuation) x
  1.0-1.6 for day clustering: MDE 0.0018-0.0029 per SD before the controls' cost; with a census VIF of `zOP` on the other
  moderators of 1.2-1.5 (assumed): **about 0.0020-0.0036 per SD.** E007's whole 1 h effect is 0.0036: the test detects a
  moderation per SD of about the main effect. **Inconclusive is a likely outcome.**
- **Floors (Unavailable):** < 20,000 covered units, < 500 events, < 10 days.
- **Economics.** Upper `OP` tercile (census cut), `|imb6| >= 0.5`: follow `sign(imb6)`, taker round trip to the 6 h target,
  entry at capture k's recorded touch (optimistic: the sample is received minutes later; disclosed as LT3 E016); the gross
  6 h move in that cell must reach 0.5c for *material*.
- **Caveats (disclosed).** `side` agreement with the touch is 93.3% for large non-sports fills (q0400); mis-signing attenuates
  `x6`, and a BUY/SELL swap would move a row between the legs. The census measures the side-touch agreement **by leg** and
  drops E023 if SELL rows agree more than 5 pp less than BUY rows (>= 500 rows per arm). A sell can follow a mint (split) and
  then be an opening of the other outcome; the UI's sell path needs a position, so this is assumed rare and disclosed.

## 6. E024: one order or a crowd (CH173)

- **Hypothesis and mechanism.** Data API rows are one taker order each (P2: 659,082 rows, 659,082 transactions). One large
  order is one agent's view (Kyle 1985; Easley and O'Hara 1987); dispersed same-direction flow is a crowd (Barber, Odean and
  Zhu 2009). Concentrated flow continues more. **Direction: beta(x6 · zC) > 0, one-sided.**
- **Unit and population.** E023's, plus **>= 3 signed rows** in the 6 h window (C is 1 by construction with one row).
- **Feature (frozen).** `C` = the largest signed row's notional / Σ notional of signed rows in `[t − 6 h, t)`; `zC` from the
  census. `HHI` (Herfindahl of row notionals) is secondary.
- **Primary statistic.** Expanding-past demeaned OLS of `y6` on `x6 · zC` with controls `zC`, E023's control set, **plus**
  `x6·zW`, `zW`, `x6·zH`, `zH` (LT3's walked and train measures, recomputed by LT4 with LT4's census scales), so the
  coefficient is the concentration effect net of walking and trains; `x6·zN`, `zN` and `x6·zSize`, `zSize` hold the row count
  and the mean order size (C >= 1/N mechanically). Seeds 20261103 / 20261203.
- **Mechanism reading:** as E023's M1. **Secondaries:** HHI in place of C; by category.
- **Planning MDE (estimate).** As E023's base (0.0018-0.0029 per SD) times `sqrt(VIF)`, the VIF of `zC` on `zN`, `zSize`,
  `zW`, `zH`, `zSPR`, `zRV`, `zHTE` (C is tied to the row count): assumed 1.5-2.5, **about 0.0022-0.0046 per SD**; the census
  computes it and gates at 0.0036. **Declared in advance: E024 may be dropped at the census.**
- **Floors, economics:** as E023 (upper `C` tercile).
- **Caveat.** The largest row is where q0400's large-fill agreement applies; the census measures side-touch agreement for
  the window's largest row versus the other rows and drops E024 on a gap > 5 pp (>= 500 rows per arm).

## 7. Ideas dropped or narrowed, and why (uncounted)

### 7.1 Narrowings of the top five at design
- **CH171 → E023:** two-leg difference → open-share moderator (S1 keeps the two-leg form). Reason: a validated within-unit
  null (LT3's donor gate, size-checked) exists for the moderator form; the round-10 label shuffle across a sample's rows
  needs row-level storage at analysis and has no size check. The contrast is the same under a common sign mix (section 5).
- **CH174 → E022:** target from the capture mid → sweep-to-sweep (leakage: the state is observed at the sweep, minutes after
  the capture); `log1p D` added as a control so the coefficient is the display's excess (without it, `h` is a thin-book
  proxy and the test repeats the impact story under a new name; that reading is M1). Standardised pooled, not within
  category (the population is non-sports only).
- **CH170 → E021:** all categories on the trade-sample stream (power and the family convention), with the trade-intensity
  control `log1p n2h` (age is mechanically shorter in busy markets) and an explicit clock-validity rule.
- **CH169 → E020:** tick-flip exclusion; the pre-move spread as a control (round 10's `spread_{k−1}`; the post-move spread
  would be the label itself); the M2 skip-slot label.
- **CH173 → E024:** the correlation gates are on absolute values (stricter than round 10's > 0.5), and a VIF-adjusted MDE gate
  is added.

### 7.2 Round-10 ideas not taken into LT4
- **CH172 (program versus human):** sixth in rank; its own census gate (>= 2,000 fades) is unprobed and the fade population
  is the smallest of round 10. Keeping k at 5 keeps the Holm threshold of the five powered tests. Candidate for LT5.
- **CH178 (E015's contrast on the sweep clock):** a replication of an LT3 primary inside LT4 would be a second counted test of
  E015's hypothesis on overlapping origins during E015's own window (double count). Out.
- **CH177 (silent edits), CH179 (races):** unprobed populations and an unknown `updated_at` clock; maps first.
- **CH175 (last-mid outcome map):** a map (k = 0), not a test. **CH176 (front page):** its price target needs about 60 days.

### 7.3 Census drops
Census drops will be recorded here, with their counts, before the pin.

## 8. Pre-registration censuses (counts only; before registration; worn pre-window data; no target read)

Each runs once, on inputs that **started before 2026-10-22T00:00Z** (before the LT2, LT3 and LT4 windows), reads origin-side
fields only (no quote at any later capture or sweep, no target, no P&L), prints counts, and is committed with its sha256
before the registration commit. **Input identity (L3):** the census refuses unless every input file it opens is named in the
seal with an equal sha256. A failed gate drops that test before registration (uncounted); `k_tests` lists the survivors.

**Inputs.** CQ (E020) and CH (E022): the complete captures of UTC **2026-10-15 and 2026-10-16** and their slot k − 1
(from 2026-10-14T22:31Z), and sweep 1 of each census pass (the days LT3's C1 already wore). CF (E021, E023, E024): the **23
sealed active-frame samples of 2026-10-16 and 10-17** (`seals/lt3_census_inputs_C2.json`, the same files LT3's C2 read) with
their captures and look-back slots k − 12 .. k (from 2026-10-15T12:31Z). These files rotate off the host (captures 8 days,
samples 3 days); they are restored byte for byte from the releases (queue drafts q0480, q0481) and the capture/sweep seal
`seals/lt4_census_inputs_captures.json` is written from the releases' `files.sha256` before any LT4 census runs.

**Projection** = census count x 21 / census days (an estimate). Distinct events: `E_2d + (E_2d − E_day1) x 19` (LT3's rule).
"Effective" counts = units in markets with >= 2 units of the test's population in the census days (the units that survive
the first-unit drop and carry within-market variation).

| Test | Census | Gate (all must hold; NaN fails) | Values fixed into the spec |
|---|---|---|---|
| E020 | CQ | tick known at k − 1 and k for >= 90% of one-sided non-sports movers; arrival share of one-sided units in [15%, 85%]; projected arrivals >= 15,000 and cancellations >= 15,000; **pessimistic effective-count MDE <= 0.5c** (3.388 x 4c x sqrt(1/A_eff + 1/C_eff) x sqrt(3) x 1.5) | none |
| E021 | CF | `ts` second-level (share of pre-origin rows with `ts mod 60 != 0` >= 50%); fresh and settled each >= 10% of clocked traded sampled movers; projected clocked units >= 40,000; unclocked-truncated <= 5% of traded sampled movers; **pessimistic effective-count MDE <= 0.5c** (same formula on fresh/settled) | none |
| E022 | CH | sweep-covered share (two-sided outcome-0 sweep with both depths, `L > 0`) >= 80% of traded non-sports movers; **superset share `L >= D` >= 90%**; within-market IQR of `h` >= 0.1 in >= 50% of markets with >= 10 traded movers (and >= 30 such markets; fewer fails); **pessimistic planning MDE per SD x tercile gap <= 0.5c** (3.388 x 4c / sqrt(n_eff) x sqrt(3) x 1.5 x sqrt(VIF) x gap) | `zh` centre/scale, `h` tercile cuts, gap |
| E023 | CF | V* defined (NaN fails); SELL share of signed rows in [15%, 85%]; side unusable (not BUY/SELL or outcome unknown) <= 10% of pre-origin rows; `OP` strictly in (0, 1) for >= 40% of covered units and projected interior units >= 30,000; `|corr(zOP, zW)|` <= 0.5 and `|corr(zOP, zH)|` <= 0.5; side-touch agreement gap BUY − SELL <= 5 pp with >= 500 rows per arm; **planning MDE <= 0.0036** (0.002873 x sqrt(5,000 / projected events) x sqrt(VIF_OP)) | `vol24_cap` (V*), centres and scales of zOP, zC, zW, zH, zN, zSize, zSPR, zRV, zHTE; `econ.OP_upper_cut` |
| E024 | CF | `C` < 1 (>= 3 signed rows) in projected >= 40,000 covered units; `|corr(zC, zW)|` <= 0.5 and `|corr(zC, zH)|` <= 0.5; agreement gap other − largest <= 5 pp with >= 500 rows per arm; **planning MDE <= 0.0036** (as E023 with VIF_C) | `econ.C_upper_cut` |

- The 0.0036 reference is E007's whole 1 h flow effect: a flow moderation test that cannot detect a per-SD moderation as
  large as the main effect is not worth a Holm slot. The 0.002873 base is 3.388 x 0.00053 x 1.6, LT3 E016's pessimistic
  per-SD MDE at 5,000 events; VIF = 1 / (1 − R²) of the standardised moderator regressed on the other standardised
  moderators of its model in the covered units.
- The E022 superset rule and the IQR rule are round 10's kill criteria; the 80% coverage, 30-market and MDE items are added.
- **Series concentration (descriptive):** CQ and CH print the top series family's share of each primary population (LT3 R1
  finding 2); no population rule is pre-declared for LT4 (question 9).

## 9. Implementation plan

### 9.1 Modules (code exists on this branch; DRAFT, spec not pinned)
- `backend/astrolabe/research_lab/live_tests4.py`: the reader. `run_once()` (internal non-blocking flock) finds new complete
  captures, their pass's sweep 1 and active trade sample, and in order writes, write-once (`%.17g`, atomic hard link):
  1. `series/<capture>.csv.gz` and `status/<capture>.csv.gz` (LT3's series plus Gamma `liquidity` and the reward fields);
     `sweeps/<capture>.csv.gz` (outcome-0 sweep-1 quote, sizes, 5c depths, receipt);
  2. `move/frozen/<capture>.csv.gz` (every `|x| >= 1c` mover with class, geometry and E020's fields);
     `hollow/frozen/<capture>.csv.gz` (E022, once sweep 1 of the pass exists; `.nosweep` if it never does);
     `clock/frozen/<sample>.csv.gz` (E021) and `flow/frozen/<sample>.csv.gz` (E023/E024, LT3's flow line plus `OP`, `C`,
     `HHI` and their 30-min-early versions);
  3. `<kind>/outcomes/<id>.h<j>.csv.gz` and `.s<j>.csv.gz` (status and quote at slot k + j; sweep-1 quote of pass k + j);
  4. `passes.jsonl`.
- `backend/astrolabe/research_lab/live_tests4_analysis.py`: the single analysis (1.7-1.10, Holm over k, counting), the size
  check (1.8).
- `backend/scripts/run_live_tests4.py`: `run`, `ops-stats`, `census-captures`, `census-flow`, `size-check`, `analyze`.
- Spec: `backend/astrolabe/research_lab/model_specs/live_tests4_v1.json` (every constant, k, seeds, dates, census scales,
  the four-module `code_sha256` map).
- **Reused by import, unmodified:** from `live_tests3`: `classify`, `move_join`, `series_frame`, `category_cols`, `scan_*`,
  `State`, `read_series/status/sweep`, `outcome_h/s`, `status_codes`, `target_state`, `is_late`, `grid_rv`, `signs`,
  `grid_distance`, `train_flags`, `flow_rows`, `window_features`, `freeze_flow`, `load_sample`, `token0_map`,
  `project_events`, `mde_eff`, `vol24_cap_rule`; from `live_tests3_analysis`: `fit`, `perm_gate`, `donor_gate`, `verdict`,
  `attach`, `underpowered`, `attrition`, `lee_bounds`, `paper_taker`, `econ`, `gross`, `check_fraction`, the simulated worlds.
  Pinning the LT3 module hashes (L7) means an LT3 code change after the LT4 pin invalidates LT4 lines, which is the intent.
  The stores stay separate: LT4 never opens `live_tests3/`.

### 9.2 Resources and install
- **Memory:** per pass two captures' selected columns, one sidecar, one sweep (65,771 rows, nine columns) and one trade sample;
  target peak < 400 MB, `mem_mb 480`. **CPU:** about 1-3 min per pass (estimate; the flow line recomputes LT3's features plus
  three). **No network.** **Disk:** about 1 GB over the window (estimate; series with two extra columns); stops at 1.5 GB.
- **Install (recommended):** host cron `10-59/20 * * * *` (offset 10 min from LT3's `*/20`, so the two readers never start
  together), own `flock`, `nice -n 19`, `oom_score_adj 1000`, `ulimit -v 983040`. The queue draft q0485 is the fallback,
  **never both**. Installing is a host change under the standing collection authorisation, done by the orchestrator.

### 9.3 Tests and pins
- `backend/tests/unit/test_research_lab_live_tests4.py` (20 tests, synthetic only): arrival/cancellation labels and the
  unmoved side; tick-flip exclusion; the clock (age from the newest pre-origin row, post-origin rows ignored, truncation,
  no prior, inconsistency); `h` and the superset; `OP`, `C`, `HHI`, the legs; causality (future captures and sweeps with
  wild prices leave every frozen line identical); late refusal, write-once and the dry-run guard; the `.nosweep` marker and
  sweep statuses; `%.17g` round trip; the run lock; ops-stats reads no price column; the four-module hashes and the joint
  reader sha; the counting rule equals k; the analysis refuses before the date and refuses an unpinned, null or NaN-filled
  spec; the p = max rule; the sealed censuses (counts only, tampering refused); the planning-MDE gates; the size check on
  small runs with planted effects; an end-to-end synthetic analysis (all five tests fitted; a reduced `k_tests`).
- At registration: `SPEC_SHA256` and the four module hashes are pinned together.

## 10. Disclosures

- **Selection history.** The five ideas are round 10's top five (Fable xhigh creative pass, `fe54ef20`), written with no
  host probe, from round 9's probes on worn data (P1/P1b 2026-10-15 captures; P2/P2c 2026-10-16 trade samples), LT2's
  census re-run and LT3's documents. They were ranked by a judgement score. The censuses (8) are a further counts-only read
  of the same worn days.
- **The designer** read the ideas file, LT3's and LT2's designs, the LT3 code and tests, collector code and the ledger
  section on LT3. No data, host or outcome was read.
- **Closest prior AREPO tests.** E020: E015 (S1 one-sided minus traded), E004/E006 (pooled reversal, consistent with bounce),
  SB2-J4, CB3, CH80/CB-dust. E021: E004, SB2-J3 (could not run), J4, CH132. E022: E015 M1, CB3 (quote vacuum), CH35, CH133.
  E023: E007, E013, CH144/CB17-A (withdrawn, branch T, a different sign source). E024: E016, E018, HB1 size features.
- **Mechanics stated up front.** E020: spread mean reversion can move the unmoved side in both classes (M2 label; the
  spread change is the label, so it cannot be a control). E021:
  the fresh class is the bounce (M2 is the reading). E022: hollowness is partly thinness (depth control, M1). E023: closing
  flow is larger near the end (`x6·zHTE`). E024: C is tied to the row count and to walking/trains (controls, gates).
- **Shared data.** LT2, LT3, E011, CB-batch windows read the same captures, sweeps and samples. Overlap only.

## 11. Questions for the challenger

1. E020: the unmoved side's 2 h change excludes the bounce, but spread mean reversion can still move the unmoved side, and
   the post-move spread cannot be a control (it is the label). Is the M2 "transient" label (skip-slot give-back) a
   sufficient binding check, or should the primary condition on the post-move spread's deviation from the market's
   expanding-past norm in a non-linear way (for example bins)?
2. E021: is the bounce-as-object framing acceptable as a counted primary, given that the expected Supported result carries
   both mechanism labels? Or should the primary be the skip-slot target (testing persistence instead of timing)?
3. E021: all categories on the trade-sample stream (power and family convention) versus the capture family's non-sports
   rule. Acceptable, or must the non-sports arm be the primary even if the census drops it?
4. E021: is "the newest pre-origin row in a newest-first page is the true last trade" sound when the Data API page is
   capped at 500 (rows after `t_k` fill it first)? Is 2% the right *coverage-limited* line?
5. E022: is `D = depth_bid_5c · sbid + depth_ask_5c · sask` the right reconciliation with Gamma `liquidity`, and is the
   90% superset rule enough to call `h` defined? Should `log1p D` be in the primary (display effect) or only in M1?
6. E022: the sweep-to-sweep target mixes the state's clock (sweep 1, pass k) with Gamma's `liquidity` (capture k, minutes
   earlier). Acceptable?
7. E023: is the open-share moderator an acceptable narrowing of the two-leg contrast? Is the BUY-versus-SELL agreement gap
   the right sign check for a leg split?
8. E024: is a VIF-adjusted planning MDE gate at 0.0036 (E007's whole effect) a sound way to drop a moderator that is mostly
   row count? Should `x6·zW` and `x6·zH` be controls (they are LT3 primaries' terms)?
9. Series concentration: LT3 made E019 ex-crypto by a census rule. E020 and E022 are market-level with event clusters; is a
   *series-concentrated* label enough, or is a population rule needed?
10. The p rule max(event t, two-way, day t): enough for 2 h and 6 h targets, given LT3 used max(event, day)?
11. The 48 h stagger after LT3 and the offset cron: any interference between two readers of the same captures?
12. The continuous-label permutation gate for E022 and the correlated-moderator donor scenario: are the new size-check
    scenarios the right nulls? The correlated-moderator rate was 0.075 at 200 worlds (limit 0.075; 13.3).
13. Float read-back (13.2): is a <= 1 ulp parse difference in the imported LT3 readers acceptable given the class-rule
    tolerances, or should LT4 own its series readers with `float_precision="round_trip"` (and LT2/LT3 be noted)?

## 12. Draft ledger block (DRAFT, not registered, not counted)

> ## E020-E024 — Live tests 4 (LT4): DRAFT pre-registration (not registered, nothing counted)
> - **Design:** `docs/research_lab/LIVE_TESTS_4.md`. Pure reader of streams the host already writes (complete captures,
>   sidecar, sweep 1, active trade samples); cpu work, no network, < 400 MB target, `mem_mb 480`; reuses LT3 code by import
>   (pinned), separate store `live_tests4/`.
> - **E020** (CH169) arrival minus cancellation, unmoved-side 2 h ratification, non-sports, > 0; MDE about 0.12-0.17c, floor 0.5c.
> - **E021** (CH170) fresh minus settled traded moves, 2 h continuation, all categories, < 0; MDE about 0.29-0.54c vs 0.5c; census-gated.
> - **E022** (CH174) hollowness `zh` (display versus 5c depth, depth held fixed), sweep-to-sweep continuation, < 0; about 0.08-0.16c per SD.
> - **E023** (CH171) open share moderates 6 h flow continuation, `x6·zOP` > 0; about 0.0020-0.0036 per SD; Inconclusive likely.
> - **E024** (CH173) concentration moderates 6 h flow continuation, `x6·zC` > 0, W and H held fixed; about 0.0022-0.0046 per SD; may drop at census.
> - **Family:** Holm over k (5 if every census gate passes), one-sided, alpha 0.05; p = max(event t on G − 1, two-way event x
>   UTC day, UTC day t on G − 1). Window: captures starting in `[REGISTERED_UTC, +21 d)`, proposed `[2026-10-26T00:00Z,
>   2026-11-16T00:00Z)`; single analysis on or after 2026-11-17T12:00Z. Economics: paper taker round trips, expected "not shown".
> - **Not taken:** CH172 (smallest population; LT5 candidate), CH178 (would double-count E015), CH177/CH179 (maps first), CH175 (map), CH176 (needs ~60 days).
> - **Status:** DRAFT awaiting the capture/sweep seal, censuses CQ/CH/CF (q0480-q0483), the challenger review, the size check
>   (q0484), the pin and the ledger entry; no line is `prospective_confirmation` until the pin. Code, spec and 20 synthetic
>   tests on `feat/live-tests-4` (section 13).

## 13. Code pass (2026-10-20): what exists, and what the code taught the design

Code: `live_tests4.py`, `live_tests4_analysis.py`, `scripts/run_live_tests4.py`, spec `model_specs/live_tests4_v1.json`
(DRAFT: `SPEC_SHA256 = None`, `k_tests`, scales and cuts null), tests `tests/unit/test_research_lab_live_tests4.py` (20 tests,
synthetic only), `battery2.KIND_RULES["live_tests4"]`. No real target, capture, sweep or sample was read. No threshold, floor,
alpha, direction or Holm rule was changed to obtain a pass.

### 13.1 Design changes made during the code pass (all before any data; disclosed)
1. **E020 controls (section 2).** The synthetic end-to-end test returned "no residual variation" for E020: for a one-sided
   move `spread_k − spread_{k−1} = ∓2|x|`, so `spread_k`, `spread_{k−1}` and `log |x|` together reproduce the label. The
   primary keeps `spread_{k−1}` only; the both-spreads model is `sensitivity_spread_k_control`. Consequence: spread mean
   reversion is not controlled in E020's primary; M2 is the binding reading (question 1).
2. **`.nosweep` versus `.late` (section 1.5).** A sweep is "missing" 3 h after its slot, but E022's freeze deadline is the next
   slot (2 h). As first written, every missing sweep would have become a `.late` marker and inflated the late-loss label. Now:
   if the deadline passes with no sweep file, the reader writes `.nosweep` (missing data for E022, counted), not `.late`.
3. **Secondaries not implemented, removed from the text:** E023 "OP on row counts", E024 "C on row counts" and the
   worked-order fingerprint. Added: E022 S2 reward split (it was in the text, not the code).

### 13.2 Findings for the challenger (code against design)
- **Float read-back (affects LT2 and LT3 too).** `%.17g` writes are exact, but pandas' default C parser reads a 17-digit
  value back with up to 1 ulp of error (unit test: `0.30000000000000004` read as `0.3`). LT4's analysis reads with
  `float_precision="round_trip"` (exact). LT4's imported LT3 helpers (`read_series`, `read_sweep`, `outcome_h`) use the
  default parser, so series quotes and epochs used in freezing can differ from the written value by <= 1 ulp. Every class
  rule has a tolerance of 1e-12 or wider (`classify`, the spread rule 1e-9, the tight rule), far above 1 ulp, so no label
  can flip except at an exact tie within 1e-16. LT2's and LT3's analyses read with the default parser as well; the same
  argument applies. Recorded, not fixed in LT3 (its code is frozen for its own pin).
- **LT3 code reuse and pins.** LT4 imports the LT3 reader and analysis functions listed in 9.1 (and LT3 utilities) unmodified; the hashes of `live_tests3.py`
  (`202c0d63…`) and `live_tests3_analysis.py` (`b03c6321…`) equal the values in `LIVE_TESTS_3.md` 13.9. Any LT3 change before
  LT4's pin changes LT4's `code_sha256` map; after the pin it would make LT4 lines unmatchable (intended).
- **Current module hashes (DRAFT; change with any edit):** `live_tests4.py` `e54aaff3b750e031…`,
  `live_tests4_analysis.py` `499e5b69214abe6e…`; joint reader sha `d8e1978008b669e9`.

### 13.3 Preliminary size check (not the registered statement)
Run locally on 2026-10-20, 200 worlds x 99 draws, seed 20261026, on the code of commit `c08383a5` (module hashes as in 13.2;
output sha256 `ec639342…`, not committed). Limit at 200 worlds: 0.05 + 1.645 sqrt(0.0475 / 200) = 0.075. Rates (all within the
limit, PASS): permutation binary iid **0.035**, binary persistent **0.040**, continuous persistent **0.040**; donor iid **0.055**,
AR(1) 0.6 **0.065**, life cycle **0.035**, **correlated true moderator 0.075 (at the limit)**.
- **Flag for the challenger:** the new correlated-moderator scenario (the E024 situation: a tested moderator correlated 0.4
  with a controlled moderator that has a real effect) sits exactly at the 200-world limit. A Monte Carlo SE at 200 worlds is
  about 0.015, so this is not evidence of a size problem, but it is the scenario to watch at 2,000 worlds (limit 0.058). If it
  fails there, the donor gate is not a valid null for E024 as specified and E024 must be redesigned or dropped before the pin
  (no threshold is moved to pass it). A plausible mechanism: the donor replaces `zM` but not the correlated `zA` component it
  carries, so donor draws break part of `zM`'s link to the real `x6·zA` effect that the real fit partials out only linearly.
- This is a preliminary statement. The registered one needs >= 2,000 worlds on the code to be pinned (q0484).

### 13.4 What remains before the pin
- `seals/lt4_census_inputs_captures.json` from the releases' `files.sha256` (q0480 restores the files; tags to confirm).
- Challenger review of this file (`science-reviewer`), then the freeze check of code against design.
- Censuses q0482 (CQ, CH) and q0483 (CF); fill `k_tests`, `vol24_cap`, the flow scales, the `zh` scale, `h` cuts, the gap
  and the OP/C cuts; record drops in 7.3.
- Size check at >= 2,000 worlds on the code to be pinned (q0484); any failing scenario blocks the pin.
- A host dry run on past captures into a scratch root (`run --dry-run-start ... --root <scratch>`), memory measured.
- `code_sha256` map, `SPEC_SHA256`, ledger entry, cron install (9.2), at least 24 h before `REGISTERED_UTC` (1.1).
