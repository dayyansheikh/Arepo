"""Data-access helpers for per-user preferences, saved markets and alert history.

Every function is scoped to a single user id, which is the isolation boundary: callers pass the
authenticated user's id and can only ever touch that user's rows.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..categories import USER_SELECTABLE_CATEGORIES
from ..domain.models import utcnow
from .models import (
    AccountDeletionAudit,
    AlertDelivery,
    AlertPreference,
    DigestDelivery,
    DigestEntry,
    SavedMarket,
    User,
)

DEFAULT_CATEGORIES: list[str] = []


async def get_or_create_preferences(session: AsyncSession, user_id: str) -> AlertPreference:
    pref = await session.get(AlertPreference, user_id)
    if pref is None:
        pref = AlertPreference(user_id=user_id)
        session.add(pref)
        await session.commit()
        await session.refresh(pref)
    return pref


async def update_preferences(
    session: AsyncSession, user_id: str, changes: dict
) -> AlertPreference:
    pref = await get_or_create_preferences(session, user_id)
    for key, value in changes.items():
        if value is None:
            continue
        target_key = key
        if key == "categories" and isinstance(value, list):
            value = ",".join(sorted({c.strip() for c in value if c.strip()}))
            target_key = "digest_categories"
        setattr(pref, target_key, value)
    if changes.get("digest_frequency") not in (None, "off"):
        # A deliberate save from the authenticated Preferences page re-subscribes the digest. This
        # does not affect verification, reset, or legacy immediate-alert preferences.
        pref.digest_unsubscribed = False
    pref.updated_at = utcnow()
    await session.commit()
    await session.refresh(pref)
    return pref


def categories_list(pref: AlertPreference) -> list[str]:
    raw = pref.digest_categories or ""
    selectable = set(USER_SELECTABLE_CATEGORIES)
    return [category for category in raw.split(",") if category in selectable]


async def list_saved(session: AsyncSession, user_id: str) -> list[SavedMarket]:
    rows = await session.scalars(
        select(SavedMarket)
        .where(SavedMarket.user_id == user_id)
        .order_by(SavedMarket.created_at.desc())
    )
    return list(rows)


async def add_saved(
    session: AsyncSession, user_id: str, market_id: str, question: str
) -> SavedMarket:
    existing = await session.scalar(
        select(SavedMarket).where(
            SavedMarket.user_id == user_id, SavedMarket.market_id == market_id
        )
    )
    if existing:
        return existing
    row = SavedMarket(user_id=user_id, market_id=market_id, question=question)
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def remove_saved(session: AsyncSession, user_id: str, market_id: str) -> bool:
    result = await session.execute(
        delete(SavedMarket).where(
            SavedMarket.user_id == user_id, SavedMarket.market_id == market_id
        )
    )
    await session.commit()
    return result.rowcount > 0


async def list_deliveries(
    session: AsyncSession, user_id: str, limit: int = 50
) -> list[AlertDelivery]:
    rows = await session.scalars(
        select(AlertDelivery)
        .where(AlertDelivery.user_id == user_id)
        .order_by(AlertDelivery.at.desc())
        .limit(limit)
    )
    return list(rows)


async def delete_account(session: AsyncSession, user: User, reason: str = "user_request") -> None:
    """Delete a user and all their data, leaving only a non-reversible audit row."""
    email_hash = hashlib.sha256((user.email or "").encode("utf-8")).hexdigest()
    session.add(AccountDeletionAudit(email_hash=email_hash, reason=reason))
    # Explicitly clear owned rows (works even if the DB does not enforce ON DELETE CASCADE).
    digest_ids = select(DigestDelivery.id).where(DigestDelivery.user_id == user.id)
    await session.execute(delete(DigestEntry).where(DigestEntry.digest_id.in_(digest_ids)))
    for model in (DigestDelivery, AlertPreference, SavedMarket, AlertDelivery):
        await session.execute(delete(model).where(model.user_id == user.id))
    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
