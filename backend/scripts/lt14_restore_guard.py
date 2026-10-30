# ruff: noqa: E501
"""LT14 restore guard (LIVE_TESTS_14.md 3 "Inputs" and 6). Research tooling; makes no network request itself.

    python scripts/lt14_restore_guard.py --snapshot-root HOST_SNAPSHOTS [--reserve-gb 1] [--measure-only] <restore_from_archive.py arguments>

Identical in behaviour to ``lt13_restore_guard.py`` (and so ``lt12_restore_guard.py``, imported, not edited): (1) the lag-slot readiness (``live_tests14.restore_readiness``, LT12's rule: the
restore refuses, exit 75, ONLY while a lag-slot capture (the three tail slots of 2026-11-17) is in progress or not yet past its tolerance; a final non-complete capture is MISSING, never
awaited); (2) bytes first (exit 3 "STOP AND ASK THE OWNER" when bytes + reserve exceed the free disk; nothing written); (3) otherwise ``restore_from_archive.main`` unchanged. The restore
of the ENGINE stores (quotes, features, predictions, meta) from the verified release is selected by the caller's arguments (3: "on the host within retention, else restored once"); this guard
adds no selector of its own (ambiguity A9 in reviews/LT14_CODE_NOTE_2026-10-30.md).

Added after the diff re-check (F1, F2; reviews/LT14_CODE_RECHECK_2026-10-30.md), LT14-only:
(a) with no ``--tag`` the guard computes an EXPLICIT tag list from the catalogue (the tags with at least one row matching the selectors) and passes it on, and refuses (exit 3, STOP AND
ASK THE OWNER) when none match (a stale catalogue would otherwise make the restore a silent no-op that exits 0); (b) the bytes must also fit the AREPO data cap
(``AREPO_DATA_CAP_GB``, default 55, as ``scripts/oracle/arepo_pass.sh``): data-dumps used + bytes + reserve <= cap, else exit 3; (c) after a passing restore, every span slot that has a
host ``meta/`` (``--engine-root``) must have a ``rows_ext.csv.gz`` in one of the snapshot roots or the restore tree, else exit 3.
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

from lt12_restore_guard import STOP, _selectors, measure  # noqa: E402

from astrolabe.research_lab import live_tests14 as lt  # noqa: E402
from astrolabe.research_lab import live_tests14_base as t  # noqa: E402


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _opt(argv: list[str], name: str) -> list[str]:
    out, i = [], 0
    while i < len(argv):
        if argv[i] == name and i + 1 < len(argv):
            out.append(argv[i + 1])
            i += 2
        elif argv[i].startswith(name + "="):
            out.append(argv[i].split("=", 1)[1])
            i += 1
        else:
            i += 1
    return out


def matching_tags(argv: list[str], dc=None) -> dict:
    """Tags of the catalogue with at least one row matching the restore's selectors (the same ``matches`` as ``measure``), and the catalogue tags that exist."""
    dc = dc or _load("data_catalogue", os.path.join(HERE, "..", "astrolabe", "research_lab", "data_catalogue.py"))
    a = _selectors(argv)
    cat = a.catalogue or os.path.join(HERE, "..", "..", "docs", "research_lab", "data_catalogue")
    have = sorted(f[:-6] for f in os.listdir(cat) if f.endswith(".jsonl")) if os.path.isdir(cat) else []
    hit = []
    for tag in have:
        if any(dc.matches(r, a.experiment, a.dir, a.since, a.until, None if r.get("granularity") == "group" else a.path_glob) for r in dc.load_jsonl(os.path.join(cat, tag + ".jsonl"))):
            hit.append(tag)
    return {"catalogue_tags": have, "matching_tags": hit}


def tree_bytes(root: str) -> int:
    n = 0
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            try:
                n += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return n


def cap_check(used_bytes: int, nbytes: int, reserve: int, cap_gb: float) -> dict:
    cap = int(cap_gb * 2**30)
    return {"data_cap_bytes": cap, "data_dumps_used_bytes": int(used_bytes), "fits_cap": bool(used_bytes + nbytes + reserve <= cap)}


