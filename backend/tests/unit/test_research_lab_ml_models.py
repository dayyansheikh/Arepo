"""Task 4 tests: synthetic data only. No real snapshot is read."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
pytest.importorskip("lightgbm")

from astrolabe.research_lab import ml_models as mm  # noqa: E402
from astrolabe.research_lab import ml_panel  # noqa: E402

STEP = 7200.0
N_PERIODS, ROWS = 20, 350
CATS = ["crypto", "politics", "other"]


def _panel(signal: str | None = "ml_spread", seed: int = 5, noise_only: bool = False):
    rng = np.random.default_rng(seed)
    names = ml_panel.TIER_A_NAMES
    n = N_PERIODS * ROWS
    X = pd.DataFrame(rng.normal(size=(n, len(names))), columns=names)
    X.loc[rng.random(n) < 0.1, "ml_own_dmid_prev"] = np.nan
    period = np.repeat(np.arange(N_PERIODS), ROWS)
    ev = rng.integers(0, 120, size=n)
    cat = np.array(CATS)[ev % 3]
    s = np.zeros((n, 2))
    if not noise_only:
        s[:, 0] += -1.6 * X["ml_chg_1h"].to_numpy()  # in M0 (reversal)
        s[:, 1] += 1.6 * X["ml_chg_1h"].to_numpy()
        if signal:
            s[:, 0] += -1.8 * X[signal].to_numpy()
            s[:, 1] += 1.8 * X[signal].to_numpy()
    logits = np.column_stack([s[:, 0], np.full(n, 1.5), s[:, 1]])
    p = np.exp(logits - logits.max(1, keepdims=True))
    p /= p.sum(1, keepdims=True)
    y = np.array([rng.choice(3, p=r) for r in p])
    t0 = period * STEP
    df = pd.DataFrame(
        {
            "market_id": [f"m{i}" for i in range(n)], "event_id": [f"e{e}" for e in ev],
            "period": period, "t0": t0.astype(float), "t_i": t0.astype(float),
            "t_j": (t0 + STEP).astype(float), "y_class": y.astype(float),
            "target_available": True, "fee_category": cat,
        }
    )
    return pd.concat([df, X], axis=1)


def _manifest(df):
    table = ml_panel.period_table(df)
    return ml_panel.plan_folds(table, code_sha="test", feature_vers=ml_panel.feature_versions())


@pytest.fixture(scope="module")
def panel_signal():
    df = _panel()
    return df, _manifest(df)


@pytest.fixture(scope="module")
def results(panel_signal):
    df, man = panel_signal
    return {a: mm.run_arm(a, df, man, sink=None, collect_shap=(a == "M2")) for a in mm.ARM_NAMES}


def test_manifest_has_two_folds(panel_signal):
    _, man = panel_signal
    assert len(man["folds"]) == 2


def test_planted_signal_recovered(panel_signal, results):
    df, man = panel_signal
    clusters = mm.cluster_vectors(df)
    sc = mm.score_arms(df, results, clusters, n_boot=200)
    assert sc["non_inferential"] is True and "NON-INFERENTIAL" in sc["non_inferential_reason"]
    ll = {a: v["log_loss"] for a, v in sc["arms"].items()}
    assert ll["M0"] > ll["M1"] and ll["M0"] > ll["M2"] and ll["M0"] > ll["M3_eb"]
    boot = sc["bootstrap"]["event"]["log_loss"]
    for a in ("M1", "M3_eb"):
        assert boot[a]["rel_improvement"] > 0.02
        assert boot[a]["ci95"][0] > 0  # CI excludes 0
    assert boot["M2"]["rel_improvement"] > 0.0
    assert all(r.proba[r.test_mask].min() > 0 for r in results.values())
    assert np.allclose(results["M2"].proba[results["M2"].test_mask].sum(1), 1.0)


def test_pure_noise_gives_no_material_gain():
    df = _panel(noise_only=True, seed=9)
    man = _manifest(df)
    res = {a: mm.run_arm(a, df, man, sink=None) for a in ("M0", "M1", "M3_eb")}
    sc = mm.score_arms(df, res, mm.cluster_vectors(df), n_boot=200)
    for a in ("M1", "M3_eb"):
        # shrinkage may beat the unregularised M0 by a hair; there is no real gain to find
        assert abs(sc["bootstrap"]["event"]["log_loss"][a]["rel_improvement"]) < 0.005


@pytest.mark.parametrize("arm", ["M0", "M1", "M2", "M3_eb"])
def test_no_test_row_in_tuning_or_training(panel_signal, arm):
    df, man = panel_signal
    fold = man["folds"][0]
    ff, train_pos, test_pos = mm.fit_fold(arm, df, fold, man["embargo_s"])
    assert not set(train_pos) & set(test_pos)
    per = df["period"].to_numpy()
    assert set(per[train_pos]) <= set(fold["train_periods"])
    assert not set(per[train_pos]) & set(fold["test_periods"])
    if arm in ("M1", "M2"):
        itr, iva = mm.inner_split(df, train_pos, man["embargo_s"])
        assert set(itr) | set(iva) <= set(train_pos)
        assert not (set(itr) | set(iva)) & set(test_pos)
        assert not set(itr) & set(iva)
        assert per[itr].max() < per[iva].min()
        assert df["t_j"].to_numpy()[itr].max() <= df["t0"].to_numpy()[iva].min() - man["embargo_s"]
    # decisive check: scrambling the labels of EVERY non-training row (test rows, purged rows
    # and future periods) cannot change a single prediction
    d2 = df.copy()
    rng = np.random.default_rng(1)
    other = np.setdiff1d(np.arange(len(df)), train_pos)
    assert len(other) > len(test_pos)  # includes purged and future rows
    d2.loc[other, "y_class"] = rng.integers(0, 3, size=len(other)).astype(float)
    ff2, _, test_pos2 = mm.fit_fold(arm, d2, fold, man["embargo_s"])
    assert np.array_equal(test_pos, test_pos2)
    assert np.array_equal(ff.proba, ff2.proba)
    # rows are scored independently: perturbing one test row's features moves no other row
    d3 = df.copy()
    feat = list(ml_panel.TIER_A_NAMES)
    d3.loc[test_pos[0], feat] = 1e3
    ff3, _, _ = mm.fit_fold(arm, d3, fold, man["embargo_s"])
    assert np.array_equal(ff.proba[1:], ff3.proba[1:])
    assert not np.array_equal(ff.proba[0], ff3.proba[0])
    assert "temperature" in ff.diag if arm != "M3_eb" else True


def test_deterministic_seed(panel_signal):
    df, man = panel_signal
    for arm in ("M1", "M2", "M3_eb"):
        a = mm.run_arm(arm, df, man, sink=None)
        b = mm.run_arm(arm, df, man, sink=None)
        assert np.array_equal(a.proba, b.proba, equal_nan=True)
    assert mm.SEED == 116


def test_shap_shape_and_sums(panel_signal, results):
    df, man = panel_signal
    r = results["M2"]
    assert len(r.shap_folds) == 2
    p = len(ml_panel.TIER_A_NAMES)
    for f in r.shap_folds:
        sh = f["shap"]
        assert sh["contrib"].shape == (len(f["test_pos"]), 3, p)
        assert sh["bias"].shape == (len(f["test_pos"]), 3)
        assert sh["additivity_max_abs_err"] < 1e-4
    out = mm.summarize_shap(df, r)
    assert "EXPLORATORY" in out["status"]
    m = out["margins"]["up_minus_down"]
    assert set(m["mean_abs_by_feature"]) == set(ml_panel.TIER_A_NAMES)
    assert set(m["mean_abs_by_category"]) == set(CATS)
    # the planted features lead; family aggregation is a sum of SHAP, not of |SHAP|
    top = max(m["mean_abs_by_feature"], key=m["mean_abs_by_feature"].get)
    assert top in ("ml_chg_1h", "ml_spread")
    fam_sum_check = {
        k: sum(v) for k, v in ((f, [m["mean_abs_by_feature"][x] for x in xs])
                               for f, xs in out["families"].items())
    }
    for f, tot in m["mean_abs_by_family"].items():
        assert tot <= fam_sum_check[f] + 1e-9  # |sum| <= sum of |.|
    mg = mm.shap_margins(r.shap_folds[0]["shap"]["contrib"])
    c = r.shap_folds[0]["shap"]["contrib"].astype(float)
    assert np.allclose(mg["up_minus_down"], c[:, 2] - c[:, 0])
    assert np.allclose(mg["move_vs_flat"], 0.5 * (c[:, 2] + c[:, 0]) - c[:, 1])


def test_scoring_hand_computed():
    p = np.array([[0.2, 0.5, 0.3], [0.1, 0.1, 0.8]])
    y = np.array([1, 2])
    assert np.allclose(mm.log_loss_rows(p, y), [-np.log(0.5), -np.log(0.8)])
    assert np.allclose(
        mm.brier_rows(p, y),
        [0.04 + 0.25 + 0.09, 0.01 + 0.01 + 0.04],
    )


def _fake_results(ll_m0, ll_arm, cluster_n):
    """Results whose per-row log loss is exactly the given vectors (one class, p = exp(-ll))."""
    n = len(ll_m0)
    def mk(ll):
        p = np.zeros((n, 3))
        p[:, 1] = np.exp(-np.asarray(ll))
        p[:, 0] = p[:, 2] = (1 - p[:, 1]) / 2
        return mm.ArmResult("x", p, np.ones(n, bool), [])
    return {"M0": mk(ll_m0), "A": mk(ll_arm)}


def test_bootstrap_resamples_whole_clusters_across_periods():
    # 2 clusters, each recurring in every period. Whole-cluster draws can only be AA, AB or BB.
    n = 40
    cl = np.array(["A", "B"] * (n // 2))
    period = np.repeat(np.arange(10), 4)
    ll_m0 = np.full(n, 0.7)
    ll_a = np.where(cl == "A", 0.5, 0.9)
    df = pd.DataFrame({"y_class": np.ones(n), "period": period, "event_id": cl})
    res = _fake_results(ll_m0, ll_a, 2)
    sc = mm.score_arms(df, res, {"event": cl}, n_boot=1000)
    b = sc["bootstrap"]["event"]["log_loss"]["A"]
    s0 = ll_m0.sum()
    per_cluster = {"A": ll_a[cl == "A"].sum(), "B": ll_a[cl == "B"].sum()}
    base = {"A": ll_m0[cl == "A"].sum(), "B": ll_m0[cl == "B"].sum()}
    vals = {1 - (per_cluster[x] + per_cluster[y]) / (base[x] + base[y])
            for x, y in (("A", "A"), ("A", "B"), ("B", "B"))}
    for e in b["ci95"]:
        assert min(abs(e - v) for v in vals) < 1e-9
    assert b["ci95"][0] < 0 < b["ci95"][1]
    # point estimate equals the hand-computed relative log-loss improvement
    assert abs(b["rel_improvement"] - (1 - ll_a.sum() / s0)) < 1e-12
    # treating every row as its own cluster would be far narrower: dependence matters
    rows = np.arange(n)
    narrow = mm.score_arms(df, res, {"event": rows}, n_boot=1000)["bootstrap"]["event"]
    nb = narrow["log_loss"]["A"]["ci95"]
    assert (nb[1] - nb[0]) < (b["ci95"][1] - b["ci95"][0])


def test_trial_logging(panel_signal, tmp_path):
    df, man = panel_signal
    path = tmp_path / "trials.jsonl"
    sink = mm.TrialSink(dataset="synthetic", path=path)
    res = {a: mm.run_arm(a, df, man, sink=sink) for a in ("M0", "M2")}
    mm.score_arms(df, res, mm.cluster_vectors(df), n_boot=50, sink=sink, manifest=man)
    lines = [json.loads(x) for x in path.read_text().splitlines()]
    assert len(lines) == 2 * len(man["folds"]) + 1
    fit = [x for x in lines if x["kind"] == "ml_fit" and x["arm"] == "M2"][0]
    assert fit["feature_set_version"] == ml_panel.FEATURE_SET_VERSION
    assert fit["delta"] == 0.005 and "tau" in fit and "tau_m0" in fit
    assert len(fit["hyper_search"]) == len(mm.LGB_GRID)
    assert fit["manifest_sha256"] == man["manifest_sha256"]
    assert fit["provenance"]["env"]["lightgbm"] != "unknown"
    assert lines[-1]["kind"] == "ml_score"


def test_bayes_unseen_groups_get_population_prior():
    rng = np.random.default_rng(3)
    n = 3000
    x = rng.normal(size=(n, len(mm.BAYES_FEATURES)))
    ev = pd.Series([f"e{i}" for i in rng.integers(0, 60, n)])
    cat = pd.Series(np.array(["a", "b", "c"])[rng.integers(0, 3, n)])
    off = {f"e{i}": rng.normal(0, 1.0) for i in range(60)}  # strong event-level offsets
    s = ev.map(off).to_numpy() + 1.0 * x[:, 2]
    y = np.where(s + rng.logistic(size=n) > 0.5, 2, np.where(s + rng.logistic(size=n) < -0.5, 0, 1))
    m = mm.BayesHier().fit(x, y, cat, ev)
    assert m.sd["event"] > 0.3  # the pooled event SD is learned, not left at the start value
    xt = x[:5]
    p1 = m.predict_proba(xt, cat[:5], pd.Series(["new1"] * 5))
    p2 = m.predict_proba(xt, cat[:5], pd.Series(["new2"] * 5))
    assert np.array_equal(p1, p2)
    p3 = m.predict_proba(xt, cat[:5], ev[:5])
    assert not np.allclose(p1, p3)
    assert np.allclose(p1.sum(1), 1.0)
    pc = m.predict_proba(xt, pd.Series(["zz"] * 5), pd.Series(["new1"] * 5))
    assert np.allclose(pc.sum(1), 1.0)


def test_temperature_identity_and_sharpening():
    rng = np.random.default_rng(0)
    p = rng.dirichlet([1, 1, 1], size=500)
    y = np.array([rng.choice(3, p=r) for r in p])
    assert abs(mm.fit_temperature(p, y) - 1.0) < 0.3
    assert np.allclose(mm.apply_temperature(p, 1.0), mm._finalise(p), atol=1e-6)


def test_score_arms_requires_both_cluster_definitions(panel_signal, results):
    df, _ = panel_signal
    cl = mm.cluster_vectors(df, dependence_groups=df["event_id"].str[1:].astype(int) // 5)
    sc = mm.score_arms(df, results, cl, n_boot=100)
    assert sc["non_inferential"] is False and sc["non_inferential_reason"] is None
    assert set(sc["bootstrap"]) == {"event", "dependence_group"}


def test_lgb_grid_is_declared_seeded_random_search():
    assert len(mm.LGB_GRID) == 20
    assert len({tuple(sorted(c.items())) for c in mm.LGB_GRID}) == 20
    assert mm.LGB_GRID == mm._sample_lgb_grid()
    for c in mm.LGB_GRID:
        assert all(c[k] in v for k, v in mm.LGB_SPACE.items())


def test_temperature_source_documented(results):
    for arm in ("M0", "M1", "M2"):
        for d in results[arm].folds:
            assert d["temperature_source"] == mm.TEMP_SOURCE and d["temperature"] > 0


def test_simulation_recovers_partial_pooling_sd():
    out = mm.simulate_hierarchical_check(n_reps=3, n=4000, n_event=100)
    assert 0.4 < out["estimated_sd_mean"]["event"] < 0.8  # truth 0.6
    assert out["coverage_95_mean"]["event"] > 0.8
