# Learned surprise-move detector (2026-10-12)

**Status:** `evidence_role: exploratory_historical`. A learned detector (`sm_learned_v1`) is frozen and
runs in the live monitor as an unregistered prospective collection; nothing here is a registered result,
an edge claim or a calibration claim. No wallet, trade or market is labelled as insider or informed activity;
the object of study is a *sharp, unanticipated price move* and the public, hashed-wallet conditions that
precede it.

Code: `backend/astrolabe/research_lab/surprise_moves.py` (labels, features, matched negatives, live price
context), `surprise_learn.py` (arms, walk-forward, incremental value, fixed-budget evaluation, placebo, case
recall), `backend/scripts/run_surprise_moves.py` (`log-labels`, `meta`, `build`, `learn`, `placebo`, `cases`,
`freeze`), tests `backend/tests/unit/test_research_lab_surprise_moves.py` and the learned-rule test in
`backend/tests/test_live_trade_monitor.py`. Data: `data-dumps/research_lab/surprise_moves/` (`rows.csv.gz`
39 MB, `events.csv.gz`, `results.json`, `placebo_ext.json`, `case_recall.json`, `test_scores.csv.gz`,
`lgb_mono_full.txt`, manifests; 46 MB new disk). Every arm, revision, the label spec, the placebo extension
and the freeze are lines of kind `surprise_labels` / `surprise_detector` in `trials.jsonl` (27 lines).

## 1. The idea and the order of operations

The hand-built unusual-flow rules (`UNUSUAL_FLOW_DETECTOR.md`) were a priori weights tuned on one case
(Maduro) and found nothing on the judgement half or the census. This study inverts the direction: find every
sharp move that was not anticipated by the price path, compare the pre-move conditions with matched
non-event windows, and let the data set the weights.

Governance order (each step logged before the next began):
1. **Labels fixed first.** `LABEL_SPEC` (`surprise-labels-v1`, sha256
   `d9cf42f7392a29cb27aa4e09deb9886c4e802e761e614cca8efc6af394a0cd73`) was written, hashed, logged
   (`trials.jsonl` kind `surprise_labels`, 2026-10-12T19:47:27Z) and committed (`2bd09ad`) before any
   feature was computed. The feature list (`surprise-features-v1`) was fixed in the same commit, before any fit.
2. **Split fixed before any fit** (`surprise_learn.SPLIT`): train months ≤ 2026-05, validation 2026-06 and
   2026-07, test months ≥ 2026-08 untouched until the single `evaluate_test` pass (the three `learn` runs
   re-read the same test months only to add matched controls, the matched-k hand-rule comparison and the
   placebo distribution; arms, hyper-parameters, features and split never changed between them; every run is
   logged).
3. Hand rules enter as frozen baselines (their `FROZEN.json` hashes, unchanged).

## 2. Labels (`surprise-labels-v1`)

Price source: CLOB `prices-history`, outcome-0 token, 10-minute fidelity, from the `history/h2_main` run
(3,200 seeded stratified markets, 2025-10 to 2026-10). A point stamped `t'` is usable only after `t' + 600 s`.

- **Sharp move.** *Arrival* `j`: the first 10-min point with `|p_j − p_ref| ≥ 0.15`, `p_ref` = the as-of price
  6 h earlier (age ≤ 2 h). *Departure* `i`: the latest point in `[t_j − 6 h, t_j)` with `|p_i − p_ref| < 0.05`,
  i.e. the last moment the price was still at its pre-move level. Direction = sign(`p_j − p_ref`). Cooloff 24 h
  per market after an arrival.
- **Variants.** `extreme10_6h`: ≥ 0.10 within 6 h from a departure price ≤ 0.20 or ≥ 0.80. `to_resolution_6h`:
  a primary move that reaches ≤ 0.02 or ≥ 0.98 within 6 h of departure. Both are labelled and stored; the
  primary label is `sharp15_6h`.
- **Surprise filters** (all must hold at the departure): |24 h pre-drift| < 0.05; 24 h pre-range < 0.10; at least
  6 price points in the prior 24 h (otherwise *unknown*, excluded, never treated as flat); the departure is not
  within the final hour before the scheduled end, or at/after `gameStartTime` when Gamma lists one (sports).
