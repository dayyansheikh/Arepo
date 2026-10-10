"""Exact-byte transparent compression of one closed data-dumps directory.

Same method as D099/D105/D109/D113.

Procedure (fails closed at every step; nothing logical is deleted):
1. Manifest the source: every file's relative path, sha256, size, mode, uid, gid and
   mtime_ns, and every directory's mode and mtime_ns.
2. ``ditto --hfsCompression`` the source to a sibling candidate directory (macOS native
   filesystem compression).
3. Verify that the candidate manifest equals the source manifest exactly.
4. Swap atomically: source -> rollback, candidate -> source (same volume renames).
5. Re-verify the manifest at the original path. If it differs, restore the rollback and fail.
6. Only then remove the rollback, which is the now-redundant uncompressed physical copy.
7. Write a JSON record (manifest hash, allocated and free bytes before/after) to --record.

Usage: python scripts/storage_compress_exact.py <data-dumps/dir> --record <out.json> [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

PROTECTED_NAMES = ("data-dumps",)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(root: Path) -> dict:
    entries = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        d = Path(dirpath)
        st = d.lstat()
        entries[str(d.relative_to(root)) + "/"] = ["dir", st.st_mode, st.st_mtime_ns]
        for name in sorted(filenames):
            p = d / name
            st = p.lstat()
            if not p.is_file() or p.is_symlink():
                raise SystemExit(f"refusing: non-regular file {p}")
            entries[str(p.relative_to(root))] = [
                _sha256(p), st.st_size, st.st_mode, st.st_uid, st.st_gid, st.st_mtime_ns,
            ]
    return entries


def allocated_bytes(root: Path) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            total += (Path(dirpath) / name).lstat().st_blocks * 512
    return total


def digest(m: dict) -> str:
    return hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--record", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    src = Path(a.source).resolve()
    if src.parent.name not in PROTECTED_NAMES or not src.is_dir() or src.is_symlink():
        raise SystemExit("source must be a real directory directly under data-dumps/")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    candidate = src.parent / f".arepo-compression-candidate-{src.name}-{stamp}"
    rollback = src.parent / f".arepo-uncompressed-rollback-{src.name}-{stamp}"
    if candidate.exists() or rollback.exists():
        raise SystemExit("candidate/rollback path already exists")

    rec: dict = {"version": "arepo-local-transparent-compression-v2", "source": str(src),
                 "started_at": datetime.now(UTC).isoformat(),
                 "free_before_bytes": shutil.disk_usage(src).free,
                 "allocated_before_bytes": allocated_bytes(src)}
    before = manifest(src)
    rec["files_and_dirs"] = len(before)
    rec["logical_bytes"] = sum(v[1] for v in before.values() if v[0] != "dir")
    rec["manifest_sha256"] = digest(before)
    if a.dry_run:
        rec["state"] = "dry_run"
        Path(a.record).write_text(json.dumps(rec, indent=1))
        print(json.dumps(rec))
        return 0

    subprocess.run(["ditto", "--hfsCompression", str(src), str(candidate)], check=True)
    if manifest(candidate) != before:
        shutil.rmtree(candidate)
        raise SystemExit("candidate manifest differs; candidate removed, source untouched")
    rec["allocated_compressed_bytes"] = allocated_bytes(candidate)

    os.rename(src, rollback)
    os.rename(candidate, src)
    after = manifest(src)
    if after != before:
        os.rename(src, candidate)
        os.rename(rollback, src)
        raise SystemExit("post-swap manifest differs; original restored, candidate kept")
    # Renames change only the parent's mtime; the source tree itself was verified identical.
    shutil.rmtree(rollback)

    rec.update({"finished_at": datetime.now(UTC).isoformat(), "state": "complete",
                "all_content_hashes_sizes_modes_owners_mtimes_equal": True,
                "original_paths_preserved": True, "logical_records_deleted": 0,
                "free_after_bytes": shutil.disk_usage(src).free})
    rec["observed_free_delta_bytes"] = rec["free_after_bytes"] - rec["free_before_bytes"]
    Path(a.record).write_text(json.dumps(rec, indent=1))
    keys = ("source", "allocated_before_bytes", "allocated_compressed_bytes",
            "observed_free_delta_bytes", "state")
    print(json.dumps({k: rec[k] for k in keys}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
