# ruff: noqa: E501
"""LT10 analysis tests (LIVE_TESTS_10.md 1.7-1.11): the estimator and p rule, the gate, the F rule, Unavailable floors, the verdict table, Holm with p = 1
rules, the pins and refusals, the counting line, economics, and an end-to-end analysis on a synthetic tree. Synthetic data only; no network."""

from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrolabe.research_lab import battery2
from astrolabe.research_lab import bounce_decomp as bd
from astrolabe.research_lab import live_tests10 as lt
from astrolabe.research_lab import live_tests10_analysis as an

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_research_lab_live_tests10 as T  # noqa: E402


def panel(rng, *, n_ev=20, per=2, days=12, per_day=12, beta=0.0, twin_beta=0.0, twin_corr=0.0, binary=False, sparse=None):
    """A pair x origin panel with one tested term ``x``, its far-future twin ``xt`` (corr ``twin_corr`` with ``x`` through a pair persistent level), one control
    ``c1`` and the target ``y = beta x + twin_beta xt + 0.3 c1 + event shock + noise``."""
    rows = []
    for e in range(n_ev):
        shock = rng.normal(0, 0.3, days)
        for p in range(per):
            lvl = rng.normal(0, 1)
            for d in range(days):
                for i in range(per_day):
                    z = lvl * twin_corr + rng.normal()
                    x = float(z > (sparse if sparse is not None else 0.0)) if binary else z
                    zt = lvl * twin_corr + rng.normal()
                    xt = float(zt > (sparse if sparse is not None else 0.0)) if binary else zt
                    c1 = rng.normal()
                    y = beta * x + twin_beta * xt + 0.3 * c1 + shock[d] + rng.normal()
                    rows.append({"pid": f"e{e}p{p}", "ev": f"E{e}", "t": float(d * 86400 + i * 3000), "x": x, "xt": xt, "c1": c1, "y": y})
    X = pd.DataFrame(rows)
    X["market_id"], X["t_row"], X["event_id"] = X["pid"], X["t"], X["ev"]
    X["day"] = an._day(X["t"])
    return X


# --- estimator, p rule, gate ---------------------------------------------------------------------------------------------------------------


def test_fit10_detects_a_planted_effect_and_not_a_null():
    rng = np.random.default_rng(1)
    X = panel(rng, beta=0.4)
    r = an.fit10(X, X.y.to_numpy(), "x", ["c1"], seed=20261301, n_boot=100)
    assert r["testable"] and r["beta"] == pytest.approx(0.4, abs=0.08) and r["p"] < 0.01 and r["ci95_cons"][0] > 0
    assert r["p"] == pytest.approx(max(r["p_event"], r["p_twoway"], r["p_time_t"]))
    assert "p_event_ref" in r and "t on" in r["p_event_ref"]
    g = lt.event_phase_fl_gate(X, X.y.to_numpy(), "x", ["c1"], stratum="day", n_g=144, draws=60, seed=20261391)
    assert g["testable"] and g["passes"]
    X0 = panel(np.random.default_rng(2), beta=0.0)
    r0 = an.fit10(X0, X0.y.to_numpy(), "x", ["c1"], seed=1, n_boot=100)
    assert r0["p"] > 0.05 or abs(r0["beta"]) < 0.1
    g0 = lt.event_phase_fl_gate(X0, X0.y.to_numpy(), "x", ["c1"], stratum="day", n_g=144, draws=60, seed=20261391)
    assert g0["testable"] and (not g0["passes"] or g0["p_perm"] < 0.05)


