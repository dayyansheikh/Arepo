"""Private owned transition and independent cold recovery, without an origin shortcut."""

import sys

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import activation, origin_worker, screening
from astrolabe.research_panel.original_reader import read_original_activation
from astrolabe.research_panel.panel_selection import selection_root
from astrolabe.research_panel.trigger_computation import SnapshotTriggerPolicy
from tests.unit.test_research_panel_input_read import rewrite
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_screening import assessed
from tests.unit.test_research_panel_screening_worker import prepared

original_code = _original_code


async def ready(tmp_path, code):
    _, panel, rows = await prepared(tmp_path, code, event_ids=True)
    root = tmp_path / 'fs2_screening_owned'
    frozen, finish = screening._prepare_owned_screening(
        selection_root(panel), output_root=root,
        rule=SnapshotTriggerPolicy(1, 3, 60000), policy=screening.ScreeningPolicy(60, 60))
    # Only the fixture's targeted endpoint shape differs; the original frame is intact.
    current_rows = [{k: v for k, v in row.items() if k != 'events'} for row in rows]
    await assessed(tmp_path, frozen, current_rows)
    return panel, root, finish


async def test_owned_activation_skips_population_work_and_recovers_original_identity(
    tmp_path, original_code
):
    panel, root, finish = await ready(tmp_path, original_code)
    full_read_calls = []
    code = screening._selected.__code__

    def observe(frame, event, arg):
        if event == 'call' and frame.f_code is code:
            full_read_calls.append(True)

    previous = sys.getprofile()
    sys.setprofile(observe)
    try:
        screened, active = finish(activate=True)
    finally:
        sys.setprofile(previous)
    assert not full_read_calls
    assert active['schema_version'] == activation.OWNED_VERSION
    assert active['role_capacity']['counts_per_cycle'] == {
        'scheduled': 2, 'triggered': 1, 'control': 1}
    assert active['provenance_class'] == 'synthetic'
    assert active['screening_report_hash'] == screened['screening_report_hash']
    for member in active['selected']:
        assert member['frame_identity']['source_event_ids'] == ['42']
        assert member['identity_policy'] == screening.IDENTITY_POLICY
        assert member['mapping_version'] == member['frame_identity']['mapping_version']
    assert all(r['identity_comparison']['current_event_membership'] == 'unavailable'
               for r in screened['states'])
    assert activation.read_activation(panel) == active
    recovered = read_original_activation(
        activation.activation_root(panel), implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_activation_read_owned')
    assert recovered['report']['summary'] == active
    assert not active['origin_admitted'] and not active['accepted_panel']
    policy, _ = _pair(panel, 'panel_policy')
    with pytest.raises(ValueError, match='transport provenance'):
        await origin_worker._collect_one(
            tmp_path / 'must_not_create_origin', active['slots'][0], active['selected'][0],
            policy, active, None,
            features=True)
    assert not (tmp_path / 'must_not_create_origin').exists()


async def test_owned_activation_cold_read_rejects_changed_frame_identity(tmp_path, original_code):
    panel, root, finish = await ready(tmp_path, original_code)
    _, active = finish(activate=True)
    facts = activation.activation_root(panel)
    rewrite(facts, 'activation_facts',
            lambda p: p['selected'][0]['frame_identity'].update(source_event_ids=[]))
    with pytest.raises(ValueError, match='identity|selection'):
        activation.read_activation(panel)
    assert active['selected'][0]['frame_identity']['source_event_ids'] == ['42']
