# Hypothesis battery 1 (HB1): pre-declared screen on `h2_main`

`evidence_role: exploratory_historical` | provenance `EXPLORATORY_HISTORICAL` | revision `hb1_battery` |
status: **DECLARED before any outcome was computed** (this section). Results are appended in section 11 after the
single run. Development screen only: no prospective, confirmation, edge, calibration or profitability claim.

## 0. What this is

- One pre-declared battery of **72 hypotheses** on the historical `h2_main` panel, tested once on a single
  discovery/judgement time split. It counts as **one revision** of the `h2_main` window under
  `FEATURE_DISCOVERY_PROGRAMME.md` section 3 (per-window budget of 3; the historical runs r0-r3 already used it, see
  section 10).
- The operational definition is the code: `backend/astrolabe/research_lab/battery.py` (`HYPOTHESES`, `pop_mask`,
  feature builders, tests) and `battery_data.py` (metadata rules), run by `backend/scripts/run_hypothesis_battery.py`.
  Declaration hash (`battery.declaration_sha256()`, hypotheses + split + embargo): see the commit that adds this file
  (value printed in section 8). A later change to any declared definition is a deviation and must be recorded here.
- Survivors are labelled **screen-positive (L1, exploratory_historical)**. Nothing here reaches L2 without the
  placebo and stability checks of the programme ladder, and nothing historical can reach L4.

## 1. Data

- **Panel:** `data-dumps/research_lab/history/h2_main/panel_H{2,6,24}h.csv.gz` (2-hour UTC grid, 420,937 origins,
  1,759 markets; built by `history_backfill.build_panel`). **Primary rows:** `traded_before_t != 0` (programme rule:
  placeholder prices excluded; unknown kept): 278,463 rows, 1,300 markets, 1,049 events. Every market of the panel is
  used (no 150k-row subsample).
- **Targets:** `d_h` = series mid at the last point usable before `t+h` minus mid at `t` (`h` = 2, 6, 24); 3-class
  direction (`delta` = 0.005) and `|move|` from the panel; resolution excess `Y0 - mid` (outcome-0 payout of resolved
  binary markets, sample `outcome_prices`, `uma_status = resolved`). Targets are never imputed.
- **Fetched for this battery (bounded public collection, no outcomes kept):**
  - Gamma `/events?id=` metadata for the sampled events: 2,750 of 2,755 (5 missing). Kept: title, question,
    `groupItemTitle`, slug, tags, neg-risk flags, member list, scheduled dates, outcome-0 token. Sibling
    `outcomePrices` are not stored. File `battery1/events_meta.jsonl.gz`.
  - CLOB `prices-history` (10-minute fidelity, <= 14-day windows) for the **other members** of (a) non-augmented
    neg-risk events with 2-25 members and (b) deadline ladders, whenever the event contains a sampled market with
    traded panel origins, only over that market's traded span plus 8 days of look-back: 3,848 sibling tokens targeted (the fetch, paced at
    4 req/s and yielding to the live collector, completes before the feature build; final counts in section 11).
    Files `battery1/siblings/`.
- **Existing tables:** pmxt v2 book features (`history_sources/book_features`, 6h grid, 2026-04-13 to 2026-08-10
  minus 06-12..06-17, two-sided rows only); new-wallet table (`new_wallet_features_h2_main`, `nw_share_new7d`);
  wallet first-trade map (`first_trade.jsonl`, 9,621 wallets, about 47% of 24h notional covered; wallets without a
  known first trade are treated as not fresh); sample metadata (fee category, neg-risk flag, closedTime,
  `uma_status`, `outcome_prices`).
- **Asymmetry class:** `history_topics.topic_of` (creation-time text: question, event title, slug, fee type), used
  unchanged: `asymmetric` (politics, geopolitics, awards, corporate, macro), `public` (sports, crypto, weather),
  `other`. Sampled markets: 370 / 2,195 / 635; traded rows: 153,252 asymmetric, 61,116 public.

## 2. Clocks (point in time)

- Price-path features: 10-minute points stamped `s` are usable at `t` only if `s + 600 < t` (as the panel).
- **Price-aligned trade windows:** every trade feature built for this battery uses trades with `ts < s_last`, where
  `s_last` is the stamp of the last usable price point. A trade is therefore never newer than the price it is
  compared with, which removes the "series catches up with the last trade" artefact found in r3. Exceptions, inherited
  from existing tables: the M0v activity columns (`ml_tf_n_24h`, `ml_tf_log_notional_24h`) and `nw_share_new7d`
  (unsigned; `[t-24h, t)`).
