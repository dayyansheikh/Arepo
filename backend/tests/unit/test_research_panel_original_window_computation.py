"""Original-code coverage computation recovery cannot promote or restamp evidence."""

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.original_reader import read_original_window_computation
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_window_computation import output, record, source

original_code = _original_code


async def test_original_coverage_facts_summary_and_dependency_paths(tmp_path, original_code):
    root = await source(tmp_path)
    summary = record(root, tmp_path)
    target = output(tmp_path)
    facts, _ = _pair(target, 'window_facts')
    before = (snapshot(root), snapshot(target))
    result = read_original_window_computation(target, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_window_computation_read_test')
    assert result['report'] == {'facts': facts, 'summary': summary}
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert not result['read_receipt']['observation_clocks_changed']
    assert before == (snapshot(root), snapshot(target))
    for parent in (root, target):
        with pytest.raises(ValueError, match='separate'):
            read_original_window_computation(target, implementation_commit=original_code[1],
                repository=original_code[0],
                output_root=parent / 'fs2_window_computation_read_nested')


@pytest.mark.parametrize('change', ['raw', 'projection', 'clock'])
async def test_original_decoder_rejects_altered_source_or_resealed_calculation(
        tmp_path, original_code, change):
    root = await source(tmp_path)
    record(root, tmp_path)
    target = output(tmp_path)
    if change == 'raw':
        (root / 'event_000004.bin').write_bytes(b'bad')
    elif change == 'projection':
        rewrite(target, 'window_facts', lambda p: p['projection'].update(uncovered_duration_ns='0'))
    else:
        policy, _ = _pair(target, 'window_policy')
        rewrite(target, 'window_facts', lambda p: p.update(computed_at=policy['declared_at']))
    before = (snapshot(root), snapshot(target))
    with pytest.raises(ValueError, match='original-build verification refused'):
        read_original_window_computation(target, implementation_commit=original_code[1],
            repository=original_code[0],
            output_root=tmp_path / 'fs2_window_computation_read_failed')
    assert before == (snapshot(root), snapshot(target))
    assert (tmp_path / 'fs2_window_computation_read_failed' / 'read_failure_ack.json').exists()
