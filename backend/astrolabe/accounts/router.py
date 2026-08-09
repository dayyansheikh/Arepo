"""All account routes: auth (fastapi-users) + preferences / saved markets / history / deletion.

Auth endpoints carry the per-IP rate limiter (spec §9). Personalised endpoints require an
authenticated active user and are strictly scoped to that user's id (spec §10 isolation).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..digest.service import digest_detail, list_digest_history, unsubscribe_digest
from .auth import auth_backend, current_active_user, fastapi_users
from .db import get_async_session
from .models import User
from .ratelimit import rate_limit
from .schemas import (
    AlertDeliveryRead,
    DigestDetailRead,
    DigestListRead,
    DigestSummaryRead,
    DigestUnsubscribeRead,
    DigestUnsubscribeRequest,
    PreferenceRead,
    PreferenceUpdate,
    SavedMarketCreate,
    SavedMarketRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from .service import (
    add_saved,
    categories_list,
    delete_account,
    get_or_create_preferences,
    list_deliveries,
    list_saved,
    remove_saved,
    update_preferences,
)

# fastapi-users routers. Auth-sensitive ones get the rate limiter as a router-level dependency.
auth_router = APIRouter()
auth_router.include_router(
    fastapi_users.get_auth_router(
        auth_backend, requires_verification=get_settings().require_email_verification
    ),
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(rate_limit)],
)
auth_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(rate_limit)],
)
auth_router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(rate_limit)],
)
auth_router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/api/auth",
    tags=["auth"],
    dependencies=[Depends(rate_limit)],
)
auth_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["users"],
)


def _pref_read(pref) -> PreferenceRead:
    return PreferenceRead(
        email_enabled=pref.email_enabled,
        immediate_exceptional=pref.immediate_exceptional,
        daily_digest=pref.daily_digest,
        weekly_summary=pref.weekly_summary,
        min_research_priority=pref.min_research_priority,
        min_confidence=pref.min_confidence,
        categories=categories_list(pref),
        short_term_only=pref.short_term_only,
        max_hours_to_close=pref.max_hours_to_close,
        paused=pref.paused,
        unsubscribed=pref.unsubscribed,
        digest_frequency=pref.digest_frequency,
        digest_top_n=pref.digest_top_n,
        digest_unsubscribed=pref.digest_unsubscribed,
        updated_at=pref.updated_at,
    )


account_router = APIRouter(prefix="/api/account", tags=["account"])


@account_router.get("/preferences", response_model=PreferenceRead)
async def read_preferences(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    pref = await get_or_create_preferences(session, str(user.id))
    return _pref_read(pref)


@account_router.patch("/preferences", response_model=PreferenceRead)
async def patch_preferences(
    changes: PreferenceUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    pref = await update_preferences(
        session, str(user.id), changes.model_dump(exclude_unset=True)
    )
    return _pref_read(pref)


@account_router.get("/saved", response_model=list[SavedMarketRead])
async def get_saved(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    rows = await list_saved(session, str(user.id))
    return [
        SavedMarketRead(market_id=r.market_id, question=r.question, created_at=r.created_at)
        for r in rows
    ]


@account_router.post("/saved", response_model=SavedMarketRead, status_code=status.HTTP_201_CREATED)
async def post_saved(
    body: SavedMarketCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    row = await add_saved(session, str(user.id), body.market_id, body.question)
    return SavedMarketRead(
        market_id=row.market_id, question=row.question, created_at=row.created_at
    )


@account_router.delete("/saved/{market_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved(
    market_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    await remove_saved(session, str(user.id), market_id)
    return None


@account_router.get("/alerts", response_model=list[AlertDeliveryRead])
async def get_alert_history(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    rows = await list_deliveries(session, str(user.id))
    return [
        AlertDeliveryRead(
            market_id=r.market_id, token_id=r.token_id, subject=r.subject,
            status=r.status, detail=r.detail, at=r.at,
        )
        for r in rows
    ]


@account_router.get("/digests", response_model=DigestListRead)
async def get_digest_history(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    items, has_more = await list_digest_history(
        session, str(user.id), limit=limit, offset=offset
    )
    return DigestListRead(
        items=[DigestSummaryRead(**item) for item in items], has_more=has_more
    )


@account_router.get("/digests/{digest_id}", response_model=DigestDetailRead)
async def get_digest_detail(
    digest_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    detail = await digest_detail(session, str(user.id), digest_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Digest not found")
    return DigestDetailRead(**detail)


@account_router.post(
    "/digest/unsubscribe",
    response_model=DigestUnsubscribeRead,
    dependencies=[Depends(rate_limit)],
)
async def post_digest_unsubscribe(
    body: DigestUnsubscribeRequest,
    session: AsyncSession = Depends(get_async_session),
):
    # The response is intentionally identical for valid, invalid and already-used tokens so this
    # public endpoint cannot be used to enumerate users or delivery history.
    await unsubscribe_digest(session, body.token)
    return DigestUnsubscribeRead()


@account_router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_own_account(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    await delete_account(session, user)
    return None
