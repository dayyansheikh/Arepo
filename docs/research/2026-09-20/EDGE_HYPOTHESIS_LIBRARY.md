# AREPO Edge Hypothesis Library

60 designed experiments. None has been executed or validated in this research task. Read MODEL_COMPARISON_AND_VALIDATION.md before interpreting sample requirements or tests.

## H01 — Large trade relative to market liquidity

**Feature id:** F01

**Hypothesis:** Size relative to market liquidity predicts continuation beyond prior returns

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Size relative to market liquidity predicts continuation beyond prior returns; this is a hypothesis, not an established AREPO result.

**Feature definition:** signed trade notional / pre-trade Gamma liquidity

**Raw inputs:** trade price,size,side; liquidity value and observation time

**Sources:** PTRADE;PGAMMA

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-spec/gamma-openapi.yaml

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Two-sided markets with a pre-trade liquidity observation

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Liquidity definition may differ from executable depth; price impact already occurred

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare liquidity-normalised size with raw size and depth-normalised size on identical fills.

**Cost difficulty:** L: existing-data or low-volume metadata pilot; planned 1-3 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E04;HYP

**Status:** Designed; not executed; no edge established

## H02 — Large trade relative to executable depth

**Feature id:** F02

**Hypothesis:** Depth-normalised flow predicts later continuation better than absolute size

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Depth-normalised flow predicts later continuation better than absolute size; this is a hypothesis, not an established AREPO result.

**Feature definition:** signed trade notional / pre-trade same-side executable notional within 1 percentage point

**Raw inputs:** fill price,size,side; all book levels before fill

**Sources:** PTRADE;PBOOK

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Continuous books with sequenced pre-trade state

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Using post-trade depleted depth creates mechanical endogeneity

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Freeze book before trade; separate 0-5 second impact from 5-second-to-horizon change.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E04;HYP

**Status:** Designed; not executed; no edge established

## H03 — Low-history wallet flow

**Feature id:** F03

**Hypothesis:** Flow from wallets with little recorded history contains incremental information

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Flow from wallets with little recorded history contains incremental information; this is a hypothesis, not an established AREPO result.

**Feature definition:** sum(signed notional * 1[prior mature events <= k]) / total notional; retain count continuously

**Raw inputs:** wallet fills, first seen, coverage start, prior resolved events

**Sources:** PTRADE;PWALLET

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Wallets with measured data coverage, including unranked wallets

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** History truncation; wallet rotation; bots; survivor selection

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Fit prior-history count as spline; k sensitivity is development-only.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E15;HYP

**Status:** Designed; not executed; no edge established

## H04 — Newly observed wallet flow

**Feature id:** F04

**Hypothesis:** Recently observed wallets predict repricing after controlling for size and history coverage

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Recently observed wallets predict repricing after controlling for size and history coverage; this is a hypothesis, not an established AREPO result.

**Feature definition:** signed notional weighted by exp(-observed wallet age / tau) / volume

**Raw inputs:** wallet first-seen time, chain creation if available, coverage boundary, fills

**Sources:** PWALLET;PCHAIN

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/resources/contracts

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Complete monitored wallet flow; distinguish fresh creation from fresh observation

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Exchange deposit wallets and incomplete chain history mimic new wallets

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Use coverage-matched established wallets; exclude protocol-created address migrations in a sensitivity arm.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H05 — Wallet flow concentration

**Feature id:** F05

**Hypothesis:** Concentrated directional flow adds information beyond aggregate imbalance

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Concentrated directional flow adds information beyond aggregate imbalance; this is a hypothesis, not an established AREPO result.

**Feature definition:** HHI=sum_w(abs(net_flow_w)/sum_abs_net_flow)^2; sign separate

**Raw inputs:** per-wallet buys,sells,net inventory change; total volume

**Sources:** PWALLET;PTRADE

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Markets with enough attributed flow and recorded unassigned share

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** One entity can use many wallets; hedges and market makers

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare trade-size concentration with wallet concentration; retain unresolved attribution.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E14;HYP

**Status:** Designed; not executed; no edge established

## H06 — Historical wallet posterior skill

**Feature id:** F06

**Hypothesis:** Mature-history wallet skill predicts future flow usefulness

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Mature-history wallet skill predicts future flow usefulness; this is a hypothesis, not an established AREPO result.

**Feature definition:** hierarchical posterior mean of past mature excess score over entry-price baseline, weighted by current signed flow

**Raw inputs:** as-of entries,prices,labels,fees,exposure,category; posterior variance

**Sources:** PWALLET;PTRADE

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 6h

**Secondary horizons:** 1h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** History contains at least two earlier independent labelled events; shrink all others

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Late entry, luck, bankroll, category specialism and profitable arbitrage

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Score history only after label availability; compare win rate, P&L and price-adjusted score with shrinkage.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E10;E15;E24

**Status:** Designed; not executed; no edge established

## H07 — Consensus-opposing flow

**Feature id:** F07

**Hypothesis:** Flow against the currently favoured outcome forecasts reversal or improved calibration

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Flow against the currently favoured outcome forecasts reversal or improved calibration; this is a hypothesis, not an established AREPO result.

**Feature definition:** sum signed notional against sign(midpoint-0.5) / total notional; direction retained

**Raw inputs:** midpoint before fill; signed fills; probability regime

**Sources:** PTRADE;PBOOK

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Binary mapped outcomes with contemporaneous midpoint

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Favourite-longshot effects; classification around 0.5; informed hedging

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Use continuous interaction between flow and log-odds; preregister reversal versus continuation sign.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E10;HYP

**Status:** Designed; not executed; no edge established

## H08 — Top-level book imbalance

**Feature id:** F08

**Hypothesis:** Queue imbalance predicts the next clean midpoint move

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Queue imbalance predicts the next clean midpoint move; this is a hypothesis, not an established AREPO result.

**Feature definition:** (bid_size_1-ask_size_1)/(bid_size_1+ask_size_1)

**Raw inputs:** best bid/ask prices,sizes,age,tick

**Sources:** PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1m

