# ruff: noqa: E501
"""CH251, the LT12 population map (docs/research_lab/CREATIVE_HYPOTHESES_2026-10-31.md section 2 F). COUNTS ONLY, k = 0, uncounted.

A streaming reader over the host's 2-hourly captures (``rows.csv.gz``, the ``rows_ext.csv.gz`` sidecar, ``manifest.json``), modelled on the CH240 map
(``boundary_map_ch240``; its helpers are imported, never edited). For each capture k it uses ONLY capture k and capture k - 1 fields at their own
receipt: nothing from capture k + 1 or later is read, no price target, no P&L. Captures are read one at a time in time order (a two-capture window).

Counted (per capture; strata = category sports / crypto / nonsports_excrypto / unknown, reward status rewarded / unrewarded / unknown):
  CH245  two-member neg-risk events (open binary rows grouped by event_id) by event category and pair reward class (rr / ru / uu / unk), complete pairs
         (both books two-sided at k - 1 and k), the receipt-span retention at 120 s (both rows' received_utc, at k and at k - 1), the mirror gaps
         g_A = ask_A + bid_B - 1 and g_B = bid_A + ask_B - 1 at k (quantiles), the thin / sym / dense shares at k - 1 (wider book = thin), the same-slot
         correlation of the two books' spread innovations (k against k - 1 only; a state, not a target; symmetrised over the ordered pairs);
  CH244  neg-risk ladders of 3+ members by reward class (mixed = >= 1 rewarded and >= 1 unrewarded member), member counts by status, completeness by
         status, the within-event status-liquidity correlation (liquidity of capture k), the shock share
         shock_i = 1[max over siblings j != i of |d_j| >= 2 x tick_e] on complete (k - 1, k) ladders (tick_e = largest member tick);
  CH243  traded / quote-only / unusable 2 h movers (|d| >= 0.01, p_{k-1} in [0.04, 0.96]) by fee source (flag off, rate 0, fee on) and by market age
         (created before 2026-03-30), and a coverage PROXY of the fee-free units by category x age cell (>= 20 fee-on movers in the capture);
  CH250  open binary rows, two-sided rows and traded / quote-only movers by the 2 x 2 of fee class x reward status, the maker rebate per share
         (rebateRate x rate x p(1 - p)) histogram of fee-on rows by cell;
  CH248  movers in complete two-member pairs by who printed (own / twin / both / neither / unknown) from the sidecar ``volume_num`` at k and k - 1.

NOT MAPPED (see ``not_mapped`` in the output): CH246's matcher (question text and groupItemTitle are not in the captures), CH242's split resolutions
(no label store in the captures), CH250's tier cut and minute-pay distribution, CH243's tier x category x age cell-matched control (only a proxy).
Reward reading (a MAP, not listed_carry24h_v2): rewarded = ``clob_rewards`` of capture k non-empty. Category as the CH240 map.
"""

from __future__ import annotations

import hashlib
import json
import math
import resource
import sys
from array import array
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import boundary_map_ch240 as c240

