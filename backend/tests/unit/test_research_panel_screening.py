"""Measured control admission from original raw journals, never empirical evidence."""

import json
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from astrolabe.feature_store.capture import Budget
from astrolabe.feature_store.source_run import SourceRun, _pair
from astrolabe.research_panel.book_computation import record_book_computation
from astrolabe.research_panel.panel_declaration import declare_panel
from astrolabe.research_panel.panel_selection import (
    create_panel_selection,
    selection_root,
)
from astrolabe.research_panel.quote_inputs import QuoteInputPolicy
from astrolabe.research_panel.screening import (
    ScreeningPolicy,
    declare_screening,
    finish_screening,
    read_screening,
)
from astrolabe.research_panel.trigger_computation import (
    SnapshotTriggerPolicy,
    record_snapshot_trigger,
)
from tests.unit.test_feature_store_capture import Stream
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import (
    original_code as _original_code,
)
from tests.unit.test_research_panel_selection import frame

original_code = _original_code


async def prepared(tmp_path, code, age=60, count=2, identity_policy=None):
    rows = [
        market(i, description="Rules", archived=False, acceptingOrders=True,
               **({"events": [{"id": "42"}]} if identity_policy else {}))
        for i in range(1, count + 1)
    ]
    source = await frame(tmp_path, rows)
    panel = tmp_path / "fs2_panel_screen"
    declare_panel(
        source,
        implementation_commit=code[1],
        output_root=panel,
        protocol=protocol(scheduled_per_stratum=2),
        storage_profile="compact-v1",
    )
    create_panel_selection(panel, repository=code[0])
    root = tmp_path / "fs2_screening_test"
    policy = declare_screening(
        selection_root(panel),
        output_root=root,
        rule=SnapshotTriggerPolicy(1, 3, 60000),
        policy=ScreeningPolicy(age, age), identity_policy=identity_policy,
    )
    ids = {r["member"]["market_id"] for r in policy["selected"]}
    return root, policy, [r for r in rows if r["id"] in ids]


async def assessed(tmp_path, policy, rows, bids=("2", "1"), changed=False, gamma_status=200):
    from pathlib import Path

    for i, (item, row, bid) in enumerate(zip(policy["selected"], rows, bids, strict=True)):
        payload = dict(row)
        if changed:
            payload["description"] = "Changed rules"
        token = item["member"]["token_id"]
        book = {
            "market": row["conditionId"],
            "asset_id": token,
            "bids": [{"price": "0.4", "size": bid}],
            "asks": [{"price": "0.6", "size": "1"}],
            "timestamp": "1",
        }

        def handler(request, payload=payload, book=book):
            data = payload if request.url.path.startswith("/markets/") else book
            status = gamma_status if request.url.path.startswith("/markets/") else 200
            return httpx.Response(status, stream=Stream([json.dumps(data).encode()]))

        source = tmp_path / f"fs2_capture_screen_{i}"
        run = SourceRun(
            source,
            transport=httpx.MockTransport(handler),
            policy_version="receipt-time-selected-market-v1",
            budget=Budget(requests=2),
            retained_bytes=4 * 1048576,
        )
        await run.fetch("gamma.market", {"market_id": row["id"]})
        await run.fetch("clob.book", {"token_id": token})
        record_book_computation(
            source, output_root=Path(item["book_root"]), policy=QuoteInputPolicy(60, 60)
        )
        record_snapshot_trigger(Path(item["declaration_root"]))


async def test_measured_controls_conditional_weights_and_immutable_recovery(
    tmp_path, original_code
):
    root, policy, rows = await prepared(tmp_path, original_code)
    await assessed(tmp_path, policy, rows)
    before = snapshot(selection_root(tmp_path / "fs2_panel_screen"))
    result = finish_screening(root)
    roles = result["plan"]["assignments"]
    assert [r["market_id"] for r in roles if r["arm"] == "triggered"] == ["1"]
    assert [r["market_id"] for r in roles if r["arm"] == "control"] == ["2"]
    assert len([r for r in roles if r["arm"] == "scheduled"]) == 2
    assert result["plan"]["strata"][0]["unfilled_control_slots"] == 1
    assert result["plan"]["global_arm_inclusion_probability"] is None
    assert all(r["screening_inclusion_probability"]["numerator"] == "1" for r in roles)
    assert result["provenance_class"] == "synthetic"
    assert not result["origin_admitted"] and not result["accepted_panel"]
    sealed = snapshot(root)
    assert read_screening(root) == result
    assert snapshot(root) == sealed
    assert snapshot(selection_root(tmp_path / "fs2_panel_screen")) == before
    with pytest.raises(FileExistsError):
        finish_screening(root)


