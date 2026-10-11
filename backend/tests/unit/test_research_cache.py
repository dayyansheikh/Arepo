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
