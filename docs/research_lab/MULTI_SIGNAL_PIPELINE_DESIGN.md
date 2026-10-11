# AREPO multi-signal forecasting pipeline: design

- **Status:** DESIGN, 2026-10-11. It is not a registration, and no outcome has been computed under it.
- **Scope:** research tooling only. It makes no edge, calibration, profitability or trading claim.
- **Relation to the ledger:** E001–E007, C1 and L1 keep their outcomes and registrations unchanged. This pipeline does not refit, pool or reinterpret them.
  - The frozen E002 reversal is used only as a reference arm.
  - E004–E007 continue on their own rules.
- **Next gate:** an accepting `science-reviewer` pass on this design. Then Tasks 1–2 (section 7).

## 0. Why change approach

The E-series tests one hypothesis at a time against a thin baseline. What it has found so far:
- the E002 reversal (confirmed but weak);
- E003 null;
- flow screens: only F1, which became E007;
- L1 null.

Each new hypothesis costs about one day of prospective collection and one registration. It also adds to the winner's-curse problem, as the E007 disclosures show.

The alternative tests **one model-level question**: does a model using all available point-in-time information beat the price+momentum baseline, out of sample and prospectively, on a proper score, and does that gain survive costs? The design has four parts:
- **Signals are inputs, not hypotheses.**
- **Attribution is descriptive:** SHAP, ablations.
- **Confirmation spends the alpha once:** section 5.

## 1. Targets and horizons

The unit is a (market, origin snapshot *i*, target snapshot *j*) pair:
- binary markets, outcome-0 price;
- E001 eligibility (`panel.eligibility_mask`);
- *j* = the next **complete** universe snapshot, with a gap of 1.5–3h;
- target-unavailable pairs are counted, never imputed.

The data are 10 complete loop snapshots, each about 240–277k rows (about 40k E001-eligible), plus 6 dev captures with irregular gaps.

| ID | Target | Horizon | Needs | Role |
|---|---|---|---|---|
| **T1** | 3-class material direction of `mid` (down / flat / up). `|dmid| <= δ` is flat. Proposed δ = max(0.01, 2·tick) (see note 1) | next snapshot, ~2h | consecutive complete snapshots with a gap ≤ 3h. Tick size needs the sidecar (Task 1) or a book sweep. | **Primary** (MC1). Scored by log loss and Brier |
| T2 | continuous `dmid` | ~2h | same as T1 | Secondary. Comparable with E001–E007 (R2_oos against no-change and against frozen E002) |
| T1-24 | T1 at ~24h (snapshot 12 periods later) | 24h | 12 consecutive snapshots. Overlapping labels are purged by availability. | Descriptive in development only |
| **T5** | resolution: outcome 0 pays 1 | close within 1–7 days of origin | resolution labels fetched after close (C1 rules: `umaResolutionStatus`, `outcomePrices`). The label is available at resolution time. | Later confirmation **MC2**. Baseline: the market price, which C1 found close to calibrated at 1d |

1. **δ** is fixed in development, with a single pre-declared sensitivity (δ = spread/2). It is frozen before confirmation. The flat class is kept; about 62% of active pairs have dmid = 0.
2. **The origin price must be the latest price known at the origin cutoff, and the same price for every model.** A book sweep runs about 6 minutes after the snapshot it pairs with. If the full model reads the sweep's mid while the baseline reads the older Gamma mid, the full model "wins" by seeing part of the path, not by forecasting.
   - Rule: the origin time `t0 = max(row receipt, sweep receipt)` for book-joined pairs.
   - For those pairs, `mid_0` is the sweep mid in **every** arm, and the target is measured from `mid_0`.
   - A target row must have its receipt after `t0`; a row received earlier is target-unavailable.
3. **T3/T4** (first passage, path) need dense quote paths that we do not have. They are out of scope.

## 2. Feature library

The general rules:
- Every feature reads origin-side data only. `features.register` refuses label columns.
- Features are versioned, with missing value → NaN plus a flag. A missing value is never silently 0, except in tree inputs, which handle NaN natively.
- Source clock and receipt clock are recorded.
- Families are declared now. They are the units of ablation and of SHAP aggregation.

