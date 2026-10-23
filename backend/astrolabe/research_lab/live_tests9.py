# ruff: noqa: E501
"""LIVE prospective tests LT9 (docs/research_lab/LIVE_TESTS_9.md, design text frozen at sha256 098aa3fb...). DRAFT: nothing is registered;
E-numbers are assigned at registration. Research tooling only; never trades; makes no network request.

CODE PHASE 1: the fresh census-input seal and the counts-only pre-registration censuses (design sections 1.2-1.5, 7 and 8.1-8.3 as they
apply to the seal and the censuses):

* CR9 (``census_feed``): CH215, the scheduled end (the optional fourth): programme ends listed >= 48 h ahead in the ``reward_params`` feed,
  decision-time eligibility and controls (reuse ban in decision-time order, re-check fix 1), connected-component clusters, its entry gate;
* CC9 (``census_captures``): CH213 (the band break: the panel fixed at the market's first unit, the control cell median, ``relpos_k`` over
  earlier units, re-check fix 6) and CH212 (the omission ``om_k = 1[carry_lag_k >= 1]``, ``clob_listed_k``, the feed-listed end after slot k + 2's
  nominal start under the 1.2 end-date parse rule, re-check fix 3, and the counts-only route rule);
* CS9 (``census_sweeps``): CH214 (the pool splits: the in-band sum innovation between sweeps k - 2 and k - 1, split at zero change,
  ``zdD+ = max(0, dD) / scale``, ``zdD- = min(0, dD) / scale``, re-check fix 2).

Censuses read origin-side fields only: no target, no outcome, no P&L. A later slot reaches census code ONLY through the lag-slot loaders
(:func:`lag_break_flag`: CH213's twin break flag; :func:`lag_band_sums`: CH214's four depths; the CH212 twin is the carry status of capture
k + 4, a status only). Every opened input is checked against the LT9 seal first (refused on any mismatch, L3); slots and origins come from the
seal, never from a local scan. LT3-LT8 code is used only through the vendored copies in ``live_tests9_base`` (8.1): this module never imports
``live_tests3`` .. ``live_tests8``. Every LT9 reward status is ``listed_carry24h_v2`` (LT7 13.7 and its erratum) through the vendored ``RewardCarry``
fed with LT8's rw frame of every sidecar row (LT8's null taxonomy).

The reader (``run_once``), ``backfill-series``, the single analysis, the size check and the RSS probe are CODE PHASE 2 (not in this file).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import forecast, panel
from . import live_tests9_base as b

VERSION = "live-tests9-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = ROOT / "data-dumps" / "research_lab" / "book_sweeps"
FEED_ROOT = ROOT / "data-dumps" / "research_lab" / "reward_params"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests9"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests9_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration
REGISTERED_UTC = "2027-01-21T00:00:00Z"  # proposed (design 1.1); slides later with LT8's END_UTC
END_UTC = "2027-02-11T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2027-02-12T12:00:00Z"
TEMPFAIL = 75
DAY_S = 86400.0
DESIGN_TEXT_SHA256 = "098aa3fb5f6765f08dcad3f85ad63ec70e29df65249413608f0f7ad5fd505b77"  # LIVE_TESTS_9.md design-text freeze (6b78ba90), 2026-10-22
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_9.md"
REWARD_NULL_RULE = "listed_carry24h_v2"
TESTS = ("CH213", "CH214", "CH212", "CH215")
CODE_FILES = ("live_tests9.py", "live_tests9_analysis.py", "live_tests9_base.py", "bounce_decomp.py",
              "panel.py", "trade_sample.py", "cb17_census.py", "cb13_label.py", "economics.py", "forecast.py", "maker_rewards.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)
SNAP_COLS9 = [*b.SNAP_COLS, "liquidity"]
EXT_COLS9 = [*b.EXT_COLS, "rewards_min_size", "rewards_max_spread", "clob_rewards", "page_index", "received_utc", "volume_num", "competitive"]
# The lag-slot loaders (design 7): the ONLY way census code reads a slot later than a unit's decision.
LAG_CAPTURE_COLUMNS = ("market_id", "best_bid", "best_ask")  # CH213: reduced to the spread and compared against 2v INSIDE the loader
LAG_SWEEP_COLUMNS = ("depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c")  # CH214: the four depths only
LAG_SWEEP_KEYS = ("market_id", "token_id")
LAG_CAPTURE_KEY_COLUMNS = ("market_id", "clob_token_id_0")
OPS_COLS = frozenset({"role", "panel", "route", "sports", "crypto", "capflag", "status", "late", "lookback", "nosweep_km1", "nosweep_km2", "kind"})
KINDS = ("bandbreak", "pool", "rwblink", "rwend")
MARKERS = (".late.csv.gz", ".nosweep_km1.csv.gz", ".nosweep_km2.csv.gz")
_EPS_C = 1e-9  # cents tolerance of the band comparisons
_Q_EPS = 1e-9

epoch, iso, sha256_file, _json = b.epoch, b.iso, b.sha256_file, b._json
_NULL_LIKE = b._NULL_LIKE


# --- pins, spec and design text ---------------------------------------------------------------------------------------------------


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LT3 9.3's rule)."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: (code_sha256(here / n) if (here / n).exists() else None) for n in CODE_FILES}


def _nan_free(o, path: str = "") -> list[str]:
    """Paths of NaN / inf floats in a parsed spec (L2: a pinned spec refuses them)."""
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
            raise RuntimeError(f"live_tests9 spec sha256 mismatch: {got} != pinned {sha}")
        if (bad := _nan_free(spec)):
            raise RuntimeError(f"live_tests9 pinned spec holds NaN / inf at {bad[:5]}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests9 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    if spec.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        raise RuntimeError("live_tests9 spec design_text_sha256 differs from the module constant")
    return spec


def reward_rule_error(spec: dict) -> dict | None:
    """1.4.1: every census refuses unless the spec declares ``reward_null_rule = listed_carry24h_v2`` with ``reward_carry_slots = 12``."""
    if spec.get("reward_null_rule") != REWARD_NULL_RULE or spec.get("reward_carry_slots") != b.REWARD_CARRY_SLOTS:
        return {"error": "the spec does not declare the reward-null rule listed_carry24h_v2 with reward_carry_slots 12: refused",
                "reward_null_rule": spec.get("reward_null_rule"), "reward_carry_slots": spec.get("reward_carry_slots")}
    return None


SPEC_HASHED_BLOCKS = ("census_gates", "census_inputs", "tests", "move", "eligibility", "grid", "crypto_rule", "crypto_classifier", "sports_rule", "series_key_rule",
                      "reward_rule", "member_cap", "reward_null_rule", "reward_carry_slots", "feed", "f_roles", "prior_population_specs")


def spec_blocks_sha(spec: dict) -> str:
    """sha256 of the canonical JSON of every spec block census code reads. The seal stores it; every census refuses a spec whose blocks
    differ from the seal-time ones. ``census_fixed`` (the values the censuses fill) is deliberately outside the hash."""
    blob = json.dumps({k_: spec.get(k_) for k_ in SPEC_HASHED_BLOCKS}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def design_text_sha(path: Path | None = None) -> str:
    return sha256_file(path or DESIGN_PATH)


def design_text_error(path: Path | None = None) -> dict | None:
    got = design_text_sha(path)
    return None if got == DESIGN_TEXT_SHA256 else {"error": "LIVE_TESTS_9.md differs from the text-frozen file: refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}


def f_role(spec: dict, test: str) -> str:
    """1.9 (R1 fix 1): F's role is fixed per test by design, never by a census count: binding for CH213 and CH214, a label for CH212, a reported
    placebo for CH215. A spec that says otherwise is refused (there is no ``f_binding`` key)."""
    fixed = {"CH213": "binding", "CH214": "binding", "CH212": "label", "CH215": "placebo"}
    got = (spec.get("f_roles") or {}).get(test)
    if got != fixed[test] or "f_binding" in spec:
        raise RuntimeError(f"F role of {test} must be {fixed[test]} (design 1.9); the spec says {got!r}")
    return got


# --- the feed (reward_params) and the end-date parse rule (1.2, re-check fix 3) ------------------------------------------------------


_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOW_BOUND = epoch("2020-01-01T00:00:00Z")


def parse_end(v, sentinel_year: int = 2100) -> tuple[float, float, str]:
    """``(earliest instant, latest instant, kind)`` of a served configuration end date (1.2). A timestamp with an offset is that instant in UTC;
    without an offset it is read as UTC (kind ``ts``); a date-only ``YYYY-MM-DD`` covers ``[D 00:00Z, D + 1 00:00Z)`` (kind ``date_only``); absent /
    null / empty is open-ended (``open``); a year >= 2100 is a sentinel for no end (``sentinel``, open-ended); anything else, including a value
    before 2020-01-01, is ``malformed`` (NaN). Each reader takes its own instant from the pair (CH212 and CH215: the earliest)."""
    nan = float("nan")
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return nan, nan, "open"
    if not isinstance(v, str):
        return nan, nan, "malformed"
    s = v.strip()
    if s.casefold() in _NULL_LIKE:
        return nan, nan, "open"
    if _DATE_ONLY.match(s):
        if int(s[:4]) >= sentinel_year:
            return nan, nan, "sentinel"
        try:
            lo = epoch(f"{s}T00:00:00Z")
        except (ValueError, TypeError):
            return nan, nan, "malformed"
        return (lo, lo + DAY_S, "date_only") if lo >= _LOW_BOUND else (nan, nan, "malformed")
    if not re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", s):
        return nan, nan, "malformed"
    try:
        ts = pd.Timestamp(s)
    except (ValueError, TypeError):
        return nan, nan, "malformed"
    if ts.year >= sentinel_year:
        return nan, nan, "sentinel"
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    t = ts.value / 1e9
    return (t, t, "ts") if t >= _LOW_BOUND else (nan, nan, "malformed")


def _num(v) -> float:
    if isinstance(v, bool) or v is None:
        return float("nan")
    try:
        x = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return x if math.isfinite(x) else float("nan")


SWITCHING_GATE_DEFINITION = ("mean over the span's UTC days (days holding at least one capture with a sidecar) of the number of markets that have BOTH a null and a listed "
                             "clob_rewards status among ALL sidecar rows of that day's span captures (no eligibility, category or cap filter); declared before the seal, code check 2026-10-23")
FEED_CACHE_FRAMES = 4  # feed frames kept in the census cache (older ones are evicted and re-read on demand)

def feed_frame(feed_dir: Path, spec: dict) -> pd.DataFrame:
    """One row per listed ``condition_id`` of a feed capture (native and sponsored records merged): ``feeds`` (native / sponsored / both), the
    band and minimum (as served; the first record's), ``rate`` (summed positive ``rate_per_day`` of its configurations), ``n_pos`` (positive
    configurations), and the end of the market's positive configurations under :func:`parse_end`: ``end_kind`` precedence malformed > open > dated (declared before the seal, code check
    2026-10-23 ruling 1): ``malformed`` if ANY positive configuration is malformed (the market is NaN; ``mixed_malformed`` marks the markets that also
    hold an open-ended, sentinel or dated one, counted), else ``open`` if any is open-ended or a sentinel (it qualifies, 4), else ``dated`` with
    ``end_lo`` = the LATEST of their earliest instants;
    ``ends`` (CR9) = the distinct dated ends ``(end_lo, kind)`` as a JSON list; ``n_date_only`` / ``n_sentinel`` counts. A capture without the rows
    file gives an empty frame. Reads no price."""
    f = spec["feed"]
    p = Path(feed_dir) / "rows.jsonl.gz"
    if not p.exists():
        return pd.DataFrame(columns=["feeds", "band", "rmin", "rate", "n_pos", "end_kind", "end_lo", "ends", "n_date_only", "n_sentinel", "mixed_malformed"]).rename_axis("condition_id")
    acc: dict[str, dict] = {}
    with gzip.open(p, "rt") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            cid = r.get(f["id_field"])
            if not isinstance(cid, str) or not cid:
                continue
            a = acc.setdefault(cid, {"feeds": set(), "band": _num(r.get(f["band_field"])), "rmin": _num(r.get(f["min_field"])), "rate": 0.0, "n_pos": 0,
                                     "kinds": set(), "dated": set(), "n_date_only": 0, "n_sentinel": 0})
            a["feeds"].add(str(r.get("feed") or ""))
            cfgs = r.get(f["configs_field"])
            for c in cfgs if isinstance(cfgs, list) else []:
                if not isinstance(c, dict):
                    continue
                rate = _num(c.get(f["rate_field"]))
                if not (np.isfinite(rate) and rate > 0):
                    continue
                a["rate"] += rate
                a["n_pos"] += 1
                lo, _, kind = parse_end(c.get(f["end_field"]), int(f["sentinel_year"]))
                a["kinds"].add("open" if kind in ("open", "sentinel") else kind)
                a["n_date_only"] += int(kind == "date_only")
                a["n_sentinel"] += int(kind == "sentinel")
                if kind in ("ts", "date_only"):
                    a["dated"].add((float(lo), kind))
    rows = {}
    for cid, a in acc.items():
        kinds = a["kinds"]
        kind = "malformed" if "malformed" in kinds else ("open" if "open" in kinds else ("dated" if a["dated"] else "none"))
        lo = max(x for x, _ in a["dated"]) if kind == "dated" else float("nan")
        fs = a["feeds"] - {""}
        rows[cid] = {"feeds": "both" if len(fs) > 1 else (next(iter(fs)) if fs else ""), "band": a["band"], "rmin": a["rmin"], "rate": a["rate"], "n_pos": a["n_pos"],
                     "end_kind": kind, "end_lo": lo, "ends": json.dumps(sorted(a["dated"])), "n_date_only": a["n_date_only"], "n_sentinel": a["n_sentinel"],
                     "mixed_malformed": bool("malformed" in kinds and len(kinds) > 1)}
    out = pd.DataFrame.from_dict(rows, orient="index")
    out.index.name = "condition_id"
    return out


def scan_feed(feed_roots, only=None) -> dict[str, dict]:
    """Feed captures over several roots ({dir name: {"dir", "start", "finish", "state", "usable"}}); the first root holding a directory wins.
    ``usable`` = ``state == complete`` and the rows file present (1.2); a failed capture is listed (it is skipped, never used). ``only`` (the
    sealed feed directory names; code check 2026-10-23 note): only those manifests are read, a directory the seal does not name is never opened."""
    out: dict[str, dict] = {}
    for r in b._roots(feed_roots):
        if only is None:
            manifests = sorted(Path(r).glob("*/manifest.json")) if Path(r).exists() else []
        else:
            manifests = [Path(r) / d / "manifest.json" for d in sorted(only) if (Path(r) / d / "manifest.json").exists()]
        for p in manifests:
            d = p.parent.name
            if d in out or d.startswith("."):
                continue
            try:
                m = json.loads(p.read_text())
            except (OSError, ValueError):
                continue
            st, fin = m.get("started_utc"), m.get("finished_utc")
            try:
                t0, t1 = epoch(st), epoch(fin)
            except (TypeError, ValueError):
                continue
            out[d] = {"dir": p.parent, "start": t0, "finish": t1, "state": m.get("state"), "usable": bool(m.get("state") == "complete" and (p.parent / "rows.jsonl.gz").exists())}
    return out


def last_usable_before(feeds: dict[str, dict], t: float) -> str | None:
    """1.2's one feed clock: the latest USABLE feed capture whose manifest finish time is earlier than ``t`` (a capture's manifest start). A
    failed capture is skipped; none gives None (the flag is NaN)."""
    best, bt = None, -math.inf
    for d, v in feeds.items():
        if v["usable"] and v["finish"] < t and v["finish"] > bt:
            best, bt = d, v["finish"]
    return best


def feed_completeness(feeds: dict[str, dict], slots: list[int], spec: dict) -> dict:
    """Share of the span's slots holding a usable feed capture that STARTS inside the slot's 2 h (7: >= 90% or the feed-dependent gates are NaN)."""
    starts = np.array(sorted(v["start"] for v in feeds.values() if v["usable"]))
    hit = 0
    for k in slots:
        t0 = b.slot_time(k, spec)
        hit += int(bool(len(starts)) and bool(((starts >= t0) & (starts < t0 + b.GRID_S)).any()))
    share = hit / len(slots) if slots else float("nan")
    return {"slots": len(slots), "slots_with_usable_feed": hit, "share": share, "ok": bool(np.isfinite(share) and share >= spec["census_inputs"]["feed_completeness_min"])}


# --- readers (new LT9 code: LT8's loaders plus the serving-path fields of CH212) -----------------------------------------------------


def load_rows9(cap_dir: Path) -> pd.DataFrame:
    """Origin-side capture columns (LT3's plus Gamma ``liquidity``): one row per market_id and per condition_id (first in page order), the member
    count ``n_members`` (distinct markets of the Gamma event among the capture's binary, open and active rows; a market without ``event_id`` is its
    own event) and the event key ``ekey`` (LT8's member-cap counter, 1.4), and the raw presence of ``volume24hr`` / ``last_trade_price``."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(SNAP_COLS9),
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category", "end_date": "category",
                              "closed": str, "active": str, "neg_risk": str})
    for c in SNAP_COLS9:
        if c not in rows:
            rows[c] = np.nan
    rows = rows.drop_duplicates("market_id")
    cond = rows["condition_id"].fillna("")
    rows = rows[~(cond.ne("") & cond.duplicated()).to_numpy()].reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    ev = rows["event_id"].fillna("").astype(str).str.strip()
    ev = ev.where(~ev.str.casefold().isin(_NULL_LIKE), "")
    mid = rows["market_id"].astype(str)
    open_ = (rows["binary"] == 1).to_numpy() & ~b._truthy(rows["closed"]) & b._truthy(rows["active"])
    keyed = pd.DataFrame({"ev": ev.to_numpy(), "m": mid.to_numpy()})[open_ & (ev != "").to_numpy()]
    nm = keyed.groupby("ev")["m"].nunique()
    rows["n_members"] = np.where((ev == "").to_numpy(), 1.0, ev.map(nm).fillna(1.0).to_numpy(float))
    rows["ekey"] = np.where((ev == "").to_numpy(), "m:" + mid.to_numpy(), ev.to_numpy())
    rows["vol_present"] = np.isfinite(pd.to_numeric(rows["volume24hr"], errors="coerce").to_numpy(float)).astype(float)
    rows["ltp_present"] = np.isfinite(pd.to_numeric(rows["last_trade_price"], errors="coerce").to_numpy(float)).astype(float)
    return rows


def capture_last_receipt(cap_dir: Path) -> float:
    """A capture's last row receipt: the largest ``received_utc`` over its rows (1.3's decision clock for CH213 and CH212, and the clock CR9's decision
    capture is chosen by). Reads the timestamp column only; NaN when it is absent or empty."""
    r = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c == "received_utc", dtype=str)
    if "received_utc" not in r or r.empty:
        return float("nan")
    t = panel._epoch(r["received_utc"].astype(str))
    return float(np.nanmax(t)) if np.isfinite(t).any() else float("nan")


def decision_slot(cap_slots: list[int], lasts, t: float) -> int:
    """CR9's decision capture (1.3, "strictly earlier"; code check 2026-10-23 must-fix 2): the latest slot (``cap_slots`` ascending) whose capture's LAST
    row receipt is strictly before ``t``; ``-10**9`` when none. A capture in progress at ``t`` is never the decision capture."""
    idx = np.nonzero(np.asarray(lasts, float) < float(t))[0]
    return int(cap_slots[int(idx[-1])]) if len(idx) else -10**9


