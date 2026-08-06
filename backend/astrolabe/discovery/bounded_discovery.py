"""Exhaustive bounded 30-day market discovery (prompt section A).

Queries the short-horizon target universe DIRECTLY via bounded date filters, so discovery never
fetches the first N records of an unbounded global universe and filters afterwards. Two official
keyset paths are reconciled (``/markets/keyset`` primary, ``/events/keyset`` verification via nested
markets), and if a keyset path is ever incomplete the 30-day range is split into half-open UTC
windows scanned independently, each bisected recursively until it exhausts. Completeness is proven
and stored: a scan is complete only when every path/window terminated normally with no repeated
cursor, no failed page and no emergency guard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ..clients.gamma import GammaClient

# Half-open UTC windows (hours from scan origin) used when keyset needs a windowed fallback (A4).
FALLBACK_WINDOWS: tuple[tuple[float, float], ...] = (
    (0, 6), (6, 24), (24, 72), (72, 168), (168, 336), (336, 504), (504, 720),
)
MIN_WINDOW_HOURS = 0.25  # recursive bisection floor (15 minutes)
TARGET_DAYS = 30


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_id(raw: dict) -> str | None:
    cid = raw.get("conditionId")
    if cid:
        return f"c:{cid}"
    mid = raw.get("id")
    return f"m:{mid}" if mid else None


def _markets_from_events(events: list[dict]) -> list[dict]:
    out: list[dict] = []
    for ev in events:
        for m in ev.get("markets") or []:
            if isinstance(m, dict):
                # Carry the event id down so reconciliation can compare event identity.
                m.setdefault("eventId", ev.get("id"))
                out.append(m)
    return out


@dataclass
class DiscoveryReport:
    scan_origin_at: str
    end_date_min: str
    end_date_max: str
    methods: list[str] = field(default_factory=list)
    windows: list[dict] = field(default_factory=list)
    primary_pages: int = 0
    primary_cursors: int = 0
    primary_raw: int = 0
    primary_unique: int = 0
    verification_pages: int = 0
    verification_raw: int = 0
    verification_unique: int = 0
    overlap: int = 0
    only_primary: int = 0
    only_verification: int = 0
    union_unique: int = 0
    identity_conflicts: int = 0
    complete: bool = False
    incomplete_reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "scan_origin_at": self.scan_origin_at,
            "end_date_min": self.end_date_min,
            "end_date_max": self.end_date_max,
            "methods": self.methods,
            "windows": self.windows,
            "primary_pages": self.primary_pages,
            "primary_cursors": self.primary_cursors,
            "primary_raw": self.primary_raw,
            "primary_unique": self.primary_unique,
            "verification_pages": self.verification_pages,
            "verification_raw": self.verification_raw,
            "verification_unique": self.verification_unique,
            "overlap": self.overlap,
            "only_primary": self.only_primary,
            "only_verification": self.only_verification,
            "union_unique": self.union_unique,
            "identity_conflicts": self.identity_conflicts,
            "complete": self.complete,
            "incomplete_reason": self.incomplete_reason,
        }


class BoundedDiscovery:
    """Complete bounded discovery of the 30-day active-open universe."""

    def __init__(self, gamma: GammaClient):
        self.gamma = gamma

    async def _keyset_window(
        self, endpoint: str, item_key: str, dmin: str, dmax: str, *, max_pages: int = 5000
    ) -> tuple[list[dict], dict]:
        return await self.gamma.paginate_keyset(
            endpoint, item_key, active=True, closed=False,
            end_date_min=dmin, end_date_max=dmax, page_size=100, max_pages=max_pages,
        )

    async def _windowed_fallback(
        self, endpoint: str, item_key: str, origin: datetime, report: DiscoveryReport
    ) -> list[dict]:
        """Scan the 30-day range as half-open windows, bisecting any window that is incomplete."""
        report.methods.append(f"windowed_fallback:{endpoint}")
        collected: list[dict] = []

        async def scan(h0: float, h1: float) -> None:
            dmin, dmax = _iso(origin + timedelta(hours=h0)), _iso(origin + timedelta(hours=h1))
            items, rep = await self._keyset_window(endpoint, item_key, dmin, dmax)
            report.windows.append({
                "hours": [h0, h1], "raw": rep["raw_items"], "pages": rep["pages"],
                "complete": rep["complete"], "reason": rep["incomplete_reason"],
            })
            if rep["complete"]:
                collected.extend(items)
                return
            if (h1 - h0) <= MIN_WINDOW_HOURS:
                report.complete = False
                report.incomplete_reason = (
                    f"window [{h0},{h1}) on {endpoint} could not be exhausted at the minimum "
                    f"duration ({MIN_WINDOW_HOURS}h): {rep['incomplete_reason']}"
                )
                collected.extend(items)  # keep what we got, but the scan is incomplete
                return
            mid = (h0 + h1) / 2
            await scan(h0, mid)
            await scan(mid, h1)

        for h0, h1 in FALLBACK_WINDOWS:
            await scan(h0, h1)
        return collected

    async def discover(
        self, *, scan_origin: datetime | None = None
    ) -> tuple[list[dict], DiscoveryReport]:
        origin = (scan_origin or datetime.now(UTC)).astimezone(UTC)
        dmin, dmax = _iso(origin), _iso(origin + timedelta(days=TARGET_DAYS))
        report = DiscoveryReport(scan_origin_at=_iso(origin), end_date_min=dmin, end_date_max=dmax)

        # Primary: bounded /markets/keyset.
        report.methods.append("markets_keyset")
        primary_items, prep = await self._keyset_window("/markets/keyset", "markets", dmin, dmax)
        report.primary_pages = prep["pages"]
        report.primary_cursors = prep["cursors"]
        report.primary_raw = prep["raw_items"]
        primary_complete = prep["complete"]
        if not primary_complete:
            primary_items = await self._windowed_fallback(
                "/markets/keyset", "markets", origin, report
            )
            primary_complete = report.incomplete_reason is None

        # Verification: bounded /events/keyset -> nested markets.
        report.methods.append("events_keyset")
        ver_events, vrep = await self._keyset_window("/events/keyset", "events", dmin, dmax)
        report.verification_pages = vrep["pages"]
        verification_items = _markets_from_events(ver_events)
        report.verification_raw = len(verification_items)
        verification_complete = vrep["complete"]

        # Deduplicate each path by canonical id.
        primary: dict[str, dict] = {}
        for m in primary_items:
            k = _canonical_id(m)
            if k:
                primary.setdefault(k, m)
        verification: dict[str, dict] = {}
        for m in verification_items:
            k = _canonical_id(m)
            if k:
                verification.setdefault(k, m)
        report.primary_unique = len(primary)
        report.verification_unique = len(verification)

        # Reconcile: deterministic union; never silently drop a market returned by one path.
        pk, vk = set(primary), set(verification)
        report.overlap = len(pk & vk)
        report.only_primary = len(pk - vk)
        report.only_verification = len(vk - pk)
        conflicts = 0
        union: dict[str, dict] = dict(primary)
        for k, m in verification.items():
            if k in union:
                a, b = union[k], m
                if (a.get("id") and b.get("id") and str(a["id"]) != str(b["id"])):
                    conflicts += 1
            else:
                union[k] = m
        report.identity_conflicts = conflicts
        report.union_unique = len(union)

        # Completeness proof (A5): both official paths reconciled AND each terminated normally.
        report.complete = bool(
            primary_complete and verification_complete and report.incomplete_reason is None
        )
        if not report.complete and report.incomplete_reason is None:
            if not verification_complete:
                report.incomplete_reason = (
                    f"events_keyset verification incomplete: {vrep['incomplete_reason']}"
                )
            elif not primary_complete:
                report.incomplete_reason = prep["incomplete_reason"]

        return list(union.values()), report
