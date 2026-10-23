# ruff: noqa: E501
"""LIVE prospective tests LT10 (docs/research_lab/LIVE_TESTS_10.md, design text frozen at sha256 1da6c075...): the fine-clock family on E009's
stream, CH224 (the hedged maker's price), CH223 (the other venue's makers flinch first), CH222 (the venue that traded first). DRAFT: nothing is
registered; E-numbers are assigned at registration. Research tooling only; never trades; makes no network request.

CODE PHASE 1 (this file):

* the shared origin-side unit builder (:func:`build_origins`, 1.3-1.5 and sections 2-4): one vectorised pass over a pair x 120 s poll grid, used
  by the censuses, the window reader and the simulated worlds alike; E009's seven features are re-checked against the VENDORED ``features`` on
  every census and reader unit (``check_e009``);
* the pair-record rules of 1.2: the census rule ``T_in = max(refreshed_utc + L, L_obs)`` (:class:`CensusRecords`) and the WINDOW rule of re-check
  fix 1 (:class:`WindowRecords`: a record is in force at t only if the successor's ``runs.jsonl`` shows it loaded at a cycle <= t AND
  t >= refreshed_utc + L AND the reader had seen the file; ``L_obs`` is never read in the window; the reader does not process origin t before the
  ``runs.jsonl`` line of cycle t, or of a later cycle, exists);
* the Kalshi-only lag loader (:data:`KALSHI_LAG_FIELDS`, :func:`read_quote_file` with those fields) and the far-future twins;
* the fresh seal (:func:`seal_inputs`) and the counts-only censuses CF10 / CK10 / CD10 (:func:`census_family`, :func:`census_kalshi`,
  :func:`census_design`): origin-side fields only, every gate threshold from the spec as section 7 states it, missing data counted, never imputed;
* the event-phase block Freedman-Lane gate (:func:`event_phase_fl_gate`, 1.8; R1 must-fix 4);
* the window reader's state pass (:func:`run_once`: origin statuses and frozen state lines, write-once) and ``ops-stats``.

CODE PHASE 2 (not here): the reader's target, twin and outcome writers, the single analysis (1.7, 1.9, 1.10), the full size check job, the
``battery2`` counting entry and the analysis-only vendored names (``fit``, ``holm``, ...). The simulated worlds and the gate-rate evaluation are in
``live_tests10_analysis.py`` (phase 1 part).

E009 and LT3-LT9 code is used only through the vendored copies in ``live_tests10_base`` (8.1): this module never imports ``cross_venue_live*`` or
``live_tests3`` .. ``live_tests9``.
"""

from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from . import forecast
from . import live_tests10_base as b

