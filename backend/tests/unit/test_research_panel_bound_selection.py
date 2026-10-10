"""Declaration-bound selection uses real original-code fixture reads, never live sources."""

import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel import selection
from astrolabe.research_panel.panel_declaration import declare_panel
from astrolabe.research_panel.panel_selection import (
    create_panel_selection,
    freshness,
    selection_root,
)
from astrolabe.research_panel.selection import read_selection
from tests.unit.test_research_panel_declaration import protocol
from tests.unit.test_research_panel_frame import market
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_selection import amend, frame, snapshot

original_code = _original_code


async def setup(tmp_path, original_code, rows=None, **changes):
    source = await frame(tmp_path, rows)
    panel = tmp_path / 'fs2_panel_bound'
    declare_panel(source, implementation_commit=original_code[1], output_root=panel,
                  protocol=protocol(cycles=1, target_attempts=1, **changes))
    return source, panel, selection_root(panel)


async def test_bound_seed_complete_inventory_assessments_and_exact_recovery(
        tmp_path, original_code):
    source, panel, root = await setup(tmp_path, original_code, [
        market(1), market(1), market(2), market(3), market(4, clobTokenIds=None)])
    before = snapshot(source), snapshot(panel)
    result = create_panel_selection(panel, repository=original_code[0])
    policy, ack = _pair(root, 'selection_policy')
    declaration, panel_ack = _pair(panel, 'panel_policy')
    read, _ = _pair(root / selection.READ_FOLDER, 'read_policy')
    assert panel_ack['durable_ack']['utc'] <= policy['declared_at']['utc']
    assert ack['durable_ack']['utc'] <= read['metadata_read_started_at']['utc']
    assert result['plan']['protocol']['seed'] == declaration['sampling_recipe']['seed']
    assert result['counts']['source_rows'] == 5
    assert result['counts']['duplicate_market_rows'] == 1
    assert result['counts']['sampling_members'] == 3
    assert result['counts']['excluded:identity_unresolved'] == 1
    plan = result['plan']
    assert plan['schema_version'] == 'fs2-panel-selection-plan-v1'
    encoded = plan['assessment_inventory_encoding']
    assert encoded['member_count'] == 3 and encoded['effective_state'] == 'not_assessed'
    assert 'assessment_inventory' not in plan
    assignment = plan['assignments'][0]
    assert assignment['assessment_state'] == 'not_assessed'
    assert assignment['assessment_evidence_id'] is None
    assert assignment['inclusion_probability']['denominator'] == '3'
    assert all(s['control_pool'] == s['triggered_pool'] == 0 for s in plan['strata'])
    assert result['state'] == 'fresh_selection_sealed'
    assert result['provenance_class'] == 'synthetic'
    assert not any(result[k] for k in ('origin_admitted', 'accepted_panel',
                                      'collection_enabled', 'feature_store_admitted'))
    saved = snapshot(root)
    assert read_selection(root) == result
    assert before == (snapshot(source), snapshot(panel)) and snapshot(root) == saved
    with pytest.raises(FileExistsError):
        create_panel_selection(panel, repository=original_code[0])
    assert snapshot(root) == saved


def clock(seconds):
    return {'utc': (datetime(2026, 9, 23, tzinfo=UTC) + timedelta(seconds=seconds)).isoformat(),
            'monotonic_ns': str(int(seconds * 1_000_000_000)), 'clock_session_id': 'fixture'}


@pytest.mark.parametrize('start,end,available,point,error', [
    (0, 601, 602, 603, 'interval'), (0, 5, 6, 3601, 'stale'),
    (10, 5, 6, 7, 'unordered'), (0, 5, 10, 9, 'future'),
])
def test_interval_original_age_and_future_gates(start, end, available, point, error):
    original = {'interval_start': clock(start), 'interval_end': clock(end),
                'frame_available_at': clock(available)}
    with pytest.raises(ValueError, match=error):
        freshness({'panel_protocol': asdict(protocol())}, original, clock(point))


def test_freshness_exact_inclusive_boundaries():
    original = {'interval_start': clock(0), 'interval_end': clock(600),
                'frame_available_at': clock(601)}
    freshness({'panel_protocol': asdict(protocol())}, original, clock(3600))
    with pytest.raises(ValueError, match='stale'):
        freshness({'panel_protocol': asdict(protocol())}, original, clock(3600.000001))


async def test_freshness_is_checked_at_cutoff_and_durable_ack(tmp_path, original_code, monkeypatch):
    _, panel, root = await setup(tmp_path, original_code)
    calls = []
    actual = selection._clock
    # Imported clock alias only: do not replace the protected source implementation.
    def future_cutoff():
        value = actual()
        value['utc'] = (datetime.fromisoformat(value['utc'].replace('Z', '+00:00'))
                        + timedelta(days=1)).isoformat()
        value['monotonic_ns'] = str(int(value['monotonic_ns']) + 86400 * 10**9)
        calls.append(value)
        return value
    monkeypatch.setattr(selection, '_clock', future_cutoff)
    with pytest.raises(ValueError, match='stale'):
        create_panel_selection(panel, repository=original_code[0])
    assert calls and (root / 'selection_failure_ack.json').exists()
    assert not (root / 'selection_plan.json').exists()


async def test_ack_expiry_retains_failed_seal(tmp_path, original_code, monkeypatch):
    _, panel, root = await setup(tmp_path, original_code,
                                 max_frame_age_seconds=10, max_frame_interval_seconds=1)
    persist = selection._persist
    def expired(folder, name, payload):
        if name == 'selection_report':
            time.sleep(10.1)  # actual durability delay; never invent an acknowledgement clock
        persist(folder, name, payload)
    monkeypatch.setattr(selection, '_persist', expired)
    with pytest.raises(ValueError, match='stale'):
        create_panel_selection(panel, repository=original_code[0])
    assert (root / 'selection_report_ack.json').exists()
    assert (root / 'selection_failure_ack.json').exists()
    with pytest.raises(ValueError):
        read_selection(root)


