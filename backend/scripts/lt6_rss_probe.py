# ruff: noqa: E501
"""Peak-RSS probe of the LT6 reader on a realistic synthetic pass (LIVE_TESTS_6.md 8.2): two complete captures (k - 1, k) of N markets,
sweep 1 of both passes, and one active-frame trade sample of 1,000,000 rows (2,000 markets x 500 rows). The world is written by the
PARENT process; the reader runs in a FRESH child interpreter whose only work is one ``run_once`` pass, so the number is the reader's
and not the generator's. Peak = ``VmHWM`` from /proc/self/status on Linux, else ``ru_maxrss`` (bytes on macOS, KB elsewhere).

    python scripts/lt6_rss_probe.py [--markets 30000] [--rows 1000000] [--keep DIR]

Synthetic only; no network; writes under a temporary directory.
"""

from __future__ import annotations

import argparse
import json
import resource
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)
K = 101  # the origin slot; K - 1 is a look-back capture, K is the first window origin
REG, END = "2026-10-09T12:00:00Z", "2026-10-30T12:00:00Z"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def peak_rss_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return v / 2**20 if sys.platform == "darwin" else v / 1024.0


def current_rss_mb() -> float:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return float("nan")


def build_world(root: Path, n: int, n_rows: int, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    snap, sw, smp = root / "snap", root / "sweeps", root / "samples"
    for p in (snap, sw, smp):
        p.mkdir(parents=True)
    ids = {}
    mid0 = rng.uniform(0.1, 0.9, n)
    n_s = 2000  # sampled markets; the first n_s markets move by 1-4 c and trade between k - 1 and k
    for k in (K - 1, K):
        start = G0 + timedelta(hours=2 * k)
        cid = start.strftime("%Y%m%dT%H%M%SZ") + f"_{k:08x}"
        ids[k] = cid
        d = snap / cid
        d.mkdir()
        mid = mid0.copy()
        if k == K:
            mid[:n_s] = np.clip(mid[:n_s] + rng.choice([-1, 1], n_s) * rng.uniform(0.012, 0.04, n_s), 0.06, 0.94)
        end = ["2027-03-01T00:00:00Z" if i % 3 else _iso(datetime(2026, 12, 31, 23, 59, tzinfo=UTC) + timedelta(hours=5)) for i in range(n)]
        rows = pd.DataFrame({
            "received_utc": [_iso(start + timedelta(seconds=int(s))) for s in rng.integers(1, 600, n)], "market_id": np.arange(n).astype(str),
            "condition_id": [f"0xc{i}" for i in range(n)], "event_id": (np.arange(n) // 5).astype(str), "closed": "False", "active": "True", "binary": 1,
            "best_bid": np.round(mid - 0.01, 3), "best_ask": np.round(mid + 0.01, 3), "spread": 0.02,
            "last_trade_price": np.where(np.arange(n) < n_s, np.round(mid, 3), 0.5), "chg_1h": 0.0, "chg_1d": 0.01, "chg_1w": 0.0, "liquidity": 2e5,
            "volume24hr": 1000.0 + (np.where(np.arange(n) < n_s, 100.0 * k, 0.0)), "end_date": end, "clob_token_id_0": [f"tok{i}" for i in range(n)],
            "neg_risk": "False", "updated_at": _iso(start - timedelta(hours=1))})
        rows.to_csv(d / "rows.csv.gz", index=False, compression="gzip")
        ext = pd.DataFrame({"market_id": np.arange(n).astype(str), "fee_type": "politics_fees", "fee_category": "Politics", "fees_enabled": "1", "fee_schedule": "",
                            "order_price_min_tick_size": "0.01", "created_at": _iso(G0 - timedelta(days=30)), "series_slugs": "", "order_min_size": "1"})
        ext.to_csv(d / "rows_ext.csv.gz", index=False, compression="gzip")
        (d / "manifest.json").write_text(json.dumps({"capture_id": cid, "state": "complete", "started_utc": _iso(start)}))
        # sweep 1: outcome-0 and outcome-1 token of every market
        s = start + timedelta(minutes=8)
        sd = sw / (s.strftime("%Y%m%dT%H%M%SZ") + f"_s{k:07x}")
        sd.mkdir()
        tok = [f"tok{i}" for i in range(n)]
        sdf = pd.concat([pd.DataFrame({"token_id": tok, "market_id": np.arange(n).astype(str), "batch_receipt_utc": _iso(s), "best_bid": np.round(mid - 0.01, 3),
                                       "best_ask": np.round(mid + 0.01, 3), "state": "two_sided", "bid_size_1": 60.0, "ask_size_1": 40.0,
                                       "depth_bid_1c": rng.uniform(10, 100, n), "depth_ask_1c": rng.uniform(10, 100, n), "depth_bid_5c": rng.uniform(100, 400, n),
                                       "depth_ask_5c": rng.uniform(100, 400, n), "min_order_size": 5.0}),
                         pd.DataFrame({"token_id": [f"no{i}" for i in range(n)], "market_id": np.arange(n).astype(str), "batch_receipt_utc": _iso(s),
                                       "best_bid": np.round(1 - mid - 0.01, 3), "best_ask": np.round(1 - mid + 0.01, 3), "state": "two_sided", "bid_size_1": 60.0,
                                       "ask_size_1": 40.0, "depth_bid_1c": 10.0, "depth_ask_1c": 10.0, "depth_bid_5c": 100.0, "depth_ask_5c": 100.0, "min_order_size": 5.0})])
        sdf.to_csv(sd / "rows.csv.gz", index=False, compression="gzip")
        (sd / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid}))
    # the sample: 2,000 markets x n_rows / 2,000 rows (hex tx hashes, text sizes)
    per = max(n_rows // n_s, 1)
    start = G0 + timedelta(hours=2 * K, minutes=10)
    sid = start.strftime("%Y%m%dT%H%M%SZ") + f"_t{K:07x}"
    d = smp / sid
    d.mkdir()
    o = (G0 + timedelta(hours=2 * K, seconds=300)).timestamp()
    m = np.repeat(np.arange(n_s), per)
    ts = (o - rng.integers(1, 86400, n_s * per)).astype(np.int64)
    tr = pd.DataFrame({"market_id": m.astype(str), "ts": ts, "side": rng.choice(["BUY", "SELL"], n_s * per), "price": np.round(rng.uniform(0.1, 0.9, n_s * per), 3),
                       "size": np.where(rng.random(n_s * per) < 0.2, "10", np.round(rng.uniform(1.5, 80, n_s * per), 4).astype(str)),
                       "outcome_index": 0, "asset": [f"tok{i}" for i in m], "tx_hash": [f"0x{x:064x}" for x in rng.integers(0, 2**62, n_s * per)]})
    tr.to_csv(d / "trades.csv.gz", index=False, compression="gzip")
    feats = pd.DataFrame({"market_id": np.arange(n_s).astype(str), "status": "ok", "origin_utc": _iso(datetime.fromtimestamp(o, UTC)), "n_returned": per})
    feats.to_csv(d / "features.csv.gz", index=False, compression="gzip")
    (d / "plan.json").write_text(json.dumps({"snapshot_id": ids[K]}))
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "frame": "active", "snapshot_id": ids[K]}))
    return {"snap": str(snap), "sweeps": str(sw), "samples": str(smp), "rows": int(len(tr)), "markets": n}


