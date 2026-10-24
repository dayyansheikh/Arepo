"""Pilot for research_lab.history_sources: <=20 markets (pmxt books), <=200 wallets (Data API).

Usage: python scripts/pilot_history_sources.py [--wallets 200] [--markets 20]
Writes hashed-only outputs under data-dumps/research_lab/history_sources/. Raw addresses are
held in memory only.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from datetime import UTC, datetime

import httpx
import pyarrow.parquet as pq

from astrolabe.research_lab import history_sources as hs


def yield_to_live_pass() -> None:
    """Live prospective collection has priority: wait while arepo_pass.sh is running."""
    while subprocess.run(["pgrep", "-f", "arepo_pass.sh"], capture_output=True).returncode == 0:
        time.sleep(30)


def pilot_books(n_markets: int, use_cond: bool = True) -> dict:
    t = datetime(2026, 8, 1, 12, 30, tzinfo=UTC)
    yield_to_live_pass()
    fetch = hs.httpx_range_fetch()
    url = hs.pmxt_url(t.replace(minute=0))
    rf = hs.RangeFile(url, hs.httpx_size(url), fetch)
    pf = pq.ParquetFile(rf)
    # candidate assets: first book events from a few row groups spread over the file
    assets: list[str] = []
    cond: dict[str, str] = {}
    for rg in range(5, pf.num_row_groups, max(1, pf.num_row_groups // 12)):
        tb = pf.read_row_group(rg, columns=["asset_id", "event_type", "market"]).to_pandas()
        b = tb[tb.event_type == "book"].drop_duplicates("asset_id").head(3)
        for a, m in zip(b.asset_id, b.market, strict=True):
            assets.append(a)
            cond[a] = m.decode() if isinstance(m, bytes) else str(m)
        if len(assets) >= n_markets:
            break
    assets = assets[:n_markets]
    stats: dict = {}
    t0 = time.monotonic()
    rows = hs.load_book_snapshots(t, assets, stats=stats, condition_ids=cond if use_cond else None)
    dt = time.monotonic() - t0
    states: dict = {}
    for r in rows:
        states[r["state"]] = states.get(r["state"], 0) + 1
    lag = [(int(t.timestamp() * 1000) - r["receipt_ts_ms"]) / 1000 for r in rows if r["receipt_ts_ms"]]
    return {"t": t.isoformat(), "n_tokens": len(assets), "states": states, "seconds": round(dt, 1),
            "stats": stats, "snapshot_age_s_median": statistics.median(lag) if lag else None,
            "snapshot_age_s_max": max(lag) if lag else None,
            "rows_sample": rows[:3]}


def pilot_wallets(n_wallets: int) -> dict:
    c = httpx.Client(timeout=30, headers={"User-Agent": hs.USER_AGENT})
    addr: dict[str, int] = {}
    off = 0
    while len(addr) < n_wallets and off < 3000:
        r = c.get(hs.DATA_API + "/trades", params={"limit": 500, "offset": off, "takerOnly": "false"})
        r.raise_for_status()
        for it in r.json():
            addr.setdefault(it["proxyWallet"], int(it["timestamp"]))
        off += 500
        time.sleep(0.3)
    wh = hs.WalletHistory(limiter=hs.RateLimiter(0.25, gate=yield_to_live_pass))
    res = []
    t0 = time.monotonic()
    for i, (a, ts) in enumerate(list(addr.items())[:n_wallets]):
        if i % 20 == 0:
            print(f"wallet {i} req={wh.n_requests} t={time.monotonic() - t0:.0f}s", flush=True)
        try:
            res.append(wh.lookup(a, ts))
        except hs.SourceError as exc:
            res.append({"error": str(exc)})
    dt = time.monotonic() - t0
    ok = [r for r in res if "error" not in r]
    lat = sorted(wh.latencies)
    new = [r for r in ok if r["n_prior_trades"] == 0]
    return {"n_wallets": len(res), "n_ok": len(ok), "n_errors": len(res) - len(ok),
            "n_requests": wh.n_requests, "req_per_wallet": round(wh.n_requests / max(1, len(res)), 2),
            "seconds": round(dt, 1), "latency_p50": round(lat[len(lat) // 2], 3) if lat else None,
            "latency_p95": round(lat[int(len(lat) * .95)], 3) if lat else None,
            "n_no_prior_trade": len(new), "n_truncated": sum(r["truncated"] for r in ok),
            "n_prior_trades_median": statistics.median(r["n_prior_trades"] for r in ok) if ok else None,
            "hashed_results": res}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallets", type=int, default=200)
    ap.add_argument("--markets", type=int, default=20)
    a = ap.parse_args()
    books = pilot_books(min(a.markets, 20))
    print("books", json.dumps({k: v for k, v in books.items() if k != "rows_sample"}, default=str), flush=True)
    out = {"books": books, "wallets": pilot_wallets(min(a.wallets, 200))}
    p = hs.write_manifest(hs.ROOT, "pilot_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"), out)
    summ = {k: {kk: vv for kk, vv in v.items() if kk not in ("hashed_results", "rows_sample")}
            for k, v in out.items()}
    print(json.dumps(summ, indent=1, default=str))
    print(p)
