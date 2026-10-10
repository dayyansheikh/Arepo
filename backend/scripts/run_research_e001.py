"""Run E001: extract -> panel -> walk-forward evaluation.

Writes data-dumps/research_lab/e001/results.json (outputs only; sources are read-only).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import evaluate, extract, panel  # noqa: E402

DUMPS = ROOT / "data-dumps"
OUT = DUMPS / "research_lab" / "e001"


def _lam_summary(rows: list[dict]) -> dict:
    df = pd.DataFrame(rows)
    return {
        f"period_{p}": {
            "fits": int(len(g)),
            "lam_B2": sorted(set(g.lam_B2)),
            "lam_B3": sorted(set(g.lam_B3)),
            "inner": sorted(set(g.inner)),
            "n_train_range": [int(g.n_train.min()), int(g.n_train.max())],
        }
        for p, g in df.groupby("period")
    }


def main() -> None:
    t0 = time.time()
    captures = extract.discover_full_captures(DUMPS)
    if extract.manifest_matches(OUT, captures):
        print("extract: manifest matches, skipping extraction")
        manifest = json.loads((OUT / "manifest.json").read_text())
    else:
        print(f"extract: {len(captures)} full captures ...", flush=True)
        manifest = extract.extract(DUMPS, OUT)
        print(f"extract done in {manifest['extraction_seconds']}s, rows={manifest['total_rows']}")
    caps = [
        {"capture_id": c["capture_id"], "start_utc": c["start_utc"]} for c in manifest["captures"]
    ]
    snap = pd.read_csv(
        OUT / "snapshots.csv.gz", dtype={"market_id": str, "event_id": str, "capture_id": str}
    )
    pnl, counts = panel.build_panel(snap, caps)
    pairs = panel.usable(pnl)
    print(f"panel: {len(pnl)} eligible pairs, {len(pairs)} with target", flush=True)
    preds, diag = evaluate.walk_forward(pairs)
    summ = evaluate.summarise(preds)
    eff = evaluate.effective_sample(pnl, preds)
    results = {
        "experiment": "E001",
        "development_data_only": True,
        "no_edge_claim": True,
        "captures": caps,
        "eligibility_counts": counts,
        "effective_sample": eff,
        "excluded_insufficient_train": diag["excluded_insufficient_train"],
        "lambda_choice_summary": _lam_summary(diag["lambda_choice"]),
        "metrics": summ,
        "runtime_seconds": round(time.time() - t0, 1),
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=1, default=float))
    _print(results)


def _print(r: dict) -> None:
    print("\nEligibility / target counts per period")
    for c in r["eligibility_counts"]:
        print(
            {
                k: c[k]
                for k in (
                    "period",
                    "binary_rows",
                    "eligible",
                    "target_available",
                    "target_unavailable",
                    "missing_at_j",
                    "one_sided_or_closed_at_j",
                    "spread_field_vs_ask_minus_bid_mismatch",
                )
            }
        )
    print(
        "\nEffective sample:",
        json.dumps({k: v for k, v in r["effective_sample"].items() if k != "per_period"}),
    )
    for d in r["effective_sample"]["per_period"]:
        print("  ", d)
    print("excluded (insufficient purged train):", r["excluded_insufficient_train"])
    print("lambda:", json.dumps(r["lambda_choice_summary"]))
    hdr = (
        f"\n{'model':5} {'pooledR2':>9} {'pooledCI':>20}  {'per-period R2':<44} "
        f"{'spear':>7} {'dir':>6} {'MAE':>8}  label"
    )
    print(hdr)
    for m, v in r["metrics"].items():
        pp = " ".join(f"{d['r2_oos']:+.4f}" for d in v["per_period"])
        sp = [d["spearman"] for d in v["per_period"] if d["spearman"] == d["spearman"]]
        print(
            f"{m:5} {v['pooled_r2_oos']:+9.5f} "
            f"[{v['pooled_ci'][0]:+.4f},{v['pooled_ci'][1]:+.4f}]  {pp:<44} "
            f"{(sum(sp) / len(sp) if sp else float('nan')):7.4f} "
            f"{v['pooled_dir_acc']:6.3f} {v['pooled_mae']:8.5f}  {v['label']}"
        )
    print("\nPer-period detail (R2 [CI] spearman dir_acc):")
    for m, v in r["metrics"].items():
        if m == "B0":
            continue
        for d in v["per_period"]:
            print(
                f"  {m:4} p{d['period']} n={d['n']} R2={d['r2_oos']:+.4f} "
                f"[{d['ci_lo']:+.4f},{d['ci_hi']:+.4f}] "
                f"sp={d['spearman']:+.4f} dir={d['dir_acc']:.3f} "
                f"dir_zero_wrong={d['dir_acc_zero_wrong']:.3f} "
                f"(movers {d['n_movers']}, directional {d['n_movers_directional']})"
            )
    print("\nB0 per-period MAE:", [round(d["mae"], 5) for d in r["metrics"]["B0"]["per_period"]])
    print("runtime_seconds", r["runtime_seconds"])


if __name__ == "__main__":
    main()
