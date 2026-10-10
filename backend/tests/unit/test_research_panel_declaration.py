"""Panel declarations reserve complete role/target capacity without data reads or collection."""

from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import _PACKAGE_FILES, panel_declaration
from astrolabe.research_panel.panel_declaration import (
    MIB,
    PanelProtocol,
    declare_panel,
    read_panel_declaration,
    reservation,
)
from tests.unit.test_research_panel_input_read import rewrite, snapshot

COMMIT = 'a' * 40


def protocol(**changes):
    return PanelProtocol(**{
        'scheduled_slots': 2, 'triggered_slots': 1, 'controls_per_trigger': 2,
        'cycles': 2, 'target_attempts': 2, 'scheduled_per_stratum': 1,
        'triggered_per_stratum': 1, 'cadence_seconds': 300, 'max_origin_delay_seconds': 20,
        'max_origin_save_seconds': 5, 'horizon_seconds': 60, 'tolerance_seconds': 5,
        'max_frame_age_seconds': 3600, 'max_frame_interval_seconds': 600,
        'max_quote_age_seconds': 15, 'max_identity_age_seconds': 60,
        'source_response_bytes': 262144, 'source_run_retained_bytes': 32 * MIB, **changes,
    })


def paths(tmp_path):
    frame = tmp_path / 'fs2_capture_fixture'
    frame.mkdir(exist_ok=True)
    (frame / 'numerical.bin').write_bytes(b'must not be parsed by declaration')
    return frame, tmp_path / 'fs2_panel_fixture'


def declare(tmp_path, **changes):
    frame, root = paths(tmp_path)
    return declare_panel(frame, implementation_commit=COMMIT, output_root=root,
                          protocol=protocol(**changes))


def test_reserve_controls_outcomes_and_no_overlap_discount():
    result = reservation(protocol())
    assert result['market_slots'] == 5
    assert result['origin_slots'] == 10
    assert result['scheduled_origin_slots'] == 4
    assert result['triggered_origin_slots'] == 2
    assert result['control_origin_slots'] == 4
    assert result['target_attempt_slots'] == 20
    assert result['source_run_slots'] == 30
    assert result['source_request_slots'] == 70
    assert result['raw_byte_ceiling'] == 70 * 262144
    assert result['total_retained_bytes'] == (30 * (32 + 64) + 1024 + 16 + 1) * MIB
    assert result['required_free_bytes'] == result['total_retained_bytes'] + 2048 * MIB
    assert result['runtime_source_retention_guard_required'] is True
    assert result['overlap_discount_applied'] is False
    scheduled = reservation(protocol(triggered_slots=0))
    assert scheduled['control_origin_slots'] == scheduled['triggered_origin_slots'] == 0


@pytest.mark.parametrize('changes', [
    {'scheduled_slots': True}, {'triggered_slots': -1}, {'cycles': 0}, {'cycles': 25},
    {'target_attempts': 17}, {'source_response_bytes': MIB + 1},
    {'source_run_retained_bytes': MIB, 'source_response_bytes': MIB},
    {'max_origin_save_seconds': 60}, {'tolerance_seconds': 60},
    {'target_attempts': 7}, {'max_origin_delay_seconds': 300},
    {'max_frame_interval_seconds': 3601}, {'scheduled_per_stratum': 3},
    {'triggered_per_stratum': 2}, {'scheduled_slots': 256},
    {'cycles': 24, 'cadence_seconds': 86400}, {'max_quote_age_seconds': -1},
    {'max_identity_age_seconds': 604801}, {'controls_per_trigger': 0},
])
def test_invalid_counts_timing_and_impossible_raw_reservation_refused(changes):
    with pytest.raises(ValueError):
        protocol(**changes)


def test_excessive_aggregate_quota_refuses_before_output(tmp_path):
    p = protocol(scheduled_slots=64, triggered_slots=0, cycles=16,
                 source_run_retained_bytes=256 * MIB)
    with pytest.raises(ValueError, match='finite storage'):
        reservation(p)
    frame, root = paths(tmp_path)
    with pytest.raises(ValueError, match='finite storage'):
        declare_panel(frame, implementation_commit=COMMIT, output_root=root, protocol=p)
    assert not root.exists()


def test_declaration_is_causal_random_immutable_and_reads_no_frame_numbers(tmp_path):
    frame, root = paths(tmp_path)
    before = snapshot(frame)
    first = declare(tmp_path)
    facts, ack = _pair(root, 'panel_policy')
    assert facts['declared_at']['utc'] <= ack['durable_ack']['utc']
    assert facts['frame_implementation_commit'] == COMMIT
    assert (first['frame_verified'] is first['collection_enabled']
            is first['origin_admitted'] is False)
    assert facts['trigger_assessment_policy'].startswith('not_yet_frozen')
    assert 'unavailable' in facts['feature_families']['flow']
    assert read_panel_declaration(root) == first
    assert snapshot(frame) == before
    prior = snapshot(root)
    with pytest.raises(FileExistsError):
        declare(tmp_path)
    assert snapshot(root) == prior
    second = declare_panel(frame, implementation_commit=COMMIT,
                           output_root=tmp_path / 'fs2_panel_other', protocol=protocol())
    assert first['sampling_recipe']['seed'] != second['sampling_recipe']['seed']


