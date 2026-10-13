"""Render-OOM / egress guards on the API's market-universe paths (infra fix 2026-10-11).

* Explore/facets results are IDENTICAL whether the universe is held as lean records or as full
  pydantic ``Market`` objects (parity over a randomised universe and a query matrix).
* The process cache re-reads the universe only when the latest scan changes (or a hard max age).
* Concurrent cache misses share one read (single-flight).
* The live-failure fallback (/api/status, market detail) never materialises the whole universe.
"""
import asyncio
import random
from datetime import UTC, datetime, timedelta

import pytest

import astrolabe.storage.migrate  # noqa: F401  (registers every ORM table on Base.metadata)
from astrolabe.config import Settings
from astrolabe.domain.enums import MarketStatus
from astrolabe.domain.models import Market, Outcome
from astrolabe.service import MarketService
from astrolabe.storage.db import Base, make_engine, make_sessionmaker
from astrolabe.storage.repository import Repository

CATS = ["Crypto", "Sports", "Politics", None, "Economy"]
WORDS = "alpha beta Election rate CUT bitcoin team final win yes no Trump fed".split()


def _markets(n: int, seed: int = 3) -> list[Market]:
    rng = random.Random(seed)
    now = datetime.now(UTC)
    out = []
    for i in range(n):
        p = rng.choice([None, round(rng.uniform(0, 1), 3), 1.0, 0.0])
        out.append(Market(
            id=f"m{i}", question=" ".join(rng.choices(WORDS, k=5)), slug=f"slug-{i}",
            condition_id=f"c{i}",
            outcomes=[Outcome(name="Yes", token_id=f"{i}-y", price=p),
                      Outcome(name="No", token_id=f"{i}-n",
                              price=None if p is None else round(1 - p, 3))],
            status=rng.choice([MarketStatus.ACTIVE, MarketStatus.CLOSED]),
            enable_order_book=True, category=rng.choice(CATS),
            tags=rng.sample(WORDS, k=rng.randint(0, 3)),
            end_date=rng.choice([None, now + timedelta(days=rng.randint(-5, 60))]),
            volume=rng.choice([None, rng.uniform(0, 1000)]),
            volume_24hr=rng.choice([None, rng.uniform(0, 100)]),
            liquidity=rng.choice([None, rng.uniform(0, 100)]),
            description=rng.choice([None, " ".join(rng.choices(WORDS, k=30))]),
            image="https://img/x.png",
            updated_at=now - timedelta(minutes=rng.randint(0, 600)),
        ))
    return out


