"""Opportunity Board endpoint: the focused default experience.

Ranks markets by a transparent Research Priority score (not expected profit). Each card
explains why it appears and links to the market analysis page.
"""
from __future__ import annotations

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...opportunity.schemas import OpportunityBoard, SnapshotDetail, SnapshotEntry
from ...opportunity.service import build_opportunity_board
from ...opportunity.snapshot import get_snapshot, list_snapshot_dates
from ...service import MarketService
from ...storage.db import get_session
from ..deps import get_data_api, get_service

router = APIRouter(prefix="/api/opportunity", tags=["opportunity"])


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
    mode: str | None = Query(None, description="live | cached | replay"),
    top: int = Query(30, ge=1, le=50),
    universe: int = Query(40, ge=1, le=60, description="candidate markets to consider"),
    service: MarketService = Depends(get_service),
    data_api=Depends(get_data_api),
) -> OpportunityBoard:
    return await build_opportunity_board(
        service, data_api, requested_mode=mode, top=top, universe_limit=universe
    )


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