VERSION = "ch251-population-map-v1"
GRID_S = c240.GRID_S
GAP_MAX_S = c240.GAP_MAX_S
MOVE_MIN = c240.MOVE_MIN
EPS = c240.EPS
DEFAULT_TICK = c240.DEFAULT_TICK
SPAN_S = 120.0
P_LO, P_HI = 0.04, 0.96
SHOCK_TICKS = 2.0
PRE_FEE_DEPLOY = datetime(2026, 3, 30, tzinfo=UTC).timestamp()
COVER_MIN = 20
REBATE_EDGES = (0.0, 0.0005, 0.001, 0.002, 0.003, 0.005)
ROW_COLS = ("market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "neg_risk", "liquidity")
EXT_COLS = ("market_id", "fee_type", "fee_category", "series_slugs", "clob_rewards", "order_price_min_tick_size", "volume_num", "fees_enabled", "fee_schedule", "created_at")
UNKNOWN_EXT = ("unknown", "unknown", DEFAULT_TICK, math.nan, "unknown", "no_sidecar", 0.0, "")
NOT_MAPPED = {
    "ch246_duplicate_pairs": "not mapped: the matcher needs gamma_rules question text and groupItemTitle, which are not in rows.csv.gz / rows_ext.csv.gz; it is a separate light step over stream_gamma_rules with a matcher pinned by sha256 and a 50-pair hand audit (no matcher exists yet)",
    "ch242_split_resolutions": "not mapped: no label store or resolution records in the captures (the engine's label store and the resolution fetch are other streams); a separate light step",
    "ch250_tier_cut": "not mapped: the spec names a 'tier' cut but the liquidity-tier definition is not fixed in the spec; counts are by cell and category only",
    "ch250_minute_pay": "not mapped: the minute-pay distribution needs the rewards scoring rule 'as quoted', not specified here; only the rebate-per-fill histogram is mapped",
    "ch243_cell_matched_control": "partial proxy only: fee-free units with >= 20 fee-on movers in the same capture's category x age(pre-03-30) cell; the spec's tier x category x age cell is not mapped (no tier definition)",
    "ch243_corr_vif_blockgate_mde": "not mapped: pooled |corr(fee_free, log1p liquidity)|, VIF, block-gate share and MDEs are design-stage gates computed at the LT12 census, not population counts",
}
CODE_FILES = (Path(__file__), Path(__file__).resolve().parents[2] / "scripts" / "run_ch251_map.py")
CATS, RWS = c240.CATS, c240.RWS


def code_sha256() -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CODE_FILES if p.exists()}


def event_cat(cats: set) -> str:
    return "sports" if "sports" in cats else "crypto" if "crypto" in cats else "unknown" if "unknown" in cats else "nonsports_excrypto"


def ladder_class(statuses: list[str]) -> str:
    r, u = statuses.count("rewarded"), statuses.count("unrewarded")
    if r >= 1 and u >= 1:
        return "mixed"
    if "unknown" in statuses:
        return "unknown_status"
    return "all_rewarded" if r else "all_unrewarded"


def pair_class(sa: str, sb: str) -> str:
    if "unknown" in (sa, sb):
        return "unk"
    return "rr" if sa == sb == "rewarded" else "uu" if sa == sb else "ru"


_FEE_MEMO: dict = {}


def fee_parse(fee_schedule) -> tuple[float, float]:
    """(rate, rebateRate) of a fee_schedule JSON string; (nan, nan) when empty or unparseable."""
    s = fee_schedule if isinstance(fee_schedule, str) else ""
    hit = _FEE_MEMO.get(s)
    if hit is not None:
        return hit
    try:
        d = json.loads(s) if s else {}
        out = (float(d["rate"]), float(d.get("rebateRate", 0.0))) if isinstance(d, dict) and "rate" in d else (math.nan, math.nan)
    except (ValueError, TypeError, KeyError):
        out = (math.nan, math.nan)
    if len(_FEE_MEMO) < 10000:
        _FEE_MEMO[s] = out
    return out


def fee_class(fees_enabled, has_fe_col: bool, fee_schedule) -> tuple[str, str, float]:
    """(fee class fee_on / fee_free / unknown, fee_src, rebate coefficient rebateRate x rate)."""
    rate, rebate = fee_parse(fee_schedule)
    if has_fe_col and str(fees_enabled).strip() != "" and not c240._truthy(fees_enabled):
        return "fee_free", "flag_off", 0.0
    if math.isfinite(rate):
        return ("fee_free", "rate_zero", 0.0) if rate <= 0 else ("fee_on", "rate_pos", (rebate if math.isfinite(rebate) else 0.0) * rate)
    return "unknown", "no_schedule", 0.0


def read_ext(path: Path | None, keep: set) -> dict:
    """{market_id: (cat, rw, tick, volume_num, fee, fee_src, rebate_coef, created_at)} for the markets in ``keep`` only."""
    out: dict = {}
    if path is None or not Path(path).exists():
        return out
    it = c240._iter_csv(path, EXT_COLS)
    present = next(it, None)
    if present is None:
        return out
    has_rw, has_fe = present[EXT_COLS.index("clob_rewards")], present[EXT_COLS.index("fees_enabled")]
    for mid, ft, fc, ss, rw, tk, vn, fe, fs, cr in it:
        if mid not in keep:
            continue
        t = c240._f(tk)
        fee, src, coef = fee_class(fe, has_fe, fs)
        out[mid] = (c240.category_of(ft, fc, ss, True), c240.reward_status(rw, True, has_rw), t if t > 0 else DEFAULT_TICK, c240._f(vn), fee, src, coef, sys.intern(cr))
    return out


