"""D118 population: temporal scope intersected with frame Gamma liquidity >= 1000.

The complete discovery inventory is retained; excluded members get explicit zero-inclusion
records; the earlier temporal (v4/v3) and legacy paths are unchanged.
"""

from dataclasses import asdict, replace
from datetime import UTC, datetime

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.original_reader import read_original_selection
from astrolabe.research_panel.panel_declaration import (
    LIQUIDITY_FLOOR,
    LIQUIDITY_POPULATION,
    LIQUIDITY_VERSION,
    TEMPORAL_POPULATION,
    TEMPORAL_VERSION,
    declare_panel,
    read_panel_declaration,
)
from astrolabe.research_panel.panel_selection import (
    LIQUIDITY_BELOW,
    LIQUIDITY_UNKNOWN,
    bound_plan,
    create_panel_selection,
    selection_root,
)
from astrolabe.research_panel.sampling import SamplingProtocol
from astrolabe.research_panel.screening import _selected
from astrolabe.research_panel.selection import read_selection
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_planning import member
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code
TEMPORAL_REASON = 'scheduled_end_at_or_before_selection_declaration'


def test_floor_is_the_first_predeclared_liquidity_edge():
    assert SamplingProtocol('a' * 64, 1, 1, 1, 1).liquidity_edges[0] == LIQUIDITY_FLOOR == '1000'


async def test_liquidity_population_excludes_with_reasons_and_keeps_inventory(
    tmp_path, original_code
):
    source = await frame(tmp_path, [
        market(1, endDate='2000-01-01T00:00:00Z', liquidity='5000'),  # temporal first
        market(2, endDate='2099-01-01T00:00:00Z', liquidity='1000'),  # exactly at floor
        market(3, liquidity='999.99'),
        market(4),  # liquidity missing
        market(5, liquidity='not-a-number'),  # invalid -> unknown, never imputed
        market(6, liquidity=25000.5),
        market(7, clobTokenIds=None, liquidity='9000'),  # unmapped, not a sampling member
    ])
    panel = tmp_path / 'fs2_panel_liquidity'
    declared = declare_panel(source, implementation_commit=original_code[1], output_root=panel,
        protocol=protocol(scheduled_slots=8, scheduled_per_stratum=2, cycles=1,
                          target_attempts=1),
        storage_profile='compact-v1', strata_limit=4, population_policy=LIQUIDITY_POPULATION)
    assert declared['schema_version'] == LIQUIDITY_VERSION == 'fs2-panel-declaration-v5'
    assert declared['population_policy'] == LIQUIDITY_POPULATION
    before = snapshot(source), snapshot(panel)
    result = create_panel_selection(panel, repository=original_code[0])
    root = selection_root(panel)
    assert result['schema_version'] == 'fs2-panel-selection-v4'
    assert result['counts']['source_rows'] == 7
    assert result['counts']['sampling_members'] == 6
    plan = result['plan']
    assert plan['schema_version'] == 'fs2-panel-selection-plan-v4'
    assert plan['population_policy'] == LIQUIDITY_POPULATION
    assert plan['liquidity_floor'] == '1000'
    assert plan['selection_eligible_member_count'] == 2
    assert plan['frame_size'] == len(plan['exclusions']) + plan['selection_eligible_member_count']
    assert plan['exclusions'] == [
        {'market_id': '1', 'reason': TEMPORAL_REASON},
        {'market_id': '3', 'reason': LIQUIDITY_BELOW},
        {'market_id': '4', 'reason': LIQUIDITY_UNKNOWN},
        {'market_id': '5', 'reason': LIQUIDITY_UNKNOWN},
    ]
    assert plan['population_exclusion_counts'] == {
        LIQUIDITY_BELOW: 1, LIQUIDITY_UNKNOWN: 2, TEMPORAL_REASON: 1}
    assert {a['market_id'] for a in plan['assignments']} == {'2', '6'}
    assert {s['liquidity_band'] for s in plan['strata']} <= {'1', '2', '3'}
    assert 'liquidity at least 1000' in plan['frame_scope']
    policy, _ = _pair(root, 'selection_policy')
    assert plan['population_reference_at'] == policy['declared_at']
    assert before == (snapshot(source), snapshot(panel))
    assert result == read_selection(root)
    recovered = read_original_selection(root, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_selection_read_liquidity')
    assert recovered['report'] == result
    _, _, selected = _selected(root)
    assert {r['member']['market_id'] for r in selected} == {'2', '6'}
    amend(root, 'selection_policy', lambda p: p.update(population_policy=TEMPORAL_POPULATION))
    with pytest.raises(ValueError, match='declaration/recipe'):
        read_selection(root)


async def test_temporal_v4_declaration_is_unchanged(tmp_path, original_code):
    source = await frame(tmp_path, [market(1, liquidity='5')])
    panel = tmp_path / 'fs2_panel_temporal_only'
    declared = declare_panel(source, implementation_commit=original_code[1], output_root=panel,
        protocol=protocol(), population_policy=TEMPORAL_POPULATION)
    assert declared['schema_version'] == TEMPORAL_VERSION == 'fs2-panel-declaration-v4'
    assert read_panel_declaration(panel) == declared
    chosen = create_panel_selection(panel, repository=original_code[0])
    # The temporal path never applies the liquidity scope.
    assert chosen['plan']['schema_version'] == 'fs2-panel-selection-plan-v3'
    assert chosen['plan']['exclusions'] == []
    assert 'liquidity_floor' not in chosen['plan']


def _policy(population):
    return {'schema_version': ('fs2-panel-selection-v4' if population == LIQUIDITY_POPULATION
                               else 'fs2-panel-selection-v3'),
            'population_policy': population,
            'assessment_policy': {'version': 'fs2-no-measured-assessments-v1',
                                  'state': 'not_assessed', 'reason': 'not_assessed',
                                  'supplied_assessments': 0, 'matched_controls_eligible': False},
            'declared_at': {'utc': '2026-01-01T00:00:00Z'}, 'budget': {'rows': 400000},
            'sampling_protocol': asdict(SamplingProtocol('a' * 64, 1, 1, 1, 8)),
            'panel_protocol': {'scheduled_slots': 8}}


def test_bound_plan_scope_is_pure_and_does_not_mutate_members():
    at = {'utc': '2026-01-01T00:00:00Z'}
    early = datetime(2025, 1, 1, tzinfo=UTC)
    rows = [replace(member(i), available_at=early, liquidity=value)
            for i, value in ((1, None), (2, '999.999999'), (3, '1000'), (4, '1000000'))]
    new = bound_plan(_policy(LIQUIDITY_POPULATION), rows, at, 'b' * 64, 'c' * 64)
    assert [e['reason'] for e in new['exclusions']] == [LIQUIDITY_UNKNOWN, LIQUIDITY_BELOW]
    assert {a['market_id'] for a in new['assignments']} <= {'3', '4'}
    assert new['selection_eligible_member_count'] == 2
    assert all(r.eligible for r in rows)
    temporal = bound_plan(_policy(TEMPORAL_POPULATION), rows, at, 'b' * 64, 'c' * 64)
    assert temporal['exclusions'] == [] and temporal['selection_eligible_member_count'] == 4
    assert 'population_exclusion_counts' not in temporal


def test_floor_must_equal_frozen_first_edge():
    policy = _policy(LIQUIDITY_POPULATION)
    policy['sampling_protocol']['liquidity_edges'] = ['500', '10000', '100000']
    with pytest.raises(ValueError, match='first frozen liquidity edge'):
        bound_plan(policy, [member(1)], {'utc': '2026-01-01T00:00:00Z'}, 'b' * 64, 'c' * 64)
