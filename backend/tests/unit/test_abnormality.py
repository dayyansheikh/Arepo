"""Tests for the price-derived abnormality features (movement burst, volatility regime)."""
import math

import numpy as np
import pytest

from astrolabe.analytics.abnormality import return_burst_score, volatility_regime


def _cumulative(returns_list: list[float], start: float = 0.5) -> list[float]:
    """Turn a list of per-step returns into a price series starting at ``start``."""
    prices = [start]
    for r in returns_list:
        prices.append(prices[-1] + r)
    return prices


def test_return_burst_none_on_insufficient_history():
    assert return_burst_score([0.5, 0.51, 0.52]) is None


def test_return_burst_none_on_flat_series():
    assert return_burst_score([0.5] * 60) is None  # zero baseline volatility


def test_return_burst_matches_independent_formula():
    # Baseline: 40 alternating +/-0.01 returns; then a 6-step run of +0.02 (a burst).
    base = [0.01 if i % 2 == 0 else -0.01 for i in range(40)]
    burst = [0.02] * 6
    prices = _cumulative(base + burst)

    got = return_burst_score(prices, window=6, baseline_window=40, min_periods=15)

    # Independent expected value using the same definition.
    r = np.diff(np.asarray(prices, dtype=float))
    sigma = float(np.std(r[-40:], ddof=1))
    net = float(np.sum(r[-6:]))
    expected = abs(net) / (sigma * math.sqrt(6))
    assert got == pytest.approx(expected, rel=1e-9)
    assert got > 2.0  # a clear multi-sigma burst


def test_return_burst_bigger_move_scores_higher():
    base = [0.005 if i % 2 == 0 else -0.005 for i in range(40)]
    small = return_burst_score(_cumulative(base + [0.004] * 6))
    large = return_burst_score(_cumulative(base + [0.02] * 6))
    assert small is not None and large is not None
    assert large > small


def test_volatility_regime_none_on_insufficient():
    assert volatility_regime([0.5, 0.5, 0.5]) is None


def test_volatility_regime_near_zero_when_constant_vol():
    # Constant-magnitude alternating returns => short and long vols match => ~0.
    prices = _cumulative([0.01 if i % 2 == 0 else -0.01 for i in range(50)])
    vr = volatility_regime(prices, short=10, long=40, min_periods=20)
    assert vr is not None and abs(vr) < 0.15


def test_volatility_regime_positive_on_recent_spike():
    calm = [0.002 if i % 2 == 0 else -0.002 for i in range(40)]
    spike = [0.02 if i % 2 == 0 else -0.02 for i in range(10)]
    prices = _cumulative(calm + spike)
    vr = volatility_regime(prices, short=10, long=40, min_periods=20)
    assert vr is not None and vr > 1.0  # recent vol well above baseline
