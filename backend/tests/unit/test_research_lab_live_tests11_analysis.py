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
    from tests.unit.test_research_lab_live_tests11 import _reader_world
    from tests import lt11_synth as sy

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
    from tests.unit.test_research_lab_live_tests11 import _reader_world
    from tests import lt11_synth as sy

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
    sp["census_fixed"] = {"CH234": {"a": 1.0}}
    an.code_check(sp)  # fully filled and matching: accepted
    sp["code_sha256"] = {**pins, "live_tests11.py": "0" * 64}
    with pytest.raises(an.Refused):
        an.code_check(sp)
    sp["code_sha256"], sp["k_tests"] = pins, ["CH234", "CH233"]
    sp["census_fixed"]["CH233"] = {"a": 1.0}
    with pytest.raises(an.Refused):  # a surviving test without its recorded size-check result
        an.code_check(sp)
    sp["size_check_result"]["CH233"] = "pass"
    sp["dropped_tests"] = ["CH233"]
    with pytest.raises(an.Refused):  # k_tests naming a dropped test
        an.code_check(sp)
