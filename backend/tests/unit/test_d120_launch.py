"""D120 launch wrapper precondition helpers (no launch, no git, no subprocess)."""

import importlib.util
import re
import types
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / "scripts" / "d120_launch.py"
spec = importlib.util.spec_from_file_location("d120_launch", PATH)
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)
Err = launch.PreconditionError


def record(rows, extra=""):
    lines = ["# D120 freeze record", "", "| Artefact | sha256 |", "|---|---|"]
    lines += [f"| `{path}` | `{digest}` |" for path, digest in rows.items()]
    return "\n".join(lines) + "\n" + extra


def full(digest="a" * 64):
    return {path: digest for path in sorted(launch.REQUIRED_FROZEN)}


def test_parse_reads_every_required_artefact_and_ignores_non_path_rows():
    text = record(full()).replace(
        "`backend/scripts/evaluate_d120.py`", "`backend/scripts/evaluate_d120.py` (CLI)")
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


def test_required_frozen_pins_the_new_code_and_tests():
    assert launch.REQUIRED_FROZEN == {
        launch.PROTOCOL,
        "backend/astrolabe/research_panel/d120_evaluator.py",
        "backend/astrolabe/research_panel/d116_evaluator.py",
        "backend/astrolabe/research_panel/pairing.py",
        "backend/astrolabe/research_panel/pairing_declaration.py",
        "backend/astrolabe/research_panel/pairing_selection.py",
        "backend/astrolabe/research_panel/pairing_worker.py",
        "backend/astrolabe/research_panel/panel_declaration.py",
        "backend/astrolabe/research_panel/panel_selection.py",
        "backend/scripts/evaluate_d120.py",
        "backend/scripts/d120_launch.py",
        "backend/tests/unit/test_research_panel_d120_pairing.py",
        "backend/tests/unit/test_research_panel_pairing.py",
        "backend/tests/unit/test_d120_launch.py",
    }
    for rel in launch.REQUIRED_FROZEN:
        assert (launch.REPO / rel).is_file(), rel
    assert launch.FROZEN_CODE_PATHS == (
        "backend/astrolabe", "backend/scripts/d120_launch.py", "backend/scripts/evaluate_d120.py")


def test_freeze_commit_is_read_once_and_fails_closed(tmp_path):
    commit = "0123456789abcdef0123456789abcdef01234567"
    text = record(full(), f"\nFreeze commit: `{commit}`\n")
    assert launch.parse_freeze_commit(text) == commit
    for bad in ("", "Freeze commit: `<fill at freeze>`", f"Freeze commit: `{commit.upper()}`",
                f"Freeze commit: `{commit}`\nFreeze commit: `{commit}`"):
        with pytest.raises(Err, match="exactly one freeze commit"):
            launch.parse_freeze_commit(record(full(), bad))
    (tmp_path / "docs" / "implementation").mkdir(parents=True)
    (tmp_path / launch.FREEZE_RECORD).write_text(text)
    assert launch.load_frozen(tmp_path) == (full(), commit)


def test_code_unchanged_since_freeze_uses_git_diff_quiet():
    calls = []

    def fake(rc):
        def run_git(*args):
            calls.append(args)
            return types.SimpleNamespace(returncode=rc)
        return run_git

    launch.check_code_unchanged("f" * 40, fake(0))
    assert calls[-1] == ("diff", "--quiet", "f" * 40, "HEAD", "--", "backend/astrolabe",
                         "backend/scripts/d120_launch.py", "backend/scripts/evaluate_d120.py")
    for rc in (1, 128):  # changed code, or an unknown commit: both refuse
        with pytest.raises(Err, match="frozen code differs"):
            launch.check_code_unchanged("f" * 40, fake(rc))


@pytest.mark.parametrize("hour,minute,refused", [
    (10, 45, True), (10, 46, False), (11, 0, False), (11, 49, False), (11, 50, True),
    (12, 10, True), (12, 18, True), (0, 20, True), (23, 30, False), (22, 50, False)])
def test_collector_window_refusal(hour, minute, refused):
    now = datetime(2026, 10, 11, hour, minute, 30, tzinfo=UTC)
    if refused:
        with pytest.raises(Err, match="collector window"):
            launch.check_collector_window(now)
    else:
        launch.check_collector_window(now)
    # Judged in UTC whatever the input zone.
    local = now.astimezone(timezone(timedelta(hours=1)))
    if refused:
        with pytest.raises(Err):
            launch.check_collector_window(local)
    else:
        launch.check_collector_window(local)


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
    (tmp_path / "fs2_d120_pairing_1_evaluation.json").write_text("{}")
    with pytest.raises(Err, match="wrapper file exists"):
        launch.check_absent(tmp_path)
    (tmp_path / "fs2_runtime_d120_pairing_1").mkdir()
    with pytest.raises(Err, match="root exists"):
        launch.check_absent(tmp_path)
    assert launch.extract_script("x\n```python\nprint(1)\n```\n") == "print(1)\n"
    with pytest.raises(Err, match="exactly one"):
        launch.extract_script("```python\na\n```\n```python\nb\n```\n")
    url = launch.database_url(Path("/s"))
    assert url == "sqlite+aiosqlite:////s/d120_isolated.sqlite"


def test_protocol_has_exactly_one_d120_script_block():
    text = (launch.REPO / launch.PROTOCOL).read_text()
    script = launch.extract_script(text)
    assert "fs2_panel_d120_pairing_1" in script
    assert "run_pairing_window_pilot" in script
    assert "runtime_concurrency=8" in script
    assert re.search(r"PairingDesign\(strata=6,screen_per_stratum=12", script)
    assert "frame_abort" in script and "frame_rerun" in script
    compile(script, "d120_protocol_script", "exec")  # the frozen block is valid Python


def test_reservation_matches_the_pairing_allocation():
    from astrolabe.research_panel.pairing import PairingDesign
    from astrolabe.research_panel.pairing_declaration import PairingPanelProtocol, reservation
    from astrolabe.research_panel.pairing_worker import allocation

    p = PairingPanelProtocol(
        screened_slots=72, origin_slots=12, cycles=1, target_attempts=1, cadence_seconds=120,
        max_origin_delay_seconds=60, max_origin_save_seconds=5, horizon_seconds=60,
        tolerance_seconds=15, max_frame_age_seconds=3600, max_frame_interval_seconds=600,
        max_quote_age_seconds=60, max_identity_age_seconds=180, source_response_bytes=65536,
        source_run_retained_bytes=1048576)
    reserved = allocation({"reservation": reservation(p, PairingDesign(6, 12),
                                                      storage_profile="compact-v1")})
    assert launch.RESERVATION == 7 * 1024**3 + reserved["required_free_bytes"] + 34 * 1048576
