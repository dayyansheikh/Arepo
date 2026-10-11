from __future__ import annotations

import json
import math

import numpy as np
import pytest

from astrolabe.research_lab import compare, evaluate, power
from tests.unit.test_research_lab_compare import _pairs


def _clustered(k=400, m=10, rho=0.5, seed=1):
    rng = np.random.default_rng(seed)
    ids = np.repeat(np.arange(k), m)
    x = np.sqrt(rho) * np.repeat(rng.normal(size=k), m) + np.sqrt(1 - rho) * rng.normal(size=k * m)
    return ids, x


@pytest.mark.parametrize("method", ["sandwich", "bootstrap"])
def test_design_effect_recovered(method):
    ids, x = _clustered()
    r = power.design_effect(ids, x, method=method, n_boot=400)
    assert r["deff"] == pytest.approx(1 + 9 * 0.5, rel=0.2)
    assert r["icc_implied"] == pytest.approx(0.5, abs=0.1)
    assert r["n_effective"] == pytest.approx(len(x) / r["deff"])


def test_design_effect_iid_is_one():
    rng = np.random.default_rng(0)
    r = power.design_effect(np.arange(4000), rng.normal(size=4000))
    assert r["deff"] == pytest.approx(1.0, abs=0.1)


def test_mde_monotone_and_inverse():
    sd = 0.8
    m = [power.mde_delta_r2(k, sd) for k in (100, 400, 1600)]
    assert m[0] > m[1] > m[2]
    assert m[0] / m[1] == pytest.approx(2.0)
    assert power.mde_delta_r2(400, sd, power=0.9) > power.mde_delta_r2(400, sd, power=0.8)
    assert power.mde_delta_r2(400, sd, n_tests=5) > power.mde_delta_r2(400, sd, n_tests=1)
    for target in (0.005, 0.02, 0.037):
        k = power.required_clusters(target, sd)
        assert power.mde_delta_r2(k, sd) <= target
        assert power.mde_delta_r2(k - 1, sd) > target


def test_mde_values_and_corrections():
    # (1.959964 + 0.841621) * 1 / sqrt(100)
    assert power.mde_delta_r2(100, 1.0, correction="none") == pytest.approx(0.28016, abs=1e-4)
    a = power.mde_delta_r2(100, 1.0, n_tests=4, correction="bonferroni")
    b = power.mde_delta_r2(100, 1.0, n_tests=4, correction="holm")
    assert a == b > power.mde_delta_r2(100, 1.0, n_tests=4, correction="none")
    with pytest.raises(ValueError):
        power.mde_delta_r2(10, 1.0, correction="x")


def test_holm_and_bonferroni_adjustment():
    p = [0.01, 0.04, 0.03]
    assert power.adjust_pvalues(p, "bonferroni") == pytest.approx([0.03, 0.12, 0.09])
    assert power.adjust_pvalues(p, "holm") == pytest.approx([0.03, 0.06, 0.06])
    assert (power.adjust_pvalues(p, "holm") <= power.adjust_pvalues(p, "bonferroni")).all()


def test_sd_roundtrip_via_ci():
    rng = np.random.default_rng(3)
    k = 300
    ids = np.arange(k)
    d = rng.normal(0.0, 1.0, k)
    base = 1000.0
    sd = power.cluster_contrib_sd(ids, d, base)
    assert sd == pytest.approx(k * d.std(ddof=1) / base)
    se = sd / math.sqrt(k)
    assert power.sd_from_ci(-1.96 * se, 1.96 * se, k) == pytest.approx(sd, rel=1e-3)


def test_t_distribution():
    assert power.t_ppf(0.975, 3) == pytest.approx(3.182446, abs=1e-4)
    assert power.t_ppf(0.975, 30) == pytest.approx(2.042272, abs=1e-4)
    assert power.t_cdf(0.0, 5) == pytest.approx(0.5)
    assert power.sign_test_pvalue(5, 0) == pytest.approx(0.0625)
    assert power.min_periods_sign_test() == 6


def test_per_period_test_interval():
    r = power.per_period_test([0.01, 0.02, 0.015, 0.012], target_effect=0.005)
    v = np.array([0.01, 0.02, 0.015, 0.012])
    assert r["df"] == 3 and r["n_periods"] == 4
    half = 3.182446 * v.std(ddof=1) / 2
    assert r["ci_lo"] == pytest.approx(v.mean() - half, abs=1e-4)
    assert r["ci_hi"] == pytest.approx(v.mean() + half, abs=1e-4)
    assert r["n_pos"] == 4 and r["sign_p"] == pytest.approx(0.125)
    assert r["periods_needed"] >= 3
    small = power.periods_needed(0.005, 0.002)
    assert small <= r["periods_needed"]


def test_per_period_edge_cases():
    assert power.per_period_test([])["n_periods"] == 0
    assert "sd" not in power.per_period_test([0.1])


def test_time_block_flag_is_additive(monkeypatch):
    monkeypatch.setattr(evaluate, "MIN_TRAIN", 50)
    pairs = _pairs()
    specs = compare.e001_models()
    off = compare.run_comparison(pairs, specs, cluster="market_id", n_boot=100)
    on = compare.run_comparison(
        pairs, specs, cluster="market_id", n_boot=100, time_block_inference=True
    )
    assert "time_block_inference" not in off
    extra = on.pop("time_block_inference")
    for key in ("config", "pooled", "per_period", "lambda_choice", "excluded_insufficient_train"):
        assert json.dumps(on[key], default=float) == json.dumps(off[key], default=float)
    pair = extra["B2|B3"]
    expect = [on["per_period"][p]["diffs"]["B2|B3"]["diff_r2"] for p in sorted(on["per_period"])]
    assert pair["diff_r2"] == pytest.approx(expect)
    assert pair["n_periods"] == len(expect) and pair["df"] == len(expect) - 1
    assert pair["mean"] == pytest.approx(np.mean(expect))
    assert pair["ci_lo"] < pair["mean"] < pair["ci_hi"]
    assert extra.keys() == on["pooled"]["diffs"].keys()
