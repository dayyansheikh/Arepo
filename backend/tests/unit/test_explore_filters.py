"""Explore applies shared filters and signal ordering before its display page is sliced."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from astrolabe.config import Settings
from astrolabe.domain.enums import MarketStatus
from astrolabe.domain.models import Market, Outcome
from astrolabe.service import MarketService
from astrolabe.storage.db import Base, make_engine, make_sessionmaker
from astrolabe.storage.repository import Repository


@pytest.fixture
async def explore_service(monkeypatch):
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = make_sessionmaker(engine)
    now = datetime.now(UTC)
    markets = [
        Market(
            id="low", question="Alpha crypto low", slug="low", condition_id="c-low",
            outcomes=[Outcome(name="Yes", token_id="low-y", price=0.4)],
            status=MarketStatus.ACTIVE, enable_order_book=True, category="Crypto",
            tags=["Crypto"], end_date=now + timedelta(days=3), volume=1,
        ),
        Market(
            id="high", question="Alpha crypto high", slug="high", condition_id="c-high",
            outcomes=[Outcome(name="Yes", token_id="high-y", price=0.5)],
            status=MarketStatus.ACTIVE, enable_order_book=True, category="Crypto",
            tags=["Crypto"], end_date=now + timedelta(days=20), volume=2,
        ),
        Market(
            id="middle", question="Sports middle", slug="middle", condition_id="c-middle",
            outcomes=[Outcome(name="Yes", token_id="middle-y", price=0.6)],
            status=MarketStatus.ACTIVE, enable_order_book=True, category="Sports",
            tags=["Sports"], end_date=now + timedelta(days=60), volume=3,
        ),
        Market(
            id="none", question="Crypto without signal", slug="none", condition_id="c-none",
            outcomes=[Outcome(name="Yes", token_id="none-y", price=0.7)],
            status=MarketStatus.ACTIVE, enable_order_book=True, category="Crypto",
            tags=["Crypto"], end_date=now + timedelta(days=4), volume=999,
        ),
    ]
    async with sessions() as session:
        await Repository(session).upsert_markets(markets)

    service = MarketService(
        Settings(environment="production", default_mode="cached"),
        cached_session_factory=sessions,
    )

    async def latest_signals():
        return {
            "low": SimpleNamespace(strength=0.2, primary_category="Crypto"),
            "high": SimpleNamespace(strength=0.9, primary_category="Crypto"),
            "middle": SimpleNamespace(strength=0.5, primary_category="Sports"),
        }

    monkeypatch.setattr(service, "_latest_signal_by_market", latest_signals)
    yield service
    await service.aclose()
    await engine.dispose()


async def test_signal_sort_is_global_then_paginated_and_nulls_are_last(explore_service):
    high = await explore_service.list_markets(
        requested_mode="cached", sort="signal_desc", limit=2,
    )
    assert [market.id for market in high.markets] == ["high", "middle"]
    low = await explore_service.list_markets(
        requested_mode="cached", sort="signal_asc", limit=4,
    )
    assert [market.id for market in low.markets] == ["low", "middle", "high", "none"]


async def test_combined_search_category_and_time_use_complete_cached_universe(explore_service):
    result = await explore_service.list_markets(
        requested_mode="cached",
        search="Alpha",
        category="Crypto",
        closing="month",
        sort="signal_desc",
        limit=1,
    )
    assert result.total == 1
    assert result.markets[0].id == "high"
    assert result.markets[0].category == "Crypto"


async def test_production_replay_mode_state_cannot_bypass_complete_cached_universe(
    explore_service,
):
    result = await explore_service.list_markets(
        requested_mode="replay", sort="signal_desc", limit=4,
    )
    assert result.total == 4
    assert [market.id for market in result.markets] == ["high", "middle", "low", "none"]
    assert result.status.mode.value == "cached"


async def test_explore_universe_read_is_cached_in_production(explore_service):
    """Egress: repeated Explore/facets requests must not re-read the full universe from Supabase
    each time. In production the universe (latest complete scan) is cached in-process, so N requests
    within the window trigger ONE storage read, not N."""
    reads = {"n": 0}
    original = explore_service._read_explore_universe

    async def counting(mode):
        reads["n"] += 1
        return await original(mode)

    explore_service._read_explore_universe = counting  # type: ignore[assignment]

    # A typical Explore page load: list + facets, then a category change, then a sort change.
    await explore_service.list_markets(requested_mode="cached", limit=20)
    await explore_service.facets(requested_mode="cached")
    await explore_service.list_markets(requested_mode="cached", category="Crypto", limit=20)
    await explore_service.list_markets(requested_mode="cached", sort="signal_desc", limit=20)

    assert reads["n"] == 1, f"expected one cached universe read, got {reads['n']}"
    # The cached result is still correct (same data): Crypto filter returns the 3 crypto markets.
    resp = await explore_service.list_markets(requested_mode="cached", category="Crypto", limit=50)
    assert {c.id for c in resp.markets} == {"low", "high", "none"}


async def test_explore_cache_disabled_reads_fresh_each_call(explore_service):
    """With explore_cache_seconds=0 (or non-production), every call reads fresh — identical to the
    pre-cache behaviour, so tests/dev never serve stale in-process data."""
    explore_service._settings.explore_cache_seconds = 0
    reads = {"n": 0}
    original = explore_service._read_explore_universe

    async def counting(mode):
        reads["n"] += 1
        return await original(mode)

    explore_service._read_explore_universe = counting  # type: ignore[assignment]
    await explore_service.list_markets(requested_mode="cached", limit=20)
    await explore_service.list_markets(requested_mode="cached", limit=20)
    assert reads["n"] == 2
