"""Run a preset model comparison on an existing dataset (read-only inputs).

    python scripts/run_comparison.py --dataset e001 --preset e001_repro
    python scripts/run_comparison.py --dataset e001 --preset family_ablation

Writes data-dumps/research_lab/comparisons/<run_id>/results.json (never overwrites).
family_ablation output is DEVELOPMENT / post-hoc analysis of E001 data, not a registered
experiment, and carries no edge claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import compare, panel  # noqa: E402

E001_DIR = ROOT / "data-dumps" / "research_lab" / "e001"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "comparisons"
FAMILIES = ["price", "momentum", "context", "interaction"]
TOL = 1e-9


def load_e001() -> pd.DataFrame:
    manifest = json.loads((E001_DIR / "manifest.json").read_text())
    caps = [
        {"capture_id": c["capture_id"], "start_utc": c["start_utc"]} for c in manifest["captures"]
    ]
    snap = pd.read_csv(
        E001_DIR / "snapshots.csv.gz",
        dtype={"market_id": str, "event_id": str, "capture_id": str},
    )
    pnl, _ = panel.build_panel(snap, caps)
    return panel.usable(pnl)


def repro_diff(res: dict) -> float:
    """Max abs difference vs the frozen E001 results.json (R2, CI, MAE, Spearman)."""
    ref = json.loads((E001_DIR / "results.json").read_text())["metrics"]
    worst = 0.0

    def upd(a: float, b: float) -> None:
        nonlocal worst
        if a != a and b != b:  # both NaN
            return
        worst = max(worst, abs(a - b))

    for m, v in ref.items():
        got = res["pooled"]["models"][m]
        upd(got["r2_oos"], v["pooled_r2_oos"])
        upd(got["mae"], v["pooled_mae"])
        if m != "B0":
            upd(got["ci_lo"], v["pooled_ci"][0])
            upd(got["ci_hi"], v["pooled_ci"][1])
        for d in v["per_period"]:
            g = res["per_period"][d["period"]]["models"][m]
            for a, b in (
                ("r2_oos", "r2_oos"),
                ("ci_lo", "ci_lo"),
                ("ci_hi", "ci_hi"),
                ("mae", "mae"),
                ("spearman", "spearman"),
            ):
                upd(g[a], d[b])
    return worst


def print_table(res: dict, banner: str) -> None:
    print(f"\n*** {banner} ***")
    base = res["config"]["baseline"]
    names = [m["name"] for m in res["config"]["models"]]
    pp = sorted(res["per_period"])
    print(f"baseline={base} cluster={res['config']['cluster']} n_boot={res['config']['n_boot']}")
    hdr = f"{'model':14} {'pooled R2':>10} {'95% CI':>20} " + " ".join(f"p{p:<7}" for p in pp)
    print(hdr + f" {'MAE':>9}")
    for m in names:
        v = res["pooled"]["models"][m]
        per = " ".join(f"{res['per_period'][p]['models'][m]['r2_oos']:+.4f} " for p in pp)
        print(
            f"{m:14} {v['r2_oos']:+10.5f} [{v['ci_lo']:+.4f},{v['ci_hi']:+.4f}] "
            f"{per} {v['mae']:9.6f}"
        )
    ref = next((n for n in names if n == "B3"), None)
    if ref:
        cl = res["config"]["cluster"]
        print(f"\nPaired pooled difference in R2_oos, {ref} minus other ({cl}-clustered CI):")
        for k, v in res["pooled"]["diffs"].items():
            a, b = k.split("|")
            if ref in (a, b):
                sign = 1 if a == ref else -1
                lo, hi = sorted((sign * v["ci_lo"], sign * v["ci_hi"]))
                other = b if a == ref else a
                print(f"  {ref} - {other:14} {sign * v['diff_r2']:+.5f} [{lo:+.5f},{hi:+.5f}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=["e001"])
    ap.add_argument("--preset", required=True, choices=["e001_repro", "family_ablation"])
    ap.add_argument("--run-id")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=116)
    a = ap.parse_args()
    run_id = a.run_id or f"{a.dataset}-{a.preset}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    out_dir = OUT_ROOT / run_id
    if out_dir.exists():
        print(f"refusing to overwrite existing run {out_dir}", file=sys.stderr)
        return 2
    pairs = load_e001()
    base = next(s for s in compare.e001_models() if s.name == "B3")
    if a.preset == "e001_repro":
        specs, cluster = compare.e001_models(), "market_id"  # E001 clustered by market
        banner = "REPRODUCTION of frozen E001 (market-clustered, as registered)"
    else:
        specs = [compare.e001_models()[0], base, *compare.ablations(base, FAMILIES)]
        cluster = "event_id"
        banner = "DEVELOPMENT / post-hoc analysis on E001 data - NOT a registered experiment"
    res = compare.run_comparison(
        pairs,
        specs,
        cluster=cluster,
        n_boot=a.n_boot,
        seed=a.seed,
        manifest_path=E001_DIR / "manifest.json",
    )
    res["status"] = banner
    res["preset"] = a.preset
    res["no_edge_claim"] = True
    if a.preset == "e001_repro":
        res["repro_max_abs_diff_vs_e001_results"] = repro_diff(res)
    path = compare.write_new_json(out_dir, res)
    print_table(res, banner)
    print(f"\nwrote {path}")
    if a.preset == "e001_repro":
        d = res["repro_max_abs_diff_vs_e001_results"]
        print(f"max abs diff vs E001 results.json: {d:.3e} ({'OK' if d <= TOL else 'FAIL'})")
        return 0 if d <= TOL else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
