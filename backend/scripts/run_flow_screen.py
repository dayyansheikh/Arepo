"""DEVELOPMENT flow screen over all available trade samples (NOT evidence).

    python scripts/run_flow_screen.py [--tag T]

Pairs each complete trade sample with the next complete snapshot, runs the pre-listed family in
``astrolabe.research_lab.flow_screen`` and writes data-dumps/research_lab/flow_screen/<run_id>/
results.json (refuses to overwrite). One trial per family member is appended to
docs/research_lab/trials.jsonl labelled 'DEVELOPMENT flow screen'. Read-only on snapshots and
trade samples; no network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from astrolabe.research_lab import flow_screen as fs  # noqa: E402
from astrolabe.research_lab import provenance  # noqa: E402


def run_id_for(counts: list[dict], tag: str | None) -> str:
    key = json.dumps([(c["sample_id"], c.get("target_snapshot")) for c in counts])
    return f"flowscreen-{tag or hashlib.sha256(key.encode()).hexdigest()[:10]}"


def print_table(res: dict) -> None:
    e = res["effective_sample"]
    print(f"\n{res['status']}. {e['note']}")
    print(f"pairs={e['pairs']} markets={e['markets']} events={e['events']} "
          f"periods={e['sample_periods']} median_horizon_h={e['median_horizon_h']:.2f} "
          f"share_dmid_zero={e['share_zero_dmid']:.3f}")
    print("base R2 vs no-change:", json.dumps(fs.clean(res["base_r2_vs_B0"])))
    print("dR2 = R2(variant) - R2(base); event-clustered 95% CI; MDE at n_tests="
          f"{res['n_tests_for_mde']}")
    for ref in ("vs_frozen", "vs_ridge"):
        print(f"\n[{ref}]")
        for name, v in res["variants"].items():
            for mode in ("weighted", "unweighted"):
                b = v[ref][mode]
                per = " ".join(f"{x:+.5f}" for x in b["per_period"].values())
                mde = b.get("mde")
                print(f"{name:22} {mode:10} {b['delta_r2']:+.5f} "
                      f"[{b['ci_lo']:+.5f},{b['ci_hi']:+.5f}] "
                      f"MDE={'n/a' if mde is None else f'{mde:.5f}'} per-period {per}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=116)
    a = ap.parse_args()
    pairs, counts = fs.build_all()
    for c in counts:
        print(json.dumps(fs.clean(c)))
    ok = len(pairs) >= fs.MIN_PAIRS and len(set(fs.event_keys(pairs))) >= fs.MIN_EVENTS if len(
        pairs) else False
    if not ok:
        print("no pairable samples" if not len(pairs) else
              f"insufficient pairs/events ({len(pairs)} pairs); nothing run")
        return 0
    run_id = run_id_for(counts, a.tag)
    out_dir = fs.OUT_ROOT / run_id
    if out_dir.exists():
        print(f"refusing to overwrite {out_dir}", file=sys.stderr)
        return 2
    res = fs.run_screen(pairs, a.n_boot, a.seed)
    res.update(run_id=run_id, pairing_counts=counts, seed=a.seed, n_boot=a.n_boot,
               provenance=provenance.run_provenance())
    out_dir.mkdir(parents=True, exist_ok=False)
    path = out_dir / "results.json"
    path.write_text(json.dumps(fs.clean(res), indent=1))
    sha = provenance.sha256_file(path)
    for name, v in res["variants"].items():
        provenance.append_trial({
            "status": "ok", "dataset": "trade_samples+snapshots", "preset": name,
            "run_id": run_id, "label": fs.LABEL, "kind": "flow_screen",
            "result_path": str(path.relative_to(ROOT)), "results_sha256": sha,
            "summary": fs.clean({k: {m: {x: v[k][m][x] for x in ("delta_r2", "ci_lo", "ci_hi")}
                                     for m in ("weighted", "unweighted")}
                                 for k in ("vs_frozen", "vs_ridge")}),
            "provenance": res["provenance"],
        })
    print(f"results {path}")
    print_table(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
