"""Counts-only probe 2: life coverage of the smoke window, and the h8 origin rule applied to worn h8-like markets."""
import gzip, csv, json, statistics, sys, time
from astrolabe.research_lab import cb6_tail as t, history_backfill as hb

DAY = 86400
lim = hb.Limiter(hb.httpx_transport(), rps=2.0)
files = t.verify_exclusion_files(t.EXCLUSION_PINS, history_root=t.HIST_ROOT, seals_dir=t.SEALS_DIR)
smoke = t.smoke_candidates(files, t.EXCLUSION_PINS)[: t.SMOKE_N]
side = {}
for pin in t.EXCLUSION_PINS:
    if pin["kind"] != "sample":
        continue
    with gzip.open(files[pin["name"]], "rt") as fh:
        for r in csv.DictReader(fh):
            side.setdefault(r["market_id"], {k: r.get(k) for k in ("condition_id", "token0", "end_epoch", "close_epoch",
                                                                   "closed", "created_at", "fee_category")})

def ph(tok, a, b):
    s, d = lim.get(hb.CLOB_PRICES, {"market": tok, "startTs": int(a), "endTs": int(b), "fidelity": 60})
    return None if s != 200 or not isinstance(d, dict) else sorted(int(h["t"]) for h in d.get("history") or [])

def trades(cid, a=None, b=None):
    p = {"market": cid, "takerOnly": "true", "limit": 1000}
    if a is not None:
        p.update(start=int(a), end=int(b))
    s, d = lim.get(hb.DATA_TRADES, p)
    return None if s != 200 or not isinstance(d, list) else sorted(int(x["timestamp"]) for x in d if "timestamp" in x)

# A: life coverage of the 20 smoke markets
for k, r in enumerate(smoke):
    v = side[r["market_id"]]; end = float(r["end_epoch"]); cr = t._parse_ts(v["created_at"])
    a = end - 12 * DAY
    tr = trades(v["condition_id"])
    lifep = ph(r["token0"], max(cr, end - 14 * DAY), end) if cr else None
    print(json.dumps({"set": "A_smoke_life", "k": k, "life_d": None if cr is None else round((end - cr) / DAY, 1),
                      "window_start_minus_created_d": None if cr is None else round((a - cr) / DAY, 1),
                      "life_trades_n_cap1000": None if tr is None else len(tr),
                      "first_trade_minus_window_start_d": round((tr[0] - a) / DAY, 1) if tr else None,
                      "last14d_f60_points": None if lifep is None else len(lifep),
                      "last14d_first_point_minus_created_d": round((lifep[0] - cr) / DAY, 1) if lifep and cr else None}))
    sys.stdout.flush()

# B: h8-like worn markets (created 2025-09-01..2026-07-31, closed, end <= 2026-10-10, life >= 14 d, not weather) with the
# h8 origin rule (draw_origins, T_fetch = now); one f60 request [t - 8 d, t + 2 d] per origin
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
print(json.dumps({"n_pool_h8like": len(pool)}))
t_fetch = time.time()
for k, (m, v, cr, end) in enumerate(pool[:20]):
    origins = t.draw_origins(m, cr, end, t_fetch)
    for j, o in enumerate(origins):
        a, b = o - 8 * DAY, o + 2 * DAY
        pts = ph(v["token0"], a, b)
        tr = trades(v["condition_id"], a, b)
        rec = {"set": "B_h8like_origin", "k": k, "j": j, "n_origins": len(origins), "life_d": round((end - cr) / DAY, 1),
               "f60_n": None if pts is None else len(pts), "expected": int((b - a) // 3600)}
        if pts:
            g = [y - x for x, y in zip(pts, pts[1:])]
            rec["med_gap_s"] = statistics.median(g) if g else None
            rec["usable_at_t"] = any(o - 7200 <= x <= o - 600 for x in pts)
            rec["first_off_h"] = round((pts[0] - a) / 3600, 1)
        rec["trades_n"] = None if tr is None else len(tr)
        print(json.dumps(rec)); sys.stdout.flush()
    if not origins:
        print(json.dumps({"set": "B_h8like_origin", "k": k, "n_origins": 0}))
print(json.dumps({"requests": lim.requests, "retries": lim.retries, "throttled": lim.throttled}))
