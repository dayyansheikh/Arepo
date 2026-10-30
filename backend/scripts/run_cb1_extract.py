# ruff: noqa: E501
"""CB1 snapshot extractor (docs/research_lab/CREATIVE_BATCH_1.md §2.11). Read-only on snapshots and
sweeps; writes only under --extract-root. Not a trial kind (no trials logged). Always exits 0 in
--all-new mode (the in-pass step must never fail the pass); backfill fails loudly on an archived file.

    python scripts/run_cb1_extract.py --all-new --rps 2 --max-requests 300
    python scripts/run_cb1_extract.py --backfill-from 2026-10-11T12:00Z --budget-min 90
    python scripts/run_cb1_extract.py --backfill-from 2026-10-11T12:00Z --tables ladder_candidates --budget-min 150 --disk-cap-gb 0.25   # CB2 tables only (q0041)
    python scripts/run_cb1_extract.py --freeze-list dev --until 2026-10-17T00:00Z
    python scripts/run_cb1_extract.py --freeze-list rep --from 2026-10-19T00:00Z --until 2026-11-09T00:00Z
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def _iso(s: str) -> str:
    """Accept '2026-10-11T12:00Z' / '...:00:00Z' / '...+00:00'; return '%Y-%m-%dT%H:%M:%SZ'."""
    from datetime import UTC, datetime

    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cb2_only(a, cb, cb2_root) -> int:
    """CB2 tables only (q0041 backfill, or a manual all-new run). Backfill fails loudly on an archived file."""
    import time

    tables = tuple(t.strip() for t in a.tables.split(",") if t.strip())
    backfill = a.backfill_from is not None
    budget_min = a.budget_min if a.budget_min is not None else (90.0 if backfill else 7.0)
    since = _iso(a.backfill_from) if backfill else cb.T2_DEV_START
    try:
        summ = cb.run_cb2_tables(
            a.snapshot_root, a.sweep_root, cb2_root, tables=tables, mode="backfill" if backfill else "all-new",
            since=since, deadline=time.monotonic() + budget_min * 60.0, disk_cap_gb=a.disk_cap_gb,
            data_dumps=a.data_dumps, data_dumps_max_gb=a.data_dumps_max_gb)
    except cb.ExtractLocked:
        print(json.dumps({"cb2_extract": cb.EXTRACTOR_VERSION, "skipped": "another extractor holds the lock"}))
        return 0
    except Exception as exc:
        print(json.dumps({"cb2_extract": cb.EXTRACTOR_VERSION, "error": f"{type(exc).__name__}: {exc}"[:300]}))
        return 1 if backfill else 0
    print(json.dumps({"cb2_extract": cb.EXTRACTOR_VERSION, **summ}))
    if backfill and summ.get("stopped") == "refused_data_dumps_over_cap":
        return 1  # non-zero: a refusal must not count as a successful repeat run (freeze-check fix 2)
    return 0


def main() -> int:
    from astrolabe.research_lab import creative_batch1 as cb

    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all-new", action="store_true", help="extract complete captures not yet extracted")
    g.add_argument("--backfill-from", help="ISO; extract all complete captures at/after it (oldest first)")
    g.add_argument("--freeze-list", choices=["dev", "rep"], help="write the frozen capture-id list + sha256")
    ap.add_argument("--until", help="--freeze-list: exclusive end (ISO)")
    ap.add_argument("--from", dest="from_utc", help="--freeze-list: start (dev default 2026-10-11T12:00Z)")
    ap.add_argument("--rps", type=float, default=2.0)
    ap.add_argument("--max-requests", type=int, default=300)
    ap.add_argument("--budget-min", type=float, default=None,
                    help="wall-clock self-limit (default 7 min for --all-new, 90 for --backfill-from)")
    ap.add_argument("--snapshot-root", type=Path, default=cb.SNAPSHOT_ROOT)
    ap.add_argument("--sweep-root", type=Path, default=cb.SWEEP_ROOT)
    ap.add_argument("--extract-root", type=Path, default=cb.EXTRACT_ROOT)
    ap.add_argument("--cb2-root", type=Path, default=None,
                    help="CB2 extract root (default: cb2_extract beside --extract-root); the pass step writes the "
                         "CB2 tables there")
    ap.add_argument("--tables", default=None,
                    help="comma list of CB2 tables (ladder_candidates,ladders,rewards): run ONLY those, "
                         "CB1 tables untouched")
    ap.add_argument("--disk-cap-gb", type=float, default=None, help="--tables: stop at this cb2_root size")
    ap.add_argument("--data-dumps", type=Path, default=cb.DATA_DUMPS)
    ap.add_argument("--data-dumps-max-gb", type=float, default=None,
                    help="--tables: refuse while data-dumps is larger (q0041 uses 10.5)")
    a = ap.parse_args()

    if a.freeze_list:
        if not a.until:
            ap.error("--freeze-list needs --until")
        out = cb.freeze_list(a.freeze_list, a.extract_root, snapshot_root=a.snapshot_root,
                             from_utc=_iso(a.from_utc) if a.from_utc else None, until=_iso(a.until))
        print(json.dumps({k: out[k] for k in ("kind", "from_utc", "until", "n", "sha256", "final")}
                         | {"n_missing": len(out["missing_ids"])}))
        return 0

    cb2_root = a.cb2_root or (a.extract_root.parent / "cb2_extract" if a.extract_root != cb.EXTRACT_ROOT
                              else cb.CB2_EXTRACT_ROOT)
    if a.tables:
        return _cb2_only(a, cb, cb2_root)

    backfill = a.backfill_from is not None
    budget_min = a.budget_min if a.budget_min is not None else (90.0 if backfill else 7.0)
    kw = dict(snapshot_root=a.snapshot_root, sweep_root=a.sweep_root, extract_root=a.extract_root,
              rps=a.rps, max_requests=a.max_requests, budget_s=budget_min * 60.0,
              cb2_root=None if backfill else cb2_root)
    try:
        if backfill:
            summ = cb.extract(mode="backfill", backfill_from=_iso(a.backfill_from),
                              write_dev_list=True, **kw)
        else:
            summ = cb.extract(mode="all-new", **kw)
    except cb.ExtractLocked:
        print(json.dumps({"cb1_extract": cb.EXTRACTOR_VERSION, "skipped": "another extractor holds the lock"}))
        return 0
    except Exception as exc:
        print(json.dumps({"cb1_extract": cb.EXTRACTOR_VERSION, "error": f"{type(exc).__name__}: {exc}"[:300]}))
        return 1 if backfill else 0  # in-pass: never fail the pass; backfill: fail loudly
    print(json.dumps(summ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
