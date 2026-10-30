import json

import pytest

from astrolabe.research_lab import battery2, provenance


def _w(tmp_path, recs):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    return p


def test_rule_types(tmp_path):
    p = _w(
        tmp_path,
        [
            {"kind": "ml_explain", "n_tests": 7, "source": "hypothesis_battery_1"},
            {"kind": "ml_explain", "multiple_testing": {"m_tests": 4}},
            {"kind": "flow_screen"},
            {"kind": "flow_screen"},
            {"kind": "econ_conditions_taker", "n_tests": 95},
            {"kind": "econ_conditions_maker", "n_tests": 95},
            {"kind": "ml_fit"},
            {"kind": "history_battery"},
        ],
    )
    r = battery2.cumulative_count(p)
    assert r["total"] == 7 + 4 + 2 + 95
    assert r["by_kind"]["econ_conditions_maker"] == 0
    assert r["by_kind"]["ml_fit"] == 0


def test_placebo_zero(tmp_path):
    p = _w(
        tmp_path,
        [
            {"kind": "ml_explain", "n_tests": 9, "evidence_role": "placebo"},
            {"kind": "flow_screen", "evidence_role": "placebo"},
        ],
    )
    assert battery2.cumulative_count(p)["total"] == 0


def test_unknown_kind_raises(tmp_path):
    with pytest.raises(KeyError):
        battery2.cumulative_count(_w(tmp_path, [{"kind": "brand_new_kind"}]))


def test_all_rules_have_reason():
    for kind, (rule, reason) in battery2.KIND_RULES.items():
        assert rule in (battery2.ONE, battery2.N_TESTS, battery2.EXCLUDE)
        assert len(reason) > 20, kind


def test_real_trials_log():
    p = provenance.TRIALS_PATH
    if not p.exists():
        pytest.skip("no trials log")
    kinds = {json.loads(x).get("kind") for x in open(p, encoding="utf-8") if x.strip()}
    assert kinds <= set(battery2.KIND_RULES)
    r = battery2.cumulative_count(p)
    print("cumulative total", r["total"])
    assert r["total"] >= 670
