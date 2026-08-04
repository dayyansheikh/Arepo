# Research paper evidence audit

Audit of `research-references/deep-research-report.md`, read in full by Opus and by an
independent quantitative reviewer before any change to Arepo's model (spec §2). This document
records what the report supports, what Arepo can and cannot use, and the causal/overfitting risks
that gate adoption.

## Title and authors
**Predictive Market Metrics: A Cross-Asset Research and Deployment Framework, with an Arepo and
Polymarket Audit.** No individual author is named; it is a commissioned synthesis report supplied
in `research-references/`. It cites the primary literature it draws on (Cont-Kukanov-Stoikov on
order-flow imbalance; Jegadeesh-Titman and Moskowitz-Ooi-Pedersen on momentum; Meese-Rogoff and
Evans-Lyons on FX; Gorton-Hayashi-Rouwenhorst on commodities; Campbell-Hilscher-Szilagyi on
default; Wolfers-Zitzewitz and Manski on prediction-market prices; Harvey-Liu-Zhu, Bailey-Lopez
de Prado on multiple-testing and backtest overfitting; and 2026 Polymarket-specific preprints).

## Data and market setting
Cross-asset (equities, FX, crypto, commodities, rates, prediction markets). The section directly
relevant to Arepo is **binary prediction-market contracts on Polymarket**, using the public
Gamma (discovery/metadata), Data API (trades, holders, positions, volume), CLOB REST (books,
prices, spread, price-history) and market WebSocket surfaces. It stresses that current CLOB book
endpoints are **not** historical books.

## Proposed metrics (report's ranked hierarchy)
- **Intraday (grade A):** order-flow imbalance (OFI), multi-level/queue imbalance, spread/depth/
  liquidity resilience, aggressive signed flow, microprice.
- **Days-to-weeks (A/B):** momentum/trend (as horizon-specific features), carry/funding/basis,
  post-announcement drift, positioning changes, attention shocks.
- **Prediction-market specific:** price as a *market-implied probability estimate* (not physical
  probability); calibrated hierarchical logistic / beta calibration by category, time-to-expiry,
  spread and liquidity; logical-consistency residuals across related contracts; robust abnormal
  trade size; wallet concentration (HHI/entropy/effective-N) as *context only*.
- **Feature construction:** probability-point AND logit changes (logit better near 0/1); true
  clock-time momentum; trailing volatility excluding the current observation; robust large-trade
  score using median/MAD of log size; concentration via HHI, effective-N and entropy.

## Assumptions
- A binary price is the cost of a state-contingent payoff; it approximates mean belief only under
  restrictive assumptions and can diverge from physical probability via spread, fees, risk
  preferences, heterogeneous beliefs, liquidity and resolution risk.
- Order-book predictability is **seconds-to-minutes** and often consumed by spread/latency.
- YES and NO of the same market are complements, not independent observations.

## Validation method the report requires
Define target/horizon/costs first; immutable point-in-time data with `available_time`; chronological
research/validation/test split; **group** complementary/related contracts so they cannot straddle
a fold; **purge** overlapping-label observations and **embargo** after boundaries; walk-forward
selection only; evaluate once on a frozen test set; then a **prospective shadow** period. Proper
scoring: Brier, log loss, calibration intercept/slope, reliability diagram. Multiple-testing
correction across every feature/lookback/threshold tried (benchmark t>3, or FDR/FWER; PBO and
Deflated Sharpe for return strategies). Costs modelled with executable quotes, level-by-level
fills, fees, slippage, fill probability and a capacity/participation cap. Midpoint returns measure
information, not executable value.

## Limitations the report states
- Polymarket-specific evidence is recent/preprint-level → lower confidence than mature
  microstructure literature.
- A 2026 order-book study found trade-direction inferred from the public feed matched on-chain
  ground truth only ~59% of the time → do not infer maker/taker from quote changes.
- A synchronised Polymarket-Binance study found a **null** out-of-sample result despite a visible
  lead-lag → detectable latency is not executable alpha.
- Single-market arbitrage on Polymarket was rare, short-lived and depth-constrained.

