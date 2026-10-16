# ruff: noqa: E501
"""CB5-G network data jobs (docs/research_lab/CREATIVE_BATCH_5.md CB5-F; q0102, q0103, q0111).

* ``head_fetch`` (q0102): CLOB ``prices-history`` for the h2_main markets over ``[created - 1h, created + 4d + 1h]`` at fidelity 10,
  plus a day-0 fidelity-1 request ``[created - 1h, created + 24h]`` stored as a reported seed-resolution variant (recorded either
  way). Uses the h2 frame (ids, ``created_at``, ``end_epoch``, fee category) only; reads no trade and no outcome. Windows are
  anchored on ``created_at`` (coverage invariance) and end before ``T_h2_clock``.
* ``cohort_fetch`` (q0103 census, q0111 replication): prices and trades of listings seen in ``cb5_extract/listings``. The census
  cohort is stored ONLY up to ``min(first trade + 1h, L + 24h)`` (a parse guard drops later rows before anything is written) and is
  never used for G1/G2. The replication cohort is fetched at ``L + 4d + 2h`` for ``[L - 1h, L + 4d + 1h]``.

Data-only: no statistic. Rate limited through the shared ``history_backfill.Limiter`` (yields to the live collector, 429 back-off).
Wallet addresses are never stored (the hash column is blanked).
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
from typing import Any

import pandas as pd

from . import history_backfill as hb

HEAD_VERSION = "cb5-head-v1"
COHORT_VERSION = "cb5-cohort-v1"
H, D = 3600.0, 86400.0
HEAD_BEFORE_H, HEAD_AFTER_D, HEAD_AFTER_H = 1.0, 4.0, 1.0
T_H2_CLOCK = "2026-10-11T23:00:33Z"
MIN_LIFE_D = 4.0
MAX_TRADES = 10000
CENSUS_AFTER_TRADE_H = 1.0
CENSUS_WINDOW_H = 24.0
REP_FETCH_AFTER_H = 4 * 24 + 2.0
TRADE_COLS = ["ts", "side", "size", "price", "outcome_index", "wallet_hash", "trade_key"]
DAY0_FID1_WINDOW_H = 24.0
FRAME_NEEDED = ("market_id", "token0", "created_at", "end_epoch", "fee_category", "neg_risk")


class DiskCapExceeded(RuntimeError):
    """The job's own output would exceed its disk cap."""


def _gz_csv(path: Path, header: list[str], rows: list[list]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz, io.TextIOWrapper(gz, encoding="utf-8", newline="") as tw:
        import csv

        w = csv.writer(tw)
        w.writerow(header)
        w.writerows(rows)
    data = buf.getvalue()
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return len(data)


def _dir_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file()) if Path(p).exists() else 0


def _progress(path: Path) -> dict[str, dict]:
    return hb._read_progress(path)


