# ruff: noqa: E501
"""CH261, the LT13 population map (docs/research_lab/CREATIVE_HYPOTHESES_2026-11-01.md section 2 CH261). COUNTS ONLY, k = 0, uncounted.

A streaming reader over the host's 2-hourly captures (``rows.csv.gz``, ``rows_ext.csv.gz``, ``manifest.json``), modelled on the CH251 map
(``population_map_ch251``; its readers and helpers are imported, never edited). For each capture k it uses ONLY capture k and capture k - 1 fields at
their own receipt: nothing from capture k + 1 or later, no resolution winner, no price change after an origin, no P&L. One capture at a time.

Counted (per capture; strata = category sports / crypto / nonsports_excrypto / unknown, reward status rewarded / unrewarded / unknown, fee class):
  CH252  two-sided units, widenings and narrowings (spread change >= 2 x tick between k - 1 and k) by the 2 x 2 fee x reward cell and category, each cell's
         per-capture total / min / median / mean, the widening units' category x age distribution, a cell-matched coverage PROXY (fee-free unrewarded
         widening units in a category x age cell holding >= 20 fee-on unrewarded widening units);
  CH253  creation batches over ``created_at`` (chain; closes after 120 s without a new creation; >= 3 markets spanning >= 2 events; mates in the unit's
         own event excluded; cap 30 cross-event mates; completeness >= 60% of members two-sided at k - 1 and k; receipt span <= 120 s about the batch
         median at both captures): size distribution, cross-event counts, the share of eligible rows in a cross-event batch of >= 3, batches with
         >= 24 complete units in a UTC day, the same-slot correlation of a unit's spread innovation with its mates', the category-factor correlation (VIF
         derived), and pseudo-batch coverage (NO category match: the created_at age decile over the capture's complete eligible
         units, created >= 7 days apart, enough such units; see the code in ``_batches``);
  CH254  favourite collapses between k - 1 and k (mid >= 0.85 at k - 1 and <= 0.15 at k) by category and UMA-proposed-at-k kind, their volume_num where
         present, category-days with one, the favourite share of eligible two-sided rows, favourites absent from the open rows at k;
  CH255  first-of-day leader flips (the leader by mid changes between k - 1 and k; complete events) by trade class, event size (2 held out), visibility
         (event_volume rank among non-sports ex-crypto events: top 200 / top 1000), distinct events, the re-flip share;
  CH256  event_comment_count presence, change share and bursts (>= +5) on non-sports ex-crypto events, and its correlation with the event_volume change;
  CH257  halted rows (accepting_orders false on open active binary rows) by category, completed halt lengths (captures), the share two-sided, the
         reopening move across the reopen capture only;
  CH260  the fee per dollar staked (rate x (1 - mid)) of fee-on two-sided rows by cell, cumulative bins.

UNAVAILABLE (``not_mapped`` in the output, never invented): anything that needs capture k + 1 (CH252/CH253 forward targets and the k + 1 two-sidedness,
CH254 'vanished at k + 1', the post-reopen move beyond k), the carry reward reading with the CLOB feed adjudicating, the liquidity tier, CH258 (se20 klines
are not in the captures), CH259 (the engine's own files), CH260's res_7d label census. Reward reading (a MAP): rewarded = ``clob_rewards`` of capture k
non-empty. Category as the CH240 map.
"""

from __future__ import annotations

import hashlib
import math
import resource
import sys
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import population_map_ch251 as c251

