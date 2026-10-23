# ruff: noqa: E501
"""CH240, the boundary map (docs/research_lab/CREATIVE_HYPOTHESES_2026-10-30.md section E). COUNTS ONLY, k = 0, uncounted.

A streaming reader over the host's 2-hourly captures (``rows.csv.gz``, the ``rows_ext.csv.gz`` sidecar and ``manifest.json``).
For each capture k it uses ONLY capture k and capture k - 1 fields at their own receipt; nothing from capture k + 1 or later is read,
no price target, no P&L. Read-only: it imports (never edits) the existing classifiers.

Counted (per capture, by category sports / crypto / nonsports_excrypto / unknown, and reward status rewarded / unrewarded / unknown):
  CH232  first crossings of 0.10 / 0.90 (and 0.04 / 0.96 for the record) by the YES mid between k - 1 and k, by boundary and direction
         (outward = away from 0.5 across the boundary), tick-coincident crossings (one tick step) separately, the per-market-day re-crossing share;
  CH233  neg-risk events and member rows, complete event-captures (every member two-sided) by size bucket, the bid-sum headroom
         hb = 1 - sum(member best bids), the share within 2 ticks of zero, headroom crossings of zero, the within-event SD of the
         siblings' bid-sum change (events with >= 48 units over the span);
  CH234  traded 2 h movers (|d| >= 0.01 and volume_num up) and quote-only movers (volume_num unchanged) by price bin of p_{k-1}, the collateral
         weight w = 0.5 + sign(d) (p_{k-1} - 0.5), the share of mover market-days (>= 2 traded moves) whose SD of w is >= 0.1.

Reward reading (a MAP, not the listed_carry24h_v2 rule of LT8): ``rewarded`` = ``clob_rewards`` of capture k non-empty (not null-like, not ``[]``),
``unrewarded`` = sidecar row present with the column but empty, ``unknown`` = no sidecar row or no ``clob_rewards`` column.
Category: sports by ``cb17_census.is_sports_sidecar``; crypto by ``live_tests8_base.crypto_class`` (fee_category); ``unknown`` without a sidecar row.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import statistics
from array import array
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import cb17_census
from . import live_tests8_base as b

VERSION = "ch240-boundary-map-v1"
GRID_S = 7200.0
GAP_MAX_S = 9000.0  # a previous capture further back than 2 h + 30 min is not capture k - 1
GRID_REF_S = 1860.0  # slot rounding only (00:31Z grid); used to drop duplicate copies of one capture
BOUNDARIES = (0.04, 0.10, 0.90, 0.96)
LOWER = (0.04, 0.10)
MOVE_MIN = 0.01
EPS = 1e-9
BINS = ("lt0.1", "0.1-0.5", "0.5-0.9", "ge0.9")
SIZE_BUCKETS = ("2", "3-5", "6-10", "11+")
W_SD_MIN = 0.1
MIN_UNITS = 48
DEFAULT_TICK = 0.01
CATS = ("sports", "crypto", "nonsports_excrypto", "unknown")
RWS = ("rewarded", "unrewarded", "unknown")
ROW_COLS = ("market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "volume_num", "neg_risk", "neg_risk_market_id")
EXT_COLS = ("market_id", "fee_type", "fee_category", "series_slugs", "clob_rewards", "order_price_min_tick_size")
_NULL_LIKE = {"", "nan", "none", "null", "[]"}
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)

CODE_FILES = (Path(__file__), Path(__file__).resolve().parents[2] / "scripts" / "run_ch240_map.py")


def code_sha256() -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CODE_FILES if p.exists()}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _f(v) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) else math.nan


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "1.0", "t")


def parse_utc(v) -> float:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return math.nan


def day_of(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d")


def price_bin(p: float) -> str:
    return BINS[0] if p < 0.1 else BINS[1] if p < 0.5 else BINS[2] if p < 0.9 else BINS[3]


def size_bucket(n: int) -> str | None:
    return None if n < 2 else "2" if n == 2 else "3-5" if n <= 5 else "6-10" if n <= 10 else "11+"


def collateral_weight(d: float, p_prev: float) -> float:
    """w = 0.5 + sign(d) (p_{k-1} - 0.5)."""
    s = 1.0 if d > 0 else -1.0 if d < 0 else 0.0
    return 0.5 + s * (p_prev - 0.5)


def reward_status(clob_rewards, has_sidecar: bool, has_column: bool) -> str:
    if not has_sidecar or not has_column:
        return "unknown"
    s = str(clob_rewards if clob_rewards is not None else "").strip().casefold()
    return "unrewarded" if s in _NULL_LIKE else "rewarded"


def category_of(fee_type, fee_category, series_slugs, has_sidecar: bool) -> str:
    if not has_sidecar:
        return "unknown"
    if cb17_census.is_sports_sidecar(fee_type, fee_category, series_slugs):
        return "sports"
    c = b.crypto_class(fee_category, True, 0)
    return "crypto" if c == "crypto" else "nonsports_excrypto" if c == "non_crypto" else "unknown"


def crossing(prev_mid: float, mid: float, boundary: float) -> str | None:
    """'outward' / 'inward' when the YES mid crossed ``boundary`` between k - 1 and k (strict side change, >= boundary counts as upper side), else None."""
    if not (math.isfinite(prev_mid) and math.isfinite(mid)):
        return None
    up_prev, up_now = prev_mid >= boundary, mid >= boundary
    if up_prev == up_now:
        return None
    moved_up = up_now
    return "outward" if moved_up != (boundary in LOWER) else "inward"


# --- stream readers (one file at a time) -------------------------------------------------------------------------------------------


def _iter_csv(path: Path, cols: tuple[str, ...]):
    csv.field_size_limit(10**9)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd, None)
        if head is None:
            return
        pos = {c: i for i, c in enumerate(head)}
        idx = [pos.get(c, -1) for c in cols]
        yield tuple(c in pos for c in cols)  # first item: which columns exist
        for row in rd:
            yield tuple(row[i] if 0 <= i < len(row) else "" for i in idx)


def read_ext(path: Path | None) -> tuple[dict, bool]:
    """{market_id: (category, reward, tick)} and whether a ``clob_rewards`` column exists."""
    out: dict = {}
    if path is None or not Path(path).exists():
        return out, False
    it = _iter_csv(path, EXT_COLS)
    present = next(it, None)
    if present is None:
        return out, False
    has_rw = present[EXT_COLS.index("clob_rewards")]
    for mid, ft, fc, ss, rw, tk in it:
        t = _f(tk)
        out[mid] = (category_of(ft, fc, ss, True), reward_status(rw, True, has_rw), t if t > 0 else DEFAULT_TICK)
    return out, has_rw


def read_rows(path: Path) -> dict:
    """{market_id: dict} of the last row per market (binary, open, active only are kept in 'ok'); fields at the capture's own receipt."""
    out: dict = {}
    it = _iter_csv(path, ROW_COLS)
    present = next(it, None)
    if present is None:
        return out
    has_vol = present[ROW_COLS.index("volume_num")]
    for mid, ev, rec, closed, active, binary, bid, ask, vol, nr, nrm in it:
        bid_f, ask_f = _f(bid), _f(ask)
        two = bid_f > 0 and ask_f > 0 and ask_f <= 1 and bid_f < ask_f
        out[mid] = {"event": ev, "binary": _truthy(binary), "open": (not _truthy(closed)) and _truthy(active), "bid": bid_f, "ask": ask_f,
                    "two": two, "vol": _f(vol) if has_vol else math.nan, "neg_risk": _truthy(nr), "nrm": nrm, "rec": rec}
    return out