_NO_SWEEPS = "census reads no sweeps"
PRIOR_POPULATION_OVERLAPS = {  # CC9 and CR9 (section 7 descriptive: the overlaps with LT8 CH203 / LT7 CH197 on the same days; re-check 2026-10-23 item 5)
    "LT8_CH203": {"units": float("nan"), "reason": _NO_SWEEPS},
    "LT7_CH197": {"units": float("nan"), "reason": _NO_SWEEPS},
}
# CS9: CH203's quiet test reads capture k's quotes (mid_k), which CS9 reads for its manifest start only (section 7 loader), so its overlap is not computed
# (declared_before_seal.prior_population_overlaps); CH197 is computed with the vendored patient_units.
CS9_CH203_UNAVAILABLE = {"units": float("nan"), "reason": "LT8 CH203's units need capture k's quotes (mid_k and the quiet test |mid_k - smid_{k-1}|); CS9 reads capture k for its manifest start only (frozen text section 7 loader), so the overlap is not computed (declared deviation)"}


def prior_spec_view(spec: dict) -> dict:
    """The LT9 spec with LT7 CH197's (and LT8 CH203's) test blocks restated from ``prior_population_specs`` for the vendored ``patient_units`` / ``quiet_units``."""
    ps = spec["prior_population_specs"]
    tests = {**spec["tests"], "CH197": ps["LT7_CH197"]["test"], "CH203": ps["LT8_CH203"]["test"]}
    return {**spec, "tests": tests, "reward_rule": {**spec["reward_rule"], "ft_factor": ps["LT8_CH203"]["ft_factor"]}}


def day_keys(f: pd.DataFrame) -> pd.DataFrame:
    """(market, UTC day) keys from a unit frame with a ``slot`` (12 slots a day from the 00:31Z grid origin), for :func:`b.unit_overlaps`."""
    if f is None or not len(f):
        return pd.DataFrame({"market_id": [], "slot": []})
    return pd.DataFrame({"market_id": f["market_id"].astype(str).to_numpy(), "slot": (f["slot"].to_numpy(float) // 12).astype(int)}).drop_duplicates()


def load_ext9(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS9), dtype=str)
    has_clob = "clob_rewards" in ext.columns  # a sidecar WITHOUT the column says nothing about rewards: NaN, not unrewarded (LT8 check fix 7)
    for c in EXT_COLS9:
        if c not in ext:
            ext[c] = None
    out = ext.drop_duplicates("market_id").set_index("market_id")
    out.attrs["has_clob_rewards"] = has_clob
    return out


def series9_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, day: str, cap_start: float) -> pd.DataFrame:
    """LT3's series (vendored) plus Gamma ``liq``, ``n_members``, the event key, ``condition_id``, the reward fields of LT8's null taxonomy
    (``rew_rate`` / ``rew_state`` / ``rew_status`` in the LT7 vocabulary; ``rew_min``; ``rew_maxspread`` in cents as served), the raw ``fee_cat``,
    the pinned ``crypto7`` class, ``volume_num`` and CH212's serving-path fields (``page_norm`` = page index / the capture's largest, ``recv_off``
    = sidecar receipt minus the capture start, s; presence of ``volume24hr``, ``last_trade_price`` and ``competitive``)."""
    ser, _ = b.series_frame(rows, ext, spec)
    mids = pd.Index(ser["market_id"].astype(str))
    r = rows.set_index(rows["market_id"].astype(str))
    for col, src in (("liq", "liquidity"), ("n_members", "n_members"), ("vol_present", "vol_present"), ("ltp_present", "ltp_present")):
        ser[col] = pd.to_numeric(r[src], errors="coerce").reindex(mids).to_numpy(float)
    ser["event_id"] = r["ekey"].reindex(mids).to_numpy(object)
    ser["condition_id"] = r["condition_id"].reindex(mids).fillna("").astype(str).to_numpy(object)
    if ext is not None:
        e = ext.reindex(mids)
        present = np.asarray(mids.isin(ext.index))
        has_col = bool(ext.attrs.get("has_clob_rewards", True))
        st = [b.reward_detail(v, day) if (p and has_col) else (float("nan"), "no_sidecar" if not p else "no_column", "") for v, p in zip(e["clob_rewards"], present, strict=True)]
        ser["rew_rate"] = [x[0] for x in st]
        ser["rew_state"] = [x[1] for x in st]
        ser["rew_status"] = b.lt7_status(ser["rew_state"])
        ser["rew_reason"] = [x[2] for x in st]
        ser["rew_min"] = pd.to_numeric(e["rewards_min_size"], errors="coerce").to_numpy(float)
        ser["rew_maxspread"] = pd.to_numeric(e["rewards_max_spread"], errors="coerce").to_numpy(float)
        ser["vnum"] = pd.to_numeric(e["volume_num"], errors="coerce").to_numpy(float)
        pg = pd.to_numeric(ext["page_index"], errors="coerce")
        pmax = float(pg.max()) if pg.notna().any() else float("nan")
        ser["page_norm"] = pd.to_numeric(e["page_index"], errors="coerce").to_numpy(float) / pmax if pmax and np.isfinite(pmax) and pmax > 0 else np.nan
        ser["recv_off"] = panel._epoch(e["received_utc"].astype(str)) - float(cap_start)
        comp = e["competitive"].astype(str).str.strip().str.casefold()
        ser["comp_present"] = np.where(present, (~comp.isin(_NULL_LIKE)).to_numpy(float), np.nan)
        fc = e["fee_category"].where(e["fee_category"].notna(), None).tolist()
    else:
        present = np.zeros(len(mids), bool)
        ser["rew_rate"], ser["rew_state"], ser["rew_reason"], ser["rew_min"], ser["rew_maxspread"] = np.nan, "no_sidecar", "", np.nan, np.nan
        ser["rew_status"] = "absent"
        ser["vnum"], ser["page_norm"], ser["recv_off"], ser["comp_present"] = np.nan, np.nan, np.nan, np.nan
        fc = [None] * len(mids)
    sp = ser["sports"].to_numpy(int)
    ser["fee_cat"] = pd.Series(fc, dtype=object).to_numpy()
    ser["crypto7"] = [b.crypto_class(f, bool(p), int(s)) for f, p, s in zip(fc, present, sp, strict=True)]
    return ser


def write_series9(work: Path, cap: dict, spec: dict) -> None:
    """Write-once ``series/<id>.csv.gz`` (two-sided quotes) and ``rw/<id>.csv.gz`` (LT8's :func:`rw_frame` of EVERY sidecar row, the carry's input)."""
    p = Path(work) / "series" / f"{cap['id']}.csv.gz"
    if p.exists():
        return
    rows = load_rows9(cap["dir"])
    ext = load_ext9(cap["dir"])
    day = b._utc_day(cap["start"])
    b.write_once_csv(p, series9_frame(rows, ext, spec, day, cap["start"]))
    b.write_once_csv(Path(work) / "rw" / f"{cap['id']}.csv.gz", b.rw_frame(ext, day))


def read_series9(work: Path, cap_id: str) -> pd.DataFrame | None:
    ser = b.read_series(work, cap_id)
    if ser is None:
        return None
    ser["condition_id"] = ser["condition_id"].fillna("").astype(str) if "condition_id" in ser else ""
    return ser


# --- the lag-slot loaders (design 7; unit tested: a later slot's prices never reach census code) ------------------------------------


def lag_break_flag(cap_a: Path, cap_b: Path, v_price: pd.Series) -> pd.Series:
    """CH213's twin (design 2, 7): ``1[s_a < 2v and s_b >= 2v]`` for the markets of ``v_price`` (index market_id, the band in price units),
    from captures k + 4 (``cap_a``) and k + 5 (``cap_b``), read with ``usecols`` = market_id, best_bid, best_ask; the spread is formed and
    compared INSIDE this function and only the flag (0 / 1 / NaN when either capture is not two-sided for the market) is returned."""
    def sp(d: Path) -> pd.Series:
        r = pd.read_csv(forecast.require_local(Path(d) / "rows.csv.gz"), usecols=list(LAG_CAPTURE_COLUMNS), dtype={"market_id": str}).drop_duplicates("market_id").set_index("market_id")
        bid, ask = pd.to_numeric(r["best_bid"], errors="coerce"), pd.to_numeric(r["best_ask"], errors="coerce")
        two = (bid > 0) & (ask > bid) & (ask <= 1)
        return ((ask - bid) * 100.0).where(two)
    sa, sb = sp(cap_a).reindex(v_price.index), sp(cap_b).reindex(v_price.index)
    v2 = 2.0 * v_price.astype(float) * 100.0
    ok = sa.notna() & sb.notna() & v2.notna()
    flag = ((sa < v2 - _EPS_C) & (sb >= v2 - _EPS_C)).astype(float)
    return flag.where(ok, np.nan).rename("break_twin")


def lag_twin_flags(cap_a: Path, cap_b: Path, grp: pd.DataFrame, cells_b: dict | None, spec: dict) -> pd.Series:
    """CH213's twin flag for ONE origin's units (design 2, 7; code check 2026-10-23 must-fix 3). The twin break is ``1[s_{k+4} < 2v and s_{k+5} >= 2v]``
    against "the same ``v``" for a reward unit and against ``v_ctrl`` OF CAPTURE k + 5's CELL for a control unit: ``cells_b`` is
    :func:`control_cells` of capture k + 5 (cell medians and counts of ``rewards_max_spread``, no price), the unit's own (category, tier, tick) key
    comes from its decision-time fields, and the band is assigned here by :func:`assign_control_band` (cell, else (tier, tick), else NaN). The spread
    comparison happens inside :func:`lag_break_flag`; only the flag leaves (aligned to ``grp.index``)."""
    mk = grp["market_id"].astype(str).to_numpy()
    if cells_b is None:
        v_ctrl = np.full(len(grp), np.nan)
    else:
        v_ctrl, _ = assign_control_band(cat_key(grp["fee_cat"]), tier_of(grp["liq"]), tick_key(grp["tick"]), cells_b, int(spec["tests"]["CH213"]["cell_min_units"]))
    v = np.where(grp["rew"].to_numpy(float) == 1.0, grp["v_c"].to_numpy(float), v_ctrl) / 100.0
    vp = pd.Series(v, index=mk)
    vp = vp[~vp.index.duplicated()]
    fl = lag_break_flag(cap_a, cap_b, vp)
    return pd.Series(fl.reindex(mk).to_numpy(float), index=grp.index)


def lag_band_sums(sweep_dir: Path, cap_dir: Path) -> pd.DataFrame:
    """CH214's twin input (design 3, 7): a later pass's sweep 1 on the outcome-0 token, indexed by market_id, with ONLY the four 1c / 5c depths.
    The sweep is read with ``usecols`` = keys + the four depths, the same pass's capture with ``usecols`` = market_id + clob_token_id_0. No best bid
    or ask, touch size, receipt or other column of a later slot reaches census code."""
    tok = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=list(LAG_CAPTURE_KEY_COLUMNS), dtype=str).drop_duplicates("market_id")
    sw = pd.read_csv(Path(sweep_dir) / "rows.csv.gz", usecols=lambda c: c in {*LAG_SWEEP_KEYS, *LAG_SWEEP_COLUMNS}, dtype={"token_id": str, "market_id": str})
    for c in LAG_SWEEP_COLUMNS:
        if c not in sw:
            sw[c] = np.nan
    sw = sw.merge(tok, on="market_id", how="inner")
    sw = sw[sw["token_id"] == sw["clob_token_id_0"]].drop_duplicates("market_id").set_index("market_id")
    return sw[list(LAG_SWEEP_COLUMNS)].apply(pd.to_numeric, errors="coerce")


# --- shared unit machinery ----------------------------------------------------------------------------------------------------------


def tier_of(liq) -> np.ndarray:
    """Liquidity tier of 2 (the cost model's cuts): ``<1k``, ``1k-10k``, ``10k-100k``, ``>=100k``; NaN liquidity gives ``unknown``."""
    v = np.asarray(liq, float)
    out = np.full(len(v), "unknown", dtype=object)
    ok = np.isfinite(v)
    out[ok & (v < 1e3)] = "<1k"
    out[ok & (v >= 1e3) & (v < 1e4)] = "1k-10k"
    out[ok & (v >= 1e4) & (v < 1e5)] = "10k-100k"
    out[ok & (v >= 1e5)] = ">=100k"
    return out


def tick_key(tick) -> np.ndarray:
    v = np.asarray(tick, float)
    return np.where(np.abs(v - 0.001) < 1e-9, "0.001", np.where(np.abs(v - 0.01) < 1e-9, "0.01", np.where(np.isfinite(v), "other", "unknown"))).astype(object)


def cat_key(fee_cat) -> np.ndarray:
    return np.array([b._norm_cat(v) or "unknown" for v in fee_cat], dtype=object)


def rewarded_of(ser_c: pd.DataFrame) -> np.ndarray:
    """``rewarded`` under ``listed_carry24h_v2`` of a carried frame (``RewardCarry.apply``): 1 when the (carried) rate is > 0, 0 when null without a
    positive listing in the window or listed-inactive, NaN when the status is malformed, absent (no sidecar row) or ``no_column``."""
    st = b._status_array(ser_c)
    rate = ser_c["rew_rate"].to_numpy(float)
    unk = np.isin(st, ["malformed", "absent", "no_column"]) | ~np.isfinite(rate)
    return np.where(unk, np.nan, (rate > 0).astype(float))


def carry_frame(carry: b.RewardCarry, ser: pd.DataFrame, k: int, day: str) -> pd.DataFrame:
    """The carry at slot ``k`` (slots [k - 11, k - 1] only) plus ``rewarded``, ``carry_lag`` (0 when listed with a positive rate at k, j - source slot
    when carried, NaN otherwise) and ``om`` (``1[carry_lag >= 1]`` among rewarded rows; 0 for listed rewarded rows; NaN when not rewarded)."""
    c = carry.apply(ser, k, day)
    rew = rewarded_of(c)
    lag = c["rew_carry_lag"].to_numpy(float)
    c["rewarded"] = rew
    c["carry_lag"] = np.where(rew == 1.0, np.where(np.isfinite(lag), lag, 0.0), np.nan)
    c["om"] = np.where(rew == 1.0, (np.where(np.isfinite(lag), lag, 0.0) >= 1).astype(float), np.nan)
    return c


def _rv(store, k: int, mk, tick, c: dict):
    return b._rv24(store, k, mk, tick, c)


def _slot_dummies(u: pd.DataFrame, slot_of_day: int) -> None:
    for s in range(1, 12):
        u[f"sd{s}"] = float(slot_of_day == s)


def _eligible_single(ser: pd.DataFrame, spec: dict, lo: float, hi: float, margin_h: float, t_dec: float | None = None) -> np.ndarray:
    """1.4 at ONE capture (the CH213 cell rows and CR9's decision capture): two-sided and tight, mid in [lo, hi], end unknown or > t + margin."""
    bid, ask = ser["bid"].to_numpy(float), ser["ask"].to_numpy(float)
    ok = b.tight_arr(bid, ask, ser["spread"].to_numpy(float), spec["eligibility"]["spread_max"])
    mid = (bid + ask) / 2.0
    end = ser["end_ts"].to_numpy(float)
    t = ser["t_row"].to_numpy(float) if t_dec is None else np.full(len(ser), float(t_dec))
    with np.errstate(invalid="ignore"):
        return ok & (mid >= lo - 1e-12) & (mid <= hi + 1e-12) & (np.isnan(end) | (end > t + margin_h * 3600.0))


def _cat_ok(ser: pd.DataFrame) -> np.ndarray:
    return (ser["sports"].to_numpy(int) == 0) & (np.asarray(ser["crypto7"].astype(str)) == "non_crypto")


# --- CH213 the band break (design 2) ------------------------------------------------------------------------------------------------


