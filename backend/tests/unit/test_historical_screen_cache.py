"""Caching / input bounds on the unauthenticated, expensive endpoints (audit run 1)."""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from astrolabe.api import app as app_mod
from astrolabe.api.routes import historical


async def test_screen_is_cached_and_concurrent_calls_share_one_computation(monkeypatch):
    calls = 0

    async def fake(service, as_of, universe_limit, top_n):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return {"n": calls}

    monkeypatch.setattr(historical, "run_live_historical", fake)
    historical._cache.clear()

    args = dict(days=7, limit=80, top_n=5, service=object())
    results = await asyncio.gather(*(historical.screen(**args) for _ in range(5)))
    assert calls == 1
    assert all(r == {"n": 1} for r in results)
    assert await historical.screen(**args) == {"n": 1}  # served from TTL cache
    assert calls == 1
    await historical.screen(days=8, limit=80, top_n=5, service=object())
    assert calls == 2  # different parameters compute separately
    historical._cache.clear()


def test_search_query_length_is_bounded():
    with TestClient(app_mod.create_app()) as c:
        r = c.get("/api/markets/search", params={"q": "x" * 201})
        assert r.status_code == 422
