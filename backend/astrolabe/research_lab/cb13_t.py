# ruff: noqa: E501
"""CB13-T: maker toxicity by resolution class (docs/research_lab/CREATIVE_BATCH_13.md CB13-T, section 10 items 1-4, 9, 10, 14). Rules part ``T``.

Host files only, NO network: the live large-trade monitor's prints (``live_trades/trades-YYYYMMDD.jsonl``, whitelisted fields) and the complete-universe captures
(``snapshots/<capture>/rows.csv.gz`` + ``rows_ext.csv.gz``, whitelisted columns). The class labeller is its own frozen part (``cb13_label``, rules part ``LABELLER``).

**Print-anchored fill (round 1 item 1).** A large taker transaction (``tx16`` + condition id aggregated in memory, the hash discarded) is a real maker fill. With its YES-terms prices
``[P_min, P_max]`` and the touch ``(b0, a0)``, ``s0 = a0 - b0``: ``a0 <= P_min`` and ``P_max <= a0 + s0`` -> the maker SOLD YES (``d = -1``) at ``P = P_min``; ``b0 - s0 <= P_min`` and
``P_max <= b0`` -> the maker BOUGHT YES (``d = +1``) at ``P = P_max``; strictly inside the spread -> no fill (counted); anything else -> "inconsistent with touch (drift)" (counted by class).
``M_h = 100 d (mid_h - P)`` cents. The touch only signs the print; the stale-touch variant (paper quote at the touch itself) is reported, not counted.

The quote index has two modes: ``touch`` (frame and census: NO mark accessor exists, ``mark()`` raises) and ``mark`` (screen and rep). Every capture or print timed inside the J4-R window is
refused. Nothing here computes anything for ``surprise_live`` / E011 / E004-E007 (no ``chg_1h``, no alert, candidate or control status).
"""

from __future__ import annotations

import json
import math
import time
from bisect import bisect_left
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import numpy as np

from . import cb8_common as cm
from . import cb13_common as c13
from . import cb13_label as lab

Refused = cm.Refused
NotNow = cm.NotNow

LABEL_T = "L1, worn captures, new statistic"
LABEL_T2 = "mid-marked maker net, upper bound (free exit), L1"
LABEL_HOLD = "adjacent window, same regime"
LABEL_T3 = "recorded-touch round trip (L2)"
LABEL_REP = "later live window replication, event-disjoint (L2)"
LABEL_THIN = "population thinned by exclusions"
LABEL_HOLD_THIN = "HOLDOUT thinned by event overlap"
LABEL_CADENCE = "cadence informativeness unverified (n < 200)"
SCREEN_STATUS_FILL = "fill"
S_INSIDE = "inside spread"
S_INCONSISTENT = "inconsistent with touch (drift)"
S_NO_ROW = "excluded: no row"
S_STALE = "excluded: touch older than 60 min"
S_ONESIDED = "excluded: one-sided"
S_MID = "excluded: mid outside [0.03, 0.97]"
S_SPREAD = "excluded: spread > 10c"
S_END = "excluded: scheduled end within 3 h"
S_NOTBINARY = "excluded: not binary or closed"
S_UNKNOWN = "excluded: UNKNOWN label"
S_KEY = "dropped: key"
TOUCH_MAX_AGE_S = 3600.0
TOUCH_AGE_ROBUST_S = 1200.0
SPREAD_MAX = 0.10
MID_LO = 0.03
MID_HI = 0.97
END_MARGIN_S = 3 * 3600.0
MARK_H = {"2-4h": 7200.0, "6-8h": 21600.0}
MARK_USABLE_EXTRA_S = 7200.0
WIDE_MARK = 0.10
BIG_TX_USD = 10000.0
T1_FLOOR = 0.5  # cents per filled share
T2_FLOOR = 0.25
T3_FLOOR = 0.5
T3_EXIT_ROBUST = 0.5
T3_DEFAULT_FEE = 0.07
T3_MAX_SIZE = 100.0
GT_MIN = {"fills": 500, "events": 60}
GTP_MDE_MAX = {"T1": 1.0, "T2": 0.5}
GTI_MIN_PAIRS = 200
GTI_AGREE = 0.70
GTI_WINDOW_S = 1800.0
EXCL_THIN_SHARE = 0.30
HOLD_OVERLAP_THIN_SHARE = 0.40
COMPONENT_MIN_FILLS = 200
SPREAD_BANDS = (0.01, 0.02, 0.04)
MID_BANDS = (0.2, 0.4, 0.6, 0.8)
TTE_BANDS_S = (86400.0, 7 * 86400.0)
SIZE_BANDS = (2000.0, 5000.0, 10000.0)
AGE_BANDS_S = (1200.0, 2400.0)
SMOKE_NEEDS = ("guards_fixture_T", "t_capture_print_join", "t_labeller_unknown")
T_EXCL_SKIP_RUNS = ("h1_first", "h2_main", "h3_power", "h4_seal", "h13_touch", "h13_binance")
FILL_COLUMNS = ["tx_id", "condition_id", "market_id", "event_id", "status", "label", "underlying", "path_key", "tau", "tau_last", "p_vwap", "p_min", "p_max", "size", "cash", "n_fills", "d", "P",
                "bid0", "ask0", "spread0", "mid0", "touch_recv", "touch_age_s", "touch_cap", "liq", "end_epoch", "prev_mid", "prev_recv", "q_stale", "d_stale", "fee_rate", "clob_rewards",
                "fee_type", "block", "day", "neg_risk_market_id"]
LABEL_COLUMNS = ["condition_id", "label", "underlying", "fee_type", "fee_category", "series_slug", "title", "slug"]
MARK_COLUMNS = ["tx_id", "h", "status", "recv", "bid", "ask"]
FILLS_NAME = "fills.csv.gz"
LABELS_NAME = "labels.csv.gz"
EXCL_NAME = "t_exclusion_keys.csv.gz"
AUDIT_NAME = "labeller_audit.json"


# =====================================================================================================================================================
# Transactions
# =====================================================================================================================================================


def yes_price(p: dict) -> float:
    """YES-terms price of a whitelisted print: outcome index 0 keeps its price, index 1 maps to ``1 - price``."""
    return float(p["price"]) if int(p["outcome_index"]) == 0 else 1.0 - float(p["price"])


def build_transactions(prints, *, aggregate: bool = True) -> tuple[list[dict], dict]:
    """Prints -> one row per (``tx16``, condition id) in YES terms, the hash discarded: earliest / latest venue time, size-weighted VWAP, min and max YES price, total size, cash, count and the
    static print attributes. A print without a hash is its own transaction (counted). ``aggregate=False`` makes every print its own row (the all-prints variant)."""
    groups: dict[tuple, list[dict]] = {}
    n_nohash = 0
    for i, p in enumerate(prints):
        if aggregate and p.get("tx16"):
            key = (p["tx16"], p["condition_id"])
        else:
            n_nohash += 1 if aggregate else 0
            key = (f"single:{i}", p["condition_id"])
        groups.setdefault(key, []).append(p)
    rows = []
    for fills in groups.values():
        ys = [yes_price(f) for f in fills]
        sz = sum(f["size"] for f in fills)
        cash = sum((f["cash"] if math.isfinite(f["cash"]) else f["size"] * f["price"]) for f in fills)
        f0 = min(fills, key=lambda f: f["ts"])
        rows.append({"condition_id": f0["condition_id"], "ts": min(f["ts"] for f in fills), "ts_last": max(f["ts"] for f in fills), "p_vwap": sum(y * f["size"] for y, f in zip(ys, fills, strict=True)) / sz,
                     "p_min": min(ys), "p_max": max(ys), "size": sz, "cash": cash, "n_fills": len(fills), "title": f0.get("title") or "", "slug": f0.get("slug") or "",
                     "ctx_event_id": f0.get("ctx_event_id"), "ctx_market_id": f0.get("ctx_market_id"), "ctx_category": f0.get("ctx_category") or "", "ctx_fee_type": f0.get("ctx_fee_type") or ""})
    rows.sort(key=lambda r: (r["ts"], r["condition_id"], r["p_vwap"]))
    return rows, {"n_nohash": n_nohash, "n_tx": len(rows)}


def classify_position(p_min: float, p_max: float, b0: float, a0: float, tol: float = 1e-9) -> tuple[str, int, float]:
    """(kind, d, P): "lift" (maker sold, P = P_min), "hit" (maker bought, P = P_max), "inside" or "inconsistent" (d = 0, P = nan)."""
    s0 = a0 - b0
    if a0 <= p_min + tol and p_max <= a0 + s0 + tol:
        return "lift", -1, float(p_min)
    if b0 - s0 - tol <= p_min and p_max <= b0 + tol:
        return "hit", 1, float(p_max)
    if b0 < p_min - tol and p_max < a0 - tol:
        return "inside", 0, math.nan
    return "inconsistent", 0, math.nan


def stale_variant(p_vwap: float, b0: float, a0: float) -> tuple[float, int]:
    """The draft's stale-touch paper quote (reported, uncounted): the quote is the touch itself, the side is read against it."""
    if p_vwap >= a0:
        return a0, -1
    if p_vwap <= b0:
        return b0, 1
    return math.nan, 0


# =====================================================================================================================================================
# The quote index (touch mode: no mark accessor)
# =====================================================================================================================================================


class Q(NamedTuple):
    recv: float
    bid: float
    ask: float
    liq: float
    end: float
    cap: int
    closed: bool
    binary: bool
    market_id: str
    event_id: str
    nrm: str


def two_sided(bid: float, ask: float) -> bool:
    return bool(math.isfinite(bid) and math.isfinite(ask) and 0.0 < bid < ask < 1.0)


