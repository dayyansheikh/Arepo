# ruff: noqa: E501
"""LT11 size-check worlds: declared shapes, seeding, binding map, refusals, fail-closed per-test status (synthetic only)."""

import numpy as np
import pytest

from astrolabe.research_lab import live_tests11 as lt
from astrolabe.research_lab import live_tests11_worlds as W

SPEC = lt.load_spec(sha=None)


def test_limit_and_seed_constants():
    assert W.limit_for(2000) == 0.058 == SPEC["size_check"]["limit"]  # the frozen value (1.8), not the formula's 0.058017
    assert abs(W.limit_for(2) - (0.05 + 1.645 * (0.0475 / 2) ** 0.5)) < 1e-12
    assert W.REGISTERED_SEED == 20261497 == SPEC["seeds"]["size_check"]
    assert W.DEV_SEED == 20261497 * 100 + 99
    assert W.POWER["CH234"][2] == 41 and W.POWER["CH232"][2] == 43


def test_scenario_map_matches_spec_binding():
    assert list(W.SCENARIO_ORDER) == SPEC["size_check"]["scenarios"]
    bind = SPEC["size_check"]["binding_scenarios"]
    for t, scs in bind.items():
        assert sorted(s for s in W.SCENARIO_ORDER if W.SCENARIOS[s]["test"] == t) == sorted(scs)
    assert {s for s in W.SCENARIOS if W.SCENARIOS[s]["stat"] == "verdict"} == {"12", "13", "14"}


def test_registered_seed_refused_on_development_runs():
    with pytest.raises(W.Refused):
        W.size_check(worlds=2, draws=2, seed=W.REGISTERED_SEED, spec=SPEC, tests=["CH232"], scenarios=("9",), small=True)
    with pytest.raises(W.Refused):
        W.size_check(worlds=2, draws=2, seed=W.DEV_SEED, spec=SPEC, scenarios=("99",), small=True)


def test_world_shapes():
    rng = np.random.default_rng(1)
    d5, _ = W.generate("5", rng)
    per_event = d5.groupby("event_id")["market_id"].nunique()
    assert per_event.min() >= 3 and per_event.max() <= 10 and d5["event_id"].nunique() == 200
    d13, _ = W.generate("13", np.random.default_rng(1))
    assert len(d13) > len(d5)  # worlds 5-8 drop 10% of member units, world 13 does not
    d1, _ = W.generate("1", np.random.default_rng(2))
    assert d1["market_id"].nunique() <= 400 and set(d1["vclass"]) == {"traded", "quote_only"}
    d3, _ = W.generate("3", np.random.default_rng(2), q=0.2)
    assert "unknown" in set(d3["vclass"])
    d9, _ = W.generate("9", np.random.default_rng(3))
    assert set(d9["rew"]) == {0.0, 1.0} and (d9["absd"] >= 0.01 - 1e-9).all()


def test_worlds_are_deterministic_in_the_sub_seed():
    a = W.evaluate_world("9", 11, SPEC, stat="gate", draws=20, small=True)
    b = W.evaluate_world("9", 11, SPEC, stat="gate", draws=20, small=True)
    assert a == b


def test_planted_effect_is_detected_by_the_gate():
    hits = [W.evaluate_world("1", 50 + i, SPEC, stat="gate", draws=30, effect=2.0, small=True)["reject"] for i in range(4)]  # mechanics only: a large planted effect (cents per tercile gap) is found
    assert sum(hits) >= 3


def test_size_check_fail_closed_status():
    out = W.size_check(worlds=2, draws=5, seed=W.DEV_SEED, spec=SPEC, tests=["CH232"], scenarios=("9", "10"), small=True)
    assert out["limit"] == W.limit_for(2) and out["seed_kind"] == "development"
    # scenarios 11, 14, 15 were not run: missing statistics fail the test closed
    out2 = W.size_check(worlds=2, draws=5, seed=W.REGISTERED_SEED, spec=SPEC, tests=["CH232"], scenarios=("9", "10"), small=True, registered=True)
    assert out2["per_test"]["CH232"]["status"] == "fail_size_scenario" and set(out2["per_test"]["CH232"]["missing"]) == {"11", "14", "15"}


