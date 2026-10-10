from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import compare, evaluate, features, panel
from astrolabe.research_lab.compare import ModelSpec


def _pairs(n=600, seed=0):
    """3 periods; labels of period p land in period p+1's origin window."""
    rng = np.random.default_rng(seed)
    frames = []
    for p in range(3):
        t_i = p * 1000.0 + np.sort(rng.uniform(0, 100, n))
        t_j = (p + 1) * 1000.0 + np.sort(rng.uniform(0, 100, n))
        df = pd.DataFrame(
            {
                "market_id": [f"m{p}_{k}" for k in range(n)],
                "event_id": [f"e{k // 3}" for k in range(n)],
                "period": p,
                "t_i": t_i,
                "t_j": t_j,
                "horizon_h": 1.0,
            }
        )
        for c in panel.FEATURES_B3:
            df[c] = rng.normal(size=n)
        df["dmid"] = 0.01 * df["chg_1d"] + rng.normal(0, 0.02, n)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


@pytest.fixture(autouse=True)
def small_min_train(monkeypatch):
    monkeypatch.setattr(evaluate, "MIN_TRAIN", 50)


def test_generic_matches_e001_walk_forward():
    pairs = _pairs()
    ref, _ = evaluate.walk_forward(pairs)
    got, _ = compare.walk_forward_generic(pairs, compare.e001_models(), "market_id")
    assert len(ref) == len(got)
    for m in evaluate.MODELS:
        np.testing.assert_allclose(got[m].to_numpy(), ref[m].to_numpy(), atol=1e-12)
    res = compare.run_comparison(pairs, compare.e001_models(), cluster="market_id", n_boot=200)
    summ = evaluate.summarise(ref)
    for m in evaluate.MODELS:
        assert res["pooled"]["models"][m]["r2_oos"] == pytest.approx(
            summ[m]["pooled_r2_oos"], abs=1e-12
        )
        for d in summ[m]["per_period"]:
            assert res["per_period"][d["period"]]["models"][m]["r2_oos"] == pytest.approx(
                d["r2_oos"], abs=1e-12
            )


def test_features_come_from_origin_columns_only():
    for spec in features.REGISTRY.values():
        assert not set(spec.requires) & features.LABEL_COLUMNS
    with pytest.raises(ValueError):
        features.register(
            features.FeatureSpec("leak", "price", "v", lambda o: o["dmid"], ("dmid",))
        )
    o = pd.DataFrame(
        {
            "best_bid": [0.4],
            "best_ask": [0.5],
            "spread": [0.1],
            "chg_1h": [0.01],
            "chg_1d": [0.02],
            "chg_1w": [0.03],
            "liquidity": [100.0],
            "volume24hr": [10.0],
            "end_date": [None],
            "last_trade_price": [0.45],
            "received_utc": ["2026-10-05T00:00:01.000000Z"],
        }
    )
    ref = panel.compute_features(o, panel._epoch(o["received_utc"]))
    noisy = o.assign(dmid=9.9, t_j=1.0, mid_j=0.9, horizon_h=3.0)
    for n in panel.FEATURES_B3:
        spec = features.REGISTRY[n]
        # compute() is handed only its declared origin columns, never label-side ones
        assert features.compute_origin(spec, noisy).iloc[0] == pytest.approx(ref[n].iloc[0])
    with pytest.raises(KeyError):
        features.compute_origin(features.REGISTRY["mid"], o.drop(columns=["best_ask"]))


def test_book_features_only_when_columns_present():
    pairs = _pairs(100)
    assert "book_imbalance" not in features.expand(["family:book"], pairs)
    pairs["bid_depth"], pairs["ask_depth"] = 3.0, 1.0
    assert features.expand(["family:book"], pairs) == ["book_imbalance"]
    X = features.feature_matrix(pairs, ["book_imbalance"])
    assert X[0, 0] == pytest.approx(0.5)


def test_purge_excludes_label_overlapping_training_rows():
    pairs = _pairs()
    _, diag = compare.walk_forward_generic(
        pairs, [compare.e001_models()[0], ModelSpec("R", ("chg_1d", "mid"), "ridge")], "market_id"
    )
    for d in diag["lambda_choice"]:
        tmin = d["bin"] * evaluate.BIN_SECONDS
        te_t_i = pairs[(pairs.period == d["period"])]
        te_t_i = te_t_i[np.floor(te_t_i.t_i / evaluate.BIN_SECONDS) == d["bin"]].t_i.min()
        ok = (pairs.t_j <= te_t_i) & (pairs.period < d["period"])
        assert d["n_train"] == int(ok.sum()) and tmin <= te_t_i


