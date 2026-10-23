# ruff: noqa: E501
"""LIVE prospective tests LT12 (docs/research_lab/LIVE_TESTS_12.md, design text frozen at sha256 a543db63...): the mirror and the farmed half, CH245 (the
dense book's spread innovation and the thin book's next spread change, two-member neg-risk pairs) and CH244 (a sibling shock and the unpaid members' next
spread, mixed 3-10 member ladders). DRAFT: nothing is registered; E-numbers are assigned at registration. Research tooling only; never trades; makes no
network request.

This module holds: the pins and the spec (1.1, 8.4), the capture loaders and the write-once per-capture series (1.2, 1.5), the reward status
``listed_carry24h_v2`` in its three cases (1.4.1), the event key, completeness, series family and event-id set (1.4.3), the two unit builders (2.2-2.3,
3.2-3.3) with the placebo pair (2.3) and the day-fixed status (3.2), the CLOB reward-feed clock (1.2), the lag-slot loaders (7), the window reader
(:func:`run_once`), ``ops-stats``, the expanding-past event x UTC-day demeaning and the NEW event-phase state-shift gate
:func:`event_day_state_shift_gate` (1.8; new code, not a vendored copy), the fresh seal and the counts-only census CC12 with every gate of section 7 and the
header pre-check. The simulated worlds and the size check are in ``live_tests12_worlds.py``, the single analysis in ``live_tests12_analysis.py``
(LT12 ambiguity A1: 8.1 lists one module; the house split of LT10 / LT11 is kept, the gate stays here).

LT3-LT11 code is used only through the vendored copies in ``live_tests12_base`` / ``live_tests12_analysis_base`` (8.1); this module never imports
``live_tests3`` .. ``live_tests11``, and no E026 frozen file is imported, copied or edited.

Causality (1.3): a unit at capture k reads captures <= k (the 12-slot look-back and the earlier slots of the UTC day); targets start at capture k + 1; twins
(k + 2, k + 3) are readings written after the fact and never read by a unit builder (a unit test checks that a builder never touches a slot after k).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import forecast, panel
from . import live_tests12_base as b

VERSION = "live-tests12-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
FEED_ROOT = ROOT / "data-dumps" / "research_lab" / "reward_params"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests12"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests12_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration (8.4 step 9)
REGISTERED_UTC = "2026-12-10T00:00:00Z"  # proposed (design 1.1, fast lane)
END_UTC = "2026-12-31T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2027-01-01T12:00:00Z"
TEMPFAIL = 75
DAY_S = 86400.0
GRID_S = b.GRID_S
DESIGN_TEXT_SHA256 = "a543db63baeb3e85ff2dfa0189478086216c708e59b36f6db575c6b84592b62d"  # LIVE_TESTS_12.md design-text freeze (ledger aec7a686)
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_12.md"
REWARD_NULL_RULE = "listed_carry24h_v2"
TESTS = ("CH245", "CH244")
KINDS = {"CH245": "mirror", "CH244": "mixedlad"}
TERM = {"CH245": "zs", "CH244": "shock_x_unrew"}
TWIN = {"CH245": "zs_tw", "CH244": "shock_x_unrew_tw"}
F_ROLES = {"CH245": "binding", "CH244": "binding"}  # 1.7 / 1.9: F binds for both, fixed by design (rolling states)
RECEIPT_SPAN_S = 120.0  # 1.3
EPS = 1e-9
CODE_FILES = ("live_tests12.py", "live_tests12_worlds.py", "live_tests12_analysis.py", "live_tests12_base.py", "live_tests12_analysis_base.py", "bounce_decomp.py",
              "battery.py", "panel.py", "economics.py", "forecast.py", "maker_rewards.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)
SNAP_COLS12 = [*b.SNAP_COLS, "liquidity", "neg_risk_market_id", "neg_risk_other", "event_neg_risk_augmented"]
EXT_COLS12 = [*b.EXT_COLS, "rewards_min_size", "rewards_max_spread", "clob_rewards", "received_utc", "volume_num", "accepting_orders", "event_ids"]
# columns ops_stats may read (never a price, a spread, a volume, a liquidity or a target; enforced by a unit test)
OPS_COLS = frozenset({"role", "kind", "line", "arm", "in_scope", "cell", "size_class", "status", "late", "noprev", "slot", "day", "empty", "boundary"})
MARKERS = (".late.csv.gz", ".noprev.csv.gz", ".boundary.csv.gz")
ROLE_CONF, ROLE_UNREG = "prospective_confirmation", "prospective_unregistered"
MISSING_AFTER_S = 3 * 3600.0  # a target capture absent 3 h after its slot is "capture_missing" (LT3-LT11)
DISK_CAP_BYTES = int(3.0e9)  # 1.12: the reader refuses above 3.0 GB in live_tests12/
TIER_CUTS = (1000.0, 10000.0, 100000.0)  # 1.4.2: the cost model's liquidity bins (< $1k, $1k-10k, $10k-100k, >= $100k)
FEED_CLOCK_H = 6.0  # 1.2: the feed capture at most 6 h before capture k - 1's start
SHOCK_TICKS = 2.0  # 3.2
SHOCK_SIZE_WINSOR = 20.0  # 3.2
FINAL_CAPTURE_STATES = frozenset({"complete", "failed", "partial", "incomplete", "error", "aborted"})  # 7: a restore refuses only while a lag-slot capture is in progress

epoch, iso, now_ts, sha256_file, git_commit, _json = b.epoch, b.iso, b.now_ts, b.sha256_file, b.git_commit, b._json
append_jsonl, dir_bytes, du_bytes = b.append_jsonl, b.dir_bytes, b.du_bytes
write_once_csv = b.write_once_csv
_NULL_LIKE = b._NULL_LIKE


class Refused(RuntimeError):
    """A pin, spec, seal or date check failed: nothing is written."""


# --- pins, spec and design text (1.1, 8.4) ----------------------------------------------------------------------------------------------


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LT3 9.3's rule)."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: (code_sha256(here / n) if (here / n).exists() else None) for n in CODE_FILES}


def joint_sha(h12: str | None, hbase: str | None) -> str:
    """16 hex digits identifying the reader code: the unit-building module together with the vendored base (the registered pins feed the same function)."""
    return hashlib.sha256((str(h12) + str(hbase)).encode("utf-8")).hexdigest()[:16]


def reader_sha() -> str:
    h = code_hashes()
    return joint_sha(h["live_tests12.py"], h["live_tests12_base.py"])


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
            raise RuntimeError(f"live_tests12 spec sha256 mismatch: {got} != pinned {sha}")
        if (bad := _nan_free(spec)):
            raise RuntimeError(f"live_tests12 pinned spec holds NaN / inf at {bad[:5]}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests12 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    if spec.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        raise RuntimeError("live_tests12 spec design_text_sha256 differs from the module constant")
    return spec


def reward_rule_error(spec: dict) -> dict | None:
    """1.4.1: every census refuses unless the spec declares ``reward_null_rule = listed_carry24h_v2`` with ``reward_carry_slots = 12``."""
    if spec.get("reward_null_rule") != REWARD_NULL_RULE or spec.get("reward_carry_slots") != b.REWARD_CARRY_SLOTS:
        return {"error": "the spec does not declare the reward-null rule listed_carry24h_v2 with reward_carry_slots 12: refused",
                "reward_null_rule": spec.get("reward_null_rule"), "reward_carry_slots": spec.get("reward_carry_slots")}
    return None


def k_block_error(spec: dict) -> dict | None:
    """7 / 1.7: the header pre-check result (whether ``chg_1d`` / ``chg_1w`` exist) is committed BEFORE the seal and fixes K's columns: the seal and every
    census refuse a spec in which either is still null."""
    kb = spec.get("k_block") or {}
    if not isinstance(kb.get("chg_1d"), bool) or not isinstance(kb.get("chg_1w"), bool):
        return {"error": "the spec's k_block (chg_1d, chg_1w) is not filled from the committed header pre-check: refused (7)", "k_block": kb}
    return None


SPEC_HASHED_BLOCKS = ("census_gates", "census_inputs", "tests", "eligibility", "grid", "crypto_classifier", "sports_rule", "crypto_rule", "reward_null_rule",
                      "reward_carry_slots", "f_roles", "rv", "k_block", "receipt_span_s", "tiers", "feed")


def spec_blocks_sha(spec: dict) -> str:
    """sha256 of the canonical JSON of every spec block census code reads. The seal stores it; every census refuses a spec whose blocks differ from the
    seal-time ones. ``census_fixed`` (the values the census fills) is deliberately outside the hash."""
    blob = json.dumps({k_: spec.get(k_) for k_ in SPEC_HASHED_BLOCKS}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def design_text_sha(path: Path | None = None) -> str:
    return sha256_file(path or DESIGN_PATH)


def design_text_error(path: Path | None = None) -> dict | None:
    got = design_text_sha(path)
    return None if got == DESIGN_TEXT_SHA256 else {"error": "LIVE_TESTS_12.md differs from the text-frozen file: refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}


def f_role(spec: dict, test: str) -> str:
    """1.9: F binds for both tests, fixed now by design, never by a census count. A spec that says otherwise is refused."""
    got = (spec.get("f_roles") or {}).get(test)
    if got != F_ROLES[test] or "f_binding" in spec:
        raise RuntimeError(f"F role of {test} must be {F_ROLES[test]} (design 1.9); the spec says {got!r}")
    return got


CENSUS_FIXED_KEYS = {"CH245": ("s_D", "s_T", "s_w", "zs_cuts", "zs_gap", "rgap_q50_s", "rgap_q90_s", "exclude_family", "rho_census"),
                     "CH244": ("world9_corr", "shock_size_scale", "exclude_family")}  # 7: the exhaustive list (k_tests is the tenth item)


def census_fixed_missing(spec: dict, test: str) -> list[str]:
    """Census-fixed values of ``test`` that are unfilled: None or non-finite anywhere (nested). ``exclude_family`` is ``""`` when no family was excluded;
    ``rho_census`` may be None ONLY together with ``rho_census_nan: true`` (7 item 9: NaN on zero variance; world 1 then fails by 1.8.1's rule)."""
    cf = (spec.get("census_fixed") or {}).get(test) or {}

    def bad(v) -> bool:
        if v is None:
            return True
        if isinstance(v, (list, tuple)):
            return not v or any(bad(x) for x in v)
        if isinstance(v, float):
            return not math.isfinite(v)
        return False

    miss = []
    for k_ in CENSUS_FIXED_KEYS[test]:
        v = cf.get(k_)
        if k_ == "rho_census" and v is None and cf.get("rho_census_nan") is True:
            continue
        if bad(v):
            miss.append(k_)
    return miss


def registration_error(spec: dict) -> dict | None:
    """The registration refusals of a pinned spec (8.4 steps 5-9): a null / empty / unknown ``k_tests`` and unfilled census values refuse. DRAFT: None."""
    if not spec.get("_pinned"):
        return None
    k = spec.get("k_tests")
    if not k:
        return {"error": "pinned spec with null or empty k_tests"}
    if [t for t in k if t not in TESTS]:
        return {"error": f"pinned spec with unknown k_tests {[t for t in k if t not in TESTS]}"}
    for t in k:
        if (m := census_fixed_missing(spec, t)):
            return {"error": f"pinned spec with unfilled census_fixed values of {t}: {m}"}
    return None


# --- small helpers ----------------------------------------------------------------------------------------------------------------------------


def _num(v) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return math.nan
    return x if math.isfinite(x) else math.nan


def role_of(capture_start: float, registered_utc: str, end_utc: str, pinned: bool) -> str:
    ok = pinned and epoch(registered_utc) <= capture_start < epoch(end_utc)
    return ROLE_CONF if ok else ROLE_UNREG


def target_state(by_slot: dict, j: int, now: float, spec: dict) -> str:
    """"ready" (capture exists), "missing" (absent MISSING_AFTER_S after its slot), else "pending" (LT3's rule)."""
    if j in by_slot:
        return "ready"
    return "missing" if now > b.slot_time(j, spec) + MISSING_AFTER_S else "pending"


def is_late(j: int, now: float, spec: dict) -> bool:
    """A freeze is refused once its earliest target slot's capture may have started (slot time - 60 s; LT3's rule)."""
    return now >= b.slot_time(j, spec) - 60.0


def day_start_slot(k: int) -> int:
    """The first slot of the UTC day of slot ``k`` (the grid starts at 00:31Z: 12 slots a day, ``k mod 12`` the slot of day)."""
    return k - (k % 12)


def _flag_num(v) -> float:
    """A 0/1 flag text of the capture ('1', '0', '1.0', 'true', 'false') to 1.0 / 0.0, else NaN (a missing or unreadable value stays NaN)."""
    s = str(v).strip().casefold()
    if s in ("1", "1.0", "true", "t"):
        return 1.0
    if s in ("0", "0.0", "false", "f"):
        return 0.0
    return math.nan


def tier_of(liq) -> np.ndarray:
    """1.4.2: the cost model's four liquidity bins of ``liquidity`` (0: < $1k, 1: $1k-10k, 2: $10k-100k, 3: >= $100k); NaN when missing."""
    v = np.asarray(liq, float)
    out = np.full(len(v), np.nan)
    ok = np.isfinite(v)
    out[ok] = np.searchsorted(np.asarray(TIER_CUTS), v[ok], side="right").astype(float)
    return out


def tier_dummies(tier, prefix: str) -> dict:
    """Three dummies of the four tiers (reference: tier 0, < $1k); NaN when the tier is NaN (the unit is excluded, counted)."""
    t = np.asarray(tier, float)
    return {f"{prefix}{i}": np.where(np.isfinite(t), (t == i).astype(float), np.nan) for i in (1, 2, 3)}


def series_family(series_slugs, key: str) -> str:
    """1.4.3: the first entry of the sidecar ``series_slugs`` after strip and casefold (the vendored ``first_series_slug``); an empty value gives the
    singleton family ``none:<event key>``."""
    s = b.first_series_slug(series_slugs).strip().casefold()
    return s if s else f"none:{key}"


def event_id_set(sidecar_value, row_event) -> list[str]:
    """1.4.3: the sidecar ``event_ids`` (parsed as a set of strings) plus the row ``event_id``; empty if neither is present. LT12 ambiguity A6: the field's
    text is read as a JSON list when it parses, else as a comma / semicolon / whitespace separated list (quotes and brackets stripped)."""
    out: set[str] = set()
    if sidecar_value is not None and not (isinstance(sidecar_value, float) and math.isnan(sidecar_value)):
        s = str(sidecar_value).strip()
        if s and s.casefold() not in _NULL_LIKE:
            try:
                j = json.loads(s)
                items = j if isinstance(j, list) else [j]
            except (ValueError, TypeError):
                items = re.split(r"[,;\s]+", s.strip("[]"))
            for x in items:
                x = str(x).strip().strip('"').strip("'")
                if x and x.casefold() not in _NULL_LIKE:
                    out.add(x)
    if row_event is not None and not (isinstance(row_event, float) and math.isnan(row_event)):
        r = str(row_event).strip()
        if r and r.casefold() not in _NULL_LIKE:
            out.add(r)
    return sorted(out)


# --- loaders and the per-capture series (1.2, 1.5) --------------------------------------------------------------------------------------


def load_rows12(cap_dir: Path) -> pd.DataFrame:
    """Origin-side capture columns (LT3's plus Gamma ``liquidity`` and the neg-risk fields): one row per market_id and per condition_id (first in page
    order, 1.4)."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(SNAP_COLS12),
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category", "end_date": str, "closed": str,
                              "active": str, "neg_risk": str, "neg_risk_market_id": str, "neg_risk_other": str, "event_neg_risk_augmented": str})
    for c in SNAP_COLS12:
        if c not in rows:
            rows[c] = np.nan
    rows = rows.drop_duplicates("market_id")
    cond = rows["condition_id"].fillna("")
    rows = rows[~(cond.ne("") & cond.duplicated()).to_numpy()].reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    return rows


def load_ext12(cap_dir: Path) -> pd.DataFrame | None:
    """The sidecar by market_id, or None when the capture has no ``rows_ext.csv.gz`` (sidecar missing: category, tick and reward status unknown, 1.2)."""
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS12), dtype=str)
    has_clob = "clob_rewards" in ext.columns  # LT12 ambiguity A7: a sidecar WITHOUT the column says nothing about rewards: NaN (LT8 check fix 7), never case (b)
    for c in EXT_COLS12:
        if c not in ext:
            ext[c] = None
    out = ext.drop_duplicates("market_id").set_index("market_id")
    out.attrs["has_clob_rewards"] = has_clob
    return out


def capture_last_receipt(cap_dir: Path) -> float:
    """A capture's last row receipt (1.3): the largest ``received_utc`` over the capture's complete rows AND its sidecar rows (timestamp columns only)."""
    best = math.nan
    for fn in ("rows.csv.gz", "rows_ext.csv.gz"):
        p = Path(cap_dir) / fn
        if not p.exists():
            continue
        r = pd.read_csv(p, usecols=lambda c: c == "received_utc", dtype=str)
        if "received_utc" not in r or r.empty:
            continue
        t = panel._epoch(r["received_utc"].astype(str))
        if np.isfinite(t).any():
            m = float(np.nanmax(t))
            best = m if not math.isfinite(best) else max(best, m)
    return best


def series12_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, day: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(series, status) of a capture: the vendored LT3 series (two-sided quotes of open active binary markets) plus Gamma ``liq``, ``condition_id``,
    ``neg_risk_other``, ``fee_cat``, the pinned crypto class ``crypto7`` and ``side`` (1 when the sidecar has a row). LT12 ambiguity A3 (LT11 A2): the
    vendored series treats ``ask == 1`` as two-sided; 1.4 says two-sided means ``ask < 1``, so such rows move to the status file as ``one_sided``."""
    ser, st = b.series_frame(rows, ext, spec)
    ask1 = ser["ask"].to_numpy(float) >= 1.0 - 1e-12
    if ask1.any():
        st = pd.concat([st, pd.DataFrame({"market_id": ser["market_id"].to_numpy()[ask1], "st": "one_sided"})], ignore_index=True)
        ser = ser[~ask1].reset_index(drop=True)
    mids = pd.Index(ser["market_id"].astype(str))
    r = rows.set_index(rows["market_id"].astype(str))
    ser["liq"] = pd.to_numeric(r["liquidity"], errors="coerce").reindex(mids).to_numpy(float)
    ser["condition_id"] = r["condition_id"].reindex(mids).fillna("").astype(str).to_numpy(object)
    ser["neg_risk_other"] = pd.Series([_flag_num(v) for v in r["neg_risk_other"].reindex(mids).tolist()]).to_numpy(float)
    if ext is not None:
        present = np.asarray(mids.isin(ext.index))
        fc = ext["fee_category"].reindex(mids).where(lambda s: s.notna(), None).tolist()
    else:
        present = np.zeros(len(mids), bool)
        fc = [None] * len(mids)
    ser["side"] = present.astype(int)
    ser["fee_cat"] = pd.Series(fc, dtype=object).to_numpy()
    ser["crypto7"] = [b.crypto_class(f, bool(p), int(s)) for f, p, s in zip(fc, present, ser["sports"].to_numpy(int), strict=True)]
    return ser, st


def members12_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict) -> pd.DataFrame:
    """The neg-risk member table of a capture (1.4.3): every binary, open and active row with ``neg_risk`` true, with the event key (``neg_risk_market_id``
    where present and non-empty, else the Gamma ``event_id``, else the market itself), the two-sided flag (bid > 0, ask < 1, bid < ask), the quote, the row
    receipt, the tick, Gamma ``liquidity``, ``neg_risk_other``, the augmented flag (NaN when missing: counted augmented by the callers), the category
    (``sports`` -1 = sidecar missing; ``crypto7``), ``nr_conflict`` (the key group spans more than one Gamma event), the series family ``fam`` and the
    event-id set ``eids`` (a JSON list; ``eids_missing`` 1 when empty)."""
    cols = ["market_id", "condition_id", "nrkey", "event_id", "two", "bid", "ask", "t_row", "tick", "liq", "other", "aug", "sports", "crypto7", "nr_conflict", "fam", "eids", "eids_missing", "side"]
    closed, active = b._truthy(rows["closed"]), b._truthy(rows["active"])
    nr = b._truthy(rows["neg_risk"]) & (rows["binary"] == 1).to_numpy() & ~closed & active
    m = rows[nr].reset_index(drop=True)
    if m.empty:
        return pd.DataFrame({c: [] for c in cols})
    mids = m["market_id"].astype(str)
    ev = m["event_id"].fillna("").astype(str).str.strip()
    ev = ev.where(~ev.str.casefold().isin(_NULL_LIKE), "")
    nk = m["neg_risk_market_id"].fillna("").astype(str).str.strip()
    nk = nk.where(~nk.str.casefold().isin(_NULL_LIKE), "")
    key = np.where(nk != "", nk, np.where(ev != "", ev, "m:" + mids))
    bid, ask = m["best_bid"].to_numpy(float), m["best_ask"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        two = (bid > 0) & (ask < 1.0 - 1e-12) & (bid < ask)
    cat = b.category_cols(ext, mids, m["event_id"], spec)
    present = np.asarray(mids.isin(ext.index)) if ext is not None else np.zeros(len(m), bool)
    if ext is not None:
        e = ext.reindex(pd.Index(mids))
        fc = e["fee_category"].astype(object).where(lambda s: s.notna(), None).tolist()
        slugs = e["series_slugs"].tolist()
        eid_raw = e["event_ids"].tolist()
    else:
        fc, slugs, eid_raw = [None] * len(m), [None] * len(m), [None] * len(m)
    crypto7 = [b.crypto_class(f, bool(p), int(s)) for f, p, s in zip(fc, present, cat["sports"], strict=True)]
    g = pd.DataFrame({"k": key, "e": ev.to_numpy()})
    nev = g[g["e"] != ""].groupby("k")["e"].nunique()
    conflict = g["k"].map(nev).fillna(0).to_numpy(float) > 1
    fam = [series_family(s_ if p else None, k_) for s_, p, k_ in zip(slugs, present, key, strict=True)]
    eids = [event_id_set(x if p else None, e_ if e_ != "" else None) for x, p, e_ in zip(eid_raw, present, ev.tolist(), strict=True)]
    return pd.DataFrame({"market_id": mids.to_numpy(), "condition_id": m["condition_id"].fillna("").astype(str).to_numpy(), "nrkey": key,
                         "event_id": np.where(ev != "", ev, "m:" + mids).astype(object), "two": two.astype(int), "bid": bid, "ask": ask, "t_row": m["t_row"].to_numpy(float),
                         "tick": cat["tick"], "liq": pd.to_numeric(m["liquidity"], errors="coerce").to_numpy(float),
                         "other": np.array([_flag_num(v) for v in m["neg_risk_other"].tolist()], float),
                         "aug": np.array([_flag_num(v) for v in m["event_neg_risk_augmented"].tolist()], float), "sports": cat["sports"],
                         "crypto7": np.array(crypto7, dtype=object), "nr_conflict": conflict.astype(int), "fam": np.array(fam, dtype=object),
                         "eids": [json.dumps(x) for x in eids], "eids_missing": np.array([int(not x) for x in eids]), "side": present.astype(int)})


def write_series12(work: Path, cap: dict, spec: dict) -> dict:
    """Write-once ``series/<id>.csv.gz`` (two-sided quotes), ``status/<id>.csv.gz`` (the other binary rows), ``rw/<id>.csv.gz`` (LT8's :func:`b.rw_frame`
    of EVERY sidecar row, the reward status's input) and ``members/<id>.csv.gz`` (the neg-risk members). Returns the counts."""
    work = Path(work)
    cid = cap["id"]
    paths = [work / sub / f"{cid}.csv.gz" for sub in ("series", "status", "rw", "members")]
    if all(p.exists() for p in paths):
        return {"written": False}
    rows = load_rows12(cap["dir"])
    ext = load_ext12(cap["dir"])
    day = b._utc_day(cap["start"])
    ser, st = series12_frame(rows, ext, spec, day)
    mem = members12_frame(rows, ext, spec)
    w = [write_once_csv(paths[0], ser), write_once_csv(paths[1], st), write_once_csv(paths[2], b.rw_frame(ext, day)), write_once_csv(paths[3], mem)]
    return {"written": any(w), "rows": len(ser), "status_rows": len(st), "members": len(mem), "sidecar": ext is not None}


def read_series12(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    ser = b.read_series(work, cap_id)
    if ser is None:
        return None
    ser["condition_id"] = ser["condition_id"].fillna("").astype(str) if "condition_id" in ser else ""
    return ser


def read_status12(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(work) / "status" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "st": str}).drop_duplicates("market_id").set_index("market_id")


def read_members12(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(work) / "members" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "condition_id": str, "nrkey": str, "event_id": str, "crypto7": str, "fam": str, "eids": str}, keep_default_na=True)


