"""Data-mode status + app metadata endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...config import get_settings
from ...domain.models import DataStatus
from ...service import MarketService
from ..deps import get_service

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/status", response_model=DataStatus)
async def status(
    mode: str | None = Query(None),
    service: MarketService = Depends(get_service),
) -> DataStatus:
    """Current data mode, REST/WS health, last update and data age."""
    return await service.status(requested_mode=mode)


@router.get("/meta")
async def meta() -> dict:
    """Static app metadata for the frontend (name, default mode, disclaimer)."""
    s = get_settings()
    return {
        "app": s.app_name,
        "environment": s.environment,
        "default_mode": s.default_mode,
        "modes": ["live", "cached", "replay"],
        "disclaimer": (
            "Astrolabe is a read-only research tool over public Polymarket data. It does not "
            "place trades. Signals flag statistically unusual behaviour for investigation and "
            "are not evidence of insider activity, nor a claim of profitability."
        ),
    }
