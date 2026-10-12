# HB1 replication on `h3_power` (HB1-R)

`evidence_role: exploratory_historical` | revision `hb1_replication_h3` | status: **DECLARED before any `h3_power`
outcome was computed** (sections 0-6). Results are appended in section 7 after the single run. Development evidence on
historical data only: no prospective, confirmation, edge, calibration or profitability claim.

## 0. Purpose

Test whether the 18 hypotheses that passed BY in hypothesis battery 1 (HB1, `HYPOTHESIS_BATTERY_1.md`, all on
`h2_main`) replicate on an independent sample of markets, with HB1's definitions and estimators frozen. Separately,
re-test three wallet-age hypotheses that were null in HB1, because `h3_power` has its own wallet first-trade lookups.

## 1. Data

- **`h3_power`:** 10,000 binary markets drawn from a 365-day random-window frame that excludes every `h1_first` and
  `h2_main` market (`params.exclude_runs`), with 3x oversampling of decision-asymmetric topics. Panels exist for 5,112
  markets (582,587 origins on the 2h grid). **Primary rows** (programme rule, `traded_before_t != 0`): 211,515 rows,
  3,203 markets, 2,688 events, 2025-06-30 to 2026-10-12; 52% fall before the HB1 split date and 47% after it.
- **Overlap with `h2_main`:** 0 markets, 66 events (different markets of the same events). A declared sensitivity drops
  those events.
- **Same calendar:** the replication uses new markets, not a new time period; market-wide shocks are shared with HB1.
- **`sample_weight`** (panel column): design weight of the topic oversampling, 5 to 41 (decision-asymmetric topics about
  8-10, others about 25-29).
- **Wallet first trades:** merged map `h3_power/new_wallets/first_trade_merged.jsonl` (19,230 wallets: HB1's 9,621 plus
  9,609 new lookups for every h3 wallet with a trade of at least $500); `nw_share_new7d` from
  `new_wallet_features_h3_power.csv.gz`. Coverage (share of 24h notional from wallets with a known first trade): mean
  0.511 (median 0.587) on h3 against 0.475 (0.452) on h2, so only modestly better.
- No sibling or book data are needed (no survivor uses them); those columns are NaN.

## 2. Frozen definitions

- **Spec:** `backend/astrolabe/research_lab/model_specs/hb1_replication_v1.json`, sha256 `f9b7341628ff7653c3cc5697a3af355e9a89373df5b0a895f4035a95a952a8f6`, built only from
  the HB1 results file (h2). For each hypothesis: HB1's feature, population, controls, target and horizon (code in
  `battery.py`, HB1 declaration hash `9e0f15de...`), **HB1's tested direction**, **HB1's scaling** (winsor bounds and SD
  from h2 discovery rows, applied unchanged to h3), **HB1's moderator cuts** (never re-estimated on h3), HB1's judgement
  effect and CI (the comparison), and HB1's economics rule (discovery slope and threshold).
- Code: `battery_replication.py`, `scripts/run_hb1_replication.py`. Changes to `battery.py` since HB1 are optional row
  weights in the estimators (unweighted results unchanged; unit-tested against a WLS sandwich) and a configurable
  first-trade map and extra panel columns in `build_features`.

