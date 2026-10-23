# ruff: noqa: E501
"""LT11 size-check worlds: declared shapes, seeding, binding map, refusals, fail-closed per-test status (synthetic only)."""

import numpy as np
import pytest

from astrolabe.research_lab import live_tests11 as lt
from astrolabe.research_lab import live_tests11_worlds as W

SPEC = lt.load_spec(sha=None)


def test_limit_and_seed_constants():
    assert abs(W.limit_for(2000) - 0.058) < 5e-4
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
    d3, _ = W.generate("3", np.random.default_rng(2))
    assert "unknown" in set(d3["vclass"])
    d9, _ = W.generate("9", np.random.default_rng(3))
    assert set(d9["rew"]) == {0.0, 1.0} and (d9["absd"] >= 0.01 - 1e-9).all()


def test_worlds_are_deterministic_in_the_sub_seed():
    a = W.evaluate_world("9", 11, SPEC, stat="gate", draws=20, small=True)
    b = W.evaluate_world("9", 11, SPEC, stat="gate", draws=20, small=True)
    assert a == b


def test_planted_effect_is_detected_by_the_gate():
    hits = [W.evaluate_world("1", 50 + i, SPEC, stat="gate", draws=30, effect=0.5, small=True)["reject"] for i in range(4)]
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
