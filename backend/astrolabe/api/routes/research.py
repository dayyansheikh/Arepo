"""Research-status API (prompt sections 13, 14).

Reports the REAL edge-research state from stored prospective rows: cohort counts by cadence, role
and horizon coverage, per-horizon baseline and ablation tables, calibration status and the edge
verdict. No synthetic or reconstructed numbers enter here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...evaluation.research_service import ResearchReadService
from ...storage.db import get_session

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/status")
async def status(session: AsyncSession = Depends(get_session)) -> dict:
    """Full research status + edge verdict from real stored prospective rows."""
    return await ResearchReadService(session).status()


@router.get("/horizon/{horizon}")
async def horizon(
    horizon: str, session: AsyncSession = Depends(get_session)
) -> dict:
    """Baseline + ablation tables for one forward horizon (1h | 6h | 24h | 7d)."""
    return await ResearchReadService(session).horizon_analysis(horizon)


@router.get("/edge")
async def edge(
    session: AsyncSession = Depends(get_session),
    _horizon: str = Query("24h", alias="horizon"),
) -> dict:
    """Just the edge verdict block (a compact endpoint for the status banner)."""
    full = await ResearchReadService(session).status()
    return full["edge"]
