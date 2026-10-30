# ruff: noqa: E501
"""Synthetic capture trees for the LT13 tests (no real data, no network): ``snapshots/<id>/{rows.csv.gz, rows_ext.csv.gz, manifest.json}`` with listing batches (markets created
within seconds of each other, spread over several events) and singletons. Built on the LT12 synthetic writers."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from astrolabe.research_lab import live_tests13_base as t
from tests import lt12_synth as sy

T0 = datetime(2026, 10, 1, 0, 0, tzinfo=UTC)
FEE_ON = '{"rate": 0.04, "rebateRate": 0.25}'
FEE_FREE = '{"rate": 0, "rebateRate": 0}'


def cstr(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_world(root: Path, slots, seed: int = 11, *, n_batches: int = 24, per_batch: int = 6, n_events: int = 3, singles: int = 40, recv_jitter: float = 20.0, drop: dict | None = None,
               created_gap_s: float = 15.0, same_event_batches: tuple = (), cats=("politics_fees", "zero_fees")) -> dict:
    """Returns {slot: capture dict}. Batch b has ``per_batch`` markets over ``n_events`` events, created ``created_gap_s`` apart, batches 3 days apart (so some are >= 7 days from each
    other); a shared batch spread factor makes the mates' innovation informative. ``drop`` = {market_id: set(slots)} removes rows. A crypto singleton is included (the classifier's failsafe)."""
    rng = np.random.default_rng(seed)
    n_s = max(slots) + 2
    mk: dict[str, dict] = {}
    for bi in range(n_batches):
        base = T0 + timedelta(days=3 * bi, hours=int(rng.integers(0, 20)))
        fac = np.clip(np.round(2 + np.cumsum(rng.normal(0, 0.8, n_s))), 1, 6)
        for j in range(per_batch):
            mid_id = f"b{bi}_{j}"
            ev = f"EB{bi}" if bi in same_event_batches else f"EB{bi}_{j % n_events}"
            sp = np.clip(fac + rng.integers(-1, 2, n_s), 1, 7)
            mk[mid_id] = {"mid": np.round(0.5 + rng.normal(0, 0.01, n_s), 3), "spread": sp / 100.0, "event": ev, "created": base + timedelta(seconds=created_gap_s * j),
                          "cat": cats[bi % len(cats)], "slugs": f'["fam{bi % 5}"]', "liq": float(np.exp(rng.uniform(np.log(200.0), np.log(2e5))))}
    for si in range(singles):
        sp = np.clip(2 + rng.integers(-1, 3, n_s), 1, 6)
        mk[f"s{si}"] = {"mid": np.round(0.4 + rng.normal(0, 0.01, n_s), 3), "spread": sp / 100.0, "event": f"ES{si}", "created": T0 + timedelta(days=int(rng.integers(0, 70)), hours=7 + si),
                        "cat": cats[si % len(cats)], "slugs": f'["fams{si % 7}"]', "liq": float(np.exp(rng.uniform(np.log(200.0), np.log(2e5))))}
    mk["x0"] = {"mid": np.full(n_s, 0.5), "spread": np.full(n_s, 0.02), "event": "ex0", "created": T0 + timedelta(days=1, hours=3), "cat": "crypto", "slugs": "", "liq": 1e4}
    by_slot = {}
    for s in slots:
        rows, ext = [], []
        for mid_id, m in mk.items():
            if drop and s in drop.get(mid_id, ()):
                continue
            p, half = float(m["mid"][s]), float(m["spread"][s]) / 2.0
            bid, ask = round(p - half, 4), round(p + half, 4)
            off = 60.0 + (abs(hash(mid_id)) % int(recv_jitter))
            if drop and ("late", mid_id) in drop:
                off += 300.0
            rows.append(sy.mrow(mid_id, bid, ask, event=m["event"], neg=0, nrkey="", liq=m["liq"], vol24=float(rng.uniform(100, 5e4)), recv_off=off))
            x = sy.xrow(mid_id, cat=m["cat"], ftype=m["cat"], slugs=m["slugs"], eids=f'["{m["event"]}"]')
            x["created_at"] = cstr(m["created"])
            x["fee_schedule"] = FEE_FREE if m["cat"] == "zero_fees" else FEE_ON
            ext.append(x)
        by_slot[s] = sy.write_capture(root, s, rows, ext)
    return by_slot


def loose_spec(first: int = 14, last: int = 40) -> dict:
    """Every census minimum made trivial and every maximum huge, so a rich synthetic world passes the CH253 block; a test then makes ONE threshold impossible."""
    spec = t.load_spec()
    spec["k_block"] = {"chg_1d": True, "chg_1w": True}
    spec["k_tests"], spec["dropped_tests"], spec["census_unavailable"] = None, None, None
    g = spec["census_gates"]["CH253"]
    keep = ("events_min_units", "same_slot_min_units", "ident_nonzero_min", "block_min_captures", "leverage_top_frac", "same_slot_abs_corr", "venue_clock_abs_z", "de_floor")
    for k, v in list(g.items()):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or k in keep:
            continue
        if k.endswith("_min"):
            g[k] = 0
        elif k.endswith("_max"):
            g[k] = 1e9
    g["block_min_captures"], g["same_slot_min_units"], g["events_min_units"] = 2, 2, 2
    g["ident_nonzero_min"] = 1
    spec["controls_own"] = [c for c in spec["controls_own"] if c != "spread_km1_c"]  # the declared list is exactly collinear (A3); the happy-path tests drop the redundant column
    spec["census_gates"]["mde_common"]["g_eff_min"] = 0
    spec["census_gates"]["mde_common"]["mde_max_c"] = {"CH253": 1e9}
    spec["census_gates"]["mde_common"]["f_mde_max_c"] = {"CH253": 1e9}
    ci = spec["census_inputs"]
    ci["span"] = {"start_utc": sy.iso(sy.slot_dt(first)), "end_utc": sy.iso(sy.slot_dt(last + 1)), "first_slot_utc": sy.iso(sy.slot_dt(first)), "last_slot_utc": sy.iso(sy.slot_dt(last))}
    ci["min_covered_days"] = {"CC13": 1.0, "CC13_twins": 1.0}
    ci["refuse_at_or_after_utc"] = sy.iso(sy.slot_dt(100))
    return copy.deepcopy(spec)
