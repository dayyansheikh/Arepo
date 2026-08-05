"""Analysis-framework tests (prompt sections 7-11, 14): baselines, ablation, walk-forward
partitions, calibration guard and the edge verdict. Pure and deterministic."""
import pytest

from astrolabe.evaluation.research_analysis import (
    HorizonObs,
    ablation_table,
    baseline_table,
    edge_verdict,
    score_predictor,
)
from astrolabe.evaluation.research_calibration import (
    brier_score,
    calibration_status,
    confidence_frequency_bins,
    log_loss,
)
from astrolabe.evaluation.research_constants import (
    MIN_CALIBRATION_SAMPLE,
    PARTITION_DEVELOPMENT,
    PARTITION_HELDOUT,
    PARTITION_LIVE,
    PARTITION_THRESHOLD,
)
from astrolabe.evaluation.research_predictors import BASELINES, EntryView
from astrolabe.evaluation.research_walk_forward import (
    LeakageError,
    assert_no_leakage,
    is_reportable,
    partition_for_backfill,
    walk_forward_windows,
    window_verdict,
)


def _obs(direction, mom, ob, move, *, entry=0.5, depth=2000.0):
    ev = EntryView(direction=direction, momentum_direction=mom, orderbook_direction=ob,
                   tradeflow_direction=None, entry_price=entry)
    return HorizonObs(entry=ev, entry_midpoint=entry, entry_spread=0.02, entry_depth=depth,
                      forward_midpoint=entry + move, forward_spread=0.02, forward_depth=depth)


def test_score_predictor_flat_and_executable():
    obs = [
        _obs("up", "up", "up", 0.06),    # correct (big move)
        _obs("up", "up", "up", 0.0),     # flat
        _obs("up", "up", "up", -0.05),   # incorrect
    ]
    s = score_predictor(lambda e: e.direction, obs)
    assert s["correct"] == 1 and s["incorrect"] == 1 and s["flat"] == 1
    assert s["evaluated"] == 2                     # flat excluded from denominator
    assert s["mean_midpoint_move"] is not None
    # all three directional calls have a move (incl the flat 0.0) and depth, so all are costed
    assert s["executable_evaluated"] == 3


def test_baselines_score_and_agreement():
    # Arepo direction == momentum by construction here => agreement 1.0
    obs = [_obs("up", "up", "down", 0.05), _obs("down", "down", "up", -0.05)]
    t = baseline_table(obs)
    assert set(BASELINES).issubset(t["baselines"].keys())
    assert t["arepo_momentum_agreement"] == 1.0
    # order-book-only used the (opposing) orderbook direction, so it is scored differently
    assert t["baselines"]["order_book_only"]["evaluated"] >= 1
    assert "Brier" in t["probabilistic_metrics_note"]


def test_ablation_reports_diffs_vs_full_and_momentum():
    obs = [_obs("up", "up", "up", 0.05) for _ in range(4)]
    ab = ablation_table(obs)
    assert "full_model" in ab and "without_momentum" in ab
    assert ab["full_model"]["hit_rate_vs_full"] == 0.0
    # every field present for a reviewer to read
    assert "hit_rate_vs_momentum" in ab["without_order_book"]


def test_walk_forward_partitions_and_leakage():
    assert partition_for_backfill(0, 10) == PARTITION_DEVELOPMENT
    assert partition_for_backfill(6, 10) == PARTITION_THRESHOLD
    assert partition_for_backfill(9, 10) == PARTITION_HELDOUT
    assert is_reportable(PARTITION_HELDOUT) and is_reportable(PARTITION_LIVE)
    assert not is_reportable(PARTITION_THRESHOLD)
    assert_no_leakage({1, 2, 3}, {4, 5})            # no overlap: fine
    with pytest.raises(LeakageError):
        assert_no_leakage({1, 2, 3}, {3, 4})        # overlap: refused


def test_walk_forward_windows_do_not_overlap_train_and_test():
    from datetime import UTC, datetime, timedelta
    cutoffs = [datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=d) for d in range(10)]
    windows = list(walk_forward_windows(cutoffs, train=4, test=2))
    assert windows
    for w in windows:
        assert w.train[1] < w.test[0]              # train strictly before test
    assert window_verdict(5) == "inconclusive"


def test_calibration_guarded_until_minimum_sample():
    st = calibration_status(10)
    assert not st.available and "Calibration unavailable" in st.message
    st2 = calibration_status(MIN_CALIBRATION_SAMPLE)
    assert st2.available
    # metrics compute only with genuine probabilities
    assert brier_score([0.8, 0.2], [1, 0]) == pytest.approx((0.04 + 0.04) / 2)
    assert log_loss([0.9, 0.1], [1, 0]) is not None
    assert brier_score([], []) is None
    bins = confidence_frequency_bins([(0.1, False), (0.9, True), (0.85, True)], n_bins=5)
    assert len(bins) == 5


def test_edge_verdict_not_supported_on_empty_sample():
    empty = {"hit_rate": None, "ci95": [0.0, 1.0], "mean_executable_move": None}
    v = edge_verdict(
        evaluable_sample=0, arepo=empty, momentum=empty, price_only=empty, implied=empty,
        all_prospective=True, walk_forward_stable=False, ablation_beats_momentum=False,
    )
    assert v.edge_supported is False
    assert "not yet accumulated enough prospective evidence" in v.message
    assert v.criteria["meets_minimum_sample"] is False
