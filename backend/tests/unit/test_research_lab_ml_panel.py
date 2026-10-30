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


# ---- extended features: sweep (a11), sibling (a10), dependence groups ------------------------


def _sweep_dir(root, sid, idx, snap, *, start_h, end_h, bid_size=100.0, req=3, ret=3,
               state="complete"):
    d = root / sid
    d.mkdir(parents=True)
    man = {"sweep_id": sid, "series_index": idx, "snapshot_id": snap, "state": state,
           "sweep_version": "book-sweep-v1", "tokens_requested": req, "tokens_returned": ret,
           "started_utc": _ts(start_h), "finished_utc": _ts(end_h)}
    (d / "manifest.json").write_text(json.dumps(man))
    rows = pd.DataFrame({
        "market_id": ["1", "2", "3"], "batch_receipt_utc": _ts(end_h),
        "book_timestamp": str(int((T0 + pd.Timedelta(hours=end_h, seconds=-5)).timestamp() * 1000)),
        "best_bid": [0.49, 0.29, np.nan], "best_ask": [0.52, 0.31, 0.72],
        "bid_size_1": [bid_size, 50.0, np.nan], "ask_size_1": [100.0, 50.0, 10.0],
        "depth_bid_1c": [bid_size, 50.0, np.nan], "depth_ask_1c": [100.0, 50.0, 10.0],
        "depth_bid_5c": [300.0, 80.0, np.nan], "depth_ask_5c": [100.0, 90.0, 10.0],
        "n_bid_levels": [5, 3, 0], "n_ask_levels": [4, 3, 1],
        "state": ["two_sided", "two_sided", "one_sided"],
    })
    rows.to_csv(d / "rows.csv.gz", index=False)
    return d


def test_pick_sweeps_declares_A_and_applies_coverage(tmp_path):
    _sweep_dir(tmp_path, "sA", 0, "c1", start_h=0.12, end_h=0.2, bid_size=100.0)
    _sweep_dir(tmp_path, "sB", 1, "c1", start_h=0.21, end_h=0.3, bid_size=999.0)
    _sweep_dir(tmp_path, "sLow", 0, "c9", start_h=0.1, end_h=0.2, req=1000, ret=980)
    _sweep_dir(tmp_path, "sInc", 0, "c8", start_h=0.1, end_h=0.2, state="incomplete:x")
    use, rep = ml_panel.pick_sweeps(tmp_path)
    assert list(use) == ["c1"] and use["c1"]["sweep_id"] == "sA"
    assert rep["not_a_sweep"] == 1 and rep["low_coverage"] == ["sLow"] and rep["not_complete"] == 1
    rows = ml_panel.load_sweep_rows(use["c1"])
    col = ml_panel.sweep_columns(np.array(["1", "2", "3", "zz"]), rows)
    assert list(col["sw_bid_size_1"][:2]) == [100.0, 50.0]  # A, never B's 999
    assert np.isnan(col["sw_bid_size_1"][2]) and np.isnan(col["sw_best_bid"][3])  # NaN, not 0
    assert col["sw_book_age_s"][0] == pytest.approx(5.0)
    assert np.isnan(col["sw_mid"][2])  # one-sided: no mid


def test_sweep_features_joined_relative_to_sweep_mid_and_gap_is_report_only(tmp_path):
    _sweep_dir(tmp_path, "sA", 0, "c1", start_h=0.12, end_h=0.2)
    use, _ = ml_panel.pick_sweeps(tmp_path)
    e = use["c1"]
    si, sj = _snap(0, MIDS, cap="c1"), _snap(2, MIDS, cap="c2")
    df, c = ml_panel.build_period(
        si, sj, _cap(1, 0), _cap(2, 2), 1, [], sweep_receipt_epoch=e["receipt_epoch"],
        sweep_returned=e["returned"], sweep_eligible=e["eligible"],
        sweep_rows=ml_panel.load_sweep_rows(e), sweep_started_epoch=e["started_epoch"])
    r = df.set_index("market_id")
    assert r.loc["1", "ml_sw_imb_top"] == 0.0
    assert r.loc["1", "ml_sw_imb_5c"] == pytest.approx(0.5)
    micro = (0.52 * 100 + 0.49 * 100) / 200 - (0.49 + 0.52) / 2
    assert r.loc["1", "ml_sw_microprice_disp"] == pytest.approx(micro)
    assert np.isnan(r.loc["3", "ml_sw_imb_top"])  # one-sided book stays NaN
    assert r.loc["1", "rep_sw_gap"] == pytest.approx(0.505 - 0.5)
    assert c["sweep_book_rows"] == 2
    assert not any("gap" in n for n in ml_panel.EXTENDED_NAMES) and "rep_sw_gap" not in (
        ml_panel.EXTENDED_NAMES)
    # t0 moved to the sweep receipt, target stays Gamma mid to Gamma mid
    assert (df["t0"] >= e["receipt_epoch"]).all()
    assert df.loc[df.market_id == "1", "mid_j"].iloc[0] == pytest.approx(0.5)
    with pytest.raises(ValueError):  # the gap and group ids can never be registered as features
        ml_panel.register_ml(FeatureSpec("ml_bad", "x", "v", lambda o: o["rep_sw_gap"],
                                         ("rep_sw_gap",)))
    with pytest.raises(ValueError):
        ml_panel.register_ml(FeatureSpec("ml_bad2", "x", "v", lambda o: o["dep_group"],
                                         ("dep_group",)))


