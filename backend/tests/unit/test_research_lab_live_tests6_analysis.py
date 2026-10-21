# ruff: noqa: E501
"""LT6 (LIVE_TESTS_6.md) code unit 3: the analysis skeleton. The estimator and the p = max rule (with the G_treated - 1 event t for D
and B), the gates, Holm over k, verdicts, labels and the counting record on small synthetic frames; the size-check worlds as declared
and the scenario-to-test map. Synthetic data only; the full size check is never run here."""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests6 as lt
from astrolabe.research_lab import live_tests6_analysis as la

HERE = Path(lt.__file__).resolve().parent


def _spec(**over) -> dict:
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["registered_utc"], spec["end_utc"], spec["analysis_not_before"] = "2026-11-16T00:00:00Z", "2026-12-07T00:00:00Z", "2026-12-08T12:00:00Z"
    spec["gates"]["draws"] = 40
    for t in ("v", "k", "d", "b"):
        spec[t]["exclude_family"] = ""
        spec[t]["perm_stratum"] = "day"
        for f in spec[t]["floors"]:
            spec[t]["floors"][f] = 1
    spec["v"].update(c_v=0.0, s_v=0.3, terciles=[-0.5, 0.5], tercile_gap=2.2)
    spec["b"]["fake_birth_terciles"] = [0.01, 0.02]
    spec["labels"]["partially_seen_d"] = False
    spec["k_tests"] = ["V", "K", "D", "B"]
    spec["code_sha256"] = {"x": "y"}
    spec["e022"]["dropped"] = True
    spec["_pinned"], spec["_sha256"] = True, "abc"
    spec.update(over)
    return spec


def _frame(test: str, seed: int, effect: float = 0.0, n_mkt: int = 40, n: int = 24) -> pd.DataFrame:
    """A prepared frame: the test's term, y, every control column the primary names, and the identifiers; a planted effect of ``effect``."""
    rng = np.random.default_rng(seed)
    cfg = la.PRIMARY[test]
    rows = []
    for m in range(n_mkt):
        lvl = rng.normal(0, 0.005)
        for i in range(n):
            r = {"market_id": f"m{m}", "event_id": f"e{m // 4}", "skey": f"event:e{m // 4}" if m % 5 else "ser-a", "t_row": 1.8e9 + i * 7200.0 + m,
                 "day": f"2026112{(i // 12)}"}
            for c in cfg["controls"]:
                r[c] = rng.normal()
            term = float(rng.random() < 0.3) if test != "V" else rng.normal()
            r[cfg["term"]] = term
            r[cfg["y"]] = lvl + effect * term + 0.003 * r[cfg["controls"][0]] + rng.normal(0, 0.02)
            rows.append(r)
    return pd.DataFrame(rows)


# --- p rule ---------------------------------------------------------------------------------------------------------------------


def test_event_df_rule():
    assert la.event_df(60, None, None) == 59
    assert la.event_df(60, 20, None) == 19  # D / B: G_treated - 1
    assert la.event_df(60, 20, 8) == 7  # the series-family df rule applies if smaller
    assert la.event_df(60, None, 8) == 7
    assert la.event_df(60, 1, None) == 0 and la.event_df(1, None, None) == 0


def test_fit6_uses_g_treated_for_the_event_t_and_reports_plain_cr1():
    df = _frame("D", 3, effect=0.02, n_mkt=60, n=18)
    # few treated events: keep the label only in 4 events
    df["LT"] = np.where(df["event_id"].isin(["e0", "e1", "e2", "e3"]), df["LT"], 0.0)
    y = df["y22"].to_numpy(float)
    r = la.fit6(df, y, "LT", la.PRIMARY["D"]["controls"], treated_col="LT", seed=1, n_boot=50)
    assert r["testable"] and r["g_treated"] == 4 and r["event_df"] == 3 and r["g_event"] > 10
    assert r["p_event_ref"] == "t on 3 df"
    assert r["p"] >= r["p_plain_cr1"]  # t on 3 df is wider than t on G_event - 1 df
    plain = la.fit6(df, y, "LT", la.PRIMARY["D"]["controls"], seed=1, n_boot=50)
    assert plain["event_df"] == plain["g_event"] - 1 and plain["g_treated"] is None
    assert plain["p"] == pytest.approx(r["p_plain_cr1"])
    lo, hi = r["ci95_cons"]
    assert lo < r["beta"] < hi and (hi - lo) >= (plain["ci95_cons"][1] - plain["ci95_cons"][0])  # the treated-df interval is not narrower
    assert r["p_rule"].startswith("max(p_event")