def control_cells(ser_c: pd.DataFrame, spec: dict) -> dict:
    """The cell rule of CH213's control band (design 2, re-check fix 6): from capture k ONLY, the cell rows are every carry-rewarded
    (``rewarded_k = 1``) non-sports ex-crypto row eligible under 1.4 at capture k (two-sided, tight, mid in [0.10, 0.90], end unknown or > t + 7 h) with
    a finite ``v``, regardless of ``panel_m`` and of the other unit filters. Returns {"cell": {(cat, tier, tick): (n, median v)}, "tt": {(tier, tick):
    (n, median v)}}."""
    c = spec["tests"]["CH213"]
    rew = ser_c["rewarded"].to_numpy(float) if "rewarded" in ser_c else rewarded_of(ser_c)
    v = ser_c["rew_maxspread"].to_numpy(float)
    ok = _eligible_single(ser_c, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"]) & _cat_ok(ser_c) & (rew == 1.0) & np.isfinite(v)
    d = pd.DataFrame({"cat": cat_key(ser_c["fee_cat"]), "tier": tier_of(ser_c["liq"]), "tick": tick_key(ser_c["tick"]), "v": v})[ok]
    cell = {k_: (int(len(g)), float(g["v"].median())) for k_, g in d.groupby(["cat", "tier", "tick"])}
    tt = {k_: (int(len(g)), float(g["v"].median())) for k_, g in d.groupby(["tier", "tick"])}
    return {"cell": cell, "tt": tt, "rows": int(ok.sum())}


def assign_control_band(cat, tier, tick, cells: dict, min_n: int) -> tuple[np.ndarray, np.ndarray]:
    """(v_ctrl in cents, level): the (cat, tier, tick) cell median if the cell holds >= ``min_n`` reward rows, else the (tier, tick) median if
    >= ``min_n``, else NaN (``ctrl_band_uncovered``). ``level``: 2 cell, 1 fallback, 0 uncovered."""
    n = len(cat)
    out, lev = np.full(n, np.nan), np.zeros(n, int)
    for i in range(n):
        a = cells["cell"].get((cat[i], tier[i], tick[i]))
        if a is not None and a[0] >= min_n:
            out[i], lev[i] = a[1], 2
            continue
        a = cells["tt"].get((tier[i], tick[i]))
        if a is not None and a[0] >= min_n:
            out[i], lev[i] = a[1], 1
    return out, lev


def break_flag(s_prev_c, s_k_c, v_c) -> np.ndarray:
    """The strict break (design 2) in cents: ``1[s_{k-1} < 2v and s_k >= 2v]`` (tolerance 1e-9 c: ``s_k`` exactly ``2v`` is a break, ``s_{k-1}``
    exactly ``2v`` is not); NaN where an input is missing."""
    sp, sk, v = (np.asarray(x, float) for x in (s_prev_c, s_k_c, v_c))
    with np.errstate(invalid="ignore"):
        f = ((sp < 2.0 * v - _EPS_C) & (sk >= 2.0 * v - _EPS_C)).astype(float)
    return np.where(np.isfinite(sp) & np.isfinite(sk) & np.isfinite(v), f, np.nan)


def bandbreak_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: b.MidStore, cap: dict, k: int, spec: dict, cells: dict) -> tuple[pd.DataFrame, dict]:
    """CH213's CANDIDATE units of capture k (design 2), before the market's panel is fixed (:func:`fix_panels`). ``ser_k`` / ``ser_p`` are the
    carried frames of captures k and k - 1 (:func:`carry_frame`). 1.4 at k - 1 and k, mid_k in [0.10, 0.90], non-sports ex-crypto, sidecar rows
    present at k - 1 and k with a finite reward status, end unknown or > t + 7 h with t = capture k's LAST row receipt (the decision, 1.3). Reward
    status ``rew`` = ``rewarded_k``: a rewarded unit takes the source's ``v`` and needs the same ``v`` at k - 1 under the carry (else ``band_changed``);
    an unrewarded unit takes ``v_ctrl(k)`` from :func:`control_cells` (else ``ctrl_band_uncovered``). No slot after k is read."""
    c = spec["tests"]["CH213"]
    t_dec = float(np.nanmax(ser_k["t_row"].to_numpy(float))) if len(ser_k) else float("nan")
    j, cnt = b._movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = b._non_sports_ex_crypto(j.copy(), cnt)
    mk = j["market_id"].astype(str)
    pj = ser_p.reindex(mk)
    rew = j["rewarded"].to_numpy(float)
    st_p = b._status_array(pj)
    rew_p = pj["rewarded"].to_numpy(float)
    # the finite-status gate (7, pre-exclusion): eligible non-sports ex-crypto rows in band, PLUS the rows whose sidecar is missing (category unknown,
    # status NaN), so that a missing sidecar can only lower the share (census convention)
    cnt["eligible_in_band"] = len(j) + int(cnt.get("sports_unknown", 0))
    cnt["eligible_in_band_status_finite"] = int(np.isfinite(rew).sum())
    with np.errstate(invalid="ignore"):
        end_ok = np.isnan(j["end_ts"].to_numpy(float)) | (j["end_ts"].to_numpy(float) > t_dec + c["end_margin_h"] * 3600.0)
    side_p = st_p != "absent"
    keep = end_ok & side_p & np.isfinite(rew) & np.isfinite(rew_p)
    cnt["end_date_decision"] = int((~end_ok).sum())
    cnt["sidecar_missing"] = int((end_ok & ~side_p).sum()) + int(cnt.get("sports_unknown", 0))
    cnt["reward_unparseable"] = int((end_ok & side_p & ~np.isfinite(rew)).sum())
    cnt["reward_unparseable_km1"] = int((end_ok & side_p & np.isfinite(rew) & ~np.isfinite(rew_p)).sum())
    j = j[keep].reset_index(drop=True)
    rew, rew_p = rew[keep], rew_p[keep]
    if j.empty:
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    v = j["rew_maxspread"].to_numpy(float)
    v_p = ser_p["rew_maxspread"].reindex(mk).to_numpy(float)
    with np.errstate(invalid="ignore"):
        same_v = (rew_p == 1.0) & np.isfinite(v) & np.isfinite(v_p) & (np.abs(v - v_p) <= 1e-9)
    v_ctrl, lev = assign_control_band(cat_key(j["fee_cat"]), tier_of(j["liq"]), tick_key(j["tick"]), cells, int(c["cell_min_units"]))
    is_r, is_c = rew == 1.0, rew == 0.0
    cnt["reward_candidates"], cnt["control_candidates"] = int(is_r.sum()), int(is_c.sum())
    cnt["band_changed"] = int((is_r & ~same_v).sum())
    cnt["ctrl_band_uncovered"] = int((is_c & ~np.isfinite(v_ctrl)).sum())
    cnt["ctrl_band_cell"], cnt["ctrl_band_fallback"] = int((is_c & (lev == 2)).sum()), int((is_c & (lev == 1)).sum())
    ok = (is_r & same_v) | (is_c & np.isfinite(v_ctrl))
    vv = np.where(is_r, v, v_ctrl)
    j, rew, vv = j[ok].reset_index(drop=True), rew[ok], vv[ok]
    if j.empty:
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    s_k = (j["ask"] - j["bid"]).to_numpy(float) * 100.0
    s_p = (j["ask_p"] - j["bid_p"]).to_numpy(float) * 100.0
    brk = break_flag(s_p, s_k, vv)
    with np.errstate(invalid="ignore"):
        inb = ((s_p <= vv + _EPS_C) & (s_k > vv + _EPS_C)).astype(float)
        one_sided = ((np.abs(j["bid"] - j["bid_p"]).to_numpy(float) > 1e-12) ^ (np.abs(j["ask"] - j["ask_p"]).to_numpy(float) > 1e-12)).astype(float)
    mid, mid_p = j["mid"].to_numpy(float), j["mid_p"].to_numpy(float)
    om = np.where(rew == 1.0, j["om"].to_numpy(float), 0.0)
    m12 = b._mid12(store, k, mk)
    d24, d24f = b._own24(1.0, mid, m12)
    tick = j["tick"].to_numpy(float)
    rv, rvs, rvf = _rv(store, k, mk.to_numpy(), tick, c)
    end = j["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        f_ok = (np.isnan(end) | (end > t_dec + c["f_end_margin_h"] * 3600.0)).astype(float)
    u = pd.DataFrame({**b._base_out(j, cap, k), "t_row": np.full(len(j), t_dec), "t_unit": j["t_row"].to_numpy(float), "mid": mid, "tick": tick,
                      "liq": j["liq"].to_numpy(float), "end_ts": end, "n_members": j["n_members"].to_numpy(float), "rew": rew, "v_c": vv,
                      "s_k_c": s_k, "s_p_c": s_p, "brk": brk, "inb_flip": inb, "om": om, "x_k": s_k / (2.0 * vv), "x_p": s_p / (2.0 * vv),
                      "log_s": np.log(np.where(s_k > 0, s_k, np.nan)), "d2h": mid - mid_p, "abs_d2h": np.abs(mid - mid_p), "one_sided": one_sided,
                      "d24": d24, "d24_flag": d24f, "rv24": rv, "rv24s": rvs, "rv_floor": rvf, "f_ok": f_ok, "carry_lag": j["carry_lag"].to_numpy(float),
                      "rate": j["rew_rate"].to_numpy(float), "fee_cat": j["fee_cat"].to_numpy(object), "condition_id": j["condition_id"].astype(str).to_numpy(object),
                      "cell_level": np.where(rew == 1.0, -1, 0)})
    u = b._common_cols(u)
    u["log_rv24s"] = np.log(u["rv24s"])
    _slot_dummies(u, k % 12)
    u = b._drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "tick": "tick_unknown", "log_s": "spread_nonpositive", "brk": "break_undefined"})
    cnt["candidates"] = len(u)
    return u, cnt


def fix_panels(U: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """R1 fix 2 and re-check fix 6: each market's panel is ``rew`` at its FIRST candidate unit (the first origin at which it passed every other
    filter, the band filter of the status it held there included: a ``band_changed`` or ``ctrl_band_uncovered`` origin is never a candidate). Later
    units whose ``rew`` differs are excluded (``panel_switched``). Then ``relpos_k = log s_k - mean(log s)`` over the market's STRICTLY EARLIER kept
    units (NaN at its first), and the interaction columns."""
    if U.empty:
        return U, {"panel_switched": 0}
    U = U.sort_values(["market_id", "slot"], kind="mergesort").reset_index(drop=True)
    panel_m = U.groupby("market_id")["rew"].transform("first").to_numpy(float)
    sw = U["rew"].to_numpy(float) != panel_m
    cnt = {"panel_switched": int(sw.sum()), "panel_switched_reward": int((sw & (panel_m == 1)).sum()), "panel_switched_control": int((sw & (panel_m == 0)).sum())}
    U = U[~sw].reset_index(drop=True)
    U["panel"] = U["rew"]
    g = U.groupby("market_id")["log_s"]
    prior_sum = g.cumsum() - U["log_s"]
    prior_n = g.cumcount()
    U["relpos"] = np.where(prior_n.to_numpy() > 0, U["log_s"].to_numpy() - prior_sum.to_numpy() / np.maximum(prior_n.to_numpy(), 1), np.nan)
    return U, cnt


def cap_then_panel(A: pd.DataFrame, cap_n: int) -> tuple[pd.DataFrame, dict]:
    """The member cap is one of section 2's unit filters, so it is applied BEFORE the panel is fixed and ``relpos`` formed (a ladder-arm origin, n_members
    > 10, is never a market's first unit). Returns the capped units after :func:`fix_panels` and the counts (with ``cap_share_reward``, the share of
    reward-status candidates within the cap, the census's cap-share input)."""
    cnt: dict = {}
    if len(A):
        rc = A[A["rew"] == 1]
        cnt["cap_share_reward"] = float((rc["n_members"] <= cap_n).mean()) if len(rc) else float("nan")
        cnt["ladder_arm_candidates"] = int((A["n_members"] > cap_n).sum())
        A = A[A["n_members"] <= cap_n].reset_index(drop=True)
    A, pc = fix_panels(A)
    return A, {**cnt, **pc}


def ch213_terms(pop: pd.DataFrame) -> pd.DataFrame:
    """The design matrix columns of section 2 (``rew`` constant within market is NOT a regressor; it is removed by the demeaning)."""
    p = pop.copy()
    zl = b._z(p["log1p_liq"], *b.standardise(p["log1p_liq"]))
    zs = b._z(p["log_s"], *b.standardise(p["log_s"]))
    p["z_liq"] = zl
    p["break_rew"] = p["brk"] * p["panel"]
    p["break_zliq"], p["break_tick"], p["break_zlogs"] = p["brk"] * zl, p["brk"] * p["tick001"], p["brk"] * zs
    p["break_relpos"], p["break_om"] = p["brk"] * p["relpos"], p["brk"] * p["om"]
    if "brk_twin" in p:
        p["twin_rew"] = p["brk_twin"] * p["panel"]
    return p


CONTROLS_213 = ["brk", "break_zliq", "break_tick", "break_zlogs", "break_relpos", "x_p", "x_k", "log_s", "logit_mid", "abs_dev", "log1p_liq", "d2h", "abs_d2h", "d24",
                "d24_flag", "log_rv24s", "rv_floor", "tick001", "one_sided", "om", "break_om", "log_hte", "hte_unknown", *(f"sd{s}" for s in range(1, 12))]


def mde_ch213_declared(nrb: float, nrn: float, ncb: float, ncn: float, sd: float, de: float, a: dict, vif: float) -> float:
    """Section 2's interaction formula at the census's projected effective cell counts: ``3.47 x SD x sqrt(1/n_rb + 1/n_rn + 1/n_cb + 1/n_cn) x
    sqrt(DE_gate) x 1.5 x sqrt(max(1, VIF_w))`` (price units)."""
    if not (min(nrb, nrn, ncb, ncn) > 0 and np.isfinite(de) and np.isfinite(vif)):
        return float("inf")
    return a["t_sum"] * sd * math.sqrt(1 / nrb + 1 / nrn + 1 / ncb + 1 / ncn) * math.sqrt(de) * a["day_factor"] * math.sqrt(max(vif, 1.0))


def f_mde_gate(mde_c: float, r_gate: float, design_c: float) -> dict:
    """7's F-MDE: ``max(design-based MDE of Delta in the arm model, MDE x sqrt(2 / (1 - max(0, r_gate))))`` (cents); NaN anywhere gives inf."""
    if not (np.isfinite(mde_c) and np.isfinite(r_gate) and r_gate < 1.0):
        return {"declared_c": float("inf"), "design_c": design_c, "f_mde_c": float("inf"), "r_gate": r_gate}
    dec = mde_c * math.sqrt(2.0 / (1.0 - max(0.0, r_gate)))
    return {"declared_c": dec, "design_c": design_c, "f_mde_c": float(max(dec, design_c)) if np.isfinite(design_c) else float("inf"), "r_gate": r_gate}


def _scale(days: float) -> float:
    return 21.0 / days if days and np.isfinite(days) else float("nan")


def band_unit_check(v_cents, spec: dict) -> dict:
    """7's band unit check: the median ``rewards_max_spread`` over carry-rewarded rows must lie in [0.5, 20] (cents), else every gate that uses v is NaN."""
    v = np.asarray(v_cents, float)
    v = v[np.isfinite(v)]
    med = float(np.median(v)) if len(v) else float("nan")
    lo, hi = spec["census_inputs"]["band_unit_check_cents"]
    return {"median_v_cents": med, "rows": int(len(v)), "ok": bool(np.isfinite(med) and lo <= med <= hi)}


def _nan_gates(res: dict, key: str, why: str) -> dict:
    g = res.get(key, {})
    res[key] = {**{k_: False for k_ in g if k_ != "pass"}, why: False, "pass": False, "values_nan": True}
    return res


def census_ch213(U: pd.DataFrame, tot: dict, spec: dict, covered_days: float, band: dict, pair_days: float) -> dict:
    """CH213's census gate (design 7 table, CC9). ``U`` = the units after the member cap and :func:`fix_panels` (the cap is one of section 2's unit
    filters, so it comes BEFORE the panel and ``relpos``); ``tot["cap_share_reward"]`` = the share of reward-status candidates with n_members <= 10."""
    g, a = spec["census_gates"]["CC9_CH213"], b.mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CC9_CH213"]
    scale = _scale(covered_days)
    if U.empty:
        return b._gate_min_days({"error": "no units", "gate_CH213": {"pass": False}}, "gate_CH213", covered_days, mind)
    cap_n = spec["member_cap"]["max_members"]
    elig, fin = tot.get("eligible_in_band", 0), tot.get("eligible_in_band_status_finite", 0)
    finite_share = fin / elig if elig else float("nan")
    cap_share = float(tot.get("cap_share_reward", float("nan")))
    P = U[U["n_members"] <= cap_n]
    pop, excl, top = b._fam(P, a["family_cap"])
    pop = ch213_terms(pop)
    R, C = pop[pop["panel"] == 1], pop[pop["panel"] == 0]
    Rp, Cp = P[P["panel"] == 1], P[P["panel"] == 0]  # count gates: gross counts after every filter, before the census-fixed family exclusion (LT8's practice)
    proj_r, proj_c = float(len(Rp) * scale), float(len(Cp) * scale)
    proj_rb, proj_cb = float(Rp["brk"].sum() * scale), float(Cp["brk"].sum() * scale)
    cc, cu = tot.get("control_candidates", 0), tot.get("ctrl_band_uncovered", 0)
    ctrl_cov = (cc - cu) / cc if cc else float("nan")
    rb_slots = Rp.loc[Rp["brk"] == 1, "slot"] % 12
    venue_top = float(rb_slots.value_counts(normalize=True).iloc[0]) if len(rb_slots) else float("nan")
    de = b._de(pop, scale, g["de_floor"], a)
    eff = b._eff(pop)
    pe = pop[eff]
    cells = {nm: float(((pe["panel"] == p_) & (pe["brk"] == br)).sum()) * scale for nm, p_, br in (("n_rb", 1, 1), ("n_rn", 1, 0), ("n_cb", 0, 1), ("n_cn", 0, 0))}
    dsg = b.design_ss(pe, "break_rew", CONTROLS_213)
    vif = dsg["vif_w"]
    sd = a[g["sd"]]
    declared = mde_ch213_declared(cells["n_rb"], cells["n_rn"], cells["n_cb"], cells["n_cn"], sd, de["DE_gate"], a, vif) * 100.0
    se = b.design_se(pe, ["break_rew"], CONTROLS_213, {"break_rew": 1.0}, float(a["de_rho"]), scale)
    design = a["t_sum"] * a["day_factor"] * sd * se * 100.0 if np.isfinite(se) else float("inf")
    mde_c = float(max(declared, design)) if np.isfinite(declared) else float("inf")
    corr_liq = b.wcorr(pop, "break_rew", "z_liq")
    corr_om = b.wcorr(pop, "break_rew", "om")
    bm = b.block_min_units(covered_days)
    bs = b.block_share(pop, bm)
    F = pop[(pop["f_ok"] == 1) & np.isfinite(pop["brk_twin"].to_numpy(float))] if "brk_twin" in pop else pop.iloc[0:0]
    arm_share = len(F) / len(pop) if len(pop) else float("nan")
    pr = pd.DataFrame({"market_id": F["market_id"].to_numpy(), "t_row": F["t_row"].to_numpy(float), "imb_j": F["break_rew"].to_numpy(float), "imb_j13": F["twin_rew"].to_numpy(float)}) if len(F) else pd.DataFrame()
    pc = b.pair_correlations(pr, int(g["pair_min_per_market"]))
    scale_f = _scale(pair_days)
    se_f = b.design_se(F[b._eff(F)], ["break_rew", "twin_rew"], [*CONTROLS_213, "brk_twin"], {"break_rew": 1.0, "twin_rew": -1.0}, float(a["de_rho"]), scale_f) if len(F) else float("nan")
    fm = f_mde_gate(mde_c, pc["r_gate"], a["t_sum"] * a["day_factor"] * sd * se_f * 100.0 if np.isfinite(se_f) else float("inf"))
    relpos_b = pop.loc[pop["brk"] == 1, "relpos"]
    res = {"eligible_in_band": elig, "finite_status_share": finite_share, "band_unit_check": band, "units_reward_panel": int(len(R)), "units_control_panel": int(len(C)),
           "projected_reward_units_21d": proj_r, "projected_control_units_21d": proj_c, "projected_reward_breaks_21d": proj_rb, "projected_control_breaks_21d": proj_cb,
           "reward_breaks_per_capture": proj_rb / 252.0, "control_breaks_per_capture": proj_cb / 252.0, "control_band_coverage": ctrl_cov, "cap_share_reward_panel": cap_share,
           "venue_clock_top_share": venue_top, "exclude_family": excl, "top_family_share": top, "design_effect": de, "cells_effective_projected": cells,
           "vif_w": vif, "design_ss": dsg, "mde": {"declared_c": declared, "design_c": design, "se_1": se, "mde_c": mde_c}, "F": fm, "F_arm_share": arm_share, "pairs": pc, "pair_days": pair_days,
           "corr_liq": corr_liq, "corr_om": corr_om, "block_min_units": bm, "block_share": bs, "events": b._events8(pop, scale, covered_days),
           "panel_switched": {k_: tot.get(k_, 0) for k_ in ("panel_switched", "panel_switched_reward", "panel_switched_control")},
           "s_over_2v_quantiles": {"reward": b._q(R["x_k"], (0.1, 0.25, 0.5, 0.75, 0.9)), "control": b._q(C["x_k"], (0.1, 0.25, 0.5, 0.75, 0.9))},
           "inb_flip_per_capture": {"reward": float(R["inb_flip"].sum() * scale / 252.0), "control": float(C["inb_flip"].sum() * scale / 252.0)},
           "relpos_at_breaks_pooled": b._q(relpos_b, (0.1, 0.5, 0.9)), "broken_rate_quantiles_reward": b._q(R.loc[R["brk"] == 1, "rate"]),
           "control_cell_levels": {k_: tot.get(k_, 0) for k_ in ("ctrl_band_cell", "ctrl_band_fallback", "ctrl_band_uncovered")},
           "splits": b._desc_splits(tot), "per_market": b._per_market(pop["market_id"]), "t_sum_used": a["t_sum"],
           "n_members_dist": {str(int(v_)): int(n_) for v_, n_ in U["n_members"].clip(upper=11).value_counts().sort_index().items()},
           "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    if "persist_pooled" in tot:
        res["broken_at_km1_given_km2_pooled"] = tot["persist_pooled"]
    gate = {"finite_status": bool(np.isfinite(finite_share) and finite_share >= g["finite_status_min"]), "band_unit": bool(band["ok"]),
            "reward_units": proj_r >= g["units_projected_min"], "control_units": proj_c >= g["units_projected_min"],
            "control_band_coverage": bool(np.isfinite(ctrl_cov) and ctrl_cov >= g["control_band_coverage_min"]),
            "reward_breaks": proj_rb >= g["breaks_projected_min"], "control_breaks": proj_cb >= g["breaks_projected_min"],
            "cap_share": bool(np.isfinite(cap_share) and cap_share >= g["cap_share_min"]), "venue_clock": bool(np.isfinite(venue_top) and venue_top <= g["venue_clock_max"]),
            "corr_liq": b.corr_ok(corr_liq, g["corr_max"], both=True), "corr_om": b.corr_ok(corr_om, g["corr_max"]),
            "vif_w": bool(np.isfinite(vif) and vif <= g["vif_w_max"]), "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]),
            "mde": bool(mde_c <= a["mde_max"] * 100.0), "f_arm": bool(np.isfinite(arm_share) and arm_share >= g["f_arm_min_share"]),
            "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max"] * 100.0)}
    res["gate_CH213"] = b._gate(gate)
    if not band["ok"]:
        res = _nan_gates(res, "gate_CH213", "band_unit")
    return b._gate_min_days(res, "gate_CH213", covered_days, mind)


