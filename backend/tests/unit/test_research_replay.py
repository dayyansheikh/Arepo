"""Prospective-Replay read-service tests (refinement prompt sections 1-11, 15).

Deterministic, in memory, no network or wall-clock. Builds real research cohorts via the repository
so every field (role, rank, midpoint, frozen time-to-close, forward observation) is controlled, then
asserts the Replay service returns the correct result states, aggregate counts, top-ten ranking,
closing-window filtering, scope, freeze-as-origin, final-resolution separation, and that reads never
mutate a frozen entry and are idempotent.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation.models import MarketResolutionRow as ResolutionRow
from astrolabe.evaluation.research_constants import (
    CADENCE_6H,
    CADENCE_DAILY,
    LATENESS_MAX_SECONDS,
    ROLE_ABSTENTION,
    ROLE_OBSERVATION,
    ROLE_PUBLIC,
    ROLE_SHADOW,
)
from astrolabe.evaluation.research_replay import (
    ResearchReplayService,
    replay_result_state,
)
from astrolabe.evaluation.research_repository import EntryInput, ResearchRepository
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

CUTOFF = datetime(2026, 8, 6, 0, 0, 0, tzinfo=UTC)
FROZEN = datetime(2026, 8, 6, 1, 24, 13, tzinfo=UTC)  # 84 min late, like the real cohort


@pytest.fixture
async def session():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s
    await engine_.dispose()


def _entry(
    *, role, rank, market, direction, midpoint, ttc, token=None, question=None
) -> EntryInput:
    return EntryInput(
        role=role, rank=rank, walk_forward_partition="live",
        market_id=market, condition_id=f"c-{market}", event_id=None,
        token_id=token or f"{market}-yes", market_question=question or f"Q {market}",
        outcome_name="Yes", direction=direction, momentum_direction=direction,
        orderbook_direction=direction, tradeflow_direction=None,
        signal_classification="Directional opportunity" if direction else "Non-directional anomaly",
        strength=0.5, confidence=0.6, research_priority=max(0, 90 - (rank or 0)),
        n_families=2 if direction else 0,
        evidence_families=(["price behaviour"] if direction else []),
        component_scores=[], component_availability={}, data_quality="good",
        entry_price=midpoint, best_bid=(midpoint - 0.01), best_ask=(midpoint + 0.01),
        midpoint=midpoint, spread=0.02, near_mid_depth=1000.0, liquidity=10000.0,
        volume=5000.0, data_age_seconds=10.0,
        expected_close=(FROZEN + timedelta(hours=ttc)) if ttc is not None else None,
        time_remaining_hours=ttc, intended_horizons=["1h", "6h", "24h", "7d"],
    )


async def _make_cohort(
    session, entries, *, cadence=CADENCE_6H, cutoff=CUTOFF, frozen_at=None,
    provenance="prospective", forwards=None,
):
    """Freeze a cohort with the given EntryInputs and optional per-market forward observations.

    ``forwards`` maps market_id -> {horizon: forward_midpoint | None}. A ``None`` forward midpoint
    is stored as an unavailable observation (a row with no usable midpoint); a market absent from
    the map has no forward row at all (pending).
    """
    # Default freeze is 84 minutes after THIS cohort's own cut-off (late, but not excessively so),
    # so a cohort with an earlier cut-off is not accidentally marked excessively late.
    if frozen_at is None:
        frozen_at = cutoff + timedelta(minutes=84, seconds=13)
    repo = ResearchRepository(session)
    cohort, _ = await repo.get_or_create_cohort(
        cadence=cadence, cutoff_at=cutoff, model_version="arepo-model-1",
        calculation_version="test",
    )
    cohort.provenance_class = provenance
    rows = []
    for e in entries:
        rows.append(await repo.add_entry(cohort, e))
    await repo.freeze_cohort(cohort, frozen_at=frozen_at)
    if forwards:
        by_market = {r.market_id: r for r in rows}
        for market, horizons in forwards.items():
            entry = by_market[market]
            for horizon, mid in horizons.items():
                await repo.upsert_forward(
                    entry_id=entry.id, horizon=horizon, observed_at=frozen_at + timedelta(hours=6),
                    midpoint=mid, best_bid=None, best_ask=None,
                    spread=(0.02 if mid is not None else None),
                    near_mid_depth=(1000.0 if mid is not None else None),
                    source_timestamp=None, exact=True, observation_delay_seconds=0.0,
                    unavailable_reason=(None if mid is not None else "book unavailable"),
                )
    await session.commit()
    return cohort


# --- pure result-state logic -----------------------------------------------------------------


class _Fwd:
    def __init__(self, midpoint):
        self.midpoint = midpoint


def test_result_state_covers_every_case():
    assert replay_result_state("up", 0.5, _Fwd(0.56)) == "moved_expected"
    assert replay_result_state("up", 0.5, _Fwd(0.44)) == "moved_against"
    assert replay_result_state("down", 0.5, _Fwd(0.44)) == "moved_expected"
    assert replay_result_state("up", 0.5, _Fwd(0.5)) == "no_change"
    # A tiny sub-materiality move still counts as a directional move for the product (not the
    # 0.01 edge floor): 0.5 -> 0.505 is "moved_expected", not "no_change".
    assert replay_result_state("up", 0.5, _Fwd(0.505)) == "moved_expected"
    assert replay_result_state("up", 0.5, None) == "pending"
    assert replay_result_state("up", 0.5, _Fwd(None)) == "unavailable"
    assert replay_result_state("up", None, _Fwd(0.5)) == "unavailable"
    assert replay_result_state(None, 0.5, _Fwd(0.5)) == "invalid"


# --- cohort listing --------------------------------------------------------------------------


async def test_lists_only_real_prospective_cohorts_newest_default(session):
    await _make_cohort(session, [_entry(role=ROLE_PUBLIC, rank=1, market="m1",
                                        direction="up", midpoint=0.5, ttc=100)],
                       cadence=CADENCE_6H, cutoff=CUTOFF - timedelta(hours=6))
    await _make_cohort(session, [_entry(role=ROLE_PUBLIC, rank=1, market="m2",
                                        direction="up", midpoint=0.5, ttc=100)],
                       cadence=CADENCE_6H, cutoff=CUTOFF)
    out = await ResearchReplayService(session).list_cohorts()
    assert out["has_prospective"] is True
    assert len(out["cohorts"]) == 2
    # Newest first + default is the newest cohort.
    assert out["cohorts"][0]["scheduled_for"].startswith("2026-08-06T00:00")
    newest_id = out["cohorts"][0]["id"]
    assert out["default_cohort_id"] == newest_id


async def test_cadence_filtering_only_shows_present_cadences(session):
    await _make_cohort(session, [_entry(role=ROLE_PUBLIC, rank=1, market="m1",
                                        direction="up", midpoint=0.5, ttc=100)],
                       cadence=CADENCE_6H)
    await _make_cohort(session, [_entry(role=ROLE_PUBLIC, rank=1, market="m2",
                                        direction="up", midpoint=0.5, ttc=100)],
                       cadence=CADENCE_DAILY, cutoff=CUTOFF - timedelta(days=1))
    out = await ResearchReplayService(session).list_cohorts()
    cadences = {c["cadence"] for c in out["cadences"]}
    assert cadences == {"6h", "daily"}  # weekly absent (no real cohort)
    six = next(c for c in out["cadences"] if c["cadence"] == "6h")
    assert six["label"] == "Six-hourly"


async def test_excessively_late_cohort_excluded(session):
    # Frozen far past its boundary -> excessively late -> excluded from the selectable list.
    late_frozen = CUTOFF + timedelta(seconds=LATENESS_MAX_SECONDS + 3600)
    await _make_cohort(session, [_entry(role=ROLE_PUBLIC, rank=1, market="m1",
                                        direction="up", midpoint=0.5, ttc=100)],
                       frozen_at=late_frozen)
    out = await ResearchReplayService(session).list_cohorts()
    assert out["has_prospective"] is False
    assert out["cohorts"] == []


async def test_non_prospective_cohort_excluded(session):
    await _make_cohort(session, [_entry(role=ROLE_PUBLIC, rank=1, market="m1",
                                        direction="up", midpoint=0.5, ttc=100)],
                       provenance="synthetic")
    out = await ResearchReplayService(session).list_cohorts()
    assert out["has_prospective"] is False


# --- results: aggregate + result states ------------------------------------------------------


async def _mixed_cohort(session):
    """A cohort with public + shadow directional plus observation/abstention rows and 6h forwards
    that produce a known result mix."""
    entries = [
        _entry(role=ROLE_PUBLIC, rank=1, market="p_exp", direction="up", midpoint=0.5, ttc=5),
        _entry(role=ROLE_PUBLIC, rank=2, market="p_against", direction="up", midpoint=0.5, ttc=20),
        _entry(role=ROLE_PUBLIC, rank=3, market="p_flat", direction="up", midpoint=0.5, ttc=100),
        _entry(role=ROLE_SHADOW, rank=4, market="s_exp", direction="down", midpoint=0.5, ttc=1000),
        _entry(role=ROLE_SHADOW, rank=5, market="s_unavail", direction="up", midpoint=0.5, ttc=100),
        _entry(role=ROLE_SHADOW, rank=6, market="s_pending", direction="up", midpoint=0.5, ttc=100),
        _entry(role=ROLE_OBSERVATION, rank=None, market="obs", direction=None,
               midpoint=0.5, ttc=100),
        _entry(role=ROLE_ABSTENTION, rank=None, market="abs", direction=None,
               midpoint=0.5, ttc=100),
    ]
    forwards = {
        "p_exp": {"6h": 0.56},        # up & up -> expected
        "p_against": {"6h": 0.44},    # up & down -> against
        "p_flat": {"6h": 0.5},        # no change
        "s_exp": {"6h": 0.44},        # down & down -> expected
        "s_unavail": {"6h": None},    # observation exists but no midpoint -> unavailable
        # s_pending: no forward row -> pending
    }
    return await _make_cohort(session, entries, forwards=forwards)


async def test_result_states_and_aggregate_counts(session):
    cohort = await _mixed_cohort(session)
    svc = ResearchReplayService(session)
    r = await svc.cohort_results(cohort.id, horizon="6h", scope="directional", closing="all")
    assert r["found"] is True
    # 6 directional entries total (3 public + 3 shadow); the directional-scope headline covers all.
    assert r["headline"]["total"] == 6
    assert r["combined"]["total"] == 6
    assert r["combined"]["moved_expected"] == 2   # p_exp, s_exp
    assert r["combined"]["moved_against"] == 1    # p_against
    assert r["combined"]["no_change"] == 1        # p_flat
    assert r["combined"]["unavailable"] == 1      # s_unavail
    assert r["combined"]["pending"] == 1          # s_pending
    # Public vs shadow split.
    assert r["public"]["total"] == 3
    assert r["public"]["moved_expected"] == 1 and r["public"]["moved_against"] == 1
    assert r["public"]["no_change"] == 1
    assert r["shadow"]["total"] == 3
    assert r["shadow"]["moved_expected"] == 1
    # Movement coverage = evaluated / total (3 of 6 for combined).
    assert r["combined"]["evaluated"] == 4  # 2 expected + 1 against + 1 flat
    # Hit rate among moved: 2 expected of 3 moved.
    assert r["combined"]["moved"] == 3
    assert abs(r["combined"]["hit_rate_among_moved"] - 2 / 3) < 1e-9
    # Non-directional rows are never in the directional table.
    for row in r["rows"]:
        assert row["role"] in (ROLE_PUBLIC, ROLE_SHADOW)
    # Their counts stay in the methodology role summary.
    assert r["role_counts"][ROLE_OBSERVATION] == 1
    assert r["role_counts"][ROLE_ABSTENTION] == 1


async def test_public_scope_restricts_the_table_only(session):
    cohort = await _mixed_cohort(session)
    svc = ResearchReplayService(session)
    r = await svc.cohort_results(cohort.id, horizon="6h", scope="public", closing="all")
    # Headline + table follow the public scope; public/shadow/combined splits are scope-independent.
    assert r["headline"]["total"] == 3
    assert all(row["role"] == ROLE_PUBLIC for row in r["rows"])
    assert r["shadow"]["total"] == 3  # still computed
    assert r["combined"]["total"] == 6


async def test_pending_when_horizon_not_collected(session):
    cohort = await _mixed_cohort(session)
    svc = ResearchReplayService(session)
    r = await svc.cohort_results(cohort.id, horizon="24h", scope="directional", closing="all")
    assert r["horizon_evaluable"] is False
    assert r["combined"]["pending"] == 6
    assert r["combined"]["moved_expected"] == 0


# --- top-ten ranking + fewer-than-ten --------------------------------------------------------


async def test_top_ten_by_frozen_rank_and_not_padded(session):
    entries = [
        _entry(role=ROLE_PUBLIC, rank=i, market=f"m{i}", direction="up", midpoint=0.5, ttc=100)
        for i in range(1, 26)
    ]
    cohort = await _make_cohort(session, entries)
    r = await ResearchReplayService(session).cohort_results(
        cohort.id, horizon="6h", scope="directional", closing="all"
    )
    assert r["qualifying"] == 25
    assert r["shown"] == 20  # display capped at twenty (top-20 policy), never padded
    ranks = [row["rank"] for row in r["rows"]]
    assert ranks == list(range(1, 21))  # top twenty by FROZEN rank


async def test_fewer_than_ten_shows_all(session):
    entries = [
        _entry(role=ROLE_PUBLIC, rank=i, market=f"m{i}", direction="up", midpoint=0.5, ttc=100)
        for i in range(1, 4)
    ]
    cohort = await _make_cohort(session, entries)
    r = await ResearchReplayService(session).cohort_results(
        cohort.id, horizon="6h", scope="directional", closing="all"
    )
    assert r["qualifying"] == 3 and r["shown"] == 3


# --- closing-window filtering (frozen time-to-close) -----------------------------------------


async def test_closing_window_uses_frozen_time_to_close(session):
    entries = [
        _entry(role=ROLE_PUBLIC, rank=1, market="soon", direction="up", midpoint=0.5, ttc=5),
        _entry(role=ROLE_PUBLIC, rank=2, market="day", direction="up", midpoint=0.5, ttc=20),
        _entry(role=ROLE_PUBLIC, rank=3, market="week", direction="up", midpoint=0.5, ttc=120),
        _entry(role=ROLE_PUBLIC, rank=4, market="month", direction="up", midpoint=0.5, ttc=500),
        _entry(role=ROLE_PUBLIC, rank=5, market="far", direction="up", midpoint=0.5, ttc=5000),
        _entry(role=ROLE_PUBLIC, rank=6, market="noclose", direction="up", midpoint=0.5, ttc=None),
    ]
    cohort = await _make_cohort(session, entries)
    svc = ResearchReplayService(session)

    async def q(closing):
        r = await svc.cohort_results(cohort.id, horizon="6h", scope="directional", closing=closing)
        return r["qualifying"]

    assert await q("6h") == 1     # soon
    assert await q("24h") == 2    # soon + day
    assert await q("7d") == 3     # + week (120h < 168h)
    assert await q("30d") == 4    # + month (500h < 720h)
    assert await q("all") == 6    # everything incl the no-close market
    # A market with no frozen time-to-close is only shown under "all", never a bounded window.
    r_all = await svc.cohort_results(cohort.id, horizon="6h", scope="directional", closing="all")
    assert any(row["market_id"] == "noclose" for row in r_all["rows"])


# --- final resolution kept separate ----------------------------------------------------------


async def test_final_resolution_is_separate_from_movement(session):
    entries = [
        _entry(role=ROLE_PUBLIC, rank=1, market="win", direction="up", midpoint=0.5, ttc=100,
               token="win-yes"),
        _entry(role=ROLE_PUBLIC, rank=2, market="lose", direction="up", midpoint=0.5, ttc=100,
               token="lose-yes"),
        _entry(role=ROLE_PUBLIC, rank=3, market="open", direction="up", midpoint=0.5, ttc=100,
               token="open-yes"),
    ]
    # "win" moved AGAINST short-term but finally resolves to the selected outcome; "lose" moved as
    # expected short-term but resolves to a different outcome. Proves the two are not conflated.
    forwards = {"win": {"6h": 0.44}, "lose": {"6h": 0.56}, "open": {"6h": 0.5}}
    cohort = await _make_cohort(session, entries, forwards=forwards)
    session.add(ResolutionRow(
        market_id="win", condition_id="c-win", resolved=True, resolved_outcome="Yes",
        resolved_token_id="win-yes", resolved_at=FROZEN + timedelta(days=2), source="test",
        updated_at=FROZEN + timedelta(days=2),
    ))
    session.add(ResolutionRow(
        market_id="lose", condition_id="c-lose", resolved=True, resolved_outcome="No",
        resolved_token_id="lose-no", resolved_at=FROZEN + timedelta(days=2), source="test",
        updated_at=FROZEN + timedelta(days=2),
    ))
    await session.commit()

    svc = ResearchReplayService(session)
    r = await svc.cohort_results(cohort.id, horizon="6h", scope="directional", closing="all")
    # Short-term movement.
    assert r["combined"]["moved_against"] == 1   # win
    assert r["combined"]["moved_expected"] == 1  # lose
    # Final resolution is a distinct block.
    assert r["resolution"]["resolved_correct"] == 1   # win resolved to its selected outcome
    assert r["resolution"]["resolved_incorrect"] == 1  # lose resolved to a different outcome
    assert r["resolution"]["unresolved"] == 1         # open
    # Per-row resolution is exposed and separate from result_state.
    win = next(row for row in r["rows"] if row["market_id"] == "win")
    assert win["result_state"] == "moved_against" and win["resolution"]["correct"] is True


# --- causal origin + immutability + idempotency ----------------------------------------------


async def test_evaluation_origin_equals_actual_freeze(session):
    cohort = await _make_cohort(session, [
        _entry(role=ROLE_PUBLIC, rank=1, market="m1", direction="up", midpoint=0.5, ttc=100)
    ])
    r = await ResearchReplayService(session).cohort_results(cohort.id, horizon="6h")
    c = r["cohort"]
    assert c["evaluation_origin_at"] == c["frozen_at"]
    assert c["scheduled_for"] != c["frozen_at"]  # frozen 84 min after the scheduled boundary
    assert c["late"] is True and round(c["lateness_minutes"]) == 84


async def test_reads_are_idempotent_and_do_not_mutate(session):
    cohort = await _mixed_cohort(session)
    svc = ResearchReplayService(session)
    r1 = await svc.cohort_results(cohort.id, horizon="6h", scope="directional", closing="all")
    r2 = await svc.cohort_results(cohort.id, horizon="6h", scope="directional", closing="all")
    assert r1 == r2  # deterministic, idempotent
    # The frozen entry midpoints are unchanged after reading.
    entries = await ResearchRepository(session).get_entries(cohort.id)
    assert all(e.midpoint == 0.5 for e in entries)


async def test_unknown_or_excessively_late_cohort_not_found(session):
    late_frozen = CUTOFF + timedelta(seconds=LATENESS_MAX_SECONDS + 3600)
    cohort = await _make_cohort(session, [
        _entry(role=ROLE_PUBLIC, rank=1, market="m1", direction="up", midpoint=0.5, ttc=100)
    ], frozen_at=late_frozen)
    svc = ResearchReplayService(session)
    assert (await svc.cohort_results(cohort.id, horizon="6h"))["found"] is False
    assert (await svc.cohort_results(999999, horizon="6h"))["found"] is False
