"""Process cache for the read-only research endpoints (infra fix 2026-10-11).

/api/research/* and the Replay endpoints recompute their answers from every stored prospective
entry (~110k frozen rows in production) on each request, although the inputs only change when the
scheduled jobs write (a cohort freeze, a forward/pre-close observation, a resolution). Each answer
is therefore cached under a DATA VERSION read from a handful of index-backed aggregates; a write
changes the version and the next request recomputes from the database. Nothing is fabricated: a
cached response is exactly what the same stored rows produced, including its own generated_at.

Bounded: at most ``MAX_ENTRIES`` responses (oldest evicted), ``MAX_AGE_SECONDS`` hard expiry, and
one computation per key at a time (single-flight), so concurrent page loads cannot multiply load.
"""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..discovery.snapshot_models import SignalSnapshotRow
from ..evaluation.models import MarketResolutionRow
from ..evaluation.research_models import (
    ResearchCohortRow,
    ResearchForwardRow,
    ResearchPreCloseRow,
)

MAX_ENTRIES = 48
MAX_AGE_SECONDS = 3600.0

_entries: OrderedDict[str, tuple[Any, Any, float]] = OrderedDict()
_locks: dict[str, asyncio.Lock] = {}


async def data_version(session: AsyncSession) -> tuple:
    """Changes whenever any input of the research/Replay answers changes (write-once ids grow;
    mutable rows bump ``updated_at``)."""
    row = (await session.execute(select(
        select(func.max(ResearchCohortRow.id)).scalar_subquery(),
        select(func.count(ResearchCohortRow.id)).where(ResearchCohortRow.frozen.is_(True))
        .scalar_subquery(),
        select(func.max(ResearchForwardRow.id)).scalar_subquery(),
        select(func.max(ResearchPreCloseRow.updated_at)).scalar_subquery(),
        select(func.max(MarketResolutionRow.updated_at)).scalar_subquery(),
        select(func.max(SignalSnapshotRow.id)).scalar_subquery(),
    ))).one()
    return tuple(str(v) for v in row)


def _enabled() -> bool:
    return get_settings().environment == "production"


async def cached(session: AsyncSession, key: str,
                 compute: Callable[[], Awaitable[Any]],
                 max_age: float = MAX_AGE_SECONDS) -> Any:
    if not _enabled():
        return await compute()
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        version = await data_version(session)
        hit = _entries.get(key)
        if hit is not None and hit[0] == version and time.monotonic() - hit[2] < max_age:
            _entries.move_to_end(key)
            return hit[1]
        _entries.pop(key, None)
        value = await compute()
        _entries[key] = (version, value, time.monotonic())
        while len(_entries) > MAX_ENTRIES:
            old, _ = _entries.popitem(last=False)
            old_lock = _locks.get(old)
            if old_lock is not None and not old_lock.locked():
                _locks.pop(old, None)
        return value


def clear() -> None:
    _entries.clear()
    _locks.clear()
