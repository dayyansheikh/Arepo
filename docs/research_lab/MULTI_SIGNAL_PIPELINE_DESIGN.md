# AREPO multi-signal forecasting pipeline: design

- **Status:** DESIGN, 2026-10-11. It is not a registration, and no outcome has been computed under it.
- **Scope:** research tooling only. It makes no edge, calibration, profitability or trading claim.
- **Relation to the ledger:** E001–E007, C1 and L1 keep their outcomes and registrations unchanged. This pipeline does not refit, pool or reinterpret them.
  - The frozen E002 reversal is used only as a reference arm.
  - E004–E007 continue on their own rules.
- **Review:** the `science-reviewer` accepted it with 7 changes (2026-10-11). Revision 2 adopts all of them:
  1. one price source at both ends;
  2. δ frozen now;
  3. power numbers marked non-binding;
  4. dependence-group clustering;
  5. economic rule fixed;
  6. search accounting;
  7. development calendar.
- **Next gate:** the pre-implementation checks (section 7), then Tasks 1–2.

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
| **T1** | 3-class material direction of `mid` (down / flat / up). `|dmid| <= δ` is flat. **δ = 0.005 (frozen; see note 1)**. `dmid` is the **Gamma** mid at *j* minus the **Gamma** mid at *i* (note 2) | next snapshot, ~2h | consecutive complete snapshots with a gap ≤ 3h | **Primary** (MC1). Scored by log loss and Brier |
| T2 | continuous `dmid` | ~2h | same as T1 | Secondary. Comparable with E001–E007 (R2_oos against no-change and against frozen E002) |
| T1-24 | T1 at ~24h (snapshot 12 periods later) | 24h | 12 consecutive snapshots. Overlapping labels are purged by availability. | Descriptive in development only |
| **T5** | resolution: outcome 0 pays 1 | close within 1–7 days of origin | resolution labels fetched after close (C1 rules: `umaResolutionStatus`, `outcomePrices`). The label is available at resolution time. | Later confirmation **MC2**. Baseline: the market price, which C1 found close to calibrated at 1d |

1. **δ is frozen in this document, before any development fit.**
   - Primary: δ = **0.005**, with flat meaning `|dmid| ≤ 0.005`.
   - The single sensitivity: δ = **0.01**.
   - Both are absolute and tick-independent. So δ is defined identically when tick size is missing, which covers all pre-sidecar data. Tick enters only as a feature (with a missing flag).
   - **Basis:** class balance only, re-measured on the chosen source (Gamma mid at both ends) before any fit, on two loop pairs (06:19→08:18Z and 02:23→04:20Z; about 46k matched rows each; approximate E001 eligibility without the endDate term):
     - dmid = 0 in 59.8% and 62.4% of rows;
     - flat share at δ = 0.005: 84.3% and 86.3%; at δ = 0.01: 90.8% and 92.1%;
     - median spread 0.03.
   - δ = 0.005 keeps about 7% in each moving class. δ = 0.01 leaves about 4%.
   - No model was fitted and no feature was looked at in choosing δ. This choice is logged in `trials.jsonl` as the first Task 8 entry.
