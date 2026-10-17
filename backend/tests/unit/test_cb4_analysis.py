# ruff: noqa: E501
"""CB4 analysis commands: declaration guard, census/pilot/flip-trades never read outcomes, results never overwritten, exit codes 0/3, runner wiring."""
from __future__ import annotations

import inspect
import json
import math
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


PINS = {"H": 0, "rho": 0.5, "uma_extra_statuses": []}


def _freeze(ctx, pins=None, census=None):
    """Write a census.json (with its pin proposal) and the spec bound to it (census_sha256), as the real freeze does."""
    from astrolabe.research_lab import provenance

    pins = dict(PINS if pins is None else pins)
    cp = ctx.out_root / "census.json"
    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps({**(census or {}), "pin_proposal": pins}))
    D.write_spec(ctx.spec, census_pins=pins, census_sha256=provenance.sha256_file(cp))
    return cp


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
    _freeze(ctx)
    assert A.cmd_measure_N(_ns(), ctx) == 0  # H_cap < 84: recorded as not testable
    res = json.loads((ctx.out_root / "N" / "results.json").read_text())
    assert res["tests"]["N1"]["testable"] is False
    lines = [json.loads(x) for x in ctx.trials.read_text().splitlines()]
    assert any(x.get("kind") == "ml_explain" and x.get("n_tests") == 2 for x in lines)
    assert A.cmd_measure_N(_ns(), ctx) == 3
    assert json.loads((ctx.out_root / "N" / "results.json").read_text()) == res


def test_measure_commit_needs_both_results(tmp_path):
    ctx = _ctx(tmp_path, require_committed=False, register=tmp_path / "reg.json")
    _freeze(ctx)
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


@pytest.mark.parametrize("name", ["jobs/q0084_cb4_pmxt_pilot", "drafts/q0085_cb4_flip_trades_dev", "jobs/q0086_cb4_census"])
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


def test_replicate_never_derives_k_from_its_own_family():
    src = inspect.getsource(A._replicate)
    assert "else mine" not in src and "stage2_expected(c_dev, s_scr)" in src
    assert src.index("stage2_expected(c_dev, s_scr)") < src.index("if not mine:")


def test_census_e_cells_include_p0_halves_truncation_and_mde(tmp_path, monkeypatch):
    split = D.epoch(D.DATES["D_pl_E"])
    rows, prints, mt = [], [], []
    for g in ("S", "O"):
        for per, e0 in (("P0", split - 5 * 86400), ("P0", split + 5 * 86400), ("P1", split + 100 * 86400), ("P2", split + 200 * 86400)):
            for i in range(3):
                mid = f"{g}{per}{e0}{i}"
                mt.append({"market_id": mid, "group": g, "period": per, "end_epoch": e0, "truncated": i == 0})
                for k in range(2):
                    rows.append({"market_id": mid, "event_id": f"ev{mid}", "group": g, "period": per, "t": e0 - k * 3600.0, "end_epoch": e0})
                    prints.append({"market_id": mid, "event_id": f"ev{mid}", "group": g, "period": per, "t": e0 - k * 3600.0, "end_epoch": e0})
    monkeypatch.setattr(A, "era_frames", lambda rdir: (pd.DataFrame(rows), pd.DataFrame(prints), {"markets": len(mt), "no_files": 0, "_market_table": mt}))
    ctx = _ctx(tmp_path)
    assert A.cmd_census(_ns("--family", "E"), ctx) == 0
    doc = json.loads((ctx.out_root / "census.json").read_text())["E"]
    assert {"SP0a", "SP0b", "OP0a", "OP0b", "SP1", "SP2"} <= set(doc["cells"]) and doc["truncation_by_cell"]["SP0a"]["truncated"] == 1
    assert "mde_delta" in doc["predicted_mde"] and "parallel_trends_placebo_P0_halves" in doc["predicted_mde"] and "_market_table" not in doc["diag"]