| ID | Fam | Test | Target, h | Population | Feature | Controls | Frozen scaling | Direction | HB1 judgement effect [95% CI] | HB1 n (events) | Econ rule: beta_disc, tau |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MI1 | R | beta | d, 2h | `n24h_cov` | `f_rev_illiq` | C0 + `f_illiq` | raw | - | -18.891c [-24.012, -13.392] | 172,519 (490) | -0.18236, 0.00182 |
| MI2 | R | beta | d, 2h | `n24h_cov` | `f_rev_notrade` | C0 + `f_no_trade_2h` | raw | - | -27.131c [-33.147, -20.527] | 172,519 (490) | -0.26653, 0.00453 |
| MI3 | R | beta | d, 2h | `all` | `f_rev_vol` | C0 + `f_z_lrv1d` | raw | - | -21.137c [-26.722, -12.083] | 172,519 (490) | -0.22286, 0.00524 |
| MI5 | R | beta | d, 2h | `all` | `f_rev_tte` | C0 + `f_z_lte` | raw | - | -5.206c [-7.446, -2.465] | 171,574 (489) | -0.02356, 0.00042 |
| MI6 | R | beta | d, 2h | `n24h_cov` | `f_rev_confirm` | C0 + `f_confirm` | raw | + | +33.923c [+27.669, +39.655] | 172,519 (490) | +0.32509, 0.00000 |
| FL1 | R | beta | d, 2h | `n1h` | `f_imb_1h` | C0 | clip [-1.000, 1.000] / 0.9042 | + | +0.404c [+0.246, +0.647] | 10,164 (422) | +0.00360, 0.00398 |
| FL2 | R | beta | d, 6h | `n6h` | `f_imb_6h` | C0 | clip [-1.000, 1.000] / 0.8578 | + | +0.318c [+0.216, +0.441] | 33,042 (425) | +0.00284, 0.00331 |
| FL3 | R | beta | d, 24h | `n24h` | `f_imb_24h` | C0 | clip [-1.000, 1.000] / 0.8142 | + | +0.465c [+0.330, +0.623] | 64,315 (344) | +0.00409, 0.00502 |
| FL5 | R | beta | d, 6h | `small6h` | `f_small_imb_6h` | C0 | clip [-1.000, 1.000] / 0.8395 | + | +0.290c [+0.197, +0.404] | 31,134 (416) | +0.00274, 0.00326 |
| FL6 | R | beta | d, 6h | `n6h` | `f_agg_flow_6h` | C0 | clip [-1.000, 1.000] / 0.6580 | + | +0.430c [+0.323, +0.544] | 33,042 (425) | +0.00330, 0.00502 |
| FL8 | R | beta | d, 24h | `n24h_7d` | `f_flow_surprise` | C0 | clip [-1.813, 1.913] / 0.7106 | + | +0.193c [+0.094, +0.308] | 64,286 (344) | +0.00084, 0.00154 |
| FL10 | R | beta | d, 24h | `n2h` | `f_imb_2h` | C0 | clip [-1.000, 1.000] / 0.8945 | + | +0.591c [+0.398, +0.852] | 15,541 (333) | +0.00584, 0.00652 |
| WA4 | R | beta | d, 24h | `top1` | `f_top1_dir` | C0 | clip [-0.992, 0.982] / 0.6333 | + | +0.414c [+0.256, +0.614] | 42,825 (298) | +0.00328, 0.00483 |
| PX1 | R | beta | d, 24h | `all` | `f_longshot` | C0M | raw | + | +0.482c [+0.306, +0.674] | 168,295 (353) | +0.00508, 0.00508 |
| PX2 | R | beta | d, 24h | `all` | `f_favourite` | C0M | raw | + | +0.357c [+0.200, +0.566] | 168,295 (353) | +0.00429, 0.00000 |
| PX6 | R | beta | d, 24h | `n24h` | `f_flow_longshot` | C0 + `f_imb_24h`, `f_low20` | clip [-1.000, 1.000] / 0.6023 | - | -0.464c [-0.666, -0.278] | 64,315 (344) | -0.00305, 0.00506 |
| IX3 | R | beta | d, 24h | `n6h_quiet` | `f_flow_quiet` | C0 + `f_imb_6h`, `f_quiet` | clip [-1.000, 1.000] / 0.4191 | - | -0.171c [-0.280, -0.074] | 26,405 (175) | -0.00128, 0.00304 |
| VO4 | R | dll | \|move\|, 6h | `all` | `f_hours_since_move` | M0v (LightGBM) | - | ΔLL > 0 | +0.00215 [+0.00122, +0.00310] | 171,770 (444) | - |
| WA1 | W | dll | \|move\|, 24h | `nw` | `nw_share_new7d` | M0v (LightGBM) | - | ΔLL > 0 | +0.00211 [-0.00040, +0.00474] | 43,796 (287) | - |
| WA2 | W | beta | d, 24h | `fresh` | `f_fresh_flow_24h` | C0 | clip [-1.000, 1.000] / 0.3606 | + | +0.013c [-0.543, +0.641] | 2,609 (64) | - |
| WA3 | W | beta | d, 24h | `fresh_extreme` | `f_fresh_flow_24h` | C0 | clip [-1.000, 1.000] / 0.3790 | + | +0.240c [-0.389, +1.106] | 2,037 (53) | - |