def test_p_is_the_max_of_the_three_clusterings():
    df = _frame("K", 5, effect=0.01)
    r = la.fit6(df, df["c_skip"].to_numpy(float), "CL", la.PRIMARY["K"]["controls"], seed=2, n_boot=50)
    assert r["p"] == pytest.approx(max(r["p_event"], r["p_twoway"], r["p_time_t"]))
    assert r["t_df"] >= 1 and r["se_twoway"] > 0


def test_series_family_df_applies_when_no_family_is_excluded():
    df = _frame("B", 7, n_mkt=40, n=16)
    df["skey"] = np.where(df["market_id"].str[1:].astype(int) % 2 == 0, "ser-a", "ser-b")
    r = la.fit6(df, df["a22"].to_numpy(float), "BR", la.PRIMARY["B"]["controls"], treated_col="BR", series_col="skey", seed=1, n_boot=20)
    assert r["g_series"] == 2 and r["event_df"] == 1


def test_both_demeaned_target_is_expanding_past():
    df = pd.DataFrame({"market_id": ["a", "a", "a", "b", "b"], "t_row": [1.0, 2.0, 3.0, 1.0, 2.0]})
    out = la.both_demeaned_y(df, np.array([1.0, 3.0, 8.0, 5.0, 7.0]))
    assert np.isnan(out[0]) and np.isnan(out[3])  # the first unit of each market drops
    assert out[1] == pytest.approx(3.0 - 1.0) and out[2] == pytest.approx(8.0 - 2.0) and out[4] == pytest.approx(7.0 - 5.0)


# --- gates ----------------------------------------------------------------------------------------------------------------------


def test_strata_and_gate_dispatch():
    df = pd.DataFrame({"market_id": ["a"] * 4, "t_row": [0.0, 3600.0, 90000.0, 200000.0], "day": ["1", "1", "2", "3"]})
    t0 = 0.0
    assert la.strata_of(df, "day", t0).tolist() == ["a|0", "a|0", "a|1", "a|2"]
    assert la.strata_of(df, "block2", t0).tolist() == ["a|0", "a|0", "a|0", "a|1"]
    assert la.strata_of(df, "market").tolist() == ["a"] * 4
    with pytest.raises(ValueError):
        la.strata_of(df, None, t0)
    with pytest.raises(ValueError):
        la.strata_of(df, "block2", None)
    spec = _spec()
    f = _frame("V", 11, n_mkt=24, n=20)
    g = la.gate_for("V", f, f["c_vskip"].to_numpy(float), spec)
    assert g["method"] == "block circular-shift Freedman-Lane" and g["min_n"] == 16
    f = _frame("K", 11, n_mkt=24, n=20)
    g = la.gate_for("K", f, f["c_skip"].to_numpy(float), spec, t0=lt.epoch(spec["registered_utc"]))
    assert g["method"] == "Freedman-Lane"
    spec["k"]["perm_stratum"] = None
    with pytest.raises(ValueError, match="perm_stratum"):
        la.gate_for("K", f, f["c_skip"].to_numpy(float), spec, t0=0.0)


def test_gate_detects_a_planted_effect_and_holds_on_a_null():
    spec = _spec()
    spec["gates"]["draws"] = 100
    t0 = 1.8e9 - 1.8e9 % 86400
    strong = _frame("K", 21, effect=0.05)
    assert la.gate_for("K", strong, strong["c_skip"].to_numpy(float), spec, t0)["passes"] is True
    null = _frame("K", 22, effect=0.0)
    assert la.gate_for("K", null, null["c_skip"].to_numpy(float), spec, t0)["passes"] is False


# --- one primary, Holm, verdicts ------------------------------------------------------------------------------------------------------


