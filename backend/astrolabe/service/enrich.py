"""Analytics enrichment: raw per-token inputs -> explained OutcomeView + anomaly Signal.

Used identically by live, cached and replay modes so the analytics are provably mode-agnostic.
All inputs are optional/defensive; missing data degrades confidence rather than raising.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from ..analytics.abnormality import return_burst_score, volatility_regime
from ..analytics.anomaly import RawComponents, build_anomaly_signal, composite_anomaly_score
from ..analytics.implied import implied_probability, normalized_outcome_probabilities
from ..analytics.microstructure import near_mid_depth, order_book_imbalance, spread_info
from ..analytics.microstructure_changes import MicrostructureChanges
from ..analytics.movement import window_movement
from ..analytics.quality import assess_quality
from ..analytics.volatility import rolling_volatility
from ..analytics.zscore import rolling_zscore
from ..config import get_settings
from ..domain.models import Market, OrderBook, Signal
from .schemas import MarketCard, OutcomeView

MOVEMENT_WINDOW = 4        # recent observations used for "recent movement"
VOL_WINDOW = 20
Z_WINDOW = 20
Z_MIN_HISTORY = 8


@dataclass
class TokenAnalytics:
    token_id: str
    implied: float | None
    best_bid: float | None
    best_ask: float | None
    midpoint: float | None
    spread: float | None
    relative_spread: float | None
    imbalance: float | None
    near_mid_depth: float | None
    volume: float | None
    volatility: float | None
    movement: float | None
    zscore: float | None
    signal: Signal
    confidence: float
    data_quality: str
    data_age_seconds: float | None = None


def _volume_acceleration(volumes: list[float] | None) -> float | None:
    if not volumes or len(volumes) < 6:
        return None
    deltas = [max(0.0, volumes[i] - volumes[i - 1]) for i in range(1, len(volumes))]
    if len(deltas) < 4:
        return None
    recent = float(np.mean(deltas[-2:]))
    baseline = float(np.mean(deltas[-6:-2])) if len(deltas) >= 6 else float(np.mean(deltas[:-2]))
    baseline = baseline or 1e-9
    return (recent - baseline) / baseline


def compute_token_analytics(
    *,
    token_id: str,
    market_id: str,
    prices: list[float],
    book: OrderBook | None,
    volumes: list[float] | None = None,
    gamma_price: float | None = None,
    data_age_seconds: float | None = None,
    changes: MicrostructureChanges | None = None,
) -> TokenAnalytics:
    """Compute the full analytics bundle for one outcome token.

    ``changes`` carries spread-change / depth-change / volume-acceleration computed from a
    persisted snapshot SERIES (spec §7). When absent, those components stay ``None`` (missing,
    never zero); they are never reconstructed from a single current snapshot.
    """
    si = spread_info(book) if book else None
    mid = si.midpoint if si else None
    implied = implied_probability(
        mid if mid is not None else (prices[-1] if prices else gamma_price),
        source="midpoint" if mid is not None else "last",
    ).value

    imb = order_book_imbalance(book).value if book else None
    nmd = near_mid_depth(book).total_depth if book else None

    vol = rolling_volatility(prices, window=VOL_WINDOW, min_periods=5).value if prices else None
    z = (
        rolling_zscore(prices, window=Z_WINDOW, min_periods=Z_MIN_HISTORY).value
        if prices else None
    )
    mv = window_movement(prices, window=MOVEMENT_WINDOW).absolute if len(prices) >= 2 else None
    # Volume acceleration: prefer the series-based value from persisted snapshots (spec §7); fall
    # back to the in-frame ``volumes`` list (populated only in replay mode).
    vol_accel = (changes.volume_acceleration if changes else None)
    if vol_accel is None:
        vol_accel = _volume_acceleration(volumes)
    spread_change = changes.spread_change if changes else None
    depth_change = changes.depth_change if changes else None

    # Price-behaviour abnormality features, computed from the market's own history so the
    # composite is led by real price movement rather than order-book imbalance alone.
    burst = return_burst_score(prices) if prices else None
    vr = volatility_regime(prices) if prices else None
    vr_elevated = max(0.0, vr) if vr is not None else None  # only a volatility spike counts

    raw = RawComponents(
        zscore=z,
        movement_abnormality=burst,
        volatility_regime=vr_elevated,
        volume_acceleration=vol_accel,
        imbalance=imb,
        spread_change=spread_change,
        depth_change=depth_change,
    )
    quality = assess_quality(
        n_history=len(prices),
        relative_spread=si.relative_spread if si else None,
        near_mid_depth=nmd,
        data_age_seconds=data_age_seconds,
        two_sided_book=bool(book and book.is_two_sided),
    )
    signal = build_anomaly_signal(
        token_id=token_id, market_id=market_id, raw=raw, quality=quality,
        window_desc=f"{len(prices)} obs",
    )
    # Attach the displayed reliability confidence + evidence-family count from the signal alone
    # (price + order-book families), so Signal Lab and Market Detail show the SAME confidence and
    # never the raw 100% data-quality term (spec §6, §17). The Opportunity Board recomputes with
    # live trade-flow families on top, which is the one documented reason it can read higher.
    from ..opportunity.scoring import signal_reliability

    rel, n_fam = signal_reliability(signal)
    signal = signal.model_copy(update={"reliability_confidence": rel, "n_families": n_fam})
    return TokenAnalytics(
        token_id=token_id,
        implied=implied,
        best_bid=book.best_bid if book else None,
        best_ask=book.best_ask if book else None,
        midpoint=mid,
        spread=si.spread if si else None,
        relative_spread=si.relative_spread if si else None,
        imbalance=imb,
        near_mid_depth=nmd,
        volume=volumes[-1] if volumes else None,
        volatility=vol,
        movement=mv,
        zscore=z,
        signal=signal,
        confidence=signal.confidence,
        data_quality=quality.band.value,
        data_age_seconds=data_age_seconds,
    )


def outcome_view(ta: TokenAnalytics, name: str, normalized_prob: float | None) -> OutcomeView:
    return OutcomeView(
        name=name,
        token_id=ta.token_id,
        implied_probability=ta.implied,
        implied_probability_normalized=normalized_prob,
        best_bid=ta.best_bid,
        best_ask=ta.best_ask,
        midpoint=ta.midpoint,
        spread=ta.spread,
        relative_spread=ta.relative_spread,
        book_imbalance=ta.imbalance,
        near_mid_depth=ta.near_mid_depth,
        volume=ta.volume,
        rolling_volatility=ta.volatility,
        recent_movement=ta.movement,
        zscore=ta.zscore,
        signal_strength=ta.signal.strength,
        data_quality=ta.data_quality,
        confidence=ta.confidence,
        # Displayed confidence uses the one reliability definition, never the raw 1.00 data-quality
        # term (spec §6, §17; adversarial re-review F'#1: Market Detail outcome cards were still
        # showing 100%). Falls back to the data-quality term only if reliability was not computed.
        reliability_confidence=(
            ta.signal.reliability_confidence
            if ta.signal.reliability_confidence is not None
            else ta.confidence
        ),
    )


def normalized_probs_for(analytics: list[TokenAnalytics]) -> list[float | None]:
    return normalized_outcome_probabilities([ta.implied for ta in analytics])


def market_card(market: Market, analytics: list[TokenAnalytics]) -> MarketCard:
    """Build the compact card, using the leading outcome for headline figures."""
    primary = analytics[0] if analytics else None
    # Leading outcome = highest implied probability.
    lead = max(
        analytics, key=lambda a: (a.implied if a.implied is not None else -1.0), default=None
    )
    strengths = [a.signal.strength for a in analytics if a.signal is not None]
    return MarketCard(
        id=market.id,
        question=market.question,
        slug=market.slug,
        category=market.category,
        status=market.status.value,
        tags=market.tags,
        volume=market.volume,
        volume_24hr=market.volume_24hr,
        liquidity=market.liquidity,
        end_date=market.end_date.isoformat() if market.end_date else None,
        top_probability=lead.implied if lead else None,
        top_outcome=_name_for(market, lead.token_id) if lead else None,
        spread=primary.spread if primary else None,
        abs_movement=abs(primary.movement) if (primary and primary.movement is not None) else None,
        signal_strength=max(strengths) if strengths else None,
    )


def _name_for(market: Market, token_id: str) -> str | None:
    for o in market.outcomes:
        if o.token_id == token_id:
            return o.name
    return None


def now_utc() -> datetime:
    return datetime.now(UTC)


def data_age(captured_at: datetime | None) -> float | None:
    if captured_at is None:
        return None
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=UTC)
    return max(0.0, (now_utc() - captured_at).total_seconds())


# convenience for callers that only have gamma metadata (no book/history yet)
def stale_threshold() -> float:
    return get_settings().stale_after_seconds


def composite_only(prices: list[float], book: OrderBook | None) -> float:
    """Quick composite strength for ranking when a full view is not needed."""
    z = rolling_zscore(prices, window=Z_WINDOW, min_periods=Z_MIN_HISTORY).value if prices else None
    imb = order_book_imbalance(book).value if book else None
    score, _ = composite_anomaly_score(RawComponents(zscore=z, imbalance=imb))
    return score