2. **One price source at both ends.** `mid_i` and `mid_j` are both the Gamma snapshot mid (`(bestBid + bestAsk)/2` of the row) in every arm and every target. Book sweeps feed **features only**.
   - **Why:** a sweep runs about 7–8 minutes after its snapshot starts. If the origin used the sweep mid and the target used the Gamma mid, `dmid` would contain the sweep-minus-Gamma gap. A book feature would then partly predict that measurement gap.
   - **Book features** are computed within the sweep, relative to the sweep's own mid. Examples: imbalance, depth, microprice minus *sweep* mid.
   - **The sweep–Gamma mid gap is excluded from the confirmatory model.** It is used only in the gap-only placebo arm (section 4).
   - **Timing:** the origin cutoff is `t0 = max(row receipt, sweep receipt)` whenever sweep features are used. A target row received before `t0` is target-unavailable.
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
| a11 | book: top imbalance (F08), microprice displacement (F09), depth within 1c/5c per side, 5c depth imbalance, level counts, `book_timestamp` age (book). The microprice is relative to the **sweep** mid. **No** sweep–Gamma gap (placebo only) | `book_sweep` batch receipt. The latest sweep returned 43,734 of 43,734 eligible tokens; 2 sweeps per pass | E003 found the imbalance inconclusive on its own. Here it is an input. Section 1 note 2 applies |
| a12 | **sidecar metadata** (Task 1) from the same Gamma pages (metadata): `feeType` → `fee_category` (the D120 map, imported, never copied), `feesEnabled`/`takerBaseFee`, `orderPriceMinTickSize`, `orderMinSize`, `createdAt` (market age, F41), `startDate`, `competitive`, `rewardsMinSize`/`rewardsMaxSpread`/`clobRewards` (F42), `acceptingOrders`, `umaResolutionStatuses` (eligibility filter only; see the timing rules below), lifetime `volumeNum`; event `openInterest`, `commentCount`, `volume`, `liquidity`, `createdAt`, `negRiskAugmented` | page receipt | **Prospective only.** The research-lab collector does not keep raw bodies, so history before Task 1 cannot be recovered. That gap stays missing. The 6 `fs2_capture_*` dev captures keep raw pages and may be backfilled for development only |
| a13 | trade-flow: `signed_share` (E007), `n_trades_1h`, `notional_1h`, max trade / liquidity (F01), time since last trade (flow) | `trade_sample` (2,000-market probability sample of the active frame) | **Not in the primary universe model**: 95% of rows would be missing by design. It feeds a secondary active-frame model weighted by 1/π |

`category` (`fee_category`, a12) is a **model input and a pooling group, never a hard-coded filter**. The population is set by a single config parameter:

    category_policy = {"mode": "all" | "include" | "exclude", "categories": [...], "map_version": "fs2-fee-category-map-v1"}

The default is `all`. The policy is recorded in every run, fold manifest and registration. Per-category results are descriptive. Sports is the user's later decision.

**Feature-timing rules for the sidecar fields (a12), fixed now:**
- **Cumulative fields** (`volumeNum`, event `volume`, `commentCount`, `openInterest`):
  - used only as the origin-row level, or as differences from *i−1* to *i*;
  - **never** read from snapshot *j*, and never differenced from *i* to *j*.
- **`umaResolutionStatuses`:**
  - **T1:** an origin eligibility filter, not a feature. A market is excluded if its origin row shows any resolution proposal (any non-empty status list). Exclusions are counted.
  - **MC2/T5:** the same origin exclusion is pre-declared. A proposal largely reveals the outcome, so including it would make T5 trivial. The status is kept for descriptive splits only.
- **Possibly stale fields** (`competitive`, `rewardsMinSize`, `rewardsMaxSpread`, `clobRewards`):
  - treated as Gamma-computed, with opaque update timing, like `chg_*`;
  - used only as origin-row values, with no claim about when they changed.

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
- **Selection:** in development, one arm is chosen as **F\*** (expected: M2 or E50) by mean out-of-fold log loss, calibration and fold stability. Only F\* goes to confirmation.
- **Search accounting.** Every development fit and decision is one line in `trials.jsonl`, including:
  - each feature-set version (a revision means added, removed or redefined features);
  - δ (already frozen);
  - τ and τ_M0;
  - the hyperparameter search results;
  - the arm choice.

  Caps:
  - at most **3 feature-set revisions** after the first development run;
  - **one** arm selection;
  - **one** τ selection per arm.

  When a cap is reached, the current version is final. The registration reports the total number of trial lines.