def test_run_primary_floors_family_exclusion_and_sensitivity():
    spec = _spec()
    f = _frame("D", 31, effect=0.03)
    r = la.run_primary("D", f, spec, t0=lt.epoch(spec["registered_utc"]), n_boot=30)
    assert r["available"] and r["primary"]["testable"] and r["gate"]["testable"] and r["sensitivity_both_demeaned"]["testable"]
    assert r["floors"]["counts"]["later_units"] > 0 and r["primary"]["g_treated"] is not None
    spec2 = copy.deepcopy(spec)
    spec2["d"]["floors"]["later_units"] = 10**9
    r2 = la.run_primary("D", f, spec2, t0=0.0, n_boot=30)
    assert r2["available"] is False and "primary" not in r2 and "later_units" in r2["floors"]["below"]
    spec3 = copy.deepcopy(spec)
    spec3["d"]["exclude_family"] = "ser-a"
    r3 = la.run_primary("D", f, spec3, t0=lt.epoch(spec["registered_utc"]), n_boot=30)
    assert r3["n_units"] < r["n_units"] and r3["exclude_family"] == "ser-a"
    assert r3["primary"]["g_series"] is None  # the series df rule applies only where no family is excluded


def test_analyze_frames_holm_verdicts_and_counting_equals_k():
    spec = _spec()
    frames = {"V": _frame("V", 41, effect=0.0), "K": _frame("K", 42, effect=0.06), "D": _frame("D", 43), "B": _frame("B", 44)}
    out = la.analyze_frames(frames, spec, force=True, t0=lt.epoch(spec["registered_utc"]), n_boot=60)
    assert out["trial"] == {"kind": "live_tests6", "n_tests": 4, "spec_sha256": "abc"}
    assert out["holm"]["m"] == 4 and set(out["holm"]["p_holm"]) == {"V", "K", "D", "B"}
    # Holm is monotone and capped at 1; a primary that fails its gate enters with p = 1
    ph = out["holm"]["p_holm"]
    assert all(0 <= v <= 1 for v in ph.values())
    assert out["tests"]["K"]["verdict"]["verdict"].startswith("Supported") or "Inconclusive" in out["tests"]["K"]["verdict"]["verdict"]
    for t in ("V", "D", "B"):
        assert not out["tests"][t]["verdict"]["verdict"].startswith("Supported")
    sub = _spec(k_tests=["K", "B"])
    out2 = la.analyze_frames({"K": frames["K"], "B": frames["B"]}, sub, force=True, t0=lt.epoch(spec["registered_utc"]), n_boot=30)
    assert out2["trial"]["n_tests"] == 2 and out2["holm"]["tests"] == ["K", "B"] and set(out2["tests"]) == {"K", "B"}


def test_analyze_frames_refusals():
    _spec()
    fr = {"K": _frame("K", 1, n_mkt=6, n=8)}
    with pytest.raises(RuntimeError, match="before"):
        la.analyze_frames(fr, _spec(k_tests=["K"]), now=lt.epoch("2026-12-08T11:59:59Z"))
    with pytest.raises(RuntimeError, match="DRAFT"):
        la.analyze_frames(fr, _spec(k_tests=["K"], analysis_not_before=None))
    s = _spec(k_tests=["K"])
    s["_pinned"] = False
    with pytest.raises(RuntimeError, match="not pinned"):
        la.analyze_frames(fr, s, force=True)
    with pytest.raises(RuntimeError, match="k_tests is null"):
        la.analyze_frames(fr, _spec(k_tests=None), force=True)
    with pytest.raises(RuntimeError, match="at most once"):
        la.analyze_frames(fr, _spec(k_tests=["K", "E022"]), force=True)
    with pytest.raises(RuntimeError, match="at most once"):
        la.analyze_frames(fr, _spec(k_tests=["K", "K"]), force=True)
    with pytest.raises(RuntimeError, match="no frame"):
        la.analyze_frames(fr, _spec(k_tests=["K", "B"]), force=True)
    # at the analysis date it runs
    out = la.analyze_frames(fr, _spec(k_tests=["K"]), now=lt.epoch("2026-12-08T12:00:00Z"), t0=lt.epoch("2026-11-16T00:00:00Z"), n_boot=20)
    assert out["trial"]["n_tests"] == 1