**Secondary horizons:** 5m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Fresh two-sided continuous books with positive depth

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Spoof-like transient quotes; price regime; spread; tick size

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare against identical momentum and spread state; confirm persistence beyond one tick.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E05

**Status:** Designed; not executed; no edge established

## H09 — Microprice displacement

**Feature id:** F09

**Hypothesis:** Microprice displacement predicts repricing more precisely than imbalance alone

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Microprice displacement predicts repricing more precisely than imbalance alone; this is a hypothesis, not an established AREPO result.

**Feature definition:** (ask*bid_size+bid*ask_size)/(bid_size+ask_size)-midpoint

**Raw inputs:** best prices and sizes

**Sources:** PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1m

**Secondary horizons:** 5m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Fresh two-sided books; tick and spread recorded

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Algebraic overlap with imbalance and spread; apparent independent signal is redundant

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare imbalance+spread+interaction baseline; reject novelty if microprice adds nothing.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E05;HYP

**Status:** Designed; not executed; no edge established

## H10 — Depth withdrawal

**Feature id:** F10

**Hypothesis:** Asymmetric depth withdrawal precedes a move beyond contemporaneous traded flow

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Asymmetric depth withdrawal precedes a move beyond contemporaneous traded flow; this is a hypothesis, not an established AREPO result.

**Feature definition:** -change(executable ask depth minus bid depth) / previous total depth

**Raw inputs:** sequenced level updates, snapshots, trade records

**Sources:** PBOOK;PTRADE

**Source urls:** https://docs.polymarket.com/market-data/realtime-data | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 5m

**Secondary horizons:** 1m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Gap-free windows with valid reconciliation

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Cancellations cannot be inferred from snapshots alone; trades consume depth

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Subtract identified executions; retain ambiguous updates and test with/without them.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E04;HYP

**Status:** Designed; not executed; no edge established

## H11 — Trade clustering

**Feature id:** F11

**Hypothesis:** Compact directional trade clusters predict continuation beyond total flow

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Compact directional trade clusters predict continuation beyond total flow; this is a hypothesis, not an established AREPO result.

**Feature definition:** maximum signed notional in a rolling 10-second subwindow / 5-minute notional

**Raw inputs:** individual fill times,sizes,sides,IDs

**Sources:** PTRADE

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Complete deduplicated trade windows

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Batch publication and repeated maker/taker records manufacture clusters

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Use source and receipt clocks separately; compare time-shuffled within-window placebo.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E13;E14

**Status:** Designed; not executed; no edge established

## H12 — Trading burstiness

**Feature id:** F12

**Hypothesis:** Burstiness predicts material-move probability after volume and volatility controls

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Burstiness predicts material-move probability after volume and volatility controls; this is a hypothesis, not an established AREPO result.

**Feature definition:** (sd(interarrival)-mean(interarrival))/(sd(interarrival)+mean(interarrival)); count separately

**Raw inputs:** trade event and receipt times; gap flags

**Sources:** PTRADE

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** At least 20 observed trades per window; low-count arm kept separate

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Polling batching, time of day, market age and activity selection

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare simple count/acceleration before considering Hawkes intensity.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E29;HYP

**Status:** Designed; not executed; no edge established

## H13 — Late large trading

**Feature id:** F13

**Hypothesis:** Large late trades are informative before the underlying event becomes known

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Large late trades are informative before the underlying event becomes known; this is a hypothesis, not an established AREPO result.

**Feature definition:** depth-normalised signed notional * spline(log(1+seconds_to_information_event))

**Raw inputs:** trade,depth,announced event time,market close and resolution schedule

**Sources:** PTRADE;PGAMMA;POFFICIAL

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-spec/gamma-openapi.yaml | https://developer.parliament.uk/

**Primary horizon:** 15m

**Secondary horizons:** 1h;resolution

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Pre-event observations with evidenced information-event time

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Post-event settlement lag masquerades as informed prediction

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Separate pre-event, event-known/pre-resolution and post-resolution strata; never pool.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E15

**Status:** Designed; not executed; no edge established

## H14 — External market lead

**Feature id:** F14

**Hypothesis:** Underlying-market innovations predict delayed PM repricing

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Underlying-market innovations predict delayed PM repricing; this is a hypothesis, not an established AREPO result.

**Feature definition:** underlying return over 1m/5m minus prediction-market implied response estimated on training data

**Raw inputs:** Coinbase or other licensed quotes; strike,expiry; PM prices; latency

**Sources:** XCOIN;PBOOK;PGAMMA

**Source urls:** https://docs.cdp.coinbase.com/exchange/websocket-feed/overview | https://docs.polymarket.com/market-data/realtime-data | https://docs.polymarket.com/api-spec/gamma-openapi.yaml

**Primary horizon:** 1m

**Secondary horizons:** 5m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Precisely matched asset threshold/window markets

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Oracle reference mismatch; clock skew; changing volatility; trading delays

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Use Chainlink/TWAP reference where resolution requires it; compare spot-only and rule-aware mapping.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E13;E17;HYP

**Status:** Designed; not executed; no edge established

## H15 — Related-market lead

**Feature id:** F15

**Hypothesis:** Related contracts lead repricing beyond own momentum

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Related contracts lead repricing beyond own momentum; this is a hypothesis, not an established AREPO result.

**Feature definition:** lagged price innovations from linked contracts residualised on own returns

**Raw inputs:** related prices; relationship type/version; as-of group map

**Sources:** PGAMMA;PBOOK

**Source urls:** https://docs.polymarket.com/api-spec/gamma-openapi.yaml | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Verified common-event or threshold relationships

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Non-equivalent rules, simultaneity and shared information

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Fit lag graph on training only; compare reverse-time placebo and synchronous innovations.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E06;E08

**Status:** Designed; not executed; no edge established

## H16 — News acceleration

**Feature id:** F16

**Hypothesis:** Acceleration in distinct relevant claims predicts material moves

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Acceleration in distinct relevant claims predicts material moves; this is a hypothesis, not an established AREPO result.

**Feature definition:** (unique claims last 15m / 15)-(unique claims previous 60m / 60)

**Raw inputs:** document first receipt,claim clusters,sources,matching confidence

**Sources:** XNEWS