- A truncated trade history makes a window NaN, never 0.
- Sibling prices use the same as-of rule (`s + 600 < t`, at most 2h old). Neg-risk sums need a usable price for every
  member alive at `t` (`createdAt <= t < closedTime`), else NaN.
- Book features: pmxt events with receipt and venue clocks `<= t`.
- Wallet record: a resolved sample market's outcome counts as known 2 days after its closedTime; a trade's wallet
  record uses only markets known strictly before that trade.
- Known look-ahead risk: `hours to end` uses the scheduled `endDate` as listed at fetch time (may have been revised
  after `t`; inherited from the panel; affects TI3, TI4, IX4 and the M0v column).

## 3. Split

- `SPLIT` = **2026-07-01T00:00:00Z** (epoch 1782864000). Discovery rows: `t + 24h <= SPLIT`. Judgement rows:
  `t >= SPLIT + 24h`. Rows in between are dropped (24h embargo = longest horizon, on both sides).
- Chosen from origin timestamps only (no outcome): about 37% of primary rows fall in discovery, and pmxt book rows
  exist on both sides (3,074 / 3,252 traded two-sided rows).
- **Discovery is used for:** the sign tested (beta and mean tests), feature scaling (1%/99% winsorising, on non-zero
  values when at least half of the values are 0; SD), moderator cuts (median 24h notional; means/SDs of
  `log(rv_1d)` and `log1p(hours to end)`), every LightGBM fit, and the economics threshold of beta survivors.
  **Judgement is used for** every test statistic. Nothing in judgement is tuned.

## 4. Test statistics

- **beta (48 hypotheses):** OLS on judgement rows of `y` on `[1, controls, x]`. `C0` = `ml_logit_mid`,
  `ml_abs_mid_dev`, `chg_1h`, `chg_1d`, `chg_1w` (NaN -> 0), their three missing flags, `dprev` = own 2h change
  `ml_own_dmid_prev` (NaN -> 0) and its missing flag. `C0M` = `C0` without the two price-level terms (used where the
  feature is itself a price level). Tested one-sided **in the sign of the same regression on discovery rows** (theory
  prior if discovery is untestable). Standard errors: CR1 clustered by event (event id, else market) and two-way
  event x UTC day (Cameron-Gelbach-Miller; one-way maximum if not positive). **p = max(p_event, p_twoway)**, from the
  normal z. Effect: slope in price points per discovery SD of `x` (`per SD`) or per unit (`raw`); 2,000-draw
  event-cluster bootstrap CI (partialling held fixed).
- **dll (22):** LightGBM with the fixed `ml_explain.lgb_fit` configuration (learning rate 0.1, 15 leaves,
  `min_data_in_leaf` 20, `lambda_l2` 1, 100 rounds, seed 116) fitted on discovery rows of the population, once on
  `M0v` (the 16 `run_ml_history.M0V` columns) and once on `M0v + x`. `ΔLL_i = loss(M0v) - loss(M0v + x)` on judgement
  rows; mean ΔLL tested one-sided `> 0` with the same clustering rule. Effect: nats per row and relative to the M0v
  loss.
- **mean (2):** mean of the resolution excess in the population, one-sided in the discovery sign, same clustering.
- **Testable** only if judgement has >= 300 rows in >= 30 event clusters; beta tests also need >= 100 rows with
  `x != 0` in >= 20 events; dll tests also need >= 2,000 discovery rows. An untestable hypothesis gets p = 1 and is
  still counted.

## 5. Multiple testing and the decision rule

- **Cumulative count** (`battery.prior_test_count`, declared rule): non-placebo `ml_explain` lines contribute
  `n_tests` or `multiple_testing.m_tests` (T5-DEV 114 + r0-r3 129 = 243); each non-placebo line of `flow_screen`
  (105), `leadlag_screen` (8), `comparison` (7), `detector_eval` (18), `detector_eval_if_h1` (2), `e007_staleness_dev`
  (5), `calibration_study_c1` (1) and `dev_fit` (2) contributes 1. Model fits/scores, placebos and case timelines
  contribute 0. At declaration: **391 prior tests, m_total = 391 + 72 = 463.** The run recomputes the count with the
  same rule (lines appended by other workstreams in the meantime are included) and uses the run-time value.
- **BY at q = 0.10 over m_total.** With m = 463 the smallest passable p is about 3.2e-5 (k-th smallest: about
  k x 3.2e-5). **Survivor = passes cumulative BY.** BY within the battery alone (m = 72) is reported as descriptive.
- The battery's tests are written to `trials.jsonl` (one `history_battery` line per hypothesis, plus one `ml_explain`
  summary line with `n_tests` = 72 so later ml_explain runs count them).