def test_size_scenario_failure_sets_only_its_tests_to_p_one_k_unchanged():
    spec = _spec()
    frames = {"K": _frame("K", 42, effect=0.06), "D": _frame("D", 43, effect=0.06)}
    sub = _spec(k_tests=["K", "D"])
    sc = {"se_check_failed_size_scenario": ["D"], "scenarios": {"s06_fl_d_event_label_ma10": {"binding_for": ["D"], "analytic_rates": {"oversized": True}},
                                                              "s01_fl_binary_iid": {"binding_for": ["K"], "analytic_rates": {"oversized": False}}}}
    out = la.analyze_frames(frames, sub, size_check=sc, force=True, t0=lt.epoch(spec["registered_utc"]), n_boot=40)
    assert out["trial"]["n_tests"] == 2 and out["holm"]["p_raw"]["D"] == 1.0 and out["holm"]["m"] == 2
    assert "SE check failed (size scenario)" in out["tests"]["D"]["verdict"]["verdict"] and out["tests"]["D"]["verdict"]["p_for_holm"] == 1.0
    assert out["holm"]["p_raw"]["K"] < 1.0


def test_labels_material_and_oversized_and_partially_seen():
    spec = _spec(k_tests=["K", "B"])
    spec["labels"]["partially_seen_d"] = None
    assert la.is_material("K", {"primary": {"testable": True, "beta": 0.006}}, spec) is True
    assert la.is_material("K", {"primary": {"testable": True, "beta": 0.004}}, spec) is False
    assert la.is_material("B", {"primary": {"testable": True, "beta": 0.006}}, spec) is False  # B needs 1.0c
    assert la.is_material("B", {"primary": {"testable": True, "beta": 0.011}}, spec) is True
    assert la.is_material("V", {"primary": {"testable": True, "beta": 0.003}}, spec) is True  # 0.3c per SD x gap 2.2 = 0.66c >= 0.5c
    assert la.is_material("V", {"primary": {"testable": False}}, spec) is False
    frames = {"K": _frame("K", 51, effect=0.0), "B": _frame("B", 52, effect=0.0)}
    sc = {"se_check_failed_size_scenario": [], "scenarios": {"s07_fl_b_abs_target": {"binding_for": ["B"], "analytic_rates": {"oversized": True}}}}
    out = la.analyze_frames(frames, spec, size_check=sc, force=True, t0=lt.epoch(spec["registered_utc"]), n_boot=30)
    assert "analytic p oversized in simulation" in out["tests"]["B"]["verdict"]["verdict"]
    specd = _spec(k_tests=["D"])
    specd["labels"]["partially_seen_d"] = None
    outd = la.analyze_frames({"D": _frame("D", 53)}, specd, force=True, t0=lt.epoch("2026-11-16T00:00:00Z"), n_boot=30)
    assert "partially seen" in outd["tests"]["D"]["verdict"]["verdict"]


# --- simulated worlds, as declared (1.8.1) ---------------------------------------------------------------------------------------------


def test_event_label_world_matches_declaration():
    rng = np.random.default_rng(5)
    df, y = la.sim_event_label_world(rng, label_p=0.006, absolute=True)
    n = df.groupby("market_id").size()
    assert df["market_id"].nunique() == 240 and n.min() >= 24 and n.max() <= 120 and df["event_id"].nunique() == 60
    assert (y == df["y"]).all() and df["L"].isin([0.0, 1.0]).all() and df["L"].sum() > 0
    # an edit labels EVERY market of the event at that unit
    lab = df[df["event_id"] == df.loc[df["L"] == 1, "event_id"].iloc[0]]
    by_unit = lab.groupby("t_row")["L"].agg(["min", "max", "size"])
    assert (by_unit["min"] == by_unit["max"]).all() or (by_unit.loc[by_unit["size"] > 1, "min"] == by_unit.loc[by_unit["size"] > 1, "max"]).all()
    assert abs(float(np.corrcoef(df["L"], df["c1"])[0, 1]) - 0.5) < 0.1  # the control correlates about 0.5 with the label (the census cap)
    d6, y6 = la.sim_event_label_world(np.random.default_rng(6), label_p=0.004, absolute=False)
    assert (y6 < 0).any() and (y < 0).sum() < (y6 < 0).sum()  # the absolute target (scenario 7) is non-negative up to the level and control terms
    # scenario 12: markets with a higher level are labelled more often
    d12, _ = la.sim_event_label_world(np.random.default_rng(7), label_p=0.004, level_edits=True)
    assert d12["L"].sum() > 0
    # a planted effect moves the labelled units' target
    base, _ = la.sim_event_label_world(np.random.default_rng(8), label_p=0.02)
    planted, _ = la.sim_event_label_world(np.random.default_rng(8), label_p=0.02, effect=0.05)
    diff = (planted["y"] - base["y"])[base["L"] == 1]
    assert diff.mean() == pytest.approx(0.05, abs=1e-9) and ((planted["y"] - base["y"])[base["L"] == 0] == 0).all()