def test_p_uses_the_minor_class_df():
    rng = np.random.default_rng(3)
    X = panel(rng, beta=0.15, binary=True, sparse=1.2)
    full = an.fit10(X, X.y.to_numpy(), "x", ["c1"], seed=5, minor=None, n_boot=50)
    ok = full["_mask"]
    gm = an.g_minor(X.assign(x=X.x), ok, "CH223") if False else None
    v = X["x"].to_numpy()[ok]
    ev = X["event_id"].to_numpy()[ok]
    small = 1.0 if (v == 1).sum() <= (v == 0).sum() else 0.0
    gm = int(pd.unique(ev[v == small]).size)
    sparse = an.fit10(X, X.y.to_numpy(), "x", ["c1"], seed=5, minor=3, n_boot=50)
    assert sparse["p_event"] >= full["p_event"] and sparse["p"] >= full["p"] and "G_minor = 3" in sparse["p_event_ref"]
    assert 1 <= gm <= 20
    # the helper counts events holding the smaller class
    Xt = X.copy()
    Xt["pull"] = Xt["x"]
    assert an.g_minor(Xt, ok, "CH223") == gm
    assert an.g_minor(Xt, ok, "CH224") is None


def test_unavailable_floors():
    spec = lt.load_spec(sha=None)
    base = {"units": 40000, "events": 40, "days": 21, "g_eff": 20.0}
    assert an.unavailable(base, "CH224", spec) is None
    assert "units" in an.unavailable({**base, "units": 29999}, "CH224", spec)
    assert "events" in an.unavailable({**base, "events": 29}, "CH224", spec)
    assert "G_eff" in an.unavailable({**base, "g_eff": 14.9}, "CH224", spec)
    assert "UTC days" in an.unavailable({**base, "days": 9}, "CH224", spec)
    c3 = {**base, "withdrawal_units": 1500, "no_withdrawal_units": 30000}
    assert an.unavailable(c3, "CH223", spec) is None
    assert an.unavailable({**c3, "withdrawal_units": 1499}, "CH223", spec) and an.unavailable({**c3, "no_withdrawal_units": 29999}, "CH223", spec)
    c2 = {**base, "traded_units": 2000, "quote_only_units": 2000}
    assert an.unavailable(c2, "CH222", spec) is None and an.unavailable({**c2, "traded_units": 1999}, "CH222", spec)
    assert an.unavailable({**c2, "quote_only_units": 1999}, "CH222", spec)


# --- the F rule -----------------------------------------------------------------------------------------------------------------------------


def _frule(X, test="CH224"):
    spec = copy.deepcopy(lt.load_spec(sha=None))
    Xa = X.copy()
    lt_term, lt_tw = lt.TERM[test], lt.TWIN[test]
    Xa[lt_term], Xa[lt_tw] = X["x"], X["xt"]
    y = X.y.to_numpy()
    prim = an.fit10(Xa, y, lt_term, ["c1"], seed=1, n_boot=50)
    return an.f_rule(Xa, y, test, ["c1"], prim, spec, lambda A, m: None), prim


def test_f_holds_when_only_the_lead_has_an_effect():
    X = panel(np.random.default_rng(4), beta=0.5, twin_beta=0.0)
    f, prim = _frule(X)
    assert f["available"] and f["holds"] and f["delta"] >= 0.5 * prim["beta"] and f["p_delta"] < 0.05 and f["role"] == "binding"
    assert f["twin_below_lead"] and f["arm_share"] == pytest.approx(1.0)


def test_f_fails_when_the_twin_carries_the_same_effect_a_drift():
    X = panel(np.random.default_rng(5), beta=0.5, twin_beta=0.5, twin_corr=0.0)
    f, prim = _frule(X)
    assert f["available"] and not f["holds"] and abs(f["delta"]) < 0.5 * prim["beta"]
    assert f["beta_twin_arm"] == pytest.approx(0.5, abs=0.1)


def test_f_unavailable_below_half_of_the_primary_units():
    X = panel(np.random.default_rng(6), beta=0.5)
    X.loc[X.sample(frac=0.6, random_state=1).index, "xt"] = np.nan
    f, _ = _frule(X)
    assert not f["available"] and "50%" in f["reason"]


def test_f_roles_cannot_be_switched_by_the_spec():
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["f_roles"]["CH222"] = "binding"
    with pytest.raises(RuntimeError):
        lt.f_role(spec, "CH222")
    assert [lt.f_role(lt.load_spec(sha=None), t) for t in lt.TESTS] == ["binding", "label", "label"]


# --- verdict, Holm and the p = 1 rules ----------------------------------------------------------------------------------------------------------


