# ruff: noqa: E501
"""CB1-D (neg-risk set asymmetry) and CB1-B (near-rung NO carry) tests, as declared in
``docs/research_lab/CREATIVE_BATCH_1.md`` (sections 0-2.11, CB1-B, CB1-D, challenger response).

EXPLORATORY research tooling. Nothing here is an edge, calibration or profitability claim; every P&L is a paper
rule at modelled or recorded prices and AREPO never trades. Pure functions (unit-tested in
``tests/unit/test_cb1_structural.py``) plus thin IO helpers. No network except the explicitly named
``walk_events`` / ``fetch_outcomes`` helpers, which take an injected limiter.

Extract formats this module reads (section 2.11; the extractor is owned by another module):
  ``negrisk/<capture_id>.csv.gz`` one row per member of every neg-risk event (documented columns plus the
      optional ``final_yes`` = closed member's final YES outcome price, blank if not final);
  ``event_members.csv.gz``        ``neg_risk_market_id`` and ``member_count`` (alias ``n_members``);
  ``rungs/<capture_id>.csv.gz``   ``capture_id, capture_start_utc, market_id, best_bid, best_ask,
      last_trade_price, closed, accepting_orders, end_date`` (optional ``volume_num``, ``fee_category``,
      ``sw1_best_bid``, ``sw1_bid_size_1``);
  ``capture_lists/<name>.json``   ``{"capture_ids": [...], "sha256": ..., "t_rep_start": ...}``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import battery as B
from . import economics, forecast, if_h2, provenance
from . import history_backfill as hb

VERSION = "cb1-structural-v1"
LABEL = "EXPLORATORY CB1 structural tests"
KIND_TEST = "cb1_structural"  # D dev screen (CREATIVE_BATCH_1.md calls this "cb1_test"; cb1_history owns its own kinds)
KIND_REP = "cb1_structural_replication"  # D rep, B1/B2 (Stage 2)
KIND_PROSP = "cb1_structural_prospective"  # B3 (stage P)
SEED = 116

# ---- declared dates (section 1.2) -------------------------------------------------------------
T_DEV_START = "2026-10-11T12:00:00Z"
T_DEV_END = "2026-10-17T00:00:00Z"
T_REP_START_FLOOR = "2026-10-19T00:00:00Z"
T_REP_END = "2026-11-09T00:00:00Z"
T_RUNG_OUT = "2027-01-07T00:00:00Z"
T_CENSOR_B3 = "2027-01-31T00:00:00Z"
DEADLINE_MAX = "2026-12-31"
IFH2_START_RANGE = ("2025-06-01", "2026-10-10")  # IF-H2 walked event start dates (B3 secondary)

# ---- declared parameters ----------------------------------------------------------------------
ALPHA_STAGE1 = 0.01
ALPHA_STAGE2 = 0.05
MIN_CLUSTERS = 30
MIN_UNITS = 100
RANN_MIN = 0.10
COST_SENS = 0.0075  # +0.75c on every bought leg (binding)
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE_RATE = 0.015
FLOORS = {"D1": 0.01, "D2": 0.005, "B1": 0.01, "B2": 0.01, "B3": 0.01}
D_TRIGGER_C = 0.995
D_GAP_H = (1.5, 3.0)
D_OPEN_MEMBERS = (2, 25)
D_DEPTH_MIN_SIZE = 5.0
D_DEPTH_MIN_CLUSTERS = 30
D_MAX_NON_SINGLE_WINNER = 0.02
D_MIN_RESOLVED = 30
D_UQ = 0.02  # U = 1[S_ask <= -0.02], O = 1[S_bid >= +0.02]
B_MIN_LEFT_S = 2 * 86400
B_V1_RANGE = (0.05, 0.60)
B_MONO_TOL = 0.01
B_V2_RANGE = (0.02, 0.97)
B_GRID_S = 6 * 3600
B_CENSOR_MARGIN_D = 60
B_MAX_CENSORED_SHARE = 0.10
B_SURVIVOR_MISSING = 0.10
B_SURVIVOR_YES_DIFF = 0.05
B1_CALENDAR_DISJOINT_END = "2025-09-01"
NEAR_RUNG_BANDS = ((0.05, 0.0205), (0.20, 0.0150), (0.80, 0.0110), (0.95, 0.0150))  # (upper bound, h); >= 0.95: 1.25c (section 2.1)

DECLARATION_FILE = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb1_structural_DECLARATION.json"
SEALS_DIR = provenance.REPO_ROOT / "docs" / "research_lab" / "seals"
T_REP_START_FILE = SEALS_DIR / "cb1_t_rep_start.json"  # committed pin (written once by `pin-rep-start`)
OUT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "creative_batch1"
EXTRACT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "cb1_extract"
HIST_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "history"


class Cb1Error(RuntimeError):
    """Base class for refusals (guards)."""


class DeclarationError(Cb1Error):
    pass


class WindowError(Cb1Error):
    pass


class CaptureListError(Cb1Error):
    pass


class SealUnavailableError(Cb1Error):
    pass


class RungListError(Cb1Error):
    pass


class RepStartError(Cb1Error):
    """The pinned T_rep_start file is missing, malformed, or disagrees with a capture list."""


class TooEarlyError(Cb1Error):
    pass


def _ep(s: str) -> float:
    t = pd.Timestamp(s)
    return (t.tz_convert("UTC") if t.tzinfo else t.tz_localize("UTC")).timestamp()


def _utc(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


# =============================================================================================
# Declaration hash guard
# =============================================================================================


MEMBER_COUNT_SOURCES = ("asof", "first_fetch")
MEMBER_COUNT_RULE = (
    "Event member count per D event-capture: the count of the latest event_members row fetched at or before the capture "
    "time (member_count_source='asof') where one exists; otherwise the first-fetched count for that neg_risk_market_id "
    "(member_count_source='first_fetch'), with member_count_lag_h = fetch time minus capture time recorded per "
    "event-capture. No count at all => ineligible (no_member_count). Justification: eligible events are non-augmented "
    "neg-risk events, which have fixed member sets (augmented and neg_risk_other events are excluded by the eligibility "
    "rules), so a count fetched shortly after a capture describes the same member set; the lag is disclosed, never "
    "hidden. The primary analysis uses both sources. A declared sensitivity re-runs D1/D2 restricted to as-of counts "
    "only (results key sensitivity_asof_only). The census and results report the number of event-captures by source "
    "(asof, first_fetch, none).")
BATCH_HOLM_FAMILY_RULE = (
    "The batch Holm family is every test that advanced at Stage 1 in any CB1 module (history A/C/E Stage-1 screens, D "
    "dev) plus B1 and B2, which have no Stage 1 and are always in the family. A Stage-2 test that is missing from the "
    "supplied Stage-2 files counts as p = 1 and is listed. The batch-holm command takes the Stage-1 (dev) results files "
    "and the Stage-2 files, derives the expected test list from the dev files plus the always-included tests, and "
    "refuses if any Stage-2 file contains a test outside that expected list.")



def declaration() -> dict:
    return {
        "version": VERSION,
        "dates": {"T_dev_start": T_DEV_START, "T_dev_end": T_DEV_END, "T_rep_start_floor": T_REP_START_FLOOR,
                  "T_rep_end": T_REP_END, "T_rung_out": T_RUNG_OUT, "T_censor_B3": T_CENSOR_B3,
                  "deadline_max": DEADLINE_MAX, "ifh2_start_range": list(IFH2_START_RANGE)},
        "stage": {"alpha1": ALPHA_STAGE1, "alpha2": ALPHA_STAGE2, "min_clusters": MIN_CLUSTERS,
                  "min_units": MIN_UNITS, "rann_min": RANN_MIN, "cost_sens": COST_SENS,
                  "placebo_draws": PLACEBO_DRAWS, "placebo_max_advance_rate": PLACEBO_MAX_ADVANCE_RATE,
                  "seed": SEED, "top_events_dropped": 5},
        "floors": FLOORS,
        "D": {"trigger_c": D_TRIGGER_C, "gap_h": list(D_GAP_H), "open_members": list(D_OPEN_MEMBERS),
              "uq": D_UQ, "depth_min_size": D_DEPTH_MIN_SIZE, "depth_min_clusters": D_DEPTH_MIN_CLUSTERS,
              "max_non_single_winner": D_MAX_NON_SINGLE_WINNER, "min_resolved": D_MIN_RESOLVED,
              "eligibility": ["not augmented", "no neg_risk_other", "visible members == event member_count",
                              "unresolved members open+active+accepting", "closed member needs final outcome",
                              "member resolved YES => ineligible", "0<bid<ask<1", "volume_num>0"],
              "fee_policy": "conservative sidecar schedule, docs table fallback, unknown 0.07",
              "member_count_rule": MEMBER_COUNT_RULE,
              "tests": {"D1": "mean(U-O) per eligible event-capture, >0",
                        "D2": "mean net=1-C_exec per trigger at next capture, >0"},
              "hold": "latest member end_date"},
        "B": {"min_left_s": B_MIN_LEFT_S, "v1_range": list(B_V1_RANGE), "mono_tol": B_MONO_TOL,
              "v2_range": list(B_V2_RANGE), "grid_s": B_GRID_S, "censor_margin_d": B_CENSOR_MARGIN_D,
              "max_censored_share": B_MAX_CENSORED_SHARE, "survivor_missing": B_SURVIVOR_MISSING,
              "survivor_yes_diff": B_SURVIVOR_YES_DIFF, "grouper": if_h2.GROUPER_VERSION,
              "half_spread_bands": [list(x) for x in NEAR_RUNG_BANDS],
              "ask": "min(n1+max(h(n1),1c),0.999) (R1); 1-best_bid (R2)",
              "tests": {"B1": "mean NO net per near rung", "B2": "paired near-far NO net",
                        "B3": "prospective mean NO net at recorded ask"}},
        "batch_holm_family": BATCH_HOLM_FAMILY_RULE,
        "kinds": [KIND_TEST, KIND_REP, KIND_PROSP],
        "rules": ["unknown flag/field => ineligible (fail closed)",
                  "closed member classified only from final outcome; open members never use outcomes",
                  "ladder clustering = ladder event x ISO week of near-rung deadline; D = event x capture day",
                  "snapshots/ladders are unweighted (weight 1): weighted == unweighted by construction",
                  "break-even placebo at the test's own stage alpha, advance rate <= 1.5% binding",
                  "R1 trade truncation: stored trade => known true; truncated+none stored => unavailable => excluded",
                  "R1 rung fee_category is not stored in the ladder file => docs fee for unknown category (0.07)",
                  "capture lists: final, sha256 committed, missing_ids counted, listed-but-absent table raises"],
    }


def declaration_sha256() -> str:
    return hashlib.sha256(json.dumps(declaration(), sort_keys=True).encode()).hexdigest()


def write_declaration(path: Path = DECLARATION_FILE) -> dict:
    """Write the declaration record (the coordinator commits it at the CB1 freeze)."""
    rec = {"declaration_sha256": declaration_sha256(), "version": VERSION, "declaration": declaration()}
    path = Path(path)
    if path.exists():
        raise DeclarationError(f"{path} already exists; a committed declaration is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1, sort_keys=True))
    return rec


def require_declaration(path: Path = DECLARATION_FILE) -> str:
    """Refuse unless the committed declaration record exists and matches the current code's hash."""
    path = Path(path)
    if not path.exists():
        raise DeclarationError(f"no committed declaration at {path}; counted CB1 structural runs are refused")
    rec = json.loads(path.read_text())
    cur = declaration_sha256()
    if rec.get("declaration_sha256") != cur:
        raise DeclarationError(
            f"declaration hash mismatch: committed {rec.get('declaration_sha256')} != current {cur}")
    return cur


