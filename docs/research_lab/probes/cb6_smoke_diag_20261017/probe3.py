"""Counts-only, zero requests: where do the h8-like origin windows sit relative to created_at and close_time?"""
import gzip, csv, json, time
from astrolabe.research_lab import cb6_tail as t, history_backfill as hb
DAY = 86400
files = t.verify_exclusion_files(t.EXCLUSION_PINS, history_root=t.HIST_ROOT, seals_dir=t.SEALS_DIR)
side = {}
for pin in t.EXCLUSION_PINS:
    if pin["kind"] != "sample":
        continue
    with gzip.open(files[pin["name"]], "rt") as fh:
        for r in csv.DictReader(fh):
            side.setdefault(r["market_id"], {k: r.get(k) for k in ("end_epoch", "close_epoch", "closed", "created_at", "start_epoch", "fee_category")})
lo, hi, cut = t.c4._ep("2025-09-01"), t.c4._ep("2026-08-01"), t.c4._ep("2026-10-10")
pool = []
for m, v in side.items():
    cr = t._parse_ts(v["created_at"])
    try:
        end = float(v["end_epoch"])
    except (TypeError, ValueError):
        continue
    if (cr and lo <= cr < hi and end <= cut and end - cr >= 14 * DAY and str(v["closed"]) in ("1", "True", "true")
            and (v["fee_category"] or "") != "weather"):
        pool.append((m, v, cr, end))
pool.sort(key=lambda x: hb._rank(t.SMOKE_SEED, x[0]))
tf = time.time()
for k, (m, v, cr, end) in enumerate(pool[:20]):
    try:
        close = float(v["close_epoch"])
    except (TypeError, ValueError):
        close = None
    try:
        st = float(v["start_epoch"])
    except (TypeError, ValueError):
        st = None
    for j, o in enumerate(t.draw_origins(m, cr, end, tf)):
        a, b = o - 8 * DAY, o + 2 * DAY
        print(json.dumps({"k": k, "j": j, "close_before_t": close is not None and close < o,
                          "close_before_window_start": close is not None and close < a,
                          "close_minus_t_d": None if close is None else round((close - o) / DAY, 1),
                          "start_minus_window_start_d": None if st is None else round((st - a) / DAY, 1)}))
# pool-level counts (timestamps only): share of h8-like markets closing > 2 d before scheduled end
n = len(pool); early = sum(1 for _, v, _, e in pool if v["close_epoch"] and float(v["close_epoch"]) < e - 2 * DAY)
print(json.dumps({"n_pool": n, "n_close_gt_2d_before_end": early}))
