# ruff: noqa: E501
"""CB16-Q: quoter grain (docs/research_lab/CREATIVE_BATCH_16.md CB16-Q, section 9 items 1-8, section 10). Rules part ``A`` (with ``cb16_u``: Q and U share units and mark-outs).

Host files only, NO network: the live large-trade monitor's prints (``live_trades/trades-YYYYMMDD.jsonl``, whitelisted fields; ``tx16`` aggregated in memory and discarded) and the
complete-universe captures (``snapshots/<capture>/rows.csv.gz`` + ``rows_ext.csv.gz``, whitelisted columns), plus ``book_sweeps/`` for the REPORTED shape descriptor only.

**Fill and side: CB13-T's frozen rule, by pin** (``cb16_common.CB13_PINS``): transactions by ``cb13_t.build_transactions``, the touch by ``cb13_t.QuoteIndex.touch`` (latest complete
capture with ``received_utc < tau``), the side by ``cb13_t.classify_position`` (lift: maker sold YES, ``d = -1``, ``P = P_min``; hit: maker bought YES, ``d = +1``, ``P = P_max``), marks and
mark-outs by ``cb13_t.build_dataset`` (``M_h = 100 d (mid_h - P)``), the adverse-touch and worst-case marks and the CB13-T3 round trip by ``cb13_t.t3_values``. CB16 differs from CB13-T
only where the design says so: no UNKNOWN exclusion (Q and U use the LABELLER's SPORTS-FEED class only), the election-night exclusion, the windows and the key rule.

**Grain** (premise 1): ``g = 1`` (bot-grain) iff ``round(1000 P) mod 10 != 0``; ``P`` is the maker-adverse price (the best level the taker lifted), so ``g`` is the grain of the best
resting quote at the print. Eligibility: ``order_price_min_tick_size = 0.001`` at the touch AND the 2-4 h mark capture (a change is "tick change", excluded and counted) and
``P in [0.05, 0.95]``. Q1 is the coefficient on ``g`` in a market fixed-effect OLS of ``M_2-4h`` (one unit per fill, unweighted), one-sided > 0, floor +0.5c.

The quote index has two modes: ``touch`` (frame and census: NO mark accessor) and ``mark`` (screen and rep). No path computes anything for ``surprise_live`` / E011 / E004-E007.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import time
from bisect import bisect_left
from collections import Counter
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb13_common as c13
from . import cb13_label as lab
from . import cb13_t as t13
from . import cb16_common as c16

Refused = cm.Refused
NotNow = cm.NotNow

LABEL_A = "L2 live window (SCREEN_A, post-freeze), Stage-1 screen"
LABEL_UPPER = "maker mark-out at a mid exit: an upper bound for any maker"
LABEL_REP = t13.LABEL_REP
LABEL_RT = t13.LABEL_T3
LABEL_Q2 = "fills like the bots' fills; queue position ignored, so an upper bound"
LABEL_CADENCE = t13.LABEL_CADENCE
LABEL_REP_THIN = "REP_A thinned by event overlap"
LABEL_EXCL = "grain-dependent exclusion could explain the contrast"
LABEL_UNINFORMATIVE = "composition placebo uninformative"
LABEL_HALFSPREAD = "realised half-spread, not adverse selection"
LABEL_GRAIN = "quoter grain"
LABEL_COMPOSITION = "composition, not grain"
LABEL_SPREAD_STATE = "grain or contemporaneous spread state"
LABEL_UNAUDITED = "labeller unaudited"
NOT_TESTABLE_GRAIN = "not testable (grain)"
NOT_TESTABLE_POP = "not testable (population)"
NOT_RUN_POWER = "not run (power)"
NOT_TESTABLE_CADENCE = "not testable (cadence)"
S_FILL = t13.SCREEN_STATUS_FILL
S_ELECTION = "excluded: election night"
S_REP_DROP = "dropped: SCREEN event"
GRAIN_TICK = 0.001
TICK_TOL = 1e-9
GRAIN_P_BAND = (0.05, 0.95)
U_P_BAND = (0.03, 0.97)
Q_SPREAD_EDGES = (0.01, 0.02, 0.05)  # {<= 1c, 1-2c, 2-5c, > 5c}
Q_P_EDGES = (0.20, 0.80)  # {[0.05, 0.20), [0.20, 0.80], (0.80, 0.95]}
Q_SIZE_EDGES = (2500.0, 10000.0)  # {< $2.5k, $2.5-10k, >= $10k}
AGE_EDGE_S = 1200.0  # touch-age band {<= 20, 20-60 min}
TTE_EDGES_S = (86400.0, 7 * 86400.0)  # {< 1 d, 1-7 d, > 7 d}
TIGHT_AGE_S = 1200.0
TIGHT_SPREAD = 0.01
TIGHT_MIN_FILLS = 300
REWARD_MIN_FILLS = 300
INFORMATIVE_SHARE = 0.50
Q1_FLOOR = 0.5
Q2_FLOOR = 0.5
Q2_EXIT_ROBUST = 0.5
Q2_MAX_SIZE = t13.T3_MAX_SIZE
SPREAD_FREE_P = 0.05
P_ROBUST_BAND = (0.10, 0.90)
BIG_TX_USD = 10000.0
GQG_SUB_SHARE = (0.05, 0.95)
GQG_BOTH_SHARE = 0.40
GQ_MIN = {"fills": 1000, "markets": 100, "events": 60}
POWER_MDE_MAX = 1.0  # 2 x the 0.5c floor
GAI_MIN_PAIRS = t13.GTI_MIN_PAIRS
GAI_AGREE = t13.GTI_AGREE
REP_THIN_SHARE = 0.40
WORST_QUANTILE = {"bot": 10.0, "human": 90.0}
SWEEP_MAX_AGE_S = 7200.0
MARK_H = t13.MARK_H
POLITICS_FEE_PREFIX = "politics_fees"
A_EXCL_SKIP_RUNS = t13.T_EXCL_SKIP_RUNS
A_EXCL_SKIP_RE = r"(_live$|^h15_|^h16_)"  # live prospective stages are collection overlap (never dropped); h15_* is never opened
EXTRA_COLUMNS = ["tick_touch", "created_epoch", "token0", "hour", "g", "grain_ok", "u_ok", "excl_P", "excl_g", "politics", "s", "tau_prev", "n_prior", "x", "x3", "n_prior3", "wake",
                 "x_raw", "silence_status", "spans_night", "s12_dropped", "wake_lag_s", "sw_share", "sw_ratio", "sw_levels", "sw_age_s"]
FILL_COLUMNS = list(t13.FILL_COLUMNS) + EXTRA_COLUMNS
MARK_COLUMNS = list(t13.MARK_COLUMNS) + ["tick"]
FILLS_NAME = "fills.csv.gz"
MARKS_NAME = "mark_quotes.csv.gz"
KEYS_NAME = "a_exclusion_keys.csv.gz"
KEYS_PARTIAL_NAME = "a_exclusion_keys_partial.jsonl"
SMOKE_NEEDS = ("a_cb13_pins", "a_refusals", "a_forbidden_fields", "a_grain_parser", "a_monitor_gap", "a_silence_standardiser", "a_cb13_reproduction")


# =====================================================================================================================================================
# Small rules
# =====================================================================================================================================================


def grain_of(P: float) -> int:
    """1 (bot-grain, sub-cent) iff ``round(1000 P) mod 10 != 0``; 0 (human-grain, whole cent) otherwise. YES terms preserve the grain (``1 - x`` is sub-cent iff ``x`` is)."""
    if not math.isfinite(P):
        return -1
    return int(int(round(1000.0 * float(P))) % 10 != 0)


def tick_is_grain(tick: float) -> bool:
    return bool(math.isfinite(tick) and abs(float(tick) - GRAIN_TICK) < TICK_TOL)


def in_band(x: float, band: tuple[float, float]) -> bool:
    return bool(math.isfinite(x) and band[0] - 1e-12 <= float(x) <= band[1] + 1e-12)


def grain_eligible(P: float, tick_touch: float) -> bool:
    """The grain arm: tick 0.001 at the touch capture and ``P in [0.05, 0.95]`` (both edges included; the tails are on a 0.001 tick for everyone)."""
    return bool(tick_is_grain(tick_touch) and in_band(P, GRAIN_P_BAND))


def spread_band(s: float) -> int:
    return int(sum(s > e + 1e-9 for e in Q_SPREAD_EDGES)) if math.isfinite(s) else -1


def p_band(P: float) -> int:
    if not math.isfinite(P):
        return -1
    if P < Q_P_EDGES[0] - 1e-12:
        return 0
    return 1 if P <= Q_P_EDGES[1] + 1e-12 else 2


def size_band(cash: float) -> int:
    return int(sum(cash >= e for e in Q_SIZE_EDGES)) if math.isfinite(cash) else -1


def age_band(age_s: float) -> int:
    return int(age_s > AGE_EDGE_S) if math.isfinite(age_s) else -1


def tte_band(tte_s: float) -> int:
    if not math.isfinite(tte_s):
        return -1
    return 0 if tte_s < TTE_EDGES_S[0] else (1 if tte_s <= TTE_EDGES_S[1] else 2)


def is_politics(fee_type: str, label: str) -> bool:
    return bool(str(fee_type or "").startswith(POLITICS_FEE_PREFIX) or label == lab.SCHEDULED)


# =====================================================================================================================================================
# Readers (whitelisted; the lookback floor; REP_A units refused until opened)
# =====================================================================================================================================================


def trade_files(trades_dir: Path, lo: float, hi: float) -> list[Path]:
    """``trades-YYYYMMDD.jsonl`` files that can hold prints with venue time in ``[lo, hi)`` (daily by RECEIPT; prints arrive about 8 min late, so the day after ``hi`` is included;
    the venue-time filter keeps only ``ts`` inside the window)."""
    d0, d1 = datetime.fromtimestamp(lo, UTC).date(), datetime.fromtimestamp(hi - 1, UTC).date()
    d1 = datetime.fromordinal(d1.toordinal() + 1).date()
    files, d = [], d0
    while d <= d1:
        p = Path(trades_dir) / f"trades-{d:%Y%m%d}.jsonl"
        if p.exists():
            files.append(c16.guard_monitor_file(p))
        d = datetime.fromordinal(d.toordinal() + 1).date()
    return files


def iter_prints(path: Path, lo: float, hi: float) -> Iterator[dict]:
    """Whitelisted prints (CB13's ``whitelist_print``: side, wallet_*, recv_ts and every other ctx_* never copied) with venue ``ts`` in ``[lo, hi)``; ``lo`` must be at or after the floor."""
    c16.guard_floor(lo, "print window start")
    p = c16.guard_monitor_file(path)
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            w = c13.whitelist_print(rec) if isinstance(rec, dict) else None
            if w is not None and lo <= w["ts"] < hi:
                yield w


_LOOKBACK_KEEP = (*c16.LOOKBACK_FIELDS, "tx16")


def iter_lookback(path: Path, lo: float, hi: float) -> Iterator[dict]:
    """The U lookback reader: ``ts``, ``condition_id`` and ``cash`` only (``tx16`` in memory for the transaction key); every other field is dropped while decoding."""
    c16.guard_floor(lo, "lookback window start")
    p = c16.guard_monitor_file(path)
    hook = lambda kv: {k: v for k, v in kv if k in _LOOKBACK_KEEP}  # noqa: E731
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line, object_pairs_hook=hook)
            except ValueError:
                continue
            ts = c16.num(rec.get("ts")) if isinstance(rec, dict) else math.nan
            if math.isfinite(ts) and lo <= ts < hi and rec.get("condition_id"):
                yield {"ts": ts, "condition_id": str(rec["condition_id"]), "cash": c16.num(rec.get("cash")), "tx16": str(rec.get("tx16") or "")}


