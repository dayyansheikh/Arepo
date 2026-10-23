# ruff: noqa: E501
"""LIVE prospective tests LT11 (docs/research_lab/LIVE_TESTS_11.md, design text frozen at sha256 991100db...): the price of the quote, CH234 (the dollar
weight of a move), CH233 (the arb's footprint) and CH232 (the cheap side's cliff). DRAFT: nothing is registered; E-numbers are assigned at registration.
Research tooling only; never trades; makes no network request.

This module holds: the pins and the spec (1.1, 8.4), the capture loaders and the write-once per-capture series (1.2, 1.5), the three unit builders
(sections 2-4), the lag-slot loaders (7), the window reader (:func:`run_once`: origin statuses, frozen unit lines, targets, twins; write-once), the fresh
seal and the counts-only census CC11 with every gate of section 7, ``ops-stats`` and the header pre-check. The simulated worlds and the size check are in
``live_tests11_worlds.py``, the single analysis in ``live_tests11_analysis.py``.

LT3-LT9 code is used only through the vendored copies in ``live_tests11_base`` / ``live_tests11_analysis_base`` (8.1); this module never imports
``live_tests3`` .. ``live_tests10``, and no E026 frozen file is imported, copied or edited.

Causality (1.3): a unit at capture k reads captures <= k (the 12-slot look-back and the earlier slots of the UTC day); targets start at capture k + 1;
twins (k + 2, k + 3) and CH232's sweep readings are readings written after the fact and never read by a unit builder (a unit test checks that a builder
never touches a slot after k).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from . import forecast, panel
from . import live_tests11_base as b

VERSION = "live-tests11-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = ROOT / "data-dumps" / "research_lab" / "book_sweeps"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests11"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests11_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration (8.4 step 9)
REGISTERED_UTC = "2026-11-18T00:00:00Z"  # proposed (design 1.1, fast lane)
END_UTC = "2026-12-09T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-12-10T12:00:00Z"
TEMPFAIL = 75
DAY_S = 86400.0
GRID_S = b.GRID_S
DESIGN_TEXT_SHA256 = "991100db5d6c75e3f76e3d0d10cc5f957dd755108e09ec05edd8dad0f91b3583"  # LIVE_TESTS_11.md design-text freeze (3627d7fd, merged 1f353ca6)
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_11.md"
REWARD_NULL_RULE = "listed_carry24h_v2"
TESTS = ("CH234", "CH233", "CH232")
KINDS = {"CH234": "dollarw", "CH233": "nrslack", "CH232": "bandside"}
TERM = {"CH234": "xw", "CH233": "zcl", "CH232": "xo"}
TWIN = {"CH234": "xw_tw", "CH233": "zcl_tw", "CH232": "xo_tw"}
F_ROLES = {"CH234": "binding", "CH233": "binding", "CH232": "binding"}  # 1.9: F binds for all three, fixed by design (R1 ruling A4)
RECEIPT_SPAN_S = 120.0  # 1.3 (R1 must-fix 1)
EPS = 1e-9
CODE_FILES = ("live_tests11.py", "live_tests11_worlds.py", "live_tests11_analysis.py", "live_tests11_base.py", "live_tests11_analysis_base.py", "bounce_decomp.py",
              "panel.py", "cb17_census.py", "cb13_label.py", "economics.py", "forecast.py", "maker_rewards.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)
SNAP_COLS11 = [*b.SNAP_COLS, "liquidity", "neg_risk_market_id", "neg_risk_other", "event_neg_risk_augmented"]
EXT_COLS11 = [*b.EXT_COLS, "rewards_min_size", "rewards_max_spread", "clob_rewards", "received_utc", "volume_num"]
# columns ops_stats may read (never a price, a spread, a volume, a depth or a target; enforced by a unit test)
OPS_COLS = frozenset({"role", "kind", "sports", "crypto", "status", "late", "vclass", "panel", "size_class", "arm", "noprev", "nosweep", "slot", "day"})
MARKERS = (".late.csv.gz", ".noprev.csv.gz", ".nosweep.csv.gz")
ROLE_CONF, ROLE_UNREG = "prospective_confirmation", "prospective_unregistered"
MISSING_AFTER_S = 3 * 3600.0  # a target capture absent 3 h after its slot is "capture_missing" (LT3-LT9)
DISK_CAP_BYTES = int(3.0e9)  # 1.12: the reader refuses above 3.0 GB in live_tests11/
BINS = ((0.04, 0.15), (0.15, 0.50), (0.50, 0.85), (0.85, 0.96 + 1e-9))  # 2.4: four bins of p_{k-1}
BIN_CENTRES = tuple((lo + min(hi, 0.96)) / 2.0 for lo, hi in BINS)
WINSOR_ABSD = 0.20  # 2.4
BAND = (0.10, 0.90)  # 4.2 band B
ZONE_HALF = 0.04  # 4.2 outward approach zone
REWARD_SINGLE_SIDE_C = 3.0  # 1.4.2: the reduced weight c of a one-sided quote inside [0.10, 0.90]
M1_SIDE_READING = "cheap"  # 1.4.2 + the ledger record at the design-text freeze (b057e076): documented reading, M1 cheap side

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


def reader_sha() -> str:
    """16 hex digits identifying the reader code: the unit-building module together with the vendored base."""
    h = code_hashes()
    return hashlib.sha256((str(h["live_tests11.py"]) + str(h["live_tests11_base.py"])).encode("utf-8")).hexdigest()[:16]


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
            raise RuntimeError(f"live_tests11 spec sha256 mismatch: {got} != pinned {sha}")
        if (bad := _nan_free(spec)):
            raise RuntimeError(f"live_tests11 pinned spec holds NaN / inf at {bad[:5]}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests11 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    if spec.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        raise RuntimeError("live_tests11 spec design_text_sha256 differs from the module constant")
    return spec


def reward_rule_error(spec: dict) -> dict | None:
    """1.4.1: every census refuses unless the spec declares ``reward_null_rule = listed_carry24h_v2`` with ``reward_carry_slots = 12``."""
    if spec.get("reward_null_rule") != REWARD_NULL_RULE or spec.get("reward_carry_slots") != b.REWARD_CARRY_SLOTS:
        return {"error": "the spec does not declare the reward-null rule listed_carry24h_v2 with reward_carry_slots 12: refused",
                "reward_null_rule": spec.get("reward_null_rule"), "reward_carry_slots": spec.get("reward_carry_slots")}
    return None


def k_block_error(spec: dict) -> dict | None:
    """7: the header pre-check result (whether ``chg_1d`` / ``chg_1w`` exist) is committed BEFORE the seal and fixes K's columns: the seal and every census
    refuse a spec in which either is still null."""
    kb = spec.get("k_block") or {}
    if not isinstance(kb.get("chg_1d"), bool) or not isinstance(kb.get("chg_1w"), bool):
        return {"error": "the spec's k_block (chg_1d, chg_1w) is not filled from the committed header pre-check: refused (7, R1 should-fix 6)", "k_block": kb}
    return None


SPEC_HASHED_BLOCKS = ("census_gates", "census_inputs", "tests", "move", "eligibility", "grid", "crypto_classifier", "sports_rule", "series_key_rule", "crypto_rule",
                      "reward_null_rule", "reward_carry_slots", "member_cap", "f_roles", "rv", "k_block", "receipt_span_s")


def spec_blocks_sha(spec: dict) -> str:
    """sha256 of the canonical JSON of every spec block census code reads. The seal stores it; every census refuses a spec whose blocks differ from the
    seal-time ones. ``census_fixed`` (the values the census fills) is deliberately outside the hash."""
    blob = json.dumps({k_: spec.get(k_) for k_ in SPEC_HASHED_BLOCKS}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def design_text_sha(path: Path | None = None) -> str:
    return sha256_file(path or DESIGN_PATH)


def design_text_error(path: Path | None = None) -> dict | None:
    got = design_text_sha(path)
    return None if got == DESIGN_TEXT_SHA256 else {"error": "LIVE_TESTS_11.md differs from the text-frozen file: refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}


def f_role(spec: dict, test: str) -> str:
    """1.9 (R1 ruling A4): F binds for all three, fixed now by design, never by a census count. A spec that says otherwise is refused."""
    got = (spec.get("f_roles") or {}).get(test)
    if got != F_ROLES[test] or "f_binding" in spec:
        raise RuntimeError(f"F role of {test} must be {F_ROLES[test]} (design 1.9); the spec says {got!r}")
    return got


def registration_error(spec: dict) -> dict | None:
    """The registration refusals of a pinned spec (8.4 steps 5-9): a null / empty / unknown ``k_tests`` and unfilled census values refuse. DRAFT: None."""
    if not spec.get("_pinned"):
        return None
    k = spec.get("k_tests")
    if not k:
        return {"error": "pinned spec with null or empty k_tests"}
    if [t for t in k if t not in TESTS]:
        return {"error": f"pinned spec with unknown k_tests {[t for t in k if t not in TESTS]}"}
    cf = spec.get("census_fixed") or {}
    for t in k:
        if any(v is None for v in (cf.get(t) or {}).values()) or not cf.get(t):
            return {"error": f"pinned spec with unfilled census_fixed values of {t}"}
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


# --- loaders and the per-capture series (1.2, 1.5) --------------------------------------------------------------------------------------


def load_rows11(cap_dir: Path) -> pd.DataFrame:
    """Origin-side capture columns (LT3's plus Gamma ``liquidity`` and the neg-risk fields): one row per market_id and per condition_id (first in page
    order), the member count ``n_members`` (distinct markets of the Gamma event among the capture's binary, open and active rows; a market without
    ``event_id`` is its own event, 1.4) and the event key ``ekey``."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(SNAP_COLS11),
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category", "end_date": "category", "closed": str,
                              "active": str, "neg_risk": str, "neg_risk_market_id": str, "neg_risk_other": str, "event_neg_risk_augmented": str})
    for c in SNAP_COLS11:
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
    return rows


