# ruff: noqa: E501
"""LT12 single analysis (LIVE_TESTS_12.md 1.7-1.11), synthetic only: the refusals (date, pin, design text, code hashes, registration slots), the Holm
p = 1 rules, the verdict rules of 1.9 (Supported / Inconclusive with its labels / Contradicted / Unavailable), the F rule, the binding point conditions
(CH245's dense twin on BOTH sets with the 5,000-unit floor, re-check fix 7, and the two-sided placebo; CH244's low-liquidity twin), the labels (CH244's
certain 'informed (E022)'), the trials line, and one reader -> analysis integration run on a synthetic tree (forced, unregistered roles)."""

from __future__ import annotations

import copy

import numpy as np
import pytest

from astrolabe.research_lab import live_tests12 as lt
from astrolabe.research_lab import live_tests12_analysis as an
from astrolabe.research_lab import live_tests12_worlds as W
from tests import lt12_synth as sy

SEED = 7_310_001  # a test seed (never the registered size-check seed or a declared derivative)


def _spec() -> dict:
    return lt.load_spec(sha=None)


def test_preconditions_refuse_before_the_date_unpinned_and_a_changed_design(monkeypatch):
    spec = _spec()
    with pytest.raises(an.Refused, match="on or after"):
        an.preconditions(spec, lt.epoch("2027-01-01T11:59:59Z"))
    with pytest.raises(an.Refused, match="unpinned"):
        an.preconditions(spec, lt.epoch("2027-01-02T00:00:00Z"))
    monkeypatch.setattr(lt, "design_text_error", lambda path=None: {"error": "LIVE_TESTS_12.md differs"})
    with pytest.raises(an.Refused, match="differs"):
        an.preconditions(spec, lt.epoch("2027-01-02T00:00:00Z"), force=True)


def test_analyze_refuses_before_the_analysis_date(tmp_path):
    with pytest.raises(an.Refused):
        an.analyze(tmp_path, spec=_spec(), now=lt.epoch("2026-12-31T00:00:00Z"))


def test_code_check_refuses_a_pinned_spec_without_matching_pins():
    spec = copy.deepcopy(_spec())
    assert an.code_check(spec)["label"] == "DRAFT: code hashes not verified"
    spec["_pinned"] = True
    with pytest.raises(an.Refused, match="pins"):
        an.code_check(spec)
    spec["code_sha256"] = lt.code_hashes()
    with pytest.raises(an.Refused, match="k_tests"):
        an.code_check(spec)  # registration_error: null k_tests (and null informed_labels behind it)


def _pinned_census(k, dropped, unav) -> dict:
    spec = copy.deepcopy(_spec())
    spec["_pinned"], spec["code_sha256"] = True, lt.code_hashes()
    spec["k_tests"], spec["dropped_tests"], spec["census_unavailable"] = k, dropped, unav
    spec["census_fixed"]["CH245"] = {"s_D": 1.2, "s_T": 1.1, "s_w": 0.9, "zs_cuts": [-0.4, 0.4], "zs_gap": 1.5, "rgap_q50_s": 6.0, "rgap_q90_s": 20.0, "exclude_family": "",
                                     "rho_census": 0.5, "rho_census_nan": False}
    spec["census_fixed"]["CH244"] = {"world9_corr": -0.1, "shock_size_scale": 2.0, "exclude_family": ""}
    spec["census_gate_values"] = {"CH245": {"mde_c": 0.5}, "CH244": {"mde_c": 0.7}}
    spec["informed_labels"] = {"CH245": [], "CH244": []}
    spec["size_check_result"] = {t: {"status": "pass"} for t in k}
    return spec


def test_code_check_refuses_a_test_in_none_or_two_census_lists():
    """Code-freeze check fix 5: every test in exactly one of k_tests, dropped_tests, census_unavailable."""
    assert an.code_check(_pinned_census(["CH245", "CH244"], [], []))["status"]
    assert an.code_check(_pinned_census(["CH245"], ["CH244"], []))["status"]
    assert an.code_check(_pinned_census(["CH245"], [], ["CH244"]))["status"]
    with pytest.raises(an.Refused, match="exactly one"):
        an.code_check(_pinned_census(["CH245"], [], []))  # CH244 in none of the three
    with pytest.raises(an.Refused, match="exactly one"):
        an.code_check(_pinned_census(["CH245", "CH244"], [], ["CH244"]))  # in k and census_unavailable
    with pytest.raises(an.Refused, match="exactly one"):
        an.code_check(_pinned_census(["CH245"], ["CH244"], ["CH244"]))  # dropped and unavailable
    with pytest.raises(an.Refused, match="dropped"):
        an.code_check(_pinned_census(["CH245", "CH244"], ["CH244"], []))
    with pytest.raises(an.Refused, match="unknown"):
        an.code_check(_pinned_census(["CH245", "CH244"], ["CH243"], []))