## 6. Checks on survivors (declared)

- **beta survivors:** slope within each fee category and each judgement month (sign agreement reported); including
  untraded rows (sensitivity); only rows with >= 1 trade in the prior 24h; for flow, wallet, interaction and category
  features the trade windows ended **30 minutes earlier** (staleness check); within-period permutation of the
  control-residualised feature (200 draws, Freedman-Lane style).
- **dll survivors:** mean ΔLL within category, month and the trade-in-prior-24h subset (same predictions).
- **Economics** (`economics.py` fee formula, paper only, "optimistic, not tradable"): beta survivors trade
  `sign(s)` with `s = beta_discovery * x` on judgement rows whose `|s|` is at least the discovery 90th percentile;
  3-class dll survivors trade the sign of the incremental `P(up) - P(down)` tilt in its top judgement decile (a
  feature-only threshold). Gross = sign x `d_h` per share (mid to mid). Taker cost = spread (pmxt book at the origin
  when present, else the `EXECUTION_COSTS.md` band median: 4.1c below 0.05, 3.0c to 0.20, 2.2c to 0.80, 3.0c to 0.95,
  2.5c above) plus taker fees on entry and exit at the docs category rate (`fee = rate * p * (1 - p)` per share;
  current fee era applied to all rows, which is conservative for older rows; geopolitics/"unknown" and zero-fee
  categories at 0). Also reported: an optimistic variant paying half the spread and no fee. Volatility (`|move|`)
  and resolution-level survivors have no directional trade rule and get no economic check.
- **Calibration placebo:** the whole battery re-run on globally permuted targets. Expected: no BY survivor and about
  5% of p below 0.05. Not counted in BY.

## 7. Candidate rule (declared)

Up to five survivors are named as candidates for live registration, in this order of preference: (1) sign stable in
at least 2/3 of judgement months and of categories with a testable slope; (2) computable from AREPO's live collection
(snapshots, trade sample, sweeps, wallet sidecar) without new collection, or with a named cheap addition; (3)
economic headroom (net taker mean, then the optimistic variant); (4) effect z. Volatility-only survivors may be named
only as `|move|` (risk / filter) candidates. Mechanically suspect survivors (quote noise, staleness, structural sums)
are flagged and not named first.

## 8. Hypotheses

Declaration hash: `9e0f15ded297e5193ea318a01a257ef3a5801e17f4a44309b91d2b1e45f8d5fe` (72 hypotheses, split 1782864000, embargo 86400 s).

