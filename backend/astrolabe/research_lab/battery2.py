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

import dataclasses
import hashlib
import json
import math
import re
import subprocess
import time
from bisect import bisect_left, insort
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd

from . import battery as B
from . import history_backfill as hb
from . import ml_explain, provenance

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
    "live_tests3": (
        N_TESTS,
        "LT3 single analysis (E015-E019; LIVE_TESTS_3.md 1.11): one line, n_tests = k = the Holm primaries that "
        "survived their census gates; gate draws, secondaries, mechanism readings, economics and censuses are 0.",
    ),
    "live_tests4": (
        N_TESTS,
        "LT4 single analysis (E020-E024; LIVE_TESTS_4.md 1.11): one line, n_tests = k = the Holm primaries that "
        "survived their census gates; gate draws, secondaries, mechanism readings, economics and censuses are 0.",
    ),
    "copy_skilled": (
        N_TESTS,
        "E026 single analysis (copy skilled wallets with latency; LIVE_TESTS_COPY.md): one line, n_tests = 2 (the "
        "Holm primaries E026-N and E026-C; E026-N is itself net of costs, so no separate economics test); "
        "secondaries, the large-print arm, sensitivities and the planning census are 0.",
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
    "history_seal_declaration": (EXCLUDE, "data seal (CB1-F h5); no test"),
    "cb1_structural": (
        EXCLUDE,
        "CB1-D dev per-test lines (D1, D2); the tests are the n_tests of the ml_explain line "
        "'creative_batch_1:D', counted there. Placebo lines count 0.",
    ),
    "cb1_structural_replication": (
        EXCLUDE,
        "CB1 Stage-2 per-test lines (D rep, B1/B2); counted by the n_tests of the matching "
        "'creative_batch_1:D' / 'creative_batch_1:B' ml_explain line. Placebo lines count 0.",
    ),
    "cb1_structural_prospective": (
        EXCLUDE,
        "CB1-B3 stage-P line; the one test is the n_tests of the ml_explain line 'creative_batch_1:B3', "
        "counted there. Placebo lines count 0.",
    ),
    "cb1_history": (
        EXCLUDE,
        "CB1 A/C/E per-test lines; the tests are the n_tests of the ml_explain lines "
        "'creative_batch_1:A|C|E', counted there. Placebo lines count 0.",
    ),
    "cb1_history_replication": (
        EXCLUDE,
        "CB1 A/C/E Stage-2 per-test lines; counted by the n_tests of the matching ml_explain line. "
        "Placebo lines count 0.",
    ),
    "cb1_history_descriptive": (EXCLUDE, "CB1 A1 sports descriptive line; not a test"),
    "cb2_test": (
        EXCLUDE,
        "CB2 Stage-1 per-test lines (W2, W3, L1, X1, X2); the tests are the n_tests of the "
        "'creative_batch_2:<job>' ml_explain line, counted there. Placebo lines count 0.",
    ),
    "cb2_replication": (
        EXCLUDE,
        "CB2 Stage-2 per-test lines (W holdout, L/X replication); counted by the n_tests of the matching "
        "'creative_batch_2:<job>' ml_explain line. Placebo lines count 0.",
    ),
    "cb2_prospective": (
        EXCLUDE,
        "CB2 W stage-P per-test lines; counted by the n_tests of the matching 'creative_batch_2:*' "
        "ml_explain line. Placebo lines count 0.",
    ),
    "cb2_descriptive": (
        EXCLUDE,
        "CB2 descriptive lines (W1, census, P gate, comparators); no inference, not a test.",
    ),
    "cb3_test": (
        EXCLUDE,
        "CB3 Stage-1 per-test lines (A1, A2, B1-B6); the tests are the n_tests of the "
        "'creative_batch_3:<job>' ml_explain line, counted there. Placebo lines count 0.",
    ),
    "cb3_replication": (
        EXCLUDE,
        "CB3 Stage-2 per-test lines; counted by the n_tests of the matching 'creative_batch_3:<job>' "
        "ml_explain line. Placebo lines count 0.",
    ),
    "cb3_prospective": (
        EXCLUDE,
        "CB3 Stage-P per-test lines; counted by the n_tests of the matching 'creative_batch_3:*' "
        "ml_explain line. Placebo lines count 0.",
    ),
    "cb3_descriptive": (
        EXCLUDE,
        "CB3 descriptive lines (census, U baseline, sports stratum, reward scenarios, resolution marks); "
        "no inference, not a test.",
    ),
    "cb4_test": (
        EXCLUDE,
        "CB4 Stage-1 route per-test lines (C1, C2, S2, S3); the tests are the n_tests of the "
        "'creative_batch_4:C' / 'creative_batch_4:S' ml_explain lines, counted there. Placebo lines count 0.",
    ),
    "cb4_replication": (
        EXCLUDE,
        "CB4 Stage-2 route per-test lines; counted by the n_tests of the matching 'creative_batch_4:*' "
        "ml_explain line. Placebo lines count 0.",
    ),
    "cb4_measurement": (
        EXCLUDE,
        "CB4 family-M per-test lines (N1, N2, E1, E2; own Holm, k=4); the tests are the n_tests of the "
        "'creative_batch_4:M' ml_explain line, counted there. Placebo lines count 0.",
    ),
    "cb4_descriptive": (
        EXCLUDE,
        "CB4 descriptive lines (S1, band map, balanced-wallet share, gates, census, pilot, strata, "
        "sports strata); no inference, not a test.",
    ),
    "cb5_test": (
        EXCLUDE,
        "CB5 Stage-1 route per-test lines (G1, G2, L1); the tests are the n_tests of the "
        "'creative_batch_5:G' / 'creative_batch_5:L' ml_explain lines, counted there. Placebo lines count 0.",
    ),
    "cb5_replication": (
        EXCLUDE,
        "CB5 Stage-2 route per-test lines; counted by the n_tests of the matching 'creative_batch_5:*' "
        "ml_explain line. Placebo lines count 0.",
    ),
    "cb5_measurement": (
        EXCLUDE,
        "CB5 family-K per-test line (K1; two-sided, k=1) and the optional K1-R; the test is the n_tests of the "
        "'creative_batch_5:K' ml_explain line, counted there. Placebo lines count 0.",
    ),
    "cb5_descriptive": (
        EXCLUDE,
        "CB5 descriptive lines (census, seed strata, incidence and persistence curves, r_inc, sports strata, "
        "J4 wide-state counts, K activity controls, gates and reported variants); no inference, not a test.",
    ),
    "cb8_test": (
        EXCLUDE,
        "CB8 Stage-1 per-test lines (B1, W1, H1); counted by the matching 'creative_batch_8:*' ml_explain count line "
        "(n_tests). Placebo lines count 0.",
    ),
    "cb8_replication": (
        EXCLUDE,
        "CB8 Stage-2 per-test lines (B1-rep, W1-rep, H1-rep); counted by the matching 'creative_batch_8:*' ml_explain "
        "count line (n_tests). Placebo lines count 0.",
    ),
    "cb8_descriptive": (
        EXCLUDE,
        "CB8 descriptive lines (census, gates, strata, reported variants, attribution labels); no inference, not a test.",
    ),
    "cb9_test": (
        EXCLUDE,
        "CB9 Stage-1 per-test lines (S0, P1, P2, K1, D1, conditional S1); the tests are the n_tests of the "
        "'creative_batch_9:S|P|K|D' ml_explain count lines, counted there. Placebo lines count 0.",
    ),
    "cb9_replication": (
        EXCLUDE,
        "CB9 Stage-2 per-test lines (P1-rep, P2-rep, K1-rep, D1-rep); counted by the n_tests of the matching "
        "'creative_batch_9:*' ml_explain line. Placebo lines count 0.",
    ),
    "cb9_descriptive": (
        EXCLUDE,
        "CB9 descriptive lines (smoke, census, gates, strata, S0 feed-side column, P strike stratum, half-day "
        "poll, reported variants); no inference, not a test.",
    ),
    "cb10_test": (
        EXCLUDE,
        "CB10 Stage-1 per-test lines (D1, B1, B2); the tests are the n_tests of the 'creative_batch_10:D|B' ml_explain "
        "count lines, counted there. Placebo lines count 0.",
    ),
    "cb10_replication": (
        EXCLUDE,
        "CB10 Stage-2 per-test lines (D1-rep, D2, B1-rep, B2-rep); counted by the n_tests of the matching "
        "'creative_batch_10:*' ml_explain line. Placebo lines count 0.",
    ),
    "cb10_descriptive": (
        EXCLUDE,
        "CB10 descriptive lines (smoke, census, gates GD/GDP/GB/GB2, coverage audits, strata, DVOL / flat-smile / "
        "haircut variants, cascade descriptive); no inference, not a test.",
    ),
    "cb11_test": (
        EXCLUDE,
        "CB11 Stage-1 per-test lines (W1, W2, P1, P2, A1, A2); the tests are the n_tests of the 'creative_batch_11:W|P|A' ml_explain "
        "count lines, counted there. Placebo lines count 0.",
    ),
    "cb11_replication": (
        EXCLUDE,
        "CB11 Stage-2 per-test lines (W1-rep, W2-rep, P1-rep, P2-rep, A1-rep, A2-rep); counted by the n_tests of the matching "
        "'creative_batch_11:*' ml_explain line. Placebo lines count 0.",
    ),
    "cb11_descriptive": (
        EXCLUDE,
        "CB11 descriptive lines (smoke, census, gates GWC/GW/GW2/GP/GPP/GA0/GA, coverage audits, strata, variants, the on-chain proposer "
        "variant); no inference, not a test.",
    ),
    "cb12_test": (
        EXCLUDE,
        "CB12 Stage-1 per-test lines (M1, M2, E1, AL1, AL2, SH1, SH2, X1, O1, O2); the tests are the n_tests of the 'creative_batch_12:M|E|F|X|O' "
        "ml_explain count lines, counted there. Placebo lines count 0.",
    ),
    "cb12_replication": (
        EXCLUDE,
        "CB12 Stage-2 per-test lines (M1-rep, M2-rep, E1-rep, E2, AL/SH reps, O reps); counted by the n_tests of the matching "
        "'creative_batch_12:<family>:rep' ml_explain line. Placebo lines count 0.",
    ),
    "cb12_descriptive": (
        EXCLUDE,
        "CB12 descriptive lines (smoke, exclusion keys, census, gates GM/GMP/GE/GEP/GAL/GSH/GS15/GFP/GX/GO, coverage audits, strata, variants, the CH103 "
        "hidden-book census); no inference, not a test.",
    ),
    "cb13_test": (
        EXCLUDE,
        "CB13 Stage-1 per-test lines (T1, T2, R1); the tests are the n_tests of the 'creative_batch_13:T|R' ml_explain count lines, counted there. "
        "Placebo lines count 0.",
    ),
    "cb13_replication": (
        EXCLUDE,
        "CB13 Stage-2 per-test lines (T1-rep, T2-rep, T3, R1-rep, R2); counted by the n_tests of the matching 'creative_batch_13:<family>:rep' "
        "ml_explain line. Placebo lines count 0.",
    ),
    "cb13_descriptive": (
        EXCLUDE,
        "CB13 descriptive lines (smoke, labeller audit, census, gates GT/GL/GTP/GTI/GR/GRC/GRP, strata incl. SPORTS-FEED and SCHEDULED-EVENT, variants, "
        "pregate counts, cross-horizon implied sigma, Binance-Gamma agreement audit); no inference, not a test.",
    ),
    "cb14_test": (
        EXCLUDE,
        "CB14 Stage-1 per-test lines (W1, W2, S1, S2); the tests are the n_tests of the 'creative_batch_14:W|S' ml_explain count lines, counted there. "
        "Placebo lines count 0.",
    ),
    "cb14_replication": (
        EXCLUDE,
        "CB14 Stage-2 per-test lines (W1-rep, W2-rep, S1-rep, S2-rep); counted by the n_tests of the matching 'creative_batch_14:<family>:rep' "
        "ml_explain line. Placebo lines count 0.",
    ),
    "cb14_descriptive": (
        EXCLUDE,
        "CB14 descriptive lines (smoke, exclusion keys, audits, pre-gates, census, gates GW/GWP/GS/GSP, burst-rule grid, lead distribution, strata, "
        "latency, transcript-Gamma agreement); no inference, not a test.",
    ),
    "cb15_test": (
        EXCLUDE,
        "CB15 Stage-1 per-test lines (E1, E2, P1, P2); the tests are the n_tests of the 'creative_batch_15:E|P' ml_explain count lines, counted there. "
        "Placebo lines count 0.",
    ),
    "cb15_replication": (
        EXCLUDE,
        "CB15 Stage-2 per-test lines (P1-rep, P2-rep); counted by the n_tests of the 'creative_batch_15:P:rep' ml_explain line. Placebo lines count 0.",
    ),
    "cb15_descriptive": (
        EXCLUDE,
        "CB15 descriptive lines (smokes, GE0 and its audit, exclusion keys, pre-gates, censuses, gates GEI/GEC/GEP/GE/GPB/GP/GPP, strata, tiers, sign shares, "
        "Polymarket-first and sports pairs, seeded-history shares, gap-closure shares, latency, gap and storage logs, the CH125 withdrawal); no inference, not a test.",
    ),
    "cb16_test": (
        EXCLUDE,
        "CB16 Stage-1 per-test lines (Q1, U1); the tests are the n_tests of the 'creative_batch_16:Q|U' ml_explain count lines, counted there. "
        "Placebo lines count 0.",
    ),
    "cb16_replication": (
        EXCLUDE,
        "CB16 Stage-2 per-test lines (Q1-rep, Q2, U1-rep, U2); counted by the n_tests of the 'creative_batch_16:<Q|U>:rep' ml_explain lines. "
        "Placebo lines count 0.",
    ),
    "cb16_descriptive": (
        EXCLUDE,
        "CB16 descriptive lines (smoke, exclusion keys, the grain census, the K census, gates, strata, sports arms, shape descriptor, "
        "U validity sample, exclusion tables, decomposition, the H withdrawal record); no inference, not a test.",
    ),
    "cb17_test": (
        EXCLUDE,
        "CB17 Stage-1 per-test lines (B1, B2, C1; A1 only under branch S, withdrawn under branch T); the tests are the n_tests of the "
        "'creative_batch_17:B|C' ml_explain count lines, counted there. Placebo lines count 0.",
    ),
    "cb17_replication": (
        EXCLUDE,
        "CB17 Stage-2 per-test lines (B1-rep, B1-econ, B2-rep, B2-econ, C1-rep, C1-econ); counted by the n_tests of the "
        "'creative_batch_17:<B|C>:rep' ml_explain lines. Placebo lines count 0.",
    ),
    "cb17_descriptive": (
        EXCLUDE,
        "CB17 descriptive lines (pre-censuses q0400-q0403, the branch decision and the A withdrawal, smoke, exclusion keys, censuses, gates, "
        "strata, sports arms, the E census and re-entry verdict, the CH149 / CH155 maps, taker lines); no inference, not a test.",
    ),
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
    "bounce_decomp": (
        EXCLUDE,
        "SB2-J4 per-test lines (P1..P4, P1x); the 5 tests are the n_tests of the ml_explain line "
        "'screening_batch_2:J4', counted there. Placebo lines count 0.",
    ),
    "book_decomp": (
        EXCLUDE,
        "SB2-J3 per-test lines (B1-B4, D1, D2); the 6 tests are the n_tests of the ml_explain line "
        "'screening_batch_2:J3', counted there. Placebo lines count 0.",
    ),
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
    "history_battery2": (
        EXCLUDE,
        "13 per-hypothesis HB2 lines (J1); the same 13 tests are the n_tests of the ml_explain count line "
        "(source screening_batch_2:J1), counted there (as history_battery vs the HB1 count line).",
    ),
    "history_battery2_replication": (
        EXCLUDE,
        "per-test frozen-replication lines (J2 F/L, J6 X); their tests are the n_tests of the ml_explain "
        "count lines (source screening_batch_2:J2 / :J6), counted there.",
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
    "design_change": (EXCLUDE, "recorded design amendment (e.g. CB6 A-T1 top-up, 2026-10-17), n_tests 0; no test"),
    "history_replication_declaration": (EXCLUDE, "pre-declaration of a replication; no test (tests counted when run)"),
    "live_tests2": (
        N_TESTS,
        "LT2 single analysis (E012, E013-F4, E013-F5, E014; LIVE_TESTS_2.md): one line, n_tests = 8 = the 4 Holm "
        "primaries + the 4 declared paper-economics tests (precedent: economics lines are counted); descriptive "
        "companions and placebo/gate draws are not tests.",
    ),
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


# =============================================================================================
# HB2 (Screening Batch 2, J1/J2/J6): declared interaction screen on h2_main, frozen replication on h3
# See docs/research_lab/SCREENING_BATCH_2.md sections 2, J1, J2, J6. Exploratory_historical only.
# =============================================================================================

VERSION = "hb2-v1"
REVISION = "hb2_battery"
REVISION_R = "hb2_replication_h3"
EVIDENCE_ROLE = "exploratory_historical"
TRIAL_KIND = "history_battery2"
TRIAL_KIND_R = "history_battery2_replication"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "hb2_v1.json"
GATE_P = 0.01  # Stage 1: advance if one-sided p < 0.01 in the discovery sign
BY_Q = B.BY_Q  # 0.10, label only
HOLM_ALPHA = 0.05  # Stage 2 (h3), Holm over the advanced tests
H = 3600.0
DAY = 86400.0
# HB1 FL2 / FL3 frozen scalings (clip [-1, 1], divide by the h2-discovery SD): hb1_replication_v1.json
X6_CLIP, X6_SD = 1.0, 0.8578247852488129
X24_CLIP, X24_SD = 1.0, 0.8142193274031836
# F7 relative-size flow
Q_LOOKBACK_S = 30 * DAY
Q_MIN_PRIOR = 20
Q_PCT = 80.0
UNCLASSIFIED_MAX = 0.10
# stale-follower indicators
S_EPS = 0.005
# F3 end-date look-ahead sensitivity: drop markets closed more than this long before their listed end
CLOSED_EARLY_S = DAY
MIN_TERCILE_ROWS = 300
RV_EPS = 1e-4

TARGET_RE = re.compile(
    r"^(d|ya|y3|ok)_\d+$|^(res_excess|ok_res|dmid|y_class|y_absmove|target_available)$"
)


def is_target_col(c: str) -> bool:
    return bool(TARGET_RE.match(str(c)))


def assert_no_target_cols(cols) -> None:
    bad = [c for c in cols if is_target_col(c)]
    if bad:
        raise ValueError(f"derive2 may read origin-side columns only; target columns rejected: {bad}")


# --- declared hypotheses ---------------------------------------------------------------------------

POP_RULES2: dict[str, str] = {
    **B.POP_RULES,
    "n6h_tte": "f_n_6h >= 1 and ml_log_hours_to_end defined",
    "n6h_spr": "f_n_6h >= 1 and f_spread_proxy defined",
    "n6h_chg": "f_n_6h >= 1 and f_chg_6h defined",
    "n6h_size": "f_n_6h >= 1 and x_big6 and x_rest6 defined (30-day q80 with full lookback coverage)",
}


def pop_mask2(name: str, d: pd.DataFrame, base: pd.Series | None = None) -> pd.Series:
    """HB2 population ``name`` within ``base`` (default: rows with a trade before t)."""
    b = d["traded"] if base is None else base
    nn = pd.Series.notna
    m = {
        "n6h_tte": lambda: (d["f_n_6h"] >= 1) & nn(d["ml_log_hours_to_end"]),
        "n6h_spr": lambda: (d["f_n_6h"] >= 1) & nn(d["f_spread_proxy"]),
        "n6h_chg": lambda: (d["f_n_6h"] >= 1) & nn(d["f_chg_6h"]),
        "n6h_size": lambda: (d["f_n_6h"] >= 1) & nn(d["x_big6"]) & nn(d["x_rest6"]),
    }.get(name)
    if m is None:
        return B.pop_mask(name, d, base)
    return (b & m()).fillna(False).astype(bool)


def _H(*a, **k) -> B.Hyp:
    return B.Hyp(*a, **k)


C0 = B.C0
C0M = B.C0M
# prior = theory sign (+1/-1) where the table gives one, 0 where it says "discovery sign". The tested
# sign is always the discovery sign (run_beta); the prior is only reported (sign_agrees_with_prior).
HYPOTHESES2: tuple[B.Hyp, ...] = (
    _H("F1", "F", "beta", "d", 6, ("ix_F1",), "n6h", 0, controls=(*C0, "x6", "mod_F1"), scale="raw",
       text="6h flow x z(log1p 24h notional): liquidity moderates flow continuation (6h); overlaps IX3"),
    _H("F2", "F", "beta", "d", 6, ("ix_F2",), "n6h", 1, controls=(*C0, "x6", "mod_F2"), scale="raw",
       text="6h flow x z(log1p 6h trade count): breadth moderates continuation; overlaps IX3"),
    _H("F3", "F", "beta", "d", 6, ("ix_F3",), "n6h_tte", -1, controls=(*C0, "x6", "mod_F3"), scale="raw",
       text="6h flow x z(time to end): more continuation near resolution; partial re-test of IX4"),
    _H("F4", "F", "beta", "d", 6, ("ix_F4",), "n6h", 0, controls=(*C0, "x6", "mod_F4"), scale="raw",
       text="6h flow x z(log realised vol 1d): volatility moderates continuation"),
    _H("F5", "F", "beta", "d", 6, ("ix_F5",), "n6h_spr", 0, controls=(*C0, "x6", "mod_F5"), scale="raw",
       text="6h flow x z(spread proxy): spread moderates continuation"),
    _H("F6", "F", "beta", "d", 6, ("ix_F6",), "n6h_chg", 1, controls=(*C0, "x6", "U"), scale="raw",
       text="6h flow x U (flow not yet reflected in the 6h price change): unabsorbed flow continues more"),
    _H("F7", "F", "beta", "d", 6, ("xb6",), "n6h_size", 1, controls=(*C0, "xr6"), scale="raw",
       text="large-for-this-market trades (>= causal 30d q80) carry the flow information; rest as control"),
    _H("F8", "F", "beta", "d", 24, ("ix_F8",), "n24h", 0, controls=(*C0, "x24", "mod_F8"), scale="raw",
       text="24h flow x z(log1p 24h notional): liquidity moderates 24h continuation; overlaps IX3"),
    _H("L1", "L", "beta", "d", 24, ("ix_L1",), "all", 0, controls=(*C0, "mod_L1"), scale="raw",
       text="1d price change x z(log1p 24h notional): liquidity moderates momentum; re-test of E001 chg1d_x_logliq"),
    _H("L2", "L", "beta", "d", 24, ("ix_L2",), "all", 0, controls=(*C0M, "f_longshot", "mod_L2"), scale="raw",
       text="longshot x z(log1p 24h notional): is the longshot effect an illiquidity effect"),
    _H("X1", "X", "beta", "d", 2, ("ix_X1",), "nr_sib2", -1,
       controls=(*C0, "f_sib_nr_d2h", "S2"), scale="raw",
       text="neg-risk sibling 2h change x own market stale (no trade 2h, |own dmid| < 0.005)"),
    _H("X2", "X", "beta", "d", 2, ("ix_X2",), "co_sib2", 1,
       controls=(*C0, "f_sib_d2h", "S2"), scale="raw",
       text="co-event sibling 2h change x own market stale (diffusion to a stale follower)"),
    _H("X3", "X", "beta", "d", 24, ("ix_X3",), "nr_sib24", -1,
       controls=(*C0, "f_sib_nr_d24h", "S24"), scale="raw",
       text="neg-risk sibling 24h change x own market stale 24h (no trade 24h, |own 1d change| < 0.005)"),
)
assert len({h.hid for h in HYPOTHESES2}) == len(HYPOTHESES2) == 13
HMAP2 = {h.hid: h for h in HYPOTHESES2}
FAMILY_FL = ("F", "L")
FAMILY_X = ("X",)

# raw moderator definition per z-moderated hypothesis: (name, base term of the interaction)
MOD_SPEC: dict[str, tuple[str, str]] = {
    "F1": ("L", "x6"),
    "F2": ("K", "x6"),
    "F3": ("TTE", "x6"),
    "F4": ("RV", "x6"),
    "F5": ("SPR", "x6"),
    "F8": ("L", "x24"),
    "L1": ("L", "c1d"),
    "L2": ("L", "f_longshot"),
}
# flow variable whose continuation slope is compared across moderator terciles (fixed on h2)
TERCILE_FLOW = {"F1": "x6", "F2": "x6", "F3": "x6", "F4": "x6", "F5": "x6", "F8": "x24", "L1": "c_chg_1d"}
ECON_HYPS = ("F1", "F2", "F3", "F4", "F5", "F8")  # flow-following paper rule
# origin-side columns derive2 may read (never a target)
INPUT_COLS = (
    "f_imb_6h", "f_imb_24h", "f_N_24h", "f_n_6h", "f_n_2h", "f_n_24h", "ml_log_hours_to_end", "ml_rv_1d",
    "f_spread_proxy", "f_chg_6h", "ml_own_dmid_prev", "ml_chg_1d", "f_longshot", "f_quiet",
    "x_big6", "x_rest6", "f_sib_nr_d2h", "f_sib_nr_d24h", "f_sib_d2h",
)


def declaration_table2() -> list[dict]:
    return [
        {
            "id": h.hid, "family": h.family, "test": h.test, "target": h.target, "h": h.h, "x": list(h.x),
            "pop": h.pop, "prior": h.prior, "controls": list(h.controls), "scale": h.scale, "text": h.text,
        }
        for h in HYPOTHESES2
    ]


def declaration_sha256() -> str:
    pops = {h.pop: POP_RULES2[h.pop] for h in HYPOTHESES2}
    blob = json.dumps(
        {
            "version": VERSION, "split": B.SPLIT_TS, "embargo": B.EMBARGO_S,
            "gate_p": GATE_P, "by_q": BY_Q, "holm_alpha": HOLM_ALPHA,
            "constants": {
                "x6": [X6_CLIP, X6_SD], "x24": [X24_CLIP, X24_SD], "q80": [Q_LOOKBACK_S, Q_MIN_PRIOR, Q_PCT],
                "unclassified_max": UNCLASSIFIED_MAX, "s_eps": S_EPS, "closed_early_s": CLOSED_EARLY_S,
                "rv_eps": RV_EPS, "mod_spec": MOD_SPEC, "tercile_flow": TERCILE_FLOW, "inputs": list(INPUT_COLS),
            },
            "pops": pops, "hyps": declaration_table2(),
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()


# --- F7 relative-size flow features (streamed per market) -------------------------------------------


def q80_prior(
    ts: np.ndarray,
    n: np.ndarray,
    cov_from: float = -np.inf,
    lookback: float = Q_LOOKBACK_S,
    min_prior: int = Q_MIN_PRIOR,
    pct: float = Q_PCT,
) -> tuple[np.ndarray, np.ndarray]:
    """Causal per-trade q80 of USDC notional over the market's trades in ``[ts - lookback, ts)``
    (strictly earlier timestamps only; a trade never enters its own threshold). A trade is classified
    only if >= ``min_prior`` such trades exist AND the stored history is untruncated over the lookback
    (``cov_from`` <= ts - lookback; untruncated histories pass ``-inf``). Returns (q, classified)."""
    ts = np.asarray(ts, float)
    n = np.asarray(n, float)
    N = len(ts)
    q = np.full(N, np.nan)
    ok = np.zeros(N, bool)
    vals: list[float] = []
    queue: deque = deque()
    i = 0
    while i < N:
        j = i
        while j < N and ts[j] == ts[i]:
            j += 1
        t0 = ts[i]
        while queue and queue[0][0] < t0 - lookback:
            _, v = queue.popleft()
            del vals[bisect_left(vals, v)]
        k = len(vals)
        if cov_from <= t0 - lookback and k >= min_prior:
            pos = pct / 100.0 * (k - 1)
            lo = int(math.floor(pos))
            hi = min(lo + 1, k - 1)
            q[i:j] = vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)
            ok[i:j] = True
        for m in range(i, j):  # same-timestamp trades enter only after the whole group is classified
            if np.isfinite(n[m]):
                insort(vals, float(n[m]))
                queue.append((ts[m], float(n[m])))
        i = j
    return q, ok


def size_features(
    run_dir: Path,
    base: pd.DataFrame,
    shift_s: float = 0.0,
    log=None,
    progress: dict | None = None,
) -> pd.DataFrame:
    """``market_id, t_i, x_big6, x_rest6, n_classified_6h`` for every ``base`` origin (columns
    ``market_id``, ``t_i``). Windows are price-aligned (end at the last usable price point, shifted
    earlier by ``shift_s``); x_big6 / x_rest6 are the notional-weighted net imbalances of trades with
    notional >= / < their causal q80 (0.0 if the group is empty); NaN when the 6h window is not covered
    or more than 10% of its notional is unclassified. No target is read."""
    run_dir = Path(run_dir)
    if progress is None:
        progress = {}
        pp = run_dir / "progress.jsonl"
        if pp.exists():
            for line in pp.read_text().splitlines():
                if line.strip():
                    rec = json.loads(line)
                    progress[str(rec["market_id"])] = rec
    parts = []
    t_start = time.time()
    for i, (mid, g) in enumerate(base.groupby("market_id", sort=True)):
        t = np.sort(g["t_i"].to_numpy(float))
        nan = np.full(len(t), np.nan)
        res = {"x_big6": nan, "x_rest6": nan.copy(), "n_classified_6h": nan.copy()}
        tf = run_dir / "trades" / f"{mid}.csv.gz"
        if tf.exists():
            tr = hb.load_trades(tf)
            pf = run_dir / "prices" / f"{mid}.csv.gz"
            ts_p, v_p = hb.load_prices(pf) if pf.exists() else (np.array([]), np.array([]))
            p = progress.get(str(mid), {})
            cov_from = (
                float(p["trades_oldest_ts"])
                if p.get("trades_truncated") and p.get("trades_oldest_ts") is not None
                else -np.inf
            )
            if len(tr):
                T = B.Trades(tr, (ts_p, v_p), {}, None, cov_from)
                res = _window_size(T, ts_p, t, shift_s, cov_from)
        parts.append(pd.DataFrame({"market_id": mid, "t_i": t, **res}))
        if log and i % 200 == 0:
            log(f"size features: market {i} ({time.time() - t_start:.0f}s)")
    if not parts:
        return pd.DataFrame(columns=["market_id", "t_i", "x_big6", "x_rest6", "n_classified_6h"])
    return pd.concat(parts, ignore_index=True)


def _window_size(T, ts_p: np.ndarray, t: np.ndarray, shift_s: float, cov_from: float) -> dict:
    u = B._last_idx(ts_p, t) if len(ts_p) else np.full(len(t), -1)
    s_last = np.where(u >= 0, ts_p[np.maximum(u, 0)] if len(ts_p) else np.nan, np.nan)
    e = np.where(np.isfinite(s_last), s_last - shift_s, t - B.LAG - shift_s)
    q, clf = q80_prior(T.ts, T.n, cov_from)
    big = clf & (T.n >= q)
    rest = clf & ~big
    sn = T.sgn * T.n
    cum = {
        "Sb": B._cum(np.where(big, sn, 0.0)), "Nb": B._cum(np.where(big, T.n, 0.0)),
        "Sr": B._cum(np.where(rest, sn, 0.0)), "Nr": B._cum(np.where(rest, T.n, 0.0)),
        "Nu": B._cum(np.where(~clf, T.n, 0.0)), "Na": B._cum(T.n), "C": B._cum(clf.astype(float)),
    }
    a, b = e - 6 * H, e
    ia, ib = T.idx(a), T.idx(b)

    def w(k: str) -> np.ndarray:
        return cum[k][ib] - cum[k][ia]

    Na, Nu = w("Na"), w("Nu")
    valid = T.covered(a) & (Na > 0) & (Nu <= UNCLASSIFIED_MAX * Na)
    Nb, Nr = w("Nb"), w("Nr")
    with np.errstate(invalid="ignore", divide="ignore"):
        xb = np.where(valid, np.where(Nb > 0, w("Sb") / Nb, 0.0), np.nan)
        xr = np.where(valid, np.where(Nr > 0, w("Sr") / Nr, 0.0), np.nan)
    return {"x_big6": xb, "x_rest6": xr, "n_classified_6h": np.where(valid, w("C"), np.nan)}


# --- derivation ------------------------------------------------------------------------------------


def _raw_moderators(o: pd.DataFrame) -> dict[str, np.ndarray]:
    """Raw (unstandardised) moderators from origin-side columns only."""
    return {
        "L": np.log1p(o["f_N_24h"].to_numpy(float)),
        "K": np.log1p(o["f_n_6h"].to_numpy(float)),
        "TTE": o["ml_log_hours_to_end"].to_numpy(float),
        "RV": np.log(o["ml_rv_1d"].to_numpy(float) + RV_EPS),
        "SPR": o["f_spread_proxy"].to_numpy(float),
    }


def _base_terms(o: pd.DataFrame, spec: dict) -> dict[str, np.ndarray]:
    x6 = np.clip(o["f_imb_6h"].to_numpy(float), -X6_CLIP, X6_CLIP) / X6_SD
    x24 = np.clip(o["f_imb_24h"].to_numpy(float), -X24_CLIP, X24_CLIP) / X24_SD
    chg = o["f_chg_6h"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        U = np.where(np.isfinite(chg) & np.isfinite(x6), (np.sign(x6) * chg <= 0).astype(float), np.nan)
    n2, dprev = o["f_n_2h"].to_numpy(float), o["ml_own_dmid_prev"].to_numpy(float)
    n24, c1d = o["f_n_24h"].to_numpy(float), o["ml_chg_1d"].to_numpy(float)
    S2 = np.where(np.isfinite(n2) & np.isfinite(dprev), ((n2 == 0) & (np.abs(dprev) < S_EPS)).astype(float), np.nan)
    S24 = np.where(np.isfinite(n24) & np.isfinite(c1d), ((n24 == 0) & (np.abs(c1d) < S_EPS)).astype(float), np.nan)
    return {"x6": x6, "x24": x24, "U": U, "S2": S2, "S24": S24, "c1d": c1d,
            "f_longshot": o["f_longshot"].to_numpy(float)}


def derive2(d: pd.DataFrame, spec: dict, input_cols: tuple[str, ...] | list[str] | None = None) -> pd.DataFrame:
    """Add the HB2 columns (x6, x24, U, S2, S24, q_x6, xb6, xr6, mod_<id>, ix_<id>) in place and return
    ``d``. Only origin-side input columns are read (``INPUT_COLS``); a guard rejects any target column,
    so the interaction construction cannot touch an outcome."""
    cols = tuple(input_cols) if input_cols is not None else INPUT_COLS
    assert_no_target_cols(cols)
    assert_no_target_cols(spec.get("inputs", []))
    miss = [c for c in cols if c not in d.columns]
    if miss:
        raise KeyError(f"derive2 missing origin-side columns: {miss}")
    o = d[list(cols)]
    bt = _base_terms(o, spec)
    for k in ("x6", "x24", "U", "S2", "S24"):
        d[k] = bt[k]
    d["q_x6"] = o["f_quiet"].to_numpy(float) * bt["x6"]
    sd_b, sd_r = spec["f7"]["sd_big"], spec["f7"]["sd_rest"]
    d["xb6"] = o["x_big6"].to_numpy(float) / sd_b
    d["xr6"] = o["x_rest6"].to_numpy(float) / sd_r
    raw = _raw_moderators(o)
    for hid, (mod, term) in MOD_SPEC.items():
        hs = spec["hyps"][hid]
        z = (raw[mod] - hs["mod_mean"]) / hs["mod_sd"]
        d[f"mod_{hid}"] = z
        d[f"ix_{hid}"] = bt[term] * z
    d["ix_F6"] = bt["x6"] * bt["U"]
    d["ix_X1"] = o["f_sib_nr_d2h"].to_numpy(float) * bt["S2"]
    d["ix_X2"] = o["f_sib_d2h"].to_numpy(float) * bt["S2"]
    d["ix_X3"] = o["f_sib_nr_d24h"].to_numpy(float) * bt["S24"]
    return d


# --- spec (discovery rows only) --------------------------------------------------------------------


def spec_sha256(spec: dict) -> str:
    body = {k: v for k, v in spec.items() if k != "spec_sha256"}
    return hashlib.sha256(json.dumps(B._clean(body), sort_keys=True).encode()).hexdigest()


def file_sha256(path: Path) -> str | None:
    """sha256 of a file's bytes (streamed), or None when it does not exist."""
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def feature_hashes(paths: dict[str, Path]) -> dict[str, str | None]:
    return {k: file_sha256(p) for k, p in sorted(paths.items())}


def check_feature_hashes(spec: dict, paths: dict[str, Path]) -> None:
    """Refuse unless every feature file hashes to what ``fitspec`` recorded (absent stays absent)."""
    rec = spec.get("feature_sha256")
    if not isinstance(rec, dict) or not rec:
        raise SystemExit("refusing: spec has no feature_sha256 (re-run fitspec)")
    now = feature_hashes(paths)
    bad = sorted(k for k in set(rec) | set(now) if rec.get(k) != now.get(k))
    if bad:
        raise SystemExit(f"refusing: feature files changed since fitspec: {bad}")


def _needed_cols() -> list[str]:
    cols = set(INPUT_COLS) | set(C0) | {
        "market_id", "t_i", "mid_i", "event_c", "day_c", "split", "traded", "month", "fee_cat",
        "fee_category", "d_2", "d_6", "d_24", "ok_2", "ok_6", "ok_24", "close_epoch", "end_epoch",
        "sample_weight", "f_quiet", "c_chg_1d",
    }
    return sorted(cols)


def _disc_rows(d: pd.DataFrame, h: B.Hyp) -> np.ndarray:
    y, ok = B._target(d, h)
    m = (pop_mask2(h.pop, d) & ok).to_numpy() & np.isfinite(y) & np.isfinite(d[h.x[0]].to_numpy(float))
    Z = d[list(h.controls)].to_numpy(float)
    return m & np.all(np.isfinite(Z), axis=1) & (d["split"] == "disc").to_numpy()


def fit_spec(d_h2: pd.DataFrame, strict: bool = True) -> dict:
    """Freeze the quantities estimated on h2 **discovery rows only** (``split == 'disc'`` and a trade
    before t): per-hypothesis moderator mean / SD, F7 SDs, discovery signs, moderator tercile cuts and
    paper-rule thresholds. Judgement and embargo rows are dropped before anything is computed."""
    keep = [c for c in _needed_cols() if c in d_h2.columns]
    dd = d_h2.loc[(d_h2["split"] == "disc") & d_h2["traded"], keep].copy()
    spec: dict = {"version": VERSION, "declaration_sha256": declaration_sha256(), "inputs": list(INPUT_COLS),
                  "hyps": {}, "f7": {}}
    o = dd[list(INPUT_COLS)]
    raw = _raw_moderators(o)
    for hid, (mod, _term) in MOD_SPEC.items():
        m = pop_mask2(HMAP2[hid].pop, dd).to_numpy() & np.isfinite(raw[mod])
        v = raw[mod][m]
        if len(v) < 2 or not np.isfinite(v.std()) or v.std() == 0:
            if strict:
                raise ValueError(f"{hid}: too few discovery rows to standardise moderator {mod}")
            v = np.array([0.0, 1.0])
        spec["hyps"][hid] = {"mod": mod, "mod_mean": float(v.mean()), "mod_sd": float(v.std()), "n_z": int(len(v))}
    m7 = pop_mask2("n6h_size", dd).to_numpy()
    sb, sr = np.std(o["x_big6"].to_numpy(float)[m7]), np.std(o["x_rest6"].to_numpy(float)[m7])
    if not (np.isfinite(sb) and np.isfinite(sr) and sb > 0 and sr > 0):
        if strict:
            raise ValueError("F7: too few discovery rows to scale x_big6 / x_rest6")
        sb, sr = 1.0, 1.0
    spec["f7"] = {"sd_big": float(sb), "sd_rest": float(sr), "n": int(m7.sum())}
    derive2(dd, spec)
    ev, day = dd["event_c"].to_numpy(), dd["day_c"].to_numpy()
    for h in HYPOTHESES2:
        hs = spec["hyps"].setdefault(h.hid, {})
        m = _disc_rows(dd, h)
        hs["n_disc"] = int(m.sum())
        hs["sign"], hs["disc_beta"] = 0, None
        if m.sum() >= B.MIN_JUDGE_ROWS and len(pd.unique(ev[m])) >= B.MIN_JUDGE_CLUSTERS:
            y, _ = B._target(dd, h)
            r = B.beta_test(y[m], dd[h.x[0]].to_numpy(float)[m], dd[list(h.controls)].to_numpy(float)[m],
                            ev[m], day[m], None, n_boot=200)
            if r.get("testable") and r["beta"] != 0:
                hs["sign"], hs["disc_beta"] = int(np.sign(r["beta"])), float(r["beta"])
        if h.hid in TERCILE_FLOW:
            mod = dd[f"mod_{h.hid}"].to_numpy(float)
            pm = pop_mask2(h.pop, dd).to_numpy() & np.isfinite(mod)
            cuts = np.percentile(mod[pm], [100 / 3, 200 / 3])
            hs["tercile_cuts"] = [float(c) for c in cuts]
            flow = np.abs(dd[TERCILE_FLOW[h.hid]].to_numpy(float))
            edges = [(-np.inf, cuts[0]), (cuts[0], cuts[1]), (cuts[1], np.inf)]
            taus = []
            for lo, hi in edges:
                s = pm & (mod > lo) & (mod <= hi) & np.isfinite(flow)
                taus.append(float(np.percentile(flow[s], 90)) if s.sum() else None)
            hs["econ_tau"] = taus
    spec["spec_sha256"] = spec_sha256(spec)
    return spec


def load_spec(path: Path = SPEC_PATH) -> dict:
    spec = json.loads(Path(path).read_text())
    if spec.get("spec_sha256") != spec_sha256(spec):
        raise ValueError("hb2 spec_sha256 does not match its content (file modified)")
    return spec


def _is_committed(path: Path) -> bool:
    root = provenance.REPO_ROOT
    try:
        rel = str(Path(path).resolve().relative_to(root))
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root,
                                 capture_output=True, text=True, timeout=30)
        dirty = subprocess.run(["git", "status", "--porcelain", "--", rel], cwd=root,
                               capture_output=True, text=True, timeout=30)
        return tracked.returncode == 0 and dirty.stdout.strip() == ""
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def require_frozen_spec(path: Path = SPEC_PATH, *, committed: bool = True) -> dict:
    """Load the spec and refuse unless its declaration hash equals the code's (and, by default, the file
    is committed and unmodified)."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"refusing: {p} does not exist (run 'fitspec' on the host, review, commit it)")
    spec = load_spec(p)
    if spec.get("declaration_sha256") != declaration_sha256():
        raise SystemExit("refusing: hb2 spec declaration hash differs from the code's declaration hash")
    if committed and not _is_committed(p):
        raise SystemExit(f"refusing: {p} is not committed (or has local changes); commit the reviewed spec first")
    return spec


# --- running ---------------------------------------------------------------------------------------

PERM_COLS = ("d_2", "d_6", "d_24")


def run_all2(
    d: pd.DataFrame,
    spec: dict,
    n_boot: int,
    threads: int = 1,
    y_perm_seed: int | None = None,
    log=print,
    only: set[str] | None = None,
) -> dict:
    """Run every declared HB2 test with ``battery.run_beta`` (one-sided in the discovery sign).
    ``y_perm_seed``: globally permute every target first (calibration placebo / dry run). Adds the
    Stage-1 verdict (``advance``) to each result. ``threads`` is accepted for CLI symmetry."""
    if "ix_F1" not in d.columns:
        derive2(d, spec)
    over = {}
    if y_perm_seed is not None:
        rng = np.random.default_rng(y_perm_seed)
        for col in PERM_COLS:
            v = d[col].to_numpy(float).copy()
            fin = np.isfinite(v)
            v[fin] = v[fin][rng.permutation(int(fin.sum()))]
            over[col] = v
    results: dict = {}
    for h in HYPOTHESES2:
        if only and h.hid not in only:
            continue
        t0 = time.time()
        r = B.run_beta(d, h, pop_mask2(h.pop, d), n_boot, y_override=over.get(f"d_{h.h}"))
        r["seconds"] = round(time.time() - t0, 1)
        r["prior_theory_sign"] = h.prior
        if h.prior and r.get("sign_tested"):
            r["sign_agrees_with_prior"] = bool(r["sign_tested"] == h.prior)
        if y_perm_seed is None and r.get("sign_source") == "discovery":
            frozen = spec["hyps"][h.hid].get("sign")
            if frozen is not None and frozen != r["sign_tested"]:
                raise RuntimeError(f"{h.hid}: discovery sign {r['sign_tested']} differs from frozen spec {frozen}")
        r["advance"] = stage1_advance(r)
        results[h.hid] = r
        log(f"  {h.hid:3s} p={r.get('p', 1.0):.3g} eff={r.get('effect')} n_j={r.get('n_judge')} adv={r['advance']}")
    return results


def stage1_advance(r: dict) -> bool:
    """Stage-1 gate: testable, discovery-signed, one-sided p < 0.01."""
    return bool(r.get("testable", True) and r.get("sign_source") == "discovery" and float(r.get("p", 1.0)) < GATE_P)


def apply_by2(results: dict, m_total: int) -> dict:
    """BY label (q = 0.10) over the cumulative denominator; a label only, never the gate."""
    return B.apply_by(results, m_total)


def end_date_keep(d: pd.DataFrame) -> pd.Series:
    """F3 look-ahead sensitivity filter: False for markets whose frame closed time is more than 24h
    before the listed end (their true end leaked into ``ml_log_hours_to_end``)."""
    ce, ee = d["close_epoch"].to_numpy(float), d["end_epoch"].to_numpy(float)
    early = np.isfinite(ce) & np.isfinite(ee) & ((ee - ce) > CLOSED_EARLY_S)
    return pd.Series(~early, index=d.index)


def _row_summary(r: dict) -> dict:
    keys = ("beta", "effect", "se_event", "ci_event_boot", "p", "n", "n_judge", "n_event", "testable", "sign_tested")
    return {k: r.get(k) for k in keys if k in r}


def enddate_check(d: pd.DataFrame, h: B.Hyp, res: dict, n_boot: int) -> dict:
    keep = end_date_keep(d)
    r = B.run_beta(d, h, pop_mask2(h.pop, d) & keep, n_boot)
    base, sub = res.get("effect"), r.get("effect")
    flip = bool(base is not None and sub is not None and np.sign(base) != np.sign(sub))
    half = bool(base and sub is not None and abs(sub) < 0.5 * abs(base))
    return {
        "rerun": _row_summary(r),
        "markets_excluded": int(d.loc[~keep, "market_id"].nunique()),
        "sign_flip": flip,
        "estimate_halved": half,
        "verdict": "not robust to end-date look-ahead" if (flip or half) else "robust to end-date look-ahead",
    }


def joint_quiet_check(d: pd.DataFrame, h: B.Hyp, res: dict, n_boot: int) -> dict:
    """F1/F2/F8 vs IX3: refit with f_quiet and f_quiet x x6 added as controls."""
    h2 = dataclasses.replace(h, controls=(*h.controls, "f_quiet", "q_x6"))
    mask = pop_mask2(h.pop, d) & d["f_quiet"].notna()
    r = B.run_beta(d, h2, mask, n_boot)
    base, sub = res.get("effect"), r.get("effect")
    return {"rerun": _row_summary(r), "ratio_to_primary": None if not base or sub is None else float(sub / base),
            "survives_p_lt_0.05": bool(r.get("p", 1.0) < 0.05)}


def _tercile_masks(mod: np.ndarray, cuts: list[float]) -> list[np.ndarray]:
    return [mod <= cuts[0], (mod > cuts[0]) & (mod <= cuts[1]), mod > cuts[1]]


def tercile_slopes(d: pd.DataFrame, h: B.Hyp, spec: dict, rows: np.ndarray, n_boot: int = 500) -> dict | None:
    """Continuation slope of the flow variable inside each moderator tercile (cuts frozen from h2
    discovery rows) on ``rows``. Returns None for hypotheses without a continuous moderator."""
    hs = spec["hyps"].get(h.hid, {})
    if h.hid not in TERCILE_FLOW or "tercile_cuts" not in hs:
        return None
    flow_col = TERCILE_FLOW[h.hid]
    y, _ = B._target(d, h)
    flow = d[flow_col].to_numpy(float)
    mod = d[f"mod_{h.hid}"].to_numpy(float)
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    out = {}
    for k, tm in enumerate(_tercile_masks(mod, hs["tercile_cuts"])):
        m = rows & tm & np.isfinite(y) & np.isfinite(flow) & np.isfinite(mod)
        if m.sum() < MIN_TERCILE_ROWS or len(pd.unique(ev[m])) < B.MIN_JUDGE_CLUSTERS:
            out[str(k)] = {"testable": False, "n": int(m.sum())}
            continue
        Z = d[[*C0, f"mod_{h.hid}"]].to_numpy(float)[m]
        r = B.beta_test(y[m], flow[m], Z, ev[m], day[m], None, n_boot=n_boot)
        out[str(k)] = _row_summary(r) if r.get("testable") else {"testable": False, "n": int(m.sum())}
    ok = {k: v for k, v in out.items() if v.get("beta") is not None}
    fav = max(ok, key=lambda k: ok[k]["beta"]) if ok else None
    return {"flow": flow_col, "slopes": out, "favourable_tercile": None if fav is None else int(fav),
            "direction_sign": None if fav is None else int(np.sign(ok[fav]["beta"])),
            "note": "chosen on h2 judgement; frozen for h3, never re-chosen"}


def _by_subsets(d: pd.DataFrame, h: B.Hyp, rows: np.ndarray) -> dict:
    out: dict = {"by_category": {}, "by_month": {}}
    for c in sorted(d.loc[rows, "fee_cat"].dropna().unique()):
        out["by_category"][c] = B._subset_beta(d, h, pop_mask2(h.pop, d), rows & (d["fee_cat"] == c).to_numpy())
    for mo in sorted(d.loc[rows, "month"].unique()):
        out["by_month"][mo] = B._subset_beta(d, h, pop_mask2(h.pop, d), rows & (d["month"] == mo).to_numpy())
    return out


def robustness2(d: pd.DataFrame, h: B.Hyp, res: dict, spec: dict, d_shift: pd.DataFrame | None, n_boot: int,
                shared_events: set[str] | None = None) -> dict:
    """Declared robustness on an advanced test (h2): sign by month and fee category, flow windows ending
    30 min earlier, F3 end-date look-ahead, F1/F2/F8 joint control with f_quiet, favourable tercile."""
    judge = (d["split"] == "judge").to_numpy()
    out: dict = _by_subsets(d, h, judge)
    shared = d["event_c"].isin(shared_events or set()).to_numpy()
    out["excl_shared_events"] = B._subset_beta(d, h, pop_mask2(h.pop, d), judge & ~shared)
    out["n_shared_events_in_judge"] = int(d.loc[judge & shared, "event_c"].nunique())
    if h.hid == "F7":
        xb, xr = d["x_big6"].to_numpy(float), d["x_rest6"].to_numpy(float)
        fin = np.isfinite(xb) & np.isfinite(xr)
        pm = pop_mask2(h.pop, d).to_numpy() & judge & fin
        out["f7_empty_groups"] = {
            "rows": int(pm.sum()),
            "share_empty_big": float(np.mean(xb[pm] == 0)) if pm.any() else None,
            "share_empty_rest": float(np.mean(xr[pm] == 0)) if pm.any() else None,
            "share_either_empty": float(np.mean((xb[pm] == 0) | (xr[pm] == 0))) if pm.any() else None,
        }
        out["f7_both_groups_nonempty"] = B._subset_beta(d, h, pop_mask2(h.pop, d), judge & fin & (xb != 0) & (xr != 0))
    if d_shift is not None:
        out["flow_window_end_minus_30min"] = B._subset_beta(
            d_shift, h, pop_mask2(h.pop, d_shift), (d_shift["split"] == "judge").to_numpy())
    else:
        out["flow_window_end_minus_30min"] = {"available": False}
    if h.hid == "F3":
        out["end_date_lookahead"] = enddate_check(d, h, res, n_boot)
    if h.hid in ("F1", "F2", "F8"):
        out["joint_control_f_quiet"] = joint_quiet_check(d, h, res, n_boot)
    disc, jm, _ = res["_masks"]
    out["favourable_tercile"] = tercile_slopes(d, h, spec, jm)
    return out


def _load_cols(path: Path, columns: list[str]) -> pd.DataFrame:
    import pyarrow.parquet as pq

    have = set(pq.read_schema(path).names)
    return B.read_features(path, [c for c in columns if c in have])


def run_main2(
    d: pd.DataFrame, spec: dict, d_shift: pd.DataFrame | None, n_boot: int, threads: int, out_dir: Path, log=print,
    shared_events: set[str] | None = None,
) -> int:
    path = Path(out_dir) / "results_hb2.json"
    if path.exists():
        raise SystemExit(f"refusing: {path} exists (results are never overwritten)")
    prior = cumulative_count()
    m_total = prior["total"] + len(HYPOTHESES2)
    log(f"cumulative prior {prior['total']}; m_total {m_total}; declaration {declaration_sha256()}")
    derive2(d, spec)
    res = run_all2(d, spec, n_boot, threads, log=log)
    by = apply_by2(res, m_total)
    adv = sorted(k for k, v in res.items() if v["advance"])
    if d_shift is not None:
        derive2(d_shift, spec)
    extra = {}
    for hid in adv:
        log(f"  robustness for {hid}")
        extra[hid] = robustness2(d, HMAP2[hid], res[hid], spec, d_shift, n_boot, shared_events)
    log("calibration placebo: whole battery on globally permuted targets")
    plc = run_all2(d, spec, 200, threads, y_perm_seed=B.SEED + 1, log=log)
    plc_p = {k: float(v.get("p", 1.0)) for k, v in plc.items()}
    out = {
        "version": VERSION, "revision": REVISION, "evidence_role": EVIDENCE_ROLE,
        "declaration_sha256": declaration_sha256(), "spec_sha256": spec["spec_sha256"],
        "stage1_gate": {"rule": "one-sided p < 0.01 in the discovery sign", "p": GATE_P},
        "prior_tests": prior, "m_total": m_total, "results": res, "by": by,
        "advanced": adv,
        "advanced_FL": [k for k in adv if HMAP2[k].family in FAMILY_FL],
        "advanced_X": [k for k in adv if HMAP2[k].family in FAMILY_X],
        "robustness": extra,
        "favourable_tercile": {k: (extra[k].get("favourable_tercile") or {}) for k in extra
                               if extra[k].get("favourable_tercile")},
        "placebo_global_permutation": {
            "p_values": plc_p,
            "share_p_lt_0.05": float(np.mean([p < 0.05 for p in plc_p.values()])),
            "advanced": sorted(k for k, v in plc.items() if v["advance"]),
        },
        "reads_note": "h2_main screening beyond the revision budget; L1 at most; nothing here is confirmation",
        "provenance": provenance.run_provenance(),
    }
    path.write_text(json.dumps(B._clean(out), indent=1))
    log_trials(out, path)
    log(f"advanced (p < {GATE_P}): {adv}; BY survivors: {by['survivors']}; wrote {path}")
    return 0


# --- replication (frozen definitions only) ---------------------------------------------------------


def _frozen_rows(d: pd.DataFrame, h: B.Hyp) -> np.ndarray:
    y, ok = B._target(d, h)
    m = (pop_mask2(h.pop, d) & ok).to_numpy() & np.isfinite(y) & np.isfinite(d[h.x[0]].to_numpy(float))
    return m & np.all(np.isfinite(d[list(h.controls)].to_numpy(float)), axis=1)


def beta_frozen2(
    d: pd.DataFrame, h: B.Hyp, sign: int, rows: np.ndarray, weighted: bool, n_boot: int, controls: tuple | None = None
) -> dict:
    y, _ = B._target(d, h)
    x = d[h.x[0]].to_numpy(float)
    ctl = list(controls if controls is not None else h.controls)
    Z = d[ctl].to_numpy(float)
    ev, day = d["event_c"].to_numpy(), d["day_c"].to_numpy()
    # Same finite-control convention as battery.run_beta (zok): rows with a non-finite control are dropped
    # and counted. For the default frozen controls ``rows`` is already finite, so this drops nothing.
    fin = np.all(np.isfinite(Z), axis=1) if Z.size else np.ones(len(d), bool)
    n_drop = int((rows & ~fin).sum())
    rows = rows & fin
    nz = rows & (x != 0)
    out = {"n_dropped_nonfinite_controls": n_drop, "n_rows": int(rows.sum()), "n_nonzero": int(nz.sum()), "n_nonzero_events": int(len(pd.unique(ev[nz])))}
    if (rows.sum() < B.MIN_JUDGE_ROWS or len(pd.unique(ev[rows])) < B.MIN_JUDGE_CLUSTERS
            or out["n_nonzero"] < B.MIN_NONZERO_ROWS or out["n_nonzero_events"] < B.MIN_NONZERO_CLUSTERS):
        return {**out, "testable": False, "p": 1.0, "reason": "too few rows/clusters/nonzero"}
    w = d["sample_weight"].to_numpy(float)[rows] if weighted else None
    r = B.beta_test(y[rows], x[rows], Z[rows], ev[rows], day[rows], int(sign), n_boot=n_boot, w=w)
    if not r.get("testable"):
        return {**out, **r, "p": 1.0}
    return {**out, **r, "effect": r["beta"]}


def _paper_cost(d: pd.DataFrame, pick: np.ndarray, sgn: np.ndarray, h: B.Hyp) -> dict:
    sub = d.loc[pick]
    dh = d[f"d_{h.h}"].to_numpy(float)[pick]
    m0 = sub["mid_i"].to_numpy(float)
    m1 = m0 + dh
    gross = sgn * dh
    spread = B._band_spread(m0)
    rates = np.array([B.fee_rate(c) for c in sub["fee_category"].fillna("unknown")])
    pe = np.where(sgn > 0, m0, 1 - m0)
    px = np.clip(np.where(sgn > 0, m1, 1 - m1), 0, 1)
    fee = rates * (pe * (1 - pe) + px * (1 - px))
    ev, day = sub["event_c"].to_numpy(), sub["day_c"].to_numpy()
    rg, rn = B.mean_test(gross, ev, day, 1, n_boot=1000), B.mean_test(gross - spread - fee, ev, day, 1, n_boot=1000)
    ro = B.mean_test(gross - spread / 2.0, ev, day, 1, n_boot=1000)
    return {
        "applicable": True, "testable": True, "n_trades": int(pick.sum()), "n_events": rn["n_event"],
        "mean_gross": rg["mean"], "gross_ci": rg["ci_event_boot"], "mean_spread": float(spread.mean()),
        "mean_fee": float(fee.mean()), "mean_net_taker": rn["mean"], "net_taker_ci": rn["ci_event_boot"],
        "mean_net_half_spread_no_fee": ro["mean"], "net_half_spread_ci": ro["ci_event_boot"],
        "hit_rate": float((gross > 0).mean()),
        "note": "optimistic, not tradable: paper only, mid-to-mid gross, favourable tercile fixed on h2",
    }


def economics_tercile(d: pd.DataFrame, h: B.Hyp, spec: dict, rows: np.ndarray, fav: dict | None) -> dict:
    hs = spec["hyps"].get(h.hid, {})
    if h.hid not in ECON_HYPS or not fav or fav.get("favourable_tercile") is None or "econ_tau" not in hs:
        return {"applicable": False, "reason": "no flow-following paper rule or no h2 favourable tercile"}
    k = int(fav["favourable_tercile"])
    tau = hs["econ_tau"][k]
    flow = d[TERCILE_FLOW[h.hid]].to_numpy(float)
    mod = d[f"mod_{h.hid}"].to_numpy(float)
    tm = _tercile_masks(mod, hs["tercile_cuts"])[k]
    pick = rows & tm & np.isfinite(flow) & (flow != 0) & (np.abs(flow) >= tau)
    if pick.sum() < 30:
        return {"applicable": True, "testable": False, "n_trades": int(pick.sum())}
    sgn = np.sign(flow[pick]) * float(fav["direction_sign"])
    return _paper_cost(d, pick, sgn, h)


def replicate(
    d_h3: pd.DataFrame,
    spec: dict,
    advanced: list[str],
    n_boot: int = 2000,
    log=print,
    shared_events: set[str] | None = None,
    h2_results: dict | None = None,
    d_shift: pd.DataFrame | None = None,
) -> dict:
    """Frozen-definition replication on h3: every definition, scaling, z parameter, cut and sign comes
    from ``spec`` (h2 discovery); nothing is re-estimated on h3. All h3 primary rows. Holm 0.05 over the
    ``advanced`` tests, one-sided in the h2 direction. Secondaries: sample-weighted, pre/post 2026-07-01
    windows, without the events shared with h2, F3 end-date look-ahead, F1/F2/F8 joint control, sign by
    month and category, shifted flow windows (if supplied), and the paper rule in the h2 favourable tercile."""
    derive2(d_h3, spec)
    if d_shift is not None:
        derive2(d_shift, spec)
    shared = d_h3["event_c"].isin(shared_events or set()).to_numpy()
    pre, post = (d_h3["split"] == "disc").to_numpy(), (d_h3["split"] == "judge").to_numpy()
    tests: dict = {}
    for hid in advanced:
        h = HMAP2[hid]
        sign = int(spec["hyps"][hid]["sign"])
        rows = _frozen_rows(d_h3, h)
        rr = {
            "sign_frozen": sign,
            "primary": beta_frozen2(d_h3, h, sign, rows, False, n_boot),
            "weighted": beta_frozen2(d_h3, h, sign, rows, True, n_boot),
            "pre_split_window": beta_frozen2(d_h3, h, sign, rows & pre, False, 500),
            "post_split_window": beta_frozen2(d_h3, h, sign, rows & post, False, 500),
            "excl_shared_events": beta_frozen2(d_h3, h, sign, rows & ~shared, False, 500),
        }
        if d_shift is not None:
            rs = _frozen_rows(d_shift, h)
            rr["flow_window_end_minus_30min"] = beta_frozen2(d_shift, h, sign, rs, False, 500)
        else:
            rr["flow_window_end_minus_30min"] = {"available": False}
        rr["sign_by_slice"] = _by_subsets(d_h3, h, rows)
        if hid == "F3":
            keep = end_date_keep(d_h3).to_numpy()
            sub = beta_frozen2(d_h3, h, sign, rows & keep, False, 500)
            e0, e1 = rr["primary"].get("effect"), sub.get("effect")
            rr["end_date_lookahead"] = {
                "rerun": _row_summary(sub),
                "markets_excluded": int(d_h3.loc[~keep, "market_id"].nunique()),
                "verdict": "not robust to end-date look-ahead"
                if (e0 and e1 is not None and (np.sign(e0) != np.sign(e1) or abs(e1) < 0.5 * abs(e0)))
                else "robust to end-date look-ahead",
            }
        if hid in ("F1", "F2", "F8"):
            qrows = rows & d_h3["f_quiet"].notna().to_numpy()
            rr["joint_control_f_quiet"] = beta_frozen2(
                d_h3, h, sign, qrows, False, 500, controls=(*h.controls, "f_quiet", "q_x6"))
        h2e = ((h2_results or {}).get("robustness", {}).get(hid, {}) or {}).get("favourable_tercile")
        rr["h2_favourable_tercile"] = h2e
        h2_eff = ((h2_results or {}).get("results", {}).get(hid, {}) or {}).get("effect")
        e = rr["primary"].get("effect")
        rr["ratio_to_h2"] = None if e is None or not h2_eff else float(e / h2_eff)
        tests[hid] = rr
        p = rr["primary"]
        log(f"  {hid:3s} p={p.get('p', 1.0):.3g} eff={e} ratio={rr['ratio_to_h2']} n={p.get('n', p.get('n_rows'))}")
    holm = ml_explain.holm({k: float(v["primary"].get("p", 1.0)) for k, v in tests.items()}) if tests else {}
    holm_w = ml_explain.holm({k: float(v["weighted"].get("p", 1.0)) for k, v in tests.items()}) if tests else {}
    replicated = sorted(k for k, v in holm.items()
                        if v["reject_5pct"] and tests[k]["primary"].get("sign_tested") == tests[k]["sign_frozen"])
    for k in replicated:
        rows = _frozen_rows(d_h3, HMAP2[k])
        tests[k]["economics_favourable_tercile"] = economics_tercile(
            d_h3, HMAP2[k], spec, rows, tests[k]["h2_favourable_tercile"])
    return {
        "tests": tests, "holm_primary": holm, "holm_weighted": holm_w, "replicated_primary": replicated,
        "replicated_weighted": sorted(k for k, v in holm_w.items() if v["reject_5pct"]),
        "verdict_label": "development-replicated (L2-dev) = Holm 0.05 pass, same sign; never confirmation",
    }


# --- trial log -------------------------------------------------------------------------------------


def log_trials(out: dict, path: Path, *, replication: bool = False, job: str | None = None,
               trials_path: Path = provenance.TRIALS_PATH) -> None:
    """One ``history_battery2`` / ``history_battery2_replication`` line per test (counted 0 by KIND_RULES)
    plus one ``ml_explain`` count line carrying ``n_tests`` (the single place each test is counted).
    The J1 placebo is one line with evidence_role 'placebo' (counts 0)."""
    sha = provenance.sha256_file(path)
    dsha = declaration_sha256()
    if not replication:
        job = job or "J1"
        for hid, r in out["results"].items():
            h = HMAP2[hid]
            provenance.append_trial({
                "kind": TRIAL_KIND, "label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE, "revision": REVISION,
                "dataset": "history:h2_main", "hypothesis": hid, "family": h.family, "test": h.test,
                "target": h.target, "horizon_hours": h.h, "features": list(h.x), "population": h.pop,
                "sign_tested": r.get("sign_tested"), "effect": B._clean(r.get("effect")), "p": B._clean(r.get("p")),
                "advance": bool(r.get("advance")), "p_by_cumulative": B._clean(r.get("p_by_cumulative")),
                "pass_by_cumulative": r.get("pass_by_cumulative"), "testable": r.get("testable", True),
                "n_judge": r.get("n_judge"), "m_total": out["m_total"], "declaration_sha256": dsha,
                "spec_sha256": out["spec_sha256"], "results_sha256": sha, "data_provenance": hb.PROVENANCE,
            }, trials_path)
        provenance.append_trial({
            "kind": TRIAL_KIND, "label": "EXPLORATORY", "evidence_role": "placebo", "revision": REVISION,
            "dataset": "history:h2_main", "hypothesis": "ALL", "note": "global-permutation calibration placebo",
            "advanced": out["placebo_global_permutation"]["advanced"],
            "share_p_lt_0.05": out["placebo_global_permutation"]["share_p_lt_0.05"],
            "declaration_sha256": dsha, "results_sha256": sha,
        }, trials_path)
        n_tests = len(out["results"])
        fam: dict[str, int] = {}
        for h in HYPOTHESES2:
            fam[f"hb2:{h.family}"] = fam.get(f"hb2:{h.family}", 0) + 1
        provenance.append_trial({
            "kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE,
            "source": f"screening_batch_2:{job}", "revision": REVISION, "dataset": "history:h2_main",
            "n_tests": n_tests, "n_tests_by_family": fam,
            "multiple_testing": {"by_q": BY_Q, "m_tests": n_tests, "prior_tests": out["prior_tests"]["total"],
                                 "m_total": out["m_total"]},
            "advanced": out["advanced"], "survivors": out["by"]["survivors"], "declaration_sha256": dsha,
            "results_sha256": sha, "data_provenance": hb.PROVENANCE,
            "note": "HB2 summary: counts its tests into the cumulative ml_explain denominator",
        }, trials_path)
        return
    job = job or "J2"
    tests = out["replication"]["tests"]
    holm = out["replication"]["holm_primary"]
    for hid, rr in tests.items():
        p = rr["primary"]
        provenance.append_trial({
            "kind": TRIAL_KIND_R, "label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE, "revision": REVISION_R,
            "dataset": "history:h3_power", "hypothesis": hid, "family": HMAP2[hid].family,
            "sign_tested": rr["sign_frozen"], "effect": B._clean(p.get("effect")), "p": B._clean(p.get("p")),
            "p_holm": B._clean(holm[hid]["p_holm"]), "replicated": hid in out["replication"]["replicated_primary"],
            "effect_weighted": B._clean(rr["weighted"].get("effect")), "p_weighted": B._clean(rr["weighted"].get("p")),
            "ratio_to_h2": B._clean(rr.get("ratio_to_h2")), "testable": p.get("testable", True),
            "declaration_sha256": dsha, "spec_sha256": out["spec_sha256"], "results_sha256": sha,
        }, trials_path)
    provenance.append_trial({
        "kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": EVIDENCE_ROLE,
        "source": f"screening_batch_2:{job}", "revision": REVISION_R, "dataset": "history:h3_power",
        "n_tests": len(tests), "n_tests_by_family": {f"hb2_replication_{job}": len(tests)},
        "replicated": out["replication"]["replicated_primary"], "declaration_sha256": dsha,
        "spec_sha256": out["spec_sha256"], "results_sha256": sha,
        "note": "HB2 frozen replication on h3_power (read 4/5); counted into the cumulative ml_explain denominator",
    }, trials_path)
