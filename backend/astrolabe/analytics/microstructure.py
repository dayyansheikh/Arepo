"""Order-book microstructure measures: midpoint, spread, imbalance, near-mid depth.

These operate on the typed ``OrderBook`` domain model (bids sorted desc, asks asc, best first)
and never raise on empty/degenerate books — they return ``None`` for undefined quantities.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import OrderBook


@dataclass(frozen=True)
class SpreadInfo:
    midpoint: float | None
    spread: float | None            # best_ask - best_bid, in probability points
    relative_spread: float | None   # spread / midpoint (guarded)
    spread_ticks: float | None      # spread / tick_size, if tick known


def spread_info(book: OrderBook) -> SpreadInfo:
    """Midpoint, absolute spread, relative spread and spread-in-ticks for a book."""
    mid = book.midpoint
    spr = book.spread
    rel = (spr / mid) if (spr is not None and mid not in (None, 0.0)) else None
    ticks = (
        spr / book.tick_size
        if (spr is not None and book.tick_size not in (None, 0.0))
        else None
    )
    return SpreadInfo(mid, spr, rel, ticks)


@dataclass(frozen=True)
class Imbalance:
    value: float | None       # (bid_depth - ask_depth)/(bid_depth + ask_depth) in [-1, 1]
    bid_depth: float
    ask_depth: float
    levels: int               # N levels used per side


def order_book_imbalance(book: OrderBook, levels: int = 5, use_notional: bool = False) -> Imbalance:
    """Order-book imbalance over the first ``levels`` levels on each side.

    ``imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)`` in [-1, 1]; positive =
    bid-heavy (buying pressure). ``depth`` is summed size by default, or summed *notional*
    (price * size) when ``use_notional=True``. Returns ``value=None`` when both sides are empty
    (zero denominator).
    """
    if levels < 1:
        raise ValueError("levels must be >= 1")

    def depth(side_levels) -> float:
        chosen = side_levels[:levels]
        if use_notional:
            return float(sum(lvl.price * lvl.size for lvl in chosen))
        return float(sum(lvl.size for lvl in chosen))

    bid_depth = depth(book.bids)
    ask_depth = depth(book.asks)
    denom = bid_depth + ask_depth
    value = ((bid_depth - ask_depth) / denom) if denom > 0.0 else None
    return Imbalance(value, bid_depth, ask_depth, levels)


@dataclass(frozen=True)
class NearMidDepth:
    bid_depth: float
    ask_depth: float
    total_depth: float
    band: float               # +/- band around midpoint (probability points)
    defined: bool             # False if midpoint is undefined


def near_mid_depth(book: OrderBook, band: float = 0.02) -> NearMidDepth:
    """Executable size resting within ``+/- band`` of the midpoint.

    This is a *transparent, explicitly-defined* measure of near-touch liquidity, NOT a claim of
    universal "liquidity". ``band`` is in probability points (default 0.02 = 2 points). If the
    midpoint is undefined (one-sided/empty book) returns ``defined=False`` and zero depths.
    """
    if band <= 0.0:
        raise ValueError("band must be > 0")
    mid = book.midpoint
    if mid is None:
        return NearMidDepth(0.0, 0.0, 0.0, band, False)
    lo, hi = mid - band, mid + band
    bid_depth = float(sum(lvl.size for lvl in book.bids if lo <= lvl.price <= hi))
    ask_depth = float(sum(lvl.size for lvl in book.asks if lo <= lvl.price <= hi))
    return NearMidDepth(bid_depth, ask_depth, bid_depth + ask_depth, band, True)
