"""Freeze a research cohort: every screened market/token, with role and full cut-off snapshot.

Two layers, so the classification logic is unit-testable without a network:
- ``screen_universe`` (async, live): enrich the active universe and score every market exactly as
  the Opportunity Board does, returning one ``ScoredScreen`` per market (its strongest outcome).
- ``build_entry_inputs`` (pure): assign role, signal classification and walk-forward partition and
  produce ``EntryInput`` rows for the FULL universe (not only the public top-N).
- ``freeze_from_inputs`` (persistence): idempotent get-or-create cohort, add all entries, freeze.

The public product still shows only the top selections; research freezes them all (prompt §2, §4).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from ..domain.enums import DataMode
from ..domain.models import Trade, utcnow
from ..ingest.normalize import normalize_trades
from ..opportunity.hypothesis import STRENGTH_MODERATE, has_directional_view
from ..opportunity.scoring import score_opportunity
from ..opportunity.service import market_flow_indicators
from .errors import CohortFrozenError
from .research_constants import (
    CADENCE_6H,
    CADENCE_DAILY,
    CADENCE_WEEKLY,
    DEGRADED_EXCLUSION_RATE,
    MAX_EXCLUSION_RATE,
    MIN_USABLE_UNIVERSE,
    MODEL_VERSION,
    PARTITION_LIVE,
    PUBLIC_SELECTION_SIZE,
    RESEARCH_HORIZONS,
    ROLE_ABSTENTION,
    ROLE_OBSERVATION,
    ROLE_PUBLIC,
    ROLE_SHADOW,
)
from .research_repository import EntryInput, ResearchRepository

MICRO_COMPONENTS = ("spread_change", "depth_change", "volume_acceleration")


def cadence_cutoff(cadence: str, now: datetime) -> datetime:
    """Snap ``now`` DOWN to the cadence boundary so repeated runs in one period are idempotent."""
    now = now.astimezone(UTC)
    if cadence == CADENCE_6H:
        hour = (now.hour // 6) * 6
        return now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if cadence == CADENCE_DAILY:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if cadence == CADENCE_WEEKLY:
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight - timedelta(days=now.weekday())  # Monday 00:00 UTC of this ISO week
    raise ValueError(f"unknown cadence {cadence!r}")


def classify_signal(
    *, direction: str | None, n_families: int, strength: float, data_quality: str
) -> str:
    """One of the five selective classes (validation spec §3)."""
    if data_quality == "poor":
        return "Data-quality warning"
    if has_directional_view(direction, n_families, strength):
        return "Directional opportunity"
    if direction in ("up", "down"):
        return "Directional observation"       # a lean, but not enough evidence to act on
    if strength >= STRENGTH_MODERATE:
        return "Non-directional anomaly"
    return "Insufficient evidence"


@dataclass
class ScoredScreen:
    """One market's strongest-outcome result at the cut-off (from screen_universe or a fixture)."""

    market_id: str
    condition_id: str | None
    event_id: str | None
    token_id: str
    market_question: str
    outcome_name: str
    direction: str | None
    momentum_direction: str | None  # sign of the z-score (Arepo's price signal)
    orderbook_direction: str | None  # sign of near-touch book imbalance
    tradeflow_direction: str | None  # sign of net aggressive flow
    strength: float
    confidence: float               # reliability confidence
    research_priority: int          # 0-100
    n_families: int
    evidence_families: list
    component_scores: list
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


def _component_availability(component_scores: list) -> dict:
    present = {c["name"] for c in component_scores if c.get("raw_value") is not None}
    return {name: (name in present) for name in MICRO_COMPONENTS}


@dataclass
class UniverseFunnel:
    """The market-discovery funnel for one freeze (prompt section 5): how many markets were
    discovered, how many yielded usable point-in-time data, and which were excluded and why."""

    discovered: int = 0
    usable: int = 0
    exclusions: list = field(default_factory=list)  # [{"market_id", "reason"}]

    @property
    def excluded(self) -> int:
        return len(self.exclusions)

    @property
    def exclusion_rate(self) -> float:
        return (self.excluded / self.discovered) if self.discovered else 0.0


