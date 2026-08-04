"""Microstructure change-feature tests (spec §7): each retained component CAN contribute."""
import pytest

from astrolabe.analytics.anomaly import RawComponents, composite_anomaly_score
from astrolabe.analytics.microstructure_changes import (
    MicrostructureChanges,
    changes_from_series,
    depth_change,
    spread_change,
    volume_acceleration,
)
from astrolabe.ingest.microstructure_store import (
    changes_for_token,
    recent_snapshots,
    record_snapshot,
)
from astrolabe.storage.db import Base, make_engine, make_sessionmaker


# -- pure functions: missing vs present --------------------------------------------------
def test_short_series_is_missing_not_zero():
    assert spread_change(0.05, [0.02]) is None            # too few baseline points
    assert depth_change(100.0, []) is None
    assert volume_acceleration([1.0, 2.0]) is None
    # A short series must never be silently coerced to 0.0.
    c = changes_from_series(
        current_spread=0.05, current_depth=100.0,
        prior_spreads=[0.02], prior_depths=[], cumulative_volumes=[1.0, 2.0],
    )
    assert c.spread_change is None and c.depth_change is None and c.volume_acceleration is None


def test_spread_widening_is_positive():
    c = spread_change(0.10, [0.02, 0.02, 0.02, 0.02])
    assert c is not None and c > 0                        # spread widened vs baseline


def test_depth_fall_is_negative():
    c = depth_change(40.0, [100.0, 100.0, 100.0, 100.0])
    assert c is not None and c < 0                        # depth fell vs baseline


def test_volume_acceleration_detects_a_burst():
    # Cumulative volume with a late acceleration: deltas 1,1,1,1,10 -> recent >> baseline.
    series = [0.0, 1.0, 2.0, 3.0, 4.0, 14.0]
    a = volume_acceleration(series)
    assert a is not None and a > 0


def test_each_change_feature_can_contribute_to_the_composite():
    # The whole point of §7: prove a retained component can actually move the composite score.
    base = composite_anomaly_score(RawComponents(zscore=0.5))
    with_spread = composite_anomaly_score(RawComponents(zscore=0.5, spread_change=0.8))
    with_depth = composite_anomaly_score(RawComponents(zscore=0.5, depth_change=0.8))
    with_vol = composite_anomaly_score(RawComponents(zscore=0.5, volume_acceleration=2.0))
    assert with_spread[0] > base[0]
    assert with_depth[0] > base[0]
    assert with_vol[0] > base[0]


# -- store: idempotent collection + series-based changes ---------------------------------
@pytest.fixture
async def session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        yield s
    await engine.dispose()


async def test_snapshot_collection_is_idempotent_per_minute(session):
    from datetime import UTC, datetime

    at = datetime(2026, 8, 4, 12, 0, 30, tzinfo=UTC)
    await record_snapshot(session, token_id="t1", spread=0.02, near_mid_depth=100.0,
                          cumulative_volume=10.0, now=at)
    # Same minute -> updates in place, no duplicate row.
    await record_snapshot(session, token_id="t1", spread=0.03, near_mid_depth=90.0,
                          cumulative_volume=12.0, now=at.replace(second=45))
    rows = await recent_snapshots(session, "t1")
    assert len(rows) == 1 and rows[0].spread == pytest.approx(0.03)


async def test_changes_from_stored_series(session):
    from datetime import UTC, datetime, timedelta

    start = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
    for i in range(5):
        await record_snapshot(
            session, token_id="t1", spread=0.02, near_mid_depth=100.0,
            cumulative_volume=float(i), now=start + timedelta(minutes=i),
        )
    # Current reading with a widened spread vs the stored 0.02 baseline.
    changes = await changes_for_token(session, "t1", current_spread=0.08, current_depth=100.0)
    assert isinstance(changes, MicrostructureChanges)
    assert changes.spread_change is not None and changes.spread_change > 0
