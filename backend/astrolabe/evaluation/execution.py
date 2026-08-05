"""Transparent depth-aware execution model (prompt section 6).

Turns a midpoint move into an *executable* move after realistic costs, so a favourable midpoint
drift smaller than the cost of trading is never counted as practical edge. Pure and side-effect
free. Missing depth stays missing: executable performance is then unavailable, never assumed to be
free (no infinite-liquidity assumption).

Cost model (all in probability points on the 0-1 outcome scale):
- spread crossing: you cross ``SPREAD_CROSS_FRACTION`` of the quoted spread on entry AND on exit.
- depth-aware slippage: consuming size against finite near-mid depth moves the price by
  ``SLIPPAGE_COEFF * (stake / near_mid_depth)``, capped at ``SLIPPAGE_CAP``, charged on entry and
  exit. When depth is missing the slippage (and thus the executable result) is unavailable.
- fees: ``FEE_RATE`` of stake per round trip (0 on Polymarket today, kept explicit).
"""
from __future__ import annotations

from dataclasses import dataclass

from .research_constants import (
    FEE_RATE,
    SLIPPAGE_CAP,
    SLIPPAGE_COEFF,
    SPREAD_CROSS_FRACTION,
    STANDARD_STAKE,
)


def _spread_cross(spread: float | None) -> float:
    return SPREAD_CROSS_FRACTION * spread if spread is not None else 0.0


def slippage_points(near_mid_depth: float | None, stake: float) -> float | None:
    """Price impact in probability points from consuming ``stake`` against ``near_mid_depth``.

    None when depth is unknown (executable performance is then unavailable, not free).
    """
    if near_mid_depth is None:
        return None
    if near_mid_depth <= 0:
        return SLIPPAGE_CAP
    return min(SLIPPAGE_CAP, SLIPPAGE_COEFF * (stake / near_mid_depth))


@dataclass(frozen=True)
class ExecutionResult:
    midpoint_move: float | None       # signed move IN the predicted direction (points)
    executable_move: float | None     # midpoint_move minus round-trip costs (points)
    entry_cost: float | None          # spread cross + slippage at entry (points)
    exit_cost: float | None           # spread cross + slippage at exit (points)
    fee: float                        # quote-unit fee for the round trip
    round_trip_cost: float | None     # total cost in points (entry_cost + exit_cost)
    unavailable_reason: str | None


def evaluate_execution(
    *,
    direction: str | None,
    entry_midpoint: float | None,
    forward_midpoint: float | None,
    entry_spread: float | None,
    entry_depth: float | None,
    forward_spread: float | None,
    forward_depth: float | None,
    stake: float = STANDARD_STAKE,
    fee_rate: float = FEE_RATE,
) -> ExecutionResult:
    """Midpoint and executable signed move for a directional call over one horizon."""
    if direction not in ("up", "down") or entry_midpoint is None or forward_midpoint is None:
        return ExecutionResult(None, None, None, None, 0.0, None, "no directional midpoint pair")

    sign = 1.0 if direction == "up" else -1.0
    midpoint_move = sign * (forward_midpoint - entry_midpoint)

    entry_slip = slippage_points(entry_depth, stake)
    # Exit depth defaults to entry depth when the forward depth was not captured, but if BOTH are
    # missing the executable result is unavailable.
    exit_depth = forward_depth if forward_depth is not None else entry_depth
    exit_slip = slippage_points(exit_depth, stake)
    if entry_slip is None or exit_slip is None:
        return ExecutionResult(
            midpoint_move, None, None, None, 0.0, None,
            "near-mid depth unavailable, so executable cost cannot be estimated",
        )

    exit_spread = forward_spread if forward_spread is not None else entry_spread
    entry_cost = _spread_cross(entry_spread) + entry_slip
    exit_cost = _spread_cross(exit_spread) + exit_slip
    round_trip = entry_cost + exit_cost
    fee = fee_rate * stake
    # Fee is in quote units; convert to points per unit stake so it is comparable to price move.
    fee_points = (fee / stake) if stake else 0.0
    executable_move = midpoint_move - round_trip - fee_points
    return ExecutionResult(
        midpoint_move=midpoint_move,
        executable_move=executable_move,
        entry_cost=entry_cost,
        exit_cost=exit_cost,
        fee=fee,
        round_trip_cost=round_trip,
        unavailable_reason=None,
    )