VERSION = "ch261-population-map-v1"
GRID_S, GAP_MAX_S, EPS, DEFAULT_TICK = c240.GRID_S, c240.GAP_MAX_S, c240.EPS, c240.DEFAULT_TICK
CATS, RWS = c240.CATS, c240.RWS
PRE_FEE_DEPLOY = c251.PRE_FEE_DEPLOY
ELIG = "nonsports_excrypto"
WIDEN_TICKS = 2.0
COVER_MIN = 20
BATCH_GAP_S, BATCH_MIN, BATCH_CAP, COMPLETE_MIN, SPAN_S, PSEUDO_GAP_S, UNITS_DAY_MIN = 120.0, 3, 30, 0.60, 120.0, 7 * 86400.0, 24
FAV_HI, FAV_LO = 0.85, 0.15
BURST_MIN = 5.0
TOP_A, TOP_B = 200, 1000
FEE_STAKE_EDGES = (0.0, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05)
EXT_COLS = (*c251.EXT_COLS, "accepting_orders", "uma_resolution_statuses", "event_comment_count", "event_volume")
ROW_COLS = c251.ROW_COLS
UNKNOWN_EXT = (*c251.UNKNOWN_EXT, -1, False, math.nan, math.nan, math.nan)
SPEC_LINES = {"ch252_median_fee_free_unrewarded_widenings_below_which_lt13_is_not_drafted": 40, "ch255_traded_first_of_day_flips_per_capture_line": 690}
NOT_MAPPED = {
    "k_plus_1_targets": "unavailable: CH252's re-tightening over (k, k+1], CH253's own change over (k, k+1], and any 'two-sided at k + 1' condition need capture k + 1; this map never opens it (counts at k - 1 and k only)",
    "ch252_carry_reward_reading": "unavailable: the carry reading (listed_carry24h_v2) with the CLOB feed adjudicating is not in the captures; the MAP reading (clob_rewards non-empty at k) is printed instead",
    "liquidity_tier": "unavailable: no tier definition is fixed and the captures carry no tier; tier x category x age distributions are printed as category x age only (CH252, CH255, CH260)",
    "ch254_vanished_at_k_plus_1": "unavailable: 'vanished at k + 1 with a resolved status' needs capture k + 1 and the resolution status; printed instead: favourites at k - 1 that are absent from the open rows at k, and crashes with UMA-proposed at k",
    "ch254_dollar_size": "partial: the collapsing market's sidecar volume_num at k where present (about 17% of rows), not a dollar position size",
    "ch255_page_index_visibility": "unavailable: page_index is not read (collector sort order unconfirmed); only the event_volume rank is printed",
    "ch257_post_reopen_move": "partial: only the move across the reopen capture (last halted mid at k - 1 to the reopened mid at k); the move after the reopen would need k + 1",
    "ch257_halt_reading": "reading, not a venue fact: halted = accepting_orders false on an open, active, binary row at the capture",
    "ch258_stress_slots": "unavailable: the crypto stress slots need se20's kline files, which are not in the snapshot captures (a separate light step)",
    "ch259_prediction_dispersion": "unavailable: reads the engine's own prediction files (a separate light step by the builder), not the captures",
    "ch260_res7d_census": "unavailable: res_7d rows by fee panel x price bin x tier need the engine's label store (outcomes); this map holds none",
    "ch253_design_stage_gates": "not mapped: per-batch SD standardisation, the pseudo-batch slope and the permutation structure are design-stage items; the category VIF is derived from the printed correlation only",
}
CODE_FILES = (Path(__file__), Path(__file__).resolve().parents[2] / "scripts" / "run_ch261_map.py")


def code_sha256() -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CODE_FILES if p.exists()}


def _accepting(v) -> int:
    s = str(v).strip().lower()
    return 1 if s in ("true", "1", "1.0", "t") else 0 if s in ("false", "0", "0.0", "f") else -1


def read_ext(path: Path | None, keep: set) -> dict:
    """{market_id: ext tuple}: the CH251 8-tuple (cat, rw, tick, volume_num, fee, fee_src, rebate_coef, created_at) + (accepting -1/0/1, uma_proposed, event_comment_count, event_volume, fee rate). ``keep`` only."""
    out: dict = {}
    if path is None or not Path(path).exists():
        return out
    it = c240._iter_csv(path, EXT_COLS)
    present = next(it, None)
    if present is None:
        return out
    has_rw, has_fe = present[EXT_COLS.index("clob_rewards")], present[EXT_COLS.index("fees_enabled")]
    for mid, ft, fc, ss, rw, tk, vn, fe, fs, cr, acc, uma, ecc, evol in it:
        if mid not in keep:
            continue
        t = c240._f(tk)
        fee, src, coef = c251.fee_class(fe, has_fe, fs)
        rate = c251.fee_parse(fs)[0]
        out[mid] = (c240.category_of(ft, fc, ss, True), c240.reward_status(rw, True, has_rw), t if t > 0 else DEFAULT_TICK, c240._f(vn), fee, src, coef, sys.intern(cr),
                    _accepting(acc), "propos" in str(uma).lower(), c240._f(ecc), c240._f(evol), rate)
    return out


def _med(vals: list) -> float:
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _size_bk(n: int) -> str:
    return "3" if n == 3 else "4-5" if n <= 5 else "6-10" if n <= 10 else "11-30" if n <= 30 else "31+"


