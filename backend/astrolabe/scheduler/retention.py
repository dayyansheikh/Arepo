"""Category-C retention + storage-health (master prompt §8, §16).

The high-frequency scan/signal history (``discovery_signal_snapshots`` and
``microstructure_snapshots``) is a ROLLING hot window. Rows older than the configured window are
pruned so a single free Postgres never silently fills, while every live product surface keeps enough
history (trajectory needs <=6h; market-detail reads <=200 rows/market).

Hard safety invariants (never weakened):

1. A scan referenced by a frozen research cohort (``research_cohorts.scan_id`` /
   ``research_entries.scan_id``) is PERMANENT provenance and is NEVER pruned.
2. The latest complete scan (current product state) is NEVER pruned, regardless of age.
3. When a cold archive is configured, each scan is archived + verified BEFORE its rows are deleted;
   an archive failure retains the source (archive-before-delete). Default is prune-only.
4. Only category-C tables are touched. Permanent research (A) and user (D) data are never eligible.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..discovery.snapshot_models import ScanRunRow, SignalSnapshotRow
from ..evaluation.research_models import ResearchCohortRow
from ..ingest.microstructure_store import MicrostructureSnapshotRow
from .archive import ArchiveError, get_archive


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


async def database_size_bytes(session: AsyncSession) -> int | None:
    """Best-effort total database size in bytes (Postgres and SQLite). None if unknown."""
    dialect = session.bind.dialect.name if session.bind is not None else ""
    try:
        if dialect == "postgresql":
            return int(await session.scalar(text("SELECT pg_database_size(current_database())")))
        if dialect == "sqlite":
            pages = await session.scalar(text("PRAGMA page_count"))
            page_size = await session.scalar(text("PRAGMA page_size"))
            if pages is not None and page_size is not None:
                return int(pages) * int(page_size)
    except Exception:  # noqa: BLE001 - health must never raise
        return None
    return None


async def table_sizes(session: AsyncSession, *, top: int = 12) -> list[dict] | None:
    """Per-table total size (Postgres only), largest first, for storage diagnostics.

    Read-only. Lets the health snapshot report the REAL per-table byte breakdown so the lean-
    architecture retention/compaction decisions rest on measurement, not estimates. None on
    non-Postgres or error (health must never raise)."""
    dialect = session.bind.dialect.name if session.bind is not None else ""
    if dialect != "postgresql":
        return None
    try:
        rows = (await session.execute(text(
            """
            SELECT relname AS table_name,
                   pg_total_relation_size(c.oid) AS total_bytes,
                   pg_relation_size(c.oid)       AS table_bytes,
                   COALESCE(n_live_tup, 0)       AS live_rows
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
            WHERE c.relkind = 'r' AND n.nspname = 'public'
            ORDER BY pg_total_relation_size(c.oid) DESC
            LIMIT :top
            """
        ), {"top": top})).all()
    except Exception:  # noqa: BLE001 - health must never raise
        return None
    return [
        {
            "table": r.table_name,
            "total_mb": round((r.total_bytes or 0) / 1024 / 1024, 1),
            "table_mb": round((r.table_bytes or 0) / 1024 / 1024, 1),
            "index_mb": round(((r.total_bytes or 0) - (r.table_bytes or 0)) / 1024 / 1024, 1),
            "live_rows": int(r.live_rows or 0),
        }
        for r in rows
    ]


async def storage_health(session: AsyncSession, *, include_tables: bool = False) -> dict:
    """Storage-size + quota-warning snapshot. Never raises (health path).

    ``include_tables`` adds the per-table size breakdown (Postgres) for storage diagnostics."""
    settings = get_settings()
    size = await database_size_bytes(session)
    limit = settings.storage_soft_limit_mb * 1024 * 1024
    ratio = (size / limit) if (size and limit) else None
    level = "unknown"
    if ratio is not None:
        if ratio >= settings.storage_crit_ratio:
            level = "critical"
        elif ratio >= settings.storage_warn_ratio:
            level = "warn"
        else:
            level = "ok"
    out = {
        "size_bytes": size,
        "size_mb": round(size / 1024 / 1024, 1) if size else None,
        "soft_limit_mb": settings.storage_soft_limit_mb,
        "used_ratio": round(ratio, 3) if ratio is not None else None,
        "level": level,
        "warn_ratio": settings.storage_warn_ratio,
        "crit_ratio": settings.storage_crit_ratio,
    }
    if include_tables:
        out["tables"] = await table_sizes(session)
    return out


async def _cohort_referenced_scan_ids(session: AsyncSession) -> set[str]:
    """scan_ids that any frozen cohort references — permanent provenance, never pruned.

    A cohort's frozen entries carry their own copied values, so the linkage to the source scan lives
    on ``research_cohorts.scan_id``; protecting those scans preserves the ability to reconstruct
    exactly what universe each cohort was frozen from.
    """
    rows = await session.execute(
        select(ResearchCohortRow.scan_id).where(ResearchCohortRow.scan_id.is_not(None)).distinct()
    )
    return {r[0] for r in rows if r[0]}


def _row_to_dict(row) -> dict:
    return {c.key: getattr(row, c.key) for c in inspect(row).mapper.column_attrs}


async def run_retention(
    session: AsyncSession, *, now: datetime | None = None, commit: bool = True
) -> dict:
    """Prune category-C history older than the hot window. Idempotent; returns a report.

    Honours all four safety invariants above. Safe to run repeatedly (a second run is a no-op).
    """
    settings = get_settings()
    if not settings.retention_enabled:
        return {"enabled": False, "pruned_scans": 0, "pruned_signal_rows": 0,
                "pruned_microstructure_rows": 0}
    now = _utc(now) or datetime.now(UTC)
    archive = get_archive(settings.archive_backend, directory=settings.archive_dir)

    signal_cutoff = now - timedelta(days=settings.signal_history_retention_days)
    micro_cutoff = now - timedelta(days=settings.microstructure_retention_days)

    protected = await _cohort_referenced_scan_ids(session)
    # Never prune the latest complete scan (current product state), whatever its age.
    latest_complete = await session.scalar(
        select(ScanRunRow.scan_id)
        .where(ScanRunRow.pagination_complete.is_(True))
        .order_by(ScanRunRow.started_at.desc())
        .limit(1)
    )
    if latest_complete:
        protected.add(latest_complete)

    # Candidate scans: older than the window and not protected.
    candidates = (await session.execute(
        select(ScanRunRow).where(ScanRunRow.started_at < signal_cutoff)
    )).scalars().all()

    pruned_scans = 0
    pruned_signal_rows = 0
    archived: list[dict] = []
    retained_archive_failures: list[str] = []
    for scan in candidates:
        if scan.scan_id in protected:
            continue
        rows = (await session.execute(
            select(SignalSnapshotRow).where(SignalSnapshotRow.scan_id == scan.scan_id)
        )).scalars().all()
        if archive is not None and rows:
            try:
                manifest = archive.put_scan(scan.scan_id, [_row_to_dict(r) for r in rows])
                archived.append(manifest)
            except ArchiveError:
                # Archive-before-delete: a failed archive RETAINS the source (never deletes).
                retained_archive_failures.append(scan.scan_id)
                continue
        n = await session.execute(
            delete(SignalSnapshotRow).where(SignalSnapshotRow.scan_id == scan.scan_id)
            .execution_options(synchronize_session=False)
        )
        pruned_signal_rows += n.rowcount or len(rows)
        await session.execute(
            delete(ScanRunRow).where(ScanRunRow.id == scan.id)
            .execution_options(synchronize_session=False)
        )
        pruned_scans += 1

    micro_deleted = await session.execute(
        delete(MicrostructureSnapshotRow)
        .where(MicrostructureSnapshotRow.captured_at < micro_cutoff)
        .execution_options(synchronize_session=False)
    )
    pruned_micro = micro_deleted.rowcount or 0

    if commit:
        await session.commit()

    report = {
        "enabled": True,
        "signal_retention_days": settings.signal_history_retention_days,
        "microstructure_retention_days": settings.microstructure_retention_days,
        "pruned_scans": pruned_scans,
        "pruned_signal_rows": pruned_signal_rows,
        "pruned_microstructure_rows": pruned_micro,
        "protected_scan_ids": len(protected),
        "archive_backend": settings.archive_backend or None,
        "archived_scans": len(archived),
        "retained_archive_failures": retained_archive_failures,
    }
    return report
