"""Original runtime recovery preserves scheduling, targets and actual availability."""

import pytest

from astrolabe.research_panel.original_reader import read_original_runtime
from astrolabe.research_panel.runtime import exercise_panel, run_root
from tests.unit.test_research_panel_original_reader import git
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_runtime import setup, transport
from tests.unit.test_research_panel_selection import amend, snapshot

original_code = _original_code


def read(panel, code, output):
    return read_original_runtime(run_root(panel), implementation_commit=code[1],
                                 repository=code[0], output_root=output)


async def test_original_runtime_exact_recovery_and_all_dependency_paths_protected(
        tmp_path, original_code):
    panel = await setup(tmp_path, original_code)
    report = await exercise_panel(panel, transport=transport([]))
    roots = [panel, run_root(panel), tmp_path / 'fs2_activation_runtime',
             tmp_path / 'fs2_selection_panel_runtime']
    from pathlib import Path

    from astrolabe.feature_store.source_run import _pair
    policy, _ = _pair(panel, 'panel_policy')
    roots.append(Path(policy['frame_root']))
    before = [snapshot(r) for r in roots]
    result = read(panel, original_code, tmp_path / 'fs2_runtime_read_exact')
    assert result['report'] == report
    assert result['read_receipt']['original_state'] == 'verified_synthetic_runtime'
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert result['read_receipt']['origin_admitted'] is False
    assert result['read_receipt']['observation_clocks_changed'] is False
    assert report['runtime_available_at']['utc'] <= result['read_available_at']['utc']
    assert before == [snapshot(r) for r in roots]
    for parent in roots:
        target = parent / 'fs2_runtime_read_nested'
        with pytest.raises(ValueError, match='separate'):
            read(panel, original_code, target)
        assert not target.exists()
    assert not git(original_code[0], 'status', '--porcelain')
    with pytest.raises(FileExistsError):
        read(panel, original_code, tmp_path / 'fs2_runtime_read_exact')


@pytest.mark.parametrize('change', ['raw', 'events', 'outcome'])
async def test_original_runtime_rejects_changed_evidence_without_repair(
        tmp_path, original_code, change):
    panel = await setup(tmp_path, original_code)
    await exercise_panel(panel, transport=transport([]))
    root = run_root(panel)
    if change == 'raw':
        next(root.glob('origins/*/fs2_capture_origin/*/raw.bin')).write_bytes(b'changed fixture')
    elif change == 'events':
        amend(root, 'runtime_report', lambda p: p['events'].reverse())
    else:
        amend(root, 'runtime_report', lambda p: p['outcomes'][0].update(midpoint_change='0.9'))
    before = snapshot(root)
    output = tmp_path / 'fs2_runtime_read_refused'
    with pytest.raises(ValueError, match='original-build verification refused'):
        read(panel, original_code, output)
    assert (output / 'read_failure_ack.json').exists()
    assert snapshot(root) == before