- **Positive row.** The 2 h grid origin `t_o = floor(t_dep / 7200) · 7200`; every feature uses data strictly before
  `t_o`. Training label `y = 1` iff a surprise departure falls in `(t, t + 2 h]`. Evaluation hit: departure in
  `(t, t + 6 h]` (primary) or `(t, t + 2 h]` (secondary); undirected.
- **Negatives (training).** 5 per positive from the same stratum (fee category × price band on |mid − 0.5|
  (0.05/0.20/0.45) × tercile of log 24 h notional × 6 h hour bucket), seeded hash order, from rows with no surprise
  departure of any variant within 24 h before or after. Same market allowed.
- **Exclusions.** Rows with `traded_before_t ≠ 1` (listing-price placeholders) everywhere; mid outside
  [0.02, 0.98]; 2,316 Maduro/Venezuela condition ids and the 16 catalogue condition ids (`exclusions.json`;
  the catalogue list re-hashes to the pinned `6cea3fc5…`). None of the 3,200 sample markets was in either list.

Counts. 8,860 raw events (all variants, before filters); primary sharp moves 5,645 of which **1,411 pass the
surprise filters** before the game-start cut and **1,186** after it (reasons for the rest: pre-window unknown
1,501, pre-drift 1,414, pre-range 950, final hour 369). Labelled positive rows (an eligible grid row exists
immediately before the departure): train 219, validation 143, test 240. Eligible rows: 277,605 of 420,937
(train 79,502 / valid 69,168 / test 128,935). Test-month base rate of a departure within 6 h: **0.56 %**.
1,441 of 3,200 markets have no grid row at all (shorter than the one-day history the grid needs: mostly
single-game sports and short crypto markets), as in the existing history panels.

## 3. Pre-event features (`surprise-features-v1`)

Windows 15 min, 1 h, 6 h, 24 h, all trades strictly before `t`, token-0 signs, NaN (never 0) when the window is
not inside the fetched trade history (`sm_covered_*`): count, log notional, |imbalance| (signed imbalance kept
only for the alert direction), largest trade / mean 24 h trade size, burst (count against the 24 h or 7 d pace),
distinct wallets, top-1 share, HHI, same-side wallet share and count, new-wallet count and volume share
(in-sample first-seen index of 132,976 hashed wallets, 14-day burn-in; **not** true first-trade times: the
`/activity` caches cover about 5 % of these wallets, and a panel-wide lookup is out of budget), price response in
the flow's direction, convex stake (|signed notional| × (1 − p_acq)/p_acq over the 24 h notional). Context:
mid, |mid − 0.5|, logit, distance to 0/1, log hours to end, market age, 1 h/1 d/1 w changes, own 2 h-grid
volatility, realised volatility over 2 h/6 h/1 d/7 d, hour of day (sin/cos), weekday, last-trade age, last-trade
price minus mid, fee category (one-hot), decision-asymmetry class A/B/C (`if_h1` class-v2 keyword rule on the
Gamma question; metadata pulled for all 3,200 markets, 159 requests), sibling moves (max |2 h change| over other
markets of the same event at the same grid time; 46 % coverage) and deadline-ladder moves (same question stem
after removing dates and numbers; 18 % coverage). 83 features in the full set; the "live" subset drops the
response, new-wallet, group and most price-history terms.

## 4. Arms, learning and feature ranking

| Arm | Model | Selection (one per arm, validation months) | Non-zero weights |
|---|---|---|---|
| `en_logit_full` | elastic-net logistic (l1 = 0.5) on clipped robust z-scores (centre = train median, scale = 1.4826·MAD, cap ±4, missing → centre) | C = 0.03 (valid log loss 0.419) | 20 of 83 |
| `lgb_mono_full` | LightGBM, monotone constraints from declared sign priors (+ for intensity/size/concentration/new-wallet/volatility, − for response, 0 for context) | 105 rounds (early stopping) | – |
| `en_logit_live` | elastic net on the live-computable subset | C = 0.01 | 2 (`sm_burst_6h`, `last_trade_age_h`) |
| 5 frozen hand rules | `detector_eval.score_rule` on the same rows (history mapping) | none | – |

