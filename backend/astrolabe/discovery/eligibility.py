"""Short-horizon eligibility gate and non-overlapping closing-time buckets (prompt sections 3, 4).

Pure and deterministic. This is the BACKEND eligibility rule that runs BEFORE scoring and public
ranking, so the public top ten is only ever a display limit over a completely-analysed universe, and
markets closing more than 30 days out never enter the public product. Historical bucket membership
is always computed from the close time known at the scan/freeze timestamp against the ``now`` passed
in, never recalculated from the present time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..domain.enums import MarketStatus
from ..domain.models import Market

# --- Horizon constants (hours) ----------------------------------------------------------------
H_6 = 6.0
H_24 = 24.0
H_7D = 24.0 * 7
H_30D = 24.0 * 30
ELIGIBLE_MAX_HOURS = H_30D  # public eligibility ends at 30 days

# --- Primary (non-overlapping) buckets --------------------------------------------------------
BUCKET_0_6H = "closing_0_6h"
BUCKET_6_24H = "closing_6_24h"
BUCKET_1_7D = "closing_1_7d"
BUCKET_7_30D = "closing_7_30d"
BUCKET_ALL = "all_0_30d"
PRIMARY_BUCKETS = (BUCKET_0_6H, BUCKET_6_24H, BUCKET_1_7D, BUCKET_7_30D)

BUCKET_LABELS: dict[str, str] = {
    BUCKET_0_6H: "Closing in the next 6 hours",
    BUCKET_6_24H: "Closing later today",
    BUCKET_1_7D: "Closing this week",
    BUCKET_7_30D: "Closing this month",
    BUCKET_ALL: "All markets closing within 30 days",
}

# --- Cumulative "within X" windows (hours) ----------------------------------------------------
CUMULATIVE_WINDOWS: dict[str, float] = {
    "within_6h": H_6,
    "within_24h": H_24,
    "within_7d": H_7D,
    "within_30d": H_30D,
}

# --- Exclusion reasons (stable strings, stored on each snapshot) ------------------------------
REASON_NOT_ACTIVE = "not active"
REASON_CLOSED = "already closed (status)"
REASON_NO_CLOSE_TIME = "no known close time"
REASON_INVALID_CLOSE_TIME = "invalid close time"
REASON_EXPIRED = "no time remaining (already past close)"
REASON_BEYOND_30D = "closing more than 30 days away"
REASON_NO_TOKEN = "no resolvable tradable outcome token"


def time_remaining_hours(market: Market, now: datetime) -> float | None:
    """Hours from ``now`` to the market's close, using the close time known at ``now``.

    None when there is no valid close time. Never uses the present wall-clock; the caller passes the
    scan/freeze ``now`` so historical membership is reproducible (prompt section 4).
    """
    end = market.end_date
    if end is None:
        return None
    if end.tzinfo is None:
        end = end.replace(tzinfo=now.tzinfo)
    return (end - now).total_seconds() / 3600.0


def primary_bucket(hours: float | None) -> str | None:
    """The single non-overlapping primary bucket for a time-to-close, or None if not within 30d.

    Boundaries are inclusive at the upper edge so a market exactly on a boundary lands in the
    shorter bucket (prompt section 4: "more than 0 and up to 6 hours", etc.).
    """
    if hours is None or hours <= 0:
        return None
    if hours <= H_6:
        return BUCKET_0_6H
    if hours <= H_24:
        return BUCKET_6_24H
    if hours <= H_7D:
        return BUCKET_1_7D
    if hours <= H_30D:
        return BUCKET_7_30D
    return None


def in_cumulative_window(hours: float | None, window: str) -> bool:
    """Whether a time-to-close falls in a cumulative "within X" window."""
    if hours is None or hours <= 0:
        return False
    cap = CUMULATIVE_WINDOWS.get(window)
    return cap is not None and hours <= cap


@dataclass(frozen=True)
class Eligibility:
    eligible: bool
    reason: str | None
    hours: float | None
    bucket: str | None


def classify_market(market: Market, now: datetime) -> Eligibility:
    """Structural 30-day public eligibility for one market at ``now`` (prompt section 3).

    Data-quality, liquidity and spread exclusions happen later during scoring (the existing rules);
    this gate is the point-in-time structural test that must pass before a market can be scored for
    the public short-horizon universe.
    """
    if market.status in (MarketStatus.CLOSED, MarketStatus.RESOLVED, MarketStatus.ARCHIVED):
        return Eligibility(False, REASON_CLOSED, None, None)
    if market.status != MarketStatus.ACTIVE:
        # UNKNOWN status with a live order book is still testable, but a non-active market is not
        # part of the public tradeable universe.
        if not market.enable_order_book:
            return Eligibility(False, REASON_NOT_ACTIVE, None, None)
    if market.end_date is None:
        return Eligibility(False, REASON_NO_CLOSE_TIME, None, None)
    hours = time_remaining_hours(market, now)
    if hours is None:
        return Eligibility(False, REASON_INVALID_CLOSE_TIME, None, None)
    if hours <= 0:
        return Eligibility(False, REASON_EXPIRED, hours, None)
    if hours > ELIGIBLE_MAX_HOURS:
        return Eligibility(False, REASON_BEYOND_30D, hours, None)
    if not market.token_ids:
        return Eligibility(False, REASON_NO_TOKEN, hours, None)
    return Eligibility(True, None, hours, primary_bucket(hours))


@dataclass
class DiscoveryFunnel:
    """The complete discovery funnel (prompt sections 1, 23). Every discovered market lands in
    exactly one terminal bucket, so the counts reconcile to ``unique_markets``."""

    raw_records: int = 0
    unique_markets: int = 0
    duplicates_removed: int = 0
    no_close_time: int = 0
    invalid_close_time: int = 0
    not_active: int = 0
    already_closed: int = 0
    no_token: int = 0
    beyond_30d: int = 0
    closing_0_6h: int = 0
    closing_6_24h: int = 0
    closing_1_7d: int = 0
    closing_7_30d: int = 0
    eligible_30d: int = 0
    pagination_complete: bool = False
    pagination_reason: str | None = None
    per_bucket: dict[str, int] = field(default_factory=dict)

    def add(self, e: Eligibility) -> None:
        if e.eligible:
            self.eligible_30d += 1
            if e.bucket == BUCKET_0_6H:
                self.closing_0_6h += 1
            elif e.bucket == BUCKET_6_24H:
                self.closing_6_24h += 1
            elif e.bucket == BUCKET_1_7D:
                self.closing_1_7d += 1
            elif e.bucket == BUCKET_7_30D:
                self.closing_7_30d += 1
            return
        r = e.reason
        if r == REASON_NO_CLOSE_TIME:
            self.no_close_time += 1
        elif r == REASON_INVALID_CLOSE_TIME:
            self.invalid_close_time += 1
        elif r == REASON_NOT_ACTIVE:
            self.not_active += 1
        elif r == REASON_CLOSED:
            self.already_closed += 1
        elif r == REASON_EXPIRED:
            self.already_closed += 1
        elif r == REASON_NO_TOKEN:
            self.no_token += 1
        elif r == REASON_BEYOND_30D:
            self.beyond_30d += 1

    def finalise(self) -> None:
        self.per_bucket = {
            BUCKET_0_6H: self.closing_0_6h,
            BUCKET_6_24H: self.closing_6_24h,
            BUCKET_1_7D: self.closing_1_7d,
            BUCKET_7_30D: self.closing_7_30d,
        }

    def as_dict(self) -> dict:
        self.finalise()
        return {
            "raw_records": self.raw_records,
            "unique_markets": self.unique_markets,
            "duplicates_removed": self.duplicates_removed,
            "no_close_time": self.no_close_time,
            "invalid_close_time": self.invalid_close_time,
            "not_active": self.not_active,
            "already_closed": self.already_closed,
            "no_token": self.no_token,
            "beyond_30d": self.beyond_30d,
            "closing_0_6h": self.closing_0_6h,
            "closing_6_24h": self.closing_6_24h,
            "closing_1_7d": self.closing_1_7d,
            "closing_7_30d": self.closing_7_30d,
            "eligible_30d": self.eligible_30d,
            "per_bucket": self.per_bucket,
            "pagination_complete": self.pagination_complete,
            "pagination_reason": self.pagination_reason,
        }


def build_funnel(
    markets: list[Market], now: datetime
) -> tuple[DiscoveryFunnel, list[tuple[Market, Eligibility]]]:
    """Classify every discovered market into the funnel and return (funnel, eligible pairs)."""
    funnel = DiscoveryFunnel(unique_markets=len(markets))
    eligible: list[tuple[Market, Eligibility]] = []
    for m in markets:
        e = classify_market(m, now)
        funnel.add(e)
        if e.eligible:
            eligible.append((m, e))
    funnel.finalise()
    return funnel, eligible


def rank_within(items: list, key) -> list[tuple[int, object]]:
    """Assign a dense 1-based rank to ``items`` by descending ``key`` (deterministic tie-break by
    the item's own order). Returns (rank, item) pairs. Used for per-bucket and overall rankings so a
    bucket's ranking is computed over ALL its eligible markets, not a pre-filtered top ten."""
    ordered = sorted(enumerate(items), key=lambda p: (-key(p[1]), p[0]))
    return [(i + 1, item) for i, (_orig, item) in enumerate(ordered)]