def test_verdict_scenarios_run_f_and_point_condition():
    r = W.evaluate_world("12", 5, SPEC, stat="verdict", draws=5, small=True)
    assert {"p_analytic", "f_holds", "point_holds", "reject"} <= set(r)


# --- review 2026-10-23 fixes (LT11_CODE_FREEZE_CHECK) -------------------------------------------------------------------------------------------


def _corr(a, b):
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])


def test_world1_state_is_the_declared_collateral_weight():
    """MUST-FIX 1: w = 0.5 + sign(d)(p_{k-1} - 0.5), |d| winsorised at 0.20, xw = z(w) z(|d|) on the traded units' centres and scales (2.4)."""
    d, _ = W.generate("1", np.random.default_rng(4))
    assert np.allclose(d["w"], 0.5 + d["sgn"] * (d["p_k"] - 0.5))
    assert d["absd"].max() <= 0.20 + 1e-12 and np.allclose(d["absd"], np.minimum(np.abs(d["d"]), 0.20))
    tr = d["vclass"] == "traded"
    zw = (d["w"] - d.loc[tr, "w"].mean()) / d.loc[tr, "w"].std(ddof=1)
    za = (d["absd"] - d.loc[tr, "absd"].mean()) / d.loc[tr, "absd"].std(ddof=1)
    assert np.allclose(d["xw"], zw * za)
    # the bins span w: sign(d) x bin and its level term reproduce w - 0.5 exactly (w's main effect is held fixed by the controls)
    X = d[["sb0", "sb1", "sb2", "sb3", "sb0_lvl", "sb1_lvl", "sb2_lvl", "sb3_lvl"]].to_numpy(float)
    coef, *_ = np.linalg.lstsq(X, d["w"].to_numpy(float) - 0.5, rcond=None)
    assert np.allclose(X @ coef, d["w"] - 0.5, atol=1e-9)
    # traded independent of everything (probability 0.35); the level drift reaches continuation through w's level, not through traded
    assert abs(tr.mean() - 0.35) < 0.02 and abs(_corr(tr, d["w"])) < 0.03
    # the twin uses the same formula on (k + 2, k + 3], w = 0.5 where that move is 0
    assert ((d["absd_tw"] == 0) <= (d["w_tw"] == 0.5)).all()
    assert d["w"].std() > 0.2  # w varies with the price level (it was a uniform draw on traded units only before the fix)


def test_world3_needs_the_census_q_and_refuses_none():
    """MUST-FIX 2: worlds 3 / 3b read q = census_fixed.CH234.q_unknown (floor 0.15); None refuses."""
    for w in ("3", "3b"):
        with pytest.raises(W.Refused):
            W.generate(w, np.random.default_rng(1), small=True)
    lo, _ = W.generate("3", np.random.default_rng(5), q=0.05)  # floored to 0.15
    fl, _ = W.generate("3", np.random.default_rng(5), q=0.15)
    assert (lo["vclass"] == fl["vclass"]).all()
    hi, _ = W.generate("3", np.random.default_rng(5), q=0.40)
    assert (hi["vclass"] == "unknown").mean() > (fl["vclass"] == "unknown").mean()
    with pytest.raises(W.Refused):
        W.world_q({"census_fixed": {"CH234": {"q_unknown": None}}}, dev=False)
    assert W.world_q({"census_fixed": {"CH234": {"q_unknown": 0.31}}}, dev=False)[0] == 0.31
    assert W.world_q({"census_fixed": {"CH234": {"q_unknown": 0.1}}}, dev=False)[0] == 0.15
    assert W.world_q({"census_fixed": {"CH234": {"q_unknown": None}}}, dev=True)[0] == W.DEV_Q


