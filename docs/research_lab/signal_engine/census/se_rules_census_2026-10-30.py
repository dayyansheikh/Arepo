# ruff: noqa: E501
"""Census for the `rules` aux family (DESIGN_V1 section 41; CH267 class levels + CH239 text columns). Counts only.

Reads the engine's features (eligible rows: market_id, category, ms_log_liq) of the newest capture and the
gamma_rules stream known at that capture's start. No label, prediction, price change or outcome is read.
Kill and keep lines (fixed in section 41 before this run):
  family killed if rc_has == 1 on < 5% of the capture's eligible rows;
  a 0/1 column is kept iff it is 1 on >= 5% and <= 95% of the covered rows;
  a count / length column is kept iff it is non-NaN on >= 10% of the covered rows (CH239's line) and not constant.
Information only (cannot change a line): non-sports and sports coverage, the CH267 class split, each flag by
category, the rc_has / ms_log_liq correlation, and a seeded sample of 40 covered texts for a hand precision audit.
Run on the host: PYTHONPATH=~/arepo/backend nice -n 19 ~/arepo/.venv/bin/python <this file>
"""
import json
import random
from collections import Counter

import numpy as np

from astrolabe.signal_engine import config as C
from astrolabe.signal_engine import rules_text as R
from astrolabe.signal_engine import store as S

paths = S.Paths()
print(f"run start {S.iso(S.now_ts())}; rules_text sha256 {R.code_sha256()}", flush=True)
root = C.DUMPS / "stream_gamma_rules"
index = S.load_index(paths)
m = index[max(index)]
cid, t0 = m["capture_id"], S.epoch(m["started_utc"])
f = S.read_parquet(paths.features(cid), ["market_id", "category", "ms_log_liq"])
res = R.rules_at(root, t0)
known = res["known"]
print(f"capture {cid} start {m['started_utc']}; eligible rows {len(f)}; stream files read {len(res['files'])} "
      f"({res['files'][0] if res['files'] else None}..{res['files'][-1] if res['files'] else None}); last slot {res['last_slot']}; "
      f"markets with a known row {len(known)}")
ids = f["market_id"].to_numpy(np.int64)
cat = f["category"].astype(str).to_numpy()
has = np.array([i in known for i in ids])
sports = np.char.lower(cat.astype(str)) == "sports"
share = float(has.mean()) if len(has) else 0.0
print(f"rc_has share: all {share:.4f}; non-sports {has[~sports].mean():.4f} (n {int((~sports).sum())}); "
      f"sports {has[sports].mean() if sports.any() else float('nan'):.4f} (n {int(sports.sum())})")
print(f"FAMILY {'KILLED' if share < 0.05 else 'PASSES'} (line: rc_has share >= 0.05)")
X = np.array([known[i] for i in ids[has]], float) if has.any() else np.zeros((0, len(R.TEXT_COLUMNS)))
keep = []
for j, c in enumerate(R.TEXT_COLUMNS):
    v = X[:, j]
    fin = np.isfinite(v)
    if c in ("rc_n_hosts", "rc_log_len"):
        ok = fin.mean() >= 0.10 and np.nanstd(v) > 0
        print(f"  {c}: non-NaN {fin.mean():.4f}; mean {np.nanmean(v):.3f}; sd {np.nanstd(v):.3f}; dist {dict(Counter(np.round(v[fin], 0).astype(int)).most_common(6))} -> {'keep' if ok else 'DROP'}")
    else:
        p1 = float(np.nanmean(v))
        ok = 0.05 <= p1 <= 0.95
        print(f"  {c}: share 1 {p1:.4f} -> {'keep' if ok else 'DROP'}")
    if ok:
        keep.append(c)
print(f"KEPT {['rc_has'] + keep}")
s, b, cns = (X[:, R.TEXT_COLUMNS.index(c)] > 0 for c in ("cl_sched", "cl_barrier", "cl_consensus"))
cls = np.where(s & ~b, "scheduled", np.where(b & ~s, "barrier", np.where(s & b, "both", np.where(cns, "consensus", "other"))))
print(f"CH267 class split (covered rows): {dict(Counter(cls))}")
ns = ~sports[has]
print(f"CH267 class split (covered non-sports rows): {dict(Counter(cls[ns]))}")
for c in ("cl_sched", "cl_barrier", "cl_consensus", "rc_inclusive", "rc_numeric"):
    v = X[:, R.TEXT_COLUMNS.index(c)]
    by = {k: (round(float(v[cat[has] == k].mean()), 3), int((cat[has] == k).sum())) for k in sorted(set(cat[has])) if (cat[has] == k).sum() >= 200}
    print(f"  {c} by category (share, n): {by}")
liq = f["ms_log_liq"].to_numpy(float)
fin = np.isfinite(liq)
print(f"corr(rc_has, ms_log_liq) {np.corrcoef(has[fin].astype(float), liq[fin])[0, 1]:.3f}")
# hand audit sample: raw text of 40 covered markets (seeded), read from the newest known row
rng = random.Random(20261030)
pick = set(rng.sample(sorted(int(i) for i in ids[has]), min(40, int(has.sum()))))
txt = {}
for name in res["files"]:
    with open(root / name, encoding="utf-8") as fh:
        for line in fh:
            if '"kind":"row"' not in line or '"key":"m:' not in line:
                continue
            r = json.loads(line)
            mid = int(r["key"][2:])
            if mid in pick:
                txt[mid] = r["data"]
print("AUDIT SAMPLE (market_id | class | inclusive numeric | question | description head)")
for mid in sorted(pick):
    d = txt.get(mid, {})
    cols = known[mid]
    c = "scheduled" if cols[0] and not cols[1] else "barrier" if cols[1] and not cols[0] else "both" if cols[0] else "consensus" if cols[2] else "other"
    print(f"{mid} | {c} | {int(cols[3])} {int(cols[4])} | {str(d.get('question'))[:110]} | {str(d.get('description')).replace(chr(10), ' ')[:220]}")
print(f"run end {S.iso(S.now_ts())}")
