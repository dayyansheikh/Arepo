"""Production Explore must NEVER silently fall back to the demo/replay dataset.

Root cause fixed: with default_mode=live, MarketService._select_source used to fall back
live -> cached -> REPLAY. When live discovery was momentarily down on Render and the cached
MarketRow table was empty, Explore served the demo scenario (the fabricated "Team Aurora" /
"Candidate X" rows). These tests pin the production-safe behaviour: replay is only ever used
outside production; in production a live failure with no cached scan is an honest error.
"""
from __future__ import annotations

import pytest

from astrolabe.clients.errors import UpstreamUnavailable
from astrolabe.config import Settings
from astrolabe.domain.enums import DataMode
from astrolabe.service import MarketService


class _FailingLive:
    mode = DataMode.LIVE

    async def markets(self):
        raise RuntimeError("upstream down")


class _Cached:
    mode = DataMode.CACHED

    def __init__(self, markets):
        self._markets = markets

    def available(self) -> bool:
        return True

    async def markets(self):
        return list(self._markets)


def _prod_service() -> MarketService:
    return MarketService(settings=Settings(environment="production", default_mode="live"))


@pytest.mark.asyncio
async def test_production_live_failure_with_empty_cache_raises_not_demo():
    svc = _prod_service()
    svc._live = _FailingLive()
    svc._cached = _Cached([])  # nothing scanned yet
    with pytest.raises(UpstreamUnavailable):
        await svc._select_source(None)


@pytest.mark.asyncio
async def test_production_live_failure_uses_cached_scan_never_replay():
    svc = _prod_service()
    # Reuse the replay player's Market objects purely as stand-in "cached scan" rows.
    cached_markets = await svc._replay.markets()
    assert cached_markets, "fixture sanity: replay player has markets to stand in for a scan"
    svc._live = _FailingLive()
    svc._cached = _Cached(cached_markets)
    source, reason = await svc._select_source(None)
    assert source.mode == DataMode.CACHED
    assert reason and "scan" in reason.lower()


@pytest.mark.asyncio
async def test_production_replay_request_is_refused_and_never_serves_demo():
    svc = _prod_service()
    # Live is healthy here; an explicit ?mode=replay must NOT return the demo dataset in production.
    source, _reason = await svc._select_source("replay")
    assert source.mode == DataMode.LIVE
    assert source is svc._live


@pytest.mark.asyncio
async def test_non_production_still_falls_back_to_replay_for_dev_and_tests():
    svc = MarketService(settings=Settings(environment="development", default_mode="live"))
    svc._live = _FailingLive()
    svc._cached = _Cached([])
    source, reason = await svc._select_source(None)
    assert source.mode == DataMode.REPLAY
    assert reason and "replay" in reason.lower()
