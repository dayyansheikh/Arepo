"""Prospective-timestamp / causal-origin tests (causal-timing audit).

Proves the causal origin is frozen_at, not the cutoff_at cadence label: horizons run from frozen_at,
a late freeze is never presented as a scheduled-boundary prediction, moderately-late cohorts stay
causally valid and in the sample, excessively-late cohorts are excluded from comparable performance,
early observations are rejected, and the research status reports scheduled/actual/lateness.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation.research_constants import CADENCE_6H, CADENCE_WEEKLY
from astrolabe.evaluation.research_engine import (
    ScoredScreen,
    build_entry_inputs,
    freeze_from_inputs,
)
from astrolabe.evaluation.research_service import ResearchReadService
from astrolabe.evaluation.research_tracking import Quote, collect_due_forward
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

CUTOFF = datetime(2026, 8, 3, 0, 0, 0, tzinfo=UTC)   # a scheduled Monday boundary


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
        evidence_families=[], component_scores=[], data_quality="good",
        entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5, spread=0.02,
        near_mid_depth=2000.0, liquidity=2000.0, volume=100.0, data_age_seconds=1.0,
        expected_close=CUTOFF + timedelta(days=30),
    )


async def _price(mid, tok):
    return Quote(midpoint=0.56, best_bid=0.55, best_ask=0.57, spread=0.02, near_mid_depth=2000.0)


async def test_on_time_freeze_is_not_late(session):
    inputs = build_entry_inputs([_screen("m")], now=CUTOFF)
    frozen = CUTOFF + timedelta(minutes=5)   # cron fires ~5 min after the boundary
    s = await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=frozen)
    assert s["lateness_seconds"] == pytest.approx(300)
    assert s["late"] is False and s["excessively_late"] is False


async def test_moderately_late_cohort_stays_causally_valid_and_in_sample(session):
    # Frozen 30 min late: flagged "late" but NOT excessively late, so it remains in the performance
    # sample, and its 1h outcome (measured from frozen_at) is a genuine forward.
    inputs = build_entry_inputs([_screen("m")], now=CUTOFF)
    frozen = CUTOFF + timedelta(minutes=30)
    s = await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=frozen)
    assert s["late"] is True and s["excessively_late"] is False
    r = await collect_due_forward(
        session, now=frozen + timedelta(hours=1, minutes=1), price_of=_price
    )
    assert r["written"] == 1
    h1 = await ResearchReadService(session).horizon_analysis("1h")
    assert h1["evaluable"] == 1                      # stays in comparable performance


async def test_excessively_late_cohort_is_excluded_from_performance(session):
    # A weekly cohort frozen 3 days after its Monday boundary: causally valid (origin=frozen_at) but
    # excluded from the comparable-performance sample so it can't be shown as a Monday prediction.
    inputs = build_entry_inputs([_screen("m")], now=CUTOFF)
    frozen = CUTOFF + timedelta(days=3)
    s = await freeze_from_inputs(session, cadence=CADENCE_WEEKLY, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=frozen)
    assert s["excessively_late"] is True
    await collect_due_forward(session, now=frozen + timedelta(hours=25), price_of=_price)
    svc = ResearchReadService(session)
    h24 = await svc.horizon_analysis("24h")
    assert h24["evaluable"] == 0                     # excluded despite having an outcome
    status = await svc.status()
    assert status["excessively_late_cohorts_excluded"] == 1


async def test_horizon_due_after_market_close_is_terminal_not_pending(session):
    """A market that CLOSED before its horizon became due must not stay 'pending' forever
    (final-completion prompt §11): the collector records a terminal closed-before-horizon
    observation (no live post-close fetch), so freeze-to-close is the correct evaluation."""
    sc = _screen("m")
    sc = ScoredScreen(**{**sc.__dict__, "expected_close": CUTOFF + timedelta(hours=2)})
    inputs = build_entry_inputs([sc], now=CUTOFF)
    s = await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="t", frozen_at=CUTOFF)
    assert s["frozen"]
    # Collect at +7h: the 1h and 6h horizons are due, but the market closed at +2h. The 6h horizon
    # target (+6h) is after close, and the market is closed now, so it is recorded terminally.
    fired = False

    async def _no_price(mid, tok):
        nonlocal fired
        fired = True   # a live fetch must NOT happen for a closed market
        return _price(mid, tok)

    r = await collect_due_forward(session, now=CUTOFF + timedelta(hours=7), price_of=_no_price)
    assert r["closed_before_horizon"] >= 1
    assert fired is False                              # no live post-close fetch
    # The identity holds: every due horizon has a terminal state, nothing left silently pending.
    from sqlalchemy import select

    from astrolabe.evaluation.research_models import ResearchForwardRow
    rows = (await session.execute(select(ResearchForwardRow))).scalars().all()
    closed = [x for x in rows if x.unavailable_reason and "closed before" in x.unavailable_reason]
    assert len(closed) >= 1 and all(x.midpoint is None for x in closed)


async def test_status_reports_scheduled_actual_and_lateness(session):
    inputs = build_entry_inputs([_screen("m")], now=CUTOFF)
    frozen = CUTOFF + timedelta(minutes=30)
    await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                             inputs=inputs, calculation_version="t", frozen_at=frozen)
    status = await ResearchReadService(session).status()
    assert status["late_cohorts"] == 1
    run = status["latest_run"]
    # The status shows BOTH the scheduled boundary and the actual freeze time, with lateness.
    assert run["scheduled_for"].startswith("2026-08-03T00:00")
    assert run["frozen_at"].startswith("2026-08-03T00:30")
    assert run["evaluation_origin_at"] == run["frozen_at"]
    assert run["lateness_seconds"] == pytest.approx(1800)
    assert run["late"] is True
