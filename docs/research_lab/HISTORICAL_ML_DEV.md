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
* Multiple testing: 117 cumulative tests in the BY denominator; this run adds more.
* No directional claim: the 3-class lift is mostly flat-versus-move. No economic check (fees, spread,
  executability) was done.

## Pending revisions and next steps

1. `book` and `wallet_age` families: `run_ml_history.py --book-table .../book_features.csv.gz` (analysis
   restricted to origins inside the pmxt window; ablation judged on rows with a book) and
   `--wallet-age-table` (columns `ml_wage_*`/`ml_wa_*` keyed by `market_id`, `origin_ts`). Each is a separate
   `--revision` (`r1_book`, `r2_wallet_age`). The tables had not landed when this note was written.
2. A conditional direction target (sign of the move given a move) with a volatility-aware baseline, so that
   "beats M0" cannot be explained by volatility.
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
```
