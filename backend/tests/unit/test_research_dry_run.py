"""Production-equivalent end-to-end dry run (prompt section 17B), deterministic and in memory.

Proves the whole sequence works WITHOUT a browser and without the wall clock: freeze 6h/daily/weekly
cohorts of the full universe with roles, collect 1h/6h/24h forward outcomes with a controlled clock
and a fixture price feed, record a final resolution, then compute midpoint + executable results,
baselines, ablation and the real research status. Test rows are clearly marked and the sample stays
below the edge minimum, so nothing here can be mistaken for real prospective evidence.

The only sanctioned use of a controlled clock and fixtures is exactly this: proving the pipeline,
not manufacturing a performance record.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation.research_constants import CADENCE_6H, CADENCE_DAILY, CADENCE_WEEKLY
from astrolabe.evaluation.research_engine import (
    ScoredScreen,
    build_entry_inputs,
    freeze_from_inputs,
)
from astrolabe.evaluation.research_service import ResearchReadService
from astrolabe.evaluation.research_tracking import (
    Quote,
    ResolutionInput,
    collect_due_forward,
    record_resolution,
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


def _screen(mid, direction, mom, ob, rp, strength=0.5):
    return ScoredScreen(
        market_id=mid, condition_id=f"c{mid}", event_id=None, token_id=f"{mid}-yes",
        market_question=f"Q {mid}", outcome_name="Yes", direction=direction,
        momentum_direction=mom, orderbook_direction=ob, tradeflow_direction=None,
        strength=strength, confidence=0.6, research_priority=rp, n_families=2,
        evidence_families=["price behaviour", "order book"],
        component_scores=[{"name": "unusual_return", "raw_value": 1.0,
                           "normalized_value": 0.5, "weight": 0.24},
                          {"name": "spread_change", "raw_value": 0.1,
                           "normalized_value": 0.3, "weight": 0.08}],
        data_quality="good", entry_price=0.5, best_bid=0.49, best_ask=0.51, midpoint=0.5,
        spread=0.02, near_mid_depth=3000.0, liquidity=20000.0, volume=8000.0,
        data_age_seconds=10.0, expected_close=CUTOFF + timedelta(days=10),
    )


def _universe():
    # 3 directional (2 will be public, 1 shadow if PUBLIC_SELECTION_SIZE were smaller; here all
    # public), 1 non-directional anomaly (observation), 1 weak (abstention). Full universe = 5.
    return [
        _screen("d1", "up", "up", "up", rp=90),
        _screen("d2", "down", "down", "down", rp=80),
        _screen("d3", "up", "up", "down", rp=70),
        _screen("a1", None, None, None, rp=0, strength=0.5),   # non-directional anomaly
        _screen("w1", None, None, None, rp=0, strength=0.1),   # insufficient -> abstention
    ]


async def test_end_to_end_dry_run(session):
    screens = _universe()
    inputs = build_entry_inputs(screens, now=CUTOFF)

    # 1-9. Freeze all three cadences from the full screened universe.
    summaries = {}
    for cadence in (CADENCE_6H, CADENCE_DAILY, CADENCE_WEEKLY):
        summaries[cadence] = await freeze_from_inputs(
            session, cadence=cadence, cutoff_at=CUTOFF, inputs=inputs,
            calculation_version="dry-run", frozen_at=CUTOFF,
        )
    # 10-11. Full universe + roles persisted (not only the public top-N).
    assert summaries[CADENCE_6H]["universe_size"] == 5
    assert summaries[CADENCE_6H]["directional"] == 3
    assert summaries[CADENCE_6H]["observation"] == 1
    assert summaries[CADENCE_6H]["abstention"] == 1

    # 12-15. Collect 1h/6h/24h outcomes with a controlled clock + fixture feed (7d not yet due).
    async def price_of(market_id, token_id):
        # "up" markets drift up, "down" markets drift down (a clean, favourable fixture move).
        up = market_id in ("d1", "d3")
        mid = 0.56 if up else 0.44
        return Quote(midpoint=mid, best_bid=mid - 0.01, best_ask=mid + 0.01,
                     spread=0.02, near_mid_depth=3000.0)

    r = await collect_due_forward(session, now=CUTOFF + timedelta(hours=25), price_of=price_of)
    assert r["written"] > 0                       # observations recorded across all three cohorts

    # 16. Record a final resolution (fixture) for one market.
    changed = await record_resolution(session, ResolutionInput(
        market_id="d1", condition_id="cd1", resolved=True, resolved_outcome="Yes",
        resolved_token_id="d1-yes", resolved_at=CUTOFF + timedelta(days=10), source="fixture",
    ))
    assert changed is True

    # 17-22. Midpoint + executable results, baselines, ablation, status.
    svc = ResearchReadService(session)
    h24 = await svc.horizon_analysis("24h")
    assert h24["evaluable"] == 9                  # 3 directional x 3 cadences
    bl = h24["baselines"]
    # Fixture was constructed so Arepo's direction matched the move on every directional entry.
    assert bl["full_arepo"]["correct"] == 9 and bl["full_arepo"]["incorrect"] == 0
    assert bl["full_arepo"]["mean_executable_move"] is not None   # depth present -> executable
    assert h24["arepo_momentum_agreement"] == 1.0                 # Arepo == momentum here
    assert "without_momentum" in h24["ablation"]

    status = await svc.status()
    assert status["cohort_counts_by_cadence"] == {
        CADENCE_6H: 1, CADENCE_DAILY: 1, CADENCE_WEEKLY: 1,
    }
    assert status["total_frozen_markets"] == 15   # 5 markets x 3 cadences
    assert status["public_selections"] == 9       # 3 directional x 3 cadences (all within top-10)
    assert status["abstentions"] == 3
    assert status["resolved_markets"] == 1
    # Coverage counts the WHOLE universe (abstention controls get outcomes too, by design);
    # only horizon_analysis filters to directional entries for the baselines.
    assert status["horizon_coverage"]["24h"]["evaluable"] == 15
    assert status["horizon_coverage"]["7d"]["evaluable"] == 0    # 7d not yet due (causal)
    # 23. Edge verdict stays NOT supported: the sample is far below the predeclared minimum.
    assert status["edge"]["edge_supported"] is False
    assert status["calibration"]["available"] is False