| ID | Family | Test | Target, h | Population | Feature(s) | Controls | Prior | Statement |
|---|---|---|---|---|---|---|---|---|
| MS1 | market_state | dll | \|move\|, 6h | `all` | `f_log_age` | M0v (LightGBM) | ΔLL>0 | log1p(market age h) adds to M0v for \|move\| 6h |
| MS2 | market_state | dll | \|move\|, 6h | `all` | `f_log_last_trade_age` | M0v (LightGBM) | ΔLL>0 | log1p(hours since last trade, price-aligned) adds to M0v for \|move\| 6h |
| MS3 | market_state | dll | \|move\|, 6h | `n24h_7d` | `f_vol_surprise` | M0v (LightGBM) | ΔLL>0 | 24h notional vs own 7-day daily mean (log) adds to M0v for \|move\| 6h |
| MS4 | market_state | beta (per SD) | d, 24h | `n24h_7d` | `f_vol_confirm` | C0 + `f_vol_surprise` | + | sign(1d change) x volume surprise predicts 24h continuation |
| MI1 | microstructure | beta (raw) | d, 2h | `n24h_cov` | `f_rev_illiq` | C0 + `f_illiq` | - | 2h reversal stronger when 24h notional is below the discovery median |
| MI2 | microstructure | beta (raw) | d, 2h | `n24h_cov` | `f_rev_notrade` | C0 + `f_no_trade_2h` | - | 2h reversal stronger when the 2h move had no trade (quote noise) |
| MI3 | microstructure | beta (raw) | d, 2h | `all` | `f_rev_vol` | C0 + `f_z_lrv1d` | - | 2h reversal stronger at high 1d realised volatility |
| MI4 | microstructure | beta (raw) | d, 2h | `all` | `f_rev_extreme` | C0 + `f_extreme` | - | 2h reversal differs within 0.10 of 0/1 |
| MI5 | microstructure | beta (raw) | d, 2h | `all` | `f_rev_tte` | C0 + `f_z_lte` | - | 2h reversal stronger further from scheduled end (E006 H2 analogue) |
| MI6 | microstructure | beta (raw) | d, 2h | `n24h_cov` | `f_rev_confirm` | C0 + `f_confirm` | + | a 2h move confirmed by same-sign 2h taker flow reverses less |
| MI7 | microstructure | dll | \|move\|, 2h | `all` | `f_spread_proxy` | M0v (LightGBM) | ΔLL>0 | median \|trade price - prevailing series price\| over 24h adds to M0v for \|move\| 2h |
| MI8 | microstructure | dll | \|move\|, 6h | `book` | `bk_ml_sw_spread` | M0v (LightGBM) | ΔLL>0 | pmxt book spread adds to M0v for \|move\| 6h |
| MI9 | microstructure | beta (per SD) | d, 6h | `book` | `bk_ml_sw_imb_1c` | C0 | + | 1c depth imbalance (bid - ask) predicts 6h drift |
| MI10 | microstructure | beta (per SD) | d, 6h | `book` | `bk_ml_sw_microprice_disp` | C0 | + | microprice displacement predicts 6h drift |
| FL1 | flow | beta (per SD) | d, 2h | `n1h` | `f_imb_1h` | C0 | + | 1h notional imbalance predicts 2h drift |
| FL2 | flow | beta (per SD) | d, 6h | `n6h` | `f_imb_6h` | C0 | + | 6h notional imbalance predicts 6h drift |
| FL3 | flow | beta (per SD) | d, 24h | `n24h` | `f_imb_24h` | C0 | + | 24h notional imbalance predicts 24h drift |
| FL4 | flow | beta (per SD) | d, 6h | `n6h` | `f_large_flow_6h` | C0 | + | net notional of trades >= $500 over 6h (per mean daily notional) predicts 6h drift |
| FL5 | flow | beta (per SD) | d, 6h | `small6h` | `f_small_imb_6h` | C0 | - | imbalance of trades < $50 over 6h predicts 6h drift (retail: reversal prior) |
| FL6 | flow | beta (per SD) | d, 6h | `n6h` | `f_agg_flow_6h` | C0 | + | net share of trades paying >= 1c through the prevailing price predicts 6h drift |
| FL7 | flow | beta (raw) | d, 6h | `persist` | `f_persist_6h` | C0 | + | three consecutive same-sign 2h flow windows predict 6h drift |
| FL8 | flow | beta (per SD) | d, 24h | `n24h_7d` | `f_flow_surprise` | C0 | + | 24h imbalance minus own 7d imbalance predicts 24h drift |
| FL9 | flow | dll | \|move\|, 6h | `n24h` | `f_burst_2h` | M0v (LightGBM) | ΔLL>0 | 2h trade count vs trailing 24h rate adds to M0v for \|move\| 6h |
| FL10 | flow | beta (per SD) | d, 24h | `n2h` | `f_imb_2h` | C0 | + | 2h notional imbalance predicts 24h drift |
| WA1 | wallet | dll | \|move\|, 24h | `nw` | `nw_share_new7d` | M0v (LightGBM) | ΔLL>0 | 24h volume share of wallets < 7d old (true first trade) adds to M0v for \|move\| 24h |
| WA2 | wallet | beta (per SD) | d, 24h | `fresh` | `f_fresh_flow_24h` | C0 | + | net notional share of fresh (< 7d) wallets over 24h predicts 24h drift |
| WA3 | wallet | beta (per SD) | d, 24h | `fresh_extreme` | `f_fresh_flow_24h` | C0 | + | WA2 restricted to mid <= 0.20 or >= 0.80 (convex acquisition by fresh wallets) |
| WA4 | wallet | beta (per SD) | d, 24h | `top1` | `f_top1_dir` | C0 | + | top wallet's 24h notional share x its net direction predicts 24h drift |
| WA5 | wallet | dll | \|move\|, 24h | `n24h` | `f_hhi_24h` | M0v (LightGBM) | ΔLL>0 | 24h wallet notional HHI adds to M0v for \|move\| 24h |
| WA6 | wallet | beta (per SD) | d, 24h | `win` | `f_win_flow_24h` | C0 | + | net notional share of wallets with a positive causal record predicts 24h drift |
| WA7 | wallet | beta (per SD) | d, 24h | `lose` | `f_lose_flow_24h` | C0 | - | net notional share of wallets with a negative causal record predicts 24h drift |
| WA8 | wallet | dll | \|move\|, 24h | `n24h_cov` | `f_n_new1d_24h` | M0v (LightGBM) | ΔLL>0 | number of wallets < 1d old trading in 24h adds to M0v for \|move\| 24h |
| XM1 | cross_market | beta (per SD) | d, 6h | `nr` | `f_nr_dev` | C0 | + | neg-risk sum deviation -(S-1)*mid/S predicts 6h drift |
| XM2 | cross_market | dll | \|move\|, 6h | `nr` | `f_nr_absdev` | M0v (LightGBM) | ΔLL>0 | \|neg-risk sum - 1\| adds to M0v for \|move\| 6h |
| XM3 | cross_market | beta (per SD) | d, 2h | `nr_sib2` | `f_sib_nr_d2h` | C0 | - | sum of neg-risk siblings' 2h changes predicts own 2h drift |
| XM4 | cross_market | beta (per SD) | d, 2h | `co_sib2` | `f_sib_d2h` | C0 | + | mean 2h change of non-neg-risk siblings predicts own 2h drift |
| XM5 | cross_market | beta (per SD) | d, 24h | `nr_sib24` | `f_sib_nr_d24h` | C0 | - | sum of neg-risk siblings' 24h changes predicts own 24h drift |
| XM6 | cross_market | beta (per SD) | d, 24h | `co_sib24` | `f_sib_d24h` | C0 | + | mean 24h change of non-neg-risk siblings predicts own 24h drift |
| XM7 | cross_market | beta (per SD) | d, 24h | `ladder` | `f_ladder_z` | C0 | + | IF-H2 decay-adjusted near/far ladder residual z predicts near-rung 24h drift |
| XM8 | cross_market | beta (per SD) | d, 6h | `ladder_v` | `f_ladder_viol` | C0 | - | near rung above the next later rung (monotonicity violation) predicts 6h fall |
| TI1 | time | dll | \|move\|, 2h | `all` | `f_hour_sin`, `f_hour_cos` | M0v (LightGBM) | ΔLL>0 | UTC hour of day adds to M0v for \|move\| 2h |
| TI2 | time | dll | \|move\|, 6h | `all` | `f_wd_0` ... (7 cols) | M0v (LightGBM) | ΔLL>0 | weekday adds to M0v for \|move\| 6h |
| TI3 | time | beta (raw) | d, 24h | `near72` | `f_mid_c` | C0M | + | within 72h of scheduled end, mid - 0.5 predicts 24h drift (favourites up) |
| TI4 | time | beta (raw) | d, 24h | `mid35` | `f_near_end` | C0M + `ml_logit_mid` | - | for mid <= 0.35, being within 72h of scheduled end predicts 24h decay |
| TI5 | time | beta (raw) | d, 2h | `all` | `f_rev_weekend` | C0 + `f_weekend` | - | 2h reversal stronger at weekends (UTC) |
| CA1 | category | dll | \|move\|, 6h | `all` | `f_cat_sports` ... (11 cols) | M0v (LightGBM) | ΔLL>0 | fee category adds to M0v for \|move\| 6h |
| CA2 | category | dll | 3-class, 24h | `all` | `f_cls_asymmetric`, `f_cls_public`, `f_cls_other` | M0v (LightGBM) | ΔLL>0 | asymmetry class adds to M0v for 3-class direction 24h |
| CA3 | category | beta (raw) | d, 2h | `all` | `f_rev_asym` | C0 + `f_asym` | + | 2h reversal weaker in decision-asymmetric markets |
| CA4 | category | beta (per SD) | d, 24h | `n6h` | `f_flow_asym` | C0 + `f_imb_6h`, `f_asym` | + | 6h flow predicts 24h drift more in decision-asymmetric markets |
| CA5 | category | beta (raw) | d, 24h | `all` | `f_asym_longshot` | C0 + `f_asym`, `f_low20` | - | longshots (mid <= 0.20) in decision-asymmetric markets drift differently |
| PX1 | extremity | beta (raw) | d, 24h | `all` | `f_longshot` | C0M | - | mid <= 0.15 predicts 24h downward drift (favourite-longshot) |
| PX2 | extremity | beta (raw) | d, 24h | `all` | `f_favourite` | C0M | + | mid >= 0.85 predicts 24h upward drift |
| PX3 | extremity | mean | Y0 - mid, resolution | `res_long` | (intercept) | none | - | resolution excess Y0 - mid < 0 for mid <= 0.15 (longshots overpriced) |
| PX4 | extremity | mean | Y0 - mid, resolution | `res_fav` | (intercept) | none | + | resolution excess Y0 - mid > 0 for mid >= 0.85 (favourites underpriced) |
| PX5 | extremity | beta (raw) | d, 24h | `all` | `f_mom_extreme` | C0 + `f_extreme` | + | 1d momentum continues within 0.10 of 0/1 |
| PX6 | extremity | beta (per SD) | d, 24h | `n24h` | `f_flow_longshot` | C0 + `f_imb_24h`, `f_low20` | - | 24h flow at mid <= 0.20 (longshot buying) predicts 24h drift differently |
| LQ1 | liquidity | dll | \|move\|, 6h | `book_prev` | `f_bk_depth_chg` | M0v (LightGBM) | ΔLL>0 | 6h change of 5c book depth adds to M0v for \|move\| 6h |
| LQ2 | liquidity | beta (per SD) | d, 6h | `book_prev` | `f_bk_side_withdraw` | C0 | + | ask-side minus bid-side depth withdrawal over 6h predicts 6h drift |
| LQ3 | liquidity | dll | \|move\|, 6h | `book` | `f_bk_log_depth` | M0v (LightGBM) | ΔLL>0 | log 5c book depth adds to M0v for \|move\| 6h |
| LQ4 | liquidity | dll | \|move\|, 6h | `book_prev` | `f_bk_spread_chg` | M0v (LightGBM) | ΔLL>0 | 6h spread change adds to M0v for \|move\| 6h |
| LQ5 | liquidity | dll | \|move\|, 6h | `n24h` | `f_illiq_surprise` | M0v (LightGBM) | ΔLL>0 | Amihud illiquidity 24h vs 7d (log ratio) adds to M0v for \|move\| 6h |
| VO1 | volatility | dll | \|move\|, 6h | `all` | `f_jump_ratio` | M0v (LightGBM) | ΔLL>0 | largest 10-min jump in 6h over 7d rv adds to M0v for \|move\| 6h |
| VO2 | volatility | dll | \|move\|, 6h | `all` | `f_vol_of_vol` | M0v (LightGBM) | ΔLL>0 | dispersion of 2h rv over 24h adds to M0v for \|move\| 6h |
| VO3 | volatility | dll | \|move\|, 2h | `all` | `f_vol_ratio` | M0v (LightGBM) | ΔLL>0 | rv 2h / rv 7d adds to M0v for \|move\| 2h |
| VO4 | volatility | dll | \|move\|, 6h | `all` | `f_hours_since_move` | M0v (LightGBM) | ΔLL>0 | hours since the last >= 1c 10-min move adds to M0v for \|move\| 6h |
| VO5 | volatility | beta (per SD) | d, 24h | `all` | `f_semivar_asym` | C0 | + | 24h up minus down semivariance share predicts 24h drift |
| IX1 | interaction | beta (per SD) | d, 24h | `convex` | `f_convex_pressure` | C0 | + | convex longshot pressure (theory 4a) predicts 24h drift in its direction |
| IX2 | interaction | beta (per SD) | d, 24h | `n2h3` | `f_pressure_noresp` | C0 + `f_imb_2h` | + | pressure without price response (theory 4b) predicts 24h continuation |
| IX3 | interaction | beta (per SD) | d, 24h | `n6h_quiet` | `f_flow_quiet` | C0 + `f_imb_6h`, `f_quiet` | + | 6h flow in a quiet market (24h notional below own 29-day median) predicts more |
| IX4 | interaction | beta (per SD) | d, 6h | `n6h_near` | `f_flow_near_end` | C0 + `f_imb_6h`, `f_near_end` | + | 6h flow predicts 6h drift more within 72h of scheduled end |
| IX5 | interaction | beta (raw) | d, 24h | `n24h_cov` | `f_convex_dir` | C0 | + | net direction of >= $1,000 trades acquiring an outcome at <= 0.20 |
| IX6 | interaction | beta (per SD) | d, 24h | `fresh` | `f_fresh_asym` | C0 + `f_fresh_flow_24h`, `f_asym` | + | fresh-wallet flow predicts more in decision-asymmetric markets |

