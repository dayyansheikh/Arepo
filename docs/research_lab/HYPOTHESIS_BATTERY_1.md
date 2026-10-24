# Hypothesis battery 1 (HB1): pre-declared screen on `h2_main`

`evidence_role: exploratory_historical` | provenance `EXPLORATORY_HISTORICAL` | revision `hb1_battery` |
status: **DECLARED before any outcome was computed** (sections 0-10, commit 7a4d80c); **results appended in section 11**
after the single run (2026-10-12 21:01Z). Development screen only: no prospective, confirmation, edge, calibration or profitability claim.

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

## 11. Results (single run, 2026-10-12 21:01Z)

**Label: DEVELOPMENT, `exploratory_historical`, screen-positive (L1) at most. No edge, calibration or profitability
claim.** Results file `data-dumps/research_lab/history/h2_main/battery1/results_hb1.json` (not committed; sha256 in
the `history_battery` lines of `trials.jsonl`).

### 11.1 Run facts

- Code at git head `75eb706` (declaration commit `7a4d80c` plus I/O-only fixes; declaration hash unchanged,
  `9e0f15de...`). The tree was dirty only through other workstreams' files.
- Sibling fetch: 3,848 of 3,848 tokens (3,741 neg-risk members, 107 ladder rungs), 8,386 requests, cap not reached,
  478 empty series (those events have incomplete neg-risk sums and drop out of XM1/XM2 by rule).
- Feature table: 420,937 origins; primary rows 278,463. With the 2h target: discovery 103,487 and judgement 172,519
  primary rows (490 judgement event clusters); with the 24h target: 353 judgement events.
- **Cumulative count at run time: 396 prior tests** (five `flow_screen` lines were appended by the live collector
  after the declaration; the declared rule uses the run-time value), so **m_total = 468**. BY passes the k-th
  smallest p below about k x 3.2e-5.
- **67 testable, 5 not testable** (p = 1, still counted): XM7 and XM8 (ladders: only 8 and 12 judgement events),
  LQ1 and LQ4 (consecutive pmxt books: under 2,000 discovery rows), IX5 (too few rows with a >= $1,000 convex
  trade).
- **Calibration placebo** (all 72 on globally permuted targets): 4 of 72 p below 0.05. Its only BY "survivors" are
  PX3 and PX4, and they are an artefact of the placebo, not of the data: a global permutation keeps the pooled mean
  resolution excess of resolved traded rows (about -7c), so a subgroup mean is not centred at 0 under it. The
  placebo is therefore not a null for the two mean tests (declared design flaw, disclosed here); the real PX3/PX4
  were not significant. For the other 70: 2 of 70 p below 0.05, so the clustered inference is calibrated or
  conservative. (The pooled -7c itself is an incidental, post-hoc observation about this sample and needs its own
  study; it is not a finding.)

### 11.2 Every result

Effects: beta and mean tests in cents of probability (price points x 100) per discovery SD of the feature (`per SD`)
or per unit (`raw`; interactions `dprev x moderator` are per unit of the 2h price change, so -27c means the slope on
the previous 2h change is 0.27 lower); dll tests in nats per judgement row. "Sign tested" comes from the discovery
fit. "BY within" is the descriptive BY over the 72 battery tests only.

