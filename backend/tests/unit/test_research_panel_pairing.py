"""D120 pairing primitives: fee category, dependence groups, screen and role draws (pure)."""

from dataclasses import replace
from fractions import Fraction

import pytest

from astrolabe.research_panel import pairing
from astrolabe.research_panel.assessments import TriggerAssessment, TriggerAssessmentPolicy
from astrolabe.research_panel.sampling import SamplingProtocol, plan_sample
from tests.unit.test_research_panel_planning import AT, member

DESIGN = pairing.PairingDesign(strata=2, screen_per_stratum=3, min_groups_per_stratum=3)


def fraction(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


@pytest.mark.parametrize("raw,expected", [
    ("sports_fees_v3", "sports"), ("Politics_fees", "politics"), ("crypto_15m", "crypto"),
    ("weather", "weather"), ("finance_v1", "finance"), ("economics", "economics"),
    ("culture_fees", "culture"), ("tech_fees", "tech"), ("mentions_v2", "mentions"),
    ("general_fees", "other:general_fees"), ("unknown", "other:unknown"),
    ("geopolitics_fees", "other:geopolitics_fees"), ("", "unknown"), ("   ", "unknown"),
    (None, "unknown"), (7, "unknown"), ("x" * 300, "unknown"),
])
def test_fee_category_prefix_map_and_literal_collision_guard(raw, expected):
    assert pairing.fee_category(raw) == expected
    # A literal source value never collides with the missing-category stratum.
    assert pairing.STRATUM_CATEGORY_PREFIX + pairing.fee_category(raw) != "unknown"


def test_row_facts_union_every_event_and_series_and_count_invalid_entries():
    row = {"feeType": "sports_fees_v3", "negRiskMarketID": "0xabc", "question": "bitcoin?",
           "events": [{"id": "1", "slug": "a-b", "parentEventId": 9,
                       "series": [{"id": "s1", "slug": "nba"}, {"slug": "nba-playoffs"}]},
                      {"id": 2, "slug": "c", "series": [{"slug": {"bad": 1}}]}, "junk"]}
    facts = pairing.row_facts(row)
    assert facts["event_ids"] == ["1", "2"]
    assert facts["series_slugs"] == ["nba", "nba-playoffs"]
    assert facts["parent_event_ids"] == ["9"]
    assert facts["neg_risk_market_id"] == "0xabc"
    assert facts["fee_category"] == "sports" and facts["invalid_entries"] == 2
    assert pairing.row_facts({"events": None})["event_ids"] == []
    with pytest.raises(ValueError):
        pairing.row_facts([])


def test_dependence_groups_transitive_order_independent_and_slug_only_underlyings():
    def facts(events=(), series=(), neg=None, slugs=()):
        return {"event_ids": list(events), "series_slugs": list(series),
                "event_slugs": list(slugs), "neg_risk_market_id": neg}

    rows = {
        "10": facts(events=["e1"]), "11": facts(events=["e2"], neg="n1"),
        "12": facts(events=["e1"], neg="n1"),           # bridges 10 and 11
        "20": facts(events=["e3"], series=["nba"]), "21": facts(events=["e4"], series=["nba"]),
        "30": facts(events=["e5"], slugs=["bitcoin-up-or-down"]),
        "31": facts(events=["e6"], series=["btc-hourly"]),
        "40": facts(events=["e7"]),
    }
    groups = pairing.dependence_groups(rows)
    assert groups["10"] == groups["11"] == groups["12"] == "g:10"
    assert groups["20"] == groups["21"] != groups["10"]
    assert groups["30"] == groups["31"]  # btc/bitcoin tokens of slugs only
    plain = pairing.dependence_groups(rows, underlying=False)
    assert plain["30"] != plain["31"]
    assert groups["40"] == "g:40"
    assert pairing.dependence_groups(dict(reversed(list(rows.items())))) == groups
    assert pairing.underlyings(facts(slugs=["solar-eclipse"])) == []  # exact tokens only
    # parentEventId is an event id: a child event's market joins its parent event's group.
    child = {**facts(events=["e9"]), "parent_event_ids": ["e7"]}
    assert pairing.dependence_groups({**rows, "41": child})["41"] == groups["40"]


def test_design_keeps_scheduled_arm_zero_and_activation_of_pairs_only():
    assert DESIGN.screened_slots == 6 and DESIGN.origin_slots == 4
    assert DESIGN.category_policy == "all"
    for bad in ({"scheduled_per_stratum": 1}, {"activate_screened": True},
                {"pairs_per_stratum": 2}, {"exclude_categories": ("tech", "crypto")},
                {"exclude_categories": ["sports"]}, {"min_groups_per_stratum": 1}):
        with pytest.raises(ValueError):
            replace(DESIGN, **bad)
    excluded = replace(DESIGN, exclude_categories=("crypto", "sports"))
    assert excluded.category_policy == "all_except:crypto,sports"
    assert pairing.design_from_dict(excluded.as_dict()) == excluded


def strata_fixture():
    # Stratum A has groups g1..g4 (g1 has two members); B has g1, g5, g6; C has 2 groups.
    return {
        "A": {"fields": {}, "groups": {"g1": ["1", "2"], "g2": ["3"], "g3": ["4"], "g4": ["5"]}},
        "B": {"fields": {}, "groups": {"g1": ["6"], "g5": ["7"], "g6": ["8"]}},
        "C": {"fields": {}, "groups": {"g7": ["9"], "g8": ["10"]}},
    }


def test_screen_draw_shared_claims_one_member_per_group_and_exact_probabilities():
    for seed in ("a" * 64, "b" * 64, "c" * 64, "d" * 64):
        draw = pairing.screen_draw(seed, strata_fixture(), DESIGN)
        assert draw["drawable_strata"] == ["A", "B"]  # C has fewer than 3 groups
        groups = [p["dependence_group"] for p in draw["screened"]]
        assert len(groups) == len(set(groups))  # g1 screened at most once across strata
        for pick in draw["screened"]:
            assert fraction(pick["stratum_inclusion_probability"]) == 1
            expected = (Fraction(min(3, pick["available_groups"]), pick["available_groups"])
                        / pick["group_members_in_stratum"])
            assert fraction(pick["conditional_market_inclusion_probability"]) == expected
        second = draw["drawn_strata"][1]
        claimed = {p["dependence_group"] for p in draw["screened"]
                   if p["stratum"] == draw["drawn_strata"][0]}
        report = next(r for r in draw["drawn_reports"] if r["stratum"] == second)
        assert report["available_groups"] == len(
            set(strata_fixture()[second]["groups"]) - claimed)
        assert pairing.screen_draw(seed, strata_fixture(), DESIGN) == draw


def test_role_draw_pairs_scarcity_and_no_trigger():
    screened = [{"market_id": m, "stratum": s, "stratum_order": o, "dependence_group": "g" + m}
                for m, s, o in (("1", "A", 0), ("2", "A", 0), ("3", "A", 0),
                                ("4", "B", 1), ("5", "B", 1), ("6", "C", 2))]
    states = {"1": "triggered", "2": "untriggered", "3": "triggered", "4": "triggered",
              "5": "unavailable", "6": "untriggered"}
    states = {m: {"state": s, "evidence_id": f"{int(m):064x}"} for m, s in states.items()}
    draw = pairing.role_draw("a" * 64, screened, states, DESIGN)
    by_stratum = {r["stratum"]: r for r in draw["strata"]}
    assert [by_stratum[k]["pair_state"] for k in "ABC"] == [
        "paired", "control_scarcity", "no_trigger"]
    assert draw["triggers_in_scope"] == 2 and draw["pairs_drawn"] == 1
    assert fraction(draw["fill"]) == Fraction(1, 2) and draw["control_scarcity_strata"] == 1
    trigger = next(a for a in draw["assignments"] if a["arm"] == "triggered")
    control = next(a for a in draw["assignments"] if a["arm"] == "control")
    assert trigger["market_id"] in {"1", "3"} and control["market_id"] == "2"
    assert control["matched_trigger_ids"] == [trigger["trigger_id"]]
    assert fraction(trigger["conditional_role_probability"]) == Fraction(1, 2)
    assert pairing.role_draw("a" * 64, list(reversed(screened)), states, DESIGN) == draw


def population():
    rows = []
    for index in range(1, 25):
        category = "fee:sports" if index <= 12 else "fee:politics"
        rows.append(replace(member(index), category=category,
                            liquidity="5000" if index % 2 else "50000"))
    rows.append(replace(member(99), eligible=False, exclusion_reason="excluded_fixture"))
    return rows


def groups_for(rows):
    # Markets 1/2 and 13/14 are siblings; everything else is its own group.
    result = {r.market_id: "g:" + r.market_id for r in rows}
    result["2"], result["14"] = "g:1", "g:13"
    return result


def first_stage(rows=None, design=DESIGN, groups=None):
    rows = population() if rows is None else rows
    return plan_sample(
        SamplingProtocol("a" * 64, 1, 1, 1, 256), rows, cutoff=AT,
        frame_scope="synthetic pairing population", frame_status="enumerated_complete",
        frame_evidence_ids=["f" * 64], pairing=design,
        dependence_groups=groups_for(rows) if groups is None else groups)


def test_first_stage_plan_v5_group_is_attribute_not_stratum_key():
    result = first_stage()
    assert result["schema_version"] == "fs2-sampling-plan-v5"
    assert result == first_stage(list(reversed(population())))
    assert all("event_group" not in s for s in result["strata"])
    assert {s["category"] for s in result["strata"]} == {"fee:sports", "fee:politics"}
    screened = result["assignments"]
    assert {a["arm"] for a in screened} == {"screened"} and len(screened) == 6
    assert len({a["dependence_group"] for a in screened}) == 6
    assert all(a["activated"] is False for a in screened)
    assert result["exclusions"] == [{"market_id": "99", "reason": "excluded_fixture"}]
    assert result["stratum_draw"]["drawable_strata"] == 4
    assert all(s["scheduled_count"] == 0 for s in result["strata"])
    with pytest.raises(ValueError, match="dependence group"):
        first_stage(groups={})
    with pytest.raises(ValueError, match="attributes"):
        first_stage([replace(m, event_group="e", group_available_at=AT) for m in population()])
    with pytest.raises(ValueError, match="budget"):
        plan_sample(SamplingProtocol("a" * 64, 1, 1, 1, 2), population(), cutoff=AT,
                    frame_scope="x", frame_status="enumerated_complete",
                    frame_evidence_ids=["f" * 64], pairing=DESIGN,
                    dependence_groups=groups_for(population()))


def test_role_stage_plan_v6_uses_first_stage_strata_and_fresh_assessments():
    first = first_stage()
    screened = {a["market_id"]: a for a in first["assignments"]}
    rows = [m for m in population() if m.market_id in screened]
    records = [TriggerAssessment(
        market_id=m.market_id, token_id=m.token_id, policy_hash="c" * 64,
        evidence_id=f"{int(m.market_id) + 1000:064x}",
        state="triggered" if int(m.market_id) % 3 else "untriggered",
        input_window_start=AT, input_window_end=AT, available_at=AT) for m in rows]
    result = plan_sample(
        SamplingProtocol("e" * 64, 6, 1, 1, 6), rows, cutoff=AT,
        frame_scope="screened list", frame_status="explicit_list",
        frame_evidence_ids=["f" * 64], max_frame_members=256,
        assessment_policy=TriggerAssessmentPolicy("c" * 64, AT, 120, 120),
        trigger_assessments=records, pairing=DESIGN, screened_assignments=screened)
    assert result["schema_version"] == "fs2-sampling-plan-v6"
    assert len(result["assessment_inventory"]) == 6
    arms = {a["arm"] for a in result["assignments"]}
    assert arms <= {"triggered", "control"}
    for a in result["assignments"]:
        assert a["stratum"] == screened[a["market_id"]]["stratum"]
        assert a["activated"] is True
    assert result["pairs_drawn"] == len(result["assignments"]) // 2
    assert result["roles_fixed_at_screening"] is True
    with pytest.raises(ValueError, match="cover"):
        plan_sample(SamplingProtocol("e" * 64, 6, 1, 1, 6), rows, cutoff=AT,
                    frame_scope="x", frame_status="explicit_list",
                    frame_evidence_ids=["f" * 64], max_frame_members=256,
                    assessment_policy=TriggerAssessmentPolicy("c" * 64, AT, 120, 120),
                    trigger_assessments=records, pairing=DESIGN,
                    screened_assignments=dict(list(screened.items())[:3]))


def test_legacy_planner_is_unchanged_without_a_pairing_design():
    from tests.unit.test_research_panel_planning import plan

    rows = [member(1, True), member(2, True), *[member(i) for i in range(3, 8)]]
    assert plan(rows)["schema_version"] == "fs2-sampling-plan-v1"