@pytest.fixture
async def svc_factory():
    engines = []
    services = []

    async def make(cache_seconds: int):
        engine = make_engine("sqlite+aiosqlite:///:memory:")
        engines.append(engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sessions = make_sessionmaker(engine)
        async with sessions() as session:
            await Repository(session).upsert_markets(_markets(300))
        service = MarketService(
            Settings(environment="production", default_mode="cached",
                     explore_cache_seconds=cache_seconds),
            cached_session_factory=sessions,
        )
        services.append(service)
        return service

    yield make
    for s in services:
        await s.aclose()
    for e in engines:
        await e.dispose()


QUERIES = [
    {}, {"sort": "volume_24hr"}, {"sort": "liquidity"}, {"sort": "end_date"},
    {"sort": "signal_desc"}, {"sort": "signal_asc"}, {"search": "election"}, {"search": "msft"},
    {"search": "BITCOIN"}, {"category": "Crypto"}, {"category": "Sports", "closing": "week"},
    {"status": "closed"}, {"closing": "month", "sort": "end_date"}, {"limit": 7, "offset": 13},
]


async def test_lean_universe_results_are_identical_to_pydantic_universe(svc_factory):
    service = await svc_factory(0)   # caching off: every call reads fresh
    lean = [await service.list_markets(requested_mode="cached", **q) for q in QUERIES]
    lean_facets = await service.facets(requested_mode="cached")
    # Legacy path: full pydantic Market objects for the whole universe.
    service._cached.explore_markets = service._cached.markets  # type: ignore[method-assign]
    legacy = [await service.list_markets(requested_mode="cached", **q) for q in QUERIES]
    legacy_facets = await service.facets(requested_mode="cached")
    for a, b in zip(lean, legacy, strict=True):
        assert a.model_dump(exclude={"status"}) == b.model_dump(exclude={"status"})
        assert a.status.last_update == b.status.last_update
    assert lean_facets == legacy_facets
    assert sum(r.total for r in lean) > 0


async def test_cache_rereads_only_when_the_latest_scan_changes(svc_factory, monkeypatch):
    service = await svc_factory(60)
    reads = []
    original = service._cached.explore_markets

    async def counting(**kw):
        reads.append(1)
        return await original(**kw)

    service._cached.explore_markets = counting  # type: ignore[method-assign]
    key = {"v": "scan-1"}

    async def scan_key():
        return key["v"]

    monkeypatch.setattr(service, "_latest_scan_key", scan_key)
    await service.list_markets(requested_mode="cached")
    await service.facets(requested_mode="cached")
    assert len(reads) == 1
    # Window elapsed, same scan: revalidated by id, no re-read.
    service._universe_cache.checked_at -= 120
    await service.list_markets(requested_mode="cached")
    assert len(reads) == 1
    # A new scan landed: re-read.
    service._universe_cache.checked_at -= 120
    key["v"] = "scan-2"
    await service.list_markets(requested_mode="cached")
    assert len(reads) == 2
    # Hard max age forces a re-read even for an unchanged scan.
    service._universe_cache.checked_at -= 120
    service._universe_cache.loaded_at -= service._settings.explore_cache_max_age_seconds + 1
    await service.list_markets(requested_mode="cached")
    assert len(reads) == 3


async def test_concurrent_misses_share_one_read(svc_factory):
    service = await svc_factory(60)
    reads = []
    original = service._cached.explore_markets

    async def slow(**kw):
        reads.append(1)
        await asyncio.sleep(0.05)
        return await original(**kw)

    service._cached.explore_markets = slow  # type: ignore[method-assign]
    await asyncio.gather(*(service.list_markets(requested_mode="cached") for _ in range(5)))
    assert len(reads) == 1


async def test_live_failure_fallback_never_materialises_the_universe(svc_factory):
    service = await svc_factory(60)

    async def live_down():
        raise RuntimeError("gamma down")

    async def full_read_forbidden(*a, **k):
        raise AssertionError("full markets read on a fallback path")

    service._live.markets = live_down  # type: ignore[method-assign]
    service._cached.markets = full_read_forbidden  # type: ignore[method-assign]
    status = await service.status(requested_mode="live")
    assert status.mode.value == "cached"
    assert "using latest scan" in (status.degradation_reason or "")
    market = await service._find_market(service._cached, "m7")
    assert market is not None and market.id == "m7"
    assert await service._find_market(service._cached, "missing") is None


def _live(env: str, ttl: int = 30):
    from astrolabe.service.sources import LiveSource

    src = LiveSource(Settings(environment=env, live_discovery_cache_seconds=ttl))
    calls = {"n": 0, "fail": False}

    async def list_events(limit, active=True, closed=False):  # noqa: ARG001
        calls["n"] += 1
        if calls["fail"]:
            from astrolabe.clients.errors import UpstreamUnavailable
            raise UpstreamUnavailable("down")
        return []

    src._gamma.list_events = list_events  # type: ignore[method-assign]
    return src, calls


async def test_live_discovery_memo_shares_one_fetch_in_production():
    src, calls = _live("production")
    await asyncio.gather(*(src.markets() for _ in range(5)))
    await src.markets()
    assert calls["n"] == 1
    src._markets_memo = (src._markets_memo[0] - 60, src._markets_memo[1])  # expire
    await src.markets()
    assert calls["n"] == 2
    await src.aclose()


async def test_live_discovery_failures_are_not_memoised_and_dev_is_uncached():
    src, calls = _live("production")
    calls["fail"] = True
    for _ in range(2):
        with pytest.raises(Exception):  # noqa: B017,PT011
            await src.markets()
    assert calls["n"] == 2
    await src.aclose()
    dev, dcalls = _live("development")
    await dev.markets()
    await dev.markets()
    assert dcalls["n"] == 2
    await dev.aclose()
