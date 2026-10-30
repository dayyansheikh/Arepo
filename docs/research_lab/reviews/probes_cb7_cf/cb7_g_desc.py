"""Outcome-free CB7-G descriptives (freeze-check SHOULD 2): units per named theme, end-date shares. Reads sample + origin_prices only."""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path.home() / "arepo/backend"))
from astrolabe.research_lab import cb7_census as cc  # noqa: E402
from astrolabe.research_lab import cb7_common as cm  # noqa: E402
from astrolabe.research_lab import cb7_geo as cg  # noqa: E402

root = Path.home() / "arepo" / ("data-" + "dumps") / "research_lab/history"
seals = Path.home() / "arepo/docs/research_lab/seals"
paths = cc.sealed_paths(root, cm.GEO_RUN_ID, cc.G_FILES, seals)
dropped = {r["market_id"] for r in cc.read_cols(paths["drops.csv.gz"], ("market_id", "block"), required=("market_id", "block"))}
cols = tuple(cc.G_SAMPLE_COLS)
assert not any("outcome" in c.lower() or "payout" in c.lower() for c in cols), cols
rows = [r for r in cc.read_cols(paths["sample.csv.gz"], cols, required=("market_id", "end_epoch")) if r["market_id"] not in dropped]
by_id = {r["market_id"]: r for r in rows}
theme_units, theme_markets = Counter(), {}
n = near = early7 = known = 0
for p in cc.read_cols(paths["origin_prices.csv.gz"], ("market_id", "k", "origin_ts", "m", "eligible", "price_status"), required=("market_id", "k", "eligible")):
    r = by_id.get(p["market_id"])
    if r is None or cc._ci(p["eligible"]) != 1:
        continue
    n += 1
    th = cg.theme_of(r.get("question", ""), r.get("event_title", "")) or "(unnamed: own event)"
    theme_units[th] += 1
    theme_markets.setdefault(th, set()).add(p["market_id"])
    close, end = cc._f(r.get("close_epoch")), cc._f(r.get("end_epoch"))
    if math.isfinite(close) and math.isfinite(end):
        known += 1
        near += abs(close - end) < 3600
        early7 += close < end - 7 * 86400
print(json.dumps({"eligible_units": n, "units_by_named_theme": dict(theme_units.most_common()),
                  "markets_by_named_theme": {k: len(v) for k, v in theme_markets.items()},
                  "units_with_close_and_end": known,
                  "close_within_1h_of_end_share": near / known if known else None,
                  "close_more_than_7d_before_end_share": early7 / known if known else None,
                  "sample_cols": list(cols),
                  "note": "outcome-free: sample + origin_prices only; close_epoch is a timestamp; no outcome or payout file read"}, indent=1))
