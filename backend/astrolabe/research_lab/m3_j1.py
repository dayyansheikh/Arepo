# ruff: noqa: E501
"""M3 (CH274, "the wait") J1 window-time extractor and blind follow-up recorder, and its J0 dry mode (sections 3.2-3.5, 10.1 and 10.2 of
``docs/research_lab/MEASUREMENT_M3_CH274.md``).

One class, :class:`M3Pass`, folds complete 2-hourly captures in strict chronological order. For each capture k of the window it classifies the markets whose row is
newly near-certain (favoured ask >= 0.95 with the favoured mid >= 0.90 on a two-sided row, or the one-sided firm-bound forms of 3.2) and that were never near-certain at any
earlier processed capture of the look-back span or the window (E1-E8, every exclusion a counted class); a candidate passing every rule is a unit.

* ``dry_run=True`` is M3-J0: counts only in memory; no units store, no state file, no follow-up file and no proposal-set file (it refuses a store path). Nothing after a
  hypothetical unit's k is read for that unit: a market in the near-seen set is skipped without parsing its prices (the extractor never reads such a row's content again).
* ``dry_run=False`` is J1: write-once ``units/<capture_id>.jsonl.gz``, ``status/<capture_id>.json`` (funnel, side counts, state sha256 chain; for the blind files only their
  sha256 and line count), ``followup/<capture_id>.jsonl.gz`` and ``proposals/<capture_id>.json.gz`` (blind: written, never read by the extractor) and ``state.json``.

Only E026-frozen ``costs.py`` and the pinned CH240 / CH251 / CH269 readers are imported (read only). The five rule patterns are copied verbatim (3.5). Nothing here reads a book
sweep, a trade, an engine store, a resolution or any Gamma outcome field.
"""

from __future__ import annotations

import base64
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
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import census_map_ch269 as c269
from . import costs
from . import m3_spec as sp
from . import population_map_ch251 as c251

VERSION = "m3-j1-v1"
ROLE = sp.ROLE
REGISTERED_UTC = sp.ts(sp.SPEC, "registered_utc")
END_UTC = sp.ts(sp.SPEC, "end_utc")
READOUT_UTC = sp.ts(sp.SPEC, "readout_utc")
GRID0 = sp.grid0(sp.SPEC)
GRID_S = sp.SPEC["grid_s"]
TOL_S = sp.SPEC["tol_s"]
MISSING_AFTER_S = float(sp.SPEC["missing_after_grid_s"])
LOOKBACK_SLOTS = sp.SPEC["lookback_slots"]
RULES_FIRST_DAY = sp.SPEC["rules_first_day"]
SCOPE = sp.SPEC["scope"]
NEAR_ASK, NEAR_MID = sp.SPEC["near_ask"], sp.SPEC["near_mid"]
ONE_SIDED_BID, ONE_SIDED_ASK = sp.SPEC["one_sided_bid"], sp.SPEC["one_sided_ask"]
MIN_END_S, MIN_AGE_S = sp.SPEC["min_end_s"], sp.SPEC["min_age_s"]
EMPTY_FORMS = tuple(sp.SPEC["empty_forms"])  # E6 whitelist (CH269's empty forms; copied, not imported)
P_TOKENS = tuple(sp.SPEC["followup_p_tokens"])
TIER_NAMES = c269.TIER_NAMES
S9_KEYS = ("economics", "culture", "weather", "other", "finance", "politics", "mentions", "tech", "geopolitics")
CLASSED = ("scheduled", "barrier", "both", "consensus", "other")
ROW_COLS = ("market_id", "event_id", "binary", "best_bid", "best_ask", "closed", "active", "end_date", "liquidity", "received_utc")
EXT_COLS = ("market_id", "received_utc", "uma_resolution_statuses", "accepting_orders", "created_at", "fee_type", "fee_category", "series_slugs", "fees_enabled", "fee_schedule",
            "order_price_min_tick_size", "neg_risk_market_id")
FUNNEL_ORDER = ("no_previous_capture", "k_minus_1_before_window", "near_seen_but_candidate", "prior_unit", "first_near_one_sided", "left_censored_first_row", "no_k_minus_1_row",
                "k_minus_1_not_two_sided", "ask_not_crossed", "not_open_at_k", "sidecar_missing", "accepting_unknown", "out_of_scope_sports", "out_of_scope_crypto",
                "out_of_scope_unknown", "uma_state_at_k", "uma_other_at_k", "end_date_missing", "end_within_24h", "created_at_missing", "created_at_after_k", "young_at_k", "unit")

# The five rule patterns, copied verbatim (3.5; signal_engine/rules_text.py and census_map_ch269.py). The sha256 of the five strings is a spec pin.
_MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
SCHEDULED_RE = re.compile(r"\b(scheduled|fomc|federal reserve|cpi|consumer price index|jobs report|nonfarm|unemployment rate|gdp|earnings|box office|election|vote|referendum|certified|official (?:results?|data|release|figures?)|will be (?:released|published|announced)|press release)\b")
BARRIER_RE = re.compile(r"\b(at any point|at any time|any time|reach(?:es)?|hits?|touch(?:es)?|dips?|exceeds?|before|by (?:january|february|march|april|may|june|july|august|september|october|november|december|the end of))\b")
CONSENSUS_RE = re.compile(r"\b(consensus of credible reporting|credible report(?:ing|s)|credible sources?)\b")
OCCUR_Q_RE = re.compile(rf"\b(?:by|before) (?:the end of |end of )?(?:{_MONTHS}|20\d\d|q[1-4]\b)")
OCCUR_D_RE = re.compile(r"\bbetween (?:the )?(?:market(?:'s)? creation|creation of (?:this|the) market)\b")
LEXICON = (SCHEDULED_RE, BARRIER_RE, CONSENSUS_RE, OCCUR_Q_RE, OCCUR_D_RE)


class DryModeError(Exception):
    """A dry (J0) pass was asked to write a store."""


class StateOrderError(sp.M3Refusal):
    """The state file / capture order violates 10.2 (chronological processing), or the state no longer matches the code, spec or chain status."""


# --- small helpers ---------------------------------------------------------------------------------------------------------------------

sha256_file, sha256_bytes = sp.sha256_file, sp.sha256_bytes


def lexicon_sha256() -> str:
    return sha256_bytes("\n".join(p.pattern for p in LEXICON).encode())


def module_pins() -> dict:
    """sha256 of every imported module whose function sets an eligibility class, split cell or outcome class (12.5)."""
    d = Path(__file__).resolve().parent
    return {n: (sha256_file(d / n) if (d / n).exists() else None) for n in sp.PINNED_MODULES}


def r6(x: float) -> float:
    return round(x, 6) if math.isfinite(x) else x


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


def acc_state(v) -> str:
    s = str(v).strip().lower()
    return "true" if s in ("true", "1", "1.0", "t") else "false" if s in ("false", "0", "0.0", "f") else "unknown"


def is_p_form(s: str) -> bool:
    """4.1: a whole token ``proposed`` / ``disputed`` / ``resolved`` after splitting on non-letters and lower-casing."""
    return any(t in P_TOKENS for t in re.split(r"[^a-z]+", str(s).lower()))


# --- 3.2: usable prices, the book on a row, the near-certain state ----------------------------------------------------------------------

def usable(v) -> float | None:
    """A touch value is usable iff it parses finite and, rounded to 6 dp, lies strictly in (0, 1): an ask of 1.0 or a bid of 0 is not a resting order (M1 D6)."""
    x = r6(c240._f(v))
    return x if (math.isfinite(x) and 0.0 < x < 1.0) else None


def read_book(bid_s, ask_s) -> tuple[str, float | None, float | None]:
    """(kind, bid, ask): two_sided (both usable, bid < ask), crossed (both usable, bid >= ask), bid_only, ask_only, unparseable (neither usable)."""
    b, a = usable(bid_s), usable(ask_s)
    if b is not None and a is not None:
        return ("two_sided" if b < a else "crossed"), b, a
    if b is not None:
        return "bid_only", b, None
    if a is not None:
        return "ask_only", None, a
    return "unparseable", None, None


