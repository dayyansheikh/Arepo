"""Forward-observation and resolution collection for research cohorts (prompt section 5).

Causal by construction: a horizon observation is only recorded once that horizon has elapsed
measured from the cohort's ACTUAL prediction time (``now >= evaluation_origin_at + horizon``, where
evaluation_origin_at == frozen_at), NEVER from the ``cutoff_at`` cadence LABEL. So a cohort frozen
late gets 1h/6h/24h/7d outcomes from when it was really made, and is never presented as a prediction
made at its scheduled boundary. In production a cron runs this every ~20 minutes and fills any due
observation with the then-current quote; nothing reaches back in time. For tests and the
production-equivalent dry run a controlled ``now`` and a fixture ``price_of`` provider stand in for
the wall clock and the live feed, the only sanctioned use of a test clock (prompt section 17B).

Idempotent: an observation is written once per (entry, horizon) and never overwritten, so re-runs
and retries are safe.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from ..domain.models import utcnow
from .models import MarketResolutionRow
from .research_constants import NEAREST_TOLERANCE_SECONDS, RESEARCH_HORIZONS
from .research_models import ResearchCohortRow, ResearchEntryRow
from .research_repository import ResearchRepository


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@dataclass(frozen=True)
class Quote:
    midpoint: float | None
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    near_mid_depth: float | None
    source_timestamp: datetime | None = None


# price_of(market_id, token_id) -> Quote | None (None when unavailable at this moment).
PriceProvider = Callable[[str, str], Awaitable[Quote | None]]


async def collect_due_forward(
    session, *, now: datetime | None = None, price_of: PriceProvider
) -> dict:
    """Record any forward observation whose horizon has elapsed for frozen prospective cohorts.

    Returns a summary of how many observations were written, unavailable or already present.
    """
    now = (now or utcnow()).astimezone(UTC)
    repo = ResearchRepository(session)
    written = unavailable = already = 0
    closed_before = 0

    invalid = 0
    cohorts = await repo.list_cohorts(provenance="prospective", frozen=True)
    for cohort in cohorts:
        # CAUSAL ORIGIN = when the prediction was actually made (evaluation_origin_at == frozen_at),
        # NEVER the cutoff_at cadence LABEL. Every horizon runs from here, so a cohort frozen late
        # (e.g. a missed weekly run frozen on Thursday) gets 1h/6h/24h/7d outcomes measured from
        # Thursday - it is never presented as if the prediction were made on the scheduled Monday.
        origin = (_utc(cohort.evaluation_origin_at) or _utc(cohort.frozen_at)
                  or _utc(cohort.cutoff_at))
        entries = await repo.get_entries(cohort.id)
        existing_by_entry = {e.id: await repo.get_forward(e.id) for e in entries}
        for entry in entries:
            have = existing_by_entry[entry.id]
            for horizon, secs in RESEARCH_HORIZONS.items():
                target = origin + _timedelta(secs)   # horizon from the actual prediction time
                if horizon in have:
                    already += 1
                    continue
                if now < target:
                    continue  # horizon not yet elapsed (causal: never observe early)
                # Closed-market handling (final-completion prompt C5/§11): if the market has already
                # closed, a live quote now is post-close and useless, and no stored price at the
                # target exists, so record a terminal state (evaluate via freeze-to-close) rather
                # than a wasteful fetch that would only 404. This also bounds a late one-shot local
                # collection to the markets that are genuinely still open.
                close = _utc(entry.expected_close)
                if close is not None and close <= now:
                    reason = (
                        f"market closed before the {horizon} horizon; see freeze-to-close"
                        if close <= target
                        else f"market closed after the {horizon} horizon before it could be "
                             "collected; see freeze-to-close"
                    )
                    await repo.upsert_forward(
                        entry_id=entry.id, horizon=horizon, observed_at=now,
                        midpoint=None, best_bid=None, best_ask=None, spread=None,
                        near_mid_depth=None, source_timestamp=None,
                        exact=abs((now - target).total_seconds()) <= NEAREST_TOLERANCE_SECONDS,
                        observation_delay_seconds=(now - target).total_seconds(),
                        unavailable_reason=reason,
                    )
                    closed_before += 1
                    continue
                quote = await _safe_quote(price_of, entry.market_id, entry.token_id)
                delay = (now - target).total_seconds()
                exact = abs(delay) <= NEAREST_TOLERANCE_SECONDS
                if quote is None:
                    await repo.upsert_forward(
                        entry_id=entry.id, horizon=horizon, observed_at=now,
                        midpoint=None, best_bid=None, best_ask=None, spread=None,
                        near_mid_depth=None, source_timestamp=None, exact=exact,
                        observation_delay_seconds=delay,
                        unavailable_reason="no quote available at observation time",
                    )
                    unavailable += 1
                    continue
                await repo.upsert_forward(
                    entry_id=entry.id, horizon=horizon, observed_at=now,
                    midpoint=quote.midpoint, best_bid=quote.best_bid, best_ask=quote.best_ask,
                    spread=quote.spread, near_mid_depth=quote.near_mid_depth,
                    source_timestamp=quote.source_timestamp, exact=exact,
                    observation_delay_seconds=delay, unavailable_reason=None,
                )
                written += 1
    await session.commit()
    return {
        "written": written, "unavailable": unavailable, "closed_before_horizon": closed_before,
        "invalid_predates_freeze": invalid, "already_present": already,
    }


@dataclass(frozen=True)
class ResolutionInput:
    market_id: str
    condition_id: str | None
    resolved: bool
    resolved_outcome: str | None
    resolved_token_id: str | None
    resolved_at: datetime | None
    source: str | None


async def record_resolution(session, r: ResolutionInput) -> bool:
    """Upsert a market's final resolution (one row per market_id). Never duplicated (prompt §5)."""
    existing = await session.get(MarketResolutionRow, r.market_id)
    now = utcnow()
    if existing is None:
        session.add(
            MarketResolutionRow(
                market_id=r.market_id, condition_id=r.condition_id, resolved=r.resolved,
                resolved_outcome=r.resolved_outcome, resolved_token_id=r.resolved_token_id,
                resolved_at=r.resolved_at, source=r.source, updated_at=now,
            )
        )
        await session.commit()
        return True
    # Only fill in a resolution; never flip an already-resolved market silently.
    if not existing.resolved and r.resolved:
        existing.resolved = True
        existing.resolved_outcome = r.resolved_outcome
        existing.resolved_token_id = r.resolved_token_id
        existing.resolved_at = r.resolved_at
        existing.source = r.source
        existing.updated_at = now
        await session.commit()
        return True
    await session.commit()
    return False


