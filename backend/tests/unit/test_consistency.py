"""Data-consistency tests (spec §14): checks fire on contradictions; model invariants hold."""
from datetime import UTC, datetime, timedelta

from astrolabe.analytics.consistency import (
    check_close_state,
    check_confidence_vs_family,
    check_directional_has_direction,
    check_replay_entry_causal,
    check_stale_labelled_live,
    check_title_end_year,
)
from astrolabe.opportunity.scoring import reliability_confidence

NOW = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)


def test_confidence_family_contradiction_detected():
    assert check_confidence_vs_family(1.0, 1)          # 100% on one family -> warning
    assert not check_confidence_vs_family(1.0, 3)      # 100% on three families is fine
    assert not check_confidence_vs_family(0.6, 1)      # 60% on one family is fine


def test_model_never_produces_100pct_on_single_family():
    # Invariant guard: the confidence model itself cannot generate the contradiction above.
    for dq in (0.5, 0.9, 1.0):
        conf = reliability_confidence(dq, n_families=1, component_completeness=1.0)
        assert not check_confidence_vs_family(conf, 1), f"model emitted {conf} on 1 family"


def test_directional_requires_direction():
    assert check_directional_has_direction(True, None)
    assert check_directional_has_direction(True, "flat")
    assert not check_directional_has_direction(True, "up")
    assert not check_directional_has_direction(False, None)


def test_close_state_contradiction():
    past = NOW - timedelta(days=2)
    assert check_close_state("active", past, NOW)
    assert not check_close_state("closed", past, NOW)
    assert not check_close_state("active", NOW + timedelta(days=2), NOW)


def test_title_end_year_contradiction():
    end = datetime(2026, 12, 31, tzinfo=UTC)
    assert check_title_end_year("Will X happen by 2027?", end)      # 2026 < 2027 -> warn
    assert not check_title_end_year("Will X happen by 2026?", end)  # consistent
    assert not check_title_end_year("Will X happen?", end)          # no year -> no warning


def test_stale_labelled_live():
    assert check_stale_labelled_live("live", 400.0)     # > 5x stale_after
    assert not check_stale_labelled_live("live", 30.0)
    assert not check_stale_labelled_live("replay", 9999.0)


def test_replay_entry_causality():
    as_of = NOW
    assert check_replay_entry_causal(NOW + timedelta(hours=1), as_of)   # after cut-off -> warn
    assert not check_replay_entry_causal(NOW - timedelta(hours=1), as_of)