def iter_recv_lag(path: Path, lo: float, hi: float, wanted: set[tuple[str, str]]) -> Iterator[tuple[str, str, float]]:
    """U2's receipt-lag robustness ONLY (rep frame): ``(condition_id, tx16, recv_ts - ts)`` for the wanted wake-up transactions; ``recv_ts`` is read for nothing else and never written."""
    c16.guard_floor(lo, "lag window start")
    p = c16.guard_monitor_file(path)
    hook = lambda kv: {k: v for k, v in kv if k in (*c16.U2_LAG_FIELDS, "tx16")}  # noqa: E731
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line, object_pairs_hook=hook)
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            ts, rv = c16.num(rec.get("ts")), c16.num(rec.get("recv_ts"))
            key = (str(rec.get("condition_id") or ""), str(rec.get("tx16") or ""))
            if key in wanted and math.isfinite(ts) and math.isfinite(rv) and lo <= ts < hi:
                yield key[0], key[1], rv - ts


def timeline(trades_dir: Path, lo: float, hi: float) -> tuple[dict[str, np.ndarray], np.ndarray, dict]:
    """The large-transaction stream: per condition id the sorted venue times of its transactions (``(tx16, condition_id)`` keys, earliest print; a print without a hash is its own
    transaction) in ``[lo, hi)``, and the sorted times of every print in any market (the global monitor-gap detector)."""
    first: dict[tuple, float] = {}
    all_ts: list[float] = []
    n = 0
    for f in trade_files(trades_dir, lo, hi):
        for r in iter_lookback(f, lo, hi):
            all_ts.append(r["ts"])
            key = (r["tx16"], r["condition_id"]) if r["tx16"] else (f"single:{n}", r["condition_id"])
            n += 1
            first[key] = min(first.get(key, math.inf), r["ts"])
    by: dict[str, list[float]] = {}
    for (_, cid), t in first.items():
        by.setdefault(cid, []).append(t)
    return {k: np.array(sorted(v)) for k, v in by.items()}, np.array(sorted(all_ts)), {"n_prints": len(all_ts), "n_transactions": len(first)}


def window_transactions(trades_dir: Path, lo: float, hi: float, s_a: float, *, rep_open: bool = False) -> tuple[list[dict], dict]:
    """Whitelisted prints with ``ts`` in ``[lo, hi)`` aggregated into transactions by CB13's pinned ``build_transactions`` (YES terms, hash discarded). A REP_A transaction is refused
    unless the REP_A path is open."""
    prints = []
    files = trade_files(trades_dir, lo, hi)
    for p in files:
        prints.extend(iter_prints(p, lo, hi))
    txs, info = t13.build_transactions(prints)
    for t in txs:
        c16.guard_rep_unit(t["ts"], s_a, rep_open=rep_open)
    return txs, {**info, "n_prints": len(prints), "n_files": len(files), "window": [c16.iso(lo), c16.iso(hi)]}


# =====================================================================================================================================================
# The quote index (CB13's pinned class plus per-capture ticks, creation times and the YES token)
# =====================================================================================================================================================


class QuoteIndex16(t13.QuoteIndex):
    """CB13-T's ``QuoteIndex`` (touch: latest row with ``received_utc < tau``; marks: first capture at or after ``tau + h``, usable within 2 h) plus the sidecar tick of every capture
    (the grain rule reads it at the touch AND the 2-4 h mark capture), the market creation time (genesis rule) and the YES token (sweep join)."""

    def __init__(self, mode: str, boundary_epoch: float | None = None):
        super().__init__(mode, boundary_epoch)
        self.tick: dict[tuple[str, int], float] = {}
        self.created: dict[str, float] = {}
        self.token0: dict[str, str] = {}

    def tick_at(self, cid: str, cap: int) -> float:
        return self.tick.get((cid, int(cap)), math.nan)

    def mark_cap(self, cid: str, tau: float, h: float) -> int | None:
        """The capture index of the row the CB13 mark rule uses at horizon ``h`` (None if no usable row); mark mode only."""
        if self.mode != "mark":
            raise Refused("the quote index is in touch mode: no mark capture is available to a frame or census path")
        target = tau + h
        lst = self.q.get(cid) or []
        i = bisect_left(self.recv.get(cid, []), target)
        if i < len(lst) and lst[i].recv <= target + t13.MARK_USABLE_EXTRA_S:
            return int(lst[i].cap)
        return None

    def tick_for(self, fill: dict, h: float) -> float:
        cap = self.mark_cap(fill["condition_id"], fill["tau"], h)
        return math.nan if cap is None else self.tick_at(fill["condition_id"], cap)


class MarkTable16(t13.MarkTable):
    """CB13's sealed raw mark-quote table interface plus the mark capture's tick (``tick`` column)."""

    def tick_for(self, fill: dict, h: float) -> float:
        key = next(k for k, v in MARK_H.items() if v == h)
        r = self.rows.get((int(fill["tx_id"]), key))
        return c16.num(r.get("tick")) if r is not None and r.get("tick") not in ("", None) else math.nan


def list_captures(snap_root: Path, lo: float, hi: float, *, guard: Callable[[float], object] | None = None, only_complete: bool = True) -> list[dict]:
    """Complete captures whose START lies in ``[lo, hi]`` (oldest first). The default guard refuses a range before the lookback floor; a capture outside the range is never opened beyond
    its directory name."""
    guard = guard or (lambda t: c16.guard_floor(t, "capture"))
    guard(lo)
    root = c16.refuse_path(Path(snap_root), allow=("snapshots",))
    out = []
    for d in sorted(root.iterdir() if root.exists() else []):
        m = re.match(c16.CAPTURE_DIR_RE, d.name)
        if not m or not d.is_dir():
            continue
        nominal = datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()
        if not (lo <= nominal <= hi):
            continue
        meta = c13.capture_meta(c16.guard_capture_dir(d))
        if not (lo <= meta["start"] <= hi):
            continue
        guard(meta["start"])
        if only_complete and meta["state"] != "complete":
            continue
        out.append(meta)
    return sorted(out, key=lambda m: m["start"])


def load_quote_index(captures: list[dict], wanted: set[str], mode: str, *, boundary_epoch: float | None = None, guard: Callable[[float], object] | None = None) -> QuoteIndex16:
    """Stream the captures one at a time (whitelisted columns, rows filtered to ``wanted``) into a ``QuoteIndex16``; the sidecar's static attributes come from the first capture that
    carries the market, the tick from EVERY capture."""
    guard = guard or (lambda t: c16.guard_floor(t, "capture"))
    qi = QuoteIndex16(mode, boundary_epoch)
    for k, meta in enumerate(captures):
        guard(meta["start"])
        qi.caps.append((meta["start"], meta["capture_id"]))
        for r in c13.iter_capture_rows(meta["dir"], wanted):
            cid = r["condition_id"]
            qi.add(cid, t13.Q(c13.parse_iso(r["received_utc"]), c13.num(r.get("best_bid")), c13.num(r.get("best_ask")), c13.num(r.get("liquidity")), c13.parse_iso(r.get("end_date")), k,
                              str(r.get("closed")).lower() == "true", str(r.get("binary")) == "1", str(r.get("market_id")), str(r.get("event_id") or ""), str(r.get("neg_risk_market_id") or "")))
            if cid not in qi.token0 and r.get("clob_token_id_0"):
                qi.token0[cid] = str(r["clob_token_id_0"])
        for s in c13.iter_sidecar_rows(meta["dir"], wanted):
            cid = s["condition_id"]
            qi.tick[(cid, k)] = c13.num(s.get("order_price_min_tick_size"))
            if cid not in qi.static:
                qi.static[cid] = {"fee_type": s.get("fee_type", ""), "fee_category": s.get("fee_category", ""), "series_slugs": s.get("series_slugs", ""),
                                  "fee_rate": t13.fee_rate_of(s.get("fee_schedule")), "clob_rewards": 1 if str(s.get("clob_rewards") or "") not in ("", "[]", "null") else 0}
            if cid not in qi.created:
                ce = c13.parse_iso(s.get("created_at"))
                if math.isfinite(ce):
                    qi.created[cid] = ce
    qi.finish()
    return qi


# =====================================================================================================================================================
# Exclusion keys (sealed historical sets with a stored timestamp inside the window; section 1.3)
# =====================================================================================================================================================


def a_exclusion_keys(hist_root: Path, windows_: list[tuple[float, float]], *, state_path: Path | None = None, budget_s: float | None = None, clock=time.monotonic) -> tuple[dict[str, str], dict]:
    """Keys (``market_id:x``, ``event_id:x``, ``condition_id:x``, ``neg_risk_market_id:x``) of every sealed historical set (a run directory under ``hist_root`` other than the inert runs,
    the live prospective stages ``*_live`` and every ``h15_*`` / ``h16_*`` root) that holds the id with a stored timestamp INSIDE a CB16 window. Only id and timestamp columns are read
    (CB13's field-restricted accessor); a file with no timestamp column contributes no key (counted). Resumable by file (``t13.ScanUnfinished`` between files once ``budget_s`` is spent)."""
    keys: dict[str, str] = {}
    rep: dict = {"sources": {}, "skipped_runs": []}
    hr = Path(hist_root)
    if not hr.exists():
        return keys, {**rep, "history_root_missing": True}
    todo: list[tuple[str, Path, str]] = []
    for run in sorted(p for p in hr.iterdir() if p.is_dir()):
        if run.name in A_EXCL_SKIP_RUNS or re.search(A_EXCL_SKIP_RE, run.name):
            rep["skipped_runs"].append(run.name)
            continue
        for f in sorted(f for f in run.rglob("*") if f.is_file() and (f.name.endswith(".csv") or f.name.endswith(".csv.gz"))):
            if "guarded" in f.name or "outcome" in f.name.lower():
                continue
            todo.append((run.name, f, f.relative_to(hr).as_posix()))
    done: dict[str, dict] = {}
    if state_path is not None:
        sp = Path(state_path)
        valid = t13._partial_records(sp, windows_)
        done = {r["file"]: r for r in valid}
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("".join(json.dumps(r) + "\n" for r in [{"windows": [list(w) for w in windows_]}, *valid]))
    t0 = clock()
    for run_name, f, rel in todo:
        if rel in done:
            continue
        if budget_s is not None and clock() - t0 >= budget_s:
            raise t13.ScanUnfinished(f"A exclusion-key scan unfinished: {len(done)}/{len(todo)} files; resumable")
        hit: set[str] = set()
        nots = False
        for w in windows_:
            in_win, _every, info = c13.read_id_ts_columns(f, w)
            hit |= in_win
            nots = bool(info["no_ts"])
        rec = {"run": run_name, "file": rel, "no_ts": nots, "keys": sorted(hit)}
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


