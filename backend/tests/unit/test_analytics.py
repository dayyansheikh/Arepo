"""Analytics correctness tests, including hand-derived numeric expectations.

Where practical these assert against values computed by hand (not just numpy-vs-numpy) so a
genuine implementation error would fail the test.
"""
import math

import pytest

from astrolabe.analytics.anomaly import (
    DEFAULT_WEIGHTS,
    RawComponents,
    build_anomaly_signal,
    composite_anomaly_score,
)
from astrolabe.analytics.implied import (
    implied_probability,
    normalized_outcome_probabilities,
)
from astrolabe.analytics.microstructure import (
    near_mid_depth,
    order_book_imbalance,
    spread_info,
)
from astrolabe.analytics.movement import movement, window_movement
from astrolabe.analytics.quality import assess_quality, squash
from astrolabe.analytics.series import returns
from astrolabe.analytics.volatility import rolling_volatility
from astrolabe.analytics.zscore import rolling_zscore
from astrolabe.domain.enums import DataQuality, SignalKind
from astrolabe.domain.models import BookLevel, OrderBook


# --------------------------------------------------------------------------- series
def test_returns_diff_simple_log_and_gaps():
    assert returns([0.4, 0.5, 0.45], "diff").tolist() == pytest.approx([0.1, -0.05])
    # None is dropped pairwise (no spurious jump fabricated)
    assert returns([0.4, None, 0.5], "diff").tolist() == pytest.approx([0.1])
    assert returns([0.2, 0.4], "simple").tolist() == pytest.approx([1.0])
    assert returns([0.5, 0.5], "log").tolist() == pytest.approx([0.0])
    assert returns([0.5], "diff").size == 0            # <2 finite => empty
    assert returns([], "diff").size == 0


# --------------------------------------------------------------------------- movement
def test_movement_absolute_and_relative():
    m = movement([0.40, 0.42, 0.50])
    assert m.absolute == pytest.approx(0.10)
    assert m.relative == pytest.approx(0.25)          # (0.5-0.4)/0.4
    assert m.n == 3
    assert movement([0.5]).absolute is None           # insufficient
    # window uses only the last `window` steps
    wm = window_movement([0.1, 0.2, 0.3, 0.9], window=1)
    assert wm.absolute == pytest.approx(0.6)          # 0.9 - 0.3


# --------------------------------------------------------------------------- volatility
def test_rolling_volatility_hand_value():
    # returns from diffs = [0, 0, 0, 0.02]; sample std (ddof=1) = 0.01 exactly.
    v = rolling_volatility([0.3, 0.3, 0.3, 0.3, 0.32], window=20, min_periods=4)
    assert v.sufficient is True
    assert v.value == pytest.approx(0.01, abs=1e-9)
    # insufficient history returns None, not a crash
    assert rolling_volatility([0.3, 0.31], window=20, min_periods=5).value is None


# --------------------------------------------------------------------------- z-score
def test_rolling_zscore_hand_value():
    # returns = [0,0,0,0.02]; mean=0.005, std=0.01 => z=(0.02-0.005)/0.01 = 1.5
    z = rolling_zscore([0.3, 0.3, 0.3, 0.3, 0.32], window=10, min_periods=4)
    assert z.value == pytest.approx(1.5, abs=1e-9)
    assert z.last_return == pytest.approx(0.02)
    assert z.mean == pytest.approx(0.005)
    assert z.std == pytest.approx(0.01)


def test_rolling_zscore_edge_cases():
    # zero variance: flat series -> no meaningful standardised move
    z = rolling_zscore([0.5] * 12, window=10, min_periods=4)
    assert z.value is None and z.reason == "zero_variance"
    # insufficient history
    z2 = rolling_zscore([0.5, 0.51, 0.52], window=10, min_periods=8)
    assert z2.value is None and z2.reason == "insufficient_history"
    # clip bounds extreme z
    prices = [0.5] * 20 + [0.9]           # one big jump after a flat run
    z3 = rolling_zscore(prices, window=25, min_periods=8, clip=5.0)
    assert z3.value is not None and abs(z3.value) <= 5.0


