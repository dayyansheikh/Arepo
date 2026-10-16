# Historical exploratory ML development run (`h2_main`)

`evidence_role: exploratory_historical` | provenance `EXPLORATORY_HISTORICAL` | status: DEVELOPMENT, post-hoc.

This is not prospective confirmation, it is not pooled with the prospective panel, and it supports no edge,
calibration or profitability claim. It exists to debug the ML pipeline and to see which feature families are
worth carrying into the prospective collection. All numbers below come from
`data-dumps/research_lab/history/h2_main/ml_history_results_*.json` (not committed) and from the matching
`ml_fit`, `ml_score` and `ml_explain` lines in `docs/research_lab/trials.jsonl` (stamped with `revision`).

## What was built

* `backend/astrolabe/research_lab/history_backfill.py`, `backend/scripts/backfill_history.py`: seeded,
  resumable backfill from public Gamma `markets`, CLOB `prices-history` (10-minute fidelity) and Data API
  `trades`. Wallets are stored only as `wallet_sidecar.hash_wallet` output (HMAC-SHA256, lower-cased address,
  raw key bytes from `~/.arepo/wallet_hash_key`). The backfill pauses inside the collector window and while the
  live pass runs.
* `backend/scripts/run_ml_history.py`: walk-forward ML run using `ml_panel` folds, `ml_models` arms and
  `ml_explain.ablation_study`. Optional `--book-table` / `--wallet-age-table` joins (NaN where absent).

## Endpoint facts (probe, 2026-10-11)

* `prices-history`: for closed markets `interval=max` returns nothing at 10-minute fidelity. Explicit
  `startTs`/`endTs` windows of at most 14 days work (30 days returns HTTP 400). Timestamps are venue unix
  seconds. The value `p` rarely equals any trade price (mean absolute difference about 0.01), so it is
  mid-like or derived. Whether a stamp marks the start or end of its interval cannot be verified, so a point
  is treated as known only from stamp + 600 s, strictly before the origin.
* Data API `trades`: newest first, `limit` up to 10000, `offset` capped at 10000; 41 of 3200 markets were
  truncated and their flow features are NaN wherever the window is not covered. About 5 req/s was sustained
  (one HTTP 429 in the first run, none in the main run).
* Gamma `markets`: offset is capped near 2100; the keyset cursor is signed, so random jumps are impossible.
  One day of closed markets can exceed 20,000 rows (mostly short crypto markets).

## Frame, sample and coverage

* Frame (`frame-v2-random-windows`): for each day of the last 270 days, 6 seeded random 15-minute windows;
  closed markets are selected by `endDate` in the window and active markets by `startDate` in the window,
  read in id order up to 3 pages per window (370 of 1626 closed windows hit the page cap, 11 of 1626 active).
  254,379 binary markets entered the frame. **No volume or liquidity filter.**
* Sample: 3,200 markets (2,786 closed, 414 active), seeded square-root allocation over `status x fee_category x
  creation month` (creation-known attributes only). Fetched: 6.3M price points and 875k trades, 202 MB.
* Panel: 1,759 markets (1,388 closed, 371 active) and 420,937 origins on a 2-hour UTC grid from 2025-09-05 to
  2026-10-11 (most origins in 2026-03 to 2026-10). Crypto contributes only 77 of 812 sampled markets because
  short-lived markets rarely survive the one-day lag requirement (the first origin is one day after the first
  price point), so **the panel under-represents markets that live less than about a day**. About 21% of sampled
  markets had zero trades.
* Exclusions the frame/panel imply: non-binary markets; closed markets ending outside the lookback; active
  markets listed outside it; everything outside the random windows (about 6.25% of the time axis); markets
  beyond page 3 of a capped window (highest ids); markets with no price history or under one day of it; origins
  with price outside [0.02, 0.98] or no series point within 2 hours.