- **Full-development refit of F\* (before the sha256 freeze):**
  - Hyperparameters are the most common per-fold selected config (ties go to the more regularised one).
  - LightGBM rounds are the median per-fold early-stopping round.
  - F\* is refitted once on **all** development periods with these fixed. Nothing is tuned in this step.
  - The temperature is fitted on the pooled out-of-fold predictions of the last 2 development test blocks.
  - M0 is refitted on all development periods, with no tuning.
  - The sha256 of both artifacts, the config and the trial count is then recorded in the registration.
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
- **Primary inference: clustered paired bootstrap, with two co-primary cluster definitions.**
  - Loss difference `ΔLL = LL(M0) − LL(arm)` per row. 1,000 resamples, seed 116, shared across arms.
  - **Clusters:**
    - (i) **D120 dependence groups** (`fs2-dependence-groups-v1`): connected components over event IDs, series slugs and `neg_risk_market_id`. For crypto, underlying × UTC date (the D120 underlying token table).
    - (ii) the event, with market ID as the fallback (counted).
  - A cluster is defined once over the whole evaluation window. **Each bootstrap draw resamples all of a cluster's rows across all periods together**, so a market or event that recurs over periods is a single unit.
  - A claim needs the CI to exclude 0 under **both** definitions.
  - **Implementation:** `compare.paired_bootstrap` already sums any per-row quantity within clusters and returns `1 − tot/tot_baseline`. Passing per-row log loss (or Brier) in place of SSE gives the relative loss improvement `ΔLL/LL(M0)` directly, with no new code. The cluster vector is the dependence-group ID or the event ID.
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
    - clustered CIs (dependence groups) on mean |SHAP|.
  - Correlated features share credit arbitrarily, so families are the unit of interpretation.
  - **SHAP is exploratory. It is never evidence of edge or of a mechanism.**
- **Ablations:** pre-declared, at most 6 drops. Each is the F\* candidate with one family removed:
  1. momentum/own-history (a2–a4);
  2. book (a11);
  3. structure (a9–a10);
  4. metadata (a12);
  5. liquidity/time/quality (a5–a8);
  6. external (tier b, when present).

  They are reported with dependence-group and event-clustered CIs and are descriptive. No family is promoted to a hypothesis from these results without a new registration.
- **Placebos** (development, required before freeze):
  - labels shuffled within period × event blocks (ΔLL should be about 0);
  - every feature shifted to the *target* snapshot (the leakage alarm must fire);
  - the quote-age-only model;
  - **gap-only model:** M0 + the sweep–Gamma mid gap. This measures how much a pure fresher-price measurement can buy. The registration reports F\*'s gain against this model, and F\*'s gain on rows where `|gap| < 0.0025`. **Report-only and non-gating:** it never enters a verdict.

## 5. Prospective confirmation MC1 (one registration)

- **Registration:**
  - one ledger entry, written and committed before any confirmation snapshot exists;
  - an accepting `science-reviewer` pass.
  - Frozen at registration:
    - the refitted F\* and M0 artifacts (sha256; section 3);
    - δ = 0.005 (already frozen) and its sensitivity 0.01;
    - feature versions, `category_policy`, the fee table, τ and τ_M0;
    - `sd_c` and K\*;
    - the trial count.
  - **No refitting** during confirmation.
  - Forecasts from both arms are logged per snapshot before the target exists (the `forecast.predict` pattern), and scoring asserts equality with the log.
