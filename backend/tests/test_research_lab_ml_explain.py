"""Synthetic-data tests for research_lab.ml_explain (no real data)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import ml_explain as mx


def _folds(n: int, k: int = 3) -> list[mx.Fold]:
    pos = np.arange(n)
    edges = np.linspace(n // 3, n, k + 1).astype(int)
    return [mx.Fold(f"f{i}", pos[: edges[i]], pos[edges[i] : edges[i + 1]]) for i in range(k)]


def _clusters(n: int, size: int = 3) -> dict:
    return {"event": np.arange(n) // size, "dep_group": np.arange(n) // (size * 2)}


def _fast_boot(**kw):
    return {"n_boot": 200, **kw}


def test_planted_interaction_detected():
    rng = np.random.default_rng(0)
    n = 1800
    X = pd.DataFrame(rng.normal(size=(n, 5)), columns=[f"a{i}" for i in range(5)])
    y = ((X.a0 * X.a1 > 0) ^ (rng.random(n) < 0.1)).astype(int).to_numpy()
    oof = mx.fit_oof(X, y, _folds(n), list(X.columns), keep_models=True)
    res = mx.interaction_study(X, oof, list(X.columns), m=40)
    assert res["top_pairs"][0]["pair"] == ["a0", "a1"]
    assert res["top_pairs"][0]["h2_mean"] > 2 * res["top_pairs"][1]["h2_mean"]


def test_duplicate_feature_low_conditional_importance():
    rng = np.random.default_rng(1)
    n = 2400
    x0 = rng.normal(size=n)
    X = pd.DataFrame(
        {
            "s": x0,
            "dup": x0 + 0.01 * rng.normal(size=n),
            "ind": rng.normal(size=n),
            "noise": rng.normal(size=n),
        }
    )
    y = ((x0 + X.ind + rng.normal(scale=0.7, size=n)) > 0).astype(int).to_numpy()
    oof = mx.fit_oof(X, y, _folds(n), list(X.columns), keep_models=True)
    res = mx.conditional_permutation_importance(X, y, oof, _clusters(n), n_boot=200, n_repeats=2)
    f = res["features"]
    assert "s" in f["dup"]["partners_over_threshold"]
    for dup in ("dup", "s"):
        c, m = f[dup]["conditional"]["event"]["mean"], f[dup]["marginal"]["event"]["mean"]
        assert c < 0.3 * m
    ind = f["ind"]
    assert ind["conditional"]["event"]["mean"] > 0.7 * ind["marginal"]["event"]["mean"]
    assert f["noise"]["conditional"]["event"]["mean"] < 0.2 * ind["conditional"]["event"]["mean"]


def test_ablation_noise_family_ci_covers_zero_and_signal_does_not():
    rng = np.random.default_rng(2)
    n = 3000
    X = pd.DataFrame(
        rng.normal(size=(n, 6)), columns=["mid", "spread", "flow_a", "ext_n1", "ext_n2", "ext_n3"]
    )
    y = ((X.mid + 0.8 * X.flow_a + rng.normal(size=n)) > 0).astype(int).to_numpy()
    fam = mx.assign_families(X.columns)
    assert "wallet" in fam and fam["wallet"] == []  # declared but absent
    rep = mx.ablation_study(X, y, _folds(n), fam, ["mid", "spread"], _clusters(n), **_fast_boot())
    assert "wallet" in rep["absent_families"]
    noise = rep["families"]["external"]["drop_minus_full"]["event"]["ci"]
    assert noise[0] < 0 < noise[1]
    sig = rep["families"]["flow"]["only_minus_baseline"]["dep_group"]
    assert sig["ci"][1] < 0  # adding flow to the baseline lowers log loss
    assert rep["families"]["flow"]["demonstrated_incremental_value"] is True
    assert rep["families"]["external"]["demonstrated_incremental_value"] is False
    assert rep["families"]["external"]["label"] == "descriptive_only"
    assert rep["ranking"][0]["unit"] in {"flow", "market_state"}
    assert rep["multiple_testing"]["m_total"] == rep["multiple_testing"]["m_tests"]


def test_threshold_reuse_refused_and_heldout_allowed():
    rng = np.random.default_rng(3)
    n = 900
    X = pd.DataFrame({"a": rng.normal(size=n), "b": rng.normal(size=n)})
    y = ((X.a > 0.3) ^ (rng.random(n) < 0.1)).astype(int).to_numpy()
    folds = _folds(n)
    cl = np.arange(n) // 3
    ids = np.arange(n)
    m = mx.lgb_fit(X.to_numpy()[folds[0].train_pos], y[folds[0].train_pos], list(X.columns))
    hyps = mx.propose_gbm_thresholds(m, folds[0], ids, cl, features=["a"])
    assert hyps and hyps[0].status == "HYPOTHESIS" and hyps[0].discovered_in == "f0"
    h = hyps[0]
    assert 0.0 < h.value < 0.8
    # same fold label
    with pytest.raises(mx.ThresholdReuseError):
        mx.evaluate_threshold(
            h, X.a, y, np.arange(10_000, 10_050), np.arange(50) + 10**6, eval_label="f0"
        )
    # row overlap with the discovery fold (train + test of f0)
    with pytest.raises(mx.ThresholdReuseError):
        mx.evaluate_threshold(
            h, X.a.to_numpy()[:50], y[:50], ids[:50], np.arange(50) + 10**6, eval_label="new"
        )
    # cluster overlap
    with pytest.raises(mx.ThresholdReuseError):
        mx.evaluate_threshold(
            h, X.a.to_numpy()[:50], y[:50], np.arange(50) + 10**5, cl[:50], eval_label="new"
        )
    # genuinely new data is evaluated
    xn = rng.normal(size=600)
    yn = ((xn > 0.3) ^ (rng.random(600) < 0.1)).astype(float)
    out = mx.evaluate_threshold(
        h, xn, yn, np.arange(600) + 10**5, np.arange(600) // 3 + 10**5, eval_label="new", n_boot=200
    )
    assert out["status"] == "confirmatory_evaluation" and out["ci"][0] > 0.3


def test_regimes_flag_uninformative_and_declared_hash():
    rng = np.random.default_rng(4)
    n = 1500
    X = pd.DataFrame(rng.normal(size=(n, 3)), columns=["mid", "flow_a", "ext_n"])
    y = ((X.flow_a + rng.normal(size=n)) > 0).astype(int).to_numpy()
    frame = pd.DataFrame(
        {
            "mid_i": rng.uniform(0, 1, n),
            "ml_log_hours_to_end": np.log1p(rng.uniform(0, 900, n)),
            "ml_log1p_liq": rng.normal(size=n),
            "fee_category": rng.choice(["a", "b"], n),
        }
    )
    frame.loc[n - 20 :, "fee_category"] = "tiny"
    folds, cl = _folds(n), _clusters(n)
    fam = mx.assign_families(X.columns)
    full = mx.fit_oof(X, y, folds, list(X.columns), keep_models=True)
    base = mx.fit_oof(X, y, folds, ["mid"])
    r = mx.regime_study(frame, y, full, base, cl, fam, X, n_boot=100)
    assert r["declaration_hash"] == mx.regime_declaration_hash()
    cat = r["regimes"]["category"]
    assert cat["tiny"]["informative"] is False
    assert not any(c["demonstrated_incremental_value"] for c in cat.values())  # no split declared
    assert cat["a"]["informative"] is True
    assert set(r["regimes"]["price_extremity"]) <= {"<0.1", "0.1-0.9", ">0.9"}
    assert "descriptive_mean_abs_shap_by_family" in cat["a"]


def test_run_explain_and_trial_log(tmp_path):
    rng = np.random.default_rng(5)
    n = 1500
    X = pd.DataFrame(rng.normal(size=(n, 4)), columns=["mid", "spread", "flow_a", "ext_n"])
    y = ((X.mid + X.flow_a + rng.normal(size=n)) > 0).astype(int).to_numpy()
    fam = mx.assign_families(X.columns)
    res, hyps = mx.run_explain(
        X, y, _folds(n, 4), fam, ["mid"], _clusters(n), top_k=3, n_boot=100, prior_tests=0
    )
    assert res["label"] == "EXPLORATORY" and res["judge_fold_ids"] == ["f2", "f3"]
    log = tmp_path / "trials.jsonl"
    assert sum(res["n_tests_by_family"].values()) == res["n_tests"]
    with pytest.raises(ValueError, match="evidence_role"):
        mx.log_trial(res, path=log)
    assert not log.exists()
    rec = mx.log_trial(res, path=log, evidence_role="exploratory_dev")
    line = json.loads(log.read_text().splitlines()[0])
    assert line["evidence_role"] == "exploratory_dev"
    assert mx.prior_ml_explain_tests(log) == res["n_tests"]  # next run's BY carry-over
    assert line["kind"] == "ml_explain" and line["label"] == "EXPLORATORY"
    assert line["trial_id"] == rec["trial_id"] and "multiple_testing" in line
    json.dumps(res, default=float)  # result is serialisable


def _dup_data(seed=7, n=4000):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    X = pd.DataFrame(
        {
            "mid": rng.normal(size=n),
            "flow_s": x,
            "flow_dup": x + 0.01 * rng.normal(size=n),
            "ext_n": rng.normal(size=n),
        }
    )
    y = ((x + rng.normal(scale=0.7, size=n)) > 0).astype(int)
    return X, y


def test_high_shap_duplicate_is_descriptive_only():
    X, y = _dup_data()
    n = len(y)
    res, _ = mx.run_explain(
        X,
        y,
        _folds(n, 4),
        mx.assign_families(X.columns),
        ["mid"],
        _clusters(n),
        top_k=3,
        n_boot=200,
        prior_tests=0,
    )
    units = {r["unit"]: r for r in res["ablation"]["ranking"]}
    shap = res["descriptive"]["mean_abs_shap"]
    assert units["flow"]["label"] == "demonstrated"  # the family does add value
    dup = units["flow_dup"]
    assert shap["flow_dup"] > 2 * shap["ext_n"]  # the model leans on it...
    assert dup["label"] == "descriptive_only"  # ...but removing it costs nothing
    assert dup["demonstrated_incremental_value"] is False
    assert dup["descriptive"]["mean_abs_shap"] == pytest.approx(shap["flow_dup"])
    assert res["ranking_key"].startswith("incremental out-of-sample")


def test_interaction_demonstrated_only_on_later_blocks():
    rng = np.random.default_rng(8)
    n = 4000
    X = pd.DataFrame(rng.normal(size=(n, 4)), columns=["a0", "a1", "a2", "a3"])
    y = ((X.a0 * X.a1 > 0) ^ (rng.random(n) < 0.1)).astype(int).to_numpy()
    folds, cl = _folds(n, 4), _clusters(n)
    cols = list(X.columns)
    pairs = [["a0", "a1"], ["a2", "a3"]]
    kw = {"n_boot": 200, "prior_tests": 0}
    ok = mx.interaction_validation(
        X,
        y,
        folds,
        cols,
        pairs,
        cl,
        discovery_fold_ids=["f0", "f1"],
        judge_fold_ids=["f2", "f3"],
        **kw,
    )
    assert ok["pairs"]["a0xa1"]["label"] == "demonstrated"
    assert ok["pairs"]["a2xa3"]["label"] == "descriptive_only"
    # judging blocks not later than discovery blocks: never demonstrated
    bad = mx.interaction_validation(
        X,
        y,
        folds,
        cols,
        pairs,
        cl,
        discovery_fold_ids=["f2", "f3"],
        judge_fold_ids=["f0", "f1"],
        **kw,
    )
    assert bad["pairs"]["a0xa1"]["label"] == "descriptive_only"


def test_threshold_value_refuses_discovery_fold_and_regime_needs_split():
    X, y = _dup_data(9, 2400)
    n = len(y)
    folds, cl = _folds(n, 4), _clusters(n)
    ids = np.arange(n)
    m = mx.lgb_fit(X.to_numpy()[folds[0].train_pos], y[folds[0].train_pos], list(X.columns))
    h = mx.propose_gbm_thresholds(m, folds[0], ids, cl["event"], features=["flow_s"])[0]
    with pytest.raises(mx.ThresholdReuseError):
        mx.threshold_value(h, X, y, folds, list(X.columns), cl, judge_fold_ids=["f0"], row_ids=ids)
    out = mx.threshold_value(
        h, X, y, folds, list(X.columns), cl, judge_fold_ids=["f2", "f3"], row_ids=ids, n_boot=100
    )
    assert out["hypothesis"]["status"] == "HYPOTHESIS" and out["value"]["n_clusters"] > 0


def test_zero_delta_ll_is_a_value_not_missing():
    assert mx._rank_key(0.0) == 0.0
    order = sorted([None, 0.0, 0.2, -0.1, float("nan")], key=mx._rank_key)
    assert order[:3] == [0.2, 0.0, -0.1]  # 0.0 ranks between positive and negative
    assert all(not mx._is_num(v) for v in order[3:])


# ---------------------------------------------------------------------------------------------
# Screening Batch 2 (J7/J8): history regime contrasts, interaction flags, frozen replication
# ---------------------------------------------------------------------------------------------


def _hist_frame(n: int, seed: int, shape: str = "high_liq"):
    """Synthetic history cell: ``a`` is the flow-like feature, ``liq`` the liquidity proxy. The
    label depends on ``a`` only in the top liquidity tercile ("high_liq"), everywhere
    ("uniform") or not at all ("none")."""
    rng = np.random.default_rng(seed)
    liq = rng.normal(size=n)
    a = rng.normal(size=n)
    b = rng.normal(size=n)
    hi = liq > np.quantile(liq, 2 / 3)
    gate = {"high_liq": hi, "uniform": np.ones(n, bool), "none": np.zeros(n, bool)}[shape]
    logit = 0.3 * b + np.where(gate, 2.5 * a, 0.0)
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    frame = pd.DataFrame(
        {
            "ml_tf_log_notional_24h": liq,
            "ml_log_hours_to_end": rng.uniform(0, 8, n),
            "ml_tf_n_2h": rng.integers(0, 3, n).astype(float),
            "mid_i": rng.uniform(0.02, 0.98, n),
            "a": a,
            "b": b,
        }
    )
    return frame, y


def _hist_cell(shape: str, n: int = 4800, seed: int = 0, n_boot: int = 300, **kw):
    frame, y = _hist_frame(n, seed, shape)
    folds = _folds(n, 6)
    cl = _clusters(n)
    full = mx.fit_oof(frame, y, folds, ["ml_tf_log_notional_24h", "b", "a"])
    base = mx.fit_oof(frame, y, folds, ["ml_tf_log_notional_24h", "b"])
    out = mx.regime_ix_discover(
        frame, frame, y, folds, full, base, ["ml_tf_log_notional_24h", "a", "b"], cl,
        n_boot=n_boot, **kw,
    )
    return frame, y, folds, cl, full, base, out


def test_history_regimes_declared_and_hash_distinct():
    names = [s.name for s in mx.HISTORY_REGIMES]
    assert names == ["liquidity_hist", "time_to_resolution", "trade_active", "price_extremity"]
    assert [c.name for c in mx.HISTORY_CONTRASTS] == ["C-LIQ", "C-TTE", "C-ACT", "C-EXT"]
    assert mx.history_declaration_hash() == mx.history_declaration_hash()
    assert mx.history_declaration_hash() != mx.regime_declaration_hash()
    # trade_active is exactly "n > 0": zero is inactive, any positive count is active
    spec = mx.HISTORY_REGIMES[2]
    lab = mx.assign_regime(spec, pd.Series([0.0, 1.0, 5.0, np.nan]))
    assert list(lab) == ["inactive", "active", "active", "missing"]


def test_planted_high_liquidity_signal_gives_positive_c_liq():
    *_, out = _hist_cell("high_liq")
    c = out["contrasts"]["C-LIQ"]
    assert c["value"]["mean"] > 0 and c["value"]["ci"][0] > 0
    assert c["g_plus"] > c["g_minus"]
    assert c["advance"] and "C-LIQ" in out["advanced"]["contrasts"]
    assert out["declaration_hash"] == mx.history_declaration_hash()


def test_uniform_signal_gives_c_liq_near_zero():
    *_, out = _hist_cell("uniform")
    c = out["contrasts"]["C-LIQ"]
    assert c["g_plus"] > 0 and c["g_minus"] > 0  # the pooled gain exists in every regime
    assert abs(c["value"]["mean"]) < 0.3 * c["g_plus"]  # ...yet the difference is small
    assert c["value"]["ci"][0] < 0 < c["value"]["ci"][1] and not c["advance"]


def test_no_effect_advances_nothing():
    *_, out = _hist_cell("none", seed=3)
    assert out["advanced"] == {"contrasts": [], "pairs": []}


def test_contrast_bootstrap_resamples_whole_clusters_spanning_regimes():
    rng = np.random.default_rng(5)
    k, per = 150, 6
    cl = np.repeat(np.arange(k), per)
    shock = np.repeat(rng.normal(scale=1.0, size=k), per)  # shared by both regimes in a cluster
    plus = np.tile([True, True, True, False, False, False], k)
    d = shock + rng.normal(scale=0.1, size=k * per) + np.where(plus, 0.2, 0.0)
    whole = mx._contrast_boot(d, cl, plus, ~plus, 400, 1)
    rows = mx._contrast_boot(d, np.arange(k * per), plus, ~plus, 400, 1)  # independent rows
    assert whole["n_clusters"] == k and rows["n_clusters"] == k * per
    w_whole = whole["ci"][1] - whole["ci"][0]
    w_rows = rows["ci"][1] - rows["ci"][0]
    assert w_whole < w_rows  # the shared cluster shock cancels in the difference
    assert whole["ci"][0] > 0  # +0.2 effect recovered
    assert abs(whole["mean"] - 0.2) < 0.05


def test_cuts_depend_on_discovery_rows_only():
    n = 300
    liq = np.concatenate([np.linspace(0, 1, n), 1000 + np.linspace(0, 1, n)])
    frame = pd.DataFrame({"ml_tf_log_notional_24h": liq})
    disc = np.arange(2 * n) < n
    cuts = mx.discovery_cuts(frame, disc)["liquidity_hist"]
    assert 0 < cuts[0] < cuts[1] < 1  # judgement rows (>= 1000) did not move the terciles
    frame2 = frame.copy()
    frame2.loc[~disc, "ml_tf_log_notional_24h"] = -50.0
    assert mx.discovery_cuts(frame2, disc)["liquidity_hist"] == cuts
    lab = mx.assign_regime(mx.HISTORY_REGIMES[0], frame["ml_tf_log_notional_24h"], cuts)
    assert set(lab[~disc]) == {"high"}  # later rows classified by the stored cuts


def test_frozen_replication_does_no_discovery(monkeypatch):
    frame, y, folds, cl, full, base, out = _hist_cell("high_liq", n_interactions=0)
    frozen = json.loads(json.dumps(out))  # as read back from a results file
    assert frozen["advanced"]["contrasts"]

    def boom(*a, **k):
        raise AssertionError("discovery must not run in a frozen replication")

    monkeypatch.setattr(mx, "discovery_cuts", boom)
    monkeypatch.setattr(mx, "interaction_study", boom)
    monkeypatch.setattr(mx, "regime_study", boom)
    rep = mx.regime_ix_frozen(frame, frame, y, folds, full, base, cl, frozen, n_boot=200)
    assert set(rep["items"]) == {f"contrast:{n}" for n in frozen["advanced"]["contrasts"]}
    it = rep["items"]["contrast:C-LIQ"]
    assert it["h2_sign"] == 1.0 and it["p_directional"] == it["value"]["p_pos"]
    assert rep["judge_fold_ids"] == [f.fold_id for f in folds]  # every fold judges
    h = mx.holm_replication({"1/direction": rep})
    assert h["n_tested"] == len(rep["items"]) and "p_holm" in it


def test_pairs_validated_with_early_sign_and_weights():
    rng = np.random.default_rng(2)
    n = 3000
    X = pd.DataFrame(rng.normal(size=(n, 4)), columns=["a0", "a1", "a2", "a3"])
    y = ((X.a0 * X.a1 > 0) ^ (rng.random(n) < 0.1)).astype(int).to_numpy()
    folds = _folds(n, 4)
    w = rng.uniform(0.5, 2, n)
    full = mx.fit_oof(X, y, folds, list(X.columns))
    base = mx.fit_oof(X, y, folds, ["a2", "a3"])
    out = mx.regime_ix_discover(
        X.assign(mid_i=0.5), X, y, folds, full, base, list(X.columns), _clusters(n),
        regimes=False, n_interactions=2, n_boot=150, weights=w,
    )
    pairs = out["interactions"]["validation"]["pairs"]
    top = out["interactions"]["discovery"]["top_pairs"][0]["pair"]
    assert top == ["a0", "a1"] and "a0xa1" in pairs
    e = pairs["a0xa1"]
    assert e["early_mean"] > 0 and "weighted" in e and e["advance"]
    assert out["discovery_fold_ids"] == ["f0", "f1"] and out["judge_fold_ids"] == ["f2", "f3"]


def test_tte_lookahead_sensitivity_reported():
    frame, y = _hist_frame(4800, 0)
    folds = _folds(4800, 6)
    full = mx.fit_oof(frame, y, folds, ["ml_tf_log_notional_24h", "b", "a"])
    base = mx.fit_oof(frame, y, folds, ["ml_tf_log_notional_24h", "b"])
    flag = frame["ml_log_hours_to_end"].to_numpy() < 1.0
    out = mx.regime_ix_discover(
        frame, frame, y, folds, full, base, ["a", "b"], _clusters(4800), n_boot=150, exclude=flag
    )
    s = out["tte_lookahead_sensitivity"]
    assert s["rows_excluded"] > 0 and {"sign_flips", "halves"} <= set(s)