def read_rows(path: Path) -> dict:
    """{market_id: (event, bid, ask, two_sided, neg_risk, received_utc, liquidity)} of open active binary rows (last row per market) at the capture's own receipt."""
    out: dict = {}
    it = c240._iter_csv(path, ROW_COLS)
    if next(it, None) is None:
        return out
    for mid, ev, rec, closed, active, binary, bid, ask, nr, liq in it:
        if not (c240._truthy(binary) and (not c240._truthy(closed)) and c240._truthy(active)):
            out.pop(mid, None)
            continue
        b_, a_ = c240._f(bid), c240._f(ask)
        two = b_ > 0 and a_ > 0 and a_ <= 1 and b_ < a_
        out[mid] = (sys.intern(ev), b_, a_, two, c240._truthy(nr), sys.intern(rec), c240._f(liq))
    return out


class _Corr:
    __slots__ = ("n", "sx", "sy", "sxx", "syy", "sxy")

    def __init__(self) -> None:
        self.n, self.sx, self.sy, self.sxx, self.syy, self.sxy = 0, 0.0, 0.0, 0.0, 0.0, 0.0

    def add(self, x: float, y: float) -> None:
        self.n += 1
        self.sx += x
        self.sy += y
        self.sxx += x * x
        self.syy += y * y
        self.sxy += x * y

    def corr(self) -> float | None:
        if self.n < 3:
            return None
        cov = self.sxy - self.sx * self.sy / self.n
        vx, vy = self.sxx - self.sx**2 / self.n, self.syy - self.sy**2 / self.n
        return cov / math.sqrt(vx * vy) if vx > 1e-18 and vy > 1e-18 else None


def _span_ok(ra: str, rb: str) -> bool | None:
    ta, tb = c240.parse_utc(ra), c240.parse_utc(rb)
    if not (math.isfinite(ta) and math.isfinite(tb)):
        return None
    return abs(ta - tb) <= SPAN_S


def _vol_class(own_p: float, own_k: float, twin_p: float, twin_k: float) -> str:
    vals = (own_p, own_k, twin_p, twin_k)
    if not all(math.isfinite(v) for v in vals) or own_k < own_p or twin_k < twin_p:
        return "unknown"
    o, t = own_k > own_p, twin_k > twin_p
    return "both" if o and t else "own_printed" if o else "twin_printed" if t else "neither"