# =====================================================================================================================================================
# Fills (features only; no mark)
# =====================================================================================================================================================


def excluded_side_price(t: dict, b0: float, a0: float) -> float:
    """The maker-adverse price an excluded transaction would have had (section CB16-Q 'exclusion by grain'): ``P_min`` for a transaction above the touch mid, ``P_max`` below it (a
    one-sided touch uses its one side as the reference)."""
    ref = (a0 + b0) / 2 if t13.two_sided(b0, a0) else (a0 if math.isfinite(a0) else b0)
    if not math.isfinite(ref):
        return math.nan
    return float(t["p_min"]) if t["p_vwap"] > ref else float(t["p_max"])


def make_fills(txs: list[dict], qi: QuoteIndex16, keys: dict[str, str] | None = None) -> tuple[list[dict], dict]:
    """One row per transaction (CB13-T's statuses and its pinned touch-consistency rule): ``fill``, ``inside spread``, ``inconsistent with touch (drift)``, ``excluded: ...`` (no row,
    one-sided, not binary, touch > 60 min, mid outside [0.03, 0.97], spread > 10c, end within 3 h), ``excluded: election night`` or ``dropped: key <source>``. Unlike CB13-T there is no
    UNKNOWN exclusion. Features only (touch, the capture before it, ticks, grain); no mark quote is read."""
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
        row = {"tx_id": i, "condition_id": cid, "market_id": tq.market_id if tq else str(t.get("ctx_market_id") or ""), "event_id": ev, "label": cls, "underlying": under or "",
               "path_key": path_key, "tau": t["ts"], "tau_last": t["ts_last"], "p_vwap": t["p_vwap"], "p_min": t["p_min"], "p_max": t["p_max"], "size": t["size"], "cash": t["cash"],
               "n_fills": t["n_fills"], "d": 0, "P": math.nan, "bid0": math.nan, "ask0": math.nan, "spread0": math.nan, "mid0": math.nan, "touch_recv": math.nan, "touch_age_s": math.nan,
               "touch_cap": -1, "liq": math.nan, "end_epoch": math.nan, "prev_mid": math.nan, "prev_recv": math.nan, "q_stale": math.nan, "d_stale": 0, "fee_rate": st.get("fee_rate", math.nan),
               "clob_rewards": st.get("clob_rewards", 0), "fee_type": ft, "block": c16.block6(t["ts"]), "day": c16.utc_day(t["ts"]), "neg_risk_market_id": tq.nrm if tq else "",
               "tick_touch": math.nan, "created_epoch": qi.created.get(cid, math.nan), "token0": qi.token0.get(cid, ""), "hour": c16.hour_of_day(t["ts"]), "g": -1, "grain_ok": 0, "u_ok": 0,
               "excl_P": math.nan, "excl_g": -1, "politics": int(is_politics(ft, cls))}
        for k in EXTRA_COLUMNS:
            row.setdefault(k, math.nan)
        row["wake"], row["silence_status"], row["spans_night"], row["s12_dropped"] = 0, "", 0, 0
        status = S_FILL
        src = t13.key_hit(keys, cid, row["market_id"], ev, row["neg_risk_market_id"]) if keys else None
        if src:
            status = f"{t13.S_KEY} {src}"
        elif c16.in_election_night(t["ts"]):
            status = S_ELECTION
        elif tq is None:
            status = t13.S_NO_ROW
        else:
            b0, a0 = tq.bid, tq.ask
            age = t["ts"] - tq.recv
            row.update(bid0=b0, ask0=a0, spread0=a0 - b0 if t13.two_sided(b0, a0) else math.nan, mid0=(a0 + b0) / 2 if t13.two_sided(b0, a0) else math.nan, touch_recv=tq.recv,
                       touch_age_s=age, touch_cap=tq.cap, liq=tq.liq, end_epoch=tq.end, tick_touch=qi.tick_at(cid, tq.cap))
            if pq is not None and t13.two_sided(pq.bid, pq.ask):
                row.update(prev_mid=(pq.bid + pq.ask) / 2, prev_recv=pq.recv)
            if not t13.two_sided(b0, a0):
                status = t13.S_ONESIDED
            elif tq.closed or not tq.binary:
                status = t13.S_NOTBINARY
            elif age > t13.TOUCH_MAX_AGE_S:
                status = t13.S_STALE
            elif not (t13.MID_LO <= row["mid0"] <= t13.MID_HI):
                status = t13.S_MID
            elif row["spread0"] > t13.SPREAD_MAX + 1e-9:
                status = t13.S_SPREAD
            elif not (math.isfinite(tq.end) and tq.end >= t["ts"] + t13.END_MARGIN_S):
                status = t13.S_END
            else:
                kind, d, P = t13.classify_position(t["p_min"], t["p_max"], b0, a0)
                qs, ds = t13.stale_variant(t["p_vwap"], b0, a0)
                row.update(q_stale=qs, d_stale=ds)
                if kind == "inside":
                    status = t13.S_INSIDE
                elif kind == "inconsistent":
                    status = t13.S_INCONSISTENT
                else:
                    row.update(d=d, P=P)
            if status in (t13.S_INSIDE, t13.S_INCONSISTENT, t13.S_ONESIDED):
                xp = excluded_side_price(t, b0, a0)
                row.update(excl_P=xp, excl_g=grain_of(xp) if grain_eligible(xp, row["tick_touch"]) else -1)
        if status == S_FILL:
            row["g"] = grain_of(row["P"])
            row["grain_ok"] = int(grain_eligible(row["P"], row["tick_touch"]))
            row["u_ok"] = int(in_band(row["P"], U_P_BAND))
        row["status"] = status
        counts[status if not status.startswith(t13.S_KEY) else t13.S_KEY] += 1
        rows.append(row)
    return rows, dict(counts)


def is_primary(row: dict) -> bool:
    """A Q/U unit candidate: a touch-consistent fill outside the SPORTS-FEED class (``CB16_SPORTS_IN_PRIMARY = false``)."""
    return bool(row["status"] == S_FILL and (c16.CB16_SPORTS_IN_PRIMARY or row["label"] != lab.SPORTS))


def is_sports_arm(row: dict) -> bool:
    return bool(row["status"] == S_FILL and row["label"] == lab.SPORTS)


def both_grain_markets(rows: list[dict], *, sports: bool = False) -> set[str]:
    """Markets with at least one grain-eligible fill of EACH grain in the window (single-grain markets are counted and reported, never in the statistic); ``sports`` selects the reported
    sports arm instead of the primary."""
    seen: dict[str, set[int]] = {}
    for r in rows:
        if (is_sports_arm(r) if sports else is_primary(r)) and int(r["grain_ok"]) == 1:
            seen.setdefault(r["condition_id"], set()).add(int(r["g"]))
    return {c for c, s in seen.items() if s >= {0, 1}}


def write_fills(path: Path, rows: list[dict]) -> Path:
    c16.assert_clean_columns(FILL_COLUMNS)
    return c16.write_gz_csv(Path(path), FILL_COLUMNS, ([_fmt(r.get(c, math.nan)) for c in FILL_COLUMNS] for r in rows))


def _fmt(x):
    return "" if isinstance(x, float) and math.isnan(x) else x


_INTS = {"tx_id", "d", "touch_cap", "block", "d_stale", "n_fills", "clob_rewards", "hour", "g", "grain_ok", "u_ok", "excl_g", "politics", "wake", "spans_night", "s12_dropped", "n_prior", "n_prior3"}
_STRS = {"condition_id", "market_id", "event_id", "status", "label", "underlying", "path_key", "fee_type", "day", "neg_risk_market_id", "token0", "silence_status"}


def read_fills(path: Path) -> list[dict]:
    out = []
    for r in c13.read_csv_gz(Path(path)):
        row = {}
        for c in FILL_COLUMNS:
            v = r.get(c, "")
            if c in _STRS:
                row[c] = v
            elif c in _INTS:
                row[c] = int(float(v)) if v not in ("", None) else (-1 if c in ("g", "excl_g") else 0)
            else:
                row[c] = c13.num(v) if v not in ("", None) else math.nan
        out.append(row)
    return out


# =====================================================================================================================================================
# The reported shape descriptor (sweeps; reported only, never a test)
# =====================================================================================================================================================


def load_sweeps(sweep_root: Path | None, tokens: set[str], lo: float, hi: float) -> dict[str, list[tuple[float, dict]]]:
    """Sweep rows (whitelisted fields) of the wanted YES tokens with receipt in ``[lo, hi)``; floor-guarded. Missing root -> no coverage."""
    out: dict[str, list[tuple[float, dict]]] = {}
    if sweep_root is None or not Path(sweep_root).exists() or not tokens:
        return out
    c16.guard_floor(lo, "sweep window start")
    root = c16.refuse_path(Path(sweep_root), allow=("book_sweeps",))
    csv.field_size_limit(10**9)
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        f = d / "rows.csv.gz"
        if not f.is_file():
            continue
        c16.guard_sweep_file(f)
        with gzip.open(f, "rt", encoding="utf-8", newline="") as fh:
            rdr = csv.DictReader(fh)
            for r in rdr:
                tok = r.get("token_id") or ""
                if tok not in tokens:
                    continue
                t = c13.parse_iso(r.get("batch_receipt_utc"))
                if math.isfinite(t) and lo <= t < hi:
                    out.setdefault(tok, []).append((t, {k: r.get(k) for k in c16.SWEEP_FIELDS}))
    for v in out.values():
        v.sort(key=lambda x: x[0])
    return out


