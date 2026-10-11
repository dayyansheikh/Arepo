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
                 skip_sidecar_at: int | None = None) -> tuple[Path, Path]:
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
            (d / "ext_manifest.json").write_text(json.dumps({"sidecar_status": "complete"}))
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
    assert rc == 2
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
    assert set(s["panel"]["k_clusters_labelled"]) == {"event", "dep_group", "dep_group_season"}
    assert s["panel"]["feature_nan_rates"] and s["sweeps"]["used"] == 11
    # second call reuses the parquet cache (keyed by panel hash) and gives the same hash
    assert rmd.main(_args(tmp_path, "--dry-run")) == 0
    assert "(cache)" in capsys.readouterr().out
    assert len(list((tmp_path / "cache").glob("*/panel.parquet"))) == 1


def test_end_to_end_development_run(tmp_path):
    snaps, _ = _write_world(tmp_path, 19)
    before = {p: p.stat().st_mtime_ns for p in snaps.rglob("*") if p.is_file()}
    assert rmd.main(_args(tmp_path, "--min-snapshots", "19")) == 0
    assert before == {p: p.stat().st_mtime_ns for p in snaps.rglob("*") if p.is_file()}
    rep = json.loads(next((tmp_path / "out").glob("ml_dev_*[0-9a-f].json")).read_text())
    assert list((tmp_path / "out").glob("*.md"))
    assert list((tmp_path / "out").glob("*_fold_manifest.json"))
    assert rep["n_folds"] == 1 and "DEVELOPMENT" in rep["status"]
    arms = rep["score"]["arms"]
    assert set(arms) == {"M0", "M1", "M2", "M3_eb"}
    boot = rep["score"]["bootstrap"]
    assert {"event", "dependence_group", "dep_group_season"} <= set(boot)
    assert rep["score"]["non_inferential"] is False
    assert rep["shap"]["margins"]["up_minus_down"]["mean_abs_by_family"]
    sg = rep["sweep_gap"]
    assert sg["rescore"]["all"]["loss"]["base"] > 0 and "gap_placebo_vs_M0" in sg
    assert rep["arms_use_sweep_features"] is False
    pl = rep["placebos"]
    ev = "event"
    shuf = pl["shuffled_labels"]["bootstrap"][ev]["log_loss"]["M1_placebo_shuffled"]
    assert shuf["rel_improvement"] < 0.01  # no gain from permuted labels
    leak = pl["leak_positive_control"]["bootstrap"][ev]["log_loss"]["M0_placebo_leak"]
    assert leak["rel_improvement"] > 0.2 and leak["ci95"][0] > 0  # the leak alarm fires
    assert "M0_placebo_quote_age" in pl["quote_age_only"]["arms"]
    lines = [json.loads(x) for x in (tmp_path / "trials.jsonl").read_text().splitlines()]
    fits = [x for x in lines if x["kind"] == "ml_fit"]
    assert {x["arm"] for x in fits} == {"M0", "M1", "M2", "M3_eb", "M0_gap_placebo",
                                         "M0_probe_sw", "M0_probe_sw_gap", "M0_placebo_shuffled",
                                         "M1_placebo_shuffled",
                                         "M0_placebo_leak", "M0_placebo_quote_age"}
    assert all(x["label"] == "DEVELOPMENT/post-hoc" for x in lines)
    assert rep["accounting"]["trial_lines_written"] == len(lines)
    assert rep["accounting"]["tuning_configs_evaluated_inside_folds"]["M2"] == 20


def test_shuffle_is_seeded_within_period_event_blocks():
    lab = pd.DataFrame({"period": [0] * 6 + [1] * 6, "event_id": ["a", "a", "a", "b", "b", "b"] * 2,
                        "market_id": [f"m{i}" for i in range(12)],
                        "y_class": [0.0, 1.0, 2.0, 0.0, 0.0, 2.0] * 2})
    a, b = rmd.shuffle_labels(lab), rmd.shuffle_labels(lab)
    assert a["y_class"].tolist() == b["y_class"].tolist()
    for _, g in a.assign(orig=lab["y_class"]).groupby(["period", "event_id"]):
        assert sorted(g["y_class"]) == sorted(g["orig"])
