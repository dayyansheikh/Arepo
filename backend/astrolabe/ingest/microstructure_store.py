"""Persisted microstructure snapshot series (spec §7, §19).

Stores timestamped (spread, near-mid depth, cumulative volume) observations per outcome token so
the change features in ``analytics.microstructure_changes`` have a real series to difference. This
is the ONLY honest way to make 'Faster trading activity', 'Spread change' and 'Available depth
change' work on the live prospective path: they are collected forward in time by the scheduler,
never reconstructed from current books for a past timestamp.

Collection is idempotent per (token_id, minute bucket): re-running the collector within the same
minute updates the existing row rather than inserting a duplicate.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ..analytics.microstructure_changes import MicrostructureChanges, changes_from_series
from ..domain.models import utcnow
from ..storage.db import Base

# Provenance: these snapshots are recorded prospectively at wall-clock time, never reconstructed.
PROVENANCE_PROSPECTIVE = "prospective"


class MicrostructureSnapshotRow(Base):
    """One timestamped microstructure observation for a token."""

    __tablename__ = "microstructure_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    minute_bucket: Mapped[str] = mapped_column(String, index=True, nullable=False)
    spread: Mapped[float | None] = mapped_column(Float, nullable=True)
    near_mid_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    cumulative_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    provenance: Mapped[str] = mapped_column(String, nullable=False, default=PROVENANCE_PROSPECTIVE)


def _bucket(token_id: str, at: datetime) -> str:
    return f"{token_id}:{at.strftime('%Y%m%d%H%M')}"


async def record_snapshot(
    session: AsyncSession,
    *,
    token_id: str,
    spread: float | None,
    near_mid_depth: float | None,
    cumulative_volume: float | None,
    now: datetime | None = None,
) -> MicrostructureSnapshotRow:
    """Record (or idempotently update) one snapshot for ``token_id`` in the current minute."""
    now = now or utcnow()
    bucket = _bucket(token_id, now)
    existing = await session.scalar(
        select(MicrostructureSnapshotRow).where(
            MicrostructureSnapshotRow.minute_bucket == bucket
        )
    )
    if existing is not None:
        existing.captured_at = now
        existing.spread = spread
        existing.near_mid_depth = near_mid_depth
        existing.cumulative_volume = cumulative_volume
        await session.commit()
        return existing
    row = MicrostructureSnapshotRow(
        token_id=token_id, captured_at=now, minute_bucket=bucket,
        spread=spread, near_mid_depth=near_mid_depth, cumulative_volume=cumulative_volume,
        provenance=PROVENANCE_PROSPECTIVE,
    )
    session.add(row)
    await session.commit()
    return row


async def recent_snapshots(
    session: AsyncSession, token_id: str, limit: int = 30
) -> list[MicrostructureSnapshotRow]:
    """Most recent snapshots for a token, oldest first (chronological)."""
    rows = await session.scalars(
        select(MicrostructureSnapshotRow)
        .where(MicrostructureSnapshotRow.token_id == token_id)
        .order_by(MicrostructureSnapshotRow.captured_at.desc())
        .limit(limit)
    )
    return list(reversed(list(rows)))


async def collect_snapshots(
    session: AsyncSession, market_service, *, requested_mode: str | None = "live",
    limit: int = 60, now: datetime | None = None,
) -> int:
    """Record a current microstructure snapshot for each surfaced outcome token (spec §19).

    Idempotent per minute. Returns the number of snapshots written/updated. Designed to be run on
    a UTC schedule so the change features accumulate a real prospective series over time.
    """
    now = now or utcnow()
    pairs, _mode = await market_service.enrich_markets(
        requested_mode=requested_mode, limit=limit
    )
    written = 0
    for market, analytics in pairs:
        cumulative_volume = getattr(market, "volume", None)
        for ta in analytics:
            await record_snapshot(
                session, token_id=ta.token_id, spread=ta.spread,
                near_mid_depth=ta.near_mid_depth, cumulative_volume=cumulative_volume, now=now,
            )
            written += 1
    return written


async def changes_for_token(
    session: AsyncSession,
    token_id: str,
    *,
    current_spread: float | None,
    current_depth: float | None,
) -> MicrostructureChanges:
    """Compute the three change features for a token from its stored series (each may be None).

    The most recent snapshot is excluded from the baseline so the current reading is not compared
    against itself. Returns all-``None`` (missing, never zero) until enough snapshots accumulate.
    """
    series = await recent_snapshots(session, token_id)
    if not series:
        return MicrostructureChanges()
    prior = series[:-1] if len(series) > 1 else []
    return changes_from_series(
        current_spread=current_spread,
        current_depth=current_depth,
        prior_spreads=[s.spread for s in prior if s.spread is not None],
        prior_depths=[s.near_mid_depth for s in prior if s.near_mid_depth is not None],
        cumulative_volumes=[s.cumulative_volume for s in series],
    )