Populations (each within rows with a trade before t unless noted):

- `all`: all primary rows
- `book`: has_book
- `book_prev`: has_book_prev
- `n1h`: f_n_1h >= 1
- `n2h`: f_n_2h >= 1
- `n6h`: f_n_6h >= 1
- `n24h`: f_n_24h >= 1
- `n24h_7d`: f_n_24h >= 1 and f_N_7d > 0
- `small6h`: f_n_small_6h == 1
- `persist`: f_persist_6h defined
- `nw`: nw_share_new7d defined
- `fresh`: f_n_fresh_24h == 1
- `fresh_extreme`: f_n_fresh_24h == 1 and (mid <= 0.20 or mid >= 0.80)
- `top1`: f_top1_dir defined and f_n_wallets_24h >= 2
- `win`: f_n_win_24h == 1
- `lose`: f_n_lose_24h == 1
- `nr`: f_nr_dev defined (complete neg-risk sum)
- `nr_sib2`: f_sib_nr_d2h defined
- `nr_sib24`: f_sib_nr_d24h defined
- `co_sib2`: f_sib_d2h defined
- `co_sib24`: f_sib_d24h defined
- `ladder`: f_ladder_z defined
- `ladder_v`: f_ladder_viol defined
- `near72`: 0 < hours_to_end <= 72
- `mid35`: mid <= 0.35 and hours_to_end known
- `res_long`: resolved binary market and mid <= 0.15
- `res_fav`: resolved binary market and mid >= 0.85
- `convex`: f_n_2h >= 3 and p_acq <= 0.20 and f_convex_pressure defined
- `n2h3`: f_n_2h >= 3 and f_top1_share defined
- `n6h_quiet`: f_n_6h >= 1 and f_quiet defined
- `n6h_near`: f_n_6h >= 1 and f_near_end defined
- `n24h_cov`: f_n_24h defined (24h trade window covered)