@dataclass
class UniverseDecision:
    freeze: bool
    degraded: bool
    reason: str


def assess_universe(funnel: UniverseFunnel) -> UniverseDecision:
    """Decide whether a freeze may proceed given the funnel (prompt section 5). Reject (no cohort)
    on complete/near-complete upstream failure; otherwise allow, flagging a degraded run when a
    notable share was excluded. Pure and testable."""
    if funnel.usable < MIN_USABLE_UNIVERSE:
        return UniverseDecision(
            False, True,
            f"rejected: only {funnel.usable} usable markets (< {MIN_USABLE_UNIVERSE}); "
            "no cohort created to avoid a misleading record",
        )
    if funnel.exclusion_rate > MAX_EXCLUSION_RATE:
        return UniverseDecision(
            False, True,
            f"rejected: {funnel.excluded}/{funnel.discovered} markets excluded "
            f"({funnel.exclusion_rate:.0%} > {MAX_EXCLUSION_RATE:.0%}); no cohort created",
        )
    degraded = funnel.exclusion_rate > DEGRADED_EXCLUSION_RATE
    return UniverseDecision(
        True, degraded,
        (f"degraded: {funnel.excluded}/{funnel.discovered} markets excluded"
         if degraded else "ok"),
    )


def _sign(x: float | None) -> str | None:
    if x is None or x == 0:
        return None
    return "up" if x > 0 else "down"


def _flow_direction(indicators) -> str | None:
    """Net aggressive trade-flow direction from the fired flow indicators (up | down | None).

    Uses ``consensus_opposing_flow``'s signed direction when present (it knows which outcome the
    aggressive money favoured); otherwise abstains. Frozen at the cut-off so trade-flow-only is a
    genuine prospective baseline.
    """
    for ind in indicators:
        meta = getattr(ind, "meta", None) or {}
        d = meta.get("flow_direction") or meta.get("direction")
        if d in ("up", "down"):
            return d
    return None


def build_entry_inputs(screens: list[ScoredScreen], *, now: datetime) -> list[EntryInput]:
    """Assign role + classification + partition to the FULL universe (pure, deterministic).

    Directional entries are ranked by Research Priority; the top ``PUBLIC_SELECTION_SIZE`` are
    labelled public_selection, the rest shadow_directional. Non-directional anomalies are
    observations; everything else is an abstention control. Every screened market is kept.
    """
    directional = [
        s for s in screens
        if has_directional_view(s.direction, s.n_families, s.strength) and s.data_quality != "poor"
    ]
    directional.sort(key=lambda s: s.research_priority, reverse=True)
    public_ids = {id(s) for s in directional[:PUBLIC_SELECTION_SIZE]}
    rank_by_id = {id(s): i + 1 for i, s in enumerate(directional)}

    inputs: list[EntryInput] = []
    for s in screens:
        classification = classify_signal(
            direction=s.direction, n_families=s.n_families,
            strength=s.strength, data_quality=s.data_quality,
        )
        is_dir = (
            has_directional_view(s.direction, s.n_families, s.strength)
            and s.data_quality != "poor"
        )
        if is_dir:
            role = ROLE_PUBLIC if id(s) in public_ids else ROLE_SHADOW
            rank = rank_by_id.get(id(s))
        elif classification == "Non-directional anomaly":
            role, rank = ROLE_OBSERVATION, None
        else:
            role, rank = ROLE_ABSTENTION, None
        time_remaining_h = (
            (s.expected_close - now).total_seconds() / 3600.0
            if s.expected_close is not None and s.expected_close > now else None
        )
        inputs.append(
            EntryInput(
                role=role,
                rank=rank,
                walk_forward_partition=PARTITION_LIVE,  # frozen live => genuine prospective
                market_id=s.market_id,
                condition_id=s.condition_id,
                event_id=s.event_id,
                token_id=s.token_id,
                market_question=s.market_question,
                outcome_name=s.outcome_name,
                direction=s.direction if is_dir else None,
                momentum_direction=s.momentum_direction,
                orderbook_direction=s.orderbook_direction,
                tradeflow_direction=s.tradeflow_direction,
                signal_classification=classification,
                strength=s.strength,
                confidence=s.confidence,
                research_priority=s.research_priority,
                n_families=s.n_families,
                evidence_families=list(s.evidence_families),
                component_scores=list(s.component_scores),
                component_availability=_component_availability(s.component_scores),
                data_quality=s.data_quality,
                entry_price=s.entry_price,
                best_bid=s.best_bid,
                best_ask=s.best_ask,
                midpoint=s.midpoint,
                spread=s.spread,
                near_mid_depth=s.near_mid_depth,
                liquidity=s.liquidity,
                volume=s.volume,
                data_age_seconds=s.data_age_seconds,
                expected_close=s.expected_close,
                time_remaining_hours=round(time_remaining_h, 2) if time_remaining_h else None,
                intended_horizons=list(RESEARCH_HORIZONS.keys()),
            )
        )
    return inputs