| ID | Test | n judge (events) | Sign tested (source) | Discovery effect | Judgement effect | 95% CI (event boot) | z event / two-way | p | p BY cum. | Survivor | BY within |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MS1 | dll | 171,770 (444) | + (ΔLL>0) | - | -0.00177 | [-0.00296, -0.00054] | -2.83 / -2.83 | 0.997663 | 1.0000 | no | no |
| MS2 | dll | 171,770 (444) | + (ΔLL>0) | - | +0.00108 | [+0.00025, +0.00213] | +2.31 / +2.33 | 0.010445 | 1.0000 | no | no |
| MS3 | dll | 66,549 (432) | + (ΔLL>0) | - | +0.00076 | [+0.00002, +0.00138] | +2.17 / +2.13 | 0.016603 | 1.0000 | no | no |
| MS4 | beta | 64,286 (344) | + (disc) | +0.261c | +0.173c | [+0.074, +0.288] | +3.24 / +2.94 | 0.001626 | 0.2560 | no | yes |
| MI1 | beta | 172,519 (490) | - (disc) | -18.236c | -18.891c | [-24.012, -13.392] | -6.87 / -7.14 | 3.19e-12 | 2.51e-09 | **yes** | yes |
| MI2 | beta | 172,519 (490) | - (disc) | -26.653c | -27.131c | [-33.147, -20.527] | -8.34 / -8.37 | 3.84e-17 | 6.04e-14 | **yes** | yes |
| MI3 | beta | 172,519 (490) | - (disc) | -22.286c | -21.137c | [-26.722, -12.083] | -5.63 / -5.52 | 1.69e-08 | 8.86e-06 | **yes** | yes |
| MI4 | beta | 172,519 (490) | + (disc) | +16.740c | +11.206c | [+3.542, +21.383] | +2.35 / +2.23 | 0.013033 | 1.0000 | no | no |
| MI5 | beta | 171,574 (489) | - (disc) | -2.356c | -5.206c | [-7.446, -2.465] | -4.14 / -4.19 | 1.73e-05 | 0.0039 | **yes** | yes |
| MI6 | beta | 172,519 (490) | + (disc) | +32.509c | +33.923c | [+27.669, +39.655] | +11.03 / +11.72 | 1.31e-28 | 4.12e-25 | **yes** | yes |
| MI7 | dll | 172,519 (490) | + (ΔLL>0) | - | +0.00017 | [-0.00008, +0.00042] | +1.29 / +1.27 | 0.102269 | 1.0000 | no | no |
| MI8 | dll | 3,243 (155) | + (ΔLL>0) | - | +0.00353 | [-0.00187, +0.00896] | +1.30 / +1.17 | 0.121190 | 1.0000 | no | no |
| MI9 | beta | 3,243 (155) | + (disc) | +0.150c | +0.153c | [-0.014, +0.322] | +1.80 / +2.05 | 0.035578 | 1.0000 | no | no |
| MI10 | beta | 3,243 (155) | + (disc) | +0.361c | +0.029c | [-0.313, +0.350] | +0.20 / +0.21 | 0.420982 | 1.0000 | no | no |
| FL1 | beta | 10,164 (422) | + (disc) | +0.360c | +0.404c | [+0.246, +0.647] | +3.86 / +3.91 | 5.75e-05 | 0.0113 | **yes** | yes |
| FL2 | beta | 33,042 (425) | + (disc) | +0.284c | +0.318c | [+0.216, +0.441] | +5.42 / +5.90 | 2.96e-08 | 1.33e-05 | **yes** | yes |
| FL3 | beta | 64,315 (344) | + (disc) | +0.409c | +0.465c | [+0.330, +0.623] | +6.44 / +6.48 | 5.87e-11 | 3.70e-08 | **yes** | yes |
| FL4 | beta | 33,013 (425) | + (disc) | +0.028c | +0.029c | [-0.144, +0.204] | +0.35 / +0.41 | 0.363731 | 1.0000 | no | no |
| FL5 | beta | 31,134 (416) | + (disc) | +0.274c | +0.290c | [+0.197, +0.404] | +5.27 / +5.26 | 7.14e-08 | 2.81e-05 | **yes** | yes |
| FL6 | beta | 33,042 (425) | + (disc) | +0.330c | +0.430c | [+0.323, +0.544] | +7.42 / +8.02 | 6.06e-14 | 6.36e-11 | **yes** | yes |
| FL7 | beta | 4,100 (194) | + (disc) | +0.212c | +0.294c | [-0.131, +0.884] | +1.29 / +1.33 | 0.098255 | 1.0000 | no | no |
| FL8 | beta | 64,286 (344) | + (disc) | +0.084c | +0.193c | [+0.094, +0.308] | +3.57 / +3.72 | 1.79e-04 | 0.0313 | **yes** | yes |
| FL9 | dll | 66,578 (432) | + (ΔLL>0) | - | +0.00005 | [-0.00078, +0.00081] | +0.14 / +0.14 | 0.446181 | 1.0000 | no | no |
| FL10 | beta | 15,541 (333) | + (disc) | +0.584c | +0.591c | [+0.398, +0.852] | +4.70 / +4.71 | 1.29e-06 | 3.70e-04 | **yes** | yes |
| WA1 | dll | 43,796 (287) | + (ΔLL>0) | - | +0.00211 | [-0.00040, +0.00474] | +1.67 / +1.70 | 0.047140 | 1.0000 | no | no |
| WA2 | beta | 2,609 (64) | + (disc) | +0.126c | +0.013c | [-0.543, +0.641] | +0.05 / +0.05 | 0.482045 | 1.0000 | no | no |
| WA3 | beta | 2,037 (53) | + (disc) | +0.063c | +0.240c | [-0.389, +1.106] | +0.77 / +0.77 | 0.219592 | 1.0000 | no | no |
| WA4 | beta | 42,825 (298) | + (disc) | +0.328c | +0.414c | [+0.256, +0.614] | +4.57 / +4.44 | 4.58e-06 | 0.0011 | **yes** | yes |
| WA5 | dll | 64,315 (344) | + (ΔLL>0) | - | +0.00093 | [-0.00126, +0.00303] | +0.84 / +0.89 | 0.201057 | 1.0000 | no | no |
| WA6 | beta | 14,472 (238) | + (disc) | +0.245c | +0.279c | [+0.127, +0.453] | +3.26 / +3.07 | 0.001072 | 0.1776 | no | yes |
| WA7 | beta | 18,980 (234) | - (disc) | -0.120c | +0.056c | [-0.107, +0.203] | +0.72 / +0.73 | 0.767638 | 1.0000 | no | no |
| WA8 | dll | 168,295 (353) | + (ΔLL>0) | - | +0.00000 | [+0.00000, +0.00000] | +0.00 / +0.00 | 0.500000 | 1.0000 | no | no |
| XM1 | beta | 30,203 (127) | + (disc) | +0.736c | +0.188c | [-0.006, +0.443] | +1.70 / +1.66 | 0.048936 | 1.0000 | no | no |
| XM2 | dll | 30,203 (127) | + (ΔLL>0) | - | -0.00308 | [-0.01196, +0.00381] | -0.75 / -0.76 | 0.775517 | 1.0000 | no | no |
| XM3 | beta | 85,781 (201) | - (disc) | -0.107c | -0.094c | [-0.176, -0.026] | -2.47 / -2.66 | 0.006704 | 0.8514 | no | yes |
| XM4 | beta | 43,438 (93) | - (disc) | -0.062c | +0.012c | [-0.100, +0.122] | +0.21 / +0.24 | 0.594015 | 1.0000 | no | no |
| XM5 | beta | 84,009 (158) | + (disc) | +0.097c | +0.217c | [-0.032, +0.452] | +1.80 / +2.05 | 0.036194 | 1.0000 | no | no |
| XM6 | beta | 42,295 (75) | + (disc) | +0.349c | +0.082c | [-0.187, +0.342] | +0.62 / +0.59 | 0.278932 | 1.0000 | no | no |
| XM7 | beta | 3,648 | - | - | not testable: judgement too small (rows/clusters/nonzero) | - | - | 1 | 1.000 | no | no |
| XM8 | beta | 3,906 | - | - | not testable: judgement too small (rows/clusters/nonzero) | - | - | 1 | 1.000 | no | no |
| TI1 | dll | 172,519 (490) | + (ΔLL>0) | - | +0.00017 | [-0.00006, +0.00042] | +1.45 / +1.42 | 0.077278 | 1.0000 | no | no |
| TI2 | dll | 171,770 (444) | + (ΔLL>0) | - | +0.00158 | [+0.00058, +0.00288] | +2.64 / +2.65 | 0.004119 | 0.5894 | no | yes |
| TI3 | beta | 3,712 (178) | + (disc) | +3.787c | +0.329c | [-3.959, +3.848] | +0.17 / +0.16 | 0.435741 | 1.0000 | no | no |
| TI4 | beta | 119,934 (270) | + (disc) | +0.221c | -0.988c | [-2.394, +0.425] | -1.37 / -1.32 | 0.914988 | 1.0000 | no | no |
| TI5 | beta | 172,519 (490) | - (disc) | -2.230c | +3.023c | [-3.378, +9.408] | +0.95 / +0.82 | 0.829610 | 1.0000 | no | no |
| CA1 | dll | 171,770 (444) | + (ΔLL>0) | - | +0.00009 | [-0.00070, +0.00092] | +0.22 / +0.22 | 0.413271 | 1.0000 | no | no |
| CA2 | dll | 168,295 (353) | + (ΔLL>0) | - | +0.00048 | [-0.00166, +0.00291] | +0.42 / +0.41 | 0.340569 | 1.0000 | no | no |
| CA3 | beta | 172,519 (490) | + (disc) | +3.027c | -3.104c | [-12.200, +6.612] | -0.62 / -0.61 | 0.733865 | 1.0000 | no | no |
| CA4 | beta | 31,577 (338) | - (disc) | -0.384c | -0.048c | [-0.350, +0.207] | -0.32 / -0.33 | 0.373866 | 1.0000 | no | no |
| CA5 | beta | 168,295 (353) | + (disc) | +0.008c | +0.132c | [-0.402, +0.628] | +0.51 / +0.52 | 0.303708 | 1.0000 | no | no |
| PX1 | beta | 168,295 (353) | + (disc) | +0.508c | +0.482c | [+0.306, +0.674] | +5.25 / +5.15 | 1.28e-07 | 4.46e-05 | **yes** | yes |
| PX2 | beta | 168,295 (353) | + (disc) | +0.429c | +0.357c | [+0.200, +0.566] | +4.23 / +4.12 | 1.91e-05 | 0.0040 | **yes** | yes |
| PX3 | mean | 9,556 (177) | - (disc) | -1.022c | -2.213c | [-5.007, +2.052] | -1.28 / -1.32 | 0.099483 | 1.0000 | no | no |
| PX4 | mean | 2,060 (61) | + (disc) | +1.246c | -1.141c | [-12.774, +7.435] | -0.22 / -0.22 | 0.588779 | 1.0000 | no | no |
| PX5 | beta | 168,295 (353) | + (disc) | +4.486c | +8.661c | [+1.624, +15.272] | +2.51 / +2.93 | 0.006042 | 0.8270 | no | yes |
| PX6 | beta | 64,315 (344) | - (disc) | -0.305c | -0.464c | [-0.666, -0.278] | -4.73 / -4.77 | 1.10e-06 | 3.45e-04 | **yes** | yes |
| LQ1 | dll | 1,250 | - | - | not testable: too few rows/clusters | - | - | 1 | 1.000 | no | no |
| LQ2 | beta | 1,250 (125) | + (disc) | +0.167c | +0.421c | [+0.065, +0.838] | +2.18 / +2.79 | 0.014645 | 1.0000 | no | no |
| LQ3 | dll | 3,243 (155) | + (ΔLL>0) | - | +0.00516 | [+0.00029, +0.01035] | +2.03 / +2.16 | 0.021139 | 1.0000 | no | no |
| LQ4 | dll | 1,250 | - | - | not testable: too few rows/clusters | - | - | 1 | 1.000 | no | no |
| LQ5 | dll | 66,578 (432) | + (ΔLL>0) | - | -0.00051 | [-0.00119, +0.00027] | -1.31 / -1.36 | 0.912754 | 1.0000 | no | no |
| VO1 | dll | 171,770 (444) | + (ΔLL>0) | - | +0.00007 | [-0.00045, +0.00068] | +0.24 / +0.24 | 0.405380 | 1.0000 | no | no |
| VO2 | dll | 171,770 (444) | + (ΔLL>0) | - | +0.00138 | [+0.00048, +0.00248] | +2.71 / +2.72 | 0.003365 | 0.5045 | no | yes |
| VO3 | dll | 172,519 (490) | + (ΔLL>0) | - | -0.00006 | [-0.00030, +0.00016] | -0.48 / -0.45 | 0.684487 | 1.0000 | no | no |
| VO4 | dll | 171,770 (444) | + (ΔLL>0) | - | +0.00215 | [+0.00122, +0.00310] | +4.46 / +4.48 | 4.17e-06 | 0.0011 | **yes** | yes |
| VO5 | beta | 119,513 (353) | + (disc) | +0.004c | +0.104c | [+0.022, +0.189] | +2.56 / +2.47 | 0.006761 | 0.8514 | no | yes |
| IX1 | beta | 1,214 (117) | - (disc) | -0.112c | +0.465c | [-0.098, +1.431] | +1.53 / +1.49 | 0.936490 | 1.0000 | no | no |
| IX2 | beta | 4,874 (231) | - (disc) | -0.156c | -0.252c | [-0.472, +0.019] | -2.23 / -1.82 | 0.034627 | 1.0000 | no | no |
| IX3 | beta | 26,405 (175) | - (disc) | -0.128c | -0.171c | [-0.280, -0.074] | -3.64 / -3.58 | 1.72e-04 | 0.0313 | **yes** | yes |
| IX4 | beta | 32,857 (424) | + (disc) | +0.095c | +0.282c | [+0.026, +0.532] | +2.12 / +2.23 | 0.016818 | 1.0000 | no | no |
| IX5 | beta | 168,295 | - | - | not testable: judgement too small (rows/clusters/nonzero) | - | - | 1 | 1.000 | no | no |
| IX6 | beta | 2,609 (64) | - (disc) | -0.275c | -0.499c | [-1.516, +0.121] | -1.34 / -1.36 | 0.089406 | 1.0000 | no | no |

