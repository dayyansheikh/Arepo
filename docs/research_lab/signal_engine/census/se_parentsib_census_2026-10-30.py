"""Census for the `parentsib` aux family (DESIGN_V1 section 45; CH237). Counts only.

Reads the newest capture's engine features (market_id, category), its rows.csv.gz and rows_ext.csv.gz, and the previous
slot's engine quotes: exactly the builder's inputs. No label, prediction or outcome is read; the 2 h sibling moves are
feature values (counted for coverage and the moving share only).
Kill and keep lines (fixed in section 45 before this run):
  family killed if ps_has_parent == 1 on < 5% of the non-sports eligible rows (CH237's line);
  family killed if ps_sib_d2h is finite on < 2% of all eligible rows or on < 200 rows (the parent factor is the idea);
  ps_sib_moving kept iff its value is > 0 on >= 200 rows (else it leaves the column list).
Information only: parents and child-event counts, the share of parent rows with >= 2 child events seen, rows lost to
the clock, coverage by category, the sidecar versions of the last 12 captures, corr(ps_sib_d2h, ev_sib_d2h).
Run on the host: PYTHONPATH=~/arepo/backend nice -n 19 ~/arepo/.venv/bin/python <this file> <path to parent_sib.py>
"""
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from astrolabe.signal_engine import aux as A
from astrolabe.signal_engine import features as F
from astrolabe.signal_engine import store as S

if len(sys.argv) > 1:  # the committed module, before it is deployed
    spec = importlib.util.spec_from_file_location("astrolabe.signal_engine.parent_sib", sys.argv[1])
    P = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = P
    spec.loader.exec_module(P)
else:
    from astrolabe.signal_engine import parent_sib as P

paths = S.Paths()
print(f"run start {S.iso(S.now_ts())}; parent_sib sha256 {P.code_sha256()}", flush=True)
index = S.load_index(paths)
slots = sorted(index)
k = slots[-1]
m = index[k]
cid = m["capture_id"]
cap_dir = Path(paths.snapshots) / cid
f = S.read_parquet(paths.features(cid), ["market_id", "category"])
rows = F.read_rows(cap_dir)
prev = index.get(k - 1)
prev_mid = F.mid_series(S.read_parquet(paths.quotes(prev["capture_id"]), ["market_id", "bid", "ask", "st"])) if prev else None
ext = P.read_parent_ext(cap_dir)
print(f"capture {cid}; eligible rows {len(f)}; previous slot capture {prev['capture_id'] if prev else None}; "
      f"sidecar v3 columns {'present' if ext is not None else 'ABSENT'}")
for s in slots[-12:]:
    try:
        v = json.loads((Path(paths.snapshots) / index[s]["capture_id"] / "ext_manifest.json").read_text()).get("version")
    except (OSError, ValueError):
        v = None
    print(f"  sidecar {index[s]['capture_id']}: {v}")
out = P.parentsib_features(rows, f, prev_mid, ext)
cat = f["category"].astype(str).to_numpy()
sports = np.char.lower(cat.astype(str)) == "sports"
hp = out["ps_has_parent"].to_numpy(float)
print(f"ps_has_parent: known {np.isfinite(hp).mean():.4f}; share 1 all {np.nansum(hp) / len(hp):.4f}; non-sports "
      f"{np.nansum(hp[~sports]) / max((~sports).sum(), 1):.4f} (n {int((~sports).sum())}); sports "
      f"{np.nansum(hp[sports]) / max(sports.sum(), 1):.4f}")
line1 = np.nansum(hp[~sports]) / max((~sports).sum(), 1) >= 0.05
d = out["ps_sib_d2h"].to_numpy(float)
nd = int(np.isfinite(d).sum())
line2 = nd >= 0.02 * len(d) and nd >= 200
mv = out["ps_sib_moving"].to_numpy(float)
keep_mv = int((mv > 0).sum()) >= 200
print(f"ps_sib_d2h finite {nd} ({nd / max(len(d), 1):.4f}); ps_sib_moving > 0 on {int((mv > 0).sum())} -> "
      f"{'keep' if keep_mv else 'DROP'}")
fam = line1 and line2
print(f"FAMILY {'PASSES' if fam else 'KILLED'} (parent share line {'ok' if line1 else 'FAIL'}; d2h coverage line "
      f"{'ok' if line2 else 'FAIL'})")
nch = np.exp(out["ps_log_n_child"].to_numpy(float))
fin = np.isfinite(nch)
print(f"child events seen per parent row: {dict(Counter(np.round(nch[fin]).astype(int).clip(max=20)).most_common(10))}; "
      f">= 2 seen {(nch[fin] >= 2).mean() if fin.any() else float('nan'):.4f}")
has = hp == 1
print(f"parent rows {int(has.sum())}; with >= 2 child events seen but no d2h (clock or share rule) "
      f"{int((has & fin & (nch >= 2) & ~np.isfinite(d)).sum())}")
by = {c: (round(float(np.nanmean(hp[cat == c])), 4), round(float(np.isfinite(d[cat == c]).mean()), 4), int((cat == c).sum()))
      for c in sorted(set(cat)) if (cat == c).sum() >= 200}
print(f"by category (has_parent share, d2h coverage, n): {by}")
ev = A.event_features(rows, S.read_parquet(paths.features(cid), ["market_id", "event_id", "ms_mid"]), prev_mid)["ev_sib_d2h"].to_numpy(float)
ok = np.isfinite(ev) & np.isfinite(d)
r = np.corrcoef(ev[ok], d[ok])[0, 1] if ok.sum() > 2 else float("nan")
print(f"corr(ps_sib_d2h, ev_sib_d2h) {r:.3f} (n {int(ok.sum())})")
print(f"run end {S.iso(S.now_ts())}")
