"""A small async stale-while-revalidate cache for the Opportunity Board.

The board is expensive to build (it fans out to the public Polymarket order-book and trade
endpoints for dozens of markets), and its contents change only slowly. Rebuilding it on every
request made the default page feel slow. This cache serves a recent board immediately and
refreshes it in the background, so users almost never wait for a full rebuild.

Behaviour per cache key:
- fresh (age < ``fresh_ttl``): return the cached board, no rebuild.
- stale (``fresh_ttl`` <= age < ``hard_ttl``): return the cached board immediately AND trigger a
  single background refresh (stale-while-revalidate).
- missing or expired (age >= ``hard_ttl``): build synchronously (the caller waits once).

A per-key lock prevents a thundering herd: only one build runs per key at a time. ``time`` is
used for ages; there is no wall-clock dependency in behaviour beyond elapsed seconds.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from ..observability.logging import get_logger

logger = get_logger("astrolabe.opportunity.cache")

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    stored_at: float


class SwrCache(Generic[T]):
    def __init__(self, *, fresh_ttl: float = 90.0, hard_ttl: float = 900.0):
        self.fresh_ttl = fresh_ttl
        self.hard_ttl = hard_ttl
        self._entries: dict[str, _Entry[T]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        # Tracks the last outcome for observability/tests: "hit" | "stale" | "miss".
        self.last_status: str | None = None

    def _lock(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def _rebuild(self, key: str, builder: Callable[[], Awaitable[T]]) -> T:
        async with self._lock(key):
            # Another waiter may have refreshed while we waited for the lock.
            entry = self._entries.get(key)
            if entry is not None and (time.monotonic() - entry.stored_at) < self.fresh_ttl:
                return entry.value
            value = await builder()
            self._entries[key] = _Entry(value=value, stored_at=time.monotonic())
            return value

    def _spawn_refresh(self, key: str, builder: Callable[[], Awaitable[T]]) -> None:
        async def _bg() -> None:
            try:
                await self._rebuild(key, builder)
            except Exception as exc:  # noqa: BLE001 - background refresh must never crash a request
                logger.warning("board background refresh failed", extra={"ctx_err": str(exc)})

        # Fire and forget; the reference is intentionally dropped.
        asyncio.ensure_future(_bg())  # noqa: RUF006

    async def get(self, key: str, builder: Callable[[], Awaitable[T]]) -> T:
        entry = self._entries.get(key)
        now = time.monotonic()
        if entry is not None:
            age = now - entry.stored_at
            if age < self.fresh_ttl:
                self.last_status = "hit"
                return entry.value
            if age < self.hard_ttl:
                self.last_status = "stale"
                self._spawn_refresh(key, builder)
                return entry.value
        self.last_status = "miss"
        return await self._rebuild(key, builder)

    def clear(self) -> None:
        self._entries.clear()
