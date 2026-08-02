"""Implied probability from contract prices.

A binary contract that pays 1 unit on "Yes" trades at a price ``p`` that is treated as an
**approximate, risk-neutral, market-implied probability** of the event. Caveats (surfaced in
the UI and docs/methodology.md):
- It is contaminated by the bid/ask spread and any fees; the mid-price is a better estimate
  than a one-sided trade price.
- It is risk-neutral, not a calibrated real-world forecast, and can be biased by liquidity,
  limits to arbitrage and market sentiment.
- Across the outcomes of one market the prices need not sum to exactly 1 (spread/imbalance);
  a normalised view divides by the sum to remove that "overround".
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ImpliedProbability:
    value: float | None        # clamped to [0, 1]
    source: str                # e.g. "midpoint" | "last" | "gamma"
    caveat: str


def implied_probability(price: float | None, source: str = "midpoint") -> ImpliedProbability:
    """Treat a price as an implied probability, clamped to [0, 1]."""
    if price is None:
        return ImpliedProbability(None, source, "no price available")
    value = max(0.0, min(1.0, float(price)))
    caveat = (
        "Approximate risk-neutral, spread/fee-contaminated estimate; not a calibrated forecast."
    )
    return ImpliedProbability(value, source, caveat)


def normalized_outcome_probabilities(prices: Sequence[float | None]) -> list[float | None]:
    """Normalise a set of outcome prices to sum to 1, removing the 'overround'.

    Missing prices (None) stay None and are excluded from the denominator. If the finite prices
    sum to 0, returns the inputs clamped without scaling (cannot normalise).
    """
    clamped = [None if p is None else max(0.0, min(1.0, float(p))) for p in prices]
    total = sum(p for p in clamped if p is not None)
    if total <= 0.0:
        return clamped
    return [None if p is None else p / total for p in clamped]