def test_stochvol_world_matches_declaration():
    rng = np.random.default_rng(9)
    df, y = la.sim_stochvol_world(rng)
    assert df["market_id"].nunique() == 240 and df["event_id"].nunique() == 60 and {"a1", "a6", "a24", "loo_a1", "L"} <= set(df.columns)
    assert (y >= 0).all() or (y > -0.2).all()  # level (SD 0.01) + |S|
    assert df["a1"].ge(0).all() and df["a24"].ge(0).all() and df["loo_a1"].notna().mean() > 0.9
    assert df["L"].mean() > 0.003  # a listing hazard of about 0.006 exp(sbar), truncated at 0.05
    # the - 0.25 keeps the MEAN variance of the market shocks at the base 0.0173^2 (E[exp(2 (s - 0.25))] = 1 when Var(s) = 0.25)
    big = np.random.default_rng(10)
    s = 0.5 * big.standard_normal(2_000_000)
    assert float(np.mean(np.exp(2 * (s - 0.25)))) == pytest.approx(1.0, abs=0.02)
    # clustering of volatility: |prior move| predicts the listing label (the hazard rises with current volatility)
    big_df, _ = la.sim_stochvol_world(np.random.default_rng(12))
    assert float(np.corrcoef(big_df["L"], big_df["a1"])[0, 1]) > 0.0


def test_v_world_and_k_world_match_declaration():
    rng = np.random.default_rng(13)
    df, _ = la.sim_v_world(rng, rho=0.9)
    n = df.groupby("market_id").size()
    assert df["market_id"].nunique() == 80 and n.min() >= 6 and n.max() <= 60
    wz = df["z"] - df.groupby("market_id")["z"].transform("mean")
    wc = df["c1"] - df.groupby("market_id")["c1"].transform("mean")
    assert 0.2 < float(np.corrcoef(wz, wc)[0, 1]) < 0.7
    k, _ = la.sim_markov_ma2_world6(rng, persistence=0.9)
    nk = k.groupby("market_id").size()
    assert k["market_id"].nunique() == 60 and nk.min() >= 6 and nk.max() <= 60
    rates = k.groupby("market_id")["P"].mean()
    assert rates.mean() < 0.3  # rarer than LT5's jumps (U(0.15, 0.6))


# --- size check -----------------------------------------------------------------------------------------------------------------------------


def _sized_spec(k=("V", "K", "D", "B"), strata=("day", "block2", "day")) -> dict:
    """A copy of the draft spec with k_tests and the census-fixed strata filled (TEST ONLY: the real values come from the censuses)."""
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["k_tests"] = list(k)
    for t_, st_ in zip(("k", "d", "b"), strata, strict=True):
        spec[t_]["perm_stratum"] = st_
    return spec


def test_scenario_table_matches_the_specs_binding_map_and_order():
    spec = lt.load_spec(sha=None)
    table = la.scenario_table(np.random.default_rng(1), 5, {}, strata=la.size_strata(_sized_spec(), spec["size_check"]["scenarios"]))
    assert list(table) == list(spec["size_check"]["scenarios"])  # table order = the spec's order = the design's
    tests = sorted(t for v in spec["size_check"]["scenarios"].values() for t in v)
    assert tests == ["B", "B", "D", "K", "K", "K", "K", "K", "V", "V", "V"]
    assert la.NOMINALS == (0.0125, 0.05)