Final weights are fit on train + validation (2,172 case-control rows, 362 positives). **Learned weights
(`en_logit_full`, standardised units):** `rv_1d` −0.46, `rv_7d` +0.23, `dow` −0.14, `rv_6h` +0.12,
`market_age_h` −0.08, `rv_2h` +0.08, `sm_large_rel_24h` −0.07, `sib_max_abs_chg_2h` +0.06, `sm_resp_24h` −0.05,
`sib_n` −0.05, `sm_burst_6h` +0.05, `last_trade_age_h` −0.04, `ladder_n` −0.04, `sm_same_side_share_24h` +0.02,
`abs_mid_dev` −0.02, `dist_01` +0.02, `sm_abs_imb_1h` +0.01, `log_hours_to_end` −0.01, `own_vol` −0.01,
`chg_1w` −0.003. Reading: a market that was volatile over the week but quiet over the last day, young, on a
weekday, with a 6 h burst and a sibling that just moved, and whose 24 h flow was *not* answered by price.

**Incremental out-of-sample value** (`ml_explain.ablation_study`, refit drop-one/add-one, expanding monthly
walk-forward over the development months, judged on the validation months, event-clustered bootstrap, BY over
106 units + 114 prior tests = 220): the full model beats the two-feature baseline (ΔLL +0.0125, CI
[+0.0023, +0.0239], p = 0.008). Family drop-one ΔLL: `price_context` +0.0156 (CI [+0.0057, +0.0257]),
`group` +0.0008, `intensity` +0.0004, `response` +0.0004, `imbalance`, `size`, `concentration`,
`new_wallets`, `coverage` ≈ 0, `market_context` −0.0018. Feature level: `rv_1d` +0.0108 (CI [+0.0049,
+0.0163]), `rv_7d` +0.0045, `rv_2h` +0.0015, `sib_max_abs_chg_2h` +0.0008, `sm_burst_6h` +0.0004. **No unit
carries `demonstrated_incremental_value` after BY at q = 0.10** (`price_context` p_BY = 0.66; everything else
1.0). SHAP/gain importances are descriptive only (GBM gain: `chg_1d`, `ltp_minus_mid`, `rv_7d`, `chg_1w`,
`market_age_h`, `dow`, …).

## 5. Test months (2026-08 to 2026-10, 128,935 rows, 503 surprise events, untouched until this pass)

Primary statistic: **excess precision over matched controls** at the 1 % budget (1,289 alerts): for every
alert, 5 non-alerted rows of the same UTC day, price band and 24 h-notional tercile, different market, seeded;
event-clustered bootstrap, one-sided p, Holm across the 8 arms. Hit = surprise departure within 6 h.

| Arm | Alertable | Alerts | Precision 6 h | Precision 2 h | Matched control rate | Excess (95 % CI) | p | Holm p | Recall of events | Lead to departure (median h) | Paper P&L 6 h / 24 h (USDC per 5 shares) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `en_logit_full` | 128,935 | 1,289 | **2.25 %** | 0.93 % | 0.43 % | **+1.82 pts (+0.61, +3.39)** | 0.001 | **0.008** | 14/503 (2.8 %) | 4.3 | −0.04 / −0.06 |
| `lgb_mono_full` | 128,935 | 1,289 | 1.78 % | 0.85 % | 0.68 % | +1.10 pts (+0.19, +2.33) | 0.007 | 0.049 | 18/503 (3.6 %) | 2.3 | −0.08 / +0.06 |
| `en_logit_live` | 128,935 | 1,289 | 0.93 % | 0.47 % | 0.67 % | +0.26 pts (−0.32, +0.86) | 0.19 | 1.0 | 11/503 (2.2 %) | 2.3 | −0.13 / −0.12 |
| `uf_imbalance_burst_v1` | 3,696 | 36 | 0 % | 0 % | 1.11 % | −1.1 pts | 1.0 | 1.0 | 0 | – | −0.13 / −0.11 |
| `uf_new_wallet_concentration_v1` | 3,649 | 36 | 0 % | 0 % | 0.56 % | −0.6 pts | 1.0 | 1.0 | 0 | – | −0.22 / −0.14 |
| `uf_large_trade_v1` | 11,647 | 116 | 0 % | 0 % | 0.52 % | −0.5 pts | 1.0 | 1.0 | 0 | – | −0.23 / −0.13 |
| `uf_convex_longshot_v1` | 887 | 8 | 0 % | 0 % | 0 % | 0 | 1.0 | 1.0 | 0 | – | −0.16 / −0.19 |
| `uf_pressure_no_response_v1` | 3,696 | 36 | 0 % | 0 % | 1.11 % | −1.1 pts | 1.0 | 1.0 | 0 | – | +0.01 / −0.05 |

