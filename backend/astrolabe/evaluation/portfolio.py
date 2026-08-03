"""Hypothetical portfolio simulation (pure).

This is a simulation for illustration, not trading advice and not evidence of future
profitability. It uses only information available at the signal timestamp to ENTER a
position (entry price and quoted spread), and later observations only to VALUE it.

Position model (documented in docs/methodology.md):
- Fixed stake S per signal (default 100 notional).
- Enter the selected outcome at a fill that crosses half the quoted spread:
  fill = clamp(entry_price + spread/2, 0.01, 0.99). Never a price unavailable at signal.
- Contracts c = S / fill. Each contract pays 1 if the outcome resolves true, else 0.
- Round-trip fee = fee_rate * S (default 0).
Valuation:
- Resolved: payoff = c if the selected outcome won else 0 -> realised P&L = payoff - S - fee.
- Unresolved with a forward price p: mark-to-market value = c * p -> unrealised P&L.
- Unresolved with no forward price: held at cost (value = S, P&L 0), counted as pending.
"""
from __future__ import annotations

from dataclasses import dataclass

from .constants import DEFAULT_FEE_RATE, DEFAULT_STAKE, SPREAD_CROSS_FRACTION


def fill_price(entry_price: float | None, spread: float | None) -> float | None:
    """Entry fill crossing half the quoted spread. Uses only signal-time inputs."""
    if entry_price is None:
        return None
    half = (spread or 0.0) * SPREAD_CROSS_FRACTION
    return max(0.01, min(0.99, entry_price + half))


@dataclass
class PositionResult:
    entry_id: int
    stake: float
    fill: float | None
    contracts: float | None
    status: str  # "completed" | "open" | "pending"
    exit_price: float | None
    value: float          # current value of the position (realised or marked)
    pnl: float            # value - stake - fee (0 when fully pending)


@dataclass
class PortfolioResult:
    stake_per_signal: float
    fee_rate: float
    total_allocated: float
    realised_value: float
    unrealised_value: float
    pending_value: float
    completed_return: float
    completed_positions: int
    pending_positions: int
    positions: list[PositionResult]


def value_position(
    *,
    entry_id: int,
    entry_price: float | None,
    spread: float | None,
    won: bool | None,
    forward_price: float | None,
    stake: float = DEFAULT_STAKE,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> PositionResult:
    """Value one position. ``won`` is True/False when resolved, None when unresolved.
    ``forward_price`` marks an unresolved position (None if no forward price yet)."""
    fill = fill_price(entry_price, spread)
    fee = fee_rate * stake
    if fill is None:
        # No usable entry price: cannot simulate; hold flat at cost.
        return PositionResult(entry_id, stake, None, None, "pending", None, stake, 0.0)
    contracts = stake / fill
    if won is not None:
        payoff = contracts if won else 0.0
        return PositionResult(
            entry_id, stake, fill, contracts, "completed",
            1.0 if won else 0.0, payoff, payoff - stake - fee,
        )
    if forward_price is not None:
        value = contracts * forward_price
        return PositionResult(
            entry_id, stake, fill, contracts, "open", forward_price, value,
            value - stake - fee,
        )
    return PositionResult(entry_id, stake, fill, contracts, "pending", None, stake, 0.0)


def simulate_portfolio(
    positions: list[PositionResult],
    *,
    stake: float = DEFAULT_STAKE,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> PortfolioResult:
    realised = sum(p.value for p in positions if p.status == "completed")
    unrealised = sum(p.value for p in positions if p.status == "open")
    pending = sum(p.value for p in positions if p.status == "pending")
    completed_return = sum(p.pnl for p in positions if p.status == "completed")
    n_completed = sum(1 for p in positions if p.status == "completed")
    return PortfolioResult(
        stake_per_signal=stake,
        fee_rate=fee_rate,
        total_allocated=stake * len(positions),
        realised_value=realised,
        unrealised_value=unrealised,
        pending_value=pending,
        completed_return=completed_return,
        completed_positions=n_completed,
        pending_positions=len(positions) - n_completed,
        positions=positions,
    )
