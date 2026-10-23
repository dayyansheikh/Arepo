# ruff: noqa: E501
"""Synthetic capture trees for the LT11 tests (no real data, no network): host-style ``snapshots/<id>/{rows.csv.gz, rows_ext.csv.gz, manifest.json}``."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import extract
from astrolabe.research_lab import live_tests11 as lt
from astrolabe.research_lab import live_tests11_base as b

G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)
EXT_ORDER = ["market_id", "received_utc", "fee_type", "fee_category", "fees_enabled", "order_price_min_tick_size", "rewards_min_size", "rewards_max_spread", "volume_num",
             "created_at", "clob_rewards", "event_neg_risk_augmented", "fee_schedule", "series_slugs"]


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def slot_dt(k: int) -> datetime:
    return G0 + timedelta(hours=2 * k)


def mrow(mid: str, bid, ask, *, event: str | None = "e1", cond: str | None = None, neg: int = 0, nrkey: str = "", other: int = 0, aug="0", closed: str = "False", active: str = "True",
         binary: int = 1, ltp=0.5, vol24=1000.0, liq=50000.0, end: str = "2027-06-01T00:00:00Z", recv_off: float = 60.0, chg1h=0.0, spread=None) -> dict:
    return {"market_id": mid, "condition_id": cond or ("c" + mid), "event_id": event if event is not None else "", "closed": closed, "active": active, "binary": binary,
            "best_bid": bid, "best_ask": ask, "spread": (ask - bid) if (spread is None and bid is not None and ask is not None) else spread, "last_trade_price": ltp,
            "chg_1h": chg1h, "chg_1d": 0.0, "chg_1w": 0.0, "liquidity": liq, "volume24hr": vol24, "end_date": end, "updated_at": "", "dup_count": 1, "clob_token_id_0": "t" + mid,
            "neg_risk": "true" if neg else "false", "neg_risk_market_id": nrkey, "neg_risk_other": other, "event_neg_risk_augmented": aug, "_recv_off": recv_off}


def xrow(mid: str, *, cat: str = "politics", ftype: str = "", tick="0.01", rewards="", rmin="", rmax="", vnum="", recv_off: float = 90.0, slugs: str = "") -> dict:
    return {"market_id": mid, "received_utc": None, "fee_type": ftype, "fee_category": cat, "fees_enabled": "1", "order_price_min_tick_size": tick, "rewards_min_size": rmin,
            "rewards_max_spread": rmax, "volume_num": vnum, "created_at": "2026-01-01T00:00:00Z", "clob_rewards": rewards, "event_neg_risk_augmented": "", "fee_schedule": "", "series_slugs": slugs,
            "_recv_off": recv_off}


def write_capture(root: Path, k: int, rows: list[dict], ext: list[dict] | None, *, state: str = "complete", start_shift_s: float = 0.0) -> dict:
    """Write one capture directory for slot ``k`` and return the scan record ``{id, start, dir}``."""
    start = slot_dt(k) + timedelta(seconds=start_shift_s)
    cid = start.strftime("%Y%m%dT%H%M%SZ") + "_syn"
    d = Path(root) / cid
    d.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([{**{c: None for c in extract.COLUMNS}, **{kk: v for kk, v in r.items() if kk != "_recv_off"}} for r in rows])
    df["capture_id"], df["capture_start_utc"] = cid, iso(start)
    df["received_utc"] = [iso(start + timedelta(seconds=r.get("_recv_off", 60.0))) for r in rows]
    df = df[extract.COLUMNS]
    with gzip.open(d / "rows.csv.gz", "wt") as fh:
        df.to_csv(fh, index=False)
    if ext is not None:
        e = pd.DataFrame([{kk: v for kk, v in r.items() if kk != "_recv_off"} for r in ext])
        e["received_utc"] = [iso(start + timedelta(seconds=r.get("_recv_off", 90.0))) for r in ext]
        e = e[EXT_ORDER]
        with gzip.open(d / "rows_ext.csv.gz", "wt") as fh:
            e.to_csv(fh, index=False)
    (d / "manifest.json").write_text(json.dumps({"state": state, "started_utc": iso(start)}))
    return {"id": cid, "start": start.timestamp(), "dir": d}


def spec_for_tests(**over) -> dict:
    spec = lt.load_spec(sha=None)
    spec["k_block"] = {"chg_1d": True, "chg_1w": True}
    spec.update(over)
    return spec


def build_tree(root: Path, slots: range | list[int], gen) -> dict[int, dict]:
    """``gen(k) -> (rows, ext)``; returns ``{slot: record}``; a ``None`` result skips the slot (a missing capture)."""
    out = {}
    for k in slots:
        r = gen(k)
        if r is None:
            continue
        rows, ext = r
        out[k] = write_capture(root, k, rows, ext)
    return out


def prepare(work: Path, by_slot: dict, spec: dict) -> lt.SlotStore:
    """Write every series / status / rw / members file of ``by_slot`` into ``work`` and return a SlotStore over them."""
    for k in sorted(by_slot):
        lt.write_series11(work, by_slot[k], spec)
    return lt.SlotStore(work, by_slot, spec)


def mid_path(n_slots: int, start: float, steps: dict[int, float] | None = None, base_step: float = 0.0) -> np.ndarray:
    """A deterministic mid path with explicit jumps at slots (``steps``: slot -> change)."""
    p = np.full(n_slots, start, float)
    for i in range(1, n_slots):
        p[i] = p[i - 1] + base_step + (steps or {}).get(i, 0.0)
    return p


def quote(mid: float, half: float = 0.01) -> tuple[float, float]:
    return round(mid - half, 4), round(mid + half, 4)


__all__ = ["G0", "b", "build_tree", "iso", "mid_path", "mrow", "prepare", "quote", "slot_dt", "spec_for_tests", "write_capture", "xrow"]
