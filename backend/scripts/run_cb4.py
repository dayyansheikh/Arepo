# ruff: noqa: E501
"""CB4 runner (docs/research_lab/CREATIVE_BATCH_4.md section 4.2). Run from cwd=backend (queue worker).
EXPLORATORY: no edge, calibration or profitability claim; paper rules only.

DATA subcommands (this file; module ``astrolabe.research_lab.cb4_data``):
    python scripts/run_cb4.py fetch --kind era --run-id h7_cb4_era --seed arepo-h7-era --per-cell 800 ... --cap-at 2026-10-22T00:00Z   # q0081 (alias era-fetch)
    python scripts/run_cb4.py fetch --kind series --run-id h7_cb4_series --seed arepo-h7-series --n-series 400 ...                    # q0082 (alias series-fetch)
    python scripts/run_cb4.py era-frame / series-frame ...   # stop after the frame; writes frame_report.json (category counts)
    python scripts/run_cb4.py record-deadline                # q0083b: records 'not run' for unsealed incomplete h7 runs at T_seal
    python scripts/run_cb4.py seal --run-ids h7_cb4_era,h7_cb4_series                                                                 # q0083
    python scripts/run_cb4.py verify-seal --run-ids h7_cb4_era,h7_cb4_series
    python scripts/run_cb4.py series-rules                       # writes docs/research_lab/seals/cb4_series_rules.json (commit it before q0082)
    python scripts/run_cb4.py closewin --backfill-from 2026-10-11T12:00Z --release-stream --budget-min 150 --disk-cap-gb 0.40   # q0080
    python scripts/run_cb4.py closewin --all-new --data-dumps-max-gb 12            # pass step (after the CB4 closewin step)

ANALYSIS hooks (pilot, flip-trades, census, measure-N, measure-E, measure-commit, fetch-outcomes, screen, replicate)
call ``astrolabe.research_lab.cb4_analysis.cmd_<name>(args)`` (name with '-' as '_'); if the module or the function
is missing the command exits 2. Their own options (--family, --window, ...) are parsed by cb4_analysis; a guard refusal there exits 3.

Exit codes: 0 ok / lock held / transient pause; 1 error or backfill refusal (data-dumps over cap, version mismatch);
2 refusal of a guard or a missing analysis hook. A fetch at/after T_seal 2026-10-22T00:00Z starts no chunk (exit 0,
status ``not_run_deadline`` for an incomplete run).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

HOOK_EXIT = 2
ANALYSIS_COMMANDS = ("pilot", "flip-trades", "census", "measure-N", "measure-E", "measure-commit",
                     "fetch-outcomes", "screen", "replicate")


def _iso(s: str) -> str:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(obj: dict) -> None:
    print(json.dumps(obj, default=str, sort_keys=True))


def _analysis_hook(name: str, a) -> int:
    """Lazy import so the analysis module can plug in without editing this file (exit 2 if absent)."""
    fn_name = "cmd_" + name.replace("-", "_")
    try:
        from astrolabe.research_lab import cb4_analysis  # noqa: PLC0415
    except ImportError as exc:
        print(f"cb4_analysis is not available ({exc}); '{name}' cannot run", file=sys.stderr)
        return HOOK_EXIT
    fn = getattr(cb4_analysis, fn_name, None)
    if fn is None:
        print(f"cb4_analysis has no {fn_name}(args); '{name}' cannot run", file=sys.stderr)
        return HOOK_EXIT
    out = fn(a)
    return int(out) if isinstance(out, int) else 0


def cmd_closewin(a) -> int:
    from astrolabe.research_lab import cb4_data as d

    backfill = a.backfill_from is not None
    budget_min = a.budget_min if a.budget_min is not None else (150.0 if backfill else 7.0)
    cat = d.Catalogue(Path(a.catalogue_dir)) if backfill else None  # all-new: no catalogue scan in the pass step
    release = d.ReleaseCopies(Path(a.root) / "_scratch", catalogue=cat) if a.release_stream else None
    try:
        summ = d.run_closewin(
            Path(a.snapshot_root), Path(a.sweep_root), Path(a.root), mode="backfill" if backfill else "all-new",
            since=_iso(a.backfill_from) if backfill else d.T4_DEV_START, budget_s=budget_min * 60.0,
            disk_cap_gb=a.disk_cap_gb, data_dumps=Path(a.data_dumps), data_dumps_max_gb=a.data_dumps_max_gb,
            retry_missing=a.retry_missing, release=release, catalogue=cat)
    except d.ExtractLocked:
        _emit({"cb4_closewin": d.CLOSEWIN_VERSION, "skipped": "another extractor holds the lock"})
        return 0
    except d.VersionMismatch as exc:
        _emit({"cb4_closewin": d.CLOSEWIN_VERSION, "refused": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    except Exception as exc:
        _emit({"cb4_closewin": d.CLOSEWIN_VERSION, "error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1 if backfill else 0  # in-pass: never fail the pass; backfill: fail loudly
    _emit(summ)
    # a refusal must not count as a successful repeat run (non-zero), as q0041/q0060
    return 1 if summ.get("stopped") in ("refused_data_dumps_over_cap", "data_dumps_over_cap") else 0


def build_parser() -> argparse.ArgumentParser:
    from astrolabe.research_lab import cb4_data as d

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("closewin", help="closewin/ + departures/ extract (q0080 backfill, or the later all-new pass step)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all-new", action="store_true", help="live: extract complete captures not yet extracted (oldest first)")
    g.add_argument("--backfill-from", help="ISO; extract all complete captures at/after it (oldest first)")
    p.add_argument("--release-stream", action="store_true",
                   help="read captures gone from the host from the verified release copy (scratch <= 0.2 GB)")
    p.add_argument("--budget-min", type=float, default=None, help="wall-clock self-limit (default 7 all-new, 150 backfill)")
    p.add_argument("--disk-cap-gb", type=float, default=0.40, help="stop when the written tables exceed this size")
    p.add_argument("--data-dumps", default=str(d.DATA_DUMPS))
    p.add_argument("--data-dumps-max-gb", type=float, default=12.0,
                   help="data-dumps cap; refuse (exit 1) only when size + remaining output allowance + scratch would pass it")
    p.add_argument("--retry-missing", action="store_true", help="re-attempt captures recorded as missing")
    p.add_argument("--snapshot-root", default=str(d.SNAPSHOT_ROOT))
    p.add_argument("--sweep-root", default=str(d.SWEEP_ROOT))
    p.add_argument("--root", default=str(d.CB4_ROOT))
    p.add_argument("--catalogue-dir", default=str(d.CATALOGUE_DIR))

    from astrolabe.research_lab import cb4_data as _d  # noqa: PLC0415

    def add_fetch_args(q: argparse.ArgumentParser) -> None:
        q.add_argument("--run-id", default=None)
        q.add_argument("--seed", default=None)
        q.add_argument("--per-cell", type=int, default=None, help="era: markets per group x period cell (800)")
        q.add_argument("--periods", default=None, help="era: a/b,a/b,... (P0,P1,P2)")
        q.add_argument("--origin-window-h", type=float, default=None)
        q.add_argument("--min-life-d", type=float, default=None)
        q.add_argument("--n-series", type=int, default=None)
        q.add_argument("--n-sports-series", type=int, default=None)
        q.add_argument("--members-per-series", type=int, default=None)
        q.add_argument("--roll-from", default=None)
        q.add_argument("--exclude-runs", default="")
        q.add_argument("--exclude-seal-ids", default="")
        q.add_argument("--exclude-categories", default="weather")
        q.add_argument("--walk-closed", default="true,false")
        q.add_argument("--cap-at", default=_d.T_SEAL)
        q.add_argument("--rps", type=float, default=4.0)
        q.add_argument("--disk-cap-gb", type=float, default=None)
        q.add_argument("--budget-min", type=float, default=None)
        q.add_argument("--max-trades", type=int, default=None)
        q.add_argument("--root", default=None)
        q.add_argument("--data-dumps", default=None)
        q.add_argument("--data-dumps-cap-gb", type=float, default=_d.DATA_DUMPS_FETCH_CAP_GB)
        q.add_argument("--snapshot-root", default=None)
        q.add_argument("--series-rules-file", default=None)
        q.add_argument("--group-s-amendment", default=None, help="committed decision file for group S (sampling waits for it)")
        q.add_argument("--stage", choices=["frame", "all"], default="all", help="frame = stop after the frame and its report")

    p = sub.add_parser("fetch", help="h7 fetch (q0081 era / q0082 series)")
    p.add_argument("--kind", choices=["era", "series"], required=True)
    add_fetch_args(p)
    for alias, kind, stg in (("era-fetch", "era", "all"), ("series-fetch", "series", "all"),
                             ("era-frame", "era", "frame"), ("series-frame", "series", "frame")):
        p = sub.add_parser(alias, help=f"alias of: fetch --kind {kind} --stage {stg}")
        p.set_defaults(kind=kind)
        add_fetch_args(p)
        p.set_defaults(stage=stg)
    p = sub.add_parser("record-deadline", help="record 'not run' for unsealed, incomplete h7 runs at T_seal (dependency-free)")
    p.add_argument("--root", default=None)
    p.add_argument("--seals-dir", default=None)
    for name in ("seal", "verify-seal"):
        p = sub.add_parser(name, help="seal / verify h7_cb4_era and h7_cb4_series (q0083)")
        p.add_argument("--run-ids", default=",".join(_d.H7_RUN_IDS))
        p.add_argument("--root", default=None)
        p.add_argument("--seals-dir", default=None)
        p.add_argument("--trials-path", default=None)
    p = sub.add_parser("series-rules", help="write the committed cadence/matching rule hash file")
    p.add_argument("--path", default=None)

    for name in ANALYSIS_COMMANDS:
        q = sub.add_parser(name, help=f"analysis hook (cb4_analysis.cmd_{name.replace('-', '_')})")
        q.add_argument("extra", nargs=argparse.REMAINDER)
    return ap


def main(argv: list[str] | None = None) -> int:
    # analysis subparsers take their options verbatim (parsed in cb4_analysis); argparse.REMAINDER alone rejects a leading ``--flag``.
    a, rest = build_parser().parse_known_args(argv)
    if rest:
        if a.cmd not in ANALYSIS_COMMANDS:
            build_parser().error(f"unrecognized arguments: {' '.join(rest)}")
        a.extra = [*rest, *(a.extra or [])]
    if a.cmd == "closewin":
        return cmd_closewin(a)
    if a.cmd in ANALYSIS_COMMANDS:
        return _analysis_hook(a.cmd, a)
    return cmd_data_dispatch(a)


def cmd_data_dispatch(a) -> int:
    from astrolabe.research_lab import cb4_data as d  # noqa: PLC0415

    if a.cmd in ("fetch", "era-fetch", "series-fetch", "era-frame", "series-frame"):
        return d.cmd_fetch(a)
    if a.cmd == "seal":
        return d.cmd_seal(a)
    if a.cmd == "verify-seal":
        return d.cmd_verify_seal(a)
    if a.cmd == "record-deadline":
        return d.cmd_record_deadline(a)
    if a.cmd == "series-rules":
        return d.cmd_series_rules(a)
    print(f"unknown command {a.cmd}", file=sys.stderr)
    return HOOK_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