class Mapper:
    """Feeds captures in time order; keeps only per-market / per-event state of capture k - 1."""

    def __init__(self) -> None:
        self.prev: dict | None = None
        self.prev_t = math.nan
        self.prev_pairs: dict = {}  # event -> ({mid: (bid, ask, vol)}, span_ok_at_km1) of two-member events complete at k - 1
        self.prev_ladders: dict = {}  # event -> {mid: mid_price} of complete 3+ member ladders at k - 1
        self.cap_lvl: list[Counter] = []
        self.cap_chg: list[Counter] = []
        self.events: dict[str, set] = {}
        self.arrays: dict[str, array] = {}
        self.corr: dict[str, _Corr] = {}
        self.n_captures = 0
        self.n_changes = 0
        self.notes = Counter()

    def _arr(self, key: str) -> array:
        return self.arrays.setdefault(key, array("f"))

    def _corr(self, key: str) -> _Corr:
        return self.corr.setdefault(key, _Corr())

    def feed(self, t: float, rows: dict, ext: dict) -> None:
        self.n_captures += 1
        lvl, chg = Counter(), Counter()
        has_prev = self.prev is not None and 0 < t - self.prev_t <= GAP_MAX_S
        if not has_prev and self.prev is not None:
            self.notes["previous_capture_gap_too_large"] += 1
        if has_prev:
            self.n_changes += 1
        cur: dict = {}
        events: dict = {}
        movers_by_cell: list = []
        for mid, r in rows.items():
            ev, bid, ask, two, nr, _rec, _liq = r
            cat, rw, _tick, vol, fee, _src, coef, _cr = ext.get(mid, UNKNOWN_EXT)
            lvl[f"ch250/rows_open_binary/{fee}/{rw}/{cat}"] += 1
            if two:
                m_k = (bid + ask) / 2.0
                cur[mid] = (ev, m_k, vol)
                lvl[f"ch250/rows_two_sided/{fee}/{rw}/{cat}"] += 1
                if fee == "fee_on" and coef > 0:
                    rb = coef * m_k * (1.0 - m_k)
                    bi = sum(1 for e in REBATE_EDGES[1:] if rb >= e)
                    lvl[f"ch250/rebate_ps_bin_ge_{REBATE_EDGES[bi]:g}/{rw}/{cat}"] += 1
            if nr and ev:
                events.setdefault(ev, []).append(mid)
        # --- movers (CH243, CH250): capture k against k - 1
        if has_prev:
            cell_on: Counter = Counter()
            for mid, (_ev, m_k, v_k) in cur.items():
                p = self.prev.get(mid)
                if p is None:
                    continue
                d = m_k - p[1]
                if abs(d) < MOVE_MIN - EPS or not (P_LO <= p[1] <= P_HI):
                    continue
                cat, rw, _tick, _v, fee, src, _coef, created = ext.get(mid, UNKNOWN_EXT)
                v_p = p[2]
                kind = "unusable" if (not (math.isfinite(v_k) and math.isfinite(v_p)) or v_k < v_p) else "traded" if v_k > v_p else "quote_only"
                ct = c240.parse_utc(created)
                age = "age_na" if not math.isfinite(ct) else "pre_0330" if ct < PRE_FEE_DEPLOY else "post_0330"
                chg[f"ch250/movers_{kind}/{fee}/{rw}/{cat}"] += 1
                chg[f"ch243/movers_{kind}/{src}/{age}/{cat}"] += 1
                if kind != "unusable":
                    if fee == "fee_on":
                        cell_on[(cat, age)] += 1
                    elif fee == "fee_free":
                        movers_by_cell.append((cat, age))
            for cat, age in movers_by_cell:
                chg[f"ch243/fee_free_movers_classed/{cat}"] += 1
                if cell_on[(cat, age)] >= COVER_MIN:
                    chg[f"ch243/fee_free_movers_in_covered_cell_proxy/{cat}"] += 1
        new_pairs: dict = {}
        new_ladders: dict = {}
        for ev, mids in events.items():
            n = len(mids)
            if n < 2:
                continue
            exts = [ext.get(m, UNKNOWN_EXT) for m in mids]
            cat = event_cat({e[0] for e in exts})
            if n == 2:
                self._pair(ev, sorted(mids), rows, ext, cat, has_prev, lvl, chg, new_pairs)
            else:
                self._ladder(ev, mids, rows, ext, exts, cat, has_prev, lvl, chg, new_ladders)
        self.prev = cur
        self.prev_t = t
        self.prev_pairs = new_pairs
        self.prev_ladders = new_ladders
        self.cap_lvl.append(lvl)
        if has_prev:
            self.cap_chg.append(chg)

    # -- CH245 / CH248 ------------------------------------------------------------------------------------------------------------
    def _pair(self, ev, mids, rows, ext, cat, has_prev, lvl, chg, new_pairs) -> None:
        a, b = mids
        ra, rb = rows[a], rows[b]
        ea, eb = ext.get(a, UNKNOWN_EXT), ext.get(b, UNKNOWN_EXT)
        strat = f"{cat}/{pair_class(ea[1], eb[1])}"
        lvl[f"ch245/two_member_events/{strat}"] += 1
        self.events.setdefault(f"ch245/two_member/{strat}", set()).add(ev)
        if not (ra[3] and rb[3]):
            return
        lvl[f"ch245/two_member_complete_at_k/{strat}"] += 1
        sk = _span_ok(ra[5], rb[5])
        new_pairs[ev] = ({a: (ra[1], ra[2], ea[3]), b: (rb[1], rb[2], eb[3])}, sk)
        pv = self.prev_pairs.get(ev) if has_prev else None
        if pv is None or pv[0].keys() != {a, b}:
            if has_prev:
                chg[f"ch245/complete_at_k_not_complete_pair_km1/{strat}"] += 1
            return
        pdata, sp = pv
        chg[f"ch245/complete_pairs_k_km1/{strat}"] += 1
        if sk is None or sp is None:
            chg[f"ch245/span_unparseable_receipt/{strat}"] += 1
        if sk is not True:
            chg[f"ch245/span_excluded_at_k/{strat}"] += 1
        if sp is not True:
            chg[f"ch245/span_excluded_at_km1/{strat}"] += 1
        retained = sk is True and sp is True
        d_a = (ra[1] + ra[2]) / 2 - sum(pdata[a][:2]) / 2
        d_b = (rb[1] + rb[2]) / 2 - sum(pdata[b][:2]) / 2
        for own, twin, d_i, e_i in ((a, b, d_a, ea), (b, a, d_b, eb)):
            if abs(d_i) < MOVE_MIN - EPS:
                continue
            if not retained:
                chg[f"ch248/movers_in_span_excluded_pairs/{e_i[1]}/{e_i[0]}"] += 1
                continue
            cls = _vol_class(pdata[own][2], ext.get(own, UNKNOWN_EXT)[3], pdata[twin][2], ext.get(twin, UNKNOWN_EXT)[3])
            chg[f"ch248/movers/{cls}/{e_i[1]}/{e_i[0]}"] += 1
            chg[f"ch248/movers_total/{e_i[1]}/{e_i[0]}"] += 1
        if not retained:
            return
        chg[f"ch245/pairs_span_retained/{strat}"] += 1
        chg[f"ch245/member_units_retained/{strat}"] += 2
        g_a, g_b = ra[2] + rb[1] - 1.0, ra[1] + rb[2] - 1.0
        self._arr(f"ch245/mirror_gap_g/{strat}").extend((g_a, g_b))
        if min(g_a, g_b) < -EPS:
            chg[f"ch245/pairs_gap_negative_either/{strat}"] += 1
        sa_p, sb_p = pdata[a][1] - pdata[a][0], pdata[b][1] - pdata[b][0]
        sa_k, sb_k = ra[2] - ra[1], rb[2] - rb[1]
        self._arr(f"ch245/spread_gap_abs_km1/{strat}").append(abs(sa_p - sb_p))
        if abs(sa_p - sb_p) <= EPS:
            chg[f"ch245/sym_units/{strat}"] += 2
        else:
            chg[f"ch245/thin_units/{strat}"] += 1
            chg[f"ch245/dense_units/{strat}"] += 1
        chg[f"ch245/units_total/{strat}"] += 2
        ds_a, ds_b = sa_k - sa_p, sb_k - sb_p
        c = self._corr(f"ch245/spread_innovation_corr/{strat}")
        c.add(ds_a, ds_b)
        c.add(ds_b, ds_a)
        if abs(ds_a) <= EPS and abs(ds_b) <= EPS:
            chg[f"ch245/pairs_both_innovation_zero/{strat}"] += 1
        elif abs(ds_a) > EPS and abs(ds_b) > EPS and (ds_a > 0) == (ds_b > 0):
            chg[f"ch245/pairs_both_nonzero_same_sign/{strat}"] += 1
        elif abs(ds_a) > EPS and abs(ds_b) > EPS:
            chg[f"ch245/pairs_both_nonzero_opposite_sign/{strat}"] += 1
        else:
            chg[f"ch245/pairs_one_innovation_zero/{strat}"] += 1

    # -- CH244 ---------------------------------------------------------------------------------------------------------------------
    def _ladder(self, ev, mids, rows, ext, exts, cat, has_prev, lvl, chg, new_ladders) -> None:
        n = len(mids)
        bk = c240.size_bucket(n)
        sts = [e[1] for e in exts]
        cls = ladder_class(sts)
        lvl[f"ch244/ladders/{cls}/{bk}/{cat}"] += 1
        complete = all(rows[m][3] for m in mids)
        if complete:
            lvl[f"ch244/ladders_complete/{cls}/{bk}/{cat}"] += 1
        if cls == "mixed":
            self.events.setdefault(f"ch244/mixed/{cat}", set()).add(ev)
            for m, st in zip(mids, sts, strict=True):
                lvl[f"ch244/mixed_members/{st}/{bk}/{cat}"] += 1
                lvl[f"ch244/mixed_members_total/{st}/{cat}"] += 1
                if rows[m][3]:
                    lvl[f"ch244/mixed_members_two_sided/{st}/{cat}"] += 1
            pts = [(1.0 if st == "unrewarded" else 0.0, math.log1p(max(rows[m][6], 0.0))) for m, st in zip(mids, sts, strict=True) if st != "unknown" and math.isfinite(rows[m][6])]
            if len(pts) >= 2:
                grp = "3-10" if n <= 10 else "11+"
                mu, ml = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
                cw, cp = self._corr(f"ch244/status_liquidity_corr_within_event/{grp}/{cat}"), self._corr(f"ch244/status_liquidity_corr_pooled/{grp}/{cat}")
                for u, lq in pts:
                    cw.add(u - mu, lq - ml)
                    cp.add(u, lq)
        if not complete:
            return
        mp = {m: (rows[m][1] + rows[m][2]) / 2.0 for m in mids}
        new_ladders[ev] = mp
        pv = self.prev_ladders.get(ev) if has_prev else None
        if pv is None or pv.keys() != mp.keys():
            return
        tick_e = max(exts[i][2] for i in range(n))
        dabs = {m: abs(mp[m] - pv[m]) for m in mids}
        order = sorted(mids, key=lambda m: dabs[m], reverse=True)
        top, second = dabs[order[0]], dabs[order[1]]
        chg[f"ch244/complete_pairs/{cls}/{bk}/{cat}"] += 1
        if top >= SHOCK_TICKS * tick_e - EPS:
            chg[f"ch244/event_captures_with_a_ge2tick_mover/{cls}/{bk}/{cat}"] += 1
        for m, st in zip(mids, sts, strict=True):
            sib = second if m == order[0] else top
            chg[f"ch244/units/{cls}/{st}/{cat}"] += 1
            if sib >= SHOCK_TICKS * tick_e - EPS:
                chg[f"ch244/shock_units/{cls}/{st}/{cat}"] += 1

    def finish(self, covered_days_per_capture: float = GRID_S / 86400.0) -> dict:
        out: dict = {"level_counts": {}, "change_counts": {}}
        for name, caps, per in (("level_counts", self.cap_lvl, self.n_captures), ("change_counts", self.cap_chg, self.n_changes)):
            days = per * covered_days_per_capture
            for k in sorted({k for c in caps for k in c}):
                st = c240._stats([float(c.get(k, 0)) for c in caps])
                st["projected_21d"] = st["total"] * 21.0 / days if days > 0 else None
                out[name][k] = st
        out["distinct_events_over_span"] = {k: len(v) for k, v in sorted(self.events.items())}
        out["quantiles"] = {k: c240._quantiles(a) for k, a in sorted(self.arrays.items())}
        out["correlations"] = {k: {"n": c.n, "corr": c.corr()} for k, c in sorted(self.corr.items())}
        lv, ch = out["level_counts"], out["change_counts"]

        def ratio(sec: dict, num: str, den: str, tag: str) -> dict:
            r: dict = {}
            for k, v in sec.items():
                if k.startswith(num + "/"):
                    d = sec.get(den + k[len(num):])
                    r[tag + k[len(num):]] = v["total"] / d["total"] if d and d["total"] else None
            return r

        sh: dict = {}
        sh.update(ratio(lv, "ch245/two_member_complete_at_k", "ch245/two_member_events", "ch245/complete_share_at_k"))
        sh.update(ratio(ch, "ch245/pairs_span_retained", "ch245/complete_pairs_k_km1", "ch245/span_retention_share"))
        for u in ("thin", "sym", "dense"):
            sh.update(ratio(ch, f"ch245/{u}_units", "ch245/units_total", f"ch245/{u}_share"))
        sh.update(ratio(lv, "ch244/ladders_complete", "ch244/ladders", "ch244/ladder_complete_share"))
        sh.update(ratio(lv, "ch244/mixed_members_two_sided", "ch244/mixed_members_total", "ch244/mixed_member_two_sided_share"))
        sh.update(ratio(ch, "ch244/shock_units", "ch244/units", "ch244/shock_share"))
        sh.update(ratio(ch, "ch243/fee_free_movers_in_covered_cell_proxy", "ch243/fee_free_movers_classed", "ch243/fee_free_cell_coverage_proxy"))
        rows_tot = {c: sum(v["total"] for k, v in lv.items() if k.startswith("ch250/rows_open_binary/") and k.endswith("/" + c)) for c in CATS}
        cells: dict = {}
        for c in CATS:
            for k, v in lv.items():
                if k.startswith("ch250/rows_open_binary/") and k.endswith("/" + c) and rows_tot[c]:
                    cells[f"ch250/row_share/{k.split('/', 2)[2]}"] = v["total"] / rows_tot[c]
            ff = sum(v["total"] for k, v in lv.items() if k.startswith("ch250/rows_open_binary/fee_free/") and k.endswith("/" + c))
            cells[f"ch250/fee_free_row_share_both_rw/{c}"] = ff / rows_tot[c] if rows_tot[c] else None
        out["shares"] = dict(sorted({**sh, **cells}.items()))
        out["notes"] = dict(self.notes)
        return out


