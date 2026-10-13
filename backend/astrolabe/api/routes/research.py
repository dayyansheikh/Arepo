"""Research-status API (prompt sections 13, 14).

Reports the REAL edge-research state from stored prospective rows: cohort counts by cadence, role
and horizon coverage, per-horizon baseline and ablation tables, calibration status and the edge
verdict. No synthetic or reconstructed numbers enter here.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...categories import normalize_category_filter
from ...evaluation.research_constants import RESEARCH_HORIZONS
from ...evaluation.research_replay import (
    CLOSING_FILTERS,
    REPLAY_HORIZONS,
    SCOPE_DIRECTIONAL,
    SCOPE_PUBLIC,
    ResearchReplayService,
)
from ...evaluation.research_service import ResearchReadService
from ...storage.db import get_session
from .. import research_cache

router = APIRouter(prefix="/api/research", tags=["research"])
STATUS_MAX_AGE = 300.0


@router.get("/status")
async def status(session: AsyncSession = Depends(get_session)) -> dict:
    """Full research status + edge verdict from real stored prospective rows."""
    # status() reports collector recency against the wall clock, so a short max age.
    return await research_cache.cached(
        session, "status", ResearchReadService(session).status, max_age=STATUS_MAX_AGE)


@router.get("/horizon/{horizon}")
async def horizon(
    horizon: str, session: AsyncSession = Depends(get_session)
) -> dict:
    """Baseline + ablation tables for one forward horizon (1h | 6h | 24h | 7d)."""
    if horizon not in RESEARCH_HORIZONS:
        # Unknown horizon: not cached (bounded key space); the query matches no rows.
        return await ResearchReadService(session).horizon_analysis(horizon)
    return await research_cache.cached(
        session, f"horizon:{horizon}",
        lambda: ResearchReadService(session).horizon_analysis(horizon))


@router.get("/edge")
async def edge(
    session: AsyncSession = Depends(get_session),
    _horizon: str = Query("24h", alias="horizon"),
) -> dict:
    """Just the edge verdict block (a compact endpoint for the status banner)."""
    full = await research_cache.cached(
        session, "status", ResearchReadService(session).status, max_age=STATUS_MAX_AGE)
    return full["edge"]


# --- Prospective-Replay product (refinement prompt sections 1-11) -----------------------------


@router.get("/replay/cohorts")
async def replay_cohorts(session: AsyncSession = Depends(get_session)) -> dict:
    """Available real prospective cohorts + per-cadence summary for the Replay selectors."""
    return await research_cache.cached(
        session, "replay:cohorts", ResearchReplayService(session).list_cohorts)


@router.get("/replay/headline")
async def replay_headline(session: AsyncSession = Depends(get_session)) -> dict:
    """Market-deduplicated, dependence-aware cross-cohort research headline (selected vs wider)."""
    return await research_cache.cached(
        session, "replay:headline", ResearchReplayService(session).dependence_aware_headline)


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
        # Canonicalise exactly as cohort_results does (invalid values fall back to its defaults;
        # an unknown category raises -> 422) so the cache key space stays bounded.
        key_h = horizon if horizon in REPLAY_HORIZONS else "6h"
        key_s = scope if scope in (SCOPE_PUBLIC, SCOPE_DIRECTIONAL) else SCOPE_DIRECTIONAL
        key_c = closing if closing in CLOSING_FILTERS else "all"
        key_cat = normalize_category_filter(category)
        return await research_cache.cached(
            session, f"replay:cohort:{cohort_id}:{key_h}:{key_s}:{key_c}:{key_cat}",
            lambda: ResearchReplayService(session).cohort_results(
                cohort_id, horizon=horizon, scope=scope, closing=closing, category=category
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
