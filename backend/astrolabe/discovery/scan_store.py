"""Append-only persistence + advisory lock for complete scans (prompt sections 7, 8).

Writes are INSERT-only: a later refresh never updates or deletes an earlier ``signal_snapshots`` row
(unique on scan_id+market+token) or ``scan_runs`` header. The advisory lease in ``scan_locks``
prevents overlapping scans and recovers a crashed scan's stale lock after its lease expires.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..evaluation.constants import CALCULATION_VERSION
from ..evaluation.research_constants import MODEL_VERSION
from ..evaluation.research_engine import classify_signal
from .scan_service import ScanResult
from .snapshot_models import ScanLockRow, ScanRunRow, SignalSnapshotRow

LOCK_NAME = "complete_scan"


def _now() -> datetime:
    return datetime.now(UTC)


async def acquire_lock(
    session: AsyncSession, *, holder: str, lease_seconds: float = 600.0, now: datetime | None = None
) -> bool:
    """Acquire the single scan lease. Returns False if a live (non-expired) lock is held by another
    holder. A stale lock (past ``held_until``) is reclaimed. Commits so the lock is visible to other
    connections immediately."""
    now = now or _now()
    existing = await session.get(ScanLockRow, LOCK_NAME)
    if existing is not None:
        held_until = existing.held_until
        if held_until.tzinfo is None:
            held_until = held_until.replace(tzinfo=UTC)
        if held_until > now and existing.holder != holder:
            return False  # a live lock held by someone else
        existing.holder = holder
        existing.acquired_at = now
        existing.held_until = now + timedelta(seconds=lease_seconds)
    else:
        session.add(ScanLockRow(
            name=LOCK_NAME, holder=holder, acquired_at=now,
            held_until=now + timedelta(seconds=lease_seconds),
        ))
    await session.commit()
    return True


async def release_lock(session: AsyncSession, *, holder: str) -> None:
    existing = await session.get(ScanLockRow, LOCK_NAME)
    if existing is not None and existing.holder == holder:
        await session.delete(existing)
        await session.commit()


async def scan_exists(session: AsyncSession, scan_id: str) -> bool:
    return (
        await session.scalar(
            select(func.count(ScanRunRow.id)).where(ScanRunRow.scan_id == scan_id)
        )
    ) > 0


async def record_scan(session: AsyncSession, result: ScanResult) -> dict:
    """Append one scan header + its analysed snapshots. Idempotent on scan_id: a re-record is a
    no-op (returns inserted=0), so a retried refresh never duplicates rows."""
    if await scan_exists(session, result.scan_id):
        return {"scan_id": result.scan_id, "inserted_snapshots": 0, "already_recorded": True}

    bucket_counts = result.bucket_counts()
    top_ten = {b: bucket_counts[b]["public_top_ten"] for b in bucket_counts}
    disc = result.discovery
    pages = disc.primary_pages + disc.verification_pages
    session.add(ScanRunRow(
        scan_id=result.scan_id,
        started_at=result.started_at,
        finished_at=result.finished_at,
        duration_seconds=result.duration_seconds,
        pagination_complete=disc.complete,
        pagination_reason=disc.incomplete_reason,
        pages_fetched=pages,
        raw_discovered=disc.union_unique,
        unique_markets=disc.union_unique,
        funnel=result.funnel.as_dict(),
        eligible_30d=result.funnel.eligible_30d,
        analysed=len(result.analysed),
        directional=len(result.directional),
        bucket_counts=bucket_counts,
        top_ten_counts=top_ten,
        status=result.status,
        failure_reason=disc.incomplete_reason if not disc.complete else None,
        discovery=disc.as_dict(),
        selection_policy=result.selection_policy,
        public_selection_limit=result.public_selection_limit,
        model_version=MODEL_VERSION,
        calculation_version=CALCULATION_VERSION,
        provenance="live_scan",
        created_at=_now(),
    ))

    inserted = 0
    for a in result.analysed:
        s = a.screen
        session.add(SignalSnapshotRow(
            scan_id=result.scan_id,
            captured_at=result.started_at,
            market_id=s.market_id,
            condition_id=s.condition_id,
            event_id=s.event_id,
            token_id=s.token_id,
            market_question=s.market_question,
            outcome_name=s.outcome_name,
            close_time=s.expected_close,
            time_remaining_hours=a.hours,
            bucket=a.bucket,
            active=True,
            eligible=True,
            exclusion_reason=None,
            direction=s.direction,
            momentum_direction=s.momentum_direction,
            orderbook_direction=s.orderbook_direction,
            tradeflow_direction=s.tradeflow_direction,
            signal_classification=classify_signal(
                direction=s.direction, n_families=s.n_families,
                strength=s.strength, data_quality=s.data_quality,
            ),
            strength=s.strength,
            confidence=s.confidence,
            research_priority=s.research_priority,
            rank_in_bucket=a.rank_in_bucket,
            overall_rank_30d=a.overall_rank_30d,
            public_top_ten=a.public_top_ten,
            shadow_directional=a.shadow_directional,
            selection_policy=result.selection_policy,
            n_families=s.n_families,
            evidence_families=list(s.evidence_families or []),
            component_scores=list(s.component_scores or []),
            component_availability={},
            data_quality=s.data_quality,
            midpoint=s.midpoint,
            best_bid=s.best_bid,
            best_ask=s.best_ask,
            spread=s.spread,
            near_mid_depth=s.near_mid_depth,
            liquidity=s.liquidity,
            volume=s.volume,
            data_age_seconds=s.data_age_seconds,
            model_version=MODEL_VERSION,
            calculation_version=CALCULATION_VERSION,
            provenance="live_scan",
            created_at=_now(),
        ))
        inserted += 1
    await session.commit()
    return {"scan_id": result.scan_id, "inserted_snapshots": inserted, "already_recorded": False}


# --- reads (server-side truth for the API + trajectory) --------------------------------------


async def latest_scan(session: AsyncSession) -> ScanRunRow | None:
    return await session.scalar(
        select(ScanRunRow).order_by(ScanRunRow.started_at.desc()).limit(1)
    )


async def list_scans(session: AsyncSession, limit: int = 50) -> list[ScanRunRow]:
    res = await session.execute(
        select(ScanRunRow).order_by(ScanRunRow.started_at.desc()).limit(limit)
    )
    return list(res.scalars().all())


async def snapshots_for_scan(
    session: AsyncSession, scan_id: str, *, bucket: str | None = None
) -> list[SignalSnapshotRow]:
    q = select(SignalSnapshotRow).where(SignalSnapshotRow.scan_id == scan_id)
    if bucket is not None:
        q = q.where(SignalSnapshotRow.bucket == bucket)
    q = q.order_by(SignalSnapshotRow.rank_in_bucket.is_(None), SignalSnapshotRow.rank_in_bucket)
    res = await session.execute(q)
    return list(res.scalars().all())


async def snapshots_for_market(
    session: AsyncSession, market_id: str, *, limit: int = 200
) -> list[SignalSnapshotRow]:
    """Every stored snapshot for one market, oldest first (for the market-detail history)."""
    res = await session.execute(
        select(SignalSnapshotRow)
        .where(SignalSnapshotRow.market_id == market_id)
        .order_by(SignalSnapshotRow.captured_at.asc())
        .limit(limit)
    )
    return list(res.scalars().all())


async def snapshots_for_markets(
    session: AsyncSession, market_ids: list[str], *, limit_per_market: int = 200
) -> dict[str, list[SignalSnapshotRow]]:
    """Stored snapshots for MANY markets in ONE query, {market_id: [oldest..newest]}.

    Replaces a per-row ``snapshots_for_market`` N+1 in the trajectory attach path (which timed
    out for Signal Lab's full directional scope over the pooler). Same rows, one round-trip.
    """
    out: dict[str, list[SignalSnapshotRow]] = {m: [] for m in market_ids}
    if not market_ids:
        return out
    res = await session.execute(
        select(SignalSnapshotRow)
        .where(SignalSnapshotRow.market_id.in_(market_ids))
        .order_by(SignalSnapshotRow.market_id, SignalSnapshotRow.captured_at.asc())
    )
    for row in res.scalars().all():
        lst = out.setdefault(row.market_id, [])
        if len(lst) < limit_per_market:
            lst.append(row)
    return out


async def purge_scan(session: AsyncSession, scan_id: str) -> None:
    """Remove a scan and its snapshots. Only for test cleanup of THROWAWAY scans, never used on
    real prospective research rows."""
    await session.execute(delete(SignalSnapshotRow).where(SignalSnapshotRow.scan_id == scan_id))
    await session.execute(delete(ScanRunRow).where(ScanRunRow.scan_id == scan_id))
    await session.commit()
