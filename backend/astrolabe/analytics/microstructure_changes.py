"""Microstructure CHANGE features from a persisted snapshot series (spec §7).

'Faster trading activity' (volume acceleration), 'Spread change' and 'Available depth change'
cannot be computed from a single live order-book snapshot: they need a time series of prior
snapshots to difference against. The live read-only path never stored one, so these features were
always empty. These pure functions compute each change from a stored series and return ``None``
(genuinely missing, never silently 0) when the series is too short. They must NEVER be fed a
series reconstructed from current books for a historical timestamp (report Arepo audit): the
caller is responsible for provenance.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

# Minimum prior snapshots before a baseline is trustworthy.
MIN_BASELINE_SNAPSHOTS = 3


@dataclass(frozen=True)
class MicrostructureChanges:
    """Change features derived from a snapshot series; any field may be ``None`` (missing)."""

    spread_change: float | None = None
    depth_change: float | None = None
    volume_acceleration: float | None = None

    def any_present(self) -> bool:
        return any(
            v is not None
            for v in (self.spread_change, self.depth_change, self.volume_acceleration)
        )


def _relative_change(current: float | None, baseline: Sequence[float]) -> float | None:
    """Relative change of ``current`` vs the median of a prior ``baseline`` series."""
    if current is None:
        return None
    vals = [float(v) for v in baseline if v is not None]
    if len(vals) < MIN_BASELINE_SNAPSHOTS:
        return None
    ref = float(np.median(vals))
    if ref <= 0:
        return None
    return (float(current) - ref) / ref


def spread_change(current_spread: float | None, prior_spreads: Sequence[float]) -> float | None:
    """Relative widening (+) or tightening (-) of the spread vs its recent baseline."""
    return _relative_change(current_spread, prior_spreads)


def depth_change(current_depth: float | None, prior_depths: Sequence[float]) -> float | None:
    """Relative rise (+) or fall (-) in near-mid depth vs its recent baseline."""
    return _relative_change(current_depth, prior_depths)


def volume_acceleration(cumulative_volumes: Sequence[float | None]) -> float | None:
    """Acceleration of trading from a series of CUMULATIVE volume readings.

    Differences the cumulative series into per-interval volumes, then compares the most recent
    interval(s) with an earlier baseline. Returns ``None`` when the series is too short. This is
    the series-based replacement for the old live path that always received an empty volume list.
    """
    vals = [float(v) for v in cumulative_volumes if v is not None]
    if len(vals) < MIN_BASELINE_SNAPSHOTS + 2:
        return None
    deltas = [max(0.0, vals[i] - vals[i - 1]) for i in range(1, len(vals))]
    if len(deltas) < MIN_BASELINE_SNAPSHOTS + 1:
        return None
    recent = float(np.mean(deltas[-2:]))
    baseline = float(np.mean(deltas[:-2]))
    if baseline <= 0:
        return None
    return (recent - baseline) / baseline


def changes_from_series(
    *,
    current_spread: float | None,
    current_depth: float | None,
    prior_spreads: Sequence[float],
    prior_depths: Sequence[float],
    cumulative_volumes: Sequence[float | None],
) -> MicrostructureChanges:
    """Compute all three change features from a stored series (each may be ``None``)."""
    return MicrostructureChanges(
        spread_change=spread_change(current_spread, prior_spreads),
        depth_change=depth_change(current_depth, prior_depths),
        volume_acceleration=volume_acceleration(cumulative_volumes),
    )
