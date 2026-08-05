"""Universe degradation + honest exclusion (prompt section 5).

Covers: one/several unavailable tokens excluded with a reason, complete upstream failure rejected
(no cohort), minimum-viable-universe rejection, a degraded-but-valid cohort, and that a rejecting
funnel creates no cohort while a degraded funnel freezes with the degraded flag recorded.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation.research_constants import CADENCE_6H
from astrolabe.evaluation.research_engine import (
    ScoredScreen,
    UniverseFunnel,
    assess_universe,
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


def _funnel(discovered, usable):
    f = UniverseFunnel(discovered=discovered, usable=usable)
    for i in range(discovered - usable):
        f.exclusions.append({"market_id": f"x{i}", "reason": "no usable point-in-time token data"})
    return f


def test_assess_universe_decisions():
    # Complete upstream failure: nothing usable -> reject, no cohort.
    d = assess_universe(_funnel(30, 0))
    assert d.freeze is False and "no cohort" in d.reason
    # Below the minimum viable universe -> reject.
    assert assess_universe(_funnel(10, 4)).freeze is False
    # More than 60% excluded -> reject even if >= min usable.
    assert assess_universe(_funnel(30, 10)).freeze is False       # 20/30 excluded = 67%
    # 20-60% excluded -> freeze but DEGRADED.
    ok_degraded = assess_universe(_funnel(30, 20))                 # 10/30 = 33% excluded
    assert ok_degraded.freeze is True and ok_degraded.degraded is True
    # < 20% excluded -> healthy freeze.
    healthy = assess_universe(_funnel(30, 28))                     # ~7% excluded
    assert healthy.freeze is True and healthy.degraded is False


def test_exclusions_carry_a_reason():
    f = _funnel(5, 3)
    assert f.excluded == 2 and all("reason" in e for e in f.exclusions)
    assert f.exclusion_rate == pytest.approx(2 / 5)


def _screen(mid):
    return ScoredScreen(
        market_id=mid, condition_id=None, event_id=None, token_id=f"{mid}-y",
        market_question="Q", outcome_name="Yes", direction="up",
        momentum_direction="up", orderbook_direction="up", tradeflow_direction=None,
        strength=0.5, confidence=0.6, research_priority=90, n_families=2,
        evidence_families=[], component_scores=[], data_quality="good",
        entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5, spread=0.02,
        near_mid_depth=1000.0, liquidity=1000.0, volume=100.0, data_age_seconds=1.0,
        expected_close=CUTOFF + timedelta(days=5),
    )


async def test_rejecting_funnel_creates_no_cohort(session):
    inputs = build_entry_inputs([_screen("a"), _screen("b")], now=CUTOFF)
    # Complete failure funnel: 2 usable out of 40 discovered -> reject.
    funnel = _funnel(40, 2)
    result = await freeze_from_inputs(
        session, cadence=CADENCE_6H, cutoff_at=CUTOFF, inputs=inputs,
        calculation_version="t", frozen_at=CUTOFF, funnel=funnel,
    )
    assert result["frozen"] is False and result["rejected"] is True
    assert await ResearchRepository(session).list_cohorts() == []   # no misleading cohort


async def test_degraded_funnel_freezes_with_flag(session):
    screens = [_screen(f"m{i}") for i in range(8)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    funnel = _funnel(11, 8)   # 3/11 = 27% excluded -> degraded but valid
    result = await freeze_from_inputs(
        session, cadence=CADENCE_6H, cutoff_at=CUTOFF, inputs=inputs,
        calculation_version="t", frozen_at=CUTOFF, funnel=funnel,
    )
    assert result["frozen"] is True and result["degraded"] is True and result["excluded"] == 3
    cohort = (await ResearchRepository(session).list_cohorts(cadence=CADENCE_6H))[0]
    assert cohort.degraded is True and cohort.excluded_markets == 3
