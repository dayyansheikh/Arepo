"""Break-even table from the latest complete book sweep + its snapshot (memory-light, read-only).

Usage: python scripts/execution_cost_breakeven.py [sweep_dir]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from astrolabe.research_lab import economics as ec

ROOT = Path(__file__).resolve().parents[2] / "data-dumps" / "research_lab"


def main() -> None:
    sweeps = sorted(p for p in (ROOT / "book_sweeps").iterdir()
                    if (p / "manifest.json").exists()
                    and json.loads((p / "manifest.json").read_text()).get("state") == "complete")
    sd = Path(sys.argv[1]) if len(sys.argv) > 1 else sweeps[-1]
    snap = ROOT / "snapshots" / json.loads((sd / "manifest.json").read_text())["snapshot_id"]
    sw = pd.read_csv(sd / "rows.csv.gz", dtype={"token_id": str, "market_id": str})
    ext = pd.read_csv(snap / "rows_ext.csv.gz", dtype=str,
                      usecols=["market_id", "fee_category", "fee_schedule", "fees_enabled"])
    rows = pd.read_csv(snap / "rows.csv.gz", dtype={"market_id": str},
                       usecols=["market_id", "liquidity"])
    ext = ext.drop_duplicates("market_id")
    rows = rows.drop_duplicates("market_id")
    d = sw.merge(ext, on="market_id", how="left").merge(rows, on="market_id", how="left")
    d["fees_enabled"] = pd.to_numeric(d["fees_enabled"], errors="coerce")
    t = ec.breakeven_table(d)
    t["state"] = d["state"].to_numpy()
    n2 = int((d.state == "two_sided").sum())
    print(f"sweep {sd.name} snapshot {snap.name} n={len(t)} two_sided={n2} "
          f"fillable={int(t['ok'].sum())}")
    print("fee_flag:", t["fee_flag"].value_counts(dropna=False).to_dict())
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    for by in ("price_band", "liq_band", "fee_category"):
        print(ec.regime_summary(t, by).to_string(index=False))
    ok = t[t["ok"]]
    print("overall", ok["cost_ps"].describe(percentiles=[.25, .5, .75, .9]).to_dict())
    print("share cost<=0.02:", (ok.cost_ps <= .02).mean(), " <=0.03:", (ok.cost_ps <= .03).mean(),
          " <=0.05:", (ok.cost_ps <= .05).mean())
    print(ec.regime_summary(t.assign(pl=t.price_band.astype(str) + "|" + t.liq_band.astype(str)),
                            "pl").sort_values("cost_med").head(12).to_string(index=False))


if __name__ == "__main__":
    main()
