# ruff: noqa: E501
"""CB4 analysis commands: declaration guard, census/pilot/flip-trades never read outcomes, results never overwritten, exit codes 0/3, runner wiring."""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from astrolabe.research_lab import cb4_analysis as A
from astrolabe.research_lab import cb4_declaration as D

COUNTED = ("measure_N", "measure_E", "measure_commit", "fetch_outcomes", "screen", "replicate")
UNCOUNTED = ("pilot", "flip_trades", "census")


def _ns(*extra):
    return SimpleNamespace(extra=list(extra))


def _ctx(tmp_path, **kw):
    return A.Ctx(spec=tmp_path / "cb4_v1.json", trials=tmp_path / "trials.jsonl", out_root=tmp_path / "out", hist_root=tmp_path / "hist", extract_root=tmp_path / "ext", **kw)


@pytest.mark.parametrize("name", COUNTED)
def test_counted_commands_refuse_without_committed_declaration(tmp_path, name):
    fn = getattr(A, f"cmd_{name}")
    assert fn(_ns("--family", "C"), _ctx(tmp_path)) == A.REFUSED_EXIT == 3
    assert not (tmp_path / "out").exists() and not (tmp_path / "trials.jsonl").exists()


@pytest.mark.parametrize("name", COUNTED)
def test_counted_commands_refuse_uncommitted_spec_and_wrong_hash(tmp_path, name):
    ctx = _ctx(tmp_path)
    D.write_spec(ctx.spec, census_pins={"H": 0}, census_sha256="a" * 64)
    fn = getattr(A, f"cmd_{name}")
    assert fn(_ns("--family", "C"), ctx) == 3  # not a single-commit committed file under git
    spec = json.loads(ctx.spec.read_text())
    spec["declaration_sha256"] = "0" * 64
    ctx.spec.write_text(json.dumps(spec))
    ctx.require_committed = False
    assert fn(_ns("--family", "C"), ctx) == 3  # hash differs from the code's


def test_refused_run_id_and_forbidden_root_exit_3(tmp_path):
    ctx = _ctx(tmp_path)
    assert A.cmd_census(_ns("--family", "C", "--run-id", "h5_cb1"), ctx) == 3
    assert A.cmd_census(_ns("--family", "C", "--extract-root", "x/cb1_extract"), ctx) == 3


def test_census_counts_only_never_reads_outcomes(tmp_path, monkeypatch):
    reads = []
    real = pd.read_csv

    def spy(*a, **k):
        reads.append((str(a[0]) if a else "", k.get("usecols")))
        return real(*a, **k)

    monkeypatch.setattr(pd, "read_csv", spy)
    ctx = _ctx(tmp_path)
    assert A.cmd_census(_ns("--family", "C,N"), ctx) == 0
    doc = json.loads((ctx.out_root / "census.json").read_text())
    assert "counts only" in doc["note"] and set(doc["pin_proposal"]) >= {"rho", "uma_extra_statuses"}
    forbidden = set(D.CENSUS_FORBIDDEN_COLUMNS)
    assert all(not (set(u or []) & forbidden) and "outcome" not in p for p, u in reads)


@pytest.mark.parametrize("name", UNCOUNTED)
def test_uncounted_commands_do_not_touch_outcome_machinery(name):
    src = inspect.getsource(getattr(A, "_" + name.lower()))
    for token in ("fetch_market_outcomes", "check_outcome_allowed", "outcomes_guarded", "OUTCOME_FILE", "attach_c2_outcomes", "require_declaration"):
        assert token not in src
    assert "counted=False" in src or name == "pilot" or "_gate(ctx, args, counted=False)" in src


def test_counted_gate_flag_matches_declaration():
    for name in COUNTED:
        src = inspect.getsource(getattr(A, "_" + name.lower()))
        assert "counted=True" in src


def test_results_never_overwritten(tmp_path):
    ctx = _ctx(tmp_path)
    p, sha = A._write(ctx, "N/results.json", {"a": 1})
    assert p.exists() and len(sha) == 64
    with pytest.raises(FileExistsError):
        A._write(ctx, "N/results.json", {"a": 2})
    assert json.loads(p.read_text()) == {"a": 1}


