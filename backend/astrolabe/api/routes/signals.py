"""Signal Lab endpoint — statistically unusual market behaviour."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...service import MarketService
from ...service.schemas import SignalsResponse
from ..deps import get_service

router = APIRouter(prefix="/api", tags=["signals"])


@router.get("/signals", response_model=SignalsResponse)
async def signals(
    limit: int = Query(25, ge=1, le=100),
    mode: str | None = Query(None, description="live | cached | replay (default from settings)"),
    service: MarketService = Depends(get_service),
) -> SignalsResponse:
    return await service.signals(requested_mode=mode, limit=limit)