**Source urls:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Markets with explicit entities and evidence-linked text matching

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Syndication, publisher batching, market moves generating coverage

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Deduplicate by claim, compare article count, control pre-news PM returns.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E19;E20

**Status:** Designed; not executed; no edge established

## H17 — News novelty

**Feature id:** F17

**Hypothesis:** Novel relevant information predicts more durable repricing than repeated information

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Novel relevant information predicts more durable repricing than repeated information; this is a hypothesis, not an established AREPO result.

**Feature definition:** 1-max cosine(embedding(new claim), embeddings of prior related claims within 7d)

**Raw inputs:** frozen embedding model, text/version, prior claim corpus

**Sources:** XNEWS

**Source urls:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Permitted text archive and historical first-seen corpus

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Entity mismatch, model updates, first article missing, semantic direction

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare exact-copy, lexical and embedding novelty; zero-shot outcome guessing excluded.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E20

**Status:** Designed; not executed; no edge established

## H18 — Social acceleration

**Feature id:** F18

**Hypothesis:** Social activity acceleration adds information beyond news and prices

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Social activity acceleration adds information beyond news and prices; this is a hypothesis, not an established AREPO result.

**Feature definition:** unique-author relevant original posts per minute acceleration, bot/repost counts separate

**Raw inputs:** licensed posts,receipt time,author/repost IDs,match confidence

**Sources:** XX

**Source urls:** https://docs.x.com/x-api/getting-started/pricing

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Predeclared entity watchlist with stable paid coverage

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** API sampling, bots, engagement revisions, attention after price moves

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Match coverage and posting-hour controls; replace total posts with unique claims in ablation.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E18;E21

**Status:** Designed; not executed; no edge established

## H19 — Official statement detection

**Feature id:** F19

**Hypothesis:** Official statements predict PM adjustment after realistic ingestion delay

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Official statements predict PM adjustment after realistic ingestion delay; this is a hypothesis, not an established AREPO result.

**Feature definition:** indicator and stance probability for a first-available authoritative claim matched to market rules

**Raw inputs:** official release text,receive/publish time,entity/action/date extraction

**Sources:** POFFICIAL

**Source urls:** https://developer.parliament.uk/

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Officially resolvable markets and verified rule matches

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Release already priced; incorrect event date; post-resolution leakage

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Human-audit blinded matched sample; compare observation after 1/10/60-second delay.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H20 — Independent source corroboration

**Feature id:** F20

**Hypothesis:** Additional independent corroboration changes predictive usefulness nonlinearly

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Additional independent corroboration changes predictive usefulness nonlinearly; this is a hypothesis, not an established AREPO result.

**Feature definition:** number of independent origin-source clusters supporting a claim; disagreement separate

**Raw inputs:** source lineage,syndication graph,claim stance,receipt times

**Sources:** XNEWS;XX;POFFICIAL

**Source urls:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ | https://docs.x.com/x-api/getting-started/pricing | https://developer.parliament.uk/

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** At least one matched claim with source lineage

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Ten syndicated copies are not ten independent sources; popularity confounding

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare first-source signal vs incremental independent confirmations at their actual arrival times.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E18;HYP

**Status:** Designed; not executed; no edge established

## H21 — Social and wallet interaction

**Feature id:** F21

**Hypothesis:** Concordant social and wallet evidence adds beyond either family alone

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Concordant social and wallet evidence adds beyond either family alone; this is a hypothesis, not an established AREPO result.

**Feature definition:** social stance acceleration * contemporaneous skill-weighted signed wallet flow

**Raw inputs:** F06,F18 inputs with cutoffs

**Sources:** XX;PWALLET

**Source urls:** https://docs.x.com/x-api/getting-started/pricing | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Common complete observation panel; main effects included

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Both react to the same earlier public news; sparse intersections

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Factorial main-effects versus interaction comparison; double event-group sample floor.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H22 — News and book interaction

**Feature id:** F22

**Hypothesis:** Books validate which novel stories will produce persistent repricing

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Books validate which novel stories will produce persistent repricing; this is a hypothesis, not an established AREPO result.

**Feature definition:** novel claim stance * signed depth withdrawal or microprice displacement

**Raw inputs:** F09,F10,F17,claim direction probabilities

**Sources:** XNEWS;PBOOK

**Source urls:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 15m

**Secondary horizons:** 5m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Continuous book panel and matched stories

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Book may already incorporate news before origin; latency selection

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Prediction begins after both dependencies arrive; compare slower receipt clock.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H23 — Multi-level order-flow imbalance

**Feature id:** F23

**Hypothesis:** Deeper order-flow imbalance adds beyond top-of-book and momentum

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Deeper order-flow imbalance adds beyond top-of-book and momentum; this is a hypothesis, not an established AREPO result.

**Feature definition:** sum_l training-weight_l * signed change in bid/ask queued size with price-level alignment

**Raw inputs:** book deltas,price levels,executions,sequence gaps

**Sources:** PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1m

**Secondary horizons:** 5m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Continuous multi-level books; level alignment valid

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Level relabelling when best price changes; collinearity

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare equal weights to training-estimated weights; no final-test PCA fitting.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E04;E06

**Status:** Designed; not executed; no edge established

## H24 — Book resiliency

**Feature id:** F24

**Hypothesis:** Rapid liquidity replenishment predicts reversal of initial impact

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Rapid liquidity replenishment predicts reversal of initial impact; this is a hypothesis, not an established AREPO result.

**Feature definition:** depth recovered within 30s after shock / depth removed; half-life separately

**Raw inputs:** pre/post-shock books and shock time

**Sources:** PBOOK;PTRADE

**Source urls:** https://docs.polymarket.com/market-data/realtime-data | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Origins 30s after shock, not at shock before recovery is observed

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Conditioning on future recovery; quote flicker; endogenous shock definition

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Origin explicitly after measurement window; match initial shock and spread.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E04;HYP

**Status:** Designed; not executed; no edge established

## H25 — Spread widening state

**Feature id:** F25

**Hypothesis:** Spread widening predicts move magnitude or abstention value beyond volatility

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Spread widening predicts move magnitude or abstention value beyond volatility; this is a hypothesis, not an established AREPO result.

