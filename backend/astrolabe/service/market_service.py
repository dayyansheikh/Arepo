"""MarketService — the application brain.

Resolves the active data mode (live/cached/replay) with graceful fallback, enriches markets
with the shared analytics, and assembles the public API responses. Never presents cached or
replay data as live: the returned ``DataStatus`` always states the true mode and, on fallback,
the degradation reason.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from ..analytics.backtest import run_backtest
from ..config import Settings, get_settings
from ..domain.enums import DataMode
from ..domain.models import DataStatus, Market, PricePoint, Signal
from ..observability.logging import get_logger
from ..replay.player import ReplayPlayer, default_player
from . import enrich
from .enrich import TokenAnalytics
from .schemas import (
    BacktestEvent,
    BacktestResponse,
    MarketCard,
    MarketDetail,
    MarketDetailResponse,
    MarketFacetsResponse,
    MarketListResponse,
    OverviewResponse,
    SignalsResponse,
)
from .sources import CachedSource, DataSource, LiveSource, ReplaySource, TokenData

logger = get_logger("astrolabe.service")

OVERVIEW_ENRICH = 15       # bound how many markets we deep-fetch for the overview (live)
DETAIL_HISTORY_MAX = 400


class MarketService:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        cached_session_factory=None,
        player: ReplayPlayer | None = None,
    ):
        self._settings = settings or get_settings()
        self._player = player or default_player()
        self._replay = ReplaySource(self._player)
        self._live = LiveSource(self._settings)
        self._cached = CachedSource(cached_session_factory)

    # -- mode resolution -------------------------------------------------------------
    def _default_mode(self) -> DataMode:
        try:
            return DataMode(self._settings.default_mode)
        except ValueError:
            return DataMode.LIVE

    async def _select_source(self, requested: str | None) -> tuple[DataSource, str | None]:
        """Return (source, degradation_reason). Falls back live -> cached -> replay."""
        mode = self._default_mode() if not requested else _coerce_mode(requested)

        if mode == DataMode.REPLAY:
            return self._replay, None
        if mode == DataMode.CACHED:
            if self._cached.available():
                return self._cached, None
            return self._replay, "cache unavailable; using replay"

        # LIVE requested: probe by attempting a discovery; fall back on failure.
        try:
            await self._live.markets()
            return self._live, None
        except Exception as exc:  # noqa: BLE001 - fall back rather than fail the request
            logger.warning("live discovery failed; falling back", extra={"ctx_err": str(exc)})
            if self._cached.available():
                cached_markets = await self._cached.markets()
                if cached_markets:
                    return self._cached, f"live unavailable ({type(exc).__name__}); using cache"
            return self._replay, f"live unavailable ({type(exc).__name__}); using replay"

    async def _status(self, source: DataSource, reason: str | None,
                     last_update: datetime | None) -> DataStatus:
        rest, ws = await source.health()
        age = enrich.data_age(last_update) if last_update else None
        return DataStatus(
            mode=source.mode,
            rest=rest,
            websocket=ws,
            last_update=last_update,
            data_age_seconds=age,
            degradation_reason=reason,
        )

    # -- enrichment helpers ----------------------------------------------------------
    async def _enrich_market(
        self, source: DataSource, market: Market
    ) -> tuple[list[TokenAnalytics], MarketCard]:
        async def one(token_id: str) -> tuple[str, TokenData]:
            return token_id, await source.get_token_data(market.id, token_id)

        results = await asyncio.gather(*(one(o.token_id) for o in market.outcomes))
        token_data = dict(results)
        analytics: list[TokenAnalytics] = []
        for o in market.outcomes:
            td = token_data[o.token_id]
            analytics.append(
                enrich.compute_token_analytics(
                    token_id=o.token_id,
                    market_id=market.id,
                    prices=td.prices,
                    book=td.book,
                    volumes=td.volumes,
                    gamma_price=o.price,
                    data_age_seconds=enrich.data_age(td.captured_at),
                )
            )
        return analytics, enrich.market_card(market, analytics)

    def _card_from_metadata(self, market: Market) -> MarketCard:
        """Cheap card from discovery metadata only (no per-token network fetch)."""
        lead = max(
            market.outcomes,
            key=lambda o: (o.price if o.price is not None else -1.0),
            default=None,
        )
        return MarketCard(
            id=market.id, question=market.question, slug=market.slug,
            category=market.category, sport=market.sport, competition=market.competition,
            status=market.status.value, tags=market.tags,
            volume=market.volume, volume_24hr=market.volume_24hr, liquidity=market.liquidity,
            end_date=market.end_date.isoformat() if market.end_date else None,
            top_probability=lead.price if lead else None,
            top_outcome=lead.name if lead else None,
            spread=None, abs_movement=None, signal_strength=None,
        )

    # -- public API ------------------------------------------------------------------
    async def list_markets(
        self, *, requested_mode=None, search=None, category=None, status=None,
        sort="volume", limit=50, offset=0,
    ) -> MarketListResponse:
        source, reason = await self._select_source(requested_mode)
        markets = await source.markets()
        markets = _filter_markets(markets, search=search, category=category, status=status)
        markets = _sort_markets(markets, sort)
        total = len(markets)
        page = markets[offset: offset + limit]
        cards = [self._card_from_metadata(m) for m in page]
        last_update = _latest_update(page)
        status_env = await self._status(source, reason, last_update)
        return MarketListResponse(
            markets=cards, total=total, limit=limit, offset=offset, status=status_env
        )

    async def facets(self, *, requested_mode=None) -> MarketFacetsResponse:
        """Distinct real filter values (category/sport/competition/status) currently present.

        Reuses the same source path as :meth:`list_markets` (no filtering/paging applied)
        so the facets always describe what a user could actually filter down to.
        """
        source, _ = await self._select_source(requested_mode)
        markets = await source.markets()
        categories = sorted({m.category for m in markets if m.category})
        sports = sorted({m.sport for m in markets if m.sport})
        competitions = sorted({m.competition for m in markets if m.competition})
        statuses = sorted({m.status.value for m in markets if m.status is not None})
        return MarketFacetsResponse(
            categories=categories, sports=sports, competitions=competitions, statuses=statuses,
        )

    async def enrich_markets(self, *, requested_mode=None, limit=None):
        """(Market, [TokenAnalytics]) pairs for the current markets, plus the source mode.

        Used by the cohort engine to snapshot the signals Arepo would select right now.
        Sees only information available at this instant (no look-ahead)."""
        source, _ = await self._select_source(requested_mode)
        markets = await source.markets()
        subset = _sort_markets(markets, "volume_24hr")
        if limit is not None:
            subset = subset[:limit]
        results = await asyncio.gather(
            *(self._enrich_market(source, m) for m in subset), return_exceptions=True
        )
        out: list[tuple[Market, list[TokenAnalytics]]] = []
        for m, item in zip(subset, results, strict=False):
            if isinstance(item, BaseException):
                continue
            analytics, _ = item
            out.append((m, analytics))
        return out, source.mode

    async def token_price(self, market_id: str, token_id: str, *, requested_mode=None):
        """Current (price, source_timestamp) for one outcome token, or (None, None).

        Price is the two-sided-book midpoint where available, else the latest observed
        price. Used to collect forward prices after a cohort freezes."""
        source, _ = await self._select_source(requested_mode)
        td = await source.get_token_data(market_id, token_id)
        price = None
        if td.book is not None and td.book.midpoint is not None:
            price = td.book.midpoint
        elif td.prices:
            price = td.prices[-1]
        return price, td.captured_at

    async def market_resolution(self, market_id: str, *, requested_mode=None):
        """Best-effort real resolution from market metadata: (resolved, winning_token_id,
        winning_outcome_name) or None when still unknown. A market counts as resolved only
        when it is closed and exactly one outcome sits at an extreme price (>= 0.99)."""
        source, _ = await self._select_source(requested_mode)
        markets = await source.markets()
        market = next((m for m in markets if m.id == market_id), None)
        if market is None:
            return None
        if market.status.value not in {"closed", "resolved"}:
            return None
        winners = [o for o in market.outcomes if o.price is not None and o.price >= 0.99]
        if len(winners) == 1:
            return True, winners[0].token_id, winners[0].name
        return None

    async def overview(self, *, requested_mode=None) -> OverviewResponse:
        source, reason = await self._select_source(requested_mode)
        markets = await source.markets()
        # Deep-enrich the most actively-trading markets (24h volume): these have recent CLOB
        # history, so the composite's price-behaviour features have real data instead of the
        # score falling back to order-book imbalance on quiet mega-markets. Replay: enrich all.
        by_volume = _sort_markets(markets, "volume")
        active = _sort_markets(markets, "volume_24hr")
        enrich_set = active if source.mode == DataMode.REPLAY else active[:OVERVIEW_ENRICH]

        enriched = await asyncio.gather(
            *(self._enrich_market(source, m) for m in enrich_set), return_exceptions=True
        )
        cards: list[MarketCard] = []
        signals: list[Signal] = []
        for item in enriched:
            if isinstance(item, BaseException):
                continue
            analytics, card = item
            cards.append(card)
            signals.extend(a.signal for a in analytics if a.signal.strength > 0)

        highest_volume = [self._card_from_metadata(m) for m in by_volume[:8]]
        most_active = [
            self._card_from_metadata(m)
            for m in _sort_markets(markets, "volume_24hr")[:8]
        ]
        movers = sorted(
            [c for c in cards if c.abs_movement is not None],
            key=lambda c: c.abs_movement, reverse=True,
        )[:8]
        widest = sorted(
            [c for c in cards if c.spread is not None],
            key=lambda c: c.spread, reverse=True,
        )[:8]
        recent_signals = sorted(signals, key=lambda s: s.strength, reverse=True)[:10]

        last_update = _latest_update(enrich_set)
        status_env = await self._status(source, reason, last_update)
        return OverviewResponse(
            top_movers=movers, most_active=most_active, highest_volume=highest_volume,
            widest_spreads=widest, recent_signals=recent_signals, status=status_env,
        )

    async def market_detail(self, market_id: str, *, requested_mode=None):
        source, reason = await self._select_source(requested_mode)
        markets = await source.markets()
        market = next((m for m in markets if m.id == market_id), None)
        if market is None:
            return None

        analytics, _ = await self._enrich_market(source, market)
        outcomes_view = []
        norm = enrich.normalized_probs_for(analytics)
        history: dict[str, list[PricePoint]] = {}
        for ta, o, np_ in zip(analytics, market.outcomes, norm, strict=False):
            outcomes_view.append(enrich.outcome_view(ta, o.name, np_))
            td = await source.get_token_data(market.id, o.token_id)
            # Use real per-point timestamps where the source has them (replay via the
            # player; live/cached via td.price_points), so the chart plots a genuine
            # time axis instead of collapsing every point onto "now".
            history[o.token_id] = _history_points(source, market.id, o.token_id, td)

        signals = [ta.signal for ta in analytics]
        last_update = _latest_update([market])
        detail = MarketDetail(
            id=market.id, question=market.question, slug=market.slug,
            description=market.description, category=market.category,
            sport=market.sport, competition=market.competition,
            status=market.status.value, tags=market.tags, volume=market.volume,
            volume_24hr=market.volume_24hr, liquidity=market.liquidity,
            tick_size=market.tick_size,
            end_date=market.end_date.isoformat() if market.end_date else None,
            outcomes=outcomes_view, price_history=history, signals=signals,
            limitations=(
                "Implied probabilities are spread/fee-contaminated risk-neutral estimates. "
                "Signals are screening heuristics, not evidence of insider activity or profit."
            ),
            data_source=source.mode.value,
        )
        status_env = await self._status(source, reason, last_update)
        return MarketDetailResponse(market=detail, status=status_env)

    async def signals(self, *, requested_mode=None, limit=25) -> SignalsResponse:
        source, reason = await self._select_source(requested_mode)
        markets = await source.markets()
        active = _sort_markets(markets, "volume_24hr")
        enrich_set = active if source.mode == DataMode.REPLAY else active[:OVERVIEW_ENRICH]
        enriched = await asyncio.gather(
            *(self._enrich_market(source, m) for m in enrich_set), return_exceptions=True
        )
        signals: list[Signal] = []
        for item in enriched:
            if isinstance(item, BaseException):
                continue
            analytics, _ = item
            signals.extend(a.signal for a in analytics)
        signals = sorted(signals, key=lambda s: s.strength, reverse=True)[:limit]
        status_env = await self._status(source, reason, _latest_update(enrich_set))
        return SignalsResponse(signals=signals, status=status_env)

    async def status(self, *, requested_mode=None) -> DataStatus:
        source, reason = await self._select_source(requested_mode)
        return await self._status(source, reason, None)

    def backtest(self, **kwargs) -> BacktestResponse:
        r = run_backtest(self._player, **kwargs)
        events = [
            BacktestEvent(
                market_id=e.market_id, token_id=e.token_id, frame=e.frame, strength=e.strength,
                zscore=e.zscore, direction=e.direction, entry_price=e.entry_price,
                forward_price=e.forward_price, forward_move=e.forward_move,
                followed_through=e.followed_through,
            )
            for e in r.events
        ]
        return BacktestResponse(
            strength_threshold=r.strength_threshold, move_threshold=r.move_threshold,
            horizon=r.horizon, zscore_window=r.zscore_window, min_history=r.min_history,
            sample_size=r.sample_size, evaluated=r.evaluated,
            missing_observations=r.missing_observations, hit_rate=r.hit_rate,
            false_positive_rate=r.false_positive_rate,
            avg_forward_move_directional=r.avg_forward_move_directional,
            avg_abs_forward_move=r.avg_abs_forward_move, events=events,
            assumptions=r.assumptions, limitations=r.limitations, dataset_meta=self._player.meta,
        )

    async def aclose(self) -> None:
        await self._live.aclose()


# ------------------------------------------------------------------------------ helpers
def _coerce_mode(value: str) -> DataMode:
    try:
        return DataMode(value.lower())
    except ValueError:
        return DataMode.LIVE


def _filter_markets(markets, *, search, category, status):
    out = markets
    if search:
        s = search.lower()
        out = [m for m in out if s in m.question.lower()]
    if category:
        c = category.lower()
        out = [m for m in out if (m.category or "").lower() == c]
    if status:
        out = [m for m in out if m.status.value == status.lower()]
    return out


def _sort_markets(markets, sort):
    key = {
        "volume": lambda m: m.volume or 0.0,
        "volume_24hr": lambda m: m.volume_24hr or 0.0,
        "liquidity": lambda m: m.liquidity or 0.0,
        "end_date": lambda m: (m.end_date.timestamp() if m.end_date else float("inf")),
    }.get(sort, lambda m: m.volume or 0.0)
    reverse = sort != "end_date"
    return sorted(markets, key=key, reverse=reverse)


def _latest_update(markets) -> datetime | None:
    dts = [m.updated_at for m in markets if getattr(m, "updated_at", None)]
    return max(dts) if dts else datetime.now(UTC)


def _history_points(source, market_id, token_id, td) -> list[PricePoint]:
    """Price-history points with real timestamps wherever the source has them.

    Replay reads timestamps from the deterministic player. Live and cached carry
    ``td.price_points`` (real per-observation times). Only as a last resort, when a
    source gives values without any timestamps, do we synthesise an evenly-spaced
    minute axis so the series still has distinct times and does not collapse onto a
    single point (which rendered as an apparently blank chart).
    """
    if isinstance(source, ReplaySource):
        return source._player.price_history(market_id, token_id)
    if td.price_points:
        return td.price_points[-DETAIL_HISTORY_MAX:]
    prices = td.prices[-DETAIL_HISTORY_MAX:]
    if not prices:
        return []
    base = datetime.now(UTC) - timedelta(minutes=len(prices) - 1)
    return [PricePoint(t=base + timedelta(minutes=i), p=p) for i, p in enumerate(prices)]