class QuoteIndex:
    """Per-condition quote rows (whitelisted fields) of the allowed captures, newest queries by bisect. ``mode='touch'`` has no ``mark``; ``mode='mark'`` allows it."""

    def __init__(self, mode: str, boundary_epoch: float | None = None):
        if mode not in ("touch", "mark"):
            raise Refused(f"quote index mode {mode!r}")
        self.mode = mode
        self.boundary_epoch = boundary_epoch
        self.q: dict[str, list[Q]] = {}
        self.recv: dict[str, list[float]] = {}
        self.static: dict[str, dict] = {}
        self.caps: list[tuple[float, str]] = []

    def add(self, cid: str, row: Q) -> None:
        self.q.setdefault(cid, []).append(row)

    def finish(self) -> None:
        for cid, lst in self.q.items():
            lst.sort(key=lambda x: x.recv)
            self.recv[cid] = [x.recv for x in lst]

    def touch(self, cid: str, tau: float) -> tuple[Q | None, Q | None]:
        """(touch row, row in the capture before the touch capture): the market's latest row with ``received_utc < tau`` (equality excluded)."""
        lst = self.q.get(cid)
        if not lst:
            return None, None
        j = bisect_left(self.recv[cid], tau) - 1
        if j < 0:
            return None, None
        t = lst[j]
        prev = lst[j - 1] if j >= 1 and lst[j - 1].cap == t.cap - 1 else None
        return t, prev

    def capture_in(self, lo: float, hi: float) -> bool:
        return any(lo <= s <= hi for s, _ in self.caps)

    def mark(self, cid: str, tau: float, h: float) -> dict:
        """The mark at nominal horizon ``h``: the market's row in the first capture with ``received_utc >= tau + h``, usable iff received <= tau + h + 2 h. A capture that lacks the market is
        skipped (the realised horizon is reported). Statuses: ok / wide / onesided / closed_absent / gap / boundary."""
        if self.mode != "mark":
            raise Refused("the quote index is in touch mode: no mark quote is available to a frame or census path")
        target = tau + h
        lim = target + MARK_USABLE_EXTRA_S
        lst = self.q.get(cid) or []
        i = bisect_left(self.recv.get(cid, []), target)
        if i < len(lst) and lst[i].recv <= lim:
            r = lst[i]
            if not two_sided(r.bid, r.ask):
                return {"status": "onesided", "recv": r.recv, "bid": r.bid, "ask": r.ask, "realised": r.recv - tau}
            st = "wide" if (r.ask - r.bid) > WIDE_MARK + 1e-9 else "ok"
            return {"status": st, "recv": r.recv, "bid": r.bid, "ask": r.ask, "realised": r.recv - tau}
        if self.capture_in(target - 400.0, lim):
            return {"status": "closed_absent", "recv": math.nan, "bid": math.nan, "ask": math.nan, "realised": math.nan}
        if self.boundary_epoch is not None and lim > self.boundary_epoch:
            return {"status": "boundary", "recv": math.nan, "bid": math.nan, "ask": math.nan, "realised": math.nan}
        return {"status": "gap", "recv": math.nan, "bid": math.nan, "ask": math.nan, "realised": math.nan}


    def mark_for(self, fill: dict, h: float) -> dict:
        return self.mark(fill["condition_id"], fill["tau"], h)


class MarkTable:
    """The sealed HOLDOUT raw mark-quote table (q0274) behind the same ``mark_for`` interface as a mark-mode ``QuoteIndex``: ``(tx_id, h)`` -> status, bid, ask, recv. No mark-out is stored in it."""

    mode = "mark"

    def __init__(self, rows: list[dict], taus: dict[int, float]):
        self.rows = {(int(float(r["tx_id"])), r["h"]): r for r in rows}
        self.taus = taus

    def mark_for(self, fill: dict, h: float) -> dict:
        key = next(k for k, v in MARK_H.items() if v == h)
        r = self.rows.get((int(fill["tx_id"]), key))
        if r is None:
            return {"status": "gap", "recv": math.nan, "bid": math.nan, "ask": math.nan, "realised": math.nan}
        recv = c13.num(r["recv"]) if r["recv"] not in ("", None) else math.nan
        return {"status": r["status"], "recv": recv, "bid": c13.num(r["bid"]) if r["bid"] not in ("", None) else math.nan,
                "ask": c13.num(r["ask"]) if r["ask"] not in ("", None) else math.nan, "realised": recv - fill["tau"] if math.isfinite(recv) else math.nan}


def fee_rate_of(fee_schedule) -> float:
    try:
        d = json.loads(fee_schedule) if isinstance(fee_schedule, str) and fee_schedule else {}
    except ValueError:
        return math.nan
    return c13.num(d.get("rate")) if isinstance(d, dict) else math.nan


def load_quote_index(captures: list[dict], wanted: set[str], mode: str, split: str, pin: dict, *, boundary_epoch: float | None = None) -> QuoteIndex:
    """Stream the allowed captures one at a time (whitelisted columns, rows filtered to ``wanted`` condition ids) into a ``QuoteIndex``; the sidecar's static attributes are taken from the first
    capture that carries the market."""
    qi = QuoteIndex(mode, boundary_epoch)
    for k, meta in enumerate(captures):
        c13.require_capture_allowed(meta["start"], split, pin)
        qi.caps.append((meta["start"], meta["capture_id"]))
        for r in c13.iter_capture_rows(meta["dir"], wanted):
            qi.add(r["condition_id"], Q(c13.parse_iso(r["received_utc"]), c13.num(r.get("best_bid")), c13.num(r.get("best_ask")), c13.num(r.get("liquidity")), c13.parse_iso(r.get("end_date")), k,
                                        str(r.get("closed")).lower() == "true", str(r.get("binary")) == "1", str(r.get("market_id")), str(r.get("event_id") or ""), str(r.get("neg_risk_market_id") or "")))
        missing = wanted - set(qi.static)
        if missing:
            for s in c13.iter_sidecar_rows(meta["dir"], missing):
                qi.static[s["condition_id"]] = {"fee_type": s.get("fee_type", ""), "fee_category": s.get("fee_category", ""), "series_slugs": s.get("series_slugs", ""),
                                                "fee_rate": fee_rate_of(s.get("fee_schedule")), "clob_rewards": 1 if str(s.get("clob_rewards") or "") not in ("", "[]", "null") else 0}
    qi.finish()
    return qi


# =====================================================================================================================================================
# Exclusion keys (sealed historical sets with rows in a T window)
# =====================================================================================================================================================


class ScanUnfinished(NotNow):
    """The budgeted history scan stopped between files; the partial file makes the re-run resume (exit 0 / ``in_progress`` in the runner, never a partial analysis)."""


KEYS_PARTIAL_NAME = "t_exclusion_keys_partial.jsonl"


def _partial_records(path: Path, windows: list[tuple[float, float]]) -> list[dict]:
    """Complete lines of the partial scan file (a torn last line is dropped); a file written for other windows is discarded."""
    path = Path(path)
    if not path.exists():
        return []
    recs: list[dict] = []
    for line in path.read_text().split("\n"):
        if not line.strip():
            continue
        try:
            recs.append(json.loads(line))
        except ValueError:
            break
    head = recs[0] if recs and "windows" in recs[0] else None
    if head is None or [list(w) for w in head["windows"]] != [list(w) for w in windows]:
        path.unlink(missing_ok=True)
        return []
    return recs[1:]


def t_exclusion_keys(hist_root: Path, windows: list[tuple[float, float]], *, state_path: Path | None = None, budget_s: float | None = None, clock=time.monotonic) -> tuple[dict[str, str], dict]:
    """Keys (``market_id:x``, ``event_id:x``, ``condition_id:x``, ``neg_risk_market_id:x``) of every historical set (a run directory under ``hist_root`` other than the inert ones) that holds
    the id with a stored timestamp INSIDE a T window (section 1.3: nothing else). A file with no timestamp column contributes no key; it is counted (``files_without_timestamp``) so the loss is
    visible. Returns ``{key: source}`` and a report. Only id and timestamp columns are read (field-restricted accessor). Resumable by file: with ``state_path`` every finished file is appended
    to a partial file, and ``budget_s`` raises ``ScanUnfinished`` between files once the wall budget is spent (the next run resumes)."""
    keys: dict[str, str] = {}
    rep: dict = {"sources": {}, "absent": []}
    hr = Path(hist_root)
    if not hr.exists():
        return keys, {**rep, "history_root_missing": True}
    todo: list[tuple[str, Path, str]] = []
    for run in sorted(p for p in hr.iterdir() if p.is_dir()):
        if run.name in T_EXCL_SKIP_RUNS or run.name.startswith("h13_"):
            continue
        for f in sorted(f for f in run.rglob("*") if f.is_file() and (f.name.endswith(".csv") or f.name.endswith(".csv.gz"))):
            if f.name in c13.GUARDED_NAMES or "guarded" in f.name:
                continue
            todo.append((run.name, f, f.relative_to(hr).as_posix()))
    done: dict[str, dict] = {}
    if state_path is not None:
        sp = Path(state_path)
        valid = _partial_records(sp, windows)
        done = {r["file"]: r for r in valid}
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("".join(json.dumps(r) + "\n" for r in [{"windows": [list(w) for w in windows]}, *valid]))  # clean rewrite: a torn last line never stays in the middle
    t0 = clock()
    for run_name, f, rel in todo:
        if rel in done:
            continue
        if budget_s is not None and clock() - t0 >= budget_s:
            raise ScanUnfinished(f"T exclusion-key scan unfinished: {len(done)}/{len(todo)} files; resumable")
        hit_any: set[str] = set()
        nots = False
        for w in windows:
            in_win, _every, info = c13.read_id_ts_columns(f, w)
            hit_any |= in_win
            nots = bool(info["no_ts"])
        rec = {"run": run_name, "file": rel, "no_ts": nots, "keys": sorted(hit_any)}
        done[rel] = rec
        if state_path is not None:
            with Path(state_path).open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
    for run_name, _f, rel in todo:
        r = done[rel]
        src = rep["sources"].setdefault(run_name, {"files": 0, "keys_in_window": 0, "files_without_timestamp": 0})
        src["files"] += 1
        src["files_without_timestamp"] += int(bool(r["no_ts"]))
        src["keys_in_window"] += len(r["keys"])
        for k in r["keys"]:
            keys.setdefault(k, run_name)
    return keys, rep


def key_hit(keys: dict[str, str], cid: str, market_id: str, event_id: str, nrm: str) -> str | None:
    for k in (f"condition_id:{cid}", f"market_id:{market_id}", f"event_id:{event_id}", f"neg_risk_market_id:{nrm}"):
        if k in keys and k.split(":", 1)[1]:
            return keys[k]
    return None


# =====================================================================================================================================================
# Fills (features only; no mark)
# =====================================================================================================================================================


def size_band(cash: float) -> int:
    return int(sum(cash >= b for b in SIZE_BANDS))


def band_of(x: float, edges: tuple[float, ...]) -> int:
    return int(sum(x >= e for e in edges))