**Feature definition:** (ask-bid)/tick and change over 1m

**Raw inputs:** fresh bid/ask,tick,age

**Sources:** PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T2 magnitude / probability of material move

**Eligible population:** Two-sided quotes; no crossed books

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Mechanical spread bounce; low liquidity; stale sides

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Primary target is absolute clean midpoint move, not trade-price direction.

**Cost difficulty:** L: existing-data or low-volume metadata pilot; planned 1-3 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E03;E05

**Status:** Designed; not executed; no edge established

## H26 — Book slope and convexity

**Feature id:** F26

**Hypothesis:** Depth shape predicts impact persistence beyond top-level depth

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Depth shape predicts impact persistence beyond top-level depth; this is a hypothesis, not an established AREPO result.

**Feature definition:** cumulative notional depth at 0.1/0.5/1/2pp; slope differences across distances

**Raw inputs:** all relevant levels and exact units

**Sources:** PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Enough visible price range; boundaries accounted for

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Near 0/1 truncated side; arbitrary depth bands

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Bands fixed on development; compare continuous cumulative-depth curve model.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E04;HYP

**Status:** Designed; not executed; no edge established

## H27 — Quote persistence

**Feature id:** F27

**Hypothesis:** Persistent imbalance is more predictive than transient imbalance

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Persistent imbalance is more predictive than transient imbalance; this is a hypothesis, not an established AREPO result.

**Feature definition:** time-weighted imbalance / instantaneous imbalance with zero-safe representation

**Raw inputs:** timestamped changes,imbalance series

**Sources:** PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1m

**Secondary horizons:** 5m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Gap-free 60-second book windows

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Receipts batched; unchanged stale book mimics persistence

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Retain last-update age; compare duration and update-count weighted variants.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E05;HYP

**Status:** Designed; not executed; no edge established

## H28 — Impact continuation versus reversal

**Feature id:** F28

**Hypothesis:** Trade shocks split into transient and persistent components using depth and flow context

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Trade shocks split into transient and persistent components using depth and flow context; this is a hypothesis, not an established AREPO result.

**Feature definition:** signed logit(mid at origin)-logit(pre-trade mid); subsequent residual response

**Raw inputs:** trade and pre/post quotes; actual timestamps

**Sources:** PTRADE;PBOOK

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 15m

**Secondary horizons:** 1m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Origin 5s after impact; legitimate pre-trade book

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Predicting already-observed impact; bid-ask bounce; selection on price move

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Forecast remaining response only; estimate response curves over preregistered horizons.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E04;E20

**Status:** Designed; not executed; no edge established

## H29 — Signed-flow autocorrelation

**Feature id:** F29

**Hypothesis:** Persistent flow predicts continued repricing beyond the latest bin

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Persistent flow predicts continued repricing beyond the latest bin; this is a hypothesis, not an established AREPO result.

**Feature definition:** corr(signed notional in adjacent fixed bins), conditional on total flow

**Raw inputs:** deduplicated fills,sides,times

**Sources:** PTRADE

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Minimum bin coverage and trades specified

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Single order split across fills; market-maker inventory cycling

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare order-linked dedup where possible; retain unknown fill grouping.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E29;HYP

**Status:** Designed; not executed; no edge established

## H30 — Trade size tail shape

**Feature id:** F30

**Hypothesis:** Heavy-tailed flow carries information beyond the maximum trade

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Heavy-tailed flow carries information beyond the maximum trade; this is a hypothesis, not an established AREPO result.

**Feature definition:** p95 size / median size; top-1% volume share; raw distribution retained

**Raw inputs:** exact trade sizes,notionals,coverage

**Sources:** PTRADE

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Adequate trade count and no pagination truncation

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Small-sample quantile instability; denomination and liquidity effects

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Shrink quantiles and control count; separate signed tails by side.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H31 — Flow disagreement

**Feature id:** F31

**Hypothesis:** High opposing flow forecasts volatility or reduced directional reliability

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** High opposing flow forecasts volatility or reduced directional reliability; this is a hypothesis, not an established AREPO result.

**Feature definition:** 1-abs(net signed notional)/gross notional; wallet-side entropy separately

**Raw inputs:** all buy/sell flow and wallet side counts

**Sources:** PTRADE;PWALLET

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T2 magnitude / probability of material move

**Eligible population:** Attributed and unattributed volume shares known

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Wash-like circulation, market making, complement-token double counts

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Primary magnitude target; directional candidate includes signed net flow main effect.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H32 — Open-interest versus volume

**Feature id:** F32

**Hypothesis:** New capital exposure distinguishes informative positioning from churn

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** New capital exposure distinguishes informative positioning from churn; this is a hypothesis, not an established AREPO result.

**Feature definition:** change(open interest)/gross traded notional with gross flows separate

**Raw inputs:** as-of OI,trade volume,splits,merges

**Sources:** PDATA;PCHAIN

**Source urls:** https://data-api.polymarket.com/v2/docs | https://docs.polymarket.com/resources/contracts

**Primary horizon:** 1h

**Secondary horizons:** 6h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Comparable OI snapshots and token universe

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** OI definition, mint/redeem, collateral conversions, delayed indexer

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Reconcile with splits/merges; compare OI freshness strata.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H33 — Inventory accumulation

**Feature id:** F33

**Hypothesis:** Accumulation predicts continuation more reliably than isolated purchases

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Accumulation predicts continuation more reliably than isolated purchases; this is a hypothesis, not an established AREPO result.

**Feature definition:** wallet net share accumulation over 1h / earlier visible holdings

**Raw inputs:** wallet historical balances,trades,transfers

**Sources:** PWALLET;PCHAIN

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/resources/contracts

**Primary horizon:** 6h

**Secondary horizons:** 1h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Reconciled inventory windows

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Transfers mistaken for buys; hedges in unobserved venues

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Trade-only and transfer-adjusted variants; no inferred private portfolio.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E14;HYP

**Status:** Designed; not executed; no edge established

## H34 — Wallet specialisation

**Feature id:** F34

