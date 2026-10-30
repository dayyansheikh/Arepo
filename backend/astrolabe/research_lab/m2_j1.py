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
import time
from array import array
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import costs
from . import m2_spec as sp
from . import population_map_ch251 as c251

VERSION = "m2-j1-v2"
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


class StateOrderError(sp.M2Refusal):
    """The state file / capture order violates 9.2 (chronological processing), or the state no longer matches the code, spec or chain status."""


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
    """Per-file shas of the J0-era files (kept for J0's report) plus the combined ``code_sha`` of every M2 code file (``m2_spec.CODE_FILES``)."""
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


def decision_time(start: float, row_rec: float, ext_rec: float) -> tuple[float, str]:
    """3.3: the later of the row's and the sidecar's ``received_utc``; one alone if only one parses; else the capture's manifest start (counted)."""
    fin = [x for x in (row_rec, ext_rec) if math.isfinite(x)]
    return (max(fin), "receipt") if fin else (start, "capture_start_fallback")


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


def _day_end_ts(day: str) -> float:
    """Upper bound of a day file's commit times (day files are keyed by poll start): the UTC midnight that ends the file's day."""
    return datetime(int(day[:4]), int(day[4:6]), int(day[6:8]), tzinfo=UTC).timestamp() + 86400.0


def lookup_records(recs, sha_class: dict, t_d: float, k_day: str) -> tuple[str, float | None]:
    """(class, commit time) of the market's latest committed record visible at ``t_d`` (3.5, ruling 7). Each record has its own reader: a record
    with a parseable poll ``finished_utc`` is visible iff it is <= ``t_d``; a record without one is visible only if its day file's UTC day is
    strictly before k's UTC day. The latest record is chosen by COMMIT TIME, never by list position (code-freeze item 2): a record without a
    parseable time is ordered by the end of its day file, ties by position. No record -> ``no_rules``; a ``hash`` record resolves through any
    committed ``row`` with an equal sha (``sha_class``), else ``rules_unresolved``. ``gone`` records are never read."""
    kd = k_day.replace("-", "")
    best = None
    for pos, (ts, day, kind, cls_, sh) in enumerate(recs):
        if ts is not None:
            if not ts <= t_d:
                continue
            key = (ts, pos)
        elif not day < kd:
            continue
        else:
            key = (_day_end_ts(day), pos)
        if best is None or key > best[0]:
            best = (key, ts, kind, cls_, sh)
    if best is None:
        return "no_rules", None
    _key, ts, kind, cls_, sh = best
    if kind == "row":
        return cls_, ts
    return sha_class.get(sh) or "rules_unresolved", ts


class Ledger:
    """The append-only rule ledger of ruling 12 (never pruned; a retired day file never changes a later unit's class), in a compact columnar form so that a ledger of
    end-of-window size fits the 600 MB cap (final verification SHOULD 3). One record = (commit time or None, day file, kind row / hash, class, sha); the columns are
    ``array`` / ``bytearray`` / a list of packed shas, indexed per market. ``records`` decodes a market's records on demand (only unit candidates are looked up)."""

    KINDS = ("row", "hash")

    def __init__(self) -> None:
        self.ts = array("d")  # nan = no parseable commit time
        self.day = array("i")  # YYYYMMDD
        self.kind = bytearray()
        self.cls = bytearray()  # index into self.cls_names; 255 = none
        self.sha: list = []
        self.cls_names: list = []
        self.by_mid: dict = {}
        self.sha_class: dict = {}  # packed sha -> class code

    @staticmethod
    def pack_sha(s):
        if s is None:
            return None
        try:
            b = bytes.fromhex(s)
            return b if len(b) * 2 == len(s) and b.hex() == s else b"\xff" + s.encode()
        except ValueError:
            return b"\xff" + s.encode()

    @staticmethod
    def unpack_sha(b):
        if b is None:
            return None
        return b[1:].decode() if b[:1] == b"\xff" else b.hex()

    def _code(self, name):
        if name is None:
            return 255
        if name not in self.cls_names:
            self.cls_names.append(name)
        return self.cls_names.index(name)

    def append(self, mid: int, rec) -> None:
        ts, day, kind, cls_, sh = rec
        self.by_mid.setdefault(mid, array("I")).append(len(self.ts))
        self.ts.append(math.nan if ts is None else float(ts))
        self.day.append(int(day))
        self.kind.append(self.KINDS.index(kind))
        self.cls.append(self._code(cls_))
        self.sha.append(self.pack_sha(sh))

    def add_class(self, sh: str, cls_name: str) -> None:
        self.sha_class.setdefault(self.pack_sha(sh), self._code(cls_name))

    def records(self, mid: int) -> list:
        out = []
        for i in self.by_mid.get(mid, ()):
            t = self.ts[i]
            out.append((None if t != t else t, f"{self.day[i]:08d}", self.KINDS[self.kind[i]], None if self.cls[i] == 255 else self.cls_names[self.cls[i]], self.unpack_sha(self.sha[i])))
        return out

    def get(self, sh):
        """sha -> class name (the mapping interface :func:`lookup_records` uses)."""
        c = self.sha_class.get(self.pack_sha(sh))
        return None if c is None else self.cls_names[c]

    def markets(self) -> list:
        return sorted(self.by_mid)

    def n_markets(self) -> int:
        return len(self.by_mid)

    def n_records(self) -> int:
        return len(self.ts)

    def sha_items(self):
        return sorted((self.unpack_sha(k), self.cls_names[v]) for k, v in self.sha_class.items())


