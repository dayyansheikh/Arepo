# ruff: noqa: E501
"""Screening Batch 2 (SB2): cumulative multiple-testing trial counter (challenger change 1).

``battery.prior_test_count`` skips the ``hypothesis_battery_1`` ml_explain line and ignores several test-bearing
kinds, so it undercounts (598 where the corrected pre-SB2 base is 670). That function is unchanged (frozen past
runs use it). SB2 uses :func:`cumulative_count`, driven by the explicit :data:`KIND_RULES` table.

Rules: ``ONE`` = 1 per non-placebo line; ``N_TESTS`` = the line's ``n_tests`` (falling back to
``multiple_testing.m_tests``); ``EXCLUDE`` = 0, with a written reason (usually: the same tests are already
counted by another kind, so counting both would double count). Placebo lines (``evidence_role == "placebo"``)
always count 0. A kind absent from the table raises (fail closed).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import provenance

ONE = "one_per_line"
N_TESTS = "n_tests"
EXCLUDE = "exclude"

KIND_RULES: dict[str, tuple[str, str]] = {
    # --- counted by n_tests ---------------------------------------------------------------------
    "ml_explain": (
        N_TESTS,
        "every non-placebo ml_explain line (all sources, including hypothesis_battery_1 and the posthoc/"
        "replication lines) contributes n_tests, else multiple_testing.m_tests; this is the BY family size "
        "per run. Fixes the battery.prior_test_count skip of hypothesis_battery_1 (72 tests).",
    ),
    "econ_conditions_taker": (
        N_TESTS,
        "n_tests=95: BY was applied across 95 testable cells of BOTH parts (taker and maker), so the "
        "family is counted once, on the taker line.",
    ),
    # --- counted one per line -------------------------------------------------------------------
    "flow_screen": (ONE, "one screen run = one test (as battery.PRIOR_KIND_ONE)"),
    "leadlag_screen": (ONE, "one screen = one test (as battery.PRIOR_KIND_ONE)"),
    "comparison": (ONE, "one comparison = one test (as battery.PRIOR_KIND_ONE)"),
    "detector_eval": (ONE, "one detector evaluation = one test (as battery.PRIOR_KIND_ONE)"),
    "detector_eval_if_h1": (ONE, "one evaluation = one test (as battery.PRIOR_KIND_ONE)"),
    "e007_staleness_dev": (ONE, "one dev test (as battery.PRIOR_KIND_ONE)"),
    "calibration_study_c1": (ONE, "one study = one test (as battery.PRIOR_KIND_ONE)"),
    "dev_fit": (ONE, "one dev fit evaluated against a bar = one test (as battery.PRIOR_KIND_ONE)"),
    "history_cross_venue": (
        ONE,
        "each line is one analysis x subset/revision result with its own p / BY entry (82 lines); "
        "counted per line, conservatively (overlapping subsets are not netted out).",
    ),
    "surprise_detector": (
        ONE,
        "each line is one detector arm evaluated (p_one_sided / Holm); 46 lines, counted per arm. "
        "Conservative: includes fixed-rule and extension arms.",
    ),
    "if_h2_ladder_dev": (
        ONE,
        "one ladder study with bootstrap CIs on several targets; counted as a single dev test "
        "(conservative lower bound; sub-targets are not enumerated).",
    ),
    "history_case_timeline": (
        ONE,
        "descriptive per-case look at a pre-listed case; counted one per case as a conservative "
        "inclusion because detector alerts are read against it (challenger asked for history_case_*).",
    ),
    "history_case_controls": (ONE, "one case-control panel/rule look; counted as one (see history_case_timeline)"),
    # --- excluded (already counted elsewhere, or not a test) ------------------------------------
    "econ_conditions_maker": (
        EXCLUDE,
        "same BY family of 95 cells as econ_conditions_taker (n_tests=95 covers both parts); counting it "
        "again would double count.",
    ),
    "history_battery": (
        EXCLUDE,
        "72 per-hypothesis HB1 lines; the same 72 tests are the n_tests of the hypothesis_battery_1 "
        "ml_explain line, counted there.",
    ),
    "history_battery_replication": (
        EXCLUDE,
        "21 replication lines; their n_tests=21 is carried by the hypothesis_battery_1_replication "
        "ml_explain line.",
    ),
    "history_battery_posthoc": (
        EXCLUDE,
        "5 posthoc diagnostics; carried by ml_explain lines hypothesis_battery_1_posthoc (3) and "
        "hypothesis_battery_1_replication_posthoc (2).",
    ),
    "history_resolution_dev": (
        EXCLUDE,
        "summary of the T5 resolution_dev run; its tests are the n_tests=114 of the ml_explain "
        "'resolution_dev (T5) ablation' line.",
    ),
    "ml_fit": (
        EXCLUDE,
        "individual model fits (estimation, 6842 lines); the hypothesis tests derived from them are "
        "counted by the ml_explain line of the run (ml_explain.tests_by_family counts ablation/"
        "interaction/threshold/regime units, not fits).",
    ),
    "ml_score": (
        EXCLUDE,
        "per-arm scores of the same fits (193 lines); tests are counted via ml_explain, as ml_fit.",
    ),
    "surprise_labels": (EXCLUDE, "label specification fixed before features; no test"),
    "history_replication_declaration": (EXCLUDE, "pre-declaration of a replication; no test (tests counted when run)"),
}


def _tests_for(rec: dict, rule: str) -> int:
    if rule == ONE:
        return 1
    if rule == N_TESTS:
        n = rec.get("n_tests")
        if n is None:
            n = (rec.get("multiple_testing") or {}).get("m_tests", 0)
        return int(n or 0)
    return 0


def count_line(rec: dict) -> tuple[str, int]:
    """(kind, contribution) of one trial record; raises KeyError for an unknown kind."""
    kind = rec.get("kind")
    if kind not in KIND_RULES:
        raise KeyError(f"unknown trial kind {kind!r}: add it to battery2.KIND_RULES with a rule and reason")
    if rec.get("evidence_role") == "placebo":
        return kind, 0
    return kind, _tests_for(rec, KIND_RULES[kind][0])


def cumulative_count(path: Path = provenance.TRIALS_PATH) -> dict:
    """Total plus per-kind contributions; fails closed on an unknown kind. Unparseable lines are skipped."""
    by_kind: dict[str, int] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            kind, n = count_line(rec)
            by_kind[kind] = by_kind.get(kind, 0) + n
    return {
        "total": int(sum(by_kind.values())),
        "by_kind": dict(sorted(by_kind.items())),
        "rule_version": "battery2-count-v1",
    }
