# ruff: noqa: E501
"""Synthetic fixtures for the CB16 tests (offline; no network): fill rows with a mark table, capture and monitor-file writers."""

from __future__ import annotations

import gzip
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from astrolabe.research_lab import cb13_label as lab
from astrolabe.research_lab import cb16_common as c16
from astrolabe.research_lab import cb16_q as q

S_A = c16.ep("2026-11-02T00:00:00Z")
FREEZE_UTC = "2026-11-01T00:00:00Z"


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def synth(beta_g: float = 1.5, beta_x: float = 0.0, n_mkt: int = 140, per: int = 14, seed: int = 3, spread: float = 0.02, p_edge: bool = False, wake_p: float = 0.0, tau0: float = S_A):
    """Fill rows (``cb16_q.FILL_COLUMNS``) plus a ``MarkTable16``. ``M = beta_g g + beta_x x + u_market + noise`` (cents, maker view); ``U1`` measures ``-beta_x`` (positive = longer silence
    is worse for the maker)."""
    rng = np.random.default_rng(seed)
    fills, marks = [], []
    i = 0
    for m in range(n_mkt):
        cid, ev = f"c{m}", f"E{m // 2}"
        u_m = rng.normal(0, 1.0)
        for k in range(per):
            tau = tau0 + 3600.0 * (m % 24) + 86400.0 * (k % 14) + 60.0 * k
            g = int(rng.random() < 0.4)
            x = float(rng.normal(0, 1.0))
            d = -1 if rng.random() < 0.5 else 1
            M = beta_g * g + beta_x * x + u_m + rng.normal(0, 3.0)
            P = round(0.5 + (0.007 if g else 0.0) * -d, 3)
            mid_h = P + d * M / 100.0
            row = dict(tx_id=i, condition_id=cid, market_id=str(m), event_id=ev, status="fill", label=lab.PATH if m % 3 else lab.SCHEDULED, underlying="", path_key=f"pk{m % 5}", tau=tau, tau_last=tau,
                       p_vwap=P, p_min=P, p_max=P, size=5000.0, cash=float(rng.uniform(2600, 9000)), n_fills=1, d=d, P=P, bid0=0.5 - spread / 2, ask0=0.5 + spread / 2, spread0=spread, mid0=0.5,
                       touch_recv=tau - 600, touch_age_s=float(rng.uniform(0, 3000)), touch_cap=1, liq=2000.0, end_epoch=tau + 5 * 86400.0, prev_mid=0.5 + rng.normal(0, 0.02), prev_recv=tau - 9000,
                       q_stale=math.nan, d_stale=0, fee_rate=0.04, clob_rewards=int(m % 2), fee_type="x", block=c16.block6(tau), day=c16.utc_day(tau), neg_risk_market_id="", tick_touch=0.001,
                       created_epoch=tau - 10 * 86400.0, token0="", hour=c16.hour_of_day(tau), g=g, grain_ok=1, u_ok=1, excl_P=math.nan, excl_g=-1, politics=0, s=3600.0, tau_prev=tau - 3600.0,
                       n_prior=6, x_raw=x, x=x, x3=x, n_prior3=6, wake=int(rng.random() < wake_p), silence_status="ok", spans_night=int(k % 5 == 0), s12_dropped=0, wake_lag_s=math.nan,
                       sw_share=math.nan, sw_ratio=math.nan, sw_levels=math.nan, sw_age_s=math.nan)
            fills.append(row)
            for h, off in (("2-4h", 7200.0), ("6-8h", 21600.0)):
                mh = mid_h if h == "2-4h" else mid_h + rng.normal(0, 0.003)
                marks.append(dict(tx_id=i, h=h, status="ok", recv=tau + off + 300, bid=round(mh - 0.01, 4), ask=round(mh + 0.01, 4), tick=0.001))
            i += 1
    return fills, q.MarkTable16(marks, {})


CAP_COLS = ["capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price", "chg_1h",
            "chg_1d", "chg_1w", "liquidity", "volume24hr", "end_date", "updated_at", "dup_count", "clob_token_id_0", "neg_risk", "neg_risk_market_id", "neg_risk_other",
            "event_neg_risk_augmented", "page_index"]
EXT_COLS = ["capture_id", "received_utc", "page_index", "market_id", "condition_id", "clob_token_id_0", "clob_token_id_1", "event_id", "fee_type", "fee_category", "fees_enabled", "accepting_orders",
            "taker_base_fee", "order_price_min_tick_size", "order_min_size", "competitive", "rewards_min_size", "rewards_max_spread", "volume_num", "open_interest", "created_at", "start_date",
            "uma_resolution_statuses", "clob_rewards", "fee_schedule", "event_ids", "series_slugs", "neg_risk_market_id"]


