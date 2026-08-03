"""Opportunity Board endpoint: the focused default experience.

Ranks markets by a transparent Research Priority score (not expected profit). Each card
explains why it appears and links to the market analysis page.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...opportunity.schemas import OpportunityBoard
from ...opportunity.service import build_opportunity_board
from ...service import MarketService
from ..deps import get_data_api, get_service

router = APIRouter(prefix="/api/opportunity", tags=["opportunity"])


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
