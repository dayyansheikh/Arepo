# Synthetic Replay: deliberate decision (spec §8)

## Decision

Synthetic Replay data is **retained only as a clearly-labelled demonstration**, and is **excluded
from every performance and edge figure**. It is never the default Replay view and is never mixed
with reconstructed or prospective samples.

## What exists

1. **Reconstructed Replay (default).** Signals rebuilt from only the price history available at a
   past cut-off. The Replay page defaults to this ("Last week's opportunities").
2. **Prospective cohorts (the real record).** Frozen weekly selections tracked forward. Currently
   **0** exist; the store holds one labelled synthetic demo cohort (`2026-W28`).
3. **Synthetic demonstration.** A deterministic dataset used for (a) the deterministic backtest
   demonstration behind a "Show the signal backtest (demonstration dataset)" disclosure on the
   Replay page, and (b) automated tests / teaching. Provenance class `synthetic`.

## Why keep it (rather than delete)

It still has genuine value: the deterministic backtest gives a reproducible, offline demonstration
of how a signal is evaluated (entry, forward move, hit definition) when no real sample is large
enough to be meaningful, and it anchors deterministic tests. It provides teaching value on a page
that is explicit that it "is not evidence of predictive skill".

## Guardrails enforced (verified this pass)

- The Replay default is reconstructed, not synthetic.
- `GET /api/cohorts/latest` now **excludes synthetic cohorts** and returns 404 with an honest
  message when only the demo exists, so demo data can never be served as the current prospective
  record (adversarial finding F#6; verified live: `/latest` → 404 while only `2026-W28 synthetic`
  exists).
- The synthetic cohort is labelled "Synthetic demonstration" in the week picker and carries a
  provenance notice; it is never aggregated into any headline performance number.
- The deterministic backtest is behind a disclosure, labelled a demonstration dataset, and its
  copy states it is not evidence of an edge.

## If it ever stops being useful

If the deterministic backtest and its tests are removed, the synthetic cohort and seed should be
deleted from the user-facing product, retaining only minimal fixtures inside the automated tests.
Until then the decision above stands.