* Survivorship: no final volume or outcome enters the frame or the panel membership. Panel membership is
  `createdAt <= t < closedTime`. Stratification uses status, `fee_category` and creation month only. `status`
  (closed versus active at fetch time) is a design mix, not a creation-time attribute.

## Point-in-time rules applied

* Price features use series points with stamp + 600 s < t; trade features use trades with venue timestamp < t.
  Targets use the last point usable before t + H (no interpolation, no imputation, no extrapolation).
* No Gamma end-of-life metadata (liquidity, volume, tags, end date) is used as a feature; those columns, and
  all book-based columns, are NaN. Only market age from `createdAt` is used.
* Wallet "new to sample" uses a causal first-seen index built inside the history data (earliest trade over all
  fetched markets). It is left-censored at the sample start and by truncation, so it is NaN during a 14-day
  burn-in. Cluster key is the Gamma event id (an identifier, not a feature); neg-risk and parent ids were not
  captured in the frame, so the `dependence_group` cluster equals the event cluster here.
* **Placeholder-price rule (challenger finding).** Every row carries `traded_before_t` (trades strictly before
  t; NaN = unknown because the trade history is truncated before t) and `price_unchanged_since_listing`
  (NaN when the series does not start at listing). The primary analysis **excludes rows with
  `traded_before_t == 0`** (51,554 of 150,000 sampled origins, 34%) and reports them separately; unknown rows
  are kept (211). Untraded rows are very different: mean mid 0.45 vs 0.31, 53% within 0.02 of 0.5 vs 5%, and
  flat share 0.85 vs 0.80 at 2h. `price_unchanged_since_listing` is rarely true (1,714 rows, mostly because
  the series begins at the first trade) and is only reported.

## Design of the run

* Subsample: seeded 623 of the 1,759 panel markets (150,000 origins; 98,446 after the untraded exclusion,
  461 markets). Folds: expanding window, test block 240 periods (10 days), at least 480 periods of training,
  embargo = k x 2h, label-availability purge via `ml_panel.fold_masks`; 18 folds.
* Horizons: k = 1, 3, 12 grid steps (2h, 6h, 24h). Targets: direction (3-class, flat if |dmid| <= 0.005) and
  |move| (binary). Arms: M0 (price and momentum, 8 features), M1 (elastic net with splines), M2 (LightGBM,
  nested tuning on an inner validation split, 6 of the 20 declared configurations), and M1F/M2F that add the
  flow and wallet families. The "market_state_extra" family is everything in the tier-(a) set beyond M0 that
  exists historically (own volatility, previous 2h change, number of prior points, market age, flags).
* Flow: signed flow, buy share, log notional (2h and 24h), burst (2h count against the trailing 24h average),
  largest 2h trade relative to the trailing mean trade size (book depth is unavailable), last-trade age and
  last-trade-minus-mid. Wallet: distinct wallets (2h/24h), concentration (HHI, top-1 share), new-to-sample
  wallets (counts and share).
* Incremental value: `ml_explain.ablation_study` (drop-one and add-one refit, fixed LightGBM, out-of-fold
  log loss, conservative cluster bootstrap CI, Benjamini-Yekutieli over this run plus 114 prior logged
  tests). Positive delta = the family helps.
* Revisions (governance budget, each logged separately): `r0_no_external` (arms, scores, ablation with 500
  bootstrap draws) and `r0b_ablation_nboot10000` (ablation only, 10,000 draws). With 117 cumulative tests the
  smallest p that BY (q = 0.10) can pass is about 1.6e-4, so 500 draws could not label anything
  "demonstrated"; this is why r0b exists. Nothing else changed between them.

## Results

### Do the arms beat M0 out of sample?

Relative log-loss improvement over M0 (1 - loss/loss_M0), pooled out-of-fold, cluster-bootstrap 95% CI
(event cluster; the dependence-group CI is identical). Test rows: about 96,000 per horizon.

Direction (3-class):

