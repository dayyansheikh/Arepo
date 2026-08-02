"""Price-movement measures.

All functions are pure and return ``None`` when there is insufficient data rather than
raising, so callers can degrade gracefully. Movements on probability series are reported in
*percentage points* (e.g. 0.05 = +5 probability points) unless a relative measure is requested.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .series import Number, clean


@dataclass(frozen=True)
class Movement:
    """A movement measurement over a window."""

    absolute: float | None          # percentage-point change (p_end - p_start), in [-1, 1]
    relative: float | None          # (p_end - p_start) / p_start, guarded for p_start == 0
    start_price: float | None
    end_price: float | None
    n: int                          # number of finite observations used


def movement(prices: Sequence[Number | None]) -> Movement:
    """Total movement from the first to the last finite price in the series."""
    arr = clean(prices)
    if arr.size < 2:
        first = float(arr[0]) if arr.size == 1 else None
        return Movement(None, None, first, first, int(arr.size))
    start, end = float(arr[0]), float(arr[-1])
    absolute = end - start
    relative = (end - start) / start if start != 0.0 else None
    return Movement(absolute, relative, start, end, int(arr.size))


def window_movement(prices: Sequence[Number | None], window: int) -> Movement:
    """Movement over the most recent ``window`` observations.

    ``window`` is a count of observations. If fewer are available, uses what exists.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    arr = clean(prices)
    tail = arr[-(window + 1):] if arr.size > window else arr
    return movement(tail)


def percentage_point_change(p_start: float | None, p_end: float | None) -> float | None:
    """Simple helper: additive change between two prices."""
    if p_start is None or p_end is None:
        return None
    return float(p_end) - float(p_start)
