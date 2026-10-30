"""Census for the `umaparams` aux family (DESIGN_V1 section 42; CH207). Counts only.

Reads the engine's features (eligible rows: market_id, category, ms_log_liq) of the newest capture and the gamma_rules
stream known at that capture's start. No label, prediction, price change or outcome is read.
Kill and keep lines (fixed in section 42 before this run):
  family killed if up_has == 1 on < 5% of the capture's eligible rows;
  a 0/1 column is kept iff its minority value holds >= 2% and >= 200 of the covered rows;
  up_log_bond / up_log_reward are kept iff >= 2% and >= 200 covered rows differ from the modal value;
  family killed if no value column is kept.
up_resolver_top is scored here from the raw resolvedBy counts (the top address is pinned in code after this run).
Information only (cannot change a line): non-sports / sports coverage, value counts, the top 5 resolvedBy addresses,
each kept flag by category, corr with ms_log_liq and with section 41's rc_occur_by.
Run on the host: PYTHONPATH=~/arepo/backend nice -n 19 ~/arepo/.venv/bin/python <this file> <path to uma_params.py>
"""
import importlib.util
import json
import sys
from collections import Counter

import numpy as np
from astrolabe.signal_engine import config as C
from astrolabe.signal_engine import rules_text as R
from astrolabe.signal_engine import store as S

if len(sys.argv) > 1:  # the committed module, before it is deployed
    spec = importlib.util.spec_from_file_location("astrolabe.signal_engine.uma_params", sys.argv[1])
    U = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = U
    spec.loader.exec_module(U)
else:
    from astrolabe.signal_engine import uma_params as U

paths = S.Paths()
print(f"run start {S.iso(S.now_ts())}; uma_params sha256 {U.code_sha256()}", flush=True)
root = C.DUMPS / "stream_gamma_rules"
index = S.load_index(paths)
m = index[max(index)]
cid, t0 = m["capture_id"], S.epoch(m["started_utc"])
f = S.read_parquet(paths.features(cid), ["market_id", "category", "ms_log_liq"])
res = U.uma_at(root, t0)
known = res["known"]
print(f"capture {cid} start {m['started_utc']}; eligible rows {len(f)}; stream files read {len(res['files'])} "
      f"({res['files'][0] if res['files'] else None}..{res['files'][-1] if res['files'] else None}); last slot {res['last_slot']}; "
      f"markets with a known row {len(known)}")
ids = f["market_id"].to_numpy(np.int64)
cat = f["category"].astype(str).to_numpy()
has = np.array([i in known for i in ids])
sports = np.char.lower(cat.astype(str)) == "sports"
share = float(has.mean()) if len(has) else 0.0
print(f"up_has share: all {share:.4f}; non-sports {has[~sports].mean():.4f} (n {int((~sports).sum())}); "
      f"sports {has[sports].mean() if sports.any() else float('nan'):.4f} (n {int(sports.sum())})")
fam_ok = share >= 0.05
print(f"FAMILY coverage {'PASSES' if fam_ok else 'KILLED'} (line: up_has share >= 0.05)")
# raw field values known at t0 (same clock as uma_at: a row counts iff its slot's poll finished at or before t0)
raw: dict[int, dict] = {}
for name in res["files"]:
    polls, rows = {}, []
    with open(root / name, encoding="utf-8") as fh:
        for line in fh:
            if '"kind":"hash"' in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "poll" and r.get("ok") and r.get("slot"):
                polls[r["slot"]] = S.epoch(r.get("finished_utc"))
            elif r.get("kind") == "row" and str(r.get("key", "")).startswith("m:") and isinstance(r.get("data"), dict):
                d = r["data"]
                rows.append((r.get("slot"), int(r["key"][2:]), {k: d.get(k) for k in ("umaBond", "umaReward", "customLiveness", "hasReviewedDates", "fallbackResolutionType", "resolvedBy")}))
    ok = {s for s, ts in polls.items() if ts <= t0}
    for slot, mid, d in rows:
        if slot in ok:
            raw[mid] = d
cov = [int(i) for i in ids[has]]
n_cov = len(cov)
print(f"covered eligible rows {n_cov}; raw rows matched {sum(1 for i in cov if i in raw)}")
for k in ("umaBond", "umaReward", "customLiveness", "hasReviewedDates", "fallbackResolutionType"):
    print(f"  {k}: {dict(Counter(str(raw.get(i, {}).get(k)) for i in cov).most_common(8))}")
addr = Counter(str(raw.get(i, {}).get("resolvedBy")).lower() for i in cov)
print(f"  resolvedBy top 5: {addr.most_common(5)}")
top = addr.most_common(1)[0][0] if addr else ""
print(f"RESOLVER_TOP candidate (pin in code): {top}")
X = np.array([known[i] for i in cov], float) if n_cov else np.zeros((0, len(U.VALUE_COLUMNS)))
j_top = U.VALUE_COLUMNS.index("up_resolver_top")
X[:, j_top] = [float(str(raw.get(i, {}).get("resolvedBy")).lower() == top) if isinstance(raw.get(i, {}).get("resolvedBy"), str) and raw[i]["resolvedBy"] else np.nan for i in cov]
keep = []
for j, c in enumerate(U.VALUE_COLUMNS):
    v = X[:, j]
    fin = np.isfinite(v)
    if c in ("up_log_bond", "up_log_reward"):
        vals = Counter(np.round(v[fin], 6))
        mode_n = vals.most_common(1)[0][1] if vals else 0
        off = int(fin.sum()) - mode_n
        ok = off >= 0.02 * n_cov and off >= 200
        print(f"  {c}: non-NaN {fin.mean():.4f}; off-mode rows {off} ({off / max(n_cov, 1):.4f}) -> {'keep' if ok else 'DROP'}")
    else:
        ones = int(np.nansum(v))
        minority = min(ones, int(fin.sum()) - ones)
        ok = minority >= 0.02 * n_cov and minority >= 200
        print(f"  {c}: non-NaN {fin.mean():.4f}; share 1 {np.nanmean(v) if fin.any() else float('nan'):.4f}; minority rows {minority} -> {'keep' if ok else 'DROP'}")
    if ok:
        keep.append(c)
fam_ok = fam_ok and bool(keep)
print(f"KEPT {['up_has'] + keep}; FAMILY {'PASSES' if fam_ok else 'KILLED'}")
for c in keep:
    v = X[:, U.VALUE_COLUMNS.index(c)]
    cc = cat[has]
    by = {k: (round(float(np.nanmean(v[cc == k])), 3), int((cc == k).sum())) for k in sorted(set(cc)) if (cc == k).sum() >= 200}
    print(f"  {c} by category (mean, n): {by}")
liq = f["ms_log_liq"].to_numpy(float)
fin = np.isfinite(liq)
print(f"corr(up_has, ms_log_liq) {np.corrcoef(has[fin].astype(float), liq[fin])[0, 1]:.3f}")
rres = R.rules_at(root, t0)["known"]
occ = np.array([rres.get(i, [np.nan] * len(R.TEXT_COLUMNS))[R.TEXT_COLUMNS.index("rc_occur_by")] for i in cov], float)
for c in keep:
    v = X[:, U.VALUE_COLUMNS.index(c)]
    ok2 = np.isfinite(v) & np.isfinite(occ)
    r = np.corrcoef(v[ok2], occ[ok2])[0, 1] if ok2.sum() > 2 and np.std(v[ok2]) > 0 else float("nan")
    print(f"  corr({c}, rc_occur_by) {r:.3f} (n {int(ok2.sum())})")
print(f"run end {S.iso(S.now_ts())}")