async def freeze_from_inputs(
    session,
    *,
    cadence: str,
    cutoff_at: datetime,
    inputs: list[EntryInput],
    model_version: str = MODEL_VERSION,
    calculation_version: str,
    provenance_class: str = "prospective",
    frozen_at: datetime | None = None,
    funnel: UniverseFunnel | None = None,
) -> dict:
    """Idempotently create the (cadence, cutoff) cohort, add all entries, and freeze it.

    Idempotent: a second call for the same (cadence, cutoff) finds the frozen cohort and adds
    nothing. If ``funnel`` shows the universe failed the degradation guard (too few usable markets
    or too many exclusions) the freeze is REJECTED and no cohort is created (prompt section 5).
    Returns a summary dict for logging/status.
    """
    decision = (
        assess_universe(funnel) if funnel is not None else UniverseDecision(True, False, "ok")
    )
    if not decision.freeze:
        return {
            "cadence": cadence, "cutoff_at": cutoff_at.isoformat(), "created": False,
            "frozen": False, "rejected": True, "reason": decision.reason,
            "discovered": funnel.discovered if funnel else 0,
            "usable": funnel.usable if funnel else 0,
            "excluded": funnel.excluded if funnel else 0,
        }
    repo = ResearchRepository(session)
    try:
        cohort, created = await repo.get_or_create_cohort(
            cadence=cadence,
            cutoff_at=cutoff_at,
            model_version=model_version,
            calculation_version=calculation_version,
        )
    except IntegrityError:
        # A concurrent freeze for the same (cadence, cutoff) won the unique-constraint race. Degrade
        # to the normal already-frozen no-op instead of crashing the loser (DB review MODERATE-6):
        # roll back our failed insert and read the winner's now-committed row.
        await session.rollback()
        existing = await repo.get_cohort(cadence, cutoff_at)
        if existing is None:  # extremely unlikely; surface honestly rather than loop
            raise
        cohort, created = existing, False
    # Provenance is part of the immutable identity: set it only on creation, and never mutate it on
    # a frozen cohort (adversarial review finding 4 - closes an immutability hole).
    if created:
        cohort.provenance_class = provenance_class
    elif cohort.provenance_class != provenance_class:
        if cohort.frozen:
            raise CohortFrozenError(
                f"research cohort {cadence}@{cutoff_at} is frozen with provenance "
                f"{cohort.provenance_class!r}; cannot change it to {provenance_class!r}"
            )
        cohort.provenance_class = provenance_class
    if cohort.frozen:
        return {
            "cadence": cadence, "cutoff_at": cutoff_at.isoformat(), "created": False,
            "frozen": True, "already_frozen": True, "universe_size": cohort.universe_size,
        }
    # Atomic freeze (prompt section 4): ONE transaction boundary. The cohort row and every universe
    # entry are only made durable by the single commit AFTER freeze_cohort. Any failure before that
    # rolls the whole unit back, so a partial or non-frozen cohort is never visible. On error we
    # roll back explicitly (belt-and-suspenders) and re-raise so the caller sees the real cause.
    try:
        for e in inputs:
            await repo.add_entry(cohort, e)
        await repo.freeze_cohort(
            cohort, frozen_at=frozen_at,
            excluded_markets=(funnel.excluded if funnel else 0),
            degraded=decision.degraded,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return {
        "cadence": cadence, "cutoff_at": cutoff_at.isoformat(), "created": created,
        "frozen": True, "already_frozen": False,
        "universe_size": cohort.universe_size,
        "directional": cohort.directional_count,
        "public": cohort.public_selection_count,
        "shadow": cohort.shadow_count,
        "observation": cohort.observation_count,
        "abstention": cohort.abstention_count,
        "excluded": cohort.excluded_markets,
        "degraded": cohort.degraded,
    }


async def screen_universe(
    market_service, data_api, *, now: datetime | None = None, universe_limit: int = 60
) -> tuple[list[ScoredScreen], str, UniverseFunnel]:
    """Enrich + score the live active universe (one strongest outcome per market).

    Returns the usable screens, the data mode, and a :class:`UniverseFunnel` recording every market
    that was discovered but EXCLUDED for lack of usable point-in-time data, with a reason (prompt
    section 5). A market with no usable token analytics (its upstream book/history was unavailable,
    already retried at the HTTP layer) is excluded honestly rather than frozen with empty values.
    """
    now = now or utcnow()
    pairs, mode = await market_service.enrich_markets(requested_mode="live", limit=universe_limit)
    live = mode == DataMode.LIVE

    async def one(market, analytics) -> ScoredScreen | None:
        if not analytics:
            return None
        ta = max(analytics, key=lambda a: a.signal.strength)
        trades: list[Trade] = []
        if live and market.condition_id:
            try:
                raw = await data_api.get_market_trades(market.condition_id, limit=1000)
                trades = normalize_trades(raw)
            except Exception:  # noqa: BLE001 - trades are best-effort
                trades = []
        indicators = market_flow_indicators(
            trades, market_price=ta.implied, price_change=ta.movement,
            end_date=market.end_date, start_date=market.start_date, now=now,
        )
        scored = score_opportunity(
            ta.signal, indicators, liquidity=market.liquidity,
            relative_spread=ta.relative_spread, data_age_seconds=ta.data_age_seconds, now=now,
        )
        momentum_dir = _sign(ta.zscore)               # Arepo's price signal = z-score sign
        orderbook_dir = _sign(ta.imbalance)           # bid-heavy (>0) => upward pressure
        tradeflow_dir = _flow_direction(indicators)   # net aggressive flow sign
        return ScoredScreen(
            market_id=market.id,
            condition_id=market.condition_id or None,
            event_id=getattr(market, "event_id", None),
            token_id=ta.token_id,
            market_question=market.question,
            outcome_name=ta.signal.outcome_name or ta.token_id,
            direction=ta.signal.direction,
            momentum_direction=momentum_dir,
            orderbook_direction=orderbook_dir,
            tradeflow_direction=tradeflow_dir,
            strength=scored.signal_strength,
            confidence=scored.confidence,
            research_priority=int(round(scored.research_priority * 100)),
            n_families=scored.n_families,
            evidence_families=list(scored.families),
            component_scores=[
                {"name": c.name, "raw_value": c.raw_value,
                 "normalized_value": c.normalized_value, "weight": c.weight}
                for c in ta.signal.components
            ],
            data_quality=scored.data_quality,
            entry_price=ta.midpoint if ta.midpoint is not None else ta.implied,
            best_bid=ta.best_bid,
            best_ask=ta.best_ask,
            midpoint=ta.midpoint,
            spread=ta.spread,
            near_mid_depth=ta.near_mid_depth,
            liquidity=market.liquidity,
            volume=ta.volume,
            data_age_seconds=ta.data_age_seconds,
            expected_close=market.end_date,
        )

    results = await asyncio.gather(*(one(m, a) for m, a in pairs), return_exceptions=True)
    funnel = UniverseFunnel(discovered=len(pairs))
    screens: list[ScoredScreen] = []
    for (market, _analytics), r in zip(pairs, results, strict=False):
        if isinstance(r, ScoredScreen):
            screens.append(r)
        elif isinstance(r, BaseException):
            funnel.exclusions.append({"market_id": market.id, "reason": f"error: {r}"})
        else:  # None: no usable token data
            funnel.exclusions.append(
                {"market_id": market.id, "reason": "no usable point-in-time token data"}
            )
    funnel.usable = len(screens)
    return screens, mode.value, funnel
