# ruff: noqa: E501
"""Maker P&L held to resolution and liquidity-reward yield: DEVELOPMENT study (prior-art gaps 5 and 6).

Read-only on its inputs; writes only ``--out``. No network. AREPO never trades.

  pnl      maker vs taker P&L per contract held to resolution, by market class, one unit per event,
           from the history backfills' Data API taker prints (``history/<run>/trades/<market_id>.csv.gz``)
           and the frames' resolved ``outcome_prices``.
  rewards  paper liquidity-reward yield of a minimum-size two-sided quote, bounded, from the snapshot
           sidecar (``rows_ext.csv.gz``: Gamma ``clobRewards``, ``rewardsMinSize``, ``rewardsMaxSpread``)
           and the paired book sweep (``book_sweeps/<id>/rows.csv.gz``).

Examples (host, read-only, output to a scratch dir):
  python scripts/run_maker_dev.py pnl --history-root ~/arepo/data-dumps/research_lab/history \
      --runs h2_main h3_power --out /tmp/makerdev/pnl
  python scripts/run_maker_dev.py rewards --research-root ~/arepo/data-dumps/research_lab --n-pairs 12 \
      --out /tmp/makerdev/rewards
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from astrolabe.research_lab import maker_rewards as mr  # noqa: E402

DEV_END_UTC = 1792627200  # 2026-10-22T00:00:00Z: development data strictly before this
UPDOWN_RE = re.compile(r"up-?or-?down|updown", re.I)
SAMPLE_COLS = ["market_id", "event_id", "fee_category", "status", "closed", "outcome_prices", "neg_risk",
               "start_epoch", "end_epoch", "close_epoch"]


def _truncated(run_dir: Path) -> set[str]:
    out: set[str] = set()
    p = run_dir / "progress.jsonl"
    if p.exists():
        for line in p.open():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("trades_truncated"):
                out.add(str(r.get("market_id")))
    return out


def cmd_pnl(a: argparse.Namespace) -> dict:
    t0 = time.time()
    acc = mr.Accumulator()
    ex: Counter = Counter()
    seen: set[str] = set()
    crypto_check: Counter = Counter()
    per_run: dict = {}
    for run in a.runs:
        rd = Path(a.history_root).expanduser() / run
        cols = pd.read_csv(rd / "sample.csv.gz", nrows=0).columns
        use = [c for c in SAMPLE_COLS + ["slug"] if c in cols]
        s = pd.read_csv(rd / "sample.csv.gz", usecols=use, dtype={"market_id": str, "event_id": str})
        trunc = _truncated(rd)
        n_used = 0
        for r in s.itertuples(index=False):
            mid = str(r.market_id)
            if a.max_markets and n_used >= a.max_markets:
                break
            if mid in seen:
                ex["duplicate_market_across_runs"] += 1
                continue
            seen.add(mid)
            if str(r.status) != "closed":
                ex["not_closed_at_fetch"] += 1
                continue
            y0 = mr.parse_resolution(r.outcome_prices)
            if y0 is None:
                ex["not_resolved_0_1 (50/50 or other)"] += 1
                continue
            if mid in trunc and not a.include_truncated:
                ex["trades_truncated"] += 1
                continue
            tp = rd / "trades" / f"{mid}.csv.gz"
            if not tp.exists():
                ex["no_trade_file"] += 1
                continue
            t = pd.read_csv(tp, usecols=["ts", "side", "size", "price", "outcome_index"])
            close = r.close_epoch if math.isfinite(r.close_epoch) else r.end_epoch
            if not math.isfinite(close):
                ex["no_close_time"] += 1
                continue
            ok = (t.side.isin(["BUY", "SELL"]) & t.outcome_index.isin([0, 1]) & (t.price > 0) & (t.price < 1)
                  & (t["size"] > 0) & (t.ts < close) & (t.ts < DEV_END_UTC))
            ex["fills_dropped_after_close_or_invalid"] += int((~ok).sum())
            t = t[ok]
            if t.empty:
                ex["no_fills_before_close"] += 1
                continue
            cls = mr.market_class(r.fee_category, r.neg_risk, r.start_epoch, r.end_epoch)
            if cls == "crypto_short" and "slug" in use:
                crypto_check["updown_slug" if UPDOWN_RE.search(str(r.slug)) else "other_slug"] += 1
            unit = f"e:{r.event_id}" if isinstance(r.event_id, str) and r.event_id not in ("", "nan") else f"m:{mid}"
            f = mr.per_fill(t.side.values, t.outcome_index.values, t.price.values, t["size"].values, t.ts.values,
                            y0, r.fee_category)
            acc.add_market(unit, cls, float(close), f)
            n_used += 1
        per_run[run] = {"sample_rows": int(len(s)), "markets_used": n_used, "truncated_listed": len(trunc)}
    cells: dict = {}
    nb, seed = a.n_boot, a.seed
    ex_sports = [c for c in mr.CLASSES if c != "sports"]

    def put(name: str, **sel) -> None:
        _, tab = acc.unit_table(**sel)
        cells[name] = mr.summarise(tab, n_boot=nb, seed=seed, min_units=a.min_units)

    put("all_incl_sports")
    put("all_ex_sports", classes=ex_sports)
    fav = [b[2] for b in mr.PRICE_BANDS if b[0] >= 0.5]
    lng = [b[2] for b in mr.PRICE_BANDS if b[0] < 0.5]
    for c in mr.CLASSES:
        put(f"class={c}", classes=[c])
        put(f"class={c}|maker_bought>=0.50", classes=[c], pbands=fav)
        put(f"class={c}|maker_bought<0.50", classes=[c], pbands=lng)
        put(f"class={c}|h>30d", classes=[c], horizons=["h>30d"])
    for h in mr.HORIZON_BANDS:
        put(f"ex_sports|{h[2]}", classes=ex_sports, horizons=[h[2]])
    for p in mr.PRICE_BANDS:
        put(f"ex_sports|maker_bought {p[2]}", classes=ex_sports, pbands=[p[2]])
        put(f"sports|maker_bought {p[2]}", classes=["sports"], pbands=[p[2]])
    return {"version": mr.VERSION, "kind": "development (exploratory_historical; not a test, not counted)",
            "runs": a.runs, "per_run": per_run, "exclusions": dict(ex), "crypto_short_slug_check": dict(crypto_check),
            "units": "event (event_id; market id when absent)", "n_boot": nb, "seed": seed,
            "min_units": a.min_units, "dev_end_utc": DEV_END_UTC, "cells": cells, "runtime_s": round(time.time() - t0, 1)}


# ---------------------------------------------------------------------------------------------
EXT_COLS = ["market_id", "condition_id", "clob_token_id_0", "clob_token_id_1", "fee_category", "rewards_min_size",
            "rewards_max_spread", "clob_rewards", "neg_risk_market_id"]
SWEEP_COLS = ["token_id", "best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c",
              "depth_bid_5c", "depth_ask_5c", "state"]


def _pairs(root: Path, n: int) -> list[tuple[Path, Path]]:
    pairs: dict[str, Path] = {}
    for sd in sorted((root / "book_sweeps").iterdir(), reverse=True):
        man = sd / "manifest.json"
        if not man.exists() or not (sd / "rows.csv.gz").exists():
            continue
        try:
            m = json.loads(man.read_text())
        except json.JSONDecodeError:
            continue
        snap = root / "snapshots" / str(m.get("snapshot_id"))
        if m.get("state") == "complete" and (snap / "rows_ext.csv.gz").exists() and m["snapshot_id"] not in pairs:
            if snap.name[:15] < "20261022T000000":
                pairs[m["snapshot_id"]] = sd
        if len(pairs) >= n:
            break
    return [(root / "snapshots" / k, v) for k, v in sorted(pairs.items())]


def cmd_rewards(a: argparse.Namespace) -> dict:
    t0 = time.time()
    root = Path(a.research_root).expanduser()
    per_pair, per_market = [], {}
    for snap, sweep in _pairs(root, a.n_pairs):
        e = pd.read_csv(snap / "rows_ext.csv.gz", usecols=EXT_COLS, dtype={c: str for c in ("market_id", "condition_id", "clob_token_id_0", "clob_token_id_1", "clob_rewards", "neg_risk_market_id", "fee_category")})
        day = f"{snap.name[:4]}-{snap.name[4:6]}-{snap.name[6:8]}"
        e["rate"] = [mr.parse_daily_rate(x, day) for x in e.clob_rewards.fillna("")]
        e = e[(e.rate > 0)]
        b = pd.read_csv(sweep / "rows.csv.gz", usecols=SWEEP_COLS, dtype={"token_id": str})
        b = b[b.state == "two_sided"].drop_duplicates("token_id").set_index("token_id")
        books = b.to_dict("index")
        st: Counter = Counter()
        rows = []
        for r in e.itertuples(index=False):
            st["reward_markets"] += 1
            t0b = books.get(str(r.clob_token_id_0))
            if t0b is None:
                st["no_two_sided_book"] += 1
                continue
            res = mr.paper_quote_reward(float(r.rate), float(r.rewards_max_spread or 0), float(r.rewards_min_size or 0),
                                        t0b, books.get(str(r.clob_token_id_1)))
            if res is None or not res["scorable"]:
                st["not_scorable"] += 1
                continue
            st["scored"] += 1
            cls = mr.fee_key(r.fee_category)
            rows.append((r.market_id, cls, float(r.rate), res))
            pm = per_market.setdefault(r.market_id, {"cls": cls, "rate": [], "low": [], "high": [], "ylow": [], "yhigh": [], "cap": []})
            pm["rate"].append(float(r.rate))
            pm["low"].append(res["reward_low"])
            pm["high"].append(res["reward_high"])
            pm["ylow"].append(res["yield_low"])
            pm["yhigh"].append(res["yield_high"])
            pm["cap"].append(res["capital"])
        per_pair.append({"snapshot": snap.name, "sweep": sweep.name, **dict(st),
                         "pool_usd_day_reward_markets": float(e.rate.sum()),
                         "pool_usd_day_scored": float(sum(x[2] for x in rows))})
    # per-market means across pairs -> distribution across markets
    def q(v: np.ndarray) -> dict:
        v = v[np.isfinite(v)]
        if not len(v):
            return {}
        return {k: float(np.percentile(v, p)) for k, p in (("p25", 25), ("median", 50), ("p75", 75), ("p90", 90))} | {"mean": float(v.mean())}

    out_cls: dict = {}
    allm = list(per_market.values())
    groups = {"all": allm} | {c: [m for m in allm if m["cls"] == c] for c in sorted({m["cls"] for m in allm})}
    for g, ms in groups.items():
        if not ms:
            continue
        rl = np.array([np.mean(m["low"]) for m in ms])
        rh = np.array([np.mean(m["high"]) for m in ms])
        yl = np.array([np.nanmean(m["ylow"]) for m in ms])
        yh = np.array([np.nanmean(m["yhigh"]) for m in ms])
        cap = np.array([np.nanmean(m["cap"]) for m in ms])
        out_cls[g] = {"markets": len(ms), "rate_usd_day": q(np.array([np.mean(m["rate"]) for m in ms])),
                      "reward_usd_day_low": q(rl), "reward_usd_day_high": q(rh),
                      "yield_pct_day_low": q(100 * yl), "yield_pct_day_high": q(100 * yh),
                      "capital_usd": q(cap),
                      # filled shares per day at 1c adverse selection that the reward would pay for
                      "breakeven_shares_at_1c_low": q(rl / 0.01), "breakeven_shares_at_1c_high": q(rh / 0.01),
                      "share_markets_yield_high_ge_0.1pct_day": float(np.mean(yh >= 0.001))}
    return {"version": mr.VERSION, "kind": "development (descriptive; stationary-book paper quote; not a test, not counted)",
            "quote": "min-size two-sided on outcome 0 at s = max(v/2, half-spread); stationary book over the day; mid = touch mid (not size-adjusted)",
            "pairs": per_pair, "by_class": out_cls, "runtime_s": round(time.time() - t0, 1)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pnl")
    p.add_argument("--history-root", required=True)
    p.add_argument("--runs", nargs="+", default=["h2_main", "h3_power"])
    p.add_argument("--out", required=True)
    p.add_argument("--max-markets", type=int, default=0)
    p.add_argument("--include-truncated", action="store_true")
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20261020)
    p.add_argument("--min-units", type=int, default=30)
    r = sub.add_parser("rewards")
    r.add_argument("--research-root", required=True)
    r.add_argument("--n-pairs", type=int, default=12)
    r.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    sealed = ("h5_cb1", "h6_weather")
    if a.cmd == "pnl" and any(x in sealed for x in a.runs):
        print(f"refused: {sealed} are sealed for registered tests", file=sys.stderr)
        return 2
    res = cmd_pnl(a) if a.cmd == "pnl" else cmd_rewards(a)
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    (out / f"maker_dev_{a.cmd}.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps({"done": a.cmd, "runtime_s": res.get("runtime_s")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