def load_ext11(cap_dir: Path) -> pd.DataFrame | None:
    """The sidecar by market_id, or None when the capture has no ``rows_ext.csv.gz`` (sidecar missing: sports / crypto / tick unknown, 1.2)."""
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS11), dtype=str)
    has_clob = "clob_rewards" in ext.columns  # a sidecar WITHOUT the column says nothing about rewards: NaN, not unrewarded (LT8 check fix 7)
    has_vnum = "volume_num" in ext.columns
    for c in EXT_COLS11:
        if c not in ext:
            ext[c] = None
    out = ext.drop_duplicates("market_id").set_index("market_id")
    out.attrs["has_clob_rewards"], out.attrs["has_volume_num"] = has_clob, has_vnum
    return out


def capture_last_receipt(cap_dir: Path) -> float:
    """A capture's last row receipt (1.3): the largest ``received_utc`` over the capture's complete rows AND its sidecar rows. Reads the timestamp columns
    only; NaN when none is readable."""
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


def series11_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, day: str, cap_start: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(series, status) of a capture. The vendored LT3 series (two-sided quotes of open active binary markets, ``ask <= 1``) plus: Gamma ``liq``,
    ``n_members``, ``condition_id``, ``event_id`` = the event key (the market itself when it has no event), the reward fields of LT8's null taxonomy
    (``rew_rate`` / ``rew_state`` / ``rew_status`` in the LT7 vocabulary), ``rew_min`` / ``rew_maxspread``, ``fee_cat``, the pinned crypto class
    ``crypto7``, ``volume_num`` as ``vnum`` (NaN when empty / non-numeric) and ``side`` (1 when the sidecar has a row for the market), and the neg-risk
    fields. LT11 ambiguity A2: the vendored series treats ``ask == 1`` as two-sided; the design says two-sided means ``ask < 1`` (1.5, 4.2), so such rows
    move to the status file as ``one_sided`` (the conservative reading)."""
    ser, st = b.series_frame(rows, ext, spec)  # LT11 ambiguity A2: filtered below
    ask1 = ser["ask"].to_numpy(float) >= 1.0 - 1e-12
    if ask1.any():
        st = pd.concat([st, pd.DataFrame({"market_id": ser["market_id"].to_numpy()[ask1], "st": "one_sided"})], ignore_index=True)
        ser = ser[~ask1].reset_index(drop=True)
    mids = pd.Index(ser["market_id"].astype(str))
    r = rows.set_index(rows["market_id"].astype(str))
    for col, src in (("liq", "liquidity"), ("n_members", "n_members")):
        ser[col] = pd.to_numeric(r[src], errors="coerce").reindex(mids).to_numpy(float)
    ser["event_id"] = r["ekey"].reindex(mids).to_numpy(object)
    ser["condition_id"] = r["condition_id"].reindex(mids).fillna("").astype(str).to_numpy(object)
    ser["neg_risk_other"] = pd.Series([_flag_num(v) for v in r["neg_risk_other"].reindex(mids).tolist()]).to_numpy(float)
    if ext is not None:
        e = ext.reindex(mids)
        present = np.asarray(mids.isin(ext.index))
        has_col = bool(ext.attrs.get("has_clob_rewards", True))
        stt = [b.reward_detail(v, day) if (p and has_col) else (float("nan"), "no_sidecar" if not p else "no_column", "") for v, p in zip(e["clob_rewards"], present, strict=True)]
        ser["rew_rate"] = [x[0] for x in stt]
        ser["rew_state"] = [x[1] for x in stt]
        ser["rew_status"] = b.lt7_status(ser["rew_state"])
        ser["rew_min"] = pd.to_numeric(e["rewards_min_size"], errors="coerce").to_numpy(float)
        ser["rew_maxspread"] = pd.to_numeric(e["rewards_max_spread"], errors="coerce").to_numpy(float)
        ser["vnum"] = pd.to_numeric(e["volume_num"], errors="coerce").to_numpy(float)
        ser["vnum"] = np.where(np.isfinite(ser["vnum"].to_numpy(float)), ser["vnum"].to_numpy(float), np.nan)
        ser["side"] = present.astype(int)
        fc = e["fee_category"].where(e["fee_category"].notna(), None).tolist()
    else:
        present = np.zeros(len(mids), bool)
        ser["rew_rate"], ser["rew_state"], ser["rew_min"], ser["rew_maxspread"] = np.nan, "no_sidecar", np.nan, np.nan
        ser["rew_status"] = "absent"
        ser["vnum"], ser["side"] = np.nan, 0
        fc = [None] * len(mids)
    sp = ser["sports"].to_numpy(int)
    ser["fee_cat"] = pd.Series(fc, dtype=object).to_numpy()
    ser["crypto7"] = [b.crypto_class(f, bool(p), int(s)) for f, p, s in zip(fc, present, sp, strict=True)]
    return ser, st


def members11_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict) -> pd.DataFrame:
    """CH233's member table of a capture (3.2): every binary, open and active row with ``neg_risk`` true, with the event key (``neg_risk_market_id`` where
    present, else the Gamma ``event_id``, else the market itself), the two-sided flag (bid > 0, ask < 1, bid < ask: ``ask < 1`` is the design's rule, A2),
    the quote, the row receipt, the tick, ``neg_risk_other``, the augmented flag (NaN when missing: counted augmented by the callers), the category
    (``sports`` -1 = sidecar missing; ``crypto7``) and ``nr_conflict`` (the row's key group spans more than one Gamma event, counted ``nr_key_conflict``)."""
    cols = ["market_id", "condition_id", "nrkey", "event_id", "two", "bid", "ask", "t_row", "tick", "other", "aug", "sports", "crypto7", "nr_conflict"]
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
        fc = ext["fee_category"].reindex(pd.Index(mids)).astype(object).where(lambda s: s.notna(), None).tolist()
    else:
        fc = [None] * len(m)
    crypto7 = [b.crypto_class(f, bool(p), int(s)) for f, p, s in zip(fc, present, cat["sports"], strict=True)]
    g = pd.DataFrame({"k": key, "e": ev.to_numpy()})
    nev = g[g["e"] != ""].groupby("k")["e"].nunique()
    conflict = g["k"].map(nev).fillna(0).to_numpy(float) > 1
    return pd.DataFrame({"market_id": mids.to_numpy(), "condition_id": m["condition_id"].fillna("").astype(str).to_numpy(), "nrkey": key,
                         "event_id": np.where(ev != "", ev, "m:" + mids).astype(object), "two": two.astype(int), "bid": bid, "ask": ask, "t_row": m["t_row"].to_numpy(float),
                         "tick": cat["tick"], "other": np.array([_flag_num(v) for v in m["neg_risk_other"].tolist()], float),
                         "aug": np.array([_flag_num(v) for v in m["event_neg_risk_augmented"].tolist()], float), "sports": cat["sports"],
                         "crypto7": np.array(crypto7, dtype=object), "nr_conflict": conflict.astype(int)})


def write_series11(work: Path, cap: dict, spec: dict) -> dict:
    """Write-once ``series/<id>.csv.gz`` (two-sided quotes), ``status/<id>.csv.gz`` (the other binary rows), ``rw/<id>.csv.gz`` (LT8's :func:`b.rw_frame`
    of EVERY sidecar row, the carry's input) and ``members/<id>.csv.gz`` (CH233's neg-risk members). Returns the counts."""
    work = Path(work)
    cid = cap["id"]
    paths = [work / sub / f"{cid}.csv.gz" for sub in ("series", "status", "rw", "members")]
    if all(p.exists() for p in paths):
        return {"written": False}
    rows = load_rows11(cap["dir"])
    ext = load_ext11(cap["dir"])
    day = b._utc_day(cap["start"])
    ser, st = series11_frame(rows, ext, spec, day, cap["start"])
    mem = members11_frame(rows, ext, spec)
    w = [write_once_csv(paths[0], ser), write_once_csv(paths[1], st), write_once_csv(paths[2], b.rw_frame(ext, day)), write_once_csv(paths[3], mem)]
    return {"written": any(w), "rows": len(ser), "status_rows": len(st), "members": len(mem), "sidecar": ext is not None}


def read_series11(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    ser = b.read_series(work, cap_id)
    if ser is None:
        return None
    ser["condition_id"] = ser["condition_id"].fillna("").astype(str) if "condition_id" in ser else ""
    return ser


def read_status11(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(work) / "status" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "st": str}).drop_duplicates("market_id").set_index("market_id")


def read_members11(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(work) / "members" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "condition_id": str, "nrkey": str, "event_id": str, "crypto7": str}, keep_default_na=True)


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
    """Every listed slot with a complete capture already has its series file (a missing series file must never be read as a missing capture)."""
    return all((Path(root) / "series" / f"{by_slot[j]['id']}.csv.gz").exists() and (Path(root) / "members" / f"{by_slot[j]['id']}.csv.gz").exists() for j in slots if j in by_slot)


# --- access by slot, the causality guard (1.3) --------------------------------------------------------------------------------------------


class SlotStore:
    """Read access to the per-capture files by slot with a bounded cache. ``reads`` records every slot opened: the unit builders of origin k read only
    slots <= k (the unit test asserts ``max(reads) <= k``); twins and readings go through the lag loaders, never through this store."""

    def __init__(self, work: Path, by_slot: dict, spec: dict, cache_slots: int = 20) -> None:
        self.work, self.by_slot, self.spec, self.cache_slots = Path(work), by_slot, spec, cache_slots
        self.reads: set[int] = set()
        self._ser: dict[int, pd.DataFrame | None] = {}
        self._mem: dict[int, pd.DataFrame | None] = {}
        self._rw: dict[int, pd.DataFrame | None] = {}
        self._st: dict[int, pd.DataFrame | None] = {}
        self._tdec: dict[int, float] = {}
        self.mids = b.MidStore()
        self._added: set[int] = set()

    def has(self, j: int) -> bool:
        return j in self.by_slot

    def _trim(self, cache: dict, keep_from: int) -> None:
        for old in [s_ for s_ in cache if s_ < keep_from]:
            cache.pop(old)

    def ser(self, j: int) -> pd.DataFrame | None:
        if j not in self.by_slot:
            return None
        self.reads.add(j)
        if j not in self._ser:
            self._ser[j] = read_series11(self.work, self.by_slot[j]["id"])
            if len(self._ser) > self.cache_slots:
                self._trim(self._ser, j - self.cache_slots + 1)
        return self._ser[j]

    def status(self, j: int) -> pd.DataFrame | None:
        if j not in self.by_slot:
            return None
        self.reads.add(j)
        if j not in self._st:
            self._st[j] = read_status11(self.work, self.by_slot[j]["id"])
            if len(self._st) > self.cache_slots:
                self._trim(self._st, j - self.cache_slots + 1)
        return self._st[j]

    def members(self, j: int) -> pd.DataFrame | None:
        if j not in self.by_slot:
            return None
        self.reads.add(j)
        if j not in self._mem:
            self._mem[j] = read_members11(self.work, self.by_slot[j]["id"])
            if len(self._mem) > self.cache_slots:
                self._trim(self._mem, j - self.cache_slots + 1)
        return self._mem[j]

    def rw(self, j: int) -> pd.DataFrame | None:
        if j not in self.by_slot:
            return None
        self.reads.add(j)
        if j not in self._rw:
            self._rw[j] = b.read_rw8(self.work, self.by_slot[j]["id"])
            if len(self._rw) > self.cache_slots:
                self._trim(self._rw, j - self.cache_slots + 1)
        return self._rw[j]

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

    def carry(self, k: int) -> b.RewardCarry:
        """The 13.7 carry over slots [k - 11, k] (slot k's sidecar included, as LT9's census loop); ``apply`` itself reads only slots <= k - 1."""
        c = b.RewardCarry(b.REWARD_CARRY_SLOTS)
        for j in range(k - b.REWARD_CARRY_SLOTS + 1, k + 1):
            rw = self.rw(j)
            if rw is not None:
                c.add(j, rw)
        return c


# --- shared features (1.4, 1.5, 1.7) ----------------------------------------------------------------------------------------------------


def rewarded_of(ser_c: pd.DataFrame) -> np.ndarray:
    """``rewarded`` under ``listed_carry24h_v2`` of a carried frame: 1 when the (carried) rate is > 0, 0 when null without a positive listing in the window or
    listed-inactive, NaN when the status is malformed, absent (no sidecar row) or ``no_column``."""
    st = b._status_array(ser_c)
    rate = ser_c["rew_rate"].to_numpy(float)
    unk = np.isin(st, ["malformed", "absent", "no_column"]) | ~np.isfinite(rate)
    return np.where(unk, np.nan, (rate > 0).astype(float))


def carry_frame(carry: b.RewardCarry, ser: pd.DataFrame, k: int, day: str) -> pd.DataFrame:
    """The carry at slot ``k`` plus ``rewarded`` and ``carry_lag`` (0 when listed with a positive rate at k, j - source slot when carried, NaN otherwise)."""
    c = carry.apply(ser, k, day)
    rew = rewarded_of(c)
    lag = c["rew_carry_lag"].to_numpy(float)
    c["rewarded"] = rew
    c["carry_lag"] = np.where(rew == 1.0, np.where(np.isfinite(lag), lag, 0.0), np.nan)
    return c


def slot_dummies(u: pd.DataFrame, slot_of_day: int) -> None:
    """11 slot-of-day dummies (reference slot 0), 1.7."""
    for s in range(1, 12):
        u[f"sd{s}"] = float(slot_of_day == s)


def vnum_classes(vk, side_k, vp, side_p, slot_p_present: bool, tol: float = 1e-6) -> np.ndarray:
    """2.3: the ``volume_num`` class of each mover from the values keyed by their OWN slots (``vk`` = slot k's sidecar row, ``vp`` = slot k - 1's sidecar
    row and nothing else; the last non-missing value of an earlier slot never stands in, no value is carried in either direction).
    ``traded`` (both finite, ``v_k - v_{k-1} > 1e-6``), ``quote_only`` (both finite, ``|v_k - v_{k-1}| <= 1e-6``), else one of the four unknown sub-classes:
    ``vnum_missing_km1`` (slot k - 1 has no capture, no sidecar row of the market there, or an empty / non-numeric value), ``sidecar_missing`` (no sidecar
    row at k), ``vnum_missing_k`` (empty, NaN or non-numeric at k), ``vnum_decrease`` (``v_k < v_{k-1} - 1e-6``, a data anomaly). Unknown movers are never
    classed, imputed or re-classed from any other field."""
    vk, vp, side_k, side_p = (np.asarray(x, float) for x in (vk, vp, side_k, side_p))
    n = len(vk)
    if not slot_p_present:
        return np.full(n, "vnum_missing_km1", dtype=object)
    fk, fp = np.isfinite(vk), np.isfinite(vp) & (side_p == 1)
    out = np.full(n, "quote_only", dtype=object)
    with np.errstate(invalid="ignore"):
        dv = vk - vp
        out[dv > tol] = "traded"
        out[dv < -tol] = "vnum_decrease"
    out[~fp] = "vnum_missing_km1"
    out[~fk] = "vnum_missing_k"
    out[side_k != 1] = "sidecar_missing"
    out[~np.isfinite(side_k)] = "sidecar_missing"
    return out


def collateral_weight(d, p_prev) -> np.ndarray:
    """2.4: ``w = 0.5 + sign(d) x (p_{k-1} - 0.5)``: the collateral a share of the side whose buying moved the price (0.5 for a zero move)."""
    return 0.5 + np.sign(np.asarray(d, float)) * (np.asarray(p_prev, float) - 0.5)


def winsorise_absd(d) -> tuple[np.ndarray, np.ndarray]:
    """2.4: ``|d|`` winsorised at 0.20 (a declared convention) and the flag of the units it changed (counted)."""
    a = np.abs(np.asarray(d, float))
    return np.minimum(a, WINSOR_ABSD), (a > WINSOR_ABSD).astype(float)


def bin_index(p) -> np.ndarray:
    """2.4: the four declared bins of ``p_{k-1}`` ([0.04, 0.15), [0.15, 0.50), [0.50, 0.85), [0.85, 0.96]); -1 outside [0.04, 0.96]."""
    p = np.asarray(p, float)
    out = np.full(len(p), -1, dtype=int)
    for i, (lo, hi) in enumerate(BINS):
        out[(p >= lo - EPS) & (p < hi - EPS if i < 3 else p <= 0.96 + EPS)] = i
    return out


def zcentre(x, centre: float, scale: float) -> np.ndarray:
    """``z(x) = (x - c) / s`` with the census-fixed centre and scale (NaN when either is missing)."""
    if centre is None or scale is None or not (isinstance(scale, (int, float)) and math.isfinite(scale) and scale > 0):
        return np.full(len(np.asarray(x)), np.nan)
    return (np.asarray(x, float) - float(centre)) / float(scale)


def xw_term(w, absd, cf: dict | None) -> np.ndarray:
    """2.4: the centred product ``xw = z(w) x z(|d|)`` on the census-fixed centres and scales (``cf`` = ``census_fixed.CH234``); NaN while they are unfilled."""
    if not cf or any(cf.get(k) is None for k in ("w_centre", "w_scale", "absd_centre", "absd_scale")):
        return np.full(len(np.asarray(w)), np.nan)
    return zcentre(w, cf["w_centre"], cf["w_scale"]) * zcentre(absd, cf["absd_centre"], cf["absd_scale"])


def _tight(bid, ask, spread, spec: dict) -> np.ndarray:
    return b.tight_arr(bid, ask, spread, spec["eligibility"]["spread_max"])


def defined_mid(ser: pd.DataFrame | None, markets, spec: dict) -> np.ndarray:
    """4.2's defined mid at one slot: the market has a series row (open, active, binary, two-sided with ``ask < 1``) and the row is tight; anything else
    (capture missing, row absent, one-sided, not tight, closed) is NaN, never interpolated or carried."""
    mk = pd.Index(np.asarray(markets, dtype=str))
    if ser is None:
        return np.full(len(mk), np.nan)
    r = ser.reindex(mk)
    bid, ask, sp = r["bid"].to_numpy(float), r["ask"].to_numpy(float), r["spread"].to_numpy(float)
    ok = _tight(bid, ask, sp, spec)
    return np.where(ok, (bid + ask) / 2.0, np.nan)


def category_split(j: pd.DataFrame, cnt: dict) -> pd.DataFrame:
    """1.4: the category rule. Primary: sidecar says non-sports and the pinned classifier says non-crypto (``in_scope`` 1). The sports arm is kept
    (``in_scope`` 0, reported uncounted); crypto, unknown crypto class and a missing sidecar are counted and dropped (unknown is treated as crypto)."""
    sp = j["sports"].to_numpy(int)
    c7 = j["crypto7"].astype(str).to_numpy()
    cnt["sports_unknown"] = int((sp == -1).sum())
    cnt["sports_arm"] = int((sp == 1).sum())
    cnt["crypto"] = int(((sp == 0) & (c7 == "crypto")).sum())
    cnt["crypto_unknown"] = int(((sp == 0) & (c7 == "unknown")).sum())
    keep = (sp == 1) | ((sp == 0) & (c7 == "non_crypto"))
    j = j[keep].copy()
    j["in_scope"] = ((j["sports"].to_numpy(int) == 0) & (j["crypto7"].astype(str).to_numpy() == "non_crypto")).astype(int)
    return j


def pair_frame(store: SlotStore, k: int, spec: dict, margin_h: float) -> tuple[pd.DataFrame | None, dict, float]:
    """Markets two-sided and tight at k - 1 and k (the vendored LT3 ``move_join`` through ``_movers_join``), with the carried reward columns of slot k,
    the k - 1 columns this module needs (``tick_p``, ``vnum_p``, ``side_p``) and the end-date rule against the DECISION time (capture k's last row
    receipt, 1.3): end unknown or > t + ``margin_h``. Returns (frame or None, counts, t_dec). Reads only slots <= k."""
    cap = store.by_slot[k]
    cnt: dict = {}
    ser_k, ser_p = store.ser(k), store.ser(k - 1)
    t_dec = store.t_dec(k)
    if ser_k is None or ser_p is None or not math.isfinite(t_dec):
        return None, {"no_pair": 1}, t_dec
    day = b._utc_day(cap["start"])
    sc = carry_frame(store.carry(k), ser_k, k, day)
    j, cnt = b._movers_join(sc, ser_p, cap, spec, 0.0, 1.0, 0.0)
    j = j.copy()
    p = ser_p.reindex(j["market_id"].astype(str))
    j["tick_p"], j["vnum_p"], j["side_p"] = p["tick"].to_numpy(float), p["vnum"].to_numpy(float), p["side"].to_numpy(float)
    end = j["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        eok = np.isnan(end) | (end > t_dec + margin_h * 3600.0)
    cnt["end_date_decision"] = int((~eok).sum())
    j = j[eok].reset_index(drop=True)
    return j, cnt, t_dec


def momentum_cols(store: SlotStore, k: int, mk: np.ndarray, mid_k: np.ndarray, sign: np.ndarray | None = None) -> dict:
    """1.7 / 1.5: the own 6 h and 24 h changes (``mid_k - mid_{k-3}``, ``mid_k - mid_{k-12}``, a missing slot enters 0 with the single indicator
    ``mom_missing``, which a missing venue ``chg_1h`` also sets) as arrays; ``sign`` multiplies them (CH234's sign-adjusted form, LT11 ambiguity A3)."""
    M = store.mid_store(k).matrix(k, 12, mk, "mid")
    s = np.ones(len(mk)) if sign is None else np.asarray(sign, float)
    d6, m6 = b._own24(s, mid_k, M[:, 9])
    d24, m24 = b._own24(s, mid_k, M[:, 0])
    return {"own6": d6, "own24": d24, "mom_missing_own": np.maximum(m6, m24), "M": M}


def common_controls(store: SlotStore, k: int, j: pd.DataFrame, t_dec: float, spec: dict, sign: np.ndarray | None = None) -> pd.DataFrame:
    """The market-state and momentum block K (1.7) for the pair frame ``j`` (columns ``mid``, ``mid_p``, ``tick``, ``liq``, ``vol24``, ``end_ts``,
    ``chg_*``, ``neg_risk``, ``rewarded``, ``n_members``): the level at k, the spread at k (cents), ``log1p liquidity``, ``log1p volume24hr`` with
    ``vol_missing``, log hours-to-end with ``hte_unknown``, ``1[tick = 0.001]``, ``log rv24*`` over 12 slots, ``neg_risk``, ``rewarded_k``, the 6 h /
    24 h own changes and the venue ``chg_1h`` with ``mom_missing``, ``chg_1d`` / ``chg_1w`` as indicator pairs when the pre-check found them (K's
    columns are fixed by ``spec['k_block']``), and the 11 slot-of-day dummies."""
    mk = j["market_id"].astype(str).to_numpy()
    mid = j["mid"].to_numpy(float)
    mom = momentum_cols(store, k, mk, mid, sign)
    s = np.ones(len(j)) if sign is None else np.asarray(sign, float)
    kb = spec.get("k_block") or {}
    chg1h = j["chg_1h"].to_numpy(float)
    c1h = np.where(np.isfinite(chg1h), chg1h, 0.0) * s
    u = pd.DataFrame({"p_k": mid, "spread_c": (j["ask"].to_numpy(float) - j["bid"].to_numpy(float)) * 100.0, "own6": mom["own6"], "own24": mom["own24"], "chg1h": c1h,
                      "mom_missing": np.maximum(mom["mom_missing_own"], (~np.isfinite(chg1h)).astype(float)),
                      "neg_risk": j["neg_risk"].to_numpy(float), "rewarded": j["rewarded"].to_numpy(float), "n_members": j["n_members"].to_numpy(float)})
    for name, flag in (("chg_1d", "chg1d_missing"), ("chg_1w", "chg1w_missing")):
        if kb.get(name):
            v = j[name].to_numpy(float)
            u[name.replace("_", "")] = np.where(np.isfinite(v), v, 0.0) * s
            u[flag] = (~np.isfinite(v)).astype(float)
    tmp = pd.DataFrame({"tick": j["tick"].to_numpy(float), "liq": j["liq"].to_numpy(float), "end_ts": j["end_ts"].to_numpy(float), "mid": mid, "t_row": np.full(len(j), t_dec)})
    cc = b._common_cols(tmp)
    u["tick001"], u["log_hte"], u["hte_unknown"], u["log1p_liq"] = cc["tick001"].to_numpy(float), cc["log_hte"].to_numpy(float), cc["hte_unknown"].to_numpy(float), cc["log1p_liq"].to_numpy(float)
    u["log1p_vol"], u["vol_missing"] = b._vol_cols(j["vol24"].to_numpy(float))
    rv, rvs, rvf = b._rv24(store.mid_store(k), k, mk, j["tick"].to_numpy(float), spec["rv"])
    with np.errstate(invalid="ignore", divide="ignore"):
        u["log_rv24s"] = np.log(rvs)
    u["rv_floor"] = rvf
    slot_dummies(u, k % 12)
    return u


def _stamp(df: pd.DataFrame, spec: dict, commit: str, role: str) -> pd.DataFrame:
    df = df.drop(columns=[c for c in ("frozen_utc", "code_commit", "spec_sha", "code_sha", "role") if c in df.columns])
    df["frozen_utc"] = iso(now_ts())
    df["code_commit"], df["spec_sha"], df["code_sha"], df["role"] = commit, spec["_sha256"][:16], reader_sha(), role
    return df


def _base_cols(j: pd.DataFrame, cap: dict, k: int, t_dec: float, kind: str) -> dict:
    return {"market_id": j["market_id"].astype(str).to_numpy(), "event_id": j["event_id"].astype(str).to_numpy(), "skey": j["skey"].astype(str).to_numpy(),
            "sports": j["sports"].to_numpy(int), "in_scope": j["in_scope"].to_numpy(int), "day": b._utc_day(cap["start"]), "slot": k, "t_row": np.full(len(j), t_dec),
            "kind": kind, "condition_id": j["condition_id"].astype(str).to_numpy(object)}


def tick_rule(j: pd.DataFrame, cnt: dict) -> pd.DataFrame:
    """1.4: ``order_price_min_tick_size`` equal at k - 1 and k, else the unit is excluded (``tick_changed``); an unknown tick at either is counted
    ``tick_unknown`` and excluded (LT11 ambiguity A4: the text names only the changed case, an unknown tick is the conservative reading)."""
    t, tp = j["tick"].to_numpy(float), j["tick_p"].to_numpy(float)
    unk = ~(np.isfinite(t) & np.isfinite(tp))
    changed = ~unk & (np.abs(t - tp) > 1e-12)
    cnt["tick_unknown"], cnt["tick_changed"] = int(unk.sum()), int(changed.sum())
    return j[~unk & ~changed].reset_index(drop=True)


# --- CH234: the dollar weight of a move (section 2) ------------------------------------------------------------------------------------------


def ch234_units(store: SlotStore, k: int, spec: dict, role: str = ROLE_UNREG, commit: str = "unknown", stamp: bool = True) -> tuple[pd.DataFrame, dict]:
    """CH234's units of origin k (2.2-2.4): non-sports ex-crypto markets two-sided and tight at k - 1 and k, ``p_{k-1}`` in [0.04, 0.96], ``|d_k| >= 0.01``,
    tick unchanged, end unknown or > t + 3 h (``f_end_ok``: > t + 7 h for the F arm), classed by ``volume_num`` (2.3: traded / quote_only / the four
    unknown sub-classes, ``vclass``); the member cap is the ``ladder`` flag (primary ``n_members <= 10``). One line per unit with the raw collateral weight
    ``w`` and winsorised ``absd`` (the centred product ``xw`` is added on the census-fixed scales when they exist), the level-drift-by-bin controls and
    the known-factor block K (momentum sign-adjusted by ``sign(d)``, LT11 ambiguity A3). Reads only slots <= k."""
    t = spec["tests"]["CH234"]
    j, cnt, t_dec = pair_frame(store, k, spec, t["end_margin_h"])
    if j is None:
        return pd.DataFrame(), cnt
    cap = store.by_slot[k]
    cnt["pair_units"] = len(j)
    j = category_split(j, cnt)
    j = tick_rule(j, cnt)
    p_prev = j["mid_p"].to_numpy(float)
    inband = (p_prev >= t["p_lo"] - EPS) & (p_prev <= t["p_hi"] + EPS)
    cnt["p_band"] = int((~inband).sum())
    j = j[inband].reset_index(drop=True)
    d = j["mid"].to_numpy(float) - j["mid_p"].to_numpy(float)
    mover = np.abs(d) >= t["min_abs_d"] - EPS
    cnt["not_mover"] = int((~mover).sum())
    j = j[mover].reset_index(drop=True)
    if j.empty:
        return pd.DataFrame(), cnt
    d = j["mid"].to_numpy(float) - j["mid_p"].to_numpy(float)
    sgn = np.sign(d)
    vcl = vnum_classes(j["vnum"].to_numpy(float), j["side"].to_numpy(float), j["vnum_p"].to_numpy(float), j["side_p"].to_numpy(float), True)
    for c_ in ("traded", "quote_only", "vnum_missing_k", "vnum_missing_km1", "vnum_decrease", "sidecar_missing"):
        cnt[f"vclass_{c_}"] = int((vcl == c_).sum())
    absd, wins = winsorise_absd(d)
    cnt["winsorised"] = int(wins.sum())
    p_prev = j["mid_p"].to_numpy(float)
    w = collateral_weight(d, p_prev)
    bi = bin_index(p_prev)
    X = common_controls(store, k, j, t_dec, spec, sign=sgn)
    end = j["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        f_ok = (np.isnan(end) | (end > t_dec + t["f_end_margin_h"] * 3600.0)).astype(float)
    u = pd.DataFrame({**_base_cols(j, cap, k, t_dec, KINDS["CH234"]), "vclass": vcl, "d": d, "sgn": sgn, "p_prev": p_prev, "absd": absd, "absd_wins": wins, "w": w, "bin": bi,
                      "ladder": (j["n_members"].to_numpy(float) > spec["member_cap"]["max_members"]).astype(int), "f_end_ok": f_ok, "tick": j["tick"].to_numpy(float),
                      "fee_cat": j["fee_cat"].to_numpy(object)})
    for i, ctr in enumerate(BIN_CENTRES):
        on = (bi == i).astype(float) * sgn
        u[f"sb{i}"], u[f"sb{i}_lvl"] = on, on * (p_prev - ctr)
    u = pd.concat([u, X.reset_index(drop=True)], axis=1)
    cf = (spec.get("census_fixed") or {}).get("CH234")
    u["xw"] = xw_term(u["w"].to_numpy(float), u["absd"].to_numpy(float), cf)
    u = b._drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "rewarded": "reward_unparseable"})
    cnt["units"] = len(u)
    return (_stamp(u, spec, commit, role) if stamp else u), cnt


# --- CH232: the cheap side's cliff (section 4) ------------------------------------------------------------------------------------------


# arm -> (band, zones of m_{k-1}, direction). "out" is the primary (4.2); "in" is S1 (the inward twin, predicted < 0), "pseudo" S2 (the 0.20 / 0.80 placebo).
ARMS = {"out": ((0.10, 0.90), ((0.10, 0.14), (0.86, 0.90)), "out"),
        "in": ((0.10, 0.90), ((0.06, 0.10 - 2 * EPS), (0.90 + 2 * EPS, 0.94)), "in"),
        "pseudo": ((0.20, 0.80), ((0.20, 0.24), (0.76, 0.80)), "out")}


def in_band(m, band) -> np.ndarray:
    """4.2: the closed band ``B`` with tolerance 1e-9 (NaN is never inside)."""
    m = np.asarray(m, float)
    with np.errstate(invalid="ignore"):
        return (m >= band[0] - EPS) & (m <= band[1] + EPS)


def crossing(m_prev, m_cur, band, direction: str = "out") -> np.ndarray:
    """4.2: an outward crossing at one interval is ``m_prev`` inside ``B`` and ``m_cur`` outside it (inward: the reverse); exists only where BOTH mids are
    defined (NaN gives False): never across a gap."""
    a, c = np.asarray(m_prev, float), np.asarray(m_cur, float)
    ok = np.isfinite(a) & np.isfinite(c)
    ia, ic = in_band(a, band), in_band(c, band)
    return ok & ((ia & ~ic) if direction == "out" else (~ia & ic))


def reward_side_weight(mid, c: float = REWARD_SINGLE_SIDE_C) -> np.ndarray:
    """1.4.2, the documented reading (the ledger record of the design-text freeze, M1 cheap side): inside [0.10, 0.90] a one-sided quote scores at the reduced
    weight ``1 / c`` (``c = 3.0``); outside it only two-sided quoting scores (weight 0). Used only to name which side retreats at an outward crossing."""
    m = np.asarray(mid, float)
    return np.where(in_band(m, BAND), 1.0 / c, 0.0)


def m1_side(reading: str = M1_SIDE_READING) -> tuple[str, ...]:
    """1.4.2: the reading fixes only the side of M1: the cheap side under the documented reading, the dear side under the reverse reading; a page that states
    neither gives both sides (a two-row table)."""
    return {"cheap": ("cheap",), "dear": ("dear",)}.get(reading, ("cheap", "dear"))


def cheap_side(mid_k) -> np.ndarray:
    """4.2: the CHEAP side at k is the side that costs little collateral: below 0.10 the YES bid, above 0.90 the YES ask (the dear side is the other)."""
    return np.where(np.asarray(mid_k, float) < 0.5, "bid", "ask").astype(object)


def ch232_units(store: SlotStore, k: int, spec: dict, role: str = ROLE_UNREG, commit: str = "unknown", stamp: bool = True,
                arms: tuple[str, ...] = ("out", "in", "pseudo")) -> tuple[pd.DataFrame, dict]:
    """CH232's units of origin k (4.2-4.3) for every arm: markets with a defined mid at k - 1 and k whose ``m_{k-1}`` lies in the arm's approach zone,
    ``|d_k| >= 0.01`` (``half_tick``), crossings only between consecutive defined mids, ``xo`` = the first crossing of the UTC day (reading only earlier
    slots of that day), ``xr`` = a later one; a unit whose UTC day has a missing earlier capture slot is excluded (``day_gap``) and so is one with any
    undefined same-day earlier mid of its own market (``day_gap_market``); tick-coincident units (``m_k`` beyond 0.04 / 0.96) are excluded and counted.
    ``rew`` is ``listed_carry24h_v2`` at k (NaN excluded and counted); the panel is fixed later (:func:`fix_panels11`). Reads only slots <= k."""
    t = spec["tests"]["CH232"]
    j0, cnt0, t_dec = pair_frame(store, k, spec, t["end_margin_h"])
    if j0 is None:
        return pd.DataFrame(), cnt0
    cap = store.by_slot[k]
    ds = day_start_slot(k)
    earlier = list(range(ds, k))
    gap_slots = [s_ for s_ in earlier if s_ not in store.by_slot]
    out, tot = [], {"pair_units": len(j0)}
    j0 = category_split(j0, tot)
    j0 = tick_rule(j0, tot)
    for arm in arms:
        band, zones, direction = ARMS[arm]
        cnt: dict = {}
        j = j0
        mp = j["mid_p"].to_numpy(float)
        zone = np.zeros(len(j), bool)
        for lo, hi in zones:
            zone |= (mp >= lo - EPS) & (mp <= hi + EPS)
        cnt["zone"] = int(zone.sum())
        j = j[zone].reset_index(drop=True)
        d = j["mid"].to_numpy(float) - j["mid_p"].to_numpy(float)
        mover = np.abs(d) >= t["min_abs_d"] - EPS
        cnt["half_tick"] = int((~mover).sum())
        j = j[mover].reset_index(drop=True)
        mk = j["market_id"].astype(str).to_numpy()
        mk_ = j["mid"].to_numpy(float)
        coin = (mk_ < 0.04 - EPS) | (mk_ > 0.96 + EPS)
        cnt["tick_coincident"] = int(coin.sum())
        j = j[~coin].reset_index(drop=True)
        mk = j["market_id"].astype(str).to_numpy()
        if gap_slots:
            cnt["day_gap"] = len(j)
            j = j.iloc[0:0]
            mk = mk[:0]
        else:
            cnt["day_gap"] = 0
        if len(j):
            DM = np.column_stack([defined_mid(store.ser(s_), mk, spec) for s_ in range(ds - 1, k + 1)])  # columns: slots ds-1 .. k
            ok_day = np.all(np.isfinite(DM[:, 1:k - ds + 1]), axis=1) if earlier else np.ones(len(j), bool)
            cnt["day_gap_market"] = int((~ok_day).sum())
            j, DM, mk = j[ok_day].reset_index(drop=True), DM[ok_day], mk[ok_day]
        if j.empty:
            cnt["units"] = 0
            tot[f"arm_{arm}"] = cnt
            continue
        prev_cross = np.zeros(len(j), bool)
        for i_ in range(len(earlier)):  # intervals (s-1, s] of the day: columns i_ (slot s-1) and i_ + 1 (slot s)
            prev_cross |= crossing(DM[:, i_], DM[:, i_ + 1], band, direction)
        cur = crossing(DM[:, -2], DM[:, -1], band, direction)
        xo, xr = (cur & ~prev_cross).astype(float), (cur & prev_cross).astype(float)
        rew = j["rewarded"].to_numpy(float)
        cnt["reward_unparseable"] = int((~np.isfinite(rew)).sum())
        d = j["mid"].to_numpy(float) - j["mid_p"].to_numpy(float)
        mp = j["mid_p"].to_numpy(float)
        lower = mp < 0.5
        bd_ = np.where(lower, band[0], band[1])
        dist = np.abs(mp - bd_)
        spr_k = (j["ask"].to_numpy(float) - j["bid"].to_numpy(float))
        spr_p = (j["ask_p"].to_numpy(float) - j["bid_p"].to_numpy(float))
        tick = j["tick"].to_numpy(float)
        S_k, S_p = np.rint(spr_k / tick), np.rint(spr_p / tick)
        dS = S_k - S_p
        v = np.where(rew == 1.0, j["rew_maxspread"].to_numpy(float), 0.0)
        rate = j["rew_rate"].to_numpy(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            lr = np.where((rew == 1.0) & (rate > 0), np.log(rate), 0.0)
        X = common_controls(store, k, j, t_dec, spec, sign=None)
        end = j["end_ts"].to_numpy(float)
        with np.errstate(invalid="ignore"):
            f_ok = (np.isnan(end) | (end > t_dec + t["f_end_margin_h"] * 3600.0)).astype(float)
        u = pd.DataFrame({**_base_cols(j, cap, k, t_dec, KINDS["CH232"]), "arm": arm, "rew": rew, "xo": xo, "xr": xr, "cross_any": cur.astype(float), "d": d, "absd": np.abs(d),
                          "d_tow": np.where(lower, -d, d) * (1.0 if direction == "out" else -1.0), "dist": dist, "upper": (~lower).astype(float), "m_prev": mp, "m_k": j["mid"].to_numpy(float),
                          "bid_k": j["bid"].to_numpy(float), "ask_k": j["ask"].to_numpy(float), "spread_k_c": spr_k * 100.0, "dspread_c": (spr_k - spr_p) * 100.0,
                          "S2": (S_k == 2).astype(float), "S3": (S_k == 3).astype(float), "S4p": (S_k >= 4).astype(float), "dSm2p": (dS <= -2).astype(float),
                          "dSm1": (dS == -1).astype(float), "dSp1": (dS == 1).astype(float), "dSp2p": (dS >= 2).astype(float), "v_c": v, "log_rate": lr,
                          "cheap_side": cheap_side(j["mid"].to_numpy(float)),
                          "ladder": (j["n_members"].to_numpy(float) > spec["member_cap"]["max_members"]).astype(int), "f_end_ok": f_ok, "tick": tick,
                          "fee_cat": j["fee_cat"].to_numpy(object)})
        u = pd.concat([u, X.reset_index(drop=True)], axis=1)
        u = b._drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "rew": "reward_status_nan", "v_c": "band_missing"})
        cnt["units"], cnt["crossings"] = len(u), int(u["xo"].sum())
        tot[f"arm_{arm}"] = cnt
        out.append(u)
    if not out:
        return pd.DataFrame(), tot
    U = pd.concat(out, ignore_index=True)
    return (_stamp(U, spec, commit, role) if stamp else U), tot