### 11.3 Survivors: 18 pass BY on the cumulative count

| Group | Survivors | Reading |
|---|---|---|
| 2h reversal moderators | MI1, MI2, MI3, MI5, MI6 | The 2h reversal of the mid-like series is much stronger after moves **without any trade** (MI2, -27c per unit move), in illiquid markets (MI1), at high volatility (MI3) and far from the end date (MI5, the E006 H2 sign), and almost disappears when the move is **confirmed by same-sign taker flow** (MI6, +34c). This is the quote-noise / bounce structure behind E004, now split by trade confirmation. |
| Flow continuation | FL1, FL2, FL3, FL6, FL10, FL8, (FL5, WA4) | Net taker imbalance predicts drift in its own direction at 2h, 6h and 24h (+0.3c to +0.6c per SD), with price-aligned windows, in 4 of 4 months and 8-10 of 10 categories, and it survives ending the windows 30 minutes earlier (68-94% of the effect). Aggressive flow (FL6) is the strongest 6h measure. FL5 (small trades) and WA4 (top-wallet direction) are redundant with plain imbalance (section 11.5). |
| Flow moderators | PX6, IX3 | Flow continues **less** at longshot prices (PX6: -0.46c per SD for mid <= 0.20) and in quiet markets (IX3: -0.17c; opposite to the theory prior). |
| Price-level drift | PX1, PX2 | Over 24h, mid <= 0.15 (+0.48c) and mid >= 0.85 (+0.36c) drift up relative to mid-range rows (PX1 opposite to the longshot-decay prior). Price only, so not "information beyond price". |
| Volatility | VO4 | Hours since the last 10-minute move of >= 1c adds 0.0021 nats per row (0.58% of the M0v loss) to the 6h \|move\| forecast. No direction. |

