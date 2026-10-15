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
    for c in ("dmid", "y_p1x", "y_far_bid", "mid_j"):
        assert (pdf.groupby("market_id")[c].apply(lambda s: sorted(s)).to_dict()
                == df.groupby("market_id")[c].apply(lambda s: sorted(s)).to_dict())
        assert not np.allclose(pdf[c], df[c])
    # one shared index: target columns stay row-aligned with each other
    assert np.allclose(pdf["y_far_bid"] - pdf["mid_j"], (df["y_far_bid"] - df["mid_j"]).to_numpy()[
        _perm_index(df, pdf)])


def _perm_index(df, pdf):
    # recover the shared index from mid_j (unique continuous values within market)
    key = {(m, round(v, 12)): k for k, (m, v) in enumerate(zip(df["market_id"], df["mid_j"], strict=True))}
    return np.array([key[(m, round(v, 12))] for m, v in zip(pdf["market_id"], pdf["mid_j"], strict=True)])


def test_placebo_null_on_random_walk_world():
    df = snap_world("walk")
    r = bd.snapshot_tests(bd.permute_snapshot_targets(df, 7), n_boot=100, seed=1)
    for name in ("P1", "P1x"):
        t = r["tests"][name]
        assert abs(t["beta"]) < 0.1 and not t["reject"], (name, t["beta"])


def test_p1x_excludes_negative_lag_and_counts_it():
    df = snap_world("walk", n_mkt=60, n_per=4)
    df.loc[df.index % 7 == 0, "sweep_lag_min"] = -3.0
    df.loc[df.index % 11 == 0, "sweep_lag_min"] = 30.0
    r = bd.snapshot_tests(df, n_boot=50, seed=1)["tests"]["P1x"]
    ok = (df["sweep_lag_min"] >= 0) & (df["sweep_lag_min"] <= 20)
    assert r["rows_used"] == int(ok.sum())
    assert r["sweep_rows_lag_negative"] == int((df["sweep_lag_min"] < 0).sum()) > 0


def test_bound_verdicts_use_conservative_interval():
    base = {"testable": True, "reject": False, "beta": -0.02, "ci95": [-0.04, 0.0],
            "ci90": [-0.04, 0.0], "lodo": {"sign_stable": True, "betas": {"d1": -0.02, "d2": -0.01}}}
    t = lambda **k: {**base, **k}  # noqa: E731
    mk = lambda p4: {"tests": {"P1": t(reject=True, beta=-0.4, ci95=[-0.5, -0.3], ci90=[-0.48, -0.32]),  # noqa: E731
                               "P1x": t(reject=True, beta=-0.3, ci95=[-0.4, -0.2], ci90=[-0.38, -0.22]),
                               "P2": t(half_spread_cents_median=1.0), "P3": t(), "P4": p4}}
    # no SE recorded: bootstrap bound -0.04 > -0.05 -> explained
    assert bd.verdicts(mk(t()))["e004_reversal"] == "explained"
    # larger two-way SE: beta - 1.96 se = -0.118 < -0.05 -> bound not met
    v = bd.verdicts(mk(t(se=0.05)))
    assert v["e004_reversal"] == "inconclusive"
    assert v["bound_intervals"]["e004_reversal.explained"]["binding"] == "normal_max_se"
    # B1 bound clause
    b = lambda **k: {"testable": True, "reject": False, "beta": 0.0, "ci95": [-0.05, 0.05], **k}  # noqa: E731
    res = {"tests": {"B1": b(se=0.01), "B2": b(reject=True, beta=-0.5), "B4": b()}, "rho_s": {"testable": True, "beta": -0.2}}
    res["tests"]["B1"] = b(ci95=[-0.04, 0.05], se=0.01)  # -0.04 > -0.1 with small se
    assert bd.book_verdicts(res)["overall"] == "measurement/bounce"
    res["tests"]["B1"] = b(ci95=[-0.04, 0.05], se=0.04)  # -0.078 ... still > -0.1
    assert bd.book_verdicts(res)["overall"] == "measurement/bounce"
    res["tests"]["B1"] = b(ci95=[-0.04, 0.05], se=0.08)  # -0.157 < -0.1 -> not met
    v = bd.book_verdicts(res)
    assert v["overall"] != "measurement/bounce"
    assert v["bound_intervals"]["B1.measurement_bounce"]["binding"] == "normal_max_se"


