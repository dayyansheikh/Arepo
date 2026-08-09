"""Complete-scan / Signal Lab API (prompt sections 10, 11, 12, 19).

Typed, deterministic, idempotent reads over stored scan results. Evaluation truth (bucket
membership, ranks, trajectory, completeness, top-ten subset) is computed server-side.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...discovery.signal_service import SignalReadService
from ...storage.db import get_session

router = APIRouter(prefix="/api/scan", tags=["scan"])


@router.get("/status")
async def scan_status(session: AsyncSession = Depends(get_session)) -> dict:
    """Latest complete-scan status: pagination completeness, discovery funnel, bucket counts."""
    return await SignalReadService(session).scan_status()


@router.get("/signals")
async def signals(
    session: AsyncSession = Depends(get_session),
    bucket: str | None = Query(None),
    scope: str = Query("directional"),
    limit: int = Query(10, ge=1, le=500),
) -> dict:
    """Current signals for the latest scan by closing-time bucket + scope (public|directional|
    shadow|full). Public is a display subset; the others expose the full underlying universe."""
    return await SignalReadService(session).signals(bucket=bucket, scope=scope, limit=limit)


@router.get("/opportunities")
async def opportunities(
    session: AsyncSession = Depends(get_session),
    window: str = Query("all"),
    category: str = Query("All"),
    limit: int | None = Query(None, ge=1, le=50),
) -> dict:
    """Public Opportunities ranked from the complete eligible set after category filtering."""
    try:
        return await SignalReadService(session).opportunities(
            window=window, category=category, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/market/{market_id}/history")
async def market_history(
    market_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    """Signal history + trajectory for one market across stored scans."""
    return await SignalReadService(session).market_history(market_id)