def test_census_fixed_refusal_on_any_none_or_nan():
    """MUST-FIX 3: the registered size check refuses on any None / NaN census-fixed value (the old check was disabled)."""
    assert W.census_fixed_error(SPEC, ["CH234"]) is not None  # the DRAFT spec: every value null
    full = {"CH234": {"w_centre": 0.5, "w_scale": 0.2, "absd_centre": 0.02, "absd_scale": 0.01, "xw_cuts": [-0.3, 0.3], "xw_gap": 2.2, "exclude_family": "", "q_unknown": 0.2},
            "CH233": {"s_c": {"3-5": 1.0, "6-10": 1.2}, "zcl_cuts": [-0.4, 0.4], "zcl_gap": 2.0, "exclude_family": "fam"}}
    assert W.census_fixed_error({"census_fixed": full}, ["CH234", "CH233"]) is None
    for t, k, v in (("CH234", "q_unknown", None), ("CH234", "xw_gap", float("nan")), ("CH233", "s_c", {"3-5": 1.0, "6-10": None}), ("CH234", "xw_cuts", [0.1, None])):
        bad = {**full, t: {**full[t], k: v}}
        assert W.census_fixed_error({"census_fixed": bad}, [t]) is not None
    assert W.census_fixed_error({"census_fixed": full}, ["CH232"]) is not None  # missing block


def test_world3b_is_world3_with_capture_level_missingness():
    """MUST-FIX 4: row-level a (0.3c x a continuation, logistic(-0.6 + 0.8 a) trading), A_t, capture-level missingness, control a + A_t + noise, slot dummies."""
    d, _ = W.generate("3b", np.random.default_rng(6), q=0.25)
    unk = (d["vclass"] == "unknown").astype(float)
    per_slot = unk.groupby(d["slot"]).mean()
    assert set(np.round(per_slot.unique(), 9)) <= {0.0, 1.0} and 0 < per_slot.mean() < 1  # whole captures lose volume_num together
    assert d["lat_a"].std() > 0.5 and d["lat_A"].std() > 0.3
    assert _corr(d["log1p_vol"], d["lat_a"] + d["lat_A"]) > 0.8
    known = d[unk == 0]
    assert _corr(known["traded"], known["lat_a"]) > 0.1  # trading rises with a
    assert _corr(d["y"], d["lat_a"]) > 0.02 and _corr(d["y"], d["lat_A"]) > 0.0
    assert {f"sd{s}" for s in range(1, 12)} <= set(W._controls("CH234", "3b", d))
    assert "sd1" not in W._controls("CH234", "1", d)
    # missingness falls with the market-wide latent
    assert _corr(per_slot.to_numpy(), d.groupby("slot")["lat_A"].first().to_numpy()) < 0
    d3, _ = W.generate("3", np.random.default_rng(6), q=0.25)
    assert d3["lat_A"].abs().max() == 0 and _corr(d3["log1p_vol"], d3["lat_a"]) > 0.8
    ps3 = (d3["vclass"] == "unknown").groupby(d3["slot"]).mean()
    assert ((ps3 > 0) & (ps3 < 1)).any()  # world 3 is row-level


def test_mq_worlds_load_the_drift_on_lead_and_twin():
    """MUST-FIX 5: worlds 12-14 apply loading 0.3 per SD of the drift on the lead state and the twin; world 12 has no 0.3a term."""
    d12, _ = W.generate("12", np.random.default_rng(7))
    assert 0.2 < _corr(d12["xw"], d12["lat_mu_k"]) < 0.4 and 0.2 < _corr(d12["xw_tw"], d12["lat_mu_tw"]) < 0.4
    assert d12["lat_a"].abs().max() == 0 and d12["lat_mu_k"].std() == pytest.approx(0.5, rel=0.35)
    d13, _ = W.generate("13", np.random.default_rng(7))
    assert 0.2 < _corr(d13["zcl"], d13["lat_mu_k"]) < 0.4 and 0.2 < _corr(d13["zcl_tw"], d13["lat_mu_tw"]) < 0.4
    d14, _ = W.generate("14", np.random.default_rng(7))
    r = d14[d14["rew"] == 1]
    hi, lo = r["lat_mu_k"] > r["lat_mu_k"].quantile(2 / 3), r["lat_mu_k"] < r["lat_mu_k"].quantile(1 / 3)
    assert r.loc[hi, "xo"].mean() > r.loc[lo, "xo"].mean() and r.loc[hi, "xo_tw"].mean() > r.loc[lo, "xo_tw"].mean()
    assert d14.loc[d14["rew"] == 0, "lat_mu_k"].abs().max() == 0  # reward-panel markets only
    for w in ("1", "3"):
        d, _ = W.generate(w, np.random.default_rng(7), q=0.2)
        assert d["lat_mu_k"].abs().max() == 0


