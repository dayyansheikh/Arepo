# ruff: noqa: E501
"""Live tests E012-E014 (docs/research_lab/LIVE_TESTS_2.md; DRAFT until registered). Research only; never trades;
makes no network request (reads the collector's snapshots and trade samples).

    python scripts/run_live_tests2.py run            # series + freezes + due outcomes; exit 75 if nothing new
    python scripts/run_live_tests2.py ops-stats      # counts only (never reads a mid or an outcome value)
    python scripts/run_live_tests2.py census --until 2026-10-19T21:00:00Z --work /tmp/x   # pre-window scales
    python scripts/run_live_tests2.py analyze        # the single registered analysis (refused before the date)

Queue use (draft q0420): lane net, ``repeat``; exit 0 after writing (re-queued at once), exit 75 when nothing is new
(the queue waits 30 min and does not count the attempt).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_tests2 as lt  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    r.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    r.add_argument("--sample-root", type=Path, default=lt.SAMPLE_ROOT)
    r.add_argument("--max-items", type=int, default=40)
    r.add_argument("--dry-run-start", default=None,
                   help="DRY RUN ONLY: origin window start instead of REGISTERED_UTC (lines stay unregistered)")
    r.add_argument("--dry-run-end", default=None)
    r.add_argument("--data-dumps-cap-gb", type=float, default=None,
                   help="exit 75 (not now) if data-dumps exceeds this many GiB")
    o = sub.add_parser("ops-stats")
    o.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    c = sub.add_parser("census")
    c.add_argument("--until", required=True)
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    c.add_argument("--sample-root", type=Path, default=lt.SAMPLE_ROOT)
    c.add_argument("--n-caps", type=int, default=4)
    c.add_argument("--n-samples", type=int, default=4)
    a = sub.add_parser("analyze")
    a.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    a.add_argument("--out", type=Path, default=None)
    a.add_argument("--no-trials", action="store_true", help="do not append the counted trials line (tests only)")
    args = ap.parse_args(argv)

    if args.cmd == "run":
        if args.data_dumps_cap_gb is not None:
            dd = lt.ROOT / "data-dumps"
            if dd.exists() and lt.du_bytes(dd) > args.data_dumps_cap_gb * 2**30:
                print(f"data-dumps above {args.data_dumps_cap_gb} GiB: not now")
                return lt.TEMPFAIL
        dry = args.dry_run_start is not None
        spec = lt.load_spec(sha=None) if dry else lt.load_spec()
        if dry:
            spec["_pinned"] = False  # a dry run never writes confirmation lines
        st = lt.run_once(snapshot_root=args.snapshot_root, sample_root=args.sample_root, root=args.root, spec=spec,
                         registered_utc=args.dry_run_start or lt.REGISTERED_UTC,
                         end_utc=args.dry_run_end or lt.END_UTC, max_items=args.max_items, allow_late=dry)
        print(json.dumps(st, sort_keys=True))
        if st.get("status") == "disk_cap":
            print("live_tests2 disk cap reached: collection stopped (window not extended)")
            return lt.TEMPFAIL
        if lt.now_ts() >= lt.epoch(lt.END_UTC) + 30 * 3600 and st["written"] == 0:
            print("LIVE_TESTS2_WINDOW_CLOSED")
            return 0
        return 0 if st["written"] else lt.TEMPFAIL
    if args.cmd == "ops-stats":
        print(json.dumps(lt.ops_stats(args.root), sort_keys=True, indent=1))
        return 0
    if args.cmd == "census":
        res = lt.census(snapshot_root=args.snapshot_root, sample_root=args.sample_root, until_utc=args.until,
                        n_caps=args.n_caps, n_samples=args.n_samples, work=args.work)
        print(json.dumps(res, sort_keys=True, indent=1))
        return 0
    if args.cmd == "analyze":
        from astrolabe.research_lab import live_tests2_analysis as la

        if args.out and args.out.exists():
            print(f"refusing to overwrite {args.out}")
            return 1
        res = la.analyze(args.root)
        txt = json.dumps(res, sort_keys=True, indent=1, default=str)
        if args.out:
            args.out.write_text(txt)
        if not args.no_trials:
            from astrolabe.research_lab import provenance

            provenance.append_trial(la.trial_record(res))
        print(txt)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