def _r(beta=0.5, p=0.001, ci=(0.2, 0.8), gate=True, f=None, avail=True, size_note=None):
    return {"available": avail, "unavailable_reason": None if avail else "x", "primary": {"testable": True, "beta": beta, "p": p, "ci95_cons": list(ci)},
            "gate": {"passes": gate}, "f": f or {"available": True, "holds": True, "twin_below_lead": True}, "size_note": size_note, "load": {}}


def test_verdict_table():
    assert an.verdict(_r(), 0.002, "CH224")["verdict"] == "Supported"
    assert an.verdict(_r(avail=False), 1.0, "CH224")["verdict"] == "Unavailable"
    # CH224: F fails -> Inconclusive with the label; unavailable F -> falsification unavailable
    v = an.verdict(_r(f={"available": True, "holds": False}), 0.002, "CH224")
    assert v["verdict"] == "Inconclusive" and "mechanical null not excluded" in v["labels"]
    v = an.verdict(_r(f={"available": False}), 0.002, "CH224")
    assert v["verdict"] == "Inconclusive" and "falsification unavailable" in v["labels"]
    # CH223 needs beta_twin < beta_lead; CH222's F is a label only
    assert an.verdict(_r(f={"available": True, "holds": False, "twin_below_lead": False}), 0.002, "CH223")["verdict"] == "Inconclusive"
    assert an.verdict(_r(f={"available": False}), 0.002, "CH223")["verdict"] == "Inconclusive"
    assert an.verdict(_r(f={"available": False}), 0.002, "CH222")["verdict"] == "Supported"
    assert an.verdict(_r(f={"available": True, "holds": False}), 0.002, "CH222")["verdict"] == "Supported"
    # Holm p >= 0.05, wrong direction, failed gate
    assert an.verdict(_r(), 0.06, "CH222")["verdict"] == "Inconclusive"
    assert an.verdict(_r(beta=-0.1, p=0.9, ci=(-0.4, 0.2)), 1.0, "CH222")["verdict"] == "Inconclusive"
    g = an.verdict(_r(gate=False), 1.0, "CH222")
    assert g["verdict"] == "Inconclusive" and an.GATE_LABEL in g["labels"]
    # Contradicted: the conservative CI entirely below 0
    assert an.verdict(_r(beta=-0.5, p=1.0, ci=(-0.9, -0.1)), 1.0, "CH222")["verdict"] == "Contradicted"


def test_p_equals_one_rules_and_k_unchanged():
    assert an.p_for_holm(_r()) == (0.001, None)
    assert an.p_for_holm(_r(avail=False)) == (1.0, None)
    assert an.p_for_holm(_r(gate=False)) == (1.0, an.GATE_LABEL)
    p, lab = an.p_for_holm(_r(size_note=an.SIZE_LABEL))
    assert p == 1.0 and lab == an.SIZE_LABEL
    # a size scenario that failed sets only its own test to p = 1; the Holm family size is unchanged
    ps = {"CH224": an.p_for_holm(_r(p=0.001, size_note=an.SIZE_LABEL))[0], "CH223": an.p_for_holm(_r(p=0.001))[0], "CH222": an.p_for_holm(_r(p=0.2))[0]}
    hp = bd.holm(ps)
    assert len(hp) == 3 and hp["CH224"] == 1.0 and hp["CH223"] == pytest.approx(0.003) and hp["CH222"] == pytest.approx(0.4)


def test_counting_equals_k_and_is_fail_closed():
    spec = lt.load_spec(sha=None)
    line = an.trials_line(spec, ["CH224", "CH222"])
    assert line["kind"] == "live_tests10" and line["n_tests"] == 2
    kind, n = battery2.count_line({**line})
    assert kind == "live_tests10" and n == 2
    assert battery2.KIND_RULES["live_tests10"][0] == battery2.N_TESTS
    assert battery2.count_line({"kind": "live_tests10", "n_tests": 3, "evidence_role": "placebo"})[1] == 0
    with pytest.raises(KeyError):
        battery2.count_line({"kind": "live_tests99", "n_tests": 1})


