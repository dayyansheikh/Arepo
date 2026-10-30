# ruff: noqa: E501
"""SB2-J4 (snapshots) / SB2-J3 (book) bounce decomposition runner (DEVELOPMENT, NOT evidence).

    python scripts/run_bounce_decomp.py snapshots --tag sb2-snap [--n-boot 2000] [--dry-run]
    python scripts/run_bounce_decomp.py book --run-id h2_main --tag sb2-book [--n-boot 2000]

J4-R (declared re-read on fresh captures) and J3 with the expanding-past estimator:
    python scripts/run_bounce_decomp.py snapshots --tag j4r --since 2026-10-16T00:00:00Z \
        --until 2026-10-21T00:00:00Z --h-tight --estimator expanding --placebo-draws 20 --min-periods 48
    python scripts/run_bounce_decomp.py book --run-id h2_main --tag j3x --estimator expanding --placebo-draws 20
``--until`` is an EXCLUSIVE end (captures started < it); ``--until-utc`` keeps its inclusive meaning.
A "period" is a triple with in-range gaps that contributes >= 1 row; < --min-periods periods exits 3 before
any test or placebo. With --until the run also exits 3 if the newest complete capture started earlier than
--until minus 2 h (the window is not yet covered). The new flags (--since, --h-tight, --placebo-draws,
--min-periods) are refused (exit 2) with --estimator pooled. Default placebo: market-pooled bootstrap.

Writes data-dumps/research_lab/bounce_decomp/bounce-<tag>/results.json (refuses to overwrite) and
appends trials (per test + one ml_explain count line + placebo lines). ``--dry-run`` runs on
permuted targets only, writes dryrun.json and logs NO trials. Read-only on inputs; no network.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    from astrolabe.research_lab import bounce_decomp as bd
    from astrolabe.research_lab import provenance

    ap = argparse.ArgumentParser()
    ap.add_argument("job", choices=["snapshots", "book"])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--run-id", default="h2_main")
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=116)
    ap.add_argument("--until-utc", default=None)
    ap.add_argument("--since", default=None, help="only captures started >= this (h, i, j all fresh)")
    ap.add_argument("--until", default=None, help="exclusive end: only captures started < this")
    ap.add_argument("--h-tight", action="store_true", help="apply the E001 tightness rule at h")
    ap.add_argument("--estimator", choices=["pooled", "expanding"], default="pooled")
    ap.add_argument("--placebo-draws", type=int, default=0,
                    help="> 0: matched increment-shuffle placebo family with this many draws "
                         "(default 0: the original permuted-target placebo)")
    ap.add_argument("--placebo-scheme", choices=["bootstrap", "permute"], default="bootstrap",
                    help="increments drawn with replacement from the market's pooled increments "
                         "(bootstrap, default) or permuted within runs (permute, explicit only)")
    ap.add_argument("--min-periods", type=int, default=0,
                    help="refuse to run (exit 3) if fewer qualifying 2h periods (snapshots)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot-root", type=Path, default=bd.SNAPSHOT_ROOT,
                    help="capture root to read (default: the live SNAPSHOT_ROOT)")
    ap.add_argument("--sweep-root", type=Path, default=bd.SWEEP_ROOT,
                    help="book-sweep root to read (default: the live SWEEP_ROOT)")
    a = ap.parse_args()
    roots = {"snapshot_root": str(a.snapshot_root.resolve()),
             "sweep_root": str(a.sweep_root.resolve())}
    out_dir = bd.OUT_ROOT / f"bounce-{a.tag}"
    target = out_dir / ("dryrun.json" if a.dry_run else "results.json")
    if target.exists():
        print(f"refusing to overwrite {target}", file=sys.stderr)
        return 2

    if a.until and a.until_utc:
        print("--until (exclusive) and --until-utc (inclusive) are mutually exclusive", file=sys.stderr)
        return 2
    job = "J4" if a.job == "snapshots" else "J3"
    expanding = a.estimator == "expanding"
    new_flags = [f for f, on in (("--since", a.since), ("--h-tight", a.h_tight),
                                 ("--placebo-draws", a.placebo_draws > 0),
                                 ("--min-periods", a.min_periods > 0)) if on]
    if new_flags and not expanding:
        print(f"refusing {new_flags} with --estimator pooled (legacy estimator; use --estimator expanding)",
              file=sys.stderr)
        return 2
    if job == "J3" and (a.since or a.h_tight or a.min_periods or a.until):
        print("--since/--until/--h-tight/--min-periods apply to the snapshots job only", file=sys.stderr)
        return 2
    if job == "J4":
        if a.until:
            from datetime import timedelta
            newest = bd.newest_capture_start(a.snapshot_root)
            need = bd.forecast._parse_ts(a.until) - timedelta(hours=2)
            if newest is None or newest < need:
                print(f"newest complete capture starts {newest} < --until minus 2h ({need}); window not "
                      "yet covered; refusing to run", file=sys.stderr)
                return 3
        df, counts = bd.build_snapshot_triples(a.snapshot_root, a.sweep_root, a.until_utc, log=print,
                                               since_utc=a.since, h_tight=a.h_tight, before_utc=a.until)
        if not len(df):
            print("no triples; nothing run")
            return 3 if a.min_periods else 0
        n_periods = bd.qualifying_periods(df)
        if n_periods < a.min_periods:
            print(f"only {n_periods} qualifying periods < --min-periods {a.min_periods}; refusing to run",
                  file=sys.stderr)
            return 3
        permute = bd.permute_snapshot_targets
        run_tests = lambda d: bd.snapshot_tests(d, a.n_boot, a.seed, a.estimator)  # noqa: E731
        run_placebo = lambda d: bd.placebo_family(d, a.placebo_draws, a.seed + 1, a.estimator, 20, a.placebo_scheme)  # noqa: E731
        dataset = "snapshots"
    else:
        hist = bd.HIST_ROOT / a.run_id
        df, counts = bd.build_book_triples(
            hist / "battery1" / "features.parquet",
            bd.HIST_ROOT.parent / "history_sources" / "book_features" / "book_features.csv.gz",
            hist / "panel_H6h.csv.gz", log=print, run_dir=hist)
        if not len(df):
            print("no book triples; nothing run")
            return 0
        permute = bd.permute_book_targets
        run_tests = lambda d: bd.book_tests(d, {}, a.n_boot, a.seed, a.estimator)  # noqa: E731
        run_placebo = lambda d: bd.book_placebo_family(d, a.placebo_draws, a.seed + 1, a.estimator, 20, a.placebo_scheme)  # noqa: E731
        dataset = f"history:{a.run_id}"

    print(f"{len(df)} rows; running {'dry run' if a.dry_run else 'tests'}, placebo: {f'family x{a.placebo_draws} ({a.placebo_scheme})' if a.placebo_draws else 'permuted targets'}", flush=True)
    placebo = run_placebo(df) if a.placebo_draws > 0 else run_tests(permute(df, a.seed + 1))
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.dry_run:
        target.write_text(json.dumps({"job": job, "dry_run": True, "roots": roots, "counts": bd._clean(counts),
                                      "placebo": placebo}, indent=1))
        print(f"dry run {target}")
        return 0
    res = run_tests(df)
    prior = bd.prior_tests()
    res["prior_tests"] = prior
    prov = provenance.run_provenance()
    revision = ("j4r_expanding_v1" if job == "J4" else "j3_expanding_v1") if expanding else None
    if a.placebo_draws > 0:
        bd.apply_placebo_reading(res, placebo)
        if res["family_status"] != "OK":
            print(f"{res['family_status']}; verdicts withheld", file=sys.stderr)
    if job == "J4" and expanding:
        res["sensitivities"] = bd.snapshot_sensitivities(df, 200, a.seed)
    doc = {"job": job, "run_id": f"bounce-{a.tag}", "seed": a.seed, "n_boot": a.n_boot,
           "until_utc": a.until_utc, "since": a.since, "until_exclusive": a.until, "h_tight": a.h_tight,
           "estimator": a.estimator, "placebo_draws": a.placebo_draws, "placebo_scheme": a.placebo_scheme, "min_periods": a.min_periods,
           "n_periods": bd.qualifying_periods(df) if job == "J4" else None,
           "revision": revision, "roots": roots, "dataset": dataset, "counts": bd._clean(counts),
           "results": res, "placebo": placebo, "prior_tests": prior, "provenance": prov}
    target.write_text(json.dumps(bd._clean(doc), indent=1))
    sha = provenance.sha256_file(target)
    bd.log_trials(job, res, str(target.relative_to(ROOT)), sha, f"bounce-{a.tag}", prov,
                  placebo=placebo, dataset=dataset, revision=revision, family_status=res.get("family_status"))
    print(f"results {target}")
    for k, t in res.get("tests", {}).items():
        print(k, json.dumps({x: t.get(x) for x in ("beta", "se", "p", "p_holm", "n")}))
    print("verdicts:", json.dumps(res.get("verdicts")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
