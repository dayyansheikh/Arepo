"""Mechanical E009/E010/E011 verdicts from frozen analysis outputs (synthetic dicts only)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from astrolabe.research_lab import live_verdicts as lv


def e9(**kw):
    h = {"status": "ok", "n_clusters": 40, "n_origins": 60000, "rel_mse_gain": 0.05,
         "p_one_sided": 0.01, "ci": [0.01, 0.09], "slope_dp_on_dk1": 0.2,
         "partial_slope_ci": [-0.1, 0.3]}
    h.update(kw)
    return {"horizons": {"20": h}, "executable_pnl": {"status": "below_minimum"}}


def test_e009_decision_table():
    assert lv.verdict_e009(e9())["verdict"] == lv.SUPPORTED
    assert lv.verdict_e009(e9(slope_dp_on_dk1=-0.1))["verdict"] == "Inconclusive"
    assert lv.verdict_e009(e9(p_one_sided=0.2))["verdict"] == "Inconclusive"
    c = e9(rel_mse_gain=-0.05, p_one_sided=0.99, ci=[-0.09, -0.01])
    assert lv.verdict_e009(c)["verdict"] == "Contradicted"
    c["horizons"]["20"]["partial_slope_ci"] = [0.05, 0.4]
    assert lv.verdict_e009(c)["verdict"].endswith("frozen scale miscalibrated")
    assert lv.verdict_e009(e9(n_clusters=19))["verdict"] == "Unavailable"
    assert lv.verdict_e009(e9(n_origins=4999))["verdict"] == "Unavailable"
    assert lv.verdict_e009({"horizons": {"20": {"status": "insufficient"}}})["verdict"] == (
        "Unavailable")
    r = e9()
    assert lv.verdict_e009(r)["economics"] == "not shown"
    r["executable_pnl"] = {"status": "ok", "mean_pnl_per_share": 0.01, "p_one_sided": 0.01}
    assert lv.verdict_e009(r)["economics"] == "covers taker costs (paper)"


def e10(h60=None, h360=None, holm=None):
    base = {"status": "ok", "n_clusters": 40, "n_origins": 30000, "rel_mse_gain_m1": 0.1,
            "p_one_sided_m1": 0.01, "ci_m1": [0.02, 0.2], "executable_pnl": {"status": "ok",
            "mean_pnl_per_share": -0.01, "p_one_sided": 0.9}}
    return {"horizons": {"60": {**base, **(h60 or {})}, "360": {**base, **(h360 or {})}},
            "holm_m1": holm or {"60": 0.02, "360": 0.02}}


def test_e010_decision_table_uses_holm_adjusted_p():
    v = lv.verdict_e010(e10())
    assert {h: x["verdict"] for h, x in v["horizons"].items()} == {"60": lv.SUPPORTED,
                                                                  "360": lv.SUPPORTED}
    assert not v["verdicts_differ"] and v["holm_declared"] == v["holm_m1_frozen"]
    v = lv.verdict_e010(e10(holm={"60": 0.06, "360": 0.02}))
    assert v["horizons"]["60"]["verdict"] == "Inconclusive"  # raw p 0.01, Holm 0.06
    v = lv.verdict_e010(e10(h360={"rel_mse_gain_m1": -0.1, "ci_m1": [-0.2, -0.01]},
                            holm={"60": 0.02, "360": 1.0}))
    assert v["horizons"]["360"]["verdict"] == "Contradicted"
    assert v["horizons"]["360"]["economics"] == "not shown"


def test_e010_unavailable_horizon_enters_holm_with_p_one():
    # 360 has 15 clusters (Unavailable) but status ok, so the frozen Holm used its own p (0.01):
    # frozen adjusted p for 60 = max(2 * 0.01, 0.03) = 0.03; declared = min(1, 2 * 0.03) = 0.06
    r = e10(h60={"p_one_sided_m1": 0.03}, h360={"n_clusters": 15, "p_one_sided_m1": 0.01},
            holm={"60": 0.03, "360": 0.02})
    v = lv.verdict_e010(r)
    assert v["horizons"]["360"]["verdict"] == "Unavailable"
    assert v["holm_declared"] == {"60": 0.06, "360": 1.0}
    assert v["horizons"]["60"]["verdict"] == "Inconclusive"  # declared rule
    assert v["verdicts_differ"] and v["verdicts_with_frozen_holm"]["60"] == lv.SUPPORTED
    # no difference when the available horizon's p is small enough either way
    r = e10(h60={"p_one_sided_m1": 0.001}, h360={"n_origins": 10},
            holm={"60": 0.002, "360": 0.01})
    v = lv.verdict_e010(r)
    assert v["holm_declared"]["60"] == 0.002 and not v["verdicts_differ"]


def test_e011_rederivation_matches_frozen_verdict():
    res = {"n_episodes_analysed": 3000, "n_clusters": 300, "p_one_sided": 0.01,
           "excess_mean": 0.02, "excess_ci95": [0.005, 0.03], "verdict": lv.SUPPORTED}
    assert lv.verdict_e011(res)["consistent"]
    res.update(n_clusters=9, verdict="Unavailable")
    assert lv.verdict_e011(res)["consistent"]


def test_script_reads_saved_json(tmp_path):
    f = tmp_path / "e009.json"
    f.write_text(json.dumps(e9()))
    script = Path(__file__).resolve().parents[1] / "scripts" / "live_verdicts.py"
    out = subprocess.run([sys.executable, str(script), "e009", str(f)], capture_output=True,
                         text=True, check=True).stdout
    d = json.loads(out)
    assert d["verdict"] == lv.SUPPORTED and len(d["input"]["sha256"]) == 64