**Hypothesis:** Domain-specific historical skill beats pooled wallet rankings

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Domain-specific historical skill beats pooled wallet rankings; this is a hypothesis, not an established AREPO result.

**Feature definition:** past-category exposure entropy and category-specific posterior excess score

**Raw inputs:** mature wallet history,category map version

**Sources:** PWALLET;PGAMMA

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-spec/gamma-openapi.yaml

**Primary horizon:** 6h

**Secondary horizons:** 1h;resolution

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Several prior independent events per domain; shrink sparse wallets

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Posthoc category choice; one dominant event; survivor bias

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Leave-one-domain-out sensitivity; compare pooled and partially pooled posteriors.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E10;E24

**Status:** Designed; not executed; no edge established

## H35 — Public wallet co-trading graph

**Feature id:** F35

**Hypothesis:** Repeated co-trading structure predicts incremental flow quality

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Repeated co-trading structure predicts incremental flow quality; this is a hypothesis, not an established AREPO result.

**Feature definition:** past-only graph similarity from co-trade times/markets; clustered net flow

**Raw inputs:** public addresses,fill times,markets; windowed graph

**Sources:** PWALLET;PCHAIN

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/resources/contracts

**Primary horizon:** 1h

**Secondary horizons:** 6h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Historical graph constructed before origin

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Common news, exchanges, many people sharing infrastructure; identity uncertainty

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then No real-person attribution; degree/time-of-day preserving shuffled graph placebo.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P3

**Expected information gain:** Speculative: retain as a falsifiable candidate; defer expense until core controls work.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H36 — Cross-venue probability gap

**Feature id:** F36

**Hypothesis:** A verified cross-venue gap predicts convergence of the lagging contract

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** A verified cross-venue gap predicts convergence of the lagging contract; this is a hypothesis, not an established AREPO result.

**Feature definition:** rule-aligned PM midpoint minus Kalshi implied midpoint, net of observable costs

**Raw inputs:** venue quotes,rule texts,fees,settlement currencies,clock latency

**Sources:** XKALSHI;PBOOK

**Source urls:** https://docs.kalshi.com/getting_started/quick_start_market_data | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Strictly equivalent event/settlement definitions

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Different rules, fees, access, currency, liquidity and expiry

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Separate price prediction from executable multi-leg arbitrage; test which venue leads.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E08;E09

**Status:** Designed; not executed; no edge established

## H37 — Mutually exclusive outcome coherence

**Feature id:** F37

**Hypothesis:** Coherence deviations predict relative repricing after full-set and cost controls

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Coherence deviations predict relative repricing after full-set and cost controls; this is a hypothesis, not an established AREPO result.

**Feature definition:** sum outcome prices minus 1; executable basket cost separately

**Raw inputs:** event grouping,all outcome prices,ask depths,fee config

**Sources:** PGAMMA;PBOOK

**Source urls:** https://docs.polymarket.com/api-spec/gamma-openapi.yaml | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Verified exhaustive mutually exclusive outcomes

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Incomplete outcome set, negative-risk conversion, missing depth

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Use midpoint deviation for predictive test and basket asks only for economic test.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E08;E09

**Status:** Designed; not executed; no edge established

## H38 — Nested threshold monotonicity

**Feature id:** F38

**Hypothesis:** Violations or unusual curve shape predict relative correction

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Violations or unusual curve shape predict relative correction; this is a hypothesis, not an established AREPO result.

**Feature definition:** p(X>higher strike)-p(X>lower strike), matched expiry/rules

**Raw inputs:** strikes,expiry,quotes,oracle definition

**Sources:** PGAMMA;PBOOK

**Source urls:** https://docs.polymarket.com/api-spec/gamma-openapi.yaml | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Exact common-underlying and same-time outcomes

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Different time windows or reference prices; mapping errors

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Require human-reviewed mapping and bid/ask-aware bounds.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E08;HYP

**Status:** Designed; not executed; no edge established

## H39 — Probability-regime nonlinearity

**Feature id:** F39

**Hypothesis:** Predictive signal changes continuously across near-zero, central and near-one probabilities

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Predictive signal changes continuously across near-zero, central and near-one probabilities; this is a hypothesis, not an established AREPO result.

**Feature definition:** spline(logit(midpoint)) interacting with price and flow features

**Raw inputs:** probability,returns,flow; training knot locations

**Sources:** PBOOK;PTRADE

**Source urls:** https://docs.polymarket.com/market-data/realtime-data | https://docs.polymarket.com/api-reference/data-api/migrating-from-v1

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Entire eligible probability range with quality controls

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Mechanical bounded support; favourite-longshot calibration differs by horizon

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare continuous effects with fixed probability exclusions on same population.

**Cost difficulty:** L: existing-data or low-volume metadata pilot; planned 1-3 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E10

**Status:** Designed; not executed; no edge established

## H40 — Time-to-close and information time

**Feature id:** F40

**Hypothesis:** Information time explains signal decay better than an arbitrary time-to-resolution cutoff

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Information time explains signal decay better than an arbitrary time-to-resolution cutoff; this is a hypothesis, not an established AREPO result.

**Feature definition:** separate log(seconds_to_close), log(seconds_to_event), log(seconds_to_resolution)

**Raw inputs:** versioned close,announced event and resolution state

**Sources:** PGAMMA;POFFICIAL

**Source urls:** https://docs.polymarket.com/api-spec/gamma-openapi.yaml | https://developer.parliament.uk/

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Valid source times with uncertainty flags

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Close extensions and source end-date semantics; known outcome before resolution

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Never substitute current final close date for as-known close date.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E15;HYP

**Status:** Designed; not executed; no edge established

## H41 — Market age and discovery lag

**Feature id:** F41

**Hypothesis:** New-market price discovery yields different signal effects from mature markets

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** New-market price discovery yields different signal effects from mature markets; this is a hypothesis, not an established AREPO result.

**Feature definition:** time since creation; time since first observed; discrepancy retained

**Raw inputs:** createdAt,first received,first tradable book

**Sources:** PGAMMA;PBOOK

**Source urls:** https://docs.polymarket.com/api-spec/gamma-openapi.yaml | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1h

