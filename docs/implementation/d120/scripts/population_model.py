"""Read-only: per-member availability/trigger model for the D118 frame population.

Inputs: scratch d118_frame.csv.gz (from build_frame_table.py), research-lab book sweeps and the
nearest complete snapshot. Output: scratch members.parquet-like CSV with a_i, p_i, group, category.
Design figures only.
"""
import gzip
import json
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/DayyanSheikh/Projects/astrolabe")
LAB = REPO / "data-dumps" / "research_lab"
SCR = Path(sys.argv[1])
SWEEPS = sys.argv[2].split(",")  # sweep ids
SNAP = sys.argv[3]  # snapshot id for availability proxy


def dec(v):
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def trig(b, a):
    b, a = dec(b), dec(a)
    if b is None or a is None or b <= 0 or a <= 0:
        return None
    return int(3 * abs(b - a) >= b + a)


frame = pd.read_csv(SCR / "d118_frame.csv.gz", dtype=str, keep_default_na=False)
frame["eligible_pl"] = frame["eligible_pl"].astype(int)
frame["frame_ok"] = frame["frame_ok"].astype(int)

# --- category from feeType (declared mapping candidate, v1) ---
def category(fee):
    if not fee:
        return "unknown"
    f = fee.lower()
    for prefix, name in (("sports", "sports"), ("crypto", "crypto"), ("finance", "finance"),
                         ("politics", "politics"), ("weather", "weather"),
                         ("economics", "economics"), ("culture", "culture"), ("tech", "tech"),
                         ("mentions", "mentions"), ("geopolitics", "geopolitics")):
        if f.startswith(prefix):
            return name
    return "other:" + fee


frame["category"] = frame["fee_type"].map(category)

# --- dependence group: union of event_id and negRiskMarketID (union-find) ---
parent = {}


def find(x):
    while parent.setdefault(x, x) != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


for mid, ev, nr in frame[["market_id", "event_id", "nr_id"]].itertuples(index=False):
    node = "m:" + mid
    find(node)
    if ev:
        union("e:" + ev, node)
    if nr:
        union("n:" + nr, node)
frame["group"] = ["g:" + find("m:" + m) for m in frame["market_id"]]

# --- sweeps: per token counts of two-sided books and triggered books; and state counts ---
per = defaultdict(lambda: [0, 0, 0])  # n_books_seen, n_two_sided_valid, n_triggered
pair_states = defaultdict(list)  # token -> list of (sweep_idx, trig or None)
for idx, sid in enumerate(SWEEPS):
    path = LAB / "book_sweeps" / sid / "rows.csv.gz"
    df = pd.read_csv(path, usecols=["token_id", "state", "bid_size_1", "ask_size_1"], dtype=str,
                     keep_default_na=False)
    for tok, st, b, a in df[["token_id", "state", "bid_size_1", "ask_size_1"]].itertuples(
            index=False):
        rec = per[tok]
        rec[0] += 1
        t = trig(b, a) if st == "two_sided" else None
        if t is not None:
            rec[1] += 1
            rec[2] += t
        pair_states[tok].append((idx, t))
    del df

snap = pd.read_csv(LAB / "snapshots" / SNAP / "rows.csv.gz",
                   usecols=["market_id", "best_bid", "best_ask", "volume24hr"],
                   dtype={"market_id": str})
bid, ask = snap["best_bid"], snap["best_ask"]
two = (bid.notna() & ask.notna() & (bid > 0) & (ask < 1) & (bid < ask)).to_numpy()
snap_two = dict(zip(snap["market_id"].to_numpy(), two, strict=True))
vol = dict(zip(snap["market_id"].to_numpy(), snap["volume24hr"].fillna(0).to_numpy(), strict=True))
del snap

p0_mask = (frame["frame_ok"] == 1) & frame["excl"].isin(
    ["", "frame_gamma_liquidity_below_1000", "frame_gamma_liquidity_missing_or_invalid"])
