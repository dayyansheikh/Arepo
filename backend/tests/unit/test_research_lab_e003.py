"""E003 tests on synthetic sweeps (no network, no real data)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import e003

REG = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
T0 = REG + timedelta(minutes=10)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def write_snapshot(root, snap_id, markets, chg=None, events=None):
    d = Path(root) / snap_id
    d.mkdir(parents=True)
    rows = pd.DataFrame({
        "market_id": markets,
        "event_id": events if events is not None else [f"ev{i // 2}" for i in range(len(markets))],
        "chg_1h": chg if chg is not None else [0.0] * len(markets),
    })
    rows.to_csv(d / "rows.csv.gz", index=False)
    return d


def write_sweep(root, sid, series, idx, start, snap, rows, state="complete", length=3):
    d = Path(root) / sid
    d.mkdir(parents=True)
    recv = iso(start + timedelta(seconds=5))
    recs = []
    for r in rows:
        base = {"sweep_id": sid, "batch_receipt_utc": recv, "state": "two_sided",
                "bid_size_1": 10.0, "ask_size_1": 10.0, "depth_bid_5c": 10.0,
                "depth_ask_5c": 10.0}
        recs.append({**base, **r})
    pd.DataFrame(recs).to_csv(d / "rows.csv.gz", index=False)
    man = {"sweep_id": sid, "series_id": series, "series_index": idx, "series_length": length,
           "snapshot_id": snap, "started_utc": iso(start),
           "finished_utc": iso(start + timedelta(seconds=60)), "state": state}
    (d / "manifest.json").write_text(json.dumps(man))


def make_series(
    sweeps, snaps, name, start, a, b, c, markets, chg=None, events=None, state="complete"
):
    snap = f"snap_{name}"
    write_snapshot(snaps, snap, markets, chg, events)
    for i, rows in enumerate((a, b, c)):
        write_sweep(sweeps, f"{name}_{i}", name, i, start + timedelta(minutes=2 * i), snap, rows,
                    state=state if i == 2 else "complete")


def row(tok, mkt, bid, ask, **kw):
    return {"token_id": tok, "market_id": mkt, "best_bid": bid, "best_ask": ask, **kw}


def test_series_selection_rules(tmp_path):
    sw, sn = tmp_path / "sw", tmp_path / "sn"
    m = ["1"]
    one = [row("t1", "1", 0.4, 0.5)]
    # pre-registration series is ignored
    make_series(sw, sn, "pre", REG - timedelta(hours=2), one, one, one, m)
    # incomplete series is not "complete 3-sweep"
    make_series(sw, sn, "bad", T0, one, one, one, m, state="incomplete:x")
    make_series(sw, sn, "s1", T0 + timedelta(minutes=30), one, one, one, m)
    # starts 30 min after S1 ends (< 60): not S2
    make_series(sw, sn, "early", T0 + timedelta(minutes=64), one, one, one, m)
    make_series(sw, sn, "s2", T0 + timedelta(minutes=30 + 4 + 1 + 60), one, one, one, m)
    s1, s2 = e003.select_series(e003.list_series(sw), REG)
    assert s1["series_id"] == "s1" and s2["series_id"] == "s2"
    assert (s2["start"] - s1["end"]) >= timedelta(minutes=60)
    assert e003.select_series(e003.list_series(sw), REG + timedelta(days=1)) == (None, None)


def test_s2_none_when_gap_too_small(tmp_path):
    sw, sn = tmp_path / "sw", tmp_path / "sn"
    one = [row("t1", "1", 0.4, 0.5)]
    make_series(sw, sn, "s1", T0, one, one, one, ["1"])
    make_series(sw, sn, "x", T0 + timedelta(minutes=30), one, one, one, ["1"])
    s1, s2 = e003.select_series(e003.list_series(sw), REG)
    assert s1["series_id"] == "s1" and s2 is None


def test_feature_formulas_and_zero_size_guard():
    a = pd.DataFrame({
        "best_bid": [0.40, 0.40, 0.40], "best_ask": [0.50, 0.50, 0.50],
        "bid_size_1": [30.0, 0.0, 10.0], "ask_size_1": [10.0, 0.0, 10.0],
        "depth_bid_5c": [60.0, 5.0, 0.0], "depth_ask_5c": [20.0, 5.0, 0.0],
    }, index=["a", "b", "c"])
    f = e003.compute_features(a)
    assert f.loc["a", "I1"] == pytest.approx(0.5)
    mid = 0.45
    assert f.loc["a", "micro"] == pytest.approx((0.5 * 30 + 0.4 * 10) / 40 - mid)
    assert f.loc["a", "I5"] == pytest.approx(0.5)
    assert f.loc["a", "spread"] == pytest.approx(0.10)
    assert np.isnan(f.loc["b", "I1"]) and np.isnan(f.loc["b", "micro"])
    assert np.isnan(f.loc["c", "I5"])
    assert f.loc["b", "I5"] == 0.0


def test_panel_targets_reasons_and_exclusions(tmp_path):
    sw, sn = tmp_path / "sw", tmp_path / "sn"
    mk = ["1", "2", "3", "4", "5"]
    a = [row(f"t{i}", mk[i - 1], 0.40, 0.50) for i in range(1, 6)]
    a[3] = row("t4", "4", 0.4, 0.5, bid_size_1=0.0, ask_size_1=0.0)  # zero-size -> excluded
    a[4]["state"] = "one_sided"  # t5 not in the unit
    b = [row("t1", "1", 0.44, 0.54), row("t2", "2", 0.4, None, state="one_sided"),
         row("t4", "4", 0.4, 0.5)]  # t3 missing from sweep B
    c = [row("t1", "1", 0.50, 0.60), row("t2", "2", 0.4, 0.5), row("t3", "3", 0.42, 0.52),
         row("t4", "4", 0.4, 0.5)]
    make_series(sw, sn, "s1", T0, a, b, c, mk, chg=[0.01, None, 0.0, 0.0, 0.0],
                events=["e1", "e1", None, "e2", "e2"])
    s1, _ = e003.select_series(e003.list_series(sw), REG)
    df, cnt = e003.build_panel(s1, sn)
    df = df.set_index("token_id")
    assert cnt["tokens_two_sided_A"] == 4
    # target uses only B / C mids
    assert df.loc["t1", "dmid_AB"] == pytest.approx(0.49 - 0.45)
    assert df.loc["t1", "dmid_AC"] == pytest.approx(0.55 - 0.45)
    assert cnt["target_unavailable_AB"] == {"one_sided": 1, "missing_from_sweep": 1}
    assert cnt["target_unavailable_AC"] == {}
    assert df.loc["t1", "horizon_B_s"] == pytest.approx(120.0)
    assert df.loc["t1", "horizon_C_s"] == pytest.approx(240.0)
    assert bool(df.loc["t4", "feature_ok"]) is False and cnt["excluded_feature_nan"] == 1
    assert cnt["event_id_fallback_to_market_id"] == 1
    assert df.loc["t3", "event_key"] == "m:3"
    assert df.loc["t2", "chg_1h"] == 0.0 and df.loc["t2", "chg_1h_missing"] == 1.0
    assert set(e003.usable(df.reset_index(), "AB")["token_id"]) == {"t1"}
    # changing A-only information after the fact must not alter B-based targets
    assert df.loc["t1", "mid_B"] == pytest.approx(0.49)


def synth(n, slope_i1, rng, noise=0.01, chg_coef=0.0):
    """Synthetic panel frame with a planted I1 -> dmid relation."""
    i1 = rng.uniform(-1, 1, n)
    micro = 0.05 * i1 + rng.normal(0, 0.002, n)
    chg = rng.normal(0, 0.02, n)
    y = slope_i1 * i1 + chg_coef * chg + rng.normal(0, noise, n)
    return pd.DataFrame({
        "token_id": [f"t{i}" for i in range(n)], "market_id": [f"m{i}" for i in range(n)],
        "event_key": [f"e:{i // 3}" for i in range(n)], "I1": i1, "micro": micro,
        "I5": rng.uniform(-1, 1, n), "spread": rng.uniform(0.01, 0.1, n), "chg_1h": chg,
        "dmid_AB": y, "dmid_AC": y, "feature_ok": True,
    })


def test_fit_recovers_signal_and_planted_verdicts():
    rng = np.random.default_rng(0)
    s1 = synth(3000, 0.02, rng)
    fit = e003.fit_models(s1)
    assert fit["M8"]["I1"] == pytest.approx(0.02, rel=0.15)
    assert fit["M9"]["micro"] > 0 and "intercept" in fit["MC"]
    s2 = synth(3000, 0.02, np.random.default_rng(1))
    res = e003.score_series(s2, fit)
    p = res["primary_AB"]
    assert p["a_M8_vs_R0"]["verdict"] == "supported (exploratory)"
    assert p["c_MC_vs_R1"]["verdict"] == "supported (exploratory)"
    assert p["H09_beyond_H08"]["adds_beyond"] is False or p["H09_beyond_H08"]["ci"][0] > 0
    assert set(res["spread_terciles_AB_descriptive"]) == {"low", "mid", "high"}
    # sign flip in S2 -> wrong sign
    flipped = e003.score_series(synth(3000, -0.02, np.random.default_rng(2)), fit)
    assert flipped["primary_AB"]["a_M8_vs_R0"]["verdict"] == "wrong sign"
    # no signal -> inconclusive
    null = e003.score_series(synth(3000, 0.0, np.random.default_rng(3)), fit)
    assert null["primary_AB"]["a_M8_vs_R0"]["verdict"] in ("inconclusive", "wrong sign")
    assert null["primary_AB"]["a_M8_vs_R0"]["verdict"] != "supported (exploratory)"


def test_verdict_rule():
    assert e003.verdict(0.1, (0.01, 0.2), 1, 1) == "supported (exploratory)"
    assert e003.verdict(0.1, (-0.01, 0.2), 1, 1) == "inconclusive"
    assert e003.verdict(0.1, (0.01, 0.2), -1, 1) == "wrong sign"


def build_two_series(tmp_path, s2_slope):
    sw, sn = tmp_path / "sw", tmp_path / "sn"
    rng = np.random.default_rng(5)

    def sweeps(n, slope, tag):
        d = synth(n, slope, rng)
        mk = [f"{tag}{i}" for i in range(n)]
        evs = [f"{tag}e{i // 3}" for i in range(n)]
        # I1 via sizes: (b-a)/(b+a) = i1 with b+a = 20
        bs = 10 * (1 + d["I1"]).to_numpy()
        a_rows = [row(f"{tag}t{i}", mk[i], 0.40, 0.50, bid_size_1=bs[i], ask_size_1=20 - bs[i])
                  for i in range(n)]
        mid_b = [0.45 + d["dmid_AB"][i] for i in range(n)]
        b_rows = [row(f"{tag}t{i}", mk[i], mid_b[i] - 0.05, mid_b[i] + 0.05) for i in range(n)]
        return mk, evs, a_rows, b_rows

    mk, evs, a, b = sweeps(600, 0.02, "x")
    make_series(sw, sn, "s1", T0, a, b, b, mk, events=evs)
    return sw, sn, tmp_path / "out", rng, sweeps


def test_frozen_fit_not_refit_and_refuse_overwrite(tmp_path):
    sw, sn, out, rng, sweeps = build_two_series(tmp_path, 0.02)
    payload = e003.fit_s1(sw, sn, out, REG)
    assert payload["n_fit"] > 500 and payload["in_sample"]["label"].startswith("DEVELOPMENT")
    with pytest.raises(FileExistsError):
        e003.fit_s1(sw, sn, out, REG)
    # no S2 yet
    with pytest.raises(RuntimeError):
        e003.score_s2(sw, sn, out, REG)
    mk, evs, a, b = sweeps(600, -0.02, "y")  # S2 with the opposite relation
    make_series(sw, sn, "s2", T0 + timedelta(hours=3), a, b, b, mk, events=evs)
    fit_bytes = (out / "s1_fit.json").read_bytes()
    res = e003.score_s2(sw, sn, out, REG)
    assert (out / "s1_fit.json").read_bytes() == fit_bytes  # frozen file untouched
    frozen = json.loads(fit_bytes)["fit"]
    assert res["primary_AB"]["a_M8_vs_R0"]["s1_coef"] == frozen["M8"]["I1"]  # frozen coef used
    assert res["primary_AB"]["a_M8_vs_R0"]["verdict"] == "wrong sign"
    assert res["s2_series_id"] == "s2" and res["gap_min"] >= 60
    with pytest.raises(FileExistsError):
        e003.score_s2(sw, sn, out, REG)
