"""Historical reconstructed retrospective endpoint.

A clearly-labelled analysis mode, separate from the prospective frozen-weekly cohorts. It
reconstructs the composite anomaly signal at a past cut-off using only real price history up
to that point (no look-ahead), then measures what actually happened afterwards.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query

from ...evaluation.historical import HistoricalScreen, run_live_historical
from ...service import MarketService
from ..deps import get_service

router = APIRouter(prefix="/api/historical", tags=["historical"])


@router.get("/screen", response_model=HistoricalScreen)
async def screen(
    days: int = Query(7, ge=1, le=30, description="how many days before now the cut-off sits"),
    limit: int = Query(24, ge=1, le=40, description="how many near-mid markets to consider"),
    top_n: int = Query(15, ge=1, le=25),
    service: MarketService = Depends(get_service),
) -> HistoricalScreen:
    """Reconstruct the top-N composite anomaly signals as of ``days`` ago and score them
    against the real later price history. Uses live data; can be slow (fetches full history
    for each candidate market)."""
    as_of = datetime.now(UTC) - timedelta(days=days)
    return await run_live_historical(service, as_of=as_of, universe_limit=limit, top_n=top_n)