**Robustness (declared checks).** For flow, wallet and interaction survivors, "including untraded" and "trade in the
prior 24h" are identical to the main estimate by construction (any row with trades in the window has traded and has a
trade in the prior 24h); those two checks are informative only for MI and PX survivors.

| ID | Effect (judgement) | Months same sign | Categories same sign | Incl. untraded | Trade in prior 24h | Window -30 min | Permutation p |
|---|---|---|---|---|---|---|---|
| FL1 | +0.404c | 4/4 | 10/10 | +0.404c [+0.240, +0.619] | +0.404c [+0.240, +0.619] | +0.276c [+0.142, +0.460] | <0.005 (0 of 200) |
| FL10 | +0.591c | 4/4 | 10/10 | +0.591c [+0.407, +0.857] | +0.591c [+0.407, +0.857] | +0.495c [+0.322, +0.718] | <0.005 (0 of 200) |
| FL2 | +0.318c | 4/4 | 9/10 | +0.318c [+0.218, +0.446] | +0.318c [+0.218, +0.446] | +0.273c [+0.191, +0.382] | <0.005 (0 of 200) |
| FL3 | +0.465c | 4/4 | 10/10 | +0.465c [+0.329, +0.601] | +0.465c [+0.329, +0.601] | +0.439c [+0.311, +0.619] | <0.005 (0 of 200) |
| FL5 | +0.290c | 4/4 | 10/10 | +0.290c [+0.201, +0.401] | +0.290c [+0.201, +0.401] | +0.255c [+0.164, +0.358] | <0.005 (0 of 200) |
| FL6 | +0.430c | 4/4 | 10/10 | +0.430c [+0.316, +0.547] | +0.430c [+0.316, +0.547] | +0.358c [+0.251, +0.469] | <0.005 (0 of 200) |
| FL8 | +0.193c | 4/4 | 8/10 | +0.193c [+0.094, +0.305] | +0.193c [+0.094, +0.305] | +0.179c [+0.077, +0.298] | <0.005 (0 of 200) |
| IX3 | -0.171c | 3/4 | 7/8 | -0.171c [-0.275, -0.075] | -0.171c [-0.275, -0.075] | -0.162c [-0.271, -0.071] | <0.005 (0 of 200) |
| MI1 | -18.891c | 4/4 | 8/10 | -11.047c [-15.517, -6.161] | -6.967c [-23.733, +8.841] | - | <0.005 (0 of 200) |
| MI2 | -27.131c | 4/4 | 10/10 | -21.102c [-26.087, -15.444] | -23.340c [-30.705, -16.097] | - | <0.005 (0 of 200) |
| MI3 | -21.137c | 4/4 | 9/10 | -17.056c [-22.703, -9.239] | -18.857c [-29.174, -5.879] | - | <0.005 (0 of 200) |
| MI5 | -5.206c | 4/4 | 9/10 | -2.619c [-4.752, -0.437] | -2.453c [-5.021, +0.361] | - | <0.005 (0 of 200) |
| MI6 | +33.923c | 4/4 | 10/10 | +28.585c [+22.775, +33.202] | +30.398c [+24.022, +37.220] | - | <0.005 (0 of 200) |
| PX1 | +0.482c | 4/4 | 10/10 | +0.542c [+0.391, +0.701] | +0.419c [+0.185, +0.690] | - | <0.005 (0 of 200) |
| PX2 | +0.357c | 4/4 | 7/9 | +0.264c [+0.068, +0.473] | +0.622c [+0.133, +1.146] | - | <0.005 (0 of 200) |
| PX6 | -0.464c | 4/4 | 10/10 | -0.464c [-0.650, -0.283] | -0.464c [-0.650, -0.283] | - | <0.005 (0 of 200) |
| VO4 | +0.00215 | 4/4 | 8/10 | n/a | +0.00125 [+0.00035, +0.00226] | n/a | n/a |
| WA4 | +0.414c | 4/4 | 9/9 | +0.414c [+0.259, +0.608] | +0.414c [+0.259, +0.608] | +0.374c [+0.205, +0.575] | <0.005 (0 of 200) |

