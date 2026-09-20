from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from astrolabe.feature_store.book_replay import BookReplay

AT = datetime(2026, 9, 20, tzinfo=UTC)
CONDITION = "0x" + "a" * 64


def snapshot():
    return {"event_type": "book", "market": CONDITION, "asset_id": "1", "timestamp": None,
            "bids": [{"price": "0.1234567890123456789", "size": "1.000"}],
            "asks": [{"price": "0.600", "size": "12.000"}]}


def delta(size="0.000"):
    return {"event_type": "price_change", "market": CONDITION, "timestamp": "native",
            "price_changes": [{"asset_id": "1", "price": "0.1234567890123456789",
                               "size": size, "side": "BUY"}]}


def apply(replay, message, n, session="s"):
    return replay.apply(message, evidence_id=f"e{n}", session_id=session,
                        received_at=AT + timedelta(seconds=n), monotonic_ns=str(n))


def test_exact_snapshot_and_zero_removal_keep_lineage_without_sequence_claim():
    replay = BookReplay("1", CONDITION)
    first = apply(replay, snapshot(), 1)
    assert first["bids"] == [(Decimal("0.1234567890123456789"), Decimal("1.000"))]
    later = apply(replay, delta(), 2)
    assert later["bids"] == [] and later["lineage"] == ["e1", "e2"]
    assert later["complete_continuous_history"] is False
    assert replay.native_timestamps[0]["raw"] is None
    assert apply(replay, delta(), 2) == later
    with pytest.raises(ValueError, match="identity conflict"):
        apply(replay, delta("5"), 2)


def test_reconnect_requires_snapshot_and_retains_prior_gap():
    replay = BookReplay("1", CONDITION)
    with pytest.raises(ValueError, match="snapshot required"):
        apply(replay, delta(), 1)
    apply(replay, snapshot(), 2)
    replay.disconnect(evidence_id="disconnect", received_at=AT + timedelta(seconds=3))
    with pytest.raises(ValueError, match="snapshot required"):
        apply(replay, delta(), 4)
    result = apply(replay, snapshot(), 5, session="new")
    assert not result["requires_snapshot"]
    assert result["gap_events"] and result["lineage"] == ["e5"]


def test_bad_atomic_batch_does_not_partially_change_book():
    replay = BookReplay("1", CONDITION)
    old = apply(replay, snapshot(), 1)
    bad = delta("99")
    bad["price_changes"].append({"asset_id": "1", "price": "NaN", "size": "1", "side": "SELL"})
    with pytest.raises(ValueError):
        apply(replay, bad, 2)
    assert replay.view()["bids"] == old["bids"]
    assert replay.view()["asks"] == old["asks"]
    assert replay.view()["requires_snapshot"]
    with pytest.raises(ValueError, match="snapshot required"):
        apply(replay, delta(), 3)


def test_regression_budget_and_schema_change_fail_closed():
    replay = BookReplay("1", CONDITION, message_budget=4)
    apply(replay, snapshot(), 2)
    with pytest.raises(ValueError, match="clock regression"):
        apply(replay, delta(), 1)
    assert replay.view()["requires_snapshot"]
    with pytest.raises(ValueError, match="unsupported"):
        apply(replay, {"event_type": "invented"}, 3)
    apply(replay, snapshot(), 4)
    with pytest.raises(ValueError, match="budget"):
        apply(replay, delta(), 5)


def test_duplicate_levels_and_wrong_token_are_not_repaired():
    replay = BookReplay("1", CONDITION)
    bad = snapshot()
    bad["bids"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        apply(replay, bad, 1)
    bad = snapshot()
    bad["asset_id"] = "2"
    with pytest.raises(ValueError, match="token mismatch"):
        apply(replay, bad, 2)


def test_new_session_does_not_hide_utc_regression():
    replay = BookReplay("1", CONDITION)
    apply(replay, snapshot(), 2)
    with pytest.raises(ValueError, match="clock regression"):
        apply(replay, snapshot(), 1, session="new")
    assert replay.view()["requires_snapshot"]
    result = replay.apply(snapshot(), evidence_id="recovered", session_id="new",
                          received_at=AT + timedelta(seconds=3), monotonic_ns="0")
    assert not result["requires_snapshot"]