| h | M0 loss | M1 | M2 | M1F | M2F |
|---|---|---|---|---|---|
| 2h | 0.619 | 15.3% [12.4, 18.4] | 24.1% [20.8, 27.8] | 15.8% [12.9, 18.9] | 25.9% [22.5, 29.7] |
| 6h | 0.778 | 12.5% [9.5, 16.3] | 20.3% [16.7, 24.7] | 13.4% [10.3, 17.1] | 21.4% [17.8, 25.8] |
| 24h | 0.966 | 9.0% [5.3, 13.1] | 15.5% [10.9, 20.6] | 10.3% [6.1, 15.1] | 16.4% [11.7, 21.5] |

|move| (binary):

| h | M0 loss | M1 | M2 | M1F | M2F |
|---|---|---|---|---|---|
| 2h | 0.489 | 20.1% [16.5, 24.2] | 30.7% [26.4, 35.6] | 19.8% [15.9, 24.0] | 31.9% [27.6, 36.7] |
| 6h | 0.587 | 16.6% [12.3, 21.6] | 27.0% [22.3, 32.8] | 17.7% [13.2, 22.8] | 27.7% [23.0, 33.3] |
| 24h | 0.679 | 14.3% [10.2, 18.1] | 22.8% [17.3, 28.4] | 16.4% [11.6, 21.5] | 23.7% [18.3, 29.4] |

Yes, models beat M0 at every horizon and for both targets. **This must not be read as directional skill.**
M0 has no volatility feature. The lift comes almost entirely from "will it move at all" (flat versus not flat):
the |move| arms gain about as much as the 3-class arms, and the family ablation attributes the lift to
`market_state_extra` (own volatility and recent-move features). Whether the direction of a move is predictable
was not tested here (see next steps).

### Which families add incremental value (ablation, 10,000 draws, r0b)

Delta log loss (drop-one minus full), positive = family helps; conservative 95% CI; label from
`finalize_demonstration` (CI above 0 and BY pass and later-blocks rule):

| target, h | market_state_extra | flow | wallet |
|---|---|---|---|
| direction 2h | 0.0215 [0.016, 0.027] demonstrated | 0.0089 [0.007, 0.011] demonstrated | 0.0004 [-0.001, 0.001] descriptive_only |
| direction 6h | 0.0233 [0.016, 0.032] demonstrated | 0.0085 [0.005, 0.013] demonstrated | 0.0008 [-0.001, 0.003] descriptive_only |
| direction 24h | 0.0163 [0.003, 0.033] descriptive_only | 0.0066 [-0.001, 0.014] descriptive_only | 0.0015 [-0.001, 0.004] descriptive_only |
| \|move\| 2h | 0.0174 [0.013, 0.022] demonstrated | 0.0028 [0.001, 0.004] demonstrated | 0.0003 [-0.001, 0.001] descriptive_only |
| \|move\| 6h | 0.0235 [0.016, 0.033] demonstrated | 0.0051 [0.002, 0.008] descriptive_only | 0.0007 [-0.001, 0.003] descriptive_only |
| \|move\| 24h | 0.0110 [0.004, 0.019] descriptive_only | -0.0053 [-0.016, 0.002] descriptive_only | -0.0027 [-0.009, 0.002] descriptive_only |

* `demonstrated_incremental_value` (in this exploratory, in-sample-of-the-history sense, not a confirmation):
  market-state extras at 2h and 6h for both targets, and flow at 2h and 6h for direction and 2h for |move|.
* Flow adds a modest amount on top of M2 (point estimate: M2F beats M2 by about 2.4% of its log loss for
  direction 2h, 1.4% at 6h, 1.1% at 24h; 1.7%, 0.9%, 1.2% for |move|). It is a volume/activity signal, not
  evidence about direction or informed trading.
* The wallet family (concentration, distinct wallets, new-to-sample wallets) shows no demonstrated value at
  any horizon.
* At 24h nothing is demonstrated: fewer labelled rows per fold and wider CIs.
* The r0 revision (500 draws) labelled everything `descriptive_only` because of p-value resolution; the
  point estimates and CIs are the same as r0b to three decimals.

