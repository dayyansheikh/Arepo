"""Exploratory demo: trentmkelly/polymarket_historical_data (CC BY 4.0, rev 122205f) -> AREPO pairs.

Development data only. Reuses backend/astrolabe/research_lab compare/features unchanged; registers
history-derived features IN MEMORY (repo untouched). Run with the backend venv python, -I, and
argv: <repo_backend_dir> <pylib_dir> <tk_dir> <out_json>.
"""
import sys

BACKEND, PYLIB, TK, OUT = sys.argv[1:5]
sys.path[:0] = [PYLIB, BACKEND]

import glob, json, os  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
from astrolabe.research_lab import compare, features  # noqa: E402
from astrolabe.research_lab.features import FeatureSpec, register  # noqa: E402

H, TOL, D = 3600.0, 1200.0, 86400.0
files = sorted(glob.glob(os.path.join(TK, "*.parquet")))
cols = ["market_id", "asset_id", "outcome", "collected_at", "source_timestamp",
        "source_latency_ms", "best_bid", "best_ask", "bids_json", "asks_json"]
parts = []
for f in files:
    t = pq.read_table(f, columns=cols).to_pandas()
    t["run"] = os.path.basename(f)
    parts.append(t)
raw = pd.concat(parts, ignore_index=True)
del parts

# one token per market, fixed rule: lexicographically smallest asset_id
keep = raw.groupby("market_id")["asset_id"].transform("min") == raw["asset_id"]
s = raw[keep].copy()
s["t"] = pd.to_datetime(s["collected_at"], utc=True).astype("int64") / 1e9
s["t_src"] = pd.to_numeric(s["source_timestamp"]) / 1e3
s = s.sort_values(["asset_id", "t"]).reset_index(drop=True)
bb, ba = s["best_bid"].astype(float), s["best_ask"].astype(float)
s["two_sided"] = (bb > 0) & (ba > bb) & (ba < 1)
s["mid"] = np.where(s["two_sided"], (bb + ba) / 2, np.nan)
s["spread_v"] = ba - bb


def depth(js, best, side):
    lv = json.loads(js) if isinstance(js, str) else []
    if side == "b":
        return sum(x["size"] for x in lv if x["price"] >= best - 0.05)
    return sum(x["size"] for x in lv if x["price"] <= best + 0.05)


s["bid_depth"] = [depth(j, b, "b") for j, b in zip(s["bids_json"], bb)]
s["ask_depth"] = [depth(j, a, "a") for j, a in zip(s["asks_json"], ba)]
s = s.drop(columns=["bids_json", "asks_json"])

diag = {
    "files": len(files), "rows_raw": int(len(raw)), "markets_total": int(raw["market_id"].nunique()),
    "markets_per_run_median": float(raw.groupby("run")["market_id"].nunique().median()),
    "crossed_or_onesided_share": float(1 - s["two_sided"].mean()),
    "recv_minus_exchange_s_p50_p99_max": [float(x) for x in
        np.nanpercentile(s["t"] - s["t_src"], [50, 99, 100])],
    "run_gap_minutes_p50_max": [float(x) for x in
        np.percentile(np.diff(np.sort(s.groupby("run")["t"].min().to_numpy())) / 60, [50, 100])],
}
del raw


def at_offset(g_t, g_mid, t0, off, forward):
    """mid at first snapshot >= t0+off (forward) or last <= t0-off (back), within TOL."""
    if forward:
        k = np.searchsorted(g_t, t0 + off, side="left")
        ok = (k < len(g_t))
        kk = np.minimum(k, len(g_t) - 1)
        ok &= g_t[kk] <= t0 + off + TOL
    else:
        k = np.searchsorted(g_t, t0 - off, side="right") - 1
        ok = k >= 0
        kk = np.maximum(k, 0)
        ok &= g_t[kk] >= t0 - off - TOL
    return np.where(ok, g_mid[kk], np.nan), np.where(ok, g_t[kk], np.nan)