def make_fills(txs: list[dict], qi: QuoteIndex, keys: dict[str, str] | None = None) -> tuple[list[dict], dict]:
    """One row per transaction with its status: ``fill`` (touch-consistent), ``inside spread``, ``inconsistent with touch (drift)``, ``excluded: ...`` or ``dropped: key <source>``.
    Features only: the touch (b0, a0, age, liquidity, end), the capture before it (``prev_mid``), the stale-touch variant and the frozen class. No mark quote is read."""
    keys = keys or {}
    rows, counts = [], Counter()
    for i, t in enumerate(txs):
        cid = t["condition_id"]
        tq, pq = qi.touch(cid, t["ts"])
        st = qi.static.get(cid, {})
        ft = st.get("fee_type") or t["ctx_fee_type"]
        cls, under = lab.classify(t["title"], t["slug"], ft, st.get("fee_category", ""), st.get("series_slugs", ""), t["ctx_category"], has_sidecar=bool(st))
        series1 = lab.first_series_slug(st.get("series_slugs", ""))
        ev = (tq.event_id if tq and tq.event_id else "") or str(t.get("ctx_event_id") or "") or cid
        path_key = under if (cls == lab.PATH and under) else (series1 or f"event:{ev}")
        row = {"tx_id": i, "condition_id": cid, "market_id": tq.market_id if tq else str(t.get("ctx_market_id") or ""), "event_id": ev, "label": cls, "underlying": under or "", "path_key": path_key,
               "tau": t["ts"], "tau_last": t["ts_last"], "p_vwap": t["p_vwap"], "p_min": t["p_min"], "p_max": t["p_max"], "size": t["size"], "cash": t["cash"], "n_fills": t["n_fills"],
               "d": 0, "P": math.nan, "bid0": math.nan, "ask0": math.nan, "spread0": math.nan, "mid0": math.nan, "touch_recv": math.nan, "touch_age_s": math.nan, "touch_cap": -1, "liq": math.nan,
               "end_epoch": math.nan, "prev_mid": math.nan, "prev_recv": math.nan, "q_stale": math.nan, "d_stale": 0, "fee_rate": st.get("fee_rate", math.nan), "clob_rewards": st.get("clob_rewards", 0),
               "fee_type": ft, "block": c13.block6(t["ts"]), "day": c13.utc_day(t["ts"]), "neg_risk_market_id": tq.nrm if tq else ""}
        status = SCREEN_STATUS_FILL
        src = key_hit(keys, cid, row["market_id"], ev, row["neg_risk_market_id"]) if keys else None
        if src:
            status = f"{S_KEY} {src}"
        elif tq is None:
            status = S_NO_ROW
        else:
            b0, a0 = tq.bid, tq.ask
            age = t["ts"] - tq.recv
            row.update(bid0=b0, ask0=a0, spread0=a0 - b0 if two_sided(b0, a0) else math.nan, mid0=(a0 + b0) / 2 if two_sided(b0, a0) else math.nan, touch_recv=tq.recv, touch_age_s=age,
                       touch_cap=tq.cap, liq=tq.liq, end_epoch=tq.end)
            if pq is not None and two_sided(pq.bid, pq.ask):
                row.update(prev_mid=(pq.bid + pq.ask) / 2, prev_recv=pq.recv)
            if not two_sided(b0, a0):
                status = S_ONESIDED
            elif tq.closed or not tq.binary:
                status = S_NOTBINARY
            elif age > TOUCH_MAX_AGE_S:
                status = S_STALE
            elif not (MID_LO <= row["mid0"] <= MID_HI):
                status = S_MID
            elif row["spread0"] > SPREAD_MAX + 1e-9:
                status = S_SPREAD
            elif not (math.isfinite(tq.end) and tq.end >= t["ts"] + END_MARGIN_S):
                status = S_END
            elif cls == lab.UNKNOWN:
                status = S_UNKNOWN
            else:
                kind, d, P = classify_position(t["p_min"], t["p_max"], b0, a0)
                qs, ds = stale_variant(t["p_vwap"], b0, a0)
                row.update(q_stale=qs, d_stale=ds)
                if kind == "inside":
                    status = S_INSIDE
                elif kind == "inconsistent":
                    status = S_INCONSISTENT
                else:
                    row.update(d=d, P=P)
        row["status"] = status
        counts[status if not status.startswith(S_KEY) else S_KEY] += 1
        rows.append(row)
    return rows, dict(counts)


def first_per_side(rows: list[dict]) -> list[dict]:
    """The one-fill-per-side-per-pass collapse (reported variant): the earliest fill per (condition, touch capture, side)."""
    seen, out = set(), []
    for r in sorted((x for x in rows if x["status"] == SCREEN_STATUS_FILL), key=lambda x: x["tau"]):
        k = (r["condition_id"], r["touch_cap"], r["d"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def write_fills(path: Path, rows: list[dict]) -> None:
    c13.assert_clean_columns(FILL_COLUMNS)
    from . import history_backfill as hb  # noqa: PLC0415

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(hb._gz_csv_bytes(FILL_COLUMNS, ([_fmt(r[c]) for c in FILL_COLUMNS] for r in rows)))


def _fmt(x):
    return "" if isinstance(x, float) and math.isnan(x) else x


def read_fills(path: Path) -> list[dict]:
    """Fills table back to typed rows (numeric columns as floats / ints, NaN for blanks)."""
    out = []
    ints = {"tx_id", "d", "touch_cap", "block", "d_stale", "n_fills", "clob_rewards"}
    strs = {"condition_id", "market_id", "event_id", "status", "label", "underlying", "path_key", "fee_type", "day", "neg_risk_market_id"}
    for r in c13.read_csv_gz(Path(path)):
        row = {}
        for c in FILL_COLUMNS:
            v = r.get(c, "")
            if c in strs:
                row[c] = v
            elif c in ints:
                row[c] = int(float(v)) if v not in ("", None) else 0
            else:
                row[c] = c13.num(v) if v not in ("", None) else math.nan
        out.append(row)
    return out


# =====================================================================================================================================================
# Marks and the analysis dataset (screen / rep only)
# =====================================================================================================================================================


def worst_value(d: int, P: float) -> float:
    """``d (Y_adv - P)`` in cents with ``Y_adv`` the adverse extreme (1 if the maker sold YES, 0 if the maker bought)."""
    y = 1.0 if d == -1 else 0.0
    return 100.0 * d * (y - P)


def adverse_value(d: int, P: float, bid: float, ask: float) -> float:
    """Mark at the adverse touch: ``ask`` after a maker sell, ``bid`` after a maker buy; a missing / invalid adverse side falls back to the worst case."""
    adv = ask if d == -1 else bid
    if not (math.isfinite(adv) and 0.0 < adv < 1.0):
        return worst_value(d, P)
    return 100.0 * d * (adv - P)


def build_dataset(fills: list[dict], qi: QuoteIndex) -> dict:
    """Numpy arrays of the touch-consistent fills with their 2-4 h and 6-8 h marks (mark-mode index). Per horizon: ``m`` (mid mark-out in cents; NaN unless ok / wide), ``adv`` (adverse-touch
    mark: wide / one-sided -> adverse side or worst case; closed / absent -> worst case; gap / boundary -> NaN), ``wc`` (worst-case rule of T2: ok -> mid, wide -> adverse touch, closed -> worst
    case), ``st`` (status), ``realised`` (seconds)."""
    fs = [f for f in fills if f["status"] == SCREEN_STATUS_FILL]
    D: dict = {k: [] for k in ("tx_id", "cid", "label", "grp", "d", "P", "event", "pathkey", "pathblock", "block", "day", "cash", "size", "age", "spread", "mid0", "tte", "liq", "proxy", "fee_rate",
                               "stale_q", "stale_d", "tau", "rewards", "stale_share")}
    n_inc: Counter = Counter(f["event_id"] for f in fills if f["status"] == S_INCONSISTENT)
    n_fill: Counter = Counter(f["event_id"] for f in fills if f["status"] == SCREEN_STATUS_FILL)
    for h in MARK_H:
        for k in ("m", "adv", "wc", "realised", "bid", "ask"):
            D[f"{k}_{h}"] = []
        D[f"st_{h}"] = []
    for f in fs:
        D["tx_id"].append(f["tx_id"])
        D["cid"].append(f["condition_id"])
        D["label"].append(f["label"])
        D["grp"].append(lab.audit_group(f["label"]))
        D["d"].append(f["d"])
        D["P"].append(f["P"])
        D["event"].append(f["event_id"])
        D["pathkey"].append(f["path_key"])
        D["pathblock"].append(f"{f['path_key']}|{f['block']}")
        D["block"].append(f["block"])
        D["day"].append(f["day"])
        D["cash"].append(f["cash"])
        D["size"].append(f["size"])
        D["age"].append(f["touch_age_s"])
        D["spread"].append(f["spread0"])
        D["mid0"].append(f["mid0"])
        D["tte"].append(f["end_epoch"] - f["tau"])
        D["liq"].append(f["liq"])
        D["proxy"].append(100.0 * f["d"] * (f["mid0"] - f["prev_mid"]) if math.isfinite(f["prev_mid"]) else math.nan)
        D["fee_rate"].append(f["fee_rate"])
        D["stale_q"].append(f["q_stale"])
        D["stale_d"].append(f["d_stale"])
        D["tau"].append(f["tau"])
        D["rewards"].append(f["clob_rewards"])
        D["stale_share"].append(n_inc[f["event_id"]] / (n_inc[f["event_id"]] + n_fill[f["event_id"]]))
        for h, hs in MARK_H.items():
            mk = qi.mark_for(f, hs)
            st = mk["status"]
            m = 100.0 * f["d"] * ((mk["bid"] + mk["ask"]) / 2 - f["P"]) if st in ("ok", "wide") else math.nan
            if st in ("ok", "wide", "onesided"):
                adv = adverse_value(f["d"], f["P"], mk["bid"], mk["ask"])
            elif st == "closed_absent":
                adv = worst_value(f["d"], f["P"])
            else:
                adv = math.nan
            wc = m if st == "ok" else (adv if st in ("wide", "closed_absent") else math.nan)
            D[f"m_{h}"].append(m)
            D[f"adv_{h}"].append(adv)
            D[f"wc_{h}"].append(wc)
            D[f"realised_{h}"].append(mk["realised"])
            D[f"bid_{h}"].append(mk["bid"])
            D[f"ask_{h}"].append(mk["ask"])
            D[f"st_{h}"].append(st)
    out: dict = {}
    for k, v in D.items():
        if k in ("cid", "label", "grp", "event", "pathkey", "pathblock", "day"):
            out[k] = np.asarray(v, dtype=str)
        elif k.startswith("st_"):
            out[k] = np.asarray(v, dtype=object)
        else:
            out[k] = np.asarray(v, dtype=float)
    return out


# =====================================================================================================================================================
# Inference: one generic analyser (pseudo-values, max over ways, leave-one-day-out, top-5)
# =====================================================================================================================================================


def _ways(D: dict, idx: np.ndarray) -> tuple[dict, np.ndarray]:
    return {"event": D["event"][idx], "pathblock": D["pathblock"][idx]}, D["block"][idx]


def make_contrast(m: np.ndarray, low: np.ndarray, news: np.ndarray, w: np.ndarray | None = None):
    """make_v(idx) -> (pseudo-values, LOW - NEWS contrast) for the index set ``idx``; optional weights give weighted class means."""
    def f(idx: np.ndarray):
        if w is None:
            return c13.diff_pseudo(m[idx], low[idx], news[idx])
        x, a, b, ww = m[idx], low[idx], news[idx], w[idx]
        if a.sum() == 0 or b.sum() == 0:
            return np.full(len(x), math.nan), math.nan
        ma, mb = float(np.average(x[a], weights=ww[a])), float(np.average(x[b], weights=ww[b]))
        v = np.full(len(x), ma - mb)
        v[a] += len(x) * ww[a] / ww[a].sum() * (x[a] - ma)
        v[b] -= len(x) * ww[b] / ww[b].sum() * (x[b] - mb)
        return v, ma - mb
    return f


def make_mean(m: np.ndarray):
    def f(idx: np.ndarray):
        x = m[idx]
        return x, float(x.mean()) if len(x) else math.nan
    return f


def p_of(make_v, idx: np.ndarray, D: dict, *, alpha: float | None = None) -> dict:
    """The clustered result of one statistic on the rows ``idx``: estimate, p (max over the event and path-key x block ways + the 6 h block way under the CB10 rule), testable."""
    if len(idx) < 2:
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False, "block_rule_holds": False}
    v, est = make_v(idx)
    if not math.isfinite(est) or np.isnan(v).any():
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False, "block_rule_holds": False}
    ways, block = _ways(D, idx)
    est_fn = lambda keep: make_v(idx[keep])[1]  # noqa: E731
    r = c13.cluster_p_block(v, ways, block, est_fn, alpha=alpha)
    return {"n": int(len(idx)), "est": float(est), "p": float(r["p"]), "testable": bool(r["testable"]), "block_rule_holds": bool(r.get("week_rule_holds", True)), "ways": r.get("ways"),
            "block_way": r.get("week")}