## 9. Feature glossary

Notation: `t` origin; `s` = `s_last(t)`; `mid` = panel mid at `t`; trade sign `sgn` = +1 when it acquires token 0
(BUY outcome 0 or SELL outcome 1); `n` = USDC notional (size x traded price); `p0` = trade price in token-0 terms;
`ref` = series price usable at the trade's own time; `N_W`, `n_W` = notional and count over `[s-W, s)`;
`imb_W` = sum(sgn n) / N_W (NaN without trades); `dprev` = `ml_own_dmid_prev` (NaN -> 0); `rv_W` = panel realised
volatility.

- Market state: `f_log_age` = log1p(market age h); `f_log_last_trade_age` = log1p(min(h since the last trade before s,
  720)); `f_vol_surprise` = log1p(N_24h) - log1p(N_7d / 7); `f_vol_confirm` = sign(chg_1d) x `f_vol_surprise`.
- Microstructure: `f_illiq` = 1[N_24h < discovery median]; `f_no_trade_2h` = 1[n_2h = 0]; `f_z_lrv1d` =
  z(log(rv_1d + 1e-4)); `f_extreme` = 1[min(mid, 1 - mid) < 0.10]; `f_z_lte` = z(log1p hours to end); `f_confirm` =
  1[sign(imb_2h) = sign(dprev) != 0]; `f_rev_*` = dprev x the moderator; `f_spread_proxy` = median over trades in
  [s-24h, s) of |p0 - ref|; `bk_ml_sw_spread`, `bk_ml_sw_imb_1c`, `bk_ml_sw_microprice_disp` = pmxt book at `t`.
