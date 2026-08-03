"""Tests for the Research Priority score, evidence families and tags."""
from datetime import UTC, datetime

from astrolabe.analytics.flow import FAMILY_FLOW, FAMILY_TIMING, FlowIndicator
from astrolabe.domain.enums import DataQuality, SignalKind
from astrolabe.domain.models import Signal, SignalComponent
from astrolabe.opportunity import scoring

NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def sig(*, strength=0.5, confidence=0.6, dq=DataQuality.GOOD, price_feature=0.0, imbalance=None):
    comps = []
    if price_feature > 0:
        comps.append(SignalComponent(name="movement_abnormality", normalized_value=price_feature,
                                     weight=0.2))
    if imbalance is not None:
        comps.append(
            SignalComponent(name="book_imbalance", normalized_value=imbalance, weight=0.12)
        )
    return Signal(
        kind=SignalKind.COMPOSITE_ANOMALY, token_id="tok", market_id="m",
        strength=strength, confidence=confidence, direction="up",
        detected="x", method="y", why_it_matters="z", limitations="w",
        components=comps, data_quality=dq, window="1000 obs",
    )


def flow_ind(family=FAMILY_FLOW, *, fired=True, mag=0.7, tag="Large relative trade"):
    return FlowIndicator(name="i", family=family, fired=fired, magnitude=mag, tag=tag,
                         explanation="A large relative trade occurred.", detail={})


def test_no_extra_evidence_low_family_count():
    score = scoring.score_opportunity(
        sig(strength=0.4, price_feature=0.0), [], liquidity=60_000, relative_spread=0.01,
        data_age_seconds=100, now=NOW,
    )
    assert score.n_families == 0
    assert "no additional independent evidence" in score.explanation
    assert score.high_priority is False


def test_price_family_and_tag():
    score = scoring.score_opportunity(
        sig(price_feature=0.6), [], liquidity=60_000, relative_spread=0.01,
        data_age_seconds=100, now=NOW,
    )
    assert "price" in score.families
    labels = [t.label for t in score.tags]
    assert "Rapid repricing" in labels
    tag = next(t for t in score.tags if t.label == "Rapid repricing")
    assert tag.methodology_anchor and tag.timestamp == NOW and tag.data_quality == "good"


def test_two_independent_families_can_be_high_priority():
    score = scoring.score_opportunity(
        sig(strength=0.6, confidence=0.8, price_feature=0.7),
        [flow_ind(FAMILY_FLOW, mag=0.8)],
        liquidity=80_000, relative_spread=0.005, data_age_seconds=60, now=NOW,
    )
    assert set(score.families) == {"price", "trade_flow"}
    assert score.n_families == 2
    assert score.high_priority is True


def test_two_flow_indicators_are_one_family():
    # Two indicators in the same family must not count as two independent families.
    score = scoring.score_opportunity(
        sig(price_feature=0.0),
        [flow_ind(FAMILY_FLOW, tag="Large relative trade"),
         flow_ind(FAMILY_FLOW, tag="Clustered trades")],
        liquidity=60_000, relative_spread=0.01, data_age_seconds=60, now=NOW,
    )
    assert score.families == ["trade_flow"]
    assert score.n_families == 1


def test_distinct_families_counted():
    score = scoring.score_opportunity(
        sig(price_feature=0.5),
        [flow_ind(FAMILY_FLOW), flow_ind(FAMILY_TIMING, tag="Late large trade")],
        liquidity=60_000, relative_spread=0.01, data_age_seconds=60, now=NOW,
    )
    assert set(score.families) == {"price", "trade_flow", "timing"}
    assert score.n_families == 3


def test_confidence_degrades_score():
    hi = scoring.score_opportunity(
        sig(strength=0.7, confidence=0.9, price_feature=0.7), [flow_ind()],
        liquidity=80_000, relative_spread=0.005, data_age_seconds=60, now=NOW)
    lo = scoring.score_opportunity(
        sig(strength=0.7, confidence=0.2, price_feature=0.7), [flow_ind()],
        liquidity=80_000, relative_spread=0.005, data_age_seconds=60, now=NOW)
    assert lo.research_priority < hi.research_priority


def test_thin_liquidity_penalises_and_tags():
    score = scoring.score_opportunity(
        sig(strength=0.7, confidence=0.8, price_feature=0.7), [flow_ind()],
        liquidity=500, relative_spread=0.01, data_age_seconds=60, now=NOW)
    assert score.liquidity_quality == "thin"
    assert "Thin market" in [t.label for t in score.tags]


def test_wide_spread_and_staleness_reduce_score():
    fresh_tight = scoring.score_opportunity(
        sig(strength=0.7, confidence=0.8, price_feature=0.7), [flow_ind()],
        liquidity=80_000, relative_spread=0.005, data_age_seconds=60, now=NOW)
    wide_stale = scoring.score_opportunity(
        sig(strength=0.7, confidence=0.8, price_feature=0.7), [flow_ind()],
        liquidity=80_000, relative_spread=0.09, data_age_seconds=200_000, now=NOW)
    assert wide_stale.research_priority < fresh_tight.research_priority


def test_poor_data_quality_tag():
    score = scoring.score_opportunity(
        sig(dq=DataQuality.POOR, price_feature=0.3), [], liquidity=60_000,
        relative_spread=0.01, data_age_seconds=60, now=NOW)
    assert "Limited data" in [t.label for t in score.tags]
