"""Compatibility exports for the shared Arepo primary-category system."""
from __future__ import annotations

from ..categories import (
    PRIMARY_CATEGORIES,
    USER_SELECTABLE_CATEGORIES,
    primary_category,
)

DIGEST_CATEGORIES = PRIMARY_CATEGORIES
DIGEST_PREFERENCE_CATEGORIES = USER_SELECTABLE_CATEGORIES
digest_category = primary_category

__all__ = ("DIGEST_CATEGORIES", "DIGEST_PREFERENCE_CATEGORIES", "digest_category")
