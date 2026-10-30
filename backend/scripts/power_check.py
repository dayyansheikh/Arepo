"""Print minimum detectable DeltaR2 and cluster requirements from a comparison results.json.

Read-only: reads one existing ``results.json`` (inputs are backed out of its bootstrap CIs),
writes only to stdout, or to ``--out`` which must be a new path. Usage:

    python scripts/power_check.py <results.json> [--alpha 0.05] [--power 0.8] [--n-tests N]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import power  # noqa: E402

TARGETS = (0.005, 0.01, 0.02, 0.037)


def analyse(res: dict, alpha: float, pw: float, n_tests: int | None, correction: str) -> dict:
    pooled = res["pooled"]
    k = int(pooled["n_clusters"])
    diffs = pooled["diffs"]
    nt = n_tests if n_tests is not None else max(1, len(diffs))
    rows = {}
    for key, d in diffs.items():
        sd = power.sd_from_ci(d["ci_lo"], d["ci_hi"], k)
        rows[key] = {
            "diff_r2": d["diff_r2"],
            "ci": [d["ci_lo"], d["ci_hi"]],
            "sd_cluster_contrib": sd,
            "mde_at_current_k": power.mde_delta_r2(k, sd, alpha, pw, nt, correction),
            "mde_single_test": power.mde_delta_r2(k, sd, alpha, pw, 1, correction),
            "clusters_required": {
                str(t): power.required_clusters(t, sd, alpha, pw, nt, correction) for t in TARGETS
            },
        }
        per = [
            pp["diffs"][key]["diff_r2"]
            for pp in res.get("per_period", {}).values()
            if key in pp.get("diffs", {})
        ]
        rows[key]["per_period"] = power.per_period_test(per, 0.01, alpha, pw)
    return {
        "source_cluster": res["config"]["cluster"],
        "n_rows": pooled["n"],
        "n_clusters": k,
        "alpha": alpha,
        "power": pw,
        "n_tests": nt,
        "correction": correction,
        "comparisons": rows,
        "assumptions": (
            "SE backed out of the bootstrap 95% CI (width/3.92); sd_c = SE*sqrt(K) held constant; "
            "normal approximation; clusters independent; per-period t/sign tests assume "
            "independent periods and are very low-powered at few periods."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", type=Path)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.8)
    ap.add_argument("--n-tests", type=int, default=None, help="default: number of pairs")
    ap.add_argument("--correction", choices=power.CORRECTIONS, default="bonferroni")
    ap.add_argument("--out", type=Path, default=None, help="optional NEW json path")
    a = ap.parse_args()
    out = analyse(json.loads(a.results.read_text()), a.alpha, a.power, a.n_tests, a.correction)
    print(
        f"source={a.results} cluster={out['source_cluster']} rows={out['n_rows']} "
        f"K={out['n_clusters']} alpha={a.alpha} power={a.power} "
        f"n_tests={out['n_tests']} ({a.correction})"
    )
    hdr = "pair        dR2       sd_c    MDE(m)   MDE(1)  " + "  ".join(
        f"K@{t}" for t in TARGETS
    )
    print(hdr)
    for key, r in out["comparisons"].items():
        ks = "  ".join(f"{r['clusters_required'][str(t)]:>8d}" for t in TARGETS)
        print(
            f"{key:<10} {r['diff_r2']:+.4f} {r['sd_cluster_contrib']:8.3f} "
            f"{r['mde_at_current_k']:8.4f} {r['mde_single_test']:8.4f}  {ks}"
        )
    print(out["assumptions"])
    if a.out:
        with a.out.open("x") as fh:  # refuses to overwrite
            json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