def test_sweep_timing_guards_in_build_period(tmp_path):
    d = _sweep_dir(tmp_path, "sA", 0, "c1", start_h=0.1, end_h=0.2)
    rows = ml_panel.load_sweep_rows({"dir": str(d)})
    si, sj = _snap(0, MIDS, cap="c1"), _snap(2, MIDS, cap="c2")
    kw = dict(sweep_returned=3, sweep_eligible=3, sweep_rows=rows)
    late = float(pd.Timestamp(_ts(2.5)).timestamp())
    with pytest.raises(ValueError, match="after the target"):
        ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [], sweep_receipt_epoch=late, **kw)
    early_start = float(pd.Timestamp(_ts(-1)).timestamp())
    with pytest.raises(ValueError, match="before the origin"):
        ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [], sweep_receipt_epoch=1.0,
                              sweep_started_epoch=early_start, **kw)
    with pytest.raises(ValueError, match="needs sweep_receipt_epoch"):
        ml_panel.build_period(si, sj, _cap(1, 0), _cap(2, 2), 1, [], **kw)


def test_extended_features_and_groups_ignore_everything_in_j(tmp_path):
    d = _sweep_dir(tmp_path, "sA", 0, "c1", start_h=0.1, end_h=0.2)
    rows = ml_panel.load_sweep_rows({"dir": str(d)})
    e = {"receipt_epoch": float(pd.Timestamp(_ts(0.2)).timestamp())}
    prev = _snap(-2, {"1": 0.48, "2": 0.30, "3": 0.72}, cap="c0")
    si = _snap(0, MIDS, cap="c1", event_id="A")  # one event: siblings exist
    sj_a = _snap(2, {"1": 0.55, "2": 0.30, "3": 0.60}, cap="c2", event_id="A")
    sj_b = _snap(2, {"1": 0.40, "2": 0.45, "3": 0.65}, cap="c2", liquidity=7.0, event_id="zzz",
                 neg_risk_market_id="N9", chg_1h=0.5)
    kw = dict(sweep_receipt_epoch=e["receipt_epoch"], sweep_returned=3, sweep_eligible=3,
              sweep_rows=rows)
    a, _ = ml_panel.build_period(si, sj_a, _cap(1, 0), _cap(2, 2), 1, _hist(prev), **kw)
    b, _ = ml_panel.build_period(si, sj_b, _cap(1, 0), _cap(2, 2), 1, _hist(prev), **kw)
    cols = [*ml_panel.EXTENDED_NAMES, "dep_group", "dep_group_fallback", "rep_sw_gap"]
    pd.testing.assert_frame_equal(a[cols], b[cols])
    assert a["ml_sib_mean_abs_dmid"].notna().all() and a["ml_sw_imb_top"].notna().any()


def _hist1(mids: dict[str, float], hours=-2.0):
    t = float(pd.Timestamp(_ts(hours)).timestamp())
    return pd.DataFrame({"mid": list(mids.values()), "t": [t] * len(mids)},
                        index=pd.Index(list(mids), name="market_id"))


def test_sibling_moves_exclude_self_and_use_nan_when_no_sibling():
    si = _snap(0, {"1": 0.60, "2": 0.32, "3": 0.74, "4": 0.50, "5": 0.50}, cap="c1")
    si["event_id"] = ["A", "A", "A", "B", "C"]
    si["neg_risk_market_id"] = [None, None, None, None, "NR"]
    h = _hist1({"1": 0.50, "2": 0.30, "3": 0.70, "4": 0.40, "5": 0.40})
    out = ml_panel.sibling_moves(si, h, np.array(["1", "2", "3", "4", "5", "9"]))
    # market 1 (d=.10): siblings 2 (.02), 3 (.04); self excluded from mean and max
    assert out.loc[0, "sib_mean_abs_dmid"] == pytest.approx(0.03)
    assert out.loc[0, "sib_max_abs_dmid"] == pytest.approx(0.04)
    # market 2 (d=.02): siblings 1 (.10) and 3 (.04)
    assert out.loc[1, "sib_mean_abs_dmid"] == pytest.approx(0.07)
    assert out.loc[1, "sib_max_abs_dmid"] == pytest.approx(0.10)
    # singletons (event B, neg-risk group NR) and an unknown market: NaN, never 0 or self
    assert out.loc[[3, 4, 5]].isna().all().all()
    # no history: all NaN
    assert ml_panel.sibling_moves(si, None, np.array(["1"])).isna().all().all()
    # a sibling with a stale link (> 3h) does not count
    h2 = _hist1({"1": 0.50, "2": 0.30, "3": 0.70}, hours=-4.0)
    assert ml_panel.sibling_moves(si, h2, np.array(["1"])).isna().all().all()