# --- discovery -----------------------------------------------------------------------------------------------------------------------

def discover_all(root: Path, start_ts: float, end_ts: float) -> dict:
    """Every complete capture (manifest ``state`` complete, rows present) with start in [start, end), sorted into: ``caps`` (the earliest-start ON-TIME
    capture of each 2 h slot, ordered by slot), ``extra`` (later on-time duplicates), ``late`` (not on time) and ``off`` (off-grid). On time (9.2, code-freeze
    item 1): the manifest's ``finished_utc`` is at most grid time + 6 h; a fact about the capture, never about when J1 runs. A manifest without a parseable
    ``finished_utc`` is not on time (M1 re-check R3). ``by_id`` holds every one of them by directory id (k - 1 is found by the id the chain folded)."""
    notes: Counter = Counter()
    by_slot: dict = {}
    extra: list = []
    late: list = []
    off: list = []
    by_id: dict = {}
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
        fin = c240.parse_utc(m.get("finished_utc"))
        c = {"id": p.parent.name, "capture_id": str(m.get("capture_id") or p.parent.name), "start": t, "slot": s, "dir": p.parent, "fin": fin, "fin_missing": not math.isfinite(fin)}
        by_id[c["id"]] = c
        if not on_grid:
            notes["off_grid"] += 1
            off.append(c)
            continue
        if c["fin_missing"] or fin > slot_time(s) + MISSING_AFTER_S:
            notes["late"] += 1
            late.append(c)
            continue
        cur = by_slot.get(s)
        if cur is None:
            by_slot[s] = c
        elif (t, c["id"]) < (cur["start"], cur["id"]):
            extra.append(cur)
            by_slot[s] = c
        else:
            extra.append(c)
        if cur is not None:
            notes["duplicate"] += 1
    return {"caps": [by_slot[k] for k in sorted(by_slot)], "extra": extra, "late": late, "off": off, "by_id": by_id, "notes": notes}