SPEC = {"min_rows": 100, "min_events": 10}


def test_book_tests_second_clustering_is_utc_day(monkeypatch):
    seen = []
    orig = bd.fit_test

    def spy(y, x, Z, ev, per, n_boot, seed):
        seen.append(set(np.asarray(per).astype(str)))
        return orig(y, x, Z, ev, per, n_boot, seed)

    monkeypatch.setattr(bd, "fit_test", spy)
    d = book_world("reversion", n_mkt=300)
    bd.book_tests(d, SPEC, n_boot=20, seed=2)
    days = set(d["day"])
    assert seen and all(s <= days for s in seen)


def test_c0_in_b4_d1_d2_controls():
    d = book_world("reversion", n_mkt=300)
    d2 = d.copy()
    d2["c_chg_1d"] = d2["c_chg_1d"] + 5.0 * d2["y_bm"]  # leak into a C0 control only
    a = bd.book_tests(d, SPEC, n_boot=20, seed=2)["tests"]
    b = bd.book_tests(d2, SPEC, n_boot=20, seed=2)["tests"]
    for k in ("B4", "D1", "D2"):
        assert a[k]["beta"] != pytest.approx(b[k]["beta"])


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
        "mid_i": [0.52], "d_6": [0.01], "ok_6": [True], "f_imb_6h": [0.1], "f_n_6h": [3.0], "f_N_6h": [500.0],
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
    # D2 term: signed 6h notional (f_imb_6h * f_N_6h = 50 USDC) / (depth shares x book mid + 100)
    assert r["flow_pressure"] == pytest.approx(50.0 / (200.0 * 0.50 + 100.0))
    assert "shares" in c["units"]["depth5c"]
    # target book missing: row is counted unavailable, not silently kept
    pd.DataFrame({"market_id": ["z"], "origin_ts": [t[2]], "state": ["two_sided"],
                  "sw_best_bid": [0.5], "sw_best_ask": [0.52]}).to_csv(tmp_path / "b2.csv.gz", index=False)
    d2, c2 = bd.build_book_triples(tmp_path / "f.parquet", tmp_path / "b2.csv.gz", tmp_path / "p.csv.gz")
    assert len(d2) == 0 and c2["rows_target_book_unavailable"] == 1


# --- fail-loud on archived (missing) files and root routing -------------------------------------


def test_missing_capture_rows_raises_archived(tmp_path):
    from astrolabe.research_lab import forecast
    for n, h in enumerate([0, 2, 4]):
        t = T0 + timedelta(hours=h)
        write_capture(tmp_path / "snap", f"c{n}", t, make_rows(t, MIDS))
    (tmp_path / "snap" / "c1" / "rows.csv.gz").unlink()
    with pytest.raises(forecast.ArchivedDataError, match="restore_from_archive"):
        bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "sw")


def test_sweep_manifest_without_rows_raises_archived(tmp_path):
    from astrolabe.research_lab import forecast
    for n, h in enumerate([0, 2, 4]):
        t = T0 + timedelta(hours=h)
        write_capture(tmp_path / "snap", f"c{n}", t, make_rows(t, MIDS))
    write_sweep(tmp_path / "sw", "s1", "c1", T0 + timedelta(hours=2, minutes=5), MIDS)
    (tmp_path / "sw" / "s1" / "rows.csv.gz").unlink()
    with pytest.raises(forecast.ArchivedDataError):
        bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "sw")


def test_no_sweep_for_snapshot_is_still_counted_not_error(tmp_path):
    for n, h in enumerate([0, 2, 4]):
        t = T0 + timedelta(hours=h)
        write_capture(tmp_path / "snap", f"c{n}", t, make_rows(t, MIDS))
    (tmp_path / "sw").mkdir()
    df, counts = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "sw")
    assert len(df) and counts[0]["sweep_found"] is False


# =============================================================================================
# J4-R / J3: expanding-past estimator, increment-shuffle placebo, fresh-capture and h-tight filters
# =============================================================================================


