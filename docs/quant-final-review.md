# Prediction-market quant final review (spec §2)

Independent quantitative review of Arepo after the final gap-closure pass. Grounded in code and in
live measurements. Verdicts: OK / CONCERN / RESOLVED.

## 1. Causal validity and look-ahead — OK
`evaluation/historical.py`: entry is the price **at** the cut-off (`entry = prices[-1]` from
`prefix = [p for p in hist if p.t <= as_of]`); forward prices use only `suffix` (`t > as_of`); the
near-mid gate is applied to the cut-off price, never today's. `analytics/zscore.py` now scores the
last return against a baseline that **excludes** it (was contaminated). No path lets outcome
information change eligibility, features or labels. `test_replay_regression.py` and the existing
no-look-ahead tests lock this. Momentum baseline uses only pre-cut-off prices.

## 2. Survivorship and sample selection — CONCERN (disclosed)
The reconstruction universe is drawn from markets **still active now**, filtered to those with
usable historical price data and a near-mid entry. This is a mild survivorship channel into *which
markets are considered* (not into entry price or outcome). It is disclosed in the Replay
limitations and in `docs/replay-regression-investigation.md`. The funnel (existed → had price data
→ eligible → directional → top five) now makes the attrition visible. An immutable historical
market universe would remove it entirely (recorded as future work).

## 3. Replay reconstruction / historical confidence — RESOLVED
Reconstructed entries carry a reduced confidence (~0.30) computed from cut-off information
(price-only, no historical order book/flow), not current confidence. Modes (prospective /
reconstructed / synthetic) are badged and never mixed in one metric.

## 4. Confidence calibration — RESOLVED
Was a data-completeness gate saturating at 100% (10% of live cards). Now `reliability_confidence =
data_quality × family_corroboration × component_completeness`. Live: max 0.80, 0% at 100%. 100%
requires perfect data AND ≥3 families AND all microstructure components present. Monotonicity,
missing-data-penalty, single-family-cap and saturation tests added. Full outcome-based calibration
(reliability curve) still needs a larger prospective sample (future work) — not claimed now.

## 5. Sensitivity / specificity / thresholds — OK
Directional gate is one shared rule across board, market detail, Signal Lab and Replay
(`opportunity/hypothesis.py` / `lib/directional.ts`). It was not loosened to inflate coverage; the
z-score fix (signed `flat_baseline_move`) legitimately resolves direction on flat-then-move
markets. Coverage is a measured 47% of screened markets, disclosed.

## 6. Component availability — RESOLVED
The three microstructure change features are now computed from a persisted snapshot series and
wired into live signal generation (were 0/40). Missing stays missing (never zero); a single
snapshot cannot produce a change; collection is idempotent per minute. `/api/opportunity/diagnostics`
reports availability.

## 7. Baselines and edge claims — OK / RESOLVED
Replay compares Arepo against no-change, momentum, always-up, always-down over the same sample with
hit rate and Wilson 95% intervals. On the current tiny sample Arepo (3/5) equals momentum and
always-down; the UI labels this **inconclusive** and claims no edge. This is the correct posture: a
3-5 market hit rate is not evidence. Brier/log-loss framework exists in `replay_stats`; extend to
the resolution target as the prospective sample grows.

## 8. Misleading metrics — RESOLVED
The main risks (100% confidence with missing components; a tiny-sample hit rate shown as a result;
a tag link to a non-existent methodology section; every anomaly implied to be a directional
opportunity) are all fixed: confidence penalised for missing components; inconclusive banner +
baselines; broken link removed; Signal Lab marks observational-only signals. Research Priority
remains labelled a heuristic; no component claims alpha.

## Top remaining (future research, not blockers)
1. Outcome-based confidence calibration curve once the prospective sample is large enough.
2. Immutable historical market universe to remove residual survivorship.
3. Extend baselines to the resolution target with Brier/log-loss as the sample grows.
