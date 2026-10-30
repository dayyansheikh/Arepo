# ruff: noqa: E501
"""LT6 readings (live_tests6_readings): the binding label rules, attrition with Lee bounds, coverage / sweep-missing labels, the fake-birth
placebo, the Thanksgiving sensitivity. Synthetic frames only; nothing here changes a verdict."""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from astrolabe.research_lab import live_tests6 as lt
from astrolabe.research_lab import live_tests6_readings as rd


def sig(beta=0.01, p=0.01):
    return {"testable": True, "beta": beta, "p": p, "ci95_cons": [beta - 0.01, beta + 0.01]}


def non_sig(beta=0.002, p=0.4):
    return {"testable": True, "beta": beta, "p": p, "ci95_cons": [beta - 0.02, beta + 0.02]}


def test_v_label_rules():
    # M1 below half of D_V, or not significant: sweep-stream specific (only when the primary is Supported)
    assert "sweep-stream specific" in rd.label_rules("V", True, 0.01, {"M1": non_sig(0.012, 0.3)})
    assert "sweep-stream specific" in rd.label_rules("V", True, 0.01, {"M1": sig(0.004, 0.01)})
    assert "sweep-stream specific" not in rd.label_rules("V", True, 0.01, {"M1": sig(0.006, 0.01)})
    assert "sweep-stream specific" not in rd.label_rules("V", False, 0.01, {"M1": non_sig()})
    # M3: only the toward-side term one-sided significant in the predicted direction (lt < 0)
    m3 = {"lt": sig(-0.01, 0.01), "la": non_sig()}
    assert any("depletion mechanics" in x for x in rd.label_rules("V", True, 0.01, {"M1": sig(0.01), "M3": m3}))
    assert not any("depletion" in x for x in rd.label_rules("V", True, 0.01, {"M1": sig(0.01), "M3": {"lt": sig(-0.01, 0.01), "la": sig(0.01, 0.01)}}))
    assert not any("depletion" in x for x in rd.label_rules("V", True, 0.01, {"M1": sig(0.01), "M3": {"lt": sig(0.01, 0.01), "la": non_sig()}}))  # wrong sign
    # the placebo (pre-move vote): significant and at least half of D_V
    assert "standing skew, not a reaction" in rd.label_rules("V", False, 0.01, {"P_vprev": sig(0.006, 0.02)})
    assert "standing skew, not a reaction" not in rd.label_rules("V", False, 0.01, {"P_vprev": sig(0.004, 0.02)})


def test_k_label_rules():
    assert "Gamma-quote mechanics" in rd.label_rules("K", True, 0.01, {"M1": non_sig()})
    m3 = {"running": non_sig(), "finished": sig()}
    assert "not schedule pressure" in rd.label_rules("K", True, 0.01, {"M1": sig(), "M3": m3})
    assert "not schedule pressure" not in rd.label_rules("K", True, 0.01, {"M1": sig(), "M3": {"running": sig(), "finished": sig()}})
    assert "size identity not shown" in rd.label_rules("K", False, 0.01, {"P1": sig(0.006, 0.03)})
    assert "persistent trait" in rd.label_rules("K", False, 0.01, {"P2": sig(0.02, 0.03)})
    assert rd.label_rules("K", False, 0.01, {"P1": non_sig(), "P2": sig(0.002, 0.2)}) == []


def test_d_and_b_label_rules():
    rem = {"testable": True, "beta": -0.01, "p": 0.9, "ci95_cons": [-0.03, -0.001]}  # the conservative CI lies below 0: contradicted
    assert "transient" in rd.label_rules("D", True, 0.01, {"M1": sig(0.02), "M1_remainder": rem})
    assert "transient" not in rd.label_rules("D", True, 0.01, {"M1": sig(0.02), "M1_remainder": non_sig(-0.002, 0.7)})
    assert "transient" not in rd.label_rules("D", False, 0.01, {"M1": sig(0.02), "M1_remainder": rem})
    assert "event-level volatility, not the listing" in rd.label_rules("B", False, 0.01, {"P_fake_birth": sig(0.006, 0.04)})
    assert rd.label_rules("B", True, 0.01, {"P_fake_birth": non_sig()}) == []


def test_coverage_and_sweep_missing_labels():
    spec = lt.load_spec(sha=None)
    assert rd.coverage_label({"traded_ge4_rows": 1000, "traded_ge4_truncated": 21}, spec).startswith("coverage-limited")
    assert rd.coverage_label({"traded_ge4_rows": 1000, "traded_ge4_truncated": 20}, spec) is None and rd.coverage_label({}, spec) is None
    assert rd.sweep_missing_label({"files": 90, "nosweep_files": 3, "noprevsweep_files": 1, "late_files": 6}, spec).startswith("sweep-missing")
    assert rd.sweep_missing_label({"files": 97, "nosweep_files": 1, "noprevsweep_files": 1, "late_files": 1}, spec) is None


