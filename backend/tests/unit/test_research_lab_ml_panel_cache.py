"""ml_panel_cache: the disk-backed, period-cached panel equals ml_panel.build_panel exactly.

Synthetic snapshots only (no real data). "Equal" means ``assert_frame_equal`` after the parquet
round trip that every cached run already applies to the in-memory ``build_panel`` result.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import ml_panel, ml_panel_cache

pytest.importorskip("pyarrow")

T0 = pd.Timestamp("2026-10-11T00:00:00Z")
N_MKT, N_EVENT = 90, 25
HOURS = (0, 2, 4, 6, 10, 12, 14, 16, 18, 20)  # 6 -> 10 is a 4h gap: that period is skipped
NO_SIDECAR = 2  # snapshot without a sidecar: its fee_category is an all-NaN float column


def _ts(h: float, m: float = 0.0) -> str:
    return (T0 + pd.Timedelta(hours=h, minutes=m)).strftime("%Y-%m-%dT%H:%M:%S.000000Z")


def _world(root: Path) -> tuple[list[dict], dict]:
    rng = np.random.default_rng(11)
    snaps, sweeps = root / "snapshots", root / "book_sweeps"
    mid = rng.uniform(0.1, 0.9, N_MKT)
    ev = rng.integers(0, N_EVENT, N_MKT)
    cats = np.array(["crypto", "politics", "sports"])[ev % 3]
    caps = []
    for k, h in enumerate(HOURS):
        cid = f"cap{k:03d}"
        d = snaps / cid
        d.mkdir(parents=True)
        mid = np.clip(mid + rng.normal(0, 0.015, N_MKT), 0.04, 0.96)
        live = rng.random(N_MKT) > 0.08  # markets drop in and out of the universe
        idx = np.flatnonzero(live)
        rows = pd.DataFrame({
            "capture_id": cid, "received_utc": [_ts(h, 4 + (i % 30) / 10) for i in idx],
            "market_id": [f"m{i}" for i in idx], "event_id": [f"e{ev[i]}" for i in idx],
            "closed": False, "active": True, "binary": 1,
            "best_bid": mid[idx] - 0.01, "best_ask": mid[idx] + 0.01, "spread": 0.02,
            "last_trade_price": mid[idx], "chg_1h": rng.normal(0, 0.01, len(idx)),
            "chg_1d": 0.02, "chg_1w": -0.03, "liquidity": 100.0 + idx, "volume24hr": 50.0,
            "end_date": np.where(idx % 4 == 0, "2026-10-12T00:00:00Z", "2027-01-01T00:00:00Z"),
            "updated_at": _ts(h, 1), "neg_risk": 0, "neg_risk_market_id": None,
            "neg_risk_other": 0, "event_neg_risk_augmented": 0,
            # columns no panel code reads (PANEL_UNUSED_COLS): the cached build never loads them
            "condition_id": [f"0xc{i}" for i in idx], "clob_token_id_0": [f"t{i}" for i in idx],
            "page_index": idx // 10, "dup_count": 1,
        })
        rows.to_csv(d / "rows.csv.gz", index=False)
        (d / "manifest.json").write_text(json.dumps(
            {"capture_id": cid, "state": "complete", "started_utc": _ts(h),
             "finished_utc": _ts(h, 8)}))
        if k != NO_SIDECAR:
            ext = pd.DataFrame({
                "market_id": rows["market_id"], "received_utc": rows["received_utc"],
                "fee_category": [None if i % 11 == 0 else cats[i] for i in idx],
                "volume_num": 1000.0 + 10 * k,
                # a few markets link two events, so period-local groups merge when pooled
                "event_ids": [json.dumps([f"e{ev[i]}", f"e{(ev[i] + 1) % N_EVENT}"]) if i % 9 == 0
                              else json.dumps([f"e{ev[i]}"]) for i in idx],
                "series_slugs": json.dumps([]), "parent_event_ids": "",
                "start_date": _ts(-48), "competitive": 0.5,
                "clob_rewards": "[]", "fee_schedule": "{}",
            })
            ext.to_csv(d / "rows_ext.csv.gz", index=False)
            (d / "ext_manifest.json").write_text(json.dumps(
                {"sidecar_status": "complete", "ext_version": "snapshot-ext-v3"}))
        caps.append({"capture_id": cid, "started_utc": _ts(h), "dir": str(d),
                     "sidecar": k != NO_SIDECAR})
        if k == len(HOURS) - 1 or k == 5:  # no sweep after the last snapshot or at snapshot 5
            continue
        sd = sweeps / f"sw{k:03d}"
        sd.mkdir(parents=True)
        sm = mid[idx] + rng.normal(0, 0.004, len(idx))
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
            "finished_utc": _ts(h, 12), "tokens_requested": len(idx),
            "tokens_returned": len(idx)}))
    picked, _ = ml_panel.pick_sweeps(sweeps)
    return caps, picked


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    return _world(tmp_path_factory.mktemp("w"))


def _roundtrip(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    df.to_parquet(path, index=False)
    return pd.read_parquet(path)


def _norm_counts(counts: list[dict]) -> list:
    return json.loads(json.dumps(counts, default=ml_panel_cache._json_default))


def _reference(caps, sweeps, tmp, **kw):
    df, counts = ml_panel.build_panel(caps, sweep_receipts=sweeps, **kw)
    return _roundtrip(df, tmp / "ref.parquet"), counts, df.attrs["category_info"]


@pytest.mark.parametrize("with_leak", [False, True])
@pytest.mark.parametrize("policy", [None, ml_panel.category_policy("include", ["crypto"]),
                                    ml_panel.category_policy("exclude", ["sports"])])
def test_cached_panel_identical_to_build_panel(world, tmp_path, with_leak, policy):
    caps, sweeps = world
    ref, ref_counts, ref_info = _reference(caps, sweeps, tmp_path, with_leak=with_leak,
                                           policy=policy)
    out = tmp_path / "panel.parquet"
    counts, info, n = ml_panel_cache.build_panel_to_parquet(
        caps, out, tmp_path / "periods", "salt", sweep_receipts=sweeps, with_leak=with_leak,
        policy=policy)
    new = pd.read_parquet(out)
    pd.testing.assert_frame_equal(new, ref, check_exact=True)
    assert n == len(ref) and info == ref_info
    assert _norm_counts(counts) == _norm_counts(ref_counts)
    # the fixture exercises what matters: a skipped period, a sidecar-less period, pooling
    assert any(c.get("skipped") for c in counts)
    assert (ref["dep_group"] != ref["dep_group_period"]).any()
    assert with_leak == any(c.startswith("leak_") for c in new.columns)


def test_cached_periods_are_reused_without_reading_snapshots(world, tmp_path):
    caps, sweeps = world
    pdir = tmp_path / "periods"
    ml_panel_cache.build_panel_to_parquet(caps, tmp_path / "a.parquet", pdir, "s",
                                          sweep_receipts=sweeps)

    def no_read(cap):
        raise AssertionError("cached periods must not read a snapshot")

    counts, _, _ = ml_panel_cache.build_panel_to_parquet(
        caps, tmp_path / "b.parquet", pdir, "s", load=no_read, sweep_receipts=sweeps,
        with_leak=True, sweep_loader=no_read)
    ref, ref_counts, _ = _reference(caps, sweeps, tmp_path, with_leak=True)
    pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / "b.parquet"), ref, check_exact=True)
    assert _norm_counts(counts) == _norm_counts(ref_counts)
    # a different salt (code / feature version / delta change) never reuses a period
    with pytest.raises(AssertionError, match="must not read"):
        ml_panel_cache.build_panel_to_parquet(caps, tmp_path / "c.parquet", pdir, "other",
                                              load=no_read, sweep_receipts=sweeps)


def test_growing_and_shifted_capture_lists_reuse_only_matching_periods(world, tmp_path):
    caps, sweeps = world
    pdir = tmp_path / "periods"
    ml_panel_cache.build_panel_to_parquet(caps[:6], tmp_path / "p6.parquet", pdir, "s",
                                          sweep_receipts=sweeps)
    reads: list[str] = []

    def load(cap):
        reads.append(cap["capture_id"])
        return ml_panel.load_snapshot_rows(Path(cap["dir"]))

    for sub, name in ((caps, "all"), (caps[3:], "shifted")):
        reads.clear()
        ml_panel_cache.build_panel_to_parquet(sub, tmp_path / f"{name}.parquet", pdir, "s",
                                              load=load, sweep_receipts=sweeps)
        ref, _, _ = _reference(sub, sweeps, tmp_path)
        pd.testing.assert_frame_equal(pd.read_parquet(tmp_path / f"{name}.parquet"), ref,
                                      check_exact=True)
        if name == "all":  # periods 0-4 cached; 5.. need snapshots 5.. plus history 0-4
            assert "cap000" in reads and reads.count("cap009") == 1
    # a shifted list renumbers periods and changes the history of its first periods
    assert set(pd.read_parquet(tmp_path / "shifted.parquet")["period"]) <= set(range(6))


def test_slim_group_inputs_identical_to_full_snapshot(world, monkeypatch):
    caps, _ = world
    snap = ml_panel.load_snapshot_rows(Path(caps[4]["dir"]))
    mids = snap["market_id"].to_numpy()[::2]
    slim = ml_panel.dependence_group_ids(snap, mids)
    monkeypatch.setattr(ml_panel, "GROUP_INPUT_COLS", tuple(snap.columns))  # the old full read
    full = ml_panel.dependence_group_ids(snap, mids)
    pd.testing.assert_frame_equal(slim, full, check_exact=True)


def test_unused_columns_are_not_loaded(world):
    caps, _ = world
    full = ml_panel.load_snapshot_rows(Path(caps[4]["dir"]))
    slim = ml_panel.load_snapshot_rows(Path(caps[4]["dir"]), exclude=ml_panel.PANEL_UNUSED_COLS)
    gone = set(full.columns) - set(slim.columns)
    assert {"condition_id", "clob_token_id_0", "start_date", "fee_schedule"} <= gone
    assert gone <= set(ml_panel.PANEL_UNUSED_COLS)
    pd.testing.assert_frame_equal(slim, full[list(slim.columns)], check_exact=True)


def test_empty_panel(tmp_path):
    caps = [{"capture_id": "a", "started_utc": _ts(0), "dir": str(tmp_path)}]
    counts, info, n = ml_panel_cache.build_panel_to_parquet(caps, tmp_path / "p.parquet",
                                                            tmp_path / "pd", "s")
    assert counts == [] and n == 0 and info["rows_in"] == 0
    assert pd.read_parquet(tmp_path / "p.parquet").empty


def test_dry_run_slim_summary_matches_full_summary(world, tmp_path):
    caps, sweeps = world
    spec = importlib.util.spec_from_file_location(
        "run_ml_dev", Path(__file__).resolve().parents[2] / "scripts" / "run_ml_dev.py")
    rmd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rmd)
    out = tmp_path / "panel.parquet"
    ml_panel_cache.build_panel_to_parquet(caps, out, tmp_path / "periods", "s",
                                          sweep_receipts=sweeps)
    full = pd.read_parquet(out)
    slim = pd.read_parquet(out, columns=list(rmd.DRY_COLUMNS))
    rates = rmd.feature_nan_rates(out, ml_panel.EXTENDED_NAMES)
    assert rmd.panel_summary(slim, rates) == rmd.panel_summary(full)
    assert rmd.family_coverage(slim, [], tmp_path, rates)[1] == rmd.family_coverage(
        full, [], tmp_path)[1]
