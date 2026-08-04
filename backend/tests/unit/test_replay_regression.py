"""Replay regression + honest-sample tests (spec §5, §6)."""
import pytest

from astrolabe.evaluation.replay_stats import (
    FLAT_EPS,
    MIN_MEANINGFUL_SAMPLE,
    DirectionalResult,
    classify_directional,
    compare_baselines,
    sample_verdict,
    wilson_interval,
)
from astrolabe.evaluation.tracking import _movement_correct


def test_classify_directional_is_flat_aware():
    # A move at/below the epsilon is flat: neither correct nor incorrect for either direction.
    assert classify_directional("up", 0.0) == "flat"
    assert classify_directional("down", 0.0) == "flat"
    assert classify_directional("up", FLAT_EPS) == "flat"
    # A genuine move is scored against the call.
    assert classify_directional("up", 0.05) == "correct"
    assert classify_directional("up", -0.05) == "incorrect"
    assert classify_directional("down", -0.05) == "correct"
    # No forward data => pending; no directional call => abstained (both None).
    assert classify_directional("up", None) is None
    assert classify_directional(None, 0.05) is None


def test_flat_market_is_not_an_arepo_miss_but_is_a_no_change_win():
    # The exact asymmetry the baseline recorded: a flat market must NOT count against a directional
    # predictor, while it is legitimately a win for the "predict flat" no-change baseline.
    r = [DirectionalResult(arepo_direction="up", momentum_direction="up", move_24h=0.0)]
    cmp = compare_baselines(r)
    assert cmp.arepo["evaluated"] == 0          # flat excluded from the hit-rate denominator
    assert cmp.arepo["flat"] == 1               # but reported transparently
    assert cmp.arepo["incorrect"] == 0          # never booked as a miss
    assert cmp.baselines["no_change"]["correct"] == 1  # no-change predicted flat, and was right


def test_prospective_pipeline_flat_move_is_not_a_miss():
    # F-adv#1: the flat bug also lived in the real cohort pipeline. A zero 24h move must not be
    # scored False (a miss); it is None (flat/pending), so the summary can bucket it as flat.
    assert _movement_correct("up", 0.0) is None
    assert _movement_correct("down", 0.0) is None
    assert _movement_correct("up", 0.05) is True
    assert _movement_correct("up", -0.05) is False


def test_small_samples_are_inconclusive():
    # Both the reported "~50% on 4" and "0% on 3" must be labelled inconclusive.
    assert sample_verdict(3) == "inconclusive"
    assert sample_verdict(4) == "inconclusive"
    assert sample_verdict(MIN_MEANINGFUL_SAMPLE) == "indicative"


def test_wilson_interval_is_wide_for_tiny_samples():
    lo, hi = wilson_interval(2, 4)          # 50% on 4 trials
    assert hi - lo > 0.5                     # interval spans most of [0, 1] -> not evidence
    lo0, hi0 = wilson_interval(0, 3)         # 0% on 3 trials
    assert lo0 < 0.05 and hi0 > 0.5          # 0/3 is consistent with a coin flip


def test_baseline_comparison_scores_all_baselines():
    # A tiny, mixed sample: Arepo down/up/down vs real moves.
    results = [
        DirectionalResult(arepo_direction="down", momentum_direction="down", move_24h=-0.05),
        DirectionalResult(arepo_direction="down", momentum_direction="up", move_24h=0.03),
        DirectionalResult(arepo_direction="up", momentum_direction="up", move_24h=0.02),
    ]
    cmp = compare_baselines(results)
    assert cmp.sample_size == 3
    assert cmp.verdict == "inconclusive"     # never presented as proof
    assert cmp.arepo["correct"] == 2 and cmp.arepo["incorrect"] == 1
    # every baseline is scored on the same sample
    for key in ("no_change", "momentum", "always_up", "always_down"):
        assert key in cmp.baselines
        assert cmp.baselines[key]["verdict"] == "inconclusive"
    # always-up is correct exactly when the move is positive (2 of 3 here are... -0.05,+0.03,+0.02)
    assert cmp.baselines["always_up"]["correct"] == 2


def test_none_directions_and_moves_are_excluded():
    results = [
        DirectionalResult(arepo_direction=None, momentum_direction=None, move_24h=0.02),
        DirectionalResult(arepo_direction="up", momentum_direction="up", move_24h=None),
    ]
    cmp = compare_baselines(results)
    assert cmp.arepo["evaluated"] == 0       # no scorable Arepo directions


@pytest.mark.parametrize("move,flat", [(0.005, True), (0.05, False)])
def test_no_change_baseline_counts_flat_markets(move, flat):
    r = [DirectionalResult(arepo_direction="up", momentum_direction="up", move_24h=move)]
    cmp = compare_baselines(r)
    assert (cmp.baselines["no_change"]["correct"] == 1) == flat


def test_requested_baselines_present():
    # §2.1: current-implied and price-only must be included alongside the existing baselines.
    results = [
        DirectionalResult(arepo_direction="up", momentum_direction="up", move_24h=0.03,
                          entry_price=0.7, price_only_direction="up"),
        DirectionalResult(arepo_direction="down", momentum_direction="down", move_24h=-0.02,
                          entry_price=0.3, price_only_direction="down"),
    ]
    cmp = compare_baselines(results)
    expected = ("no_change", "current_implied", "price_only", "momentum",
                "always_up", "always_down")
    for key in expected:
        assert key in cmp.baselines, f"missing baseline {key}"
    # current-implied predicts up for entry>0.5 (+0.03, correct) and down for entry<0.5 (-0.02, ok)
    assert cmp.baselines["current_implied"]["correct"] == 2
    # price-only follows the trend sign here (both correct)
    assert cmp.baselines["price_only"]["evaluated"] == 2