# =============================================================================================
# Frozen capture lists and window guards
# =============================================================================================


def _iso_z(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pin_rep_start(freeze_commit: str, commit_time_iso: str, path: Path | None = None) -> dict:
    """Write the committed T_rep_start pin (never overwritten): ``max(T_rep_start_floor, freeze commit time + 2h)``.
    ``commit_time_iso`` is the committer date of the CB1 freeze commit (``git show -s --format=%cI <sha>``).
    The first-complete-capture clause of the design is realised by the rep capture list, whose ``from_utc``
    must equal this pinned value."""
    path = Path(path) if path is not None else T_REP_START_FILE
    if path.exists():
        raise RepStartError(f"{path} exists; T_rep_start is pinned once and never rewritten")
    sha = str(freeze_commit).strip()
    if not (7 <= len(sha) <= 64) or any(c not in "0123456789abcdef" for c in sha.lower()):
        raise RepStartError(f"not a commit sha: {freeze_commit!r}")
    plus2h = _ep(commit_time_iso) + 2 * 3600.0
    start = max(_ep(T_REP_START_FLOOR), plus2h)
    doc = {"version": VERSION, "freeze_commit": sha, "freeze_commit_time": _iso_z(_ep(commit_time_iso)),
           "freeze_commit_plus_2h": _iso_z(plus2h), "t_rep_start_floor": T_REP_START_FLOOR,
           "t_rep_start": _iso_z(start),
           "rule": "max(floor, freeze commit time + 2h); the rep capture list from_utc must equal t_rep_start"}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return doc


def load_pinned_rep_start(path: Path | None = None) -> str:
    """The committed, pinned T_rep_start (ISO Z). Fail closed if absent or malformed."""
    path = Path(path) if path is not None else T_REP_START_FILE
    if not path.exists():
        raise RepStartError(f"no pinned T_rep_start at {path}; run `pin-rep-start --freeze-commit <sha>` and commit it")
    try:
        t = json.loads(path.read_text())["t_rep_start"]
        ep = _ep(t)
    except (ValueError, KeyError, TypeError) as exc:
        raise RepStartError(f"{path}: malformed pin: {exc}") from exc
    if ep < _ep(T_REP_START_FLOOR):
        raise RepStartError(f"{path}: t_rep_start {t} is before the declared floor {T_REP_START_FLOOR}")
    return _iso_z(ep)


def capture_list_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(str(i) for i in ids)).encode()).hexdigest()


def load_capture_list(path: Path, expected_sha256: str | None = None, *, window: str | None = None) -> dict:
    """Frozen capture-id list written by ``creative_batch1.freeze_list``. Verifies its own sha256 field and,
    if given, the committed value. For a counted window the list must be ``final`` (covers the whole window)
    and its ``from_utc``/``until`` must match the declared window. ``missing_ids`` (listed, not extracted)
    are carried through so the caller counts them; they are never silently dropped."""
    path = forecast.require_local(Path(path))
    doc = json.loads(path.read_text())
    raw = doc.get("capture_ids", doc.get("captures"))
    if not isinstance(raw, list) or not raw:
        raise CaptureListError(f"{path}: no capture ids")
    ids = [str(x["capture_id"] if isinstance(x, dict) else x) for x in raw]
    if len(set(ids)) != len(ids):
        raise CaptureListError(f"{path}: duplicate capture ids")
    sha = capture_list_sha256(ids)
    if doc.get("sha256") not in (None, sha):
        raise CaptureListError(f"{path}: sha256 field {doc.get('sha256')} != recomputed {sha}")
    if expected_sha256 is not None and expected_sha256 != sha:
        raise CaptureListError(f"{path}: sha256 {sha} != committed {expected_sha256}")
    if window in ("dev", "rep"):
        if not doc.get("final"):
            raise CaptureListError(f"{path}: list is not final (does not cover the whole {window} window)")
        end = T_DEV_END if window == "dev" else T_REP_END
        if doc.get("until") and _ep(doc["until"]) != _ep(end):
            raise CaptureListError(f"{path}: until {doc['until']} != declared window end {end}")
        lo = T_DEV_START if window == "dev" else T_REP_START_FLOOR
        if window == "rep":  # the rep list must start exactly at the pinned T_rep_start
            pinned = load_pinned_rep_start()
            if not doc.get("from_utc") or _ep(doc["from_utc"]) != _ep(pinned):
                raise CaptureListError(f"{path}: from_utc {doc.get('from_utc')} != pinned T_rep_start {pinned}")
        if doc.get("from_utc") and _ep(doc["from_utc"]) < _ep(lo):
            raise CaptureListError(f"{path}: from_utc {doc['from_utc']} is before the declared floor {lo}")
        if window == "dev" and doc.get("from_utc") and _ep(doc["from_utc"]) != _ep(T_DEV_START):
            raise CaptureListError(f"{path}: dev list must start at {T_DEV_START}")
    missing = [str(x) for x in doc.get("missing_ids", [])]
    if not set(missing) <= set(ids):
        raise CaptureListError(f"{path}: missing_ids not a subset of capture_ids")
    return {"ids": ids, "sha256": sha, "missing_ids": missing, "from_utc": doc.get("from_utc"),
            "until": doc.get("until"), "path": str(path)}


def window_bounds(window: str, t_rep_start: str | None = None) -> tuple[float, float]:
    """[lo, hi) epoch bounds. ``dev``: [T_dev_start, T_dev_end). ``rep``: [T_rep_start, T_rep_end).
    ``b3``: [T_rep_start, inf) (B3 follows its own frozen rung list)."""
    if window == "dev":
        return _ep(T_DEV_START), _ep(T_DEV_END)
    pinned = load_pinned_rep_start()  # T_rep_start is never a free value
    start = t_rep_start or pinned
    if _ep(start) != _ep(pinned):
        raise WindowError(f"t_rep_start {start} != pinned T_rep_start {pinned}")
    if _ep(start) < _ep(T_REP_START_FLOOR):
        raise WindowError(f"t_rep_start {start} is before the declared floor {T_REP_START_FLOOR}")
    if window == "rep":
        return _ep(start), _ep(T_REP_END)
    if window == "b3":
        return _ep(start), math.inf
    raise WindowError(f"unknown window {window!r}")


def check_window_allowed(window: str, now: datetime | None = None) -> None:
    """``rep`` is refused before T_rep_end (the rep list is written then)."""
    if window == "rep" and _utc(now).timestamp() < _ep(T_REP_END):
        raise TooEarlyError(f"window rep is refused before T_rep_end {T_REP_END}")


def assert_captures_in_window(cs_by_id: dict[str, float], window: str, t_rep_start: str | None = None) -> None:
    lo, hi = window_bounds(window, t_rep_start)
    for cid, cs in cs_by_id.items():
        if not (lo <= cs < hi):
            raise WindowError(f"capture {cid} at {pd.Timestamp(cs, unit='s', tz='UTC')} is outside window "
                              f"{window} [{pd.Timestamp(lo, unit='s', tz='UTC')}, "
                              f"{pd.Timestamp(hi, unit='s', tz='UTC') if hi != math.inf else 'inf'})")


# =============================================================================================
# Readers
# =============================================================================================

_STR_COLS = {"capture_id": str, "neg_risk_market_id": str, "event_id": str, "market_id": str,
             "clob_token_id_0": str}


def read_capture_table(extract_root: Path, sub: str, capture_id: str) -> pd.DataFrame:
    p = forecast.require_local(Path(extract_root) / sub / f"{capture_id}.csv.gz")  # fail loudly if missing
    return pd.read_csv(p, dtype=_STR_COLS)


def load_event_members(extract_root: Path, asof_utc: str | None = None) -> dict[str, int]:
    """neg_risk_market_id -> member count. The file is append-only: with ``asof_utc`` only rows with
    ``fetched_utc <= asof_utc`` count (``creative_batch1.event_members_asof``), so a count fetched after a capture is
    absent for it (missing stays missing). Without ``asof_utc`` the latest row per id is used (census/diagnostics only)."""
    from . import creative_batch1

    root = Path(extract_root)
    forecast.require_local(root / "event_members.csv.gz")
    d = creative_batch1.event_members_asof(root, asof_utc)
    col = next((c for c in ("member_count", "n_members", "members") if c in d), None)
    if col is None:
        raise Cb1Error(f"{root / 'event_members.csv.gz'}: no member_count column")
    d = d[d[col].astype(str).str.strip() != ""]
    d = d.assign(**{col: pd.to_numeric(d[col], errors="coerce")}).dropna(subset=["neg_risk_market_id", col])
    return {str(k): int(v) for k, v in zip(d["neg_risk_market_id"], d[col], strict=True)}


def load_first_fetch(extract_root: Path) -> dict[str, tuple[int, float]]:
    """neg_risk_market_id -> (member count, fetch epoch) of the FIRST fetched row (earliest ``fetched_utc``). Used only
    when no row was fetched at or before a capture (``MEMBER_COUNT_RULE``); the fetch time is kept for the lag."""
    from . import creative_batch1

    root = Path(extract_root)
    forecast.require_local(root / "event_members.csv.gz")
    d = creative_batch1._read_event_members(root)
    col = next((c for c in ("member_count", "n_members", "members") if c in d), None)
    if col is None:
        raise Cb1Error(f"{root / 'event_members.csv.gz'}: no member_count column")
    d = d[(d[col].astype(str).str.strip() != "") & (d["fetched_utc"].astype(str).str.strip() != "")]
    d = d.assign(**{col: pd.to_numeric(d[col], errors="coerce")}).dropna(subset=["neg_risk_market_id", col])
    d = d.sort_values(["neg_risk_market_id", "fetched_utc"], kind="stable").drop_duplicates("neg_risk_market_id", keep="first")
    return {str(k): (int(v), _ep(f)) for k, v, f in zip(d["neg_risk_market_id"], d[col], d["fetched_utc"], strict=True)}


def members_asof_loader(extract_root: Path) -> Callable[[float], dict[str, int]]:
    """capture start epoch -> member-count table valid at that time (cached per capture time)."""
    cache: dict[float, dict[str, int]] = {}

    def get(cs: float) -> dict[str, int]:
        if cs not in cache:
            cache[cs] = load_event_members(extract_root, _iso_z(cs))
        return cache[cs]

    return get


def load_manifest_starts(extract_root: Path) -> dict[str, float]:
    """capture_id -> capture start epoch from the extractor manifest (authoritative, also for captures whose
    negrisk table is empty)."""
    p = forecast.require_local(Path(extract_root) / "manifest.json")
    man = json.loads(p.read_text()).get("captures", {})
    return {cid: _ep(e["started_utc"]) for cid, e in man.items() if e.get("started_utc")}


