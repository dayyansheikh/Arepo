"""Tests for the computed statistical-hypothesis generator (spec §6, §16)."""
from astrolabe.opportunity.hypothesis import (
    build_hypothesis,
    has_directional_view,
)


def test_no_direction_means_no_view():
    assert has_directional_view(None, 3, 0.9) is False
    txt = build_hypothesis(direction=None, outcome="Yes", n_families=3, signal_strength=0.9)
    assert "not currently have enough" in txt


def test_weak_single_measure_is_insufficient():
    # Direction resolved, but no family fired and strength below the floor -> no view.
    assert has_directional_view("up", 0, 0.2) is False
    txt = build_hypothesis(direction="up", outcome="Yes", n_families=0, signal_strength=0.2)
    assert "not currently have enough" in txt


def test_family_evidence_warrants_a_view():
    assert has_directional_view("up", 1, 0.2) is True
    txt = build_hypothesis(direction="up", outcome="Yes", n_families=1, signal_strength=0.5)
    assert "upward repricing pressure" in txt
    assert "Yes" in txt


def test_strong_strength_alone_warrants_a_view():
    assert has_directional_view("down", 0, 0.8) is True
    txt = build_hypothesis(direction="down", outcome="No", n_families=0, signal_strength=0.8)
    assert "downward repricing pressure" in txt
    assert "strong" in txt


def test_strength_words_track_bands():
    early = build_hypothesis(direction="up", outcome="A", n_families=2, signal_strength=0.30)
    moderate = build_hypothesis(direction="up", outcome="A", n_families=1, signal_strength=0.50)
    strong = build_hypothesis(direction="up", outcome="A", n_families=1, signal_strength=0.80)
    assert "early" in early
    assert "moderate" in moderate
    assert "strong" in strong


def test_horizon_phrase_for_short_dated():
    within_day = build_hypothesis(
        direction="up", outcome="Yes", n_families=2, signal_strength=0.6,
        time_remaining_hours=12,
    )
    assert "within a day" in within_day
    within_week = build_hypothesis(
        direction="up", outcome="Yes", n_families=2, signal_strength=0.6,
        time_remaining_hours=72,
    )
    assert "days before it closes" in within_week


def test_never_promises_profit_or_certainty():
    for direction in ("up", "down"):
        txt = build_hypothesis(
            direction=direction, outcome="Yes", n_families=2, signal_strength=0.9,
        ).lower()
        for banned in ("profit", "guaranteed", "will ", "certain", "buy", "sell"):
            assert banned not in txt
