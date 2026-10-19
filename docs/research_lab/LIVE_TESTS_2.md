# Live tests 2 (LT2): E012, E013, E014 — DRAFT pre-registrations

**Status: DRAFT, not registered, nothing counted.** Drafted 2026-10-19 (~21:50Z) on branch `feat/live-tests-2`. Registration
needs, in order: a challenger review (`science-reviewer`) of this file and of the code, the fixes, the `SPEC_SHA256` pin in
`backend/astrolabe/research_lab/live_tests2.py`, the ledger entries (draft block in section 8) and the promotion of the queue
draft `q0460`. Until the pin exists, every line the code writes is `prospective_unregistered` by construction.

Research tooling only. No edge, calibration, profitability or tradability claim exists or is implied. Development numbers
quoted here are **development (historical)** evidence and are labelled as such.

## 0. Summary

| ID | Hypothesis (direction) | Development evidence | Stream (already captured) | Primary | MDE (planning, Holm worst case) |
|---|---|---|---|---|---|
| **E012** | The 24 h change carries forward more (reverses less) in liquid markets: slope of `x · zL` > 0 | SB2 L1, development-replicated (h2 +0.062, h3 +0.075, Holm 0.05; ratio 1.22; stable across halves) | complete-universe snapshots, 6-hourly grid origins, 24 h target | expanding-past demeaned OLS, one-sided p (event; event x UTC day) | about 0.032 (range 0.022-0.040) vs dev 0.062-0.075 |
| **E013-F4** | 6 h taker flow continues more in volatile markets: slope of `x6 · zRV` > 0 | SB2 F4, development-replicated (h2 +0.0019, BY survivor; h3 +0.0030) | trade samples (6 h flow) + snapshots (RV proxy, 6 h target) | same estimator, plus a within-market timing gate | about 0.0016 vs dev 0.0019-0.0030 |
| **E013-F5** | 6 h taker flow continues more where the spread is wide: slope of `x6 · zSPR` > 0 | SB2 F5, development-replicated (h2 +0.0047; h3 +0.0060) | same | same | about 0.0026 vs dev 0.0047-0.0060 |
| **E014** | The frozen E007 flow model gains more over its frozen base in the last 24 h before the as-of end date than more than 30 days out | SB2-J8 C-TTE, development-replicated as an ML-model contrast (+0.0188 nats, CI [0.0094, 0.0292]); E007 flow continuation supported prospectively | trade samples (1 h flow, E007 frozen coefficients) + snapshots (as-of end date, 2 h target) | mean per-row squared-error gain, A minus B, one-sided p, plus a within-market timing gate | slope-equivalent about 0.0028 (moderate power; Inconclusive is a likely outcome) |

- **One Holm family over the four primaries** (E012, E013-F4, E013-F5, E014): one-sided, familywise alpha 0.05. A primary that is
  unavailable, void, placebo-biased or fails its timing gate enters Holm with p = 1. This family is separate from E009-E011.
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
- **Effective start** = max(REGISTERED_UTC, first capture processed by `q0460` running the registration commit). The analysis
  keeps only lines whose `spec_sha` equals the pinned spec (16 hex digits) and whose role is `prospective_confirmation`.
- Nothing in the window has been read: the census (section 6.2) used captures and samples that started before
  2026-10-19T21:00Z and read no target. J4-R's fresh window (2026-10-16 to 2026-10-21, SCREENING_BATCH_2.md J4-R) ends before ours.

### 1.2 Data and the collector (`q0460`, `live_tests2.run_once`)
- **Inputs (read-only, no network):** complete captures `research_lab/snapshots/<id>/rows.csv.gz` (+ `rows_ext.csv.gz` for fee
  fields) and active-frame trade samples `research_lab/trade_samples/<id>/` (plan, manifest, features, trades). Nothing else.
- **Slots:** captures are mapped to the collector's 2 h grid (`grid0 = 2026-10-01T00:31Z`, tolerance 30 min). The first complete
  capture of a slot is used.
- **Outputs** (`research_lab/live_tests2/`), every data file **write-once** (atomic hard-link; an existing file is never touched):
  `series/<capture>.csv.gz` (two-sided quotes of open binary markets per capture, from REGISTERED_UTC − 26 h),
  `e012/frozen/`, `flow/frozen/`, `e012/outcomes/`, `flow/outcomes/`, `passes.jsonl` (append-only log), `state.json` (cache only).
