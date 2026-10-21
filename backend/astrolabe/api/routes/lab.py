"""Private Lab dashboard API: signed machine endpoints + owner-only (superuser) endpoints."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...accounts.auth import current_optional_user
from ...accounts.db import get_async_session
from ...accounts.models import User
from ...accounts.stepup_gate import locked_body
from ...config import get_settings
from ...domain.models import utcnow
from ...lab import security_keys, service
from ...lab.signing import MAX_BODY_BYTES, SignatureError, verify_signature

router = APIRouter(prefix="/api/lab", tags=["lab"])


class CommandCreate(BaseModel):
    # "queue" (research host) or an autopilot instance: "autopilot" (experiments, the original
    # target) or "autopilot-<name>" (e.g. "autopilot-signal"). "start" is autopilot-only.
    target: str = Field(pattern=r"^(queue|autopilot(-[a-z0-9]{1,24})?)$", max_length=40)
    action: Literal["pause", "resume", "start"]


class CommandResult(BaseModel):
    ok: bool
    message: str = Field(default="", max_length=500)


class MessageCreate(BaseModel):
    target: str = Field(pattern=r"^autopilot(-[a-z0-9]{1,24})?$", max_length=40)
    body: str = Field(min_length=1, max_length=service.MESSAGE_MAX_CHARS + 200)


class MessageState(BaseModel):
    state: Literal["delivered", "read", "failed"]
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


async def owner_password(
    request: Request, user: User | None = Depends(current_optional_user)
) -> User:
    """Owner with a password session only (no security-key step-up check).

    Used directly ONLY by the step-up ceremony endpoints themselves (status, key sign-in,
    recovery, first-key registration). Everything else depends on :func:`owner`.
    """
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


def hardware_key_required(keys: int) -> HTTPException:
    return HTTPException(403, detail=locked_body(keys)["detail"])


async def owner(
    request: Request,
    user: User = Depends(owner_password),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Owner-only gate for every Lab dashboard / command / admin / key-management endpoint.

    401 signed out, 404 for anyone but an owner, and, when security keys are enforced
    (``LAB_REQUIRE_HARDWARE_KEY``), 403 ``hardware_key_required`` until a valid step-up cookie is
    presented. The site-wide gate (accounts/stepup_gate.py) already enforces this for non-exempt
    paths; this explicit check also covers the exempt ``/api/lab/webauthn/*`` management routes.
    Machine-signed ``/api/lab/agent/*`` endpoints never use this dependency.
    """
    token = request.cookies.get(security_keys.STEPUP_COOKIE)
    keys = await security_keys.user_locked(
        session, user, token, utcnow(),
        device_token=request.cookies.get(security_keys.DEVICE_COOKIE),
    )
    if keys is not None:
        raise hardware_key_required(keys)
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


@router.get("/agent/messages")
async def get_messages(
    signed: tuple[str, bytes] = Depends(signed_source),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    return await service.fetch_messages(session, signed[0], utcnow())


@router.post("/agent/messages/{message_id}/status", status_code=204)
async def post_message_status(
    message_id: int,
    signed: tuple[str, bytes] = Depends(signed_source),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    try:
        body = MessageState.model_validate_json(signed[1])
    except ValueError as exc:
        raise HTTPException(422, "invalid status body") from exc
    try:
        await service.record_message_state(session, signed[0], message_id, body.state,
                                           body.message, utcnow())
    except service.MessageNotFound as exc:
        raise HTTPException(404, "message not found") from exc
    except service.MessageConflict as exc:
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
                                            str(user.id), utcnow(), actor_email=user.email)
    except service.CommandInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except service.RateLimited as exc:
        raise HTTPException(429, "too many commands") from exc


@router.post("/messages", status_code=201)
async def post_message(
    body: MessageCreate,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await service.create_message(session, body.target, body.body, str(user.id),
                                            user.email, utcnow())
    except service.MessageInvalid as exc:
        raise HTTPException(422, str(exc)) from exc
    except service.RateLimited as exc:
        raise HTTPException(429, "too many messages today") from exc


@router.post("/messages/{message_id}/cancel")
async def cancel_message(
    message_id: int,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await service.cancel_message(session, message_id, str(user.id), user.email,
                                            utcnow())
    except service.MessageNotFound as exc:
        raise HTTPException(404, "message not found") from exc
    except service.MessageConflict as exc:
        raise HTTPException(409, str(exc)) from exc