# --- capture discovery and the run ----------------------------------------------------------------------------------------------------


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
        rows = read_rows(d / "rows.csv.gz")
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
        "version": VERSION, "kind": "CH251 LT12 population map: counts only, k = 0, uncounted; captures k and k - 1 only; nothing from capture k + 1 or later; no target, no P&L",
        "span": {"start_utc": start_utc, "end_utc": end_utc, "expected_2h_slots": int((t1 - t0) // GRID_S),
                 "note": "orchestrator decision: ten UTC days already on the host, disjoint from LT11's census seal [10-28, 11-07) and LT11's window (11-18..12-09); overlaps the CH240 map's span (also counts-only), disclosed"},
        "captures": {"covered": len(caps), "covered_ids": [c["id"] for c in caps], "with_previous_capture_k_minus_1": mp.n_changes,
                     "missing_expected": max(0, int((t1 - t0) // GRID_S) - len(caps)), "gaps_over_2h30": gaps, "covered_days": len(caps) * GRID_S / 86400.0},
        "reward_reading": "MAP reading, not listed_carry24h_v2: rewarded = clob_rewards of capture k non-empty; unrewarded = sidecar row with an empty field; unknown = no sidecar row or column",
        "category_reading": "as the CH240 map: sports by cb17_census.is_sports_sidecar; crypto by live_tests8_base.crypto_class; unknown without a sidecar row",
        "conventions": {
            "population": "open active binary rows; two-sided = 0 < best_bid < best_ask <= 1; mid = (bid + ask) / 2; neg-risk events = rows with neg_risk true grouped by event_id; event category sports > crypto > unknown > nonsports_excrypto",
            "pairs": "two-member event = exactly two such rows; complete = both two-sided at k and at k - 1 with the same two market ids; retained = |received_utc_A - received_utc_B| <= 120 s at k AND at k - 1 (unparseable counts as excluded)",
            "pair_class": "rr both rewarded, uu both unrewarded, ru one each, unk any unknown", "ladders": "3+ member neg-risk events; mixed = >= 1 rewarded and >= 1 unrewarded member; units use complete (k - 1, k) ladders",
            "shock": "shock_i = max over siblings j != i of |mid_j,k - mid_j,k-1| >= 2 x tick_e - eps, tick_e = largest member order_price_min_tick_size",
            "movers": "|d| >= 0.01 and p_{k-1} in [0.04, 0.96] (CH243 / CH250); CH248 movers have |d| >= 0.01 only; traded = volume_num_k > volume_num_{k-1}; quote_only = equal; unusable = a missing or falling sidecar volume_num",
            "fee": "fee_free = fees_enabled false (flag_off) or fee_schedule.rate = 0 (rate_zero); fee_on = rate > 0; unknown = no sidecar or no schedule; age = created_at before 2026-03-30",
            "printed": "own_printed / twin_printed / both / neither / unknown from sidecar volume_num at k and k - 1 of both books", "projection": "total x 21 / covered days",
            "innovation_corr": "Pearson over ordered pairs (A, B) and (B, A) of the spread change (k - 1 to k) of each book; state only, no k + 1"},
        "not_mapped": NOT_MAPPED,
        "peak_rss_mb": round(rss / (2**20 if sys.platform == "darwin" else 1024), 1),
        "inputs": inputs, "code_sha256": code_sha256(), **res,
    }
