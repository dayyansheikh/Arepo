"""Pluggable data sources behind the market service.

Three sources, one interface, so the analytics/enrichment code is identical regardless of
provenance:
- ``ReplaySource``  — deterministic committed dataset (always available, offline).
- ``LiveSource``    — real Gamma + CLOB public REST (network).
- ``CachedSource``  — most-recent stored data via the storage Repository (best-effort).

Each ``get_token_data`` returns (prices, book, volumes) for one outcome token so the service
can enrich it uniformly.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from ..clients.clob_rest import ClobRestClient
from ..clients.errors import AstrolabeClientError, NotFound
from ..clients.gamma import GammaClient
from ..config import Settings, get_settings
from ..domain.enums import ConnState, DataMode
from ..domain.models import Market, OrderBook, PricePoint, SourceHealth
from ..ingest.normalize import (
    normalize_book,
    normalize_events_to_markets,
    normalize_price_history,
)
from ..observability.logging import get_logger
from ..replay.player import ReplayPlayer, default_player

logger = get_logger("astrolabe.service.sources")

# Cap on live price-history points kept per token (most recent first). At 30-minute
# resolution this is roughly the last month, enough for the analytics windows without
# shipping thousands of points per token.
LIVE_HISTORY_MAX = 1500

# Chart timeline ranges. Short ranges use a fine resolution; longer ones a coarser one.
# "7d" has no named CLOB interval so it uses a start/end window. Seconds are the window
# length, used to filter replay/cached series to the same span.
RANGE_WINDOW_SECONDS: dict[str, int] = {
    "1h": 3600,
    "6h": 21_600,
    "24h": 86_400,
    "7d": 604_800,
}
_RANGE_FETCH: dict[str, dict] = {
    "1h": {"interval": "1h", "fidelity": 1},
    "6h": {"interval": "6h", "fidelity": 1},
    "24h": {"interval": "1d", "fidelity": 1},
    "7d": {"window_seconds": 604_800, "fidelity": 30},
    "all": {"interval": "max", "fidelity": 30},
}


@dataclass
class TokenData:
    prices: list[float]
    book: OrderBook | None
    volumes: list[float]
    captured_at: datetime | None
    # Timestamped history where the source has real per-point times (live/cached).
    # Kept alongside ``prices`` (values only) so analytics stay unchanged while the
    # chart can plot against a genuine time axis instead of collapsing to one point.
    price_points: list[PricePoint] | None = None


class DataSource(Protocol):
    mode: DataMode

    async def markets(self) -> list[Market]: ...
    async def get_token_data(self, market_id: str, token_id: str) -> TokenData: ...
    async def health(self) -> tuple[SourceHealth, SourceHealth]: ...


# --------------------------------------------------------------------------------------
# Replay
# --------------------------------------------------------------------------------------
class ReplaySource:
    mode = DataMode.REPLAY

    def __init__(self, player: ReplayPlayer | None = None):
        self._player = player or default_player()

    async def markets(self) -> list[Market]:
        return self._player.markets()

    async def get_token_data(self, market_id: str, token_id: str) -> TokenData:
        last = self._player.n_frames(market_id) - 1
        prices = self._player.prices(market_id, token_id)
        book = self._player.book_at(market_id, token_id, last)
        volumes = self._player.volumes(market_id, token_id)
        # captured_at=None: a deterministic recorded dataset has no wall-clock "age", so it is
        # not penalised as stale. It is always clearly labelled REPLAY, never presented as live.
        return TokenData(prices=prices, book=book, volumes=volumes, captured_at=None)

    async def health(self) -> tuple[SourceHealth, SourceHealth]:
        # Deterministic dataset: "connected" in the sense that it is fully available.
        h = SourceHealth(name="replay", state=ConnState.CONNECTED, last_success=_now())
        return h, SourceHealth(name="replay-ws", state=ConnState.CONNECTED, last_success=_now())


# --------------------------------------------------------------------------------------
# Live (real Polymarket public REST)
# --------------------------------------------------------------------------------------
class LiveSource:
    mode = DataMode.LIVE

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._gamma = GammaClient(settings=self._settings)
        self._clob = ClobRestClient(settings=self._settings)
        self._rest_health = SourceHealth(name="clob_rest", state=ConnState.UNKNOWN)
        self._gamma_health = SourceHealth(name="gamma", state=ConnState.UNKNOWN)

    async def markets(self) -> list[Market]:
        try:
            raw_events = await self._gamma.list_events(
                limit=self._settings.discovery_limit, active=True, closed=False
            )
            markets = normalize_events_to_markets(raw_events)
            markets = [m for m in markets if _is_tradeable(m)]
            self._gamma_health = SourceHealth(
                name="gamma", state=ConnState.CONNECTED, last_success=_now()
            )
            return markets
        except AstrolabeClientError as exc:
            self._gamma_health = SourceHealth(
                name="gamma", state=ConnState.DISCONNECTED, last_error=str(exc)
            )
            raise

    async def search(
        self, query: str, *, active_only: bool = True, limit_per_type: int = 20
    ) -> list[Market]:
        """Full-universe market search via Gamma public-search (questions, descriptions,
        event titles, tags, slugs). Returns normalized tradeable markets."""
        events = await self._gamma.search(query, limit_per_type=limit_per_type)
        if active_only:
            events = [e for e in events if not e.get("closed", False)]
        markets = normalize_events_to_markets(events)
        return [m for m in markets if _is_tradeable(m)]

    async def get_token_data(self, market_id: str, token_id: str) -> TokenData:
        book: OrderBook | None = None
        prices: list[float] = []
        points: list[PricePoint] = []
        try:
            raw_book = await self._clob.get_book(token_id)
            book = normalize_book(token_id, raw_book)
            # Fetch the market's full history at 30-minute resolution, not just the last day:
            # many liquid markets are quiet intraday, so a 1-day window returned nothing and the
            # composite fell back to order-book imbalance alone. The full history gives the
            # price-behaviour features (return z-score, movement burst, volatility regime) real
            # data. Bounded to the most recent points to keep payloads sane.
            raw_hist = await self._clob.get_prices_history(token_id, interval="max", fidelity=30)
            points = normalize_price_history(raw_hist)[-LIVE_HISTORY_MAX:]
            prices = [pp.p for pp in points]
            self._rest_health = SourceHealth(
                name="clob_rest", state=ConnState.CONNECTED, last_success=_now()
            )
        except AstrolabeClientError as exc:
            # NotFound (resolved market, no book) is expected and benign; other client errors
            # mark REST degraded. Either way one token never crashes the request.
            if not isinstance(exc, NotFound):
                self._rest_health = SourceHealth(
                    name="clob_rest", state=ConnState.DEGRADED, last_error=str(exc)
                )
            logger.warning("live token data unavailable", extra={"ctx_token": token_id[:8]})
        except Exception as exc:  # noqa: BLE001 - belt-and-suspenders: never crash enrichment
            logger.warning("live token data error", extra={"ctx_error": str(exc)})
        captured = book.timestamp if book else None
        return TokenData(
            prices=prices, book=book, volumes=[], captured_at=captured, price_points=points
        )

    async def get_range_history(self, token_id: str, rng: str) -> list[PricePoint]:
        """Real price history for one token at a resolution suited to the chart range.

        Short ranges fetch fine (1-minute) points; longer ranges coarser ones; "7d" uses a
        start/end window. Returns [] on any error so the chart degrades to an empty state."""
        spec = _RANGE_FETCH.get(rng, _RANGE_FETCH["all"])
        try:
            if "window_seconds" in spec:
                now = int(datetime.now(UTC).timestamp())
                raw = await self._clob.get_prices_history(
                    token_id,
                    fidelity=spec["fidelity"],
                    start_ts=now - spec["window_seconds"],
                    end_ts=now,
                )
            else:
                raw = await self._clob.get_prices_history(
                    token_id, interval=spec["interval"], fidelity=spec["fidelity"]
                )
            return normalize_price_history(raw)[-LIVE_HISTORY_MAX:]
        except Exception as exc:  # noqa: BLE001 - never crash the detail request
            logger.warning("range history error", extra={"ctx_error": str(exc)})
            return []

    async def health(self) -> tuple[SourceHealth, SourceHealth]:
        # REST health tracked; the live WS runs in the ingestion pipeline (reported separately).
        rest = self._rest_health
        if rest.state == ConnState.UNKNOWN:
            rest = self._gamma_health
        ws = SourceHealth(name="clob_ws", state=ConnState.UNKNOWN)
        return rest, ws

    async def aclose(self) -> None:
        await asyncio.gather(self._gamma.aclose(), self._clob.aclose(), return_exceptions=True)


# --------------------------------------------------------------------------------------
# Cached (storage-backed, best-effort)
# --------------------------------------------------------------------------------------
class CachedSource:
    mode = DataMode.CACHED

    def __init__(self, session_factory=None):
        # session_factory: callable returning an async context manager AsyncSession.
        self._session_factory = session_factory

    def available(self) -> bool:
        return self._session_factory is not None

    async def markets(self) -> list[Market]:
        if not self._session_factory:
            return []
        from ..storage.repository import Repository  # lazy: storage may load late
        async with self._session_factory() as session:
            return await Repository(session).get_markets(limit=self._limit())

    async def get_token_data(self, market_id: str, token_id: str) -> TokenData:
        if not self._session_factory:
            return TokenData(prices=[], book=None, volumes=[], captured_at=None)
        from ..storage.repository import Repository
        async with self._session_factory() as session:
            repo = Repository(session)
            snap = await repo.latest_snapshot(token_id)
            series = await repo.price_series(token_id)
            prices = [p for _, p in series]
            points = [PricePoint(t=ts, p=p) for ts, p in series]
            book = snap.book if snap else None
            return TokenData(
                prices=prices, book=book, volumes=[],
                captured_at=snap.captured_at if snap else None,
                price_points=points,
            )

    async def health(self) -> tuple[SourceHealth, SourceHealth]:
        state = ConnState.CONNECTED if self.available() else ConnState.DISCONNECTED
        return (
            SourceHealth(name="cache", state=state),
            SourceHealth(name="clob_ws", state=ConnState.UNKNOWN),
        )

    @staticmethod
    def _limit() -> int:
        return get_settings().discovery_limit


def _is_tradeable(market: Market) -> bool:
    """Keep only markets likely to have a live, two-sided CLOB book worth analysing.

    Excludes markets without an order book, with fewer than two outcomes, or that are
    effectively resolved (an outcome priced ~0 or ~1 has no live book — fetching it 404s).
    """
    if not market.enable_order_book or len(market.outcomes) < 2:
        return False
    prices = [o.price for o in market.outcomes if o.price is not None]
    if prices and (max(prices) >= 0.999 or max(prices) <= 0.001):
        return False
    return True


def _now() -> datetime:
    return datetime.now(UTC)
