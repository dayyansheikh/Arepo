"""Owner-only member administration for the Lab (list, emails, verify, suspend, admin, delete).

Every function takes the acting owner (already authorised by ``routes.lab.owner``) and the target
member, applies the guard rules, writes one ``lab_admin_audit`` row in the SAME transaction as the
change, and commits. Passwords are never read, set or returned: password resets and verification
emails go through the standard fastapi-users flows (``forgot_password`` / ``request_verify``) so
the member receives the normal email and sets their own password.

Only account tables are touched. Research, cohort, market and lab tables are never modified,
except that ``lab_commands.created_by`` (a plain string, not a foreign key) is left as written.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Request
from fastapi_users import exceptions as fu_exc
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..accounts.manager import UserManager
from ..accounts.models import AlertDelivery, AlertPreference, DigestDelivery, SavedMarket, User
from ..accounts.service import delete_account
from .models import LabAdminAudit

# Per-owner rolling-hour allowances (counted from the audit log, so they hold across processes
# and restarts). Email actions are capped tighter because each one sends a real email.
EMAIL_ACTIONS = ("password_reset", "verification_email")
MAX_EMAIL_ACTIONS_PER_HOUR = 20
MAX_ACTIONS_PER_HOUR = 60
AUDIT_LIMIT = 50

# Per-user tables summarised in the member list and removed on delete (digest_entries are
# removed through their digest_deliveries parent).
USER_DATA_TABLES: tuple[tuple[str, type], ...] = (
    ("alert_preferences", AlertPreference),
    ("saved_markets", SavedMarket),
    ("alert_deliveries", AlertDelivery),
    ("digest_deliveries", DigestDelivery),
)


class AdminError(Exception):
    """A refused action. ``status`` is the HTTP status the route should answer with."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def _same_email(a: str | None, b: str | None) -> bool:
    return bool(a) and bool(b) and a.strip().casefold() == b.strip().casefold()


def mask_email(email: str | None) -> str:
    """Privacy mask kept after a deletion: first character + "***@" + domain ("d***@gmail.com")."""
    local, sep, domain = (email or "").strip().partition("@")
    if not sep or not local or not domain:
        return "***"
    return f"{local[0]}***@{domain}"


def email_sha256(email: str | None) -> str:
    """The same non-reversible hash ``delete_account`` stores in account_deletions."""
    return hashlib.sha256((email or "").encode("utf-8")).hexdigest()


def member_dict(user: User, data: dict[str, int] | None = None) -> dict:
    """Public shape of a member. Never includes hashed_password or any token."""
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": bool(user.is_active),
        "is_verified": bool(user.is_verified),
        "is_superuser": bool(user.is_superuser),
        "created_at": _iso(user.created_at),
        "data": data if data is not None else {name: 0 for name, _ in USER_DATA_TABLES},
    }


def audit_dict(row: LabAdminAudit) -> dict:
    return {
        "id": row.id,
        "at": _iso(row.at),
        "actor_user_id": row.actor_user_id,
        "actor_email": row.actor_email,
        "action": row.action,
        "target_user_id": row.target_user_id,
        "target_email": row.target_email,
        "detail": row.detail,
    }


async def _data_counts(session: AsyncSession) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for name, model in USER_DATA_TABLES:
        rows = await session.execute(
            select(model.user_id, func.count()).group_by(model.user_id)
        )
        for user_id, n in rows:
            out.setdefault(str(user_id), {})[name] = int(n)
    return out


async def list_members(session: AsyncSession) -> list[dict]:
    counts = await _data_counts(session)
    users = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars()
    result = []
    for u in users:
        per = counts.get(str(u.id), {})
        result.append(member_dict(u, {name: per.get(name, 0) for name, _ in USER_DATA_TABLES}))
    return result


async def list_audit(session: AsyncSession, limit: int = AUDIT_LIMIT) -> list[dict]:
    rows = await session.execute(
        select(LabAdminAudit).order_by(LabAdminAudit.id.desc()).limit(limit)
    )
    return [audit_dict(r) for r in rows.scalars()]


