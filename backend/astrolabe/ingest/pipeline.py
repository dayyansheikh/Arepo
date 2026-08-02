"""Ingestion pipeline: Gamma discovery -> CLOB snapshots -> validation -> storage.

Implements the spec's data flow (§10) for the *cached* mode: it periodically pulls real
public data, normalizes it into typed domain models, and persists market metadata + token
snapshots so the API can serve recent stored data when live retrieval fails.

Runs standalone (``python -m astrolabe.ingest.pipeline`` via ``scripts/ingest.py``) or as an
optional background task. All upstream calls are read-only and rate-limit-polite (bounded set,
small concurrency). Clients are injectable so the pipeline is unit-testable with no network.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from ..clients.clob_rest import ClobRestClient
from ..clients.errors import AstrolabeClientError
from ..clients.gamma import GammaClient
from ..config import Settings, get_settings
from ..domain.enums import ConnState, MarketStatus
from ..domain.models import Market, MarketSnapshot, SourceHealth
from ..observability.logging import get_logger
from ..storage.repository import Repository
from .normalize import normalize_book, normalize_events_to_markets

logger = get_logger("astrolabe.ingest.pipeline")


def _tradeable(m: Market) -> bool:
    if not m.enable_order_book or len(m.outcomes) < 2 or m.status != MarketStatus.ACTIVE:
        return False
    prices = [o.price for o in m.outcomes if o.price is not None]
    return not (prices and (max(prices) >= 0.999 or max(prices) <= 0.001))


class IngestionPipeline:
    def __init__(
        self,
        session_factory,
        *,
        settings: Settings | None = None,
        gamma: GammaClient | None = None,
        clob: ClobRestClient | None = None,
        max_snapshot_markets: int = 15,
        snapshot_concurrency: int = 5,
    ):
        self._settings = settings or get_settings()
        self._session_factory = session_factory
        self._gamma = gamma or GammaClient(settings=self._settings)
        self._clob = clob or ClobRestClient(settings=self._settings)
        self._max_snapshot_markets = max_snapshot_markets
        self._sem = asyncio.Semaphore(snapshot_concurrency)

    async def discover_and_store(self, limit: int | None = None) -> list[Market]:
        """Fetch active events, normalize to tradeable markets, upsert to storage."""
        raw_events = await self._gamma.list_events(
            limit=limit or self._settings.discovery_limit, active=True, closed=False
        )
        markets = [m for m in normalize_events_to_markets(raw_events) if _tradeable(m)]
        async with self._session_factory() as session:
            repo = Repository(session)
            await repo.upsert_markets(markets)
            await repo.upsert_source_health(
                SourceHealth(name="gamma", state=ConnState.CONNECTED, last_success=_now())
            )
        logger.info("ingest.discovered", extra={"ctx_markets": len(markets)})
        return markets

    async def snapshot_tokens(self, markets: list[Market]) -> int:
        """Snapshot order books for the top markets by volume and persist them."""
        top = sorted(markets, key=lambda m: m.volume or 0.0, reverse=True)[
            : self._max_snapshot_markets
        ]

        async def snap_one(market: Market, token_id: str) -> MarketSnapshot | None:
            async with self._sem:
                try:
                    raw = await self._clob.get_book(token_id)
                except AstrolabeClientError:
                    return None
                book = normalize_book(token_id, raw)
                return MarketSnapshot(
                    token_id=token_id,
                    market_id=market.id,
                    book=book,
                    midpoint=book.midpoint,
                    spread=book.spread,
                    captured_at=book.timestamp,
                )

        tasks = [snap_one(m, o.token_id) for m in top for o in m.outcomes]
        snaps = [s for s in await asyncio.gather(*tasks) if s is not None]

        async with self._session_factory() as session:
            repo = Repository(session)
            for snap in snaps:
                await repo.insert_snapshot(snap)
            await repo.upsert_source_health(
                SourceHealth(name="clob_rest", state=ConnState.CONNECTED, last_success=_now())
            )
        logger.info("ingest.snapshotted", extra={"ctx_snapshots": len(snaps)})
        return len(snaps)

    async def run_once(self, limit: int | None = None) -> dict:
        """One full discovery + snapshot cycle. Returns a small summary dict."""
        markets = await self.discover_and_store(limit)
        n_snaps = await self.snapshot_tokens(markets)
        return {"markets": len(markets), "snapshots": n_snaps}

    async def run_forever(self, interval_seconds: float | None = None) -> None:
        """Loop ``run_once`` on an interval until cancelled (for a long-running ingester)."""
        interval = interval_seconds or self._settings.poll_interval_seconds
        while True:
            try:
                await self.run_once()
            except AstrolabeClientError as exc:
                logger.warning("ingest.cycle_failed", extra={"ctx_err": str(exc)})
            await asyncio.sleep(interval)

    async def aclose(self) -> None:
        await asyncio.gather(self._gamma.aclose(), self._clob.aclose(), return_exceptions=True)


def _now() -> datetime:
    return datetime.now(UTC)
