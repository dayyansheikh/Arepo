# ruff: noqa: E501
"""Live tests E012-E014 (LIVE_TESTS_2.md): freezer causality, write-once, idempotency, late refusal, feature
conventions, placebo helpers and an end-to-end synthetic analysis. Synthetic data only; no network."""

from __future__ import annotations

import gzip
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests2 as lt
from astrolabe.research_lab import live_tests2_analysis as la

G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)


def _spec(tmp_path: Path) -> dict:
    spec = json.loads(lt.SPEC_PATH.read_text())
    spec["e012"]["zL"] = {"centre": 5.0, "scale": 2.0}
    spec["e012"]["econ"]["liquid_cut"] = 7.0
    spec["flow"]["zRV"] = {"centre": -4.0, "scale": 1.0}
    spec["flow"]["zSPR"] = {"centre": 0.03, "scale": 0.02}
    spec["flow"]["econ"]["lrv_upper_tercile_cut"] = -4.0
    spec["flow"]["econ"]["spr_upper_tercile_cut"] = 0.02
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec))
    s = lt.load_spec(p, sha=None)
    return s


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


N_MKT = 30


def _mid_path(m: int, k: int, rng_seed: int = 0) -> float:
    r = np.random.default_rng(1000 * m + k + rng_seed)
    return float(np.clip(0.3 + 0.01 * m + 0.02 * np.sin(k / 3.0 + m) + r.normal(0, 0.01), 0.05, 0.95))


def write_capture(snap_root: Path, k: int, *, mids: dict | None = None, state: str = "complete") -> str:
    start = G0 + timedelta(hours=2 * k)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
    d = snap_root / cid
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": state, "started_utc": _iso(start),
                                                 "pages": [{"index": 0}]}))
    rows = []
    for m in range(N_MKT):
        mid = (mids or {}).get(m, _mid_path(m, k))
        sp = 0.02 if m % 5 else 0.2  # every 5th market is wide (not tight)
        rows.append({"market_id": str(100 + m), "event_id": str(10 + m // 3), "clob_token_id_0": f"tok{m}",
                     "received_utc": _iso(start + timedelta(seconds=5 + m)), "closed": False, "active": True,
                     "binary": 1, "best_bid": round(mid - sp / 2, 4), "best_ask": round(mid + sp / 2, 4), "spread": sp,
                     "last_trade_price": mid, "chg_1h": 0.01 * ((m + k) % 3 - 1), "chg_1d": 0.02, "chg_1w": np.nan,
                     "liquidity": 1000.0 * (m + 1), "volume24hr": 50.0 * (m + 1),
                     "end_date": _iso(start + timedelta(hours=10 if m < 6 else 2000))})
    pd.DataFrame(rows).to_csv(d / "rows.csv.gz", index=False, compression="gzip")
    pd.DataFrame({"market_id": [str(100 + m) for m in range(N_MKT)], "fee_category": "politics", "fees_enabled": 1,
                  "fee_schedule": json.dumps({"exponent": 1, "rate": 0.04, "takerOnly": True})}).to_csv(
        d / "rows_ext.csv.gz", index=False, compression="gzip")
    return cid


def write_sample(sample_root: Path, snap_root: Path, cid: str, k: int, *, trades: list[dict] | None = None) -> str:
    start = G0 + timedelta(hours=2 * k)
    sid = (start + timedelta(minutes=8)).strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}"
    d = sample_root / sid
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"sample_id": sid, "state": "complete", "snapshot_id": cid, "frame": "active"}))
    (d / "plan.json").write_text(json.dumps({"strata": [{"stratum": "V0-S0", "inclusion_float": 0.25}]}))
    feats, trs = [], []
    for m in range(N_MKT):
        origin = start + timedelta(seconds=5 + m)
        ot = origin.timestamp()
        sgn = 1 if m % 2 else -1
        feats.append({"market_id": str(100 + m), "condition_id": f"c{m}", "stratum": "V0-S0", "origin_utc": _iso(origin),
                      "status": "ok", "n_returned": 4, "n_trades_1h": 2, "volume_1h": 10.0,
                      "signed_volume_1h": 10.0 * sgn if m % 4 else 0.0, "trades_truncated": False})
        for j, dt_s in enumerate((600, 3000, 7200, 18000)):
            trs.append({"market_id": str(100 + m), "condition_id": f"c{m}", "ts": ot - dt_s,
                        "side": "BUY" if sgn > 0 else "SELL", "price": 0.4, "size": 10.0 + j,
                        "outcome_index": 0, "asset": f"tok{m}", "tx_hash": f"h{m}{j}"})
    if trades is not None:
        trs = trades
    pd.DataFrame(feats).to_csv(d / "features.csv.gz", index=False, compression="gzip")
    pd.DataFrame(trs).to_csv(d / "trades.csv.gz", index=False, compression="gzip")
    return sid


def ts(k: int, minutes: float = 0.0) -> float:
    return (G0 + timedelta(hours=2 * k, minutes=minutes)).timestamp()


# 2026-10-02 00:31 is slot 12 (an E012 grid capture: hour 0)
REG = "2026-10-02T00:00:00Z"
END = "2026-10-03T00:00:00Z"


@pytest.fixture
def world(tmp_path):
    snap, samp, out = tmp_path / "snap", tmp_path / "samp", tmp_path / "out"
    snap.mkdir(), samp.mkdir()
    return snap, samp, out, _spec(tmp_path)


def test_write_once_round_trips_epochs_and_floats_exactly(tmp_path):
    # freeze-check finding (2026-10-20): "%.6g" rounded epoch seconds to ~10,000 s (00:31 origins could move to the
    # previous UTC day) and volumes to 6 digits; every float must survive the write-once file exactly
    df = pd.DataFrame({"t": [1792456260.0, 1792456261.5, np.nan], "vol24": [123456.789012, 0.1, 9.87654321e7],
                       "mid": [0.123456789, 0.5, 0.999]})
    p = tmp_path / "f.csv.gz"
    assert lt.write_once_csv(p, df)
    back = pd.read_csv(p)
    for c in df.columns:
        np.testing.assert_array_equal(back[c].to_numpy(float), df[c].to_numpy(float))


