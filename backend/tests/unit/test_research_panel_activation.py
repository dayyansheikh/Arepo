"""Actual activation reads and stable schedules from synthetic source/selection journals."""

import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest

from astrolabe.feature_store.source_bridge import _time
from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import _PACKAGE_FILES, activation
from astrolabe.research_panel.activation import (
    POLICY,
    activate_panel,
    activation_root,
    allocation,
    read_activation,
)
from astrolabe.research_panel.panel_declaration import declare_panel, read_panel_declaration
from astrolabe.research_panel.panel_selection import create_panel_selection, selection_root
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


async def prepared(tmp_path, original_code, **changes):
    source = await frame(tmp_path, [market(1), market(2, category='sports')])
    panel = tmp_path / 'fs2_panel_activation'
    declared = declare_panel(source, implementation_commit=original_code[1], output_root=panel,
                              protocol=protocol(**changes), storage_profile='compact-v1')
    selected = create_panel_selection(panel, repository=original_code[0])
    return source, panel, declared, selected


async def test_actual_full_selection_read_identity_and_schedule_anchor(tmp_path, original_code):
    source, panel, declaration, selected = await prepared(tmp_path, original_code)
    before = snapshot(source), snapshot(panel), snapshot(selection_root(panel))
    result = activate_panel(panel)
    root = activation_root(panel)
    policy, policy_ack = _pair(root, 'activation_policy')
    facts, facts_ack = _pair(root, 'activation_facts')
    assert policy['panel_declaration_hash'] == declaration['declaration_hash']
    assert policy_ack['durable_ack']['utc'] <= facts['read_started_at']['utc']
    assert selected['selection_available_at']['utc'] <= facts['read_started_at']['utc']
    assert facts['read_completed_at']['utc'] <= facts_ack['durable_ack']['utc']
    assert result['provenance_class'] == 'synthetic'
    assert len(result['selected']) == 2 and len(result['slots']) == 4
    assert len({s['intent_id'] for s in result['slots']}) == 4
    first = _time(facts_ack['durable_ack']) + timedelta(seconds=2)
    for slot in result['slots']:
        expected = first + timedelta(seconds=slot['cycle'] * 300)
        assert slot['scheduled_at'] == expected.isoformat()
        assert slot['latest_origin_at'] == (expected + timedelta(seconds=20)).isoformat()
    for member in result['selected']:
        assert member['condition_id'] == '0x' + f'{int(member["market_id"]):064x}'
        assert member['token_id'] == str(2 * int(member['market_id']))
        assert member['outcome_index'] == 0 and member['outcome_label'] == 'Yes'
        assert member['roles'][0]['assessment_state'] == 'not_assessed'
        assert member['roles'][0]['source_observation_id'] == member['source_observation_id']
    assert (result['origin_admitted'] is result['collection_enabled']
            is result['accepted_panel'] is False)
    saved = snapshot(root)
    assert read_activation(panel) == result
    assert saved == snapshot(root)
    assert before == (snapshot(source), snapshot(panel), snapshot(selection_root(panel)))


async def test_complete_origin_and_target_metadata_reservation(tmp_path, original_code):
    _, panel, declared, _ = await prepared(tmp_path, original_code)
    extra = (declared['reservation']['origin_slots'] * POLICY['per_origin_metadata_bytes']
             + declared['reservation']['target_attempt_slots']
             * POLICY['per_target_metadata_bytes'])
    reserved = allocation(declared)
    assert reserved['runtime_metadata_bytes'] == extra
    assert reserved['total_retained_bytes'] == (declared['reservation']['total_retained_bytes']
                                               + POLICY['max_output_bytes'] + extra)
    assert reserved['duration_seconds'] == declared['reservation']['duration_seconds'] + 2
    assert reserved['future_writer_quota_enforcement_required'] is True
    activate_panel(panel)
    policy, _ = _pair(activation_root(panel), 'activation_policy')
    assert policy['reservation'] == reserved


async def test_capacity_refuses_before_consuming_selection(tmp_path, original_code, monkeypatch):
    _, panel, declaration, _ = await prepared(tmp_path, original_code)
    needed = allocation(declaration)['required_free_bytes']
    monkeypatch.setattr(shutil, 'disk_usage',
                        lambda p: shutil._ntuple_diskusage(needed, 1, needed - 1))
    with pytest.raises(ValueError, match='complete activation/origin/target reservation'):
        activate_panel(panel)
    assert not activation_root(panel).exists()


async def test_recovery_preserves_expired_schedule_without_current_capacity_check(
        tmp_path, original_code, monkeypatch):
    _, panel, _, _ = await prepared(tmp_path, original_code)
    expected = activate_panel(panel)
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(1, 1, 0))
    monkeypatch.setattr(activation, '_clock', lambda: (_ for _ in ()).throw(AssertionError()))
    assert read_activation(panel) == expected
    with pytest.raises(FileExistsError, match='never resume or reschedule'):
        activate_panel(panel)


@pytest.mark.parametrize('change', ['weight', 'identity', 'clock', 'claim', 'schedule', 'source',
                                   'extra', 'reservation', 'profile'])