def test_flip_trades_not_before_guard_exits_75(tmp_path):
    from datetime import UTC, datetime

    ctx = _ctx(tmp_path, now=datetime(2026, 10, 25, 1, 59, tzinfo=UTC))
    assert A.cmd_flip_trades(_ns("--window", "dev"), ctx) == A.TEMPFAIL_EXIT == 75
    assert not (tmp_path / "out").exists()


# ---- analysis freeze-check fixes (2026-10-17) -------------------------------------------------------------------------------------


def test_counted_runs_verify_pins_against_the_census(tmp_path):
    """Fix 3: a counted command refuses when census.json is missing, differs from the spec's census_sha256, or its pin proposal differs."""
    ctx = _ctx(tmp_path, require_committed=False)
    cp = _freeze(ctx)
    cp.unlink()
    assert A.cmd_measure_N(_ns(), ctx) == 3
    cp.write_text(json.dumps({"pin_proposal": PINS, "extra": 1}))  # different bytes -> sha mismatch
    assert A.cmd_measure_N(_ns(), ctx) == 3
    assert not (ctx.out_root / "N" / "results.json").exists()


@pytest.mark.parametrize("bad", [{"H": 0, "rho": 0.0, "uma_extra_statuses": []}, {"H": 0, "rho": 0.5, "uma_extra_statuses": ["Bad Status"]}, {"H": -1, "rho": 0.5, "uma_extra_statuses": []},
                                 {"H": 0, "rho": 0.5}])
def test_pin_values_are_validated(tmp_path, bad):
    ctx = _ctx(tmp_path, require_committed=False)
    _freeze(ctx, pins=bad)
    assert A.cmd_measure_N(_ns(), ctx) == 3


def test_measure_n_uses_the_pinned_rho(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, require_committed=False)
    seen = {}
    monkeypatch.setattr(A, "_events_meta", lambda ctx, a, b: ([], {}))

    def fake(ctx, hours, meta, seed, meter, rates, rho=None):
        seen["rho"] = rho
        return [], {"hours_done": 0, "hours_missing": 0, "bytes_per_hour": [], "minutes": [], "bytes": 0}

    monkeypatch.setattr(A, "_read_hours", fake)
    _freeze(ctx, pins={"H": 84, "rho": 0.4, "uma_extra_statuses": []})  # after patching: hashed functions are part of the declaration
    assert A.cmd_measure_N(_ns(), ctx) == 0
    assert seen["rho"] == 0.4
    assert "rho=D.N" not in inspect.getsource(A._read_hours).split('"""')[-1]


def test_counted_c_paths_use_pinned_uma_extra_and_guarded_outcomes():
    for fn in (A.c_run, A._fetch_outcomes):
        assert "uma_extra=_uma_extra(ctx)" in inspect.getsource(fn)
    src = inspect.getsource(A.c_run)
    assert "fetch_market_outcomes" not in src and "load_guarded_outcomes" in src


def test_c_inputs_passes_uma_extra(tmp_path, monkeypatch):
    seen = {}
    real = A.R.assign_strata
    monkeypatch.setattr(A.R, "assign_strata", lambda caps, deps, uma_extra=(): seen.setdefault("u", uma_extra) and real(caps, deps, uma_extra=uma_extra) or real(caps, deps, uma_extra=uma_extra))
    A.c_inputs(_ctx(tmp_path), "dev", uma_extra=("paused",))
    assert seen["u"] == ("paused",)


def _census_c(ok_g46=True, ok_side=True):
    return {"C": {"g46": {"ok": ok_g46}, "side_audit_two_sided": {"ok": ok_side}}}


def test_census_gates_and_missing_gate_is_unverified():
    assert A.census_gates(_census_c(), "C")["ok"]
    g = A.census_gates(_census_c(ok_side=False), "C")
    assert not g["ok"] and g["failed"] == ["side_audit_two_sided"]
    assert not A.census_gates({}, "S")["ok"] and A.census_gates({}, "S")["failed"] == ["g50", "h7_side_audit", "t0_publicity"]
    s_ok = {"S": {"g50": {"ok": True}, "t0_publicity": {"ok": True}, "h7_side_audit": {"ok": True}}}
    assert A.census_gates(s_ok, "S")["ok"]
    t = A.gate_failed_tests("S", A.census_gates({}, "S"), ["S2"])
    assert set(t) == {"S2"} and t["S2"]["p"] == 1.0 and t["S2"]["testable"] is False