# --- CH212 the omission (design 4) --------------------------------------------------------------------------------------------------


def feed_flags(cond: pd.Series, feed_k: pd.DataFrame | None, feed_prev: pd.DataFrame | None) -> dict:
    """``clob_listed_k`` (the market's condition_id in the last usable feed capture before capture k's start; NaN without one), ``clob_dropped_k``
    (listed in the last usable capture before capture k - 1's start and absent from the one before capture k's start; NaN if either is missing)."""
    c = cond.astype(str).to_numpy()
    lk = np.full(len(c), np.nan) if feed_k is None else np.isin(c, feed_k.index.to_numpy()).astype(float)
    lp = np.full(len(c), np.nan) if feed_prev is None else np.isin(c, feed_prev.index.to_numpy()).astype(float)
    with np.errstate(invalid="ignore"):
        dropped = np.where(np.isfinite(lk) & np.isfinite(lp), ((lp == 1) & (lk == 0)).astype(float), np.nan)
    return {"clob_listed": lk, "clob_listed_prev": lp, "clob_dropped": dropped}


def feed_end_ok(cond: pd.Series, feed_k: pd.DataFrame | None, k: int, spec: dict) -> tuple[np.ndarray, np.ndarray]:
    """R1 fix 6 and re-check fix 3: route A needs the programme end the SAME feed capture lists to be after the start of slot k + 2, the nominal
    instant ``grid0 + 2 h x (k + 2)``: the latest end among the market's positive-rate configurations, each at its earliest consistent instant
    (a date-only ``D`` at ``D 00:00Z``), is later than it; open-ended or sentinel qualifies; malformed (any positive configuration) is NaN. Returns (ok 1 / 0 / NaN, reason; ``feed_unlisted`` for a market the capture does not list)."""
    n = len(cond)
    if feed_k is None:
        return np.full(n, np.nan), np.full(n, "feed_missing", dtype=object)
    f = feed_k.reindex(cond.astype(str).to_numpy())
    kind = f["end_kind"].fillna("none").astype(str).to_numpy()
    lo = f["end_lo"].to_numpy(float)
    t2 = b.slot_time(k + 2, spec)
    ok = np.full(n, np.nan)
    why = np.full(n, "", dtype=object)
    ok[kind == "open"], why[kind == "open"] = 1.0, "feed_end_open"
    ok[kind == "malformed"], why[kind == "malformed"] = np.nan, "feed_end_malformed"
    d = kind == "dated"
    with np.errstate(invalid="ignore"):
        ok[d] = (lo[d] > t2).astype(float)
    why[d & (ok == 0)] = "feed_end_soon"
    unlisted = ~pd.Index(cond.astype(str).to_numpy()).isin(feed_k.index)
    why[kind == "none"] = "feed_no_positive_config"
    why[unlisted] = "feed_unlisted"  # a ghost market (absent from the feed capture) is its own category, never "listed with no positive configuration"
    ok[kind == "none"] = np.nan
    return ok, why


def rwblink_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: b.MidStore, cap: dict, k: int, spec: dict, feed_k: pd.DataFrame | None,
                  feed_prev: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    """CH212's units of capture k (design 4): 1.4 at k - 1 and k, mid_k in [0.05, 0.95], non-sports ex-crypto, end unknown or > t + 7 h (t = capture
    k's last row receipt), ``rewarded_k = 1`` under the carry. ``om = 1[carry_lag_k >= 1]``; ``om_prev`` the same at k - 1; ``listed_prev`` the Gamma
    field listed at k - 1; the feed flags from the last usable feed captures before captures k and k - 1 (``feed_k`` / ``feed_prev``); route A's end
    rule (:func:`feed_end_ok`). The returned frame holds every rewarded unit (route membership is decided by the census). No slot after k is read."""
    c = spec["tests"]["CH212"]
    t_dec = float(np.nanmax(ser_k["t_row"].to_numpy(float))) if len(ser_k) else float("nan")
    j, cnt = b._movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = b._non_sports_ex_crypto(j.copy(), cnt)
    rew = j["rewarded"].to_numpy(float)
    cnt["eligible_in_band"], cnt["eligible_in_band_status_finite"] = len(j) + int(cnt.get("sports_unknown", 0)), int(np.isfinite(rew).sum())
    with np.errstate(invalid="ignore"):
        end_ok = np.isnan(j["end_ts"].to_numpy(float)) | (j["end_ts"].to_numpy(float) > t_dec + c["end_margin_h"] * 3600.0)
    cnt["end_date_decision"] = int((~end_ok).sum())
    cnt["reward_unparseable"] = int((end_ok & ~np.isfinite(rew)).sum())
    cnt["unrewarded"] = int((end_ok & (rew == 0.0)).sum())
    j = j[end_ok & (rew == 1.0)].reset_index(drop=True)
    if j.empty:
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    pj = ser_p.reindex(mk)
    om = j["om"].to_numpy(float)
    om_p = np.where(pj["rewarded"].to_numpy(float) == 1.0, pj["om"].to_numpy(float), np.where(np.isfinite(pj["rewarded"].to_numpy(float)), 0.0, np.nan))
    listed_p = (b._status_array(pj) == "listed").astype(float)
    ff = feed_flags(j["condition_id"], feed_k, feed_prev)
    eok, why = feed_end_ok(j["condition_id"], feed_k, k, spec)
    mid, mid_p = j["mid"].to_numpy(float), j["mid_p"].to_numpy(float)
    tick = j["tick"].to_numpy(float)
    m12 = b._mid12(store, k, mk)
    d24, d24f = b._own24(1.0, mid, m12)
    rv, rvs, rvf = _rv(store, k, mk.to_numpy(), tick, c)
    vol, volm = b._vol_cols(j["vol24"])
    end = j["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        f_ok = (np.isnan(end) | (end > t_dec + c["f_end_margin_h"] * 3600.0)).astype(float)
    u = pd.DataFrame({**b._base_out(j, cap, k), "t_row": np.full(len(j), t_dec), "mid": mid, "tick": tick, "liq": j["liq"].to_numpy(float), "end_ts": end,
                      "n_members": j["n_members"].to_numpy(float), "om": om, "om_prev": om_p, "listed_prev": listed_p, "carry_lag": j["carry_lag"].to_numpy(float),
                      "abs_d2h": np.abs(mid - mid_p), "spread": j["spread"].to_numpy(float), "log1p_vol": vol, "vol_missing": volm, "d24": d24, "d24_flag": d24f,
                      "rv24s": rvs, "rv_floor": rvf, "f_ok": f_ok, "page_norm": j["page_norm"].to_numpy(float), "recv_off": j["recv_off"].to_numpy(float),
                      "vol_absent": 1.0 - j["vol_present"].to_numpy(float), "ltp_absent": 1.0 - j["ltp_present"].to_numpy(float), "comp_present": j["comp_present"].to_numpy(float),
                      "clob_listed": ff["clob_listed"], "clob_listed_prev": ff["clob_listed_prev"], "clob_dropped": ff["clob_dropped"], "feed_end_ok": eok, "feed_end_why": why,
                      "fee_cat": j["fee_cat"].to_numpy(object), "condition_id": j["condition_id"].astype(str).to_numpy(object)})
    u = b._common_cols(u)
    u["log_rv24s"] = np.log(u["rv24s"])
    _slot_dummies(u, k % 12)
    u = b._drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "tick": "tick_unknown", "om_prev": "noprev_status"})
    cnt["units_pre_cap"] = len(u)
    return u, cnt


CONTROLS_212 = [*(f"sd{s}" for s in range(1, 12)), "abs_d2h", "om_prev", "logit_mid", "abs_dev", "spread", "log1p_liq", "log1p_vol", "vol_missing", "d24", "d24_flag",
                "log_rv24s", "rv_floor", "tick001", "log_hte", "hte_unknown"]


def mh_odds_ratio(y, x, strata) -> dict:
    """Mantel-Haenszel odds ratio of ``y = 1`` (e.g. ``volume24hr`` absent) given ``x = 1`` (``om = 1``) against ``x = 0``, over ``strata``
    (market x UTC day): ``sum(a d / n) / sum(b c / n)`` over strata holding both classes. NaN when undefined."""
    d = pd.DataFrame({"y": np.asarray(y, float), "x": np.asarray(x, float), "s": np.asarray(strata)}).dropna()
    if d.empty:
        return {"or": float("nan"), "strata": 0}
    d["a"] = ((d["x"] == 1) & (d["y"] == 1)).astype(float)
    d["b"] = ((d["x"] == 1) & (d["y"] == 0)).astype(float)
    d["c"] = ((d["x"] == 0) & (d["y"] == 1)).astype(float)
    d["d"] = ((d["x"] == 0) & (d["y"] == 0)).astype(float)
    s = d.groupby("s")[["a", "b", "c", "d"]].sum()
    s = s[((s["a"] + s["b"]) > 0) & ((s["c"] + s["d"]) > 0)]
    n = s.sum(axis=1)
    num, den = float((s["a"] * s["d"] / n).sum()), float((s["b"] * s["c"] / n).sum())
    return {"or": num / den if den > 0 else (float("inf") if num > 0 else float("nan")), "strata": int(len(s)), "num": num, "den": den}


def page_diff(pop: pd.DataFrame) -> dict:
    """The within-market mean difference of the normalised page position between ``om = 1`` and ``om = 0`` rows: per market holding both classes the
    difference of class means, averaged over those markets (each market once)."""
    d = pop[["market_id", "om", "page_norm"]].dropna()
    g = d.groupby(["market_id", "om"])["page_norm"].mean().unstack()
    if 0.0 not in g.columns or 1.0 not in g.columns:
        return {"diff": float("nan"), "markets": 0}
    g = g.dropna()
    return {"diff": float((g[1.0] - g[0.0]).mean()) if len(g) else float("nan"), "markets": int(len(g))}


def route_rule(inp: dict, rule: dict) -> str:
    """Section 4's route rule on census counts only: ``A`` if either odds ratio >= 1.5 or |page difference| >= 0.10; ``B`` if >= 30% of the
    listed -> null transitions have ``clob_dropped``; both -> ``A`` (route B a reported reading); neither -> ``dropped``. NaN inputs never pass."""
    def ge(v, t):
        return bool(v is not None and np.isfinite(v) and v >= t)
    a = ge(inp.get("or_vol_absent"), rule["or_min"]) or ge(inp.get("or_ltp_absent"), rule["or_min"]) or ge(abs(inp.get("page_diff", float("nan"))), rule["page_diff_min"])
    bb = ge(inp.get("dropped_share_of_transitions"), rule["dropped_share_min"])
    return "A" if a else ("B" if bb else "dropped")


def census_ch212(U: pd.DataFrame, tot: dict, spec: dict, covered_days: float, feed_ok: dict, switching: dict) -> dict:
    """CH212's census gate (design 7 table, CC9). ``U`` = every rewarded unit with its feed flags (every n_members)."""
    g, a = spec["census_gates"]["CC9_CH212"], b.mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CC9_CH212"]
    scale = _scale(covered_days)
    if U.empty:
        return b._gate_min_days({"error": "no units", "gate_CH212": {"pass": False}}, "gate_CH212", covered_days, mind)
    c = spec["tests"]["CH212"]
    elig, fin = tot.get("eligible_in_band", 0), tot.get("eligible_in_band_status_finite", 0)
    finite_share = fin / elig if elig else float("nan")
    cap_n = spec["member_cap"]["max_members"]
    cap_share = float((U["n_members"] <= cap_n).mean())
    P = U[U["n_members"] <= cap_n]
    pop, excl, top = b._fam(P, a["family_cap"])
    pop = pop.copy()
    listed = P[P["clob_listed"] == 1]  # the route rule reads the capped census units before the census-fixed family exclusion
    strata = listed["market_id"].astype(str) + "|" + listed["day"].astype(str)
    inp = {"or_vol_absent": mh_odds_ratio(listed["vol_absent"], listed["om"], strata)["or"], "or_ltp_absent": mh_odds_ratio(listed["ltp_absent"], listed["om"], strata)["or"],
           "page_diff": page_diff(listed)["diff"]}
    trans = P[(P["listed_prev"] == 1) & (P["om"] == 1)]
    tr_known = trans[np.isfinite(trans["clob_dropped"].to_numpy(float))]
    inp["dropped_share_of_transitions"] = float(tr_known["clob_dropped"].mean()) if len(tr_known) else float("nan")
    route = route_rule(inp, c["route_rule"]) if feed_ok["ok"] else "dropped"
    A = pop[(pop["clob_listed"] == 1) & (pop["feed_end_ok"] == 1)]
    Bp = pop[((pop["om"] == 0) & (pop["clob_listed"] == 1)) | ((pop["om"] == 1) & (pop["clob_dropped"] == 1))]
    Ap = P[(P["clob_listed"] == 1) & (P["feed_end_ok"] == 1)]
    Bpp = P[((P["om"] == 0) & (P["clob_listed"] == 1)) | ((P["om"] == 1) & (P["clob_dropped"] == 1))]
    proj_a_om = float((Ap["om"] == 1).sum() * scale)
    proj_b_drop = float((Bpp["om"] == 1).sum() * scale)
    R = A if route != "B" else Bp
    Rq = Ap if route != "B" else Bpp
    om_slots = Rq.loc[Rq["om"] == 1, "slot"] % 12
    venue_top = float(om_slots.value_counts(normalize=True).iloc[0]) if len(om_slots) else float("nan")
    sd = a["sd_a"] if route != "B" else a["sd_ds"]
    floor = a["ch212_floor_A"] if route != "B" else a["ch212_floor_B"]
    de = b._de(R, scale, g["de_floor"], a) if len(R) else {"DE_gate": float("nan")}
    cm = b.class_mde8(R, "om", CONTROLS_212, scale, a, de["DE_gate"], sd) if len(R) else {"mde_class_c": float("inf"), "design_ss": {"vif_w": float("nan")}}
    vif = cm["design_ss"]["vif_w"]
    corr_liq = b.wcorr(R, "om", "log1p_liq") if len(R) else {"within": None, "pooled": None}
    corr_mv = b.wcorr(R, "om", "abs_d2h") if len(R) else {"within": None, "pooled": None}
    bm = b.block_min_units(covered_days)
    bs = b.block_share(R, bm) if len(R) else float("nan")
    F = R[(R["f_ok"] == 1) & np.isfinite(R["om_twin"].to_numpy(float))] if "om_twin" in R and len(R) else R.iloc[0:0]
    pr = pd.DataFrame({"market_id": F["market_id"].to_numpy(), "t_row": F["t_row"].to_numpy(float), "imb_j": F["om"].to_numpy(float), "imb_j13": F["om_twin"].to_numpy(float)}) if len(F) else pd.DataFrame()
    pc = b.pair_correlations(pr, 3)
    fm = f_mde_gate(cm["mde_class_c"], pc["r_gate"], float("nan"))
    sp_days = switching.get("per_day", {})
    sw_mean = float(np.mean(list(sp_days.values()))) if sp_days else float("nan")
    why = pop["feed_end_why"].astype(str).value_counts().to_dict() if len(pop) else {}
    res = {"route": route, "route_rule_inputs": inp, "route_rule_strata": {"vol": mh_odds_ratio(listed["vol_absent"], listed["om"], strata), "ltp": mh_odds_ratio(listed["ltp_absent"], listed["om"], strata),
           "page": page_diff(listed)}, "transitions_listed_to_null": int(len(trans)), "transitions_with_feed_known": int(len(tr_known)),
           "receipt_offset_diff_s": float(listed.loc[listed["om"] == 1, "recv_off"].mean() - listed.loc[listed["om"] == 0, "recv_off"].mean()) if len(listed) else float("nan"),
           "finite_status_share": finite_share, "feed_completeness": feed_ok, "switching_markets_per_day": sp_days, "switching_markets_mean_per_day": sw_mean,
           "projected_routeA_omitted_21d": proj_a_om, "projected_routeB_dropped_21d": proj_b_drop, "units_routeA": int(len(A)), "units_routeB": int(len(Bp)),
           "ghost_units": int((pop["clob_listed"] == 0).sum()), "feed_missing_units": int((~np.isfinite(pop["clob_listed"].to_numpy(float))).sum()), "feed_end_reasons": why,
           "feed_end_shares": {k_: v_ / max(1, int((pop["clob_listed"] == 1).sum())) for k_, v_ in why.items() if k_ != "feed_unlisted"},
           "feed_end_shares_denominator": "units of the capped, family-excluded CH212 population whose market is listed in the feed capture (clob_listed = 1); feed_unlisted (ghost) units are counted in feed_end_reasons and excluded from the shares",
           "switching_gate_definition": SWITCHING_GATE_DEFINITION, "cap_share": cap_share, "venue_clock_top_share": venue_top,
           "exclude_family": excl, "top_family_share": top, "design_effect": de, "class_mde": cm, "vif_w": vif, "corr_liq": corr_liq, "corr_abs_move": corr_mv,
           "block_min_units": bm, "block_share": bs, "F_label_printed": fm, "F_pairs": pc, "f_role": "label", "events": b._events8(R, scale, covered_days) if len(R) else {},
           "omitted_by_slot_of_day": {str(int(k_)): int(v_) for k_, v_ in (pop.loc[pop["om"] == 1, "slot"] % 12).value_counts().sort_index().items()},
           "run_lengths": {k_: int(v_) for k_, v_ in tot.items() if str(k_).startswith("om_run_")}, "splits": b._desc_splits(tot), "t_sum_used": a["t_sum"],
           "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    gate = {"finite_status": bool(np.isfinite(finite_share) and finite_share >= g["finite_status_min"]), "feed_completeness": bool(feed_ok["ok"]),
            "switching": bool(np.isfinite(sw_mean) and sw_mean >= g["switching_per_day_min"]),
            "units": (proj_a_om >= g["routeA_omitted_projected_min"]) if route != "B" else (proj_b_drop >= g["routeB_dropped_projected_min"]),
            "venue_clock": bool(np.isfinite(venue_top) and venue_top <= g["venue_clock_max"]), "cap_share": bool(cap_share >= g["cap_share_min"]),
            "corr_liq": b.corr_ok(corr_liq, g["corr_max"], both=True), "corr_abs_move": b.corr_ok(corr_mv, g["corr_max"]),
            "vif_w": bool(np.isfinite(vif) and vif <= g["vif_w_max"]), "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]),
            "route": route in ("A", "B"), "mde": bool(cm["mde_class_c"] <= floor * 100.0)}
    res["gate_CH212"] = b._gate(gate)
    return b._gate_min_days(res, "gate_CH212", covered_days, mind)


# --- CH214 the pool splits (design 3) -----------------------------------------------------------------------------------------------


def band_sum(dbid1, dask1, dbid5, dask5, v_cents, max_1c: float) -> np.ndarray:
    """The declared band-sum proxy: ``depth_bid_1c + depth_ask_1c`` if ``v <= 1.5c``, else ``depth_bid_5c + depth_ask_5c`` (NaN when v is missing)."""
    v = np.asarray(v_cents, float)
    s1 = np.asarray(dbid1, float) + np.asarray(dask1, float)
    s5 = np.asarray(dbid5, float) + np.asarray(dask5, float)
    with np.errstate(invalid="ignore"):
        return np.where(~np.isfinite(v), np.nan, np.where(v <= max_1c + 1e-12, s1, s5))


def split_innovation(dD, scale: float) -> tuple[np.ndarray, np.ndarray]:
    """Re-check fix 2: ``zdD+ = max(0, dD) / scale`` and ``zdD- = min(0, dD) / scale``, split at ZERO change and scaled by the census scale, never
    centred (a census centre below 0 cannot move a small departure into the arrival term)."""
    d = np.asarray(dD, float)
    if not (np.isfinite(scale) and scale > 0):
        return np.full(len(d), np.nan), np.full(len(d), np.nan)
    return np.maximum(0.0, d) / scale, np.minimum(0.0, d) / scale


