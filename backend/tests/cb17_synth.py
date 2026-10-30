# ruff: noqa: E501
"""Synthetic fixtures for the CB17 tests (offline; no network): worn-window captures, sweeps, monitor days and the CB13-T SCREEN fill table, each also carrying fields CB17 must never read."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

from astrolabe.research_lab import cb13_label as lab
from astrolabe.research_lab.book_sweep import ROW_COLUMNS

CAP_COLS = ["capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price", "chg_1h",
            "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date", "updated_at", "clob_token_id_0", "neg_risk", "neg_risk_market_id", "page_index"]
EXT_COLS = ["capture_id", "received_utc", "page_index", "market_id", "condition_id", "event_id", "fee_type", "fee_category", "accepting_orders", "order_price_min_tick_size", "volume_num",
            "open_interest", "created_at", "uma_resolution_statuses", "clob_rewards", "fee_schedule", "series_slugs", "neg_risk_market_id", "event_open_interest", "event_volume"]
FILL_COLS = ["tx_id", "condition_id", "market_id", "event_id", "status", "label", "path_key", "tau", "tau_last", "d", "P", "size", "cash", "spread0", "mid0", "prev_mid", "touch_age_s", "block", "day",
             "p_vwap", "mark_2h"]  # p_vwap and mark_2h are columns the census must not copy


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(t: float, suffix: str = "ab12cd34") -> str:
    return f"{datetime.fromtimestamp(t, UTC):%Y%m%dT%H%M%SZ}_{suffix}"


def write_csv_gz(path: Path, cols: list[str], rows: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        fh.write(",".join(cols) + "\n")
        for r in rows:
            fh.write(",".join('"' + str(r.get(c, "")).replace('"', '""') + '"' for c in cols) + "\n")


def write_capture(snap: Path, start: str | float, quotes: list[dict], *, name: str | None = None, last_page_offset: float = 30.0) -> Path:
    """quotes: dicts with mid (market id), cid, eid, bid, ask; optional closed, end, liq, oi, vol, nrm, created, fee_type, fee_category, series, rewards, recv (a per-row received_utc override).
    The rows are stamped across pages: the first row at start + 1 s, the last at start + ``last_page_offset`` (a capture's time is its LAST page's received_utc)."""
    t0 = ep(start) if isinstance(start, str) else float(start)
    d = Path(snap) / (name or stamp(t0))
    n = len(quotes)
    rows, ext = [], []
    for i, q in enumerate(quotes):
        recv = q.get("recv", t0 + 1.0 + (last_page_offset - 1.0) * (i / max(n - 1, 1)))
        rows.append({"capture_id": d.name, "capture_start_utc": iso(t0), "received_utc": iso(recv), "market_id": q["mid"], "condition_id": q["cid"], "event_id": q["eid"], "closed": q.get("closed", "False"),
                     "active": "True", "binary": "1", "best_bid": q["bid"], "best_ask": q["ask"], "last_trade_price": "0.5", "chg_1h": "0.7", "chg_1d": "0.1", "chg_1w": "0.2", "liquidity": q.get("liq", "20000"),
                     "volume24hr": "5", "end_date": q.get("end", "2027-01-01T00:00:00Z"), "clob_token_id_0": f"tok-{q['cid']}", "neg_risk": q.get("nr", ""), "neg_risk_market_id": q.get("nrm", ""), "page_index": 0})
        ext.append({"capture_id": d.name, "received_utc": iso(recv), "page_index": 0, "market_id": q["mid"], "condition_id": q["cid"], "event_id": q["eid"], "fee_type": q.get("fee_type", "crypto_fees_v2"),
                    "fee_category": q.get("fee_category", "crypto"), "accepting_orders": "True", "order_price_min_tick_size": "0.001", "volume_num": "9", "open_interest": "9",
                    "created_at": q.get("created", "2026-09-01T00:00:00Z"), "uma_resolution_statuses": "RESOLVED_SECRET", "clob_rewards": q.get("rewards", "[]"),
                    "fee_schedule": '{"exponent":1,"rate":0.04}', "series_slugs": q.get("series", '["btc-weekly"]'), "neg_risk_market_id": q.get("nrm", ""), "event_open_interest": q.get("oi", ""),
                    "event_volume": q.get("vol", "")})
    write_csv_gz(d / "rows.csv.gz", CAP_COLS, rows)
    write_csv_gz(d / "rows_ext.csv.gz", EXT_COLS, ext)
    (d / "manifest.json").write_text(json.dumps({"capture_id": d.name, "state": "complete"}))
    return d


def write_sweep(root: Path, start: str | float, books: list[dict], *, name: str | None = None) -> Path:
    """books: dicts with tok, mid (market id), bid, ask, ts (book_timestamp ms), hash, d1b/d1a/d5b/d5a (depth within 1c / 5c), nb, na; receipt = start + 5 s unless ``recv``."""
    t0 = ep(start) if isinstance(start, str) else float(start)
    d = Path(root) / (name or stamp(t0))
    rows = []
    for b in books:
        recv = b.get("recv", t0 + 5.0)
        rows.append({"sweep_id": d.name, "token_id": b["tok"], "market_id": b["mid"], "batch_index": 0, "batch_receipt_utc": iso(recv), "book_timestamp": b.get("ts", int((recv - 30.0) * 1000)),
                     "book_hash": b.get("hash", "h"), "best_bid": b["bid"], "best_ask": b["ask"], "bid_size_1": b.get("bs1", 100), "ask_size_1": b.get("as1", 100), "depth_bid_1c": b.get("d1b", 500),
                     "depth_ask_1c": b.get("d1a", 500), "depth_bid_5c": b.get("d5b", 2000), "depth_ask_5c": b.get("d5a", 2000), "n_bid_levels": b.get("nb", 5), "n_ask_levels": b.get("na", 5),
                     "tick_size": "0.001", "min_order_size": 5, "state": b.get("state", "two_sided")})
    write_csv_gz(d / "rows.csv.gz", ROW_COLUMNS, rows)
    return d


def print_(ts: float, cid: str, price: float, *, oi: int = 0, side: str = "BUY", size: float = 300.0, tx: str = "", title: str = "Will Bitcoin reach $100k this week?", mkt: str = "1", ev: str = "E1",
           recv_lag: float = 400.0, fee: str = "crypto_fees_v2") -> dict:
    return {"key": "k-secret", "recv_ts": ts + recv_lag, "ts": ts, "condition_id": cid, "token_id": "t", "side": side, "outcome_index": oi, "size": size, "price": price, "cash": size * price,
            "wallet_hash": "WALLET-SECRET", "tx16": tx, "title": title, "slug": "s", "ctx_event_id": ev, "ctx_market_id": mkt, "ctx_category": "", "ctx_fee_type": fee,
            "ctx_status": "ok", "ctx_chg_1h": 0.9}


def write_day(tr: Path, day: str, lines: list[dict]) -> Path:
    Path(tr).mkdir(parents=True, exist_ok=True)
    p = Path(tr) / f"trades-{day}.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return p


def fill_row(i: int, cid: str, tau: float, d: int, *, mkt: str = "1", ev: str = "E1", label: str = lab.PATH, price: float = 0.5, touch_age: float = 600.0, spread: float = 0.02, cash: float = 150.0,
             status: str = "fill") -> dict:
    return {"tx_id": i, "condition_id": cid, "market_id": mkt, "event_id": ev, "status": status, "label": label, "path_key": "pk1", "tau": tau, "tau_last": tau, "d": d, "P": price, "size": 300, "cash": cash,
            "spread0": spread, "mid0": 0.49, "prev_mid": 0.48, "touch_age_s": touch_age, "block": int(tau // 21600), "day": iso(tau)[:10], "p_vwap": price, "mark_2h": "SECRET-MARK"}


def write_screen(root: Path, fills: list[dict]) -> Path:
    d = Path(root) / "creative_batch13" / "t_screen"
    write_csv_gz(d / "fills.csv.gz", FILL_COLS, fills)
    write_csv_gz(d / "labels.csv.gz", ["condition_id", "label"], [{"condition_id": f["condition_id"], "label": f["label"]} for f in fills])
    return d