def test_screen_c_after_failed_census_gate_is_counted_not_testable(tmp_path):
    """Fix 4: a failed side audit makes C1/C2 'not testable', p = 1, counted; no outcome file is needed or read."""
    from datetime import UTC, datetime

    ctx = _ctx(tmp_path, require_committed=False, now=datetime(2026, 11, 9, tzinfo=UTC))
    _freeze(ctx, census=_census_c(ok_side=False))
    assert A.cmd_screen(_ns("--family", "C"), ctx) == 0
    doc = json.loads((ctx.out_root / "C_dev" / "results.json").read_text())
    assert all(doc["tests"][t]["testable"] is False and doc["tests"][t]["p"] == 1.0 for t in ("C1", "C2"))
    lines = [json.loads(x) for x in ctx.trials.read_text().splitlines()]
    assert sum(1 for x in lines if x.get("kind") == D.KIND_TEST) == 2 and any(x.get("source") == "creative_batch_4:C" and x.get("n_tests") == 2 for x in lines)


def test_screen_s_gate_checked_before_the_sealed_half_is_opened():
    src = inspect.getsource(A._screen)
    s_branch = src[src.index('elif fam == "S"'):]
    assert s_branch.index('_census_gates(ctx, "S")') < s_branch.index("load_series(")
    assert 'gate_failed_tests("S", gates)' in s_branch
    rsrc = inspect.getsource(A._replicate)
    assert rsrc.index('_census_gates(ctx, "S")') < rsrc.index("load_series(")


def test_screen_c_refuses_without_the_guarded_outcome_file(tmp_path):
    from datetime import UTC, datetime

    ctx = _ctx(tmp_path, require_committed=False, now=datetime(2026, 11, 9, tzinfo=UTC))
    _freeze(ctx, census=_census_c())
    assert A.cmd_screen(_ns("--family", "C"), ctx) == 3  # gates pass, no outcomes_guarded.json: blocked, never refetched
    assert not (ctx.out_root / "C_dev" / "results.json").exists() and not ctx.trials.exists()


class _Lim:
    def __init__(self, replies):
        self.replies = list(replies)

    def get(self, url, params):
        return self.replies.pop(0)


def test_fetch_market_outcomes_records_failed_batches_and_missing_ids():
    ids = [f"m{i}" for i in range(25)]
    ok = [{"id": f"m{i}", "closed": True, "outcomePrices": '["1", "0"]', "closedTime": "2026-11-01T00:00:00Z"} for i in range(19)]  # m19 missing from a 200
    outs, failed = A.fetch_market_outcomes(_Lim([(200, ok), (500, None)]), ids)
    assert failed == sorted(["m19", *[f"m{i}" for i in range(20, 25)]])
    assert set(outs) == {f"m{i}" for i in range(19)} and outs["m0"]["status"] == "resolved"
    outs2, failed2 = A.fetch_market_outcomes(_Lim([(200, [{"id": "a", "closed": False}])]), ["a"])
    assert not failed2 and outs2["a"]["status"] == "unresolved" and outs2["a"]["y0"] is None


