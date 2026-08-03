"""Tests for the Opportunity Board stale-while-revalidate cache (spec §13)."""
import asyncio

from astrolabe.opportunity.cache import SwrCache


async def test_first_call_is_a_miss_and_builds():
    cache: SwrCache[int] = SwrCache(fresh_ttl=100, hard_ttl=1000)
    calls = 0

    async def build() -> int:
        nonlocal calls
        calls += 1
        return 42

    assert await cache.get("k", build) == 42
    assert cache.last_status == "miss"
    assert calls == 1


async def test_fresh_hit_does_not_rebuild():
    cache: SwrCache[int] = SwrCache(fresh_ttl=100, hard_ttl=1000)
    calls = 0

    async def build() -> int:
        nonlocal calls
        calls += 1
        return calls

    await cache.get("k", build)
    v = await cache.get("k", build)  # still fresh
    assert v == 1
    assert cache.last_status == "hit"
    assert calls == 1


async def test_stale_serves_old_and_refreshes_in_background():
    cache: SwrCache[int] = SwrCache(fresh_ttl=0.0, hard_ttl=1000)  # everything is instantly stale
    calls = 0

    async def build() -> int:
        nonlocal calls
        calls += 1
        return calls

    assert await cache.get("k", build) == 1  # miss -> build
    # Next call finds it stale: returns the OLD value immediately, refreshes in the background.
    v = await cache.get("k", build)
    assert v == 1
    assert cache.last_status == "stale"
    await asyncio.sleep(0.05)  # let the background refresh run
    assert calls == 2  # background rebuild happened


async def test_concurrent_misses_build_once():
    cache: SwrCache[int] = SwrCache(fresh_ttl=100, hard_ttl=1000)
    calls = 0

    async def build() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return calls

    results = await asyncio.gather(*(cache.get("k", build) for _ in range(5)))
    # The per-key lock means the expensive build runs once; all callers get that result.
    assert calls == 1
    assert results == [1, 1, 1, 1, 1]
