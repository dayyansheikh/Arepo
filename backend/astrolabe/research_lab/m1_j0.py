# ruff: noqa: E501
"""M1-J0 (CH263): the counts-only pre-freeze check of ``docs/research_lab/MEASUREMENT_M1_CH263.md`` section 9.1. COUNTS ONLY, k = 0, uncounted.

A read-only pass over stores the host's 2-hourly pass already writes:

* ``snapshots/<capture>/manifest.json``, ``rows.csv.gz`` and ``rows_ext.csv.gz`` (the sidecar), the last N days (default 8);
* sweep 1 of each capture (``book_sweeps/<id>/``, ``series_index`` 0, state complete, manifest ``snapshot_id`` = the capture): only
  ``token_id``, ``batch_receipt_utc`` and ``ask_size_1`` (whether it is finite); no sweep price or size value is printed;
* optionally the signal engine's ``state/labels.json`` key ``res_candidates`` (market ids only; a rebuildable cache, no resolution value).

It applies the text's eligibility E1-E7 (3.2) and unit fields (3.3) at each capture k using captures k - 1 and k only, in strictly
chronological order, and prints counts and receipt-time gaps. It never reads a resolution, a label, an outcome field or any capture
after k for a unit, and it prints no price beyond the k-time zone counts of S6. Its only effects on the design text are rules (a) and
(b) of 9.1 and the observed distribution of S2's fixed cells. Missing captures are listed, never reconstructed.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import resource
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import costs
from . import population_map_ch251 as c251

VERSION = "m1-j0-v1"
GRID0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC).timestamp()
GRID_S = 7200.0
TOL_S = 1800.0
FAV = 0.90
SCOPE = "nonsports_excrypto"
S2_CELLS = ("economics", "culture", "weather", "other", "finance", "politics", "mentions", "tech", "geopolitics", "unknown")
TIER_NAMES = ("lt1k", "1k-10k", "10k-100k", "ge100k", "tier_na")
ROW_COLS = ("market_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date", "clob_token_id_0")
EXT_COLS = ("market_id", "received_utc", "clob_token_id_1", "uma_resolution_statuses", "accepting_orders", "fee_type", "fee_category", "series_slugs",
            "fees_enabled", "fee_schedule", "order_price_min_tick_size")
SWEEP_COLS = ("token_id", "batch_receipt_utc", "ask_size_1")
EMPTY = ("", "[]", "nan", "none", "null")
CODE_NAMES = ("empty", "proposed", "disputed", "resolved", "other")
CLASSES = ("no_previous_capture", "disputed_at_k", "no_k_minus_1_row", "already_proposed", "prior_proposal_state", "not_open_at_k",
           "out_of_scope_sports", "out_of_scope_crypto", "out_of_scope_unknown", "not_two_sided", "contested", "unit")
FORMS_CAP = 200
DECISION_LINES = {"rule_a_extend_to_42_days_if_median_full_day_units_below": 100,
                  "rule_b_extend_to_42_days_if_projected_21_day_units_below": 2000,
                  "projection": "median eligible units per full UTC day x 21"}


# --- small readers ------------------------------------------------------------------------------------------------------------------

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def code_sha256() -> dict:
    here = Path(__file__).resolve()
    run = here.parents[2] / "scripts" / "run_m1_j0.py"
    return {p.name: sha256_file(p) for p in (here, run) if p.exists()}


def iter_csv(path: Path, cols: tuple[str, ...]):
    """First item: which columns exist; then one tuple per row (missing columns as '')."""
    csv.field_size_limit(10**9)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd, None)
        if head is None:
            return
        pos = {c: i for i, c in enumerate(head)}
        idx = [pos.get(c, -1) for c in cols]
        yield tuple(c in pos for c in cols)
        for row in rd:
            yield tuple(row[i] if 0 <= i < len(row) else "" for i in idx)


def status_code(u) -> tuple[int, bool]:
    """(code, both): 0 empty, 1 proposed (``propos`` without ``disput``), 2 disputed (``disput``, with or without ``propos``), 3 resolved
    (``resolv`` only), 4 other non-empty; ``both`` = the string carries both ``propos`` and ``disput``."""
    s = str(u if u is not None else "").strip().lower()
    if s in EMPTY:
        return 0, False
    p, d = "propos" in s, "disput" in s
    if d:
        return 2, p
    if p:
        return 1, False
    if "resolv" in s:
        return 3, False
    return 4, False


def false_flag(v) -> bool:
    return str(v).strip().lower() in ("false", "0", "0.0", "f")


def tier_of(liq: float) -> int:
    if not math.isfinite(liq):
        return 4
    return 0 if liq < 1e3 else 1 if liq < 1e4 else 2 if liq < 1e5 else 3


def zone_of(c: float) -> str:
    if c <= 0.001 + 1e-12:
        return "c<=0.001"
    for hi, name in ((0.005, "(0.001,0.005]"), (0.01, "(0.005,0.01]"), (0.03, "(0.01,0.03]"), (0.10, "(0.03,0.10]")):
        if c <= hi + 1e-12:
            return name
    return ">0.10"


def end_rel_of(end_ts: float, t_d: float) -> str:
    if not math.isfinite(end_ts):
        return "missing"
    if end_ts > t_d:
        return "future"
    return "past<=24h" if t_d - end_ts <= 86400.0 else "past>24h"


def members_of(n: int) -> str:
    return "1" if n <= 1 else "2-5" if n <= 5 else "6+"


def units_bucket(n: int) -> str:
    return "1" if n <= 1 else "2-3" if n <= 3 else "4-9" if n <= 9 else "10+"


def tick_of(v) -> str:
    t = c240._f(v)
    if not math.isfinite(t):
        return "other_or_missing"
    return "0.001" if abs(t - 0.001) < 1e-9 else "0.01" if abs(t - 0.01) < 1e-9 else "other_or_missing"


def s2_cell(key: str) -> str:
    return key if key in S2_CELLS and key != "unknown" else "unknown"


def qdist(vals: list[float]) -> dict:
    v = sorted(x for x in vals if math.isfinite(x))
    if not v:
        return {"n": 0}

    def q(p):
        return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))]

    return {"n": len(v), "median": q(0.5), "p90": q(0.9), "min": v[0], "max": v[-1]}


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(r / (2**20 if sys.platform == "darwin" else 1024.0), 1)


# --- discovery ------------------------------------------------------------------------------------------------------------------------

def slot_of(t: float) -> tuple[int, bool]:
    s = int(round((t - GRID0) / GRID_S))
    return s, abs(t - (GRID0 + s * GRID_S)) <= TOL_S


def discover_captures(root: Path, start_ts: float, end_ts: float) -> tuple[list[dict], Counter]:
    """The first complete capture of each 2 h slot (by manifest start) with start in [start, end), ordered by start."""
    notes: Counter = Counter()
    by_slot: dict = {}
    for p in sorted(Path(root).glob("*/manifest.json")):
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            notes["manifest_unreadable"] += 1
            continue
        t = c240.parse_utc(m.get("started_utc"))
        if m.get("state") != "complete" or not math.isfinite(t) or not (start_ts <= t < end_ts):
            continue
        if not (p.parent / "rows.csv.gz").exists():
            notes["complete_without_rows"] += 1
            continue
        s, on_grid = slot_of(t)
        if not on_grid:
            notes["off_grid"] += 1
            continue
        cur = by_slot.get(s)
        if cur is None or t < cur["start"]:
            by_slot[s] = {"id": p.parent.name, "capture_id": str(m.get("capture_id") or p.parent.name), "start": t, "slot": s, "dir": p.parent}
    return [by_slot[k] for k in sorted(by_slot)], notes


def discover_sweeps(root: Path | None) -> dict:
    """{snapshot_id: sweep dir} for sweep 1 (series_index 0, state complete, rows present); the first by directory name."""
    out: dict = {}
    if root is None or not Path(root).is_dir():
        return out
    for p in sorted(Path(root).glob("*/manifest.json")):
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        if m.get("state") != "complete" or m.get("series_index") != 0 or not m.get("snapshot_id") or not (p.parent / "rows.csv.gz").exists():
            continue
        out.setdefault(str(m["snapshot_id"]), p.parent)
    return out


def engine_candidates(engine_root: Path | None) -> set | None:
    if engine_root is None:
        return None
    p = Path(engine_root) / "state" / "labels.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    out = {int(k) for k in (d.get("res_candidates") or {}) if str(k).lstrip("-").isdigit()}
    del d
    return out


# --- the pass -------------------------------------------------------------------------------------------------------------------------

class J0Pass:
    """Feeds captures strictly in time order. Keeps only capture k - 1's row ids and status codes, the last proposal-or-dispute time per
    market (E3), the markets already counted as units, and small per-unit records of k-time fields."""

    def __init__(self, warmup: int) -> None:
        self.warmup = warmup
        self.n_fed = 0
        self.last_t = -math.inf
        self.prev: dict | None = None
        self.hist_last: dict = {}
        self.unit_markets: set = set()
        self.units: list[dict] = []
        self.funnel: Counter = Counter()
        self.funnel_by_cat: Counter = Counter()
        self.prior_gap: Counter = Counter()
        self.forms: Counter = Counter()
        self.forms_overflow = 0
        self.both_tokens_rows = 0
        self.transitions: Counter = Counter()
        self.sidecar_missing_open_binary = 0
        self.processed: list[dict] = []
        self.warmup_caps: list[str] = []
        self.warmup_slots: set = set()
        self.inputs: list[dict] = []
        self.notes: Counter = Counter()

    def _read_ext(self, path: Path | None) -> tuple[dict, dict]:
        codes: dict = {}
        cand: dict = {}
        if path is None or not Path(path).exists():
            self.notes["captures_without_sidecar"] += 1
            return codes, cand
        it = iter_csv(path, EXT_COLS)
        pres = next(it, None)
        if pres is None:
            return codes, cand
        for c, ok in zip(EXT_COLS, pres, strict=True):
            if not ok:
                self.notes[f"sidecar_column_missing:{c}"] += 1
        for mid_s, rec, tok1, uma, acc, ft, fc, ss, fe, fsch, tick in it:
            try:
                mid = int(mid_s)
            except ValueError:
                continue
            code, both = status_code(uma)
            codes[mid] = code
            if code:
                form = str(uma).strip().lower()
                if form in self.forms or len(self.forms) < FORMS_CAP:
                    self.forms[form] += 1
                else:
                    self.forms_overflow += 1
            if both:
                self.both_tokens_rows += 1
            if code in (1, 2) and "propos" in str(uma).lower():
                cand[mid] = (c240.parse_utc(rec), tok1, code, acc, ft, fc, ss, fe, fsch, tick, pres[EXT_COLS.index("fees_enabled")])
        return codes, cand

    def feed(self, cap: dict, sweep_dir: Path | None) -> None:
        if cap["start"] <= self.last_t:
            raise ValueError(f"captures must be fed strictly in time order: {cap['id']}")
        self.last_t = cap["start"]
        d = Path(cap["dir"])
        ext_p = d / "rows_ext.csv.gz"
        for f in (d / "manifest.json", d / "rows.csv.gz", ext_p):
            if f.exists():
                self.inputs.append({"path": str(f), "bytes": f.stat().st_size, "sha256": sha256_file(f)})
        codes, cand = self._read_ext(ext_p if ext_p.exists() else None)
        has_prev = self.prev is not None and cap["slot"] == self.prev["slot"] + 1
        if has_prev:
            pc = self.prev["codes"]
            for mid, c in codes.items():
                p = pc.get(mid)
                if p is not None and p != c:
                    self.transitions[f"{CODE_NAMES[p]}->{CODE_NAMES[c]}"] += 1
        row_ids: set = set()
        evc: Counter = Counter()
        rows: dict = {}
        it = iter_csv(d / "rows.csv.gz", ROW_COLS)
        pres = next(it, None)
        if pres is not None:
            for c, ok in zip(ROW_COLS, pres, strict=True):
                if not ok:
                    self.notes[f"rows_column_missing:{c}"] += 1
            for mid_s, ev, rec, closed, active, binary, bid, ask, liq, end, tok0 in it:
                try:
                    mid = int(mid_s)
                except ValueError:
                    continue
                row_ids.add(mid)
                is_open = c240._truthy(binary) and not c240._truthy(closed) and c240._truthy(active)
                if is_open:
                    evc[ev] += 1
                    if mid not in codes and codes:
                        self.sidecar_missing_open_binary += 1
                if mid in cand:
                    rows[mid] = (ev, c240.parse_utc(rec), closed, active, binary, c240._f(bid), c240._f(ask), c240._f(liq), c240.parse_utc(end), tok0)
        counted = self.n_fed >= self.warmup
        self.n_fed += 1
        if counted:
            self._classify(cap, has_prev, codes, cand, rows, evc, sweep_dir)
            self.processed.append({"id": cap["id"], "start": cap["start"], "slot": cap["slot"], "with_prev": has_prev})
        else:
            self.warmup_caps.append(cap["id"])
            self.warmup_slots.add(cap["slot"])
        for mid, c in codes.items():
            if c in (1, 2):
                self.hist_last[mid] = cap["start"]
        self.prev = {"slot": cap["slot"], "codes": codes, "row_ids": row_ids}

    def _classify(self, cap, has_prev, codes, cand, rows, evc, sweep_dir) -> None:
        day = c240.day_of(cap["start"])
        new_units: list[dict] = []
        for mid in sorted(cand):
            rec_e, tok1, code, acc, ft, fc, ss, fe, fsch, tick, has_fe = cand[mid]
            cat = c240.category_of(ft, fc, ss, True)
            cls = None
            if not has_prev:
                cls = "no_previous_capture"
            elif code == 2:
                cls = "disputed_at_k"
            elif mid not in self.prev["row_ids"] or mid not in self.prev["codes"]:
                cls = "no_k_minus_1_row"
            elif self.prev["codes"][mid] in (1, 2, 3):
                cls = "already_proposed"
            elif mid in self.unit_markets or mid in self.hist_last:
                cls = "prior_proposal_state"
                gap_h = (cap["start"] - self.hist_last[mid]) / 3600.0 if mid in self.hist_last else math.nan
                self.prior_gap["earlier_unit" if mid in self.unit_markets else "<=24h" if gap_h <= 24 else "24-72h" if gap_h <= 72 else "72-168h" if gap_h <= 168 else ">168h"] += 1
            r = rows.get(mid)
            if cls is None and (r is None or not c240._truthy(r[4]) or c240._truthy(r[2]) or not c240._truthy(r[3]) or false_flag(acc)):
                cls = "not_open_at_k"
            if cls is None and cat != SCOPE:
                cls = f"out_of_scope_{cat}"
            if cls is None:
                bid, ask = r[5], r[6]
                if not (bid > 0 and bid < ask and ask <= 1):
                    cls = "not_two_sided"
                else:
                    m = (bid + ask) / 2.0
                    if m >= FAV:
                        side, ask_f = "YES", ask
                    elif m <= 1 - FAV:
                        side, ask_f = "NO", 1.0 - bid
                    else:
                        cls = "contested"
            self.funnel[cls or "unit"] += 1
            self.funnel_by_cat[f"{cls or 'unit'}|{cat}"] += 1
            if cls is not None:
                continue
            ev = r[0]
            key = costs.category_key(fc)
            fee_cls = c251.fee_class(fe, bool(has_fe), fsch)[0]
            new_units.append({"mid": mid, "day": day, "event": ev, "side": side, "zone": zone_of(1.0 - ask_f), "tier": TIER_NAMES[tier_of(r[7])],
                              "cat_key": key, "fee_category_raw": str(fc), "s2": s2_cell(key), "fee_class": fee_cls,
                              "ladder": "standalone" if evc[ev] <= 1 else ("member_winner" if side == "YES" else "member_loser"),
                              "members": members_of(evc[ev]), "tick": tick_of(tick), "end_ts": r[8], "row_rec": r[1], "ext_rec": rec_e,
                              "token": r[9] if side == "YES" else tok1, "cap": cap["id"]})
            self.unit_markets.add(mid)
        if not new_units:
            return
        want = {u["token"]: u for u in new_units if u["token"]}
        if sweep_dir is not None and (Path(sweep_dir) / "rows.csv.gz").exists():
            it = iter_csv(Path(sweep_dir) / "rows.csv.gz", SWEEP_COLS)
            pres = next(it, None)
            if pres is not None:
                for tok, rec, asz in it:
                    u = want.get(tok)
                    if u is None or "sweep_rec" in u:
                        continue
                    u["sweep_rec"] = c240.parse_utc(rec)
                    u["sweep_covered"] = math.isfinite(c240._f(asz))
        else:
            self.notes["captures_without_sweep_1"] += 1
        for u in new_units:
            t_d = max(x for x in (u["row_rec"], u["ext_rec"], u.get("sweep_rec", math.nan)) if math.isfinite(x)) if any(
                math.isfinite(x) for x in (u["row_rec"], u["ext_rec"], u.get("sweep_rec", math.nan))) else cap["start"]
            u["end_rel"] = end_rel_of(u.pop("end_ts"), t_d)
            u["gap_ext_row_s"] = u["ext_rec"] - u["row_rec"]
            u["gap_sweep_row_s"] = u.get("sweep_rec", math.nan) - u["row_rec"]
            u["sweep_covered"] = bool(u.get("sweep_covered", False))
            u.pop("token", None)
            self.units.append(u)

    # --- report ---------------------------------------------------------------------------------------------------------------------

    def report(self, start_ts: float, end_ts: float, eng: set | None) -> dict:
        U = self.units
        caps_by_day = Counter(c240.day_of(c["start"]) for c in self.processed)
        full_days = sorted(d for d, n in caps_by_day.items() if n >= 12)
        per_day = Counter(u["day"] for u in U)
        med = None
        if full_days:
            v = sorted(per_day.get(d, 0) for d in full_days)
            n = len(v)
            med = float(v[n // 2]) if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0
        first_day = min((c240.day_of(c["start"]) for c in self.processed), default=None)

        def week(day):
            if first_day is None:
                return "na"
            k = (datetime.fromisoformat(day) - datetime.fromisoformat(first_day)).days // 7
            return f"days {7 * k + 1}-{7 * k + 7}"

        ev_units = Counter(u["event"] for u in U)
        cov = [u for u in U if u["sweep_covered"]]

        def by(key, rows=U):
            return dict(sorted(Counter(r[key] for r in rows).items()))

        def cov_by(key):
            tot, cv = Counter(u[key] for u in U), Counter(u[key] for u in cov)
            return {k: {"units": tot[k], "covered": cv.get(k, 0), "share": round(cv.get(k, 0) / tot[k], 4)} for k in sorted(tot)}

        raw = Counter(f"{u['fee_category_raw']} -> {u['cat_key'] or '(empty)'}" for u in U)
        all_slots = range(int(math.ceil((start_ts - GRID0) / GRID_S)), int(math.ceil((end_ts - GRID0) / GRID_S)))
        seen = {c["slot"] for c in self.processed} | self.warmup_slots
        missing = [s for s in all_slots if s not in seen]
        decision_a = None if med is None else bool(med < DECISION_LINES["rule_a_extend_to_42_days_if_median_full_day_units_below"])
        decision_b = None if med is None else bool(med * 21 < DECISION_LINES["rule_b_extend_to_42_days_if_projected_21_day_units_below"])
        return {
            "kind": "M1-J0 counts-only pre-freeze check (MEASUREMENT_M1_CH263.md 9.1): counts only, k = 0, uncounted; no resolution, label, outcome or post-k price read; informed (M1-J0)",
            "version": VERSION,
            "code_sha256": code_sha256(),
            "span": {"start_utc": datetime.fromtimestamp(start_ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "end_utc": datetime.fromtimestamp(end_ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "warmup_captures": self.warmup_caps, "processed_captures": len(self.processed), "with_previous": sum(1 for c in self.processed if c["with_prev"]),
                     "full_days": full_days, "missing_slots_utc": [datetime.fromtimestamp(GRID0 + s * GRID_S, UTC).strftime("%Y-%m-%dT%H:%MZ") for s in missing]},
            "decision_lines": DECISION_LINES,
            "decisions": {"median_full_day_units": med, "projected_21_day_units": None if med is None else med * 21,
                          "rule_a_extend_to_42_days": decision_a, "rule_b_extend_to_42_days": decision_b,
                          "note": "a null decision means no full day was covered (unavailable), not a pass; J0's only effects are rules (a) / (b) and S2's distribution"},
            "eligible_units": {"total": len(U), "per_day": dict(sorted(per_day.items())), "events": len(ev_units),
                               "units_per_event_projected": by("b", [{"b": units_bucket(n)} for n in ev_units.values()]),
                               "units_per_event_note": "T_U strata (1, 2-3, 4-9, 10+) projected with every unit treated as final-state; counts of events"},
            "funnel": {c: self.funnel.get(c, 0) for c in CLASSES} | {k: v for k, v in self.funnel.items() if k not in CLASSES},
            "funnel_note": "market-capture rows whose sidecar status carries 'propos' at k, classed by the first failing rule of E1-E7 (3.2); 'unit' = eligible",
            "funnel_by_category": dict(sorted(self.funnel_by_cat.items())),
            "unavailable_by_category": {k: v for k, v in sorted(self.funnel_by_cat.items()) if k.split("|")[0] in ("no_k_minus_1_row", "no_previous_capture")},
            "prior_proposal_state_gap": dict(sorted(self.prior_gap.items())),
            "sidecar_missing_open_binary_rows": self.sidecar_missing_open_binary,
            "splits_counts": {"S1_tier": by("tier"), "S2_fee_category": {c: sum(1 for u in U if u["s2"] == c) for c in S2_CELLS}, "S3_ladder": by("ladder"),
                              "S4_fee_class": by("fee_class"), "S5_side": by("side"), "S6_zone": by("zone"), "S7_end_rel": by("end_rel"), "S8_members": by("members"),
                              "S9_tick": by("tick"), "S10_span_week": dict(sorted(Counter(week(u["day"]) for u in U).items())),
                              "S6_x_S9": dict(sorted(Counter(f"{u['zone']}|{u['tick']}" for u in U).items()))},
            "s2_raw_fee_category_to_key": dict(raw.most_common(100)),
            "sweep_1_coverage": {"units": len(U), "covered_finite_ask_size_1": len(cov), "share": round(len(cov) / len(U), 4) if U else None,
                                 "by_S1": cov_by("tier"), "by_S7": cov_by("end_rel"),
                                 "units_with_any_sweep_row": sum(1 for u in U if math.isfinite(u["gap_sweep_row_s"]))},
            "receipt_gaps_s": {"sidecar_minus_row": qdist([u["gap_ext_row_s"] for u in U]), "sweep_minus_row": qdist([u["gap_sweep_row_s"] for u in U])},
            "engine_resolution_candidates": None if eng is None else {"units_in_candidates": sum(1 for u in U if u["mid"] in eng), "units": len(U),
                                                                       "note": "membership of state/labels.json res_candidates only; no resolution value read"},
            "status_forms": {"distinct_forms": dict(self.forms.most_common(FORMS_CAP)), "forms_overflow_rows": self.forms_overflow,
                             "rows_with_both_propos_and_disput": self.both_tokens_rows, "transitions_between_consecutive_captures": dict(sorted(self.transitions.items()))},
            "notes": dict(sorted(self.notes.items())),
            "inputs": self.inputs,
            "not_printed": "no price, size, c value, resolution, label or outcome; c enters only as the S6 zone count",
        }


def run_j0(snapshot_root: Path, sweep_root: Path | None, engine_root: Path | None, start_ts: float, end_ts: float, warmup: int = 12) -> dict:
    caps, notes = discover_captures(snapshot_root, start_ts, end_ts)
    sweeps = discover_sweeps(sweep_root)
    jp = J0Pass(warmup)
    for c in caps:
        sd = sweeps.get(c["capture_id"]) or sweeps.get(c["id"])
        jp.feed(c, sd)
    jp.notes.update({f"discover:{k}": v for k, v in notes.items()})
    rep = jp.report(start_ts, end_ts, engine_candidates(engine_root))
    rep["peak_rss_mb"] = peak_rss_mb()
    return rep
