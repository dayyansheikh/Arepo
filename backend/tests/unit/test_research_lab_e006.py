"""Synthetic tests for E006 (reversal moderation by liquidity and time-to-end)."""

from __future__ import annotations

import gzip
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import e004, e006, extract

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_research_e006

REG = datetime(2026, 11, 1, tzinfo=UTC)
FMT = "%Y-%m-%dT%H:%M:%S.%fZ"
COEF = -0.33161
FIT = {
    "m_L": 5.0, "m_H": 6.0, "m_S": 0.03, "b_2": 0.02, "b_4": 0.03,
    "baseline": {"a": 0.0, "s": 0.0, "coef": COEF},
}


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(e004, "e002_capture_ids", lambda caps: set())
    same = {"registered": "h", "working_tree": "h"}
    monkeypatch.setattr(e006, "ledger_section_hashes", lambda: same)


def _frame(n, seed=0, gamma=0.6 * COEF, th2=0.0, th4=0.0, th_sp=0.0, miss=0.0, n_per=11):
    """Pair-level frame (post panel features) with dmid = gamma*chg + planted moderation."""
    rng = np.random.default_rng(seed)
    f = pd.DataFrame(
        {
            "market_id": [str(i) for i in range(n)],
            "event_id": [f"e{i // 3}" for i in range(n)],
            "period": np.arange(n) % n_per,
            "chg_1h": rng.normal(0, 0.05, n),
            "spread": rng.uniform(0.01, 0.08, n),
            "log_liq": rng.normal(FIT["m_L"], 1.5, n),
            "log_hours_to_end": rng.normal(FIT["m_H"], 1.2, n),
        }
    )
    f["chg_1h_missing"] = (rng.random(n) < miss).astype(float)
    f.loc[f["chg_1h_missing"] == 1, "chg_1h"] = 0.0
    f["end_unknown"] = 0.0
    f["liq_missing"] = 0.0
    chg = f["chg_1h"].to_numpy()
    dm = (
        gamma * chg
        + th2 * chg * (f["log_liq"] - FIT["m_L"])
        + th4 * chg * (f["log_hours_to_end"] - FIT["m_H"])
        + th_sp * chg * (f["spread"] - FIT["m_S"])
        + rng.normal(0, 0.005, n)
    )
    f["dmid"] = dm
    return f


def _mod(f):
    return e006.add_moderators(f, FIT["m_L"], FIT["m_H"], FIT["m_S"])


def test_centring_and_dev_fit_frame():
    f = _frame(4000, seed=1, miss=0.5, gamma=COEF, th2=0.05)
    f.loc[:99, "liq_missing"] = 1.0
    f.loc[100:199, "end_unknown"] = 1.0
    f.loc[100:199, "log_hours_to_end"] = 0.0
    info, z = e006.fit_dev_frame(f, 0.0, 0.0, COEF)
    obs = f["chg_1h_missing"] == 0
    exp_l = f.loc[obs & (f["liq_missing"] == 0), "log_liq"].mean()
    exp_h = f.loc[obs & (f["end_unknown"] == 0), "log_hours_to_end"].mean()
    assert info["m_L"] == float(f"{exp_l:.6g}") and info["m_H"] == float(f"{exp_h:.6g}")
    assert info["m_S"] == float(f"{f.loc[obs, 'spread'].mean():.6g}")
    assert info["H1"]["b"] == pytest.approx(0.05, abs=0.01)  # planted (gamma at frozen reversal)
    assert info["H1"]["n_excluded"] == 100 and info["H2"]["n_excluded"] == 100
    assert abs(info["H1"]["corr_chg_1h_zk"]) < 0.1  # centred: nearly orthogonal to chg_1h
    assert abs(z.loc[obs & (z["liq_missing"] == 0), "z2"].mean()) < 0.01