def test_sibling_max_handles_ties_for_self():
    si = _snap(0, {"1": 0.60, "2": 0.60, "3": 0.50}, cap="c1")
    si["event_id"] = "A"
    h = _hist1({"1": 0.50, "2": 0.50, "3": 0.50})
    out = ml_panel.sibling_moves(si, h, np.array(["1", "3"]))
    assert out.loc[0, "sib_max_abs_dmid"] == pytest.approx(0.10)  # the other tied sibling
    assert out.loc[1, "sib_max_abs_dmid"] == pytest.approx(0.10)
    assert out.loc[1, "sib_mean_abs_dmid"] == pytest.approx(0.10)


def test_dependence_groups_use_pairing_and_flag_fallback(monkeypatch):
    from astrolabe.research_panel import pairing

    calls = []
    real = pairing.dependence_groups
    monkeypatch.setattr(pairing, "dependence_groups",
                        lambda *a, **k: calls.append(1) or real(*a, **k))
    new = _snap(0, {"10": 0.5, "11": 0.5, "12": 0.5}, cap="c1")
    new["ext_present"] = 1.0
    new["fee_category"] = "politics"
    new["event_ids"] = ['["E1"]', '["E2"]', '["E3"]']
    new["series_slugs"] = ['["s-x"]', '["s-x"]', None]  # series links E1 and E2
    new["neg_risk_market_id"] = [None, None, "NR1"]
    g = ml_panel.dependence_group_ids(new, np.array(["10", "11", "12"]))
    assert calls and g["dep_group"][0] == g["dep_group"][1] != g["dep_group"][2]
    assert g["dep_group_fallback"].tolist() == [0.0, 0.0, 0.0]
    old = _snap(0, {"10": 0.5, "11": 0.5, "12": 0.5}, cap="c1")
    old["event_id"] = ["E1", "E1", "E3"]
    old["neg_risk_market_id"] = [None, None, "NR1"]
    old["ext_present"] = 0.0
    g2 = ml_panel.dependence_group_ids(old, np.array(["10", "11", "12"]))
    assert g2["dep_group_fallback"].tolist() == [1.0, 1.0, 1.0]  # event id only, flagged
    assert g2["dep_group"][0] == g2["dep_group"][1] != g2["dep_group"][2]
    assert "dep_group" not in ml_panel.EXTENDED_NAMES


def test_build_panel_pools_groups_across_periods_and_joins_declared_sweeps(tmp_path):
    caps = [{"capture_id": f"c{k}", "started_utc": _ts(2.0 * k), "dir": ""} for k in range(3)]
    snaps = {
        "c0": _snap(0, {"1": 0.5, "2": 0.3}, cap="c0"),
        "c1": _snap(2, {"1": 0.5, "2": 0.3}, cap="c1"),
        "c2": _snap(4, {"1": 0.5, "2": 0.3}, cap="c2"),
    }
    snaps["c0"]["event_id"] = ["A", "B"]  # period 0: markets 1, 2 apart
    snaps["c1"]["event_id"] = ["A", "A"]  # period 1: together
    snaps["c2"]["event_id"] = ["A", "B"]
    d = _sweep_dir(tmp_path, "sA", 0, "c1", start_h=2.1, end_h=2.2)
    use, _ = ml_panel.pick_sweeps(tmp_path)
    df, counts = ml_panel.build_panel(caps, load=lambda cap: snaps[cap["capture_id"]],
                                      sweep_receipts=use)
    assert d.exists()
    assert df["dep_group"].nunique() == 1  # period 1 joins them; pooled over the panel
    assert df.groupby("period")["dep_group_period"].nunique().tolist() == [2, 1]
    assert (df["dep_group_fallback"] == 1.0).all()
    p1 = df[df.period == 1]
    assert p1["ml_sw_imb_top"].notna().any()
    assert df[df.period == 0]["ml_sw_imb_top"].isna().all()  # no sweep declared for c0


# ---- review fixes: underlying x date, sweep-gap diagnostic, unmatched markets ----------------


