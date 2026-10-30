"""Original-code recovery preserves endpoint and source chronology exactly."""

import pytest

from astrolabe.research_panel.original_reader import read_original_window_reconciliation
from tests.unit.test_research_panel_bound_window import output as bound_output
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_window_reconciliation import output, prepare, record

original_code = _original_code


async def test_original_endpoint_report_and_all_transitive_dependencies(tmp_path, original_code):
    deps = await prepare(tmp_path)
    report = record(tmp_path, deps[-1])
    root = output(tmp_path)
    before = tuple(snapshot(p) for p in (*deps, bound_output(tmp_path), root))
    result = read_original_window_reconciliation(root, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_window_reconciliation_read_test')
    assert result['report'] == report
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert not result['read_receipt']['observation_clocks_changed']
    for parent in (*deps, root, bound_output(tmp_path)):
        with pytest.raises(ValueError, match='separate'):
            read_original_window_reconciliation(root, implementation_commit=original_code[1],
                repository=original_code[0],
                output_root=parent / 'fs2_window_reconciliation_read_nested')
    assert before == tuple(snapshot(p) for p in (*deps, bound_output(tmp_path), root))


async def test_original_decoder_refuses_mutated_post_receipt(tmp_path, original_code):
    deps = await prepare(tmp_path)
    record(tmp_path, deps[-1])
    next(deps[2].glob('*/raw.bin')).write_bytes(b'bad')
    before = tuple(snapshot(p) for p in (*deps, bound_output(tmp_path), output(tmp_path)))
    target = tmp_path / 'fs2_window_reconciliation_read_failed'
    with pytest.raises(ValueError, match='original-build verification refused'):
        read_original_window_reconciliation(output(tmp_path),
            implementation_commit=original_code[1], repository=original_code[0], output_root=target)
    assert before == tuple(snapshot(p) for p in (*deps, bound_output(tmp_path), output(tmp_path)))
    assert (target / 'read_failure_ack.json').exists()
