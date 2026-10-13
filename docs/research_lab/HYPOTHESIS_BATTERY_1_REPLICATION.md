# HB1 replication on `h3_power` (HB1-R)

`evidence_role: exploratory_historical` | revision `hb1_replication_h3` | status: **DECLARED before any `h3_power`
outcome was computed** (sections 0-6, commit e5a3ef3); **results appended in section 7** after the single run. Development evidence on
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

## 7. Results (single run, 2026-10-13 01:23Z)

**Label: development evidence on historical data (`exploratory_historical`). No edge, calibration or profitability
claim.** Results file `data-dumps/research_lab/history/h3_power/battery1_rep/results_hb1_replication.json` (not
committed; sha256 in the `history_battery_replication` lines of `trials.jsonl`). Code at `e5a3ef3`, spec sha256
`f9b73416...`. The run waited about 90 minutes for the heavy lock (another workstream's h3 ML run) and started outside
the collector window. h3 feature table: 582,587 origins. Tests used 24,000-211,000 rows in 296-2,688 events (HB1:
175-490 judgement events).

### 7.1 Family R: the 18 HB1 survivors

- **Replication rate: 16 of 18 (89%)** under Holm at 0.05, unweighted (primary). The sample-weighted Holm result is the
  same 16.
- **Not replicated:** MI5 (2h reversal x time to end: -1.6c against HB1's -5.2c; nominal p 0.039, Holm 0.079; positive
  after July) and PX2 (favourite drift: +0.25c, p 0.12).
- **Sign agreement 18 of 18**; 17 of 18 have nominal p < 0.05.
- **Effect size: no shrinkage on average.** Median h3/HB1 ratio 1.20 (1.24 among the replicated). Flow effects are
  larger on h3 (median 1.48; FL6 +0.60c against +0.43c per SD); the trade-confirmation reversal moderators are about
  unchanged (median 0.92); VO4 is about half (0.55). Restricted to h3 rows after the HB1 split (the calendar HB1 was
  judged on), the median ratio is 1.16 (flow 1.23, MI 0.65): part of the larger flow effect comes from earlier months,
  where flow continuation was stronger (FL1 +0.81c before July, +0.43c after).
- **Fragile:** VO4's ΔLL roughly halves and loses significance when the 66 shared events are dropped (both LightGBM
  models refitted: +0.0012 to +0.0005, CI spanning 0), so its replication rests on a small, refit-sensitive ΔLL. MI5
  changes sign after July. Every beta result is stable without the shared events.

