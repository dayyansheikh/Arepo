# Cross-surface consistency contract (spec §17)

For the same market/signal, these must agree across Signal Lab, Market Detail, the Opportunity
Board, alerts and Replay. Contradictions are test failures
(`backend/tests/unit/test_cross_surface.py`), not silent UI differences.

| Property | Signal Lab | Market Detail | Opportunity Board | Alerts | Replay (reconstructed) | Rule |
| --- | --- | --- | --- | --- | --- | --- |
| Direction | signal.direction | signal.direction | card.direction (gated) | via card | entry.direction | Same `direction` field. |
| Directional gate | `has_directional_view(n_families, strength)` via `signal.n_families` | same | `has_directional_view` server-side | same gate + stricter confidence/quality | reconstructed price-only gate | One `has_directional_view` rule everywhere. Frontend `directionalVerdict` now consumes `signal.n_families`. |
| Strength | signal.strength | signal.strength | card.signal_strength | via card | entry.strength | Same composite strength. |
| **Confidence** | `reliability_confidence` | `reliability_confidence` | `reliability_confidence` | gate on `reliability_confidence` | reliability-at-cut-off | **All surfaces display the reliability confidence; none shows the raw 1.00 data-quality term.** |
| Evidence families | `signal.n_families` (price + book) | same | `n_families` incl. trade flow | via card | price-only families | Signal Lab / Market Detail identical; Board may ADD live trade-flow families (documented exception). |
| Qualification | directional gate | directional gate | `directional` + view filter | gate + thresholds | historical gate | Board default = directional only. |

## The one allowed difference

The Opportunity Board fetches live public trades; Signal Lab and Market Detail do not. So the Board
can legitimately show a higher evidence-family count and confidence for the same market when trade
flow adds a family. This is the only permitted divergence and its cause is explicit. All other
surfaces (Signal Lab, Market Detail, Replay confidence-at-cut-off) use the identical
`reliability_confidence` definition and the identical directional gate.

## Executable checks (`test_cross_surface.py`)

1. Signal Lab reliability confidence is never the raw 100% data-quality term (`rel <= dq`, `< 1.0`).
2. With no trade flow, `signal_reliability(sig)` equals `score_opportunity(sig, []).confidence` and
   `.n_families` — Signal Lab and the Board agree exactly when the Board has no extra trade data.
3. `has_directional_view` matches the exact rule the frontend `directionalVerdict` now mirrors via
   `signal.n_families`.

## Timestamp correctness (Replay)

Replay shows strength, confidence and Research Priority AS AT the cut-off, reconstructed price-only,
and the confidence uses the same reliability definition (so it is honestly low for the thin
historical evidence, not the constant data-quality term it showed before this pass).
