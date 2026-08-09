"""Freeze a real prospective cohort from a complete short-horizon scan (prompt C1, C2).

A cohort references a specific complete discovery scan and preserves the FULL eligible 30-day
universe (public top-20, shadow directional, observations and abstention controls), the bucket
membership, both rankings and the selection policy. It REFUSES an incomplete source scan, so a
normal cohort is never built from a partial universe. The pre-existing historical 60-market cohort
is never touched.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..evaluation.constants import CALCULATION_VERSION
from ..evaluation.research_constants import (
    MODEL_VERSION,
    ROLE_ABSTENTION,
    ROLE_OBSERVATION,
    ROLE_PUBLIC,
    ROLE_SHADOW,
)
from ..evaluation.research_engine import cadence_cutoff, freeze_from_inputs
from ..evaluation.research_repository import EntryInput
from .snapshot_models import ScanRunRow, SignalSnapshotRow

RESEARCH_HORIZONS = ["1h", "6h", "24h", "7d"]


def _role_for(snap: SignalSnapshotRow) -> str:
    if snap.direction in ("up", "down"):
        return ROLE_PUBLIC if snap.public_top_ten else ROLE_SHADOW
    if snap.signal_classification == "Non-directional anomaly":
        return ROLE_OBSERVATION
    return ROLE_ABSTENTION


def _entry_input(snap: SignalSnapshotRow) -> EntryInput:
    role = _role_for(snap)
    directional = snap.direction in ("up", "down")
    return EntryInput(
        role=role,
        rank=(snap.overall_rank_30d if directional else None),
        walk_forward_partition="live",
        market_id=snap.market_id,
        condition_id=snap.condition_id,
        event_id=snap.event_id,
        token_id=snap.token_id,
        market_question=snap.market_question,
        outcome_name=snap.outcome_name,
        primary_category=snap.primary_category,
        direction=snap.direction,
        momentum_direction=snap.momentum_direction,
        orderbook_direction=snap.orderbook_direction,
        tradeflow_direction=snap.tradeflow_direction,
        signal_classification=snap.signal_classification,
        strength=snap.strength,
        confidence=snap.confidence,
        research_priority=snap.research_priority,
        n_families=snap.n_families,
        evidence_families=list(snap.evidence_families or []),
        component_scores=list(snap.component_scores or []),
        component_availability=dict(snap.component_availability or {}),
        data_quality=snap.data_quality,
        entry_price=snap.midpoint,
        best_bid=snap.best_bid,
        best_ask=snap.best_ask,
        midpoint=snap.midpoint,
        spread=snap.spread,
        near_mid_depth=snap.near_mid_depth,
        liquidity=snap.liquidity,
        volume=snap.volume,
        data_age_seconds=snap.data_age_seconds,
        expected_close=snap.close_time,
        time_remaining_hours=snap.time_remaining_hours,
        intended_horizons=list(RESEARCH_HORIZONS),
        bucket=snap.bucket,
        overall_rank_30d=snap.overall_rank_30d,
        public_selected=snap.public_top_ten,
    )


async def latest_complete_scan(session: AsyncSession) -> ScanRunRow | None:
    res = await session.execute(
        select(ScanRunRow)
        .where(ScanRunRow.pagination_complete.is_(True))
        .order_by(ScanRunRow.started_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def freeze_cohort_from_scan(
    session: AsyncSession,
    *,
    cadence: str,
    scan_id: str | None = None,
    cutoff_at: datetime | None = None,
    frozen_at: datetime | None = None,
) -> dict:
    """Freeze a prospective cohort from a stored complete scan.

    ``scan_id`` defaults to the latest complete scan. Refuses if the source scan is incomplete
    (prompt C1). ``cutoff_at`` defaults to the cadence boundary for the scan's start; ``frozen_at``
    (the causal evaluation origin) defaults to the scan start time so outcomes are measured from the
    actual freeze.
    """
    if scan_id is not None:
        scan = await session.scalar(select(ScanRunRow).where(ScanRunRow.scan_id == scan_id))
    else:
        scan = await latest_complete_scan(session)
    if scan is None:
        return {"frozen": False, "reason": "no scan found"}
    if not scan.pagination_complete:
        return {
            "frozen": False, "refused": True,
            "reason": f"source scan {scan.scan_id} is incomplete; a normal cohort requires a "
                      f"complete scan ({scan.pagination_reason})",
        }

    rows = (await session.execute(
        select(SignalSnapshotRow).where(SignalSnapshotRow.scan_id == scan.scan_id)
    )).scalars().all()
    if not rows:
        return {"frozen": False, "reason": f"scan {scan.scan_id} has no stored snapshots"}

    started = scan.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    frozen = frozen_at or started
    cutoff = cutoff_at or cadence_cutoff(cadence, frozen)

    inputs = [_entry_input(s) for s in rows]
    result = await freeze_from_inputs(
        session, cadence=cadence, cutoff_at=cutoff, inputs=inputs,
        model_version=MODEL_VERSION, calculation_version=CALCULATION_VERSION,
        frozen_at=frozen, scan_id=scan.scan_id, scan_complete=True,
        selection_policy=scan.selection_policy, public_selection_limit=scan.public_selection_limit,
    )
    result["source_scan_id"] = scan.scan_id
    result["selection_policy"] = scan.selection_policy
    return result
