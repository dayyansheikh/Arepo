# ruff: noqa: E501
"""CH269, the one-shot census and the tails map (docs/research_lab/CREATIVE_HYPOTHESES_2026-11-02.md section 2 F). COUNTS ONLY, k = 0, uncounted.

A read-only reader over four stores the host already keeps:

* the 2-hourly sidecars (``snapshots/<capture>/rows.csv.gz``, ``rows_ext.csv.gz``, ``manifest.json``), the last N days (default 8);
* the signal engine's ``quotes/<capture>.parquet`` (every binary market of a complete capture; bid / ask two-sided only; status code), ``features/``,
  ``predictions/<capture>/<model>.parquet`` and ``logs/resolutions-*.jsonl`` (the label store; no new resolution is fetched);
* the keyless ``stream_gamma_rules`` day files (the rule text, classified here by a PLACEHOLDER lexicon; CH239's parser is not in the repository).

Nothing in the engine's code is imported or edited; the files are opened read-only through this module's own readers. Missing captures, files and columns are listed as
missing and never reconstructed. Nothing printed is a target, a verdict or a P&L. Used from capture k: only capture k and k - 1 of the sidecars; the quotes of slot k + 1 are
read ONLY for a status code (two-sided / not) of a unit already fixed at k (CH262's ``unavailable`` share, CH266's usable share), never for a mid, and the residual of CH265
and the label store of CH266's map are the engine's own past labelling frame (section F declares them).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import resource
import sys
from array import array
from collections import Counter, deque
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from . import boundary_map_ch240 as c240
from . import population_map_ch251 as c251

VERSION = "ch269-census-map-v1"
GRID0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC).timestamp()
GRID_S = 7200.0
GAP_MAX_S = c240.GAP_MAX_S
CATS = c240.CATS
ELIG_CAT = CATS.index("nonsports_excrypto")
UNMAPPED = 4
CAT_NAMES = (*CATS, "unmapped")
TIER_NAMES = ("lt1k", "1k-10k", "10k-100k", "ge100k", "tier_na")
TIER_EDGES = (1e3, 1e4, 1e5)
ROW_COLS = ("market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date")
EXT_COLS = ("market_id", "fee_type", "fee_category", "series_slugs", "fees_enabled", "fee_schedule", "accepting_orders", "open_interest", "volume_num", "uma_resolution_statuses")
OVERDUE_S = 7200.0
OVERDUE_FRESH_S = 24 * 3600.0
CLOSE_WIN_S = 5 * 3600.0
DIR_DELTA, DIR_TOL = 0.005, 1e-6  # the engine's frozen direction constants, restated (not imported)
Q16 = 65535.0
DISPLAY, PLACEBO = 0.010, 0.015
EPS = 1e-9
LINES = {
    "lt14_drafted_if_median_top_decile_units_10k_100k_per_capture_at_least": 100,
    "m1_ch263_drafted_if_proposals_seen_a_day_exceed": 100,
    "m2_ch264_drafted_if_overdue_units_a_day_exceed": 25,
    "lt15_ch267_drafted_if_scheduled_class_closes_a_day_exceed": 30,
    "ch266_sketch_if_display_crossings_a_day_exceed": 50,
    "ch263_window_extended_to_42_days_if_proposals_a_day_below": 100,
    "ch268_hygiene_only_if_fr_unavail_12_positive_on_under_share": 0.05,
    "ch268_killed_if_abs_corr_with_log1p_liquidity_above": 0.8,
}
SCHEDULED_RE = re.compile(r"\b(scheduled|fomc|federal reserve|cpi|consumer price index|jobs report|nonfarm|unemployment rate|gdp|earnings|box office|election|vote|referendum|certified|official (?:results?|data|release|figures?)|will be (?:released|published|announced)|press release)\b")
BARRIER_RE = re.compile(r"\b(at any point|at any time|any time|reach(?:es)?|hits?|touch(?:es)?|dips?|exceeds?|before|by (?:january|february|march|april|may|june|july|august|september|october|november|december|the end of))\b")
NOT_MAPPED = {
    "ask_size_1_coverage": "not mapped: sweep 1's ask_size_1 (book_sweeps) is a separate light step; CH263's capacity line is therefore unprinted here",
    "open_interest": "printed as presence only (share of sidecar rows with a non-empty open_interest); when it is empty the tercile arms of CH264 are printed on a LIQUIDITY proxy, labelled as such",
    "rule_class": "PLACEHOLDER lexicon of this map (printed in the output), not CH239's parser; counts only, no class is a design input until the builder pins one",
    "tier": "liquidity tier = the sidecar rows' liquidity at the capture (< 1k, 1k-10k, 10k-100k, >= 100k); the cost model's own definition is not re-derived here",
    "proposal_time": "the sidecar carries no proposal timestamp; hours-to-liveness arms are unavailable (as the section 0.3 fact 6 says)",
    "ch262_rung_constants_mde": "not mapped: the rung constants, MDE and F-MDE and VIF_w of decile membership are design-stage items of the CH262 census text; only the counts, tenure and unavailable share are printed",
    "ch267_identification_gate": "not mapped: the within- vs between-stratum SD of the class label and the MDE are design-stage items; the class split and strata counts are printed",
    "category_lookup": "category and tier of a market in the engine's stores are the LATEST sidecar capture's reading (this map's last 8 days); a market not in any covered sidecar is 'unmapped' and counted",
    "fee_class_for_engine_captures": "the CH262 fee-class split is printed only for engine captures that lie inside the covered sidecar span, at the capture's own fee_schedule; other captures print fee_na",
}


def code_sha256(files: tuple[Path, ...] | None = None) -> dict:
    fs = files or (Path(__file__), Path(__file__).resolve().parents[2] / "scripts" / "run_ch269_map.py")
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fs if p.exists()}


def tier_of(liq: float) -> int:
    if not math.isfinite(liq):
        return 4
    return 0 if liq < TIER_EDGES[0] else 1 if liq < TIER_EDGES[1] else 2 if liq < TIER_EDGES[2] else 3


def dist(vals) -> dict:
    v = sorted(float(x) for x in vals if x == x)
    n = len(v)
    if not n:
        return {"n": 0}
    med = v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0
    return {"n": n, "min": v[0], "p25": v[(n - 1) // 4], "median": med, "mean": sum(v) / n, "p75": v[(3 * (n - 1)) // 4], "max": v[-1]}


def median_of(vals) -> float | None:
    d = dist(vals)
    return d.get("median")


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return math.nan, math.nan
    p = wins / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return ctr - half, ctr + half


def pearson(s: list[float] | np.ndarray) -> float:
    n, sx, sy, sxx, syy, sxy = s
    if n < 3:
        return math.nan
    vx, vy = sxx - sx * sx / n, syy - sy * sy / n
    return float((sxy - sx * sy / n) / math.sqrt(vx * vy)) if vx > 0 and vy > 0 else math.nan


def acc_pairs(s: list, x: np.ndarray, y: np.ndarray) -> None:
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok].astype(np.float64), y[ok].astype(np.float64)
    s[0] += len(x)
    s[1] += float(x.sum())
    s[2] += float(y.sum())
    s[3] += float((x * x).sum())
    s[4] += float((y * y).sum())
    s[5] += float((x * y).sum())


def sha256_file(p: Path) -> str:
    return c240.sha256_file(p)


def cap_time(cid: str) -> float:
    try:
        return datetime.strptime(cid[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()
    except ValueError:
        return math.nan


def slot_of(t: float) -> int:
    return int(round((t - GRID0) / GRID_S))


# --------------------------------------------------------------------------------------------------------------- rules (placeholder lexicon)


def classify_rule(text: str) -> str:
    t = text.lower()
    s, b = bool(SCHEDULED_RE.search(t)), bool(BARRIER_RE.search(t))
    return "scheduled" if s and not b else "barrier" if b and not s else "both" if s and b else "other"


def read_rules(root: Path | None) -> dict:
    """{market_id: class} from the keyless gamma_rules day files (rows with key m:<id>; the last row per market wins). Text is classified and dropped."""
    out: dict = {}
    info = {"files": 0, "row_lines": 0, "markets": 0, "day_files": []}
    if root is None or not Path(root).exists():
        return {"classes": out, "info": info}
    for f in sorted(Path(root).glob("*.jsonl")):
        info["files"] += 1
        info["day_files"].append(f.name)
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if '"row"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                key = str(d.get("key", ""))
                if d.get("kind") != "row" or not key.startswith("m:"):
                    continue
                data = d.get("data")
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except ValueError:
                        data = {}
                if not isinstance(data, dict):
                    continue
                try:
                    mid = int(key[2:])
                except ValueError:
                    continue
                txt = " ".join(str(data.get(k) or "") for k in ("question", "description", "resolutionSource"))
                out[mid] = classify_rule(txt)
                info["row_lines"] += 1
    info["markets"] = len(out)
    return {"classes": out, "info": info}


# --------------------------------------------------------------------------------------------------------------- sidecar pass (last N days)

_CAT_MEMO: dict = {}


def _cat(ft, fc, ss) -> int:
    k = (ft, fc, ss)
    v = _CAT_MEMO.get(k)
    if v is None:
        v = CATS.index(c240.category_of(ft, fc, ss, True))
        if len(_CAT_MEMO) < 50000:
            _CAT_MEMO[k] = v
    return v


def read_ext(path: Path | None) -> tuple[dict, dict, dict]:
    """(E, X, flags): E[mid] = cat + 4 fee + 12 acc + 36 uma (fee 0 free / 1 on / 2 unknown; acc 0 false / 1 true / 2 unknown; uma 0 none / 1 proposed / 2 other),
    X[mid] = (open_interest, volume_num) for the nonsports_excrypto markets only, flags = {rows, open_interest_nonempty}."""
    E: dict = {}
    X: dict = {}
    flags = {"rows": 0, "open_interest_nonempty": 0, "columns_present": {}}
    if path is None or not Path(path).exists():
        return E, X, flags
    it = c240._iter_csv(path, EXT_COLS)
    pres = next(it, None)
    if pres is None:
        return E, X, flags
    flags["columns_present"] = {c: bool(p) for c, p in zip(EXT_COLS, pres, strict=True)}
    has_fe = pres[EXT_COLS.index("fees_enabled")]
    for mid_s, ft, fc, ss, fe, fsch, acc, oi, vn, uma in it:
        try:
            mid = int(mid_s)
        except ValueError:
            continue
        flags["rows"] += 1
        cat = _cat(ft, fc, ss)
        fcl = c251.fee_class(fe, has_fe, fsch)[0]
        feei = 0 if fcl == "fee_free" else 1 if fcl == "fee_on" else 2
        a = str(acc).strip().lower()
        acci = 1 if a in ("true", "1", "1.0", "t") else 0 if a in ("false", "0", "0.0", "f") else 2
        u = str(uma).strip().lower()
        ui = 1 if "propos" in u else 0 if u in ("", "[]", "nan", "none") else 2
        E[mid] = cat + 4 * feei + 12 * acci + 36 * ui
        oif = c240._f(oi)
        if oif == oif:
            flags["open_interest_nonempty"] += 1
        if cat == ELIG_CAT:
            X[mid] = (oif, c240._f(vn))
    return E, X, flags


class SidecarPass:
    """Feeds captures in time order; keeps only capture k - 1's id array, proposal set and the ELIG end dates, plus small per-unit lists."""

    def __init__(self) -> None:
        self.idx = 0
        self.prev_t = math.nan
        self.prev_ids: np.ndarray | None = None
        self.prev_prop: set = set()
        self.prev_end: dict = {}
        self.first_prop: dict = {}  # mid -> (capture start, category) for every first proposal state seen
        self.props: list[dict] = []  # first-seen proposal units (all categories)
        self.props_unavail: Counter = Counter()  # no k - 1 row or no previous capture
        self.overdue_seen: set = set()
        self.overdue_units: list[dict] = []
        self.overdue_late: list[dict] = []
        self.overdue_funnel: list[dict] = []
        self.closing: dict = {}  # mid -> [end, tier, ev, fee, s4, s2]
        self.moved: set = set()
        self.caps: list[dict] = []
        self.lk_ids = np.empty(0, np.int64)
        self.lk_cat = np.empty(0, np.int8)
        self.lk_tier = np.empty(0, np.int8)
        self.fee_by_cap: dict = {}
        self.oi_nonempty = 0
        self.ext_rows = 0
        self.notes: Counter = Counter()

    def feed(self, cid: str, start: float, rows_path: Path, ext_path: Path | None) -> None:
        day = c240.day_of(start)
        has_prev = self.prev_ids is not None and 0 < start - self.prev_t <= GAP_MAX_S
        E, X, flags = read_ext(ext_path)
        self.oi_nonempty += flags["open_interest_nonempty"]
        self.ext_rows += flags["rows"]
        if not E:
            self.notes["captures_without_usable_sidecar"] += 1
        it = c240._iter_csv(rows_path, ROW_COLS)
        pres = next(it, None)
        if pres is None:
            return
        for c, p in zip(ROW_COLS, pres, strict=True):
            if not p:
                self.notes[f"rows_column_missing:{c}"] += 1
        ids, cats, tiers = array("q"), array("b"), array("b")
        eids, efee = array("q"), array("b")
        evc: Counter = Counter()
        cands: list = []
        cur_prop: set = set()
        cur_end: dict = {}
        fun = Counter()
        n_open = n_elig = 0
        for mid_s, ev, _rec, closed, active, binary, bid, ask, liq, end in it:
            if not c240._truthy(binary):
                continue
            try:
                mid = int(mid_s)
            except ValueError:
                continue
            pk = E.get(mid)
            cat = pk % 4 if pk is not None else 3
            tier = tier_of(c240._f(liq))
            ids.append(mid)
            cats.append(cat if pk is not None else UNMAPPED)
            tiers.append(tier)
            if c240._truthy(closed) or not c240._truthy(active):
                continue
            n_open += 1
            evc[ev] += 1
            b_f, a_f = c240._f(bid), c240._f(ask)
            two = b_f > 0 and a_f > 0 and a_f <= 1 and b_f < a_f
            midp = (b_f + a_f) / 2.0 if two else math.nan
            if pk is None:
                continue
            fee, acc, uma = (pk // 4) % 3, (pk // 12) % 3, pk // 36
            if uma == 1:
                cur_prop.add(mid)
                if mid not in self.prev_prop:
                    cands.append((mid, cat, tier, fee, two, midp, (a_f - b_f) / 2.0 if two else math.nan, ev))
            if cat != ELIG_CAT:
                continue
            n_elig += 1
            eids.append(mid)
            efee.append(fee)
            end_ts = c240.parse_utc(end)
            if end_ts != end_ts:
                fun["elig_open_without_end_date"] += 1
                continue
            cur_end[mid] = end_ts
            pe = self.prev_end.get(mid)
            moved = pe is not None and abs(pe - end_ts) > 1.0
            if moved:
                self.moved.add(mid)
            age = start - end_ts
            if age >= OVERDUE_S:
                fun["past_end"] += 1
                if acc == 1:
                    fun["accepting"] += 1
                    if uma == 0:
                        fun["no_proposal"] += 1
                        if two:
                            fun["two_sided"] += 1
                            if 0.05 <= midp <= 0.95:
                                fun["interior_mid"] += 1
                                if mid not in self.overdue_seen:
                                    self.overdue_seen.add(mid)
                                    oi, vn = X.get(mid, (math.nan, math.nan))
                                    u = {"mid": mid, "day": day, "tier": tier, "age_h": age / 3600.0, "oi": oi, "vol": vn, "liq": c240._f(liq), "moved": bool(moved), "ev": ev, "fee": fee, "warm": self.idx == 0}
                                    if self.idx == 0:
                                        pass
                                    elif age <= OVERDUE_FRESH_S:
                                        self.overdue_units.append(u)
                                    else:
                                        self.overdue_late.append(u)
            tte = end_ts - start
            if 0 < tte <= CLOSE_WIN_S:
                rec = self.closing.get(mid)
                if rec is None:
                    rec = self.closing[mid] = [end_ts, tier, ev, fee, 0, 0]
                rec[0] = end_ts
                if two and tte > 3 * 3600:
                    rec[4] = 1
                elif two and tte > 3600:
                    rec[5] = 1
        # proposals first seen at k
        prev_sorted = self.prev_ids
        for mid, cat, tier, fee, two, midp, hs, ev in cands:
            known_before = False
            if has_prev and prev_sorted is not None and len(prev_sorted):
                j = int(np.searchsorted(prev_sorted, mid))
                known_before = j < len(prev_sorted) and int(prev_sorted[j]) == mid
            if not known_before:
                self.props_unavail["no_k_minus_1_row" if has_prev else "no_previous_capture"] += 1
                self.first_prop.setdefault(mid, (start, cat))
                continue
            self.first_prop.setdefault(mid, (start, cat))
            size = evc[ev]
            pos = "standalone" if size == 1 else ("member_leading" if two and midp >= 0.9 else "member_trailing" if two and midp <= 0.1 else "member_other" if two else "member_not_two_sided")
            side = "readable" if two and max(midp, 1 - midp) >= 0.9 else "two_sided_unread" if two else "not_two_sided"
            self.props.append({"day": day, "cap": self.idx, "cat": cat, "tier": tier, "fee": fee, "pos": pos, "side": side, "hs": hs, "ev": ev})
        self.overdue_funnel.append({"cap": cid, "day": day, "with_prev": bool(has_prev), **{k: fun.get(k, 0) for k in ("past_end", "accepting", "no_proposal", "two_sided", "interior_mid", "elig_open_without_end_date")}})
        self.caps.append({"id": cid, "start": start, "day": day, "with_prev": bool(has_prev), "open_binary": n_open, "elig_open_binary": n_elig, "proposed_open_rows": len(cur_prop),
                          "first_seen_proposals_all_categories": sum(1 for p in self.props if p["cap"] == self.idx)})
        # lookups and carried state
        ni = np.frombuffer(ids, dtype=np.int64) if len(ids) else np.empty(0, np.int64)
        nc = np.frombuffer(cats, dtype=np.int8) if len(cats) else np.empty(0, np.int8)
        nt = np.frombuffer(tiers, dtype=np.int8) if len(tiers) else np.empty(0, np.int8)
        allid = np.concatenate([ni, self.lk_ids])
        u_ids, first = np.unique(allid, return_index=True)
        self.lk_cat = np.concatenate([nc, self.lk_cat])[first]
        self.lk_tier = np.concatenate([nt, self.lk_tier])[first]
        self.lk_ids = u_ids
        if len(eids):
            ei = np.frombuffer(eids, dtype=np.int64).copy()
            ef = np.frombuffer(efee, dtype=np.int8).copy()
            o = np.argsort(ei, kind="stable")
            self.fee_by_cap[cid] = (ei[o], ef[o])
        self.prev_ids = np.unique(ni)
        self.prev_t = start
        self.prev_prop = cur_prop
        self.prev_end = cur_end
        self.idx += 1

    # ----------------------------------------------------------------------------------------------------------- lookups used later
    def cat_tier(self, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        n = len(self.lk_ids)
        if not n:
            return np.full(len(q), UNMAPPED, np.int8), np.full(len(q), 4, np.int8)
        pos = np.minimum(np.searchsorted(self.lk_ids, q), n - 1)
        hit = self.lk_ids[pos] == q
        return np.where(hit, self.lk_cat[pos], UNMAPPED).astype(np.int8), np.where(hit, self.lk_tier[pos], 4).astype(np.int8)

    # ----------------------------------------------------------------------------------------------------------- reports
    def full_days(self) -> list[str]:
        per: Counter = Counter()
        for c in self.caps:
            if c["with_prev"]:
                per[c["day"]] += 1
        return sorted(d for d, n in per.items() if n >= 12)

    def report(self, rules: dict, res_log: dict) -> dict:
        full = self.full_days()
        elig = [p for p in self.props if p["cat"] == ELIG_CAT]
        by_day_elig = Counter(p["day"] for p in elig)
        by_day_all = Counter(p["day"] for p in self.props)
        per_cap_elig = Counter(p["cap"] for p in elig)
        caps_with_prev = [i for i, c in enumerate(self.caps) if c["with_prev"]]
        prop = {
            "unit": "first-seen proposal state at k (an open binary row with 'propos' in uma_resolution_statuses at k, none at k - 1, the market present at k - 1); the first covered capture and gap captures have no k - 1 and are unavailable, counted",
            "unavailable_first_seen": dict(self.props_unavail),
            "units_all_categories": len(self.props),
            "units_by_category": {CAT_NAMES[c]: sum(1 for p in self.props if p["cat"] == c) for c in range(4)},
            "per_capture_nonsports_excrypto": dist([per_cap_elig.get(i, 0) for i in caps_with_prev]),
            "per_capture_by_category": {CAT_NAMES[c]: dist([sum(1 for p in self.props if p["cap"] == i and p["cat"] == c) for i in caps_with_prev]) for c in range(4)},
            "per_day_nonsports_excrypto": {d: by_day_elig.get(d, 0) for d in sorted({c["day"] for c in self.caps})},
            "per_day_all_categories": {d: by_day_all.get(d, 0) for d in sorted({c["day"] for c in self.caps})},
            "full_days_used_for_the_line": full,
            "nonsports_excrypto_by_tier": {TIER_NAMES[t]: sum(1 for p in elig if p["tier"] == t) for t in range(5)},
            "nonsports_excrypto_by_ladder_position": dict(Counter(p["pos"] for p in elig)),
            "nonsports_excrypto_by_tier_x_ladder_position": {f"{TIER_NAMES[t]}/{pos}": n for (t, pos), n in sorted(Counter((p["tier"], p["pos"]) for p in elig).items())},
            "nonsports_excrypto_by_fee_class": {("fee_free", "fee_on", "unknown")[f]: sum(1 for p in elig if p["fee"] == f) for f in range(3)},
            "nonsports_excrypto_side_readability": dict(Counter(p["side"] for p in elig)),
            "nonsports_excrypto_half_spread_at_k": dist([p["hs"] for p in elig if p["hs"] == p["hs"]]),
            "readable_side_note": "the status field does not name the proposed side; readable = two-sided with the favoured side's mid >= 0.90 at k (the pinned reading of the CH263 text)",
        }
        # seen share against the label store's daily counts (a lagged read, counts only)
        days = sorted({c["day"] for c in self.caps})
        seen = {}
        for mid, (t, cat) in self.first_prop.items():
            seen[mid] = (t, cat)
        res_days: dict = {}
        for d in days:
            row = Counter()
            for mid, ct in res_log.get("by_day", {}).get(d, []):
                cat = self._cat_of(mid)
                row[f"{CAT_NAMES[cat]}"] += 1
                if cat == ELIG_CAT:
                    s = seen.get(mid)
                    if s is not None and ct is not None and s[0] < ct:
                        row["nonsports_excrypto_proposal_seen_before_close"] += 1
            res_days[d] = dict(row)
        prop["label_store_resolutions_by_closed_day"] = {"note": "markets of the engine's resolution logs (its res_7d candidates, NOT every venue resolution) by closed_time day and category lookup; 'proposal_seen_before_close' = a first-seen proposal state at an earlier covered capture; a lagged read", "days": res_days}
        m1 = median_of([by_day_elig.get(d, 0) for d in full])
        prop["median_per_full_day_nonsports_excrypto"] = m1
        # CH264
        od = self.overdue_units
        oi_have = [u for u in od if u["oi"] == u["oi"]]
        key_name = "open_interest" if oi_have and len(oi_have) >= 0.5 * max(1, len(od)) else "liquidity_proxy"
        vals = [u["oi"] if key_name == "open_interest" else u["liq"] for u in od]
        finite = sorted(v for v in vals if v == v)
        cuts = (finite[len(finite) // 3], finite[2 * len(finite) // 3]) if len(finite) >= 3 else (math.nan, math.nan)

        def terc(v):
            return "na" if v != v else "low" if v < cuts[0] else "mid" if v < cuts[1] else "high"

        cls = rules["classes"]
        by_day_od = Counter(u["day"] for u in od)
        over = {
            "unit": "ELIG market at the first covered capture (not the first) where it is >= 2 h past end_date, accepting_orders true, no proposal state, two-sided, mid in [0.05, 0.95]; entries more than 24 h past end_date are 'late' and reported apart; the first covered capture is a warm-up (its entrants are not counted)",
            "units_fresh": len(od),
            "units_late_entrants_over_24h": len(self.overdue_late),
            "per_day": {d: by_day_od.get(d, 0) for d in days},
            "full_days_used_for_the_line": full,
            "median_per_full_day": median_of([by_day_od.get(d, 0) for d in full]),
            "funnel_per_capture": {k: dist([f[k] for f in self.overdue_funnel if f["with_prev"]]) for k in ("past_end", "accepting", "no_proposal", "two_sided", "interior_mid")},
            "stock_interior_overdue_per_capture": dist([f["interior_mid"] for f in self.overdue_funnel if f["with_prev"]]),
            "tercile_variable": key_name,
            "open_interest_presence": {"sidecar_rows": self.ext_rows, "non_empty": self.oi_nonempty, "share": (self.oi_nonempty / self.ext_rows) if self.ext_rows else None, "units_with_open_interest": len(oi_have)},
            "tercile_cuts_census_fixed": list(cuts),
            "units_by_tercile": dict(Counter(terc(v) for v in vals)),
            "units_by_rule_class": dict(Counter(cls.get(u["mid"], "no_rules") for u in od)),
            "classed_share": (sum(1 for u in od if cls.get(u["mid"], "no_rules") in ("scheduled", "barrier")) / len(od)) if od else None,
            "units_by_tercile_x_rule_class": {f"{t}/{c}": n for (t, c), n in sorted(Counter((terc(v), cls.get(u["mid"], "no_rules")) for u, v in zip(od, vals, strict=True)).items())},
            "end_date_moved_share": (sum(1 for u in od if u["moved"]) / len(od)) if od else None,
            "age_h_past_end_at_entry": dist([u["age_h"] for u in od]),
            "ev_distinct": len({u["ev"] for u in od}),
        }
        # CH267
        t_first = self.caps[0]["start"] if self.caps else math.nan
        t_last = self.caps[-1]["start"] if self.caps else math.nan
        cl_days = []
        if self.caps:
            d0 = datetime.fromtimestamp(t_first + CLOSE_WIN_S, UTC).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() + 86400.0
            d = d0
            while d + 86400.0 <= t_last:
                cl_days.append(c240.day_of(d))
                d += 86400.0
        closes = []
        for mid, (end, tier, ev, _fee, s4, s2) in self.closing.items():
            fp = self.first_prop.get(mid)
            closes.append({"mid": mid, "day": c240.day_of(end), "tier": tier, "ev": ev, "usable": bool(s4 and s2), "moved": mid in self.moved, "early": fp is not None and fp[0] < end, "cls": cls.get(mid, "no_rules")})
        for c in closes:
            c["use"] = c["usable"] and not c["moved"] and not c["early"]
        fd = set(cl_days)
        inday = [c for c in closes if c["day"] in fd]
        by_day_all_c = Counter(c["day"] for c in inday)
        by_day_sched = Counter(c["day"] for c in inday if c["use"] and c["cls"] == "scheduled")
        by_day_sched_raw = Counter(c["day"] for c in inday if c["cls"] == "scheduled")
        clos = {
            "unit": "ELIG market seen open within 5 h of its end_date (a close); usable = two-sided at the capture 3-5 h and at the capture 1-3 h before end_date, end_date unchanged across the covered captures, no proposal state before the close; availability only, no spread is read",
            "days_with_full_coverage": cl_days,
            "closes_seen_total": len(closes),
            "closes_per_full_day": {d: by_day_all_c.get(d, 0) for d in cl_days},
            "closes_per_full_day_dist": dist([by_day_all_c.get(d, 0) for d in cl_days]),
            "usable_share": (sum(1 for c in inday if c["use"]) / len(inday)) if inday else None,
            "components": {"two_sided_at_both": sum(1 for c in inday if c["usable"]), "end_date_moved": sum(1 for c in inday if c["moved"]), "decided_early": sum(1 for c in inday if c["early"])},
            "classed_share_of_all_closes": (sum(1 for c in inday if c["cls"] in ("scheduled", "barrier")) / len(inday)) if inday else None,
            "classed_share_of_usable_closes": (sum(1 for c in inday if c["use"] and c["cls"] in ("scheduled", "barrier")) / max(1, sum(1 for c in inday if c["use"]))) if inday else None,
            "classed_share_by_tier": {TIER_NAMES[t]: _share([c for c in inday if c["tier"] == t], lambda c: c["cls"] in ("scheduled", "barrier")) for t in range(5)},
            "class_split_all_closes": dict(Counter(c["cls"] for c in inday)),
            "class_split_usable_closes": dict(Counter(c["cls"] for c in inday if c["use"])),
            "decided_early_by_class": dict(Counter(c["cls"] for c in inday if c["early"])),
            "scheduled_class_usable_closes_per_full_day": {d: by_day_sched.get(d, 0) for d in cl_days},
            "scheduled_class_all_closes_per_full_day": {d: by_day_sched_raw.get(d, 0) for d in cl_days},
            "median_scheduled_usable_per_full_day": median_of([by_day_sched.get(d, 0) for d in cl_days]),
            "closes_strata_tier_x_class": {f"{TIER_NAMES[t]}/{k}": n for (t, k), n in sorted(Counter((c["tier"], c["cls"]) for c in inday if c["use"]).items())},
            "events_distinct_among_usable": len({c["ev"] for c in inday if c["use"]}),
        }
        return {"proposals_ch263": prop, "overdue_ch264": over, "closes_ch267": clos}

    def _cat_of(self, mid: int) -> int:
        c, _ = self.cat_tier(np.array([mid], np.int64))
        return int(c[0])


def _share(lst: list, f) -> float | None:
    return (sum(1 for x in lst if f(x)) / len(lst)) if lst else None


def read_resolution_log(engine: Path) -> dict:
    """The engine's label store for resolutions: the latest record per market, read-only. {records, by_day: {closed day: [(mid, closed_ts)]}, resolved: arrays}"""
    latest: dict = {}
    files = sorted((Path(engine) / "logs").glob("resolutions-*.jsonl"))
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    mid = int(d["market_id"])
                except (ValueError, KeyError, TypeError):
                    continue
                latest[mid] = (d.get("state"), d.get("y"), d.get("closed_time"), str(d.get("fetched_utc", "")))
    by_day: dict = {}
    res_ids, res_y, res_ct = [], [], []
    for mid, (state, y, ct, _ft) in latest.items():
        cts = c240.parse_utc(str(ct).replace(" ", "T")) if ct else math.nan
        if state == "resolved" and cts == cts:
            by_day.setdefault(c240.day_of(cts), []).append((mid, cts))
        if state == "resolved" and y in (0, 1):
            res_ids.append(mid)
            res_y.append(int(y))
            res_ct.append(cts)
    o = np.argsort(np.array(res_ids, np.int64), kind="stable") if res_ids else np.empty(0, np.int64)
    return {"files": [f.name for f in files], "records": len(latest), "states": dict(Counter(v[0] for v in latest.values())), "by_day": by_day,
            "ids": np.array(res_ids, np.int64)[o], "y": np.array(res_y, np.int8)[o], "closed_ts": np.array(res_ct, np.float64)[o]}


# --------------------------------------------------------------------------------------------------------------- engine pass (quotes / features / predictions)


def _look(ids_sorted: np.ndarray, q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(ids_sorted)
    if not n:
        return np.zeros(len(q), np.int64), np.zeros(len(q), bool)
    pos = np.minimum(np.searchsorted(ids_sorted, q), n - 1)
    return pos, ids_sorted[pos] == q


class Frame:
    __slots__ = ("slot", "t", "ids", "mid", "st", "bid", "ask")

    def __init__(self, slot, t, ids, mid, st, bid, ask):
        self.slot, self.t, self.ids, self.mid, self.st, self.bid, self.ask = slot, t, ids, mid, st, bid, ask


def read_quotes(path: Path, slot: int, t: float) -> Frame:
    tb = pq.read_table(path, columns=["market_id", "bid", "ask", "st"])
    ids = tb.column("market_id").to_numpy().astype(np.int64)
    bid = tb.column("bid").to_numpy(zero_copy_only=False).astype(np.float32)
    ask = tb.column("ask").to_numpy(zero_copy_only=False).astype(np.float32)
    st = tb.column("st").to_numpy().astype(np.int8)
    o = np.argsort(ids, kind="stable")
    ids, bid, ask, st = ids[o], bid[o], ask[o], st[o]
    mid = np.where(st == 0, (bid.astype(np.float64) + ask.astype(np.float64)) / 2.0, np.nan).astype(np.float32)
    return Frame(slot, t, ids, mid, st, bid, ask)


def list_captures(directory: Path, pattern: str, strip: str) -> dict:
    out = {}
    if Path(directory).exists():
        for p in sorted(Path(directory).glob(pattern)):
            cid = p.name.removesuffix(strip) if strip else p.name
            t = cap_time(cid)
            if t == t:
                out[cid] = (t, p)
    return out


def missing_slots(have: dict, lo: float, hi: float) -> dict:
    slots = {slot_of(t) for t, _p in have.values() if lo <= t <= hi}
    if not slots:
        return {"present": 0, "expected": 0, "missing": 0, "missing_slots_utc": []}
    a, b = min(slots), max(slots)
    miss = [s for s in range(a, b + 1) if s not in slots]
    return {"present": len(slots), "expected": b - a + 1, "missing": len(miss), "missing_slots_utc": [datetime.fromtimestamp(GRID0 + s * GRID_S, UTC).strftime("%Y-%m-%dT%H:%MZ") for s in miss[:200]]}


class EnginePass:
    def __init__(self, side: SidecarPass, res: dict, elig_cats: tuple = ("sports", "crypto", "unknown")) -> None:
        self.side = side
        self.res = res
        self.excl = set(elig_cats)
        self.frames: deque = deque(maxlen=13)
        self.notes: Counter = Counter()
        # CH266 sketch
        self.cross_seen = {"display": set(), "placebo": set()}
        self.cross_units: list[dict] = []
        self.cross_pending: list = []
        self.cross_all: Counter = Counter()
        self.zone_hs: Counter = Counter()
        self.zone_rows: list[int] = []
        self.q_days_full: Counter = Counter()
        # CH266 map
        n = len(res["ids"]) if res else 0
        self.r_last = np.full(n, np.nan, np.float32)
        self.r_cut = np.full(n, np.nan, np.float32)
        self.r_cut_ts = (res["closed_ts"] - 86400.0) if n else np.empty(0)
        # CH262
        self.top_counts: list[dict] = []
        self.top_pending: dict | None = None
        self.unav_acc: Counter = Counter()
        self.runs: dict = {}
        self.run_lengths: Counter = Counter()
        self.prev_top_slot = None
        self.top_markets: set = set()
        self.top_events_by_tier: dict = {}
        # CH265
        self.pred_prev: dict | None = None
        self.r_prev: dict | None = None
        self.s_lag = [0.0] * 6
        self.s_mo = [0.0] * 6
        self.s_lag_el = [0.0] * 6
        self.s_mo_el = [0.0] * 6
        self.resid_stats = {"origins": 0, "labelled": 0}
        # CH268
        self.fr_hist_all: Counter = Counter()
        self.fr_hist_el: Counter = Counter()
        self.fr_corr_all = [0.0] * 6
        self.fr_corr_el = [0.0] * 6
        self.fr_gt25_el = 0
        self.fr_rows_total = 0
        self.fr_rows_skipped_history = 0

    def process(self, cid: str, t: float, qpath: Path, fpath: Path | None, ppath: Path | None, model_path_ok: bool, in_pred_window: bool, in_feat_window: bool) -> None:
        slot = slot_of(t)
        cur = read_quotes(qpath, slot, t)
        prev = self.frames[-1] if self.frames and self.frames[-1].slot == slot - 1 else None
        day = c240.day_of(t)
        if prev is not None:
            self.q_days_full[day] += 1
        self._pending(cur, prev)
        if prev is not None:
            self._crossings(cur, prev, day)
        self._label_store(cur)
        feats = self._read_features(fpath) if (fpath is not None and (in_feat_window or in_pred_window)) else None
        if feats is not None and in_feat_window:
            self._fr12(cur, feats)
        pred = None
        if feats is not None and in_pred_window and ppath is not None and model_path_ok:
            pred = self._read_pred(ppath, feats)
        self._residual(cur, prev, pred, feats, slot)
        if pred is not None:
            self._top_decile(cid, cur, feats, pred, slot, day)
        self.frames.append(cur)

    # ------------------------------------------------------------------------------------------------------- readers
    def _read_features(self, p: Path) -> dict | None:
        try:
            tb = pq.read_table(p, columns=["market_id", "category", "ms_log_liq", "mo_chg_1d"])
        except Exception:  # noqa: BLE001
            self.notes["features_unreadable"] += 1
            return None
        cat = tb.column("category").to_pylist()
        return {"ids": tb.column("market_id").to_numpy().astype(np.int64), "elig_cat": np.array([c not in self.excl for c in cat], bool), "cat": cat,
                "log_liq": tb.column("ms_log_liq").to_numpy(zero_copy_only=False).astype(np.float64), "chg1d": tb.column("mo_chg_1d").to_numpy(zero_copy_only=False).astype(np.float64)}

    def _read_pred(self, p: Path, feats: dict) -> dict | None:
        tb = pq.read_table(p, columns=["elig", "dir_2h_dn", "dir_2h_up"])
        if tb.num_rows != len(feats["ids"]):
            self.notes["predictions_not_aligned_with_features"] += 1
            return None
        el = tb.column("elig").to_numpy().astype(np.uint8)
        dn = tb.column("dir_2h_dn").to_numpy().astype(np.float64) / Q16
        up = tb.column("dir_2h_up").to_numpy().astype(np.float64) / Q16
        return {"elig": el, "s": up - dn, "bit": (el & 1) > 0}

    # ------------------------------------------------------------------------------------------------------- pending (k + 1 status only)
    def _pending(self, cur: Frame, prev: Frame | None) -> None:
        pend = self.top_pending
        self.top_pending = None
        if pend is not None and pend["slot"] == cur.slot - 1:
            for grp, ids, tiers in (("top", pend["top_ids"], pend["top_tier"]), ("rest", pend["rest_ids"], pend["rest_tier"])):
                pos, hit = _look(cur.ids, ids)
                ok = hit & (cur.st[pos] == 0)
                for t in range(4):
                    m = tiers == t
                    self.unav_acc[(grp, t, "n")] += int(m.sum())
                    self.unav_acc[(grp, t, "unavailable")] += int((m & ~ok).sum())
        elif pend is not None:
            self.notes["top_decile_without_k_plus_1_capture"] += 1
        cp = self.cross_pending
        self.cross_pending = []
        for u, slot0 in cp:
            if slot0 == cur.slot - 1:
                pos, hit = _look(cur.ids, np.array([u["mid"]], np.int64))
                u["two_sided_k1"] = bool(hit[0] and cur.st[pos[0]] == 0)
            else:
                u["two_sided_k1"] = None

    # ------------------------------------------------------------------------------------------------------- CH266 sketch
    def _crossings(self, cur: Frame, prev: Frame, day: str) -> None:
        pos, hit = _look(prev.ids, cur.ids)
        mp = prev.mid[pos].astype(np.float64)
        mc = cur.mid.astype(np.float64)
        ok = hit & np.isfinite(mp) & np.isfinite(mc)
        disp = ok & (mp >= DISPLAY - EPS) & (mc < DISPLAY - EPS)
        plc = ok & (mp >= PLACEBO - EPS) & (mc < PLACEBO - EPS) & ~disp
        cats, tiers = self.side.cat_tier(cur.ids)
        half = (cur.ask.astype(np.float64) - cur.bid.astype(np.float64)) / 2.0
        zone = np.isfinite(mc) & (mc < 0.02)
        self.zone_rows.append(int(zone.sum()))
        for h in half[zone & (cats == ELIG_CAT)]:
            self.zone_hs[int(round(h * 10000))] += 1
        for name, m in (("display", disp), ("placebo", plc)):
            for i in np.nonzero(m)[0]:
                mid = int(cur.ids[i])
                c, tr = int(cats[i]), int(tiers[i])
                self.cross_all[(name, day, c)] += 1
                if mid in self.cross_seen[name]:
                    continue
                self.cross_seen[name].add(mid)
                u = {"mid": mid, "name": name, "day": day, "cat": c, "tier": tr, "hs": float(half[i]), "two_sided_k1": None}
                self.cross_units.append(u)
                self.cross_pending.append((u, cur.slot))

    # ------------------------------------------------------------------------------------------------------- CH266 map (label store frame)
    def _label_store(self, cur: Frame) -> None:
        ids = self.res["ids"] if self.res else np.empty(0, np.int64)
        if not len(ids):
            return
        rpos, rhit = _look(cur.ids, ids)
        ok = rhit & (cur.st[rpos] == 0)
        mid = cur.mid[rpos]
        self.r_last = np.where(ok, mid, self.r_last)
        late = ok & (cur.t <= self.r_cut_ts)
        self.r_cut = np.where(late, mid, self.r_cut)

    # ------------------------------------------------------------------------------------------------------- CH268
    def _fr12(self, cur: Frame, feats: dict) -> None:
        hist = list(self.frames)[-12:]
        self.fr_rows_total += len(feats["ids"])
        if len(hist) < 12 or [f.slot for f in hist] != list(range(cur.slot - 12, cur.slot)):
            self.fr_rows_skipped_history += len(feats["ids"])
            return
        unav = np.zeros(len(feats["ids"]), np.int16)
        for f in hist:
            pos, hit = _look(f.ids, feats["ids"])
            unav += (~(hit & (f.st[pos] == 0))).astype(np.int16)
        ll = feats["log_liq"]
        el = feats["elig_cat"]
        self.fr_hist_all.update(unav.tolist())
        self.fr_hist_el.update(unav[el].tolist())
        fr = unav / 12.0
        acc_pairs(self.fr_corr_all, fr, ll)
        acc_pairs(self.fr_corr_el, fr[el], ll[el])
        self.fr_gt25_el += int(((fr > 0.25) & el).sum())

    # ------------------------------------------------------------------------------------------------------- CH265
    def _residual(self, cur: Frame, prev: Frame | None, pred: dict | None, feats: dict | None, slot: int) -> None:
        pp = self.pred_prev
        if pp is not None and prev is not None and pp["slot"] == slot - 1:
            pos_c, hit_c = _look(cur.ids, pp["ids"])
            pos_p, hit_p = _look(prev.ids, pp["ids"])
            mc = cur.mid[pos_c].astype(np.float64)
            mp = prev.mid[pos_p].astype(np.float64)
            ok = pp["bit"] & hit_c & hit_p & np.isfinite(mc) & np.isfinite(mp)
            d = mc - mp
            y = np.where(d < -DIR_DELTA - DIR_TOL, -1.0, np.where(d > DIR_DELTA + DIR_TOL, 1.0, 0.0))
            r = np.where(ok, y - pp["s"], np.nan)
            self.resid_stats["origins"] += 1
            self.resid_stats["labelled"] += int(ok.sum())
            for acc_m, mask in ((self.s_mo, np.ones(len(r), bool)), (self.s_mo_el, pp["elig_cat"])):
                acc_pairs(acc_m, r[mask], pp["chg1d"][mask])
            rp = self.r_prev
            if rp is not None and rp["slot"] == slot - 2:
                o = np.argsort(rp["ids"])
                ids_s, r_s = rp["ids"][o], rp["r"][o]
                pos, hit = _look(ids_s, pp["ids"])
                prior = np.where(hit, r_s[pos], np.nan)
                acc_pairs(self.s_lag, r, prior)
                acc_pairs(self.s_lag_el, r[pp["elig_cat"]], prior[pp["elig_cat"]])
            self.r_prev = {"slot": slot - 1, "ids": pp["ids"], "r": r}
        else:
            self.r_prev = None
        if pred is not None and feats is not None:
            self.pred_prev = {"slot": slot, "ids": feats["ids"], "s": pred["s"], "bit": pred["bit"], "chg1d": feats["chg1d"], "elig_cat": feats["elig_cat"]}
        else:
            self.pred_prev = None

    # ------------------------------------------------------------------------------------------------------- CH262
    def _top_decile(self, cid: str, cur: Frame, feats: dict, pred: dict, slot: int, day: str) -> None:
        m = pred["bit"] & feats["elig_cat"]
        idx = np.nonzero(m)[0]
        n = len(idx)
        if n == 0:
            return
        top_n = int(math.ceil(n / 10.0))
        order = np.argsort(-pred["s"][idx], kind="stable")
        top_idx, rest_idx = idx[order[:top_n]], idx[order[top_n:]]
        tier = np.array([tier_of(math.expm1(v)) if v == v else 4 for v in feats["log_liq"]], np.int8)
        fee_ids, fee_codes = self.side.fee_by_cap.get(cid, (None, None))
        row = {"cap": cid, "day": day, "eligible_rows": n, "top_n": top_n, "by_tier": {TIER_NAMES[t]: int((tier[top_idx] == t).sum()) for t in range(5)}}
        if fee_ids is not None:
            pos, hit = _look(fee_ids, feats["ids"][top_idx])
            code = np.where(hit, fee_codes[pos], 3)
            row["by_fee_class"] = {("fee_free", "fee_on", "unknown", "fee_na")[k]: int((code == k).sum()) for k in range(4)}
            row["by_tier_x_fee_class"] = {f"{TIER_NAMES[t]}/{('fee_free', 'fee_on', 'unknown', 'fee_na')[k]}": int(((tier[top_idx] == t) & (code == k)).sum()) for t in range(4) for k in range(4) if int(((tier[top_idx] == t) & (code == k)).sum())}
        else:
            row["by_fee_class"] = {"fee_na": top_n}
        self.top_counts.append(row)
        ids_top = feats["ids"][top_idx]
        self.top_markets.update(ids_top.tolist())
        # tenure (consecutive captures in the top decile)
        consec = self.prev_top_slot == slot - 1
        new_runs = {}
        cur_set = set(ids_top.tolist())
        for mid in cur_set:
            new_runs[mid] = (self.runs.get(mid, 0) if consec else 0) + 1
        for mid, ln in self.runs.items():
            if mid not in new_runs:
                self.run_lengths[ln] += 1
        self.runs = new_runs
        self.prev_top_slot = slot
        self.top_pending = {"slot": slot, "top_ids": ids_top, "top_tier": tier[top_idx], "rest_ids": feats["ids"][rest_idx], "rest_tier": tier[rest_idx]}

    # ------------------------------------------------------------------------------------------------------- report
    def report(self, q_have: dict, p_have: dict, f_have: dict, windows: dict) -> dict:
        side = self.side
        full_q = sorted(d for d, n in self.q_days_full.items() if n >= 12)
        # CH266 sketch
        disp = [u for u in self.cross_units if u["name"] == "display"]
        plc = [u for u in self.cross_units if u["name"] == "placebo"]

        def per_day(units, cat=None):
            c = Counter(u["day"] for u in units if cat is None or u["cat"] == cat)
            return {d: c.get(d, 0) for d in sorted(self.q_days_full)}

        def breakdown(units):
            return {f"{CAT_NAMES[c]}/{TIER_NAMES[t]}": n for (c, t), n in sorted(Counter((u["cat"], u["tier"]) for u in units).items())}

        hs_ticks = self.zone_hs
        hs_tot = sum(hs_ticks.values())
        cs = {
            "unit": "first downward crossing per market (mid_{k-1} >= 0.010 > mid_k display; >= 0.015 > mid_k placebo, not also display) over consecutive quotes frames, two-sided at k - 1 and k; category and tier are the latest-sidecar lookup (unmapped counted); k + 1 status read only for 'two_sided at k + 1'; no proposal condition (quotes carry none)",
            "days_with_all_12_slots": full_q,
            "display_units_nonsports_excrypto_per_day": per_day(disp, ELIG_CAT),
            "display_units_all_categories_per_day": per_day(disp),
            "placebo_units_nonsports_excrypto_per_day": per_day(plc, ELIG_CAT),
            "display_median_per_full_day_nonsports_excrypto": median_of([per_day(disp, ELIG_CAT).get(d, 0) for d in full_q]),
            "display_units_by_category_tier": breakdown(disp),
            "placebo_units_by_category_tier": breakdown(plc),
            "display_total_downward_crossings_incl_repeats": sum(n for (k, _d, _c), n in self.cross_all.items() if k == "display"),
            "display_units_two_sided_at_k_plus_1_share": _share([u for u in disp if u["two_sided_k1"] is not None], lambda u: u["two_sided_k1"]),
            "display_units_without_k_plus_1_capture": sum(1 for u in disp if u["two_sided_k1"] is None),
            "display_units_half_spread_at_k": dist([u["hs"] for u in disp if u["cat"] == ELIG_CAT]),
            "zone_rows_mid_below_0.02_two_sided_per_frame": dist(self.zone_rows),
            "zone_half_spread_nonsports_excrypto_hist_units_0.01c": {str(k): n for k, n in sorted(hs_ticks.items())[:40]},
            "zone_half_spread_nonsports_excrypto_rows": hs_tot,
        }
        # CH266 map
        r = self.res
        tabs = {}
        if r and len(r["ids"]):
            cats, _t = side.cat_tier(r["ids"])
            for arm, arr in (("last_two_sided_quote_any", self.r_last), ("last_two_sided_quote_at_least_24h_before_close", self.r_cut)):
                have = np.isfinite(arr)
                grp: dict = {}
                for g, gm in (("nonsports_excrypto", cats == ELIG_CAT), ("sports", cats == 0), ("crypto", cats == 1), ("other_or_unmapped", (cats == 3) | (cats == UNMAPPED))):
                    sel = have & gm
                    p = arr[sel].astype(np.float64)
                    y = r["y"][sel]
                    bins: dict = {}
                    for lo_edge, hi_edge in ((0.0, 0.03), (0.97, 1.0)):
                        mk = (p >= lo_edge - EPS) & (p < hi_edge - EPS) if hi_edge < 1 else (p >= lo_edge - EPS)
                        k = np.floor(p[mk] / 0.001 + 1e-9).astype(int)
                        for b in sorted(set(k.tolist())):
                            nn = int((k == b).sum())
                            ww = int(y[mk][k == b].sum())
                            lo, hi = wilson(ww, nn)
                            bins[f"{b / 10:.1f}c-{(b + 1) / 10:.1f}c"] = {"n": nn, "wins": ww, "rate": ww / nn, "ci_lo": lo, "ci_hi": hi}
                    grp[g] = {"n_with_quote": int(sel.sum()), "bins_0.1c": bins}
                tabs[arm] = {"resolved_with_label_and_quote": int(have.sum()), "groups": grp}
        lbl = {
            "unit": "markets of the engine's resolution logs with state resolved and y in {0, 1} (the label store's own frame); the price is the market's last two-sided quote in quotes/ (arm 1) or its last two-sided quote at least 24 h before the logged closed_time (arm 2); win rate = share y = 1 (YES won); Wilson 95% CIs; no new resolution is read",
            "label_store_records": r["records"] if r else 0,
            "label_store_states": r["states"] if r else {},
            "label_store_resolved_with_y": int(len(r["ids"])) if r else 0,
            "resolved_without_any_two_sided_quote_in_window": int(len(r["ids"]) - int(np.isfinite(self.r_last).sum())) if r else 0,
            "arms": tabs,
        }
        # CH262
        tc = self.top_counts
        tier_names = TIER_NAMES[:4]
        per_tier = {t: dist([row["by_tier"][t] for row in tc]) for t in tier_names}
        unav = {}
        for grp in ("top", "rest"):
            unav[grp] = {TIER_NAMES[t]: {"n": self.unav_acc[(grp, t, "n")], "unavailable": self.unav_acc[(grp, t, "unavailable")], "share": (self.unav_acc[(grp, t, "unavailable")] / self.unav_acc[(grp, t, "n")]) if self.unav_acc[(grp, t, "n")] else None} for t in range(4)}
        allruns = Counter(self.run_lengths)
        open_runs = Counter(self.runs.values())
        ch262 = {
            "unit": "the pinned champion's dir_2h score s = P(up) - P(down) from predictions/<capture>/<model>.parquet (write-once uint16 / 65535), top decile by score among engine-eligible rows (elig bit 1) of the non-sports ex-crypto categories (the engine's category not in sports / crypto / unknown); tier = expm1(ms_log_liq); no mid after an origin is read; the k + 1 'unavailable' share reads quotes status codes only (status != 0 or absent)",
            "captures": len(tc),
            "eligible_rows_per_capture": dist([row["eligible_rows"] for row in tc]),
            "top_decile_units_per_capture": dist([row["top_n"] for row in tc]),
            "top_decile_units_per_capture_by_tier": per_tier,
            "fee_class_split_totals": dict(Counter({k: v for row in tc for k, v in row.get("by_fee_class", {}).items()})),
            "fee_class_split_by_tier_totals": dict(Counter({k: v for row in tc for k, v in row.get("by_tier_x_fee_class", {}).items()})),
            "distinct_markets_in_a_top_decile_over_window": len(self.top_markets),
            "tenure_completed_runs_captures": {str(k): v for k, v in sorted(allruns.items())},
            "tenure_open_runs_at_window_end_captures": {str(k): v for k, v in sorted(open_runs.items())},
            "unavailable_at_k_plus_1_top_vs_rest_by_tier": unav,
            "unavailable_gap_top_minus_rest_points_by_tier": {t: ((unav["top"][t]["share"] - unav["rest"][t]["share"]) * 100.0) if unav["top"][t]["share"] is not None and unav["rest"][t]["share"] is not None else None for t in (TIER_NAMES[i] for i in range(4))},
            "per_capture_rows": [{"cap": row["cap"], "top_n": row["top_n"], "by_tier": row["by_tier"]} for row in tc],
        }
        med_10_100 = per_tier["10k-100k"].get("median")
        # CH265 / CH268
        ch265 = {
            "unit": "residual r = y - (P(up) - P(down)) of the champion's dir_2h on labelled origins (y in {-1, 0, +1} from the engine's direction frame: |dmid| <= 0.005 flat, quote mids at the origin and the next slot); lag-1 pairs are the same market at consecutive origins; correlation with mo_chg_1d at the origin; Pearson",
            "origins": self.resid_stats["origins"], "labelled_rows": self.resid_stats["labelled"],
            "lag1_autocorrelation_all_eligible": pearson(self.s_lag), "lag1_pairs_all": int(self.s_lag[0]),
            "corr_with_mo_chg_1d_all_eligible": pearson(self.s_mo), "pairs_mo_all": int(self.s_mo[0]),
            "lag1_autocorrelation_nonsports_excrypto": pearson(self.s_lag_el), "lag1_pairs_nonsports_excrypto": int(self.s_lag_el[0]),
            "corr_with_mo_chg_1d_nonsports_excrypto": pearson(self.s_mo_el), "pairs_mo_nonsports_excrypto": int(self.s_mo_el[0]),
        }
        tot_el = sum(self.fr_hist_el.values())
        tot_all = sum(self.fr_hist_all.values())
        ch268 = {
            "unit": "fr_unavail_12 = share of the 12 previous slots in which the market's quotes status was not 0 or the market was absent from the frame (needs all 12 previous frames present; else the capture's rows are skipped, counted)",
            "rows_total": self.fr_rows_total, "rows_skipped_incomplete_history": self.fr_rows_skipped_history,
            "rows_used_all_eligible": tot_all, "rows_used_nonsports_excrypto": tot_el,
            "histogram_unavailable_slots_of_12_all_eligible": {str(k): v for k, v in sorted(self.fr_hist_all.items())},
            "histogram_unavailable_slots_of_12_nonsports_excrypto": {str(k): v for k, v in sorted(self.fr_hist_el.items())},
            "share_positive_all_eligible": (1 - self.fr_hist_all.get(0, 0) / tot_all) if tot_all else None,
            "share_positive_nonsports_excrypto": (1 - self.fr_hist_el.get(0, 0) / tot_el) if tot_el else None,
            "share_above_0.25_nonsports_excrypto": (self.fr_gt25_el / tot_el) if tot_el else None,
            "corr_with_log1p_liquidity_all_eligible": pearson(self.fr_corr_all),
            "corr_with_log1p_liquidity_nonsports_excrypto": pearson(self.fr_corr_el),
        }
        return {"captures_engine": {"quotes": missing_slots(q_have, *windows["quotes"]), "features": missing_slots(f_have, *windows["features"]), "predictions": missing_slots(p_have, *windows["predictions"])},
                "tails_ch266_sketch_crossings": cs, "tails_ch266_map_label_store": lbl, "champion_top_decile_ch262": ch262, "residual_ch265": ch265, "fragile_ch268": ch268,
                "_median_top_decile_10k_100k": med_10_100, "_notes": dict(self.notes)}


# --------------------------------------------------------------------------------------------------------------- orchestration


def run_map(snapshot_roots: list[Path], engine_root: Path, rules_root: Path, start_utc: str, end_utc: str, quote_days: int, pred_days: int, champion: str) -> dict:
    caps = c240.discover(snapshot_roots, start_utc, end_utc)
    t0, t1 = c240.parse_utc(start_utc), c240.parse_utc(end_utc)
    inputs: list[dict] = []
    rules = read_rules(rules_root)
    side = SidecarPass()
    for c in caps:
        d = Path(c["dir"])
        ext_p = d / "rows_ext.csv.gz"
        for f in [d / "manifest.json", d / "rows.csv.gz"] + ([ext_p] if ext_p.exists() else []):
            inputs.append({"path": str(f), "bytes": f.stat().st_size, "sha256": sha256_file(f)})
        side.feed(c["id"], c["start"], d / "rows.csv.gz", ext_p if ext_p.exists() else None)
    gaps = []
    starts = [c["start"] for c in caps]
    edges = [t0 - GRID_S / 2, *starts, t1 - GRID_S / 2 + 1]
    for a, z in zip(edges, edges[1:], strict=False):
        if z - a > GAP_MAX_S:
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            gaps.append({"after": datetime.fromtimestamp(a, UTC).strftime(fmt), "before": datetime.fromtimestamp(z, UTC).strftime(fmt), "hours": round((z - a) / 3600, 2)})
    res = read_resolution_log(engine_root)
    for f in res["files"]:
        p = Path(engine_root) / "logs" / f
        inputs.append({"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    eng = EnginePass(side, res)
    q_have = list_captures(Path(engine_root) / "quotes", "*.parquet", ".parquet")
    f_have = list_captures(Path(engine_root) / "features", "*.parquet", ".parquet")
    p_have = {}
    if (Path(engine_root) / "predictions").exists():
        for x in sorted((Path(engine_root) / "predictions").glob("*")):
            if x.is_dir() and cap_time(x.name) == cap_time(x.name):
                p_have[x.name] = (cap_time(x.name), x)
    t_hi = max((t for t, _ in q_have.values()), default=math.nan)
    wins = {"quotes": (t_hi - quote_days * 86400.0, t_hi), "features": (t_hi - quote_days * 86400.0, t_hi), "predictions": (t_hi - pred_days * 86400.0, t_hi)}
    for cid, (t, qp) in sorted(q_have.items(), key=lambda kv: kv[1][0]):
        if not (wins["quotes"][0] <= t <= t_hi):
            continue
        fp = f_have.get(cid, (None, None))[1]
        pp_dir = p_have.get(cid, (None, None))[1]
        pp = (pp_dir / f"{champion}.parquet") if pp_dir is not None else None
        ok_model = pp is not None and pp.exists()
        in_pred = wins["predictions"][0] <= t <= t_hi
        for f in (qp, fp, pp if (ok_model and in_pred) else None):
            if f is not None:
                inputs.append({"path": str(f), "bytes": f.stat().st_size, "sha256": sha256_file(f)})
        eng.process(cid, t, qp, fp, pp, ok_model, in_pred, True)
    er = eng.report(q_have, p_have, f_have, wins)
    sr = side.report(rules, res)
    med_top = er.pop("_median_top_decile_10k_100k")
    notes = er.pop("_notes")
    decisions = {
        "lines": LINES,
        "lt14_ch262": {"median_top_decile_units_10k_100k_per_capture": med_top, "drafted": (med_top is not None and med_top >= 100), "unavailable_gap_note": "per-tier top-minus-rest unavailable gap printed in champion_top_decile_ch262 (a gap above 10 points fails the census as written)"},
        "m1_ch263": {"median_proposals_per_full_day": sr["proposals_ch263"]["median_per_full_day_nonsports_excrypto"], "drafted": _gt(sr["proposals_ch263"]["median_per_full_day_nonsports_excrypto"], 100)},
        "m2_ch264": {"median_overdue_units_per_full_day": sr["overdue_ch264"]["median_per_full_day"], "drafted": _gt(sr["overdue_ch264"]["median_per_full_day"], 25)},
        "lt15_ch267": {"median_scheduled_class_usable_closes_per_full_day": sr["closes_ch267"]["median_scheduled_usable_per_full_day"], "drafted": _gt(sr["closes_ch267"]["median_scheduled_usable_per_full_day"], 30)},
        "ch266_sketch": {"median_display_crossings_per_full_day_nonsports_excrypto": er["tails_ch266_sketch_crossings"]["display_median_per_full_day_nonsports_excrypto"], "kept": _gt(er["tails_ch266_sketch_crossings"]["display_median_per_full_day_nonsports_excrypto"], 50)},
        "resid_ch265_and_fragile_ch268": "the builder's by their own lines; the printed correlations and shares are the inputs",
        "a_decision_is_none_when_its_count_is_unavailable": True,
    }
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "version": VERSION,
        "kind": "CH269 one-shot census and tails map: counts only, k = 0, uncounted; nothing printed is a target, a verdict or a P&L; missing captures are listed as missing and never reconstructed",
        "span": {"start_utc": start_utc, "end_utc": end_utc, "expected_2h_slots": int((t1 - t0) // GRID_S), "quote_days": quote_days, "prediction_days": pred_days, "champion_model": champion,
                 "engine_windows_utc": {k: [datetime.fromtimestamp(v[0], UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), datetime.fromtimestamp(v[1], UTC).strftime("%Y-%m-%dT%H:%M:%SZ")] for k, v in wins.items()} if t_hi == t_hi else {}},
        "sidecar_captures": {"covered": len(caps), "covered_ids": [c["id"] for c in caps], "with_previous_capture_k_minus_1": sum(1 for c in side.caps if c["with_prev"]), "missing_expected": max(0, int((t1 - t0) // GRID_S) - len(caps)),
                             "gaps_over_2h30": gaps, "notes": dict(side.notes)},
        "rules_stream": {"info": rules["info"], "classifier": "PLACEHOLDER lexicon of this map (not CH239's parser)", "scheduled_regex": SCHEDULED_RE.pattern, "barrier_regex": BARRIER_RE.pattern,
                         "classes_n": dict(Counter(rules["classes"].values()))},
        **sr, **er, "decisions": decisions, "engine_notes": notes,
        "not_mapped": NOT_MAPPED, "peak_rss_mb": round(rss / (2**20 if sys.platform == "darwin" else 1024), 1), "inputs": inputs, "code_sha256": code_sha256(),
    }


def _gt(v, line) -> bool | None:
    return None if v is None else bool(v > line)