def load_window_captures(extract_root: Path, cl: dict, window: str, sub: str = "negrisk",
                         t_rep_start: str | None = None) -> tuple[pd.DataFrame, dict[str, float], dict]:
    """All listed captures. Every listed id must have a manifest start inside the window (fail loudly);
    ``missing_ids`` of the list (never extracted) are counted and skipped; any other listed capture without
    a table raises ``ArchivedDataError``. Returns (rows with ``cs``, capture starts, counts)."""
    starts = load_manifest_starts(extract_root)
    skip = set(cl.get("missing_ids", []))
    cs_by: dict[str, float] = {}
    for cid in cl["ids"]:
        if cid in skip:
            continue
        if cid not in starts:
            raise CaptureListError(f"capture {cid} is listed but has no manifest start")
        cs_by[cid] = starts[cid]
    assert_captures_in_window(cs_by, window, t_rep_start)
    parts = []
    empty = 0
    for cid in cs_by:
        d = read_capture_table(extract_root, sub, cid)  # raises if the listed file is missing
        if not len(d):
            empty += 1
            continue
        d["cs"] = cs_by[cid]
        d["capture_id"] = cid
        parts.append(d)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return df, cs_by, {"listed": len(cl["ids"]), "missing_listed": len(skip), "loaded": len(cs_by),
                       "empty_tables": empty}


# =============================================================================================
# Fees
# =============================================================================================


def _isnull(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x)) or (not isinstance(x, str) and pd.isna(x))


def leg_rate(fee_schedule, fee_category) -> tuple[float, float]:
    """(rate, exponent): sidecar schedule with the conservative policy; docs table by category otherwise;
    unknown/null -> 0.07."""
    sched = None if _isnull(fee_schedule) or fee_schedule == "" else fee_schedule
    cat = None if _isnull(fee_category) else str(fee_category).split(":")[0]
    docs = economics.DOCS_CATEGORY_RATE.get(cat, math.nan) if cat else math.nan
    spec = economics.fee_spec(sched, None, cat)
    if spec.known:
        return economics.resolve_rate(spec, "conservative"), spec.exponent
    return (docs if not math.isnan(docs) else economics.MAX_DOCS_RATE), 1.0


def leg_fee(ask: float, rate: float, exponent: float = 1.0) -> float:
    return float(economics.taker_fee(1.0, ask, rate, exponent))


def docs_fee(price: float, fee_category) -> float:
    r, e = leg_rate(None, fee_category)
    return leg_fee(price, r, e)


def half_spread(p: float) -> float:
    """Half-spread by the bought side's price band (section 2.1): <0.05 2.05c; 0.05-0.20 1.50c; 0.20-0.80 1.10c;
    0.80-0.95 1.50c; >=0.95 1.25c."""
    for upper, h in NEAR_RUNG_BANDS:
        if p < upper:
            return h
    return 0.0125


def _flag(s: pd.Series) -> np.ndarray:
    m = {"true": 1.0, "1": 1.0, "1.0": 1.0, "false": 0.0, "0": 0.0, "0.0": 0.0}
    return s.map(lambda v: m.get(str(v).strip().lower(), np.nan) if not isinstance(v, (bool, np.bool_))
                 else float(v)).to_numpy(float)


# =============================================================================================
# CB1-D: neg-risk set
# =============================================================================================


def member_complete(visible: int, event_count: int | None) -> bool:
    """Visible member count (open plus resolved in the capture) must equal the event's member count."""
    return event_count is not None and int(visible) == int(event_count)


def set_cost(asks, rates, exps) -> float:
    """C = sum_j (ask_j + f(ask_j)); fees are summed per leg with each leg's own rate."""
    return float(sum(a + leg_fee(a, r, e) for a, r, e in zip(asks, rates, exps, strict=True)))


def _group_eligible(g: pd.DataFrame, n_members: int | None, outcomes: dict[str, float] | None = None
                    ) -> tuple[dict | None, str]:
    """Event-capture eligibility (challenger item 4). Every unknown flag is ineligible (fail closed).
    ``outcomes``: market_id -> final YES price, used only to classify members that are ALREADY closed at the
    capture (their outcome is a fact at capture time); an open member's outcome is never consulted."""
    outcomes = outcomes or {}
    g = g.drop_duplicates("market_id")
    if n_members is None:
        return None, "no_member_count"
    if not member_complete(len(g), n_members):
        return None, "member_count_mismatch"
    aug = _flag(g["event_neg_risk_augmented"]) if "event_neg_risk_augmented" in g else np.full(len(g), np.nan)
    oth = _flag(g["neg_risk_other"]) if "neg_risk_other" in g else np.full(len(g), np.nan)
    if np.any(np.isnan(aug)):
        return None, "augmented_unknown"
    if np.any(aug != 0):
        return None, "augmented"
    if np.any(np.isnan(oth)):
        return None, "other_unknown"
    if np.any(oth == 1):
        return None, "other"
    closed_f = _flag(g["closed"])
    if np.any(np.isnan(closed_f)):
        return None, "closed_unknown"
    closed = closed_f == 1
    final = pd.to_numeric(g["final_yes"], errors="coerce").to_numpy(float) if "final_yes" in g \
        else np.full(len(g), np.nan)
    if outcomes:
        mo = np.array([outcomes.get(str(m), math.nan) for m in g["market_id"]], float)
        final = np.where(np.isnan(final), mo, final)
    if closed.any():
        fc = final[closed]
        if np.any(np.isnan(fc)) or np.any(~np.isin(fc, (0.0, 1.0))):
            return None, "closed_without_final_outcome"
        if np.any(fc == 1.0):
            return None, "member_resolved_yes"
    op = g[~closed]
    if not (D_OPEN_MEMBERS[0] <= len(op) <= D_OPEN_MEMBERS[1]):
        return None, "open_member_count"
    act, acc = _flag(op["active"]), _flag(op["accepting_orders"])
    if np.any(act != 1) or np.any(acc != 1):  # NaN != 1: unknown is not open
        return None, "member_not_open"
    bid, ask = op["best_bid"].to_numpy(float), op["best_ask"].to_numpy(float)
    vol = pd.to_numeric(op["volume_num"], errors="coerce").to_numpy(float) if "volume_num" in op \
        else np.full(len(op), np.nan)
    with np.errstate(invalid="ignore"):
        if not np.all((bid > 0) & (ask > bid) & (ask < 1)):
            return None, "bad_quote"
        if not np.all(vol > 0):
            return None, "no_volume"
    rates = [leg_rate(fs, fc_) for fs, fc_ in zip(op.get("fee_schedule", [None] * len(op)),
                                                  op.get("fee_category", [None] * len(op)), strict=True)]
    legs = {}
    for i, (mid, a, b) in enumerate(zip(op["market_id"], ask, bid, strict=True)):
        def _opt(col, i=i):
            return float(op[col].iloc[i]) if col in op and not pd.isna(op[col].iloc[i]) else math.nan
        legs[str(mid)] = {"ask": float(a), "bid": float(b), "rate": rates[i][0], "exp": rates[i][1],
                          "sw1_ask": _opt("sw1_best_ask"), "sw1_size": _opt("sw1_ask_size_1")}
    ends = pd.to_datetime(op["end_date"], utc=True, errors="coerce") if "end_date" in op else None
    end_ep = float(ends.max().timestamp()) if ends is not None and ends.notna().any() else math.nan
    return {"legs": legs, "end_epoch": end_ep,
            "S_ask": float(ask.sum() - 1), "S_bid": float(bid.sum() - 1),
            "C": set_cost(list(ask), [r[0] for r in rates], [r[1] for r in rates]),
            "event_id": str(g["event_id"].iloc[0]) if "event_id" in g else ""}, "ok"


def negrisk_event_captures(df: pd.DataFrame, members: dict[str, int] | Callable[[float], dict[str, int]], outcomes: dict[str, float] | None = None,
                           *, first_fetch: dict[str, tuple[int, float]] | None = None, asof_only: bool = False
                           ) -> tuple[pd.DataFrame, dict]:
    """Eligible event-captures (one row each) plus counts of ineligibility reasons. Member count per event-capture
    follows ``MEMBER_COUNT_RULE``: as-of the capture, else (unless ``asof_only``) the first-fetched count with its lag."""
    reasons: dict[str, int] = {}
    srcs = {"asof": 0, "first_fetch": 0, "none": 0}
    rows = []
    if len(df):
        for (cid, gid), g in df.groupby(["capture_id", "neg_risk_market_id"], sort=False):
            cs0 = float(g["cs"].iloc[0])
            mem = members(cs0) if callable(members) else members
            n_mem, src, lag = mem.get(str(gid)), "asof", math.nan
            if n_mem is None and not asof_only and first_fetch and str(gid) in first_fetch:
                n_mem, fe = first_fetch[str(gid)]
                src, lag = "first_fetch", (fe - cs0) / 3600.0
            srcs[src if n_mem is not None else "none"] += 1
            res, why = _group_eligible(g, n_mem, outcomes)
            reasons[why] = reasons.get(why, 0) + 1
            if res is None:
                continue
            S = res["S_ask"]
            rows.append({"capture_id": cid, "cs": float(g["cs"].iloc[0]), "gid": str(gid),
                         "event_id": res["event_id"], "n_open": len(res["legs"]), "S_ask": S,
                         "S_bid": res["S_bid"], "U": float(S <= -D_UQ), "O": float(res["S_bid"] >= D_UQ),
                         "C": res["C"], "end_epoch": res["end_epoch"], "legs": res["legs"],
                         "member_count_source": src, "member_count_lag_h": lag})
    ec = pd.DataFrame(rows, columns=["capture_id", "cs", "gid", "event_id", "n_open", "S_ask", "S_bid", "U",
                                     "O", "C", "end_epoch", "legs", "member_count_source", "member_count_lag_h"])
    ec["day"] = pd.to_datetime(ec["cs"], unit="s", utc=True).dt.strftime("%Y-%m-%d") if len(ec) else []
    elig_src = ec["member_count_source"].value_counts().to_dict() if len(ec) else {}
    lags = ec.loc[ec["member_count_source"] == "first_fetch", "member_count_lag_h"] if len(ec) else []
    return ec, {"eligible": len(ec), "ineligible_reasons": reasons,
                "member_count_source_all_groups": srcs,
                "member_count_source_eligible": {k: int(elig_src.get(k, 0)) for k in MEMBER_COUNT_SOURCES},
                "member_count_lag_h_first_fetch": ({"min": float(np.min(lags)), "median": float(np.median(lags)),
                                                    "max": float(np.max(lags))} if len(lags) else None)}


def next_capture_pairs(cs_by_id: dict[str, float], gap_h: tuple[float, float] = D_GAP_H
                       ) -> tuple[dict[str, str], dict]:
    """capture -> next capture (by start time) whose gap lies in [lo, hi] hours; others are dropped and
    counted (as SB2 J5: an outage pair is excluded, not repaired)."""
    order = sorted(cs_by_id, key=lambda c: cs_by_id[c])
    nxt, cnt = {}, {"pairs": 0, "kept": 0, "excluded_gap": 0, "no_next": 1 if order else 0}
    for a, b in zip(order[:-1], order[1:], strict=True):
        g = (cs_by_id[b] - cs_by_id[a]) / 3600.0
        cnt["pairs"] += 1
        if gap_h[0] <= g <= gap_h[1]:
            nxt[a] = b
            cnt["kept"] += 1
        else:
            cnt["excluded_gap"] += 1
    return nxt, cnt