def level_world(kind: str, n_mkt=200, T=8, seed=0, sd=0.01) -> pd.DataFrame:
    """Triples built from per-market level series (row t = captures t, t+1, t+2, so consecutive rows
    overlap exactly as in the real build). 'walk': iid increments; 'reversal': the observed Gamma mid is
    the latent walk plus iid noise (negative increment autocorrelation) and the sweep B_i is observed
    without the noise (a genuine reversal relative to the independent measurement)."""
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(n_mkt):
        latent = 0.5 + np.cumsum(rng.normal(0, sd, T + 2))
        obs = latent + (rng.normal(0, sd, T + 2) if kind == "reversal" else 0.0)
        for t in range(T):
            mh, mi, mj = obs[t], obs[t + 1], obs[t + 2]
            d_bid, d_ask = rng.normal(0, 0.01, 2)
            den = abs(d_ask) + abs(d_bid)
            w = abs(d_ask - d_bid) / den
            B = latent[t + 1] if kind == "reversal" else mi
            rows.append(dict(
                market_id=f"m{k}", cluster=f"e{k // 2}", period=t, day=f"2026-10-{16 + t // 3}",
                spread=0.02, chg_1h=rng.normal(0, 0.01), chg_1h_missing=0.0, b_pos=rng.uniform(-1, 1),
                d_bm=mi - mh, d_bid=d_bid, d_ask=d_ask, w=w, mid_h=mh, mid_i=mi, mid_j=mj,
                bid_h=mh - 0.01, ask_h=mh + 0.01, bid_j=mj - 0.01, ask_j=mj + 0.01, B_i=B,
                sweep_lag_min=5.0, volume_up=True, liquidity_i=1e4, ltp_i=mi, ltp_h=mh))
    df = pd.DataFrame(rows)
    df["b_pos0"], df["b_pos_missing"] = df["b_pos"], 0.0
    df["d_bm_x_w"] = df["d_bm"] * df["w"]
    df["dmid"] = df["mid_j"] - df["mid_i"]
    df["y_p1x"] = df["mid_j"] - df["B_i"]
    df["y_far_bid"], df["y_far_ask"] = df["bid_j"] - (df["mid_i"] - 0.01), df["ask_j"] - (df["mid_i"] + 0.01)
    return df


def _p1_beta(df, estimator):
    return bd.snapshot_tests(df, n_boot=2, seed=1, estimator=estimator, descriptive=False)["tests"]["P1"]["beta"]


def _fe_beta(df):
    """Plain market fixed-effects slope of dmid on d_bm (whole-sample demeaning)."""
    x = df["d_bm"] - df.groupby("market_id")["d_bm"].transform("mean")
    y = df["dmid"] - df.groupby("market_id")["dmid"].transform("mean")
    return float((x * y).sum() / (x * x).sum())


def test_expanding_resid_causal_and_first_row_nan():
    df = pd.DataFrame({"market_id": ["a"] * 4 + ["b"] * 2, "period": [3, 0, 1, 2, 5, 4],
                       "x": [10.0, 1.0, 3.0, np.nan, 7.0, 5.0]})
    out = bd.expanding_demean(df, ["x"])
    got = out.set_index(["market_id", "period"])["x"]
    assert np.isnan(got[("a", 0)]) and np.isnan(got[("b", 4)])  # first row of each market
    assert got[("a", 1)] == pytest.approx(3.0 - 1.0)  # mean of strictly earlier rows only
    assert np.isnan(got[("a", 2)])  # own value NaN
    assert got[("a", 3)] == pytest.approx(10.0 - 2.0)  # NaN earlier row ignored
    assert got[("b", 5)] == pytest.approx(7.0 - 5.0)
    assert df["x"].equals(pd.Series([10.0, 1.0, 3.0, np.nan, 7.0, 5.0], name="x"))  # input untouched
    # changing a later row never changes an earlier row's value (causality)
    df2 = df.copy()
    df2.loc[0, "x"] = 99.0
    got2 = bd.expanding_demean(df2, ["x"]).set_index(["market_id", "period"])["x"]
    assert got2[("a", 1)] == got[("a", 1)] and got2[("a", 2)] is not None


def test_expanding_estimator_zero_bias_short_panels_fe_biased():
    means_exp, means_fe = {}, {}
    for T in (3, 4, 6, 10):
        be, bf = [], []
        for s in range(25):
            df = level_world("walk", n_mkt=150, T=T, seed=1000 * T + s)
            be.append(_p1_beta(df, "expanding"))
            bf.append(_fe_beta(df))
        means_exp[T], means_fe[T] = float(np.mean(be)), float(np.mean(bf))
    for T, m in means_exp.items():
        assert abs(m) < 0.02, (T, m)
    assert means_fe[3] < -0.2 and means_fe[6] < -0.1 and means_fe[10] < -0.05, means_fe