**Economics (paper only, `economics.py` fee formula; "optimistic, not tradable").** Rule in section 6.

| ID | Trades (events) | Gross mean | Spread | Fee | Net taker mean [CI] | Net half-spread, no fee [CI] | Hit rate | Book spread share |
|---|---|---|---|---|---|---|---|---|
| FL1 | 1,355 (104) | -0.003c | +2.973c | +0.955c | -3.931c [-4.16, -3.73] | -1.489c [-1.63, -1.24] | 0.173 | 0.067 |
| FL10 | 1,954 (121) | -0.002c | +3.008c | +0.940c | -3.949c [-4.13, -3.73] | -1.506c [-1.71, -1.14] | 0.345 | 0.057 |
| FL2 | 4,525 (135) | +0.038c | +2.936c | +1.039c | -3.937c [-4.05, -3.77] | -1.430c [-1.57, -1.25] | 0.250 | 0.030 |
| FL3 | 9,274 (144) | +0.020c | +2.840c | +1.160c | -3.980c [-4.23, -3.73] | -1.400c [-1.63, -1.17] | 0.343 | 0.019 |
| FL5 | 4,669 (138) | +0.144c | +2.922c | +1.065c | -3.843c [-3.97, -3.69] | -1.317c [-1.48, -1.12] | 0.265 | 0.032 |
| FL6 | 5,433 (316) | +0.428c | +2.899c | +1.221c | -3.693c [-3.99, -3.41] | -1.022c [-1.29, -0.78] | 0.417 | 0.026 |
| FL8 | 7,675 (167) | +0.162c | +2.966c | +1.030c | -3.834c [-4.09, -3.53] | -1.321c [-1.57, -1.01] | 0.351 | 0.019 |
| IX3 | 2,634 (82) | -0.190c | +2.971c | +0.962c | -4.122c [-4.40, -3.90] | -1.675c [-1.90, -1.45] | 0.282 | 0.037 |
| MI1 | 12,635 (216) | +1.490c | +3.059c | +1.478c | -3.046c [-3.38, -2.72] | -0.039c [-0.30, +0.23] | 0.566 | 0.017 |
| MI2 | 11,339 (285) | +2.008c | +2.931c | +1.521c | -2.444c [-2.76, -2.09] | +0.543c [+0.27, +0.87] | 0.584 | 0.017 |
| MI3 | 10,709 (378) | +2.130c | +2.945c | +1.555c | -2.370c [-2.71, -2.01] | +0.657c [+0.34, +1.01] | 0.566 | 0.022 |
| MI5 | 12,028 (438) | +0.910c | +2.947c | +1.509c | -3.546c [-3.97, -3.20] | -0.564c [-1.00, -0.20] | 0.482 | 0.024 |
| MI6 | 7,482 (406) | +0.133c | +2.848c | +1.202c | -3.918c [-4.09, -3.73] | -1.292c [-1.44, -1.13] | 0.356 | 0.051 |
| PX1 | 81,403 (224) | +0.274c | +3.354c | +0.595c | -3.676c [-3.79, -3.55] | -1.403c [-1.51, -1.27] | 0.266 | 0.019 |
| PX2 | 13,620 (55) | -0.099c | +2.834c | +0.573c | -3.507c [-3.77, -3.32] | -1.516c [-1.72, -1.39] | 0.235 | 0.018 |
| PX6 | 14,910 (203) | +0.035c | +3.302c | +0.664c | -3.931c [-4.10, -3.77] | -1.616c [-1.78, -1.46] | 0.312 | 0.021 |
| VO4 | not applicable: no directional trade rule (volatility or resolution-level test) | | | | | | | |
| WA4 | 3,874 (179) | +0.551c | +3.058c | +0.847c | -3.354c [-3.71, -2.90] | -0.978c [-1.33, -0.51] | 0.392 | 0.027 |

