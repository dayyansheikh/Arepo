# ruff: noqa: E501
"""Live tests E015-E019 (LIVE_TESTS_3.md, sections 1-9 as amended by section 13): class labels, the walked and train
constructs, causality, late refusal, write-once, statuses, the gates under simulated nulls, the counting rule, the
ops-stats column whitelist, the censuses and an end-to-end synthetic analysis. Synthetic data only; no network."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2
from astrolabe.research_lab import live_tests3 as lt
from astrolabe.research_lab import live_tests3_analysis as la

G0 = datetime(2027, 1, 1, 0, 31, tzinfo=UTC)  # on the spec grid; later than the wall clock, so real frozen_utc stamps are never "late"
N_MKT = 40


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _spec(tmp_path: Path, **over) -> dict:
    spec = json.loads(lt.SPEC_PATH.read_text())
    f = spec["flow"]
    for z, (c, s) in {"zW": (0.2, 0.2), "zH": (0.5, 0.3), "zN": (2.0, 1.0), "zSize": (3.0, 1.0), "zSPR": (0.02, 0.01),
                      "zRV": (-4.0, 1.0), "zHTE": (4.0, 1.5)}.items():
        f[z] = {"centre": c, "scale": s}
    f["vol24_cap"] = 1e9
    f["econ"]["W_upper_cut"], f["econ"]["H_lower_cut"] = 0.3, 0.4
    spec["e019"]["exclude_crypto"] = False
    for k, v in over.items():
        spec[k] = v
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    return lt.load_spec(p, sha=None)


def _mid(m: int, k: int, wild: bool = False) -> float:
    if wild:
        return float(np.clip(0.05 + 0.9 * ((m * 7 + k * 13) % 17) / 17.0, 0.05, 0.95))
    r = np.random.default_rng(1000 * m + k)
    if m in (10, 11):  # quiet markets (E017: 10 surges without a move, 11 is a quiet baseline)
        return 0.4 + 0.0005 * (k % 2)
    return float(np.clip(0.3 + 0.01 * m + 0.03 * np.sin(k / 2.0 + m) + r.normal(0, 0.01), 0.05, 0.9))


def _traded(m: int, k: int) -> bool:
    return (m + k) % 3 == 0 if m >= 12 else (m + k) % 11 == 0


def write_capture(snap_root: Path, k: int, *, wild: bool = False, ext: bool = True, drop: tuple = ()) -> str:
    start = G0 + timedelta(hours=2 * k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = snap_root / cid
    d.mkdir(parents=True)
    rows, exts = [], []
    for m in range(N_MKT):
        if m in drop:
            continue
        mid = round(_mid(m, k, wild), 3)
        sp = 0.02 if m % 9 else 0.2
        one_sided = (m == 5 and k % 4 == 0)
        bid, ask = (mid - sp / 2, mid + sp / 2) if not one_sided else (None, mid + 0.01)
        ltp = None if m == 3 else (round(mid, 4) if _traded(m, k) else 0.5)
        rows.append({"capture_id": cid, "capture_start_utc": _iso(start), "received_utc": _iso(start + timedelta(seconds=5 + m)),
                     "market_id": str(100 + m), "condition_id": f"0xc{m}", "event_id": str(10 + m // 4), "closed": "False", "active": "True",
                     "binary": 1, "best_bid": bid, "best_ask": ask, "spread": sp, "last_trade_price": ltp, "chg_1h": 0.01, "chg_1d": None,
                     "chg_1w": 0.0, "liquidity": 100.0, "volume24hr": 1000.0 + 50 * sum(_traded(m, j) for j in range(k + 1)) + (5000 * k if (m in (7, 10) and k % 4 == 0) else 0),
                     "end_date": _iso(start + timedelta(days=30)), "updated_at": "", "dup_count": 1, "clob_token_id_0": f"tok{m}",
                     "neg_risk": "1" if m < 20 else "0", "neg_risk_market_id": "", "neg_risk_other": "", "event_neg_risk_augmented": "", "page_index": 0})
        exts.append({"capture_id": cid, "market_id": str(100 + m), "fee_type": "sports_fees_v3" if m >= 32 else ("crypto_fees_v2" if m in (0, 1, 2, 3) else "politics_fees"),
                     "fee_category": "", "fees_enabled": "1", "fee_schedule": "", "order_price_min_tick_size": "0.001" if m % 2 else "0.01",
                     "created_at": _iso(G0 - timedelta(days=30)), "series_slugs": '["bitcoin-neg-risk-weekly"]' if m < 4 else ""})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    if ext:
        pd.DataFrame(exts).to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start)}))
    return cid


def write_sweep(sweep_root: Path, cid: str, k: int) -> None:
    start = G0 + timedelta(hours=2 * k, minutes=6)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}"
    d = sweep_root / sid
    d.mkdir(parents=True)
    rows = [{"sweep_id": sid, "token_id": f"tok{m}", "market_id": str(100 + m), "batch_index": 0, "batch_receipt_utc": _iso(start),
             "best_bid": round(_mid(m, k) - 0.01, 3), "best_ask": round(_mid(m, k) + 0.01, 3), "state": "two_sided"} for m in range(N_MKT)]
    rows += [{"sweep_id": sid, "token_id": f"tokB{m}", "market_id": str(100 + m), "batch_index": 0, "batch_receipt_utc": _iso(start),
              "best_bid": 0.1, "best_ask": 0.2, "state": "two_sided"} for m in range(N_MKT)]
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    (d / "manifest.json").write_text(json.dumps({"sweep_id": sid, "state": "complete", "series_index": 0, "snapshot_id": cid}))


def write_sample(sample_root: Path, cid: str, k: int, seed: int = 0) -> str:
    start = G0 + timedelta(hours=2 * k, minutes=9)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_t{k:07x}"
    d = sample_root / sid
    d.mkdir(parents=True)
    rng = np.random.default_rng(seed + k)
    feats, trades = [], []
    for m in range(N_MKT):
        origin = G0 + timedelta(hours=2 * k, seconds=5 + m)
        feats.append({"market_id": str(100 + m), "condition_id": f"0xc{m}", "stratum": "a", "origin_utc": _iso(origin), "sent_utc": _iso(start),
                      "status": "ok", "n_returned": 40, "n_dropped_future": 0, "n_unsigned": 0, "n_trades_1h": 3, "volume_1h": 10.0,
                      "notional_1h": 5.0, "signed_volume_1h": 1.0, "max_trade_size_1h": 2.0, "time_since_last_trade_s": 60, "trades_truncated": False})
        o = origin.timestamp()
        for i in range(30):
            ts = int(o - rng.uniform(0, 7 * 3600))
            p = round(_mid(m, k) + rng.choice([0.0, 0.0, 0.0004, -0.0003]), 4)
            trades.append({"market_id": str(100 + m), "condition_id": f"0xc{m}", "ts": ts, "side": rng.choice(["BUY", "SELL"]), "price": p,
                           "size": float(rng.uniform(1, 50)), "outcome_index": int(rng.integers(0, 2)), "asset": f"tok{m}", "tx_hash": f"0x{m}{i}"})
        trades.append({"market_id": str(100 + m), "condition_id": f"0xc{m}", "ts": int(o + 30), "side": "BUY", "price": 0.5, "size": 1.0,
                       "outcome_index": 0, "asset": f"tok{m}", "tx_hash": "post"})
    pd.DataFrame(feats).to_csv(d / "features.csv.gz", index=False, compression="gzip")
    pd.DataFrame(trades).to_csv(d / "trades.csv.gz", index=False, compression="gzip")
    (d / "plan.json").write_text(json.dumps({"snapshot_id": cid, "strata": [{"stratum": "a", "inclusion_float": 1.0}]}))
    (d / "manifest.json").write_text(json.dumps({"sample_id": sid, "state": "complete", "frame": "active", "snapshot_id": cid}))
    return sid


def _world(tmp_path: Path, k0: int = 0, k1: int = 30, samples: bool = True, wild_from: int | None = None) -> dict:
    snap, sw, smp = tmp_path / "snap", tmp_path / "sweeps", tmp_path / "samples"
    ids = {}
    for k in range(k0, k1 + 1):
        ids[k] = write_capture(snap, k, wild=wild_from is not None and k >= wild_from)
        write_sweep(sw, ids[k], k)
        if samples:
            write_sample(smp, ids[k], k)
    return {"snap": snap, "sweeps": sw, "samples": smp, "ids": ids}


def _t(k: int, minutes: float = 0) -> float:
    return (G0 + timedelta(hours=2 * k, minutes=minutes)).timestamp()


def _run(w: dict, root: Path, spec: dict, reg_k: int, end_k: int, now: float, **kw) -> dict:
    return lt.run_once(snapshot_root=w["snap"], sample_root=w["samples"], sweep_root=w["sweeps"], root=root, spec=spec,
                       registered_utc=_iso(G0 + timedelta(hours=2 * reg_k, minutes=-31)),
                       end_utc=_iso(G0 + timedelta(hours=2 * end_k, minutes=-31)), now=now, max_items=10_000, **kw)


# --- class labels ------------------------------------------------------------------------------------------------------


def test_classify_every_branch(tmp_path):
    spec = _spec(tmp_path)
    nan = np.nan
    #            bid_p  ask_p  bid_k  ask_k  ltp_p  ltp_k  vol_p  vol_k   expected class, geometry
    cases = [(0.40, 0.42, 0.45, 0.47, nan, nan, 10.0, 10.0, "never_traded", "parallel"),
             (0.40, 0.42, 0.45, 0.47, 0.41, 0.46, 10.0, 10.0, "traded", "parallel"),          # L (price changed)
             (0.40, 0.42, 0.45, 0.47, 0.41, 0.41, 10.0, 12.0, "traded", "parallel"),          # V+
             (0.40, 0.42, 0.45, 0.47, nan, 0.46, 10.0, 10.0, "traded", "parallel"),           # first trade
             (0.40, 0.42, 0.45, 0.47, 0.41, 0.41, 10.0, 8.0, "ambiguous", "parallel"),        # V-
             (0.40, 0.42, 0.45, 0.47, 0.41, nan, 10.0, 10.0, "ambiguous", "parallel"),        # ltp disappears
             (0.40, 0.42, 0.45, 0.47, 0.41, 0.41, nan, 10.0, "ambiguous", "parallel"),        # volume unknown
             (0.40, 0.42, 0.45, 0.47, 0.41, 0.41, 10.0, 10.005, "quote_only", "parallel"),
             (0.40, 0.42, 0.40, 0.45, 0.41, 0.41, 10.0, 10.0, "quote_only", "one_sided"),
             (0.40, 0.46, 0.43, 0.44, 0.41, 0.41, 10.0, 10.0, "quote_only", "spread_change"),
             (0.40, 0.42, 0.42, 0.47, 0.41, 0.41, 10.0, 10.0, "quote_only", "same_side_unequal")]
    a = np.array([c[:8] for c in cases], float)
    cls, geom = lt.classify(*a.T, spec)
    assert list(cls) == [c[8] for c in cases]
    assert list(geom) == [c[9] for c in cases]


# --- walked, trains ----------------------------------------------------------------------------------------------------


def test_walked_grid_distance_rule():
    price = np.array([0.45, 0.5099998899, 0.453, 0.453, 0.4537, 0.4500004, 0.45])
    tick = np.array([0.01, 0.01, 0.01, 0.001, 0.001, 0.01, np.nan])
    d = lt.grid_distance(price, tick)
    walked = np.isfinite(d) & (d >= 1e-4 - 1e-12)
    assert list(walked) == [False, False, True, False, True, False, False]
    assert np.isnan(d[-1])  # tick unknown: left out of W


def test_train_flags_same_sign_and_window():
    codes = np.array([0, 0, 0, 0, 1, 1])
    ts = np.array([0.0, 200.0, 1000.0, 1150.0, 0.0, 100.0])
    sg = np.array([1.0, 1.0, 1.0, -1.0, -1.0, -1.0])
    assert list(lt.train_flags(codes, ts, sg, 300.0, True)) == [True, True, False, False, True, True]
    assert list(lt.train_flags(codes, ts, sg, 300.0, False)) == [True, True, True, True, True, True]
    # a row at or after the origin never makes an earlier row a train member: window_features drops it first
    tr = pd.DataFrame({"market_id": ["a", "a"], "ts": [990.0, 1100.0], "sg": [1.0, 1.0], "o": [1000.0, 1000.0], "nt": [1.0, 1.0],
                       "walk_known": [1, 1], "walked": [False, False]})
    f = lt.window_features(tr, pd.Series(["a"]), 3600.0, 0.0, 300.0)
    assert f["N"][0] == 1 and f["H"][0] == 0.0


# --- reader: causality, late refusal, write-once, statuses ------------------------------------------------------------


def test_causality_future_captures_do_not_change_frozen_lines(tmp_path):
    spec = _spec(tmp_path)
    a = _world(tmp_path / "a", 0, 16)
    b = _world(tmp_path / "b", 0, 16, wild_from=15)  # captures 15, 16 differ wildly (post-origin for origin 14)
    now = _t(14, 40)
    for w, r in ((a, tmp_path / "ra"), (b, tmp_path / "rb")):
        st = _run(w, r, spec, 14, 15, now)
        assert st["move"] == 1 and st["surge"] == 1 and st["flow"] == 1
    drop = ["frozen_utc", "code_commit", "capture_id", "sample_id"]
    for kind, name in (("move", a["ids"][14]), ("events", a["ids"][14]), ("surge", a["ids"][14])):
        fa = pd.read_csv(tmp_path / "ra" / kind / "frozen" / f"{name}.csv.gz").drop(columns=drop, errors="ignore")
        fb = pd.read_csv(tmp_path / "rb" / kind / "frozen" / f"{b['ids'][14]}.csv.gz").drop(columns=drop, errors="ignore")
        pd.testing.assert_frame_equal(fa, fb)
    sa = sorted((tmp_path / "ra" / "flow" / "frozen").glob("*.csv.gz"))[0]
    sb = sorted((tmp_path / "rb" / "flow" / "frozen").glob("*.csv.gz"))[0]
    pd.testing.assert_frame_equal(pd.read_csv(sa).drop(columns=drop), pd.read_csv(sb).drop(columns=drop))


def test_late_refusal_and_write_once(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 16)
    root = tmp_path / "r"
    st = _run(w, root, spec, 14, 15, _t(15, -0.5))  # 30 s before slot 15: move (target k + 1) is late, surge / flow (k + 3) are not
    assert st["refused_late"] == 1
    assert (root / "move" / "frozen" / f"{w['ids'][14]}.late.csv.gz").exists()
    assert st["surge"] == 1 and st["flow"] == 1
    p = root / "surge" / "frozen" / f"{w['ids'][14]}.csv.gz"
    before = (p.read_bytes(), p.stat().st_mtime_ns)
    st2 = _run(w, root, spec, 14, 15, _t(15, -0.4))
    assert st2["surge"] == 0 and st2["move"] == 0
    assert (p.read_bytes(), p.stat().st_mtime_ns) == before
    with pytest.raises(ValueError):
        lt.run_once(root=root, spec={**spec, "_pinned": True}, allow_late=True)


def test_outcome_statuses(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 15)
    # slot 16 capture missing; slot 17 present without market 104 (absent); market 105 one-sided at slots with k % 4 == 0
    write_capture(w["snap"], 17, drop=(4,))
    root = tmp_path / "r"
    _run(w, root, spec, 14, 16, _t(14, 40))
    _run(w, root, spec, 14, 16, _t(17, 0) + lt.MISSING_AFTER_S)
    _run(w, root, spec, 14, 16, _t(17, 0) + lt.MISSING_AFTER_S + 1)
    o = pd.read_csv(root / "move" / "outcomes" / f"{w['ids'][15]}.h1.csv.gz", dtype={"market_id": str})
    assert set(o["status"]) == {"capture_missing"}
    o3 = pd.read_csv(root / "surge" / "outcomes" / f"{w['ids'][14]}.h3.csv.gz", dtype={"market_id": str}).set_index("market_id")
    assert o3.loc["104", "status"] == "absent"
    st = lt.status_codes(pd.DataFrame(index=pd.Index(["1"])), pd.DataFrame({"st": ["one_sided", "closed_flag"]}, index=["2", "3"]),
                         ["1", "2", "3", "4"], False)
    assert list(st) == ["two_sided", "one_sided", "closed_flag", "absent"]


def test_pretrend_and_lag_labels_use_only_pre_origin_mids(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 15)
    root = tmp_path / "r"
    _run(w, root, spec, 14, 15, _t(14, 40))
    s = pd.read_csv(root / "surge" / "frozen" / f"{w['ids'][14]}.csv.gz", dtype={"market_id": str}).set_index("market_id")
    ser = {k: lt.read_series(root, w["ids"][k]) for k in (1, 12, 13)}
    m = "110"
    mid = {k: (ser[k].loc[m, "bid"] + ser[k].loc[m, "ask"]) / 2 for k in ser}
    assert s.loc[m, "pre24"] == pytest.approx(mid[13] - mid[1], abs=1e-6)
    assert s.loc[m, "x_km1"] == pytest.approx(mid[13] - mid[12], abs=1e-6)
    # market 107 surges when k % 4 == 0; at 14 it is a baseline unit
    assert s.loc["107", "S"] == 0


def test_surge_labels():
    spec = json.loads(lt.SPEC_PATH.read_text())
    spec["_sha256"] = "x" * 64
    idx = pd.Index(["a", "b", "c", "d"], name="market_id")
    base = {"event_id": ["e"] * 4, "t_row": [1e6] * 4, "spread": [0.02] * 4, "ltp": [0.5] * 4, "end_ts": [np.nan] * 4,
            "created_ts": [0.0] * 4, "chg_1d": [0.0] * 4, "neg_risk": [1] * 4, "sports": [0] * 4, "crypto": [0] * 4, "skey": ["s"] * 4,
            "fee_rate": [0.0] * 4, "fee_exp": [1.0] * 4}
    ser_p = pd.DataFrame({**base, "bid": [0.49, 0.49, 0.49, 0.49], "ask": [0.51] * 4, "vol24": [100.0, 100.0, 100.0, 100.0]}, index=idx)
    ser_k = pd.DataFrame({**base, "bid": [0.49, 0.52, 0.49, 0.49], "ask": [0.51, 0.54, 0.51, 0.51], "vol24": [700.0, 700.0, 700.0, 150.0]}, index=idx)
    ser_p2 = pd.DataFrame({**base, "bid": [0.49, 0.49, 0.45, 0.49], "ask": [0.51, 0.51, 0.47, 0.51], "vol24": [100.0] * 4}, index=idx)
    ser_p2 = ser_p2.drop(index="a")  # a: x_{k-1} unknown -> lag_unknown
    fr, cnt = lt.freeze_surge(ser_k, ser_p, ser_p2, None, {"id": "c", "start": 1e6}, 1, spec, lt.ROLE_UNREG, "t")
    fr = fr.set_index("market_id")
    assert list(fr.loc[["a", "b", "c", "d"], "lag_unknown"]) == [1, 0, 0, 0]
    assert list(fr.loc[["a", "b", "c", "d"], "A"]) == [0, 0, 0, 0]  # b moved now, c moved in k-1 (finding 8), d no surge
    assert list(fr.loc[["a", "b", "c", "d"], "SM"]) == [0, 1, 1, 0]


def test_event_interval_breadth(tmp_path):
    spec = _spec(tmp_path)
    idx = pd.Index(["a", "b", "c", "d", "e"], name="market_id")
    base = {"event_id": ["E"] * 5, "t_row": [1e6] * 5, "spread": [0.02] * 5, "end_ts": [np.nan] * 5, "created_ts": [0.0] * 5,
            "neg_risk": [1] * 5, "sports": [0] * 5, "crypto": [0] * 5, "skey": ["event:E"] * 5, "fee_rate": [0.0] * 5, "fee_exp": [1.0] * 5,
            "ltp": [0.5] * 5, "vol24": [10.0] * 5}
    ser_p = pd.DataFrame({**base, "bid": [0.20, 0.30, 0.40, 0.50, 0.60], "ask": [0.22, 0.32, 0.42, 0.52, 0.62]}, index=idx)
    ser_k = pd.DataFrame({**base, "bid": [0.22, 0.32, 0.42, 0.52, 0.60], "ask": [0.24, 0.34, 0.44, 0.54, 0.62]}, index=idx)
    u, e, _ = lt.freeze_move(ser_k, ser_p, {"id": "c", "start": 1e6}, 1, spec, lt.ROLE_UNREG, "t")
    assert len(u) == 4 and set(u["cls"]) == {"quote_only"} and set(u["geom"]) == {"parallel"}
    r = e.iloc[0]
    assert r["n_elig"] == 5 and r["n_qo_mov"] == 4 and r["b"] == pytest.approx(0.8) and r["untraded"] == 1
    assert r["sh_os"] == 0.0 and r["sh_sc"] == 0.0


# --- gates under simulated nulls ----------------------------------------------------------------------------------------


def _flow_panel(seed: int, n_mkt: int = 40, n_t: int = 30, ar: float = 0.0, effect: float = 0.0) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows = []
    for m in range(n_mkt):
        x = 0.0
        lvl = rng.normal(0, 0.5)
        for i in range(n_t):
            x = ar * x + rng.normal(0, 1)
            z = lvl + rng.normal(0, 1)
            rows.append({"market_id": f"m{m}", "event_id": f"e{m // 2}", "t_row": i * 7200.0, "day": str(i // 12), "x6": x, "zW": z,
                         "c1": rng.normal()})
    df = pd.DataFrame(rows)
    y = 0.003 * df["x6"].to_numpy() + effect * df["x6"].to_numpy() * df["zW"].to_numpy() + rng.normal(0, 0.01, len(df))
    return df, y


def test_donor_gate_null_rejection_and_planted_effect():
    rej = []
    for s in range(20):
        df, y = _flow_panel(s, ar=0.0 if s % 2 else 0.6)
        g = la.donor_gate(df, y, "x6", "zW", ["x6", "c1"], sign=+1, draws=39, seed=s, min_units=4, min_sep_s=43200.0, min_donors=2)
        rej.append(g["passes"])
    assert np.mean(rej) <= 0.15  # reduced unit-test version; the pinned-code check uses 200 panels (section 13)
    df, y = _flow_panel(99, effect=0.004)
    g = la.donor_gate(df, y, "x6", "zW", ["x6", "c1"], sign=+1, draws=39, seed=1, min_units=4, min_sep_s=43200.0, min_donors=2)
    assert g["passes"]


def test_donor_plan_respects_separation():
    codes = np.array([0, 0, 0, 0, 1, 1, 1])
    t = np.array([0.0, 3600.0, 50000.0, 90000.0, 0.0, 10.0, 99999.0])
    plan = la.donor_plan(codes, t, 43200.0)
    rng = np.random.default_rng(0)
    for _ in range(50):
        idx, has = la.donor_indices(plan, rng, 2)
        for i in range(len(t)):
            if has[i]:
                assert codes[idx[i]] == codes[i] and abs(t[idx[i]] - t[i]) >= 43200.0
            else:
                assert idx[i] == i
    assert list(plan["cnt"]) == [2, 2, 2, 2, 1, 1, 2]


def test_perm_gate_null_and_effect():
    rng = np.random.default_rng(5)
    n = 2000
    df = pd.DataFrame({"market_id": rng.integers(0, 50, n).astype(str), "t_row": np.arange(n, dtype=float), "day": (np.arange(n) // 200).astype(str),
                       "P": rng.integers(0, 2, n), "c1": rng.normal(size=n)})
    strata = (df["market_id"] + "|" + df["day"]).to_numpy()
    y0 = rng.normal(0, 1, n)
    g0 = la.perm_gate(df, y0, "P", ["c1"], sign=+1, group="market_id", order="t_row", strata=strata, draws=49, seed=1, min_stratum=4)
    y1 = y0 + 0.5 * df["P"].to_numpy()
    g1 = la.perm_gate(df, y1, "P", ["c1"], sign=+1, group="market_id", order="t_row", strata=strata, draws=49, seed=1, min_stratum=4)
    assert not g0["passes"] or g0["p_perm"] > 0.01
    assert g1["passes"] and 0 < g1["share_rows_permuted"] <= 1


# --- counting, Holm, refusals, ops-stats ------------------------------------------------------------------------------


def test_counting_rule_equals_k():
    res = {"holm": {"tests": ["E015", "E017", "E019"]}, "E015": {"verdict": {}}, "E017": {"verdict": {}}, "E019": {"verdict": {}}}
    rec = la.trial_record(res)
    assert rec["kind"] == "live_tests3" and rec["n_tests"] == 3
    assert battery2.count_line(rec) == ("live_tests3", 3)


def test_analysis_refusals(tmp_path):
    with pytest.raises(RuntimeError):
        la.analyze(tmp_path)  # before ANALYSIS_NOT_BEFORE
    spec = _spec(tmp_path)
    spec["_pinned"] = True
    with pytest.raises(RuntimeError):
        la.code_check(spec)  # code hashes not pinned
    spec["code_sha256"] = lt.code_hashes()
    with pytest.raises(RuntimeError):
        la.code_check(spec)  # null k_tests


def test_ops_stats_reads_no_price_column(tmp_path, monkeypatch):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 16)
    root = tmp_path / "r"
    _run(w, root, spec, 14, 15, _t(14, 40))
    _run(w, root, spec, 14, 15, _t(16, 40) + 4 * 3600)
    seen = []
    real = pd.read_csv

    def spy(path, *a, **k):
        seen.append((str(path), k.get("usecols"), k.get("nrows")))
        return real(path, *a, **k)

    monkeypatch.setattr(lt.pd, "read_csv", spy)
    out = lt.ops_stats(root)
    assert out["move/frozen"]["files"] == 1 and out["outcome_status_counts"]
    for _, use, nrows in seen:
        assert nrows == 0 or (use is not None and set(use) <= lt.OPS_COLS)
    with pytest.raises(ValueError):
        lt._read_ops(root / "move" / "frozen" / f"{w['ids'][14]}.csv.gz", ["mid_k"])


# --- censuses and the end-to-end analysis -------------------------------------------------------------------------------


def test_census_captures_counts_only(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 26, samples=False)
    days = ["2027-01-02", "2027-01-03"]
    res = lt.census_captures(snapshot_root=w["snap"], work=tmp_path / "work", days=days, spec=spec)
    assert set(res) >= {"C1", "C3", "C4"}
    assert "pass" in res["C1"]["gate_E015"] and "pass" in res["C3"]["gate_E017"] and "pass" in res["C4"]["gate_E019"]
    assert res["C1"]["movers"]["all"] > 0
    assert not list((tmp_path / "work").glob("**/outcomes/*"))  # no target is ever written


def test_census_flow_verifies_seal(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 26)
    sids = sorted(p.name for p in w["samples"].iterdir())[13:25]
    files = {}
    for sid in sids:
        for fn in ("features.csv.gz", "manifest.json", "plan.json", "trades.csv.gz"):
            files[f"data-dumps/research_lab/trade_samples/{sid}/{fn}"] = {"sha256": lt.sha256_file(w["samples"] / sid / fn)}
    seal = tmp_path / "seal.json"
    seal.write_text(json.dumps({"samples": sids, "files": files}))
    res = lt.census_flow(seal=seal, sample_roots=[w["samples"]], snapshot_root=w["snap"], work=tmp_path / "work", spec=spec)
    assert not res["bad"] and res["totals"]["signed"] > 0
    assert res["ge4dec_on_grid_share"] is not None and "pass" in res["gate_E016"] and "pass" in res["gate_E018"]
    assert res["gate_E016"]["vol24_cap_defined"] and res["agreement"]["min_rows_per_arm"] == 500
    if not res["agreement"]["enough_rows"]:  # fewer than 500 rows per arm: both agreement gates fail closed
        assert not res["gate_E016"]["agreement_gap"] and not res["gate_E018"]["agreement_gap"]
    # a tampered input is refused
    p = w["samples"] / sids[0] / "plan.json"
    p.write_text(p.read_text() + " ")
    res2 = lt.census_flow(seal=seal, sample_roots=[w["samples"]], snapshot_root=w["snap"], work=tmp_path / "work2", spec=spec)
    assert any(b["sample"] == sids[0] for b in res2["bad"])


def test_end_to_end_synthetic_analysis(tmp_path):
    spec = _spec(tmp_path, k_tests=["E015", "E016", "E017", "E018", "E019"])
    spec["gates"]["draws"] = 5
    w = _world(tmp_path, 0, 40)
    root = tmp_path / "r"
    for k in range(14, 41):
        _run(w, root, spec, 14, 26, _t(k, 40))
    _run(w, root, spec, 14, 26, _t(44, 0))
    res = la.analyze(root, start_utc=_iso(G0 + timedelta(hours=28, minutes=-31)), end_utc=_iso(G0 + timedelta(hours=52, minutes=-31)),
                     spec=spec, roles=(lt.ROLE_UNREG,), force=True)
    assert res["holm"]["m"] == 5
    for t in la.TESTS:
        assert "verdict" in res[t]["verdict"]
    assert res["E015"]["counts"]["lines"] > 0 and res["E017"]["counts"]["lines"] > 0 and res["E016"]["counts"]["lines"] > 0
    res2 = la.analyze(root, start_utc=_iso(G0 + timedelta(hours=28, minutes=-31)), end_utc=_iso(G0 + timedelta(hours=52, minutes=-31)),
                      spec={**spec, "k_tests": ["E015", "E017"]}, roles=(lt.ROLE_UNREG,), force=True)
    assert res2["holm"]["m"] == 2 and res2["E016"]["verdict"]["verdict"].startswith("dropped")


# --- R1 additions: manifests, V*, label rules, verdicts, attrition, pins, size check ------------------------------------


def test_scan_captures_only_complete_manifests(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 2, samples=False)
    m = w["snap"] / w["ids"][2] / "manifest.json"
    m.write_text(json.dumps({"state": "running", "started_utc": _iso(G0 + timedelta(hours=4))}))
    st = lt.State(tmp_path / "r")
    by_slot = lt.scan_captures(w["snap"], st, spec)
    k0 = min(by_slot)
    assert [k - k0 for k in sorted(by_slot)] == [0, 1]  # the running capture is not read (and not cached: re-checked next run)
    m.write_text(json.dumps({"state": "complete", "started_utc": _iso(G0 + timedelta(hours=4))}))
    assert [k - k0 for k in sorted(lt.scan_captures(w["snap"], st, spec))] == [0, 1, 2]


def test_vol24_cap_rule():
    t = pd.DataFrame({"vol24_i": [1.0, 2.0, 3.0, 4.0, 5.0, np.nan], "trunc6": [0, 0, 0, 1, 1, 1]})
    assert lt.vol24_cap_rule(t, 0.0) == 3.0
    assert lt.vol24_cap_rule(t, 0.25) == 4.0  # cumulative share 1/4 at v = 4
    assert lt.vol24_cap_rule(t, 0.5) == np.inf  # the whole census meets it (2/5)
    assert np.isnan(lt.vol24_cap_rule(t.assign(trunc6=1), 0.0))


def test_mechanism_and_composition_label_rules():
    spec = json.loads(lt.SPEC_PATH.read_text())
    sup = {"verdict": "Supported (exploratory, prospective)"}
    good = {"testable": True, "beta": 0.004, "p": 0.01}
    weak = {"testable": True, "beta": 0.001, "p": 0.01}
    insig = {"testable": True, "beta": 0.004, "p": 0.20}
    res = {"primary": {"beta": 0.006}, "M1_sweep": good, "M3_traded_parallel": good}
    assert la.e015_labels(res, sup, spec, 5) == []
    assert la.e015_labels({**res, "M1_sweep": insig}, sup, spec, 5) == ["Gamma-quote mechanics"]
    assert la.e015_labels({**res, "M3_traded_parallel": weak}, sup, spec, 5) == ["impact/anatomy mechanics"]
    assert la.e015_labels({**res, "M1_sweep": weak}, {"verdict": "Inconclusive"}, spec, 5) == []  # labels qualify a Supported result only
    r19 = {"primary": {"beta": 0.006}, "anatomy_par": good, "M1_sweep": good, "counts": {"top_family_share_high": 0.3}}
    assert la.e019_labels(r19, sup, spec) == []
    assert la.e019_labels({**r19, "anatomy_par": weak}, sup, spec) == ["quote-anatomy composition"]
    assert la.e019_labels({**r19, "anatomy_par": insig}, sup, spec) == ["quote-anatomy composition"]
    assert la.e019_labels({**r19, "counts": {"top_family_share_high": 0.6}}, {"verdict": "Inconclusive"}, spec)[0].startswith("series-concentrated")
    r17 = {"primary": {"beta": 0.01}, "pretrend": {"testable": True, "beta": 0.006, "p": 0.01},
           "SM_coefficient": {"testable": True, "beta": 0.012, "ci95_cons": [0.005, 0.02]}}
    assert la.e017_labels(r17, sup, spec) == ["pre-existing trend", "volume, not attention-without-news"]
    assert la.e017_labels({**r17, "pretrend": {"testable": True, "beta": 0.004, "p": 0.01}, "SM_coefficient": {"testable": True, "beta": -0.01, "ci95_cons": [-0.02, 0.0]}}, sup, spec) == []
    rf = {"primary": {"beta": -0.003}, "M1_lag30": {"testable": True, "beta": -0.001, "p": 0.01}, "counts": {"truncated_share": 0.05}}
    assert la.flow_labels(rf, sup, spec, "E018") == ["possibly mechanical (stale-mid catch-up)", "coverage-limited"]


def test_verdict_gate_failure_enters_holm_with_p_one():
    r = {"testable": True, "beta": 0.01, "p": 0.001, "ci95_cons": [0.004, 0.02]}
    v = la.verdict(r, {"passes": False}, True, None, +1, "SE check failed")
    assert v["p_for_holm"] == 1.0 and v["verdict"] == "Inconclusive (SE check failed)"
    assert la.verdict(r, {"passes": True}, True, 0.01, +1, "x")["verdict"].startswith("Supported")
    assert la.verdict(r, {"passes": True}, False, 0.01, +1, "x") == {"verdict": "Unavailable", "p_for_holm": 1.0}
    assert la.verdict({**r, "beta": -0.01, "ci95_cons": [-0.02, -0.004]}, {"passes": True}, True, 0.9, +1, "x")["verdict"] == "Contradicted"
    hp = la.bd.holm({"E015": 0.001, "E016": 1.0, "E017": 0.02})
    assert hp["E015"] == pytest.approx(0.003) and hp["E016"] == 1.0


def test_attrition_rule_and_lee_bounds():
    st = np.array(["two_sided"] * 90 + ["absent"] * 10 + ["two_sided"] * 97 + ["one_sided"] * 3 + ["capture_missing"] * 50, dtype=object)
    cls = np.array([1] * 100 + [0] * 100 + [1] * 50)
    a = la.attrition(st, cls, (1, 0), 0.02)
    assert a["share"]["1"] == pytest.approx(0.10) and a["share"]["0"] == pytest.approx(0.03) and a["triggered"]
    assert a["1"]["units"] == 100  # capture_missing excluded from the shares
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"P": cls[:200], "c1": rng.normal(size=200)})
    y = rng.normal(size=200)
    b = la.lee_bounds(df, y, df["P"].to_numpy(), (1, 0), a, lambda d, yy: {"beta": float(np.mean(yy)), "p": 0.5, "testable": True})
    assert b["computed"] and b["trimmed_class"] == "0" and b["trim_share"] == pytest.approx(0.07 / 0.97)
    assert b["trim_top"]["beta"] < b["trim_bottom"]["beta"]


def test_pinned_spec_refuses_unfilled_census_values(tmp_path):
    spec = _spec(tmp_path, k_tests=["E016", "E019"])
    spec["_pinned"] = True
    spec["code_sha256"] = lt.code_hashes()
    la.code_check(spec)  # filled: accepted
    for mut in (lambda s: s["flow"].__setitem__("vol24_cap", None), lambda s: s["flow"]["zW"].__setitem__("scale", None),
                lambda s: s["e019"].__setitem__("exclude_crypto", None)):
        s2 = json.loads(json.dumps({k: v for k, v in spec.items()}))
        mut(s2)
        with pytest.raises(RuntimeError):
            la.code_check(s2)
    s3 = {**spec, "code_sha256": {**spec["code_sha256"], "live_tests3.py": "0" * 64}}
    with pytest.raises(RuntimeError):
        la.code_check(s3)


def test_census_c4_gate_includes_cluster_floor(tmp_path):
    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 26, samples=False)
    res = lt.census_captures(snapshot_root=w["snap"], work=tmp_path / "work", days=["2027-01-02", "2027-01-03"], spec=spec)
    assert set(res["C4"]["gate_E019"]) == {"high_21d", "events_both_21d", "clusters_high_census", "mde_plan", "pass"}
    assert "mde_plan" in res["C3"]["gate_E017"] and res["C4"]["mde_plan_c"] > 0
    assert "empty_slug_event_share" in res["C4"] and "top_family_high_share" in res["C4"]
    assert "mde_eff_c" in res["C1"] and "perm_strata_share_permuted" in res["C1"]


def test_size_check_small_runs_and_planted_effects_pass():
    sc = la.size_check(worlds=6, draws=19, seed=3)
    assert set(sc["scenarios"]) == {"donor_iid", "donor_ar0.6", "donor_lifecycle", "perm_iid", "perm_persistent",
                                  "donor_corr_control", "perm_corr_control",
                                  "donor_collinear_control_0.5", "donor_collinear_control_0.7"}
    assert all(0.0 <= v["rate"] <= 1.0 for v in sc["scenarios"].values()) and sc["limit"] > 0.05
    rng = np.random.default_rng(7)
    df, y, others = la.sim_flow_world(rng, effect=0.004)
    assert la.donor_gate(df, y, "x6", "zM", others, sign=+1, draws=39, seed=1, min_units=4, min_sep_s=43200.0, min_donors=2)["passes"]
    dm, ym = la.sim_move_world(rng, persistent=True, effect=0.02)
    strata = (dm["market_id"] + "|" + dm["day"]).to_numpy()
    assert la.perm_gate(dm, ym, "P", ["c1"], sign=+1, group="market_id", order="t_row", strata=strata, draws=39, seed=1, min_stratum=4)["passes"]


def test_spec_size_check_draws_match_gate_draws():
    spec = lt.load_spec(sha=None)
    assert spec["size_check"]["draws"] == spec["gates"]["draws"] == 200


def test_freedman_lane_gate_size_on_correlated_world():
    rng = np.random.default_rng(11)
    worlds, rej = 60, 0
    for _ in range(worlds):
        df, y = la.sim_move_world(rng, n_mkt=30, n_t=24, corr_control=True)
        assert abs(np.corrcoef(df["P"], df["c1"])[0, 1]) > 0.5
        strata = (df["market_id"] + "|" + df["day"]).to_numpy()
        g = la.perm_gate(df, y, "P", ["c1"], sign=+1, group="market_id", order="t_row", strata=strata, draws=49,
                         seed=int(rng.integers(1 << 31)), min_stratum=4)
        rej += int(bool(g["passes"]))
    assert rej / worlds <= 0.05 + 3 * np.sqrt(0.0475 / worlds)  # old raw-label gate sat near 0.13


# --- freeze-check fixes (LIVE_TESTS_3.md 13.9) ------------------------------------------------------------------------------


def test_write_once_round_trips_epochs_and_volumes_exactly(tmp_path):
    df = pd.DataFrame({"t_row": [1792800661.123456, 1792807861.5], "capture_t": [1792800661.932437, 1792807862.0],
                       "vol24": [123456.789012, 1000.005], "end_ts": [1793578261.0, np.nan], "s_t": [1792801012.65273, 1.0]})
    p = tmp_path / "x.csv.gz"
    assert lt.write_once_csv(p, df)
    back = pd.read_csv(p)
    for c in df.columns:
        np.testing.assert_array_equal(back[c].to_numpy(float), df[c].to_numpy(float))
    # the V+ / V0 rule needs volume differences of 0.01 to survive
    assert back["vol24"].iloc[1] - 1000.0 == pytest.approx(0.005, abs=1e-9)


def test_run_lock_prevents_two_readers(tmp_path):
    import fcntl

    spec = _spec(tmp_path)
    w = _world(tmp_path, 0, 15)
    root = tmp_path / "r"
    root.mkdir()
    with open(root / "run.lock", "a") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        st = _run(w, root, spec, 14, 15, _t(14, 40))
        assert st["status"] == "locked" and st["written"] == 0
    assert _run(w, root, spec, 14, 15, _t(14, 40))["written"] > 0


def test_nan_vol24_cap_refused_and_c2_gate_fails_closed(tmp_path):
    spec = _spec(tmp_path, k_tests=["E016"])
    spec["_pinned"] = True
    spec["code_sha256"] = lt.code_hashes()
    spec["flow"]["vol24_cap"] = float("nan")
    with pytest.raises(RuntimeError):
        la.code_check(spec)


def test_spec_dates_must_equal_module_constants(tmp_path):
    spec = json.loads(lt.SPEC_PATH.read_text())
    spec["registered_utc"] = "2026-10-25T00:00:00Z"
    p = tmp_path / "s.json"
    p.write_text(json.dumps(spec))
    with pytest.raises(RuntimeError):
        lt.load_spec(p, sha=None)


def test_crypto_regex_rulings():
    import re

    rx = re.compile(json.loads(lt.SPEC_PATH.read_text())["crypto_rule"]["slug_regex"])
    for slug in ("bitcoin-up-or-down-daily", "eth-price-weekly", "dogecoin-above", "solana-price", "btc-15m"):
        assert rx.search(slug), slug
    for slug in ("doge-government-cuts", "ethiopia-election", "ethics-committee", "us-politics"):
        assert not rx.search(slug), slug


def test_c3_c4_planning_mde_gates():
    spec = json.loads(lt.SPEC_PATH.read_text())
    a3 = spec["census_gates"]["C3_E017"]["mde_assumptions"]
    m3 = a3["t_sum"] * a3["sd_c"] / np.sqrt(1500) * a3["within"] * a3["block_factor"]
    assert m3 > 0.01  # at the old 1,500-event gate the pessimistic MDE exceeds the 1.0c floor: the new gate binds
    a4 = spec["census_gates"]["C4_E019"]["mde_assumptions"]
    m4 = a4["t_sum"] * a4["sd_c"] / np.sqrt(3000) * a4["within"] * np.sqrt(a4["deff_series"]) * a4["day_factor"]
    assert m4 > 0.005


def test_donor_statistic_is_studentised_score_invariant_to_x_scale():
    rng = np.random.default_rng(5)
    Z = rng.normal(size=(200, 2))
    x = Z[:, 0] + rng.normal(size=200)
    y = 0.3 * x + rng.normal(size=200)
    yt = la._partial(Z, y)
    s1, s2 = la.fast_score(x, Z, yt), la.fast_score(10.0 * x, Z, yt)
    assert np.isclose(s1, s2) and abs(la.fast_beta(10.0 * x, Z, yt) - la.fast_beta(x, Z, yt)) > 1e-6
    xt = la._partial(Z, x)
    assert np.isclose(s1, xt @ yt / np.sqrt(xt @ xt))


def test_donor_gate_invariant_to_moderator_scale():
    rng = np.random.default_rng(9)
    df, y, others = la.sim_flow_world(rng, n_mkt=12, n_t=20)
    a = la.donor_gate(df, y, "x6", "zM", others, sign=+1, draws=19, seed=2, min_units=4, min_sep_s=43200.0, min_donors=2)
    d2 = df.copy()
    d2["zM"] = 7.0 * d2["zM"]
    b = la.donor_gate(d2, y, "x6", "zM", others, sign=+1, draws=19, seed=2, min_units=4, min_sep_s=43200.0, min_donors=2)
    assert a["p_perm"] == b["p_perm"]


def test_collinear_control_world_has_controlled_interaction_and_runs():
    rng = np.random.default_rng(4)
    df, y, others = la.sim_flow_world(rng, n_mkt=12, n_t=20, collinear=0.7, za_effect=0.004)
    assert "x6*zA" in others and "zA" in others and {"x6*zA", "zA"} <= set(df.columns)
    assert 0.5 < np.corrcoef(df["zM"], df["zA"])[0, 1] < 0.85
    g = la.donor_gate(df, y, "x6", "zM", others, sign=+1, draws=19, seed=1, min_units=4, min_sep_s=43200.0, min_donors=2)
    assert g["testable"]


def test_within_market_r2_and_abs_corr_helper():
    rng = np.random.default_rng(2)
    n = 400
    d = pd.DataFrame({"market_id": [f"m{i // 20}" for i in range(n)], "x6": rng.normal(size=n)})
    for z in ("zN", "zSPR", "zSize", "zHTE", "zRV", "zW"):
        d[z] = rng.normal(size=n)
    assert lt.within_market_r2(d, "zW") < 0.1
    d["zW"] = d["zN"]  # x6*zW exactly a controlled interaction
    assert lt.within_market_r2(d, "zW") > 0.999
    assert lt.within_market_r2(d.head(5), "zW") is None
