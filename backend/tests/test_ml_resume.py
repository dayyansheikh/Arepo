"""Per-unit resume of the MC1 dev run: interrupted + resumed == uninterrupted (bit-for-bit)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import ml_models as mm
from astrolabe.research_lab import ml_resume

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_ml_dev.py"
spec = importlib.util.spec_from_file_location("run_ml_dev_resume_test", SCRIPT)
rmd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rmd
spec.loader.exec_module(rmd)

N, FOLDS = 60, 3
FIT_CALLS: list[tuple[str, int]] = []


def _fake_fit_fold(arm, df, fold, embargo_s, *, collect_shap=False, arms=None):
    """Seeded stand-in for a model fit: deterministic given (arm, fold), counts calls."""
    FIT_CALLS.append((arm, fold["fold"]))
    test_pos = np.arange(fold["fold"], N, FOLDS)
    rng = np.random.default_rng([abs(hash(arm)) % 1000 + len(arm), fold["fold"]])
    p = rng.dirichlet([2, 2, 2], size=len(test_pos))
    shap = {"v": rng.normal(size=(len(test_pos), 2))} if collect_shap else None
    return mm.FoldFit(p, {"config": {"k": fold["fold"]}}, shap), None, test_pos


@pytest.fixture()
def env(monkeypatch):
    FIT_CALLS.clear()
    monkeypatch.setattr(mm, "fit_fold", _fake_fit_fold)
    monkeypatch.setattr(mm, "ARMS", {**mm.ARMS, "Mx": mm.fit_m0})
    monkeypatch.setattr(mm, "UNIT_STORE", None)
    df = pd.DataFrame({"y_class": np.zeros(N)})
    man = {"folds": [{"fold": i} for i in range(FOLDS)], "embargo_s": 0.0,
           "feature_set_version": "t", "delta": 0.01, "manifest_sha256": "abc",
           "category_policy": {}}
    return df, man


def _identity(**kw):
    base = {"fold_manifest_sha256": "abc", "panel_hash": "p", "code_sha256": {"a": "1"},
            "argv": ["x"]}
    return {**base, **kw}


def _run(tmp, df, man, *, budget, sink):
    store = ml_resume.UnitStore(tmp / "res", _identity(), budget_s=budget)
    store.open("STAMP")
    store.begin_slice()
    mm.UNIT_STORE = store
    try:
        return mm.run_arms(df, man, ("M0", "M2"), sink=sink, collect_shap=True)
    finally:
        mm.UNIT_STORE = None


def _same(a, b):
    for arm in a:
        assert np.array_equal(a[arm].proba, b[arm].proba, equal_nan=True)
        assert np.array_equal(a[arm].test_mask, b[arm].test_mask)
        assert a[arm].folds == b[arm].folds
        assert len(a[arm].shap_folds) == len(b[arm].shap_folds)
        for x, y in zip(a[arm].shap_folds, b[arm].shap_folds, strict=True):
            assert np.array_equal(x["test_pos"], y["test_pos"])
            assert np.array_equal(x["shap"]["v"], y["shap"]["v"])


def test_interrupted_then_resumed_equals_uninterrupted(env, tmp_path):
    df, man = env
    plain = mm.run_arms(df, man, ("M0", "M2"), sink=None, collect_shap=True)
    FIT_CALLS.clear()
    slices = 0
    while True:
        slices += 1
        try:
            res = _run(tmp_path, df, man, budget=0.0, sink=None)
            break
        except ml_resume.BudgetExhausted:
            assert slices < 20
    # budget 0 => exactly one new unit per slice, 6 units, last slice completes (fits the last)
    assert slices == 6
    assert len(FIT_CALLS) == 6 and len(set(FIT_CALLS)) == 6  # no unit refitted
    _same(plain, res)
    prog = json.loads((tmp_path / "res" / ml_resume.PROGRESS).read_text())
    assert len(prog["units"]) == 6 and prog["slices"] == 6


def test_finished_units_loaded_not_refitted(env, tmp_path):
    df, man = env
    _run(tmp_path, df, man, budget=None, sink=None)
    n = len(FIT_CALLS)
    _run(tmp_path, df, man, budget=None, sink=None)
    assert len(FIT_CALLS) == n


def test_mismatched_identity_refused(env, tmp_path):
    ml_resume.UnitStore(tmp_path / "r", _identity()).open("S")
    for bad in (_identity(panel_hash="q"), _identity(fold_manifest_sha256="z"),
                _identity(code_sha256={"a": "2"}), _identity(argv=["y"])):
        with pytest.raises(SystemExit, match="REFUSED"):
            ml_resume.UnitStore(tmp_path / "r", bad).open("S2")
    ml_resume.UnitStore(tmp_path / "r", _identity()).open("S3")  # same identity is fine


def test_argv_normalisation_ignores_budget_and_dir():
    a = ["--x", "1", "--time-budget-s", "5", "--resume-dir", "d"]
    b = ["--x", "1", "--time-budget-s=9", "--resume-dir=e"]
    assert ml_resume.normalise_argv(a) == ml_resume.normalise_argv(b) == ["--x", "1"]


def test_buffer_sink_defers_and_preserves_order(tmp_path):
    path = tmp_path / "trials.jsonl"
    like = mm.TrialSink(dataset="d", path=path, evidence_role="exploratory_dev")
    sink = rmd.make_buffer_sink(mm, like)
    import dataclasses

    plc = dataclasses.replace(sink, evidence_role="placebo")
    sink.write({"kind": "ml_fit", "n": 1})
    plc.write({"kind": "ml_fit", "n": 2})
    sink.write({"kind": "ml_fit", "n": 3})
    assert not path.exists()  # nothing written before the final flush
    assert sink.flush() == 3
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    assert [r["n"] for r in rows] == [1, 2, 3]
    assert [r["evidence_role"] for r in rows] == ["exploratory_dev", "placebo", "exploratory_dev"]


# -- reviewer notes: overrun safety, versions, fold manifest, complete refusal -----
class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _store(tmp, clock, budget, name="r"):
    s = ml_resume.UnitStore(tmp / name, _identity(), budget_s=budget, clock=clock, clock_start=0.0)
    s.open("S")
    s.begin_slice()
    return s


def _fit(store, clock, arm, fold, seconds):
    store.checkpoint()
    clock.t += seconds
    store.save(arm, fold, False, test_pos=np.arange(2), proba=np.zeros((2, 3)), diag={}, shap=None)


def test_unit_stops_when_longest_unit_would_overrun(tmp_path):
    clk = FakeClock()
    s = _store(tmp_path, clk, 100.0)
    _fit(s, clk, "M0", 0, 40.0)  # elapsed 40, longest 40
    _fit(s, clk, "M0", 1, 30.0)  # 40 + 40 <= 100 -> allowed; elapsed 70
    with pytest.raises(ml_resume.BudgetExhausted, match="would overrun"):
        s.checkpoint()  # 70 + 40 > 100 though 70 < 100
    prog = json.loads((tmp_path / "r" / ml_resume.PROGRESS).read_text())
    assert sorted(prog["unit_seconds"].values()) == [30.0, 40.0]
    # a later slice knows the longest unit from progress.json even before fitting anything
    clk2 = FakeClock()
    s2 = _store(tmp_path, clk2, 100.0)
    clk2.t = 70.0
    s2.checkpoint()  # no work yet in this slice: always allowed
    s2.save("M0", 2, False, test_pos=np.arange(2), proba=np.zeros((2, 3)), diag={}, shap=None)
    with pytest.raises(ml_resume.BudgetExhausted):
        s2.checkpoint()


def test_final_stage_guard_and_recording(tmp_path):
    clk = FakeClock()
    s = _store(tmp_path, clk, 5000.0)
    _fit(s, clk, "M0", 0, 10.0)
    clk.t = 3500.0
    with pytest.raises(ml_resume.BudgetExhausted, match="final stage"):
        s.final_stage_begin()  # default 1800 s estimate: 3500 + 1800 > 5000
    clk.t = 3000.0
    s.final_stage_begin()  # 3000 + 1800 <= 5000
    clk.t = 3300.0
    s.final_stage_end()
    prog = json.loads((tmp_path / "r" / ml_resume.PROGRESS).read_text())
    assert prog["final_stage_seconds"] == 300.0
    # next slice uses the recorded value (300), not the default
    clk2 = FakeClock()
    s2 = _store(tmp_path, clk2, 5000.0)
    _fit(s2, clk2, "M0", 1, 10.0)
    clk2.t = 4600.0
    s2.final_stage_begin()  # 4600 + 300 <= 5000
    clk2.t = 4800.0
    s3 = _store(tmp_path, FakeClock(), 100.0, name="r2")  # no work done yet: always proceeds
    s3.final_stage_begin()


def test_main_exits_75_when_final_stage_would_overrun(env, tmp_path, monkeypatch):
    monkeypatch.setattr(rmd, "discover_captures", lambda root: [])
    monkeypatch.setattr(rmd, "gate_status", lambda caps, minimum: {"met": True})
    monkeypatch.delenv(rmd.TEST_GATE_ENV, raising=False)
    clk = FakeClock()

    def fake_real_run(args, caps, gate, policy):
        s = _store(tmp_path, clk, args.time_budget_s)
        mm.UNIT_STORE = s
        _fit(s, clk, "M0", 0, 10.0)
        clk.t = 500.0
        s.final_stage_begin()
        return {"_paths": []}

    monkeypatch.setattr(rmd, "real_run", fake_real_run)
    rc = rmd.main(["--resume-dir", str(tmp_path / "r"), "--time-budget-s", "1000"])
    assert rc == 75  # 500 + 1800 default > 1000
    assert mm.UNIT_STORE is None


def test_identity_includes_versions_and_mismatch_refused(tmp_path):
    from types import SimpleNamespace

    ident = rmd.resume_identity(SimpleNamespace(argv=["a"]), {"manifest_sha256": "m"}, "p")
    assert set(ident["versions"]) == {"python", "numpy", "pandas", "scikit-learn", "lightgbm"}
    ml_resume.UnitStore(tmp_path / "v", ident).open("S")
    bad = {**ident, "versions": {**ident["versions"], "numpy": "0.0.0"}}
    with pytest.raises(SystemExit, match="versions"):
        ml_resume.UnitStore(tmp_path / "v", bad).open("S2")


def test_fold_manifest_written_if_missing(tmp_path):
    p = tmp_path / "x_fold_manifest.json"
    assert rmd.write_fold_manifest_if_missing(p, {"a": 1}) is True
    first = p.read_text()
    assert rmd.write_fold_manifest_if_missing(p, {"a": 2}) is False
    assert p.read_text() == first


def test_complete_resume_dir_refused(tmp_path):
    s = ml_resume.UnitStore(tmp_path / "c", _identity())
    s.open("S")
    s.mark_complete(["out.json"])
    with pytest.raises(SystemExit, match="already complete"):
        ml_resume.UnitStore(tmp_path / "c", _identity()).open("S2")