def add_shape(rows: list[dict], sweeps: dict[str, list[tuple[float, dict]]]) -> dict:
    """Per primary fill with a sweep row of its YES token received before ``tau`` and at most 2 h old: the touch size's share of the 1c depth on the lifted side, ``depth_5c /
    depth_1c`` and the level count of that side. Reported only."""
    n = cov = 0
    for r in rows:
        if not is_primary(r):
            continue
        n += 1
        lst = sweeps.get(r.get("token0") or "", [])
        j = bisect_left([x[0] for x in lst], r["tau"]) - 1
        if j < 0 or r["tau"] - lst[j][0] > SWEEP_MAX_AGE_S:
            continue
        sw = lst[j][1]
        side = "ask" if int(r["d"]) == -1 else "bid"
        s1, d1, d5, nl = (c16.num(sw.get(f"{side}_size_1")), c16.num(sw.get(f"depth_{side}_1c")), c16.num(sw.get(f"depth_{side}_5c")), c16.num(sw.get(f"n_{side}_levels")))
        r.update(sw_share=s1 / d1 if d1 and d1 > 0 else math.nan, sw_ratio=d5 / d1 if d1 and d1 > 0 else math.nan, sw_levels=nl, sw_age_s=r["tau"] - lst[j][0])
        cov += 1
    return {"primary_fills": n, "with_sweep": cov, "coverage_share": (cov / n) if n else math.nan}


# =====================================================================================================================================================
# The analysis dataset (screen / rep only) and the generic market fixed-effect analyser
# =====================================================================================================================================================


def build_dataset(fills: list[dict], qi) -> dict:
    """CB13-T's pinned ``build_dataset`` (marks, adverse-touch and worst-case marks, the pre-fill proxy) on the given fills, extended with the CB16 arrays: grain, eligibility, the
    mark-capture tick, the spread-free mark ``100 d (mid_h - mid_0)``, the silence state, hour of day and the both-grain flag."""
    D = t13.build_dataset(fills, qi)
    fs = [f for f in fills if f["status"] == S_FILL]
    bg = both_grain_markets(fs) | both_grain_markets(fs, sports=True)
    ext: dict[str, list] = {k: [] for k in ("g", "grain_ok", "u_ok", "tick_touch", "tick_mark", "hour", "x", "x3", "wake", "s", "spans_night", "silence_ok", "both_grain", "politics",
                                              "created", "sw_share", "sw_ratio", "sw_levels")}
    for f in fs:
        ext["g"].append(f["g"])
        ext["grain_ok"].append(f["grain_ok"])
        ext["u_ok"].append(f["u_ok"])
        ext["tick_touch"].append(f["tick_touch"])
        ext["tick_mark"].append(qi.tick_for(f, MARK_H["2-4h"]) if hasattr(qi, "tick_for") else math.nan)
        ext["hour"].append(f["hour"])
        ext["x"].append(f["x"])
        ext["x3"].append(f["x3"])
        ext["wake"].append(f["wake"])
        ext["s"].append(f["s"])
        ext["spans_night"].append(f["spans_night"])
        ext["silence_ok"].append(int(f["silence_status"] == "ok"))
        ext["both_grain"].append(int(f["condition_id"] in bg))
        ext["politics"].append(f["politics"])
        ext["created"].append(f["created_epoch"])
        ext["sw_share"].append(f["sw_share"])
        ext["sw_ratio"].append(f["sw_ratio"])
        ext["sw_levels"].append(f["sw_levels"])
    for k, v in ext.items():
        D[k] = np.asarray(v, dtype=float)
    for h in MARK_H:
        mid = (D[f"bid_{h}"] + D[f"ask_{h}"]) / 2 if len(fs) else np.array([])
        ok = np.isfinite(D[f"m_{h}"])
        D[f"sf_{h}"] = np.where(ok, 100.0 * D["d"] * (mid - D["mid0"]), math.nan) if len(fs) else np.array([])
    D["hs"] = 100.0 * D["d"] * (D["mid0"] - D["P"]) if len(fs) else np.array([])  # the realised half-spread against the touch
    D["block_s"] = D["block"].astype(int).astype(str) if len(fs) else np.array([], dtype=str)
    D["hour_s"] = D["hour"].astype(int).astype(str) if len(fs) else np.array([], dtype=str)
    return D


def ways_of(D: dict, idx: np.ndarray) -> dict:
    """The four declared ways (section 2.3): Gamma event; path key x 6-hour block; 6-hour block; UTC hour of day. UTC day is never in the max (leave-one-day-out binds)."""
    return {"event": D["event"][idx], "pathblock": D["pathblock"][idx], "block": D["block_s"][idx], "hour": D["hour_s"][idx]}


def make_fe(y: np.ndarray, X: np.ndarray, D: dict, *, j: int = 0, sign: float = 1.0, w: np.ndarray | None = None):
    """make_v(idx) -> (pseudo-values, estimate) of ``sign x`` the coefficient on column ``j`` of ``X`` in the market fixed-effect OLS of ``y`` on ``X`` over the rows ``idx``."""
    Xa = X if X.ndim == 2 else X[:, None]

    def f(idx: np.ndarray):
        v, b = c16.fe_coef_pseudo(y[idx], Xa[idx], D["cid"][idx], j, None if w is None else w[idx])
        return sign * v, (sign * b if math.isfinite(b) else math.nan)
    return f


def make_mean(m: np.ndarray, sign: float = 1.0):
    def f(idx: np.ndarray):
        x = sign * m[idx]
        return x, float(x.mean()) if len(x) else math.nan
    return f


def p_of(make_v, idx: np.ndarray, D: dict, *, alpha: float | None = None) -> dict:
    """The clustered result of one statistic on ``idx``: estimate and p (the max over the four ways under the CB10 small-G rule)."""
    if len(idx) < 2:
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False, "small_g_rules_hold": False}
    v, est = make_v(idx)
    if not math.isfinite(est) or np.isnan(v).any():
        return {"n": int(len(idx)), "est": math.nan, "p": 1.0, "testable": False, "small_g_rules_hold": False}
    r = c16.cluster_p(v, ways_of(D, idx), estimator=lambda keep: make_v(idx[keep])[1], alpha=alpha)
    return {"n": int(len(idx)), "est": float(est), "p": float(r["p"]), "testable": bool(r["testable"]), "small_g_rules_hold": bool(r.get("small_g_rules_hold", True)), "ways": r.get("ways")}


def est_only(make_v, idx: np.ndarray) -> float:
    return make_v(idx)[1] if len(idx) else math.nan


def analyse(make_v, idx: np.ndarray, D: dict, floor: float, *, loo: bool = True, top5: bool = True, alpha: float | None = None) -> dict:
    """Primary result plus the common binding checks (section 2.6): one-sided p < 0.01 and the floor; (ii) without the top 5 clusters of EACH way p < 0.01 and the floor hold; (iii)
    leave-one-day-out keeps p < 0.05 and the sign; the small-G leave-one-cluster-out sign rules."""
    base = p_of(make_v, idx, D, alpha=alpha)
    out = {**base, "floor": floor, "floor_ok": bool(math.isfinite(base["est"]) and base["est"] >= floor), "p_ok": c16.p_pass(base, c16.GATE_P)}
    if not base["testable"] or not math.isfinite(base["est"]):
        out.update(loo_day={"holds": False, "n_groups": 0}, top5={k: False for k in ("event", "pathblock", "block", "hour")})
        return out
    v, _ = make_v(idx)
    if loo:
        out["loo_day"] = c16.leave_one_out_p(D["day"][idx], lambda keep: make_v(idx[keep]), lambda _v, keep: p_of(make_v, idx[keep], D, alpha=c16.LOO_DAY_P)["p"], sign=1.0,
                                             p_max=c16.LOO_DAY_P)
    if top5:
        t5 = {}
        for name, cl in ways_of(D, idx).items():
            keep = c16.top_k_drop_mask(v, cl, c16.TOP_DROP)
            r = p_of(make_v, idx[keep], D, alpha=c16.GATE_P)
            t5[name] = bool(r["testable"] and r["p"] < c16.GATE_P and r["est"] >= floor)
        out["top5"] = t5
    return out


def not_testable(label: str) -> dict:
    return {"testable": False, "p": 1.0, "advance": False, "verdict": label, "est": None, "n": 0, "checks_ok": False}


def covariates(D: dict, idx: np.ndarray, *, extra: dict[str, np.ndarray] | None = None) -> tuple[np.ndarray, list[str]]:
    """The attribution covariates (section CB16-Q): touch-spread band, P band, size band, touch-age band, time-to-end band, reward band, 6-hour block of day (dummies), log capture
    liquidity, plus ``extra`` columns (U's ``x`` with a missing indicator for Q; ``g`` with a missing indicator for U)."""
    cols, names = [], []
    bands = {"spread": np.array([spread_band(s) for s in D["spread"]]), "pband": np.array([p_band(p) for p in D["P"]]), "size": np.array([size_band(c) for c in D["cash"]]),
             "age": np.array([age_band(a) for a in D["age"]]), "tte": np.array([tte_band(t) for t in D["tte"]]), "reward": D["rewards"].astype(int),
             "block_of_day": (D["block"].astype(int) % 4)}
    for key, arr in bands.items():
        a = arr[idx]
        for lv in sorted(set(a.tolist()))[1:]:
            cols.append((a == lv).astype(float))
            names.append(f"{key}{lv}")
    cols.append(np.log(np.maximum(D["liq"][idx], 1.0)))
    names.append("log_liq")
    for k, v in (extra or {}).items():
        cols.append(v[idx])
        names.append(k)
    return (np.column_stack(cols) if cols else np.zeros((len(idx), 0))), names


def attribution(D: dict, idx: np.ndarray, y: np.ndarray, main: np.ndarray, est: float, *, sign: float = 1.0, extra: dict[str, np.ndarray] | None = None,
                credit: str = LABEL_GRAIN, debit: str = LABEL_COMPOSITION) -> dict:
    """Market fixed-effect OLS of ``y`` on ``main`` plus the covariates: credit ``credit`` only if ``sign x`` the main coefficient keeps at least half of ``est``; else ``debit``."""
    C, names = covariates(D, idx, extra=extra)
    X = np.column_stack([main[idx], C]) if C.shape[1] else main[idx][:, None]
    ok = np.isfinite(y[idx]) & np.isfinite(X).all(axis=1)
    if ok.sum() < X.shape[1] + 5:
        return {"label": debit, "coef": math.nan, "reason": "too few rows"}
    beta = c16.fe_ols(y[idx][ok], X[ok], D["cid"][idx][ok])
    coef = float(sign * beta[0])
    return {"coef": coef, "est": est, "kept_share": coef / est if est else math.nan, "label": credit if (est > 0 and coef >= est / 2) else debit, "n": int(ok.sum()),
            "covariates": ["main", *names]}