@pytest.mark.parametrize("bids,expected", [(("1", "1"), "untriggered"), (("2", "2"), "triggered")])
async def test_one_sided_pool_never_redraws_or_invents_controls(
    tmp_path, original_code, bids, expected
):
    root, policy, rows = await prepared(tmp_path, original_code)
    await assessed(tmp_path, policy, rows, bids)
    result = finish_screening(root)
    assert {r["effective_state"] for r in result["plan"]["assessment_inventory"]} == {expected}
    assert not any(r["arm"] == "control" for r in result["plan"]["assignments"])
    assert result["plan"]["strata"][0]["controls_selected"] == 0


async def test_unassessed_stays_unknown_and_postseal_addition_refused(tmp_path, original_code):
    root, policy, rows = await prepared(tmp_path, original_code)
    result = finish_screening(root)
    assert {r["effective_state"] for r in result["plan"]["assessment_inventory"]} == {
        "not_assessed"
    }
    assert {r["arm"] for r in result["plan"]["assignments"]} == {"scheduled"}
    await assessed(tmp_path, policy, rows)
    with pytest.raises(ValueError):
        read_screening(root)


@pytest.mark.parametrize("changed,age", [(True, 60), (False, 0)])
async def test_changed_mapping_or_stale_value_is_not_negative(
    tmp_path, original_code, changed, age
):
    root, policy, rows = await prepared(tmp_path, original_code, age)
    await assessed(tmp_path, policy, rows, changed=changed)
    result = finish_screening(root)
    assert {r["effective_state"] for r in result["plan"]["assessment_inventory"]} == {"unavailable"}
    assert {r["arm"] for r in result["plan"]["assignments"]} == {"scheduled"}


@pytest.mark.parametrize("target", ["raw", "plan", "clock", "assignment"])
async def test_raw_resealed_result_clock_and_assignment_tampering_refused(
    tmp_path, original_code, target
):
    root, policy, rows = await prepared(tmp_path, original_code)
    await assessed(tmp_path, policy, rows)
    finish_screening(root)
    if target == "raw":
        next((tmp_path / "fs2_capture_screen_0").glob("*/raw.bin")).write_bytes(b"corrupt")
    elif target == "plan":
        rewrite(
            root,
            "screening_report",
            lambda p: p["plan"].update(global_arm_inclusion_probability="1"),
        )
    elif target == "clock":
        frozen, _ = _pair(root, "screening_policy")
        rewrite(root, "screening_report", lambda p: p.update(cutoff=frozen["declared_at"]))
    else:
        rewrite(
            root, "screening_policy", lambda p: p["selected"][0]["member"].update(token_id="999")
        )
    with pytest.raises(ValueError):
        read_screening(root)


async def test_single_completion_owner(tmp_path, original_code):
    root, policy, rows = await prepared(tmp_path, original_code)
    await assessed(tmp_path, policy, rows)

    def attempt():
        try:
            return finish_screening(root)
        except FileExistsError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert len([r for r in results if r]) == 1


async def test_full_original_build_recovery_and_transitive_protection(tmp_path, original_code):
    from pathlib import Path

    from astrolabe.research_panel.original_reader import read_original_screening

    root, policy, rows = await prepared(tmp_path, original_code)
    await assessed(tmp_path, policy, rows)
    result = finish_screening(root)
    recovered = read_original_screening(
        root,
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_screening_read_test",
    )
    assert recovered["report"] == result
    assert not recovered["read_receipt"]["observation_clocks_changed"]
    for dependency in (
        root,
        Path(policy["selection_root"]),
        tmp_path / "fs2_capture_screen_0",
        Path(policy["selected"][0]["declaration_root"]),
    ):
        with pytest.raises(ValueError, match="separate"):
            read_original_screening(
                root,
                implementation_commit=original_code[1],
                repository=original_code[0],
                output_root=dependency / "fs2_screening_read_bad",
            )


