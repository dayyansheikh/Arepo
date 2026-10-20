# Live tests 2 (LT2): E012, E013, E014 — DRAFT pre-registrations

**Status: DRAFT, not registered, nothing counted.** Drafted 2026-10-19 (~21:50Z) on branch `feat/live-tests-2`; revised
2026-10-20 after challenger round 1 (REVISE x 4; `reviews/LT2_CHALLENGER_R1_2026-10-20.md`; response in section 9) on branch
`feat/live-tests-2-r1`. Registration needs, in order: the challenger re-check of the R1 fixes, the census re-run that fills
`flow.vol24_cap` (section 3), the `code_sha256` map refresh, the `SPEC_SHA256` pin in
`backend/astrolabe/research_lab/live_tests2.py`, the ledger entries (draft block in section 8) and the promotion of the queue
draft `q0460`. Until the pin exists, every line the code writes is `prospective_unregistered` by construction.

Research tooling only. No edge, calibration, profitability or tradability claim exists or is implied. Development numbers
quoted here are **development (historical)** evidence and are labelled as such.

## 0. Summary

| ID | Hypothesis (direction) | Development evidence | Stream (already captured) | Primary | MDE (planning, Holm worst case) |
|---|---|---|---|---|---|
| **E012** | The 24 h change carries forward more (reverses less) in liquid markets: slope of `x · zL` > 0 | SB2 L1, development-replicated (h2 +0.062, h3 +0.075, Holm 0.05; ratio 1.22; stable across halves); **prior prospective: E006 H1** (1 h version, Supported on sign, "consistent with bounce") | complete-universe snapshots, 6-hourly grid origins, 24 h target | expanding-past demeaned OLS, one-sided p = max(event, two-way event x two-day block, t with G − 1 df); 6 h skip-slot bounce label | about 0.037 (range 0.025-0.046) vs dev 0.062-0.075 |
| **E013-F4** | 6 h taker flow continues more in volatile markets: slope of `x6 · zRV` > 0 | SB2 F4, development-replicated (h2 +0.0019, BY survivor; h3 +0.0030; 40-55% weaker in the later half) | trade samples (6 h flow) + snapshots (RV proxy, 6 h target) | same estimator (UTC-day time clusters), plus a far-future-control timing gate | about 0.0017 vs realistic 0.0008-0.0016: **likely underpowered** |
| **E013-F5** | 6 h taker flow continues more where the spread is wide: slope of `x6 · zSPR` > 0 | SB2 F5, development-replicated (h2 +0.0047; h3 +0.0060) | same | same | about 0.0028 vs dev 0.0047-0.0060 |
| **E014** | The frozen E007 flow model gains more over its frozen base in the last 24 h before the as-of end date than more than 30 days out | SB2-J8 C-TTE, development-replicated as an ML-model contrast (+0.0188 nats, CI [0.0094, 0.0292]); E007 flow continuation supported prospectively | trade samples (1 h flow, E007 frozen coefficients) + snapshots (as-of end date, 2 h target) | mean per-row squared-error gain, A minus B, same p rule (UTC days), plus a far-future-control timing gate | slope-equivalent about 0.0030 (moderate power; Inconclusive is a likely outcome) |

- **One Holm family over the four primaries** (E012, E013-F4, E013-F5, E014): one-sided, familywise alpha 0.05, **Holm k = 4**.
  A primary that is unavailable, void, placebo-biased or fails its timing gate enters Holm with p = 1. This family is separate
  from E009-E011. **Counted tests: 8** (the 4 primaries + the 4 declared paper-economics tests, section 1.9); the economics tests
  are not in the Holm family and never change a primary verdict.
- **Origin window (all four):** captures with start in `[2026-10-22T00:00:00Z, 2026-11-12T00:00:00Z)` (21 days).
- **Single analysis:** on or after **2026-11-13T12:00:00Z** (`q0461`), once. Last targets are due about 2026-11-13T00:31Z (E012).
- **Live from:** 2026-10-22T00:00Z if registered before then (section 1.1). The collector job may start on 2026-10-21T00:00Z
  (series look-back only; no origin line before the registered start).

## 1. Common rules

### 1.1 Registration, causal boundary and the sealed-window rule
- All four rest on Screening Batch 2 candidates. SB2's rule (SCREENING_BATCH_2.md §1.2, Methods note M3) says confirmation must
  come from SEALED-P (data captured after the registration commit) or SEALED-H4 (origins >= 2026-10-22T00:00Z). These tests
  are SEALED-P confirmations, and the origin start is set to `T_seal` = **2026-10-22T00:00:00Z** as well, so both readings hold.
- `REGISTERED_UTC = 2026-10-22T00:00:00Z` in `live_tests2.py` and in the spec. If the registration commit (pin + ledger) is not
  made before it, `REGISTERED_UTC` moves to the first 00:00Z at least 2 hours after that commit, `END_UTC` = REGISTERED_UTC + 21
  days and the analysis date = END_UTC + 36 h; the move is recorded in the ledger. No data inspection is involved in that rule.
- **Effective start** = max(REGISTERED_UTC, first capture processed by `q0460` running the registration code). Enforced, not
  only stated: the spec JSON pins `code_sha256` of `live_tests2.py` and `live_tests2_analysis.py` (normalised sha256 with the
  `SPEC_SHA256 = ...` line replaced by a placeholder, `live_tests2.code_sha256`, so the two pins do not chase each other), filled
  in the same commit as `SPEC_SHA256`. Every frozen line carries `spec_sha` (16 hex digits of the spec sha256) and `code_sha`
  (16 hex digits of the collector hash). The analysis keeps only lines with role `prospective_confirmation`, `spec_sha` = the pin
  and `code_sha` = the pinned collector hash (dropped lines counted per reason), and with a pinned spec it refuses to run if
  either module on disk differs from its pin or if `flow.vol24_cap` is unfilled. `code_commit` stays in each line as provenance.
- Nothing in the window has been read: the census (section 6.2) used captures and samples that started before
  2026-10-19T21:00Z and read no target. J4-R's fresh window (2026-10-16 to 2026-10-21, SCREENING_BATCH_2.md J4-R) ends before ours.

### 1.2 Data and the collector (`q0460`, `live_tests2.run_once`)
- **Inputs (read-only, no network):** complete captures `research_lab/snapshots/<id>/rows.csv.gz` (+ `rows_ext.csv.gz` for fee
  fields) and active-frame trade samples `research_lab/trade_samples/<id>/` (plan, manifest, features, trades). Nothing else.
- **Slots:** captures are mapped to the collector's 2 h grid (`grid0 = 2026-10-01T00:31Z`, tolerance 30 min). The first complete
  capture of a slot is used.