Frozen HB1 cuts: {"illiq_median_N24": 0.256, "lrv1d_mean": -6.000259, "lrv1d_sd": 1.858416, "lte_mean": 6.654592, "lte_sd": 1.705909}

## 3. Rows and estimators (HB1's)

- **Beta tests (17 in family R, 2 in family W):** all h3 primary rows in the hypothesis population with the target and
  the controls available, **all dates** (direction, scaling and cuts are fixed, so no discovery rows are needed). OLS
  with the declared controls; **one-sided in the HB1 direction**; p = max(event-clustered p, two-way event x UTC-day
  p); 2,000-draw event-cluster bootstrap 95% CI. HB1's testability thresholds (>= 300 rows, >= 30 events, >= 100
  non-zero rows in >= 20 events).
- **ΔLL tests (VO4; WA1 in family W):** LightGBM with HB1's fixed configuration, M0v against M0v + feature, **fitted on h3
  rows with t + 24h <= 2026-07-01 and scored on h3 rows with t >= 2026-07-02** (HB1's split and embargo, inside h3);
  mean ΔLL one-sided > 0, same clustering rule.
- **Weighted (declared secondary):** the same tests with `sample_weight` (WLS slopes; weighted mean ΔLL with the models
  fitted unweighted).
- **Descriptive secondaries (unweighted, beta tests):** the h3 rows before the HB1 split, the h3 rows after it, and all
  rows without the 66 shared events (ΔLL tests: the shared-event exclusion only).

## 4. Decision rules

- **Family R:** Holm over the 18 one-sided p-values at alpha = 0.05, unweighted (primary). **Replicated** = Holm-adjusted
  p < 0.05 in the HB1 direction. **Replication rate** = replicated / 18. Also reported: count with nominal p < 0.05,
  sign agreement, and the weighted Holm result.
- **Shrinkage:** h3 estimate / HB1 judgement estimate (same units, because the scaling is frozen); median over the 18
  and over the replicated ones.
- **Cost check (paper only, "optimistic, not tradable"):** HB1's frozen rule. Signal `s = beta_disc(HB1) x x` with the
  frozen scaling; trade `sign(s)` on primary rows with `|s| >= tau(HB1)` and `s != 0`; gross = sign x `d_h` per share;
  taker cost = `EXECUTION_COSTS.md` band-median spread (h3 has no book data) plus entry and exit taker fees at the docs
  category rate (current fee era); also the optimistic half-spread, no-fee variant and a sample-weighted net mean.
  VO4 has no directional rule.
- **Family W (separate):** WA1 (ΔLL), WA2 and WA3 (beta), one-sided in the HB1 direction (positive), Holm over the 3 at
  alpha = 0.05, unweighted primary, weighted secondary. A rejection would turn an HB1 null into a development lead only.

## 5. Counting

21 tests (18 + 3), logged as `history_battery_replication` lines plus one `ml_explain` count line (source
`hypothesis_battery_1_replication`). Cumulative count after this run: 471 + 21 = 492 (plus anything other workstreams
add).

## 6. Disclosures before any h3 outcome

- The spec uses HB1 (h2) results only. h3 feature coverage, weights, dates and event overlap were inspected without
  targets.
- A smoke run of this code on 150 h3 markets with **globally permuted targets** exercised the pipeline (no real outcome
  relation visible): nothing "replicated" there, as expected.
- Weak spots known in advance: ladder, book and sibling features play no part; WA2/WA3 rest on rare fresh-wallet trades
  (HB1 had 64 and 53 judgement events), so family W has low power and a null there stays inconclusive; the same
  mid-like `prices-history` series is the target, so a mechanical series artefact would replicate too (only prospective
  Gamma/book mids settle that); 66 shared events.

## 7. Results

Pending: appended after the single run.