def pool_units(ser_p: pd.DataFrame, ser_p2: pd.DataFrame, store: b.MidStore, sw_k2: pd.DataFrame | None, sw_k1: pd.DataFrame | None, cap_p: dict, k_start: float,
               k: int, spec: dict) -> tuple[pd.DataFrame, dict]:
    """CH214's units of origin k (design 3): carried frames of captures k - 1 (``ser_p``) and k - 2 (``ser_p2``); 1.4 at k - 2 and k - 1, mid_{k-1} in
    [0.10, 0.90], non-sports ex-crypto, ``rewarded_{k-1} = 1``; sweep 1 of passes k - 2 and k - 1 two-sided on outcome 0, tight, both band sums
    positive, each received BEFORE capture k's start (``k_start``); quiet (mid and spread of the sweeps unchanged, < 0.005); half-spread < v at both
    sweeps (``touch_out_of_band``); the source's band equal at k - 2 and k - 1 (``band_changed``); no status change (``status_changed``); end unknown or
    > t + 7 h with t = sweep k - 1's receipt (the decision). The frame keeps every n_members. No sweep or capture after the decision is read
    (capture k gives its manifest start only)."""
    c = spec["tests"]["CH214"]
    j, cnt = b._movers_join(ser_p, ser_p2, cap_p, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = b._non_sports_ex_crypto(j.copy(), cnt)
    rew = j["rewarded"].to_numpy(float)
    cnt["eligible_in_band_status_finite"] = int(np.isfinite(rew).sum())
    j = j[rew == 1.0].reset_index(drop=True)
    cnt["rewarded_eligible_in_band"] = len(j)
    if sw_k1 is None:
        cnt["nosweep_km1"] = 1
        return pd.DataFrame(), cnt
    if sw_k2 is None:
        cnt["nosweep_km2"] = 1
        return pd.DataFrame(), cnt
    if j.empty:
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    a1, a2 = sw_k1.reindex(mk).reset_index(drop=True), sw_k2.reindex(mk).reset_index(drop=True)
    v = j["rew_maxspread"].to_numpy(float)
    D1 = band_sum(a1["dbid1"], a1["dask1"], a1["dbid5"], a1["dask5"], v, c["band_1c_max_cents"])
    D2 = band_sum(a2["dbid1"], a2["dask1"], a2["dbid5"], a2["dask5"], v, c["band_1c_max_cents"])
    smax = c["sweep_spread_max"] + 1e-12
    s1, s2 = (a1["sask"] - a1["sbid"]).to_numpy(float), (a2["sask"] - a2["sbid"]).to_numpy(float)
    with np.errstate(invalid="ignore"):
        two = (a1["s_two"].to_numpy(float) == 1) & (a2["s_two"].to_numpy(float) == 1)
        tight = (s1 <= smax) & (s2 <= smax)
        dep = np.isfinite(D1) & np.isfinite(D2) & (D1 > 0) & (D2 > 0)
        t1, t2 = a1["s_t"].to_numpy(float), a2["s_t"].to_numpy(float)
        recv = np.isfinite(t1) & np.isfinite(t2) & (t1 < k_start) & (t2 < k_start)
    struct = two & tight & dep
    cnt["sweep_after_origin"] = int((struct & ~recv).sum())
    cov = struct & recv
    cnt["covered"] = int(cov.sum())
    cov_nt = two & dep & recv  # section 7's coverage as WRITTEN (no 'tight'): the gate numerators (LT8 verification fix 1's lesson)
    cnt["covered_notight"] = int(cov_nt.sum())
    sm1, sm2 = (a1["sbid"] + a1["sask"]).to_numpy(float) / 2.0, (a2["sbid"] + a2["sask"]).to_numpy(float) / 2.0
    with np.errstate(invalid="ignore"):
        quiet = (np.abs(sm1 - sm2) < c["quiet_eps"] - _Q_EPS) & (np.abs(s1 - s2) < c["quiet_eps"] - _Q_EPS)
        inb = (s1 / 2.0 * 100.0 < v - _EPS_C) & (s2 / 2.0 * 100.0 < v - _EPS_C)
    cnt["quiet_covered"] = int((cov & quiet).sum())
    pj2 = ser_p2.reindex(mk)
    rew2 = pj2["rewarded"].to_numpy(float)
    v2 = pj2["rew_maxspread"].to_numpy(float)
    stat_ok = rew2 == 1.0
    with np.errstate(invalid="ignore"):
        band_ok = stat_ok & np.isfinite(v2) & np.isfinite(v) & (np.abs(v - v2) <= 1e-9)
        end = j["end_ts"].to_numpy(float)
        end_ok = np.isnan(end) | (end > t1 + c["end_margin_h"] * 3600.0)
    qc = cov & quiet
    cnt["quiet_covered_notight"] = int((cov_nt & quiet).sum())
    cnt["band_unchanged_quiet_covered_notight"] = int((cov_nt & quiet & band_ok).sum())
    cnt["touch_out_of_band"] = int((qc & ~inb).sum())
    cnt["status_changed"] = int((qc & inb & ~stat_ok).sum())
    cnt["band_changed"] = int((qc & inb & stat_ok & ~band_ok).sum())
    cnt["quiet_covered_in_band_status_ok"] = int((qc & inb & stat_ok).sum())
    cnt["band_unchanged"] = int((qc & inb & band_ok).sum())
    cnt["end_date_decision"] = int((qc & inb & band_ok & ~end_ok).sum())
    keep = qc & inb & band_ok & end_ok
    j, a1, a2 = j[keep].reset_index(drop=True), a1[keep].reset_index(drop=True), a2[keep].reset_index(drop=True)
    D1, D2, v, t1, s1 = D1[keep], D2[keep], v[keep], t1[keep], s1[keep]
    if j.empty:
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    imb1, imb2 = b.imbalance(a1["dbid5"], a1["dask5"]), b.imbalance(a2["dbid5"], a2["dask5"])
    vn1, vn2 = j["vnum"].to_numpy(float), ser_p2["vnum"].reindex(mk).to_numpy(float)
    dv = vn1 - vn2
    dv_ok = np.isfinite(dv)
    dvnum = np.where(dv_ok, np.log1p(np.clip(np.where(dv_ok, dv, 0.0), 0, None)), 0.0)
    mid = j["mid"].to_numpy(float)
    tick = j["tick"].to_numpy(float)
    m12 = b._mid12(store, k - 1, mk)
    d24, d24f = b._own24(1.0, mid, m12)
    rv, rvs, rvf = _rv(store, k - 1, mk.to_numpy(), tick, c)
    vol, volm = b._vol_cols(j["vol24"])
    ft = b._ft_both(np.ones(len(j)), a1["bsz1"], a1["asz1"], j["rew_min"], spec["reward_rule"]["ft_factor"])
    rate = j["rew_rate"].to_numpy(float)
    end = j["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        f_ok = (np.isnan(end) | (end > t1 + c["f_end_margin_h"] * 3600.0)).astype(float)
    sg = j["spread"].to_numpy(float)
    u = pd.DataFrame({**b._base_out(j, cap_p, k), "t_row": t1, "mid": mid, "tick": tick, "liq": j["liq"].to_numpy(float), "end_ts": end, "n_members": j["n_members"].to_numpy(float),
                      "v_c": v, "D_km1": D1, "D_km2": D2, "dD": np.log(D1) - np.log(D2), "logD_km1": np.log(D1), "dDb": _side_change(a1, a2, "bid", v, c), "dDa": _side_change(a1, a2, "ask", v, c), "D1c_km1": (a1["dbid1"] + a1["dask1"]).to_numpy(float), "D5c_km1": (a1["dbid5"] + a1["dask5"]).to_numpy(float),
                      "dimb5": imb1 - imb2, "sws_km1": s1, "s_km1": sg, "gap_s": sg - s1, "lag_s": (k_start - t1) / 60.0, "log1p_vol": vol, "vol_missing": volm,
                      "dvnum": dvnum, "vnum_missing": (~dv_ok).astype(float), "d24": d24, "d24_flag": d24f, "rv24s": rvs, "rv_floor": rvf, "ft_both": ft,
                      "log_rate": np.log(np.where(rate > 0, rate, np.nan)), "om_km1": j["om"].to_numpy(float), "f_ok": f_ok, "fee_cat": j["fee_cat"].to_numpy(object),
                      "yield0": rate / (D1 * np.where(np.isfinite(mid), mid, np.nan))})
    u = b._common_cols(u)
    u["log_rv24s"] = np.log(u["rv24s"])
    u = b._drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "tick": "tick_unknown", "dD": "dD_undefined", "dimb5": "dimb_unknown", "ft_both": "ft_both_unknown",
                                 "log_rate": "rate_unknown"})
    u["dD_lag"] = np.nan
    cnt["units_pre_cap"] = len(u)
    return u, cnt


def add_pool_lag(Q: pd.DataFrame, lag2: pd.DataFrame | None, lag3: pd.DataFrame | None, spec: dict) -> pd.DataFrame:
    """CH214's twin ``dD_lag = log D_{k+3} - log D_{k+2}`` from sweep 1 of passes k + 2 and k + 3 through :func:`lag_band_sums` (sizes only; no quiet
    condition, LT8 13.3 Q3), the unit's own band rule (1c if v <= 1.5c, else 5c); NaN (out of the F arm) when a sum is missing or zero."""
    Q = Q.copy()
    if lag2 is None or lag3 is None or Q.empty:
        Q["dD_lag"] = np.nan
        return Q
    c = spec["tests"]["CH214"]
    mk = Q["market_id"].astype(str)
    a, d = lag2.reindex(mk), lag3.reindex(mk)
    v = Q["v_c"].to_numpy(float)
    Da = band_sum(a["depth_bid_1c"], a["depth_ask_1c"], a["depth_bid_5c"], a["depth_ask_5c"], v, c["band_1c_max_cents"])
    Dd = band_sum(d["depth_bid_1c"], d["depth_ask_1c"], d["depth_bid_5c"], d["depth_ask_5c"], v, c["band_1c_max_cents"])
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = np.isfinite(Da) & np.isfinite(Dd) & (Da > 0) & (Dd > 0)
        Q["dD_lag"] = np.where(ok, np.log(Dd) - np.log(Da), np.nan)
    return Q


def _side_change(a1: pd.DataFrame, a2: pd.DataFrame, side: str, v, c: dict) -> np.ndarray:
    """Per-side split of ``dD`` (S4) under the same band rule (1c if v <= 1.5c, else 5c); NaN where a side's sum is missing or zero."""
    one = np.asarray(v, float) <= c["band_1c_max_cents"] + 1e-12
    x1 = np.where(one, a1[f"d{side}1"].to_numpy(float), a1[f"d{side}5"].to_numpy(float))
    x2 = np.where(one, a2[f"d{side}1"].to_numpy(float), a2[f"d{side}5"].to_numpy(float))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((x1 > 0) & (x2 > 0), np.log(x1) - np.log(x2), np.nan)


CONTROLS_214 = ["zdDm", "logD_km1", "z_dimb5", "sws_km1", "s_km1", "gap_s", "lag_s", "logit_mid", "abs_dev", "log1p_vol", "vol_missing", "dvnum", "vnum_missing", "d24", "d24_flag",
                "log_rv24s", "rv_floor", "tick001", "ft_both", "log_rate", "om_km1", "log_hte", "hte_unknown"]


def slope_mde9(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float, gap: float) -> dict:
    """CH214's slope MDE (cents) for a change of the UNSTANDARDISED tested term ``zdD+`` equal to ``gap`` (the census tercile gap of the centred
    ``zdD``; re-check fix 4: a declared scale): ``max(declared, design)``. Declared = ``t_sum x SD / sqrt(n_eff) x sqrt(DE_gate) x day x sqrt(max(1,
    VIF_w)) / SD(term) x gap`` (section 3's formula at the census counts); design = ``t_sum x day x SD x se_1 x gap`` (:func:`design_se` per unit of the
    term). NaN anywhere gives inf."""
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    pe = pop[eff] if len(pop) else pop
    dsg = b.design_ss(pe, term, controls) if len(pop) else {"n": 0, "ss_resid": float("nan"), "vif_w": float("nan")}
    n_eff = float(eff.sum()) * scale
    sd_t = float(np.nanstd(pe[term].to_numpy(float), ddof=1)) if len(pe) > 1 else float("nan")
    per_sd = b.mde_slope_declared(n_eff, sd, de_gate, a, dsg["vif_w"])
    declared = per_sd / sd_t * gap * 100.0 if np.isfinite(per_sd) and np.isfinite(sd_t) and sd_t > 0 and np.isfinite(gap) else float("inf")
    se = b.design_se(pe, [term], controls, {term: 1.0}, float(a["de_rho"]), scale) if len(pe) else float("nan")
    design = a["t_sum"] * a["day_factor"] * sd * se * gap * 100.0 if np.isfinite(se) and np.isfinite(gap) else float("inf")
    return {"design_ss": dsg, "n_eff_projected": n_eff, "sd_term": sd_t, "declared_c": declared, "design_c": design, "se_1": se,
            "mde_c": float(max(declared, design)) if np.isfinite(declared) else float("inf")}


def census_ch214(Q: pd.DataFrame, tot: dict, spec: dict, covered_days: float, pair_days: float, band: dict) -> dict:
    """CH214's census gate (design 7 table, CS9). ``Q`` = the quiet in-band units with their members (cap applied here)."""
    g, a = spec["census_gates"]["CS9_CH214"], b.mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CS9_CH214"]
    scale = _scale(covered_days)
    if Q.empty:
        return b._gate_min_days({"error": "no units", "gate_CH214": {"pass": False}}, "gate_CH214", covered_days, mind)
    elig, cov = tot.get("rewarded_eligible_in_band", 0), tot.get("covered_notight", 0)
    coverage = cov / elig if elig else float("nan")
    qc = tot.get("quiet_covered_notight", 0)
    quiet_share = qc / cov if cov else float("nan")
    unch_share = tot.get("band_unchanged_quiet_covered_notight", 0) / qc if qc else float("nan")
    tight_variant = {"coverage": tot.get("covered", 0) / elig if elig else float("nan"), "quiet_share": tot.get("quiet_covered", 0) / tot.get("covered", 0) if tot.get("covered", 0) else float("nan")}
    cap_n = spec["member_cap"]["max_members"]
    cap_share = float((Q["n_members"] <= cap_n).mean())
    P = Q[Q["n_members"] <= cap_n]
    pop, excl, top = b._fam(P, a["family_cap"])
    pop = pop.copy()
    cen, scl = b.standardise(pop["dD"])
    pop["zdD"] = b._z(pop["dD"], cen, scl)
    pop["zdDp"], pop["zdDm"] = split_innovation(pop["dD"], scl)
    pop["zdDp_lag"], pop["zdDm_lag"] = split_innovation(pop["dD_lag"], scl)
    pop["z_dimb5"] = b._z(pop["dimb5"], *b.standardise(pop["dimb5"]))
    pop["z_d24"] = b._z(pop["d24"], *b.standardise(pop["d24"]))
    t1, t2, gap = b.terciles(pop["zdD"])
    z = pop["zdD"].to_numpy(float)
    gap_plus = float(pop.loc[z >= t2, "zdDp"].mean() - pop.loc[z <= t1, "zdDp"].mean()) if np.isfinite(gap) else float("nan")
    de = b._de(pop, scale, g["de_floor"], a)
    sm = slope_mde9(pop, "zdDp", CONTROLS_214, scale, a, de["DE_gate"], a[g["sd"]], gap)
    vif = sm["design_ss"]["vif_w"]
    ri = b.resid_iqr(pop, "dD", ["logD_km1"], int(g["resid_iqr_min_units"]), g["resid_iqr_min"])
    corr = {}
    for x in ("zdD", "zdDp"):
        corr[f"{x}:dimb5"] = b.wcorr(pop, x, "z_dimb5")
        corr[f"{x}:own24"] = b.corr_pair(pop, x, "z_d24", "d24_flag")
        corr[f"{x}:dvnum"] = b.corr_pair(pop, x, "dvnum", "vnum_missing")
        corr[f"{x}:ft_both"] = b.wcorr(pop, x, "ft_both")
        corr[f"{x}:log_rate"] = b.wcorr(pop, x, "log_rate")
    corr_liq = {x: b.wcorr(pop, x, "log1p_liq") for x in ("zdD", "zdDp")}
    bm = b.block_min_units(covered_days)
    bs = b.block_share(pop, bm)
    F = pop[(pop["f_ok"] == 1) & np.isfinite(pop["zdDp_lag"].to_numpy(float))]
    pr = pd.DataFrame({"market_id": F["market_id"].to_numpy(), "t_row": F["t_row"].to_numpy(float), "imb_j": F["zdDp"].to_numpy(float), "imb_j13": F["zdDp_lag"].to_numpy(float)}) if len(F) else pd.DataFrame()
    pc = b.pair_correlations(pr, int(g["pair_min_per_market"]))
    scale_f = _scale(pair_days)
    se_f = b.design_se(F[b._eff(F)], ["zdDp", "zdDp_lag"], [*CONTROLS_214, "zdDm_lag"], {"zdDp": 1.0, "zdDp_lag": -1.0}, float(a["de_rho"]), scale_f) if len(F) else float("nan")
    fm = f_mde_gate(sm["mde_c"], pc["r_gate"], a["t_sum"] * a["day_factor"] * a[g["sd"]] * se_f * gap * 100.0 if np.isfinite(se_f) and np.isfinite(gap) else float("inf"))
    proj = float(len(P) * scale)
    pair_ok = bool(np.isfinite(pair_days) and pair_days >= g["pair_min_days"] and pc["markets"] >= g["pair_markets_min"] and np.isfinite(pc["r_gate"]) and pc["r_gate"] <= g["r_gate_max"])
    vnum_share = float(pop["vnum_missing"].mean()) if len(pop) else float("nan")
    res = {"two_sweep_coverage": coverage, "quiet_share": quiet_share, "band_unchanged_share": unch_share, "tight_variant_printed": tight_variant, "projected_units_21d": proj, "cap_share": cap_share,
           "exclude_family": excl, "top_family_share": top, "band_unit_check": band, "dD": {"centre": cen, "scale": scl, "within_market_sd_median": float(pop.groupby("market_id")["dD"].std().median()),
           "share_positive": float((pop["dD"] > 0).mean()), "share_zdD_positive": float((pop["zdD"] > 0).mean())}, "zdD": {"terciles": [t1, t2], "tercile_gap": gap, "zdDp_gap_between_zdD_terciles": gap_plus},
           "design_effect": de, "slope": sm, "vif_w": vif, "resid_iqr": ri, "corr": corr, "corr_liq": corr_liq, "block_min_units": bm, "block_share": bs,
           "F": fm, "pairs": pc, "pair_days": pair_days, "f_role": "binding", "vnum_missing_share": vnum_share, "p_vm_input": vnum_share,
           "vol_missing_share": float(pop["vol_missing"].mean()), "band_sum_proxies": {"1c_quantiles": b._q(pop["D1c_km1"]), "5c_quantiles": b._q(pop["D5c_km1"]),
           "share_1c_rule": float((pop["v_c"] <= spec["tests"]["CH214"]["band_1c_max_cents"] + 1e-12).mean())}, "yield0_terciles": b._q(pop["yield0"], (1 / 3, 2 / 3)),
           "events": b._events8(pop, scale, covered_days), "splits": b._desc_splits(tot), "per_market": b._per_market(pop["market_id"]), "t_sum_used": a["t_sum"],
           "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    gate = {"coverage": bool(np.isfinite(coverage) and coverage >= g["coverage_min"]), "quiet_share": bool(np.isfinite(quiet_share) and quiet_share >= g["quiet_share_min"]),
            "band_unchanged": bool(np.isfinite(unch_share) and unch_share >= g["band_unchanged_min"]), "units": proj >= g["units_projected_min"],
            "cap_share": bool(cap_share >= g["cap_share_min"]), "resid_iqr": b.iqr_ok(ri, g), "vif_w": bool(np.isfinite(vif) and vif <= g["vif_w_max"]),
            **{f"corr_{nm}": b.corr_pair_ok(c_, g["corr_max"]) for nm, c_ in corr.items()}, **{f"corr_liq_{x}": b.corr_ok(c_, g["corr_max"], both=True) for x, c_ in corr_liq.items()},
            "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]), "r_gate": pair_ok, "slope_mde": bool(sm["mde_c"] <= a["mde_max"] * 100.0),
            "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max"] * 100.0)}
    res["gate_CH214"] = b._gate(gate)
    if not band["ok"]:
        res = _nan_gates(res, "gate_CH214", "band_unit")
    res = b._gate_min_days(res, "gate_CH214", covered_days, mind)
    res["census_fixed"] = {"zdD_centre": cen, "zdD_scale": scl, "zdD_cuts": [t1, t2], "zdD_gap": gap, "exclude_family": excl, "p_vm": max(vnum_share, spec["census_inputs"]["p_vm_floor"]) if np.isfinite(vnum_share) else None}
    return res


