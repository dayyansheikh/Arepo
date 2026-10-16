# ruff: noqa: E501
"""CB4 runner (docs/research_lab/CREATIVE_BATCH_4.md section 4.2). Run from cwd=backend (queue worker).
EXPLORATORY: no edge, calibration or profitability claim; paper rules only.

DATA subcommands (this file; module ``astrolabe.research_lab.cb4_data``):
    python scripts/run_cb4.py closewin --backfill-from 2026-10-11T12:00Z --release-stream --budget-min 150 --disk-cap-gb 0.40   # q0080
    python scripts/run_cb4.py closewin --all-new --data-dumps-max-gb 11            # later pass step (NOT wired)

ANALYSIS hooks (pilot, flip-trades, census, measure-N, measure-E, measure-commit, fetch-outcomes, screen, replicate)
call ``astrolabe.research_lab.cb4_analysis.cmd_<name>(args)`` (name with '-' as '_'); if the module or the function
is missing the command exits 2. Other sessions own that module.

Exit codes: 0 ok / lock held / transient pause; 1 error or backfill refusal (data-dumps over cap, version mismatch);
2 refusal of a guard or a missing analysis hook.
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
    release = None
    if a.release_stream:
        release = d.ReleaseCopies(Path(a.root) / "_scratch", catalogue=d.Catalogue(Path(a.catalogue_dir)))
    try:
        summ = d.run_closewin(
            Path(a.snapshot_root), Path(a.sweep_root), Path(a.root), mode="backfill" if backfill else "all-new",
            since=_iso(a.backfill_from) if backfill else d.T4_DEV_START, budget_s=budget_min * 60.0,
            disk_cap_gb=a.disk_cap_gb, data_dumps=Path(a.data_dumps), data_dumps_max_gb=a.data_dumps_max_gb,
            retry_missing=a.retry_missing, release=release)
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
    p.add_argument("--data-dumps-max-gb", type=float, default=10.5, help="refuse (exit 1) while data-dumps is larger")
    p.add_argument("--retry-missing", action="store_true", help="re-attempt captures recorded as missing")
    p.add_argument("--snapshot-root", default=str(d.SNAPSHOT_ROOT))
    p.add_argument("--sweep-root", default=str(d.SWEEP_ROOT))
    p.add_argument("--root", default=str(d.CB4_ROOT))
    p.add_argument("--catalogue-dir", default=str(d.CATALOGUE_DIR))

    for name in ANALYSIS_COMMANDS:
        q = sub.add_parser(name, help=f"analysis hook (cb4_analysis.cmd_{name.replace('-', '_')})")
        q.add_argument("extra", nargs=argparse.REMAINDER)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "closewin":
        return cmd_closewin(a)
    if a.cmd in ANALYSIS_COMMANDS:
        return _analysis_hook(a.cmd, a)
    return cmd_data_dispatch(a)


def cmd_data_dispatch(a) -> int:  # replaced below by the fetch/seal subcommands
    print(f"unknown command {a.cmd}", file=sys.stderr)
    return HOOK_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
