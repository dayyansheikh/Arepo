# ruff: noqa: E501
"""CB17-B window code (docs/research_lab/CREATIVE_BATCH_17.md section CB17-B; rules part ``B`` = ``cb17_rules_b``): the shared (token, pass) frame, the mark readers, the census
block, B1 (book age) and B2 (the breathing book), their Stage-2 replications and the econ lines.

Frame (q0406 SCREEN_8 arm 0; q0410 REP_8 arm 1): units are (token, pass) for the outcome-0 tokens of the sweep universe, non-sports by the sidecar rule, in the arm's events, with the
decision time in the window. Every eligibility rule uses the decision sweep and EARLIER rows only (the market's latest complete capture BEFORE the decision, the previous passes);
the mark passes are read for their availability status only (present and two-sided, spread, tick), never stored as a value in the frame. The screen (q0409) reads the mark values
from the raw sweeps / captures (mark rows only); the REP frame seals them in a raw mark table (no mark-out computed).
"""

from __future__ import annotations

import bisect
import math
import time
from array import array
from collections import Counter, deque
from pathlib import Path

import numpy as np

from . import cb13_t as t13
from . import cb17_census as cen
from . import cb17_common as c17
from . import cb17_pre as pre
from . import cb17_rules_b as rb
from . import cb17_wcommon as w
from . import cb17_win as win

Refused = c17.Refused

UNITS_NAME = "b_units.npz"
META_NAME = "b_meta.json.gz"
MARKS_NAME = "b_marks.npz"
FILL_AGES_NAME = "fill_ages.npz"
ST_OK, ST_NO, ST_WIDE, ST_TICK = 0, 1, 2, 3
ST_NAMES = {ST_OK: rb.MARK_OK, ST_NO: rb.NO_MARK, ST_WIDE: rb.WIDE_MARK, ST_TICK: rb.TICK_CHANGE}
STATE_CODE = {rb.STATE_FRESH: 0, rb.STATE_OLD: 1, rb.STATE_MID: 2}
B2_OK, B2_NO_S2, B2_SPLIT, B2_ONESIDED, B2_TOUCH, B2_DEPTH, B2_NIGHT, B2_END = 0, 1, 2, 3, 4, 5, 6, 7
B2_EXCL_NAMES = {B2_NO_S2: "no second sweep", B2_SPLIT: "split pass", B2_ONESIDED: "not two-sided at the second sweep", B2_TOUCH: "touch changed (B2)", B2_DEPTH: "no depth (B2)",
                 B2_NIGHT: "election night", B2_END: "end too near"}
SWEEP_LOAD = ("token_id", "market_id", "book_timestamp", "book_hash", "best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c",
              "n_bid_levels", "n_ask_levels", "tick_size", "state")
CAP_ROWS = ("market_id", "condition_id", "event_id", "end_date", "liquidity", "volume24hr", "neg_risk_market_id")
CAP_EXT = ("market_id", "fee_type", "fee_category", "clob_rewards", "series_slugs")
VOL_BAND_EDGES = (1000.0, 10000.0, 100000.0)  # attribution's volume24hr band (code choice, declared here): < $1k, $1-10k, $10-100k, >= $100k
MARK2 = rb.MARK_2H_S
MARK6 = rb.MARK_6H_S
FLOAT_COLS = ("age", "b0", "a0", "tick1", "tick2", "act", "liq", "vol24", "lpre", "dmpre", "s", "x", "imb", "tsz_chg")
INT8_COLS = ("state", "act_t", "imb_t", "reward", "hchg", "grain", "tsz_same", "prt", "excl2", "st2_1", "st6_1", "st2_2", "st6_2")
INT16_COLS = ("nlev", "dnlev", "mk2_1", "mk6_1", "mk2_2", "mk6_2")
INT32_COLS = ("tok", "mkt", "ev", "path")
F64_COLS = ("t1", "t2")
READ_BACK_F64 = ("tick1", "tick2")  # read back while the frame is built (the tick-change comparison against the mark sweep's float64 tick): kept float64 until ``to_arrays`` casts them


# =====================================================================================================================================================
# readers
# =====================================================================================================================================================


def load_sweep(sdir: Path) -> dict:
    """One sweep -> {token: (market, receipt, book_ts_ms, hash, bid str, ask str, bid, ask, bs1, as1, db1, da1, db5, da5, n_bid, n_ask, tick, two-sided)}; whitelisted columns only."""
    out: dict[str, tuple] = {}
    for row in win.iter_rows(Path(sdir) / "rows.csv.gz", SWEEP_LOAD, c17.SWEEP_FIELDS, "batch_receipt_utc"):
        tk, mk, bts, bh, bid_s, ask_s, bs1, as1, db1, da1, db5, da5, nb, na, tick, state, recv = row
        bid, ask = c17.num(bid_s), c17.num(ask_s)
        out[tk] = (mk, recv, c17.num(bts), bh, bid_s, ask_s, bid, ask, c17.num(bs1), c17.num(as1), c17.num(db1), c17.num(da1), c17.num(db5), c17.num(da5), c17.num(nb), c17.num(na),
                   c17.num(tick), state == cen.STATE_TWO_SIDED and t13.two_sided(bid, ask))
    return out


class MarketState:
    """Point-in-time market attributes from the captures: for each market the two latest capture states (time = the capture's LAST page ``received_utc``). ``at(m, t)`` returns the
    latest state with capture time < t (never a capture finishing at or after the decision)."""

    def __init__(self):
        self.cur: dict[str, tuple] = {}
        self.prev: dict[str, tuple] = {}
        self.n = 0

    def ingest(self, cdir: Path) -> float:
        rows: dict[str, list] = {}
        t_last = -math.inf
        for mk, cid, ev, end, liq, vol, nrm, t in win.iter_rows(Path(cdir) / "rows.csv.gz", CAP_ROWS, c17.CAPTURE_FIELDS, "received_utc"):
            t_last = max(t_last, t)
            rows[mk] = [ev, cen.ep_cached(end) if end else math.nan, c17.num(liq), c17.num(vol), nrm or "", cid, False, 0, "", "none"]
        for mk, ft, fc, rw, ss, t in win.iter_rows(Path(cdir) / "rows_ext.csv.gz", CAP_EXT, c17.SIDECAR_FIELDS, "received_utc"):
            t_last = max(t_last, t)
            r = rows.get(mk)
            if r is not None:
                r[6] = cen.is_sports_sidecar(ft, fc, ss)
                r[7] = 1 if str(rw or "") not in ("", "[]", "null") else 0
                r[8] = cen.lab.first_series_slug(ss) or ""
                r[9] = fc or "none"
        if not rows:
            return t_last
        for mk, r in rows.items():
            old = self.cur.get(mk)
            if old is not None:
                self.prev[mk] = old
            self.cur[mk] = (t_last, *r)
        self.n += 1
        return t_last

    def at(self, mk: str, t: float) -> tuple | None:
        """(capture time, event, end, liquidity, volume24hr, neg-risk market, condition id, sports, reward, first series slug, fee category) of the latest capture before ``t``."""
        c = self.cur.get(mk)
        if c is not None and c[0] < t:
            return c
        p = self.prev.get(mk)
        return p if p is not None and p[0] < t else None


