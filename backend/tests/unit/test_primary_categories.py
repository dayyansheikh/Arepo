"""Shared primary-category classification and public-filter contract."""

import pytest

from astrolabe.categories import (
    ALL_CATEGORY,
    INTERNAL_OTHER_CATEGORY,
    USER_CATEGORY_FILTERS,
    category_matches,
    normalize_category_filter,
    opportunity_display_limit,
    primary_category,
)


def test_primary_classification_is_deterministic_from_metadata_and_tags():
    cases = [
        ("Politics", ["Geopolitics", "Ukraine"], "Geopolitics / War"),
        ("Politics", ["US Election"], "Politics / Elections"),
        ("Economy", ["Gold"], "Commodities"),
        ("Economy", ["Federal Reserve"], "Economics / Macro"),
        ("Economy", ["Earnings"], "Technology / Business"),
        ("Crypto", ["Bitcoin"], "Crypto"),
        ("Sports", ["NBA"], "Sports"),
        ("Entertainment", ["Film"], "Entertainment / Culture"),
    ]
    for source, tags, expected in cases:
        assert primary_category(source, tags) == expected
        assert primary_category(source, tags) == expected


def test_ambiguous_is_other_and_all_includes_it_without_exposing_other():
    assert primary_category("Weather", ["Rainfall"]) == INTERNAL_OTHER_CATEGORY
    assert category_matches(ALL_CATEGORY, INTERNAL_OTHER_CATEGORY) is True
    assert category_matches(ALL_CATEGORY, None) is True
    assert INTERNAL_OTHER_CATEGORY not in USER_CATEGORY_FILTERS
    with pytest.raises(ValueError):
        normalize_category_filter(INTERNAL_OTHER_CATEGORY)


def test_display_limits_are_configured_by_public_category():
    assert opportunity_display_limit(ALL_CATEGORY) == 20
    assert opportunity_display_limit("Sports") == 20
    assert opportunity_display_limit("Crypto") == 24
