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
| `spread_change` (relative spread vs baseline) | order book | persisted snapshot series | 0.08 | ~60-72% (warm) | No | Yes | Yes when present |
| `depth_change` (near-mid depth vs baseline) | order book | persisted snapshot series | 0.08 | ~60-67% (warm) | No | Yes | Yes when present |
| `volume_acceleration` (relative rise in volume) | flow | persisted snapshot series (or in-frame volumes in Replay) | 0.12 | 0% cold → present in every signal once warm | No | Yes | Yes when present |

### `volume_acceleration` — corrected finding (spec §4, §14)

An earlier revision of this pass recorded volume_acceleration as "present 0/120, Replay-only" after
capturing it at a **cold start**, and excluded it from the confidence completeness set. The running
product then showed it warming up with the microstructure snapshot series exactly like spread and
depth change: **0% at a cold start, present in 15/15 signals** once ~950 snapshots had accumulated.
So it is a **genuine, live-wired component**, not dead and not Replay-only.

Corrected decision: it is **counted in the confidence completeness set** alongside spread and depth
change (`scoring.COMPLETENESS_COMPONENTS`). A reading taken before the series has warmed is honestly
less complete and therefore lower confidence — the intended behaviour, and a concrete example of
"one day may improve component availability" (spec §14). The UI reason when it is briefly absent is
"Needs a warmed volume series from recent snapshots", not a claim that it never appears.

This correction is recorded because following the running data over a prior hypothesis is the point
of the pass: the honest state is that the live composite is a genuine seven-component model whose
microstructure components warm up over time.

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
