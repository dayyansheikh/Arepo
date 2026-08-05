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
            created_at=_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def freeze_cohort(
        self, cohort: ResearchCohortRow, *, frozen_at: datetime | None = None
    ) -> bool:
        """Freeze a cohort and record its counts. Idempotent: returns False if already frozen.

        ``frozen_at`` records WHEN the entry prices were captured (defaults to now); the forward
        collector uses it as the causal reference so a horizon that predates the freeze is never
        backfilled. Tests pass it explicitly to keep the controlled clock deterministic.
        """
        if cohort.frozen:
            return False
        entries = await self.get_entries(cohort.id)
        cohort.universe_size = len(entries)
        cohort.directional_count = sum(1 for e in entries if e.direction in ("up", "down"))
        cohort.public_selection_count = sum(1 for e in entries if e.role == "public_selection")
        cohort.shadow_count = sum(1 for e in entries if e.role == "shadow_directional")
        cohort.observation_count = sum(1 for e in entries if e.role == "observation")
        cohort.abstention_count = sum(1 for e in entries if e.role == "abstention_control")
        cohort.frozen = True
        cohort.frozen_at = frozen_at or _now()
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

    # -- forward observations --------------------------------------------------
    async def get_forward(self, entry_id: int) -> dict[str, ResearchForwardRow]:
        res = await self.session.execute(
            select(ResearchForwardRow).where(ResearchForwardRow.entry_id == entry_id)
        )
        return {r.horizon: r for r in res.scalars().all()}

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
    ) -> bool:
        """Insert one forward observation if absent. Idempotent on (entry, horizon): a real
        observation is never overwritten once recorded (returns False)."""
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
