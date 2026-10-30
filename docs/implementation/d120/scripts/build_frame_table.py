"""Read-only: rebuild the D118 frame population with pre-t0 group/category fields.

Streams the retained D118 frame raw pages (gzip) one at a time; writes a compact CSV to the
scratchpad. Verifies the reconstructed eligible strata against the D118 selection plan.
"""
import csv
import gzip
import json
import os
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation

REPO = "/Users/DayyanSheikh/Projects/astrolabe"
FRAME = f"{REPO}/data-dumps/fs2_capture_52eead5d6a984264a9eb0828502fb697"
SEL = f"{REPO}/data-dumps/fs2_selection_panel_d118_control_pairing_1"
OUT = sys.argv[1]


def dec(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None
    return d if d.is_finite() else None


def band(v, edges):
    if v is None:
        return "unknown"
    return str(sum(v >= Decimal(e) for e in edges))


plan = json.load(open(f"{SEL}/selection_plan.json"))
policy = json.load(open(f"{SEL}/selection_policy.json"))
excluded = {e["market_id"]: e["reason"] for e in plan["exclusions"]}
ref = datetime.fromisoformat(policy["declared_at"]["utc"].replace("Z", "+00:00"))
plan_strata = {(s["time_to_close"], s["probability_band"], s["liquidity_band"]): s["eligible_count"]
               for s in plan["strata"]}
del plan

cols = ["market_id", "token0", "eligible_pl", "frame_ok", "excl", "close_bin", "pband", "lband", "liquidity",
        "p0", "event_id", "event_slug", "series_slug", "neg_risk", "nr_id", "fee_type",
        "sports_type", "game_start", "gamma_bid", "gamma_ask", "end_date", "question"]
seen = set()
counts = Counter()
rows_total = dup = 0
with gzip.open(OUT, "wt", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(cols)
    for d in sorted(os.listdir(FRAME)):
        p = os.path.join(FRAME, d, "raw.bin")
        if not os.path.isfile(p):
            continue
        b = open(p, "rb").read()
        try:
            t = gzip.decompress(b)
        except OSError:
            t = b
        try:
            markets = json.loads(t)["markets"]
        except (ValueError, KeyError, TypeError):
            continue
        for r in markets:
            rows_total += 1
            mid = str(r.get("id"))
            if mid in seen:
                dup += 1
                continue
            seen.add(mid)
            toks = r.get("clobTokenIds")
            outs = r.get("outcomes")
            try:
                toks = json.loads(toks) if isinstance(toks, str) else toks
                outs = json.loads(outs) if isinstance(outs, str) else outs
            except ValueError:
                toks, outs = None, None
            token0 = toks[0] if isinstance(toks, list) and toks else ""
            prices = r.get("outcomePrices")
            p0 = None
            try:
                prices = json.loads(prices) if isinstance(prices, str) else prices
                if isinstance(prices, list) and isinstance(outs, list) and len(prices) == len(outs):
                    p0 = dec(prices[0])
                    if p0 is not None and not (0 <= p0 <= 1):
                        p0 = None
            except ValueError:
                p0 = None
            liq = dec(r.get("liquidity"))
            if liq is not None and liq < 0:
                liq = None
            close = r.get("endDate")
            cb = "unknown"
            if isinstance(close, str):
                try:
                    secs = (datetime.fromisoformat(close.replace("Z", "+00:00")) - ref).total_seconds()
                    cb = ("past" if secs <= 0 else "le_1d" if secs <= 86400 else "le_7d"
                          if secs <= 604800 else "le_30d" if secs <= 2592000 else "gt_30d")
                except ValueError:
                    cb = "unknown"
            ev = (r.get("events") or [{}])[0] or {}
            ser = (ev.get("series") or [{}])[0] or {}
            frame_ok = (r.get("active") is True and r.get("closed") is False
                        and isinstance(toks, list) and isinstance(outs, list)
                        and len(toks) == len(outs) and len(toks) >= 1)
            excl = excluded.get(mid, "")
            elig = int(frame_ok and not excl)
            pb, lb = band(p0, ("0.1", "0.5", "0.9")), band(liq, ("1000", "10000", "100000"))
            if elig:
                counts[(cb, pb, lb)] += 1
            w.writerow([mid, token0, elig, int(frame_ok), excl, cb, pb, lb,
                        "" if liq is None else str(liq), "" if p0 is None else str(p0),
                        ev.get("id", ""), ev.get("slug", ""), ser.get("slug", ""),
                        int(bool(r.get("negRisk"))), r.get("negRiskMarketID") or "",
                        r.get("feeType") or "", r.get("sportsMarketType") or "",
                        r.get("gameStartTime") or "", r.get("bestBid", ""), r.get("bestAsk", ""),
                        close or "", (r.get("question") or "")[:120]])
mismatch = {k: (counts.get(k), v) for k, v in plan_strata.items() if counts.get(k) != v}
extra = {k: c for k, c in counts.items() if k not in plan_strata}
print(json.dumps({"rows_total": rows_total, "unique": len(seen), "dup": dup,
                  "eligible": sum(counts.values()), "plan_strata": len(plan_strata),
                  "strata": len(counts), "mismatch": {str(k): v for k, v in mismatch.items()},
                  "extra": {str(k): v for k, v in extra.items()}}, indent=1))
