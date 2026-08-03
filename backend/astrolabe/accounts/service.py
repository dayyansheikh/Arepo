"""Data-access helpers for per-user preferences, saved markets and alert history.

Every function is scoped to a single user id, which is the isolation boundary: callers pass the
authenticated user's id and can only ever touch that user's rows.
"""
from __future__ import annotations

import hashlib

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from .models import (
    AccountDeletionAudit,
    AlertDelivery,
    AlertPreference,
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
        if key == "categories" and isinstance(value, list):
            value = ",".join(sorted({c.strip() for c in value if c.strip()}))
        setattr(pref, key, value)
    pref.updated_at = utcnow()
    await session.commit()
    await session.refresh(pref)
    return pref


def categories_list(pref: AlertPreference) -> list[str]:
    return [c for c in pref.categories.split(",") if c] if pref.categories else []


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
    for model in (AlertPreference, SavedMarket, AlertDelivery):
        await session.execute(delete(model).where(model.user_id == user.id))
    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
