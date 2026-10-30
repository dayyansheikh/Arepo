"""Counts-only diagnosis of the q0135 smoke FAIL. No ids, prices or outcomes are stored or printed."""
import gzip, csv, json, statistics, sys
from astrolabe.research_lab import cb6_tail as t, history_backfill as hb

DAY = 86400
lim = hb.Limiter(hb.httpx_transport(), rps=2.0)
files = t.verify_exclusion_files(t.EXCLUSION_PINS, history_root=t.HIST_ROOT, seals_dir=t.SEALS_DIR)
smoke = t.smoke_candidates(files, t.EXCLUSION_PINS)[: t.SMOKE_N]
# side info (timestamps / ids only; outcome columns never touched)
side = {}
for pin in t.EXCLUSION_PINS:
    if pin["kind"] != "sample":
        continue
    with gzip.open(files[pin["name"]], "rt") as fh:
        for r in csv.DictReader(fh):
            side.setdefault(r["market_id"], {k: r.get(k) for k in ("condition_id", "token0", "end_epoch", "close_epoch",
                                                                   "closed", "created_at", "start_epoch")})
# 2026 pool: same rule as smoke_candidates but end_at in [2026-01-01, 2026-10-10)
lo26, hi26 = t.c4._ep("2026-01-01"), t.c4._ep("2026-10-10")
pool26 = sorted({m: v for m, v in side.items() if str(v["closed"]) in ("1", "True", "true") and v["end_epoch"]
                 and lo26 <= float(v["end_epoch"]) < hi26}.items(), key=lambda kv: hb._rank(t.SMOKE_SEED, kv[0]))
print(json.dumps({"n_smoke": len(smoke), "n_pool_2026_closed": len(pool26)}))

def ph(params):
    s, d = lim.get(hb.CLOB_PRICES, params)
    if s != 200 or not isinstance(d, dict):
        return None
    return sorted(int(h["t"]) for h in d.get("history") or [])

def med_gap(ts):
    g = [y - x for x, y in zip(ts, ts[1:])]
    return statistics.median(g) if g else None

def probe(mid, tok, cid, end, close):
    a, b = int(end - 12 * DAY), int(end - 2 * DAY)
    out = {"close_minus_end_h": None if close is None else round((close - end) / 3600, 1),
           "close_before_window_end": close is not None and close < b, "close_before_window_start": close is not None and close < a}
    p60 = ph({"market": tok, "startTs": a, "endTs": b, "fidelity": 60})
    out["f60_n"] = None if p60 is None else len(p60)
    if p60:
        out["f60_first_off_h"] = round((p60[0] - a) / 3600, 1); out["f60_last_off_h"] = round((p60[-1] - a) / 3600, 1)
        out["f60_med_gap_s"] = med_gap(p60)
    p10 = ph({"market": tok, "startTs": a, "endTs": b, "fidelity": 10})
    out["f10_n"] = None if p10 is None else len(p10)
    pmax = ph({"market": tok, "interval": "max", "fidelity": 60})
    out["max60_n_total"] = None if pmax is None else len(pmax)
    out["max60_n_in_window"] = None if pmax is None else sum(a <= x <= b for x in pmax)
    if pmax:
        out["max60_first_rel_end_d"] = round((pmax[0] - end) / DAY, 1); out["max60_last_rel_end_d"] = round((pmax[-1] - end) / DAY, 1)
        out["max60_med_gap_s"] = med_gap(pmax)
    # trades in window (one page, no takerOnly filter change: default)
    s, d = lim.get(hb.DATA_TRADES, {"market": cid, "start": a, "end": b, "takerOnly": "true", "limit": 1000})
    if s == 200 and isinstance(d, list):
        ts = [int(x["timestamp"]) for x in d if "timestamp" in x]
        inw = [x for x in ts if a <= x <= b]
        out["trades_n"] = len(ts); out["trades_outside_window"] = len(ts) - len(inw)
        th = {(x - a) // 3600 for x in inw}
        ph_ = {(x - a) // 3600 for x in (p60 or [])}
        out["trade_hours"] = len(th); out["point_hours"] = len(ph_)
        out["trade_hours_without_point"] = len(th - ph_); out["point_hours_without_trade"] = len(ph_ - th)
        if inw:
            out["trade_first_off_h"] = round((min(inw) - a) / 3600, 1); out["trade_last_off_h"] = round((max(inw) - a) / 3600, 1)
    else:
        out["trades_status"] = s
    return out

for label, items in (("smoke2025", [(r["market_id"], r["token0"], side[r["market_id"]]["condition_id"], r["end_epoch"],
                                     side[r["market_id"]]["close_epoch"]) for r in smoke]),
                     ("pool2026", [(m, v["token0"], v["condition_id"], float(v["end_epoch"]), v["close_epoch"]) for m, v in pool26[:20]])):
    for k, (mid, tok, cid, end, close) in enumerate(items):
        try:
            c = float(close) if close not in (None, "") else None
        except ValueError:
            c = None
        print(json.dumps({"set": label, "k": k, **probe(mid, tok, cid, float(end), c)}))
        sys.stdout.flush()
print(json.dumps({"requests": lim.requests, "retries": lim.retries, "throttled": lim.throttled}))