# --- aggregation ------------------------------------------------------------------------------------------------------------------


class _Welford:
    __slots__ = ("n", "mean", "m2")

    def __init__(self) -> None:
        self.n, self.mean, self.m2 = 0, 0.0, 0.0

    def add(self, x: float) -> None:
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self.m2 += d * (x - self.mean)

    def sd(self) -> float:
        return math.sqrt(self.m2 / (self.n - 1)) if self.n >= 2 else math.nan


def _stats(vals: list[float]) -> dict:
    if not vals:
        return {"n_captures": 0}
    return {"n_captures": len(vals), "total": float(sum(vals)), "mean": float(statistics.fmean(vals)), "median": float(statistics.median(vals)), "min": float(min(vals))}


def _quantiles(a: array) -> dict:
    if not len(a):
        return {"n": 0}
    s = sorted(a)
    n = len(s)
    return {"n": n, **{f"q{int(q * 100):02d}": float(s[min(n - 1, int(q * n))]) for q in QUANTILES}}


class Mapper:
    """Feeds captures in time order; keeps only per-market state of capture k - 1 and small per-market-day / per-event accumulators."""

    def __init__(self) -> None:
        self.prev: dict | None = None  # {market_id: (event, mid, vol, two_ok)} of capture k - 1
        self.prev_t = math.nan
        self.prev_event_bids: dict = {}  # event -> {market_id: bid} of capture k - 1 (complete events only)
        self.day = None
        self.cap_lvl: list[Counter] = []
        self.cap_chg: list[Counter] = []
        self.events: dict[str, set] = {}  # population key -> distinct event ids
        self.day_cross: dict = {}  # (market, boundary) -> [count, stratum]  (current UTC day)
        self.day_w: dict = {}  # market -> [_Welford, stratum]  (current UTC day, traded moves)
        self.agg = Counter()  # span-level aggregates (market-day shares and the like)
        self.hb = {}  # stratum -> array of hb
        self.ev_sd: dict = {}  # event -> [_Welford, stratum, tick]
        self.n_captures = 0
        self.n_changes = 0
        self.notes = Counter()

    # -- day roll: finalise the per-market-day accumulators
    def _roll(self, new_day: str) -> None:
        if self.day is not None and new_day != self.day:
            self._finalise_day()
        self.day = new_day

    def _finalise_day(self) -> None:
        for (_m, bd), (cnt, strat) in self.day_cross.items():
            self.agg[f"ch232/market_days_with_cross/b{bd:.2f}/{strat}"] += 1
            if cnt >= 2:
                self.agg[f"ch232/market_days_with_recross/b{bd:.2f}/{strat}"] += 1
        for _m, (w, strat) in self.day_w.items():
            if w.n >= 2:
                self.agg[f"ch234/mover_market_days_ge2_traded/{strat}"] += 1
                if w.sd() >= W_SD_MIN:
                    self.agg[f"ch234/mover_market_days_w_sd_ge_0.1/{strat}"] += 1
        self.day_cross, self.day_w = {}, {}

    def feed(self, t: float, rows: dict, ext: dict) -> None:
        self._roll(day_of(t))
        self.n_captures += 1
        lvl, chg = Counter(), Counter()
        has_prev = self.prev is not None and 0 < t - self.prev_t <= GAP_MAX_S
        if not has_prev and self.prev is not None:
            self.notes["previous_capture_gap_too_large"] += 1
        cur: dict = {}
        events: dict = {}  # event -> members for the neg-risk events at k
        for mid, r in rows.items():
            if not r["binary"] or not r["open"]:
                continue
            e = ext.get(mid)
            cat, rw, tick = (e if e else ("unknown", "unknown", DEFAULT_TICK))
            r["cat"], r["rw"], r["tick"] = cat, rw, tick
            strat = f"{cat}/{rw}"
            r["strat"] = strat
            if r["two"]:
                mid_k = (r["bid"] + r["ask"]) / 2.0
                cur[mid] = (r["event"], mid_k, r["vol"])
            if r["neg_risk"] and r["event"]:
                events.setdefault(r["event"], []).append((mid, r))
        # --- CH232 / CH234 (market level, k - 1 and k)
        if has_prev:
            self.n_changes += 1
            for mid, (ev, m_k, v_k) in cur.items():
                p = self.prev.get(mid)
                if p is None:
                    continue
                _ev0, m_p, v_p = p
                r = rows[mid]
                strat, tick = r["strat"], r["tick"]
                d = m_k - m_p
                for bd in BOUNDARIES:
                    side = crossing(m_p, m_k, bd)
                    if side is None:
                        continue
                    key = (mid, bd)
                    rec = self.day_cross.get(key)
                    chg[f"ch232/all_crossings/b{bd:.2f}/{side}/{strat}"] += 1
                    if rec is None:
                        self.day_cross[key] = [1, strat]
                        tc = abs(d) <= tick + EPS
                        chg[f"ch232/first_crossings/b{bd:.2f}/{side}/{strat}"] += 1
                        if tc:
                            chg[f"ch232/first_crossings_tick_coincident/b{bd:.2f}/{side}/{strat}"] += 1
                        else:
                            chg[f"ch232/first_crossings_ex_tick/b{bd:.2f}/{side}/{strat}"] += 1
                        self.events.setdefault(f"ch232/b{bd:.2f}/{strat}", set()).add(ev)
                    else:
                        rec[0] += 1
                        chg[f"ch232/recrossings/b{bd:.2f}/{side}/{strat}"] += 1
                if abs(d) >= MOVE_MIN - EPS:
                    if not (math.isfinite(v_k) and math.isfinite(v_p)) or v_k < v_p:
                        chg[f"ch234/movers_volume_unusable/{strat}"] += 1
                        continue
                    kind = "traded" if v_k > v_p else "quote_only"
                    pb = price_bin(m_p)
                    chg[f"ch234/movers_{kind}/{pb}/{strat}"] += 1
                    self.events.setdefault(f"ch234/{kind}/{strat}", set()).add(ev)
                    if kind == "traded":
                        w = collateral_weight(d, m_p)
                        rec2 = self.day_w.get(mid)
                        if rec2 is None:
                            rec2 = self.day_w[mid] = [_Welford(), strat]
                        rec2[0].add(w)
        # --- CH233 (event level)
        new_bids: dict = {}
        for ev, members in events.items():
            cats = {r["cat"] for _, r in members}
            rws = {r["rw"] for _, r in members}
            cat = "sports" if "sports" in cats else "crypto" if "crypto" in cats else "unknown" if "unknown" in cats else "nonsports_excrypto"
            rw = "rewarded" if "rewarded" in rws else "unknown" if "unknown" in rws else "unrewarded"
            strat = f"{cat}/{rw}"
            n = len(members)
            bk = size_bucket(n)
            lvl[f"ch233/events/{strat}"] += 1
            lvl[f"ch233/member_rows/{strat}"] += n
            self.events.setdefault(f"ch233/events/{strat}", set()).add(ev)
            if bk is None:
                lvl[f"ch233/events_single_member/{strat}"] += 1
                continue
            lvl[f"ch233/event_captures/{bk}/{strat}"] += 1
            if not all(r["two"] for _, r in members):
                continue
            lvl[f"ch233/complete_event_captures/{bk}/{strat}"] += 1
            self.events.setdefault(f"ch233/complete/{strat}", set()).add(ev)
            bids = {mid: r["bid"] for mid, r in members}
            hb = 1.0 - sum(bids.values())
            tick = max(r["tick"] for _, r in members)
            self.hb.setdefault(strat, array("f")).append(hb)
            if abs(hb) <= 2 * tick + EPS:
                lvl[f"ch233/hb_within_2_ticks/{strat}"] += 1
            if hb > 0:
                lvl[f"ch233/hb_positive/{strat}"] += 1
            new_bids[ev] = bids
            pb_ = self.prev_event_bids.get(ev) if has_prev else None
            if pb_ is not None and pb_.keys() == bids.keys():
                hb_p = 1.0 - sum(pb_.values())
                if (hb_p > 0) != (hb > 0):
                    chg[f"ch233/headroom_zero_crossings/{strat}"] += 1
                chg[f"ch233/complete_pairs/{strat}"] += 1
                ds = sum(bids.values()) - sum(pb_.values())
                rec3 = self.ev_sd.get(ev)
                if rec3 is None:
                    rec3 = self.ev_sd[ev] = [_Welford(), strat, tick]
                rec3[1], rec3[2] = strat, tick
                for mid, bd_k in bids.items():
                    rec3[0].add(ds - (bd_k - pb_[mid]))  # change in the siblings' bid sum (all members but this one)
        # --- carry k - 1 state (only fields of capture k at its own receipt)
        self.prev = {m: v for m, v in cur.items()}
        self.prev_t = t
        self.prev_event_bids = new_bids
        self.cap_lvl.append(lvl)
        if has_prev:
            self.cap_chg.append(chg)

    def finish(self, covered_days_per_capture: float = GRID_S / 86400.0) -> dict:
        if self.day is not None:
            self._finalise_day()
        out: dict = {"level_counts": {}, "change_counts": {}}
        for name, caps, per in (("level_counts", self.cap_lvl, self.n_captures), ("change_counts", self.cap_chg, self.n_changes)):
            keys = sorted({k for c in caps for k in c})
            days = per * covered_days_per_capture
            for k in keys:
                st = _stats([float(c.get(k, 0)) for c in caps])
                st["projected_21d"] = st["total"] * 21.0 / days if days > 0 else None
                out[name][k] = st
        out["distinct_events_over_span"] = {k: len(v) for k, v in sorted(self.events.items())}
        out["market_day_aggregates"] = dict(sorted(self.agg.items()))
        shares: dict = {}
        for k, v in self.agg.items():
            if k.startswith("ch232/market_days_with_recross/"):
                base = k.replace("market_days_with_recross", "market_days_with_cross")
                shares[k.replace("market_days_with_recross", "recross_share")] = v / self.agg[base] if self.agg.get(base) else None
            if k.startswith("ch234/mover_market_days_w_sd_ge_0.1/"):
                base = k.replace("w_sd_ge_0.1", "ge2_traded")
                shares[k.replace("mover_market_days_w_sd_ge_0.1", "share_w_sd_ge_0.1")] = v / self.agg[base] if self.agg.get(base) else None
        out["shares"] = dict(sorted(shares.items()))
        out["hb_quantiles"] = {k: _quantiles(a) for k, a in sorted(self.hb.items())}
        # complete share by size bucket, from totals
        cs: dict = {}
        for k, st in out["level_counts"].items():
            if k.startswith("ch233/event_captures/"):
                comp = out["level_counts"].get(k.replace("event_captures", "complete_event_captures"))
                cs[k.replace("event_captures", "complete_share")] = (comp["total"] if comp else 0.0) / st["total"] if st["total"] else None
        out["complete_share_by_size_bucket"] = dict(sorted(cs.items()))
        wi: dict = {}
        for w, strat, tick in self.ev_sd.values():
            if w.n >= MIN_UNITS:
                wi[strat] = wi.setdefault(strat, [0, 0])
                wi[strat][0] += 1
                if w.sd() >= tick - EPS:
                    wi[strat][1] += 1
        out["ch233_within_event_sd"] = {s: {"events_ge_48_units": a, "events_sd_ge_1_tick": c, "share": (c / a if a else None)} for s, (a, c) in sorted(wi.items())}
        out["notes"] = dict(self.notes)
        return out


