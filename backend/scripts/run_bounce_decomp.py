# ruff: noqa: E501
"""SB2-J4 (snapshots) / SB2-J3 (book) bounce decomposition runner (DEVELOPMENT, NOT evidence).

    python scripts/run_bounce_decomp.py snapshots --tag sb2-snap [--n-boot 2000] [--dry-run]
    python scripts/run_bounce_decomp.py book --run-id h2_main --tag sb2-book [--n-boot 2000]

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
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    out_dir = bd.OUT_ROOT / f"bounce-{a.tag}"
    target = out_dir / ("dryrun.json" if a.dry_run else "results.json")
    if target.exists():
        print(f"refusing to overwrite {target}", file=sys.stderr)
        return 2

    job = "J4" if a.job == "snapshots" else "J3"
    if job == "J4":
        df, counts = bd.build_snapshot_triples(bd.SNAPSHOT_ROOT, bd.SWEEP_ROOT, a.until_utc, log=print)
        if not len(df):
            print("no triples; nothing run")
            return 0
        permute, tests = bd.permute_snapshot_targets, bd.snapshot_tests
        run_tests = lambda d: tests(d, a.n_boot, a.seed)  # noqa: E731
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
        run_tests = lambda d: bd.book_tests(d, {}, a.n_boot, a.seed)  # noqa: E731
        dataset = f"history:{a.run_id}"

    print(f"{len(df)} rows; running {'permuted-target dry run' if a.dry_run else 'tests'}", flush=True)
    placebo = run_tests(permute(df, a.seed + 1))
    out_dir.mkdir(parents=True, exist_ok=True)
    if a.dry_run:
        target.write_text(json.dumps({"job": job, "dry_run": True, "counts": bd._clean(counts),
                                      "placebo": placebo}, indent=1))
        print(f"dry run {target}")
        return 0
    res = run_tests(df)
    prior = bd.prior_tests()
    res["prior_tests"] = prior
    prov = provenance.run_provenance()
    doc = {"job": job, "run_id": f"bounce-{a.tag}", "seed": a.seed, "n_boot": a.n_boot,
           "until_utc": a.until_utc, "dataset": dataset, "counts": bd._clean(counts),
           "results": res, "placebo": placebo, "prior_tests": prior, "provenance": prov}
    target.write_text(json.dumps(bd._clean(doc), indent=1))
    sha = provenance.sha256_file(target)
    bd.log_trials(job, res, str(target.relative_to(ROOT)), sha, f"bounce-{a.tag}", prov,
                  placebo=placebo, dataset=dataset)
    print(f"results {target}")
    for k, t in res.get("tests", {}).items():
        print(k, json.dumps({x: t.get(x) for x in ("beta", "se", "p", "p_holm", "n")}))
    print("verdicts:", json.dumps(res.get("verdicts")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