## Features RELEVANT to Arepo (adopt / prioritise, with report location)
| Feature / change | Report location | Arepo action |
|---|---|---|
| Logit change alongside probability-point change (better near 0/1) | Foundational metrics table; §"Features to remove or rename", lines 110, 127, 737 | Add logit movement to the movement feature set |
| True clock-time momentum; stop calling a 4-observation window "1h" | Arepo audit table, lines 734, 1117 | Rename `movement_1h`; compute true-window where timestamps allow |
| Exclude the current observation from its own z-score baseline (score t against t-L..t⁻) | Arepo audit table, line 736 | Fix `rolling_zscore` reference window |
| Confidence = estimated model reliability + data quality, computed separately; NOT observation count/completeness | Terminology + handoff, lines 774, 1087-1089 | Redesign confidence (Phase B) |
| "Distinct evidence families", estimate dependence; drop "independent" claim | Arepo audit, line 740 | Wording + no family-count double-count inflation |
| Permit "no directional view"; direction needs a target-specific reason, not one z-score sign | Arepo audit, line 741 | Keep abstention; make board selective by direction |
| Research Priority = investigation-ranking heuristic, not probability/EV | Terminology + handoff, lines 742, 775, 1091-1093 | Keep as labelled heuristic |
| Missing-data indicators + fixed model semantics (do not renormalise weights over available components) | Arepo audit, line 739 | Missing-feature policy (Phase C) |
| Baselines: no-change, midpoint, price-only, order-book-only, momentum, implied-probability for resolution | §13; report lines 272-283, 1111-1113 | Replay baseline harness (Phase D) |
| Robust abnormal trade size via median/MAD of log size | Feature engineering, lines 402-410 | Already implemented in flow.py; keep |
| Concentration via HHI / effective-N / entropy (context, never insider proof) | lines 414-422, 1077 | Keep neutral wording |

## Features that CANNOT be used (yet or at all)
- **Historical order books / spread / depth / wallet-flow reconstruction from current state** —
  structurally unavailable; must be labelled "price-only retrospective" (lines 745, 1101).
- **Calibrated specialist models (calibration/repricing/liquidity/logical-consistency)** — require
  months of point-in-time data + walk-forward validation the current data store does not yet hold
  (implementation phases table, lines 1026-1049). Not buildable in-session; flagged as research.
- **Cross-venue lead-lag / latency alpha** — the report's own null result; do not claim.
- **Insider/identity inference from wallets** — explicitly "Reject" (line 1038).
- **Perps / Bridge / private trading endpoints** — out of scope for the read-only core (line 1063).

## Look-ahead, survivorship and overfitting risks (called out for Arepo)
- **Look-ahead:** current observation in its own z-score window (line 736); using current metadata
  to define the historical universe (line 744); metadata-based resolution instead of oracle
  settlement (line 748).
- **Survivorship:** historical reconstruction uses currently-discoverable active markets, under-
  representing resolved/delisted markets (line 744). Fix: immutable historical universe.
- **Overfitting:** composite weights/caps/thresholds fixed by judgement give the score no
  calibrated meaning (line 738); renormalising weights over available components makes 0.6 mean
  different things (line 739); family-count bonus inflates when correlated symptoms fire together
  (line 751). Report requires multiple-testing discipline (lines 509-547).

## Implementation priority (what THIS pass adopts vs defers)
**Adopt now (data genuinely available, causal, interpretable, testable — the report's bar, line 43):**
1. Exclude current observation from its z-score baseline (line 736). *Tested.*
2. Rename `movement_1h`; add logit-change movement (lines 734, 110, 1117). *Tested.*
3. Redesign confidence to a reliability estimate combining data quality + evidence-family
   agreement + sample size, producing meaningful variation and no 100% spike (lines 774, 1087-1089).
4. Keep abstention but make the Opportunity Board **selective by directional view**; show how
   selective (screened N, M qualify) (spec §4; report line 741).
5. Missing-component policy: persist timestamped spread/depth/volume snapshots on the live path to
   compute change features; label missing, reduce confidence, never missing→zero; remove any row
   that can never contribute (lines 150-162, 739).
6. Replay baseline comparison (no-change, price-only, momentum, implied) with Brier/log loss and
   honest "no reliable edge" reporting (§13; lines 281-285).
7. Keep Research Priority labelled as a heuristic investigation ranking (line 1093).

**Defer (research-grade, needs point-in-time store + walk-forward — out of session scope):**
Calibrated hierarchical logistic/beta calibration model; repricing distribution model; liquidity/
cost/capacity model; logical-consistency engine; OFI from a reconstructed live book. These are
recorded in `DECISIONS.md` and `docs/limitations.md` as future research, explicitly not claimed.

## Adopted-feature provenance (page/section for each adopted change)
- z-score baseline exclusion → Arepo audit table, report line 736.
- `movement_1h` rename + logit change → lines 734, 110, 127, 1117.
- confidence as reliability (not completeness) → lines 774, 1087-1089.
- abstention + selective directional board → line 741; spec §4.
- missing-feature indicators, no renormalisation → line 739; handoff lines 150-162.
- Replay baselines + proper scoring → lines 272-285, 581-603, 1111-1113.
- Research Priority as heuristic ranking → lines 742, 775, 1093.

**Strict constraint carried into implementation (report line 1123-1125):** no Arepo component
claims alpha without positive prospective/out-of-sample evidence after executable spread, fees,
slippage, fill probability, liquidity and resolution risk. A statistically unusual observation is
not a forecast; a correct forecast is not automatically a profitable trade.