- Flow: `f_imb_1h/2h/6h/24h`; `f_large_flow_6h` = sum over 6h trades with n >= $500 of sgn n / max(N_7d / 7, 100);
  `f_small_imb_6h` = imbalance of 6h trades with n < $50; `f_agg_flow_6h` = sum over trades with
  sgn (p0 - ref) >= 0.01 of sgn n / N_6h; `f_persist_6h` = sign of imb in [s-2h, s) if the three 2h windows of
  [s-6h, s) all trade with the same sign, else 0 (NaN if one is empty); `f_flow_surprise` = imb_24h - imb_7d;
  `f_burst_2h` = n_2h / (n_24h / 12).
- Wallet: `nw_share_new7d` (existing table); `f_fresh_flow_24h` = sum over trades by wallets whose first Polymarket
  trade is < 7 days before the trade of sgn n / N_24h; `f_top1_dir` = top wallet's 24h notional share x sign(its net
  sgn n); `f_hhi_24h` = sum of squared wallet shares; `f_win_flow_24h` / `f_lose_flow_24h` = sum of sgn n / N_24h over
  trades by wallets with >= 2 known resolved sample markets and a shrunk record `sum(edge_m) / (k + 3)` above 0.05 /
  below -0.05, where `edge_m` is the wallet's notional-weighted `payout - price` of acquired outcomes in market m;
  `f_n_new1d_24h` = distinct wallets whose first trade is < 1 day before their trade.
- Cross-market: `S` = mid + sum of alive neg-risk siblings' prices; `f_nr_dev` = -(S - 1) x mid / S;
  `f_nr_absdev` = |S - 1|; `f_sib_nr_d2h/d24h` = sum of alive neg-risk siblings' price changes over 2h / 24h;
  `f_sib_d2h/d24h` = mean change of siblings in non-neg-risk events (sampled or fetched); ladder (own market = near
  rung j, far = rung j + 1): `N = v_near / v_far`, constant hazard `h` fitted to `v_far` at `t-6h`,
  `R = (N(t) - N(t-6h)) - (Nc(t) - Nc(t-6h))`, `f_ladder_z` = R / sd(R at the 56 previous 6h steps, >= 8 values),
  defined only with >= 2 days to the near deadline (IF-H2 `ifx_term`); `f_ladder_viol` = max(0, v_near - v_far).