def status_codes(ser: pd.DataFrame | None, st: pd.DataFrame | None, mids, capture_missing: bool) -> np.ndarray:
    """One status per unit at a target slot (1.5): ``two_sided`` (a series row), else the status file's code (``one_sided``, ``closed_flag``), else
    ``absent``; ``capture_missing`` when the slot has no complete capture."""
    n = len(mids)
    if capture_missing:
        return np.full(n, "capture_missing", dtype=object)
    idx = pd.Index(np.asarray(mids, dtype=str))
    in_ser = idx.isin(ser.index) if ser is not None else np.zeros(n, bool)
    code = st["st"].reindex(idx).to_numpy(object) if st is not None else np.full(n, None, dtype=object)
    return np.array(["two_sided" if a else ("absent" if (c is None or (isinstance(c, float) and np.isnan(c))) else c) for a, c in zip(in_ser, code, strict=True)], dtype=object)


def series_ready(root: Path, by_slot: dict, slots) -> bool:
    """Every listed slot with a complete capture already has its series and members files (a missing file is never read as a missing capture)."""
    return all((Path(root) / "series" / f"{by_slot[j]['id']}.csv.gz").exists() and (Path(root) / "members" / f"{by_slot[j]['id']}.csv.gz").exists() for j in slots if j in by_slot)


# --- access by slot, the causality guard (1.3) --------------------------------------------------------------------------------------------


class SlotStore:
    """Read access to the per-capture files by slot with a bounded cache. ``reads`` records every slot opened: the unit builders of origin k read only
    slots <= k (the unit test asserts ``max(reads) <= k``); twins and readings go through the lag loaders, never through this store."""

    def __init__(self, work: Path, by_slot: dict, spec: dict, cache_slots: int = 30) -> None:
        self.work, self.by_slot, self.spec, self.cache_slots = Path(work), by_slot, spec, cache_slots
        self.reads: set[int] = set()
        self._c: dict[str, dict[int, object]] = {"ser": {}, "st": {}, "mem": {}, "rw": {}, "rs": {}}
        self._tdec: dict[int, float] = {}
        self.mids = b.MidStore()
        self._added: set[int] = set()

    def has(self, j: int) -> bool:
        return j in self.by_slot

    def _get(self, kind: str, j: int, fn):
        if j not in self.by_slot:
            return None
        self.reads.add(j)
        cache = self._c[kind]
        if j not in cache:
            cache[j] = fn(j)
            if len(cache) > self.cache_slots:
                for old in sorted(cache)[: len(cache) - self.cache_slots]:
                    cache.pop(old)
        return cache[j]

    def ser(self, j: int) -> pd.DataFrame | None:
        return self._get("ser", j, lambda s: read_series12(self.work, self.by_slot[s]["id"]))

    def status(self, j: int) -> pd.DataFrame | None:
        return self._get("st", j, lambda s: read_status12(self.work, self.by_slot[s]["id"]))

    def members(self, j: int) -> pd.DataFrame | None:
        return self._get("mem", j, lambda s: read_members12(self.work, self.by_slot[s]["id"]))

    def rw(self, j: int) -> pd.DataFrame | None:
        return self._get("rw", j, lambda s: b.read_rw8(self.work, self.by_slot[s]["id"]))

    def t_dec(self, j: int) -> float:
        """Capture ``j``'s last row receipt (rows and sidecar), 1.3's decision clock."""
        if j not in self._tdec:
            self.reads.add(j)
            self._tdec[j] = capture_last_receipt(self.by_slot[j]["dir"]) if j in self.by_slot else math.nan
        return self._tdec[j]

    def mid_store(self, k: int, window: int = 12) -> b.MidStore:
        """The mid store holding slots k - window .. k (two-sided mids; a missing slot stays absent)."""
        for j in range(k - window, k + 1):
            if j not in self._added and j in self.by_slot:
                s = self.ser(j)
                if s is not None:
                    self.mids.add(j, s)
                    self._added.add(j)
        for old in [s_ for s_ in self.mids.slots if s_ < k - window - 8]:
            self.mids.slots.pop(old)
            self._added.discard(old)
        return self.mids

    def carry(self, s: int) -> b.RewardCarry:
        """The 13.7 carry over slots [s - 11, s] (``apply`` itself reads only slots <= s - 1); no slot after s is added."""
        c = b.RewardCarry(b.REWARD_CARRY_SLOTS)
        for j in range(s - b.REWARD_CARRY_SLOTS + 1, s + 1):
            rw = self.rw(j)
            if rw is not None:
                c.add(j, rw)
        return c

    def reward_status(self, s: int) -> pd.DataFrame | None:
        """1.4.1's status at status capture ``s`` for every sidecar row of capture s (None when capture s is missing): see :func:`status_at`."""
        return self._get("rs", s, lambda s_: status_at(self, s_))


# --- the reward status listed_carry24h_v2 (1.4.1; R1 must-fix 2) --------------------------------------------------------------------------


REWARD_CASES = ("listed_positive", "rewards_listed_inactive", "rewards_null_carried", "rewards_null_window_listed_inactive", "rewards_null_as_zero", "malformed", "no_column", "absent")


def status_at(store: SlotStore, s: int) -> pd.DataFrame | None:
    """``rewarded`` of every market with a sidecar row at status capture ``s`` (index market_id) under ``listed_carry24h_v2`` (LIVE_TESTS_7.md 13.7, via the
    vendored ``RewardCarry`` fed with LT8's rw frames of slots [s - 11, s]):

    * (a) listed at s: the text at s parsed for the UTC day of s; rate > 0 -> 1, rate 0 -> 0 (``rewards_listed_inactive``);
    * (b) null at s (an empty cell on a present row): 1 if a listed text of a sealed capture in [s - 11, s - 1] re-parsed for the UTC day of s gives a rate
      > 0 (the latest such capture; ``rewards_null_carried``), else 0 (``rewards_null_as_zero`` with nothing listed, ``rewards_null_window_listed_inactive``
      with only rate-0 texts); a window slot without a capture is skipped and counted (``win_missing``), no slot after s is read;
    * (c) NaN for a malformed cell at s (``malformed``) or a sidecar without the column (``no_column``, A7); a market without a sidecar row at s is absent
      from the frame (callers reindex: NaN, ``absent``)."""
    rw = store.rw(s)
    if rw is None:
        return None
    day = b._utc_day(store.by_slot[s]["start"])
    f = rw.copy()
    st = f["rew_status"].astype(str).to_numpy()
    raw = f["rew_raw"].to_numpy(object)
    rate = np.full(len(f), np.nan)
    for i, (s_, r_) in enumerate(zip(st, raw, strict=True)):
        if s_ == "listed":
            rate[i] = b.reward_detail(r_, day)[0]
        elif s_ == "null":
            rate[i] = 0.0
    f["rew_rate"] = rate
    c = store.carry(s).apply(f, s, day)
    lag = c["rew_carry_lag"].to_numpy(float)
    rr = c["rew_rate"].to_numpy(float)
    unk = np.isin(st, ["malformed", "absent", "no_column"]) | ~np.isfinite(rr)
    rewarded = np.where(unk, np.nan, (rr > 0).astype(float))
    case = np.where(st == "malformed", "malformed", np.where(st == "no_column", "no_column", np.where(st == "absent", "absent", "")))
    listed = st == "listed"
    case = np.where(listed & (rr > 0), "listed_positive", case)
    case = np.where(listed & ~(rr > 0) & np.isfinite(rr), "rewards_listed_inactive", case)
    null = st == "null"
    case = np.where(null & np.isfinite(lag), "rewards_null_carried", case)
    case = np.where(null & ~np.isfinite(lag) & (c["rew_win_inactive"].to_numpy(float) == 1), "rewards_null_window_listed_inactive", case)
    case = np.where(null & ~np.isfinite(lag) & (c["rew_win_inactive"].to_numpy(float) != 1), "rewards_null_as_zero", case)
    return pd.DataFrame({"rewarded": rewarded, "case": case, "carry_lag": lag, "win_missing": c["rew_win_missing"].to_numpy(float),
                         "simple_nonempty": (~null & ~np.isin(st, ["absent", "no_column"])).astype(float)}, index=f.index)


def rewarded_for(store: SlotStore, s: int, markets) -> tuple[np.ndarray, np.ndarray]:
    """(rewarded, case) of ``markets`` at status capture ``s``; a missing capture or a missing sidecar row gives NaN / ``absent`` (case (c))."""
    mk = pd.Index(np.asarray(markets, dtype=str))
    rs = store.reward_status(s)
    if rs is None:
        return np.full(len(mk), np.nan), np.full(len(mk), "absent", dtype=object)
    r = rs.reindex(mk)
    return r["rewarded"].to_numpy(float), r["case"].fillna("absent").to_numpy(object)


# --- the known-factor block K (1.7) ------------------------------------------------------------------------------------------------------


SD_DUMMIES = [f"sd{s_}" for s_ in range(1, 12)]


def slot_dummies(u: pd.DataFrame, slot_of_day: int) -> None:
    """11 slot-of-day dummies (reference slot 0), 1.7."""
    for s in range(1, 12):
        u[f"sd{s}"] = float(slot_of_day == s)


def k_block(store: SlotStore, k: int, markets, t_dec: float, spec: dict, prefix: str = "") -> pd.DataFrame:
    """The known-factor block K (1.7, LT11 1.7 unchanged) of ``markets`` at origin k: ``p_k``, the spread at k (cents), ``log1p liquidity``, ``log1p
    volume24hr`` (``vol_missing``), log hours to end (``hte_unknown``), ``1[tick = 0.001]``, ``log rv24*`` over 12 slots, ``rewarded_k`` (1.4.1 with s = k),
    the own ``d_k``, the own 6 h and 24 h changes and ``chg_1h`` (``mom_missing``), ``chg_1d`` / ``chg_1w`` as indicator pairs when the header pre-check
    found them, and the 11 slot-of-day dummies; the tier at k (1.4.2: "read ... at k as a K control", LT12 ambiguity A8) as three dummies ``tk1..tk3``.
    The fee-category dummies are added where the population is known (census, analysis). Reads slots <= k only."""
    mk = np.asarray(markets, dtype=str)
    ser_k, ser_p = store.ser(k), store.ser(k - 1)
    J, P = ser_k.reindex(pd.Index(mk)), ser_p.reindex(pd.Index(mk))
    bid, ask = J["bid"].to_numpy(float), J["ask"].to_numpy(float)
    mid = (bid + ask) / 2.0
    mid_p = (P["bid"].to_numpy(float) + P["ask"].to_numpy(float)) / 2.0
    M = store.mid_store(k).matrix(k, 12, mk, "mid")
    d6, m6 = b._own24(np.ones(len(mk)), mid, M[:, 9])
    d24, m24 = b._own24(np.ones(len(mk)), mid, M[:, 0])
    chg1h = J["chg_1h"].to_numpy(float)
    rew, case = rewarded_for(store, k, mk)
    u = pd.DataFrame({"p_k": mid, "spread_c": (ask - bid) * 100.0, "d": mid - mid_p, "own6": d6, "own24": d24, "chg1h": np.where(np.isfinite(chg1h), chg1h, 0.0),
                      "mom_missing": np.maximum(np.maximum(m6, m24), (~np.isfinite(chg1h)).astype(float)), "rewarded": rew, "rew_case_k": case})
    kb = spec.get("k_block") or {}
    for name, flag in (("chg_1d", "chg1d_missing"), ("chg_1w", "chg1w_missing")):
        if kb.get(name):
            v = J[name].to_numpy(float)
            u[name.replace("_", "")] = np.where(np.isfinite(v), v, 0.0)
            u[flag] = (~np.isfinite(v)).astype(float)
    tmp = pd.DataFrame({"tick": J["tick"].to_numpy(float), "liq": J["liq"].to_numpy(float), "end_ts": J["end_ts"].to_numpy(float), "mid": mid, "t_row": np.full(len(mk), t_dec)})
    cc = b._common_cols(tmp)
    u["tick001"], u["log_hte"], u["hte_unknown"], u["log1p_liq"] = cc["tick001"].to_numpy(float), cc["log_hte"].to_numpy(float), cc["hte_unknown"].to_numpy(float), cc["log1p_liq"].to_numpy(float)
    u["log1p_vol"], u["vol_missing"] = b._vol_cols(J["vol24"].to_numpy(float))
    _rv, rvs, rvf = b._rv24(store.mid_store(k), k, mk, J["tick"].to_numpy(float), spec["rv"])
    with np.errstate(invalid="ignore", divide="ignore"):
        u["log_rv24s"] = np.log(rvs)
    u["rv_floor"] = rvf
    for nm, v in tier_dummies(tier_of(J["liq"].to_numpy(float)), "tk").items():
        u[nm] = v
    slot_dummies(u, k % 12)
    u["fee_cat"] = J["fee_cat"].to_numpy(object)
    u["fee_rate"], u["fee_exp"] = J["fee_rate"].to_numpy(float), J["fee_exp"].to_numpy(float)
    if prefix:
        u = u.add_prefix(prefix)
    return u


K_COMMON = ["p_k", "spread_c", "log1p_liq", "log1p_vol", "vol_missing", "log_hte", "hte_unknown", "tick001", "log_rv24s", "rewarded", "d", "own6", "own24", "chg1h", "mom_missing",
            "chg1d", "chg1d_missing", "chg1w", "chg1w_missing", "tk1", "tk2", "tk3", *SD_DUMMIES]  # neg_risk is constant within both tests and dropped (1.7)


# --- the event join (1.4.3) ------------------------------------------------------------------------------------------------------------


def event_captures(M: pd.DataFrame | None) -> dict[str, pd.DataFrame]:
    if M is None or M.empty:
        return {}
    return {k_: g for k_, g in M.groupby("nrkey", sort=False)}


def size_class(n: int) -> str:
    """``2`` (CH245), ``3-5`` / ``6-10`` (CH244's 3-10 ladders), ``11+`` (CH244's reported arm); ``1`` has no unit."""
    return "1" if n < 2 else "2" if n == 2 else "3-5" if n <= 5 else "6-10" if n <= 10 else "11+"


def _span(g: pd.DataFrame) -> float:
    t = g["t_row"].to_numpy(float)
    return float(np.nanmax(t) - np.nanmin(t)) if np.isfinite(t).any() and np.isfinite(t).all() else math.nan


