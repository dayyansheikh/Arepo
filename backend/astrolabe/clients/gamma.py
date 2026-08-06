"""Async client for the Polymarket Gamma API (market/event discovery & metadata).

Returns RAW dicts/lists exactly as received from upstream. Normalization into typed domain
models happens separately in ``astrolabe.ingest.normalize`` — this module knows nothing about
``astrolabe.domain``.
"""
from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Self

import httpx

from ..config import Settings, get_settings
from ..observability.logging import get_logger
from .errors import NotFound, RateLimited, UpstreamSchemaError, UpstreamUnavailable

logger = get_logger(__name__)


@dataclass
class PaginationReport:
    """Verifiable record of one complete-pagination attempt (prompt sections 2, 19, 23).

    ``complete`` is the single source of truth: a scan is complete only when the upstream genuinely
    signalled the end of the result set (an empty or short final page). Any offset cap, non-
    progressing page, transient failure after retries, or emergency-guard trip leaves ``complete``
    False with an ``incomplete_reason``, so a caller can fail loudly and refuse to build a cohort
    from a partial universe.
    """

    pages: int
    raw_items: int
    unique_markets: int
    complete: bool
    incomplete_reason: str | None = None
    offset_progression: list[int] = field(default_factory=list)
    duplicates_removed: int = 0
    repeated_page_detected: bool = False
    offset_cap_reached: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "pages": self.pages,
            "raw_items": self.raw_items,
            "unique_markets": self.unique_markets,
            "complete": self.complete,
            "incomplete_reason": self.incomplete_reason,
            "offset_progression": self.offset_progression,
            "duplicates_removed": self.duplicates_removed,
            "repeated_page_detected": self.repeated_page_detected,
            "offset_cap_reached": self.offset_cap_reached,
        }


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