def discover_captures(root: Path, start_ts: float, end_ts: float) -> tuple[list[dict], Counter]:
    """The on-time first capture of each 2 h slot with start in [start, end), ordered by start, and the discovery notes (see :func:`discover_all`)."""
    d = discover_all(root, start_ts, end_ts)
    return d["caps"], d["notes"]


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
        self.ledger = Ledger()  # ruling 12: append-only rule ledger
        self.dry = dry_run
        self.store = Path(store) if store is not None else None
        self.spec_sha = spec_sha
        self.code_sha = sp.code_sha()  # the combined sha of every M2 code file (m2_spec.CODE_FILES), as M1
        self.record_followup = record_followup
        self.followup_until = followup_until if followup_until is not None else READOUT_UTC
        # chronological state
        self.last_t = -math.inf
        self.last_slot: int | None = None
        self.processed_slots: set = set()
        self.missing_slots: set = set()
        self.last_id: str | None = None  # directory id of the capture folded at last_slot (the chain's capture for k - 1); None after a missing slot
        self.last_kind = "init"
        self.slot_capture: dict = {}  # {str(slot): directory id} of the capture the chain folded in each processed slot
        self.seen: set = set()
        self.unit_ids: set = set()
        self.unit_events: dict = {}  # {unit_id: event_id at the unit's own k} (amendment 22: the S8 member count never reads an earlier unit's row after its k)
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
        self.nofav: list[dict] = []
        self.oi_nonempty = 0
        self.oi_rows = 0
        self.cat_raw: Counter = Counter()
        self.rule_cov: Counter = Counter()
        self.state_sha = "none"
        if self.store is not None:
            for sub in ("units", "status", "followup", "nofav"):
                (self.store / sub).mkdir(parents=True, exist_ok=True)
            self._load_state()

    # --- state file (J1 only) ----------------------------------------------------------------------------------------------------------
    def _state_path(self) -> Path:
        return self.store / "state.json"

    def _stage_state(self) -> str:
        """Write the state to ``state.json.tmp`` as JSON lines and return its sha256 (streamed; no whole-state blob in memory, so the 600 MB cap holds with a
        ledger of end-of-window size). Line 1: the header (counters and sets); then one ``{"m", "r"}`` line per market of the rule ledger and one ``{"s", "c"}`` line
        per sha-to-class entry, in a fixed order. The file is replaced into place by :meth:`_commit_staged` AFTER the unit, status and follow-up files are written,
        so a crash leaves the state at the previous slot and the re-run rewrites identical files (``_write_once`` accepts identical bytes)."""
        if self.dry:
            raise DryModeError("no state file in dry mode")
        h = hashlib.sha256()
        tmp = self._state_path().with_suffix(".tmp")
        head = {"version": VERSION, "spec_sha": self.spec_sha, "code_sha": self.code_sha, "last_slot": self.last_slot, "last_start": self.last_t if math.isfinite(self.last_t) else None,
                "last_capture_id": self.last_id, "last_kind": self.last_kind, "slot_capture": dict(sorted(self.slot_capture.items(), key=lambda kv: int(kv[0]))),
                "processed_slots": sorted(self.processed_slots), "missing_slots": sorted(self.missing_slots), "seen": sorted(self.seen), "unit_ids": sorted(self.unit_ids),
                "unit_events": dict(sorted(self.unit_events.items()))}
        with open(tmp, "wb") as fh:
            buf: list = []

            def put(line: str) -> None:
                buf.append(line)
                if len(buf) >= 4096:
                    flush()

            def flush() -> None:
                if buf:
                    b = ("\n".join(buf) + "\n").encode()
                    fh.write(b)
                    h.update(b)
                    buf.clear()

            put(json.dumps(head, sort_keys=True, separators=(",", ":")))
            for m in self.ledger.markets():
                put(json.dumps({"m": m, "r": self.ledger.records(m)}, separators=(",", ":")))
            for sh, c in self.ledger.sha_items():
                put(json.dumps({"s": sh, "c": c}, separators=(",", ":")))
            flush()
        return h.hexdigest()

    def _commit_staged(self, sha: str) -> None:
        os.replace(self._state_path().with_suffix(".tmp"), self._state_path())
        self.state_sha = sha

    def _write_state(self) -> None:
        if self.dry:
            raise DryModeError("no state file in dry mode")
        self._commit_staged(self._stage_state())

    def _load_state(self) -> None:
        p = self._state_path()
        if not p.exists():
            return
        h = hashlib.sha256()
        with open(p, "rb") as fh:  # streamed line by line: the ledger is never held twice
            for i, line in enumerate(fh):
                h.update(line)
                d = json.loads(line)
                if i == 0:
                    if d.get("code_sha") != self.code_sha or d.get("spec_sha") != self.spec_sha:
                        raise StateOrderError("the state file was written by a different code_sha or spec_sha: the code and spec are pinned for the whole window")
                    self.last_slot = d.get("last_slot")
                    self.last_t = d["last_start"] if d.get("last_start") is not None else -math.inf
                    self.last_id = d.get("last_capture_id")
                    self.last_kind = d.get("last_kind", "init")
                    self.slot_capture = {str(k): v for k, v in (d.get("slot_capture") or {}).items()}
                    self.processed_slots = set(d.get("processed_slots", ()))
                    self.missing_slots = set(d.get("missing_slots", ()))
                    self.seen = {int(x) for x in d.get("seen", ())}
                    self.unit_ids = {str(x) for x in d.get("unit_ids", ())}
                    self.unit_events = {str(k): str(v) for k, v in (d.get("unit_events") or {}).items()}
                elif "m" in d:
                    for r in d["r"]:
                        self.ledger.append(int(d["m"]), r)
                else:
                    self.ledger.add_class(d["s"], d["c"])
        self.state_sha = h.hexdigest()

    def pad_ledger(self, n_records: int, n_markets: int) -> None:
        """Host dry run only (code-freeze item 5, final verification SHOULD 3): fill the rule ledger with inert synthetic records for synthetic markets
        (negative ids, which no real market has) up to the planned END-of-window size, so the 600 MB cap is measured at the ledger size it will reach.
        Refused unless this is a dry-run spec (``run_pass`` checks); it never touches a real market's records."""
        for i in range(n_records):
            mid = -(i % n_markets) - 1
            kind = "row" if i % 3 == 0 else "hash"
            sh = f"{i:064x}"  # a valid hex sha, packed like a real one
            cls_ = ("barrier", "both", "other", "scheduled")[i % 4]
            self.ledger.append(mid, (1.0e9 + i, "19700101", kind, cls_ if kind == "row" else None, sh))
            if kind == "row":
                self.ledger.add_class(sh, cls_)

    def ledger_closed(self) -> bool:
        """True once the state has folded a slot at or after ``window_end``: the ledger is final and the rule day files are not read again."""
        return self.window_end is not None and self.last_slot is not None and slot_time(self.last_slot) >= self.window_end

    def merge_rule_ledger(self) -> None:
        """Ruling 12: merge the retained day files' committed records into the append-only ledger (never pruned; a retired day file never changes
        a later unit's class). Called at the start of every pass. Once the pass has folded a slot at or after ``window_end`` it stops: no further unit can
        be created (captures at or after END_UTC are follow-up only), so the ledger keeps its end-of-window size (code-freeze item 5)."""
        if self.ledger_closed():
            self.rules.by_mid = {}  # post-window: the index is never read again; hold no second copy (code-freeze check MUST 1)
            self.rules.sha_class = {}
            return
        for mid, recs in self.rules.by_mid.items():
            have = set(self.ledger.records(mid))
            for r in recs:
                r = tuple(r)
                if r not in have:
                    have.add(r)
                    self.ledger.append(mid, r)
        for sh, c in self.rules.sha_class.items():
            self.ledger.add_class(sh, c)
        self.rules.by_mid = {}  # the ledger holds every record from here on; free the second copy (memory cap)
        self.rules.sha_class = {}

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
                if is_open and mid not in follow_mids:  # an earlier unit's row at k is never read for the count; it is added from state below
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
        for uid in self.unit_ids:
            evc[self.unit_events[uid]] += 1  # every earlier unit of the event counts, by its event_id at its own k, even if it has left the listing
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
        sha_before, id_before = self.state_sha, self.last_id
        sc = self._scan(cap)
        start = cap["start"]
        in_window = start >= self.window_start and (self.window_end is None or start < self.window_end)
        after_window = self.window_end is not None and start >= self.window_end
        has_prev = self.prev is not None and self.prev["slot"] == s - 1
        classify = in_window and has_prev and self.prev["start"] >= self.window_start
        day = c240.day_of(start)
        new_units: list[dict] = []
        self.nofav = []
        status: dict = {"kind": "processed", "capture_id": cap["capture_id"], "id": cap["id"], "slot": s, "grid_utc": iso(slot_time(s)), "start_utc": iso(start),
                        "mode": "dry" if self.dry else "j1", "classified": bool(classify), "fold_only": not classify and not after_window,
                        "prev_capture_id": self.prev["id"] if has_prev else None, "last_capture_id_before": id_before, "state_sha256_before": sha_before}
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
            self.unit_events[u["unit_id"]] = u["event_id"]
        self.units.extend(new_units) if self.dry else None
        self.last_t, self.last_slot, self.last_id, self.last_kind = start, s, cap["id"], "processed"
        self.processed_slots.add(s)
        self.slot_capture[str(s)] = cap["id"]
        self.prev = {"slot": s, "start": start, "id": cap["id"], "ends": sc["ends"], "uma": sc["uma"], "watch": sc["watch"]}
        for k, v in local.items():
            self.extra[k] += v
        if classify:
            self.classified.append({"id": cap["id"], "start": start, "slot": s})
        if not self.dry:
            sha_after = self._stage_state()
            ub, nb = self._write_units(cap, new_units), self._write_nofav(cap)
            status.update({"counts": dict(sorted(local.items())), "funnel": dict(sorted(self._cap_funnel.items())), "units": len(new_units),
                           "unit_file_sha256": ub, "no_favourite": {"sha256": nb, "lines": len(self.nofav)}, "state_sha256_after": sha_after, "followup": fu_info,
                           "spec_sha": self.spec_sha, "code_sha": self.code_sha, "role": ROLE})
            self._write_status(cap, status)  # the status is written before the state: a crash in between re-runs the slot and rewrites identical bytes
            self._commit_staged(sha_after)
        return status

    def _record_missing(self, s: int) -> None:
        """Slot ``s`` has no on-time capture at grid + 6 h: it is recorded missing, with its own write-once status file so the sha chain has no gap
        (code-freeze item 3)."""
        sha_before, id_before = self.state_sha, self.last_id
        self.missing_slots.add(s)
        self.last_slot, self.last_id, self.last_kind = s, None, "missing"
        self.extra["missing_lookback_slot" if slot_time(s) < self.window_start else "missing_capture"] += 1
        self.prev = None
        if not self.dry:
            sha_after = self._stage_state()
            g = iso(slot_time(s))
            status = {"kind": "missing_capture", "slot": s, "grid_utc": g, "last_capture_id_before": id_before, "state_sha256_before": sha_before,
                      "state_sha256_after": sha_after, "spec_sha": self.spec_sha, "code_sha": self.code_sha, "role": ROLE}
            self._write_once(self.store / "status" / f"missing_{g.replace('-', '').replace(':', '')}.json", json.dumps(status, sort_keys=True, indent=1).encode())
            self._commit_staged(sha_after)

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
            if mid in self.seen and f"m2:{mid}" not in self.unit_ids:  # amendment 22: an earlier unit's end_date / k - 1 row is follow-up content
                pe = prev["ends"].get(mid)
                if pe is not None and pe == pe and prev["start"] - pe < OVERDUE_S:
                    local["reoverdue_seen"] += 1
                elif pe is None or pe != pe:
                    # code-freeze item 4 (section 21): a seen market overdue at k with no row at k - 1, or with an unparseable k - 1 end_date, falls in no
                    # class of the funnel; recorded here, over every category, as a recorded class only (it changes no unit).
                    local["seen_without_k_minus_1_row"] += 1
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
            if cls == "no_favourite":
                self.nofav.append(self._nofav_record(sc, mid, tup, r, bid, ask, mid_k))
            if cls is not None:
                continue
            out.append(self._unit(sc, mid, tup, r, bid, ask, mid_k, end_k, age_k, pe, has_fe, evc, day))
        return out

    def _nofav_record(self, sc, mid, tup, r, bid, ask, mid_k) -> dict:
        """E9 ``no_favourite`` (mid exactly 0.5): a k-time funnel class, never a unit and never in an estimand. Its market id is written (k-visible fields only)
        so the read-out can print its YES-resolved share and its fetch coverage separately (E9, 4, 8.4)."""
        start, cap = sc["start"], sc["cap"]
        t_d, src = decision_time(start, c240.parse_utc(tup[9]), c240.parse_utc(r[1]))
        return {"market_id": mid, "event_id": tup[1] if str(tup[1]).strip() else f"market:{mid}", "capture_id": cap["capture_id"], "k_start_utc": iso(start), "bid": bid, "ask": ask,
                "mid_k": mid_k, "t_d": t_d, "t_d_source": src, "role": ROLE, "spec_sha": self.spec_sha, "code_sha": self.code_sha}

    def _unit(self, sc, mid, tup, r, bid, ask, mid_k, end_k, age_k, end_prev, has_fe, evc, day) -> dict:
        cap, start, prev = sc["cap"], sc["start"], self.prev
        yes = mid_k > 0.5
        ask_f, bid_f, mid_f = (ask, bid, mid_k) if yes else (r6(1 - bid), r6(1 - ask), r6(1 - mid_k))
        spread = r6(ask - bid)
        half = spread / 2.0
        fc, fe, fsch = r[5], r[7], r[8]
        cat_k = costs.category_key(fc)
        row_rec, ext_rec = c240.parse_utc(tup[9]), c240.parse_utc(r[1])
        t_d, t_d_src = decision_time(start, row_rec, ext_rec)
        k_day = c240.day_of(start)
        self.t_d_source[t_d_src] += 1
        rcls, rts = lookup_records(self.ledger.records(mid), self.ledger, t_d, k_day)
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
        """Create ``p`` exclusively; an existing file is accepted only when its bytes are identical (idempotent re-run after a crash), else refused."""
        if self.dry:
            raise DryModeError("no store in dry mode")
        if p.exists():
            if p.read_bytes() == blob:
                return
            raise FileExistsError(f"refusing to overwrite {p}")
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(blob)
        os.link(tmp, p)
        tmp.unlink()

    def _write_units(self, cap: dict, units: list[dict]) -> str:
        blob = self._gz_bytes([json.dumps(u, sort_keys=True, default=str) for u in units])
        self._write_once(self.store / "units" / f"{cap['id']}.jsonl.gz", blob)
        return sha256_bytes(blob)

    def _write_nofav(self, cap: dict) -> str:
        blob = self._gz_bytes([json.dumps(u, sort_keys=True, default=str) for u in self.nofav])
        self._write_once(self.store / "nofav" / f"{cap['id']}.jsonl.gz", blob)
        return sha256_bytes(blob)

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
    def rebuild_prev(self, by_id: dict) -> None:
        """Resume: capture k - 1 is the capture the CHAIN folded in the last slot (its directory id, held by the state file and checked against that slot's chain
        status file), never a pick by slot: a later on-time capture of the same slot cannot replace it (code-freeze check, M1 MUST 1). When that capture is
        no longer on disk, k is ``no_previous_capture`` (E1, gone on resume)."""
        if self.last_slot is None or self.prev is not None or self.last_kind != "processed":
            return
        cap = by_id.get(self.last_id)
        if cap is None:
            self.notes["resume_prev_capture_gone"] += 1
            return
        if cap["slot"] != self.last_slot:
            raise StateOrderError(f"the state's last folded capture {self.last_id} is in slot {cap['slot']}, not slot {self.last_slot}")
        if self.store is not None:
            sp_ = self.store / "status" / f"{self.last_id}.json"
            if not sp_.exists() or json.loads(sp_.read_text()).get("slot") != self.last_slot:
                raise StateOrderError(f"the chain status of slot {self.last_slot} ({sp_.name}) is missing or names another slot")
        sc = self._scan(cap, for_resume=True)
        self.prev = {"slot": cap["slot"], "start": cap["start"], "id": cap["id"], "ends": sc["ends"], "uma": sc["uma"], "watch": sc["watch"]}

    def run_available(self, caps: list[dict], now: float, side: dict | None = None) -> list[dict]:
        """Process every capture that is next in slot order. A slot is DECIDED only once ``now >= grid + 6 h`` (the set of on-time captures, judged by the
        manifest's ``finished_utc`` <= grid + 6 h, is then final, whenever J1 runs); a decided slot with no on-time capture is recorded missing with its own
        status file; a capture appearing later stays unprocessed and is recorded as a late / duplicate side file. ``side`` is :func:`discover_all`'s output."""
        by_slot = {c["slot"]: c for c in sorted(caps, key=lambda c: c["start"])}
        by_id = (side or {}).get("by_id") or {c["id"]: c for c in caps}
        self.merge_rule_ledger()
        for s in sorted(by_slot):
            if self.last_slot is not None and s <= self.last_slot and s not in self.processed_slots and s not in self.missing_slots:
                raise StateOrderError(f"the state holds a capture at or after slot {s} but slot {s} was never processed or recorded missing")
        self.rebuild_prev(by_id)
        done: list[dict] = []
        if by_slot:  # no capture on disk at all (a misconfigured or unreadable root) must never record every slot missing
            s = (self.last_slot + 1) if self.last_slot is not None else min(by_slot)
            if self.last_slot is None and self.lookback_from is not None:
                s = min(s, slot_of(self.lookback_from)[0])  # N4: look-back slots before the first retained capture are counted missing_lookback_slot
            top = max(by_slot)
            if self.window_end is not None and not self.dry:
                last_follow = math.ceil((self.followup_until - GRID0) / GRID_S) - 1
                top = max(top, min(math.floor((now - MISSING_AFTER_S - GRID0) / GRID_S), last_follow))
            while s <= top:
                if now < slot_time(s) + MISSING_AFTER_S:
                    break  # the on-time set of the slot is not final yet
                c = by_slot.get(s)
                if c is not None:
                    done.append(self.feed(c))
                else:
                    self._record_missing(s)
                s += 1
        self._process_side(side, by_id)
        return done

    def _side_file(self, kind: str, name: str, payload: dict) -> None:
        """Write-once side status (late / duplicate / off-grid capture), counted once when first written (never re-added by a later run)."""
        key = {"late": "late_capture_ignored", "dup": "duplicate_slot_capture_ignored", "off": "off_grid_capture_ignored"}[kind]
        if self.dry:
            self.extra[key] += 1
            return
        p = self.store / "status" / f"{name}.json"
        if p.exists():
            return
        self._write_once(p, json.dumps(payload | {"role": ROLE}, sort_keys=True, indent=1).encode())
        self.extra[key] += 1

    def _process_side(self, side: dict | None, by_id: dict) -> None:
        """Captures that never enter the chain are counted in write-once status files, so J2's manifest carries them (not only an append log)."""
        if not side:
            return
        decided = self.processed_slots | self.missing_slots
        for c in side["late"]:
            if c["slot"] in decided:
                self._side_file("late", f"late_{c['id']}", {"kind": "late_capture_ignored", "capture_id": c["capture_id"], "id": c["id"], "slot": c["slot"],
                                                             "reason": "finished_utc_absent" if c["fin_missing"] else "finished_after_grid_plus_6h",
                                                             "capture_start_utc": iso(c["start"]), "finished_utc": None if c["fin_missing"] else iso(c["fin"])})
        for c in [*side["caps"], *side["extra"]]:
            s = c["slot"]
            kept_id = self.slot_capture.get(str(s))
            if s in self.missing_slots:
                why = "delivered_after_missing_recorded"
            elif s in self.processed_slots and kept_id is not None and c["id"] != kept_id:
                kept = by_id.get(kept_id)
                why = "on_time_but_delivered_after_slot_decided" if kept is not None and c["start"] < kept["start"] else None
                if why is None:
                    self._side_file("dup", f"dup_{c['id']}", {"kind": "duplicate_slot_capture_ignored", "capture_id": c["capture_id"], "id": c["id"], "slot": s,
                                                              "kept_id": kept_id, "capture_start_utc": iso(c["start"])})
                    continue
            else:
                continue
            self._side_file("late", f"late_{c['id']}", {"kind": "late_capture_ignored", "capture_id": c["capture_id"], "id": c["id"], "slot": s, "reason": why,
                                                         "capture_start_utc": iso(c["start"]), "finished_utc": iso(c["fin"])})
        for c in side["off"]:
            self._side_file("off", f"offgrid_{c['id']}", {"kind": "off_grid_capture_ignored", "capture_id": c["capture_id"], "id": c["id"], "nearest_slot": c["slot"],
                                                           "capture_start_utc": iso(c["start"])})

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
            "version": VERSION, "dry_run": True, "code_sha256": code_sha256(), "m2_j1_code_sha256": sha256_file(Path(__file__).resolve()), "code_sha": self.code_sha, "spec_sha256": sha256_file(spec_path) if spec_path and Path(spec_path).exists() else None,
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
            "side_classes": {k: self.extra.get(k, 0) for k in ("reoverdue_seen", "seen_without_k_minus_1_row", "end_date_missing", "left_before_overdue_slot", "pre_window_source",
                                                               "missing_capture", "missing_lookback_slot", "late_capture_ignored", "duplicate_slot_capture_ignored",
                                                               "off_grid_capture_ignored")},
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
    info = discover_all(snapshot_root, start_ts, end_ts)
    caps, notes = info["caps"], info["notes"]
    rules = RulesIndex.load(rules_root)
    window_start = start_ts
    if caps and lookback_slots and lookback_slots < len(caps):
        window_start = caps[lookback_slots]["start"] - 1.0  # the first classified k needs k - 1 at or after window_start
    mp = M2Pass(window_start=window_start, window_end=None, rules=rules, dry_run=True, spec_sha=sha256_file(spec_path) if spec_path and Path(spec_path).exists() else "")
    mp.run_available(caps, now=math.inf, side=info)
    mp.notes.update({f"discover:{k}": v for k, v in notes.items()})
    rep = mp.report_j0(start_ts, end_ts, spec_path, lookback_slots)
    rep["peak_rss_mb"] = peak_rss_mb()
    return rep


