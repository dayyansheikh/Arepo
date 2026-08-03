"""Forward-price collection, resolution recording and evaluation over frozen cohorts.

All data providers are injected (a price lookup, a resolver) so this orchestration is
unit-testable without the network, and so live/cached/replay all reuse it. Everything
here is idempotent: forward observations are unique per (entry, horizon), resolutions
are upserted per market, and evaluation results are upserted per entry. Nothing here
ever modifies a frozen cohort's entries (only derived observation/result rows).
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from .constants import DEFAULT_FEE_RATE, DEFAULT_STAKE, FORWARD_HORIZONS, HORIZON_24H
from .portfolio import value_position
from .repository import EvaluationRepository, _utc

# price_of(market_id, token_id) -> (price_in_[0,1] | None, source_timestamp | None)
PriceLookup = Callable[[str, str], Awaitable[tuple[float | None, datetime | None]]]


@dataclass
class Resolution:
    resolved: bool
    resolved_token_id: str | None = None
    resolved_outcome: str | None = None
    resolved_at: datetime | None = None
    condition_id: str | None = None
    source: str | None = None


# resolver(market_id, condition_id) -> Resolution | None  (None: still unknown)
Resolver = Callable[[str, str | None], Awaitable[Resolution | None]]

# Preference order for marking an open position / the movement view.
_MARK_ORDER = ["7d", HORIZON_24H, "1h"]


def due_horizons(frozen_at: datetime, now: datetime) -> list[str]:
    """Timed horizons (1h/24h/7d) whose window has elapsed since freeze."""
    frozen_at = _utc(frozen_at)
    now = _utc(now)
    return [
        label
        for label, secs in FORWARD_HORIZONS.items()
        if now >= frozen_at + timedelta(seconds=secs)
    ]


async def collect_forward_prices(
    session: AsyncSession, *, now: datetime, price_of: PriceLookup
) -> int:
    """Record any due-and-missing forward prices for frozen cohorts. Returns count added."""
    repo = EvaluationRepository(session)
    added = 0
    for cohort in await repo.list_cohorts():
        if not cohort.frozen or cohort.frozen_at is None:
            continue
        due = due_horizons(cohort.frozen_at, now)
        if not due:
            continue
        for entry in await repo.get_entries(cohort.id):
            have = {o.horizon for o in await repo.get_forward(entry.id)}
            for horizon in due:
                if horizon in have:
                    continue
                price, src_ts = await price_of(entry.market_id, entry.token_id)
                if price is None:
                    # A transient lookup failure must not permanently lose the horizon:
                    # leave it unrecorded so the next scheduled run can capture the price.
                    continue
                _, created = await repo.add_forward(
                    entry.id, horizon, observed_at=now, price=price, source_timestamp=src_ts
                )
                if created:
                    added += 1
    await session.commit()
    return added


async def record_resolutions(session: AsyncSession, *, resolver: Resolver) -> int:
    """Check unresolved markets in frozen cohorts and upsert any resolutions found."""
    repo = EvaluationRepository(session)
    updated = 0
    seen: set[str] = set()
    for cohort in await repo.list_cohorts():
        if not cohort.frozen:
            continue
        for entry in await repo.get_entries(cohort.id):
            if entry.market_id in seen:
                continue
            seen.add(entry.market_id)
            existing = await repo.get_resolution(entry.market_id)
            if existing is not None and existing.resolved:
                continue  # never overwrite a settled resolution
            res = await resolver(entry.market_id, entry.condition_id)
            if res is None:
                continue
            await repo.upsert_resolution(
                entry.market_id,
                condition_id=res.condition_id or entry.condition_id,
                resolved=res.resolved,
                resolved_outcome=res.resolved_outcome,
                resolved_token_id=res.resolved_token_id,
                resolved_at=res.resolved_at,
                source=res.source,
            )
            if res.resolved:
                updated += 1
    await session.commit()
    return updated


def _mark_price(forward_by_horizon: dict[str, float | None]) -> tuple[str | None, float | None]:
    for h in _MARK_ORDER:
        if forward_by_horizon.get(h) is not None:
            return h, forward_by_horizon[h]
    return None, None


def _movement_correct(direction: str | None, movement: float | None) -> bool | None:
    if direction is None or movement is None:
        return None
    if direction == "up":
        return movement > 0
    if direction == "down":
        return movement < 0
    return None


async def evaluate_all(
    session: AsyncSession,
    *,
    stake: float = DEFAULT_STAKE,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> int:
    """(Re)compute evaluation results for every frozen-cohort entry. Idempotent."""
    repo = EvaluationRepository(session)
    count = 0
    for cohort in await repo.list_cohorts():
        if not cohort.frozen:
            continue
        for entry in await repo.get_entries(cohort.id):
            forward = {o.horizon: o.price for o in await repo.get_forward(entry.id)}
            _, mark_price = _mark_price(forward)

            # Price-movement view is fixed to the 24h horizon so it matches the horizon
            # the summary states; before a 24h price exists the entry is movement-pending.
            # (Portfolio marking below still uses the best available price via mark_price.)
            move_price = forward.get(HORIZON_24H)
            move_h = HORIZON_24H if move_price is not None else None
            raw_movement = (
                None
                if move_price is None or entry.entry_price is None
                else move_price - entry.entry_price
            )
            movement_correct = _movement_correct(entry.direction, raw_movement)

            # Final-resolution view.
            resolution = await repo.get_resolution(entry.market_id)
            resolved = bool(resolution and resolution.resolved)
            resolution_correct: bool | None = None
            if resolved:
                resolution_correct = resolution.resolved_token_id == entry.token_id

            pos = value_position(
                entry_id=entry.id,
                entry_price=entry.entry_price,
                spread=entry.spread,
                won=resolution_correct if resolved else None,
                forward_price=mark_price,
                stake=stake,
                fee_rate=fee_rate,
            )
            await repo.upsert_evaluation(
                entry.id,
                movement_horizon=move_h,
                raw_prob_movement=raw_movement,
                movement_correct=movement_correct,
                resolved=resolved,
                resolution_correct=resolution_correct,
                pending=not resolved,
                hypothetical_value=pos.value,
            )
            count += 1
    await session.commit()
    return count
