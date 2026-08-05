"""Edge-research pipeline tests (prompt sections 2-6): full-universe freeze, roles, cadences,
immutability, idempotency, five-horizon outcomes and executable costs. All deterministic, in
memory, with clearly-marked fixtures and a controlled clock (no network, no wall-clock).
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation.errors import CohortFrozenError
from astrolabe.evaluation.execution import evaluate_execution, slippage_points
from astrolabe.evaluation.research_constants import (
    CADENCE_6H,
    CADENCE_DAILY,
    CADENCE_WEEKLY,
    ROLE_ABSTENTION,
    ROLE_OBSERVATION,
    ROLE_PUBLIC,
    ROLE_SHADOW,
)
from astrolabe.evaluation.research_engine import (
    ScoredScreen,
    build_entry_inputs,
    cadence_cutoff,
    classify_signal,
    freeze_from_inputs,
)
from astrolabe.evaluation.research_repository import ResearchRepository
from astrolabe.evaluation.research_tracking import (
    Quote,
    collect_due_forward,
    pending_forward_backlog,
)
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


def _screen(market, strength, direction, n_families, rp, *, dq="good", depth=1000.0):
    return ScoredScreen(
        market_id=market, condition_id=f"c{market}", event_id=None, token_id=f"{market}-yes",
        market_question=f"Q {market}", outcome_name="Yes", direction=direction,
        momentum_direction=direction, orderbook_direction=direction, tradeflow_direction=None,
        strength=strength, confidence=0.6, research_priority=rp, n_families=n_families,
        evidence_families=["price behaviour"] * min(n_families, 1),
        component_scores=[{"name": "unusual_return", "raw_value": 1.0,
                           "normalized_value": 0.5, "weight": 0.24}],
        data_quality=dq, entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5,
        spread=0.02, near_mid_depth=depth, liquidity=10000.0, volume=5000.0,
        data_age_seconds=10.0, expected_close=CUTOFF + timedelta(days=14),
    )


def test_cadence_cutoff_snaps_down():
    now = datetime(2026, 8, 5, 14, 37, tzinfo=UTC)
    assert cadence_cutoff(CADENCE_6H, now) == datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
    assert cadence_cutoff(CADENCE_DAILY, now) == datetime(2026, 8, 5, 0, 0, tzinfo=UTC)
    assert cadence_cutoff(CADENCE_WEEKLY, now) == datetime(2026, 8, 3, 0, 0, tzinfo=UTC)


def test_classification_is_selective():
    def c(direction, nf, st, dq="good"):
        return classify_signal(direction=direction, n_families=nf, strength=st, data_quality=dq)
    assert c("up", 2, 0.5) == "Directional opportunity"
    assert c("up", 0, 0.1) == "Directional observation"
    assert c(None, 0, 0.5) == "Non-directional anomaly"
    assert c(None, 0, 0.1) == "Insufficient evidence"
    assert c("up", 3, 0.9, "poor") == "Data-quality warning"


def test_full_universe_frozen_with_roles():
    # 12 directional + 2 anomalies + 1 weak: the FULL universe of 15 must be stored, not top-10.
    screens = [_screen(f"d{i}", 0.5, "up", 2, rp=90 - i) for i in range(12)]
    screens += [_screen("a1", 0.5, None, 0, rp=0), _screen("a2", 0.45, None, 0, rp=0)]
    screens += [_screen("w1", 0.1, None, 0, rp=0)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    assert len(inputs) == 15  # nothing dropped
    roles = [i.role for i in inputs]
    assert roles.count(ROLE_PUBLIC) == 10          # only the top 10 directional are public
    assert roles.count(ROLE_SHADOW) == 2           # remaining directional are shadow
    assert roles.count(ROLE_OBSERVATION) == 2      # anomalies
    assert roles.count(ROLE_ABSTENTION) == 1       # weak
    # ranks are dense over directional entries, public first
    ranked = sorted([i.rank for i in inputs if i.rank is not None])
    assert ranked == list(range(1, 13))


async def test_freeze_is_idempotent_and_immutable(session):
    screens = [_screen(f"d{i}", 0.5, "up", 2, rp=90 - i) for i in range(3)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    s1 = await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                  inputs=inputs, calculation_version="test-1", frozen_at=CUTOFF)
    assert s1["frozen"] and s1["universe_size"] == 3 and not s1["already_frozen"]
    # Second freeze of the same (cadence, cutoff) does nothing new.
    s2 = await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                                  inputs=inputs, calculation_version="test-1", frozen_at=CUTOFF)
    assert s2["already_frozen"] is True
    repo = ResearchRepository(session)
    cohorts = await repo.list_cohorts(cadence=CADENCE_6H)
    assert len(cohorts) == 1  # no duplicate cohort
    # Adding to a frozen cohort is refused.
    with pytest.raises(CohortFrozenError):
        await repo.add_entry(cohorts[0], inputs[0])  # type: ignore[arg-type]


async def test_distinct_cadences_are_independent(session):
    screens = [_screen("d0", 0.5, "up", 2, rp=90)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    for cadence in (CADENCE_6H, CADENCE_DAILY, CADENCE_WEEKLY):
        await freeze_from_inputs(session, cadence=cadence, cutoff_at=CUTOFF,
                                 inputs=inputs, calculation_version="test-1", frozen_at=CUTOFF)
    repo = ResearchRepository(session)
    counts = await repo.count_cohorts_by_cadence()
    assert counts == {CADENCE_6H: 1, CADENCE_DAILY: 1, CADENCE_WEEKLY: 1}


async def test_forward_collection_is_causal_and_idempotent(session):
    screens = [_screen("d0", 0.5, "up", 2, rp=90)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                             inputs=inputs, calculation_version="test-1", frozen_at=CUTOFF)

    async def price_of(mid, tok):
        return Quote(
            midpoint=0.56, best_bid=0.55, best_ask=0.57, spread=0.02, near_mid_depth=1000.0
        )

    # Before any horizon elapses, nothing is recorded (causal).
    r0 = await collect_due_forward(
        session, now=CUTOFF + timedelta(minutes=30), price_of=price_of
    )
    assert r0["written"] == 0
    # After 24h, the 1h/6h/24h horizons are due (not 7d).
    r1 = await collect_due_forward(
        session, now=CUTOFF + timedelta(hours=24, minutes=5), price_of=price_of
    )
    assert r1["written"] == 3
    # Re-running is idempotent: no new writes, all already present.
    r2 = await collect_due_forward(
        session, now=CUTOFF + timedelta(hours=24, minutes=6), price_of=price_of
    )
    assert r2["written"] == 0 and r2["already_present"] >= 3
    backlog = await pending_forward_backlog(session)
    assert backlog["backlog"] == 0  # 7d not due yet, so not counted as backlog


async def test_horizon_predating_freeze_is_invalid_not_backfilled(session):
    # A cohort frozen LATER than a horizon's target (e.g. a weekly freeze run mid-week) must never
    # backfill that horizon with a current price: it is recorded terminal-invalid (causal guard).
    screens = [_screen("d0", 0.5, "up", 2, rp=90)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    # Freeze 2 days AFTER the cut-off, so 1h/6h/24h all predate the freeze.
    late = CUTOFF + timedelta(days=2)
    await freeze_from_inputs(session, cadence=CADENCE_WEEKLY, cutoff_at=CUTOFF,
                             inputs=inputs, calculation_version="test-1", frozen_at=late)

    async def price_of(mid, tok):
        return Quote(midpoint=0.9, best_bid=0.89, best_ask=0.91, spread=0.02, near_mid_depth=1000.0)

    r = await collect_due_forward(session, now=late + timedelta(minutes=5), price_of=price_of)
    assert r["invalid_predates_freeze"] == 3 and r["written"] == 0  # 1h/6h/24h all invalid
    repo = ResearchRepository(session)
    cohort = (await repo.list_cohorts(cadence=CADENCE_WEEKLY))[0]
    entry = (await repo.get_entries(cohort.id))[0]
    fwd = await repo.get_forward(entry.id)
    assert fwd["24h"].midpoint is None and "predates the freeze" in fwd["24h"].unavailable_reason


async def test_forward_unavailable_reason_when_no_quote(session):
    screens = [_screen("d0", 0.5, "up", 2, rp=90)]
    inputs = build_entry_inputs(screens, now=CUTOFF)
    await freeze_from_inputs(session, cadence=CADENCE_6H, cutoff_at=CUTOFF,
                             inputs=inputs, calculation_version="test-1", frozen_at=CUTOFF)

    async def no_price(mid, tok):
        return None

    r = await collect_due_forward(session, now=CUTOFF + timedelta(hours=7), price_of=no_price)
    assert r["unavailable"] == 2  # 1h + 6h due, both unavailable
    repo = ResearchRepository(session)
    cohort = (await repo.list_cohorts(cadence=CADENCE_6H))[0]
    entry = (await repo.get_entries(cohort.id))[0]
    fwd = await repo.get_forward(entry.id)
    assert fwd["1h"].unavailable_reason is not None and fwd["1h"].midpoint is None


def test_execution_costs_reduce_a_favourable_move():
    r = evaluate_execution(direction="up", entry_midpoint=0.5, forward_midpoint=0.56,
                           entry_spread=0.02, entry_depth=1000.0, forward_spread=0.02,
                           forward_depth=1000.0)
    assert r.midpoint_move == pytest.approx(0.06)
    assert r.executable_move < r.midpoint_move   # costs always reduce the move
    assert r.round_trip_cost > 0


def test_execution_unavailable_without_depth():
    r = evaluate_execution(direction="up", entry_midpoint=0.5, forward_midpoint=0.56,
                           entry_spread=0.02, entry_depth=None, forward_spread=0.02,
                           forward_depth=None)
    assert r.executable_move is None and r.unavailable_reason is not None
    assert slippage_points(None, 100.0) is None  # missing depth stays missing, never free
