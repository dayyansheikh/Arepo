"""Build an immutable signal snapshot from a market + its computed analytics.

Pure and side-effect free: given the market metadata and the ``TokenAnalytics`` that
enrichment already produced, it captures exactly the inputs available at the signal
timestamp. Crucially the entry price is defined only from information present at that
moment, never a later price (spec section 14).
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime

from ..domain.models import Market
from ..service.enrich import TokenAnalytics

_OBS_RE = re.compile(r"(\d+)")


def make_snapshot_ref(market_id: str, token_id: str, captured_at: datetime, version: str) -> str:
    """Stable identity hash so re-ingesting the same instant dedupes to one snapshot."""
    key = f"{market_id}|{token_id}|{captured_at.isoformat()}|{version}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _lookback_from_window(window: str | None) -> int | None:
    if not window:
        return None
    m = _OBS_RE.search(window)
    return int(m.group(1)) if m else None


def _entry_price(ta: TokenAnalytics) -> float | None:
    """The price a position would enter at, using only signal-time information.

    Prefer the two-sided-book midpoint; fall back to the implied probability (last/mid
    derived) when no book is present. Never a later observation.
    """
    if ta.midpoint is not None:
        return ta.midpoint
    if ta.best_bid is not None and ta.best_ask is not None:
        return (ta.best_bid + ta.best_ask) / 2.0
    return ta.implied


@dataclass
class SnapshotInput:
    snapshot_ref: str
    calculation_version: str
    captured_at: datetime
    source_timestamp: datetime | None
    market_id: str
    condition_id: str | None
    event_id: str | None
    token_id: str
    market_question: str
    outcome_name: str
    direction: str | None
    strength: float
    confidence: float
    data_quality: str
    value: float | None
    entry_price: float | None
    best_bid: float | None
    best_ask: float | None
    midpoint: float | None
    spread: float | None
    volume: float | None
    near_mid_depth: float | None
    lookback_size: int | None
    expected_close: datetime | None
    component_scores: list = field(default_factory=list)


def build_snapshot_input(
    market: Market,
    ta: TokenAnalytics,
    *,
    captured_at: datetime,
    calculation_version: str,
    source_timestamp: datetime | None = None,
    event_id: str | None = None,
) -> SnapshotInput:
    sig = ta.signal
    outcome_name = next(
        (o.name for o in market.outcomes if o.token_id == ta.token_id), ta.token_id
    )
    components = [
        {
            "name": c.name,
            "raw_value": c.raw_value,
            "normalized_value": c.normalized_value,
            "weight": c.weight,
        }
        for c in sig.components
    ]
    return SnapshotInput(
        snapshot_ref=make_snapshot_ref(
            market.id, ta.token_id, captured_at, calculation_version
        ),
        calculation_version=calculation_version,
        captured_at=captured_at,
        source_timestamp=source_timestamp,
        market_id=market.id,
        condition_id=market.condition_id or None,
        event_id=event_id,
        token_id=ta.token_id,
        market_question=market.question,
        outcome_name=outcome_name,
        direction=sig.direction,
        strength=float(sig.strength),
        confidence=float(sig.confidence),
        data_quality=ta.data_quality,
        value=sig.value,
        entry_price=_entry_price(ta),
        best_bid=ta.best_bid,
        best_ask=ta.best_ask,
        midpoint=ta.midpoint,
        spread=ta.spread,
        volume=ta.volume,
        near_mid_depth=ta.near_mid_depth,
        lookback_size=_lookback_from_window(sig.window),
        expected_close=market.end_date,
        component_scores=components,
    )
