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
