"""Gate probe for `rsrev` (DESIGN_V1 section 39): se1's 2 h residual lag-1 autocorrelation. Same rules as section 37's census.

Reads realised 2 h labels (the residual needs them); prints two numbers and their kill lines, nothing else is scored.
Run on the host: PYTHONPATH=~/arepo/backend nice -n 19 ~/arepo/.venv/bin/python <this file>
"""
import math
import sys
import warnings
from collections import defaultdict

import numpy as np
import pandas as pd
from astrolabe.signal_engine import config as C
from astrolabe.signal_engine import labels as L
from astrolabe.signal_engine import predict as P
from astrolabe.signal_engine import store as S

warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN lag rows give NaN by design
CHAMP, T, M6_MIN, B = "se1_lgbm_mm", "dir_2h", 4, 400
paths = S.Paths()
now = S.now_ts()
print(f"run start {S.iso(now)}; model {CHAMP}", flush=True)
index = S.load_index(paths)
log = P.prediction_log(paths)
qc = L.QuoteCache(paths, index, keep=4)
resid: dict[int, pd.Series] = {}  # slot -> residual by market_id (dir_2h-eligible, labelled, on-time rows only)
pairs = []  # (market_id, r_prev, r_now)
m6_rows = []  # (rs_2h_m6, mo_chg_1d, rs_2h_l1, mo_d2h)
n_elig_k, n_m6_k, skipped = 0, 0, defaultdict(int)

for slot, m in sorted(index.items()):
    cid = m["capture_id"]
    pp = paths.predictions(cid, CHAMP)
    fp = paths.features(cid)
    if not (pp.exists() and fp.exists()):
        skipped["no_prediction_or_features"] += 1
        continue
    if (cid, CHAMP) not in log:
        skipped["unlogged"] += 1
        continue
    f = S.read_parquet(fp, ["market_id", "end_ts", "ms_mid", "mo_chg_1d", "mo_d2h", "ms_spread"])
    pf = S.read_parquet(pp, [f"{T}_dn", f"{T}_up"])
    md = S.parquet_meta(pp)
    fsha = m.get("features_sha256")
    if len(pf) != len(f) or (fsha and md.get("features_sha256") != fsha):
        skipped["sha_mismatch"] += 1
        continue
    start = S.epoch(m["started_utc"])
    ids = f["market_id"].to_numpy(np.int64)
    e = (L.elig_mask(f, slot, start) & C.ELIG_BITS[T]) > 0
    # the feature side at this origin: lags k-1..k-6 of residuals already known here (labels of k-j at k - j + 1 <= k)
    lags = [resid.get(slot - j) for j in range(1, 7)]
    have = [s for s in lags if s is not None]
    if have:
        R = np.column_stack([(s.reindex(ids).to_numpy() if s is not None else np.full(len(ids), np.nan)) for s in lags])
        cnt = np.isfinite(R).sum(axis=1)
        with np.errstate(invalid="ignore"):
            m6 = np.where(cnt >= M6_MIN, np.nanmean(R, axis=1), np.nan)
        l1 = R[:, 0]
        ok = e & np.isfinite(m6) & np.isfinite(f["mo_chg_1d"].to_numpy(float))
        n_elig_k += int(e.sum())
        n_m6_k += int((e & np.isfinite(m6)).sum())
        m6_rows.append(np.column_stack([m6[ok], f["mo_chg_1d"].to_numpy(float)[ok], l1[ok], f["mo_d2h"].to_numpy(float)[ok]]))
    # the outcome side of this origin: its own residual (label at k + 1), on-time predictions only (the scorer's rule)
    y, st, _ = L.direction_labels(qc, index, slot, 2, ids, f["ms_mid"].to_numpy(np.float64), now)
    on_time = S.epoch(log[(cid, CHAMP)]["written_utc"]) < S.slot_time(slot + L.horizon_slots(2))
    v = e & (st == L.LABELLED) & on_time
    if not v.any():
        skipped["no_labelled_rows"] += 1
        continue
    p = P.dequantise_dir(pf[f"{T}_dn"].to_numpy()[v], pf[f"{T}_up"].to_numpy()[v])
    r = pd.Series((y[v].astype(np.float64) - 1.0) - (p[:, 2] - p[:, 0]), index=ids[v])
    r = r[~r.index.duplicated()]
    prev = resid.get(slot - 1)
    if prev is not None:
        j = pd.concat([prev.rename("a"), r.rename("b")], axis=1, join="inner")
        fk = f.drop_duplicates("market_id").set_index("market_id").reindex(j.index)
        pairs.append(pd.DataFrame({"m": j.index.to_numpy(np.int64), "a": j["a"].to_numpy(), "b": j["b"].to_numpy(),
                                   "d2h": fk["mo_d2h"].to_numpy(float), "spr": fk["ms_spread"].to_numpy(float)}))
    resid[slot] = r
    for old in [s for s in resid if s < slot - 6]:
        del resid[old]

