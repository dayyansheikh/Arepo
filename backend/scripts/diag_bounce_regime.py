# ruff: noqa: E501
"""SB2-J4 regime-toggle diagnostic (engineering check, NOT a test: logs no trials, writes one JSON).

q0031 showed the J4 P1 slope is almost entirely between-market (market-FE slope -0.011 vs pooled -0.207;
market-demeaned placebo -0.003). Candidate mechanism: rows require origin i to be E001-eligible (spread
<= 0.10, mid in [0.02, 0.98]) but h and j only two-sided, so a market that toggles between a tight state
and a wide-spread state with a different mid gives d_bm and dmid opposite signs regardless of timing.
This script reports plain OLS point estimates of P1, P1x, P2, P3, P4 (J4 specs) under:
  pooled | market FE | rows with h and j also "tight" (same rule as i) | tight + market FE,
the matching within-market permuted placebo for each, and the share of rows with h or j wide.

    python scripts/diag_bounce_regime.py --out ../data-dumps/research_lab/bounce_decomp/diag_regime_q0032.json --until-utc 2026-10-15T21:00:00Z
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    import numpy as np
    import pandas as pd

    from astrolabe.research_lab import bounce_decomp as bd
    from astrolabe.research_lab import panel

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=117)
    ap.add_argument("--until-utc", default=None)
    a = ap.parse_args()
    if a.out.exists():
        print(f"refusing to overwrite {a.out}", file=sys.stderr)
        return 2

    df, _ = bd.build_snapshot_triples(bd.SNAPSHOT_ROOT, bd.SWEEP_ROOT, a.until_utc, log=None)
    codes = pd.factorize(df["market_id"])[0]
    perm = bd.permute_snapshot_targets(df, a.seed)

    def tight(bid, ask):
        bid, ask = np.asarray(bid, float), np.asarray(ask, float)
        mid = (bid + ask) / 2
        with np.errstate(invalid="ignore"):
            return (bid > 0) & (bid < ask) & (ask < 1) & (ask - bid <= panel.SPREAD_MAX) & (mid >= panel.MID_LO) & (mid <= panel.MID_HI)

    t_h = tight(df["bid_h"], df["ask_h"])
    t_j = tight(df["bid_j"], df["ask_j"])
    both = t_h & t_j

    def fit(d, name, mask, fe):
        sp = bd.J4_SPEC[name]
        m = bd._rows_for(d, name) & mask
        scale = 100.0 if name == "P2" else 1.0
        y = d[sp["target"]].to_numpy(float)[m] * scale
        x = d[sp["term"]].to_numpy(float)[m]
        Z = d[list(sp["controls"])].to_numpy(float)[m].reshape(int(m.sum()), -1)
        if m.sum() < 100:
            return None
        if fe:
            c = codes[m]

            def dm(v):
                return v - pd.Series(v).groupby(c).transform("mean").to_numpy()
            y, x = dm(y), dm(x)
            Z = np.column_stack([dm(Z[:, k]) for k in range(Z.shape[1])]) if Z.shape[1] else Z
        return {"beta": bd._plain_ols(y, x, Z)["coef"][1], "n": int(m.sum())}

    allm = np.ones(len(df), bool)
    out = {"n_rows": int(len(df)), "share_h_wide": float((~t_h).mean()), "share_j_wide": float((~t_j).mean()),
           "share_h_or_j_wide": float((~both).mean()), "tests": {}}
    wide_h = ~t_h & np.isfinite(df["mid_h"].to_numpy(float))
    out["mean_abs_dbm_h_wide"] = float(np.nanmean(np.abs(df["d_bm"].to_numpy(float)[wide_h]))) if wide_h.any() else None
    out["mean_abs_dbm_h_tight"] = float(np.nanmean(np.abs(df["d_bm"].to_numpy(float)[t_h])))
    for name in bd.J4_SPEC:
        r = {}
        for lab, mask in (("all", allm), ("tight_hj", both)):
            for fe in (False, True):
                k = f"{lab}{'_fe' if fe else ''}"
                r[k] = {"real": fit(df, name, mask, fe), "placebo": fit(perm, name, mask, fe)}
        out["tests"][name] = r
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
