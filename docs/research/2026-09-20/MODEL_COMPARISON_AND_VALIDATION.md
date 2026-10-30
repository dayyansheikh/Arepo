# AREPO model comparison, targets and prospective confirmation

Protocol proposal, 19 September 2026. All numerical decision thresholds below are proposed research choices to preregister, not empirically established AREPO optima. No candidate model or ensemble has been fitted or prospectively validated in this task.

## 1. Distinct estimands

**Repricing:** conditional distribution of a future clean quote change given information actually available to AREPO at origin t. **Event forecasting:** probability of the underlying event/final payout, with rules and resolution uncertainty explicit. **Economic value:** attainable net proceeds under a specified strategy, order type, size, latency and fee schedule. A model can improve one without improving the others. Forecasting an underlying asset is a fourth, separately labelled target when relevant: compare against the underlying venue's own price/volatility baseline, not only the Polymarket price.

A prediction-market midpoint can be a powerful final-resolution prior, but it is not the probability that the midpoint will rise in the next hour. The repricing model needs a distribution for future price change; the resolution model needs a payout probability.

## 2. Targets and quote eligibility

Let b and a denote valid best bid and ask, m=(a+b)/2, s=a-b, and h the horizon. Choose a quote at the target using a prespecified rule; do not select whichever nearby quote produces a favourable outcome. Proposed primary rule: first valid quote at or after t+h within tolerance; report its delay. A target-window time-weighted midpoint is a separate sensitivity target and includes an explicitly declared later observation window. Never carry a stale trade price forward as a fresh quote.

| Target | Definition | Primary metric and restrictions |
|---|---|---|
| T1 three-class material direction | down if m(t+h)-m(t)<-delta(t); flat within ±delta(t); up above delta(t) | Multiclass Brier and log loss; retain flat observations. Proposed delta(t)=max(2 ticks, origin spread) for development comparison against fixed 1/2 percentage-point thresholds. Freeze choice before confirmation. |
| T2 continuous/magnitude | probability-point change, and logit(clip(m(t+h)))-logit(clip(m(t))) | MAE and predictive log score/CRPS where a distribution exists; magnitude variant uses absolute change. Clip only for modelling, retaining raw 0/1 prices and a versioned epsilon. |
| T3 time to material move | first passage through ±delta(t) after origin | Competing risks up/down with censoring; time-dependent Brier or appropriate survival likelihood. A 15-minute polling schedule cannot identify a one-minute first passage. |
| T4 path and execution | maximum favourable/adverse excursion; size-specific bid/ask liquidation proceeds | Requires dense quote paths and depth. Sparse observations provide lower bounds on extrema, not exact extrema. |
| T5 resolution | payout vector, underlying event state, and time to authoritative resolution | Binary/multiclass proper score for event; survival for delay. Voids, fractional payouts, ambiguity and revisions remain separate states. |
| T6 quality | source gap, stale/invalid quote, indexing or settlement delay | Coverage, latency quantiles, error classification and calibration; operational utility is not alpha. |
| T7 model error | absolute error/proper-loss distribution, conditioned on disagreement | Selective risk versus coverage; useful abstention must beat a matched-coverage baseline. |

Proposed timing tolerances for a new pilot are 5 seconds for 1-minute horizons, 15 seconds for 5-minute horizons, 30 seconds for 15-minute horizons, 60 seconds for 1 hour, and 5 minutes for 6/24 hours. These are design tolerances, not guarantees that the sources can meet them. Record actual delay and run stricter sensitivity checks. If timing coverage fails, move that experiment to a longer horizon or collect appropriately; do not silently relax the label. Seven-day targets are a separate slow programme.

Require a two-sided noncrossed book, valid units, known token mapping and recorded update age. Use source/receipt latency bounds, not a universal “fresh within x” assumption. A source without reliable event time may support a receipt-time experiment if both inputs and outcomes use that contract; it cannot support a claim about millisecond venue information. Store every eligibility exclusion and report coverage by model, category, probability, spread, depth and time.

Closure before horizon is a competing event/censoring state for repricing, not an automatic flat return. For final-resolution experiments it can supply a later label when the official outcome is available. Missing quote outcomes should be reported with sensitivity bounds and, only under defendable missing-at-random assumptions, inverse-probability weighting. A missingness model does not make informative missingness disappear.

## 3. Sampling and applicability