### Tier (a): available now, or from pages we already fetch

| # | Feature (family) | Source / clock | Notes |
|---|---|---|---|
| a1 | `logit(mid)`, `|mid−0.5|` (price) | snapshot row receipt | in the baseline |
| a2 | `chg_1h`, `chg_1d`, `chg_1w` plus missing flags (momentum) | Gamma-computed; the update latency is unknown | in the baseline. The `chg_1h` reversal is the strongest known predictor (E002) |
| a3 | **own Δmid since the previous complete snapshot**, and its age (momentum) | our own receipt clocks, so latency is exact | Fixes the unknown Gamma latency. Needs snapshot *i−1* within 3h, otherwise missing |
| a4 | own realised volatility of mid over the last k ≤ 6 snapshots (volatility) | own clocks | missing for new markets; the count of prior observations is included |
| a5 | `spread`, `spread/tick`, `ltp − mid` (liquidity) | row | B3 context. Gave +0.013 R2 in M1 development (not a finding) |
| a6 | `log1p(liquidity)`, `log1p(volume24hr)`, turnover `vol24h/liq` (liquidity) | row | |
| a7 | `log hours to endDate`, end-unknown flag (time) | row | |
| a8 | quote staleness: `t_i − updated_at` (quality) | row | it may also proxy for activity |
| a9 | neg-risk member flag, group mid-sum excess (`nr_excess`), sibling count (structure) | same scan | L3/E005 are small or unsupported. Kept as context, not as hypotheses |
| a10 | liquidity-weighted sibling `chg_1h` (L1) (structure) | same scan; sibling receipt may be minutes later | it still precedes the target. The L1 screen was underpowered, not negative |
| a11 | book: top imbalance (F08), microprice displacement (F09), depth within 1c/5c per side, 5c depth imbalance, level counts, book–Gamma mid gap, `book_timestamp` age (book) | `book_sweep` batch receipt (all eligible tokens, 2 sweeps per pass) | E003 found the imbalance inconclusive on its own. Here it is an input. Section 1 note 2 applies |
| a12 | **sidecar metadata** (Task 1) from the same Gamma pages (metadata): `feeType` → `fee_category` (the D120 map, imported, never copied), `feesEnabled`/`takerBaseFee`, `orderPriceMinTickSize`, `orderMinSize`, `createdAt` (market age, F41), `startDate`, `competitive`, `rewardsMinSize`/`rewardsMaxSpread`/`clobRewards` (F42), `acceptingOrders`, `umaResolutionStatuses` (F56 early state), lifetime `volumeNum`; event `openInterest`, `commentCount`, `volume`, `liquidity`, `createdAt`, `negRiskAugmented` | page receipt | **Prospective only.** The research-lab collector does not keep raw bodies, so history before Task 1 cannot be recovered. That gap stays missing. The 6 `fs2_capture_*` dev captures keep raw pages and may be backfilled for development only |
| a13 | trade-flow: `signed_share` (E007), `n_trades_1h`, `notional_1h`, max trade / liquidity (F01), time since last trade (flow) | `trade_sample` (2,000-market probability sample of the active frame) | **Not in the primary universe model**: 95% of rows would be missing by design. It feeds a secondary active-frame model weighted by 1/π |

`category` (`fee_category`, a12) is a **model input and a pooling group, never a hard-coded filter**. The population is set by a single config parameter:

    category_policy = {"mode": "all" | "include" | "exclude", "categories": [...], "map_version": "fs2-fee-category-map-v1"}

The default is `all`. The policy is recorded in every run, fold manifest and registration. Per-category results are descriptive. Sports is the user's later decision.

### Tier (b): free external sources worth adding

Each source must need no key, no account and no fee. Each is admitted only after a short source-admission note, and **collected live**: a value is used only if it was received before `t0`. Backfilled history is development-only and is labelled as such.

