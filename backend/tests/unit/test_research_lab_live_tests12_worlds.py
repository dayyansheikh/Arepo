# ruff: noqa: E501
"""LT12 simulated worlds and size check (LIVE_TESTS_12.md 1.8, 1.8.1; re-check fix 2, final verification fix 3), synthetic only. NO test here (or in any
LT12 test file) runs a world, a calibration, a power run, world R1 or the timing at the registered seed 20261597 or at a seed derived from it as 1.8 / 1.8.1
declare (x 100 + 51, 52, 54, 61): :func:`test_no_lt12_test_passes_a_registered_seed` scans every LT12 test file, and the ``_no_registered_seed`` fixture
refuses at run time (LT11's code re-check defect 1 is not repeated). Only shapes, refusals and the calibration mechanics are asserted; no size rate is read."""

from __future__ import annotations

import ast
import copy
import math
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import live_tests12 as lt
from astrolabe.research_lab import live_tests12_analysis as an
from astrolabe.research_lab import live_tests12_worlds as W

TEST_SEED = 4_242_001  # a development test seed; not 20261597 and not one of its declared derivatives
TESTS_DIR = Path(__file__).resolve().parent
GUARDED_CALLS = {"size_check", "world1_lambda", "calib_corr", "evaluate_world", "world_r1", "size_timing", "generate", "world_ch245", "world_ch244", "default_rng", "derived_seed", "seed_guard"}
REGISTERED_NAMES = {"REGISTERED_SEED", "CALIB_SEED", "R1_SEED", "POWER_SEEDS", "REGISTERED_SEEDS"}


@pytest.fixture(autouse=True)
def _no_registered_seed(monkeypatch):
    """Run-time guard: any size_check / calibration / R1 / timing call of this module at a registered seed fails the test."""
    for name in ("size_check", "world1_lambda", "world_r1", "size_timing", "calib_corr"):
        real = getattr(W, name)

        def wrapped(*a, _real=real, _name=name, **kw):
            seeds = [v for v in (*a, *kw.values()) if isinstance(v, (int, np.integer)) and not isinstance(v, bool)]
            assert not any(int(s) in W.REGISTERED_SEEDS for s in seeds), f"{_name} called with a registered seed in a test"
            return _real(*a, **kw)

        monkeypatch.setattr(W, name, wrapped)


def _const(node):
    try:
        return eval(compile(ast.Expression(node), "<seed>", "eval"), {"__builtins__": {}}, {})  # literals and arithmetic of literals only
    except Exception:
        return None


def _violations(text: str, name: str) -> list[str]:
    bad = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func.attr if isinstance(node.func, ast.Attribute) else (node.func.id if isinstance(node.func, ast.Name) else None)
        if fn not in GUARDED_CALLS:
            continue
        for arg in (*node.args, *(k.value for k in node.keywords)):
            v = _const(arg)
            if isinstance(v, int) and v in W.REGISTERED_SEEDS:
                bad.append(f"{name}:{node.lineno} {fn}(... {v} ...)")
            for sub in ast.walk(arg):
                nm = sub.attr if isinstance(sub, ast.Attribute) else (sub.id if isinstance(sub, ast.Name) else None)
                if nm in REGISTERED_NAMES:
                    bad.append(f"{name}:{node.lineno} {fn}(... {nm} ...)")
    return bad


def test_no_lt12_test_passes_a_registered_seed():
    """The guard asked for after LT11's code re-check (defect 1): no LT12 test passes 20261597 (or 20261597 x 100 + 51 / 52 / 54 / 61), or one of the
    worlds module's registered-seed constants, to a size-check, world, calibration, R1, timing or generator call."""
    files = sorted(TESTS_DIR.glob("test_*live_tests12*.py"))
    assert len(files) >= 6
    bad = [v for p in files for v in _violations(p.read_text(), p.name)]
    assert not bad, bad


def test_the_seed_guard_catches_planted_violations():
    planted = ("W.size_check(worlds=2, draws=2, seed=20261597, spec=s)\n"
               "size_check(worlds=2, draws=2, seed=W.REGISTERED_SEED, spec=s)\n"
               "W.world1_lambda(0.5, s, seed=20261597 * 100 + 61)\n"
               "W.world_r1(5, s, seed=W.R1_SEED)\n"
               "np.random.default_rng(2026159751)\n"
               "W.size_check(worlds=2, draws=2, seed=4242, spec=s)\n")
    assert len(_violations(planted, "planted")) == 5


def test_registered_seed_set_is_the_declared_one():
    assert W.REGISTERED_SEED == 20261597 and W.CALIB_SEED == 20261597 * 100 + 61 and W.R1_SEED == 20261597 * 100 + 54
    assert set(W.POWER_SEEDS.values()) == {20261597 * 100 + 51, 20261597 * 100 + 52}
    assert TEST_SEED not in W.REGISTERED_SEEDS and W.DEV_SEED not in W.REGISTERED_SEEDS and W.TIMING_SEED not in W.REGISTERED_SEEDS
    spec = lt.load_spec(sha=None)
    assert spec["seeds"]["size_check"] == 20261597 and spec["size_check"]["world1"]["seed"] == W.CALIB_SEED
    assert W.derived_seed(TEST_SEED, 61) not in W.REGISTERED_SEEDS