def test_census_state_is_printed_from_the_spec_lists():
    sp = _pinned_census(["CH245"], [], ["CH244"])
    assert an.census_state(sp, "CH245") == "k" and an.census_state(sp, "CH244") == lt.CENSUS_UNAVAILABLE
    sp = _pinned_census(["CH245"], ["CH244"], [])
    assert an.census_state(sp, "CH244") == lt.CENSUS_DROPPED
    assert an.census_state(_spec(), "CH244") is None
    assert an.NOT_IN_K[lt.CENSUS_UNAVAILABLE].startswith("census_unavailable (coverage)") and "ordered lane" in an.NOT_IN_K[lt.CENSUS_UNAVAILABLE]
    assert an.NOT_IN_K[lt.CENSUS_DROPPED].startswith("census_dropped") and an.NOT_IN_K[lt.CENSUS_UNAVAILABLE] != an.NOT_IN_K[lt.CENSUS_DROPPED]


def _r(beta=1.0, p=0.001, ci=(0.2, 2.0), gate=True, f=(True, True), pc=True, test="CH245", ge2_available=True, placebo=True):
    r = {"available": True, "primary": {"testable": True, "beta": beta, "p": p, "ci95_cons": list(ci)}, "gate": {"passes": gate}, "f": {"available": f[0], "holds": f[1]}, "size_note": None}
    if test == "CH245":
        dt_holds = bool(pc and ge2_available)  # as point_conditions: an unavailable >= 2 ticks set cannot hold
        r["point_condition"] = {"holds": bool(dt_holds and placebo), "dense_twin": {"holds": dt_holds, "ge2_ticks": {"available": ge2_available}}, "placebo": {"holds": placebo}}
    else:
        r["point_condition"] = {"holds": pc}
    return r


def test_verdict_rules():
    assert an.verdict(_r(), 0.01, "CH245")["verdict"] == "Supported"
    v = an.verdict(_r(f=(True, False)), 0.01, "CH245")
    assert v["verdict"] == "Inconclusive" and "mechanical null not excluded" in v["labels"]
    assert "falsification unavailable" in an.verdict(_r(f=(False, False)), 0.01, "CH245")["labels"]
    v = an.verdict(_r(pc=False), 0.01, "CH245")
    assert v["verdict"] == "Inconclusive" and "not thin-specific" in v["labels"]
    v = an.verdict(_r(ge2_available=False), 0.01, "CH245")
    assert v["verdict"] == "Inconclusive" and "dense-twin unavailable" in v["labels"]  # re-check fix 7: at most Inconclusive
    v = an.verdict(_r(placebo=False), 0.01, "CH245")
    assert v["verdict"] == "Inconclusive" and "placebo not null" in v["labels"]
    assert "not status-specific" in an.verdict(_r(pc=False, test="CH244"), 0.01, "CH244")["labels"]
    assert an.verdict(_r(), 0.20, "CH245")["verdict"] == "Inconclusive"  # Holm-adjusted p not below 0.05
    assert an.verdict(_r(beta=-1.0, ci=(-2.0, -0.1)), 0.9, "CH245")["verdict"] == "Contradicted"
    assert an.verdict({"available": False, "unavailable_reason": "fewer than 20000 thin units"}, 1.0, "CH245")["verdict"] == "Unavailable"


def test_holm_p_is_one_for_a_failed_gate_a_failed_size_scenario_or_unavailable():
    assert an.p_for_holm(_r(gate=False)) == (1.0, an.GATE_LABEL)
    r = _r()
    r["size_note"] = an.SIZE_LABEL
    assert an.p_for_holm(r) == (1.0, an.SIZE_LABEL)
    assert an.p_for_holm({"available": False}) == (1.0, None)
    assert an.p_for_holm(_r(p=0.003)) == (0.003, None)
    v = an.verdict(_r(gate=False), 1.0, "CH245")
    assert v["verdict"] == "Inconclusive" and an.GATE_LABEL in v["labels"]