def analyse(make_v, idx: np.ndarray, D: dict, floor: float, *, loo: bool = True, top5: bool = True, alpha: float | None = None) -> dict:
    """Primary result plus the binding checks of T1 / T2: p < 0.01 and the floor; leave-one-day-out (every sample keeps the sign and p < 0.05); top-5 drops by event, by path key x 6 h block and
    by 6 h block (p < 0.01 and the floor hold)."""
    base = p_of(make_v, idx, D, alpha=alpha)
    out = {**base, "floor": floor, "floor_ok": bool(math.isfinite(base["est"]) and base["est"] >= floor), "p_ok": bool(base["testable"] and base["p"] < c13.GATE_P)}
    if not base["testable"] or not math.isfinite(base["est"]):
        out.update(loo_day={"holds": False, "n_groups": 0}, top5={"event": False, "pathblock": False, "block": False})
        return out
    v, _ = make_v(idx)
    if loo:
        days = D["day"][idx]
        def stat(keep):
            return make_v(idx[keep])
        def pfn(_v, keep):
            return p_of(make_v, idx[keep], D, alpha=c13.LOO_DAY_P)["p"]
        out["loo_day"] = c13.leave_one_out_p(days, stat, pfn, sign=1.0, p_max=c13.LOO_DAY_P)
    if top5:
        t5 = {}
        for name, cl in (("event", D["event"][idx]), ("pathblock", D["pathblock"][idx]), ("block", D["block"][idx])):  # every declared way (section 2.6 ii)
            keep = c13.top_k_drop_mask(v, cl, c13.TOP_DROP)
            r = p_of(make_v, idx[keep], D, alpha=c13.GATE_P)
            t5[name] = bool(r["testable"] and r["p"] < c13.GATE_P and r["est"] >= floor)
        out["top5"] = t5
    return out


def est_only(make_v, idx: np.ndarray) -> float:
    return make_v(idx)[1] if len(idx) else math.nan


def bands_of(D: dict) -> dict:
    return {"spread": np.array([band_of(x, SPREAD_BANDS) for x in D["spread"]]), "mid": np.array([band_of(x, MID_BANDS) for x in D["mid0"]]),
            "tte": np.array([band_of(x, TTE_BANDS_S) for x in D["tte"]]), "size": np.array([size_band(x) for x in D["cash"]]), "age": np.array([band_of(x, AGE_BANDS_S) for x in D["age"]])}


def attribution(D: dict, idx: np.ndarray, y: np.ndarray, d_hat: float) -> dict:
    """OLS of the mark-out on the LOW indicator (base NEWS) plus spread, mid, time-to-end, size and touch-age band dummies, log liquidity and the event-level "inconsistent with touch" share
    (the declared staleness control). Credit "class effect" only if the LOW
    coefficient keeps at least half of ``d_hat``; otherwise "composition, not class"."""
    b = bands_of(D)
    cols = [(D["grp"][idx] == "LOW").astype(float)]
    names = ["LOW"]
    for key in ("spread", "mid", "tte", "size", "age"):
        arr = b[key][idx]
        for lv in sorted(set(arr.tolist()))[1:]:
            cols.append((arr == lv).astype(float))
            names.append(f"{key}{lv}")
    cols.append(np.log(np.maximum(D["liq"][idx], 1.0)))
    names.append("log_liq")
    cols.append(D["stale_share"][idx])  # the event-level share of touch-eligible transactions "inconsistent with touch" (the declared staleness control)
    names.append("stale_share")
    X = np.column_stack(cols)
    ok = np.isfinite(y[idx]) & np.isfinite(X).all(axis=1)
    if ok.sum() < X.shape[1] + 5:
        return {"label": "composition, not class", "coef_low": math.nan, "reason": "too few rows"}
    beta = c13.ols_coef(y[idx][ok], X[ok])
    coef = float(beta[1])
    return {"coef_low": coef, "d_hat": d_hat, "kept_share": coef / d_hat if d_hat else math.nan, "label": "class effect" if (d_hat > 0 and coef >= d_hat / 2) else "composition, not class", "n": int(ok.sum())}


def composition_placebo(D: dict, idx: np.ndarray, m: np.ndarray, *, n_draws: int = c13.PLACEBO_DRAWS, seed: int = c13.PLACEBO_SEEDS["T1_composition"]) -> dict:
    """Binding T1 composition placebo: the event-level class group (LOW / NEWS by the event's majority) is permuted across events within strata of (touch spread band x touch mid band x
    time-to-end band); 200 draws; a draw advances on p < 0.01 alone (floors off). Advance rate must be <= 1.5%."""
    b = bands_of(D)
    ev = D["event"][idx]
    grp = D["grp"][idx]
    first: dict[str, int] = {}
    cnt: dict[str, list[int]] = {}
    for j, e in enumerate(ev):
        first.setdefault(e, j)
        cnt.setdefault(e, [0, 0])[0 if grp[j] == "LOW" else 1] += 1
    events = sorted(first)
    egrp = {e: ("LOW" if cnt[e][0] >= cnt[e][1] else "NEWS") for e in events}
    strat = {e: (int(b["spread"][idx][first[e]]), int(b["mid"][idx][first[e]]), int(b["tte"][idx][first[e]])) for e in events}
    by_stratum: dict[tuple, list[str]] = {}
    for e in events:
        by_stratum.setdefault(strat[e], []).append(e)
    rng = np.random.default_rng(seed)
    ps = []
    for _ in range(n_draws):
        perm = dict(egrp)
        for evs in by_stratum.values():
            labs = [egrp[e] for e in evs]
            rng.shuffle(labs)
            perm.update(dict(zip(evs, labs, strict=True)))
        low = np.array([perm.get(e) == "LOW" for e in D["event"]])  # events outside the T1 index (SPORTS-FEED, SCHEDULED-EVENT, unmarked fills) belong to neither arm
        news = np.array([perm.get(e) == "NEWS" for e in D["event"]])
        mk = make_contrast(m, low, news)
        r = p_of(mk, idx, D, alpha=c13.GATE_P)
        ps.append(r["p"] if r["testable"] else None)
    return {**c13.placebo_advance_rate(ps), "note": "T1 composition placebo (event-level class permutation within spread x mid x time-to-end strata)", "seed": seed}


def signflip_placebo(D: dict, idx: np.ndarray, m: np.ndarray, *, n_draws: int = c13.PLACEBO_DRAWS, seed: int = c13.PLACEBO_SEEDS["T2_signflip"]) -> dict:
    """Binding T2 sign-flip calibration: one coin per event flips ``d`` (the mark-out changes sign); 200 draws; a draw advances on p < 0.01 alone."""
    def draw(signs: np.ndarray):
        mm = m.copy()
        mm[idx] = mm[idx] * signs[idx]
        r = p_of(make_mean(mm), idx, D, alpha=c13.GATE_P)
        return r["p"] if r["testable"] else None
    ev = D["event"]
    uniq, codes = np.unique(ev, return_inverse=True)
    rng = np.random.default_rng(seed)
    ps = []
    for _ in range(n_draws):
        coin = rng.integers(0, 2, len(uniq)) * 2 - 1
        ps.append(draw(coin[codes].astype(float)))
    return {**c13.placebo_advance_rate(ps), "note": "T2 sign-flip calibration (one coin per event)", "seed": seed}


# =====================================================================================================================================================
# Gates
# =====================================================================================================================================================


def gate_gt(fills: list[dict]) -> dict:
    """GT: >= 500 LOW fills in >= 60 events and >= 500 NEWS fills in >= 60 events (touch-consistent fills)."""
    out = {}
    for g in ("LOW", "NEWS"):
        fs = [f for f in fills if f["status"] == SCREEN_STATUS_FILL and lab.audit_group(f["label"]) == g]
        out[g] = {"fills": len(fs), "events": len({f["event_id"] for f in fs})}
    out["t1_pass"] = all(out[g]["fills"] >= GT_MIN["fills"] and out[g]["events"] >= GT_MIN["events"] for g in ("LOW", "NEWS"))
    out["t2_pass"] = out["LOW"]["fills"] >= GT_MIN["fills"] and out["LOW"]["events"] >= GT_MIN["events"]
    return out


def gate_gl(audit_path: Path | None, labeller_sha: str) -> dict:
    """GL: the committed blind-audit file (``labeller_audit.json``): ``gl_pass`` true and recorded for THIS labeller sha256. A second failed audit -> T1 and T2 not testable (labeller)."""
    if audit_path is None or not Path(audit_path).exists():
        return {"pass": False, "reason": "audit file missing"}
    a = json.loads(Path(audit_path).read_text())
    ok = bool(a.get("gl_pass")) and a.get("labeller_sha256") == labeller_sha
    return {"pass": ok, "audit_rounds": a.get("rounds"), "labeller_sha_matches": a.get("labeller_sha256") == labeller_sha, "reason": None if ok else "gl_pass false or labeller sha differs"}


def gate_gtp(fills: list[dict]) -> dict:
    """GTP on the pre-fill proxy outcome (the move of the capture mid from the capture before the touch capture to the touch capture, signed by ``d``): each test's own estimator and ways; ONLY the
    clustered SEs (max over ways) and MDEs are returned, never a proxy point estimate. T1 is "not run (power)" if MDE > 1.0c, T2 if MDE > 0.5c."""
    fs = [f for f in fills if f["status"] == SCREEN_STATUS_FILL and math.isfinite(f["prev_mid"]) and lab.audit_group(f["label"]) in ("LOW", "NEWS")]
    if len(fs) < 4:
        return {"T1": {"se": math.nan, "mde": math.nan, "pass": False}, "T2": {"se": math.nan, "mde": math.nan, "pass": False}, "n": len(fs)}
    y = np.array([100.0 * f["d"] * (f["mid0"] - f["prev_mid"]) for f in fs])
    grp = np.array([lab.audit_group(f["label"]) for f in fs])
    ev = np.array([f["event_id"] for f in fs])
    pb = np.array([f"{f['path_key']}|{f['block']}" for f in fs])
    bl = np.array([str(f["block"]) for f in fs])
    low, news = grp == "LOW", grp == "NEWS"
    v1, _ = c13.diff_pseudo(y, low, news)
    se1 = c13.max_se_over_ways(v1, {"event": ev, "pathblock": pb, "block": bl})
    v2 = y[low]
    se2 = c13.max_se_over_ways(v2, {"event": ev[low], "pathblock": pb[low], "block": bl[low]})
    out = {"n": len(fs)}
    for tid, se in (("T1", se1), ("T2", se2)):
        m_ = c13.mde(se) if math.isfinite(se) else math.nan
        out[tid] = {"se": se, "mde": m_, "pass": bool(math.isfinite(m_) and m_ <= GTP_MDE_MAX[tid])}
    return out


