# ruff: noqa: E501
"""CB17 trial kinds are known to battery2 (section 2.5): cumulative_count fails closed on an unknown kind, and the q0400-q0403 lines are already in trials.jsonl."""

from __future__ import annotations

import json

from astrolabe.research_lab import battery2


def test_cb17_kinds_registered_and_excluded(tmp_path):
    for kind in ("cb17_test", "cb17_replication", "cb17_descriptive"):
        assert kind in battery2.KIND_RULES
        assert battery2.KIND_RULES[kind][0] == battery2.EXCLUDE
    p = tmp_path / "trials.jsonl"
    lines = [{"kind": "cb17_descriptive", "n_tests": 0, "source": "creative_batch_17:pre_census_A"},
             {"kind": "cb17_test", "n_tests": 0, "hypothesis": "B1"},
             {"kind": "cb17_replication", "n_tests": 0, "hypothesis": "B1-rep"}]
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    res = battery2.cumulative_count(p)
    assert res["total"] == 0
    assert set(res["by_kind"]) == {"cb17_test", "cb17_replication", "cb17_descriptive"}


def test_repo_trials_count_does_not_raise():
    assert battery2.cumulative_count()["total"] > 0
