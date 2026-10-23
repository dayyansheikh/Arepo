# ruff: noqa: E501
"""Synthetic capture trees for the LT12 tests (no real data, no network): host-style ``snapshots/<id>/{rows.csv.gz, rows_ext.csv.gz, manifest.json}`` and
reward-feed captures ``reward_params/<id>/{rows.jsonl.gz, manifest.json}``."""

from __future__ import annotations

import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_lab import extract
from astrolabe.research_lab import live_tests12 as lt

G0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC)
EXT_ORDER = ["market_id", "received_utc", "fee_type", "fee_category", "fees_enabled", "order_price_min_tick_size", "rewards_min_size", "rewards_max_spread", "volume_num",
             "created_at", "clob_rewards", "event_neg_risk_augmented", "fee_schedule", "series_slugs", "accepting_orders", "event_ids"]
RW_TEXT = '[{"rewardsDailyRate": 10, "startDate": "2026-01-01", "endDate": "2027-12-31"}]'
RW_ZERO = '[{"rewardsDailyRate": 0, "startDate": "2026-01-01", "endDate": "2027-12-31"}]'


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def slot_dt(k: int) -> datetime:
    return G0 + timedelta(hours=2 * k)


def mrow(mid: str, bid, ask, *, event: str | None = "e1", cond: str | None = None, neg: int = 1, nrkey: str = "", other: int = 0, aug="0", closed: str = "False", active: str = "True",
         binary: int = 1, liq=50000.0, vol24=1000.0, end: str = "2027-06-01T00:00:00Z", recv_off: float = 60.0) -> dict:
    return {"market_id": mid, "condition_id": cond or ("c" + mid), "event_id": event if event is not None else "", "closed": closed, "active": active, "binary": binary,
            "best_bid": bid, "best_ask": ask, "spread": (ask - bid) if (bid is not None and ask is not None) else None, "last_trade_price": 0.5,
            "chg_1h": 0.0, "chg_1d": 0.0, "chg_1w": 0.0, "liquidity": liq, "volume24hr": vol24, "end_date": end, "updated_at": "", "dup_count": 1, "clob_token_id_0": "t" + mid,
            "neg_risk": "true" if neg else "false", "neg_risk_market_id": nrkey, "neg_risk_other": other, "event_neg_risk_augmented": aug, "_recv_off": recv_off}


def xrow(mid: str, *, cat: str = "politics", ftype: str = "", tick="0.01", rewards="", rmin="", rmax="", vnum="100", recv_off: float = 90.0, slugs: str = "", eids: str = "") -> dict:
    return {"market_id": mid, "received_utc": None, "fee_type": ftype, "fee_category": cat, "fees_enabled": "1", "order_price_min_tick_size": tick, "rewards_min_size": rmin,
            "rewards_max_spread": rmax, "volume_num": vnum, "created_at": "2026-01-01T00:00:00Z", "clob_rewards": rewards, "event_neg_risk_augmented": "", "fee_schedule": "",
            "series_slugs": slugs, "accepting_orders": "true", "event_ids": eids, "_recv_off": recv_off}


def write_capture(root: Path, k: int, rows: list[dict], ext: list[dict] | None, *, state: str = "complete", start_shift_s: float = 0.0) -> dict:
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


def write_feed(root: Path, start: datetime, listed: dict[str, float], *, state: str = "complete") -> str:
    """A reward-feed capture: ``listed`` = condition_id -> rate_per_day (0 = listed without a positive configuration)."""
    cid = start.strftime("%Y%m%dT%H%M%SZ") + "_feed"
    d = Path(root) / cid
    d.mkdir(parents=True, exist_ok=True)
    with gzip.open(d / "rows.jsonl.gz", "wt") as fh:
        for c, r in listed.items():
            fh.write(json.dumps({"condition_id": c, "feed": "native", "rewards_max_spread": 4.5, "rewards_min_size": 20,
                                 "rewards_config": [{"rate_per_day": r, "start_date": "2026-01-01", "end_date": "2027-12-31"}]}) + "\n")
    (d / "manifest.json").write_text(json.dumps({"state": state, "started_utc": iso(start), "finished_utc": iso(start + timedelta(minutes=3))}))
    return cid


def spec_for_tests(**over) -> dict:
    spec = lt.load_spec(sha=None)
    spec["k_block"] = {"chg_1d": True, "chg_1w": True}
    spec.update(over)
    return spec


def build_tree(root: Path, slots, gen) -> dict[int, dict]:
    out = {}
    for k in slots:
        r = gen(k)
        if r is None:
            continue
        rows, ext = r
        out[k] = write_capture(root, k, rows, ext)
    return out


def prepare(work: Path, by_slot: dict, spec: dict) -> lt.SlotStore:
    for k in sorted(by_slot):
        lt.write_series12(work, by_slot[k], spec)
    return lt.SlotStore(work, by_slot, spec)