class Mapper:
    """Feeds captures in time order; keeps only the state of capture k - 1 plus small per-day accumulators."""

    def __init__(self) -> None:
        self.prev: dict | None = None  # mid -> (event, bid, ask, two, rec_ts, cat, vol)
        self.prev_t = math.nan
        self.prev_events: dict = {}  # neg-risk event -> {mid: (mid_price, vol)} of complete events at k - 1
        self.prev_comments: dict = {}  # eligible event -> (comment_count, event_volume) at k - 1
        self.cts: dict = {}  # market -> created_at epoch (parsed once)
        self.halts: dict = {}  # mid -> [captures halted, left_censored, last mid price, cat]
        self.flip_day: dict = {}
        self.flip_day_of = ""
        self.day = ""
        self.day_units: Counter = Counter()
        self.day_closed: list[dict] = []
        self.cap_lvl: list[Counter] = []
        self.cap_chg: list[Counter] = []
        self.events: dict[str, set] = {}
        self.cat_days: set = set()
        self.arrays: dict[str, array] = {}
        self.corr: dict[str, c251._Corr] = {}
        self.n_captures = 0
        self.n_changes = 0
        self.notes = Counter()

    def _arr(self, key: str) -> array:
        return self.arrays.setdefault(key, array("f"))

    def _corr(self, key: str) -> c251._Corr:
        return self.corr.setdefault(key, c251._Corr())

    def _created(self, mid: str, s: str) -> float:
        v = self.cts.get(mid)
        if v is None:
            v = c240.parse_utc(s) if s else math.nan
            self.cts[mid] = v
        return v

    def _flush_day(self) -> None:
        if self.day:
            self.day_closed.append({"day": self.day, "batches_with_a_unit": len(self.day_units), "batches_ge_24_units": sum(1 for v in self.day_units.values() if v >= UNITS_DAY_MIN)})
        self.day_units = Counter()

    def feed(self, t: float, rows: dict, ext: dict) -> None:
        self.n_captures += 1
        day = c240.day_of(t)
        if day != self.day:
            self._flush_day()
            self.day = day
            self.flip_day = {}
        lvl, chg = Counter(), Counter()
        has_prev = self.prev is not None and 0 < t - self.prev_t <= GAP_MAX_S
        if not has_prev and self.prev is not None:
            self.notes["previous_capture_gap_too_large"] += 1
        if not has_prev:
            self.halts = {}
        if has_prev:
            self.n_changes += 1
        prev = self.prev if has_prev else {}
        rec_memo: dict = {}

        def rts(s: str) -> float:
            v = rec_memo.get(s)
            if v is None:
                v = rec_memo[s] = c240.parse_utc(s)
            return v

        cur: dict = {}
        units: dict = {}  # complete (two-sided at k - 1 and k): mid -> (ds, ev, cat, rec_k, rec_p, ct)
        events: dict = {}
        evvol: dict = {}
        ev_cat: dict = {}
        cm_k: dict = {}  # eligible event -> (comment_count, event_volume) at k
        elig_two = 0
        wd_on_cell: Counter = Counter()
        wd_free: list = []
        for mid, (ev, bid, ask, two, nr, rec, _liq) in rows.items():
            x = ext.get(mid, UNKNOWN_EXT)
            cat, rw, tick, vol, fee, _src, _coef, created, acc, uma, ecc, evol, rate = x
            mp = (bid + ask) / 2.0 if two else math.nan
            rt = rts(rec)
            cur[mid] = (ev, bid, ask, two, rt, cat, vol)
            if ev:
                ev_cat.setdefault(ev, set()).add(cat)
            if cat == ELIG and ev and math.isfinite(evol):
                evvol[ev] = evol
            if nr and ev:
                events.setdefault(ev, []).append(mid)
            if cat == ELIG:
                lvl["ch256/eligible_rows"] += 1
                if math.isfinite(ecc):
                    lvl["ch256/eligible_rows_with_comment_field"] += 1
                if ev and ev not in cm_k:
                    cm_k[ev] = (ecc, evol)
            # CH257 halts (level)
            if acc == 0:
                lvl[f"ch257/halted_rows/{cat}"] += 1
                if two:
                    lvl[f"ch257/halted_rows_two_sided/{cat}"] += 1
            if two:
                lvl[f"ch252/units_two_sided_k/{fee}/{rw}/{cat}"] += 1
                if cat == ELIG:
                    elig_two += 1
                if mp >= FAV_HI:
                    lvl[f"ch254/favourite_rows/{cat}"] += 1
                lvl[f"ch254/two_sided_rows/{cat}"] += 1
                if fee == "fee_on" and math.isfinite(rate) and rate > 0:
                    fps = rate * (1.0 - mp)
                    bi = max(i for i, e in enumerate(FEE_STAKE_EDGES) if fps >= e)
                    lvl[f"ch260/fee_per_stake_ge_{FEE_STAKE_EDGES[bi]:g}/{rw}/{cat}"] += 1
                    lvl[f"ch260/fee_on_rows/{rw}/{cat}"] += 1
            p = prev.get(mid)
            if p is not None and two and p[3]:
                ds = (ask - bid) - (p[2] - p[1])
                ct = self._created(mid, created)
                units[mid] = (ds, ev, cat, rt, p[4], ct)
                thr = WIDEN_TICKS * tick - EPS
                chg[f"ch252/units_complete/{fee}/{rw}/{cat}"] += 1
                age = "age_na" if not math.isfinite(ct) else "pre_0330" if ct < PRE_FEE_DEPLOY else "post_0330"
                if ds >= thr:
                    chg[f"ch252/widenings/{fee}/{rw}/{cat}"] += 1
                    chg[f"ch252/widenings_age/{fee}/{rw}/{cat}/{age}"] += 1
                    if rw == "unrewarded" and fee == "fee_on":
                        wd_on_cell[(cat, age)] += 1
                    elif rw == "unrewarded" and fee == "fee_free":
                        wd_free.append((cat, age))
                elif ds <= -thr:
                    chg[f"ch252/narrowings/{fee}/{rw}/{cat}"] += 1
                # CH254 collapses (k - 1 -> k)
                m_p = (p[1] + p[2]) / 2.0
                if m_p >= FAV_HI and mp <= FAV_LO:
                    kind = "crash_uma_proposed_at_k" if uma else "crash_no_uma_proposal"
                    chg[f"ch254/collapses/{kind}/{cat}"] += 1
                    self.cat_days.add((cat, day))
                    if math.isfinite(vol):
                        self._arr(f"ch254/collapse_volume_num/{cat}").append(vol)
                        chg[f"ch254/collapses_with_volume_num/{cat}"] += 1
        for cat, age in wd_free:
            chg[f"ch252/fee_free_unrewarded_widenings_classed/{cat}"] += 1
            if wd_on_cell[(cat, age)] >= COVER_MIN:
                chg[f"ch252/fee_free_unrewarded_widenings_in_covered_cell_proxy/{cat}"] += 1
        lvl["ch253/eligible_rows_two_sided_k"] += elig_two
        if has_prev:
            for mid, p in prev.items():  # favourites at k - 1 absent from the open rows at k
                if mid not in rows and p[3] and (p[1] + p[2]) / 2.0 >= FAV_HI:
                    chg[f"ch254/favourites_km1_absent_from_open_rows_at_k/{p[5]}"] += 1
        self._halts(has_prev, rows, ext, cur, lvl, chg)
        self._batches(has_prev, rows, ext, units, lvl, chg)
        self._flips(has_prev, events, rows, ext, ev_cat, evvol, lvl, chg, day)
        self._comments(has_prev, cm_k, chg)
        self.prev, self.prev_t = cur, t
        self.prev_comments = cm_k
        self.cap_lvl.append(lvl)
        if has_prev:
            self.cap_chg.append(chg)

    # -- CH257 -----------------------------------------------------------------------------------------------------------------------
    def _halts(self, has_prev, rows, ext, cur, lvl, chg) -> None:
        now = {mid for mid in rows if ext.get(mid, UNKNOWN_EXT)[8] == 0}
        for mid in list(self.halts):
            if mid in now:
                continue
            st = self.halts.pop(mid)
            if mid not in rows:
                chg[f"ch257/halt_ended_row_left_open_set/{st[3]}"] += 1
                continue
            two = cur[mid][3]
            if st[1]:
                chg[f"ch257/halt_reopened_left_censored/{st[3]}"] += 1
            else:
                chg[f"ch257/halt_reopened_observed_start/{st[3]}"] += 1
                self._arr(f"ch257/halt_length_captures/{st[3]}").append(st[0])
            if two and math.isfinite(st[2]):
                self._arr(f"ch257/reopen_abs_move_across_reopen_capture/{st[3]}").append(abs((cur[mid][1] + cur[mid][2]) / 2.0 - st[2]))
        for mid in now:
            x = cur[mid]
            price = (x[1] + x[2]) / 2.0 if x[3] else math.nan
            st = self.halts.get(mid)
            if st is None:
                self.halts[mid] = [1, not has_prev, price, x[5]]
            else:
                st[0] += 1
                st[2] = price
        if not has_prev:
            return
        for mid in now:
            chg[f"ch257/halted_rows_with_previous_capture/{cur[mid][5]}"] += 1

    # -- CH256 -----------------------------------------------------------------------------------------------------------------------
    def _comments(self, has_prev, cm_k, chg) -> None:
        if not has_prev:
            return
        for ev, (ecc, evol) in cm_k.items():
            q = self.prev_comments.get(ev)
            if q is None:
                continue
            chg["ch256/event_captures"] += 1
            if not (math.isfinite(ecc) and math.isfinite(q[0])):
                continue
            chg["ch256/event_captures_with_comment_field_both"] += 1
            d = ecc - q[0]
            if d != 0:
                chg["ch256/event_captures_comment_changed"] += 1
            if d >= BURST_MIN:
                chg["ch256/comment_bursts_ge5"] += 1
            if math.isfinite(evol) and math.isfinite(q[1]):
                self._corr("ch256/comment_change_vs_event_volume_change").add(d, evol - q[1])

    # -- CH255 -----------------------------------------------------------------------------------------------------------------------
    def _flips(self, has_prev, events, rows, ext, ev_cat, evvol, lvl, chg, day) -> None:
        new_prev: dict = {}
        thr_a = thr_b = math.nan
        if evvol:
            s = sorted(evvol.values(), reverse=True)
            thr_a, thr_b = s[min(TOP_A, len(s)) - 1], s[min(TOP_B, len(s)) - 1]
        for ev, mids in events.items():
            n = len(mids)
            if n < 2 or not all(rows[m][3] for m in mids):
                continue
            data = {m: ((rows[m][1] + rows[m][2]) / 2.0, ext.get(m, UNKNOWN_EXT)[3]) for m in mids}
            new_prev[ev] = data
            pv = self.prev_events.get(ev) if has_prev else None
            if pv is None or pv.keys() != data.keys():
                continue
            o_p = sorted(mids, key=lambda m: pv[m][0], reverse=True)
            o_k = sorted(mids, key=lambda m: data[m][0], reverse=True)
            ties = pv[o_p[0]][0] - pv[o_p[1]][0] <= EPS or data[o_k[0]][0] - data[o_k[1]][0] <= EPS
            cat = c251.event_cat(ev_cat.get(ev, {"unknown"}))
            bk = c240.size_bucket(n) or "11+"
            chg[f"ch255/complete_events/{bk}/{cat}"] += 1
            if ties:
                chg[f"ch255/events_leader_tie_excluded/{cat}"] += 1
                continue
            if o_k[0] == o_p[0]:
                continue
            new_l, old_l = o_k[0], o_p[0]
            runner_up = new_l == o_p[1]
            vols = (pv[new_l][1], data[new_l][1], pv[old_l][1], data[old_l][1])
            if not all(math.isfinite(v) for v in vols) or vols[1] < vols[0] or vols[3] < vols[2]:
                tr = "unknown"
            else:
                tr = "traded" if (vols[1] > vols[0] or vols[3] > vols[2]) else "quote_only"
            first = ev not in self.flip_day
            self.flip_day[ev] = day
            ev_v = evvol.get(ev, math.nan)
            vis = "na" if not math.isfinite(ev_v) else "top200" if ev_v >= thr_a else "top1000" if ev_v >= thr_b else "other"
            kind = "to_runner_up" if runner_up else "to_lower_rank"
            chg[f"ch255/flips_all/{kind}/{cat}"] += 1
            self.events.setdefault(f"ch255/flip_events/{cat}", set()).add(ev)
            if not runner_up:
                continue
            if first:
                chg[f"ch255/flips_first_of_day/{tr}/{bk}/{vis}/{cat}"] += 1
                chg[f"ch255/flips_first_of_day_total/{tr}/{cat}"] += 1
                if n == 2:
                    chg[f"ch255/flips_first_of_day_two_member_held_out/{tr}/{cat}"] += 1
                else:
                    chg[f"ch255/flips_first_of_day_ex_two_member/{tr}/{cat}"] += 1
            else:
                chg[f"ch255/reflips/{cat}"] += 1
        self.prev_events = new_prev

    # -- CH253 -----------------------------------------------------------------------------------------------------------------------
    def _batches(self, has_prev, rows, ext, units, lvl, chg) -> None:
        items = []
        for mid in rows:
            if mid in ext:
                ct = self._created(mid, ext[mid][7])
                if math.isfinite(ct):
                    items.append((ct, mid))
            else:
                lvl["ch253/rows_without_sidecar_created_at"] += 1
        items.sort()
        batches: list[list] = []
        cur_b: list = []
        last = math.nan
        for ct, mid in items:
            if cur_b and ct - last > BATCH_GAP_S:
                batches.append(cur_b)
                cur_b = []
            cur_b.append((ct, mid))
            last = ct
        if cur_b:
            batches.append(cur_b)
        lvl["ch253/batches_all_sizes"] += len(batches)
        elig_in_cross = 0
        cat_s: Counter = Counter()
        cat_n: Counter = Counter()
        elig_ts: list = []
        for ds, _ev, cat, _rk, _rp, ct in units.values():
            cat_s[cat] += ds
            cat_n[cat] += 1
            if cat == ELIG and math.isfinite(ct):
                elig_ts.append(ct)
        elig_ts.sort()
        n_el = len(elig_ts)
        for b in batches:
            size = len(b)
            if size < BATCH_MIN:
                continue
            evs = Counter((rows[m][0] or "m:" + m) for _ct, m in b)
            if len(evs) < 2:
                lvl["ch253/batches_ge3_single_event"] += 1
                continue
            bk = _size_bk(size)
            lvl[f"ch253/batches_cross_event/{bk}"] += 1
            elig = [m for _ct, m in b if ext[m][0] == ELIG]
            elig_in_cross += len(elig)
            if not has_prev:
                continue
            comp = [m for _ct, m in b if m in units]
            frac = len(comp) / size
            if frac < COMPLETE_MIN:
                chg["ch253/batch_captures_unavailable_under_60pct_complete"] += 1
                chg["ch253/eligible_rows_in_unavailable_batch_captures"] += len(elig)
                continue
            mk = _med([units[m][3] for m in comp])
            mp_ = _med([units[m][4] for m in comp])
            ret = [m for m in comp if abs(units[m][3] - mk) <= SPAN_S and abs(units[m][4] - mp_) <= SPAN_S]
            chg["ch253/batch_captures_available"] += 1
            chg["ch253/complete_members_dropped_by_span"] += len(comp) - len(ret)
            s_all = sum(units[m][0] for m in ret)
            s_ev: Counter = Counter()
            n_ev: Counter = Counter()
            b_s: Counter = Counter()
            b_n: Counter = Counter()
            for m in ret:
                u = units[m]
                key = u[1] or "m:" + m
                s_ev[key] += u[0]
                n_ev[key] += 1
                b_s[u[2]] += u[0]
                b_n[u[2]] += 1
            key0 = f"{b[0][0]:.0f}-{min(m for _c, m in b)}"
            for m in ret:
                u = units[m]
                if u[2] != ELIG:
                    continue
                key = u[1] or "m:" + m
                mates = len(ret) - n_ev[key]
                if mates < 2:
                    chg["ch253/eligible_units_under_2_complete_cross_event_mates"] += 1
                    continue
                if size - evs[key] > BATCH_CAP:
                    chg["ch253/eligible_units_over_cap_arm_gt30_cross_event_mates"] += 1
                    continue
                chg["ch253/primary_units"] += 1
                self.day_units[key0] += 1
                m_i = (s_all - s_ev[key]) / mates
                self._corr("ch253/same_slot_corr_own_vs_mates_mean_innovation").add(u[0], m_i)
                cn = cat_n[ELIG] - b_n[ELIG]
                if cn >= 1:
                    c_i = (cat_s[ELIG] - b_s[ELIG]) / cn
                    self._corr("ch253/mates_mean_vs_category_nonmates_mean_innovation").add(m_i, c_i)
                if n_el >= 10 and math.isfinite(u[5]):
                    dec = min(9, bisect_left(elig_ts, u[5]) * 10 // n_el)
                    lo, hi = dec * n_el // 10, (dec + 1) * n_el // 10
                    chunk_lo = bisect_left(elig_ts, u[5] - PSEUDO_GAP_S, lo, hi)
                    chunk_hi = bisect_right(elig_ts, u[5] + PSEUDO_GAP_S, lo, hi)
                    avail = (hi - lo) - (chunk_hi - chunk_lo)
                    chg["ch253/primary_units_pseudo_batch_covered" if avail >= mates else "ch253/primary_units_pseudo_batch_not_covered"] += 1
        lvl["ch253/eligible_rows_in_cross_event_batch_ge3"] += elig_in_cross

    def finish(self) -> dict:
        self._flush_day()
        self.day = ""
        out: dict = {"level_counts": {}, "change_counts": {}}
        for name, caps, per in (("level_counts", self.cap_lvl, self.n_captures), ("change_counts", self.cap_chg, self.n_changes)):
            days = per * GRID_S / 86400.0
            for k in sorted({k for c in caps for k in c}):
                st = c240._stats([float(c.get(k, 0)) for c in caps])
                st["projected_21d"] = st["total"] * 21.0 / days if days > 0 else None
                out[name][k] = st
        out["distinct_events_over_span"] = {k: len(v) for k, v in sorted(self.events.items())}
        out["category_days_with_a_collapse"] = dict(sorted(Counter(c for c, _d in self.cat_days).items()))
        out["quantiles"] = {k: c240._quantiles(a) for k, a in sorted(self.arrays.items())}
        out["correlations"] = {k: {"n": c.n, "corr": c.corr()} for k, c in sorted(self.corr.items())}
        r = out["correlations"].get("ch253/mates_mean_vs_category_nonmates_mean_innovation", {}).get("corr")
        out["derived"] = {"ch253/category_vif_from_printed_corr": (1.0 / (1.0 - r * r) if r is not None and r * r < 1 else None)}
        out["ch253_batch_days"] = self.day_closed
        lv, ch = out["level_counts"], out["change_counts"]

        def share(sec: dict, num: str, den: str) -> float | None:
            a, b = sec.get(num), sec.get(den)
            return a["total"] / b["total"] if a and b and b["total"] else None

        sh: dict = {"ch253/eligible_rows_in_cross_event_batch_ge3_share": share(lv, "ch253/eligible_rows_in_cross_event_batch_ge3", "ch253/eligible_rows_two_sided_k")}
        sh["ch253/pseudo_batch_coverage_share"] = share(ch, "ch253/primary_units_pseudo_batch_covered", "ch253/primary_units")
        sh["ch256/comment_field_presence_share_eligible_rows"] = share(lv, "ch256/eligible_rows_with_comment_field", "ch256/eligible_rows")
        sh["ch256/comment_change_share_of_event_captures"] = share(ch, "ch256/event_captures_comment_changed", "ch256/event_captures_with_comment_field_both")
        for k, v in ch.items():
            if k.startswith("ch252/widenings/"):
                sfx = k[len("ch252/widenings/"):]
                den = ch.get(f"ch252/units_complete/{sfx}")
                sh[f"ch252/widening_share/{sfx}"] = v["total"] / den["total"] if den and den["total"] else None
            if k.startswith("ch252/fee_free_unrewarded_widenings_in_covered_cell_proxy/"):
                c = k.rsplit("/", 1)[1]
                sh[f"ch252/fee_free_unrewarded_cell_coverage_proxy/{c}"] = share(ch, k, f"ch252/fee_free_unrewarded_widenings_classed/{c}")
        for k in lv:
            if k.startswith("ch254/favourite_rows/"):
                c = k.rsplit("/", 1)[1]
                sh[f"ch254/favourite_share_of_two_sided_rows/{c}"] = share(lv, k, f"ch254/two_sided_rows/{c}")
            if k.startswith("ch257/halted_rows_two_sided/"):
                c = k.rsplit("/", 1)[1]
                sh[f"ch257/halted_two_sided_share/{c}"] = share(lv, k, f"ch257/halted_rows/{c}")
        flips = sum(v["total"] for k, v in ch.items() if k.startswith("ch255/flips_first_of_day_total/"))
        reflips = sum(v["total"] for k, v in ch.items() if k.startswith("ch255/reflips/"))
        sh["ch255/reflip_share_of_to_runner_up_flips"] = reflips / (flips + reflips) if flips + reflips else None
        out["shares"] = dict(sorted(sh.items()))

        def line(sec: dict, key: str) -> dict:
            v = sec.get(key)
            return {k: v.get(k) for k in ("n_captures", "min", "median", "mean", "total")} if v else {"n_captures": 0}

        out["headline"] = {
            "ch252_fee_free_unrewarded_widenings_per_capture_nonsports_excrypto": line(ch, f"ch252/widenings/fee_free/unrewarded/{ELIG}"),
            "ch252_fee_on_unrewarded_widenings_per_capture_nonsports_excrypto": line(ch, f"ch252/widenings/fee_on/unrewarded/{ELIG}"),
            "ch252_fee_free_unrewarded_narrowings_per_capture_nonsports_excrypto": line(ch, f"ch252/narrowings/fee_free/unrewarded/{ELIG}"),
            "ch253_primary_units_per_capture": line(ch, "ch253/primary_units"),
            "ch255_traded_first_of_day_flips_per_capture_nonsports_excrypto": line(ch, f"ch255/flips_first_of_day_total/traded/{ELIG}"),
            "spec_lines_reported_not_applied": SPEC_LINES,
        }
        out["notes"] = dict(self.notes)
        return out


def run_map(roots: list[Path], start_utc: str, end_utc: str) -> dict:
    caps = c240.discover(roots, start_utc, end_utc)
    t0, t1 = c240.parse_utc(start_utc), c240.parse_utc(end_utc)
    mp = Mapper()
    inputs: list[dict] = []
    for c in caps:
        d = Path(c["dir"])
        ext_p = d / "rows_ext.csv.gz"
        for f in [d / "manifest.json", d / "rows.csv.gz"] + ([ext_p] if ext_p.exists() else []):
            inputs.append({"path": str(f), "bytes": f.stat().st_size, "sha256": c240.sha256_file(f)})
        rows = c251.read_rows(d / "rows.csv.gz")
        ext = read_ext(ext_p if ext_p.exists() else None, set(rows))
        mp.feed(c["start"], rows, ext)
        del rows, ext
    starts = [c["start"] for c in caps]
    gaps = []
    edges = [t0 - GRID_S / 2, *starts, t1 - GRID_S / 2 + 1]
    for a, z in zip(edges, edges[1:], strict=False):
        if z - a > GAP_MAX_S:
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            gaps.append({"after": datetime.fromtimestamp(a, UTC).strftime(fmt), "before": datetime.fromtimestamp(z, UTC).strftime(fmt), "hours": round((z - a) / 3600, 2)})
    res = mp.finish()
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "version": VERSION, "kind": "CH261 LT13 population map: counts only, k = 0, uncounted; captures k and k - 1 only; nothing from capture k + 1 or later; no resolution winner, no price change after an origin, no P&L",
        "span": {"start_utc": start_utc, "end_utc": end_utc, "expected_2h_slots": int((t1 - t0) // GRID_S)},
        "captures": {"covered": len(caps), "covered_ids": [c["id"] for c in caps], "with_previous_capture_k_minus_1": mp.n_changes,
                     "missing_expected": max(0, int((t1 - t0) // GRID_S) - len(caps)), "gaps_over_2h30": gaps, "covered_days": len(caps) * GRID_S / 86400.0},
        "reward_reading": "MAP reading, not listed_carry24h_v2: rewarded = clob_rewards of capture k non-empty; unrewarded = sidecar row with an empty field; unknown = no sidecar row or column",
        "category_reading": "as the CH240 / CH251 maps; eligible = nonsports_excrypto",
        "conventions": {
            "population": "open active binary rows; two-sided = 0 < best_bid < best_ask <= 1; mid = (bid + ask) / 2; spread = ask - bid; complete = two-sided at k - 1 and k",
            "widening": "spread_k - spread_{k-1} >= 2 x order_price_min_tick_size (tick of capture k's sidecar); narrowing the mirror image; per-capture min / median / mean over captures with a previous capture (zeros included)",
            "batch": "markets with a sidecar created_at in the capture's open binary rows, sorted; a batch closes when > 120 s pass without a new creation; counted when >= 3 markets span >= 2 events; mates exclude the unit's own event; > 30 cross-event mates is a reported arm; a batch-capture with < 60% of its members complete is unavailable (counted); complete members must lie within 120 s of the batch median receipt at k and at k - 1",
            "pseudo_batch": "coverage only: an eligible complete unit is covered if its created_at decile (over complete eligible units at the capture) holds at least as many units created >= 7 days from its own as it has complete mates",
            "flip": "complete neg-risk events (all members two-sided at k - 1 and k, same members); the leader by mid changes and the new leader was the runner-up; ties at the top excluded; first of the UTC day; traded = a leader's sidecar volume_num rose (both known), quote_only = unchanged, else unknown; events of 2 members counted separately and held out; visibility = event_volume rank among non-sports ex-crypto events at k",
            "collapse": "two-sided at k - 1 and k, mid >= 0.85 at k - 1 and <= 0.15 at k",
            "fee_per_stake": "fee-on two-sided rows: rate x (1 - mid), cumulative bins at 0, 0.5, 1, 2, 3, 4, 5 cents per dollar",
            "comments": "event_comment_count of the sidecar on eligible events; burst = a rise of >= 5 between k - 1 and k",
            "halt": "accepting_orders false on an open active binary row; length in captures from first observed halted capture to the reopening capture; halts already open at the first capture or after a gap are left-censored and not in the length distribution",
            "projection": "total x 21 / covered days"},
        "not_mapped": NOT_MAPPED,
        "peak_rss_mb": round(rss / (2**20 if sys.platform == "darwin" else 1024), 1),
        "inputs": inputs, "code_sha256": code_sha256(), **res,
    }
