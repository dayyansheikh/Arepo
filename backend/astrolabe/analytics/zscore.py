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
    """Rolling z-score of the most recent return.

    The reference distribution is the returns over the trailing ``window`` (excluding the very
    last return is *not* required; we include it in mean/std which is the standard rolling
    definition). ``clip`` bounds the reported z to +/- ``clip`` to avoid absurd magnitudes from
    a near-zero std; set ``clip=None`` to disable.
    """
    if window < 3:
        raise ValueError("window must be >= 3")
    if min_periods < 3:
        raise ValueError("min_periods must be >= 3")

    r = returns(prices, method=method)
    if r.size < min_periods:
        return ZScore(None, None, None, None, int(r.size), "insufficient_history")

    ref = r[-window:] if r.size > window else r
    last = float(ref[-1])
    ref_w = winsorize(ref, winsor_limit)

    mean = float(np.mean(ref_w))
    std = float(np.std(ref_w, ddof=1))
    if std == 0.0 or not np.isfinite(std):
        return ZScore(None, last, mean, std, int(ref.size), "zero_variance")

    z = (last - mean) / std
    if clip is not None:
        z = float(np.clip(z, -clip, clip))
    return ZScore(float(z), last, mean, std, int(ref.size), None)
