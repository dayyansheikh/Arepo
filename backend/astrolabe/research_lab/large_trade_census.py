"""Historical large-trade census (research lab, EXPLORATORY_HISTORICAL only).

Probe findings (2026-10-12, recorded in ``PROBE``): the global v1 ``/trades`` feed ignores
``start``/``end`` when no ``market`` is given and stops at the 10,000 offset cap (about 29 h of
prints >= $1k), so it cannot reach months back. ``/v2/trades`` returns ``{data, pagination}`` with
a signed keyset ``next_cursor``: 60 consecutive pages were strictly time-monotonic, with no
duplicates, and a market cross-check against v1 ``market=...&start&end`` matched exactly (331/331).
The census therefore walks the v2 cursor from the head back to ``stop_ts`` with
``takerOnly=true&filterType=CASH&filterAmount=<min_cash>``.

Stored per print: ts, condition_id, token_id, side, outcome_index, price, size, cash,
wallet_hash (HMAC, ``wallet_sidecar``), tx16 (first 16 hex of the public transaction hash, for
de-duplication). Market text (slug, event slug, title, outcome label) is kept once per
condition id in ``markets.jsonl``. Names, pseudonyms, bios, images and raw addresses are never
written. Chunks are gzip CSV; ``progress.json`` holds the cursor so a run resumes.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import time
from collections.abc import Callable
from pathlib import Path

from . import history_backfill as hb
from .wallet_sidecar import hash_wallet

V2_TRADES = "https://data-api.polymarket.com/v2/trades"
EVIDENCE_ROLE = "exploratory_historical"
VERSION = "large-trade-census-v1"
COLUMNS = ["ts", "condition_id", "token_id", "side", "outcome_index", "price", "size", "cash",
           "wallet_hash", "tx16"]
PROBE = {
    "date": "2026-10-12",
    "v1_global": "start/end ignored without market; newest-first; offset cap 10000; limit 10000 "
    "accepted -> about 29 h of >= $1k prints reachable",
    "v1_market_list": "market=<comma-separated condition ids> with start/end honoured",
    "v2": "dict {data, pagination{next_cursor, has_more}}; signed keyset cursor; start/end "
    "ignored; 60 pages monotonic, no duplicates; v1 per-market cross-check 331/331",
    "rate": "about 10k prints >= $1k per day (early Oct 2026)",
}


def row_of(t: dict, key: bytes) -> tuple[list, dict] | None:
    try:
        cid = str(t["condition_id"])
        cash = float(t["size"]) * float(t["price"])
        h = hash_wallet(key, t.get("proxy_wallet")) or ""
        r = [int(t["timestamp"]), cid, str(t.get("token_id") or ""), str(t["side"]),
             int(t["outcome_index"]), float(t["price"]), float(t["size"]), round(cash, 6), h,
             str(t.get("transaction_hash") or "")[2:18]]
    except (KeyError, TypeError, ValueError):
        return None
    meta = {"condition_id": cid, "slug": t.get("slug"), "event_slug": t.get("event_slug"),
            "title": t.get("title"), "outcome_index": t.get("outcome_index"),
            "outcome": t.get("outcome")}
    return r, meta


def _write_chunk(path: Path, rows: list[list]) -> int:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    w.writerows(rows)
    data = gzip.compress(buf.getvalue().encode(), compresslevel=6, mtime=0)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)
    return len(data)


def pull_census(out_dir: Path, lim: hb.Limiter, key: bytes, *, min_cash: float, stop_ts: int,
                pages_per_chunk: int = 100, max_pages: int = 100_000,
                disk_cap: int = 2 * 1024**3,
                should_stop: Callable[[], bool] | None = None) -> dict:
    """Walk the v2 cursor back to ``stop_ts``. Resumable from ``progress.json``."""
    out_dir = Path(out_dir)
    (out_dir / "chunks").mkdir(parents=True, exist_ok=True)
    prog_path = out_dir / "progress.json"
    prog = json.loads(prog_path.read_text()) if prog_path.exists() else {
        "cursor": None, "pages": 0, "rows": 0, "chunks": 0, "oldest_ts": None, "newest_ts": None,
        "bytes": 0, "done": False, "min_cash": min_cash, "stop_ts": stop_ts,
        "started_utc": hb.utc_iso()}
    if prog.get("done"):
        return prog
    seen_meta: set[str] = set()
    meta_path = out_dir / "markets.jsonl"
    if meta_path.exists():
        for line in meta_path.read_text().splitlines():
            if line:
                d = json.loads(line)
                seen_meta.add(f"{d['condition_id']}|{d['outcome_index']}")
    params = {"takerOnly": "true", "filterType": "CASH", "filterAmount": min_cash, "limit": 1000}
    rows: list[list] = []
    cur = prog["cursor"]
    t0 = time.time()
    pages_here = 0
    while prog["pages"] < max_pages:
        if should_stop is not None and should_stop():
            break
        st, d = lim.get(V2_TRADES, {**params, **({"cursor": cur} if cur else {})})
        if st != 200 or not isinstance(d, dict):
            prog["last_error"] = f"status {st}"
            break
        data = d.get("data") or []
        new_meta = []
        for t in data:
            res = row_of(t, key)
            if res is None:
                continue
            r, meta = res
            rows.append(r)
            mk = f"{meta['condition_id']}|{meta['outcome_index']}"
            if mk not in seen_meta:
                seen_meta.add(mk)
                new_meta.append(meta)
        if new_meta:
            with meta_path.open("a") as fh:
                fh.writelines(json.dumps(m) + "\n" for m in new_meta)
        prog["pages"] += 1
        pages_here += 1
        if data:
            mn = min(int(t["timestamp"]) for t in data)
            mx = max(int(t["timestamp"]) for t in data)
            prog["oldest_ts"] = mn if prog["oldest_ts"] is None else min(prog["oldest_ts"], mn)
            prog["newest_ts"] = mx if prog["newest_ts"] is None else max(prog["newest_ts"], mx)
        cur = (d.get("pagination") or {}).get("next_cursor")
        reached = prog["oldest_ts"] is not None and prog["oldest_ts"] < stop_ts
        if len(rows) >= pages_per_chunk * 1000 or not cur or not data or reached:
            if rows:
                if prog["bytes"] > disk_cap:
                    prog["last_error"] = "disk cap"
                    break
                prog["bytes"] += _write_chunk(out_dir / "chunks" / f"c{prog['chunks']:05d}.csv.gz",
                                              rows)
                prog["chunks"] += 1
                prog["rows"] += len(rows)
                rows = []
            prog["cursor"] = cur
            prog["updated_utc"] = hb.utc_iso()
            prog_path.write_text(json.dumps(prog, indent=1))
        if not cur or not data or reached:
            prog["done"] = True
            prog["end_reason"] = "stop_ts reached" if reached else "cursor exhausted"
            break
    if rows:  # interrupted mid-chunk: keep what we have, cursor points past it
        prog["bytes"] += _write_chunk(out_dir / "chunks" / f"c{prog['chunks']:05d}.csv.gz", rows)
        prog["chunks"] += 1
        prog["rows"] += len(rows)
    prog["cursor"] = cur
    prog["requests_this_session"] = lim.requests
    prog["http_429_this_session"] = lim.throttled
    prog["yielded_to_live_s"] = prog.get("yielded_to_live_s", 0) + lim.yielded_s
    prog["seconds_this_session"] = round(time.time() - t0, 1)
    prog["pages_this_session"] = pages_here
    prog["updated_utc"] = hb.utc_iso()
    prog_path.write_text(json.dumps(prog, indent=1))
    return prog


def load_census(out_dir: Path, columns: list[str] | None = None):
    import pandas as pd

    files = sorted((Path(out_dir) / "chunks").glob("*.csv.gz"))
    parts = [pd.read_csv(f, usecols=columns, dtype={"condition_id": str, "token_id": str,
                                                    "wallet_hash": str, "tx16": str})
             for f in files]
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=columns or COLUMNS)
    return df.drop_duplicates().sort_values(["ts"], kind="stable").reset_index(drop=True)


def load_market_meta(out_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    p = Path(out_dir) / "markets.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            if line:
                d = json.loads(line)
                e = out.setdefault(d["condition_id"], {k: d.get(k) for k in
                                                       ("slug", "event_slug", "title")})
                e.setdefault("outcomes", {})[str(d.get("outcome_index"))] = d.get("outcome")
    return out


# ---------------------------------------------------------------------------------------------
# v1 route: Gamma universe -> per-market-list trade census with time windows (reaches months back)
# ---------------------------------------------------------------------------------------------

UNIVERSE_COLS = ["condition_id", "market_id", "question", "slug", "event_slug", "fee_type",
                 "neg_risk", "token0", "token1", "created_ts", "end_ts", "closed_ts", "closed",
                 "volume"]


def slim_market(m: dict) -> dict | None:
    try:
        toks = json.loads(m.get("clobTokenIds") or "[]")
    except ValueError:
        toks = []
    if not m.get("conditionId") or len(toks) != 2:
        return None
    ev = m.get("events") if isinstance(m.get("events"), list) else []
    return {"condition_id": m["conditionId"], "market_id": str(m.get("id")),
            "question": m.get("question") or "", "slug": m.get("slug") or "",
            "event_slug": (ev[0].get("slug") if ev and isinstance(ev[0], dict) else "") or "",
            "fee_type": m.get("feeType") or "", "neg_risk": int(bool(m.get("negRisk"))),
            "token0": str(toks[0]), "token1": str(toks[1]),
            "created_ts": hb._epoch(m.get("createdAt")), "end_ts": hb._epoch(m.get("endDate")),
            "closed_ts": hb._epoch(m.get("closedTime")), "closed": int(bool(m.get("closed"))),
            "volume": float(m.get("volumeNum") or 0.0)}


def _gamma_window(lim: hb.Limiter, base: dict, a: int, b: int, field: str, depth: int = 0
                  ) -> tuple[list[dict], int]:
    """All markets with ``field`` in [a, b); splits the window in halves while the Gamma offset cap
    (~2,100) is hit. Returns (markets, capped_leaf_windows)."""
    p = {**base, f"{field}_min": hb.utc_iso(a), f"{field}_max": hb.utc_iso(b - 1),
         "order": "id", "ascending": "true"}
    rows, capped = hb._paged(lim, p, max_rows=hb.GAMMA_OFFSET_CAP)
    if not capped:
        return rows, 0
    if b - a <= 300 or depth > 12:
        return rows, 1
    m = (a + b) // 2
    r1, c1 = _gamma_window(lim, base, a, m, field, depth + 1)
    r2, c2 = _gamma_window(lim, base, m, b, field, depth + 1)
    return r1 + r2, c1 + c2


def enumerate_universe(lim: hb.Limiter, out_dir: Path, start_ts: int, end_ts: int,
                       min_volume: float, active_start_ts: int) -> dict:
    """Closed markets by end_date day (resumable per day) plus still-open markets by start_date
    month, all with ``volume_num_min``. Writes ``universe/days.jsonl`` (one record per window)."""
    out_dir = Path(out_dir) / "universe"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "days.jsonl"
    done = set()
    if path.exists():
        for line in path.read_text().splitlines():
            if line:
                done.add(json.loads(line)["window"])
    rep = {"windows": 0, "capped_leaves": 0}
    jobs = [("closed", d, d + 86400, "end_date") for d in range(start_ts, end_ts, 86400)]
    a = active_start_ts
    while a < end_ts:
        jobs.append(("active", a, min(a + 30 * 86400, end_ts), "start_date"))
        a += 30 * 86400
    for kind, a, b, field in jobs:
        wid = f"{kind}:{a}"
        if wid in done:
            continue
        base = {"closed": "true" if kind == "closed" else "false", "volume_num_min": min_volume}
        ms, capped = _gamma_window(lim, base, a, b, field)
        rows = [r for r in (slim_market(m) for m in ms) if r is not None]
        with path.open("a") as fh:
            fh.write(json.dumps({"window": wid, "n": len(rows), "capped_leaves": capped,
                                 "rows": rows}, default=float) + "\n")
        rep["windows"] += 1
        rep["capped_leaves"] += capped
    return rep


def load_universe(out_dir: Path):
    import pandas as pd

    rows, capped, n_win = [], 0, 0
    for line in (Path(out_dir) / "universe" / "days.jsonl").read_text().splitlines():
        if line:
            d = json.loads(line)
            rows.extend(d["rows"])
            capped += d["capped_leaves"]
            n_win += 1
    df = pd.DataFrame(rows, columns=UNIVERSE_COLS).drop_duplicates("condition_id")
    df.attrs.update({"capped_leaves": capped, "windows": n_win})
    return df


def census_markets(lim: hb.Limiter, key: bytes, out_dir: Path, markets, win_lo: int, win_hi: int,
                   min_cash: float, batch: int = 40, min_window_s: int = 600) -> dict:
    """Large prints of the given markets: v1 ``/trades?market=<list>&start&end`` (takerOnly, cash
    filter), windows split in halves at the 10,000-offset cap. ``markets``: DataFrame with
    condition_id, created_ts, closed_ts/end_ts. Resumable per batch (``v1_progress.jsonl``)."""
    out_dir = Path(out_dir)
    (out_dir / "chunks").mkdir(parents=True, exist_ok=True)
    prog_path = out_dir / "v1_progress.jsonl"
    done = set()
    if prog_path.exists():
        for line in prog_path.read_text().splitlines():
            if line:
                done.add(json.loads(line)["batch"])
    m = markets.copy()
    end = m["closed_ts"].where(m["closed_ts"].notna(), m["end_ts"]).fillna(win_hi)
    m["lo"] = m["created_ts"].fillna(win_lo).clip(lower=win_lo).astype(int)
    m["hi"] = (end + 86400).clip(upper=win_hi).astype(int)
    m = m[m["hi"] > m["lo"]].sort_values(["hi", "condition_id"]).reset_index(drop=True)
    meta_path = out_dir / "markets.jsonl"
    rep = {"batches": 0, "requests": 0, "rows": 0, "incomplete_windows": 0}
    for bi in range(0, len(m), batch):
        if bi in done:
            continue
        g = m.iloc[bi:bi + batch]
        cids = list(g["condition_id"])
        rows: dict[str, list] = {}
        metas: dict[str, dict] = {}
        stack = [(int(g["lo"].min()), int(g["hi"].max()))]
        incomplete = 0
        while stack:
            a, b = stack.pop()
            off, capped = 0, False
            while True:
                st, data = lim.get(hb.DATA_TRADES, {
                    "market": ",".join(cids), "start": a, "end": b, "takerOnly": "true",
                    "filterType": "CASH", "filterAmount": min_cash, "limit": 1000,
                    "offset": off})
                rep["requests"] += 1
                if st != 200 or not isinstance(data, list):
                    capped = st == 400
                    break
                for t in data:
                    res = row_of_v1(t, key)
                    if res is not None:
                        rows[f"{res[0][0]}|{res[0][9]}|{res[0][8]}|{res[0][6]}"] = res[0]
                        metas.setdefault(f"{res[1]['condition_id']}|{res[1]['outcome_index']}",
                                         res[1])
                if len(data) < 1000:
                    break
                off += 1000
                if off > hb.TRADE_OFFSET_CAP:
                    capped = True
                    break
            if capped:
                if b - a <= min_window_s:
                    incomplete += 1
                    continue
                mid = (a + b) // 2
                stack.extend([(a, mid), (mid + 1, b)])
        out = sorted(rows.values(), key=lambda r: (r[0], r[9]))
        if out:
            _write_chunk(out_dir / "chunks" / f"b{bi:07d}.csv.gz", out)
        if metas:
            with meta_path.open("a") as fh:
                fh.writelines(json.dumps(x) + "\n" for x in metas.values())
        with prog_path.open("a") as fh:
            fh.write(json.dumps({"batch": bi, "n_markets": len(cids), "rows": len(out),
                                 "incomplete_windows": incomplete}) + "\n")
        rep["batches"] += 1
        rep["rows"] += len(out)
        rep["incomplete_windows"] += incomplete
    return rep


def row_of_v1(t: dict, key: bytes) -> tuple[list, dict] | None:
    """v1 field names mapped onto the v2 row layout."""
    return row_of({"condition_id": t.get("conditionId"), "token_id": t.get("asset"),
                   "side": t.get("side"), "outcome_index": t.get("outcomeIndex"),
                   "price": t.get("price"), "size": t.get("size"), "timestamp": t.get("timestamp"),
                   "proxy_wallet": t.get("proxyWallet"),
                   "transaction_hash": t.get("transactionHash"), "slug": t.get("slug"),
                   "event_slug": t.get("eventSlug"), "title": t.get("title"),
                   "outcome": t.get("outcome")}, key)


# ---------------------------------------------------------------------------------------------
# Large-trade-anchored rows for the frozen unusual-flow variants (history panel layout)
# ---------------------------------------------------------------------------------------------

ANCHOR_LAG_S = 600  # origin = gate print + 10 min (the live N1 cadence)


def anchor_trades(lim: hb.Limiter, key: bytes, cid: str, t: int, max_pages: int = 3):
    """All taker trades of ``cid`` in [t - 24h, t), newest first, up to ``max_pages`` pages.
    Returns (DataFrame in history_backfill trade layout, covered_from)."""
    import pandas as pd

    rows, off, full = {}, 0, False
    for _ in range(max_pages):
        st, data = lim.get(hb.DATA_TRADES, {"market": cid, "start": t - 86400, "end": t - 1,
                                            "takerOnly": "true", "limit": 1000, "offset": off})
        if st != 200 or not isinstance(data, list):
            break
        for x in data:
            try:
                k = hb.trade_key(x)
                rows[k] = [int(x["timestamp"]), str(x["side"]), float(x["size"]),
                           float(x["price"]), int(x["outcomeIndex"]),
                           hb.wallet_hash(key, str(x.get("proxyWallet", ""))), k]
            except (KeyError, TypeError, ValueError):
                continue
        if len(data) < 1000:
            break
        off += 1000
    else:
        full = True
    df = pd.DataFrame(sorted(rows.values()), columns=hb.TRADE_COLUMNS)
    covered = float(df["ts"].min()) if full and len(df) else float(t - 86400)
    return df, covered


def anchored_rows(r: dict, t: int, tr, covered_from: float, pts, vals, first_seen,
                  horizons=(2, 6, 24)) -> list[dict]:
    """History-panel rows (one per horizon) for one anchored origin ``t``; [] when the origin
    price is missing or outside ``history_backfill.MID_RANGE``."""
    import numpy as np

    tt = np.array([float(t)])
    mid, age = hb._asof(pts, vals, tt, hb.MAX_QUOTE_AGE_S)
    if np.isnan(mid[0]) or not (hb.MID_RANGE[0] <= mid[0] <= hb.MID_RANGE[1]):
        return []
    prev, _ = hb._asof(pts, vals, tt - hb.GRID_S, hb.MAX_QUOTE_AGE_S)
    tf = hb._trade_flow(tr if len(tr) else None, tt, mid, covered_from, first_seen)
    base = {"market_id": r["condition_id"], "event_id": r.get("event_slug") or "",
            "t_i": float(t), "mid_i": float(mid[0]), "quote_age_s": float(age[0]),
            "fee_category": r.get("fee_category", ""), "traded_before_t": 1.0,
            "ml_own_dmid_prev": float(mid[0] - prev[0]),
            "provenance": "EXPLORATORY_HISTORICAL", "evidence_role": EVIDENCE_ROLE,
            **{k: float(v[0]) for k, v in tf.items()}}
    out = []
    for h in horizons:
        tj = tt + h * 3600
        mj, _ = hb._asof(pts, vals, tj, hb.MAX_QUOTE_AGE_S)
        ok = len(pts) and tj[0] <= pts[-1] + hb.MAX_QUOTE_AGE_S
        out.append({**base, "horizon_target_h": float(h),
                    "y_dmid": float(mj[0] - mid[0]) if ok else float("nan")})
    return out