def test_size_check_fails_closed_on_binding_map():
    spec = _sized_spec()
    with pytest.raises(ValueError):
        la.size_check(worlds=1, draws=3, seed=1, binding={"s01_fl_binary_iid": ["K"]}, spec=spec, dev=True)
    bad = dict(spec["size_check"]["scenarios"])
    bad.pop(sorted(bad)[0])
    with pytest.raises(ValueError):
        la.size_check(worlds=1, draws=3, seed=1, binding=bad, spec=spec, dev=True)
    bad2 = dict(spec["size_check"]["scenarios"], s99_unknown=["K"])
    with pytest.raises(ValueError):
        la.size_check(worlds=1, draws=3, seed=1, binding=bad2, spec=spec, dev=True)


def test_size_check_maps_failures_to_tests_only(monkeypatch):
    calls = {"s01_fl_binary_iid": lambda: True, "s08_block_v_rho0": lambda: False}
    monkeypatch.setattr(la, "scenario_table", lambda rng, draws, rates, **kw: calls)
    r = la.size_check(worlds=20, draws=9, seed=1, binding={"s01_fl_binary_iid": ["K"], "s08_block_v_rho0": ["V"]}, spec=_sized_spec(), dev=True)
    assert r["se_check_failed_size_scenario"] == ["K"] and not r["all_ok"]
    assert r["scenarios"]["s08_block_v_rho0"]["ok"] and not r["scenarios"]["s01_fl_binary_iid"]["ok"]
    assert r["limit"] == pytest.approx(0.05 + 1.645 * math.sqrt(0.0475 / 20))


def test_size_check_small_run_all_scenarios_with_analytic_rates():
    r = la.size_check(worlds=2, draws=9, seed=11, spec=_sized_spec(), dev=True)
    assert len(r["scenarios"]) == 11 and set(r["code_sha256"]) == set(lt.CODE_FILES)
    assert r["scenarios"]["s11_fl_b_stochvol"]["binding_for"] == ["B"] and r["scenarios"]["s06_fl_d_event_label_ma10"]["binding_for"] == ["D"]
    for name in ("s06_fl_d_event_label_ma10", "s07_fl_b_abs_target", "s11_fl_b_stochvol"):
        a = r["scenarios"][name]["analytic_rates"]
        assert {"treated_0.0125", "treated_0.05", "plain_0.0125", "plain_0.05", "oversized", "limits"} <= set(a)
    assert "analytic_rates" not in r["scenarios"]["s01_fl_binary_iid"]
    # same seed, same code: identical result (one generator in table order; analytic rates draw nothing)
    r2 = la.size_check(worlds=2, draws=9, seed=11, spec=_sized_spec(), dev=True)
    assert {k: v["rate"] for k, v in r["scenarios"].items()} == {k: v["rate"] for k, v in r2["scenarios"].items()}


def test_analytic_rates_do_not_perturb_the_binding_generator():
    spec = _sized_spec()
    only = ["s06_fl_d_event_label_ma10", "s08_block_v_rho0"]
    a = la.size_check(worlds=2, draws=9, seed=3, only=only, spec=spec)
    # the same two scenarios after other scenarios would shift; instead check determinism of the analytic block itself
    b_ = la.size_check(worlds=2, draws=9, seed=3, only=only, spec=spec)
    assert a["scenarios"] == b_["scenarios"] and a["dev"] is True


def test_nonbinding_runs_use_their_own_seeds_and_do_not_touch_binding():
    spec = _sized_spec()
    out = la.nonbinding_runs(spec, draws=9, worlds=2, only=["s12", "power_d_0.5c", "power_b_1.0c"])
    assert out["s12_label_correlated_with_level"]["seed"] == 2026116712 and out["power_d_0.5c"]["seed"] == 2026116721 and out["power_b_1.0c"]["seed"] == 2026116724
    assert out["power_d_0.5c"]["effect"] == 0.005 and out["power_b_1.0c"]["effect"] == 0.01 and not out["power_d_0.5c"]["binding"]
    assert 0.0 <= out["power_d_0.5c"]["gate_power"] <= 1.0 and "analytic_power_treated_0.05" in out["power_b_1.0c"]
    assert {"rate_raw_target", "rate_both_demeaned"} <= set(out["s12_label_correlated_with_level"])
    # binding scenarios 1-11 draw from the one generator, in table order; the module has no other draw from the 20261167 stream
    src = (HERE / "live_tests6_analysis.py").read_text()
    assert len(re.findall(r"default_rng\(seed\)", src)) == 1 and not re.search(r"default_rng\(2026\d+\)", src)