def event_pairs(Mp: pd.DataFrame | None, Mk: pd.DataFrame | None, spec: dict) -> tuple[dict, dict]:
    """The event-capture pair logic of 1.4.3 on the member tables of captures ``p`` and ``k`` (k - 1 and k for a unit; k + 2 and k + 3 for a twin).
    Returns (``pairs``: key -> record, counts). A record holds the members at both captures, ``reason`` (first match, counted once): ``members_changed``
    (the eligible member sets differ, or the key is absent at p), ``category`` (sports on some but not all members, crypto or unknown on any member;
    ``sports_arm`` when every member is sports at both), ``event_incomplete`` (a member not two-sided at p or k), ``receipt_span`` (the members' rows
    ``received_utc`` span above 120 s at p or k; NaN fails) or ``ok``; ``augmented`` (any eligible member with the field non-zero or MISSING at p or k).
    Nothing is filled: an incomplete event-capture gives no unit for any member, no bid is set to 0 or carried."""
    cnt = Counter()
    pairs: dict = {}
    ek, ep = event_captures(Mk), event_captures(Mp)
    span_s = float(spec.get("receipt_span_s", RECEIPT_SPAN_S))
    for key, gk in ek.items():
        gp = ep.get(key)
        n_k = len(gk)
        rec = {"key": key, "n_k": n_k, "size_class": size_class(n_k), "gk": gk, "gp": gp, "reason": "ok", "augmented": False, "span_k": math.nan, "span_p": math.nan}
        cnt["event_captures"] += 1
        both = [gk] if gp is None else [gk, gp]
        aug = np.concatenate([g_["aug"].to_numpy(float) for g_ in both])
        rec["augmented"] = bool((~np.isfinite(aug) | (aug != 0)).any())
        sp = np.concatenate([g_["sports"].to_numpy(int) for g_ in both])
        c7 = np.concatenate([g_["crypto7"].astype(str).to_numpy() for g_ in both])
        if gp is None or set(gk["market_id"]) != set(gp["market_id"]):
            rec["reason"] = "members_changed"
        elif (c7 != "non_crypto").any() or ((sp != 0).any() and not (sp == 1).all()):
            rec["reason"] = "category"
        elif (gk["two"].to_numpy(int) != 1).any() or (gp["two"].to_numpy(int) != 1).any():
            rec["reason"] = "event_incomplete"
        else:
            rec["span_k"], rec["span_p"] = _span(gk), _span(gp)
            if not (rec["span_k"] <= span_s and rec["span_p"] <= span_s):
                rec["reason"] = "receipt_span"
        rec["sports_arm"] = bool(rec["reason"] != "category" and (sp == 1).all())
        cnt[f"reason_{rec['reason']}"] += 1
        cnt[f"rows_{rec['reason']}"] += n_k
        cnt["nr_key_conflict_rows"] += int(gk["nr_conflict"].sum())
        pairs[key] = rec
    return pairs, dict(cnt)