Unconditional base rate 0.56 %: lift 4.0 (`en_logit_full`), 3.2 (`lgb_mono_full`), 1.7 (`en_logit_live`).
Budgets 0.5 % / 2 % give the same picture for `en_logit_full` (precision 2.0 % / 2.1 %, matched excess +1.5 /
+1.7 pts, p = 0.02 / 0.001). Hand rules at the **same absolute alert count** (1,289 alerts = 11-100 % of their
alertable rows): precision 0.16-0.79 %, matched excess −0.3 to +0.5 pts, no p below 0.08. By category at 1 %:
`en_logit_full` sports 2.8 % on 252 alerts, non-sports 2.1 % on 1,037; `lgb_mono_full` sports 7.1 % on 99,
non-sports 1.3 % on 1,190 (category scope remains a user decision; the detector is category-agnostic).

**Placebo (the decisive check).** The elastic net refit on *shuffled* labels of the same development sample
reached precision 2.4 % on the first draw: any ranking that favours extreme feature values picks active,
volatile markets, where sharp moves are commoner (base rate by `rv_7d` quintile 0.14 % → 1.15 %; 62 % of eligible
rows have no trade in the prior 24 h). This is why the raw lift over the base rate is not the primary statistic.
Against matched controls, 100 shuffled-label refits give an excess with median −0.02 pts, IQR [−0.33, +0.31],
max +1.57 pts; the real `en_logit_full` excess (+1.82) ranks first of 100 (**p_rank = 0.010**; on raw precision
0.020). `lgb_mono_full`: p_rank 0.020 (placebo max +1.75). `en_logit_live`: p_rank 0.14 on 20 draws, not
distinguishable from placebo.

**Economics.** Direction = sign of the 1 h imbalance (the label is undirected). Paper round trips at the
assumed 0.02 spread and `max_if_unknown` taker fees are negative or indistinguishable from zero for every
arm (`en_logit_full` 6 h: −0.04 USDC per 5 shares, 95 % CI [−0.17, +0.14], 63 episodes); moves of ≥ 0.15 in the
flow's direction follow 4 % (`en_logit_full`) to 14 % (`lgb_mono_full`) of alerts. **No economic value.**

## 6. Case-catalogue recall (held out; reporting-conditioned, no precision)

Same feature code on the 15 catalogue markets with data (`case_studies/`, prices + full taker trades over
[news − 14 d, news + 1 d]; true first-trade times from the case caches for the top wallets; Nobel 2026 has no grid
rows) and on Maduro `916440` (in-sample months, reported separately). Statistic: the maximum score in
[news − 72 h, news) as a percentile of the test-month score distribution, and whether it clears the 1 % budget
threshold.