def rich_world(root: Path, slots, seed: int = 7, *, n_pairs: int = 24, n_ladders: int = 14, feed_root: Path | None = None, feed_every: int = 1) -> dict[int, dict]:
    """A synthetic tree rich enough for both census gate blocks: ``n_pairs`` two-member neg-risk events (spreads on a 1c grid moving each slot; 6 series
    families; disjoint event ids) and ``n_ladders`` mixed ladders of 3-7 members (members 0, 2, ... rewarded; an event mid shock on about half the slots),
    plus one crypto market (the classifier's failsafe). With ``feed_root`` a feed capture 30 min before every ``feed_every``-th slot lists the rewarded
    members with a positive rate. Deterministic for a seed."""
    rng = np.random.default_rng(seed)
    n_s = max(slots) + 2
    mk: dict[str, dict] = {}
    for e in range(n_pairs):
        for j in range(2):
            sp = np.clip(1 + rng.integers(0, 5, n_s), 1, 6) / 100.0
            base = 0.40 + 0.1 * j
            mk[f"p{e}_{j}"] = {"mid": np.round(base + rng.normal(0, 0.005, n_s), 3), "spread": sp, "nrkey": f"NRP{e}", "event": f"EP{e}", "rew": j == 0, "liq": float(rng.uniform(2e3, 2e5)),
                               "slugs": f'["fam{e % 6}"]', "eids": f'["EP{e}"]'}
    for e in range(n_ladders):
        n = 3 + (e % 5)
        shock = np.clip(np.where(rng.random(n_s) < 0.5, rng.choice([-0.02, 0.02], n_s), 0.0).cumsum(), -0.04, 0.04)
        for j in range(n):
            mid = np.clip(0.85 / n + shock + rng.normal(0, 0.002, n_s), 0.03, 0.9)
            mk[f"l{e}_{j}"] = {"mid": np.round(mid, 3), "spread": np.clip(rng.integers(1, 5, n_s), 1, 6) / 100.0, "nrkey": f"NRL{e}", "event": f"EL{e}", "rew": j % 2 == 0,
                               "liq": float(rng.uniform(5e2, 3e5)), "slugs": f'["lad{e % 4}"]', "eids": f'["EL{e}"]'}
    mk["x0"] = {"mid": np.full(n_s, 0.5), "spread": np.full(n_s, 0.02), "nrkey": "", "event": "ex0", "rew": False, "liq": 1e4, "cat": "crypto", "neg": 0, "slugs": "", "eids": ""}
    by_slot = {}
    for s in slots:
        rows, ext = [], []
        for mid_id, m in mk.items():
            p, half = float(m["mid"][s]), float(m["spread"][s]) / 2.0
            bid, ask = round(p - half, 4), round(p + half, 4)
            rows.append(mrow(mid_id, bid, ask, event=m["event"], neg=m.get("neg", 1), nrkey=m["nrkey"], liq=m["liq"], recv_off=60.0 + (hash(mid_id) % 20)))
            ext.append(xrow(mid_id, cat=m.get("cat", "politics"), rewards=RW_TEXT if m["rew"] else "", rmin=20 if m["rew"] else "", rmax=4.5 if m["rew"] else "",
                            slugs=m["slugs"], eids=m["eids"]))
        by_slot[s] = write_capture(root, s, rows, ext)
        if feed_root is not None and s % feed_every == 0:
            write_feed(feed_root, slot_dt(s) - timedelta(minutes=30), {"c" + k_: 10.0 for k_, m in mk.items() if m["rew"]})
    return by_slot


def loose_spec(spec: dict) -> dict:
    """Every census minimum made trivial and every maximum made huge, so that a rich synthetic world passes each gate block; a test then makes ONE threshold
    impossible and asserts the gate it governs (and the status) flips."""
    g = spec["census_gates"]
    keep = ("events_min_units", "same_slot_min_pair_captures", "ident_nonzero_min", "block_min_captures", "leverage_top_frac", "same_slot_abs_corr", "venue_clock_abs_z", "de_floor")
    for blk in ("CH245", "CH244"):
        for k, v in list(g[blk].items()):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or k in keep:
                continue
            if k.endswith("_min"):
                g[blk][k] = 0
            elif k.endswith("_max"):
                g[blk][k] = 1e9
    g["CH244"]["shock_share_band"] = [0.0, 1.0]
    g["CH245"]["block_min_captures"] = 2
    g["CH244"]["block_min_captures"] = 2
    g["CH245"]["same_slot_min_pair_captures"] = 2
    g["mde_common"]["g_eff_min"] = 0
    g["mde_common"]["mde_max_c"] = {"CH245": 1e9, "CH244": 1e9}
    g["mde_common"]["f_mde_max_c"] = {"CH245": 1e9, "CH244": 1e9}
    return spec


def census_spec(first: int = 14, last: int = 40) -> dict:
    spec = loose_spec(spec_for_tests())
    ci = spec["census_inputs"]
    ci["span"] = {"start_utc": iso(slot_dt(first)), "end_utc": iso(slot_dt(last + 1)), "first_slot_utc": iso(slot_dt(first)), "last_slot_utc": iso(slot_dt(last))}
    ci["min_covered_days"] = {"CC12": 1.0, "CC12_twins": 1.0}
    ci["refuse_at_or_after_utc"] = iso(slot_dt(100))
    ci["feed_window"] = [iso(slot_dt(0)), iso(slot_dt(100))]
    return spec
