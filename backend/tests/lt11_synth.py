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


RW_TEXT = '[{"rewardsDailyRate": 10, "startDate": "2026-01-01", "endDate": "2027-12-31"}]'


def rich_world(root: Path, slots: range, seed: int = 7) -> dict[int, dict]:
    """A synthetic tree rich enough for every census gate block: 60 free-standing movers (CH234 / CH232 populations, half rewarded), 30 band-hoppers near
    0.10 / 0.90 (CH232), and 20 neg-risk events of 3-6 members (CH233). Deterministic for a seed; no real data."""
    rng = np.random.default_rng(seed)
    n_s = max(slots) + 1
    mk: dict[str, dict] = {}
    # free movers: a mid random walk with jumps of 1-4c, a cumulative volume_num that rises on about 60% of the jumps
    for i in range(60):
        mid = np.empty(n_s)
        v = np.empty(n_s)
        mid[0], v[0] = rng.uniform(0.1, 0.9), 1000.0
        for s in range(1, n_s):
            jump = rng.random() < 0.55
            step = rng.choice([-1, 1]) * rng.integers(1, 5) * 0.01 if jump else 0.0
            mid[s] = float(np.clip(mid[s - 1] + step, 0.05, 0.95))
            v[s] = v[s - 1] + (rng.uniform(5, 50) if (jump and rng.random() < 0.6) else 0.0)
        mk[f"a{i}"] = {"mid": mid, "v": v, "event": f"ea{i // 2}", "rew": i % 2 == 0, "liq": float(rng.uniform(2e3, 2e5)), "cat": ["politics", "economics", "culture"][i % 3]}
    # band hoppers: near 0.10 / 0.90, crossing the boundary on about a quarter of the slots
    for i in range(30):
        base = 0.12 if i % 2 == 0 else 0.88
        mid = np.empty(n_s)
        mid[0] = base
        inside = True
        for s in range(1, n_s):
            if rng.random() < 0.3:
                inside = not inside
            lo = (0.11, 0.14) if base < 0.5 else (0.86, 0.89)
            out = (0.05, 0.085) if base < 0.5 else (0.915, 0.95)
            mid[s] = rng.uniform(*lo) if inside else rng.uniform(*out)
        mk[f"h{i}"] = {"mid": np.round(mid, 3), "v": np.cumsum(np.full(n_s, 10.0)), "event": f"eh{i // 3}", "rew": i % 3 != 0, "liq": 5e4, "cat": "politics"}
    # neg-risk events: bids around 0.9 / n with an event shock and member noise
    for e in range(20):
        n = 3 + (e % 4)
        shock = rng.normal(0, 0.012, n_s)
        for m in range(n):
            bid = np.clip(0.88 / n + shock + rng.normal(0, 0.004, n_s), 0.02, 0.9)
            mk[f"n{e}_{m}"] = {"mid": np.round(bid + 0.01, 4), "v": np.cumsum(np.full(n_s, 5.0)), "event": f"en{e}", "rew": False, "liq": 3e4, "cat": "politics", "neg": True, "nrkey": f"NR{e}"}
    mk["x0"] = {"mid": np.full(n_s, 0.5), "v": np.cumsum(np.full(n_s, 1.0)), "event": "ex0", "rew": False, "liq": 1e4, "cat": "crypto"}  # the crypto classifier needs a crypto value in the set
    by_slot = {}
    for s in slots:
        rows, ext = [], []
        for mid_id, m in mk.items():
            p = float(m["mid"][s])
            bid, ask = quote(p, 0.01)
            liq = m["liq"] * (1.0 + 0.2 * np.sin(0.7 * s + sum(map(ord, mid_id)) % 7))  # a liquidity that moves over time (a within-market control)
            rows.append(mrow(mid_id, bid, ask, event=m["event"], neg=1 if m.get("neg") else 0, nrkey=m.get("nrkey", ""), liq=liq, recv_off=60.0))
            vn = "" if (mid_id.startswith("a") and rng.random() < 0.12) else float(m["v"][s])  # some volume_num cells are empty (the unknown class)
            ext.append(xrow(mid_id, cat=m["cat"], vnum=vn, rewards=RW_TEXT if m["rew"] else "", rmin=20 if m["rew"] else "", rmax=4.5 if m["rew"] else ""))
        by_slot[s] = write_capture(root, s, rows, ext)
    return by_slot


def loose_spec(spec: dict) -> dict:
    """Every census minimum made trivial and every maximum made huge, so that a rich synthetic world passes each gate block; a test then makes ONE
    threshold impossible and asserts the gate it governs (and the status) flips."""
    g = spec["census_gates"]
    for blk in ("CH234", "CH233", "CH232"):
        for k, v in list(g[blk].items()):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            if k.endswith("_min") and k not in ("events_min_units", "w_sd_min_moves", "pair_min_per_market", "resid_iqr_min_units"):
                g[blk][k] = 1 if k.endswith(("events_min", "markets_min")) else 0
            elif k.endswith("_max") and not k.startswith("unknown_capture_cut"):
                g[blk][k] = 1e9
    g["CH234"]["resid_iqr_markets_min"] = 1
    g["CH234"]["unknown_capture_cut"] = 0.80
    g["mde_common"]["g_eff_min"] = 0
    g["mde_common"]["mde_max_c"] = {"CH234": 1e9, "CH233": 1e9, "CH232": 1e9}
    g["mde_common"]["f_mde_max_c"] = {"CH234": 1e9, "CH233": 1e9, "CH232": 1e9}
    spec["census_inputs"]["band_unit_check_cents"] = [0.5, 20]
    return spec


def census_spec(first: int = 14, last: int = 66) -> dict:
    spec = loose_spec(spec_for_tests())
    ci = spec["census_inputs"]
    ci["span"] = {"start_utc": iso(slot_dt(first)), "end_utc": iso(slot_dt(last + 1)), "first_slot_utc": iso(slot_dt(first)), "last_slot_utc": iso(slot_dt(last))}
    ci["min_covered_days"] = {"CC11": 1.0, "CC11_twins": 1.0}
    ci["refuse_at_or_after_utc"] = iso(slot_dt(100))
    return spec