**Secondary horizons:** 6h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** New and matched mature markets; universe entry captured

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Left truncation; retrospective survival; launch incentives

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Include delisted and never-active markets in discovery denominator.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H42 — Incentive and reward changes

**Feature id:** F42

**Hypothesis:** Reward changes alter apparent book signals and short-horizon reliability

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Reward changes alter apparent book signals and short-horizon reliability; this is a hypothesis, not an established AREPO result.

**Feature definition:** change in reward rate,min size,max spread,fee config before origin

**Raw inputs:** versioned public incentives,quotes,trades,fees

**Sources:** PREWARD;PBOOK

**Source urls:** https://docs.polymarket.com/api-spec/clob-openapi.yaml | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1h

**Secondary horizons:** 6h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Documented parameter changes with known observation times

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Policy responds to liquidity; nonrandom treatment

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Matched interrupted-time analysis plus predictive interaction; no causal claim without assumptions.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H43 — Tick-size transition

**Feature id:** F43

**Hypothesis:** Tick transitions change queue-signal effectiveness

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Tick transitions change queue-signal effectiveness; this is a hypothesis, not an established AREPO result.

**Feature definition:** tick change indicator and time since change interacting with imbalance

**Raw inputs:** tick_size_change events,quotes,price regime

**Sources:** PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1m

**Secondary horizons:** 5m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Observed transition windows and matched nontransition markets

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Price boundary triggers tick changes; endogenous transition

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Control continuous probability and spread/tick ratio.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E05;HYP

**Status:** Designed; not executed; no edge established

## H44 — Venue-reference basis and TWAP

**Feature id:** F44

**Hypothesis:** Rule-matched TWAP state improves short crypto forecast beyond spot return

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Rule-matched TWAP state improves short crypto forecast beyond spot return; this is a hypothesis, not an established AREPO result.

**Feature definition:** PM-implied underlying threshold probability relative to Chainlink 30/60s TWAP path and spot basis

**Raw inputs:** RTDS spot,TWAP values,window times,strike,expiry

**Sources:** PRTDS;XCOIN;PGAMMA

**Source urls:** https://docs.polymarket.com/market-data/chainlink-twap | https://docs.cdp.coinbase.com/exchange/websocket-feed/overview | https://docs.polymarket.com/api-spec/gamma-openapi.yaml

**Primary horizon:** 1m

**Secondary horizons:** 5m;resolution

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Crypto markets with exact reference/window rules

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Oracle/spot mismatch; data-stream latency; regime migration

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Compare spot, reference spot and TWAP incremental arms; stratify pre/post rule changes.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H45 — Macro release surprise

**Feature id:** F45

**Hypothesis:** Release surprise predicts residual PM repricing after ingestion delay

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Release surprise predicts residual PM repricing after ingestion delay; this is a hypothesis, not an established AREPO result.

**Feature definition:** (first released actual - frozen prerelease expectation)/training historical surprise sd

**Raw inputs:** official first release,consensus or AREPO prerelease forecast,vintage

**Sources:** XBLS;XFRED;POFFICIAL

**Source urls:** https://www.bls.gov/developers/ | https://fred.stlouisfed.org/docs/api/fred/realtime_period.html | https://developer.parliament.uk/

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Repeated comparable scheduled releases; independent release clusters

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Revised actual, consensus collected after release, simultaneous indicators

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Expectations and first actual frozen separately; realistic delay curve required.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H46 — Official revision surprise

**Feature id:** F46

**Hypothesis:** Revisions convey incremental information about linked event probabilities

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Revisions convey incremental information about linked event probabilities; this is a hypothesis, not an established AREPO result.

**Feature definition:** new vintage minus previous published vintage, scaled by prior uncertainty

**Raw inputs:** vintage history,revision release times,PM quotes

**Sources:** XFRED;XBLS;XEIA

**Source urls:** https://fred.stlouisfed.org/docs/api/fred/realtime_period.html | https://www.bls.gov/developers/ | https://www.eia.gov/opendata/documentation.php

**Primary horizon:** 1h

**Secondary horizons:** 6h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Markets related to revised series with valid vintage calendar

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** ALFRED date granularity may not prove intraday availability

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Daily-only timing cannot support minute-level claims; prospective timestamping needed.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H47 — Weather forecast innovation

**Feature id:** F47

**Hypothesis:** Official forecast revisions lead weather-market repricing

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Official forecast revisions lead weather-market repricing; this is a hypothesis, not an established AREPO result.

**Feature definition:** change in rule-matched probability from consecutive issued forecast ensembles

**Raw inputs:** forecast issue/valid times,location,threshold,station,uncertainty

**Sources:** XNOAA;PGAMMA

**Source urls:** https://www.weather.gov/documentation/services-web-api | https://docs.polymarket.com/api-spec/gamma-openapi.yaml

**Primary horizon:** 1h

**Secondary horizons:** 6h;resolution

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Exact location/station/day/threshold market mapping

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Observation delays, revised forecasts, station mismatch and deterministic forecasts

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Retain issued forecast vintages; compare latest level versus revision.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H48 — Company filing and disclosure novelty

**Feature id:** F48

**Hypothesis:** Relevant filing surprises predict linked market repricing

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Relevant filing surprises predict linked market repricing; this is a hypothesis, not an established AREPO result.

**Feature definition:** new numerical guidance or claim minus prior disclosed/expected value; novelty separate

**Raw inputs:** SEC filing accession,acceptance/receipt time,XBRL units,prior filings

**Sources:** XSEC;XNEWS

**Source urls:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces | https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

**Primary horizon:** 1h

**Secondary horizons:** 6h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Entity-matched company event markets with explicit rule linkage

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Filing reuses earlier press release; XBRL restatement; market already moved

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Earliest public dissemination, not filing date alone, determines novelty.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E19;E20;HYP

**Status:** Designed; not executed; no edge established

## H49 — Search attention innovation

**Feature id:** F49

**Hypothesis:** Search attention predicts later activity or repricing beyond news counts

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Search attention predicts later activity or repricing beyond news counts; this is a hypothesis, not an established AREPO result.

**Feature definition:** training-seasonally-adjusted change in query interest; sample version retained

