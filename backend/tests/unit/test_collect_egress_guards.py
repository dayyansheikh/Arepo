"""Egress/IO guards on the scheduled collectors (infra fix 2026-10-11).

Production collect ticks were egressing every full ``research_entries`` row (twice: forward and
preclose) plus one SELECT per tracked preclose entry, every run, while writing nothing. These tests
pin that (a) the outputs are unchanged and (b) a fully-collected cohort / finalised preclose row is
never re-read or re-fetched.
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, select

from astrolabe.evaluation.research_constants import RESEARCH_HORIZONS, ROLE_PUBLIC
from astrolabe.evaluation.research_engine import freeze_from_inputs
from astrolabe.evaluation.research_models import ResearchCohortRow, ResearchPreCloseRow
from astrolabe.evaluation.research_preclose import collect_preclose
from astrolabe.evaluation.research_repository import EntryInput, ResearchRepository
from astrolabe.evaluation.research_tracking import Quote, collect_due_forward
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

FROZEN = datetime(2026, 8, 6, 0, 0, 0, tzinfo=UTC)


@pytest.fixture
async def env():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    statements: list[str] = []

    @event.listens_for(engine_.sync_engine, "before_cursor_execute")
    def _capture(conn, cursor, statement, params, context, executemany):  # noqa: ARG001
        statements.append(statement)

    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s, statements
    await engine_.dispose()


def _entry(market, close_hours, *, public=True, direction="up") -> EntryInput:
    return EntryInput(
        role=ROLE_PUBLIC, rank=1, walk_forward_partition="live", market_id=market,
        condition_id=f"c{market}", event_id=None, token_id=f"{market}-y",
        market_question=f"Q{market}", outcome_name="Yes", direction=direction,
        momentum_direction=direction, orderbook_direction=direction, tradeflow_direction=None,
        signal_classification="Directional opportunity", strength=0.6, confidence=0.6,
        research_priority=80, n_families=2, evidence_families=["price behaviour"],
        component_scores=[], component_availability={}, data_quality="good",
        entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5,
        spread=0.02, near_mid_depth=1000.0, liquidity=25000.0, volume=5000.0, data_age_seconds=10.0,
        expected_close=FROZEN + timedelta(hours=close_hours), time_remaining_hours=close_hours,
        intended_horizons=["1h", "6h"], bucket="closing_0_6h", overall_rank_30d=1,
        public_selected=public,
    )


async def _freeze(session, entries, cutoff=FROZEN):
    return await freeze_from_inputs(
        session, cadence="6h", cutoff_at=cutoff, inputs=entries, model_version="m",
        calculation_version="c", frozen_at=cutoff, provenance_class="prospective",
    )


def _counting_provider(calls: list):
    async def price_of(market_id, token_id):
        calls.append(market_id)
        return Quote(midpoint=0.6, best_bid=0.59, best_ask=0.61, spread=0.02,
                     near_mid_depth=1000.0, source_timestamp=None)
    return price_of


def _full_entry_reads(statements) -> int:
    """SELECTs that pull the wide frozen-entry columns (a full research_entries row)."""
    return sum(1 for s in statements
               if s.lstrip().upper().startswith("SELECT") and "research_entries.market_question"
               in s)


async def test_forward_complete_cohort_is_skipped_without_reading_entries(env):
    session, statements = env
    await _freeze(session, [_entry("m1", 24 * 30), _entry("m2", 24 * 30)])
    calls: list = []
    late = FROZEN + timedelta(days=8)  # every horizon due
    r1 = await collect_due_forward(session, now=late, price_of=_counting_provider(calls))
    assert r1["written"] == 2 * len(RESEARCH_HORIZONS)
    statements.clear()
    calls.clear()
    r2 = await collect_due_forward(session, now=late + timedelta(minutes=15),
                                   price_of=_counting_provider(calls))
    assert r2 == {"written": 0, "unavailable": 0, "closed_before_horizon": 0,
                  "invalid_predates_freeze": 0, "already_present": 2 * len(RESEARCH_HORIZONS)}
    assert calls == []
    assert _full_entry_reads(statements) == 0
    # No per-entry key read either: a complete cohort is decided by the grouped COUNTs alone.
    assert not any("research_entries.token_id" in s for s in statements)


async def test_forward_partial_cohort_still_collects_missing_horizons(env):
    session, _ = env
    await _freeze(session, [_entry("m1", 24 * 30)])
    calls: list = []
    r1 = await collect_due_forward(session, now=FROZEN + timedelta(hours=2),
                                   price_of=_counting_provider(calls))
    assert r1["written"] == 1  # 1h only
    r2 = await collect_due_forward(session, now=FROZEN + timedelta(days=8),
                                   price_of=_counting_provider(calls))
    assert r2["written"] == len(RESEARCH_HORIZONS) - 1
    assert r2["already_present"] == 1


async def test_forward_never_reads_full_entry_rows(env):
    session, statements = env
    await _freeze(session, [_entry("m1", 24 * 30)])
    statements.clear()
    await collect_due_forward(session, now=FROZEN + timedelta(hours=2),
                              price_of=_counting_provider([]))
    assert _full_entry_reads(statements) == 0


async def test_preclose_skips_closed_rows_and_has_no_per_entry_select(env):
    session, statements = env
    await _freeze(session, [_entry(f"m{i}", 3) for i in range(5)])
    calls: list = []
    r1 = await collect_preclose(session, price_of=_counting_provider(calls),
                                now=FROZEN + timedelta(hours=1), public_only=True,
                                within_hours=168.0)
    assert r1["updated"] == 5 and len(calls) == 5
    # After close: every row finalises once.
    r2 = await collect_preclose(session, price_of=_counting_provider(calls),
                                now=FROZEN + timedelta(hours=4), public_only=True,
                                within_hours=168.0)
    assert r2["closed"] == 5 and r2["updated"] == 0
    statements.clear()
    calls.clear()
    r3 = await collect_preclose(session, price_of=_counting_provider(calls),
                                now=FROZEN + timedelta(hours=5), public_only=True,
                                within_hours=168.0)
    assert r3 == {"updated": 0, "closed": 0, "rejected_after_close": 0, "unavailable": 0}
    assert calls == []
    assert _full_entry_reads(statements) == 0
    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 2  # candidate query (+ at most one batched row load), never N+1


async def test_preclose_creates_closed_row_for_entry_first_seen_after_close(env):
    session, _ = env
    await _freeze(session, [_entry("m1", 3)])
    r = await collect_preclose(session, price_of=_counting_provider([]),
                               now=FROZEN + timedelta(hours=10))
    assert r["closed"] == 1
    row = (await session.execute(select(ResearchPreCloseRow))).scalar_one()
    assert row.closed is True and row.observations == 0


async def test_preclose_respects_public_window_direction_and_lateness_filters(env):
    session, _ = env
    await _freeze(session, [
        _entry("pub", 3),
        _entry("hidden", 3, public=False),
        _entry("far", 500),                      # > within_hours
        _entry("flat", 3, direction="none"),
    ])
    late_cutoff = FROZEN + timedelta(hours=6)
    await _freeze(session, [_entry("late", 9)], cutoff=late_cutoff)
    cohort = (await session.execute(
        select(ResearchCohortRow).where(ResearchCohortRow.cutoff_at == late_cutoff))).scalar_one()
    cohort.excessively_late = True
    await session.commit()
    calls: list = []
    r = await collect_preclose(session, price_of=_counting_provider(calls),
                               now=FROZEN + timedelta(hours=1), public_only=True,
                               within_hours=168.0)
    assert sorted(calls) == ["pub"] and r["updated"] == 1
    # Without the public/window bounds, the hidden + far entries are tracked too.
    calls.clear()
    await collect_preclose(session, price_of=_counting_provider(calls),
                           now=FROZEN + timedelta(hours=2))
    assert sorted(calls) == ["far", "hidden", "pub"]
    assert await ResearchRepository(session).entry_count(cohort.id) == 1
