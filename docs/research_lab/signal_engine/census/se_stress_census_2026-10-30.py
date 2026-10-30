"""Counts-only census for CH258 `stress` (DESIGN_V1 section 35). Reads only engine files; no outcome is read."""
import gzip, json, math
from pathlib import Path
import numpy as np
import pandas as pd

R = Path.home() / "arepo/data-dumps/research_lab/signal_engine"
files = sorted((R / "aux_inputs/crypto").glob("*.json.gz"))
seen = {"BTCUSDT": {}, "ETHUSDT": {}}  # open_ms -> close, strictly from files of earlier-or-same captures
conflicts, out = 0, []


def rv_last(d, cap_ms, n=60, min_n=50):
    ks = sorted(k for k in d if k + 60_000 <= cap_ms)[-(n + 1):]
    c = np.array([d[k] for k in ks]); r = np.diff(np.log(c)) if len(c) > 1 else np.array([])
    r = r[np.isfinite(r)]
    return float(np.sqrt((r ** 2).sum())) if len(r) >= min_n else math.nan


for p in files:
    doc = json.loads(gzip.decompress(p.read_bytes()))
    cid = doc["capture_id"]
    cap_ms = int(pd.Timestamp(doc["cap_start_utc"]).timestamp() * 1000)
    for s in seen:
        for o, _op, c in ((doc["klines"].get(s) or {}).get("1m", [])):
            if o + 60_000 > cap_ms:
                continue
            if o in seen[s] and seen[s][o] != c:
                conflicts += 1
            seen[s].setdefault(o, c)
    b = seen["BTCUSDT"]
    rv1 = rv_last(b, cap_ms)
    lo = cap_ms - 7 * 86_400_000
    ks = np.array(sorted(k for k in b if lo <= k and k + 60_000 <= cap_ms), dtype=np.int64)
    c = np.array([b[k] for k in ks])
    consec = np.diff(ks) == 60_000
    r = np.diff(np.log(c))[consec] if len(c) > 1 else np.array([])
    n = int(len(r))
    base = float(np.sqrt((r ** 2).sum() * 60.0 / n)) if n else math.nan
    fac, n_nc = math.nan, 0
    fp, ap = R / "features" / f"{cid}.parquet", R / "aux/crypto" / f"{cid}.parquet"
    if fp.exists() and ap.exists():
        f = pd.read_parquet(fp, columns=["market_id", "mo_d2h"])
        a = pd.read_parquet(ap)
        if "market_id" in a.columns:
            a = a.set_index("market_id")["cr_has"].reindex(f["market_id"]).to_numpy()
        else:
            a = a["cr_has"].to_numpy()
        m = (a == 0) & np.isfinite(f["mo_d2h"].to_numpy(float))
        n_nc = int(m.sum())
        fac = float(np.abs(f["mo_d2h"].to_numpy(float)[m]).mean()) if n_nc else math.nan
    out.append({"cid": cid, "rv1h": rv1, "eth_rv1h": rv_last(seen["ETHUSDT"], cap_ms), "base_n": n, "base": base,
                "ratio": rv1 / base if base else math.nan, "factor": fac, "n_noncrypto": n_nc})

d = pd.DataFrame(out)
ok = (d["base_n"] >= 0.9 * 10_080) & d["rv1h"].notna() & d["factor"].notna()
c = d[ok]
res = {"files": len(files), "kline_conflicts": conflicts, "census_slots": int(ok.sum()),
       "first": c["cid"].iloc[0] if len(c) else None, "last": c["cid"].iloc[-1] if len(c) else None,
       "days": round(len(c) / 12, 2), "stress_slots": int((c["ratio"] >= 2).sum()),
       "ratio_q": [round(float(x), 3) for x in c["ratio"].quantile([0.5, 0.9, 0.99, 1.0])],
       "ratio_ge_1_5": int((c["ratio"] >= 1.5).sum()),
       "pearson_rv1h_factor": round(float(c["rv1h"].corr(c["factor"])), 4),
       "spearman_rv1h_factor_info": round(float(c["rv1h"].corr(c["factor"], method="spearman")), 4),
       "median_noncrypto_rows": int(c["n_noncrypto"].median()) if len(c) else 0,
       "stress_cids": c.loc[c["ratio"] >= 2, "cid"].tolist()}
print("SE_STRESS_CENSUS " + json.dumps(res))
