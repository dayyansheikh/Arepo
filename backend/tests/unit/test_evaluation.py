"""Prospective cohort evaluation tests (spec section 17).

Everything runs against an in-memory SQLite database with hand-built snapshots, so the
selection, freeze-immutability, idempotency and provenance-separation guarantees are
proven directly and deterministically (no network, no wall-clock dependence).
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.evaluation import engine, tracking
from astrolabe.evaluation.constants import (
    CALCULATION_VERSION,
    PROVENANCE_PROSPECTIVE,
    PROVENANCE_SYNTHETIC,
)
from astrolabe.evaluation.errors import CohortFrozenError
from astrolabe.evaluation.portfolio import fill_price, value_position
from astrolabe.evaluation.ranking import is_eligible, week_bounds
from astrolabe.evaluation.repository import EvaluationRepository
from astrolabe.evaluation.service import CohortReadService
from astrolabe.evaluation.snapshots import SnapshotInput, make_snapshot_ref
from astrolabe.storage.db import Base, make_engine, make_sessionmaker

# 2026-08-03 is a Monday, so all default snapshots land in one ISO week (2026-W32).
MONDAY = datetime(2026, 8, 3, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s
    await engine_.dispose()


def snap(
    market: str,
    strength: float,
    *,
    token: str | None = None,
    at: datetime = MONDAY,
    direction: str = "up",
    dq: str = "good",
    confidence: float = 0.9,
    entry: float = 0.5,
    spread: float = 0.02,
) -> SnapshotInput:
    token = token or f"{market}-yes"
    return SnapshotInput(
        snapshot_ref=make_snapshot_ref(market, token, at, CALCULATION_VERSION),
        calculation_version=CALCULATION_VERSION,
        captured_at=at,
        source_timestamp=None,
        market_id=market,
        condition_id=f"cond-{market}",
        event_id=None,
        token_id=token,
        market_question=f"Question {market}?",
        outcome_name="Yes",
        direction=direction,
        strength=strength,
        confidence=confidence,
        data_quality=dq,
        value=2.0,
        entry_price=entry,
        best_bid=entry - 0.01,
        best_ask=entry + 0.01,
        midpoint=entry,
        spread=spread,
        volume=1000.0,
        near_mid_depth=500.0,
        lookback_size=145,
        expected_close=at + timedelta(days=30),
        component_scores=[{"name": "unusual_return", "raw_value": 2.0,
                           "normalized_value": 0.8, "weight": 0.4}],
    )


async def _strengths(repo: EvaluationRepository, cohort_id: int) -> list[float]:
    return [round(e.strength, 3) for e in await repo.get_entries(cohort_id)]


# 1. provisional rankings retain only the strongest qualifying entries -------------------
async def test_only_strongest_ten_retained(session):
    strengths = [0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35]
    snaps = [snap(f"m{i}", s) for i, s in enumerate(strengths)]
    cohort = await engine.update_rankings(session, snapshots=snaps, at=MONDAY)
    repo = EvaluationRepository(session)
    got = sorted(await _strengths(repo, cohort.id), reverse=True)
    assert len(got) == 10
    assert got == sorted(strengths, reverse=True)[:10]
    assert 0.40 not in got and 0.35 not in got


# 2. a stronger signal replaces only the current lowest entry ----------------------------
async def test_stronger_replaces_only_lowest(session):
    base = [snap(f"m{i}", s) for i, s in enumerate(
        [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50])]
    cohort = await engine.update_rankings(session, snapshots=base, at=MONDAY)
    repo = EvaluationRepository(session)
    # A much stronger new market replaces the 0.50 (lowest) and nothing else.
    cohort = await engine.update_rankings(session, snapshots=[snap("mNew", 0.99)], at=MONDAY)
    got = await _strengths(repo, cohort.id)
    assert 0.50 not in got
    assert 0.99 in got
    assert sorted(got, reverse=True)[1:] == [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55]
    # A weak new market changes nothing.
    await engine.update_rankings(session, snapshots=[snap("mWeak", 0.31)], at=MONDAY)
    assert 0.31 not in await _strengths(repo, cohort.id)


# 3. ties are deterministic --------------------------------------------------------------
async def test_ties_are_deterministic(session):
    early = snap("mEarly", 0.80, at=MONDAY)
    late = snap("mLate", 0.80, at=MONDAY + timedelta(hours=5))
    cohort = await engine.update_rankings(session, snapshots=[late, early], at=MONDAY)
    repo = EvaluationRepository(session)
    await engine.freeze_week(session, at=MONDAY)
    entries = await repo.get_entries(cohort.id)
    ranked = {e.market_id: e.rank for e in entries}
    # Equal strength/confidence/quality -> earlier signal ranks higher (rank 1).
    assert ranked["mEarly"] == 1
    assert ranked["mLate"] == 2


# 4. frozen cohorts cannot be modified ---------------------------------------------------
async def test_frozen_cohort_is_immutable(session):
    cohort = await engine.update_rankings(session, snapshots=[snap("m0", 0.8)], at=MONDAY)
    await engine.freeze_week(session, at=MONDAY)
    repo = EvaluationRepository(session)
    frozen = await repo.get_cohort_by_id(cohort.id)
    entry = (await repo.get_entries(cohort.id))[0]
    snap_row = await repo.add_snapshot(snap("mX", 0.99))
    with pytest.raises(CohortFrozenError):
        await repo.add_entry(frozen, snap_row, rank=2)
    with pytest.raises(CohortFrozenError):
        await repo.remove_entry(frozen, entry)
    with pytest.raises(CohortFrozenError):
        await repo.set_rank(frozen, entry, 5)
    with pytest.raises(CohortFrozenError):
        await repo.replace_entry_snapshot(frozen, entry, snap_row)


# 5. later data cannot change the original ranking ---------------------------------------
async def test_later_data_cannot_change_frozen_ranking(session):
    base = [snap(f"m{i}", s) for i, s in enumerate([0.8, 0.7, 0.6])]
    cohort = await engine.update_rankings(session, snapshots=base, at=MONDAY)
    await engine.freeze_week(session, at=MONDAY)
    repo = EvaluationRepository(session)
    before = [(e.market_id, e.rank, e.strength) for e in await repo.get_entries(cohort.id)]
    # A far stronger later signal for the same week must be ignored (frozen no-op).
    later = snap("mLater", 0.99, at=MONDAY + timedelta(days=1))
    await engine.update_rankings(session, snapshots=[later], at=MONDAY + timedelta(days=1))
    after = [(e.market_id, e.rank, e.strength) for e in await repo.get_entries(cohort.id)]
    assert before == after
    assert "mLater" not in [m for m, _, _ in after]


# 6. losing entries remain stored --------------------------------------------------------
async def test_losing_entries_remain(session):
    cohort = await engine.update_rankings(session, snapshots=[snap("m0", 0.8)], at=MONDAY)
    await engine.freeze_week(session, at=MONDAY)
    repo = EvaluationRepository(session)
    entry = (await repo.get_entries(cohort.id))[0]
    # Market resolves to a DIFFERENT outcome: the signal lost.
    await repo.upsert_resolution(
        entry.market_id, condition_id=entry.condition_id, resolved=True,
        resolved_outcome="No", resolved_token_id="other-token",
        resolved_at=MONDAY + timedelta(days=8), source="test",
    )
    await session.commit()
    await tracking.evaluate_all(session)
    remaining = await repo.get_entries(cohort.id)
    assert len(remaining) == 1  # the losing entry is not removed
    ev = await repo.get_evaluation(entry.id)
    assert ev.resolved is True and ev.resolution_correct is False


# 7. unresolved entries remain pending ---------------------------------------------------
async def test_unresolved_entries_pending(session):
    cohort = await engine.update_rankings(session, snapshots=[snap("m0", 0.8)], at=MONDAY)
    await engine.freeze_week(session, at=MONDAY)
    repo = EvaluationRepository(session)
    await tracking.evaluate_all(session)
    entry = (await repo.get_entries(cohort.id))[0]
    ev = await repo.get_evaluation(entry.id)
    assert ev.pending is True
    assert ev.resolution_correct is None


# 8. repeated scheduler runs are idempotent ----------------------------------------------
async def test_ranking_idempotent(session):
    snaps = [snap(f"m{i}", s) for i, s in enumerate([0.9, 0.8, 0.7])]
    c1 = await engine.update_rankings(session, snapshots=snaps, at=MONDAY)
    first = await _strengths(EvaluationRepository(session), c1.id)
    c2 = await engine.update_rankings(session, snapshots=snaps, at=MONDAY)
    second = await _strengths(EvaluationRepository(session), c2.id)
    assert first == second
    assert c1.id == c2.id
    # Snapshots dedupe by ref: no duplicate snapshot rows on the second run.
    repo = EvaluationRepository(session)
    snap_row_a = await repo.add_snapshot(snaps[0])
    snap_row_b = await repo.add_snapshot(snaps[0])
    assert snap_row_a.id == snap_row_b.id


# 9. forward observations are not duplicated ---------------------------------------------
async def test_forward_observations_not_duplicated(session):
    cohort = await engine.update_rankings(session, snapshots=[snap("m0", 0.8)], at=MONDAY)
    await engine.freeze_week(session, at=MONDAY)
    repo = EvaluationRepository(session)
    entry = (await repo.get_entries(cohort.id))[0]
    _, created1 = await repo.add_forward(entry.id, "24h", observed_at=MONDAY, price=0.6)
    _, created2 = await repo.add_forward(entry.id, "24h", observed_at=MONDAY, price=0.7)
    await session.commit()
    obs = await repo.get_forward(entry.id)
    assert created1 is True and created2 is False
    assert len(obs) == 1
    assert obs[0].price == 0.6  # first write wins; not overwritten


# 10. resolution updates do not overwrite entry data -------------------------------------
async def test_resolution_does_not_overwrite_entry(session):
    cohort = await engine.update_rankings(
        session, snapshots=[snap("m0", 0.8, entry=0.42)], at=MONDAY)
    await engine.freeze_week(session, at=MONDAY)
    repo = EvaluationRepository(session)
    entry = (await repo.get_entries(cohort.id))[0]
    original = (entry.entry_price, entry.strength, entry.token_id)
    await repo.upsert_resolution(
        entry.market_id, condition_id=entry.condition_id, resolved=True,
        resolved_outcome="Yes", resolved_token_id=entry.token_id,
        resolved_at=MONDAY, source="test",
    )
    await session.commit()
    await tracking.evaluate_all(session)
    refreshed = (await repo.get_entries(cohort.id))[0]
    assert (refreshed.entry_price, refreshed.strength, refreshed.token_id) == original


# 11. weekly summaries use correct denominators ------------------------------------------
async def test_summary_denominators(session):
    snaps = [snap(f"m{i}", 0.8 - i * 0.05, direction="up", entry=0.5) for i in range(3)]
    cohort = await engine.update_rankings(session, snapshots=snaps, at=MONDAY)
    await engine.freeze_week(session, at=MONDAY)
    repo = EvaluationRepository(session)
    entries = await repo.get_entries(cohort.id)
    # m0 moves up (correct), m1 moves down (against), m2 no forward price (pending).
    await repo.add_forward(entries[0].id, "24h", observed_at=MONDAY, price=0.7)
    await repo.add_forward(entries[1].id, "24h", observed_at=MONDAY, price=0.3)
    # m0 resolves correct; others unresolved.
    await repo.upsert_resolution(
        entries[0].market_id, condition_id=entries[0].condition_id, resolved=True,
        resolved_outcome="Yes", resolved_token_id=entries[0].token_id,
        resolved_at=MONDAY, source="test")
    await session.commit()
    await tracking.evaluate_all(session)
    detail = await CohortReadService(session).cohort_detail(cohort.iso_year, cohort.iso_week)
    s = detail.summary
    assert s.selected == 3
    assert s.moved_expected + s.moved_against + s.movement_pending == 3
    assert s.resolved_correct + s.resolved_incorrect + s.unresolved == 3
    assert s.moved_expected == 1 and s.moved_against == 1 and s.movement_pending == 1
    assert s.resolved_correct == 1 and s.unresolved == 2
    assert "3" in s.plain_summary and "pending" in s.plain_summary


# 12. simulated returns use only available entry information ------------------------------
async def test_portfolio_uses_only_entry_information(session):
    # Fill price depends only on entry_price + spread, never a forward/exit price.
    f = fill_price(0.50, 0.02)
    assert f == pytest.approx(0.51)  # 0.50 + half of 0.02
    p_win = value_position(entry_id=1, entry_price=0.50, spread=0.02, won=True,
                           forward_price=0.99)
    p_win2 = value_position(entry_id=1, entry_price=0.50, spread=0.02, won=True,
                            forward_price=0.10)  # different later price
    # Contracts/fill identical regardless of the later forward price.
    assert p_win.fill == p_win2.fill
    assert p_win.contracts == p_win2.contracts
    # A missing entry price cannot be simulated: held flat, no invented P&L.
    p_none = value_position(entry_id=2, entry_price=None, spread=0.02, won=None,
                            forward_price=0.8)
    assert p_none.status == "pending" and p_none.pnl == 0.0


# 13. prospective, reconstructed and synthetic datasets cannot be mixed silently ---------
async def test_provenance_not_mixed(session):
    # A real prospective week.
    await engine.update_rankings(
        session, snapshots=[snap("mP", 0.8)], at=MONDAY,
        provenance_class=PROVENANCE_PROSPECTIVE)
    # A synthetic week in a different ISO week.
    other = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)  # 2026-W28
    await engine.update_rankings(
        session, snapshots=[snap("mS", 0.9, at=other)], at=other,
        provenance_class=PROVENANCE_SYNTHETIC)
    svc = CohortReadService(session)
    prov = await svc.provenance()
    assert prov.prospective_weeks == 1
    assert prov.synthetic_weeks == 1
    # The first prospective week ignores the (stronger, earlier) synthetic one.
    assert prov.first_prospective_week == "2026-W32"
    # Each cohort reports its own provenance; nothing is aggregated across classes.
    weeks = {w.label: w.provenance_class for w in await svc.available_weeks()}
    assert weeks["2026-W32"] == PROVENANCE_PROSPECTIVE
    assert weeks["2026-W28"] == PROVENANCE_SYNTHETIC


# Extra guarantees -----------------------------------------------------------------------
async def test_week_bounds_cutoff_is_sunday_2359():
    iso_year, iso_week, week_start, cutoff = week_bounds(MONDAY)
    assert (iso_year, iso_week) == (2026, 32)
    assert week_start.weekday() == 0 and week_start.hour == 0
    assert cutoff.weekday() == 6 and (cutoff.hour, cutoff.minute, cutoff.second) == (23, 59, 59)


async def test_eligibility_rules():
    assert is_eligible(strength=0.5, data_quality="good", entry_price=0.5)
    assert not is_eligible(strength=0.1, data_quality="good", entry_price=0.5)  # too weak
    assert not is_eligible(strength=0.9, data_quality="poor", entry_price=0.5)  # coverage
    assert not is_eligible(strength=0.9, data_quality="good", entry_price=None)  # no price


async def test_ineligible_signals_excluded(session):
    snaps = [
        snap("mOk", 0.8),
        snap("mWeak", 0.10),                 # below MIN_STRENGTH
        snap("mPoor", 0.90, dq="poor"),       # below data-quality floor
        snap("mNoPrice", 0.90),               # entry price nulled below
    ]
    snaps[3].entry_price = None  # no valid entry price -> ineligible
    cohort = await engine.update_rankings(session, snapshots=snaps, at=MONDAY)
    repo = EvaluationRepository(session)
    markets = {e.market_id for e in await repo.get_entries(cohort.id)}
    assert markets == {"mOk"}


async def test_freeze_fewer_than_ten_records_reason(session):
    await engine.update_rankings(
        session, snapshots=[snap("m0", 0.8), snap("m1", 0.7)], at=MONDAY)
    frozen = await engine.freeze_week(session, at=MONDAY)
    assert frozen.actual_size == 2
    assert frozen.note is not None and "qualified" in frozen.note


async def test_audit_trail_records_changes(session):
    base = [snap(f"m{i}", 0.5 + i * 0.02) for i in range(10)]
    cohort = await engine.update_rankings(session, snapshots=base, at=MONDAY)
    await engine.update_rankings(session, snapshots=[snap("mBig", 0.99)], at=MONDAY)
    repo = EvaluationRepository(session)
    actions = [a.action for a in await repo.get_audit(cohort.id)]
    assert "enter" in actions
    assert "replace" in actions


async def test_no_duplicate_market_slots(session):
    # Same market, two outcomes firing: only one slot, kept at the stronger outcome.
    snaps = [
        snap("mDup", 0.7, token="mDup-yes", direction="up"),
        snap("mDup", 0.9, token="mDup-no", direction="down"),
    ]
    cohort = await engine.update_rankings(session, snapshots=snaps, at=MONDAY)
    repo = EvaluationRepository(session)
    entries = await repo.get_entries(cohort.id)
    assert len(entries) == 1
    assert entries[0].strength == pytest.approx(0.9)
    assert entries[0].token_id == "mDup-no"