def run_j1(snapshot_root: Path, rules_root: Path | None, store: Path, *, window_start: float = REGISTERED_UTC, window_end: float = END_UTC, spec_sha: str,
           now: float, record_followup: bool = True, followup_until: float | None = None, pad_ledger: tuple[int, int] | None = None) -> M2Pass:
    """One J1 pass (9.2): the fixed look-back span ``[window_start - 7 d, window_start)`` and the window, then follow-up captures to READOUT. ``spec_sha`` is
    given by the caller (the registered runner passes the pinned one); see :func:`run_pass` for the gated entry point."""
    fu = READOUT_UTC if followup_until is None else followup_until
    info = discover_all(snapshot_root, window_start - LOOKBACK_SLOTS * GRID_S, fu)
    mp = M2Pass(window_start=window_start, window_end=window_end, rules=None, dry_run=False, store=store,
                spec_sha=spec_sha, record_followup=record_followup, lookback_from=window_start - LOOKBACK_SLOTS * GRID_S, followup_until=fu)
    if not mp.ledger_closed():  # post-window passes never read the rule day files (the ledger is final): no second copy is loaded (MUST 1)
        mp.rules = RulesIndex.load(rules_root)
    if pad_ledger and mp.last_slot is None:
        mp.pad_ledger(*pad_ledger)
    mp.run_available(info["caps"], now=now, side=info)
    mp.notes.update({f"discover:{k}": v for k, v in info["notes"].items()})
    return mp


