import gzip, csv, json
from astrolabe.research_lab import cb6_tail as t, history_backfill as hb
files = t.verify_exclusion_files(t.EXCLUSION_PINS, history_root=t.HIST_ROOT, seals_dir=t.SEALS_DIR)
side = {}
for pin in t.EXCLUSION_PINS:
    if pin["kind"] != "sample":
        continue
    with gzip.open(files[pin["name"]], "rt") as fh:
        for r in csv.DictReader(fh):
            side.setdefault(r["market_id"], (r.get("end_epoch"), r.get("close_epoch"), r.get("closed"), r.get("created_at"), r.get("fee_category")))
def v2ok(m):
    e, c, cl, cr, _ = side[m]
    try: e = float(e); c = float(c)
    except (TypeError, ValueError): return False
    cr = t._parse_ts(cr)
    return str(cl) in ("1","True","true") and t.c4._ep("2025-01-01") <= e < t.c4._ep("2026-01-01") and cr is not None and e - cr >= 14*86400 and c >= e - 2*86400
v1 = [r["market_id"] for r in t.smoke_candidates(files, t.EXCLUSION_PINS)[:20]]
lo, hi, cut = t.c4._ep("2025-09-01"), t.c4._ep("2026-08-01"), t.c4._ep("2026-10-10")
pool = []
for m, (e, c, cl, cr, fee) in side.items():
    cr = t._parse_ts(cr)
    try: e = float(e)
    except (TypeError, ValueError): continue
    if cr and lo <= cr < hi and e <= cut and e - cr >= 14*86400 and str(cl) in ("1","True","true") and (fee or "") != "weather":
        pool.append(m)
pool.sort(key=lambda m: hb._rank(t.SMOKE_SEED, m))
v2pool = sorted([m for m in side if v2ok(m)], key=lambda m: hb._rank("arepo-h8-smoke2", m))
print(json.dumps({"n_v2_pool": len(v2pool), "v1_probed_in_v2_pool": sum(m in v2pool for m in v1),
                  "h8like_probed_in_v2_pool": sum(m in v2pool for m in pool[:20]),
                  "v1_probed_in_v2_first20": sum(m in v2pool[:20] for m in v1),
                  "h8like_probed_in_v2_first20": sum(m in v2pool[:20] for m in pool[:20])}))
