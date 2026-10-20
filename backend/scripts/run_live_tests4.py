# ruff: noqa: E501
"""Live tests E020-E024 (docs/research_lab/LIVE_TESTS_4.md; DRAFT until registered). Research only; never trades; makes
no network request (a pure reader of the collector's captures, sweeps and trade samples).

    python scripts/run_live_tests4.py run                    # series + sweeps + freezes + due outcomes; exit 75 if nothing new
    python scripts/run_live_tests4.py ops-stats              # counts only (never reads a price or an outcome value)
    python scripts/run_live_tests4.py census-captures --seal S --work /tmp/x --out cqch.json            # CQ, CH (counts only)
    python scripts/run_live_tests4.py census-flow --capture-seal S --sample-root R --work /tmp/y --out cf.json   # CF
    python scripts/run_live_tests4.py size-check --out size.json   # simulated-null size of the gates (code to be pinned)
    python scripts/run_live_tests4.py analyze --out res.json # the single registered analysis (refused before the date)

Install (section 9.2): host cron every 20 min offset from LT3's reader (10-59/20) under its own flock, or the queue
draft q0485 (fallback only); exit 0 after writing, exit 75 when nothing is new.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import live_tests4 as lt  # noqa: E402

SEALS = lt.ROOT / "docs" / "research_lab" / "seals"


def _write_out(path: Path | None, txt: str) -> int:
    if path is None:
        print(txt)
        return 0
    if path.exists():
        print(f"refusing to overwrite {path}")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt)
    print(f"wrote {path} sha256={lt.sha256_file(path)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    r.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    r.add_argument("--sample-root", type=Path, default=lt.SAMPLE_ROOT)
    r.add_argument("--sweep-root", type=Path, default=lt.SWEEP_ROOT)
    r.add_argument("--max-items", type=int, default=40)
    r.add_argument("--dry-run-start", default=None, help="DRY RUN ONLY: origin window start instead of REGISTERED_UTC (lines stay unregistered)")
    r.add_argument("--dry-run-end", default=None)
    r.add_argument("--data-dumps-cap-gb", type=float, default=None, help="exit 75 (not now) if data-dumps exceeds this many GiB")
    o = sub.add_parser("ops-stats")
    o.add_argument("--root", type=Path, default=lt.OUT_ROOT)
    c = sub.add_parser("census-captures")
    c.add_argument("--seal", type=Path, default=SEALS / "lt4_census_inputs_captures.json")
    c.add_argument("--work", type=Path, required=True)
    c.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    c.add_argument("--sweep-root", type=Path, default=lt.SWEEP_ROOT)
    c.add_argument("--day", action="append", default=None, help="UTC day (default: the spec census days)")
    c.add_argument("--out", type=Path, default=None)
    c.add_argument("--keep-work", action="store_true")
    f = sub.add_parser("census-flow")
    f.add_argument("--seal", type=Path, default=SEALS / "lt3_census_inputs_C2.json")
    f.add_argument("--capture-seal", type=Path, default=SEALS / "lt4_census_inputs_captures.json")
    f.add_argument("--sample-root", type=Path, action="append", required=True, help="restored trade_samples dir(s), searched in order")
    f.add_argument("--snapshot-root", type=Path, default=lt.SNAPSHOT_ROOT)
    f.add_argument("--work", type=Path, required=True)
    f.add_argument("--out", type=Path, default=None)
    f.add_argument("--keep-work", action="store_true")
    z = sub.add_parser("size-check")
    z.add_argument("--worlds", type=int, default=None)
    z.add_argument("--draws", type=int, default=None)
    z.add_argument("--out", type=Path, default=None)
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
        if dry and args.root.resolve() == lt.OUT_ROOT.resolve():
            print("refusing a dry run into the live root: pass --root <scratch dir>")
            return 2
        spec = lt.load_spec(sha=None) if dry else lt.load_spec()
        if dry:
            spec["_pinned"] = False  # a dry run never writes confirmation lines
        st = lt.run_once(snapshot_root=args.snapshot_root, sample_root=args.sample_root, sweep_root=args.sweep_root, root=args.root,
                         spec=spec, registered_utc=args.dry_run_start or lt.REGISTERED_UTC, end_utc=args.dry_run_end or lt.END_UTC,
                         max_items=args.max_items, allow_late=dry)
        print(json.dumps(st, sort_keys=True))
        if st.get("status") == "locked":
            print("another live_tests4 reader holds the lock: not now")
            return lt.TEMPFAIL
        if st.get("status") == "disk_cap":
            print("live_tests4 disk cap reached: collection stopped (window not extended)")
            return lt.TEMPFAIL
        if lt.now_ts() >= lt.epoch(lt.END_UTC) + 30 * 3600 and st["written"] == 0:
            print("LIVE_TESTS4_WINDOW_CLOSED")
            return 0
        return 0 if st["written"] else lt.TEMPFAIL
    if args.cmd == "ops-stats":
        print(json.dumps(lt.ops_stats(args.root), sort_keys=True, indent=1))
        return 0
    if args.cmd in ("census-captures", "census-flow", "size-check", "analyze") and args.out is not None and args.out.exists():
        print(f"refusing to overwrite {args.out}")
        return 1
    if args.cmd == "census-captures":
        res = lt.census_captures(seal=args.seal, snapshot_root=args.snapshot_root, sweep_root=args.sweep_root, work=args.work, days=args.day)
        res["code_sha256"] = lt.code_hashes()
        if not args.keep_work:
            lt.cleanup_census(args.work)
        rc = _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
        return 3 if "error" in res else rc
    if args.cmd == "census-flow":
        res = lt.census_flow(seal=args.seal, capture_seal=args.capture_seal, sample_roots=args.sample_root, snapshot_root=args.snapshot_root,
                             work=args.work)
        res["code_sha256"] = lt.code_hashes()
        if not args.keep_work:
            lt.cleanup_census(args.work)
        rc = _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
        return 3 if "error" in res else rc
    if args.cmd == "size-check":
        from astrolabe.research_lab import live_tests4_analysis as la

        sc = lt.load_spec(sha=None)["size_check"]
        res = la.size_check(worlds=args.worlds or sc["worlds"], draws=args.draws or sc["draws"], seed=sc["seed"], nominal=sc["nominal"])
        return _write_out(args.out, json.dumps(res, sort_keys=True, indent=1, default=lt._json))
    if args.cmd == "analyze":
        from astrolabe.research_lab import live_tests4_analysis as la

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