def test_seed_guard_refuses_registered_seeds_outside_the_registered_run(monkeypatch):
    fake = 999_000_111
    monkeypatch.setattr(W, "REGISTERED_SEEDS", frozenset({fake}))
    with pytest.raises(W.Refused):
        W.seed_guard(fake, registered=False)
    W.seed_guard(TEST_SEED, registered=False)
    W.seed_guard(TEST_SEED, registered=True)  # the registered code path at a non-registered master seed (tests)


def test_limit_is_frozen():
    assert W.limit_for(2000) == 0.058 and W.limit_for(500) == pytest.approx(0.05 + 1.645 * math.sqrt(0.0475 / 500))


# --- world 1's loading (re-check fix 2, final verification fix 3) ----------------------------------------------------------------------------------


def test_world1_bisection_reaches_rho_ss_within_tolerance():
    spec = lt.load_spec(sha=None)
    s = W.derived_seed(TEST_SEED, 61)
    for rho_census, want in ((0.30, 0.64), (0.80, 0.80)):  # rho_ss = max(rho_census, 0.64)
        r = W.world1_lambda(rho_census, spec, seed=s)
        assert r["ok"] and r["rho_ss"] == pytest.approx(want) and abs(r["corr"] - want) <= 0.005 and r["steps"] <= 40
        assert 0.0 <= r["lambda"] <= 10.0 and abs(W.calib_corr(r["lambda"], slots=20000, seed=s) - want) <= 0.005
    assert spec["size_check"]["world1"] == {"rho_floor": 0.64, "bracket": [0.0, 10.0], "tol": 0.005, "max_steps": 40, "slots": 20000, "seed": W.CALIB_SEED}


def test_world1_failure_rule_nan_unbracketed_and_no_convergence():
    spec = lt.load_spec(sha=None)
    s = W.derived_seed(TEST_SEED, 61)
    assert W.world1_lambda(float("nan"), spec, seed=s)["ok"] is False
    assert W.world1_lambda(None, spec, seed=s)["reason"] == "rho_census is NaN"
    r = W.world1_lambda(0.9999, spec, seed=s)  # above the correlation reachable at lambda = 10
    assert r["ok"] is False and "not bracketed" in r["reason"] and r["corr_at_hi"] < 0.9999
    sp = copy.deepcopy(spec)
    sp["size_check"]["world1"]["max_steps"] = 1
    sp["size_check"]["world1"]["tol"] = 1e-9
    r = W.world1_lambda(0.70, sp, seed=s)
    assert r["ok"] is False and "within 1 bisection steps" in r["reason"]


def test_world1_failure_marks_ch245_size_failed_without_running_worlds_1_and_3(monkeypatch):
    calls = []
    monkeypatch.setattr(W, "evaluate_world", lambda sc, *a, **k: calls.append(sc) or {"reject": False})
    spec = lt.load_spec(sha=None)
    out = W.size_check(worlds=3, draws=2, seed=TEST_SEED, spec=spec, scenarios=("1", "2", "3"), small=True, cal={**W.DEV_CAL, "rho_census": float("nan")})
    assert set(calls) == {"2"} and len(calls) == 3  # world 2 has no v_t and runs; worlds 1 and 3 are not run
    sc = out["scenarios"]["CH245"]
    assert sc["1"]["not_run"] and sc["3"]["not_run"] and not sc["1"]["ok"]
    assert out["per_test"]["CH245"]["status"] == "fail_size_scenario" and set(out["per_test"]["CH245"]["failed_size"]) == {"1", "3"}


def test_registered_size_check_refuses_without_census_inputs():
    spec = lt.load_spec(sha=None)
    with pytest.raises(W.Refused):
        W.size_check(worlds=2, draws=2, seed=TEST_SEED, spec=spec, registered=True, cal=None)
    with pytest.raises(W.Refused):
        W.census_cal(spec, dev=False)
    cal, src = W.census_cal(spec, dev=True)
    assert cal == W.DEV_CAL and "not a size result" in src


# --- declared shapes (1.8.1) --------------------------------------------------------------------------------------------------------------------------


def _rng(i: int = 0):
    return np.random.default_rng(TEST_SEED + i)


def test_worlds_1_and_7_generate_events_with_fewer_than_16_captures():
    df, test = W.generate("1", _rng(1), small=False, cal={**W.DEV_CAL, "lambda": 2.0})
    T = df[df["line"] == "thin"]
    ncap = T.groupby("event_id")["slot"].nunique()
    assert test == "CH245" and (ncap < 16).any() and (ncap >= 16).any() and T["event_id"].nunique() <= 300
    df7, test7 = W.generate("7", _rng(2), small=False)
    n7 = df7.groupby("event_id")["slot"].nunique()
    assert test7 == "CH244" and (n7 < 16).any() and (n7 >= 16).any()
    m = df7.groupby("event_id")["market_id"].nunique()
    assert m.min() >= 3 and m.max() <= 10


