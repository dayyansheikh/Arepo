import gzip, csv, json
from astrolabe.research_lab import cb6_tail as t
files = t.verify_exclusion_files(t.EXCLUSION_PINS, history_root=t.HIST_ROOT, seals_dir=t.SEALS_DIR)
rows = {}
for pin in t.EXCLUSION_PINS:
    if pin["kind"] != "sample":
        continue
    with gzip.open(files[pin["name"]], "rt") as fh:
        for r in csv.DictReader(fh):
            try:
                end = float(r["end_epoch"])
            except (TypeError, ValueError):
                continue
            if str(r.get("closed")) in ("1", "True", "true") and t.c4._ep("2025-01-01") <= end < t.c4._ep("2026-01-01"):
                rows[r["market_id"]] = (end, t._parse_ts(r.get("created_at")), r.get("close_epoch"))
c = {"n_closed_end_2025": len(rows), "drop_no_created": 0, "drop_life_lt_14d": 0, "drop_no_close": 0, "drop_closed_before_window_end": 0, "n_pool": 0}
for end, cr, close in rows.values():
    if cr is None: c["drop_no_created"] += 1; continue
    if end - cr < 14 * 86400: c["drop_life_lt_14d"] += 1; continue
    try: close = float(close)
    except (TypeError, ValueError): c["drop_no_close"] += 1; continue
    if close < end - 2 * 86400: c["drop_closed_before_window_end"] += 1; continue
    c["n_pool"] += 1
print(json.dumps(c))