- **Origin features** use the origin capture, earlier captures (series) and, for flow, trades strictly before the origin row's
  receipt time. Targets come only from the target capture's series file.
- **Late rule:** a freeze is refused once the earliest target slot may have started (`now >= slot time − 60 s`); a `.late`
  marker records it and the origin is lost (counted). At analysis, a line whose `frozen_utc` is not strictly before its target
  capture's start is excluded and counted (`late`).
- **Clocks:** origin = each row's receipt time (`received_utc`); slot membership = capture start; trades use their venue `ts`.

### 1.3 Missing data (never imputed)
- Origin capture or trade sample missing (collector outage, failed pass, skipped for disk): no lines; counted from slot gaps.
- Target capture missing 3 h after its slot: `missing_capture`. Market absent or not two-sided at the target: `unavailable`
  (absent and one-sided are not distinguished; resolved markets leave the open-market listing and land here).
- `x` (E012) is NaN unless the market was tight at h; `x6` (E013) is NaN if the 6 h window is not covered by the 500-trade page
  or holds no trade; `rv` is NaN with fewer than 6 valid 2 h differences; such rows are excluded from that test only.
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
  planted 0.5 reads about 0.44 with 20 rows per market), so it is conservative. SEs: event-clustered and two-way event x UTC day
  (CR1, `battery.beta_test`); one-sided p = the larger of the two. CI: 2,000-draw event-cluster bootstrap; the conservative CI is
  the hull of the bootstrap CI and beta ± 1.96 max-SE.
- **E012 placebo (J4-R, matched):** 20 draws; per market the 2 h mid series is rebuilt from the market's pooled valid increments
  drawn with replacement, each contiguous run from its observed start level; `x`, `y`, `dprev`, logit mid and |mid − 0.5| are
  recomputed; tightness flags, volume and Gamma change fields stay as observed. J4-R reading rule: VOID if the 2.5-97.5% range of
  placebo betas excludes 0; "inconclusive (placebo bias)" if |mean placebo beta| > 0.5 x the real max-SE.
- **E013 and E014 timing gate (new; the J4-R reading rule is miscalibrated for regressor-only placebos):** each draw rotates every
  market's flow series (time order) by a random non-zero offset; one-row markets lose their flow. A draw keeps the market's flow
  multiset and its link to the market's level and breaks only the timing. Gate: p_perm = (1 + #{draw >= real}) / (1 + draws)
  < 0.05 (E013: 200 draws per test; E014: 1,000 draws, on rows of markets with >= 2 rows). Reason recorded in the code tests: with a
  regressor-only shift the draws scatter around the realised between-market component, whose own sampling noise is of the order
  of the SE, so a "range covers 0" rule fails by chance. `between_share` = mean draw / real is reported (within/between breakdown).
- **Sensitivities (reported, not tested):** pooled (no demeaning), full-sample market demeaning (within slope), j-tight targets,
  markets with >= 20 rows (E012), Gamma `oneDayPriceChange` in place of `x` (E012), flow window ending 30 min early (E013), 1/p
  inclusion weights (E013, E014), relative-gain contrast and slope contrast (E014), leave-one-UTC-day-out range (E012).

### 1.6 Verdicts (per primary, after Holm over 4)
- **Supported (exploratory, prospective):** Holm-adjusted one-sided p < 0.05, estimate > 0, placebo family OK (E012) or timing
  gate passed (E013, E014).
- **Contradicted:** conservative 95% CI entirely below 0.
- **Inconclusive:** otherwise, including "inconclusive (placebo bias)" and "within-market timing not shown".
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
- Counting (Methods note M3): the analysis adds 4 counted tests. `battery2.cumulative_count` is fail-closed on unknown kinds, so
  a count rule for kind `live_tests2` (one per primary) must be added before q0461 runs.

## 2. E012 — 1-day change x liquidity on complete-universe snapshots (SB2 L1)

- **Hypothesis and direction:** the slope of the next-24 h mid change on the past-24 h mid change is higher (less reversal) in
  more liquid markets. Tested term `x · zL`, one-sided, positive (the development sign in h2 and h3).
