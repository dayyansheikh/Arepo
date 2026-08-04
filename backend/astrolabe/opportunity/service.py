"""Opportunity Board service: per-market signal + public trade flow -> ranked cards.

For each candidate market it reuses the existing enrichment (composite anomaly signal from
price and order book), fetches recent public trades, computes the trade-flow / wallet / timing
indicators, scores a Research Priority, and returns the top cards. Trades are only available in
Live mode; in other modes the flow indicators degrade to "no data" and the board falls back to
the price/order-book signal, which is stated honestly.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from ..analytics import flow
from ..domain.enums import DataMode
from ..domain.models import Trade, utcnow
from ..ingest.normalize import normalize_trades
from .hypothesis import build_hypothesis, has_directional_view
from .schemas import CALCULATION_VERSION, OpportunityBoard, OpportunityCard, TagOut
from .scoring import ScoredOpportunity, score_opportunity


def market_flow_indicators(
    trades: list[Trade],
    *,
    market_price: float | None,
    price_change: float | None,
    end_date: datetime | None,
    start_date: datetime | None,
    now: datetime,
    wallet_market_counts: dict[str, int] | None = None,
) -> list[flow.FlowIndicator]:
    """All trade-flow / wallet / timing indicators for one market's recent trades."""
    inds = [
        flow.large_relative_trade(trades),
        flow.consensus_opposing_flow(trades, market_price=market_price, price_change=price_change),
        flow.concentrated_flow(trades),
        flow.clustered_trades(trades),
        flow.late_large_trade(trades, end_date=end_date, now=now, start_date=start_date),
    ]
    if wallet_market_counts:
        inds.append(flow.limited_activity_history(trades, wallet_market_counts))
    return inds


def _card(market, ta, scored: ScoredOpportunity, mode: str, now: datetime) -> OpportunityCard:
    end = market.end_date
    hours = (end - now).total_seconds() / 3600.0 if end else None
    hours_r = round(hours, 1) if hours is not None else None
    directional = has_directional_view(
        ta.signal.direction, scored.n_families, scored.signal_strength
    )
    hypothesis = build_hypothesis(
        direction=ta.signal.direction,
        outcome=ta.signal.outcome_name,
        n_families=scored.n_families,
        signal_strength=scored.signal_strength,
        time_remaining_hours=hours_r,
    )
    return OpportunityCard(
        market_id=market.id,
        token_id=ta.token_id,
        question=market.question,
        category=getattr(market, "category", None),
        outcome=ta.signal.outcome_name,
        direction=ta.signal.direction if directional else None,
        directional=directional,
        hypothesis=hypothesis,
        probability=ta.implied,
        research_priority=int(round(scored.research_priority * 100)),
        signal_strength=scored.signal_strength,
        confidence=scored.confidence,
        families=scored.families,
        n_families=scored.n_families,
        high_priority=scored.high_priority,
        tags=[
            TagOut(
                label=t.label, family=t.family, explanation=t.explanation,
                methodology_anchor=t.methodology_anchor, data_quality=t.data_quality,
                timestamp=t.timestamp,
            )
            for t in scored.tags
        ],
        explanation=scored.explanation,
        liquidity=market.liquidity,
        liquidity_quality=scored.liquidity_quality,
        relative_spread=ta.relative_spread,
        time_remaining_hours=hours_r,
        end_date=end.isoformat() if end else None,
        data_quality=scored.data_quality,
        data_mode=mode,
    )


async def build_opportunity_board(
    market_service,
    data_api,
    *,
    requested_mode: str | None = None,
    top: int = 30,
    universe_limit: int = 40,
    view: str = "directional",
    now: datetime | None = None,
) -> OpportunityBoard:
    """Build the ranked Opportunity Board.

    ``view`` controls selectivity (spec §4): ``directional`` (default) shows only markets with a
    usable directional view; ``strongest`` the highest-priority directional views; ``inconclusive``
    the screened markets without a directional view; ``all`` every screened market. Abstention is
    preserved: neutral markets never dominate the default board.
    """
    now = now or utcnow()
    pairs, mode = await market_service.enrich_markets(
        requested_mode=requested_mode, limit=universe_limit
    )
    live = mode == DataMode.LIVE

    async def build(market, analytics) -> OpportunityCard | None:
        if not analytics:
            return None
        ta = max(analytics, key=lambda a: a.signal.strength)
        trades: list[Trade] = []
        if live and market.condition_id:
            try:
                raw = await data_api.get_market_trades(market.condition_id, limit=1000)
                trades = normalize_trades(raw)
            except Exception:  # noqa: BLE001 - trades are best-effort; degrade cleanly
                trades = []
        indicators = market_flow_indicators(
            trades,
            market_price=ta.implied,
            price_change=ta.movement,
            end_date=market.end_date,
            start_date=market.start_date,
            now=now,
        )
        scored = score_opportunity(
            ta.signal, indicators,
            liquidity=market.liquidity, relative_spread=ta.relative_spread,
            data_age_seconds=ta.data_age_seconds, now=now,
        )
        return _card(market, ta, scored, mode.value, now)

    results = await asyncio.gather(
        *(build(m, a) for m, a in pairs), return_exceptions=True
    )
    cards = [c for c in results if isinstance(c, OpportunityCard)]
    cards.sort(key=lambda c: c.research_priority, reverse=True)

    screened_count = len(pairs)
    directional = [c for c in cards if c.directional]
    directional_count = len(directional)

    # Selectivity (spec §4): the default board is directional-only, so neutral markets do not
    # dominate. Other views are available for exploration; Explore holds the full neutral universe.
    if view == "strongest":
        selected = sorted(directional, key=lambda c: c.signal_strength, reverse=True)
    elif view == "inconclusive":
        selected = [c for c in cards if not c.directional]
    elif view == "all":
        selected = cards
    else:  # "directional" (default)
        view = "directional"
        selected = directional
    top_cards = selected[:top]

    flow_note = (
        "Trade-flow indicators use live public trades."
        if live
        else "Trade-flow indicators need Live mode; this board uses the price and order-book "
        "signal only."
    )
    note = (
        f"Arepo screened {screened_count} markets; {directional_count} currently meet the "
        f"evidence and quality requirements for a directional view. Ranked by a transparent "
        f"Research Priority score (not expected profit). " + flow_note
    )
    return OpportunityBoard(
        generated_at=now,
        data_mode=mode.value,
        calculation_version=CALCULATION_VERSION,
        count=len(top_cards),
        universe_considered=len(pairs),
        screened_count=screened_count,
        directional_count=directional_count,
        view=view,
        cards=top_cards,
        note=note,
    )