def print_index(trades_dir: Path | None, lo: float, hi: float, stats: Counter) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Sorted print times per condition id and per market id (B2's 'no monitor print in the market between the two sweeps' robustness). Features: prints before the decision."""
    by_c: dict[str, list[float]] = {}
    by_m: dict[str, list[float]] = {}
    if trades_dir is None:
        stats["monitor_not_read"] += 1
        return {}, {}
    for ts, cid, mk in win.iter_monitor(trades_dir, lo, hi, stats):
        by_c.setdefault(cid, []).append(ts)
        if mk:
            by_m.setdefault(mk, []).append(ts)
    return {k: np.sort(np.asarray(v)) for k, v in by_c.items()}, {k: np.sort(np.asarray(v)) for k, v in by_m.items()}


def _any_between(arr: np.ndarray | None, a: float, b: float) -> bool:
    if arr is None or not len(arr):
        return False
    i = int(np.searchsorted(arr, a, side="right"))
    return bool(i < len(arr) and arr[i] <= b)


def subcent(s: str) -> bool:
    return bool(s and "." in s and len(s.split(".")[1].rstrip("0")) > 2)


def mark_status(r: tuple | None, tick_dec: float) -> int:
    """Availability status of a mark-sweep row (no value is kept): absent or one-sided -> no mark; spread > 10c -> wide mark; another tick size -> tick change; else ok (rules B
    ``mark_status``)."""
    if r is None:
        return ST_NO
    st = rb.mark_status({"tick": tick_dec}, {"two_sided": r[17], "bid": r[6], "ask": r[7], "tick": r[16]})
    return {rb.MARK_OK: ST_OK, rb.NO_MARK: ST_NO, rb.WIDE_MARK: ST_WIDE, rb.TICK_CHANGE: ST_TICK}[st]


# =====================================================================================================================================================
# the frame (q0406 / q0410)
# =====================================================================================================================================================


def build_frame(sweep_root: Path, snap_root: Path, trades_dir: Path | None, *, units: tuple[float, float], read_lo: float, marks_hi: float, arm: int, drops: dict[str, str] | None = None,
                fill_needs: dict[str, list[float]] | None = None, budget_s: float | None = None, clock=time.monotonic) -> dict:
    """Stream the passes in time order (captures ingested before each pass; the market state of a unit is its latest capture BEFORE the decision). Returns the unit arrays, vocabularies,
    the pass list and the counts. ``fill_needs`` (REP econ only): token -> sorted fill times; the age of the token's latest sweep in [tau - 30 min, tau) is recorded per fill."""
    t0 = clock()
    stats: Counter = Counter()
    excl: Counter = Counter()
    drops = drops or {}
    floor = c17.ep(c17.LOOKBACK_FLOOR)
    sweeps = win.list_window_dirs(sweep_root, "book_sweeps", c17.SWEEP_DIR_RE, read_lo, marks_hi, stats)
    caps = win.list_captures(snap_root, max(read_lo - 4 * 3600.0, floor), units[1], stats)
    passes, lone = cen.pair_passes(sweeps)
    pr_c, pr_m = print_index(trades_dir, read_lo, units[1], stats)
    ms = MarketState()
    ci = 0
    V = {k: win.Vocab() for k in ("tok", "mkt", "ev", "path")}
    cols = new_columns()  # typed buffers, not python lists: about 1.4 M SCREEN_8 units must fit the job's memory (section 2.8)
    pending: deque = deque()  # (pass index, [unit indices])
    prev1 = prev2 = None  # (pass start, {tok: (mid, bid, ask, hash)})
    gbt: Counter = Counter()
    fill_age: dict[str, dict[float, tuple[float, float]]] = {}
    pass_list = []
    for pi, ((d1, ts1), (d2, _ts2)) in enumerate(passes):
        if budget_s is not None and clock() - t0 > budget_s:
            raise c17.NotNow(f"B frame unfinished after {pi} of {len(passes)} passes (budget); the job repeats from the start of the stage (pending)")
        while ci < len(caps) and caps[ci]["stamp"] < ts1:
            ms.ingest(caps[ci]["dir"])
            ci += 1
        s1, s2 = load_sweep(d1), load_sweep(d2)
        pass_list.append({"i": pi, "s1": d1.name, "s2": d2.name, "t": ts1})
        if fill_needs:
            for s in (s1, s2):
                for tk, r in s.items():
                    taus = fill_needs.get(tk)
                    if not taus:
                        continue
                    a = rb.book_age_s(r[1], r[2])
                    j = bisect.bisect_right(taus, r[1])  # fills with tau > receipt
                    while j < len(taus) and taus[j] - r[1] <= rb.ECON_B1_SWEEP_LOOKBACK_S:
                        rec = fill_age.setdefault(tk, {})
                        old = rec.get(taus[j])
                        if old is None or r[1] > old[0]:
                            rec[taus[j]] = (r[1], a)
                        j += 1
        # ---- resolve the pending marks against this pass's FIRST sweep (availability only) ----
        keep = deque()
        for (pj, ulist) in pending:
            for u in ulist:
                tk = V["tok"].items[cols["tok"][u]]
                r = s1.get(tk)
                if r is None:
                    continue
                for tcol, lo_hi, mkc, stc, tickc in (("t1", MARK2, "mk2_1", "st2_1", "tick1"), ("t1", MARK6, "mk6_1", "st6_1", "tick1"), ("t2", MARK2, "mk2_2", "st2_2", "tick2"),
                                                     ("t2", MARK6, "mk6_2", "st6_2", "tick2")):
                    t = cols[tcol][u]
                    if cols[mkc][u] >= 0 or not math.isfinite(t):
                        continue
                    dt = r[1] - t
                    if lo_hi[0] <= dt <= lo_hi[1]:
                        cols[mkc][u] = pi
                        cols[stc][u] = mark_status(r, cols[tickc][u])
            if ts1 - pass_list[pj]["t"] <= MARK6[1] + 3600.0:
                keep.append((pj, ulist))
        pending = keep
        # ---- units of this pass ----
        gap1 = ts1 - prev1[0] if prev1 else math.inf
        p1 = prev1[1] if prev1 and gap1 <= pre.PREV_PASS_MAX_GAP_S else None
        p2 = prev2[1] if p1 is not None and prev2 and (prev1[0] - prev2[0]) <= pre.PREV_PASS_MAX_GAP_S else None
        new_units = []
        for tk, r in s1.items():
            mk, t1 = r[0], r[1]
            if not (units[0] <= t1 < units[1]):
                continue
            st = ms.at(mk, t1)
            if st is None:
                stats["no_capture_before_decision"] += 1
                continue
            if st[7]:
                stats["sports_token_passes"] += 1
                continue
            evk = w.event_key(st[1], mk)
            if w.arm(evk) != arm:
                stats["other_arm_token_passes"] += 1
                continue
            age = rb.book_age_s(t1, r[2])
            state = rb.age_state(age)
            sb = state if state != rb.STATE_ANOMALY else "anomaly"
            r2 = s2.get(tk)
            # GBT counts (stamp semantics) on this arm's non-sports two-sided pairs in the window
            if r2 is not None and r[17] and r2[17] and abs(r2[1] - t1) <= pre.SPLIT_PASS_S:
                sh, stp = r[3] == r2[3], r[2] == r2[2]
                gbt["pairs"] += 1
                gbt["hash_same"] += sh
                gbt["hash_same_stamp_same"] += sh and stp
                gbt["hash_changed"] += not sh
                gbt["hash_changed_stamp_changed"] += (not sh) and (not stp)
            if state == rb.STATE_ANOMALY:
                excl[f"clock anomaly|{sb}"] += 1
                continue
            if not r[17]:
                excl[f"not two-sided|{sb}"] += 1
                continue
            bid, ask = r[6], r[7]
            spread, mid = ask - bid, (ask + bid) / 2.0
            if spread > pre.MAX_SPREAD + 1e-12 or not pre.MID_RANGE[0] <= mid <= pre.MID_RANGE[1]:
                excl[f"wide or extreme|{sb}"] += 1
                continue
            if math.isfinite(st[2]) and st[2] < t1 + pre.B_END_BUFFER_S:
                excl[f"end too near|{sb}"] += 1
                continue
            if win.in_night_span(t1):
                excl[f"election night|{sb}"] += 1
                continue
            src = win.key_drop(drops, mk, evk, st[5], st[6])
            if src:
                excl[f"dropped: key|{sb}"] += 1
                continue
            if p1 is None or tk not in p1:
                why = w.UNAVAILABLE_LOOKBACK if t1 - pre.PREV_PASS_MAX_GAP_S < floor else "no previous pass"  # the previous pass would lie before the floor: never read (finding 5)
                excl[f"{why}|{sb}"] += 1
                continue
            m1, _b1p, _a1p, h1p = p1[tk]
            act = abs(mid - m1) * 100.0
            lpre = math.nan
            if p2 is not None and tk in p2:
                _m2, b2p, a2p, _h2p = p2[tk]
                lpre = 100.0 * (max(0.0, m1 - a2p) + max(0.0, b2p - m1))
            elif t1 - 2 * pre.PREV_PASS_MAX_GAP_S < floor:
                stats["lpre_unavailable_lookback_floor"] += 1
            dmpre = (mid - m1) * 100.0
            # ---- B2 (decision at the SECOND sweep) ----
            ex2, x, s_, imb, t2, tick2, dnlev, tsz_chg, tsz_same, prt = B2_NO_S2, math.nan, math.nan, math.nan, math.nan, math.nan, 0, math.nan, 0, 0
            if r2 is not None:
                t2, tick2 = r2[1], r2[16]
                dnlev = int((r2[14] + r2[15]) - (r[14] + r[15])) if all(math.isfinite(v) for v in (r2[14], r2[15], r[14], r[15])) else 0
                tsz_chg = abs(r2[8] - r[8]) + abs(r2[9] - r[9]) if all(math.isfinite(v) for v in (r2[8], r2[9], r[8], r[9])) else math.nan
                tsz_same = int(math.isfinite(tsz_chg) and tsz_chg == 0)
                cid = st[6]
                prt = int(_any_between(pr_m.get(mk), t1, t2) or _any_between(pr_c.get(cid), t1, t2))
                if abs(t2 - t1) > pre.SPLIT_PASS_S:
                    ex2 = B2_SPLIT
                elif not r2[17]:
                    ex2 = B2_ONESIDED
                elif win.in_night_span(t2):
                    ex2 = B2_NIGHT
                elif math.isfinite(st[2]) and st[2] < t2 + pre.B_END_BUFFER_S:
                    ex2 = B2_END
                else:
                    sh = rb.shift_state({"bid_s": r[4], "ask_s": r[5], "db1": r[10], "da1": r[11], "db5": r[12], "da5": r[13]},
                                        {"bid_s": r2[4], "ask_s": r2[5], "db1": r2[10], "da1": r2[11], "db5": r2[12], "da5": r2[13]})
                    if sh is None:
                        ex2 = B2_TOUCH
                    elif not sh["ok"]:
                        ex2 = B2_DEPTH
                    else:
                        ex2, x, s_, imb = B2_OK, sh["x"], sh["s"], sh["imb"]
            if ex2 != B2_OK:
                excl[f"B2: {B2_EXCL_NAMES[ex2]}|{sb}"] += 1
            u = len(cols["tok"])
            vals = {"tok": V["tok"].code(tk), "mkt": V["mkt"].code(mk), "ev": V["ev"].code(evk), "path": V["path"].code(w.path_key(st[9], evk)), "t1": t1, "t2": t2, "age": age,
                    "b0": bid, "a0": ask, "tick1": r[16], "tick2": tick2, "act": rb.f32(act), "liq": st[3], "vol24": st[4], "lpre": lpre, "dmpre": dmpre, "s": s_, "x": x, "imb": imb,
                    "tsz_chg": tsz_chg, "state": STATE_CODE[state], "act_t": rb.activity_tercile(act), "imb_t": rb.imbalance_tercile(imb) if math.isfinite(imb) else -1,
                    "reward": int(st[8]), "hchg": int(h1p != r[3]), "grain": int(subcent(r[4]) or subcent(r[5])), "tsz_same": tsz_same, "prt": prt, "excl2": ex2,
                    "st2_1": ST_NO, "st6_1": ST_NO, "st2_2": ST_NO, "st6_2": ST_NO, "nlev": int(r[14] + r[15]) if math.isfinite(r[14] + r[15]) else -1, "dnlev": dnlev,
                    "mk2_1": -1, "mk6_1": -1, "mk2_2": -1, "mk6_2": -1}
            for k, v in vals.items():
                cols[k].append(v)
            new_units.append(u)
        if new_units:
            pending.append((pi, new_units))
        prev2, prev1 = prev1, (ts1, {tk: ((r[6] + r[7]) / 2.0, r[6], r[7], r[3]) for tk, r in s1.items() if r[17]})
    arrays = to_arrays(cols)
    return {"arrays": arrays, "vocab": {k: v.items for k, v in V.items()}, "passes": pass_list, "stats": dict(stats), "exclusions": dict(excl), "gbt": dict(gbt), "lone_sweeps": lone,
            "n_passes": len(passes), "n_captures": ms.n, "fill_ages": {tk: {str(t): list(v) for t, v in d.items()} for tk, d in fill_age.items()} if fill_needs else None}


def new_columns() -> dict[str, array]:
    """One typed ``array.array`` per frame column (int32 / float64 / float32 / int8 / int16): the same dtypes ``to_arrays`` produces, at their storage size while the frame is built."""
    cols: dict[str, array] = {}
    for names, code in ((INT32_COLS, "i"), (F64_COLS, "d"), (FLOAT_COLS, "f"), (INT8_COLS, "b"), (INT16_COLS, "h")):
        for k in names:
            cols[k] = array("d" if k in READ_BACK_F64 else code)
    return cols


def to_arrays(cols: dict[str, list]) -> dict[str, np.ndarray]:
    out = {}
    for k, v in cols.items():
        dt = np.int32 if k in INT32_COLS else np.float64 if k in F64_COLS else np.float32 if k in FLOAT_COLS else np.int8 if k in INT8_COLS else np.int16
        out[k] = np.asarray(v, dtype=dt)
    return out


def write_frame(out_dir: Path, fr: dict) -> list[Path]:
    a = win.write_arrays(Path(out_dir) / UNITS_NAME, fr["arrays"])
    meta = {k: fr[k] for k in ("vocab", "passes", "stats", "exclusions", "gbt", "lone_sweeps", "n_passes", "n_captures")}
    b = win.write_json_gz(Path(out_dir) / META_NAME, meta)
    return [a, b]


def load_frame(rdir: Path) -> dict:
    D = win.read_arrays(Path(rdir) / UNITS_NAME)
    meta = win.read_json_gz(Path(rdir) / META_NAME)
    return {**D, "_meta": meta}


# =====================================================================================================================================================
# mark values (q0409 from the raw files; q0410 sealed)
# =====================================================================================================================================================


MARK_KINDS = (("2h_b1", "mk2_1", "st2_1"), ("6h_b1", "mk6_1", "st6_1"), ("2h_b2", "mk2_2", "st2_2"), ("6h_b2", "mk6_2", "st6_2"))


def read_mark_values(sweep_root: Path, F: dict, *, read_lo: float, marks_hi: float) -> dict[str, np.ndarray]:
    """bid / ask of every unit's mark row (ok or wide only), read from the FIRST sweep of the recorded mark pass (whitelisted token, bid, ask). Returns ``{kind_bid, kind_ask}``."""
    stats: Counter = Counter()
    dirs = {d.name: d for d, _t in win.list_window_dirs(sweep_root, "book_sweeps", c17.SWEEP_DIR_RE, read_lo, marks_hi, stats)}
    toks = F["_meta"]["vocab"]["tok"]
    passes = F["_meta"]["passes"]
    n = len(F["tok"])
    out = {f"{k}_{s}": np.full(n, np.nan) for k, _m, _s in MARK_KINDS for s in ("bid", "ask")}
    need: dict[int, dict[str, list[tuple[str, int]]]] = {}
    for kind, mk, stc in MARK_KINDS:
        sel = np.nonzero((F[mk] >= 0) & np.isin(F[stc], (ST_OK, ST_WIDE)))[0]
        for u in sel:
            need.setdefault(int(F[mk][u]), {}).setdefault(toks[int(F["tok"][u])], []).append((kind, int(u)))
    for pi in sorted(need):
        name = passes[pi]["s1"]
        if name not in dirs:
            raise Refused(f"mark sweep {name} is not in the read window or missing (restore it byte for byte)")
        want = need[pi]
        for tk, bid, ask, _t in win.iter_rows(dirs[name] / "rows.csv.gz", ("token_id", "best_bid", "best_ask"), c17.SWEEP_FIELDS, "batch_receipt_utc"):
            for kind, u in want.get(tk, ()):
                out[f"{kind}_bid"][u], out[f"{kind}_ask"][u] = c17.num(bid), c17.num(ask)
    return out


def capture_marks(snap_root: Path, mkt_names: list[str], t: np.ndarray, *, lo: float, hi: float) -> np.ndarray:
    """The CB13 capture mark (finding 4 modification): the market's mid in the FIRST complete capture with last-page ``received_utc`` >= t + 2 h, usable iff <= t + 4 h; NaN when that
    capture lacks a two-sided row (no recorded price)."""
    stats: Counter = Counter()
    n = len(t)
    mid = np.full(n, np.nan)
    if not n:
        return mid
    order = np.argsort(t, kind="stable")
    ts = np.asarray(t, float)[order]
    assigned = np.zeros(n, bool)
    want = set(mkt_names)
    for cap in win.list_captures(snap_root, lo, hi, stats):
        mids: dict[str, float] = {}
        t_last = -math.inf
        for mk, bid, ask, tr in win.iter_rows(cap["dir"] / "rows.csv.gz", ("market_id", "best_bid", "best_ask"), c17.CAPTURE_FIELDS, "received_utc"):
            t_last = max(t_last, tr)
            if mk in want:
                b, a = c17.num(bid), c17.num(ask)
                if t13.two_sided(b, a):
                    mids[mk] = (a + b) / 2.0
        if not math.isfinite(t_last):
            continue
        i0 = int(np.searchsorted(ts, t_last - rb.CAPTURE_MARK_S[1], side="left"))
        i1 = int(np.searchsorted(ts, t_last - rb.CAPTURE_MARK_S[0], side="right"))
        sel = order[i0:i1]
        sel = sel[~assigned[sel]]
        assigned[sel] = True
        mid[sel] = [mids.get(mkt_names[u], math.nan) for u in sel]
    return mid


def mark_tables(sweep_root: Path, snap_root: Path, F: dict, *, read_lo: float, marks_hi: float) -> dict[str, np.ndarray]:
    """Every mark value B needs: the sweep marks (2 h, 6 h; B1 and B2 decision times) and the capture marks (B1 at t1, B2 at t2)."""
    mv = read_mark_values(sweep_root, F, read_lo=read_lo, marks_hi=marks_hi)
    mk = F["_meta"]["vocab"]["mkt"]
    names = [mk[int(i)] for i in F["mkt"]]
    lo = max(read_lo, c17.ep(c17.LOOKBACK_FLOOR))
    mv["cap_b1"] = capture_marks(snap_root, names, F["t1"], lo=lo, hi=marks_hi)
    t2 = np.where(np.isfinite(F["t2"]), F["t2"], np.inf)
    mv["cap_b2"] = capture_marks(snap_root, names, t2, lo=lo, hi=marks_hi)
    return mv


# =====================================================================================================================================================
# analysis dataset
# =====================================================================================================================================================


def dataset(F: dict) -> dict:
    """The analysis dict of a B frame: arrays plus the four ways and the UTC day (from the B1 decision time; B2 rows use t2 for their own ways)."""
    D = {k: v for k, v in F.items() if not k.startswith("_")}
    D["_meta"] = F["_meta"]
    D["mid0"] = (D["b0"].astype(float) + D["a0"].astype(float)) / 2.0
    D["spread"] = D["a0"].astype(float) - D["b0"].astype(float)
    return D


def with_ways(D: dict, t: np.ndarray) -> dict:
    E = dict(D)
    return win.set_ways(E, D["ev"], D["path"], t)


def l_from_mid(b0: np.ndarray, a0: np.ndarray, m: np.ndarray) -> np.ndarray:
    """B1's target ``L = 100 [max(0, m_h - a0) + max(0, b0 - m_h)]`` for vectors (rules B ``excursion_L``, vectorised; NaN where an input is missing)."""
    b0, a0, m = (np.asarray(v, float) for v in (b0, a0, m))
    out = 100.0 * (np.maximum(0.0, m - a0) + np.maximum(0.0, b0 - m))
    return np.where(np.isfinite(b0) & np.isfinite(a0) & np.isfinite(m), out, np.nan)


def l_of(b0: np.ndarray, a0: np.ndarray, bid: np.ndarray, ask: np.ndarray) -> np.ndarray:
    """``L`` from the mark row's mid ``(bid + ask) / 2``."""
    return l_from_mid(b0, a0, (np.asarray(bid, float) + np.asarray(ask, float)) / 2.0)


def bands_spread(sp: np.ndarray) -> np.ndarray:
    return np.array([pre.spread_band(float(s)) for s in sp])


def vol_band(v: float) -> int:
    if not math.isfinite(v):
        return -1
    return 0 if v < VOL_BAND_EDGES[0] else 1 if v < VOL_BAND_EDGES[1] else 2 if v < VOL_BAND_EDGES[2] else 3


def lev_band(n: float) -> int:
    if not math.isfinite(n) or n < 0:
        return -1
    return 0 if n <= pre.LEVEL_BAND_EDGES[0] else 1 if n <= pre.LEVEL_BAND_EDGES[1] else 2


# =====================================================================================================================================================
# census block (q0408: counts, shares and SEs only)
# =====================================================================================================================================================


def sd_x_of(D: dict) -> float:
    """``SD_x``: the pooled SD of x over the SCREEN_8 B2 units (a feature; frozen for REP_8)."""
    m = (D["excl2"] == B2_OK) & np.isfinite(D["x"])
    return float(np.std(D["x"][m].astype(float))) if m.sum() > 1 else math.nan


def b1_sample(D: dict) -> np.ndarray:
    return (D["state"] <= 1) & (D["st2_1"] != ST_TICK)


def b2_sample(D: dict) -> np.ndarray:
    return (D["excl2"] == B2_OK) & np.isfinite(D["x"]) & (D["st2_2"] != ST_TICK)


def census(F: dict) -> dict:
    """GBT, GBA, GBS, GB1P, GB2P (SEs only), the informativeness shares at the selected levels, the no-mark shares (B1 by age bin, B2 by x sign and |x| quintile), exclusions."""
    D = dataset(F)
    meta = F["_meta"]
    g = meta["gbt"]
    gbt = rb.gate_gbt(g.get("hash_same", 0), g.get("hash_same_stamp_same", 0), g.get("hash_changed", 0), g.get("hash_changed_stamp_changed", 0))
    n = len(D["tok"])
    old, fresh = D["state"] == 1, D["state"] == 0
    tok_both = set(D["tok"][old].tolist()) & set(D["tok"][fresh].tolist())
    ev_both = {int(e) for t_, e in zip(D["tok"].tolist(), D["ev"].tolist(), strict=True) if t_ in tok_both}
    gba = rb.gate_gba(int(old.sum()), int(fresh.sum()), n, len(tok_both), len(ev_both))
    tu = D["excl2"] == B2_OK
    shifted = tu & np.isfinite(D["s"]) & (D["s"] != 0)
    gbs = rb.gate_gbs(int(tu.sum()), int(shifted.sum()), len(set(D["ev"][shifted].tolist())))
    sd_x = sd_x_of(D)
    s1 = b1_sample(D)
    D1 = with_ways(D, D["t1"])
    i1 = np.nonzero(s1 & np.isfinite(D["lpre"]))[0]
    se1 = pre.fe_cluster_se(D["lpre"][i1].astype(float).tolist(), old[i1].astype(float).tolist(), D["tok"][i1].tolist(), {k: D1[f"way_{k}"][i1].tolist() for k in w.WAYS}) if len(i1) else {"n": 0, "se": None}
    s2 = b2_sample(D)
    D2 = with_ways(D, np.where(np.isfinite(D["t2"]), D["t2"], D["t1"]))
    i2 = np.nonzero(s2 & np.isfinite(D["dmpre"]))[0] if math.isfinite(sd_x) and sd_x > 0 else np.array([], dtype=int)
    se2 = pre.fe_cluster_se(D["dmpre"][i2].astype(float).tolist(), (D["x"][i2].astype(float) / sd_x).tolist(), D["tok"][i2].tolist(), {k: D2[f"way_{k}"][i2].tolist() for k in w.WAYS}) if len(i2) else {"n": 0, "se": None}
    st1 = rb.STRATA_LEVEL["B1"]
    info1 = pre.informativeness("B1", (((int(D["tok"][i]), (int(D["act_t"][i]),)), int(D["state"][i])) for i in np.nonzero(s1)[0]))
    info2 = pre.informativeness("B2", (((int(D["tok"][i]), (int(D["act_t"][i]), int(D["imb_t"][i]))), float(D["x"][i])) for i in np.nonzero(s2)[0]))
    nm1 = {}
    for code, name in ((0, "fresh"), (1, "old"), (2, "mid")):
        m = D["state"] == code
        nm1[name] = {ST_NAMES[k]: int(((D["st2_1"] == k) & m).sum()) for k in ST_NAMES}
    nm2 = {}
    if s2.any() or (D["excl2"] == B2_OK).any():
        base = (D["excl2"] == B2_OK) & np.isfinite(D["x"])
        xs = D["x"].astype(float)
        nm2["sign"] = {lab_: {ST_NAMES[k]: int(((D["st2_2"] == k) & base & sel).sum()) for k in ST_NAMES} for lab_, sel in (("x>0", xs > 0), ("x=0", xs == 0), ("x<0", xs < 0))}
        ax = np.abs(xs[base])
        qs = np.quantile(ax, [0.2, 0.4, 0.6, 0.8]) if len(ax) else np.array([])
        qi = np.searchsorted(qs, np.abs(xs), side="right") if len(qs) else np.zeros(len(xs), int)
        nm2["abs_x_quintile"] = {f"q{j + 1}": {ST_NAMES[k]: int(((D["st2_2"] == k) & base & (qi == j)).sum()) for k in ST_NAMES} for j in range(5)}
    return {"units": n, "gates": {"GBT": gbt, "GBA": gba, "GBS": gbs, "GB1P": w.power_gate(se1.get("se")), "GB2P": w.power_gate(se2.get("se"))},
            "planning_se": {"B1_L_pre": se1, "B2_dm_pre": se2}, "sd_x": sd_x,
            "informativeness": {"B1": {"level": st1, **info1}, "B2": {"level": rb.STRATA_LEVEL["B2"], **info2}, "window_rule": w.INFORMATIVE_MIN},
            "no_mark": {"B1_by_age_bin": nm1, "B2": nm2}, "exclusions": meta["exclusions"], "stats": meta["stats"], "gbt_counts": g, "passes": meta["n_passes"]}


# =====================================================================================================================================================
# B1 and B2 (Stage 1, and the same statistic on REP_8)
# =====================================================================================================================================================


def _keep_sign(make_v, idx: np.ndarray) -> bool | None:
    if len(idx) < 3:
        return None
    e = win.est_only(make_v, idx)
    return bool(math.isfinite(e) and e > 0)


def b1_test(F: dict, MV: dict, census_b: dict | None, *, n_draws: int = w.PLACEBO_DRAWS, rep: bool = False) -> dict:
    """B1: ``beta_B1`` = coefficient on ``old`` in a token-FE OLS of the 2 h excursion beyond the touch ``L`` (old and fresh units), one-sided > 0, floor +0.5c; adverse movement only."""
    D = with_ways(dataset(F), F["t1"])
    labels = [rb.LABEL_B1, w.LABEL_REP if rep else w.LABEL_SCREEN]
    if census_b is not None:
        gates = census_b["gates"]
        if not gates["GBT"]["pass"]:
            return win.not_testable(w.NOT_TESTABLE_SEMANTICS, labels=labels)
        if not gates["GBA"]["pass"]:
            return win.not_testable(w.NOT_TESTABLE_POP, labels=labels)
        if not rep and not gates["GB1P"]["run"]:
            return win.not_testable(w.NOT_RUN_POWER, labels=labels, power=gates["GB1P"])
    elig = b1_sample(D)
    ok = elig & (D["st2_1"] == ST_OK) & np.isfinite(MV["2h_b1_bid"])
    av = w.availability(int(ok.sum()), int(elig.sum()))
    info = {"availability": av, "tick_change": int(((D["state"] <= 1) & (D["st2_1"] == ST_TICK)).sum()), "rep": rep, "labels": labels}
    if not av["ok"]:
        return {**win.not_testable(w.NOT_TESTABLE_AVAIL), **info}
    L = np.full(len(D["tok"]), np.nan)
    b0, a0 = D["b0"].astype(float), D["a0"].astype(float)
    L[ok] = l_of(b0[ok], a0[ok], MV["2h_b1_bid"][ok], MV["2h_b1_ask"][ok])
    old = (D["state"] == 1).astype(float)
    tok = D["tok"].astype(np.int64)
    idx = np.nonzero(ok & np.isfinite(L))[0]
    mk = win.make_fe(L, old, tok)
    res = {**win.analyse(mk, idx, D, w.FLOOR_C), **info}
    res["bins"] = {"old": int(old[idx].sum()), "fresh": int((1 - old[idx]).sum()), "tokens": len(set(tok[idx].tolist())), "events": len(set(D["ev"][idx].tolist()))}
    if not res["testable"]:
        res.update(advance=False, checks_ok=False, verdict="not testable (population / clusters)")
        return res
    est = res["est"]
    strata = D["act_t"].astype(np.int64)
    comp = win.composition_guard(D, idx, L, old, lambda lab_: lab_, tok, strata, est, family="B1", info_units=(((int(tok[i]), (int(strata[i]),)), int(old[i])) for i in idx),
                                 seed=w.SEEDS["B1_composition"], n_draws=n_draws)
    res["composition_guard"] = comp
    res["calibration_placebo"] = {**win.calibration(D, idx, L, old, lambda lab_: lab_, tok, D["t1"], seed=w.SEEDS["B1_calibration"], n_draws=n_draws),
                                  "note": "B1 calibration: old / fresh circularly shifted within token over its passes"}
    ip = np.nonzero(elig & np.isfinite(D["lpre"]))[0]
    pp = win.p_of(win.make_fe(D["lpre"].astype(float), old, tok), ip, D, alpha=w.GATE_P)
    res["pre_period_placebo"] = {"p": pp["p"], "n": pp["n"], "holds": bool((not pp["testable"]) or pp["p"] >= w.GATE_P)}
    cov, names = [], []
    for arr, nm in ((bands_spread(D["spread"]), "spread_band"), (np.array([vol_band(float(v)) for v in D["vol24"]]), "vol24_band"), (np.array([lev_band(float(v)) for v in D["nlev"]]), "levels_band"),
                    (np.array([c17.band6(float(t)) for t in D["t1"]]), "utc6"), (np.array([pre.p_band(float(m)) if pre.p_band(float(m)) is not None else -1 for m in D["mid0"]]), "mid_band"),
                    (D["reward"], "reward"), (D["grain"], "grain"), (D["hchg"], "hash_changed")):
        c, n_ = win.dummies(arr, nm)
        cov += c
        names += n_
    cov += [D["act"].astype(float), np.log(np.maximum(np.nan_to_num(D["liq"].astype(float), nan=1.0), 1.0)), (~np.isfinite(D["liq"])).astype(float)]
    names += ["activity", "log_liq", "liq_missing"]
    res["attribution"] = win.attribution(L, old, cov, names, tok, idx, est, credit="book age", debit="composition, not book age")
    rob: dict[str, bool | None] = {}
    # no-mark worst case (binding): ok -> L; no / wide mark -> the capture mark, else the bound adverse to the hypothesis (old 0, fresh p95 of available fresh L)
    wc = np.full(len(L), np.nan)
    wc[idx] = L[idx]
    nm = elig & np.isin(D["st2_1"], (ST_NO, ST_WIDE))
    capm = MV["cap_b1"]
    has_c = nm & np.isfinite(capm)
    wc[has_c] = l_from_mid(b0[has_c], a0[has_c], capm[has_c])
    p95 = rb.worst_b1(False, L[idx][old[idx] == 0])
    rest = nm & ~has_c
    wc[rest & (old == 1)] = rb.worst_b1(True, np.array([]))
    wc[rest & (old == 0)] = p95
    iw = np.nonzero(elig & np.isfinite(wc))[0]
    rob["no_mark_worst_case"] = _keep_sign(win.make_fe(wc, old, tok), iw)
    Lc = np.full(len(L), np.nan)
    hc = elig & np.isfinite(capm)
    Lc[hc] = l_from_mid(b0[hc], a0[hc], capm[hc])
    rob["capture_mark"] = _keep_sign(win.make_fe(Lc, old, tok), np.nonzero(hc & np.isfinite(Lc))[0])
    okm = (D["st2_1"] == ST_OK) & np.isfinite(MV["2h_b1_bid"]) & (D["state"] >= 0)
    Lall = np.full(len(L), np.nan)
    Lall[okm] = l_of(b0[okm], a0[okm], MV["2h_b1_bid"][okm], MV["2h_b1_ask"][okm])
    age = D["age"].astype(float)
    for cut in rb.OLD_CUT_ALTS_S:
        o2 = (age >= cut).astype(float)
        s_ = okm & ((age < pre.FRESH_AGE_S) | (age >= cut)) & np.isfinite(Lall)
        rob[f"old_cut_{int(cut)}s"] = _keep_sign(win.make_fe(Lall, o2, tok), np.nonzero(s_)[0])
    rob["exclude_age_gt_3600s"] = _keep_sign(mk, idx[age[idx] <= rb.AGE_EXCLUDE_ABOVE_S])
    m2 = (MV["2h_b1_bid"] + MV["2h_b1_ask"]) / 2.0
    la = np.where(np.isfinite(m2), 100.0 * np.maximum(0.0, m2 - a0), np.nan)
    lb = np.where(np.isfinite(m2), 100.0 * np.maximum(0.0, b0 - m2), np.nan)
    rob["ask_crossing_component"] = _keep_sign(win.make_fe(la, old, tok), idx)
    rob["bid_crossing_component"] = _keep_sign(win.make_fe(lb, old, tok), idx)
    rob["relative_L"] = _keep_sign(win.make_fe(L / np.where(D["spread"] > 0, D["spread"], np.nan), old, tok), idx)
    mid = D["mid0"]
    rob["mid_10_90"] = _keep_sign(mk, idx[(mid[idx] >= rb.MID_ROBUST[0] - 1e-12) & (mid[idx] <= rb.MID_ROBUST[1] + 1e-12)])
    ok6 = elig & (D["st6_1"] == ST_OK) & np.isfinite(MV["6h_b1_bid"])
    L6 = np.full(len(L), np.nan)
    L6[ok6] = l_of(b0[ok6], a0[ok6], MV["6h_b1_bid"][ok6], MV["6h_b1_ask"][ok6])
    rob["mark_6h"] = _keep_sign(win.make_fe(L6, old, tok), np.nonzero(ok6 & np.isfinite(L6))[0])
    res["robustness"] = rob
    res["robust_ok"] = bool(all(v for v in rob.values() if v is not None) and all(v is not None for v in (rob["no_mark_worst_case"],)) and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["checks_ok"] = bool(res["floor_ok"] and res["small_g_rules_hold"] and comp["holds"] and res["calibration_placebo"]["holds"] and res["pre_period_placebo"]["holds"] and res["robust_ok"])
    res["advance"] = w.stage1_advance(res["p"] if res["testable"] else None, res["checks_ok"])
    if not comp["informative"]:
        labels.append(w.UNINFORMATIVE)
    res["labels"] = labels
    res["verdict"] = ("advance" if res["advance"] else "no advance") + (f"; {res['attribution']['label']}" if res["advance"] else "")
    return res


def b2_test(F: dict, MV: dict, census_b: dict | None, *, sd_x: float, n_draws: int = w.PLACEBO_DRAWS, rep: bool = False) -> dict:
    """B2: ``beta_B2`` = coefficient on ``x / SD_x`` in a token-FE OLS of the signed 2 h mid change, one-sided > 0, floor +0.5c per SD (SD_x from SCREEN_8, frozen for REP_8)."""
    t2 = np.where(np.isfinite(F["t2"]), F["t2"], F["t1"])
    D = with_ways(dataset(F), t2)
    labels = [w.LABEL_REP if rep else w.LABEL_SCREEN]
    if census_b is not None:
        gates = census_b["gates"]
        if not gates["GBS"]["pass"]:
            return win.not_testable(w.NOT_TESTABLE_POP, labels=labels)
        if not rep and not gates["GB2P"]["run"]:
            return win.not_testable(w.NOT_RUN_POWER, labels=labels, power=gates["GB2P"])
    if not (math.isfinite(sd_x) and sd_x > 0):
        return win.not_testable(w.NOT_TESTABLE_POP, labels=labels, reason="SD_x undefined")
    elig = b2_sample(D)
    ok = elig & (D["st2_2"] == ST_OK) & np.isfinite(MV["2h_b2_bid"])
    av = w.availability(int(ok.sum()), int(elig.sum()))
    info = {"availability": av, "tick_change": int(((D["excl2"] == B2_OK) & (D["st2_2"] == ST_TICK)).sum()), "rep": rep, "sd_x": sd_x, "labels": labels}
    if not av["ok"]:
        return {**win.not_testable(w.NOT_TESTABLE_AVAIL), **info}
    m0 = D["mid0"]
    dm = np.full(len(m0), np.nan)
    dm[ok] = 100.0 * ((MV["2h_b2_bid"][ok] + MV["2h_b2_ask"][ok]) / 2.0 - m0[ok])
    xs = D["x"].astype(float) / sd_x
    tok = D["tok"].astype(np.int64)
    idx = np.nonzero(ok & np.isfinite(dm))[0]
    mk = win.make_fe(dm, xs, tok)
    res = {**win.analyse(mk, idx, D, w.FLOOR_C), **info}
    res["units"] = {"n": int(len(idx)), "s_nonzero": int((D["s"][idx] != 0).sum()), "tokens": len(set(tok[idx].tolist())), "events": len(set(D["ev"][idx].tolist()))}
    if not res["testable"]:
        res.update(advance=False, checks_ok=False, verdict="not testable (population / clusters)")
        return res
    est = res["est"]
    strata = (D["act_t"].astype(np.int64) * 4 + D["imb_t"].astype(np.int64))
    comp = win.composition_guard(D, idx, dm, xs, lambda lab_: lab_, tok, strata, est, family="B2",
                                 info_units=(((int(tok[i]), (int(D["act_t"][i]), int(D["imb_t"][i]))), float(D["x"][i])) for i in idx), seed=w.SEEDS["B2_composition"], n_draws=n_draws)
    res["composition_guard"] = comp
    res["calibration_placebo"] = {**win.calibration(D, idx, dm, xs, lambda lab_: lab_, tok, t2, seed=w.SEEDS["B2_calibration"], n_draws=n_draws),
                                  "note": "B2 calibration: x circularly shifted within token over its passes"}
    ip = np.nonzero(elig & np.isfinite(D["dmpre"]))[0]
    pp = win.p_of(win.make_fe(D["dmpre"].astype(float), xs, tok), ip, D, alpha=w.GATE_P)
    res["pre_sweep_placebo"] = {"p": pp["p"], "n": pp["n"], "holds": bool((not pp["testable"]) or pp["p"] >= w.GATE_P)}
    cov, names = [D["dmpre"].astype(float), D["imb"].astype(float), D["dnlev"].astype(float), np.nan_to_num(D["tsz_chg"].astype(float), nan=0.0), D["act"].astype(float)], \
        ["dm_pre", "imbalance", "levels_change", "touch_size_change", "activity"]
    for arr, nm in ((bands_spread(D["spread"]), "spread_band"), (np.array([c17.band6(float(t)) for t in t2]), "utc6")):
        c, n_ = win.dummies(arr, nm)
        cov += c
        names += n_
    res["attribution"] = win.attribution(dm, xs, cov, names, tok, idx, est, credit="breathing book", debit="composition, not the breathing book")
    rob: dict[str, bool | None] = {}
    wc = np.full(len(dm), np.nan)
    wc[idx] = dm[idx]
    nm_ = elig & np.isin(D["st2_2"], (ST_NO, ST_WIDE))
    capm = MV["cap_b2"]
    hc = nm_ & np.isfinite(capm)
    wc[hc] = 100.0 * (capm[hc] - m0[hc])
    rest = nm_ & ~hc
    avail_dm = dm[idx]
    x_raw = D["x"].astype(float)
    for sel, xv in ((rest & (x_raw > 0), 1.0), (rest & (x_raw < 0), -1.0), (rest & (x_raw == 0), 0.0)):
        wc[sel] = rb.worst_b2(xv, avail_dm)
    rob["no_mark_worst_case"] = _keep_sign(win.make_fe(wc, xs, tok), np.nonzero(elig & np.isfinite(wc))[0])
    rob["s_nonzero_only"] = _keep_sign(mk, idx[D["s"][idx] != 0])
    rob["no_print_between_sweeps"] = _keep_sign(mk, idx[D["prt"][idx] == 0])
    rob["unchanged_touch_sizes"] = _keep_sign(mk, idx[D["tsz_same"][idx] == 1])
    dmc = np.where(elig & np.isfinite(capm), 100.0 * (capm - m0), np.nan)
    rob["capture_mark"] = _keep_sign(win.make_fe(dmc, xs, tok), np.nonzero(np.isfinite(dmc))[0])
    ok6 = elig & (D["st6_2"] == ST_OK) & np.isfinite(MV["6h_b2_bid"])
    dm6 = np.where(ok6, 100.0 * ((MV["6h_b2_bid"] + MV["6h_b2_ask"]) / 2.0 - m0), np.nan)
    rob["mark_6h"] = _keep_sign(win.make_fe(dm6, xs, tok), np.nonzero(np.isfinite(dm6))[0])
    res["robustness"] = rob
    res["robust_ok"] = bool(all(v for v in rob.values() if v is not None) and rob["no_mark_worst_case"] is not None and res["loo_day"]["holds"] and all(res["top5"].values()))
    res["checks_ok"] = bool(res["floor_ok"] and res["small_g_rules_hold"] and comp["holds"] and res["calibration_placebo"]["holds"] and res["pre_sweep_placebo"]["holds"] and res["robust_ok"])
    res["advance"] = w.stage1_advance(res["p"] if res["testable"] else None, res["checks_ok"])
    conc = rb.concentration_share(D["x"][idx].astype(float), D["ev"][idx])
    res["concentration_share"] = conc
    if conc > rb.CONCENTRATION_SHARE:
        labels.append(rb.LABEL_CONCENTRATED)
    if not comp["informative"]:
        labels.append(w.UNINFORMATIVE)
    res["labels"] = labels
    res["verdict"] = ("advance" if res["advance"] else "no advance") + (f"; {res['attribution']['label']}" if res["advance"] else "")
    return res


# =====================================================================================================================================================
# econ (Stage 2, REP_8 arm-1; branch T fill source = CB13-T touch-consistent fills by pin)
# =====================================================================================================================================================


def b1_econ_bins(fills: list[dict], ages: dict) -> list[str | None]:
    """Per fill: old / fresh at the token's latest sweep in [tau - 30 min, tau) (rules B ``econ_b1_bin``), None otherwise."""
    out = []
    for f in fills:
        rec = (ages.get(f.get("token0") or "") or {}).get(str(f["tau"]))
        out.append(rb.econ_b1_bin(float(rec[1])) if rec else None)
    return out


def b2_econ_flags(fills: list[dict], F: dict, sd_x: float) -> list[bool | None]:
    """Per fill: the token's MOST RECENT flagged pass (B2-eligible, |x| >= SD_x) with t < tau <= t + 2 h (O10) defines the side: abandoned-side iff the maker sold YES when x > 0 or
    bought YES when x < 0 (rules B ``econ_b2_abandoned``); None = no flagged pass in the horizon. The contrast is abandoned (True) minus the market's other REP_8 fills (False / None)."""
    toks = F["_meta"]["vocab"]["tok"]
    by: dict[str, tuple[list[float], list[float]]] = {}
    m = (F["excl2"] == B2_OK) & np.isfinite(F["x"]) & np.isfinite(F["t2"]) & (np.abs(F["x"].astype(float)) >= sd_x)  # flagged passes only (O10: the most recent FLAGGED pass)
    for u in np.nonzero(m)[0]:
        tl, xl = by.setdefault(toks[int(F["tok"][u])], ([], []))
        tl.append(float(F["t2"][u]))
        xl.append(float(F["x"][u]))
    for k, (tl, xl) in list(by.items()):
        o = np.argsort(tl)
        by[k] = ([tl[i] for i in o], [xl[i] for i in o])
    out = []
    for f in fills:
        tl, xl = by.get(f.get("token0") or "", ([], []))
        j = bisect.bisect_left(tl, float(f["tau"])) - 1
        if j < 0 or float(f["tau"]) - tl[j] > rb.ECON_B2_HORIZON_S:
            out.append(None)
            continue
        out.append(rb.econ_b2_abandoned(xl[j], sd_x, int(f["d"])))
    return out


def declared() -> dict:
    return {"frame": UNITS_NAME, "meta": META_NAME, "marks": MARKS_NAME, "mark_statuses": {str(k): v for k, v in ST_NAMES.items()}, "b2_exclusions": {str(k): v for k, v in B2_EXCL_NAMES.items()},
            "vol_band_edges": list(VOL_BAND_EDGES)}
