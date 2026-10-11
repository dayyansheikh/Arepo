"""D118 launch wrapper precondition helpers (no launch, no git, no subprocess)."""

import importlib.util
import re
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / "scripts" / "d118_launch.py"
spec = importlib.util.spec_from_file_location("d118_launch", PATH)
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)
Err = launch.PreconditionError


def record(rows, extra=""):
    lines = ["# D118 freeze record", "", "| Artefact | sha256 |", "|---|---|"]
    lines += [f"| `{path}` | `{digest}` |" for path, digest in rows.items()]
    return "\n".join(lines) + "\n" + extra


def full(digest="a" * 64):
    return {path: digest for path in sorted(launch.REQUIRED_FROZEN)}


def test_parse_reads_every_required_artefact_and_ignores_non_path_rows():
    text = record(full()).replace(
        "`backend/scripts/evaluate_d118.py`", "`backend/scripts/evaluate_d118.py` (CLI)")
    text += "| Classification table (`TABLE_SHA256`) | `" + "b" * 64 + "` |\n"
    assert launch.parse_freeze_record(text) == full()


@pytest.mark.parametrize("digest", ["", "<fill at freeze>", "A" * 64, "a" * 63])
def test_unfilled_or_invalid_hash_fails_closed(digest):
    rows = full()
    rows[launch.PROTOCOL] = digest
    with pytest.raises(Err, match="unfilled or invalid hash"):
        launch.parse_freeze_record(record(rows))


def test_missing_extra_and_duplicate_rows_fail_closed():
    rows = full()
    rows.pop(launch.PROTOCOL)
    with pytest.raises(Err, match="missing"):
        launch.parse_freeze_record(record(rows))
    with pytest.raises(Err, match="extra"):
        launch.parse_freeze_record(record({**full(), "backend/other.py": "c" * 64}))
    text = record(full()) + f"| `{launch.PROTOCOL}` | `{'d' * 64}` |\n"
    with pytest.raises(Err, match="duplicate"):
        launch.parse_freeze_record(text)
    with pytest.raises(Err, match="artefacts differ"):
        launch.parse_freeze_record("no table here")


def test_absent_record_fails_closed(tmp_path):
    with pytest.raises(Err, match="not frozen"):
        launch.load_frozen(tmp_path)


def test_verify_frozen_matches_and_detects_mismatch(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "f.py").write_bytes(b"x")
    good = {"a/f.py": launch.sha(tmp_path / "a" / "f.py")}
    launch.verify_frozen(good, tmp_path)
    with pytest.raises(Err, match="MISMATCH"):
        launch.verify_frozen({"a/f.py": "0" * 64}, tmp_path)
    with pytest.raises(Err, match="missing"):
        launch.verify_frozen({"a/g.py": "0" * 64}, tmp_path)


def test_collector_detection_excludes_own_processes():
    seen = {"sample_trades": "123 python scripts/sample_trades.py --n 2000\n",
            "run_forecast": "999 python wrapper run_forecast\n"}
    found = launch.running_collectors(pgrep=lambda name: seen.get(name, ""), own_pids=(999,))
    assert found == {"sample_trades": ["123 python scripts/sample_trades.py --n 2000"]}
    assert launch.running_collectors(pgrep=lambda name: "", own_pids=(1,)) == {}
    assert set(launch.COLLECTORS) == {
        "collect_universe_snapshot", "sweep_books", "sample_trades", "run_forecast"}


def test_disk_absent_roots_script_and_database_url(tmp_path):
    launch.check_disk(launch.RESERVATION + launch.MARGIN)
    with pytest.raises(Err, match="insufficient"):
        launch.check_disk(launch.RESERVATION + launch.MARGIN - 1)
    launch.check_absent(tmp_path)
    (tmp_path / "fs2_d118_control_pairing_1_evaluation.json").write_text("{}")
    with pytest.raises(Err, match="wrapper file exists"):
        launch.check_absent(tmp_path)
    (tmp_path / "fs2_runtime_d118_control_pairing_1").mkdir()
    with pytest.raises(Err, match="root exists"):
        launch.check_absent(tmp_path)
    assert launch.extract_script("x\n```python\nprint(1)\n```\n") == "print(1)\n"
    with pytest.raises(Err, match="exactly one"):
        launch.extract_script("```python\na\n```\n```python\nb\n```\n")
    url = launch.database_url(Path("/s"))
    assert url == "sqlite+aiosqlite:////s/d118_isolated.sqlite"


def test_protocol_has_exactly_one_d118_script_block():
    text = (launch.REPO / launch.PROTOCOL).read_text()
    script = launch.extract_script(text)
    assert "fs2_panel_d118_control_pairing_1" in script
    assert "population_policy=LIQUIDITY_POPULATION" in script
    assert "runtime_concurrency=8" in script
    assert re.search(r"scheduled_per_stratum=3,triggered_per_stratum=3", script)