def test_z_construction_and_missing_rules():
    f = _frame(6, seed=2)
    f.loc[0, ["chg_1h_missing", "chg_1h"]] = [1.0, 0.0]
    f.loc[1, "liq_missing"] = 1.0
    f.loc[2, "end_unknown"] = 1.0
    z = _mod(f)
    assert z.loc[0, "z2"] == 0 and z.loc[0, "z4"] == 0 and z.loc[0, "obs"] == 0
    assert z.loc[3, "z2"] == pytest.approx(f.loc[3, "chg_1h"] * (f.loc[3, "log_liq"] - 5.0))
    hrs = f.loc[3, "log_hours_to_end"]
    assert z.loc[3, "z4"] == pytest.approx(f.loc[3, "chg_1h"] * (hrs - 6.0))
    assert not z.loc[1, "in_H1"] and z.loc[1, "in_H2"]
    assert z.loc[2, "in_H1"] and not z.loc[2, "in_H2"]
    assert z.loc[3, "spread_c"] == pytest.approx(f.loc[3, "spread"] - 0.03)


def test_theta_recovered_under_horizon_rescaling():
    # reversal rescaled to 0.6x (gamma != -0.3316); moderation planted on the same 0.6x scale
    f = _frame(6000, seed=3, th2=0.6 * 0.05, th4=-0.6 * 0.04)
    res, draws = e006.analyse_hyp(_mod(f), "H1", FIT["b_2"], FIT)
    assert res["gamma"] == pytest.approx(0.6 * COEF, abs=0.01)
    assert res["gamma_residual"] == pytest.approx(-0.4 * COEF, abs=0.01)
    assert res["theta"] == pytest.approx(0.03, abs=0.008)
    assert res["p_two_sided"] < 0.01 and len(draws["theta"]) == e006.BOOT_N
    ratio = res["S2_theta_over_gamma"]
    assert ratio["value"] == pytest.approx(res["theta"] / res["gamma"])
    assert ratio["value"] != pytest.approx(FIT["b_2"] / COEF, abs=0.01)
    res4, _ = e006.analyse_hyp(_mod(f), "H2", FIT["b_4"], FIT)
    assert res4["theta"] < 0 and res4["theta_ci95"][1] < 0  # sign opposite to frozen b_4 > 0
    assert res4["consistency"]["n_predicted_sign"] <= 2
    assert res["consistency"]["n_periods"] == 11 and res["consistency"]["n_predicted_sign"] >= 9


def test_missing_rules_in_hypothesis_samples():
    f = _frame(3000, seed=4, th2=0.03, miss=0.5)
    f.loc[:49, "liq_missing"] = 1.0
    f.loc[50:79, "end_unknown"] = 1.0
    r1, _ = e006.analyse_hyp(_mod(f), "H1", FIT["b_2"], FIT)
    r2, _ = e006.analyse_hyp(_mod(f), "H2", FIT["b_4"], FIT)
    assert r1["n_excluded_by_missing_rule"] == 50 and r2["n_excluded_by_missing_rule"] == 30
    assert r1["n_eff"] < 3000 - 50 and r1["K_eff"] <= r1["event_clusters_all"]


def test_holm():
    out = e006.holm({"H1": 0.02, "H2": 0.04})
    assert out["H1"]["rejected"] and out["H2"]["rejected"] and out["H1"]["threshold"] == 0.025
    out = e006.holm({"H1": 0.03, "H2": 0.04})
    assert not out["H1"]["rejected"] and not out["H2"]["rejected"]
    out = e006.holm({"H1": 0.30, "H2": 0.01})
    assert out["H2"]["rejected"] and not out["H1"]["rejected"]
    assert out["H1"]["threshold"] == 0.05
    out = e006.holm({"H1": float("nan"), "H2": 0.001})
    assert out["H2"]["rejected"] and not out["H1"]["rejected"]


def test_boot_p_and_ci():
    d = np.linspace(0.1, 1.0, 999)
    assert e006.boot_p(d) == pytest.approx(2 * 1 / 1000)
    assert e006.boot_ci(d)[0] > 0.1
    assert e006.boot_ci(d, 0.01)[0] < e006.boot_ci(d, 0.05)[0]