- **Outputs** (`research_lab/live_tests2/`), every data file **write-once** (atomic hard-link; an existing file is never touched):
  `series/<capture>.csv.gz` (two-sided quotes of open binary markets per capture, from REGISTERED_UTC − 26 h),
  `status/<capture>.csv.gz` (written with the series file: every binary market of the listing that is not in the series, with
  status `closed`, `inactive` or `one_sided`; a market in neither file was absent from the listing),
  `e012/frozen/`, `flow/frozen/`, `e012/outcomes/`, `flow/outcomes/`, `passes.jsonl` (append-only log), `state.json` (cache only).
- **Origin features** use the origin capture, earlier captures (series) and, for flow, trades strictly before the origin row's
  receipt time. Targets come only from the target capture's series file.
- **Late rule:** an E012 freeze is refused once its 24 h target slot may have started; a flow (E013/E014) freeze is refused
  once its **last** target slot (6 h, E013) may have started (`now >= slot time − 60 s`); a `.late` marker records the refusal
  and the origin is lost (counted). At analysis every test judges lateness against its own target: a line whose `frozen_utc` is
  not strictly before the start of that test's target capture is excluded from that test and counted (`late`); so an E014 row
  frozen after its 2 h target capture started is excluded from E014 but may stay in E013.
- **Clocks:** origin = each row's receipt time (`received_utc`); slot membership = capture start; trades use their venue `ts`.

### 1.3 Missing data (never imputed into a test; declared bounds are labels only)
- Origin capture or trade sample missing (collector outage, failed pass, skipped for disk): no lines; counted from slot gaps.
- Target capture missing 3 h after its slot: `missing_capture`. Market without a two-sided quote at the target:
  `unavailable_closed`, `unavailable_inactive`, `unavailable_one_sided` (from the target capture's status file) or
  `unavailable_absent` (in neither file; plain `unavailable` only if a status file is missing). Resolution and closure are
  therefore measurable (challenger R1 finding 3). **Attrition rule (declared):** for each test the unavailable share among rows
  whose target capture exists is compared between two pre-declared origin-side groups (E012: L = 0 vs L > 0; E013: upper vs lower
  census tercile of the moderator; E014: regime A vs B). If the absolute difference exceeds **5 percentage points**, the verdict
  carries "differential attrition (+d pp)" and a declared bound is computed: E012/E013 refit the primary with every unavailable
  row's target set to −sign(raw tested term) x the 95th percentile of observed |y|; E014 a pessimistic bound (unavailable A rows
  get the 5th percentile of observed A gains, B rows the 95th percentile of B gains) and a Manski worst case (each unavailable
  row's target at the end of [−mid_i, 1 − mid_i] least favourable to A − B). If the pessimistic bound is <= 0 the verdict also
  carries "attrition-sensitive". The bound never changes the verdict or the Holm p; it is a label.
- `x` (E012) is NaN unless the market was tight at h; `x6` (E013) is NaN if the 6 h window is not covered by the 500-trade page
  or holds no trade; `ss` (E014) is NaN if the trade sample flags the 1 h window truncated (`trades_truncated`; never a partial
  value); `rv` is NaN with fewer than 6 valid 2 h differences; such rows are excluded from that test only and counted. Because
  truncation depends on trades after the origin (the page runs to request time), E013's population is cut on an origin-side
  activity measure and residual truncation is a label (section 3; E014 section 4).
- Outcomes are written once; a pending target is never filled later from another source.

### 1.4 What is not looked at before the analysis date
- No mid, move, P&L, regression, correlation or plot from `live_tests2/` files, or from the snapshots and trade samples of
  in-window origins, for these hypotheses. Only `run_live_tests2.py ops-stats` (file, line, role and status counts; it reads no
  price column, enforced by a test) may be run.
- The automatic `flow_screen` development lines (one per pass, on the same trade samples; F1 is E007's signed share against the
  next snapshot) keep running. They are not regime-split, not about the L1/F4/F5 moderators, and must not be consulted for any
  E012-E014 decision. Disclosed as a shared-data overlap, as in E007.
- No interim analysis; no change of thresholds, scales, populations or estimators after registration. Operational fixes are
  logged as deviations.

### 1.5 Estimators, placebos and gates (J4 lessons)
- **E012 and E013:** `expanding-past demeaned` OLS (J4-R, accepted by the challenger 2026-10-16): every regressor (the tested
  term and all controls) minus the market's mean over its strictly earlier rows; the target is raw; the first row of each market
  drops. Unbiased under the null of independent increments; it **attenuates** effect sizes under the alternative (unit test: a
  planted 0.5 reads about 0.44 with 20 rows per market), so it is conservative.
- **Inference with few time clusters (challenger R1 finding 5):** SEs are event-clustered and two-way event x time cluster (CR1,
  `battery.beta_test`). Time clusters: **E012 two-day blocks** anchored at the window start (11 blocks; the 24 h targets on the 6 h
  grid overlap across midnight, so UTC days are not independent units for E012; blocks halve the cross-boundary overlap share);
  **E013 and E014 UTC days** (21; their targets are 6 h and 2 h: a quarter of E013 origins (passes from 18:31 on) and one in
  twelve E014 origins cross midnight, by a few hours only). **Primary
  one-sided p = max(p_event, p_twoway, p_t)**, p_t = the two-way z referred to Student t with G − 1 df (G = time clusters in the
  fit; G < 2 gives p = 1). This is a conservative small-G reference (it does not rely on the normal approximation with about 11 or
  21 clusters). CI: 2,000-draw event-cluster bootstrap (E014: 4,000); the conservative 95% CI is the hull of the bootstrap CI,
  beta ± 1.96 se_event and beta ± t(0.975, G − 1) se_twoway. UTC-day clustering of E012 is reported as a sensitivity.
- **E012 placebo (J4-R, matched):** 20 draws; per market the 2 h mid series is rebuilt from the market's pooled valid increments
  drawn with replacement, each contiguous run from its observed start level; `x`, `y`, `dprev`, logit mid and |mid − 0.5| are
  recomputed; tightness flags, volume and Gamma change fields stay as observed. J4-R reading rule: VOID if the 2.5-97.5% range of
  placebo betas excludes 0; "inconclusive (placebo bias)" if |mean placebo beta| > 0.5 x the real max-SE.
- **E013 and E014 timing gate: far-future control target (replaces the R0 cyclic-shift gate; challenger R1 finding 1).** The
  question is whether the tested link is about *timing* (flow now predicts the price move just after now) rather than a market-level
  association (markets with persistent flow drift persistently). For each test row i, its **sources** are the LATER test rows of
  the same market (E014: same market and regime) whose origin is at least **flow window + target horizon** later (E013: >= 12 h;
  E014: >= 3 h). A source's flow window and target therefore never overlap row i's flow window or target. Earlier rows are never
  sources (their flow is already in row i's expanding-past demeaned regressors). Gate rows = test rows with **>= 4 sources**.
  The far-future control target `y_far,i` = mean target of row i's sources. Statistic: E013, the interaction slope (expanding-past
  demeaned regressors and controls, re-demeaned within the gate rows, as the primary) of `y − y_far`; E014, mean_A − mean_B of
  `gain(y) − gain(y_far)` with the row's own frozen predictions. A market-level link moves both targets alike and cancels; only a
  timed link survives; persistent (autocorrelated) flow makes `y_far` partly respond to a true effect too, which attenuates the
  statistic (conservative). One-sided **p_gate = max(p_CR1, p_jackknife)**, the event-clustered CR1 t and the delete-one-event
  jackknife t each referred to Student t with G − 1 df (G = event clusters of the gate rows). **Pass: p_gate < 0.05.** Gate floors:
  E013 >= 1,000 gate rows in >= 100 markets; E014 >= 50 gate rows per regime; below the floor the gate is untestable and the
  primary enters Holm with p = 1 ("within-market timing not shown"). `between_share` = far-control statistic / real statistic on
  the gate rows is reported. **Simulated null size** (unit tests, 300 worlds per scenario, assertion at the 99% binomial bound;
  plus a one-off 1,500-world run per scenario on 2026-10-20): E013 iid flow 0.047, AR(1) flow (phi 0.8) 0.053, overlapping 3-slot
  windows 0.050, overlapping with 40% missing rows 0.051; E014 iid 0.048, AR(1) 0.054, market-constant flow 0.046, overlapping
  0.055 (pooled 605 / 12,000 = 0.050; Monte Carlo SE per scenario 0.006). Every null world carries a strong between-market link
  (a pooled interaction would reject). Power: a planted timed effect passes in >= 80% (E013) / >= 90% (E014) of worlds.
- **Sensitivities (reported, not tested):** pooled (no demeaning), full-sample market demeaning (within slope), j-tight targets,
  markets with >= 20 rows (E012), Gamma `oneDayPriceChange` in place of `x` (E012), flow window ending 30 min early (E013), 1/p
  inclusion weights (E013, E014), relative-gain contrast and slope contrast (E014), leave-one-UTC-day-out range (E012).

### 1.6 Verdicts (per primary, after Holm over 4)
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate > 0, placebo family OK (E012) or timing
  gate passed (E013, E014).
- **Contradicted:** conservative 95% CI entirely below 0.
- **Inconclusive:** otherwise, including "inconclusive (placebo bias)" and "within-market timing not shown".
- **Declared labels** (appended to any non-Unavailable verdict; never change it or its Holm p): E012 "possibly bounce (quote
  noise); mechanical not excluded" unless the 6 h skip-slot check passes (section 2); E013 "flow-quote continuation moderation,
  possibly mechanical" unless the 30-min-early check passes (section 3); "differential attrition" / "attrition-sensitive"
  (section 1.3); "truncation-sensitive" (sections 3, 4); "DRAFT: code hashes not verified" (unpinned runs only).
