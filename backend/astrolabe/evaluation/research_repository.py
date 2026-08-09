"""Persistence for the edge-research cohorts. The only place that touches the research ORM.

Mirrors ``repository.py``: callers own the session and commit; these methods ``flush`` so ids are
available. Freezing is idempotent (get-or-create on the (cadence, cutoff_at) unique key) and a
frozen cohort can never gain, drop or alter an entry (raises ``CohortFrozenError``). Forward
observations upsert on (entry, horizon) so re-running the collector never duplicates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .errors import CohortFrozenError
from .research_models import (
    ResearchCohortRow,
    ResearchEntryRow,
    ResearchForwardRow,
    ResearchRevisionRow,
)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class EntryInput:
    role: str
    rank: int | None
    walk_forward_partition: str
    market_id: str
    condition_id: str | None
    event_id: str | None
    token_id: str
    market_question: str
    outcome_name: str
    direction: str | None
    momentum_direction: str | None
    orderbook_direction: str | None
    tradeflow_direction: str | None
    signal_classification: str
    strength: float
    confidence: float
    research_priority: int
    n_families: int
    evidence_families: list
    component_scores: list
    component_availability: dict
    data_quality: str
    entry_price: float | None
    best_bid: float | None
    best_ask: float | None
    midpoint: float | None
    spread: float | None
    near_mid_depth: float | None
    liquidity: float | None
    volume: float | None
    data_age_seconds: float | None
    expected_close: datetime | None
    time_remaining_hours: float | None
    intended_horizons: list
    # Short-horizon universe membership (final-completion prompt C1). Optional so existing callers
    # (the legacy freeze) need not set them.
    # Category is likewise optional for legacy/manual freezes; complete-scan freezes always supply
    # the value classified from point-in-time metadata.
    primary_category: str | None = None
    bucket: str | None = None
    overall_rank_30d: int | None = None
    public_selected: bool | None = None


class ResearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -- cohorts ---------------------------------------------------------------
    async def get_cohort(self, cadence: str, cutoff_at: datetime) -> ResearchCohortRow | None:
        res = await self.session.execute(
            select(ResearchCohortRow).where(
                ResearchCohortRow.cadence == cadence,
                ResearchCohortRow.cutoff_at == cutoff_at,
            )
        )
        return res.scalar_one_or_none()

    async def get_or_create_cohort(
        self, *, cadence: str, cutoff_at: datetime, model_version: str, calculation_version: str
    ) -> tuple[ResearchCohortRow, bool]:
        existing = await self.get_cohort(cadence, cutoff_at)
        if existing is not None:
            return existing, False
        row = ResearchCohortRow(
            cadence=cadence,
            cutoff_at=cutoff_at,
            model_version=model_version,
            calculation_version=calculation_version,
            provenance_class="prospective",
            frozen=False,
            created_at=_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row, True

    async def add_entry(self, cohort: ResearchCohortRow, e: EntryInput) -> ResearchEntryRow:
        """Insert one screened entry. Raises if the cohort is already frozen; idempotent on the
        (cohort, market, token) unique key (returns the existing row)."""
        if cohort.frozen:
            raise CohortFrozenError(
                f"research cohort {cohort.cadence}@{cohort.cutoff_at} is frozen; cannot add entries"
            )
        res = await self.session.execute(
            select(ResearchEntryRow).where(
                ResearchEntryRow.cohort_id == cohort.id,
                ResearchEntryRow.market_id == e.market_id,
                ResearchEntryRow.token_id == e.token_id,
            )
        )
        found = res.scalar_one_or_none()
        if found is not None:
            return found
        row = ResearchEntryRow(
            cohort_id=cohort.id,
            role=e.role,
            rank=e.rank,
            walk_forward_partition=e.walk_forward_partition,
            market_id=e.market_id,
            condition_id=e.condition_id,
            event_id=e.event_id,
            token_id=e.token_id,
            market_question=e.market_question,
            outcome_name=e.outcome_name,
            primary_category=e.primary_category,
            direction=e.direction,
            momentum_direction=e.momentum_direction,
            orderbook_direction=e.orderbook_direction,
            tradeflow_direction=e.tradeflow_direction,
            signal_classification=e.signal_classification,
            strength=e.strength,
            confidence=e.confidence,
            research_priority=e.research_priority,
            n_families=e.n_families,
            evidence_families=e.evidence_families,
            component_scores=e.component_scores,
            component_availability=e.component_availability,
            data_quality=e.data_quality,
            entry_price=e.entry_price,
            best_bid=e.best_bid,
            best_ask=e.best_ask,
            midpoint=e.midpoint,
            spread=e.spread,
            near_mid_depth=e.near_mid_depth,
            liquidity=e.liquidity,
            volume=e.volume,
            data_age_seconds=e.data_age_seconds,
            expected_close=e.expected_close,
            time_remaining_hours=e.time_remaining_hours,
            intended_horizons=e.intended_horizons,
            bucket=e.bucket,
            overall_rank_30d=e.overall_rank_30d,
            public_selected=e.public_selected,
            created_at=_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def freeze_cohort(
        self, cohort: ResearchCohortRow, *, frozen_at: datetime | None = None,
        excluded_markets: int = 0, degraded: bool = False,
    ) -> bool:
        """Freeze a cohort + record counts and causal timing. Idempotent: False if already frozen.

        ``frozen_at`` records WHEN the prediction was actually made (defaults to now). It becomes
        cohort's ``evaluation_origin_at`` - the single causal origin every forward horizon, entry
        timestamp and time-to-close is measured from. Lateness (frozen_at - cutoff_at, the scheduled
        boundary) is recorded and the late / excessively-late flags set from it.
        """
        from .research_constants import LATENESS_MAX_SECONDS, LATENESS_WARN_SECONDS

        if cohort.frozen:
            return False
        origin = frozen_at or _now()
        scheduled = _utc(cohort.cutoff_at)
        lateness = max(0.0, (origin - scheduled).total_seconds()) if scheduled else 0.0
        entries = await self.get_entries(cohort.id)
        cohort.universe_size = len(entries)
        cohort.directional_count = sum(1 for e in entries if e.direction in ("up", "down"))
        cohort.public_selection_count = sum(1 for e in entries if e.role == "public_selection")
        cohort.shadow_count = sum(1 for e in entries if e.role == "shadow_directional")
        cohort.observation_count = sum(1 for e in entries if e.role == "observation")
        cohort.abstention_count = sum(1 for e in entries if e.role == "abstention_control")
        cohort.excluded_markets = excluded_markets
        cohort.degraded = degraded
        cohort.frozen = True
        cohort.frozen_at = origin
        cohort.evaluation_origin_at = origin  # causal origin == actual prediction time
        cohort.lateness_seconds = lateness
        cohort.late = lateness > LATENESS_WARN_SECONDS
        cohort.excessively_late = lateness > LATENESS_MAX_SECONDS
        await self.session.flush()
        return True

    async def add_revision(self, cohort_id: int, reason: str, detail: dict) -> None:
        self.session.add(
            ResearchRevisionRow(cohort_id=cohort_id, at=_now(), reason=reason, detail=detail)
        )
        await self.session.flush()

    # -- reads -----------------------------------------------------------------
    async def get_entries(self, cohort_id: int) -> list[ResearchEntryRow]:
        res = await self.session.execute(
            select(ResearchEntryRow)
            .where(ResearchEntryRow.cohort_id == cohort_id)
            .order_by(ResearchEntryRow.rank.is_(None), ResearchEntryRow.rank, ResearchEntryRow.id)
        )
        return list(res.scalars().all())

    async def list_cohorts(
        self, *, cadence: str | None = None, provenance: str | None = None,
        frozen: bool | None = None,
    ) -> list[ResearchCohortRow]:
        q = select(ResearchCohortRow)
        if cadence is not None:
            q = q.where(ResearchCohortRow.cadence == cadence)
        if provenance is not None:
            q = q.where(ResearchCohortRow.provenance_class == provenance)
        if frozen is not None:
            q = q.where(ResearchCohortRow.frozen == frozen)
        q = q.order_by(ResearchCohortRow.cutoff_at.desc())
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def entry_count(self, cohort_id: int) -> int:
        return await self.session.scalar(
            select(func.count(ResearchEntryRow.id)).where(
                ResearchEntryRow.cohort_id == cohort_id
            )
        ) or 0

    async def incomplete_cohorts(self) -> list[dict]:
        """Cohorts that are provably incomplete (prompt section 4): never frozen, or frozen with an
        entry count that disagrees with the recorded universe size. Valid frozen cohorts are never
        included, so a repair can act only on genuinely broken rows."""
        out: list[dict] = []
        for c in await self.list_cohorts():
            n = await self.entry_count(c.id)
            reason = None
            if not c.frozen:
                reason = "not frozen (freeze never completed)"
            elif n != c.universe_size:
                reason = f"frozen but entry count {n} != universe_size {c.universe_size}"
            if reason:
                out.append({
                    "id": c.id, "cadence": c.cadence, "cutoff_at": c.cutoff_at.isoformat(),
                    "frozen": c.frozen, "universe_size": c.universe_size, "entries": n,
                    "reason": reason,
                })
        return out

    async def delete_cohort(self, cohort_id: int) -> None:
        """Delete a cohort + its entries and forward rows. Only for proven-incomplete cohorts."""
        entries = await self.get_entries(cohort_id)
        for e in entries:
            for fwd in (await self.get_forward(e.id)).values():
                await self.session.delete(fwd)
            await self.session.delete(e)
        cohort = await self.session.get(ResearchCohortRow, cohort_id)
        if cohort is not None:
            await self.session.delete(cohort)
        await self.session.flush()

    # -- forward observations --------------------------------------------------
    async def get_forward(self, entry_id: int) -> dict[str, ResearchForwardRow]:
        res = await self.session.execute(
            select(ResearchForwardRow).where(ResearchForwardRow.entry_id == entry_id)
        )
        return {r.horizon: r for r in res.scalars().all()}

    async def forward_horizons_for_entries(
        self, entry_ids: list[int]
    ) -> dict[int, set[str]]:
        """Batch-load which (entry, horizon) forward observations already exist, in ONE query.

        Replaces a per-entry ``get_forward`` loop (thousands of sequential round-trips for a
        full-universe cohort) so the collector can decide what is due without hammering the DB.
        """
        out: dict[int, set[str]] = {eid: set() for eid in entry_ids}
        if not entry_ids:
            return out
        res = await self.session.execute(
            select(ResearchForwardRow.entry_id, ResearchForwardRow.horizon)
            .where(ResearchForwardRow.entry_id.in_(entry_ids))
        )
        for eid, horizon in res.all():
            out.setdefault(eid, set()).add(horizon)
        return out

    async def available_forward_horizons(self, entry_ids: list[int]) -> set[str]:
        """Horizons that have at least one stored observation WITH a usable midpoint, in ONE query.

        Replaces a per-entry ``get_forward`` scan (thousands of round-trips over the pooler) used to
        decide which Replay horizon tabs are populated for a cohort.
        """
        if not entry_ids:
            return set()
        res = await self.session.execute(
            select(ResearchForwardRow.horizon)
            .where(ResearchForwardRow.entry_id.in_(entry_ids),
                   ResearchForwardRow.midpoint.is_not(None))
            .distinct()
        )
        return {r[0] for r in res.all()}

    async def forwards_for_entries(
        self, entry_ids: list[int]
    ) -> dict[int, dict[str, ResearchForwardRow]]:
        """All forward observations for many entries in ONE query, as {entry_id: {horizon: row}}.

        Replaces the per-entry ``get_forward`` N+1 in the Replay result/breakdown path — the same
        stored rows, just fetched in a single round-trip instead of thousands.
        """
        out: dict[int, dict[str, ResearchForwardRow]] = {eid: {} for eid in entry_ids}
        if not entry_ids:
            return out
        res = await self.session.execute(
            select(ResearchForwardRow).where(ResearchForwardRow.entry_id.in_(entry_ids))
        )
        for row in res.scalars().all():
            out.setdefault(row.entry_id, {})[row.horizon] = row
        return out

    async def upsert_forward(
        self,
        *,
        entry_id: int,
        horizon: str,
        observed_at: datetime,
        midpoint: float | None,
        best_bid: float | None,
        best_ask: float | None,
        spread: float | None,
        near_mid_depth: float | None,
        source_timestamp: datetime | None,
        exact: bool,
        observation_delay_seconds: float | None,
        unavailable_reason: str | None,
        known_absent: bool = False,
    ) -> bool:
        """Insert one forward observation if absent. Idempotent on (entry, horizon): a real
        observation is never overwritten once recorded (returns False).

        ``known_absent`` skips the existence SELECT when the caller has already confirmed the row is
        absent via a batched load (e.g. ``forward_horizons_for_entries``), avoiding a per-row
        round-trip. The DB unique constraint on (entry, horizon) is the ultimate idempotency guard.
        """
        if not known_absent:
            existing = (await self.get_forward(entry_id)).get(horizon)
            if existing is not None:
                return False
        self.session.add(
            ResearchForwardRow(
                entry_id=entry_id,
                horizon=horizon,
                observed_at=observed_at,
                midpoint=midpoint,
                best_bid=best_bid,
                best_ask=best_ask,
                spread=spread,
                near_mid_depth=near_mid_depth,
                source_timestamp=source_timestamp,
                exact=exact,
                observation_delay_seconds=observation_delay_seconds,
                unavailable_reason=unavailable_reason,
                created_at=_now(),
            )
        )
        await self.session.flush()
        return True

    async def repair_incomplete(self) -> dict:
        """Remove NEVER-FROZEN incomplete cohorts (proven not completed) and REPORT frozen-but-
        mismatched cohorts without deleting them (frozen evidence is immutable; a human inspects).
        Returns a summary. Idempotent: a clean database returns empty lists."""
        incomplete = await self.incomplete_cohorts()
        removed, anomalies, skipped = [], [], []
        for row in incomplete:
            if not row["frozen"]:
                # Re-fetch and re-check frozen IMMEDIATELY before deleting: a legitimate freeze
                # retry may have frozen this same cohort between the snapshot and now. Deleting on
                # the stale snapshot would destroy real frozen evidence (DB review CRITICAL-2), so
                # any cohort that is now frozen is skipped.
                fresh = await self.session.get(ResearchCohortRow, row["id"])
                if fresh is None:
                    continue
                if fresh.frozen:
                    skipped.append(row)  # became valid between snapshot+delete; keep it
                    continue
                await self.delete_cohort(row["id"])
                removed.append(row)
            else:
                anomalies.append(row)  # frozen mismatch: report, never auto-delete
        await self.session.commit()
        return {
            "removed_incomplete": removed, "frozen_anomalies": anomalies,
            "skipped_now_frozen": skipped,
        }

    # -- counts (for research status, O(1)-ish) --------------------------------
    async def count_cohorts_by_cadence(self, provenance: str = "prospective") -> dict[str, int]:
        res = await self.session.execute(
            select(ResearchCohortRow.cadence, func.count(ResearchCohortRow.id))
            .where(
                ResearchCohortRow.provenance_class == provenance,
                ResearchCohortRow.frozen.is_(True),
            )
            .group_by(ResearchCohortRow.cadence)
        )
        return {c: n for c, n in res.all()}