def run_pass(snapshot_root: Path, rules_root: Path | None, store: Path, spec: dict = sp.SPEC, now: float | None = None, pins: dict | None = None, paths: dict | None = None,
             design: Path | None = None, record_followup: bool = True, pad_ledger: tuple[int, int] | None = None) -> dict:
    """The registered J1 entry point. Refuses on a pin mismatch (design text, eight modules, lexicon; spec_sha / code_sha against ``pins`` at every pass), before
    ``REGISTERED_UTC`` (the first pass folds the look-back and must see the span), once the follow-up manifest exists, and a ledger pad outside a dry-run spec.
    Appends one line to ``logs/j1_runs.jsonl`` (counts, peak RSS; no follow-up content)."""
    sp.check_pins(spec, paths, design)
    sp.check_run_pins(pins, spec)
    now = time.time() if now is None else now
    reg, end = sp.ts(spec, "registered_utc"), sp.ts(spec, "end_utc")
    if now < reg:
        raise sp.M2Refusal(f"J1 refuses before REGISTERED_UTC ({spec['registered_utc']}): the first pass folds the look-back span and must see every pre-window capture")
    if pad_ledger and not spec.get("dry_run"):
        raise sp.M2Refusal("a rule-ledger pad is for the host dry run only")
    store = Path(store)
    if (store / "followup_manifest.json").exists():
        raise sp.M2Refusal("J1 refuses: the follow-up is closed (followup_manifest.json exists)")
    mp = run_j1(snapshot_root, rules_root, store, window_start=reg, window_end=end, spec_sha=sp.spec_sha(spec), now=now, record_followup=record_followup,
                followup_until=sp.ts(spec, "readout_utc"), pad_ledger=pad_ledger)
    rec = {"now_utc": iso(now), "peak_rss_mb": peak_rss_mb(), "spec_sha": mp.spec_sha, "code_sha": mp.code_sha, "last_slot": mp.last_slot, "processed_slots": len(mp.processed_slots),
           "missing_slots": len(mp.missing_slots), "units_total": len(mp.unit_ids), "counts": dict(sorted(mp.extra.items())), "ledger_markets": mp.ledger.n_markets(), "ledger_records": mp.ledger.n_records()}
    (store / "logs").mkdir(parents=True, exist_ok=True)
    with open(store / "logs" / "j1_runs.jsonl", "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec
