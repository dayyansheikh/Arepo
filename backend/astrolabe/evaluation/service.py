"""Read service (builds typed API responses) and runner (drives the scheduler commands).

The read side computes the two evaluation views from stored, backend-owned data so the
frontend never derives evaluation truth from client state. The runner turns the current
market analytics into immutable snapshots and applies the ranking/freeze/forward/
resolution/evaluation operations, wiring the injected providers to a MarketService.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..domain.models import utcnow
from . import engine, tracking
from .constants import (
    CALCULATION_VERSION,
    DEFAULT_FEE_RATE,
    DEFAULT_STAKE,
    HORIZON_24H,
    PROVENANCE_PROSPECTIVE,
    PROVENANCE_RECONSTRUCTED,
    PROVENANCE_SYNTHETIC,
    SPREAD_CROSS_FRACTION,
)
from .models import WeeklyCohortRow
from .portfolio import PositionResult, simulate_portfolio, value_position
from .repository import EvaluationRepository
from .schemas import (
    CohortDetail,
    CohortEntryOut,
    CohortSummary,
    CohortWeek,
    EntryEvaluation,
    ForwardObservation,
    PortfolioOut,
    PositionOut,
    ProvenanceOut,
    ResolutionOut,
)
from .snapshots import build_snapshot_input

_MARK_ORDER = ["7d", HORIZON_24H, "1h"]


def _week_label(iso_year: int, iso_week: int) -> str:
    return f"{iso_year}-W{iso_week:02d}"


def _cohort_week(c: WeeklyCohortRow) -> CohortWeek:
    return CohortWeek(
        iso_year=c.iso_year,
        iso_week=c.iso_week,
        label=_week_label(c.iso_year, c.iso_week),
        week_start=c.week_start,
        cutoff_at=c.cutoff_at,
        frozen=c.frozen,
        frozen_at=c.frozen_at,
        provenance_class=c.provenance_class,
        actual_size=c.actual_size,
        target_size=c.target_size,
    )


def _mark_price(forward: dict[str, float | None]) -> float | None:
    for h in _MARK_ORDER:
        if forward.get(h) is not None:
            return forward[h]
    return None


# ---------------------------------------------------------------------------------------
# Read side (API)
# ---------------------------------------------------------------------------------------
class CohortReadService:
    def __init__(self, session: AsyncSession):
        self.repo = EvaluationRepository(session)

    async def available_weeks(self) -> list[CohortWeek]:
        return [_cohort_week(c) for c in await self.repo.list_cohorts()]

    async def provenance(self) -> ProvenanceOut:
        cohorts = await self.repo.list_cohorts()
        prospective = [c for c in cohorts if c.provenance_class == PROVENANCE_PROSPECTIVE]
        first = min(
            prospective, key=lambda c: (c.iso_year, c.iso_week), default=None
        )
        return ProvenanceOut(
            calculation_version=CALCULATION_VERSION,
            first_prospective_week=(
                _week_label(first.iso_year, first.iso_week) if first else None
            ),
            prospective_weeks=len(prospective),
            reconstructed_weeks=sum(
                1 for c in cohorts if c.provenance_class == PROVENANCE_RECONSTRUCTED
            ),
            synthetic_weeks=sum(
                1 for c in cohorts if c.provenance_class == PROVENANCE_SYNTHETIC
            ),
            note=(
                "Prospective cohorts are real signals frozen at the weekly cut-off and "
                "tracked forward. Synthetic cohorts are clearly-labelled demonstrations "
                "and are never mixed into prospective statistics."
            ),
        )

    async def _entry_out(self, entry) -> tuple[CohortEntryOut, PositionResult]:
        forward_rows = await self.repo.get_forward(entry.id)
        forward = [
            ForwardObservation(horizon=o.horizon, observed_at=o.observed_at, price=o.price)
            for o in forward_rows
        ]
        forward_by_h = {o.horizon: o.price for o in forward_rows}
        res_row = await self.repo.get_resolution(entry.market_id)
        resolution = (
            ResolutionOut(
                resolved=res_row.resolved,
                resolved_outcome=res_row.resolved_outcome,
                resolved_token_id=res_row.resolved_token_id,
                resolved_at=res_row.resolved_at,
                source=res_row.source,
            )
            if res_row is not None
            else None
        )
        eval_row = await self.repo.get_evaluation(entry.id)
        evaluation = (
            EntryEvaluation(
                movement_horizon=eval_row.movement_horizon,
                raw_prob_movement=eval_row.raw_prob_movement,
                movement_correct=eval_row.movement_correct,
                resolved=eval_row.resolved,
                resolution_correct=eval_row.resolution_correct,
                pending=eval_row.pending,
                hypothetical_value=eval_row.hypothetical_value,
            )
            if eval_row is not None
            else None
        )
        resolved = bool(res_row and res_row.resolved)
        won = (res_row.resolved_token_id == entry.token_id) if resolved else None
        position = value_position(
            entry_id=entry.id,
            entry_price=entry.entry_price,
            spread=entry.spread,
            won=won,
            forward_price=_mark_price(forward_by_h),
        )
        out = CohortEntryOut(
            rank=entry.rank,
            market_id=entry.market_id,
            token_id=entry.token_id,
            condition_id=entry.condition_id,
            event_id=entry.event_id,
            market_question=entry.market_question,
            outcome_name=entry.outcome_name,
            direction=entry.direction,
            signal_timestamp=entry.signal_timestamp,
            expected_close=entry.expected_close,
            strength=entry.strength,
            confidence=entry.confidence,
            data_quality=entry.data_quality,
            value=entry.value,
            entry_price=entry.entry_price,
            best_bid=entry.best_bid,
            best_ask=entry.best_ask,
            midpoint=entry.midpoint,
            spread=entry.spread,
            volume=entry.volume,
            near_mid_depth=entry.near_mid_depth,
            lookback_size=entry.lookback_size,
            component_scores=entry.component_scores or [],
            forward=forward,
            resolution=resolution,
            evaluation=evaluation,
        )
        return out, position

    async def cohort_detail(self, iso_year: int, iso_week: int) -> CohortDetail | None:
        cohort = await self.repo.get_cohort(iso_year, iso_week)
        if cohort is None:
            return None
        entries = await self.repo.get_entries(cohort.id)
        entry_outs: list[CohortEntryOut] = []
        positions: list[PositionResult] = []
        moved_expected = moved_against = movement_pending = 0
        resolved_correct = resolved_incorrect = unresolved = 0
        for e in entries:
            out, pos = await self._entry_out(e)
            entry_outs.append(out)
            positions.append(pos)
            ev = out.evaluation
            if ev is None or ev.movement_correct is None:
                movement_pending += 1
            elif ev.movement_correct:
                moved_expected += 1
            else:
                moved_against += 1
            if ev is not None and ev.resolved:
                if ev.resolution_correct:
                    resolved_correct += 1
                else:
                    resolved_incorrect += 1
            else:
                unresolved += 1

        pos_outs = [
            PositionOut(
                rank=e.rank,
                market_question=e.market_question,
                outcome_name=e.outcome_name,
                status=p.status,
                entry_price=e.entry_price,
                fill=p.fill,
                exit_price=p.exit_price,
                value=round(p.value, 4),
                pnl=round(p.pnl, 4),
            )
            for e, p in zip(entries, positions, strict=False)
        ]
        pr = simulate_portfolio(positions)
        portfolio = PortfolioOut(
            stake_per_signal=pr.stake_per_signal,
            fee_rate=pr.fee_rate,
            spread_assumption=(
                f"Entry crosses {int(SPREAD_CROSS_FRACTION * 100)}% of the quoted spread; "
                f"fees {pr.fee_rate * 100:.1f}% of stake per position."
            ),
            total_allocated=round(pr.total_allocated, 2),
            realised_value=round(pr.realised_value, 2),
            unrealised_value=round(pr.unrealised_value, 2),
            pending_value=round(pr.pending_value, 2),
            completed_return=round(pr.completed_return, 2),
            completed_positions=pr.completed_positions,
            pending_positions=pr.pending_positions,
            positions=pos_outs,
        )
        summary = CohortSummary(
            week=_cohort_week(cohort),
            calculation_version=cohort.calculation_version or CALCULATION_VERSION,
            note=cohort.note,
            selected=len(entries),
            moved_expected=moved_expected,
            moved_against=moved_against,
            movement_pending=movement_pending,
            movement_horizon=HORIZON_24H,
            resolved_correct=resolved_correct,
            resolved_incorrect=resolved_incorrect,
            unresolved=unresolved,
            plain_summary=_plain_summary(
                len(entries), moved_expected, moved_against, movement_pending
            ),
        )
        return CohortDetail(summary=summary, entries=entry_outs, portfolio=portfolio)


def _plain_summary(selected: int, expected: int, against: int, pending: int) -> str:
    if selected == 0:
        return "No signals qualified for this week."
    return (
        f"Arepo selected {selected} qualifying "
        f"{'signal' if selected == 1 else 'signals'} this week. "
        f"Of those, {expected} later moved in the expected direction, "
        f"{against} moved against it and {pending} remain pending, "
        f"measured at the 24 hour horizon."
    )


# ---------------------------------------------------------------------------------------
# Runner (scheduler commands)
# ---------------------------------------------------------------------------------------
class CohortRunner:
    """Drives the idempotent scheduler operations against a live MarketService."""

    def __init__(self, market_service, *, mode: str = "live"):
        self.market_service = market_service
        self.mode = mode

    async def _snapshots(self, at: datetime, limit: int | None):
        pairs, _ = await self.market_service.enrich_markets(
            requested_mode=self.mode, limit=limit
        )
        snaps = []
        for market, analytics in pairs:
            for ta in analytics:
                snaps.append(
                    build_snapshot_input(
                        market, ta, captured_at=at, calculation_version=CALCULATION_VERSION
                    )
                )
        return snaps

    async def update_rankings(
        self, session: AsyncSession, *, at: datetime | None = None,
        provenance_class: str = PROVENANCE_PROSPECTIVE, limit: int | None = None,
    ) -> WeeklyCohortRow:
        at = at or utcnow()
        snaps = await self._snapshots(at, limit)
        return await engine.update_rankings(
            session, snapshots=snaps, at=at, provenance_class=provenance_class
        )

    async def freeze(self, session: AsyncSession, *, at: datetime | None = None):
        return await engine.freeze_week(session, at=at or utcnow())

    async def collect_forward(self, session: AsyncSession, *, now: datetime | None = None) -> int:
        now = now or utcnow()

        async def price_of(market_id: str, token_id: str):
            return await self.market_service.token_price(
                market_id, token_id, requested_mode=self.mode
            )

        return await tracking.collect_forward_prices(session, now=now, price_of=price_of)

    async def check_resolutions(self, session: AsyncSession) -> int:
        async def resolver(market_id: str, condition_id: str | None):
            res = await self.market_service.market_resolution(
                market_id, requested_mode=self.mode
            )
            if res is None:
                return None
            resolved, token_id, name = res
            return tracking.Resolution(
                resolved=resolved,
                resolved_token_id=token_id,
                resolved_outcome=name,
                resolved_at=utcnow(),
                condition_id=condition_id,
                source=f"metadata:{self.mode}",
            )

        return await tracking.record_resolutions(session, resolver=resolver)

    async def evaluate(
        self, session: AsyncSession, *, stake: float = DEFAULT_STAKE,
        fee_rate: float = DEFAULT_FEE_RATE,
    ) -> int:
        return await tracking.evaluate_all(session, stake=stake, fee_rate=fee_rate)