- **Void:** E012 placebo range excludes 0 (verdict withheld).
- **Unavailable:** below the floors: E012 < 20,000 rows, < 200 events or < 10 UTC days; E013 (each) < 10,000 rows, < 500 events or
  < 10 days; E014 < 1,000 rows or < 100 events in either regime, or < 10 days.

### 1.7 Economics (separate; never changes a primary verdict)
- Paper taker round trip per share: enter at the origin touch, exit at the target touch; long outcome 0 = bid_j − ask_i, short
  (buy outcome 1) = bid_i − ask_j; taker fee on both legs from the origin capture's fee fields (`economics.fee_spec`,
  `resolve_rate` max_if_unknown, `rate · (p(1 − p))^exponent`). No depth, queue or latency: optimistic.
- Event-clustered mean, one-sided p (`battery.mean_test`); valid only with >= 30 trades in >= 10 events
  (`economics.MIN_TRADES`, `MIN_CLUSTERS`). "Covers taker costs (paper)" only if mean > 0 with p < 0.05; otherwise "not shown".
- **Declared in advance:** every development cost check of these families was negative as a taker (F4/F5 net about −2.5c; E007
  +0.36c against about 4.5c round trip), so "not shown" is the expected economics outcome. A Supported primary without it is
  information about forecasting, not a route.

### 1.8 Stop rules
- Fixed end `END_UTC`; the window is never extended. The analysis runs once (q0461 refuses before the date; `--out` refuses to
  overwrite).
- Disk: the module stops writing at 1.5 GB in `live_tests2/` (expected about 0.35 GB); the job exits 75 ("not now") above 40 GiB
  of data-dumps. Either way missing stays missing.
- The job is marked failed after 48 consecutive idle runs (about a day without a new capture); revival with `retry` is an
  operational action logged as a deviation.

### 1.9 Overlaps and dependence (disclosed)
- **E013 and E014 share every trade sample and origin;** E012 shares snapshots with both. Their results are correlated and never
  counted as independent confirmations; Holm treats them as one family.
- E011 (to 2026-11-10) reads the same snapshots for a different, undirected hypothesis. CB-batch SEALED-P windows (CB1-D, CB2,
  CB3, CB5, CB6, CB7, CB13 T_hold, ...) cover the same captures for other hypotheses. No hypothesis here is theirs.
- Repeated markets: rows of a market are dependent; the event is the cluster; UTC day is the second clustering dimension.
- Counting (Methods note M3): the analysis writes one trials line of kind `live_tests2` with **n_tests = 8** = the 4 Holm
  primaries + the 4 declared paper-economics tests (the precedent: economics lines are counted). The count rule is in
  `battery2.KIND_RULES["live_tests2"]` (rule `n_tests`; unit test `test_trial_record_counts_eight`). Not counted (verdict
  conditions or descriptive): the E012 placebo, the E013/E014 timing gates, the skip-slot and 30-min-early label checks,
  attrition bounds, sensitivities and the descriptive economics companions. Holm stays over the 4 primaries (k = 4).

## 2. E012 — 1-day change x liquidity on complete-universe snapshots (SB2 L1)

- **Hypothesis and direction:** the slope of the next-24 h mid change on the past-24 h mid change is higher (less reversal) in
  more liquid markets. Tested term `x · zL`, one-sided, positive (the development sign in h2 and h3).
- **Development evidence (development, historical):** SB2-J1 L1 on `h2_main` +0.062 [+0.028, +0.093], 4/4 months; SB2-J2
  frozen replication on `h3_power` +0.0751 (p 2.3e-9), Holm 0.05 over 6, ratio 1.22, pre/post split +0.071 / +0.079, weighted and
  without-shared-events secondaries agree. L1 re-tests E001 B3's `chg1d_x_logliq` in another frame (disclosed in SB2). Reading
  in SB2: consistent with quote/bounce noise in illiquid prices.
