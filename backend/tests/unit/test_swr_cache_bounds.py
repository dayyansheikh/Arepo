"""SwrCache memory bounds: entry cap + one build at a time (infra 2026-10-11)."""
import asyncio

from astrolabe.opportunity.cache import SwrCache


async def test_entries_are_capped_to_most_recent():
    cache: SwrCache[int] = SwrCache(max_entries=3)
    for i in range(10):
        async def build(i=i):
            return i
        assert await cache.get(f"k{i}", build) == i
    assert sorted(cache._entries) == ["k7", "k8", "k9"]
    assert len(cache._locks) <= 3


async def test_builds_for_different_keys_never_overlap():
    cache: SwrCache[int] = SwrCache(max_concurrent_builds=1)
    active = {"now": 0, "peak": 0}

    async def build():
        active["now"] += 1
        active["peak"] = max(active["peak"], active["now"])
        await asyncio.sleep(0.02)
        active["now"] -= 1
        return 1

    await asyncio.gather(*(cache.get(f"k{i}", build) for i in range(5)))
    assert active["peak"] == 1
