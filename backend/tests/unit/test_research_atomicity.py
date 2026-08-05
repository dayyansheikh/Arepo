"""Freeze atomicity + partial-cohort repair (prompt section 4).

Injects a failure midway through entry creation and proves NO cohort becomes visible (atomic
rollback), and proves the repair removes a never-frozen incomplete cohort while leaving valid frozen
cohorts untouched.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation.research_constants import CADENCE_6H, CADENCE_DAILY
from astrolabe.evaluation.research_engine import (
    ScoredScreen,
    build_entry_inputs,
    freeze_from_inputs,
)
from astrolabe.evaluation.research_repository import ResearchRepository
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

CUTOFF = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s
    await engine_.dispose()


def _screen(mid):
    return ScoredScreen(
        market_id=mid, condition_id=None, event_id=None, token_id=f"{mid}-y",
        market_question="Q", outcome_name="Yes", direction="up",
        momentum_direction="up", orderbook_direction="up", tradeflow_direction=None,
        strength=0.5, confidence=0.6, research_priority=90, n_families=2,
        evidence_families=["price behaviour"], component_scores=[],
        data_quality="good", entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5,
        spread=0.02, near_mid_depth=1000.0, liquidity=1000.0, volume=100.0,
        data_age_seconds=1.0, expected_close=CUTOFF + timedelta(days=5),
    )


async def test_failure_midway_leaves_no_visible_cohort(session, monkeypatch):
    inputs = build_entry_inputs([_screen("a"), _screen("b"), _screen("c")], now=CUTOFF)

    # Make the THIRD add_entry blow up, simulating a mid-freeze failure.
    original = ResearchRepository.add_entry
    calls = {"n": 0}

    async def flaky(self, cohort, e):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("simulated mid-freeze failure")
        return await original(self, cohort, e)

    monkeypatch.setattr(ResearchRepository, "add_entry", flaky)

    with pytest.raises(RuntimeError, match="simulated mid-freeze failure"):
        await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=CUTOFF)

    # Atomic: the whole unit rolled back, so NO cohort and NO entries are visible.
    repo = ResearchRepository(session)
    assert await repo.list_cohorts() == []
    assert await repo.incomplete_cohorts() == []


async def test_retry_after_failure_succeeds_cleanly(session, monkeypatch):
    inputs = build_entry_inputs([_screen("a"), _screen("b")], now=CUTOFF)
    original = ResearchRepository.add_entry
    state = {"fail": True}

    async def flaky(self, cohort, e):
        if state["fail"] and e.market_id == "b":
            state["fail"] = False
            raise RuntimeError("boom")
        return await original(self, cohort, e)

    monkeypatch.setattr(ResearchRepository, "add_entry", flaky)
    with pytest.raises(RuntimeError):
        await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=CUTOFF)
    # Retry (add_entry no longer fails): a clean, frozen, complete cohort results.
    summary = await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                       inputs=inputs, calculation_version="t", frozen_at=CUTOFF)
    assert summary["frozen"] and summary["universe_size"] == 2
    repo = ResearchRepository(session)
    assert len(await repo.list_cohorts()) == 1
    assert await repo.incomplete_cohorts() == []


async def test_repair_removes_never_frozen_but_keeps_valid_frozen(session):
    repo = ResearchRepository(session)
    # A valid, frozen, complete cohort.
    good = build_entry_inputs([_screen("a")], now=CUTOFF)
    await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                             inputs=good, calculation_version="t", frozen_at=CUTOFF)
    # A never-frozen incomplete cohort (simulate an interrupted freeze that somehow committed).
    cohort, _ = await repo.get_or_create_cohort(
        cadence=CADENCE_DAILY, cutoff_at=CUTOFF, model_version="m", calculation_version="t"
    )
    await session.commit()
    incomplete = await repo.incomplete_cohorts()
    assert len(incomplete) == 1 and incomplete[0]["cadence"] == CADENCE_DAILY

    result = await repo.repair_incomplete()
    assert len(result["removed_incomplete"]) == 1
    assert result["frozen_anomalies"] == []
    remaining = await repo.list_cohorts()
    assert len(remaining) == 1 and remaining[0].cadence == CADENCE_6H  # valid frozen kept
    # Idempotent: a second repair does nothing.
    assert (await repo.repair_incomplete())["removed_incomplete"] == []