| ID | Dir | HB1 effect [CI] | h3 effect, unweighted [CI] | n (events) | p | Holm p | Replicated | Ratio to HB1 | h3 weighted effect [CI] | weighted Holm p | Ratio (weighted) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MI1 | - | -18.891c [-24.012, -13.392] | -17.399c [-21.553, -13.457] | 207,410 (2678) | 4.31e-17 | 6.03e-16 | **yes** | 0.92 | -17.597c [-22.554, -12.584] | 1.88e-11 | 0.93 |
| MI2 | - | -27.131c [-33.147, -20.527] | -24.874c [-29.241, -20.700] | 207,410 (2678) | 6.01e-28 | 1.02e-26 | **yes** | 0.92 | -25.071c [-30.176, -19.788] | 1.64e-18 | 0.92 |
| MI3 | - | -21.137c [-26.722, -12.083] | -25.702c [-30.608, -21.097] | 211,488 (2688) | 1.63e-25 | 2.60e-24 | **yes** | 1.22 | -30.446c [-36.269, -24.431] | 2.74e-24 | 1.44 |
| MI5 | - | -5.206c [-7.446, -2.465] | -1.626c [-3.133, +0.100] | 211,488 (2688) | 0.0394 | 0.0788 | no | 0.31 | -0.809c [-2.541, +1.228] | 0.4517 | 0.16 |
| MI6 | + | +33.923c [+27.669, +39.655] | +33.828c [+29.567, +38.265] | 207,410 (2678) | 1.26e-50 | 2.27e-49 | **yes** | 1.00 | +36.329c [+30.981, +41.635] | 3.50e-39 | 1.07 |
| FL1 | + | +0.404c [+0.246, +0.647] | +0.651c [+0.488, +0.840] | 24,179 (2234) | 1.39e-13 | 1.53e-12 | **yes** | 1.61 | +0.823c [+0.625, +1.052] | 4.99e-14 | 2.04 |
| FL2 | + | +0.318c [+0.216, +0.441] | +0.478c [+0.351, +0.617] | 57,963 (2102) | 2.71e-11 | 2.44e-10 | **yes** | 1.50 | +0.551c [+0.381, +0.738] | 7.46e-08 | 1.73 |
| FL3 | + | +0.465c [+0.330, +0.623] | +0.690c [+0.539, +0.858] | 90,800 (1424) | 2.74e-16 | 3.57e-15 | **yes** | 1.48 | +0.741c [+0.554, +0.947] | 1.94e-11 | 1.59 |
| FL5 | + | +0.290c [+0.197, +0.404] | +0.428c [+0.306, +0.557] | 55,316 (2057) | 1.96e-11 | 1.96e-10 | **yes** | 1.48 | +0.487c [+0.321, +0.651] | 7.46e-08 | 1.68 |
| FL6 | + | +0.430c [+0.323, +0.544] | +0.598c [+0.472, +0.727] | 57,963 (2102) | 1.62e-18 | 2.43e-17 | **yes** | 1.39 | +0.696c [+0.523, +0.877] | 3.21e-13 | 1.62 |
| FL8 | + | +0.193c [+0.094, +0.308] | +0.218c [+0.088, +0.364] | 90,618 (1422) | 7.40e-04 | 0.0037 | **yes** | 1.13 | +0.222c [+0.061, +0.386] | 0.0212 | 1.15 |
| FL10 | + | +0.591c [+0.398, +0.852] | +0.857c [+0.650, +1.092] | 27,070 (1360) | 7.39e-14 | 8.86e-13 | **yes** | 1.45 | +0.853c [+0.618, +1.101] | 2.76e-11 | 1.44 |
| WA4 | + | +0.414c [+0.256, +0.614] | +0.519c [+0.312, +0.738] | 61,707 (1125) | 1.09e-06 | 7.64e-06 | **yes** | 1.26 | +0.486c [+0.240, +0.741] | 6.72e-04 | 1.18 |
| PX1 | + | +0.482c [+0.306, +0.674] | +0.725c [+0.500, +0.972] | 194,023 (1457) | 6.91e-10 | 5.53e-09 | **yes** | 1.51 | +0.802c [+0.505, +1.104] | 1.92e-07 | 1.66 |
| PX2 | + | +0.357c [+0.200, +0.566] | +0.254c [-0.294, +0.630] | 194,023 (1457) | 0.1245 | 0.1245 | no | 0.71 | +0.121c [-0.696, +0.718] | 0.4517 | 0.34 |
| PX6 | - | -0.464c [-0.666, -0.278] | -0.501c [-0.711, -0.299] | 90,800 (1424) | 1.99e-06 | 1.19e-05 | **yes** | 1.08 | -0.539c [-0.784, -0.287] | 1.60e-04 | 1.16 |
| IX3 | - | -0.171c [-0.280, -0.074] | -0.203c [-0.386, -0.069] | 27,903 (296) | 0.0030 | 0.0121 | **yes** | 1.18 | -0.190c [-0.389, -0.034] | 0.0473 | 1.11 |
| VO4 | ΔLL>0 | +0.00215 [+0.00122, +0.00310] | +0.00118 [+0.00032, +0.00205] | 97,835 (845) | 0.0056 | 0.0168 | **yes** | 0.55 | +0.00151 [+0.00050, +0.00249] | 0.0212 | 0.70 |

### 7.2 Costs (HB1's frozen rule, paper only, "optimistic, not tradable")

Every directional hypothesis still loses as a taker on h3: net -1.2c to -4.1c per share (spread from the band
medians, since h3 has no books; fees at current docs rates). In the optimistic half-spread, no-fee variant only the
quote-noise reversals MI1, MI2 and MI3 are positive (+0.45c, +1.09c, +1.09c); the best flow signal, FL6, is -0.55c
[-0.78, -0.32]. Sample weighting moves the net by at most 0.4c.