def child(snap: str, sweeps: str, samples: str, out: str, now: float, max_items: int = 2) -> None:
    from astrolabe.research_lab import live_tests6 as lt

    base = peak_rss_mb()
    spec = lt.load_spec(sha=None)
    spec["_pinned"] = False
    st = lt.run_once(snapshot_root=Path(snap), sample_root=Path(samples), sweep_root=Path(sweeps), root=Path(out), spec=spec, registered_utc=REG, end_utc=END,
                     now=now, max_items=max_items, allow_late=True)
    print(json.dumps({"baseline_peak_mb_after_imports": round(base, 1), "peak_mb": round(peak_rss_mb(), 1), "rss_end_mb": round(current_rss_mb(), 1),
                      "platform": sys.platform, "stats": {k: v for k, v in st.items() if isinstance(v, (int, str, bool))}}))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", type=int, default=30000)
    ap.add_argument("--rows", type=int, default=1_000_000)
    ap.add_argument("--keep", type=Path, default=None)
    ap.add_argument("--max-items", type=int, default=2, help="reader --max-items: ladder step 1 is 2 (8.2); the old probe's 40 measured a different run")
    ap.add_argument("--child", nargs=5, metavar=("SNAP", "SWEEPS", "SAMPLES", "OUT", "NOW"), default=None)
    a = ap.parse_args()
    if a.child:
        child(a.child[0], a.child[1], a.child[2], a.child[3], float(a.child[4]), a.max_items)
        return 0
    root = a.keep or Path(tempfile.mkdtemp(prefix="lt6_rss_"))
    root.mkdir(parents=True, exist_ok=True)
    w = build_world(root, a.markets, a.rows)
    now = (G0 + timedelta(hours=2 * (K + 2))).timestamp()
    r = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--child", w["snap"], w["sweeps"], w["samples"], str(root / "out"), str(now), "--max-items", str(a.max_items)],
                       capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[1]), env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]), "PATH": "/usr/bin:/bin"})
    print(r.stdout.strip() or r.stderr[-6000:])
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
