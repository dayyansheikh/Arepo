# Resolution-forecasting development study (target T5)

**Status:** DEVELOPMENT, retrospective, `evidence_role: exploratory_historical`. This is not prospective evidence. It
makes no claim about calibration, edge, tradability or profitability. Run `resdev-t5-20261011b`, analysed
2026-10-11 23:12Z. Code: `backend/astrolabe/research_lab/resolution_dev.py` and `backend/scripts/run_resolution_dev.py`
(tests in `backend/tests/unit/test_research_lab_resolution_dev.py`). Outputs (gitignored):
`data-dumps/research_lab/resolution_dev/resdev-t5-20261011b/` (`sample_plan.json.gz`, `frame/`, `raw/`,
`rows.parquet`, `results.json`). Trial lines: `kind: history_resolution_dev` and `kind: ml_explain` (114 tests).

## Question

At 1, 3 and 7 days before the scheduled close, does a model using point-in-time market features predict the eventual
binary resolution better than (a) the market price used as a probability, and (b) a recalibrated price (Platt or
isotonic, fitted on earlier markets only)? The recalibrated price is the real bar. The economic reading is
hold-to-resolution, not price movement.

## Design (fixed in code before any outcome was analysed)

- **Universe and enumeration:** binary Gamma markets with `closed=true` and lifetime `volumeNum >= 100`, scheduled
  `endDate` in [2025-10-11, 2026-10-04). The window is cut into 1,432 six-hour `endDate` blocks across 4 periods. A
  seeded draw takes 12 blocks per period (48 in total), and every market in a drawn block is enumerated through
  `/markets/keyset`. The frame holds 49,684 markets.
  - Frame filter, using an ex-ante field: listed at least 30h before the scheduled end. 24,432 markets pass. By
    category: sports 17,651, science/weather 3,004, crypto 2,383, economy 604, politics 314, culture 297, tech 112,
    other 38, geopolitics 29.
  - Stage 2 is a seeded stratified draw by period x coarse category (C1's tag rules), capped at 600 per cell. It
    reads frame fields only, and pi and 1/pi are recorded. Sample: 7,489 markets.
  - Survivorship: every resolved market in a drawn block is eligible. Markets still unresolved or disputed on
    2026-10-11 are not in a `closed=true` listing (right-censoring, as in C1).
- **Horizon anchor:** `t_h = endDate - h`. Unlike C1, the anchor is the *scheduled* end, never `closedTime`. Early
  closure correlates with the outcome (a "by date" market closes early on Yes), so a `closedTime` anchor or a
  time-to-close feature would leak. A row exists only if the market was listed and still open at `t_h`, which is
  observable at `t_h`.
- **Point in time:**
  - CLOB `prices-history` at 10-minute fidelity over [end-14d, end-1d]. A point stamped `s` is used at `t` only if
    `s + 600 s < t`, because the stamp convention is undocumented (same lag as `history_backfill`). The price must be
    at most 6h old.
  - Data API trades: one or two pages of 10,000, kept only if `ts < t`. Trades after end-1d are discarded before
    storage, and no wallets are stored.
  - Lifetime volume, liquidity, `closedTime` and outcome fields are never features.
- **Features:**
  - Price path: `logit_p` (baseline), distance from 0/1, changes over 1h, 6h, 24h and 72h, logit change over 24h,
    volatility over 24h and 72h, 24h range, 7d max and min, count of price moves, staleness.
  - Metadata: listing age, scheduled lifetime, midnight-end flag, neg-risk and augmented flags, Yes/No flag, category
    dummies.
  - Trade history: count and log notional over 24h, 7d and cumulative; 24h buy share; time since the last trade;
    last trade price minus price.
  - Book and liquidity history does not exist historically, so it is absent. Time to the scheduled end equals the
    horizon, so it is constant within a horizon model.
- **Label:** `calibration.parse_outcome`. 7,464 markets resolved cleanly. 25 split 50-50 are excluded; none were
  disputed or other.
- **Trade coverage:** 5 markets reached the 20,000-trade limit. The primary population needs every trade window
  covered, which excludes 1 row per horizon. A sensitivity analysis runs all rows without trade features.
- **Evaluation:** separately per horizon.
  - Walk-forward by scheduled end: 8 contiguous chunks; chunks 3-8 are tested on an expanding training window. A
    training row is used only if its label time (max(end, closed)) plus a 2-day embargo precedes the first test
    origin.
  - Tuning uses an inner split (the last 25% of training rows by end, with its own embargo).
  - Arms:
    - `price`: raw price.
    - `platt`: logistic on logit(p).
    - `isotonic`.
    - `enet`: elastic-net logistic over a 12-point C x l1_ratio grid, with median imputation, missing flags and
      standardisation.
    - `lgbm`: LightGBM boosted from an init score of logit(p), 12 seeded configs, early stopping on the inner split,
      then refit with that round count.
  - All predictions are clipped to [0.001, 0.999].
  - Primary is unweighted. Weighted (1/pi) and mid-range (0.05 <= p <= 0.95) views are sensitivities.
  - CIs: 1,000-resample cluster bootstrap. The reported CI is the **conservative hull** over the event, dep_group
    (negRiskMarketID, else event) and parent (parentEvent / seriesSlug, else dep_group) clusterings.
- **Hierarchical model (`ml_models.BayesHier`):** not run. It is hard-wired to the 3-class direction target and the
  `ml_panel` feature set, and adapting it would mean editing `ml_models.py`, which was out of scope.
- **Interpretability:** `ml_explain.ablation_study` (imported, unchanged), which uses a fixed-config LightGBM
  without a price prior.
  - Baseline is `logit_p`. Units are the three declared families plus every single feature, declared a priori.
  - Value is drop-one ΔLL out of fold. CIs are the hull over the event and dep_group clusterings. BY q=0.10 is
    applied cumulatively over 38 / 76 / 114 tests; no ml_explain tests had been logged before.

## Data actually scored (out-of-fold, chunks 3-8)

| Horizon | Rows with a price (markets) | Scored rows | Events (scored) | Base rate | Not listed at t_h | Closed before t_h |
|---|---|---|---|---|---|---|
| 1d | 6,641 | 4,980 | 2,233 | 0.287 | 0 (frame filter) | 586 |
| 3d | 3,268 | 2,449 | 862 | 0.275 | 3,405 | 554 |
| 7d | 1,698 | 1,272 | 869 | 0.366 | 5,523 | 237 closed before every horizon (not fetched) |

There is one row per market per horizon. **The 3d and 7d sets are conditional on a market already being listed that
early**, so they are mostly sports (7d: 1,036 of 1,272 scored rows). The three horizons are not the same markets.
Requests: about 11,600 plus enumeration. No 403s, 1 transient error. About 50 MB on disk. Collection ran at
3 req/s or less, paused during :25-:59 after even UTC hours, and yielded to the live `arepo_pass.sh`.

## Results (log loss, unweighted primary; improvement = baseline loss minus arm loss, positive = arm better)

| Horizon | price | Platt | isotonic | enet | LightGBM |
|---|---|---|---|---|---|
| 1d | 0.3735 | 0.3734 | 0.3761 | 0.3811 | 0.3747 |
| 3d | 0.3772 | 0.3763 | 0.3887 | 0.3958 | 0.3767 |
| 7d | 0.5641 | 0.5572 | 0.5597 | 0.5577 | 0.5531 |

| Horizon | Platt vs price | LightGBM vs price | **LightGBM vs Platt** | enet vs Platt | LightGBM vs isotonic | Folds LightGBM > Platt |
|---|---|---|---|---|---|---|
| 1d | +0.0001 [-0.0020, +0.0022] | -0.0011 [-0.0040, +0.0016] | **-0.0013 [-0.0039, +0.0014]** | -0.0077 [-0.0118, -0.0034] | +0.0015 [-0.0017, +0.0052] | 2/6 |
| 3d | +0.0009 [-0.0011, +0.0027] | +0.0004 [-0.0067, +0.0065] | **-0.0004 [-0.0080, +0.0059]** | -0.0195 [-0.0377, -0.0031] | +0.0120 [-0.0002, +0.0266] | 3/6 |
| 7d | **+0.0069 [+0.0022, +0.0113]** | +0.0111 [+0.0040, +0.0181] | **+0.0041 [-0.0022, +0.0106]** | -0.0005 [-0.0113, +0.0101] | +0.0066 [-0.0024, +0.0175] | 4/6 |

Brier gives the same picture. At 7d, Platt vs price is +0.0034 [+0.0012, +0.0054] and LightGBM vs Platt is
+0.0018 [-0.0012, +0.0047].

- **Sensitivities:**
  - All rows without trade features: at 7d, LightGBM vs Platt reverses to -0.0031 [-0.0105, +0.0049]. The point
    estimate of the 7d model gain is not robust to dropping the trade family.
  - Weighted (1/pi): 7d LightGBM vs Platt is +0.0047 [-0.0039, +0.0133]. At 1d, raw price beats Platt (-0.0049
    [-0.0094, -0.0005]), so recalibration fitted on earlier markets *hurts* there.
  - Mid-range only: same conclusions.
- **Calibration of raw price (intercept, slope):** 1d (0.00, 1.15); 3d (-0.29, 1.02); 7d (-0.33, 1.12). The 7d
  outcome-0 overpricing seen in C1 reappears with the *scheduled-end* anchor, so it is not explained by C1's
  outcome-dependent `closedTime` anchor. It is still mostly sports and still a backfilled price of unknown type
  (mid or last trade).
- **By category (descriptive, many cells, no multiplicity control):**
  - LightGBM vs Platt has a CI above 0 only for 1d politics (+0.023, 189 rows, 33 events) and 3d crypto (+0.016,
    657 rows, 73 events).
  - It has a CI below 0 for 1d crypto (-0.006) and 3d politics (-0.007).
  - The signs alternate, which reads as noise.
- **Hold to resolution (gross, non-executable, descriptive only):** this buys the side that LightGBM favours over
  the backfill price by more than 0.05, at that price, with no spread, fees or depth. Buying outcome 1 (against
  outcome 0) returns:
  - 7d: +0.153 per share [+0.105, +0.205], 338 rows, 284 events.
  - 3d: +0.142 [+0.073, +0.209], 180 rows.
  - 1d: +0.038 [-0.015, +0.086].

  This is the same outcome-0 overpricing seen through the model. It is not a profitability estimate: the backfill
  price is not an executable ask.
- **Incremental features (ml_explain, drop-one ΔLL vs full):**
  - **No unit is demonstrated** at any horizon. Every BY-adjusted p is 1.0, and the full feature model loses to
    `logit_p` alone at 1d (-0.011) and 7d (-0.044).
  - Top descriptive units by ΔLL:
    - 1d: `chg_6h` +0.0048 [+0.0009, +0.0086] is the only CI above 0, and it fails BY.
    - 3d: flow family +0.0097 [-0.0004, +0.0211].
    - 7d: market_state family +0.019 [-0.011, +0.050] and `price_age_h` +0.013.
  - Note: `ml_explain` ranks units with `delta_ll == 0.0` as missing (the `or -1e9` in its sort key), so this report
    ranks by `delta_ll` directly. The bug is in `ml_explain.py` and was not edited here.

## Reading

1. **Nothing beats the recalibrated price.** At every horizon the feature models (elastic-net and LightGBM) are
   within noise of Platt, or worse. Elastic-net is significantly worse at 1d and 3d (overfitting on a few thousand
   rows). The 1d result matches C1: about one day out, the price is close to calibrated and carries the
   information these features hold.
2. **The one robust signal is recalibration at 7d (and weakly 3d).** Raw outcome-0 prices are too high (intercept
   about -0.3). A Platt map fitted on earlier markets improves log loss by +0.0069 [+0.0022, +0.0113]. It needs no
   features beyond the price.
3. The 7d LightGBM gain over Platt (+0.004, 4/6 folds) is not supported. Its CI includes 0, it reverses without
   trade features, and no family passes ablation.

## Does anything merit pre-registration?

- **Feature models for T5: no.** Nothing clears the recalibrated-price bar, and no feature family is demonstrated.
- **The recalibration hypothesis: possibly, as a narrow MC2 candidate.** The hypothesis: "at 7 days (and 3 days)
  before scheduled end, outcome-0 is overpriced; a Platt map frozen on this development data improves log loss over
  raw price on new markets."
  - It needs its own registration with a frozen map.
  - Its prospective origin prices must be the recorded book (mid and ask), not a backfill.
  - It needs the economic check at executable asks with fees.
  - It needs a decision on the sports dominance (category scope is undecided).
  - Before any registration, a challenger should rule out a label-order artefact: outcome 0 is often the favourite
    or home team in sports. Check the Yes/No subset and the favourite-folded view at 7d.