# --- CH215 the scheduled end (design 5) ---------------------------------------------------------------------------------------------


def rank_control_candidates(pool: pd.DataFrame, loglq_ref: float, n: int = 50) -> list[str]:
    """CH215's control order (design 5; code check 2026-10-23 must-fix 4): nearest ``|log liquidity|`` first, ties by ``condition_id`` (never ``market_id``).
    ``pool`` holds ``market_id``, ``condition_id`` and ``loglq``; a non-finite distance sorts last. Returns up to ``n`` market ids."""
    dist = np.abs(pool["loglq"].to_numpy(float) - float(loglq_ref))
    ranked = pool.assign(_d=np.where(np.isfinite(dist), dist, np.inf)).sort_values(["_d", "condition_id"], kind="mergesort")
    return ranked["market_id"].astype(str).tolist()[:n]


def assign_controls(ends: pd.DataFrame, cands: dict, max_n: int, span_s: float) -> pd.DataFrame:
    """Re-check fix 1: controls assigned greedily in DECISION-TIME order (the receipt of each end's decision feed capture, ties by ``condition_id``);
    each end considers only ends ALREADY decided and takes its nearest candidates (``cands[end_key]``, sorted nearest first) unused by those of
    them whose ``[T_e - 48 h, T_e)`` spans overlap its own. An end with no control is kept with an empty list (``no_control``)."""
    order = ends.sort_values(["t_dec", "condition_id", "T_e"], kind="mergesort")
    done: list[tuple[float, list[str]]] = []
    out = {}
    for key, row in zip(order["key"], order.itertuples(index=False), strict=True):
        lo, hi = row.T_e - span_s, row.T_e
        used = {m for t_e, ctl in done if (t_e - span_s) < hi and lo < t_e for m in ctl}
        pick = [m for m in cands.get(key, []) if m not in used][:max_n]
        out[key] = pick
        done.append((row.T_e, pick))
    e = ends.copy()
    e["controls"] = e["key"].map(lambda k_: out.get(k_, []))
    e["n_controls"] = e["controls"].map(len)
    return e


def end_clusters(ends: pd.DataFrame) -> pd.Series:
    """CH215's cluster: the treated event merged with every event linked to it by a shared control market (connected components)."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a_: str, b_: str) -> None:
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[rb] = ra

    first_ev: dict[str, str] = {}
    for ev, ctl in zip(ends["event_id"].astype(str), ends["controls"], strict=True):
        find(ev)
        for m in ctl:
            if m in first_ev:
                union(ev, first_ev[m])
            else:
                first_ev[m] = ev
    return ends["event_id"].astype(str).map(find)


def census_feed(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, feed_root=FEED_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CR9: CH215 on the sealed feed captures and captures (counts only). An end (condition_id, ``T_e``) of a positive-rate configuration with a
    dated end (a date-only ``D`` at ``D 00:00Z``) qualifies when ``T_e`` is in [span start + 48 h, span end], its DECISION is the first sealed usable
    feed capture listing it whose finish is <= ``T_e - 48 h`` and not before the first sealed capture's start (census convention), and at the decision capture (the last sealed capture whose LAST ROW RECEIPT is strictly before the decision time, 1.3 and the code check's
    must-fix 2) the market is eligible (1.4 at that capture, mid in [0.10, 0.90], non-sports ex-crypto) with a KNOWN end_date > ``T_e + 48 h``.
    Controls: reward-panel markets (the carry at the decision capture) of the same (category, tier, tick) cell, eligible, with no listed positive end
    within ``[T_e - 72 h, T_e + 72 h]`` at the decision feed capture, nearest ``|log liquidity|`` first (ties by condition_id, code check 2026-10-23 must-fix 4); reuse ban in decision-time
    order (:func:`assign_controls`). ``end_moved``: the last usable feed capture before ``T_e`` does not list the same end (a feed status only)."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    loaded = _load_for_census(seal, snapshot_root, [], feed_root, work, spec, need_sweeps=False, verify=verify)
    if "error" in loaded:
        return loaded
    by_slot, feeds = loaded["by_slot"], loaded["feeds"]
    c = spec["tests"]["CH215"]
    ci = spec["census_inputs"]
    t0, t1 = epoch(ci["span"]["start_utc"]), epoch(ci["span"]["end_utc"])
    lo_e, hi_e = t0 + c["knowledge_h"] * 3600.0, t1
    usable = sorted(((v["finish"], d) for d, v in feeds.items() if v["usable"]), key=lambda x: (x[0], x[1]))
    span_slots = _span_slots(spec)
    fc = feed_completeness(feeds, span_slots, spec)  # all of the span's slots (7; code check 2026-10-23 must-fix 5: not only those from the first possible end on)
    frames: dict[str, pd.DataFrame] = {}

    def ff(d: str) -> pd.DataFrame:
        if d not in frames:
            frames[d] = feed_frame(feeds[d]["dir"], spec)
        return frames[d]

    decision: dict[tuple[str, float], tuple[float, str, str]] = {}
    seen_ends: set[tuple[str, float]] = set()
    kinds = {"end_date_only": 0, "end_sentinel": 0, "open_or_none": 0, "malformed_markets": 0, "malformed_mixed_markets": 0, "positive_configs": 0, "ends_in_malformed_markets_excluded": 0}
    mv = {"pairs": 0, "moved": 0}
    prev_ends: dict[str, set[float]] = {}
    first_cap = min((v["start"] for v in by_slot.values()), default=math.inf)
    for fin, d in usable:
        if fin < first_cap:  # census convention: a decision needs a sealed capture at or before it (the 26 h feed look-back starts 2 h before the captures)
            continue
        f = ff(d)
        kinds["end_date_only"] += int(f["n_date_only"].sum()) if len(f) else 0
        kinds["end_sentinel"] += int(f["n_sentinel"].sum()) if len(f) else 0
        kinds["positive_configs"] += int(f["n_pos"].sum()) if len(f) else 0
        kinds["malformed_markets"] += int((f["end_kind"] == "malformed").sum()) if len(f) else 0
        kinds["malformed_mixed_markets"] += int(f["mixed_malformed"].sum()) if len(f) else 0
        cur_ends: dict[str, set[float]] = {}
        for cid, ends_js, ekind, fds in zip(f.index, f["ends"], f["end_kind"], f["feeds"], strict=True):
            es = [(float(x), k2) for x, k2 in json.loads(ends_js)]
            if ekind == "malformed":  # ruling 1: any malformed positive configuration makes the market NaN (its dated ends give no unit)
                kinds["ends_in_malformed_markets_excluded"] += sum(1 for x, _ in es if lo_e <= x <= hi_e)
                continue
            cur_ends[str(cid)] = {x for x, _ in es}
            for e_lo, _kind in es:
                if not (lo_e <= e_lo <= hi_e):
                    continue
                key = (str(cid), e_lo)
                seen_ends.add(key)
                if key not in decision and fin <= e_lo - c["knowledge_h"] * 3600.0:
                    decision[key] = (fin, d, str(fds))
        for cid, es in prev_ends.items():  # consecutive usable feed captures: a listed in-window end that the next capture does not carry (the market still listed)
            if cid in cur_ends:
                for e_lo in es:
                    if lo_e <= e_lo <= hi_e and fin < e_lo:
                        mv["pairs"] += 1
                        mv["moved"] += int(e_lo not in cur_ends[cid])
        prev_ends = cur_ends
    cnt = {"ends_in_window_listed_ahead": len(decision), **kinds}
    cnt["ends_in_window_seen"] = len(seen_ends)
    cnt["share_listed_ge_48h_ahead"] = len(decision) / len(seen_ends) if seen_ends else float("nan")
    cnt["moved_between_consecutive_feed_captures"] = {**mv, "share": mv["moved"] / mv["pairs"] if mv["pairs"] else float("nan"),
                                                      "denominator": "(listed in-window end, consecutive usable sealed feed captures with the market listed in both and the later finishing before the end) pairs"}
    n_dec = len(decision)
    cnt["sponsored_shares_of_decisions"] = {"sponsored_only": sum(1 for v_ in decision.values() if v_[2] == "sponsored") / n_dec if n_dec else float("nan"),
                                            "native_and_sponsored": sum(1 for v_ in decision.values() if v_[2] == "both") / n_dec if n_dec else float("nan"),
                                            "native_only": sum(1 for v_ in decision.values() if v_[2] == "native") / n_dec if n_dec else float("nan"),
                                            "denominator": "ends in the window listed at least 48 h ahead (decisions), by the feed(s) listing the market at the decision capture"}
    cnt["date_only_share"] = kinds["end_date_only"] / kinds["positive_configs"] if kinds["positive_configs"] else float("nan")
    cnt["sentinel_share"] = kinds["end_sentinel"] / kinds["positive_configs"] if kinds["positive_configs"] else float("nan")
    cnt["end_kind_denominator"] = ("positive-rate configurations of the sealed usable feed captures from the first sealed capture's start on, each capture counted once; "
                                   "CC9's feed_end_kinds_of_positive_configs counts every capture it reads (span-wide, once each): the two denominators differ and are declared")
    cnt["overlaps_with_prior_populations"] = PRIOR_POPULATION_OVERLAPS
    ends = pd.DataFrame([{"condition_id": k_[0], "T_e": k_[1], "t_dec": v_[0], "dec_feed": v_[1], "key": f"{k_[0]}|{k_[1]:.0f}"} for k_, v_ in decision.items()])
    if ends.empty:
        return {"feed_completeness": fc, "counts": cnt, "CH215": census_ch215(pd.DataFrame(), cnt, spec, fc, 0.0)}
    cap_slots = sorted(by_slot)
    lasts = np.array([capture_last_receipt(by_slot[k]["dir"]) for k in cap_slots])  # each capture's last row receipt (a timestamp column only)
    n_nr = int(np.isnan(lasts).sum())  # a capture with no readable receipt is never a decision capture (NaN < t is False); counted with its denominator (re-check item 1)
    cnt["captures_no_readable_receipt"] = {"n": n_nr, "of_captures": len(cap_slots), "share": n_nr / len(cap_slots) if cap_slots else float("nan"),
                                           "denominator": "sealed span captures whose largest row received_utc could not be read"}
    ends["dec_slot"] = [decision_slot(cap_slots, lasts, t) for t in ends["t_dec"]]
    cnt["no_decision_capture"] = int((ends["dec_slot"] < -10**8).sum())
    ends = ends[ends["dec_slot"] > -10**8].reset_index(drop=True)
    need_slots = set(ends["dec_slot"].astype(int))
    if not need_slots:
        return {"feed_completeness": fc, "counts": cnt, "CH215": census_ch215(pd.DataFrame(), cnt, spec, fc, 0.0)}
    carry = b.RewardCarry(int(spec["reward_carry_slots"]))
    nslot = int(spec["reward_carry_slots"])
    lo_k = min(need_slots) - nslot + 1 if need_slots else 0
    rows_out, cands = [], {}
    pool_stat = {"candidates_before": 0, "malformed_excluded": 0}
    for k in [s for s in cap_slots if lo_k <= s <= max(need_slots)]:
        cap = by_slot[k]
        write_series9(work, cap, spec)
        ser = read_series9(work, cap["id"])
        rw = b.read_rw8(work, cap["id"])
        if rw is not None:
            carry.add(k, rw)
        if k not in need_slots:
            continue
        sc = carry_frame(carry, ser, k, b._utc_day(cap["start"]))
        sc = sc.reset_index().rename(columns={"index": "market_id"}) if "market_id" not in sc.columns else sc.reset_index(drop=True)
        el = _eligible_single(sc.set_index("market_id"), spec, c["mid_lo"], c["mid_hi"], 0.0) & _cat_ok(sc)
        sc["el"] = el
        sc["cat"], sc["tier"], sc["tickk"] = cat_key(sc["fee_cat"]), tier_of(sc["liq"]), tick_key(sc["tick"])
        sc["loglq"] = np.log(np.where(sc["liq"].to_numpy(float) > 0, sc["liq"].to_numpy(float), np.nan))
        by_cond = sc[sc["condition_id"].astype(str) != ""].drop_duplicates("condition_id").set_index("condition_id")
        for e in ends[ends["dec_slot"] == k].itertuples(index=False):
            r = by_cond.loc[e.condition_id] if e.condition_id in by_cond.index else None
            rec = {"key": e.key, "found": r is not None}
            if r is None:
                rows_out.append(rec)
                continue
            end_ok = bool(np.isfinite(r["end_ts"]) and r["end_ts"] > e.T_e + c["market_end_margin_h"] * 3600.0)
            rec.update({"market_id": str(r["market_id"]), "event_id": str(r["event_id"]), "eligible": bool(r["el"]), "market_end_ok": end_ok, "end_unknown": bool(not np.isfinite(r["end_ts"])),
                        "market_end_h": float((r["end_ts"] - e.T_e) / 3600.0) if np.isfinite(r["end_ts"]) else float("nan")})
            rows_out.append(rec)
            if not (r["el"] and end_ok):
                continue
            f = ff(e.dec_feed)
            near = set()
            for cid2, js in zip(f.index, f["ends"], strict=True):
                if any(abs(x - e.T_e) <= c["control_exclusion_h"] * 3600.0 for x, _ in json.loads(js)):
                    near.add(str(cid2))
            malformed_cids = {str(c_) for c_ in f.index[(f["end_kind"] == "malformed").to_numpy()]} if len(f) else set()  # unknown end: may fall inside T_e +- 72 h (code check re-check item 4)
            pool0 = sc[sc["el"] & (sc["rewarded"] == 1.0) & (sc["cat"] == r["cat"]) & (sc["tier"] == r["tier"]) & (sc["tickk"] == r["tickk"])
                       & (sc["market_id"].astype(str) != str(r["market_id"])) & ~sc["condition_id"].astype(str).isin(near)]
            pool = pool0[~pool0["condition_id"].astype(str).isin(malformed_cids)]
            pool_stat["candidates_before"] += len(pool0)
            pool_stat["malformed_excluded"] += len(pool0) - len(pool)
            cands[e.key] = rank_control_candidates(pool, float(r["loglq"]))
    cnt["control_pool_malformed_excluded"] = {"candidates_excluded": pool_stat["malformed_excluded"], "candidates_before_exclusion": pool_stat["candidates_before"],
                                              "share": pool_stat["malformed_excluded"] / pool_stat["candidates_before"] if pool_stat["candidates_before"] else float("nan"),
                                              "denominator": "(qualifying end, control candidate) pairs passing the cell, eligibility and near-set rules, before the exclusion of markets whose feed end kind at the decision capture is malformed"}
    info = pd.DataFrame(rows_out)
    E = ends.merge(info, on="key", how="left")
    cnt["market_not_in_capture"] = int((~E["found"].fillna(False).astype(bool)).sum())
    E = E[E["found"].fillna(False).astype(bool)]
    cnt["not_eligible_at_decision"] = int((~E["eligible"].astype(bool)).sum())
    cnt["market_end_unknown"] = int((E["eligible"].astype(bool) & E["end_unknown"].astype(bool)).sum())
    cnt["market_end_within_48h"] = int((E["eligible"].astype(bool) & ~E["market_end_ok"].astype(bool) & ~E["end_unknown"].astype(bool)).sum())
    Q = E[E["eligible"].astype(bool) & E["market_end_ok"].astype(bool)].reset_index(drop=True)
    cnt["pre_window_decision"] = int((Q["t_dec"] < t0).sum()) if len(Q) else 0
    if len(Q):
        Q = assign_controls(Q, cands, int(c["max_controls"]), c["span_h"] * 3600.0)
        Q["cluster"] = end_clusters(Q)
        moved = []
        for e in Q.itertuples(index=False):
            last = None
            for fin, d in usable:
                if fin < e.T_e:
                    last = d
            f = ff(last) if last else None
            listed = bool(f is not None and e.condition_id in f.index and any(abs(x - e.T_e) < 1e-6 for x, _ in json.loads(f.loc[e.condition_id, "ends"])))
            moved.append(float(not listed) if f is not None else float("nan"))
        Q["end_moved"] = moved
        Q["day"] = pd.to_datetime(Q["T_e"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    days_cov = fc["slots_with_usable_feed"] / 12.0
    return {"declared_before_seal": spec.get("declared_before_seal"), "feed_completeness": fc, "inputs_verified": bool(verify), "files_checked": loaded.get("files_checked"), "counts": cnt,
            "CH215": census_ch215(Q, cnt, spec, fc, days_cov)}


def census_ch215(Q: pd.DataFrame, tot: dict, spec: dict, fc: dict, covered_days: float) -> dict:
    """CH215's entry gate CR9 (design 5, 7): every gate must pass for ``ch215.entered``; NaN fails."""
    g, a = spec["census_gates"]["CR9_CH215"], b.mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CR9_CH215"]
    scale = _scale(covered_days)
    if Q is None or Q.empty:
        res = b._gate_min_days({"error": "no qualifying ends", "gate_CH215": {"pass": False}}, "gate_CH215", covered_days, mind)
        res["entered"] = False
        return res
    n = len(Q)
    with_ctl = Q[Q["n_controls"] >= 1]
    ctl_share = len(with_ctl) / n
    ctl3_share = float((Q["n_controls"] >= 3).mean())
    day_top = float(Q["day"].value_counts(normalize=True).iloc[0])
    mv = Q["end_moved"].to_numpy(float)
    moved_share = float(np.nanmean(mv)) if np.isfinite(mv).any() else float("nan")
    proj_ends = float(n * scale)
    proj_clusters = float(Q["cluster"].nunique() * scale)
    cl = with_ctl["cluster"].astype(str).value_counts().to_numpy(float)
    m = float((cl ** 2).sum() / cl.sum()) if len(cl) else float("nan")
    de_v = 1.0 + (m * scale - 1.0) * float(a["de_rho"]) if np.isfinite(m) else float("nan")
    de_gate = float(max(g["de_floor"], de_v)) if np.isfinite(de_v) else float("nan")
    n_eff = float(len(with_ctl) * scale)
    sd = a[g["sd"]]
    declared = a["t_sum"] * sd * math.sqrt(2.0 / n_eff) * math.sqrt(de_gate) * a["day_factor"] * math.sqrt(g["vif_w"]) * 100.0 if n_eff > 0 and np.isfinite(de_gate) else float("inf")
    N, rho = n_eff, float(a["de_rho"])
    se_mean = math.sqrt((1 - rho) * N + rho * float(((cl * scale) ** 2).sum())) / N if N > 0 else float("nan")
    design = a["t_sum"] * a["day_factor"] * sd * math.sqrt(2.0) * se_mean * 100.0 if np.isfinite(se_mean) else float("inf")
    mde_c = float(max(declared, design)) if np.isfinite(declared) else float("inf")
    res = {"qualifying_ends": n, "projected_ends_21d": proj_ends, "ends_per_day": proj_ends / 21.0, "projected_clusters_21d": proj_clusters, "control_share_ge1": ctl_share,
           "control_share_ge3": ctl3_share, "one_day_top_share": day_top, "end_moved_share": moved_share, "design_effect": {"m_census": m, "DE": de_v, "DE_gate": de_gate},
           "mde": {"declared_c": declared, "design_c": design, "mde_c": mde_c, "n_eff_projected": n_eff}, "feed_completeness": fc,
           "ends_per_day_census": {str(k_): int(v_) for k_, v_ in Q["day"].value_counts().sort_index().items()},
           "hours_to_market_end_quantiles": b._q(Q.get("market_end_h", pd.Series(dtype=float))), "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    gate = {"feed_completeness": bool(fc["ok"]), "ends": proj_ends >= g["ends_projected_min"], "clusters": proj_clusters >= g["clusters_projected_min"],
            "controls": bool(ctl_share >= g["control_share_min"]), "one_day": bool(day_top <= g["one_day_share_max"]),
            "end_moved": bool(np.isfinite(moved_share) and moved_share <= g["end_moved_share_max"]), "mde": bool(mde_c <= a["mde_max"] * 100.0)}
    res["gate_CH215"] = b._gate(gate)
    res = b._gate_min_days(res, "gate_CH215", covered_days, mind)
    res["entered"] = bool(res["gate_CH215"]["pass"])
    return res