### Placebos

* **Shuffled labels** (labels permuted within period, ablation at all horizons and targets): every family has a
  CI that includes 0 or is negative (largest positive delta 0.0021, flat at 6h |move|, CI [-0.0000, 0.0045]);
  nothing is labelled demonstrated. At 24h the shuffled flow delta is significantly negative (-0.004), i.e.
  overfitting noise costs log loss.
* **Shuffled labels, arms** (direction 2h, M2F against M0): relative improvement **+0.27% [0.13, 0.45]**. This
  is a small placebo excess whose CI excludes 0. A within-period shuffle keeps each period's class mix, so a
  model that learns period-level regimes retains a sliver of the class-rate signal. It is about one hundredth
  of the real 25.9% lift, but it means arm-level CIs should not be read to the last decimal.
* **Leak positive control** (a feature equal to the realised move plus N(0, 0.02) noise): detected and labelled
  `demonstrated` at all six target/horizon cells (delta 0.035 to 0.243), so the ablation machinery can find
  signal when it exists.

## Revision r1 (M0v baseline, placebo diagnosis, conditional direction), r2 (wallet age), r3 (flow drill)

Changes versus r0/r0b (all logged in `trials.jsonl` with `revision`): the panel gained realised-volatility
windows (`ml_rv_2h/6h/1d/7d`), distance from 0/1 and the scheduled time to end (`endDate` as listed now; it may
have been revised after t, flagged), and the reference baseline is now **M0v**: M0 features + `ml_own_vol` +
the four realised-vol windows + time to end + distance from 0/1 + trading activity (24h trade count and log
notional). "Demonstrated" now means ΔLL against M0v (LightGBM on both sides); the flow family excludes the two
activity columns that live in M0v. Arms: M0, M0v (logistic), M2v (LightGBM on the M0v features, the like-for-like
reference), M1, M2 (all tier-(a) historical features), M2F (M2 + flow + wallet). Same folds, subset (461 markets,
98k origins after the untraded exclusion), seeds and 6-configuration search as r0.

**Volatility was the discovery.** Against M0v the "market_state_extra" family collapses (direction 2h ΔLL 0.0023,
descriptive only) and M2 is no better than M2v (-0.17% [-0.39, 0.04]). Learning from the M0v features with a
GBM already gives 14.7% over the logistic M0v at 2h (direction), which is a learner effect, not a feature family.

**Same-learner result (M2F against M2v, relative log-loss gain, 95% CI, event cluster):**

| target | 2h | 6h | 24h |
|---|---|---|---|
| direction (3-class) | 2.07% [1.72, 2.43] | 0.98% [0.64, 1.29] | 0.15% [-0.15, 0.44] |
| \|move\| | 1.16% [0.79, 1.49] (gated) | 0.58% [0.17, 1.17] | -0.47% [-1.15, 0.03] |
| up vs down given a move | 4.00% [3.22, 4.73] | 2.65% [2.19, 3.07] | 0.66% [0.12, 1.20] |

Labels against M0v (ablation, 10,000 draws, BY with 117 prior tests plus this run): flow is `demonstrated` for
direction 2h, up-vs-down 2h and 6h, and market-state extras for up-vs-down 2h. Wallet: none. Everything at 24h
and everything else: `descriptive_only`. \|move\| 2h flow (ΔLL 0.0035 [0.0023, 0.0047]) would have been
demonstrated but is blocked by the placebo gate (below).

### Shuffled-label placebo: cause and handling

The r0 placebo (M2F +0.27% over M0, CI excluding 0) was a **learner asymmetry, not a label or leakage defect**.
`ml_models` M0/M0v is a nearly unpenalised logistic regression (C = 1e4). On pure noise it overfits and loses
about 0.2% log loss to a model that stays near the base rate. The early-stopped, temperature-scaled GBM does
exactly that. Evidence (global shuffle, direction 2h): M2v over M0v +0.21% [0.10, 0.36] and M2F over M0v +0.21%,
but **M2F over M2v 0.00% [-0.01, 0.01]**. Same pattern at every horizon and target. Conclusion: family claims
must be measured with the same learner on both sides (M2F vs M2v; the ablation already is), and arm-versus-M0
numbers carry a learner effect.

