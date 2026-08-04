"""Confidence-as-reliability tests (spec §6): no 100% spike, variation, monotonicity."""
import pytest

from astrolabe.opportunity.scoring import (
    RELIABILITY_BASE,
    TARGET_FAMILIES,
    reliability_confidence,
)


def test_single_family_perfect_data_is_not_full_confidence():
    # The core bug being fixed: perfect data quality on a lone, uncorroborated reading used to
    # display 100%. It must now be capped by the single-family reliability base.
    c = reliability_confidence(1.0, n_families=1)
    assert c < 1.0
    assert c == pytest.approx(RELIABILITY_BASE + 0.55 * (1 / TARGET_FAMILIES))


def test_zero_families_is_lowest():
    assert reliability_confidence(1.0, 0) == pytest.approx(RELIABILITY_BASE)


def test_full_corroboration_reaches_full_confidence_only_with_perfect_data():
    assert reliability_confidence(1.0, TARGET_FAMILIES) == pytest.approx(1.0)
    assert reliability_confidence(1.0, TARGET_FAMILIES + 5) == pytest.approx(1.0)  # saturates
    # but poor data quality still caps it well below 1.0 even when fully corroborated
    assert reliability_confidence(0.5, TARGET_FAMILIES) == pytest.approx(0.5)


def test_monotonic_in_both_inputs():
    # Non-decreasing in family count...
    prev = -1.0
    for n in range(0, TARGET_FAMILIES + 2):
        c = reliability_confidence(1.0, n)
        assert c >= prev
        prev = c
    # ...and strictly increasing in data quality at a fixed family count.
    assert reliability_confidence(0.3, 2) < reliability_confidence(0.9, 2)


def test_meaningful_variation_across_realistic_inputs():
    # A spread of (data_quality, n_families) inputs should NOT collapse onto 1.0.
    values = {
        round(reliability_confidence(dq, n), 3)
        for dq in (0.4, 0.7, 1.0)
        for n in (0, 1, 2, 3)
    }
    assert len(values) >= 6            # genuine variation, not a spike
    assert max(values) <= 1.0 and min(values) >= 0.0
    at_100 = [v for v in values if v >= 0.999]
    assert len(at_100) <= 1            # only the perfect-data, fully-corroborated corner


def test_bounds_and_clamping():
    assert reliability_confidence(2.0, 1) <= 1.0     # dq clamped
    assert reliability_confidence(-1.0, 3) >= 0.0    # dq clamped