def fix_panels11(U: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """1.4.1: each market's panel is ``rew`` at its FIRST unit of the arm in the window (ordered by slot); later units of the opposite status are
    excluded (``panel_switched``, counted), as LT9 CH213. Adds ``panel`` (= ``rew``)."""
    if U.empty:
        return U, {"panel_switched": 0}
    U = U.sort_values(["market_id", "slot"], kind="mergesort").reset_index(drop=True)
    panel_m = U.groupby("market_id")["rew"].transform("first").to_numpy(float)
    sw = U["rew"].to_numpy(float) != panel_m
    cnt = {"panel_switched": int(sw.sum()), "panel_switched_reward": int((sw & (panel_m == 1)).sum()), "panel_switched_control": int((sw & (panel_m == 0)).sum())}
    U = U[~sw].reset_index(drop=True)
    U["panel"] = U["rew"]
    return U, cnt


# --- CH233: the arb's footprint (section 3) ---------------------------------------------------------------------------------------------


def event_captures(M: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The members table of a capture grouped by event key (``{nrkey: members}``)."""
    if M is None or M.empty:
        return {}
    return {k_: g for k_, g in M.groupby("nrkey", sort=False)}


def size_class(n: int) -> str:
    """3.2 / 3.4: ``2`` (reported arm), ``3-5``, ``6-10`` (the primary's two size classes), ``11+`` (the ladder arm); ``1`` has no unit."""
    return "1" if n < 2 else "2" if n == 2 else "3-5" if n <= 5 else "6-10" if n <= 10 else "11+"


def event_pairs(Mp: pd.DataFrame | None, Mk: pd.DataFrame | None, spec: dict) -> tuple[dict, dict]:
    """The event-capture pair logic of 3.2 on the member tables of captures k - 1 and k. Returns (``pairs``: key -> record, counts). A record holds the
    pair's members at k - 1 and k, its ``reason`` (``category``, ``members_changed``, ``event_incomplete``, ``receipt_span``, ``single`` or ``ok``), its
    ``arm`` (``primary`` for 3-10 members, ``size2``, ``ladder``) and ``augmented`` (any eligible member with the field non-zero or MISSING at k - 1 or k: the
    reported arm). Order of the exclusions (counted once, first match): category (sports, crypto or unknown on any member), members_changed (the eligible
    member sets differ), event_incomplete (a member not two-sided at k - 1 or k), receipt_span (the members' ``received_utc`` span above 120 s at k - 1 or
    k). Nothing is filled: an incomplete pair gives no unit for any member, no bid is set to 0 or carried. Reads only the two tables."""
    cnt = Counter()
    pairs: dict = {}
    ek, ep = event_captures(Mk), event_captures(Mp)
    span_s = float(spec.get("receipt_span_s", RECEIPT_SPAN_S))
    for key, gk in ek.items():
        gp = ep.get(key)
        n_k = len(gk)
        rec = {"key": key, "n_k": n_k, "size_class": size_class(n_k), "gk": gk, "gp": gp, "reason": "ok", "augmented": False,
               "arm": "primary" if 3 <= n_k <= 10 else ("size2" if n_k == 2 else ("ladder" if n_k >= 11 else "single"))}
        cnt["event_captures"] += 1
        cnt["member_rows"] += n_k
        if gp is None:
            rec["reason"] = "members_changed"
        elif any(((g_["sports"].to_numpy(int) != 0) | (g_["crypto7"].astype(str).to_numpy() != "non_crypto")).any() for g_ in (gk, gp)):
            rec["reason"] = "category"
        elif set(gk["market_id"]) != set(gp["market_id"]):
            rec["reason"] = "members_changed"
        elif (gk["two"].to_numpy(int) != 1).any() or (gp["two"].to_numpy(int) != 1).any():
            rec["reason"] = "event_incomplete"
        else:
            span_k = float(np.nanmax(gk["t_row"].to_numpy(float)) - np.nanmin(gk["t_row"].to_numpy(float)))
            span_p = float(np.nanmax(gp["t_row"].to_numpy(float)) - np.nanmin(gp["t_row"].to_numpy(float)))
            rec["span_k"], rec["span_p"] = span_k, span_p
            if not (span_k <= span_s and span_p <= span_s):  # NaN fails (never a unit on an unreadable receipt)
                rec["reason"] = "receipt_span"
        if gp is not None:
            aug = np.concatenate([gk["aug"].to_numpy(float), gp["aug"].to_numpy(float)])
            rec["augmented"] = bool((~np.isfinite(aug) | (aug != 0)).any())
        else:
            aug = gk["aug"].to_numpy(float)
            rec["augmented"] = bool((~np.isfinite(aug) | (aug != 0)).any())
        cnt[f"reason_{rec['reason']}"] += 1
        cnt[f"rows_{rec['reason']}"] += n_k
        if rec["reason"] != "category":
            cnt["nr_key_conflict_rows"] += int(gk["nr_conflict"].sum())
        pairs[key] = rec
    return pairs, dict(cnt)


def headroom(g: pd.DataFrame) -> float:
    """3.3: ``hb = 1 - sum of the members' bids`` (signed)."""
    return 1.0 - float(g["bid"].sum())


def member_states(rec: dict) -> pd.DataFrame:
    """3.3: the per-member states of one complete event-capture pair (``rec`` from :func:`event_pairs`): ``cl_sib`` = the siblings' bid-sum change over
    (k - 1, k] in cents (positive = the headroom closed because of the other members), ``ca_sib`` the ask-sum twin regressor, the headroom at k - 1 and k, the
    LARGEST member tick at k - 1 (``|hb| <= 2 x tick_e`` is the working range), the member's own bid change, its bid share, the event's mid overround and the
    favourite flag. Index = market_id. No quote of a slot other than k - 1 and k is touched."""
    gk, gp = rec["gk"].set_index("market_id"), rec["gp"].set_index("market_id")
    gp = gp.reindex(gk.index)
    bk, bp = gk["bid"].to_numpy(float), gp["bid"].to_numpy(float)
    ak, ap = gk["ask"].to_numpy(float), gp["ask"].to_numpy(float)
    sum_bk, sum_bp, sum_ak, sum_ap = bk.sum(), bp.sum(), ak.sum(), ap.sum()
    tick_p = float(np.nanmax(gp["tick"].to_numpy(float)))
    tick_k = float(np.nanmax(gk["tick"].to_numpy(float)))
    hb_p, hb_k = 1.0 - sum_bp, 1.0 - sum_bk
    rank = pd.Series(bk).rank(ascending=False, method="min").to_numpy()
    return pd.DataFrame({"cl_sib": ((sum_bk - bk) - (sum_bp - bp)) * 100.0, "ca_sib": ((sum_ak - ak) - (sum_ap - ap)) * 100.0, "hb_km1": hb_p, "hb_k": hb_k, "tick_e": tick_p,
                         "near_zero_km1": float(abs(hb_p) <= 2.0 * tick_p + EPS), "near_zero_k": float(abs(hb_k) <= 2.0 * tick_k + EPS), "own_dbid_c": (bk - bp) * 100.0,
                         "bid_share": bk / sum_bk if sum_bk > 0 else math.nan, "overround": float(((bk + ak) / 2.0).sum() - 1.0), "fav": (rank == 1).astype(float)}, index=gk.index)


def ch233_units(store: SlotStore, k: int, spec: dict, role: str = ROLE_UNREG, commit: str = "unknown", stamp: bool = True) -> tuple[pd.DataFrame, dict]:
    """CH233's units of origin k (3.2-3.3): one line per eligible member of every complete (k - 1, k) event-capture pair with the receipt-span rule, for the
    primary arm (3-10 members, non-augmented) and the reported arms (``size2``, ``ladder``, ``augmented``; ``arm`` column). The state ``cl_sib`` is the
    siblings' bid-sum change over (k - 1, k] in cents (positive = the headroom closed because of the other members), ``ca_sib`` the ask-sum twin regressor.
    Member-level filters (tight at both, end rule, tick unchanged, reward status known, required controls) remove a member's unit only; the event-capture
    stays complete for its other members. Reads only slots <= k."""
    t = spec["tests"]["CH233"]
    Mp, Mk = store.members(k - 1), store.members(k)
    ser_k, ser_p = store.ser(k), store.ser(k - 1)
    t_dec = store.t_dec(k)
    if Mp is None or Mk is None or ser_k is None or ser_p is None or not math.isfinite(t_dec):
        return pd.DataFrame(), {"no_pair": 1}
    cap = store.by_slot[k]
    pairs, cnt = event_pairs(Mp, Mk, spec)
    cnt = {**cnt, "pair_units": len(Mk)}
    parts = []
    for r in pairs.values():
        if r["reason"] != "ok" or r["size_class"] == "1":
            continue
        ms = member_states(r)
        ms["nrkey"], ms["size_class"], ms["n_elig"] = r["key"], r["size_class"], r["n_k"]
        ms["arm"] = "augmented" if r["augmented"] else ("primary" if r["arm"] == "primary" else r["arm"])
        ms["span_k"], ms["span_p"] = r.get("span_k", math.nan), r.get("span_p", math.nan)
        parts.append(ms)
    if not parts:
        return pd.DataFrame(), cnt
    U = pd.concat(parts).rename_axis("market_id").reset_index()
    mk = pd.Index(U["market_id"].astype(str), name="market_id")
    day = b._utc_day(cap["start"])
    sc = carry_frame(store.carry(k), ser_k, k, day)
    J = sc.reindex(mk).reset_index()
    jp = ser_p.reindex(mk)
    J["mid"] = (J["bid"] + J["ask"]) / 2.0
    J["mid_p"] = ((jp["bid"] + jp["ask"]) / 2.0).to_numpy(float)
    J["bid_p"], J["ask_p"] = jp["bid"].to_numpy(float), jp["ask"].to_numpy(float)
    J["spread_p_g"], J["tick_p"] = jp["spread"].to_numpy(float), jp["tick"].to_numpy(float)
    J["event_id"] = U["nrkey"].to_numpy(object)
    J["in_scope"] = 1
    present = J["bid"].notna().to_numpy() & jp["bid"].notna().to_numpy()
    cnt["member_not_in_series"] = int((~present).sum())
    keep = present.copy()
    tight = _tight(J["bid"], J["ask"], J["spread"], spec) & _tight(J["bid_p"], J["ask_p"], J["spread_p_g"], spec)
    cnt["not_tight"] = int((keep & ~tight).sum())
    keep &= tight
    end = J["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        eok = np.isnan(end) | (end > t_dec + t["end_margin_h"] * 3600.0)
    cnt["end_date"] = int((keep & ~eok).sum())
    keep &= eok
    tk, tkp = J["tick"].to_numpy(float), J["tick_p"].to_numpy(float)
    unk = ~(np.isfinite(tk) & np.isfinite(tkp))
    chg = ~unk & (np.abs(tk - tkp) > 1e-12)
    cnt["tick_unknown"], cnt["tick_changed"] = int((keep & unk).sum()), int((keep & chg).sum())
    keep &= ~unk & ~chg
    dup = J["condition_id"].astype(str).duplicated().to_numpy() & (J["condition_id"].astype(str) != "").to_numpy()  # defensive: load_rows11 already dedupes
    cnt["dup_condition_id"] = int((keep & dup).sum())
    keep &= ~dup
    U, J = U[keep].reset_index(drop=True), J[keep].reset_index(drop=True)
    if U.empty:
        return pd.DataFrame(), cnt
    X = common_controls(store, k, J, t_dec, spec, sign=None)
    end = J["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        f_end = (np.isnan(end) | (end > t_dec + t["f_end_margin_h"] * 3600.0)).astype(float)
    out = pd.DataFrame({**_base_cols(J, cap, k, t_dec, KINDS["CH233"]), "arm": U["arm"].to_numpy(object), "nrkey": U["nrkey"].to_numpy(object),
                        "size_class": U["size_class"].to_numpy(object), "n_elig": U["n_elig"].to_numpy(float), "cl_sib": U["cl_sib"].to_numpy(float),
                        "ca_sib": U["ca_sib"].to_numpy(float), "hb_km1": U["hb_km1"].to_numpy(float), "hb_k": U["hb_k"].to_numpy(float), "tick_e": U["tick_e"].to_numpy(float),
                        "near_zero_km1": U["near_zero_km1"].to_numpy(float), "near_zero_k": U["near_zero_k"].to_numpy(float), "own_dbid_c": U["own_dbid_c"].to_numpy(float),
                        "own_dspread_c": ((J["ask"] - J["bid"]) - (J["ask_p"] - J["bid_p"])).to_numpy(float) * 100.0, "d": (J["mid"] - J["mid_p"]).to_numpy(float),
                        "bid_share": U["bid_share"].to_numpy(float), "overround": U["overround"].to_numpy(float), "fav": U["fav"].to_numpy(float),
                        "nr_other": J["neg_risk_other"].to_numpy(float), "f_end_ok": f_end, "bid_k": J["bid"].to_numpy(float), "ask_k": J["ask"].to_numpy(float),
                        "spread_k_c": (J["ask"] - J["bid"]).to_numpy(float) * 100.0, "tick": J["tick"].to_numpy(float), "span_k": U["span_k"].to_numpy(float),
                        "span_p": U["span_p"].to_numpy(float), "fee_cat": J["fee_cat"].to_numpy(object)})
    out["event_id"] = out["nrkey"]
    out = pd.concat([out, X.reset_index(drop=True)], axis=1)
    cf = (spec.get("census_fixed") or {}).get("CH233") or {}
    out["zcl"] = zcl_term(out["cl_sib"].to_numpy(float), out["size_class"].to_numpy(object), cf)
    out["zca"] = zcl_term(out["ca_sib"].to_numpy(float), out["size_class"].to_numpy(object), cf)
    out = b._drop_missing(out, cnt, {"log_rv24s": "rv24_undefined", "rewarded": "reward_unparseable"})
    cnt["units"] = len(out)
    cnt["primary_units"] = int((out["arm"] == "primary").sum())
    return (_stamp(out, spec, commit, role) if stamp else out), cnt


def zcl_term(raw_c, size_cls, cf: dict | None) -> np.ndarray:
    """3.3: ``z cl_sib = cl_sib / s_c`` with ``s_c`` the census pooled SD of ``cl_sib`` in the member's size class (3-5 or 6-10), fixed in the spec; NaN for any
    other size class (the reported arms are scaled with the size class they are nearest to: 2 -> 3-5, 11+ -> 6-10, LT11 ambiguity A8) or while unfilled."""
    raw_c = np.asarray(raw_c, float)
    sc = (cf or {}).get("s_c") or {}
    out = np.full(len(raw_c), np.nan)
    for cls, s in (("3-5", sc.get("3-5")), ("6-10", sc.get("6-10")), ("2", sc.get("3-5")), ("11+", sc.get("6-10"))):
        if s is None or not (isinstance(s, (int, float)) and math.isfinite(s) and s > 0):
            continue
        m = np.asarray(size_cls, dtype=object) == cls
        out[m] = raw_c[m] / float(s)
    return out