Shuffle designs (k = 1; other horizons: global only):
* **Global shuffle** (the null: only the label marginal survives): ablation shows no family above 0.0005;
  same-learner arms clean for 8 of 9 cells.
* **Within-period shuffle** (keeps each period's class mix): M2F over M2v +0.16% [0.03, 0.29] (direction),
  +0.25% [0.13, 0.36] (|move|). **Within-market shuffle** (keeps each market's class mix): +0.51% and +0.34%
  (the latter not significant). The model can learn time-varying and market-level flat shares from activity
  features, so these designs are not null designs. They explain the original gain and are reported as diagnostics,
  not gated.
* **Gate rule**: a cell is gated if, on the global shuffle, any same-learner arm beats its baseline with a CI above
  0 or any family is labelled `demonstrated`. A gated cell cannot carry a `demonstrated` label. One cell fails:
  **|move| 2h** (M2F over M2v +0.01% [0.00, 0.03], a lower bound that rounds to zero; the real gain is 1.16%).
  The strict rule is applied, so flow at |move| 2h is `descriptive_only (placebo_gate)` in r1 and r2.
* **Leak positive control**: detected (`demonstrated`) in all nine cells (ΔLL 0.033 to 0.396).

### Conditional direction (up vs down given |dmid| > 0.005; fitted on moved rows only)

Moved rows: 19.8k (2h, 13 folds), 28.4k (6h, 14), 41.9k (24h, 16); about half are up. Loss of the best arm is
0.626 (M2F, 2h) against 0.693 for a coin. Flow is `demonstrated` at 2h (ΔLL 0.0223 [0.0166, 0.0288]) and 6h
(0.0119 [0.0071, 0.0166]) and market-state extras at 2h (0.0074 [0.0035, 0.0112]); nothing at 24h. Placebos
(global shuffle) are clean and the leak control is detected. So **direction skill separate from volatility
skill exists in this historical sample at 2-6h, carried by trade flow**.

**Staleness caution (r3 drill, flow split by mechanism).** At 2h the biggest piece is "last trade versus the
price series" (`ml_tf_ltp_minus_mid`, `ml_tf_last_age_h`): direction ΔLL 0.0040, |move| 0.0028 (the only
demonstrated piece), up-vs-down 0.0078. Signed flow and buy share are also demonstrated at 2h (0.0020 direction,
0.0049 up-vs-down) and at 6h for direction (0.0036); intensity is not. Because the prices-history value is
mid-like and possibly lagged relative to trades, a last-trade-minus-price feature can be a price-series
lag (the series catches up to the last trade), not information about the market. This data cannot separate
the two. Read the flow result as "trade flow tells you where the lagged series is heading", and treat it as a
hypothesis for the prospective data, where book mid and trades have receipt times.

### Wallet age (r2; `nw_*` table from `history_sources.new_wallet_features`, 149,770 of 150,000 rows covered)

`wallet_age` against M0v: no `demonstrated` label anywhere. Direction 2h ΔLL -0.0007 [-0.0014, -0.0001];
up-vs-down 2h -0.0001; |move| 24h +0.0071 [0.0018, 0.0140] but labelled `descriptive_only` (BY) and M2FX is only
+0.06% over M2v. Adding the table to M2F changes nothing material (e.g. direction 2h
2.07% to 2.08% over M2v).

## Replication on a new data window: `h3_power` (revision `h3_replication`)

**Pre-declared** (trial line `history_replication_declaration`, 2026-10-12T23:37:50Z, committed and pushed before
any result): independent replication of r1/r2 on `h3_power`, 10,000 markets disjoint from `h1_first` and
`h2_main` (seed `arepo-h3-power`, topic-oversampled 3x for asymmetric topics, `sample_weight` = inverse
inclusion probability). Panel: 582,587 origins, 5,112 markets; run on a seeded 2,138-market subset (250,000
origins; 93,508 after the untraded exclusion, 1,324 markets; 20 folds). Same design as r1/r2 (M0v, M2v, M2F, M2FX
with the `nw_*` table, nine cells, global/period/market placebos with the global gate, leak control). Declared
criterion for a flow replication: flow ΔLL against M0v with a conservative CI lower bound above 0, **and** M2F over
M2v relative gain with CI lower bound above 0, **and** the cell passes the global-shuffle gate. Cells declared:
direction and up-vs-down at 2h and 6h. Wallet age "helps" only if ΔLL CI lower bound is above 0 and the BY label
is `demonstrated`. The tests are added to the cumulative `ml_explain` count (154 lines in `trials.jsonl`); a new
window is a new replication family, but the conservative cumulative BY denominator was kept. Weights enter the
evaluation only (weighted out-of-fold comparison, weighted cluster bootstrap), not the fit.

**BY labels are not usable here.** With a cumulative denominator above 150 the smallest passable p is below the
10,000-draw bootstrap floor (1e-4), and the denominator grows as the run logs, so labels differ across cells for
a bookkeeping reason (even the leak control is `descriptive_only` after the first cells). The declared CI
criterion above is therefore the replication test; `label` fields in the JSON should not be compared across cells.

| cell | flow ΔLL vs M0v [CI] | M2F over M2v [CI] | weighted M2F over M2v | placebo gate | declared criterion |
|---|---|---|---|---|---|
| direction 2h | 0.0081 [0.0057, 0.0105] | 1.67% [1.40, 1.94] | 1.70% [1.36, 2.05] | pass | **replicates** (h2: 0.0082, 2.07%) |
| up-vs-down 2h | 0.0121 [0.0067, 0.0172] | 3.22% [2.67, 3.74] | 3.26% [2.54, 3.96] | **fail** | not met (gated) |
| direction 6h | 0.0023 [-0.0018, 0.0059] | 0.99% [0.76, 1.18] | 1.00% [0.73, 1.23] | pass | not met (ablation CI includes 0) |
| up-vs-down 6h | 0.0107 [0.0047, 0.0161] | 2.53% [2.00, 3.02] | 2.25% [1.75, 2.73] | pass | **replicates** (h2: 0.0119, 2.65%) |

So **2 of 4 declared cells replicate**. The 2h up-vs-down gate failed on a tiny excess: M2F over M2v on shuffled
labels is +0.05% [0.005%, 0.107%] against a real +3.22%, but the strict rule applies, so no `demonstrated`
claim is made for that cell (the effect size and sign replicate; the gate is what blocks it). Direction 6h: the
arm gain over M2v holds (0.99%) but the family ablation does not clear zero. |move| 2h: flow ΔLL 0.0025
[0.0008, 0.0041], M2F over M2v 1.07% [0.80, 1.36], gate pass (it failed in h2). |move| 6h and all 24h cells:
no flow effect (|move| 24h M2F -0.13%). Up-vs-down at 24h shows M2F over M2v +1.46% [0.99, 1.98] with flow ΔLL
0.0103 [0.0020, 0.0183], which h2 only weakly showed (0.66%); undeclared, so exploratory only.

Placebo diagnostics: the same-learner global shuffle is clean in 8 of 9 cells; the period shuffle gives M2F
over M2v +0.05% [0.001, 0.10]% and the market shuffle +0.15% [-0.02, 0.32]% at direction 2h (h2: 0.16% and
0.51%), consistent with the block-level base-rate explanation. The leak control is detected (CI above 0) in all
nine cells.

**Weighted results** agree with unweighted ones: weighted M2F over M2v is within 0.3 percentage points of the
unweighted value in every declared cell; effective sample size is 64k (direction/|move|, 2h), 17k to 24k
(up-vs-down 2h/6h) against 93k and 26k to 36k rows. The topic oversampling therefore does not drive the result.

**Wallet age with better coverage** (247,739 of 250,000 rows covered, 99%): still no `demonstrated` help.
ΔLL against M0v: direction 2h -0.0009 [-0.0018, -0.0001], up-vs-down 2h -0.0007, 6h up-vs-down +0.0029
[0.0003, 0.0054] (BY not met), 24h direction +0.0019 [-0.0016, 0.0056]. In the arm view M2FX versus M2F adds
nothing at 2h or 6h and a small amount at 24h (direction 0.54% [0.23, 0.83] over M2v against 0.28% for M2F;
|move| and up-vs-down unchanged). By the declared criterion it does not help; the 24h direction hint is
undeclared and small, to be re-examined only in a prospective sample.

## Revision r5_regime_ix (SB2-J7, q0012, 2026-10-16): regime contrasts and pairwise interactions on `h2_main`

Design: `SCREENING_BATCH_2.md` J7 (frozen at 6ad5dff, regime declaration hash `c5c143c6974d226a`). Three cells chosen
from h2 r1 only (direction 2h, up-vs-down 2h, up-vs-down 6h); discovery = first half of the test blocks, judgement =
later half; 27 counted `ml_explain` tests (prior cumulative count 952). Results file
`history/h2_main/ml_history_results_r5_regime_ix.json` (host). Runtime 87 min. Global placebo gate passed in all three
cells; leak positive control detected.

Contrast = (mean per-row LL gain of the full model over M0v in regime A) − (same in regime B), judgement rows,
cluster bootstrap over event and `dep_group` (conservative of the two). Stage-1 advance: two-sided p < 0.01 and the
same sign on discovery blocks.

| cell | C-LIQ (high − low liquidity) | C-TTE (<24h − >30d) | C-ACT (active − inactive 2h) | C-EXT (extreme − middle price) |
|---|---|---|---|---|
| direction 2h (98k rows) | not informative (0 low rows) | **+0.012 [0.004, 0.047], advances** | **+0.059 [0.045, 0.074], advances** | −0.007 [−0.011, −0.003], p 0.0006, discovery sign +0.004, does not advance |
| up-vs-down 2h (20k) | not informative | +0.007 [−0.028, 0.040] | **+0.063 [0.044, 0.083], advances** | +0.009 [−0.008, 0.026] |
| up-vs-down 6h (28k) | not informative | −0.013 [−0.035, 0.009] | **+0.043 [0.030, 0.057], advances** | +0.002 [−0.007, 0.011] |

Interactions: no pair advances in any cell (0 of 15). The Friedman H² leaders are degenerate pairs of
missing-history indicators (`ml_chg_1h/1d/1w_missing`, H² = 1 on folds where they co-vary perfectly), whose
constrained-versus-free validation gain is exactly 0; the price pairs (`logit_mid × dist_01`, `logit_mid × rv_1d`,
`own_vol × rv_7d`, `tf_n_2h × tf_last_age_h`) do not validate either.

Reading:
- **C-ACT is close to mechanical.** The full model's extra families (flow, state, wallet) are mostly zero or missing
  when no trade printed in the last 2h, so the gain over M0v has to sit in active rows. It says where the
  flow value is (about 0.06 nats per active row against 0.005-0.014 per inactive row), not that activity creates a new
  conditional signal. It goes to J8 as declared, with this caveat attached.
- **C-TTE (direction 2h only):** the gain is larger in the last 24h before the end date. Robust to the end-date
  look-ahead sensitivity (dropping 1,550 rows from markets closed > 24h early: +0.0118 [0.005, 0.047], no sign flip).
- **C-LIQ is untestable as declared (defect, disclosed).** The tercile cut for `ml_tf_log_notional_24h` is computed
  on discovery rows, where more than a third of rows have zero 24h notional, so the lower cut is 0.0 and, with
  `<` assignment, the "low" regime is empty in every cell. The three C-LIQ tests stay counted as run and are
  recorded as `not informative`. Changing the cut after seeing this would be a post-hoc redefinition. J8 applies the
  same frozen cuts and will also be uninformative for C-LIQ. Any future liquidity contrast needs a new declaration
  (for example, zero-notional as its own level), on data not yet read by ML.
- **Q6 (historical, h2 stage 1):** no pairwise interaction adds out-of-sample value beyond what M2F already uses.
  J8 (q0013) now replicates the 4 advanced contrasts (C-TTE direction; C-ACT × 3) on h3 markets never read by ML,
  Holm at 0.05.

## Caveats

* Historical and exploratory. Panels are reconstructed after the fact from prices-history, not point-in-time
  snapshots; the series semantics (last trade versus mid, interval convention) are unverified, hence the
  600-second lag.
* Survivorship and selection: the frame is a time-window sample with a page cap (lowest ids), under-represents
  markets living under a day, drops untraded rows, and covers one regime. Closed markets are 87% of the sample.
  Results say nothing about the full universe.
* No book features. Liquidity, spread and depth columns are NaN, so M1/M2 here are weaker than their
  prospective counterparts; "large trade relative to recent volume" replaces depth.
* Flow/wallet limitations: trade truncation (41 markets), first-seen index censoring, and the fact that
  prices in markets with sparse trading are stale by construction.
* 623 of 1,759 panel markets were used (150,000-row cap); the hyperparameter search used 6 configurations.
* Multiple testing: 117 cumulative tests in the BY denominator (r1 onward); every revision adds more.
* The M0/M0v logistic is nearly unpenalised; arm-versus-M0 gains include a learner effect (see the placebo
  diagnosis). Use M2F-versus-M2v for family claims.
* No directional claim: the 3-class lift is mostly flat-versus-move. No economic check (fees, spread,
  executability) was done.

## Pending revisions and next steps

1. `book` family: `--book-table` (analysis restricted to pmxt-window origins; judged on rows with a book).
   `wallet_age` is done (r2). The `h2_main` book table is still being built (the `h1_first` table has 11.6%
   coverage); run `--revision r4_book` when it lands.
2. Done: conditional direction with the M0v baseline (r1).
3. Capture neg-risk and parent event ids in the frame so the second cluster is distinct from the event.
4. Scale to all 1,759 panel markets once the per-fold cost is acceptable.

## Reproduce

```bash
cd backend && source .venv/bin/activate
python scripts/backfill_history.py run --run-id h2_main --n-markets 3200 --seed arepo-h2
python scripts/backfill_history.py panel --run-id h2_main
python scripts/run_ml_history.py --run-id h2_main --max-rows 150000 --revision r0_no_external
python scripts/run_ml_history.py --run-id h2_main --max-rows 150000 --skip-arms --placebo-all \
    --n-boot-ablation 10000 --revision r0b_ablation_nboot10000
python scripts/run_ml_history.py --run-id h2_main --max-rows 150000 --n-boot-ablation 10000 \
    --revision r1_m0v_placebo_updown   # M0v baseline, gated placebos, updown target
python scripts/run_ml_history.py --run-id h2_main --max-rows 150000 --n-boot-ablation 10000 \
    --revision r2_wallet_age --wallet-age-table ../data-dumps/research_lab/history_sources/new_wallets/new_wallet_features_h2_main.csv.gz
python scripts/run_ml_history.py --run-id h3_power --max-rows 250000 --n-boot-ablation 10000 \
    --revision h3_replication --wallet-age-table ../data-dumps/research_lab/history_sources/new_wallets/new_wallet_features_h3_power.csv.gz
python scripts/run_ml_history.py --run-id h2_main --max-rows 150000 --skip-arms --drill-flow \
    --n-boot-ablation 10000 --horizons 1,3 --revision r3_flow_drill
```