# --------------------------------------------------------------------------- implied
def test_implied_probability_clamp_and_normalize():
    assert implied_probability(0.73).value == pytest.approx(0.73)
    assert implied_probability(1.4).value == 1.0           # clamped
    assert implied_probability(None).value is None
    # normalise removes overround: 0.55 + 0.5 = 1.05 -> scaled to sum 1
    norm = normalized_outcome_probabilities([0.55, 0.50])
    assert sum(norm) == pytest.approx(1.0)
    assert norm[0] == pytest.approx(0.55 / 1.05)
    # None preserved, excluded from denominator
    norm2 = normalized_outcome_probabilities([0.6, None])
    assert norm2[1] is None and norm2[0] == pytest.approx(1.0)


# --------------------------------------------------------------------------- microstructure
def _book():
    return OrderBook(
        token_id="t",
        bids=[BookLevel(price=0.49, size=100), BookLevel(price=0.48, size=50)],
        asks=[BookLevel(price=0.52, size=80), BookLevel(price=0.53, size=40)],
        tick_size=0.01,
    )


def test_spread_and_imbalance_and_near_mid():
    si = spread_info(_book())
    assert si.midpoint == pytest.approx(0.505)
    assert si.spread == pytest.approx(0.03)
    assert si.relative_spread == pytest.approx(0.03 / 0.505)
    assert si.spread_ticks == pytest.approx(3.0)

    imb = order_book_imbalance(_book(), levels=5)
    # (150 - 120)/(150 + 120) = 30/270
    assert imb.value == pytest.approx(30 / 270)
    assert imb.bid_depth == 150 and imb.ask_depth == 120

    nmd = near_mid_depth(_book(), band=0.02)   # mid 0.505 -> [0.485, 0.525]
    assert nmd.bid_depth == pytest.approx(100)  # 0.49 in, 0.48 out
    assert nmd.ask_depth == pytest.approx(80)   # 0.52 in, 0.53 out
    assert nmd.total_depth == pytest.approx(180) and nmd.defined is True


def test_microstructure_degenerate_books():
    empty = OrderBook(token_id="t")
    assert order_book_imbalance(empty).value is None      # zero denominator
    assert near_mid_depth(empty).defined is False
    assert spread_info(empty).midpoint is None
    one_sided = OrderBook(token_id="t", bids=[BookLevel(price=0.4, size=10)])
    assert spread_info(one_sided).spread is None
    assert order_book_imbalance(one_sided).value == pytest.approx(1.0)  # all bid depth


# --------------------------------------------------------------------------- quality
def test_quality_penalties_and_bands():
    # Ideal inputs => full confidence, GOOD.
    good = assess_quality(
        n_history=40, relative_spread=0.01, near_mid_depth=1000,
        data_age_seconds=1, two_sided_book=True,
    )
    assert good.confidence == pytest.approx(1.0) and good.band == DataQuality.GOOD

    # One-sided + stale + short history => low confidence, reasons recorded.
    poor = assess_quality(
        n_history=2, ideal_history=20, relative_spread=None, near_mid_depth=None,
        data_age_seconds=600, stale_after_seconds=60, two_sided_book=False,
    )
    assert poor.confidence < 0.45 and poor.band == DataQuality.POOR
    assert any("history" in r for r in poor.reasons)
    assert any("stale" in r for r in poor.reasons)
    assert any("one-sided" in r for r in poor.reasons)

    assert squash(2.0, 4.0) == pytest.approx(0.5)
    assert squash(10.0, 4.0) == 1.0                     # saturates


# --------------------------------------------------------------------------- anomaly
def test_composite_renormalises_over_available_components():
    # Only zscore present: score == its normalised magnitude regardless of other weights.
    raw = RawComponents(zscore=2.0)                     # |2|/cap4 = 0.5
    score, comps = composite_anomaly_score(raw)
    assert score == pytest.approx(0.5)
    present = [c for c in comps if c.normalized_value is not None]
    assert len(present) == 1 and present[0].name == "unusual_return"

    # All components present => weighted mean with full weights (sum to 1).
    raw2 = RawComponents(zscore=4.0, volume_acceleration=3.0, imbalance=1.0,
                         spread_change=1.0, depth_change=1.0)
    score2, _ = composite_anomaly_score(raw2)
    assert score2 == pytest.approx(sum(DEFAULT_WEIGHTS.values()))  # all normalised to 1 => 1.0
    assert score2 == pytest.approx(1.0)


