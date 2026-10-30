"""Census for the `ruleedit` aux family (DESIGN_V1 section 43; CH228 + CH187's end-date moves). Counts only.

Reads the engine's features (eligible rows: market_id, category, ms_log_liq, ms_hours_to_end) of the newest capture and
the gamma_rules stream known at that capture's start. No label, prediction, price change or outcome is read.
Kill and keep lines (fixed in section 43 before this run), over the covered rows (a known m: row):
  re_text_7d kept iff its 1s hold >= 0.5% and >= 100 of the covered rows; re_text_age is kept iff re_text_7d is;
  re_end_7d / re_end_age: the same line;
  re_end_later kept iff re_end_7d is kept and its minority value holds >= 10% and >= 50 of the covered rows with a
  finite re_end_later;
  family killed if neither re_text_7d nor re_end_7d is kept, or if covered rows < 5% of eligible rows.
Information only (cannot change a line): edit counts over the stream, the 7-day shares by category, the age quartiles,
corr of each kept column with ms_log_liq and ms_hours_to_end, and the overlap of the two 7-day flags.
Run on the host: PYTHONPATH=~/arepo/backend nice -n 19 ~/arepo/.venv/bin/python <this file> <path to rule_edits.py>
"""
import importlib.util
import sys

import numpy as np
from astrolabe.signal_engine import config as C
from astrolabe.signal_engine import store as S

if len(sys.argv) > 1:  # the committed module, before it is deployed
    spec = importlib.util.spec_from_file_location("astrolabe.signal_engine.rule_edits", sys.argv[1])
    R = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = R
    spec.loader.exec_module(R)
else:
    from astrolabe.signal_engine import rule_edits as R

paths = S.Paths()
print(f"run start {S.iso(S.now_ts())}; rule_edits sha256 {R.code_sha256()}", flush=True)
root = C.DUMPS / "stream_gamma_rules"
index = S.load_index(paths)
m = index[max(index)]
cid, t0 = m["capture_id"], S.epoch(m["started_utc"])
f = S.read_parquet(paths.features(cid), ["market_id", "category", "ms_log_liq", "ms_hours_to_end"])
res = R.edits_at(root, t0)
known = res["known"]
print(f"capture {cid} start {m['started_utc']}; eligible rows {len(f)}; stream files read {len(res['files'])} "
      f"({res['files'][0] if res['files'] else None}..{res['files'][-1] if res['files'] else None}); last slot {res['last_slot']}; "
      f"markets with a known row {len(known)}; edits over the stream: market text {res['n_text_m']}, event text "
      f"{res['n_text_e']}, market endDate {res['n_end']}")
ids = f["market_id"].to_numpy(np.int64)
cat = f["category"].astype(str).to_numpy()
has = np.array([int(i) in known for i in ids])
n_cov = int(has.sum())
cov_share = n_cov / max(len(ids), 1)
sports = np.char.lower(cat.astype(str)) == "sports"
print(f"covered rows {n_cov} ({cov_share:.4f}); non-sports {has[~sports].mean():.4f}, sports "
      f"{has[sports].mean() if sports.any() else float('nan'):.4f}")
X = np.array([R.edit_columns(known[int(i)], t0) for i in ids[has]], float) if n_cov else np.zeros((0, len(R.RE_COLUMNS)))
col = {c: X[:, j] for j, c in enumerate(R.RE_COLUMNS)}
keep = []
for flag, age in (("re_text_7d", "re_text_age"), ("re_end_7d", "re_end_age")):
    ones = int(np.nansum(col[flag]))
    ok = ones >= 0.005 * n_cov and ones >= 100
    ages = np.expm1(col[age][np.isfinite(col[age])])
    q = np.percentile(ages, [25, 50, 75]).round(1).tolist() if len(ages) else []
    print(f"  {flag}: ones {ones} ({ones / max(n_cov, 1):.4f}) -> {'keep' if ok else 'DROP'}; any known edit "
          f"{len(ages)}; age h quartiles {q}")
    if ok:
        keep += [flag, age]
lat = col["re_end_later"]
fin = np.isfinite(lat)
if "re_end_7d" in keep:
    later = int(np.nansum(lat))
    minority = min(later, int(fin.sum()) - later)
    ok = minority >= 0.10 * max(int(fin.sum()), 1) and minority >= 50
    print(f"  re_end_later: finite {int(fin.sum())}; later {later}; minority {minority} -> {'keep' if ok else 'DROP'}")
    if ok:
        keep.append("re_end_later")
fam_ok = cov_share >= 0.05 and ("re_text_7d" in keep or "re_end_7d" in keep)
print(f"KEPT {keep}; FAMILY {'PASSES' if fam_ok else 'KILLED'}")
cc = cat[has]
for c in ("re_text_7d", "re_end_7d"):
    by = {k: (round(float(np.nanmean(col[c][cc == k])), 4), int((cc == k).sum())) for k in sorted(set(cc)) if (cc == k).sum() >= 200}
    print(f"  {c} by category (share, n): {by}")
both = int(np.nansum(col["re_text_7d"] * col["re_end_7d"]))
print(f"  both 7-day flags: {both}")
for other in ("ms_log_liq", "ms_hours_to_end"):
    o = f[other].to_numpy(float)[has]
    for c in keep:
        v = col[c]
        ok2 = np.isfinite(v) & np.isfinite(o)
        r = np.corrcoef(v[ok2], o[ok2])[0, 1] if ok2.sum() > 2 and np.std(v[ok2]) > 0 and np.std(o[ok2]) > 0 else float("nan")
        print(f"  corr({c}, {other}) {r:.3f} (n {int(ok2.sum())})")
print(f"run end {S.iso(S.now_ts())}")
