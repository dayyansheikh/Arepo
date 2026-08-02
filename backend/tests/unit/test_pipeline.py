"""Ingestion pipeline + cached-mode round-trip (fake clients, in-memory storage)."""
import pytest

from astrolabe.config import Settings
from astrolabe.domain.enums import DataMode
from astrolabe.ingest.pipeline import IngestionPipeline
from astrolabe.service import MarketService
from astrolabe.storage.db import init_db, make_engine, make_sessionmaker


class FakeGamma:
    async def list_events(self, limit, active=True, closed=False):
        return [
            {
                "id": "evt1",
                "tags": [{"label": "Sports"}],
                "markets": [
                    {
                        "id": "m1",
                        "question": "Will it rain on finals day?",
                        "slug": "rain-finals",
                        "conditionId": "0xabc",
                        "outcomes": '["Yes", "No"]',
                        "outcomePrices": '["0.4", "0.6"]',
                        "clobTokenIds": '["t1", "t2"]',
                        "enableOrderBook": True,
                        "active": True,
                        "closed": False,
                        "volumeNum": 123456.0,
                        "orderPriceMinTickSize": 0.001,
                    }
                ],
            }
        ]

    async def aclose(self):
        pass


class FakeClob:
    async def get_book(self, token_id):
        # deliberately unsorted to exercise normalization's best-first sorting
        return {
            "bids": [{"price": "0.38", "size": "50"}, {"price": "0.39", "size": "100"}],
            "asks": [{"price": "0.42", "size": "80"}, {"price": "0.41", "size": "120"}],
            "tick_size": "0.001",
            "timestamp": "1700000000000",
        }

    async def aclose(self):
        pass


@pytest.fixture
async def session_factory():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    yield make_sessionmaker(engine)
    await engine.dispose()


async def test_pipeline_populates_storage_and_cached_mode_reads_it(session_factory):
    pipeline = IngestionPipeline(
        session_factory, settings=Settings(), gamma=FakeGamma(), clob=FakeClob()
    )
    summary = await pipeline.run_once()
    assert summary["markets"] == 1
    assert summary["snapshots"] == 2        # two outcome tokens snapshotted

    # Now the service in CACHED mode should serve the stored market + analytics.
    svc = MarketService(cached_session_factory=session_factory)
    lst = await svc.list_markets(requested_mode="cached")
    assert lst.status.mode == DataMode.CACHED
    assert lst.total == 1
    assert lst.markets[0].question == "Will it rain on finals day?"

    detail = await svc.market_detail("m1", requested_mode="cached")
    assert detail.status.mode == DataMode.CACHED
    yes = next(o for o in detail.market.outcomes if o.name == "Yes")
    # book was stored best-first; midpoint = (0.39 + 0.41)/2
    assert yes.midpoint == pytest.approx(0.40)
    assert yes.spread == pytest.approx(0.02, abs=1e-9)
    await svc.aclose()


async def test_cached_source_empty_falls_back_when_no_data(session_factory):
    # A wired-but-empty cache: cached list is empty, so a live request that fails would fall
    # back to replay. Here we just assert cached mode returns an empty (but valid) response.
    svc = MarketService(cached_session_factory=session_factory)
    resp = await svc.list_markets(requested_mode="cached")
    assert resp.status.mode == DataMode.CACHED
    assert resp.total == 0
    await svc.aclose()