| ID | Trades (events) | Gross | Spread | Fee | Net taker [CI] | Net taker, weighted [CI] | Net half spread, no fee [CI] | Hit rate |
|---|---|---|---|---|---|---|---|---|
| MI1 | 22,790 (800) | +1.739c | +2.577c | +1.168c | -2.006c [-2.21, -1.79] | -2.009c [-2.28, -1.71] | +0.451c [+0.25, +0.66] | 0.545 |
| MI2 | 22,891 (1216) | +2.368c | +2.563c | +1.126c | -1.321c [-1.51, -1.12] | -1.185c [-1.43, -0.93] | +1.087c [+0.90, +1.30] | 0.562 |
| MI3 | 25,377 (2064) | +2.355c | +2.534c | +1.052c | -1.231c [-1.44, -0.99] | -1.092c [-1.38, -0.78] | +1.088c [+0.88, +1.33] | 0.537 |
| MI5 | 28,494 (2442) | -0.061c | +2.572c | +0.975c | -3.609c [-3.92, -3.31] | -3.950c [-4.34, -3.55] | -1.347c [-1.68, -1.01] | 0.440 |
| MI6 | 16,736 (2079) | +0.156c | +2.749c | +0.692c | -3.285c [-3.48, -3.10] | -3.212c [-3.47, -2.95] | -1.218c [-1.39, -1.04] | 0.399 |
| FL1 | 1,280 (195) | +0.118c | +2.835c | +0.720c | -3.437c [-3.70, -3.05] | -3.464c [-3.74, -3.14] | -1.300c [-1.45, -1.08] | 0.270 |
| FL2 | 2,853 (220) | +0.128c | +2.848c | +0.778c | -3.498c [-3.75, -3.22] | -3.585c [-3.94, -3.25] | -1.296c [-1.49, -1.07] | 0.309 |
| FL3 | 6,539 (245) | +0.278c | +2.838c | +0.850c | -3.410c [-3.74, -3.08] | -3.355c [-3.73, -2.94] | -1.141c [-1.42, -0.86] | 0.411 |
| FL5 | 3,470 (238) | +0.054c | +2.890c | +0.743c | -3.579c [-3.83, -3.30] | -3.643c [-4.08, -3.26] | -1.391c [-1.61, -1.17] | 0.333 |
| FL6 | 13,451 (1379) | +0.816c | +2.739c | +0.733c | -2.656c [-2.90, -2.39] | -2.541c [-2.86, -2.20] | -0.554c [-0.78, -0.32] | 0.433 |
| FL8 | 7,606 (355) | +0.193c | +2.883c | +0.734c | -3.424c [-3.73, -3.08] | -3.252c [-3.69, -2.75] | -1.248c [-1.55, -0.92] | 0.386 |
| FL10 | 1,407 (167) | +0.444c | +2.895c | +0.731c | -3.181c [-3.61, -2.57] | -3.165c [-3.82, -2.49] | -1.003c [-1.35, -0.52] | 0.436 |
| WA4 | 5,662 (487) | +0.534c | +2.962c | +0.579c | -3.007c [-3.42, -2.53] | -2.978c [-3.50, -2.41] | -0.947c [-1.35, -0.51] | 0.485 |
| PX1 | 85,128 (719) | +0.447c | +3.427c | +0.405c | -3.385c [-3.53, -3.21] | -3.269c [-3.48, -3.04] | -1.267c [-1.41, -1.10] | 0.330 |
| PX2 | 10,561 (138) | -0.855c | +2.801c | +0.423c | -4.078c [-4.91, -3.53] | -4.522c [-5.45, -3.82] | -2.255c [-3.02, -1.77] | 0.380 |
| PX6 | 20,798 (604) | -0.158c | +3.365c | +0.449c | -3.972c [-4.16, -3.77] | -3.960c [-4.21, -3.68] | -1.840c [-2.04, -1.64] | 0.332 |
| IX3 | 1,840 (95) | +0.029c | +2.955c | +0.572c | -3.498c [-3.89, -3.04] | -3.320c [-3.85, -2.67] | -1.448c [-1.80, -0.99] | 0.358 |
| VO4 | not applicable | | | | | | | |