def gate_gti(fills: list[dict], D: dict, txs: list[dict]) -> dict:
    """GTI (cadence informativeness): fills with a later monitor transaction in the same market in [tau + 2 h - 30 min, tau + 2 h + 30 min]; the print-based move is ``d (VWAP_later - P)``
    from the FILL PRINT P (round 1 item 1), the mid move is the 2-4 h mark-out. Among pairs with both moves nonzero the signs must agree in > 70%. n < 200 -> "not evaluable"."""
    by_cid: dict[str, list[dict]] = {}
    for t in txs:
        by_cid.setdefault(t["condition_id"], []).append(t)
    agree = n = 0
    for j in range(len(D["tx_id"])):
        m = D["m_2-4h"][j]
        if not math.isfinite(m) or m == 0:
            continue
        lo, hi = D["tau"][j] + 7200.0 - GTI_WINDOW_S, D["tau"][j] + 7200.0 + GTI_WINDOW_S
        later = [t for t in by_cid.get(D["cid"][j], []) if lo <= t["ts"] <= hi]
        if not later:
            continue
        sz = sum(t["size"] for t in later)
        vw = sum(t["p_vwap"] * t["size"] for t in later) / sz
        pm = D["d"][j] * (vw - D["P"][j])
        if pm == 0:
            continue
        n += 1
        agree += int(np.sign(pm) == np.sign(m))
    share = agree / n if n else math.nan
    ev = n >= GTI_MIN_PAIRS
    return {"pairs": n, "agree": agree, "agree_share": share, "evaluable": ev, "pass": bool(ev and share > GTI_AGREE), "not_evaluable_label": None if ev else LABEL_CADENCE}


# =====================================================================================================================================================
# T1 / T2 / T3
# =====================================================================================================================================================


def _valid(D: dict, key: str) -> np.ndarray:
    return np.isfinite(D[key])