**No survivor covers taker costs.** Net per share as a taker is -2.4c to -4.1c for every directional survivor: the
top-decile gross is at most +2.1c (reversal of unconfirmed moves) and +0.4c for flow, against about 3c of spread and
0.6-1.6c of fees. In the optimistic variant (half the spread, no fee) only MI2 (+0.54c [+0.27, +0.87]) and MI3 (+0.66c
[+0.34, +1.01]) are positive: these are mid-to-mid reversals of quote noise, which a taker cannot capture (E004 found
the same prospectively). VO4 has no directional rule.

### 11.4 What did not survive

- **Wallet:** fresh-wallet volume share (WA1), fresh-wallet direction (WA2, WA3; only 64 and 53 judgement events),
  wallet HHI (WA5), new-wallet counts (WA8: ΔLL exactly 0, the model never used it) and prior-loser flow (WA7) are null. Prior-winner flow (WA6,
  a causal repeat-winner proxy) is the closest miss: +0.28c per SD [+0.13, +0.45], p 0.0011, BY-cumulative 0.18 (passes
  only within the battery). WA4 survived but is redundant with imbalance.
- **Cross-market:** neg-risk sum deviation (XM1, XM2) and sibling lead-lag (XM3-XM6) do not survive (XM3, neg-risk
  siblings' 2h changes, passes only within the battery: -0.09c per SD). This matches E005 ("not supported"
  prospectively). **IF-H2 ladders (XM7, XM8) were not testable on `h2_main`**: no evidence either way; the dedicated
  IF-H2 study is the right test.
