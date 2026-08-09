"""Delivery preference labels layered over Arepo's existing normalized market taxonomy.

This adapter does not change ``derive_category`` or any research/Explore classification. It uses
the existing normalized category first and real upstream tags only to split the broader Politics
and Economy buckets into the user-facing digest choices requested by the account product.
"""
from __future__ import annotations

DIGEST_CATEGORIES: tuple[str, ...] = (
    "Geopolitics / War",
    "Economics / Macro",
    "Commodities",
    "Politics / Elections",
    "Crypto",
    "Technology / Business",
    "Sports",
    "Entertainment / Culture",
    "Other",
)

# User-selectable filters intentionally exclude the deterministic ``Other`` fallback. An empty
# preference means All, which still includes markets classified internally as Other.
DIGEST_PREFERENCE_CATEGORIES: tuple[str, ...] = DIGEST_CATEGORIES[:-1]

_GEOPOLITICS_TAGS = (
    "geopolit", "war", "military", "conflict", "ukraine", "russia", "israel", "gaza",
    "iran", "nato", "ceasefire",
)
_COMMODITY_TAGS = (
    "commodit", "oil", "brent", "wti", "gold", "silver", "copper", "natural gas", "opec",
)
_BUSINESS_TAGS = ("business", "company", "companies", "earnings", "ipo", "merger", "acquisition")


def digest_category(source_category: str | None, tags: list[str] | None = None) -> str:
    """Return one stable delivery label without altering the stored source category."""
    category = (source_category or "").strip().lower()
    tag_text = " ".join(t.strip().lower() for t in (tags or []) if t).strip()
    if category == "politics":
        return (
            "Geopolitics / War"
            if any(word in tag_text for word in _GEOPOLITICS_TAGS)
            else "Politics / Elections"
        )
    if category == "economy":
        if any(word in tag_text for word in _COMMODITY_TAGS):
            return "Commodities"
        if any(word in tag_text for word in _BUSINESS_TAGS):
            return "Technology / Business"
        return "Economics / Macro"
    if "commodit" in category:
        return "Commodities"
    if category == "crypto":
        return "Crypto"
    if category == "science & technology":
        return "Technology / Business"
    if category == "sports":
        return "Sports"
    if category == "entertainment":
        return "Entertainment / Culture"
    return "Other"
