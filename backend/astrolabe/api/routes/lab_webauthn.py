"""Security-key (WebAuthn / passkey) step-up endpoints: ``/api/lab/webauthn``.

These paths are exempt from the site-wide step-up gate (accounts/stepup_gate.py) because they are
how a locked owner unlocks. Each endpoint applies its own rule:

* status, unlock (authentication options/verify), recovery, end-session: a password session of an
  owner, or of any account that already has a key (so a key holder can always unlock);
* registration: owner password session for the FIRST key; any further key needs a live step-up;
* list / rename / delete keys, regenerate recovery codes: ``owner`` (step-up when enforced);
* devices: listing, renaming, forgetting and ending trust need ``owner``; marking THIS device as
  trusted needs a fresh key assertion made on it (a password session alone, a recovery code or a
  trusted device are never enough).

Options endpoints accept an optional JSON body ``{"method": "device" | "phone" | "security_key" |
"any"}`` that steers the browser (WebAuthn hints, transports, authenticator attachment).

Non-GET requests carry the same Origin allow-list check as the rest of the Lab.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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


class MethodBody(BaseModel):
    method: Literal["device", "phone", "security_key", "any"] = "any"


class DeviceRenameBody(BaseModel):
    nickname: str = Field(min_length=1, max_length=200)


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


def _set_device_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        sk.DEVICE_COOKIE, token, max_age=sk.DEVICE_COOKIE_MAX_AGE,
        path=sk.STEPUP_COOKIE_PATH_ROOT, httponly=True, secure=s.auth_cookie_secure,
        samesite="strict",
    )


async def _this_device(request: Request, response: Response, session: AsyncSession,
                       user: User):
    """Record this browser as one of ``user``'s devices, issuing the device cookie if needed."""
    row, new_token = await sk.ensure_device(
        session, user, request.cookies.get(sk.DEVICE_COOKIE),
        request.headers.get("user-agent"), utcnow(),
    )
    if new_token:
        _set_device_cookie(response, new_token)
    return row


def _raise(exc: sk.SecurityKeyError) -> HTTPException:
    detail: Any = {"code": exc.code, "message": exc.message} if exc.code else exc.message
    return HTTPException(exc.status, detail=detail)


# ---- status + unlock --------------------------------------------------------------------------
@router.get("/status")
async def get_status(
    request: Request,
    response: Response,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    row = await _this_device(request, response, session, user)
    return await sk.status(session, user, request.cookies.get(sk.STEPUP_COOKIE), utcnow(),
                           device=row)


@router.post("/authentication/options")
async def post_auth_options(
    body: MethodBody | None = None,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await sk.authentication_options(session, user, utcnow(),
                                               method=(body or MethodBody()).method)
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.post("/authentication/verify")
async def post_auth_verify(
    body: CredentialBody,
    request: Request,
    response: Response,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        token, expires = await sk.authenticate(session, user, body.credential, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc
    _set_stepup_cookie(response, token, expires)
    await _this_device(request, response, session, user)
    return {"step_up": {"active": True, "expires_at": expires.isoformat(), "method": "key"}}


@router.post("/recovery")
async def post_recovery(
    body: RecoveryBody,
    request: Request,
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
    await _this_device(request, response, session, user)
    return {"step_up": {"active": True, "expires_at": expires.isoformat(), "method": "recovery"},
            "recovery_codes_remaining": remaining}


@router.post("/lock", status_code=204)
async def post_lock(
    request: Request,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    """Ends this browser's step-up now and any trust on this device (the password session stays)."""
    await sk.lock_this_browser(session, user, request.cookies.get(sk.STEPUP_COOKIE),
                               request.cookies.get(sk.DEVICE_COOKIE), utcnow())
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
    body: MethodBody | None = None,
    user: User = Depends(registrar),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await sk.registration_options(session, user, utcnow(),
                                             method=(body or MethodBody()).method)
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.post("/registration/verify", status_code=201)
async def post_reg_verify(
    body: RegisterBody,
    request: Request,
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
    await _this_device(request, response, session, user)
    return {"key": result.key, "recovery_codes": result.recovery_codes}


async def fresh_owner(
    request: Request,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """``owner`` plus, when keys are enforced, a live key unlock on this browser.

    A trusted device alone is not enough to remove keys or mint new recovery codes: those could
    otherwise turn "password + trusted device" into a way to replace the owner's keys.
    """
    keys = await sk.key_count(session, user.id)
    if keys > 0 and get_settings().lab_hardware_key_mode != "off":
        live = await sk.active_stepup(session, user, request.cookies.get(sk.STEPUP_COOKIE),
                                      utcnow())
        if live is None:
            raise hardware_key_required(keys)
    return user


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
    user: User = Depends(fresh_owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await sk.delete_key(session, user, key_id, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.post("/recovery-codes")
async def post_regenerate_codes(
    user: User = Depends(fresh_owner), session: AsyncSession = Depends(get_async_session)
) -> dict:
    if await sk.key_count(session, user.id) == 0:
        raise HTTPException(409, "Register a security key first.")
    return {"recovery_codes": await sk.regenerate_recovery_codes(session, user, utcnow())}


# ---- devices + per-device trust ---------------------------------------------------------------
@router.get("/devices")
async def get_devices(
    request: Request,
    response: Response,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    current = await _this_device(request, response, session, user)
    return {"devices": await sk.list_devices(session, user, current, utcnow()),
            "trusted_device_days": get_settings().trusted_device_days,
            "stepup_hours": get_settings().lab_stepup_hours}


@router.post("/devices/current/trust")
async def post_trust_current_device(
    body: CredentialBody,
    request: Request,
    response: Response,
    user: User = Depends(key_holder),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Don't ask for a key on THIS browser for up to 30 days. Needs a fresh key assertion
    (from ``/authentication/options``) made on this device."""
    if not user.is_superuser:
        raise HTTPException(404, "Not Found")
    try:
        device, new_token = await sk.trust_this_device(
            session, user, body.credential, request.cookies.get(sk.DEVICE_COOKIE),
            request.headers.get("user-agent"), utcnow(),
        )
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc
    if new_token:
        _set_device_cookie(response, new_token)
    return {"device": device}


@router.delete("/devices/{device_id}/trust")
async def delete_device_trust(
    device_id: int,
    request: Request,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Ask for the key again on that device (ends its trust now)."""
    try:
        device = await sk.untrust_device(session, user, device_id, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc
    current = await sk.find_device(session, user, request.cookies.get(sk.DEVICE_COOKIE))
    device["current"] = current is not None and current.id == device_id
    return {"device": device}


@router.patch("/devices/{device_id}")
async def patch_device(
    device_id: int,
    body: DeviceRenameBody,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return {"device": await sk.rename_device(session, user, device_id, body.nickname,
                                                 utcnow())}
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc


@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: int,
    user: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    try:
        return await sk.forget_device(session, user, device_id, utcnow())
    except sk.SecurityKeyError as exc:
        raise _raise(exc) from exc