- **Development evidence (development, historical):** SB2-J1 L1 on `h2_main` +0.062 [+0.028, +0.093], 4/4 months; SB2-J2
  frozen replication on `h3_power` +0.0751 (p 2.3e-9), Holm 0.05 over 6, ratio 1.22, pre/post split +0.071 / +0.079, weighted and
  without-shared-events secondaries agree. L1 re-tests E001 B3's `chg1d_x_logliq` in another frame (disclosed in SB2). Reading
  in SB2: consistent with quote/bounce noise in illiquid prices; that reading is not tested here.
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
- **Sample size and MDE (planning):** the census found about 38,000 eligible markets per capture in about 7,600 events; in the
  dry run 23,774 of 35,117 origin rows of a grid capture were tight at h (7,368 events). Over 84 origins, about 2.0 M rows, with
  1-2 x 10^4 distinct events (many recur). Scaling the h3 SE (0.0128; h3 events assumed about 3,000) by sqrt(3,000 / 10,000) gives
  0.0070; times 1.5 for Gamma-mid noise and demeaning attenuation, about 0.0105. With z = 2.24 + 0.84 (Holm worst case 0.0125,
  power 0.8): **MDE about 0.032 (range 0.022-0.040)**, about half the development effect. Caveats: the live `x` is a snapshot-mid
  change, not the 10-minute history series, so effect units may not transfer; 21 UTC days make the two-way SE the likely binding
  one.
- **Economics:** L is 0 for 75.5% of eligible rows (census), so terciles of L are degenerate (both lower cuts 0). Paper rule:
  `L == 0` and |x| >= 0.05: take the side against x (reversal), taker round trip to j. Descriptive companion: `L >= 5.3377`
  (upper tercile of L > 0) and |x| >= 0.05, follow x.
- **Secondary (descriptive):** pooled, within (FE), j-tight, markets >= 20 rows, Gamma `chg_1d` version, leave-one-day-out
  range, accounting (late, missing_capture, unavailable, not tight at h).
- **Non-claims:** no mechanism claim (bounce noise vs information), no tradability claim.

## 3. E013 — 6 h flow continuation moderated by volatility (F4) and spread (F5) (SB2 F4, F5)

- **Hypotheses and direction:** the slope of the next-6 h mid change on 6 h taker flow is higher in more volatile markets (F4:
  `x6 · zRV` > 0) and where the quoted spread is wider (F5: `x6 · zSPR` > 0). Two primaries in the Holm family.
- **Development evidence (development, historical):** SB2-J1 F4 +0.0019 [+0.0011, +0.0026] (BY survivor, 4/4 months, robust to
  a flow window ending 30 min early), F5 +0.0047 [+0.0024, +0.0071]; SB2-J2 on h3: F4 +0.00299 (p 2.7e-8, ratio 1.59), F5 +0.00601
  (p 9.1e-13, ratio 1.27), both Holm 0.05; both weaker in the later half (40-55%). Taker economics negative (net about −2.5c).
- **Unit:** (market, trade sample). Each 2-hourly pass draws 2,000 markets from the active frame (`trade_sample`, stratified,
  inclusion probabilities recorded). Population (`n6h`): tight at i (all frame rows are), end date unknown or > capture start + 7
  h, at least one signed trade in the 6 h window, window covered.
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
- **Primary tests:** expanding-past demeaned OLS per test, ordered by origin receipt within market; one-sided p; seeds 20261023
  (F4), 20261024 (F5). **Timing gate** (section 1.5): 200 within-market flow rotations per test.
- **Sample size and MDE (planning):** census: about 1,000 rows per sample with 6 h flow in about 800-890 events; RV finite for
  about 95%. Over about 250 samples, about 250,000 rows; distinct events plausibly 5,000-8,000; demeaning drops each market's first
  row (sports markets often appear once or twice). Scaling the h3 SEs (F4 0.00055, F5 0.00086 at 2,100 events) by sqrt(2,100 /
  5,000) and 1.5 for proxy noise and attenuation: **F4 MDE about 0.0016** (dev 0.0019-0.0030), **F5 MDE about 0.0026** (dev
  0.0047-0.0060). Effect units differ from development (other moderator measures), so these are rough.
- **Economics:** favourable (upper) tercile of the moderator (census cuts: log rv >= −4.0124 for F4; spread >= 0.03 for F5) and
  |imb6| >= 0.5: follow sign(imb6), taker round trip to the 6 h target. Descriptive (never a claim): gross mid-to-mid move and a
  maker upper bound (own-side touch entry with a certain fill, exit at the target mid, no fee; no fill model).
