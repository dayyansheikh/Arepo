"""Wallet sidecar + flow features: pinned E007 outputs, privacy, causality, definitions."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import stat
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import flow_features as ff
from astrolabe.research_lab import trade_sample as ts
from astrolabe.research_lab import wallet_sidecar as ws
from tests.unit.test_research_lab_trade_sample import (
    ORIGIN_EPOCH,
    SEED,
    Clock,
    Fake,
    make_snapshot,
    trade,
)

# sha256 of decoded outputs produced by the pre-change sampler (git HEAD) on this fixture
PRE = {
    "trades.csv.gz": "6ec0c84142ec2d3c85bb7c135e8a4f6743b506d40ffcc3d6648df0879d0ed3db",
    "features.csv.gz": "48f51fa6a6543f98dffdf728ffcddad832f5a761a149777f1861fa4439bead2a",
    "manifest.json": "5fcb56d882b9ed22d3107479dc5a928e2804bb05b760ad8418a290bb406f0268",
}
ORG = int(ORIGIN_EPOCH)
RAW = "0xAbCdEf0123456789aBcDeF0123456789abcdef01"


def sha(p: Path) -> str:
    raw = gzip.open(p).read() if p.suffix == ".gz" else p.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def det_snapshot(tmp_path: Path) -> Path:
    """make_snapshot, but rows.csv.gz re-written with mtime 0 so the plan/manifest hashes are
    reproducible (pandas embeds the wall-clock mtime otherwise)."""
    d = make_snapshot(tmp_path)
    raw = gzip.open(d / "rows.csv.gz").read()
    (d / "rows.csv.gz").write_bytes(gzip.compress(raw, mtime=0))
    return d


def sample_run(tmp_path, body=None, n_total=3, transport=None, **kw):
    snap = det_snapshot(tmp_path)
    plan, _ = ts.build_plan(pd.read_csv(snap / "rows.csv.gz", dtype={"market_id": str}),
                            {"capture_id": "cap"}, "", "", n_total, SEED)
    cid = plan["sample"][0]["condition_id"]
    body = body if body is not None else [
        trade(ORG - 30), trade(ORG - 100, side="SELL"), trade(ORG + 5)]
    man = ts.run(snap, transport or Fake({cid: body}), out_root=tmp_path / "out",
                 sleep=lambda s: None, now=Clock(), seed=SEED, n_total=n_total, **kw)
    return man, next((tmp_path / "out").iterdir()), cid


def test_e007_outputs_byte_identical_to_pre_change(tmp_path, monkeypatch):
    monkeypatch.setattr(ts, "_git_commit", lambda: "abc")
    _, d, _ = sample_run(tmp_path)
    for f, h in PRE.items():
        assert sha(d / f) == h, f
    assert (d / "wallets.csv.gz").exists()


def test_main_outputs_identical_when_sidecar_disabled_or_failing(tmp_path, monkeypatch):
    monkeypatch.setattr(ts, "_git_commit", lambda: "abc")

    class Boom(ws.WalletSidecar):
        def add_market(self, *a, **k):
            raise RuntimeError("boom")

        def write(self, *a, **k):
            raise RuntimeError("boom")

    # an exception escaping the sidecar must not be swallowed silently by design; the shipped
    # class never raises, so test the realistic failures: unreadable key and bad write.
    monkeypatch.setenv(ws.KEY_ENV, str(tmp_path / "nodir" / "sub" / "k"))
    monkeypatch.setattr(ws, "load_or_create_key",
                        lambda p=None: (_ for _ in ()).throw(PermissionError("x")))
    man, d, _ = sample_run(tmp_path)
    assert man["state"] == "complete"
    for f, h in PRE.items():
        assert sha(d / f) == h
    assert not (d / "wallets.csv.gz").exists()
    wm = json.loads((d / "wallets_manifest.json").read_text())
    assert wm["sidecar_status"] == "missing"


def test_no_raw_address_in_any_output_and_hash_stable(tmp_path):
    body = [{**trade(ORG - 30), "proxyWallet": RAW},
            {**trade(ORG - 60), "proxyWallet": RAW.lower()}]
    _, d, _ = sample_run(tmp_path, body=body)
    for p in d.rglob("*"):
        if p.is_file():
            data = gzip.open(p).read() if p.suffix == ".gz" else p.read_bytes()
            assert RAW.lower().encode() not in data.lower(), p
            assert b"0xwallet" not in data
    w = ff.read_wallets(d / "wallets.csv.gz")
    key = ws.load_or_create_key()
    exp = ws.hash_wallet(key, RAW)
    assert exp == ws.hash_wallet(key, RAW.lower())  # case-insensitive
    assert set(w["wallet_hash"]) == {exp} and len(exp) == 64
    assert ws.hash_wallet(b"other", RAW) != exp
    assert list(w.columns) == ws.WALLET_COLS


def test_key_created_once_mode_600_and_not_overwritten(tmp_path):
    p = tmp_path / "d" / "wallet_hash_key"
    k1 = ws.load_or_create_key(p)
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(p.parent).st_mode) == 0o700
    assert ws.load_or_create_key(p) == k1
    assert not list(p.parent.glob("*.tmp"))
    p2 = tmp_path / "pre"
    p2.write_text("backfill-key\n")
    assert ws.load_or_create_key(p2) == b"backfill-key\n"


def test_missing_wallet_is_null_not_zero(tmp_path):
    t = trade(ORG - 30)
    t.pop("proxyWallet")
    _, d, _ = sample_run(tmp_path, body=[t])
    w = ff.read_wallets(d / "wallets.csv.gz")
    assert w["wallet_hash"].isna().all()
    assert json.loads((d / "wallets_manifest.json").read_text())["rows_missing_wallet"] == 1


# --- features ---------------------------------------------------------------------------------


def df(rows):
    cols = ["market_id", "condition_id", "ts", "side", "outcome_index", "asset", "size", "price",
            "wallet_hash"]
    return pd.DataFrame([{"market_id": "1", "condition_id": "c", "outcome_index": 0,
                          "asset": "t", "price": 0.5, **r} for r in rows])[cols]


def trd(dt, side="BUY", size=10.0, w="a", **kw):
    return {"ts": ORG - dt, "side": side, "size": size, "wallet_hash": w, **kw}


def test_imbalance_windows_and_causality():
    base = [trd(60, "BUY", 30), trd(600, "SELL", 10), trd(2000, "SELL", 20),
            trd(10000, "BUY", 40)]
    f = ff.compute_flow_features(df(base), ORG)
    assert f["flow_imb_15m"] == (30 - 10) / 40
    assert f["flow_imb_1h"] == (30 - 10 - 20) / 60
    assert f["flow_imb_6h"] == (30 - 10 - 20 + 40) / 100
    assert f["flow_n_1h"] == 3
    # trades at or after origin are ignored (even huge ones)
    poison = [{"ts": ORG, "side": "BUY", "size": 1e6, "wallet_hash": "z"},
              {"ts": ORG + 50, "side": "BUY", "size": 1e6, "wallet_hash": "z"}]
    g = ff.compute_flow_features(df(base + poison), ORG)
    for k, v in f.items():
        assert (np.isnan(v) and np.isnan(g[k])) or v == g[k], k


def test_outcome1_sign_and_truncation_uncovered():
    f = ff.compute_flow_features(df([trd(60, "BUY", 10, outcome_index=1)]), ORG)
    assert f["flow_imb_1h"] == -1.0
    full = df([trd(60 + i, "BUY", 1) for i in range(500)])  # page full, oldest ~1 min back
    g = ff.compute_flow_features(full, ORG, n_returned=500)
    assert g["flow_covered_1h"] == 0.0 and np.isnan(g["flow_imb_1h"])
    assert np.isnan(g["flow_imb_6h"]) and np.isnan(g["wlt_hhi_1h"])


def test_burstiness_and_acceleration():
    regular = df([trd(60 * i, "BUY", 1) for i in range(1, 11)])
    assert ff.compute_flow_features(regular, ORG)["flow_burstiness_1h"] == -1.0
    bursty = df([trd(s, "BUY", 1) for s in (3000, 3001, 3002, 3003, 10, 11)])
    assert ff.compute_flow_features(bursty, ORG)["flow_burstiness_1h"] > 0.3
    assert np.isnan(ff.compute_flow_features(df([trd(5), trd(9)]), ORG)["flow_burstiness_1h"])
    acc = ff.compute_flow_features(df([trd(60 * i) for i in range(1, 6)]), ORG)
    assert abs(acc["flow_accel_15m"] - np.log((5 / 0.25 + 1) / 1)) < 1e-12
    quiet = ff.compute_flow_features(df([trd(2000), trd(2100), trd(2200)]), ORG)
    assert quiet["flow_accel_15m"] < 0


def test_largest_trade_vs_liquidity():
    f = ff.compute_flow_features(df([trd(60, size=100, price=0.4), trd(90, size=10)]), ORG,
                                 liquidity=200.0)
    assert f["flow_max_trade_liq_1h"] == 100 * 0.4 / 200.0
    assert np.isnan(ff.compute_flow_features(df([trd(60)]), ORG, liquidity=0)
                    ["flow_max_trade_liq_1h"])


def test_price_agreement():
    up = df([trd(1800, "BUY", price=0.40), trd(60, "BUY", price=0.45)])
    assert ff.compute_flow_features(up, ORG)["flow_price_agree"] == 1.0
    contra = df([trd(1800, "SELL", price=0.40), trd(60, "SELL", price=0.45)])
    assert ff.compute_flow_features(contra, ORG)["flow_price_agree"] == -1.0
    assert ff.compute_flow_features(contra, ORG, recent_price_change=-0.02)["flow_price_agree"] == 1
    assert np.isnan(ff.compute_flow_features(df([trd(60)]), ORG)["flow_price_agree"])


def test_wallet_concentration_sides_agreement_exposure():
    rows = [trd(60, "BUY", 50, "a"), trd(120, "BUY", 30, "b"), trd(180, "SELL", 10, "c"),
            trd(240, "SELL", 10, "d")]
    f = ff.compute_flow_features(df(rows), ORG, liquidity=100.0)
    shares = np.array([50, 30, 10, 10]) / 100
    assert abs(f["wlt_hhi_1h"] - (shares ** 2).sum()) < 1e-12
    assert f["wlt_top1_share_1h"] == 0.5 and abs(f["wlt_top3_share_1h"] - 0.9) < 1e-12
    assert (f["wlt_n_buy_1h"], f["wlt_n_sell_1h"]) == (2, 2)
    assert f["wlt_agree_1h"] == 0.0
    assert abs(f["wlt_top3_exposure_liq_1h"] - (25 + 15 - 5) / 100) < 1e-12  # a,b,c (ties by order)
    same = ff.compute_flow_features(df(rows[:2]), ORG)
    assert same["wlt_agree_1h"] == 1.0


def test_missing_wallets_excluded_and_counted():
    rows = [trd(60, "BUY", 10, "a"), trd(90, "BUY", 90, None)]
    f = ff.compute_flow_features(df(rows), ORG)
    assert f["wlt_n_missing_1h"] == 1 and f["wlt_hhi_1h"] == 1.0


def sidecar_frame(rows):
    return df(rows)


def test_new_to_arepo_share_is_causal_and_span_guarded():
    idx = ff.FirstSeenIndex()
    d = 86400
    # old wallet 'a' first seen 10 days ago; 'b' 2 days ago; span 10 days
    idx.add_frame(df([{"ts": ORG - 10 * d, "side": "BUY", "size": 1, "wallet_hash": "a"},
                      {"ts": ORG - 2 * d, "side": "BUY", "size": 1, "wallet_hash": "b"},
                      # after origin: must not count as having been seen
                      {"ts": ORG + 100, "side": "BUY", "size": 1, "wallet_hash": "c"}]))
    rows = [trd(60, "BUY", 50, "a"), trd(90, "BUY", 20, "b"), trd(120, "BUY", 30, "c")]
    f = ff.compute_flow_features(df(rows), ORG, first_seen=idx)
    # a old; b first seen 2d ago (< 7d) -> new; c unseen before origin -> new
    assert abs(f["wlt_new_share_1h"] - 0.5) < 1e-12
    assert idx.span_days(ORG) == 10
    short = ff.FirstSeenIndex()
    short.add_frame(df([{"ts": ORG - 3 * d, "side": "BUY", "size": 1, "wallet_hash": "a"}]))
    g = ff.compute_flow_features(df(rows), ORG, first_seen=short)
    assert np.isnan(g["wlt_new_share_1h"]) and g["wlt_index_span_days"] == 3


def test_wallet_age_hook_optional():
    rows = [trd(60, "BUY", 10, "a"), trd(90, "BUY", 10, "b")]
    assert np.isnan(ff.compute_flow_features(df(rows), ORG)["wlt_age_activity_median_days"])
    f = ff.compute_flow_features(df(rows), ORG, wallet_age_fn={"a": 10.0, "b": 30.0}.get)
    assert f["wlt_age_activity_median_days"] == 20.0


def test_index_rebuild_deterministic_and_excludes_self_and_later(tmp_path):
    root = tmp_path / "samples"
    for sid, w, t in (("20261010T000000Z_aa", "x", 100), ("20261010T020000Z_bb", "y", 200),
                      ("20261010T040000Z_cc", "z", 300)):
        (root / sid).mkdir(parents=True)
        d = df([{"ts": t, "side": "BUY", "size": 1, "wallet_hash": w}])
        with gzip.GzipFile(root / sid / "wallets.csv.gz", "wb", mtime=0) as gz:
            gz.write(d.to_csv(index=False).encode())
    (root / "20261010T030000Z_missing").mkdir()  # sidecar missing: skipped
    idx = ff.FirstSeenIndex.build(root, "20261010T040000Z_cc")
    assert set(idx.first_ts) == {"x", "y"}
    assert ff.FirstSeenIndex.build(root, "20261010T040000Z_cc").digest() == idx.digest()
    assert set(ff.FirstSeenIndex.build(root).first_ts) == {"x", "y", "z"}
    a, b = tmp_path / "a.gz", tmp_path / "b.gz"
    idx.write(a)
    ff.FirstSeenIndex.build(root, "20261010T040000Z_cc").write(b)
    assert a.read_bytes() == b.read_bytes()


def test_features_for_sample_end_to_end_and_no_insider_labels(tmp_path):
    _, d, cid = sample_run(tmp_path)
    out = ff.features_for_sample(d, {m: 1000.0 for m in ["1000", "1001", "1002"]},
                                 first_seen=ff.FirstSeenIndex())
    assert len(out) == 3 and set(ff.feature_names()) <= set(out.columns)
    row = out[out["market_id"] == ff.read_wallets(d / "wallets.csv.gz")["market_id"].iloc[0]]
    assert len(row) == 1
    for name in ff.feature_names():
        assert "insider" not in name and "inform" not in name
