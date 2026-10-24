# ruff: noqa: E501
"""Pilot for research_lab.external_news: seeded category-stratified sample from the latest snapshot.

Writes ``data-dumps/research_lab/external_news/pilot_<snapshot>.jsonl`` (one record per market, with the
query, top headlines, features and latency) and prints a summary. Public GDELT/Gamma reads only.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path

import httpx
import pandas as pd

from astrolabe.research_lab import external_news as en
from astrolabe.research_lab.calibration import coarse_category

GAMMA = "https://gamma-api.polymarket.com"
SNAP = Path("data-dumps/research_lab/snapshots")


def latest_snapshot() -> Path:
    for d in sorted(SNAP.iterdir(), reverse=True):
        m = d / "manifest.json"
        if m.exists() and (d / "rows.csv.gz").exists() and json.loads(m.read_text()).get("state") == "complete":
            return d
    raise SystemExit("no complete snapshot")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--origin", default=None, help="override origin (default: snapshot received_utc)")
    a = ap.parse_args()
    d = latest_snapshot()
    rows = pd.read_csv(d / "rows.csv.gz", dtype={"market_id": str, "event_id": str})
    rows = rows[(rows.binary == 1) & rows.best_bid.notna() & rows.best_ask.notna()].drop_duplicates("market_id")
    rows = rows[(rows.best_bid > 0) & (rows.best_ask < 1)]
    origin = a.origin or str(rows.received_utc.min())
    rng = random.Random(a.seed)
    ids = sorted(rows.event_id.dropna().unique())
    cat: dict[str, str] = {}
    pool = rng.sample(ids, min(len(ids), 6000))
    with httpx.Client(timeout=60) as h:
        for i in range(0, len(pool), 50):
            r = h.get(f"{GAMMA}/events", params=[("id", x) for x in pool[i:i + 50]])
            for e in r.json():
                cat[str(e["id"])] = coarse_category([t.get("slug") for t in e.get("tags", []) if t.get("slug")])
    rows = rows[rows.event_id.isin(cat)].copy()
    rows["category"] = rows.event_id.map(cat)
    cats = sorted(rows.category.unique())
    per = max(1, a.n // len(cats))
    pick: list[str] = []
    for c in cats:
        m = sorted(rows[rows.category == c].market_id)
        pick += rng.sample(m, min(per, len(m)))
    rest = sorted(set(rows.market_id) - set(pick))
    pick += rng.sample(rest, max(0, min(a.n - len(pick), len(rest))))
    pick = pick[: a.n]
    info: dict[str, dict] = {}
    with httpx.Client(timeout=60) as h:
        for i in range(0, len(pick), 50):
            r = h.get(f"{GAMMA}/markets", params=[("id", x) for x in pick[i:i + 50]])
            for m in r.json():
                ev = (m.get("events") or [{}])[0]
                info[str(m["id"])] = {"question": m.get("question") or "", "event_title": ev.get("title")}
    client = en.GdeltClient(max_retries=4, min_interval_s=6.0)
    out = Path(en.CACHE_ROOT) / f"pilot_{d.name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmap = dict(zip(rows.market_id, rows.category, strict=True))
    with out.open("w") as f:
        for k, mid in enumerate(pick, 1):
            q = info.get(mid)
            if not q:
                continue
            rec = en.market_features(client, q["question"], q["event_title"], origin, "exploratory_dev")
            rec.update(market_id=mid, category=cmap[mid], question=q["question"])
            f.write(json.dumps({x: en.nan_to_none(y) for x, y in rec.items()}) + "\n")
            f.flush()
            print(k, rec["status"], rec["query"], flush=True)
    recs = [json.loads(x) for x in out.read_text().splitlines()]
    n = len(recs)
    ok = [r for r in recs if r["status"] == "ok"]
    print("snapshot", d.name, "origin", origin, "n", n)
    print("status", pd.Series([r["status"] for r in recs]).value_counts().to_dict())
    for c in en.FEATURE_COLUMNS:
        print(f"coverage {c}: {sum(r.get(c) is not None for r in recs) / n:.2f}")
    lat = [r["fetch_seconds"] for r in recs if "fetch_seconds" in r]
    print("per-market seconds median", statistics.median(lat) if lat else None, "requests", client.requests_made,
          "failures", client.failures, "req latency median", statistics.median(client.latencies) if client.latencies else None)
    print("ok-with-n24h>0", sum(1 for r in ok if (r.get("ext_news_n_24h") or 0) > 0), "of", n)
    for r in recs[:: max(1, n // 20)][:20]:
        print("Q:", r["question"], "\n  query:", r["query"], "\n  ", r.get("top_titles"))


if __name__ == "__main__":
    main()
