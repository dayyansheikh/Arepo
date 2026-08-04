"""Cross-surface consistency contract (spec §17).

The same signal must show the same displayed confidence and the same directional gate on Signal
Lab, Market Detail and the Opportunity Board (the Board may only differ by ADDING live trade-flow
families, which is the one documented exception). These are executable checks so a regression that
re-splits confidence or the gate across surfaces is a test failure, not a silent contradiction.
"""
from datetime import UTC, datetime

from astrolabe.opportunity.hypothesis import has_directional_view
from astrolabe.opportunity.scoring import (
    CONFIDENCE_DISPLAY_CEILING,
    score_opportunity,
    signal_reliability,
)
from astrolabe.service.enrich import compute_token_analytics, outcome_view

NOW = datetime(2026, 8, 4, tzinfo=UTC)
_PRICES = [0.5, 0.55, 0.45, 0.6, 0.4, 0.58, 0.42, 0.61, 0.39, 0.5, 0.66, 0.34]


def _ta(prices):
    return compute_token_analytics(
        token_id="t1", market_id="m1", prices=prices, book=None, volumes=[]
    )


def _signal(prices):
    return _ta(prices).signal


def test_market_detail_outcome_card_shows_reliability_not_raw_100pct():
    # F'#1: the Market Detail per-outcome card must carry reliability_confidence, never only the raw
    # data-quality term. It must equal the signal's reliability and be capped below 100%.
    ta = _ta(_PRICES)
    ov = outcome_view(ta, name="Yes", normalized_prob=0.5)
    assert ov.reliability_confidence is not None
    assert ov.reliability_confidence == ta.signal.reliability_confidence
    assert ov.reliability_confidence <= CONFIDENCE_DISPLAY_CEILING
    assert ov.reliability_confidence < 1.0


def test_reliability_ignores_absent_volume_acceleration():
    # F'#10: volume_acceleration is never present live and is NOT in the completeness set, so its
    # absence must not change the reliability of an otherwise-identical live-shaped signal.
    sig = _signal(_PRICES)
    assert not any(
        c.name == "volume_acceleration" and c.raw_value is not None for c in sig.components
    )
    rel, _ = signal_reliability(sig)
    assert 0.0 < rel <= CONFIDENCE_DISPLAY_CEILING


def test_signal_lab_confidence_is_never_the_raw_100pct_data_quality_term():
    # A clean, moving series has data_quality confidence ~1.0, but the DISPLAYED reliability must
    # be capped well below 1.0 by corroboration (spec §6: do not display 100%).
    sig = _signal([0.5, 0.52, 0.48, 0.53, 0.6, 0.4, 0.55, 0.45, 0.5, 0.62, 0.38, 0.58])
    rel, n_fam = signal_reliability(sig)
    assert rel < 1.0
    assert 0.0 <= rel <= 1.0
    # The raw data-quality term is what feeds reliability; they must not be the same displayed value
    # unless corroboration is full (n_families >= TARGET), which a price-only signal cannot reach.
    assert rel <= sig.confidence


def test_signal_lab_and_board_agree_without_trade_flow():
    # With no trade-flow indicators (Signal Lab / Market Detail have no trades), the Board's
    # score_opportunity must produce the SAME confidence and family count as signal_reliability.
    sig = _signal([0.5, 0.55, 0.45, 0.6, 0.4, 0.58, 0.42, 0.61, 0.39, 0.5, 0.66, 0.34])
    rel, n_fam = signal_reliability(sig)
    scored = score_opportunity(
        sig, [], liquidity=None, relative_spread=None, data_age_seconds=None, now=NOW
    )
    assert scored.confidence == rel
    assert scored.n_families == n_fam


def test_directional_gate_uses_the_same_rule_everywhere():
    # has_directional_view is the one gate; it must agree with the n_families carried on the signal
    # (which Signal Lab / Market Detail consume) for the same inputs.
    sig = _signal([0.5, 0.55, 0.45, 0.6, 0.4, 0.58, 0.42, 0.61, 0.39, 0.5, 0.66, 0.34])
    _, n_fam = signal_reliability(sig)
    gate = has_directional_view(sig.direction, n_fam, sig.strength)
    # If it qualifies, it is because a family fired or strength cleared the floor - the exact rule
    # the frontend directionalVerdict now mirrors via signal.n_families.
    assert gate == (
        sig.direction in ("up", "down") and (n_fam >= 1 or sig.strength >= 0.40)
    )