def test_trial_record_counts_k_only():
    assert la.trial_record(3, "sha") == {"kind": "live_tests6", "n_tests": 3, "spec_sha256": "sha"}
    json.dumps(la.trial_record(2, None))


def test_size_check_refuses_while_k_tests_or_a_needed_stratum_is_null():
    with pytest.raises(ValueError, match="k_tests is null"):
        la.size_check(worlds=1, draws=3, seed=1, spec=lt.load_spec(sha=None), dev=True)
    spec = _sized_spec()
    spec["d"]["perm_stratum"] = None
    with pytest.raises(ValueError, match=r"perm_stratum is null for \['D'\]"):
        la.size_check(worlds=1, draws=3, seed=1, spec=spec, dev=True)
    spec["k_tests"] = ["V", "K", "B"]  # D dropped at the census: its null stratum no longer blocks, its scenario runs informationally on day
    assert la.size_strata(spec, spec["size_check"]["scenarios"])["s06_fl_d_event_label_ma10"] == "day"


def test_size_check_and_the_gate_use_identical_strata_for_the_same_spec(monkeypatch):
    """The LT4 defect: every FL scenario permuted within market x day while the registered gate used the census-fixed stratum."""
    spec = _sized_spec(strata=("block2", "block2", "block2"))
    seen = []
    real = la.fl_perm_gate

    def spy(df, y, term, controls, **kw):
        seen.append((df, kw["strata"], kw["min_stratum"], kw["draws"]))
        return real(df, y, term, controls, **kw)

    monkeypatch.setattr(la, "fl_perm_gate", spy)
    la.size_check(worlds=1, draws=5, seed=2, spec=spec, only=["s01_fl_binary_iid", "s06_fl_d_event_label_ma10"])
    assert len(seen) == 2
    for df, strata, min_s, _ in seen:
        want = la.strata_of(df, "block2", la.SIZE_T0)  # what gate_for computes for the same census-fixed stratum
        assert (strata == want).all() and min_s == spec["gates"]["perm_min_stratum"]
        assert len(set(strata)) < len(set(la.strata_of(df, "day", la.SIZE_T0)))  # not the day strata of the old code
    # gate_for itself routes through strata_of with the spec's stratum
    df = seen[0][0]
    y = np.random.default_rng(0).normal(size=len(df))
    gseen = []
    monkeypatch.setattr(la, "fl_perm_gate", lambda *a, **kw: gseen.append(kw["strata"]) or {"passes": False})
    d2 = df.assign(PL=(np.arange(len(df)) % 5 == 0).astype(float))
    la.gate_for("K", d2.rename(columns={"P": "CL"}), y, spec, la.SIZE_T0)
    assert (gseen[0] == la.strata_of(df, "block2", la.SIZE_T0)).all()


def test_load_size_check_verifies_the_pin_and_labels_flow_into_the_analysis(tmp_path):
    spec = _sized_spec()
    with pytest.raises(RuntimeError, match="null"):
        la.load_size_check(spec)
    res = {"dev": False, "worlds": 2000, "draws": 200, "seed": 20261167, "code_sha256": {"a": "1"}, "se_check_failed_size_scenario": ["K"], "scenarios": {}}
    p = tmp_path / "size.json"
    p.write_text(json.dumps(res))
    spec["size_check"].update(result_path=str(p), result_sha256=lt.sha256_file(p))
    spec["code_sha256"] = {"a": "1"}
    assert la.load_size_check(spec)["se_check_failed_size_scenario"] == ["K"]
    spec["size_check"]["result_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="!= pinned"):
        la.load_size_check(spec)
    spec["size_check"]["result_sha256"] = lt.sha256_file(p)
    spec["code_sha256"] = {"a": "2"}
    with pytest.raises(RuntimeError, match="pinned code"):
        la.load_size_check(spec)
    p.write_text(json.dumps({**res, "dev": True}))
    spec["size_check"]["result_sha256"], spec["code_sha256"] = lt.sha256_file(p), {"a": "1"}
    with pytest.raises(RuntimeError, match="dev run"):
        la.load_size_check(spec)
