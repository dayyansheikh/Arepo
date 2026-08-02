"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from ...config import get_settings
from ...domain.models import utcnow

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe: process is up and serving."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "time": utcnow().isoformat(),
    }