def _append(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def fetch_price_window(lim: hb.Limiter, token: str, start: int, end: int, fidelity: int) -> list[tuple[int, float]]:
    """One ``prices-history`` series, split in <= 14-day windows (sorted unique points)."""
    pts: dict[int, float] = {}
    a = start
    step = hb.WINDOW_DAYS * 86400
    while a < end:
        b = min(a + step, end)
        status, data = lim.get(hb.CLOB_PRICES, {"market": token, "startTs": int(a), "endTs": int(b), "fidelity": fidelity})
        if status == 200 and isinstance(data, dict):
            for h in data.get("history") or []:
                try:
                    pts[int(h["t"])] = float(h["p"])
                except (KeyError, TypeError, ValueError):
                    continue
        a = b
    return sorted(pts.items())


# ---- q0102: head prices ----------------------------------------------------------------------------------------------


def head_eligible(frame: pd.DataFrame, clock_epoch: float) -> pd.DataFrame:
    """Every h2 market the G population could need: ``created + 4d + 1h <= T_h2_clock``, scheduled life >= 4d, not weather. Static
    facts only (``created_at``, ``end_epoch``, fee category)."""
    df = frame.copy()
    df["created"] = [hb._epoch(v) for v in df["created_at"]]
    end = pd.to_numeric(df["end_epoch"], errors="coerce")
    ok = df["created"].notna() & (df["created"] + HEAD_AFTER_D * D + HEAD_AFTER_H * H <= clock_epoch)
    ok &= (end - df["created"]) >= MIN_LIFE_D * D
    ok &= df["fee_category"].astype(str) != "weather"
    return df[ok].reset_index(drop=True)


def head_fetch(run_dir: Path, lim: hb.Limiter, *, clock_epoch: float | None = None, out_dir: Path | None = None, disk_cap_bytes: int = 50_000_000,
               max_items: int | None = None, should_stop=None) -> dict:
    """Resumable head-price refetch for ``run_dir`` (h2_main). Never reads trades or outcomes."""
    run_dir = Path(run_dir)
    clock = float(clock_epoch) if clock_epoch is not None else hb._epoch(T_H2_CLOCK)
    if clock > hb._epoch(T_H2_CLOCK) + 1:
        raise ValueError("the head refetch may not extend past T_h2_clock")
    out = Path(out_dir) if out_dir is not None else run_dir / "cb5" / "head_prices"
    frame = pd.read_csv(run_dir / "sample.csv.gz", dtype=str, keep_default_na=False, usecols=lambda c: c in FRAME_NEEDED)
    el = head_eligible(frame, clock)
    prog_p = out / "progress.jsonl"
    done = _progress(prog_p)
    used = _dir_bytes(out)
    n_done = 0
    res: dict[str, Any] = {"cb5_head": HEAD_VERSION, "eligible": int(len(el)), "stopped": None}
    for _, r in el.iterrows():
        mid = str(r["market_id"])
        if mid in done:
            continue
        if (should_stop and should_stop()) or (max_items is not None and n_done >= max_items):
            res["stopped"] = "budget"
            break
        L = float(r["created"])
        start, end = int(L - HEAD_BEFORE_H * H), int(L + HEAD_AFTER_D * D + HEAD_AFTER_H * H)
        pts = fetch_price_window(lim, str(r["token0"]), start, end, 10)
        p1 = fetch_price_window(lim, str(r["token0"]), start, int(L + DAY0_FID1_WINDOW_H * H), 1)
        gaps = [b[0] - a[0] for a, b in zip(p1, p1[1:], strict=False)]
        sub10 = bool(gaps and min(gaps) < 540)
        size = _gz_csv(out / f"{mid}.csv.gz", ["t", "p"], [[t, p] for t, p in pts])
        if p1 and sub10:
            size += _gz_csv(out / "fid1" / f"{mid}.csv.gz", ["t", "p"], [[t, p] for t, p in p1])
        used += size
        if used > disk_cap_bytes:
            raise DiskCapExceeded(f"head_prices {used} > {disk_cap_bytes}")
        _append(prog_p, {"market_id": mid, "n_points": len(pts), "n_fid1": len(p1), "fid1_sub10min": sub10, "start": start, "end": end})
        n_done += 1
    res.update(done=n_done, total_done=len(done) + n_done, complete=bool(res["stopped"] is None))
    mp = out / "manifest.json"
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps({"version": HEAD_VERSION, "clock_epoch": clock, "eligible": int(len(el)), "done": len(done) + n_done, "complete": res["complete"],
                              "fid1_request": "day-0 fidelity 1 stored only when the API returns sub-10-minute spacing (recorded either way)"}, sort_keys=True, indent=1))
    return res


# ---- q0103 / q0111: listing cohorts ----------------------------------------------------------------------------------


def census_trim(rows: list[list], created: float) -> tuple[list[list], dict]:
    """The census parse guard: keep only trades with ``created <= ts <= min(first trade + 1h, created + 24h)`` (rows sorted by
    ``ts``). Returns the kept rows and the bound; everything later is dropped before storage."""
    rows = [r for r in rows if r[0] >= created]
    if not rows:
        return [], {"bound": created + CENSUS_WINDOW_H * H, "first_trade": None}
    ft = min(r[0] for r in rows)
    bound = min(ft + CENSUS_AFTER_TRADE_H * H, created + CENSUS_WINDOW_H * H)
    return [r for r in rows if r[0] <= bound], {"bound": bound, "first_trade": ft}


def select_cohort(listings: pd.DataFrame, *, window: str, seed: str, max_markets: int, dev_start: str, census_end: str | None = None, rep_start: str | None = None,
                  rep_end: str | None = None, exclude_ids: set[str] | None = None) -> pd.DataFrame:
    """Listing-cohort markets (first sighting per market): non-sports, non-weather, binary (a second token), created inside the
    window. Census: ``dev_start <= created < census_end`` (= ``T5_dev_end - 1d``); replication: ``rep_start <= created < rep_end``.
    A seeded sample of at most ``max_markets`` (rank by sha256(seed|id)). The census and replication cohorts cannot share a market."""
    df = listings.drop_duplicates("market_id").copy()
    df["created"] = [hb._epoch(v) for v in df["created_at"]]
    lo = hb._epoch(dev_start if window == "census" else rep_start)
    hi = hb._epoch(census_end if window == "census" else rep_end)
    cat = df["fee_category"].astype(str).str.split(":").str[0]
    ok = df["created"].between(lo, hi, inclusive="left") & (cat != "sports") & (cat != "weather") & (df["clob_token_id_0"].astype(str) != "") & (df["clob_token_id_1"].astype(str) != "")
    df = df[ok]
    if exclude_ids:
        df = df[~df["market_id"].isin(exclude_ids)]
    df = df.assign(_rank=[hashlib.sha256(f"{seed}|{m}".encode()).hexdigest() for m in df["market_id"]]).sort_values("_rank")
    return df.head(max_markets).drop(columns="_rank").reset_index(drop=True)


