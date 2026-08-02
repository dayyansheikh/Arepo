"""Return/series primitives shared by the analytics modules.

Design note — why *first differences* by default for prediction-market prices
----------------------------------------------------------------------------
A binary contract price is a probability in [0, 1]. Conventional *relative* returns
``(p_t - p_{t-1}) / p_{t-1}`` and log returns explode near the 0/1 boundaries (a move from
0.01 to 0.02 is a +100% "return" that is not economically meaningful on a probability scale).
We therefore default to **additive returns** (first differences, in probability points),
``r_t = p_t - p_{t-1}``, which are the natural scale for a bounded probability series and keep
the downstream z-score interpretable ("this move is k std-devs vs recent moves").

Relative and log returns are still provided (``method="simple"|"log"``) for reference and are
documented in ``docs/methodology.md``; callers must opt in.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

Number = float | int


def to_array(values: Sequence[Number | None]) -> np.ndarray:
    """Convert a sequence (possibly containing None) to a float array with NaN for None."""
    return np.array([np.nan if v is None else float(v) for v in values], dtype=float)


def clean(values: Sequence[Number | None]) -> np.ndarray:
    """Drop None/NaN, returning a finite float array (order preserved)."""
    arr = to_array(values)
    return arr[np.isfinite(arr)]


def returns(prices: Sequence[Number | None], method: str = "diff") -> np.ndarray:
    """Compute a return series from a price series.

    Parameters
    ----------
    prices : sequence of price observations (probabilities in [0, 1]); None/NaN allowed and
        are dropped *pairwise* so a single gap does not fabricate a spurious jump.
    method : "diff" (additive, default), "simple" (relative), or "log".

    Returns an array of length ``max(0, n_finite - 1)``. Empty if fewer than 2 finite prices.
    """
    arr = clean(prices)
    if arr.size < 2:
        return np.array([], dtype=float)
    prev, cur = arr[:-1], arr[1:]
    if method == "diff":
        return cur - prev
    if method == "simple":
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.where(prev != 0.0, (cur - prev) / prev, np.nan)
        return out[np.isfinite(out)]
    if method == "log":
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.where((prev > 0.0) & (cur > 0.0), np.log(cur / prev), np.nan)
        return out[np.isfinite(out)]
    raise ValueError(f"unknown return method: {method!r}")


def winsorize(values: np.ndarray, limit: float = 0.0) -> np.ndarray:
    """Symmetrically clip extreme values to the given quantile on each tail.

    ``limit`` is the fraction clipped per tail (e.g. 0.05 clips the top/bottom 5%). ``0``
    disables winsorization. Used to keep single outliers from dominating a rolling std.
    """
    if limit <= 0.0 or values.size == 0:
        return values
    lo, hi = np.quantile(values, [limit, 1.0 - limit])
    return np.clip(values, lo, hi)
