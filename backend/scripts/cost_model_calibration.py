# ruff: noqa: E501
"""Development calibration of the paper execution-cost model (``astrolabe.research_lab.costs``).

Read-only. Reads recorded book sweeps, their snapshots and later trade samples from a DEVELOPMENT
window, and writes one summary JSON (plus an optional per-order CSV) under ``--out`` only.
Never writes into the data root. No network. AREPO never trades; nothing here simulates an order
against a venue.

What it measures (all per outcome-0 token, two-sided books):
1. Quote distributions by liquidity tier and fee category: spread, book age, touch depth and depth
   within 1c / 5c in USDC, taker fillability and impact for 10 / 100 / 1000 USDC (conservative walk on
   the sweep summary, ``costs.levels_from_summary``), $100 taker round trip, 2h mid-change SD.
2. Maker fills: a hypothetical order of ``q`` shares joins the BACK of the queue at each touch at the
   sweep receipt time. Over ``(t, t + H]`` it fills under the ``touch`` rule if any taker trade hits
   its price or through it, and under the ``queue`` rule if a trade goes through its price or the
   hitting volume at its price reaches queue-ahead + q (cancellations ahead ignored: conservative).
   Taker trades come from the first trade sample that starts after ``t + H``; a market is used only
   if that sample's 500-trade page reaches back to ``t`` (else excluded and counted). Mark-out: the
   mid of the first sweep at least ``--mark-min-s`` after ``t``. Realised spread = mark - bid (bid
   side) or ask - mark (ask side); adverse selection = half-spread - realised spread.
3. Fit of ``costs.fill_probability`` per tier: ``p_active`` = share of orders with any hitting
   trade; Lomax ``(scale, alpha)`` by maximum likelihood of the queue-rule fill among active
   orders; predicted vs observed fill rate by queue-size quintile is reported as validation.

Uncertainty: cluster bootstrap over events (market id when no event), seed 116.

Usage (host, temp dir only)::

    PYTHONPATH=/tmp/costmodel/src python cost_model_calibration.py \
        --data-root ~/arepo/data-dumps/research_lab --start 2026-10-12T00:00Z --end 2026-10-14T00:00Z \
        --out /tmp/costmodel/out
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import costs

VERSION = "cost-model-calibration-v1"
SEED = 116
N_BOOT = 400
NOTIONALS = (10.0, 100.0, 1000.0)
TRADE_PAGE = 500  # trade_sample.TRADE_LIMIT
EPS = 1e-6
SWEEP_COLS = ["token_id", "market_id", "batch_receipt_utc", "book_timestamp", "best_bid", "best_ask",
              "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c",
              "tick_size", "min_order_size", "state"]
SNAP_COLS = ["market_id", "clob_token_id_0", "event_id", "liquidity", "volume24hr"]
EXT_COLS = ["market_id", "fee_category", "fees_enabled", "fee_schedule", "rewards_max_spread",
            "rewards_min_size", "clob_rewards"]
TRADE_COLS = ["market_id", "ts", "side", "price", "size", "outcome_index"]


def parse_name_ts(name: str) -> float:
    return datetime.strptime(name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()


def parse_iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def list_runs(root: Path) -> list[tuple[float, Path]]:
    out = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and len(d.name) >= 16:
            try:
                out.append((parse_name_ts(d.name), d))
            except ValueError:
                continue
    return out


def first_of_pairs(runs: list[tuple[float, Path]], gap_s: float = 900.0) -> list[tuple[float, Path]]:
    keep: list[tuple[float, Path]] = []
    for t, d in runs:
        if not keep or t - keep[-1][0] > gap_s:
            keep.append((t, d))
    return keep


def schedule_rate(raw) -> tuple[float, float]:
    """(rate, rebateRate) from a feeSchedule JSON string; NaN when absent."""
    if not isinstance(raw, str) or not raw.strip():
        return math.nan, math.nan
    try:
        d = json.loads(raw)
        return float(d.get("rate", math.nan)), float(d.get("rebateRate", math.nan))
    except (ValueError, TypeError, AttributeError):
        return math.nan, math.nan


def fees_flag(v) -> bool | None:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    t = str(v).strip().lower()
    return True if t in ("1", "1.0", "true") else False if t in ("0", "0.0", "false") else None


def load_sweep(d: Path) -> tuple[pd.DataFrame, dict]:
    man = json.loads((d / "manifest.json").read_text())
    df = pd.read_csv(d / "rows.csv.gz", usecols=SWEEP_COLS, dtype={"token_id": str, "market_id": str})
    df["t"] = df["batch_receipt_utc"].map(parse_iso)
    df["book_age_s"] = df["t"] - pd.to_numeric(df["book_timestamp"], errors="coerce") / 1000.0
    return df, man


def load_snapshot(snap_root: Path, snap_id: str) -> pd.DataFrame | None:
    d = snap_root / snap_id
    if not (d / "rows.csv.gz").exists():
        return None
    s = pd.read_csv(d / "rows.csv.gz", usecols=SNAP_COLS, dtype={"market_id": str, "clob_token_id_0": str,
                                                                 "event_id": str})
    s = s.drop_duplicates("market_id")
    if (d / "rows_ext.csv.gz").exists():
        e = pd.read_csv(d / "rows_ext.csv.gz", usecols=EXT_COLS, dtype={"market_id": str, "fee_schedule": str,
                                                                       "clob_rewards": str})
        s = s.merge(e.drop_duplicates("market_id"), on="market_id", how="left")
    for c in EXT_COLS[1:]:
        if c not in s.columns:
            s[c] = np.nan
    return s


def book_rows(sw: pd.DataFrame, snap: pd.DataFrame, nxt: pd.DataFrame | None) -> pd.DataFrame:
    """Per-token quote/depth/taker-cost rows for one origin sweep."""
    df = sw[sw["state"] == "two_sided"].merge(snap, on="market_id", how="inner")
    df = df[df["token_id"] == df["clob_token_id_0"]]
    if nxt is not None:
        nm = nxt[nxt["state"] == "two_sided"].assign(mid_next=lambda x: (x.best_bid + x.best_ask) / 2)
        df = df.merge(nm[["token_id", "mid_next", "t"]].rename(columns={"t": "t_next"}), on="token_id", how="left")
    else:
        df["mid_next"], df["t_next"] = np.nan, np.nan
    recs = []
    for r in df.itertuples(index=False):
        bid, ask = float(r.best_bid), float(r.best_ask)
        mid, spr = (bid + ask) / 2, ask - bid
        tick = float(r.tick_size) if pd.notna(r.tick_size) else 0.01
        la = costs.levels_from_summary(ask, r.ask_size_1, r.depth_ask_1c, r.depth_ask_5c, lift_asks=True, tick=tick)
        lb = costs.levels_from_summary(bid, r.bid_size_1, r.depth_bid_1c, r.depth_bid_5c, lift_asks=False, tick=tick)
        srate, rebate = schedule_rate(r.fee_schedule if hasattr(r, "fee_schedule") else None)
        rate = costs.taker_rate(getattr(r, "fee_category", None), srate, fees_flag(getattr(r, "fees_enabled", None)))
        rec = {"market_id": r.market_id, "event_id": r.event_id if isinstance(r.event_id, str) else r.market_id,
               "liq": float(r.liquidity) if pd.notna(r.liquidity) else 0.0,
               "cat": costs.category_key(getattr(r, "fee_category", None)) or "unknown",
               "mid": mid, "spread": spr, "tick": tick, "book_age_s": r.book_age_s, "rate": rate,
               "sched_rate": srate, "rebate_rate": rebate,
               "rewards": int(isinstance(getattr(r, "clob_rewards", None), str) and len(str(r.clob_rewards)) > 4),
               "rewards_max_spread": getattr(r, "rewards_max_spread", np.nan),
               "touch_usd_bid": bid * r.bid_size_1, "touch_usd_ask": ask * r.ask_size_1,
               "d1_usd_ask": costs.depth_notional_within(la, 0.01), "d5_usd_ask": costs.depth_notional_within(la, 0.05),
               "d1_usd_bid": costs.depth_notional_within(lb, 0.01), "d5_usd_bid": costs.depth_notional_within(lb, 0.05),
               "dmid_2h": (r.mid_next - mid) if pd.notna(r.mid_next) else np.nan,
               "dt_next_h": (r.t_next - r.t) / 3600 if pd.notna(r.t_next) else np.nan}
        for n in NOTIONALS:
            wb = costs.walk(la, notional=n)
            rec[f"buy{int(n)}_ok"] = int(not wb.exhausted)
            rec[f"buy{int(n)}_impact"] = wb.impact_ps if not wb.exhausted else np.nan
            if n == 100.0 and not wb.exhausted:
                ws = costs.walk(lb, shares=wb.filled_shares)
                if not ws.exhausted:
                    q = wb.filled_shares
                    fee = costs.taker_fee_ps(wb.vwap, rate) + costs.taker_fee_ps(ws.vwap, rate)
                    rec["rt100"] = (wb.cash - ws.cash) / q + fee
                    rec["rt100_fee"] = fee
        recs.append(rec)
    return pd.DataFrame(recs)


def maker_rows(sw: pd.DataFrame, snap: pd.DataFrame, trades: pd.DataFrame, nxt: pd.DataFrame | None,
               horizons: tuple[float, ...], own_shares: float) -> tuple[pd.DataFrame, dict]:
    """Hypothetical back-of-queue touch orders (both sides) for markets the trade sample covers."""
    df = sw[sw["state"] == "two_sided"].merge(snap[["market_id", "clob_token_id_0", "event_id", "liquidity",
                                                    "fee_category"]], on="market_id", how="inner")
    df = df[df["token_id"] == df["clob_token_id_0"]]
    if nxt is not None:
        nm = nxt[nxt["state"] == "two_sided"].assign(mark=lambda x: (x.best_bid + x.best_ask) / 2)
        df = df.merge(nm[["token_id", "mark"]], on="token_id", how="left")
    else:
        df["mark"] = np.nan
    tr = trades[trades["market_id"].isin(set(df["market_id"]))]
    groups = {k: g for k, g in tr.groupby("market_id")}
    cnt = {"sample_markets_in_origin": 0, "excluded_page_short": 0, "used": 0}
    recs = []
    for r in df.itertuples(index=False):
        g = groups.get(r.market_id)
        if g is None:
            continue
        cnt["sample_markets_in_origin"] += 1
        ts = g["ts"].to_numpy(float)
        if len(ts) >= TRADE_PAGE and ts.min() > r.t:
            cnt["excluded_page_short"] += 1
            continue
        cnt["used"] += 1
        oi = g["outcome_index"].to_numpy()
        sell = (g["side"].to_numpy() == "SELL")
        px = g["price"].to_numpy(float)
        sz = g["size"].to_numpy(float)
        p0 = np.where(oi == 1, 1.0 - px, px)
        hit_bid = ((oi == 0) & sell) | ((oi == 1) & ~sell)  # taker sells outcome 0 (or buys outcome 1)
        bid, ask = float(r.best_bid), float(r.best_ask)
        h = (ask - bid) / 2
        base = {"market_id": r.market_id, "event_id": r.event_id if isinstance(r.event_id, str) else r.market_id,
                "liq": float(r.liquidity) if pd.notna(r.liquidity) else 0.0,
                "cat": costs.category_key(r.fee_category) or "unknown", "mid": (bid + ask) / 2, "half_spread": h}
        for side, price, qa in (("bid", bid, float(r.bid_size_1)), ("ask", ask, float(r.ask_size_1))):
            hits = hit_bid if side == "bid" else ~hit_bid
            at = (p0 <= price + EPS) if side == "bid" else (p0 >= price - EPS)
            thr = (p0 < price - EPS) if side == "bid" else (p0 > price + EPS)
            rec = dict(base, side=side, queue_ahead=qa, queue_usd=qa * price,
                       realised=((r.mark - price) if side == "bid" else (price - r.mark)) if pd.notna(r.mark) else np.nan)
            for H in horizons:
                w = (ts > r.t) & (ts <= r.t + H) & hits
                vol = float(sz[w & at].sum())
                through = bool((w & thr).any())
                rec[f"hit_vol_{int(H)}"] = vol
                rec[f"fill_touch_{int(H)}"] = int(vol > 0)
                rec[f"fill_queue_{int(H)}"] = int(through or vol >= qa + own_shares)
            recs.append(rec)
    return pd.DataFrame(recs), cnt


# ------------------------------------------------------------------ summaries


def tier_col(df: pd.DataFrame) -> pd.Series:
    return df["liq"].map(costs.liquidity_tier)


def qtiles(x: pd.Series, scale: float = 1.0, qs=(0.1, 0.25, 0.5, 0.75, 0.9)) -> dict:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), **{f"p{int(q * 100)}": round(float(x.quantile(q)) * scale, 4) for q in qs},
            "mean": round(float(x.mean()) * scale, 4)}


def cluster_boot(df: pd.DataFrame, num: str, den: str | None, rng: np.random.Generator) -> dict:
    """Ratio estimate sum(num)/sum(den) (den None -> count) with a cluster bootstrap 95% CI over event_id."""
    d = df[[num, "event_id"] + ([den] if den else [])].dropna()
    if len(d) == 0:
        return {"n": 0}
    d = d.assign(_den=d[den] if den else 1.0)
    g = d.groupby("event_id").agg(n=(num, "sum"), d=("_den", "sum"))
    n, dd = g["n"].to_numpy(), g["d"].to_numpy()
    est = n.sum() / dd.sum()
    k = len(g)
    idx = rng.integers(0, k, size=(N_BOOT, k))
    bs = n[idx].sum(1) / np.maximum(dd[idx].sum(1), 1e-12)
    return {"n": int(len(d)), "clusters": int(k), "est": round(float(est), 5),
            "ci95": [round(float(np.quantile(bs, 0.025)), 5), round(float(np.quantile(bs, 0.975)), 5)]}


def fit_lomax(active: pd.DataFrame, H: int, own: float) -> tuple[float, float]:
    """MLE of (scale, alpha) in P(queue fill | active) = (1 + (Q + q) / scale) ** -alpha on a log grid.

    Pareto-II (Lomax) survival of the hitting volume. An exponential survival was tried first and
    rejected: it over-predicted fills at short queues and under-predicted at long ones (heavy tail)."""
    if len(active) < 20:
        return math.nan, math.nan
    x = active["queue_ahead"].to_numpy(float) + own
    y = active[f"fill_queue_{H}"].to_numpy(float)
    best, arg = -np.inf, (math.nan, math.nan)
    for sc in np.exp(np.linspace(0.0, math.log(1e6), 70)):
        lx = np.log1p(x / sc)
        for al in np.exp(np.linspace(math.log(0.03), math.log(5.0), 60)):
            p = np.clip(np.exp(-al * lx), 1e-9, 1 - 1e-9)
            ll = float((y * np.log(p) + (1 - y) * np.log1p(-p)).sum())
            if ll > best:
                best, arg = ll, (float(sc), float(al))
    return arg


def summarise(books: pd.DataFrame, makers: pd.DataFrame, horizons, own: float) -> dict:
    rng = np.random.default_rng(SEED)
    out: dict = {"books": {}, "maker": {}}
    if len(books):
        books = books.assign(tier=tier_col(books))
        for by in ("tier", "cat"):
            tab = {}
            for k, d in books.groupby(by):
                tab[str(k)] = {
                    "n": int(len(d)), "markets": int(d["market_id"].nunique()),
                    "spread_c": qtiles(d["spread"], 100), "book_age_s": qtiles(d["book_age_s"]),
                    "touch_usd_ask": qtiles(d["touch_usd_ask"]), "d1_usd_ask": qtiles(d["d1_usd_ask"]),
                    "d5_usd_ask": qtiles(d["d5_usd_ask"]), "touch_usd_bid": qtiles(d["touch_usd_bid"]),
                    **{f"buy{int(n)}_fillable_5c": round(float(d[f"buy{int(n)}_ok"].mean()), 4) for n in NOTIONALS},
                    **{f"buy{int(n)}_impact_c": qtiles(d[f"buy{int(n)}_impact"], 100) for n in NOTIONALS},
                    "rt100_c": qtiles(d.get("rt100", pd.Series(dtype=float)), 100),
                    "rt100_fee_c": qtiles(d.get("rt100_fee", pd.Series(dtype=float)), 100),
                    "dmid_2h_sd_c": round(float(d["dmid_2h"].std()) * 100, 4) if d["dmid_2h"].notna().sum() > 2 else None,
                    "dmid_2h_mad_c": round(float(d["dmid_2h"].abs().median()) * 100, 4) if d["dmid_2h"].notna().any() else None,
                    "rewards_share": round(float(d["rewards"].mean()), 4),
                }
            out["books"][by] = tab
        out["books"]["all"] = {"n": int(len(books)), "spread_c": qtiles(books["spread"], 100),
                               "rt100_c": qtiles(books.get("rt100", pd.Series(dtype=float)), 100),
                               "book_age_s": qtiles(books["book_age_s"]),
                               "dt_next_h": qtiles(books["dt_next_h"])}
    if len(makers):
        makers = makers.assign(tier=tier_col(makers))
        makers["as_c"] = makers["half_spread"] - makers["realised"]
        for by in ("tier", "cat", "all"):
            tab = {}
            grp = [("all", makers)] if by == "all" else list(makers.groupby(by))
            for k, d in grp:
                row: dict = {"orders": int(len(d)), "markets": int(d["market_id"].nunique()),
                             "half_spread_c": qtiles(d["half_spread"], 100), "queue_usd": qtiles(d["queue_usd"])}
                for H in horizons:
                    H = int(H)
                    row[f"fill_touch_{H}"] = cluster_boot(d, f"fill_touch_{H}", None, rng)
                    row[f"fill_queue_{H}"] = cluster_boot(d, f"fill_queue_{H}", None, rng)
                    f = d[(d[f"fill_queue_{H}"] == 1) & d["realised"].notna()]
                    u = d[(d[f"fill_queue_{H}"] == 0) & d["realised"].notna()]
                    row[f"realised_filled_{H}_c"] = {k2: (v * 100 if isinstance(v, float) else
                                                          [x * 100 for x in v] if isinstance(v, list) else v)
                                                     for k2, v in cluster_boot(f, "realised", None, rng).items()}
                    row[f"adverse_sel_filled_{H}_c"] = {k2: (v * 100 if isinstance(v, float) else
                                                             [x * 100 for x in v] if isinstance(v, list) else v)
                                                        for k2, v in cluster_boot(f, "as_c", None, rng).items()}
                    row[f"realised_unfilled_{H}_c"] = round(float(u["realised"].mean()) * 100, 4) if len(u) else None
                    act = d[d[f"hit_vol_{H}"] > 0]
                    row[f"p_active_{H}"] = round(float(len(act) / len(d)), 5)
                    sc, al = fit_lomax(act, H, own)
                    row[f"lomax_scale_shares_{H}"] = None if math.isnan(sc) else round(sc, 3)
                    row[f"lomax_alpha_{H}"] = None if math.isnan(al) else round(al, 4)
                    if not math.isnan(sc):
                        pa = row[f"p_active_{H}"]
                        pred = pd.Series([costs.fill_probability(qa, own, pa, sc, al) for qa in d["queue_ahead"]], index=d.index)
                        b = pd.qcut(d["queue_usd"], 5, duplicates="drop")
                        row[f"validation_{H}"] = [
                            {"queue_usd_bin": str(k3), "n": int(len(g)), "observed": round(float(g[f"fill_queue_{H}"].mean()), 4),
                             "predicted": round(float(pred.loc[g.index].mean()), 4)} for k3, g in d.groupby(b, observed=True)]
                tab[str(k)] = row
            out["maker"][by] = tab
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--horizons", default="900,3600")
    ap.add_argument("--own-shares", type=float, default=5.0)
    ap.add_argument("--mark-min-s", type=float, default=5400.0)
    ap.add_argument("--book-every", type=int, default=2, help="book stats on every k-th origin")
    ap.add_argument("--max-origins", type=int, default=0)
    ap.add_argument("--write-orders", action="store_true")
    a = ap.parse_args(argv)
    root = a.data_root.expanduser().resolve()
    out = a.out.expanduser().resolve()
    if out == root or root in out.parents:
        print("refusing to write inside the data root", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    t0, t1 = parse_iso(a.start), parse_iso(a.end)
    horizons = tuple(float(x) for x in a.horizons.split(","))
    sweeps = first_of_pairs(list_runs(root / "book_sweeps"))
    samples = list_runs(root / "trade_samples")
    origins = [(t, d) for t, d in sweeps if t0 <= t < t1]
    if a.max_origins:
        origins = origins[: a.max_origins]
    books, makers, used = [], [], []
    started = time.time()
    for i, (t, d) in enumerate(origins):
        sw, man = load_sweep(d)
        if man.get("state") != "complete":
            continue
        snap = load_snapshot(root / "snapshots", man["snapshot_id"])
        if snap is None:
            continue
        nxt_run = next(((tt, dd) for tt, dd in sweeps if tt >= t + a.mark_min_s), None)
        if nxt_run is None or nxt_run[0] >= t1 + 4 * 3600:
            nxt = None
        else:
            nxt, _ = load_sweep(nxt_run[1])
        rec = {"sweep": d.name, "snapshot": man["snapshot_id"], "mark_sweep": nxt_run[1].name if nxt is not None else None}
        if i % a.book_every == 0:
            books.append(book_rows(sw, snap, nxt))
        smp = next(((tt, dd) for tt, dd in samples if tt >= sw["t"].max() + max(horizons) + 60), None)
        if smp is not None and smp[0] < t1 + 4 * 3600 and (smp[1] / "trades.csv.gz").exists():
            tr = pd.read_csv(smp[1] / "trades.csv.gz", usecols=TRADE_COLS, dtype={"market_id": str})
            m, cnt = maker_rows(sw, snap, tr, nxt, horizons, a.own_shares)
            makers.append(m)
            rec.update(trade_sample=smp[1].name, **cnt)
            del tr
        used.append(rec)
        print(f"[{i + 1}/{len(origins)}] {d.name} books={sum(len(b) for b in books)} "
              f"orders={sum(len(m) for m in makers)} {time.time() - started:.0f}s", flush=True)
        del sw, snap, nxt
    B = pd.concat(books, ignore_index=True) if books else pd.DataFrame()
    M = pd.concat(makers, ignore_index=True) if makers else pd.DataFrame()
    summary = {"version": VERSION, "costs_version": costs.MAKER_DEFAULTS["version"],
               "window": [a.start, a.end], "horizons_s": list(horizons), "own_shares": a.own_shares,
               "mark_min_s": a.mark_min_s, "seed": SEED, "n_boot": N_BOOT, "inputs": used,
               "label": "development calibration (descriptive; not a test)",
               "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
               **summarise(B, M, horizons, a.own_shares)}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    if a.write_orders and len(M):
        M.to_csv(out / "maker_orders.csv.gz", index=False)
    print(f"done in {time.time() - started:.0f}s -> {out / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
