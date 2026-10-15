# ruff: noqa: E501
"""SB2-J4/J3 bounce decomposition: construction, statistics, verdict map, counting."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2, provenance
from astrolabe.research_lab import bounce_decomp as bd

T0 = datetime(2026, 10, 12, 0, 0, tzinfo=UTC)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def make_rows(start: datetime, mids: dict[str, float], *, spread=0.02, ltp=None, vol=1000.0,
              chg=0.0, liq=5000.0, shift=0.0) -> pd.DataFrame:
    rows = []
    for k, (mid_id, m) in enumerate(mids.items()):
        m = m + shift
        rows.append({
            "market_id": mid_id, "event_id": f"e{k % 3}", "received_utc": iso(start + timedelta(seconds=30)),
            "best_bid": m - spread / 2, "best_ask": m + spread / 2, "spread": spread,
            "last_trade_price": m if ltp is None else ltp, "chg_1h": chg, "chg_1d": 0.0, "chg_1w": 0.0,
            "liquidity": liq, "volume24hr": vol, "end_date": "", "closed": "False", "active": "True",
            "binary": 1,
        })
    df = pd.DataFrame(rows)
    df["end_date"] = np.nan
    return df


def write_capture(root, cid: str, start: datetime, df: pd.DataFrame) -> None:
    d = root / cid
    d.mkdir(parents=True)
    df.to_csv(d / "rows.csv.gz", index=False)
    (d / "manifest.json").write_text(json.dumps(
        {"capture_id": cid, "state": "complete", "started_utc": iso(start)}))


def write_sweep(root, sweep_id: str, snapshot_id: str, receipt: datetime, mids: dict[str, float]) -> None:
    d = root / sweep_id
    d.mkdir(parents=True)
    pd.DataFrame([{"market_id": k, "batch_receipt_utc": iso(receipt), "best_bid": v - 0.01,
                   "best_ask": v + 0.01, "state": "two_sided"} for k, v in mids.items()]
                 ).to_csv(d / "rows.csv.gz", index=False)
    (d / "manifest.json").write_text(json.dumps(
        {"sweep_id": sweep_id, "snapshot_id": snapshot_id, "state": "complete",
         "started_utc": iso(receipt), "series_index": 0}))


MIDS = {"m1": 0.30, "m2": 0.50, "m3": 0.70}


# --- construction -------------------------------------------------------------------------------


def test_triples_skip_gaps_outside_window(tmp_path):
    hours = [0, 2, 4, 9, 11, 13]
    for n, h in enumerate(hours):
        t = T0 + timedelta(hours=h)
        write_capture(tmp_path / "snap", f"c{n}", t, make_rows(t, MIDS, shift=0.001 * n))
    df, counts = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none")
    built = [c for c in counts if "skipped" not in c]
    skipped = [c for c in counts if "skipped" in c]
    assert [c["capture_i"] for c in built] == ["c1", "c4"]
    assert [c["capture_i"] for c in skipped] == ["c2", "c3"]
    assert len(df) == 6 and set(df["period"]) == {0, 3}
    assert not df["day"].isna().any()


def test_b_pos_clipping_and_nan(tmp_path):
    hs = [0, 2, 4]
    for n, h in enumerate(hs):
        t = T0 + timedelta(hours=h)
        rows = make_rows(t, MIDS)
        if n == 1:
            rows["last_trade_price"] = [0.90, np.nan, 0.70 + 0.003]  # far above ask, none, inside
        write_capture(tmp_path / "snap", f"c{n}", t, rows)
    df, _ = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none")
    by = df.set_index("market_id")
    assert by.loc["m1", "b_pos"] == pytest.approx(1.0)  # clipped
    assert np.isnan(by.loc["m2", "b_pos"]) and by.loc["m2", "b_pos0"] == 0 and by.loc["m2", "b_pos_missing"] == 1
    assert by.loc["m3", "b_pos"] == pytest.approx(0.3, abs=1e-3)
    # zero spread => NaN b_pos
    sh, si, sj = (make_rows(T0 + timedelta(hours=h), MIDS) for h in (0, 2, 4))
    si["spread"] = 0.0
    si["best_bid"] = si["best_ask"] - 0.0001
    out, _ = bd.build_triple(sh, si, sj, iso(T0 + timedelta(hours=2)), iso(T0 + timedelta(hours=4)), 0, None)
    assert out["b_pos"].isna().all()


def test_origin_only_guard():
    with pytest.raises(ValueError):
        bd.assert_origin_only(["spread", "dmid"])
    assert not set(bd.J4_FEATURES) & set(bd.J4_TARGETS)
    sh, si = (make_rows(T0 + timedelta(hours=h), MIDS, shift=0.002 * h) for h in (0, 2))
    sj = make_rows(T0 + timedelta(hours=4), MIDS, shift=0.01)
    args = (sh, si)
    a, _ = bd.build_triple(*args, sj, iso(T0 + timedelta(hours=2)), iso(T0 + timedelta(hours=4)), 0, None)
    sj2 = sj.copy()  # change every non-quote column of j
    sj2["chg_1h"], sj2["last_trade_price"], sj2["volume24hr"], sj2["liquidity"] = 0.4, 0.9, 1e9, 1e9
    b, _ = bd.build_triple(*args, sj2, iso(T0 + timedelta(hours=2)), iso(T0 + timedelta(hours=4)), 0, None)
    pd.testing.assert_frame_equal(a, b)
    sj3 = sj.copy()  # change j quotes: only target columns move
    sj3["best_bid"] = sj3["best_bid"] + 0.02
    sj3["best_ask"] = sj3["best_ask"] + 0.02
    c, _ = bd.build_triple(*args, sj3, iso(T0 + timedelta(hours=2)), iso(T0 + timedelta(hours=4)), 0, None)
    changed = [col for col in a.columns if not a[col].equals(c[col])]
    assert set(changed) <= set(bd.J4_TARGETS)
    assert "dmid" in changed


def test_sweep_join_and_lag(tmp_path):
    for n, h in enumerate([0, 2, 4]):
        t = T0 + timedelta(hours=h)
        write_capture(tmp_path / "snap", f"c{n}", t, make_rows(t, MIDS))
    write_sweep(tmp_path / "sw", "s1", "c1", T0 + timedelta(hours=2, minutes=30), MIDS)
    df, counts = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "sw")
    assert df["B_i"].notna().all()
    assert (df["sweep_lag_min"] > 20).all() and counts[0]["sweep_lag_gt_20min"] == 3


# --- statistics worlds --------------------------------------------------------------------------


def snap_world(kind: str, n_mkt=300, n_per=8, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    sd_m, sd_e = 0.01, 0.01
    for k in range(n_mkt):
        for p in range(n_per):
            m_h, m_i, m_j = np.cumsum(rng.normal(0, sd_m, 3))
            e = rng.normal(0, sd_e, 3) if kind == "noise" else np.zeros(3)
            mh, mi, mj = 0.5 + m_h + e[0], 0.5 + m_i + e[1], 0.5 + m_j + e[2]
            B = 0.5 + m_i if kind == "noise" else mi
            d_bid, d_ask = rng.normal(0, 0.01, 2)
            if kind == "refill":
                d_bid, d_ask = (rng.normal(0, 0.01), 0.0) if rng.random() < 0.5 else (rng.normal(0, 0.01),) * 2
                mi_ = 0.5
                mh_ = mi_ - (d_bid + d_ask) / 2
                dm = -0.8 * (d_bid + d_ask) / 2 * (1.0 if d_bid * d_ask == 0 else 0.0) + rng.normal(0, 0.003)
                mh, mi, mj = mh_, mi_, mi_ + dm
                B = mi
            den = abs(d_ask) + abs(d_bid)
            w = abs(d_ask - d_bid) / den if den > 0 else 0.0
            d_bm = (d_bid + d_ask) / 2 if kind == "refill" else mi - mh
            rows.append(dict(
                market_id=f"m{k}", cluster=f"e{k // 3}", period=p, day=f"2026-10-{12 + p // 2}",
                spread=0.02, chg_1h=rng.normal(0, 0.01), chg_1h_missing=0.0,
                b_pos=rng.uniform(-1, 1), d_bm=d_bm, d_bid=d_bid, d_ask=d_ask, w=w,
                mid_i=mi, mid_j=mj, bid_j=mj - 0.01, ask_j=mj + 0.01, B_i=B, sweep_lag_min=5.0,
                volume_up=True, liquidity_i=rng.uniform(1e3, 1e5), ltp_i=mi, ltp_h=mh))
    df = pd.DataFrame(rows)
    df["b_pos0"], df["b_pos_missing"] = df["b_pos"], 0.0
    df["d_bm_x_w"] = df["d_bm"] * df["w"]
    df["dmid"] = df["mid_j"] - df["mid_i"]
    df["y_p1x"] = df["mid_j"] - df["B_i"]
    df["y_far_bid"], df["y_far_ask"] = df["bid_j"] - (df["mid_i"] - 0.01), df["ask_j"] - (df["mid_i"] + 0.01)
    return df


def test_random_walk_all_near_zero():
    r = bd.snapshot_tests(snap_world("walk"), n_boot=100, seed=1)
    for name in ("P1", "P1x", "P3", "P4"):
        t = r["tests"][name]
        assert abs(t["beta"]) < 4 * t["se"] + 0.05
        assert not t["reject"] or name == "P2"
    assert r["tests"]["P2"]["testable"]


def test_gamma_noise_world_p1_negative_p1x_zero():
    r = bd.snapshot_tests(snap_world("noise"), n_boot=100, seed=1)
    p1, p1x = r["tests"]["P1"], r["tests"]["P1x"]
    assert p1["beta"] < -0.2 and p1["reject"]
    assert abs(p1x["beta"]) < 0.05
    assert r["verdicts"]["gamma_mid_reversal"] in ("present", "inconclusive (day-unstable)")
    assert r["verdicts"]["reversion_nature"] != "genuine reversion"


def test_refill_world_p3_negative():
    r = bd.snapshot_tests(snap_world("refill"), n_boot=100, seed=1)
    assert r["tests"]["P3"]["beta"] < -0.3 and r["tests"]["P3"]["reject"]


def test_volume_rule_and_sweep_lag_exclusion():
    df = snap_world("walk", n_mkt=60, n_per=4)
    df.loc[df.index % 2 == 0, "volume_up"] = False
    df.loc[df.index % 5 == 0, "sweep_lag_min"] = 45.0
    r = bd.snapshot_tests(df, n_boot=50, seed=1)
    assert r["tests"]["P2"]["rows_used"] == int(df["volume_up"].sum())
    assert r["tests"]["P1x"]["rows_used"] == int((df["sweep_lag_min"] <= 20).sum())
    assert r["tests"]["P2"]["share_dropped_volume_rule"]["all"] == pytest.approx(0.5, abs=0.01)


def test_holm_ordering():
    adj = bd.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == {"a": pytest.approx(0.03), "b": pytest.approx(0.06), "c": pytest.approx(0.06)}
    assert bd.holm({"x": 0.5})["x"] == 0.5


def test_lodo_sign_rule_and_verdict_downgrade():
    rng = np.random.default_rng(3)
    n = 3000
    day = np.repeat(["d1", "d2", "d3"], n // 3)
    x = rng.normal(size=n)
    y = np.where(day == "d1", -3 * x, 0.05 * x) + rng.normal(0, 0.1, n)
    full = np.polyfit(x, y, 1)[0]
    lo = bd.lodo(y, x, np.empty((n, 0)), day, full)
    assert full < 0 and lo["betas"]["d1"] > 0 and not lo["sign_stable"]
    t = lambda **k: {"testable": True, "reject": True, "beta": -0.4, "ci95": [-0.5, -0.3],  # noqa: E731
                     "ci90": [-0.48, -0.32], "lodo": {"sign_stable": True}, **k}
    res = {"tests": {"P1": t(), "P1x": t(beta=-0.3, ci95=[-0.4, -0.2], ci90=[-0.38, -0.22]),
                     "P2": t(reject=False, beta=0.0, ci95=[-1, 1], ci90=[-0.01, 0.01],
                             half_spread_cents_median=1.0,
                             lodo={"sign_stable": False, "betas": {"d1": -0.02, "d2": 0.03}}),
                     "P3": t(), "P4": t(reject=False, beta=-0.01, ci95=[-0.02, 0.0],
                                        lodo={"sign_stable": False, "betas": {"d1": -0.03, "d2": 0.01}})}}
    v = bd.verdicts(res)
    assert v["gamma_mid_reversal"] == "present" and v["reversion_nature"] == "genuine reversion"
    assert v["last_trade"].startswith("pure bounce") and v["e004_reversal"] == "explained"
    assert v["quote_refill"] == "supporting: refill"
    res["tests"]["P1x"]["lodo"] = {"sign_stable": False}
    v2 = bd.verdicts(res)
    assert v2["reversion_nature"] == "inconclusive (day-unstable)"
    assert v2["gamma_mid_reversal"] == "present"
    # equivalence/bound verdicts: sign flips inside the band are fine (above); a day outside is not
    res["tests"]["P2"]["lodo"] = {"sign_stable": False, "betas": {"d1": -0.02, "d2": 0.2}}
    res["tests"]["P4"]["lodo"] = {"sign_stable": True, "betas": {"d1": -0.08, "d2": -0.01}}
    v3 = bd.verdicts(res)
    assert v3["last_trade"] == "inconclusive (day-unstable)"
    assert v3["e004_reversal"] == "inconclusive (day-unstable)"


def test_placebo_permutation_breaks_time_link_within_market():
    df = snap_world("noise", n_mkt=40, n_per=6)
    pdf = bd.permute_snapshot_targets(df, 5)
    for c in bd.J4_FEATURES:
        if c in df:
            assert df[c].equals(pdf[c])
    assert (pdf.groupby("market_id")["mid_j"].apply(lambda s: sorted(s)).to_dict()
            == df.groupby("market_id")["mid_j"].apply(lambda s: sorted(s)).to_dict())
    assert not np.allclose(pdf["mid_j"], df["mid_j"])
    assert np.allclose(pdf["dmid"], pdf["mid_j"] - pdf["mid_i"])


# --- J3 -----------------------------------------------------------------------------------------


def book_world(kind: str, n_mkt=500, n_per=12, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = n_mkt * n_per
    bm = 0.5 + np.cumsum(rng.normal(0, 0.005, n)) * 0 + rng.normal(0, 0.05, n)
    d_prev = rng.normal(0, 0.01, n)
    e_t = rng.normal(0, 0.01, n) if kind == "measurement" else np.zeros(n)
    y_bm = rng.normal(0, 0.01, n)
    y_series = y_bm - e_t if kind == "measurement" else rng.normal(0, 0.01, n)
    w = rng.random(n)
    if kind == "reversion":
        y_bm = -0.4 * d_prev + rng.normal(0, 0.01, n)
    d = pd.DataFrame({
        "market_id": np.repeat([f"m{i}" for i in range(n_mkt)], n_per),
        "cluster": np.repeat([f"e{i // 2}" for i in range(n_mkt)], n_per),
        "day": np.tile(np.repeat([f"d{i}" for i in range(4)], 3), n_mkt),
        "period": np.tile(np.arange(n_per, dtype=float), n_mkt),
        "split": np.where(np.tile(np.arange(n_per), n_mkt) < 6, "disc", "judge"),
        "bm": bm, "e_t": e_t, "d_bm_prev": d_prev, "w": w, "d_bm_x_w": d_prev * w,
        "log_depth": rng.normal(6, 1, n), "x6": rng.normal(0, 1, n), "flow_pressure": rng.normal(0, 1, n),
        "y_series": y_series, "y_bm": y_bm, "d_series_prev": d_prev + e_t * 0 + rng.normal(0, 0.01, n),
    })
    d["y_series"] = d["y_series"] - 0.2 * d["d_series_prev"]
    for c in bd.C0_COLS:
        d[c] = rng.normal(0, 0.1, n)
    return d


def test_pure_measurement_world_b2_negative_b1_zero():
    r = bd.book_tests(book_world("measurement"), {}, n_boot=100, seed=2)
    assert r["tests"]["B2"]["beta"] < -0.5 and r["tests"]["B2"]["reject"]
    assert abs(r["tests"]["B1"]["beta"]) < 0.1 and not r["tests"]["B1"]["reject"]
    assert r["rho_s"]["beta"] == pytest.approx(-0.2, abs=0.1)
    assert r["verdicts"]["overall"] == "measurement/bounce"


def test_book_mean_reversion_and_unavailable():
    r = bd.book_tests(book_world("reversion"), {}, n_boot=100, seed=2)
    assert r["tests"]["B1"]["beta"] < -0.3 and r["verdicts"]["overall"] == "book-mid mean reversion"
    small = bd.book_tests(book_world("measurement", n_mkt=20, n_per=12), {}, n_boot=50, seed=2)
    assert small["verdicts"]["overall"] == "unavailable"


def test_book_random_walk_near_zero_and_placebo():
    d = book_world("walk")
    r = bd.book_tests(d, {}, n_boot=100, seed=2)
    for k in ("B1", "B2", "B3", "B4"):
        assert not r["tests"][k]["reject"] or abs(r["tests"][k]["beta"]) < 0.1
    pl = bd.permute_book_targets(d, 4)
    assert not np.allclose(pl["y_bm"], d["y_bm"])
    assert sorted(pl["y_bm"]) == pytest.approx(sorted(d["y_bm"]))


# --- counting -----------------------------------------------------------------------------------


def test_log_trials_counts_once(tmp_path):
    path = tmp_path / "trials.jsonl"
    res = {"tests": {n: {"beta": 0.0, "p": 0.5, "reject": False} for n in bd.J4_SPEC},
           "prior_tests": {"total": 906}}
    lines = bd.log_trials("J4", res, "x/results.json", "abc", "bounce-t", {"git_head": "h"},
                          placebo={"tests": res["tests"]}, path=path)
    assert len(lines) == 5 + 5 + 1
    assert sum(1 for rec in lines if rec["kind"] == "bounce_decomp" and rec["evidence_role"] == "placebo") == 5
    cnt = battery2.cumulative_count(path)
    assert cnt["total"] == 5 and cnt["by_kind"]["bounce_decomp"] == 0
    res6 = {"tests": {n: {"beta": 0.0, "p": 0.5} for n in bd.J3_IDS}}
    bd.log_trials("J3", res6, "x/r.json", "abc", "bounce-b", {}, path=path)
    assert battery2.cumulative_count(path)["total"] == 11
    assert provenance.validate_evidence_role({"kind": "ml_explain", "evidence_role": "exploratory_dev"}) is None


def test_build_book_triples_joins_and_counts(tmp_path):
    t = [1.7e9 + 6 * 3600 * k for k in range(3)]  # prev, t, next
    feats = pd.DataFrame({
        "market_id": ["a"], "event_c": ["e:1"], "day_c": ["d"], "t_i": [t[1]], "split": ["judge"],
        "mid_i": [0.52], "d_6": [0.01], "ok_6": [True], "f_imb_6h": [0.1], "f_n_6h": [3.0],
        "bk_sw_best_bid": [0.49], "bk_sw_best_ask": [0.51], "bk_sw_depth_bid_5c": [100.0],
        "bk_sw_depth_ask_5c": [100.0], "bp_sw_best_bid": [0.47], "bp_sw_best_ask": [0.50],
        **{c: [0.0] for c in bd.C0_COLS}})
    feats.to_parquet(tmp_path / "f.parquet")
    pd.DataFrame({"market_id": ["a", "a"], "t_i": [t[0], t[1]], "mid_i": [0.50, 0.52]}
                 ).to_csv(tmp_path / "p.csv.gz", index=False)
    pd.DataFrame({"market_id": ["a"], "origin_ts": [t[2]], "state": ["two_sided"],
                  "sw_best_bid": [0.50], "sw_best_ask": [0.52]}).to_csv(tmp_path / "b.csv.gz", index=False)
    d, c = bd.build_book_triples(tmp_path / "f.parquet", tmp_path / "b.csv.gz", tmp_path / "p.csv.gz")
    assert len(d) == 1 and c["rows_complete"] == 1
    r = d.iloc[0]
    assert r["bm"] == pytest.approx(0.50) and r["e_t"] == pytest.approx(0.02)
    assert r["d_bm_prev"] == pytest.approx(0.50 - 0.485) and r["y_bm"] == pytest.approx(0.01)
    assert r["d_series_prev"] == pytest.approx(0.02)
    # target book missing: row is counted unavailable, not silently kept
    pd.DataFrame({"market_id": ["z"], "origin_ts": [t[2]], "state": ["two_sided"],
                  "sw_best_bid": [0.5], "sw_best_ask": [0.52]}).to_csv(tmp_path / "b2.csv.gz", index=False)
    d2, c2 = bd.build_book_triples(tmp_path / "f.parquet", tmp_path / "b2.csv.gz", tmp_path / "p.csv.gz")
    assert len(d2) == 0 and c2["rows_target_book_unavailable"] == 1