- **Time:** hour of day (TI1) and weekday (TI2, within-battery only) add little to `|move|`; pre-resolution drift
  (TI3), longshot decay near the end date (TI4) and the weekend reversal (TI5) are null.
- **Category and asymmetry class:** all null (CA1-CA5), including flow x decision-asymmetric markets (CA4).
- **Book and liquidity (pmxt, 3,243 judgement rows, 155 events):** spread, depth imbalance, microprice, depth level and
  withdrawal are null or underpowered (LQ3 p 0.021; MI9 p 0.036); LQ1/LQ4 not testable.
- **Volatility:** jump ratio, rv ratio (null) and vol-of-vol, semivariance asymmetry (within-battery only).
- **Market state:** market age **hurts** the 6h `|move|` forecast out of sample (MS1, ΔLL -0.0018, CI below 0);
  volume-confirmed momentum (MS4) passes within the battery only.
- **Theory interactions:** convex longshot pressure (IX1, 117 events) and pressure without price response (IX2) are null;
  flow x near expiry (IX4) and fresh flow x asymmetric (IX6) are null; IX5 not testable (convex >= $1,000 trades are
  too rare in this sample).

### 11.5 Post-hoc redundancy checks (labelled; not part of the declared family)

Run after the results, only to avoid naming redundant candidates. Three extra tests, logged as
`history_battery_posthoc` lines plus one `ml_explain` count line (so the cumulative count is now 396 + 72 + 3 = 471).
Same judgement rows, scaling and tested sign; one added control.

| Survivor | Added control | Slope with the control | Reading |
|---|---|---|---|
| WA4 top-wallet direction | `f_imb_24h` | -0.14c per SD [-0.43, +0.14], p 0.85 | redundant: the top wallet adds nothing beyond total 24h imbalance |
| FL6 aggressive flow | `f_imb_6h` | +0.31c per SD [+0.19, +0.44], z 4.7 | incremental: aggressiveness carries most of the 6h flow signal |
| FL5 small-trade imbalance | `f_imb_6h` | +0.11c per SD [-0.11, +0.33], p 0.19 | redundant with total imbalance |

### 11.6 Candidates for live registration (declared rule, section 7)

Ranking: sign stability, live feasibility, economic headroom, then z; mechanically suspect survivors flagged. Not
named: PX1/PX2 (price level only, so outside "information beyond price"), MI1/MI3/MI5 (further quote-noise
moderators), FL1 (the E007 analogue, already confirmed prospectively), FL2/FL8/FL10 (overlap C1/C2), FL5 and WA4
(redundant), IX3 (3 of 4 months, 7 of 8 categories). Expect shrinkage: E002 kept about 2/3 and E007 about 70% of the
development effect. No candidate is an economic candidate: all fail the taker cost check.