def _safe_json(resp: httpx.Response):
    """Parse a response body as JSON, raising a typed error (never a raw json/httpx error)."""
    try:
        return resp.json()
    except (json.JSONDecodeError, ValueError) as exc:
        raise UpstreamSchemaError(
            "Gamma returned a non-JSON body", status_code=resp.status_code
        ) from exc


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
        offset: int | None = None,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        if offset is not None:
            params["offset"] = offset
        if order is not None:
            params["order"] = order
            params["ascending"] = str(ascending).lower()

        resp = await self._request("GET", "/markets", params=params)
        data = _safe_json(resp)
        if not isinstance(data, list):
            raise UpstreamSchemaError(
                "Gamma /markets did not return a JSON array", status_code=resp.status_code
            )
        return data

    async def paginate_markets(
        self,
        *,
        active: bool = True,
        closed: bool = False,
        page_size: int = 100,
        order: str | None = None,
        ascending: bool = False,
        max_pages: int = 1000,
        id_keys: tuple[str, ...] = ("conditionId", "id"),
    ) -> tuple[list[dict], PaginationReport]:
        """Follow EVERY offset page of Gamma ``/markets`` until the upstream signals completion.

        The core correction (prompt section 2): discovery must never stop at the first page or an
        arbitrary cap. It follows offset pages, deduplicates by canonical id, records page, raw
        unique counts and offset progression, detects a non-progressing page (only already-seen
        markets) and the upstream's documented offset cap (HTTP 422 "use keyset"), and enforces an
        emergency ``max_pages`` loop guard. Crucially it distinguishes GENUINE completion (an empty
        or short final page) from an INCOMPLETE scan (offset cap, non-progression, or the emergency
        guard): an incomplete scan sets ``complete=False`` with a reason so the caller fails loudly
        and never treats a partial universe as complete (prompt sections 2, 20).

        Bounded retries and typed errors are handled by ``_request`` per page. Repeated complete
        scans are idempotent: the same upstream yields the same deduplicated, deterministically
        ordered list.
        """
        seen: set[str] = set()
        out: list[dict] = []
        offset = 0
        pages = 0
        raw = 0
        duplicates = 0
        progression: list[int] = []
        complete = False
        reason: str | None = None
        repeated = False
        cap_reached = False

        while True:
            if pages >= max_pages:
                reason = (
                    f"emergency loop guard: {max_pages} pages fetched before the upstream "
                    "signalled "
                    "completion; scan marked incomplete rather than returning a partial universe"
                )
                break
            try:
                batch = await self.list_markets(
                    limit=page_size, active=active, closed=closed,
                    order=order, ascending=ascending, offset=offset,
                )
            except (UpstreamUnavailable, RateLimited) as exc:
                if getattr(exc, "status_code", None) == 422:
                    cap_reached = True
                    reason = (
                        "upstream offset pagination cap reached (HTTP 422: use keyset for deeper "
                        "pagination); deeper pages are unreachable on this endpoint, "
                        "scan incomplete"
                    )
                    break
                # A genuine transient failure after the client's bounded retries: fail loud.
                reason = f"upstream page fetch failed at offset {offset} after retries: {exc}"
                break

            progression.append(offset)
            if not batch:
                complete = True  # genuine exhaustion: the upstream returned an empty page
                break
            pages += 1
            raw += len(batch)
            new_in_page = 0
            for item in batch:
                key = next(
                    (str(item[k]) for k in id_keys if item.get(k) not in (None, "")), None
                )
                if key is None:
                    # No canonical id: keep it, keyed by position, but never silently drop it.
                    key = f"__pos_{offset}_{new_in_page}"
                if key in seen:
                    duplicates += 1
                    continue
                seen.add(key)
                out.append(item)
                new_in_page += 1
            if new_in_page == 0:
                repeated = True
                reason = (
                    f"non-progressing pagination at offset {offset}: the page contained only "
                    "already-seen markets; scan marked incomplete"
                )
                break
            if len(batch) < page_size:
                complete = True  # a short final page is a genuine end of the result set
                break
            offset += page_size

        report = PaginationReport(
            pages=pages, raw_items=raw, unique_markets=len(out),
            complete=complete, incomplete_reason=reason,
            offset_progression=progression, duplicates_removed=duplicates,
            repeated_page_detected=repeated, offset_cap_reached=cap_reached,
        )
        return out, report

    async def keyset_page(
        self,
        endpoint: str,
        *,
        after_cursor: str | None = None,
        active: bool = True,
        closed: bool = False,
        end_date_min: str | None = None,
        end_date_max: str | None = None,
        limit: int = 100,
    ) -> dict:
        """One page of a Gamma keyset endpoint (``/markets/keyset`` or ``/events/keyset``).

        Uses the official cursor contract: the FIRST request omits ``after_cursor``; subsequent
        requests pass the previous response's ``next_cursor`` as ``after_cursor`` (never ``offset``,
        never a guessed name). Returns the raw dict (top-level keys include the item list and
        ``next_cursor``). Bounded date filters keep the returned universe inside the target window.
        """
        params: dict[str, Any] = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        if end_date_min is not None:
            params["end_date_min"] = end_date_min
        if end_date_max is not None:
            params["end_date_max"] = end_date_max
        if after_cursor is not None:
            params["after_cursor"] = after_cursor
        resp = await self._request("GET", endpoint, params=params)
        data = _safe_json(resp)
        if not isinstance(data, dict):
            raise UpstreamSchemaError(
                f"Gamma {endpoint} did not return an object", status_code=resp.status_code
            )
        return data

    async def paginate_keyset(
        self,
        endpoint: str,
        item_key: str,
        *,
        active: bool = True,
        closed: bool = False,
        end_date_min: str | None = None,
        end_date_max: str | None = None,
        page_size: int = 100,
        max_pages: int = 5000,
    ) -> tuple[list[dict], dict]:
        """Follow the official keyset cursor to exhaustion, returning (items, report).

        Terminates cleanly when ``next_cursor`` is absent or an item page is empty; flags an
        incomplete scan (report ``complete=False`` + reason) on a repeated cursor, a page fetch
        failure after retries, or the emergency ``max_pages`` guard. ``item_key`` is ``markets`` for
        ``/markets/keyset`` or ``events`` for ``/events/keyset``. Raw items are returned verbatim
        (events still carry their nested markets); deduplication happens in the discovery layer.
        """
        items: list[dict] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        pages = 0
        complete = False
        reason: str | None = None
        while True:
            if pages >= max_pages:
                reason = (
                    f"emergency guard: {max_pages} keyset pages fetched on {endpoint} before "
                    "the cursor terminated; scan marked incomplete rather than partial"
                )
                break
            try:
                data = await self.keyset_page(
                    endpoint, after_cursor=cursor, active=active, closed=closed,
                    end_date_min=end_date_min, end_date_max=end_date_max, limit=page_size,
                )
            except (UpstreamUnavailable, RateLimited) as exc:
                reason = (
                    f"keyset page fetch on {endpoint} failed after retries at page {pages}: {exc}"
                )
                break
            page = data.get(item_key) or []
            pages += 1
            if page:
                items.extend(page)
            next_cursor = data.get("next_cursor")
            if not page or not next_cursor:
                complete = True  # genuine termination: empty page or no further cursor
                break
            if next_cursor in seen_cursors or next_cursor == cursor:
                reason = (
                    f"non-progressing keyset cursor on {endpoint} at page {pages} "
                    "(cursor repeated); scan marked incomplete"
                )
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        report = {
            "endpoint": endpoint,
            "pages": pages,
            "raw_items": len(items),
            "cursors": len(seen_cursors),
            "complete": complete,
            "incomplete_reason": reason,
        }
        return items, report

    async def list_events(
        self, limit: int, active: bool = True, closed: bool = False
    ) -> list[dict]:
        params: dict[str, Any] = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
        }
        resp = await self._request("GET", "/events", params=params)
        data = _safe_json(resp)
        if not isinstance(data, list):
            raise UpstreamSchemaError(
                "Gamma /events did not return a JSON array", status_code=resp.status_code
            )
        return data

    async def search(self, query: str, limit_per_type: int = 20) -> list[dict]:
        """Full-universe search via Gamma ``/public-search``. Returns matching events (each
        carrying its markets). Searches questions, descriptions, event titles, tags and slugs
        across the whole market universe, not just a pre-loaded page."""
        resp = await self._request(
            "GET", "/public-search", params={"q": query, "limit_per_type": limit_per_type}
        )
        data = _safe_json(resp)
        if isinstance(data, dict):
            events = data.get("events", [])
            return events if isinstance(events, list) else []
        return []

    async def get_market(self, market_id: str) -> dict | None:
        try:
            resp = await self._request("GET", f"/markets/{market_id}")
        except NotFound:
            return None
        data = _safe_json(resp)
        if not isinstance(data, dict):
            raise UpstreamSchemaError(
                f"Gamma /markets/{market_id} did not return an object",
                status_code=resp.status_code,
            )
        return data
