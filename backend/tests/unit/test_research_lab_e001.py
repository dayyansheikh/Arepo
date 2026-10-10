"""E001 research-lab tests (synthetic fixtures only; no data-dumps access)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import evaluate, extract, models, panel


def _row(mid_id="1", received="2026-10-05T00:00:01.000000Z", **kw):
    base = {
        "capture_id": "c1",
        "capture_start_utc": "2026-10-05T00:00:00.000000Z",
        "received_utc": received,
        "market_id": mid_id,
        "condition_id": "0x" + mid_id,
        "event_id": "e" + mid_id,
        "closed": False,
        "active": True,
        "binary": 1,
        "best_bid": 0.48,
        "best_ask": 0.52,
        "spread": 0.04,
        "last_trade_price": 0.5,
        "chg_1h": 0.01,
        "chg_1d": 0.02,
        "chg_1w": -0.03,
        "liquidity": 100.0,
        "volume24hr": 50.0,
        "end_date": "2026-12-01T00:00:00Z",
        "updated_at": "x",
        "dup_count": 0,
    }
    base.update(kw)
    return base


def test_parse_num_decimal_forms():
    assert extract.parse_num({"$decimal": "0.96"}) == 0.96
    assert extract.parse_num("20.6848") == 20.6848
    assert extract.parse_num(5) == 5.0
    assert extract.parse_num(None) is None
    assert extract.parse_num({"$decimal": None}) is None
    assert extract.parse_num("") is None
    assert extract.parse_num("abc") is None
    assert extract.parse_num(float("nan")) is None
    assert extract.parse_num(True) is None


def test_market_row_and_binary_flag():
    m = {
        "id": 7,
        "outcomes": '["Yes", "No"]',
        "bestBid": {"$decimal": "0.4"},
        "bestAsk": {"$decimal": "0.5"},
        "events": [{"id": "99"}],
        "liquidity": "12.5",
        "endDate": "2026-12-01T00:00:00Z",
    }
    r = extract.market_row(m, "c", "s", "2026-10-05T00:00:01.000000Z")
    assert r["market_id"] == "7" and r["binary"] == 1 and r["event_id"] == "99"
    assert r["best_bid"] == 0.4 and r["liquidity"] == 12.5 and r["chg_1d"] is None
    m3 = dict(m, outcomes='["A","B","C"]')
    assert extract.market_row(m3, "c", "s", "t")["binary"] == 0
    assert extract.market_row({"outcomes": "[]"}, "c", "s", "t") is None


def test_dedup_keeps_first_receipt_and_counts():
    rows = [
        _row("1", "2026-10-05T00:00:05.000000Z", best_bid=0.1),
        _row("2", "2026-10-05T00:00:06.000000Z"),
        _row(
            "1", "2026-10-05T00:00:02.000000Z", best_bid=0.2
        ),  # earlier receipt arrives later in stream
        _row("1", "2026-10-05T00:00:09.000000Z", best_bid=0.3),
    ]
    kept, n = extract.dedup_rows(rows)
    assert n == 2 and len(kept) == 2
    one = next(r for r in kept if r["market_id"] == "1")
    assert one["best_bid"] == 0.2 and one["dup_count"] == 2


J_SCHED = pd.Timestamp("2026-10-06T00:00:00Z").timestamp()


def test_eligibility_rules():
    cases = {
        "ok": {},
        "closed": {"closed": True},
        "inactive": {"active": False},
        "nonbinary": {"binary": 0},
        "no_bid": {"best_bid": None},
        "crossed": {"best_bid": 0.55, "best_ask": 0.52},
        "wide": {"best_bid": 0.40, "best_ask": 0.52, "spread": 0.12},
        "low_mid": {"best_bid": 0.005, "best_ask": 0.02, "spread": 0.015},
        "high_mid": {"best_bid": 0.98, "best_ask": 0.99, "spread": 0.01},
        "ended_before_j": {"end_date": "2026-10-05T12:00:00Z"},
        "end_unknown": {"end_date": None},
    }
    df = pd.DataFrame([_row(str(i), **kw) for i, kw in enumerate(cases.values())])
    ok = dict(zip(cases, panel.eligibility_mask(df, J_SCHED), strict=True))
    assert ok["ok"] and ok["end_unknown"]
    assert not any(v for k, v in ok.items() if k not in ("ok", "end_unknown"))


def _snaps(j_overrides=None):
    i_rows = [_row("1", chg_1d=0.05), _row("2", closed=True), _row("3"), _row("4")]
    j_rows = [
        _row("1", "2026-10-06T00:00:03.000000Z", capture_id="c2", best_bid=0.58, best_ask=0.62),
        _row(
            "3", "2026-10-06T00:00:04.000000Z", capture_id="c2", best_bid=None, best_ask=0.62
        ),  # one-sided
    ]  # market 4 absent at j
    if j_overrides:
        j_rows = j_overrides
    return pd.DataFrame(i_rows), pd.DataFrame(j_rows)


def test_pair_counts_and_target_unavailable():
    si, sj = _snaps()
    pairs, c = panel.build_pair(si, sj, J_SCHED, 0)
    assert c["eligible"] == 3 and c["target_available"] == 1 and c["target_unavailable"] == 2
    assert c["missing_at_j"] == 1 and c["one_sided_or_closed_at_j"] == 1
    p1 = pairs[pairs["market_id"] == "1"].iloc[0]
    assert p1["dmid"] == pytest.approx(0.60 - 0.50)
    assert p1["horizon_h"] == pytest.approx(24.0, abs=0.01)
    assert pairs[pairs["market_id"] != "1"]["dmid"].isna().all()  # not imputed


def test_features_use_only_origin_row():
    si, sj = _snaps()
    base, _ = panel.build_pair(si, sj, J_SCHED, 0)
    # Change everything about j (prices, momentum, liquidity, end/closed):
    # features and eligibility must stay fixed.
    sj2 = sj.copy()
    sj2["best_bid"], sj2["best_ask"] = 0.10, 0.12
    sj2["chg_1d"], sj2["liquidity"], sj2["last_trade_price"] = 0.9, 1e9, 0.99
    sj2["end_date"], sj2["closed"] = "2026-10-06T00:00:01Z", False
    alt, c2 = panel.build_pair(si, sj2, J_SCHED, 0)
    assert list(base["market_id"]) == list(alt["market_id"])
    pd.testing.assert_frame_equal(base[panel.FEATURES_B3], alt[panel.FEATURES_B3])
    assert (
        base.loc[base.market_id == "1", "dmid"].iloc[0]
        != alt.loc[alt.market_id == "1", "dmid"].iloc[0]
    )
    # a feature built from j would have changed the result
    assert alt.loc[alt.market_id == "1", "chg_1d"].iloc[0] == pytest.approx(0.05)
    f = base[base.market_id == "1"].iloc[0]
    assert f["mid"] == pytest.approx(0.5) and f["ltp_minus_mid"] == pytest.approx(0.0)
    assert f["chg1d_x_logliq"] == pytest.approx(0.05 * np.log1p(100.0))


def test_missing_changes_flagged_and_zero():
    o = pd.DataFrame([_row("1", chg_1d=None, end_date=None, last_trade_price=None)])
    f = panel.compute_features(o, np.array([J_SCHED]))
    assert f["chg_1d"].iloc[0] == 0 and f["chg_1d_missing"].iloc[0] == 1
    assert (
        f["end_unknown"].iloc[0] == 1
        and f["ltp_missing"].iloc[0] == 1
        and f["ltp_minus_mid"].iloc[0] == 0
    )


def test_purge_mask_excludes_overlapping_labels():
    t_j = np.array([100.0, 200.0, 300.0, 400.0])
    assert purged_list(t_j, 300.0) == [True, True, True, False]
    assert purged_list(t_j, 99.0) == [False] * 4


def purged_list(t_j, t):
    return list(evaluate.purged_train_mask(t_j, t))


def _synthetic_pairs(n=800, seed=0):
    """3 periods; period p origin times in [p*1000, p*1000+100], labels known 'horizon' later."""
    rng = np.random.default_rng(seed)
    frames = []
    for p in range(3):
        t_i = p * 1000.0 + np.sort(rng.uniform(0, 100, n))
        t_j = (p + 1) * 1000.0 + np.sort(rng.uniform(0, 100, n))
        df = pd.DataFrame(
            {
                "market_id": [f"m{k}" for k in range(n)],
                "event_id": [f"e{k // 2}" for k in range(n)],
                "period": p,
                "t_i": t_i,
                "t_j": t_j,
                "horizon_h": 1.0,
                "dmid": rng.normal(0, 0.02, n),
            }
        )
        for c in panel.FEATURES_B3:
            df[c] = rng.normal(size=n)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def test_walk_forward_purges_label_overlap(monkeypatch):
    pairs = _synthetic_pairs()
    seen = []
    orig = evaluate.fit_predict_all

    def spy(train, test, l2, l3):
        seen.append(len(train["y"]))
        return orig(train, test, l2, l3)

    monkeypatch.setattr(evaluate, "fit_predict_all", spy)
    monkeypatch.setattr(evaluate, "MIN_TRAIN", 50)
    preds, diag = evaluate.walk_forward(pairs)
    # Test period 1 has origins in [1000,1100] while period-0 labels land in [1000,1100]: the
    # earliest bins may only train on label-known pairs; no fit may ever see all 800 period-0
    # pairs at t<=1100 bins start.
    assert set(preds["period"]) <= {1, 2}
    assert max(d["n_train"] for d in diag["lambda_choice"] if d["period"] == 1) <= 800
    # period 2 may use all of period 0 (labels at <= 1100 <= 2000) plus label-known part of period 1
    for d in diag["lambda_choice"]:
        if d["period"] == 1:
            tmin = d["bin"] * evaluate.BIN_SECONDS
            n_known = int((pairs[pairs.period == 0].t_j <= tmin + evaluate.BIN_SECONDS).sum())
            assert d["n_train"] <= n_known
    assert len(seen) == len(diag["lambda_choice"])


def test_ridge_equals_closed_form():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(200, 4)) * [1, 5, 0.1, 3] + [0, 2, 1, -4]
    y = X @ [0.1, -0.2, 0.3, 0.05] + rng.normal(size=200) * 0.1
    lam = 10.0
    r = models.Ridge(lam).fit(X, y)
    mu, sd = X.mean(0), X.std(0)
    Z = (X - mu) / sd
    beta = np.linalg.inv(Z.T @ Z + lam * np.eye(4)) @ Z.T @ (y - y.mean())
    Xt = rng.normal(size=(5, 4))
    np.testing.assert_allclose(
        r.predict(Xt), ((Xt - mu) / sd) @ beta + y.mean(), rtol=1e-9, atol=1e-12
    )
    # train-only standardisation: predictions on test must not refit scaling
    np.testing.assert_allclose(r.mu, mu)


def test_origin_ols_and_lambda_choice():
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([2.0, 4.0, 6.0])
    assert models.fit_origin_ols(x, y) == pytest.approx(2.0)
    assert models.fit_origin_ols(np.zeros(3), y) == 0.0
    rng = np.random.default_rng(2)
    Xf, Xv = rng.normal(size=(300, 3)), rng.normal(size=(300, 3))
    yf, yv = Xf[:, 0] * 0.5, Xv[:, 0] * 0.5
    assert models.choose_lambda(Xf, yf, Xv, yv) == 0.1  # noiseless: least shrinkage wins


def test_r2_oos_and_spearman_known_values():
    assert evaluate.r2_oos(25.0, 100.0) == pytest.approx(0.75)
    assert evaluate.r2_oos(100.0, 100.0) == 0.0
    assert evaluate.r2_oos(1.0, 125.0) == pytest.approx(1 - 1 / 125)
    a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    assert evaluate.spearman(a, a**3) == pytest.approx(1.0)
    assert evaluate.spearman(a, -a) == pytest.approx(-1.0)
    # known value with ties: ranks (1,2.5,2.5,4) vs (1,2,3,4)
    assert evaluate.spearman(
        np.array([1.0, 2.0, 2.0, 3.0]), np.array([1.0, 2.0, 3.0, 4.0])
    ) == pytest.approx(np.corrcoef([1, 2.5, 2.5, 4], [1, 2, 3, 4])[0, 1])
    assert np.isnan(evaluate.spearman(np.zeros(5), a))


def test_summarise_known_synthetic():
    y = np.array([0.02, -0.02, 0.0, 0.03] * 50)
    df = pd.DataFrame(
        {
            "market_id": [f"m{i}" for i in range(len(y))],
            "event_id": "e",
            "period": np.repeat([1, 2], len(y) // 2),
            "dmid": y,
            "B0": 0.0,
            "B1": y * 0.5,
            "B1h": 0.0,
            "B2": y,
            "B3": -y,
        }
    )
    res = evaluate.summarise(df)
    assert res["B1"]["pooled_r2_oos"] == pytest.approx(1 - 0.25)
    assert res["B2"]["pooled_r2_oos"] == pytest.approx(1.0)
    assert res["B3"]["pooled_r2_oos"] == pytest.approx(1 - 4.0)
    assert res["B2"]["pooled_dir_acc"] == 1.0 and res["B3"]["pooled_dir_acc"] == 0.0
    assert (
        np.isnan(res["B0"]["pooled_dir_acc"])
        and res["B0"]["pooled_dir_acc_zero_wrong"] == 0.0
        and res["B0"]["label"] == "baseline"
    )
    assert res["B2"]["label"] == "Inconclusive"  # fewer than 3 test periods


def test_label_rule():
    pp = [
        {"r2_oos": 0.1, "ci_lo": 0.05},
        {"r2_oos": 0.1, "ci_lo": 0.02},
        {"r2_oos": 0.05, "ci_lo": -0.01},
    ]
    assert evaluate.label_for(pp, 0.08) == "Indicative (exploratory)"
    assert evaluate.label_for(pp, -0.01) != "Indicative (exploratory)"
    neg = [
        {"r2_oos": -0.1, "ci_lo": -0.2},
        {"r2_oos": -0.0, "ci_lo": -0.2},
        {"r2_oos": 0.05, "ci_lo": -0.01},
    ]
    assert evaluate.label_for(neg, -0.02) == "Negative"
    mixed = [
        {"r2_oos": 0.1, "ci_lo": -0.05},
        {"r2_oos": -0.1, "ci_lo": -0.2},
        {"r2_oos": 0.05, "ci_lo": -0.01},
    ]
    assert evaluate.label_for(mixed, 0.01) == "Inconclusive"
    assert evaluate.label_for(pp[:2], 0.1) == "Inconclusive"


def test_bootstrap_determinism_and_clustering():
    rng = np.random.default_rng(3)
    cluster = np.repeat([f"m{i}" for i in range(40)], 3)
    sse0 = rng.uniform(0.5, 1.5, 120)
    ssem = sse0 * rng.uniform(0.8, 1.0, 120)
    a = evaluate.clustered_bootstrap_r2(cluster, ssem, sse0, n=200, seed=116)
    b = evaluate.clustered_bootstrap_r2(cluster, ssem, sse0, n=200, seed=116)
    c = evaluate.clustered_bootstrap_r2(cluster, ssem, sse0, n=200, seed=117)
    assert a == b and a != c
    assert a[0] < a[1]
    point = 1 - ssem.sum() / sse0.sum()
    assert a[0] <= point <= a[1]