def write_capture(snap: Path, start: str, quotes: dict, *, state: str = "complete", fee_type: str = "crypto_fees_v2", end: str = "2027-01-01T00:00:00Z", tick: str = "0.001", created: str = "2026-09-01T00:00:00Z"):
    """quotes: {cid: (market_id, event_id, bid, ask)}; rows are received 1 s after the start."""
    t0 = ep(start)
    d = Path(snap) / f"{datetime.fromtimestamp(t0, UTC):%Y%m%dT%H%M%SZ}_ab{int(t0) % 100000:05d}"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"capture_id": d.name, "started_utc": start, "state": state}))
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        fh.write(",".join(CAP_COLS) + "\n")
        for cid, (mid, eid, b, a) in quotes.items():
            row = {c: "" for c in CAP_COLS}
            row.update(capture_id=d.name, capture_start_utc=start, received_utc=iso(t0 + 1), market_id=mid, condition_id=cid, event_id=eid, closed="False", active="True", binary="1", best_bid=b, best_ask=a,
                       liquidity="1000", end_date=end, chg_1h="0.5", last_trade_price="0.5", clob_token_id_0=f"tok-{cid}")
            fh.write(",".join(str(row[c]) for c in CAP_COLS) + "\n")
    with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
        fh.write(",".join(EXT_COLS) + "\n")
        for cid, (mid, eid, _b, _a) in quotes.items():
            row = {c: "" for c in EXT_COLS}
            row.update(capture_id=d.name, market_id=mid, condition_id=cid, event_id=eid, fee_type=fee_type, fee_category="crypto", fee_schedule='{"exponent":1,"rate":0.04}', series_slugs='["btc-weekly"]',
                       clob_rewards="[]", open_interest="9", order_price_min_tick_size=tick, created_at=created)
            fh.write(",".join('"' + str(row[c]).replace('"', '""') + '"' for c in EXT_COLS) + "\n")
    return d


def trade(ts: str | float, cid: str, price: float, size: float = 3000.0, oi: int = 0, tx: str = "", title: str = "Will Bitcoin reach $100k this week?") -> dict:
    t = ep(ts) if isinstance(ts, str) else float(ts)
    return {"key": "k", "recv_ts": t + 400, "ts": t, "condition_id": cid, "token_id": "1", "side": "BUY", "outcome_index": oi, "size": size, "price": price, "cash": size * price, "wallet_hash": "w",
            "tx16": tx, "title": title, "slug": "s", "ctx_status": "ok", "ctx_chg_1h": 0.9}


def write_trades(tr: Path, day: str, lines: list[dict]) -> Path:
    Path(tr).mkdir(parents=True, exist_ok=True)
    p = Path(tr) / f"trades-{day}.jsonl"
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return p


def make_cb13_screen_world(tmp_path: Path) -> dict:
    """CB13-T SCREEN raw files (two consecutive captures and the prints between them) for the smoke reproduction."""
    root = Path(tmp_path) / "cb13"
    snap, tr = root / "snapshots", root / "live_trades"
    snap.mkdir(parents=True)
    for st in ("2026-10-12T00:00:00Z", "2026-10-12T02:00:00Z", "2026-10-12T04:00:00Z"):
        write_capture(snap, st, {"0xA": ("1", "E1", "0.48", "0.50")})
    lines = [trade("2026-10-12T00:30:00Z", "0xA", 0.50, tx="tx1"), trade("2026-10-12T00:31:00Z", "0xA", 0.49, oi=1, tx="tx2"), trade("2026-10-12T00:32:00Z", "0xA", 0.48, tx="tx3"),
             trade("2026-10-12T00:33:00Z", "0xA", 0.49, tx="tx4"), trade("2026-10-12T00:34:00Z", "0xA", 0.60, tx="tx5"), trade("2026-10-12T00:35:00Z", "0xA", 0.50, tx="tx6")]
    write_trades(tr, "20261012", lines)
    return {"snap": snap, "trades": tr}


def write_pin(tmp_path: Path) -> Path:
    p = Path(tmp_path) / "j4r_window.json"
    p.write_text(json.dumps({"t_j4r_start": "2026-10-16T00:00:00Z", "t_j4r_end": "2026-10-21T00:00:00Z", "declared_end": "2026-10-21T00:00:00Z", "final": False}))
    return p


def make_window_world(tmp_path: Path) -> dict:
    """A one-day SCREEN_A-like world (2026-11-02): two PATH-settled markets, captures every 30 min (tick 0.001), trades timed 01:00-07:50 as transactions with sub-cent and whole-cent lifted quotes."""
    snap, tr = Path(tmp_path) / "snapshots", Path(tmp_path) / "live_trades"
    snap.mkdir(parents=True, exist_ok=True)
    cids = {"0xA": ("1", "EA"), "0xB": ("2", "EB")}
    t = ep("2026-11-01T20:00:00Z")
    end = ep("2026-11-03T12:00:00Z")
    while t <= end:
        hh = datetime.fromtimestamp(t, UTC).hour
        bid, ask = ("0.478", "0.503") if hh < 2 else ("0.48", "0.50")  # sub-cent quotes before 02:00Z, whole-cent after
        write_capture(snap, iso(t), {cid: (mid, eid, bid, ask) for cid, (mid, eid) in cids.items()})
        t += 1800.0
    lines = []
    n = 0
    for cid in cids:
        for k in range(8):  # 01:00..01:50 (sub-cent quote of the 00:00 capture): lift the 0.503 ask / hit the 0.478 bid
            ts = ep("2026-11-02T01:00:00Z") + 600.0 * k + (30.0 if cid == "0xB" else 0.0)
            n += 1
            lines.append(trade(ts, cid, 0.503 if k % 2 == 0 else 0.478, tx=f"{cid}-{k}"))
        for k in range(8):  # 03:00..: whole-cent quote of the 02:00 capture
            ts = ep("2026-11-02T03:00:00Z") + 900.0 * k + (30.0 if cid == "0xB" else 0.0)
            n += 1
            lines.append(trade(ts, cid, 0.50 if k % 2 == 0 else 0.48, tx=f"{cid}-w{k}"))
    write_trades(tr, "20261102", lines)
    return {"snap": snap, "trades": tr, "n_trades": n}