- Time: `f_hour_sin/cos` (UTC hour); `f_wd_0..6`; `f_weekend`; `f_near_end` = 1[0 < hours to end <= 72];
  `f_mid_c` = mid - 0.5.
- Category: `f_cat_*` (fee category); `f_cls_*` (asymmetry class); `f_asym` = 1[asymmetric]; `f_low20` =
  1[mid <= 0.20]; `f_asym_longshot` = `f_asym` x `f_low20`; `f_flow_asym` = imb_6h x `f_asym`.
- Extremity: `f_longshot` = 1[mid <= 0.15]; `f_favourite` = 1[mid >= 0.85]; `f_mom_extreme` = chg_1d x `f_extreme`;
  `f_flow_longshot` = imb_24h x `f_low20`.
- Liquidity: book 5c depth `D` = bid + ask depth within 5c; `f_bk_log_depth` = log1p(D); `f_bk_depth_chg` = change of
  log1p(D) vs the book 6h earlier; `f_bk_side_withdraw` = change of log1p(bid 5c) minus change of log1p(ask 5c);
  `f_bk_spread_chg`; `f_illiq_surprise` = log((I_24h + 1e-6) / (I_7d + 1e-6)) with
  `I_24h` = sum |10-min change| over 24h / (N_24h + 100) and `I_7d` = the 7-day sum / (N_7d + 700).
- Volatility: `f_jump_ratio` = largest |10-min change| in 6h / (rv_7d + 1e-4); `f_vol_of_vol` = sd / mean of rv_2h at
  t, t-2h, ..., t-22h (>= 6 values); `f_vol_ratio` = rv_2h / (rv_7d + 1e-4); `f_hours_since_move` = hours since the
  last 10-min change >= 0.01 (cap 168); `f_semivar_asym` = (up - down semivariance) / total over 24h.
- Interactions (theory section 4): `f_convex_pressure` = imb_2h x log1p(largest 2h trade / mean 24h trade) x top-1
  wallet share (population: >= 3 trades in 2h, acquired-outcome price <= 0.20); `f_pressure_noresp` = imb_2h x top-1
  share x 1[sign(imb_2h) x dprev <= 0]; `f_quiet` = 1[N_24h < median of the prior 29 daily notionals after the first
  trade, >= 7 days]; `f_flow_quiet` = imb_6h x `f_quiet`; `f_flow_near_end` = imb_6h x `f_near_end`; `f_convex_dir` =
  sign of the net sgn n of 24h trades >= $1,000 that acquire an outcome priced <= 0.20; `f_fresh_asym` =
  `f_fresh_flow_24h` x `f_asym`.

## 10. Disclosures made before any outcome

- **The judgement half is not virgin for every family.** r0-r3 (`HISTORICAL_ML_DEV.md`) ran walk-forward ablations
  over all `h2_main` periods for the `state_extra`, flow, wallet and wallet-age families; flow was "demonstrated" at
  2h/6h there (unaligned windows; r3 traced much of it to last-trade-versus-series staleness). This battery is a
  further revision on the same window, beyond the per-window budget of 3; it is reported as such and cannot license
  more than L1. Cross-market, time, category, book/liquidity and extremity hypotheses have not been screened on
  `h2_main` by this programme; resolution calibration was studied on other samples (C1, T5-DEV; the T5-DEV 7d gap
  was an untraded-row artefact).
- **Pre-declaration code checks:** feature coverage was inspected on 30 markets (no targets), and the whole pipeline
  was run on about 54 markets with **globally permuted targets** (no outcome relation visible). Two code defects were
  fixed then (the economics gross used the class label for 3-class survivors; the permutation placebo permuted the raw
  rather than the residualised feature). No statistic on real outcomes was computed before this file was committed.
- **IF-H2 overlap:** a separate workstream runs the dedicated IF-H2 study (`if_h2.py`, c986fde). XM7/XM8 use their own
  implementation on the 36 `h2_main` ladders only and overlap part of that study's universe; HB1 results must not be
  used to tune that study.
- **Known weak spots:** ladder and book populations are small (low power: an untestable or null result there is not
  evidence of absence); first-trade coverage is partial; neg-risk sums assume reported prices of untraded members
  (sibling trades were not fetched); augmented neg-risk events and events with more than 25 members are excluded;
  the frame under-represents markets living less than a day (`HISTORICAL_ML_DEV.md`); fees of the current era are
  applied to older rows.

## 11. Results

Pending: appended after the single run.