def stratum_keys(*arrays) -> np.ndarray:
    return np.array(["|".join(str(a[i]) for a in arrays) for i in range(len(arrays[0]))]) if len(arrays[0]) else np.array([], dtype=str)


def permutation_placebo(D: dict, idx: np.ndarray, y: np.ndarray, label: np.ndarray, strata: np.ndarray, *, sign: float, n_draws: int, seed: int, note: str,
                        transform: Callable[[np.ndarray], np.ndarray] | None = None) -> dict:
    """A binding stratified permutation placebo: ``label`` (the regressor) permuted within ``strata`` over the rows ``idx`` (a value never moves across strata); each draw is judged on
    p < 0.01 alone (floors off); the advance rate must be <= 1.5%."""
    rng = np.random.default_rng(seed)
    ps: list[float | None] = []
    for _ in range(int(n_draws)):
        lab_ = label.astype(float).copy()
        lab_[idx] = c16.permute_within(label[idx].astype(float), strata[idx], rng)
        reg = transform(lab_) if transform is not None else lab_
        r = p_of(make_fe(y, reg, D, sign=sign), idx, D, alpha=c16.GATE_P)
        ps.append(r["p"] if r["testable"] else None)
    rate = c16.placebo_advance_rate(ps)
    return {**rate, "note": note, "seed": seed, "holds": bool(rate.get("advance_rate") is not None and rate["advance_rate"] <= c16.PLACEBO_MAX_ADVANCE)}


def strata_permutation_test(D: dict, idx: np.ndarray, y: np.ndarray, label: np.ndarray, strata: np.ndarray, observed: float, *, sign: float, n_draws: int, seed: int, note: str) -> dict:
    """The composition placebo (freeze-check amendment 2): ``label`` permuted within ``strata`` over ``idx`` ``n_draws`` times; each draw's coefficient (the same estimator and sign as the
    observed one) is compared with ``observed``. It HOLDS iff at most ``floor(1.5% x n_draws)`` (3 of 200) permuted coefficients reach the observed one; a non-finite permuted coefficient
    counts as reaching it (never in the placebo's favour)."""
    rng = np.random.default_rng(seed)
    reach = 0
    nonfinite = 0
    for _ in range(int(n_draws)):
        lab_ = label.astype(float).copy()
        lab_[idx] = c16.permute_within(label[idx].astype(float), strata[idx], rng)
        e = est_only(make_fe(y, lab_, D, sign=sign), idx)
        if not math.isfinite(e):
            nonfinite += 1
            reach += 1
        elif e >= observed:
            reach += 1
    max_reach = int(math.floor(c16.PLACEBO_MAX_ADVANCE * int(n_draws) + 1e-9))
    return {"rule": "within-strata permutation: holds iff permuted coefficients reaching the observed one <= floor(1.5% x draws)", "observed": float(observed), "n_draws": int(n_draws),
            "reached": int(reach), "max_reached": max_reach, "nonfinite_draws": int(nonfinite), "note": note, "seed": seed,
            "holds": bool(math.isfinite(observed) and int(n_draws) > 0 and reach <= max_reach)}


def prefill_placebo(D: dict, idx_pool: np.ndarray, reg: np.ndarray, *, sign: float) -> dict:
    """The binding pre-fill placebo: the same estimator with the outcome replaced by the pre-fill move (capture mid from the capture before the touch capture to the touch capture,
    signed by ``d``); it must NOT pass p < 0.01."""
    pf = idx_pool[np.isfinite(D["proxy"][idx_pool])]
    pr = p_of(make_fe(D["proxy"], reg, D, sign=sign), pf, D, alpha=c16.GATE_P)
    return {"p": pr["p"], "holds": bool((not pr["testable"]) or pr["p"] >= c16.GATE_P), "n": int(len(pf))}


# =====================================================================================================================================================
# Q1
# =====================================================================================================================================================


def arm_mask(D: dict, *, sports: bool = False) -> np.ndarray:
    """The primary arm (not SPORTS-FEED, unless ``CB16_SPORTS_IN_PRIMARY``) or the reported sports arm of an analysis dataset."""
    if not len(D.get("tx_id", [])):
        return np.zeros(0, bool)
    is_sp = np.asarray(D["label"]) == lab.SPORTS
    return is_sp if sports else (np.ones(len(is_sp), bool) if c16.CB16_SPORTS_IN_PRIMARY else ~is_sp)