def coverage_gaps(engine_root, snapshot_roots, spec: dict) -> dict:
    """F1(c): every span slot with a host ``meta/`` needs ``<capture>/rows_ext.csv.gz`` in one of the roots. Returns the slots checked and the gaps."""
    sp = t.span_slots(spec)
    metas = lt._meta_by_slot(Path(engine_root), sp[0], sp[-1])
    gaps, checked = [], 0
    for k in sp:
        m = metas.get(k)
        if m is None:
            continue
        checked += 1
        cid = m["capture_id"]
        if not any((Path(r) / cid / "rows_ext.csv.gz").is_file() for r in snapshot_roots):
            gaps.append({"slot": k, "capture_id": cid})
    return {"slots_with_meta": checked, "gaps": gaps}


def main(argv: list[str] | None = None, *, restore_main=None, dc=None, now: float | None = None, used_bytes: int | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    g = argparse.ArgumentParser(add_help=False)
    g.add_argument("--reserve-gb", type=float, default=1.0)
    g.add_argument("--measure-only", action="store_true")
    g.add_argument("--snapshot-root", action="append", default=None)
    g.add_argument("--engine-root", default=None)
    g.add_argument("--data-dumps-root", default=None)
    g.add_argument("--data-cap-gb", type=float, default=None)
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
    if not _opt(rest, "--tag"):
        mt = matching_tags(rest, dc=dc)
        print(json.dumps({"lt14_restore_tags": mt}, sort_keys=True))
        if not mt["matching_tags"]:
            print("STOP AND ASK THE OWNER: no catalogue row matches the restore's selectors (a stale data catalogue would make the restore a silent no-op; regenerate it first, q0744); nothing was downloaded or written")
            return STOP
        for tg in mt["matching_tags"]:
            rest += ["--tag", tg]
    m = measure(rest, dc=dc)
    reserve = int(ga.reserve_gb * 2**30)
    m["reserve_bytes"] = reserve
    cap_gb = ga.data_cap_gb if ga.data_cap_gb is not None else float(os.environ.get("AREPO_DATA_CAP_GB", "55"))
    used = used_bytes if used_bytes is not None else tree_bytes(ga.data_dumps_root or str(t.ROOT / "data-dumps"))
    m.update(cap_check(used, m["bytes"], reserve, cap_gb))
    m["fits"] = bool(m["rows_without_bytes"] == 0 and not m["catalogues_missing"] and m["bytes"] + reserve <= m["free_bytes"] and m["fits_cap"])
    print(json.dumps({"lt14_restore_measure": m}, sort_keys=True))
    if not m["fits"]:
        why = ("catalogue rows without a byte count or a missing catalogue: the restore cannot be measured" if (m["rows_without_bytes"] or m["catalogues_missing"])
               else "the restore would exceed the AREPO data cap (data-dumps used + bytes + reserve > AREPO_DATA_CAP_GB; collection passes would skip)" if m["bytes"] + reserve <= m["free_bytes"]
               else "the restore would exceed the free disk (with the reserve)")
        print(f"STOP AND ASK THE OWNER: {why} (CLAUDE.md storage stop rule; LIVE_TESTS_14.md 6); nothing was downloaded or written")
        return STOP
    if ga.measure_only:
        return 0
    rc = (restore_main or _load("restore_from_archive", os.path.join(HERE, "restore_from_archive.py")).main)(rest)
    if rc != 0:
        return rc
    dest = os.path.abspath(os.path.expanduser(_selectors(rest).dest))
    cov = coverage_gaps(ga.engine_root or str(t.ENGINE_ROOT), [*roots, os.path.join(dest, "data-dumps", "research_lab", "snapshots")], spec)
    print(json.dumps({"lt14_restore_coverage": cov}, sort_keys=True))
    if cov["gaps"]:
        print(f"STOP AND ASK THE OWNER: {len(cov['gaps'])} span slot(s) with a host meta/ have no rows_ext.csv.gz in the host snapshots or the restore tree (e.g. {cov['gaps'][0]}); "
              "the seal would count their origins as uncovered, which cannot be undone (LIVE_TESTS_14.md 3; re-check F1)")
        return STOP
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
