"""The scan job persists its discovered universe to MarketRow so Explore has a GENUINE offline
fallback (the latest complete scan in the DB) instead of ever showing the demo replay dataset.
"""
from __future__ import annotations

import pytest

from astrolabe.config import Settings
from astrolabe.discovery import refresh_cli
from astrolabe.discovery.scan_service import CompleteScanService, ScanResult
from astrolabe.domain.models import utcnow
from astrolabe.replay.player import default_player
from astrolabe.storage.db import Base, make_engine, make_sessionmaker
from astrolabe.storage.repository import Repository


@pytest.fixture
async def session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        yield s
    await engine.dispose()


def _scan_result(markets, *, status="ok") -> ScanResult:
    now = utcnow()
    return ScanResult(
        scan_id="scan-test",
        started_at=now,
        finished_at=now,
        duration_seconds=1.0,
        discovery=None,
        funnel=None,
        status=status,
        eligible_markets=list(markets),
    )


async def test_complete_scan_persists_universe_to_market_cache(session, monkeypatch):
    monkeypatch.setattr(refresh_cli, "get_settings", lambda: Settings(scan_lease_seconds=600))
    markets = default_player().markets()
    assert markets

    async def _fake_scan(self, **_kw):
        return _scan_result(markets, status="ok")

    monkeypatch.setattr(CompleteScanService, "run_scan", _fake_scan)
    monkeypatch.setattr(CompleteScanService, "result_summary", lambda self, result: {})
    monkeypatch.setattr(
        refresh_cli.scan_store, "record_scan",
        lambda session, result: _async_none(),
    )

    out = await refresh_cli.run_refresh(session, None, None, holder="h1")
    assert out["ran"] is True
    assert out["markets_cached"] == len(markets)

    cached = await Repository(session).get_markets(limit=1000)
    assert {m.id for m in cached} == {m.id for m in markets}


async def test_incomplete_scan_does_not_overwrite_market_cache(session, monkeypatch):
    monkeypatch.setattr(refresh_cli, "get_settings", lambda: Settings(scan_lease_seconds=600))
    markets = default_player().markets()

    async def _fake_scan(self, **_kw):
        return _scan_result(markets, status="incomplete")  # truncated universe

    monkeypatch.setattr(CompleteScanService, "run_scan", _fake_scan)
    monkeypatch.setattr(CompleteScanService, "result_summary", lambda self, result: {})
    monkeypatch.setattr(
        refresh_cli.scan_store, "record_scan",
        lambda session, result: _async_none(),
    )

    out = await refresh_cli.run_refresh(session, None, None, holder="h1")
    assert out["markets_cached"] == 0
    # A partial scan must never clobber the cached complete universe.
    assert await Repository(session).get_markets(limit=1000) == []


async def _async_none():
    return None
