"""Opportunity Board endpoint: the focused default experience.

Ranks markets by a transparent Research Priority score (not expected profit). Each card
explains why it appears and links to the market analysis page.
"""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...opportunity.cache import SwrCache
from ...opportunity.schemas import OpportunityBoard, SnapshotDetail, SnapshotEntry
from ...opportunity.service import build_opportunity_board
from ...opportunity.snapshot import get_snapshot, list_snapshot_dates
from ...service import MarketService
from ...storage.db import get_session
from ..deps import get_data_api, get_service

router = APIRouter(prefix="/api/opportunity", tags=["opportunity"])

# Process-wide board cache (stale-while-revalidate). The board changes slowly, so serving a
# recent copy and refreshing in the background keeps the default page fast without showing
# fabricated data (a stale board is real, just a couple of minutes old, and is labelled by the
# X-Board-Cache header and its own generated_at timestamp).
_board_cache: SwrCache[OpportunityBoard] = SwrCache(fresh_ttl=90.0, hard_ttl=900.0)


def _snapshot_detail(row, entries) -> SnapshotDetail:
    return SnapshotDetail(
        snapshot_date=row.snapshot_date.isoformat(),
        generated_at=row.generated_at,
        data_mode=row.data_mode,
        calculation_version=row.calculation_version,
        count=row.count,
        note=row.note,
        entries=[
            SnapshotEntry(
                rank=e.rank, market_id=e.market_id, token_id=e.token_id, question=e.question,
                outcome=e.outcome, research_priority=e.research_priority,
                signal_strength=e.signal_strength, confidence=e.confidence,
                n_families=e.n_families, high_priority=e.high_priority, families=e.families,
                tags=e.tags, probability=e.probability, relative_spread=e.relative_spread,
                liquidity=e.liquidity, data_quality=e.data_quality,
            )
            for e in entries
        ],
    )


@router.get("/board", response_model=OpportunityBoard)
async def board(
    response: Response,
    mode: str | None = Query(None, description="live | cached | replay"),
    top: int = Query(30, ge=1, le=50),
    universe: int = Query(40, ge=1, le=60, description="candidate markets to consider"),
    service: MarketService = Depends(get_service),
    data_api=Depends(get_data_api),
) -> OpportunityBoard:
    key = f"{mode or 'default'}:{top}:{universe}"

    async def _build() -> OpportunityBoard:
        return await build_opportunity_board(
            service, data_api, requested_mode=mode, top=top, universe_limit=universe
        )

    board = await _board_cache.get(key, _build)
    # Let clients cache briefly too, and revalidate in the background (mirrors the server SWR).
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    response.headers["X-Board-Cache"] = _board_cache.last_status or "miss"
    return board


@router.get("/snapshots", response_model=list[str])
async def snapshots(session: AsyncSession = Depends(get_session)) -> list[str]:
    """Dates for which an immutable daily snapshot exists, newest first."""
    return [d.isoformat() for d in await list_snapshot_dates(session)]


@router.get("/snapshot/{snapshot_date}", response_model=SnapshotDetail)
async def snapshot(
    snapshot_date: date_type, session: AsyncSession = Depends(get_session)
) -> SnapshotDetail:
    got = await get_snapshot(session, snapshot_date)
    if got is None:
        raise HTTPException(status_code=404, detail="No snapshot for that date.")
    return _snapshot_detail(*got)
