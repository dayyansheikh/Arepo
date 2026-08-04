"""Replay + backtest endpoints (deterministic demo dataset)."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...service import MarketService
from ...service.schemas import BacktestResponse
from ...storage.db import get_session
from ..deps import get_service

router = APIRouter(prefix="/api/replay", tags=["replay"])


@router.get("/data-status")
async def data_status(session: AsyncSession = Depends(get_session)) -> dict:
    """Collector + evaluation data status (spec §18): how much has actually been recorded, so a
    user understands that leaving the website open does NOT grow the sample; only the scheduled
    backend collectors do, over many days."""
    from ...evaluation.models import WeeklyCohortRow
    from ...ingest.microstructure_store import MicrostructureSnapshotRow

    now = datetime.now(UTC)
    snap_count = await session.scalar(select(func.count(MicrostructureSnapshotRow.id))) or 0
    last_snap = await session.scalar(select(func.max(MicrostructureSnapshotRow.captured_at)))
    cohort_count = await session.scalar(select(func.count(WeeklyCohortRow.id))) or 0
    prospective_count = await session.scalar(
        select(func.count(WeeklyCohortRow.id)).where(
            WeeklyCohortRow.provenance_class == "prospective"
        )
    ) or 0
    oldest = await session.scalar(select(func.min(WeeklyCohortRow.cutoff_at)))
    newest = await session.scalar(select(func.max(WeeklyCohortRow.cutoff_at)))
    # SQLite returns naive datetimes; treat them as UTC so the subtraction is well-defined.
    if last_snap is not None and last_snap.tzinfo is None:
        last_snap = last_snap.replace(tzinfo=UTC)
    age_s = (now - last_snap).total_seconds() if last_snap else None
    # "Running" is inferred from snapshot recency: a snapshot within the last 30 min => a
    # collector is active. We cannot see the cron directly from here, so we report the evidence.
    return {
        "generated_at": now.isoformat(),
        "microstructure_snapshots_stored": int(snap_count),
        "last_collection_at": last_snap.isoformat() if last_snap else None,
        "collector_recent": bool(age_s is not None and age_s < 1800),
        "seconds_since_last_collection": round(age_s) if age_s is not None else None,
        "snapshot_interval_seconds": 300,
        "weekly_cohorts_total": int(cohort_count),
        "prospective_cohorts": int(prospective_count),
        "oldest_cutoff": oldest.isoformat() if oldest else None,
        "newest_cutoff": newest.isoformat() if newest else None,
        "note": (
            "Leaving the website open does not increase the Replay sample. The backend collectors "
            "and scheduled jobs must run: microstructure snapshots every few minutes build "
            "component availability going forward, and the weekly evaluation freezes real "
            "selections at each cut-off. A meaningful performance sample takes many days or weeks, "
            "and historical order books that were never stored cannot be recreated by running the "
            "app now."
        ),
    }


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