rows = []
for aid, g in s.groupby("asset_id", sort=False):
    gt, gm = g["t"].to_numpy(), g["mid"].to_numpy()
    mj, tj = at_offset(gt, gm, gt, H, True)
    m1h, _ = at_offset(gt, gm, gt, H, False)
    m15, _ = at_offset(gt, gm, gt, 900.0, False)
    m1d, _ = at_offset(gt, gm, gt, D, False)
    gg = g.assign(mid_j=mj, t_j=tj, mid_1h=m1h, mid_15m=m15, mid_1d=m1d)
    rows.append(gg)
p = pd.concat(rows, ignore_index=True)

elig = p["two_sided"] & (p["spread_v"] <= 0.10) & p["mid"].between(0.02, 0.98)
n_elig = int(elig.sum())
p = p[elig].copy()
tgt_ok = p["mid_j"].notna()
diag.update({"origins_eligible": n_elig, "target_unavailable": int((~tgt_ok).sum())})
p = p[tgt_ok].copy()

p["t_i"] = p["t"]
p["dmid"] = p["mid_j"] - p["mid"]
p["horizon_h"] = (p["t_j"] - p["t_i"]) / 3600
p["period"] = (p["t_i"] // D).astype(int)
p["period"] -= p["period"].min()
p["event_id"] = p["market_id"]  # no event id in source; market clustering (understates dependence)
p["mid"] = p["mid"]
p["spread"] = p["spread_v"]
for name, ref in (("h_chg_1h", "mid_1h"), ("h_chg_1d", "mid_1d")):
    p[name + "_missing"] = p[ref].isna().astype(float)
    p[name] = (p["mid"] - p[ref]).fillna(0.0)
p["h_skip_1h_15m"] = (p["mid_15m"] - p["mid_1h"]).fillna(0.0)
p["h_skip_missing"] = (p["mid_15m"].isna() | p["mid_1h"].isna()).astype(float)

hist = [("h_chg_1h", "momentum"), ("h_chg_1h_missing", "momentum"), ("h_chg_1d", "momentum"),
        ("h_chg_1d_missing", "momentum"), ("h_skip_1h_15m", "momentum"),
        ("h_skip_missing", "momentum")]
for n, fam in hist:
    register(FeatureSpec(n, fam, "hist-tk-v0", lambda o, n=n: o[n], (n,)))

M = compare.ModelSpec
specs = [
    M("B0", (), "zero"),
    M("B1h_hist", ("h_chg_1h",), "ols_origin"),
    M("B1skip", ("h_skip_1h_15m",), "ols_origin"),
    M("B2_hist", ("mid", "spread", "h_chg_1h", "h_chg_1h_missing", "h_chg_1d",
                  "h_chg_1d_missing"), "ridge"),
    M("B2_hist_book", ("mid", "spread", "h_chg_1h", "h_chg_1h_missing", "h_chg_1d",
                       "h_chg_1d_missing", "book_imbalance"), "ridge"),
]
cols_keep = ["market_id", "event_id", "asset_id", "period", "t_i", "t_j", "dmid", "horizon_h",
             "mid", "spread", "bid_depth", "ask_depth"] + [n for n, _ in hist]
pairs = p[cols_keep].reset_index(drop=True)
res = compare.run_comparison(pairs, specs, cluster="event_id")
res["diagnostics"] = diag
res["sample"] = {"pairs": int(len(pairs)), "markets": int(pairs["market_id"].nunique()),
                 "periods": int(pairs["period"].nunique()),
                 "horizon_h_p5_p95": [float(x) for x in np.percentile(pairs["horizon_h"], [5, 95])]}
with open(OUT, "w") as fh:
    json.dump(res, fh, indent=1, default=str)
print(json.dumps({"diag": diag, "sample": res["sample"], "pooled": res["pooled"]}, indent=1,
                 default=str)[:6000])