def _crypto_snap():
    s = _snap(0, {"20": 0.5, "21": 0.5, "22": 0.5, "23": 0.5}, cap="c1")
    s["ext_present"], s["fee_category"] = 1.0, "crypto"
    s["event_ids"] = ['["E1"]', '["E2"]', '["E3"]', '["E4"]']
    s["series_slugs"] = ['["btc-up-down"]', '["bitcoin-daily"]', '["btc-hourly"]', '["politics"]']
    s["end_date"] = ["2026-10-12T16:00:00Z", "2026-10-12T20:00:00Z", "2026-10-13T16:00:00Z",
                     "2026-10-12T16:00:00Z"]
    return s


def test_underlying_date_node_groups_same_day_only():
    s = _crypto_snap()
    ids = np.array(["20", "21", "22", "23"])
    on = ml_panel.dependence_group_ids(s, ids)["dep_group"].tolist()
    off = ml_panel.dependence_group_ids(s, ids, underlying_date=False)["dep_group"].tolist()
    assert on[0] == on[1]  # btc / bitcoin, same UTC day
    assert on[2] != on[0] and on[3] != on[0]  # other day, non-crypto
    assert len(set(off)) == 4  # off: separate events and distinct series
    assert ml_panel.DEP_GROUP_UNDERLYING is True


def test_unmatched_market_gets_flagged_singleton_group():
    s = _crypto_snap()
    g = ml_panel.dependence_group_ids(s, np.array(["20", "nope"]))
    assert g["dep_group"].notna().all() and g["dep_group"][1] == "g:u:nope"
    assert g["dep_group_unmatched"].tolist() == [0.0, 1.0]
    pooled = ml_panel.pool_dependence_groups(pd.DataFrame(
        {"market_id": ["20", "21"], "period": [0, 0], "dep_group": ["g:20", "g:20"]}))
    assert pooled.notna().all()


def test_sweep_gap_diagnostic_and_rescore_hook():
    rng = np.random.default_rng(0)
    gap = rng.normal(0, 0.01, 200)
    df = pd.DataFrame({"rep_sw_gap": gap, "ml_sw_imb_top": gap * 2 + rng.normal(0, 1e-4, 200),
                       "ml_sw_spread": rng.normal(size=200), "b": rng.normal(size=200)})
    d = ml_panel.sweep_gap_diagnostic(df, ["ml_sw_imb_top", "ml_sw_spread"])
    assert d["features"]["ml_sw_imb_top"]["pearson"] > 0.99 and d["n_gap"] == 200
    assert abs(d["features"]["ml_sw_spread"]["pearson"]) < 0.3
    seen = []

    def score(d_, cols):
        seen.append(tuple(cols))
        return 1.0 - 0.1 * ("ml_sw_imb_top" in cols) - 0.1 * ("rep_sw_gap" in cols)

    r = ml_panel.rescore_with_gap_control(df, ["b"], score, ["ml_sw_imb_top"])
    assert r["all"]["gain_sweep"] == pytest.approx(0.1)
    assert r["all"]["gain_sweep_given_gap"] == pytest.approx(0.1)
    assert ("b", "ml_sw_imb_top", "rep_sw_gap") in seen
    assert "abs_gap_lt_0025" in r


def test_fixture_day_groups_vs_season_sensitivity_and_parent_flag():
    s = _snap(0, {"30": 0.5, "31": 0.5, "32": 0.5, "33": 0.5, "34": 0.5}, cap="c1")
    s["ext_present"], s["fee_category"] = 1.0, "sports"
    s["event_ids"] = ['["G1"]', '["G1P"]', '["G2"]', '["G3"]', '["G4"]']
    s["series_slugs"] = ['["nfl-2026"]'] * 4 + [None]
    s["end_date"] = ["2026-10-11T17:00:00Z", "2026-10-11T17:00:00Z", "2026-10-11T20:00:00Z",
                     "2026-10-18T17:00:00Z", "2026-10-11T17:00:00Z"]
    ids = np.array(["30", "31", "32", "33", "34"])
    g = ml_panel.dependence_group_ids(s, ids)
    assert g["dep_group_season"].iloc[:4].nunique() == 1  # whole season in one group
    assert g["dep_group_season"][4] != g["dep_group_season"][0]
    fd = g["dep_group"].tolist()  # no v3 column: series x day only, flagged
    assert fd[0] == fd[1] == fd[2] and fd[3] != fd[0] and fd[4] != fd[0]
    assert g["dep_group_no_parent"].tolist() == [1.0] * 5
    s["parent_event_ids"] = ['[null]', '["G1"]', '[null]', '[null]', '["G3"]']
    g2 = ml_panel.dependence_group_ids(s, ids)
    assert g2["dep_group_no_parent"].tolist() == [0.0] * 5
    fd2 = g2["dep_group"].tolist()
    assert fd2[4] == fd2[3]  # parent G3 links the series-less satellite to the other-day game
    assert fd2[3] != fd2[0] and fd2[0] == fd2[1]  # other day stays apart; G1P joins G1
