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
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..domain.enums import DataMode
from ..domain.models import Trade, utcnow
from ..ingest.normalize import normalize_trades
from ..opportunity.hypothesis import STRENGTH_MODERATE, has_directional_view
from ..opportunity.scoring import score_opportunity
from ..opportunity.service import market_flow_indicators
from .research_constants import (
    CADENCE_6H,
    CADENCE_DAILY,
    CADENCE_WEEKLY,
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
) -> dict:
    """Idempotently create the (cadence, cutoff) cohort, add all entries, and freeze it.

    Idempotent: a second call for the same (cadence, cutoff) finds the frozen cohort and adds
    nothing. Returns a summary dict for logging/status.
    """
    repo = ResearchRepository(session)
    cohort, created = await repo.get_or_create_cohort(
        cadence=cadence,
        cutoff_at=cutoff_at,
        model_version=model_version,
        calculation_version=calculation_version,
    )
    if cohort.provenance_class != provenance_class:
        cohort.provenance_class = provenance_class
    if cohort.frozen:
        return {
            "cadence": cadence, "cutoff_at": cutoff_at.isoformat(), "created": False,
            "frozen": True, "already_frozen": True, "universe_size": cohort.universe_size,
        }
    for e in inputs:
        await repo.add_entry(cohort, e)
    await repo.freeze_cohort(cohort)
    await session.commit()
    return {
        "cadence": cadence, "cutoff_at": cutoff_at.isoformat(), "created": created,
        "frozen": True, "already_frozen": False,
        "universe_size": cohort.universe_size,
        "directional": cohort.directional_count,
        "public": cohort.public_selection_count,
        "shadow": cohort.shadow_count,
        "observation": cohort.observation_count,
        "abstention": cohort.abstention_count,
    }


async def screen_universe(
    market_service, data_api, *, now: datetime | None = None, universe_limit: int = 60
) -> tuple[list[ScoredScreen], str]:
    """Enrich + score the live active universe (one strongest outcome per market)."""
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
    screens = [r for r in results if isinstance(r, ScoredScreen)]
    return screens, mode.value