if not pairs or not m6_rows:
    print("census: no data", dict(skipped))
    sys.exit(1)
pr = pd.concat(pairs, ignore_index=True)
ac = float(np.corrcoef(pr["a"], pr["b"])[0, 1])
# information only: market-demeaned pairs and a market-clustered bootstrap CI of the pooled Pearson
dm = pr.groupby("m")[["a", "b"]].transform("mean")
ac_dm = float(np.corrcoef(pr["a"] - dm["a"], pr["b"] - dm["b"])[0, 1])
g = pr.assign(aa=pr.a * pr.a, bb=pr.b * pr.b, ab=pr.a * pr.b, n=1.0).groupby("m")[["a", "b", "aa", "bb", "ab", "n"]].sum().to_numpy()
rng = np.random.default_rng(265)
boot = []
for _ in range(B):
    s = g[rng.integers(0, len(g), len(g))].sum(axis=0)
    a, b, aa, bb, ab, n = s
    boot.append((ab / n - a / n * b / n) / math.sqrt((aa / n - (a / n) ** 2) * (bb / n - (b / n) ** 2)))
lo, hi = np.percentile(boot, [2.5, 97.5])
X = np.concatenate(m6_rows)
c_m6 = float(np.corrcoef(X[:, 0], X[:, 1])[0, 1])
fin = np.isfinite(X[:, 2]) & np.isfinite(X[:, 3])
c_l1 = float(np.corrcoef(X[fin, 2], X[fin, 3])[0, 1])

print(f"census window: slots {min(index)}..{max(index)}; skipped captures {dict(skipped)}")
print(f"lag-1 pairs: {len(pr):,} over {pr['m'].nunique():,} markets")
print(f"GATE  lag-1 residual autocorrelation (pooled Pearson) = {ac:.4f}  [rsrev gate met if <= -0.02]")
print(f"   info: market-clustered bootstrap 95% CI [{lo:.4f}, {hi:.4f}] (B={B}); market-demeaned Pearson {ac_dm:.4f}")
print(f"rs_2h_m6 rows: {len(X):,}; coverage of dir_2h-eligible rows with >= {M6_MIN} of 6 lags: {n_m6_k / max(n_elig_k, 1):.3f}")
print(f"   info: Pearson(rs_2h_m6, mo_chg_1d) = {c_m6:.4f}")
print(f"   info: Pearson(rs_2h_l1, mo_d2h) = {c_l1:.4f} over {int(fin.sum()):,} rows")
# information only: partial correlation on mo_d2h at k, and the pooled Pearson by ms_spread tercile at k
q = pr.dropna(subset=["d2h", "spr"])
Z = np.column_stack([np.ones(len(q)), q["d2h"].to_numpy()])
ra = q["a"].to_numpy() - Z @ np.linalg.lstsq(Z, q["a"].to_numpy(), rcond=None)[0]
rb = q["b"].to_numpy() - Z @ np.linalg.lstsq(Z, q["b"].to_numpy(), rcond=None)[0]
print(f"   info: partial Pearson given mo_d2h at k {float(np.corrcoef(ra, rb)[0, 1]):.4f} over {len(q):,} pairs")
cuts = np.quantile(q["spr"], [1 / 3, 2 / 3])
for name, sel in (("low", q["spr"] <= cuts[0]), ("mid", (q["spr"] > cuts[0]) & (q["spr"] <= cuts[1])), ("high", q["spr"] > cuts[1])):
    print(f"   info: spread tercile {name}: Pearson {float(np.corrcoef(q.a[sel], q.b[sel])[0, 1]):.4f} n {int(sel.sum()):,}")
verdict = "GATE MET (a rsrev builder section may follow, after review)" if ac <= -0.02 else "GATE NOT MET (rsrev not built)"
print(f"gate as written (pooled lag-1 <= -0.02): {verdict}; peak RSS {S.peak_rss_mb():.0f} MB")
