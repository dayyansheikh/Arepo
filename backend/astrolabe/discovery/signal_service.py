"""Read/aggregation service for the complete-scan surface (prompt sections 10, 11, 12, 19).

Server-side evaluation truth for Signal Lab and the market-detail history: the latest scan status +
discovery funnel, the current signals per closing-time bucket (full eligible universe, all
directional, public top ten, shadow directional), and per-market signal history + trajectory. The
browser only renders these; it never derives bucket membership, ranks, trajectory state or
completeness from client state. Reads are deterministic and idempotent.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from . import scan_store
from .eligibility import BUCKET_LABELS, PRIMARY_BUCKETS
from .snapshot_models import ScanRunRow, SignalSnapshotRow
from .trajectory import Snap, compute_trajectory

SCOPE_FULL = "full"              # every eligible market in the bucket
SCOPE_DIRECTIONAL = "directional"  # every directional signal
SCOPE_PUBLIC = "public"          # up to ten highest-ranked directional (display)
SCOPE_SHADOW = "shadow"          # directional not in the public ten


def _row_public(r: SignalSnapshotRow) -> dict:
    return {
        "market_id": r.market_id,
        "condition_id": r.condition_id,
        "event_id": r.event_id,
        "token_id": r.token_id,
        "market_question": r.market_question,
        "outcome_name": r.outcome_name,
        "bucket": r.bucket,
        "bucket_label": BUCKET_LABELS.get(r.bucket or "", r.bucket),
        "close_time": r.close_time.isoformat() if r.close_time else None,
        "time_remaining_hours": r.time_remaining_hours,
        "direction": r.direction,
        "signal_classification": r.signal_classification,
        "strength": r.strength,
        "confidence": r.confidence,
        "research_priority": r.research_priority,
        "rank_in_bucket": r.rank_in_bucket,
        "overall_rank_30d": r.overall_rank_30d,
        "public_top_ten": r.public_top_ten,
        "shadow_directional": r.shadow_directional,
        "n_families": r.n_families,
        "evidence_families": r.evidence_families,
        "data_quality": r.data_quality,
    }


def _scan_summary(s: ScanRunRow) -> dict:
    return {
        "scan_id": s.scan_id,
        "started_at": s.started_at.isoformat(),
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
        "duration_seconds": s.duration_seconds,
        "status": s.status,
        "pagination_complete": s.pagination_complete,
        "pagination_reason": s.pagination_reason,
        "pages_fetched": s.pages_fetched,
        "raw_discovered": s.raw_discovered,
        "unique_markets": s.unique_markets,
        "eligible_30d": s.eligible_30d,
        "analysed": s.analysed,
        "directional": s.directional,
        "funnel": s.funnel,
        "bucket_counts": s.bucket_counts,
        "top_ten_counts": s.top_ten_counts,
        "model_version": s.model_version,
        "calculation_version": s.calculation_version,
    }


class SignalReadService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def scan_status(self) -> dict:
        latest = await scan_store.latest_scan(self.session)
        if latest is None:
            return {
                "has_scan": False,
                "note": (
                    "No complete scan has been recorded yet. Signal Lab reads stored scan results; "
                    "the scheduled backend refresh performs the scan, never the browser."
                ),
            }
        now = utcnow()
        started = latest.started_at
        if started.tzinfo is None:
            from datetime import UTC
            started = started.replace(tzinfo=UTC)
        return {
            "has_scan": True,
            "generated_at": now.isoformat(),
            "seconds_since_scan": (now - started).total_seconds(),
            "buckets": [
                {"bucket": b, "label": BUCKET_LABELS[b], **(latest.bucket_counts.get(b, {}))}
                for b in PRIMARY_BUCKETS
            ],
            **_scan_summary(latest),
            "note": (
                "Top ten is a display limit only. Every eligible market within 30 days is "
                "analysed, "
                "ranked and stored; the full universe is preserved for research. Leaving this page "
                "open does not scan; the scheduled backend refresh does."
            ),
        }

    async def signals(
        self, *, bucket: str | None = None, scope: str = SCOPE_DIRECTIONAL, limit: int = 10
    ) -> dict:
        """Current signals for the latest scan, filtered by closing-time bucket + scope.

        ``public`` is capped at ``limit`` (ten) as a display subset; ``directional``/``full``/
        ``shadow`` return the complete matching set so the underlying universe is never hidden.
        """
        latest = await scan_store.latest_scan(self.session)
        if latest is None:
            return {"has_scan": False, "rows": [], "total_matching": 0}
        rows = await scan_store.snapshots_for_scan(self.session, latest.scan_id, bucket=bucket)

        if scope == SCOPE_PUBLIC:
            matching = [r for r in rows if r.public_top_ten]
        elif scope == SCOPE_SHADOW:
            matching = [r for r in rows if r.shadow_directional]
        elif scope == SCOPE_FULL:
            matching = list(rows)
        else:  # directional
            matching = [r for r in rows if r.direction in ("up", "down")]

        matching.sort(key=lambda r: (r.rank_in_bucket is None, r.rank_in_bucket or 1 << 30))
        shown = matching[:limit] if scope == SCOPE_PUBLIC else matching
        eligible_in_bucket = len(rows)
        directional_in_bucket = sum(1 for r in rows if r.direction in ("up", "down"))
        # Server-side trajectory per shown market (prompt section 19: the frontend never infers
        # trajectory state). Computed from that market's full stored snapshot history.
        now = utcnow()
        out_rows = []
        for r in shown:
            d = _row_public(r)
            hist = await scan_store.snapshots_for_market(self.session, r.market_id)
            snaps = [
                Snap(
                    captured_at=h.captured_at, strength=h.strength, direction=h.direction,
                    rank_in_bucket=h.rank_in_bucket, research_priority=h.research_priority,
                    evidence_families=tuple(h.evidence_families or ()),
                )
                for h in hist
            ]
            t = compute_trajectory(snaps, now=now)
            d["trajectory"] = {
                "label": t.label,
                "strength_change_prev": t.strength_change_prev,
                "change_1h": t.change_1h,
                "consecutive_same_direction": t.consecutive_same_direction,
                "first_detected": t.first_detected.isoformat() if t.first_detected else None,
                "scans": t.scans,
            }
            out_rows.append(d)
        return {
            "has_scan": True,
            "scan_id": latest.scan_id,
            "bucket": bucket,
            "bucket_label": BUCKET_LABELS.get(bucket or "", bucket),
            "scope": scope,
            "eligible_in_bucket": eligible_in_bucket,
            "directional_in_bucket": directional_in_bucket,
            "total_matching": len(matching),
            "shown": len(shown),
            "rows": out_rows,
            # The line the UI shows so ten is never read as "only ten analysed".
            "coverage_caption": (
                f"Top {min(limit, len(matching))} shown from {eligible_in_bucket} eligible markets"
                if scope == SCOPE_PUBLIC
                else f"{len(matching)} of {eligible_in_bucket} eligible markets in this window"
            ),
        }

    async def market_history(self, market_id: str, *, now: datetime | None = None) -> dict:
        """Per-market signal history + trajectory across stored scans (prompt sections 11, 12)."""
        now = now or utcnow()
        rows = await scan_store.snapshots_for_market(self.session, market_id)
        if not rows:
            return {"market_id": market_id, "has_history": False,
                    "snapshots": [], "trajectory": None}
        snaps = [
            Snap(
                captured_at=r.captured_at, strength=r.strength, direction=r.direction,
                rank_in_bucket=r.rank_in_bucket, research_priority=r.research_priority,
                evidence_families=tuple(r.evidence_families or ()),
            )
            for r in rows
        ]
        traj = compute_trajectory(snaps, now=now)
        return {
            "market_id": market_id,
            "has_history": True,
            "market_question": rows[-1].market_question,
            "outcome_name": rows[-1].outcome_name,
            "snapshots": [
                {
                    "captured_at": r.captured_at.isoformat(),
                    "scan_id": r.scan_id,
                    "strength": r.strength,
                    "direction": r.direction,
                    "research_priority": r.research_priority,
                    "rank_in_bucket": r.rank_in_bucket,
                    "bucket": r.bucket,
                    "midpoint": r.midpoint,
                    "time_remaining_hours": r.time_remaining_hours,
                }
                for r in rows
            ],
            "trajectory": traj.as_dict(),
        }