def realised_set_payout(final_yes: dict[str, float], market_ids) -> tuple[float, bool, bool]:
    """(payout, resolved, single_winner) over the set's legs; payout = sum of final outcome prices."""
    vals = [final_yes.get(str(m), math.nan) for m in market_ids]
    if any(math.isnan(v) for v in vals):
        return math.nan, False, False
    pay = float(sum(vals))
    single = all(v in (0.0, 1.0) for v in vals) and abs(pay - 1.0) < 1e-9
    return pay, True, single


def final_yes_map(df: pd.DataFrame) -> dict[str, float]:
    """Final YES outcome per closed member from the window's own captures (last capture wins)."""
    if not len(df) or "final_yes" not in df:
        return {}
    d = df[(_flag(df["closed"]) == 1)].copy()
    d["f"] = pd.to_numeric(d["final_yes"], errors="coerce")
    d = d.dropna(subset=["f"]).sort_values("cs")
    return {str(m): float(f) for m, f in zip(d["market_id"], d["f"], strict=True)}


def d2_triggers(ec: pd.DataFrame, nxt: dict[str, str], final_yes: dict[str, float] | None = None
                ) -> tuple[pd.DataFrame, dict]:
    """One row per trigger C(c) <= 0.995 with a kept next-capture pair. No trade (net 0, kept in the
    denominator) unless the event is eligible at c', its open set is unchanged and every ask is present."""
    final_yes = final_yes or {}
    idx = {(r.capture_id, r.gid): r for r in ec.itertuples(index=False)}
    cnt = {"triggers": 0, "no_next_or_gap": 0, "executed": 0, "no_trade": 0}
    rows = []
    for r in ec.itertuples(index=False):
        if not r.C <= D_TRIGGER_C:
            continue
        j = nxt.get(r.capture_id)
        if j is None:
            cnt["no_next_or_gap"] += 1
            continue
        cnt["triggers"] += 1
        r2 = idx.get((j, r.gid))
        base = {"gid": r.gid, "capture_id": r.capture_id, "day": r.day, "C": r.C}
        if r2 is None or set(r2.legs) != set(r.legs):
            cnt["no_trade"] += 1
            rows.append({**base, "executed": False, "net": 0.0, "K": 0.0, "d": math.nan, "n_legs": len(r.legs),
                         "sweep_ok": False, "net_sweep": math.nan, "resolved": False, "net_real": math.nan,
                         "single_winner": False})
            continue
        cnt["executed"] += 1
        C2 = r2.C
        d = (r2.end_epoch - r2.cs) / 86400.0 if not math.isnan(r2.end_epoch) else math.nan
        sw_ok = all(not math.isnan(L["sw1_ask"]) and L["sw1_size"] >= D_DEPTH_MIN_SIZE for L in r2.legs.values())
        net_sw = 1.0 - sum(L["sw1_ask"] + leg_fee(L["sw1_ask"], L["rate"], L["exp"])
                           for L in r2.legs.values()) if sw_ok else math.nan
        pay, resolved, single = realised_set_payout(final_yes, list(r2.legs))
        rows.append({**base, "executed": True, "net": 1.0 - C2, "K": C2, "d": d, "n_legs": len(r2.legs),
                     "sweep_ok": sw_ok, "net_sweep": net_sw, "resolved": resolved,
                     "net_real": pay - C2 if resolved else math.nan, "single_winner": single})
    cols = ["gid", "capture_id", "day", "C", "executed", "net", "K", "d", "n_legs", "sweep_ok", "net_sweep",
            "resolved", "net_real", "single_winner"]
    return pd.DataFrame(rows, columns=cols), cnt


# ---- generic statistics ------------------------------------------------------------------


def _top_drop(vals: np.ndarray, ev: np.ndarray, k: int = 5) -> np.ndarray:
    """Boolean keep-mask removing the k events with the largest absolute total contribution."""
    s = pd.Series(vals).groupby(ev).sum()
    drop = set(s.abs().sort_values(ascending=False).index[:k])
    return ~np.isin(ev, list(drop))


def leave_one_day_out(vals: np.ndarray, day: np.ndarray) -> dict[str, float]:
    out = {}
    for d in pd.unique(day):
        m = day != d
        out[str(d)] = float(vals[m].mean()) if m.any() else math.nan
    return out


