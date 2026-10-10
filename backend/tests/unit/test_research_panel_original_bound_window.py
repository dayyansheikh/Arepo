"""Original bound-window recovery protects all transitive source dependencies."""

import pytest

from astrolabe.research_panel.original_reader import read_original_bound_window
from tests.unit.test_research_panel_bound_window import capture, output, pre
from tests.unit.test_research_panel_input_read import rewrite, snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code

original_code = _original_code


async def test_original_binding_report_and_all_dependency_paths(tmp_path, original_code):
    source, computation = await pre(tmp_path)
    report = await capture(computation, tmp_path)
    root = output(tmp_path)
    before = tuple(snapshot(p) for p in (source, computation, root))
    result = read_original_bound_window(root, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_bound_window_read_test')
    assert result['report'] == report
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert not result['read_receipt']['observation_clocks_changed']
    for parent in (source, computation, root):
        with pytest.raises(ValueError, match='separate'):
            read_original_bound_window(root, implementation_commit=original_code[1],
                repository=original_code[0], output_root=parent / 'fs2_bound_window_read_nested')
    assert before == tuple(snapshot(p) for p in (source, computation, root))


@pytest.mark.parametrize('change', ['raw', 'binding', 'child'])
async def test_original_decoder_refuses_changed_dependencies(tmp_path, original_code, change):
    source, computation = await pre(tmp_path)
    await capture(computation, tmp_path)
    root = output(tmp_path)
    if change == 'raw':
        next(source.glob('*/raw.bin')).write_bytes(b'bad')
    elif change == 'binding':
        rewrite(root, 'bound_window_binding', lambda p: p['identity'].update(outcome_label='No'))
    else:
        (root / 'fs2_window_capture' / 'event_000004.bin').write_bytes(b'bad')
    before = tuple(snapshot(p) for p in (source, computation, root))
    with pytest.raises(ValueError, match='original-build verification refused'):
        read_original_bound_window(root, implementation_commit=original_code[1],
            repository=original_code[0], output_root=tmp_path / 'fs2_bound_window_read_failed')
    assert before == tuple(snapshot(p) for p in (source, computation, root))
    assert (tmp_path / 'fs2_bound_window_read_failed' / 'read_failure_ack.json').exists()