| Case market | `en_logit_full` pct | clears 1 % | `lgb_mono_full` pct | clears 1 % (lead h) |
|---|---|---|---|---|
| Axiom 1419011 | 0.96 | no | 0.96 | no |
| Year in Search 635230 / 635246 | 0.91 / 0.88 | no | 0.97 / 0.92 | no |
| Israel strikes 532742 / 551651 | 0.91 / 0.16 (1 row) | no | **0.997** / 0.30 | **yes (54 h)** / no |
| Khamenei 916732 | 0.76 | no | 0.74 | no |
| Nobel 2025 560868 (7 rows) | 0.67 | no | 0.86 | no |
| OpenAI 822860 / 897817 | 0.88 / 0.36 | no | **0.994** / 0.99 | **yes (58 h)** / no |
| Pope 525015 (5 rows) | 0.62 | no | 0.81 | no |
| Taylor Swift 516906 | 0.75 | no | 0.72 | no |
| Ceasefire 1569627 / 1706788 | 0.88 / 0.91 | no | 0.80 / 0.90 | no |
| Feb strikes 1198423 / 1198479 | 0.84 / 0.82 | no | 0.88 / 0.88 | no |
| **Maduro 916440 (in-sample months)** | 0.74 | no | 0.72 | no |

Reading: the learned detectors rank most case markets in the top 5-25 % of the test-month distribution in the
72 h before the news, but **no case clears the 1 % budget under `en_logit_full`**, and the GBM clears it on two
markets 54-58 h early (the OpenAI "by Dec 13" market was already priced ≥ 0.9, a public expectation). The
reported last-hours flow is not what these detectors key on; their value sits in the price path. Maduro does
not clear the budget either. The verbatim selection-bias caveat of `UNUSUAL_FLOW_PROGRAMME.md` §6 applies.

## 7. Verdict and freeze

- `en_logit_full` beats the base rate, matched controls (Holm p = 0.008 on the primary statistic), every hand
  rule at both the programme budget and the same alert count, and ranks first among 100 shuffled-label
  placebos. `lgb_mono_full` is similar but weaker after Holm (0.049) and is not expressible as a rule spec.
- The value is **not** unusual flow: the flow, wallet and size families carry no incremental out-of-sample value
  (ΔLL ≈ 0; nothing demonstrated after BY). The detector finds "volatile week, quiet day, young market, weekday"
  configurations. The user's hypothesis that pre-move *flow* conditions distinguish surprise moves is not
  supported on this sample; the live-computable flow-only arm is indistinguishable from placebo.
- **Frozen:** `sm_learned_v1` = the `en_logit_full` weights as a declarative `RuleSpec` (20 terms, centre/scale
  numbers written into the spec, cap 4, direction = sign of `sm_imb_1h`), sha256
  `ee7ea5f18e71b9ef6c4edad845c04d3f6aea596197098887c5bb787cdc77f7f6`, index
  `detector_specs/FROZEN_SURPRISE.json` (separate from the closed unusual-flow set of five; `freeze_rules` now
  refuses a rule id present in any index). The spec reproduces the model's logit up to the intercept (tested).
  Known quirk: the `sm_abs_imb_1h` term has scale 2·10⁻¹⁴ (a MAD at floating-point noise around the median
  |imbalance| = 1), so it acts as a −0.05 penalty on mixed flow; the standardiser now guards against this, and
  v1 is kept exactly as evaluated.
- **Deployed:** `live_trade_monitor` (`live-trade-monitor-v2`) loads `FROZEN_SURPRISE.json` when present, computes
  the `sm_*` windows from the same 500-trade page, the price context from one CLOB `prices-history` request per
  enriched market (8 days, 10-min fidelity, cached 5 min; at most 50 per 5-min cycle), fee/decision one-hots from
  Gamma, and scores `sm_learned_v1` through the same causal trailing-99th-percentile budget as the five flow
  rules, writing alerts and matched controls to `alerts.jsonl` before any outcome. Live deviations (recorded in
  the module docstring): Gamma mid instead of the series as-of price; sibling/ladder and new-wallet terms are NaN
  (contribute 0); 24 h windows NaN when the page does not reach back. Restarted with
  `launchctl kickstart -k gui/$(id -u)/com.arepo.live-trade-monitor`. This is a **prospective, unregistered**
  collection (`evidence_role: prospective_unregistered`); a registration (programme §7) is the next step if the
  live alert stream accumulates ≥ 30 episodes with controls.

## 8. Budget and caveats