def mean_gate(vals, ev, day, *, floor: float, alpha: float, n_boot: int, seed: int = SEED,
              r_ann: float | None = None, need_rann: bool = False, cost_add=None,
              lodo: bool = False, min_clusters: int = MIN_CLUSTERS, min_units: int = MIN_UNITS) -> dict:
    """One-sided mean test with the Stage gate: p < alpha, point >= floor, R_ann >= 10% (economic),
    +0.75c cost keeps the mean > 0, still passes without the top 5 events, weighted == unweighted (units
    are unit-weighted here), and, if ``lodo``, every leave-one-day-out mean is > 0."""
    vals = np.asarray(vals, float)
    ev = np.asarray(ev).astype(str)
    day = np.asarray(day).astype(str)
    n, nev = len(vals), len(pd.unique(ev))
    base = {"n": int(n), "n_event": int(nev), "alpha": alpha, "floor": floor}
    if n < min_units or nev < min_clusters:
        return {**base, "testable": False, "p": 1.0, "advance": False,
                "reason": f"not testable (n={n}<{min_units} or events={nev}<{min_clusters})"}
    t = B.mean_test(vals, ev, day, 1, n_boot, seed)
    keep = _top_drop(vals, ev)
    t5 = B.mean_test(vals[keep], ev[keep], day[keep], 1, max(n_boot // 4, 20), seed) \
        if keep.sum() >= 2 and len(pd.unique(ev[keep])) >= 2 else {"p": 1.0, "mean": math.nan}
    cost_ok = None
    if cost_add is not None:
        cost_ok = bool((vals - np.asarray(cost_add, float)).mean() > 0)
    rob = {"cost_0.75c_positive": cost_ok,
           "without_top5_events": {"p": t5["p"], "mean": t5["mean"],
                                   "ok": bool(t5["p"] < alpha and t5["mean"] >= floor)},
           "weighted_sign_agrees": True}
    ld = leave_one_day_out(vals, day) if lodo else None
    ok = bool(t["p"] < alpha and t["mean"] >= floor and rob["without_top5_events"]["ok"]
              and (cost_ok is None or cost_ok))
    if need_rann:
        ok = ok and r_ann is not None and not math.isnan(r_ann) and r_ann >= RANN_MIN
    if lodo:
        ok = ok and all(v > 0 for v in ld.values())
    return {**base, "testable": True, "mean": t["mean"], "p": t["p"], "se_event": t["se_event"],
            "se_twoway": t["se_twoway"], "ci95": t["ci_event_boot"], "n_day": t["n_day"], "r_ann": r_ann,
            "robustness": rob, "leave_one_day_out": ld, "advance": ok}


def r_ann_of(net: np.ndarray, K: np.ndarray, d: np.ndarray) -> float:
    """365 * sum(net) / sum(K * max(d, 1)) over rows with capital and a known hold (not risk-adjusted)."""
    m = (K > 0) & np.isfinite(d)
    den = float((K[m] * np.maximum(d[m], 1.0)).sum())
    return 365.0 * float(net[m].sum()) / den if den > 0 else math.nan


def negrisk_tests(ec: pd.DataFrame, trig: pd.DataFrame, *, n_boot: int, dev: bool, alpha: float,
                  seed: int = SEED) -> dict:
    """D1 (mechanism) and D2 (economic) with the binding D2 gates (realised payout, anomalies, depth)."""
    out: dict = {"D1": {}, "D2": {}}
    if len(ec):
        dv = (ec["U"] - ec["O"]).to_numpy(float)
        out["D1"] = mean_gate(dv, ec["gid"], ec["day"], floor=FLOORS["D1"], alpha=alpha, n_boot=n_boot,
                              seed=seed, lodo=dev)
        out["D1"]["incidence"] = {"U": float(ec["U"].mean()), "O": float(ec["O"].mean())}
    else:
        out["D1"] = {"testable": False, "p": 1.0, "advance": False, "reason": "no eligible event-captures"}
    if len(trig):
        net = trig["net"].to_numpy(float)
        ex = trig["executed"].to_numpy(bool)
        rann = r_ann_of(net, trig["K"].to_numpy(float), trig["d"].to_numpy(float))
        cost = np.where(ex, COST_SENS * trig["n_legs"].to_numpy(float), 0.0)
        d2 = mean_gate(net, trig["gid"], trig["day"], floor=FLOORS["D2"], alpha=alpha, n_boot=n_boot, seed=seed,
                       r_ann=rann, need_rann=True, cost_add=cost, lodo=dev)
        # realised payouts (binding)
        res = trig[trig["executed"] & trig["resolved"]]
        n_res_ev = int(res["gid"].nunique())
        real = {"n_resolved": int(len(res)), "n_resolved_events": n_res_ev}
        cap = None
        if n_res_ev < D_MIN_RESOLVED:
            cap = "inconclusive (payoff unverified)"
        else:
            # per resolved triggered EVENT (design: share of resolved triggered events that are not single-winner)
            nsw = float(res.groupby("gid")["single_winner"].all().eq(False).mean())
            real.update(non_single_winner_share=nsw, mean_net_realised=float(res["net_real"].mean()),
                        same_sign=bool(res["net_real"].mean() > 0), ceiling_ok=bool(nsw <= D_MAX_NON_SINGLE_WINNER))
            if not (real["same_sign"] and real["ceiling_ok"]):
                d2["advance"] = False
        d2["realised"] = real
        # depth (binding)
        sw = trig[trig["executed"] & trig["sweep_ok"]]
        depth = {"share_triggers_with_sweep": float(trig.loc[trig["executed"], "sweep_ok"].mean())
                 if ex.any() else math.nan, "n_sweep_events": int(sw["gid"].nunique())}
        if depth["n_sweep_events"] < D_DEPTH_MIN_CLUSTERS:
            cap = cap or "inconclusive (depth unverified)"
        else:
            depth["mean_net_sweep"] = float(sw["net_sweep"].mean())
            depth["same_sign"] = bool(sw["net_sweep"].mean() > 0)
            if not depth["same_sign"]:
                d2["advance"] = False
        d2["depth"] = depth
        d2["cap"] = cap
        d2["stage_gate_passed"] = bool(d2.get("advance"))
        if cap is not None:
            d2["advance"] = False
        out["D2"] = d2
    else:
        out["D2"] = {"testable": False, "p": 1.0, "advance": False, "n": 0,
                     "reason": "no triggers: the state is too rare to test (itself the economic answer)"}
    return out


def d2_placebo(ec: pd.DataFrame, trig: pd.DataFrame, *, draws: int = PLACEBO_DRAWS, seed: int = SEED + 1,
               alpha: float = ALPHA_STAGE1, n_boot: int = 20) -> dict:
    """Capture-order permutation within event: each trigger executes at the price of a random OTHER eligible
    capture of the same event (no persistence by construction, so nothing should advance). A trigger whose
    event has no other eligible capture keeps net 0 (as the real rule's no-trade). Advance rate <= 1.5%."""
    by_ev = {g: grp[["capture_id", "C"]].reset_index(drop=True) for g, grp in ec.groupby("gid")}
    t = trig.reset_index(drop=True)
    d = t["d"].to_numpy(float)
    d = np.where(np.isfinite(d), d, np.nanmedian(d) if np.isfinite(d).any() else 30.0)
    rng = np.random.default_rng(seed)
    adv, means = 0, []
    for _ in range(draws):
        net, K = np.zeros(len(t)), np.zeros(len(t))
        for i, r in enumerate(t.itertuples(index=False)):
            g = by_ev.get(r.gid)
            cand = g[g["capture_id"] != r.capture_id] if g is not None else None
            if cand is None or not len(cand):
                continue
            c = float(cand["C"].iloc[int(rng.integers(len(cand)))])
            net[i], K[i] = 1.0 - c, c
        res = mean_gate(net, t["gid"].to_numpy(), t["day"].to_numpy(), floor=FLOORS["D2"], alpha=alpha,
                        n_boot=n_boot, seed=seed, r_ann=r_ann_of(net, K, d), need_rann=True)
        means.append(res.get("mean", math.nan))
        adv += int(res["advance"])
    return {"draws": draws, "advance_rate": adv / max(draws, 1), "n_advance": adv,
            "mean_net": float(np.nanmean(means)) if np.isfinite(means).any() else math.nan,
            "calibrated": adv / max(draws, 1) <= PLACEBO_MAX_ADVANCE_RATE}


def build_negrisk(extract_root: Path, cl: dict, window: str, *, t_rep_start: str | None = None,
                  outcomes: dict[str, float] | None = None, asof_only: bool = False) -> dict:
    """Load a frozen window and build event-captures and triggers (no test statistic computed here)."""
    members = members_asof_loader(extract_root)
    df, cs_by, load_cnt = load_window_captures(extract_root, cl, window, "negrisk", t_rep_start)
    ec, ecnt = negrisk_event_captures(df, members, outcomes, asof_only=asof_only,
                                      first_fetch=None if asof_only else load_first_fetch(extract_root))
    nxt, pcnt = next_capture_pairs(cs_by)
    fin = {**final_yes_map(df), **(outcomes or {})}
    trig, tcnt = d2_triggers(ec, nxt, fin)
    return {"ec": ec, "trig": trig, "counts": {"load": load_cnt, "event_captures": ecnt, "pairs": pcnt,
                                                "triggers": tcnt, "n_captures": len(cs_by)}}


def census_negrisk(built: dict) -> dict:
    """Counts only (population/testability); no incidence, no net, no p-value."""
    ec, trig = built["ec"], built["trig"]
    return {**built["counts"], "n_event_clusters": int(ec["gid"].nunique()) if len(ec) else 0,
            "n_trigger_events": int(trig["gid"].nunique()) if len(trig) else 0,
            "n_trigger_rows": int(len(trig)), "n_executed": int(trig["executed"].sum()) if len(trig) else 0,
            "n_days": int(ec["day"].nunique()) if len(ec) else 0}


def run_negrisk(extract_root: Path, cl: dict, window: str, *, n_boot: int, dev: bool, alpha: float,
                t_rep_start: str | None = None, seed: int = SEED, placebo_draws: int = PLACEBO_DRAWS,
                outcomes: dict[str, float] | None = None, tests: tuple[str, ...] = ("D1", "D2")) -> dict:
    """D1/D2 on a frozen window with the D2 placebo. ``tests`` restricts which tests are reported
    (replication runs only the tests that advanced in dev)."""
    built = build_negrisk(extract_root, cl, window, t_rep_start=t_rep_start, outcomes=outcomes)
    ec, trig = built["ec"], built["trig"]
    allt = negrisk_tests(ec, trig, n_boot=n_boot, dev=dev, alpha=alpha, seed=seed)
    out_tests = {k: v for k, v in allt.items() if k in tests}
    placebo: dict = {}
    if "D2" in out_tests:
        placebo["D2"] = d2_placebo(ec, trig, draws=placebo_draws, seed=seed + 1, alpha=alpha) if len(trig) else \
            {"draws": 0, "advance_rate": 0.0, "n_advance": 0, "calibrated": True}
        if not placebo["D2"]["calibrated"]:
            out_tests["D2"]["advance"] = False
            out_tests["D2"]["placebo_miscalibrated"] = True
    # declared sensitivity: the same tests on as-of member counts only (no placebo; never gates anything)
    sb = build_negrisk(extract_root, cl, window, t_rep_start=t_rep_start, outcomes=outcomes, asof_only=True)
    sens = negrisk_tests(sb["ec"], sb["trig"], n_boot=n_boot, dev=dev, alpha=alpha, seed=seed)
    return {"window": window, "capture_list_sha256": cl["sha256"], "missing_listed_captures": cl["missing_ids"],
            **built["counts"], "tests": out_tests, "placebo": placebo,
            "sensitivity_asof_only": {"counts": sb["counts"], "tests": {k: v for k, v in sens.items() if k in tests},
                                      "note": "declared sensitivity (MEMBER_COUNT_RULE); descriptive, does not gate"}}


def window_market_ids(extract_root: Path, cl: dict, window: str, t_rep_start: str | None = None) -> list[str]:
    """Sorted unique member market ids of the window's neg-risk event-captures (outcome-fetch targets)."""
    df, _cs, _cnt = load_window_captures(extract_root, cl, window, "negrisk", t_rep_start)
    return sorted(set(df["market_id"].astype(str))) if len(df) else []


def write_outcomes_csv(path: Path, outcomes: dict[str, dict], ids: list[str]) -> str:
    """market_id, final_yes (blank = unknown/unresolved), closed_time. Never overwrites."""
    path = Path(path)
    if path.exists():
        raise Cb1Error(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"market_id": m, "final_yes": (outcomes.get(m) or {}).get("final_yes"),
             "closed_time": (outcomes.get(m) or {}).get("closed_time", "")} for m in ids]
    pd.DataFrame(rows, columns=["market_id", "final_yes", "closed_time"]).to_csv(path, index=False)
    return provenance.sha256_file(path)


def load_outcomes_csv(path: Path) -> dict[str, float]:
    """market_id, final_yes (0, 0.5, 1) from the outcomes fetch; a blank final_yes is unknown."""
    o = pd.read_csv(forecast.require_local(Path(path)), dtype={"market_id": str})
    return {str(m): float(f) for m, f in zip(o["market_id"], pd.to_numeric(o["final_yes"], errors="coerce"),
                                             strict=True) if not math.isnan(f)}


# =============================================================================================
# CB1-B: ladders
# =============================================================================================


def yes_final(r: dict) -> float:
    """Final YES payout of a closed rung from Gamma outcomePrices: 0, 0.5 or 1; NaN otherwise."""
    try:
        p = json.loads(r["outcome_prices"]) if isinstance(r.get("outcome_prices"), str) else None
        v = float(p[0])
    except (ValueError, TypeError, IndexError, KeyError):
        return math.nan
    return v if r.get("closed") and v in (0.0, 0.5, 1.0) else math.nan


def no_ask(v_yes: float, fee_category=None) -> tuple[float, float]:
    """R1 modelled NO ask and its taker fee: n1 + max(h(n1), 1c), capped 0.999."""
    n1 = 1.0 - v_yes
    a = min(n1 + max(half_spread(n1), 0.01), 0.999)
    return a, docs_fee(a, fee_category)


def trade_before(ts: np.ndarray | None, truncated: bool, t: float) -> bool | None:
    """>= 1 trade with venue ts < t. True if a stored trade satisfies it; otherwise None (unavailable,
    never 0) in a truncated market, False in a complete one; None when no trades were stored/fetched."""
    if ts is None:
        return None
    if len(ts) and float(np.min(ts)) < t:
        return True
    return None if truncated else False


def exclusion_sets(runs_dir: Path, runs: list[str], ifh2_ladders: list[dict] | None) -> dict[str, set]:
    """Event and market ids to exclude: IF-H2 ladders plus the h1/h2/h3 samples (fail loudly if missing)."""
    mk: set[str] = set()
    ev: set[str] = set()
    for r in ifh2_ladders or []:
        ev.add(str(r["event_id"]))
        mk.update(str(x["market_id"]) for x in r["rungs"])
    for run in runs:
        p = forecast.require_local(Path(runs_dir) / run / "sample.csv.gz")
        d = pd.read_csv(p, dtype=str, usecols=lambda c: c in ("market_id", "event_id"))
        mk.update(d["market_id"].dropna())
        if "event_id" in d:
            ev.update(d["event_id"].dropna())
    return {"markets": mk, "events": ev}


def apply_exclusions(ladders: list[dict], excl: dict[str, set]) -> tuple[list[dict], dict]:
    """Drop any ladder whose event id or any rung id is in the exclusion sets."""
    kept, n_ev, n_mk = [], 0, 0
    for L in ladders:
        if str(L["event_id"]) in excl["events"]:
            n_ev += 1
        elif any(str(r["market_id"]) in excl["markets"] for r in L["rungs"]):
            n_mk += 1
        else:
            kept.append(L)
    return kept, {"in": len(ladders), "kept": len(kept), "dropped_event_id": n_ev, "dropped_rung_id": n_mk}


def near_rung_origins(ladder: dict, series: Callable, trades: Callable, grid: np.ndarray, *,
                      t_censor: float | None = None) -> tuple[list[dict], list[dict]]:
    """One origin per near rung (the first eligible), using only information available at t.

    ``series(mid) -> (ts, vals) | None``; ``trades(mid) -> (ts_array | None, truncated)``.
    Near = earliest-deadline rung OPEN at t (``created_at <= t < closed_time``, both facts at t) with >= 2 days
    to its deadline; far = the next-deadline open rung. A rung's resolution is never used to choose it. If an
    earlier candidate origin had an unavailable trade condition (truncation), the rung is excluded and
    recorded, never silently kept."""
    rungs = sorted(ladder["rungs"], key=lambda r: r["deadline"])
    created = np.array([hb._epoch(r.get("created_at")) for r in rungs], float)
    closed_t = np.array([hb._epoch(r.get("closed_time")) for r in rungs], float)
    deadline = np.array([float(r["deadline"]) for r in rungs], float)
    done: set[str] = set()
    units, excluded = [], []
    last_t = (t_censor - B_CENSOR_MARGIN_D * 86400) if t_censor is not None else math.inf
    with np.errstate(invalid="ignore"):
        for t in grid:
            t = float(t)
            if t > last_t:
                break
            op = (np.isnan(created) | (created <= t)) & (np.isnan(closed_t) | (t < closed_t))
            cand = np.flatnonzero(op & (deadline - t >= B_MIN_LEFT_S))
            if not len(cand):
                if not np.any(np.isnan(closed_t) | (t < closed_t)):
                    break  # every rung closed: nothing more can open
                continue
            i = int(cand[0])
            near = rungs[i]
            if near["market_id"] in done:
                continue
            fj = np.flatnonzero(op & (deadline > deadline[i]))
            if not len(fj):
                continue
            far = rungs[int(fj[0])]
            s1 = series(near["market_id"])
            s2 = series(far["market_id"])
            if s1 is None or s2 is None:
                continue
            v1 = if_h2.asof(s1[0], s1[1], t)
            v2 = if_h2.asof(s2[0], s2[1], t)
            if not (math.isfinite(v1) and math.isfinite(v2) and B_V1_RANGE[0] <= v1 <= B_V1_RANGE[1]
                    and v1 <= v2 + B_MONO_TOL):
                continue
            ts1, tr1 = trades(near["market_id"])
            tb = trade_before(ts1, bool(tr1), t)
            a, f = no_ask(v1, near.get("fee_category"))
            if tb is None:
                done.add(near["market_id"])
                excluded.append({"ladder_id": ladder["ladder_id"], "event_id": ladder["event_id"],
                                 "near_id": near["market_id"], "t": t, "reason": "trade_condition_unavailable",
                                 "a": a, "f": f, "near": near})
                continue
            if not tb:
                continue
            done.add(near["market_id"])
            far_valid, a2, f2 = False, math.nan, math.nan
            if B_V2_RANGE[0] <= v2 <= B_V2_RANGE[1]:
                ts2, tr2 = trades(far["market_id"])
                far_valid = bool(trade_before(ts2, bool(tr2), t))  # unavailable -> pair invalid
                a2, f2 = no_ask(v2, far.get("fee_category"))
            units.append({"ladder_id": ladder["ladder_id"], "event_id": ladder["event_id"],
                          "near_id": near["market_id"], "far_id": far["market_id"], "t": t, "v1": v1, "v2": v2,
                          "a": a, "f": f, "far_valid": far_valid, "a_far": a2, "f_far": f2,
                          "near": near, "far": far})
    return units, excluded


def _value_leg(rung: dict, a: float, f: float, t: float, series, t_censor: float, y_override=None
               ) -> tuple[float, bool, float, str]:
    """(net, censored, hold_days, status) for one NO leg bought at modelled ask ``a``, held to resolution.
    Unresolved at ``t_censor``: marked at the last as-of NO price minus h and the exit fee (flagged)."""
    y_yes = yes_final(rung) if y_override is None else y_override
    ct = hb._epoch(rung.get("closed_time"))
    if not math.isnan(y_yes) and (math.isnan(ct) or ct <= t_censor):
        d = ((ct if not math.isnan(ct) else rung["deadline"]) - t) / 86400.0
        return (1.0 - y_yes) - a - f, False, d, "resolved"
    if rung.get("closed") and math.isnan(y_yes):
        return math.nan, False, math.nan, "closed_no_outcome"
    s = series(rung["market_id"])
    if s is None:
        return math.nan, True, math.nan, "censored_no_price"
    p = if_h2.asof(np.asarray(s[0], float), np.asarray(s[1], float), t_censor)
    if not math.isfinite(p):
        return math.nan, True, math.nan, "censored_no_price"
    n_last = 1.0 - p
    exit_bid = max(n_last - max(half_spread(n_last), 0.0), 0.0)
    return exit_bid - economics.taker_fee(1.0, exit_bid, leg_rate(None, rung.get("fee_category"))[0]) \
        - a - f, True, (t_censor - t) / 86400.0, "censored"


def ladder_pnl(units: list[dict], series, t_censor: float, cens_value: float | None = None) -> pd.DataFrame:
    """Per-rung P&L rows. ``cens_value``: None = mark-to-last, 0.0/1.0 = NO payout sensitivity."""
    rows = []
    for u in units:
        near = u["near"]
        net, cens, d, st = _value_leg(near, u["a"], u["f"], u["t"], series, t_censor)
        if cens_value is not None and cens:
            net = cens_value - u["a"] - u["f"]
        row = {**{k: u[k] for k in ("ladder_id", "event_id", "near_id", "t", "v1", "v2", "a", "f")},
               "net": net, "K": u["a"] + u["f"], "d": d, "censored": cens, "status": st}
        # ladder clustering: ladder event x ISO week of the near rung's scheduled deadline (section 2.3)
        row["week"] = pd.Timestamp(float(near["deadline"]), unit="s", tz="UTC").strftime("%G-W%V")
        row["net_far"] = math.nan
        row["far_status"] = "invalid"
        if u["far_valid"]:
            nf, cf, _d, sf = _value_leg(u["far"], u["a_far"], u["f_far"], u["t"], series, t_censor)
            if cens_value is not None and cf:
                nf = cens_value - u["a_far"] - u["f_far"]
            row["net_far"], row["far_status"] = nf, sf
        rows.append(row)
    cols = ["ladder_id", "event_id", "near_id", "t", "v1", "v2", "a", "f", "net", "K", "d", "censored", "status",
            "week", "net_far", "far_status"]
    return pd.DataFrame(rows, columns=cols)


def _units_for_test(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["net"].notna()].copy()


def breakeven_placebo(u: pd.DataFrame, *, floor: float, alpha: float = ALPHA_STAGE1, draws: int = PLACEBO_DRAWS,
                      seed: int = SEED + 2, n_boot: int = 20) -> dict:
    """Y_NO ~ Bern(min(a+f, 1)) so expected net is exactly 0; rerun the gate; advance rate must be <= 1.5%."""
    rng = np.random.default_rng(seed)
    K = u["K"].to_numpy(float)
    d = u["d"].to_numpy(float)
    ev, wk = u["event_id"].to_numpy(), u["week"].to_numpy()
    adv = 0
    for _ in range(draws):
        y = (rng.random(len(K)) < np.minimum(K, 1.0)).astype(float)
        net = y - K
        res = mean_gate(net, ev, wk, floor=floor, alpha=alpha, n_boot=n_boot, seed=seed,
                        r_ann=r_ann_of(net, K, d), need_rann=True, cost_add=np.full(len(K), COST_SENS))
        adv += int(res["advance"])
    return {"draws": draws, "n_advance": adv, "advance_rate": adv / max(draws, 1),
            "calibrated": adv / max(draws, 1) <= PLACEBO_MAX_ADVANCE_RATE}


def ladder_tests(df: pd.DataFrame, excluded: list[dict], *, n_boot: int, alpha: float, seed: int = SEED,
                 id_b1: str = "B1", with_b2: bool = True, placebo_draws: int = PLACEBO_DRAWS) -> dict:
    """B1 (economic) and optionally B2 (near - far paired mechanism), plus reported-not-binding bounds."""
    u = _units_for_test(df)
    cost = np.full(len(u), COST_SENS)
    out = {id_b1: mean_gate(u["net"], u["event_id"], u["week"], floor=FLOORS[id_b1], alpha=alpha, n_boot=n_boot,
                            seed=seed, r_ann=r_ann_of(u["net"].to_numpy(float), u["K"].to_numpy(float),
                                                      u["d"].to_numpy(float)),
                            need_rann=True, cost_add=cost)} if len(u) else \
        {id_b1: {"testable": False, "p": 1.0, "advance": False, "reason": "no units"}}
    placebo = {}
    if len(u):
        placebo[id_b1] = breakeven_placebo(u, floor=FLOORS[id_b1], alpha=alpha, draws=placebo_draws, seed=seed + 2)
        if not placebo[id_b1]["calibrated"]:
            out[id_b1]["advance"] = False
            out[id_b1]["placebo_miscalibrated"] = True
    cens_n = int(u["censored"].sum()) if len(u) else 0
    out[id_b1]["censored_share"] = cens_n / len(u) if len(u) else math.nan
    out[id_b1]["resolution_lag_sensitive"] = bool(len(u) and cens_n / len(u) > B_MAX_CENSORED_SHARE)
    reported = {"excluded_truncation": len(excluded)}
    if excluded and len(u):
        net = np.r_[u["net"].to_numpy(float), [-(e["a"] + e["f"]) for e in excluded]]
        reported["truncation_worst_case_mean"] = float(net.mean())
    out[id_b1]["reported"] = reported
    if with_b2:
        p = u[u["net_far"].notna()]
        if len(p):
            diff = (p["net"] - p["net_far"]).to_numpy(float)
            out["B2"] = mean_gate(diff, p["event_id"], p["week"], floor=FLOORS["B2"], alpha=alpha, n_boot=n_boot,
                                  seed=seed, cost_add=None)
            out["B2"]["mean_near"], out["B2"]["mean_far"] = float(p["net"].mean()), float(p["net_far"].mean())
        else:
            out["B2"] = {"testable": False, "p": 1.0, "advance": False, "reason": "no valid far-rung pairs"}
    return {"tests": out, "placebo": placebo}


def calendar_disjoint_subset(df: pd.DataFrame) -> pd.DataFrame:
    """Secondary for R1: origins before IF-H2's grid start (2025-09-01)."""
    return df[df["t"] < _ep(B1_CALENDAR_DISJOINT_END)]


# ---- R1 runner over a ladders run directory ---------------------------------------------------


def committed_listing_hash(run_id: str, seals_dir: Path = SEALS_DIR) -> str:
    """Listing hash of the committed seal copy: ONE file per sealed run, ``<run_id>_SEAL.json``, with a top-level
    ``listing_sha256`` (the format ``h5_seal.require_sealed`` reads). No other layout is accepted. Fail closed."""
    p = Path(seals_dir) / f"{run_id}_SEAL.json"
    if not p.exists():
        raise SealUnavailableError(f"no committed seal copy {p}; refusing to read h5")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise SealUnavailableError(f"committed seal copy unreadable: {p}") from exc
    h = doc.get("listing_sha256") if isinstance(doc, dict) else None
    if not isinstance(h, str) or not h:
        raise SealUnavailableError(f"{p.name}: no top-level listing_sha256 (only the one-file-per-run format is accepted)")
    return h


def require_sealed(run_dir: Path, seals_dir: Path = SEALS_DIR) -> dict:
    """The h5 guard: the run must verify against its own SEAL.json AND the committed repo copy must exist and
    carry the same listing hash. Reads nothing else."""
    from . import h5_seal

    run_dir = Path(run_dir)
    try:
        seal = h5_seal.verify_seal(run_dir)
    except h5_seal.SealError as exc:
        raise SealUnavailableError(str(exc)) from exc
    want = committed_listing_hash(run_dir.name, seals_dir)
    if seal["listing_sha256"] != want:
        raise SealUnavailableError(f"{run_dir.name}: listing hash {seal['listing_sha256']} != committed {want}")
    return seal


def append_access_log(run_dir: Path, job: str, files: list[str], decl_sha: str) -> dict:
    from . import h5_seal

    return h5_seal.log_access(Path(run_dir), job, files, declaration_sha=decl_sha)


def _read_pts(path_base: Path) -> tuple[np.ndarray, np.ndarray] | None:
    """Hourly price points ``t, p`` (sorted by t); None if the file is absent."""
    gz = path_base.with_name(path_base.name + ".csv.gz")
    if not gz.exists():
        return None
    d = pd.read_csv(gz).dropna().sort_values("t", kind="stable")
    if not len(d):
        return None
    return d["t"].to_numpy(float), d["p"].to_numpy(float)


def _min_trade_ts(path: Path) -> np.ndarray | None:
    """Only the earliest trade stamp is needed for ``trade_before`` (one-element array; empty if no trades)."""
    if not path.exists():
        return None
    ts = pd.read_csv(path, usecols=["ts"])["ts"].to_numpy(float)
    return np.array([ts.min()]) if len(ts) else np.array([], float)


def load_trade_flags(run_dir: Path) -> dict[str, bool]:
    """``trades_truncated`` per rung from ``progress.jsonl`` (the fetcher's per-rung record). A rung with no
    ``done`` record has no flag and is treated as truncated (unknown = unavailable, fail closed)."""
    p = forecast.require_local(Path(run_dir) / "progress.jsonl")
    out: dict[str, bool] = {}
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("status") == "done":
                out[str(r["market_id"])] = bool(r.get("trades_truncated"))
    return out


def run_ladders_r1(run_dir: Path, *, n_boot: int, decl_sha: str, job: str, alpha: float = ALPHA_STAGE2,
                   exclude: dict[str, set] | None = None, seed: int = SEED, placebo_draws: int = PLACEBO_DRAWS,
                   min_ladders: int = 300, seals_dir: Path = SEALS_DIR, t_censor: float | None = None) -> dict:
    """B1/B2 on ``h5_cb1_ladders`` (frozen definitions; one read, logged). Refuses unless sealed and the seal
    matches the committed copy. ``t_censor`` defaults to the manifest ``request_clock_now`` (T_fetch)."""
    run_dir = Path(run_dir)
    require_sealed(run_dir, seals_dir)
    append_access_log(run_dir, job, ["ladders.jsonl.gz", "progress.jsonl", "manifest.json", "prices/*", "trades/*"],
                      decl_sha)
    if t_censor is None:
        t_censor = _ep(json.loads((run_dir / "manifest.json").read_text())["request_clock_now"])
    lad = if_h2.load_jsonl_gz(forecast.require_local(run_dir / "ladders.jsonl.gz"))
    guard = None
    if exclude is not None:
        lad, guard = apply_exclusions(lad, exclude)
    if len(lad) < min_ladders:
        return {"not_testable": True, "reason": f"{len(lad)} usable ladders < {min_ladders}", "guard": guard,
                "t_censor": t_censor, "tests": {t: {"testable": False, "p": 1.0, "advance": False}
                                                for t in ("B1", "B2")}, "placebo": {}}
    flags = load_trade_flags(run_dir)
    cache: dict[str, object] = {}

    def series(mid):
        if mid not in cache:
            cache[mid] = _read_pts(run_dir / "prices" / mid)
        return cache[mid]

    tcache: dict[str, tuple] = {}

    def trades(mid):
        if mid not in tcache:
            tcache[mid] = (_min_trade_ts(run_dir / "trades" / f"{mid}.csv.gz"), flags.get(mid, True))
        return tcache[mid]

    units, excluded = [], []
    for L in lad:
        c = np.array([hb._epoch(r.get("created_at")) for r in L["rungs"]], float)
        lo = float(np.nanmin(c)) if np.isfinite(c).any() else float(min(r["deadline"] for r in L["rungs"]))
        hi = max(r["deadline"] for r in L["rungs"])
        grid = np.arange(math.ceil(lo / B_GRID_S) * B_GRID_S, hi, B_GRID_S)
        u, e = near_rung_origins(L, series, trades, grid, t_censor=t_censor)
        units += u
        excluded += e
    df = ladder_pnl(units, series, t_censor)
    res = ladder_tests(df, excluded, n_boot=n_boot, alpha=alpha, seed=seed, placebo_draws=placebo_draws)
    sens = {}
    for cv in (0.0, 1.0):
        d2 = ladder_pnl(units, series, t_censor, cens_value=cv)
        sens[f"censored_at_{int(cv)}"] = float(d2["net"].mean()) if d2["net"].notna().any() else math.nan
    miss = df["status"].isin(["closed_no_outcome", "censored_no_price"])
    if len(df) and miss.any():  # worst case: closed-without-outcome and unpriced rungs lose their NO leg
        worst = df["net"].where(~miss, -(df["a"] + df["f"]))
        sens["missing_outcome_as_loss_mean"] = float(worst.mean())
    sub = calendar_disjoint_subset(df)
    sens["calendar_disjoint_mean"] = float(sub["net"].mean()) if sub["net"].notna().any() else math.nan
    return {"not_testable": False, "guard": guard, "t_censor": t_censor, "n_ladders": len(lad),
            "n_units": int(len(df)), "status_counts": df["status"].value_counts().to_dict() if len(df) else {},
            "n_excluded_truncation": len(excluded), "sensitivities": sens, **res,
            "stage": "stage2_pre_holm", "holm_pending": True}


# =============================================================================================
# CB1-B3: prospective rungs
# =============================================================================================


def walk_events(lim, start: datetime, end: datetime, step_days: int = 7, log=print) -> tuple[list[dict], dict]:
    """Gamma /events walk by start date, keeping each event's ``startDate`` (metadata only)."""
    from datetime import timedelta
    events: dict[str, dict] = {}
    report = {"windows": 0, "split": 0, "capped": 0, "requests": 0}
    stack, t = [], start
    while t < end:
        stack.append((t, min(t + timedelta(days=step_days), end)))
        t += timedelta(days=step_days)
    while stack:
        a, b = stack.pop(0)
        rows, capped, off = [], False, 0
        while True:
            params = [("start_date_min", a.strftime("%Y-%m-%dT%H:%M:%SZ")),
                      ("start_date_max", b.strftime("%Y-%m-%dT%H:%M:%SZ")), ("limit", 100), ("offset", off),
                      *[("exclude_tag_id", x) for x in if_h2.EXCLUDE_TAGS]]
            status, data = lim.get(if_h2.GAMMA_EVENTS, params)
            report["requests"] += 1
            if status != 200 or not isinstance(data, list):
                break
            rows.extend(data)
            if len(data) < 100:
                break
            off += 100
            if off >= hb.GAMMA_OFFSET_CAP:
                capped = True
                break
        if capped and (b - a) > timedelta(hours=3):
            mid = a + (b - a) / 2
            stack[:0] = [(a, mid), (mid, b)]
            report["split"] += 1
            continue
        report["windows"] += 1
        report["capped"] += int(capped)
        for e in rows:
            ms = [{k: m.get(k) for k in ("id", "question", "groupItemTitle", "clobTokenIds", "negRisk",
                                          "createdAt", "closedTime", "closed", "outcomePrices", "outcomes",
                                          "endDate")} for m in (e.get("markets") or [])]
            events[str(e.get("id"))] = {"id": str(e.get("id")), "title": e.get("title"), "negRisk": e.get("negRisk"),
                                        "startDate": e.get("startDate"), "markets": ms}
        log(f"  {a:%Y-%m-%d} .. {b:%Y-%m-%d}: {len(rows)} events (capped={capped})")
    return list(events.values()), report


def build_rung_list(events: list[dict], as_of: str, deadline_max: str = DEADLINE_MAX,
                    ifh2_event_ids: set[str] | None = None) -> dict:
    """Metadata-only B3 rung list. Ladders (``ladder-grouper-v1``) with >= 1 rung whose deadline lies in
    [as_of + 2d, deadline_max]; outcome fields are stripped. Rungs are flagged ``in_window``."""
    lo = _ep(as_of) + B_MIN_LEFT_S
    hi = if_h2._deadline_epoch(pd.Timestamp(deadline_max).date())
    start_of = {str(e["id"]): e.get("startDate") for e in events}
    out = []
    for L in if_h2.group_ladders(events):
        rs = [{"market_id": r["market_id"], "deadline": r["deadline"], "token_yes": r["token_yes"],
               "created_at": r["created_at"], "question": r["question"], "in_window": bool(lo <= r["deadline"] <= hi)}
              for r in L["rungs"]]
        if not any(r["in_window"] for r in rs):
            continue
        sd = start_of.get(L["event_id"])
        in_ifh2 = bool(sd) and _ep(IFH2_START_RANGE[0] + "T00:00:00Z") <= _ep(sd) <= _ep(IFH2_START_RANGE[1] + "T23:59:59Z")
        out.append({"ladder_id": L["ladder_id"], "event_id": L["event_id"], "stem": L["stem"],
                    "event_start_date": sd, "ifh2_period": in_ifh2 or (L["event_id"] in (ifh2_event_ids or set())),
                    "rungs": rs})
    return {"version": VERSION, "grouper": if_h2.GROUPER_VERSION, "as_of_utc": as_of, "deadline_max": deadline_max,
            "n_ladders": len(out), "n_rungs": sum(len(x["rungs"]) for x in out), "ladders": out}


def write_rung_list(doc: dict, path: Path) -> str:
    """Write the list and its sha256 sidecar; refuses to overwrite either (immutable once hashed)."""
    path = Path(path)
    side = path.with_name(path.name + ".sha256")
    if path.exists() or side.exists():
        raise RungListError(f"{path} already exists; the B3 rung list is immutable after its hash is written")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(doc, sort_keys=True, indent=1).encode()
    path.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    side.write_text(sha + "\n")
    return sha


def load_rung_list(path: Path, expected_sha256: str | None = None) -> dict:
    path = forecast.require_local(Path(path))
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    side = path.with_name(path.name + ".sha256")
    if side.exists() and side.read_text().strip() != sha:
        raise RungListError(f"{path}: sha256 {sha} != sidecar {side.read_text().strip()}")
    if expected_sha256 is not None and expected_sha256 != sha:
        raise RungListError(f"{path}: sha256 {sha} != committed {expected_sha256}")
    doc = json.loads(data)
    doc["sha256"] = sha
    return doc


def _mid(bid: float, ask: float) -> float:
    return (bid + ask) / 2.0 if (bid > 0 and ask > bid and ask < 1) else math.nan


def prospective_rungs(rows: pd.DataFrame, rung_list: dict, *, outcomes: dict[str, dict] | None = None,
                      t_censor: float = _ep(T_CENSOR_B3), only_non_ifh2: bool = False) -> pd.DataFrame:
    """B3 units from the extract ``rungs`` tables. Per capture (in time order), per listed ladder: the
    earliest-deadline listed rung that is open (not closed, accepting orders) with >= 2 days to its deadline,
    ``in_window``, v1 (mid of YES bid/ask) in [0.05, 0.60], v1 <= v2 + 0.01 (v2 = next open rung's mid),
    ``last_trade_price`` present and ``volume_num`` > 0 (if the column exists). One unit per rung (first
    eligible capture). Entry at the recorded ask 1 - best_bid(YES). Only rows with an outcome available at
    ``t_censor`` and a deadline that has passed are valued; others are skipped (not yet due).
    ``outcomes``: market_id -> {final_yes, closed_time}."""
    outcomes = outcomes or {}
    ladders = []
    for L in rung_list["ladders"]:
        if only_non_ifh2 and L.get("ifh2_period"):
            continue
        ladders.append((L, sorted(L["rungs"], key=lambda r: r["deadline"])))
    if not len(rows):
        return pd.DataFrame()
    rows = rows.copy()
    rows["market_id"] = rows["market_id"].astype(str)
    rows["capture_id"] = rows["capture_id"].astype(str)
    rows["open"] = (_flag(rows["closed"]) == 0) & (_flag(rows["accepting_orders"]) == 1)
    num = [c for c in ("best_bid", "best_ask", "last_trade_price", "volume_num", "sw1_best_bid", "sw1_bid_size_1")
           if c in rows]
    for c in num:
        rows[c] = pd.to_numeric(rows[c], errors="coerce")
    cap_starts = rows.groupby("capture_id")["cs"].first().sort_values(kind="stable")
    deadline_max = if_h2._deadline_epoch(pd.Timestamp(rung_list["deadline_max"]).date())
    done: set[str] = set()
    last_row: dict[str, dict] = {}
    units = []
    by_cap = dict(tuple(rows.groupby("capture_id", sort=False)))
    for c, t in cap_starts.items():
        t = float(t)
        g = by_cap[c].drop_duplicates("market_id").set_index("market_id").to_dict("index")
        last_row.update(g)
        for L, rs in ladders:
            openr = [r for r in rs if r["market_id"] in g and g[r["market_id"]]["open"]]
            near = next((r for r in openr if r["deadline"] - t >= B_MIN_LEFT_S), None)
            if near is None or near["market_id"] in done or not near["in_window"] or near["deadline"] > deadline_max:
                continue
            far = next((r for r in openr if r["deadline"] > near["deadline"]), None)
            if far is None:
                continue
            n, f_ = g[near["market_id"]], g[far["market_id"]]
            v1, v2 = _mid(n.get("best_bid", math.nan), n.get("best_ask", math.nan)), \
                _mid(f_.get("best_bid", math.nan), f_.get("best_ask", math.nan))
            ltp, vol = n.get("last_trade_price", math.nan), n.get("volume_num", 1.0)
            if not (math.isfinite(v1) and math.isfinite(v2) and B_V1_RANGE[0] <= v1 <= B_V1_RANGE[1]
                    and v1 <= v2 + B_MONO_TOL and pd.notna(ltp) and pd.notna(vol) and vol > 0):
                continue
            done.add(near["market_id"])
            a = 1.0 - float(n["best_bid"])
            cat = n.get("fee_category")
            swb, sws = n.get("sw1_best_bid", math.nan), n.get("sw1_bid_size_1", math.nan)
            units.append({"ladder_id": L["ladder_id"], "event_id": L["event_id"], "near_id": near["market_id"],
                          "t": t, "v1": v1, "v2": v2, "a": a, "f": docs_fee(a, cat), "deadline": near["deadline"],
                          "ifh2_period": bool(L.get("ifh2_period")),
                          "sweep_ok": bool(pd.notna(swb) and pd.notna(sws) and float(sws) >= D_DEPTH_MIN_SIZE),
                          "a_sweep": (1.0 - float(swb)) if pd.notna(swb) else math.nan})
    out = []
    for u in units:
        o = outcomes.get(u["near_id"])
        fy = o.get("final_yes") if o else None
        ct = hb._epoch(o.get("closed_time")) if o else math.nan
        resolved = fy is not None and not (isinstance(fy, float) and math.isnan(fy)) \
            and (math.isnan(ct) or ct <= t_censor)
        lr = last_row.get(u["near_id"])
        if resolved:
            net = (1.0 - float(fy)) - u["a"] - u["f"]
            d = ((ct if not math.isnan(ct) else u["deadline"]) - u["t"]) / 86400.0
            cens, st = False, "resolved"
        elif u["deadline"] <= t_censor and lr is not None and pd.notna(lr.get("best_ask")):
            net = (1.0 - float(lr["best_ask"])) - u["a"] - u["f"]  # last extracted NO bid
            d, cens, st = (t_censor - u["t"]) / 86400.0, True, "censored"
        else:
            continue  # not yet due: no outcome read allowed
        out.append({**{k: u[k] for k in ("ladder_id", "event_id", "near_id", "t", "v1", "v2", "a", "f", "ifh2_period",
                                         "sweep_ok", "a_sweep")},
                    "net": net, "K": u["a"] + u["f"], "d": d, "censored": cens, "status": st,
                    "yes_final": float(fy) if resolved else math.nan,
                    "week": pd.Timestamp(u["deadline"], unit="s", tz="UTC").strftime("%G-W%V")})
    cols = ["ladder_id", "event_id", "near_id", "t", "v1", "v2", "a", "f", "ifh2_period", "sweep_ok", "a_sweep",
            "net", "K", "d", "censored", "status", "yes_final", "week"]
    return pd.DataFrame(out, columns=cols)


def survivorship_check(rungs: pd.DataFrame) -> dict:
    """``rungs``: market_id, in_walk (returned by the re-walk), yes_final, net. Gating label."""
    if not len(rungs):
        return {"checked": False}
    miss = rungs[~rungs["in_walk"]]
    ret = rungs[rungs["in_walk"]]
    share = len(miss) / len(rungs)
    yes_m = float((miss["yes_final"] > 0.5).mean()) if len(miss) else math.nan
    yes_r = float((ret["yes_final"] > 0.5).mean()) if len(ret) else math.nan
    biased = bool(share >= B_SURVIVOR_MISSING and len(ret) and len(miss) and abs(yes_m - yes_r) > B_SURVIVOR_YES_DIFF)
    return {"checked": True, "share_missing": share, "yes_rate_missing": yes_m, "yes_rate_returned": yes_r,
            "net_missing": float(miss["net"].mean()) if len(miss) else math.nan,
            "net_returned": float(ret["net"].mean()) if len(ret) else math.nan,
            "listing_survivorship_biased": biased}


def fetch_outcomes(lim, ids: list[str], batch: int = 20) -> dict[str, dict]:
    """Gamma /markets outcomes for the listed rungs (read-only, metadata)."""
    out = {}
    for i in range(0, len(ids), batch):
        params = [("id", x) for x in ids[i:i + batch]] + [("limit", batch)]
        status, data = lim.get(hb.GAMMA_MARKETS, params)
        if status != 200 or not isinstance(data, list):
            continue
        for m in data:
            fy = yes_final({"outcome_prices": m.get("outcomePrices"), "closed": bool(m.get("closed"))})
            out[str(m.get("id"))] = {"final_yes": None if math.isnan(fy) else fy,
                                     "closed_time": m.get("closedTime") or ""}
    return out


def b3_tests(units: pd.DataFrame, *, n_boot: int, seed: int = SEED, placebo_draws: int = PLACEBO_DRAWS) -> dict:
    """B3: one prospective test, one-sided alpha 0.05, plus sensitivities and secondaries."""
    if not len(units):
        return {"tests": {"B3": {"testable": False, "p": 1.0, "advance": False, "reason": "no units"}},
                "placebo": {}}
    u = units
    cost = np.full(len(u), COST_SENS)
    t = mean_gate(u["net"], u["event_id"], u["week"], floor=FLOORS["B3"], alpha=ALPHA_STAGE2, n_boot=n_boot,
                  seed=seed, r_ann=r_ann_of(u["net"].to_numpy(float), u["K"].to_numpy(float),
                                            u["d"].to_numpy(float)), need_rann=True, cost_add=cost)
    pl = breakeven_placebo(u, floor=FLOORS["B3"], alpha=ALPHA_STAGE2, draws=placebo_draws, seed=seed + 2)
    if not pl["calibrated"]:
        t["advance"] = False
        t["placebo_miscalibrated"] = True
    share = float(u["censored"].mean())
    t["censored_share"] = share
    t["resolution_lag_sensitive"] = bool(share > B_MAX_CENSORED_SHARE)
    sens = {}
    for cv in (0.0, 1.0):
        n = np.where(u["censored"], cv - u["a"] - u["f"], u["net"])
        sens[f"censored_at_{int(cv)}"] = float(np.mean(n))
    non = u[~u["ifh2_period"]]
    sec = {"without_ifh2_period": mean_gate(non["net"], non["event_id"], non["week"], floor=FLOORS["B3"],
                                            alpha=ALPHA_STAGE2, n_boot=max(n_boot // 4, 100), seed=seed)
           if len(non) else {"testable": False}}
    dep = u[u["sweep_ok"] & ~u["censored"]]
    sec["depth_checked"] = {
        "n": int(len(dep)),
        "mean_net_sweep": float(((1.0 - dep["yes_final"]) - dep["a_sweep"] - dep["f"]).mean())
        if len(dep) else math.nan}
    return {"tests": {"B3": t}, "placebo": {"B3": pl}, "sensitivities": sens, "secondaries": sec}


def check_b3_read_date(now: datetime | None = None, interim: bool = False) -> None:
    """B3 outcomes are first readable at T_rung_out; the counted verdict run only at T_censor_B3."""
    ts = _utc(now).timestamp()
    if ts < _ep(T_RUNG_OUT):
        raise TooEarlyError(f"B3 outcome read refused before T_rung_out {T_RUNG_OUT}")
    if not interim and ts < _ep(T_CENSOR_B3):
        raise TooEarlyError(f"counted B3 run refused before T_censor_B3 {T_CENSOR_B3} (use --interim for a "
                            "non-counted descriptive read)")


# =============================================================================================
# Trial logging
# =============================================================================================


def log_trials(family: str, tests: dict, *, kind: str, role: str, dataset: str, results_path: str,
               results_sha256: str, run_id: str, prov: dict, decl_sha: str, placebo: dict | None = None,
               n_tests: int | None = None, path: Path = provenance.TRIALS_PATH) -> list[dict]:
    """One line per test (``kind``), one count line per run (ml_explain, source ``creative_batch_1:<family>``)
    and one placebo line (count 0) per placebo."""
    written = []
    for name, t in tests.items():
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": name, "run_id": run_id, "label": LABEL, "kind": kind,
            "evidence_role": role, "revision": VERSION, "result_path": results_path,
            "results_sha256": results_sha256, "declaration_sha256": decl_sha,
            "summary": {k: t.get(k) for k in ("mean", "p", "n", "n_event", "ci95", "r_ann", "advance", "testable")},
            "provenance": prov}, path))
    for name, p in (placebo or {}).items():
        written.append(provenance.append_trial({
            "status": "ok", "dataset": dataset, "preset": f"{name}:placebo", "run_id": run_id, "label": LABEL,
            "kind": kind, "evidence_role": "placebo", "revision": VERSION, "result_path": results_path,
            "results_sha256": results_sha256, "declaration_sha256": decl_sha,
            "summary": {k: p.get(k) for k in ("draws", "n_advance", "advance_rate", "calibrated")},
            "provenance": prov}, path))
    written.append(provenance.append_trial({
        "dataset": dataset, "evidence_role": role, "kind": "ml_explain", "label": "EXPLORATORY",
        "n_tests": len(tests) if n_tests is None else n_tests, "revision": VERSION, "run_id": run_id,
        "source": f"creative_batch_1:{family}", "results_sha256": results_sha256,
        "note": "CB1 structural count line; per-test cb1_structural* lines are EXCLUDEd in battery2.KIND_RULES"},
        path))
    return written


def write_json(path: Path, doc: dict) -> str:
    path = Path(path)
    if path.exists():
        raise Cb1Error(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(doc), indent=1, sort_keys=True, default=str))
    return provenance.sha256_file(path)


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def cumulative_total() -> dict:
    """Cumulative count at run time (recorded in each results file); never blocks a run."""
    try:
        from . import battery2
        return battery2.cumulative_count()
    except Exception as e:  # noqa: BLE001 - recorded, not hidden
        return {"error": f"{type(e).__name__}: {e}"}