- **Secondary (descriptive):** pooled, within (FE), weighted, flow window ending 30 min early (E007's "flow-quote continuation"
  caveat: if the primary passes and this is null, the label is "flow-quote continuation moderation, possibly mechanical"),
  j6-tight targets, accounting.

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
  volume_1h` (0 if no volume), the E007 definition. Both predictions are written into each origin line before the target exists.
- **Regimes (as-of):** hours to end = (Gamma `end_date` at the origin capture − origin receipt) / 3600. A: (0, 24]; B: > 720;
  past nominal end (<= 0), middle and unknown are excluded (counted). Nothing after the origin is used to place a row.
- **Unit and population:** (market, trade sample) with `ss != 0`, regime A or B, target two-sided. Target `y = mid(slot k + 1) −
  mid_i` (the next pass, about 2 h, as E007). Gain `g = (y − p_base)^2 − (y − p_aug)^2`.
- **Primary test:** slope of `g` on the regime-A indicator (= mean_A − mean_B), unweighted, event-clustered and two-way event x
  UTC day SEs, one-sided p (larger of the two), 4,000-draw event bootstrap CI; seed 20261025. **Timing gate:** 1,000 within-market
  rotations of `ss` on rows of markets with >= 2 rows (section 1.5).
- **Sample size and MDE (planning):** census per sample: 308-387 rows with `ss != 0`, of which A 61-113 (43-88 events) and B
  72-102 (68-91 events). Over about 250 samples: A about 20,000 rows, B about 23,000 rows. The gain contrast is, to first order,
  `c · E[ss^2] · 2 (beta_A − beta_B)` (c = 0.00503, the frozen flow coefficient), so power follows the slope contrast. Scaling E007's
  slope SE (about 0.0009 over about 3,800 non-zero rows) and doubling regime A's residual variance (near-end moves are larger):
  SE(beta_A − beta_B) about 0.0009, **slope-equivalent MDE about 0.0028** (Holm worst case), about 0.8 x E007's overall slope:
  detectable only if the near-end flow slope is roughly twice the far one. **Declared in advance: Inconclusive is a likely
  outcome.**
- **Economics:** regime A, |ss| = 1 and >= 3 trades in the hour: follow sign(ss), taker round trip to the 2 h target. Expected
  "not shown" (E007: +0.36c gross vs about 4.5c round trip).
- **Secondary (descriptive):** weighted (1/p), relative-gain contrast `G_A − G_B` (G = 1 − SSE_aug / SSE_base), slope contrast
  (residual on ss, A, ss·A), regime counts including past-end rows, accounting.

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
- `backend/tests/unit/test_research_lab_live_tests2.py` (20 tests): write-once, slot grid, spec sha guard, end-to-end freeze ->
  outcomes -> idempotent re-run with byte-identical files, causality (future captures with wild prices leave frozen lines
  unchanged), late refusal and its final marker, missing target capture, flow sign convention (outcome-1 trades, token-0 fallback,
  trades after the origin and outside the window excluded), truncated window -> NaN, E014 frozen predictions and regimes, cyclic
  shift never keeps a value, increment rebuild keeps run starts, planted-interaction recovery (and attenuation), paper P&L
  conventions, E014 planted near-end gain passes the gate while a market-constant flow fails it, end-to-end analysis (Holm m = 4,
  refuses before the date), `ops-stats` reads no price column.

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

## 7. Open questions for the challenger
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
> - **E012:** 1-day change x liquidity (SB2 L1, development-replicated) on 6-hourly complete-universe grid origins, 24 h Gamma-mid
>   target, expanding-past demeaned OLS, J4-R placebo; planning MDE about 0.032 vs dev 0.062-0.075.
> - **E013:** 6 h flow x volatility (F4) and x spread (F5) (SB2, development-replicated) on trade samples, 6 h target, same
>   estimator plus a within-market timing gate; planning MDE F4 about 0.0016 (dev 0.0019-0.0030), F5 about 0.0026 (dev 0.0047-0.0060).
> - **E014:** near-end (as-of <= 24 h) minus far (> 30 d) squared-error gain of the frozen E007 flow model over its base (light
>   proxy of SB2-J8 C-TTE), 2 h target, timing gate; slope-equivalent MDE about 0.0028; Inconclusive likely.
> - **Family:** Holm over the 4 primaries, one-sided, alpha 0.05. Window: origins `[2026-10-22T00:00Z, 2026-11-12T00:00Z)`;
>   single analysis on or after 2026-11-13T12:00Z. Economics: paper taker round trips, expected "not shown".
> - **Status:** DRAFT awaiting the challenger review; no line is `prospective_confirmation` until the spec sha is pinned.