def test_world6_and_world8_shapes():
    """SHOULD-FIX 7: world 6 longshot spreads a reflected AR(0.8) around 3c; world 8 scales the bid-change VARIANCE by exp(0.5 L_e)."""
    d6, _ = W.generate("6", np.random.default_rng(8))
    ls = d6[~d6["market_id"].str.endswith("-0")]
    assert ls["spread_k_c"].min() >= 1 and abs(ls["spread_k_c"].mean() - 3.0) < 0.5
    x = ls.sort_values(["market_id", "slot"])
    lag = x.groupby("market_id")["spread_k_c"].shift(1)
    assert _corr(x["spread_k_c"][lag.notna()], lag[lag.notna()]) > 0.6
    assert np.allclose(W.reflect(np.array([0.5, 1.5, 41.0]), 1.0, 40.0), [1.5, 1.5, 39.0])
    d8, _ = W.generate("8", np.random.default_rng(8))
    g = d8.groupby("event_id").agg(v=("own_dbid_c", "var"), le=("lat_Le", "first"))
    slope = np.polyfit(g["le"], np.log(g["v"]), 1)[0]
    assert 0.3 < slope < 0.7  # log variance rises 0.5 per unit of L_e (the old code scaled the SD by exp(0.5 L_e): slope 1.0)


def test_power_effect_is_per_tercile_gap():
    """SHOULD-FIX 9: the power runs plant ``effect`` cents per tercile gap of the tested term on the traded units."""
    a, _ = W.generate("1", np.random.default_rng(9), small=True)
    e, _ = W.generate("1", np.random.default_rng(9), small=True, effect=0.5)
    tr = (a["vclass"] == "traded").to_numpy()
    from astrolabe.research_lab import live_tests11_base as b_

    gap = b_.terciles(a["xw"].to_numpy(float)[tr])[2]
    assert np.allclose((e["y"] - a["y"])[tr], 0.5 * a["xw"][tr] / gap) and np.allclose((e["y"] - a["y"])[~tr], 0.0)


def test_size_timing_writes_the_clock_only(monkeypatch):
    """SHOULD-FIX 10: size-timing runs every scenario at a timing seed and writes only wall-clock seconds, the projection and hashes: no rejection, rate,
    p-value or status anywhere in the output."""
    seen = []

    def fake(world, sub, spec, *, stat, draws, small=False, q=None, effect=0.0):
        seen.append((world, stat, draws))
        return {"reject": True, "rate": 1.0, "p_analytic": 0.0}

    monkeypatch.setattr(W, "evaluate_world", fake)
    t = iter(range(10_000))
    out = W.size_timing(spec=SPEC, worlds=3, draws=7, clock=lambda: float(next(t)))
    assert [s for s, _, _ in seen[::3]] == list(W.SCENARIO_ORDER) and len(seen) == 48 and {d for _, _, d in seen} == {7}
    assert set(out) <= W.TIMING_KEYS and set(out["seconds_per_world"]) == set(W.SCENARIO_ORDER)
    txt = __import__("json").dumps(out).lower()
    for bad in ("reject", "rate", "p_analytic", "power\"", "status", "holds", "pass"):
        assert bad not in txt, bad
    pr = out["projection"]
    assert pr["worlds"] == 2000 and pr["draws"] == 200 and pr["power_worlds"] == 500
    assert pr["total_seconds"] == pytest.approx(sum(pr["seconds_by_scenario"].values()) + pr["power_run_seconds"])
    assert pr["seconds_by_scenario"]["1"] == pytest.approx(out["seconds_per_world"]["1"] * 2000 * 200 / 7)
    for s in (W.REGISTERED_SEED, W.DEV_SEED):
        with pytest.raises(W.Refused):
            W.size_timing(spec=SPEC, worlds=1, draws=1, seed=s)
    assert W.TIMING_SEED not in (W.REGISTERED_SEED, W.DEV_SEED)
