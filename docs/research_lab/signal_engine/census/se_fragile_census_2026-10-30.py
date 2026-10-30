"""Census for CH268 `fragile` (DESIGN_V1 section 38). Reads label availability states only (never a label's value).

Run on the host: PYTHONPATH=~/arepo/backend nice -n 19 ~/arepo/.venv/bin/python <this file>
"""
import sys
from collections import Counter, deque

import numpy as np
import pandas as pd
from astrolabe.signal_engine import config as C
from astrolabe.signal_engine import labels as L
from astrolabe.signal_engine import store as S

T, N_LAG = "dir_2h", 12
paths = S.Paths()
now = S.now_ts()
index = S.load_index(paths)
qc = L.QuoteCache(paths, index, keep=4)
hist: deque = deque(maxlen=N_LAG)  # unavailable flag (0/1) by market_id of the last 12 indexed origins with features
rows, states, n_elig, n_features = [], Counter(), 0, 0

for slot, m in sorted(index.items()):
    fp = paths.features(m["capture_id"])
    if not fp.exists():
        continue
    n_features += 1
    f = S.read_parquet(fp, ["market_id", "end_ts", "ms_mid", "ms_log_liq"])
    ids = f["market_id"].to_numpy(np.int64)
    e = (L.elig_mask(f, slot, S.epoch(m["started_utc"])) & C.ELIG_BITS[T]) > 0
    if len(hist) == N_LAG:  # the feature side at origin k: the 12 previous origins' 2 h labels all target <= k
        H = np.column_stack([s.reindex(ids).to_numpy() for s in hist])
        full = np.isfinite(H).all(axis=1)
        ok = e & full
        n_elig += int(e.sum())
        rows.append(np.column_stack([H[ok].mean(axis=1), f["ms_log_liq"].to_numpy(float)[ok]]))
    _y, st, _ = L.direction_labels(qc, index, slot, 2, ids, f["ms_mid"].to_numpy(np.float64), now)
    if (st[e] == L.PENDING).any():
        break  # the newest origin's target is not written yet: stop (it would enter no complete 12-origin window)
    states.update(L.LABEL_STATES[int(s)] for s in st[e])
    u = pd.Series((st[e] != L.LABELLED).astype(np.float64), index=ids[e])
    hist.append(u[~u.index.duplicated()])

if not rows:
    print("census: no data")
    sys.exit(1)
X = np.concatenate(rows)
fr, liq = X[:, 0], X[:, 1]
pos = float((fr > 0).mean())
fin = np.isfinite(liq)
c = float(np.corrcoef(fr[fin], liq[fin])[0, 1])
print(f"captures with features {n_features}; census rows {len(X):,} ({len(X) / max(n_elig, 1):.3f} of dir_2h-eligible rows after 12 origins)")
print(f"origin label states (eligible rows): {dict(states)}")
print(f"KILL LINE 1  share of rows with fr_unavail_12 > 0 = {pos:.4f}  [kill (hygiene only, no family) if < 0.05]")
print(f"KILL LINE 2  Pearson(fr_unavail_12, ms_log_liq) = {c:.4f}  [kill if |.| > 0.8]")
q = np.percentile(fr, [50, 90, 95, 99])
print(f"   info: fr_unavail_12 p50/p90/p95/p99 {q.round(4).tolist()}; share > 0.25 (display-pool rule) {(fr > 0.25).mean():.4f}")
verdict = "PASS (family may follow)" if (pos >= 0.05 and abs(c) <= 0.8) else "KILLED as a family"
print(f"reading as written: {verdict}; peak RSS {S.peak_rss_mb():.0f} MB")
