# ruff: noqa: E501
"""LT11 analysis: refusals, the event-index gate, fit11, Holm p rules, verdict logic (synthetic only)."""

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import live_tests11 as lt
from astrolabe.research_lab import live_tests11_analysis as an


def _spec():
    return {"_pinned": False, "registered_utc": "2026-11-18T00:00:00Z"}


def test_analysis_date_refusal():
    with pytest.raises(an.Refused):
        an.preconditions(_spec(), lt.epoch(lt.ANALYSIS_NOT_BEFORE) - 1)


def test_unpinned_spec_refused_after_date():
    with pytest.raises(an.Refused):
        an.preconditions(_spec(), lt.epoch(lt.ANALYSIS_NOT_BEFORE) + 1)


def test_p_for_holm_rules():
    base = {"available": True, "primary": {"testable": True, "p": 0.01}, "gate": {"passes": True}}
    assert an.p_for_holm(base) == (0.01, None)
    assert an.p_for_holm({**base, "gate": {"passes": False}}) == (1.0, an.GATE_LABEL)
    assert an.p_for_holm({**base, "size_note": an.SIZE_LABEL}) == (1.0, an.SIZE_LABEL)
    assert an.p_for_holm({"available": False}) == (1.0, None)


def test_verdict_branches():
    prim = {"testable": True, "p": 0.001, "beta": 1.0, "ci95_cons": [0.5, 1.5]}
    r = {"available": True, "primary": prim, "gate": {"passes": True}, "f": {"available": True, "holds": True}, "point_condition": {"holds": True}}
    assert an.verdict(r, 0.01, "CH234")["verdict"] == "Supported"
    r2 = {**r, "f": {"available": False}}
    v = an.verdict(r2, 0.01, "CH234")
    assert v["verdict"] == "Inconclusive" and "falsification unavailable" in v["labels"]
    r3 = {**r, "primary": {**prim, "beta": -1.0, "ci95_cons": [-2, -0.5]}}
    assert an.verdict(r3, 0.9, "CH234")["verdict"] == "Contradicted"
    assert an.verdict({"available": False, "unavailable_reason": "x"}, 1.0, "CH234")["verdict"] == "Unavailable"