def test_guard_regression_separates_spread_interaction():
    # planted: chg*(spread-m_S) matters, z4 does not; guard theta ~ 0 and coef on spread term found
    f = _frame(8000, seed=5, th_sp=3.0, th4=0.0)
    res, _ = e006.analyse_hyp(_mod(f), "H2", FIT["b_4"], FIT)
    g = res["guard"]
    assert g["regressors"][2] == "chg_1h*(spread-m_S)" and len(g["coefs"]) == 4
    assert g["coefs"][2] == pytest.approx(3.0, abs=0.4)
    assert abs(g["theta"]) < 0.02
    # planted z4 with a spread confound: guard keeps theta
    f2 = _frame(8000, seed=6, th_sp=1.0, th4=0.04)
    r2, _ = e006.analyse_hyp(_mod(f2), "H2", FIT["b_4"], FIT)
    assert r2["guard"]["theta"] == pytest.approx(0.04, abs=0.01) and r2["guard"]["n"] == 8000
    f3 = _frame(2000, seed=7)
    f3.loc[:99, "end_unknown"] = 1.0
    r3, _ = e006.analyse_hyp(_mod(f3), "H1", FIT["b_2"], FIT)
    assert r3["guard"]["n"] == 1900 and not r3["guard"]["required_for_verdict"]


@pytest.mark.parametrize(
    ("reason", "rej", "theta", "b", "cons", "guard", "s1", "expected"),
    [
        (None, True, 0.02, 0.03, True, None, 0.001, "Supported and transferable"),
        (None, True, 0.02, 0.03, True, None, -0.001, "Supported (exploratory, prospective)"),
        (None, True, 0.02, 0.03, True, None, None, "Supported (exploratory, prospective)"),
        (None, True, -0.02, -0.03, True, True, 0.001, "Supported and transferable"),
        (None, True, 0.02, 0.03, True, False, 0.001, "Inconclusive"),
        (None, True, 0.02, 0.03, False, True, 0.001, "Inconclusive"),
        (None, False, 0.02, 0.03, True, True, 0.001, "Inconclusive"),
        (None, False, 0.0, 0.03, True, True, 0.001, "Not supported"),
        (None, True, -0.02, 0.03, True, True, 0.001, "Not supported"),
        ("n_eff", True, 0.02, 0.03, True, True, 0.001, "Unavailable (no verdict)"),
    ],
)
def test_verdict_rules(reason, rej, theta, b, cons, guard, s1, expected):
    assert e006.verdict(reason, rej, theta, b, cons, guard, s1) == expected


def _full(f, reason=None):
    res, draws = {}, {}
    for h, b in (("H1", FIT["b_2"]), ("H2", FIT["b_4"])):
        res[h], draws[h] = e006.analyse_hyp(_mod(f), h, b, FIT)
    return e006.finalise(res, draws, reason)


def test_finalise_verdicts_and_unavailable(monkeypatch):
    f = _frame(6000, seed=8, th2=0.6 * 0.05, th4=0.6 * 0.05)
    monkeypatch.setattr(e006, "MIN_N_EFF", 1000)
    monkeypatch.setattr(e006, "MIN_K_EFF", 100)
    out = _full(f)
    assert out["H1"]["verdict"].startswith("Supported")
    assert out["H2"]["verdict"].startswith("Supported") and out["H2"]["guard"]["passes"]
    assert out["H1"]["holm"]["rejected"]
    assert _full(f, "E004 unavailable")["H1"]["verdict"] == "Unavailable (no verdict)"
    monkeypatch.undo()  # defaults: n_eff < 2000 or K_eff < 500
    small = _full(_frame(1500, seed=9, th2=0.03))
    assert small["H1"]["verdict"] == "Unavailable (no verdict)"
    assert "n_eff" in small["H1"]["unavailable_reason"]
    ev = _frame(6000, seed=10)
    ev["event_id"] = [f"e{i // 20}" for i in range(6000)]  # 300 events only
    assert "K_eff" in _full(ev)["H1"]["unavailable_reason"]


def test_target_unavailable_by_liquidity():
    f = _frame(900, seed=11)
    f.loc[f["log_liq"] < f["log_liq"].quantile(0.2), "dmid"] = np.nan
    f.loc[:9, "liq_missing"] = 1.0
    s3 = e006.target_unavailable_by_liquidity(f)
    assert s3["n_missing_liquidity_pairs"] == 10
    assert s3["terciles"]["low"]["rate"] > s3["terciles"]["high"]["rate"]


def test_ledger_section_stops_at_non_claims():
    text = "x\n## E006 - t\n- a  \n- **Non-claims:** n\nmore\n"
    assert e006.ledger_section(text) == "## E006 - t\n- a\n- **Non-claims:** n"
    assert e006.ledger_section("none") == ""


