"""scripts/oracle/union_jsonl.py: append-only union of trials.jsonl across collection hosts."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "oracle" / "union_jsonl.py"


def run(*args) -> str:
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_in_place_appends_only_missing_lines(tmp_path):
    base, other = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    base.write_text('{"a":1}\n{"b":2}\n')
    other.write_text('{"b":2}\n{"c":3}\n{"a":1}\n{"d":4}\n')
    ino = base.stat().st_ino
    assert run(base, other) == "2"
    assert base.read_text() == '{"a":1}\n{"b":2}\n{"c":3}\n{"d":4}\n'
    assert base.stat().st_ino == ino  # appended, not replaced
    assert run(base, other) == "0"  # idempotent


def test_missing_trailing_newline_and_missing_other(tmp_path):
    base = tmp_path / "a.jsonl"
    base.write_text('{"a":1}')
    other = tmp_path / "b.jsonl"
    other.write_text('{"z":0}\n')
    assert run(base, other) == "1"
    assert base.read_text() == '{"a":1}\n{"z":0}\n'
    assert run(base, tmp_path / "absent.jsonl") == "0"


def test_out_path_leaves_inputs_untouched(tmp_path):
    a, b, out = tmp_path / "a", tmp_path / "b", tmp_path / "o"
    a.write_text("1\n")
    b.write_text("2\n1\n")
    assert run(a, b, out) == "1"
    assert out.read_text() == "1\n2\n" and a.read_text() == "1\n"
