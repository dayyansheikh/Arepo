# ruff: noqa: E501
"""SB2-J4 placebo diagnostic (engineering check, NOT a test: logs no trials, writes one JSON).

The q0006 permuted-target placebo reproduced P1 (beta -0.20 vs -0.21). This script rebuilds the same
triples and asks why, using plain OLS point estimates only:
  - share of rows the within-market permutation leaves in place, and rows-per-market distribution;
  - P1/P1x slopes: real, placebo, placebo with market-demeaned y and x, placebo on markets with
    >= 10 rows, and a placebo with a per-market cyclic shift by half the market's rows (never a
    neighbouring triple);
  - real P1 with market fixed effects (descriptive).

    python scripts/diag_bounce_placebo.py --out ../data-dumps/research_lab/bounce_decomp/diag_placebo.json
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

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=117)  # q0006 placebo used seed 116 + 1
    ap.add_argument("--until-utc", default=None)
    a = ap.parse_args()
    if a.out.exists():
        print(f"refusing to overwrite {a.out}", file=sys.stderr)
        return 2

    df, _ = bd.build_snapshot_triples(bd.SNAPSHOT_ROOT, bd.SWEEP_ROOT, a.until_utc, log=None)
    codes = pd.factorize(df["market_id"])[0]
    idx = bd._within_perm(codes, a.seed)
    n_per = np.bincount(codes)
    rows_n = n_per[codes]

    def slope(y, x, Z=None, m=None):
        y, x = np.asarray(y, float), np.asarray(x, float)
        Z = np.empty((len(y), 0)) if Z is None else np.asarray(Z, float).reshape(len(y), -1)
        ok = np.isfinite(y) & np.isfinite(x) & np.isfinite(Z).all(1)
        if m is not None:
            ok &= m
        if ok.sum() < 50:
            return None
        return {"beta": bd._plain_ols(y[ok], x[ok], Z[ok])["coef"][1], "n": int(ok.sum())}

    def demean(v):
        v = np.asarray(v, float)
        s = pd.Series(v).groupby(codes).transform("mean").to_numpy()
        return v - s

    # cyclic half-shift within market, rows ordered by period
    order = np.lexsort((df["period"].to_numpy(), codes))
    shift = np.empty(len(df), np.int64)
    start = 0
    for n in n_per[codes[order][np.r_[0, np.flatnonzero(np.diff(codes[order])) + 1]]]:
        blk = order[start:start + n]
        shift[blk] = np.roll(blk, -(n // 2)) if n >= 2 else blk
        start += n

    out = {"n_rows": int(len(df)), "n_markets": int(len(n_per)),
           "rows_per_market_quantiles": {q: float(np.quantile(n_per, q)) for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
           "share_rows_market_n1": float((rows_n == 1).mean()),
           "share_rows_perm_identity": float((idx == np.arange(len(df))).mean()),
           "share_rows_shift_identity": float((shift == np.arange(len(df))).mean()),
           "tests": {}}
    big = rows_n >= 10
    for name, tgt in (("P1", "dmid"), ("P1x", "y_p1x")):
        y, x = df[tgt].to_numpy(float), df["d_bm"].to_numpy(float)
        Z = df["spread"].to_numpy(float)
        yp, ys = y[idx], y[shift]
        out["tests"][name] = {
            "real": slope(y, x, Z), "placebo_perm": slope(yp, x, Z),
            "placebo_perm_demeaned": slope(demean(yp), demean(x),
                                           m=np.isfinite(yp) & np.isfinite(x)),
            "placebo_perm_markets_ge10": slope(yp, x, Z, big),
            "placebo_halfshift": slope(ys, x, Z),
            "real_market_fe": slope(demean(y), demean(x),
                                    m=np.isfinite(y) & np.isfinite(x)),
            "corr_target_with_neg_dbm_same_market_mean": None,
        }
        # market-level: mean target vs mean d_bm across markets (cross-sectional channel)
        g = pd.DataFrame({"c": codes, "y": y, "x": x}).dropna().groupby("c").mean()
        out["tests"][name]["corr_target_with_neg_dbm_same_market_mean"] = float(np.corrcoef(g["y"], -g["x"])[0, 1])
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1))
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