| Source (register code) | Feature | Point-in-time availability | Collection cost | Leakage risk |
|---|---|---|---|---|
| Coinbase Exchange public REST/WS, or Polymarket RTDS (XCOIN, PRTDS) | F14/F44: spot vs strike distance for crypto threshold markets; 5m/1h spot return; model-implied digital probability minus mid | live ticks carry exchange timestamps; candles are immutable afterwards | **low** for the feed. **Medium** for parsing strike and expiry from the question text (versioned parser; unmatched → missing) | low if fetched at `t0`. Medium if a candle straddles `t0`: use only candles that closed before `t0` |
| Deribit public API (XDERIBIT) | BTC/ETH implied vol at matching expiry → digital probability | live only. Historical depth is not assumed | low to medium | low live. Do not use historical IV snapshots for confirmation |
| Kalshi public market-data REST (XKALSHI) | F36: rule-matched cross-venue mid gap | live request time; the rules' history must be stored | **high**: rule equivalence is manual and versioned | low live. High if the matching uses resolved outcomes |
| NWS `api.weather.gov` (XNOAA; User-Agent, no key) | F47: forecast innovation for weather threshold markets | issue time is in the payload. The archive is not kept, so collection must be prospective | medium to high (location and threshold matching) | medium: observations can arrive up to 20 minutes late. Use issue time and receipt time |
| GDELT 2.0 event/GKG 15-minute files (XNEWS; free, no key) | F16 news acceleration: entity mention counts over the last 1h/24h against the trailing baseline | file publish time (15 minutes) | medium: entity mapping from the question text through a frozen keyword map | medium: use the file *publish* time, never the event date |
| Wikimedia pageviews (XWIKI) | F50 abnormal attention | daily, published with a lag | low feed cost; high entity-mapping cost | **high at 2h**: use only fully published days before `t0`. Suits T1-24/T5 only |
| SEC EDGAR (XSEC; User-Agent) / BLS public v1 (XBLS; no key, 25 queries per day) | F48/F45 filing and release surprise | acceptance or release timestamps | medium | low. Few markets are affected, so expect low power |

**Excluded** under the no-paid/no-key rule:
- FRED/ALFRED (key);
- X/Truth/Reddit (key, paid);
- Betfair (account);
- CME (paid);
- Google Trends (unofficial, rescaled, look-ahead).

**Recommended order:** crypto spot and IV first. They have the cheapest matching and the cleanest clocks. Then GDELT, then Kalshi.

### Tier (c): later

These are deferred until tiers (a) and (b) leave a stable residual:
- wallet history and skill (F03–F06, F33–F35; Polygon RPC is heavy);
- WebSocket book deltas (F10, F23 OFI, F24 resiliency);
- UMA/CTF dispute logs (F56 in full);
- sports live state (F58; also conditional on the category decision);
- comment stance (F59);
- text novelty / LLM features (F17, F51, F54; risk of historical knowledge leakage);
- a full trade-flow census of the active frame.

## 3. Models

The set is small, and fixed now. Every arm sees the same origin IDs, folds, targets and outcome observations.

| Arm | Model | Features | Notes |
|---|---|---|---|
| **M0 baseline** | multinomial logistic (T1), refitted per fold | a1 + a2 only (price + momentum) | The strong baseline. **The frozen E002 model** (`dmid_hat = −0.3316·chg_1h`) is a fixed reference arm on T2 only. It is not probabilistic, so it cannot be the T1 baseline |
| M1 regularised GLM | elastic-net multinomial logistic; natural-spline expansion of `logit(mid)`, `chg_1h`, `log hours`; a small pre-declared interaction set (`chg_1h` × {spread, log liq, log hours}) | tier (a) without a13 | Linear attribution is exact |
| **M2 gradient boosting** | LightGBM multiclass | tier (a) without a13 | The principal nonlinear challenger. Fixed search budget (section 4). Native NaN. TreeSHAP built in |
| M3 Bayesian hierarchical | multinomial logit. Random intercepts by `fee_category` and by event. `chg_1h` and spread slopes partially pooled by category. Priors from the research package (main effects N(0, 0.5), group SD half-N(0, 0.5)) | a subset of tier (a) (about 12 standardised features) | NumPyro. NUTS on a stratified subsample of ≤50k rows, or SVI on all rows. R-hat < 1.01, no divergences, prior-predictive check. New events get the population prior |
| E50 (optional) | 0.5·p(M2) + 0.5·p(M3) | — | no fitted weights, so no extra tuning. Only if M3 is ready in time |