el = frame[p0_mask].copy()
seen = np.array([per[t][0] if t in per else 0 for t in el["token0"]])
nts = np.array([per[t][1] if t in per else 0 for t in el["token0"]])
ntr = np.array([per[t][2] if t in per else 0 for t in el["token0"]])
el["sweep_seen"], el["sweep_two"], el["sweep_trig"] = seen, nts, ntr
el["snap_two"] = pd.Series([float(snap_two[m]) if m in snap_two else np.nan
                            for m in el["market_id"]], index=el.index, dtype=float)
el["vol24"] = [vol.get(m, np.nan) for m in el["market_id"]]
# availability: own sweep two-sided share when seen, else snapshot proxy, else band rate
band_av = el[el["snap_two"].notna()].groupby("lband")["snap_two"].mean().to_dict()
a = np.where(seen > 0, nts / np.maximum(seen, 1),
             np.where(el["snap_two"].notna(), el["snap_two"].fillna(0.0),
                      el["lband"].map(band_av).fillna(0.0)))
# trigger probability: Jeffreys own-sweep posterior mean, else pooled rate of liquidity band
band = el.assign(n=nts, k=ntr).groupby("lband")[["n", "k"]].sum()
band_rate = ((band["k"] + 0.5) / (band["n"] + 1)).to_dict()
pooled = ntr.sum() / max(nts.sum(), 1)
p = np.where(nts > 0, (ntr + 0.5) / (nts + 1), el["lband"].map(band_rate).fillna(pooled))
el["a"], el["p"] = a, p
el["p_src"] = np.where(nts > 0, "own", "band")
el["a_src"] = np.where(seen > 0, "sweep", np.where(el["snap_two"].notna(), "snapshot", "band"))
keep = ["market_id", "token0", "eligible_pl", "close_bin", "pband", "lband", "category", "fee_type",
        "sports_type", "event_id", "nr_id", "series_slug", "group", "a", "p", "a_src", "p_src",
        "sweep_seen", "sweep_two", "sweep_trig", "vol24", "game_start", "question"]
el[keep].to_csv(SCR / "members_p0.csv.gz", index=False)

# persistence within a sweep series (sweeps passed as adjacent pairs 0-1, 2-3, ... ~80 s apart)
flip = stay = 0
t_to_u = t_total = 0
for tok, lst in pair_states.items():
    d = dict(lst)
    for i in range(0, len(SWEEPS) - 1, 2):
        if d.get(i) is not None and d.get(i + 1) is not None:
            if d[i] == d[i + 1]:
                stay += 1
            else:
                flip += 1
            if d[i] == 1:
                t_total += 1
                t_to_u += d[i + 1] == 0
pl = el["eligible_pl"].to_numpy() == 1
summary = {
    "frame_rows": int(len(frame)), "eligible_p0": int(len(el)), "eligible_pl": int(pl.sum()),
    "mean_a_pl": round(float(a[pl].mean()), 4),
    "mean_p_given_available_pl": round(float((a[pl] * p[pl]).sum() / a[pl].sum()), 4),
    "pooled_trigger_rate_two_sided": round(float(pooled), 4),
    "band_trigger_rate": {k: round(v, 4) for k, v in band_rate.items()},
    "band_availability_snapshot": {k: round(float(v), 4) for k, v in band_av.items()},
    "a_src": el["a_src"].value_counts().to_dict(), "p_src": el["p_src"].value_counts().to_dict(),
    "mean_a": round(float(a.mean()), 4), "mean_p_given_available": round(float(
        (a * p).sum() / a.sum()), 4),
    "within_series_state_pairs_80s": {"same": stay, "flipped": flip,
                                      "flip_rate": round(flip / max(stay + flip, 1), 4),
                                      "P_untriggered_next_given_triggered": round(
                                          t_to_u / max(t_total, 1), 4)},
    "sweeps": SWEEPS, "snapshot": SNAP,
}
print(json.dumps(summary, indent=1))