def test_imbalance_alone_cannot_drive_a_top_score():
    # Order-book imbalance with no price context is capped, so it can never be a top signal.
    score, _ = composite_anomaly_score(RawComponents(imbalance=1.0))
    assert score <= 0.5 + 1e-9
    # Even imbalance + volume (both non-price) stay capped.
    score2, _ = composite_anomaly_score(
        RawComponents(imbalance=1.0, volume_acceleration=3.0)
    )
    assert score2 <= 0.5 + 1e-9


def test_present_but_zero_price_feature_does_not_bypass_the_cap():
    # A calm market produces a present-but-zero volatility regime on every tick. That must NOT
    # count as price context, so order-book/flow features alone still cannot exceed the ceiling.
    score, _ = composite_anomaly_score(
        RawComponents(volatility_regime=0.0, imbalance=1.0, spread_change=1.0, depth_change=1.0)
    )
    assert score <= 0.5 + 1e-9
    # Likewise a negligible (below-floor) price feature.
    z_floor = 0.05 * 4.0  # cap for unusual_return is 4.0, so this normalises to exactly 0.05
    tiny, _ = composite_anomaly_score(
        RawComponents(zscore=z_floor * 0.5, imbalance=1.0, spread_change=1.0, depth_change=1.0)
    )
    assert tiny <= 0.5 + 1e-9


def test_material_price_feature_lifts_the_cap():
    # A price feature clearly above the floor is genuine context and lifts the ceiling.
    score, _ = composite_anomaly_score(
        RawComponents(movement_abnormality=1.2, imbalance=1.0, spread_change=1.0, depth_change=1.0)
    )
    assert score > 0.5


def test_price_features_contribute_and_lift_above_the_book_only_cap():
    # A strong abnormal move alone (a price feature) can exceed the book-only ceiling.
    score, comps = composite_anomaly_score(RawComponents(movement_abnormality=4.0))
    present = [c.name for c in comps if c.normalized_value is not None]
    assert present == ["movement_abnormality"]
    assert score == pytest.approx(1.0)  # normalised to 1, price context present => uncapped

    # Volatility-regime is a distinct price feature that also contributes.
    score2, _ = composite_anomaly_score(RawComponents(volatility_regime=2.0))
    assert score2 == pytest.approx(1.0)


def test_composite_not_dominated_by_imbalance_when_price_present():
    # With a full-strength price feature and full-strength imbalance, imbalance is a minority.
    score, _ = composite_anomaly_score(
        RawComponents(movement_abnormality=4.0, imbalance=1.0)
    )
    # Both normalise to 1, so the score is 1.0 regardless; the point is the WEIGHT split.
    from astrolabe.analytics.anomaly import DEFAULT_WEIGHTS

    assert DEFAULT_WEIGHTS["book_imbalance"] < DEFAULT_WEIGHTS["movement_abnormality"]
    # The three price features together outweigh every book/flow feature combined.
    price_w = sum(
        DEFAULT_WEIGHTS[k]
        for k in ("unusual_return", "movement_abnormality", "volatility_regime")
    )
    assert price_w >= 0.55
    assert score == pytest.approx(1.0)


def test_build_anomaly_signal_folds_confidence():
    q = assess_quality(
        n_history=5, ideal_history=20, relative_spread=0.2, near_mid_depth=50,
        data_age_seconds=10, two_sided_book=True,
    )
    sig = build_anomaly_signal(
        token_id="tok", market_id="mkt",
        raw=RawComponents(zscore=-3.0, imbalance=-0.4), quality=q, window_desc="20 obs",
    )
    assert sig.kind == SignalKind.COMPOSITE_ANOMALY
    assert sig.direction == "down"                      # negative z
    assert 0.0 <= sig.strength <= 1.0
    # confidence = strength * quality.confidence <= strength
    assert sig.confidence <= sig.strength + 1e-9
    assert "insider" in sig.limitations.lower()          # ethical caveat present
    assert not math.isnan(sig.strength)
