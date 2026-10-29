"""Historical reconstructed retrospective endpoint.

A clearly-labelled analysis mode, separate from the prospective frozen-weekly cohorts. It
reconstructs the composite anomaly signal at a past cut-off using only real price history up
to that point (no look-ahead), then measures what actually happened afterwards.
"""
from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query

from ...evaluation.historical import HistoricalScreen, run_live_historical
from ...service import MarketService
from ..deps import get_service

router = APIRouter(prefix="/api/historical", tags=["historical"])

_TTL_SECONDS = 600.0
_CACHE_MAX = 64
_cache: dict[tuple, tuple[float, HistoricalScreen]] = {}
_lock = asyncio.Lock()


@router.get("/screen", response_model=HistoricalScreen)
async def screen(
    days: int = Query(7, ge=1, le=30, description="how many days before now the cut-off sits"),
    limit: int = Query(80, ge=1, le=150, description="how many active markets to scan"),
    top_n: int = Query(5, ge=1, le=25, description="top qualifying opportunities (default 5)"),
    service: MarketService = Depends(get_service),
) -> HistoricalScreen:
    """Reconstruct the top-N composite anomaly signals as of ``days`` ago and score them
    against the real later price history. Uses live data; can be slow (fetches full history
    for each candidate market).

    The cut-off is snapped to the START of the target UTC day (midnight) rather than "now minus
    days", so repeated same-day requests with the same ``days`` resolve to the SAME cut-off and are
    reproducible within the day (spec §16; reproducibility findings C#1/F#4). It is still a live
    reconstruction, not a frozen record: the reproducible, immutable evidence is the prospective
    cohort. The universe and later prices are refetched live, so a result may still shift as
    upstream history is revised; the prospective path is the one that never rewrites the past.
    """
    target_day = (datetime.now(UTC) - timedelta(days=days)).date()
    as_of = datetime(target_day.year, target_day.month, target_day.day, tzinfo=UTC)
    # Unauthenticated and expensive (fans out to the upstream API): serve a short-lived cached
    # result per parameter set, and let concurrent identical requests share one computation.
    key = (as_of, limit, top_n)
    now = time.monotonic()
    hit = _cache.get(key)
    if hit and now - hit[0] < _TTL_SECONDS:
        return hit[1]
    async with _lock:
        hit = _cache.get(key)
        if hit and time.monotonic() - hit[0] < _TTL_SECONDS:
            return hit[1]
        result = await run_live_historical(service, as_of=as_of, universe_limit=limit, top_n=top_n)
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        _cache[key] = (time.monotonic(), result)
        return result