- **Closest prior prospective test (disclosed; challenger R1 finding 2): E006 H1** (EXPERIMENT_LEDGER.md, "Results: E004, E005,
  E006", 2026-10-11): the 1 h version (`chg_1h x log liquidity`, one day of Gamma quotes) was Supported on sign only (theta 0.051,
  p 0.002; reversal weaker in liquid markets), "consistent with bounce", with liquidity-correlated survivorship (target unavailable
  0.66% low vs 0.22% high tercile) and frozen moderator models worse than R. E012 is therefore not a new direction: it asks whether
  the same sign holds at 24 h over 21 days on the complete universe. A Supported E012 adds horizon and duration, not mechanism.
- **Bid/ask bounce is an expected positive channel.** `x = mid_i − mid_h` and `y = mid_j − mid_i` share `mid_i`, so quote noise at
  i alone yields a negative x-y slope that is stronger where quotes are noisier (illiquid, L low), i.e. a positive `x · zL` slope.
  E012 does not test against this channel; it carries a **declared label** unless a bounce-robust check passes (below).
- **Unit:** (market, grid origin). **Grid origins:** the first complete capture in each of [00:00, 02:00), [06:00, 08:00),
  [12:00, 14:00), [18:00, 20:00) UTC (normally the :31 passes). Up to 84 origins.
- **Eligibility at i:** `panel.eligibility_mask` (binary, open, active, two-sided, spread <= 0.10, mid in [0.02, 0.98], end date
  unknown or > capture start + 25 h). **At h** (the slot 12 before i): tight (same quote rule). **At j** (slot 12 after i):
  two-sided (`panel.target_valid`).
- **Frozen definitions:** `x = mid_i − mid_h`; `y = mid_j − mid_i` (Gamma best bid/ask mids); `L = log1p(volume24hr)` at i (NaN
  -> 0); `zL = (L − 1.13294) / 2.25400` (census, section 6.2; scaling changes units only). Controls (each also demeaned): `x`,
  `zL`, logit(mid_i), |mid_i − 0.5|, Gamma `chg_1h` and `chg_1w` with missing flags, `dprev` = mid_i − mid at slot i − 1 (0 if
  missing) with its flag. (`chg_1d` is not a control: `x` replaces it.)
- **Primary test:** expanding-past demeaned OLS (section 1.5) of `y` on `x · zL` given the controls, ordered by capture start
  within market; one-sided p for > 0; seed 20261022.
- **Placebo:** J4-R increment bootstrap, 20 draws, seed 20261122 (section 1.5).
- **6 h skip-slot check (declared; decides the label only):** `x_skip6 = mid_{i−3} − mid_h` (mid at the slot 3 before i, i.e. 6 h
  before, tight at that slot; frozen in the origin line as `x_skip6`, `tight_s3`). It never contains `mid_i`, so quote noise at i
  is not shared with y; a quote would have to stay stale for 6 h to recreate the channel. Same estimator, time clusters and p rule
  as the primary, regressing y on `x_skip6 · zL` with `x_skip6`, `zL` and the controls except `dprev` (which contains `mid_i`).
  **Label rule:** a Supported E012 carries "possibly bounce (quote noise); mechanical not excluded" unless the check is testable,
  its slope is > 0 and >= 0.5 x the primary slope, its one-sided p < 0.05 and its conservative 95% CI lies above 0. Even when the
  check passes, no mechanism claim is made (stale quotes over 6 h in illiquid markets are not excluded).
- **Sample size and MDE (planning):** the census found about 38,000 eligible markets per capture in about 7,600 events; in the
  dry run 23,774 of 35,117 origin rows of a grid capture were tight at h (7,368 events). Over 84 origins, about 2.0 M rows, with
  1-2 x 10^4 distinct events (many recur). Scaling the h3 SE (0.0128; h3 events assumed about 3,000) by sqrt(3,000 / 10,000) gives
  0.0070; times 1.5 for Gamma-mid noise and demeaning attenuation, about 0.0105. With the R1 p rule (t with G − 1 = 10 df for 11
  two-day blocks; t(0.9875, 10) + t(0.8, 10) = 3.51 at the Holm worst case 0.0125, power 0.8): **MDE about 0.037 (range
  0.025-0.046)** (R0, normal reference: 0.032), about half to 0.6 x the development effect. Caveats: the live `x` is a snapshot-mid
  change, not the 10-minute history series, so effect units may not transfer; with 11 blocks the two-way SE is itself noisy and
  likely binding.
- **Economics:** L is 0 for 75.5% of eligible rows (census), so terciles of L are degenerate (both lower cuts 0). Paper rule:
  `L == 0` and |x| >= 0.05: take the side against x (reversal), taker round trip to j. Descriptive companion: `L >= 5.3377`
  (upper tercile of L > 0) and |x| >= 0.05, follow x.
- **Secondary (descriptive):** pooled, within (FE), j-tight, markets >= 20 rows, Gamma `chg_1d` version, UTC-day time clusters,
  leave-one-day-out range, accounting (late, missing_capture, unavailable by reason, not tight at h); attrition L = 0 vs L > 0
  (section 1.3).
- **Non-claims:** no mechanism claim (bounce noise vs information), no tradability claim.

## 3. E013 — 6 h flow continuation moderated by volatility (F4) and spread (F5) (SB2 F4, F5)

- **Hypotheses and direction:** the slope of the next-6 h mid change on 6 h taker flow is higher in more volatile markets (F4:
  `x6 · zRV` > 0) and where the quoted spread is wider (F5: `x6 · zSPR` > 0). Two primaries in the Holm family.
- **Development evidence (development, historical):** SB2-J1 F4 +0.0019 [+0.0011, +0.0026] (BY survivor, 4/4 months, robust to
  a flow window ending 30 min early), F5 +0.0047 [+0.0024, +0.0071]; SB2-J2 on h3: F4 +0.00299 (p 2.7e-8, ratio 1.59), F5 +0.00601
  (p 9.1e-13, ratio 1.27), both Holm 0.05; both weaker in the later half (40-55%). Taker economics negative (net about −2.5c).
- **Unit:** (market, trade sample). Each 2-hourly pass draws 2,000 markets from the active frame (`trade_sample`, stratified,
  inclusion probabilities recorded). Population (`n6h`): tight at i (all frame rows are), end date unknown or > capture start + 7
  h, **origin-capture Gamma `volume24hr` <= `vol24_cap`** (below), at least one signed trade in the 6 h window, window covered.