- **Calibration:** temperature scaling, fitted on the inner validation block of each training fold.
- **Selection:** in development, one arm is chosen as **F\*** (expected: M2 or E50) by mean out-of-fold log loss, calibration and fold stability. Only F\* goes to confirmation. Every development fit is logged to `trials.jsonl` with its config, so the search size is on the record.
- **Libraries:** `backend/.venv` currently has only numpy, pandas and pyarrow. sklearn, lightgbm, shap, statsmodels, scipy, pymc, numpyro/jax and polars are all **missing**. Task 3 adds an optional extra `research-ml`:
  - `scikit-learn`, `lightgbm`, `numpyro` + `jax[cpu]`;
  - free, about 0.5–1 GB of disk, with 13 GiB free.
  - The `shap` package is not needed. LightGBM's `predict(..., pred_contrib=True)` gives exact TreeSHAP, and linear SHAP is closed form.

## 4. Validation (development)

- **Folds:**
  - expanding-window walk-forward over snapshot periods;
  - test blocks of 4 consecutive periods (about 8h);
  - the first test block starts after at least 12 training periods.
- **Purge and embargo:**
  - A training pair is kept only if its label time `t_j` ≤ (the earliest test `t0`) − **embargo** (1 period, about 2h). This is the existing `evaluate.purged_train_mask` rule plus a gap.
  - T1-24 and T5 purge by actual label availability (24h target receipt; resolution time).
- **Nested tuning:** every tuning step happens inside a training fold, on an inner time split. The inner split is the last 25% of training periods, with its own purge. This covers the λ / elastic-net mix, LightGBM's 20-config random search plus early stopping, temperature, and spline knots. The test block is never used for tuning, and the search budget is fixed.
- **Fold manifest:**
  - written and hashed before any fit;
  - it records period IDs, cutoffs, embargo, `category_policy`, feature versions and the code sha.
- **Primary inference: event-clustered paired bootstrap.**
  - Loss difference `ΔLL = LL(M0) − LL(arm)` per row. 1,000 resamples, seed 116, shared across arms. The cluster is the event; a market with no event uses its market ID, and those are counted.
  - Generalises `compare.paired_bootstrap` from SSE to any per-row loss.
  - Time-block check: `power.per_period_test` (t-test and sign test across test periods).
  - The secondary deployment question uses event-held-out folds. It is descriptive.
- **Metrics:**
  - log loss (primary); 3-class Brier;
  - calibration intercept/slope per class (up vs rest, down vs rest);
  - T2 R2_oos for comparison with the E-series;
  - effective sample: rows, markets, events and periods, plus target-unavailable counts.
- **SHAP:**
  - Computed **only on out-of-fold test rows**, each with the model fitted on that fold.
  - M2: native TreeSHAP in log-odds, per class. M1: β·(x − training mean).
  - Reported for two margins: "up minus down" (direction) and "move vs flat" (activity).
  - Reported as:
    - mean |SHAP| per feature and **per family**. Family values are SHAP sums, which is valid because SHAP is additive;
    - fold-to-fold rank stability (Spearman);
    - dependence plots for the top 5 features;
    - event-clustered CIs on mean |SHAP|.
  - Correlated features share credit arbitrarily, so families are the unit of interpretation.
  - **SHAP is exploratory. It is never evidence of edge or of a mechanism.**
- **Ablations:** pre-declared, at most 6 drops. Each is the F\* candidate with one family removed:
  1. momentum/own-history (a2–a4);
  2. book (a11);
  3. structure (a9–a10);
  4. metadata (a12);
  5. liquidity/time/quality (a5–a8);
  6. external (tier b, when present).

  They are reported with event-clustered CIs and are descriptive. No family is promoted to a hypothesis from these results without a new registration.
- **Placebos** (development, required before freeze):
  - labels shuffled within period × event blocks (ΔLL should be about 0);
  - every feature shifted to the *target* snapshot (the leakage alarm must fire);
  - the quote-age-only model.