async def _safe_quote(price_of: PriceProvider, market_id: str, token_id: str) -> Quote | None:
    try:
        return await price_of(market_id, token_id)
    except Exception:  # noqa: BLE001 - a feed failure must not abort the whole collection run
        return None


def _timedelta(seconds: int):
    from datetime import timedelta

    return timedelta(seconds=seconds)


async def pending_forward_backlog(session) -> dict:
    """How many (entry, horizon) observations are due but not yet recorded (monitoring)."""
    now = utcnow().astimezone(UTC)
    repo = ResearchRepository(session)
    due = recorded = 0
    for cohort in await repo.list_cohorts(provenance="prospective", frozen=True):
        origin = (_utc(cohort.evaluation_origin_at) or _utc(cohort.frozen_at)
                  or _utc(cohort.cutoff_at))
        for entry in await repo.get_entries(cohort.id):
            have = await repo.get_forward(entry.id)
            for horizon, secs in RESEARCH_HORIZONS.items():
                if now >= origin + _timedelta(secs):  # due from the causal origin, not the label
                    due += 1
                    if horizon in have:
                        recorded += 1
    return {"due": due, "recorded": recorded, "backlog": due - recorded}


async def frozen_prospective_entries(session) -> list[tuple[ResearchCohortRow, ResearchEntryRow]]:
    repo = ResearchRepository(session)
    out: list[tuple[ResearchCohortRow, ResearchEntryRow]] = []
    for cohort in await repo.list_cohorts(provenance="prospective", frozen=True):
        for entry in await repo.get_entries(cohort.id):
            out.append((cohort, entry))
    return out


async def _all_resolutions(session) -> dict[str, MarketResolutionRow]:
    res = await session.execute(select(MarketResolutionRow))
    return {r.market_id: r for r in res.scalars().all()}