def cohort_fetch(listings: pd.DataFrame, lim: hb.Limiter, out_dir: Path, *, window: str, now_epoch: float, key: bytes | None = None, disk_cap_bytes: int = 30_000_000,
                 max_items: int | None = None, should_stop=None, due_after_h: float = REP_FETCH_AFTER_H) -> dict:
    """Fetch prices and trades for the selected cohort rows (``condition_id`` + tokens from the listings table). Census: stored only
    up to ``min(first trade + 1h, L + 24h)``. Replication: each market fetched only once ``now >= L + 4d + 2h``, stored up to
    ``L + 4d + 1h``. Resumable by ``progress.jsonl``."""
    if window not in ("census", "rep"):
        raise ValueError(window)
    out = Path(out_dir)
    done = _progress(out / "progress.jsonl")
    used = _dir_bytes(out)
    key = key if key is not None else b"cb5-no-wallet-storage"
    res: dict[str, Any] = {"cb5_cohort": COHORT_VERSION, "window": window, "selected": int(len(listings)), "stopped": None}
    n = pending = 0
    for _, r in listings.iterrows():
        mid = str(r["market_id"])
        if mid in done:
            continue
        L = float(r["created"])
        if window == "rep" and now_epoch < L + due_after_h * H:
            pending += 1
            continue
        if (should_stop and should_stop()) or (max_items is not None and n >= max_items):
            res["stopped"] = "budget"
            break
        rows, st = hb.fetch_trades(lim, str(r["condition_id"]), key, MAX_TRADES)
        rows = [[x[0], x[1], x[2], x[3], x[4], "", x[6]] for x in rows]  # wallet hash blanked: never stored
        if window == "census":
            kept, info = census_trim(rows, L)
            bound = info["bound"]
        else:
            bound = L + HEAD_AFTER_D * D + HEAD_AFTER_H * H
            kept = [x for x in rows if L <= x[0] <= bound]
            info = {"first_trade": min((x[0] for x in kept), default=None)}
        start = int(L - HEAD_BEFORE_H * H)
        pts = fetch_price_window(lim, str(r["clob_token_id_0"]), start, int(bound), 10)
        pts = [(t, p) for t, p in pts if t <= bound]  # parse guard: nothing past the bound is written
        size = _gz_csv(out / "trades" / f"{mid}.csv.gz", TRADE_COLS, kept) + _gz_csv(out / "prices" / f"{mid}.csv.gz", ["t", "p"], [[t, p] for t, p in pts])
        used += size
        if used > disk_cap_bytes:
            raise DiskCapExceeded(f"{window} cohort {used} > {disk_cap_bytes}")
        _append(out / "progress.jsonl", {"market_id": mid, "created": L, "bound": bound, "first_trade": info["first_trade"], "n_trades": len(kept), "n_points": len(pts),
                                          "trades_truncated": bool(st["truncated"]), "trades_oldest_ts": st["oldest_ts"], "status": "done", "window": window})
        n += 1
    complete = pending == 0 and res["stopped"] is None
    res.update(done=n, pending_not_due=pending, total_done=len(done) + n, complete=complete)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps({"version": COHORT_VERSION, "window": window, "selected": int(len(listings)), "done": len(done) + n, "complete": complete},
                                                 sort_keys=True, indent=1))
    return res


def load_cohort_market(out_dir: Path, mid: str) -> tuple[Any, Any, pd.DataFrame]:
    """(ts, vals, trades) of one stored cohort market."""
    ts, vals = hb.load_prices(Path(out_dir) / "prices" / f"{mid}.csv.gz")
    tr = hb.load_trades(Path(out_dir) / "trades" / f"{mid}.csv.gz")
    return ts, vals, tr


# ---- guarded outcome reads (q0107 historical, T5_L_out, G hold-to-resolution) ----------------------------------------


def fetch_yes_payouts(lim: hb.Limiter, market_ids: list[str], batch: int = 40) -> dict[str, float]:
    """YES (token 0) final payout (1.0 / 0.0, NaN if not closed or not decisive) for ``market_ids`` from Gamma ``/markets``. Only the
    callers that are allowed to read outcomes (runner guards) call this; nothing else in CB5 touches ``outcomePrices``."""
    from . import cb1_history

    out: dict[str, float] = {}
    ids = [str(i) for i in market_ids]
    for a in range(0, len(ids), batch):
        chunk = ids[a:a + batch]
        status, data = lim.get(hb.GAMMA_MARKETS, [("id", i) for i in chunk] + [("limit", len(chunk))])  # type: ignore[arg-type]
        got = {}
        if status == 200 and isinstance(data, list):
            for m in data:
                v = cb1_history.parse_outcome0(m.get("outcomePrices")) if m.get("closed") else None
                got[str(m.get("id"))] = math.nan if v is None or v not in (0.0, 1.0) else float(v)
        for i in chunk:
            out[i] = got.get(i, math.nan)
    return out
