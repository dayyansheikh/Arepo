"""Public read-only signal view: ``GET /api/public/signals`` (off unless PUBLIC_SIGNALS_ENABLED).

Serves only the allow-listed projection in :mod:`astrolabe.lab.public_signals` of the stored host
Lab snapshot. No auth, no writes, no new table; the embargo is re-checked per request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...accounts.db import get_async_session
from ...config import get_settings
from ...domain.models import utcnow
from ...lab import public_signals
from ...lab.models import LabSnapshot
from ...lab.service import _aware

router = APIRouter(prefix="/api/public", tags=["public-signals"])


@router.get("/signals")
async def get_public_signals(
    response: Response, session: AsyncSession = Depends(get_async_session)
) -> dict:
    if not get_settings().public_signals_enabled:
        raise HTTPException(404, "Not Found")
    row = await session.get(LabSnapshot, "host")
    now = utcnow()
    response.headers["Cache-Control"] = "public, max-age=60"
    if row is None:
        return public_signals.project({}, None, now)
    return public_signals.project_text(row.payload, _aware(row.received_at), now)
