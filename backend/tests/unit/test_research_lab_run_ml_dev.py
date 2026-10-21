"""run_ml_dev tests: a tiny fake snapshot directory, synthetic end to end. No real data is read."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")
pytest.importorskip("lightgbm")
pytest.importorskip("pyarrow")

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_ml_dev.py"
spec = importlib.util.spec_from_file_location("run_ml_dev", SCRIPT)
rmd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rmd)

T0 = pd.Timestamp("2026-10-11T00:00:00Z")
N_MKT, N_EVENT = 160, 40


def _ts(hours: float, minutes: float = 0.0) -> str:
    return (T0 + pd.Timedelta(hours=hours, minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S.000000Z")


def _write_world(root: Path, n_snap: int, *, sidecar: bool = True, step_h: float = 2.0,
                 skip_sidecar_at: int | None = None,
                 ext_version: str = "snapshot-ext-v3") -> tuple[Path, Path]:
    rng = np.random.default_rng(3)
    snaps, sweeps = root / "snapshots", root / "book_sweeps"
    mid = rng.uniform(0.15, 0.85, N_MKT)
    ev = rng.integers(0, N_EVENT, N_MKT)
    cats = np.array(["crypto", "politics", "other"])[ev % 3]
    for k in range(n_snap):
        h = k * step_h
        cid = f"cap{k:03d}"
        d = snaps / cid
        d.mkdir(parents=True)
        mid = np.clip(mid + rng.normal(0, 0.012, N_MKT) - 0.2 * (mid - 0.5) * 0.02, 0.05, 0.95)
        rec = [_ts(h, 5 + (i % 40) / 10) for i in range(N_MKT)]
        rows = pd.DataFrame({
            "capture_id": cid, "received_utc": rec, "market_id": [f"m{i}" for i in range(N_MKT)],
            "event_id": [f"e{e}" for e in ev], "closed": False, "active": True, "binary": 1,
            "best_bid": mid - 0.01, "best_ask": mid + 0.01, "spread": 0.02, "last_trade_price": mid,
            "chg_1h": rng.normal(0, 0.01, N_MKT), "chg_1d": 0.02, "chg_1w": -0.03,
            "liquidity": 100.0 + np.arange(N_MKT), "volume24hr": 50.0,
            "end_date": "2027-01-01T00:00:00Z", "updated_at": _ts(h, 1), "neg_risk": 0,
            "neg_risk_market_id": None, "neg_risk_other": 0, "event_neg_risk_augmented": 0,
        })
        rows.to_csv(d / "rows.csv.gz", index=False)
        (d / "manifest.json").write_text(json.dumps({
            "capture_id": cid, "state": "complete", "started_utc": _ts(h),
            "finished_utc": _ts(h, 8)}))
        if sidecar and k != skip_sidecar_at:
            ext = pd.DataFrame({"market_id": rows["market_id"],
                                "received_utc": rows["received_utc"],
                                "fee_category": cats, "volume_num": 1000.0 + 10 * k})
            ext.to_csv(d / "rows_ext.csv.gz", index=False)
            (d / "ext_manifest.json").write_text(json.dumps(
                {"sidecar_status": "complete", "ext_version": ext_version}))
        if k < n_snap - 1:  # one A sweep per snapshot, 10-15 minutes after it starts
            sd = sweeps / f"sw{k:03d}"
            sd.mkdir(parents=True)
            sm = mid + rng.normal(0, 0.004, N_MKT)
            pd.DataFrame({
                "market_id": rows["market_id"], "batch_receipt_utc": _ts(h, 12),
                "book_timestamp": str(int((T0 + pd.Timedelta(hours=h, minutes=11.9)).timestamp()
                                          * 1000)),
                "best_bid": sm - 0.01, "best_ask": sm + 0.01, "bid_size_1": 100.0,
                "ask_size_1": 80.0, "depth_bid_1c": 100.0, "depth_ask_1c": 80.0,
                "depth_bid_5c": 400.0, "depth_ask_5c": 300.0, "n_bid_levels": 5,
                "n_ask_levels": 5, "state": "two_sided",
            }).to_csv(sd / "rows.csv.gz", index=False)
            (sd / "manifest.json").write_text(json.dumps({
                "sweep_id": f"sw{k:03d}", "series_index": 0, "sweep_version": "book-sweep-v1",
                "snapshot_id": cid, "state": "complete", "started_utc": _ts(h, 10),
                "finished_utc": _ts(h, 12), "tokens_requested": N_MKT,
                "tokens_returned": N_MKT}))
    return snaps, sweeps


def _args(tmp_path: Path, *extra: str) -> list[str]:
    return ["--snapshot-root", str(tmp_path / "snapshots"), "--sweep-root",
            str(tmp_path / "book_sweeps"), "--cache-root", str(tmp_path / "cache"),
            "--out-dir", str(tmp_path / "out"), "--trials-path", str(tmp_path / "trials.jsonl"),
            *extra]


def test_gate_counts_consecutive_sidecar_snapshots_and_eta(tmp_path):
    snaps, _ = _write_world(tmp_path, 10, skip_sidecar_at=4)
    caps = rmd.discover_captures(snaps)
    g = rmd.gate_status(caps, 40)
    assert g["complete_snapshots"] == 10 and g["qualifying_with_sidecar"] == 9
    assert g["longest_consecutive_run"] == 5 and g["current_run"] == 5 and not g["met"]
    assert g["remaining"] == 35 and g["eta_utc"]


def test_real_run_refused_below_gate_and_writes_nothing(tmp_path, capsys):
    _write_world(tmp_path, 10)
    rc = rmd.main(_args(tmp_path))
    assert rc == 75
    text = capsys.readouterr().out
    assert "REFUSED" in text and "10 consecutive" in text and "ETA" in text
    assert not (tmp_path / "trials.jsonl").exists() and not (tmp_path / "out").exists()


def test_dry_run_builds_panel_fits_nothing_logs_nothing(tmp_path, capsys, monkeypatch):
    _write_world(tmp_path, 12)
    from astrolabe.research_lab import ml_models

    def boom(*a, **k):
        raise AssertionError("dry run must not fit")

    monkeypatch.setattr(ml_models, "run_arm", boom)
    monkeypatch.setattr(ml_models, "run_arms", boom)
    assert rmd.main(_args(tmp_path, "--dry-run")) == 0
    out = capsys.readouterr().out
    assert "[dry-run]" in out and "K (labelled)" in out and "peak RSS" in out
    assert not (tmp_path / "trials.jsonl").exists() and not (tmp_path / "out").exists()
    s = json.loads(next((tmp_path / "cache").glob("dry_run_*.json")).read_text())
    assert s["panel"]["n_periods"] == 11 and s["folds"]["n_folds"] == 0
    assert set(s["panel"]["k_clusters_labelled"]) == {
        "event", "dep_group", "dep_group_season", "dep_group_econ", "dep_group_category_driver"}
    assert s["panel"]["feature_nan_rates"] and s["sweeps"]["used"] == 11
    # second call reuses the parquet cache (keyed by panel hash) and gives the same hash
    assert rmd.main(_args(tmp_path, "--dry-run")) == 0
    assert "(cache)" in capsys.readouterr().out
    assert len(list((tmp_path / "cache").glob("*/panel.parquet"))) == 1


def test_old_sidecar_versions_do_not_count_toward_gate(tmp_path):
    snaps, _ = _write_world(tmp_path, 8, ext_version="snapshot-ext-v2")
    g = rmd.gate_status(rmd.discover_captures(snaps), 40)
    assert g["qualifying_with_sidecar"] == 0 and g["longest_consecutive_run"] == 0
    assert rmd.sidecar_version(snaps / "cap000") == 2


def test_archived_but_complete_sidecar_counts_for_discovery(tmp_path):
    from astrolabe.research_lab import forecast

    snaps, _ = _write_world(tmp_path, 6)
    (snaps / "cap000" / "rows_ext.csv.gz").unlink()  # retention deleted it, manifest says complete
    assert rmd.sidecar_version(snaps / "cap000") == 3
    caps = rmd.discover_captures(snaps)
    assert all(c["sidecar"] for c in caps)
    assert rmd.gate_status(caps, 40)["longest_consecutive_run"] == 6
    # reading the archived sidecar is still loud (require_local guards every actual read)
    from astrolabe.research_lab import ml_panel

    with pytest.raises(forecast.ArchivedDataError):
        ml_panel.load_snapshot_rows(snaps / "cap000")


@pytest.mark.parametrize("manifest", [
    "{not json", json.dumps({"sidecar_status": "partial", "ext_version": "snapshot-ext-v3"}),
    json.dumps({"sidecar_status": "complete"}),
    json.dumps({"sidecar_status": "complete", "ext_version": "snapshot-ext-vX"})])
def test_archived_sidecar_with_bad_manifest_fails_closed(tmp_path, manifest):
    from astrolabe.research_lab import forecast

    snaps, _ = _write_world(tmp_path, 3)
    (snaps / "cap000" / "rows_ext.csv.gz").unlink()
    (snaps / "cap000" / "ext_manifest.json").write_text(manifest)
    with pytest.raises(forecast.ArchivedDataError):
        rmd.sidecar_version(snaps / "cap000")
    with pytest.raises(forecast.ArchivedDataError):
        rmd.discover_captures(snaps)
    (snaps / "cap000" / "ext_manifest.json").unlink()  # never had a sidecar: still "none"
    assert rmd.sidecar_version(snaps / "cap000") is None


def test_min_snapshots_flag_is_gone_and_env_override_is_stamped(tmp_path, monkeypatch, capsys):
    _write_world(tmp_path, 10)
    with pytest.raises(SystemExit):
        rmd.main(_args(tmp_path, "--min-snapshots", "5"))
    monkeypatch.setenv(rmd.TEST_GATE_ENV, "3")
    monkeypatch.setattr(rmd, "real_run", lambda a, c, g, p: {"_paths": [], "gate": g})
    assert rmd.main(_args(tmp_path)) == 0
    assert "OVERRIDDEN" in capsys.readouterr().err


@pytest.fixture(scope="module")
def e2e(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    mp = pytest.MonkeyPatch()
    mp.setenv(rmd.TEST_GATE_ENV, "19")
    snaps, _ = _write_world(tmp, 19)
    before = {p: p.stat().st_mtime_ns for p in snaps.rglob("*") if p.is_file()}
    assert rmd.main(_args(tmp)) == 0
    mp.undo()
    assert before == {p: p.stat().st_mtime_ns for p in snaps.rglob("*") if p.is_file()}
    rep = json.loads(next((tmp / "out").glob("ml_dev_*[0-9a-f].json")).read_text())
    lines = [json.loads(x) for x in (tmp / "trials.jsonl").read_text().splitlines()]
    return tmp, rep, lines


def test_end_to_end_development_run(e2e):
    tmp, rep, lines = e2e
    assert list((tmp / "out").glob("*.md"))
    assert list((tmp / "out").glob("*_fold_manifest.json"))
    assert rep["n_folds"] == 1 and "DEVELOPMENT" in rep["status"]
    assert rep["status"].startswith("GATE OVERRIDDEN") and rep["gate_overridden"] is True
    assert set(rep["score"]["arms"]) == {"M0", "M1", "M2", "M3_eb"}
    boot = rep["score"]["bootstrap"]
    assert {"event", "dependence_group", "dep_group_season"} <= set(boot)
    assert rep["score"]["non_inferential"] is False
    assert rep["shap"]["margins"]["up_minus_down"]["mean_abs_by_family"]
    assert 0.0 <= rep["panel"]["dep_group_no_parent_share"] <= 1.0
    fits = [x for x in lines if x["kind"] == "ml_fit"]
    assert {"M0", "M1", "M2", "M3_eb", "M0_gap_placebo", "M0_probe_sw", "M0_probe_sw_gap",
            "M1_noSweep", "M2_noSweep", "M0_placebo_leak_dmid", "M0_placebo_quote_age",
            "M1_placebo_leak_all_features", "M1_placebo_shuffled_period",
            "M0_placebo_shuffled_period_event"} <= {x["arm"] for x in fits}
    assert all(x["label"] == "DEVELOPMENT/post-hoc" and x["gate_overridden"] is True
               for x in lines)
    assert rep["accounting"]["trial_lines_written"] == len(lines)
    assert rep["accounting"]["tuning_configs_evaluated_inside_folds"]["M2"] == 20


def test_sweep_features_in_m1_m2_and_gap_out_and_lists_logged(e2e):
    _, rep, lines = e2e
    from astrolabe.research_lab import ml_models, ml_panel

    assert rep["arms_use_sweep_features"] is True and rep["sweep_gap_diagnostic_mandatory"]
    assert set(ml_panel.SWEEP_NAMES) <= set(ml_models.M12_FEATURES)
    assert set(ml_panel.SIBLING_NAMES) <= set(ml_models.M12_FEATURES)
    assert "rep_sw_gap" not in ml_models.M12_FEATURES
    assert rep["sweep_gap"]["rescore"]["all"]["loss"]["base"] > 0
    assert "gap_placebo_vs_M0" in rep["sweep_gap"]
    by_arm = {x["arm"]: x["feature_list"] for x in lines if x["kind"] == "ml_fit"}
    assert set(ml_panel.SWEEP_NAMES) <= set(by_arm["M1"]) and set(by_arm["M2"]) >= set(
        ml_panel.SWEEP_NAMES)
    assert not set(ml_panel.SWEEP_NAMES) & set(by_arm["M2_noSweep"])
    assert by_arm["M0"] == list(ml_models.M0_FEATURES)
    ns = rep["no_sweep_sensitivity"]
    assert set(ns["features_removed"]) == set(ml_panel.SWEEP_NAMES)
    assert {"M1_noSweep", "M2_noSweep"} <= set(ns["score"]["arms"])


def test_placebos_shuffled_null_leak_wins_quote_age_runs(e2e):
    _, rep, _ = e2e
    pl, ev = rep["placebos"], "event"
    for by in ("period", "period_event"):
        sh = pl[f"shuffled_labels_{by}"]["bootstrap"][ev]["log_loss"][f"M1_placebo_shuffled_{by}"]
        assert sh["rel_improvement"] < 0.01  # no gain from permuted labels
    assert set(pl["singleton_share"]) == {"period", "period_event"}
    leak = pl["leak_all_features_positive_control"]["bootstrap"][ev]["log_loss"][
        "M1_placebo_leak_all_features"]
    assert leak["rel_improvement"] > 0.2 and leak["ci95"][0] > 0  # the alarm fires
    dm = pl["leak_dmid_sanity_check"]["bootstrap"][ev]["log_loss"]["M0_placebo_leak_dmid"]
    assert dm["rel_improvement"] > 0.2
    assert "M0_placebo_quote_age" in pl["quote_age_only"]["arms"]


def test_leak_columns_use_target_snapshot_same_way_as_origin(tmp_path):
    from astrolabe.research_lab import ml_panel

    snaps, _ = _write_world(tmp_path, 4)
    caps = rmd.discover_captures(snaps)
    df, _ = ml_panel.build_panel(caps, with_leak=True)
    d = df[df["target_available"]]
    # own move over i -> j, computed from j-data exactly as ml_own_dmid_prev is from i-data
    np.testing.assert_allclose(d["leak_ml_own_dmid_prev"], d["dmid"], atol=1e-9)
    plain = ml_panel.build_panel(caps)[0]
    assert not any(c.startswith("leak_") for c in plain.columns)


def test_shuffle_is_seeded_within_blocks_and_singletons_reported():
    lab = pd.DataFrame({"period": [0] * 6 + [1] * 6, "event_id": ["a", "a", "a", "b", "b", "c"] * 2,
                        "market_id": [f"m{i}" for i in range(12)],
                        "y_class": [0.0, 1.0, 2.0, 0.0, 0.0, 2.0] * 2})
    for by, keys in (("period", ["period"]), ("period_event", ["period", "event_id"])):
        a, b = rmd.shuffle_labels(lab, by), rmd.shuffle_labels(lab, by)
        assert a["y_class"].tolist() == b["y_class"].tolist()
        for _, g in a.assign(orig=lab["y_class"]).groupby(keys):
            assert sorted(g["y_class"]) == sorted(g["orig"])
    assert rmd.singleton_share(lab, "period_event") == pytest.approx(2 / 12)
    assert rmd.singleton_share(lab, "period") == 0.0


def test_exploratory_target_run_is_separate_and_labelled(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("expl")
    mp = pytest.MonkeyPatch()
    mp.setenv(rmd.TEST_GATE_ENV, "28")
    _write_world(tmp, 28)
    assert rmd.main(_args(tmp, "--target", "dmid", "--horizon", "3")) == 0
    mp.undo()
    path = next((tmp / "out").glob("ml_dev_dmid_magnitude_h3_*[0-9a-f].json"))
    rep = json.loads(path.read_text())
    assert "EXPLORATORY" in rep["status"] and rep["horizon_snapshots"] == 3
    assert rep["embargo_s"] == 3 * 7200.0
    lines = [json.loads(x) for x in (tmp / "trials.jsonl").read_text().splitlines()]
    assert lines and all(x["target"] == "dmid_magnitude" and x["horizon_snapshots"] == 3
                         and x["evidence_status"] == "EXPLORATORY" for x in lines)
    assert not list((tmp / "out").glob("ml_dev_2*.md"))  # no primary-style report written


def test_families_dry_run_reports_coverage_and_marks_exploratory(tmp_path, capsys):
    _write_world(tmp_path, 12)
    h, mk = 3 * 2.0, [f"m{i}" for i in range(20)]
    root = tmp_path / "trade_samples" / "20261011T080000Z_abcd1234"
    root.mkdir(parents=True)
    members = [{"market_id": m, "condition_id": "c" + m, "stratum": "L0-S0", "token0": "t0",
                "origin_utc": _ts(h, 5 + (i % 40) / 10), "inclusion_prob": "1/8",
                "inclusion_float": 0.125} for i, m in enumerate(mk)]
    (root / "plan.json").write_text(json.dumps(
        {"sample_id": root.name, "snapshot_id": "cap003", "sample": members, "frame_size": 160}))
    (root / "manifest.json").write_text(json.dumps({"state": "complete"}))
    pd.DataFrame({"market_id": mk, "n_returned": 3, "status": "ok"}).to_csv(
        root / "features.csv.gz", index=False)
    ts = int((T0 + pd.Timedelta(hours=h)).timestamp()) + 60  # before every origin
    pd.DataFrame([{"market_id": m, "condition_id": "c" + m, "ts": ts, "side": "BUY",
                   "outcome_index": 0, "asset": "t0", "size": 5.0, "price": 0.5,
                   "wallet_hash": "w1"} for m in mk]).to_csv(root / "wallets.csv.gz", index=False)
    rc = rmd.main(_args(tmp_path, "--dry-run", "--families", "market_state,flow,wallet",
                        "--sample-root", str(tmp_path / "trade_samples")))
    assert rc == 0
    out = capsys.readouterr().out
    assert "family flow (exploratory_family)" in out and "family market_state (MC1)" in out
    s = json.loads(next((tmp_path / "cache").glob("dry_run_*.json")).read_text())
    assert s["families"]["flow"]["exploratory_family"] is True
    assert s["families"]["flow"]["sampled_rows"] == 20
    assert s["families"]["market_state"]["exploratory_family"] is False
    assert s["families"]["_join"]["captures_with_sample"] == 1
    assert not (tmp_path / "trials.jsonl").exists()
    with pytest.raises(SystemExit):
        rmd.parse_families("market_state,news")
    assert rmd.parse_families("market_state") == []


def test_primary_run_lines_carry_evidence_role(e2e):
    _, rep, lines = e2e
    assert lines and all(x["evidence_role"] in ("exploratory_dev", "placebo") for x in lines)
    assert any(x["evidence_role"] == "placebo" for x in lines)
    assert any(x["evidence_role"] == "exploratory_dev" for x in lines)
    assert "dep_group_econ" in rep["panel"]["k_clusters_labelled"]
