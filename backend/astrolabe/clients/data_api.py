"""Async client for the Polymarket Data API (read-only public trade activity).

Endpoint used: ``GET /trades`` filtered by ``market`` (a market conditionId) or by ``user``
(a proxy-wallet address). Returns raw trade dicts, newest first; normalization into
``domain.models.Trade`` happens in ``ingest.normalize``. Only public, read-only data is used,
and wallet addresses are only ever used for neutral aggregate measures.
"""
from __future__ import annotations

import asyncio
import json
import random
from types import TracebackType
from typing import Any, Self

import httpx

from ..config import Settings, get_settings
from ..observability.logging import get_logger
from .errors import NotFound, RateLimited, UpstreamSchemaError, UpstreamUnavailable

logger = get_logger(__name__)


def _backoff(attempt: int) -> float:
    delay = min(0.05 * (2**attempt), 1.0)
    return delay + random.uniform(0, delay * 0.1)


class DataApiClient:
    """Thin async wrapper over the Data API's read-only ``/trades`` surface."""

    def __init__(
        self, client: httpx.AsyncClient | None = None, *, settings: Settings | None = None
    ) -> None:
        self._settings = settings or get_settings()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._settings.data_api_base_url,
            timeout=self._settings.http_timeout_seconds,
            headers={"User-Agent": self._settings.http_user_agent},
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def _get(self, path: str, params: dict[str, Any]) -> list[dict]:
        max_retries = self._settings.http_max_retries
        for attempt in range(max_retries + 1):
            try:
                resp = await self._client.request("GET", path, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= max_retries:
                    raise UpstreamUnavailable(f"Data API {path} failed: {exc}") from exc
                await asyncio.sleep(_backoff(attempt))
                continue

            if resp.status_code == 429:
                if attempt >= max_retries:
                    raise RateLimited(f"Data API rate limited on {path}", status_code=429)
                await asyncio.sleep(_backoff(attempt))
                continue
            if resp.status_code == 404:
                raise NotFound(f"Data API {path} not found", status_code=404)
            if resp.status_code >= 500:
                if attempt >= max_retries:
                    raise UpstreamUnavailable(
                        f"Data API {path} returned {resp.status_code}", status_code=resp.status_code
                    )
                await asyncio.sleep(_backoff(attempt))
                continue
            if resp.status_code >= 400:
                raise UpstreamUnavailable(
                    f"Data API {path} returned {resp.status_code}", status_code=resp.status_code
                )

            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise UpstreamSchemaError(
                    "Data API returned a non-JSON body", status_code=resp.status_code
                ) from exc
            if not isinstance(data, list):
                raise UpstreamSchemaError(
                    "Data API /trades did not return a list", status_code=resp.status_code
                )
            return data
        return []  # pragma: no cover - loop always returns or raises

    async def get_market_trades(self, condition_id: str, limit: int = 1000) -> list[dict]:
        """Recent public trades for a market (by conditionId), newest first."""
        return await self._get("/trades", {"market": condition_id, "limit": limit})

    async def get_wallet_trades(self, wallet: str, limit: int = 100) -> list[dict]:
        """A wallet's recent public trades across markets (used only for activity breadth)."""
        return await self._get("/trades", {"user": wallet, "limit": limit})
