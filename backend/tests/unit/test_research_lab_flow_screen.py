"""Flow-screen tests on synthetic samples and snapshots (no data-dumps access)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import flow_screen as fs

T0 = pd.Timestamp("2026-10-11T00:00:00Z")
N = 60


def _snap_rows(cap: str, start: pd.Timestamp, mids: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame({
        "capture_id": cap, "capture_start_utc": start.isoformat(),
        "received_utc": (start + pd.Timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "market_id": [str(i) for i in range(N)], "condition_id": [f"0x{i}" for i in range(N)],
        "event_id": [str(i // 2) for i in range(N)], "closed": False, "active": True,
        "binary": 1, "best_bid": mids - 0.01, "best_ask": mids + 0.01, "spread": 0.02,
        "last_trade_price": mids, "chg_1h": np.linspace(-0.02, 0.02, N), "chg_1d": 0.0,
        "chg_1w": 0.0, "liquidity": 1000.0, "volume24hr": 50.0,
        "end_date": "2027-01-01T00:00:00Z",
    })


def _write_snap(root: Path, cap: str, start: pd.Timestamp, state: str, mids) -> None:
    d = root / cap
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps(
        {"capture_id": cap, "state": state, "started_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ")}))
    _snap_rows(cap, start, mids).to_csv(d / "rows.csv.gz", index=False)


def _write_sample(root: Path, sid: str, src: str, incl: float = 0.25) -> Path:
    d = root / sid
    d.mkdir(parents=True)
    ids = [str(i) for i in range(N)]
    (d / "manifest.json").write_text(json.dumps(
        {"sample_id": sid, "state": "complete", "snapshot_id": src}))
    plan = {"sample": [{"market_id": m, "inclusion_float": incl * (1 + (int(m) % 2))}
                       for m in ids]}
    (d / "plan.json").write_text(json.dumps(plan))
    origin = (T0 + pd.Timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    rng = np.random.default_rng(0)
    vol = rng.integers(0, 5, N).astype(float)
    f = pd.DataFrame({
        "market_id": ids, "origin_utc": origin, "status": "ok",
        "n_trades_1h": (vol > 0).astype(int) * 3, "volume_1h": vol,
        "signed_volume_1h": vol * 0.5, "max_trade_size_1h": vol / 2,
        "time_since_last_trade_s": np.where(vol > 0, 100.0, np.nan),
        "trades_truncated": False,
    })
    f.to_csv(d / "features.csv.gz", index=False)
    with gzip.open(d / "trades.csv.gz", "wt") as fh:
        fh.write("market_id\n")
    return d


@pytest.fixture
def world(tmp_path):
    snaps, samples = tmp_path / "snaps", tmp_path / "samples"
    mid0 = np.full(N, 0.5)
    chg = np.linspace(-0.02, 0.02, N)
    _write_snap(snaps, "c1", T0, "complete", mid0)
    _write_snap(snaps, "c2", T0 + pd.Timedelta(hours=1), "incomplete", mid0 + 0.5)
    _write_snap(snaps, "c3", T0 + pd.Timedelta(hours=2), "complete", mid0 - 0.3 * chg)
    _write_sample(samples, "s1", "c1")
    return snaps, samples


def test_pairs_to_next_complete_snapshot_only(world):
    snaps, samples = world
    pairs, counts = fs.build_all(samples, snaps)
    assert counts[0]["target_snapshot"] == "c3"  # incomplete c2 skipped
    assert len(pairs) == N and pairs["horizon_h"].between(1.99, 2.0).all()
    np.testing.assert_allclose(pairs["dmid"], -0.3 * np.linspace(-0.02, 0.02, N), atol=1e-12)


def test_no_subsequent_snapshot_is_skipped(tmp_path):
    snaps, samples = tmp_path / "snaps", tmp_path / "samples"
    _write_snap(snaps, "c1", T0, "complete", np.full(N, 0.5))
    _write_sample(samples, "s1", "c1")
    pairs, counts = fs.build_all(samples, snaps)
    assert pairs.empty and "no subsequent" in counts[0]["skipped"]


def test_weights_are_inverse_inclusion_probability(world):
    snaps, samples = world
    pairs, _ = fs.build_all(samples, snaps)
    odd = pairs["market_id"].astype(int) % 2 == 1
    assert np.allclose(pairs.loc[~odd, "w"], 4.0) and np.allclose(pairs.loc[odd, "w"], 2.0)
    assert abs(pairs["w"].sum() - (N / 2) * 4 - (N / 2) * 2) < 1e-9


def test_flow_features_origin_scaled_and_flagged(world):
    snaps, samples = world
    pairs, _ = fs.build_all(samples, snaps)
    z = pairs[pairs["log_volume_1h"] == 0]
    assert (z["signed_share"] == 0).all() and (z["tsl_missing"] == 1).all()
    nz = pairs[pairs["log_volume_1h"] > 0]
    np.testing.assert_allclose(nz["signed_share"], 0.5)
    assert (nz["tsl_missing"] == 0).all()
    assert not set(pairs.columns[pairs.columns.str.startswith("origin_utc")])


def test_origin_time_mismatch_dropped(world):
    snaps, samples = world
    p = samples / "s1" / "features.csv.gz"
    f = pd.read_csv(p, dtype={"market_id": str})
    f.loc[0, "origin_utc"] = "2026-10-11T05:00:00.000000Z"
    f.to_csv(p, index=False)
    pairs, counts = fs.build_all(samples, snaps)
    assert counts[0]["dropped_origin_time_mismatch"] == 1 and len(pairs) == N - 1


def test_target_columns_refused():
    for bad in ("dmid", "mid_j", "t_j", "horizon_h"):
        with pytest.raises(ValueError):
            fs.assert_origin_only(("chg_1h", bad))
    for v in fs.FAMILY.values():
        fs.assert_origin_only(v["features"])


def test_family_prelisted():
    assert list(fs.FAMILY) == ["F1_signed_share", "F2a_activity_trades", "F2b_activity_volume",
                               "F3_staleness", "F4_max_trade"]
    assert fs.FROZEN_COEF == -0.331610
    for tag in ("F1", "F2", "F3", "F4"):
        assert tag in fs.__doc__


def _synthetic_pairs(n=400, seed=1):
    rng = np.random.default_rng(seed)
    c = rng.normal(0, 0.02, n)
    d = {"market_id": [str(i) for i in range(n)], "event_id": [str(i // 2) for i in range(n)],
         "period": (np.arange(n) % 2), "chg_1h": c, "dmid": -0.3 * c + rng.normal(0, 0.01, n),
         "horizon_h": 2.0, "w": rng.uniform(1, 5, n), "sample_id": "s"}
    for k in fs.FLOW_COLS:
        d[k] = rng.normal(size=n)
    return pd.DataFrame(d)


def test_crossfit_and_bootstrap_deterministic():
    p = _synthetic_pairs()
    a = fs.crossfit_ridge(p, ("chg_1h", "signed_share"))
    b = fs.crossfit_ridge(p, ("chg_1h", "signed_share"))
    np.testing.assert_array_equal(a, b)
    assert np.isfinite(a).all()
    r1 = fs.run_screen(p, n_boot=50, seed=116)
    r2 = fs.run_screen(p, n_boot=50, seed=116)
    assert fs.clean(r1) == fs.clean(r2)
    assert set(r1["variants"]) == set(fs.FAMILY)
    e = r1["effective_sample"]
    assert e["pairs"] == 400 and e["events"] == 200 and e["sample_periods"] == 2


def test_delta_r2_weighting():
    y = np.array([1.0, 1.0])
    yb, yv = np.array([0.0, 0.0]), np.array([1.0, 0.0])
    # base sse = [1,1], var sse = [0,1], sse0 = [1,1]
    assert fs.delta_r2(y, yb, yv, np.array([1.0, 1.0])) == pytest.approx(0.5)
    assert fs.delta_r2(y, yb, yv, np.array([3.0, 1.0])) == pytest.approx(0.75)


def test_signal_detected_when_planted():
    p = _synthetic_pairs(1200, seed=2)
    p["dmid"] = p["dmid"] + 0.02 * p["signed_share"]
    r = fs.run_screen(p, n_boot=100, seed=116)["variants"]["F1_signed_share"]
    assert r["vs_ridge"]["unweighted"]["ci_lo"] > 0


# --- archive-aware pair cache (raw files removed after archiving) -----------------------------


def _drop_raw(snaps: Path, samples: Path, *, keep_cache: bool = True) -> None:
    for p in list(snaps.glob("*/rows.csv.gz")) + list(samples.glob("*/features.csv.gz")):
        p.unlink()
    for p in samples.glob("*/trades.csv.gz"):
        p.unlink()


def test_pair_cache_replays_identical_frame_after_raw_removal(world):
    snaps, samples = world
    before, counts_before = fs.build_all(samples, snaps)
    st = fs.pair_cache_status(samples, snaps)
    assert st["samples_with_target"] == 1 and st["cached"] == 1
    assert st["complete_samples"] == 1 and not st["complete"]  # span is written by e007
    from astrolabe.research_lab import e007

    f = pd.read_csv(samples / "s1" / "features.csv.gz", dtype={"market_id": str})
    f["sent_utc"] = "2026-10-11T00:01:00Z"
    f.to_csv(samples / "s1" / "features.csv.gz", index=False)
    e007.list_metas(samples)
    assert fs.pair_cache_status(samples, snaps)["complete"]
    _drop_raw(snaps, samples)
    after, counts_after = fs.build_all(samples, snaps)
    pd.testing.assert_frame_equal(before, after)
    assert counts_before == counts_after


def test_pair_cache_restamps_period(world):
    snaps, samples = world
    caps = fs.forecast.list_complete_captures(snaps)
    first, _ = fs.build_sample_pairs(samples / "s1", caps, 0)
    _drop_raw(snaps, samples)
    again, cnt = fs.build_sample_pairs(samples / "s1", caps, 5)
    assert (again["period"] == 5).all() and cnt["period"] == 5
    assert (first["period"] == 0).all()
    pd.testing.assert_frame_equal(first.drop(columns="period"), again.drop(columns="period"))


def test_missing_raw_without_cache_raises_clear_error(world):
    snaps, samples = world
    _drop_raw(snaps, samples)
    with pytest.raises(fs.forecast.ArchivedDataError, match="restore_from_archive"):
        fs.build_all(samples, snaps)


def test_cache_not_used_while_raw_present(world, monkeypatch):
    snaps, samples = world
    fs.build_all(samples, snaps)
    calls = []
    orig = fs._compute_sample_pairs

    def spy(*a, **k):
        calls.append(1)
        return orig(*a, **k)

    monkeypatch.setattr(fs, "_compute_sample_pairs", spy)
    fs.build_all(samples, snaps)
    assert calls == [1]  # raw files present -> recomputed from raw exactly as before
