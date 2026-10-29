"""A small in-memory per-IP sliding-window rate limiter for account endpoints (spec §9).

Deliberately dependency-free and process-local. It protects the auth endpoints (register,
login, forgot-password, verify) from brute force and abuse in a single-process deployment. A
multi-process or multi-instance deployment should front this with a shared limiter (e.g. Redis
or the reverse proxy); this is documented in docs/authentication.md.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from ..config import get_settings

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque[float]] = defaultdict(deque)


_MAX_KEYS = 10_000


def _client_key(request: Request) -> str:
    """Identify the caller. X-Forwarded-For is client-controlled on its left side: each trusted
    proxy APPENDS the address it saw, so only the entry TRUSTED_PROXY_COUNT hops from the right is
    reliable. With 0 trusted proxies the header is ignored entirely."""
    direct = request.client.host if request.client else "unknown"
    n = get_settings().trusted_proxy_count
    fwd = request.headers.get("x-forwarded-for")
    if n > 0 and fwd:
        hops = [h.strip() for h in fwd.split(",") if h.strip()]
        if len(hops) >= n:
            return hops[-n]
    return direct


def cutoff_all(now: float) -> float:
    return now - _WINDOW_SECONDS


def reset() -> None:
    """Clear all counters (used by tests)."""
    _hits.clear()


def rate_limit(request: Request) -> None:
    """FastAPI dependency: raise 429 when a client exceeds the per-minute allowance.

    Uses ``time.monotonic`` so it is unaffected by wall-clock changes.
    """
    limit = get_settings().account_rate_limit_per_minute
    if limit <= 0:
        return
    now = time.monotonic()
    key = _client_key(request)
    if key not in _hits and len(_hits) >= _MAX_KEYS:
        # Bound memory: drop expired buckets first, then (if still full) the oldest-inserted key.
        for k in [k for k, b in _hits.items() if not b or b[-1] < cutoff_all(now)]:
            del _hits[k]
        if len(_hits) >= _MAX_KEYS:
            del _hits[next(iter(_hits))]
    bucket = _hits[key]
    cutoff = now - _WINDOW_SECONDS
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        retry_after = int(_WINDOW_SECONDS - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": str(max(1, retry_after))},
        )
    bucket.append(now)
