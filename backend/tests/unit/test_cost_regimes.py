# ruff: noqa: E501
"""R0 tests (CB4 section 4.4, challenger item 13): cost_regime never goes below the CB1 section 2.1 defaults, has no band map,
planning_band_map refuses April-August pmxt data and any selection use, writing a cost-lowering register raises."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pytest

from astrolabe.research_lab import battery2, cb1_history
from astrolabe.research_lab import cost_regimes as cr
from astrolabe.research_lab import economics as eco


def _payload(**kw):
    p = {"version": cr.VERSION, "label": cr.LABEL, "fee_eras": cr.FEE_ERAS, "family_M_complete": True, "era_rule": cr.ERA_RULE_POST,
         "a_AS_cents": 0.4, "fee_rate_add": 0.0, "half_spread_add": 0.0,
         "measurements": {k: {"label": cr.LABEL, "adopted": False} for k in cr.MEASUREMENTS},
         "band_map": {"politics": {"share_mid": 0.02}}}
    p.update(kw)
    return p


def _reg(tmp_path, payload, name="reg.json"):
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return p


CATS = [*sorted(set(eco.DOCS_CATEGORY_RATE) | {"unknown", "other:xyz"}), None]
PRICES = (0.01, 0.1, 0.5, 0.9, 0.99)
ADVERSARIAL = [
    {}, {"fee_rate_add": -0.5, "half_spread_add": -1.0, "a_AS_cents": -3.0},
    {"fee_rate_add": float("nan"), "half_spread_add": float("inf"), "a_AS_cents": float("-inf")},
    {"fee_rate_add": "x", "half_spread_add": None, "a_AS_cents": "1"},
    {"fee_rate_add": 0.01, "half_spread_add": 0.005, "a_AS_cents": 2.5},
]


def test_grid_never_below_cb1_defaults(tmp_path):
    d0, d1 = date(2025, 6, 1), date(2027, 6, 30)
    days = [d0 + timedelta(days=i) for i in range(0, (d1 - d0).days + 1, 7)] + [date(2026, 2, 17), date(2026, 2, 18), date(2026, 3, 29), date(2026, 3, 30), d1]
    for i, adv in enumerate(ADVERSARIAL):
        path = _reg(tmp_path, _payload(**adv), f"r{i}.json")
        for d in days:
            for c in CATS:
                for p in PRICES:
                    out = cr.cost_regime(d, c, p, register_path=path)
                    assert out["fee_rate"] >= cb1_history.fee_rate(c) - 1e-15
                    assert out["half_spread"] >= cb1_history.half_spread(p) - 1e-15
                    assert out["a_as_cents"] >= 0.0
                    assert "band_map" not in out


def test_absent_register_gives_defaults_flagged(tmp_path):
    out = cr.cost_regime("2026-05-01", "politics", 0.3, register_path=tmp_path / "none.json")
    assert out["register_status"] == "absent_defaults"
    assert out["fee_rate"] == cb1_history.fee_rate("politics") and out["half_spread"] == cb1_history.half_spread(0.3)
    assert out["a_as_cents"] == 0.0 and out["era_rule"] == cr.ERA_RULE_POOLED


def test_a_as_applies_only_before_the_category_rollout(tmp_path):
    path = _reg(tmp_path, _payload(a_AS_cents=0.7))
    assert cr.cost_regime("2026-03-01", "politics", register_path=path)["a_as_cents"] == 0.7  # before 03-30
    assert cr.cost_regime("2026-03-30", "politics", register_path=path)["a_as_cents"] == 0.0
    assert cr.cost_regime("2026-02-17", "sports", register_path=path)["a_as_cents"] == 0.7
    assert cr.cost_regime("2026-02-18", "sports", register_path=path)["a_as_cents"] == 0.0
    assert cr.cost_regime("2026-04-05", "politics", register_path=path)["post_rollout"] is False
    assert cr.cost_regime("2026-04-06", "politics", register_path=path)["post_rollout"] is True
    assert cr.cost_regime("2026-02-25", "sports", register_path=path)["post_rollout"] is True


def test_clamped_adjustment_is_flagged(tmp_path):
    out = cr.cost_regime("2026-05-01", "crypto", register_path=_reg(tmp_path, _payload(fee_rate_add=-0.02)))
    assert "register_adjustment_clamped_to_zero" in out["flags"] and out["fee_rate"] == cb1_history.fee_rate("crypto")


def test_planning_band_map_refuses_pmxt_window_and_selection_use(tmp_path):
    path = _reg(tmp_path, _payload())
    ok = {"data_window": ["2026-10-20", "2026-12-31"], "planning_only": True, "selects": []}
    assert cr.planning_band_map(ok, register_path=path) == {"politics": {"share_mid": 0.02}}
    for w in (["2026-04-13", "2026-04-13"], ["2026-01-01", "2026-04-20"], ["2026-08-10", "2026-09-01"], ["2026-05-01", "2026-06-01"], ["2026-01-01", "2026-12-31"]):
        with pytest.raises(cr.CostRegimeError):
            cr.planning_band_map({**ok, "data_window": w}, register_path=path)
    for bad in (["category"], ["band"], ["event"], ["threshold"], ["bands", "x"]):
        with pytest.raises(cr.CostRegimeError):
            cr.planning_band_map({**ok, "selects": bad}, register_path=path)
    for decl in ({}, {"data_window": ok["data_window"]}, {**ok, "planning_only": False}, {"data_window": ["2026-10-20"], "planning_only": True}):
        with pytest.raises(cr.CostRegimeError):
            cr.planning_band_map(decl, register_path=path)
    with pytest.raises(cr.CostRegimeError):
        cr.planning_band_map(ok, register_path=tmp_path / "missing.json")
    # March data (before the pmxt window) is allowed as planning input: the window rule is the pmxt overlap only
    assert cr.planning_band_map({**ok, "data_window": ["2025-12-01", "2026-04-12"]}, register_path=path)


def test_write_register_refuses_cost_lowering_and_incomplete_family(tmp_path):
    for k, v in (("fee_rate_add", -0.001), ("half_spread_add", -0.001), ("a_AS_cents", -0.1), ("a_AS_cents", float("nan")), ("fee_rate_add", "a")):
        with pytest.raises(cr.CostRegimeError):
            cr.write_register(_payload(**{k: v}), tmp_path / "x.json")
    bad = _payload()
    del bad["measurements"]["E2"]
    with pytest.raises(cr.CostRegimeError):
        cr.write_register(bad, tmp_path / "x.json")
    with pytest.raises(cr.CostRegimeError):
        cr.write_register(_payload(family_M_complete=False), tmp_path / "x.json")
    bad = _payload()
    bad["measurements"]["N1"]["label"] = "replicated"
    with pytest.raises(cr.CostRegimeError):
        cr.write_register(bad, tmp_path / "x.json")
    assert not (tmp_path / "x.json").exists()
    ok = cr.write_register(_payload(), tmp_path / "ok.json")
    assert (tmp_path / "ok.json.sha256").read_text().strip() == ok["sha256"]
    with pytest.raises(FileExistsError):  # never overwritten
        cr.write_register(_payload(), tmp_path / "ok.json")


def test_kind_rules_and_counter_on_real_trials():
    for k in ("cb4_test", "cb4_replication", "cb4_measurement", "cb4_descriptive"):
        assert battery2.KIND_RULES[k][0] == battery2.EXCLUDE and len(battery2.KIND_RULES[k][1]) > 20
    out = battery2.cumulative_count()  # the real docs/research_lab/trials.jsonl; fails closed on an unknown kind
    assert out["total"] >= 900