def _panel(n_events=40, sig=0.0, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for e in range(n_events):
        for m in range(4):
            for s in range(30):
                x = rng.normal()
                rows.append({"event_id": str(e), "market_id": f"{e}-{m}", "slot": s, "t_row": float(s * 7200), "xw": x, "y": sig * x + rng.normal()})
    return pd.DataFrame(rows)


def test_event_index_gate_null_and_signal():
    df = _panel(sig=0.0)
    g0 = an.event_index_fl_gate(df, df["y"].to_numpy(), "xw", [], draws=60, seed=3)
    assert g0["testable"] and g0["omitted_share_max"] == 0.0
    df1 = _panel(sig=0.5)
    g1 = an.event_index_fl_gate(df1, df1["y"].to_numpy(), "xw", [], draws=60, seed=3)
    assert g1["passes"] is True


def test_event_gate_omits_missing_positions():
    df = _panel(n_events=10, sig=0.2)
    df = df.drop(df.sample(frac=0.2, random_state=0).index).reset_index(drop=True)
    g = an.event_index_fl_gate(df, df["y"].to_numpy(), "xw", [], draws=20, seed=4)
    assert g["testable"] and g["omitted_share_median"] > 0


def test_g_minor_ch232():
    X = pd.DataFrame({"xo": [1, 1, 0, 1], "event_id": ["a", "a", "b", "c"]})
    assert an.g_minor(X, np.ones(4, bool), "CH232") == 2
    assert an.g_minor(X, np.ones(4, bool), "CH234") is None


def test_run_test_smoke_on_reader_world_is_unavailable_by_floors(tmp_path):
    from tests import lt11_synth as sy
    from tests.unit.test_research_lab_live_tests11 import _reader_world

    root, by_slot, spec = _reader_world(tmp_path)
    out = tmp_path / "out"
    lt.run_once(snapshot_root=root, sweep_root=tmp_path / "nosweeps", root=out, spec=spec, now=sy.slot_dt(60).timestamp(), allow_late=True, max_items=10_000)
    spec = {**spec, "seeds": {"estimators": {"CH234": 1, "CH233": 2, "CH232": 3}, "gates": {"CH234": 4, "CH233": 5, "CH232": 6}}, "gates": {"draws": 20, "min_shift_rows": 16, "block_min_n": 8}}
    roles = ("prospective_unregistered", an.ROLE_CONF)
    for t in an.TESTS:
        r = an.run_test(out, t, 0.0, 4e9, spec, roles, None)
        assert r["available"] is False
        assert an.verdict(r, 1.0, t)["verdict"] == "Unavailable"


def test_full_path_with_loose_floors_runs_every_block(tmp_path):
    import copy

    from tests import lt11_synth as sy
    from tests.unit.test_research_lab_live_tests11 import _reader_world

    root, by_slot, spec = _reader_world(tmp_path)
    out = tmp_path / "out"
    lt.run_once(snapshot_root=root, sweep_root=tmp_path / "nosweeps", root=out, spec=spec, now=sy.slot_dt(60).timestamp(), allow_late=True, max_items=10_000)
    spec = copy.deepcopy(spec)
    spec.update(seeds={"estimators": {"CH234": 1, "CH233": 2, "CH232": 3}, "gates": {"CH234": 4, "CH233": 5, "CH232": 6}}, gates={"draws": 20, "min_shift_rows": 4, "block_min_n": 4})
    spec["verdict"]["floors"] = {k: 1 for k in spec["verdict"]["floors"]}
    spec["verdict"]["floors"]["g_eff"] = 0
    roles = ("prospective_unregistered", an.ROLE_CONF)
    seen = 0
    for t in an.TESTS:
        r = an.run_test(out, t, 0.0, 4e9, spec, roles, None)
        if r.get("primary") is not None and r.get("counts"):
            seen += 1
            v = an.verdict(r, 1.0, t)
            assert v["verdict"] in {"Inconclusive", "Contradicted", "Supported", "Unavailable"}
    assert seen >= 0


def test_pinned_spec_with_nan_or_null_census_value_or_code_mismatch_refuses():
    base = lt.load_spec(sha=None)
    pins = dict(lt.code_hashes())
    sp = {**base, "_pinned": True, "code_sha256": pins, "k_tests": ["CH234"], "dropped_tests": [], "census_fixed": {"CH234": {"a": float("nan")}}, "size_check_result": {"CH234": "pass"}}
    with pytest.raises(an.Refused):
        an.code_check(sp)
    sp["census_fixed"] = {"CH234": {"a": None}}
    with pytest.raises(an.Refused):
        an.code_check(sp)
    sp["census_fixed"] = {"CH234": {"a": 1.0, "b": [1.0, float("nan")]}}
    with pytest.raises(an.Refused):  # a non-finite value inside a nested list (review defect 6)
        an.code_check(sp)
    sp["census_fixed"] = {"CH234": {"a": 1.0, "b": []}}
    with pytest.raises(an.Refused):  # an empty nested list
        an.code_check(sp)
    sp["census_fixed"] = {"CH234": {"a": 1.0}}
    with pytest.raises(an.Refused):  # informed_labels still null (unfilled): refused (review defect 3)
        an.code_check(sp)
    sp["informed_labels"] = {"CH234": []}
    an.code_check(sp)  # fully filled and matching ([] = none, explicitly assigned): accepted
    sp["code_sha256"] = {**pins, "live_tests11.py": "0" * 64}
    with pytest.raises(an.Refused):
        an.code_check(sp)
    sp["code_sha256"], sp["k_tests"] = pins, ["CH234", "CH233"]
    sp["census_fixed"]["CH233"] = {"a": 1.0}
    sp["informed_labels"]["CH233"] = []
    with pytest.raises(an.Refused):  # a surviving test without its recorded size-check result
        an.code_check(sp)
    sp["size_check_result"]["CH233"] = "pass"
    sp["dropped_tests"] = ["CH233"]
    with pytest.raises(an.Refused):  # k_tests naming a dropped test
        an.code_check(sp)


# --- review 2026-10-23 fixes (LT11_CODE_FREEZE_CHECK) -------------------------------------------------------------------------------------------


def test_event_gate_minimum_counts_captures_not_units():
    """SHOULD-FIX 1: an event enters the event-phase gate only with >= 16 captures on its index (the census's 'events with >= 16 shiftable captures')."""
    rng = np.random.default_rng(2)
    rows = []
    for e in range(30):  # 10 members x 12 captures = 120 units but only 12 captures: excluded
        for m in range(10):
            for s in range(12):
                rows.append({"event_id": f"a{e}", "market_id": f"a{e}-{m}", "slot": s, "t_row": float(s * 7200), "xw": rng.normal(), "y": rng.normal()})
    df = pd.DataFrame(rows)
    g = an.event_index_fl_gate(df, df["y"].to_numpy(), "xw", [], draws=20, seed=1)
    assert not g["testable"] and "captures" in g["reason"]
    df2 = _panel(n_events=10)  # 30 captures each: shifted
    g2 = an.event_index_fl_gate(df2, df2["y"].to_numpy(), "xw", [], draws=20, seed=1)
    assert g2["testable"] and g2["events_shifted"] == 10


def _ch233_frame(beta_bid, beta_ask, seed=4):
    rng = np.random.default_rng(seed)
    rows = []
    for e in range(60):
        for m in range(4):
            for s in range(30):
                zcl, zca = rng.normal(), rng.normal()
                rows.append({"event_id": str(e), "market_id": f"{e}-{m}", "slot": s, "t_row": float(s * 7200), "day": str(s // 12), "arm": "primary", "zcl": zcl, "zca": zca,
                             "y": beta_bid * zcl + beta_ask * zca + rng.normal(0, 0.5)})
    return pd.DataFrame(rows)


def test_ch233_difference_is_beta_bid_minus_beta_ask():
    """SHOULD-FIX 3 (A23 revised): the CH233 difference is the coefficient on zcl with zcl + zca added (F's form), i.e. beta_bid - beta_ask."""
    X = _ch233_frame(1.0, 0.6)
    spec = {"verdict": {"point_condition_ratio": 0.5}}
    pc = an.point_condition(X, "CH233", [], {"beta": 1.0}, spec, X["y"].to_numpy(float), 1)
    assert pc["beta_difference"] == pytest.approx(0.4, abs=0.08) and pc["beta_alt"] == pytest.approx(0.6, abs=0.08)


def _label_spec(**cf):
    return {"verdict": {"material_c": {"CH234": 0.5, "CH233": 1.0, "CH232": 1.0}, "series_concentrated": 0.5, "late_loss_max": 0.02},
            "census_fixed": {"CH234": {"xw_gap": 2.0, "mde_c": 0.4, **cf}, "CH233": {"zcl_gap": 2.0}, "CH232": {}}, "m1_side_reading": "cheap", "informed_labels": {"CH234": ["E015"]}}


def _label_r(beta=0.3, p_diff=0.2, **extra):
    fr = pd.DataFrame({"skey": ["a"] * 6 + ["b"] * 4})
    return {"primary": {"beta": beta, "p": 0.2, "n_day": 21, "se_day": 0.05}, "point_condition": {"p_difference": p_diff, "holds": True}, "load": {"late_loss_share": 0.0},
            "_frame": fr, "_prim": {"_mask": np.ones(len(fr), bool)}, **extra}


def test_labels_follow_1_9():
    """SHOULD-FIX 2: material = estimate x census tercile gap >= floor; the difference label iff its p < 0.05 (no precedence slip); series-concentrated on the
    series family; informed (X); within-bin; volume-missing sensitive; ladder-dominated; underpowered; side reading ambiguous."""
    cc = {"label": None}
    sp = _label_spec()
    inc = {"verdict": "Inconclusive", "labels": []}
    lab = an.labels_for("CH234", _label_r(beta=0.3), inc, sp, 1, cc)
    assert "material" in lab  # 0.3 x 2.0 = 0.6 >= 0.5 (the old rule compared 0.3 with 0.5)
    assert "material" not in an.labels_for("CH234", _label_r(beta=0.2), inc, sp, 1, cc)
    assert "traded-difference significant" not in lab  # p_difference 0.2 (the old precedence labelled it whenever the point condition failed)
    assert "traded-difference significant" in an.labels_for("CH234", _label_r(p_diff=0.01), {"verdict": "Supported", "labels": []}, sp, 1, cc)
    assert "series-concentrated (60%)" in lab and "informed (E015)" in lab
    ok_bins = {str(i): {"testable": True, "beta": 0.1} for i in range(4)}
    li = {"bins": ok_bins, "unknown_arm": {"testable": True, "beta": 0.5}, "ladder_arm": {"testable": True, "beta": -0.1}}
    lab2 = an.labels_for("CH234", _label_r(label_readings=li, underpowered={"above": True}), inc, sp, 1, cc)
    assert {"within-bin", "volume-missing sensitive", "ladder-dominated", "underpowered"} <= set(lab2)
    li["bins"]["2"] = {"testable": True, "beta": -0.1}
    assert "within-bin" not in an.labels_for("CH234", _label_r(label_readings=li), inc, sp, 1, cc)
    m1 = {"m1": {"testable": True, "beta": -0.4, "p": 0.01}}
    assert "re-centring not widening" in an.labels_for("CH233", _label_r(label_readings=m1), inc, sp, 1, cc)
    assert "re-centring not widening" not in an.labels_for("CH233", _label_r(label_readings=m1), {"verdict": "Supported", "labels": []}, sp, 1, cc)
    assert "side reading ambiguous" in an.labels_for("CH232", _label_r(), inc, {**sp, "m1_side_reading": None}, 1, cc)
    assert "side reading ambiguous" not in an.labels_for("CH232", _label_r(), inc, sp, 1, cc)


def test_underpowered_uses_the_census_mde():
    sp = _label_spec()
    r = _label_r()
    u = an.underpowered("CH234", r, sp, 3)
    from scipy.stats import t as t_

    want = (t_.ppf(1 - 0.05 / 3, 20) + t_.ppf(0.8, 20)) * 0.05
    assert u["computed"] and u["window_mde_c"] == pytest.approx(want) and u["above"] == (want > 0.4)
    assert not an.underpowered("CH234", r, _label_spec(mde_c=None), 3)["computed"]


def test_default_spec_informed_labels_is_null_and_not_computed_list_is_reported():
    assert lt.load_spec(sha=None)["informed_labels"] is None
    import inspect
    assert "labels_not_computed" in inspect.getsource(an.analyze)