# --- the LT9 seal (a fresh seal of the span's captures, sweeps and feed captures; design 7, 8.4 step 4) ---------------------------------


def _span_slots(spec: dict) -> list[int]:
    ci = spec["census_inputs"]
    k0 = b.slot_of(epoch(ci["span"]["first_slot_utc"]), spec)
    k1 = b.slot_of(epoch(ci["span"]["last_slot_utc"]), spec)
    return list(range(k0, k1 + 1))


def seal_windows(spec: dict) -> dict:
    """The sealed slot ranges (design 7): captures from 12 slots before the span to 2 slots after it (the lag passes' token keys and capture k's
    start of CH214's last origins); sweeps from 2 passes before to 2 passes after; feed captures STARTING in [span start - feed look-back, the
    sealed bound)."""
    ci = spec["census_inputs"]
    sl = _span_slots(spec)
    return {"captures": (sl[0] - ci["lookback_capture_slots"], sl[-1] + ci["lag_passes_after"]), "sweeps": (sl[0] - ci["lookback_sweep_passes"], sl[-1] + ci["lag_passes_after"]),
            "feed": (epoch(ci["span"]["start_utc"]) - ci["feed_lookback_h"] * 3600.0, epoch(ci["refuse_at_or_after_utc"]))}


def seal_inputs(*, snapshot_root, sweep_root, feed_root, work: Path, spec: dict | None = None, unavailable=None, design_path: Path | None = None) -> dict:
    """The LT9 seal (design 7): every complete capture (rows, manifest, sidecar), sweep 1 (rows, manifest) and feed capture (manifest, rows when
    present, failed ones included so that a skipped capture is visible) in the sealed windows, found in the roots (host copies first, then restore
    trees), each hashed. A directory found in two roots with different bytes refuses (never substituted). Records the seal's own slot assignment, the
    frozen design-text sha256 (the seal is written only after the freeze) and the spec's census blocks. Missing slots are counted, never filled."""
    spec = spec or load_spec(sha=None)
    if (derr := design_text_error(design_path)):
        return derr
    if (rerr := reward_rule_error(spec)):
        return rerr
    win = seal_windows(spec)
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    by_slot, sweeps = b._scan(Path(work), snapshot_root, sweep_root, spec)
    files, slots, conflicts = {}, {}, []

    def other_roots(sub_roots, d: str, fn: str, first: Path) -> list[Path]:
        return [Path(r) / d / fn for r in b._roots(sub_roots) if (Path(r) / d / fn).exists() and (Path(r) / d) != Path(first)]

    def put(rel: str, p: Path, roots, d: str, kind: str, extra: dict | None = None) -> None:
        h = sha256_file(p)
        for q in other_roots(roots, d, p.name, p.parent):
            if sha256_file(q) != h:
                conflicts.append({"file": rel, "root_a": str(p), "root_b": str(q)})
        files[rel] = {"sha256": h, "root": str(p.parent.parent), "kind": kind, **(extra or {})}

    caps_k = sorted(k for k in by_slot if win["captures"][0] <= k <= win["captures"][1])
    for k in caps_k:
        c = by_slot[k]
        if c["start"] >= bound:
            continue
        for rel, p in b.capture_files(c["dir"]):
            put(rel, p, snapshot_root, c["id"], "capture", {"capture": c["id"]})
        slots[c["id"]] = iso(b.slot_time(k, spec))
    sw_k = sorted(k for k in by_slot if win["sweeps"][0] <= k <= win["sweeps"][1] and by_slot[k]["id"] in sweeps)
    for k in sw_k:
        v = sweeps[by_slot[k]["id"]]
        for rel, p in b.sweep_files(v["dir"]):
            put(rel, p, sweep_root, Path(v["dir"]).name, "sweep", {"capture": by_slot[k]["id"]})
        slots[Path(v["dir"]).name] = iso(b.slot_time(k, spec))
    feeds = scan_feed(feed_root)
    feed_meta = {}
    for d, v in sorted(feeds.items()):
        if not (win["feed"][0] <= v["start"] < win["feed"][1]):
            continue
        for fn in ("manifest.json", "rows.jsonl.gz"):
            p = Path(v["dir"]) / fn
            if p.exists():
                put(f"data-dumps/research_lab/reward_params/{d}/{fn}", p, feed_root, d, "feed")
        feed_meta[d] = {"started_utc": iso(v["start"]), "finished_utc": iso(v["finish"]), "state": v["state"], "usable": v["usable"]}
    if conflicts:
        return {"error": "a sealed directory exists in two roots with different bytes: LT9 seal refused", "conflicts": conflicts[:50], "n_conflicts": len(conflicts)}
    bad = [d for d, s in slots.items() if epoch(s) >= bound]
    if bad:
        return {"error": "a sealed slot is at or after the sealed bound: refused", "bad": bad[:20]}
    span = _span_slots(spec)
    cap_need = range(win["captures"][0], win["captures"][1] + 1)
    sw_need = range(win["sweeps"][0], win["sweeps"][1] + 1)
    miss_c = [iso(b.slot_time(k, spec)) for k in cap_need if k not in caps_k]
    miss_s = [iso(b.slot_time(k, spec)) for k in sw_need if k not in sw_k]
    unavail = sorted(b.load_unavailable(unavailable)) if unavailable else []
    return {"purpose": "LT9 census inputs (LIVE_TESTS_9.md section 7): every capture, sweep 1 and reward_params capture the censuses may open, each hashed; counts-only use",
            "written_utc": iso(b.now_ts()), "spec_sha256": sha256_file(SPEC_PATH), "design_text_sha256": design_text_sha(design_path), "spec_blocks_sha256": spec_blocks_sha(spec),
            "span": spec["census_inputs"]["span"], "refuse_at_or_after_utc": spec["census_inputs"]["refuse_at_or_after_utc"], "windows": {k_: [v_[0], v_[1]] for k_, v_ in win.items()},
            "slots": dict(sorted(slots.items())), "feed": feed_meta, "needs": {"captures": len(caps_k), "sweeps": len(sw_k), "feed_captures": len(feed_meta),
            "feed_usable": sum(1 for v in feed_meta.values() if v["usable"])}, "span_slots": len(span), "missing": {"captures": miss_c, "sweeps": miss_s},
            "n_missing": {"captures": len(miss_c), "sweeps": len(miss_s)}, "unavailable_declared": unavail, "n_files": len(files), "files": dict(sorted(files.items()))}


def bound_violations(seal: dict, spec: dict) -> list[dict]:
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = [{"what": d, "value": s, "error": "at or after the sealed bound"} for d, s in (seal.get("slots") or {}).items() if epoch(s) >= bound]
    bad += [{"what": d, "value": v.get("started_utc"), "error": "feed capture at or after the sealed bound"} for d, v in (seal.get("feed") or {}).items() if epoch(v["started_utc"]) >= bound]
    if seal.get("written_utc") is None:
        bad.append({"what": "written_utc", "error": "seal not stamped"})
    return bad


def _sealed_feeds(seal: dict, feed_root) -> tuple[dict, list[dict]]:
    """Sealed feed captures found locally (each sealed file present and hash-equal), else bad. A local feed directory the seal does not name is
    never opened."""
    found = scan_feed(feed_root, only=set(seal.get("feed") or {}))
    out, bad = {}, []
    for d, meta in (seal.get("feed") or {}).items():
        rels = [r for r in seal["files"] if r.startswith(f"data-dumps/research_lab/reward_params/{d}/")]
        v = found.get(d)
        if v is None:
            bad.append({"dir": d, "error": "sealed feed capture is absent from every root"})
            continue
        for rel in rels:
            p = Path(v["dir"]) / rel.rsplit("/", 1)[1]
            if not p.exists():
                bad.append({"file": rel, "error": "sealed but absent locally"})
            elif sha256_file(p) != seal["files"][rel]["sha256"]:
                bad.append({"file": rel, "error": "sha256 mismatch"})
        rows_sealed = any(r.endswith("rows.jsonl.gz") for r in rels)
        out[d] = {**v, "start": epoch(meta["started_utc"]), "finish": epoch(meta["finished_utc"]), "state": meta["state"], "usable": bool(meta["usable"] and rows_sealed)}
    return out, bad


def sealed_slot_maps(seal: dict, spec: dict) -> tuple[dict, dict]:
    """(capture slot -> sealed dir names, sweep slot -> sealed dir names) from the seal's OWN slot assignment (never from a local scan)."""
    caps, sws = b.sealed_dirs(seal, "snapshots"), b.sealed_dirs(seal, "book_sweeps")

    def to(names) -> dict:
        out: dict[int, set[str]] = {}
        for d in names:
            k = b.slot_of(epoch(seal["slots"][d]), spec) if d in seal.get("slots", {}) else None
            if k is not None:
                out.setdefault(k, set()).add(d)
        return out

    return to(caps), to(sws)


def _load_for_census(seal: Path, snapshot_root, sweep_root, feed_root, work: Path, spec: dict, need_sweeps: bool = True, verify: bool = True, design_path: Path | None = None) -> dict:
    """The refusals every census runs first: the frozen design text, the seal's design hash, the sealed bound, the seal-time spec blocks, the reward
    rule, an empty work dir; then every sealed capture / sweep / feed capture must be present locally with every sealed file hash-equal, and the scan
    must pick the sealed directory for each sealed slot (else refused, L3)."""
    seal_d = json.loads(Path(seal).read_text())
    if (derr := design_text_error(design_path)):
        return derr
    if seal_d.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        return {"error": "the seal was written against a different LIVE_TESTS_9.md: census refused", "seal_design_text_sha256": seal_d.get("design_text_sha256")}
    if (viol := bound_violations(seal_d, spec)):
        return {"error": "sealed bound violated: census refused", "bad": viol[:20]}
    if seal_d.get("spec_blocks_sha256") != spec_blocks_sha(spec):
        return {"error": "the spec's census blocks differ from those at seal time: census refused", "seal_blocks_sha256": seal_d.get("spec_blocks_sha256"), "spec_blocks_sha256": spec_blocks_sha(spec)}
    if (rerr := reward_rule_error(spec)):
        return rerr
    w = Path(work)
    if w.exists() and any(w.iterdir()):
        return {"error": f"work directory {w} is not empty: a stale series file would be reused (census refused)"}
    by_slot, sweeps = b._scan(w, snapshot_root, sweep_root if need_sweeps else [], spec)
    sc, ss = sealed_slot_maps(seal_d, spec)
    bad = []
    for k, names in sorted(sc.items()):
        cc = by_slot.get(k)
        if cc is None:
            bad.append({"slot": k, "sealed": sorted(names), "error": "sealed capture is absent from every root"})
        elif cc["id"] not in names:
            bad.append({"slot": k, "sealed": sorted(names), "scanned": cc["id"], "error": "the scanned capture differs from the sealed one"})
    by_slot = {k: v for k, v in by_slot.items() if k in sc and v["id"] in sc[k]}
    if need_sweeps:
        names_sw = {Path(v["dir"]).name for v in sweeps.values()}
        for k, names in sorted(ss.items()):
            for d in sorted(names - names_sw):
                bad.append({"slot": k, "sealed": d, "error": "sealed sweep 1 is absent from every root"})
        sweeps = {sid: v for sid, v in sweeps.items() if Path(v["dir"]).name in {d for n in ss.values() for d in n}}
    else:
        sweeps = {}
    files_checked = 0
    if verify:
        # LT8's completeness check (code check 2026-10-23 must-fix 1): EVERY sealed file of a sealed capture / sweep (the optional sidecar included) must
        # be present locally, else the census is refused; the vendored ``capture_files`` skips a missing ``rows_ext``, so ``verify_files`` alone cannot see it.
        cap_slots_s, sw_slots_s = set(sc), (set(ss) if need_sweeps else set())
        if cap_slots_s or sw_slots_s:
            comp = b.seal_completeness(seal_d, by_slot, sweeps if need_sweeps else {}, cap_slots_s, sw_slots_s, spec, sweep_root if need_sweeps else None)
            bad += comp["bad"]
            files_checked = comp["files_checked"]
    feeds, fbad = _sealed_feeds(seal_d, feed_root)
    bad += fbad
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    return {"seal": seal_d, "by_slot": by_slot, "sweeps": sweeps, "feeds": feeds, "files_checked": files_checked}


# --- CC9's reward-field descriptives (section 7: counts only, no gate; descriptive for LT7 and LT8, never changes their controls) --------


def reward_field_counts(sc: pd.DataFrame, feed_k: pd.DataFrame | None, day: str, acc: dict) -> None:
    """Accumulate, for one span capture (its carried frame ``sc``, the two-sided series rows) restricted to non-sports ex-crypto rows: the null
    taxonomy (``rew_state``), the vendored carry counts (``_reward_cols``: lags 1 / 2-3 / 4-11, listed-inactive, carried_param_differs, switching), the
    carry-versus-feed agreement table by day (carry-rewarded x CLOB-listed at the last usable feed capture before the capture), the two-ledger map
    (listed and rewarded; listed and carry-unrewarded; carry-rewarded and CLOB-absent, the ghost; band and rate mismatches where both list it), the
    per-market listed-and-unrewarded tally for the whole span (hidden programme) and the omitted slots per market-day. No price is read."""
    m = _cat_ok(sc)
    x = sc[m]
    tax = acc.setdefault("null_taxonomy", {})
    for k_, v_ in x["rew_state"].astype(str).value_counts().items():
        tax[k_] = tax.get(k_, 0) + int(v_)
    cnt: dict = {}
    if len(x):
        b._reward_cols(x, cnt)
    b._merge_counts(acc.setdefault("carry_counts", {}), cnt)
    rew = x["rewarded"].to_numpy(float)
    cond = x["condition_id"].astype(str).to_numpy()
    listed = np.isin(cond, feed_k.index.to_numpy()).astype(float) if feed_k is not None else np.full(len(x), np.nan)
    t = acc.setdefault("carry_x_feed_by_day", {}).setdefault(day, {"r1_l1": 0, "r1_l0": 0, "r0_l1": 0, "r0_l0": 0, "r_nan": 0, "feed_missing": 0})
    fin = np.isfinite(rew)
    t["r_nan"] += int((~fin).sum())
    if feed_k is None:
        t["feed_missing"] += int(fin.sum())
    else:
        for a_, c_ in ((1, 1), (1, 0), (0, 1), (0, 0)):
            t[f"r{a_}_l{c_}"] += int((fin & (rew == a_) & (listed == c_)).sum())
        f = feed_k.reindex(cond)
        both = fin & (rew == 1) & (listed == 1)
        v, fb = x["rew_maxspread"].to_numpy(float), f["band"].to_numpy(float)
        r_, fr = x["rew_rate"].to_numpy(float), f["rate"].to_numpy(float)
        with np.errstate(invalid="ignore"):
            lm = acc.setdefault("two_ledger", {"listed_rewarded": 0, "listed_carry_unrewarded": 0, "ghost": 0, "band_mismatch": 0, "rate_mismatch": 0, "both_listed": 0})
            lm["listed_rewarded"] += int(both.sum())
            lm["listed_carry_unrewarded"] += int((fin & (rew == 0) & (listed == 1)).sum())
            lm["ghost"] += int((fin & (rew == 1) & (listed == 0)).sum())
            lm["both_listed"] += int(both.sum())
            lm["band_mismatch"] += int((both & np.isfinite(v) & np.isfinite(fb) & (np.abs(v - fb) > 1e-9)).sum())
            lm["rate_mismatch"] += int((both & np.isfinite(r_) & np.isfinite(fr) & (np.abs(r_ - fr) > 1e-6 * np.maximum(1.0, np.abs(fr)))).sum())
        hid = acc.setdefault("hidden", {})
        ids = x.index.astype(str) if x.index.name == "market_id" else x["market_id"].astype(str)
        for mid_, lu, seen in zip(ids, (fin & (rew == 0) & (listed == 1)), fin, strict=True):
            if seen:
                h = hid.setdefault(mid_, [0, 0])
                h[0] += int(lu)
                h[1] += 1
    om = x["om"].to_numpy(float)
    ids = x.index.astype(str) if x.index.name == "market_id" else x["market_id"].astype(str)
    md = acc.setdefault("om_market_day", {})
    for mid_, o in zip(ids, om, strict=True):
        if o == 1.0:
            md[(mid_, day)] = md.get((mid_, day), 0) + 1


def reward_field_summary(acc: dict) -> dict:
    hid = acc.get("hidden", {})
    md = acc.get("om_market_day", {})
    hist = {"1": 0, "2": 0, "ge3": 0}
    for v in md.values():
        hist["1" if v == 1 else ("2" if v == 2 else "ge3")] += 1
    return {"null_taxonomy": acc.get("null_taxonomy", {}), "carry_counts": acc.get("carry_counts", {}), "carry_x_feed_by_day": acc.get("carry_x_feed_by_day", {}),
            "two_ledger_map": {**acc.get("two_ledger", {}), "hidden_programme_markets_whole_span": int(sum(1 for a_, n_ in hid.values() if n_ and a_ == n_))},
            "omitted_slots_per_market_day": hist, "seen_before_T_LT7_note": "descriptive; changes no LT7 or LT8 control; recorded in the ledger as seen before T_LT7 (10)"}


# --- CC9 and CS9 (the streaming census loops) ---------------------------------------------------------------------------------------


def _fee_ok(fee_counts: dict) -> dict:
    return b.crypto_failsafe(fee_counts)


