"""Original socket-analysis recovery retains full diagnostics and all dependency clocks."""

import pytest

from astrolabe.feature_store.source_run import _pair
from astrolabe.research_panel.original_reader import read_original_socket_analysis
from tests.unit.test_research_panel_input_read import snapshot
from tests.unit.test_research_panel_original_reader import original_code as _original_code
from tests.unit.test_research_panel_socket_analysis import output, record, setup
from tests.unit.test_research_panel_socket_window import output as socket_output

original_code = _original_code


async def test_original_analysis_values_clocks_and_dependency_paths(tmp_path, original_code):
    deps = await setup(tmp_path)
    report = record(tmp_path, deps[-1])
    facts, _ = _pair(output(tmp_path), "socket_analysis_facts")
    before = tuple(snapshot(p) for p in (*deps, socket_output(tmp_path), output(tmp_path)))
    result = read_original_socket_analysis(
        output(tmp_path),
        implementation_commit=original_code[1],
        repository=original_code[0],
        output_root=tmp_path / "fs2_socket_analysis_read_test",
    )
    assert result["report"] == {"summary": report, "facts": facts}
    assert not result["read_receipt"]["observation_clocks_changed"]
    for parent in (*deps, socket_output(tmp_path), output(tmp_path)):
        with pytest.raises(ValueError, match="separate"):
            read_original_socket_analysis(
                output(tmp_path),
                implementation_commit=original_code[1],
                repository=original_code[0],
                output_root=parent / "fs2_socket_analysis_read_nested",
            )
    assert before == tuple(snapshot(p) for p in (*deps, socket_output(tmp_path), output(tmp_path)))