**C1. HB1-FL6, aggressive taker flow -> 6h mid drift.**
- Feature at origin `t` (snapshot receipt): over the trade sample's taker trades in `[t-6h, t)`, `x = sum over trades
  with sgn*(p0 - ref) >= 0.01 of sgn*n / sum of n`, with the `trade_sample._sign` token-0 convention, `n` = USDC
  notional and `ref` = the last CLOB `prices-history` point (10-minute fidelity) stamped at least 10 minutes before the
  trade. Cheap addition: one `prices-history` request per sampled market with a trade in the window (roughly a fifth
  of the 2,000 sampled markets per pass; to be measured). A window cut by the 500-trade cap is NaN.
- Population: sampled markets with >= 1 trade in the window; traded before `t`.
- Target and test: Gamma mid change to the snapshot about 6h later; slope on `x` with `chg_1h`, `chg_1d`, previous-pass
  change and period intercepts as controls; event-clustered; one-sided `> 0`; >= 12 periods.
- HB1 development estimate: +0.43c per SD (SD 0.66), CI [+0.32, +0.54], z 7.4; 4/4 months, 10/10 categories; +0.36c
  with windows ending 30 min earlier; +0.31c beyond total imbalance (post-hoc).
- Economics: top-decile gross +0.43c, taker net -3.7c [-4.0, -3.4], optimistic -1.0c. Predictive only.

**C2. HB1-FL3, 24h net taker imbalance -> 24h mid drift (horizon extension of E007).**
- Feature: `imb_24h = sum sgn*n / sum n` over trade-sample taker trades in `[t-24h, t)` (strictly before the snapshot
  receipt; the E007 staleness check found the last 5-15 minutes immaterial). NaN when the 500-trade cap truncates the
  window (about the busiest 10% of markets; disclose).
- Population: >= 1 trade in the window. Target: Gamma mid change to the snapshot about 24h later (12 passes). Test as C1.
- HB1: +0.47c per SD (SD 0.81), CI [+0.33, +0.62], z 6.4; 4/4 months, 10/10 categories; +0.44c with windows ending 30
  minutes earlier.
- Caveat for the registration design: the top decile by `|imb|` is dominated by one-trade windows and its gross is
  about 0 (+0.02c), so the slope comes from markets with several trades. Any minimum-trade condition must be declared
  in the registration with its own justification; it was not tested here.
- Economics: taker net -4.0c; optimistic -1.4c.

**C3. HB1-MI2/MI6, trade confirmation of 2h moves (mechanism candidate; flagged quote noise).**
- Features from two consecutive snapshots and the trade sample: `dprev` = Gamma mid change over the previous pass;
  `NT = 1[no taker trade in [t-2h, t)]`; `CF = 1[sign(net 2h taker flow) = sign(dprev) != 0]`.
- Model: `d_next = a + b*dprev + c*dprev*NT + e*dprev*CF + controls`; a two-hypothesis Holm family: `c < 0` (unconfirmed
  moves revert more), `e > 0` (confirmed moves revert less).
- HB1: `c` = -0.27 [-0.33, -0.21] (z -8.3), `e` = +0.34 [+0.28, +0.40] (z 11.0), per unit of the 2h move; 4/4 months,
  10/10 categories each.
- Value: separates bounce from information in the E004 reversal and the E007 continuation. Not economic: reversal
  trades on unconfirmed moves have taker net -2.4c; the optimistic +0.54c is a mid-to-mid capture (E004).

**C4. HB1-PX6, flow continuation weaker at longshot prices (moderator).**
- Feature: `imb_24h x 1[mid <= 0.20]`, with `imb_24h` and `1[mid <= 0.20]` as controls; target Gamma mid change about 24h
  later; one-sided `< 0`.
- HB1: -0.46c per SD [-0.65, -0.28], z -4.7; 4/4 months, 10/10 categories.
- Value: at market level, buying pressure on cheap outcomes does not continue like ordinary flow (lottery-type demand).
  It does not test IF-H1 (rare, identity-gated episodes), but it argues against registering market-level "longshot
  pressure" as a continuation signal.

**C5 (optional, risk filter only). HB1-VO4, hours since the last >= 1c 10-minute move -> 6h `|move|`.**
- ΔLL +0.0021 nats per row over M0v (0.58%), CI [+0.0012, +0.0031], z 4.5; 4/4 months, 8/10 categories. Needs the
  10-minute path (`prices-history`) or a coarser snapshot proxy, which would be a different feature. Volatility only:
  a candidate for MC1's `|move|` target, never a directional signal.

### 11.7 Deviations and disclosures after the run

- m_total 468 instead of 463: the declared run-time recount (five collector `flow_screen` lines).
- The calibration placebo is not a null for the two mean tests (section 11.1). No verdict depends on it.
- Three post-hoc redundancy tests (section 11.5) were added after seeing the results; they are logged and counted and
  change no verdict, but they did shape the candidate list.
- For flow survivors the "including untraded" and "trade in prior 24h" checks are vacuous (section 11.3).
- **What this licenses:** a ranked shortlist for prospective registration, nothing more. The judgement half had already
  been seen by r0-r3 for the flow family, the series is mid-like and possibly trade-derived (flow could partly predict
  the series rather than the book mid; only prospective Gamma/book mids settle this), and the frame under-represents
  short-lived markets. Every candidate needs its own registration, MDE and `science-reviewer` pass.