def _frame(n=60, seed=0, effect=0.0):
    rng = np.random.default_rng(seed)
    mk = np.repeat([f"m{i}" for i in range(n // 6)], 6)
    br = (rng.random(n) < 0.3).astype(float)
    y = 0.01 * rng.normal(size=n) + effect * br
    f = pd.DataFrame({"market_id": mk, "event_id": [f"e{i // 12}" for i in range(n)], "t_row": np.tile(np.arange(6) * 7200.0, n // 6), "day": np.tile(np.arange(6).astype(str), n // 6),
                      "BR": br, "a22": np.abs(y), "slot": np.tile(np.arange(6), n // 6) + 100, "loo_a1": rng.uniform(0, 0.03, n), "cls": np.where(br > 0, "birth", "nobirth"),
                      "capture_t": 1.7e9 + np.tile(np.arange(6) * 7200.0, n // 6)})
    return f


def test_attrition_triggers_and_lee_bounds_are_computed_for_a_differential():
    spec = lt.load_spec(sha=None)
    f = _frame(120, 1, 0.01)
    # 30% of birth units lost versus 5% of no-birth units: |diff| > 2 pp
    st = np.where((f["BR"] == 1) & (np.arange(len(f)) % 10 < 3), "absent", "two_sided")
    st = np.where((f["BR"] == 0) & (np.arange(len(f)) % 20 == 0), "absent", st)
    pre = pd.DataFrame({"status": st, "cls": f["BR"].astype(int).astype(object)})
    f["y"] = f["a22"]
    calls = []

    def refit(sub, y):
        calls.append(len(sub))
        return {"beta": float(np.mean(y)), "p": 0.5, "testable": True}

    out = rd.attrition_reading("B", pre, f, spec, refit)
    assert out["triggered"] and out["lee"]["computed"] and out["lee"]["trimmed_class"] == "0" and len(calls) == 2
    ok = rd.attrition_reading("B", pre.assign(status="two_sided"), f, spec, refit)
    assert not ok["triggered"] and "lee" not in ok


def test_fake_birth_placebo_draws_far_from_real_births_in_the_same_tercile_with_the_registered_seed():
    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec["b"]["fake_birth_terciles"] = [0.01, 0.02]
    rows = []
    for s in range(100, 140):  # one event, 40 slots; a real birth at slot 110 and 111 (same event)
        for m in range(3):
            rows.append({"market_id": f"m{m}", "event_id": "e1", "slot": s, "BR": 1.0 if s == 110 else 0.0, "loo_a1": 0.005 + 0.0005 * (s % 40),
                         "a22": 0.01, "cls": "birth" if s == 110 else "nobirth"})
    f = pd.DataFrame(rows)
    pop, cnt = rd.fake_birth_frame(f, spec)
    assert cnt["real_births"] == 1 and cnt["fake_drawn"] == 1 and cnt["none_available"] == 0
    assert (pop["BR"] == 0).all() and set(pop["slot"]) == set(range(100, 140)) - {110}
    fake_slots = set(pop.loc[pop["BR_fake"] == 1, "slot"])
    assert len(fake_slots) == 1 and abs(next(iter(fake_slots)) - 110) >= 12
    pop2, _ = rd.fake_birth_frame(f, spec)  # deterministic under the seed 20261364
    assert set(pop2.loc[pop2["BR_fake"] == 1, "slot"]) == fake_slots
    spec["b"]["fake_birth_terciles"] = None
    assert rd.fake_birth_frame(f, spec)[0].empty
    assert spec["seeds"]["B_fake_birth"] == 20261364


def test_thanksgiving_sensitivity_drops_the_two_days_and_counts_them():
    spec = lt.load_spec(sha=None)
    f = _frame(120, 2).assign(zv=0.0)
    lo, hi = (lt.epoch(x) for x in spec["labels"]["thanksgiving_excluded_utc"])
    f["capture_t"] = np.where(np.arange(len(f)) % 6 == 0, lo + 3600.0, lo - 86400.0 * 3)
    from astrolabe.research_lab import live_tests6_analysis as la

    f = f.assign(**{la.PRIMARY["B"]["y"]: f["a22"]})
    out = rd.thanksgiving_sensitivity("B", f, spec, 10)
    assert out["units_dropped"] == int((np.arange(len(f)) % 6 == 0).sum())
    assert hi > lo


def test_d_p1_label_rule():
    assert "not template-specific" in rd.label_rules("D", True, 0.01, {"P1": sig(0.006, 0.03)})
    assert "not template-specific" not in rd.label_rules("D", True, 0.01, {"P1": sig(0.004, 0.03)})
    assert "not template-specific" not in rd.label_rules("D", True, 0.01, {"P1": {"computed": False}})


def test_pass_counts_filters_by_spec_sha_and_window(tmp_path):
    import json

    spec = copy.deepcopy(lt.load_spec(sha=None))
    spec.update(_pinned=True, _sha256="a" * 64, registered_utc="2026-10-02T00:00:00Z", end_utc="2026-10-03T00:00:00Z")
    rows = [{"kind": "clips_frozen", "id": "20261002T040000Z_x", "spec_sha": "a" * 16, "counts": {"traded_ge4_rows": 10}},
            {"kind": "clips_frozen", "id": "20261002T060000Z_x", "spec_sha": "b" * 16, "counts": {"traded_ge4_rows": 100}},  # another spec
            {"kind": "clips_frozen", "id": "20260930T060000Z_x", "spec_sha": "a" * 16, "counts": {"traded_ge4_rows": 1000}},  # before the window
            {"kind": "clips_frozen", "id": "20261002T080000Z_x", "spec_sha": "a" * 16, "counts": {"traded_ge4_rows": 1}}]
    (tmp_path / "passes.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    assert rd.pass_counts(tmp_path, "clips", spec) == {"traded_ge4_rows": 11}