- **Hypotheses (fixed-sequence gatekeeping, family-wise α = 0.05).** Each is tested at α only if every earlier one is Supported.
  - **H1 (predictive):**
    - relative ΔLL = (LL(M0) − LL(F\*)) / LL(M0) > 0 on T1;
    - two-sided 95% CI excludes 0 under both cluster definitions (section 4).
  - **H2a (economic, absolute):**
    - **Statistic:** net mean P&L per trade of the F\* rule (total net P&L ÷ number of trades, recomputed in each resample as a ratio of cluster sums).
    - **Test:** one-sided, H2a: mean > 0. Reject if the one-sided 95% percentile-bootstrap lower bound (the 5th percentile) is above 0.
    - **Clustering:** the same co-primary clusters as H1, resampling whole clusters across periods. 1,000 resamples, seed 116, the same draws as H1.
    - **Rule:** it must reject under **both** cluster definitions.
    - **Minimum:** fewer than 30 trades, or fewer than 10 clusters with a trade, means "not testable". The result is reported, but H2a is not rejected.
  - **H2b (economic, incremental):**
    - **Statistic:** mean over all H2-qualifying origins of (P&L of the F\* rule − P&L of the M0 rule), where an origin without a trade counts 0. This is a paired comparison per opportunity.
    - **Test:** one-sided, H2b: mean > 0. Reject if the 5th-percentile bootstrap lower bound is above 0.
    - **Clustering and rule:** the same co-primary clusters, whole-cluster resampling, shared draws, and rejection required under both definitions.

  This replaces Holm across two hypotheses. The economic labels require predictive support anyway (change 5), so a fixed sequence controls family-wise error without splitting α. It also keeps H1's MDE at the single-test value.
- **Secondary (descriptive):**
  - Brier;
  - calibration slope;
  - δ = 0.01 sensitivity;
  - T2 R2_oos against frozen E002;
  - gain over the gap-only placebo;
  - per-category rows;
  - E50 if registered as secondary.
- **Verdicts:**
  - **Supported (exploratory, prospective), predictive** requires all three:
    - H1 rejects with ΔLL > 0 under both cluster definitions;
    - positive in ≥ 17 of 24 qualifying periods (sign test p ≈ 0.032; if the period count differs, the threshold is the smallest count with one-sided p < 0.05);
    - F\* calibration slope CI overlaps 1, or is at least as close to 1 as M0's.
  - **Economically non-negative at stated costs (optimistic):** predictive Supported, **and** H2a rejects with P&L > 0.
  - **Economically incremental:** additionally H2b rejects with F\* > M0.
  - **Contradicted:** H1 rejects with ΔLL < 0.
  - **Underpowered:** the cap is reached with K < K\* (see the stopping rule).
  - **Inconclusive:** otherwise.
  - **Unavailable:** fewer than 24 qualifying periods by the cap.