def q_eligible(D: dict, *, sports: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """(eligible, tick-change) masks of the Q population: grain-eligible fills of the arm in both-grain markets; a 0.001 tick at the touch but another tick at the 2-4 h mark capture is
    'tick change' (excluded and counted)."""
    elig = (D["grain_ok"] == 1) & (D["both_grain"] == 1) & arm_mask(D, sports=sports)
    tick_change = elig & np.isfinite(D["tick_mark"]) & ~np.array([tick_is_grain(t) for t in D["tick_mark"]], dtype=bool)
    return elig & ~tick_change, tick_change


def q_strata(D: dict) -> np.ndarray:
    """Composition-placebo strata: market x touch-spread band x P band x transaction-size band."""
    return stratum_keys(D["cid"], [spread_band(s) for s in D["spread"]], [p_band(p) for p in D["P"]], [size_band(c) for c in D["cash"]])


def informative_share(g: np.ndarray, strata: np.ndarray, idx: np.ndarray) -> float:
    """The share of Q1's fills that lie in strata holding BOTH grains (the placebo's informativeness rule, round 1 item 4)."""
    if not len(idx):
        return math.nan
    s, gg = strata[idx], g[idx]
    both = {k for k in set(s.tolist()) if len(set(gg[s == k].tolist())) == 2}
    return float(np.mean([x in both for x in s]))


def q1_test(D: dict, *, n_draws: int = c16.PLACEBO_DRAWS, rep: bool = False, x_frozen_sd: float | None = None) -> dict:
    """Q1 (within-market grain contrast): ``beta_Q`` = the coefficient on ``g`` in a market fixed-effect OLS of ``M_2-4h`` (unweighted), one-sided > 0, floor +0.5c. Binding: the
    composition placebo (primary; FAILS below 50% of fills in both-grain strata), the within-market calibration placebo, the pre-fill placebo, the spread-free mark (sign, half of beta_Q
    and p < 0.05), robustness (touch age <= 20 min, 6-8 h, adverse-touch mark, tx < $10k, each side, market-weighted, P in [0.10, 0.90], reward bands >= 300 each, top-5 of every way,
    leave-one-day-out p < 0.05) and availability; labels: attribution ("quoter grain") and the tight-touch stratum."""
    elig, tick_change = q_eligible(D)
    m = D["m_2-4h"]
    idx = np.where(elig & np.isfinite(m))[0]
    av = c16.availability(len(idx), int(elig.sum()))
    base_info = {"availability": av, "tick_change": int(tick_change.sum()), "rep": rep}
    if not av["ok"]:
        return {**not_testable(c16.AVAILABILITY_LABEL), **base_info}
    g = D["g"].astype(float)
    mk = make_fe(m, g, D)
    res = {**analyse(mk, idx, D, Q1_FLOOR), **base_info}
    res["grains"] = {"bot": int((g[idx] == 1).sum()), "human": int((g[idx] == 0).sum()), "markets": len(set(D["cid"][idx].tolist())), "events": len(set(D["event"][idx].tolist()))}
    if not res["testable"]:
        res.update(advance=False, checks_ok=False, verdict="not testable (population / clusters)")
        return res
    est = res["est"]
    xm = np.where(np.isfinite(D["x"]), D["x"] / (x_frozen_sd or 1.0), 0.0)
    res["attribution"] = attribution(D, idx, m, g, est, extra={"x": xm, "x_missing": (~np.isfinite(D["x"])).astype(float)})
    strata = q_strata(D)
    share = informative_share(g, strata, idx)
    comp = strata_permutation_test(D, idx, m, g, strata, est, sign=1.0, n_draws=n_draws, seed=c16.PLACEBO_SEEDS["Q1_composition"],
                                   note="Q1 composition placebo (g permuted within market x spread band x P band x size band; coefficient permutation test)")
    comp["informative_share"] = share
    comp["informative"] = bool(math.isfinite(share) and share >= INFORMATIVE_SHARE)
    if not comp["informative"]:
        comp.update(holds=False, label=LABEL_UNINFORMATIVE)
    res["composition_placebo"] = comp
    res["calibration_placebo"] = permutation_placebo(D, idx, m, g, np.asarray(D["cid"]).astype(str), sign=1.0, n_draws=n_draws, seed=c16.PLACEBO_SEEDS["Q1_calibration"],
                                                     note="Q1 within-market calibration placebo (g permuted within market)")
    res["prefill_placebo"] = prefill_placebo(D, np.where(elig)[0], g, sign=1.0)
    isf = np.where(elig & np.isfinite(D["sf_2-4h"]))[0]
    sf = analyse(make_fe(D["sf_2-4h"], g, D), isf, D, -math.inf, loo=False, top5=False, alpha=None)
    sf_ok = bool(sf["testable"] and math.isfinite(sf["est"]) and sf["est"] > 0 and sf["est"] >= est / 2 and c16.p_pass(sf, SPREAD_FREE_P))
    res["spread_free"] = {"est": sf["est"], "p": sf["p"], "n": sf["n"], "holds": sf_ok, "label": None if sf_ok else LABEL_HALFSPREAD}
    tight = idx[(D["age"][idx] <= TIGHT_AGE_S) & (D["spread"][idx] <= TIGHT_SPREAD + 1e-9)]
    tb = {c for c in set(D["cid"][tight].tolist()) if len(set(g[tight][D["cid"][tight] == c].tolist())) == 2}
    tight = tight[np.array([c in tb for c in D["cid"][tight]], dtype=bool)] if len(tight) else tight
    te = est_only(mk, tight) if len(tight) >= TIGHT_MIN_FILLS else math.nan
    res["tight_touch"] = {"n": int(len(tight)), "est": te, "known": bool(len(tight) >= TIGHT_MIN_FILLS), "keeps_sign": bool(math.isfinite(te) and te > 0)}
    rob: dict[str, bool | None] = {}
    rob["age_le_20m"] = est_only(mk, idx[D["age"][idx] <= TIGHT_AGE_S]) > 0
    i68 = np.where(elig & np.isfinite(D["m_6-8h"]))[0]
    rob["mark_6_8h"] = est_only(make_fe(D["m_6-8h"], g, D), i68) > 0
    ia = np.where(elig & np.isfinite(D["adv_2-4h"]))[0]
    rob["adverse_touch_mark"] = est_only(make_fe(D["adv_2-4h"], g, D), ia) > 0
    rob["tx_lt_10k"] = est_only(mk, idx[D["cash"][idx] < BIG_TX_USD]) > 0
    rob["side_maker_sells"] = est_only(mk, idx[D["d"][idx] == -1]) > 0
    rob["side_maker_buys"] = est_only(mk, idx[D["d"][idx] == 1]) > 0
    w = np.zeros(len(m))
    cnt = Counter(D["cid"][idx].tolist())
    w[idx] = [1.0 / cnt[c] for c in D["cid"][idx]]
    rob["market_weighted"] = est_only(make_fe(m, g, D, w=w), idx) > 0
    rob["p_10_90"] = est_only(mk, idx[(D["P"][idx] >= P_ROBUST_BAND[0] - 1e-12) & (D["P"][idx] <= P_ROBUST_BAND[1] + 1e-12)]) > 0
    for nm, sel in (("reward_band", D["rewards"][idx] == 1), ("no_reward_band", D["rewards"][idx] != 1)):
        rob[nm] = (est_only(mk, idx[sel]) > 0) if sel.sum() >= REWARD_MIN_FILLS else None  # None = stratum below 300 fills: not evaluated
    res["robustness"] = rob
    res["robust_ok"] = bool(all(v for v in rob.values() if v is not None) and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["checks_ok"] = bool(res["floor_ok"] and res["small_g_rules_hold"] and comp["holds"] and res["calibration_placebo"]["holds"] and res["prefill_placebo"]["holds"] and sf_ok
                            and res["robust_ok"])  # every binding check but the primary p gate
    res["advance"] = c16.stage1_advance(res["p"] if res["testable"] else None, res["checks_ok"])
    labels = [LABEL_UPPER]
    if not comp["informative"]:
        labels.append(LABEL_UNINFORMATIVE)
    if not sf_ok:
        labels.append(LABEL_HALFSPREAD)
    grain_label = res["attribution"]["label"]
    if grain_label == LABEL_GRAIN and not res["tight_touch"]["keeps_sign"]:
        grain_label = LABEL_SPREAD_STATE
    res["grain_label"] = grain_label
    res["labels"] = labels
    res["verdict"] = ("advance" if res["advance"] else "no advance") + (f"; {grain_label}" if res["advance"] else "")
    return res


def q_gate_gq(rows: list[dict]) -> dict:
    """GQ (section 2.3): >= 1,000 eligible fills in markets with both grains, in >= 100 such markets and >= 60 events (features only)."""
    bg = both_grain_markets(rows)
    fs = [r for r in rows if is_primary(r) and int(r["grain_ok"]) == 1 and r["condition_id"] in bg]
    out = {"fills": len(fs), "markets": len({r["condition_id"] for r in fs}), "events": len({r["event_id"] for r in fs})}
    out["pass"] = all(out[k] >= GQ_MIN[k] for k in GQ_MIN)
    return out


def ways_rows(rows: list[dict]) -> dict:
    return {"event": np.array([r["event_id"] for r in rows]), "pathblock": np.array([f"{r['path_key']}|{r['block']}" for r in rows]),
            "block": np.array([str(r["block"]) for r in rows]), "hour": np.array([str(r["hour"]) for r in rows])}


def power_se(rows: list[dict], reg: np.ndarray, *, sign: float = 1.0) -> dict:
    """GQP / GUP on the PRE-FILL PROXY outcome: the test's own estimator (market fixed-effect coefficient) and ways; ONLY the clustered SE (max over ways) and the MDE are returned, never
    a proxy point estimate."""
    y = np.array([100.0 * r["d"] * (r["mid0"] - r["prev_mid"]) for r in rows]) if rows else np.array([])
    ok = np.isfinite(y) & np.isfinite(reg) if len(rows) else np.array([], dtype=bool)
    if ok.sum() < 4:
        return {"se": math.nan, "mde": math.nan, "pass": False, "n": int(ok.sum())}
    cid = np.array([r["condition_id"] for r in rows])[ok]
    v, _ = c16.fe_coef_pseudo(y[ok], reg[ok], cid)
    se = c16.max_se_over_ways(sign * v, {k: a[ok] for k, a in ways_rows(rows).items()}) if np.isfinite(v).all() else math.nan
    m = c16.mde(se)
    return {"se": se, "mde": m, "pass": bool(math.isfinite(m) and m <= POWER_MDE_MAX), "n": int(ok.sum())}


def q_power(rows: list[dict]) -> dict:
    bg = both_grain_markets(rows)
    fs = [r for r in rows if is_primary(r) and int(r["grain_ok"]) == 1 and r["condition_id"] in bg]
    return power_se(fs, np.array([float(r["g"]) for r in fs]))


def exclusion_by_grain(rows: list[dict]) -> dict:
    """Section CB16-Q (round 1 item 3): inside, inconsistent and one-sided rates BY GRAIN among grain-eligible transactions (the grain of ``P_min`` above the touch mid, of ``P_max``
    below it). The no-mark rate by grain is added by the screen."""
    out = {}
    for gname, gv in (("bot", 1), ("human", 0)):
        fills = sum(1 for r in rows if is_primary(r) and int(r["grain_ok"]) == 1 and int(r["g"]) == gv)
        ex = Counter(r["status"] for r in rows if r["label"] != lab.SPORTS and int(r["excl_g"]) == gv)
        tot = fills + sum(ex.values())
        out[gname] = {"fills": fills, "inside": ex.get(t13.S_INSIDE, 0), "inconsistent": ex.get(t13.S_INCONSISTENT, 0), "one_sided": ex.get(t13.S_ONESIDED, 0),
                      "rates": {k: (v / tot if tot else None) for k, v in (("inside", ex.get(t13.S_INSIDE, 0)), ("inconsistent", ex.get(t13.S_INCONSISTENT, 0)), ("one_sided", ex.get(t13.S_ONESIDED, 0)))}}
    return out


def beta_worst(D: dict, rows: list[dict]) -> dict:
    """The worst-case bound (round 1 item 3, modified): within each both-grain market, every excluded transaction of a grain (inside / inconsistent / one-sided, and eligible fills with
    no usable mark) is added at that grain's ADVERSE quantile of its included ``M`` (the 10th percentile for bot-grain, the 90th for human-grain); ``beta_Q,worst`` is the market
    fixed-effect contrast on the augmented data. A label, not a gate (point estimate only)."""
    elig, _ = q_eligible(D)
    m = D["m_2-4h"]
    idx = np.where(elig & np.isfinite(m))[0]
    if not len(idx):
        return {"beta_worst": None, "label": None}
    g = D["g"][idx]
    if not ((g == 1).any() and (g == 0).any()):
        return {"beta_worst": None, "label": None}
    q_bot = float(np.percentile(m[idx][g == 1], WORST_QUANTILE["bot"]))
    q_hum = float(np.percentile(m[idx][g == 0], WORST_QUANTILE["human"]))
    mk = set(D["cid"][idx].tolist())
    add_y, add_g, add_c = [], [], []
    for r in rows:
        if r["condition_id"] in mk and r["label"] != lab.SPORTS and int(r["excl_g"]) in (0, 1):
            add_y.append(q_bot if int(r["excl_g"]) == 1 else q_hum)
            add_g.append(int(r["excl_g"]))
            add_c.append(r["condition_id"])
    nomark = np.where(elig & ~np.isfinite(m))[0]
    for j in nomark:
        add_y.append(q_bot if D["g"][j] == 1 else q_hum)
        add_g.append(int(D["g"][j]))
        add_c.append(D["cid"][j])
    y = np.concatenate([m[idx], np.array(add_y, float)])
    gx = np.concatenate([g.astype(float), np.array(add_g, float)])
    cc = np.concatenate([D["cid"][idx], np.array(add_c, dtype=str)])
    _, b = c16.fe_coef_pseudo(y, gx, cc)
    return {"beta_worst": float(b) if math.isfinite(b) else None, "q10_bot": q_bot, "q90_human": q_hum, "n_added": len(add_y),
            "label": LABEL_EXCL if (math.isfinite(b) and b <= 0) else None}


def q_reported(D: dict, rows: list[dict]) -> dict:
    """Uncounted readings (point estimates; the stale-touch variant and the shape tercile split carry NO p-value and can never be promoted, round 1 item 8): beta_Q by LABELLER class
    and in the sports arm, the mark-out decomposition by grain, the exclusion-by-grain table with the no-mark rate and beta_Q,worst, the single-grain markets' mean M by grain, the
    stale-touch variant and the reduced shape descriptor."""
    out: dict = {}
    elig, _ = q_eligible(D)
    m = D["m_2-4h"]
    g = D["g"].astype(float)
    idx = np.where(elig & np.isfinite(m))[0]
    out["by_class"] = {c: est_only(make_fe(m, g, D), idx[D["label"][idx] == c]) for c in lab.CLASSES if (D["label"][idx] == c).sum() >= 2}
    es, _ = q_eligible(D, sports=True)
    isp = np.where(es & np.isfinite(m))[0]
    out["sports_arm"] = {"n": int(len(isp)), "est": est_only(make_fe(m, g, D), isp) if len(isp) > 3 else None, "note": "uncounted; a counted sports arm would be a later registration"}
    out["decomposition"] = {gn: {"n": int(sel.sum()), "M": float(np.nanmean(m[idx][sel])) if sel.any() else None, "spread_free": float(np.nanmean(D["sf_2-4h"][idx][sel])) if sel.any() else None,
                                 "half_spread": float(np.nanmean(D["hs"][idx][sel])) if sel.any() else None} for gn, sel in (("bot", g[idx] == 1), ("human", g[idx] == 0))}
    exc = exclusion_by_grain(rows)
    for gn, gv in (("bot", 1), ("human", 0)):
        sel = elig & (D["g"] == gv)
        exc[gn]["no_mark"] = int((sel & ~np.isfinite(m)).sum())
        exc[gn]["no_mark_rate"] = float((sel & ~np.isfinite(m)).sum() / sel.sum()) if sel.sum() else None
    out["exclusion_by_grain"] = exc
    out["worst_case"] = beta_worst(D, rows)
    single = (D["grain_ok"] == 1) & (D["both_grain"] == 0) & np.isfinite(m) & arm_mask(D)
    out["single_grain_markets"] = {gn: {"n": int((single & (D["g"] == gv)).sum()), "mean_M": float(m[single & (D["g"] == gv)].mean()) if (single & (D["g"] == gv)).any() else None}
                                   for gn, gv in (("bot", 1), ("human", 0))}
    tq = np.where(D["d"] == -1, D["ask0"] if "ask0" in D else np.nan, np.nan)
    _ = tq
    stale_q, stale_d = D["stale_q"], D["stale_d"]
    mids = (D["bid_2-4h"] + D["ask_2-4h"]) / 2
    ms = 100.0 * stale_d * (mids - stale_q)
    gs = np.array([grain_of(q) for q in stale_q], float)
    ist = np.where((D["grain_ok"] == 1) & np.isfinite(ms) & (gs >= 0) & (stale_d != 0))[0]
    out["stale_touch_variant"] = {"n": int(len(ist)), "est": est_only(make_fe(ms, gs, D), ist), "p_value": None, "note": "point estimate only; never a test, trigger or Stage-2 object"}
    shp = idx[np.isfinite(D["sw_share"][idx])]
    terc = {}
    if len(shp) >= 3:
        cuts = np.percentile(D["sw_share"][shp], [100 / 3, 200 / 3])
        tt = np.digitize(D["sw_share"][shp], cuts)
        for k in range(3):
            sel = shp[tt == k]
            terc[str(k)] = {"n": int(len(sel)), "mean_M_within_market": float(c16.fe_demean(m[sel], D["cid"][sel]).mean() + 0.0) if len(sel) else None, "p_value": None}
    out["shape_descriptor"] = {"coverage_share": float(len(shp) / len(idx)) if len(idx) else None, "share_terciles": terc, "note": "reported only; point estimates; no p-value"}
    return out


def q2_values(D: dict, idx: np.ndarray, extra_exit: float = 0.0) -> np.ndarray:
    """Q2 net per filled share (cents): CB13-T3's pinned round trip (maker entry at the recorded print P, maker fee 0; taker exit at the adverse touch of the 2-4 h mark capture with
    fee ``r x (1 - x)``, unknown rate -> 0.07), minus ``extra_exit``."""
    return t13.t3_values(D, idx, extra_exit)


def q2_worst(D: dict, idx: np.ndarray) -> np.ndarray:
    """The Q2 worst case: wide-mark and closed-before-mark units at the adverse extreme (``d (Y_adv - P)``, no exit fee at 0 / 1); a missing adverse exit at the adverse extreme too."""
    net = q2_values(D, idx)
    st = D["st_2-4h"][idx]
    for k, j in enumerate(idx):
        if st[k] in ("wide", "closed_absent") or (st[k] in ("ok", "onesided") and not math.isfinite(net[k])):
            net[k] = t13.worst_value(int(D["d"][j]), float(D["P"][j]))
    return net


def q2_test(D: dict) -> dict:
    """Q2 (economic, Stage 2; triggered by Q1; the pooled GAI PASS is checked by the caller): bot-grain REP_A fills, one-sided net > 0, floor +0.5c, robustness +0.5c on the exit keeps
    net > 0, the worst case keeps p < 0.01; position min(print size, 100) shares (recorded; per-share net)."""
    elig, tick_change = q_eligible(D)
    elig = (D["grain_ok"] == 1) & (D["g"] == 1) & ~tick_change & arm_mask(D)
    idx_all = np.where(elig)[0]
    net = np.full(len(D["tx_id"]), math.nan)
    net[idx_all] = q2_values(D, idx_all)
    ok = np.where(np.isfinite(net))[0]
    av = c16.availability(len(ok), int(elig.sum()))
    if not av["ok"]:
        return {**not_testable(c16.AVAILABILITY_LABEL), "availability": av}
    res = analyse(make_mean(net), ok, D, Q2_FLOOR)
    res["availability"] = av
    sizes = np.asarray(D["size"], float)[ok]
    res["position"] = {"max_shares": Q2_MAX_SIZE, "n_clipped": int((sizes > Q2_MAX_SIZE).sum()), "mean_position_shares": float(np.minimum(sizes, Q2_MAX_SIZE).mean()) if len(sizes) else None,
                       "note": "per-filled-share net; position = min(print size, 100); exit depth unknown"}
    if not res["testable"]:
        res.update(advance=False, checks_ok=False, verdict="not testable (population / clusters)", label=LABEL_Q2)
        return res
    n2 = np.full(len(D["tx_id"]), math.nan)
    n2[idx_all] = q2_values(D, idx_all, Q2_EXIT_ROBUST)
    rob = bool(est_only(make_mean(n2), np.where(np.isfinite(n2))[0]) > 0)
    wc = np.full(len(D["tx_id"]), math.nan)
    wc[idx_all] = q2_worst(D, idx_all)
    iw = np.where(np.isfinite(wc))[0]
    wr = p_of(make_mean(wc), iw, D, alpha=c16.GATE_P)
    res["robustness"] = {"exit_plus_0_5c_net_positive": rob, "worst_case_p_lt_001": c16.p_pass(wr, c16.GATE_P)}
    res["worst_case"] = {k: wr.get(k) for k in ("est", "p", "n")}
    res["checks_ok"] = bool(res["floor_ok"] and res["small_g_rules_hold"] and rob and res["robustness"]["worst_case_p_lt_001"] and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["label"] = LABEL_Q2
    res["verdict"] = "checks ok" if res["checks_ok"] else "checks fail"
    return res


# =====================================================================================================================================================
# GQG (q0382; pre-freeze; features only) and GAI
# =====================================================================================================================================================


def gate_gqg(rows: list[dict]) -> dict:
    """GQG on CB13-T's SCREEN window (features only; the mark-capture tick is not read): among eligible non-sports fills (tick 0.001 at the touch capture, ``P in [0.05, 0.95]``) the
    sub-cent share lies in [5%, 95%] AND at least 40% of eligible fills lie in both-grain markets."""
    fs = [r for r in rows if is_primary(r) and int(r["grain_ok"]) == 1]
    n = len(fs)
    sub = sum(1 for r in fs if int(r["g"]) == 1)
    bg = both_grain_markets(rows)
    inb = sum(1 for r in fs if r["condition_id"] in bg)
    share = sub / n if n else math.nan
    both = inb / n if n else math.nan
    ok = bool(n and GQG_SUB_SHARE[0] <= share <= GQG_SUB_SHARE[1] and both >= GQG_BOTH_SHARE)
    by_tick = dict(Counter(f"{r['tick_touch']}" for r in rows if is_primary(r)))
    by_band = dict(Counter(p_band(r["P"]) for r in fs))
    return {"eligible_fills": n, "sub_cent": sub, "sub_share": share, "both_grain_markets": len(bg), "fills_in_both_grain_markets": inb, "both_grain_share": both, "pass": ok,
            "by_touch_tick": by_tick, "by_p_band": by_band, "counts_only": True}


def gate_gai(fills: list[dict], D: dict, txs: list[dict]) -> dict:
    """GAI (cadence informativeness, as CB13 GTI measured from ``P``): CB13-T's pinned ``gate_gti`` on the A fills; later prints are read from the same window only."""
    if not len(D.get("tx_id", [])):
        return {"pairs": 0, "agree": 0, "agree_share": math.nan, "evaluable": False, "pass": False, "not_evaluable_label": LABEL_CADENCE}
    return t13.gate_gti(fills, D, txs)


def gai_pooled(screen: dict | None, rep: dict) -> dict:
    pairs = int((screen or {}).get("pairs", 0) or 0) + int(rep.get("pairs", 0) or 0)
    agree = int((screen or {}).get("agree", 0) or 0) + int(rep.get("agree", 0) or 0)
    return {"pairs": pairs, "agree": agree, "agree_share": (agree / pairs) if pairs else math.nan, "evaluable": pairs >= GAI_MIN_PAIRS, "pass": bool(pairs >= GAI_MIN_PAIRS and agree / pairs > GAI_AGREE)}


# =====================================================================================================================================================
# REP_A event-disjointness
# =====================================================================================================================================================


def drop_screen_events(rep_rows: list[dict], screen_events: set[str]) -> tuple[list[dict], dict]:
    """REP_A drops every Gamma event with a SCREEN_A fill (CB13-T's pinned rule; status rewritten, never deleted), binding even if thinned; > 40% of REP_A fills dropped -> label."""
    tot = sum(1 for r in rep_rows if is_primary(r))
    out, rep = t13.drop_screen_events(rep_rows, screen_events)
    dropped = sum(rep["dropped_by_class"].values())
    share = dropped / tot if tot else 0.0
    return out, {**rep, "primary_fills_before": tot, "dropped": dropped, "dropped_share": share, "label": LABEL_REP_THIN if share > REP_THIN_SHARE else None}


# =====================================================================================================================================================
# Smoke (part A, no network): fixtures + the CB13 reproduction
# =====================================================================================================================================================


def independent_status(t: dict, row: dict | None, label: str) -> str:
    """CB16's OWN re-implementation of CB13-T's touch-consistency chain (written independently of ``cb13_t.make_fills`` / ``classify_position``; raw capture fields), used only by the
    smoke to reproduce the pinned function's counts (round 1 item 16)."""
    if row is None:
        return t13.S_NO_ROW
    b, a = row["bid"], row["ask"]
    if not (math.isfinite(b) and math.isfinite(a) and 0.0 < b < a < 1.0):
        return t13.S_ONESIDED
    if row["closed"] or not row["binary"]:
        return t13.S_NOTBINARY
    if t["ts"] - row["recv"] > 3600.0:
        return t13.S_STALE
    mid, spr = (a + b) / 2.0, a - b
    if mid < 0.03 or mid > 0.97:
        return t13.S_MID
    if spr > 0.10 + 1e-9:
        return t13.S_SPREAD
    if not (math.isfinite(row["end"]) and row["end"] >= t["ts"] + 10800.0):
        return t13.S_END
    if label == lab.UNKNOWN:
        return t13.S_UNKNOWN
    lo, hi = t["p_min"], t["p_max"]
    eps = 1e-9
    if lo >= a - eps and hi <= 2 * a - b + eps:
        return S_FILL
    if lo >= 2 * b - a - eps and hi <= b + eps:
        return S_FILL
    if lo > b + eps and hi < a - eps:
        return t13.S_INSIDE
    return t13.S_INCONSISTENT


def reproduction(trades_dir: Path, snap_root: Path, pin: dict) -> dict:
    """The CB13 reproduction (independent of q0271, round 1 item 16): on two consecutive CB13-T SCREEN captures and the prints between them, read from the RAW files through CB13's
    own guarded readers, the pinned ``cb13_t.make_fills`` (every print its own transaction) and ``independent_status`` give identical status counts. A missing raw file is a FAIL."""
    caps = c13.list_captures(Path(snap_root), "screen", pin)
    pair = t13.smoke_capture_pair(caps, pin)
    if pair is None:
        return {"pass": False, "reason": "no two consecutive CB13-T SCREEN captures inside the SCREEN print window (raw file missing?)"}
    c0, c1 = pair
    prints, _ = t13.screen_prints(Path(trades_dir), "screen", pin)
    between = [p for p in prints if c0["start"] < p["ts"] < c1["start"]]
    wanted = {p["condition_id"] for p in between}
    qi = t13.load_quote_index([c0, c1], wanted, "touch", "screen", pin)
    single, _ = t13.build_transactions(between, aggregate=False)
    _fills, pinned = t13.make_fills(single, qi)
    raw: dict[str, list[dict]] = {}
    side: dict[str, dict] = {}
    for meta in (c0, c1):
        for r in c13.iter_capture_rows(meta["dir"], wanted):
            raw.setdefault(r["condition_id"], []).append({"recv": c13.parse_iso(r["received_utc"]), "bid": c13.num(r.get("best_bid")), "ask": c13.num(r.get("best_ask")),
                                                         "closed": str(r.get("closed")).lower() == "true", "binary": str(r.get("binary")) == "1", "end": c13.parse_iso(r.get("end_date"))})
        for s in c13.iter_sidecar_rows(meta["dir"], wanted):
            side.setdefault(s["condition_id"], s)
    own: Counter = Counter()
    for t in single:
        rows_ = [x for x in raw.get(t["condition_id"], []) if x["recv"] < t["ts"]]
        row = max(rows_, key=lambda x: x["recv"]) if rows_ else None
        st = side.get(t["condition_id"], {})
        ft = st.get("fee_type") or t["ctx_fee_type"]
        label, _u = lab.classify(t["title"], t["slug"], ft, st.get("fee_category", ""), st.get("series_slugs", ""), t["ctx_category"], has_sidecar=bool(st))
        own[independent_status(t, row, label)] += 1
    keys = (S_FILL, t13.S_INSIDE, t13.S_INCONSISTENT, t13.S_ONESIDED)
    ok = bool(len(between) > 0 and dict(own) == dict(pinned))
    return {"pass": ok, "n_prints_between": len(between), "captures": [c0["capture_id"], c1["capture_id"]], "pinned_counts": dict(pinned), "independent_counts": dict(own),
            "compared": {k: [pinned.get(k, 0), own.get(k, 0)] for k in keys}}


def smoke_offline(ctx: dict) -> dict:
    """Part A smoke checks (no network): the CB13 pins, refusal fixtures (J4-R and CB13-T HOLDOUT rows on both edges, rows before the floor, REP_A rows before the seal, refused roots,
    the monitor's other files), forbidden fields, the grain parser, the global monitor-gap detector, the silence standardiser and the CB13 reproduction on raw files."""
    from . import cb16_u as u  # noqa: PLC0415

    out: dict = {"a_cb13_pins": {**c16.cb13_pins_ok(), "pass": c16.cb13_pins_ok()["ok"]}}
    s_a = c16.ep(c16.S_A_EARLIEST)
    refusals = [
        lambda: c16.guard_floor(c16.ep(c16.J4R_WINDOW[0])), lambda: c16.guard_floor(c16.ep(c16.J4R_WINDOW[1]) - 1),
        lambda: c16.guard_floor(c16.ep(c16.CB13_T_HOLDOUT[0])), lambda: c16.guard_floor(c16.ep(c16.CB13_T_HOLDOUT[1]) - 1),
        lambda: c16.guard_rep_unit(s_a + c16.WINDOW_S, s_a, rep_open=False), lambda: c16.guard_rep_unit(s_a + 2 * c16.WINDOW_S - 1, s_a, rep_open=False),
        lambda: c16.refuse_path(Path("x/surprise_live/a")), lambda: c16.refuse_path(Path("x/cross_venue_live/a"), allow=("cross_venue_live",)),
        lambda: c16.refuse_path(Path("x/e005/a")), lambda: c16.refuse_path(Path("x/e011/a")), lambda: c16.refuse_path(Path("x/trade_samples/a"), allow=("trade_samples",)),
        lambda: c16.refuse_path(Path("x/cb3_extract/a")), lambda: c16.refuse_path(Path("x/cb3_followup/a"), allow=("cb3_followup",)), lambda: c16.refuse_path(Path("x/h15_new/a")),
        lambda: c16.guard_monitor_file(Path("x/live_trades/alerts.jsonl")), lambda: c16.guard_monitor_file(Path("x/live_trades/scores-20261102.jsonl")),
        lambda: c16.guard_monitor_file(Path("x/live_trades/outcomes.jsonl")), lambda: c16.guard_monitor_file(Path("x/live_trades/wallets.jsonl")),
        lambda: c16.guard_monitor_file(Path("x/live_trades/stats.jsonl")), lambda: c16.require_output_root(Path("x/creative_batch13/a")),
    ]
    res = []
    for fn in refusals:
        try:
            fn()
            res.append(False)
        except Refused:
            res.append(True)
    try:
        res.append(c16.guard_floor(c16.ep(c16.LOOKBACK_FLOOR)) == c16.ep(c16.LOOKBACK_FLOOR))
        res.append(c16.guard_rep_unit(s_a + c16.WINDOW_S - 1, s_a, rep_open=False) == s_a + c16.WINDOW_S - 1)
    except Refused:
        res.append(False)
    out["a_refusals"] = {"pass": bool(all(res)), "checks": res}
    rec = {"ts": 1.0, "condition_id": "0xa", "outcome_index": 0, "price": 0.5, "size": 10, "cash": 5, "side": "BUY", "wallet_hash": "w", "ctx_chg_1h": 0.1, "recv_ts": 5, "key": "k",
           "tx16": "t", "title": "T", "slug": "s", "ctx_status": "x", "chg_1h": 0.2, "uma_resolution_statuses": "r"}
    w = c13.whitelist_print(rec)
    hook = lambda kv: {k: v for k, v in kv if k in _LOOKBACK_KEEP}  # noqa: E731
    lb = json.loads(json.dumps(rec), object_pairs_hook=hook)
    clean = bool(w and not any(k in w for k in c16.FORBIDDEN_PRINT_FIELDS)) and set(lb) <= set(_LOOKBACK_KEEP)
    out["a_forbidden_fields"] = {"pass": clean}
    yes = t13.yes_price({"price": 0.465, "outcome_index": 1})
    gp = [grain_of(0.535) == 1, grain_of(0.53) == 0, grain_of(0.53000000001) == 0, grain_of(yes) == 1, grain_eligible(0.05, 0.001), grain_eligible(0.95, 0.001),
          not grain_eligible(0.0499, 0.001), not grain_eligible(0.5, 0.01)]
    out["a_grain_parser"] = {"pass": bool(all(gp)), "checks": gp}
    out.update(u.smoke_silence_checks())
    try:
        out["a_cb13_reproduction"] = reproduction(Path(ctx["cb13_trades_dir"]), Path(ctx["cb13_snap_root"]), ctx["pin"])
    except (KeyError, OSError, Refused, NotNow) as exc:
        out["a_cb13_reproduction"] = {"pass": False, "error": f"{type(exc).__name__}: {exc}"[:200]}
    return out


def declared() -> dict:
    return {"family": "Q (CH131)", "fill": "CB13-T's pinned print-anchored rule (cb13_t.classify_position); no UNKNOWN exclusion; SPORTS-FEED out of the primary",
            "grain": {"rule": "g = 1 iff round(1000 P) mod 10 != 0", "tick": GRAIN_TICK, "tick_at": ["touch capture", "2-4 h mark capture (else 'tick change', excluded)"], "p_band": list(GRAIN_P_BAND)},
            "statistic": "market fixed-effect OLS of M_2-4h on g, one unit per fill, unweighted; one-sided > 0; floor +0.5c", "floor_cents": Q1_FLOOR,
            "ways": ["event", "path key x 6 h block", "6 h block", "UTC hour of day"], "loo_day": {"p_max": c16.LOO_DAY_P, "sign": True},
            "bands": {"spread": list(Q_SPREAD_EDGES), "p": list(Q_P_EDGES), "size": list(Q_SIZE_EDGES), "age_s": AGE_EDGE_S, "tte_s": list(TTE_EDGES_S)},
            "placebos": {"composition": {"strata": "market x spread band x P band x size band", "rule": "within-strata permutation test: holds iff <= 3 of 200 permuted coefficients reach the observed one", "seed": c16.PLACEBO_SEEDS["Q1_composition"], "informative_share": INFORMATIVE_SHARE},
                         "calibration": {"strata": "market", "seed": c16.PLACEBO_SEEDS["Q1_calibration"]}, "prefill": "pre-fill proxy must not pass p < 0.01",
                         "draws": c16.PLACEBO_DRAWS, "max_advance": c16.PLACEBO_MAX_ADVANCE},
            "spread_free": {"mark": "100 d (mid_h - mid_0)", "rule": "sign, >= half of beta_Q, one-sided p < 0.05", "p": SPREAD_FREE_P},
            "tight_touch": {"age_s": TIGHT_AGE_S, "spread": TIGHT_SPREAD, "min_fills": TIGHT_MIN_FILLS, "consequence": "label only"},
            "robustness": ["age <= 20 min", "6-8 h", "adverse-touch mark", "tx < $10k", "each side", "market-weighted", "P in [0.10, 0.90]", "reward bands (>= 300 each)", "top-5 of every way"],
            "worst_case": {"quantiles": WORST_QUANTILE, "consequence": "label"}, "gates": {"GQG": {"sub_share": list(GQG_SUB_SHARE), "both_grain_share": GQG_BOTH_SHARE}, "GQ": GQ_MIN,
                                                                                              "GQP_mde_max": POWER_MDE_MAX, "GAI": {"min_pairs": GAI_MIN_PAIRS, "agree": GAI_AGREE}},
            "q2": {"floor_cents": Q2_FLOOR, "exit_robust_cents": Q2_EXIT_ROBUST, "max_size": Q2_MAX_SIZE, "fee": "r x (1 - x), unknown 0.07 (CB13-T3)"},
            "rep": {"event_disjoint": True, "thin_share": REP_THIN_SHARE, "keep_variant": "reported only"},
            "keys": {"skip_runs": list(A_EXCL_SKIP_RUNS), "skip_re": A_EXCL_SKIP_RE}, "shape": {"sweep_max_age_s": SWEEP_MAX_AGE_S, "reported_only": True},
            "labels": {"upper": LABEL_UPPER, "q2": LABEL_Q2, "rep": LABEL_REP, "rt": LABEL_RT, "excl": LABEL_EXCL, "uninformative": LABEL_UNINFORMATIVE, "halfspread": LABEL_HALFSPREAD,
                       "grain": LABEL_GRAIN, "composition": LABEL_COMPOSITION, "spread_state": LABEL_SPREAD_STATE}}