# --- pins and refusals ---------------------------------------------------------------------------------------------------------------------------


def _pinned_spec(**over):
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["_pinned"] = True
    spec["code_sha256"] = lt.code_hashes()
    spec["k_tests"] = ["CH224", "CH223", "CH222"]
    spec["size_check_result"] = {"CH224": "pass", "CH223": "pass", "CH222": "pass"}
    spec["census_fixed"]["scale_K_cents"] = 0.8
    spec["census_fixed"]["rv60"] = {"rv60_P": {"centre": .02, "scale": .006}, "rv60_K": {"centre": .02, "scale": .006}}
    spec.update(over)
    return spec


def test_analysis_refusals():
    ok = _pinned_spec()
    assert an.code_check(ok)["label"] is None
    for bad, msg in (({"k_tests": None}, "null k_tests"), ({"k_tests": []}, "empty k_tests"), ({"k_tests": ["CH224", "CH999"]}, "unknown"),
                     ({"dropped_tests": ["CH223"]}, "dropped"), ({"size_check_result": None}, "size-check")):
        with pytest.raises(an.Refused, match=msg):
            an.code_check(_pinned_spec(**bad))
    s = _pinned_spec()
    s["code_sha256"] = {**lt.code_hashes(), "live_tests10.py": "0" * 64}
    with pytest.raises(an.Refused, match="code sha256"):
        an.code_check(s)
    s = _pinned_spec()
    s["code_sha256"] = {**lt.code_hashes(), "xv_quotes_poller.py": None}
    with pytest.raises(an.Refused, match="code sha256"):
        an.code_check(s)
    s = _pinned_spec()
    s["census_fixed"]["scale_K_cents"] = None
    with pytest.raises(an.Refused, match="scale_K"):
        an.code_check(s)
    s = _pinned_spec()
    s["census_fixed"]["rv60"]["rv60_P"]["scale"] = None
    with pytest.raises(an.Refused, match="rv60"):
        an.code_check(s)
    # a DRAFT spec is only labelled
    assert "DRAFT" in an.code_check(copy.deepcopy(lt.load_spec(sha=None)))["label"]


def test_preconditions_date_pin_and_design_text(tmp_path):
    spec = _pinned_spec()
    before = lt.epoch(lt.ANALYSIS_NOT_BEFORE) - 1
    with pytest.raises(an.Refused, match="on or after"):
        an.preconditions(spec, before)
    an.preconditions(spec, before + 2)
    with pytest.raises(an.Refused, match="unpinned"):
        an.preconditions(lt.load_spec(sha=None), before + 2)
    an.preconditions(lt.load_spec(sha=None), before + 2, force=True)


def test_analyze_cli_refuses(tmp_path, capsys):
    import types

    args = types.SimpleNamespace(out=tmp_path / "a.json", xv_root=tmp_path, out_root=tmp_path)
    assert an.analyze_cli(args, lambda *a: 0, lt.epoch(lt.ANALYSIS_NOT_BEFORE) - 5) == 2
    assert an.analyze_cli(args, lambda *a: 0, lt.epoch(lt.ANALYSIS_NOT_BEFORE) + 5) == 2  # unpinned spec (SPEC_SHA256 None)
    assert "refusing" in capsys.readouterr().out


# --- economics --------------------------------------------------------------------------------------------------------------------------------


def test_taker_pnl_and_rule():
    side = np.array([1, -1, 0, 1])
    pnl = an.taker_pnl10(side, [0.49, 0.49, 0.49, 0.49], [0.51, 0.51, 0.51, np.nan], [0.53, 0.47, 0.5, 0.5], [0.55, 0.49, 0.52, 0.52], [0.02] * 4)
    assert pnl[0] == pytest.approx((0.53 - 0.51) - 0.02 * 0.51 * 0.49 - 0.02 * 0.53 * 0.47, abs=2e-5)
    assert pnl[1] == pytest.approx((0.49 - 0.49) - 0.02 * 0.49 * 0.51 - 0.02 * 0.49 * 0.51, abs=2e-5)
    assert math.isnan(pnl[2]) and math.isnan(pnl[3])
    assert an.gross10([1.0, np.nan, 3.0], ["a", "b", "c"])["mean"] == 2.0
    m1 = an.e009_models(lt.load_spec(sha=None))
    assert {"intercept", "r1", "dk6"} <= set(m1)
    bad = copy.deepcopy(lt.load_spec(sha=None))
    bad["economics"]["e009_spec_sha256"] = "0" * 64
    with pytest.raises(an.Refused):
        an.e009_models(bad)