Use two complementary arms: a stable scheduled eligible-universe sample and event-triggered observations. The first estimates broad applicability; the second measures screening efficiency. For each trigger, sample untriggered controls in the same time, probability, liquidity and economic-event strata. Save selection probability, trigger policy/version and features before selection. Event-only samples cannot establish population-wide uplift.

Do not exclude a whole category or long time-to-close region because of an intuitive theory. Model continuous probability, depth, spread, market age, time to information event, time to close and source intensity, then test prespecified interactions with partial pooling. Establish minimum data-quality requirements first; estimate where the model is applicable using development data. Report out-of-distribution and insufficient-evidence abstention separately from low predicted movement.

For the legacy data, use the 56 six-hour cohorts as one exploratory panel; daily and weekly cohorts that share the same origin must not be counted as independent extra observations. A strict timing subset is valid for an explicitly selected population only. Compare its characteristics with the excluded population. The 16-day collection span cannot certify stability across seasons or macro regimes even if many distinct markets appear.

## 4. Baselines

B0 is no expected change/empirical class frequencies for repricing, and current clean market probability for final resolution. B1 is momentum at predeclared trailing windows, calibrated on development data. B2 adds price/context: return path, probability, volatility, spread, depth, age, time-to-event/close and source quality, using regularised regression/GAM and a constrained boosted-tree challenger. B3 is the frozen current AREPO score/ranking/direction where reproducible. B4 is a relevant domain baseline: rule-aware asset threshold model, official forecast or cross-venue probability, where available.

The main edge claim is improvement over the strongest relevant development-selected baseline, not merely a coin flip. Report all baselines so an expensive model cannot hide that a simple context model performs equally well. Preserve predictions from each baseline at identical origins. For ranking, include random-within-eligible, absolute momentum, unusual-return score, liquidity/volume and current AREPO rank.

## 5. Chronological and event-aware splitting

Create a versioned split manifest before modelling. In development, use expanding training windows and subsequent validation windows. Remove training examples whose outcome availability extends into validation; purge overlapping label intervals at boundaries using actual intervals, not only the nominal longest horizon. For unrelated events in the same news regime, use date-block uncertainty as well as event clustering.

There are two deployment questions and therefore two reported evaluations: (a) forecasting later observations of existing events using only their mature past information; (b) generalising to unseen economic events. The latter holds complete economic event groups out of training and tuning. Do not make a random row split, or pretend that event grouping and chronological ordering are automatically compatible. A long-lived event spanning a boundary is excluded from the unseen-event test or assigned wholly to one side; the choice is frozen.

The final confirmation period starts only after definitions, data-quality checks, hyperparameter budget, model choice, ensemble variants, thresholds, metrics and sample/stopping rules are fixed. All candidates use **the exact same origin IDs, event groups, horizons, target versions and outcome observations**. Report an additional broad-panel analysis with explicit missing-family handling; never compare one model on an easier complete-case subset with another on the whole population.

Use event-block bootstrap or cluster-robust paired loss differences, with time-block sensitivity. If clusters overlap through a graph, define connected economic groups conservatively and report the loss of effective sample. With very few independent events, ordinary bootstrap confidence intervals are unreliable: use descriptive results and an explicit insufficient-evidence verdict.

## 6. Bayesian candidates

Start with a hierarchical multinomial logistic T1 model. For each nonreference class, linear predictor = global intercept + horizon effect + partially pooled category/regime effects + standardised feature effects + a small preregistered interaction set. Avoid one unregularised coefficient per wallet or market. New groups receive the population predictive distribution, not a fitted effect based on their future labels.

