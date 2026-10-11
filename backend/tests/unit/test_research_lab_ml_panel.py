"""Task 2 (multi-signal pipeline) tests: synthetic fixtures only, at most 3 snapshots in memory."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import evaluate, features, ml_panel
from astrolabe.research_lab.features import FeatureSpec

T0 = pd.Timestamp("2026-10-11T00:00:00Z")


def _ts(hours: float, minutes: float = 0.0) -> str:
    return (T0 + pd.Timedelta(hours=hours, minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.000000Z")


def _cap(k: int, hours: float) -> dict:
    return {"capture_id": f"c{k}", "started_utc": _ts(hours)}


def _snap(hours: float, mids: dict[str, float], *, cap: str, vol: float | None = None, **kw):
    rows = []
    for i, (mid_id, mid) in enumerate(mids.items()):
        r = {
            "capture_id": cap, "received_utc": _ts(hours, 5 + i), "market_id": mid_id,
            "event_id": "e" + mid_id, "closed": False, "active": True, "binary": 1,
            "best_bid": mid - 0.01, "best_ask": mid + 0.01, "spread": 0.02,
            "last_trade_price": mid, "chg_1h": 0.01, "chg_1d": 0.02, "chg_1w": -0.03,
            "liquidity": 100.0, "volume24hr": 50.0, "end_date": "2026-12-01T00:00:00Z",
            "updated_at": _ts(hours, 1), "neg_risk": 0, "neg_risk_market_id": None,
            "neg_risk_other": 0, "event_neg_risk_augmented": 0,
        }
        if vol is not None:
            r["volume_num"] = vol
        r.update(kw)
        rows.append(r)
    df = pd.DataFrame(rows)
    for c in ml_panel._ext_columns():
        if c not in df.columns:
            df[c] = np.nan
    return df


def _hist(*snaps):
    return [ml_panel.slim_history(s) for s in snaps]


MIDS = {"1": 0.50, "2": 0.30, "3": 0.70}


# ---- target ---------------------------------------------------------------------------------


def test_assign_class_boundaries_and_nan():
    d = np.array([-0.02, -0.005, -0.0049, 0.0, 0.005, 0.0051, 0.02, np.nan])
    y = ml_panel.assign_class(d, 0.005)
    assert list(y[:7]) == [0, 1, 1, 1, 1, 2, 2]
    assert np.isnan(y[7])
    # float-grid case: 0.505 - 0.5 is not exactly 0.005 but is flat
    assert ml_panel.assign_class(np.array([0.505 - 0.5]), 0.005)[0] == 1
    # sensitivity delta 0.01: 0.008 moves from "up" to "flat"
    assert ml_panel.assign_class(np.array([0.008]), 0.005)[0] == 2
    assert ml_panel.assign_class(np.array([0.008]), ml_panel.DELTA_SENSITIVITY)[0] == 1
    with pytest.raises(ValueError):
        ml_panel.assign_class(d, 0.0)


def test_class_shares():
    s = ml_panel.class_shares(np.array([0, 1, 1, 2, np.nan]))
    assert s["n"] == 4 and s["flat"] == 0.5 and s["down"] == 0.25 and s["up"] == 0.25


# ---- causality ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "col", ["mid_j", "t_j", "dmid", "y_class", "hist_mid_0", "hist_mid_7", "next_mid", "px_j"]
)
def test_register_ml_rejects_j_or_future_columns(col):
    spec = FeatureSpec("ml_bad", "ml_price", "v", lambda o: o[col], (col,))
    with pytest.raises(ValueError):
        ml_panel.register_ml(spec)
    assert "ml_bad" not in features.REGISTRY


def test_registry_refuses_label_named_feature():
    with pytest.raises(ValueError):
        features.register(FeatureSpec("dmid", "ml_price", "v", lambda o: o["best_bid"], ()))


def test_history_beyond_depth_or_future_impossible():
    with pytest.raises(ValueError):
        ml_panel.history_columns(np.array(["1"]), np.array([1e9]), [ml_panel.slim_history(
            _snap(0, MIDS, cap="c"))] * 7)
    assert all(ml_panel.is_origin_side(f"hist_mid_{k}") for k in range(1, 7))
    assert not ml_panel.is_origin_side("hist_mid_-1")


def test_features_ignore_everything_in_j():
    prev = _snap(-2, {"1": 0.48, "2": 0.30, "3": 0.72}, cap="c0", vol=100.0)
    si = _snap(0, MIDS, cap="c1", vol=110.0)
    sj_a = _snap(2, {"1": 0.55, "2": 0.30, "3": 0.60}, cap="c2", vol=150.0)
    sj_b = _snap(2, {"1": 0.40, "2": 0.45, "3": 0.65}, cap="c2", vol=999.0, liquidity=7.0,
                 chg_1h=0.5)
    a, ca = ml_panel.build_period(si, sj_a, _cap(1, 0), _cap(2, 2), 1, _hist(prev))
    b, cb = ml_panel.build_period(si, sj_b, _cap(1, 0), _cap(2, 2), 1, _hist(prev))
    fcols = list(ml_panel.TIER_A_NAMES)
    pd.testing.assert_frame_equal(a[fcols], b[fcols])
    assert not (a["dmid"].to_numpy() == b["dmid"].to_numpy()).all()  # labels do change
    # cumulative field: origin value and i-1 -> i difference only
    assert list(a["ml_volume_num"]) == [110.0] * 3
    assert list(a["ml_volume_num_delta_prev"]) == [10.0] * 3


def test_no_feature_or_name_encodes_label_or_sweep_gap():
    ml_panel.register_tier_a()
    for n in ml_panel.TIER_A_NAMES:
        spec = features.REGISTRY[n]
        assert not set(spec.requires) & features.LABEL_COLUMNS
        assert all(ml_panel.is_origin_side(c) for c in spec.requires)
        assert "gap" not in n and "sweep" not in n
    assert set(ml_panel.TIER_A_NAMES).isdisjoint(features.LABEL_COLUMNS)


# ---- pairs, Gamma mid at both ends, sweep timing --------------------------------------------


def test_pairs_use_gamma_mid_at_both_ends_and_classes():
    si = _snap(0, MIDS, cap="c1")
    sj = _snap(2, {"1": 0.60, "2": 0.30, "3": 0.50}, cap="c2")
    df, c = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [])
    by = df.set_index("market_id")
    assert by.loc["1", "mid_i"] == pytest.approx(0.50)
    assert by.loc["1", "mid_j"] == pytest.approx(0.60)
    assert by.loc["1", "dmid"] == pytest.approx(0.10)
    assert list(by["y_class"]) == [2, 1, 0]
    assert c["target_available"] == 3 and c["gap_h"] == pytest.approx(2.0)
    assert 0 <= by["horizon_h"].min() and by["horizon_h"].max() < 3


def test_sweep_moves_t0_only_and_marks_early_targets_unavailable():
    si = _snap(0, MIDS, cap="c1")
    sj = _snap(2, {"1": 0.60, "2": 0.35, "3": 0.50}, cap="c2")
    plain, _ = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [])
    t_late = pd.Timestamp(_ts(2, 6.5)).timestamp()  # after market 1, before market 3
    swept, c = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [],
                                     sweep_receipt_epoch=t_late,
                                     sweep_returned=990, sweep_eligible=1000)
    assert c["sweep"] == {"returned": 990, "eligible": 1000, "coverage": 0.99}
    assert (swept["t0"] >= plain["t_i"]).all() and swept["t0"].nunique() == 1
    assert swept["target_available"].sum() < plain["target_available"].sum()
    assert c["target_before_t0"] == (plain["target_available"].sum()
                                     - swept["target_available"].sum())
    # labels for the rows that remain are identical: the sweep never enters the target
    both = swept["target_available"].to_numpy()
    np.testing.assert_array_equal(swept.loc[both, "dmid"], plain.loc[both, "dmid"])
    assert swept.loc[~both, "y_class"].isna().all()


def test_gap_outside_window_skips_period():
    si, sj = _snap(0, MIDS, cap="c1"), _snap(4, MIDS, cap="c2")
    df, c = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 4), 1, [])
    assert df is None and "gap" in c["skipped"]
    df, c = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 1), 1, [])
    assert df is None


def test_sweep_coverage_assertion():
    assert ml_panel.assert_sweep_coverage(43734, 43734) == 1.0
    assert ml_panel.assert_sweep_coverage(990, 1000) == pytest.approx(0.99)
    with pytest.raises(ValueError):
        ml_panel.assert_sweep_coverage(980, 1000)


# ---- history (a3 / a4) ----------------------------------------------------------------------


def test_a3_a4_from_history_and_missing_on_long_gap():
    s = {k: _snap(-2 * k, {"1": 0.5 - 0.01 * k, "2": 0.3, "3": 0.7}, cap=f"h{k}")
         for k in range(1, 5)}
    si = _snap(0, MIDS, cap="c1")
    sj = _snap(2, MIDS, cap="c2")
    df, _ = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1,
                                  _hist(*(s[k] for k in range(1, 5))))
    r = df.set_index("market_id")
    assert r.loc["1", "ml_own_dmid_prev"] == pytest.approx(0.01)
    assert r.loc["1", "ml_own_prev_age_h"] == pytest.approx(2.0, abs=0.01)
    assert r.loc["1", "ml_own_n_prior"] == 4
    assert r.loc["1", "ml_own_vol"] == pytest.approx(0.01)
    assert r.loc["2", "ml_own_dmid_prev"] == 0.0 and r.loc["2", "ml_own_vol"] == 0.0
    # previous snapshot 4h before: a3 missing (NaN, not 0), and nothing older is usable either
    far = _snap(-4, MIDS, cap="h1")
    df2, _ = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, _hist(far, s[2]))
    assert df2["ml_own_dmid_prev"].isna().all() and df2["ml_own_vol"].isna().all()
    assert (df2["ml_own_n_prior"] == 0).all()
    # no history at all: missing, never 0
    df3, _ = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [])
    assert df3["ml_own_dmid_prev"].isna().all()


# ---- sidecar optional -----------------------------------------------------------------------


def _write_snapshot(d, rows: pd.DataFrame, ext: pd.DataFrame | None, status="complete"):
    d.mkdir(parents=True)
    rows.to_csv(d / "rows.csv.gz", index=False)
    if ext is not None:
        ext.to_csv(d / "rows_ext.csv.gz", index=False)
        (d / "ext_manifest.json").write_text(json.dumps({"sidecar_status": status}))


def test_sidecar_missing_stays_nan_and_present_is_joined(tmp_path):
    base = _snap(0, MIDS, cap="c1").drop(columns=ml_panel._ext_columns(), errors="ignore")
    base["volume_num"] = np.nan
    _write_snapshot(tmp_path / "old", base, None)
    old = ml_panel.load_snapshot_rows(tmp_path / "old")
    ext = base[["market_id", "received_utc"]].assign(
        order_price_min_tick_size=0.01, fee_category="crypto", fees_enabled=1.0,
        created_at=_ts(-48), volume_num=500.0)
    _write_snapshot(tmp_path / "new", base, ext)
    _write_snapshot(tmp_path / "part", base, ext, status="missing")
    new = ml_panel.load_snapshot_rows(tmp_path / "new")
    part = ml_panel.load_snapshot_rows(tmp_path / "part")
    assert old["ext_present"].iloc[0] == 0 and new["ext_present"].iloc[0] == 1
    assert part["order_price_min_tick_size"].isna().all()  # incomplete sidecar is not used
    sj = _snap(2, MIDS, cap="c2")
    d_old, _ = ml_panel.build_period(old, sj, _cap(1, 0), _cap(2, 2), 1, [])
    d_new, _ = ml_panel.build_period(new, sj, _cap(1, 0), _cap(2, 2), 1, [])
    for n in ("ml_tick_size", "ml_spread_over_tick", "ml_fees_enabled", "ml_market_age_h",
              "ml_volume_num", "ml_volume_num_delta_prev"):
        assert d_old[n].isna().all(), n
    assert (d_new["ml_tick_size"] == 0.01).all()
    assert d_new["ml_spread_over_tick"].iloc[0] == pytest.approx(2.0)
    assert d_new["ml_market_age_h"].iloc[0] == pytest.approx(48.08, abs=0.01)
    assert d_old["fee_category"].isna().all() and (d_new["fee_category"] == "crypto").all()


# ---- category -------------------------------------------------------------------------------


def test_category_policy_all_include_exclude():
    df = pd.DataFrame({"market_id": list("abcd"),
                       "fee_category": ["crypto", "sports", None, "crypto"]})
    allp, i = ml_panel.apply_category_policy(df)
    assert len(allp) == 4 and i["policy"]["mode"] == "all" and i["rows_missing_category"] == 1
    inc, i = ml_panel.apply_category_policy(df, ml_panel.category_policy("include", ["crypto"]))
    assert list(inc["market_id"]) == ["a", "d"]
    exc, i = ml_panel.apply_category_policy(df, ml_panel.category_policy("exclude", ["sports"]))
    assert list(exc["market_id"]) == ["a", "c", "d"]  # missing stays (not dropped)
    assert i["rows_kept"] == 3
    with pytest.raises(ValueError):
        ml_panel.category_policy("include", [])
    with pytest.raises(ValueError):
        ml_panel.category_policy("bogus")


# ---- fold plan ------------------------------------------------------------------------------


def _fold_frame(n_periods=20, per=3, spacing=7200.0, lag=7260.0):
    rows = []
    for p in range(n_periods):
        for r in range(per):
            t0 = 1e9 + p * spacing + r * 30.0
            rows.append({"period": p, "t0": t0, "t_i": t0, "t_j": t0 + lag,
                         "target_available": True})
    return pd.DataFrame(rows)


def test_fold_plan_structure_embargo_and_purge_exact():
    df = _fold_frame()
    plan = ml_panel.plan_folds(ml_panel.period_table(df), code_sha="x")
    assert plan["embargo_s"] == 7200.0
    assert [f["test_periods"] for f in plan["folds"]] == [[12, 13, 14, 15], [16, 17, 18, 19]]
    assert plan["unused_trailing_periods"] == []
    f0 = plan["folds"][0]
    assert f0["train_periods"] == list(range(12))
    assert f0["purge_cutoff_t"] == pytest.approx(df[df.period == 12].t0.min() - 7200.0, abs=1e-3)
    assert f0["purge_cutoff_t"] <= df[df.period == 12].t0.min() - 7200.0  # floored
    assert plan["delta_sens"] == 0.01 and plan["observed_period_spacing_s"] == 7200.0
    tr, te = ml_panel.fold_masks(df, f0)
    # exactly the training rows with t_j <= cutoff survive, independent re-derivation
    expect = (df.period < 12).to_numpy() & (df.t_j.to_numpy() <= f0["purge_cutoff_t"])
    np.testing.assert_array_equal(tr, expect)
    assert (df.loc[tr, "period"] <= 9).all()  # label lag of ~2h + embargo of one period
    assert {10, 11} & set(df.loc[tr, "period"]) == set()
    assert not (tr & te).any() and set(df.loc[te, "period"]) == {12, 13, 14, 15}
    # purge rule is the evaluate function
    np.testing.assert_array_equal(
        tr, (df.period < 12).to_numpy() & evaluate.purged_train_mask(
            df.t_j.to_numpy(), f0["purge_cutoff_t"]))
    # a label seen only after the cutoff is purged; unlabelled rows never train
    d2 = df.copy()
    d2.loc[(d2.period == 0), "target_available"] = False
    tr2, _ = ml_panel.fold_masks(d2, f0)
    assert not tr2[(d2.period == 0).to_numpy()].any()


def test_fold_plan_too_few_periods_and_partial_block():
    df = _fold_frame(n_periods=14)
    plan = ml_panel.plan_folds(ml_panel.period_table(df), code_sha="x")
    assert plan["folds"] == [] and plan["unused_trailing_periods"] == list(range(14))
    plan = ml_panel.plan_folds(ml_panel.period_table(_fold_frame(n_periods=18)), code_sha="x")
    assert len(plan["folds"]) == 1 and plan["unused_trailing_periods"] == [16, 17]


def test_fold_manifest_hash_stable_and_sensitive():
    df = _fold_frame()
    t = ml_panel.period_table(df)
    a = ml_panel.plan_folds(t, code_sha="abc")
    b = ml_panel.plan_folds(list(reversed(t)), code_sha="abc")
    c = ml_panel.plan_folds(ml_panel.period_table(df.sample(frac=1.0, random_state=3)),
                            code_sha="abc")
    assert a["manifest_sha256"] == b["manifest_sha256"] == c["manifest_sha256"]
    assert ml_panel.manifest_hash(a) == a["manifest_sha256"]
    assert json.loads(json.dumps(a)) == a
    assert ml_panel.plan_folds(t, code_sha="abd")["manifest_sha256"] != a["manifest_sha256"]
    pol = ml_panel.category_policy("exclude", ["sports"])
    assert ml_panel.plan_folds(t, policy=pol, code_sha="abc")["category_policy"] == pol
    assert ml_panel.plan_folds(t, policy=pol, code_sha="abc")["manifest_sha256"] != a[
        "manifest_sha256"]
    assert ml_panel.plan_folds(t, code_sha="abc", delta=0.01)["manifest_sha256"] != a[
        "manifest_sha256"]


# ---- orchestration with <= 3 snapshots ------------------------------------------------------


def test_build_panel_chain_uses_history_and_skips_bad_gap():
    caps = [_cap(0, 0), _cap(1, 2), _cap(2, 4), _cap(3, 9)]
    snaps = {c["capture_id"]: _snap(h, {"1": 0.5 + 0.02 * i, "2": 0.3}, cap=c["capture_id"])
             for i, (c, h) in enumerate(zip(caps, (0, 2, 4, 9), strict=True))}
    loaded = []

    def load(cap):
        loaded.append(cap["capture_id"])
        return snaps[cap["capture_id"]]

    df, counts = ml_panel.build_panel(caps, load=load)
    assert [c.get("skipped") is None for c in counts] == [True, True, False]
    assert sorted(df["period"].unique()) == [0, 1]
    p1 = df[(df.period == 1) & (df.market_id == "1")].iloc[0]
    assert p1["ml_own_dmid_prev"] == pytest.approx(0.02)
    assert loaded == ["c0", "c1", "c1", "c2", "c2", "c3"] or len(loaded) <= 6


# ---- reviewer changes -----------------------------------------------------------------------


def test_uma_nonempty_excluded_missing_flagged():
    si = _snap(0, MIDS, cap="c1")
    si["uma_resolution_statuses"] = ["[]", '["proposed"]', np.nan]
    sj = _snap(2, MIDS, cap="c2")
    df, c = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [])
    assert sorted(df["market_id"]) == ["1", "3"]
    assert c["uma_excluded"] == 1 and c["uma_unknown"] == 1
    assert df.set_index("market_id")["uma_unknown"].to_dict() == {"1": 0.0, "3": 1.0}


def test_sweep_coverage_enforced_in_build_period():
    si, sj = _snap(0, MIDS, cap="c1"), _snap(2, MIDS, cap="c2")
    with pytest.raises(ValueError):
        ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [], sweep_receipt_epoch=1.0,
                              sweep_returned=900, sweep_eligible=1000)
    with pytest.raises(ValueError):
        ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [], sweep_receipt_epoch=1.0)


def test_build_panel_applies_category_and_manifest_records_it():
    caps = [_cap(0, 0), _cap(1, 2)]
    snaps = [_snap(0, MIDS, cap="c0"), _snap(2, MIDS, cap="c1")]
    snaps[0]["fee_category"] = ["crypto", "sports", "crypto"]
    pol = ml_panel.category_policy("include", ["crypto"])
    it = iter(snaps)
    df, _ = ml_panel.build_panel(caps, load=lambda cap: next(it), policy=pol)
    assert sorted(df["market_id"]) == ["1", "3"]
    info = df.attrs["category_info"]
    assert info["rows_in"] == 3 and info["rows_kept"] == 2
    plan = ml_panel.plan_folds(ml_panel.period_table(df), category_info=info, code_sha="x")
    assert plan["category_policy"] == pol and plan["category_applied"] == info
    with pytest.raises(ValueError):
        ml_panel.plan_folds(ml_panel.period_table(df), policy=ml_panel.category_policy(),
                            category_info=info, code_sha="x")


def test_manifest_requires_code_sha_and_sane_spacing():
    t = ml_panel.period_table(_fold_frame())
    with pytest.raises(ValueError):
        ml_panel.plan_folds(t)
    with pytest.raises(ValueError):
        ml_panel.plan_folds(ml_panel.period_table(_fold_frame(spacing=3600.0)), code_sha="x")
    with pytest.raises(ValueError):
        ml_panel.plan_folds(ml_panel.period_table(_fold_frame(spacing=14400.0)), code_sha="x")


def test_negative_staleness_is_nan_and_counted():
    si = _snap(0, MIDS, cap="c1")
    si["updated_at"] = [_ts(0, 1), _ts(1), _ts(0, 1)]  # market 2 updated after receipt
    sj = _snap(2, MIDS, cap="c2")
    df, c = ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [])
    r = df.set_index("market_id")["ml_quote_staleness_h"]
    assert np.isnan(r["2"]) and r["1"] >= 0 and c["stale_negative_age"] == 1
