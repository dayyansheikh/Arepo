"""Freeze-to-close quote collection (final-completion prompt C4).

Over each short-horizon market's REMAINING lifetime this collector records the first valid
post-freeze observation and keeps the latest valid quote at or before the market's close. It is
idempotent (safe to run every 15 minutes), measured from the actual freeze, retry-safe, and
explicit about unavailable data. Once the close time passes, the row is marked closed and its last
valid quote becomes the final pre-close price; a quote observed at or after close is rejected and
never overwrites it. Final resolution is never inferred from price here.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from .research_models import (
    ResearchCohortRow,
    ResearchEntryRow,
    ResearchPreCloseRow,
)
from .research_repository import ResearchRepository
from .research_tracking import PriceProvider


class _PreCloseCandidate(NamedTuple):
    id: int
    market_id: str
    token_id: str
    expected_close: datetime | None


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


async def _get_or_create(session: AsyncSession, entry: ResearchEntryRow) -> ResearchPreCloseRow:
    row = await session.scalar(
        select(ResearchPreCloseRow).where(ResearchPreCloseRow.entry_id == entry.id)
    )
    if row is None:
        row = ResearchPreCloseRow(
            entry_id=entry.id, close_time=entry.expected_close, observations=0,
            closed=False, updated_at=utcnow(),
        )
        session.add(row)
        await session.flush()
    return row


async def collect_preclose(
    session: AsyncSession, *, price_of: PriceProvider, now: datetime | None = None,
    public_only: bool = False, within_hours: float | None = None,
) -> dict:
    """Collect one freeze-to-close observation per eligible entry. Returns a summary.

    Only directional entries of frozen prospective cohorts are tracked (the entries whose
    freeze-to-close result matters). A quote at/after the market's close is rejected; the last valid
    pre-close quote is preserved as the final price.

    ``public_only`` restricts collection to the public-selected entries and ``within_hours`` to
    markets whose close is within that horizon of the freeze; both bound the live CLOB load so the
    scheduled collector stays inside the venue's rate limits while covering the markets whose
    freeze-to-close is actually approaching.
    """
    now = now or utcnow()
    updated = closed = rejected_after_close = unavailable = 0

    # Egress/IO guard (infra 2026-10-11): the previous loop loaded EVERY full research_entries row
    # of every cohort (~166 MB in production) and then issued one SELECT per tracked entry (N+1), on
    # every tick, even though almost every tracked row is already finalised. The SQL below applies
    # the SAME eligibility rules server-side (frozen prospective cohort, not excessively late,
    # directional, has a close time, public-selected when ``public_only``) and drops entries whose
    # freeze-to-close row is already ``closed`` -- a closed row is terminal (the loop only ever
    # ``continue``d past it), so excluding it changes nothing. Ordering matches the old loop.
    q = (
        select(
            ResearchEntryRow.id, ResearchEntryRow.market_id, ResearchEntryRow.token_id,
            ResearchEntryRow.expected_close, ResearchEntryRow.time_remaining_hours,
        )
        .join(ResearchCohortRow, ResearchCohortRow.id == ResearchEntryRow.cohort_id)
        .outerjoin(ResearchPreCloseRow, ResearchPreCloseRow.entry_id == ResearchEntryRow.id)
        .where(
            ResearchCohortRow.provenance_class == "prospective",
            ResearchCohortRow.frozen.is_(True),
            ResearchCohortRow.excessively_late.is_not(True),
            ResearchEntryRow.direction.in_(("up", "down")),
            ResearchEntryRow.expected_close.is_not(None),
            or_(ResearchPreCloseRow.id.is_(None), ResearchPreCloseRow.closed.is_not(True)),
        )
        .order_by(
            ResearchCohortRow.cutoff_at.desc(), ResearchEntryRow.rank.is_(None),
            ResearchEntryRow.rank, ResearchEntryRow.id,
        )
    )
    if public_only:
        q = q.where(ResearchEntryRow.public_selected.is_(True))
    candidates = []
    for entry_id, market_id, token_id, expected_close, trh in (await session.execute(q)).all():
        # Same expression as before (incl. ``0.0 or 1e9``), applied in Python for exact parity.
        if within_hours is not None and (trh or 1e9) > within_hours:
            continue
        candidates.append(_PreCloseCandidate(entry_id, market_id, token_id, expected_close))

    rows_by_entry: dict[int, ResearchPreCloseRow] = {}
    ids = [c.id for c in candidates]
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        res = await session.execute(
            select(ResearchPreCloseRow).where(ResearchPreCloseRow.entry_id.in_(chunk))
        )
        rows_by_entry.update({r.entry_id: r for r in res.scalars().all()})

    for entry in candidates:
        close = _utc(entry.expected_close)
        row = rows_by_entry.get(entry.id)
        if row is None:
            row = ResearchPreCloseRow(
                entry_id=entry.id, close_time=entry.expected_close, observations=0,
                closed=False, updated_at=utcnow(),
            )
            session.add(row)
            rows_by_entry[entry.id] = row

        if close is not None and now >= close:
            # Market has closed: finalise. Never fetch or accept a post-close quote.
            if not row.closed:
                row.closed = True
                row.closed_detected_at = now
                row.updated_at = now
                closed += 1
            continue

        quote = await price_of(entry.market_id, entry.token_id)
        if quote is None or quote.midpoint is None:
            row.unavailable_reason = "no valid quote at this collection"
            row.updated_at = now
            unavailable += 1
            continue

        src = _utc(quote.source_timestamp)
        if close is not None and src is not None and src >= close:
            # The quote itself is at/after close: reject it, keep the last valid pre-close.
            rejected_after_close += 1
            continue

        if row.first_observed_at is None:
            row.first_observed_at = now
            row.first_midpoint = quote.midpoint
        row.last_valid_at = now
        row.last_midpoint = quote.midpoint
        row.last_best_bid = quote.best_bid
        row.last_best_ask = quote.best_ask
        row.last_spread = quote.spread
        row.last_near_mid_depth = quote.near_mid_depth
        row.last_source_timestamp = src
        row.unavailable_reason = None
        row.observations += 1
        row.updated_at = now
        updated += 1

    await session.commit()
    return {
        "updated": updated,
        "closed": closed,
        "rejected_after_close": rejected_after_close,
        "unavailable": unavailable,
    }


async def preclose_for_cohort(
    session: AsyncSession, cohort_id: int
) -> dict[int, ResearchPreCloseRow]:
    """All freeze-to-close rows for a cohort's entries, keyed by entry id (for the Replay panel)."""
    entry_ids = [
        e.id for e in await ResearchRepository(session).get_entries(cohort_id)
    ]
    if not entry_ids:
        return {}
    res = await session.execute(
        select(ResearchPreCloseRow).where(ResearchPreCloseRow.entry_id.in_(entry_ids))
    )
    return {r.entry_id: r for r in res.scalars().all()}


