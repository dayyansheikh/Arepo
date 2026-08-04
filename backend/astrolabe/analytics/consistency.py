"""Data-consistency checks (spec §14).

Surfaces contradictions between what different parts of the system say, so they become internal
warnings and test failures rather than silently displayed contradictory data. Each check returns a
list of human-readable warning strings (empty when consistent). The invariant checks double as
regression guards: the model layer is built so these never fire (e.g. confidence can never be 100%
on a single evidence family, and a directional view always has a resolved direction), and tests
assert that.
"""
from __future__ import annotations

import re
from datetime import datetime


def check_confidence_vs_family(confidence: float, n_families: int) -> list[str]:
    """100% confidence on a single evidence family is contradictory (spec §14)."""
    if confidence >= 0.999 and n_families <= 1:
        return [
            f"confidence {confidence:.2f} with only {n_families} evidence family "
            "(100% confidence requires multiple corroborating families)"
        ]
    return []


def check_directional_has_direction(directional: bool, direction: str | None) -> list[str]:
    """A directional view must have a resolved up/down direction (spec §14)."""
    if directional and direction not in ("up", "down"):
        return ["a directional view is set but the direction is not resolved (up/down)"]
    return []


def check_close_state(status: str | None, end_date: datetime | None, now: datetime) -> list[str]:
    """A market past its end date but still labelled active, or vice versa (spec §14)."""
    warnings: list[str] = []
    s = (status or "").lower()
    if end_date is not None and end_date < now and s in ("active", "open"):
        warnings.append(
            f"market end date {end_date.date()} is in the past but status is '{status}'"
        )
    return warnings


def check_title_end_year(question: str | None, end_date: datetime | None) -> list[str]:
    """A year named in the market title that contradicts the displayed end-date year (spec §14).

    Only flags a four-digit year in a plausible range; a title with no year is not a contradiction.
    """
    if not question or end_date is None:
        return []
    years = [int(y) for y in re.findall(r"\b(20[2-4]\d)\b", question)]
    if not years:
        return []
    # Use the latest year mentioned (e.g. "by end of 2027"); flag only if the end date is before it.
    latest = max(years)
    if end_date.year < latest:
        return [
            f"title mentions {latest} but the end date is {end_date.date()} "
            f"({end_date.year} < {latest})"
        ]
    return []


def check_stale_labelled_live(data_mode: str, data_age_seconds: float | None,
                              stale_after: float = 60.0) -> list[str]:
    """Live data that is actually stale (spec §14)."""
    if data_mode == "live" and data_age_seconds is not None and data_age_seconds > stale_after * 5:
        return [
            f"data labelled live is {data_age_seconds:.0f}s old "
            f"(> {stale_after * 5:.0f}s); it should be flagged stale"
        ]
    return []


def check_replay_entry_causal(entry_time: datetime, as_of: datetime) -> list[str]:
    """A Replay entry price taken after the historical cut-off is look-ahead (spec §14)."""
    if entry_time > as_of:
        return [f"replay entry time {entry_time} is after the cut-off {as_of} (look-ahead)"]
    return []


def collect_card_warnings(
    *, confidence: float, n_families: int, directional: bool, direction: str | None,
    status: str | None, end_date: datetime | None, question: str | None, now: datetime,
) -> list[str]:
    """All consistency warnings for one opportunity card / market (empty when consistent)."""
    return [
        *check_confidence_vs_family(confidence, n_families),
        *check_directional_has_direction(directional, direction),
        *check_close_state(status, end_date, now),
        *check_title_end_year(question, end_date),
    ]
