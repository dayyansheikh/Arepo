"""Exception hierarchy for upstream (Gamma / CLOB) HTTP clients.

Kept small and deliberate: callers up the stack (ingest, API) catch these to decide how to
degrade (serve cached data, surface a `DataMode.CACHED` envelope, etc.) without needing to
know anything about ``httpx`` internals.
"""
from __future__ import annotations


class AstrolabeClientError(Exception):
    """Base class for all upstream client errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class UpstreamUnavailable(AstrolabeClientError):
    """The upstream could not be reached, or failed repeatedly (timeouts, 5xx, network)."""


class RateLimited(AstrolabeClientError):
    """The upstream responded 429 and retries were exhausted (or none were configured)."""


class UpstreamSchemaError(AstrolabeClientError):
    """The upstream responded successfully but the payload shape was not what we expected."""
