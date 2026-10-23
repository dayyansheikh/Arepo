# ruff: noqa: E501
"""The LT11 runner: refusals and exit codes (synthetic only; no data-dumps)."""

import importlib.util
import sys
from pathlib import Path

import pytest

_SP = Path(__file__).resolve().parents[2] / "scripts" / "run_live_tests11.py"
_spec = importlib.util.spec_from_file_location("run_live_tests11", _SP)
R = importlib.util.module_from_spec(_spec)
sys.modules["run_live_tests11"] = R
_spec.loader.exec_module(R)


def test_analyze_refuses_before_the_analysis_date(capsys, tmp_path):
    assert R.main(["analyze", "--out-root", str(tmp_path), "--out", str(tmp_path / "a.json")]) == 2
    assert "refusing" in capsys.readouterr().out and not (tmp_path / "a.json").exists()


def test_size_check_refuses_worlds_without_dev(capsys):
    assert R.main(["size-check", "--worlds", "5"]) == 2


def test_size_check_registered_refuses_unfilled_k_tests(capsys, tmp_path):
    assert R.main(["size-check", "--out", str(tmp_path / "s.json")]) == 2
    assert "k_tests" in capsys.readouterr().out


def test_out_is_never_overwritten(tmp_path, capsys):
    p = tmp_path / "o.json"
    p.write_text("{}")
    assert R.main(["ops-stats", "--root", str(tmp_path), "--out", str(p)]) == 1
    assert p.read_text() == "{}"


def test_census_refuses_an_uncommitted_seal(tmp_path, capsys):
    s = tmp_path / "seal.json"
    s.write_text("{}")
    assert R.main(["census", "--seal", str(s), "--work", str(tmp_path / "w")]) == 2


def test_reader_exits_75_when_nothing_is_new(tmp_path):
    snap, sw, out = tmp_path / "snap", tmp_path / "sw", tmp_path / "out"
    snap.mkdir()
    assert R.main(["reader", "--snapshot-root", str(snap), "--sweep-root", str(sw), "--out-root", str(out)]) == 75


def test_parser_has_every_subcommand():
    ch = R.build_parser()._subparsers._group_actions[0].choices
    assert {"header-precheck", "seal", "census", "size-check", "reader", "backfill-series", "ops-stats", "analyze"} <= set(ch)


@pytest.mark.parametrize("cmd", ["analyze", "ops-stats"])
def test_help_text_mentions_location_ambiguity(cmd):
    assert "LT11 ambiguity A1" in R.__doc__