- Trials: 1 label spec, 3 × 8 arm evaluations (same arms; runs 2 and 3 only added the matched-control and
  placebo statistics), 1 placebo extension, 1 freeze = 27 `surprise_*` lines. BY denominator for the ranking:
  106 + 114 prior = 220. Revision budget for this data window: 0 of 3 feature-set revisions used.
- Small positive sample (362 development positives, 240 test); 503 test events of which 240 have an eligible row
  immediately before departure; recall is 3-4 % at 1 %.
- Labels depend on `prices-history` semantics (mid-like, unverified) and on Gamma end dates as listed now.
- Wallet "newness" is in-sample first-seen, not true age; wallets beyond the trade-fetch cap are invisible
  (41 markets truncated at 5,000 trades).
- Test months overlap the judgement half of the unusual-flow programme; the hand rules were frozen before either,
  so the comparison is fair but not independent of that earlier evaluation.
- Sports are included (509 of the 1,411 pre-cut surprises); results by category are reported, the scope decision is
  the user's.

## 9. Independent replication on `h3_power`: protocol (pre-declared 2026-10-13, before any h3 outcome)

Data: `data-dumps/research_lab/history/h3_power` (10,000 markets disjoint from `h1_first` and `h2_main`,
365-day lookback, 3x topic oversampling recorded as `sample_weight` = 1 / inclusion probability, 2.02M trades,
true first-trade table `new_wallets/first_trade_merged.jsonl` for wallets with ≥ $500 prints). Nothing in h3
was read before this section was committed except the sample and manifest metadata.

1. **Labels:** `surprise-labels-v1` unchanged (sha `d9cf42f7…`), same build code (`surprise_moves.build_dataset`),
   same exclusions (Maduro/Venezuela and catalogue condition ids), game-start cut from a Gamma metadata pull.
2. **Rule under test:** FROZEN `sm_learned_v1` (sha `ee7ea5f18e71b9ef6c4edad845c04d3f6aea596197098887c5bb787cdc77f7f6`),
   scored through `detector_eval.score_rule`; **no refit, no re-centring**. The five frozen hand rules are scored
   beside it as baselines (history mapping, as in §5).
3. **Evaluation rows:** eligible rows (`traded_before_t == 1`, mid in [0.02, 0.98]). **Primary set:** rows with
   `t ≥ 2026-08-01` (disjoint markets *and* months after the development window). **Secondary set:** all h3 rows
   (disjoint markets, months overlapping the development window). Budgets 0.5 / 1 / 2 % of alertable rows;
   the 1 % budget is primary.
4. **Statistics** (as §5): precision of a surprise departure within 6 h (and 2 h), unconditional base rate and
   lift, matched-control excess (UTC day | price band | 24 h-notional tercile | different market, k = 5, seeded,
   event-clustered bootstrap, one-sided p), recall of surprise events, lead time, paper P&L. Holm across the six
   rules at the 1 % budget on the matched excess. Every statistic is reported **unweighted and sample-weighted**
   (row weight = the market's `sample_weight`; weighted precision, base rate and weighted mean of the per-alert
   excess). Placebo: the 100 shuffled-label elastic-net refits of §5 (development sample of h2, same C) scored
   on the h3 rows; the frozen rule's matched excess is ranked among them.
5. **By topic:** the same table per `topic` (sports, crypto, other, corporate, politics, weather, awards,
   geopolitics, macro, mentions) and per decision-asymmetry class (A/B/C/unclassified), descriptive, no Holm.
6. **Exploratory, clearly labelled, not a rule change:** refit `en_logit_full` and the family ablation on the
   combined h2 + h3 development months (train ≤ 2026-05, validation 2026-06/07; h3 wallet "newness" uses the
   true first-trade table merged with the in-sample index) and report which families and features carry
   incremental value, in particular flow and wallet ones. **This never alters `sm_learned_v1` or the live
   monitor.** Any new rule would be a new rule id, a new budget line and a new live registration.
7. Budget: one `surprise_detector` line per rule evaluated on h3 (6, primary set) plus one per rule on the
   secondary set (6), one placebo line, one line for the exploratory refit; cumulative count carried in each line.
   Heavy lock held for the build and the fits.
