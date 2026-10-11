"""DEVELOPMENT cross-market lead/lag screen over all complete snapshots (NOT evidence).

    python scripts/run_leadlag_screen.py [--tag T] [--n-boot N]

Builds E001-semantics pairs over dev_snapshots_v2 + research_lab/snapshots (complete only; one or
two snapshots in memory at a time), runs the pre-listed family in
``astrolabe.research_lab.leadlag_screen`` on (a) all periods and (b) the periods where the
neg-risk columns allow L3, and writes data-dumps/research_lab/leadlag_screen/<run_id>/results.json
(refuses to overwrite). One trial per family member and configuration is appended to
docs/research_lab/trials.jsonl. Read-only on snapshots; no network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))



def print_table(ls, name: str, res: dict) -> None:
    e = res["effective_sample"]
    print(f"\n=== {name}: {res['status']} ===")
    print(f"pairs={e['pairs']} markets={e['markets']} clusters={e['events_clusters']} "
          f"periods={e['periods']} test_rows={e.get('test_rows')} "
          f"test_clusters={e.get('test_clusters')} test_periods={e.get('test_periods')}")
    print(f"share_no_sibling={e['share_no_sibling']:.3f} share_l3_in_group="
          f"{e['share_l3_in_group']:.3f} corr(L1,chg_1h)={e['corr_l1_chg1h']} "
          f"corr(L1,dmid)={e['corr_l1_dmid']}")
    print("base vs B0:", json.dumps(ls.clean({m: v["r2_oos"] for m, v in
                                              res["base_vs_B0"].items()})))
    print("R vs B3 (diff R2):", json.dumps(ls.clean(res["R_vs_B3"])))
    for n, v in res["variants"].items():
        d = v["pooled_vs_R"]
        per = " ".join(f"{x:+.5f}" for x in v["per_period_vs_R"].values())
        mde = v.get("mde")
        print(f"{n}: dR2 vs R {d['diff_r2']:+.5f} [{d['ci_lo']:+.5f},{d['ci_hi']:+.5f}] "
              f"MDE={'n/a' if mde is None else f'{mde:.5f}'} pos {v['n_positive_periods']}/"
              f"{v['n_periods']} rule={v['meets_drafting_rule']}\n    per-period {per}")
    print("recommendation:", json.dumps(res["recommendation"]))


def main() -> int:
    from astrolabe.research_lab import leadlag_screen as ls
    from astrolabe.research_lab import provenance

    ap = argparse.ArgumentParser()
    ap.add_argument("--tag")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=116)
    a = ap.parse_args()
    pairs, counts = ls.build_all(log=print)
    if not len(pairs):
        print("no pairs; nothing run")
        return 0
    key = json.dumps([(c["capture_i"], c["capture_j"]) for c in counts])
    run_id = f"leadlag-{a.tag or hashlib.sha256(key.encode()).hexdigest()[:10]}"
    out_dir = ls.OUT_ROOT / run_id
    if out_dir.exists():
        print(f"refusing to overwrite {out_dir}", file=sys.stderr)
        return 2
    configs = {"all_periods": pairs}
    nr_periods = sorted(pairs.loc[pairs["nr_data"], "period"].unique())
    if nr_periods:
        configs["neg_risk_periods"] = pairs[pairs["period"].isin(nr_periods)].reset_index(
            drop=True)
    results = {}
    for cname, frame in configs.items():
        print(f"\nrunning {cname}: {len(frame)} pairs", flush=True)
        results[cname] = ls.run_screen(frame, a.n_boot, a.seed)
    prov = provenance.run_provenance()
    doc = {"run_id": run_id, "seed": a.seed, "n_boot": a.n_boot, "pairing_counts": counts,
           "configs": results, "provenance": prov}
    out_dir.mkdir(parents=True, exist_ok=False)
    path = out_dir / "results.json"
    path.write_text(json.dumps(ls.clean(doc), indent=1))
    sha = provenance.sha256_file(path)
    for cname, res in results.items():
        for name, v in res["variants"].items():
            provenance.append_trial({
                "status": "ok", "dataset": "dev_snapshots_v2+snapshots",
                "preset": f"{name}:{cname}",
                "run_id": run_id, "label": ls.LABEL, "kind": "leadlag_screen",
                "result_path": str(path.relative_to(ROOT)), "results_sha256": sha,
                "summary": ls.clean({"pooled_vs_R": v["pooled_vs_R"],
                                     "share_positive_periods": v["share_positive_periods"],
                                     "mde": v.get("mde"),
                                     "meets_drafting_rule": v["meets_drafting_rule"]}),
                "provenance": prov,
            })
    print(f"results {path}")
    for cname, res in results.items():
        print_table(ls, cname, res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
