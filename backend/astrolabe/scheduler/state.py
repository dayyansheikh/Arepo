"""Scheduler state + lease helpers (portable SQLite + Postgres).

The lease acquire is atomic on both dialects: the conditional UPDATE's WHERE clause (``held_until <
now``) is evaluated row-atomically, so at most one holder can flip an expired/free lease. A loser's
UPDATE affects zero rows and it backs off cleanly (duplicate-invocation safety, master prompt §11).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SchedulerLeaseRow, SchedulerStateRow


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


async def acquire_lease(
    session: AsyncSession, *, name: str, holder: str, ttl_seconds: int, now: datetime | None = None
) -> bool:
    """Try to take the named lease. True if acquired; False if a live lease is held by another."""
    now = _utc(now) or datetime.now(UTC)
    held_until = now + timedelta(seconds=ttl_seconds)
    existing = await session.scalar(
        select(SchedulerLeaseRow).where(SchedulerLeaseRow.name == name)
    )
    if existing is None:
        session.add(SchedulerLeaseRow(
            name=name, holder=holder, acquired_at=now, held_until=held_until))
        try:
            await session.commit()
            return True
        except IntegrityError:
            # A concurrent inserter won the race; fall through to the conditional takeover.
            await session.rollback()
    # Take over only if the current lease has expired (atomic conditional update). The DB evaluates
    # the WHERE clause; synchronize_session=False avoids the ORM's Python-side re-evaluation, which
    # would trip over SQLite's naive datetimes vs a tz-aware ``now``.
    result = await session.execute(
        update(SchedulerLeaseRow)
        .where(SchedulerLeaseRow.name == name, SchedulerLeaseRow.held_until < now)
        .values(holder=holder, acquired_at=now, held_until=held_until)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return (result.rowcount or 0) == 1


async def release_lease(session: AsyncSession, *, name: str, holder: str) -> None:
    """Release the lease if we still hold it (expiry-based takeover covers a crash w/o release)."""
    await session.execute(
        update(SchedulerLeaseRow)
        .where(SchedulerLeaseRow.name == name, SchedulerLeaseRow.holder == holder)
        .values(held_until=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    await session.commit()


async def get_state(session: AsyncSession, job: str) -> SchedulerStateRow | None:
    return await session.scalar(select(SchedulerStateRow).where(SchedulerStateRow.job == job))


async def record_attempt(
    session: AsyncSession, *, job: str, ok: bool, duration_seconds: float, detail: dict,
    now: datetime | None = None,
) -> None:
    """UPSERT the last-run bookkeeping for one job (bounded: one row per job)."""
    now = _utc(now) or datetime.now(UTC)
    row = await get_state(session, job)
    if row is None:
        row = SchedulerStateRow(job=job, run_count=0, fail_count=0)
        session.add(row)
    row.last_attempt_at = now
    row.last_ok = ok
    row.last_duration_seconds = duration_seconds
    row.last_detail = detail
    row.run_count = (row.run_count or 0) + 1
    if ok:
        row.last_success_at = now
    else:
        row.fail_count = (row.fail_count or 0) + 1
    await session.commit()