async def test_rehashed_identity_lineage_and_admission_changes_refused(
        tmp_path, original_code, change):
    source, panel, _, _ = await prepared(tmp_path, original_code)
    activate_panel(panel)
    root = activation_root(panel)
    if change == 'weight':
        amend(root, 'activation_facts', lambda p: p['selected'][0]['roles'][0][
            'inclusion_probability'].update(denominator='100'))
    elif change == 'identity':
        amend(root, 'activation_facts', lambda p: p['selected'][0].update(token_id='98765'))
    elif change == 'clock':
        amend(root, 'activation_facts', lambda p: p.update(
            read_started_at={'utc': '2000-01-01T00:00:00Z',
                             'monotonic_ns': '1', 'clock_session_id': 'old'}))
    elif change == 'claim':
        amend(root, 'activation_facts', lambda p: p.update(origin_admitted=True))
    elif change == 'schedule':
        amend(root, 'activation_policy', lambda p: p['policy'].update(lead_seconds=0))
    elif change == 'reservation':
        amend(root, 'activation_policy', lambda p: p['reservation'].update(
            runtime_metadata_bytes=0))
    elif change == 'profile':
        amend(panel, 'panel_policy', lambda p: p.update(computation_storage_profile=None))
    elif change == 'source':
        next(source.glob('*/raw.bin')).write_bytes(b'changed fixture')
    else:
        (root / 'unrecorded').write_text('{}')
    saved = snapshot(root)
    with pytest.raises(ValueError):
        read_activation(panel)
    assert snapshot(root) == saved


async def test_failure_is_retained_when_selection_no_longer_verifies(tmp_path, original_code):
    source, panel, _, _ = await prepared(tmp_path, original_code)
    next(source.glob('*/raw.bin')).write_bytes(b'corrupt fixture')
    with pytest.raises(ValueError):
        activate_panel(panel)
    root = activation_root(panel)
    assert (root / 'activation_policy_ack.json').exists()
    assert (root / 'activation_failure_ack.json').exists()
    assert not (root / 'activation_facts.json').exists()
    with pytest.raises(FileExistsError):
        activate_panel(panel)


async def test_source_expiry_during_actual_activation_save_preserves_failed_ack(
        tmp_path, original_code, monkeypatch):
    _, panel, _, _ = await prepared(tmp_path, original_code, max_frame_age_seconds=10,
                                    max_frame_interval_seconds=1)
    persist = activation._persist
    def delayed(root, name, payload):
        if name == 'activation_facts':
            time.sleep(10.1)
        return persist(root, name, payload)
    monkeypatch.setattr(activation, '_persist', delayed)
    with pytest.raises(ValueError, match='stale'):
        activate_panel(panel)
    root = activation_root(panel)
    assert (root / 'activation_facts_ack.json').exists()
    assert (root / 'activation_failure_ack.json').exists()
    with pytest.raises(ValueError, match='complete successful'):
        read_activation(panel)


async def test_exclusive_activation_ownership(tmp_path, original_code):
    _, panel, _, _ = await prepared(tmp_path, original_code)
    def attempt():
        try:
            return activate_panel(panel)
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(r is not None for r in results) == 1
    assert not (activation_root(panel) / 'activation_failure.json').exists()
    read_activation(panel)


async def test_changed_build_or_caller_payload_cannot_activate(
        tmp_path, original_code, monkeypatch):
    _, panel, _, _ = await prepared(tmp_path, original_code)
    for kw in ({'clock': None}, {'selected': []}, {'output_root': tmp_path}, {'seed': '0' * 64}):
        with pytest.raises(TypeError):
            activate_panel(panel, **kw)
    monkeypatch.setitem(_PACKAGE_FILES, 'activation.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed'):
        activate_panel(panel)
    assert not activation_root(panel).exists()


async def test_actual_read_clock_cannot_precede_selection_availability(
        tmp_path, original_code, monkeypatch):
    _, panel, _, _ = await prepared(tmp_path, original_code)
    monkeypatch.setattr(activation, '_clock', lambda: {
        'utc': '2000-01-01T00:00:00Z', 'clock_session_id': 'old', 'monotonic_ns': '1'})
    with pytest.raises(ValueError, match='chronology'):
        activate_panel(panel)
    assert (activation_root(panel) / 'activation_failure_ack.json').exists()


def test_output_caps_reject_before_excess_write(tmp_path):
    root = tmp_path / 'fs2_activation_cap'
    root.mkdir()
    with pytest.raises(ValueError, match='artefact'):
        activation._save(root, 'too_large', {'text': 'x' * (16 * 1048576)}, time.monotonic())
    assert not list(root.iterdir())
    with pytest.raises(ValueError, match='retained-byte'):
        activation._check(root, time.monotonic(), 32 * 1048576)
    with pytest.raises(ValueError, match='deadline'):
        activation._check(root, time.monotonic() - 601)


async def test_read_and_frame_references_are_only_to_current_declaration(tmp_path, original_code):
    _, panel, _, _ = await prepared(tmp_path, original_code)
    activate_panel(panel)
    before = read_panel_declaration(panel)
    saved = snapshot(activation_root(panel))
    assert read_panel_declaration(panel) == before
    assert before['collection_enabled'] is False
    assert snapshot(activation_root(panel)) == saved