# --- capture discovery and the run ------------------------------------------------------------------------------------------------


def discover(roots: list[Path], start_utc: str, end_utc: str) -> list[dict]:
    t0, t1 = parse_utc(start_utc), parse_utc(end_utc)
    by_slot: dict = {}
    for root in roots:
        for p in sorted(Path(root).glob("*/manifest.json")):
            try:
                m = json.loads(p.read_text())
            except (OSError, ValueError):
                continue
            t = parse_utc(m.get("started_utc"))
            if m.get("state") != "complete" or not math.isfinite(t) or not (t0 <= t < t1) or not (p.parent / "rows.csv.gz").exists():
                continue
            slot = int(round((t - GRID_REF_S) / GRID_S))
            by_slot.setdefault(slot, {"id": p.parent.name, "start": t, "dir": p.parent})
    return [by_slot[k] for k in sorted(by_slot)]


def run_map(roots: list[Path], start_utc: str, end_utc: str) -> dict:
    caps = discover(roots, start_utc, end_utc)
    t0, t1 = parse_utc(start_utc), parse_utc(end_utc)
    mp = Mapper()
    inputs: list[dict] = []
    for c in caps:
        d = Path(c["dir"])
        files = [d / "manifest.json", d / "rows.csv.gz"] + ([d / "rows_ext.csv.gz"] if (d / "rows_ext.csv.gz").exists() else [])
        for f in files:
            inputs.append({"path": str(f), "bytes": f.stat().st_size, "sha256": sha256_file(f)})
        ext, _has_rw = read_ext(d / "rows_ext.csv.gz" if (d / "rows_ext.csv.gz").exists() else None)
        rows = read_rows(d / "rows.csv.gz")
        mp.feed(c["start"], rows, ext)
        del rows, ext
    starts = [c["start"] for c in caps]
    gaps = []
    edges = [t0 - GRID_S / 2, *starts, t1 - GRID_S / 2 + 1]
    for a, z in zip(edges, edges[1:], strict=False):
        if z - a > GAP_MAX_S:
            gaps.append({"after": datetime.fromtimestamp(a, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "before": datetime.fromtimestamp(z, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "hours": round((z - a) / 3600, 2)})
    res = mp.finish()
    return {
        "version": VERSION, "kind": "CH240 boundary map: counts only, k = 0, uncounted; nothing from capture k + 1 or later; no target, no P&L",
        "span": {"start_utc": start_utc, "end_utc": end_utc, "expected_2h_slots": int((t1 - t0) // GRID_S)},
        "captures": {"covered": len(caps), "covered_ids": [c["id"] for c in caps], "with_previous_capture_k_minus_1": mp.n_changes,
                     "missing_expected": max(0, int((t1 - t0) // GRID_S) - len(caps)), "gaps_over_2h30": gaps,
                     "covered_days": len(caps) * GRID_S / 86400.0},
        "reward_reading": "MAP reading, not listed_carry24h_v2: rewarded = clob_rewards of capture k non-empty (not null-like, not '[]'); unrewarded = sidecar row with an empty field; unknown = no sidecar row or column",
        "category_reading": "sports: cb17_census.is_sports_sidecar; crypto: live_tests8_base.crypto_class (fee_category); unknown: no sidecar row or no fee_category",
        "conventions": {"mid": "(best_bid + best_ask) / 2 of a two-sided open active binary row", "crossing": "strict side change of mid >= boundary between k - 1 and k; outward = away from 0.5",
                        "first_crossing": "first of that market, boundary and UTC day (day of capture k)", "tick_coincident": "|d| <= order_price_min_tick_size (default 0.01)",
                        "neg_risk_event": "rows with neg_risk true grouped by event_id; members = open active binary rows; complete = all members two-sided; event stratum: sports > crypto > unknown > nonsports_excrypto, rewarded if any member rewarded",
                        "movers": "|d| >= 0.01; traded = volume_num_k > volume_num_{k-1}; quote_only = equal; a falling or missing volume_num is counted as movers_volume_unusable", "projection": "total x 21 / covered days"},
        "inputs": inputs, "code_sha256": code_sha256(), **res,
    }
