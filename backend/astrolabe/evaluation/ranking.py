"""Pure eligibility, tie-breaking and ISO-week helpers for the cohort engine.

No I/O here so the selection rules are unit-testable in isolation (spec section 17).
All of these see only information available at the calculation timestamp.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .constants import DATA_QUALITY_RANK, MIN_DATA_QUALITY_RANK, MIN_STRENGTH


def data_quality_rank(band: str | None) -> int:
    return DATA_QUALITY_RANK.get((band or "").lower(), 0)


def is_eligible(*, strength: float, data_quality: str, entry_price: float | None) -> bool:
    """A signal qualifies for a weekly slot only if it clears the documented minimums:
    a valid entry price, at least 'limited' data coverage, and the minimum strength."""
    if entry_price is None:
        return False
    if data_quality_rank(data_quality) < MIN_DATA_QUALITY_RANK:
        return False
    return strength >= MIN_STRENGTH


def selection_key(
    *,
    strength: float,
    confidence: float,
    data_quality: str,
    captured_at: datetime,
    tiebreak: str | int,
) -> tuple:
    """Ascending sort key where the *strongest* signal sorts first.

    Deterministic tie-breaking: strength, then confidence, then data-quality band, then
    the earlier signal timestamp, then a stable id/ref. Two signals can therefore never
    order ambiguously.
    """
    return (
        -float(strength),
        -float(confidence),
        -data_quality_rank(data_quality),
        captured_at,
        str(tiebreak),
    )


def week_bounds(at: datetime) -> tuple[int, int, datetime, datetime]:
    """Return (iso_year, iso_week, week_start, cutoff_at) for the calendar week of ``at``.

    week_start is Monday 00:00:00 UTC; cutoff is Sunday 23:59:59 UTC (spec section 14).
    """
    if at.tzinfo is None:
        at = at.replace(tzinfo=UTC)
    at = at.astimezone(UTC)
    iso_year, iso_week, iso_weekday = at.isocalendar()
    midnight = at.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = midnight - timedelta(days=iso_weekday - 1)
    cutoff_at = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return iso_year, iso_week, week_start, cutoff_at
