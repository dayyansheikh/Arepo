"""Paper-only economic-conditions study, part B: passive (maker) entry on historical pmxt books.

Exploratory/historical. Books: pmxt v2 hourly archive at 6h-grid origins (book_features rows.jsonl).
Prints: Data API trades of the h2_main backfill. Fill in (t0, t_j] vs. print stream. Never executed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from econ_conditions_taker import boot  # noqa: E402

from astrolabe.research_lab import economics, forecast  # noqa: E402

H = forecast.ROOT / "data-dumps/research_lab/history/h2_main"
BF = forecast.ROOT / "data-dumps/research_lab/history_sources/book_features/rows.jsonl"
# Maker rebate share of taker fees by category (docs.polymarket.com/trading/fees, fetched 2026-10-12)
REBATE = {"crypto": 0.20, "sports": 0.15, "finance": 0.25, "politics": 0.25, "economics": 0.25,
          "culture": 0.25, "weather": 0.25, "other": 0.25, "mentions": 0.25, "tech": 0.25}
OWN = 5.0  # own order size (shares) for the queue variant


def prints_token0(mid: str) -> pd.DataFrame | None:
    p = H / "trades" / f"{mid}.csv.gz"
    if not p.exists():
        return None
    t = pd.read_csv(p, usecols=["ts", "side", "size", "price", "outcome_index"])
    t = t[t.outcome_index.isin([0, 1]) & t.side.isin(["BUY", "SELL"])]
    o1 = t.outcome_index == 1
    buy_taker = (t.side == "BUY") != o1  # taker buys token0 (BUY of 0, or SELL of 1)
    out = pd.DataFrame({"ts": t.ts.to_numpy(float), "p0": np.where(o1, 1 - t.price, t.price),
                        "buy": buy_taker.to_numpy(), "size": t["size"].to_numpy(float)})
    return out.sort_values("ts").reset_index(drop=True)


def main(out: str) -> None:
    bf = pd.read_json(BF, lines=True, dtype={"market_id": str, "token_id": str})
    bf["market_id"] = bf.market_id.astype(str)
    bf = bf[(bf.state == "two_sided") & bf.sw_best_bid.notna() & (bf.sw_best_ask > bf.sw_best_bid)]
    pan = pd.read_csv(H / "panel_H2h.csv.gz", dtype={"market_id": str}, usecols=[
        "market_id", "event_id", "t_i", "t_j", "mid_i", "mid_j", "dmid", "ml_chg_1h", "fee_category",
        "traded_before_t", "dep_group"])
    df = bf.merge(pan, left_on=["market_id", "origin_ts"], right_on=["market_id", "t_i"], how="inner")
    n0 = len(df)
    df = df[(df.traded_before_t != 0) & df.mid_j.notna() & df.mid_i.between(0.02, 0.98)].copy()
    df["mid0"] = (df.sw_best_bid + df.sw_best_ask) / 2
    df["cl"] = np.where(df.dep_group.notna(), df.dep_group.astype(str), df.event_id.astype(str))
    rows = []
    cache: dict[str, pd.DataFrame | None] = {}
    for r in df.itertuples():
        if r.market_id not in cache:
            cache[r.market_id] = prints_token0(r.market_id)
        pr = cache[r.market_id]
        ss = 0.0
        if pr is not None:
            w1 = pr[(pr.ts >= r.t_i - 3600) & (pr.ts < r.t_i)]
            vol = w1["size"].sum()
            ss = float(((np.where(w1.buy, 1, -1)) * w1["size"]).sum() / vol) if vol > 0 else 0.0
        chg = r.ml_chg_1h if pd.notna(r.ml_chg_1h) else 0.0
        for sig, d in (("reversal", -np.sign(chg)), ("flow", np.sign(ss)),
                       ("agree", np.sign(ss) if (chg != 0 and ss != 0 and -np.sign(chg) == np.sign(ss)) else 0.0)):
            if d == 0:
                continue
            b, a = r.sw_best_bid, r.sw_best_ask
            entry = b if d > 0 else a
            fills = {"touch": False, "through": False, "queue": False}
            tf = {}
            if pr is not None:
                win = pr[(pr.ts > r.t_i) & (pr.ts <= r.t_j)]
                if d > 0:
                    hit = win[(~win.buy) & (win.p0 <= b + 1e-9)]
                    thr = hit[hit.p0 < b - 1e-9]
                    qsz = r.sw_bid_size_1
                else:
                    hit = win[win.buy & (win.p0 >= a - 1e-9)]
                    thr = hit[hit.p0 > a + 1e-9]
                    qsz = r.sw_ask_size_1
                if len(hit):
                    fills["touch"], tf["touch"] = True, hit.ts.iloc[0]
                if len(thr):
                    fills["through"], tf["through"] = True, thr.ts.iloc[0]
                cum = hit["size"].cumsum()
                need = (qsz if pd.notna(qsz) else 0.0) + OWN
                if len(hit) and (cum >= need).any():
                    fills["queue"], tf["queue"] = True, hit.ts[(cum >= need).to_numpy()].iloc[0]
            cat = str(r.fee_category).split(":")[0]
            rate = economics.DOCS_CATEGORY_RATE.get(cat, economics.MAX_DOCS_RATE)
            fee = lambda p: rate * p * (1 - p)  # noqa: E731
            hs = (a - b) / 2
            rows.append(dict(market_id=r.market_id, cl=r.cl, sig=sig, d=d, t0=r.t_i, spread=a - b,
                             cat=cat, entry=entry, mid0=r.mid0, mid_j=r.mid_j,
                             move=d * (r.mid_j - r.mid0), pnl_mark=d * (r.mid_j - entry),
                             pnl_taker_exit=d * (r.mid_j - entry) - hs - fee(r.mid_j),
                             rebate=REBATE.get(cat, 0.0) * fee(entry),
                             taker_entry_net=d * (r.mid_j - (a if d > 0 else b)) - hs - fee(r.mid_j)
                             - fee(a if d > 0 else b),
                             **{f"fill_{k}": v for k, v in fills.items()}))
    O = pd.DataFrame(rows)
    res: dict = {"n_book_rows_joined": int(n0), "n_after_filters": int(len(df)), "n_orders": int(len(O)),
                 "mid_source_gap_abs_mean": float((df.mid0 - df.mid_i).abs().mean()), "cells": {}}
    for sig in ("reversal", "flow", "agree"):
        S = O[O.sig == sig]
        for sub, m in (("all", S.spread > 0), ("spread>=2c", S.spread >= 0.0199)):
            T = S[m]
            if len(T) < 30:
                continue
            res["cells"][f"{sig}|{sub}|taker entry @touch (same orders)"] = boot(
                T.cl.to_numpy(), T.taker_entry_net.to_numpy(), np.ones(len(T)))
            res["cells"][f"{sig}|{sub}|orders"] = {"n": int(len(T)),
                "mean_move_all": float(T.move.mean()), "mean_spread": float(T.spread.mean())}
            for rule in ("touch", "through", "queue"):
                F = T[T[f"fill_{rule}"]]
                U = T[~T[f"fill_{rule}"]]
                info = {"n_orders": int(len(T)), "n_filled": int(len(F)), "fill_rate": float(len(F) / len(T)),
                        "mean_move_filled": float(F.move.mean()) if len(F) else None,
                        "mean_move_unfilled": float(U.move.mean()) if len(U) else None,
                        "mean_pnl_mark_filled": float(F.pnl_mark.mean()) if len(F) else None}
                for ex, col in (("markexit", "pnl_mark"), ("takerexit", "pnl_taker_exit")):
                    for rb in (False, True):
                        v = (F[col] + (F.rebate if rb else 0)).to_numpy()
                        key = f"{sig}|{sub}|{rule}|{ex}|{'rebate' if rb else 'norebate'}"
                        c = boot(F.cl.to_numpy(), v, np.ones(len(F))) if len(F) else {"n": 0, "testable": False}
                        c.update(info)
                        c["ev_per_order"] = float(np.sum(v) / len(T)) if len(F) else 0.0
                        res["cells"][key] = c
    Path(out).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1])