def test_increment_shuffle_placebo_is_consistent_and_keeps_observed_columns():
    df = level_world("walk", n_mkt=30, T=8, seed=3)
    pl = bd.shuffle_increments_placebo(df, 5)
    for c in ("spread", "b_pos", "w", "chg_1h", "liquidity_i", "volume_up", "period", "market_id", "d_bid"):
        assert df[c].equals(pl[c]), c
    assert not np.allclose(pl["dmid"], df["dmid"])
    for _, g in pl.sort_values(["market_id", "period"]).groupby("market_id"):
        # overlapping rows share a capture level: row t's (i, j) is row t+1's (h, i)
        assert np.allclose(g["mid_i"].to_numpy()[1:], g["mid_j"].to_numpy()[:-1], atol=1e-6)
        assert np.allclose(g["mid_h"].to_numpy()[1:], g["mid_i"].to_numpy()[:-1], atol=1e-6)
    assert np.allclose(pl["d_bm"], pl["mid_i"] - pl["mid_h"], atol=1e-6)
    assert np.allclose(pl["dmid"], pl["mid_j"] - pl["mid_i"], atol=1e-6)
    assert np.allclose(pl["d_bm_x_w"], pl["d_bm"] * pl["w"], atol=1e-6)
    assert np.allclose(pl["y_p1x"], pl["mid_j"] - pl["B_i"], atol=1e-6)
    # start level kept and increment multiset preserved per market
    for m, g in df.sort_values("period").groupby("market_id"):
        gp = pl[pl["market_id"] == m].sort_values("period")
        assert gp["mid_h"].iloc[0] == pytest.approx(g["mid_h"].iloc[0], abs=1e-6)
        inc = np.r_[g["d_bm"].to_numpy(), g["dmid"].iloc[-1]]
        incp = np.r_[gp["d_bm"].to_numpy(), gp["dmid"].iloc[-1]]
        assert np.allclose(sorted(inc), sorted(incp), atol=1e-6)


def test_increment_shuffle_runs_break_at_gaps():
    df = level_world("walk", n_mkt=6, T=9, seed=4)
    # no rows at periods 4 and 5: the increment 5 -> 6 is observed by no row, so the runs break there
    gap = df[~df["period"].isin([4, 5])].reset_index(drop=True)
    pl = bd.shuffle_increments_placebo(gap, 2)
    for m, g in gap.sort_values("period").groupby("market_id"):
        a, b = g[g["period"] < 4], g[g["period"] > 5]
        pa, pb = (pl[(pl["market_id"] == m) & cond].sort_values("period") for cond in
                  (pl["period"] < 4, pl["period"] > 5))
        # increments never move across the missing period: each side keeps its own multiset
        assert np.allclose(sorted(np.r_[a["d_bm"], a["dmid"].iloc[-1]]),
                           sorted(np.r_[pa["d_bm"], pa["dmid"].iloc[-1]]), atol=1e-6)
        assert np.allclose(sorted(np.r_[b["d_bm"], b["dmid"].iloc[-1]]),
                           sorted(np.r_[pb["d_bm"], pb["dmid"].iloc[-1]]), atol=1e-6)


def test_placebo_reproduces_fe_bias_and_is_null_under_expanding():
    fe, ex = [], []
    for s in range(12):
        df = level_world("walk", n_mkt=250, T=5, seed=70 + s)
        pl = bd.shuffle_increments_placebo(df, s)
        fe.append(_fe_beta(pl))
        ex.append(_p1_beta(pl, "expanding"))
    assert np.mean(fe) < -0.1, np.mean(fe)  # the FE estimator's mechanical bias shows up in the placebo
    assert abs(np.mean(ex)) < 0.03, np.mean(ex)


def test_genuine_reversal_expanding_negative_placebo_null():
    df = level_world("reversal", n_mkt=250, T=10, seed=11)
    r = bd.snapshot_tests(df, n_boot=50, seed=1, estimator="expanding")
    assert r["estimator"] == "expanding"
    assert r["tests"]["P1"]["beta"] < -0.15 and r["tests"]["P1"]["reject"]
    fam = bd.placebo_family(df, draws=20, seed=500, estimator="expanding", n_boot=5)
    assert fam["draws"] == 20 and fam["placebo_null"] is True
    assert all(len(t["betas"]) == 20 for t in fam["tests"].values())
    assert abs(fam["tests"]["P1"]["beta"]) < 0.06
    # the same placebo is NOT null for a naive pooled-with-FE-like bias check elsewhere; here it also
    # must not manufacture the genuine reversal
    assert fam["tests"]["P1"]["beta"] > r["tests"]["P1"]["beta"] + 0.1


