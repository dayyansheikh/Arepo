"""Provisional weekly ranking and the weekly freeze.

During the live week the engine keeps a provisional top ten of the strongest
*qualifying* signals, seeing only information available at each calculation timestamp.
A stronger qualifying signal replaces the current lowest entry; one market never holds
two slots (anti-concentration). At the cut-off the cohort is frozen and becomes
permanently immutable. Every provisional change is written to the ranking audit.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from .constants import (
    CALCULATION_VERSION,
    COHORT_TARGET_SIZE,
    PROVENANCE_PROSPECTIVE,
)
from .models import CohortEntryRow, WeeklyCohortRow
from .ranking import is_eligible, selection_key, week_bounds
from .repository import EvaluationRepository, _utc
from .snapshots import SnapshotInput


def _snap_key(s: SnapshotInput) -> tuple:
    return selection_key(
        strength=s.strength,
        confidence=s.confidence,
        data_quality=s.data_quality,
        captured_at=_utc(s.captured_at),
        tiebreak=s.snapshot_ref,
    )


def _entry_key(e: CohortEntryRow) -> tuple:
    return selection_key(
        strength=e.strength,
        confidence=e.confidence,
        data_quality=e.data_quality,
        captured_at=_utc(e.signal_timestamp),
        tiebreak=e.id,
    )


async def _rerank(repo: EvaluationRepository, cohort: WeeklyCohortRow) -> None:
    entries = await repo.get_entries(cohort.id)
    entries.sort(key=_entry_key)
    for i, e in enumerate(entries, start=1):
        if e.rank != i:
            await repo.set_rank(cohort, e, i)


async def get_or_create_current_cohort(
    session: AsyncSession,
    *,
    at: datetime,
    provenance_class: str = PROVENANCE_PROSPECTIVE,
    calculation_version: str = CALCULATION_VERSION,
    target_size: int = COHORT_TARGET_SIZE,
) -> WeeklyCohortRow:
    repo = EvaluationRepository(session)
    await repo.ensure_calculation_version(calculation_version, "Arepo composite anomaly v1")
    iso_year, iso_week, week_start, cutoff_at = week_bounds(at)
    cohort = await repo.get_cohort(iso_year, iso_week)
    if cohort is None:
        cohort = await repo.create_cohort(
            iso_year=iso_year,
            iso_week=iso_week,
            week_start=week_start,
            cutoff_at=cutoff_at,
            provenance_class=provenance_class,
            calculation_version=calculation_version,
            target_size=target_size,
        )
    return cohort


async def update_rankings(
    session: AsyncSession,
    *,
    snapshots: list[SnapshotInput],
    at: datetime,
    provenance_class: str = PROVENANCE_PROSPECTIVE,
    calculation_version: str = CALCULATION_VERSION,
    target_size: int = COHORT_TARGET_SIZE,
) -> WeeklyCohortRow:
    """Ingest snapshots and update the current week's provisional top ten.

    Idempotent: snapshots dedupe by ref, and re-running with the same inputs converges
    to the same set (a signal already represented at equal-or-greater strength causes no
    change). If the week is already frozen this is a safe no-op.
    """
    repo = EvaluationRepository(session)
    cohort = await get_or_create_current_cohort(
        session,
        at=at,
        provenance_class=provenance_class,
        calculation_version=calculation_version,
        target_size=target_size,
    )
    if cohort.frozen:
        # The week closed. Never touch a frozen cohort; nothing to do.
        return cohort

    # Record every provided snapshot as immutable provenance (dedup by ref).
    rows = {}
    for snap in snapshots:
        rows[snap.snapshot_ref] = await repo.add_snapshot(snap)

    # Consider only qualifying signals, strongest first (deterministic).
    eligible = [
        s
        for s in snapshots
        if is_eligible(
            strength=s.strength, data_quality=s.data_quality, entry_price=s.entry_price
        )
    ]
    eligible.sort(key=_snap_key)

    for snap in eligible:
        snap_row = rows[snap.snapshot_ref]
        market_entry = await repo.get_market_entry(cohort.id, snap.market_id)
        if market_entry is not None:
            # This market already holds a slot. Upgrade it only if the new signal is
            # strictly stronger than what is stored (keeps the strongest per market).
            if _snap_key(snap) < _entry_key(market_entry):
                replaced = market_entry.snapshot_id
                await repo.replace_entry_snapshot(cohort, market_entry, snap_row)
                await repo.add_audit(
                    cohort.id,
                    "replace",
                    snapshot_id=snap_row.id,
                    replaced_snapshot_id=replaced,
                    strength=snap.strength,
                    note="stronger signal for a market already selected",
                )
            else:
                await repo.add_audit(
                    cohort.id, "skip", snapshot_id=snap_row.id, strength=snap.strength,
                    note="market already represented by an equal-or-stronger signal",
                )
            continue

        entries = await repo.get_entries(cohort.id)
        if len(entries) < cohort.target_size:
            await repo.add_entry(cohort, snap_row, rank=len(entries) + 1)
            await repo.add_audit(
                cohort.id, "enter", snapshot_id=snap_row.id, strength=snap.strength,
                note="entered a free provisional slot",
            )
        else:
            weakest = max(entries, key=_entry_key)
            if _snap_key(snap) < _entry_key(weakest):
                replaced = weakest.snapshot_id
                await repo.remove_entry(cohort, weakest)
                await repo.add_entry(cohort, snap_row, rank=weakest.rank)
                await repo.add_audit(
                    cohort.id, "replace", snapshot_id=snap_row.id,
                    replaced_snapshot_id=replaced, strength=snap.strength,
                    note="stronger than the lowest provisional entry",
                )
            else:
                await repo.add_audit(
                    cohort.id, "skip", snapshot_id=snap_row.id, strength=snap.strength,
                    note="not stronger than the lowest provisional entry",
                )

    await _rerank(repo, cohort)
    cohort.actual_size = len(await repo.get_entries(cohort.id))
    await session.commit()
    return cohort


async def freeze_week(
    session: AsyncSession, *, at: datetime, note: str | None = None
) -> WeeklyCohortRow | None:
    """Freeze the cohort for ``at``'s week. Idempotent (a frozen cohort is returned
    unchanged). Returns None if no cohort exists for that week."""
    repo = EvaluationRepository(session)
    iso_year, iso_week, _, _ = week_bounds(at)
    cohort = await repo.get_cohort(iso_year, iso_week)
    if cohort is None:
        return None
    already = cohort.frozen
    await repo.freeze_cohort(cohort)
    if not already and note is None and cohort.actual_size < cohort.target_size:
        cohort.note = (
            f"Only {cohort.actual_size} signals qualified this week; froze the actual "
            f"qualifying number rather than padding to {cohort.target_size}."
        )
    elif note is not None and not already:
        cohort.note = note
    await session.commit()
    return cohort
