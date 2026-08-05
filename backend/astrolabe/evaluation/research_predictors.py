"""Prospective baselines and feature-ablation directions (prompt sections 8, 9).

Every predictor maps a FROZEN research entry to a directional call (up | down | None) using only
information frozen at the cut-off, so all of them are scored on the exact same observations. This
is where the central question is answered mechanically: because Arepo's direction is the sign of
the latest-return z-score, "momentum", "price-only" and "Arepo" share a direction by construction,
and dropping the non-price families leaves the direction unchanged. The ablation makes that visible
rather than asserting Arepo adds value.

Pure and deterministic. Scoring reuses ``replay_stats.classify_directional`` so flats are handled
identically for every predictor (flats excluded from the hit-rate denominator).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class EntryView:
    """The subset of a frozen entry a predictor may use (all known at the cut-off)."""

    direction: str | None            # Arepo's directional call
    momentum_direction: str | None   # z-score sign (Arepo's price signal)
    orderbook_direction: str | None
    tradeflow_direction: str | None
    entry_price: float | None        # implied probability at the cut-off
    evidence_families: tuple[str, ...] = ()


def _implied(e: EntryView) -> str | None:
    if e.entry_price is None:
        return None
    return "up" if e.entry_price > 0.5 else "down"


def _first(*vals: str | None) -> str | None:
    for v in vals:
        if v in ("up", "down"):
            return v
    return None


# name -> (direction function, metadata). Metadata documents inputs/type (prompt section 8).
@dataclass(frozen=True)
class PredictorSpec:
    name: str
    fn: Callable[[EntryView], str | None]
    kind: str            # "directional" | "flat"
    inputs: str
    note: str = ""


BASELINES: dict[str, PredictorSpec] = {
    "no_change": PredictorSpec("No change", lambda e: None, "flat", "none",
                               "predicts flat; correct when |move| <= FLAT_EPS"),
    "always_up": PredictorSpec("Always up", lambda e: "up", "directional", "none"),
    "always_down": PredictorSpec("Always down", lambda e: "down", "directional", "none"),
    "momentum": PredictorSpec("Momentum", lambda e: e.momentum_direction, "directional",
                              "latest-return z-score sign"),
    "price_z_only": PredictorSpec("Price z-score only", lambda e: e.momentum_direction,
                                  "directional", "z-score sign",
                                  "same price signal as Arepo's direction (documented)"),
    "current_implied": PredictorSpec("Current implied", _implied, "directional",
                                     "cut-off implied probability"),
    "order_book_only": PredictorSpec("Order-book only", lambda e: e.orderbook_direction,
                                     "directional", "near-touch imbalance sign"),
    "trade_flow_only": PredictorSpec("Trade-flow only", lambda e: e.tradeflow_direction,
                                     "directional", "net aggressive flow sign"),
    "full_arepo": PredictorSpec("Full Arepo", lambda e: e.direction, "directional",
                                "full composite direction"),
    "full_arepo_no_momentum": PredictorSpec(
        "Full Arepo without momentum",
        lambda e: _first(e.orderbook_direction, e.tradeflow_direction),
        "directional", "order-book then trade-flow direction",
        "removes the price/momentum signal; falls back to microstructure evidence",
    ),
}


# Ablation variants (prompt section 9). Each yields a direction from the frozen entry.
ABLATIONS: dict[str, PredictorSpec] = {
    "full_model": PredictorSpec("Full model", lambda e: e.direction, "directional", "all families"),
    "without_price": PredictorSpec(
        "Full model without price features",
        lambda e: _first(e.orderbook_direction, e.tradeflow_direction),
        "directional", "microstructure only"),
    "without_momentum": PredictorSpec(
        "Full model without momentum",
        lambda e: _first(e.orderbook_direction, e.tradeflow_direction),
        "directional", "microstructure only"),
    "without_order_book": PredictorSpec(
        "Full model without order book",
        lambda e: _first(e.momentum_direction, e.tradeflow_direction),
        "directional", "price + flow"),
    "without_trade_flow": PredictorSpec(
        "Full model without trade flow",
        lambda e: _first(e.momentum_direction, e.orderbook_direction),
        "directional", "price + order book"),
    "price_only": PredictorSpec("Price only", lambda e: e.momentum_direction, "directional",
                                "z-score sign"),
    "momentum_only": PredictorSpec("Momentum only", lambda e: e.momentum_direction, "directional",
                                   "z-score sign"),
    "order_book_only": PredictorSpec("Order-book only", lambda e: e.orderbook_direction,
                                     "directional", "imbalance sign"),
    "trade_flow_only": PredictorSpec("Trade-flow only", lambda e: e.tradeflow_direction,
                                     "directional", "flow sign"),
}


def agreement_rate(a: list[str | None], b: list[str | None]) -> float | None:
    """Fraction of entries where two predictors made the same directional call (both non-None)."""
    both = [(x, y) for x, y in zip(a, b, strict=False)
            if x in ("up", "down") and y in ("up", "down")]
    if not both:
        return None
    return round(sum(1 for x, y in both if x == y) / len(both), 3)