def _toggle_captures(root, n_cap=40, n_mkt=100, sd=0.01, off=0.04, seed=0):
    rng = np.random.default_rng(seed)
    latent = 0.5 + np.cumsum(rng.normal(0, sd, (n_mkt, n_cap)), axis=1)
    sign = rng.choice([-1.0, 1.0], n_mkt)
    wide = rng.random((n_mkt, n_cap)) < 0.5
    for c in range(n_cap):
        t = T0 + timedelta(hours=2 * c)
        mids = {f"m{k}": float(latent[k, c] + (sign[k] * off if wide[k, c] else 0.0)) for k in range(n_mkt)}
        rows = make_rows(t, mids, vol=1000.0 + 10 * c)
        rows["event_id"] = [f"e{k}" for k in range(n_mkt)]
        rows["chg_1h"] = rng.normal(0, 0.01, n_mkt)
        sp = np.where(wide[:, c], 0.2, 0.02)
        rows["spread"] = sp
        rows["best_bid"] = rows["best_bid"].to_numpy(float) + 0.01 - sp / 2
        rows["best_ask"] = rows["best_ask"].to_numpy(float) - 0.01 + sp / 2
        write_capture(root, f"c{c:03d}", t, rows)


def test_regime_toggle_world_null_with_h_tight_and_biased_without(tmp_path):
    _toggle_captures(tmp_path / "snap")
    plain, cnt0 = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none")
    tight, cnt1 = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none", h_tight=True)
    assert len(tight) < len(plain)
    assert sum(c.get("h_tight_excluded", 0) for c in cnt1) == len(plain) - len(tight)
    assert cnt1[-1]["filters"]["rows_excluded_h_not_tight"] == len(plain) - len(tight)
    assert bd.snapshot_tests(plain, n_boot=20, seed=1, descriptive=False)["tests"]["P1"]["beta"] < -0.2
    r = bd.snapshot_tests(tight, n_boot=100, seed=1, estimator="expanding", descriptive=False)
    p1 = r["tests"]["P1"]
    assert abs(p1["beta"]) < 3.5 * p1["se"] and not p1["reject"], p1


def test_since_before_and_h_tight_filters(tmp_path):
    for n in range(6):
        t = T0 + timedelta(hours=2 * n)
        rows = make_rows(t, MIDS, shift=0.001 * n)
        if n == 2:  # capture c2 is the h of triple (c2, c3, c4): m2 wide there
            rows.loc[rows["market_id"] == "m2", ["spread", "best_bid", "best_ask"]] = [0.2, 0.4, 0.6]
        write_capture(tmp_path / "snap", f"c{n}", t, rows)
    full, _ = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none")
    assert len(full) == 11 and full["d_bm"].notna().all()  # m2 is wide at i=c2: not an origin
    df, counts = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none",
                                           since_utc=iso(T0 + timedelta(hours=4)))
    built = [c for c in counts if "capture_h" in c]
    assert [c["capture_h"] for c in built] == ["c2", "c3"]  # h, i, j all start >= since
    assert counts[-1]["filters"]["captures_excluded_by_time_window"] == 2 and len(df) == 6
    b, cb = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none",
                                      before_utc=iso(T0 + timedelta(hours=6)))  # c0, c1, c2 only
    assert len(b) == 3 and cb[-1]["filters"]["captures_read"] == 3
    ht, ch = bd.build_snapshot_triples(tmp_path / "snap", tmp_path / "none", since_utc=iso(T0 + timedelta(hours=4)),
                                       h_tight=True)
    assert len(ht) == 5 and set(ht["market_id"][ht["period"] == 0]) == {"m1", "m3"}
    assert [c.get("h_tight_excluded", 0) for c in ch if "capture_h" in c] == [1, 0]
    assert ch[-1]["filters"]["rows_excluded_h_not_tight"] == 1
    # tightness rule itself
    ok = bd.h_tight_mask(np.array([0.48, 0.0, 0.40, 0.97, 0.005, 0.5]), np.array([0.52, 0.5, 0.60, 1.0, 0.02, 0.5]),
                         np.array([0.04, np.nan, 0.2, 0.03, np.nan, np.nan]))
    assert ok.tolist() == [True, False, False, False, False, False]


