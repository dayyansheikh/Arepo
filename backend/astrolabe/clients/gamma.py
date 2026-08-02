"""Async client for the Polymarket Gamma API (market/event discovery & metadata).

Returns RAW dicts/lists exactly as received from upstream. Normalization into typed domain
models happens separately in ``astrolabe.ingest.normalize`` — this module knows nothing about
``astrolabe.domain``.
"""
from __future__ import annotations

import asyncio
import random
from types import TracebackType
from typing import Any, Self

import httpx

from ..config import Settings, get_settings
from ..observability.logging import get_logger
from .errors import NotFound, RateLimited, UpstreamSchemaError, UpstreamUnavailable

logger = get_logger(__name__)

_BASE_DELAY_SECONDS = 0.05
_MAX_DELAY_SECONDS = 1.0


def _backoff_delay(attempt: int) -> float:
    """Bounded exponential backoff with jitter, ``attempt`` is 0-indexed."""
    delay = min(_BASE_DELAY_SECONDS * (2**attempt), _MAX_DELAY_SECONDS)
    return delay + random.uniform(0, delay * 0.1)


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a ``Retry-After`` header value (seconds form only). Returns None if unparsable."""
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


class GammaClient:
    """Thin async wrapper around Gamma's read-only REST surface."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._settings.gamma_base_url,
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

    async def _request(
        self, method: str, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Issue one request with bounded retry on transient failures.

        Retries timeouts/network errors and 5xx up to ``http_max_retries`` times with
        exponential backoff; retries 429 honoring ``Retry-After`` when present. Raises
        ``RateLimited`` / ``UpstreamUnavailable`` once retries are exhausted. Any other
        response (including non-retryable 4xx) is returned as-is for the caller to inspect.
        """
        max_retries = self._settings.http_max_retries
        last_exc: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                resp = await self._client.request(method, path, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt >= max_retries:
                    logger.warning(
                        "gamma request failed after retries",
                        extra={"ctx_path": path, "ctx_error": str(exc)},
                    )
                    raise UpstreamUnavailable(
                        f"Gamma request to {path} failed: {exc}"
                    ) from exc
                await asyncio.sleep(_backoff_delay(attempt))
                continue

            if resp.status_code == 429:
                retry_after = _parse_retry_after(resp.headers.get("retry-after"))
                if attempt >= max_retries:
                    logger.warning(
                        "gamma rate limited, retries exhausted", extra={"ctx_path": path}
                    )
                    raise RateLimited(
                        f"Gamma rate limited on {path}",
                        status_code=429,
                        retry_after=retry_after,
                    )
                await asyncio.sleep(
                    retry_after if retry_after is not None else _backoff_delay(attempt)
                )
                continue

            if resp.status_code >= 500:
                if attempt >= max_retries:
                    logger.warning(
                        "gamma upstream error, retries exhausted",
                        extra={"ctx_path": path, "ctx_status": resp.status_code},
                    )
                    raise UpstreamUnavailable(
                        f"Gamma {path} returned {resp.status_code}",
                        status_code=resp.status_code,
                    )
                await asyncio.sleep(_backoff_delay(attempt))
                continue

            # Non-retryable client errors: map to the typed hierarchy — never leak httpx.
            if resp.status_code == 404:
                raise NotFound(f"Gamma {path} not found", status_code=404)
            if resp.status_code >= 400:
                raise UpstreamUnavailable(
                    f"Gamma {path} returned {resp.status_code}", status_code=resp.status_code
                )

            return resp

        # Defensive: loop always returns or raises above.
        raise UpstreamUnavailable(f"Gamma request to {path} failed after retries") from last_exc

    async def list_markets(
        self,
        limit: int,
        active: bool = True,
        closed: bool = False,
        order: str | None = None,
        ascending: bool = False,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        if order is not None:
            params["order"] = order
            params["ascending"] = str(ascending).lower()

        resp = await self._request("GET", "/markets", params=params)
        data = resp.json()
        if not isinstance(data, list):
            raise UpstreamSchemaError(
                "Gamma /markets did not return a JSON array", status_code=resp.status_code
            )
        return data

    async def list_events(
        self, limit: int, active: bool = True, closed: bool = False
    ) -> list[dict]:
        params: dict[str, Any] = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        resp = await self._request("GET", "/events", params=params)
        data = resp.json()
        if not isinstance(data, list):
            raise UpstreamSchemaError(
                "Gamma /events did not return a JSON array", status_code=resp.status_code
            )
        return data

    async def get_market(self, market_id: str) -> dict | None:
        try:
            resp = await self._request("GET", f"/markets/{market_id}")
        except NotFound:
            return None
        data = resp.json()
        if not isinstance(data, dict):
            raise UpstreamSchemaError(
                f"Gamma /markets/{market_id} did not return an object",
                status_code=resp.status_code,
            )
        return data
