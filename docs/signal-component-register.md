# Signal component register

Every component the composite anomaly signal can use, its source, and — critically — whether it is
actually wired into the LIVE model and whether it is reconstructable historically. Produced for the
functional validation pass (spec §4). Figures in "live availability" are from the running product
(`/api/opportunity/diagnostics`, 120 tokens) on 2026-08-04.

The composite is a weight-renormalised mean over the components that are actually present, so a
missing component neither inflates nor deflates the score (it is dropped, never treated as zero).
A reading with no material price context is capped (`BOOK_ONLY_CEILING`) so order-book features
cannot drive a top score alone.

## Composite components (`analytics/anomaly.py`)

| Component | Family | Source | Weight | Live availability | Historically reconstructable | Wired live | Materially moves output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `unusual_return` (rolling z-score of latest return) | price | price history | 0.24 | ~100% | Yes (price-only) | Yes | Yes |
| `movement_abnormality` (return-burst score) | price | price history | 0.20 | ~100% | Yes | Yes | Yes |
| `volatility_regime` (short vs long return vol) | price | price history | 0.16 | ~100% | Yes | Yes | Yes |
| `book_imbalance` (near-touch bid/ask imbalance) | order book | current order book | 0.12 | live only | **No** (no historical books) | Yes | Yes (capped alone) |
| `spread_change` (relative spread vs baseline) | order book | persisted snapshot series | 0.08 | 66.7% | No | Yes | Yes when present |
| `depth_change` (near-mid depth vs baseline) | order book | persisted snapshot series | 0.08 | 60.0% | No | Yes | Yes when present |
| `volume_acceleration` (relative rise in volume) | (price/flow) | in-frame volumes | 0.12 (nominal) | **0.0%** | No | **Replay/backtest only** | No effect live |

### `volume_acceleration` — deliberate decision (spec §4)

It is present **0/120** on the live path and cannot become available there: the read-only live path
never builds a per-interval volume series (the underlying `market.volume` is cumulative lifetime
volume, so 5-minute differences are ~0 and yield `None`; impl review D#4). It therefore contributes
nothing to any live signal.

Decision: **keep the component defined** (it is genuinely computed in Replay/backtest, which carry
in-frame volumes, and in the deterministic demonstration dataset), but:

- exclude it from the confidence **completeness** set, so a permanently-absent component no longer
  drags every live confidence down for a non-data reason (`scoring.COMPLETENESS_COMPONENTS`);
- because the composite renormalises over present components, its nominal 0.12 weight is simply
  redistributed live — the live model is effectively a six-component model, which this register now
  states plainly rather than implying a seven-component model that never runs;
- surface an honest, mode-accurate reason in the UI ("Only computed in Replay mode; the live path
  builds no volume series") instead of "Not enough volume history yet", which wrongly implied it
  would appear over time.

It is **not** removed outright because it has a valid source and effect in Replay/backtest; removing
it would break those paths for no honesty gain, since it is already inert and clearly labelled live.

## Trade-flow / wallet / timing indicators (`analytics/flow.py`, Opportunity Board only)

These require public trade history and are available only in live mode on the Opportunity Board
(not on the per-signal Signal Lab view, which has no trades). This is the one documented reason a
Board card's confidence / family count can exceed the Signal Lab value for the same market (§17).

| Indicator | Family | Source | Reconstructable historically |
| --- | --- | --- | --- |
| `large_relative_trade` | trade flow | public trades | No (no historical trade store) |
| `consensus_opposing_flow` | trade flow | public trades + price | No |
| `concentrated_flow` | wallet concentration | public trades | No |
| `clustered_trades` | timing | public trades | No |
| `late_large_trade` | timing | public trades + close | No |
| `limited_activity_history` | wallet concentration | wallet market counts | No |

## Evidence families (independence)

Distinct families used for corroboration (confidence) and the family bonus (Research Priority):
**price behaviour**, **trade flow**, **order-book state**, **wallet concentration**, **timing**.
The three price components (`unusual_return`, `movement_abnormality`, `volatility_regime`) are
correlated and count as **one** price family, not three, so highly-correlated price features are
never counted as several independent lines of evidence (spec §4.4; verified by the adversarial
reviewer, who confirmed families are not triple-counted).