async def test_recovery_does_not_reage_or_check_current_disk(tmp_path, original_code, monkeypatch):
    _, panel, root = await setup(tmp_path, original_code)
    expected = create_panel_selection(panel, repository=original_code[0])
    monkeypatch.setattr(selection, '_clock', lambda: (_ for _ in ()).throw(AssertionError()))
    monkeypatch.setattr(shutil, 'disk_usage', lambda p: shutil._ntuple_diskusage(1, 1, 0))
    assert read_selection(root) == expected


async def test_total_and_scheduled_role_limits_never_truncate(tmp_path, original_code):
    _, panel, root = await setup(tmp_path, original_code, [market(1), market(2, category='sports')],
                                 scheduled_slots=1)
    with pytest.raises(ValueError, match='scheduled slot ceiling; never truncate'):
        create_panel_selection(panel, repository=original_code[0])
    assert (root / 'inventory_ack.json').exists()
    assert not (root / 'selection_plan.json').exists()


async def test_full_panel_capacity_rechecked_before_frame_read(
        tmp_path, original_code, monkeypatch):
    _, panel, root = await setup(tmp_path, original_code)
    policy, _ = _pair(panel, 'panel_policy')
    needed = policy['reservation']['required_free_bytes']
    monkeypatch.setattr(shutil, 'disk_usage',
                        lambda p: shutil._ntuple_diskusage(needed, 1, needed - 1))
    with pytest.raises(ValueError, match='full panel/control/target capacity'):
        create_panel_selection(panel, repository=original_code[0])
    assert not root.exists()


@pytest.mark.parametrize('change', ['seed', 'declaration', 'assessment', 'limit', 'admission',
                                  'weight', 'encoding', 'extra', 'source'])
async def test_rehashed_or_external_changes_refused(tmp_path, original_code, change):
    source, panel, root = await setup(tmp_path, original_code)
    create_panel_selection(panel, repository=original_code[0])
    if change == 'seed':
        amend(root, 'selection_policy', lambda p: p['sampling_protocol'].update(seed='0' * 64))
    elif change == 'declaration':
        amend(panel, 'panel_policy', lambda p: p['sampling_recipe'].update(seed='0' * 64))
    elif change == 'assessment':
        amend(root, 'selection_policy', lambda p: p['assessment_policy'].update(
            state='untriggered'))
    elif change == 'limit':
        amend(root, 'selection_policy', lambda p: p['panel_protocol'].update(
            max_frame_age_seconds=604800))
    elif change == 'admission':
        amend(root, 'selection_report', lambda p: p.update(origin_admitted=True))
    elif change in {'weight', 'encoding'}:
        def alter(p):
            if change == 'weight':
                p['assignments'][0]['inclusion_probability']['denominator'] = '100'
            else:
                p['assessment_inventory_encoding']['effective_state'] = 'untriggered'
        hash_ = amend(root, 'selection_plan', alter)
        amend(root, 'selection_report', lambda p: p.update(plan_hash=hash_))
    elif change == 'extra':
        (root / 'unrecorded.json').write_text('{}')
    else:
        next(source.glob('*/raw.bin')).write_bytes(b'changed')
    before = snapshot(root)
    with pytest.raises(ValueError):
        read_selection(root)
    assert snapshot(root) == before


async def test_no_payload_seed_clock_path_or_assessment_overrides(tmp_path, original_code):
    _, panel, root = await setup(tmp_path, original_code)
    for kwargs in ({'seed': '0' * 64}, {'clock': None}, {'output_root': root},
                   {'trigger_assessments': []}, {'provenance': 'prospective'}):
        with pytest.raises(TypeError):
            create_panel_selection(panel, repository=original_code[0], **kwargs)
    assert not root.exists()


async def test_concurrent_selection_has_one_owner(tmp_path, original_code):
    _, panel, root = await setup(tmp_path, original_code)
    def attempt():
        try:
            return create_panel_selection(panel, repository=original_code[0])
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sum(r is not None for r in results) == 1
    assert not (root / 'selection_failure.json').exists()
    read_selection(root)


async def test_wrong_original_build_keeps_failed_attempt(tmp_path, original_code):
    source, _, _ = await setup(tmp_path, original_code)
    panel = tmp_path / 'fs2_panel_wrong_commit'
    declare_panel(source, implementation_commit='f' * 40, output_root=panel,
                  protocol=protocol(cycles=1, target_attempts=1))
    with pytest.raises(ValueError):
        create_panel_selection(panel, repository=original_code[0])
    assert (selection_root(panel) / 'selection_failure_ack.json').exists()


@pytest.mark.parametrize('kind', ['extra_projection', 'extra_read', 'symlink'])
async def test_nested_evidence_closure_and_links_refused(tmp_path, original_code, kind):
    _, panel, root = await setup(tmp_path, original_code)
    create_panel_selection(panel, repository=original_code[0])
    folder = next((root / 'pages').iterdir())
    if kind == 'extra_projection':
        (folder / 'unexpected').write_text('{}')
    elif kind == 'extra_read':
        (root / selection.READ_FOLDER / 'unexpected').write_text('{}')
    else:
        path = folder / 'projection.json'
        saved = tmp_path / 'saved_projection.json'
        path.rename(saved)  # disposable fixture only; production journals are never moved
        path.symlink_to(saved)
    with pytest.raises(ValueError, match='file closure'):
        read_selection(root)
