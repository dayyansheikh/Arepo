# ruff: noqa: E501
"""LT12 q0710 restore guard (LIVE_TESTS_12.md 7). Research tooling; makes no network request itself.

    python scripts/lt12_restore_guard.py --snapshot-root HOST_SNAPSHOTS [--reserve-gb 1] [--measure-only] <restore_from_archive.py arguments>

1. **Lag-slot readiness (final verification fix 2).** ``live_tests12.restore_readiness`` on the host's snapshot roots: the restore refuses (exit 75, the
   queue's "not now") ONLY while a lag-slot capture is still in progress (started, not yet in a final state) or a lag slot is not yet past its tolerance; a
   capture in a final non-complete state, one still open one slot after its start, or no capture past the tolerance is MISSING (counted by the seal, never
   substituted), so the one-shot restore never waits on a capture that will not complete.
2. **Bytes first (7; CLAUDE.md storage stop rule).** The bytes the restore would write, from the data catalogue rows that the restore's own selectors match (a
   group row counts in full: an upper bound), against the free disk at ``--dest``. A selected row without a byte count, a missing catalogue, or ``bytes +
   reserve`` above the free disk: prints the measure and exits 3 "STOP AND ASK THE OWNER"; nothing is downloaded or written.
3. Otherwise runs ``restore_from_archive.main`` with the remaining arguments unchanged (byte-for-byte restore, sha256 proof) and returns its exit code.

``restore_from_archive.py`` (shared) is NOT modified; this wrapper is new code (the same byte measure as LT11's guard, which lives on LT11's branch).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, str(Path(HERE).parent))

from astrolabe.research_lab import live_tests12 as lt  # noqa: E402

STOP = 3


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _selectors(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--tag", action="append")
    ap.add_argument("--experiment")
    ap.add_argument("--dir", action="append")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--path-glob", action="append")
    ap.add_argument("--dest", required=True)
    ap.add_argument("--catalogue", default=None)
    a, _ = ap.parse_known_args(argv)
    return a


def measure(argv: list[str], dc=None) -> dict:
    """Bytes the restore would write, from the catalogue rows the restore's selectors match (group rows in full: an upper bound)."""
    dc = dc or _load("data_catalogue", os.path.join(HERE, "..", "astrolabe", "research_lab", "data_catalogue.py"))
    a = _selectors(argv)
    cat = a.catalogue or os.path.join(HERE, "..", "..", "docs", "research_lab", "data_catalogue")
    tags = a.tag or sorted(f[:-6] for f in os.listdir(cat) if f.endswith(".jsonl"))
    total, rows, unknown, missing_cat = 0, 0, 0, []
    for tag in tags:
        p = os.path.join(cat, tag + ".jsonl")
        if not os.path.exists(p):
            missing_cat.append(tag)
            continue
        for row in dc.load_jsonl(p):
            if not dc.matches(row, a.experiment, a.dir, a.since, a.until, None if row.get("granularity") == "group" else a.path_glob):
                continue
            rows += 1
            nb = row.get("bytes")
            if isinstance(nb, (int, float)) and nb >= 0:
                total += int(nb)
            else:
                unknown += 1
    dest = os.path.abspath(os.path.expanduser(a.dest))
    probe = dest
    while not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    free = shutil.disk_usage(probe).free
    return {"selected_rows": rows, "bytes": total, "rows_without_bytes": unknown, "catalogues_missing": missing_cat, "dest": dest, "free_bytes_at": probe, "free_bytes": int(free)}


def main(argv: list[str] | None = None, *, restore_main=None, dc=None, now: float | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    g = argparse.ArgumentParser(add_help=False)
    g.add_argument("--reserve-gb", type=float, default=1.0)
    g.add_argument("--measure-only", action="store_true")
    g.add_argument("--snapshot-root", action="append", default=None, help="repeatable: the host's snapshot roots (lag-slot readiness)")
    ga, rest = g.parse_known_args(argv)
    if "--list" in rest:
        return (restore_main or _load("restore_from_archive", os.path.join(HERE, "restore_from_archive.py")).main)(rest)
    spec = lt.load_spec(sha=None)
    roots = ga.snapshot_root or [str(lt.SNAPSHOT_ROOT)]
    rd = lt.restore_readiness(roots, spec, time.time() if now is None else now)
    print(json.dumps({"lt12_restore_readiness": rd}, sort_keys=True, default=str))
    if rd["refuse"]:
        print(f"not now: lag-slot capture(s) still in progress or not yet past the slot tolerance: {rd['refusing_slots']} (LIVE_TESTS_12.md 7)")
        return lt.TEMPFAIL
    m = measure(rest, dc=dc)
    reserve = int(ga.reserve_gb * 2**30)
    m["reserve_bytes"] = reserve
    m["fits"] = bool(m["rows_without_bytes"] == 0 and not m["catalogues_missing"] and m["bytes"] + reserve <= m["free_bytes"])
    print(json.dumps({"lt12_restore_measure": m}, sort_keys=True))
    if not m["fits"]:
        why = ("catalogue rows without a byte count or a missing catalogue: the restore cannot be measured" if (m["rows_without_bytes"] or m["catalogues_missing"])
               else "the restore would exceed the free disk (with the reserve)")
        print(f"STOP AND ASK THE OWNER: {why} (CLAUDE.md storage stop rule; LIVE_TESTS_12.md 7); nothing was downloaded or written")
        return STOP
    if ga.measure_only:
        return 0
    return (restore_main or _load("restore_from_archive", os.path.join(HERE, "restore_from_archive.py")).main)(rest)


if __name__ == "__main__":
    raise SystemExit(main())
