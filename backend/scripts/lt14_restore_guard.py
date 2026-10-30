# ruff: noqa: E501
"""LT14 restore guard (LIVE_TESTS_14.md 3 "Inputs" and 6). Research tooling; makes no network request itself.

    python scripts/lt14_restore_guard.py --snapshot-root HOST_SNAPSHOTS [--reserve-gb 1] [--measure-only] <restore_from_archive.py arguments>

Identical in behaviour to ``lt13_restore_guard.py`` (and so ``lt12_restore_guard.py``, imported, not edited): (1) the lag-slot readiness (``live_tests14.restore_readiness``, LT12's rule: the
restore refuses, exit 75, ONLY while a lag-slot capture (the three tail slots of 2026-11-17) is in progress or not yet past its tolerance; a final non-complete capture is MISSING, never
awaited); (2) bytes first (exit 3 "STOP AND ASK THE OWNER" when bytes + reserve exceed the free disk; nothing written); (3) otherwise ``restore_from_archive.main`` unchanged. The restore
of the ENGINE stores (quotes, features, predictions, meta) from the verified release is selected by the caller's arguments (3: "on the host within retention, else restored once"); this guard
adds no selector of its own (ambiguity A9 in reviews/LT14_CODE_NOTE_2026-10-30.md).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, str(Path(HERE).parent))
sys.path.insert(0, HERE)

from lt12_restore_guard import STOP, measure  # noqa: E402

from astrolabe.research_lab import live_tests14 as lt  # noqa: E402
from astrolabe.research_lab import live_tests14_base as t  # noqa: E402


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None, *, restore_main=None, dc=None, now: float | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    g = argparse.ArgumentParser(add_help=False)
    g.add_argument("--reserve-gb", type=float, default=1.0)
    g.add_argument("--measure-only", action="store_true")
    g.add_argument("--snapshot-root", action="append", default=None)
    ga, rest = g.parse_known_args(argv)
    if "--list" in rest:
        return (restore_main or _load("restore_from_archive", os.path.join(HERE, "restore_from_archive.py")).main)(rest)
    spec = t.load_spec()
    roots = ga.snapshot_root or [str(t.SNAPSHOT_ROOT)]
    rd = lt.restore_readiness(roots, spec, time.time() if now is None else now)
    print(json.dumps({"lt14_restore_readiness": rd}, sort_keys=True, default=str))
    if rd["refuse"]:
        print(f"not now: lag-slot capture(s) still in progress or not yet past the slot tolerance: {rd['refusing_slots']} (LIVE_TESTS_14.md 6)")
        return t.TEMPFAIL
    m = measure(rest, dc=dc)
    reserve = int(ga.reserve_gb * 2**30)
    m["reserve_bytes"] = reserve
    m["fits"] = bool(m["rows_without_bytes"] == 0 and not m["catalogues_missing"] and m["bytes"] + reserve <= m["free_bytes"])
    print(json.dumps({"lt14_restore_measure": m}, sort_keys=True))
    if not m["fits"]:
        why = ("catalogue rows without a byte count or a missing catalogue: the restore cannot be measured" if (m["rows_without_bytes"] or m["catalogues_missing"])
               else "the restore would exceed the free disk (with the reserve)")
        print(f"STOP AND ASK THE OWNER: {why} (CLAUDE.md storage stop rule; LIVE_TESTS_14.md 6); nothing was downloaded or written")
        return STOP
    if ga.measure_only:
        return 0
    return (restore_main or _load("restore_from_archive", os.path.join(HERE, "restore_from_archive.py")).main)(rest)


if __name__ == "__main__":
    raise SystemExit(main())