# ------------------------------------------------------------ end to end (files)
def _rows(ids, ev, bid, ask, start, chg, liq, end):
    n = len(ids)
    df = pd.DataFrame({c: [None] * n for c in extract.COLUMNS})
    df["capture_start_utc"] = start.strftime(FMT)
    df["received_utc"] = (start + timedelta(seconds=5)).strftime(FMT)
    df["market_id"], df["event_id"] = ids, ev
    df["closed"], df["active"], df["binary"] = "False", "True", 1
    df["best_bid"], df["best_ask"] = bid, ask
    df["spread"] = ask - bid
    df["chg_1h"], df["liquidity"], df["volume24hr"] = chg, liq, 50.0
    df["end_date"] = end
    return df


def _series(k, seed, start, n=300, th2=0.03):
    rng = np.random.default_rng(seed)
    ids = [str(i) for i in range(n)]
    ev = [f"e{i // 3}" for i in range(n)]
    liq = np.exp(rng.normal(6, 1.2, n))
    end = [(start + timedelta(hours=float(h))).strftime(FMT) for h in rng.uniform(100, 3000, n)]
    mid = rng.uniform(0.2, 0.8, n)
    out = []
    for s in range(k):
        t = start + timedelta(hours=2 * s)
        chg = rng.normal(0, 0.04, n)
        out.append((t, _rows(ids, ev, mid - 0.01, mid + 0.01, t, chg, liq, end)))
        step = COEF * chg + th2 * chg * (np.log1p(liq) - 6) + rng.normal(0, 0.002, n)
        mid = np.clip(mid + step, 0.1, 0.9)
    return out


def _write_snaps(root, series):
    for i, (t, df) in enumerate(series):
        cid = f"S{i:02d}"
        d = root / cid
        d.mkdir(parents=True)
        with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
            df.assign(capture_id=cid).to_csv(fh, index=False)
        (d / "manifest.json").write_text(
            json.dumps({"capture_id": cid, "state": "complete", "started_utc": t.strftime(FMT)})
        )


def _write_dev(dev_dir, series):
    dev_dir.mkdir(parents=True)
    frames, caps = [], []
    for i, (t, df) in enumerate(series):
        frames.append(df.assign(capture_id=f"D{i}"))
        caps.append({"capture_id": f"D{i}", "start_utc": t.strftime(FMT)})
    pd.concat(frames).to_csv(dev_dir / "snapshots.csv.gz", index=False)
    (dev_dir / "manifest.json").write_text(json.dumps({"captures": caps}))


def _write_e005(path, coef=COEF):
    path.mkdir(parents=True)
    (path / "dev_fit.json").write_text(
        json.dumps({"baseline": {"a": 0.0, "s": 0.0, "coef": coef}})
    )


def test_fit_dev_files_and_refuse_overwrite(tmp_path):
    _write_dev(tmp_path / "dev", _series(6, 1, REG - timedelta(days=3)))
    _write_e005(tmp_path / "e5")
    fit = e006.fit_dev(tmp_path / "dev", tmp_path / "out", tmp_path / "e5")
    assert fit["b_2"] == pytest.approx(0.03, abs=0.01)
    assert fit["m_L"] == float(f"{fit['m_L']:.6g}") and fit["counts"]["H1"]["n_pairs_used"] > 0
    assert len(fit["provenance"]["code_sha256"]) == 64 and "corr_chg_1h_zk" in fit["counts"]["H2"]
    with pytest.raises(FileExistsError):
        e006.fit_dev(tmp_path / "dev", tmp_path / "out", tmp_path / "e5")
    _write_e005(tmp_path / "e5b", coef=-0.2)
    with pytest.raises(ValueError):
        e006.fit_dev(tmp_path / "dev", tmp_path / "out2", tmp_path / "e5b")


