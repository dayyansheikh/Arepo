from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.feature_store.identity_views import dependence_components, select_as_known

T0 = datetime(2026, 9, 20, tzinfo=UTC)


def version(key, offset, **changes):
    return dict(id=key, market_id="m", observed_from_at=T0 + timedelta(hours=offset),
                recorded_at=T0 + timedelta(hours=offset), **changes)


def test_later_metadata_never_replaces_as_known_mapping():
    before = version("old", 0, outcome_order=["Yes", "No"])
    later = version("new", 2, outcome_order=["No", "Yes"])
    assert select_as_known([later, before], subject_fields=("market_id",),
                           cutoff=T0 + timedelta(hours=1)) == [before]
    assert select_as_known([before, later], subject_fields=("market_id",),
                           cutoff=T0 + timedelta(hours=3)) == [later]


def test_backdated_known_time_cannot_precede_record_time():
    row = version("late", 0)
    row["recorded_at"] = T0 + timedelta(days=1)
    assert select_as_known([row], subject_fields=("market_id",), cutoff=T0) == []


def test_effective_interval_and_correction_do_not_resurrect_old_mapping():
    before = version("old", 0, valid_from_at=T0, valid_to_at=None)
    later = version("new", 1, valid_from_at=T0, valid_to_at=T0 + timedelta(hours=1))
    assert select_as_known(
        [before, later], subject_fields=("market_id",),
        cutoff=T0 + timedelta(hours=2), effective_at=T0 + timedelta(hours=2),
    ) == []
    assert select_as_known([version("unknown", 0)], subject_fields=("market_id",),
                           cutoff=T0, effective_at=T0) == []
    with pytest.raises(ValueError, match="conflicting"):
        select_as_known([before, version("conflict", 0)], subject_fields=("market_id",), cutoff=T0)


def member(key, market, group, view="as_known", offset=0, graph="g1"):
    return version(key, offset, member_identity_id=market, event_group_id=group,
                   mapping_view=view, group_version=graph, mapping_evidence_ids=["evidence"])


def test_connected_components_and_unknown_are_distinct():
    rows = [member("1", "a", "g"), member("2", "b", "g"),
            member("3", "b", "h"), member("4", "c", "h")]
    result = dependence_components(["a", "b", "c", "unknown"], rows, view="as_known", cutoff=T0)
    assert result["components"] == [["a", "b", "c"], ["unknown"]]
    assert result["unresolved_market_ids"] == ["unknown"]
    assert not result["split_ready"]


def test_conservative_future_evidence_is_evaluation_only():
    rows = [member("1", "a", "g", "conservative_evaluation", 2),
            member("2", "b", "g", "conservative_evaluation", 2)]
    old = dependence_components(["a", "b"], rows, view="as_known", cutoff=T0)
    assert old["unresolved_market_ids"] == ["a", "b"]
    evaluation = dependence_components(["a", "b"], rows, view="conservative_evaluation",
                                        cutoff=T0 + timedelta(hours=3))
    assert evaluation["split_ready"]
    assert not evaluation["model_feature_eligible"]


def test_mixed_graphs_and_out_of_inventory_member_rejected():
    with pytest.raises(ValueError, match="whole graph"):
        dependence_components(["a", "b"], [member("1", "a", "g"),
                              member("2", "b", "g", graph="g2")], view="as_known", cutoff=T0)
    with pytest.raises(ValueError, match="inventory"):
        dependence_components(["a"], [member("1", "other", "g")], view="as_known", cutoff=T0)
