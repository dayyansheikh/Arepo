"""Production scheduler + retention + storage-health tests (free-production deployment pass).

Covers the master prompt §12 required cases: scheduler idempotency, duplicate tick, delayed/missed
tick recovery, incomplete-scan-cannot-freeze, no fabricated observation, permanent-research kept
from retention, archive-before-delete, and the storage warning threshold. All in-memory.
"""
from datetime import UTC, datetime, timedelta

import pytest

from astrolabe.config import Settings
from astrolabe.discovery import scan_store
from astrolabe.evaluation.research_repository import ResearchRepository
from astrolabe.scheduler import retention as retention_mod
from astrolabe.scheduler import state as sched_state
from astrolabe.scheduler.archive import ArchiveError
from astrolabe.storage.db import Base, make_engine, make_sessionmaker
from astrolabe.storage.migrate import _load_all_models

from .test_cohort_from_scan import _result  # reuse the complete-scan builder

_load_all_models()
NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
async def session():
    engine_ = make_engine("sqlite+aiosqlite:///:memory:")
    async with engine_.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine_)
    async with sm() as s:
        yield s
    await engine_.dispose()


async def _record_scan_at(session, scan_id: str, started_at: datetime, *, complete=True):
    """Record a complete/partial scan then backdate started_at so retention sees it as old."""
    from astrolabe.discovery.snapshot_models import ScanRunRow
    await scan_store.record_scan(session, _result(scan_id, complete=complete))
    row = await session.scalar(
        __import__("sqlalchemy").select(ScanRunRow).where(ScanRunRow.scan_id == scan_id))
    row.started_at = started_at
    await session.commit()
    return row


def _settings(**over):
    base = dict(signal_history_retention_days=2, microstructure_retention_days=2,
                retention_enabled=True, archive_backend="", storage_soft_limit_mb=500,
                storage_warn_ratio=0.8, storage_crit_ratio=0.92)
    base.update(over)
    return Settings(**base)


# --------------------------------------------------------------------------- retention

async def test_retention_protects_cohort_referenced_and_latest(session, monkeypatch):
    monkeypatch.setattr(retention_mod, "get_settings", lambda: _settings())
    # Two OLD complete scans + one recent. Freeze a cohort from one old scan -> it's permanent.
    old = NOW - timedelta(days=10)
    await _record_scan_at(session, "scan-old-ref", old)
    await _record_scan_at(session, "scan-old-unref", old + timedelta(minutes=1))
    await _record_scan_at(session, "scan-recent", NOW)
    from astrolabe.discovery.cohort_from_scan import freeze_cohort_from_scan
    res = await freeze_cohort_from_scan(
        session, cadence="6h", scan_id="scan-old-ref", frozen_at=old)
    assert res["frozen"] is True

    report = await retention_mod.run_retention(session, now=NOW)
    from astrolabe.discovery.snapshot_models import ScanRunRow
    remaining = {r.scan_id for r in (await session.execute(
        __import__("sqlalchemy").select(ScanRunRow))).scalars().all()}
    # Cohort-referenced + latest complete survive; the unreferenced old scan is pruned.
    assert "scan-old-ref" in remaining        # permanent provenance
    assert "scan-recent" in remaining         # latest complete (current product state)
    assert "scan-old-unref" not in remaining  # category-C, prunable
    assert report["pruned_scans"] == 1
    # Permanent research entries are untouched.
    repo = ResearchRepository(session)
    cohort = (await repo.list_cohorts(frozen=True))[0]
    entries = await repo.get_entries(cohort.id)
    assert len(entries) == res["universe_size"] > 0


async def test_retention_idempotent(session, monkeypatch):
    monkeypatch.setattr(retention_mod, "get_settings", lambda: _settings())
    await _record_scan_at(session, "scan-old", NOW - timedelta(days=10))
    await _record_scan_at(session, "scan-recent", NOW)
    first = await retention_mod.run_retention(session, now=NOW)
    second = await retention_mod.run_retention(session, now=NOW)
    assert first["pruned_scans"] == 1
    assert second["pruned_scans"] == 0  # nothing new to prune


async def test_retention_disabled_is_noop(session, monkeypatch):
    monkeypatch.setattr(retention_mod, "get_settings", lambda: _settings(retention_enabled=False))
    await _record_scan_at(session, "scan-old", NOW - timedelta(days=10))
    report = await retention_mod.run_retention(session, now=NOW)
    assert report["enabled"] is False and report["pruned_scans"] == 0


# --------------------------------------------------------------------------- archive-before-delete

async def test_archive_before_delete_local(session, monkeypatch, tmp_path):
    monkeypatch.setattr(retention_mod, "get_settings",
                        lambda: _settings(archive_backend="local", archive_dir=str(tmp_path)))
    await _record_scan_at(session, "scan-old", NOW - timedelta(days=10))
    await _record_scan_at(session, "scan-recent", NOW)
    report = await retention_mod.run_retention(session, now=NOW)
    assert report["pruned_scans"] == 1 and report["archived_scans"] == 1
    # The compressed archive + a checksum manifest exist BEFORE the source was deleted.
    assert (tmp_path / "scan-old.jsonl.gz").exists()
    assert (tmp_path / "scan-old.manifest.json").exists()


