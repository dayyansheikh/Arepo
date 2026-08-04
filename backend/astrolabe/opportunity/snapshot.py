"""Generate and read the immutable daily Opportunity Board snapshot.

Generation is idempotent and never rewrites an existing date: the first run for a date freezes
that day's top-N board; later runs for the same date return the stored snapshot unchanged.
"""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from .schemas import OpportunityBoard
from .service import build_opportunity_board
from .snapshot_models import OpportunityEntryRow, OpportunitySnapshotRow


async def get_snapshot(
    session: AsyncSession, snapshot_date: date_type
) -> tuple[OpportunitySnapshotRow, list[OpportunityEntryRow]] | None:
    row = await session.get(OpportunitySnapshotRow, snapshot_date)
    if row is None:
        return None
    res = await session.execute(
        select(OpportunityEntryRow)
        .where(OpportunityEntryRow.snapshot_date == snapshot_date)
        .order_by(OpportunityEntryRow.rank.asc())
    )
    return row, list(res.scalars().all())


async def list_snapshot_dates(session: AsyncSession) -> list[date_type]:
    res = await session.execute(
        select(OpportunitySnapshotRow.snapshot_date).order_by(
            OpportunitySnapshotRow.snapshot_date.desc()
        )
    )
    return list(res.scalars().all())


async def generate_snapshot(
    session: AsyncSession,
    board: OpportunityBoard,
    *,
    snapshot_date: date_type | None = None,
    top: int = 30,
) -> OpportunitySnapshotRow:
    """Freeze ``board``'s top ``top`` cards as the snapshot for ``snapshot_date`` (default:
    today, UTC). Idempotent: if a snapshot for that date already exists it is returned
    unchanged, never rewritten (spec section 9)."""
    snapshot_date = snapshot_date or utcnow().date()
    existing = await session.get(OpportunitySnapshotRow, snapshot_date)
    if existing is not None:
        return existing  # immutable: do not rewrite an earlier snapshot

    now: datetime = utcnow()
    row = OpportunitySnapshotRow(
        snapshot_date=snapshot_date,
        generated_at=board.generated_at,
        calculation_version=board.calculation_version,
        data_mode=board.data_mode,
        count=min(top, len(board.cards)),
        note=board.note,
    )
    session.add(row)
    for i, card in enumerate(board.cards[:top], start=1):
        session.add(
            OpportunityEntryRow(
                snapshot_date=snapshot_date,
                rank=i,
                market_id=card.market_id,
                token_id=card.token_id,
                question=card.question,
                outcome=card.outcome,
                research_priority=card.research_priority,
                signal_strength=card.signal_strength,
                confidence=card.confidence,
                n_families=card.n_families,
                high_priority=card.high_priority,
                families=list(card.families),
                tags=[t.label for t in card.tags],
                probability=card.probability,
                relative_spread=card.relative_spread,
                liquidity=card.liquidity,
                data_quality=card.data_quality,
                created_at=now,
            )
        )
    await session.commit()
    return row


async def run_daily_snapshot(
    session: AsyncSession,
    market_service,
    data_api,
    *,
    snapshot_date: date_type | None = None,
    requested_mode: str | None = "live",
    top: int = 30,
) -> OpportunitySnapshotRow:
    """Build today's Opportunity Board and freeze it as the daily snapshot (idempotent)."""
    # The daily snapshot is a complete immutable record of the ranked top-N, so it uses the "all"
    # view (not the directional-only default) to preserve its historical meaning.
    board = await build_opportunity_board(
        market_service, data_api, requested_mode=requested_mode, top=top, view="all"
    )
    return await generate_snapshot(session, board, snapshot_date=snapshot_date, top=top)