def test_load_guarded_outcomes_refusals(tmp_path):
    p = tmp_path / "g.json"
    with pytest.raises(A.Refusal, match="not found"):
        A.load_guarded_outcomes(p, window="dev", decl="d", need=set())
    p.write_text(json.dumps({"declaration_sha256": "d", "window": "dev", "complete": True, "failed": [], "outcomes": {"m1": {"y0": 1.0, "closed_time": None, "status": "resolved"}}}))
    assert math.isnan(A.load_guarded_outcomes(p, window="dev", decl="d", need={"m1"})["m1"]["closed_time"])
    with pytest.raises(A.Refusal):
        A.load_guarded_outcomes(p, window="dev", decl="other", need={"m1"})
    with pytest.raises(A.Refusal, match="absent"):
        A.load_guarded_outcomes(p, window="dev", decl="d", need={"m1", "m2"})
    p.write_text(json.dumps({"declaration_sha256": "d", "window": "dev", "complete": False, "failed": ["m2"], "outcomes": {}}))
    with pytest.raises(A.Refusal, match="failed"):
        A.load_guarded_outcomes(p, window="dev", decl="d", need=set())


def test_fetch_outcomes_with_a_failed_batch_writes_no_guarded_file(tmp_path, monkeypatch):
    from datetime import UTC, datetime

    ctx = _ctx(tmp_path, require_committed=False, now=datetime(2026, 11, 9, tzinfo=UTC))
    bids = pd.DataFrame({"market_id": ["m1", "m2"], "fill_state": [1, 1]})
    monkeypatch.setattr(A, "c_inputs", lambda ctx, w, uma_extra=(): {"c2": pd.DataFrame({"sports": [False, False]}), "tdir": tmp_path / "t"})
    monkeypatch.setattr(A.R, "c2_paper_bids", lambda c2, trades: bids)
    monkeypatch.setattr(A, "fetch_market_outcomes", lambda lim, ids: ({"m1": {"y0": 1.0, "closed_time": 0.0, "status": "resolved"}}, ["m2"]))
    monkeypatch.setattr(A, "_limiter", lambda ctx, rps: None)
    _freeze(ctx)
    assert A.cmd_fetch_outcomes(_ns("--window", "dev"), ctx) == 3
    assert not (ctx.out_root / "C_dev" / "outcomes_guarded.json").exists()
    rec = [json.loads(x) for x in (ctx.out_root / "C_dev" / "outcomes_fetch_failures.jsonl").read_text().splitlines()]
    assert rec[0]["failed_ids"] == ["m2"] and "y0" not in json.dumps(rec)
    ok_fetch = lambda lim, ids: ({m: {"y0": None, "closed_time": None, "status": "unresolved"} for m in ids}, [])  # noqa: E731
    monkeypatch.setattr(A, "fetch_market_outcomes", ok_fetch)
    ctx.spec.unlink()
    (ctx.out_root / "census.json").unlink()
    _freeze(ctx)
    assert A.cmd_fetch_outcomes(_ns("--window", "dev"), ctx) == 0
    doc = json.loads((ctx.out_root / "C_dev" / "outcomes_guarded.json").read_text())
    assert doc["complete"] and doc["failed"] == [] and doc["status_counts"] == {"resolved": 0, "unresolved": 2}
    assert A.cmd_fetch_outcomes(_ns("--window", "dev"), ctx) == 3  # read once


def test_census_frames_keep_counts_only_and_forbidden_keys_refused():
    df = pd.DataFrame({"market_id": ["m"], "event_id": ["e"], "e_day": ["d"], "delta": [0.1], "delta_w": [0.1], "p_f": [0.4]})
    kept = A.census_frame(df, A.CENSUS_KEEP["c1"])
    assert list(kept.columns) == ["market_id", "event_id", "e_day"]
    assert A.census_forbidden_keys({"C": {"x": [{"delta": 1}]}, "E": {"mde_delta": 1}}) == ["/C/x[0]/delta"]
    assert {"delta_w", "mark", "AS", "d6h", "neg_v", "s3_net"} <= set(D.CENSUS_FORBIDDEN_COLUMNS)


def test_pilot_ingress_cap_is_bounded(tmp_path):
    ctx = _ctx(tmp_path)
    assert A.cmd_pilot(_ns("--ingress-cap-gb", "16"), ctx) == 3
    assert A.cmd_pilot(_ns("--ingress-cap-gb", "0"), ctx) == 3
    assert not (ctx.out_root / "N_pilot").exists()
