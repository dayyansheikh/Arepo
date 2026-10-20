# ruff: noqa: E501
"""Wallet-skill family runner (research only; never trades).

  dev            DEVELOPMENT evaluation on HB1 history data (``--history`` = a read-only history directory or a copy).
  host-dry-run   light read-only timing/memory run: seed profiles from one history panel, ingest the newest trade
                 samples through the deduper, snapshot, compute family features for the newest sample. Writes only
                 under ``--work`` (default /tmp/wskill), which it deletes at the end unless ``--keep``.

Design and declaration: docs/research_lab/signal_engine/families/WALLET_SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import resource
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import wallet_skill as ws  # noqa: E402
from astrolabe.research_lab import wallet_skill_dev as wd  # noqa: E402


def peak_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024


def cmd_dev(a) -> int:
    out = wd.run(Path(a.history), Path(a.out) if a.out else None, B=a.boot)
    print(json.dumps({"holm": out["holm"], "elapsed_s": out["elapsed_s"], "peak_mb": peak_mb()}, indent=1))
    return 0


def cmd_dry(a) -> int:
    work = Path(a.work)
    if work.exists() and any(work.iterdir()) and not a.reuse:
        print(f"refusing: {work} is not empty", file=sys.stderr)
        return 2
    work.mkdir(parents=True, exist_ok=True)
    rep: dict = {"label": "host dry run (read-only inputs; writes only under --work)"}
    t0 = time.time()
    # 1. seed profiles from one history panel (positions known before now)
    h = wd.load_history(Path(a.history), panels=(a.seed_panel,))
    pt, res = wd.profile_trades(h)
    b = ws.ProfileBuilder()
    b.add_trades(pt)
    b.add_resolutions(res)
    now = time.time()
    b.advance_to(now, allow_future_trades=True)
    rep["seed"] = {"panel": a.seed_panel, "trades": int(len(pt)), "resolved_markets": int(len(res)),
                   "pending_rows": int(len(b.pending)), "wallets": int(len(b.sums)), "s": round(time.time() - t0, 1),
                   "peak_mb": round(peak_mb(), 1)}
    hist_wallets = set(h["trades"]["wallet"].unique())
    del h, pt
    # 2. ingest the newest trade samples (deduplicated)
    t1 = time.time()
    samples = sorted(p.parent for p in Path(a.samples).glob("*/wallets.csv.gz"))[-a.n_samples:]
    dd = ws.TradeDeduper()
    rows_in = rows_new = 0
    sample_wallets: set = set()
    for d in samples:
        raw = pd.read_csv(d / "wallets.csv.gz", usecols=["market_id", "ts", "side", "outcome_index", "size", "price", "wallet_hash"])
        tr = ws.normalise_trades(raw)
        tr = tr[tr["ts"] < now]
        rows_in += len(tr)
        new = dd.new_only(tr)
        rows_new += len(new)
        sample_wallets.update(new["wallet"].unique())
        b.add_trades(new)
    b.advance_to(time.time())  # every ingested sample trade is older than now
    rep["ingest"] = {"samples": len(samples), "first": samples[0].name if samples else None, "last": samples[-1].name if samples else None,
                     "rows_read": rows_in, "rows_new": rows_new, "pending_rows": int(len(b.pending)),
                     "dedup_markets": len(dd.wm), "s": round(time.time() - t1, 1), "peak_mb": round(peak_mb(), 1)}
    ov = len(sample_wallets & hist_wallets)
    rep["hash_key_check"] = {"sample_wallets": len(sample_wallets), "also_in_history": ov,
                             "share": round(ov / max(1, len(sample_wallets)), 4),
                             "note": "a large overlap means the sidecar and the history backfill share the HMAC key"}
    # 3. snapshot + save state
    t2 = time.time()
    prof = b.snapshot()
    snap = ws.snapshot_frame(prof, as_of=b.as_of)
    snap.to_parquet(work / "snapshot.parquet", index=False)
    b.save(work / "state")
    sizes = {p.name: p.stat().st_size for p in (work / "state").iterdir()}
    rep["snapshot"] = {"wallets": int(len(prof)), "eligible": int(prof["eligible"].sum()), "skilled": int(snap["skilled"].sum()),
                       "state_bytes": sizes, "snapshot_bytes": (work / "snapshot.parquet").stat().st_size,
                       "s": round(time.time() - t2, 1), "peak_mb": round(peak_mb(), 1)}
    # 4. family features for the newest sample (all its ok markets)
    t3 = time.time()
    if samples:
        fe = pd.read_csv(samples[-1] / "features.csv.gz", usecols=["market_id", "status"])
        f = pd.DataFrame({"market_id": fe.loc[fe["status"] == "ok", "market_id"].to_numpy(np.int64)})
        feats = ws.family_features(samples[-1], f, snap)
        rep["features"] = {"markets": int(len(f)), "nonnull_net24": int(feats["ws_net24h"].notna().sum()),
                           "any_skilled_24h": int((feats["ws_share24"] > 0).sum()),
                           "mean_cov24": float(np.nanmean(feats["ws_cov24"])) if feats["ws_cov24"].notna().any() else None,
                           "s": round(time.time() - t3, 1), "peak_mb": round(peak_mb(), 1)}
    rep["total_s"] = round(time.time() - t0, 1)
    rep["peak_mb"] = round(peak_mb(), 1)
    print(json.dumps(rep, indent=1, default=str))
    if not a.keep:
        shutil.rmtree(work)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dev")
    d.add_argument("--history", required=True)
    d.add_argument("--out")
    d.add_argument("--boot", type=int, default=wd.B_DEFAULT)
    r = sub.add_parser("host-dry-run")
    r.add_argument("--history", required=True)
    r.add_argument("--samples", required=True)
    r.add_argument("--seed-panel", default="h2_main")
    r.add_argument("--n-samples", type=int, default=12)
    r.add_argument("--work", default="/tmp/wskill")
    r.add_argument("--keep", action="store_true")
    r.add_argument("--reuse", action="store_true")
    a = ap.parse_args(argv)
    return cmd_dev(a) if a.cmd == "dev" else cmd_dry(a)


if __name__ == "__main__":
    raise SystemExit(main())