def test_write_once_never_overwrites(tmp_path):
    p = tmp_path / "a.csv.gz"
    assert lt.write_once_csv(p, pd.DataFrame({"a": [1]}))
    assert not lt.write_once_csv(p, pd.DataFrame({"a": [2]}))
    assert pd.read_csv(p)["a"].tolist() == [1]


def test_slots_and_grid(world):
    *_, spec = world
    assert lt.slot_of(ts(12), spec) == 12
    assert lt.slot_of(ts(12, 5), spec) == 12
    assert lt.slot_of(ts(12, 59), spec) is None
    assert lt.is_e012_origin(ts(12), spec) and lt.is_e012_origin(ts(15), spec)
    assert not lt.is_e012_origin(ts(13), spec)


def test_spec_sha_guard(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{}")
    with pytest.raises(RuntimeError):
        lt.load_spec(p, sha="0" * 64)


def _run(snap, samp, out, spec, now):
    return lt.run_once(snapshot_root=snap, sample_root=samp, root=out, spec=spec, registered_utc=REG, end_utc=END,
                       now=now, max_items=200)


def test_end_to_end_freeze_outcomes_idempotent(world):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    sid = write_sample(samp, snap, cids[12], 12)
    st = _run(snap, samp, out, spec, ts(12, 40))
    assert st["series"] == 13 and st["e012"] == 1 and st["flow"] == 1 and st["refused_late"] == 0
    fr = pd.read_csv(out / "e012" / "frozen" / f"{cids[12]}.csv.gz", dtype={"market_id": str})
    assert set(fr["role"]) == {lt.ROLE_UNREG}  # unpinned spec: never confirmation
    tight_h = fr["tight_h"] == 1
    assert np.isfinite(fr.loc[tight_h, "x"]).all() and fr.loc[~tight_h, "x"].isna().all()
    assert not (out / "e012" / "outcomes").exists()
    # second run: nothing new
    st2 = _run(snap, samp, out, spec, ts(12, 50))
    assert st2["written"] == 0 and st2["status"] == "nothing_new"
    # targets arrive: slot 13 (2 h), 15 (6 h), 24 (24 h)
    for k in range(13, 25):
        cids[k] = write_capture(snap, k)
    st3 = _run(snap, samp, out, spec, ts(24, 40))
    assert st3["flow_out"] == 1 and st3["e012_out"] == 1
    fo = pd.read_csv(out / "flow" / "outcomes" / f"{sid}.csv.gz")
    assert set(fo["status_j2"]) == {"evaluated"} and set(fo["status_j6"]) == {"evaluated"}
    eo = pd.read_csv(out / "e012" / "outcomes" / f"{cids[12]}.csv.gz")
    assert (eo["cap_j"] == cids[24]).all()
    before = {p: p.read_bytes() for p in out.rglob("*.csv.gz")}
    _run(snap, samp, out, spec, ts(25))
    assert all(p.read_bytes() == b for p, b in before.items())  # write-once: nothing rewritten


def test_freeze_is_causal_future_captures_do_not_change_lines(world, tmp_path):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    write_sample(samp, snap, cids[12], 12)
    _run(snap, samp, out, spec, ts(12, 40))
    a = pd.read_csv(out / "flow" / "frozen" / next((out / "flow" / "frozen").glob("*.csv.gz")).name)
    # rebuild in a second world where future captures exist with wild prices; the frozen origin lines must agree
    snap2, samp2, out2 = tmp_path / "snap2", tmp_path / "samp2", tmp_path / "out2"
    snap2.mkdir(), samp2.mkdir()
    c2 = {k: write_capture(snap2, k) for k in range(0, 13)}
    for k in range(13, 16):
        write_capture(snap2, k, mids={m: 0.9 for m in range(N_MKT)})
    write_sample(samp2, snap2, c2[12], 12)
    lt.run_once(snapshot_root=snap2, sample_root=samp2, root=out2, spec=spec, registered_utc=REG, end_utc=END,
                now=ts(12, 40), max_items=200)
    b = pd.read_csv(out2 / "flow" / "frozen" / next((out2 / "flow" / "frozen").glob("*.csv.gz")).name)
    cols = ["x6", "imb6", "rv", "zRV", "ss", "p_base", "p_aug", "dprev", "mid_i", "regime"]
    pd.testing.assert_frame_equal(a[cols], b[cols])


def test_late_freeze_refused(world, tmp_path):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    write_sample(samp, snap, cids[12], 12)
    st = _run(snap, samp, out, spec, ts(13, 0))  # 2 h target started, 6 h target future: frozen (E014 rows late)
    assert st["flow"] == 1 and st["refused_late"] == 0 and st["e012"] == 1
    snap2, samp2, out2 = tmp_path / "s2", tmp_path / "p2", tmp_path / "o2"
    snap2.mkdir(), samp2.mkdir()
    c2 = {k: write_capture(snap2, k) for k in range(0, 13)}
    write_sample(samp2, snap2, c2[12], 12)
    st = lt.run_once(snapshot_root=snap2, sample_root=samp2, root=out2, spec=spec, registered_utc=REG, end_utc=END,
                     now=ts(15, 0), max_items=200)  # the 6 h target slot has begun: refused
    assert st["flow"] == 0 and st["refused_late"] == 1
    assert list((out2 / "flow" / "frozen").glob("*.late.csv.gz"))
    st2 = lt.run_once(snapshot_root=snap2, sample_root=samp2, root=out2, spec=spec, registered_utc=REG, end_utc=END,
                      now=ts(15, 10), max_items=200)
    assert st2["refused_late"] == 0 and st2["flow"] == 0  # the marker is final


def test_trial_record_counts_eight():
    from astrolabe.research_lab import battery2

    rec = la.trial_record({"holm": {}, "E012": {"economics": {"p": 0.5}}})
    assert battery2.count_line(rec) == ("live_tests2", 8)
    assert battery2.count_line({**rec, "evidence_role": "placebo"}) == ("live_tests2", 0)


def test_e012_label_rule():
    sup = {"verdict": "Supported (exploratory, prospective)"}
    ok = {"testable": True, "beta": 0.04, "p": 0.001, "ci95_cons": [0.01, 0.07]}
    assert "possibly bounce" not in la.e012_label(sup, ok, 0.06)["verdict"]
    assert "possibly bounce" in la.e012_label(sup, {**ok, "ci95_cons": [-0.01, 0.07]}, 0.06)["verdict"]  # CI covers 0
    assert "possibly bounce" in la.e012_label(sup, {**ok, "beta": 0.02}, 0.06)["verdict"]  # < 0.5 x primary
    assert "possibly bounce" in la.e012_label(sup, {**ok, "beta": -0.02}, 0.06)["verdict"]  # wrong sign
    assert "possibly bounce" in la.e012_label(sup, {**ok, "p": 0.2}, 0.06)["verdict"]
    assert "possibly bounce" in la.e012_label(sup, {"testable": False}, 0.06)["verdict"]
    assert la.e012_label({"verdict": "Inconclusive"}, None, 0.06)["verdict"] == "Inconclusive"


def test_e013_lag_label_defines_null():
    lag = {"testable": True, "beta": 0.0015, "p": 0.01}
    assert la.check_slope_label(0.002, lag, la.E013_LABEL) is None
    assert la.check_slope_label(0.002, {**lag, "p": 0.06}, la.E013_LABEL) == la.E013_LABEL
    assert la.check_slope_label(0.002, {**lag, "beta": 0.0009}, la.E013_LABEL) == la.E013_LABEL
    assert la.check_slope_label(0.002, None, la.E013_LABEL) == la.E013_LABEL


def test_missing_target_capture(world):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    write_sample(samp, snap, cids[12], 12)
    _run(snap, samp, out, spec, ts(12, 40))
    write_capture(snap, 14)  # 13 (2 h) and 15 (6 h) never arrive
    st = _run(snap, samp, out, spec, ts(15) + 3 * 3600 + 1)
    assert st["flow_out"] == 1
    fo = pd.read_csv(next((out / "flow" / "outcomes").glob("*.csv.gz")))
    assert set(fo["status_j2"]) == {"missing_capture"} and fo["bid_j2"].isna().all()


def test_flow_window_sign_and_truncation(world):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    o = ts(12) + 5  # market 0 origin
    trades = [  # market 0: BUY outcome 0 (+), SELL outcome 1 (+), BUY outcome 1 (-); one trade after the origin
        {"market_id": "100", "condition_id": "c0", "ts": o - 100, "side": "BUY", "price": 0.5, "size": 10, "outcome_index": 0, "asset": "tok0", "tx_hash": "a"},
        {"market_id": "100", "condition_id": "c0", "ts": o - 200, "side": "SELL", "price": 0.5, "size": 10, "outcome_index": 1, "asset": "x", "tx_hash": "b"},
        {"market_id": "100", "condition_id": "c0", "ts": o - 300, "side": "BUY", "price": 0.5, "size": 20, "outcome_index": 1, "asset": "x", "tx_hash": "c"},
        {"market_id": "100", "condition_id": "c0", "ts": o + 10, "side": "BUY", "price": 0.5, "size": 999, "outcome_index": 0, "asset": "tok0", "tx_hash": "d"},
        {"market_id": "100", "condition_id": "c0", "ts": o - 7 * 3600, "side": "BUY", "price": 0.5, "size": 999, "outcome_index": 0, "asset": "tok0", "tx_hash": "e"},
        # market 1: outcome index missing, asset = token 0 -> outcome 0 fallback
        {"market_id": "101", "condition_id": "c1", "ts": o - 50, "side": "SELL", "price": 0.5, "size": 10, "outcome_index": np.nan, "asset": "tok1", "tx_hash": "f"},
    ]
    write_sample(samp, snap, cids[12], 12, trades=trades)
    _run(snap, samp, out, spec, ts(12, 40))
    fr = pd.read_csv(next((out / "flow" / "frozen").glob("*.csv.gz")), dtype={"market_id": str}).set_index("market_id")
    assert fr.loc["100", "imb6"] == pytest.approx((5 + 5 - 10) / (5 + 5 + 10))
    assert fr.loc["100", "n6"] == 3
    assert fr.loc["101", "imb6"] == pytest.approx(-1.0)
    assert np.isnan(fr.loc["102", "imb6"])  # no trades in the window -> NaN, never 0
    assert fr.loc["100", "n_post_origin"] == 1 and fr.loc["101", "n_post_origin"] == 0
    assert fr.loc["102", "n6"] == 0 and fr.loc["102", "cov6"] == 1  # covered, no trades (not truncated)


def test_truncated_window_is_nan(world):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    o = ts(12) + 5
    trades = [{"market_id": "100", "condition_id": "c0", "ts": o - 30 * (i + 1), "side": "BUY", "price": 0.5, "size": 1,
               "outcome_index": 0, "asset": "tok0", "tx_hash": str(i)} for i in range(500)]
    d = samp
    sid = write_sample(d, snap, cids[12], 12, trades=trades)
    f = pd.read_csv(d / sid / "features.csv.gz")
    f.loc[f["market_id"] == 100, "n_returned"] = 500  # a full page whose oldest trade is inside the 6 h window
    f.to_csv(d / sid / "features.csv.gz", index=False, compression="gzip")
    _run(snap, samp, out, spec, ts(12, 40))
    fr = pd.read_csv(next((out / "flow" / "frozen").glob("*.csv.gz")), dtype={"market_id": str}).set_index("market_id")
    assert np.isnan(fr.loc["100", "imb6"])


def test_e014_frozen_predictions_and_regimes(world):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    write_sample(samp, snap, cids[12], 12)
    _run(snap, samp, out, spec, ts(12, 40))
    fr = pd.read_csv(next((out / "flow" / "frozen").glob("*.csv.gz")))
    b, a = spec["e014"]["base"], spec["e014"]["augmented"]
    np.testing.assert_allclose(fr["p_base"], b["intercept"] + b["chg_1h"] * fr["chg_1h"], rtol=1e-5)
    np.testing.assert_allclose(fr["p_aug"], a["intercept"] + a["chg_1h"] * fr["chg_1h"] + a["signed_share"] * fr["ss"], rtol=1e-5)
    assert set(fr.loc[fr["market_id"] < 106, "regime"]) == {"A"} and set(fr.loc[fr["market_id"] >= 106, "regime"]) == {"B"}


def test_rebuild_series_keeps_run_starts_and_increment_pool():
    codes = np.array([0, 0, 0, 0, 0, 1, 1])
    slots = np.array([1, 2, 3, 5, 6, 1, 2])
    mids = np.array([0.5, 0.6, 0.7, 0.2, 0.3, 0.4, 0.4])
    out = la.rebuild_series(codes, slots, mids, 3)
    assert out[0] == 0.5 and out[3] == 0.2 and out[5] == 0.4  # run starts kept
    assert out[6] == pytest.approx(0.4)  # market 1's only increment is 0
    inc = {round(v, 6) for v in (out[1] - out[0], out[2] - out[1], out[4] - out[3])}
    assert inc <= {0.1}


def test_demeaned_fit_finds_planted_interaction():
    rng = np.random.default_rng(1)
    n_m, T = 300, 20
    m = np.repeat(np.arange(n_m), T)
    t = np.tile(np.arange(T), n_m).astype(float)
    z = np.repeat(rng.normal(size=n_m), T)
    x = rng.normal(size=n_m * T)
    y = 0.5 * x * z + 0.2 * x + rng.normal(size=n_m * T)
    # 20 time clusters (the window has 21 UTC days); the primary p refers the two-way z to t with G - 1 = 19 df
    df = pd.DataFrame({"market_id": m.astype(str), "event_id": (m // 3).astype(str), "day": t.astype(int).astype(str),
                       "t": t, "ix": x * z, "x": x, "z": z})
    r = la.demeaned_fit(df, y, "ix", ["x", "z"], "t", seed=1, n_boot=50)
    # expanding-past demeaning attenuates under the alternative (x_past enters the omitted term): conservative
    assert r["testable"] and 0.35 < r["beta"] < 0.55 and r["p"] < 1e-6
    assert r["t_df"] == 18 and r["p"] >= r["p_twoway"]  # day 0 holds only first rows, dropped by the demeaning
    yn = 0.2 * x + rng.normal(size=n_m * T)
    rn = la.demeaned_fit(df, yn, "ix", ["x", "z"], "t", seed=1, n_boot=50)
    assert rn["p"] > 0.001


def test_paper_taker_conventions():
    df = pd.DataFrame({"bid_i": [0.40, 0.40], "ask_i": [0.42, 0.42], "bid_j": [0.50, 0.30], "ask_j": [0.52, 0.32],
                       "fee_rate": [0.0, 0.0], "fee_exp": [1.0, 1.0]})
    pnl = la.paper_taker(df, np.array([1, -1]), "j")
    assert pnl[0] == pytest.approx(0.50 - 0.42) and pnl[1] == pytest.approx(0.40 - 0.32)
    df["fee_rate"] = 0.04
    assert la.paper_taker(df, np.array([1, 1]), "j")[0] < 0.08


def test_e014_tests_detects_near_end_gain():
    rng = np.random.default_rng(2)
    n_m, T = 600, 10
    n = n_m * T
    mk = np.repeat(np.arange(n_m), T)
    A = np.repeat(rng.random(n_m) < 0.5, T)  # a market is in one regime
    ss = rng.choice([-1.0, -0.5, 0.5, 1.0], n)
    beta = np.where(A, 0.02, 0.0)  # flow predicts only near the end
    y = beta * ss + rng.normal(0, 0.01, n)
    spec = json.loads(lt.SPEC_PATH.read_text())
    c = spec["e014"]["augmented"]
    e = pd.DataFrame({"market_id": mk.astype(str), "event_id": (mk // 2).astype(str),
                      "day": rng.integers(0, 12, n).astype(str), "t_row": np.tile(np.arange(T) * 7200.0, n_m),
                      "regime": np.where(A, "A", "B"),
                      "ss": ss, "chg_1h": 0.0, "p_base": spec["e014"]["base"]["intercept"],
                      "p_aug": c["intercept"] + c["signed_share"] * ss, "mid_i": 0.5, "bid_j2": 0.5 + y - 0.005,
                      "ask_j2": 0.5 + y + 0.005, "bid_i": 0.495, "ask_i": 0.505, "fee_rate": 0.0, "fee_exp": 1.0,
                      "n_trades_1h": 5, "p_incl": 0.2})
    r = la.e014_tests(e, {}, spec)
    assert r["available"] and r["primary"]["beta"] > 0 and r["primary"]["p"] < 0.001
    assert r["placebo"]["gate"]["passes"] and r["placebo"]["gate"]["p_gate"] < 1e-6
    v = la.verdict("E014", r["primary"], r["placebo"], r["available"], 0.001)
    assert v["verdict"].startswith("Supported")
    # no timing information: flow is a market-level constant -> the gate must fail even with a big pooled contrast
    e2 = e.copy()
    mk = e2["market_id"].astype(int).to_numpy()
    e2["ss"] = np.where(mk % 2, 1.0, -1.0)
    e2["p_aug"] = c["intercept"] + c["signed_share"] * e2["ss"]
    y2 = np.where(A, 0.02, 0.0) * e2["ss"].to_numpy() + rng.normal(0, 0.01, n)
    e2["bid_j2"], e2["ask_j2"] = 0.5 + y2 - 0.005, 0.5 + y2 + 0.005
    r2 = la.e014_tests(e2, {}, spec)
    assert r2["primary"]["p"] < 0.001 and not r2["placebo"]["gate"]["passes"]
    assert la.verdict("E014", r2["primary"], r2["placebo"], True, 0.001)["verdict"].startswith("Inconclusive")


def test_analyze_runs_end_to_end_and_refuses_early(world):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    for k in range(12, 20):
        if k > 12:
            cids[k] = write_capture(snap, k)
        write_sample(samp, snap, cids[k], k)
        _run(snap, samp, out, spec, ts(k, 40))
    for k in range(20, 34):
        write_capture(snap, k)
    _run(snap, samp, out, spec, ts(34))
    with pytest.raises(RuntimeError):
        la.analyze(out, start_utc=REG, end_utc=END, spec=spec)
    res = la.analyze(out, start_utc=REG, end_utc=END, spec=spec, roles=(lt.ROLE_UNREG,), placebo_draws=2, force=True)
    assert res["holm"]["m"] == 4 and set(res["holm"]["p_raw"]) == {"E012", "E013_F4", "E013_F5", "E014"}
    for k in ("E012", "E013_F4", "E013_F5", "E014"):
        assert res[k]["verdict"]["verdict"].startswith("Unavailable")  # synthetic world is far below the floors
    assert set(res["code_sha256"]) == {"live_tests2.py", "live_tests2_analysis.py"}
    assert "post_origin_trades_on_page" in res["E013_F4"]["accounting"]
    assert "status_j2_by_regime_flow_rows" in res["E014"]["accounting"]
    ops = lt.ops_stats(out)
    assert ops["flow/frozen"]["files"] == 8 and ops["e012/frozen"]["files"] == 3


def test_ops_stats_reads_no_prices(world, monkeypatch):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    write_sample(samp, snap, cids[12], 12)
    _run(snap, samp, out, spec, ts(12, 40))
    real = pd.read_csv

    def guarded(path, *a, **kw):
        cols = kw.get("usecols")
        assert cols is not None and not any(c.startswith(("bid", "ask", "mid", "x", "y")) for c in cols)
        return real(path, *a, **kw)

    monkeypatch.setattr(lt.pd, "read_csv", guarded)
    st = lt.ops_stats(out)
    assert st["e012/frozen"]["files"] == 1


def test_capture_not_complete_is_ignored(world):
    snap, samp, out, spec = world
    for k in range(0, 12):
        write_capture(snap, k)
    write_capture(snap, 12, state="partial")
    st = _run(snap, samp, out, spec, ts(12, 40))
    assert st["e012"] == 0


def test_gzip_files_are_valid(world):
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    write_sample(samp, snap, cids[12], 12)
    _run(snap, samp, out, spec, ts(12, 40))
    for p in out.rglob("*.csv.gz"):
        with gzip.open(p) as fh:
            assert fh.read(10)


# --- challenger round 1 (LIVE_TESTS_2.md section 9) ------------------------------------------------------------------


def _rewrite_rows(snap: Path, cid: str, fn) -> None:
    p = snap / cid / "rows.csv.gz"
    rows = pd.read_csv(p, dtype={"market_id": str, "event_id": str})
    fn(rows).to_csv(p, index=False, compression="gzip")


def test_status_files_give_the_unavailable_reason(world):
    """Finding 3: the collector writes a per-capture status, so closed / one-sided / absent are distinguishable."""
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    sid = write_sample(samp, snap, cids[12], 12)
    _run(snap, samp, out, spec, ts(12, 40))
    for k in range(13, 16):
        cids[k] = write_capture(snap, k)

    def edit(r):
        r.loc[r["market_id"] == "101", "closed"] = True  # resolved
        r.loc[r["market_id"] == "102", "best_bid"] = 0.0  # one-sided
        return r[r["market_id"] != "103"]  # absent from the listing

    _rewrite_rows(snap, cids[15], edit)
    _run(snap, samp, out, spec, ts(15, 40))
    st = pd.read_csv(out / "status" / f"{cids[15]}.csv.gz", dtype={"market_id": str}).set_index("market_id")
    assert st.loc["101", "st"] == "closed" and st.loc["102", "st"] == "one_sided" and "103" not in st.index
    fo = pd.read_csv(out / "flow" / "outcomes" / f"{sid}.csv.gz", dtype={"market_id": str}).set_index("market_id")
    assert fo.loc["101", "status_j6"] == "unavailable_closed"
    assert fo.loc["102", "status_j6"] == "unavailable_one_sided"
    assert fo.loc["103", "status_j6"] == "unavailable_absent"
    assert fo.loc["104", "status_j6"] == "evaluated" and fo.loc["101", "status_j2"] == "evaluated"


def test_attrition_summary_and_e014_bounds():
    st = np.array(["evaluated"] * 90 + ["unavailable_closed"] * 10 + ["evaluated"] * 99 + ["unavailable_one_sided"])
    grp = np.array(["A"] * 100 + ["B"] * 100)
    a = la.attrition_summary(st, grp, ("A", "B"))
    assert a["triggered"] and a["diff"] == pytest.approx(0.09) and a["A"]["by_reason"] == {"unavailable_closed": 10}
    st_small = np.array(["evaluated"] * 97 + ["unavailable_closed"] * 3 + ["evaluated"] * 99 + ["unavailable"])
    assert not la.attrition_summary(st_small, grp, ("A", "B"))["triggered"]  # 3% vs 1%: below 5 pp
    rng = np.random.default_rng(0)
    n = 200
    b = pd.DataFrame({"regime": grp, "p_base": 0.001, "p_aug": 0.001 + 0.005 * rng.choice([-1.0, 1.0], n),
                      "mid_i": 0.5})
    y = rng.normal(0, 0.02, n)
    avail = st == "evaluated"
    bd_ = la.e014_attrition_bounds(b, y, avail)
    assert bd_["worst_case_contrast"] <= bd_["pessimistic_contrast"]
    assert bd_["imputed_A"] == 10 and bd_["imputed_B"] == 1


def test_flow_truncated_1h_window_makes_ss_nan_and_volume_recorded(world):
    """Finding 4: E014's ss is NaN when the trade sample flags the 1 h window truncated; vol24_i is origin-side."""
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    sid = write_sample(samp, snap, cids[12], 12)
    f = pd.read_csv(samp / sid / "features.csv.gz")
    f.loc[f["market_id"] == 101, "trades_truncated"] = True
    f.to_csv(samp / sid / "features.csv.gz", index=False, compression="gzip")
    _run(snap, samp, out, spec, ts(12, 40))
    fr = pd.read_csv(next((out / "flow" / "frozen").glob("*.csv.gz")), dtype={"market_id": str}).set_index("market_id")
    assert np.isnan(fr.loc["101", "ss"]) and np.isnan(fr.loc["101", "p_aug"]) and fr.loc["101", "trunc1h"] == 1
    assert fr.loc["103", "ss"] != 0 and fr.loc["103", "trunc1h"] == 0
    assert fr.loc["105", "vol24_i"] == pytest.approx(50.0 * 6)
    assert fr["code_sha"].astype(str).eq(lt.collector_sha()).all()


def test_vol24_cap_rule():
    F = pd.DataFrame({"tight_i": 1, "n6": [3] * 6 + [0, np.nan], "cov6": [1, 1, 1, 1, 0, 0, 1, 0],
                      "vol24_i": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 5.0, 70.0], "trunc1h": 0.0})
    # candidates exclude the covered no-trade row (vol 5); truncated at 50, 60 and 70
    assert lt.vol24_cap_rule(F, 0.0) == 40.0
    assert lt.vol24_cap_rule(F, 0.2) == 50.0  # 1 / 5 truncated at <= 50
    assert lt.vol24_cap_rule(F, 0.5) == float("inf")  # 3 / 7 overall
    tc = lt.truncation_census(F, {"flow": {"vol24_cap_max_trunc_share": 0.0}})
    assert tc["trunc6"] == {"rows": 7, "truncated": 3, "share": pytest.approx(3 / 7)} and tc["vol24_cap"] == 40.0


def test_e012_skip_slot_6h_is_frozen(world):
    """Finding 2: x_skip6 = mid_{i-3} - mid_h, from series files only (never mid_i)."""
    snap, samp, out, spec = world
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    _run(snap, samp, out, spec, ts(12, 40))
    fr = pd.read_csv(out / "e012" / "frozen" / f"{cids[12]}.csv.gz", dtype={"market_id": str})
    ser = pd.read_csv(out / "series" / f"{cids[9]}.csv.gz", dtype={"market_id": str}).set_index("market_id")
    m = fr[(fr["tight_h"] == 1) & (fr["tight_s3"] == 1)]
    assert len(m) > 10
    mid9 = ((ser["bid"] + ser["ask"]) / 2.0).reindex(m["market_id"]).to_numpy()
    np.testing.assert_allclose(m["mid_s3"], mid9, rtol=1e-5)
    np.testing.assert_allclose(m["x_skip6"], m["mid_s3"] - m["mid_h"], atol=1e-5)
    assert fr.loc[fr["tight_s3"] != 1, "x_skip6"].isna().all()


def test_gate_sources_respect_separation():
    codes = np.array([0, 0, 0, 0, 0, 0, 1, 1, 1])
    t = np.array([0, 2, 4, 6, 8, 20, 0, 2, 30], float) * 3600
    src = np.array([1, 1, 1, 1, 1, 1, 1, 0, 1], bool)
    gs = la.gate_sources(codes, t, src, 6 * 3600)
    assert gs["n"].tolist() == [3, 2, 1, 2, 3, 5, 1, 1, 1]  # e.g. t = 4 h: only 20 h is >= 6 h away
    rows = np.flatnonzero(src)
    fs = la.forward_sources(codes, t, rows, 6 * 3600, 1)
    v = np.arange(9, dtype=float) * 10
    want = {}
    for i in rows:  # brute force: mean of v over later source rows of the same market >= 6 h later
        later = [j for j in rows if codes[j] == codes[i] and t[j] - t[i] >= 6 * 3600]
        if later:
            want[i] = np.mean(v[later])
    assert fs["rows"].tolist() == sorted(want)
    np.testing.assert_allclose(la.source_mean(fs, v), [want[i] for i in fs["rows"]])
    assert la.forward_sources(codes, t, rows, 6 * 3600, 2)["rows"].tolist() == [0, 1]
    assert la.gate_p(float("nan"), 50) == 1.0 and la.gate_p(3.0, 1) == 1.0 and la.gate_p(3.0, 50) < 0.01


def test_p_primary_uses_t_reference_with_g_minus_1_df():
    r = {"beta": 1.0, "se_event": 0.4, "se_twoway": 0.5, "z_twoway": 2.0, "p_event": 0.0062, "p_twoway": 0.0228,
         "n_day": 6, "ci_event_boot": [0.3, 1.7]}
    la.p_primary(r)
    from scipy.stats import t as tt

    assert r["p"] == pytest.approx(tt.sf(2.0, 5)) and r["p"] > 0.0228 and r["t_df"] == 5
    assert r["ci95_cons"][0] == pytest.approx(1.0 - tt.ppf(0.975, 5) * 0.5)
    assert la.p_primary({**r, "n_day": 1})["p"] == 1.0


# --- simulated nulls of the timing gate (finding 1). Synthetic data only, seeded, vectorised. Each scenario runs
# N_SIM null worlds at the gate's alpha 0.05 and records the rejection rate (printed with -s). The assertion allows
# Monte Carlo error only: it fails if the number of rejections exceeds the 99% binomial quantile at 0.05, so a
# true size above 0.05 by a few points is detected while a size of exactly 0.05 fails with probability < 1%.
# Reproducible larger run (LIVE_TESTS_2.md section 1.5): from backend/,
#   LT2_N_SIM=1500 LT2_SIZE_OUT=../docs/research_lab/seals/lt2_gate_null_size_1500.json \
#     pytest tests/unit/test_research_lab_live_tests2.py -k null_size -q
# The seeds are fixed in the tests below, so the first 300 worlds of every scenario equal the unit-test worlds.
N_SIM = int(os.environ.get("LT2_N_SIM", "300"))
SIZE_RATES: dict = {}
SIZE_COUNTS: dict = {}


@pytest.fixture(scope="module", autouse=True)
def _dump_size_rates():
    yield
    out = os.environ.get("LT2_SIZE_OUT")
    if out and SIZE_COUNTS:
        tot_r = sum(r for r, _ in SIZE_COUNTS.values())
        tot_n = sum(n for _, n in SIZE_COUNTS.values())
        Path(out).write_text(json.dumps({
            "n_sim_per_scenario": N_SIM, "alpha": 0.05,
            "scenarios": {k: {"rejections": r, "worlds": n, "rate": r / n} for k, (r, n) in sorted(SIZE_COUNTS.items())},
            "pooled": {"rejections": tot_r, "worlds": tot_n, "rate": tot_r / tot_n},
            "command": "LT2_N_SIM=1500 LT2_SIZE_OUT=<path> pytest tests/unit/test_research_lab_live_tests2.py -k null_size",
        }, indent=1, sort_keys=True) + "\n")


def _null_tolerance(n: int) -> int:
    from scipy.stats import binom

    return int(binom.ppf(0.99, n, 0.05))


def _flat(rng, arrs: dict, keep: float, short: np.ndarray | None = None) -> pd.DataFrame:
    n_m, T = next(iter(arrs.values())).shape
    mask = rng.random((n_m, T)) < keep
    if short is not None:
        mask[short, 6:] = False
    m = np.repeat(np.arange(n_m)[:, None], T, axis=1)
    k = np.repeat(np.arange(T)[None, :], n_m, axis=0)
    out = {"m": m[mask], "t": (k * 7200.0 + m)[mask]}
    out.update({c: v[mask] for c, v in arrs.items()})
    return pd.DataFrame(out)


def _e013_world(rng, kind: str, effect: float = 0.0, n_m: int = 300, T: int = 16, keep: float = 1.0) -> pd.DataFrame:
    """A strong between-market link (y's market drift moves with the market's flow x moderator) and no timing link,
    plus ``effect`` x x z. iid: flow iid around the market mean; ar1: persistent flow (phi 0.8); overlap: x = flow of
    the 3 slots before t and y = the price impact (moderated by z) of the 3 slots after it, so neighbouring rows'
    flow windows and targets overlap as with 6 h windows on the 2 h grid."""
    mu, zm = rng.normal(0, 0.4, (n_m, 1)), rng.normal(0, 1, (n_m, 1))
    z = zm + rng.normal(0, 0.3, (n_m, T))
    link = 0.5 * mu * (1 + zm)
    if kind == "iid":
        x = mu + rng.normal(0, 0.5, (n_m, T))
        y = link + rng.normal(0, 1, (n_m, T))
    elif kind == "ar1":
        a = np.empty((n_m, T))
        a[:, 0] = rng.normal(0, 0.5, n_m)
        for k in range(1, T):
            a[:, k] = 0.8 * a[:, k - 1] + rng.normal(0, 0.3, n_m)
        x = mu + a
        y = link + rng.normal(0, 1, (n_m, T))
    else:
        phi = rng.normal(0, 1, (n_m, T + 6))
        x = mu + np.stack([phi[:, k:k + 3].mean(axis=1) for k in range(T)], axis=1)
        zp = np.concatenate([z, np.repeat(z[:, -1:], 3, axis=1)], axis=1)
        u = 0.5 * (1 + 0.5 * zp) * phi[:, 3:] + rng.normal(0, 1, (n_m, T + 3))
        y = link + np.stack([u[:, k:k + 3].sum(axis=1) for k in range(T)], axis=1)
    y = y + effect * x * z
    short = np.arange(n_m) < n_m // 6  # 6-row markets: no row has 4 sources 12 h later
    return _flat(rng, {"x": x, "z": z, "y": y, "c": rng.normal(0, 1, (n_m, T))}, keep, short)


def _e013_gate(w: pd.DataFrame) -> dict:
    return la.slope_gate(w["m"].to_numpy(), w["t"].to_numpy(), w["x"].to_numpy(), np.arange(len(w)),
                         w["y"].to_numpy(), w["z"].to_numpy(), w[["c"]].to_numpy(), min_rows=100, min_markets=20)


@pytest.mark.parametrize("kind,keep", [("iid", 1.0), ("ar1", 1.0), ("overlap", 1.0), ("overlap", 0.6)])
def test_e013_gate_null_size(kind, keep):
    rng = np.random.default_rng({"iid": 11, "ar1": 12, "overlap": 13}[kind] + int(keep * 10))
    rej = 0
    for _ in range(N_SIM):
        g = _e013_gate(_e013_world(rng, kind, keep=keep))
        assert g["testable"] and g["gate_markets"] <= 250  # the 6-row markets never enter the gate
        rej += g["passes"]
    SIZE_RATES[f"E013 {kind} keep={keep}"] = rej / N_SIM
    SIZE_COUNTS[f"E013 {kind} keep={keep}"] = (rej, N_SIM)
    print(f"E013 gate null size {kind} keep={keep}: {rej}/{N_SIM} = {rej / N_SIM:.3f}")
    assert rej <= _null_tolerance(N_SIM), (kind, rej)


def test_e013_gate_has_power_against_a_timed_effect():
    rng = np.random.default_rng(14)
    passes = sum(_e013_gate(_e013_world(rng, "ar1", effect=0.4))["passes"] for _ in range(40))
    assert passes >= 32
    # the null worlds of the size tests are not trivial: a POOLED (not demeaned) interaction slope is driven by the
    # between-market link and is strongly positive, so a pooled test would reject; the gate's size under the same
    # worlds is checked by test_e013_gate_null_size (a single null draw passes the gate with probability ~0.05, so
    # no one-draw gate assertion is made here)
    w = _e013_world(np.random.default_rng(15), "iid")
    X = np.column_stack([np.ones(len(w)), w["x"] * w["z"], w["x"], w["z"]])
    b = np.linalg.lstsq(X, w["y"].to_numpy(), rcond=None)[0]
    assert b[1] > 0.1


def _e014_world(rng, kind: str, n_m: int = 240, T: int = 12, effect: float = 0.0) -> pd.DataFrame:
    """A markets (even) and B markets (odd); the 2 h target carries a market-level link to the market's flow and no
    timing link. iid / ar1 flow; const: flow constant within the market; overlap: ss = flow of the hour before the
    origin and the target = impact of the next 2 hours, so the next row's flow hour lies inside the target."""
    A = (np.arange(n_m) % 2 == 0)[:, None]
    mu = rng.normal(0, 0.5, (n_m, 1))
    if kind == "iid":
        ss = np.clip(mu + rng.normal(0, 0.5, (n_m, T)), -1, 1)
    elif kind == "ar1":
        a = np.empty((n_m, T))
        a[:, 0] = rng.normal(0, 0.5, n_m)
        for k in range(1, T):
            a[:, k] = 0.8 * a[:, k - 1] + rng.normal(0, 0.3, n_m)
        ss = np.tanh(mu + a)
    elif kind == "const":
        ss = np.repeat(np.where(rng.random((n_m, 1)) < 0.5, 1.0, -1.0), T, axis=1)
    else:
        f = rng.normal(0, 1, (n_m, 2 * T + 2))
        ss = np.tanh(mu + f[:, 1:2 * T:2])
    link = np.where(A, 0.02, 0.0) * (ss.mean(axis=1, keepdims=True) if kind == "const" else np.tanh(mu))
    y = link + rng.normal(0, 0.01, (n_m, T))
    if kind == "overlap":
        y = y + np.where(A, 0.01, 0.002) * (f[:, 2:2 * T + 1:2] + f[:, 3:2 * T + 2:2])
    y = y + effect * A * ss
    ss = np.where(ss == 0, 0.01, ss)
    return _flat(rng, {"ss": ss, "y": y, "A": np.repeat(A, T, axis=1).astype(float),
                       "chg": rng.normal(0, 0.01, (n_m, T))}, 1.0)


def _e014_gate(w: pd.DataFrame, spec: dict) -> dict:
    return la.contrast_gate(w["m"].to_numpy(), w["t"].to_numpy(), w["ss"].to_numpy(), np.arange(len(w)),
                            w["y"].to_numpy(), w["chg"].to_numpy(), w["A"].to_numpy(), spec["e014"]["augmented"],
                            spec["e014"]["base"])


@pytest.mark.parametrize("kind", ["iid", "ar1", "const", "overlap"])
def test_e014_gate_null_size(kind):
    spec = json.loads(lt.SPEC_PATH.read_text())
    rng = np.random.default_rng({"iid": 21, "ar1": 22, "const": 23, "overlap": 24}[kind])
    rej = 0
    for _ in range(N_SIM):
        g = _e014_gate(_e014_world(rng, kind), spec)
        assert g["testable"]
        rej += g["passes"]
    SIZE_RATES[f"E014 {kind}"] = rej / N_SIM
    SIZE_COUNTS[f"E014 {kind}"] = (rej, N_SIM)
    print(f"E014 gate null size {kind}: {rej}/{N_SIM} = {rej / N_SIM:.3f}")
    assert rej <= _null_tolerance(N_SIM), (kind, rej)


def test_e014_gate_has_power_against_a_timed_effect():
    spec = json.loads(lt.SPEC_PATH.read_text())
    rng = np.random.default_rng(25)
    assert sum(_e014_gate(_e014_world(rng, "overlap", effect=0.01), spec)["passes"] for _ in range(20)) >= 18


# --- code and spec pins (finding 6) ----------------------------------------------------------------------------------


def test_code_hash_ignores_only_the_pin_line(tmp_path):
    src = lt.Path(lt.__file__).read_text()
    a, b = tmp_path / "a.py", tmp_path / "b.py"
    a.write_text(src)
    b.write_text(src.replace("SPEC_SHA256 = None", 'SPEC_SHA256 = "' + "f" * 64 + '"', 1))
    assert lt.code_sha256(a) == lt.code_sha256(b)
    b.write_text(src + "\n# changed\n")
    assert lt.code_sha256(a) != lt.code_sha256(b)


def test_spec_code_hash_map_matches_the_modules():
    pins = json.loads(lt.SPEC_PATH.read_text())["code_sha256"]
    assert {n: pins[n] for n in lt.CODE_FILES} == lt.code_hashes(), "refresh model_specs/live_tests2_v1.json code_sha256"


def _pinned_spec(tmp_path: Path, **over) -> dict:
    spec = json.loads(lt.SPEC_PATH.read_text())
    spec["code_sha256"].update(lt.code_hashes())
    spec["flow"]["vol24_cap"] = 1e12
    for k, v in over.items():
        spec[k] = v
    p = tmp_path / "pinned.json"
    p.write_text(json.dumps(spec))
    return lt.load_spec(p, sha=lt.sha256_file(p))


def test_pinned_analysis_keeps_only_registered_lines_and_refuses_mismatch(world, tmp_path):
    snap, samp, out, _ = world
    spec = _pinned_spec(tmp_path)
    cids = {k: write_capture(snap, k) for k in range(0, 13)}
    for k in range(12, 16):
        if k > 12:
            cids[k] = write_capture(snap, k)
        write_sample(samp, snap, cids[k], k)
        _run(snap, samp, out, spec, ts(k, 40))
    for k in range(16, 30):
        write_capture(snap, k)
    _run(snap, samp, out, spec, ts(30))
    files = sorted((out / "flow" / "frozen").glob("*.csv.gz"))
    fr = pd.read_csv(files[0])
    assert set(fr["role"]) == {lt.ROLE_CONF}
    fr["code_sha"] = "0123456789abcdef"  # simulate lines written by other collector code
    fr.to_csv(files[0], index=False, compression="gzip")
    res = la.analyze(out, start_utc=REG, end_utc=END, spec=spec, placebo_draws=2, force=True)
    acc = res["E013_F4"]["accounting"]
    assert acc["dropped_code_sha"] == len(fr) and acc["lines"] == (len(files) - 1) * len(fr)
    assert res["E012"]["accounting"]["dropped_code_sha"] == 0 and res["code_check"]["label"] is None
    bad = _pinned_spec(tmp_path, code_sha256={"live_tests2.py": "0" * 64, "live_tests2_analysis.py": "0" * 64})
    with pytest.raises(RuntimeError, match="code sha256"):
        la.analyze(out, start_utc=REG, end_utc=END, spec=bad, force=True)
    nocap = _pinned_spec(tmp_path)
    nocap["flow"]["vol24_cap"] = None
    with pytest.raises(RuntimeError, match="vol24_cap"):
        la.analyze(out, start_utc=REG, end_utc=END, spec=nocap, force=True)


def test_runner_refuses_dry_run_into_the_live_root(capsys):
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "scripts" / "run_live_tests2.py"
    spec = importlib.util.spec_from_file_location("run_live_tests2_cli", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rc = mod.main(["run", "--dry-run-start", "2026-10-20T00:00:00Z", "--root", str(lt.OUT_ROOT)])
    assert rc == 2 and "refused" in capsys.readouterr().out
