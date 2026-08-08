"""Pluggable cold archive for category-C high-frequency history (master prompt §8, §14).

Default is prune-only (``archive_backend=""``): the high-frequency scan history is a rolling hot
window whose product value is bounded (trajectory <=6h, market-detail <=200 rows/market), so rows
outside the window can be dropped without losing any product functionality or research integrity.

When an archive backend IS configured, the retention pass writes each pruned scan to the archive
FIRST, verifies it (row count + checksum manifest), and only then deletes the source. An archive
failure raises, so the retention caller RETAINS the source rather than deleting it (archive-before-
delete, never delete-before-archive). Frozen research records are never handed to the archive — the
retention pass excludes any scan referenced by a cohort before this is ever called.

Backends:
    ""      none / prune-only (default)
    local   compressed JSONL + manifest under ``archive_dir`` (genuinely free; used by tests)
    r2      Cloudflare R2 / S3-compatible (credentials from env; see docs). Same manifest contract.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Protocol


class ArchiveError(RuntimeError):
    """Raised when an archive write/verify fails so the caller retains (never deletes) source."""


class ArchiveBackend(Protocol):
    def put_scan(self, scan_id: str, rows: list[dict]) -> dict:
        """Archive one scan's rows; return a verified manifest dict. Raises ArchiveError on fail."""


def _manifest(scan_id: str, rows: list[dict], payload: bytes) -> dict:
    return {
        "scan_id": scan_id,
        "row_count": len(rows),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "format": "jsonl.gz",
    }


def _encode(rows: list[dict]) -> bytes:
    body = "\n".join(json.dumps(r, default=str, sort_keys=True) for r in rows).encode("utf-8")
    return gzip.compress(body)


class LocalArchive:
    """Compressed-JSONL archive on the local filesystem. Genuinely free and fully verifiable."""

    def __init__(self, directory: str):
        self.dir = Path(directory)

    def put_scan(self, scan_id: str, rows: list[dict]) -> dict:
        # Any filesystem fault (permissions, disk full, ...) is surfaced as ArchiveError so the
        # retention caller degrades per-scan (retain this source, continue) instead of aborting the
        # whole pass — archive-before-delete still holds either way (never deletes on a failure).
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            payload = _encode(rows)
            manifest = _manifest(scan_id, rows, payload)
            data_path = self.dir / f"{scan_id}.jsonl.gz"
            man_path = self.dir / f"{scan_id}.manifest.json"
            tmp = data_path.with_suffix(".gz.tmp")
            tmp.write_bytes(payload)
            os.replace(tmp, data_path)
            man_path.write_text(json.dumps(manifest, indent=2))
            # Verify what actually landed on disk before the caller is allowed to delete the source.
            readback = data_path.read_bytes()
            if hashlib.sha256(readback).hexdigest() != manifest["sha256"]:
                raise ArchiveError(f"archive verify failed for {scan_id}: checksum mismatch")
            with gzip.open(data_path, "rt", encoding="utf-8") as fh:
                n = sum(1 for line in fh if line.strip())
            if n != len(rows):
                raise ArchiveError(f"archive verify failed for {scan_id}: {n} rows != {len(rows)}")
            return manifest
        except ArchiveError:
            raise
        except OSError as exc:
            raise ArchiveError(f"archive write failed for {scan_id}: {exc}") from exc


def get_archive(backend: str, *, directory: str = "./archive") -> ArchiveBackend | None:
    """Return the configured backend, or ``None`` for prune-only. Raises for an unknown name."""
    if not backend:
        return None
    if backend == "local":
        return LocalArchive(directory)
    if backend == "r2":  # pragma: no cover - requires external credentials/account
        raise ArchiveError(
            "archive_backend='r2' requires the S3/R2 client and credentials from the environment; "
            "enable it during the external deployment step, not the code-preparation pass. See "
            "docs/PRODUCTION_ROLLBACK.md and docs/FREE_PRODUCTION_DEPLOYMENT.md."
        )
    raise ArchiveError(f"unknown archive_backend {backend!r}")