def test_score_pending_requires_fit_and_refuses_overwrite(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(e006, "MIN_N_EFF", 500)
    monkeypatch.setattr(e006, "MIN_K_EFF", 50)
    root = tmp_path / "s"
    _write_snaps(root, _series(11, 2, REG + timedelta(hours=1)))
    args = ["--snapshot-root", str(root), "--out-dir", str(tmp_path / "o"),
            "--registration-time", REG.isoformat(), "--trials-path", str(tmp_path / "t.jsonl")]
    assert run_research_e006.main(["score", *args]) == 0
    assert "Pending" in capsys.readouterr().out and not (tmp_path / "o").exists()
    assert run_research_e006.main(["score", "--status", *args]) == 0
    assert '"dev_fit_exists": false' in capsys.readouterr().out
    root2 = tmp_path / "s2"
    _write_snaps(root2, _series(13, 3, REG + timedelta(hours=1)))
    with pytest.raises(FileNotFoundError):
        e006.score(root2, tmp_path / "o2", REG, tmp_path / "e4")
    _write_dev(tmp_path / "dev", _series(6, 4, REG - timedelta(days=3)))
    _write_e005(tmp_path / "e5")
    assert run_research_e006.main(
        ["fit-dev", "--dev-dir", str(tmp_path / "dev"), "--e005-dir", str(tmp_path / "e5"), *args]
    ) == 0
    trial = json.loads((tmp_path / "t.jsonl").read_text().splitlines()[-1])
    assert trial["label"] == "E006 dev fit (frozen before confirmation)"
    with pytest.raises(FileExistsError):
        run_research_e006.main(
            ["fit-dev", "--dev-dir", str(tmp_path / "dev"), "--e005-dir", str(tmp_path / "e5"),
             *args]
        )
    e006.fit_dev(tmp_path / "dev", tmp_path / "o2", tmp_path / "e5")
    res = e006.score(root2, tmp_path / "o2", REG, tmp_path / "e4")
    h1 = res["hypotheses"]["H1"]
    assert h1["theta"] == pytest.approx(0.03, abs=0.01) and h1["consistency"]["n_periods"] == 11
    assert res["counts"]["periods_with_observed_chg_1h"] == 11
    assert res["global_unavailable_reason"] is None and h1["verdict"].startswith("Supported")
    assert res["provenance"]["dev_fit_sha256"]
    with pytest.raises(FileExistsError):
        e006.score(root2, tmp_path / "o2", REG, tmp_path / "e4")


def test_score_unavailable_on_spec_mismatch_and_e004(tmp_path, monkeypatch):
    monkeypatch.setattr(e006, "MIN_N_EFF", 500)
    monkeypatch.setattr(e006, "MIN_K_EFF", 50)
    root = tmp_path / "s"
    _write_snaps(root, _series(13, 5, REG + timedelta(hours=1)))
    _write_dev(tmp_path / "dev", _series(6, 6, REG - timedelta(days=3)))
    _write_e005(tmp_path / "e5")
    e006.fit_dev(tmp_path / "dev", tmp_path / "o", tmp_path / "e5")
    fit_p = tmp_path / "o" / "dev_fit.json"
    fit = json.loads(fit_p.read_text())
    fit["provenance"]["ledger_section_sha256"] = "other"  # frozen differs from registered
    (tmp_path / "o2").mkdir()
    (tmp_path / "o2" / "dev_fit.json").write_text(json.dumps(fit))
    res = e006.score(root, tmp_path / "o2", REG, tmp_path / "e4")
    assert "spec hash" in res["global_unavailable_reason"]
    assert res["hypotheses"]["H1"]["verdict"] == "Unavailable (no verdict)"
    (tmp_path / "e4").mkdir()
    (tmp_path / "e4" / "results.json").write_text(
        json.dumps({"primary": {"verdict": "Unavailable (no verdict)"}})
    )
    res2 = e006.score(root, tmp_path / "o", REG, tmp_path / "e4")
    assert res2["global_unavailable_reason"] == "E004 unavailable"


def test_unavailable_when_few_periods_observed():
    f = _frame(6000, seed=12, th2=0.03)
    f.loc[f["period"] >= 8, "chg_1h_missing"] = 1.0
    f.loc[f["period"] >= 8, "chg_1h"] = 0.0
    out = e006.analyse(f, [], {**FIT, "baseline": FIT["baseline"]}, True, False)
    assert out["counts"]["periods_with_observed_chg_1h"] == 8
    assert "periods" in out["global_unavailable_reason"]
    assert out["hypotheses"]["H1"]["verdict"] == "Unavailable (no verdict)"
