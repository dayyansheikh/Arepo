"""Health and readiness endpoints.

``/health`` is the public liveness probe (Render's health check hits it). Detailed diagnostics
diagnostics (scheduler state, latest cohort, storage growth, quota warning) live behind
``/admin/health`` guarded by ``ADMIN_TOKEN`` (master prompt §16: normal user pages never become an
engineering dashboard; detailed diagnostics go through a protected route/CLI).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...domain.models import utcnow
from ...storage.db import get_session

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


@router.get("/admin/health")
async def admin_health(
    x_admin_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Detailed production/research health snapshot. Requires the ``X-Admin-Token`` header to match
    ``ADMIN_TOKEN``. Disabled (404) when ``ADMIN_TOKEN`` is unset so no diagnostic surface is
    exposed by default."""
    settings = get_settings()
    if not settings.admin_token:
        raise HTTPException(status_code=404, detail="not found")
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="unauthorized")
    from ...scheduler.tick import health_from_session
    try:
        return await health_from_session(session)
    except Exception:  # noqa: BLE001 - health must not leak internals
        return {"db_healthy": False, "time": utcnow().isoformat()}
