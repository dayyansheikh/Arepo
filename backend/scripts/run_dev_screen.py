"""DEVELOPMENT screening of six pre-listed reversal-moderation variants (NOT confirmation).

    python scripts/run_dev_screen.py --tag s1

Family and definitions: see ``astrolabe.research_lab.features_dev`` docstring (six variants).
Data: dev_snapshots_v2 (the six E001 captures plus neg-risk columns), event-clustered paired
bootstrap, E001 walk-forward protocol via ``compare.run_comparison``. Each variant is added to
the reversal-only base ('B1h' OLS, and 'B1h_r' = ridge on chg_1h alone so the add-one contrast
isolates the feature, not the estimator) and to B3. Every variant run is a new run directory
under data-dumps/research_lab/comparisons and one trial in docs/research_lab/trials.jsonl,
labelled DEVELOPMENT/post-hoc. These numbers are not evidence and carry no edge claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import (  # noqa: E402
    compare,
    e005,
    features_dev,
    panel,
    power,
    provenance,
)

DATA = ROOT / "data-dumps" / "research_lab" / "dev_snapshots_v2"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "comparisons"
LABEL = provenance.DEV_LABEL + " reversal-moderation screen"
REFS = {"B1h": "B1h", "B1h_r": "B1h_r", "B3": "B3"}


def load_dev() -> tuple[pd.DataFrame, list[dict]]:
    manifest = json.loads((DATA / "manifest.json").read_text())
    caps = [
        {"capture_id": c["capture_id"], "start_utc": c["start_utc"]} for c in manifest["captures"]
    ]
    snap = pd.read_csv(DATA / "snapshots.csv.gz", dtype=e005.ID_DTYPES)
    pnl, _ = panel.build_panel(snap, caps)
    pairs = panel.usable(pnl)
    by_cap = {cid: g for cid, g in snap.groupby("capture_id")}
    origin = {k: by_cap[c["capture_id"]] for k, c in enumerate(caps[:-1])}
    return features_dev.add_negrisk_columns(pairs, origin), caps


def specs_for(feats: tuple[str, ...]) -> list[compare.ModelSpec]:
    base = compare.e001_models()
    b0, b1h, b3 = base[0], base[2], base[4]
    return [
        b0,
        b1h,
        compare.ModelSpec("B1h_r", ("chg_1h",), "ridge"),
        b3,
        compare.ModelSpec("V_B1h", ("chg_1h", *feats), "ridge"),
        compare.ModelSpec("V_B3", (*b3.features, *feats), "ridge"),
    ]


def contrast(res: dict, ref: str, var: str) -> dict:
    """Pooled and per-period paired dR2 = R2(var) - R2(ref) with event-clustered CI."""

    def pick(block: dict) -> dict:
        d = block["diffs"][f"{ref}|{var}"]  # diff_r2 = R2_ref - R2_var -> flip sign
        return {"d": -d["diff_r2"], "lo": -d["ci_hi"], "hi": -d["ci_lo"]}

    pp = {int(p): pick(b)["d"] for p, b in sorted(res["per_period"].items())}
    out = pick(res["pooled"])
    vals = np.array(list(pp.values()))
    out.update(per_period=pp, n_pos=int((vals > 0).sum()), n_periods=len(vals))
    K = res["pooled"]["n_clusters"]
    sd_c = power.sd_from_ci(out["lo"], out["hi"], K)
    out["sd_c"] = sd_c
    out["mde_k"] = power.mde_delta_r2(K, sd_c, n_tests=2)
    out["clusters_for_0.005"] = power.required_clusters(0.005, sd_c, n_tests=2)
    out["clusters_for_0.01"] = power.required_clusters(0.01, sd_c, n_tests=2)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=116)
    a = ap.parse_args()
    pairs, _ = load_dev()
    print(f"pairs={len(pairs)} events={pairs['event_id'].nunique()}")
    table: dict[str, dict] = {}
    for vname, feats in features_dev.VARIANTS.items():
        run_id = f"devscreen-{a.tag}-{vname}"
        out_dir = OUT_ROOT / run_id
        if out_dir.exists():
            print(f"refusing to overwrite {out_dir}", file=sys.stderr)
            return 2
        try:
            res = compare.run_comparison(
                pairs,
                specs_for(feats),
                cluster="event_id",
                n_boot=a.n_boot,
                seed=a.seed,
                manifest_path=DATA / "manifest.json",
            )
        except Exception as exc:
            provenance.append_trial(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "run_id": run_id,
                    "dataset": "dev_snapshots_v2",
                    "preset": vname,
                    "label": LABEL,
                }
            )
            raise
        res.update(status="DEVELOPMENT screening - not evidence", variant=vname, no_edge_claim=True)
        path = compare.write_new_json(out_dir, res)
        provenance.append_trial(
            {
                "status": "ok",
                "dataset": "dev_snapshots_v2",
                "preset": vname,
                "run_id": run_id,
                "label": LABEL,
                "result_path": str(path.relative_to(ROOT)),
                "results_sha256": provenance.sha256_file(path),
                "summary": provenance.summarize_pooled(res),
                "provenance": res["provenance_v2"],
            }
        )
        table[vname] = {
            "run_id": run_id,
            "features": list(feats),
            "pooled_r2": {m: v["r2_oos"] for m, v in res["pooled"]["models"].items()},
            "n": res["pooled"]["n"],
            "n_clusters": res["pooled"]["n_clusters"],
            "vs_B1h": contrast(res, "B1h", "V_B1h"),
            "vs_B1h_r": contrast(res, "B1h_r", "V_B1h"),
            "vs_B3": contrast(res, "B3", "V_B3"),
        }
    summ = {"label": LABEL, "n_variants": len(table), "table": table, "no_edge_claim": True}
    sp = compare.write_new_json(OUT_ROOT / f"devscreen-{a.tag}-summary", summ)
    print(f"summary {sp}")
    print_table(table)
    return 0


def print_table(table: dict) -> None:
    print("\nDEVELOPMENT screening - not evidence. dR2 = R2(var) - R2(ref), event-clustered 95% CI")
    for ref in ("vs_B1h", "vs_B1h_r", "vs_B3"):
        print(f"\n[{ref}]")
        rows = sorted(table.items(), key=lambda kv: -kv[1][ref]["lo"])
        for v, t in rows:
            c = t[ref]
            per = " ".join(f"{x:+.4f}" for x in c["per_period"].values())
            print(
                f"{v:20} {c['d']:+.5f} [{c['lo']:+.5f},{c['hi']:+.5f}] pos {c['n_pos']}/"
                f"{c['n_periods']} per {per} MDE(K)={c['mde_k']:.4f}"
            )


if __name__ == "__main__":
    raise SystemExit(main())
