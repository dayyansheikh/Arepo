"""Signal trajectory from stored snapshots (prompt sections 9, 11, 17).

Pure and deterministic over a market's ordered snapshot history. A trajectory describes how the
STORED SIGNAL-STRENGTH SCORE changed over time; it is explicitly NOT a statement about probability,
accuracy, expected profit or final resolution. "Strengthening" means only that the stored strength
score increased over the comparison period.

The stability threshold is predeclared from score precision and numerical jitter, not tuned to
realised outcomes. Strength is stored on a 0-1 scale; the product shows it as points (x100), so the
threshold is 0.02 = 2 points.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta


def _utc(dt: datetime) -> datetime:
    """Coerce to UTC-aware (SQLite returns naive datetimes); assumes stored times are UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

# Predeclared stability threshold: a strength move of 2 points (0.02) or less is treated as noise,
# not a real change. Chosen from the score's display precision (whole points) plus a 1-point margin
# for input jitter. Documented and tested; never adjusted after looking at outcomes.
STABILITY_THRESHOLD = 0.02

# A snapshot older than this (from "now") makes the current reading STALE.
STALE_AFTER_SECONDS = 20 * 60  # 20 minutes (>3 missed 5-minute scans)

LABEL_NEW = "New signal"
LABEL_STRENGTHENING = "Strengthening"
LABEL_WEAKENING = "Weakening"
LABEL_STABLE = "Stable"
LABEL_REVERSED = "Direction reversed"
LABEL_UNAVAILABLE = "Temporarily unavailable"
LABEL_STALE = "Stale"


@dataclass(frozen=True)
class Snap:
    """The minimal snapshot shape trajectory needs (a view over SignalSnapshotRow or a fixture)."""

    captured_at: datetime
    strength: float
    direction: str | None
    rank_in_bucket: int | None
    research_priority: int
    evidence_families: tuple[str, ...] = ()


def _at_or_before(history: list[Snap], target: datetime) -> Snap | None:
    """The most recent snapshot at or before ``target`` (history is oldest-first)."""
    chosen = None
    for s in history:
        if s.captured_at <= target:
            chosen = s
        else:
            break
    return chosen


def _delta_over(history: list[Snap], latest: Snap, window: timedelta) -> float | None:
    ref = _at_or_before(history, latest.captured_at - window)
    if ref is None or ref is latest:
        return None
    return round(latest.strength - ref.strength, 4)


@dataclass
class Trajectory:
    label: str
    strength: float
    strength_change_prev: float | None      # vs the immediately previous snapshot
    change_15m: float | None
    change_1h: float | None
    change_6h: float | None
    first_detected: datetime | None
    last_updated: datetime | None
    consecutive_same_direction: int
    rank_change: int | None                 # positive = improved (rank number decreased)
    research_priority_change: int | None
    evidence_family_changes: dict
    direction_reversed: bool
    scans: int

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "strength": round(self.strength, 4),
            "strength_change_prev": self.strength_change_prev,
            "change_15m": self.change_15m,
            "change_1h": self.change_1h,
            "change_6h": self.change_6h,
            "first_detected": self.first_detected.isoformat() if self.first_detected else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "consecutive_same_direction": self.consecutive_same_direction,
            "rank_change": self.rank_change,
            "research_priority_change": self.research_priority_change,
            "evidence_family_changes": self.evidence_family_changes,
            "direction_reversed": self.direction_reversed,
            "scans": self.scans,
        }


def compute_trajectory(
    history: list[Snap], *, now: datetime, present_in_latest: bool = True
) -> Trajectory:
    """Compute the trajectory for one market from its oldest-first snapshot history.

    ``present_in_latest`` is False when the market was analysed before but is absent from the most
    recent scan (temporarily unavailable). ``history`` may be empty.
    """
    if not history:
        return Trajectory(
            label=LABEL_UNAVAILABLE, strength=0.0, strength_change_prev=None,
            change_15m=None, change_1h=None, change_6h=None,
            first_detected=None, last_updated=None, consecutive_same_direction=0,
            rank_change=None, research_priority_change=None, evidence_family_changes={},
            direction_reversed=False, scans=0,
        )

    # Normalise timestamps to UTC-aware so naive DB rows and an aware ``now`` compare cleanly.
    now = _utc(now)
    history = [replace(s, captured_at=_utc(s.captured_at)) for s in history]
    latest = history[-1]
    prev = history[-2] if len(history) >= 2 else None

    strength_change_prev = (
        round(latest.strength - prev.strength, 4) if prev is not None else None
    )
    direction_reversed = bool(
        prev is not None and latest.direction in ("up", "down")
        and prev.direction in ("up", "down") and latest.direction != prev.direction
    )

    # Consecutive scans with the same (non-null) direction ending at the latest snapshot.
    consec = 0
    if latest.direction in ("up", "down"):
        for s in reversed(history):
            if s.direction == latest.direction:
                consec += 1
            else:
                break

    rank_change = (
        (prev.rank_in_bucket - latest.rank_in_bucket)
        if (prev is not None and prev.rank_in_bucket is not None
            and latest.rank_in_bucket is not None)
        else None
    )
    rp_change = (
        latest.research_priority - prev.research_priority if prev is not None else None
    )
    fam_prev = set(prev.evidence_families) if prev is not None else set()
    fam_now = set(latest.evidence_families)
    fam_changes = {
        "added": sorted(fam_now - fam_prev),
        "removed": sorted(fam_prev - fam_now),
    }

    # Label.
    last_age = (now - latest.captured_at).total_seconds()
    if not present_in_latest:
        label = LABEL_UNAVAILABLE
    elif last_age > STALE_AFTER_SECONDS:
        label = LABEL_STALE
    elif prev is None:
        label = LABEL_NEW
    elif direction_reversed:
        label = LABEL_REVERSED
    elif strength_change_prev is not None and strength_change_prev > STABILITY_THRESHOLD:
        label = LABEL_STRENGTHENING
    elif strength_change_prev is not None and strength_change_prev < -STABILITY_THRESHOLD:
        label = LABEL_WEAKENING
    else:
        label = LABEL_STABLE

    return Trajectory(
        label=label,
        strength=latest.strength,
        strength_change_prev=strength_change_prev,
        change_15m=_delta_over(history, latest, timedelta(minutes=15)),
        change_1h=_delta_over(history, latest, timedelta(hours=1)),
        change_6h=_delta_over(history, latest, timedelta(hours=6)),
        first_detected=history[0].captured_at,
        last_updated=latest.captured_at,
        consecutive_same_direction=consec,
        rank_change=rank_change,
        research_priority_change=rp_change,
        evidence_family_changes=fam_changes,
        direction_reversed=direction_reversed,
        scans=len(history),
    )
