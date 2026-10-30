# ruff: noqa: E501
"""M2 (CH264) J1 extractor (sections 3.2, 3.3, 3.5 and 9.2 of ``docs/research_lab/MEASUREMENT_M2_CH264.md``) and its J0 dry mode (9.1).

One class, :class:`M2Pass`, folds complete 2-hourly captures in strict chronological order and, for each capture k, classifies the
markets whose row is at least 2 h past ``end_date`` and that were never seen overdue before (E1-E9, every exclusion a counted class).

* ``dry_run=True`` is M2-J0: it keeps counts only in memory, writes no units store, no state file and no follow-up file (it refuses a
  store path), and reads no resolution, outcome, follow-up state or post-k price. ``report_j0`` prints counts and the decision values of
  rules (a) / (e) of 9.1.
* ``dry_run=False`` is J1: write-once ``units/<capture_id>.jsonl.gz``, ``status/<capture_id>.json`` (funnel counts, state sha chain,
  only the sha256 and line count of the follow-up file), ``followup/<capture_id>.jsonl.gz`` (blind, no price, written but never read
  by the extractor) and ``state.json``.

Only E026-frozen ``costs.py`` and the CH240 / CH251 readers are imported (read only). The rule lexicon is copied verbatim from CH269.
Nothing here reads a book sweep, a trade, an engine store or any Gamma outcome field. The J2 / J3 / A parts are not in this module.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import resource
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import costs
from . import population_map_ch251 as c251

VERSION = "m2-j1-v1"
ROLE = "prospective_measurement"
REGISTERED_UTC = datetime(2026, 11, 24, tzinfo=UTC).timestamp()
END_UTC = datetime(2026, 12, 15, tzinfo=UTC).timestamp()
READOUT_UTC = datetime(2027, 1, 29, tzinfo=UTC).timestamp()
GRID0 = datetime(2026, 10, 1, 0, 31, tzinfo=UTC).timestamp()
GRID_S = 7200.0
TOL_S = 1800.0
MISSING_AFTER_S = 6 * 3600.0
LOOKBACK_SLOTS = 84
OVERDUE_S = 7200.0
SLOT_MAX_FWD_S = 3 * 3600.0  # watch bound for left_before_overdue_slot: k - 1 start + the longest k - 1 -> k gap the slot tolerance allows
SCOPE = "nonsports_excrypto"
MID_LO, MID_HI = 0.05, 0.95
LIQ_CUTS = (47.46151, 330.74525)  # CH269 census-fixed (seals/CH269_map_q0730.json), 6
EMPTY_FORMS = ("", "[]", "nan", "none")  # E6 whitelist (CH269's empty forms)
PIN_MODULES = ("boundary_map_ch240.py", "cb17_census.py", "live_tests11_base.py", "live_tests8_base.py", "population_map_ch251.py", "calibration.py", "costs.py",
               "cb13_label.py")  # cb13_label.py: added on the coordinator's instruction (cb17_census.is_sports_sidecar reads it; decides E5 sports scope); not in the doc list
S3_KEYS = ("economics", "culture", "weather", "other", "finance", "politics", "mentions", "tech", "geopolitics")
S2_CELLS = ("scheduled", "barrier", "both", "other", "no_rules", "rules_unresolved")
S1_CELLS = ("low", "mid", "high", "na")
ROW_COLS = ("market_id", "event_id", "binary", "best_bid", "best_ask", "closed", "active", "end_date", "liquidity", "received_utc")
EXT_COLS = ("market_id", "received_utc", "uma_resolution_statuses", "accepting_orders", "fee_type", "fee_category", "series_slugs", "fees_enabled",
            "fee_schedule", "order_price_min_tick_size", "open_interest")
FUNNEL_ORDER = ("no_previous_capture", "k_minus_1_before_window", "no_k_minus_1_row", "k_minus_1_end_date_missing", "already_overdue_at_k_minus_1", "prior_unit", "not_open_at_k", "sidecar_missing", "accepting_unknown",
                "out_of_scope_sports", "out_of_scope_crypto", "out_of_scope_unknown", "uma_state_at_k", "uma_other_at_k", "not_two_sided", "mid_low", "mid_high",
                "no_favourite", "unit")
FORMS_CAP = 200  # the cap on the distinct-form table of ALL status strings (diagnostic); the E6 non-whitelist forms are never capped (ruling 15)
DECISION_LINES = {"rule_a_extend_to_42_days_if_median_full_day_units_below": 75, "rule_b_record_only_projected_21_day_units_below": 1500,
                  "rule_e_receipt_time_reading_computed_never_manual_day_before_for_records_without_finished_utc": True}

# CH269's placeholder lexicon, copied verbatim (census_map_ch269.py l. 65-66); the sha256 of the two patterns is a spec pin (3.5).
SCHEDULED_RE = re.compile(r"\b(scheduled|fomc|federal reserve|cpi|consumer price index|jobs report|nonfarm|unemployment rate|gdp|earnings|box office|election|vote|referendum|certified|official (?:results?|data|release|figures?)|will be (?:released|published|announced)|press release)\b")
BARRIER_RE = re.compile(r"\b(at any point|at any time|any time|reach(?:es)?|hits?|touch(?:es)?|dips?|exceeds?|before|by (?:january|february|march|april|may|june|july|august|september|october|november|december|the end of))\b")


class DryModeError(Exception):
    """A dry (J0) pass was asked to write a store."""


class StateOrderError(Exception):
    """The state file / capture order violates 9.2 (chronological processing)."""


# --- small helpers -------------------------------------------------------------------------------------------------------------------

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def code_sha256() -> dict:
    here = Path(__file__).resolve()
    run = here.parents[2] / "scripts" / "run_m2_j0.py"
    return {p.name: sha256_file(p) for p in (here, run) if p.exists()}


def lexicon_sha256() -> str:
    return sha256_bytes((SCHEDULED_RE.pattern + "\n" + BARRIER_RE.pattern).encode())


def module_pins() -> dict:
    """sha256 of every imported module whose function sets an eligibility class, split cell or outcome class (5, MUST 2)."""
    d = Path(__file__).resolve().parent
    return {n: (sha256_file(d / n) if (d / n).exists() else None) for n in PIN_MODULES}


def r6(x: float) -> float:
    return round(x, 6) if math.isfinite(x) else x


def classify_rule(text: str) -> str:
    t = text.lower()
    s, b = bool(SCHEDULED_RE.search(t)), bool(BARRIER_RE.search(t))
    return "scheduled" if s and not b else "barrier" if b and not s else "both" if s and b else "other"


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


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(r / (2**20 if sys.platform == "darwin" else 1024.0), 1)


def slot_of(t: float) -> tuple[int, bool]:
    s = int(round((t - GRID0) / GRID_S))
    return s, abs(t - (GRID0 + s * GRID_S)) <= TOL_S


def slot_time(s: int) -> float:
    return GRID0 + s * GRID_S


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def acc_state(v) -> str:
    s = str(v).strip().lower()
    return "true" if s in ("true", "1", "1.0", "t") else "false" if s in ("false", "0", "0.0", "f") else "unknown"


def s1_cell(liq: float) -> str:
    if not math.isfinite(liq):
        return "na"
    return "low" if liq < LIQ_CUTS[0] else "mid" if liq < LIQ_CUTS[1] else "high"


def s6_cell(mid_f: float) -> str:
    m = r6(mid_f)
    for hi, name in ((0.6, "(0.5,0.6]"), (0.7, "(0.6,0.7]"), (0.8, "(0.7,0.8]"), (0.9, "(0.8,0.9]")):
        if m <= hi:
            return name
    return "(0.9,0.95]"


def s11_cell(spread: float) -> str:
    s = r6(spread)
    return "<=0.01" if s <= 0.01 else "(0.01,0.03]" if s <= 0.03 else "(0.03,0.10]" if s <= 0.10 else ">0.10"


def s8_cell(n: int) -> str:
    return "1" if n <= 1 else "2-5" if n <= 5 else "6+"


def s9_cell(tick) -> str:
    t = r6(c240._f(tick))
    return "0.001" if t == 0.001 else "0.01" if t == 0.01 else "other_or_missing"


def s3_cell(cat_k: str) -> str:
    return cat_k if cat_k in S3_KEYS else "unknown"


def units_bucket(n: int) -> str:
    return "1" if n <= 1 else "2-3" if n <= 3 else "4-9" if n <= 9 else "10+"


def fee_exponent(fee_schedule) -> float:
    try:
        d = json.loads(fee_schedule) if isinstance(fee_schedule, str) and fee_schedule else {}
        x = float(d["exponent"]) if isinstance(d, dict) and "exponent" in d else 1.0
    except (ValueError, TypeError, KeyError):
        return 1.0
    return x if math.isfinite(x) else 1.0


def fee_lines(cat_k: str, fees_enabled, has_fe_col: bool, fee_schedule, ask_f: float) -> dict:
    """5: L1 (conservative, served flag) and L2 (docs rate; MAX_TAKER_RATE for a key outside the docs table), per share at p = ask_f."""
    rate, _ = c251.fee_parse(fee_schedule)
    sched = rate if math.isfinite(rate) else None
    served = has_fe_col and str(fees_enabled).strip() != ""
    fe_arg = (True if c240._truthy(fees_enabled) else False) if served else None
    exp = fee_exponent(fee_schedule)
    r1 = costs.taker_rate(cat_k, sched, fe_arg, policy="conservative")
    r2 = costs.taker_rate(cat_k, sched, None, policy="conservative") if cat_k in costs.CATEGORY_TAKER_RATE else costs.MAX_TAKER_RATE
    return {"rate_l1": r1, "rate_l2": r2, "exponent": exp, "schedule_rate": sched, "fees_enabled_arg": fe_arg,
            "fee_l1": costs.taker_fee_ps(ask_f, r1, exp), "fee_l2": costs.taker_fee_ps(ask_f, r2, exp)}


# --- rule text index (3.5) -----------------------------------------------------------------------------------------------------------

class RulesIndex:
    """Per market, the committed ``row`` / ``hash`` records of the keyless ``gamma_rules`` day files in file order, each with the commit time
    of the ``poll`` line that follows it (``finished_utc``). Text is classified and dropped. Rows of a slot without a following ``ok`` poll
    line are torn and ignored. ``last_row_class`` is CH269's reading (last ``row`` line per market, committed or not) for the J0 coverage
    comparison only; it is never used for a unit."""

    def __init__(self) -> None:
        self.by_mid: dict = {}
        self.sha_class: dict = {}
        self.last_row_class: dict = {}
        self.info = {"files": 0, "oldest_file": None, "newest_file": None, "poll_lines": 0, "poll_ok": 0, "poll_ok_with_parseable_receipt": 0,
                     "rows_committed": 0, "hash_committed": 0, "rows_torn_or_failed": 0, "markets": 0, "records_without_receipt": 0,
                     "commits_crossing_midnight": 0, "max_poll_duration_s": None}

    @classmethod
    def load(cls, root: Path | None) -> RulesIndex:
        ix = cls()
        if root is None or not Path(root).is_dir():
            return ix
        for f in sorted(Path(root).glob("*.jsonl")):
            ix.info["files"] += 1
            ix.info["oldest_file"] = ix.info["oldest_file"] or f.name
            ix.info["newest_file"] = f.name
            day = f.stem
            pending: list = []
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    if '"row"' not in line and '"hash"' not in line and '"poll"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                    except ValueError:
                        continue
                    kind = d.get("kind")
                    if kind in ("row", "hash"):
                        key = str(d.get("key", ""))
                        if not key.startswith("m:"):
                            continue
                        try:
                            mid = int(key[2:])
                        except ValueError:
                            continue
                        if kind == "row":
                            data = d.get("data")
                            if isinstance(data, str):
                                try:
                                    data = json.loads(data)
                                except ValueError:
                                    data = {}
                            if not isinstance(data, dict):
                                continue
                            cls_ = classify_rule(" ".join(str(data.get(k) or "") for k in ("question", "description", "resolutionSource")))
                            ix.last_row_class[mid] = cls_
                            pending.append((d.get("slot"), mid, "row", cls_, d.get("sha")))
                        else:
                            pending.append((d.get("slot"), mid, "hash", None, d.get("sha")))
                    elif kind == "poll":
                        ix.info["poll_lines"] += 1
                        if d.get("ok") is True:
                            ix.info["poll_ok"] += 1
                            ts = c240.parse_utc(d.get("finished_utc"))
                            if math.isfinite(ts):
                                ix.info["poll_ok_with_parseable_receipt"] += 1
                                if c240.day_of(ts).replace("-", "") != day:
                                    ix.info["commits_crossing_midnight"] += 1  # day files are keyed by poll start (streams/common.py:366)
                                t0 = c240.parse_utc(d.get("started_utc"))
                                if math.isfinite(t0) and ts >= t0:
                                    ix.info["max_poll_duration_s"] = max(ix.info["max_poll_duration_s"] or 0.0, ts - t0)
                            slot = d.get("slot")
                            for sl, mid, k2, cls_, sh in pending:
                                if sl != slot:
                                    ix.info["rows_torn_or_failed"] += 1
                                    continue
                                if not math.isfinite(ts):
                                    ix.info["records_without_receipt"] += 1
                                ix.by_mid.setdefault(mid, []).append((ts if math.isfinite(ts) else None, day, k2, cls_, sh))
                                ix.info["rows_committed" if k2 == "row" else "hash_committed"] += 1
                                if k2 == "row" and sh:
                                    ix.sha_class[sh] = cls_
                        else:
                            ix.info["rows_torn_or_failed"] += len(pending)
                        pending = []
            ix.info["rows_torn_or_failed"] += len(pending)
        ix.info["markets"] = len(ix.by_mid)
        return ix

    def lookup(self, mid: int, t_d: float, k_day: str) -> tuple[str, float | None]:
        return lookup_records(self.by_mid.get(mid, ()), self.sha_class, t_d, k_day)


def lookup_records(recs, sha_class: dict, t_d: float, k_day: str) -> tuple[str, float | None]:
    """(class, commit time) of the market's last committed record visible at ``t_d`` (3.5, ruling 7). Each record has its own reader: a record
    with a parseable poll ``finished_utc`` is visible iff it is <= ``t_d``; a record without one is visible only if its day file's UTC day is
    strictly before k's UTC day. No record -> ``no_rules``; a ``hash`` record resolves through any committed ``row`` with an equal sha
    (``sha_class``), else ``rules_unresolved``. ``gone`` records are never read."""
    kd = k_day.replace("-", "")
    for ts, day, kind, cls_, sh in reversed(recs):
        if ts is not None:
            if not ts <= t_d:
                continue
        elif not day < kd:
            continue
        if kind == "row":
            return cls_, ts
        return sha_class.get(sh) or "rules_unresolved", ts
    return "no_rules", None


# --- discovery -----------------------------------------------------------------------------------------------------------------------

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


# --- the pass ------------------------------------------------------------------------------------------------------------------------

class M2Pass:
    """Folds captures strictly in time order (9.2). See the module docstring for dry (J0) versus J1."""

    def __init__(self, *, window_start: float, window_end: float | None = None, rules: RulesIndex | None = None, lookback_from: float | None = None,
                 dry_run: bool = True, store: Path | None = None, spec_sha: str = "", record_followup: bool = True, followup_until: float | None = None) -> None:
        if dry_run and store is not None:
            raise DryModeError("dry mode (M2-J0) writes no units store, no state file and no follow-up file")
        if not dry_run and store is None:
            raise ValueError("J1 needs a store directory")
        self.window_start, self.window_end = window_start, window_end
        self.rules = rules or RulesIndex()
        self.lookback_from = lookback_from  # N4: J1 counts look-back slots from slot_of(lookback_from)
        self.ledger: dict = {}  # ruling 12: append-only rule ledger {market_id: [[ts|None, day, kind, class, sha], ...]}
        self.ledger_sha_class: dict = {}
        self.dry = dry_run
        self.store = Path(store) if store is not None else None
        self.spec_sha = spec_sha
        self.code_sha = sha256_file(Path(__file__).resolve())
        self.record_followup = record_followup
        self.followup_until = followup_until if followup_until is not None else READOUT_UTC
        # chronological state
        self.last_t = -math.inf
        self.last_slot: int | None = None
        self.processed_slots: set = set()
        self.missing_slots: set = set()
        self.seen: set = set()
        self.unit_ids: set = set()
        self.prev: dict | None = None
        # counts
        self.funnel: Counter = Counter()
        self.funnel_by_day: Counter = Counter()
        self.extra: Counter = Counter()
        self.left_by_day: Counter = Counter()
        self.end_missing_by_day: Counter = Counter()
        self.forms: Counter = Counter()
        self.forms_other: Counter = Counter()
        self.end_missing_markets: set = set()
        self.t_d_source: Counter = Counter()
        self._cap_funnel: Counter = Counter()
        self.forms_overflow = 0
        self.notes: Counter = Counter()
        self.units: list[dict] = []
        self.classified: list[dict] = []
        self.inputs: list[dict] = []
        self.oi_nonempty = 0
        self.oi_rows = 0
        self.cat_raw: Counter = Counter()
        self.rule_cov: Counter = Counter()
        self.state_sha = "none"
        if self.store is not None:
            for sub in ("units", "status", "followup"):
                (self.store / sub).mkdir(parents=True, exist_ok=True)
            self._load_state()

    # --- state file (J1 only) ----------------------------------------------------------------------------------------------------------
    def _state_path(self) -> Path:
        return self.store / "state.json"

    def _state_blob(self) -> bytes:
        d = {"version": VERSION, "spec_sha": self.spec_sha, "code_sha": self.code_sha, "last_slot": self.last_slot, "last_start": self.last_t if math.isfinite(self.last_t) else None,
             "processed_slots": sorted(self.processed_slots), "missing_slots": sorted(self.missing_slots),
             "seen": sorted(self.seen), "unit_ids": sorted(self.unit_ids),
             "rule_ledger": {"records": {str(m): self.ledger[m] for m in sorted(self.ledger)}, "sha_class": dict(sorted(self.ledger_sha_class.items()))}}
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def _write_state(self) -> None:
        if self.dry:
            raise DryModeError("no state file in dry mode")
        blob = self._state_blob()
        tmp = self._state_path().with_suffix(".tmp")
        tmp.write_bytes(blob)
        os.replace(tmp, self._state_path())
        self.state_sha = sha256_bytes(blob)

    def _load_state(self) -> None:
        p = self._state_path()
        if not p.exists():
            return
        raw = p.read_bytes()
        d = json.loads(raw)
        self.state_sha = sha256_bytes(raw)
        self.last_slot = d.get("last_slot")
        self.last_t = d["last_start"] if d.get("last_start") is not None else -math.inf
        self.processed_slots = set(d.get("processed_slots", ()))
        self.missing_slots = set(d.get("missing_slots", ()))
        self.seen = {int(x) for x in d.get("seen", ())}
        self.unit_ids = {str(x) for x in d.get("unit_ids", ())}
        led = d.get("rule_ledger") or {}
        self.ledger = {int(m): [list(r) for r in recs] for m, recs in (led.get("records") or {}).items()}
        self.ledger_sha_class = dict(led.get("sha_class") or {})

    def merge_rule_ledger(self) -> None:
        """Ruling 12: merge the retained day files' committed records into the append-only ledger (never pruned; a retired day file never changes
        a later unit's class). Called at the start of every pass."""
        for mid, recs in self.rules.by_mid.items():
            cur = self.ledger.setdefault(mid, [])
            have = {tuple(r) for r in cur}
            for r in recs:
                if tuple(r) not in have:
                    have.add(tuple(r))
                    cur.append(list(r))
        for sh, c in self.rules.sha_class.items():
            self.ledger_sha_class.setdefault(sh, c)

    # --- scanning one capture (no counters touched except notes / inputs) ------------------------------------------------------------
    def _scan(self, cap: dict, *, for_resume: bool = False) -> dict:
        d = Path(cap["dir"])
        start = cap["start"]
        for f in (d / "manifest.json", d / "rows.csv.gz", d / "rows_ext.csv.gz"):
            if f.exists() and not for_resume:
                self.inputs.append({"path": str(f), "bytes": f.stat().st_size, "sha256": sha256_file(f)})
        end_memo: dict = {}
        ends: dict = {}
        evc: Counter = Counter()
        cand: dict = {}
        overdue: list = []
        watch_cand: list = []
        end_missing: list = []
        watch_now: dict = {}
        unit_rows: dict = {}
        prev_watch = self.prev["watch"] if self.prev else {}
        follow_mids = {int(u.split(":")[1]) for u in self.unit_ids}
        it = iter_csv(d / "rows.csv.gz", ROW_COLS)
        pres = next(it, None)
        if pres is not None:
            for c, ok in zip(ROW_COLS, pres, strict=True):
                if not ok and not for_resume:
                    self.notes[f"rows_column_missing:{c}"] += 1
            for tup in it:
                try:
                    mid = int(tup[0])
                except ValueError:
                    continue
                es = tup[7]
                end_ts = end_memo.get(es)
                if end_ts is None:
                    end_ts = c240.parse_utc(es)
                    if len(end_memo) < 200000:
                        end_memo[es] = end_ts
                ends[mid] = end_ts
                closed_t = c240._truthy(tup[5])
                is_open = c240._truthy(tup[2]) and not closed_t and c240._truthy(tup[6])
                if is_open:
                    evc[tup[1] if str(tup[1]).strip() else f"market:{mid}"] += 1
                if mid in prev_watch:
                    watch_now[mid] = closed_t
                if mid in follow_mids:
                    unit_rows[mid] = (tup[5], tup[6], es)
                if end_ts != end_ts:
                    end_missing.append(mid)
                elif start - end_ts >= OVERDUE_S:
                    overdue.append(mid)
                    if mid not in self.seen:
                        cand[mid] = tup
                elif is_open and end_ts <= start + SLOT_MAX_FWD_S:
                    watch_cand.append(mid)
        uma: dict = {}
        ext: dict = {}
        ext_pres = None
        ext_p = d / "rows_ext.csv.gz"
        wanted = set(cand) | set(watch_cand) | set(end_missing) | set(unit_rows)
        if ext_p.exists():
            it2 = iter_csv(ext_p, EXT_COLS)
            ext_pres = next(it2, None)
            if ext_pres is not None:
                if not for_resume:
                    for c, ok in zip(EXT_COLS, ext_pres, strict=True):
                        if not ok:
                            self.notes[f"sidecar_column_missing:{c}"] += 1
                for row in it2:
                    try:
                        mid = int(row[0])
                    except ValueError:
                        continue
                    uma[mid] = sys.intern(row[2].strip()) if len(row[2]) < 64 else row[2].strip()
                    if mid in wanted:
                        ext[mid] = row
        elif not for_resume:
            self.notes["captures_without_sidecar"] += 1
        watch_next: dict = {}
        for mid in watch_cand:
            r = ext.get(mid)
            if r is not None and c240.category_of(r[4], r[5], r[6], True) == SCOPE:
                watch_next[mid] = ends[mid]
        return {"cap": cap, "start": start, "ends": ends, "uma": uma, "ext": ext, "ext_pres": ext_pres, "evc": evc, "cand": cand, "overdue": overdue,
                "end_missing": end_missing, "watch": watch_next, "watch_now": watch_now, "unit_rows": unit_rows}

    # --- feed ----------------------------------------------------------------------------------------------------------------------
    def feed(self, cap: dict) -> dict:
        if cap["start"] <= self.last_t:
            raise StateOrderError(f"captures must be fed strictly in time order: {cap['id']}")
        s = cap["slot"]
        if self.last_slot is not None and s <= self.last_slot:
            raise StateOrderError(f"slot {s} is not after the state's last folded slot {self.last_slot}")
        if self.last_slot is not None and self.last_slot != s - 1:
            raise StateOrderError(f"slot {s - 1} is neither processed nor recorded missing")
        sha_before = self.state_sha
        sc = self._scan(cap)
        start = cap["start"]
        in_window = start >= self.window_start and (self.window_end is None or start < self.window_end)
        after_window = self.window_end is not None and start >= self.window_end
        has_prev = self.prev is not None and self.prev["slot"] == s - 1
        classify = in_window and has_prev and self.prev["start"] >= self.window_start
        day = c240.day_of(start)
        new_units: list[dict] = []
        status: dict = {"capture_id": cap["capture_id"], "id": cap["id"], "slot": s, "start_utc": iso(start), "mode": "dry" if self.dry else "j1",
                        "classified": bool(classify), "fold_only": not classify and not after_window, "state_sha256_before": sha_before}
        local: Counter = Counter()
        self._cap_funnel = Counter()
        if after_window:
            local["after_window_followup_only"] += 1
        elif not in_window:
            local["pre_window_source"] += 1
        else:
            for u, n in Counter(sc["uma"].values()).items():
                f = str(u).strip().lower()
                if f in self.forms or len(self.forms) < FORMS_CAP:
                    self.forms[f] += n
                else:
                    self.forms_overflow += n
        if classify:
            new_units = self._classify(sc, day, local)
        elif in_window:
            # N1 / W15: every candidate at an in-window capture that is not classified is counted
            why = "k_minus_1_before_window" if has_prev else "no_previous_capture"
            for _ in sc["cand"]:
                self.funnel[why] += 1
                self.funnel_by_day[f"{day}|{why}"] += 1
                self._cap_funnel[why] += 1
        if not after_window:
            self.seen.update(sc["overdue"])
        # follow-up (blind; 9.2). Units created at this capture are not included (k < j).
        fu_info = None
        if not self.dry and self.record_followup and self.unit_ids and start < self.followup_until:
            fu_info = self._write_followup(cap, sc)
        for u in new_units:
            self.unit_ids.add(u["unit_id"])
        if not self.dry:
            if new_units:
                self._write_units(cap, new_units)
            else:
                self._write_units(cap, [])
        self.units.extend(new_units) if self.dry else None
        self.last_t, self.last_slot = start, s
        self.processed_slots.add(s)
        self.prev = {"slot": s, "start": start, "id": cap["id"], "ends": sc["ends"], "uma": sc["uma"], "watch": sc["watch"]}
        for k, v in local.items():
            self.extra[k] += v
        if classify:
            self.classified.append({"id": cap["id"], "start": start, "slot": s})
        if not self.dry:
            self._write_state()
            status.update({"counts": dict(sorted(local.items())), "funnel": dict(sorted(self._cap_funnel.items())), "units": len(new_units), "state_sha256_after": self.state_sha,
                           "followup": fu_info})
            self._write_status(cap, status)
        return status

    def _classify(self, sc: dict, day: str, local: Counter) -> list[dict]:
        start, prev = sc["start"], self.prev
        ext, evc = sc["ext"], sc["evc"]
        has_fe = bool(sc["ext_pres"][EXT_COLS.index("fees_enabled")]) if sc["ext_pres"] is not None else False

        def bump(cls: str) -> None:
            self.funnel[cls] += 1
            self._cap_funnel[cls] += 1
            self.funnel_by_day[f"{day}|{cls}"] += 1

        # counted side classes
        for mid in sc["end_missing"]:
            r = ext.get(mid)
            if r is not None and c240.category_of(r[4], r[5], r[6], True) == SCOPE:
                self.end_missing_by_day[day] += 1
                self.end_missing_markets.add(mid)
                local["end_date_missing"] += 1
        for mid in sc["overdue"]:
            if mid in self.seen:
                pe = prev["ends"].get(mid)
                if pe is not None and pe == pe and prev["start"] - pe < OVERDUE_S:
                    local["reoverdue_seen"] += 1
        for mid, end_p in sorted(prev["watch"].items()):
            if end_p <= start - OVERDUE_S and (mid not in sc["ends"] or sc["watch_now"].get(mid, False)):
                self.left_by_day[day] += 1
                local["left_before_overdue_slot"] += 1
        out: list[dict] = []
        for mid in sorted(sc["cand"]):
            tup = sc["cand"][mid]
            r = ext.get(mid)
            end_k = sc["ends"][mid]
            age_k = start - end_k
            pe = prev["ends"].get(mid) if mid in prev["ends"] else None
            cls = None
            if mid not in prev["ends"]:
                cls = "no_k_minus_1_row"
            elif pe is None or pe != pe:
                cls = "k_minus_1_end_date_missing"
            elif prev["start"] - pe >= OVERDUE_S:
                cls = "already_overdue_at_k_minus_1"
            elif f"m2:{mid}" in self.unit_ids:
                cls = "prior_unit"
            elif not (c240._truthy(tup[2]) and not c240._truthy(tup[5]) and c240._truthy(tup[6])):
                cls = "not_open_at_k"
            elif r is None:
                cls = "sidecar_missing"
            elif acc_state(r[3]) == "unknown":
                cls = "accepting_unknown"
            elif acc_state(r[3]) == "false":
                cls = "not_open_at_k"
            if cls is None:
                cat = c240.category_of(r[4], r[5], r[6], True)
                if cat != SCOPE:
                    cls = f"out_of_scope_{cat}"
            if cls is None:
                u = str(r[2]).strip().lower()
                if u not in EMPTY_FORMS:
                    cls = "uma_state_at_k" if "propos" in u else "uma_other_at_k"
                    self.forms_other[u] += 1
            bid, ask = (r6(c240._f(tup[3])), r6(c240._f(tup[4]))) if cls is None else (math.nan, math.nan)
            if cls is None and not (0 < bid < ask <= 1):
                cls = "not_two_sided"
            mid_k = math.nan
            if cls is None:
                mid_k = round((bid + ask) / 2.0, 6)
                if mid_k < MID_LO:
                    cls = "mid_low"
                elif mid_k > MID_HI:
                    cls = "mid_high"
                elif mid_k == 0.5:
                    cls = "no_favourite"
            bump(cls or "unit")
            if cls is not None:
                continue
            out.append(self._unit(sc, mid, tup, r, bid, ask, mid_k, end_k, age_k, pe, has_fe, evc, day))
        return out

    def _unit(self, sc, mid, tup, r, bid, ask, mid_k, end_k, age_k, end_prev, has_fe, evc, day) -> dict:
        cap, start, prev = sc["cap"], sc["start"], self.prev
        yes = mid_k > 0.5
        ask_f, bid_f, mid_f = (ask, bid, mid_k) if yes else (r6(1 - bid), r6(1 - ask), r6(1 - mid_k))
        spread = r6(ask - bid)
        half = spread / 2.0
        fc, fe, fsch = r[5], r[7], r[8]
        cat_k = costs.category_key(fc)
        row_rec, ext_rec = c240.parse_utc(tup[9]), c240.parse_utc(r[1])
        fin = [x for x in (row_rec, ext_rec) if math.isfinite(x)]
        t_d, t_d_src = (max(fin), "receipt") if fin else (start, "capture_start_fallback")
        k_day = c240.day_of(start)
        self.t_d_source[t_d_src] += 1
        rcls, rts = lookup_records(self.ledger.get(mid, ()), self.ledger_sha_class, t_d, k_day)
        self.rule_cov[f"{rcls}|{self.rules.last_row_class.get(mid, 'no_rules')}"] += 1
        self.cat_raw[f"{fc} -> {cat_k or '(empty)'}"] += 1
        oi = str(r[10]).strip().lower()
        self.oi_rows += 1
        if oi not in EMPTY_FORMS and oi not in ("null",):
            self.oi_nonempty += 1
        liq = c240._f(tup[8])
        ev = tup[1] if str(tup[1]).strip() else f"market:{mid}"
        moved = bool(end_prev is not None and end_prev == end_prev and abs(end_k - end_prev) > 1.0)
        wk = int((start - self.window_start) // 86400.0) // 7
        s1, s2 = s1_cell(liq), rcls
        fee = fee_lines(cat_k, fe, has_fe, fsch, ask_f)
        cells = {"S1": s1, "S2": s2, "S3": s3_cell(cat_k), "S4": c251.fee_class(fe, has_fe, fsch)[0], "S5": "YES" if yes else "NO", "S6": s6_cell(mid_f),
                 "S7": "yes" if moved else "no", "S8": s8_cell(evc[ev]), "S9": s9_cell(r[9]), "S10": f"days {7 * wk + 1}-{7 * wk + 7}", "S11": s11_cell(spread),
                 "S12": f"{s1}|{s2}"}
        return {"unit_id": f"m2:{mid}", "market_id": mid, "event_id": ev, "day": day, "k_start_utc": iso(start), "capture_id": cap["capture_id"], "capture_k_minus_1_id": prev["id"],
                "side": cells["S5"], "bid": bid, "ask": ask, "mid_k": mid_k, "bid_f": bid_f, "ask_f": ask_f, "mid_f": mid_f, "spread_k": spread, "half_spread": half,
                "tick": r[9], "event_open_binary_members": evc[ev], "end_date_k": end_k, "end_date_k_minus_1": end_prev, "age_k_s": age_k, "liquidity": liq,
                "open_interest_present": oi not in EMPTY_FORMS and oi != "null", "category": SCOPE, "cat_k": cat_k, "fee_category_raw": fc, **fee,
                "rule_class": rcls, "rule_commit_utc": rts, "t_d": t_d, "t_d_source": t_d_src, "gap_sidecar_minus_row_s": ext_rec - row_rec,
                "uma_raw_k": r[2], "uma_raw_k_minus_1": prev["uma"].get(mid), "cells": cells, "role": ROLE, "spec_sha": self.spec_sha, "code_sha": self.code_sha}

    # --- writers (J1 only; write-once, deterministic bytes) ----------------------------------------------------------------------------
    @staticmethod
    def _gz_bytes(lines: list[str]) -> bytes:
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
            gz.write(("".join(x + "\n" for x in lines)).encode())
        return buf.getvalue()

    def _write_once(self, p: Path, blob: bytes) -> None:
        if self.dry:
            raise DryModeError("no store in dry mode")
        if p.exists():
            raise FileExistsError(f"refusing to overwrite {p}")
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(blob)
        os.link(tmp, p)
        tmp.unlink()

    def _write_units(self, cap: dict, units: list[dict]) -> None:
        self._write_once(self.store / "units" / f"{cap['id']}.jsonl.gz", self._gz_bytes([json.dumps(u, sort_keys=True, default=str) for u in units]))

    def _write_status(self, cap: dict, status: dict) -> None:
        self._write_once(self.store / "status" / f"{cap['id']}.json", json.dumps(status, sort_keys=True, indent=1).encode())

    def _write_followup(self, cap: dict, sc: dict) -> dict:
        lines = []
        for uid in sorted(self.unit_ids):
            mid = int(uid.split(":")[1])
            row = sc["unit_rows"].get(mid)
            x = sc["ext"].get(mid)
            lines.append(json.dumps({"unit_id": uid, "capture_id": cap["capture_id"], "row_present": row is not None, "closed": row[0] if row else None,
                                     "active": row[1] if row else None, "end_date": row[2] if row else None,
                                     "accepting_orders": x[3] if x else None, "uma_raw": x[2] if x else None, "role": ROLE, "spec_sha": self.spec_sha,
                                     "code_sha": self.code_sha}, sort_keys=True))
        blob = self._gz_bytes(lines)
        self._write_once(self.store / "followup" / f"{cap['id']}.jsonl.gz", blob)
        return {"sha256": sha256_bytes(blob), "lines": len(lines)}

    # --- driving -------------------------------------------------------------------------------------------------------------------
    def rebuild_prev(self, caps_by_slot: dict) -> None:
        """Resume: the k - 1 state is re-read from the last folded capture when it is still on disk (otherwise k is ``no_previous_capture``)."""
        if self.last_slot is None or self.prev is not None:
            return
        cap = caps_by_slot.get(self.last_slot)
        if cap is None:
            self.notes["resume_prev_capture_gone"] += 1
            return
        sc = self._scan(cap, for_resume=True)
        self.prev = {"slot": cap["slot"], "start": cap["start"], "id": cap["id"], "ends": sc["ends"], "uma": sc["uma"], "watch": sc["watch"]}

    def run_available(self, caps: list[dict], now: float) -> list[dict]:
        """Process every capture that is next in slot order; a slot is recorded missing once it has no complete capture 6 h after its grid time;
        a capture appearing later stays unprocessed (``late_capture_ignored``). Stops at the first slot that may still arrive."""
        by_slot = {c["slot"]: c for c in sorted(caps, key=lambda c: c["start"])}
        self.merge_rule_ledger()
        for s in sorted(by_slot):
            if self.last_slot is not None and s <= self.last_slot and s not in self.processed_slots and s not in self.missing_slots:
                raise StateOrderError(f"the state holds a capture at or after slot {s} but slot {s} was never processed or recorded missing")
            if s in self.missing_slots:
                self.extra["late_capture_ignored"] += 1
        self.rebuild_prev(by_slot)
        if not by_slot:
            return []
        s = (self.last_slot + 1) if self.last_slot is not None else min(by_slot)
        if self.last_slot is None and self.lookback_from is not None:
            s = min(s, slot_of(self.lookback_from)[0])  # N4: look-back slots before the first retained capture are counted missing_lookback_slot
        top = max(by_slot)
        done: list[dict] = []
        while s <= top:
            c = by_slot.get(s)
            if c is not None and s not in self.missing_slots:
                done.append(self.feed(c))
            elif c is None and now >= slot_time(s) + MISSING_AFTER_S:
                self.missing_slots.add(s)
                self.last_slot = s
                self.extra["missing_lookback_slot" if slot_time(s) < self.window_start else "missing_capture"] += 1
                self.prev = None if self.prev is None or self.prev["slot"] != s - 1 else self.prev
                if not self.dry:
                    self._write_state()
            else:
                break
            s += 1
        return done

    # --- J0 report -----------------------------------------------------------------------------------------------------------------
    def report_j0(self, start_ts: float, end_ts: float, spec_path: Path | None, lookback_slots_used: int) -> dict:
        U = self.units
        caps_by_day = Counter(c240.day_of(c["start"]) for c in self.classified)
        full_days = sorted(d for d, n in caps_by_day.items() if n >= 12)
        per_day = Counter(u["day"] for u in U)
        med = None
        if full_days:
            v = sorted(per_day.get(d, 0) for d in full_days)
            n = len(v)
            med = float(v[n // 2]) if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0
        ev_units = Counter(u["event_id"] for u in U)
        info = self.rules.info
        pok = info["poll_ok"]
        rule_a = None if med is None else bool(med < DECISION_LINES["rule_a_extend_to_42_days_if_median_full_day_units_below"])
        rule_b = None if med is None else bool(med * 21 < DECISION_LINES["rule_b_record_only_projected_21_day_units_below"])
        rule_e = None if pok == 0 else bool(info["poll_ok_with_parseable_receipt"] == 0)  # computed, never a manual mode (N5)
        cells = {k: dict(sorted(Counter(u["cells"][k] for u in U).items())) for k in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12")}
        avg_caps = (READOUT_UTC - (REGISTERED_UTC + END_UTC) / 2.0) / GRID_S
        nfin = lambda x: x if (x is not None and math.isfinite(x)) else None  # noqa: E731
        gaps = sorted(g for g in (u["gap_sidecar_minus_row_s"] for u in U) if math.isfinite(g))
        return {
            "kind": "M2-J0 counts-only pre-freeze check (MEASUREMENT_M2_CH264.md 9.1): J1 code in dry mode; counts only, k = 0, uncounted; no resolution, outcome, follow-up state or post-k price read; no store written; informed (M2-J0)",
            "version": VERSION, "dry_run": True, "code_sha256": code_sha256(), "m2_j1_code_sha256": self.code_sha, "spec_sha256": sha256_file(spec_path) if spec_path and Path(spec_path).exists() else None,
            "pins": {"imported_module_sha256": module_pins(), "rule_lexicon_sha256": lexicon_sha256(), "note": "5 / MUST 2: recorded in J0's seal and at registration"},
            "rule_reader": "per-record receipt time (3.5, ruling 7): finished_utc <= t_d, else day file strictly before k's UTC day",
            "t_d_source_counts": dict(sorted(self.t_d_source.items())),
            "span": {"start_utc": iso(start_ts), "end_utc": iso(end_ts), "window_start_utc": iso(self.window_start), "lookback_slots_used": lookback_slots_used,
                     "lookback_slots_registered": LOOKBACK_SLOTS, "classified_captures": len(self.classified), "full_days": full_days,
                     "missing_slots_utc": [iso(slot_time(s)) for s in sorted(self.missing_slots)],
                     "note": "J0 reads the host's retained 8 days, so its fold (12 captures, fixed now, W9) is shorter than the registered 84-slot look-back; reoverdue_seen is understated and units slightly overstated at the start"},
            "decision_lines": DECISION_LINES,
            "decisions": {"median_full_day_units": med, "projected_21_day_units": None if med is None else med * 21, "rule_a_extend_to_42_days": rule_a,
                          "rule_b_record_only": rule_b, "rule_e_day_before_reader_applies": rule_e,
                          "note": "null = unavailable (no full day / no committed poll line), not a pass; J0's only effects are rules (a) and (e)"},
            "eligible_units": {"total": len(U), "per_day": dict(sorted(per_day.items())), "events": len(ev_units),
                               "units_per_event_strata": dict(sorted(Counter(units_bucket(n) for n in ev_units.values()).items())),
                               "note": "7.2 strata (1, 2-3, 4-9, 10+) with every unit treated as final-state; counts of events"},
            "funnel": {c: self.funnel.get(c, 0) for c in FUNNEL_ORDER} | {k: v for k, v in sorted(self.funnel.items()) if k not in FUNNEL_ORDER},
            "side_classes": {k: self.extra.get(k, 0) for k in ("reoverdue_seen", "end_date_missing", "left_before_overdue_slot", "pre_window_source", "missing_capture",
                                                               "missing_lookback_slot", "late_capture_ignored")},
            "funnel_by_day": dict(sorted(self.funnel_by_day.items())),
            "left_before_overdue_slot_by_day": dict(sorted(self.left_by_day.items())),
            "end_date_missing_scope_by_day": dict(sorted(self.end_missing_by_day.items())),
            "end_date_missing_scope_distinct_markets": len(self.end_missing_markets),
            "end_date_missing_note": "row-captures (every row of k with an unparseable end_date whose k sidecar row maps to scope), never a unit; distinct markets beside",
            "already_overdue_at_k_minus_1_note": "a guard class, expected 0; a non-zero count is printed and audited",
            "no_favourite": self.funnel.get("no_favourite", 0),
            "splits_counts": cells,
            "k_time_zone_counts": {"S6": cells["S6"], "S11": cells["S11"]},
            "cat_k_distribution": dict(sorted(Counter(u["cat_k"] or "(empty)" for u in U).items())),
            "fee_category_raw_to_cat_k": dict(self.cat_raw.most_common(100)),
            "rule_class_coverage_k_visible_vs_ch269_last_row": dict(sorted(self.rule_cov.items())),
            "rules_stream": {**info, "committed_poll_lines_carry_parseable_receipt_time": None if pok == 0 else info["poll_ok_with_parseable_receipt"] == pok},
            "status_forms": {"distinct_forms": dict(self.forms.most_common(FORMS_CAP)), "forms_overflow_rows": self.forms_overflow, "uma_other_at_k_forms": dict(self.forms_other.most_common())},
            "open_interest": {"units_with_nonempty_value": self.oi_nonempty, "units": self.oi_rows},
            "receipt_gap_sidecar_minus_row_s": {"n": len(gaps), "median": gaps[len(gaps) // 2] if gaps else None, "min": nfin(gaps[0]) if gaps else None, "max": nfin(gaps[-1]) if gaps else None},
            "planned_followup_volume": {"unit_capture_lines_per_unit_assuming_window_midpoint": round(avg_caps, 1), "projected_lines_21_days": None if med is None else round(med * 21 * avg_caps),
                                        "note": "units x captures to READOUT_UTC; counts only"},
            "notes": dict(sorted(self.notes.items())),
            "inputs": self.inputs,
            "not_printed": "no bid, ask, mid, liquidity value, resolution, label or outcome; prices enter only as S6 / S11 zone counts",
        }


# --- entry points ----------------------------------------------------------------------------------------------------------------------

def run_j0(snapshot_root: Path, rules_root: Path | None, start_ts: float, end_ts: float, *, lookback_slots: int = 12, spec_path: Path | None = None) -> dict:
    """M2-J0: the J1 extractor in dry mode over [start, end). The first ``lookback_slots`` captures only fold (the overdue-seen set); the rest are
    classified. The rule reader is per record (3.5); there is no mode to choose (N5)."""
    caps, notes = discover_captures(snapshot_root, start_ts, end_ts)
    rules = RulesIndex.load(rules_root)
    window_start = start_ts
    if caps and lookback_slots and lookback_slots < len(caps):
        window_start = caps[lookback_slots]["start"] - 1.0  # the first classified k needs k - 1 at or after window_start
    mp = M2Pass(window_start=window_start, window_end=None, rules=rules, dry_run=True, spec_sha=sha256_file(spec_path) if spec_path and Path(spec_path).exists() else "")
    mp.run_available(caps, now=math.inf)
    mp.notes.update({f"discover:{k}": v for k, v in notes.items()})
    rep = mp.report_j0(start_ts, end_ts, spec_path, lookback_slots)
    rep["peak_rss_mb"] = peak_rss_mb()
    return rep


def run_j1(snapshot_root: Path, rules_root: Path | None, store: Path, *, window_start: float = REGISTERED_UTC, window_end: float = END_UTC, spec_sha: str,
           now: float, record_followup: bool = True) -> M2Pass:
    """One J1 pass (9.2): the fixed look-back span ``[window_start - 7 d, window_start)`` and the window, then follow-up captures to READOUT."""
    caps, _ = discover_captures(snapshot_root, window_start - LOOKBACK_SLOTS * GRID_S, READOUT_UTC)
    mp = M2Pass(window_start=window_start, window_end=window_end, rules=RulesIndex.load(rules_root), dry_run=False, store=store,
                spec_sha=spec_sha, record_followup=record_followup, lookback_from=window_start - LOOKBACK_SLOTS * GRID_S)
    mp.run_available(caps, now=now)
    return mp