def census_captures(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, feed_root=FEED_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CC9: CH213 and CH212 on the sealed captures and feed captures (counts only). Streaming one capture at a time with the 12-slot carry window per
    market, a 13-slot mid store and the k - 1 / k carried frames. Twins: CH213's through :func:`lag_break_flag` (captures k + 4, k + 5; the flag only),
    CH212's ``om_{k+4}`` = the carry status of capture k + 4 (a status only). No target is formed."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    loaded = _load_for_census(seal, snapshot_root, [], feed_root, work, spec, need_sweeps=False, verify=verify)
    if "error" in loaded:
        return loaded
    by_slot, feeds = loaded["by_slot"], loaded["feeds"]
    span = _span_slots(spec)
    cap_slots = set(by_slot)
    ORG = [k for k in span if k in cap_slots and (k - 1) in cap_slots]
    nslot = int(spec["reward_carry_slots"])
    loop = sorted(s for s in cap_slots if (min(ORG) - nslot if ORG else 0) <= s <= (max(ORG) + 5 if ORG else -1))
    carry = b.RewardCarry(nslot)
    store = b.MidStore()
    frames: dict[int, pd.DataFrame] = {}
    om_status: dict[int, pd.Series] = {}
    fee_counts: dict = {}
    switch: dict[str, dict[str, set]] = {}
    U213, U212, tot213, tot212 = [], [], {}, {}
    v_rewarded: list[np.ndarray] = []
    feed_frames: dict[str, pd.DataFrame] = {}
    persist = {"broken_km2": 0, "broken_km1_given_km2": 0}
    rf_acc: dict = {}
    ends_acc = {"feed_captures_read": 0, "listed_markets": 0, "positive_configs": 0, "end_date_only": 0, "end_sentinel": 0,
                "malformed_markets": 0, "malformed_mixed_markets": 0}
    ends_counted: set[str] = set()
    cells5: dict[int, dict] = {}  # control_cells of capture k + 5 (medians and counts of the served band only), for the control twin's v_ctrl

    def fframe(d: str | None) -> pd.DataFrame | None:
        if d is None:
            return None
        if d not in feed_frames:
            feed_frames[d] = f = feed_frame(feeds[d]["dir"], spec)
            if d not in ends_counted:  # frames are evicted and can be re-read: count each capture once
                ends_counted.add(d)
                ends_acc["feed_captures_read"] += 1
                ends_acc["listed_markets"] += int(len(f))
                ends_acc["positive_configs"] += int(f["n_pos"].sum()) if len(f) else 0
                ends_acc["end_date_only"] += int(f["n_date_only"].sum()) if len(f) else 0
                ends_acc["end_sentinel"] += int(f["n_sentinel"].sum()) if len(f) else 0
                ends_acc["malformed_markets"] += int((f["end_kind"] == "malformed").sum()) if len(f) else 0
                ends_acc["malformed_mixed_markets"] += int(f["mixed_malformed"].sum()) if len(f) else 0
            for old in list(feed_frames)[:-FEED_CACHE_FRAMES]:
                feed_frames.pop(old)
        return feed_frames[d]

    org_set = set(ORG)
    for k in loop:
        cap = by_slot[k]
        write_series9(work, cap, spec)
        ser = read_series9(work, cap["id"])
        rw = b.read_rw8(work, cap["id"])
        if rw is not None:
            carry.add(k, rw)
            day = b._utc_day(cap["start"])
            if k in span:
                sd = switch.setdefault(day, {"null": set(), "listed": set()})
                st = rw["rew_status"].astype(str)
                sd["null"] |= set(rw.index[st == "null"].astype(str))
                sd["listed"] |= set(rw.index[st == "listed"].astype(str))
        store.add(k, ser)
        b._fee_counts(ser, fee_counts)
        sc = carry_frame(carry, ser, k, b._utc_day(cap["start"]))
        frames[k] = sc
        if (k - 5) in org_set:
            cells5[k] = control_cells(sc, spec)
        om_status[k] = pd.Series(sc["om"].to_numpy(float), index=sc.index.astype(str))
        for old in [s_ for s_ in frames if s_ < k - 2]:
            frames.pop(old)
        for old in [s_ for s_ in store.slots if s_ < k - 12]:
            store.slots.pop(old)
        if k in span:
            rr = sc["rewarded"].to_numpy(float) == 1.0
            v_rewarded.append(sc["rew_maxspread"].to_numpy(float)[rr & _cat_ok(sc)])
            reward_field_counts(sc, fframe(last_usable_before(feeds, cap["start"])), b._utc_day(cap["start"]), rf_acc)
        if k in org_set and (k - 1) in frames:
            cells = control_cells(sc, spec)
            u, cnt = bandbreak_units(sc, frames[k - 1], store, cap, k, spec, cells)
            b._merge_counts(tot213, cnt)
            if len(u):
                U213.append(u)
            fk = last_usable_before(feeds, cap["start"])
            fp = last_usable_before(feeds, by_slot[k - 1]["start"])
            u2, cnt2 = rwblink_units(sc, frames[k - 1], store, cap, k, spec, fframe(fk), fframe(fp))
            b._merge_counts(tot212, cnt2)
            if len(u2):
                U212.append(u2)
    fs = _fee_ok(fee_counts)
    if not fs["classifier_shown_to_work"]:
        return {"error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    A = pd.concat(U213, ignore_index=True) if U213 else pd.DataFrame()
    if len(A):  # CH213 twin flags (captures k + 4 and k + 5 through the loader; the flag only)
        tw = []
        for k, grp in A.groupby("slot"):
            k = int(k)
            if (k + 4) in by_slot and (k + 5) in by_slot:
                tw.append(lag_twin_flags(by_slot[k + 4]["dir"], by_slot[k + 5]["dir"], grp, cells5.get(k + 5), spec))
            else:
                tw.append(pd.Series(np.nan, index=grp.index))
        A["brk_twin"] = pd.concat(tw).reindex(A.index).to_numpy(float)
        key = A.set_index(["market_id", "slot"])["brk"]
        prev = pd.Series(key.to_numpy(), index=pd.MultiIndex.from_arrays([key.index.get_level_values(0), key.index.get_level_values(1) + 1]))
        both = prev.reindex(key.index)
        m = np.isfinite(both.to_numpy(float))
        persist["broken_km2"] = int((both.to_numpy(float)[m] == 1).sum())
        persist["broken_km1_given_km2"] = int(((both.to_numpy(float)[m] == 1) & (key.to_numpy(float)[m] == 1)).sum())
    A, pcnt = cap_then_panel(A, spec["member_cap"]["max_members"])
    b._merge_counts(tot213, pcnt)
    tot213["persist_pooled"] = {**persist, "share": persist["broken_km1_given_km2"] / persist["broken_km2"] if persist["broken_km2"] else float("nan")}
    B = pd.concat(U212, ignore_index=True) if U212 else pd.DataFrame()
    if len(B):
        B["om_twin"] = [float(om_status[s + 4].get(m_, np.nan)) if (s + 4) in om_status else np.nan for m_, s in zip(B["market_id"].astype(str), B["slot"].astype(int), strict=True)]
    days = len(ORG) / 12.0
    pair_days = len([k for k in ORG if (k + 4) in cap_slots and (k + 5) in cap_slots]) / 12.0
    band = band_unit_check(np.concatenate(v_rewarded) if v_rewarded else [], spec)
    fc = feed_completeness(feeds, span, spec)
    sw_counts = {d: len(v["null"] & v["listed"]) for d, v in sorted(switch.items())}
    exp = spec["census_inputs"]["expected_origins"]
    return {"span": spec["census_inputs"]["span"], "inputs_verified": bool(verify), "files_checked": loaded["files_checked"], "fee_category_values": fs["distinct_values"],
            "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"], "reward_null_rule": spec.get("reward_null_rule"), "design_text_sha256": DESIGN_TEXT_SHA256,
            "covered_origins": {"CC9": len(ORG), "CH213_F_pairs": int(pair_days * 12)}, "expected_origins": exp.get("CC9"), "origins_differ_from_design": len(ORG) != exp.get("CC9"),
            "feed_completeness": fc, "band_unit_check": band, "reward_field": reward_field_summary(rf_acc), "overlaps_with_prior_populations": PRIOR_POPULATION_OVERLAPS,
            "declared_before_seal": spec.get("declared_before_seal"),
            "feed_end_kinds_of_positive_configs": {**ends_acc, "denominator": "positive-rate configurations of every sealed usable feed capture read by this census, each capture counted once (not market-level, not slot-level)",
                                                   "date_only_share": ends_acc["end_date_only"] / ends_acc["positive_configs"] if ends_acc["positive_configs"] else float("nan"),
                                                   "sentinel_share": ends_acc["end_sentinel"] / ends_acc["positive_configs"] if ends_acc["positive_configs"] else float("nan")},
            "unit_overlaps": b.unit_overlaps({"CH213": A[A["n_members"] <= spec["member_cap"]["max_members"]] if len(A) else A, "CH212": B[B["n_members"] <= spec["member_cap"]["max_members"]] if len(B) else B}),
            "CH213": census_ch213(A, tot213, spec, days, band, pair_days), "CH212": census_ch212(B, tot212, spec, days, fc, {"per_day": sw_counts})}


def census_sweeps(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, sweep_root=SWEEP_ROOT, feed_root=FEED_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CS9: CH214 on the sealed sweeps and captures (counts only). Origins k in the span with captures k - 2, k - 1, k (k: its manifest start only)
    and sweeps k - 2, k - 1 sealed; F pairs: origins whose sweeps k + 2, k + 3 are also sealed (read ONLY through :func:`lag_band_sums`)."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    loaded = _load_for_census(seal, snapshot_root, sweep_root, feed_root, work, spec, need_sweeps=True, verify=verify)
    if "error" in loaded:
        return loaded
    by_slot, sweeps = loaded["by_slot"], loaded["sweeps"]
    span = _span_slots(spec)
    cap_slots = set(by_slot)
    sw_slots = {k for k in cap_slots if by_slot[k]["id"] in sweeps}
    ORG = [k for k in span if {k - 2, k - 1, k} <= cap_slots and {k - 2, k - 1} <= sw_slots]
    PAIRS = {k for k in ORG if {k + 2, k + 3} <= sw_slots}
    nslot = int(spec["reward_carry_slots"])
    loop = sorted(s for s in cap_slots if (min(ORG) - nslot - 1 if ORG else 0) <= s <= (max(ORG) - 1 if ORG else -1))
    carry = b.RewardCarry(nslot)
    store = b.MidStore()
    frames: dict[int, pd.DataFrame] = {}
    cache: dict[int, pd.DataFrame] = {}
    fee_counts: dict = {}
    Qs, tot = [], {}
    v_rewarded: list[np.ndarray] = []
    pview = prior_spec_view(spec)
    ch197_slot = int(spec["prior_population_specs"]["LT7_CH197"]["test"]["slot_index_in_day"])
    raw: dict[int, pd.DataFrame] = {}
    U197, tot197 = [], {}
    c197 = {"passes": 0, "pass_sweep_unsealed": 0}

    def sw_of(j: int) -> pd.DataFrame | None:
        if j not in sw_slots:
            return None
        if j not in cache:
            cache[j] = b.sweep_frame(sweeps[by_slot[j]["id"]]["dir"], by_slot[j]["dir"]).set_index("market_id")
        return cache[j]

    org_set = set(ORG)
    for s in loop:
        cap = by_slot[s]
        write_series9(work, cap, spec)
        ser = read_series9(work, cap["id"])
        rw = b.read_rw8(work, cap["id"])
        if rw is not None:
            carry.add(s, rw)
        store.add(s, ser)
        b._fee_counts(ser, fee_counts)
        sc = carry_frame(carry, ser, s, b._utc_day(cap["start"]))
        frames[s] = sc
        raw[s] = ser
        for old in [x for x in raw if x < s - 1]:
            raw.pop(old)
        if s in span and b.slot_in_day(s) == ch197_slot and (s + 1) in org_set and (s - 1) in raw:  # LT7 CH197's pass k = s (its sweep is origin s + 1's sweep k - 1)
            c197["passes"] += 1
            sw_s = sw_of(s)
            if sw_s is None:
                c197["pass_sweep_unsealed"] += 1
            u197, cnt197 = b.patient_units(sc.assign(osz=np.nan), raw[s - 1], store, sw_s, cap, s, pview)  # osz (order_min_size) is a bookkeeping column of LT7's frame, no unit filter; CS9 does not read it
            b._merge_counts(tot197, cnt197)
            if len(u197):
                U197.append(u197)
        if s in span:
            rr = sc["rewarded"].to_numpy(float) == 1.0
            v_rewarded.append(sc["rew_maxspread"].to_numpy(float)[rr & _cat_ok(sc)])
        for old in [x for x in frames if x < s - 2]:
            frames.pop(old)
        for old in [x for x in store.slots if x < s - 12]:
            store.slots.pop(old)
        for old in [x for x in cache if x < s - 1]:
            cache.pop(old)
        k = s + 1  # the origin whose capture k - 1 is s (decision at sweep k - 1's receipt; capture k gives its manifest start only)
        if k in org_set and (s - 1) in frames:
            q, cnt = pool_units(sc, frames[s - 1], store, sw_of(s - 1), sw_of(s), cap, by_slot[k]["start"], k, spec)
            b._merge_counts(tot, cnt)
            if len(q):
                Qs.append(q)
    fs = _fee_ok(fee_counts)
    if not fs["classifier_shown_to_work"]:
        return {"error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    Q = pd.concat(Qs, ignore_index=True) if Qs else pd.DataFrame()
    if len(Q):  # the F twin through the sizes-only loader
        parts = []
        for k, grp in Q.groupby("slot"):
            k = int(k)
            if k in PAIRS:
                l2 = lag_band_sums(sweeps[by_slot[k + 2]["id"]]["dir"], by_slot[k + 2]["dir"])
                l3 = lag_band_sums(sweeps[by_slot[k + 3]["id"]]["dir"], by_slot[k + 3]["dir"])
                parts.append(add_pool_lag(grp, l2, l3, spec))
            else:
                parts.append(add_pool_lag(grp, None, None, spec))
        Q = pd.concat(parts).sort_index()
    days, pair_days = len(ORG) / 12.0, len(PAIRS) / 12.0
    band = band_unit_check(np.concatenate(v_rewarded) if v_rewarded else [], spec)
    exp = spec["census_inputs"]["expected_origins"]
    cap_max = spec["member_cap"]["max_members"]
    ch214_keys = day_keys(Q[Q["n_members"] <= cap_max] if len(Q) else Q)
    ch197_keys = day_keys(pd.concat(U197, ignore_index=True) if U197 else pd.DataFrame())
    overlaps = {"LT8_CH203": CS9_CH203_UNAVAILABLE,
                "LT7_CH197": {"key": "(market, UTC day)", "passes_12_31Z_in_span_with_sweep_read": c197["passes"], "pass_sweep_unsealed": c197["pass_sweep_unsealed"],
                              "units_ch197": int(sum(len(u_) for u_ in U197)), "counts": {k_: v_ for k_, v_ in tot197.items() if isinstance(v_, (int, float))},
                              **b.unit_overlaps({"CH214": ch214_keys, "CH197": ch197_keys}).get("CH197&CH214", {"units": 0})}}
    return {"inputs_verified": bool(verify), "files_checked": loaded["files_checked"], "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"],
            "overlaps_with_prior_populations": overlaps,
            "reward_null_rule": spec.get("reward_null_rule"), "design_text_sha256": DESIGN_TEXT_SHA256, "covered_origins": {"CS9": len(ORG), "CS9_F_pairs": len(PAIRS)}, "declared_before_seal": spec.get("declared_before_seal"),
            "expected_origins": exp.get("CS9"), "origins_differ_from_design": len(ORG) != exp.get("CS9"), "band_unit_check": band,
            "CH214": census_ch214(Q, tot, spec, days, pair_days, band)}


# --- header pre-check (headers only, no rows; design 7) -----------------------------------------------------------------------------


def header_precheck(*, capture_dir: Path | None = None, sweep_dir: Path | None = None, feed_dir: Path | None = None, spec: dict | None = None) -> dict:
    """The fields each stream must carry (spec ``census_inputs.header_precheck``): CSV headers are read with ``nrows=0``; for the feed only the KEY
    NAMES of the first record and of its first configuration are returned (no value). A missing field makes the dependent quantity NaN."""
    spec = spec or load_spec(sha=None)
    want = spec["census_inputs"]["header_precheck"]
    out: dict = {}

    def cols(p: Path) -> list[str]:
        return list(pd.read_csv(p, nrows=0).columns) if p.exists() else []

    if capture_dir is not None:
        out["rows_missing"] = sorted(set(want["rows"]) - set(cols(Path(capture_dir) / "rows.csv.gz")))
        out["sidecar_missing"] = sorted(set(want["sidecar"]) - set(cols(Path(capture_dir) / "rows_ext.csv.gz")))
        m = Path(capture_dir) / "manifest.json"
        out["manifest_missing"] = sorted(set(want["manifest"]) - set(json.loads(m.read_text()).keys())) if m.exists() else list(want["manifest"])
    if sweep_dir is not None:
        out["sweep_missing"] = sorted(set(want["sweeps"]) - set(cols(Path(sweep_dir) / "rows.csv.gz")))
    if feed_dir is not None:
        keys, ckeys = set(), set()
        p = Path(feed_dir) / "rows.jsonl.gz"
        if p.exists():
            with gzip.open(p, "rt") as fh:
                for line in fh:
                    r = json.loads(line)
                    keys = set(r)
                    cfg = r.get(spec["feed"]["configs_field"])
                    ckeys = set(cfg[0]) if isinstance(cfg, list) and cfg and isinstance(cfg[0], dict) else set()
                    break
        out["feed_missing"] = sorted(set(want["feed"]) - keys)
        out["feed_config_missing"] = sorted(set(want["feed_config"]) - ckeys)
        m = Path(feed_dir) / "manifest.json"
        out["feed_manifest_missing"] = sorted({"state", "started_utc", "finished_utc"} - set(json.loads(m.read_text()).keys())) if m.exists() else ["manifest"]
    out["ok"] = not any(v for k_, v in out.items() if k_.endswith("missing"))
    return out


# --- operational counts (never reads a price, a move, a state value or a target) ----------------------------------------------------


def _read_ops(path: Path, cols: list[str]) -> pd.DataFrame:
    bad = [c for c in cols if c not in OPS_COLS]
    if bad:
        raise ValueError(f"ops_stats may not read {bad}")
    head = pd.read_csv(path, nrows=0).columns
    use = [c for c in cols if c in head]
    return pd.read_csv(path, usecols=use) if use else pd.DataFrame()


def ops_stats(root: Path = OUT_ROOT) -> dict:
    """File, line, role, panel, route and status counts of ``live_tests9/`` (design 1.6: the only thing that may run before the analysis date). The
    reader (phase 2) writes the files; this reads only the ``OPS_COLS`` columns."""
    root = Path(root)
    out: dict = {"root": str(root), "bytes": b.dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "sweeps", "feed", *(f"{k}/frozen" for k in KINDS), *(f"{k}/outcomes" for k in KINDS)):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith(MARKERS)]), **{s.split(".")[1]: len([f for f in files if f.name.endswith(s)]) for s in MARKERS}}
    counts, status = {}, {}
    cols = {"bandbreak": ["role", "panel", "sports", "crypto", "capflag", "lookback"], "pool": ["role", "sports", "crypto", "capflag", "lookback"],
            "rwblink": ["role", "route", "sports", "crypto", "capflag", "lookback"], "rwend": ["role", "sports", "crypto"]}
    for kind, cl in cols.items():
        d = root / kind / "frozen"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            if f.name.endswith(MARKERS):
                continue
            s = _read_ops(f, cl)
            for c in s.columns:
                for k_, v in s[c].value_counts().items():
                    counts[f"{kind}:{c}:{k_}"] = counts.get(f"{kind}:{c}:{k_}", 0) + int(v)
        d = root / kind / "outcomes"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            tag = f.name[:-7].rsplit(".", 1)[-1]
            s = _read_ops(f, ["status"])
            if "status" in s:
                for k_, v in s["status"].value_counts().items():
                    status[f"{kind}:{tag}:{k_}"] = status.get(f"{kind}:{tag}:{k_}", 0) + int(v)
    out.update(line_counts=counts, outcome_status_counts=status)
    return out


cleanup_census = b.cleanup_census