def fav_prices(side: str, bid: float, ask: float) -> tuple[float, float, float]:
    """(ask_f, bid_f, mid_f) on the favoured side, each rounded to 6 dp (3.4)."""
    mid = round((bid + ask) / 2.0, 6)
    return (ask, bid, mid) if side == "YES" else (r6(1.0 - bid), r6(1.0 - ask), r6(1.0 - mid))


def near_side(kind: str, bid: float | None, ask: float | None) -> tuple[str, str] | None:
    """(side, how) when the row is in the near-certain state N (3.2 (i) two-sided; (ii) one-sided beyond the line), else None."""
    if kind == "two_sided":
        for side in ("YES", "NO"):
            ask_f, _bid_f, mid_f = fav_prices(side, bid, ask)
            if ask_f >= NEAR_ASK and mid_f >= NEAR_MID:
                return side, "two_sided"
        return None
    if kind == "bid_only" and bid >= ONE_SIDED_BID:
        return "YES", "bid_only_ge_095"
    if kind == "ask_only" and ask <= ONE_SIDED_ASK:
        return "NO", "ask_only_le_005"
    return None


def wide_book_high_ask(bid: float, ask: float) -> bool:
    """A two-sided row with a favoured ask >= 0.95 whose favoured mid is below 0.90 (side count)."""
    for side in ("YES", "NO"):
        ask_f, _b, mid_f = fav_prices(side, bid, ask)
        if ask_f >= NEAR_ASK and mid_f < NEAR_MID:
            return True
    return False


# --- cells (8) --------------------------------------------------------------------------------------------------------------------------

def s4_cell(h_s: float) -> str:
    h = round(h_s, 3)
    return "[1 d, 3 d)" if h < 3 * 86400.0 else "[3 d, 14 d)" if h < 14 * 86400.0 else "[14 d, 43 d)" if h < 43 * 86400.0 else ">= 43 d"


def s8_cell(n: int) -> str:
    return "1" if n <= 1 else "2-5" if n <= 5 else "6+"


def s9_cell(cat_k: str) -> str:
    return cat_k if cat_k in S9_KEYS else "unknown"


def s11_cell(ask_f: float) -> str:
    a = r6(ask_f)
    for lo, hi in ((0.95, 0.96), (0.96, 0.97), (0.97, 0.98), (0.98, 0.99)):
        if a < hi:
            return f"[{lo:.2f},{hi:.2f})"
    return "[0.99,1)"


def s12_cell(tick) -> str:
    t = r6(c240._f(tick))
    return "0.001" if t == 0.001 else "0.01" if t == 0.01 else "other_or_missing"


