"""Rolling volatility of returns.

Volatility is the sample standard deviation (ddof=1) of the return series over a defined
window. For prediction-market probability series the default return method is additive
(see ``series.returns``), so volatility is expressed in probability points per step.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .series import Number, returns, winsorize


@dataclass(frozen=True)
class Volatility:
    value: float | None       # sample std of returns over the window
    window: int               # requested window (in return observations)
    n: int                    # number of return observations actually used
    sufficient: bool          # whether n >= min_periods


def rolling_volatility(
    prices: Sequence[Number | None],
    window: int = 20,
    min_periods: int = 5,
    method: str = "diff",
    winsor_limit: float = 0.0,
) -> Volatility:
    """Sample standard deviation of the most recent ``window`` returns.

    Returns ``value=None`` (and ``sufficient=False``) when fewer than ``min_periods`` return
    observations are available. Uses ddof=1 (sample std). Optionally winsorizes the returns to
    limit the influence of a single extreme observation.
    """
    if window < 2:
        raise ValueError("window must be >= 2")
    if min_periods < 2:
        raise ValueError("min_periods must be >= 2")

    r = returns(prices, method=method)
    r = r[-window:] if r.size > window else r
    if r.size < min_periods:
        return Volatility(None, window, int(r.size), False)

    r = winsorize(r, winsor_limit)
    value = float(np.std(r, ddof=1))
    return Volatility(value, window, int(r.size), True)


def volatility_series(
    prices: Sequence[Number | None],
    window: int = 20,
    min_periods: int = 5,
    method: str = "diff",
) -> list[float | None]:
    """Rolling volatility computed at each step (for charting). Uses pandas-free NumPy."""
    r = returns(prices, method=method)
    out: list[float | None] = []
    for i in range(r.size):
        seg = r[max(0, i - window + 1): i + 1]
        if seg.size < min_periods:
            out.append(None)
        else:
            out.append(float(np.std(seg, ddof=1)))
    return out
