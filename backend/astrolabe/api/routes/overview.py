"""Overview dashboard endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...service import MarketService
from ...service.schemas import OverviewResponse
from ..deps import get_service

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview", response_model=OverviewResponse)
async def overview(
    mode: str | None = Query(None, description="live | cached | replay (default from settings)"),
    service: MarketService = Depends(get_service),
) -> OverviewResponse:
    return await service.overview(requested_mode=mode)
