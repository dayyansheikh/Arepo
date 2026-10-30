"""Unit tests for hypothesis battery 1 (statistics, parsers, clocks). No real data is read."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery as B
from astrolabe.research_lab import battery_data as bd


def _ols_cluster_se(y, X, cl, j):
    """Full-regression CR1 sandwich SE of coefficient j (reference implementation)."""
    xtx_inv = np.linalg.inv(X.T @ X)
    b = xtx_inv @ X.T @ y
    e = y - X @ b
    codes, uniq = pd.factorize(cl)
    g = len(uniq)
    S = np.zeros((g, X.shape[1]))
    np.add.at(S, codes, X * e[:, None])
    meat = S.T @ S * g / (g - 1)
    n, k = X.shape
    V = xtx_inv @ meat @ xtx_inv * (n - 1) / (n - k)
    return b[j], math.sqrt(V[j, j])


def _synthetic(n=6000, g=150, beta=0.5, seed=0):
    rng = np.random.default_rng(seed)
    cl = rng.integers(0, g, n)
    day = rng.integers(0, 40, n)
    Z = rng.normal(size=(n, 3))
    x = 0.4 * Z[:, 0] + rng.normal(size=n) + 0.3 * rng.normal(size=g)[cl]
    y = beta * x + Z @ np.array([0.2, -0.1, 0.05]) + rng.normal(size=n) + rng.normal(size=g)[cl]
    return y, x, Z, cl.astype(str), day.astype(str)


def test_beta_matches_full_regression_sandwich():
    y, x, Z, cl, day = _synthetic()
    r = B.beta_test(y, x, Z, cl, day, sign=1, n_boot=200)
    X = np.column_stack([np.ones(len(y)), Z, x])
    b_ref, se_ref = _ols_cluster_se(y, X, cl, X.shape[1] - 1)
    assert r["beta"] == pytest.approx(b_ref, rel=1e-9)
    assert r["se_event"] == pytest.approx(se_ref, rel=1e-6)
    assert r["p"] < 1e-6 and r["sign_tested"] == 1
    lo, hi = r["ci_event_boot"]
    assert lo < r["beta"] < hi


def test_beta_wrong_sign_gives_large_p_and_null_is_calm():
    y, x, Z, cl, day = _synthetic(beta=0.5)
    assert B.beta_test(y, x, Z, cl, day, sign=-1, n_boot=50)["p"] > 0.99
    y0, x0, Z0, cl0, day0 = _synthetic(beta=0.0, seed=3)
    r0 = B.beta_test(y0, x0, Z0, cl0, day0, sign=1, n_boot=50)
    assert 0.001 < r0["p"] < 0.999


def test_twoway_equals_oneway_when_dimensions_coincide():
    rng = np.random.default_rng(1)
    sc = rng.normal(size=500)
    cl = rng.integers(0, 40, 500).astype(str)
    va, vb, v2 = B._twoway(sc, cl, cl)
    assert va == pytest.approx(vb)
    assert v2 == pytest.approx(va)


def test_mean_test_cluster_formula():
    rng = np.random.default_rng(2)
    cl = rng.integers(0, 60, 3000)
    dv = 0.01 + rng.normal(size=3000) * 0.1 + rng.normal(size=60)[cl] * 0.02
    r = B.mean_test(dv, cl.astype(str), rng.integers(0, 30, 3000).astype(str), 1, n_boot=200)
    s = pd.Series(dv - dv.mean()).groupby(cl).sum().to_numpy()
    se = math.sqrt((s**2).sum() * 60 / 59) / len(dv)
    assert r["mean"] == pytest.approx(dv.mean())
    assert r["se_event"] == pytest.approx(se, rel=1e-9)
    assert r["p"] <= 1.0 and r["p_event"] < 0.05


def test_by_uses_cumulative_denominator():
    ps = {"a": 1e-6, "b": 0.01, "c": 0.5}
    small = B.benjamini_yekutieli(ps, 3)
    big = B.benjamini_yekutieli(ps, 400)
    assert small["b"]["pass_by"] and not big["b"]["pass_by"]
    assert big["a"]["p_by"] > small["a"]["p_by"]


def test_parse_deadline_variants():
    ref = datetime(2026, 12, 31, tzinfo=UTC).timestamp()
    d1 = bd.parse_deadline("Will X happen by March 31?", "", ref)
    assert datetime.fromtimestamp(d1, UTC).date().isoformat() == "2026-03-31"
    d2 = bd.parse_deadline("", "June 30, 2027", ref)
    assert datetime.fromtimestamp(d2, UTC).date().isoformat() == "2027-06-30"
    d3 = bd.parse_deadline("Will Y be out by end of April?", "", ref)
    assert math.isnan(d3) or datetime.fromtimestamp(d3, UTC).month == 4
    assert math.isnan(bd.parse_deadline("Who wins the final?", "Team A", ref))


def test_event_ladders_skip_neg_risk_and_order_rungs():
    def mk(i, q, git):
        return {"market_id": str(i), "question": q, "group_item_title": git, "token0": f"t{i}",
                "end_epoch": datetime(2026, 12, 31, tzinfo=UTC).timestamp(),
                "neg_risk_other": False}

    ev = {"neg_risk": False, "markets": [mk(1, "Will X happen by June 30?", "June 30"),
                                         mk(2, "Will X happen by March 31?", "March 31"),
                                         mk(3, "Will X happen by December 31?", "December 31")]}
    lads = bd.event_ladders(ev)
    assert len(lads) == 1 and [r["market_id"] for r in lads[0]] == ["2", "1", "3"]
    assert bd.event_ladders({**ev, "neg_risk": True}) == []


def test_asym_class_rule():
    assert bd.asym_class("Will the Fed cut rates in June?", "", "", "unknown") == "asymmetric"
    assert bd.asym_class("Lakers vs Celtics", "", "", "sports") == "public"
    assert bd.asym_class("Will it snow?", "", "", "other") in ("other", "public")


def _trades(rows):
    return pd.DataFrame(rows, columns=["ts", "side", "size", "price", "outcome_index",
                                       "wallet_hash", "trade_key"])


def test_flow_window_is_price_aligned():
    # price points every 600 s; origin t = 7200; last usable point stamp s < t - 600
    ts_p = np.arange(0, 7200, 600, dtype=float)
    v_p = np.full(len(ts_p), 0.5)
    tr = _trades([[3000.0, "BUY", 10, 0.5, 0, "w1", "a"],  # before s: counted
                  [6500.0, "BUY", 100, 0.5, 0, "w2", "b"]])  # after s, before t: excluded
    T = B.Trades(tr, (ts_p, v_p), {}, None, -np.inf)
    t = np.array([7200.0])
    u = B._last_idx(ts_p, t)
    s = ts_p[u]
    assert s[0] < 7200 - 600
    f = B.flow_features(t, s, np.array([0.5]), T)
    assert f["f_n_2h"][0] == 1.0 and f["f_imb_2h"][0] == pytest.approx(1.0)
    f30 = B.flow_features(t, s, np.array([0.5]), T, shift_s=1800.0)
    assert f30["f_n_2h"][0] == 1.0  # the 3000 s trade is still inside [s-1800-7200, s-1800)


def test_flow_signs_token0_terms_and_truncation():
    ts_p = np.arange(0, 20000, 600, dtype=float)
    v_p = np.full(len(ts_p), 0.4)
    tr = _trades([[10000.0, "SELL", 10, 0.6, 1, "w1", "a"],  # selling outcome 1 = buying token 0
                  [11000.0, "BUY", 10, 0.6, 1, "w2", "b"]])  # buying outcome 1 = selling token 0
    T = B.Trades(tr, (ts_p, v_p), {}, None, -np.inf)
    assert list(T.sgn) == [1.0, -1.0]
    t = np.array([19000.0])
    f = B.flow_features(t, B._last_idx(ts_p, t).astype(float) * 0 + 18000.0, np.array([0.4]), T)
    assert f["f_imb_6h"][0] == pytest.approx(0.0)
    Tt = B.Trades(tr, (ts_p, v_p), {}, None, covered_from=15000.0)  # truncated history
    ft = B.flow_features(t, np.array([18000.0]), np.array([0.4]), Tt)
    assert np.isnan(ft["f_imb_6h"][0]) and np.isnan(ft["f_n_6h"][0])


def test_fresh_wallet_uses_true_first_trade():
    ts_p = np.arange(0, 200000, 600, dtype=float)
    v_p = np.full(len(ts_p), 0.3)
    tr = _trades([[150000.0, "BUY", 10, 0.3, 0, "new", "a"],
                  [151000.0, "BUY", 10, 0.3, 0, "old", "b"]])
    ft = {"new": 149000.0, "old": 150000.0 - 30 * 86400}
    T = B.Trades(tr, (ts_p, v_p), ft, None, -np.inf)
    assert list(T.fresh) == [True, False]


def test_wallet_record_is_causal():
    ent = pd.DataFrame({"wallet": ["w", "w", "w"], "edge": [0.5, 0.3, -0.2],
                        "known": [100.0, 200.0, 300.0]})
    rec = B.WalletRecord(ent)
    r, k = rec.lookup(np.array(["w", "w", "w", "x"]), np.array([50.0, 150.0, 250.0, 500.0]))
    assert k.tolist() == [0, 1, 2, 0]
    assert np.isnan(r[0]) and r[1] == pytest.approx(0.5 / (1 + B.REC_K))
    assert r[2] == pytest.approx(0.8 / (2 + B.REC_K))


def test_ladder_residual_zero_under_constant_hazard():
    hz = 1e-6
    d1, d2 = 2.0e6, 4.0e6
    ts = np.arange(0, 1.5e6, 600, dtype=float)
    near = 1 - np.exp(-hz * (d1 - ts))
    far = 1 - np.exp(-hz * (d2 - ts))
    tt = np.array([1.0e6, 1.2e6])
    R = B.Siblings._ladder_R((ts, near), (ts, far), tt, d1, d2)
    assert np.all(np.abs(R) < 2e-3)


def test_pop_mask_base_and_declared_rules_match():
    assert set(B.POP_RULES) == {h.pop for h in B.HYPOTHESES} | (set(B.POP_RULES) - {
        h.pop for h in B.HYPOTHESES})
    assert {h.pop for h in B.HYPOTHESES} <= set(B.POP_RULES)
    d = pd.DataFrame({"traded": [True, False, True], "f_n_6h": [1.0, 3.0, 0.0]})
    assert B.pop_mask("n6h", d).tolist() == [True, False, False]
    assert B.pop_mask("n6h", d, base=pd.Series(True, index=d.index)).tolist() == [True, True,
                                                                                  False]


def test_declaration_has_40_to_80_unique_hypotheses():
    ids = [h.hid for h in B.HYPOTHESES]
    assert 40 <= len(ids) <= 80 and len(set(ids)) == len(ids)
    for h in B.HYPOTHESES:
        assert h.test in ("beta", "dll", "mean") and h.prior in (-1, 1)
        if h.test == "beta":
            assert len(h.x) == 1
    assert len(B.declaration_sha256()) == 64


def test_prior_test_count_rule(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [
        {"kind": "ml_explain", "n_tests": 10, "evidence_role": "exploratory_historical"},
        {"kind": "ml_explain", "multiple_testing": {"m_tests": 4},
         "evidence_role": "exploratory_historical"},
        {"kind": "ml_explain", "n_tests": 99, "evidence_role": "placebo"},
        {"kind": "ml_explain", "n_tests": 72, "source": "hypothesis_battery_1",
         "evidence_role": "exploratory_historical"},
        {"kind": "flow_screen"}, {"kind": "ml_fit", "evidence_role": "exploratory_historical"},
    ]
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    c = B.prior_test_count(p)
    assert c["ml_explain"] == 14 and c["flow_screen"] == 1 and c["total"] == 15
