# ruff: noqa: E501
"""CB17 rules parts common / B / C / E (CREATIVE_BATCH_17.md sections 1.2-1.4, 2.3-2.6, CB17-B, CB17-C, CB17-E, 11): declarations and pure definitions; part pre unchanged; A withdrawn."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from astrolabe.research_lab import cb17_common as c17
from astrolabe.research_lab import cb17_pre as pre
from astrolabe.research_lab import cb17_rules_b as rb
from astrolabe.research_lab import cb17_rules_c as rc
from astrolabe.research_lab import cb17_rules_e as re_
from astrolabe.research_lab import cb17_wcommon as w

RULES = Path(__file__).resolve().parents[2] / "docs" / "research_lab" / "seals" / "cb17_rules.json"
PRE_SHA = "ddc0249b23eedf8cfe50b2b60e94378264804ca4791c82c01cf3993df54df6a7"


def ep(s: str) -> float:
    return c17.ep(s)


# ---- parts -------------------------------------------------------------------------------------------------------------------------------------------


def test_part_pre_hash_unchanged_by_later_parts():
    assert c17.rules_part_file_doc("pre")["rules_sha256"] == PRE_SHA


def test_parts_declared_and_a_withdrawn():
    for p in ("common", "B", "C", "E"):
        d = c17.rules_part_file_doc(p)
        assert d["part_declared"] is True and len(d["rules_sha256"]) == 64
    a = c17.rules_part_file_doc("A")
    assert a["part_declared"] is False and a["rules_sha256"] is None and "withdrawn uncounted (branch T)" in a["reason"]
    with pytest.raises(c17.Refused):
        c17.verify_rules(RULES, require_committed=False, part="A")


def test_parts_hash_their_own_modules_only():
    assert c17.rules_part_file_doc("common")["modules"] == ["cb17_common", "cb17_wcommon"]
    assert c17.rules_part_file_doc("B")["modules"] == ["cb17_common", "cb17_rules_b"]
    assert "cb17_rules_b.excursion_L" in c17.rules_part_file_doc("B")["func_sources_sha256"]
    assert "cb17_rules_b.excursion_L" not in c17.rules_part_file_doc("C")["func_sources_sha256"]
    assert "cb17_wcommon.arm" in c17.rules_part_file_doc("common")["func_sources_sha256"]


def test_rules_file_parts_verify():
    for p in ("pre", "common", "B", "C", "E"):
        assert c17.verify_rules(RULES, require_committed=False, part=p) == c17.rules_part_file_doc(p)["rules_sha256"]


def test_declared_docs_are_json():
    for mod in (w, rb, rc, re_):
        json.dumps(mod.declared(), sort_keys=True)


def test_pins_current():
    r = w.pins_ok()
    assert r["ok"], r["diverged"]
    from astrolabe.research_lab import cb16_common as c16
    assert {k: v for k, v in w.CB13_PINS.items() if k in c16.CB13_PINS} == c16.CB13_PINS


def test_branch_record_matches_pre_census_rule():
    rec = w.BRANCH_RECORD
    assert w.BRANCH == "T" and w.A_WITHDRAWN and rec["rule_pass"] is False
    assert round(pre.wilson_lower(rec["agreement_k"], rec["agreement_n"]), 6) == rec["wilson_lower"]
    assert w.K1 == 3 and w.K2_MAX == 6 and sum(len(v) for v in w.FAMILY_TESTS.values()) == 3


# ---- common: dates, arm, decision rules ---------------------------------------------------------------------------------------------------------------


def test_s8_rule_edges():
    assert w.s8_from_rules(ep("2026-10-24T12:00:00Z")) == ep("2026-10-26T00:00:00Z")
    assert w.s8_from_rules(ep("2026-10-25T00:00:00Z")) == ep("2026-10-26T00:00:00Z")
    assert w.s8_from_rules(ep("2026-10-25T00:00:01Z")) == ep("2026-10-27T00:00:00Z")
    assert w.s8_from_rules(ep("2026-10-19T00:00:00Z")) == ep("2026-10-26T00:00:00Z")


def test_windows_and_floor_clipping():
    s8 = ep("2026-10-26T00:00:00Z")
    W = w.windows8(s8)
    floor = ep(c17.LOOKBACK_FLOOR)
    assert W["screen"]["units"] == (s8, s8 + 14 * 86400)
    assert W["screen"]["sweeps"][0] == floor and W["screen"]["captures_bc"][0] == floor and W["screen"]["captures_e"][0] == floor
    assert W["screen"]["frame_not_before"] == s8 + 14 * 86400 + 8 * 3600
    assert W["rep"]["units"] == (s8 + 14 * 86400, s8 + 28 * 86400) and W["rep"]["read"][0] == s8 + 7 * 86400
    W2 = w.windows8(ep("2026-10-27T00:00:00Z"))
    assert W2["screen"]["sweeps"][0] == ep("2026-10-26T22:00:00Z") and W2["screen"]["captures_bc"][0] == ep("2026-10-26T18:00:00Z")


def test_lookback_floor_label():
    floor = ep(c17.LOOKBACK_FLOOR)
    assert w.lookback_available(floor) and not w.lookback_available(floor - 1) and not w.lookback_available(math.nan)
    for lead in (2, 3, 6):  # q0406 / q0407 lookbacks with S_8 = the floor
        assert not w.lookback_available(floor - lead * 3600)
    with pytest.raises(c17.Refused):
        w.guard_window_row(floor - 1)


def test_rep_units_refused_before_seal():
    s8 = ep("2026-10-26T00:00:00Z")
    t = s8 + 15 * 86400
    with pytest.raises(c17.Refused):
        w.guard_rep_unit(t, s8, rep_open=False)
    assert w.guard_rep_unit(t, s8, rep_open=True) == t
    assert w.guard_rep_unit(s8 + 86400, s8, rep_open=False) == s8 + 86400


def _arm_ref(e: str) -> int:
    return int(hashlib.sha256(("cb17-arm-v1|" + e).encode()).hexdigest()[0], 16) % 2


def test_arm_hash_deterministic_both_arms():
    ids = [str(i) for i in range(100, 140)]
    arms = [w.arm(e) for e in ids]
    assert arms == [_arm_ref(e) for e in ids] and set(arms) == {0, 1}
    assert w.arm("12345") == w.arm("12345")
    assert w.event_key("", "m1") == "m1" and w.event_key("e1", "m1") == "e1"
    with pytest.raises(c17.Refused):
        w.arm("")


def test_holm_k1_3_and_stage2():
    r = w.stage1_holm({"B1": 0.009})
    assert r["k1"] == 3 and set(r["tests"]) == {"B1", "B2", "C1"}
    assert w.stage1_advance(0.0099, True) and not w.stage1_advance(0.01, True) and not w.stage1_advance(0.001, False)
    with pytest.raises(c17.Refused):
        w.stage1_holm({"A1": 0.001})
    assert w.early_stage2_ok(0.05 / 8 - 1e-9) and not w.early_stage2_ok(0.05 / 8)
    assert w.stage2_final({"B1-rep": 0.01, "C1-econ": None})["k2"] == 2
    with pytest.raises(c17.Refused):
        w.stage2_final({"A2": 0.01})


def test_power_gate_edges():
    assert w.power_gate(0.263)["run"] is True
    g = w.power_gate(0.2632)
    assert g["run"] is False and g["label"] == w.NOT_RUN_POWER
    assert w.power_gate(None)["run"] is False and w.power_gate(math.nan)["run"] is False


def test_permutation_reach_boundaries():
    obs = 1.0
    perm = [0.0] * 197 + [1.0, 2.0, 1.5]
    assert w.permutation_reach(obs, perm)["holds"] and w.permutation_reach(obs, perm)["reach"] == 3
    assert not w.permutation_reach(obs, [0.0] * 196 + [1.0, 2.0, 1.5, 3.0])["holds"]
    assert w.permutation_reach(obs, [0.0] * 197 + [None, math.nan, 1.0])["holds"]  # 3 reach: an uncomputable draw reaches
    assert not w.permutation_reach(obs, [0.0] * 196 + [None, math.nan, 1.0, 1.0])["holds"]
    assert not w.permutation_reach(obs, [0.0] * 199)["holds"]  # 199 draws is not the declared 200
    assert w.permutation_reach(-1.0, [0.0] * 200, sign=-1.0)["reach"] == 0


def test_calibration_placebo_boundaries():
    ps = [0.5] * 197 + [0.001, 0.009, 0.0099]
    assert w.calibration_placebo(ps)["holds"]
    assert not w.calibration_placebo([0.5] * 196 + [0.001] * 4)["holds"]
    assert w.calibration_placebo([0.5] * 199 + [0.01])["advanced"] == 0
    assert w.calibration_placebo([None] * 200)["holds"]


def test_composition_guard_rules():
    perm_ok = {"holds": True}
    assert w.composition_guard(1.0, 0.5, 0.049, perm_ok, 0.5)["holds"]
    assert not w.composition_guard(1.0, 0.49, 0.001, perm_ok, 0.9)["holds"]
    assert not w.composition_guard(1.0, 0.8, 0.05, perm_ok, 0.9)["holds"]
    assert not w.composition_guard(1.0, 0.8, 0.01, {"holds": False}, 0.9)["holds"]
    r = w.composition_guard(1.0, 0.8, 0.01, perm_ok, 0.4999)
    assert not r["holds"] and r["label"] == w.UNINFORMATIVE
    assert not w.composition_guard(1.0, -0.8, 0.01, perm_ok, 0.9)["holds"]


def test_circular_shift_keeps_multiset_and_autocorrelation():
    rng = np.random.default_rng(17112)
    units = np.array([0] * 6 + [1] * 1 + [2] * 4)
    times = np.array([5, 1, 2, 3, 4, 6, 1, 4, 3, 2, 1], float)
    vals = np.array([1, 1, 1, 0, 0, 0, 7, 1, 0, 0, 1])
    out = w.circular_shift(vals, units, times, rng)
    assert out[6] == 7  # n < 2 left as it is
    for u in (0, 2):
        assert sorted(out[units == u]) == sorted(vals[units == u])
        order = np.argsort(times[units == u])
        a, b = vals[units == u][order], out[units == u][order]
        assert any(np.array_equal(np.roll(a, k), b) for k in range(1, len(a)))  # a non-zero circular rotation in time order
        assert not np.array_equal(a, b) or len(set(a)) == 1


def test_econ_decision_max_p_and_floors():
    r = w.econ_decision({"est": -0.6, "p": 0.001}, {"est": -1.2, "p": 0.02})
    assert r["p"] == 0.02 and r["floors_ok"]
    assert not w.econ_decision({"est": -0.4, "p": 0.001}, {"est": -1.2, "p": 0.001})["floors_ok"]
    assert not w.econ_decision({"est": -0.6, "p": 0.001}, {"est": -0.9, "p": 0.001})["floors_ok"]
    assert w.econ_decision({"est": -0.6, "p": None}, {"est": -1.2, "p": 0.001})["p"] == 1.0


# ---- B ------------------------------------------------------------------------------------------------------------------------------------------------


def test_b_cut_points_verbatim_and_float32():
    assert rb.ACTIVITY_CUTS_C == (0.0, 0.10000000149011612) and rb.IMBALANCE_CUTS == (-0.021718762814998627, 0.4006465971469879)
    assert rb.STRATA_LEVEL == {"B1": 2, "B2": 1}
    assert rb.f32(0.1) == rb.ACTIVITY_CUTS_C[1]
    assert rb.activity_tercile(0.0) == 0
    assert rb.activity_tercile(rb.activity_c(0.505, 0.504)) == 1 and rb.activity_tercile(rb.activity_c(0.506, 0.505)) == 1
    assert rb.activity_tercile(0.01) == 1 and rb.activity_tercile(0.2) == 2
    assert rb.imbalance_tercile(-0.021718762814998627) == 0 and rb.imbalance_tercile(-0.0217) == 1
    assert rb.imbalance_tercile(0.4006465971469879) == 1 and rb.imbalance_tercile(0.41) == 2


def test_b_age_edges():
    assert rb.book_age_s(1000.0, 995_000.0) == 5.0
    assert rb.age_state(-5.0001) == rb.STATE_ANOMALY and rb.age_state(-5.0) == rb.STATE_FRESH and rb.age_state(math.nan) == rb.STATE_ANOMALY
    assert rb.age_state(59.999) == rb.STATE_FRESH and rb.age_state(60.0) == rb.STATE_MID
    assert rb.age_state(599.9) == rb.STATE_MID and rb.age_state(600.0) == rb.STATE_OLD
    assert rb.age_state(300.0, old_cut_s=300.0) == rb.STATE_OLD and rb.age_state(1799.0, old_cut_s=1800.0) == rb.STATE_MID


def test_b_excursion():
    assert rb.excursion_L(0.48, 0.52, 0.50) == 0.0
    assert math.isclose(rb.excursion_L(0.48, 0.52, 0.55), 3.0)
    assert math.isclose(rb.excursion_L(0.48, 0.52, 0.46), 2.0)
    assert math.isnan(rb.excursion_L(0.48, 0.52, math.nan))


def _sw(bid="0.48", ask="0.52", db1=10.0, db5=50.0, da1=10.0, da5=50.0):
    return {"bid_s": bid, "ask_s": ask, "db1": db1, "db5": db5, "da1": da1, "da5": da5}


def test_b_shift_state():
    assert rb.shift_state(_sw(), _sw(ask="0.53")) is None  # touch change -> not a unit
    z = rb.shift_state(_sw(), _sw())
    assert z["s"] == 0 and z["x"] == 0.0 and z["ok"]  # s = 0 kept
    up = rb.shift_state(_sw(), _sw(da5=40.0))  # mass leaves the ask side beneath the touch -> x > 0 (up move predicted)
    assert up["s"] == -10.0 and math.isclose(up["x"], 0.1) and math.isclose(up["imb"], (50.0 - 40.0) / 100.0)
    dn = rb.shift_state(_sw(), _sw(db5=40.0))
    assert dn["x"] < 0
    assert rb.shift_state(_sw(), _sw(da5=-1000.0))["x"] == 1.0  # clipped
    assert rb.shift_state(_sw(db5=0.0, da5=0.0, db1=0.0, da1=0.0), _sw())["ok"] is False


def test_b_mark_status():
    dec = {"tick": 0.01}
    assert rb.mark_status(dec, None) == rb.NO_MARK
    assert rb.mark_status(dec, {"two_sided": False, "bid": 0.4, "ask": 0.5, "tick": 0.01}) == rb.NO_MARK
    assert rb.mark_status(dec, {"two_sided": True, "bid": 0.4, "ask": 0.51, "tick": 0.01}) == rb.WIDE_MARK
    assert rb.mark_status(dec, {"two_sided": True, "bid": 0.4, "ask": 0.45, "tick": 0.001}) == rb.TICK_CHANGE
    assert rb.mark_status(dec, {"two_sided": True, "bid": 0.4, "ask": 0.45, "tick": 0.01}) == rb.MARK_OK


def test_b_worst_cases():
    fresh_L = np.arange(101, dtype=float)
    assert rb.worst_b1(True, fresh_L) == 0.0 and rb.worst_b1(False, fresh_L) == 95.0
    dm = np.arange(-50, 51, dtype=float)
    assert rb.worst_b2(0.0, dm) == 0.0 and rb.worst_b2(0.3, dm) == -45.0 and rb.worst_b2(-0.3, dm) == 45.0


def test_b_gates():
    assert rb.gate_gbt(100, 99, 100, 95)["pass"] and not rb.gate_gbt(100, 98, 100, 95)["pass"] and not rb.gate_gbt(100, 99, 100, 94)["pass"]
    assert rb.gate_gba(50, 50, 1000, 1000, 300)["pass"] and not rb.gate_gba(49, 50, 1000, 1000, 300)["pass"] and not rb.gate_gba(50, 50, 1000, 999, 300)["pass"]
    assert not rb.gate_gba(50, 50, 1000, 1000, 299)["pass"]
    assert rb.gate_gbs(250000, 50000, 300)["pass"] and not rb.gate_gbs(250001, 50000, 300)["pass"] and not rb.gate_gbs(100000, 49999, 300)["pass"]


def test_b_concentration_and_econ_flags():
    x = np.array([1.0] * 10 + [0.1] * 10)
    ev = np.array([str(i) for i in range(10)] + ["z"] * 10)
    assert math.isclose(rb.concentration_share(x, ev), 5.0 / 10.1)
    assert rb.econ_b1_bin(700.0) == rb.STATE_OLD and rb.econ_b1_bin(10.0) == rb.STATE_FRESH and rb.econ_b1_bin(100.0) is None
    assert rb.econ_b2_abandoned(0.2, 0.1, -1) is True and rb.econ_b2_abandoned(0.2, 0.1, 1) is False
    assert rb.econ_b2_abandoned(-0.2, 0.1, 1) is True and rb.econ_b2_abandoned(0.05, 0.1, -1) is None


def test_b_strata_at_selected_levels():
    u = {"ts": ep("2026-10-27T13:00:00Z"), "spread": 0.03, "act": 1, "reward": 1, "imb": 2}
    assert rb.stratum_b("B1", u) == (1,) and rb.stratum_b("B2", u) == (1, 2)


# ---- C ------------------------------------------------------------------------------------------------------------------------------------------------


def test_c_interval_and_r():
    assert not rc.interval_ok(99 * 60.0) and rc.interval_ok(100 * 60.0) and rc.interval_ok(140 * 60.0) and not rc.interval_ok(140 * 60.0 + 1)
    assert rc.r_state(10.0, 12.0, 100.0, 100.0) is None  # dV = 0: not traded
    assert rc.r_state(10.0, 12.0, 100.0, 104.0) == (0.5, 4.0)
    assert rc.r_state(math.nan, 12.0, 100.0, 104.0) is None


def test_c_trailing_classes_prior_only():
    prior5 = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert rc.classify(0.3, prior5) is None  # 5 prior -> thin history
    prior6 = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    lo, hi = pre.trailing_cuts(prior6)
    assert rc.classify(hi + 1e-6, prior6) == rc.CLASS_MINT and rc.classify(lo - 1e-6, prior6) == rc.CLASS_MERGE and rc.classify(lo, prior6) == rc.CLASS_TRANSFER
    assert rc.classify(100.0, prior6) == rc.CLASS_MINT and pre.trailing_cuts(prior6) == (lo, hi)  # r_k never enters its own cut points


def test_c_moves_continuation_and_marks():
    mv = rc.qualifying_moves(["a", "b", "c"], {"a": 0.50, "b": 0.50, "c": 0.5}, {"a": 0.505, "b": 0.5049, "c": math.nan})
    assert [m for m, _ in mv] == ["a"]
    assert math.isclose(rc.continuation(0.5, 0.505, 0.515), 1.0) and math.isclose(rc.continuation(-0.5, 0.495, 0.485), 1.0)
    assert math.isnan(rc.member_mid(0.40, 0.51)) and math.isnan(rc.member_mid(0.01, 0.03)) and math.isclose(rc.member_mid(0.40, 0.42), 0.41)
    assert rc.mark_reason(False, None) == "capture missing"
    assert rc.mark_reason(True, {"bid": 0.4, "ask": 0.42, "closed": True}) == "member closed"
    assert rc.mark_reason(True, {"bid": math.nan, "ask": 0.42, "closed": False}) == "one-sided"
    assert rc.mark_reason(True, {"bid": 0.30, "ask": 0.42, "closed": False}) == "wide"
    assert rc.mark_reason(True, {"bid": 0.97, "ask": 0.99, "closed": False}) == "extreme mid"
    assert rc.mark_reason(True, {"bid": 0.40, "ask": 0.42, "closed": False}) is None


def test_c_worst_member_and_robustness():
    C = np.arange(-50, 51, dtype=float)
    assert rc.worst_member(rc.CLASS_TRANSFER, C) == -45.0 and rc.worst_member(rc.CLASS_MINT, C) == 45.0 and rc.worst_member(rc.CLASS_MERGE, C) == 45.0
    assert rc.worst_member(rc.CLASS_TRANSFER, C, -60.0) == -60.0 and rc.worst_member(rc.CLASS_TRANSFER, C, 0.0) == -45.0
    v = rc.onesided_adverse(1.0, 0.50, {"bid": 0.48, "ask": math.nan})
    assert math.isclose(v, -2.0)
    assert rc.whole_window_class(0.3, [0.1] * 5) is None and rc.whole_window_class(0.9, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]) == rc.CLASS_MINT
    assert math.isclose(rc.r_lag(10.0, 12.0, 100.0, 104.0), 0.5) and math.isnan(rc.r_lag(10.0, 12.0, 100.0, 100.0))


def test_c_gates_and_level():
    assert rc.STRATA_LEVEL_C == 2
    assert rc.gate_gcu(70, 100)["pass"] and not rc.gate_gcu(69, 100)["pass"]
    assert rc.gate_gc(600, 10000)["pass"] and not rc.gate_gc(599, 10000)["pass"] and not rc.gate_gc(600, 9999)["pass"]
    u = {"ts": ep("2026-10-27T13:00:00Z"), "dv_tercile": 0, "dv_above": 0, "n_moving": 1}
    assert rc.stratum_c({**u, "abs_dm_c": 0.9}) == (0,) and rc.stratum_c({**u, "abs_dm_c": 1.0}) == (0,) and rc.stratum_c({**u, "abs_dm_c": 1.01}) == (1,)


# ---- E ------------------------------------------------------------------------------------------------------------------------------------------------


def test_e_age_groups_and_reentry():
    assert re_.age_group(0.0) == "first" and re_.age_group(23.99) == "first" and re_.age_group(24.0) == "later" and re_.age_group(167.9) == "later"
    assert re_.age_group(168.0) is None and re_.age_group(-1.0) is None and re_.age_group(math.nan) is None
    assert re_.reentry_verdict(400, 150, 1.0)["pass"]
    assert not re_.reentry_verdict(399, 150, 0.5)["pass"] and not re_.reentry_verdict(400, 149, 0.5)["pass"]
    assert not re_.reentry_verdict(400, 150, 1.0001)["pass"] and not re_.reentry_verdict(400, 150, None)["pass"]
    assert re_.reentry_verdict(10, 1, 0.1)["verdict"] == re_.VERDICT_DENIED
