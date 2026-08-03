"""Market discovery + detail endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...service import MarketService
from ...service.schemas import MarketDetailResponse, MarketFacetsResponse, MarketListResponse
from ..deps import get_service

router = APIRouter(prefix="/api", tags=["markets"])


@router.get("/markets", response_model=MarketListResponse)
async def list_markets(
    search: str | None = Query(None, description="Case-insensitive substring of the question"),
    category: str | None = None,
    status: str | None = None,
    sort: str = Query("volume", pattern="^(volume|volume_24hr|liquidity|end_date)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    mode: str | None = Query(None, description="live | cached | replay (default from settings)"),
    service: MarketService = Depends(get_service),
) -> MarketListResponse:
    return await service.list_markets(
        requested_mode=mode, search=search, category=category, status=status,
        sort=sort, limit=limit, offset=offset,
    )


@router.get("/markets/facets", response_model=MarketFacetsResponse)
async def market_facets(
    mode: str | None = Query(None, description="live | cached | replay (default from settings)"),
    service: MarketService = Depends(get_service),
) -> MarketFacetsResponse:
    """Distinct real filter values (categories/sports/competitions/statuses) for the Markets
    page filter controls. Built dynamically from the current normalized market set; never
    fabricated, and empty lists are returned where data is absent."""
    return await service.facets(requested_mode=mode)


@router.get("/markets/{market_id}", response_model=MarketDetailResponse)
async def market_detail(
    market_id: str,
    mode: str | None = None,
    range: str = Query("all", pattern="^(1h|6h|24h|7d|all)$", description="chart timeline range"),
    service: MarketService = Depends(get_service),
) -> MarketDetailResponse:
    detail = await service.market_detail(market_id, requested_mode=mode, chart_range=range)
    if detail is None:
        raise HTTPException(status_code=404, detail="market not found")
    return detail