Candidate weakly informative priors: standardised main effects Normal(0,0.5), interactions Normal(0,0.2), group standard deviations half-Normal(0,0.5), intercepts centred on development baseline class log-odds with scale 1.5. These need prior-predictive checking for plausible probability distributions; alternative scales 0.25/1.0 form a recorded sensitivity analysis. With many candidates use regularised shrinkage and set the expected number of nonzero effects before fitting. [Regularised horseshoe research](https://doi.org/10.1214/17-EJS1337SI).

For continuous log-odds changes, start with a Student-t location/scale model, e.g. nu=4 in the simple candidate, a horizon-specific scale and partial pooling; compare heteroskedastic scale driven by depth/volatility. The tail parameter is a sensitivity choice, not known truth. A hurdle model for flat versus moving markets may be appropriate if price discreteness is material. For event resolution, use an offset of current market log-odds and learn a shrunken correction rather than discarding a strong prior. Underlying-asset threshold models must specify the return distribution and reference-price rule separately.

Check convergence across chains, effective sample sizes, divergences, posterior predictive class/return tails, calibration and influential event groups. Proposed diagnostic standards include R-hat below 1.01 and adequate bulk/tail effective sample size for the estimands; diagnostics cannot compensate for a wrong sampling model. Report prior sensitivity and leave-one-event-family-out influence. Bayesian posterior certainty is conditional on assumptions and does not exempt the research from multiplicity or prospective validation. [Bayesian Workflow](https://arxiv.org/abs/2011.01808).

Online updating is a later experiment. Update only with mature labels, freeze and log each parameter state, and compare a fixed model against a scheduled rolling retrain. Immediate adaptation using delayed outcomes or retrospective drift boundaries leaks information. Bayesian state-space drift models may help, but flexible dynamics can also chase noise.

## 7. ML candidates

Use regularised multinomial/logistic and additive models first, then one well-tuned gradient-boosted-tree family as the principal nonlinear challenger. Compare XGBoost and/or LightGBM within a fixed development search budget; choose the strongest using mean paired proper score, calibration and stability, not final-test accuracy. Both are established tabular implementations, not evidence of Polymarket advantage. [XGBoost](https://arxiv.org/abs/1603.02754), [LightGBM](https://papers.nips.cc/paper/2017/hash/6449f44a102fde848669bdd9eb6b76fa-Abstract.html).

Fit transformations, imputation, feature selection, target encodings and calibration within each training fold. Include explicit missingness and coverage where appropriate; never compute wallet encodings on future labels. Grouped permutation importance and leave-family-out tests are more informative than correlated-feature importance rankings alone. Explainability values describe a fitted model's attribution, not the causal reason prices moved.

Defer deep sequence models, graph networks and broad text fine-tuning until simpler models leave a stable residual and sufficient independent events exist. A million fills from a few related markets is not a million independent training examples. Retrain on a fixed schedule selected in development; monitor feature coverage, loss, calibration and latency with delayed labels. Drift alerts trigger review, not automatic final-test re-optimisation.

## 8. Explicit ensemble tournament

Let pB and pM be calibrated class-probability vectors from the selected Bayesian and ML constituents for the same target. Continuous forecasts require distribution or quantile-compatible combinations; averaging class probabilities cannot be presented as a continuous-return model.

| Arm | Definition | Fitting restriction |
|---|---|---|
| B | Bayesian alone | Fixed development choice and calibration. |
| M | Strongest ML alone | Chosen solely on development data. |
| E50 | 0.5 pB + 0.5 pM | No fitted weights. |
| EW | w pB + (1-w) pM; 0≤w≤1 | Estimate w by proper loss on chronological out-of-fold predictions; shrink toward 0.5. |
| ES | Regularised logistic/multinomial meta-model of constituent log probabilities and a very small context set | Train on genuinely forward out-of-fold base predictions; nested calibration. Never on in-sample fitted probabilities. |
| EG | Regime-dependent mixture, w(x) pB+(1-w(x)) pM | Only after stable expert-by-regime differences and sufficient per-regime events; gate uses origin-available variables and regularisation. |

Every arm faces the same final panel and scoring rules. Store uncalibrated and calibrated constituent predictions so any improvement from recalibration can be separated from combination. Fit ensemble calibration inside development as another recorded choice. The stacking literature supports predictive combination as a method, not a guarantee that a particular ensemble wins. Standard leave-one-out stacking must be adapted to forward, event-aware folds here. [Stacking](https://doi.org/10.1214/17-BA1091), [forecast combination puzzle](https://doi.org/10.3390/econometrics7030039).

**Proposed recommendation gate:** choose a primary target/horizon before confirmation; require at least 1% relative Brier-loss improvement over the stronger development-selected constituent, a multiplicity-adjusted one-sided 95% lower confidence bound on improvement above zero, no material calibration deterioration, and consistency across at least two nonoverlapping future blocks with adequate event diversity. Also compare against both constituents with simultaneous uncertainty so post-test selection of “stronger” cannot flatter the ensemble. The 1% threshold is a proposed minimum useful predictive gain, not a profitability threshold; amend it once, before the prospective lock, based on product utility and attainable power.

If the ensemble ties or loses, recommend the stronger simpler constituent. If confidence intervals are wide, retain the ensemble as unproven. EG must beat EW/ES as well as constituents after its extra search complexity. No ensemble currently qualifies for recommendation.

## 9. Disagreement, calibration and screening

Store full predictive vectors, distance between models, entropy of each model, posterior uncertainty where available, data-quality uncertainty and out-of-distribution flags separately. Agreement can reflect shared bias. Disagreement is not automatically a confidence interval. Test whether it predicts error and supports better selective risk at equal coverage (H60).

Use reliability plots with event-aware uncertainty, calibration intercept/slope, Brier decomposition where appropriate, log loss and class-wise diagnostics. Avoid excessive bins when sample sizes are small. Compare temperature/Platt-style calibration with isotonic only when development data support its flexibility. Calibrate separately by horizon, with partial pooling across sparse regimes; no calibration on final outcomes. [Proper scoring rules](https://doi.org/10.1198/016214506000001437), [calibration study](https://arxiv.org/abs/1706.04599).

For screening report precision@K for material moves, directional precision@K separately, lift over the same eligible baseline, recall/coverage, ranking stability under resampling and turnover of top-K. Declare K or a review-capacity rule in development. Report ties, unavailable outcomes and concentration by event. A useful research screener may save analyst time without producing positive net trading returns; test time-to-relevant-evidence and independently judged alert usefulness as product outcomes.

## 10. Power, multiplicity and falsification

The cards' 1,000/2,000 event-block planning floors are triage estimates, not power calculations. For a paired proper-loss effect d with cluster-level standard deviation sigma, an initial approximation is N≈((z_alpha+z_power)*sigma/d)^2, then inflate for dependence, unequal cluster sizes, attrition and planned comparisons. Estimate sigma on a pilot and simulate the actual clustered design. For a simple independent 50% hit-rate benchmark, detecting +5 percentage points at two-sided 5% and 80% power takes roughly 784 observations; +2 points takes roughly 4,900. With 50 Bonferroni comparisons these become roughly 1,700 and 10,700. Those examples are not the required N for paired multiclass Brier scores.

Count independent economic events and calendar blocks, report cluster-size distributions and effective sample sensitivity. Repeated quotes can improve within-event measurement without adding independent event-level evidence. Slow macro releases may need years or cross-release pooling; make that limitation explicit instead of promising a short calendar deadline.

Group the 60 hypotheses into prespecified families; use discovery FDR with dependence-aware treatment or conservative resampling, then a small fixed confirmation set. Basic Benjamini-Hochberg guarantees require assumptions; use a conservative alternative or block-resampling calibration when dependence is not defensible. Record every feature/threshold/model/horizon attempted. Do not recycle an inspected final test as “fresh”. [FDR foundation](https://doi.org/10.1111/j.2517-6161.1995.tb02031.x), [backtest overfitting](https://doi.org/10.21314/JCF.2016.322).

The null is no incremental useful information beyond the strong baseline. A nonsignificant estimate with a wide interval is inconclusive. At adequate power, an interval excluding the minimum useful improvement, a consistently wrong signed mechanism, or disappearance under legitimate timing controls is evidence against the hypothesis. Save negative results and the exact conditions tested; a failed 1-minute experiment does not prove the feature is useless for final resolution.

Required placebo checks include future-shift detection, shuffled event labels within permitted blocks, reversed lead-lag, duplicated/syndicated text, historical LLM knowledge leakage, quote-age-only predictions and source-outage indicators. Their purpose is to detect measurement artefacts, not generate extra positive hypotheses.

## 11. Economic confirmation and promotion

For a size-Q long trade, compare later depth-weighted sale proceeds with initial depth-weighted purchase cost, then subtract both applicable fees, latency/slippage and other costs. A midpoint change is not an executable return. For bearish exposure specify buying the complementary token or an actually feasible inventory strategy; do not assume unlimited shorting. Maker strategies need queue-position/fill uncertainty and adverse-selection modelling. Displayed depth is not a fill guarantee, and multi-leg baskets can have leg risk and locked capital.

Use market/time-specific fee parameters. Current documentation defines taker fee as C*feeRate*p*(1-p), with configuration varying by category/market; the audited AREPO constant of zero is not a valid universal current assumption. Preserve collateral denomination and protocol version. Report gross predictive movement, fee/spread-adjusted indicative opportunity, simulated execution and actual fill evidence as four distinct evidence levels. This task authorises none of the trading stages. [Polymarket fees](https://docs.polymarket.com/trading/fees).

Promotion gates are sequential: (1) provenance and archive equivalence; (2) prospectively better calibrated predictive performance; (3) useful screening at fixed review capacity; (4) economic evidence at stated capacity and conservative latency/cost assumptions; (5) separately authorised implementation/security review. Passing one gate never implies passing the next.
