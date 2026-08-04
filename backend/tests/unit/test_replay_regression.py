"""Replay regression + honest-sample tests (spec §5, §6)."""
import pytest

from astrolabe.evaluation.replay_stats import (
    MIN_MEANINGFUL_SAMPLE,
    DirectionalResult,
    compare_baselines,
    sample_verdict,
    wilson_interval,
)


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