def t1_test(D: dict, *, placebo: bool = True, n_draws: int = c13.PLACEBO_DRAWS, rep: bool = False) -> dict:
    """T1 (class contrast): ``D = mean M(LOW) - mean M(NEWS)`` at the 2-4 h mark, one-sided > 0, floor 0.5c. Binding: pre-fill placebo (p >= 0.01), composition placebo (advance rate <= 1.5%),
    robustness (touch age <= 20 min, 6-8 h mark, adverse-touch mark, tx < $10k, each side, event-weighted, top-5, leave-one-day-out p < 0.05) and the attribution label."""
    low, news = D["grp"] == "LOW", D["grp"] == "NEWS"
    m = D["m_2-4h"]
    idx = np.where((low | news) & _valid(D, "m_2-4h"))[0]
    av = c13.availability(len(idx), int((low | news).sum()))
    if not av["ok"]:
        return {**not_testable(c13.AVAILABILITY_LABEL), "availability": av}
    mk = make_contrast(m, low, news)
    res = analyse(mk, idx, D, T1_FLOOR)
    res["availability"] = av
    res["classes"] = {"LOW": int((low[idx]).sum()), "NEWS": int((news[idx]).sum())}
    if not res["testable"]:
        res.update(advance=False, verdict="not testable (population / clusters)")
        return res
    res["attribution"] = attribution(D, idx, m, res["est"])
    # binding placebos
    pf = np.where((low | news) & np.isfinite(D["proxy"]))[0]
    pr = p_of(make_contrast(D["proxy"], low, news), pf, D, alpha=c13.GATE_P)
    res["prefill_placebo"] = {"p": pr["p"], "holds": bool((not pr["testable"]) or pr["p"] >= c13.GATE_P), "n": int(len(pf))}
    res["composition_placebo"] = composition_placebo(D, idx, m, n_draws=n_draws) if placebo else {"holds": True, "skipped": True}
    # robustness (the sign of the contrast)
    rob = {}
    young = D["age"] <= TOUCH_AGE_ROBUST_S
    rob["age_le_20m"] = est_only(mk, idx[young[idx]]) > 0
    i68 = np.where((low | news) & _valid(D, "m_6-8h"))[0]
    rob["mark_6_8h"] = est_only(make_contrast(D["m_6-8h"], low, news), i68) > 0
    ia = np.where((low | news) & _valid(D, "adv_2-4h"))[0]
    rob["adverse_touch_mark"] = est_only(make_contrast(D["adv_2-4h"], low, news), ia) > 0
    rob["tx_lt_10k"] = est_only(mk, idx[D["cash"][idx] < BIG_TX_USD]) > 0
    rob["side_maker_sells"] = est_only(mk, idx[D["d"][idx] == -1]) > 0
    rob["side_maker_buys"] = est_only(mk, idx[D["d"][idx] == 1]) > 0
    w = np.zeros(len(m))
    cnt = Counter(zip(D["event"][idx], D["grp"][idx], strict=True))
    for j in idx:
        w[j] = 1.0 / cnt[(D["event"][j], D["grp"][j])]
    rob["event_weighted"] = est_only(make_contrast(m, low, news, w), idx) > 0
    rob["staleness_control_attribution_sign"] = bool(math.isfinite(res["attribution"].get("coef_low", math.nan)) and res["attribution"]["coef_low"] > 0)  # attribution includes the stale_share regressor
    res["robustness"] = rob
    res["staleness"] = {"note": "the attribution regression carries the event-level 'inconsistent with touch' share; per-class shares are reported by the census and screen (fills table)"}
    res["robust_ok"] = bool(all(rob.values()) and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["checks_ok"] = bool(res["floor_ok"] and res["block_rule_holds"] and res["prefill_placebo"]["holds"] and res["composition_placebo"].get("holds", False) and res["robust_ok"])  # every binding check but the primary p gate
    res["advance"] = bool(res["p_ok"] and res["checks_ok"])
    res["verdict"] = ("advance" if res["advance"] else "no advance") + (f"; {res['attribution']['label']}" if res["advance"] else "")
    res["rep"] = rep
    return res


def t2_test(D: dict, *, placebo: bool = True, n_draws: int = c13.PLACEBO_DRAWS, rep: bool = False) -> dict:
    """T2 (maker sign in LOW): ``mean M(LOW)`` at the 2-4 h mark, one-sided > 0, floor +0.25c (upper bound, free exit). Binding: sign-flip calibration, pre-fill placebo, robustness (age <=
    20 min, 6-8 h keeps sign and half, each LOW component with >= 200 fills keeps sign, the worst case keeps p < 0.01 and the floor, tx < $10k, top-5, leave-one-day-out p < 0.05)."""
    low = D["grp"] == "LOW"
    m = D["m_2-4h"]
    idx = np.where(low & _valid(D, "m_2-4h"))[0]
    av = c13.availability(len(idx), int(low.sum()))
    if not av["ok"]:
        return {**not_testable(c13.AVAILABILITY_LABEL), "availability": av}
    mk = make_mean(m)
    res = analyse(mk, idx, D, T2_FLOOR)
    res["availability"] = av
    if not res["testable"]:
        res.update(advance=False, verdict="not testable (population / clusters)")
        return res
    pf = np.where(low & np.isfinite(D["proxy"]))[0]
    pr = p_of(make_mean(D["proxy"]), pf, D, alpha=c13.GATE_P)
    res["prefill_placebo"] = {"p": pr["p"], "holds": bool((not pr["testable"]) or pr["p"] >= c13.GATE_P), "n": int(len(pf))}
    res["signflip_placebo"] = signflip_placebo(D, idx, m, n_draws=n_draws) if placebo else {"holds": True, "skipped": True}
    rob = {}
    young = D["age"] <= TOUCH_AGE_ROBUST_S
    rob["age_le_20m"] = est_only(mk, idx[young[idx]]) > 0
    i68 = np.where(low & _valid(D, "m_6-8h"))[0]
    e68 = est_only(make_mean(D["m_6-8h"]), i68)
    rob["mark_6_8h_sign_and_half"] = bool(math.isfinite(e68) and e68 > 0 and e68 >= res["est"] / 2)
    comp = {}
    for c in lab.LOW_CLASSES:
        ic = idx[D["label"][idx] == c]
        if len(ic) >= COMPONENT_MIN_FILLS:
            comp[c] = est_only(mk, ic) > 0
    rob["components_keep_sign"] = bool(all(comp.values()))
    rob["tx_lt_10k"] = est_only(mk, idx[D["cash"][idx] < BIG_TX_USD]) > 0
    iw = np.where(low & np.isfinite(D["wc_2-4h"]))[0]
    wc = analyse(make_mean(D["wc_2-4h"]), iw, D, T2_FLOOR, loo=False, top5=False, alpha=c13.GATE_P)
    rob["worst_case_p_and_floor"] = bool(wc["p_ok"] and wc["floor_ok"])
    res["components"] = comp
    res["worst_case"] = {k: wc.get(k) for k in ("est", "p", "n", "floor_ok", "p_ok")}
    res["robustness"] = rob
    res["robust_ok"] = bool(all(rob.values()) and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["checks_ok"] = bool(res["floor_ok"] and res["block_rule_holds"] and res["prefill_placebo"]["holds"] and res["signflip_placebo"].get("holds", False) and res["robust_ok"])
    res["advance"] = bool(res["p_ok"] and res["checks_ok"])
    res["verdict"] = "advance" if res["advance"] else "no advance"
    res["label"] = LABEL_T2
    res["rep"] = rep
    return res


def t3_values(D: dict, idx: np.ndarray, extra_exit: float = 0.0) -> np.ndarray:
    """``net = 100 (d (x_exit - P) - r x_exit (1 - x_exit)) - extra`` per filled share (cents): the maker entry at the recorded print P, a taker exit at the adverse touch of the 2-4 h mark capture
    (``ask`` after a maker sell, ``bid`` after a maker buy), taker fee ``r x (1 - x)`` with ``r`` the sidecar fee rate (unknown -> 0.07)."""
    out = np.full(len(idx), math.nan)
    for k, j in enumerate(idx):
        x = D["ask_2-4h"][j] if D["d"][j] == -1 else D["bid_2-4h"][j]
        if not (math.isfinite(x) and 0.0 < x < 1.0):
            continue
        r = D["fee_rate"][j] if math.isfinite(D["fee_rate"][j]) else T3_DEFAULT_FEE
        out[k] = 100.0 * (D["d"][j] * (x - D["P"][j]) - r * x * (1.0 - x)) - extra_exit
    return out


def t3_test(D: dict) -> dict:
    """T3 (economic at recorded prints and touches), triggered by T2 and needing the pooled GTI PASS: LOW fills, size <= 100 shares, one-sided net > 0, floor +0.5c, robustness +0.5c on the exit."""
    low = D["grp"] == "LOW"
    idx = np.where(low & _valid(D, "m_2-4h"))[0]
    net = np.full(len(D["tx_id"]), math.nan)
    vals = t3_values(D, idx)
    net[idx] = vals
    ok = np.where(np.isfinite(net))[0]
    av = c13.availability(len(ok), int(low.sum()))  # eligible = every touch-consistent LOW fill; available = a usable adverse exit quote
    if not av["ok"]:
        return {**not_testable(c13.AVAILABILITY_LABEL), "availability": av}
    res = analyse(make_mean(net), ok, D, T3_FLOOR, loo=True, top5=True)
    res["availability"] = av
    # design 2.2 "size <= 100 shares": the MODELLED maker position is min(print size, 100) shares (the print is >= $1k, i.e. normally > 100 shares, so a size filter would empty the test); the
    # net is per filled share, so the clip does not change the statistic; it is recorded, with the share of fills clipped, and the exit depth stays unknown
    sizes = np.asarray(D["size"], dtype=float)[ok]
    res["position"] = {"max_shares": T3_MAX_SIZE, "n_clipped": int((sizes > T3_MAX_SIZE).sum()), "n": int(len(ok)), "mean_position_shares": float(np.minimum(sizes, T3_MAX_SIZE).mean()),
                       "note": "per-filled-share net; position = min(print size, max_shares); exit depth unknown (displayed depth is not captured)"}
    if not res["testable"]:
        res.update(advance=False, verdict="not testable (population / clusters)")
        return res
    net2 = np.full(len(D["tx_id"]), math.nan)
    net2[idx] = t3_values(D, idx, T3_EXIT_ROBUST)
    rob = bool(est_only(make_mean(net2), np.where(np.isfinite(net2))[0]) > 0)
    res["robustness"] = {"exit_plus_0_5c_net_positive": rob}
    res["checks_ok"] = bool(res["floor_ok"] and res["block_rule_holds"] and rob and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["advance"] = bool(res["p_ok"] and res["checks_ok"])
    res["verdict"] = "advance" if res["advance"] else "no advance"
    res["label"] = LABEL_T3
    return res


def reported_variants(D: dict, fills: list[dict]) -> dict:
    """Uncounted readings: per-class mean mark-outs at 2-4 h and 6-8 h (incl. SPORTS-FEED and SCHEDULED-EVENT), realised horizons, size-weighted means, reward-band split, the per-class share of
    transactions inconsistent with the touch, the stale-touch variant (paper quote at the touch itself) and the one-per-side collapse count."""
    out: dict = {"per_class": {}, "inconsistent_share": {}}
    for c in lab.CLASSES:
        sel = D["label"] == c
        e = {"n": int(sel.sum())}
        for h in MARK_H:
            v = D[f"m_{h}"][sel]
            v = v[np.isfinite(v)]
            e[h] = {"n": int(len(v)), "mean_cents": float(v.mean()) if len(v) else None}
            rl = D[f"realised_{h}"][sel]
            rl = rl[np.isfinite(rl)]
            e[h]["realised_median_s"] = float(np.median(rl)) if len(rl) else None
        w = D["size"][sel & np.isfinite(D["m_2-4h"])]
        v = D["m_2-4h"][sel & np.isfinite(D["m_2-4h"])]
        e["size_weighted_2_4h"] = float(np.average(v, weights=w)) if len(v) and w.sum() > 0 else None
        out["per_class"][c] = e
        cons = [f for f in fills if f["label"] == c and f["status"] in (SCREEN_STATUS_FILL, S_INCONSISTENT)]
        out["inconsistent_share"][c] = (sum(1 for f in cons if f["status"] == S_INCONSISTENT) / len(cons)) if cons else None
    rw = D["rewards"] == 1
    for nm, sel in (("rewards", rw), ("no_rewards", ~rw)):
        v = D["m_2-4h"][sel & np.isfinite(D["m_2-4h"])]
        out[f"reward_band_{nm}"] = {"n": int(len(v)), "mean_cents": float(v.mean()) if len(v) else None}
    st = np.isfinite(D["stale_q"]) & np.isfinite(D["m_2-4h"])
    mids = np.array([(D["bid_2-4h"][j] + D["ask_2-4h"][j]) / 2 for j in range(len(D["tx_id"]))]) if len(D["tx_id"]) else np.array([])
    if len(mids):
        ms = 100.0 * D["stale_d"] * (mids - D["stale_q"])
        for g in ("LOW", "NEWS"):
            sel = st & (D["grp"] == g) & np.isfinite(ms)
            out.setdefault("stale_touch_variant", {})[g] = {"n": int(sel.sum()), "mean_cents": float(ms[sel].mean()) if sel.any() else None}
    out["one_per_side_fills"] = len(first_per_side(fills))
    out["mark_status_counts"] = {h: {c: dict(Counter(D[f"st_{h}"][D["label"] == c])) for c in lab.CLASSES if (D["label"] == c).any()} for h in MARK_H}
    out["boundary_note"] = "status 'boundary' = excluded (J4-R boundary) for SCREEN, excluded (window end) for HOLDOUT"
    return out


# =====================================================================================================================================================
# Census, screen, holdout, rep (orchestration on files)
# =====================================================================================================================================================


def trade_files(trades_dir: Path, split: str, pin: dict) -> list[Path]:
    """The ``trades-YYYYMMDD.jsonl`` files (daily by RECEIPT, prints arrive about 8 min late) that can hold prints with venue time in the split's window. SCREEN reads UTC days 10-12..10-15 (the J4-R
    window starts 10-16); HOLDOUT reads the days from the J4-R end through 10-26 INCLUDING the next receipt day after the window end (``trades-20261026.jsonl`` holds the late prints of
    10-25 23:5x); the venue-time filter of ``iter_prints`` keeps only ``ts`` inside the window."""
    lo, hi = c13.split_bounds(split, pin)
    d0, d1 = datetime.fromtimestamp(lo, UTC).date(), datetime.fromtimestamp(hi - 1, UTC).date()
    if split == "holdout":
        d1 = datetime.fromordinal(d1.toordinal() + 1).date()
    files = []
    d = d0
    while d <= d1:
        p = Path(trades_dir) / f"trades-{d:%Y%m%d}.jsonl"
        if p.exists():
            files.append(p)
        d = datetime.fromordinal(d.toordinal() + 1).date()
    return files


def screen_prints(trades_dir: Path, split: str, pin: dict) -> tuple[list[dict], dict]:
    """The split's whitelisted monitor prints (venue ``ts`` inside the window). Window checks: ``check_window``."""
    lo, hi = c13.split_bounds(split, pin)
    c13.check_window(split, lo, hi, pin)
    prints = []
    files = trade_files(trades_dir, split, pin)
    for p in files:
        prints.extend(c13.iter_prints(p, lo, hi))
    return prints, {"n_prints": len(prints), "n_files": len(files), "window": [c13.iso(lo), c13.iso(hi)]}


def screen_transactions(trades_dir: Path, split: str, pin: dict, *, days: list[str] | None = None) -> tuple[list[dict], dict]:
    """Aggregate the split's monitor prints into transactions (see ``trade_files`` for the files read)."""
    prints, pinfo = screen_prints(trades_dir, split, pin)
    txs, info = build_transactions(prints)
    return txs, {**info, **pinfo}


def build_frame(trades_dir: Path, snap_root: Path, hist_root: Path, split: str, pin: dict, *, state_dir: Path | None = None, budget_s: float | None = None) -> dict:
    """Transactions, the touch-mode quote index (NO mark accessor), exclusion keys and the fill table of one split, features only. ``state_dir``/``budget_s`` make the history key scan
    resumable and budgeted (``ScanUnfinished``)."""
    txs, tinfo = screen_transactions(trades_dir, split, pin)
    caps = c13.list_captures(snap_root, split, pin)
    wanted = {t["condition_id"] for t in txs}
    qi = load_quote_index(caps, wanted, "touch", split, pin)
    lo, hi = c13.split_bounds(split, pin)
    kstate = (Path(state_dir) / KEYS_PARTIAL_NAME) if state_dir is not None else None
    keys, krep = t_exclusion_keys(hist_root, [(lo, hi)], state_path=kstate, budget_s=budget_s)
    fills, counts = make_fills(txs, qi, keys)
    return {"txs": txs, "tinfo": tinfo, "caps": caps, "qi": qi, "keys": keys, "krep": krep, "fills": fills, "counts": counts, "wanted": wanted, "keys_state": kstate}


def market_labels(txs: list[dict], qi: QuoteIndex) -> dict[str, list]:
    """``{condition_id: [condition_id, class, underlying, fee_type, fee_category, series_slug, title, slug]}``: the frozen labeller on every market of the transactions."""
    labels: dict[str, list] = {}
    for t in txs:
        if t["condition_id"] in labels:
            continue
        st = qi.static.get(t["condition_id"], {})
        ft = st.get("fee_type") or t["ctx_fee_type"]
        cls, under = lab.classify(t["title"], t["slug"], ft, st.get("fee_category", ""), st.get("series_slugs", ""), t["ctx_category"], has_sidecar=bool(st))
        labels[t["condition_id"]] = [t["condition_id"], cls, under or "", ft, st.get("fee_category", ""), lab.first_series_slug(st.get("series_slugs", "")), t["title"], t["slug"]]
    return labels


def write_frame_files(out_dir: Path, B: dict, fills: list[dict] | None = None) -> list[Path]:
    from . import history_backfill as hb  # noqa: PLC0415

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_fills(out_dir / FILLS_NAME, fills if fills is not None else B["fills"])
    (out_dir / LABELS_NAME).write_bytes(hb._gz_csv_bytes(LABEL_COLUMNS, sorted(market_labels(B["txs"], B["qi"]).values())))
    (out_dir / EXCL_NAME).write_bytes(hb._gz_csv_bytes(["key", "source"], sorted([k, s] for k, s in B["keys"].items())))
    if B.get("keys_state") is not None:
        Path(B["keys_state"]).unlink(missing_ok=True)  # the scan is complete and its keys are written
    return [out_dir / FILLS_NAME, out_dir / LABELS_NAME, out_dir / EXCL_NAME]


def thin_label(fills: list[dict]) -> str | None:
    """Section 1.3: if more than 30% of the SCREEN LOW fills OR more than 30% of the NEWS fills are dropped by the exclusion keys, T lines carry "population thinned by exclusions". The share is
    computed per class (never pooled over LOW + NEWS) among that class's transactions that had a quote row."""
    for g in ("LOW", "NEWS"):
        rows = [f for f in fills if lab.audit_group(f["label"]) == g and f["status"] != S_NO_ROW]
        if rows and sum(1 for f in rows if f["status"].startswith(S_KEY)) / len(rows) > EXCL_THIN_SHARE:
            return LABEL_THIN
    return None


def frame_report(B: dict, split: str, *, labeller_sha: str, audit_path: Path | None) -> dict:
    fills = B["fills"]
    return {"split": split, "transactions": B["tinfo"], "captures_used": len(B["caps"]), "status_counts": B["counts"], "key_drop_report": B["krep"], "population_label": thin_label(fills),
            "labeller_sha256": labeller_sha, "gl": gate_gl(audit_path, labeller_sha), "n_fills": sum(1 for f in fills if f["status"] == SCREEN_STATUS_FILL)}


def frame_t(trades_dir: Path, snap_root: Path, hist_root: Path, split: str, pin: dict, *, labeller_sha: str, audit_path: Path | None, out_dir: Path, budget_s: float | None = None) -> tuple[dict, list[Path]]:
    """q0271 (SCREEN): exclusion keys (resumable, budgeted), the fill table with the frozen labeller, features only, no mark quote read. Returns (report, output files)."""
    B = build_frame(trades_dir, snap_root, hist_root, split, pin, state_dir=out_dir, budget_s=budget_s)
    files = write_frame_files(out_dir, B)
    return frame_report(B, split, labeller_sha=labeller_sha, audit_path=audit_path), files


def census_t(fills: list[dict], *, labeller_sha: str, audit_path: Path | None, window_label: str = "SCREEN") -> dict:
    """q0272, counts only: transactions by day / label / fee category / touch position by class; key drops; one-per-side count; fills by class, event, path key x block, block, day; spread / mid /
    time-to-end bands; excluded units by label; gates GT, GL, GTP (clustered SEs only, no proxy point estimate); MDEs."""
    fs = [f for f in fills if f["status"] == SCREEN_STATUS_FILL]
    census: dict = {"window": window_label, "n_transactions": len(fills), "n_fills": len(fs), "status_counts": dict(Counter(f["status"] if not f["status"].startswith(S_KEY) else S_KEY for f in fills)),
                    "key_drops_by_source": dict(Counter(f["status"][len(S_KEY):].strip() for f in fills if f["status"].startswith(S_KEY)))}
    census["by_day_label"] = {d: dict(Counter(f["label"] for f in fills if f["day"] == d)) for d in sorted({f["day"] for f in fills})}
    census["by_fee_type"] = dict(Counter(f["fee_type"] for f in fills))
    census["position_by_class"] = {c: dict(Counter(f["status"] for f in fills if f["label"] == c and (f["status"] in (SCREEN_STATUS_FILL, S_INSIDE, S_INCONSISTENT)))) for c in lab.CLASSES}
    age_band = lambda a: "<=20m" if a <= 1200 else ("20-40m" if a <= 2400 else "40-60m")  # noqa: E731
    census["touch_age_by_class"] = {c: dict(Counter(age_band(f["touch_age_s"]) for f in fs if f["label"] == c)) for c in lab.CLASSES}
    census["one_per_side_fills"] = len(first_per_side(fills))
    for g in ("LOW", "NEWS"):
        sel = [f for f in fs if lab.audit_group(f["label"]) == g]
        census.setdefault("fills_by_group", {})[g] = {"fills": len(sel), "events": len({f["event_id"] for f in sel}), "path_key_blocks": len({(f["path_key"], f["block"]) for f in sel}),
                                                    "blocks": len({f["block"] for f in sel}), "days": len({f["day"] for f in sel})}
    census["fills_by_class"] = dict(Counter(f["label"] for f in fs))
    census["spread_bands"] = dict(Counter(band_of(f["spread0"], SPREAD_BANDS) for f in fs))
    census["mid_bands"] = dict(Counter(band_of(f["mid0"], MID_BANDS) for f in fs))
    census["tte_bands"] = dict(Counter(band_of(f["end_epoch"] - f["tau"], TTE_BANDS_S) for f in fs))
    census["gt"] = gate_gt(fills)
    unk = sum(1 for f in fills if f["label"] == lab.UNKNOWN)
    census["unknown_share"] = unk / len(fills) if fills else math.nan
    census["unknown_ok"] = bool(fills and census["unknown_share"] <= lab.UNKNOWN_MAX_SHARE)
    gl = gate_gl(audit_path, labeller_sha)
    if not census["unknown_ok"]:  # UNKNOWN > 5% of SCREEN fills: GL fails (section 3, labeller class 6)
        gl = {**gl, "pass": False, "reason": f"UNKNOWN share {census['unknown_share']:.3f} > {lab.UNKNOWN_MAX_SHARE}"}
    census["gl"] = gl
    census["gtp"] = gate_gtp(fills)
    census["population_label"] = thin_label(fills)
    census["counts_only"] = True
    return census


def not_testable(label: str) -> dict:
    return {"testable": False, "p": 1.0, "advance": False, "verdict": label, "est": None, "n": 0}


def screen_t(fills: list[dict], txs: list[dict], qi: QuoteIndex, census: dict, *, n_draws: int = c13.PLACEBO_DRAWS) -> dict:
    """q0273. Gates (GT, GL, GTP, GTI) first; a failed or unknown gate counts the test with p = 1. Every line carries the labels. The qi must be a mark-mode index."""
    D = build_dataset(fills, qi)
    gti = gate_gti(fills, D, txs) if len(D["tx_id"]) else {"pairs": 0, "evaluable": False, "pass": False, "not_evaluable_label": LABEL_CADENCE}
    gt, gl, gtp = census["gt"], dict(census["gl"]), census["gtp"]
    if not census.get("unknown_ok", False):  # never "met" by default: UNKNOWN > 5% fails GL
        gl["pass"] = False
    labels = [LABEL_T] + ([LABEL_THIN] if census.get("population_label") else []) + ([gti["not_evaluable_label"]] if gti.get("not_evaluable_label") else [])
    cad_fail = bool(gti.get("evaluable") and not gti.get("pass"))
    out: dict = {"gti": gti, "labels": labels, "reported": reported_variants(D, fills) if len(D["tx_id"]) else {}}
    if not gl["pass"]:
        why1 = why2 = "not testable (labeller)"
    elif cad_fail:
        why1 = why2 = "not testable (cadence)"
    else:
        why1 = None if (gt["t1_pass"] and gtp["T1"]["pass"]) else ("not testable (population)" if not gt["t1_pass"] else "not run (power)")
        why2 = None if (gt["t2_pass"] and gtp["T2"]["pass"]) else ("not testable (population)" if not gt["t2_pass"] else "not run (power)")
    out["T1"] = not_testable(why1) if why1 else t1_test(D, n_draws=n_draws)
    out["T2"] = not_testable(why2) if why2 else t2_test(D, n_draws=n_draws)
    adv = {t: out[t].get("advance") is True for t in ("T1", "T2")}
    holm = c13.stage1_holm({"T1": out["T1"].get("p"), "T2": out["T2"].get("p")})
    out["batch_holm_T"] = holm
    for t in ("T1", "T2"):
        out[t]["labels"] = labels
        out[t]["effect"] = out[t].get("est")
    out["advanced"] = [t for t, a in adv.items() if a]
    return out


# ---- HOLDOUT (q0274 seal, q0275 rep) -------------------------------------------------------------------------------------------------------------


def holdout_source_files(trades_dir: Path, snap_root: Path, pin: dict) -> list[Path]:
    """Every source file the HOLDOUT reads and q0274 seals: the monitor files ``trade_files`` returns (2026-10-21..26, the next receipt day included) and ``rows.csv.gz`` / ``rows_ext.csv.gz``
    of every capture starting inside the window."""
    files = list(trade_files(trades_dir, "holdout", pin))
    for meta in c13.list_captures(snap_root, "holdout", pin):
        files += [meta["dir"] / "rows.csv.gz", meta["dir"] / "rows_ext.csv.gz"]
    return files


def mark_quote_rows(fills: list[dict], qi: QuoteIndex) -> list[list]:
    """The raw mark-quote table (q0274): bid and ask at the mark capture of each filled transaction and horizon, no mark-out."""
    rows = []
    for f in fills:
        if f["status"] != SCREEN_STATUS_FILL:
            continue
        for h, hs in MARK_H.items():
            mk = qi.mark_for(f, hs)
            rows.append([f["tx_id"], h, mk["status"], _fmt(mk["recv"]), _fmt(mk["bid"]), _fmt(mk["ask"])])
    return rows


def drop_screen_events(hold_fills: list[dict], screen_events: set[str]) -> tuple[list[dict], dict]:
    """HOLDOUT is event-disjoint from SCREEN: every transaction whose Gamma event had a SCREEN fill is dropped (row status rewritten, never deleted), counted by class."""
    by_class: Counter = Counter()
    kept = 0
    out = []
    for f in hold_fills:
        if f["status"] == SCREEN_STATUS_FILL and f["event_id"] in screen_events:
            f = {**f, "status": "dropped: SCREEN event"}
            by_class[f["label"]] += 1
        elif f["status"] == SCREEN_STATUS_FILL:
            kept += 1
        out.append(f)
    return out, {"dropped_by_class": dict(by_class), "kept_fills": kept}


def hold_thin_label(before: list[dict], after_report: dict) -> str | None:
    tot = {g: sum(1 for f in before if f["status"] == SCREEN_STATUS_FILL and lab.audit_group(f["label"]) == g) for g in ("LOW", "NEWS")}
    dr = {g: sum(n for c, n in after_report["dropped_by_class"].items() if lab.audit_group(c) == g) for g in ("LOW", "NEWS")}
    if any(tot[g] and dr[g] / tot[g] > HOLD_OVERLAP_THIN_SHARE for g in ("LOW", "NEWS")):
        return LABEL_HOLD_THIN
    return None


def stage2_t(D: dict, triggered: dict[str, bool], gti_pooled: dict, *, n_draws: int = c13.PLACEBO_DRAWS) -> dict:
    """T Stage 2 on the sealed HOLDOUT dataset: T1-rep / T2-rep run only when triggered (T1 advanced / T2 advanced), each needs >= 500 fills of each class it uses in >= 60 events (else "not run
    (power)", counted); T3 needs T2's trigger and the POOLED SCREEN + HOLDOUT GTI PASS (< 200 pooled pairs -> "not testable (cadence)"). Judged at alpha / 5 when early, Holm once final."""
    out: dict = {"labels": [LABEL_REP, LABEL_HOLD], "gti_pooled": gti_pooled}

    def pop_ok(groups):
        for g in groups:
            sel = D["grp"] == g
            ok_ = sel & np.isfinite(D["m_2-4h"])
            if not (ok_.sum() >= GT_MIN["fills"] and len(set(D["event"][ok_])) >= GT_MIN["events"]):
                return False
        return True
    if triggered.get("T1"):
        out["T1"] = t1_test(D, n_draws=n_draws, rep=True) if pop_ok(("LOW", "NEWS")) else not_testable("not run (power)")
    if triggered.get("T2"):
        out["T2"] = t2_test(D, n_draws=n_draws, rep=True) if pop_ok(("LOW",)) else not_testable("not run (power)")
        if not gti_pooled.get("evaluable"):
            out["T3"] = not_testable("not testable (cadence)")
        elif not gti_pooled.get("pass"):
            out["T3"] = not_testable("not testable (cadence)")
        elif not pop_ok(("LOW",)):
            out["T3"] = not_testable("not run (power)")
        else:
            out["T3"] = t3_test(D)
    tests = {t: out[t] for t in ("T1", "T2", "T3") if t in out}
    for r in tests.values():
        r["stage2_early_alpha_ok"] = c13.early_stage2_ok(r.get("p") if r.get("testable", True) else None)
        r["labels"] = out["labels"]
    out["holm_family_partial"] = c13.stage2_holm({t: (r.get("p") if r.get("testable", True) else None) for t, r in tests.items()}) if tests else {}  # information only: the decision step is the CB13-wide stage2-final Holm
    for r in tests.values():
        r["stage2_pass_alpha_over_k"] = bool(r.get("checks_ok") and r["stage2_early_alpha_ok"])  # early alpha / 5 only (all binding checks + p < alpha / 5); the CB13-wide final Holm (run_cb13.py stage2-final) can only add passes
    return out


# =====================================================================================================================================================
# Smoke (q0270: no network), declared
# =====================================================================================================================================================


def _first(x):
    """(recv, bid, ask) of a ``Q`` touch row, None for no row."""
    return None if x is None else (x.recv, x.bid, x.ask)


def h8_counts(prints: list[dict], lookup) -> dict[str, int]:
    """Probe H8's classification of prints against the market's latest complete-capture row received before the print: touch age band (<= 20 / 20-60 / 60-120 / > 120 min) x position of the
    YES-terms price (crossing = at or beyond the touch, inside = strictly inside the spread; no row / one-sided counted apart). ``lookup(condition_id, ts) -> (recv, bid, ask) | None``."""
    out: Counter = Counter()
    for p in prints:
        row = lookup(p["condition_id"], p["ts"])
        if row is None:
            out["no row"] += 1
            continue
        recv, bid, ask = row
        if not two_sided(bid, ask):
            out["one-sided"] += 1
            continue
        age = (p["ts"] - recv) / 60.0
        band = "<=20m" if age <= 20 else ("20-60m" if age <= 60 else ("60-120m" if age <= 120 else ">120m"))
        y = yes_price(p)
        out[f"{band}|{'crossing' if (y >= ask or y <= bid) else 'inside'}"] += 1
    return dict(sorted(out.items()))


def smoke_capture_pair(caps: list[dict], pin: dict) -> tuple[dict, dict] | None:
    """The two SCREEN captures of the smoke join: the first CONSECUTIVE pair (oldest first) whose interval lies inside the SCREEN print window ``split_bounds('screen')``. The capture range
    starts at ``T_SCREEN_CAPTURE_FROM`` (2026-10-11T20Z, touches for the first prints), before the print window opens (2026-10-12T00Z), so the first two captures hold no print between them
    (smoke v1 defect, CREATIVE_BATCH_13.md section 11.y)."""
    lo, hi = c13.split_bounds("screen", pin)
    for a, b in zip(caps, caps[1:], strict=False):
        if a["start"] >= lo and b["start"] <= hi:
            return a, b
    return None


def smoke_offline(ctx: dict) -> dict:
    """Guard fixtures (no network), the capture-print join on two SCREEN captures of the host (counts only) and the labeller UNKNOWN share on all SCREEN titles. ``ctx``: ``pin`` (J4-R pin),
    ``trades_dir``, ``snap_root`` (host files; missing -> the host criteria fail), ``cb3_spec_dir`` (tests)."""
    import tempfile  # noqa: PLC0415

    pin = ctx["pin"]
    res = []
    edges = [
        lambda: c13.check_window("screen", c13.ep(c13.T_SCREEN[0]), pin["start"] + 1, pin),
        lambda: c13.check_window("holdout", pin["end"] - 1, pin["end"] + 10, pin),
        lambda: c13.require_capture_allowed(pin["start"], "screen", pin),
        lambda: c13.require_capture_allowed(pin["end"] - 1, "holdout", pin),
        lambda: c13.guard_monitor_file(Path("x/live_trades/alerts.jsonl")),
        lambda: c13.guard_monitor_file(Path("x/live_trades/scores-20261012.jsonl")),
        lambda: c13.guard_monitor_file(Path("x/live_trades/outcomes.jsonl")),
        lambda: c13.guard_monitor_file(Path("x/live_trades/wallets.jsonl")),
        lambda: c13.refuse_path(Path("x/surprise_live/a")),
        lambda: c13.refuse_path(Path("x/cross_venue_live/a"), allow=("cross_venue_live",)),
        lambda: c13.refuse_path(Path("x/e005/a")),
        lambda: c13.refuse_path(Path("x/trade_samples/a"), allow=("trade_samples",)),
        lambda: c13.require_output_root(Path("x/creative_batch12/a")),
        lambda: c13.guard_screen_path(Path("x/creative_batch13/t_holdout/fills.csv.gz")),
    ]
    for fn in edges:
        try:
            fn()
            res.append(False)
        except Refused:
            res.append(True)
    try:
        c13.require_after(ctx.get("now", time.time()), c13.ep(c13.T_SEAL_EARLIEST) + 10**9, "t_holdout")
        res.append(False)
    except NotNow:
        res.append(True)
    with tempfile.TemporaryDirectory() as d:
        try:
            c13.cb3_hold_lifted(Path(d), Path(d) / "none.md", is_committed=lambda p: False)
            res.append(False)
        except NotNow:
            res.append(True)
    w = c13.whitelist_print({"ts": 1, "condition_id": "0xa", "outcome_index": 0, "price": 0.5, "size": 10, "cash": 5, "side": "BUY", "wallet_hash": "w", "ctx_chg_1h": 0.1, "recv_ts": 5, "key": "k",
                             "tx16": "t", "title": "T", "slug": "s"})
    clean = bool(w and not any(k in w for k in ("side", "wallet_hash", "ctx_chg_1h", "recv_ts", "key")))
    res.append(clean)
    guards = {"pass": bool(all(res)), "checks": res}
    out: dict = {"guards_fixture_T": guards}
    # host: the capture-print join on two SCREEN captures
    join = {"pass": False, "reason": "no host files"}
    unk = {"pass": False, "reason": "no host files"}
    try:
        snap, trades = Path(ctx["snap_root"]), Path(ctx["trades_dir"])
        caps = c13.list_captures(snap, "screen", pin)
        pair = smoke_capture_pair(caps, pin)
        if pair is not None:
            c0, c1 = pair
            prints, _ = screen_prints(trades, "screen", pin)
            between = [p for p in prints if c0["start"] < p["ts"] < c1["start"]]
            wanted = {p["condition_id"] for p in between}
            qi = load_quote_index([c0, c1], wanted, "touch", "screen", pin)
            # (A) the join as the frame does it (QuoteIndex.touch, every print its own transaction) and (B) probe H8's rule recomputed independently from the raw capture rows
            via_index = h8_counts(between, lambda cid, ts: _first(qi.touch(cid, ts)[0]))
            raw: dict[str, list[tuple[float, float, float]]] = {}
            for meta in (c0, c1):
                for r in c13.iter_capture_rows(meta["dir"], wanted):
                    raw.setdefault(r["condition_id"], []).append((c13.parse_iso(r["received_utc"]), c13.num(r.get("best_bid")), c13.num(r.get("best_ask"))))
            via_raw = h8_counts(between, lambda cid, ts: max((x for x in raw.get(cid, []) if x[0] < ts), default=None, key=lambda x: x[0]))
            single, _ = build_transactions(between, aggregate=False)
            fills, counts = make_fills(single, qi)
            band_counts = Counter(f["status"] for f in fills)
            join = {"pass": bool(len(between) > 0 and via_index == via_raw and sum(counts.values()) == len(single) == len(between)), "n_prints_between": len(between),
                    "captures": [c0["capture_id"], c1["capture_id"]],
                    "h8_age_by_position_via_index": via_index, "h8_age_by_position_independent": via_raw, "status_counts": counts, "touch_consistency_bands": dict(band_counts),
                    "note": "the H8 rule (touch age <=20 / 20-60 / 60-120 / >120 min x crossing / inside / no row or one-sided) is recomputed independently of the quote index and must give identical counts; the "
                            "original H8 totals (44 captures, probe script not committed) are not reproduced numerically (declared in CREATIVE_BATCH_13.md, freeze-check fixes)"}
        elif not caps:
            join = {"pass": False, "reason": "no SCREEN captures found"}
        else:
            join = {"pass": False, "reason": "no two consecutive SCREEN captures inside the SCREEN print window"}
        txs, _ = screen_transactions(trades, "screen", pin)
        n = len(txs)
        unknown = sum(1 for t in txs if lab.classify(t["title"], t["slug"], t["ctx_fee_type"], "", "", t["ctx_category"])[0] == lab.UNKNOWN)
        fix = (lab.classify("Will Bitcoin reach $100k?", "", "", "", "", "")[0] == lab.PATH and lab.classify("Team A vs. Team B", "", "", "", "", "")[0] == lab.SPORTS
               and lab.classify("Will CPI be above 3%?", "", "", "", "", "")[0] == lab.PUBLIC and lab.classify("Will X resign by Friday?", "", "", "", "", "")[0] == lab.NEWS)
        unk = {"pass": bool(n > 0 and fix and unknown / n <= lab.UNKNOWN_MAX_SHARE), "n_transactions": n, "unknown": unknown, "fixtures_ok": fix,
               "note": "title-only classification of all SCREEN titles (counts only); the census recomputes with the sidecar"}
    except (KeyError, OSError, Refused) as exc:
        join = {**join, "error": f"{type(exc).__name__}: {exc}"[:200]}
    out["t_capture_print_join"] = join
    out["t_labeller_unknown"] = unk
    return out


def declared() -> dict:
    return {"fill": "print-anchored: lift (a0 <= P_min, P_max <= a0 + s0) -> maker sold at P_min; hit (b0 - s0 <= P_min, P_max <= b0) -> maker bought at P_max; inside spread: no fill; else inconsistent",
            "units": "every touch-consistent transaction; one-per-side-per-pass, all-prints, stale-touch and size-weighted variants are reported",
            "touch": {"received_utc_lt_tau": True, "max_age_s": TOUCH_MAX_AGE_S, "spread_max": SPREAD_MAX, "mid": [MID_LO, MID_HI], "end_margin_s": END_MARGIN_S},
            "marks": {"horizons_s": MARK_H, "usable_extra_s": MARK_USABLE_EXTRA_S, "wide_spread": WIDE_MARK, "labels": ["2-4 h", "6-8 h"]},
            "tau": "earliest venue time of the transaction's prints (conservative for the touch)",
            "tests": {"T1": {"floor_cents": T1_FLOOR}, "T2": {"floor_cents": T2_FLOOR}, "T3": {"floor_cents": T3_FLOOR, "exit_robust_cents": T3_EXIT_ROBUST, "default_fee": T3_DEFAULT_FEE}},
            "ways": ["event", "path key x 6 h block", "6 h block (CB10 small-G rule)"], "loo_day": {"p_max": c13.LOO_DAY_P, "sign": True},
            "gates": {"GT": GT_MIN, "GTP_mde_max": GTP_MDE_MAX, "GTI": {"min_pairs": GTI_MIN_PAIRS, "agree": GTI_AGREE, "window_s": GTI_WINDOW_S}},
            "placebos": {"T1_composition": c13.PLACEBO_SEEDS["T1_composition"], "T2_signflip": c13.PLACEBO_SEEDS["T2_signflip"], "draws": c13.PLACEBO_DRAWS, "max_advance": c13.PLACEBO_MAX_ADVANCE},
            "exclusions": {"skip_runs": list(T_EXCL_SKIP_RUNS), "thin_share": EXCL_THIN_SHARE, "no_ts_file": "all ids dropped (conservative)"},
            "labels": {"T": LABEL_T, "T2": LABEL_T2, "hold": LABEL_HOLD, "rep": LABEL_REP, "T3": LABEL_T3},
            "hold": {"event_disjoint": True, "thin_share": HOLD_OVERLAP_THIN_SHARE, "cb3_hold": "q0275 waits for CB3's freeze commit or its ledger stop record"}}
