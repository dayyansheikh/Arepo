"""Research-status API (prompt sections 13, 14).

Reports the REAL edge-research state from stored prospective rows: cohort counts by cadence, role
and horizon coverage, per-horizon baseline and ablation tables, calibration status and the edge
verdict. No synthetic or reconstructed numbers enter here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...evaluation.research_replay import ResearchReplayService
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


# --- Prospective-Replay product (refinement prompt sections 1-11) -----------------------------


@router.get("/replay/cohorts")
async def replay_cohorts(session: AsyncSession = Depends(get_session)) -> dict:
    """Available real prospective cohorts + per-cadence summary for the Replay selectors."""
    return await ResearchReplayService(session).list_cohorts()


@router.get("/replay/headline")
async def replay_headline(session: AsyncSession = Depends(get_session)) -> dict:
    """Market-deduplicated, dependence-aware cross-cohort research headline (selected vs wider)."""
    return await ResearchReplayService(session).dependence_aware_headline()


@router.get("/replay/cohort/{cohort_id}")
async def replay_cohort_results(
    cohort_id: int,
    session: AsyncSession = Depends(get_session),
    horizon: str = Query("6h"),
    scope: str = Query("public"),
    closing: str = Query("all"),
    category: str = Query("All"),
) -> dict:
    """Market-by-market result table + aggregate movement answer for one frozen cohort.

    ``horizon`` in 1h|6h|24h|7d; ``scope`` in public|directional; ``closing`` in
    6h|24h|7d|30d|all (frozen time-to-close). Deterministic and read-only.
    """
    try:
        return await ResearchReplayService(session).cohort_results(
            cohort_id, horizon=horizon, scope=scope, closing=closing, category=category
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