- **Economic rule** (an improvement on E004's touch-to-touch):
  - **Size:** q = max(1, `orderMinSize`) shares. Require top-of-book size ≥ q on the entry side.
  - **Entry** at the origin sweep (receipt before the decision):
    - if P(up) − P(down) > τ, buy outcome 0 at `best_ask`;
    - if it is below −τ, buy outcome 1 at `1 − best_bid`.
  - **Exit (primary):** at the **first complete sweep after target snapshot *j* starts**, selling at its `best_bid` (or the complement). The target side then uses a fresh book, not the stale Gamma bid.
    - The loop already runs 2 sweeps per pass, so no new collection is needed.
    - A period whose exit sweep is missing does not qualify for H2. It is counted.
    - The Gamma-bid exit is reported only as a sensitivity.
  - **Fees:** the taker fee on both legs. The fee table is frozen from the pre-implementation fee check (section 7). If a market's fee is unknown, use the highest rate in that table.
  - **Thresholds:** τ for F\* and τ_M0 for M0 are each chosen once in development, by the same rule: among the τ on a frozen grid {0.02, 0.05, 0.10, 0.20} with at least 200 development trades, pick the one with the **highest** out-of-fold mean net P&L per trade. Ties go to the smallest τ. Both are frozen.
  - Latency, queue position and mirrored orders are not modelled. Even a pass is labelled "optimistic, not tradable".
- **MDE (`power.py` logic, unchanged):**
  - The ΔR2 algebra applies to any normalised paired loss: `c_k = K·d_k / LL_M0,total`, `SE = sd_c/√K`, `MDE = (z_{1−α/2} + z_power)·sd_c/√K`.
  - `sd_c` is measured on development out-of-fold ΔLL by `power.cluster_contrib_sd`, under the dependence-group clusters, which give the larger value (Task 8). It is frozen in the registration.
  - **Non-binding planning values only.** `sd_c ≈ 0.6` is borrowed from L1's ΔR2, whose periods had mixed 5–70h gaps and a different loss. At single-test α = 0.05 and power 0.8 (z-sum 2.80), that would give:
    - K = 20k → MDE ≈ 1.2% relative log loss;
    - K ≈ 28k → MDE ≈ 1.0%.
  - These numbers are not used to set any registered quantity. Only the development-measured `sd_c` sets K\*.
- **Stopping rule (pre-declared):**
  - Fixed sample: score **once**, at the first qualifying period count ≥ 24 at which distinct dependence groups K ≥ K\* (K\* is set for MDE = 1% from the frozen `sd_c`).
  - Cap: 36 qualifying periods, or registration + 7 days.
  - **If the cap is reached with K < K\*:** score once, and report the estimate and CI. The verdict is **Underpowered**, and it can never be Supported or economically labelled, whatever the CI shows.
  - Before scoring, only availability counts (periods, rows, groups) may be viewed. No interim looks at any metric.
- **Qualifying period (H1):**
  - source and target are complete snapshots, with a gap of 1.5–3h;
  - forecast logged before the target capture starts;
  - sidecar present for the source;
  - origin sweep complete, with ≥ 99% of eligible tokens returned and receipt before the target starts.
  - **For H2, additionally:** the exit sweep is complete.
  - Failed passes are logged as unavailable, never backfilled.

**MC2 (later, separate registration):** T5 resolution within 1–7 days.
- Hypothesis: F\*-T5 vs the price-only recalibrated logistic.
- It needs a resolution-label collector and weeks of accrual. C1 had 1,976 markets with only ±0.15 slope precision.

## 6. Data volume and calendar

- **Now:** 10 complete loop snapshots, with irregular gaps (a 3h+ gap around pass 6). That is about 8 usable 2h pairs, plus 6 dev captures (5–70h gaps; T2 context only).
  - Book sweeps: 18. Trade samples: 7. Sidecar: committed in `359d675`. It lacks `feeSchedule`, series slugs and events beyond the first; a follow-up implementer is adding those now.
- **Development calendar:** **≥ 40 consecutive complete snapshots with the sidecar present**, about 3.3–3.5 days at the 2h cadence, plus about 1 day for failed passes. The 40 are:
  - 36 origin periods (12 training + 6 test blocks of 4);
  - 1 earlier snapshot for the *i−1* history (a3);
  - 1 target snapshot after the last origin;
  - 1 embargo period at the first fold boundary;
  - 1 spare.

  A dry run of the machinery on existing snapshots (tier (a) without a12) can start now. It is not used for selection.
- **Distinct-cluster accrual (non-binding):** in L1, 15 mixed-gap periods gave 22.8k events, about 10k in the first period and roughly +900 per period after that.
  - This is only a planning guide. Dependence groups are coarser than events, so K will accrue more slowly.
  - The development dry run measures the actual accrual of both cluster types at a 2h cadence, before registration.
- **Confirmation calendar:**
  - At least **26 snapshots** for 24 qualifying periods: an *i−1* and a final target are needed.
  - Budget 30–38 snapshots: about 2.5–3 days, cap 7 days.
- **Total:** about **7–9 days** of continuous 2-hourly collection, from Task 1 going live to an MC1 verdict.
  - MC1 can share snapshots with the E004–E007 confirmations: different registrations, no conflict. Development periods must end before MC1's registration commit.
- **Memory:** about 40k rows × ~70 float32 features × 60 periods ≈ 0.7 GB.
  - Build per-period Parquet and fit in one process.
  - **Never run alongside a collection pass or another multi-GB job.**

## 7. Implementation plan (Sonnet implementer; each task has tests and a review)

**Pre-implementation checks** (open items; each is resolved and written down before the task that needs it):
- **P1 Fee model.**
  - D120's `fee_category` is a category map only. No fee *rate* exists anywhere in the repo, and the sidecar draft does not capture `feeSchedule`.
  - Before Task 7:
    - verify the current Polymarket taker-fee formula and the units of `takerBaseFee` / `feeSchedule` against the official docs;
    - add raw `feeSchedule` to the sidecar;
    - freeze a versioned fee table keyed by (`fee_category`, `feesEnabled`, schedule) with a conservative maximum.
  - Until then, the economic rule cannot be finalised.
- **P2 Dependence groups.** The sidecar draft lacks event **series slugs**, which D120 grouping needs (`GROUPING_LINKS`). Add `events[].series[].slug` (or the D120 equivalent) to the sidecar before the development window starts. Otherwise the co-primary clustering is not computable prospectively.
- **P3 Sweep coverage and timing.**
  - Sweep `20261011T103957Z_1ed72f5a` returned 43,734 of 43,734 eligible tokens. It started about 8 minutes after its snapshot and took 80 s.
  - Task 2 must assert coverage ≥ 99% and receipt ordering per period. It must also record the timing distribution across all sweeps, not only this one.
- **P4 `paired_bootstrap` reuse** is resolved (section 4): pass per-row loss in place of SSE. Task 4 adds only a test that `1 − tot/tot_M0` equals the hand-computed relative log-loss improvement.
- **P5 Sidecar status.**
  - `research_lab/ext_sidecar.py` and the collector hook are committed in `359d675`.
  - Still missing: `feeSchedule` (P1), event series slugs (P2), and events beyond the first in `events[]`. A follow-up implementer is adding these now.
  - Task 1 below is the acceptance spec for that work, not a second implementation.

1. **Task 1 — Snapshot metadata sidecar** (time-critical, because the data is prospective only).
   - **Change:** `collector.collect` additionally writes `rows_ext.csv.gz` and `ext_manifest.json` from the **same** page bodies.
     - Fields: those listed under a12, plus raw `feeSchedule` (P1) and event series slugs (P2).
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
     - joins: sidecar, book sweep (features only; section 1 note 2, origin cutoff), dependence-group IDs (D120 grouping, imported), neg-risk/sibling (reusing `features_dev`/`leadlag_screen` code);
     - `category_policy` filter and recording;
     - label-time columns;
     - the hashed fold manifest (expanding window, 4-period blocks, 1-period embargo).
   - **Tests:**
     - no feature reads a *j* column (`features.register` guard);
     - a feature computed from *i+1* raises an error;
     - purge plus embargo removes exactly the overlapping pairs;
     - `mid_i` and `mid_j` are Gamma mids in every arm, even when sweep features are present;
     - no confirmatory feature equals or encodes the sweep–Gamma gap;
     - targets received before `t0` are unavailable;
     - sweep coverage ≥ 99% is asserted;
     - `category_policy` include/exclude/all, recorded in the manifest;
     - deterministic manifest hash;
     - a3 is missing when *i−1* is more than 3h earlier.
3. **Task 3 — optional deps `research-ml`.**
   - scikit-learn, lightgbm, numpyro, jax[cpu], pinned. Library versions are recorded through `provenance.environment`.
   - **Test:** import smoke, skipped when the extra is absent.
4. **Task 4 — `ml_models.py` + `ml_compare.py`.**
   - M0/M1/M2, nested inner split, fixed search budget, temperature calibration.
   - `compare.paired_bootstrap` with per-row loss and both cluster vectors (P4).
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
   - Choose F\*; compute `sd_c`, K\* (dependence groups), τ and τ_M0; full-development refit and hashes (section 3).
   - Then a challenger review.
9. **Task 9 — MC1 registration, forecast logger and scorer.**
   - `science-reviewer` freeze, then sealed confirmation.
10. **Later:**
    - tier-(b) adapters, one at a time (crypto spot/IV first). Each gets its own admission note and new development data; none is added to a frozen F\*;
    - the resolution-label collector and MC2;
    - the active-frame flow model (a13).

## 8. Risks, and what not to claim

**Risks:**
- **Fresher-price and source mismatch.**
  - Book sweeps and sibling reads arrive after the row they join.
  - Both ends of `dmid` use the Gamma mid, and the gap is placebo-only (section 1 note 2).
  - Book features may still carry some fresher-price information. The gap-only placebo and the small-gap subset bound how much.
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

## 9. Amendment A1 — model-fitting harness choices (PENDING REVIEW)

- **Status:** proposed by the Task 4 implementer, **pending `science-reviewer` review**. It changes no frozen quantity (δ, folds, clusters, gates). Code: `backend/astrolabe/research_lab/ml_models.py`.

1. **M3 as empirical-Bayes Laplace-EM (arm name `M3_eb`) instead of NumPyro NUTS/SVI.**
   - **Model kept:** multinomial logit (flat = reference); N(0, 0.5²) main effects on standardised features; random intercepts by `fee_category` and by event; `chg_1h` and `spread` slopes partially pooled by category; group SDs under a half-normal(0, 0.5) prior; unseen events and categories get the population value.
   - **Estimation:** coefficients are MAP (L-BFGS, analytic gradient). The group SDs are updated in 5 fixed outer iterations by Laplace-EM: posterior variances come from the diagonal Hessian, and the SD update has a closed form under the half-normal prior.
   - **Why:** it runs on all rows, deterministically, in numpy/scipy, with no jax (about 1 GB) and no MCMC diagnostics to babysit. The NumPyro model of Task 5 is **not** replaced: `M3_eb` is a cheaper development arm, and any M3 claim in a registration must name which one was used.
   - **Known limits:** point estimates of the group SDs (no uncertainty on them); a diagonal posterior-variance approximation that ignores cross-class and cross-parameter covariance; no posterior intervals for predictions.
   - **Simulation check** (`simulate_hierarchical_check`, 20 replications, n = 6,000, 12 categories, 150 events, truth SD: category 0.5, slope 0.3, event 0.6; seed 116; results reported as obtained, nothing tuned):

     | Group | Mean estimated SD (sd over reps) | Coverage of nominal 95% intervals for the true effects |
     |---|---|---|
     | event (0.6) | 0.601 (0.033) | 96.3% |
     | category slope (0.3, standardised scale) | 0.273 (0.038) | 85.6% |
     | category intercept (0.5) | 0.408 (0.075) | 71.3% |

   - **Reading:** the event SD is recovered and its effects are well covered. With only 12 categories, the category SD is biased low (about -18%) and its intercepts under-cover, because the diagonal approximation ignores their covariance with the overall intercept. Slopes are mildly low. M3_eb is therefore adequate for event-level pooling, and category-level results from it are descriptive and probably over-shrunk. If M3 is selected as F\*, the NumPyro arm must be run before registration.
2. **M1 grid:** `C` ∈ {0.01, 0.1, 1.0} × `l1_ratio` ∈ {0.1, 0.5}, 6 configs, chosen on the inner split. `C` spans two decades around the standardised-feature default (1.0), where 0.01 is strongly shrunk and 1.0 is nearly unpenalised. `l1_ratio` is kept at or below 0.5 because the tier-(a) features are strongly correlated (a ridge-leaning mix keeps correlated groups together; a lasso-leaning mix picks one member arbitrarily). The grid is small on purpose, so the search-accounting trial count stays low. It is not a search for the best-looking result.
3. **M2:** the design's 20-config random search is implemented: 20 distinct configs drawn without replacement, seed 116, from `LGB_SPACE` (num_leaves, min_data_in_leaf, lambda_l2, feature_fraction), with early stopping on the inner validation block.
4. **Temperature (all arms, including M0):** fitted on the inner-validation predictions of the model trained on the inner-train rows. It is then applied to the model refitted on the whole training fold with the config (and rounds) fixed. The refit model differs slightly from the one that produced the temperature, which is documented in the fit logs (`temperature_source`) and accepted for development. M3_eb has no temperature.
5. **Clustering:** `score_arms` returns `non_inferential: true` with a reason unless both the event and the dependence-group cluster vectors are supplied.
