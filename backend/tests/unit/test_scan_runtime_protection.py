"""Complete-scan runtime protection (hosted-runner slowness): hard timeout + clean lease release.

A GitHub Actions run of the complete scan was cancelled at the 20-min workflow timeout mid-scan. The
app must instead abort a slow scan CLEANLY — release its lease and record nothing — so the runner
never SIGKILLs it with a dangling lease, and a partial scan never becomes product state.
"""
import asyncio

import pytest

from astrolabe.clients.errors import UpstreamUnavailable
from astrolabe.config import Settings
from astrolabe.discovery import refresh_cli, scan_store
from astrolabe.discovery.scan_service import CompleteScanService
from astrolabe.storage.db import Base, make_engine, make_sessionmaker


@pytest.fixture
async def session():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        yield s
    await engine.dispose()


async def test_scan_timeout_aborts_clean_releases_lease_records_nothing(session, monkeypatch):
    monkeypatch.setattr(
        refresh_cli, "get_settings",
        lambda: Settings(scan_timeout_seconds=1, scan_lease_seconds=600),
    )

    async def _slow(self, **_kw):  # never finishes within the timeout
        await asyncio.sleep(30)

    monkeypatch.setattr(CompleteScanService, "run_scan", _slow)

    with pytest.raises(UpstreamUnavailable, match="aborted incomplete"):
        await refresh_cli.run_refresh(session, None, None, holder="holder-1")

    # Lease was released in the finally -> a different holder can immediately acquire.
    assert await scan_store.acquire_lock(session, holder="holder-2") is True
    # Nothing was recorded: a timed-out (incomplete) scan never becomes product state.
    assert await scan_store.latest_scan(session) is None


def test_lease_ttls_exceed_scan_timeout_invariant():
    """The ordering invariant that prevents overlap + lets the app abort before the runner kills it:
    scan_timeout_seconds < scan_lease_seconds and < tick_lease_seconds (both defaults)."""
    s = Settings()
    assert s.scan_timeout_seconds < s.scan_lease_seconds
    assert s.scan_timeout_seconds < s.tick_lease_seconds
