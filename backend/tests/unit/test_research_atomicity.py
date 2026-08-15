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

    # Make the bulk entry-insert blow up, simulating a mid-freeze failure. (Freeze now writes all
    # entries via the batched add_entries; the atomic-rollback guarantee is unchanged.)
    async def flaky(self, cohort, entries):
        raise RuntimeError("simulated mid-freeze failure")

    monkeypatch.setattr(ResearchRepository, "add_entries", flaky)

    with pytest.raises(RuntimeError, match="simulated mid-freeze failure"):
        await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=CUTOFF)

    # Atomic: the whole unit rolled back, so NO cohort and NO entries are visible.
    repo = ResearchRepository(session)
    assert await repo.list_cohorts() == []
    assert await repo.incomplete_cohorts() == []


async def test_retry_after_failure_succeeds_cleanly(session, monkeypatch):
    inputs = build_entry_inputs([_screen("a"), _screen("b")], now=CUTOFF)
    original = ResearchRepository.add_entries
    state = {"fail": True}

    async def flaky(self, cohort, entries):
        if state["fail"]:
            state["fail"] = False
            raise RuntimeError("boom")
        return await original(self, cohort, entries)

    monkeypatch.setattr(ResearchRepository, "add_entries", flaky)
    with pytest.raises(RuntimeError):
        await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=CUTOFF)
    # Retry (add_entries no longer fails): a clean, frozen, complete cohort results.
    summary = await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                       inputs=inputs, calculation_version="t", frozen_at=CUTOFF)
    assert summary["frozen"] and summary["universe_size"] == 2
    repo = ResearchRepository(session)
    assert len(await repo.list_cohorts()) == 1
    assert await repo.incomplete_cohorts() == []


async def test_repair_skips_a_cohort_that_became_frozen_after_the_snapshot(session, monkeypatch):
    # DB review CRITICAL-2: if a freeze completes between repair's snapshot and the delete, repair
    # must re-check and SKIP the now-frozen cohort rather than destroy real evidence.
    good = build_entry_inputs([_screen("a")], now=CUTOFF)
    await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                             inputs=good, calculation_version="t", frozen_at=CUTOFF)
    repo = ResearchRepository(session)
    cohort = (await repo.list_cohorts(cadence=CADENCE_6H))[0]
    assert cohort.frozen is True

    # Simulate a STALE snapshot that still reports the (now frozen) cohort as not frozen.
    async def stale_snapshot():
        return [{"id": cohort.id, "cadence": CADENCE_6H, "cutoff_at": cohort.cutoff_at.isoformat(),
                 "frozen": False, "universe_size": 0, "entries": 0, "reason": "stale"}]

    monkeypatch.setattr(repo, "incomplete_cohorts", stale_snapshot)
    result = await repo.repair_incomplete()
    assert result["removed_incomplete"] == []            # nothing destroyed
    assert len(result["skipped_now_frozen"]) == 1        # re-check caught the race
    assert len(await repo.list_cohorts()) == 1           # the valid frozen cohort survives


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