def freeze_to_close_result(
    entry: ResearchEntryRow, row: ResearchPreCloseRow | None
) -> dict:
    """Freeze-to-close movement + directional result for one entry (server-side truth).

    Kept separate from short-term repricing, final resolution and executable performance. Reports a
    lifecycle state and, when a final pre-close price exists, the signed movement and whether it
    went in the stored direction. Never claims a resolution.
    """
    if row is None or row.last_midpoint is None:
        return {"state": "pending", "movement": None, "result": None,
                "freeze_midpoint": entry.midpoint, "preclose_midpoint": None}
    freeze_mid = entry.midpoint
    pre = row.last_midpoint
    movement = None if freeze_mid is None else round(pre - freeze_mid, 4)
    result = None
    if movement is not None and abs(movement) > 1e-9:
        up = movement > 0
        result = "moved_expected" if (up == (entry.direction == "up")) else "moved_against"
    elif movement is not None:
        result = "no_change"
    return {
        "state": "closed_final" if row.closed else "open_latest",
        "freeze_midpoint": freeze_mid,
        "preclose_midpoint": pre,
        "movement": movement,
        "result": result,
        "closed": row.closed,
        "observations": row.observations,
        "last_valid_at": row.last_valid_at.isoformat() if row.last_valid_at else None,
    }
