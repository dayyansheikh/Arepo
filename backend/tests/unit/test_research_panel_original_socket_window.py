"""Original-code socket recovery never opens a new connection or reassigns clocks."""

import pytest

from astrolabe.research_panel.original_reader import read_original_socket_window
from tests.unit.test_research_panel_bound_window import pre
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_socket_window import capture, output

original_code = _original_code


async def test_original_wire_report_and_all_dependency_paths(tmp_path, original_code):
    source, computation = await pre(tmp_path)
    report = await capture(computation, tmp_path)
    root = output(tmp_path)
    before = tuple(snapshot(p) for p in (source, computation, root))
    result = read_original_socket_window(root, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_socket_window_read_test')
    assert result['report'] == report
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert not result['read_receipt']['observation_clocks_changed']
    for parent in (source, computation, root):
        with pytest.raises(ValueError, match='separate'):
            read_original_socket_window(root, implementation_commit=original_code[1],
                repository=original_code[0], output_root=parent / 'fs2_socket_window_read_bad')
    assert before == tuple(snapshot(p) for p in (source, computation, root))


async def test_original_decoder_refuses_mutated_raw(tmp_path, original_code):
    _, computation = await pre(tmp_path)
    await capture(computation, tmp_path)
    (output(tmp_path) / 'event_000005.bin').write_bytes(b'bad')
    with pytest.raises(ValueError, match='original-build verification refused'):
        read_original_socket_window(output(tmp_path), implementation_commit=original_code[1],
            repository=original_code[0], output_root=tmp_path / 'fs2_socket_window_read_failed')