async def get_member(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise AdminError(404, "Member not found.")
    return user


async def _check_rate(session: AsyncSession, actor: User, now: datetime, email: bool) -> None:
    since = now - timedelta(hours=1)
    base = (
        select(func.count())
        .select_from(LabAdminAudit)
        .where(LabAdminAudit.actor_user_id == str(actor.id), LabAdminAudit.at >= since)
    )
    if (await session.execute(base)).scalar_one() >= MAX_ACTIONS_PER_HOUR:
        raise AdminError(429, "Too many member actions this hour. Try again later.")
    if email:
        n = (await session.execute(
            base.where(LabAdminAudit.action.in_(EMAIL_ACTIONS))
        )).scalar_one()
        if n >= MAX_EMAIL_ACTIONS_PER_HOUR:
            raise AdminError(429, "Too many emails sent this hour. Try again later.")


def _audit(
    session: AsyncSession, actor: User, action: str, target: User, now: datetime,
    detail: dict | None = None,
) -> None:
    session.add(LabAdminAudit(
        at=now, actor_user_id=str(actor.id), actor_email=actor.email, action=action,
        target_user_id=str(target.id), target_email=target.email,
        detail=json.dumps(detail, sort_keys=True) if detail else None,
    ))


async def _effective_admins(session: AsyncSession) -> list[User]:
    rows = await session.execute(
        select(User).where(
            User.is_superuser.is_(True), User.is_active.is_(True), User.is_verified.is_(True)
        )
    )
    return list(rows.scalars())


# ---- email actions (standard fastapi-users flows) -------------------------------------------
async def send_password_reset(
    session: AsyncSession, manager: UserManager, actor: User, target: User,
    request: Request | None, now: datetime,
) -> dict:
    if not target.is_active:
        raise AdminError(409, "This account is suspended. Restore it before sending a reset.")
    await _check_rate(session, actor, now, email=True)
    try:
        await manager.forgot_password(target, request)
    except fu_exc.UserInactive as exc:
        raise AdminError(409, "This account is suspended.") from exc
    _audit(session, actor, "password_reset", target, now)
    await session.commit()
    return member_dict(target)


async def send_verification(
    session: AsyncSession, manager: UserManager, actor: User, target: User,
    request: Request | None, now: datetime,
) -> dict:
    if target.is_verified:
        raise AdminError(409, "This email address is already verified.")
    if not target.is_active:
        raise AdminError(409, "This account is suspended. Restore it before sending email.")
    await _check_rate(session, actor, now, email=True)
    try:
        await manager.request_verify(target, request)
    except fu_exc.UserAlreadyVerified as exc:
        raise AdminError(409, "This email address is already verified.") from exc
    except fu_exc.UserInactive as exc:
        raise AdminError(409, "This account is suspended.") from exc
    _audit(session, actor, "verification_email", target, now)
    await session.commit()
    return member_dict(target)


# ---- account state ---------------------------------------------------------------------------
async def mark_verified(session: AsyncSession, actor: User, target: User, now: datetime) -> dict:
    if target.is_verified:
        raise AdminError(409, "This email address is already verified.")
    await _check_rate(session, actor, now, email=False)
    target.is_verified = True
    _audit(session, actor, "verify", target, now)
    await session.commit()
    return member_dict(target)


async def set_active(
    session: AsyncSession, actor: User, target: User, active: bool, now: datetime
) -> dict:
    if not active:
        if target.id == actor.id:
            raise AdminError(409, "You can't suspend your own account.")
        if target.is_superuser:
            raise AdminError(409, "Revoke admin access before suspending this member.")
        if not target.is_active:
            raise AdminError(409, "This account is already suspended.")
    elif target.is_active:
        raise AdminError(409, "This account is already active.")
    await _check_rate(session, actor, now, email=False)
    target.is_active = active
    _audit(session, actor, "restore" if active else "suspend", target, now)
    await session.commit()
    return member_dict(target)


async def set_admin(
    session: AsyncSession, actor: User, target: User, grant: bool, confirm_email: str,
    now: datetime,
) -> dict:
    if not _same_email(confirm_email, target.email):
        raise AdminError(422, "The confirmation email does not match this member.")
    if grant:
        if target.is_superuser:
            raise AdminError(409, "This member is already an admin.")
        if not (target.is_active and target.is_verified):
            raise AdminError(409, "Only active, verified members can be made admin.")
    else:
        if not target.is_superuser:
            raise AdminError(409, "This member is not an admin.")
        if target.id == actor.id:
            raise AdminError(409, "You can't revoke your own admin access.")
        remaining = [u for u in await _effective_admins(session) if u.id != target.id]
        if not remaining:
            raise AdminError(409, "You can't revoke the last remaining admin.")
    await _check_rate(session, actor, now, email=False)
    target.is_superuser = grant
    _audit(session, actor, "admin_grant" if grant else "admin_revoke", target, now)
    await session.commit()
    return member_dict(target)


async def delete_member(
    session: AsyncSession, actor: User, target: User, confirm_email: str, now: datetime
) -> dict:
    if not _same_email(confirm_email, target.email):
        raise AdminError(422, "The confirmation email does not match this member.")
    if target.id == actor.id:
        raise AdminError(409, "You can't delete your own account here.")
    if target.is_superuser:
        raise AdminError(409, "Revoke admin access before deleting this member.")
    await _check_rate(session, actor, now, email=False)
    removed = (await _data_counts(session)).get(str(target.id), {})
    removed = {name: removed.get(name, 0) for name, _ in USER_DATA_TABLES}
    target_id = str(target.id)
    masked = mask_email(target.email)
    # No plain copy of a deleted member's email survives: earlier audit rows that name them (as
    # target or actor) are masked, and the delete row itself stores only the mask plus the same
    # hash account_deletions keeps.
    await session.execute(
        update(LabAdminAudit).where(LabAdminAudit.target_user_id == target_id)
        .values(target_email=masked)
    )
    await session.execute(
        update(LabAdminAudit).where(LabAdminAudit.actor_user_id == target_id)
        .values(actor_email=masked)
    )
    session.add(LabAdminAudit(
        at=now, actor_user_id=str(actor.id), actor_email=actor.email, action="delete",
        target_user_id=target_id, target_email=masked,
        detail=json.dumps({"email_sha256": email_sha256(target.email), "removed": removed},
                          sort_keys=True),
    ))
    # Reuses the self-service deletion path (explicit per-table deletes in FK order plus the
    # hashed account_deletions row); it commits once, so the audit changes and every delete land
    # in one transaction.
    await delete_account(session, target, reason="owner_admin")
    return {"deleted": target_id, "removed": removed}
