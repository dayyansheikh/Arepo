# ruff: noqa: E501
"""CB3 quote_state/ extractor (docs/research_lab/CREATIVE_BATCH_3.md §4.3.1). Data-only; read-only on
snapshots and sweeps; writes only under --root (data-dumps/research_lab/cb3_extract). Its own step, NOT part of
the CB1/CB2 extract line (challenger item 10).

    python scripts/run_cb3_quote_state.py --backfill-before 2026-10-15T21:00Z --budget-min 150 --disk-cap-gb 0.30 --data-dumps-cap-gb 12   # q0060
    python scripts/run_cb3_quote_state.py --all-new --data-dumps-cap-gb 12     # later pass step (not wired yet)

Exit codes: 0 ok / budget stop / lock held; 1 refusal (no data-dumps headroom, bad window, version mismatch), disk_cap stop or backfill error.
all-new never fails the pass on an unexpected error (exit 0) but a data-dumps refusal exits 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def _iso(s: str) -> str:
    from datetime import UTC, datetime

    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import cb3_quote_state as q

    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all-new", action="store_true", help="live: extract complete captures not yet extracted, newest first")
    g.add_argument("--backfill-before", help="ISO exclusive upper bound on capture start (<= 2026-10-15T21:00Z); oldest first")
    ap.add_argument("--backfill-from", default=None, help="ISO inclusive lower bound (default: first complete capture on the host)")
    ap.add_argument("--budget-min", type=float, default=None, help="wall-clock self-limit (default 7 all-new, 150 backfill)")
    ap.add_argument("--disk-cap-gb", type=float, default=None, help="stop when --root exceeds this size")
    ap.add_argument("--data-dumps", type=Path, default=q.DATA_DUMPS)
    ap.add_argument("--data-dumps-cap-gb", type=float, default=None,
                    help="host data-dumps ceiling (12): refuse (exit 1) only if data-dumps + projected output + scratch exceeds it")
    ap.add_argument("--restore", action="store_true",
                    help="restore archived/release-only captures from their release, one at a time (gh + zstd + network)")
    ap.add_argument("--retry-missing", action="store_true", help="re-attempt captures recorded as missing")
    ap.add_argument("--snapshot-root", type=Path, default=q.SNAPSHOT_ROOT)
    ap.add_argument("--sweep-root", type=Path, default=q.SWEEP_ROOT)
    ap.add_argument("--root", type=Path, default=q.CB3_ROOT)
    a = ap.parse_args(argv)

    backfill = a.backfill_before is not None
    budget_min = a.budget_min if a.budget_min is not None else (150.0 if backfill else 7.0)
    try:
        summ = q.run(a.snapshot_root, a.sweep_root, a.root, mode="backfill" if backfill else "all-new",
                     since=_iso(a.backfill_from) if a.backfill_from else None,
                     before=_iso(a.backfill_before) if backfill else None, budget_s=budget_min * 60.0,
                     disk_cap_gb=a.disk_cap_gb, data_dumps=a.data_dumps, data_dumps_cap_gb=a.data_dumps_cap_gb,
                     scratch_gb=0.3 if a.restore else 0.0,
                     restore=q.restore_capture_via_release if a.restore else None, retry_missing=a.retry_missing)
    except q.ExtractLocked:
        print(json.dumps({"cb3_quote_state": q.EXTRACTOR_VERSION, "skipped": "another extractor holds the lock"}))
        return 0
    except (q.VersionMismatch, q.WindowError) as exc:
        print(json.dumps({"cb3_quote_state": q.EXTRACTOR_VERSION, "refused": f"{type(exc).__name__}: {exc}"[:300]}))
        return 1
    except Exception as exc:
        print(json.dumps({"cb3_quote_state": q.EXTRACTOR_VERSION, "error": f"{type(exc).__name__}: {exc}"[:300]}))
        return 1 if backfill else 0
    print(json.dumps(summ))
    # non-zero: no headroom, or own disk cap reached (the run is incomplete and a repeat would not fix it);
    # a budget stop exits 0 so the repeat mechanism continues it
    return 1 if summ.get("stopped") in ("refused_no_headroom", "no_headroom", "disk_cap") else 0


if __name__ == "__main__":
    raise SystemExit(main())