def test_measure_n_runs_once_then_refuses_overwrite(tmp_path):
    ctx = _ctx(tmp_path, require_committed=False)
    D.write_spec(ctx.spec, census_pins={"H": 0}, census_sha256="a" * 64)
    assert A.cmd_measure_N(_ns(), ctx) == 0  # H_cap < 84: recorded as not testable
    res = json.loads((ctx.out_root / "N" / "results.json").read_text())
    assert res["tests"]["N1"]["testable"] is False
    lines = [json.loads(x) for x in ctx.trials.read_text().splitlines()]
    assert any(x.get("kind") == "ml_explain" and x.get("n_tests") == 2 for x in lines)
    assert A.cmd_measure_N(_ns(), ctx) == 3
    assert json.loads((ctx.out_root / "N" / "results.json").read_text()) == res


def test_measure_commit_needs_both_results(tmp_path):
    ctx = _ctx(tmp_path, require_committed=False, register=tmp_path / "reg.json")
    D.write_spec(ctx.spec, census_pins={"H": 0}, census_sha256="a" * 64)
    assert A.cmd_measure_commit(_ns(), ctx) == 3
    assert not (tmp_path / "reg.json").exists()


def test_stage2_expected_requires_both_stage1_files():
    with pytest.raises(A.Refusal):
        A.stage2_expected({"tests": {}}, None)
    assert A.stage2_expected({"tests": {"C1": {"advance": True}, "C2": {"advance": False}}}, {"tests": {"S2": {"advance": True}}}) == ["C1", "S2"]


def test_run_cb4_wires_every_analysis_command(monkeypatch, capsys):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import run_cb4

    called = []
    for cmd in run_cb4.ANALYSIS_COMMANDS:
        monkeypatch.setattr(A, "cmd_" + cmd.replace("-", "_"), lambda a, c=cmd: called.append(c) or 0)
    for cmd in run_cb4.ANALYSIS_COMMANDS:
        assert run_cb4.main([cmd, "--family", "C"]) == 0
    assert called == list(run_cb4.ANALYSIS_COMMANDS)
    assert set(run_cb4.ANALYSIS_COMMANDS) == {"pilot", "flip-trades", "census", "measure-N", "measure-E", "measure-commit", "fetch-outcomes", "screen", "replicate"}


def test_economics_cost_regime_accessor_delegates(tmp_path):
    from astrolabe.research_lab import cost_regimes, economics

    reg = tmp_path / "none.json"
    assert economics.cost_regime("2026-05-01", "politics", 0.3, register_path=reg) == cost_regimes.cost_regime("2026-05-01", "politics", 0.3, register_path=reg)


@pytest.mark.parametrize("name", ["drafts/q0084_cb4_pmxt_pilot", "drafts/q0085_cb4_flip_trades_dev", "jobs/q0086_cb4_census"])
def test_queue_spec_argv_parses_end_to_end(name):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    import run_cb4

    spec = json.loads((Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / f"{name}.json").read_text())
    assert spec["argv"][0] == "scripts/run_cb4.py"
    a, rest = run_cb4.build_parser().parse_known_args(spec["argv"][1:])
    assert a.cmd in run_cb4.ANALYSIS_COMMANDS
    A._args(a.cmd, SimpleNamespace(extra=[*rest, *a.extra]))  # every option is known to cb4_analysis
    assert spec["resources"]["mem_mb"] <= 1500


def test_pilot_uses_estimated_design_effect_and_narrow_except():
    import inspect

    from astrolabe.research_lab import cb4_analysis as A

    assert "design_effect_from_clusters" in inspect.getsource(A._pilot)
    assert "except _NET_DATA_ERRORS" in inspect.getsource(A._read_hours) and "except Exception" not in inspect.getsource(A._read_hours)
    assert OSError in A._NET_DATA_ERRORS and Exception not in A._NET_DATA_ERRORS