- **Population cut fixed at the origin (challenger R1 finding 4).** Whether the 6 h window is covered depends on the 500-trade
  page, which runs to request time and so includes trades after the origin; heavy trading just after the origin (which goes with
  large |y6|) truncates the window and would drop the row: selection on the future. The population is therefore cut on an
  origin-side activity measure: `vol24_cap` = the largest origin `volume24hr` v such that, among the pre-window census flow rows
  (tight; >= 1 trade in the 6 h window or a truncated window) with `volume24hr` <= v, the truncated share is <= **1%**
  (`live_tests2.vol24_cap_rule`; ties evaluated together; unknown volume excluded). It is computed **once** from the same
  pre-window census inputs (captures and samples listed in the spec JSON, all started before 2026-10-19T21:00Z; origin-side and
  page fields only, no target) and written into the spec before the pin; a pinned spec with a null cap refuses to run. Residual
  truncation under the cap is counted, and if it exceeds **2%** of the candidates in the window the verdicts carry
  "truncation-sensitive (residual 6 h-window truncation x%)". Post-origin trades on the page stay counts only. The cut narrows
  the population towards less active markets relative to development; that is the price of a causal population and is disclosed,
  not a performance choice.
- **Frozen definitions:** `imb6 = Σ sign · size · price / Σ size · price` over trades with `t − 6 h <= ts < t` (t = the market's
  origin receipt; sign +1 for BUY of outcome 0 or SELL of outcome 1, from `outcome_index`, else asset == token 0; unsigned trades
  excluded); covered if the page held < 500 trades or its oldest trade is at or before t − 6 h; `x6 = clip(imb6, −1, 1) / 0.85782`
  (HB1 FL2 scaling, as SB2). `rv` = rms of consecutive-slot two-sided mid differences over slots k − 12 .. k (series files;
  >= 6 valid differences); `zRV = (log(rv + 1e-4) + 4.88669) / 1.69505`. `SPR` = Gamma spread at i (else ask − bid);
  `zSPR = (SPR − 0.028191) / 0.022417`. Target `y6 = mid(slot k + 3) − mid_i`, two-sided at the target. Controls (each demeaned):
  `x6`, the moderator, logit mid, |mid − 0.5|, Gamma `chg_1h`, `chg_1d`, `chg_1w` with missing flags, `dprev` with its flag.
- **Disclosed deviations from development:** the RV moderator is a 2 h snapshot proxy (dev: 10-minute `ml_rv_1d`), the spread is
  the quoted spread (dev: a trade-based proxy, median |trade price − mid|), the target is the Gamma mid (dev: history series), and
  flow comes from one 500-trade page (truncated windows are NaN, never 0). The z-scales come from the pre-window census.
- **Primary tests:** expanding-past demeaned OLS per test, ordered by origin receipt within market; UTC-day time clusters;
  one-sided p by the section 1.5 rule; seeds 20261023 (F4), 20261024 (F5). **Timing gate** (section 1.5): far-future control
  target, sources >= 12 h later in the same market, >= 4 sources per gate row.
- **Sample size and MDE (planning):** census: about 1,000 rows per sample with 6 h flow in about 800-890 events; RV finite for
  about 95%. Over about 250 samples, about 250,000 rows; distinct events plausibly 5,000-8,000; demeaning drops each market's first
  row (sports markets often appear once or twice). Scaling the h3 SEs (F4 0.00055, F5 0.00086 at 2,100 events) by sqrt(2,100 /
  5,000) and 1.5 for proxy noise and attenuation, with the R1 p rule (t with 20 df: 3.28 instead of 3.08): **F4 MDE about
  0.0017**, **F5 MDE about 0.0028** (dev 0.0047-0.0060). Effect units differ from development (other moderator measures), so these
  are rough; the volume cap and the timing gate (which uses only gate rows) lower power further. **Declared in advance (challenger
  R1 finding 7): F4 is likely underpowered.** F4's development effect fell 40-55% in the later half, so a realistic live effect is
  about 0.0008-0.0016, below the MDE, and the x 1.5 attenuation factor is untested for 2-3-row markets. An Inconclusive F4 is the
  expected outcome and is not evidence against F4.
- **Economics:** favourable (upper) tercile of the moderator (census cuts: log rv >= −4.0124 for F4; spread >= 0.03 for F5) and
  |imb6| >= 0.5: follow sign(imb6), taker round trip to the 6 h target. Descriptive (never a claim): gross mid-to-mid move and a
  maker upper bound (own-side touch entry with a certain fill, exit at the target mid, no fee; no fill model).
- **30-min-early check (declared; decides the label only):** the same fit with the flow window ending 30 min before the origin
  (`x6_lag30`). **Label rule ("null" defined):** a Supported F4/F5 carries "flow-quote continuation moderation, possibly
  mechanical" unless the check is testable, its slope is > 0 and >= 0.5 x the primary slope, and its one-sided p (primary rule)
  is < 0.05; anything else is "null" for this rule.
- **Secondary (descriptive):** pooled, within (FE), weighted (1/p), j6-tight targets, accounting (truncated, no trades, above the
  volume cap, late, unavailable by reason); attrition upper vs lower moderator tercile (section 1.3).

## 4. E014 — near-end gain of the frozen E007 flow model (light proxy of SB2-J8 C-TTE)

- **Hypothesis and direction:** with an **as-of** end date, the mean per-row squared-error gain of E007's frozen augmented model
  (base + signed share) over E007's frozen base model, on rows with 1 h taker flow, is larger when the market is within 24 h of
  its listed end (regime A) than when it is more than 30 days out (regime B). One-sided, A − B > 0.
- **Development evidence (development, historical) and why this proxy:** SB2-J8 replicated C-TTE (direction 2 h: the full ML
  model's log-loss gain over M0v is +0.0188 nats larger < 24 h before the end than > 30 days; robust to the challenger's
  look-ahead, post-end and near-end-market diagnostics, q0100). The challenger asked for an as-of hours-to-end test or a near-end
  conditional rule with a cost check. The full model (MC1) is parked (memory). Flow is the ML family with the only stable positive
  ablation delta, and E007 (flow continuation, frozen) was Supported prospectively, so the frozen E007 pair is the light frozen
  predictor that carries the flow part of C-TTE. **Conflicting development evidence (disclosed):** SB2 F3 (6 h flow x time to end)
  advanced on h2 but did not replicate on h3 (−0.0013, p 0.086, same sign). A null here does not refute C-TTE for the ML model; a
  pass supports "the frozen flow model gains more near the end, with an as-of end date".
