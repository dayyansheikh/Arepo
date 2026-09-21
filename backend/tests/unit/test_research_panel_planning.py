"""Synthetic design invariants; no panel collection or predictive result."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.research_panel.sampling import (
    FrameMember,
    SamplingProtocol,
    exact_probability,
    plan_sample,
)
from astrolabe.research_panel.targets import Quote, quote_state, select_target

AT = datetime(2026, 9, 20, 10, tzinfo=UTC)


def member(index, triggered=False):
    return FrameMember(
        market_id=str(index), token_id=str(index), source_observation_id=f"{index:064x}",
        available_at=AT, time_stratum="scheduled-10:00", category="fixture-category",
        close_stratum="unknown", probability="0.4", liquidity="2000", event_group=None,
        group_available_at=None, eligible=True, exclusion_reason=None, triggered=triggered,
        trigger_id=f"trigger-{index}" if triggered else None,
        trigger_available_at=AT if triggered else None,
    )


def plan(rows, protocol=None, **kwargs):
    return plan_sample(
        protocol or SamplingProtocol("a" * 64, 1, 2, 2, 20), rows, cutoff=AT,
        frame_scope="synthetic enumerated test population", frame_status="enumerated_complete",
        frame_evidence_ids=["f" * 64], **kwargs,
    )


def test_sampling_order_invariance_exact_probabilities_and_conditional_controls():
    rows = [member(1, True), member(2, True), *[member(i) for i in range(3, 8)]]
    sample = plan(rows)
    assert sample == plan(reversed(rows))
    controls = [a for a in sample["assignments"] if a["arm"] == "control"]
    assert len(controls) == 4
    for assignment in controls:
        assert assignment["inclusion_probability"] == exact_probability(4, 5)
        assert assignment["conditional_matching_probability"] == exact_probability(2, 5)
        assert assignment["market_id"] not in {"1", "2"}
    scheduled = next(a for a in sample["assignments"] if a["arm"] == "scheduled")
    assert scheduled["inclusion_probability"]["decimal"] is None  # exactly 1/7
    assert sample["strata"][0]["economic_independence"] == "unresolved"
    assert sample["population_inference_eligible"] is False  # caller claim is not evidence


def test_exact_rational_is_never_rounded_into_an_exact_decimal():
    assert exact_probability(1, 3) == {
        "numerator": "1", "denominator": "3", "decimal": None, "decimal_state": "nonterminating",
    }
    assert exact_probability(2, 8)["decimal"] == "0.25"
    assert exact_probability(0, 2)["decimal"] == "0"
    with pytest.raises(ValueError):
        exact_probability(2, 1)


def test_controls_shortage_is_preserved_and_exclusions_are_not_silently_dropped():
    rows = [member(1, True), member(2, True), member(3),
            replace(member(4), eligible=False, exclusion_reason="missing_identity")]
    sample = plan(rows)
    assert sample["strata"][0]["controls_wanted"] == 4
    assert sample["strata"][0]["unfilled_control_slots"] == 3
    assert sample["exclusions"] == [{"market_id": "4", "reason": "missing_identity"}]
    assert len([a for a in sample["assignments"] if a["arm"] == "triggered"]) == 2


@pytest.mark.parametrize("changes", [
    {"available_at": AT + timedelta(microseconds=1)},
    {"event_group": "future-group", "group_available_at": AT + timedelta(seconds=1)},
    {"triggered": True, "trigger_id": "t", "trigger_available_at": AT + timedelta(seconds=1)},
    {"eligible": False, "exclusion_reason": None},
    {"liquidity": "-1"},
])
def test_future_or_invalid_sampling_inputs_rejected(changes):
    with pytest.raises(ValueError):
        plan([replace(member(1), **changes)])


def test_no_duplicate_markets_or_budget_truncation():
    with pytest.raises(ValueError, match="duplicate market"):
        plan([member(1), member(1)])
    protocol = SamplingProtocol("a" * 64, 2, 1, 1, 1)
    with pytest.raises(ValueError, match="never truncate"):
        plan([member(1), member(2)], protocol)


def test_unknown_values_and_long_close_strata_remain_in_population():
    sample = plan([replace(member(1), probability=None, liquidity=None, close_stratum="over-30d")])
    assert sample["strata"][0]["probability_band"] == "unknown"
    assert sample["strata"][0]["liquidity_band"] == "unknown"
    assert sample["strata"][0]["time_to_close"] == "over-30d"
    assert sample["unique_selected_markets"] == 1


def quote(index, seconds, **changes):
    return replace(Quote(
        f"{index:064x}", "1", AT + timedelta(seconds=seconds),
        AT + timedelta(seconds=seconds, milliseconds=50), AT,
        "0.4", "0.6", "10", "10",
    ), **changes)


def target(quotes, **changes):
    kwargs = dict(token_id="1", origin_at=AT, origin_persisted_at=AT + timedelta(milliseconds=50),
                  horizon_seconds=60, tolerance_seconds=5, as_of=AT + timedelta(seconds=70))
    kwargs.update(changes)
    return select_target(quotes, **kwargs)


def test_first_valid_target_ignores_better_later_price_and_records_delay():
    result = target([quote(3, 64, bid="0.8", ask="0.9"), quote(1, 60, ask=None), quote(2, 62)])
    assert result["selected"]["observation_id"] == f"{2:064x}"
    assert result["selected"]["midpoint"] == "0.5"
    assert result["selected"]["delay_seconds"] == "2"
    assert result["exclusions"] == [
        {"observation_id": f"{1:064x}", "reason": "one_sided_or_missing"},
    ]


def test_missing_late_and_closed_do_not_become_flat_outcomes():
    assert target([])["status"] == "unavailable"
    assert target([], as_of=AT + timedelta(seconds=59))["status"] == "pending"
    assert target([quote(1, 65)])["status"] == "observed"
    assert target([quote(1, 65.000001)])["status"] == "unavailable"
    result = target([quote(1, 61, source_status="closed"), quote(2, 62)])
    assert result["status"] == "closed" and result["selected"] is None
    assert result["censoring_observation_id"] == f"{1:064x}"


def test_unavailable_earlier_receipt_blocks_later_selection_without_reading_future_values():
    unknown = quote(1, 60, available_at=AT + timedelta(seconds=80), bid="not-yet-parsed")
    result = target([unknown, quote(2, 61)])
    assert result["status"] == "pending" and result["selected"] is None
    assert result["blocking_observation_id"] == f"{1:064x}"
    future = quote(3, 100, bid="future-invalid")
    assert target([quote(2, 61), future]) == target([quote(2, 61)])


def test_quote_exactness_identity_and_durable_origin_gate():
    state, midpoint = quote_state(quote(1, 61, bid="0.000000000000000000000000000001", ask="1"))
    assert state == "observed" and str(midpoint) == "0.5000000000000000000000000000005"
    changed_identity = quote(1, 61, mapping_available_at=AT + timedelta(seconds=62))
    assert quote_state(changed_identity)[0] != "observed"
    with pytest.raises(ValueError, match="durable origin"):
        target([quote(1, 61)], origin_persisted_at=AT + timedelta(seconds=60))
    with pytest.raises(ValueError, match="duplicate quote"):
        target([quote(1, 61), quote(1, 61)])


def test_later_identity_and_invalid_values_are_explicit_target_exclusions():
    result = target([
        quote(1, 60, bid="malformed"),
        quote(2, 61, mapping_available_at=AT + timedelta(seconds=1)),
        quote(3, 62),
    ])
    assert result["selected"]["observation_id"] == f"{3:064x}"
    assert [r["reason"] for r in result["exclusions"]] == [
        "invalid_numerical", "identity_not_frozen_at_origin",
    ]


def test_unbounded_iterators_stop_at_explicit_guard():
    from itertools import repeat

    with pytest.raises(ValueError, match="bounded frame"):
        plan(repeat(member(1)))
    with pytest.raises(ValueError, match="bounded quote"):
        target(repeat(quote(1, 61)))


def test_future_availability_and_token_content_do_not_leak_into_asof_result():
    pending = quote(1, 60, available_at=AT + timedelta(seconds=80), bid="future")
    assert target([pending]) == target([replace(
        pending, available_at=AT + timedelta(seconds=90), bid="different future",
    )])
    assert target([quote(1, 61)]) == target([
        quote(1, 61), quote(1, 100, token_id="999", bid="future"),
    ])


def test_target_delay_and_midpoint_ignore_ambient_decimal_rounding():
    from decimal import localcontext

    with localcontext() as context:
        context.prec = 2
        result = target([quote(1, 61.234567, bid="0.4123456789012345", ask="0.6")])
    assert result["selected"]["delay_seconds"] == "1.234567"
    assert result["selected"]["midpoint"] == "0.50617283945061725"


def test_equivalent_aware_timezones_project_identical_utc_targets():
    from datetime import timezone

    row = quote(1, 61)
    zone = timezone(timedelta(hours=1))
    assert target([row]) == target([replace(
        row, received_at=row.received_at.astimezone(zone),
        available_at=row.available_at.astimezone(zone),
    )])


def test_streamed_frame_hash_exactly_matches_original_canonical_encoding():
    from dataclasses import asdict

    from astrolabe.feature_store.admission import content_hash
    from astrolabe.research_panel.sampling import _frame_hash

    rows = [replace(member(9), category="café🐈"), member(1, True),
            replace(member(4), probability=None, liquidity=None)]
    expected = content_hash([asdict(r) for r in sorted(rows, key=lambda r: r.market_id)])
    assert _frame_hash(rows) == expected == _frame_hash(list(reversed(rows)))


def test_expanded_capacity_is_explicit_and_never_truncates_or_changes_selection():
    rows = [member(i, triggered=i < 4) for i in range(1, 17)]
    original = plan(rows)
    # Golden full output hash verified against the original 2eb7ec4 implementation.
    assert original["plan_hash"] == (
        "bb8781ef2aaa778fbad4e384bd39bd925014fc39537a3b18f6185dd103c42535"
    )
    expanded = plan(rows, max_frame_members=400000)
    assert expanded["schema_version"] == "fs2-sampling-plan-v2"
    assert expanded["max_frame_members"] == 400000
    for key in ("frame_hash", "assignments", "strata", "exclusions"):
        assert expanded[key] == original[key]
    assert expanded["plan_hash"] != original["plan_hash"]
    with pytest.raises(ValueError, match="bounded frame"):
        plan(rows, max_frame_members=15)
    for invalid in (0, True, 400001):
        with pytest.raises(ValueError, match="finite frame capacity"):
            plan(rows, max_frame_members=invalid)
    assert exact_probability(1, 400000)["decimal"] == "0.0000025"
