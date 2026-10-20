"""Security-key (WebAuthn / passkey) step-up endpoints: ``/api/lab/webauthn``.

These paths are exempt from the site-wide step-up gate (accounts/stepup_gate.py) because they are
how a locked owner unlocks. Each endpoint applies its own rule:

* status, unlock (authentication options/verify), recovery, end-session: a password session of an
  owner, or of any account that already has a key (so a key holder can always unlock);
* registration: owner password session for the FIRST key; any further key needs a live step-up;
* list / rename / delete keys, regenerate recovery codes: ``owner`` (step-up when enforced).

Non-GET requests carry the same Origin allow-list check as the rest of the Lab.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...accounts.auth import current_optional_user
from ...accounts.db import get_async_session
from ...accounts.models import User
from ...config import get_settings
from ...domain.models import utcnow
from ...lab import security_keys as sk
from .lab import hardware_key_required, owner

router = APIRouter(prefix="/api/lab/webauthn", tags=["lab-webauthn"])


class CredentialBody(BaseModel):
    credential: dict[str, Any]


class RegisterBody(CredentialBody):
    nickname: str | None = Field(default=None, max_length=200)


class RenameBody(BaseModel):
    nickname: str = Field(min_length=1, max_length=200)


class RecoveryBody(BaseModel):
    code: str = Field(min_length=1, max_length=64)


def _check_origin(request: Request) -> None:
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin not in get_settings().cors_origin_list:
            raise HTTPException(403, "origin not allowed")


async def key_holder(
    request: Request,
    user: User | None = Depends(current_optional_user),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Password session of an owner, or of any account that has a registered key."""
    if user is None:
        raise HTTPException(401, "Not authenticated")
    if not (user.is_active and user.is_verified):
        raise HTTPException(404, "Not Found")
    if not user.is_superuser and await sk.key_count(session, user.id) == 0:
        raise HTTPException(404, "Not Found")
    _check_origin(request)
    return user


def _set_stepup_cookie(response: Response, token: str, expires: datetime) -> None:
    s = get_settings()
    response.set_cookie(
        sk.STEPUP_COOKIE, token,
        max_age=max(1, int((expires - utcnow()).total_seconds())),
        path=sk.STEPUP_COOKIE_PATH_ROOT, httponly=True, secure=s.auth_cookie_secure,
        samesite="strict",
    )


def _clear_stepup_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(sk.STEPUP_COOKIE, path=sk.STEPUP_COOKIE_PATH_ROOT, httponly=True,
                           secure=s.auth_cookie_secure, samesite="strict")


def _raise(exc: sk.SecurityKeyError) -> HTTPException:
    detail: Any = {"code": exc.code, "message": exc.message} if exc.code else exc.message
    return HTTPException(exc.status, detail=detail)


# ---- status + unlock --------------------------------------------------------------------------
@router.get("/status")
async def get_status(
    request: Request,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    return await sk.status(session, user, request.cookies.get(sk.STEPUP_COOKIE), utcnow())


@router.post("/authentication/options")
async def post_auth_options(
    user: User = Depends(key_holder), session: AsyncSession = Depends(get_async_session)
) -> dict:
    try:
        return await sk.authentication_options(session, user, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.post("/authentication/verify")
async def post_auth_verify(
    body: CredentialBody,
    response: Response,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        token, expires = await sk.authenticate(session, user, body.credential, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc
    _set_stepup_cookie(response, token, expires)
    return {"step_up": {"active": True, "expires_at": expires.isoformat(), "method": "key"}}


@router.post("/recovery")
async def post_recovery(
    body: RecoveryBody,
    response: Response,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        token, expires, remaining = await sk.use_recovery_code(session, user, body.code,
                                                                utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc
    _set_stepup_cookie(response, token, expires)
    return {"step_up": {"active": True, "expires_at": expires.isoformat(), "method": "recovery"},
            "recovery_codes_remaining": remaining}


@router.post("/lock", status_code=204)
async def post_lock(
    request: Request,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    """Ends this browser's step-up now (the password session stays)."""
    await sk.revoke_stepup(session, user, request.cookies.get(sk.STEPUP_COOKIE), utcnow())
    response = Response(status_code=204)
    _clear_stepup_cookie(response)
    return response


# ---- registration -----------------------------------------------------------------------------
async def registrar(
    request: Request,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Owners only. First key: password session. Every further key: a live step-up."""
    if not user.is_superuser:
        raise HTTPException(404, "Not Found")
    keys = await sk.key_count(session, user.id)
    if keys > 0 and get_settings().lab_hardware_key_mode != "off":
        live = await sk.active_stepup(session, user, request.cookies.get(sk.STEPUP_COOKIE),
                                      utcnow())
        if live is None:
            raise hardware_key_required(keys)
    return user


@router.post("/registration/options")
async def post_reg_options(
    user: User = Depends(registrar), session: AsyncSession = Depends(get_async_session)
) -> dict:
    try:
        return await sk.registration_options(session, user, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.post("/registration/verify", status_code=201)
async def post_reg_verify(
    body: RegisterBody,
    response: Response,
    user: User = Depends(registrar),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        result = await sk.register_key(session, user, body.credential, body.nickname, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc
    if result.stepup_token and result.stepup_expires:
        _set_stepup_cookie(response, result.stepup_token, result.stepup_expires)
    return {"key": result.key, "recovery_codes": result.recovery_codes}


# ---- key management (step-up required when enforced) ------------------------------------------
@router.get("/keys")
async def get_keys(
    user: User = Depends(owner), session: AsyncSession = Depends(get_async_session)
) -> dict:
    return {"keys": await sk.list_keys(session, user),
            "recovery_codes_remaining": await sk.recovery_codes_remaining(session, user)}


@router.patch("/keys/{key_id}")
async def patch_key(
    key_id: int,
    body: RenameBody,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await sk.rename_key(session, user, key_id, body.nickname, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: int,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await sk.delete_key(session, user, key_id, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.post("/recovery-codes")
async def post_regenerate_codes(
    user: User = Depends(owner), session: AsyncSession = Depends(get_async_session)
) -> dict:
    if await sk.key_count(session, user.id) == 0:
        raise HTTPException(409, "Register a security key first.")
    return {"recovery_codes": await sk.regenerate_recovery_codes(session, user, utcnow())}
