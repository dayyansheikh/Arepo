"""Unit tests for the storage layer: repository round-trips + TTL cache.

All tests use an in-memory SQLite database (no real network, no on-disk file) created
fresh per test via ``init_db``. See ``astrolabe/storage/db.py`` for why in-memory SQLite
needs ``StaticPool`` (handled transparently by ``make_engine``).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.domain.enums import ConnState, MarketStatus
from astrolabe.domain.models import (
    BookLevel,
    Market,
    MarketSnapshot,
    OrderBook,
    Outcome,
    SourceHealth,
)
from astrolabe.storage.cache import TTLCache
from astrolabe.storage.db import init_db, make_engine, make_sessionmaker
from astrolabe.storage.repository import Repository


@pytest.fixture
async def engine():
    eng = make_engine("sqlite+aiosqlite:///:memory:")
    await init_db(eng)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    sessionmaker = make_sessionmaker(engine)
    async with sessionmaker() as sess:
        yield sess


@pytest.fixture
def repo(session):
    return Repository(session)


def _make_market(
    market_id: str,
    *,
    question: str = "Will X happen?",
    category: str | None = "Politics",
    volume: float | None = 100.0,
    volume_24hr: float | None = 10.0,
    end_date: datetime | None = None,
) -> Market:
    return Market(
        id=market_id,
        question=question,
        slug=f"slug-{market_id}",
        condition_id=f"cond-{market_id}",
        outcomes=[
            Outcome(name="Yes", token_id=f"{market_id}-yes", price=0.6),
            Outcome(name="No", token_id=f"{market_id}-no", price=0.4),
        ],
        status=MarketStatus.ACTIVE,
        enable_order_book=True,
        category=category,
        tags=["tag-a", "tag-b"],
        volume=volume,
        volume_24hr=volume_24hr,
        liquidity=50.0,
        tick_size=0.01,
        min_order_size=5.0,
        end_date=end_date or datetime(2026, 12, 31, tzinfo=UTC),
        description="A test market.",
        image="https://example.com/image.png",
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


# --------------------------------------------------------------------------------------
# Markets
# --------------------------------------------------------------------------------------


async def test_upsert_and_get_market_round_trip(repo: Repository):
    market = _make_market("m1")
    count = await repo.upsert_markets([market])
    assert count == 1

    fetched = await repo.get_market("m1")
    assert fetched is not None
    assert fetched.id == "m1"
    assert fetched.question == market.question
    assert fetched.slug == market.slug
    assert fetched.condition_id == market.condition_id
    assert fetched.status == MarketStatus.ACTIVE
    assert fetched.enable_order_book is True
    assert fetched.category == "Politics"
    assert fetched.tags == ["tag-a", "tag-b"]
    assert fetched.volume == 100.0
    assert fetched.volume_24hr == 10.0
    assert fetched.liquidity == 50.0
    assert fetched.tick_size == 0.01
    assert fetched.min_order_size == 5.0
    assert fetched.description == "A test market."
    assert fetched.image == "https://example.com/image.png"

    # outcomes preserved, including token ids and prices
    assert [o.name for o in fetched.outcomes] == ["Yes", "No"]
    assert [o.token_id for o in fetched.outcomes] == ["m1-yes", "m1-no"]
    assert [o.price for o in fetched.outcomes] == [0.6, 0.4]

    # tz-aware datetimes preserved (value equal, regardless of naive-vs-aware storage
    # detail inside SQLite -- the repository always reattaches UTC on read)
    assert fetched.end_date is not None
    assert fetched.end_date.tzinfo is not None
    assert fetched.end_date == datetime(2026, 12, 31, tzinfo=UTC)
    assert fetched.updated_at == datetime(2026, 1, 1, tzinfo=UTC)


async def test_get_market_missing_returns_none(repo: Repository):
    assert await repo.get_market("does-not-exist") is None


async def test_upsert_is_idempotent_and_updates(repo: Repository):
    market = _make_market("m1", question="Original question", volume=100.0)
    await repo.upsert_markets([market])

    updated = _make_market("m1", question="Updated question", volume=999.0)
    count = await repo.upsert_markets([updated])
    assert count == 1

    assert await repo.count_markets() == 1  # still only one row, not a duplicate
    fetched = await repo.get_market("m1")
    assert fetched is not None
    assert fetched.question == "Updated question"
    assert fetched.volume == 999.0


async def test_get_markets_search_category_ordering_limit_offset(repo: Repository):
    markets = [
        _make_market("m1", question="Will Alice win?", category="Politics", volume=300.0),
        _make_market("m2", question="Will Bob win?", category="Politics", volume=100.0),
        _make_market("m3", question="Will it rain?", category="Weather", volume=200.0),
    ]
    await repo.upsert_markets(markets)

    # search is case-insensitive substring match over question
    results = await repo.get_markets(search="alice")
    assert [m.id for m in results] == ["m1"]

    # category filter
    results = await repo.get_markets(category="Politics")
    assert {m.id for m in results} == {"m1", "m2"}

    # ordering by volume desc (default)
    results = await repo.get_markets()
    assert [m.id for m in results] == ["m1", "m3", "m2"]

    # limit/offset
    results = await repo.get_markets(limit=1, offset=1)
    assert [m.id for m in results] == ["m3"]

    # count respects filters
    assert await repo.count_markets() == 3
    assert await repo.count_markets(category="Politics") == 2
    assert await repo.count_markets(search="rain") == 1


async def test_get_markets_order_by_end_date(repo: Repository):
    markets = [
        _make_market("m1", end_date=datetime(2026, 6, 1, tzinfo=UTC)),
        _make_market("m2", end_date=datetime(2026, 3, 1, tzinfo=UTC)),
        _make_market("m3", end_date=datetime(2026, 9, 1, tzinfo=UTC)),
    ]
    await repo.upsert_markets(markets)

    results = await repo.get_markets(order_by="end_date")
    assert [m.id for m in results] == ["m3", "m1", "m2"]


async def test_get_markets_status_filter(repo: Repository):
    active = _make_market("m1")
    closed = Market(
        id="m2",
        question="Closed market",
        slug="closed",
        condition_id="cond-m2",
        status=MarketStatus.CLOSED,
    )
    await repo.upsert_markets([active, closed])

    results = await repo.get_markets(status=MarketStatus.CLOSED)
    assert [m.id for m in results] == ["m2"]

    results = await repo.get_markets(status="active")
    assert [m.id for m in results] == ["m1"]


# --------------------------------------------------------------------------------------
# Snapshots
# --------------------------------------------------------------------------------------


def _make_snapshot(
    token_id: str, market_id: str, captured_at: datetime, midpoint: float
) -> MarketSnapshot:
    book = OrderBook(
        token_id=token_id,
        bids=[BookLevel(price=midpoint - 0.01, size=100.0)],
        asks=[BookLevel(price=midpoint + 0.01, size=80.0)],
        timestamp=captured_at,
    )
    return MarketSnapshot(
        token_id=token_id,
        market_id=market_id,
        book=book,
        midpoint=midpoint,
        spread=0.02,
        last_trade_price=midpoint,
        captured_at=captured_at,
    )


async def test_insert_snapshot_and_latest_snapshot(repo: Repository):
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=5)

    await repo.insert_snapshot(_make_snapshot("tok1", "m1", t0, 0.50))
    await repo.insert_snapshot(_make_snapshot("tok1", "m1", t1, 0.55))

    latest = await repo.latest_snapshot("tok1")
    assert latest is not None
    assert latest.midpoint == 0.55
    assert latest.captured_at == t1
    assert latest.captured_at.tzinfo is not None
    assert latest.book is not None
    assert latest.book.best_bid == 0.54
    assert latest.book.best_ask == 0.56

    assert await repo.latest_snapshot("unknown-token") is None


async def test_snapshots_since_ordering(repo: Repository):
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=5)
    t2 = t0 + timedelta(minutes=10)

    # inserted out of order
    await repo.insert_snapshot(_make_snapshot("tok1", "m1", t2, 0.60))
    await repo.insert_snapshot(_make_snapshot("tok1", "m1", t0, 0.50))
    await repo.insert_snapshot(_make_snapshot("tok1", "m1", t1, 0.55))

    results = await repo.snapshots_since("tok1", since=t0)
    assert [s.captured_at for s in results] == [t0, t1, t2]
    assert [s.midpoint for s in results] == [0.50, 0.55, 0.60]

    # since filters out earlier points
    results = await repo.snapshots_since("tok1", since=t1)
    assert [s.midpoint for s in results] == [0.55, 0.60]

    # limit is respected
    results = await repo.snapshots_since("tok1", since=t0, limit=1)
    assert [s.midpoint for s in results] == [0.50]


async def test_price_series_prefers_midpoint_falls_back_to_last_trade(repo: Repository):
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    t1 = t0 + timedelta(minutes=1)

    with_midpoint = _make_snapshot("tok1", "m1", t0, 0.42)
    await repo.insert_snapshot(with_midpoint)

    # a snapshot with no book/midpoint, only a last-trade price
    no_midpoint = MarketSnapshot(
        token_id="tok1",
        market_id="m1",
        book=None,
        midpoint=None,
        spread=None,
        last_trade_price=0.47,
        captured_at=t1,
    )
    await repo.insert_snapshot(no_midpoint)

    series = await repo.price_series("tok1")
    assert series == [(t0, 0.42), (t1, 0.47)]

    series_since = await repo.price_series("tok1", since=t1)
    assert series_since == [(t1, 0.47)]

    series_limited = await repo.price_series("tok1", limit=1)
    assert series_limited == [(t0, 0.42)]


# --------------------------------------------------------------------------------------
# Source health
# --------------------------------------------------------------------------------------


async def test_source_health_upsert_get_all(repo: Repository):
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    gamma = SourceHealth(name="gamma", state=ConnState.CONNECTED, last_success=now, latency_ms=42.0)
    ws = SourceHealth(
        name="clob_ws",
        state=ConnState.DEGRADED,
        last_success=None,
        last_error="stale for 45s",
        latency_ms=None,
    )

    await repo.upsert_source_health(gamma)
    await repo.upsert_source_health(ws)

    fetched_gamma = await repo.get_source_health("gamma")
    assert fetched_gamma is not None
    assert fetched_gamma.state == ConnState.CONNECTED
    assert fetched_gamma.last_success == now
    assert fetched_gamma.last_success.tzinfo is not None
    assert fetched_gamma.latency_ms == 42.0
    assert fetched_gamma.last_error is None

    fetched_ws = await repo.get_source_health("clob_ws")
    assert fetched_ws is not None
    assert fetched_ws.state == ConnState.DEGRADED
    assert fetched_ws.last_success is None
    assert fetched_ws.last_error == "stale for 45s"

    all_health = await repo.all_source_health()
    assert {h.name for h in all_health} == {"gamma", "clob_ws"}

    assert await repo.get_source_health("nope") is None

    # upsert updates in place, no duplicate rows
    updated_gamma = SourceHealth(name="gamma", state=ConnState.DISCONNECTED, last_error="timeout")
    await repo.upsert_source_health(updated_gamma)
    all_health = await repo.all_source_health()
    assert len(all_health) == 2
    fetched_gamma = await repo.get_source_health("gamma")
    assert fetched_gamma.state == ConnState.DISCONNECTED
    assert fetched_gamma.last_error == "timeout"


# --------------------------------------------------------------------------------------
# TTLCache
# --------------------------------------------------------------------------------------


class _FakeClock:
    """A controllable monotonic clock for deterministic TTL tests (no real sleeps)."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


async def test_ttl_cache_get_set_and_miss():
    clock = _FakeClock()
    cache = TTLCache(clock=clock)

    assert await cache.get("k") is None
    assert await cache.get("k", default="sentinel") == "sentinel"

    await cache.set("k", "value", ttl_seconds=10)
    assert await cache.get("k") == "value"
    assert await cache.size() == 1


async def test_ttl_cache_expiry_with_fake_clock():
    clock = _FakeClock()
    cache = TTLCache(clock=clock)

    await cache.set("k", "value", ttl_seconds=10)
    clock.advance(9.999)
    assert await cache.get("k") == "value"

    clock.advance(0.001)
    assert await cache.get("k") is None
    # expired entry is evicted on access
    assert await cache.size() == 0


async def test_ttl_cache_delete_and_clear():
    clock = _FakeClock()
    cache = TTLCache(clock=clock)

    await cache.set("a", 1, ttl_seconds=100)
    await cache.set("b", 2, ttl_seconds=100)

    await cache.delete("a")
    assert await cache.get("a") is None
    assert await cache.get("b") == 2

    await cache.clear()
    assert await cache.size() == 0