## 5. Prospective confirmation MC1 (one registration)

- **Registration:**
  - one ledger entry, written and committed before any confirmation snapshot exists;
  - an accepting `science-reviewer` pass.
  - Frozen at registration:
    - the F\* artifact (sha256);
    - M0 coefficients, fitted on all development periods;
    - δ, the feature versions, `category_policy`, the fee model and the economic rule τ.
  - **No refitting** during confirmation.
  - Forecasts from both arms are logged per snapshot before the target exists (the `forecast.predict` pattern), and scoring asserts equality with the log.
- **Hypotheses (Holm across exactly two):**
  - **H1 (predictive):**
    - mean ΔLL = LL(M0) − LL(F\*) > 0 on T1, in relative units (ΔLL / LL(M0));
    - event-clustered bootstrap CI.
  - **H2 (economic):** the cost-aware rule (below) has net mean P&L per trade > 0, and beats the same rule driven by M0. Event-clustered CI.
- **Secondary (descriptive):**
  - Brier;
  - calibration slope;
  - T2 R2_oos against frozen E002;
  - per-category rows;
  - E50 if registered as secondary.
- **Verdicts:**
  - **Supported (exploratory, prospective), predictive** requires all three:
    - H1 rejects at its Holm level with ΔLL > 0;
    - positive in ≥ 17 of 24 qualifying periods (sign test p ≈ 0.032; if the period count changes, the threshold is the smallest count with one-sided p < 0.05);
    - F\* calibration slope CI overlaps 1, or is at least as close to 1 as M0's.
  - **Economically non-negative at stated costs:** H2 rejects with P&L > 0.
  - **Contradicted:** H1 rejects with ΔLL < 0.
  - **Inconclusive:** otherwise.
  - **Unavailable:** fewer than 24 qualifying periods by registration + 7 days.
