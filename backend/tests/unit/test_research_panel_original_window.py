"""Original-build raw-window recovery preserves received bytes and all clocks."""

import pytest

from astrolabe.research_panel.original_reader import read_original_window
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_window_capture import capture, output

original_code = _original_code


async def test_original_raw_window_read_and_nested_output_refusal(tmp_path, original_code):
    report = await capture(tmp_path, ((0, 'PONG'), (0, b'\x00bad')))
    root = output(tmp_path)
    before = snapshot(root)
    result = read_original_window(root, implementation_commit=original_code[1],
        repository=original_code[0], output_root=tmp_path / 'fs2_window_read_test')
    assert result['report'] == report
    assert not result['read_receipt']['observation_clocks_changed']
    assert result['read_receipt']['original_provenance_class'] == 'synthetic'
    assert snapshot(root) == before
    with pytest.raises(ValueError, match='separate'):
        read_original_window(root, implementation_commit=original_code[1],
            repository=original_code[0], output_root=root / 'fs2_window_read_nested')


async def test_original_window_corruption_retains_failed_read(tmp_path, original_code):
    await capture(tmp_path, ((0, 'raw'),))
    root = output(tmp_path)
    (root / 'event_000004.bin').write_bytes(b'bad')
    before = snapshot(root)
    target = tmp_path / 'fs2_window_read_test'
    with pytest.raises(ValueError, match='original-build verification refused'):
        read_original_window(root, implementation_commit=original_code[1],
                             repository=original_code[0], output_root=target)
    assert (target / 'read_failure_ack.json').exists()
    assert snapshot(root) == before
