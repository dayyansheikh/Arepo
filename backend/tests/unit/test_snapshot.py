"""Daily Opportunity snapshot: immutability and idempotency (spec sections 9, 14)."""
from datetime import UTC, date, datetime

import pytest

from astrolabe.opportunity import snapshot_models  # noqa: F401 - register tables
from astrolabe.opportunity.schemas import OpportunityBoard, OpportunityCard, TagOut
from astrolabe.opportunity.snapshot import generate_snapshot, get_snapshot, list_snapshot_dates
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

DAY = date(2026, 8, 2)
NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        yield s
    await engine.dispose()


def _card(rank_seed, rp):
    return OpportunityCard(
        market_id=f"m{rank_seed}", token_id=f"t{rank_seed}", question=f"Q{rank_seed}?",
        outcome="Yes", probability=0.4, research_priority=rp, signal_strength=0.5,
        confidence=0.6, families=["price", "trade_flow"], n_families=2, high_priority=rp >= 50,
        tags=[TagOut(label="Large relative trade", family="trade_flow", explanation="x",
                     methodology_anchor="trade-flow", data_quality="good", timestamp=NOW)],
        explanation="why", liquidity=50000.0, liquidity_quality="good", relative_spread=0.01,
        time_remaining_hours=48.0, end_date=None, data_quality="good", data_mode="live",
    )


def _board(rps):
    cards = [_card(i, rp) for i, rp in enumerate(rps)]
    return OpportunityBoard(
        generated_at=NOW, data_mode="live", count=len(cards), universe_considered=40,
        cards=cards, note="test",
    )


async def test_snapshot_generates_top_entries(session):
    board = _board([90, 70, 50, 30])
    await generate_snapshot(session, board, snapshot_date=DAY, top=3)
    got = await get_snapshot(session, DAY)
    assert got is not None
    row, entries = got
    assert row.count == 3 and len(entries) == 3
    assert [e.rank for e in entries] == [1, 2, 3]
    assert entries[0].research_priority == 90
    assert entries[0].families == ["price", "trade_flow"]
    assert entries[0].tags == ["Large relative trade"]


async def test_snapshot_is_immutable_and_idempotent(session):
    await generate_snapshot(session, _board([90, 80]), snapshot_date=DAY, top=30)
    first = await get_snapshot(session, DAY)
    assert first is not None
    # A second run for the SAME date with different data must NOT rewrite the snapshot.
    await generate_snapshot(session, _board([10, 20, 30]), snapshot_date=DAY, top=30)
    second = await get_snapshot(session, DAY)
    assert second is not None
    _, e1 = first
    _, e2 = second
    assert [e.research_priority for e in e1] == [e.research_priority for e in e2] == [90, 80]
    assert len(await list_snapshot_dates(session)) == 1


async def test_snapshot_different_dates_coexist(session):
    await generate_snapshot(session, _board([90]), snapshot_date=date(2026, 8, 1))
    await generate_snapshot(session, _board([80]), snapshot_date=date(2026, 8, 2))
    dates = await list_snapshot_dates(session)
    assert dates == [date(2026, 8, 2), date(2026, 8, 1)]  # newest first
