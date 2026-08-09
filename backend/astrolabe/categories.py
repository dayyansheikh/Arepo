"""One deterministic primary-category system for digests, Opportunities and Replay.

Classification uses normalized Polymarket metadata and tags available during the complete scan.
``Other`` is the honest internal fallback; it is included by ``All`` but is never offered as a
user-facing filter. No signal, eligibility or ranking input is used here.
"""
from __future__ import annotations

import re

ALL_CATEGORY = "All"
INTERNAL_OTHER_CATEGORY = "Other"

PRIMARY_CATEGORIES: tuple[str, ...] = (
    "Geopolitics / War",
    "Economics / Macro",
    "Commodities",
    "Politics / Elections",
    "Crypto",
    "Technology / Business",
    "Sports",
    "Entertainment / Culture",
    INTERNAL_OTHER_CATEGORY,
)

USER_CATEGORY_FILTERS: tuple[str, ...] = (ALL_CATEGORY, *PRIMARY_CATEGORIES[:-1])
USER_SELECTABLE_CATEGORIES: tuple[str, ...] = PRIMARY_CATEGORIES[:-1]

OPPORTUNITIES_ALL_LIMIT = 20
OPPORTUNITIES_SPORTS_LIMIT = 20
OPPORTUNITIES_NAMED_LIMIT = 24

_GEOPOLITICS_TAGS = (
    "geopolitics", "geopolitical", "war", "military", "conflict", "ukraine", "russia",
    "israel", "gaza",
    "iran", "nato", "ceasefire",
)
_COMMODITY_TAGS = (
    "commodity", "commodities", "oil", "brent", "wti", "gold", "silver", "copper",
    "natural gas", "opec",
)
_BUSINESS_TAGS = (
    "business", "company", "companies", "earning", "earnings", "ipo", "merger", "acquisition",
)
_POLITICS_TAGS = (
    "politics", "political", "election", "elections", "senate", "congress", "president",
    "government",
)
_CRYPTO_TAGS = ("crypto", "bitcoin", "ethereum", "solana", "defi", "btc", "eth")
_TECH_TAGS = ("technology", "tech", "science", "artificial intelligence", "ai", "space")
_SPORTS_TAGS = (
    "sport", "nfl", "nba", "mlb", "nhl", "ncaa", "soccer", "football", "basketball",
    "baseball", "hockey", "tennis", "golf", "mma", "ufc", "boxing", "cricket", "rugby",
    "esports", "olympics", "nascar", "formula 1", "premier league", "champions league",
)
_ENTERTAINMENT_TAGS = (
    "entertainment", "movie", "film", "television", "music", "award", "oscar", "pop culture",
    "celebrity",
)
_MACRO_TAGS = (
    "economy", "economics", "macro", "fed", "federal reserve", "inflation", "interest rate",
    "finance",
)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text) is not None
        for keyword in keywords
    )


def primary_category(source_category: str | None, tags: list[str] | None = None) -> str:
    """Return one stable label from point-in-time normalized metadata, else ``Other``."""
    category = (source_category or "").strip().lower()
    tag_text = " ".join(t.strip().lower() for t in (tags or []) if t).strip()
    metadata = f"{category} {tag_text}".strip()

    direct = {
        "geopolitics / war": "Geopolitics / War",
        "economics / macro": "Economics / Macro",
        "commodities": "Commodities",
        "politics / elections": "Politics / Elections",
        "crypto": "Crypto",
        "technology / business": "Technology / Business",
        "science & technology": "Technology / Business",
        "sports": "Sports",
        "entertainment / culture": "Entertainment / Culture",
        "entertainment": "Entertainment / Culture",
        "other": INTERNAL_OTHER_CATEGORY,
    }
    if category in direct:
        return direct[category]
    if category == "politics":
        return (
            "Geopolitics / War"
            if _contains_any(tag_text, _GEOPOLITICS_TAGS)
            else "Politics / Elections"
        )
    if category == "economy":
        if _contains_any(tag_text, _COMMODITY_TAGS):
            return "Commodities"
        if _contains_any(tag_text, _BUSINESS_TAGS):
            return "Technology / Business"
        return "Economics / Macro"
    if "commodit" in category:
        return "Commodities"

    # Some upstream categories are the first real event tag rather than a normalized broad label.
    # Re-check the complete metadata string conservatively; ambiguity remains Other.
    if _contains_any(metadata, _GEOPOLITICS_TAGS):
        return "Geopolitics / War"
    if _contains_any(metadata, _COMMODITY_TAGS):
        return "Commodities"
    if _contains_any(metadata, _CRYPTO_TAGS):
        return "Crypto"
    if _contains_any(metadata, _SPORTS_TAGS):
        return "Sports"
    if _contains_any(metadata, _ENTERTAINMENT_TAGS):
        return "Entertainment / Culture"
    if _contains_any(metadata, (*_TECH_TAGS, *_BUSINESS_TAGS)):
        return "Technology / Business"
    if _contains_any(metadata, _POLITICS_TAGS):
        return "Politics / Elections"
    if _contains_any(metadata, _MACRO_TAGS):
        return "Economics / Macro"
    return INTERNAL_OTHER_CATEGORY


def normalize_category_filter(value: str | None) -> str:
    """Validate a public filter; blank means All and internal Other is intentionally rejected."""
    category = (value or ALL_CATEGORY).strip() or ALL_CATEGORY
    if category not in USER_CATEGORY_FILTERS:
        raise ValueError(f"unsupported category: {category}")
    return category


def category_matches(selected: str, actual: str | None) -> bool:
    """All includes every stored category, including Other and legacy-unavailable NULLs."""
    return selected == ALL_CATEGORY or actual == selected


def opportunity_display_limit(category: str) -> int:
    """Configured public display cap applied only after category filtering and ranking."""
    if category == ALL_CATEGORY:
        return OPPORTUNITIES_ALL_LIMIT
    if category == "Sports":
        return OPPORTUNITIES_SPORTS_LIMIT
    return OPPORTUNITIES_NAMED_LIMIT