def test_local_archive_wraps_filesystem_faults(tmp_path):
    """A raw OS fault (here: archive_dir path is a file) surfaces as ArchiveError, so retention can
    degrade per-scan (retain the source) instead of aborting the whole pass."""
    from astrolabe.scheduler.archive import LocalArchive
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    arch = LocalArchive(str(blocker / "sub"))  # mkdir under a file -> OSError -> ArchiveError
    with pytest.raises(ArchiveError):
        arch.put_scan("scan-x", [{"a": 1}])


async def test_archive_failure_retains_source(session, monkeypatch, tmp_path):
    monkeypatch.setattr(retention_mod, "get_settings",
                        lambda: _settings(archive_backend="local", archive_dir=str(tmp_path)))

    class _Broken:
        def put_scan(self, scan_id, rows):
            raise ArchiveError("simulated archive outage")

    monkeypatch.setattr(retention_mod, "get_archive", lambda *a, **k: _Broken())
    await _record_scan_at(session, "scan-old", NOW - timedelta(days=10))
    await _record_scan_at(session, "scan-recent", NOW)  # so scan-old is not the protected latest
    report = await retention_mod.run_retention(session, now=NOW)
    # Archive failed => source RETAINED, never deleted (archive-before-delete invariant).
    assert report["pruned_scans"] == 0
    assert "scan-old" in report["retained_archive_failures"]
    from astrolabe.discovery.snapshot_models import ScanRunRow
    still = await session.scalar(
        __import__("sqlalchemy").select(ScanRunRow).where(ScanRunRow.scan_id == "scan-old"))
    assert still is not None


# --------------------------------------------------------------------------- storage health

@pytest.mark.parametrize("size_mb,expected", [(100, "ok"), (450, "warn"), (490, "critical")])
async def test_storage_health_levels(session, monkeypatch, size_mb, expected):
    monkeypatch.setattr(retention_mod, "get_settings", lambda: _settings())
    monkeypatch.setattr(retention_mod, "database_size_bytes",
                        lambda *_a, **_k: _async(size_mb * 1024 * 1024))
    health = await retention_mod.storage_health(session)
    assert health["level"] == expected


async def test_table_sizes_is_none_on_sqlite_and_health_tables_optional(session, monkeypatch):
    # table_sizes uses Postgres-only pg_total_relation_size; on SQLite it must degrade to None
    # (never raise), and storage_health only includes the breakdown when asked.
    monkeypatch.setattr(retention_mod, "get_settings", lambda: _settings())
    monkeypatch.setattr(retention_mod, "database_size_bytes",
                        lambda *_a, **_k: _async(100 * 1024 * 1024))
    assert await retention_mod.table_sizes(session) is None
    base = await retention_mod.storage_health(session)
    assert "tables" not in base
    with_tables = await retention_mod.storage_health(session, include_tables=True)
    assert with_tables["tables"] is None  # present (asked for) but None on sqlite


def _async(value):
    async def _c():
        return value
    return _c()


# --------------------------------------------------------------------------- lease / duplicate tick

async def test_lease_serializes_duplicate_ticks(session):
    a = await sched_state.acquire_lease(session, name="t", holder="A", ttl_seconds=600, now=NOW)
    b = await sched_state.acquire_lease(session, name="t", holder="B", ttl_seconds=600, now=NOW)
    assert a is True and b is False           # duplicate tick refused while a live lease is held
    # After the lease expires, a later tick may take over (delayed/missed-tick recovery).
    later = NOW + timedelta(seconds=601)
    c = await sched_state.acquire_lease(session, name="t", holder="C", ttl_seconds=600, now=later)
    assert c is True


# --------------------------------------------------------------------------- causal freeze-due

async def test_freeze_due_only_with_in_period_complete_scan(session, monkeypatch):
    from astrolabe.scheduler import tick as tick_mod
    monkeypatch.setattr(tick_mod, "get_settings",
                        lambda: Settings(research_freeze_cadences="6h"))
    # No complete scan yet in the current 6h period -> not due (never fabricate a freeze).
    period_now = NOW + timedelta(hours=1)      # same 6h period as NOW (12:00 boundary)
    assert await tick_mod._freeze_due_cadences(session, period_now) == []
    # A complete scan taken in-period -> due.
    await _record_scan_at(session, "scan-inperiod", NOW + timedelta(minutes=30))
    assert "6h" in await tick_mod._freeze_due_cadences(session, period_now)


async def test_incomplete_scan_cannot_freeze(session):
    # Only an incomplete scan exists -> no complete scan due, and an explicit freeze refuses.
    await scan_store.record_scan(session, _result("scan-bad", complete=False))
    from astrolabe.discovery.cohort_from_scan import freeze_cohort_from_scan
    res = await freeze_cohort_from_scan(session, cadence="6h", scan_id="scan-bad", frozen_at=NOW)
    assert res["frozen"] is False and res.get("refused") is True
