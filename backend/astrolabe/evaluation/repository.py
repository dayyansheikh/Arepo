"""Persistence for the cohort engine: the only place that touches the evaluation ORM.

Mutating a frozen cohort (adding, removing, re-ranking or rescoring an entry) raises
``CohortFrozenError`` here, so immutability is a hard guarantee rather than a
convention. Uniqueness constraints in ``models.py`` plus the get-or-create helpers make
every scheduler command idempotent. Callers own the session and commit their unit of
work; these methods ``flush`` so ids are available but do not commit.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .errors import CohortFrozenError
from .models import (
    CalculationVersionRow,
    CohortEntryRow,
    EvaluationResultRow,
    ForwardPriceObservationRow,
    MarketResolutionRow,
    RankingAuditRow,
    SignalSnapshotRow,
    WeeklyCohortRow,
)
from .ranking import selection_key
from .snapshots import SnapshotInput


def _utc(dt: datetime | None) -> datetime | None:
    """Reattach UTC if a driver returned a naive datetime (SQLite drops tzinfo)."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _now() -> datetime:
    return datetime.now(UTC)


class EvaluationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -- calculation versions ---------------------------------------------------
    async def ensure_calculation_version(self, version: str, description: str = "") -> None:
        existing = await self.session.get(CalculationVersionRow, version)
        if existing is None:
            self.session.add(
                CalculationVersionRow(
                    version=version, description=description, created_at=_now()
                )
            )
            await self.session.flush()

    # -- cohorts ----------------------------------------------------------------
    async def get_cohort(self, iso_year: int, iso_week: int) -> WeeklyCohortRow | None:
        res = await self.session.execute(
            select(WeeklyCohortRow).where(
                WeeklyCohortRow.iso_year == iso_year,
                WeeklyCohortRow.iso_week == iso_week,
            )
        )
        return res.scalar_one_or_none()

    async def get_cohort_by_id(self, cohort_id: int) -> WeeklyCohortRow | None:
        return await self.session.get(WeeklyCohortRow, cohort_id)

    async def list_cohorts(self) -> list[WeeklyCohortRow]:
        res = await self.session.execute(
            select(WeeklyCohortRow).order_by(
                WeeklyCohortRow.iso_year.desc(), WeeklyCohortRow.iso_week.desc()
            )
        )
        return list(res.scalars().all())

    async def create_cohort(
        self,
        *,
        iso_year: int,
        iso_week: int,
        week_start: datetime,
        cutoff_at: datetime,
        provenance_class: str,
        calculation_version: str,
        target_size: int,
    ) -> WeeklyCohortRow:
        row = WeeklyCohortRow(
            iso_year=iso_year,
            iso_week=iso_week,
            week_start=week_start,
            cutoff_at=cutoff_at,
            provenance_class=provenance_class,
            calculation_version=calculation_version,
            target_size=target_size,
            actual_size=0,
            frozen=False,
            created_at=_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    # -- snapshots --------------------------------------------------------------
    async def add_snapshot(self, snap: SnapshotInput) -> SignalSnapshotRow:
        """Idempotent by snapshot_ref: the same instant re-ingested returns one row."""
        res = await self.session.execute(
            select(SignalSnapshotRow).where(
                SignalSnapshotRow.snapshot_ref == snap.snapshot_ref
            )
        )
        existing = res.scalar_one_or_none()
        if existing is not None:
            return existing
        row = SignalSnapshotRow(
            snapshot_ref=snap.snapshot_ref,
            calculation_version=snap.calculation_version,
            captured_at=snap.captured_at,
            source_timestamp=snap.source_timestamp,
            market_id=snap.market_id,
            condition_id=snap.condition_id,
            event_id=snap.event_id,
            token_id=snap.token_id,
            market_question=snap.market_question,
            outcome_name=snap.outcome_name,
            direction=snap.direction,
            strength=snap.strength,
            confidence=snap.confidence,
            data_quality=snap.data_quality,
            value=snap.value,
            entry_price=snap.entry_price,
            best_bid=snap.best_bid,
            best_ask=snap.best_ask,
            midpoint=snap.midpoint,
            spread=snap.spread,
            volume=snap.volume,
            near_mid_depth=snap.near_mid_depth,
            lookback_size=snap.lookback_size,
            component_scores=snap.component_scores,
            expected_close=snap.expected_close,
            created_at=_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    # -- entries ----------------------------------------------------------------
    async def get_entries(self, cohort_id: int) -> list[CohortEntryRow]:
        res = await self.session.execute(
            select(CohortEntryRow)
            .where(CohortEntryRow.cohort_id == cohort_id)
            .order_by(CohortEntryRow.rank.asc())
        )
        return list(res.scalars().all())

    async def get_entry_slot(
        self, cohort_id: int, market_id: str, token_id: str
    ) -> CohortEntryRow | None:
        res = await self.session.execute(
            select(CohortEntryRow).where(
                CohortEntryRow.cohort_id == cohort_id,
                CohortEntryRow.market_id == market_id,
                CohortEntryRow.token_id == token_id,
            )
        )
        return res.scalar_one_or_none()

    async def get_market_entry(self, cohort_id: int, market_id: str) -> CohortEntryRow | None:
        """The single entry representing a market, if any. One entry per market keeps a
        single market from taking multiple weekly slots (anti-concentration rule)."""
        res = await self.session.execute(
            select(CohortEntryRow).where(
                CohortEntryRow.cohort_id == cohort_id,
                CohortEntryRow.market_id == market_id,
            )
        )
        return res.scalars().first()

    async def add_entry(
        self, cohort: WeeklyCohortRow, snap: SignalSnapshotRow, rank: int
    ) -> CohortEntryRow:
        self._guard(cohort)
        row = CohortEntryRow(
            cohort_id=cohort.id,
            snapshot_id=snap.id,
            rank=rank,
            market_id=snap.market_id,
            token_id=snap.token_id,
            condition_id=snap.condition_id,
            event_id=snap.event_id,
            market_question=snap.market_question,
            outcome_name=snap.outcome_name,
            direction=snap.direction,
            entry_price=snap.entry_price,
            best_bid=snap.best_bid,
            best_ask=snap.best_ask,
            midpoint=snap.midpoint,
            spread=snap.spread,
            volume=snap.volume,
            near_mid_depth=snap.near_mid_depth,
            lookback_size=snap.lookback_size,
            strength=snap.strength,
            confidence=snap.confidence,
            data_quality=snap.data_quality,
            value=snap.value,
            component_scores=snap.component_scores,
            signal_timestamp=snap.captured_at,
            expected_close=snap.expected_close,
            frozen=False,
            created_at=_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def replace_entry_snapshot(
        self, cohort: WeeklyCohortRow, entry: CohortEntryRow, snap: SignalSnapshotRow
    ) -> None:
        """Retarget a provisional slot to a stronger snapshot of the SAME market (the
        outcome may differ, e.g. the other side of a binary market later fires harder).
        market_id is unchanged; the slot always represents one market. Refused once
        frozen."""
        self._guard(cohort)
        entry.snapshot_id = snap.id
        entry.token_id = snap.token_id
        entry.condition_id = snap.condition_id
        entry.event_id = snap.event_id
        entry.market_question = snap.market_question
        entry.outcome_name = snap.outcome_name
        entry.strength = snap.strength
        entry.confidence = snap.confidence
        entry.data_quality = snap.data_quality
        entry.value = snap.value
        entry.direction = snap.direction
        entry.entry_price = snap.entry_price
        entry.best_bid = snap.best_bid
        entry.best_ask = snap.best_ask
        entry.midpoint = snap.midpoint
        entry.spread = snap.spread
        entry.volume = snap.volume
        entry.near_mid_depth = snap.near_mid_depth
        entry.lookback_size = snap.lookback_size
        entry.component_scores = snap.component_scores
        entry.signal_timestamp = snap.captured_at
        entry.expected_close = snap.expected_close
        await self.session.flush()

    async def remove_entry(self, cohort: WeeklyCohortRow, entry: CohortEntryRow) -> None:
        self._guard(cohort)
        await self.session.delete(entry)
        await self.session.flush()

    async def set_rank(self, cohort: WeeklyCohortRow, entry: CohortEntryRow, rank: int) -> None:
        self._guard(cohort)
        entry.rank = rank
        await self.session.flush()

    async def add_audit(
        self,
        cohort_id: int,
        action: str,
        *,
        snapshot_id: int | None = None,
        replaced_snapshot_id: int | None = None,
        rank: int | None = None,
        strength: float | None = None,
        note: str = "",
    ) -> None:
        self.session.add(
            RankingAuditRow(
                cohort_id=cohort_id,
                at=_now(),
                action=action,
                snapshot_id=snapshot_id,
                replaced_snapshot_id=replaced_snapshot_id,
                rank=rank,
                strength=strength,
                note=note,
            )
        )
        await self.session.flush()

    async def get_audit(self, cohort_id: int) -> list[RankingAuditRow]:
        res = await self.session.execute(
            select(RankingAuditRow)
            .where(RankingAuditRow.cohort_id == cohort_id)
            .order_by(RankingAuditRow.id.asc())
        )
        return list(res.scalars().all())

    async def freeze_cohort(self, cohort: WeeklyCohortRow) -> WeeklyCohortRow:
        """Assign permanent ranks and lock the cohort. Idempotent: a frozen cohort is
        returned unchanged."""
        if cohort.frozen:
            return cohort
        entries = await self.get_entries(cohort.id)
        entries.sort(
            key=lambda e: selection_key(
                strength=e.strength,
                confidence=e.confidence,
                data_quality=e.data_quality,
                captured_at=_utc(e.signal_timestamp),
                tiebreak=e.id,
            )
        )
        for i, e in enumerate(entries, start=1):
            e.rank = i
            e.frozen = True
        cohort.frozen = True
        cohort.frozen_at = _now()
        cohort.actual_size = len(entries)
        await self.session.flush()
        return cohort

    # -- forward observations ---------------------------------------------------
    async def get_forward(self, entry_id: int) -> list[ForwardPriceObservationRow]:
        res = await self.session.execute(
            select(ForwardPriceObservationRow)
            .where(ForwardPriceObservationRow.entry_id == entry_id)
            .order_by(ForwardPriceObservationRow.id.asc())
        )
        return list(res.scalars().all())

    async def add_forward(
        self,
        entry_id: int,
        horizon: str,
        *,
        observed_at: datetime,
        price: float | None,
        source_timestamp: datetime | None = None,
    ) -> tuple[ForwardPriceObservationRow, bool]:
        """Idempotent per (entry, horizon). Returns (row, created)."""
        res = await self.session.execute(
            select(ForwardPriceObservationRow).where(
                ForwardPriceObservationRow.entry_id == entry_id,
                ForwardPriceObservationRow.horizon == horizon,
            )
        )
        existing = res.scalar_one_or_none()
        if existing is not None:
            return existing, False
        row = ForwardPriceObservationRow(
            entry_id=entry_id,
            horizon=horizon,
            observed_at=observed_at,
            price=price,
            source_timestamp=source_timestamp,
            created_at=_now(),
        )
        self.session.add(row)
        await self.session.flush()
        return row, True

    # -- resolutions ------------------------------------------------------------
    async def get_resolution(self, market_id: str) -> MarketResolutionRow | None:
        return await self.session.get(MarketResolutionRow, market_id)

    async def upsert_resolution(
        self,
        market_id: str,
        *,
        condition_id: str | None,
        resolved: bool,
        resolved_outcome: str | None,
        resolved_token_id: str | None,
        resolved_at: datetime | None,
        source: str | None,
    ) -> MarketResolutionRow:
        row = await self.session.get(MarketResolutionRow, market_id)
        if row is None:
            row = MarketResolutionRow(market_id=market_id, updated_at=_now())
            self.session.add(row)
        row.condition_id = condition_id
        row.resolved = resolved
        row.resolved_outcome = resolved_outcome
        row.resolved_token_id = resolved_token_id
        row.resolved_at = resolved_at
        row.source = source
        row.updated_at = _now()
        await self.session.flush()
        return row

    # -- evaluation results -----------------------------------------------------
    async def get_evaluation(self, entry_id: int) -> EvaluationResultRow | None:
        res = await self.session.execute(
            select(EvaluationResultRow).where(EvaluationResultRow.entry_id == entry_id)
        )
        return res.scalar_one_or_none()

    async def upsert_evaluation(
        self,
        entry_id: int,
        *,
        movement_horizon: str | None,
        raw_prob_movement: float | None,
        movement_correct: bool | None,
        resolved: bool,
        resolution_correct: bool | None,
        pending: bool,
        hypothetical_value: float | None,
    ) -> EvaluationResultRow:
        row = await self.get_evaluation(entry_id)
        if row is None:
            row = EvaluationResultRow(entry_id=entry_id, computed_at=_now())
            self.session.add(row)
        row.movement_horizon = movement_horizon
        row.raw_prob_movement = raw_prob_movement
        row.movement_correct = movement_correct
        row.resolved = resolved
        row.resolution_correct = resolution_correct
        row.pending = pending
        row.hypothetical_value = hypothetical_value
        row.computed_at = _now()
        await self.session.flush()
        return row

    # -- guard ------------------------------------------------------------------
    @staticmethod
    def _guard(cohort: WeeklyCohortRow) -> None:
        if cohort.frozen:
            raise CohortFrozenError(
                f"cohort {cohort.iso_year}-W{cohort.iso_week:02d} is frozen and immutable"
            )