def test_defaults_unchanged_by_estimator_arguments():
    df = snap_world("noise", n_mkt=80, n_per=6)
    a = bd.snapshot_tests(df, n_boot=30, seed=1)
    b = bd.snapshot_tests(df, n_boot=30, seed=1, estimator="pooled")
    assert a["tests"]["P1"]["beta"] == b["tests"]["P1"]["beta"] and a["estimator"] == "pooled"
    with pytest.raises(ValueError):
        bd.snapshot_tests(df, n_boot=2, seed=1, estimator="fe")
    assert bd.snapshot_regressors()[0] == "d_bm"


def test_snapshot_sensitivities_descriptive():
    df = level_world("walk", n_mkt=60, T=24, seed=2)
    s = bd.snapshot_sensitivities(df, n_boot=10, seed=1)
    assert set(s) >= {"markets_ge_20_rows", "j_tight_rows", "pooled_all_rows", "within_between"}
    wb = s["within_between"]["P1"]
    assert wb["within"] < wb["pooled"] + 0.2 and wb["n_markets"] == 60


# --- J3 ----------------------------------------------------------------------------------------


def book_level_world(kind: str, n_mkt=500, n_per=12, seed=0, sd=0.01) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(n_mkt):
        b = 0.5 + np.cumsum(rng.normal(0, sd, n_per + 2))
        e = rng.normal(0, sd, n_per + 2) if kind == "measurement" else np.zeros(n_per + 2)
        s = b + e
        for g in range(1, n_per + 1):
            w = rng.random()
            rows.append({
                "market_id": f"m{k}", "cluster": f"e{k // 2}", "day": f"d{g // 3}", "t_i": g * bd.H6,
                "period": g * bd.H6, "split": "disc" if g <= n_per // 2 else "judge",
                "bm": b[g], "bm_next": b[g + 1], "d_bm_prev": b[g] - b[g - 1], "y_bm": b[g + 1] - b[g],
                "series_mid": s[g], "d_series_prev": s[g] - s[g - 1], "y_series": s[g + 1] - s[g],
                "e_t": s[g] - b[g], "w": w, "d_bm_x_w": (b[g] - b[g - 1]) * w,
                "depth5c": 1000.0, "depth5c_usdc": 1000.0 * b[g], "log_depth": np.log1p(1000.0),
                "x6": rng.normal(), "n6": 3.0, "sn6": rng.normal() * 100,
                "ml_logit_mid": rng.normal(0, 0.1), "ml_abs_mid_dev": rng.normal(0, 0.1)})
    d = pd.DataFrame(rows)
    d["log_depth"] = d["log_depth"] + np.random.default_rng(seed + 1).normal(0, 0.3, len(d))
    d["flow_pressure"] = d["sn6"] / (d["depth5c_usdc"] + 100.0)
    for c in bd.C0_COLS:
        if c not in d:
            d[c] = np.random.default_rng(seed + 2).normal(0, 0.1, len(d))
    return d


def test_book_placebo_consistency():
    d = book_level_world("measurement", n_mkt=20, n_per=10, seed=1)
    pl = bd.shuffle_book_increments_placebo(d, 3)
    for _, g in pl.sort_values(["market_id", "t_i"]).groupby("market_id"):
        assert np.allclose(g["y_bm"].to_numpy()[:-1], g["d_bm_prev"].to_numpy()[1:], atol=1e-5)
        assert np.allclose(g["y_series"].to_numpy()[:-1], g["d_series_prev"].to_numpy()[1:], atol=1e-5)
        assert np.allclose(g["bm_next"].to_numpy()[:-1], g["bm"].to_numpy()[1:], atol=1e-5)
    assert np.allclose(pl["e_t"], pl["series_mid"] - pl["bm"], atol=1e-5)
    assert np.allclose(pl["d_bm_x_w"], pl["d_bm_prev"] * pl["w"], atol=1e-5)
    assert np.allclose(pl["ml_abs_mid_dev"], np.abs(pl["series_mid"] - 0.5), atol=1e-5)
    assert not np.allclose(pl["y_bm"], d["y_bm"]) and d["x6"].equals(pl["x6"])