def _member_ok(store: SlotStore, k: int, mk: np.ndarray, t_dec: float, spec: dict, end_margin_h: float, cnt: dict, prefix: str) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame]:
    """1.4's member-level rules at k - 1 and k for ``mk``: a series row at both (two-sided, ``ask < 1``), tight at both (LT12 ambiguity A4: spread = ask - bid,
    <= 0.10), end unknown or > t + 3 h, tick known and equal at both (``tick_changed``; unknown counted ``tick_unknown``), one row per condition_id.
    Returns (mask, rows at k, rows at k - 1)."""
    J, P = store.ser(k).reindex(pd.Index(mk)), store.ser(k - 1).reindex(pd.Index(mk))
    present = J["bid"].notna().to_numpy() & P["bid"].notna().to_numpy()
    cnt[f"{prefix}not_in_series"] = cnt.get(f"{prefix}not_in_series", 0) + int((~present).sum())
    sm = spec["eligibility"]["spread_max"]
    tight = b.tight_arr(J["bid"], J["ask"], J["ask"] - J["bid"], sm) & b.tight_arr(P["bid"], P["ask"], P["ask"] - P["bid"], sm)
    end = J["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        eok = np.isnan(end) | (end > t_dec + end_margin_h * 3600.0)
    tk, tkp = J["tick"].to_numpy(float), P["tick"].to_numpy(float)
    unk = ~(np.isfinite(tk) & np.isfinite(tkp))
    chg = ~unk & (np.abs(tk - tkp) > 1e-12)
    out = present.copy()
    for name, m in (("not_tight", ~tight), ("end_date", ~eok), ("tick_unknown", unk), ("tick_changed", chg)):
        cnt[f"{prefix}{name}"] = cnt.get(f"{prefix}{name}", 0) + int((out & m).sum())
        out &= ~m
    return out, J, P


# --- CH245: the mirror (section 2) ----------------------------------------------------------------------------------------------------


def _pairs_of_two(pairs: dict) -> list[dict]:
    return [r for r in pairs.values() if r["n_k"] == 2]


def ch245_units(store: SlotStore, k: int, spec: dict, role: str = ROLE_UNREG, commit: str = "unknown", stamp: bool = True) -> tuple[pd.DataFrame, dict]:
    """CH245's lines of origin k (2.2-2.3): for every two-member event-capture that is pair-complete (1.4.3, the 120 s span at k - 1 and k), both members
    passing 1.4 at k - 1 and k (a member failing the tight rule makes the pair ``pair_wide``), with ``|spread_A - spread_B| >= tick_e`` at k - 1 (``tick_e``
    = the larger member tick at k - 1): a ``thin`` line (the wider book at k - 1; THE unit, one per pair-capture) and a ``dense`` line (the point
    condition's unit on the same pair-capture); an equal-spread pair-capture gives two ``sym`` lines (a reported class, no unit). ``arm``: ``primary``
    (non-augmented, non-sports ex-crypto), ``augmented``, ``sports``. Each line holds the OTHER book's raw spread innovation (``o_ds_c``; the dense
    innovation on a thin line) with its census scaling ``zs`` (``s_D`` on thin lines, ``s_T`` on dense lines), the own innovation, the other book's level at
    k - 1, ``hb_km1`` and ``hb_k`` (M4), the other book's ``log1p liquidity`` and ``rewarded_k``, the mirror gaps at k - 1 and k, the receipt order at k
    (M5), the reward cell, the dense spread at k in its own ticks, the series families and event-id sets, the placebo (:func:`assign_placebo`) and the
    block K of the own market. Reads only slots <= k."""
    t = spec["tests"]["CH245"]
    Mp, Mk = store.members(k - 1), store.members(k)
    t_dec = store.t_dec(k)
    if Mp is None or Mk is None or store.ser(k) is None or store.ser(k - 1) is None or not math.isfinite(t_dec):
        return pd.DataFrame(), {"no_pair": 1}
    cap = store.by_slot[k]
    pairs, cnt0 = event_pairs(Mp, Mk, spec)
    cnt: dict = {f"ev_{k_}": v for k_, v in cnt0.items()}
    spans, gaps = [], []
    for r in _pairs_of_two(pairs):
        if r["reason"] == "category" or r["augmented"] or r["sports_arm"]:
            continue
        cnt["comp_den"] = cnt.get("comp_den", 0) + 1  # eligible two-member event-captures (incl. members_changed)
        if r["reason"] in ("ok", "receipt_span"):
            cnt["comp_num"] = cnt.get("comp_num", 0) + 1  # pair-complete before the span rule
            spans.append(max(r["span_k"], r["span_p"]))
            gk = r["gk"]
            gaps.append(float(abs(gk["t_row"].to_numpy(float)[0] - gk["t_row"].to_numpy(float)[1])))
            if r["reason"] == "ok":
                cnt["span_ok"] = cnt.get("span_ok", 0) + 1
    cnt["_spans"], cnt["_gaps"] = spans, gaps
    recs = []
    for r in _pairs_of_two(pairs):
        if r["reason"] != "ok":
            continue
        arm = "augmented" if r["augmented"] else ("sports" if r["sports_arm"] else "primary")
        gk = r["gk"].set_index("market_id")
        gp = r["gp"].set_index("market_id").reindex(gk.index)
        mk = gk.index.astype(str).to_numpy()
        ok, J, P = _member_ok(store, k, mk, t_dec, spec, t["end_margin_h"], cnt, "m_")
        if not ok.all():
            tight_fail = ~(b.tight_arr(J["bid"], J["ask"], J["ask"] - J["bid"], spec["eligibility"]["spread_max"]) & b.tight_arr(P["bid"], P["ask"], P["ask"] - P["bid"], spec["eligibility"]["spread_max"]))
            cnt["pair_wide" if tight_fail.any() else "pair_member_rule"] = cnt.get("pair_wide" if tight_fail.any() else "pair_member_rule", 0) + 1
            continue
        if (gk["condition_id"].astype(str).duplicated() & (gk["condition_id"].astype(str) != "")).any():
            cnt["dup_condition_id"] = cnt.get("dup_condition_id", 0) + 1
            continue
        bk, ak = J["bid"].to_numpy(float), J["ask"].to_numpy(float)
        bp, ap = P["bid"].to_numpy(float), P["ask"].to_numpy(float)
        sk, sp = ak - bk, ap - bp
        tick_e = float(np.nanmax(gp["tick"].to_numpy(float)))
        recs.append({"key": r["key"], "arm": arm, "mk": mk, "bk": bk, "ak": ak, "bp": bp, "ap": ap, "sk": sk, "sp": sp, "tick_e": tick_e,
                     "tick_own": J["tick"].to_numpy(float), "t_row": gk["t_row"].to_numpy(float), "liq": J["liq"].to_numpy(float), "fam": gk["fam"].astype(str).to_numpy(),
                     "eids": [json.loads(x) if isinstance(x, str) else [] for x in gk["eids"].tolist()], "eids_missing": gk["eids_missing"].to_numpy(int),
                     "other": gk["other"].to_numpy(float), "end": J["end_ts"].to_numpy(float), "span_k": r["span_k"], "span_p": r["span_p"]})
    if not recs:
        return pd.DataFrame(), cnt
    lines = []
    for rc in recs:
        asym = abs(rc["sp"][0] - rc["sp"][1]) >= rc["tick_e"] - EPS
        if asym:
            th = 0 if rc["sp"][0] > rc["sp"][1] else 1
            order = [(th, 1 - th, "thin"), (1 - th, th, "dense")]
            cnt["asym_pairs"] = cnt.get("asym_pairs", 0) + 1
        else:
            order = [(0, 1, "sym"), (1, 0, "sym")]
            cnt["sym_pairs"] = cnt.get("sym_pairs", 0) + 1
        for i, o, line in order:
            lines.append({"market_id": rc["mk"][i], "o_market_id": rc["mk"][o], "nrkey": rc["key"], "arm": rc["arm"], "line": line,
                          "own_ds_c": _c(rc["sk"][i] - rc["sp"][i]), "o_ds_c": _c(rc["sk"][o] - rc["sp"][o]),
                          "own_spread_km1_c": _c(rc["sp"][i]), "o_spread_km1_c": _c(rc["sp"][o]), "own_spread_k_c": _c(rc["sk"][i]), "o_spread_k_c": _c(rc["sk"][o]),
                          "hb_km1": 1.0 - rc["bp"][i] - rc["bp"][o], "hb_k": 1.0 - rc["bk"][i] - rc["bk"][o],
                          "g_ask_k": rc["ak"][i] + rc["bk"][o] - 1.0, "g_bid_k": rc["bk"][i] + rc["ak"][o] - 1.0,
                          "g_ask_km1": rc["ap"][i] + rc["bp"][o] - 1.0, "g_bid_km1": rc["bp"][i] + rc["ap"][o] - 1.0,
                          "own_first": float(rc["t_row"][i] < rc["t_row"][o]), "o_liq": rc["liq"][o], "tick_e": rc["tick_e"],
                          "o_spread_k_ticks": rc["sk"][o] / rc["tick_own"][o] if rc["tick_own"][o] > 0 else math.nan,
                          "own_spread_k_ticks": rc["sk"][i] / rc["tick_own"][i] if rc["tick_own"][i] > 0 else math.nan,
                          "fam": rc["fam"][i], "o_fam": rc["fam"][o], "pair_fams": json.dumps(sorted(set(rc["fam"].tolist()))),
                          "pair_eids": json.dumps(sorted(set(rc["eids"][0]) | set(rc["eids"][1]))), "eids_missing": int(rc["eids_missing"].max()),
                          "nr_other": rc["other"][i], "span_k": rc["span_k"], "span_p": rc["span_p"],
                          "f_end_ok": float(all(np.isnan(e_) or e_ > t_dec + t["f_end_margin_h"] * 3600.0 for e_ in rc["end"]))})
    U = pd.DataFrame(lines)
    mk = U["market_id"].astype(str).to_numpy()
    K = k_block(store, k, mk, t_dec, spec)
    U["o_rewarded"] = rewarded_for(store, k, U["o_market_id"].astype(str).to_numpy())[0]
    U["o_log1p_liq"] = np.log1p(np.clip(U["o_liq"].to_numpy(float), 0, None))
    rew = K["rewarded"].to_numpy(float)
    orew = U["o_rewarded"].to_numpy(float)
    U["cell"] = np.where(np.isfinite(rew) & np.isfinite(orew), np.where(rew + orew == 2, "rr", np.where(rew + orew == 1, "ru", "uu")), "nan")
    out = pd.concat([U.reset_index(drop=True), K.reset_index(drop=True)], axis=1)
    out["event_id"] = out["nrkey"]
    out["day"] = b._utc_day(cap["start"])
    out["slot"], out["t_row"], out["kind"], out["in_scope"] = k, t_dec, KINDS["CH245"], (out["arm"] != "sports").astype(int)
    cf = (spec.get("census_fixed") or {}).get("CH245") or {}
    out["zs"] = zs_term(out["o_ds_c"].to_numpy(float), out["line"].to_numpy(object), cf)
    out["sym_line"] = (out["line"] == "sym").astype(int)
    out = b._drop_missing(out, cnt, {"log_rv24s": "rv24_undefined", "rewarded": "reward_status_nan", "o_rewarded": "o_reward_status_nan", "o_log1p_liq": "o_liquidity_missing",
                                     "tk1": "tier_missing"})
    out = assign_placebo(out, cf, cnt)
    cnt["lines"] = len(out)
    cnt["thin_units"] = int(((out["line"] == "thin") & (out["arm"] == "primary")).sum())
    return (_stamp(out, spec, commit, role) if stamp else out), cnt


def _c(x) -> float:
    """Price units to cents, rounded at 1e-10 c (removes floating-point noise of the quote differences; no economic value changes)."""
    return float(np.round(float(x) * 100.0, 10))


def zs_term(o_ds_c, line, cf: dict | None) -> np.ndarray:
    """2.3: ``zs_D = (spread_{D,k} - spread_{D,k-1}) / s_D`` on thin lines and ``zs_T = .../ s_T`` on dense lines (the census-fixed population SDs, cents);
    a sym line is scaled by ``s_D`` (a reported class; LT12 ambiguity A9). NaN while the census values are unfilled."""
    x = np.asarray(o_ds_c, float)
    ln = np.asarray(line, dtype=object)
    out = np.full(len(x), np.nan)
    sD, sT = (cf or {}).get("s_D"), (cf or {}).get("s_T")
    for m, s in ((ln == "thin", sD), (ln == "sym", sD), (ln == "dense", sT)):
        if s is not None and isinstance(s, (int, float)) and math.isfinite(s) and s > 0:
            out[m] = x[m] / float(s)
    return out


def placebo_order(keys) -> list[str]:
    """2.3: the event keys in the order of ``sha256(event key)`` (hex digest)."""
    return sorted(set(map(str, keys)), key=lambda k_: hashlib.sha256(k_.encode("utf-8")).hexdigest())


def assign_placebo(U: pd.DataFrame, cf: dict | None, cnt: dict) -> pd.DataFrame:
    """2.3 (rule 18; R1 must-fix 5): for the thin unit of event e at capture k, the unrelated pair e' is the FIRST CH245 thin unit of the same capture after e
    in the order of ``sha256(event key)`` (wrapping) such that (i) no member of e' shares a series family with any member of e and (ii) the event-id sets of
    the two pairs are disjoint (an empty set counts as disjoint: the keys always differ). Its raw dense innovation ``pl_ds_c`` (scaled by the same ``s_D``:
    ``zs_pl``) is attached; NaN with ``placebo_none`` counted when no pair qualifies. The pool is the capture's primary thin units (LT12 ambiguity A10). Reads
    only capture k's keys, families and event ids (one capture: ``U`` holds one origin)."""
    U = U.copy()
    U["pl_ds_c"], U["pl_key"] = np.nan, None
    thin = (U["line"] == "thin") & (U["arm"] == "primary")
    if not thin.any():
        U["zs_pl"] = np.nan
        return U
    T = U[thin]
    keys = placebo_order(T["nrkey"])
    pos = {k_: i for i, k_ in enumerate(keys)}
    info = {r.nrkey: (set(json.loads(r.pair_fams)), set(json.loads(r.pair_eids)), float(r.o_ds_c)) for r in T.itertuples()}
    n = len(keys)
    none = 0
    for idx, r in T.iterrows():
        fam_e, eid_e, _ = info[r["nrkey"]]
        hit = None
        for step in range(1, n):
            k2 = keys[(pos[r["nrkey"]] + step) % n]
            fam2, eid2, ds2 = info[k2]
            if fam_e & fam2:
                continue
            if eid_e & eid2:
                continue
            hit = (k2, ds2)
            break
        if hit is None:
            none += 1
            continue
        U.at[idx, "pl_key"], U.at[idx, "pl_ds_c"] = hit[0], hit[1]
    cnt["placebo_none"] = cnt.get("placebo_none", 0) + none
    sD = (cf or {}).get("s_D")
    U["zs_pl"] = U["pl_ds_c"].to_numpy(float) / float(sD) if (sD is not None and isinstance(sD, (int, float)) and math.isfinite(sD) and sD > 0) else np.nan
    return U


# --- CH244: the farmed half (section 3) ------------------------------------------------------------------------------------------------


class FeedIndex:
    """The CLOB reward feed (1.2): usable feed captures (manifest ``state=complete`` and the rows file present, the vendored LT9 ``scan_feed``) and the feed
    clock: the LAST usable feed capture whose start is before capture k - 1's start and at most 6 h earlier, else ``feed_uncovered``. A frame is read with
    the vendored LT9 ``feed_frame`` (positive-rate configurations summed) and cached (a few frames)."""

    def __init__(self, feed_roots, spec: dict, only=None) -> None:
        self.spec = spec
        self.feeds = b.scan_feed(feed_roots, only) if feed_roots else {}
        self._starts = sorted((v["start"], d) for d, v in self.feeds.items() if v["usable"])
        self._cache: dict[str, pd.DataFrame] = {}

    def clock(self, t: float) -> str | None:
        best = None
        lim = float(self.spec.get("feed", {}).get("clock_max_h", FEED_CLOCK_H)) * 3600.0
        for s, d in self._starts:
            if s < t and s >= t - lim:
                best = d
        return best

    def frame(self, d: str) -> pd.DataFrame:
        if d not in self._cache:
            if len(self._cache) >= 4:
                self._cache.pop(next(iter(self._cache)))
            self._cache[d] = b.feed_frame(self.feeds[d]["dir"], self.spec)
        return self._cache[d]

    def listing(self, t: float, condition_ids) -> pd.DataFrame:
        """Per condition_id: ``feed_cov`` (1 when a feed capture is at the clock), ``feed_listed_pos`` (listed with a positive rate), ``feed_listed_zero``
        (listed, no positive configuration), ``feed_age_h``. Never a state, control or target."""
        cid = pd.Index(np.asarray(condition_ids, dtype=str))
        d = self.clock(t)
        if d is None:
            return pd.DataFrame({"feed_cov": 0.0, "feed_listed_pos": np.nan, "feed_listed_zero": np.nan, "feed_age_h": np.nan}, index=cid)
        f = self.frame(d)
        r = f.reindex(cid)
        listed = r["rate"].notna().to_numpy() if len(f) else np.zeros(len(cid), bool)
        rate = r["rate"].to_numpy(float) if len(f) else np.full(len(cid), np.nan)
        return pd.DataFrame({"feed_cov": 1.0, "feed_listed_pos": (listed & (rate > 0)).astype(float), "feed_listed_zero": (listed & ~(rate > 0)).astype(float),
                             "feed_age_h": (t - self.feeds[d]["start"]) / 3600.0}, index=cid)


def day_fixed_status(store: SlotStore, k: int, key: str, markets) -> tuple[np.ndarray, np.ndarray]:
    """3.2 (R1 should-fix 4, ruling A9): ``unrew_{i,day} = 1 - rewarded`` at status capture s = j - 1 of the FIRST capture j of the UTC day of k at which
    the member is an eligible member of the event (LT12 ambiguity A11: eligible = in capture j's member table under the same event key). NaN when that
    status is NaN (1.4.1 case (c), a missing capture j - 1 included). Returns (unrew_day, first capture j). Reads slots <= k only."""
    mk = np.asarray(markets, dtype=str)
    out, first = np.full(len(mk), np.nan), np.full(len(mk), -1)
    todo = np.ones(len(mk), bool)
    for j in range(day_start_slot(k), k + 1):
        if not todo.any():
            break
        M = store.members(j)
        if M is None or M.empty:
            continue
        el = set(M.loc[M["nrkey"].astype(str) == str(key), "market_id"].astype(str))
        hit = np.array([todo[i] and mk[i] in el for i in range(len(mk))], bool)
        if not hit.any():
            continue
        rew, _ = rewarded_for(store, j - 1, mk[hit])
        out[hit] = 1.0 - rew
        first[hit] = j
        todo &= ~hit
    return out, first


def ch244_units(store: SlotStore, k: int, spec: dict, role: str = ROLE_UNREG, commit: str = "unknown", stamp: bool = True, feed: FeedIndex | None = None) -> tuple[pd.DataFrame, dict]:
    """CH244's lines of origin k (3.2-3.3): every member of a ladder-complete (1.4.3) event-capture with 3-10 eligible members (``arm`` ``primary``; 11+
    ``ladder11``; augmented ``augmented``; all-sports ``sports``) that is MIXED on the day-fixed statuses (>= 1 rewarded and >= 1 unrewarded among the eligible
    members at k - 1; all-rewarded / all-unrewarded event-captures are the M4 placebo arms ``allrew`` / ``allunrew``). A member whose day-fixed status is NaN
    makes the event-capture ineligible (``status_nan``). The member's own status at its k - 1 NaN -> excluded (``status_nan_unit``; never given the day-fixed
    status, re-check fix 4); differing from the day-fixed status -> excluded (``status_switched``); both still count for 'mixed' by their finite day-fixed
    status. ``shock`` = 1[max over the OTHER members of |d_j| >= 2 x tick_e,k] (``d`` the mid change over (k - 1, k], ``tick_e,k`` the largest member tick
    at k); ``shock_size`` = that maximum / tick_e,k winsorised at 20 (divided by its census scale in the model); ``lowliq`` = 1[liquidity at k - 1 below the
    event's member median] (ties 0); the tier at k - 1; the own d, |d| and spread change; ``hb_km1``; the bid share and the favourite at k - 1; ``n_members``;
    ``neg_risk_other``; K; the feed listing at the feed clock (census gate and the CLOB-agreement sensitivity only). Reads only slots <= k (and the feed)."""
    t = spec["tests"]["CH244"]
    Mp, Mk = store.members(k - 1), store.members(k)
    t_dec = store.t_dec(k)
    if Mp is None or Mk is None or store.ser(k) is None or store.ser(k - 1) is None or not math.isfinite(t_dec):
        return pd.DataFrame(), {"no_pair": 1}
    cap = store.by_slot[k]
    day = b._utc_day(cap["start"])
    pairs, cnt0 = event_pairs(Mp, Mk, spec)
    cnt: dict = {f"ev_{k_}": v for k_, v in cnt0.items()}
    spans, mdays, ecaps, conf = [], [], [], Counter()
    lo, hi = int(t["members_min"]), int(t["members_max"])
    for r in pairs.values():
        if not (lo <= r["n_k"] <= hi) or r["reason"] == "category" or r["augmented"] or r["sports_arm"]:
            continue
        sc_ = r["size_class"]
        cnt["comp_den_rows"] = cnt.get("comp_den_rows", 0) + r["n_k"]
        cnt[f"comp_den_rows_{sc_}"] = cnt.get(f"comp_den_rows_{sc_}", 0) + r["n_k"]
        if r["reason"] in ("ok", "receipt_span"):
            cnt["comp_num_rows"] = cnt.get("comp_num_rows", 0) + r["n_k"]
            cnt[f"comp_num_rows_{sc_}"] = cnt.get(f"comp_num_rows_{sc_}", 0) + r["n_k"]
            cnt["pair_complete_events"] = cnt.get("pair_complete_events", 0) + 1
            spans.append(max(r["span_k"], r["span_p"]))
            if r["reason"] == "ok":
                cnt["span_ok_events"] = cnt.get("span_ok_events", 0) + 1
    parts = []
    feed_t = store.by_slot[k - 1]["start"] if (k - 1) in store.by_slot else math.nan
    for r in pairs.values():
        n = r["n_k"]
        if n < lo or r["reason"] == "category":
            continue
        gk = r["gk"].set_index("market_id")
        mk = gk.index.astype(str).to_numpy()
        primary_universe = (n <= hi) and not r["augmented"] and not r["sports_arm"]
        dfix, _first = day_fixed_status(store, k, r["key"], mk)
        if primary_universe:
            mdays.extend((m_, day, bool(np.isfinite(v_))) for m_, v_ in zip(mk, dfix, strict=True))
        if r["reason"] != "ok":
            continue
        arm = "augmented" if r["augmented"] else ("sports" if r["sports_arm"] else ("ladder11" if n > hi else "primary"))
        own, own_case = rewarded_for(store, k - 1, mk)
        own_unrew = 1.0 - own
        rs_p = store.reward_status(k - 1)
        simple = rs_p["simple_nonempty"].reindex(pd.Index(mk)).to_numpy(float) if rs_p is not None else np.full(len(mk), np.nan)
        if arm == "primary":
            for a_, s_ in zip(own, simple, strict=True):
                conf[(("nan" if not np.isfinite(a_) else str(int(a_))), ("nan" if not np.isfinite(s_) else str(int(s_))))] += 1
            for c_ in own_case:
                conf[("case", str(c_))] += 1
        if not np.isfinite(dfix).all():
            cnt["status_nan_rows"] = cnt.get("status_nan_rows", 0) + n
            cnt["status_nan_event_captures"] = cnt.get("status_nan_event_captures", 0) + 1
            continue
        mixed = bool((dfix == 0).any() and (dfix == 1).any())
        if arm == "primary":
            sfin = np.isfinite(simple)
            mixed_simple = bool(sfin.all() and (simple == 0).any() and (simple == 1).any())
            cnt["mixed_carry_event_captures"] = cnt.get("mixed_carry_event_captures", 0) + int(mixed)
            cnt["mixed_simple_event_captures"] = cnt.get("mixed_simple_event_captures", 0) + int(mixed_simple)
        if not mixed:
            arm = {"primary": "allunrew" if (dfix == 1).all() else "allrew"}.get(arm, arm)
            if arm not in ("allrew", "allunrew"):
                continue
        J, P = store.ser(k).reindex(pd.Index(mk)), store.ser(k - 1).reindex(pd.Index(mk))
        bk, ak, bp, ap = (x.to_numpy(float) for x in (J["bid"], J["ask"], P["bid"], P["ask"]))
        if not (np.isfinite(bk).all() and np.isfinite(bp).all()):
            cnt["event_not_in_series"] = cnt.get("event_not_in_series", 0) + 1
            continue
        mid_k, mid_p = (bk + ak) / 2.0, (bp + ap) / 2.0
        dj = mid_k - mid_p
        tick_k = float(np.nanmax(gk["tick"].to_numpy(float)))
        a = np.abs(dj)
        oth = np.array([np.max(np.delete(a, i)) for i in range(n)])
        shock = (oth >= SHOCK_TICKS * tick_k - EPS).astype(float)
        ssize = np.minimum(oth / tick_k, SHOCK_SIZE_WINSOR) if tick_k > 0 else np.full(n, np.nan)
        if arm == "primary":
            ecaps.append((r["key"], k, day, float(a.max() >= SHOCK_TICKS * tick_k - EPS)))
        liq_p = P["liq"].to_numpy(float)
        med = float(np.nanmedian(liq_p)) if np.isfinite(liq_p).any() else math.nan
        lowliq = np.where(np.isfinite(liq_p) & math.isfinite(med), (liq_p < med - 1e-12).astype(float), np.nan)
        sum_bp = float(bp.sum())
        rank = pd.Series(mid_p).rank(ascending=False, method="min").to_numpy()
        ok, _J, _P = _member_ok(store, k, mk, t_dec, spec, t["end_margin_h"], cnt, "m_")
        nanu = ~np.isfinite(own)
        sw = np.isfinite(own) & (own_unrew != dfix)
        cnt["status_nan_unit"] = cnt.get("status_nan_unit", 0) + int((ok & nanu).sum())
        for lab, v_ in (("0", 0.0), ("1", 1.0)):
            cnt[f"status_switched_unrew{lab}"] = cnt.get(f"status_switched_unrew{lab}", 0) + int((ok & sw & (dfix == v_)).sum())
            cnt[f"status_kept_unrew{lab}"] = cnt.get(f"status_kept_unrew{lab}", 0) + int((ok & ~sw & ~nanu & (dfix == v_)).sum())
        keep = ok & ~nanu & ~sw
        if not keep.any():
            continue
        end = J["end_ts"].to_numpy(float)
        with np.errstate(invalid="ignore"):
            f_end = (np.isnan(end) | (end > t_dec + t["f_end_margin_h"] * 3600.0)).astype(float)
        tier_p = tier_of(liq_p)
        u = pd.DataFrame({"market_id": mk, "nrkey": r["key"], "arm": arm, "n_members": float(n), "size_class": r["size_class"], "unrew": dfix, "own_unrew_km1": own_unrew,
                          "rew_case_km1": own_case, "shock": shock, "shock_size_raw": ssize, "lowliq": lowliq, "tier_km1": tier_p, "absd": np.abs(dj), "own_ds_c": np.round(((ak - bk) - (ap - bp)) * 100.0, 10),
                          "hb_km1": 1.0 - sum_bp, "bid_share": bp / sum_bp if sum_bp > 0 else np.nan, "fav": (rank == 1).astype(float), "nr_other": gk["other"].to_numpy(float),
                          "tick_e": tick_k, "spread_k_c": (ak - bk) * 100.0, "bid_k": bk, "ask_k": ak, "f_end_ok": f_end, "condition_id": gk["condition_id"].astype(str).to_numpy(),
                          "fam": gk["fam"].astype(str).to_numpy(), "span_k": r["span_k"], "span_p": r["span_p"], "liq_km1": liq_p})[keep]
        parts.append(u)
    cnt["_spans"], cnt["_mdays"], cnt["_ecaps"], cnt["_conf"] = spans, mdays, ecaps, dict(conf)
    if not parts:
        return pd.DataFrame(), cnt
    U = pd.concat(parts, ignore_index=True)
    K = k_block(store, k, U["market_id"].astype(str).to_numpy(), t_dec, spec)
    out = pd.concat([U, K], axis=1)
    for nm, v in tier_dummies(out["tier_km1"].to_numpy(float), "tl").items():
        out[nm] = v
        out[f"{nm}_x_shock"] = v * out["shock"].to_numpy(float)
    out["shock_x_unrew"] = out["shock"] * out["unrew"]
    out["shock_x_lowliq"] = out["shock"] * out["lowliq"]
    cf = (spec.get("census_fixed") or {}).get("CH244") or {}
    sc = cf.get("shock_size_scale")
    out["shock_sz"] = out["shock_size_raw"] / float(sc) if (sc is not None and isinstance(sc, (int, float)) and math.isfinite(sc) and sc > 0) else np.nan
    if feed is not None and math.isfinite(feed_t):
        fl = feed.listing(feed_t, out["condition_id"].to_numpy())
        for c_ in fl.columns:
            out[c_] = fl[c_].to_numpy(float)
    else:
        out["feed_cov"], out["feed_listed_pos"], out["feed_listed_zero"], out["feed_age_h"] = 0.0, np.nan, np.nan, np.nan
    out["event_id"] = out["nrkey"]
    out["day"], out["slot"], out["t_row"], out["kind"] = day, k, t_dec, KINDS["CH244"]
    out["in_scope"] = (out["arm"] != "sports").astype(int)
    out["line"] = "member"
    out = b._drop_missing(out, cnt, {"log_rv24s": "rv24_undefined", "rewarded": "reward_status_nan", "tl1": "tier_missing", "lowliq": "liquidity_missing"})
    cnt["lines"] = len(out)
    cnt["primary_units"] = int((out["arm"] == "primary").sum())
    return (_stamp(out, spec, commit, role) if stamp else out), cnt


def _stamp(df: pd.DataFrame, spec: dict, commit: str, role: str) -> pd.DataFrame:
    df = df.drop(columns=[c for c in ("frozen_utc", "code_commit", "spec_sha", "code_sha", "role") if c in df.columns])
    df["frozen_utc"] = iso(now_ts())
    df["code_commit"], df["spec_sha"], df["code_sha"], df["role"] = commit, spec["_sha256"][:16], reader_sha(), role
    return df


# --- the lag-slot loaders (7): twins are readings of captures k + 2 and k + 3 and return the twin term ONLY --------------------------------


def _members_of(cap_dir: Path, spec: dict) -> pd.DataFrame:
    return members12_frame(load_rows12(cap_dir), load_ext12(cap_dir), spec)


def twin_components_mirror(dir_a: Path, dir_b: Path, spec: dict) -> pd.DataFrame:
    """CH245's twin (1.9): the raw spread innovation over (k + 2, k + 3] of each member of every two-member event that is pair-complete at k + 2 and k + 3
    (1.4.3, the 120 s span included), indexed by (nrkey, market_id). READER side; the census goes through :func:`lag_twin_zs`."""
    pairs, _ = event_pairs(_members_of(dir_a, spec), _members_of(dir_b, spec), spec)
    rows = []
    for r in pairs.values():
        if r["n_k"] != 2 or r["reason"] != "ok":
            continue
        gk, gp = r["gk"].set_index("market_id"), r["gp"].set_index("market_id")
        gp = gp.reindex(gk.index)
        ds = np.round(((gk["ask"] - gk["bid"]) - (gp["ask"] - gp["bid"])).to_numpy(float) * 100.0, 10)
        for m_, d_ in zip(gk.index.astype(str), ds, strict=True):
            rows.append((r["key"], m_, d_))
    return pd.DataFrame(rows, columns=["nrkey", "market_id", "ds_tw_c"]).set_index(["nrkey", "market_id"])


def lag_twin_zs(dir_a: Path, dir_b: Path, keys, o_markets, lines, cf: dict, spec: dict) -> np.ndarray:
    """The CENSUS lag-slot loader of CH245: ONLY the twin state ``zs_tw`` (the SAME pair's SAME other member's innovation over (k + 2, k + 3], scaled as the
    lead: ``s_D`` on thin lines, ``s_T`` on dense lines); NaN unless the pair is complete at k + 2 and k + 3."""
    c = twin_components_mirror(dir_a, dir_b, spec)
    idx = pd.MultiIndex.from_arrays([np.asarray(keys, dtype=str), np.asarray(o_markets, dtype=str)])
    raw = c["ds_tw_c"].reindex(idx).to_numpy(float) if len(c) else np.full(len(idx), np.nan)
    return zs_term(raw, lines, cf)


def twin_components_shock(dir_a: Path, dir_b: Path, spec: dict) -> pd.DataFrame:
    """CH244's twin (1.9): the shock over (k + 2, k + 3] of each member of every ladder-complete event-capture pair at k + 2 and k + 3 (3-10 members or
    more, the 120 s span included): 1[max over the other members of |d_j| >= 2 x tick_e,k+3], indexed by (nrkey, market_id). READER side."""
    pairs, _ = event_pairs(_members_of(dir_a, spec), _members_of(dir_b, spec), spec)
    rows = []
    for r in pairs.values():
        if r["n_k"] < 3 or r["reason"] != "ok":
            continue
        gk, gp = r["gk"].set_index("market_id"), r["gp"].set_index("market_id")
        gp = gp.reindex(gk.index)
        d = (((gk["bid"] + gk["ask"]) - (gp["bid"] + gp["ask"])) / 2.0).to_numpy(float)
        tick = float(np.nanmax(gk["tick"].to_numpy(float)))
        a = np.abs(d)
        for i, m_ in enumerate(gk.index.astype(str)):
            rows.append((r["key"], m_, float(np.max(np.delete(a, i)) >= SHOCK_TICKS * tick - EPS) if math.isfinite(tick) else math.nan))
    return pd.DataFrame(rows, columns=["nrkey", "market_id", "shock_tw"]).set_index(["nrkey", "market_id"])


def lag_twin_shock(dir_a: Path, dir_b: Path, keys, markets, spec: dict) -> np.ndarray:
    """The CENSUS lag-slot loader of CH244: ONLY the twin shock flag over (k + 2, k + 3] (NaN unless the member's event is ladder-complete there)."""
    c = twin_components_shock(dir_a, dir_b, spec)
    idx = pd.MultiIndex.from_arrays([np.asarray(keys, dtype=str), np.asarray(markets, dtype=str)])
    return c["shock_tw"].reindex(idx).to_numpy(float) if len(c) else np.full(len(idx), np.nan)


# --- outcomes (targets) and the reader (1.3, 1.5) -------------------------------------------------------------------------------------------


def _look(ser: pd.DataFrame | None, mids, col: str) -> np.ndarray:
    if ser is None:
        return np.full(len(mids), np.nan)
    return ser[col].reindex(pd.Index(np.asarray(mids, dtype=str))).to_numpy(float)


def outcome_h1(mids, by_slot: dict, j: int, root: Path, missing: bool) -> pd.DataFrame:
    """The status (1.5) and the quote of each line's market at slot ``j`` = k + 1: ``two_sided`` lines carry bid, ask and the spread (cents)."""
    cap = by_slot.get(j)
    ser = None if missing else read_series12(root, cap["id"])
    st = None if missing else read_status12(root, cap["id"])
    out = pd.DataFrame({"market_id": np.asarray(mids, dtype=str)})
    out["status"] = status_codes(ser, st, mids, missing)
    out["bid"], out["ask"] = _look(ser, mids, "bid"), _look(ser, mids, "ask")
    out["spread_c"] = (out["ask"] - out["bid"]) * 100.0
    out["cap_start"] = np.nan if missing else cap["start"]
    return out


def enabled_kinds(spec: dict) -> dict[str, bool]:
    """A kind is collected only if its test is in ``k_tests`` (1.12); null ``k_tests`` (DRAFT) collects both kinds (development only)."""
    ks = spec.get("k_tests")
    return {KINDS[t]: (ks is None or t in ks) for t in TESTS}


FROZEN_MARKERS = (*MARKERS, ".empty.csv.gz")


def _marker(p: Path, suffix: str) -> Path:
    return p.with_name(p.name.replace(".csv.gz", suffix))


def run_once(*, snapshot_root: Path = SNAPSHOT_ROOT, feed_root: Path | None = FEED_ROOT, root: Path = OUT_ROOT, spec: dict | None = None, now: float | None = None,
             max_items: int = 80, allow_late: bool = False, series_only: bool = False, window_start_utc: str | None = None) -> dict:
    """Series, freezes, due outcomes and due twins for everything new. Idempotent (write-once). ``allow_late`` is for DRY RUNS on past captures with an
    unpinned spec only (L6). ``series_only`` is ``backfill-series``. An internal run lock (L15)."""
    spec = spec or load_spec()
    if allow_late and spec.get("_pinned"):
        raise ValueError("allow_late is for dry runs with an unpinned spec only")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with open(root / "run.lock", "a") as lk:
        try:
            fcntl.flock(lk.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "locked", "written": 0, "run_utc": iso(now_ts() if now is None else now)}
        return _run_locked(snapshot_root=snapshot_root, feed_root=feed_root, root=root, spec=spec, now=now, max_items=max_items, allow_late=allow_late,
                           series_only=series_only, window_start_utc=window_start_utc)


def _run_locked(*, snapshot_root: Path, feed_root, root: Path, spec: dict, now: float | None, max_items: int, allow_late: bool, series_only: bool,
                window_start_utc: str | None) -> dict:
    now = now_ts() if now is None else now
    commit = git_commit()
    stats = {"run_utc": iso(now), "code_commit": commit, "spec_sha": spec["_sha256"][:16], "pinned": spec["_pinned"], "written": 0, "series": 0, "outcomes": 0,
             "twins": 0, "refused_late": 0, **{k_: 0 for k_ in KINDS.values()}}
    if root.exists() and dir_bytes(root) > DISK_CAP_BYTES:
        stats["status"] = "disk_cap"
        append_jsonl(root / "passes.jsonl", [{"kind": "disk_cap", **stats}])
        return stats
    t_reg, t_end = epoch(window_start_utc or spec["registered_utc"]), epoch(spec["end_utc"])
    kinds = enabled_kinds(spec)
    stats["kinds_off"] = sorted(n for n, on in kinds.items() if not on)
    st = b.State(root)
    by_slot = b.scan_captures(snapshot_root, st, spec)
    st.save()
    log: list[dict] = []
    budget = max_items
    lo = t_reg - 14 * GRID_S - DAY_S  # the 12-slot look-back plus the first slots of the day (day-fixed status) and the carry window
    hi = t_end + 4 * GRID_S + b.SLOT_TOL_S
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (lo <= c["start"] < hi) or budget <= 0:
            continue
        if not series_ready(root, {k: c}, (k,)):
            info = write_series12(root, c, spec)
            if info.get("written"):
                stats["series"] += 1
                budget -= 1
                log.append({"kind": "series", "id": c["id"], "slot": k, **info, "written_utc": iso(now_ts())})
    if series_only:
        stats["status"] = "wrote" if stats["series"] else "nothing_new"
        stats["written"] = stats["series"]
        for r in log:
            r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
        append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
        return stats
    store = SlotStore(root, by_slot, spec, cache_slots=30)
    feed = FeedIndex([feed_root], spec) if (kinds["mixedlad"] and feed_root is not None and Path(feed_root).exists()) else None
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (c["start"] < t_end) or c["start"] < t_reg:
            continue
        role = role_of(c["start"], spec["registered_utc"], spec["end_utc"], spec["_pinned"])
        for test in TESTS:
            kind = KINDS[test]
            p = root / kind / "frozen" / f"{c['id']}.csv.gz"
            if not kinds[kind] or p.exists() or any(_marker(p, s_).exists() for s_ in FROZEN_MARKERS) or budget <= 0:
                continue
            if (k - 1) in by_slot and by_slot[k - 1]["start"] < t_reg:  # 1.1: a unit's oldest state input is capture k - 1 (lt12_boundary)
                write_once_csv(_marker(p, ".boundary.csv.gz"), pd.DataFrame({"boundary": [1], "slot": [k]}))
                log.append({"kind": f"{kind}_lt12_boundary", "id": c["id"], "slot": k})
                continue
            late = not allow_late and is_late(k + 1, now, spec)
            if late:
                stats["refused_late"] += 1
                write_once_csv(_marker(p, ".late.csv.gz"), pd.DataFrame({"late": [1], "checked_utc": [iso(now)]}))
                log.append({"kind": f"{kind}_refused_late", "id": c["id"], "slot": k, "written_utc": iso(now_ts())})
                continue
            if (k - 1) not in by_slot:
                if target_state(by_slot, k - 1, now, spec) == "pending":
                    continue
                write_once_csv(_marker(p, ".noprev.csv.gz"), pd.DataFrame({"noprev": [1]}))
                log.append({"kind": f"{kind}_no_previous_slot", "id": c["id"], "slot": k})
                continue
            if not series_ready(root, by_slot, range(min(k - 12, day_start_slot(k) - 1), k + 1)):
                continue
            if test == "CH245":
                units, cnt = ch245_units(store, k, spec, role, commit)
            else:
                units, cnt = ch244_units(store, k, spec, role, commit, feed=feed)
            cnt = {k_: v_ for k_, v_ in cnt.items() if not k_.startswith("_")}
            if units.empty:
                write_once_csv(_marker(p, ".empty.csv.gz"), pd.DataFrame({"slot": [k], "empty": [1], "role": [role]}))
                log.append({"kind": f"{kind}_empty", "id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
                continue
            if write_once_csv(p, units):
                stats[kind] += 1
                budget -= 1
                log.append({"kind": f"{kind}_frozen", "id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
    for kind, on in kinds.items():
        if not on:
            continue
        fdir = root / kind / "frozen"
        for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
            if p.name.endswith(FROZEN_MARKERS) or budget <= 0:
                continue
            fid = p.name[:-7]
            fr = pd.read_csv(p, usecols=["market_id", "slot", "nrkey", "line", *(["o_market_id"] if kind == "mirror" else [])], dtype={"market_id": str, "nrkey": str, "o_market_id": str})
            if fr.empty:
                continue
            k = int(fr["slot"].iloc[0])
            mids = pd.unique(fr["market_id"].to_numpy())
            op = root / kind / "outcomes" / f"{fid}.h1.csv.gz"
            if not op.exists() and budget > 0:
                state = target_state(by_slot, k + 1, now, spec)
                if state != "pending" and not (state == "ready" and not series_ready(root, by_slot, (k + 1,))):
                    out = outcome_h1(mids, by_slot, k + 1, root, state == "missing")
                    if write_once_csv(op, out):
                        stats["outcomes"] += 1
                        budget -= 1
                        log.append({"kind": f"{kind}_outcome", "id": fid, "target_slot": k + 1, "target": state, "rows": len(out), "written_utc": iso(now_ts())})
            tp = root / kind / "twins" / f"{fid}.csv.gz"
            if tp.exists() or budget <= 0:
                continue
            sa, sb = target_state(by_slot, k + 2, now, spec), target_state(by_slot, k + 3, now, spec)
            if "pending" in (sa, sb):
                continue
            out = twin_frame(kind, fr, by_slot, k, sa == "ready" and sb == "ready", spec)
            if write_once_csv(tp, out):
                stats["twins"] += 1
                budget -= 1
                log.append({"kind": f"{kind}_twins", "id": fid, "rows": len(out), "both_ready": bool(sa == "ready" and sb == "ready"), "written_utc": iso(now_ts())})
    stats["written"] = sum(stats[k_] for k_ in ("series", "outcomes", "twins", *KINDS.values()))
    stats["status"] = "wrote" if stats["written"] else "nothing_new"
    for r in log:
        r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
    append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
    return stats


def twin_frame(kind: str, fr: pd.DataFrame, by_slot: dict, k: int, both_ready: bool, spec: dict) -> pd.DataFrame:
    """The far-future twin readings of one frozen file (1.9): written once, after captures k + 2 and k + 3 exist (NaN, ``tw_ok`` 0 when either is missing).
    Keyed by (market_id, line): CH245 the raw innovation of the line's OTHER member over (k + 2, k + 3] in the same pair; CH244 the member's twin shock."""
    base = fr[["market_id", "line", "nrkey", *(["o_market_id"] if kind == "mirror" else [])]].drop_duplicates(["market_id", "line"]).reset_index(drop=True)
    if not both_ready:
        return pd.DataFrame({"market_id": base["market_id"], "line": base["line"], "tw_ok": 0})
    da, db = by_slot[k + 2]["dir"], by_slot[k + 3]["dir"]
    if kind == "mirror":
        c = twin_components_mirror(da, db, spec)
        idx = pd.MultiIndex.from_arrays([base["nrkey"].astype(str), base["o_market_id"].astype(str)])
        raw = c["ds_tw_c"].reindex(idx).to_numpy(float) if len(c) else np.full(len(base), np.nan)
        return pd.DataFrame({"market_id": base["market_id"], "line": base["line"], "tw_ok": np.isfinite(raw).astype(int), "o_ds_tw_c": raw})
    c = twin_components_shock(da, db, spec)
    idx = pd.MultiIndex.from_arrays([base["nrkey"].astype(str), base["market_id"].astype(str)])
    sh = c["shock_tw"].reindex(idx).to_numpy(float) if len(c) else np.full(len(base), np.nan)
    return pd.DataFrame({"market_id": base["market_id"], "line": base["line"], "tw_ok": np.isfinite(sh).astype(int), "shock_tw": sh})


# --- operational counts (never reads a price, a spread, a volume, a liquidity or a target) ------------------------------------------------


def _read_ops(path: Path, cols: list[str]) -> pd.DataFrame:
    bad = [c for c in cols if c not in OPS_COLS]
    if bad:
        raise ValueError(f"ops_stats may not read {bad}")
    head = pd.read_csv(path, nrows=0).columns
    use = [c for c in cols if c in head]
    return pd.read_csv(path, usecols=use) if use else pd.DataFrame()


def ops_stats(root: Path = OUT_ROOT) -> dict:
    """1.6: file, line, role, class, panel and status counts of ``live_tests12/``; reads no price, spread, volume or liquidity column (unit-tested)."""
    root = Path(root)
    out: dict = {"root": str(root), "bytes": dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "members", *(f"{k}/frozen" for k in KINDS.values()), *(f"{k}/outcomes" for k in KINDS.values()), *(f"{k}/twins" for k in KINDS.values())):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith(FROZEN_MARKERS)]), **{s_.split(".")[1]: len([f for f in files if f.name.endswith(s_)]) for s_ in FROZEN_MARKERS}}
    counts, status = {}, {}
    cols = {"mirror": ["role", "kind", "line", "arm", "in_scope", "cell"], "mixedlad": ["role", "kind", "arm", "in_scope", "size_class"]}
    for kind, cl in cols.items():
        d = root / kind / "frozen"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            if f.name.endswith(FROZEN_MARKERS):
                continue
            s_ = _read_ops(f, cl)
            for c in s_.columns:
                for kk, v in s_[c].value_counts().items():
                    counts[f"{kind}:{c}:{kk}"] = counts.get(f"{kind}:{c}:{kk}", 0) + int(v)
        d = root / kind / "outcomes"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            s_ = _read_ops(f, ["status"])
            for kk, v in s_["status"].value_counts().items():
                status[f"{kind}:h1:{kk}"] = status.get(f"{kind}:h1:{kk}", 0) + int(v)
    out.update(line_counts=counts, outcome_status_counts=status)
    return out


# --- the model columns (1.7, 2.3, 3.3) ---------------------------------------------------------------------------------------------


CONTROLS = {
    # 2.3: the own innovation, the other (dense) book's level at k - 1, hb_{k-1}, the other book's log1p liquidity and rewarded_k, K (own spread at k in K)
    "CH245": ["own_ds_c", "o_spread_km1_c", "hb_km1", "o_log1p_liq", "o_rewarded", *K_COMMON],
    # 3.3: unrew, shock, shock_size, tier_{k-1} dummies and tier x shock, own d (in K), |d|, own spread change, hb_{k-1}, bid share, favourite, n_members, neg_risk_other, K
    "CH244": ["unrew", "shock", "shock_sz", "tl1", "tl2", "tl3", "tl1_x_shock", "tl2_x_shock", "tl3_x_shock", "absd", "own_ds_c", "hb_km1", "bid_share", "fav", "n_members", "nr_other", *K_COMMON],
}
SHIFT_RAW = {"CH245": ("zs",), "CH244": ("shock", "shock_sz")}  # 1.8: the raw states the gate shifts (CH244: shock_size shifts with shock, ruling B3)


def fee_dummies(df: pd.DataFrame, min_share: float = 0.005) -> tuple[pd.DataFrame, list[str]]:
    """1.7: the non-sports ``fee_category`` dummies of the block K (LT12 ambiguity A12 = LT11 A9: every category holding at least 0.5% of the frame's units
    except the most frequent one, the reference)."""
    cat = pd.Series([b._norm_cat(v) or "unknown" for v in df["fee_cat"]], index=df.index) if "fee_cat" in df else pd.Series("unknown", index=df.index)
    share = cat.value_counts(normalize=True)
    keep = [c for c in share.index[1:] if share[c] >= min_share]
    out = df.copy()
    names = []
    for c in keep:
        nm = "fc_" + re.sub(r"[^a-z0-9]+", "_", c)
        out[nm] = (cat == c).astype(float)
        names.append(nm)
    return out, names


def controls_for(test: str, df: pd.DataFrame, extra: list[str] | None = None) -> list[str]:
    base = [c for c in CONTROLS[test] if c in df.columns]
    return [*base, *[c for c in df.columns if str(c).startswith("fc_")], *(extra or [])]


# --- the expanding-past event x UTC-day demeaning (1.7) and the event-phase state-shift gate (1.8, R1 must-fix 6) -------------------------------


def stratum_codes(df: pd.DataFrame) -> np.ndarray:
    """The demeaning stratum of both tests: event x UTC day (1.7)."""
    return pd.factorize(df["event_id"].astype(str) + "|" + df["day"].astype(str))[0]


def strict_expanding_demean(codes: np.ndarray, slot: np.ndarray, x: np.ndarray) -> np.ndarray:
    """``x`` minus the mean of the same stratum's finite values at STRICTLY EARLIER captures (``slot`` < own slot); NaN when the stratum has no earlier finite
    value (the first capture of each stratum drops) or ``x`` is NaN. LT12 ambiguity A13: units of the same capture are not 'earlier' (CH244 holds several
    members a capture; CH245 one unit a capture, where this equals the vendored ``expanding_demean``). Causal: row t uses only rows of earlier slots."""
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return x.copy()
    codes, slot = np.asarray(codes), np.asarray(slot, float)
    o = np.lexsort((slot, codes))
    cs, ss, xs = codes[o], slot[o], x[o]
    fin = np.isfinite(xs)
    v = np.where(fin, xs, 0.0)
    blk_start = np.r_[True, (cs[1:] != cs[:-1]) | (ss[1:] != ss[:-1])]
    blk = np.cumsum(blk_start) - 1
    bsum = np.bincount(blk, weights=v)
    bcnt = np.bincount(blk, weights=fin.astype(float))
    bcode = cs[blk_start]
    first_blk = np.r_[True, bcode[1:] != bcode[:-1]]
    gstart = np.maximum.accumulate(np.where(first_blk, np.arange(len(bsum)), 0))
    csum, ccnt = np.cumsum(bsum), np.cumsum(bcnt)
    prev_s = csum - bsum - (csum[gstart] - bsum[gstart])
    prev_c = ccnt - bcnt - (ccnt[gstart] - bcnt[gstart])
    mean_b = np.where(prev_c > 0, prev_s / np.maximum(prev_c, 1), np.nan)
    out = np.empty(n)
    out[o] = xs - mean_b[blk]
    return out


def demeaned_frame(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """The frame with ``cols`` replaced by their expanding-past event x UTC-day demeaned values (the analysis' regressors). Marked
    ``attrs['lt12_demeaned'] = True``: the gate refuses such a frame (it shifts RAW states only, 1.8)."""
    out = df.copy()
    codes, slot = stratum_codes(df), df["slot"].to_numpy(float)
    for c in cols:
        out[c] = strict_expanding_demean(codes, slot, df[c].to_numpy(float))
    out.attrs["lt12_demeaned"] = True
    out.attrs["lt12_demeaned_cols"] = list(cols)
    return out


def cr1_event_t(y: np.ndarray, x: np.ndarray, Z: np.ndarray, ev: np.ndarray, sign: int = 1) -> dict:
    """The tested coefficient's event-clustered CR1 t (1.7's CR1, computed as ``battery.beta_test`` computes ``z_event``: Frisch-Waugh-Lovell partialling
    on ``[1, Z]``, scores clustered by event with ``G / (G - 1)`` and ``(n - 1) / (n - k)``, ``k`` = columns of ``[1, Z]`` + 1)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    n = len(y)
    Z1 = np.column_stack([np.ones(n), Z]) if Z.size else np.ones((n, 1))
    cx, *_ = np.linalg.lstsq(Z1, x, rcond=None)
    cy, *_ = np.linalg.lstsq(Z1, y, rcond=None)
    xt, yt = x - Z1 @ cx, y - Z1 @ cy
    sxx = float(xt @ xt)
    if sxx <= 1e-12 * max(1, n):
        return {"testable": False, "t": math.nan}
    beta = float(xt @ yt / sxx)
    e = yt - beta * xt
    sc = xt * e / sxx
    codes, uniq = pd.factorize(np.asarray(ev))
    g = len(uniq)
    s = np.bincount(codes, weights=sc, minlength=g)
    va = float((s**2).sum() * g / max(g - 1, 1))
    adj = (n - 1) / max(n - (Z1.shape[1] + 1), 1)
    se = math.sqrt(va * adj)
    return {"testable": True, "beta": beta, "se": se, "t": sign * beta / se if se > 0 else 0.0, "n": n, "g": g}


def event_phase_index(df: pd.DataFrame, rows: np.ndarray, min_captures: int) -> dict:
    """The event-phase index (LT11 CH233's, vendored as ``b.event_index_fl_gate``; the same rule): per event e, ``I_e`` = the ordered captures at which e has
    at least one unit (``rows``), ``n_e = |I_e|``, ``s_e = max(4, ceil(n_e / 4))``, offsets drawn from ``[s_e, n_e - s_e]``. Events with ``n_e <
    min_captures`` (16) are outside the gate sample (counted)."""
    ev = df["event_id"].astype(str).to_numpy()[rows]
    sl = df["slot"].to_numpy(int)[rows]
    plan, excluded_events, excluded_rows = {}, 0, 0
    for e in pd.unique(ev):
        m = ev == e
        pos = np.unique(sl[m])
        n_e = len(pos)
        s_e = max(4, math.ceil(n_e / 4))
        if n_e < min_captures or n_e - s_e < s_e:
            excluded_events += 1
            excluded_rows += int(m.sum())
            continue
        plan[e] = {"positions": pos, "n_e": n_e, "s_e": s_e}
    return {"plan": plan, "excluded_events": excluded_events, "excluded_rows": excluded_rows}


def _recompute(test: str, X: pd.DataFrame) -> None:
    """CH244: ``shock x unrew`` and ``tier x shock`` recomputed from the (shifted) shock with the unit's own ``unrew`` and tier (1.8)."""
    if test == "CH244":
        X["shock_x_unrew"] = X["shock"].to_numpy(float) * X["unrew"].to_numpy(float)
        for i in (1, 2, 3):
            if f"tl{i}" in X:
                X[f"tl{i}_x_shock"] = X[f"tl{i}"].to_numpy(float) * X["shock"].to_numpy(float)
        if "shock_x_lowliq" in X and "lowliq" in X:
            X["shock_x_lowliq"] = X["shock"].to_numpy(float) * X["lowliq"].to_numpy(float)


def event_day_state_shift_gate(df: pd.DataFrame, y: np.ndarray, term: str, controls: list[str], *, test: str, draws: int, seed: int, min_captures: int = 16,
                               sign: int = 1) -> dict:
    """The event-phase STATE-SHIFT gate of LT12 (1.8, R1 must-fix 6, re-check fix 1). New code (not a vendored copy), built from LT5's offset rule and LT11
    CH233's event-phase index (:func:`event_phase_index`).

    ``df`` holds the RAW regressors (refused by assertion when it carries ``attrs['lt12_demeaned']``). Units = rows with a finite raw term and finite raw
    controls. Gate sample = the units of events with ``n_e >= 16`` captures on their index; the others are excluded (counted). For each of ``draws`` draws and
    each gate event ONE offset ``o`` is drawn from ``[s_e, n_e - s_e]``; the RAW state is shifted, never a demeaned value: CH245's unit at index position t
    takes the raw ``zs`` of position ``(t + o) mod n_e`` (one unit a capture); CH244's member takes ITS OWN raw ``shock`` and ``shock_sz`` of position
    ``(t + o) mod n_e`` (ruling B3), and ``shock x unrew`` / ``tier x shock`` are recomputed with the unit's own ``unrew`` and tier. A member without a unit at
    the shifted position is OMITTED from that draw (never filled, never borrowed; the omitted share is returned). Then the expanding-past event x UTC-day
    demeaning is RE-APPLIED to every shifted regressor in each unit's real stratum and real order (over the draw's non-omitted units); every other regressor
    and the target keep their analysis values; the full model is refitted on the gate sample. Statistic: the tested coefficient's event-clustered CR1 t
    (:func:`cr1_event_t`, clusters = the gate sample's events), computed identically for the OBSERVED fit, which is refitted on the same gate sample (never
    taken from the all-units fit), and for every draw. ``p_perm = (1 + #{t_draw >= t_obs}) / (1 + draws)``; passes if < 0.05."""
    assert not df.attrs.get("lt12_demeaned"), "event_day_state_shift_gate shifts RAW states only: a pre-demeaned frame is refused (1.8, R1 must-fix 6)"
    assert test in SHIFT_RAW, test
    shift = [c for c in SHIFT_RAW[test] if c in df]
    derived = {"CH245": [], "CH244": [c for c in ("shock_x_unrew", "tl1_x_shock", "tl2_x_shock", "tl3_x_shock", "shock_x_lowliq") if c in df]}[test]
    reg = [term, *controls]
    if test == "CH245":
        assert term in shift, "CH245's tested term is the shifted raw state zs"
    yv = np.asarray(y, float)
    raw = df[reg].to_numpy(float)
    units = np.flatnonzero(np.all(np.isfinite(raw), axis=1))
    idx = event_phase_index(df, units, min_captures)
    plan = idx["plan"]
    gate_rows = units[np.isin(df["event_id"].astype(str).to_numpy()[units], list(plan))]
    if len(gate_rows) < 10:
        return {"testable": False, "passes": False, "reason": f"no event with >= {min_captures} captures on its index", "excluded_events": idx["excluded_events"]}
    G = df.iloc[gate_rows].reset_index(drop=True)
    yG = yv[gate_rows]
    changed = set(shift) | set(derived)
    D = demeaned_frame(df, reg).iloc[gate_rows].reset_index(drop=True)  # analysis values (demeaned on all units; strata lie inside events)
    codes, slot = stratum_codes(G), G["slot"].to_numpy(float)
    evG = G["event_id"].astype(str).to_numpy()
    ctrl_fixed = [c for c in controls if c not in changed]

    def stat(Dm: pd.DataFrame, keep: np.ndarray) -> float:
        cols = [c for c in controls if np.nanstd(Dm[c].to_numpy(float)[keep]) > 0]
        ok = keep & np.isfinite(yG) & np.isfinite(Dm[term].to_numpy(float)) & np.all(np.isfinite(Dm[cols].to_numpy(float)), axis=1)
        if ok.sum() < 10:
            return math.nan
        r = cr1_event_t(yG[ok], Dm[term].to_numpy(float)[ok], Dm[cols].to_numpy(float)[ok] if cols else np.zeros((int(ok.sum()), 0)), evG[ok], sign)
        return float(r["t"]) if r["testable"] else math.nan

    t_obs = stat(D, np.ones(len(G), bool))
    if not math.isfinite(t_obs):
        return {"testable": False, "passes": False, "reason": "observed gate-sample fit not testable"}
    member = (G["event_id"].astype(str) if test == "CH245" else G["event_id"].astype(str) + "|" + G["market_id"].astype(str)).to_numpy()
    ev_order = list(plan)
    ev_code = pd.Series(evG).map({e: i for i, e in enumerate(ev_order)}).to_numpy(int)
    pos = np.empty(len(G), int)
    for e, p_ in plan.items():
        m = evG == e
        pos[m] = np.searchsorted(p_["positions"], G["slot"].to_numpy(int)[m])
    n_e = np.array([plan[e]["n_e"] for e in ev_order])
    s_e = np.array([plan[e]["s_e"] for e in ev_order])
    mcode = pd.factorize(member)[0]
    pmax = int(n_e.max())
    key = mcode.astype(np.int64) * pmax + pos
    srt = np.argsort(key, kind="mergesort")
    skey = key[srt]
    rawG = {c: G[c].to_numpy(float) for c in shift}
    rng = np.random.default_rng(seed)
    ge, om, tvals = 0, [], []
    for _ in range(draws):
        o = rng.integers(s_e, n_e - s_e + 1)
        newpos = (pos + o[ev_code]) % n_e[ev_code]
        want = mcode.astype(np.int64) * pmax + newpos
        j = np.searchsorted(skey, want)
        j = np.minimum(j, len(skey) - 1)
        hit = skey[j] == want
        src = np.where(hit, srt[j], -1)
        keep = src >= 0
        om.append(float((~keep).mean()))
        X = G[[c for c in (*shift, *derived, "unrew", "tl1", "tl2", "tl3", "lowliq") if c in G]].copy()
        for c in shift:
            v = np.full(len(G), np.nan)
            v[keep] = rawG[c][src[keep]]
            X[c] = v
        _recompute(test, X)
        Dm = D.copy()
        for c in changed:
            if c in Dm:
                Dm[c] = strict_expanding_demean(codes, slot, X[c].to_numpy(float))
        tv = stat(Dm, keep)
        tvals.append(tv)
        ge += int(math.isfinite(tv) and tv >= t_obs)
    p = (1 + ge) / (1 + draws)
    return {"testable": True, "t_obs": t_obs, "p_perm": p, "passes": bool(p < 0.05), "draws": draws, "statistic": "event-clustered CR1 t on the gate sample (observed refitted on it)",
            "method": "event-phase state-shift (raw state shifted, one offset per event, event x UTC-day demeaning re-applied every draw)", "events_shifted": len(plan),
            "excluded_events": idx["excluded_events"], "excluded_rows": idx["excluded_rows"], "gate_rows": int(len(G)), "fixed_controls": len(ctrl_fixed),
            "omitted_share_median": float(np.median(om)) if om else 0.0, "omitted_share_max": float(np.max(om)) if om else 0.0,
            "draw_t_nan": int(sum(1 for v in tvals if not math.isfinite(v)))}


# --- census helpers (7) ------------------------------------------------------------------------------------------------------------------


def _scale(days: float) -> float:
    return 21.0 / days if days and math.isfinite(days) and days > 0 else float("nan")


def g_eff(ev) -> float:
    """Kish effective event count ``(sum m_e)^2 / sum m_e^2`` (1.7)."""
    m = pd.Series(np.asarray(ev, dtype=object)).value_counts().to_numpy(float)
    return float(m.sum() ** 2 / (m**2).sum()) if len(m) else float("nan")


def eff12(df: pd.DataFrame) -> np.ndarray:
    """Units that survive the expanding-past event x UTC-day demeaning (not in the first capture of their stratum): the census's effective units
    (LT12 ambiguity A14; LT11 used 'markets with >= 2 units' for market demeaning)."""
    if df.empty:
        return np.zeros(0, bool)
    return np.isfinite(strict_expanding_demean(stratum_codes(df), df["slot"].to_numpy(float), np.ones(len(df))))


def wcorr12(df: pd.DataFrame, a: str, c: str) -> dict:
    """Pooled and within-stratum (expanding-past event x UTC-day demeaned, the estimator's own variation) correlations of two columns (7)."""
    d = df[["event_id", "day", "slot", a, c]].replace([np.inf, -np.inf], np.nan).dropna()
    out = {"pooled": None, "within": None, "n": len(d)}
    if len(d) < 10:
        return out
    if d[a].astype(float).std() > 0 and d[c].astype(float).std() > 0:
        out["pooled"] = float(np.corrcoef(d[a].astype(float), d[c].astype(float))[0, 1])
    X = demeaned_frame(d, [a, c])[[a, c]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(X) >= 10 and X[a].std() > 0 and X[c].std() > 0:
        out["within"] = float(np.corrcoef(X[a], X[c])[0, 1])
    return out


def corr_event_fe(df: pd.DataFrame, a: str, c: str) -> dict:
    """Within-EVENT (event-mean demeaned) and pooled Pearson correlations (7: CH244's ``corr(unrew, log1p liquidity)``; LT12 ambiguity A15)."""
    d = df[["event_id", a, c]].replace([np.inf, -np.inf], np.nan).dropna()
    out = {"pooled": None, "within": None, "n": len(d)}
    if len(d) < 10:
        return out
    if d[a].std() > 0 and d[c].std() > 0:
        out["pooled"] = float(np.corrcoef(d[a], d[c])[0, 1])
    w = d[[a, c]] - d.groupby("event_id")[[a, c]].transform("mean")
    if w[a].std() > 0 and w[c].std() > 0:
        out["within"] = float(np.corrcoef(w[a], w[c])[0, 1])
    return out


def design_ss12(df: pd.DataFrame, term: str, controls: list[str]) -> dict:
    """``VIF_w`` of ``term`` on the expanding-past event x UTC-day DEMEANED regressors (7, ruling B1): ``SS(term) / SS(term | controls)``."""
    cols = [term, *controls]
    d = df[["event_id", "day", "slot", *cols]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < len(cols) + 10:
        return {"n": len(d), "ss_resid": float("nan"), "vif_w": float("nan")}
    X = demeaned_frame(d, cols)[cols].replace([np.inf, -np.inf], np.nan).dropna()
    keep = [c for c in controls if X[c].std() > 0]
    Z = X[keep].to_numpy() if keep else np.zeros((len(X), 0))
    xt = b._partial(Z, X[term].to_numpy())
    x0 = X[term].to_numpy() - X[term].mean()
    ss, ss0 = float(xt @ xt), float(x0 @ x0)
    return {"n": int(len(X)), "ss_resid": ss, "vif_w": float(ss0 / ss) if ss > 0 else float("inf")}


def design_se12(df: pd.DataFrame, terms: list[str], controls: list[str], contrast: dict, rho: float, scale: float) -> float:
    """7's design SE (the vendored ``design_se`` formula, LT8's working covariance: unit variance, within-event equicorrelation ``rho``, independence across
    events, projected by ``scale``) on the regressors AFTER the expanding-past event x UTC-day demeaning the analysis uses. No target is read."""
    cols = [*terms, *controls]
    d = df[["event_id", "day", "slot", *cols]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < len(cols) + 10:
        return float("nan")
    X = demeaned_frame(d, cols)[cols].replace([np.inf, -np.inf], np.nan).dropna()
    keep = [*terms, *[c for c in controls if X[c].std() > 0]]
    if len(X) < len(keep) + 10:
        return float("nan")
    A = np.column_stack([np.ones(len(X)), X[keep].to_numpy()])
    inv = np.linalg.pinv(A.T @ A)
    codes, _ = pd.factorize(d.loc[X.index, "event_id"].astype(str).to_numpy())
    C = np.zeros((int(codes.max()) + 1, A.shape[1]))
    np.add.at(C, codes, A)
    S = C.T @ C
    V = (1.0 - rho) / scale * inv + rho * (inv @ S @ inv)
    cvec = np.zeros(A.shape[1])
    for name, w in contrast.items():
        cvec[1 + keep.index(name)] = w
    var = float(cvec @ V @ cvec)
    return math.sqrt(var) if var > 0 else float("nan")


def r_gate12(U: pd.DataFrame, lead: str, twin: str) -> dict:
    """7: ``r_gate = max(r_w, r_pool)`` of the lead and the twin on census units with both; ``r_w`` within the demeaning stratum (event x UTC day, LT12
    ambiguity A16), ``r_pool`` pooled; NaN unless both are finite."""
    if U.empty or twin not in U or lead not in U:
        return {"r_w": float("nan"), "r_pool": float("nan"), "r_gate": float("nan"), "n": 0}
    r = wcorr12(U, lead, twin)
    rw = float(r["within"]) if r["within"] is not None else float("nan")
    rp = float(r["pooled"]) if r["pooled"] is not None else float("nan")
    return {"r_w": rw, "r_pool": rp, "r_gate": float(max(rw, rp)) if np.isfinite(rw) and np.isfinite(rp) else float("nan"), "n": int(r["n"])}


def f_mde_gate(mde_c: float, r_gate: float, design_c: float) -> dict:
    """7's F-MDE: ``max(design-based MDE of Delta in the arm model, MDE x sqrt(2 / (1 - max(0, r_gate))))`` (cents); NaN anywhere gives inf."""
    if not (np.isfinite(mde_c) and np.isfinite(r_gate) and r_gate < 1.0):
        return {"declared_c": float("inf"), "design_c": design_c, "f_mde_c": float("inf"), "r_gate": r_gate}
    dec = mde_c * math.sqrt(2.0 / (1.0 - max(0.0, r_gate)))
    return {"declared_c": dec, "design_c": design_c, "f_mde_c": float(max(dec, design_c)) if np.isfinite(design_c) else float("inf"), "r_gate": r_gate}


def slope_mde12(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float, gap: float, s_w: float) -> dict:
    """CH245's slope MDE (cents) for a change of ``zs_D`` equal to the census tercile gap (7): ``max(declared, design)``. Declared = ``t_sum x SD x 1.5 x
    sqrt(DE_gate / n_eff) x sqrt(max(1, VIF_w)) x gap / s_w`` (the gap divided by the census SD of the demeaned state, 6 item 6) at the projected effective
    count; design = ``t_sum x 1.5 x SD x se_1 x gap`` (:func:`design_se12`). NaN anywhere gives inf."""
    eff = eff12(pop)
    n_eff = float(eff.sum()) * scale
    dsg = design_ss12(pop, term, controls)
    per_sd = b.mde_slope_declared(n_eff, sd, de_gate, a, dsg["vif_w"])
    ok = all(np.isfinite(v) for v in (per_sd, gap, s_w)) and s_w > 0
    declared = per_sd * gap / s_w * 100.0 if ok else float("inf")
    se = design_se12(pop, [term], controls, {term: 1.0}, float(a["de_rho"]), scale)
    design = a["t_sum"] * a["day_factor"] * sd * se * gap * 100.0 if np.isfinite(se) and np.isfinite(gap) else float("inf")
    return {"design_ss": dsg, "n_eff_projected": n_eff, "declared_c": declared, "design_c": design, "se_1": se, "mde_c": float(max(declared, design)) if np.isfinite(declared) else float("inf")}


def class_mde4(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float) -> dict:
    """CH244's interaction MDE from the four cells (3.4, R1 should-fix 2): declared = ``t_sum x SD x 1.5 x sqrt(max(1, VIF_w)) x sqrt(DE_gate) x sqrt(1/n_us +
    1/n_un + 1/n_rs + 1/n_rn)`` on the projected effective cell counts; design = ``t_sum x 1.5 x SD x se_1``; ``max(declared, design)`` in cents."""
    eff = eff12(pop)
    pe = pop[eff]
    u, s = pe["unrew"].to_numpy(float), pe["shock"].to_numpy(float)
    cells = {"n_us": float(((u == 1) & (s == 1)).sum()) * scale, "n_un": float(((u == 1) & (s == 0)).sum()) * scale,
             "n_rs": float(((u == 0) & (s == 1)).sum()) * scale, "n_rn": float(((u == 0) & (s == 0)).sum()) * scale}
    dsg = design_ss12(pop, term, controls)
    vif = dsg["vif_w"]
    if all(v > 0 for v in cells.values()) and np.isfinite(vif) and np.isfinite(de_gate):
        declared = a["t_sum"] * sd * a["day_factor"] * math.sqrt(max(vif, 1.0)) * math.sqrt(de_gate) * math.sqrt(sum(1.0 / v for v in cells.values())) * 100.0
    else:
        declared = float("inf")
    se = design_se12(pop, [term], controls, {term: 1.0}, float(a["de_rho"]), scale)
    design = a["t_sum"] * a["day_factor"] * sd * se * 100.0 if np.isfinite(se) else float("inf")
    return {"cells_projected": cells, "design_ss": dsg, "declared_c": declared, "design_c": design, "se_1": se, "mde_class_c": float(max(declared, design)) if np.isfinite(declared) else float("inf")}


def f_design_c(F: pd.DataFrame, term: str, twin: str, controls: list[str], scale_f: float, a: dict, sd: float, gap: float | None) -> float:
    """The design-based MDE (cents) of ``Delta = beta(lead) - beta(twin)`` in the arm model on the units with both (``gap`` None: a class contrast)."""
    if F.empty:
        return float("inf")
    se = design_se12(F, [term, twin], controls, {term: 1.0, twin: -1.0}, float(a["de_rho"]), scale_f)
    g_ = 1.0 if gap is None else gap
    return a["t_sum"] * a["day_factor"] * sd * se * g_ * 100.0 if np.isfinite(se) and np.isfinite(g_) else float("inf")


def _gate_block(res: dict, gate: dict, name: str) -> dict:
    res[name] = b._gate(gate)
    res["status"] = CENSUS_PASS if res[name]["pass"] else CENSUS_DROPPED
    return res


def _slot_share(df: pd.DataFrame) -> float:
    s_ = (df["slot"].to_numpy(int) % 12)
    return float(pd.Series(s_).value_counts().iloc[0] / len(s_)) if len(s_) else float("nan")


def span_summary(spans) -> dict:
    """Quantiles q50 / q90 / q99 / max and the shares above 30, 60, 120 and 300 s of a receipt span or gap list (seconds)."""
    v = np.asarray([x for x in spans if np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "q50": float(np.quantile(v, 0.5)), "q90": float(np.quantile(v, 0.9)), "q99": float(np.quantile(v, 0.99)), "max": float(v.max()),
            **{f"share_gt_{t}s": float((v > t).mean()) for t in (30, 60, 120, 300)}}


def block_share12(pop: pd.DataFrame, min_captures: int) -> float:
    """7: the share of the population's units in events with at least ``min_captures`` (16) captures on their index (the gate's shiftable events)."""
    if pop.empty:
        return float("nan")
    ncap = pop.groupby("event_id")["slot"].nunique()
    return float(pop["event_id"].map(ncap).ge(min_captures).mean())


def identification_ch245(T: pd.DataFrame, g: dict) -> dict:
    """6 item 6 (R1 must-fix 4): (i) the share of thin units in event x UTC-day strata in which the RAW dense innovation is non-zero on >= 3 of the stratum's
    thin units; (ii) leverage: the share of the sum of squared demeaned ``zs`` held by the top 1% of thin units by |demeaned ``zs``| (ceil(1%) units, at least
    one) and the largest single event's share."""
    if T.empty:
        return {"nonzero_share": float("nan"), "top_share": float("nan"), "event_share_max": float("nan")}
    st = T["event_id"].astype(str) + "|" + T["day"].astype(str)
    nz = (np.abs(T["o_ds_c"].to_numpy(float)) > EPS).astype(int)
    per = pd.Series(nz, index=T.index).groupby(st.to_numpy()).transform("sum").to_numpy()
    nonzero_share = float((per >= int(g["ident_nonzero_min"])).mean())
    dm = strict_expanding_demean(stratum_codes(T), T["slot"].to_numpy(float), T["zs"].to_numpy(float))
    ok = np.isfinite(dm)
    v2 = dm[ok] ** 2
    tot = float(v2.sum())
    if tot <= 0 or not ok.any():
        return {"nonzero_share": nonzero_share, "top_share": float("nan"), "event_share_max": float("nan"), "n_demeaned": int(ok.sum())}
    ntop = max(1, math.ceil(float(g["leverage_top_frac"]) * len(v2) - 1e-9))
    top_share = float(np.sort(v2)[::-1][:ntop].sum() / tot)
    ev_share = pd.Series(v2).groupby(T["event_id"].astype(str).to_numpy()[ok]).sum() / tot
    return {"nonzero_share": nonzero_share, "top_share": top_share, "top_units": ntop, "event_share_max": float(ev_share.max()), "n_demeaned": int(ok.sum())}


def same_slot_ch245(S: pd.DataFrame, g: dict) -> dict:
    """7: among events with >= 24 complete pair-captures (thin or sym; each member's raw innovation over (k - 1, k], member A = the smaller market id), the
    share with within-event ``|corr(dA, dB)| >= 0.8``. LT12 ambiguity A17: an event whose correlation is undefined (a book that never moves) is counted
    separately and left out of the share."""
    if S.empty:
        return {"events": 0, "share": float("nan"), "undefined": 0}
    W = S.assign(_a=S[["market_id", "o_market_id"]].astype(str).min(axis=1))
    W = W[W["market_id"].astype(str) == W["_a"]]
    W = W.assign(dA=W["own_ds_c"], dB=W["o_ds_c"])
    n = W.groupby("event_id")["slot"].nunique()
    big = n[n >= int(g["same_slot_min_pair_captures"])].index
    vals, undef = [], 0
    for e in big:
        d = W[W["event_id"] == e]
        if d["dA"].std() > 0 and d["dB"].std() > 0:
            vals.append(abs(float(np.corrcoef(d["dA"], d["dB"])[0, 1])))
        else:
            undef += 1
    v = np.asarray(vals)
    return {"events": int(len(big)), "defined": int(len(v)), "undefined": undef, "share": float((v >= float(g["same_slot_abs_corr"]) - 1e-12).mean()) if len(v) else float("nan"),
            "abs_corr_quantiles": b._q(v, (0.1, 0.5, 0.9))}


def _add_twin12(U: pd.DataFrame, test: str, by_slot: dict, cf: dict, spec: dict) -> pd.DataFrame:
    """The census lag-slot loader step (7): for each origin slot group, the twin term from captures k + 2 and k + 3 ONLY (never a mid, a quote or a volume)."""
    out = U.copy()
    col = TWIN[test]
    out[col] = np.nan
    if U.empty:
        return out
    for k, grp in U.groupby("slot"):
        k = int(k)
        if (k + 2) in by_slot and (k + 3) in by_slot:
            da, db = by_slot[k + 2]["dir"], by_slot[k + 3]["dir"]
            if test == "CH245":
                tw = lag_twin_zs(da, db, grp["nrkey"], grp["o_market_id"], grp["line"].to_numpy(object), cf, spec)
            else:
                tw = lag_twin_shock(da, db, grp["nrkey"], grp["market_id"], spec) * grp["unrew"].to_numpy(float)
            out.loc[grp.index, col] = tw
    return out


# --- CH245's census gate block (7 table, row 1) -----------------------------------------------------------------------------------------


CENSUS_UNAVAILABLE = "census_unavailable (coverage)"
CENSUS_DROPPED = "census_dropped"
CENSUS_PASS = "census_pass"


def census_ch245(U: pd.DataFrame, tot: dict, spans: list, gaps: list, spec: dict, covered_days: float, twin_days: float, by_slot: dict) -> dict:
    """CH245's gates (7, row 1), after the coverage check has passed. ``U`` = every CH245 line (thin / dense / sym; arms)."""
    g, a = spec["census_gates"]["CH245"], b.mde_common(spec)
    scale, scale_f = _scale(covered_days), _scale(twin_days)
    res: dict = {"covered_days": covered_days, "twin_days": twin_days, "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    den, num, sok = tot.get("comp_den", 0), tot.get("comp_num", 0), tot.get("span_ok", 0)
    completeness = num / den if den else float("nan")
    span_ok = sok / num if num else float("nan")
    res.update({"pair_completeness": completeness, "receipt_span_retention": span_ok, "receipt_span_distribution": span_summary(spans), "receipt_gap_distribution": span_summary(gaps)})
    T0 = U[(U["line"] == "thin") & (U["arm"] == "primary")] if len(U) else U
    if T0.empty:
        res["gate_CH245"] = {"thin_units": False, "pass": False, "no_units": True}
        res["status"] = CENSUS_DROPPED
        return res
    T, excl, top = b._fam(T0.assign(skey=T0["fam"]), a["family_cap"])
    T = T.copy()
    s_D = float(np.std(T["o_ds_c"].to_numpy(float), ddof=0))
    s_T = float(np.std(T["own_ds_c"].to_numpy(float), ddof=0))
    cfz = {"s_D": s_D, "s_T": s_T}
    T["zs"] = zs_term(T["o_ds_c"].to_numpy(float), T["line"].to_numpy(object), cfz)
    T["zs_pl"] = T["pl_ds_c"].to_numpy(float) / s_D if s_D > 0 else np.nan
    dm = strict_expanding_demean(stratum_codes(T), T["slot"].to_numpy(float), T["zs"].to_numpy(float))
    s_w = float(np.std(dm[np.isfinite(dm)], ddof=0)) if np.isfinite(dm).any() else float("nan")
    t1, t2, gap = b.terciles(T["zs"])
    xT, xD = T["own_ds_c"].to_numpy(float), T["o_ds_c"].to_numpy(float)
    rho = float(np.corrcoef(xT, xD)[0, 1]) if (np.std(xT) > 0 and np.std(xD) > 0) else float("nan")
    gq = span_summary(gaps)
    T, fc_names = fee_dummies(T)
    controls = controls_for("CH245", T)
    de = b._de(T, scale, g["de_floor"], a)
    ev_units = T.groupby("event_id").size()
    ev_n, ev48 = int(T["event_id"].nunique()), int((ev_units >= g["events_min_units"]).sum())
    ge = g_eff(T["event_id"])
    S = U[(U["arm"] == "primary") & U["line"].isin(["thin", "sym"])]
    ss = same_slot_ch245(S, g)
    ident = identification_ch245(T, g)
    dsg = design_ss12(T, "zs", controls)
    corr_x = {x: wcorr12(T, "zs", x) for x in ("log1p_liq", "o_log1p_liq", "log_rv24s", "d")}
    zz = T[np.abs(T["zs"].to_numpy(float)) >= float(g["venue_clock_abs_z"])]
    clock = _slot_share(zz) if len(zz) else float("nan")
    bshare = block_share12(T, int(g["block_min_captures"]))
    pl_cov = float(np.isfinite(T["pl_ds_c"].to_numpy(float)).mean())
    cfx = {"s_D": s_D, "s_T": s_T}
    TW = _add_twin12(T, "CH245", by_slot, cfx, spec)
    F = TW[(TW["f_end_ok"] == 1) & np.isfinite(TW["zs_tw"].to_numpy(float))]
    rg = r_gate12(F, "zs", "zs_tw")
    sm = slope_mde12(T, "zs", controls, scale, a, de["DE_gate"], a[g["sd"]], gap, s_w)
    fm = f_mde_gate(sm["mde_c"], rg["r_gate"], f_design_c(F, "zs", "zs_tw", controls, scale_f, a, a[g["sd"]], gap))
    proj = float(len(T) * scale)
    D = U[(U["line"] == "dense") & (U["arm"] == "primary")]
    gk = np.abs(np.minimum(U["g_ask_k"].to_numpy(float), 0)) if "g_ask_k" in U else np.array([])
    res.update({"thin_units_projected_21d": proj, "thin_units": int(len(T)), "distinct_events_unprojected": ev_n, "events_ge48_units_unprojected": ev48, "g_eff": ge,
                "same_slot": ss, "identification": ident, "vif_w": dsg["vif_w"], "corr_x": corr_x, "venue_clock": clock, "block_share": bshare, "placebo_coverage": pl_cov,
                "r_gate": rg, "slope": sm, "F": fm, "design_effect": de, "exclude_family": excl, "top_family_share": top, "fee_dummies": fc_names,
                "s_D": s_D, "s_T": s_T, "s_w": s_w, "zs": {"terciles": [t1, t2], "gap": gap}, "rho_census": rho,
                "descriptive": {"cells": {k_: int(v_) for k_, v_ in T["cell"].value_counts().items()}, "sym_pairs": int(tot.get("sym_pairs", 0)), "asym_pairs": int(tot.get("asym_pairs", 0)),
                                "pair_wide": int(tot.get("pair_wide", 0)), "augmented_lines": int((U["arm"] == "augmented").sum()), "sports_lines": int((U["arm"] == "sports").sum()),
                                "members_changed": int(tot.get("ev_reason_members_changed", 0)), "receipt_span": int(tot.get("ev_reason_receipt_span", 0)), "placebo_none": int(tot.get("placebo_none", 0)),
                                "event_ids_missing_units": int(T["eids_missing"].sum()), "dense_twin_units": int(len(D)),
                                "dense_ge2_ticks_share": float((D["own_spread_k_ticks"].to_numpy(float) >= 2.0 - 1e-9).mean()) if len(D) else float("nan"),
                                "mirror_gap_ask_k_quantiles": b._q(T["g_ask_k"] * 100.0, (0.05, 0.5, 0.95)), "mirror_gap_bid_k_quantiles": b._q(T["g_bid_k"] * 100.0, (0.05, 0.5, 0.95)),
                                "mirror_gap_within_one_tick_share": float(((np.abs(T["g_ask_k"]) <= T["tick_e"] + EPS) | (np.abs(T["g_bid_k"]) <= T["tick_e"] + EPS)).mean()),
                                "series_family_top": {k_: int(v_) for k_, v_ in T["fam"].value_counts().head(10).items()}, "_n_gk": int(len(gk))},
                "f_arm_units": int(len(F)), "events_proj": b._events8(T, scale, covered_days)})
    gate = {"pair_completeness": bool(np.isfinite(completeness) and completeness >= g["completeness_min"]), "receipt_span": bool(np.isfinite(span_ok) and span_ok >= g["receipt_span_pairs_min"]),
            "thin_units": proj >= g["units_projected_min"], "distinct_events": ev_n >= g["distinct_events_min"], "events_ge48": ev48 >= g["events_ge48_min"],
            "g_eff": bool(np.isfinite(ge) and ge >= a["g_eff_min"]), "same_slot": bool(np.isfinite(ss["share"]) and ss["share"] <= g["same_slot_share_max"]),
            "ident_nonzero": bool(np.isfinite(ident["nonzero_share"]) and ident["nonzero_share"] >= g["ident_share_min"]),
            "ident_top1": bool(np.isfinite(ident["top_share"]) and ident["top_share"] <= g["leverage_top_share_max"]),
            "ident_event": bool(np.isfinite(ident["event_share_max"]) and ident["event_share_max"] <= g["leverage_event_share_max"]),
            "vif_w": bool(np.isfinite(dsg["vif_w"]) and dsg["vif_w"] <= g["vif_w_max"]), **{f"corr_zs_{x}": b.corr_ok(c_, g["corr_max"], both=True) for x, c_ in corr_x.items()},
            "venue_clock": bool(np.isfinite(clock) and clock <= g["venue_clock_max"]), "block_share": bool(np.isfinite(bshare) and bshare >= g["block_share_min"]),
            "placebo_coverage": bool(np.isfinite(pl_cov) and pl_cov >= g["placebo_coverage_min"]), "r_gate": bool(np.isfinite(rg["r_gate"]) and rg["r_gate"] <= g["r_gate_max"]),
            "slope_mde": bool(sm["mde_c"] <= a["mde_max_c"]["CH245"]), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max_c"]["CH245"])}
    res = _gate_block(res, gate, "gate_CH245")
    res["census_fixed"] = {"s_D": s_D, "s_T": s_T, "s_w": s_w, "zs_cuts": [t1, t2], "zs_gap": gap, "rgap_q50_s": gq.get("q50"), "rgap_q90_s": gq.get("q90"), "exclude_family": excl,
                           "rho_census": rho if np.isfinite(rho) else None, "rho_census_nan": bool(not np.isfinite(rho))}
    res["census_gate_values"] = {"mde_c": sm["mde_c"]}  # recorded (the 'underpowered' label's input), never re-used to change a threshold
    return res


# --- CH244's census gate block (7 table, row 2) -----------------------------------------------------------------------------------------


def census_ch244(U: pd.DataFrame, tot: dict, spans: list, mdays: list, ecaps: list, conf: dict, spec: dict, covered_days: float, twin_days: float, by_slot: dict) -> dict:
    """CH244's gates (7, row 2). The FEED COVERAGE is evaluated FIRST (re-check fix 3): under 50% of tested units (an outage included) CH244 returns at once as
    ``census_unavailable (coverage)`` with only the coverage counts; every other gate value is computed only after it. A feed-listed share above 0.20 on
    adequate coverage is a gate (``census_dropped``)."""
    g, a = spec["census_gates"]["CH244"], b.mde_common(spec)
    scale, scale_f = _scale(covered_days), _scale(twin_days)
    P0 = U[U["arm"] == "primary"] if len(U) else U
    head = {"covered_days": covered_days, "twin_days": twin_days}
    if P0.empty:
        return {**head, "gate_CH244": {"tested_units": False, "pass": False, "no_units": True}, "status": CENSUS_DROPPED}
    P, excl, top = b._fam(P0.assign(skey=P0["fam"]), a["family_cap"])
    P = P.copy()
    tested = P[(P["unrew"] == 1) & (P["shock"] == 1)]
    cov_n = int((tested["feed_cov"].to_numpy(float) == 1).sum())
    coverage = cov_n / len(tested) if len(tested) else float("nan")
    feed_cov = {"tested_units": int(len(tested)), "covered": cov_n, "feed_coverage": coverage, "min": g["feed_coverage_min"]}
    if not (np.isfinite(coverage) and coverage >= g["feed_coverage_min"]):  # returns before any other CH244 gate value is computed (re-check fix 3)
        return {**head, "feed_coverage": feed_cov, "status": CENSUS_UNAVAILABLE}
    res: dict = {**head, "feed_coverage": feed_cov, "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    covered = tested[tested["feed_cov"] == 1]
    listed_share = float((covered["feed_listed_pos"].to_numpy(float) == 1).mean()) if len(covered) else float("nan")
    md = pd.DataFrame(mdays, columns=["market_id", "day", "finite"]).drop_duplicates(["market_id", "day"]) if mdays else pd.DataFrame(columns=["market_id", "day", "finite"])
    finite_share = float(md["finite"].astype(bool).mean()) if len(md) else float("nan")
    den, num = tot.get("comp_den_rows", 0), tot.get("comp_num_rows", 0)
    completeness = num / den if den else float("nan")
    pc, so = tot.get("pair_complete_events", 0), tot.get("span_ok_events", 0)
    span_ok = so / pc if pc else float("nan")
    rs = P[(P["unrew"] == 0) & (P["shock"] == 1)]
    proj_t, proj_r = float(len(tested) * scale), float(len(rs) * scale)
    E = pd.DataFrame(ecaps, columns=["nrkey", "slot", "day", "shock_any"]) if ecaps else pd.DataFrame(columns=["nrkey", "slot", "day", "shock_any"])
    shock_share = float(E["shock_any"].mean()) if len(E) else float("nan")
    P["log1p_liq_km1"] = np.log1p(np.clip(P["liq_km1"].to_numpy(float), 0, None))
    corr_ul = corr_event_fe(P, "unrew", "log1p_liq_km1")
    st = P["event_id"].astype(str) + "|" + P["day"].astype(str)
    smax = P.groupby(st.to_numpy())["shock"].transform("max").to_numpy()
    smin = P.groupby(st.to_numpy())["shock"].transform("min").to_numpy()
    both = (smax == 1) & (smin == 0)
    tmask = ((P["unrew"] == 1) & (P["shock"] == 1)).to_numpy()
    wsv = float(both[tmask].mean()) if tmask.any() else float("nan")
    uu = P["unrew"].to_numpy() == 1
    su = P.assign(_s=P["shock"].where(uu)).groupby(st.to_numpy())["_s"]
    both_u = (su.transform("max").to_numpy() == 1) & (su.transform("min").to_numpy() == 0)
    wsv_u = float(both_u[tmask].mean()) if tmask.any() else float("nan")
    sc_size = float(np.std(P["shock_size_raw"].to_numpy(float), ddof=0))
    P["shock_sz"] = P["shock_size_raw"] / sc_size if sc_size > 0 else np.nan
    P, fc_names = fee_dummies(P)
    controls = controls_for("CH244", P)
    de = b._de(P, scale, g["de_floor"], a)
    ev_units = P.groupby("event_id").size()
    ev_n, ev48 = int(P["event_id"].nunique()), int((ev_units >= g["events_min_units"]).sum())
    ge = g_eff(P["event_id"])
    dsg = design_ss12(P, "shock_x_unrew", controls)
    clock = _slot_share(tested) if len(tested) else float("nan")
    bshare = block_share12(P, int(g["block_min_captures"]))
    TW = _add_twin12(P, "CH244", by_slot, {}, spec)
    F = TW[(TW["f_end_ok"] == 1) & np.isfinite(TW["shock_x_unrew_tw"].to_numpy(float))]
    rg = r_gate12(F, "shock_x_unrew", "shock_x_unrew_tw")
    sm = class_mde4(P, "shock_x_unrew", controls, scale, a, de["DE_gate"], a[g["sd"]])
    fm = f_mde_gate(sm["mde_class_c"], rg["r_gate"], f_design_c(F, "shock_x_unrew", "shock_x_unrew_tw", controls, scale_f, a, a[g["sd"]], None))
    lo_b, hi_b = g["shock_share_band"]
    feed_tab = {}
    for stat_, sub in (("unrewarded", P[P["unrew"] == 1]), ("rewarded", P[P["unrew"] == 0])):
        cov_ = sub["feed_cov"].to_numpy(float) == 1
        feed_tab[stat_] = {"listed_positive": int((cov_ & (sub["feed_listed_pos"].to_numpy(float) == 1)).sum()), "listed_zero": int((cov_ & (sub["feed_listed_zero"].to_numpy(float) == 1)).sum()),
                           "not_listed": int((cov_ & (sub["feed_listed_pos"].to_numpy(float) != 1) & (sub["feed_listed_zero"].to_numpy(float) != 1)).sum()), "feed_uncovered": int((~cov_).sum())}
    res.update({"feed_listed_share": listed_share, "status_finite_share": finite_share, "member_days": int(len(md)), "ladder_completeness": completeness,
                "completeness_by_size": {sc_: (tot.get(f"comp_num_rows_{sc_}", 0) / tot[f"comp_den_rows_{sc_}"] if tot.get(f"comp_den_rows_{sc_}") else float("nan")) for sc_ in ("3-5", "6-10")},
                "receipt_span_retention": span_ok, "receipt_span_distribution": span_summary(spans), "tested_units_projected_21d": proj_t, "rewarded_shock_units_projected_21d": proj_r,
                "shock_share_event_captures": shock_share, "mixed_event_captures": int(len(E)),
                "shock_share_units": {"unrewarded": float(P.loc[P["unrew"] == 1, "shock"].mean()) if (P["unrew"] == 1).any() else float("nan"),
                                      "rewarded": float(P.loc[P["unrew"] == 0, "shock"].mean()) if (P["unrew"] == 0).any() else float("nan")},
                "corr_unrew_liq": corr_ul, "within_stratum_share": wsv, "within_stratum_share_unrewarded_only": wsv_u, "vif_w": dsg["vif_w"], "distinct_events_unprojected": ev_n,
                "events_ge48_units_unprojected": ev48, "g_eff": ge, "venue_clock": clock, "block_share": bshare, "r_gate": rg, "class": sm, "F": fm, "design_effect": de,
                "exclude_family": excl, "top_family_share": top, "fee_dummies": fc_names, "f_arm_units": int(len(F)), "events_proj": b._events8(P, scale, covered_days),
                "carry_against_simple": {f"{k_[0]}:{k_[1]}": int(v_) for k_, v_ in conf.items()}, "mixed_counts": {"carry": int(tot.get("mixed_carry_event_captures", 0)), "simple": int(tot.get("mixed_simple_event_captures", 0))},
                "feed_table": feed_tab, "feed_age_h_quantiles": b._q(P.loc[P["feed_cov"] == 1, "feed_age_h"], (0.1, 0.5, 0.9)),
                "switch": {k_: int(tot.get(k_, 0)) for k_ in ("status_switched_unrew0", "status_switched_unrew1", "status_kept_unrew0", "status_kept_unrew1", "status_nan_unit", "status_nan_rows")},
                "arm_units": {k_: int(v_) for k_, v_ in U["arm"].value_counts().items()}})
    gate = {"status_finite": bool(np.isfinite(finite_share) and finite_share >= g["status_finite_min"]), "ladder_completeness": bool(np.isfinite(completeness) and completeness >= g["completeness_min"]),
            "receipt_span": bool(np.isfinite(span_ok) and span_ok >= g["receipt_span_pairs_min"]), "tested_units": proj_t >= g["tested_units_projected_min"],
            "rewarded_shock_units": proj_r >= g["rewarded_shock_projected_min"], "feed_listed_share": bool(np.isfinite(listed_share) and listed_share <= g["feed_listed_share_max"]),
            "shock_share": bool(np.isfinite(shock_share) and lo_b <= shock_share <= hi_b), "corr_unrew_liq": b.corr_ok(corr_ul, g["corr_max"], both=True),
            "within_stratum": bool(np.isfinite(wsv) and wsv >= g["within_stratum_share_min"]), "vif_w": bool(np.isfinite(dsg["vif_w"]) and dsg["vif_w"] <= g["vif_w_max"]),
            "distinct_events": ev_n >= g["distinct_events_min"], "events_ge48": ev48 >= g["events_ge48_min"], "g_eff": bool(np.isfinite(ge) and ge >= a["g_eff_min"]),
            "venue_clock": bool(np.isfinite(clock) and clock <= g["venue_clock_max"]), "block_share": bool(np.isfinite(bshare) and bshare >= g["block_share_min"]),
            "r_gate": bool(np.isfinite(rg["r_gate"]) and rg["r_gate"] <= g["r_gate_max"]), "class_mde": bool(sm["mde_class_c"] <= a["mde_max_c"]["CH244"]),
            "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max_c"]["CH244"])}
    res = _gate_block(res, gate, "gate_CH244")
    res["census_fixed"] = {"world9_corr": corr_ul.get("within"), "shock_size_scale": sc_size, "exclude_family": excl}
    res["census_gate_values"] = {"mde_c": sm["mde_class_c"]}
    return res


# --- the LT12 seal (a fresh seal of the span's captures and feed captures; 7, 8.4 step 4) ----------------------------------------------------


def _span_slots(spec: dict) -> list[int]:
    ci = spec["census_inputs"]
    k0 = b.slot_of(epoch(ci["span"]["first_slot_utc"]), spec)
    k1 = b.slot_of(epoch(ci["span"]["last_slot_utc"]), spec)
    return list(range(k0, k1 + 1))


def seal_windows(spec: dict) -> dict:
    """The sealed slot range (7): captures from 12 slots before the span (look-back) to 3 slots after it (the twins' slots of the last origins); the feed
    captures whose start lies in ``feed_window``."""
    ci = spec["census_inputs"]
    sl = _span_slots(spec)
    return {"captures": (sl[0] - ci["lookback_capture_slots"], sl[-1] + ci["lag_slots_after"]), "feed": tuple(ci["feed_window"])}


def seal_inputs(*, snapshot_root, feed_root=None, work: Path, spec: dict | None = None, unavailable=None, design_path: Path | None = None) -> dict:
    """The LT12 seal (7): every complete capture (rows, manifest, sidecar) of the sealed window found in the roots (host copies first, then restore trees),
    and every feed capture whose start lies in the feed window, each hashed. A directory found in two roots with different bytes refuses (never substituted).
    Records the seal's own slot assignment, the frozen design-text sha256, the spec's census blocks and the header pre-check result (``k_block``, which must
    already be filled). Missing slots are counted, never filled."""
    spec = spec or load_spec(sha=None)
    if (derr := design_text_error(design_path)):
        return derr
    if (rerr := reward_rule_error(spec)):
        return rerr
    if (kerr := k_block_error(spec)):
        return kerr
    win = seal_windows(spec)
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    by_slot, _ = b._scan(Path(work), snapshot_root, [], spec)
    files, slots, conflicts, feeds = {}, {}, [], {}

    def put(rel: str, p: Path, roots, d: str, extra: dict, kind: str) -> None:
        h = sha256_file(p)
        for r in b._roots(roots):
            q = Path(r) / d / p.name
            if q.exists() and q.parent != p.parent and sha256_file(q) != h:
                conflicts.append({"file": rel, "root_a": str(p), "root_b": str(q)})
        files[rel] = {"sha256": h, "root": str(p.parent.parent), "kind": kind, **extra}

    caps_k = sorted(k for k in by_slot if win["captures"][0] <= k <= win["captures"][1])
    for k in caps_k:
        c = by_slot[k]
        if c["start"] >= bound:
            continue
        for rel, p in b.capture_files(c["dir"]):
            put(rel, p, snapshot_root, c["id"], {"capture": c["id"]}, "capture")
        slots[c["id"]] = iso(b.slot_time(k, spec))
    f0, f1 = epoch(win["feed"][0]), epoch(win["feed"][1])
    if feed_root is not None:
        fe = b.scan_feed(feed_root)
        for d, v in sorted(fe.items()):
            if not (f0 <= v["start"] < f1) or v["start"] >= bound:
                continue
            feeds[d] = {"started_utc": iso(v["start"]), "finished_utc": iso(v["finish"]), "state": v["state"], "usable": v["usable"]}
            for fn in ("rows.jsonl.gz", "manifest.json"):
                p = Path(v["dir"]) / fn
                if p.exists():
                    put(f"data-dumps/research_lab/reward_params/{d}/{fn}", p, feed_root, d, {"feed": d}, "feed")
    if conflicts:
        return {"error": "a sealed directory exists in two roots with different bytes: LT12 seal refused", "conflicts": conflicts[:50], "n_conflicts": len(conflicts)}
    cap_need = range(win["captures"][0], win["captures"][1] + 1)
    miss_c = [iso(b.slot_time(k, spec)) for k in cap_need if k not in caps_k]
    unavail = sorted(b.load_unavailable(unavailable)) if unavailable else []
    return {"purpose": "LT12 census inputs (LIVE_TESTS_12.md section 7): every capture and feed capture the census may open, each hashed; counts-only use",
            "written_utc": iso(b.now_ts()), "spec_sha256": sha256_file(SPEC_PATH), "design_text_sha256": design_text_sha(design_path), "spec_blocks_sha256": spec_blocks_sha(spec),
            "k_block": spec["k_block"], "span": spec["census_inputs"]["span"], "refuse_at_or_after_utc": spec["census_inputs"]["refuse_at_or_after_utc"],
            "windows": {k_: [v_[0], v_[1]] for k_, v_ in win.items()}, "slots": dict(sorted(slots.items())), "feeds": feeds, "needs": {"captures": len(caps_k), "feeds": len(feeds)},
            "span_slots": len(_span_slots(spec)), "missing": {"captures": miss_c}, "n_missing": {"captures": len(miss_c)}, "unavailable_declared": unavail,
            "n_files": len(files), "files": dict(sorted(files.items()))}


def bound_violations(seal: dict, spec: dict) -> list[dict]:
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = [{"what": d, "value": s_, "error": "at or after the sealed bound"} for d, s_ in (seal.get("slots") or {}).items() if epoch(s_) >= bound]
    bad += [{"what": d, "value": v["started_utc"], "error": "feed at or after the sealed bound"} for d, v in (seal.get("feeds") or {}).items() if epoch(v["started_utc"]) >= bound]
    if seal.get("written_utc") is None:
        bad.append({"what": "written_utc", "error": "seal not stamped"})
    return bad


def sealed_slot_map(seal: dict, spec: dict) -> dict[int, set[str]]:
    """capture slot -> sealed directory names, from the seal's OWN slot assignment (never from a local scan)."""
    out: dict[int, set[str]] = {}
    for d in b.sealed_dirs(seal, "snapshots"):
        k = b.slot_of(epoch(seal["slots"][d]), spec) if d in seal.get("slots", {}) else None
        if k is not None:
            out.setdefault(k, set()).add(d)
    return out


def seal_coverage(seal: dict, spec: dict) -> dict:
    """7's minimum covered days, computed from the seal manifest BEFORE any row is read and identical for both tests: a covered origin is a span slot whose
    capture and the capture of the slot before it are both sealed with rows, sidecar and manifest; a covered twin origin also has the captures of slots
    k + 2 and k + 3. ``ok`` needs >= 7.0 covered days and >= 5.0 covered twin days (LT12 ambiguity A18 = LT11 A17: both are coverage conditions)."""
    full = set()
    for d, rels in b.sealed_dirs(seal, "snapshots").items():
        names = {r.rsplit("/", 1)[1] for r in rels}
        if {"rows.csv.gz", "rows_ext.csv.gz", "manifest.json"} <= names and d in seal.get("slots", {}):
            k = b.slot_of(epoch(seal["slots"][d]), spec)
            if k is not None:
                full.add(k)
    span = _span_slots(spec)
    org = [k for k in span if k in full and (k - 1) in full]
    twin = [k for k in org if (k + 2) in full and (k + 3) in full]
    mins = spec["census_inputs"]["min_covered_days"]
    cd, td = len(org) / 12.0, len(twin) / 12.0
    return {"covered_origins": len(org), "covered_days": cd, "twin_origins": len(twin), "twin_days": td, "min_covered_days": mins["CC12"], "min_twin_days": mins["CC12_twins"],
            "ok": bool(cd >= mins["CC12"] and td >= mins["CC12_twins"]), "origins": org}


def _sealed_feed_files_ok(seal: dict, feed_root) -> list[dict]:
    bad = []
    for rel, v in (seal.get("files") or {}).items():
        if v.get("kind") != "feed":
            continue
        d, fn = rel.split("/")[3], rel.split("/")[4]
        found = None
        for r in b._roots(feed_root):
            p = Path(r) / d / fn
            if p.exists():
                found = p
                break
        if found is None:
            bad.append({"file": rel, "error": "sealed feed file absent from every root"})
        elif sha256_file(found) != v["sha256"]:
            bad.append({"file": rel, "error": "sealed feed file hash differs"})
    return bad


def _load_for_census(seal: Path, snapshot_root, feed_root, work: Path, spec: dict, verify: bool = True, design_path: Path | None = None) -> dict:
    """The refusals every census runs first: the frozen design text, the seal's design hash, the sealed bound, the seal-time spec blocks, the reward rule, the
    header pre-check result, an empty work dir; then every sealed capture (and feed capture) must be present locally with every sealed file hash-equal, and
    the scan must pick the sealed directory for each sealed slot (else refused, L3)."""
    seal_d = json.loads(Path(seal).read_text())
    if (derr := design_text_error(design_path)):
        return derr
    if seal_d.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        return {"error": "the seal was written against a different LIVE_TESTS_12.md: census refused", "seal_design_text_sha256": seal_d.get("design_text_sha256")}
    if (viol := bound_violations(seal_d, spec)):
        return {"error": "sealed bound violated: census refused", "bad": viol[:20]}
    if seal_d.get("spec_blocks_sha256") != spec_blocks_sha(spec):
        return {"error": "the spec's census blocks differ from those at seal time: census refused", "seal_blocks_sha256": seal_d.get("spec_blocks_sha256"), "spec_blocks_sha256": spec_blocks_sha(spec)}
    if (rerr := reward_rule_error(spec)):
        return rerr
    if (kerr := k_block_error(spec)):
        return kerr
    w = Path(work)
    if w.exists() and any(w.iterdir()):
        return {"error": f"work directory {w} is not empty: a stale series file would be reused (census refused)"}
    by_slot, _ = b._scan(w, snapshot_root, [], spec)
    sc = sealed_slot_map(seal_d, spec)
    bad = []
    for k, names in sorted(sc.items()):
        cc = by_slot.get(k)
        if cc is None:
            bad.append({"slot": k, "sealed": sorted(names), "error": "sealed capture is absent from every root"})
        elif cc["id"] not in names:
            bad.append({"slot": k, "sealed": sorted(names), "scanned": cc["id"], "error": "the scanned capture differs from the sealed one"})
    by_slot = {k: v for k, v in by_slot.items() if k in sc and v["id"] in sc[k]}
    files_checked = 0
    if verify and sc:
        comp = b.seal_completeness(seal_d, by_slot, {}, set(sc), set(), spec, None)
        bad += comp["bad"]
        files_checked = comp["files_checked"]
    if verify:
        bad += _sealed_feed_files_ok(seal_d, feed_root)
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    return {"seal": seal_d, "by_slot": by_slot, "files_checked": files_checked}


def census_units(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, feed_root=FEED_ROOT, work: Path, spec: dict | None = None, verify: bool = True, design_path: Path | None = None) -> dict:
    """The data pass of CC12 (7): the refusals, the coverage check (FIRST: if it fails nothing else runs and no row is opened) and ONE streaming pass over the
    covered origins building both tests' lines. Counts only: no target and no outcome is read."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    loaded = _load_for_census(seal, snapshot_root, feed_root, work, spec, verify=verify, design_path=design_path)
    if "error" in loaded:
        return loaded
    cov = seal_coverage(loaded["seal"], spec)
    head = {"span": spec["census_inputs"]["span"], "inputs_verified": bool(verify), "files_checked": loaded["files_checked"], "design_text_sha256": DESIGN_TEXT_SHA256,
            "reward_null_rule": spec.get("reward_null_rule"), "k_block": spec.get("k_block"), "coverage": {k_: v_ for k_, v_ in cov.items() if k_ != "origins"}}
    if not cov["ok"]:  # returns BEFORE any gate block is built and before a row is opened
        return {"unavailable": {**head, "statuses": {t: CENSUS_UNAVAILABLE for t in TESTS}, **{t: {"status": CENSUS_UNAVAILABLE, "covered_days": cov["covered_days"], "twin_days": cov["twin_days"]} for t in TESTS}}}
    by_slot = loaded["by_slot"]
    ORG = sorted(cov["origins"])
    org_set = set(ORG)
    store = SlotStore(work, by_slot, spec, cache_slots=30)
    sealed_feeds = sorted((loaded["seal"].get("feeds") or {}).keys())
    feed = FeedIndex(feed_root, spec, only=sealed_feeds) if feed_root is not None else None
    loop = sorted(s_ for s_ in by_slot if ORG[0] - 13 <= s_ <= ORG[-1])
    parts = {t: [] for t in TESTS}
    tots: dict = {t: {} for t in TESTS}
    lists = {"spans245": [], "gaps245": [], "spans244": [], "mdays": [], "ecaps": []}
    conf: Counter = Counter()
    fee_counts: dict = {}
    for k in loop:
        cap = by_slot[k]
        write_series12(work, cap, spec)
        ser = store.ser(k)
        if ser is not None:
            b._fee_counts(ser, fee_counts)
        if k not in org_set:
            continue
        u, cnt = ch245_units(store, k, spec, stamp=False)
        lists["spans245"].extend(cnt.pop("_spans", []))
        lists["gaps245"].extend(cnt.pop("_gaps", []))
        b._merge_counts(tots["CH245"], cnt)
        if len(u):
            parts["CH245"].append(u)
        u, cnt = ch244_units(store, k, spec, stamp=False, feed=feed)
        lists["spans244"].extend(cnt.pop("_spans", []))
        lists["mdays"].extend(cnt.pop("_mdays", []))
        lists["ecaps"].extend(cnt.pop("_ecaps", []))
        for kk, vv in (cnt.pop("_conf", {}) or {}).items():
            conf[kk] += vv
        b._merge_counts(tots["CH244"], cnt)
        if len(u):
            parts["CH244"].append(u)
    return {"head": head, "cov": cov, "by_slot": by_slot, "ORG": ORG, "parts": parts, "tots": tots, "lists": lists, "conf": dict(conf), "fee_counts": fee_counts}


def census_gates(cu: dict, spec: dict) -> dict:
    """The two gate blocks of CC12 on the output of :func:`census_units` (each block evaluated independently; a failing block never changes the other)."""
    head, cov, by_slot, ORG = cu["head"], cu["cov"], cu["by_slot"], cu["ORG"]
    fs = b.crypto_failsafe(cu["fee_counts"])
    if not fs["classifier_shown_to_work"]:
        return {**head, "error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    U = {t: (pd.concat(p_, ignore_index=True) if p_ else pd.DataFrame()) for t, p_ in cu["parts"].items()}
    cd, td = cov["covered_days"], cov["twin_days"]
    L = cu["lists"]
    out = {**head, "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": True, "covered_origins": len(ORG),
           "expected_origins": spec["census_inputs"]["expected_origins"].get("CC12"),
           "CH245": census_ch245(U["CH245"], cu["tots"]["CH245"], L["spans245"], L["gaps245"], spec, cd, td, by_slot),
           "CH244": census_ch244(U["CH244"], cu["tots"]["CH244"], L["spans244"], L["mdays"], L["ecaps"], cu["conf"], spec, cd, td, by_slot)}
    prim = {"CH245": U["CH245"][(U["CH245"]["line"] == "thin") & (U["CH245"]["arm"] == "primary")] if len(U["CH245"]) else U["CH245"],
            "CH244": U["CH244"][U["CH244"]["arm"] == "primary"] if len(U["CH244"]) else U["CH244"]}
    ev = {t: set(prim[t]["event_id"].astype(str)) if len(prim[t]) else set() for t in TESTS}
    caps = {t: set(prim[t]["slot"].astype(int)) if len(prim[t]) else set() for t in TESTS}
    out["overlap"] = {"shared_events": len(ev["CH245"] & ev["CH244"]), "shared_captures": len(caps["CH245"] & caps["CH244"])}
    out["descriptive_both"] = {t: {"sports_lines": int((U[t]["arm"] == "sports").sum()) if len(U[t]) else 0} for t in TESTS}
    out["statuses"] = {t: out[t]["status"] for t in TESTS}
    return out


def census_captures(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, feed_root=FEED_ROOT, work: Path, spec: dict | None = None, verify: bool = True, design_path: Path | None = None) -> dict:
    """CC12 (7): the two gate blocks on the sealed captures (counts only). The coverage check is evaluated FIRST, from the seal manifest: if it fails, NO row
    is opened, no gate is computed or printed and both tests are ``census_unavailable (coverage)``, a status distinct from ``census_dropped``. CH244's feed
    coverage is a second coverage check, evaluated first in its block."""
    spec = spec or load_spec(sha=None)
    cu = census_units(seal=seal, snapshot_root=snapshot_root, feed_root=feed_root, work=work, spec=spec, verify=verify, design_path=design_path)
    if "error" in cu:
        return cu
    if "unavailable" in cu:
        return cu["unavailable"]
    return bd._clean(census_gates(cu, spec))


def header_precheck(*, capture_dir: Path | None = None, feed_dir: Path | None = None, spec: dict | None = None) -> dict:
    """7: the header pre-check (headers only, NO rows): which of the 1.2 row and sidecar fields one capture carries (``series_slugs``, ``event_ids``,
    ``liquidity``, ``clob_rewards`` included), whether ``chg_1d`` / ``chg_1w`` exist (they fix K's columns, 1.7), and the feed's listing fields (the first
    line's keys only). Its result is committed before the seal. A missing field makes every gate that needs it NaN."""
    spec = spec or load_spec(sha=None)
    hp = spec["census_inputs"]["header_precheck"]
    out: dict = {"capture_dir": str(capture_dir) if capture_dir else None, "feed_dir": str(feed_dir) if feed_dir else None}
    if capture_dir is not None:
        d = Path(capture_dir)
        rows = list(pd.read_csv(d / "rows.csv.gz", nrows=0).columns) if (d / "rows.csv.gz").exists() else None
        ext = list(pd.read_csv(d / "rows_ext.csv.gz", nrows=0).columns) if (d / "rows_ext.csv.gz").exists() else None
        out["rows_header"], out["sidecar_header"] = rows, ext
        out["rows_missing"] = [c for c in hp["rows"] if rows is not None and c not in rows]
        out["sidecar_missing"] = [c for c in hp["sidecar"] if ext is not None and c not in ext]
        out["chg_1d"] = bool(rows is not None and "chg_1d" in rows)
        out["chg_1w"] = bool(rows is not None and "chg_1w" in rows)
        out["manifest_has_state"] = bool((d / "manifest.json").exists() and "state" in json.loads((d / "manifest.json").read_text()))
    if feed_dir is not None:
        import gzip as _gz

        p = Path(feed_dir) / "rows.jsonl.gz"
        keys = None
        if p.exists():
            with _gz.open(p, "rt") as fh:
                line = fh.readline().strip()
                keys = sorted(json.loads(line).keys()) if line else []
        out["feed_keys"] = keys
        out["feed_missing"] = [c for c in hp["feed"] if keys is not None and c not in keys]
    return out
