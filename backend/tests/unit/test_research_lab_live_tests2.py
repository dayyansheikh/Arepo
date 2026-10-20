# ruff: noqa: E501
"""Live tests E012-E014 (LIVE_TESTS_2.md): freezer causality, write-once, idempotency, late refusal, feature
conventions, placebo helpers and an end-to-end synthetic analysis. Synthetic data only; no network."""

from __future__ import annotations

import gzip
import json
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
                      "signed_volume_1h": 10.0 * sgn if m % 4 else 0.0})
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
    assert "mechanical not excluded" in la.e012_label(sup, {"testable": True, "ci95_cons": [-0.01, 0.05]})["verdict"]
    assert "mechanical" not in la.e012_label(sup, {"testable": True, "ci95_cons": [0.01, 0.05]})["verdict"]
    assert la.e012_label({"verdict": "Inconclusive"}, None)["verdict"] == "Inconclusive"


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


def test_perm_gate():
    g = la.perm_gate(1.0, [0.0] * 99)
    assert g["passes"] and g["p_perm"] == pytest.approx(0.01)
    assert not la.perm_gate(1.0, [2.0] * 99)["passes"]


def test_cyclic_shift_never_keeps_own_value():
    codes = np.array([0, 0, 0, 1, 2, 2])
    order = np.array([3, 1, 2, 1, 1, 2], float)
    vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    for s in range(20):
        out = la.cyclic_shift_within(codes, order, vals, s)
        assert np.isnan(out[3])  # singleton market
        keep = ~np.isnan(out)
        assert not np.any(out[keep] == vals[keep])
        assert sorted(out[:3]) == [1.0, 2.0, 3.0]


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
    df = pd.DataFrame({"market_id": m.astype(str), "event_id": (m // 3).astype(str), "day": (t // 5).astype(int).astype(str),
                       "t": t, "ix": x * z, "x": x, "z": z})
    r = la.demeaned_fit(df, y, "ix", ["x", "z"], "t", seed=1, n_boot=50)
    # expanding-past demeaning attenuates under the alternative (x_past enters the omitted term): conservative
    assert r["testable"] and 0.35 < r["beta"] < 0.55 and r["p"] < 1e-6
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
    n = 6000
    A = rng.random(n) < 0.5
    ss = rng.choice([-1.0, -0.5, 0.5, 1.0], n)
    beta = np.where(A, 0.02, 0.0)  # flow predicts only near the end
    y = beta * ss + rng.normal(0, 0.01, n)
    spec = json.loads(lt.SPEC_PATH.read_text())
    c = spec["e014"]["augmented"]
    e = pd.DataFrame({"market_id": rng.integers(0, 1500, n).astype(str), "event_id": rng.integers(0, 700, n).astype(str),
                      "day": rng.integers(0, 12, n).astype(str), "t_row": np.arange(n, dtype=float), "regime": np.where(A, "A", "B"),
                      "ss": ss, "chg_1h": 0.0, "p_base": spec["e014"]["base"]["intercept"],
                      "p_aug": c["intercept"] + c["signed_share"] * ss, "mid_i": 0.5, "bid_j2": 0.5 + y - 0.005,
                      "ask_j2": 0.5 + y + 0.005, "bid_i": 0.495, "ask_i": 0.505, "fee_rate": 0.0, "fee_exp": 1.0,
                      "n_trades_1h": 5, "p_incl": 0.2})
    r = la.e014_tests(e, {}, spec, placebo_draws=99)
    assert r["available"] and r["primary"]["beta"] > 0 and r["primary"]["p"] < 0.001
    assert r["placebo"]["gate"]["passes"] and r["placebo"]["gate"]["p_perm"] == pytest.approx(0.01)
    v = la.verdict("E014", r["primary"], r["placebo"], r["available"], 0.001)
    assert v["verdict"].startswith("Supported")
    # no timing information: flow is a market-level constant -> the gate must fail even with a big pooled contrast
    e2 = e.copy()
    mk = e2["market_id"].astype(int).to_numpy()
    e2["ss"] = np.where(mk % 2, 1.0, -1.0)
    e2["p_aug"] = c["intercept"] + c["signed_share"] * e2["ss"]
    y2 = np.where(A, 0.02, 0.0) * e2["ss"].to_numpy() + rng.normal(0, 0.01, n)
    e2["bid_j2"], e2["ask_j2"] = 0.5 + y2 - 0.005, 0.5 + y2 + 0.005
    r2 = la.e014_tests(e2, {}, spec, placebo_draws=99)
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
    res = la.analyze(out, start_utc=REG, end_utc=END, spec=spec, roles=(lt.ROLE_UNREG,), placebo_draws=2, perm_draws=10, force=True)
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