# --- end to end on a synthetic tree ----------------------------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("an")
    xv, snap, t0, t1 = T._window_tree(tmp, hours=24 * 3, n_pairs=16, runs_until=None)
    out = tmp / "data-dumps" / "research_lab" / "live_tests10"
    spec = copy.deepcopy(lt.load_spec(sha=None))
    r = lt.run_once(xv_root=xv, out_root=out, snapshot_roots=[snap], spec=spec, now=float(t1 + 7200), max_origins=1000, freeze_clock=lambda tt: tt + 60.0)
    assert r["exit"] == 0
    spec["floors"] = {"CH224": {"units": 100}, "CH223": {"withdrawals": 10, "no_withdrawals": 100}, "CH222": {"traded": 10, "quote_only": 10}, "all": {"events": 3, "days": 2, "g_eff": 3}}
    spec["census_fixed"]["scale_K_cents"] = 0.8
    spec["census_fixed"]["rv60"] = {"rv60_P": {"centre": .02, "scale": .006}, "rv60_K": {"centre": .02, "scale": .006}}
    spec["gates"]["draws"] = 40
    res = an.analyze(out, xv_root=xv, spec=spec, now=float(t1 + 86400 * 30), force=True, roles=("prospective_unregistered",))
    return {"tmp": tmp, "xv": xv, "out": out, "spec": spec, "res": res, "t0": t0, "t1": t1}


def test_end_to_end_structure(world):
    res = world["res"]
    assert set(res["holm"]["tests"]) == set(lt.TESTS) and res["holm"]["m"] == 3 and res["counting"]["n_tests"] == 3
    for t in lt.TESTS:
        r = res[t]
        assert r["available"] and r["primary"]["testable"] and r["gate"] is not None and r["f"]["role"] == lt.F_ROLES[t]
        assert r["verdict"]["verdict"] in ("Supported", "Inconclusive", "Contradicted")
        assert "informed (E009, E010)" in r["verdict"]["labels"] and "DRAFT: code hashes not verified" in r["verdict"]["labels"]
        assert r["counts"]["units"] > 100 and set(r["economics"]) >= {"hurdles", "note", "reward_subset"}
        assert "sens_pair_cluster" in r["readings"] and "both_demeaned" in r["readings"] and "holiday_excluded" in r["readings"]
    assert res["CH222"]["economics"]["taker_e009_rule"]["traded"]["signals_fired"] >= 0
    assert "maker_gross_improve_one_tick_after_kalshi_tightening" in res["CH224"]["economics"]
    assert "maker_gross_class_difference" in res["CH223"]["economics"]
    assert res["stream_gap_share"] is not None and res["design_text_sha256"] == lt.DESIGN_TEXT_SHA256


def test_end_to_end_targets_are_cents_and_two_sided(world):
    df, acc = an.load_kind(world["out"], "CH224", world["t0"], world["t1"], world["spec"], roles=("prospective_unregistered",))
    X = an.frame(df, "CH224", world["spec"])
    assert acc["late_files"] == 0 and acc["late_loss_share"] == 0.0
    ok = np.isfinite(X["y"].to_numpy())
    assert ok.mean() > 0.9 and np.nanmax(np.abs(X["y"])) <= 10.5 and np.allclose(X["y"].dropna(), np.round(X["y"].dropna()), atol=1e-6)  # spreads on the 1c grid move in whole cents
    d3, _ = an.load_kind(world["out"], "CH223", world["t0"], world["t1"], world["spec"], roles=("prospective_unregistered",))
    X3 = an.frame(d3, "CH223", world["spec"])
    assert (X3["cls223"] == 0).all() and (X3["y"].dropna() >= 0).all()
    d2, _ = an.load_kind(world["out"], "CH222", world["t0"], world["t1"], world["spec"], roles=("prospective_unregistered",))
    X2 = an.frame(d2, "CH222", world["spec"])
    assert X2["cls222"].isin([0, 1]).all() and (X2["abs_dk1"] >= 0.005 - 1e-9).all()