- **Frozen predictor:** `model_specs/live_tests2_v1.json` `e014`, copied from `research_lab/e007/dev_fit.json` (sha256
  `7e2c4f79079ced0c74ad1899cfb3536e71f97385c499d9730dd62046560124c6`, E007's frozen development fit): base `0.0010731534 −
  0.1491841967 · chg_1h`; augmented `0.0010113673 − 0.1636280669 · chg_1h + 0.0050342841 · ss`; `ss = signed_volume_1h /
  volume_1h` (0 if no volume), the E007 definition; **NaN if the trade sample flags the 1 h window truncated**
  (`trades_truncated`, challenger R1 finding 4; never a partial value). Both predictions are written into each origin line before
  the target exists.
- **Regimes (as-of):** hours to end = (Gamma `end_date` at the origin capture − origin receipt) / 3600. A: (0, 24]; B: > 720;
  past nominal end (<= 0), middle and unknown are excluded (counted). Nothing after the origin is used to place a row.
- **Unit and population:** (market, trade sample) **tight at the origin** (`tight_i == 1`, the quote rule of section 1.2; all
  active-frame rows normally are; challenger R1 finding 9), `ss` finite and != 0, regime A or B, target two-sided. Target
  `y = mid(slot k + 1) − mid_i` (the next pass, about 2 h, as E007). Gain `g = (y − p_base)^2 − (y − p_aug)^2`.
- **Truncation (counted, labelled):** the 1 h window is truncated only when a full 500-trade page starts after origin − 1 h; such
  rows are excluded (NaN `ss`) and counted per regime. No volume cap is applied for E014 (a 1 h window is rarely truncated; the
  census re-run reports the share); if the truncated share exceeds **2%** in either regime the verdict carries
  "truncation-sensitive (1 h window truncated: ...)".
- **Primary test:** slope of `g` on the regime-A indicator (= mean_A − mean_B), unweighted, event-clustered and two-way event x
  UTC day SEs, one-sided p by the section 1.5 rule (max of event, two-way and t with G − 1 df), 4,000-draw event bootstrap CI;
  seed 20261025. **Timing gate** (section 1.5): far-future control target, sources >= 3 h later in the same market and regime,
  >= 4 sources per gate row, >= 50 gate rows per regime.
- **Sample size and MDE (planning):** census per sample: 308-387 rows with `ss != 0`, of which A 61-113 (43-88 events) and B
  72-102 (68-91 events). Over about 250 samples: A about 20,000 rows, B about 23,000 rows. The gain contrast is, to first order,
  `c · E[ss^2] · 2 (beta_A − beta_B)` (c = 0.00503, the frozen flow coefficient), so power follows the slope contrast. Scaling E007's
  slope SE (about 0.0009 over about 3,800 non-zero rows) and doubling regime A's residual variance (near-end moves are larger):
  SE(beta_A − beta_B) about 0.0009, **slope-equivalent MDE about 0.0030** (Holm worst case, t with 20 df; R0 normal reference
  0.0028), about 0.85 x E007's overall slope:
  detectable only if the near-end flow slope is roughly twice the far one. **Declared in advance: Inconclusive is a likely
  outcome.**
- **Economics:** regime A, |ss| = 1 and >= 3 trades in the hour: follow sign(ss), taker round trip to the 2 h target. Expected
  "not shown" (E007: +0.36c gross vs about 4.5c round trip).
- **Mechanism reading (descriptive, challenger R1 finding 8):** the gain is linear in y, g = 2c·ss·(y − p_base) − c²·ss² plus
  terms from the different intercept and chg_1h coefficient, so the A − B contrast mixes the flow-slope contrast with regime
  differences in E[ss²]. This is valid for the stated hypothesis (the frozen model gains more near the end), but the reading
  "the flow slope is larger near the end" is the **slope contrast** (residual y − p_base on ss, A and ss·A; coefficient of ss·A),
  reported as the named mechanism secondary; it never changes the verdict.
- **Secondary (descriptive):** weighted (1/p), relative-gain contrast `G_A − G_B` (G = 1 − SSE_aug / SSE_base), regime counts
  including past-end rows, accounting (truncated per regime, late against the 2 h target, unavailable by reason per regime);
  attrition A vs B with the pessimistic and worst-case bounds (section 1.3).

## 5. Considered and not chosen
- **SB2-J5 sibling event-level reversal ("L1" of J5):** its own caveats bind (increment over R only, R + L1 < B3, Gamma-mid
  target with the J4 channel); the L1-beyond-B3 and sweep-mid checks were never run. Not ready.
- **F4/F5 as a maker test:** needs fills; CB3 (quote vacuum, selective maker) and CB9 (flow-skewed maker) own that design. E013
  reports only a no-fill maker upper bound, never a claim.
- **C-ACT:** rejected by the challenger (close to mechanical).
- **CB11-CB16:** no screen survivor (CB12-X not identifiable; CB13-T and CB15-E not testable; the rest pending).
- **Full ML C-TTE (MC1):** parked for memory; E014 is the light proxy.
- Not duplicated: q0310 (CB14-W Wikipedia live), q0345/q0352 (CB15), q0257/q0261 (CB12), q0210 (CB10), CB8-H holders, CB17.

## 6. Engineering

### 6.1 Code and tests
- `backend/astrolabe/research_lab/live_tests2.py` (collector, freezers, outcomes, ops counts, census),
  `backend/astrolabe/research_lab/live_tests2_analysis.py` (the single analysis), `backend/scripts/run_live_tests2.py`
  (`run`, `ops-stats`, `census`, `analyze`), spec `backend/astrolabe/research_lab/model_specs/live_tests2_v1.json`.
- `backend/tests/unit/test_research_lab_live_tests2.py` (35 test functions, 41 cases with parameters): write-once, slot grid,
  spec sha guard, end-to-end freeze -> outcomes -> idempotent re-run with byte-identical files, causality (future captures with
  wild prices leave frozen lines unchanged), late refusal and its final marker, missing target capture, flow sign convention
  (outcome-1 trades, token-0 fallback, trades after the origin and outside the window excluded), truncated 6 h window -> NaN,
  truncated 1 h window -> `ss` NaN and `vol24_i` recorded, the volume-cap rule, status files give the unavailable reason,
  attrition summary and E014 bounds, E012 skip slot frozen, E014 frozen predictions and regimes, increment rebuild keeps run
  starts, planted-interaction recovery (and attenuation), the t(G − 1) primary p rule, gate source separation, **timing-gate null
  size** (E013: iid, AR(1), overlapping windows, overlapping with missing rows; E014: iid, AR(1), market-constant, overlapping;
  300 worlds each, rejection within the 99% binomial bound at 0.05) and **power**, the E012 and E013 label rules, the trials line
  counts 8, paper P&L conventions, E014 planted near-end gain passes the gate while a market-constant flow fails it, code-hash
  normalisation and the spec map matching the modules, pinned analysis keeps only registered lines (spec and code sha) and
  refuses a hash mismatch or a null volume cap, end-to-end analysis (Holm m = 4, refuses before the date), `ops-stats` reads no
  price column.

### 6.2 Census and host dry run (2026-10-19 ~21:35-21:45Z; `/tmp/livetest2`, deleted; nothing written under `~/arepo`)
- **Census** (`--until 2026-10-19T21:00Z`, 4 captures 14:31-20:31Z, 4 samples): zL centre 1.13294 / scale 2.25400 (n 153,711;
  75.5% of L = 0; L > 0 tercile cuts 3.699 / 5.338); log rv centre −4.88669 / scale 1.69505 (n 3,891; tercile cuts −5.4065 /
  −4.0124); spread centre 0.028191 / scale 0.022417 (n 4,142; cuts 0.01 / 0.03). Eligible markets per capture 37,923-39,254 in
  7,570-7,664 events. Origin-side fields only.
- **Dry run** (`run --dry-run-start 2026-10-19T00:00Z --dry-run-end 2026-10-20T00:00Z`, unpinned spec, all lines
  `prospective_unregistered`): first run wrote 24 series, 4 E012 frozen, 11 flow frozen and 8 flow outcome files in 3 min 23 s,
  peak RSS 660 MB under a 1.2 GB address-space cap. Shapes: series 132,068 x 7 (0.84 MB); E012 frozen 35,117 x 33 (0.9-1.0 MB;
  23,774 with x; 7,368 events); flow frozen 2,000 x 47 (994 with x6, 1,930 with rv, 308 with ss != 0); flow outcomes 2,000 x 15.
  Operational status counts only: 15,929 / 16,000 two-sided at 2 h, 15,629 / 16,000 at 6 h. Steady state: one capture + one sample
  12.6 s, 458 MB RSS; a 4-item run 35 s, 471 MB RSS, both under a 960 MB cap (= 2 x mem_mb 480); an idle run 1.5 s, 117 MB, exit
  75. No statistic on any target was computed.
- **Owed before the pin (R1):** (a) one re-run of `run_live_tests2.py census --until 2026-10-19T21:00:00Z` on the same pre-window
  inputs (ids in the spec JSON `census`) to fill `flow.vol24_cap` and report the 6 h / 1 h truncation shares (the 2026-10-19 run
  predates the `vol24_i` and `trunc1h` columns; origin-side and page fields only, no target); (b) a short host dry run of the R1
  collector (status files, skip slot) to confirm RSS stays under the 960 MB cap; (c) `sha256sum` of the host's
  `research_lab/e007/dev_fit.json` against the value in section 4 (not verified by the challenger); (d) refresh `code_sha256` in
  the spec after the last code change, then pin `SPEC_SHA256`. Trade `ts` is in epoch seconds, the unit `trade_sample` itself
  compares with the origin epoch (`trade_sample.py:301`).

## 7. Open questions for the challenger (round 0; answered by R1, see section 9)
1. Is the regressor-rotation **timing gate** (E013, E014) the right matched placebo, and is "fails the gate -> p = 1 in Holm" the
   right treatment? The J4-R range rule is miscalibrated for it (section 1.5; unit-tested).
2. E013 primary uses **expanding-past demeaning** although development was pooled. It removes the between-market channel J4 found,
   at the cost of attenuation and of dropping one-off markets. Pooled is a sensitivity. Accept, or make pooled primary with the gate?
3. E012 uses the snapshot-mid 24 h change (same measurement as the target, as in development's series) rather than Gamma's
   `oneDayPriceChange` (a sensitivity). The bounce-noise reading makes a positive E012 likely; is it still worth one Holm slot?
4. E014 is a **light proxy** of C-TTE (frozen E007 flow model, squared-error gain, 2 h target), and F3 (flow x time to end) did
   not replicate. Keep in the family, or move it out as a separate single-test registration?
5. Census scales were fixed from 4 pre-window captures/samples. They change units and the economics cuts only; acceptable?
6. Lane and memory: `mem_mb 480` (blackout-exempt) relies on the measured 471 MB RSS under a 960 MB cap. A cron-lane install (as
   CB14-W) is the alternative if the queue's net lane is busy for long stretches (a freeze delayed past the next pass is lost as
   late for E014).
7. The 6 h flow window comes from a single 500-trade page; heavy markets lose coverage (NaN), a selection towards less active
   markets that is outcome-blind but changes the population relative to development.
8. Counting: a `live_tests2` kind for `battery2.count_line` is needed before q0461 (4 counted tests).

## 8. Draft ledger block (DRAFT, not registered, not counted)

> ## E012-E014 — Live tests 2 (LT2): DRAFT pre-registration (not registered, nothing counted)
> - **Design:** `docs/research_lab/LIVE_TESTS_2.md` (sections 1-4). Code `live_tests2.py`, `live_tests2_analysis.py`,
>   `run_live_tests2.py`; spec `model_specs/live_tests2_v1.json` (sha pinned at registration); queue drafts q0460 (collector, net
>   lane, mem 480 MB) and q0461 (analysis, not before 2026-11-13T12:00Z).
> - **E012:** 1-day change x liquidity (SB2 L1, development-replicated; closest prior prospective test E006 H1, 1 h, Supported on
>   sign, "consistent with bounce") on 6-hourly complete-universe grid origins, 24 h Gamma-mid target, expanding-past demeaned
>   OLS, two-day-block time clusters, J4-R placebo, 6 h skip-slot bounce label; planning MDE about 0.037 vs dev 0.062-0.075.
> - **E013:** 6 h flow x volatility (F4) and x spread (F5) (SB2, development-replicated) on trade samples, origin-side volume cap,
>   6 h target, same estimator (UTC-day clusters) plus a far-future-control timing gate; planning MDE F4 about 0.0017 (likely
>   underpowered), F5 about 0.0028 (dev 0.0047-0.0060).
> - **E014:** near-end (as-of <= 24 h) minus far (> 30 d) squared-error gain of the frozen E007 flow model over its base (light
>   proxy of SB2-J8 C-TTE), 2 h target, far-future-control timing gate; slope-equivalent MDE about 0.0030; Inconclusive likely.
> - **Family:** Holm over the 4 primaries (k = 4), one-sided, alpha 0.05; primary p = max(event, two-way, t with G − 1 df).
>   Counted tests 8 (4 primaries + 4 paper-economics). Window: origins `[2026-10-22T00:00Z, 2026-11-12T00:00Z)`; single analysis
>   on or after 2026-11-13T12:00Z. Economics: paper taker round trips, expected "not shown".
> - **Status:** DRAFT; challenger R1 REVISE x 4 answered (section 9), awaiting the R1 re-check; no line is
>   `prospective_confirmation` until the spec sha is pinned.

## 9. Response to challenger R1 (2026-10-20; `reviews/LT2_CHALLENGER_R1_2026-10-20.md`, REVISE x 4)

Design only; no outcome of the window was read for any change below (the window has not started); no threshold, floor, alpha or
direction was loosened. Every change makes a test harder to pass, adds a label, or adds accounting.

| # | Finding | Change | Where | Scientific justification |
|---|---|---|---|---|
| 1 | HIGH: the ±1 cyclic-shift gate is not a valid null (rotated flow overlaps the real window / target; too few distinct shuffles) | Gate replaced by a **far-future control target**: sources = later rows of the same market (E014: and regime) >= flow window + horizon later (E013 12 h, E014 3 h), >= 4 sources per gate row; statistic on `y − y_far` (E013 slope) / `gain(y) − gain(y_far)` (E014 A − B); p_gate = max(CR1, delete-one-event jackknife) under t(G − 1); gate floors. Simulated null size 0.046-0.055 in 8 scenarios incl. AR(1) and overlapping windows (1,500 worlds each; unit tests 300) | §1.5; `slope_gate`, `contrast_gate`, `forward_sources`; size and power tests | A market-level flow-drift link affects y and y_far alike and cancels; the separation rule guarantees no overlap of windows or targets, the reviewer's mechanism (a); the gate no longer depends on a permutation count, so (b) is gone; the source rows are later only because earlier rows already enter the expanding-past demeaned regressors. Autocorrelated flow attenuates the statistic (conservative), shown not to inflate size |
| 2 | HIGH/MED: E012 predicted by bid/ask bounce; E006 H1 not cited; one-slot skip | E006 H1 disclosed as the closest prior prospective test; bounce stated as an expected positive channel; **6 h skip-slot check** `x_skip6 = mid_{i−3} − mid_h` frozen in each line, with a declared label rule (Supported E012 labelled "possibly bounce" unless the check passes with slope > 0, >= 0.5 x primary, p < 0.05, CI above 0) | §2; `freeze_e012`, `e012_label`, `check_slope_label` | Ruling 3: keep E012 with the disclosure and the 6 h label. The 6 h gap removes shared quote noise at i; a label (not a new primary) keeps the registered hypothesis unchanged and avoids adding a Holm slot |
| 3 | MED: attrition by resolution not measurable | Per-capture **status files** (closed / inactive / one-sided; absent = in neither file), detailed `unavailable_*` reasons in outcomes; declared rule: unavailable share differs by > 5 pp between pre-declared groups (E012 L = 0 vs L > 0; E013 moderator terciles; E014 A vs B) -> "differential attrition" label + declared pessimistic bound (E014 also Manski worst case); bound <= 0 -> "attrition-sensitive" | §1.2, §1.3; `status_frame`, `unavailable_status`, `attrition_summary`, `pessimistic_refit`, `e014_attrition_bounds` | Must be written at collection time because files are write-once and snapshots may be retired; the groups are origin-side, fixed now |
| 4 | MED: 6 h coverage selects on post-origin trades; E014 ignores truncation | E013 population cut on origin `volume24hr` <= `vol24_cap` (cap fixed once from the pre-window census at <= 1% truncated); residual truncation counted, label above 2%; E014 `ss` = NaN when `trades_truncated`, counted per regime, label above 2% | §1.3, §3, §4; `vol24_cap_rule`, `truncation_census`, `freeze_flow`; analysis refuses a pinned spec with a null cap | Eligibility is fixed at the origin; the cut is causal and outcome-blind. It narrows the population (disclosed) for validity, not performance. The 2% label threshold is fixed before any window data exist |
| 5 | MED: day-level inference optimistic (21 clusters; 24 h overlap across midnight; normal reference) | Primary p = max(p_event, p_twoway, p_t with G − 1 df); E012 time clusters = **two-day blocks** (11), E013/E014 UTC days (21); conservative CI includes beta ± t(0.975, G − 1) se_twoway; MDEs recomputed (E012 0.037, F4 0.0017, F5 0.0028, E014 0.0030) | §1.5, §2-4, §0; `p_primary`, `_tblock` | t(G − 1) is the standard small-G reference for cluster-robust tests; two-day blocks halve the cross-boundary target overlap for E012; taking the max of three p values can only raise p |
| 6 | MED: code/spec mismatches | Late rule restated per test (E012 24 h target; flow refused at the 6 h target; per-test lateness at analysis); counting stated as **8** (4 primaries + 4 economics; Holm k = 4), `battery2` rule present; E013 "possibly mechanical" label implemented with "null" defined; effective start enforced by `spec_sha` + `code_sha` per line and pinned module hashes (`code_sha256` map, refuse on mismatch) | §0, §1.1, §1.2, §1.9, §3; `code_check`, `_load_pairs`, `trial_record`, `analyze` | Spec and code now say the same thing; the pins are checked by unit tests |
| 7 | LOW: power weaker than stated | "F4 likely underpowered" declared, realistic effect 0.0008-0.0016 vs MDE 0.0017; Inconclusive F4 is not evidence against F4 | §0, §3 | Honest power statement; no design change needed |
| 8 | LOW: E014 gain mixes two terms | Slope contrast named as the mechanism reading (descriptive), decomposition written out | §4; `mechanism_reading` | The registered hypothesis is about the model's gain; the mechanism reading is separate |
| 9 | LOW: E014 requires `tight_i == 1` in code only | Spec now states the tight-at-origin requirement | §4 | Spec matches code |
| — | Not verified: census ids; E007 `dev_fit.json` sha; trade `ts` units; truncated share of the census; E007 / flow_screen overlap | Census ids are in the spec JSON; `ts` is epoch seconds (`trade_sample.py:301`); the `dev_fit.json` sha and truncation shares are owed before the pin (§6.2); the flow_screen / E007 overlap is disclosed in §1.4 and §1.9 | §1.4, §1.9, §6.2 | Items that need the host are listed as owed, not claimed |

**Rulings on §7 adopted:** (1) gate idea and "fail -> p = 1" kept, with the fix above; (2) expanding-past demeaning stays
primary, pooled a sensitivity; (3) E012 kept with the E006 disclosure and the 6 h label; (4) E014 kept in the family;
(5) census scales kept, ids recorded; (6) lane unchanged, late losses counted; cron lane if the net lane backs up (operational);
(7) replaced by the volume cap (finding 4); (8) counting 8 stated.

**Registration timing.** All R1 code and spec changes are in this revision. Still needed before the pin: the R1 re-check, the
census re-run (fills `vol24_cap`), a short host dry run, the `dev_fit.json` sha check and the `code_sha256` refresh (§6.2). If
the registration commit (pin + ledger) is not made before **2026-10-22T00:00Z**, section 1.1 applies unchanged: `REGISTERED_UTC`
moves to the first 00:00Z at least 2 h after the commit (for a commit on 2026-10-22 before 22:00Z: 2026-10-23T00:00Z, window
`[2026-10-23T00:00Z, 2026-11-13T00:00Z)`, analysis not before 2026-11-14T12:00Z), recorded in the ledger; no data are inspected
for that decision.
