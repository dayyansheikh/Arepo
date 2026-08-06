"""Freeze-to-close collection tests (final-completion prompt C4, C5, F1).

Deterministic in-memory. Proves the collector records the first valid post-freeze observation, keeps
the latest valid pre-close quote, detects close and finalises, REJECTS quotes at/after close, is
idempotent, and never infers resolution from price.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation.research_constants import ROLE_PUBLIC
from astrolabe.evaluation.research_engine import freeze_from_inputs
from astrolabe.evaluation.research_preclose import (
    collect_preclose,
    freeze_to_close_result,
    preclose_for_cohort,
)
from astrolabe.evaluation.research_repository import EntryInput, ResearchRepository
from astrolabe.evaluation.research_tracking import Quote
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

CUTOFF = datetime(2026, 8, 6, 0, 0, 0, tzinfo=UTC)
FROZEN = datetime(2026, 8, 6, 0, 0, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s
    await engine_.dispose()


def _entry(market, direction, close_hours, midpoint=0.5) -> EntryInput:
    return EntryInput(
        role=ROLE_PUBLIC, rank=1, walk_forward_partition="live", market_id=market,
        condition_id=f"c{market}", event_id=None, token_id=f"{market}-y",
        market_question=f"Q{market}", outcome_name="Yes", direction=direction,
        momentum_direction=direction, orderbook_direction=direction, tradeflow_direction=None,
        signal_classification="Directional opportunity", strength=0.6, confidence=0.6,
        research_priority=80, n_families=2, evidence_families=["price behaviour"],
        component_scores=[], component_availability={}, data_quality="good",
        entry_price=midpoint, best_bid=midpoint - 0.01, best_ask=midpoint + 0.01, midpoint=midpoint,
        spread=0.02, near_mid_depth=1000.0, liquidity=25000.0, volume=5000.0, data_age_seconds=10.0,
        expected_close=FROZEN + timedelta(hours=close_hours),
        time_remaining_hours=close_hours,
        intended_horizons=["1h", "6h"],
        bucket="closing_0_6h", overall_rank_30d=1, public_selected=True,
    )


async def _freeze(session, entries):
    return await freeze_from_inputs(
        session, cadence="6h", cutoff_at=CUTOFF, inputs=entries,
        model_version="m", calculation_version="c", frozen_at=FROZEN,
        provenance_class="prospective",
    )


def _provider(quotes: dict):
    async def price_of(market_id, token_id):
        return quotes.get(market_id)
    return price_of


async def test_first_and_latest_valid_quote(session):
    await _freeze(session, [_entry("m1", "up", close_hours=6, midpoint=0.50)])
    now1 = FROZEN + timedelta(hours=1)
    q1 = Quote(midpoint=0.55, best_bid=0.54, best_ask=0.56, spread=0.02, near_mid_depth=1000.0,
               source_timestamp=now1)
    s1 = await collect_preclose(session, price_of=_provider({"m1": q1}), now=now1)
    assert s1["updated"] == 1
    now2 = FROZEN + timedelta(hours=3)
    q2 = Quote(midpoint=0.58, best_bid=0.57, best_ask=0.59, spread=0.02, near_mid_depth=1000.0,
               source_timestamp=now2)
    await collect_preclose(session, price_of=_provider({"m1": q2}), now=now2)
    rows = await preclose_for_cohort(session, 1)
    row = next(iter(rows.values()))
    assert row.first_midpoint == 0.55           # first observation kept
    assert row.last_midpoint == 0.58            # latest valid quote
    assert row.observations == 2

    entry = (await ResearchRepository(session).get_entries(1))[0]
    res = freeze_to_close_result(entry, row)
    assert res["state"] == "open_latest"
    assert res["freeze_midpoint"] == 0.50 and res["preclose_midpoint"] == 0.58
    assert res["movement"] == pytest.approx(0.08)
    assert res["result"] == "moved_expected"    # up call, price rose


async def test_quote_after_close_is_rejected_and_final_preserved(session):
    await _freeze(session, [_entry("m1", "up", close_hours=6, midpoint=0.50)])
    pre = FROZEN + timedelta(hours=5)
    good = Quote(midpoint=0.60, best_bid=0.59, best_ask=0.61, spread=0.02, near_mid_depth=1000.0,
                 source_timestamp=pre)
    await collect_preclose(session, price_of=_provider({"m1": good}), now=pre)
    # A quote whose SOURCE timestamp is at/after close is rejected; keep the last valid pre-close.
    after = FROZEN + timedelta(hours=7)
    late_ts = FROZEN + timedelta(hours=6, minutes=1)
    late_quote = Quote(midpoint=0.99, best_bid=0.98, best_ask=1.0, spread=0.02,
                       near_mid_depth=1000.0, source_timestamp=late_ts)
    s = await collect_preclose(session, price_of=_provider({"m1": late_quote}), now=after)
    assert s["closed"] == 1                       # close detected at now >= close
    rows = await preclose_for_cohort(session, 1)
    row = next(iter(rows.values()))
    assert row.last_midpoint == 0.60              # final pre-close preserved, not 0.99
    assert row.closed is True and row.closed_detected_at is not None


async def test_idempotent_no_double_count(session):
    await _freeze(session, [_entry("m1", "down", close_hours=6, midpoint=0.50)])
    now = FROZEN + timedelta(hours=1)
    q = Quote(midpoint=0.45, best_bid=0.44, best_ask=0.46, spread=0.02, near_mid_depth=1000.0,
              source_timestamp=now)
    await collect_preclose(session, price_of=_provider({"m1": q}), now=now)
    # Same instant, same quote: one more observation row update, never a duplicate PreClose row.
    await collect_preclose(session, price_of=_provider({"m1": q}), now=now)
    rows = await preclose_for_cohort(session, 1)
    assert len(rows) == 1


async def test_pending_when_no_quote_yet(session):
    await _freeze(session, [_entry("m1", "up", close_hours=6)])
    entry = (await ResearchRepository(session).get_entries(1))[0]
    assert freeze_to_close_result(entry, None)["state"] == "pending"
    # A collection with no available quote leaves it pending + unavailable, never fabricated.
    s = await collect_preclose(session, price_of=_provider({}), now=FROZEN + timedelta(hours=1))
    assert s["unavailable"] == 1