**Raw inputs:** Trends responses,query,region,time grid,request date,coverage

**Sources:** XTRENDS

**Source urls:** https://developers.google.com/search/apis/trends

**Primary horizon:** 6h

**Secondary horizons:** 24h;resolution

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Access-approved queries with stable measurement and matched events

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Rescaling, sampling, low volume suppression, revised history

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Baseline attention forecasts; no assumed official alpha access or intraday precision.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P3

**Expected information gain:** Speculative: retain as a falsifiable candidate; defer expense until core controls work.

**Evidence ids:** E21

**Status:** Designed; not executed; no edge established

## H50 — Public pageview attention

**Feature id:** F50

**Hypothesis:** Open attention measures predict activity beyond price and news

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Open attention measures predict activity beyond price and news; this is a hypothesis, not an established AREPO result.

**Feature definition:** abnormal entity-page views relative to past weekday/time baseline

**Raw inputs:** Wikimedia pageviews,article identity,publication availability

**Sources:** XWIKI

**Source urls:** https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/documentation/getting-started.html

**Primary horizon:** 24h

**Secondary horizons:** 6h;resolution

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Unambiguous entity pages; API availability matched to origin

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Daily aggregation, bots, unrelated entity news and alias changes

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Use as-known published counts; no forward filling end-of-day totals into morning origins.

**Cost difficulty:** L: existing-data or low-volume metadata pilot; planned 1-3 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E21;HYP

**Status:** Designed; not executed; no edge established

## H51 — Information disagreement

**Feature id:** F51

**Hypothesis:** Contradictory information predicts volatility and lower directional confidence

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Contradictory information predicts volatility and lower directional confidence; this is a hypothesis, not an established AREPO result.

**Feature definition:** entropy of source-weighted claim stance, with source weights fit on past data

**Raw inputs:** stance probabilities,source lineage,matching uncertainty

**Sources:** XNEWS;POFFICIAL

**Source urls:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ | https://developer.parliament.uk/

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T2 magnitude / probability of material move

**Eligible population:** At least two independent claims about same proposition

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Classifier uncertainty versus substantive disagreement; syndication

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Keep extraction entropy distinct from source disagreement; human-adjudicated subset.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H52 — Information decay

**Feature id:** F52

**Hypothesis:** Information half-life varies by liquidity and determines remaining predictability

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Information half-life varies by liquidity and determines remaining predictability; this is a hypothesis, not an established AREPO result.

**Feature definition:** signed novelty surprise * exp(-age/tau); tau training-estimated by family

**Raw inputs:** claim times,novelty,surprise,first observed PM response

**Sources:** XNEWS;PBOOK

**Source urls:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Historical claim stream with complete receipt timing

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Choosing decay from final test; repeated reporting resets false freshness

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. New independent facts may reset age; syndicated copies may not.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E18;E20

**Status:** Designed; not executed; no edge established

## H53 — Price volatility and flow interaction

**Feature id:** F53

**Hypothesis:** The same flow predicts continuation in some volatility regimes and reversal in others

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** The same flow predicts continuation in some volatility regimes and reversal in others; this is a hypothesis, not an established AREPO result.

**Feature definition:** flow imbalance * realised volatility state; continuous spline

**Raw inputs:** return path,signed flow,depth

**Sources:** PTRADE;PBOOK

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 15m

**Secondary horizons:** 1h;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Common complete panel across regimes

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Regime labels fitted with future volatility; interaction overfitting

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Use trailing volatility only; include all main effects.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E04;HYP

**Status:** Designed; not executed; no edge established

## H54 — Market-response underreaction to corroborated news

**Feature id:** F54

**Hypothesis:** A gap between information magnitude and initial price adjustment predicts continuation

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** A gap between information magnitude and initial price adjustment predicts continuation; this is a hypothesis, not an established AREPO result.

**Feature definition:** claim surprise minus training-predicted surprise from already-observed PM move

**Raw inputs:** claim numeric surprise,source count,postreceipt PM response

**Sources:** XNEWS;POFFICIAL;PBOOK

**Source urls:** https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/ | https://developer.parliament.uk/ | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Quantified claims with calibrated direction and receipt times

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Residual model fitted on test; selecting only underreaction cases

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Freeze response model on development and evaluate overreaction as well as underreaction.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E18;E20

**Status:** Designed; not executed; no edge established

## H55 — Cross-domain wallet transfer

**Feature id:** F55

**Hypothesis:** Some wallet skill transfers to related domains but not unrelated domains

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Some wallet skill transfers to related domains but not unrelated domains; this is a hypothesis, not an established AREPO result.

**Feature definition:** posterior category skill transferred with training-estimated similarity and uncertainty

**Raw inputs:** past mature wallet scores,domain mapping,current flow

**Sources:** PWALLET;PGAMMA

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/api-spec/gamma-openapi.yaml

**Primary horizon:** 6h

**Secondary horizons:** 24h;resolution

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Repeated wallets across independent domains

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Shared event families disguised as different categories

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Leave entire economic domains out; compare zero-transfer and complete-pooling models.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P3

**Expected information gain:** Speculative: retain as a falsifiable candidate; defer expense until core controls work.

**Evidence ids:** E10;E24;HYP

**Status:** Designed; not executed; no edge established

## H56 — Public resolution process state

**Feature id:** F56

**Hypothesis:** Oracle process state predicts resolution delay or final-payout uncertainty

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Oracle process state predicts resolution delay or final-payout uncertainty; this is a hypothesis, not an established AREPO result.

**Feature definition:** request/proposal/dispute age,bond,reward,liveness and state indicators

**Raw inputs:** UMA/CTF logs and states,block timestamps,first receipt

**Sources:** PORACLE;PCHAIN

**Source urls:** https://github.com/Polymarket/uma-ctf-adapter | https://docs.polymarket.com/resources/contracts

**Primary horizon:** 24h

**Secondary horizons:** time-to-resolution;resolution

**Target:** T5 time to resolution; separate final-payout label

**Eligible population:** Unresolved conditions with verified contract mapping

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Underlying outcome already known; disputed cases selected ex post

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Primary target resolution time/uncertainty, not pre-event informational alpha.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H57 — Settlement and indexer lag

