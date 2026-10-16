# ruff: noqa: E501
"""CB5 runner (docs/research_lab/CREATIVE_BATCH_5.md section 4.2). Subcommands (one per queue job family):

    python scripts/run_cb5.py extract --all-new --tables listings                     # live pass step (never fails the pass)
    python scripts/run_cb5.py extract --backfill-from 2026-10-11T12:00Z --tables listings --release-stream --budget-min 150 --disk-cap-gb 0.05   # q0101
    python scripts/run_cb5.py extract --backfill-from 2026-10-11T12:00Z --tables cdf --family-list <families_v1.json> --release-stream   # q0105

Exit codes: 0 = ok (including 'nothing to do'); 1 = refusal or failure that must not count as a successful repeat run;
2 = a guard refused the request (sealed id, date window, missing freeze, hash mismatch).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

REFUSED = 2


def _iso(s: str) -> str:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(obj: dict) -> None:
    print(json.dumps(obj, sort_keys=True, default=str))


def cmd_extract(a) -> int:
    from astrolabe.research_lab import cb4_data as d
    from astrolabe.research_lab import cb5_extract as x

    tables = tuple(t.strip() for t in a.tables.split(",") if t.strip())
    backfill = a.backfill_from is not None
    budget_min = a.budget_min if a.budget_min is not None else (150.0 if backfill else 7.0)
    cat = d.Catalogue(Path(a.catalogue_dir)) if backfill else None
    release = d.ReleaseCopies(Path(a.root) / "_scratch", catalogue=cat) if a.release_stream else None
    try:
        summ = x.run_tables(
            Path(a.snapshot_root), Path(a.sweep_root), Path(a.root), tables=tables, mode="backfill" if backfill else "all-new",
            since=_iso(a.backfill_from) if backfill else x.T5_DEV_START, family_list=Path(a.family_list) if a.family_list else None,
            budget_s=budget_min * 60.0, disk_cap_gb=a.disk_cap_gb, data_dumps=Path(a.data_dumps),
            data_dumps_max_gb=a.data_dumps_max_gb, retry_missing=a.retry_missing, release=release, catalogue=cat)
    except x.ExtractLocked:
        _emit({"cb5_extract": x.EXTRACTOR_VERSION, "skipped": "another extractor holds the lock"})
        return 0
    except x.VersionMismatch as exc:
        _emit({"cb5_extract": x.EXTRACTOR_VERSION, "refused": f"{type(exc).__name__}: {exc}"[:300]})
        return 1
    except Exception as exc:
        _emit({"cb5_extract": x.EXTRACTOR_VERSION, "error": f"{type(exc).__name__}: {exc}"[:300]})
        return 1 if backfill else 0  # in-pass: never fail the pass; backfill: fail loudly
    _emit(summ)
    return 1 if summ.get("stopped") in ("refused_data_dumps_over_cap", "data_dumps_over_cap") else 0


def build_parser() -> argparse.ArgumentParser:
    from astrolabe.research_lab import cb5_extract as x

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract", help="listings/ and cdf/ tables from complete captures (q0101, q0105, pass step)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all-new", action="store_true")
    g.add_argument("--backfill-from")
    p.add_argument("--tables", default="listings")
    p.add_argument("--family-list", default=None, help="frozen CDF family list (cdf table only)")
    p.add_argument("--release-stream", action="store_true")
    p.add_argument("--budget-min", type=float, default=None)
    p.add_argument("--disk-cap-gb", type=float, default=None)
    p.add_argument("--data-dumps", default=str(x.DATA_DUMPS))
    p.add_argument("--data-dumps-max-gb", type=float, default=x.JOB_REFUSE_GB + 2.0)
    p.add_argument("--retry-missing", action="store_true")
    p.add_argument("--snapshot-root", default=str(x.SNAPSHOT_ROOT))
    p.add_argument("--sweep-root", default=str(x.SWEEP_ROOT))
    p.add_argument("--root", default=str(x.CB5_ROOT))
    p.add_argument("--catalogue-dir", default=str(x.forecast.ROOT / "docs" / "research_lab" / "data_catalogue"))
    p.set_defaults(fn=cmd_extract)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    return int(a.fn(a))


if __name__ == "__main__":
    raise SystemExit(main())
