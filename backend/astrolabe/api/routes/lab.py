"""Private Lab dashboard API: signed machine endpoints + owner-only (superuser) endpoints."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...accounts.auth import current_optional_user
from ...accounts.db import get_async_session
from ...accounts.models import User
from ...config import get_settings
from ...domain.models import utcnow
from ...lab import service
from ...lab.signing import MAX_BODY_BYTES, SignatureError, verify_signature

router = APIRouter(prefix="/api/lab", tags=["lab"])


class CommandCreate(BaseModel):
    target: Literal["queue", "autopilot"]
    action: Literal["pause", "resume"]


class CommandResult(BaseModel):
    ok: bool
    message: str = Field(default="", max_length=500)


async def signed_source(request: Request) -> tuple[str, bytes]:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        raise HTTPException(413, "payload too large")
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(413, "payload too large")
    try:
        source = verify_signature(
            source=request.headers.get("x-lab-source"),
            timestamp=request.headers.get("x-lab-timestamp"),
            signature=request.headers.get("x-lab-signature"),
            method=request.method, path=request.url.path, body=body,
        )
    except SignatureError as exc:
        raise HTTPException(401, "invalid signature") from exc
    return source, body


async def owner(
    request: Request, user: User | None = Depends(current_optional_user)
) -> User:
    if user is None:
        raise HTTPException(401, "Not authenticated")
    if not (user.is_active and user.is_verified and user.is_superuser):
        raise HTTPException(404, "Not Found")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        # Defence in depth beyond SameSite=lax + CORS allow-list: a sent Origin must be allowed.
        origin = request.headers.get("origin")
        if origin and origin not in get_settings().cors_origin_list:
            raise HTTPException(403, "origin not allowed")
    return user


@router.post("/agent/snapshot", status_code=204)
async def post_snapshot(
    signed: tuple[str, bytes] = Depends(signed_source),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    source, body = signed
    try:
        await service.upsert_snapshot(session, source, body, utcnow())
    except service.SnapshotInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    return Response(status_code=204)


@router.get("/agent/commands")
async def get_commands(
    signed: tuple[str, bytes] = Depends(signed_source),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    return {"commands": await service.fetch_commands(session, signed[0], utcnow())}


@router.post("/agent/commands/{command_id}/result", status_code=204)
async def post_result(
    command_id: int,
    signed: tuple[str, bytes] = Depends(signed_source),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    try:
        # Parse the already-signature-verified raw body (independent of the client's Content-Type).
        result = CommandResult.model_validate_json(signed[1])
    except ValueError as exc:
        raise HTTPException(422, "invalid result body") from exc
    try:
        await service.record_result(session, signed[0], command_id, result.ok,
                                    result.message, utcnow())
    except service.CommandNotFound as exc:
        raise HTTPException(404, "command not found") from exc
    except service.CommandConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    return Response(status_code=204)


@router.get("/dashboard")
async def get_dashboard(
    _user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    return await service.dashboard(session, utcnow())


@router.post("/commands", status_code=201)
async def post_command(
    body: CommandCreate,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await service.create_command(session, body.target, body.action,
                                            str(user.id), utcnow())
    except service.RateLimited as exc:
        raise HTTPException(429, "too many commands") from exc