VERSION = "live-tests10-v1"
ROOT = forecast.ROOT
E009_ROOT = ROOT / "data-dumps" / "research_lab" / "cross_venue_live"
XV_ROOT = ROOT / "data-dumps" / "research_lab" / "xv_quotes"
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
FEED_ROOT = ROOT / "data-dumps" / "research_lab" / "reward_params"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests10"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests10_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration
REGISTERED_UTC = "2026-11-10T00:00:00Z"  # proposed (design 1.1); slides later with any step
END_UTC = "2026-12-01T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-12-02T12:00:00Z"
STALENESS_STOP_UTC = "2026-11-30T00:00:00Z"  # 1.1: not registered if REGISTERED_UTC would fall after it
FREEZE_DEADLINE_UTC = "2026-11-03T02:00:00Z"  # 1.1: the design-text freeze must precede it and T_E009
DESIGN_TEXT_SHA256 = "1da6c07510f294c26ab0c69d17fd57bd6daefab7275d88f4bbeb6d3a130bc6e8"  # LIVE_TESTS_10.md design-text freeze (34b7e22e), 2026-10-23
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_10.md"
TEMPFAIL = 75
DAY_S = 86400
GRID_S = b.OUTCOME_GRID_S  # 600: the 10-minute origin grid
POLL_S = b.CYCLE_S  # 120
L_S = 11400  # 1.2: the declared pair-record lag (3 h 10 min)
LOOKBACK_POLLS = 32  # t - 3,840 s: the oldest poll E009's 60-minute look-up uses (1.1 boundary)
TWIN_AHEAD_POLLS = 21  # t + 2,520 s: the far-future twin's last poll (t + 2,400 s + 120 s)
TESTS = ("CH224", "CH223", "CH222")
KINDS = {"CH224": "hedge", "CH223": "flinch", "CH222": "traded"}
SCOPES = ("non_sports_ex_crypto", "ex_crypto")
SRC_SUCCESSOR = "xv_quotes_v1"
CODE_FILES = ("live_tests10.py", "live_tests10_analysis.py", "live_tests10_worlds.py", "live_tests10_base.py", "live_tests10_analysis_base.py", "xv_quotes_poller.py", "xv_quotes_poller_base.py",
              "bounce_decomp.py", "battery.py", "economics.py", "forecast.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)
EPS = 1e-9
QUIET_EPS = 1e-5  # 0.001c in price units (section 3)
MOVE_MIN = 0.005  # 0.5c (section 4)

epoch, iso, sha256_file, _json = b.epoch, b.iso, b.sha256_file, b._json

# The quote fields the ORIGIN-SIDE pass reads (1.2); k_mid / p_mid are recomputed with the vendored two_sided_mid.
QUOTE_FIELDS = ("k_bid", "k_ask", "k_last", "k_bid_sz", "k_ask_sz", "k_status", "k_vol24", "k_recv", "p_bid", "p_ask", "p_bid_sz", "p_ask_sz",
                "p_book_ts", "p_tick", "p_recv")
# Section 7: the Kalshi-only lag loader. A poll later than a unit's origin reaches census code only through these fields (keys t, pid).
KALSHI_LAG_FIELDS = ("k_bid", "k_ask", "k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "k_status", "k_recv")
POLY_FIELDS = tuple(f for f in QUOTE_FIELDS if f.startswith("p_"))
STATUS_CODES = ("unit", "lt10_boundary", "retired", "not_yet_in_force", "category_unknown", "poll_missing", "spread_censored", "one_sided_k",
                "one_sided_p", "out_of_range", "late_origin", "features_incomplete", "window_gap", "rv_short", "end_soon", "excluded_event")
ST = {s: i for i, s in enumerate(STATUS_CODES)}
CLASS223 = ("quiet_untraded", "traded_quiet", "reverted_move", "small_move", "move")  # cls223 per unit (section 3)
CLASS222 = ("traded", "quote_only", "ambiguous_trade", "no_move")  # cls222 per unit (section 4)


class Refused(RuntimeError):
    """A path, seal, spec or input check failed: LT10 refuses (nothing is written)."""


# --- pins, spec and design text -------------------------------------------------------------------------------------------------------


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LT3 9.3's rule)."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: (code_sha256(here / n) if (here / n).exists() else None) for n in CODE_FILES}


def _nan_free(o, path: str = "") -> list[str]:
    if isinstance(o, float) and not math.isfinite(o):
        return [path]
    if isinstance(o, dict):
        return [p for k, v in o.items() for p in _nan_free(v, f"{path}.{k}")]
    if isinstance(o, list):
        return [p for i, v in enumerate(o) for p in _nan_free(v, f"{path}[{i}]")]
    return []


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    """The spec as written. DRAFT (``sha is None``): null placeholders allowed. Pinned: hash equal, no NaN, dates equal the module constants (L6)."""
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None:
        if got != sha:
            raise RuntimeError(f"live_tests10 spec sha256 mismatch: {got} != pinned {sha}")
        if (bad := _nan_free(spec)):
            raise RuntimeError(f"live_tests10 pinned spec holds NaN / inf at {bad[:5]}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests10 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    if spec.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        raise RuntimeError("live_tests10 spec design_text_sha256 differs from the module constant")
    if spec.get("scope") not in SCOPES:
        raise RuntimeError(f"live_tests10 spec scope {spec.get('scope')!r} is not one of {SCOPES} (1.4 item 2)")
    return spec


SPEC_HASHED_BLOCKS = ("census_inputs", "census_gates", "eligibility", "tests", "scope", "pair_record_rule", "category_rule", "f_roles", "seeds", "mde_planning")


def spec_blocks_sha(spec: dict) -> str:
    """sha256 of the canonical JSON of every spec block census code reads. The seal stores it; every census refuses a spec whose blocks differ
    from the seal-time ones. ``census_fixed`` (the values the censuses fill) is deliberately outside the hash."""
    blob = json.dumps({k_: spec.get(k_) for k_ in SPEC_HASHED_BLOCKS}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def design_text_sha(path: Path | None = None) -> str:
    return sha256_file(path or DESIGN_PATH)


def design_text_error(path: Path | None = None) -> dict | None:
    got = design_text_sha(path)
    return None if got == DESIGN_TEXT_SHA256 else {"error": "LIVE_TESTS_10.md differs from the text-frozen file: refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}


F_ROLES = {"CH224": "binding", "CH223": "label", "CH222": "label"}  # 1.9: fixed by design, never by a census count


def f_role(spec: dict, test: str) -> str:
    """1.9: CH224's F binds; CH223's and CH222's F are reported labels (CH223 also has the binding point-estimate condition beta_twin < beta_lead).
    A spec that says otherwise, or that holds any switch key, is refused."""
    got = (spec.get("f_roles") or {}).get(test)
    if got != F_ROLES[test] or "f_binding" in spec or "f_switch" in spec:
        raise RuntimeError(f"F role of {test} must be {F_ROLES[test]} (design 1.9); the spec says {got!r}")
    return got


def registration_error(freeze_utc: str | None, t_e009_utc: str | None, registered_utc: str = REGISTERED_UTC) -> str | None:
    """1.1: LT10 is not registered when the design-text freeze is not before 2026-11-03T02:00Z and before T_E009, or when REGISTERED_UTC would
    fall after the staleness stop 2026-11-30T00:00Z, or before the floor 2026-11-10T00:00Z."""
    f, te, r = epoch(freeze_utc), epoch(t_e009_utc), epoch(registered_utc)
    if not math.isfinite(f) or not (f < epoch(FREEZE_DEADLINE_UTC)):
        return "the design-text freeze is not before 2026-11-03T02:00:00Z: not registered (1.1)"
    if not math.isfinite(te) or not (f < te):
        return "the design-text freeze is not before T_E009: not registered (1.1)"
    if not math.isfinite(r) or r > epoch(STALENESS_STOP_UTC):
        return "REGISTERED_UTC would fall after the staleness stop 2026-11-30T00:00:00Z: not registered (1.1)"
    if r < epoch("2026-11-10T00:00:00Z") or r % DAY_S:
        return "REGISTERED_UTC must be a 00:00Z on or after 2026-11-10 (1.1 (d))"
    return None


# --- the path allow-list (1.2: "a path allow-list in the reader and the census refuses any other path") ---------------------------------


_ALLOW = [re.compile(p) for p in (
    r"(^|/)data-dumps/research_lab/cross_venue_live/quotes/\d{8}\.jsonl(\.gz)?$",
    r"(^|/)data-dumps/research_lab/cross_venue_live/pairs/pairs_\d{8}T\d{6}Z\.json$",
    r"(^|/)data-dumps/research_lab/cross_venue_live/refresh\.log$",
    r"(^|/)data-dumps/research_lab/xv_quotes/quotes/\d{8}\.jsonl(\.gz)?$",
    r"(^|/)data-dumps/research_lab/xv_quotes/pairs/pairs_\d{8}T\d{6}Z\.json$",
    r"(^|/)data-dumps/research_lab/xv_quotes/runs\.jsonl$",
    r"(^|/)snapshots/[^/]+/(rows_ext\.csv\.gz|manifest\.json)$",
    r"(^|/)reward_params/[^/]+/(manifest\.json|rows\.jsonl\.gz)$",
    r"(^|/)live_tests10/.+",
    r"(^|/)live_tests10_census/.+\.json$",
    r"(^|/)seals/lt10_census_inputs\.json$",
)]
_DENY = [re.compile(p) for p in (
    r"predictions[^/]*\.jsonl", r"outcomes[^/]*\.jsonl", r"arepo_val", r"(^|/)cross_venue/", r"surprise_live", r"(^|/)live_tests[2-9]/",
    r"(^|/)live_tests[2-9]_census/", r"signal_engine", r"gapfill|gap_fill|merged", r"trade_sample", r"book_sweeps", r"live_trade_monitor",
    r"predictit|smarkets|espn|gamma_rules", r"(^|/)cb1[6-8]", r"copy_skilled|e025|e026",
)]


def check_path(p: Path | str) -> Path:
    """Refuse any path outside LT10's allow-list (1.2) and every store of 1.2's "not read" list."""
    s = str(Path(p)).replace("\\", "/")
    if any(d.search(s) for d in _DENY) or not any(a.search(s) for a in _ALLOW):
        raise Refused(f"path not on LT10's allow-list (1.2): {s}")
    return Path(p)


# --- quote lines ----------------------------------------------------------------------------------------------------------------------


def _f(v) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) else math.nan


def iter_complete_lines(path: Path) -> Iterable[bytes]:
    """Complete lines only: an incomplete trailing line (no newline yet) is left for the next run (8.1)."""
    path = check_path(path)
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rb") as fh:
        for raw in fh:
            if raw.endswith(b"\n"):
                yield raw


def read_quote_file(path: Path, fields: tuple[str, ...], t_lo: float = -math.inf, t_hi: float = math.inf, src: str | None = None) -> dict:
    """Columns of one quote day file, projected to ``fields`` IMMEDIATELY after each line is parsed (no other field leaves this function),
    lines with ``t`` in ``[t_lo, t_hi]`` only. ``k_status`` becomes ``k_active`` (in {active, open}; 1.4 item 3). ``src``: keep only lines whose
    trailing writer key equals it (the successor's ``xv_quotes_v1``); None keeps every line."""
    pids, ts, cols = [], [], {f: [] for f in fields if f != "k_status"}
    act = [] if "k_status" in fields else None
    for raw in iter_complete_lines(path):
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        t = d.get("t")
        if not isinstance(t, (int, float)) or not (t_lo <= t <= t_hi):
            continue
        if src is not None and d.get("src") != src:
            continue
        pids.append(str(d.get("pid")))
        ts.append(int(t))
        for f in cols:
            cols[f].append(_f(d.get(f)))
        if act is not None:
            act.append(d.get("k_status") in ("active", "open"))
        del d
    out = {"pid": np.array(pids, dtype=object), "t": np.array(ts, dtype=np.int64)}
    out.update({f: np.array(v, dtype=float) for f, v in cols.items()})
    if act is not None:
        out["k_active"] = np.array(act, dtype=bool)
    return out


def read_keys(path: Path, t_lo: float = -math.inf, t_hi: float = math.inf, src: str | None = None) -> dict:
    """Keys and ``t`` only (the census ``L_obs`` and coverage pass; no price field)."""
    return read_quote_file(path, (), t_lo, t_hi, src)


def concat_cols(parts: list[dict]) -> dict:
    parts = [p for p in parts if len(p["t"])]
    if not parts:
        return {"pid": np.array([], dtype=object), "t": np.array([], dtype=np.int64)}
    keys = parts[0].keys()
    return {k: np.concatenate([p[k] for p in parts]) for k in keys}


# --- pair records (1.2) ---------------------------------------------------------------------------------------------------------------


def load_pair_file(path: Path) -> dict:
    path = check_path(path)
    raw = Path(path).read_bytes()
    doc = json.loads(raw)
    stamp = re.search(r"pairs_(\d{8}T\d{6}Z)\.json$", Path(path).name)
    st = stamp.group(1) if stamp else None
    ref = doc.get("refreshed_utc")
    st_ok = bool(st and ref and st == ref.replace("-", "").replace(":", ""))
    return {"name": Path(path).name, "sha256": hashlib.sha256(raw).hexdigest(), "refreshed_utc": ref, "refreshed": epoch(ref), "stamp_ok": st_ok,
            "pairs": {p["pid"]: p for p in doc.get("pairs", [])}}


class CensusRecords:
    """1.2's CENSUS rule: record r is in force from ``T_in(r) = max(refreshed_utc(r) + L, L_obs(r))``; ``L_obs(r)`` = the first poll t at or after
    ``refreshed_utc(r)`` carrying a quote line of a pid of r that has no quote line in the ``RETIRE_KEEP_S + 120 s`` before ``refreshed_utc(r)``
    (keys and t only); unidentifiable (no such pid, or the look-back before ``refreshed_utc`` not fully inside the read keys) -> omitted. The record
    in force at t is the one with the latest ``T_in <= t``."""

    def __init__(self, records: list[dict], key_times: dict[str, np.ndarray], keys_lo: float, L: int = L_S) -> None:
        self.records = sorted(records, key=lambda r: r["refreshed"])
        self.L = L
        pre = b.RETIRE_KEEP_S + POLL_S
        for r in self.records:
            R = r["refreshed"]
            r["l_obs"] = None
            if R - pre < keys_lo:
                r["l_obs_reason"] = "look-back before refreshed_utc not inside the read keys"
            else:
                new = []
                for pid in r["pairs"]:
                    ts = key_times.get(pid)
                    if ts is None or not len(ts):
                        continue
                    i = int(np.searchsorted(ts, R - pre, side="left"))
                    if i < len(ts) and ts[i] < R:
                        continue  # polled in the RETIRE_KEEP_S + 120 s before R: not new
                    j = int(np.searchsorted(ts, R, side="left"))
                    if j < len(ts):
                        new.append(int(ts[j]))
                r["l_obs"] = min(new) if new else None
                r["l_obs_reason"] = "identified" if new else "no newly added pid with a quote line"
            r["t_in"] = max(R + L, r["l_obs"]) if r["l_obs"] is not None else R + L
        self._tin = np.array([r["t_in"] for r in self.records], dtype=float)

    def in_force(self, t: float) -> dict | None:
        ok = [r for r in self.records if r["t_in"] <= t]
        return max(ok, key=lambda r: (r["t_in"], r["refreshed"])) if ok else None

    def pending_pids(self, t: float, cur: dict | None) -> set[str]:
        """Pids of records refreshed at or before t that are not (yet) the record in force: their pairs are ``not_yet_in_force`` at t."""
        out: set[str] = set()
        for r in self.records:
            if r["refreshed"] <= t and r is not cur and r["t_in"] > t:
                out |= set(r["pairs"])
        return out

    def lags(self) -> list[dict]:
        return [{"name": r["name"], "refreshed_utc": r["refreshed_utc"], "l_obs_minus_refreshed_s": (r["l_obs"] - r["refreshed"]) if r["l_obs"] is not None else None,
                 "l_obs_after_lag_floor": bool(r["l_obs"] is not None and r["l_obs"] > r["refreshed"] + self.L), "l_obs_reason": r["l_obs_reason"]} for r in self.records]


class WindowRecords:
    """1.2's WINDOW rule (re-check fix 1; decidable in real time at t, never corrected afterwards): record r is in force at origin t only if
    (i) the successor's ``runs.jsonl`` shows r loaded at a cycle <= t (the first ``kind = cycle`` line whose ``pairs_loaded_utc`` equals r's
    ``refreshed_utc``), AND (ii) t >= ``refreshed_utc(r) + L``, AND (iii) LT10's reader had seen r's pair file (its first-seen log, at or before the
    run that processes t). The record in force at t is the latest-refreshed record meeting (i)-(iii). ``L_obs`` is census-only and never read here.
    ``ready(t)``: origin t may be processed only once the ``runs.jsonl`` line of cycle t (or of a later cycle, which proves cycle t over) exists."""

    def __init__(self, records: list[dict], runs: list[dict], seen: set[str], L: int = L_S) -> None:
        self.records = sorted(records, key=lambda r: r["refreshed"])
        self.L = L
        cyc = [r for r in runs if r.get("kind") == "cycle" and isinstance(r.get("t"), (int, float))]
        self.cycles = {int(r["t"]) for r in cyc}
        self.last_cycle = max(self.cycles) if self.cycles else None
        first: dict[str, int] = {}
        for r in sorted(cyc, key=lambda r: r["t"]):
            u = r.get("pairs_loaded_utc")
            if u is not None and u not in first:
                first[u] = int(r["t"])
        for r in self.records:
            r["load_cycle"] = first.get(r["refreshed_utc"])
            r["seen"] = r["name"] in seen

    def ready(self, t: int) -> bool:
        return self.last_cycle is not None and self.last_cycle >= t

    def cycle_ran(self, t: int) -> bool:
        return int(t) in self.cycles

    def eligible(self, r: dict, t: float) -> bool:
        return r["load_cycle"] is not None and r["load_cycle"] <= t and t >= r["refreshed"] + self.L and r["seen"]

    def in_force(self, t: float) -> dict | None:
        ok = [r for r in self.records if self.eligible(r, t)]
        return max(ok, key=lambda r: r["refreshed"]) if ok else None

    def pending_pids(self, t: float, cur: dict | None) -> set[str]:
        out: set[str] = set()
        for r in self.records:
            if r is cur or r["refreshed"] > t:
                continue
            if cur is None or r["refreshed"] > cur["refreshed"]:
                out |= set(r["pairs"])
        return out


def pair_status(pid: str, cur: dict | None, pending: set[str]) -> int:
    """1.4 item 1: in the record in force -> active (0); else added by a not-yet-in-force record -> not_yet_in_force; else retired."""
    if cur is not None and pid in cur["pairs"]:
        return ST["unit"]
    return ST["not_yet_in_force"] if pid in pending else ST["retired"]


# --- category (1.4 item 2) ------------------------------------------------------------------------------------------------------------


def read_sidecar(path: Path) -> dict[str, tuple[bool, str]]:
    """market_id -> (sports, crypto class) from one ``rows_ext.csv.gz``: the pinned sports rule (vendored ``cb17_census.is_sports_sidecar``) and
    the pinned crypto classifier (vendored ``crypto_class``: ``fee_category`` contains ``crypto`` after strip and casefold). Category columns and
    keys only; no price column is read."""
    path = check_path(path)
    df = pd.read_csv(path, usecols=lambda c: c in ("market_id", "fee_type", "fee_category", "series_slugs"), dtype=str, keep_default_na=False)
    out = {}
    for mk, ft, fc, ss in zip(df["market_id"], df.get("fee_type", [""] * len(df)), df.get("fee_category", [""] * len(df)),
                              df.get("series_slugs", [""] * len(df)), strict=False):
        if mk not in out:
            out[str(mk)] = (bool(b.is_sports_sidecar(ft, fc, ss)), b.crypto_class(fc))
    return out


def read_sidecar_cond(path: Path) -> dict[str, str]:
    """market_id -> condition_id from one ``rows_ext.csv.gz`` (keys only; the join key of the reward feed, economics only, 1.2)."""
    path = check_path(path)
    df = pd.read_csv(path, usecols=lambda c: c in ("market_id", "condition_id"), dtype=str, keep_default_na=False)
    if "condition_id" not in df:
        return {}
    return {str(m): str(c) for m, c in zip(df["market_id"], df["condition_id"], strict=True) if c}


def feed_listing(feed_roots, before: float) -> dict | None:
    """1.2's reward feed, economics only: the last USABLE feed capture (manifest state complete and its rows file present) whose manifest finish is
    earlier than ``before``; ``{"capture": id, "rates": {condition_id: summed positive rate_per_day}}`` (a listed market with no positive
    configuration has rate 0.0). None when there is none (the flags are then NaN). Counts and gross rates only; no price is read."""
    best = None
    for r in b_roots(feed_roots):
        for m in sorted(Path(r).glob("*/manifest.json")) if Path(r).exists() else []:
            try:
                d = json.loads(check_path(m).read_text())
            except (OSError, ValueError, Refused):
                continue
            fin = epoch(d.get("finished_utc"))
            if d.get("state") != "complete" or not math.isfinite(fin) or not fin < before or not (m.parent / "rows.jsonl.gz").exists():
                continue
            if best is None or fin > best[0]:
                best = (fin, m.parent)
    if best is None:
        return None
    rates: dict[str, float] = {}
    with gzip.open(check_path(best[1] / "rows.jsonl.gz"), "rt") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            cid = rec.get("condition_id") if isinstance(rec, dict) else None
            if not isinstance(cid, str) or not cid:
                continue
            cfgs = rec.get("rewards_config")
            rate = sum(x for x in (_f(c.get("rate_per_day")) for c in cfgs if isinstance(c, dict)) if math.isfinite(x) and x > 0) if isinstance(cfgs, list) else 0.0
            rates[cid] = rates.get(cid, 0.0) + rate
    return {"capture": best[1].name, "rates": rates}


def in_scope(sports: bool, crypto: str, scope: str) -> bool:
    if scope == "non_sports_ex_crypto":
        return (not sports) and crypto == "non_crypto"
    if scope == "ex_crypto":
        return crypto == "non_crypto"
    raise Refused(f"unknown scope {scope!r}")


def last_completed_capture(snapshot_roots, before: float) -> dict | None:
    """The last capture COMPLETED (its own manifest's ``finished_utc``, state complete) strictly before ``before`` (1.2, R1 should-fix 3), over
    several roots (host first, then restore trees); its sidecar may be absent (the day's pairs are then ``category_unknown``)."""
    best = None
    for r in b_roots(snapshot_roots):
        for m in sorted(Path(r).glob("*/manifest.json")):
            try:
                d = json.loads(check_path(m).read_text())
            except (OSError, ValueError, Refused):
                continue
            fin = epoch(d.get("finished_utc"))
            if d.get("state") != "complete" or not math.isfinite(fin) or not fin < before:
                continue
            if best is None or fin > best["finished"]:
                best = {"capture": m.parent.name, "finished": fin, "finished_utc": d.get("finished_utc"), "dir": m.parent}
    return best


def b_roots(r) -> list[Path]:
    return [Path(x) for x in (r if isinstance(r, (list, tuple)) else [r])] if r is not None else []


# --- the poll grid and the shared unit builder (1.3-1.5, sections 2-4) ----------------------------------------------------------------


def two_sided_vec(bid: np.ndarray, ask: np.ndarray) -> np.ndarray:
    """E009's ``two_sided_mid`` element-wise (tested equal to the vendored function)."""
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask < 1) & (ask > bid) & (ask - bid <= b.MAX_SPREAD + 1e-12)
    return np.where(ok, (bid + ask) / 2.0, np.nan)


def censored_vec(bid: np.ndarray, ask: np.ndarray) -> np.ndarray:
    """1.4 item 9: a quote that is two-sided (0 < bid < ask < 1) but wider than E009's 10c rule."""
    with np.errstate(invalid="ignore"):
        return np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask < 1) & (ask > bid) & (ask - bid > b.MAX_SPREAD + 1e-12)


def in_range_vec(x: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return np.isfinite(x) & (x >= b.MID_RANGE[0]) & (x <= b.MID_RANGE[1])


GRID_FIELDS = ("k_bid", "k_ask", "k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "k_recv", "p_bid", "p_ask", "p_bid_sz", "p_ask_sz", "p_book_ts", "p_tick", "p_recv")


def to_grid(cols: dict, pids: list[str], t0: int, n: int, *, p_until: float = math.inf) -> dict:
    """Pair x 120 s poll arrays ``A[f][i, j]`` at ``t0 + 120 j`` from projected quote columns; absent polls NaN (``present`` False). Polymarket
    fields are filled only for polls at or before ``p_until`` (the census: the span's last origin; later polls are Kalshi-only, section 7)."""
    P = len(pids)
    idx = {p: i for i, p in enumerate(pids)}
    A = {f: np.full((P, n), np.nan) for f in GRID_FIELDS}
    A["present"] = np.zeros((P, n), dtype=bool)
    A["k_active"] = np.zeros((P, n), dtype=bool)
    if not len(cols["t"]):
        return A
    ii = np.array([idx.get(p, -1) for p in cols["pid"]], dtype=np.int64)
    jj = (cols["t"] - t0) // POLL_S
    ok = (ii >= 0) & (jj >= 0) & (jj < n) & ((cols["t"] - t0) % POLL_S == 0)
    ii, jj = ii[ok], jj[ok]
    A["present"][ii, jj] = True
    for f in GRID_FIELDS:
        if f in cols:
            v = cols[f][ok]
            if f.startswith("p_") and math.isfinite(p_until):
                v = np.where(cols["t"][ok] <= p_until, v, np.nan)
            A[f][ii, jj] = v
    if "k_active" in cols:
        A["k_active"][ii, jj] = cols["k_active"][ok]
    return A


def overlay_kalshi(A: dict, kcols: dict, pids: list[str], t0: int) -> None:
    """Fill Kalshi fields (and ``present``) of polls from a Kalshi-ONLY read (the lag loader's columns); Polymarket fields stay NaN there."""
    n = A["present"].shape[1]
    idx = {p: i for i, p in enumerate(pids)}
    if not len(kcols["t"]):
        return
    bad = [f for f in kcols if f not in ("pid", "t", "k_active") and f not in KALSHI_LAG_FIELDS]
    if bad:
        raise Refused(f"the Kalshi-only loader returned non-Kalshi fields {bad} (section 7)")
    ii = np.array([idx.get(p, -1) for p in kcols["pid"]], dtype=np.int64)
    jj = (kcols["t"] - t0) // POLL_S
    ok = (ii >= 0) & (jj >= 0) & (jj < n) & ((kcols["t"] - t0) % POLL_S == 0)
    ii, jj = ii[ok], jj[ok]
    A["present"][ii, jj] = True
    for f in KALSHI_LAG_FIELDS:
        if f == "k_status":
            continue
        A[f][ii, jj] = kcols[f][ok]
    if "k_active" in kcols:
        A["k_active"][ii, jj] = kcols["k_active"][ok]


def derive(A: dict) -> dict:
    """Mids, spreads, validity and censoring per poll (E009's two-sided rule on both venues)."""
    D = {"kmid": two_sided_vec(A["k_bid"], A["k_ask"]), "pmid": two_sided_vec(A["p_bid"], A["p_ask"])}
    D["kv"], D["pv"] = np.isfinite(D["kmid"]), np.isfinite(D["pmid"])
    D["vb"] = D["kv"] & D["pv"]
    D["sK"], D["sP"] = A["k_ask"] - A["k_bid"], A["p_ask"] - A["p_bid"]
    D["k_cens"], D["p_cens"] = censored_vec(A["k_bid"], A["k_ask"]), censored_vec(A["p_bid"], A["p_ask"])
    return D


def _take(M: np.ndarray, rows: np.ndarray, cols: np.ndarray, fill=np.nan) -> np.ndarray:
    """``M[rows, cols]`` with out-of-range columns giving ``fill``."""
    ok = (cols >= 0) & (cols < M.shape[1])
    out = np.full(np.broadcast(rows, cols).shape, fill, dtype=M.dtype if fill is not np.nan else float)
    if M.dtype == bool and fill is np.nan:
        out = np.zeros(np.broadcast(rows, cols).shape, dtype=bool)
    r, c = np.broadcast_arrays(rows, cols)
    out[ok] = M[r[ok], c[ok]]
    return out


def _lookup_idx(vb: np.ndarray, rows: np.ndarray, j: np.ndarray, lo_off: int, hi_off: int) -> np.ndarray:
    """E009's ``lookup``: the LATEST valid poll (both mids finite) in ``[t + lo_off polls, t + hi_off polls]``; -1 if none."""
    out = np.full(j.shape, -1, dtype=np.int64)
    for off in range(hi_off, lo_off - 1, -1):
        c = j + off
        hit = (out < 0) & _take(vb, rows, c, False)
        out[hit] = c[hit]
    return out


def build_origins(A: dict, t0: int, origin_cols: np.ndarray, meta: dict, *, check_e009: bool = True) -> pd.DataFrame:
    """The origin statuses and the ORIGIN-SIDE states of every pair x origin in ``origin_cols`` (grid columns with ``t % 600 == 0``).

    ``meta`` (per pair i and origin column position k): ``pid`` [P], ``pair_st`` [P, K] (1.4 item 1: unit / retired / not_yet_in_force /
    lt10_boundary), ``cat_known`` [P, K], ``sports`` [P, K], ``crypto`` [P, K] (str), ``ev`` [P, K] (``p_event_id`` of the record in force),
    ``p_end`` / ``k_close`` [P, K] (epoch, NaN unknown), ``hv`` [P, K], ``exclude_event`` (str or None).

    Reads poll t and EARLIER polls only (1.3, 1.6); the far-future twins are :func:`twins` (Kalshi-only), the targets :func:`targets` (never
    called by a census). Status order (1.4, first failing check): pair active -> category -> poll t valid (missing, censored spread, one-sided
    Kalshi, one-sided Polymarket, out of range, late receipt) -> E009's seven features -> window (>= 4 Kalshi-valid polls from s0 to t) -> rv60
    inputs (>= 20 valid polls each venue) -> ends (p_end / k_close later than t + 2 h or unknown) -> excluded event."""
    D = derive(A)
    P = A["present"].shape[0]
    K = len(origin_cols)
    rows = np.repeat(np.arange(P), K).reshape(P, K)
    j = np.broadcast_to(origin_cols, (P, K)).astype(np.int64)
    t = t0 + POLL_S * j
    g = lambda M, off=0, fill=np.nan: _take(M, rows, j + off, fill)  # noqa: E731
    status = np.array(meta["pair_st"], dtype=np.int64).copy()
    act = status == ST["unit"]
    nxt = act & ~np.asarray(meta["cat_known"], bool)
    status[nxt] = ST["category_unknown"]
    alive = status == ST["unit"]
    present = g(A["present"], 0, False)
    kmid, pmid = g(D["kmid"]), g(D["pmid"])
    k_act = g(A["k_active"], 0, False)
    klag, plag = g(A["k_recv"]) - t, g(A["p_recv"]) - t
    checks = [
        ("poll_missing", ~present),
        ("spread_censored", g(D["k_cens"], 0, False) | g(D["p_cens"], 0, False)),
        ("one_sided_k", ~np.isfinite(kmid) | ~k_act),
        ("one_sided_p", ~np.isfinite(pmid)),
        ("out_of_range", ~(in_range_vec(kmid) & in_range_vec(pmid))),
        ("late_origin", ~((klag <= b.MAX_RECV_LAG_S) & (plag <= b.MAX_RECV_LAG_S))),
    ]
    for name, bad in checks:
        hit = alive & bad
        status[hit] = ST[name]
        alive &= ~bad
    # E009's seven features (vendored definition, vectorised; re-checked against the vendored function below)
    s0 = _lookup_idx(D["vb"], rows, j, -7, -5)  # [t - 840, t - 600]
    b60 = _lookup_idx(D["vb"], rows, j, -32, -30)  # [t - 3,840, t - 3,600]
    kA, pA = _take(D["kmid"], rows, s0), _take(D["pmid"], rows, s0)
    kB, pB = _take(D["kmid"], rows, b60), _take(D["pmid"], rows, b60)
    feat_ok = (s0 >= 0) & (b60 >= 0) & in_range_vec(kA) & in_range_vec(pA) & in_range_vec(kB) & in_range_vec(pB)
    status[alive & ~feat_ok] = ST["features_incomplete"]
    alive &= feat_ok
    lvl = pmid - 0.5
    F = {"r1": pmid - pA, "r6": pmid - pB, "lvl": lvl, "lvl2": lvl * lvl, "gap": kmid - pmid, "dk1": kmid - kA, "dk6": kmid - kB}
    # the state window (s0, t]: the Kalshi-valid polls from s0 to t inclusive (1.3)
    win = []
    for off in range(-7, 1):
        c = j + off
        win.append((c, (c >= s0) & (s0 >= 0) & _take(D["kv"], rows, c, False)))
    n_win = sum(m.astype(int) for _, m in win)
    status[alive & (n_win < 4)] = ST["window_gap"]
    alive &= n_win >= 4
    # rv60 (1.4 item 6): sqrt of the sum of squared consecutive 120 s mid changes over the valid polls in [t - 3,600 s, t], >= 20 valid polls
    rv = {}
    for v, mid, key in (("pv", "pmid", "rv60_P"), ("kv", "kmid", "rv60_K")):
        cnt = np.zeros((P, K))
        ss = np.zeros((P, K))
        prev_ok, prev_m = None, None
        for off in range(-30, 1):
            ok = _take(D[v], rows, j + off, False)
            m = _take(D[mid], rows, j + off)
            cnt += ok
            if prev_ok is not None:
                both = ok & prev_ok
                ss += np.where(both, (m - prev_m) ** 2, 0.0)
            prev_ok, prev_m = ok, m
        rv[key] = np.where(cnt >= 20, np.sqrt(ss), np.nan)
        rv[key + "_n"] = cnt
    rv_ok = np.isfinite(rv["rv60_P"]) & np.isfinite(rv["rv60_K"])
    status[alive & ~rv_ok] = ST["rv_short"]
    alive &= rv_ok
    p_end, k_close = np.asarray(meta["p_end"], float), np.asarray(meta["k_close"], float)
    with np.errstate(invalid="ignore"):
        soon = (np.isfinite(p_end) & (p_end <= t + 7200)) | (np.isfinite(k_close) & (k_close <= t + 7200))
    end_unknown = ~np.isfinite(p_end) | ~np.isfinite(k_close)
    status[alive & soon] = ST["end_soon"]
    alive &= ~soon
    ev = np.asarray(meta["ev"], dtype=object)
    if meta.get("exclude_event"):
        exc = ev == str(meta["exclude_event"])
        status[alive & exc] = ST["excluded_event"]
        alive &= ~exc
    # --- states (frozen at t; computed for every row, kept for units) ---
    sK_t, sP_t = g(D["sK"]), g(D["sP"])
    sK_s0, sP_s0 = _take(D["sK"], rows, s0), _take(D["sP"], rows, s0)
    kb_t, ka_t, kb_s0, ka_s0 = g(A["k_bid"]), g(A["k_ask"]), _take(A["k_bid"], rows, s0), _take(A["k_ask"], rows, s0)
    kbs_t, kas_t, kbs_s0, kas_s0 = g(A["k_bid_sz"]), g(A["k_ask_sz"]), _take(A["k_bid_sz"], rows, s0), _take(A["k_ask_sz"], rows, s0)
    pbs_t, pas_t, pbs_s0, pas_s0 = g(A["p_bid_sz"]), g(A["p_ask_sz"]), _take(A["p_bid_sz"], rows, s0), _take(A["p_ask_sz"], rows, s0)
    kv_t = g(A["k_vol24"])
    p_tick = g(A["p_tick"])
    dsK = sK_t - sK_s0
    # the window steps between consecutive Kalshi-valid polls (traded, quiet, k_vol24)
    traded_steps = np.zeros((P, K), dtype=np.int64)
    up = np.zeros((P, K), dtype=bool)
    down = np.zeros((P, K), dtype=np.int64)
    nsteps = np.zeros((P, K), dtype=np.int64)
    vol_unknown = np.zeros((P, K), dtype=bool)
    klast_missing = np.zeros((P, K), dtype=np.int64)
    moved = np.zeros((P, K), dtype=bool)
    last_l = np.full((P, K), np.nan)
    last_v = np.full((P, K), np.nan)
    have = np.zeros((P, K), dtype=bool)
    for c, m in win:
        lv, vv, km = _take(A["k_last"], rows, c), _take(A["k_vol24"], rows, c), _take(D["kmid"], rows, c)
        step = m & have
        with np.errstate(invalid="ignore"):
            chg = step & np.isfinite(lv) & np.isfinite(last_l) & (np.abs(lv - last_l) > EPS)
            fin_v = step & np.isfinite(vv) & np.isfinite(last_v)
            up |= fin_v & (vv - last_v > EPS)
            down += (fin_v & (last_v - vv > EPS)).astype(np.int64)
            moved |= m & (np.abs(km - kA) >= QUIET_EPS)
        traded_steps += chg.astype(np.int64)
        nsteps += step.astype(np.int64)
        vol_unknown |= step & ~(np.isfinite(vv) & np.isfinite(last_v))
        klast_missing += (step & ~(np.isfinite(lv) & np.isfinite(last_l))).astype(np.int64)
        last_l = np.where(m, lv, last_l)
        last_v = np.where(m, vv, last_v)
        have |= m
    traded = traded_steps > 0
    with np.errstate(invalid="ignore"):
        bid_fall = (np.abs(kb_t - kb_s0) < EPS) & np.isfinite(kbs_s0) & (kbs_s0 > 0) & (kbs_t <= 0.5 * kbs_s0)
        ask_fall = (np.abs(ka_t - ka_s0) < EPS) & np.isfinite(kas_s0) & (kas_s0 > 0) & (kas_t <= 0.5 * kas_s0)
        widen = dsK >= 0.02 - EPS
    pull = widen | bid_fall | ask_fall
    pull_side = np.where(bid_fall & ~ask_fall, -1, np.where(ask_fall & ~bid_fall, 1, 0))
    size_zero = ~(np.isfinite(kbs_s0) & (kbs_s0 > 0)) | ~(np.isfinite(kas_s0) & (kas_s0 > 0))
    dk1 = F["dk1"]
    adk1 = np.abs(dk1)
    with np.errstate(invalid="ignore"):
        is_move = adk1 >= MOVE_MIN - EPS
        is_small = (adk1 >= QUIET_EPS) & ~is_move
    quiet_all = (adk1 < QUIET_EPS) & ~moved
    trade_signal = traded | up
    cls223 = np.where(is_move, 4, np.where(is_small, 3, np.where(~quiet_all, 2, np.where(trade_signal, 1, 0))))
    cls222 = np.where(~is_move, 3, np.where(traded, 0, np.where(up, 2, 1)))
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sP_s0 / sK_s0
    l1p = lambda x: np.log1p(x)  # noqa: E731
    out = {
        "pid": np.asarray(meta["pid"], dtype=object)[rows], "ev": ev, "t": t, "status": status, "end_unknown": end_unknown,
        "sports": np.asarray(meta["sports"], bool), "crypto": np.asarray(meta["crypto"], dtype=object), "cat_known": np.asarray(meta["cat_known"], bool),
        "hv": np.asarray(meta["hv"], bool), "fee_rate": np.asarray(meta.get("fee", np.full((P, K), np.nan)), float), "kmid": kmid, "pmid": pmid, "klag": klag, "plag": plag, "dec": np.fmax(g(A["k_recv"]), g(A["p_recv"])),
        "s0_t": np.where(s0 >= 0, t0 + POLL_S * s0, -1), "n_win": n_win, "p_tick": p_tick,
        "sK_t": sK_t, "sP_t": sP_t, "sK_s0": sK_s0, "sP_s0": sP_s0, "dsK": dsK, "dsP_own": sP_t - sP_s0, "ratio": ratio,
        "floorP": (sP_t <= p_tick + EPS).astype(float), "floorK": (sK_s0 <= 0.01 + EPS).astype(float),
        "tightK": (dsK <= -0.01 + EPS).astype(float), "wideK": (dsK >= 0.01 - EPS).astype(float),
        "traded": traded.astype(float), "trade_steps": traded_steps, "kvol_up": up, "kvol_down_steps": down, "win_steps": nsteps,
        "vol_unknown": vol_unknown.astype(float), "klast_missing_steps": klast_missing, "quiet_all": quiet_all, "moved_in_window": moved,
        "pull": pull.astype(float), "widen": widen, "bid_fall": bid_fall, "ask_fall": ask_fall, "pull_side": pull_side, "size_zero": size_zero,
        "cls223": cls223, "cls222": cls222, **F, "abs_dk1": adk1, "abs_r1": np.abs(F["r1"]), "abs_r6": np.abs(F["r6"]), "abs_dk6": np.abs(F["dk6"]),
        "abs_gap": np.abs(F["gap"]), "rv60_P": rv["rv60_P"], "rv60_K": rv["rv60_K"],
        "lkb_t": l1p(g(A["k_bid_sz"])), "lka_t": l1p(g(A["k_ask_sz"])), "lpb_t": l1p(pbs_t), "lpa_t": l1p(pas_t),
        "lkb_s0": l1p(kbs_s0), "lka_s0": l1p(kas_s0), "lpb_s0": l1p(pbs_s0), "lpa_s0": l1p(pas_s0),
        "lvol": np.where(np.isfinite(kv_t), np.log1p(np.where(np.isfinite(kv_t), np.maximum(kv_t, 0), 0)), 0.0),
    }
    df = pd.DataFrame({k: np.asarray(v).reshape(-1) if np.ndim(v) else np.repeat(v, P * K) for k, v in out.items()})
    df["sign"] = np.sign(df["dk1"].to_numpy())
    df["hour"] = (df["t"].to_numpy() // 3600) % 24
    df["moh"] = df["t"].to_numpy() % 3600
    df["day"] = pd.to_datetime(df["t"].to_numpy(), unit="s", utc=True).strftime("%Y-%m-%d")
    if check_e009:
        e009_recheck(df[df["status"] == ST["unit"]], A, D, t0, rows_of={p: i for i, p in enumerate(meta["pid"])})
    return df


def e009_recheck(units: pd.DataFrame, A: dict, D: dict, t0: int, rows_of: dict) -> None:
    """Every unit's seven features equal the VENDORED ``features(hist, t, k, p)`` (E009's own code) on the pair's valid-poll history (both mids
    finite, strictly before t). A mismatch refuses (the vectorised builder would be wrong)."""
    for pid, grp in units.groupby("pid"):
        i = rows_of[pid]
        valid = np.flatnonzero(D["vb"][i])
        tv = t0 + POLL_S * valid
        for r in grp.itertuples(index=False):
            lo = int(np.searchsorted(tv, r.t - 4440, side="left"))
            hi = int(np.searchsorted(tv, r.t, side="left"))
            hist = [(float(tv[q]), float(D["kmid"][i, valid[q]]), float(D["pmid"][i, valid[q]])) for q in range(lo, hi)]
            f = b.features(hist, float(r.t), float(r.kmid), float(r.pmid))
            if f is None or any(abs(f[n] - getattr(r, n)) > 1e-12 for n in b.FEATURES):
                raise Refused(f"E009 feature re-check failed for {pid} at {r.t}: vendored {f}")


def twins(A: dict, t0: int, origin_cols: np.ndarray, pids_rows: np.ndarray) -> pd.DataFrame:
    """1.9's far-future twins over ``(t + 1,800 s, t + 2,400 s]`` from KALSHI FIELDS ONLY (the arrays of the Kalshi-only lag loader beyond the
    origin): endpoints the polls at t + 1,800 s and t + 2,400 s, each exact if Kalshi-valid, else the nearest Kalshi-valid poll within +-120 s (the
    earlier on a tie, E009's ``_find`` order); ``dsK'``, ``pull'`` (>= 2c widening or a >= 50% size fall at an unchanged touch, endpoints, no mid or
    trade condition) and ``traded'`` (``k_last`` changed at any consecutive step between Kalshi-valid polls of [e1, e2])."""
    kb, ka = A["k_bid"], A["k_ask"]
    kv = np.isfinite(two_sided_vec(kb, ka))
    rows = pids_rows[:, None] if pids_rows.ndim == 1 else pids_rows
    j = np.broadcast_to(origin_cols, np.broadcast_shapes(np.shape(origin_cols), rows.shape)).astype(np.int64)
    rows = np.broadcast_to(rows, j.shape)

    def end(c: int) -> np.ndarray:
        out = np.full(j.shape, -1, dtype=np.int64)
        for off in (c, c - 1, c + 1):
            hit = (out < 0) & _take(kv, rows, j + off, False)
            out[hit] = (j + off)[hit]
        return out

    e1, e2 = end(15), end(20)
    ok = (e1 >= 0) & (e2 >= 0)
    s1, s2 = _take(ka - kb, rows, e1), _take(ka - kb, rows, e2)
    kb1, kb2, ka1, ka2 = _take(kb, rows, e1), _take(kb, rows, e2), _take(ka, rows, e1), _take(ka, rows, e2)
    bs1, bs2, as1, as2 = (_take(A["k_bid_sz"], rows, e1), _take(A["k_bid_sz"], rows, e2), _take(A["k_ask_sz"], rows, e1), _take(A["k_ask_sz"], rows, e2))
    with np.errstate(invalid="ignore"):
        pull = ((s2 - s1) >= 0.02 - EPS) | ((np.abs(kb2 - kb1) < EPS) & (bs1 > 0) & (bs2 <= 0.5 * bs1)) | ((np.abs(ka2 - ka1) < EPS) & (as1 > 0) & (as2 <= 0.5 * as1))
    traded = np.zeros(j.shape, dtype=bool)
    last = np.full(j.shape, np.nan)
    for off in range(14, 22):
        c = j + off
        m = (c >= e1) & (c <= e2) & ok & _take(kv, rows, c, False)
        lv = _take(A["k_last"], rows, c)
        with np.errstate(invalid="ignore"):
            traded |= m & np.isfinite(lv) & np.isfinite(last) & (np.abs(lv - last) > EPS)
        last = np.where(m, lv, last)
    return pd.DataFrame({"tw_ok": ok.reshape(-1), "dsK_tw": np.where(ok, s2 - s1, np.nan).reshape(-1), "pull_tw": np.where(ok, pull.astype(float), np.nan).reshape(-1),
                         "traded_tw": np.where(ok, traded.astype(float), np.nan).reshape(-1)})


def targets(A: dict, t0: int, origin_cols: np.ndarray, h_polls: int) -> pd.DataFrame:
    """1.3's target endpoint (SIZE-CHECK WORLDS AND THE PHASE-2 READER ONLY; no census calls it): Polymarket's mid at the poll at exactly
    t + h, else the nearest within +-120 s whose ``p_recv`` is at most 60 s after its own t (the earlier on a tie); status two_sided / one_sided /
    late / poll_missing; only two_sided has a target. The tolerance never places an endpoint before t + 1,080 s for h = 20 minutes."""
    D = derive(A)
    P = A["present"].shape[0]
    rows = np.repeat(np.arange(P), len(origin_cols)).reshape(P, -1)
    j = np.broadcast_to(origin_cols, rows.shape).astype(np.int64)
    end = np.full(j.shape, -1, dtype=np.int64)
    st = np.full(j.shape, 4, dtype=np.int64)  # 0 two_sided, 1 one_sided, 2 late, 4 poll_missing
    for off in (h_polls, h_polls - 1, h_polls + 1):
        c = j + off
        pres = _take(A["present"], rows, c, False)
        lag = _take(A["p_recv"], rows, c) - (t0 + POLL_S * c)
        pv = _take(D["pv"], rows, c, False)
        good = (end < 0) & pres & pv & (lag <= b.MAX_RECV_LAG_S)
        end[good] = c[good]
        st = np.where(good, 0, np.where((st == 4) & pres & pv, 2, np.where((st == 4) & pres, 1, st)))
    st = np.where(end >= 0, 0, st)
    pm1 = _take(D["pmid"], rows, end)
    sp1 = _take(D["sP"], rows, end)
    pbs1, pas1 = _take(A["p_bid_sz"], rows, end), _take(A["p_ask_sz"], rows, end)
    return pd.DataFrame({"tg_status": st.reshape(-1), "pmid_h": np.where(end >= 0, pm1, np.nan).reshape(-1), "sP_h": np.where(end >= 0, sp1, np.nan).reshape(-1),
                         "p_bid_sz_h": np.where(end >= 0, pbs1, np.nan).reshape(-1), "p_ask_sz_h": np.where(end >= 0, pas1, np.nan).reshape(-1),
                         "t_end": np.where(end >= 0, t0 + POLL_S * end, -1).reshape(-1)})


# --- censuses: the sealed inputs, the day batches and the gates (section 7) -----------------------------------------------------------


def _day_epoch(d: str) -> int:
    return int(epoch(f"{d[:4]}-{d[4:6]}-{d[6:8]}T00:00:00Z"))


def _ymd(t: float) -> str:
    return pd.Timestamp(t, unit="s", tz="UTC").strftime("%Y%m%d")


def census_days(spec: dict) -> list[str]:
    ci = spec["census_inputs"]
    lo, hi = _day_epoch(ci["span"]["start_utc"][:10].replace("-", "")), _day_epoch(ci["span"]["end_utc"][:10].replace("-", ""))
    return [_ymd(t) for t in range(lo, hi, DAY_S)]


def seal_inputs(*, e009_roots, snapshot_roots, spec: dict, e009_commit: str | None, e010_commit: str | None, scope_decision: str | None = None,
                design_path: Path | None = None, repo: Path = ROOT, git=None) -> dict:
    """LT10's census seal (section 7): every quote day file 20261020..20261031, every pair file with ``refreshed_utc`` in [2026-10-19, 2026-10-31),
    ``refresh.log`` (the refresh-duration lower bound of re-check fix 2) and, per census day, the sidecar and manifest of the last capture COMPLETED
    before the day's 00:00Z, each hashed; plus the frozen design-text sha256, BOTH E009's and E010's analysis commit hashes (each must resolve and be
    an ancestor of HEAD; the census later checks them against the seal's own commit) and the sealed ``scope`` (``ex_crypto`` only with the ledger
    line of an owner decision recorded before the design-text freeze). A file found in two roots with different bytes refuses; missing files are
    listed and counted, never substituted."""
    if (derr := design_text_error(design_path)):
        return derr
    git = git or _git
    commits = {}
    for name, h in (("e009_analysis_commit", e009_commit), ("e010_analysis_commit", e010_commit)):
        if not h or not re.fullmatch(r"[0-9a-f]{7,40}", str(h)):
            return {"error": f"the seal needs both E009's and E010's analysis commit hashes (R1 must-fix 6): {name} missing or malformed"}
        full = git(repo, "rev-parse", "--verify", f"{h}^{{commit}}")
        if full is None:
            return {"error": f"{name} {h} does not resolve to a commit: seal refused"}
        if git(repo, "merge-base", "--is-ancestor", full, "HEAD") is None:
            return {"error": f"{name} {full} is not an ancestor of HEAD: seal refused"}
        commits[name] = full
    scope = spec.get("scope")
    if scope not in SCOPES:
        return {"error": f"spec scope {scope!r} not in {SCOPES}"}
    if scope == "ex_crypto" and not scope_decision:
        return {"error": "scope ex_crypto needs the ledger line of an owner decision recorded before the design-text freeze (1.4 item 2, re-check fix 3)"}
    ci = spec["census_inputs"]
    files, conflicts, missing = {}, [], {"quotes": [], "sidecars": [], "refresh_log": []}

    def put(rel: str, cands: list[Path], kind: str, extra: dict | None = None) -> bool:
        cands = [p for p in cands if p.exists()]
        if not cands:
            return False
        h = sha256_file(check_path(cands[0]))
        for q in cands[1:]:
            if sha256_file(check_path(q)) != h:
                conflicts.append({"file": rel, "root_a": str(cands[0]), "root_b": str(q)})
        files[rel] = {"sha256": h, "root": str(cands[0].parent), "kind": kind, **(extra or {})}
        return True

    for d in ci["quote_days"]:
        found = False
        for suf in (".jsonl.gz", ".jsonl"):
            rel = f"data-dumps/research_lab/cross_venue_live/quotes/{d}{suf}"
            found |= put(rel, [Path(r) / "quotes" / f"{d}{suf}" for r in b_roots(e009_roots)], "quotes", {"day": d})
        if not found:
            missing["quotes"].append(d)
    lo, hi = epoch(ci["pair_refresh_window"][0]), epoch(ci["pair_refresh_window"][1])
    pairs = {}
    for r in b_roots(e009_roots):
        for p in sorted((Path(r) / "pairs").glob("pairs_*.json")):
            rec = load_pair_file(p)
            if lo <= rec["refreshed"] < hi:
                rel = f"data-dumps/research_lab/cross_venue_live/pairs/{p.name}"
                if rel not in files:
                    put(rel, [Path(x) / "pairs" / p.name for x in b_roots(e009_roots)], "pairs", {"refreshed_utc": rec["refreshed_utc"]})
                    pairs[p.name] = {"refreshed_utc": rec["refreshed_utc"], "stamp_ok": rec["stamp_ok"], "n_pairs": len(rec["pairs"])}
    if not put("data-dumps/research_lab/cross_venue_live/refresh.log", [Path(r) / "refresh.log" for r in b_roots(e009_roots)], "refresh_log"):
        missing["refresh_log"].append("refresh.log")
    sidecars = {}
    for d in census_days(spec):
        cap = last_completed_capture(snapshot_roots, _day_epoch(d))
        if cap is None:
            missing["sidecars"].append(d)
            sidecars[d] = None
            continue
        cid = cap["capture"]
        ok_rows = put(f"data-dumps/research_lab/snapshots/{cid}/rows_ext.csv.gz", [Path(r) / cid / "rows_ext.csv.gz" for r in b_roots(snapshot_roots)], "sidecar",
                      {"day": d, "capture": cid})
        put(f"data-dumps/research_lab/snapshots/{cid}/manifest.json", [Path(r) / cid / "manifest.json" for r in b_roots(snapshot_roots)], "sidecar_finish",
            {"day": d, "capture": cid})
        sidecars[d] = {"capture": cid, "finished_utc": cap["finished_utc"], "rows_ext": ok_rows}
        if not ok_rows:
            missing["sidecars"].append(d)
    if conflicts:
        return {"error": "a sealed file exists in two roots with different bytes: LT10 seal refused", "conflicts": conflicts[:50]}
    return {"purpose": "LT10 census inputs (LIVE_TESTS_10.md section 7): quote, pair, refresh-log and sidecar files the censuses may open, each hashed; counts-only use",
            "written_utc": iso(b.now_ts()), "spec_sha256": sha256_file(SPEC_PATH), "design_text_sha256": design_text_sha(design_path), "spec_blocks_sha256": spec_blocks_sha(spec),
            **commits, "scope": scope, "scope_decision": scope_decision, "span": ci["span"], "census_days": census_days(spec), "pairs": pairs, "sidecars": sidecars,
            "missing": missing, "n_missing": {k: len(v) for k, v in missing.items()}, "n_files": len(files), "files": dict(sorted(files.items()))}


def _git(repo: Path, *args: str) -> str | None:
    import subprocess

    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return (r.stdout.strip() or "ok") if r.returncode == 0 else None


def load_for_census(seal: Path, *, e009_roots, snapshot_roots, spec: dict, design_path: Path | None = None) -> dict:
    """The refusals every census runs first (L3): the frozen design text; the seal's design hash; both analysis commit hashes in the seal; the spec's
    scope equal to the sealed scope; the seal-time spec blocks; then every sealed file must be present in some root with an equal sha256. Returns the
    local path of every sealed file; origins are built from the seal, never from a local scan."""
    sd = json.loads(Path(seal).read_text())
    if (derr := design_text_error(design_path)):
        return derr
    if sd.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        return {"error": "the seal was written against a different LIVE_TESTS_10.md: census refused"}
    if not sd.get("e009_analysis_commit") or not sd.get("e010_analysis_commit"):
        return {"error": "the seal lacks E009's or E010's analysis commit hash: census refused (R1 must-fix 6)"}
    if sd.get("scope") != spec.get("scope"):
        return {"error": f"the spec scope {spec.get('scope')!r} differs from the sealed scope {sd.get('scope')!r}: census refused (1.4 item 2)"}
    if sd.get("spec_blocks_sha256") != spec_blocks_sha(spec):
        return {"error": "the spec's census blocks differ from those at seal time: census refused"}
    roots = {"quotes": [Path(r) / "quotes" for r in b_roots(e009_roots)], "pairs": [Path(r) / "pairs" for r in b_roots(e009_roots)],
             "refresh_log": b_roots(e009_roots), "sidecar": None, "sidecar_finish": None}
    local, bad = {}, []
    for rel, meta in sd.get("files", {}).items():
        name = rel.rsplit("/", 1)[1]
        if meta["kind"] in ("sidecar", "sidecar_finish"):
            cands = [Path(r) / meta["capture"] / name for r in b_roots(snapshot_roots)]
        else:
            cands = [Path(r) / name for r in roots[meta["kind"]]]
        hit = None
        for p in cands:
            if p.exists():
                if sha256_file(check_path(p)) == meta["sha256"]:
                    hit = p
                    break
                bad.append({"file": rel, "local": str(p), "error": "sha256 mismatch"})
        if hit is None:
            bad.append({"file": rel, "error": "sealed but absent from every root"})
        local[rel] = hit
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    return {"seal": sd, "local": local}


def _sealed(L: dict, kind: str) -> list[tuple[str, Path, dict]]:
    return [(rel, L["local"][rel], m) for rel, m in sorted(L["seal"]["files"].items()) if m["kind"] == kind]


def census_units(L: dict, spec: dict, *, exclude_event: str | None = None, need_twins: bool = False) -> dict:
    """The census's origin rows over the sealed span, one day batch at a time (origin-side fields only, 1.6; twins through the Kalshi-only
    loader). Returns the unit rows (status unit) with the category and scope columns, every status count, the coverage, the field presence, the
    record lags and the descriptive accumulators. No target is formed."""
    days = census_days(spec)
    span_lo, span_hi = _day_epoch(days[0]), _day_epoch(days[-1]) + DAY_S
    last_origin = span_hi - GRID_S
    read_lo, read_hi = span_lo - LOOKBACK_POLLS * POLL_S, last_origin + TWIN_AHEAD_POLLS * POLL_S
    qfiles = {m["day"]: p for _, p, m in _sealed(L, "quotes")}
    # keys-only pass: L_obs and coverage (no price field)
    key_times: dict[str, list] = {}
    for d in sorted(qfiles):
        kc = read_keys(qfiles[d], read_lo, read_hi)
        for pid, t in zip(kc["pid"], kc["t"], strict=True):
            key_times.setdefault(pid, []).append(int(t))
    key_times = {p: np.array(sorted(set(v)), dtype=np.int64) for p, v in key_times.items()}
    records = [load_pair_file(p) for _, p, _ in _sealed(L, "pairs")]
    CR = CensusRecords(records, key_times, keys_lo=read_lo, L=int(spec["pair_record_rule"]["L_s"]))
    refresh_flags = refresh_duration_flags(next((p for _, p, _ in _sealed(L, "refresh_log")), None), records, spec)
    side_rel = {d: v for d, v in (L["seal"].get("sidecars") or {}).items()}
    scope = spec["scope"]
    units, statuses, cover, presence = [], Counter(), {}, Counter()
    desc = Counter()
    book_same = Counter()
    cache: dict[str, dict] = {}
    for d in days:
        d0 = _day_epoch(d)
        t0 = d0 - LOOKBACK_POLLS * POLL_S
        n = LOOKBACK_POLLS + DAY_S // POLL_S - (GRID_S // POLL_S - 1) + TWIN_AHEAD_POLLS
        prev = _ymd(d0 - DAY_S)
        nxt = _ymd(d0 + DAY_S)
        parts = []
        for dd in (prev, d):
            if dd in qfiles:
                if dd not in cache:
                    cache[dd] = read_quote_file(qfiles[dd], QUOTE_FIELDS, read_lo, last_origin)
                parts.append(cache[dd])
        for k_ in list(cache):
            if k_ not in (prev, d):
                del cache[k_]
        full = concat_cols(parts)
        sel = (full["t"] >= t0) & (full["t"] <= d0 + DAY_S - GRID_S) if len(full["t"]) else np.array([], bool)
        full = {k: v[sel] for k, v in full.items()}
        # the Kalshi-only lag loader: polls after the day's last origin (twins only; section 7)
        kparts = []
        for dd in (d, nxt):
            if dd in qfiles:
                kc = read_quote_file(qfiles[dd], KALSHI_LAG_FIELDS, d0 + DAY_S - GRID_S + POLL_S, min(d0 + DAY_S - GRID_S + TWIN_AHEAD_POLLS * POLL_S, read_hi))
                kparts.append(kc)
        kcols = concat_cols(kparts)
        pids = sorted(set(full["pid"]) | set(kcols["pid"]))
        origins = [t for t in range(d0, d0 + DAY_S, GRID_S)]
        recs = [CR.in_force(t) for t in origins]
        pend = [CR.pending_pids(t, r) for t, r in zip(origins, recs, strict=True)]
        for r in recs:
            if r is not None:
                pids = sorted(set(pids) | set(r["pairs"]))
        if not pids:
            continue
        A = to_grid(full, pids, t0, n, p_until=last_origin)
        overlay_kalshi(A, kcols, pids, t0)
        sc = side_rel.get(d)
        cats = None
        if sc and sc.get("rows_ext"):
            cats = read_sidecar(L["local"][f"data-dumps/research_lab/snapshots/{sc['capture']}/rows_ext.csv.gz"])
        meta = _meta_for(pids, origins, recs, pend, cats, exclude_event)
        ocols = np.array([(t - t0) // POLL_S for t in origins], dtype=np.int64)
        df = build_origins(A, t0, ocols, meta, check_e009=True)
        cov_mask = meta["pair_st"] == ST["unit"]
        pres = A["present"][:, ocols]
        active_pairs = int(cov_mask.any(axis=1).sum())
        cover[d] = {"covered": int((cov_mask & pres).sum()), "active_pairs": active_pairs,
                    "covered_days": float((cov_mask & pres).sum() / (144.0 * active_pairs)) if active_pairs else 0.0}
        _presence(A, pres, cov_mask, ocols, presence)
        _book_staleness(A, ocols, cov_mask, book_same)
        statuses.update(STATUS_CODES[s] for s in df["status"])
        for s in ("end_unknown",):
            desc[s] += int((df["status"] == ST["unit"]).mul(df[s]).sum())
        u = df[df["status"] == ST["unit"]].copy()
        if need_twins and len(u):
            rows_i = np.array([pids.index(p) for p in u["pid"]], dtype=np.int64)
            tw = twins(A, t0, ((u["t"].to_numpy() - t0) // POLL_S)[None, :].astype(np.int64), rows_i[None, :])
            u = pd.concat([u.reset_index(drop=True), tw.reset_index(drop=True)], axis=1)
        u["in_scope"] = [in_scope(s, c, scope) for s, c in zip(u["sports"], u["crypto"], strict=True)]
        u["in_ex_crypto"] = [in_scope(s, c, "ex_crypto") for s, c in zip(u["sports"], u["crypto"], strict=True)]
        units.append(u)
    U = pd.concat(units, ignore_index=True) if units else pd.DataFrame()
    covered_days = float(sum(v["covered_days"] for v in cover.values()))
    return {"U": U, "statuses": dict(statuses), "coverage": cover, "covered_days": covered_days, "presence": dict(presence), "records": CR.lags(),
            "refresh_flags": refresh_flags, "book_same": dict(book_same), "desc": dict(desc), "n_records": len(records)}


def _meta_for(pids: list[str], origins: list[int], recs: list, pend: list, cats: dict | None, exclude_event: str | None) -> dict:
    P, K = len(pids), len(origins)
    m = {"pid": np.array(pids, dtype=object), "pair_st": np.zeros((P, K), dtype=np.int64), "cat_known": np.zeros((P, K), bool), "sports": np.zeros((P, K), bool),
         "crypto": np.full((P, K), "unknown", dtype=object), "ev": np.full((P, K), "", dtype=object), "p_end": np.full((P, K), np.nan),
         "k_close": np.full((P, K), np.nan), "hv": np.zeros((P, K), bool), "fee": np.full((P, K), np.nan), "exclude_event": exclude_event}
    for k, (r, pe) in enumerate(zip(recs, pend, strict=True)):
        for i, pid in enumerate(pids):
            st = pair_status(pid, r, pe)
            m["pair_st"][i, k] = st
            if st != ST["unit"]:
                continue
            rec = r["pairs"][pid]
            m["ev"][i, k] = str(rec.get("p_event_id"))
            m["p_end"][i, k] = epoch(rec.get("p_end")) if rec.get("p_end") else np.nan
            m["k_close"][i, k] = epoch(rec.get("k_close")) if rec.get("k_close") else np.nan
            m["hv"][i, k] = bool(rec.get("hand_verified"))
            m["fee"][i, k] = _f(rec.get("fee_rate"))
            c = cats.get(str(rec.get("p_market_id"))) if cats is not None else None
            if c is not None:
                m["cat_known"][i, k] = True
                m["sports"][i, k], m["crypto"][i, k] = c
    return m


def _presence(A: dict, pres: np.ndarray, cov: np.ndarray, ocols: np.ndarray, acc: Counter) -> None:
    """Section 7 field presence over the census origins' polls of active pairs: shares of Kalshi-valid lines with k_last, k_bid_sz, k_ask_sz,
    k_vol24, k_recv finite and of Polymarket-valid lines with p_bid_sz, p_ask_sz, p_recv finite (finiteness only)."""
    kv = np.isfinite(two_sided_vec(A["k_bid"][:, ocols], A["k_ask"][:, ocols])) & pres & cov
    pv = np.isfinite(two_sided_vec(A["p_bid"][:, ocols], A["p_ask"][:, ocols])) & pres & cov
    acc["k_valid"] += int(kv.sum())
    acc["p_valid"] += int(pv.sum())
    for f in ("k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "k_recv"):
        acc[f] += int((kv & np.isfinite(A[f][:, ocols])).sum())
    for f in ("p_bid_sz", "p_ask_sz", "p_recv"):
        acc[f] += int((pv & np.isfinite(A[f][:, ocols])).sum())


def _book_staleness(A: dict, ocols: np.ndarray, cov: np.ndarray, acc: Counter) -> None:
    """R1 should-fix 9: the share of consecutive Polymarket-valid polls of a pair (both at or before the span's last origin) with an unchanged
    ``p_book_ts`` (equality only)."""
    lo, hi = int(ocols[0]), int(ocols[-1])
    pv = np.isfinite(two_sided_vec(A["p_bid"], A["p_ask"]))
    ts = A["p_book_ts"]
    act = cov.any(axis=1)
    for j in range(max(lo, 1), hi + 1):
        both = pv[:, j] & pv[:, j - 1] & act
        acc["pairs"] += int(both.sum())
        acc["same"] += int((both & (ts[:, j] == ts[:, j - 1])).sum())


def refresh_duration_flags(log_path: Path | None, records: list[dict], spec: dict) -> dict:
    """Re-check fix 2: per refresh summary in ``refresh.log`` (its ``refreshed_utc``, ``k_requests``, ``p_requests``), the duration lower bound
    ``(k_requests + p_requests) / 0.5`` s and whether it exceeds ``L`` (counts only)."""
    rps = float(spec["pair_record_rule"]["refresh_rps"])
    L = int(spec["pair_record_rule"]["L_s"])
    rows = []
    if log_path is not None:
        for raw in iter_complete_lines(log_path):
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if isinstance(d, dict) and "refreshed_utc" in d and "k_requests" in d and "p_requests" in d:
                lb = (float(d["k_requests"] or 0) + float(d["p_requests"] or 0)) / rps
                rows.append({"refreshed_utc": d["refreshed_utc"], "duration_lower_bound_s": lb, "exceeds_L": bool(lb > L)})
    names = {r["refreshed_utc"] for r in records}
    return {"rows": rows, "n_exceeds_L": sum(r["exceeds_L"] for r in rows), "n_sealed_records_with_summary": sum(r["refreshed_utc"] in names for r in rows),
            "n_sealed_records": len(records)}


# --- gate helpers ---------------------------------------------------------------------------------------------------------------------


def g_eff(ev) -> float:
    """Kish effective event count ``(sum m_e)^2 / sum m_e^2`` (1.7, R1 should-fix 6)."""
    m = pd.Series(np.asarray(ev, dtype=object)).value_counts().to_numpy(float)
    return float(m.sum() ** 2 / (m**2).sum()) if len(m) else float("nan")


def de_gate10(ev, scale: float, spec: dict) -> dict:
    """6.1 item 11 / section 7: ``DE_gate = max(51, 1 + (m_w - 1) x 0.0016667)``, ``m_w = sum m_e^2 / sum m_e`` on the projected 21-day units of the
    test in event e (the vendored ``de_gate``: max(floor, computed); NaN stays NaN)."""
    g = spec["census_gates"]["design_effect"]
    m = pd.Series(np.asarray(ev, dtype=object)).value_counts().to_numpy(float) * scale
    mw = float((m**2).sum() / m.sum()) if len(m) and m.sum() > 0 else float("nan")
    de = 1.0 + (mw - 1.0) * float(g["icc"]) if math.isfinite(mw) else float("nan")
    return {"m_w": mw, "DE": de, "DE_gate": b.de_gate({"DE": de}, float(g["floor"]))}


def _frame(U: pd.DataFrame) -> pd.DataFrame:
    """Column aliases the vendored LT helpers read (``market_id`` = the pair, ``t_row`` = the origin, ``event_id`` = the Polymarket event)."""
    X = U.copy()
    X["market_id"], X["t_row"], X["event_id"] = X["pid"].astype(str), X["t"].astype(float), X["ev"].astype(str)
    return X


def rho_x1(U: pd.DataFrame, term: str, min_units: int = 20) -> float:
    """Section 7: the within-pair lag-1 autocorrelation of the tested term over consecutive grid origins (t and t + 600 s) of the test's units,
    expanding-past demeaned, pairs with >= 20 units."""
    X = _frame(U[["pid", "ev", "t", term]].dropna())
    n = X.groupby("market_id")["market_id"].transform("size")
    X = X[n >= min_units]
    if len(X) < 10:
        return float("nan")
    Z = b.demean(X, [term], "market_id", "t_row", "expanding")
    X = X.assign(z=Z[term].to_numpy()).sort_values(["market_id", "t_row"])
    prev_t = X.groupby("market_id")["t_row"].shift(1)
    prev_z = X.groupby("market_id")["z"].shift(1)
    m = (X["t_row"] - prev_t == GRID_S) & np.isfinite(X["z"]) & np.isfinite(prev_z)
    a, c = X["z"][m].to_numpy(float), prev_z[m].to_numpy(float)
    if len(a) < 10 or a.std() == 0 or c.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, c)[0, 1])


def overlap_factor(rho: float) -> float:
    return 1.0 + max(0.0, rho) if math.isfinite(rho) else float("nan")


def modal_hour_share(U: pd.DataFrame, mask) -> float:
    h = U.loc[np.asarray(mask, bool), "hour"]
    return float(h.value_counts().iloc[0] / len(h)) if len(h) else float("nan")


def effective(U: pd.DataFrame, min_units: int = 20) -> pd.Series:
    """Section 7: units of the test in pairs with >= 20 units of the test over the census days."""
    return U.groupby("pid")["pid"].transform("size") >= min_units


def r_gate(U: pd.DataFrame, lead: str, twin: str, min_units: int = 20) -> dict:
    """Section 7: ``r_gate = max(r_w, r_pool)`` of the lead and twin on census units with both; r_w within-pair on expanding-past demeaned values over
    pairs with >= 20 such units (the vendored ``wcorr``); r_pool pooled (printed)."""
    X = _frame(U[["pid", "ev", "t", lead, twin]].dropna())
    X = X[X.groupby("market_id")["market_id"].transform("size") >= min_units]
    r = b.wcorr(X, lead, twin) if len(X) else {"within": None, "pooled": None, "n": 0}
    w, p = r.get("within"), r.get("pooled")
    vals = [v for v in (w, p) if v is not None and math.isfinite(v)]
    return {"r_w": w, "r_pool": p, "r_gate": max(vals) if (w is not None and math.isfinite(w)) else float("nan"), "n": int(r.get("n", 0)), "pairs": int(X["market_id"].nunique())}


def block_gate_share(U: pd.DataFrame, stratum: str, min_pair: int = 4, min_rows: int = 16) -> float:
    """CD10: the share of the test's units that the event-phase gate can shift: units in event x day (CH222: event x two-day block) strata with
    >= 16 rows, counting only pairs with >= 4 units in the stratum (re-check fix 6's disclosed easing)."""
    if U.empty:
        return float("nan")
    X = U[["pid", "ev", stratum]].copy()
    X["g"] = X["ev"].astype(str) + "|" + X[stratum].astype(str)
    n_pg = X.groupby(["g", "pid"])["pid"].transform("size")
    X = X.assign(keep=n_pg >= min_pair)
    rows = X[X["keep"]].groupby("g")["g"].transform("size")
    ok = pd.Series(False, index=X.index)
    ok.loc[rows.index] = rows >= min_rows
    return float(ok.mean())


def design_se10(U: pd.DataFrame, terms: list[str], controls: list[str], contrast: dict, scale: float, spec: dict) -> float:
    """Section 7's design-based SE of a contrast of the tested coefficients, from the census regressors (expanding-past demeaned, intercept) under a
    working covariance with unit variance, correlation 0.5 between a pair's adjacent grid origins (the target overlap), 0.5 between units of one
    event at the same origin, 0.0016667 between any other two units of one event, independence across events; scaled to 21 days with events
    recurring (local terms shrink with the count, the event term does not). No target is read. NaN when the design cannot be formed."""
    w = spec["census_gates"]["working_covariance"]
    r_adj, r_same, r_ev = float(w["adjacent"]), float(w["same_origin_event"]), float(w["event"])
    cols = [*terms, *controls]
    d = _frame(U[["pid", "ev", "t", *cols]].replace([np.inf, -np.inf], np.nan).dropna())
    if len(d) < len(cols) + 10:
        return float("nan")
    X = b.demean(d, cols, "market_id", "t_row", "expanding").replace([np.inf, -np.inf], np.nan).dropna()
    if len(X) < len(cols) + 10:
        return float("nan")
    d = d.loc[X.index]
    A = np.column_stack([np.ones(len(X)), X[cols].to_numpy()])
    inv = np.linalg.pinv(A.T @ A)
    D = A.T @ A
    ev_codes = pd.factorize(d["event_id"].to_numpy())[0]
    C = np.zeros((int(ev_codes.max()) + 1, A.shape[1]))
    np.add.at(C, ev_codes, A)
    S = C.T @ C
    # same event, same origin, different pairs: sum over (event, t) cells of (cell sum outer) minus the diagonal
    cell = pd.factorize(pd.Series(d["event_id"].to_numpy()) + "|" + pd.Series(d["t_row"].to_numpy().astype(np.int64).astype(str)))[0]
    Cc = np.zeros((int(cell.max()) + 1, A.shape[1]))
    np.add.at(Cc, cell, A)
    Ssame = Cc.T @ Cc - D
    # same pair, adjacent grid origins
    order = np.lexsort((d["t_row"].to_numpy(), d["market_id"].to_numpy()))
    pid_o, t_o = d["market_id"].to_numpy()[order], d["t_row"].to_numpy()[order]
    nxt = (pid_o[1:] == pid_o[:-1]) & (t_o[1:] - t_o[:-1] == GRID_S)
    Ao = A[order]
    Aadj = Ao[:-1][nxt].T @ Ao[1:][nxt]
    Sadj = Aadj + Aadj.T
    local = (1.0 - r_ev) * D + (r_same - r_ev) * Ssame + (r_adj - r_ev) * Sadj
    V = inv @ local @ inv / scale + r_ev * (inv @ S @ inv)
    cvec = np.zeros(A.shape[1])
    for name, wt in contrast.items():
        cvec[1 + cols.index(name)] = wt
    var = float(cvec @ V @ cvec)
    return math.sqrt(var) if var > 0 else float("nan")


HOURS = [f"h{h}" for h in range(1, 24)]


def add_hours(U: pd.DataFrame) -> pd.DataFrame:
    X = U.copy()
    for h in range(1, 24):
        X[f"h{h}"] = (X["hour"] == h).astype(float)
    return X


CONTROLS = {
    "CH224": ["sK_s0", "ratio", "sP_s0", "dsP_own", "floorP", "floorK", "traded", "abs_dk1", *b.FEATURES, "rv60_P", "rv60_K", "lkb_t", "lka_t", "lpb_t",
              "lpa_t", "lvol", "vol_unknown", *HOURS],
    "CH223": [*b.FEATURES, "abs_r1", "abs_r6", "abs_dk6", "abs_gap", "rv60_P", "rv60_K", "sP_t", "sK_s0", "floorP", "floorK", "lkb_s0", "lka_s0",
              "lpb_s0", "lpa_s0", "lvol", "vol_unknown", *HOURS],
    "CH222": ["s_r1", "s_r6", "s_gap", "s_dk6", "abs_dk1", "lvl", "lvl2", "s_lvl", "dk1_zrvP", "dk1_zrvK", "rv60_P", "rv60_K", "sP_t", "sK_t", "lkb_t",
              "lka_t", "lpb_t", "lpa_t", "lvol", "vol_unknown", *HOURS],
}
TERM = {"CH224": "zdsK", "CH223": "pull", "CH222": "traded"}
TWIN = {"CH224": "zdsK_tw", "CH223": "pull_tw", "CH222": "traded_tw"}


def population(U: pd.DataFrame, test: str) -> pd.DataFrame:
    """Each test's population filter (sections 2-4) on the eligible units."""
    if test == "CH224":
        return U
    if test == "CH223":
        return U[U["cls223"] == 0]
    if test == "CH222":
        return U[U["cls222"].isin([0, 1])]
    raise KeyError(test)


def add_test_columns(U: pd.DataFrame, scale_K: float | None = None, rv_z: dict | None = None) -> pd.DataFrame:
    """Derived regressors: CH224's ``zdsK = dsK / scale_K`` (the pooled census constant; 6.1 item 4) and its twin; CH222's sign-adjusted
    controls and the ``|dk1| x z rv60`` interactions on the census's pooled centre and scale."""
    X = add_hours(U)
    if scale_K is not None and math.isfinite(scale_K) and scale_K > 0:
        X["zdsK"] = X["dsK"] / scale_K
        if "dsK_tw" in X:
            X["zdsK_tw"] = X["dsK_tw"] / scale_K
    s = X["sign"].to_numpy()
    for c in ("r1", "r6", "gap", "dk6", "lvl"):
        X[f"s_{c}"] = s * X[c].to_numpy()
    if rv_z:
        X["dk1_zrvP"] = X["abs_dk1"] * (X["rv60_P"] - rv_z["rv60_P"]["centre"]) / rv_z["rv60_P"]["scale"]
        X["dk1_zrvK"] = X["abs_dk1"] * (X["rv60_K"] - rv_z["rv60_K"]["centre"]) / rv_z["rv60_K"]["scale"]
    return X


def _scale(days: float) -> float:
    return 21.0 / days if days and math.isfinite(days) and days > 0 else float("nan")


def _pass(d: dict) -> dict:
    d["pass"] = bool(all(bool(v) for k, v in d.items() if k != "pass"))
    return d


def _nan_fail(keys: list[str], why: str) -> dict:
    return {**{k: False for k in keys}, why: False, "pass": False, "values_nan": True}


# --- CF10: the family census ----------------------------------------------------------------------------------------------------------


FIELD_DEPENDENCE = {"k_last": ("CH222", "CH223"), "k_bid_sz": ("CH223",), "k_ask_sz": ("CH223",), "k_recv": TESTS, "p_bid_sz": TESTS, "p_ask_sz": TESTS,
                    "p_recv": TESTS, "k_vol24": ()}


def field_presence(presence: dict, spec: dict) -> dict:
    """Section 7's first stage: each share >= 95%, else the dependent tests' gates are NaN and fail (``k_last`` -> CH222, CH223; Kalshi sizes ->
    CH223; ``k_vol24`` printed only; the receipts and the Polymarket sizes, which every test's eligibility or controls read -> all three)."""
    lim = float(spec["census_gates"]["CF10"]["field_presence_min"])
    shares, dead = {}, set()
    for f, deps in FIELD_DEPENDENCE.items():
        den = presence.get("k_valid" if f.startswith("k_") else "p_valid", 0)
        sh = presence.get(f, 0) / den if den else float("nan")
        shares[f] = sh
        if not (math.isfinite(sh) and sh >= lim):
            dead |= set(deps)
    return {"shares": shares, "min": lim, "dead_tests": sorted(dead)}


def cf10_gates(U: pd.DataFrame, statuses: dict, covered_days: float, presence: dict, spec: dict) -> dict:
    g = spec["census_gates"]["CF10"]
    E = U[U["in_scope"]] if len(U) else U
    fp = field_presence(presence, spec)
    out = {"covered_days": covered_days, "field_presence": fp}

    def counts(E: pd.DataFrame) -> dict:
        n_pair = E.groupby("pid")["pid"].transform("size") if len(E) else pd.Series(dtype=int)
        Ep = E[n_pair >= int(g["pair_min_eligible_origins"])] if len(E) else E
        return {"eligible_origins": int(len(E)), "pairs": int(Ep["pid"].nunique()) if len(Ep) else 0, "events": int(Ep["ev"].nunique()) if len(Ep) else 0,
                "g_eff": g_eff(E["ev"]) if len(E) else float("nan"), "g_event": int(E["ev"].nunique()) if len(E) else 0}

    c0 = counts(E)
    top_ev, top_share = (None, float("nan"))
    if len(E):
        vc = E["ev"].value_counts()
        top_ev, top_share = str(vc.index[0]), float(vc.iloc[0] / vc.sum())
    exclude = top_ev if (math.isfinite(top_share) and top_share > float(g["event_exclusion_share"])) else None
    c1 = counts(E[E["ev"] != exclude]) if exclude else c0
    denom = sum(v for k, v in statuses.items() if k not in ("retired", "not_yet_in_force", "lt10_boundary"))
    late = statuses.get("late_origin", 0) / denom if denom else float("nan")
    gates = {"covered_days_ok": covered_days >= float(g["min_covered_days"]), "field_presence_ok": not set(TESTS) <= set(fp["dead_tests"]),
             "pairs_ok": c1["pairs"] >= int(g["min_pairs"]), "events_ok": c1["events"] >= int(g["min_events"]), "g_eff_ok": c1["g_eff"] >= float(g["min_g_eff"]),
             "late_share_ok": late <= float(g["max_late_share"])}
    if not gates["covered_days_ok"]:
        gates = _nan_fail(list(gates), "covered_days_ok")
    out.update({"counts_before_exclusion": c0, "top_event": top_ev, "top_event_share": top_share, "exclude_event": exclude, "counts": c1,
                "late_origin_share": late, "late_denominator": denom, "gates": _pass(gates)})
    return out


# --- CK10 / CD10 per test --------------------------------------------------------------------------------------------------------------


def ck10_gates(test: str, U: pd.DataFrame, covered_days: float, spec: dict, dead: set[str]) -> dict:
    g = spec["census_gates"]["CK10"][test]
    sc = _scale(covered_days)
    E = U[U["in_scope"]]
    pop = population(E, test)
    out: dict = {"units": int(len(pop)), "projected_units": len(pop) * sc}
    if test == "CH224":
        nz = np.abs(pop["dsK"].to_numpy(float)) > EPS
        per = pop.assign(nz=nz).groupby("pid").agg(n=("nz", "size"), share=("nz", "mean"))
        big = per[per["n"] >= int(g["pair_min_units"])]
        tight, wide = (pop["dsK"] < -EPS).sum(), (pop["dsK"] > EPS).sum()
        scale_K = float(np.nanstd(pop["dsK"].to_numpy(float), ddof=1) * 100.0) if len(pop) > 1 else float("nan")
        X = add_test_columns(pop, scale_K / 100.0 if math.isfinite(scale_K) else None)
        rg = r_gate(X, "zdsK", "zdsK_tw") if "zdsK_tw" in X else {"r_gate": float("nan"), "pairs": 0}
        rho = rho_x1(X, "zdsK") if "zdsK" in X else float("nan")
        out.update({"nonzero_share": float(nz.mean()) if len(nz) else float("nan"), "pairs_500": int(len(big)),
                    "pairs_500_with_5pct": int((big["share"] >= float(g["pair_nonzero_min_share"])).sum()),
                    "tight_share": float(tight / nz.sum()) if nz.sum() else float("nan"), "wide_share": float(wide / nz.sum()) if nz.sum() else float("nan"),
                    "modal_hour_share": modal_hour_share(pop, nz), "r_gate": rg, "scale_K_cents": scale_K, "rho_x1": rho})
        gates = {"projected_units_ok": out["projected_units"] >= float(g["min_projected_units"]), "nonzero_ok": out["nonzero_share"] >= float(g["min_nonzero_share"]),
                 "pair_share_ok": (len(big) > 0 and out["pairs_500_with_5pct"] / len(big) >= float(g["pair_majority"])),
                 "pairs_ok": len(big) >= int(g["min_pairs"]), "signs_ok": min(out["tight_share"], out["wide_share"]) >= float(g["min_sign_share"]),
                 "venue_clock_ok": out["modal_hour_share"] <= float(g["max_modal_hour_share"]),
                 "r_gate_ok": rg["r_gate"] <= float(g["max_r_gate"]) and rg["pairs"] >= int(g["min_r_pairs"])}
        out["values"] = {"scale_K_cents": scale_K, "rho_x1": rho}
    elif test == "CH223":
        quiet = E[E["cls223"].isin([0, 1])]
        pulls = pop["pull"].to_numpy(float) == 1
        wd_share = float(pulls.mean()) if len(pop) else float("nan")
        tq_pull = E[(E["cls223"] == 1) & (E["pull"] == 1)]
        per = pop[pulls].groupby("pid")["moh"].agg(["size", lambda s: s.value_counts().iloc[0] / len(s)])
        per.columns = ["n", "modal"]
        p10 = per[per["n"] >= int(g["min_withdrawals_per_pair"])]
        rho = rho_x1(pop, "pull")
        out.update({"withdrawal_share": wd_share, "projected_withdrawals": float(pulls.sum()) * sc, "traded_pull_share_of_quiet_withdrawals":
                    float(len(tq_pull) / (len(tq_pull) + pulls.sum())) if (len(tq_pull) + pulls.sum()) else float("nan"),
                    "quiet_with_trade_signal": int((quiet["cls223"] == 1).sum()), "modal_hour_share": modal_hour_share(pop, pulls), "rho_pull": rho,
                    "pairs_10": int(len(p10)), "pairs_10_modal_ok": int((p10["modal"] <= float(g["max_modal_minute_share"])).sum()), "rho_x1": rho})
        lo, hi = g["withdrawal_share_range"]
        gates = {"projected_units_ok": out["projected_units"] >= float(g["min_projected_quiet_untraded"]), "share_ok": lo <= wd_share <= hi,
                 "withdrawals_ok": out["projected_withdrawals"] >= float(g["min_projected_withdrawals"]),
                 "venue_clock_ok": out["modal_hour_share"] <= float(g["max_modal_hour_share"]), "autocorr_ok": rho < float(g["max_lag1_autocorr"]),
                 "minute_ok": len(p10) > 0 and out["pairs_10_modal_ok"] / len(p10) >= float(g["pair_majority"]), "pairs_ok": len(p10) >= int(g["min_pairs"])}
        out["values"] = {"rho_x1": rho}
    else:
        moves = E[E["cls222"].isin([0, 1, 2])]
        tr = (pop["cls222"] == 0).sum()
        qo = (pop["cls222"] == 1).sum()
        amb = (moves["cls222"] == 2).sum()
        per = moves.assign(tr=(moves["cls222"] == 0).astype(float)).groupby("pid")["tr"].agg(["size", "std"])
        p20 = per[per["size"] >= int(g["min_moves_per_pair"])]
        rho = rho_x1(pop, "traded")
        out.update({"projected_traded": float(tr) * sc, "projected_quote_only": float(qo) * sc, "traded_share": float(tr / len(moves)) if len(moves) else float("nan"),
                    "ambiguous_share": float(amb / len(moves)) if len(moves) else float("nan"), "modal_hour_share": modal_hour_share(pop, pop["cls222"] == 0),
                    "pairs_20": int(len(p20)), "pairs_20_sd_ok": int((p20["std"].fillna(0) >= float(g["min_within_sd"])).sum()), "rho_x1": rho})
        lo, hi = g["traded_share_range"]
        gates = {"traded_ok": out["projected_traded"] >= float(g["min_projected_traded"]), "quote_only_ok": out["projected_quote_only"] >= float(g["min_projected_quote_only"]),
                 "share_ok": lo <= out["traded_share"] <= hi, "ambiguous_ok": out["ambiguous_share"] <= float(g["max_ambiguous_share"]),
                 "venue_clock_ok": out["modal_hour_share"] <= float(g["max_modal_hour_share"]),
                 "sd_ok": len(p20) > 0 and out["pairs_20_sd_ok"] / len(p20) >= float(g["pair_majority"]), "pairs_ok": len(p20) >= int(g["min_pairs"])}
        out["values"] = {"rho_x1": rho}
    if not (covered_days >= float(spec["census_gates"]["CF10"]["min_covered_days"])):
        gates = _nan_fail(list(gates), "covered_days_ok")
    if test in dead:
        gates = _nan_fail(list(gates), "field_presence_ok")
    out["gates"] = _pass(gates)
    return out


def mde_declared(test: str, n1: float, n2: float | None, de: float, vif: float, of: float, spec: dict) -> float:
    """Sections 2-4's closed formulas (price units) at the census counts: CH224 ``3.47 x SD / sqrt(n_eff) x sqrt(DE) x 1.5 x sqrt(max(1, VIF_w)) x
    2.2 x sqrt(OF)`` (the vendored ``mde_slope_declared`` x gap x sqrt(OF)); CH223 / CH222 ``3.47 x SD x sqrt(1/n1 + 1/n2) x sqrt(DE) x 1.5 x
    sqrt(max(1, VIF_w)) x sqrt(OF)`` (the vendored ``mde_class`` x sqrt(OF)). ``t_sum = max(3.47, exact)`` (the vendored ``mde_common``)."""
    a = b.mde_common(spec)
    sd = float(spec["mde_planning"][test]["sd"])
    if not (math.isfinite(of) and math.isfinite(vif)):
        return float("inf")
    if test == "CH224":
        return b.mde_slope_declared(n1, sd, de, a, vif) * float(spec["mde_planning"]["CH224"]["gap_sd"]) * math.sqrt(of)
    return b.mde_class(n1, n2, sd, de, a, vif) * math.sqrt(of)


def cd10_gates(test: str, U: pd.DataFrame, covered_days: float, spec: dict, ck: dict) -> dict:
    """CD10 (section 7): G_eff, VIF_w, the within-pair (and pooled) correlation caps, the block-gate share, the MDE gate ``max(declared, design)``
    and the F-MDE (CH224 binding; CH223 / CH222 printed)."""
    g = spec["census_gates"]["CD10"][test]
    sc = _scale(covered_days)
    a = b.mde_common(spec)
    sd = float(spec["mde_planning"][test]["sd"])
    E = U[U["in_scope"]]
    scale_K = ck.get("CH224", {}).get("values", {}).get("scale_K_cents")
    rv_z = None
    if test == "CH222":
        mv = population(E, "CH222")
        rv_z = {k: {"centre": float(np.nanmean(mv[k])), "scale": float(np.nanstd(mv[k], ddof=1))} for k in ("rv60_P", "rv60_K")}
    X = add_test_columns(population(E, test), (scale_K / 100.0) if scale_K else None, rv_z)
    term, ctrl = TERM[test], CONTROLS[test]
    if term not in X:
        return {"gates": _nan_fail(["term"], "term_available"), "error": f"{term} unavailable (scale_K missing)"}
    F = _frame(X)
    dsg = b.design_ss(F, term, ctrl)
    vif = dsg["vif_w"]
    eff = effective(X)
    de = de_gate10(X["ev"], sc, spec)
    rho = float(ck.get(test, {}).get("values", {}).get("rho_x1", float("nan")))
    of = overlap_factor(rho)
    stratum = "block2" if test == "CH222" else "day"
    if test == "CH222":
        anchor = _day_epoch(census_days(spec)[0])
        X["block2"] = ((X["t"] - anchor) // (2 * DAY_S)).astype(int)
    share = block_gate_share(X, stratum)
    corr = {}
    for x in g["within_corr_terms"]:
        corr[x] = b.wcorr(F, term, x)
    pooled_ok = all(b.corr_ok(b.wcorr(F, term, x), float(g["max_abs_corr"]), both=True) for x in g["pooled_corr_terms"])
    within_ok = all(b.corr_ok(r, float(g["max_abs_corr"])) for r in corr.values())
    if test == "CH224":
        n_eff = float(eff.sum()) * sc
        declared = mde_declared(test, n_eff, None, de["DE_gate"], vif, of, spec)
        se = design_se10(X, [term], ctrl, {term: 1.0}, sc, spec)
        design = a["t_sum"] * a["day_factor"] * sd * se * float(spec["mde_planning"]["CH224"]["gap_sd"]) if math.isfinite(se) else float("inf")
    else:
        n1 = float((eff & (X[term] == 1)).sum()) * sc
        n2 = float((eff & (X[term] == 0)).sum()) * sc
        declared = mde_declared(test, n1, n2, de["DE_gate"], vif, of, spec)
        se = design_se10(X, [term], ctrl, {term: 1.0}, sc, spec)
        design = a["t_sum"] * a["day_factor"] * sd * se if math.isfinite(se) else float("inf")
    mde_c = float(max(declared, design)) * 100.0 if math.isfinite(declared) else float("inf")
    # F-MDE: max(design MDE of Delta in the arm model, MDE x sqrt(2 / (1 - max(0, r_gate))))
    tw = TWIN[test]
    fm = {"f_mde_c": float("inf")}
    if tw in X:
        arm = X[np.isfinite(X[tw])]
        rg = r_gate(arm, term, tw)
        se_d = design_se10(arm, [term, tw], ctrl, {term: 1.0, tw: -1.0}, sc, spec)
        gap = float(spec["mde_planning"]["CH224"]["gap_sd"]) if test == "CH224" else 1.0
        des_d = a["t_sum"] * a["day_factor"] * sd * se_d * gap * 100.0 if math.isfinite(se_d) else float("inf")
        rr = rg["r_gate"]
        dec_d = mde_c * math.sqrt(2.0 / (1.0 - max(0.0, rr))) if (math.isfinite(rr) and rr < 1) else float("inf")
        fm = {"r_gate": rg, "declared_c": dec_d, "design_c": des_d, "f_mde_c": float(max(dec_d, des_d)), "arm_units": int(len(arm)), "arm_share": len(arm) / max(1, len(X))}
    gates = {"g_eff_ok": g_eff(X["ev"]) >= float(g["min_g_eff"]), "vif_ok": vif <= float(g["max_vif_w"]), "within_corr_ok": within_ok, "pooled_corr_ok": pooled_ok,
             "block_share_ok": share >= float(g["min_block_share"]), "mde_ok": mde_c <= float(g["max_mde_c"])}
    if F_ROLES[test] == "binding":
        gates["f_mde_ok"] = fm["f_mde_c"] <= float(g["max_f_mde_c"])
    if not (covered_days >= float(spec["census_gates"]["CF10"]["min_covered_days"])):
        gates = _nan_fail(list(gates), "covered_days_ok")
    out = {"units": int(len(X)), "effective_units": int(eff.sum()), "g_eff": g_eff(X["ev"]), "g_event": int(X["ev"].nunique()), "vif_w": vif, "design_ss": dsg,
           "corr": corr, "block_gate_share": share, "de": de, "of": of, "mde": {"declared_c": declared * 100.0, "design_c": design * 100.0, "se_1": se, "mde_c": mde_c},
           "f_mde": fm, "f_role": F_ROLES[test], "values": {"DE_gate": de["DE_gate"], "OF": of, **({"rv_z": rv_z} if rv_z else {})}, "gates": _pass(gates)}
    return out


def descriptive(R: dict, spec: dict) -> dict:
    """Section 7's descriptive prints (no gate): scope splits, the with-sports (ex_crypto) values printed only, G_eff beside G_event, pair-record
    lags and refresh-duration flags, p_book_ts staleness, k_vol24 decreases, status shares, receipt lags, the event size distribution, overlaps."""
    U = R["U"]
    out = {"statuses": R["statuses"], "records": R["records"], "refresh_duration": R["refresh_flags"], "coverage": R["coverage"],
           "p_book_ts_unchanged_share": (R["book_same"].get("same", 0) / R["book_same"]["pairs"]) if R["book_same"].get("pairs") else None}
    if U.empty:
        return out
    steps = U["win_steps"].sum()
    out.update({
        "scope_split": {"in_scope": int(U["in_scope"].sum()), "sports": int(U["sports"].sum()), "crypto": int((U["crypto"] == "crypto").sum()),
                        "crypto_unknown": int((U["crypto"] == "unknown").sum()), "ex_crypto_print_only": int(U["in_ex_crypto"].sum())},
        "k_vol24_decrease_share_of_window_steps": float(U["kvol_down_steps"].sum() / steps) if steps else None,
        "receipt_lag_q": {k: [float(x) for x in np.nanquantile(U[k], [0.5, 0.9, 0.99])] for k in ("klag", "plag")},
        "event_sizes": U[U["in_scope"]].groupby("ev")["pid"].nunique().value_counts().sort_index().to_dict(),
        "hand_verified_share": float(U["hv"].mean()),
        "pairs_per_day": U.groupby("day")["pid"].nunique().to_dict(), "events_per_day": U.groupby("day")["ev"].nunique().to_dict(),
        "CH224": {"dsK_ticks": (np.round(U["dsK"] / 0.01)).value_counts().sort_index().head(41).to_dict(), "floorP_share": float(U["floorP"].mean()),
                  "floorK_share": float(U["floorK"].mean()), "rewarded_share": "not computed: the reward feed is not a sealed census input (section 7 inputs)"},
        "CH223": {"classes": {CLASS223[k]: int(v) for k, v in U["cls223"].value_counts().items()},
                  "withdrawals_by_kind": {"widen": int((U["widen"] & (U["cls223"] == 0)).sum()), "size_fall": int(((U["bid_fall"] | U["ask_fall"]) & (U["cls223"] == 0)).sum())},
                  "pull_side": U.loc[(U["cls223"] == 0) & (U["pull"] == 1), "pull_side"].value_counts().to_dict(),
                  "traded_pull": int(((U["cls223"] == 1) & (U["pull"] == 1)).sum()), "size_zero": int((U["size_zero"] & (U["cls223"] == 0)).sum()),
                  "minute_of_hour": U.loc[(U["cls223"] == 0) & (U["pull"] == 1), "moh"].value_counts().sort_index().to_dict()},
        "CH222": {"classes": {CLASS222[k]: int(v) for k, v in U["cls222"].value_counts().items()},
                  "trade_steps": U.loc[U["cls222"] == 0, "trade_steps"].value_counts().sort_index().to_dict(),
                  "move_size_c": (np.round(U.loc[U["cls222"] < 3, "abs_dk1"] * 200) / 2).value_counts().sort_index().head(30).to_dict()},
        "overlap_CH222_CH223": int(((U["cls222"] < 3) & (U["cls223"] == 0)).sum()),
    })
    return out


def census_family(*, seal: Path, e009_roots, snapshot_roots, spec: dict, design_path: Path | None = None) -> dict:
    """CF10 (section 7): the full origin-side eligibility of 1.4 in one streaming pass; the family gates; ``exclude_event``."""
    L = load_for_census(seal, e009_roots=e009_roots, snapshot_roots=snapshot_roots, spec=spec, design_path=design_path)
    if "error" in L:
        return L
    R = census_units(L, spec)
    res = cf10_gates(R["U"], R["statuses"], R["covered_days"], R["presence"], spec)
    return {"census": "CF10", "counts_only": True, **res, "alive": ([t for t in TESTS if t not in res["field_presence"]["dead_tests"]] if res["gates"]["pass"] else []),
            "descriptive": descriptive(R, spec), "values": {"exclude_event": res["exclude_event"]}}


def census_kalshi(*, seal: Path, e009_roots, snapshot_roots, spec: dict, cf10: dict, design_path: Path | None = None) -> dict:
    """CK10: the Kalshi-side state shares of the tests still alive after CF10 (refuses unless CF10 passed)."""
    if not cf10.get("gates", {}).get("pass"):
        return {"error": "CF10 did not pass: CK10 does not run (stage order, section 7)"}
    L = load_for_census(seal, e009_roots=e009_roots, snapshot_roots=snapshot_roots, spec=spec, design_path=design_path)
    if "error" in L:
        return L
    R = census_units(L, spec, exclude_event=cf10.get("exclude_event"), need_twins=True)
    dead = set(cf10["field_presence"]["dead_tests"])
    per = {t: ck10_gates(t, R["U"], R["covered_days"], spec, dead) for t in cf10.get("alive", [])}
    return {"census": "CK10", "counts_only": True, "exclude_event": cf10.get("exclude_event"), "tests": per, "covered_days": R["covered_days"],
            "alive": [t for t, v in per.items() if v["gates"]["pass"]]}


def census_design(*, seal: Path, e009_roots, snapshot_roots, spec: dict, cf10: dict, ck10: dict, design_path: Path | None = None) -> dict:
    """CD10: the design gates of the CK10 survivors (refuses unless CK10 named at least one)."""
    alive = ck10.get("alive") or []
    if not alive:
        return {"error": "no test survived CK10: CD10 does not run (stage order, section 7)"}
    L = load_for_census(seal, e009_roots=e009_roots, snapshot_roots=snapshot_roots, spec=spec, design_path=design_path)
    if "error" in L:
        return L
    R = census_units(L, spec, exclude_event=cf10.get("exclude_event"), need_twins=True)
    per = {t: cd10_gates(t, R["U"], R["covered_days"], spec, ck10["tests"]) for t in alive}
    return {"census": "CD10", "counts_only": True, "tests": per, "k_tests": [t for t in TESTS if t in per and per[t]["gates"]["pass"]],
            "covered_days": R["covered_days"], "census_fixed": {"exclude_event": cf10.get("exclude_event"),
                                                                "scale_K_cents": ck10["tests"].get("CH224", {}).get("values", {}).get("scale_K_cents"),
                                                                **{t: per[t]["values"] for t in per}}}


# --- the event-phase block Freedman-Lane gate (1.8, R1 must-fix 4) -------------------------------------------------------------------


def phase_offset(o: int, n_p: int, n_g: int) -> int:
    """``o_p = round(o x n_p / n_g)`` (half up), the pair's share of the stratum's common phase ``o / n_g``."""
    return int(math.floor(o * n_p / n_g + 0.5))


def event_phase_plan(strata: np.ndarray, pair: np.ndarray, order: np.ndarray, min_pair: int = 4, min_rows: int = 16) -> dict:
    """Per stratum (event x day, or event x two-day block), the row indices of each pair with >= 4 units in it, ordered by origin; strata with
    fewer than 16 such rows are excluded. Counts of excluded pairs and strata are returned."""
    plan, ex_pairs, ex_strata, ex_rows = [], 0, 0, 0
    for g in np.unique(strata):
        gi = np.flatnonzero(strata == g)
        members = []
        for p in np.unique(pair[gi]):
            pi = gi[pair[gi] == p]
            if len(pi) >= min_pair:
                members.append(pi[np.argsort(order[pi], kind="mergesort")])
            else:
                ex_pairs += 1
                ex_rows += len(pi)
        if sum(len(m) for m in members) < min_rows:
            ex_strata += 1
            ex_rows += sum(len(m) for m in members)
            continue
        plan.append(members)
    return {"plan": plan, "excluded_pairs": ex_pairs, "excluded_strata": ex_strata, "excluded_rows": ex_rows}


def event_phase_shift(e: np.ndarray, plan: list[list[np.ndarray]], n_g: int, rng: np.random.Generator) -> tuple[np.ndarray, list[int]]:
    """One draw: per stratum ONE offset ``o`` uniform on the integers ``[s, n_g - s]``, ``s = max(4, ceil(n_g / 4))``; every pair p of the stratum
    has its residuals (ordered by origin) circularly shifted by ``o_p = round(o x n_p / n_g)`` (the same phase for every pair of the event). Rows
    outside the plan are unchanged."""
    s = max(4, math.ceil(n_g / 4))
    ep = e.copy()
    offs = []
    for members in plan:
        o = int(rng.integers(s, n_g - s + 1))
        offs.append(o)
        for idx in members:
            ep[idx] = np.roll(e[idx], phase_offset(o, len(idx), n_g))
    return ep, offs


def event_phase_fl_gate(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, stratum: str, n_g: int, draws: int, seed: int, sign: int = 1,
                        group: str = "pid", order: str = "t", event: str = "ev", min_pair: int = 4, min_rows: int = 16) -> dict:
    """The event-phase block (circular-shift) Freedman-Lane gate (1.8): expanding-past demeaning of every regressor within pair; the reduced
    model's residuals (``y`` on the controls) shifted by one common phase per event stratum (``stratum`` = the day or the two-day block; strata are
    event x stratum); the full model refitted (Frisch-Waugh: ``beta* = x~' e* / x~' x~``); ``p_perm = (1 + #{sign beta* >= sign beta}) / (1 + draws)``;
    passes if < 0.05. The same rule as the vendored LT5 ``block_fl_gate`` except the strata and the common offset."""
    X = b.demean(df, [term, *controls], group, order, "expanding")
    yv = np.asarray(y, float)
    ok = np.isfinite(yv) & np.all(np.isfinite(X.to_numpy()), axis=1)
    if ok.sum() < 10:
        return {"testable": False, "passes": False, "reason": "fewer than 10 rows"}
    Z = X[controls].to_numpy()[ok] if controls else np.zeros((int(ok.sum()), 0))
    xt = b._partial(Z, X[term].to_numpy()[ok])
    e = b._partial(Z, yv[ok])
    sxx = float(xt @ xt)
    if sxx <= 1e-18:
        return {"testable": False, "passes": False, "reason": "no residual variation in the term"}
    real = float(xt @ e / sxx)
    strata = (df[event].astype(str) + "|" + df[stratum].astype(str)).to_numpy()[ok]
    pl = event_phase_plan(strata, df[group].astype(str).to_numpy()[ok], df[order].to_numpy(float)[ok], min_pair, min_rows)
    if not pl["plan"]:
        return {"testable": False, "passes": False, "reason": "no stratum with >= 16 rows of pairs with >= 4 units", **{k: v for k, v in pl.items() if k != "plan"}}
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(draws):
        ep, _o = event_phase_shift(e, pl["plan"], n_g, rng)
        ge += int(sign * float(xt @ ep / sxx) >= sign * real)
    p = (1 + ge) / (1 + draws)
    shifted = sum(len(i) for m in pl["plan"] for i in m)
    return {"testable": True, "real": real, "p_perm": p, "passes": bool(p < 0.05), "draws": draws, "method": "event-phase block circular-shift Freedman-Lane",
            "n_g": n_g, "strata": len(pl["plan"]), "excluded_pairs": pl["excluded_pairs"], "excluded_strata": pl["excluded_strata"],
            "share_rows_shifted": shifted / int(ok.sum())}


# --- the window reader's state pass (8.1 run_once; targets and twins are code phase 2) --------------------------------------------------


def seen_log(out_root: Path) -> list[dict]:
    p = Path(out_root) / "pairs_seen.jsonl"
    if not p.exists():
        return []
    return [json.loads(x) for x in iter_complete_lines(check_path(p))]


def update_seen(xv_root: Path, out_root: Path, run_id: str, now: float) -> set[str]:
    """Record the first sighting of every successor pair file (1.2 window rule (iii)); returns the names seen at or before this run."""
    seen = {r["name"] for r in seen_log(out_root)}
    new = []
    for p in sorted((Path(xv_root) / "pairs").glob("pairs_*.json")):
        if p.name in seen:
            continue
        rec = load_pair_file(p)
        new.append({"name": p.name, "sha256": rec["sha256"], "refreshed_utc": rec["refreshed_utc"], "seen_utc": iso(now), "run": run_id})
        seen.add(p.name)
    if new:
        b.append_jsonl(check_path(Path(out_root) / "pairs_seen.jsonl"), new)
    return seen


def _role(spec: dict) -> str:
    return "prospective_confirmation" if (spec.get("_pinned") and SPEC_SHA256) else "prospective_unregistered"


def run_once(*, xv_root: Path = XV_ROOT, out_root: Path = OUT_ROOT, snapshot_roots=None, spec: dict | None = None, now: float | None = None,
             max_origins: int = 288, feed_roots=None, freeze_clock=None) -> dict:
    """One reader run (8.1, code phase 1 part): origin statuses and frozen state lines for every origin t whose successor cycle is over (the
    ``runs.jsonl`` line of cycle t, or of a later cycle, exists; 1.2 re-check fix 1), with the record in force by :class:`WindowRecords`.
    Write-once (``%.17g``, atomic hard link): ``status/<YYYYMMDD>/<HHMM>.csv.gz`` and ``<kind>/frozen/<YYYYMMDD>/<HHMM>.csv.gz`` (or ``.late.csv.gz``
    when written at or after t + 1,080 s, 1.3). An origin whose status file exists is never processed again. Internal non-blocking run lock."""
    from .xv_quotes_poller import read_runs

    spec = spec or load_spec(sha=None)
    out_root = Path(out_root)
    injected = now is not None
    now = b.now_ts() if now is None else now
    check_path(out_root / "run.lock")
    out_root.mkdir(parents=True, exist_ok=True)
    lock = open(out_root / "run.lock", "w")  # noqa: SIM115
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return {"status": "locked", "exit": TEMPFAIL}
    try:
        if b.dir_bytes(out_root) > float(spec["reader"]["max_store_bytes"]):
            return {"status": "store above its disk limit: refused", "exit": 3}
        run_id = iso(now)
        seen = update_seen(xv_root, out_root, run_id, now)
        runs = read_runs(Path(xv_root)) if check_path(Path(xv_root) / "runs.jsonl").exists() else []
        records = [load_pair_file(p) for p in sorted((Path(xv_root) / "pairs").glob("pairs_*.json"))]
        W = WindowRecords(records, runs, seen, L=int(spec["pair_record_rule"]["L_s"]))
        reg, end = int(epoch(spec["registered_utc"])), int(epoch(spec["end_utc"]))
        if W.last_cycle is None:
            return {"status": "no successor cycle yet", "exit": TEMPFAIL}
        todo = [t for t in range(reg, min(end, W.last_cycle + 1), GRID_S) if not _status_path(out_root, t).exists()][:max_origins]
        if not todo:
            fu = followups(xv_root, out_root, W, spec, now, max_origins)
            return {"status": "ok" if fu else "nothing new", "exit": 0 if fu else TEMPFAIL, "followups": dict(fu)}
        t_lo, t_hi = todo[0] - LOOKBACK_POLLS * POLL_S, todo[-1]
        days = sorted({_ymd(x) for x in range(t_lo - t_lo % DAY_S, t_hi + 1, DAY_S)})
        parts = []
        for d in days:
            for suf in (".jsonl", ".jsonl.gz"):
                p = Path(xv_root) / "quotes" / f"{d}{suf}"
                if p.exists():
                    parts.append(read_quote_file(p, QUOTE_FIELDS, t_lo, t_hi, src=SRC_SUCCESSOR))
        cols = concat_cols(parts)
        recs = [W.in_force(t) for t in todo]
        pend = [W.pending_pids(t, r) for t, r in zip(todo, recs, strict=True)]
        pids = sorted(set(cols["pid"]) | {p for r in recs if r is not None for p in r["pairs"]})
        written = Counter()
        if pids:
            t0 = t_lo - (t_lo % POLL_S)
            n = (t_hi - t0) // POLL_S + 1
            A = to_grid(cols, pids, t0, n)
            cats_by_day, cond_by_day, feed_by_day = {}, {}, {}
            for d in {_ymd(t) for t in todo}:
                cap = last_completed_capture(snapshot_roots, _day_epoch(d)) if snapshot_roots else None
                has = bool(cap and (cap["dir"] / "rows_ext.csv.gz").exists())
                cats_by_day[d] = read_sidecar(cap["dir"] / "rows_ext.csv.gz") if has else None
                cond_by_day[d] = read_sidecar_cond(cap["dir"] / "rows_ext.csv.gz") if has else {}
                feed_by_day[d] = feed_listing(feed_roots, _day_epoch(d)) if feed_roots else None
            for k, t in enumerate(todo):
                meta = _meta_for(pids, [t], [recs[k]], [pend[k]], cats_by_day[_ymd(t)], (spec.get("census_fixed") or {}).get("exclude_event"))
                if t - LOOKBACK_POLLS * POLL_S < reg:
                    meta["pair_st"][:, 0] = np.where(meta["pair_st"][:, 0] == ST["unit"], ST["lt10_boundary"], meta["pair_st"][:, 0])
                df = build_origins(A, t0, np.array([(t - t0) // POLL_S]), meta, check_e009=True)
                keep = (meta["pair_st"][:, 0] == ST["unit"]) | A["present"][:, (t - t0) // POLL_S] | (meta["pair_st"][:, 0] != ST["retired"])
                df = df[keep]
                df = _join_reward(df, recs[k], cond_by_day[_ymd(t)], feed_by_day[_ymd(t)])
                if not W.cycle_ran(t):
                    df.loc[df["status"] == ST["unit"], "status"] = ST["poll_missing"]
                written[_write_origin(out_root, t, df, spec, freeze_clock(t) if freeze_clock else (now if injected else b.now_ts()))] += 1
        fu = followups(xv_root, out_root, W, spec, now, max_origins)
        written.update({f"followup_{k}": v for k, v in fu.items()})
        b.append_jsonl(Path(out_root) / "runs.jsonl", [{"run": run_id, "origins": len(todo), "first": iso(todo[0]), "last": iso(todo[-1]), "results": dict(written),
                                                        "code_sha256": code_hashes().get("live_tests10.py"), "spec_sha256": spec["_sha256"]}])
        return {"status": "ok", "exit": 0, "origins": len(todo), "results": dict(written)}
    finally:
        lock.close()


def _join_reward(df: pd.DataFrame, rec: dict | None, cond: dict[str, str], feed: dict | None) -> pd.DataFrame:
    """Economics only (1.2): ``rewarded`` (1 listed / 0 not listed in the day's last usable feed capture; NaN without a feed or a condition_id) and the
    gross ``reward_rate`` (summed positive rate_per_day of the listing)."""
    out_r, out_x = [], []
    for pid in df["pid"]:
        mk = str((rec or {}).get("pairs", {}).get(pid, {}).get("p_market_id"))
        cid = cond.get(mk)
        if feed is None or not cid:
            out_r.append(np.nan)
            out_x.append(np.nan)
        else:
            out_r.append(1.0 if cid in feed["rates"] else 0.0)
            out_x.append(feed["rates"].get(cid, np.nan))
    df = df.copy()
    df["rewarded"], df["reward_rate"] = out_r, out_x
    return df


def _status_path(out_root: Path, t: int) -> Path:
    d, hm = _ymd(t), pd.Timestamp(t, unit="s", tz="UTC").strftime("%H%M")
    return Path(out_root) / "status" / d / f"{hm}.csv.gz"


FROZEN_COLS = ["pid", "ev", "t", "dec", "kmid", "pmid", "sK_t", "sP_t", "sK_s0", "sP_s0", "dsK", "dsP_own", "ratio", "floorP", "floorK", "tightK", "wideK",
               "traded", "trade_steps", "kvol_up", "vol_unknown", "pull", "widen", "bid_fall", "ask_fall", "pull_side", "size_zero", "cls223", "cls222",
               *b.FEATURES, "abs_dk1", "abs_r1", "abs_r6", "abs_dk6", "abs_gap", "rv60_P", "rv60_K", "lkb_t", "lka_t", "lpb_t", "lpa_t", "lkb_s0", "lka_s0",
               "lpb_s0", "lpa_s0", "lvol", "p_tick", "hv", "fee_rate", "rewarded", "reward_rate", "sports", "crypto", "s0_t", "n_win"]


def _write_origin(out_root: Path, t: int, df: pd.DataFrame, spec: dict, wtime: float) -> str:
    """Write-once status file and, for the units, one frozen file per kind (late: the ``.late`` marker instead; 1.3)."""
    st = df[["pid", "ev", "t", "status", "cls223", "cls222"]].copy()
    st["status"] = [STATUS_CODES[s] for s in st["status"]]
    st["role"], st["spec_sha"], st["code_sha"] = _role(spec), spec["_sha256"][:16], (code_hashes().get("live_tests10.py") or "")[:16]
    u = df[df["status"] == ST["unit"]].copy()
    for c_ in ("fee_rate", "rewarded", "reward_rate"):
        if c_ not in u:
            u[c_] = np.nan
    late = wtime >= t + int(spec["reader"]["freeze_before_s"])
    d, hm = _ymd(t), pd.Timestamp(t, unit="s", tz="UTC").strftime("%H%M")
    for test, kind in KINDS.items():
        pop = population(u, test)
        if not len(pop):
            continue
        fr = pop[FROZEN_COLS].copy()
        fr["in_scope"] = [in_scope(s, c, spec["scope"]) for s, c in zip(fr["sports"], fr["crypto"], strict=True)]
        fr["written_utc"], fr["role"], fr["spec_sha"], fr["code_sha"] = iso(wtime), _role(spec), spec["_sha256"][:16], (code_hashes().get("live_tests10.py") or "")[:16]
        name = f"{hm}.late.csv.gz" if late else f"{hm}.csv.gz"
        b.write_once_csv(check_path(Path(out_root) / kind / "frozen" / d / name), fr)
    b.write_once_csv(check_path(_status_path(out_root, t)), st)
    return "late" if late else "frozen"


# --- the reader's follow-up writers: targets and far-future twins (8.1; read only polls AFTER the frozen origin) -----------------------------------


HORIZON_MIN = {"hedge": (10, 20), "flinch": (10, 20), "traded": (10, 20, 60)}  # S1 +10 min, the primary +20 min, CH222's M1 +60 min
TG_NAMES = {0: "two_sided", 1: "one_sided", 2: "late", 3: "absent", 4: "poll_missing"}


def _origin_of(path: Path) -> int:
    return _day_epoch(path.parent.name) + int(path.name[:2]) * 3600 + int(path.name[2:4]) * 60


def pending_followups(out_root: Path, W: WindowRecords, limit: int) -> dict[int, list]:
    """Frozen (not ``.late``) unit files whose target (+h) or twin file is missing and whose last needed poll's cycle has run (no endpoint is read
    before the successor's ``runs.jsonl`` shows the cycle t + h + 120 s over)."""
    items: dict[int, list] = {}
    if W.last_cycle is None:
        return items
    for kind in KINDS.values():
        for p in sorted((Path(out_root) / kind / "frozen").glob("*/*.csv.gz")):
            if p.name.endswith(".late.csv.gz") or len(p.name) != len("0000.csv.gz"):
                continue
            t, d, hm = _origin_of(p), p.parent.name, p.name[:4]
            need = [("h", h) for h in HORIZON_MIN[kind] if not (Path(out_root) / kind / "outcomes" / d / f"{hm}.h{h}.csv.gz").exists()
                    and W.last_cycle >= t + h * 60 + POLL_S]
            if not (Path(out_root) / kind / "twins" / d / f"{hm}.csv.gz").exists() and W.last_cycle >= t + TWIN_AHEAD_POLLS * POLL_S:
                need.append(("tw", 0))
            if need:
                items.setdefault(t, []).append((kind, p, need))
    return dict(sorted(items.items())[:limit])


def followups(xv_root: Path, out_root: Path, W: WindowRecords, spec: dict, now: float, limit: int = 288) -> Counter:
    """Write-once ``<kind>/outcomes/<d>/<HHMM>.h<min>.csv.gz`` (pid, t, target status, Polymarket mid, spread and touch sizes at the endpoint) and
    ``<kind>/twins/<d>/<HHMM>.csv.gz`` (Kalshi-only far-future states, read through the Kalshi-only lag loader). A target status never turns into
    another: files are never rewritten."""
    out = Counter()
    items = pending_followups(out_root, W, limit)
    if not items:
        return out
    ts = sorted(items)
    t_lo, t_hi = ts[0], ts[-1] + 3600 + POLL_S
    days = sorted({_ymd(x) for x in range(t_lo - t_lo % DAY_S, t_hi + 1, DAY_S)})
    full_parts, k_parts = [], []
    for d in days:
        for suf in (".jsonl", ".jsonl.gz"):
            f = Path(xv_root) / "quotes" / f"{d}{suf}"
            if f.exists():
                full_parts.append(read_quote_file(f, QUOTE_FIELDS, t_lo, t_hi, src=SRC_SUCCESSOR))
                k_parts.append(read_quote_file(f, KALSHI_LAG_FIELDS, t_lo, t_hi, src=SRC_SUCCESSOR))
    cols, kcols = concat_cols(full_parts), concat_cols(k_parts)
    pids = sorted(set(cols["pid"]))
    t0 = t_lo - (t_lo % POLL_S)
    n = (t_hi - t0) // POLL_S + 1
    A = to_grid(cols, pids, t0, n)
    Ak = to_grid(kcols, pids, t0, n)  # Kalshi fields only: no Polymarket column is ever in this grid
    idx = {p: i for i, p in enumerate(pids)}
    meta = {"wrote": iso(now), "role": _role(spec), "spec_sha": spec["_sha256"][:16], "code_sha": (code_hashes().get("live_tests10.py") or "")[:16]}
    for t in ts:
        j0 = (t - t0) // POLL_S
        for kind, path, need in items[t]:
            fr = pd.read_csv(check_path(path), usecols=["pid", "t"], dtype={"pid": str})
            rows = np.array([idx.get(str(p), -1) for p in fr["pid"]], dtype=np.int64)
            ok = rows >= 0
            d, hm = path.parent.name, path.name[:4]
            for what, h in need:
                if what == "h":
                    tg = pd.DataFrame({"tg_status": np.full(len(fr), 4, dtype=np.int64), "pmid_h": np.nan, "sP_h": np.nan, "p_bid_sz_h": np.nan, "p_ask_sz_h": np.nan,
                                       "t_end": -1})
                    if ok.any():
                        tt = targets(A, t0, np.array([j0], dtype=np.int64), h * 60 // POLL_S)
                        tt = tt.reset_index(drop=True)
                        tg.loc[ok, :] = tt.iloc[rows[ok]].to_numpy()
                    absent = (tg["tg_status"] == 4) & W.cycle_ran(t + h * 60)
                    tg.loc[absent, "tg_status"] = 3
                    res = pd.concat([fr.reset_index(drop=True), tg.assign(tg_status=[TG_NAMES[int(x)] for x in tg["tg_status"]])], axis=1)
                    for k_, v_ in meta.items():
                        res[k_] = v_
                    out[f"{kind}_h{h}" if b.write_once_csv(check_path(Path(out_root) / kind / "outcomes" / d / f"{hm}.h{h}.csv.gz"), res) else "exists"] += 1
                else:
                    tw = pd.DataFrame({"tw_ok": False, "dsK_tw": np.nan, "pull_tw": np.nan, "traded_tw": np.nan}, index=range(len(fr)))
                    if ok.any():
                        tt = twins(Ak, t0, np.array([j0], dtype=np.int64), np.arange(len(pids)))
                        tt = tt.reset_index(drop=True)
                        tw.loc[ok, :] = tt.iloc[rows[ok]].to_numpy()
                    res = pd.concat([fr.reset_index(drop=True), tw], axis=1)
                    for k_, v_ in meta.items():
                        res[k_] = v_
                    out[f"{kind}_twin" if b.write_once_csv(check_path(Path(out_root) / kind / "twins" / d / f"{hm}.csv.gz"), res) else "exists"] += 1
    return out


# --- ops-stats (1.6: counts only; reads no price, spread or size value) ---------------------------------------------------------------


OPS_COLS = ("pid", "t", "status", "cls223", "cls222", "role", "in_scope")


def _read_ops(path: Path) -> pd.DataFrame:
    return pd.read_csv(check_path(path), usecols=lambda c: c in OPS_COLS)


def ops_stats(root: Path = OUT_ROOT) -> dict:
    """File, line, unit, class and status counts of ``live_tests10/`` (no price, spread or size column is read)."""
    root = Path(root)
    out: dict = {"status": Counter(), "files": Counter(), "classes": {"cls223": Counter(), "cls222": Counter()}, "late_files": Counter()}
    for p in sorted(root.glob("status/*/*.csv.gz")):
        df = _read_ops(p)
        out["files"]["status"] += 1
        out["status"].update(df["status"].astype(str))
    for kind in KINDS.values():
        for p in sorted(root.glob(f"{kind}/frozen/*/*.csv.gz")):
            if p.name.endswith(".late.csv.gz"):
                out["late_files"][kind] += 1
                continue
            df = _read_ops(p)
            out["files"][kind] += 1
            out["classes"]["cls223"].update(df["cls223"].astype(str))
            out["classes"]["cls222"].update(df["cls222"].astype(str))
    return json.loads(json.dumps(out, default=dict))


PRESENCE_ONLY = ("k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "k_recv", "p_bid_sz", "p_ask_sz", "p_recv", "k_mid", "p_mid")


def presence_view(raw: bytes) -> dict | None:
    """A quote line reduced to keys, receipt lags, ``p_book_ts`` (equality only) and FINITENESS flags of the presence fields (no value of a price,
    spread or size field leaves this function)."""
    try:
        d = json.loads(raw)
    except ValueError:
        return None
    t = d.get("t")
    v = {"t": t, "pid": d.get("pid"), "src": d.get("src"), "p_book_ts": d.get("p_book_ts")}
    for f in PRESENCE_ONLY:
        v[f"has_{f}"] = math.isfinite(_f(d.get(f)))
    v["k_lag"] = _f(d.get("k_recv")) - t if isinstance(t, (int, float)) else math.nan
    v["p_lag"] = _f(d.get("p_recv")) - t if isinstance(t, (int, float)) else math.nan
    return v


def ops_stats_stream(xv_root: Path = XV_ROOT) -> dict:
    """``ops-stats --stream`` (the burn-in, 8.2; counts only): per day the cycles run against 720, pairs per cycle, request success shares,
    both-valid share, receipt-lag quantiles, refresh completions and their start times, record loads, the CF10 field-presence shares, the
    late-origin share and ``p_book_ts`` staleness; reads presence flags, receipt lags and ``p_book_ts`` equality only."""
    from .xv_quotes_poller import read_runs

    xv_root = Path(xv_root)
    runs = read_runs(xv_root) if check_path(xv_root / "runs.jsonl").exists() else []
    days: dict[str, dict] = {}
    for r in runs:
        if r.get("kind") == "cycle":
            d = days.setdefault(_ymd(r["t"]), Counter())
            d["cycles"] += 1
            d["pairs"] += r.get("pairs") or 0
            d["kalshi_ok"] += r.get("kalshi_ok") or 0
            d["books_ok"] += r.get("books_ok") or 0
            d["both_valid"] += r.get("both_valid") or 0
            d["loads"] += int(bool(r.get("load")))
        elif r.get("kind") == "refresh_done":
            d = days.setdefault(r["refreshed_utc"][:10].replace("-", ""), Counter())
            d["refreshes"] += 1
    out = {}
    for d, c in sorted(days.items()):
        pres, lags_k, lags_p, last_ts = Counter(), [], [], {}
        for suf in (".jsonl", ".jsonl.gz"):
            p = xv_root / "quotes" / f"{d}{suf}"
            if not p.exists():
                continue
            for raw in iter_complete_lines(p):
                v = presence_view(raw)
                if v is None:
                    continue
                pres["lines"] += 1
                if v["has_k_mid"]:
                    pres["k_valid"] += 1
                    for f in ("k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "k_recv"):
                        pres[f] += int(v[f"has_{f}"])
                if v["has_p_mid"]:
                    pres["p_valid"] += 1
                    for f in ("p_bid_sz", "p_ask_sz", "p_recv"):
                        pres[f] += int(v[f"has_{f}"])
                    prev = last_ts.get(v["pid"])
                    if prev is not None:
                        pres["book_pairs"] += 1
                        pres["book_same"] += int(prev == v["p_book_ts"])
                    last_ts[v["pid"]] = v["p_book_ts"]
                if isinstance(v["t"], (int, float)) and v["t"] % GRID_S == 0:
                    pres["origins"] += 1
                    pres["late"] += int(not (v["k_lag"] <= b.MAX_RECV_LAG_S and v["p_lag"] <= b.MAX_RECV_LAG_S))
                lags_k.append(v["k_lag"])
                lags_p.append(v["p_lag"])
        out[d] = {"cycles": c["cycles"], "cycles_share_of_720": c["cycles"] / 720.0, "pairs_per_cycle": c["pairs"] / c["cycles"] if c["cycles"] else None,
                  "kalshi_success": c["kalshi_ok"] / c["pairs"] if c["pairs"] else None, "books_success": c["books_ok"] / c["pairs"] if c["pairs"] else None,
                  "both_valid_share": c["both_valid"] / c["pairs"] if c["pairs"] else None, "refreshes": c["refreshes"], "loads": c["loads"],
                  "presence": {f: (pres[f] / pres["k_valid" if f.startswith("k_") else "p_valid"]) if pres["k_valid" if f.startswith("k_") else "p_valid"] else None
                               for f in ("k_last", "k_bid_sz", "k_ask_sz", "k_vol24", "k_recv", "p_bid_sz", "p_ask_sz", "p_recv")},
                  "late_origin_share": pres["late"] / pres["origins"] if pres["origins"] else None,
                  "p_book_ts_unchanged_share": pres["book_same"] / pres["book_pairs"] if pres["book_pairs"] else None,
                  "receipt_lag_q": {k: [float(x) for x in np.nanquantile(np.array(v, float), [0.5, 0.9, 0.99])] if v else None for k, v in (("k", lags_k), ("p", lags_p))}}
    return out
