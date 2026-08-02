"""A tiny async-safe in-memory TTL cache for hot reads (e.g. the market list).

This is purely an optimization layer in front of :class:`~astrolabe.storage.repository.
Repository` — never the source of truth. Nothing here talks to the database.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

_MISSING = object()


class TTLCache:
    """A minimal per-key TTL cache, safe to share across concurrent async tasks.

    ``clock`` defaults to ``time.monotonic`` but can be swapped for a fake in tests to
    make expiry deterministic without real sleeps.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._store: dict[Any, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: Any, default: Any = None) -> Any:
        """Return the cached value for ``key``, or ``default`` if missing/expired."""
        async with self._lock:
            entry = self._store.get(key, _MISSING)
            if entry is _MISSING:
                return default
            expires_at, value = entry
            if self._clock() >= expires_at:
                del self._store[key]
                return default
            return value

    async def set(self, key: Any, value: Any, ttl_seconds: float) -> None:
        """Store ``value`` under ``key``, expiring ``ttl_seconds`` from now."""
        async with self._lock:
            self._store[key] = (self._clock() + ttl_seconds, value)

    async def delete(self, key: Any) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def size(self) -> int:
        """Number of entries currently stored (including any not-yet-expired ones)."""
        async with self._lock:
            return len(self._store)
