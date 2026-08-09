"""Market discovery + detail endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ...service import MarketService
from ...service.schemas import (
    MarketDetailResponse,
    MarketFacetsResponse,
    MarketListResponse,
    MarketSearchResponse,
)
from ..deps import get_service

router = APIRouter(prefix="/api", tags=["markets"])


@router.get("/markets/search", response_model=MarketSearchResponse)
async def search_markets(
    q: str = Query(..., min_length=1, description="keyword, company or ticker"),
    active_only: bool = Query(True, description="only active markets (else include closed)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: MarketService = Depends(get_service),
) -> MarketSearchResponse:
    """Search the full Polymarket universe by keyword (questions, descriptions, events, tags,
    slugs), expanding common company/ticker aliases. Honest empty result when nothing matches;
    never a fabricated market or a stock quote."""
    return await service.search_markets(q, active_only=active_only, limit=limit, offset=offset)


@router.get("/markets", response_model=MarketListResponse)
async def list_markets(
    search: str | None = Query(None, description="Case-insensitive substring of the question"),
    category: str | None = Query("All"),
    status: str | None = None,
    closing: str = Query("any", pattern="^(any|week|month|later)$"),
    sort: str = Query(
        "signal_desc",
        pattern="^(signal_desc|signal_asc|volume|volume_24hr|liquidity|end_date)$",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    mode: str | None = Query(None, description="live | cached | replay (default from settings)"),
    service: MarketService = Depends(get_service),
) -> MarketListResponse:
    try:
        return await service.list_markets(
            requested_mode=mode, search=search, category=category, status=status,
            closing=closing, sort=sort, limit=limit, offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