### 7.3 Family W: wallet-age nulls re-tested (separate Holm family)

- **WA2** (net notional share of wallets whose first trade is under 7 days old -> 24h drift): +0.62c per SD [+0.13,
  +1.17], p 0.010, **Holm 0.030 (rejects, unweighted primary)**; weighted +0.67c [-0.05, +1.40], Holm 0.10 (does not
  reject). HB1's null rested on 64 judgement events; h3 has 280.
- **WA1** (new-wallet volume share -> 24h `|move|`, ΔLL) and **WA3** (WA2 at extreme prices) stay null.
- Coverage was only modestly better (51% against 47.5% of 24h notional from wallets with a known first trade).
- Post-hoc (section 7.5): WA2 controlling for total 24h imbalance falls to +0.51c [-0.12, +1.22], p 0.067. So most of
  WA2 is ordinary flow continuation. Reading: **a weak development lead, not a wallet signal**. It would need its own
  registration with total imbalance as a control.

| ID | Dir | HB1 effect [CI] | h3 effect, unweighted [CI] | n (events) | p | Holm p | Replicated | Ratio to HB1 | h3 weighted effect [CI] | weighted Holm p | Ratio (weighted) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| WA1 | ΔLL>0 | +0.00211 [-0.00040, +0.00474] | -0.00186 [-0.00495, +0.00129] | 28,964 (384) | 0.8737 | 1.0000 | no | -0.88 | -0.00122 [-0.00465, +0.00240] | 1.0000 | -0.58 |
| WA2 | + | +0.013c [-0.543, +0.641] | +0.623c [+0.128, +1.168] | 7,069 (280) | 0.0100 | 0.0299 | **yes** | 47.35 | +0.667c [-0.047, +1.398] | 0.1018 | 50.68 |
| WA3 | + | +0.240c [-0.389, +1.106] | -0.031c [-0.480, +0.386] | 4,158 (194) | 0.5581 | 1.0000 | no | -0.13 | -0.030c [-0.659, +0.616] | 1.0000 | -0.13 |

### 7.4 Secondary windows (unweighted, descriptive)

