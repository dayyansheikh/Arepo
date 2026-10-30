# ruff: noqa: E501
"""CH276, the surviving-side census (docs/research_lab/CREATIVE_HYPOTHESES_2026-11-03.md section 2 E). COUNTS ONLY, k = 0, uncounted.

One read-only reader over the stores the host already keeps: the 2-hourly sidecars (``snapshots/<capture>/rows.csv.gz``, ``rows_ext.csv.gz``), the signal engine's
``quotes/``, ``features/`` and ``predictions/`` files, the keyless ``stream_gamma_rules`` day files, and the live trade monitor's ``live_trades/trades-YYYYMMDD.jsonl``
and ``stats.jsonl`` (cycle lines). It prints the nine count lines of section E and the declared decision readings. It creates no table, token, column or label.

Hard limits (enforced here, tested in tests/test_ch276_map.py):

* never opens the engine's ``logs/`` (resolution store), the monitor's alerts / scores / outcomes / wallets files, or any column named like a resolution, outcome,
  payoff, label or wallet (``guard_columns`` / ``guard_path``);
* the only price read after a unit's decision capture k is what section E names: (4) the bid / ask of capture k + 1 of a ONE-SIDED eligible row, compared with
  ``mid_k +- 0.005`` as a sign class and discarded; (5) monitor prints inside (t_k, t_exit], counted (their cash notional only against the $1,000 floor, never price or
  size); (7) the presence of a proposal flag at later captures, as a count;
* no fitted model, no p-value, no edge or profit language: ``check_output`` refuses an output with such a key.

Reused read-only: ``m1_j0.J0Pass`` (the M1 unit: E1-E7 eligibility, the favoured side, the event key), ``m1_j0`` and ``boundary_map_ch240`` helpers,
``census_map_ch269`` readers (quotes frame, capture listing, the placeholder rules lexicon). Nothing is edited. Missing captures are listed and never reconstructed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import resource
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from . import boundary_map_ch240 as c240
from . import census_map_ch269 as c269
from . import m1_j0 as j0

VERSION = "ch276-map-v1"
GRID0 = c269.GRID0
GRID_S = 7200.0
SCOPE = "nonsports_excrypto"
FMT = "%Y-%m-%dT%H:%M:%SZ"
DAY_S = 86400.0
DELTA = 0.005  # the engine's frozen direction constant, restated (CH271 (b) text)
SIGN_EPS = 1e-9  # float slack for the ">= mid + 0.005" comparison
INSURED_MIN, UNINSURED_MAX = 0.010, 0.002  # CH275 classes on ins_k = 1 - bid_k (strictly above / at most)
CERTAIN = 0.95  # CH274 population edge
AGE_MIN_SLOTS = 12
PRINT_FLOOR = 1000.0  # CH272: monitor prints of $1,000 or more
MONITOR_GAP_S = 900.0  # a gap between consecutive monitor cycle lines above 3 nominal 5-minute cycles
OX_SLOTS = 84
FULL_DAY_CAPTURES = 12  # captures for a "full" UTC day (as M1-J0)
PERIODS_DEFAULT = (("2026-10-13", "2026-10-19"), ("2026-10-21", "2026-10-29"))
CHAMPION = "se0_champion_lr_mm"
HTE_BINS = ("lt3d", "3-14d", "14-60d", "ge60d", "missing")
MID_BINS = c240.BINS
EXCL_ENGINE_CATS = ("sports", "crypto", "unknown")

LINES = {
    "ch270_built_if_share_of_eligible_rows_in_negrisk_events_with_co_n_ge_3_at_least": 0.10,
    "ch270_built_if_median_event_within_sd_of_s_2h_at_least": 0.02,
    "ch271_b_if_share_of_eligible_rows_with_sign_determinable_one_sided_k1_at_least": 0.01,
    "ch271_c_if_share_of_eligible_rows_with_ox_1s_84_gt_0_at_least": 0.02,
    "ch272_amendment_if_proposal_units_a_day_with_a_print_at_least": 5,
    "ch273_drafted_if_two_sided_b_units_a_day_at_least": 25,
    "ch274_if_crossings_a_day_at_least": 30,
    "ch275_census_if_insured_units_scaled_to_21_days_at_least": 100,
    "ch275_census_if_disputes_share_of_proposal_events_at_least": 0.01,
    "semantics_per_market_if_sibling_carry_share_below": 0.10,
    "semantics_event_level_if_sibling_carry_share_above": 0.90,
}

NOT_MAPPED = {
    "event_neg_risk_augmented": "not a column of the sidecar files read here; the augmented 'Other' member is not separated (CH273 counted class not available)",
    "sweep_1_coverage": "the book sweeps are not opened (CH273 (6) and CH274 (6) capacity coverage is M1-J0's 0.73% and is not re-measured)",
    "engine_rules_table": "the engine's `rules` aux table is not opened; the class is the PLACEHOLDER lexicon of census_map_ch269 over the keyless stream_gamma_rules day files (CH239's parser is not in the repository)",
    "rule_26_payoffs": "no payoff, resolution or label is read; r_B, r_eff, the dispute outcome and W's absent-vs-settled cross-check are the later measurements' business",
    "mde_f_mde": "no MDE or F-MDE is computed (no variance of a target is read)",
    "within_vs_between_stratum_sd": "CH275's rule-24 identification gate needs a dispute target and is not computed; only the class counts are printed",
}

FORBIDDEN_EXACT = frozenset({"y", "closed_time", "closed_ts", "fetched_ts", "fetched_utc", "final_price", "payout", "state_resolved", "res_7d", "dir_2h_y"})
FORBIDDEN_SUBSTR = ("payoff", "pnl", "profit", "winner", "wallet", "proxy", "label", "outcome_price", "resolution_value", "resolved_value")
FORBIDDEN_PATH_PARTS = ("resolutions-", "outcomes", "wallets", "alerts", "scores", "labels", "holdout")
BANNED_OUTPUT_KEY_RE = re.compile(r"(p_value|pvalue|\bedge\b|alpha|sharpe|profit|pnl|t_stat|z_score)", re.I)
MONITOR_KEYS = ("ts", "recv_ts", "condition_id", "side", "outcome_index", "cash")
ROW_COLS = ("market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date", "condition_id", "neg_risk_market_id")
EXT_COLS = ("market_id", "received_utc", "uma_resolution_statuses", "accepting_orders", "fee_type", "fee_category", "series_slugs", "created_at")
FEATURE_COLS = ("market_id", "event_id", "category", "ms_neg_risk", "ms_log_liq", "ms_hours_to_end", "end_ts")


class Refusal(RuntimeError):
    """A read that section E forbids (a forbidden column or path)."""


def guard_columns(cols) -> tuple:
    for c in cols:
        lc = str(c).lower()
        if lc in FORBIDDEN_EXACT or any(s in lc for s in FORBIDDEN_SUBSTR):
            raise Refusal(f"CH276 never reads the field {c!r} (resolution / outcome / payoff / label / wallet)")
    return tuple(cols)


def guard_path(p: Path) -> Path:
    name = Path(p).name.lower()
    parts = [x.lower() for x in Path(p).parts]
    if any(f in name for f in FORBIDDEN_PATH_PARTS) or "logs" in parts:
        raise Refusal(f"CH276 never opens {p} (resolution store, label, outcome, wallet, alert or score file)")
    return Path(p)


def check_output(res: dict) -> None:
    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if BANNED_OUTPUT_KEY_RE.search(str(k)):
                    raise Refusal(f"output key {path}/{k} reads as a test statistic or an edge claim")
                walk(v, f"{path}/{k}")
        elif isinstance(o, list):
            for v in o[:50]:
                walk(v, path)

    walk(res)


def code_sha256() -> dict:
    root = Path(__file__).resolve().parents[2]
    fs = (Path(__file__), root / "scripts" / "run_ch276_map.py", Path(j0.__file__), Path(c269.__file__), Path(c240.__file__))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fs if p.exists()}


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(r / (2**20 if sys.platform == "darwin" else 1024.0), 1)


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime(FMT)


def quant(vals, p: float) -> float | None:
    v = sorted(float(x) for x in vals if x == x)
    return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))] if v else None


def median(vals) -> float | None:
    v = sorted(float(x) for x in vals if x == x)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def safe_div(a, b):
    return None if not b else a / b


def hte_bin(h_hours: float) -> str:
    if not math.isfinite(h_hours):
        return "missing"
    d = h_hours / 24.0
    return "lt3d" if d < 3 else "3-14d" if d < 14 else "14-60d" if d < 60 else "ge60d"


def list_len(s) -> int:
    t = str(s if s is not None else "").strip()
    if t.lower() in j0.EMPTY:
        return 0
    try:
        v = json.loads(t)
        if isinstance(v, list):
            return len(v)
    except ValueError:
        pass
    try:
        v = ast.literal_eval(t)
        if isinstance(v, (list, tuple)):
            return len(v)
    except (ValueError, SyntaxError):
        pass
    return len([x for x in t.strip("[]").split(",") if x.strip()])


def book_state(bid: float, ask: float) -> str:
    """two_sided / bid_only / ask_only / crossed_or_locked / no_quote (the sidecar prices, not the engine's quotes/)."""
    hb = bid == bid and bid > 0
    ha = ask == ask and 0 < ask <= 1
    if hb and ha:
        return "two_sided" if bid < ask else "crossed_or_locked"
    if hb:
        return "bid_only"
    if ha:
        return "ask_only"
    return "no_quote"


def ins_class(ins: float) -> str:
    v = j0.r6(ins)
    return "uninsured" if v <= UNINSURED_MAX else "insured" if v > INSURED_MIN else "middle"


def full_day_median(per_day: dict, full_days: list[str]) -> float | None:
    return median([per_day.get(d, 0) for d in full_days])


# --------------------------------------------------------------------------------------------------------------- discovery


def discover_all(roots: list[Path], start_ts: float, end_ts: float) -> tuple[list[dict], Counter]:
    by_slot: dict = {}
    notes: Counter = Counter()
    for r in roots:
        caps, n = j0.discover_captures(Path(r), start_ts, end_ts)
        notes.update(n)
        for c in caps:
            cur = by_slot.get(c["slot"])
            if cur is None or c["start"] < cur["start"]:
                by_slot[c["slot"]] = c
    return [by_slot[k] for k in sorted(by_slot)], notes


def last_days_span(roots: list[Path], days: int) -> tuple[float, float]:
    caps, _ = discover_all(roots, c240.parse_utc("2000-01-01T00:00:00Z"), c240.parse_utc("2100-01-01T00:00:00Z"))
    if not caps:
        raise SystemExit("no complete captures found for --last-days")
    end = datetime.fromtimestamp(caps[-1]["start"], UTC).replace(minute=0, second=0, microsecond=0).timestamp() + 7200.0
    end -= (datetime.fromtimestamp(end, UTC).hour % 2) * 3600.0
    return end - days * DAY_S, end


# --------------------------------------------------------------------------------------------------------------- the sidecar pass (lines 1, 2, 5 units, 6, 7, 8)


class SidecarPass:
    def __init__(self, start_ts: float, end_ts: float, rules: dict, n_warm: int) -> None:
        self.start_ts, self.end_ts = start_ts, end_ts
        self.rules = rules.get("classes", {})
        self.j0 = j0.J0Pass(n_warm)
        self.idx = 0
        self.prev_slot: int | None = None
        self.prev_state: dict = {}  # mid -> (bid, ask, code)
        self.notes: Counter = Counter()
        self.counted: list[dict] = []
        # line 1
        self.sem: Counter = Counter()
        self.sem_len_hist: Counter = Counter()
        self.sem_len_vs_size: Counter = Counter()
        self.sem_len_vs_w: Counter = Counter()
        self.sem_sib: Counter = Counter()
        self.sem_sib_scope: Counter = Counter()
        # line 2
        self.one_sided: Counter = Counter()
        self.first_seen_events: set = set()
        self.first_seen_rows = 0
        self.funnel_not_two_sided = 0
        # units (lines 5, 6, 8)
        self.units: list[dict] = []
        self.pending_exit: list[dict] = []
        # line 6
        self.seen_b: set = set()
        self.b_units: list[dict] = []
        self.b_classes: Counter = Counter()
        self.winner_no_group = 0
        # line 7
        self.first_obs: dict = {}
        self.ever_certain: set = set()
        self.cross_units: list[dict] = []
        self.cross_pending: dict = {}
        self.cross_classes: Counter = Counter()
        self.near_cert: Counter = Counter()
        # line 8
        self.disp_runs: dict = {}
        self.disp_active: set = set()
        self.disp_reappear = 0
        self.ever_prop_state: set = set()

    # ------------------------------------------------------------------------------- readers
    def _read_ext(self, path: Path) -> dict:
        ext: dict = {}
        if not path.exists():
            self.notes["captures_without_sidecar"] += 1
            return ext
        it = j0.iter_csv(guard_path(path), guard_columns(EXT_COLS))
        pres = next(it, None)
        if pres is None:
            return ext
        for c, ok in zip(EXT_COLS, pres, strict=True):
            if not ok:
                self.notes[f"sidecar_column_missing:{c}"] += 1
        for mid_s, rec, uma, acc, ft, fc, ss, created in it:
            try:
                mid = int(mid_s)
            except ValueError:
                continue
            code, _both = j0.status_code(uma)
            ustr = str(uma).strip().lower()
            ext[mid] = (code, "propos" in ustr, list_len(uma), c240.category_of(ft, fc, ss, True), c240.parse_utc(rec), c240.parse_utc(created), j0.false_flag(acc), ustr if code else "")
        return ext

    def _read_rows(self, path: Path) -> dict:
        cur: dict = {}
        it = j0.iter_csv(guard_path(path), guard_columns(ROW_COLS))
        pres = next(it, None)
        if pres is None:
            return cur
        for c, ok in zip(ROW_COLS, pres, strict=True):
            if not ok:
                self.notes[f"rows_column_missing:{c}"] += 1
        for mid_s, ev, rec, closed, active, binary, bid, ask, liq, end, cond, grp in it:
            if not (c240._truthy(binary) and not c240._truthy(closed) and c240._truthy(active)):
                continue
            try:
                mid = int(mid_s)
            except ValueError:
                continue
            g = str(grp).strip()
            cur[mid] = (j0.r6(c240._f(bid)), j0.r6(c240._f(ask)), ev if str(ev).strip() else f"market:{mid}", "" if g.lower() in j0.EMPTY else g, str(cond), c240._f(liq), c240.parse_utc(end), c240.parse_utc(rec))
        return cur

    # ------------------------------------------------------------------------------- the feed
    def feed(self, cap: dict, counted: bool) -> None:
        d = Path(cap["dir"])
        start, slot, day = cap["start"], cap["slot"], c240.day_of(cap["start"])
        ext = self._read_ext(d / "rows_ext.csv.gz")
        cur = self._read_rows(d / "rows.csv.gz")
        has_prev = self.prev_slot is not None and slot == self.prev_slot + 1
        n_units0 = len(self.j0.units)
        groups: dict = defaultdict(list)
        for mid, r in cur.items():
            if r[3]:
                groups[r[3]].append(mid)
        if counted:
            self.counted.append({"id": cap["id"], "start": start, "day": day, "with_prev": has_prev})
            self._semantics(ext, cur, groups, has_prev)
            self._funnel_one_sided(cap, ext, cur)
        # exits of units fixed at earlier captures: absent from the open listing at this capture
        still = []
        for u in self.pending_exit:
            if u["mid"] in cur:
                still.append(u)
            else:
                u["t_exit"] = start
        self.pending_exit = still
        self._disputes(ext, slot, counted, start)
        self._crossings(ext, cur, has_prev, counted, start, day)
        self._proposal_flags_for_crossings(ext, start)
        # the M1 unit (reused extractor); its state before this call is capture k - 1's
        self.j0.feed(cap, None)
        if counted:
            for u in self.j0.units[n_units0:]:
                self._new_unit(u, cur, ext, groups, has_prev, start)
        self.prev_state = {m: (r[0], r[1], ext[m][0] if m in ext else 0) for m, r in cur.items()}
        self.prev_slot = slot
        self.idx += 1

    # ------------------------------------------------------------------------------- line 1
    def _semantics(self, ext: dict, cur: dict, groups: dict, has_prev: bool) -> None:
        for mid in cur:
            e = ext.get(mid)
            if e and e[0]:
                self.sem_len_hist["1" if e[2] == 1 else "2" if e[2] == 2 else "3-5" if e[2] <= 5 else "6-10" if e[2] <= 10 else "11+"] += 1
        for mids in groups.values():
            s = len(mids)
            if s < 2:
                self.sem["groups_of_size_1"] += 1
                continue
            self.sem["group_captures_size_ge2"] += 1
            w = sum(1 for m in mids if m in ext and ext[m][0])
            if w:
                self.sem["group_captures_with_any_status"] += 1
                self.sem["all_members_have_status" if w == s else "some_members_have_status"] += 1
                strs = {ext[m][7] for m in mids if m in ext and ext[m][0]}
                if w >= 2:
                    self.sem["groups_with_2plus_statused_members"] += 1
                    if len(strs) == 1:
                        self.sem["groups_all_statused_members_identical_string"] += 1
            for m in mids:
                e = ext.get(m)
                if not e or not e[0]:
                    continue
                n = e[2]
                self.sem_len_vs_size["len_eq_group_size" if n == s else "len_lt_group_size" if n < s else "len_gt_group_size"] += 1
                self.sem_len_vs_w["len_eq_members_with_status" if n == w else "len_lt_members_with_status" if n < w else "len_gt_members_with_status"] += 1
        if not has_prev:
            return
        for mid, r in cur.items():
            e = ext.get(mid)
            if not e or e[0] != 1 or not e[1] or not r[3]:
                continue
            p = self.prev_state.get(mid)
            if p is None or p[2] != 0:
                continue
            members = [m for m in groups.get(r[3], []) if m != mid]
            if not members:
                continue
            scope = e[3] == SCOPE
            self.sem_sib["proposed_markets_first_seen_in_groups_ge2"] += 1
            for m in members:
                eb = ext.get(m)
                kind = "unflagged_empty_status" if (not eb or not eb[0]) else "carries_a_proposal" if eb[1] else "other_status"
                self.sem_sib["siblings_total"] += 1
                self.sem_sib[kind] += 1
                if eb and eb[0] and eb[7] == e[7]:
                    self.sem_sib["sibling_status_string_identical_to_proposed"] += 1
                if scope:
                    self.sem_sib_scope["siblings_total"] += 1
                    self.sem_sib_scope[kind] += 1

    # ------------------------------------------------------------------------------- line 2 (M1's funnel order up to the two-sided test, re-derived and cross-checked)
    def _funnel_one_sided(self, cap: dict, ext: dict, cur: dict) -> None:
        jp = self.j0.prev
        jhas_prev = jp is not None and cap["slot"] == jp["slot"] + 1
        for mid in sorted(m for m, e in ext.items() if e[1] and e[0] in (1, 2)):
            e = ext[mid]
            cls = None
            if not jhas_prev:
                cls = "no_previous_capture"
            elif e[0] == 2:
                cls = "disputed_at_k"
            elif mid not in jp["row_ids"] or mid not in jp["codes"]:
                cls = "no_k_minus_1_row"
            elif jp["codes"][mid] in (1, 2, 3):
                cls = "already_proposed"
            elif mid in self.j0.unit_markets or mid in self.j0.hist_last:
                cls = "prior_proposal_state"
            r = cur.get(mid)
            if cls is None and (r is None or e[6]):
                cls = "not_open_at_k"
            if cls is None and e[3] != SCOPE:
                cls = "out_of_scope"
            if cls is not None:
                continue
            self.first_seen_rows += 1
            self.first_seen_events.add(r[2])
            bid, ask = r[0], r[1]
            st = book_state(bid, ask)
            if st == "two_sided":
                continue
            self.funnel_not_two_sided += 1
            p = bid if st == "bid_only" else ask if st == "ask_only" else math.nan
            fav = "undetermined" if not (p == p) else "yes" if p >= j0.FAV else "no" if p <= 1 - j0.FAV else "mid_zone"
            self.one_sided[(st, fav, j0.TIER_NAMES[j0.tier_of(r[5])])] += 1

    # ------------------------------------------------------------------------------- disputes (line 8, sidecar state only)
    def _disputes(self, ext: dict, slot: int, counted: bool, start: float) -> None:
        now = {m for m, e in ext.items() if e[0] == 2 and "disput" in e[7]}
        for m in list(self.disp_active):
            if m not in now:
                self.disp_active.discard(m)
                self.disp_runs[m]["ended"] = True
        for m in now:
            run = self.disp_runs.get(m)
            if run is None:
                self.disp_runs[m] = {"first_slot": slot, "last_slot": slot, "len": 1, "ended": False, "counted": counted, "day": c240.day_of(start), "cat": ext[m][3],
                                     "after_proposal": m in self.ever_prop_state, "pre_existing": self.idx == 0}
                self.disp_active.add(m)
            elif m in self.disp_active and run["last_slot"] == slot - 1:
                run["last_slot"] = slot
                run["len"] += 1
            else:
                self.disp_reappear += 1
                self.disp_active.discard(m)
                run["ended"] = True
        for m, e in ext.items():
            if e[1]:
                self.ever_prop_state.add(m)

    # ------------------------------------------------------------------------------- line 7 (CH274's crossing, counts only)
    def _crossings(self, ext: dict, cur: dict, has_prev: bool, counted: bool, start: float, day: str) -> None:
        for mid, r in cur.items():
            e = ext.get(mid)
            if not e or e[3] != SCOPE:
                continue
            bid, ask = r[0], r[1]
            if book_state(bid, ask) != "two_sided":
                continue
            yes_c, no_c = j0.r6(ask) >= CERTAIN, j0.r6(1.0 - bid) >= CERTAIN
            cert = yes_c or no_c
            created = e[5]
            age_slots = (start - created) / GRID_S if math.isfinite(created) else math.nan
            if mid not in self.first_obs:
                self.first_obs[mid] = self.idx
                if cert:
                    self.ever_certain.add(mid)
                    if self.idx == 0 or not counted:
                        self.near_cert["pre_window_certain_by_window_start"] += 1
                    elif math.isfinite(age_slots) and age_slots < AGE_MIN_SLOTS:
                        self.near_cert["born_certain"] += 1
                    else:
                        self.near_cert["first_sight_certain_old_market"] += 1
                continue
            if not cert or mid in self.ever_certain:
                continue
            self.ever_certain.add(mid)
            if not counted:
                self.near_cert["pre_window_certain_by_window_start"] += 1
                continue
            p = self.prev_state.get(mid) if has_prev else None
            if p is None or book_state(p[0], p[1]) != "two_sided":
                self.cross_classes["no_two_sided_k_minus_1"] += 1
                continue
            prev_fav_ask = j0.r6(p[1]) if yes_c else j0.r6(1.0 - p[0])
            if prev_fav_ask >= CERTAIN:
                self.cross_classes["favoured_ask_already_certain_at_k_minus_1"] += 1
                continue
            if e[0]:
                self.cross_classes["proposal_state_at_k"] += 1
                continue
            end_ts = r[6]
            if not math.isfinite(end_ts):
                self.cross_classes["end_date_missing"] += 1
                continue
            if end_ts <= start + DAY_S:
                self.cross_classes["end_within_24h"] += 1
                continue
            if not (math.isfinite(age_slots) and age_slots >= AGE_MIN_SLOTS):
                self.cross_classes["market_younger_than_12_slots_or_age_unknown"] += 1
                continue
            u = {"mid": mid, "day": day, "cls": self.rules.get(mid, "no_rules"), "tier": j0.TIER_NAMES[j0.tier_of(r[5])], "hte": hte_bin((end_ts - start) / 3600.0), "end_ts": end_ts,
                 "start": start, "first_prop": None}
            self.cross_classes["unit"] += 1
            self.cross_units.append(u)
            self.cross_pending[mid] = u

    def _proposal_flags_for_crossings(self, ext: dict, start: float) -> None:
        for mid in list(self.cross_pending):
            u = self.cross_pending[mid]
            if start <= u["start"]:
                continue
            e = ext.get(mid)
            if e and e[1]:
                u["first_prop"] = start
                del self.cross_pending[mid]

    # ------------------------------------------------------------------------------- units (lines 5, 6, 8)
    def _new_unit(self, u: dict, cur: dict, ext: dict, groups: dict, has_prev: bool, start: float) -> None:
        mid = u["mid"]
        r = cur[mid]
        bid, ask = r[0], r[1]
        ins = j0.r6(1.0 - bid) if u["side"] == "YES" else j0.r6(ask)
        t_k = max((x for x in (u["row_rec"], u["ext_rec"]) if math.isfinite(x)), default=start)
        rec = {"mid": mid, "day": u["day"], "side": u["side"], "ins": ins, "ins_class": ins_class(ins), "zone": j0.zone_of(ins), "tier": u["tier"], "t_k": t_k, "cond": r[4], "t_exit": None,
               "event": u["event"], "start": start}
        self.units.append(rec)
        self.pending_exit.append(rec)
        if u["side"] != "YES":
            return
        grp = r[3]
        if not grp:
            self.winner_no_group += 1
            return
        members = [m for m in groups.get(grp, []) if m != mid]
        size = len(groups.get(grp, []))
        for b in members:
            if b in self.seen_b:
                continue
            eb = ext.get(b)
            rb = cur[b]
            if not eb or eb[3] != SCOPE:
                self.b_classes["out_of_scope_category"] += 1
                continue
            self.seen_b.add(b)
            if eb[0]:
                self.b_classes["own_status_at_k"] += 1
                continue
            pb = self.prev_state.get(b) if has_prev else None
            if pb is not None and pb[2] in (1, 2):
                self.b_classes["own_proposal_at_k_minus_1"] += 1
                continue
            st = book_state(rb[0], rb[1])
            moved = None
            if st == "two_sided" and pb is not None and book_state(pb[0], pb[1]) == "two_sided":
                moved = j0.r6(rb[0]) != j0.r6(pb[0])
            mid_b = (rb[0] + rb[1]) / 2.0 if st == "two_sided" else math.nan
            eng_elig = bool(st == "two_sided" and 0.02 <= mid_b <= 0.98)
            self.b_units.append({"day": u["day"], "size": c240.size_bucket(size) or "1", "state": st, "moved": moved, "elig": eng_elig})
            self.b_classes["b_unit"] += 1


# --------------------------------------------------------------------------------------------------------------- the monitor (line 5)


def read_monitor(root: Path | None, lo: float, hi: float) -> dict:
    out = {"prints": defaultdict(list), "cycles": [], "forms": Counter(), "files": [], "missing_days": [], "available": False}
    if root is None or not Path(root).is_dir():
        return out
    out["available"] = True
    keys = guard_columns(MONITOR_KEYS)
    d0, d1 = datetime.fromtimestamp(lo - 2 * DAY_S, UTC).date(), datetime.fromtimestamp(hi + DAY_S, UTC).date()
    day = d0
    while day <= d1:
        p = guard_path(Path(root) / f"trades-{day:%Y%m%d}.jsonl")
        if not p.exists():
            out["missing_days"].append(f"{day:%Y%m%d}")
        else:
            out["files"].append(p.name)
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                        vals = {k: d.get(k) for k in keys}
                        ts, cond, side, oi, cash = float(vals["ts"]), str(vals["condition_id"]), str(vals["side"]).upper(), int(vals["outcome_index"]), float(vals["cash"])
                    except (ValueError, TypeError, KeyError, AttributeError):
                        continue
                    if cash < PRINT_FLOOR:
                        continue
                    out["forms"][f"{side}|outcome_index={oi}"] += 1
                    out["prints"][cond].append((ts, side, oi))
        day = day.fromordinal(day.toordinal() + 1)
    sp = guard_path(Path(root) / "stats.jsonl")
    if sp.exists():
        with open(sp, encoding="utf-8") as fh:
            for line in fh:
                try:
                    t = c240.parse_utc(json.loads(line).get("cycle_start_utc"))
                except (ValueError, AttributeError):
                    continue
                if math.isfinite(t):
                    out["cycles"].append(t)
        out["cycles"].sort()
        out["files"].append("stats.jsonl")
    return out


def fill_flow(side: str, fav: str, oi: int) -> bool:
    """A taker SELL of the favoured outcome, or a taker BUY of the other outcome (matched against the favoured side's bids). Outcome 0 = the YES token."""
    fav_oi = 0 if fav == "YES" else 1
    return (side == "SELL" and oi == fav_oi) or (side == "BUY" and oi == 1 - fav_oi)


def monitor_line(units: list[dict], mon: dict, last_cap_start: float, full_days: list[str]) -> dict:
    if not mon["available"]:
        return {"available": False, "note": "no --monitor-root given or it is missing: line (5) is unavailable, not a pass"}
    cyc = mon["cycles"]
    gaps = [(a, b) for a, b in zip(cyc, cyc[1:], strict=False) if b - a > MONITOR_GAP_S]
    first, last = (cyc[0], cyc[-1]) if cyc else (math.nan, math.nan)
    rows = []
    for u in units:
        t0 = u["t_k"]
        t1 = u["t_exit"] if u["t_exit"] is not None else last_cap_start
        covered = bool(cyc) and t0 >= first and t1 <= last
        pre_cov = bool(cyc) and (t0 - DAY_S) >= first and t0 <= last
        prs = mon["prints"].get(u["cond"], [])
        post = [p for p in prs if t0 < p[0] <= t1]
        pre = [p for p in prs if t0 - DAY_S <= p[0] < t0]
        in_gap = any(a < t1 and b > t0 for a, b in gaps)
        rows.append({"u": u, "covered": covered, "pre_cov": pre_cov, "n_post": len(post), "n_post_fill": sum(1 for p in post if fill_flow(p[1], u["side"], p[2])),
                     "n_pre": len(pre), "n_pre_fill": sum(1 for p in pre if fill_flow(p[1], u["side"], p[2])), "in_gap": in_gap, "exited": u["t_exit"] is not None})
    cov = [r for r in rows if r["covered"]]
    cov_ex = [r for r in cov if r["exited"]]
    by_day_any, by_day_fill, by_day_prints = Counter(), Counter(), Counter()
    for r in cov:
        if r["n_post"]:
            by_day_any[r["u"]["day"]] += 1
        if r["n_post_fill"]:
            by_day_fill[r["u"]["day"]] += 1
        by_day_prints[r["u"]["day"]] += r["n_post"]
    units_day = Counter(r["u"]["day"] for r in cov)
    pre_cov = [r for r in rows if r["pre_cov"]]
    split = Counter()
    for r in cov:
        if r["pre_cov"]:
            split[("pre>=1" if r["n_pre"] else "pre=0", "post>=1" if r["n_post"] else "post=0")] += 1
    return {
        "available": True,
        "units_total": len(units), "units_exited_observed": sum(1 for u in units if u["t_exit"] is not None), "units_censored_no_exit_in_span": sum(1 for u in units if u["t_exit"] is None),
        "units_with_monitor_coverage_of_window": len(cov), "units_without_coverage": len(rows) - len(cov),
        "units_a_day_covered": dict(sorted(units_day.items())),
        "units_with_any_print_in_window_a_day": dict(sorted(by_day_any.items())),
        "units_with_fill_flow_print_in_window_a_day": dict(sorted(by_day_fill.items())),
        "prints_in_unit_windows_a_day": dict(sorted(by_day_prints.items())),
        "median_units_with_any_print_per_full_day": full_day_median(by_day_any, full_days),
        "median_units_with_fill_flow_print_per_full_day": full_day_median(by_day_fill, full_days),
        "units_with_any_print_in_window": sum(1 for r in cov if r["n_post"]), "units_with_fill_flow_print_in_window": sum(1 for r in cov if r["n_post_fill"]),
        "units_with_any_print_in_window_exited_only": sum(1 for r in cov_ex if r["n_post"]), "prints_in_unit_windows": sum(r["n_post"] for r in cov),
        "pre_k_24h": {"units_covered": len(pre_cov), "units_with_any_print": sum(1 for r in pre_cov if r["n_pre"]), "units_with_fill_flow_print": sum(1 for r in pre_cov if r["n_pre_fill"]),
                      "prints": sum(r["n_pre"] for r in pre_cov), "pre_x_post_units": {f"{a}|{b}": n for (a, b), n in sorted(split.items())}},
        "monitor_cycles": {"cycle_lines": len(cyc), "first_utc": iso(first) if cyc else None, "last_utc": iso(last) if cyc else None,
                           "gap_threshold_s": MONITOR_GAP_S, "gaps": len(gaps), "gap_seconds": round(sum(b - a for a, b in gaps), 1)},
        "share_of_covered_unit_windows_overlapping_a_cycle_gap": safe_div(sum(1 for r in cov if r["in_gap"]), len(cov)),
        "side_outcome_forms_seen_all_prints_ge_1000": dict(sorted(mon["forms"].items())),
        "fill_flow_mapping_used": "favoured YES: SELL with outcome_index 0 or BUY with outcome_index 1; favoured NO: SELL with outcome_index 1 or BUY with outcome_index 0 (outcome 0 = the YES token); the any-print counts do not depend on this mapping",
        "files_read": mon["files"], "missing_day_files": mon["missing_days"],
        "reading": "monitor prints under $1,000 are invisible: every number is a lower bound (S56); windows are cut on venue time (S57); no price, size or wallet field is read; units whose window is not inside the monitor's cycle lines are uncovered, not zero",
    }


# --------------------------------------------------------------------------------------------------------------- the engine pass (lines 3, 4 and ox, 9)


class OxCounts:
    """Per-market count of one-sided (quotes st = 3) slots among the last 84 slots, as a dense int16 array over market ids."""

    def __init__(self) -> None:
        self.cnt = np.zeros(1 << 20, np.int16)
        self.slots: dict = {}
        self.disabled = False

    def _ensure(self, m: int) -> None:
        if m >= len(self.cnt):
            new = np.zeros(max(m + 1, 2 * len(self.cnt)), np.int16)
            new[: len(self.cnt)] = self.cnt
            self.cnt = new

    def expire(self, slot: int) -> None:
        for s in [s for s in self.slots if s < slot - OX_SLOTS]:
            ids = self.slots.pop(s)
            if len(ids):
                self.cnt[ids] -= 1

    def history(self, slot: int) -> int:
        return sum(1 for s in self.slots if slot - OX_SLOTS <= s < slot)

    def get(self, ids: np.ndarray) -> np.ndarray:
        out = np.zeros(len(ids), np.int16)
        ok = ids < len(self.cnt)
        out[ok] = self.cnt[ids[ok]]
        return out

    def add(self, slot: int, ids: np.ndarray) -> None:
        if len(ids) and int(ids.max()) > 50_000_000:
            self.disabled = True
            return
        if len(ids):
            self._ensure(int(ids.max()))
            self.cnt[ids] += 1
        self.slots[slot] = ids


def _read_feat(p: Path, notes: Counter) -> dict | None:
    try:
        schema = pq.read_schema(guard_path(p)).names
        cols = [c for c in guard_columns(FEATURE_COLS) if c in schema]
        for c in FEATURE_COLS:
            if c not in schema:
                notes[f"features_column_missing:{c}"] += 1
        tb = pq.read_table(p, columns=cols)
    except Exception:  # noqa: BLE001
        notes["features_unreadable"] += 1
        return None
    n = tb.num_rows

    def col(name):
        return tb.column(name).to_numpy(zero_copy_only=False).astype(np.float64) if name in cols else np.full(n, np.nan)

    return {"ids": tb.column("market_id").to_numpy().astype(np.int64), "event": tb.column("event_id").to_pylist() if "event_id" in cols else [None] * n,
            "cat": tb.column("category").to_pylist() if "category" in cols else ["unknown"] * n, "neg": col("ms_neg_risk"), "log_liq": col("ms_log_liq"),
            "hte": col("ms_hours_to_end"), "end_ts": col("end_ts"), "n": n}


def _read_champion(p: Path | None, n: int, notes: Counter) -> np.ndarray | None:
    if p is None or not Path(p).exists():
        return None
    tb = pq.read_table(guard_path(p), columns=list(guard_columns(["dir_2h_dn", "dir_2h_up"])))
    if tb.num_rows != n:
        notes["predictions_not_aligned_with_features"] += 1
        return None
    return (tb.column("dir_2h_up").to_numpy().astype(np.float64) - tb.column("dir_2h_dn").to_numpy().astype(np.float64)) / c269.Q16


def _day_in(t: float, period: tuple[str, str]) -> bool:
    a = c240.parse_utc(period[0] + "T00:00:00Z")
    b = c240.parse_utc(period[1] + "T00:00:00Z") + DAY_S
    return a <= t < b


def hist_median(h: np.ndarray) -> float | None:
    tot = int(h.sum())
    if not tot:
        return None
    return float(np.searchsorted(np.cumsum(h), tot / 2.0) / 10000.0)


class EnginePass:
    def __init__(self, snap_by_slot: dict, periods: tuple) -> None:
        self.snaps = snap_by_slot
        self.periods = periods
        self.notes: Counter = Counter()
        self.ox = OxCounts()
        self.pending: dict | None = None
        # line 3
        self.l3: Counter = Counter()
        self.l3_event_sd: list[float] = []
        self.l3_between: list[float] = []
        self.l3_caps_with_pred = 0
        # line 4
        self.k1: Counter = Counter()
        self.k1_by_mid: Counter = Counter()
        self.k1_by_hte: Counter = Counter()
        self.k1_unreadable_sidecar = 0
        # ox
        self.ox_hist: Counter = Counter()
        self.ox_rows = 0
        self.ox_rows_full = 0
        self.ox_gt0 = 0
        self.ox_gt0_full = 0
        self.ox_hist_slots_present: Counter = Counter()
        # line 9
        self.spread = {pi: {"all": np.zeros((5, 10001), np.int64), SCOPE: np.zeros((5, 10001), np.int64)} for pi in range(len(periods))}
        self.spread_caps: Counter = Counter()

    def process(self, t: float, qpath: Path, fpath: Path | None, ppath: Path | None, in_count: bool, in_hist: bool, spread_pi: int | None) -> None:
        slot = c269.slot_of(t)
        q = c269.read_quotes(guard_path(qpath), slot, t)
        if self.pending is not None:
            self._resolve_k1(q, slot)
        feats = None
        if in_count or spread_pi is not None:
            feats = _read_feat(fpath, self.notes) if fpath is not None and Path(fpath).exists() else None
            if feats is None:
                self.notes["capture_without_features" if in_count else "spread_capture_without_features"] += 1
        self.ox.expire(slot)
        if in_count and feats is not None:
            self._count_capture(slot, q, feats, ppath)
        if spread_pi is not None:
            self._spread(spread_pi, q, feats)
        if in_hist or in_count:
            self.ox.add(slot, q.ids[q.st == 3])

    def _eligible(self, q, feats: dict, slot: int):
        pos, hit = c269._look(q.ids, feats["ids"])
        st = np.where(hit, q.st[pos], -1)
        cat_ok = np.array([c not in EXCL_ENGINE_CATS for c in feats["cat"]], bool)
        tgt = GRID0 + (slot + 1) * GRID_S
        with np.errstate(invalid="ignore"):
            dir_ok = np.isnan(feats["end_ts"]) | (feats["end_ts"] > tgt)
        elig = cat_ok & dir_ok & (st == 0)
        mid = np.where(elig, (q.bid[pos].astype(np.float64) + q.ask[pos].astype(np.float64)) / 2.0, np.nan)
        return elig, mid

    def _count_capture(self, slot: int, q, feats: dict, ppath: Path | None) -> None:
        elig, mid = self._eligible(q, feats, slot)
        n_el = int(elig.sum())
        self.l3["captures_with_features"] += 1
        self.l3["eligible_rows"] += n_el
        ids = feats["ids"][elig]
        # ox_1s_84: history strictly before k
        ox = self.ox.get(ids)
        hist = self.ox.history(slot)
        self.ox_hist_slots_present[hist] += 1
        self.ox_rows += n_el
        self.ox_gt0 += int((ox > 0).sum())
        if hist == OX_SLOTS:
            self.ox_rows_full += n_el
            self.ox_gt0_full += int((ox > 0).sum())
        for lo, hi, name in ((0, 0, "0"), (1, 2, "1-2"), (3, 12, "3-12"), (13, 42, "13-42"), (43, 84, "43-84")):
            self.ox_hist[name] += int(((ox >= lo) & (ox <= hi)).sum())
        # line 3
        neg = elig & (feats["neg"] > 0.5)
        ev = np.array([str(e) for e in np.array(feats["event"], dtype=object)[neg]], dtype=object)
        s = _read_champion(ppath, feats["n"], self.notes)
        if ppath is None or not Path(ppath).exists():
            self.notes["captures_without_champion_prediction_file"] += 1
        if len(ev):
            u, inv = np.unique(ev, return_inverse=True)
            n_ev = np.bincount(inv)
            ge3 = n_ev >= 3
            self.l3["negrisk_eligible_rows"] += int(neg.sum())
            self.l3["negrisk_events"] += int(len(u))
            self.l3["negrisk_events_with_co_n_ge_3"] += int(ge3.sum())
            self.l3["eligible_rows_in_negrisk_events_with_co_n_ge_3"] += int(n_ev[ge3].sum())
            if s is not None:
                self.l3_caps_with_pred += 1
                sv = s[neg]
                fin = np.isfinite(sv)
                nf = np.bincount(inv, weights=fin.astype(float))
                s1 = np.bincount(inv, weights=np.where(fin, sv, 0.0))
                s2 = np.bincount(inv, weights=np.where(fin, sv * sv, 0.0))
                ok = nf >= 3
                with np.errstate(invalid="ignore", divide="ignore"):
                    var = (s2 - s1 * s1 / nf) / (nf - 1)
                self.l3_event_sd.extend(float(x) for x in np.sqrt(np.clip(var[ok], 0.0, None)))
                self.l3["events_ge3_scored"] += int(ok.sum())
                if ok.sum() >= 2:
                    self.l3_between.append(float(np.std(s1[ok] / nf[ok], ddof=1)))
        hte = feats["hte"][elig]
        self.pending = {"slot": slot, "ids": ids, "mid": mid[elig], "hte": [hte_bin(h) for h in hte]}

    def _resolve_k1(self, q, slot: int) -> None:
        pend, self.pending = self.pending, None
        if pend["slot"] != slot - 1:
            self.notes["eligible_rows_without_k_plus_1_capture"] += len(pend["ids"])
            return
        ids, mid_k = pend["ids"], pend["mid"]
        pos, hit = c269._look(q.ids, ids)
        st = np.where(hit, q.st[pos], -1)
        one = st == 3
        side_bid = np.full(len(ids), np.nan)
        side_ask = np.full(len(ids), np.nan)
        if one.any():
            snap = self.snaps.get(slot)
            if snap is None:
                self.k1_unreadable_sidecar += int(one.sum())
            else:
                want = {int(i): j for j, i in zip(np.nonzero(one)[0], ids[one], strict=True)}
                it = j0.iter_csv(guard_path(Path(snap["dir"]) / "rows.csv.gz"), guard_columns(("market_id", "best_bid", "best_ask")))
                next(it, None)
                for mid_s, b, a in it:
                    try:
                        j = want.get(int(mid_s))
                    except ValueError:
                        continue
                    if j is not None:
                        side_bid[j], side_ask[j] = j0.r6(c240._f(b)), j0.r6(c240._f(a))
        for j in range(len(ids)):
            code = int(st[j])
            if code == 0:
                state = "labelled"
            elif code == 1:
                state = "closed"
            elif code == 2:
                state = "inactive"
            elif code == -1:
                state = "absent"
            else:
                bs = book_state(side_bid[j], side_ask[j])
                if bs == "bid_only":
                    state = "one_sided_sign_determinable_up" if side_bid[j] >= mid_k[j] + DELTA - SIGN_EPS else "one_sided_indeterminate"
                elif bs == "ask_only":
                    state = "one_sided_sign_determinable_down" if side_ask[j] <= mid_k[j] - DELTA + SIGN_EPS else "one_sided_indeterminate"
                else:
                    state = "one_sided_indeterminate"
            self.k1[state] += 1
            self.k1_by_mid[(state, c240.price_bin(float(mid_k[j])))] += 1
            self.k1_by_hte[(state, pend["hte"][j])] += 1

    def _spread(self, pi: int, q, feats: dict | None) -> None:
        self.spread_caps[pi] += 1
        two = q.st == 0
        if not two.any():
            return
        sp = np.clip(np.rint((q.ask[two].astype(np.float64) - q.bid[two].astype(np.float64)) * 10000.0), 0, 10000).astype(np.int64)
        ids = q.ids[two]
        tier = np.full(len(ids), 4, np.int64)
        scope = np.zeros(len(ids), bool)
        if feats is not None and feats["n"]:
            order = np.argsort(feats["ids"], kind="stable")
            pos, hit = c269._look(feats["ids"][order], ids)
            liq = np.expm1(feats["log_liq"][order][pos])
            cat = np.array([c not in EXCL_ENGINE_CATS for c in feats["cat"]], bool)[order][pos]
            t = np.where(~np.isfinite(liq), 4, np.where(liq < 1e3, 0, np.where(liq < 1e4, 1, np.where(liq < 1e5, 2, 3))))
            tier = np.where(hit, t, 4).astype(np.int64)
            scope = hit & cat
        for key, m in (("all", np.ones(len(ids), bool)), (SCOPE, scope)):
            self.spread[pi][key] += np.bincount(tier[m] * 10001 + sp[m], minlength=5 * 10001).reshape(5, 10001)

    def report(self) -> dict:
        l3 = self.l3
        el, in3 = l3.get("eligible_rows", 0), l3.get("eligible_rows_in_negrisk_events_with_co_n_ge_3", 0)
        k1 = self.k1
        n_k1 = sum(k1.values())
        det = k1.get("one_sided_sign_determinable_up", 0) + k1.get("one_sided_sign_determinable_down", 0)
        states = ("labelled", "one_sided_sign_determinable_up", "one_sided_sign_determinable_down", "one_sided_indeterminate", "absent", "closed", "inactive")

        def by(counter, dim_values):
            return {st: {v: counter.get((st, v), 0) for v in dim_values} for st in states}

        tier_names = (*j0.TIER_NAMES[:4], "tier_na")
        sp = {}
        for pi, per in enumerate(self.periods):
            lo, hi = c240.parse_utc(per[0] + "T00:00:00Z"), c240.parse_utc(per[1] + "T00:00:00Z") + DAY_S
            sp[f"{per[0]}..{per[1]}"] = {"captures_read": self.spread_caps.get(pi, 0), "expected_2h_slots": int((hi - lo) // GRID_S),
                                         **{key: {"rows": int(h.sum()), "p50_spread_all_tiers": hist_median(h.sum(axis=0)), **{f"p50_{tier_names[t]}": hist_median(h[t]) for t in range(5)},
                                                  **{f"rows_{tier_names[t]}": int(h[t].sum()) for t in range(5)}} for key, h in self.spread[pi].items()}}
        sds = self.l3_event_sd
        return {
            "line_3_negrisk_events_ge3": {
                "captures_with_features": l3.get("captures_with_features", 0), "captures_with_champion_predictions_aligned": self.l3_caps_with_pred,
                "eligible_rows": el, "negrisk_eligible_rows": l3.get("negrisk_eligible_rows", 0), "negrisk_events_with_eligible_members": l3.get("negrisk_events", 0),
                "negrisk_events_with_co_n_ge_3": l3.get("negrisk_events_with_co_n_ge_3", 0), "eligible_rows_in_negrisk_events_with_co_n_ge_3": in3,
                "share_eligible_rows_in_negrisk_events_with_co_n_ge_3": safe_div(in3, el), "events_ge3_with_3_scored_members": l3.get("events_ge3_scored", 0),
                "within_event_sd_of_s_2h": {"n_event_captures": len(sds), "median": median(sds), "p25": quant(sds, 0.25), "p75": quant(sds, 0.75)},
                "between_event_sd_of_event_mean_s_2h": {"n_captures": len(self.l3_between), "median_over_captures": median(self.l3_between)},
                "unit": "eligible = engine category not in sports / crypto / unknown, dir_2h-eligible by end_ts (the elig bit 1 rule, restated), two-sided in quotes/ at k; neg-risk = ms_neg_risk > 0.5; event = event_id; the champion's s_2h = P(up) - P(down) read as a distribution, no label"},
            "line_4_k_plus_1_state": {
                "eligible_rows_with_k_plus_1_capture": n_k1, "by_state": {s: k1.get(s, 0) for s in states}, "share_by_state": {s: safe_div(k1.get(s, 0), n_k1) for s in states},
                "sign_determinable_one_sided": det, "share_sign_determinable_one_sided": safe_div(det, n_k1),
                "by_state_x_mid_bin_k": by(self.k1_by_mid, MID_BINS), "by_state_x_hours_to_end_k": by(self.k1_by_hte, HTE_BINS),
                "one_sided_rows_without_sidecar_capture_at_k_plus_1": self.k1_unreadable_sidecar,
                "ox_1s_84": {"eligible_rows": self.ox_rows, "rows_with_ox_1s_84_gt_0": self.ox_gt0, "share_gt_0": safe_div(self.ox_gt0, self.ox_rows),
                             "rows_full_84_slot_history": self.ox_rows_full, "share_gt_0_full_history_only": safe_div(self.ox_gt0_full, self.ox_rows_full),
                             "distribution_rows_by_count": {k: self.ox_hist.get(k, 0) for k in ("0", "1-2", "3-12", "13-42", "43-84")},
                             "history_slots_present_at_k": {str(k): v for k, v in sorted(self.ox_hist_slots_present.items())},
                             "definition": "one-sided (quotes st = 3) slots among the 84 slots k - 84..k - 1 (k itself is two-sided by eligibility); missing quote slots are not one-sided and are visible in history_slots_present_at_k",
                             "id_range_guard_tripped": self.ox.disabled}},
            "line_9_spread_ops_line": {"periods": sp, "reading": "ops line for the cost model's refresh (qcm1), not a test: spread = ask - bid of two-sided quotes/ rows at 0.0001 resolution, tier from expm1(ms_log_liq); one venue event (rule 22); a disclosure for COST_MODEL.md, never a route"},
        }


# --------------------------------------------------------------------------------------------------------------- run


def run_map(snapshot_roots: list[Path], engine_root: Path, rules_root: Path, monitor_root: Path | None, start_ts: float, end_ts: float, engine_days: int = 8, warmup: int = 12,
            periods: tuple = PERIODS_DEFAULT, champion: str = CHAMPION) -> dict:
    span_days = (end_ts - start_ts) / DAY_S
    feed_lo = start_ts - warmup * GRID_S
    caps_ext, dnotes = discover_all(snapshot_roots, feed_lo, end_ts + 1.5 * GRID_S)
    caps = [c for c in caps_ext if c["start"] < end_ts]
    rules = c269.read_rules(rules_root)
    n_warm = sum(1 for c in caps if c["start"] < start_ts)
    sp = SidecarPass(start_ts, end_ts, rules, n_warm)
    for c in caps:
        sp.feed(c, c["start"] >= start_ts)
    sp.notes.update({f"discover:{k}": v for k, v in dnotes.items()})
    sp.notes.update(sp.j0.notes)
    days_n = Counter(c["day"] for c in sp.counted)
    full_days = sorted(d for d, n in days_n.items() if n >= FULL_DAY_CAPTURES)
    last_cap_start = caps[-1]["start"] if caps else math.nan

    # ---- engine
    ep = EnginePass({c["slot"]: c for c in caps_ext}, periods)
    eng = Path(engine_root)
    q_have = c269.list_captures(eng / "quotes", "*.parquet", ".parquet")
    f_have = c269.list_captures(eng / "features", "*.parquet", ".parquet")
    eng_lo = end_ts - engine_days * DAY_S
    first_count_slot = c269.slot_of(eng_lo)
    q_slots_seen = set()
    n_pred = 0
    for cid, (t, qp) in sorted(q_have.items(), key=lambda kv: kv[1][0]):
        slot = c269.slot_of(t)
        in_count = eng_lo <= t < end_ts
        in_hist = (first_count_slot - OX_SLOTS) <= slot < first_count_slot
        in_next = end_ts <= t < end_ts + 1.5 * GRID_S
        spi = next((i for i, per in enumerate(periods) if _day_in(t, per)), None)
        if not (in_count or in_hist or in_next or spi is not None):
            continue
        q_slots_seen.add(slot)
        pp = eng / "predictions" / cid / f"{champion}.parquet"
        n_pred += int(pp.exists() and in_count)
        ep.process(t, qp, f_have.get(cid, (None, None))[1], pp if pp.exists() else None, in_count, in_hist, spi)
    if ep.pending is not None:
        ep.notes["eligible_rows_without_k_plus_1_capture"] += len(ep.pending["ids"])
    er = ep.report()
    exp_slots = set(range(first_count_slot, c269.slot_of(end_ts)))
    miss_q = sorted(exp_slots - q_slots_seen)

    # ---- sidecar-side lines
    mon = read_monitor(monitor_root, start_ts, end_ts)
    l1, l2, l6, l7, l8 = line_1(sp), line_2(sp), line_6(sp, full_days), line_7(sp, full_days), line_8(sp, full_days, span_days)
    l5 = monitor_line(sp.units, mon, last_cap_start, full_days)
    res = {
        "version": VERSION,
        "kind": "CH276 surviving-side census: counts only, k = 0, uncounted; no resolution, label, outcome, payoff, wallet or post-k value read beyond the named counts; nothing printed is a target, a verdict or a P&L; no table, token, column or label is created",
        "line_1_field_semantics": l1,
        "line_2_one_sided_proposal_rows": l2,
        "line_3_negrisk_events_ge3": er["line_3_negrisk_events_ge3"],
        "line_4_k_plus_1_state": er["line_4_k_plus_1_state"],
        "line_5_monitor_prints": l5,
        "line_6_b_units": l6,
        "line_7_near_certain_first_crossings": l7,
        "line_8_insurance_and_disputes": l8,
        "line_9_spread_ops_line": er["line_9_spread_ops_line"],
        "decisions": decisions(er, l1, l5, l6, l7, l8),
        "span": {"start_utc": iso(start_ts), "end_utc": iso(end_ts), "days": span_days, "engine_days": engine_days, "warmup_captures_fed_before_start": n_warm, "counted_captures": len(sp.counted),
                 "counted_with_previous": sum(1 for c in sp.counted if c["with_prev"]), "full_days": full_days, "captures_per_day": dict(sorted(days_n.items())),
                 "missing_engine_quote_slot_count": len(miss_q), "missing_engine_quote_slots_in_engine_window": [iso(GRID0 + s * GRID_S) for s in miss_q][:200],
                 "engine_prediction_files_in_window": n_pred},
        "rules_stream": {"info": rules["info"], "classifier": "PLACEHOLDER lexicon of census_map_ch269 (not CH239's parser, not the engine's rules table)", "classes_n": dict(Counter(rules["classes"].values()))},
        "notes": {"sidecar": dict(sorted(sp.notes.items())), "engine": dict(sorted(ep.notes.items()))},
        "not_mapped": NOT_MAPPED,
        "decision_lines": LINES,
        "inputs": sp.j0.inputs,
        "engine_inputs": {"quote_captures_in_store": len(q_have), "feature_captures_in_store": len(f_have), "quote_slots_read": len(q_slots_seen)},
        "peak_rss_mb": peak_rss_mb(),
        "code_sha256": code_sha256(),
    }
    check_output(res)
    return res


# --------------------------------------------------------------------------------------------------------------- report builders


def line_1(sp: SidecarPass) -> dict:
    s, sib, sibs = sp.sem, sp.sem_sib, sp.sem_sib_scope
    share = safe_div(sib.get("carries_a_proposal", 0), sib.get("siblings_total", 0))
    lo, hi = LINES["semantics_per_market_if_sibling_carry_share_below"], LINES["semantics_event_level_if_sibling_carry_share_above"]
    reading = None if share is None else "per_market" if share < lo else "event_level" if share > hi else "mixed"
    return {
        "semantics_reading": reading,
        "reading_rule": f"share of siblings (other open members of a neg-risk group at the capture where one member first shows a proposal) whose own status carries a proposal: below {lo} = per_market, above {hi} = event_level, else mixed; a reading aid for CH273 / CH275, not a gate",
        "sibling_carry_share": share,
        "siblings_of_first_seen_proposals": {k: sib.get(k, 0) for k in ("proposed_markets_first_seen_in_groups_ge2", "siblings_total", "unflagged_empty_status", "carries_a_proposal", "other_status", "sibling_status_string_identical_to_proposed")},
        "siblings_of_first_seen_proposals_in_scope_nonsports_excrypto": {k: sibs.get(k, 0) for k in ("siblings_total", "unflagged_empty_status", "carries_a_proposal", "other_status")},
        "status_list_length_vs_neg_risk_group_size": {k: sp.sem_len_vs_size.get(k, 0) for k in ("len_lt_group_size", "len_eq_group_size", "len_gt_group_size")},
        "status_list_length_vs_members_with_any_status": {k: sp.sem_len_vs_w.get(k, 0) for k in ("len_lt_members_with_status", "len_eq_members_with_status", "len_gt_members_with_status")},
        "status_list_length_histogram_statused_open_rows": {k: sp.sem_len_hist.get(k, 0) for k in ("1", "2", "3-5", "6-10", "11+")},
        "group_captures": {k: s.get(k, 0) for k in ("group_captures_size_ge2", "groups_of_size_1", "group_captures_with_any_status", "all_members_have_status", "some_members_have_status",
                                                    "groups_with_2plus_statused_members", "groups_all_statused_members_identical_string")},
        "definitions": "group = open binary rows sharing a non-empty neg_risk_market_id at the capture; status 'carries a proposal' = the sidecar list contains 'propos'; list length parsed as a JSON / Python list (comma count otherwise); all categories (a venue field), the in-scope subset beside it",
    }


def line_2(sp: SidecarPass) -> dict:
    by_side: Counter = Counter()
    by_fav: Counter = Counter()
    by_tier: Counter = Counter()
    cube = {}
    for (st, fav, tier), n in sp.one_sided.items():
        by_side[st] += n
        by_fav[(st, fav)] += n
        by_tier[(st, tier)] += n
        cube[f"{st}|{fav}|{tier}"] = n
    check = sp.j0.funnel.get("not_two_sided", 0)
    return {
        "first_seen_proposal_rows_in_scope": sp.first_seen_rows, "not_two_sided_rows": sp.funnel_not_two_sided, "not_two_sided_rows_by_surviving_side": dict(sorted(by_side.items())),
        "by_surviving_side_x_favoured_side": {f"{a}|{b}": n for (a, b), n in sorted(by_fav.items())}, "by_surviving_side_x_tier": {f"{a}|{b}": n for (a, b), n in sorted(by_tier.items())},
        "by_surviving_side_x_favoured_side_x_tier": dict(sorted(cube.items())),
        "consistency_with_m1_j0_funnel_not_two_sided": {"this_map": sp.funnel_not_two_sided, "j0_pass": check, "equal": sp.funnel_not_two_sided == check},
        "favoured_side_rule": "from the surviving price p: p >= 0.90 favours YES, p <= 0.10 favours NO, otherwise mid_zone; both sides missing = undetermined; the surviving price is the sidecar best_bid / best_ask at k (quotes/ keeps no price for a one-sided row)",
        "definitions": "rows = M1's E1-E7 funnel at the first capture showing a proposal, up to and including the scope test, whose book is not two-sided; bid_only = best_bid > 0 with no valid ask; ask_only = valid ask with no bid; crossed_or_locked and no_quote counted apart",
    }


def line_6(sp: SidecarPass, full_days: list[str]) -> dict:
    bu = sp.b_units
    two = [b for b in bu if b["state"] == "two_sided"]
    per_day_two = Counter(b["day"] for b in two)
    by_size = Counter((b["size"], b["state"]) for b in bu)
    moved = Counter("moved" if b["moved"] else "unmoved" if b["moved"] is False else "no_two_sided_k_minus_1" for b in two)
    n_elig = sum(1 for b in bu if b["elig"])
    return {
        "b_units_total": len(bu), "b_units_two_sided": len(two), "b_units_no_bid_ask_only": sum(1 for b in bu if b["state"] == "ask_only"), "b_units_no_ask_bid_only": sum(1 for b in bu if b["state"] == "bid_only"),
        "b_units_other_book": sum(1 for b in bu if b["state"] in ("crossed_or_locked", "no_quote")), "no_bid_share_of_b_units": safe_div(sum(1 for b in bu if b["state"] == "ask_only"), len(bu)),
        "b_units_a_day_all": dict(sorted(Counter(b["day"] for b in bu).items())), "two_sided_b_units_a_day": dict(sorted(per_day_two.items())), "median_two_sided_b_units_per_full_day": full_day_median(per_day_two, full_days),
        "by_group_size_x_book_state": {f"{a}|{b}": n for (a, b), n in sorted(by_size.items())}, "two_sided_bid_moved_vs_unmoved_k_minus_1_to_k": dict(sorted(moved.items())),
        "moved_share_of_two_sided_with_k_minus_1": safe_div(moved.get("moved", 0), moved.get("moved", 0) + moved.get("unmoved", 0)),
        "E_B": {"b_units_in_engine_eligible_form": n_elig, "share_of_all_b_units": safe_div(n_elig, len(bu)), "share_of_two_sided_b_units": safe_div(n_elig, len(two)),
                "note": "sidecar-side restatement (YES mid in [0.02, 0.98], two-sided, no own proposal); the engine's end_ts / dir eligibility is not applied here"},
        "b_candidate_classes_excluded_or_counted": dict(sorted(sp.b_classes.items())), "winner_units_with_empty_neg_risk_market_id": sp.winner_no_group,
        "definitions": "A = an M1 unit (J0Pass) whose favoured side is YES and whose neg_risk_market_id is non-empty; B = every other open binary row of A's group, in scope, with no own status at k and no proposal state at k - 1; one unit per B market; group size = open binary rows of the group at k",
    }


def line_7(sp: SidecarPass, full_days: list[str]) -> dict:
    U = sp.cross_units
    per_day = Counter(u["day"] for u in U)
    withp = [u for u in U if u["first_prop"] is not None]
    before = sum(1 for u in withp if u["first_prop"] < u["end_ts"])
    nc = sp.near_cert
    pop = len(U) + sum(nc.values())

    def cnt(key):
        return dict(sorted(Counter(u[key] for u in U).items()))

    return {
        "crossings_total": len(U), "crossings_a_day": dict(sorted(per_day.items())), "median_crossings_per_full_day": full_day_median(per_day, full_days),
        "by_rules_class": cnt("cls"), "by_tier": cnt("tier"), "by_hours_to_end_bin": cnt("hte"),
        "by_rules_class_x_tier_x_hours_to_end": dict(sorted(Counter(f"{u['cls']}|{u['tier']}|{u['hte']}" for u in U).items())),
        "classed_share": safe_div(sum(1 for u in U if u["cls"] != "no_rules"), len(U)),
        "near_certain_markets_seen": pop, "born_certain": nc.get("born_certain", 0), "pre_window_certain_by_window_start": nc.get("pre_window_certain_by_window_start", 0),
        "first_sight_certain_old_market": nc.get("first_sight_certain_old_market", 0),
        "born_certain_share": safe_div(nc.get("born_certain", 0), pop), "pre_window_share": safe_div(nc.get("pre_window_certain_by_window_start", 0), pop),
        "crossing_candidates_excluded": dict(sorted((k, v) for k, v in sp.cross_classes.items() if k != "unit")),
        "proposed_before_end_date": {"units_with_a_proposal_in_span": len(withp), "proposed_before_end_date": before, "share": safe_div(before, len(withp)),
                                     "note": "a lagged count: the first later capture whose sidecar status carries 'propos', compared with the unit's end_date; units with no proposal in the span are not in the denominator"},
        "definitions": "non-sports ex-crypto, two-sided at k and k - 1, favoured ask >= 0.95 at k (YES ask, or NO ask = 1 - YES bid) and < 0.95 at k - 1, never certain at an earlier fed capture, no status at k, end_date > k + 24 h, market age (created_at) >= 12 slots; the rules class is the placeholder lexicon (no_rules = market absent from the stream)",
    }


def line_8(sp: SidecarPass, full_days: list[str], span_days: float) -> dict:
    U = sp.units
    cls = ("uninsured", "middle", "insured")
    per_day = {c: Counter(u["day"] for u in U if u["ins_class"] == c) for c in cls}
    n_cls = Counter(u["ins_class"] for u in U)
    scale = 21.0 / span_days if span_days else math.nan
    runs = [r for r in sp.disp_runs.values() if r["counted"] and not r["pre_existing"]]
    runs_scope = [r for r in runs if r["cat"] == SCOPE]
    per_day_d = Counter(r["day"] for r in runs_scope)

    def dur(rs):
        v = [r["len"] for r in rs if r["ended"]]
        return {"ended_runs": len(v), "median_captures": median(v), "max_captures": max(v) if v else None, "right_censored_runs": sum(1 for r in rs if not r["ended"])}

    n_events = len(sp.first_seen_events)
    unit_events = len({u["event"] for u in U})
    return {
        "proposal_units_total": len(U), "by_insurance_class": {c: n_cls.get(c, 0) for c in cls}, "units_a_day_by_insurance_class": {c: dict(sorted(per_day[c].items())) for c in cls},
        "median_per_full_day_by_insurance_class": {c: full_day_median(per_day[c], full_days) for c in cls},
        "insured_units_scaled_to_21_days": None if not math.isfinite(scale) else n_cls.get("insured", 0) * scale,
        "zone_counts_of_1_minus_bid_k": dict(sorted(Counter(u["zone"] for u in U).items())),
        "insurance_class_definition": {"uninsured": f"<= {UNINSURED_MAX}", "insured": f"> {INSURED_MIN}", "middle": "between", "ins_k": "1 - bid of the favoured side (YES: 1 - best_bid; NO: best_ask), rounded to 6 dp; zone counts only, never a value"},
        "disputed_state_first_appearances_in_span_all_categories": len(runs), "disputed_state_first_appearances_in_scope": len(runs_scope), "disputed_first_appearances_a_day_in_scope": dict(sorted(per_day_d.items())),
        "median_disputed_first_appearances_per_full_day_in_scope": full_day_median(per_day_d, full_days),
        "of_which_preceded_by_a_proposal_state_in_the_feed": sum(1 for r in runs_scope if r["after_proposal"]),
        "duration_in_captures_in_scope": dur(runs_scope), "duration_in_captures_all_categories": dur(runs),
        "disputed_already_present_at_feed_start_excluded": sum(1 for r in sp.disp_runs.values() if r["pre_existing"]), "disputed_runs_not_counted_started_in_warmup": sum(1 for r in sp.disp_runs.values() if not r["counted"] and not r["pre_existing"]),
        "disputed_reappearances_after_a_run_ended_not_counted_as_first": sp.disp_reappear,
        "proposal_events_in_scope_first_seen_rows": n_events, "proposal_events_of_m1_units": unit_events,
        "disputes_share_of_proposal_events_first_seen_rows": safe_div(len(runs_scope), n_events), "disputes_share_of_proposal_events_of_m1_units": safe_div(len(runs_scope), unit_events),
        "lingering_and_absent_at_k_plus_1_shares": "not computed: they need the dispute target and the listing after k for a unit (a post-k state), which section E (8) does not name; the first-appearance and duration counts above are the whole of (8)'s state reads",
        "definitions": "units = M1's (J0Pass) first capture showing a proposal, two-sided, favoured side >= 0.90; disputed state = the sidecar status list contains 'disput'; first appearance = first capture of a market's first contiguous run; duration = captures in that run",
    }


def decisions(er: dict, l1: dict, l5: dict, l6: dict, l7: dict, l8: dict) -> dict:
    def ge(v, line):
        return None if v is None else bool(v >= line)

    l3, l4 = er["line_3_negrisk_events_ge3"], er["line_4_k_plus_1_state"]
    share3, sd3 = l3["share_eligible_rows_in_negrisk_events_with_co_n_ge_3"], l3["within_event_sd_of_s_2h"]["median"]
    c270 = None if share3 is None or sd3 is None else bool(share3 >= LINES["ch270_built_if_share_of_eligible_rows_in_negrisk_events_with_co_n_ge_3_at_least"] and sd3 >= LINES["ch270_built_if_median_event_within_sd_of_s_2h_at_least"])
    m5 = l5.get("median_units_with_any_print_per_full_day") if l5.get("available") else None
    b6 = l6["median_two_sided_b_units_per_full_day"]
    sem = l1["semantics_reading"]
    c273 = None if b6 is None or sem is None else bool(b6 >= LINES["ch273_drafted_if_two_sided_b_units_a_day_at_least"] and sem == "per_market")
    ins_s = l8["insured_units_scaled_to_21_days"]
    dis = l8["disputes_share_of_proposal_events_first_seen_rows"]
    c275 = None if ins_s is None or dis is None else bool(ins_s >= LINES["ch275_census_if_insured_units_scaled_to_21_days_at_least"] and dis >= LINES["ch275_census_if_disputes_share_of_proposal_events_at_least"])
    return {
        "ch270": {"share_rows_in_events_co_n_ge_3": share3, "median_within_event_sd_s_2h": sd3, "built": c270},
        "ch271_b": {"share_sign_determinable_one_sided": l4["share_sign_determinable_one_sided"], "built": ge(l4["share_sign_determinable_one_sided"], LINES["ch271_b_if_share_of_eligible_rows_with_sign_determinable_one_sided_k1_at_least"])},
        "ch271_c": {"share_ox_1s_84_gt_0": l4["ox_1s_84"]["share_gt_0"], "built": ge(l4["ox_1s_84"]["share_gt_0"], LINES["ch271_c_if_share_of_eligible_rows_with_ox_1s_84_gt_0_at_least"])},
        "ch272": {"median_proposal_units_with_a_print_per_full_day": m5, "filed_as_m1_amendment": ge(m5, LINES["ch272_amendment_if_proposal_units_a_day_with_a_print_at_least"]),
                  "else": "share-only line" if m5 is not None and m5 < LINES["ch272_amendment_if_proposal_units_a_day_with_a_print_at_least"] else None},
        "ch273": {"median_two_sided_b_units_per_full_day": b6, "status_field": sem, "drafted": c273},
        "ch274": {"median_crossings_per_full_day": l7["median_crossings_per_full_day"], "built": ge(l7["median_crossings_per_full_day"], LINES["ch274_if_crossings_a_day_at_least"])},
        "ch275": {"insured_units_scaled_to_21_days": ins_s, "disputes_share_of_proposal_events": dis, "goes_to_census": c275},
        "a_decision_is_none_when_its_count_is_unavailable": True,
        "reading": "a decision of null means a count was unavailable (not a pass); the lines are the section text's, restated; a reading aid, never a gate that was tuned",
    }