- **Economic rule** (an improvement on E004's touch-to-touch, which ignored fees):
  - At `t0`, if P(up) − P(down) > τ, buy outcome 0 at the sweep `best_ask`. If it is below −τ, buy outcome 1 at `1 − best_bid`. τ is fixed in development.
  - Require touch size ≥ `orderMinSize`, a size of 1 share, and the sweep receipt before the decision.
  - Exit at the target snapshot touch (sell at `best_bid_j`, or the complement).
  - Subtract the taker fee on both legs, `feeRate·p·(1−p)` from the sidecar `feeType`/`takerBaseFee`. If the fee is unknown, use the highest rate in the frozen map.
  - Latency and queue position are not modelled, and stale Gamma exit quotes can flatter results. So even a pass is labelled "optimistic, not tradable".
- **MDE (`power.py` logic, unchanged):**
  - The ΔR2 algebra applies to any normalised paired loss: `c_k = K·d_k / LL_M0,total`, `SE = sd_c/√K`, `MDE = (z_{1−α/2} + z_power)·sd_c/√K`.
  - `sd_c` is measured on development out-of-fold ΔLL by `power.cluster_contrib_sd` (Task 8) and frozen in the registration.
  - Planning value until then: `sd_c ≈ 0.6`, the scale implied by L1's ΔR2 (MDE 0.013 at 22.8k events).
  - With Holm at m = 2, the first step has α = 0.025 two-sided and power 0.8 (z-sum 3.08):
    - K = 20k events → MDE ≈ 1.3% relative log loss;
    - K = 34k → 1.0%.
  - The research package's ≥1% relative-improvement gate therefore needs about 30–35k distinct events.
- **Stopping rule:**
  - Fixed sample: score **once**, when both of these hold:
    - ≥ 24 qualifying periods;
    - distinct events K ≥ K\* (K\* is computed from the frozen `sd_c` for MDE = 1%).
  - Cap: 36 periods or registration + 7 days.
  - If the cap is reached with K < K\*, score anyway and label the result "underpowered". It cannot be Supported unless the H1 CI still excludes 0.
  - Before scoring, only availability counts (periods, rows, events) may be viewed. No interim looks at the metric.
- **Qualifying period:**
  - source and target are complete snapshots, with a gap of 1.5–3h;
  - forecast logged before the target capture starts;
  - sidecar present;
  - book sweep receipt before the target starts.
  - Failed passes are logged as unavailable, never backfilled.

**MC2 (later, separate registration):** T5 resolution within 1–7 days.
- Hypothesis: F\*-T5 vs the price-only recalibrated logistic.
- It needs a resolution-label collector and weeks of accrual. C1 had 1,976 markets with only ±0.15 slope precision.

## 6. Data volume

- **Now:** 10 complete loop snapshots, with irregular gaps (a 3h+ gap around pass 6). That is about 8 usable 2h pairs, plus 6 dev captures (5–70h gaps; usable for T2 context only).
  - Book sweeps: 18. Trade samples: 7. Sidecar: none.
- **Development (sidecar-dependent features):** ≥ 36 periods with the sidecar present, which is **about 3 days** of uninterrupted 2-hourly passes after Task 1 is live.
  - This gives 12 training periods plus 6 test blocks of 4. A tier-(a)-without-a12 development run can start on existing data now, as a dry run of the machinery.
- **Distinct-event accrual:**
  - L1: 15 periods gave 22.8k event clusters. About 10k events appear in the first period, then roughly +900 per period.
  - So K = 20k needs about 12–15 periods, and K = 34k needs about 27 periods.
  - Repeated events across periods are a single cluster, so more rows do not mean more independent evidence.
- **Confirmation:** 24–36 qualifying periods, which is **2–3 days** at the 2h cadence (budget 4 days for failures, cap 7).
- **Total:** about **6–8 days** of continuous 2-hourly collection from Task 1 going live to an MC1 verdict.
  - MC1 can share snapshots with the E004–E007 confirmations: different registrations, no conflict. Development periods must end before MC1's registration commit.
- **Memory:** about 40k rows × ~70 float32 features × 60 periods ≈ 0.7 GB.
  - Build per-period Parquet and fit in one process.
  - **Never run alongside a collection pass or another multi-GB job.**

## 7. Implementation plan (Sonnet implementer; each task has tests and a review)

1. **Task 1 — Snapshot metadata sidecar** (time-critical, because the data is prospective only).
   - **Change:** `collector.collect` additionally writes `rows_ext.csv.gz` and `ext_manifest.json` from the **same** page bodies.
     - Fields: those listed under a12.
     - `fee_category` via `research_panel.pairing.fee_category`, imported.
     - Raw `feeType` is kept.
     - NaN when absent; never 0.
   - `rows.csv.gz`, `manifest.json`, the request sequence and the cursor and detour logic stay **byte-identical**, so E004–E007 are unaffected. The change is availability-only, and the ledger gets a disclosure note.
   - Optional: a read-only dev backfill from `fs2_capture_*` raw pages, labelled DEVELOPMENT.
   - **Tests:**
     - fixture pages → `rows.csv.gz` identical with the sidecar on and off;
     - sidecar columns parsed, including missing fields;
     - `fee_category` matches the D120 map;
     - an incomplete capture still writes a consistent partial sidecar;
     - no extra HTTP requests.
   - **Review:** `science-reviewer` confirms no effect on registered experiments before the loop picks it up.
2. **Task 2 — `research_lab/ml_panel.py`: multi-period panel, features and fold manifest.**
   - **Builds:**
     - T1/T2 pairs from consecutive complete snapshots, reusing `panel.build_pair` eligibility;
     - own-history features a3/a4 from snapshot *i−1…i−6*;
     - joins: sidecar, book sweep (section 1 note 2, origin cutoff), neg-risk/sibling (reusing `features_dev`/`leadlag_screen` code);
     - `category_policy` filter and recording;
     - label-time columns;
     - the hashed fold manifest (expanding window, 4-period blocks, 1-period embargo).
   - **Tests:**
     - no feature reads a *j* column (`features.register` guard);
     - a feature computed from *i+1* raises an error;
     - purge plus embargo removes exactly the overlapping pairs;
     - book-joined pairs use the sweep mid in every arm, and targets received before `t0` are unavailable;
     - `category_policy` include/exclude/all, recorded in the manifest;
     - deterministic manifest hash;
     - a3 is missing when *i−1* is more than 3h earlier.
3. **Task 3 — optional deps `research-ml`.**
   - scikit-learn, lightgbm, numpyro, jax[cpu], pinned. Library versions are recorded through `provenance.environment`.
   - **Test:** import smoke, skipped when the extra is absent.
4. **Task 4 — `ml_models.py` + `ml_compare.py`.**
   - M0/M1/M2, nested inner split, fixed search budget, temperature calibration.
   - Generic per-row-loss paired event-clustered bootstrap.
   - `power.cluster_contrib_sd` on ΔLL.
   - **Tests:**
     - synthetic data with a known signal is recovered;
     - a pure-noise feature gives ΔLL CI ∋ 0;
     - inner tuning never touches test rows (asserted by index);
     - log loss and Brier match hand-computed values.
5. **Task 5 — `bayes_hier.py` (M3).**
   - NumPyro model, prior-predictive check, diagnostics gate.
   - **Tests:** synthetic grouped data recovers the pooled effects, and an unseen group falls back to the prior.
6. **Task 6 — attribution report.**
   - Out-of-fold TreeSHAP and linear SHAP, family aggregation, stability, the 6 ablations, placebos.
   - **Tests:**
     - SHAP rows sum to the margin minus the expected value;
     - family sums are additive;
     - the shuffled-label placebo gives about 0.
7. **Task 7 — economic rule and fee model** (`ml_econ.py`).
   - **Tests:**
     - fee formula;
     - the complement-leg arithmetic;
     - touch-size and receipt-order guards;
     - unknown fee → maximum rate.
8. **Task 8 — development run** (a DEVELOPMENT ledger entry, pre-declared before the run).
   - All arms, SHAP, ablations, placebos.
   - Choose F\*; compute `sd_c`, K\* and τ.
   - Then a challenger review.
9. **Task 9 — MC1 registration, forecast logger and scorer.**
   - `science-reviewer` freeze, then sealed confirmation.
10. **Later:**
    - tier-(b) adapters, one at a time (crypto spot/IV first). Each gets its own admission note and new development data; none is added to a frozen F\*;
    - the resolution-label collector and MC2;
    - the active-frame flow model (a13).

## 8. Risks, and what not to claim

**Risks:**
- **Fresher-price leakage.** Book sweeps and sibling reads arrive after the row they join. Section 1 note 2 is mandatory.
- **Gamma field latency.** The update lag of `chg_*` and `updatedAt` is unknown, and "reversal" may be partly quote noise (D1: 51% of eligible markets never trade).
- **Garden of forking paths in development.** It is bounded by:
  - the fixed search budget;
  - pre-declared families and ablations;
  - trial logging;
  - one confirmatory model.

  The development-to-confirmation shrinkage is expected to be large (E002 kept about 2/3 of the development effect; E007 is expected to keep much less).
- **Time dependence.**
  - A few periods dominate.
  - Events recur across periods.
  - Common shocks hit every market at once.
  - Event clustering does not model correlation across events within a period, which is why the per-period sign rule exists.
- **Population drift.** Universe size fell from 277k to 240k over 15h. Category mix shifts (for example, sports by time of day).
- **Collector fragility.** Cloudflare cursor blocks cost passes. A missed pass breaks a3 and the gap rule for that period.
- **Memory and disk.** Training must not overlap collection.
- **Economic check optimism.** Stale exit quotes, no latency, 1-share size, mirrored-order uncertainty.

**Never claim:**
- edge, alpha, profitability or tradability from development fits, SHAP, ablations or a predictive-only pass;
- that a feature "causes" or "drives" prices because of its SHAP value;
- calibration of AREPO forecasts beyond the measured confirmation sample;
- that per-category rows or E50 are confirmed;
- that a backfilled or retrospective feature (tier b history, dev-capture sidecar) is point-in-time evidence;
- any change to the E001–E007, C1 or L1 verdicts.

Missing data stays missing. Thresholds, δ, τ and the gates are not changed after freeze to obtain a pass.