def test_unavailable_floors():
    spec = _spec()
    ok = {"units": 30000, "events": 400, "events_ge48": 150, "g_eff": 40.0, "days": 20, "placebo_share": 0.9, "tested_units": 25000, "rewarded_shock_units": 25000}
    assert an.unavailable(ok, "CH245", spec) is None and an.unavailable(ok, "CH244", spec) is None
    for key, val, test in (("units", 19999, "CH245"), ("placebo_share", 0.49, "CH245"), ("tested_units", 19999, "CH244"), ("rewarded_shock_units", 19999, "CH244"),
                           ("events", 299, "CH245"), ("events_ge48", 99, "CH244"), ("g_eff", 14.9, "CH245"), ("days", 9, "CH244")):
        assert an.unavailable({**ok, key: val}, test, spec) is not None, key


def _world4(i: int = 0):
    df = W.world_ch245("4", np.random.default_rng(SEED + i), events=60, cal={})
    P = df[df["line"] == "thin"].reset_index(drop=True)
    return df, P


def test_f_rule_and_point_conditions_on_a_synthetic_mirror_frame():
    spec = _spec()
    df, P = _world4()
    ctrl = ["own_ds_c", "o_spread_km1_c", "spread_c"]
    prim = an.fit12(P, P["y"].to_numpy(float), "zs", ctrl, seed=1, n_boot=20)
    assert prim["testable"] and prim["p_rule"].startswith("max(p_event")
    f = an.f_rule(P, P["y"].to_numpy(float), "CH245", ctrl, prim, spec, n_boot=20)
    assert f["available"] and f["role"] == "binding" and "delta" in f
    sp = copy.deepcopy(spec)
    sp["verdict"]["dense_twin_ge2_min_units"] = 1
    pc = an.point_conditions(df, P, "CH245", ctrl, prim, sp, n_boot=20)
    dt = pc["dense_twin"]
    assert {"full", "ge2_ticks"} <= set(dt) and dt["holds"] == bool(dt["full"]["holds"] and dt["ge2_ticks"]["holds"])  # both sets must hold
    assert pc["placebo"]["rule"] == "|beta_placebo| < 0.5 x beta_thin" and pc["holds"] == bool(dt["holds"] and pc["placebo"]["holds"])
    assert spec["verdict"]["dense_twin_ge2_min_units"] == 5000
    pc2 = an.point_conditions(df, P, "CH245", ctrl, prim, spec, n_boot=20)  # this small world holds far fewer than 5,000 units on the >= 2 ticks set
    assert pc2["dense_twin"]["ge2_ticks"]["available"] is False and pc2["holds"] is False and "5,000" in pc2["dense_twin"]["ge2_ticks"]["reason"]


def test_f_rule_unavailable_below_half_of_the_primary_units():
    spec = _spec()
    df, P = _world4(1)
    ctrl = ["own_ds_c", "o_spread_km1_c", "spread_c"]
    prim = an.fit12(P, P["y"].to_numpy(float), "zs", ctrl, seed=1, n_boot=20)
    P2 = P.copy()
    P2.loc[P2.index[: int(0.6 * len(P2))], "zs_tw"] = np.nan
    f = an.f_rule(P2, P2["y"].to_numpy(float), "CH245", ctrl, prim, spec, n_boot=20)
    assert f["available"] is False and "falsification unavailable" in f["reason"]


def test_ch244_point_condition_and_joint_model():
    spec = _spec()
    df = W.world_ch244("7", np.random.default_rng(SEED + 5), events=40)
    ctrl = ["unrew", "shock", "shock_sz", "d", "absd", "own_ds_c", "spread_c", "n_members", "fav"]
    prim = an.fit12(df, df["y"].to_numpy(float), "shock_x_unrew", ctrl, seed=1, n_boot=20)
    pc = an.point_conditions(df, df, "CH244", ctrl, prim, spec, n_boot=20)
    assert "beta_lowliq" in pc and set(pc["joint_model"]) >= {"beta_unrew", "beta_lowliq", "corr_interactions"}


def test_labels_carry_the_certain_informed_e022_for_ch244_only():
    spec = _spec()
    cc = {"label": None}
    v = {"verdict": "Unavailable", "labels": []}
    assert "informed (E022)" in an.labels_for("CH244", {"load": {}}, v, spec, 2, cc)
    assert "informed (E022)" not in an.labels_for("CH245", {"load": {}}, v, spec, 2, cc)
    sp = dict(spec, informed_labels={"CH245": ["LT11"], "CH244": []})
    assert "informed (LT11)" in an.labels_for("CH245", {"load": {}}, v, sp, 2, cc)


