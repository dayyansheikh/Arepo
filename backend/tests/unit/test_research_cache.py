"""Research endpoint cache: recompute only when stored inputs change (infra 2026-10-11)."""
from datetime import UTC, datetime

import pytest

import astrolabe.storage.migrate  # noqa: F401  (registers every ORM table)
from astrolabe.api import research_cache
from astrolabe.evaluation.research_models import ResearchCohortRow
from astrolabe.storage.db import Base, make_engine, make_sessionmaker


@pytest.fixture
async def session(monkeypatch):
    monkeypatch.setattr(research_cache, "_enabled", lambda: True)
    research_cache.clear()
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with make_sessionmaker(engine)() as s:
        yield s
    research_cache.clear()
    await engine.dispose()


async def test_recomputes_only_on_data_change_and_bounds_entries(session, monkeypatch):
    calls = []

    async def compute():
        calls.append(1)
        return {"n": len(calls)}

    assert await research_cache.cached(session, "k", compute) == {"n": 1}
    assert await research_cache.cached(session, "k", compute) == {"n": 1}
    session.add(ResearchCohortRow(
        cadence="6h", cutoff_at=datetime(2026, 8, 1, tzinfo=UTC), model_version="m",
        calculation_version="c", provenance_class="prospective", frozen=True,
        lateness_seconds=0, late=False, excessively_late=False, universe_size=0,
        directional_count=0, public_selection_count=0, shadow_count=0, observation_count=0,
        abstention_count=0, excluded_markets=0, degraded=False,
        created_at=datetime(2026, 8, 1, tzinfo=UTC)))
    await session.commit()
    assert await research_cache.cached(session, "k", compute) == {"n": 2}
    # max_age forces recompute
    assert await research_cache.cached(session, "k", compute, max_age=0) == {"n": 3}
    monkeypatch.setattr(research_cache, "MAX_ENTRIES", 2)
    for i in range(5):
        await research_cache.cached(session, f"x{i}", compute)
    assert len(research_cache._entries) == 2


async def test_disabled_outside_production(session, monkeypatch):
    monkeypatch.setattr(research_cache, "_enabled", lambda: False)
    calls = []

    async def compute():
        calls.append(1)
        return 1

    await research_cache.cached(session, "k", compute)
    await research_cache.cached(session, "k", compute)
    assert len(calls) == 2


async def test_failing_keys_leave_no_locks(session):
    async def boom():
        raise ValueError("bad params")

    for i in range(1000):
        with pytest.raises(ValueError):
            await research_cache.cached(session, f"bad:{i}", boom)
    assert research_cache._locks == {}
    assert research_cache._entries == {}


async def test_data_version_tracks_research_entries(session):
    from datetime import timedelta

    from astrolabe.evaluation.research_repository import EntryInput, ResearchRepository

    cutoff = datetime(2026, 8, 2, tzinfo=UTC)
    repo = ResearchRepository(session)
    cohort, _ = await repo.get_or_create_cohort(
        cadence="6h", cutoff_at=cutoff, model_version="m", calculation_version="c")
    await session.commit()
    before = await research_cache.data_version(session)
    await repo.add_entry(cohort, EntryInput(
        role="public_selection", rank=1, walk_forward_partition="live", market_id="m1",
        condition_id="c1", event_id=None, token_id="t1", market_question="Q", outcome_name="Yes",
        direction="up", momentum_direction="up", orderbook_direction=None,
        tradeflow_direction=None, signal_classification="x", strength=0.5, confidence=0.5,
        research_priority=50, n_families=1, evidence_families=[], component_scores=[],
        component_availability={}, data_quality="good", entry_price=0.5, best_bid=0.49,
        best_ask=0.51, midpoint=0.5, spread=0.02, near_mid_depth=1.0, liquidity=1.0,
        volume=1.0, data_age_seconds=1.0, expected_close=cutoff + timedelta(days=1),
        time_remaining_hours=24, intended_horizons=["1h"], bucket="closing_6_24h",
        overall_rank_30d=1, public_selected=True))
    await session.commit()
    assert await research_cache.data_version(session) != before