async def test_first_stage_fraction_is_preserved_without_false_global_weight(
    tmp_path, original_code
):
    root, policy, rows = await prepared(tmp_path, original_code, count=3)
    await assessed(tmp_path, policy, rows)
    result = finish_screening(root)
    for assignment in result["plan"]["assignments"]:
        assert assignment["screening_inclusion_probability"]["numerator"] == "2"
        assert assignment["screening_inclusion_probability"]["denominator"] == "3"
        assert assignment["inclusion_probability"]["numerator"] == "1"
        assert assignment["inclusion_probability"]["denominator"] == "1"
    assert result["plan"]["global_arm_inclusion_probability"] is None


async def test_source_failure_remains_unavailable_not_negative(tmp_path, original_code):
    root, policy, rows = await prepared(tmp_path, original_code)
    await assessed(tmp_path, policy, rows, gamma_status=503)
    result = finish_screening(root)
    assert {r["effective_state"] for r in result["plan"]["assessment_inventory"]} == {"unavailable"}
    assert {r["arm"] for r in result["plan"]["assignments"]} == {"scheduled"}


async def test_partial_screen_keeps_unknown_and_unfilled_control_slots(tmp_path, original_code):
    root, policy, rows = await prepared(tmp_path, original_code)
    await assessed(tmp_path, {**policy, "selected": policy["selected"][:1]}, rows[:1], bids=("2",))
    result = finish_screening(root)
    strata = result["plan"]["strata"][0]
    assert strata["triggered_count"] == 1
    assert strata["controls_selected"] == 0 and strata["unfilled_control_slots"] == 2
    assert strata["assessment_counts"]["not_assessed"] == 1
    assert len([r for r in result["plan"]["assignments"] if r["arm"] == "scheduled"]) == 2


async def test_endpoint_asymmetry_versioned_evidence_original_recovery(tmp_path, original_code):
    from astrolabe.research_panel.identity_comparison import VERSION as comparator
    from astrolabe.research_panel.original_reader import read_original_screening

    root, policy, rows = await prepared(tmp_path, original_code, identity_policy=comparator)
    targeted = [{k: v for k, v in row.items() if k != 'events'} for row in rows]
    await assessed(tmp_path, policy, targeted)
    result = finish_screening(root)
    assert {s['state'] for s in result['states']} == {'triggered', 'untriggered'}
    assert all(s['identity_comparison']['current_event_membership'] == 'unavailable'
               for s in result['states'])
    assert not result['origin_admitted']
    recovered = read_original_screening(root, implementation_commit=original_code[1],
                                        repository=original_code[0],
                                        output_root=tmp_path / 'fs2_screening_read_asymmetry')
    assert recovered['report'] == result
    from astrolabe.research_panel.activation import activate_screened_panel

    with pytest.raises(ValueError, match='versioned origin contract'):
        activate_screened_panel(tmp_path / 'fs2_panel_screen', root)

    def corrupt(value):
        value['states'][0]['identity_comparison']['core_identity_equal'] = False

    rewrite(root, 'screening_report', corrupt)
    with pytest.raises(ValueError):
        read_screening(root)


async def test_new_identity_policy_still_rejects_changed_rules(tmp_path, original_code):
    from astrolabe.research_panel.identity_comparison import VERSION as comparator

    root, policy, rows = await prepared(tmp_path, original_code, identity_policy=comparator)
    await assessed(tmp_path, policy, rows, changed=True)
    result = finish_screening(root)
    assert {s['state'] for s in result['states']} == {'unavailable'}
    assert all(not s['identity_comparison']['core_identity_equal'] for s in result['states'])


@pytest.mark.parametrize('policy', ['', True, 'future-policy'])
def test_unknown_identity_policy_refused_before_any_write(tmp_path, policy):
    with pytest.raises(ValueError, match='identity policy'):
        declare_screening(tmp_path / 'absent', output_root=tmp_path / 'fs2_screening_invalid',
                          rule=SnapshotTriggerPolicy(1, 3, 60000),
                          policy=ScreeningPolicy(60, 60), identity_policy=policy)
    assert not list(tmp_path.iterdir())
