"""Price-derived abnormality features for the composite anomaly score.

These use only the market's own (now genuinely available) price history, so the
composite is driven by real price behaviour rather than defaulting to order-book
imbalance when other inputs are missing. Both are pure and return ``None`` on
insufficient/degenerate data so callers degrade gracefully rather than fabricating a
value.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from .series import Number, returns


def return_burst_score(
    prices: Sequence[Number | None],
    window: int = 6,
    baseline_window: int = 40,
    min_periods: int = 15,
) -> float | None:
    """Standardised magnitude of the recent multi-step move (a sustained-move detector).

    Under a random-walk null the standard deviation of a ``k``-step cumulative return is
    ``sigma * sqrt(k)`` where ``sigma`` is the per-step return std. We report
    ``|net k-step move| / (sigma * sqrt(k))`` over the most recent ``k = window`` returns,
    with ``sigma`` estimated on the trailing ``baseline_window``. This complements the
    single-step z-score: it fires on a run of moves in one direction, not just one jump,
    which also serves as a light persistence check. ``None`` if history is too short or
    the baseline is flat.
    """
    r = returns(prices, method="diff")
    if r.size < min_periods:
        return None
    base = r[-baseline_window:] if r.size > baseline_window else r
    sigma = float(np.std(base, ddof=1))
    if sigma == 0.0 or not np.isfinite(sigma):
        return None
    k = min(window, r.size)
    net_move = float(np.sum(r[-k:]))
    scale = sigma * math.sqrt(k)
    if scale == 0.0:
        return None
    return abs(net_move) / scale


def volatility_regime(
    prices: Sequence[Number | None],
    short: int = 10,
    long: int = 40,
    min_periods: int = 20,
) -> float | None:
    """Volatility-regime shift: recent short-window return-volatility relative to a longer
    baseline, as ``short_vol / long_vol - 1``.

    Positive means recent volatility is elevated versus the market's own normal (a
    volatility spike, worth flagging); negative means it is calmer. The composite only
    counts the elevated side. ``None`` if history is too short or the baseline is flat.
    """
    r = returns(prices, method="diff")
    if r.size < min_periods:
        return None
    long_seg = r[-long:] if r.size > long else r
    short_seg = r[-short:] if r.size > short else r
    if short_seg.size < 3 or long_seg.size < min_periods:
        return None
    long_std = float(np.std(long_seg, ddof=1))
    short_std = float(np.std(short_seg, ddof=1))
    if long_std == 0.0 or not np.isfinite(long_std):
        return None
    return short_std / long_std - 1.0