@pytest.mark.parametrize('key,value', [
    ('origin_admitted', True), ('collection_enabled', True), ('frame_verified', True),
    ('accepted_panel', True), ('feature_store_admitted', True),
    ('trigger_assessment_policy', 'all controls measured negative'),
])
def test_rehashed_admission_or_scientific_claims_refused(tmp_path, key, value):
    declare(tmp_path)
    root = tmp_path / 'fs2_panel_fixture'
    rewrite(root, 'panel_policy', lambda p: p.update({key: value}))
    with pytest.raises(ValueError, match='build/policy/chronology'):
        read_panel_declaration(root)


@pytest.mark.parametrize('change', ['cost', 'seed', 'recipe', 'clock', 'source_policy'])
def test_rehashed_numerical_policy_seed_clock_or_source_changes_refused(tmp_path, change):
    declare(tmp_path)
    root = tmp_path / 'fs2_panel_fixture'
    def alter(p):
        if change == 'cost':
            p['reservation']['source_request_slots'] = 71
        elif change == 'seed':
            p['sampling_recipe']['seed'] = 'not-a-seed'
        elif change == 'recipe':
            p['sampling_recipe']['controls_per_trigger'] = 1
        elif change == 'clock':
            p['declared_at']['utc'] = '2099-01-01T00:00:00Z'
        else:
            p['source_policy']['sources'].append('arbitrary.source')
    rewrite(root, 'panel_policy', alter)
    with pytest.raises(ValueError):
        read_panel_declaration(root)


def test_free_space_includes_future_controls_and_targets_before_write(tmp_path, monkeypatch):
    frame, root = paths(tmp_path)
    usage = namedtuple('Usage', 'total used free')
    needed = reservation(protocol())['required_free_bytes']
    monkeypatch.setattr(panel_declaration.shutil, 'disk_usage',
                        lambda p: usage(needed, 1, needed - 1))
    with pytest.raises(ValueError, match='insufficient capacity'):
        declare(tmp_path)
    assert not root.exists()
    monkeypatch.setattr(panel_declaration.shutil, 'disk_usage', lambda p: usage(needed, 0, needed))
    assert declare(tmp_path)['reservation']['required_free_bytes'] == needed


def test_paths_mutable_commit_and_clock_payload_overrides_refused(tmp_path):
    frame, root = paths(tmp_path)
    for target in (frame, frame / 'fs2_panel_child', tmp_path):
        with pytest.raises(ValueError):
            declare_panel(frame, implementation_commit=COMMIT, output_root=target,
                          protocol=protocol())
    with pytest.raises(ValueError):
        declare_panel(frame, implementation_commit='HEAD', output_root=root, protocol=protocol())
    link = tmp_path / 'fs2_panel_link'
    link.symlink_to(frame, target_is_directory=True)
    with pytest.raises(ValueError):
        declare_panel(frame, implementation_commit=COMMIT, output_root=link, protocol=protocol())
    for extra in ({'seed': '0' * 64}, {'clock': None}, {'payload': {}},
                  {'provenance': 'prospective'}):
        with pytest.raises(TypeError):
            declare_panel(frame, implementation_commit=COMMIT, output_root=root,
                          protocol=protocol(), **extra)
    assert not root.exists()


def test_failed_ack_is_preserved_and_cannot_be_resumed(tmp_path, monkeypatch):
    persist = panel_declaration._persist
    def fail(root, name, payload):
        if name == 'panel_policy':
            (root / 'panel_policy.json').write_text('{}')
            raise OSError('synthetic failed durable acknowledgement')
        return persist(root, name, payload)
    monkeypatch.setattr(panel_declaration, '_persist', fail)
    with pytest.raises(OSError):
        declare(tmp_path)
    root = tmp_path / 'fs2_panel_fixture'
    assert (root / 'panel_failure_ack.json').exists()
    with pytest.raises(ValueError, match='complete isolated'):
        read_panel_declaration(root)
    with pytest.raises(FileExistsError):
        declare(tmp_path)


def test_changed_build_and_extra_journal_files_refused(tmp_path, monkeypatch):
    declare(tmp_path)
    root = tmp_path / 'fs2_panel_fixture'
    monkeypatch.setitem(_PACKAGE_FILES, 'panel_declaration.py', '0' * 64)
    with pytest.raises(ValueError, match='build changed'):
        read_panel_declaration(root)
    (root / 'unexpected').write_text('retained')
    with pytest.raises(ValueError, match='complete isolated'):
        read_panel_declaration(root)


def test_two_concurrent_declarations_have_one_winner_and_no_failure_marker(tmp_path):
    frame, root = paths(tmp_path)
    def attempt():
        try:
            return declare_panel(frame, implementation_commit=COMMIT,
                                 output_root=root, protocol=protocol())
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(result is not None for result in results) == 1
    assert not (root / 'panel_failure.json').exists()
    read_panel_declaration(root)


def test_subclasses_and_nonprotocol_declarations_do_not_override_policy(tmp_path):
    with pytest.raises(ValueError, match='immutable panel protocol'):
        reservation({})
    p = replace(protocol(), triggered_slots=0)
    assert reservation(p)['control_origin_slots'] == 0