def test_trials_line_counts_k_tests_of_kind_live_tests12():
    tl = an.trials_line(dict(_spec(), _sha256="x" * 64), ["CH245"])
    assert tl["kind"] == "live_tests12" and tl["n_tests"] == 1 and tl["tests"] == ["CH245"]


def test_reader_then_analysis_on_a_synthetic_tree(tmp_path):
    """Integration (forced, unregistered roles, dates moved in memory for the test only): the reader writes write-once frozen lines, k + 1 outcomes and
    twins; ops-stats counts them; the analysis runs both tests through the primary, the gate, F, the point conditions and the verdict."""
    snap, feed, out = tmp_path / "snap", tmp_path / "feed", tmp_path / "out"
    sy.rich_world(snap, range(0, 52), feed_root=feed)
    spec = sy.spec_for_tests()
    spec["registered_utc"], spec["end_utc"] = sy.iso(sy.slot_dt(14)), sy.iso(sy.slot_dt(47))
    spec["census_fixed"]["CH245"].update(s_D=1.5, s_T=1.5, s_w=1.0, zs_cuts=[-0.5, 0.5], zs_gap=1.8, rgap_q50_s=6.0, rgap_q90_s=11.0, exclude_family="", rho_census=0.2, rho_census_nan=False)
    spec["census_fixed"]["CH244"].update(world9_corr=0.05, shock_size_scale=0.7, exclude_family="")
    now = sy.slot_dt(60).timestamp()
    r = lt.run_once(snapshot_root=snap, feed_root=feed, root=out, spec=spec, now=now, allow_late=True, max_items=1000, window_start_utc=spec["registered_utc"])
    assert r["status"] == "wrote" and r["mirror"] > 0 and r["mixedlad"] > 0 and r["outcomes"] > 0 and r["twins"] > 0
    assert lt.run_once(snapshot_root=snap, feed_root=feed, root=out, spec=spec, now=now, allow_late=True, max_items=1000, window_start_utc=spec["registered_utc"])["status"] == "nothing_new"
    ops = lt.ops_stats(out)
    assert ops["line_counts"]["mirror:line:thin"] > 0 and all(":role:prospective_unregistered" in k for k in ops["line_counts"] if ":role:" in k)
    f = spec["verdict"]["floors"]
    f.update(CH245_thin_units=50, CH244_tested_units=50, CH244_rewarded_shock_units=50, events=5, events_ge48=0, days=1, g_eff=1)
    spec["gates"]["draws"] = 9
    res = an.analyze(out, spec=spec, now=now, force=True, roles=(lt.ROLE_UNREG,))
    for t in lt.TESTS:
        assert res[t]["verdict"]["verdict"] in ("Supported", "Inconclusive", "Contradicted", "Unavailable")
        assert res[t]["counts"]["units"] > 0 and res[t]["gate"]["testable"] in (True, False)
        assert "DRAFT: code hashes not verified" in res[t]["verdict"]["labels"]
    assert "informed (E022)" in res["CH244"]["verdict"]["labels"] and res["holm"]["m"] == 2 and res["counting"]["kind"] == "live_tests12"


def test_battery2_counts_the_lt12_trials_line_as_k_and_fails_closed():
    """8.1 / 1.11: battery2.KIND_RULES['live_tests12'] counts n_tests = k; a placebo-role line counts 0; an unknown kind raises (fail-closed)."""
    from astrolabe.research_lab import battery2

    assert battery2.KIND_RULES["live_tests12"][0] == battery2.N_TESTS and "Fail-closed" in battery2.KIND_RULES["live_tests12"][1]
    for k in (["CH245", "CH244"], ["CH244"]):
        assert battery2.count_line(an.trials_line(dict(_spec(), _sha256="x" * 64), k)) == ("live_tests12", len(k))
    assert battery2.count_line({"kind": "live_tests12", "n_tests": 2, "evidence_role": "placebo"}) == ("live_tests12", 0)
    with pytest.raises(KeyError):
        battery2.count_line({"kind": "live_tests13", "n_tests": 1})


def test_lt10_drafts_carry_the_lt12_battery2_ordering_rule():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "queue" / "drafts"
    for f in ("q0662_lt10_census_family.json", "q0663_lt10_census_kalshi.json", "q0664_lt10_census_design.json", "q0665_lt10_size_check.json"):
        n = json.loads((root / f).read_text())["notes"]
        assert "LT12 (feat/live-tests-12-code, which changes battery2.py) must be merged BEFORE LT10's first census run" in n, f
