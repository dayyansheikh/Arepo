"""Bounded first-stage design, exact probabilities and sealed original recovery."""

from collections import defaultdict
from dataclasses import replace
from datetime import timedelta
from decimal import localcontext
from fractions import Fraction
from itertools import combinations, product
from math import comb

import pytest

from astrolabe.research_panel import sampling
from astrolabe.research_panel.assessments import TriggerAssessmentPolicy
from astrolabe.research_panel.original_reader import read_original_selection
from astrolabe.research_panel.panel_declaration import declare_panel, read_panel_declaration
from astrolabe.research_panel.panel_selection import create_panel_selection, selection_root
from astrolabe.research_panel.screening import ScreeningPolicy, declare_screening, finish_screening
from astrolabe.research_panel.selection import read_selection
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from tests.unit.test_research_panel_declaration import paths, protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_planning import AT, member, plan
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


def bounded(rows, limit=2, **kwargs):
    return plan(
        rows,
        sampling.SamplingProtocol("a" * 64, 2, 1, 1, 256),
        assessment_policy=TriggerAssessmentPolicy("b" * 64, AT, 0, 0),
        trigger_assessments=(),
        strata_limit=limit,
        **kwargs,
    )


def fraction(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def population():
    return [
        replace(member(i), category=category)
        for category, ids in [("a", range(1, 4)), ("b", range(4, 6)), ("unknown", [6])]
        for i in ids
    ]


def test_all_inventory_unknown_singleton_and_exact_stages_are_preserved():
    rows = population() + [replace(member(7), eligible=False, exclusion_reason="unresolved")]
    result = bounded(rows)
    assert result == bounded(reversed(rows))
    assert result["schema_version"] == "fs2-sampling-plan-v4"
    assert result["frame_size"] == 7 and len(result["assessment_inventory"]) == 7
    assert len(result["strata"]) == 3 and len(result["exclusions"]) == 1
    assert result["stratum_draw"]["eligible_strata"] == 3
    assert result["stratum_draw"]["selected_strata"] == 2
    assert sum(r["sampling_state"] == "stratum_not_sampled" for r in result["strata"]) == 1
    for row in result["strata"]:
        expected = Fraction(2, 3) * Fraction(min(2, row["eligible_count"]), row["eligible_count"])
        assert fraction(row["market_inclusion_probability"]) == expected > 0
        assert row["assessment_counts"]["not_assessed"] == row["eligible_count"]
        if row["sampling_state"] == "stratum_not_sampled":
            assert row["scheduled_count"] == 0
    for row in result["assignments"]:
        assert row["arm"] == "scheduled" and row["assessment_state"] == "not_assessed"
        assert fraction(row["stratum_inclusion_probability"]) == Fraction(2, 3)
        assert fraction(row["inclusion_probability"]) == (
            Fraction(2, 3) * fraction(row["conditional_market_inclusion_probability"])
        )
    assert result["origin_admitted"] is False


def test_exact_inclusion_against_exhaustive_small_population_draws(monkeypatch):
    """Enumerate every stage outcome, execute those rankings, sum their design mass."""
    rows = population()
    reports = bounded(rows)["strata"]
    keys = {r["category"]: r["stratum"] for r in reports}
    pools = {c: [r.market_id for r in rows if r.category == c] for c in keys}
    original_hash = sampling.content_hash
    mass, total = defaultdict(Fraction), Fraction(0)
    for selected_strata in combinations(keys, 2):
        choices = [list(combinations(pools[c], min(2, len(pools[c])))) for c in selected_strata]
        for chosen in product(*choices):
            selected_keys = {keys[c] for c in selected_strata}
            selected_ids = {i for draw in chosen for i in draw}

            def ranked(value, selected_keys=selected_keys, selected_ids=selected_ids):
                if isinstance(value, dict) and value.get("arm") == "screening_stratum_v1":
                    return "0" if value["stratum"] in selected_keys else "1"
                if isinstance(value, dict) and value.get("arm") == "scheduled":
                    return "0" if value["market"] in selected_ids else "1"
                return original_hash(value)

            monkeypatch.setattr(sampling, "content_hash", ranked)
            result = bounded(rows)
            assert {r["market_id"] for r in result["assignments"]} == selected_ids
            probability = Fraction(1, comb(3, 2))
            for c in selected_strata:
                probability /= comb(len(pools[c]), min(2, len(pools[c])))
            total += probability
            for assignment in result["assignments"]:
                mass[assignment["market_id"]] += probability
    assert total == 1
    assert mass == {
        "1": Fraction(4, 9),
        "2": Fraction(4, 9),
        "3": Fraction(4, 9),
        "4": Fraction(2, 3),
        "5": Fraction(2, 3),
        "6": Fraction(2, 3),
    }


def test_cap_larger_than_population_and_no_eligible_members():
    result = bounded(population(), limit=32)
    assert result["stratum_draw"]["selected_strata"] == 3
    assert all(fraction(r["stratum_inclusion_probability"]) == 1 for r in result["strata"])
    excluded = bounded([replace(member(1), eligible=False, exclusion_reason="unresolved")])
    assert excluded["assignments"] == [] and excluded["strata"] == []
    assert excluded["stratum_draw"]["stratum_inclusion_probability"] is None
    assert len(excluded["exclusions"]) == 1


def test_product_larger_than_frame_denominator_is_exact_without_ambient_rounding():
    # 631 * 635 > 400000 but population has only 1265 members.
    rows = [replace(member(i), category="large") for i in range(1, 636)]
    rows += [replace(member(i), category=str(i)) for i in range(636, 1266)]
    with localcontext() as context:
        context.prec = 2
        result = bounded(rows, limit=1)
    large = next(r for r in result["strata"] if r["category"] == "large")
    assert fraction(large["market_inclusion_probability"]) == Fraction(1, 631) * Fraction(2, 635)
    assert large["market_inclusion_probability"]["decimal"] is None


@pytest.mark.parametrize("limit", [0, -1, 257, True, "2"])
def test_invalid_cap_refused(limit):
    with pytest.raises(ValueError, match="stratum limit"):
        bounded(population(), limit=limit)


@pytest.mark.parametrize(
    "change",
    [
        {"available_at": AT + timedelta(microseconds=1)},
        {"event_group": "future", "group_available_at": AT + timedelta(seconds=1)},
        {"triggered": True, "trigger_id": "t", "trigger_available_at": AT},
    ],
)
def test_future_or_assessed_inputs_refused_before_draw(change):
    with pytest.raises(ValueError):
        bounded([replace(member(1), **change)])


def test_bounded_mode_cannot_use_legacy_false_as_measured_negative():
    with pytest.raises(ValueError, match="complete unassessed frame"):
        plan(population(), strata_limit=1)


@pytest.mark.parametrize("limit", [0, True, 257, 2])
def test_declaration_refuses_impossible_design_before_output(tmp_path, limit):
    source, root = paths(tmp_path)
    with pytest.raises(ValueError, match="scheduled slots"):
        declare_panel(
            source,
            implementation_commit="a" * 40,
            output_root=root,
            protocol=protocol(scheduled_per_stratum=2),
            strata_limit=limit,
        )
    assert not root.exists()


async def setup_bounded(tmp_path, code):
    source = await frame(
        tmp_path, [market(1), market(2), market(3, category="sports"), market(4, clobTokenIds=None)]
    )
    panel = tmp_path / "fs2_panel_bounded"
    declare_panel(
        source,
        implementation_commit=code[1],
        output_root=panel,
        protocol=protocol(scheduled_per_stratum=2),
        strata_limit=1,
        storage_profile="compact-v1",
    )
    result = create_panel_selection(panel, repository=code[0])
    return source, panel, selection_root(panel), result


async def test_sealed_complete_inventory_and_original_recovery_then_screening(
    tmp_path, original_code
):
    source, panel, root, result = await setup_bounded(tmp_path, original_code)
    assert result["schema_version"] == "fs2-panel-selection-v2"
    assert result["plan"]["schema_version"] == "fs2-panel-selection-plan-v2"
    assert result["counts"]["source_rows"] == 4
    assert result["counts"]["sampling_members"] == 3
    assert result["counts"]["excluded:identity_unresolved"] == 1
    assert len(result["plan"]["strata"]) == 2
    assert result["plan"]["assessment_inventory_encoding"]["member_count"] == 3
    declaration = read_panel_declaration(panel)
    assert declaration["schema_version"] == "fs2-panel-declaration-v3"
    assert declaration["strata_limit"] == 1
    before = snapshot(source), snapshot(panel), snapshot(root)
    read = read_original_selection(
        root,
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_selection_read_bounded",
    )
    assert read["report"] == result == read_selection(root)
    screening = tmp_path / "fs2_screening_bounded"
    declare_screening(
        root,
        output_root=screening,
        rule=SnapshotTriggerPolicy(1, 3, 60000),
        policy=ScreeningPolicy(60, 60),
    )
    measured = finish_screening(screening)  # no source: all not assessed, not negative
    assert all(r["arm"] == "scheduled" for r in measured["plan"]["assignments"])
    first = {r["market_id"]: r for r in result["plan"]["assignments"]}
    for row in measured["plan"]["assignments"]:
        assert (
            row["screening_inclusion_probability"]
            == first[row["market_id"]]["inclusion_probability"]
        )
        assert row["assessment_state"] == "not_assessed"
    assert measured["plan"]["global_arm_inclusion_probability"] is None
    assert before == (snapshot(source), snapshot(panel), snapshot(root))


@pytest.mark.parametrize(
    "change", ["selection_cap", "declaration_cap", "legacy_schema", "weight", "unsampled_inventory"]
)
async def test_resealed_design_or_stage_probabilities_refused(tmp_path, original_code, change):
    _, panel, root, _ = await setup_bounded(tmp_path, original_code)
    if change == "selection_cap":
        amend(root, "selection_policy", lambda p: p.update(strata_limit=2))
    elif change == "declaration_cap":
        amend(panel, "panel_policy", lambda p: p.update(strata_limit=None))
    elif change == "legacy_schema":
        amend(root, "selection_policy", lambda p: p.update(schema_version="fs2-panel-selection-v1"))
    else:

        def alter(p):
            if change == "weight":
                p["assignments"][0]["stratum_inclusion_probability"]["denominator"] = "1"
            else:
                p["strata"] = [r for r in p["strata"] if r["sampling_state"] == "sampled"]

        hash_ = amend(root, "selection_plan", alter)
        amend(root, "selection_report", lambda p: p.update(plan_hash=hash_))
    with pytest.raises(ValueError):
        read_selection(root)


async def test_bounded_selection_still_rejects_existing_unintegrated_activation(
    tmp_path, original_code
):
    from astrolabe.research_panel.activation import activate_panel

    _, panel, _, _ = await setup_bounded(tmp_path, original_code)
    with pytest.raises(ValueError, match="fresh"):
        activate_panel(panel)


@pytest.mark.parametrize("state", ["triggered", "untriggered", "unavailable"])
def test_stratum_draw_cannot_be_conditioned_on_already_measured_states(state):
    from tests.unit.test_research_panel_assessments import assessment, member, plan

    with pytest.raises(ValueError, match="complete unassessed frame"):
        plan(
            [member(1)], [assessment(1, state)], frame_status="enumerated_complete", strata_limit=1
        )


def test_stratum_draw_cannot_claim_complete_population_from_partial_frame():
    from tests.unit.test_research_panel_assessments import member, plan

    with pytest.raises(ValueError, match="complete unassessed frame"):
        plan([member(1)], [], frame_status="source_partial", strata_limit=1)


def test_bounded_declaration_without_compact_profile_and_omitted_cap_legacy(tmp_path):
    source, root = paths(tmp_path)
    first = declare_panel(
        source,
        implementation_commit="a" * 40,
        output_root=root,
        protocol=protocol(),
        strata_limit=1,
    )
    assert first["schema_version"] == "fs2-panel-declaration-v3"
    assert first["strata_limit"] == 1
    legacy = declare_panel(
        source,
        implementation_commit="a" * 40,
        output_root=tmp_path / "fs2_panel_legacy",
        protocol=protocol(),
    )
    assert legacy["schema_version"] == "fs2-panel-declaration-v1"
    assert "strata_limit" not in legacy
