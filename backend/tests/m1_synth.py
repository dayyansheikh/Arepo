# ruff: noqa: E501
"""Synthetic stores for the M1 code tests: tmp trees only, never real data. Captures k = 0..N-1 on the 2 h grid from 2026-10-20T00:31Z;
look-back captures k < L, window captures k = L..L+W-1 (spec override; real pins)."""

from __future__ import annotations

import copy
import csv
import gzip
import json
import shutil
from datetime import UTC, datetime, timedelta  # noqa: F401
from pathlib import Path

from astrolabe.research_lab import m1_spec as sp

T0 = datetime(2026, 10, 20, 0, 31, tzinfo=UTC)
L, W = 6, 12
MISSING_K = 11  # window capture 11 is never delivered on time
RCOLS = ["market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date", "clob_token_id_0", "spread"]
ECOLS = ["market_id", "received_utc", "clob_token_id_1", "uma_resolution_statuses", "accepting_orders", "fee_type", "fee_category", "series_slugs",
         "fees_enabled", "fee_schedule", "order_price_min_tick_size", "outcome_trap"]
FEE_0 = '{"exponent":1,"rate":0,"rebateRate":0,"takerOnly":true}'
FEE_4 = '{"exponent":1,"rate":0.04,"rebateRate":0.25,"takerOnly":true}'
# per-test extra markets: {market_id: (event, bid, ask, fee_category, accepting_orders, first_proposed_k)}, set with monkeypatch.setitem; empty by default
EXTRA: dict = {}
P, E, PD = '["proposed"]', "[]", '["proposed","disputed"]'


def tcap(k: int) -> datetime:
    return T0 + timedelta(hours=2 * k)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def cid(k: int) -> str:
    return f"{tcap(k):%Y%m%dT%H%M%S}Z_{k:08x}"


def slot(k: int) -> int:
    return int(round((tcap(k).timestamp() - sp.grid0(sp.SPEC)) / 7200.0))


def make_spec(b: int = 200) -> dict:
    spec = copy.deepcopy(sp.SPEC)
    spec["registered_utc"] = iso(tcap(L) - timedelta(minutes=31))
    spec["end_utc"] = iso(tcap(L + W) - timedelta(minutes=31))
    spec["readout_utc"] = iso(tcap(L + W) - timedelta(minutes=31) + timedelta(days=31))
    spec["lookback_min_captures"] = 4
    spec["bootstrap"] = dict(spec["bootstrap"], B=b, chunk=100)
    spec["fetch"] = dict(spec["fetch"], batch=2)
    spec["cells"] = spec["cells"]
    return spec


# (event, bid, ask, category, fee_schedule, fees_enabled, first proposed k, status(k) override)
def status(mid: int, k: int) -> str:
    if mid in EXTRA:
        return P if k >= EXTRA[mid][5] else E
    t = {1: P if k >= 8 else E, 2: P if k >= 9 else E, 3: P if k >= 8 else E, 4: P if k >= 9 else E, 5: PD if k == 10 else E, 6: P if k >= 10 else E,
         7: P, 8: P if (k == 3 or k >= 14) else E, 9: P if k >= 13 else E, 10: P if k >= 13 else E, 11: P if k >= 16 else E, 12: P if k >= 4 else E}
    return t[mid]


def spec_rows(k: int) -> list[tuple]:
    """(market, event, bid, ask, category, fee_schedule, fees_enabled, closed) present at capture k."""
    out = [(1, "e1", "0.9413", "0.9613", "politics", FEE_0, "false", "false"),
           (2, "e2", "0.02", "0.04", "Finance:US", FEE_4, "true", "false"),
           (3, "e3", "0.94", "0.96", "sports", FEE_0, "false", "false"),
           (4, "e4", "0.50", "0.52", "politics", FEE_0, "false", "false"),
           (5, "e5", "0.94", "0.96", "politics", FEE_0, "false", "false"),
           (6, "e6", "0", "0.99", "politics", FEE_0, "false", "false"),
           (8, "e8", "0.94", "0.96", "politics", FEE_0, "false", "false"),
           (9, "e9", "0.94", "0.96", "politics", FEE_0, "false", "false"),
           (10, "e9", "0.01", "0.03", "politics", FEE_0, "false", "false"),
           (11, "e11", "0.94", "0.96", "politics", FEE_0, "false", "true" if k >= 16 else "false"),
           (12, "e12", "0.94", "0.96", "politics", FEE_0, "false", "false")]
    for mid, (ev, bid, ask, cat, _acc, _k0) in sorted(EXTRA.items()):
        out.append((mid, ev, bid, ask, cat, FEE_0, "false", "false"))
    if k >= 15:
        out.append((7, "e7", "0.94", "0.96", "politics", FEE_0, "false", "false"))  # first seen already proposed: no k - 1 row
    return out


SWEEPS = {9: [("t2_1", "50", "0.98")], 13: [("t9_0", "100", "0.96")]}


def write_capture(snap: Path, k: int, finish_after_min: float = 5.0) -> None:
    """A complete capture; its manifest ``finished_utc`` is ``finish_after_min`` after the start (the missing rule reads it)."""
    d = snap / cid(k)
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "started_utc": iso(tcap(k)), "finished_utc": iso(tcap(k) + timedelta(minutes=finish_after_min)), "capture_id": cid(k)}))
    rec = iso(tcap(k) + timedelta(minutes=3))
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(RCOLS)
        for mid, ev, bid, ask, _c, _f, _e, closed in spec_rows(k):
            w.writerow([mid, ev, rec, closed, "true", "1", bid, ask, "50000", "2026-12-20T00:00:00Z", f"t{mid}_0", ""])
    with gzip.open(d / "rows_ext.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ECOLS)
        for mid, _ev, _b, _a, cat, fsch, fe, _cl in spec_rows(k):
            w.writerow([mid, rec, f"t{mid}_1", status(mid, k), EXTRA[mid][4] if mid in EXTRA else "true", "", cat, "", fe, fsch, "0.001", "YES_WON_SECRET"])


def write_sweep(sw: Path, k: int) -> None:
    d = sw / f"sweep_{k:03d}"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"state": "complete", "series_index": 0, "snapshot_id": cid(k)}))
    with gzip.open(d / "rows.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["token_id", "market_id", "batch_receipt_utc", "best_bid", "best_ask", "ask_size_1", "depth_ask_1c", "state"])
        for tok, asz, ba in SWEEPS[k]:
            w.writerow([tok, tok[1:].split("_")[0], iso(tcap(k) + timedelta(minutes=9)), "0.94", ba, asz, "500", "two_sided"])


def build_stores(root: Path, skip: tuple = (MISSING_K,)) -> tuple[Path, Path]:
    """All captures k = 0..L+W-1 except those in ``skip`` (default: the missing window capture)."""
    snap, sw = root / "research_lab" / "snapshots", root / "research_lab" / "book_sweeps"
    snap.mkdir(parents=True)
    sw.mkdir(parents=True)
    for k in range(L + W):
        if k not in skip:
            write_capture(snap, k)
    for k in SWEEPS:
        write_sweep(sw, k)
    return snap, sw


def move_capture(src_snap: Path, dst_snap: Path, k: int) -> None:
    dst_snap.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_snap / cid(k)), str(dst_snap / cid(k)))


def after_end(spec: dict) -> float:
    return sp.ts(spec, "end_utc") + 7 * 3600.0


def after_readout(spec: dict) -> float:
    return sp.ts(spec, "readout_utc") + 13 * 3600.0
