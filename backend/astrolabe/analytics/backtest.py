"""Deterministic, look-ahead-safe backtest of the anomaly signal over replayed data.

The single most important property here is **no look-ahead**: a signal at frame *i* is computed
using only frames ``0..i``; its outcome is evaluated using only frames ``i+1..i+H``. Signal
generation data and evaluation data never overlap. This is asserted in the loop.

Reported honestly (per spec §9): thresholds, horizon, sample size, missing observations,
assumptions, and survivorship limitations. No profitability is claimed — this measures whether
a flagged move tends to be followed by further movement in the same direction on this dataset.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..replay.player import ReplayPlayer, default_player
from .anomaly import RawComponents, composite_anomaly_score
from .microstructure import near_mid_depth, order_book_imbalance, spread_info
from .zscore import rolling_zscore


@dataclass
class SignalEvent:
    market_id: str
    token_id: str
    frame: int
    strength: float
    zscore: float | None
    direction: str | None           # "up" | "down"
    entry_price: float
    forward_price: float | None     # price H frames later (None if truncated)
    forward_move: float | None      # signed percentage-point change entry -> forward
    followed_through: bool | None   # moved >= move_threshold in the signalled direction


@dataclass
class BacktestResult:
    # configuration / assumptions (surfaced for honesty)
    strength_threshold: float
    move_threshold: float
    horizon: int
    zscore_window: int
    min_history: int
    # outcomes
    sample_size: int
    evaluated: int                  # signals with enough forward data to score
    missing_observations: int       # signals dropped for insufficient forward data
    hit_rate: float | None
    false_positive_rate: float | None
    avg_forward_move_directional: float | None   # mean(direction * forward_move)
    avg_abs_forward_move: float | None
    events: list[SignalEvent] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


def _frame_price(player: ReplayPlayer, market_id: str, token_id: str, index: int) -> float | None:
    """Price at a specific frame (last trade, else book midpoint), frame-index aligned.

    Returns None when the frame has no derivable price, so callers can align entry/forward
    prices to raw frame indices without the misalignment that a filtered price array causes.
    """
    snap = player.snapshot_at(market_id, token_id, index)
    if snap.last_trade_price is not None:
        return snap.last_trade_price
    return snap.book.midpoint if snap.book else None


def _volume_deltas(volumes: list[float]) -> list[float]:
    """Per-frame incremental volume from a (roughly cumulative) volume series."""
    out = [0.0]
    for i in range(1, len(volumes)):
        out.append(max(0.0, volumes[i] - volumes[i - 1]))
    return out


def _components_at(player: ReplayPlayer, market_id: str, token_id: str, i: int,
                  zscore_window: int, min_history: int) -> tuple[RawComponents, float | None]:
    """Compute anomaly components using ONLY frames 0..i (look-ahead-safe)."""
    prices = player.prices(market_id, token_id, upto_index=i)
    if len(prices) < min_history:
        return RawComponents(), None

    z = rolling_zscore(prices, window=zscore_window, min_periods=min_history).value

    # Volume acceleration: recent incremental volume vs an earlier baseline (both <= i).
    vols = player.volumes(market_id, token_id, upto_index=i)
    deltas = _volume_deltas(vols)
    vol_accel = None
    if len(deltas) >= 6:
        recent = float(np.mean(deltas[-2:]))
        baseline = float(np.mean(deltas[-6:-2])) or 1e-9
        vol_accel = (recent - baseline) / baseline

    book = player.book_at(market_id, token_id, i)
    imb = order_book_imbalance(book, levels=5).value

    # Spread / depth change vs a trailing baseline of the previous few frames.
    spr_now = spread_info(book).spread
    depth_now = near_mid_depth(book, band=0.02).total_depth
    prev_spreads, prev_depths = [], []
    for j in range(max(0, i - 5), i):
        b = player.book_at(market_id, token_id, j)
        s = spread_info(b).spread
        if s is not None:
            prev_spreads.append(s)
        prev_depths.append(near_mid_depth(b, band=0.02).total_depth)
    spread_change = None
    if spr_now is not None and prev_spreads:
        base = float(np.mean(prev_spreads)) or 1e-9
        spread_change = (spr_now - base) / base
    depth_change = None
    if prev_depths:
        base = float(np.mean(prev_depths)) or 1e-9
        depth_change = (depth_now - base) / base

    raw = RawComponents(
        zscore=z,
        volume_acceleration=vol_accel,
        imbalance=imb,
        spread_change=spread_change,
        depth_change=depth_change,
    )
    return raw, z


def run_backtest(
    player: ReplayPlayer | None = None,
    *,
    strength_threshold: float = 0.30,
    move_threshold: float = 0.02,
    horizon: int = 5,
    zscore_window: int = 20,
    min_history: int = 8,
) -> BacktestResult:
    """Run the anomaly-signal backtest across all markets/tokens in the dataset."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")  # real guard (assert is stripped under -O)
    player = player or default_player()
    events: list[SignalEvent] = []
    missing = 0

    for market_id in player.market_ids():
        n = player.n_frames(market_id)
        for token_id in player.token_ids(market_id):
            # FRAME-ALIGNED price array (one entry per frame, None if no price that frame).
            # ``player.prices`` is a *filtered* dense array and MUST NOT be indexed by frame
            # number — doing so misaligns entry/forward and can leak a later frame's price
            # into "entry" when an earlier frame has no price.
            frame_prices = [_frame_price(player, market_id, token_id, k) for k in range(n)]
            for i in range(n):
                entry_price = frame_prices[i]
                if entry_price is None:
                    continue  # cannot anchor a signal on a frame with no price
                raw, z = _components_at(
                    player, market_id, token_id, i, zscore_window, min_history
                )
                if z is None:
                    continue
                strength, _ = composite_anomaly_score(raw)
                if strength < strength_threshold:
                    continue
                direction = "up" if (z or 0) > 0 else "down" if (z or 0) < 0 else None

                # --- evaluation window is STRICTLY after the signal frame ---
                fwd_idx = i + horizon
                forward_price = frame_prices[fwd_idx] if fwd_idx < n else None
                if forward_price is None:
                    missing += 1
                    events.append(SignalEvent(
                        market_id, token_id, i, strength, z, direction,
                        entry_price, None, None, None,
                    ))
                    continue
                assert fwd_idx > i  # defensive; real guard is the horizon>=1 check above
                forward_move = forward_price - entry_price
                dir_sign = 1.0 if direction == "up" else -1.0 if direction == "down" else 0.0
                followed = bool(dir_sign * forward_move >= move_threshold)
                events.append(SignalEvent(
                    market_id, token_id, i, strength, z, direction,
                    entry_price, forward_price, forward_move, followed,
                ))

    scored = [e for e in events if e.followed_through is not None]
    evaluated = len(scored)
    hits = sum(1 for e in scored if e.followed_through)
    hit_rate = (hits / evaluated) if evaluated else None
    no_follow = sum(
        1 for e in scored
        if e.forward_move is not None and abs(e.forward_move) < move_threshold
    )
    fp_rate = (no_follow / evaluated) if evaluated else None
    dir_moves = [
        (1.0 if e.direction == "up" else -1.0) * e.forward_move
        for e in scored if e.forward_move is not None and e.direction
    ]
    abs_moves = [abs(e.forward_move) for e in scored if e.forward_move is not None]

    return BacktestResult(
        strength_threshold=strength_threshold,
        move_threshold=move_threshold,
        horizon=horizon,
        zscore_window=zscore_window,
        min_history=min_history,
        sample_size=len(events),
        evaluated=evaluated,
        missing_observations=missing,
        hit_rate=hit_rate,
        false_positive_rate=fp_rate,
        avg_forward_move_directional=(float(np.mean(dir_moves)) if dir_moves else None),
        avg_abs_forward_move=(float(np.mean(abs_moves)) if abs_moves else None),
        events=events,
        assumptions=[
            f"Signal fires when composite anomaly strength >= {strength_threshold}.",
            f"A 'hit' means price moved >= {move_threshold} (probability points) in the "
            f"signalled direction within {horizon} frames.",
            "Signal generation uses frames 0..i; evaluation uses frames i+1..i+H only.",
            "No transaction costs, slippage or fees are modelled; this is not a P&L simulation.",
        ],
        limitations=[
            "Deterministic synthetic demo dataset — results do not generalise to live markets.",
            "Small sample; no survivorship correction (markets that closed are not repopulated).",
            "Directional 'hit rate' measures follow-through only, NOT profitability or alpha.",
        ],
    )
