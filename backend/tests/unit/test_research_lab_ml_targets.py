"""Multi-horizon targets (direction / dmid / absmove): causality, purge scaling, recovery."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
pytest.importorskip("lightgbm")

from astrolabe.research_lab import ml_models as mm  # noqa: E402
from astrolabe.research_lab import ml_panel  # noqa: E402

STEP = 7200.0
N_PERIODS, ROWS = 20, 300


def _chain(n_periods=8, markets=("a", "b"), mids=None, break_after=None):
    """Hand-built paired panel: period p has capture c{p} -> c{p+1}; mid path per market."""
    rows = []
    for p in range(n_periods):
        for m in markets:
            path = (mids or {}).get(m) or [0.5 + 0.01 * i for i in range(n_periods + 1)]
            cj = f"c{p + 1}" if p != break_after else f"x{p + 1}"
            rows.append({
                "market_id": m, "event_id": "e", "period": p, "capture_i": f"c{p}",
                "capture_j": cj, "t_i": p * STEP, "t0": p * STEP + 10.0,
                "t_j": (p + 1) * STEP + 5.0, "mid_i": path[p], "mid_j": path[p + 1],
                "dmid": path[p + 1] - path[p],
                "y_class": float(ml_panel.assign_class([path[p + 1] - path[p]])[0]),
                "target_available": True})
    return pd.DataFrame(rows)


def test_k_step_target_is_mid_at_i_plus_k():
    path = [0.50, 0.50, 0.52, 0.60, 0.60, 0.40, 0.41, 0.42, 0.43]
    df = ml_panel.add_horizon_targets(_chain(mids={"a": path, "b": path}), (1, 3))
    a = df[df.market_id == "a"].set_index("period")
    assert a.loc[0, "dmid_h3"] == pytest.approx(path[3] - path[0])
    assert a.loc[2, "dmid_h3"] == pytest.approx(path[5] - path[2])
    assert a.loc[2, "y_class_h3"] == 0.0  # down
    assert a.loc[0, "y_absmove_h3"] == 1.0 and a.loc[3, "y_absmove_h3"] == 1.0
    assert a.loc[0, "t_j_h3"] == pytest.approx(3 * STEP + 5.0)  # label time = t_{i+k}
    # k = 1 reproduces the existing columns exactly
    assert np.array_equal(df["dmid_h1"], df["dmid"], equal_nan=True)
    assert np.array_equal(df["y_class_h1"], df["y_class"], equal_nan=True)
    # the last k-1 periods have no k-step target; never imputed
    assert a.loc[[6, 7], "dmid_h3"].isna().all()
    assert not a.loc[[6, 7], "target_available_h3"].any()


def test_chain_break_and_early_target_are_unavailable():
    df = ml_panel.add_horizon_targets(_chain(break_after=1), (3,))
    a = df[df.market_id == "a"].set_index("period")
    assert a.loc[[0, 1], "dmid_h3"].isna().all()  # hop 1 -> 2 is discontinuous
    assert a.loc[3, "dmid_h3"] == pytest.approx(0.01 * 3)
    early = _chain()
    early.loc[(early.period == 2) & (early.market_id == "a"), "t_j"] = 1.0  # before any t0
    d2 = ml_panel.add_horizon_targets(early, (3,))
    a2 = d2[d2.market_id == "a"].set_index("period")
    assert np.isnan(a2.loc[0, "dmid_h3"])  # target row was received before the origin cutoff
    assert not np.isnan(a2.loc[3, "dmid_h3"])


def test_missing_market_row_makes_target_unavailable():
    df = _chain()
    df = df[~((df.market_id == "a") & (df.period == 2))]
    out = ml_panel.add_horizon_targets(df, (3,))
    a = out[out.market_id == "a"].set_index("period")
    assert np.isnan(a.loc[0, "dmid_h3"])  # needs the row of period 2
    assert not np.isnan(out[out.market_id == "b"].set_index("period").loc[0, "dmid_h3"])


def test_horizon_view_swaps_label_columns_and_k1_is_unchanged():
    base = _chain()
    df = ml_panel.add_horizon_targets(base, (3,))
    v3 = ml_panel.horizon_view(df, 3)
    assert np.array_equal(v3["t_j"], df["t_j_h3"], equal_nan=True)
    assert np.array_equal(v3["y_dmid"], df["dmid_h3"], equal_nan=True)
    v1 = ml_panel.horizon_view(base, 1)
    assert np.array_equal(v1["t_j"], base["t_j"]) and np.array_equal(v1["y_dmid"], base["dmid"])
    with pytest.raises(ValueError):
        ml_panel.horizon_view(base, 3)


def _synth(seed=3):
    rng = np.random.default_rng(seed)
    names = ml_panel.EXTENDED_NAMES
    n = N_PERIODS * ROWS
    X = pd.DataFrame(rng.normal(size=(n, len(names))), columns=names)
    period = np.repeat(np.arange(N_PERIODS), ROWS)
    ev = rng.integers(0, 100, size=n)
    sig = 0.01 * X["ml_chg_1h"].to_numpy() + 0.012 * X["ml_spread"].to_numpy()
    dmid = sig + 0.004 * rng.normal(size=n)
    # volatility of the move depends on a feature, so P(|dmid| > delta) is predictable
    vol = np.exp(1.0 * X["ml_spread"].to_numpy())
    dmid2 = 0.004 * vol * rng.normal(size=n)
    t0 = (period * STEP).astype(float)
    df = pd.DataFrame({
        "market_id": [f"m{i}" for i in range(n)], "event_id": [f"e{e}" for e in ev],
        "period": period, "t0": t0, "t_i": t0, "t_j": t0 + STEP, "target_available": True,
        "fee_category": np.array(["crypto", "politics", "other"])[ev % 3],
        "dmid": dmid, "y_class": ml_panel.assign_class(dmid)})
    df = pd.concat([df, X], axis=1)
    df["y_dmid"] = dmid
    df2 = df.copy()
    df2["y_dmid"] = dmid2
    df2["dmid"] = dmid2
    df2["y_class"] = ml_panel.assign_class(dmid2)
    df2["y_absmove"] = (df2["y_class"] != ml_panel.CLASS_FLAT).astype(float)
    return df, df2


def _manifest(df, horizon=1, min_train=None):
    view = ml_panel.horizon_view(df, horizon)
    return ml_panel.plan_folds(ml_panel.period_table(view), code_sha="t",
                               feature_vers=ml_panel.feature_versions(), horizon=horizon,
                               min_train=min_train)


def test_embargo_and_purge_scale_with_horizon():
    d1, _ = _synth()
    m1 = _manifest(d1)
    assert m1["embargo_s"] == pytest.approx(STEP) and "horizon_snapshots" not in m1
    # make a k=3 label panel: label time is three steps after t0
    d3 = d1.copy()
    d3["t_j_h3"] = d3["t0"] + 3 * STEP
    for n in ("mid_j", "dmid", "y_class", "y_dmid", "y_absmove", "target_available"):
        d3[f"{n}_h3"] = d3[n] if n in d3 else d3["y_class"].ne(1).astype(float)
    m3 = _manifest(d3, 3, min_train=12)
    assert _manifest(d3, 3)["min_train_periods"] == 20 and not _manifest(d3, 3)["folds"]
    assert m3["embargo_s"] == pytest.approx(3 * STEP) and m3["horizon_snapshots"] == 3
    assert m3["manifest_sha256"] != m1["manifest_sha256"]
    f1, f3 = m1["folds"][0], m3["folds"][0]
    assert f1["test_t0_min"] == f3["test_t0_min"]
    assert f3["purge_cutoff_t"] == pytest.approx(f3["test_t0_min"] - 3 * STEP)
    tr1, _ = ml_panel.fold_masks(ml_panel.horizon_view(d1, 1), f1)
    tr3, te3 = ml_panel.fold_masks(ml_panel.horizon_view(d3, 3), f3)
    v3 = ml_panel.horizon_view(d3, 3)
    # no training row's k-step label is known after the cutoff; the k = 3 train set is smaller
    assert (v3.loc[tr3, "t_j"] <= f3["purge_cutoff_t"]).all()
    assert tr3.sum() < tr1.sum()
    # periods whose 3-step label lands inside the embargo window are purged
    last_kept = v3.loc[tr3, "period"].max()
    assert last_kept <= (f3["test_t0_min"] - 3 * STEP - 3 * STEP) / STEP + 1e-9
    assert not (te3 & tr3).any()


def test_inner_split_uses_horizon_embargo():
    d1, _ = _synth()
    d3 = d1.copy()
    d3["t_j"] = d3["t0"] + 3 * STEP
    man = _manifest(d1)
    train = np.flatnonzero(d3["period"].to_numpy() < 12)
    itr, iva = mm.inner_split(d3, train, 3 * STEP)
    val_t0 = d3.iloc[iva]["t0"].min()
    assert (d3.iloc[itr]["t_j"] <= val_t0 - 3 * STEP).all()
    assert man["folds"]


@pytest.fixture(scope="module")
def reg_results():
    d, _ = _synth()
    man = _manifest(d)
    return d, man, mm.run_target_arms("dmid", d, man, sink=None)


def test_regression_recovers_planted_signal(reg_results):
    d, man, res = reg_results
    clusters = mm.cluster_vectors(d, d["event_id"].to_numpy())
    sc = mm.score_target(d, res, clusters, "dmid", n_boot=100, manifest=man)
    assert sc["evidence_status"].startswith("EXPLORATORY")
    arms = sc["arms"]
    for m in ("mse", "mae", "huber"):
        assert arms["M1"][m] <= arms["M0"][m] * 1.001
    # the planted spread term is outside M0; the elastic net and the trees must beat it clearly
    assert arms["M1"]["mse"] < 0.8 * arms["M0"]["mse"]
    assert arms["M2"]["mse"] < 0.9 * arms["M0"]["mse"]
    assert arms["M0"]["mse"] < sc["zero_forecast"]["mse"]
    assert set(sc["bootstrap"]) == {"event", "dependence_group"}
    assert sc["bootstrap"]["event"]["mse"]["M1"]["ci95"][0] > 0


def test_binary_recovers_planted_volatility_signal():
    _, d = _synth()
    man = _manifest(d)
    res = mm.run_target_arms("absmove", d, man, sink=None)
    clusters = mm.cluster_vectors(d, d["event_id"].to_numpy())
    sc = mm.score_target(d, res, clusters, "absmove", n_boot=100, manifest=man)
    assert sc["arms"]["M1"]["log_loss"] < sc["arms"]["M0"]["log_loss"]
    assert sc["arms"]["M2"]["log_loss"] < sc["arms"]["M0"]["log_loss"]
    for a in res.values():
        p = a.proba[a.test_mask]
        assert ((p > 0) & (p < 1)).all()


def test_target_trial_lines_record_target_and_horizon(tmp_path):
    d, _ = _synth()
    man = _manifest(d)
    sink = mm.TrialSink(dataset="t", path=tmp_path / "trials.jsonl")
    mm.run_target_arm("dmid", "M0", d, man, sink=sink)
    import json

    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    assert lines and all(x["target"] == "dmid_magnitude" for x in lines)
    assert all(x["evidence_status"] == "EXPLORATORY" and x["horizon_snapshots"] == 1
               for x in lines)
    sink2 = mm.TrialSink(dataset="t", path=tmp_path / "t2.jsonl")
    mm.run_arm("M0", d, man, sink=sink2)
    l2 = [json.loads(x) for x in (tmp_path / "t2.jsonl").read_text().splitlines()]
    assert l2[0]["target"] == "direction_3class" and "CONFIRMATORY" in l2[0]["evidence_status"]


def test_helpers():
    assert mm.is_confirmatory("direction", 1) and not mm.is_confirmatory("direction", 3)
    assert not mm.is_confirmatory("dmid", 1)
    assert mm.huber_rows(np.array([0.005, 0.1]))[0] == pytest.approx(0.5 * 0.005**2)
    with pytest.raises(ValueError):
        mm.run_target_arm("direction", "M0", pd.DataFrame(), {}, sink=None)
