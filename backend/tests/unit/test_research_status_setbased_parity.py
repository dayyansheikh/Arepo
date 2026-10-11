"""The set-based research status/horizon analysis equals the old per-entry loops (infra 2026-10-11).

The reference functions below are the pre-fix implementations (full-row load + one get_forward per
entry per horizon), kept verbatim in logic. A randomised universe covers excluded cohorts
(excessively late, non-prospective, unfrozen), non-reportable partitions, missing/NULL forward
midpoints, repeated markets across cohorts (dedup by causal origin) and every horizon.
"""
import random
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

import astrolabe.storage.migrate  # noqa: F401  (registers every ORM table)
from astrolabe.evaluation.research_analysis import ablation_table, baseline_table
from astrolabe.evaluation.research_constants import RESEARCH_HORIZONS, ROLES
from astrolabe.evaluation.research_engine import freeze_from_inputs
from astrolabe.evaluation.research_models import ResearchCohortRow
from astrolabe.evaluation.research_repository import EntryInput, ResearchRepository
from astrolabe.evaluation.research_service import ResearchReadService, _obs_for_horizon, _utc
from astrolabe.evaluation.research_walk_forward import is_reportable
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

BASE = datetime(2026, 8, 1, tzinfo=UTC)
PARTS = ["live", "heldout", "development", "threshold"]


def _inp(rng, market, role, part) -> EntryInput:
    d = rng.choice(["up", "down", None, "none"])
    return EntryInput(
        role=role, rank=rng.choice([None, 1, 2, 3, 5]), walk_forward_partition=part,
        market_id=market, condition_id=f"c{market}", event_id=None, token_id=f"{market}-y",
        market_question=f"Q{market}", outcome_name="Yes", direction=d,
        momentum_direction=rng.choice(["up", "down", None]),
        orderbook_direction=rng.choice(["up", "down", None]),
        tradeflow_direction=rng.choice(["up", "down", None]),
        signal_classification="x", strength=rng.random(), confidence=rng.random(),
        research_priority=rng.randint(0, 100), n_families=2,
        evidence_families=rng.sample(["price behaviour", "flow", "book"], k=rng.randint(0, 3)),
        component_scores=[], component_availability={}, data_quality="good",
        entry_price=rng.choice([None, rng.random()]), best_bid=0.4, best_ask=0.6,
        midpoint=rng.choice([None, rng.random()]), spread=rng.choice([None, 0.02]),
        near_mid_depth=rng.choice([None, 1000.0]), liquidity=1.0, volume=1.0,
        data_age_seconds=1.0, expected_close=BASE + timedelta(days=40), time_remaining_hours=900,
        intended_horizons=["1h"], bucket="closing_7_30d", overall_rank_30d=1, public_selected=True,
    )


@pytest.fixture
async def svc():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    rng = random.Random(11)
    async with sm() as session:
        repo = ResearchRepository(session)
        for k in range(9):
            cutoff = BASE + timedelta(hours=6 * k)
            inputs = [_inp(rng, f"m{rng.randint(0, 25)}-{i}" if i % 3 else f"m{i % 12}",
                           rng.choice(ROLES), rng.choice(PARTS)) for i in range(40)]
            dedup = {(x.market_id, x.token_id): x for x in inputs}
            await freeze_from_inputs(
                session, cadence="6h", cutoff_at=cutoff, inputs=list(dedup.values()),
                model_version="m", calculation_version="c",
                frozen_at=cutoff + timedelta(seconds=rng.randint(0, 600)),
                provenance_class="prospective" if k != 4 else "retrospective",
            )
            cid = (await repo.get_cohort("6h", cutoff)).id
            if k == 2:
                await session.execute(update(ResearchCohortRow).where(ResearchCohortRow.id == cid)
                                      .values(excessively_late=True))
            for e in await repo.get_entries(cid):
                for h in RESEARCH_HORIZONS:
                    if rng.random() < 0.7:
                        await repo.upsert_forward(
                            entry_id=e.id, horizon=h, observed_at=cutoff,
                            midpoint=rng.choice([None, rng.random(), rng.random()]),
                            best_bid=None, best_ask=None, spread=rng.choice([None, 0.01]),
                            near_mid_depth=rng.choice([None, 500.0]), source_timestamp=None,
                            exact=True, observation_delay_seconds=0.0, unavailable_reason=None,
                        )
        await session.commit()
        yield ResearchReadService(session)
    await engine.dispose()


async def _legacy_frozen_entries(s: ResearchReadService):
    out = []
    for cohort in await s.repo.list_cohorts(provenance="prospective", frozen=True):
        if cohort.excessively_late:
            continue
        for e in await s.repo.get_entries(cohort.id):
            if is_reportable(e.walk_forward_partition):
                out.append((cohort, e))
    return out


async def _legacy_horizon(s: ResearchReadService, horizon: str) -> dict:
    best = {}
    for cohort, e in await _legacy_frozen_entries(s):
        if e.direction not in ("up", "down"):
            continue
        fwd = (await s.repo.get_forward(e.id)).get(horizon)
        if fwd is None or fwd.midpoint is None:
            continue
        origin = (_utc(cohort.evaluation_origin_at) or _utc(cohort.frozen_at)
                  or _utc(cohort.cutoff_at) or datetime.min.replace(tzinfo=UTC))
        prev = best.get(e.market_id)
        if prev is None or origin > prev[0]:
            best[e.market_id] = (origin, _obs_for_horizon(e, fwd))
    obs = [o for _c, o in best.values()]
    bt = baseline_table(obs)
    return {"horizon": horizon, "evaluable": len(obs), "baselines": bt["baselines"],
            "arepo_momentum_agreement": bt["arepo_momentum_agreement"],
            "probabilistic_metrics_note": bt["probabilistic_metrics_note"],
            "ablation": ablation_table(obs)}


async def _legacy_roles_and_coverage(s: ResearchReadService):
    entries = await _legacy_frozen_entries(s)
    by_role: dict = {}
    for _c, e in entries:
        by_role[e.role] = by_role.get(e.role, 0) + 1
    cov = {}
    for h in RESEARCH_HORIZONS:
        ev = pend = 0
        for _c, e in entries:
            fwd = (await s.repo.get_forward(e.id)).get(h)
            if fwd is not None and fwd.midpoint is not None:
                ev += 1
            else:
                pend += 1
        cov[h] = {"evaluable": ev, "pending": pend}
    return len(entries), by_role, cov


@pytest.mark.parametrize("horizon", list(RESEARCH_HORIZONS))
async def test_horizon_analysis_matches_legacy(svc, horizon):
    new = await svc.horizon_analysis(horizon)
    old = await _legacy_horizon(svc, horizon)
    assert new == old
    assert old["evaluable"] > 0


async def test_status_roles_and_coverage_match_legacy(svc):
    status = await svc.status()
    total, by_role, cov = await _legacy_roles_and_coverage(svc)
    assert status["total_frozen_markets"] == total > 0
    assert status["roles"] == by_role
    assert status["horizon_coverage"] == cov
    old24 = await _legacy_horizon(svc, "24h")
    assert status["edge"] is not None and old24["evaluable"] >= 0
