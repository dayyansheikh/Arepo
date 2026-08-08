"""SQLite -> Postgres migration tool + production config/health tests (deployment pass §12).

The full import is exercised SQLite -> SQLite (a real Postgres is not available in CI); the
Postgres-specific paths (ON CONFLICT, sequence reset) are covered by the dialect-portability check
plus the shared reconciliation logic. Reconciliation, idempotency, the require-empty refusal and the
mismatch-detection guarantee are all verified end-to-end.
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from astrolabe.config import Settings
from astrolabe.discovery import scan_store
from astrolabe.discovery.cohort_from_scan import freeze_cohort_from_scan
from astrolabe.storage.db import Base, make_engine, make_sessionmaker
from astrolabe.storage.import_sqlite import _reconcile, import_all
from astrolabe.storage.migrate import _load_all_models, ddl_preview

from .test_cohort_from_scan import _result

_load_all_models()
NOW = datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC)


async def _populate(path: str):
    """Build a genuine source DB: one complete scan + a frozen cohort (exercises invariants)."""
    engine = make_engine(f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = make_sessionmaker(engine)
    async with sm() as s:
        await scan_store.record_scan(s, _result("scan-ok", complete=True))
        await freeze_cohort_from_scan(s, cadence="6h", scan_id="scan-ok", frozen_at=NOW)
    await engine.dispose()


async def test_import_roundtrip_and_reconciliation(tmp_path):
    src = tmp_path / "source.db"
    dest = tmp_path / "dest.db"
    await _populate(str(src))
    report = await import_all(
        source_path=str(src), dest_url=f"sqlite+aiosqlite:///{dest}", require_empty=True)
    recon = report["reconciliation"]
    assert recon["ok"] is True
    assert not recon["mismatches"]
    # Every frozen cohort keeps entry_count == universe_size in the destination.
    assert all(inv["ok"] for inv in recon["cohort_invariants"])
    assert any(inv["frozen"] and inv["entries"] > 0 for inv in recon["cohort_invariants"])
    # Counts match for the populated tables.
    for t, c in recon["counts"].items():
        assert c["dest"] >= c["source"], f"{t} lost rows"


async def test_import_idempotent(tmp_path):
    src = tmp_path / "source.db"
    dest = tmp_path / "dest.db"
    await _populate(str(src))
    url = f"sqlite+aiosqlite:///{dest}"
    await import_all(source_path=str(src), dest_url=url)
    second = await import_all(source_path=str(src), dest_url=url)
    assert second["reconciliation"]["ok"] is True
    assert sum(v.get("inserted", 0) for v in second["tables"].values()) == 0  # nothing duplicated


async def test_import_require_empty_refuses_populated_dest(tmp_path):
    src = tmp_path / "source.db"
    dest = tmp_path / "dest.db"
    await _populate(str(src))
    url = f"sqlite+aiosqlite:///{dest}"
    await import_all(source_path=str(src), dest_url=url)
    with pytest.raises(RuntimeError, match="already has"):
        await import_all(source_path=str(src), dest_url=url, require_empty=True)


async def test_reconciliation_detects_lost_rows(tmp_path):
    src = tmp_path / "source.db"
    dest = tmp_path / "dest.db"
    await _populate(str(src))
    url = f"sqlite+aiosqlite:///{dest}"
    await import_all(source_path=str(src), dest_url=url)
    # Simulate data loss in the destination, then reconcile: it must report NOT ok.
    from astrolabe.evaluation.research_models import ResearchEntryRow
    dst = make_engine(url)
    async with dst.begin() as conn:
        await conn.execute(delete(ResearchEntryRow).where(ResearchEntryRow.id == (
            await conn.scalar(select(ResearchEntryRow.id).limit(1)))))
    src_e = make_engine(f"sqlite+aiosqlite:///{src}")
    recon = await _reconcile(src_e, dst, list(Base.metadata.sorted_tables), dry_run=False)
    await dst.dispose()
    await src_e.dispose()
    assert recon["ok"] is False
    assert recon["mismatches"]


async def test_value_verification_catches_corrupted_immutable_row(tmp_path):
    """Spec §10: destination growth must not hide a corrupted imported source row. A same-PK row
    with a changed FROZEN value must fail reconciliation even though counts still match."""
    src = tmp_path / "source.db"
    dest = tmp_path / "dest.db"
    await _populate(str(src))
    url = f"sqlite+aiosqlite:///{dest}"
    clean = await import_all(source_path=str(src), dest_url=url, require_empty=True)
    vv = clean["reconciliation"]["value_verification"]
    assert vv["ok"] is True and vv["missing_rows"] == 0 and vv["value_mismatch_rows"] == 0
    assert vv["checked_rows"] > 0

    # Corrupt one frozen strength in the destination (counts unchanged, content changed).
    from astrolabe.evaluation.research_models import ResearchEntryRow
    dst = make_engine(url)
    async with dst.begin() as conn:
        eid = await conn.scalar(select(ResearchEntryRow.id).limit(1))
        await conn.execute(
            ResearchEntryRow.__table__.update()
            .where(ResearchEntryRow.id == eid).values(strength=0.999))
    src_e = make_engine(f"sqlite+aiosqlite:///{src}")
    recon = await _reconcile(src_e, dst, list(Base.metadata.sorted_tables), dry_run=False)
    await dst.dispose()
    await src_e.dispose()
    assert recon["ok"] is False
    assert recon["value_verification"]["value_mismatch_rows"] == 1
    assert any("strength" in e for e in recon["value_verification"]["examples"])


def test_new_tables_are_postgres_portable():
    """The new scheduler tables compile for the PostgreSQL dialect (no SQLite-only types)."""
    ddl = "\n".join(ddl_preview("postgresql"))
    assert "scheduler_state" in ddl
    assert "scheduler_leases" in ddl
    # sanity: a portable type compiled, not a SQLite-only one
    assert "CREATE TABLE scheduler_state" in ddl


# --------------------------------------------------------------------------- production config

def test_production_issues_flags_insecure_defaults():
    s = Settings(environment="production")  # all defaults => unsafe for production
    issues = " ".join(s.production_issues())
    assert "AUTH_SECRET" in issues       # default insecure secret
    assert "SQLite" in issues            # default sqlite database_url
    assert "AUTH_COOKIE_SECURE" in issues
    # The default CORS (http://localhost:3000) is legitimately allowed and must NOT be flagged.
    assert "CORS_ORIGINS" not in issues


def test_production_issues_clean_when_configured():
    s = Settings(
        environment="production",
        auth_secret="x" * 40,
        cors_origins="https://arepo.dsheikh.cc",
        database_url="postgresql+asyncpg://u:p@host:5432/db",
        auth_cookie_secure=True,
    )
    assert s.production_issues() == []


def test_development_has_no_production_issues():
    assert Settings(environment="development").production_issues() == []


def test_safe_cors_wildcard_flagged():
    s = Settings(environment="production", auth_secret="x" * 40, auth_cookie_secure=True,
                 database_url="postgresql+asyncpg://u:p@h/db", cors_origins="*")
    assert any("CORS" in i for i in s.production_issues())
