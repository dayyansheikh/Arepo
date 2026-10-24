"""Unit tests for the HB1 replication helpers and the weighted battery estimators."""

from __future__ import annotations

import gzip
import math

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery as B
from astrolabe.research_lab import battery_replication as R


def _wls_cluster_se(y, X, w, cl, j):
    W = np.diag(w)
    xtwx_inv = np.linalg.inv(X.T @ W @ X)
    b = xtwx_inv @ X.T @ W @ y
    e = y - X @ b
    codes, uniq = pd.factorize(cl)
    g = len(uniq)
    S = np.zeros((g, X.shape[1]))
    np.add.at(S, codes, X * (w * e)[:, None])
    meat = S.T @ S * g / (g - 1)
    n, k = X.shape
    V = xtwx_inv @ meat @ xtwx_inv * (n - 1) / (n - k)
    return b[j], math.sqrt(V[j, j])


def test_weighted_beta_matches_wls_sandwich():
    rng = np.random.default_rng(4)
    n, g = 3000, 80
    cl = rng.integers(0, g, n).astype(str)
    day = rng.integers(0, 20, n).astype(str)
    Z = rng.normal(size=(n, 2))
    x = 0.3 * Z[:, 0] + rng.normal(size=n)
    y = 0.4 * x + Z @ np.array([0.1, -0.2]) + rng.normal(size=n)
    w = rng.choice([1.0, 3.0], n)
    r = B.beta_test(y, x, Z, cl, day, sign=1, n_boot=100, w=w)
    X = np.column_stack([np.ones(n), Z, x])
    b_ref, se_ref = _wls_cluster_se(y, X, w, cl, X.shape[1] - 1)
    assert r["beta"] == pytest.approx(b_ref, rel=1e-9)
    assert r["se_event"] == pytest.approx(se_ref, rel=1e-6)
    assert r["weighted"] is True
    ru = B.beta_test(y, x, Z, cl, day, sign=1, n_boot=100)
    assert ru["weighted"] is False and ru["beta"] != r["beta"]


def test_weighted_mean_equals_replicated_rows():
    rng = np.random.default_rng(5)
    dv = rng.normal(size=200)
    cl = rng.integers(0, 30, 200).astype(str)
    day = rng.integers(0, 10, 200).astype(str)
    w = rng.integers(1, 4, 200).astype(float)
    r = B.mean_test(dv, cl, day, 1, n_boot=50, w=w)
    rep = np.repeat(dv, w.astype(int))
    assert r["mean"] == pytest.approx(rep.mean())
    assert B.mean_test(dv, cl, day, 1, n_boot=50)["mean"] == pytest.approx(dv.mean())


def _fake_hb1():
    res = {}
    for h in B.HYPOTHESES:
        res[h.hid] = {"sign_tested": h.prior, "effect": 0.01, "ci_event_boot": [0.0, 0.02],
                      "z_event": 3.0, "p": 1e-5, "n": 1000, "n_event": 100,
                      "scaling": {"scale": "sd", "winsor": [-1.0, 1.0], "sd": 0.5}
                      if h.scale == "sd" and h.test == "beta" else {"scale": "raw"},
                      "discovery": {"beta": 0.008}}
    return {"results": res, "declaration_sha256": "x", "cuts": {"illiq_median_N24": 1.0},
            "survivor_checks": {"FL6": {"economics": {"threshold_abs_signal": 0.004}}}}


def test_build_spec_freezes_signs_scaling_and_families():
    spec = R.build_spec(_fake_hb1())
    assert set(spec["hypotheses"]) == set(R.FAMILY_R) | set(R.FAMILY_W)
    assert len(R.FAMILY_R) == 18 and len(R.FAMILY_W) == 3
    fl6 = spec["hypotheses"]["FL6"]
    assert fl6["family"] == "R" and fl6["econ_tau"] == 0.004 and fl6["hb1_discovery_beta"] == 0.008
    assert spec["hypotheses"]["WA2"]["family"] == "W"
    assert len(R.spec_sha256(spec)) == 64


def test_frozen_x_uses_hb1_scaling_not_h3_data():
    spec = R.build_spec(_fake_hb1())
    d = pd.DataFrame({"f_agg_flow_6h": [-3.0, 0.25, 0.5], "f_rev_notrade": [0.1, 0.2, 0.3]})
    assert R.frozen_x(d, "FL6", spec).tolist() == [-2.0, 0.5, 1.0]  # clip [-1, 1] / 0.5
    assert R.frozen_x(d, "MI2", spec).tolist() == [0.1, 0.2, 0.3]  # raw


def test_write_h3_meta_classes(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    pd.DataFrame({"market_id": ["1", "2", "3"], "event_id": ["10", "20", "30"],
                  "topic": ["politics", "sports", "other"], "neg_risk": ["1", "0", "0"],
                  "question": ["a", "b", "c"]}).to_csv(run / "sample.csv.gz", index=False,
                                                       compression="gzip")
    info = R.write_h3_meta(run, tmp_path / "out")
    meta = pd.read_csv(tmp_path / "out" / "market_meta.csv.gz", dtype={"market_id": str})
    assert meta["asym_class"].tolist() == ["asymmetric", "public", "other"]
    assert info["markets"] == 3
    with gzip.open(tmp_path / "out" / "events_meta.jsonl.gz", "rt") as fh:
        assert fh.read() == ""