def s13_cell(start: float, window_start: float) -> str:
    wk = int((start - window_start) // 86400.0) // 7
    return f"days {7 * wk + 1}-{7 * wk + 7}"


def units_bucket(n: int) -> str:
    return "1" if n <= 1 else "2-3" if n <= 3 else "4-9" if n <= 9 else "10+"


def decision_time(start: float, row_rec: float, ext_rec: float) -> tuple[float, str]:
    """3.4: the later of the row's and the sidecar's ``received_utc``; one alone if only one parses; else the capture's manifest start (counted)."""
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
    """6.1: L1 (conservative; ``fees_enabled`` passed as False only for a literal served false, else None) and L2 (docs rate with the flag ignored; ``MAX_TAKER_RATE`` for a key
    outside the docs table), per share at p = ask_f."""
    rate, _ = c251.fee_parse(fee_schedule)
    sched = rate if math.isfinite(rate) else None
    served = has_fe_col and str(fees_enabled).strip() != ""
    fe_arg = False if (served and acc_state(fees_enabled) == "false") else None
    exp = fee_exponent(fee_schedule)
    r1 = costs.taker_rate(cat_k, sched, fe_arg, policy="conservative")
    r2 = costs.taker_rate(cat_k, sched, None, policy="conservative") if cat_k in costs.CATEGORY_TAKER_RATE else costs.MAX_TAKER_RATE
    return {"rate_l1": r1, "rate_l2": r2, "exponent": exp, "schedule_rate": sched, "fees_enabled_arg": fe_arg,
            "fee_l1": costs.taker_fee_ps(ask_f, r1, exp), "fee_l2": costs.taker_fee_ps(ask_f, r2, exp)}


# --- rule text index and ledger (3.5) ---------------------------------------------------------------------------------------------------

def classify_rule(data: dict) -> str:
    """``"<S2 class>/<occur_by>"`` of one ``m:`` row's data: the five patterns on question + description + resolutionSource lower-cased (S2) and the deadline flag (S3)."""
    q, d, src = (str(data.get(k) or "") for k in ("question", "description", "resolutionSource"))
    t = " ".join((q, d, src)).lower()
    s, b, c = bool(SCHEDULED_RE.search(t)), bool(BARRIER_RE.search(t)), bool(CONSENSUS_RE.search(t))
    cls = "scheduled" if s and not b else "barrier" if b and not s else "both" if s and b else "consensus" if c else "other"
    occ = "1" if (OCCUR_Q_RE.search(q.lower()) or OCCUR_D_RE.search(d.lower())) else "0"
    return f"{cls}/{occ}"


class RulesIndex:
    """Per market, the committed ``row`` / ``hash`` records of the keyless ``gamma_rules`` day files in file order, each with the commit time of the ``poll`` line that follows it
    (``finished_utc``). Text is classified and dropped. Rows of a slot without a following ``ok`` poll line are torn and ignored. ``days`` lists the day files read."""

    def __init__(self) -> None:
        self.by_mid: dict = {}
        self.sha_class: dict = {}
        self.days: list = []
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
            ix.days.append(day)
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
                            pending.append((d.get("slot"), mid, "row", classify_rule(data), d.get("sha")))
                        else:
                            pending.append((d.get("slot"), mid, "hash", None, d.get("sha")))
                    elif kind == "poll":
                        ix.info["poll_lines"] += 1
                        if d.get("ok") is True:
                            ix.info["poll_ok"] += 1
                            t = c240.parse_utc(d.get("finished_utc"))
                            if math.isfinite(t):
                                ix.info["poll_ok_with_parseable_receipt"] += 1
                                if c240.day_of(t).replace("-", "") != day:
                                    ix.info["commits_crossing_midnight"] += 1  # day files are keyed by poll start (streams/common.py:366)
                                t0 = c240.parse_utc(d.get("started_utc"))
                                if math.isfinite(t0) and t >= t0:
                                    ix.info["max_poll_duration_s"] = max(ix.info["max_poll_duration_s"] or 0.0, t - t0)
                            slot = d.get("slot")
                            for sl, mid, k2, cls_, sh in pending:
                                if sl != slot:
                                    ix.info["rows_torn_or_failed"] += 1
                                    continue
                                if not math.isfinite(t):
                                    ix.info["records_without_receipt"] += 1
                                ix.by_mid.setdefault(mid, []).append((t if math.isfinite(t) else None, day, k2, cls_, sh))
                                ix.info["rows_committed" if k2 == "row" else "hash_committed"] += 1
                                if k2 == "row" and sh:
                                    ix.sha_class[sh] = cls_
                        else:
                            ix.info["rows_torn_or_failed"] += len(pending)
                        pending = []
            ix.info["rows_torn_or_failed"] += len(pending)
        ix.info["markets"] = len(ix.by_mid)
        return ix


def _day_end_ts(day: str) -> float:
    """Upper bound of a day file's commit times (day files are keyed by poll start): the UTC midnight that ends the file's day."""
    return datetime(int(day[:4]), int(day[4:6]), int(day[6:8]), tzinfo=UTC).timestamp() + 86400.0


def lookup_records(recs, sha_class, t_d: float, k_day: str) -> tuple[str, float | None, str | None]:
    """(class string, commit time, day file) of the market's latest committed record visible at ``t_d`` (3.5). Each record has its own reader: a record with a parseable poll
    ``finished_utc`` is visible iff it is <= ``t_d``; a record without one is visible only if its day file's UTC day is strictly before k's UTC day. The latest record is chosen by
    COMMIT TIME, ties by day file, then by the record's position within the ledger (the line order of its file), never by list position alone (M2 final SHOULD 2). A record without a
    parseable time sorts at the end of its day file's UTC day. No record -> ``no_rules``; a ``hash`` record resolves through any committed ``row`` with an equal sha (``sha_class``),
    else ``rules_unresolved``. ``gone`` records are never read."""
    kd = k_day.replace("-", "")
    best = None
    for pos, (ts, day, kind, cls_, sh) in enumerate(recs):
        if ts is not None:
            if not ts <= t_d:
                continue
            key = (ts, day, pos)
        elif not day < kd:
            continue
        else:
            key = (_day_end_ts(day), day, pos)
        if best is None or key > best[0]:
            best = (key, ts, day, kind, cls_, sh)
    if best is None:
        return "no_rules", None, None
    _key, ts, day, kind, cls_, sh = best
    if kind == "row":
        return cls_, ts, day
    return sha_class.get(sh) or "rules_unresolved", ts, day


class Ledger:
    """The append-only rule ledger (never pruned; a retired day file never changes a later unit's class), in a compact columnar form so that a ledger of end-of-window size fits
    the 600 MB cap. One record = (commit time or None, day file, kind row / hash, class string, sha); the columns are ``array`` / ``bytearray`` / a list of packed shas, indexed per
    market. ``records`` decodes a market's records on demand (only unit candidates are looked up)."""

    KINDS = ("row", "hash")

    def __init__(self) -> None:
        self.ts = array("d")  # nan = no parseable commit time
        self.day = array("i")  # YYYYMMDD
        self.kind = bytearray()
        self.cls = bytearray()  # index into self.cls_names; 255 = none
        self.sha: list = []
        self.cls_names: list = []
        self.by_mid: dict = {}
        self.sha_class: dict = {}

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

    def get(self, sh, default=None):
        """sha -> class string (the mapping interface :func:`lookup_records` uses)."""
        c = self.sha_class.get(self.pack_sha(sh))
        return default if c is None else self.cls_names[c]

    def markets(self) -> list:
        return sorted(self.by_mid)

    def n_markets(self) -> int:
        return len(self.by_mid)

    def n_records(self) -> int:
        return len(self.ts)

    def sha_items(self):
        return sorted((self.unpack_sha(k), self.cls_names[v]) for k, v in self.sha_class.items())


def day_range(first: str, last: str) -> list[str]:
    """Every UTC day 'YYYYMMDD' from ``first`` to ``last`` inclusive (empty if ``last`` < ``first``)."""
    a = datetime(int(first[:4]), int(first[4:6]), int(first[6:8]), tzinfo=UTC)
    b = datetime(int(last[:4]), int(last[4:6]), int(last[6:8]), tzinfo=UTC)
    out = []
    while a <= b:
        out.append(a.strftime("%Y%m%d"))
        a += timedelta(days=1)
    return out


# --- discovery ---------------------------------------------------------------------------------------------------------------------------

def discover_all(root: Path, start_ts: float, end_ts: float, window_start: float | None = None) -> dict:
    """Every complete capture (manifest ``state`` complete, rows present) with start in [start, end), sorted into: ``caps`` (the first on-time capture of each 2 h slot by the
    ``(start, id)`` key, ordered by slot), ``extra`` (later on-time duplicates), ``late`` (not on time) and ``off`` (off-grid). On time (10.2): the manifest's ``finished_utc`` is at
    most grid time + 6 h; a fact about the capture, never about when J1 runs. A manifest without a parseable ``finished_utc`` is not on time. ``by_id`` holds every one of them by
    directory id (k - 1 is found by the id the chain folded). Pre-window manifests that exist but are not complete are counted (``pre_window_manifest_not_complete``)."""
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
        if not math.isfinite(t) or not (start_ts <= t < end_ts):
            continue
        if m.get("state") != "complete":
            notes["manifest_not_complete"] += 1
            if window_start is not None and t < window_start:
                notes["pre_window_manifest_not_complete"] += 1
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
    d = discover_all(root, start_ts, end_ts)
    return d["caps"], d["notes"]


def audit_chain(store: Path) -> dict:
    """Verify the sha256 chain of the status files (10.2): ordered by slot, each processed / missing status names the state sha before it equal to the previous one's sha after it,
    and the capture id before it equal to the previous slot's capture id (None after a missing slot). Raises :class:`StateOrderError` on a breach; returns counts."""
    sts = []
    for p in sorted((Path(store) / "status").glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except ValueError as e:
            raise StateOrderError(f"status file {p.name} is not valid JSON") from e
        if d.get("kind") in ("processed", "missing_capture"):
            sts.append(d)
    sts.sort(key=lambda d: d["slot"])
    prev_sha, prev_id, prev_slot = "none", None, None
    by_slot: dict = {}
    for d in sts:
        if prev_slot is not None and d["slot"] != prev_slot + 1:
            raise StateOrderError(f"status chain gap: slot {d['slot']} follows slot {prev_slot}")
        if d["state_sha256_before"] != prev_sha:
            raise StateOrderError(f"status chain breach at slot {d['slot']}: state_sha256_before does not equal the previous state_sha256_after")
        if d["last_capture_id_before"] != prev_id:
            raise StateOrderError(f"status chain breach at slot {d['slot']}: last_capture_id_before is not the previous slot's capture")
        prev_sha, prev_slot = d["state_sha256_after"], d["slot"]
        prev_id = d.get("id") if d["kind"] == "processed" else None
        by_slot[d["slot"]] = (d["state_sha256_before"], d["state_sha256_after"])
    return {"statuses": len(sts), "last_slot": prev_slot, "last_state_sha256": prev_sha, "by_slot": by_slot}


# --- the pass ----------------------------------------------------------------------------------------------------------------------------

class M3Pass:
    """Folds captures strictly in time order (10.2). See the module docstring for dry (J0) versus J1."""

    def __init__(self, *, window_start: float, window_end: float | None = None, rules: RulesIndex | None = None, lookback_from: float | None = None, dry_run: bool = True,
                 store: Path | None = None, spec_sha: str = "", record_followup: bool = True, record_proposals: bool = True, followup_until: float | None = None) -> None:
        if dry_run and store is not None:
            raise DryModeError("dry mode (M3-J0) writes no units store, no state file, no follow-up file and no proposal-set file")
        if not dry_run and store is None:
            raise ValueError("J1 needs a store directory")
        self.window_start, self.window_end = window_start, window_end
        self.rules = rules or RulesIndex()
        self.lookback_from = lookback_from
        self.ledger = Ledger()
        self.merged_days: set = set()
        self.dry = dry_run
        self.store = Path(store) if store is not None else None
        self.spec_sha = spec_sha
        self.code_sha = sp.code_sha()
        self.record_followup, self.record_proposals = record_followup, record_proposals
        self.followup_until = followup_until if followup_until is not None else READOUT_UTC
        # chronological state
        self.last_t = -math.inf
        self.last_slot: int | None = None
        self.processed_slots: set = set()
        self.missing_slots: set = set()
        self.last_id: str | None = None  # directory id of the capture folded at last_slot (the chain's capture for k - 1); None after a missing slot
        self.last_kind = "init"
        self.slot_capture: dict = {}
        self.near_seen: set = set()
        self.near_seen_in_scope = 0
        self.ever_seen: set = set()
        self.unit_meta: dict = {}  # market id -> [side, k slot, k capture directory id]
        self.prev: dict | None = None
        # counts
        self.funnel: Counter = Counter()
        self.funnel_by_day: Counter = Counter()
        self.extra: Counter = Counter()
        self.sub: Counter = Counter()
        self.forms_e6: Counter = Counter()
        self.forms_other: Counter = Counter()
        self.end_missing_by_day: Counter = Counter()
        self.end_missing_markets: set = set()
        self.t_d_source: Counter = Counter()
        self.cat_raw: Counter = Counter()
        self.cand_cat: Counter = Counter()
        self.side_by_day: Counter = Counter()
        self.notes: Counter = Counter()
        self._cap_funnel: Counter = Counter()
        self.units: list[dict] = []
        self.classified: list[dict] = []
        self.state_sha = "none"
        if self.store is not None:
            for sub in ("units", "status", "followup", "proposals", "logs"):
                (self.store / sub).mkdir(parents=True, exist_ok=True)
            self._load_state()

    @property
    def unit_ids(self) -> set:
        return {f"m3:{m}" for m in self.unit_meta}

    # --- state file (J1 only) -------------------------------------------------------------------------------------------------------------
    def _state_path(self) -> Path:
        return self.store / "state.json"

    def _stage_state(self) -> str:
        """Write the state to ``state.json.tmp`` as JSON lines and return its sha256 (streamed). Line 1: the header (counters, sets, units); then one ``{"m", "r"}`` line per market of
        the rule ledger and one ``{"s", "c"}`` line per sha-to-class entry, in a fixed order. :meth:`_commit_staged` replaces it into place AFTER the unit, status and blind files
        are written, so a crash leaves the state at the previous slot and the re-run rewrites identical files (``_write_once`` accepts identical bytes)."""
        if self.dry:
            raise DryModeError("no state file in dry mode")
        h = hashlib.sha256()
        tmp = self._state_path().with_suffix(".tmp")
        head = {"version": VERSION, "spec_sha": self.spec_sha, "code_sha": self.code_sha, "last_slot": self.last_slot, "last_start": self.last_t if math.isfinite(self.last_t) else None,
                "last_capture_id": self.last_id, "last_kind": self.last_kind, "slot_capture": dict(sorted(self.slot_capture.items(), key=lambda kv: int(kv[0]))),
                "processed_slots": sorted(self.processed_slots), "missing_slots": sorted(self.missing_slots), "merged_days": sorted(self.merged_days),
                "near_seen": sorted(self.near_seen), "near_seen_in_scope": self.near_seen_in_scope, "ever_seen": sorted(self.ever_seen),
                "units": {str(m): v for m, v in sorted(self.unit_meta.items())}}
        with open(tmp, "wb") as fh:
            buf: list = []

            def flush() -> None:
                if buf:
                    b = ("\n".join(buf) + "\n").encode()
                    fh.write(b)
                    h.update(b)
                    buf.clear()

            def put(line: str) -> None:
                buf.append(line)
                if len(buf) >= 4096:
                    flush()

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

    def _load_state(self) -> None:
        p = self._state_path()
        if not p.exists():
            rec = audit_chain(self.store)  # status files without a state file: a deleted state is a breach; one first status is the crash window (status written, state not yet)
            if rec["statuses"] > 1 or (rec["statuses"] == 1 and rec["by_slot"][rec["last_slot"]][0] != "none"):
                raise StateOrderError("the state file is missing but the status chain is not empty: the state was deleted")
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
                    self.merged_days = {str(x) for x in d.get("merged_days", ())}
                    self.near_seen = {int(x) for x in d.get("near_seen", ())}
                    self.near_seen_in_scope = int(d.get("near_seen_in_scope", 0))
                    self.ever_seen = {int(x) for x in d.get("ever_seen", ())}
                    self.unit_meta = {int(m): list(v) for m, v in (d.get("units") or {}).items()}
                elif "m" in d:
                    for r in d["r"]:
                        self.ledger.append(int(d["m"]), r)
                else:
                    self.ledger.add_class(d["s"], d["c"])
        self.state_sha = h.hexdigest()
        rec = audit_chain(self.store)
        if self.last_slot is None:
            ok = rec["statuses"] == 0 or (rec["statuses"] == 1 and rec["by_slot"][rec["last_slot"]][0] == "none")
        else:
            at = rec["by_slot"].get(self.last_slot)
            ahead = [s for s in rec["by_slot"] if s > self.last_slot]
            ok = at is not None and at[1] == self.state_sha and (not ahead or (ahead == [self.last_slot + 1] and rec["by_slot"][ahead[0]][0] == self.state_sha))
        if not ok:
            raise StateOrderError("the state file does not match the status chain (its sha256 differs from the last state_sha256_after): the state was edited or a status is missing")

    def pad_state(self, ledger_pad: tuple[int, int] | None, set_pad: tuple[int, int] | None) -> None:
        """Host dry run only (20 step 8): fill the rule ledger, the ever-seen set and the near-seen set with inert synthetic entries (negative ids, which no real market has) up to the
        planned END-of-window size, so the 600 MB cap is measured at that size. ``run_pass`` refuses it outside a dry-run spec; it never touches a real market."""
        if ledger_pad:
            n_records, n_markets = ledger_pad
            for i in range(n_records):
                mid = -(i % n_markets) - 1
                kind = "row" if i % 3 == 0 else "hash"
                sh = f"{i:064x}"
                cls_ = ("barrier/0", "both/1", "other/0", "scheduled/1")[i % 4]
                self.ledger.append(mid, (1.0e9 + i, "19700101", kind, cls_ if kind == "row" else None, sh))
                if kind == "row":
                    self.ledger.add_class(sh, cls_)
        if set_pad:
            n_ever, n_near = set_pad
            self.ever_seen.update(-(i + 1) for i in range(n_ever))
            self.near_seen.update(-(i + 1) for i in range(n_near))

    def merge_rule_ledger(self) -> None:
        """Merge the retained day files' committed records into the append-only ledger (never pruned) and record which day files were merged (the source of ``rules_gap``).
        Called at the start of every pass. Once the pass has folded a slot at or after ``window_end`` it stops: no further unit can be created (captures at or after END_UTC are
        follow-up only), so the ledger keeps its end-of-window size."""
        if self.window_end is not None and self.last_slot is not None and slot_time(self.last_slot) >= self.window_end:
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
        self.merged_days.update(self.rules.days)
        self.rules.by_mid = {}  # the ledger holds every record from here on; free the second copy (memory cap)
        self.rules.sha_class = {}

    def unmerged_days(self, k_day: str) -> list[str]:
        """Day files in [RULES_FIRST_DAY, k's day] that were never merged (3.5)."""
        kd = k_day.replace("-", "")
        return [d for d in day_range(RULES_FIRST_DAY, kd) if d not in self.merged_days] if kd >= RULES_FIRST_DAY else []

    def rule_at(self, mid: int, t_d: float, k_day: str) -> dict:
        """The S2 / S3 reading at ``t_d`` (3.5): latest visible record by commit time; ``rules_gap`` only for a unit with no visible record when a day file was never merged."""
        cls_s, ts, day = lookup_records(self.ledger.records(mid), self.ledger, t_d, k_day)
        gaps = self.unmerged_days(k_day)
        if cls_s == "no_rules":
            return {"cls": "rules_gap" if gaps else "no_rules", "occ": "na", "ts": None, "day": None, "unmerged": len(gaps), "visible": False}
        if cls_s == "rules_unresolved":
            return {"cls": cls_s, "occ": "na", "ts": ts, "day": day, "unmerged": len(gaps), "visible": True}
        cls, occ = cls_s.split("/")
        return {"cls": cls, "occ": occ, "ts": ts, "day": day, "unmerged": len(gaps), "visible": True}

    # --- scanning one capture ---------------------------------------------------------------------------------------------------------------
    def _scan(self, cap: dict, *, fold: bool = True, for_resume: bool = False, want_proposals: bool = False) -> dict:
        """Read capture ``cap``. A market already in the near-seen set is never parsed (its content after its entry is read only for the blind follow-up of a unit). Counters are
        not touched here (only ``notes`` for missing columns, and not on resume)."""
        d = Path(cap["dir"])
        near = self.near_seen
        unit_mids = self.unit_meta
        seen_now: list = []
        book: dict = {}
        cand: dict = {}
        unit_rows: dict = {}
        evc: Counter = Counter()
        crossed = wide = 0
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
                    if not for_resume:
                        self.notes["rows_unparseable_market_id"] += 1
                    continue
                if mid in unit_mids:
                    unit_rows[mid] = tup
                if not fold:
                    continue
                seen_now.append(mid)
                if c240._truthy(tup[2]) and not c240._truthy(tup[5]) and c240._truthy(tup[6]):
                    evc[tup[1] if str(tup[1]).strip() else f"market:{mid}"] += 1
                if mid in near:
                    continue
                book[mid] = (tup[3], tup[4])
                kind, b, a = read_book(tup[3], tup[4])
                if kind == "crossed":
                    crossed += 1
                    continue
                ns = near_side(kind, b, a)
                if ns is not None:
                    cand[mid] = (tup, ns[0], ns[1], kind, b, a)
                elif kind == "two_sided" and wide_book_high_ask(b, a):
                    wide += 1
        uma: dict = {}
        ext: dict = {}
        p_new: list = []
        ext_pres = None
        ext_p = d / "rows_ext.csv.gz"
        wanted = set(cand) | set(unit_rows)
        prev_uma = self.prev["uma"] if (want_proposals and self.prev) else None
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
                    u = row[2].strip()
                    uma[mid] = sys.intern(u) if len(u) < 64 else u
                    if mid in wanted:
                        ext[mid] = row
                    if prev_uma is not None and mid in prev_uma and prev_uma[mid].lower() in EMPTY_FORMS and is_p_form(u):
                        if c240.category_of(row[5], row[6], row[7], True) == SCOPE:
                            p_new.append(mid)
        elif not for_resume:
            self.notes["captures_without_sidecar"] += 1
        return {"cap": cap, "start": cap["start"], "seen_now": seen_now, "book": book, "cand": cand, "unit_rows": unit_rows, "evc": evc, "crossed": crossed, "wide": wide,
                "uma": uma, "ext": ext, "ext_pres": ext_pres, "p_new": sorted(p_new)}

    # --- feed -------------------------------------------------------------------------------------------------------------------------------
    def feed(self, cap: dict) -> dict:
        if cap["start"] <= self.last_t:
            raise StateOrderError(f"captures must be fed strictly in time order: {cap['id']}")
        s = cap["slot"]
        if self.last_slot is not None and s <= self.last_slot:
            raise StateOrderError(f"slot {s} is not after the state's last folded slot {self.last_slot}")
        if self.last_slot is not None and self.last_slot != s - 1:
            raise StateOrderError(f"slot {s - 1} is neither processed nor recorded missing")
        start = cap["start"]
        in_window = start >= self.window_start and (self.window_end is None or start < self.window_end)
        after_window = self.window_end is not None and start >= self.window_end
        if not self.dry and not after_window and (self.store / "manifest.json").exists():
            raise sp.M3Refusal("J1 refuses an extractor write: the unit manifest exists (the unit set is closed; J1 continues as the recorder only)")
        sha_before, id_before = self.state_sha, self.last_id
        notes_before = Counter(self.notes)
        has_prev = self.prev is not None and self.prev["slot"] == s - 1
        classify = in_window and has_prev and self.prev["start"] >= self.window_start
        want_prop = bool(in_window and has_prev and self.record_proposals and not self.dry)
        sc = self._scan(cap, fold=not after_window, want_proposals=want_prop)
        day = c240.day_of(start)
        new_units: list[dict] = []
        status: dict = {"kind": "processed", "capture_id": cap["capture_id"], "id": cap["id"], "slot": s, "grid_utc": iso(slot_time(s)), "start_utc": iso(start),
                        "mode": "dry" if self.dry else "j1", "classified": bool(classify), "fold_only": not classify and not after_window,
                        "prev_capture_id": self.prev["id"] if has_prev else None, "last_capture_id_before": id_before, "state_sha256_before": sha_before}
        local: Counter = Counter()
        self._cap_funnel = Counter()
        if after_window:
            local["after_window_followup_only"] += 1
        else:
            if not in_window:
                local["pre_window_source"] += 1
            local["crossed_book"] += sc["crossed"]
            local["wide_book_high_ask"] += sc["wide"]
            if classify:
                new_units = self._classify(sc, day, local)
            else:
                for mid in sorted(sc["cand"]):
                    if in_window:
                        why = "k_minus_1_before_window" if has_prev else "no_previous_capture"
                        self._bump(why, day)
                    elif mid not in self.ever_seen:
                        local["left_censored_first_row_pre_window"] += 1
            # every candidate enters the near-seen set at k, whether or not it becomes a unit (one-shot); the in-scope part is read from capture k's own sidecar row
            for mid in sorted(sc["cand"]):
                r = sc["ext"].get(mid)
                self.near_seen.add(mid)
                if r is not None and c240.category_of(r[5], r[6], r[7], True) == SCOPE:
                    self.near_seen_in_scope += 1
            self.ever_seen.update(sc["seen_now"])
            for mid in sc["cand"]:
                sc["book"].pop(mid, None)
            local["near_seen_size"] = len(self.near_seen)
            local["near_seen_in_scope"] = self.near_seen_in_scope
        # blind recorders (10.2). Units created at this capture are not included (k < j).
        fu_info = pr_info = None
        if not self.dry and self.record_followup and self.unit_meta and start < self.followup_until:
            fu_info = self._write_followup(cap, sc)
        if want_prop:
            pr_info = self._write_proposals(cap, sc)
        for u in new_units:
            self.unit_meta[u["market_id"]] = [u["side"], s, cap["id"]]
        if self.dry:
            self.units.extend(new_units)
        self.last_t, self.last_slot, self.last_id, self.last_kind = start, s, cap["id"], "processed"
        self.processed_slots.add(s)
        self.slot_capture[str(s)] = cap["id"]
        if not after_window:
            self.prev = {"slot": s, "start": start, "id": cap["id"], "rows": sc["book"], "uma": sc["uma"]}
        else:
            self.prev = None
        for k, v in local.items():
            if k not in ("near_seen_size", "near_seen_in_scope"):
                self.extra[k] += v
        if classify:
            self.classified.append({"id": cap["id"], "start": start, "slot": s})
        if not self.dry:
            sha_after = self._stage_state()
            ub = self._write_units(cap, new_units)
            cap_notes = {k: v - notes_before.get(k, 0) for k, v in sorted(self.notes.items()) if v - notes_before.get(k, 0)}  # missing columns, no sidecar, unparseable ids: counted per capture
            status.update({"counts": dict(sorted(local.items())), "funnel": dict(sorted(self._cap_funnel.items())), "notes": cap_notes, "units": len(new_units), "unit_file_sha256": ub,
                           "state_sha256_after": sha_after, "followup": fu_info, "proposals": pr_info, "spec_sha": self.spec_sha, "code_sha": self.code_sha, "role": ROLE})
            self._write_status(cap, status)  # the status is written before the state: a crash in between re-runs the slot and rewrites identical bytes
            self._commit_staged(sha_after)
        return status

    def _record_missing(self, s: int) -> None:
        """Slot ``s`` has no on-time capture at grid + 6 h: it is recorded missing, with its own write-once status file so the sha chain has no gap."""
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

    def _bump(self, cls: str, day: str) -> None:
        self.funnel[cls] += 1
        self._cap_funnel[cls] += 1
        self.funnel_by_day[f"{day}|{cls}"] += 1

    def _classify(self, sc: dict, day: str, local: Counter) -> list[dict]:
        start, prev = sc["start"], self.prev
        ext = sc["ext"]
        has_fe = bool(sc["ext_pres"][EXT_COLS.index("fees_enabled")]) if sc["ext_pres"] is not None else False
        out: list[dict] = []
        for mid in sorted(sc["cand"]):
            tup, side, how, _kind, bid, ask = sc["cand"][mid]
            r = ext.get(mid)
            cat = c240.category_of(r[5], r[6], r[7], True) if r is not None else "no_sidecar"
            self.cand_cat[cat] += 1
            local["candidates"] += 1
            cls = None
            sub = None
            if mid in self.near_seen:
                cls = "near_seen_but_candidate"  # guard, expected 0
            elif mid in self.unit_meta:
                cls = "prior_unit"  # guard, expected 0
            # E2 first near state is two-sided
            elif how != "two_sided":
                cls, sub = "first_near_one_sided", how
            else:
                # E3 crossing at k - 1
                pr = prev["rows"].get(mid)
                if pr is None:
                    cls = "no_k_minus_1_row" if mid in self.ever_seen else "left_censored_first_row"
                    if cls == "left_censored_first_row":
                        sub = "in_window"
                else:
                    k1, b1, a1 = read_book(*pr)
                    if k1 != "two_sided":
                        cls, sub = "k_minus_1_not_two_sided", {"bid_only": "one_sided", "ask_only": "one_sided", "crossed": "crossed", "unparseable": "unparseable"}[k1]
                    elif fav_prices(side, b1, a1)[0] >= NEAR_ASK:
                        cls = "ask_not_crossed"  # the side's ask was already at 0.95 or more at k - 1 (N failed on the mid clause: a wide book)
            # E4 open / sidecar / accepting
            if cls is None:
                if not (c240._truthy(tup[2]) and not c240._truthy(tup[5]) and c240._truthy(tup[6])):
                    cls = "not_open_at_k"
                elif r is None:
                    cls = "sidecar_missing"
                elif acc_state(r[3]) == "unknown":
                    cls = "accepting_unknown"
                elif acc_state(r[3]) == "false":
                    cls = "not_open_at_k"
            # E5 scope
            if cls is None and cat != SCOPE:
                cls = f"out_of_scope_{cat}" if cat in ("sports", "crypto") else "out_of_scope_unknown"
            # E6 empty UMA status (whitelist)
            if cls is None:
                u = str(r[2]).strip().lower()
                self.forms_e6[u] += 1
                if u not in EMPTY_FORMS:
                    cls = "uma_state_at_k" if "propos" in u else "uma_other_at_k"
                    self.forms_other[u] += 1
            t_d, t_d_src, row_rec, ext_rec = start, "capture_start_fallback", math.nan, math.nan
            end_k = math.nan
            if cls is None:
                row_rec, ext_rec = c240.parse_utc(tup[9]), c240.parse_utc(r[1])
                t_d, t_d_src = decision_time(start, row_rec, ext_rec)
                # E7 end more than 24 h away
                end_k = c240.parse_utc(tup[7])
                if end_k != end_k:
                    cls = "end_date_missing"
                    self.end_missing_by_day[day] += 1
                    self.end_missing_markets.add(mid)
                elif not (end_k - t_d > MIN_END_S):
                    cls = "end_within_24h"
            # E8 age
            created = math.nan
            if cls is None:
                created = c240.parse_utc(r[4])
                if created != created:
                    cls = "created_at_missing"
                elif created > start:
                    cls = "created_at_after_k"
                elif not (start - created >= MIN_AGE_S):
                    cls = "young_at_k"
            self._bump(cls or "unit", day)
            if sub is not None:
                self.sub[f"{cls}:{sub}"] += 1
                local[f"{cls}:{sub}"] += 1
            if cls is not None:
                continue
            out.append(self._unit(sc, mid, tup, r, side, bid, ask, end_k, t_d, t_d_src, row_rec, ext_rec, created, has_fe, day, local))
        return out

    def _unit(self, sc, mid, tup, r, side, bid, ask, end_k, t_d, t_d_src, row_rec, ext_rec, created, has_fe, day, local) -> dict:
        cap, start, prev = sc["cap"], sc["start"], self.prev
        ask_f, bid_f, mid_f = fav_prices(side, bid, ask)
        mid_k = round((bid + ask) / 2.0, 6)
        spread = r6(ask - bid)
        half = spread / 2.0
        b1, a1 = prev["rows"][mid]
        _k1, bid1, ask1 = read_book(b1, a1)
        ask_f_prev = fav_prices(side, bid1, ask1)[0]
        fc, fe, fsch = r[6], r[8], r[9]
        cat_k = costs.category_key(fc)
        k_day = c240.day_of(start)
        self.t_d_source[t_d_src] += 1
        local[f"t_d_source:{t_d_src}"] += 1
        self.cat_raw[f"{fc} -> {cat_k or '(empty)'}"] += 1
        rl = self.rule_at(mid, t_d, k_day)
        if rl["visible"] and rl["unmerged"]:
            local["classed_with_gap"] += 1
        liq = c240._f(tup[8])
        ev = tup[1] if str(tup[1]).strip() else f"market:{mid}"
        n_open = sc["evc"][ev]
        h_s = end_k - t_d
        s2 = rl["cls"]
        s4 = s4_cell(h_s)
        tier = TIER_NAMES[c269.tier_of(liq)]
        cells = {"S1": tier, "S2": s2, "S3": rl["occ"], "S4": s4, "S5": f"{s2}|{s4}", "S6": "standalone" if n_open <= 1 else ("member_yes" if side == "YES" else "member_no"),
                 "S7": side, "S8": s8_cell(n_open), "S9": s9_cell(cat_k), "S10": c251.fee_class(fe, has_fe, fsch)[0], "S11": s11_cell(ask_f), "S12": s12_cell(r[10]),
                 "S13": s13_cell(start, self.window_start)}
        fee = fee_lines(cat_k, fe, has_fe, fsch, ask_f)
        return {"unit_id": f"m3:{mid}", "market_id": mid, "event_id": ev, "event_id_raw": tup[1], "day": day, "k_start_utc": iso(start), "capture_id": cap["capture_id"],
                "capture_k_id": cap["id"], "capture_k_minus_1_id": prev["id"], "k_slot": cap["slot"], "side": side, "bid": bid, "ask": ask, "mid_k": mid_k, "bid_f": bid_f,
                "ask_f": ask_f, "mid_f": mid_f, "spread_k": spread, "half_spread": half, "c_discount": r6(1.0 - ask_f), "ask_f_k_minus_1": ask_f_prev, "tick": r[10],
                "event_open_binary_members": n_open, "neg_risk_market_id": r[11], "liquidity": liq, "tier": tier, "created_at": r[4], "age_k_s": start - created,
                "category": SCOPE, "cat_k": cat_k, "fee_category_raw": fc, **fee, "rule_class": s2, "occur_by": rl["occ"], "rule_commit_utc": rl["ts"],
                "rule_commit_day_file": rl["day"], "rules_days_unmerged": rl["unmerged"], "end_date_k": end_k, "end_date_k_raw": tup[7], "hours_to_end_s": h_s, "t_d": t_d,
                "t_d_source": t_d_src, "gap_sidecar_minus_row_s": ext_rec - row_rec, "uma_raw_k": r[2], "uma_raw_k_minus_1": prev["uma"].get(mid), "cells": cells, "role": ROLE,
                "spec_sha": self.spec_sha, "code_sha": self.code_sha}

    # --- writers (J1 only; write-once, deterministic bytes) -----------------------------------------------------------------------------------
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

    def _write_status(self, cap: dict, status: dict) -> None:
        self._write_once(self.store / "status" / f"{cap['id']}.json", json.dumps(status, sort_keys=True, indent=1).encode())

    def _write_followup(self, cap: dict, sc: dict) -> dict:
        """4.1 / 10.2: a header line (capture id, manifest start and ``finished_utc``) and, per unit with k < j, the fields of the blind follow-up. No outcome field."""
        lines = [json.dumps({"kind": "header", "capture_id": cap["capture_id"], "id": cap["id"], "start_utc": iso(cap["start"]), "finished_utc": None if cap["fin_missing"] else iso(cap["fin"]),
                             "role": ROLE, "spec_sha": self.spec_sha, "code_sha": self.code_sha}, sort_keys=True)]
        for m in sorted(self.unit_meta):
            row = sc["unit_rows"].get(m)
            x = sc["ext"].get(m)
            lines.append(json.dumps({"unit_id": f"m3:{m}", "capture_id": cap["capture_id"], "row_present": row is not None, "closed": row[5] if row else None,
                                     "active": row[6] if row else None, "accepting_orders": x[3] if x else None, "uma_raw": x[2] if x else None, "end_date": row[7] if row else None,
                                     "row_received_utc": row[9] if row else None, "sidecar_received_utc": x[1] if x else None, "best_bid": row[3] if row else None,
                                     "best_ask": row[4] if row else None, "role": ROLE, "spec_sha": self.spec_sha, "code_sha": self.code_sha}, sort_keys=True))
        blob = self._gz_bytes(lines)
        self._write_once(self.store / "followup" / f"{cap['id']}.jsonl.gz", blob)
        return {"sha256": sha256_bytes(blob), "lines": len(lines) - 1}

    def _write_proposals(self, cap: dict, sc: dict) -> dict:
        """10.2: the sorted ids (deltas, gzip, base64) of in-scope markets whose status turned from an empty form at the previous processed capture to a whole-token P form at j."""
        ids = sc["p_new"]
        deltas = [ids[0], *[b - a for a, b in zip(ids, ids[1:], strict=False)]] if ids else []
        z = io.BytesIO()
        with gzip.GzipFile(fileobj=z, mode="wb", mtime=0) as gz:
            gz.write(json.dumps(deltas, separators=(",", ":")).encode())
        doc = {"capture_id": cap["capture_id"], "prev_capture_id": self.prev["id"] if self.prev else None, "count": len(ids), "ids_delta_gzip_b64": base64.b64encode(z.getvalue()).decode(),
               "role": ROLE, "spec_sha": self.spec_sha, "code_sha": self.code_sha}
        blob = self._gz_bytes([json.dumps(doc, sort_keys=True)])
        self._write_once(self.store / "proposals" / f"{cap['id']}.json.gz", blob)
        return {"sha256": sha256_bytes(blob)}

    # --- driving -----------------------------------------------------------------------------------------------------------------------------
    def rebuild_prev(self, by_id: dict) -> None:
        """Resume: capture k - 1 is the capture the CHAIN folded in the last slot (its directory id, held by the state file and checked against that slot's chain status file), never
        a pick by slot: a later on-time capture of the same slot cannot replace it (M1 R-diff MUST 1). When that capture is no longer on disk, k is ``no_previous_capture``."""
        if self.last_slot is None or self.prev is not None or self.last_kind != "processed":
            return
        if self.window_end is not None and self.last_t >= self.window_end:
            return  # follow-up only: the extractor does not fold any more
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
        self.prev = {"slot": cap["slot"], "start": cap["start"], "id": cap["id"], "rows": sc["book"], "uma": sc["uma"]}

    def run_available(self, caps: list[dict], now: float, side: dict | None = None) -> list[dict]:
        """Process every capture that is next in slot order. A slot is DECIDED only once ``now >= grid + 6 h`` (the set of on-time captures, judged by the manifest's ``finished_utc``
        <= grid + 6 h, is then final, whenever J1 runs); a decided slot with no on-time capture is recorded missing with its own status file; a capture appearing later stays
        unprocessed and is recorded as a late / duplicate side file. ``side`` is :func:`discover_all`'s output."""
        by_slot = {c["slot"]: c for c in sorted(caps, key=lambda c: (c["start"], c["id"]))}
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
                s = min(s, slot_of(self.lookback_from)[0])  # look-back slots before the first retained capture are counted missing_lookback_slot
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
                why = "delivered_after_missing_recorded"  # every on-time capture of a slot recorded missing (not only the first)
            elif s in self.processed_slots and kept_id is not None and c["id"] != kept_id:
                kept = by_id.get(kept_id)
                why = "on_time_but_delivered_after_slot_decided" if kept is not None and (c["start"], c["id"]) < (kept["start"], kept["id"]) else None
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

    # --- J0 report ---------------------------------------------------------------------------------------------------------------------------
    def report_j0(self, start_ts: float, end_ts: float, spec_path: Path | None, lookback_slots_used: int, spec: dict = sp.SPEC) -> dict:
        U = self.units
        caps_by_day = Counter(c240.day_of(c["start"]) for c in self.classified)
        full_days = sorted(d for d, n in caps_by_day.items() if n >= spec["j0"]["full_day_captures"])
        per_day = Counter(u["day"] for u in U)
        med = None
        if full_days:
            v = sorted(per_day.get(d, 0) for d in full_days)
            n = len(v)
            med = float(v[n // 2]) if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0
        ev_units = Counter(u["event_id"] for u in U)
        info = self.rules.info
        rule_a = None if med is None else bool(med < spec["j0"]["rule_a_units_below"])
        rule_b = None if med is None else bool(med * 21 < spec["j0"]["rule_b_projected_21_day_units_below"])
        cells = {k: dict(sorted(Counter(u["cells"][k] for u in U).items())) for k in (f"S{i}" for i in range(1, 14))}
        classed = [u for u in U if u["rule_class"] in CLASSED]
        by_tier: dict = {}
        for t in TIER_NAMES:
            ut = [u for u in U if u["tier"] == t]
            by_tier[t] = {"units": len(ut), "classed": sum(1 for u in ut if u["rule_class"] in CLASSED), "no_rules": sum(1 for u in ut if u["rule_class"] == "no_rules")}
        avg_caps = (READOUT_UTC - (REGISTERED_UTC + END_UTC) / 2.0) / GRID_S
        gaps = sorted(g for g in (u["gap_sidecar_minus_row_s"] for u in U) if math.isfinite(g))
        days_present = sorted(set(self.merged_days))
        last_day = max(days_present) if days_present else None
        expected = day_range(RULES_FIRST_DAY, last_day) if last_day and last_day >= RULES_FIRST_DAY else []
        side = ("crossed_book", "wide_book_high_ask")
        return {
            "kind": "M3-J0 counts-only pre-freeze check (MEASUREMENT_M3_CH274.md 10.1): J1 code in dry mode; counts only, k = 0, uncounted; no follow-up, proposal state, exit, price after k or "
                    "resolution read for a hypothetical unit after its k; no store, state, follow-up or proposal-set file written; informed (M3-J0)",
            "version": VERSION, "dry_run": True, "code_sha": self.code_sha, "code_sha_parts": sp.code_sha_parts(), "spec_sha": sp.spec_sha(spec),
            "spec_sha_kind": "design_text" if spec.get("design_sha256") else "draft_constants_canonical_json",
            "design_text_sha256": sha256_file(spec_path) if spec_path and Path(spec_path).exists() else None,
            "pins": {"imported_module_sha256": module_pins(), "rule_lexicon_sha256": lexicon_sha256(), "note": "12.5: recorded in J0's seal and at registration"},
            "span": {"start_utc": iso(start_ts), "end_utc": iso(end_ts), "window_start_utc": iso(self.window_start), "lookback_fold_captures": lookback_slots_used,
                     "lookback_slots_registered": LOOKBACK_SLOTS, "classified_captures": len(self.classified), "full_days": full_days,
                     "missing_slots_utc": [iso(slot_time(s)) for s in sorted(self.missing_slots)],
                     "note": "J0 folds 12 captures (one day) plus one k - 1 capture, not the registered 84-slot look-back: units are overstated and left_censored_first_row (pre_window) understated "
                             "(R1 MUST 6); the look-back is not changed after the output is seen"},
            "decision_rule": {"rule_a_extend_to_42_days_if_median_full_day_units_below": spec["j0"]["rule_a_units_below"], "rule_b_record_only_projected_21_day_units_below":
                              spec["j0"]["rule_b_projected_21_day_units_below"]},
            "decisions": {"median_full_day_units": med, "projected_21_day_units": None if med is None else med * 21, "rule_a_extend_to_42_days": rule_a, "rule_b_record_only": rule_b,
                          "note": "null = unavailable (no full day), not a pass; J0's only effect on the text is rule (a)"},
            "eligible_units": {"total": len(U), "per_day": dict(sorted(per_day.items())), "events": len(ev_units),
                               "units_per_event_strata": dict(sorted(Counter(units_bucket(n) for n in ev_units.values()).items())),
                               "note": "7.2 strata (1, 2-3, 4-9, 10+) with every unit treated as final-state; counts of events"},
            "funnel": {c: self.funnel.get(c, 0) for c in FUNNEL_ORDER} | {k: v for k, v in sorted(self.funnel.items()) if k not in FUNNEL_ORDER},
            "funnel_subcounts": dict(sorted(self.sub.items())),
            "funnel_by_day": dict(sorted(self.funnel_by_day.items())),
            "left_censored_first_row": {"pre_window_fold": self.extra.get("left_censored_first_row_pre_window", 0),
                                         "in_window": self.sub.get("left_censored_first_row:in_window", 0)},
            "side_counts": {k: self.extra.get(k, 0) for k in side} | {"near_seen_set_size_end": len(self.near_seen), "near_seen_in_scope_end": self.near_seen_in_scope,
                                                                       "candidates": self.extra.get("candidates", 0)},
            "side_classes": {k: self.extra.get(k, 0) for k in ("pre_window_source", "missing_capture", "missing_lookback_slot", "late_capture_ignored", "duplicate_slot_capture_ignored",
                                                               "off_grid_capture_ignored", "classed_with_gap")},
            "candidates_by_category": dict(sorted(self.cand_cat.items())),
            "arm_sizes_note": "sports and crypto candidate counts (the owner's arm sizes) are candidates_by_category (all candidates at classified captures, before E1-E4 exclusions) "
                              "and funnel out_of_scope_*",
            "end_date_missing_scope_by_day": dict(sorted(self.end_missing_by_day.items())), "end_date_missing_scope_distinct_markets": len(self.end_missing_markets),
            "splits_counts": cells,
            "k_time_zone_counts": {"S11": cells["S11"]},
            "classed_share": {"overall": None if not U else round(len(classed) / len(U), 6), "classed": len(classed), "units": len(U), "by_S1_tier": by_tier},
            "cat_k_distribution": dict(sorted(Counter(u["cat_k"] or "(empty)" for u in U).items())),
            "fee_category_raw_to_cat_k": dict(self.cat_raw.most_common(100)),
            "rules_stream": {**info, "day_files_merged": days_present, "days_expected_from_first_day": expected, "days_missing_from_first_day": [d for d in expected if d not in self.merged_days],
                             "contiguous_from_first_day": bool(expected) and all(d in self.merged_days for d in expected),
                             "committed_lines_without_parseable_finished_utc": info["records_without_receipt"]},
            "status_forms_at_e6": {"distinct_normalised_forms_on_candidate_rows_reaching_E6": dict(self.forms_e6.most_common()), "non_whitelist_forms_uncapped": dict(self.forms_other.most_common())},
            "t_d_source_counts": dict(sorted(self.t_d_source.items())),
            "receipt_gap_sidecar_minus_row_s": {"n": len(gaps), "median": gaps[len(gaps) // 2] if gaps else None, "min": gaps[0] if gaps else None, "max": gaps[-1] if gaps else None},
            "planned_followup_volume": {"unit_capture_lines_per_unit_assuming_window_midpoint": round(avg_caps, 1),
                                        "projected_lines_21_days": None if med is None else round(med * 21 * avg_caps), "note": "units x captures to READOUT_UTC; counts only"},
            "notes": dict(sorted(self.notes.items())),
            "not_printed": "no bid, ask, mid, liquidity value, resolution, label or outcome; prices enter only as S11 zone counts",
        }


# --- entry points ------------------------------------------------------------------------------------------------------------------------

def run_j0(snapshot_root: Path, rules_root: Path | None, start_ts: float, end_ts: float, *, lookback_slots: int = 12, spec_path: Path | None = None, spec: dict = sp.SPEC) -> dict:
    """M3-J0: the J1 extractor in dry mode over [start, end). The first ``lookback_slots`` captures only fold; one more capture is used as k - 1 only; the rest are classified
    (10.1). The report is sealed with the code hash (``seal_sha256`` over the report without that field)."""
    info = discover_all(snapshot_root, start_ts, end_ts)
    caps, notes = info["caps"], info["notes"]
    rules = RulesIndex.load(rules_root)
    window_start = start_ts
    if caps and lookback_slots and lookback_slots < len(caps):
        window_start = caps[lookback_slots]["start"] - 1.0  # the first classified k needs k - 1 at or after window_start
    mp = M3Pass(window_start=window_start, window_end=None, rules=rules, dry_run=True, spec_sha=sp.spec_sha(spec))
    mp.run_available(caps, now=math.inf, side=info)
    mp.notes.update({f"discover:{k}": v for k, v in notes.items()})
    rep = mp.report_j0(start_ts, end_ts, spec_path if spec_path is not None else sp.DESIGN_PATH, lookback_slots, spec)
    rep["peak_rss_mb"] = peak_rss_mb()
    rep["seal_sha256"] = sha256_bytes(json.dumps(rep, sort_keys=True, default=str, separators=(",", ":")).encode())
    return rep


def run_j1(snapshot_root: Path, rules_root: Path | None, store: Path, *, window_start: float = REGISTERED_UTC, window_end: float = END_UTC, spec_sha: str, now: float,
           record_followup: bool = True, record_proposals: bool = True, followup_until: float | None = None, pad: tuple | None = None) -> M3Pass:
    """One J1 pass (10.2): the fixed look-back span ``[window_start - 7 d, window_start)`` and the window, then follow-up captures to READOUT. ``spec_sha`` is given by the caller (the
    registered runner passes the pinned one); see :func:`run_pass` for the gated entry point."""
    fu = READOUT_UTC if followup_until is None else followup_until
    info = discover_all(snapshot_root, window_start - LOOKBACK_SLOTS * GRID_S, fu, window_start=window_start)
    mp = M3Pass(window_start=window_start, window_end=window_end, rules=RulesIndex.load(rules_root), dry_run=False, store=store, spec_sha=spec_sha,
                record_followup=record_followup, record_proposals=record_proposals, lookback_from=window_start - LOOKBACK_SLOTS * GRID_S, followup_until=fu)
    if pad and mp.last_slot is None:
        mp.pad_state(*pad)
    mp.run_available(info["caps"], now=now, side=info)
    mp.notes.update({f"discover:{k}": v for k, v in info["notes"].items()})
    return mp


def run_pass(snapshot_root: Path, rules_root: Path | None, store: Path, spec: dict = sp.SPEC, now: float | None = None, pins: dict | None = None, paths: dict | None = None,
             design: Path | None = None, record_followup: bool = True, record_proposals: bool = True, pad: tuple | None = None) -> dict:
    """The registered J1 entry point. Refuses on a pin mismatch (design text once frozen, eight modules, lexicon; spec_sha / code_sha against ``pins`` at every pass), a real spec whose
    design text is not frozen, a missing or late-enough ``registration_commit_utc`` (12.6), before ``REGISTERED_UTC`` (the first pass folds the look-back and must see the span), once the
    follow-up manifest exists, and a state pad outside a dry-run spec. Appends one line to ``logs/j1_runs.jsonl`` (counts, peak RSS; no follow-up content)."""
    sp.check_pins(spec, paths, design)
    sp.check_real_run(spec)
    sp.check_run_pins(pins, spec)
    sp.check_registration_lead(pins, spec)
    now = time.time() if now is None else now
    reg, end = sp.ts(spec, "registered_utc"), sp.ts(spec, "end_utc")
    if now < reg:
        raise sp.M3Refusal(f"J1 refuses before REGISTERED_UTC ({spec['registered_utc']}): the first pass folds the look-back span and must see every pre-window capture")
    if pad and not spec.get("dry_run"):
        raise sp.M3Refusal("a state pad is for the host dry run only")
    store = Path(store)
    if (store / "followup_manifest.json").exists():
        raise sp.M3Refusal("J1 refuses: the follow-up is closed (followup_manifest.json exists)")
    mp = run_j1(snapshot_root, rules_root, store, window_start=reg, window_end=end, spec_sha=sp.spec_sha(spec), now=now, record_followup=record_followup,
                record_proposals=record_proposals, followup_until=sp.ts(spec, "readout_utc"), pad=pad)
    rec = {"now_utc": iso(now), "peak_rss_mb": peak_rss_mb(), "spec_sha": mp.spec_sha, "code_sha": mp.code_sha, "last_slot": mp.last_slot, "processed_slots": len(mp.processed_slots),
           "missing_slots": len(mp.missing_slots), "units_total": len(mp.unit_meta), "counts": dict(sorted(mp.extra.items())), "ledger_markets": mp.ledger.n_markets(),
           "ledger_records": mp.ledger.n_records(), "near_seen": len(mp.near_seen), "ever_seen": len(mp.ever_seen), "notes": dict(sorted(mp.notes.items())),
           "rules_day_files_merged": len(mp.merged_days), "rules_days_unmerged_to_today": mp.unmerged_days(iso(now)[:10])}
    (store / "logs").mkdir(parents=True, exist_ok=True)
    with open(store / "logs" / "j1_runs.jsonl", "a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec
