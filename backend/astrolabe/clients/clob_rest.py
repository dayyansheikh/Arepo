"""Async client for the Polymarket CLOB REST API (order book, price, price history).

All endpoints are keyed by ``token_id`` (a CLOB asset id = one outcome token). Scalar
convenience endpoints (midpoint/price/spread) parse their single numeric field into a float
here since there is no meaningful "raw" shape worth preserving; ``get_book`` and
``get_prices_history`` return raw dicts/lists — normalization into typed domain models happens
in ``astrolabe.ingest.normalize``.
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


def _to_float(value: Any) -> float | None:
    """Defensively coerce a scalar API field (often a string) to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ClobRestClient:
    """Thin async wrapper around the CLOB's read-only REST surface."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._settings.clob_base_url,
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
        exponential backoff; retries 429 honoring ``Retry-After`` when present. Non-retryable
        client errors are mapped to the typed hierarchy (``NotFound`` for 404, else
        ``UpstreamUnavailable``) so a raw ``httpx`` error never escapes this client. Only a 2xx
        response is returned.
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
                        "clob request failed after retries",
                        extra={"ctx_path": path, "ctx_error": str(exc)},
                    )
                    raise UpstreamUnavailable(
                        f"CLOB request to {path} failed: {exc}"
                    ) from exc
                await asyncio.sleep(_backoff_delay(attempt))
                continue

            if resp.status_code == 429:
                retry_after = _parse_retry_after(resp.headers.get("retry-after"))
                if attempt >= max_retries:
                    logger.warning(
                        "clob rate limited, retries exhausted", extra={"ctx_path": path}
                    )
                    raise RateLimited(
                        f"CLOB rate limited on {path}",
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
                        "clob upstream error, retries exhausted",
                        extra={"ctx_path": path, "ctx_status": resp.status_code},
                    )
                    raise UpstreamUnavailable(
                        f"CLOB {path} returned {resp.status_code}",
                        status_code=resp.status_code,
                    )
                await asyncio.sleep(_backoff_delay(attempt))
                continue

            # Non-retryable client errors: never leak a raw httpx error to callers — map to
            # the typed hierarchy so upstream code can catch AstrolabeClientError uniformly.
            if resp.status_code == 404:
                raise NotFound(f"CLOB {path} not found", status_code=404)
            if resp.status_code >= 400:
                raise UpstreamUnavailable(
                    f"CLOB {path} returned {resp.status_code}", status_code=resp.status_code
                )

            return resp

        # Defensive: loop always returns or raises above.
        raise UpstreamUnavailable(f"CLOB request to {path} failed after retries") from last_exc

    async def get_book(self, token_id: str) -> dict:
        resp = await self._request("GET", "/book", params={"token_id": token_id})
        data = resp.json()
        if not isinstance(data, dict):
            raise UpstreamSchemaError(
                "CLOB /book did not return an object", status_code=resp.status_code
            )
        return data

    async def get_midpoint(self, token_id: str) -> float | None:
        resp = await self._request("GET", "/midpoint", params={"token_id": token_id})
        data = resp.json()
        if not isinstance(data, dict):
            return None
        # Docs say "mid_price"; the live endpoint has been observed to return "mid" — accept
        # either (see docs/research-notes.md §4b).
        if "mid" in data:
            return _to_float(data["mid"])
        if "mid_price" in data:
            return _to_float(data["mid_price"])
        return None

    async def get_price(self, token_id: str, side: str) -> float | None:
        resp = await self._request(
            "GET", "/price", params={"token_id": token_id, "side": side}
        )
        data = resp.json()
        if not isinstance(data, dict):
            return None
        return _to_float(data.get("price"))

    async def get_spread(self, token_id: str) -> float | None:
        resp = await self._request("GET", "/spread", params={"token_id": token_id})
        data = resp.json()
        if not isinstance(data, dict):
            return None
        return _to_float(data.get("spread"))

    async def get_prices_history(
        self, token_id: str, interval: str = "1d", fidelity: int = 10
    ) -> list[dict]:
        resp = await self._request(
            "GET",
            "/prices-history",
            params={"market": token_id, "interval": interval, "fidelity": fidelity},
        )
        data = resp.json()
        if not isinstance(data, dict):
            raise UpstreamSchemaError(
                "CLOB /prices-history did not return an object", status_code=resp.status_code
            )
        history = data.get("history", [])
        if not isinstance(history, list):
            raise UpstreamSchemaError(
                "CLOB /prices-history 'history' field is not an array",
                status_code=resp.status_code,
            )
        return history
