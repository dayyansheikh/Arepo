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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from .research_models import (
    ResearchEntryRow,
    ResearchPreCloseRow,
)
from .research_repository import ResearchRepository
from .research_tracking import PriceProvider


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
    repo = ResearchRepository(session)
    cohorts = await repo.list_cohorts(provenance="prospective", frozen=True)
    updated = closed = rejected_after_close = unavailable = 0

    for cohort in cohorts:
        if cohort.excessively_late:
            continue
        for entry in await repo.get_entries(cohort.id):
            if entry.direction not in ("up", "down") or entry.expected_close is None:
                continue
            if public_only and not entry.public_selected:
                continue
            if within_hours is not None and (entry.time_remaining_hours or 1e9) > within_hours:
                continue
            close = _utc(entry.expected_close)
            row = await _get_or_create(session, entry)

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
