"""Replay + backtest endpoints (deterministic demo dataset)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...service import MarketService
from ...service.schemas import BacktestResponse
from ..deps import get_service

router = APIRouter(prefix="/api/replay", tags=["replay"])


@router.get("/backtest", response_model=BacktestResponse)
async def backtest(
    strength_threshold: float = Query(0.30, ge=0.0, le=1.0),
    move_threshold: float = Query(0.02, ge=0.0, le=1.0),
    horizon: int = Query(5, ge=1, le=40),
    service: MarketService = Depends(get_service),
) -> BacktestResponse:
    return service.backtest(
        strength_threshold=strength_threshold,
        move_threshold=move_threshold,
        horizon=horizon,
    )


@router.get("/scenario")
async def scenario(service: MarketService = Depends(get_service)) -> dict:
    """Metadata + market list for the committed replay dataset."""
    resp = await service.overview(requested_mode="replay")
    detail = resp.model_dump()
    return {
        "meta": service.backtest().dataset_meta,
        "markets": [c.model_dump() for c in detail["highest_volume"]],
    }