def test_end_to_end_role_and_pin_filters(world):
    df, acc = an.load_kind(world["out"], "CH224", world["t0"], world["t1"], world["spec"])  # role prospective_confirmation: the tree is unregistered
    assert df.empty and acc["dropped_role"] > 0
    pinned = copy.deepcopy(world["spec"])
    pinned["_pinned"] = True
    pinned["code_sha256"] = lt.code_hashes()
    d1, a1 = an.load_kind(world["out"], "CH224", world["t0"], world["t1"], pinned, roles=("prospective_unregistered",))
    assert len(d1) > 0 and a1["dropped_spec_sha"] == 0 and a1["dropped_code_sha"] == 0  # the lines carry this spec and code
    wrong_spec = {**pinned, "_sha256": "f" * 64}
    d2, a2 = an.load_kind(world["out"], "CH224", world["t0"], world["t1"], wrong_spec, roles=("prospective_unregistered",))
    assert d2.empty and a2["dropped_spec_sha"] > 0
    wrong_code = {**pinned, "code_sha256": {**lt.code_hashes(), "live_tests10.py": "0" * 64}}
    d3, a3 = an.load_kind(world["out"], "CH224", world["t0"], world["t1"], wrong_code, roles=("prospective_unregistered",))
    assert d3.empty and a3["dropped_code_sha"] > 0


def test_end_to_end_dropped_tests_get_no_estimate(world):
    spec = copy.deepcopy(world["spec"])
    spec["k_tests"] = ["CH224"]
    res = an.analyze(world["out"], xv_root=world["xv"], spec=spec, now=float(world["t1"] + 86400 * 30), force=True, roles=("prospective_unregistered",))
    assert res["holm"]["m"] == 1 and res["counting"]["n_tests"] == 1
    assert "primary" not in res["CH223"] and "dropped at its census" in res["CH223"]["verdict"]["verdict"]
    assert res["CH224"]["verdict"]["verdict"] in ("Supported", "Inconclusive", "Contradicted")


def test_end_to_end_size_check_failure_sets_only_its_tests(world):
    spec = copy.deepcopy(world["spec"])
    spec["size_check_result"] = {"CH224": "fail_size_scenario", "CH223": "pass", "CH222": "fail_mechanical_world"}
    res = an.analyze(world["out"], xv_root=world["xv"], spec=spec, now=float(world["t1"] + 86400 * 30), force=True, roles=("prospective_unregistered",))
    assert res["holm"]["m"] == 3 and res["holm"]["p_raw"]["CH224"] == 1.0 and res["holm"]["p_raw"]["CH222"] == 1.0
    assert an.SIZE_LABEL in res["CH224"]["verdict"]["labels"] and an.MECH_LABEL in res["CH222"]["verdict"]["labels"]
    assert an.SIZE_LABEL not in res["CH223"]["verdict"]["labels"]


def test_end_to_end_unavailable_floor(world):
    spec = copy.deepcopy(world["spec"])
    spec["floors"] = {**spec["floors"], "CH224": {"units": 10**9}}
    res = an.analyze(world["out"], xv_root=world["xv"], spec=spec, now=float(world["t1"] + 86400 * 30), force=True, roles=("prospective_unregistered",))
    assert res["CH224"]["verdict"]["verdict"] == "Unavailable" and res["holm"]["p_raw"]["CH224"] == 1.0


def test_stream_gap_share(world):
    spec = world["spec"]
    gap = an.stream_gap_share(world["xv"], spec)
    assert 0.8 < gap < 1.0  # three days of cycles against a 21-day window
