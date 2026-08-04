"""Standardised movement score — the rolling z-score of returns.

The z-score answers: *how unusual is the most recent move relative to this market's own recent
behaviour?*  ``z = (r_last - mean(window)) / std(window)``.

Edge cases handled explicitly (per spec):
- **Insufficient history**: fewer than ``min_periods`` returns  -> ``value=None``.
- **Zero variance**: a flat window (std == 0) -> ``value=None`` with ``reason="zero_variance"``
  (we do not emit +/-inf; a market that has not moved has no meaningful standardised move).
- **Missing values**: None/NaN prices are dropped pairwise in the return calculation.
- **Extreme outliers**: optional winsorization of the *reference* window so one prior spike
  does not inflate the std and mask a genuine new move.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .series import Number, returns, winsorize


@dataclass(frozen=True)
class ZScore:
    value: float | None       # standardized latest return; None if not computable
    last_return: float | None
    mean: float | None
    std: float | None
    n: int                    # reference return observations used
    reason: str | None        # why value is None, if applicable


def rolling_zscore(
    prices: Sequence[Number | None],
    window: int = 20,
    min_periods: int = 8,
    method: str = "diff",
    winsor_limit: float = 0.0,
    clip: float | None = 10.0,
) -> ZScore:
    """Rolling z-score of the most recent return, scored against a baseline that EXCLUDES it.

    The return being measured (the last return) must not appear in its own reference mean/std:
    including it pulls the baseline towards the very event we are trying to detect and shrinks
    large moves (deep-research-report.md, Arepo audit, "The current observation appears in its own
    z-score reference window"). So the baseline is the trailing returns over ``t-L`` through
    ``t^-`` and the score is ``(r_last - mean_baseline) / std_baseline``. ``clip`` bounds the
    reported z to +/- ``clip`` to avoid absurd magnitudes from a near-zero std; ``clip=None``
    disables it.
    """
    if window < 3:
        raise ValueError("window must be >= 3")
    if min_periods < 3:
        raise ValueError("min_periods must be >= 3")

    r = returns(prices, method=method)
    # We need the last return PLUS at least ``min_periods`` prior returns for the baseline.
    if r.size < min_periods + 1:
        return ZScore(None, None, None, None, int(r.size), "insufficient_history")

    last = float(r[-1])
    # Baseline: the trailing ``window`` returns strictly BEFORE the last one (t-L .. t^-).
    baseline = r[-(window + 1):-1] if r.size > window else r[:-1]
    baseline_w = winsorize(baseline, winsor_limit)

    mean = float(np.mean(baseline_w))
    std = float(np.std(baseline_w, ddof=1))

    if std == 0.0 or not np.isfinite(std):
        # A flat baseline. If the last return is also ~0 the market is genuinely unchanged and
        # has no standardised move (correct abstention). But a real move off a perfectly flat
        # baseline is *maximally* unusual, not undefined: report a clipped, signed extreme so a
        # flat-then-jump (the case we most want to detect) yields a directional reading rather
        # than None. This is what makes the baseline-exclusion fix improve, not harm, coverage.
        move = last - mean
        if abs(move) <= 1e-12:
            return ZScore(None, last, mean, std, int(baseline.size), "zero_variance")
        extreme = float(clip) if clip is not None else 10.0
        z = extreme if move > 0 else -extreme
        return ZScore(z, last, mean, std, int(baseline.size), "flat_baseline_move")

    z = (last - mean) / std
    if clip is not None:
        z = float(np.clip(z, -clip, clip))
    return ZScore(float(z), last, mean, std, int(baseline.size), None)