def test_book_expanding_unbiased_fe_biased_and_defaults_unchanged():
    be, bf = [], []
    for s in range(10):
        d = book_level_world("walk", n_mkt=300, n_per=6, seed=s)
        d["split"] = "judge"
        r = bd.book_tests(d, {"min_rows": 100, "min_events": 10}, n_boot=2, seed=1, estimator="expanding")
        be.append(r["tests"]["B1"]["beta"])
        x = d["d_bm_prev"] - d.groupby("market_id")["d_bm_prev"].transform("mean")
        y = d["y_bm"] - d.groupby("market_id")["y_bm"].transform("mean")
        bf.append(float((x * y).sum() / (x * x).sum()))
    assert abs(np.mean(be)) < 0.03 and np.mean(bf) < -0.1, (np.mean(be), np.mean(bf))
    d = book_level_world("walk", n_mkt=300, n_per=6, seed=0)
    spec = {"min_rows": 100, "min_events": 10}
    r0 = bd.book_tests(d, spec, n_boot=5, seed=1)
    r1 = bd.book_tests(d, spec, n_boot=5, seed=1, estimator="pooled")
    assert r0["tests"]["B1"]["beta"] == r1["tests"]["B1"]["beta"]


def test_book_measurement_world_expanding_with_null_placebo():
    d = book_level_world("measurement", n_mkt=400, n_per=12, seed=5)
    r = bd.book_tests(d, {}, n_boot=30, seed=1, estimator="expanding")
    assert r["tests"]["B2"]["beta"] < -0.3 and r["tests"]["B2"]["reject"]
    fam = bd.book_placebo_family(d, draws=20, seed=300, estimator="expanding", n_boot=5, scheme="bootstrap")
    assert fam["draws"] == 20 and set(fam["tests"]) == set(bd.J3_IDS)
    assert fam["tests"]["B2"]["covers_zero"] and abs(fam["tests"]["B1"]["beta"]) < 0.1
    assert fam["tests"]["B2"]["beta"] > r["tests"]["B2"]["beta"] + 0.2


def test_permutation_placebo_is_a_bridge_for_level_regressors():
    """Finding: permuting a run's increments fixes its total, so a LEVEL regressor (J3's e_t = series - book,
    stationary measurement error) mean-reverts mechanically in the permutation placebo; an increment
    regressor (J4's d_bm) does not. The with-replacement scheme removes the artefact."""
    d = book_level_world("measurement", n_mkt=400, n_per=12, seed=5)
    keep = lambda f: (lambda df, seed, scheme="permute": (  # noqa: E731  keep mid-level controls as observed
        lambda o: o.assign(ml_logit_mid=df["ml_logit_mid"], ml_abs_mid_dev=df["ml_abs_mid_dev"]))(f(df, seed, scheme)))
    orig = bd.shuffle_book_increments_placebo
    try:
        bd.shuffle_book_increments_placebo = keep(orig)
        perm = bd.book_placebo_family(d, draws=6, seed=300, estimator="expanding", n_boot=5, scheme="permute")
        boot = bd.book_placebo_family(d, draws=6, seed=300, estimator="expanding", n_boot=5, scheme="bootstrap")
    finally:
        bd.shuffle_book_increments_placebo = orig
    assert perm["tests"]["B2"]["beta"] < -0.1 and not perm["tests"]["B2"]["covers_zero"]
    assert abs(boot["tests"]["B2"]["beta"]) < 0.05 and boot["tests"]["B2"]["covers_zero"]
    with pytest.raises(ValueError):
        bd.shuffle_book_increments_placebo(d, 1, "nope")


def test_log_trials_revision_label(tmp_path):
    path = tmp_path / "trials.jsonl"
    res = {"tests": {n: {"beta": 0.0, "p": 0.5, "reject": False} for n in bd.J4_SPEC}, "prior_tests": {"total": 1}}
    draws = [{"tests": {n: {"testable": True, "beta": b, "se": 0.1, "mde_80": 0.3, "n": 10}
                          for n in bd.J4_SPEC}} for b in (-0.02, 0.01, 0.03)]
    fam = bd._summarise_placebo(draws, list(bd.J4_SPEC), "expanding", 1)
    lines = bd.log_trials("J4", res, "x/r.json", "abc", "bounce-t", {}, placebo=fam, path=path,
                          revision="j4r_expanding_v1")
    assert len(lines) == 11 and {x["revision"] for x in lines} == {"j4r_expanding_v1"}
    assert fam["placebo_null"] is True
    assert battery2.cumulative_count(path)["total"] == 5
