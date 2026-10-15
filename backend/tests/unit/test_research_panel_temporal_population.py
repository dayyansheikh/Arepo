"""Prospective deep-sample scope; complete original frame and legacy samples survive."""

from dataclasses import asdict, replace
from datetime import UTC, datetime

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.original_reader import read_original_selection
from astrolabe.research_panel.panel_declaration import TEMPORAL_POPULATION, declare_panel
from astrolabe.research_panel.panel_selection import (
    bound_plan,
    create_panel_selection,
    selection_root,
)
from astrolabe.research_panel.sampling import SamplingProtocol
from astrolabe.research_panel.screening import _selected
from astrolabe.research_panel.selection import read_selection
from tests.unit.test_research_panel_declaration import paths, protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_planning import member
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


@pytest.mark.parametrize('bounded', [False, True])
async def test_temporal_population_preserves_inventory_unknowns_weights_and_original_recovery(
    tmp_path, original_code, bounded
):
    source = await frame(tmp_path, [market(1, endDate='2000-01-01T00:00:00Z'),
        market(2, endDate='2099-01-01T00:00:00Z'), market(3), market(4, endDate='invalid'),
        market(5, clobTokenIds=None)])
    panel = tmp_path / 'fs2_panel_temporal'
    declare_panel(source, implementation_commit=original_code[1], output_root=panel,
        protocol=protocol(scheduled_slots=8, scheduled_per_stratum=2, cycles=1, target_attempts=1),
        storage_profile='compact-v1', strata_limit=2 if bounded else None,
        population_policy=TEMPORAL_POPULATION)
    before = snapshot(source), snapshot(panel)
    result = create_panel_selection(panel, repository=original_code[0])
    root = selection_root(panel)
    assert result['counts']['source_rows'] == 5
    assert result['counts']['sampling_members'] == 4  # mapped inventory, not temporal eligibility
    assert result['counts']['excluded:identity_unresolved'] == 1
    plan = result['plan']
    assert plan['schema_version'] == 'fs2-panel-selection-plan-v3'
    assert plan['selection_eligible_member_count'] == 3
    assert plan['assessment_inventory_encoding']['member_count'] == 4
    assert plan['exclusions'] == [{'market_id': '1',
        'reason': 'scheduled_end_at_or_before_selection_declaration'}]
    assert {a['market_id'] for a in plan['assignments']} == {'2', '3', '4'}
    assert all(a['inclusion_probability']['numerator'] ==
               a['inclusion_probability']['denominator'] for a in plan['assignments'])
    policy, _ = _pair(root, 'selection_policy')
    assert plan['population_reference_at'] == policy['declared_at']
    assert 'not a claim of active trading' in plan['frame_scope']
    assert before == (snapshot(source), snapshot(panel))
    assert result == read_selection(root)
    recovered = read_original_selection(root, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_selection_read_temporal')
    assert recovered['report'] == result
    _, _, selected = _selected(root)
    assert {r['member']['market_id'] for r in selected} == {'2', '3', '4'}
    amend(root, 'selection_policy', lambda p: p.pop('population_policy'))
    with pytest.raises(ValueError, match='declaration/recipe'):
        read_selection(root)


@pytest.mark.parametrize('bad', ['invented', False, {}, 3])
def test_unknown_population_refuses_before_writes(tmp_path, bad):
    source, panel = paths(tmp_path)
    with pytest.raises(ValueError, match='population policy'):
        declare_panel(source, implementation_commit='a'*40, output_root=panel,
                      protocol=protocol(), population_policy=bad)
    assert not panel.exists()


def test_temporal_scope_exclusion_does_not_mutate_legacy_members_or_lose_empty_inventory():
    at = {'utc': '2026-01-01T00:00:00Z'}
    rows = [replace(member(1), close_stratum='past', available_at=datetime(2025, 1, 1, tzinfo=UTC))]
    p = {'schema_version': 'fs2-panel-selection-v3', 'population_policy': TEMPORAL_POPULATION,
         'assessment_policy': {'version': 'fs2-no-measured-assessments-v1',
                              'state': 'not_assessed', 'reason': 'not_assessed',
                              'supplied_assessments': 0, 'matched_controls_eligible': False},
         'declared_at': at, 'budget': {'rows': 400000},
         'sampling_protocol': asdict(SamplingProtocol('a'*64, 1, 1, 1, 4)),
         'panel_protocol': {'scheduled_slots': 4}}
    new = bound_plan(p, rows, at, 'b'*64, 'c'*64)
    assert not new['assignments'] and new['selection_eligible_member_count'] == 0
    assert len(new['exclusions']) == 1 and rows[0].eligible
    legacy = {k: v for k, v in p.items() if k != 'population_policy'}
    legacy['schema_version'] = 'fs2-panel-selection-v1'
    assert len(bound_plan(legacy, rows, at, 'b'*64, 'c'*64)['assignments']) == 1


async def test_temporal_selection_owned_runtime_keeps_controls_and_original_audit(
    tmp_path, original_code
):
    from astrolabe.research_panel.screening import ScreeningPolicy
    from astrolabe.research_panel.screening_worker import run_synthetic_pilot
    from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
    from tests.unit.test_research_panel_owned_pilot import transport

    rows = [market(i, description='Rules', archived=False, acceptingOrders=True,
                   endDate='2000-01-01T00:00:00Z' if i == 3 else '2099-01-01T00:00:00Z',
                   events=[{'id': '42'}]) for i in (1, 2, 3)]
    source = await frame(tmp_path, rows)
    panel = tmp_path / 'fs2_panel_temporal_runtime'
    declare_panel(source, implementation_commit=original_code[1], output_root=panel,
        protocol=protocol(scheduled_per_stratum=2, controls_per_trigger=1, cycles=1,
            target_attempts=1, max_origin_delay_seconds=30, horizon_seconds=8,
            tolerance_seconds=5, max_origin_save_seconds=2, max_quote_age_seconds=60,
            source_run_retained_bytes=4*1048576),
        storage_profile='compact-v1', strata_limit=1, population_policy=TEMPORAL_POPULATION)
    chosen = create_panel_selection(panel, repository=original_code[0])
    mock, calls = transport(rows)
    result = await run_synthetic_pilot(panel, implementation_commit=original_code[1],
        repository=original_code[0], transport=mock,
        rule=SnapshotTriggerPolicy(1, 3, 60000), freshness=ScreeningPolicy(60, 60),
        concurrency=2, runtime_concurrency=3)
    assert chosen['plan']['selection_eligible_member_count'] == 2
    assert len(result['runtime']['origins']) == 2
    assert {o['state'] for o in result['runtime']['origins']} == {'observed'}
    assert {o['state'] for o in result['runtime']['outcomes']} == {'observed'}
    assert result['role_capacity']['counts_per_cycle'] == {
        'scheduled': 2, 'triggered': 1, 'control': 1}
    assert len(result['recovery']) == 1 and len(calls) == 14
    assert not any('/markets/3' in call for call in calls)
    assert not result['accepted_panel']