def test_ch245_world_shapes():
    for w in ("1", "2", "3", "4", "5", "6"):
        df, _ = W.generate(w, _rng(int(w)), small=True, cal={**W.DEV_CAL, "lambda": 2.0})
        assert {"thin", "dense"} <= set(df["line"]) and set(df["line"]) <= {"thin", "dense"}
        assert (df.groupby(["event_id", "slot", "line"]).size() == 1).all()  # one thin (and one dense) line per pair-capture
        for c in ("o_spread_km1_c", "spread_c", "o_spread_k_ticks"):
            v = df[c].to_numpy(float)
            assert (v >= 1.0).all() and np.allclose(v, np.round(v))  # 1c grid, 1c floor
        th = df[df["line"] == "thin"]
        assert (th["own_spread_k_ticks"] >= 1).all() and "zs_pl" in df and "fam" in df and df["fam"].nunique() <= 40
    w3, _ = W.generate("3", _rng(3), small=True, cal={**W.DEV_CAL, "lambda": 2.0})
    assert all(f"sd{s}" in w3 for s in range(1, 12))
    w5, _ = W.generate("5", _rng(5), small=True)
    assert "liq_proxy" in w5


def test_ch244_world_shapes():
    for w in ("7", "8", "9", "10"):
        df, _ = W.generate(w, _rng(10 + int(w)), small=True)
        st = df.groupby("event_id")["unrew"].agg(["min", "max"])
        assert ((st["min"] == 0) & (st["max"] == 1)).mean() > 0.9  # at least one of each status per event (10% unit removal may drop a member)
        assert set(np.unique(df["shock"])) <= {0.0, 1.0} and (df["shock_size_raw"] <= 20.0).all()
        assert np.allclose(df["shock_x_unrew"], df["shock"] * df["unrew"]) and np.allclose(df["shock_x_lowliq"], df["shock"] * df["lowliq"])
    w9, _ = W.generate("9", _rng(19), small=True)
    assert all(f"tl{t}" in w9 and f"tl{t}_x_shock" in w9 for t in (1, 2, 3))


def test_unit_removal_is_about_ten_percent():
    rng = _rng(30)
    import pandas as pd

    df = pd.DataFrame({"a": np.arange(20000)})
    kept = len(W._remove(df, rng)) / 20000
    assert 0.88 < kept < 0.92


def test_world9_status_liquidity_correlation_is_planted():
    rng = _rng(40)
    cs = []
    for _ in range(400):
        L = rng.normal(size=8)
        u = W.unrew_with_corr(rng, L, -0.4)
        assert 0 < u.sum() < 8
        cs.append(np.corrcoef(u, L)[0, 1])
    assert np.mean(cs) == pytest.approx(-0.4, abs=0.08)


# --- the size worlds call the analysis' own gate (1.8) --------------------------------------------------------------------------------------------------


def test_size_worlds_call_the_same_gate_function(monkeypatch):
    real = lt.event_day_state_shift_gate
    calls = []

    def spy(*a, **k):
        calls.append(k.get("test"))
        return real(*a, **k)

    monkeypatch.setattr(lt, "event_day_state_shift_gate", spy)
    spec = lt.load_spec(sha=None)
    r = W.evaluate_world("4", TEST_SEED + 7, spec, stat="gate", draws=2, small=True, cal=dict(W.DEV_CAL))
    r7 = W.evaluate_world("7", TEST_SEED + 8, spec, stat="gate", draws=2, small=True, cal=dict(W.DEV_CAL))
    assert calls == ["CH245", "CH244"] and "reject" in r and "reject" in r7
    assert an.gate.__module__ == "astrolabe.research_lab.live_tests12_analysis"


def test_size_timing_keeps_only_the_clock(monkeypatch):
    monkeypatch.setattr(W, "evaluate_world", lambda *a, **k: {"reject": True, "rate": 1.0})
    monkeypatch.setattr(W, "world_r1", lambda *a, **k: {"share_both": 1.0})
    ticks = iter(range(10_000))
    spec = lt.load_spec(sha=None)
    out = W.size_timing(spec=spec, worlds=2, draws=4, seed=W.TIMING_SEED, small=True, clock=lambda: float(next(ticks)))
    assert set(out) <= W.TIMING_KEYS
    flat = repr(out)
    assert "reject" not in flat and "rate" not in flat.replace("draw_scaling", "") and "share_both" not in flat
    assert out["projection"]["worlds"] == 2000 and out["projection"]["draws"] == 200
    with pytest.raises(W.Refused):
        W.size_timing(spec=spec, worlds=1, draws=1, seed=W.DEV_SEED)