| ID | Pre-split window effect [CI] (n) | Post-split window effect [CI] (n) | Without 66 shared events [CI] |
|---|---|---|---|
| MI1 | -20.296c [-25.313, -15.265] (106795) | -11.556c [-16.724, -5.793] (98969) | -17.391c [-21.182, -13.600] (202362) |
| MI2 | -28.205c [-33.662, -22.840] (106795) | -17.601c [-24.332, -11.739] (98969) | -24.782c [-28.557, -20.874] (202362) |
| MI3 | -20.394c [-26.640, -13.892] (110491) | -26.166c [-32.935, -20.016] (99328) | -26.201c [-30.669, -21.503] (206440) |
| MI5 | -3.431c [-5.513, -1.311] (110491) | +0.827c [-1.564, +3.256] (99328) | -1.672c [-3.383, -0.009] (206440) |
| MI6 | +36.449c [+31.036, +42.631] (106795) | +26.630c [+19.404, +33.712] (98969) | +33.961c [+29.230, +38.183] (202362) |
| FL1 | +0.806c [+0.635, +1.020] (15360) | +0.427c [+0.228, +0.688] (8605) | +0.651c [+0.484, +0.820] (23790) |
| FL2 | +0.555c [+0.370, +0.738] (34503) | +0.392c [+0.237, +0.588] (22917) | +0.501c [+0.366, +0.633] (56931) |
| FL3 | +0.693c [+0.450, +0.939] (51035) | +0.713c [+0.523, +0.952] (38834) | +0.678c [+0.518, +0.860] (88813) |
| FL5 | +0.518c [+0.351, +0.706] (32865) | +0.327c [+0.184, +0.502] (21932) | +0.444c [+0.333, +0.566] (54322) |
| FL6 | +0.614c [+0.460, +0.791] (34503) | +0.578c [+0.406, +0.759] (22917) | +0.624c [+0.494, +0.759] (56931) |
| FL8 | +0.227c [+0.029, +0.434] (50925) | +0.218c [+0.056, +0.417] (38762) | +0.213c [+0.086, +0.358] (88631) |
| FL10 | +0.849c [+0.599, +1.160] (16088) | +0.900c [+0.605, +1.339] (10684) | +0.882c [+0.662, +1.104] (26553) |
| WA4 | +0.600c [+0.301, +0.898] (34508) | +0.480c [+0.224, +0.784] (26570) | +0.488c [+0.308, +0.721] (60487) |
| PX1 | +0.669c [+0.350, +1.036] (100478) | +0.807c [+0.528, +1.133] (91936) | +0.715c [+0.517, +0.934] (189177) |
| PX2 | +0.483c [-0.296, +1.220] (100478) | +0.079c [-1.047, +0.599] (91936) | +0.283c [-0.240, +0.669] (189177) |
| PX6 | -0.494c [-0.806, -0.183] (51035) | -0.540c [-0.832, -0.251] (38834) | -0.488c [-0.679, -0.288] (88813) |
| IX3 | -0.196c [-0.401, +0.005] (13029) | -0.205c [-0.475, +0.003] (14568) | -0.219c [-0.379, -0.078] (27348) |
| VO4 | - | - | +0.00047 [-0.00259, +0.00240] (94817) |
| WA1 | - | - | +0.00225 [-0.00087, +0.00585] (28309) |
| WA2 | +0.601c [-0.109, +1.334] (5069) | +0.811c [+0.050, +2.276] (1938) | +0.606c [+0.089, +1.160] (6973) |
| WA3 | +0.090c [-0.519, +0.713] (3069) | -0.042c [-0.977, +0.464] (1065) | -0.016c [-0.429, +0.354] (4099) |

### 7.5 Post-hoc redundancy checks (labelled; not part of families R or W)

Run after the results, as for HB1; logged as `history_battery_posthoc` lines plus an `ml_explain` count line (2 tests).

| Hypothesis | Added control | Slope with the control (unweighted) | Weighted | Reading |
|---|---|---|---|---|
| WA2 fresh-wallet flow | `f_imb_24h` | +0.51c per SD [-0.12, +1.22], p 0.067 | +0.60c, p 0.094 | mostly total flow; inconclusive beyond it |
| WA4 top-wallet direction | `f_imb_24h` | -0.20c per SD [-0.64, +0.22], p 0.83 | -0.31c, p 0.88 | redundant with total imbalance (as in HB1) |

### 7.6 Reading

- The HB1 survivors replicate on new markets: market-level taker-flow continuation (1h-24h windows, aggressive flow,
  small trades, flow surprise), the trade-confirmation structure of the 2h reversal (moves without trades reverse,
  flow-confirmed moves do not), weaker continuation at longshot prices and in quiet markets, and the longshot price
  drift. They hold on 1,000-2,700 new events, with design weights or without.
- **What this does not show:** a new time period (same calendar, shared market-wide shocks) or mechanism. The target is
  the same mid-like `prices-history` series in both samples, so a series artefact would replicate too. Only
  prospective Gamma/book mids (E007-type registrations) settle that.
- HB1 candidates: C1 (FL6), C2 (FL3), C3 (MI2/MI6) and C4 (PX6) all replicate. C5 (VO4) is fragile. WA4 and FL5 stay
  redundant with total imbalance.
- **No cost viability:** nothing covers taker costs; only quote-noise reversals look positive under optimistic,
  untradable mid-to-mid accounting (E004's lesson).

### 7.7 Deviations and counting

- No deviation from the declared procedure. Two post-hoc redundancy checks were added after the results (7.5).
- Logged: 21 `history_battery_replication` lines, one `ml_explain` count line (21 tests), 2 post-hoc lines and their
  count line. Cumulative test count: 471 + 21 + 2 = 494, plus anything other workstreams have added.
