"""Database dependencies for accounts: an async session and the fastapi-users adapter.

The session dependency is deliberately thin and overridable so tests can bind it to their own
in-memory engine via ``app.dependency_overrides``.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage.db import get_session
from .models import User


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