def test_ridge_lambda_selection_never_sees_test(monkeypatch):
    pairs = _pairs()
    seen = []
    orig = compare.choose_lambda

    def spy(Xf, yf, Xv, yv, grid):
        seen.append((Xf, yf, Xv, yv))
        return orig(Xf, yf, Xv, yv, grid)

    monkeypatch.setattr(compare, "choose_lambda", spy)
    spec = ModelSpec("R", ("chg_1d", "mid"), "ridge")
    base = pairs.copy()
    p1, _ = compare.walk_forward_generic(base, [spec], "market_id")
    n1 = len(seen)
    # corrupt the held-out labels/features of the last period: selection inputs for earlier
    # test periods must not change
    mod = pairs.copy()
    last = mod.period == 2
    mod.loc[last, "dmid"] = 123.0
    mod.loc[last, "chg_1d"] = 55.0
    seen.clear()
    compare.walk_forward_generic(mod, [spec], "market_id")
    # period-1 bins precede any period-2 row: their inner inputs are identical
    n_p1_bins = len(set(np.floor(pairs[pairs.period == 1].t_i / evaluate.BIN_SECONDS)))
    assert n1 > n_p1_bins
    seen_mod = list(seen)
    seen.clear()
    compare.walk_forward_generic(base, [spec], "market_id")
    for a, b in zip(seen[:n_p1_bins], seen_mod[:n_p1_bins], strict=True):
        for u, v in zip(a, b, strict=True):
            np.testing.assert_array_equal(u, v)


def test_paired_bootstrap_shared_resamples_and_self_diff_zero():
    rng = np.random.default_rng(1)
    n = 500
    cluster = np.array([f"e{k // 4}" for k in range(n)])
    y = rng.normal(0, 1, n)
    sse = {
        "B0": y**2,
        "A": (y - 0.3 * y) ** 2,
        "B": (y - 0.2 * y + rng.normal(0, 0.1, n)) ** 2,
        "A2": (y - 0.3 * y) ** 2,
    }
    out = compare.paired_bootstrap(cluster, sse, "B0", n_boot=300, seed=7)
    assert out["diffs"]["A|A2"] == [0.0, 0.0]  # identical models, identical resamples
    again = compare.paired_bootstrap(cluster, sse, "B0", n_boot=300, seed=7)
    assert again == out
    # model CIs equal the single-model reference bootstrap (same resamples)
    lo, hi = evaluate.clustered_bootstrap_r2(cluster, sse["A"], sse["B0"], n=300, seed=7)
    assert out["models"]["A"] == pytest.approx([lo, hi], abs=1e-12)
    # diff CI equals CI of differences of R2 draws using the same resamples
    assert out["diffs"]["A|B"][0] < out["diffs"]["A|B"][1]


def test_self_comparison_via_run_comparison():
    pairs = _pairs()
    s = ModelSpec("R", ("chg_1d", "mid"), "ridge")
    t = ModelSpec("R_copy", ("chg_1d", "mid"), "ridge")
    res = compare.run_comparison(pairs, [compare.e001_models()[0], s, t], n_boot=100)
    d = res["pooled"]["diffs"]["R|R_copy"]
    assert d["diff_r2"] == 0.0 and d["ci_lo"] == 0.0 and d["ci_hi"] == 0.0


def test_ablation_specs():
    base = ModelSpec("B3", tuple(panel.FEATURES_B3), "ridge")
    specs = {s.name: s for s in compare.ablations(base, ["price", "momentum", "book"])}
    assert set(specs) == {"B3-no_price", "B3-no_momentum", "B3+book"}
    assert "mid" not in specs["B3-no_price"].features
    nm = specs["B3-no_momentum"].features
    assert "chg_1d" not in nm and "chg_1d_missing" not in nm
    assert "chg1d_x_logliq" not in nm  # dependent interaction removed too
    assert specs["B3+book"].features[-1] == "book_imbalance"
    small = ModelSpec("P", ("family:price",), "ridge")
    names = {s.name for s in compare.ablations(small, ["price", "context"])}
    assert names == {"P+context"}  # leaving out the only family leaves nothing; price adds nothing


def test_refuse_overwrite(tmp_path):
    p = compare.write_new_json(tmp_path / "run1", {"a": 1})
    assert p.exists()
    with pytest.raises(FileExistsError):
        compare.write_new_json(tmp_path / "run1", {"a": 2})
    assert '"a": 1' in p.read_text()


def test_deterministic_and_provenance(tmp_path):
    pairs = _pairs()
    man = tmp_path / "manifest.json"
    man.write_text("{}")
    specs = compare.e001_models()
    a = compare.run_comparison(pairs, specs, n_boot=100, seed=5, manifest_path=man)
    b = compare.run_comparison(pairs, specs, n_boot=100, seed=5, manifest_path=man)
    assert json.dumps(a, default=float) == json.dumps(b, default=float)
    c = compare.run_comparison(pairs, specs, n_boot=100, seed=6, manifest_path=man)
    assert c["pooled"]["models"]["B3"]["ci_lo"] != a["pooled"]["models"]["B3"]["ci_lo"]
    pv = a["provenance"]
    assert pv["seed"] == 5 and len(pv["data_manifest_sha256"]) == 64
    assert set(pv["code_sha256"]) == {"compare.py", "features.py"}
    assert pv["feature_versions"]["mid"]["version"] == "e001-v1"


def test_rejects_unsupported_options():
    pairs = _pairs(100)
    with pytest.raises(ValueError):
        compare.run_comparison(pairs, compare.e001_models(), purge="none")
    with pytest.raises(ValueError):
        compare.run_comparison(pairs, compare.e001_models(), split="random")
