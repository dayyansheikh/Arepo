"""Owner-only member administration API for the Lab (``/api/lab/admin``).

Every endpoint depends on ``routes.lab.owner`` (active + verified + superuser; 401 when signed
out, 404 for everyone else; Origin allow-list on non-GET), so the area does not reveal itself.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...accounts.db import get_async_session
from ...accounts.manager import UserManager, get_user_manager
from ...accounts.models import User
from ...domain.models import utcnow
from ...lab import admin
from .lab import owner

router = APIRouter(prefix="/api/lab/admin", tags=["lab-admin"])


class ConfirmBody(BaseModel):
    confirm_email: str = Field(min_length=1, max_length=320)


class AdminChange(ConfirmBody):
    grant: bool


async def _target(session: AsyncSession, user_id: uuid.UUID) -> User:
    try:
        return await admin.get_member(session, user_id)
    except admin.AdminError as exc:
        raise HTTPException(exc.status, exc.message) from exc


async def _run(coro) -> dict:
    try:
        return await coro
    except admin.AdminError as exc:
        raise HTTPException(exc.status, exc.message) from exc


@router.get("/users")
async def get_users(
    user: User = Depends(owner), session: AsyncSession = Depends(get_async_session)
) -> dict:
    # ``me`` lets the page hide actions the API would refuse on the owner's own account.
    return {"users": await admin.list_members(session), "me": str(user.id)}


@router.get("/audit")
async def get_audit(
    _user: User = Depends(owner), session: AsyncSession = Depends(get_async_session)
) -> dict:
    return {"entries": await admin.list_audit(session)}


@router.post("/users/{user_id}/password-reset")
async def post_password_reset(
    user_id: uuid.UUID,
    request: Request,
    actor: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
    manager: UserManager = Depends(get_user_manager),
) -> dict:
    target = await _target(session, user_id)
    return await _run(admin.send_password_reset(session, manager, actor, target, request,
                                                utcnow()))


@router.post("/users/{user_id}/verification-email")
async def post_verification_email(
    user_id: uuid.UUID,
    request: Request,
    actor: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
    manager: UserManager = Depends(get_user_manager),
) -> dict:
    target = await _target(session, user_id)
    return await _run(admin.send_verification(session, manager, actor, target, request,
                                              utcnow()))


@router.post("/users/{user_id}/verify")
async def post_verify(
    user_id: uuid.UUID,
    actor: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    target = await _target(session, user_id)
    return await _run(admin.mark_verified(session, actor, target, utcnow()))


@router.post("/users/{user_id}/suspend")
async def post_suspend(
    user_id: uuid.UUID,
    actor: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    target = await _target(session, user_id)
    return await _run(admin.set_active(session, actor, target, False, utcnow()))


@router.post("/users/{user_id}/restore")
async def post_restore(
    user_id: uuid.UUID,
    actor: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    target = await _target(session, user_id)
    return await _run(admin.set_active(session, actor, target, True, utcnow()))


@router.post("/users/{user_id}/admin")
async def post_admin(
    user_id: uuid.UUID,
    body: AdminChange,
    actor: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    target = await _target(session, user_id)
    return await _run(admin.set_admin(session, actor, target, body.grant, body.confirm_email,
                                      utcnow()))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    body: ConfirmBody,
    actor: User = Depends(owner),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    target = await _target(session, user_id)
    return await _run(admin.delete_member(session, actor, target, body.confirm_email, utcnow()))
