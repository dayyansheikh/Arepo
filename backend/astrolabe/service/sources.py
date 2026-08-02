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
from ..clients.errors import AstrolabeClientError
from ..clients.gamma import GammaClient
from ..config import Settings, get_settings
from ..domain.enums import ConnState, DataMode
from ..domain.models import Market, OrderBook, SourceHealth
from ..ingest.normalize import (
    normalize_book,
    normalize_events_to_markets,
    normalize_price_history,
)
from ..observability.logging import get_logger
from ..replay.player import ReplayPlayer, default_player

logger = get_logger("astrolabe.service.sources")


@dataclass
class TokenData:
    prices: list[float]
    book: OrderBook | None
    volumes: list[float]
    captured_at: datetime | None


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
            # Keep only markets that have a live CLOB order book and >= 2 outcomes.
            markets = [m for m in markets if m.enable_order_book and len(m.outcomes) >= 2]
            self._gamma_health = SourceHealth(
                name="gamma", state=ConnState.CONNECTED, last_success=_now()
            )
            return markets
        except AstrolabeClientError as exc:
            self._gamma_health = SourceHealth(
                name="gamma", state=ConnState.DISCONNECTED, last_error=str(exc)
            )
            raise

    async def get_token_data(self, market_id: str, token_id: str) -> TokenData:
        book: OrderBook | None = None
        prices: list[float] = []
        try:
            raw_book = await self._clob.get_book(token_id)
            book = normalize_book(token_id, raw_book)
            raw_hist = await self._clob.get_prices_history(token_id, interval="1d", fidelity=10)
            prices = [pp.p for pp in normalize_price_history(raw_hist)]
            self._rest_health = SourceHealth(
                name="clob_rest", state=ConnState.CONNECTED, last_success=_now()
            )
        except AstrolabeClientError as exc:
            self._rest_health = SourceHealth(
                name="clob_rest", state=ConnState.DEGRADED, last_error=str(exc)
            )
            logger.warning("live token data failed", extra={"ctx_token": token_id[:8]})
        captured = book.timestamp if book else None
        return TokenData(prices=prices, book=book, volumes=[], captured_at=captured)

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
            book = snap.book if snap else None
            return TokenData(
                prices=prices, book=book, volumes=[],
                captured_at=snap.captured_at if snap else None,
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


def _now() -> datetime:
    return datetime.now(UTC)