**Feature id:** F57

**Hypothesis:** Settlement/indexer lag explains apparent signals and predicts quality deterioration

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Settlement/indexer lag explains apparent signals and predicts quality deterioration; this is a hypothesis, not an established AREPO result.

**Feature definition:** receipt-to-block-confirmed lag and unmatched offchain/onchain fill share

**Raw inputs:** match events,receipts,transactions,status,indexer freshness

**Sources:** PTRADE;PCHAIN;PDATA

**Source urls:** https://docs.polymarket.com/api-reference/data-api/migrating-from-v1 | https://docs.polymarket.com/resources/contracts | https://data-api.polymarket.com/v2/docs

**Primary horizon:** 5m

**Secondary horizons:** 15m;1h

**Target:** T6 data-quality/settlement lag; price effect secondary

**Eligible population:** Reconciled public records with no private order data

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** RPC outage, reorgs, source clocks and changing contract versions

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Clock/identity audit, Feature Store v2, source coverage and baseline panel first. Quality/missingness target primary; test price effect only after censoring contaminated windows.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P1

**Expected information gain:** High: discriminates a concrete mechanism from price/context or measurement artefact early.

**Evidence ids:** E12;E13

**Status:** Designed; not executed; no edge established

## H58 — Sports state innovation

**Feature id:** F58

**Hypothesis:** Fresh game-state changes explain and may lead price adjustment

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Fresh game-state changes explain and may lead price adjustment; this is a hypothesis, not an established AREPO result.

**Feature definition:** rule-aligned score,time,period,status innovation relative to prior state

**Raw inputs:** sports WS game IDs,scores,period,elapsed,status,receipt; rules

**Sources:** PSPORTS;PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1m

**Secondary horizons:** 5m;15m

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Verified game-to-market mapping and consistent score chronology

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Feed delay, score corrections, in-play delay, game over settlement lag

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then No claim of beating faster feeds; compare several measured ingestion delays.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E09;HYP

**Status:** Designed; not executed; no edge established

## H59 — Public comment stance and engagement

**Feature id:** F59

**Hypothesis:** Market-specific comment information adds beyond broad news and prices

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Market-specific comment information adds beyond broad news and prices; this is a hypothesis, not an established AREPO result.

**Feature definition:** unique-author proposition stance and reactions known at origin; changes separate

**Raw inputs:** comment creation/removal/reaction events,author IDs,receipt,claim matching

**Sources:** PCOMMENT;PBOOK

**Source urls:** https://docs.polymarket.com/market-data/realtime-data | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1h

**Secondary horizons:** 6h;24h

**Target:** T1 three-class clean midpoint movement; T2 log-odds change secondary

**Eligible population:** Moderation and deletions tracked; permitted public content

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Manipulation, promotional content, future reaction counts, private-information claims

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 1,000 independent event blocks; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. Rows/fills are not independent events.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Compare original evidence-bearing claims to sentiment-only comments; exclude future engagement.

**Cost difficulty:** M: prospective feed/alignment pilot; planned 3-7 researcher-days; estimates exclude elapsed sample accumulation.

**Priority:** P3

**Expected information gain:** Speculative: retain as a falsifiable candidate; defer expense until core controls work.

**Evidence ids:** HYP

**Status:** Designed; not executed; no edge established

## H60 — Cross-source disagreement as a forecast feature

**Feature id:** F60

**Hypothesis:** Disagreement predicts future forecast error and useful abstention

**Null:** No prospective improvement over the strongest development-selected price/context baseline on the identical eligible panel; apparent association is explained by listed controls.

**Mechanism:** Disagreement predicts future forecast error and useful abstention; this is a hypothesis, not an established AREPO result.

**Feature definition:** dispersion among rule-aligned venue/reference probabilities and Bayesian/ML predictions

**Raw inputs:** fixed model out-of-fold predictions,matched quotes,as-of features

**Sources:** MODELS;XKALSHI;PBOOK

**Source urls:** MODEL_COMPARISON_AND_VALIDATION.md | https://docs.kalshi.com/getting_started/quick_start_market_data | https://docs.polymarket.com/market-data/realtime-data

**Primary horizon:** 1h

**Secondary horizons:** 15m;6h

**Target:** T7 forecast error and selective risk

**Eligible population:** Common OOF and prospective panel with all constituent outputs

**Sampling controls:** Scheduled eligible-universe sample plus matched untriggered controls; event/time/liquidity/probability matching; inclusion probabilities retained. See shared protocol.

**Baseline:** B0 no-change; B1 momentum; B2 price/context model; B3 current AREPO where reproducible; add-feature and leave-family-out comparisons.

**Confounders:** Disagreement reflects scale or miscalibration; stronger model chosen post-test

**Primary test:** Chronological grouped paired-score comparison with event/date-cluster uncertainty; Bayesian partial-pooling effect plus simple/boosted challenger. Magnitude/time/error targets use their prespecified proper loss. No final-test tuning.

**Effective sample requirement:** Planning floor 2,000 independent event blocks; double for sparse interactions; final N from paired-loss pilot variance and multiplicity-adjusted 80% power. If unattainable report insufficient evidence.

**Validation:** V1: expanding chronological development folds with purging by actual label availability; event-group lock; untouched future panel; family FDR discovery then prespecified confirmation.

**Falsification:** At adequate prespecified power, prospective uncertainty excludes the registered minimum useful improvement, or effect disappears with timing/quality controls. Wrong sign rejects signed mechanism. Imprecision is inconclusive, not success.

**Dependencies:** Baseline panel, provenance and rights/access verification; then Forecast absolute error/material-move probability using OOF disagreements; compare selective risk at equal coverage.

**Cost difficulty:** H: wallet/text/graph or sparse-event linkage; planned 1-3 researcher-weeks; estimates exclude elapsed sample accumulation.

**Priority:** P2

**Expected information gain:** Medium: valuable conditional on prerequisite data quality and sufficient event diversity.

**Evidence ids:** E22;E23;HYP

**Status:** Designed; not executed; no edge established
