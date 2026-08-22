"""Async SQLAlchemy 2.0 engine/session plumbing.

Built from ``settings.database_url`` (default: local SQLite via ``aiosqlite``), but kept
Postgres-compatible: no SQLite-only column types are used anywhere in ``storage/models.py``,
and the only SQLite-specific behavior here is an in-memory-database pooling fix needed for
tests (see ``make_engine``).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from ..config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all storage ORM models (see ``storage/models.py``)."""


def make_engine(url: str | None = None) -> AsyncEngine:
    """Build an async engine for ``url`` (defaults to ``settings.database_url``).

    A SQLite ``:memory:`` URL gets ``StaticPool`` so all connections share the same
    in-memory database (SQLAlchemy's default pool opens a fresh, empty in-memory DB per
    connection, which would make ``init_db`` and later queries see different databases).
    Any other URL (file-based SQLite, Postgres, ...) uses SQLAlchemy's normal pooling.
    """
    db_url = url or get_settings().database_url
    kwargs: dict = {"future": True}
    if ":memory:" in db_url:
        kwargs["poolclass"] = StaticPool
    elif not db_url.startswith("sqlite"):
        # Real (Postgres) pooling: liveness-check every pooled connection before use, and recycle
        # connections older than the pooler's idle window. A scan does no DB work for ~16-28 min
        # during discovery/enrichment; the connection it later re-acquires for persistence could be
        # one the Supabase pooler already dropped, which surfaced as intermittent empty-message
        # "flush failed / transaction rolled back" scan failures. pre_ping discards a dead
        # connection and transparently opens a fresh one; recycle proactively avoids stale ones.
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 1800
    return create_async_engine(db_url, **kwargs)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build a session factory bound to ``engine``."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine | None = None) -> None:
    """Create all known tables. Idempotent (``create_all`` skips existing tables)."""
    eng = engine or _default_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async-generator dependency yielding an AsyncSession bound to the default engine.

    Usable directly as a FastAPI dependency: ``session: AsyncSession = Depends(get_session)``.
    """
    sessionmaker = make_sessionmaker(_default_engine())
    async with sessionmaker() as session:
        yield session


_engine_singleton: AsyncEngine | None = None


def _default_engine() -> AsyncEngine:
    """Lazily-built process-wide engine for the app's configured database.

    Lazy so importing this module never opens a connection or reads settings at import
    time (tests build their own engines via ``make_engine`` and never touch this).
    """
    global _engine_singleton
    if _engine_singleton is None:
        _engine_singleton = make_engine()
    return _engine_singleton
