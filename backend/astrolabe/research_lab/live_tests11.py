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

import fcntl
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
OPS_COLS = frozenset({"role", "kind", "sports", "in_scope", "crypto", "status", "late", "vclass", "panel", "size_class", "arm", "noprev", "nosweep", "slot", "day", "empty"})
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


def joint_sha(h11: str | None, hbase: str | None) -> str:
    """16 hex digits identifying the reader code: the unit-building module together with the vendored base (the registered pins feed the same function)."""
    return hashlib.sha256((str(h11) + str(hbase)).encode("utf-8")).hexdigest()[:16]


def reader_sha() -> str:
    h = code_hashes()
    return joint_sha(h["live_tests11.py"], h["live_tests11_base.py"])


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
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category", "end_date": str, "closed": str,
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
            "kind": kind, "condition_id": j["condition_id"].astype(str).to_numpy(object), "fee_rate": j["fee_rate"].to_numpy(float), "fee_exp": j["fee_exp"].to_numpy(float)}


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
                      "bid_k": j["bid"].to_numpy(float), "ask_k": j["ask"].to_numpy(float), "fee_cat": j["fee_cat"].to_numpy(object)})
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
        cnt["candidates"] = len(u)
        u = b._drop_missing(u, cnt, {"log_rv24s": "rv24_undefined"})
        bad = (u["rew"].to_numpy(float) == 1.0) & ~np.isfinite(u["v_c"].to_numpy(float))  # a rewarded unit needs the carry source's band v (excluded, counted)
        cnt["band_missing"] = int(bad.sum())
        u = u[~bad].reset_index(drop=True)
        cnt["reward_status_nan"] = int((~np.isfinite(u["rew"].to_numpy(float))).sum())  # kept in the lines (rew NaN), excluded by every consumer and counted
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
            ak, ap = gk["ask"].to_numpy(float), gp["ask"].to_numpy(float)
            if np.all((ak > 0) & (ak < 1 - 1e-12) & (ap > 0) & (ap < 1 - 1e-12)):  # E005's zero-bid form (a sensitivity): an ask is still required
                cnt["zero_bid_added_pairs"] += 1
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
    # 7: the completeness and receipt-span gate inputs (non-augmented events of 3-10 eligible members at k in the primary category)
    spans = []
    for r in pairs.values():
        if r["reason"] == "category" or r["augmented"] or r["arm"] != "primary":
            continue
        sc_ = r["size_class"]
        cnt["comp_den"] = cnt.get("comp_den", 0) + r["n_k"]
        cnt[f"comp_den_{sc_}"] = cnt.get(f"comp_den_{sc_}", 0) + r["n_k"]
        if r["reason"] in ("ok", "receipt_span"):
            cnt["comp_num"] = cnt.get("comp_num", 0) + r["n_k"]
            cnt[f"comp_num_{sc_}"] = cnt.get(f"comp_num_{sc_}", 0) + r["n_k"]
            cnt["pair_complete_events"] = cnt.get("pair_complete_events", 0) + 1
            cnt["pair_complete_rows"] = cnt.get("pair_complete_rows", 0) + r["n_k"]
            spans.append(max(r["span_k"], r["span_p"]))
            if r["reason"] == "ok":
                cnt["span_ok_events"] = cnt.get("span_ok_events", 0) + 1
                cnt["span_ok_rows"] = cnt.get("span_ok_rows", 0) + r["n_k"]
    cnt["_spans"] = spans
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


# --- the lag-slot loaders (7): twins are readings of captures k + 2 and k + 3 and return the twin term ONLY --------------------------------


LAG_CAPTURE_COLUMNS = ("market_id", "best_bid", "best_ask", "spread", "closed", "active", "binary")  # CH234 / CH232: reduced to the defined mid INSIDE the loader


def _lag_mid(cap_dir: Path, spec: dict) -> pd.Series:
    """The defined mid (4.2: open, active, binary, two-sided with ``ask < 1``, tight) by market of one later capture, from the columns of
    ``LAG_CAPTURE_COLUMNS`` only; NaN elsewhere. Internal to the loaders: no mid leaves this module through a census code path."""
    r = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(LAG_CAPTURE_COLUMNS), dtype={"market_id": str, "closed": str, "active": str})
    for c in LAG_CAPTURE_COLUMNS:
        if c not in r:
            r[c] = np.nan
    r = r.drop_duplicates("market_id").set_index("market_id")
    bid, ask = r["best_bid"].to_numpy(float), r["best_ask"].to_numpy(float)
    spread = np.where(np.isfinite(r["spread"].to_numpy(float)), r["spread"].to_numpy(float), ask - bid)
    with np.errstate(invalid="ignore"):
        ok = (r["binary"].to_numpy(float) == 1) & ~b._truthy(r["closed"]) & b._truthy(r["active"]) & (bid > 0) & (ask < 1.0 - 1e-12) & (bid < ask) & _tight(bid, ask, spread, spec)
    return pd.Series(np.where(ok, (bid + ask) / 2.0, np.nan), index=r.index)


def twin_components_xw(dir_a: Path, dir_b: Path, markets, spec: dict) -> pd.DataFrame:
    """CH234's twin components (1.9): the market's move over (k + 2, k + 3], ``w' = 0.5 + sign(d') (p_{k+2} - 0.5)`` (0.5 where the move is 0) and the
    winsorised ``|d'|``, for every market with a defined mid at both captures. READER-side reading; the census goes through :func:`lag_twin_xw`."""
    mk = pd.Index(np.asarray(markets, dtype=str))
    ma, mb = _lag_mid(dir_a, spec).reindex(mk).to_numpy(float), _lag_mid(dir_b, spec).reindex(mk).to_numpy(float)
    d = mb - ma
    absd, _ = winsorise_absd(d)
    return pd.DataFrame({"w_tw": collateral_weight(d, ma), "absd_tw": absd, "tw_ok": np.isfinite(d).astype(int)}, index=mk)


def lag_twin_xw(dir_a: Path, dir_b: Path, markets, cf: dict, spec: dict) -> pd.Series:
    """The CENSUS lag-slot loader of CH234 (7): receives keys and the census-fixed centres / scales and returns ONLY the twin term ``xw'`` =
    ``z(w') z(|d'|)`` (NaN unless both later mids are defined); no later mid, bid, ask or volume reaches the caller."""
    c = twin_components_xw(dir_a, dir_b, markets, spec)
    return pd.Series(zcentre(c["w_tw"].to_numpy(float), cf["w_centre"], cf["w_scale"]) * zcentre(c["absd_tw"].to_numpy(float), cf["absd_centre"], cf["absd_scale"]), index=c.index, name="xw_tw")


def twin_flag_xo(dir_a: Path, dir_b: Path, markets, spec: dict) -> pd.Series:
    """CH232's twin (1.9, R1 must-fix 3): ``xo_twin = 1[m_{k+2} in B and m_{k+3} outside B]``, 0 otherwise, NaN only if either mid is undefined; no
    approach-zone, first-of-day or ``|d|`` condition. Returns the flag only."""
    mk = pd.Index(np.asarray(markets, dtype=str))
    ma, mb = _lag_mid(dir_a, spec).reindex(mk).to_numpy(float), _lag_mid(dir_b, spec).reindex(mk).to_numpy(float)
    f = crossing(ma, mb, BAND, "out").astype(float)
    return pd.Series(np.where(np.isfinite(ma) & np.isfinite(mb), f, np.nan), index=mk, name="xo_tw")


def twin_components_cl(dir_a: Path, dir_b: Path, spec: dict) -> pd.DataFrame:
    """CH233's twin components: ``cl_sib`` over (k + 2, k + 3] (cents) on complete event-capture pairs with the 120 s receipt-span rule at k + 2 and
    k + 3 (the same :func:`event_pairs`), by market, with the size class of the pair at k + 3; no ``cl_sib`` of another pair is formed."""
    def mem(d: Path) -> pd.DataFrame:
        return members11_frame(load_rows11(d), load_ext11(d), spec)

    pairs, _ = event_pairs(mem(dir_a), mem(dir_b), spec)
    parts = []
    for r in pairs.values():
        if r["reason"] != "ok" or r["size_class"] == "1":
            continue
        ms = member_states(r)[["cl_sib"]].copy()
        ms["size_class"] = r["size_class"]
        parts.append(ms)
    if not parts:
        return pd.DataFrame({"cl_sib_tw": [], "size_class_tw": []}, index=pd.Index([], name="market_id"))
    return pd.concat(parts).rename(columns={"cl_sib": "cl_sib_tw", "size_class": "size_class_tw"})


def lag_twin_zcl(dir_a: Path, dir_b: Path, markets, cf: dict, spec: dict) -> pd.Series:
    """The CENSUS lag-slot loader of CH233: ONLY ``z cl_sib'`` of the twin pair (NaN where the member is in no complete pair of (k + 2, k + 3))."""
    c = twin_components_cl(dir_a, dir_b, spec)
    mk = pd.Index(np.asarray(markets, dtype=str))
    c = c.reindex(mk)
    return pd.Series(zcl_term(c["cl_sib_tw"].to_numpy(float), c["size_class_tw"].to_numpy(object), cf), index=mk, name="zcl_tw")


# --- outcomes (targets) and the reader (1.3, 1.5) -------------------------------------------------------------------------------------------


def _look(ser: pd.DataFrame | None, mids, col: str) -> np.ndarray:
    if ser is None:
        return np.full(len(mids), np.nan)
    return ser[col].reindex(pd.Index(np.asarray(mids, dtype=str))).to_numpy(float)


def outcome_h11(mids, by_slot: dict, j: int, root: Path, missing: bool) -> pd.DataFrame:
    """The status (1.5) and the quote of each unit's market at slot ``j``: ``two_sided`` units carry bid, ask, the spread (``ask - bid``) and the row receipt."""
    cap = by_slot.get(j)
    ser = None if missing else read_series11(root, cap["id"])
    st = None if missing else read_status11(root, cap["id"])
    out = pd.DataFrame({"market_id": np.asarray(mids, dtype=str)})
    out["status"] = status_codes(ser, st, mids, missing)
    out["bid"], out["ask"], out["t_row"] = _look(ser, mids, "bid"), _look(ser, mids, "ask"), _look(ser, mids, "t_row")
    out["spread"] = out["ask"] - out["bid"]
    out["cap_start"] = np.nan if missing else cap["start"]
    out["cap_id"] = None if missing else cap["id"]
    return out


def read_sweep(root: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(root) / "sweeps" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str}).drop_duplicates("market_id").set_index("market_id")


def outcome_s11(mids, sw: pd.DataFrame | None, missing: bool) -> pd.DataFrame:
    """CH232's M3 reading (post-decision, 1.3): sweep 1's outcome-0 quote and the 1c / 5c depths of each unit's market at one pass."""
    out = pd.DataFrame({"market_id": np.asarray(mids, dtype=str)})
    cols = ("sbid", "sask", "dbid1", "dask1", "dbid5", "dask5", "s_t")
    if missing or sw is None:
        out["status"] = "capture_missing" if missing else "absent"
        for c in cols:
            out[c] = np.nan
        return out
    two = _look(sw, mids, "s_two")
    out["status"] = np.where(two == 1, "two_sided", np.where(np.isfinite(two), "one_sided", "absent"))
    for c in cols:
        out[c] = _look(sw, mids, c)
    return out


def sweep_state(by_slot: dict, sweeps: dict, j: int, root: Path, now: float, spec: dict) -> str:
    ts = target_state(by_slot, j, now, spec)
    if ts != "ready":
        return ts
    cid = by_slot[j]["id"]
    if (Path(root) / "sweeps" / f"{cid}.csv.gz").exists():
        return "ready"
    if cid in sweeps:
        return "pending"
    return "missing" if now > b.slot_time(j, spec) + MISSING_AFTER_S else "pending"


def enabled_kinds(spec: dict) -> dict[str, bool]:
    """A kind is collected only if its test is in ``k_tests`` (1.12); null ``k_tests`` (DRAFT) collects every kind (development only)."""
    ks = spec.get("k_tests")
    return {KINDS[t]: (ks is None or t in ks) for t in TESTS}


BUILDERS = {"dollarw": ch234_units, "nrslack": ch233_units, "bandside": ch232_units}
FROZEN_MARKERS = (*MARKERS, ".empty.csv.gz")


def _marker(p: Path, suffix: str) -> Path:
    return p.with_name(p.name.replace(".csv.gz", suffix))


def run_once(*, snapshot_root: Path = SNAPSHOT_ROOT, sweep_root: Path = SWEEP_ROOT, root: Path = OUT_ROOT, spec: dict | None = None, now: float | None = None,
             max_items: int = 80, allow_late: bool = False, series_only: bool = False, window_start_utc: str | None = None) -> dict:
    """Series, freezes, due outcomes and due twins for everything new. Idempotent (write-once). ``allow_late`` is for DRY RUNS on past captures with an
    unpinned spec only (L6). ``series_only`` is ``backfill-series``: only the look-back series files before the window. An internal run lock (L15)."""
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
        return _run_locked(snapshot_root=snapshot_root, sweep_root=sweep_root, root=root, spec=spec, now=now, max_items=max_items, allow_late=allow_late,
                           series_only=series_only, window_start_utc=window_start_utc)


def _run_locked(*, snapshot_root: Path, sweep_root: Path, root: Path, spec: dict, now: float | None, max_items: int, allow_late: bool, series_only: bool,
                window_start_utc: str | None) -> dict:
    now = now_ts() if now is None else now
    commit = git_commit()
    stats = {"run_utc": iso(now), "code_commit": commit, "spec_sha": spec["_sha256"][:16], "pinned": spec["_pinned"], "written": 0, "series": 0, "sweeps": 0, "outcomes": 0,
             "twins": 0, "refused_late": 0, **{k_: 0 for k_ in KINDS.values()}}
    if root.exists() and dir_bytes(root) > DISK_CAP_BYTES:
        stats["status"] = "disk_cap"
        append_jsonl(root / "passes.jsonl", [{"kind": "disk_cap", **stats}])
        return stats
    t_reg, t_end = epoch(spec["registered_utc"]), epoch(spec["end_utc"])
    kinds = enabled_kinds(spec)
    stats["kinds_off"] = sorted(n for n, on in kinds.items() if not on)
    st = b.State(root)
    by_slot = b.scan_captures(snapshot_root, st, spec)
    sweeps = b.scan_sweeps(sweep_root, st) if (kinds["bandside"] and Path(sweep_root).exists()) else {}
    st.save()
    log: list[dict] = []
    budget = max_items
    lo = (epoch(window_start_utc) if window_start_utc else t_reg) - 14 * GRID_S
    hi = t_end + 4 * GRID_S + b.SLOT_TOL_S
    # 1. series / status / rw / members for captures in [window start - 28 h, end + 4 slots); sweep-1 files of CH232's passes
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (lo <= c["start"] < hi) or budget <= 0:
            continue
        if not series_ready(root, {k: c}, (k,)):
            info = write_series11(root, c, spec)
            if info.get("written"):
                stats["series"] += 1
                budget -= 1
                log.append({"kind": "series", "id": c["id"], "slot": k, **info, "written_utc": iso(now_ts())})
        p = root / "sweeps" / f"{c['id']}.csv.gz"
        if kinds["bandside"] and c["id"] in sweeps and not p.exists() and budget > 0:
            if write_once_csv(p, b.sweep_frame(sweeps[c["id"]]["dir"], c["dir"])):
                stats["sweeps"] += 1
                budget -= 1
                log.append({"kind": "sweep", "id": c["id"], "sweep_id": sweeps[c["id"]]["id"], "written_utc": iso(now_ts())})
    if series_only:
        stats["status"] = "wrote" if stats["series"] else "nothing_new"
        stats["written"] = stats["series"] + stats["sweeps"]
        for r in log:
            r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
        append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
        return stats
    store = SlotStore(root, by_slot, spec, cache_slots=24)
    # 2. freezes: each kind's unit lines of origin k in [REGISTERED_UTC, END_UTC), refused (.late) once capture k + 1 may have started
    for k in sorted(by_slot):
        c = by_slot[k]
        if not (t_reg <= c["start"] < t_end):
            continue
        role = role_of(c["start"], spec["registered_utc"], spec["end_utc"], spec["_pinned"])
        for test in TESTS:
            kind = KINDS[test]
            p = root / kind / "frozen" / f"{c['id']}.csv.gz"
            if not kinds[kind] or p.exists() or any(_marker(p, s_).exists() for s_ in FROZEN_MARKERS) or budget <= 0:
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
            if not series_ready(root, by_slot, range(k - 12, k + 1)):
                continue
            units, cnt = BUILDERS[kind](store, k, spec, role, commit)
            cnt = {k_: v_ for k_, v_ in cnt.items() if not k_.startswith("_")}  # census-only lists stay out of the log
            if units.empty:
                write_once_csv(_marker(p, ".empty.csv.gz"), pd.DataFrame({"slot": [k], "empty": [1], "role": [role]}))
                log.append({"kind": f"{kind}_empty", "id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
                continue
            if write_once_csv(p, units):
                stats[kind] += 1
                budget -= 1
                log.append({"kind": f"{kind}_frozen", "id": c["id"], "slot": k, "counts": cnt, "written_utc": iso(now_ts())})
    # 3. outcomes (status and quote at k + 1, k + 2; CH232's sweep passes k and k + 1) and twins (captures k + 2, k + 3)
    for kind, on in ((n, on_) for n, on_ in kinds.items()):
        if not on:
            continue
        fdir = root / kind / "frozen"
        for p in sorted(fdir.glob("*.csv.gz")) if fdir.exists() else []:
            if p.name.endswith(FROZEN_MARKERS) or budget <= 0:
                continue
            fid = p.name[:-7]
            fr = pd.read_csv(p, usecols=["market_id", "slot"], dtype={"market_id": str})
            if fr.empty:
                continue
            k = int(fr["slot"].iloc[0])
            mids = pd.unique(fr["market_id"].to_numpy())
            todo = [("h", h) for h in (1, 2) if not (root / kind / "outcomes" / f"{fid}.h{h}.csv.gz").exists()]
            if kind == "bandside":
                todo += [("s", s_) for s_ in (0, 1) if not (root / kind / "outcomes" / f"{fid}.s{s_}.csv.gz").exists()]
            for typ, h in todo:
                if budget <= 0:
                    break
                j = k + h
                state = target_state(by_slot, j, now, spec) if typ == "h" else sweep_state(by_slot, sweeps, j, root, now, spec)
                if state == "pending" or (typ == "h" and state == "ready" and not series_ready(root, by_slot, (j,))):
                    continue
                out = outcome_h11(mids, by_slot, j, root, state == "missing") if typ == "h" else outcome_s11(mids, None if state == "missing" else read_sweep(root, by_slot[j]["id"]), state == "missing")
                if write_once_csv(root / kind / "outcomes" / f"{fid}.{typ}{h}.csv.gz", out):
                    stats["outcomes"] += 1
                    budget -= 1
                    log.append({"kind": f"{kind}_outcome", "id": fid, "tag": f"{typ}{h}", "target_slot": j, "target": state, "rows": len(out), "written_utc": iso(now_ts())})
            tp = root / kind / "twins" / f"{fid}.csv.gz"
            if tp.exists() or budget <= 0:
                continue
            sa, sb = target_state(by_slot, k + 2, now, spec), target_state(by_slot, k + 3, now, spec)
            if "pending" in (sa, sb):
                continue
            out = twin_frame(kind, mids, by_slot, k, sa == "ready" and sb == "ready", spec)
            if write_once_csv(tp, out):
                stats["twins"] += 1
                budget -= 1
                log.append({"kind": f"{kind}_twins", "id": fid, "rows": len(out), "both_ready": bool(sa == "ready" and sb == "ready"), "written_utc": iso(now_ts())})
    stats["written"] = sum(stats[k_] for k_ in ("series", "sweeps", "outcomes", "twins", *KINDS.values()))
    stats["status"] = "wrote" if stats["written"] else "nothing_new"
    for r in log:
        r.update(code_commit=commit, spec_sha=spec["_sha256"][:16])
    append_jsonl(root / "passes.jsonl", log + [{"kind": "run", **stats}])
    return stats


def twin_frame(kind: str, mids, by_slot: dict, k: int, both_ready: bool, spec: dict) -> pd.DataFrame:
    """The far-future twin readings of one frozen file (1.9): written once, after captures k + 2 and k + 3 exist (NaN, ``tw_ok`` 0 when either is missing)."""
    mk = pd.Index(np.asarray(mids, dtype=str), name="market_id")
    if not both_ready:
        return pd.DataFrame({"market_id": mk, "tw_ok": 0})
    da, db = by_slot[k + 2]["dir"], by_slot[k + 3]["dir"]
    cf = (spec.get("census_fixed") or {}).get({v: k_ for k_, v in KINDS.items()}[kind]) or {}
    if kind == "dollarw":
        c = twin_components_xw(da, db, mk, spec)
        xw = xw_term(c["w_tw"].to_numpy(float), c["absd_tw"].to_numpy(float), cf)
        return pd.DataFrame({"market_id": mk, "tw_ok": c["tw_ok"].to_numpy(), "w_tw": c["w_tw"].to_numpy(), "absd_tw": c["absd_tw"].to_numpy(), "xw_tw": xw})
    if kind == "bandside":
        f = twin_flag_xo(da, db, mk, spec)
        return pd.DataFrame({"market_id": mk, "tw_ok": np.isfinite(f.to_numpy()).astype(int), "xo_tw": f.to_numpy()})
    c = twin_components_cl(da, db, spec).reindex(mk)
    z = zcl_term(c["cl_sib_tw"].to_numpy(float), c["size_class_tw"].to_numpy(object), cf)
    return pd.DataFrame({"market_id": mk, "tw_ok": np.isfinite(c["cl_sib_tw"].to_numpy(float)).astype(int), "cl_sib_tw": c["cl_sib_tw"].to_numpy(float), "zcl_tw": z})


# --- operational counts (never reads a price, a spread, a volume, a depth or a target) --------------------------------------------------------


def _read_ops(path: Path, cols: list[str]) -> pd.DataFrame:
    bad = [c for c in cols if c not in OPS_COLS]
    if bad:
        raise ValueError(f"ops_stats may not read {bad}")
    head = pd.read_csv(path, nrows=0).columns
    use = [c for c in cols if c in head]
    return pd.read_csv(path, usecols=use) if use else pd.DataFrame()


def ops_stats(root: Path = OUT_ROOT) -> dict:
    root = Path(root)
    out: dict = {"root": str(root), "bytes": dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "members", "sweeps", *(f"{k}/frozen" for k in KINDS.values()), *(f"{k}/outcomes" for k in KINDS.values()), *(f"{k}/twins" for k in KINDS.values())):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith(FROZEN_MARKERS)]), **{s_.split(".")[1]: len([f for f in files if f.name.endswith(s_)]) for s_ in FROZEN_MARKERS}}
    counts, status = {}, {}
    cols = {"dollarw": ["role", "kind", "sports", "in_scope", "vclass"], "nrslack": ["role", "kind", "sports", "arm", "size_class"], "bandside": ["role", "kind", "sports", "arm"]}
    for kind, cl in cols.items():
        d = root / kind / "frozen"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            if f.name.endswith(FROZEN_MARKERS):
                continue
            s_ = _read_ops(f, [c for c in cl if c in OPS_COLS])
            for c in s_.columns:
                for kk, v in s_[c].value_counts().items():
                    counts[f"{kind}:{c}:{kk}"] = counts.get(f"{kind}:{c}:{kk}", 0) + int(v)
        d = root / kind / "outcomes"
        for f in sorted(d.glob("*.csv.gz")) if d.exists() else []:
            tag = f.name[:-7].rsplit(".", 1)[-1]
            s_ = _read_ops(f, ["status"])
            for kk, v in s_["status"].value_counts().items():
                status[f"{kind}:{tag}:{kk}"] = status.get(f"{kind}:{tag}:{kk}", 0) + int(v)
    out.update(line_counts=counts, outcome_status_counts=status)
    return out


# --- the model columns (1.7, 2.4, 3.3, 4.3) ---------------------------------------------------------------------------------------------


SD_DUMMIES = [f"sd{s_}" for s_ in range(1, 12)]
K_COMMON = ["p_k", "spread_c", "log1p_liq", "log1p_vol", "vol_missing", "log_hte", "hte_unknown", "tick001", "log_rv24s", "neg_risk", "rewarded", "own6", "own24", "chg1h", "mom_missing",
            "chg1d", "chg1d_missing", "chg1w", "chg1w_missing", *SD_DUMMIES]  # the known-factor block K (1.7); chg1d / chg1w exist only when the header pre-check found them
CONTROLS = {
    "CH234": ["absd", *(f"sb{i}" for i in range(4)), *(f"sb{i}_lvl" for i in range(4)), "n_members", *K_COMMON],
    "CH233": ["hb_km1", "own_dbid_c", "own_dspread_c", "bid_share", "overround", "n_elig", "nr_other", "d", *[c for c in K_COMMON if c not in ("neg_risk", "rewarded")], "rewarded"],
    "CH232": ["xr", "d_tow", "absd", "dist", "upper", "spread_k_c", "dspread_c", "S2", "S3", "S4p", "dSm2p", "dSm1", "dSp1", "dSp2p", "v_c", "log_rate", "n_members", *K_COMMON],
}


def fee_dummies(df: pd.DataFrame, min_share: float = 0.005) -> tuple[pd.DataFrame, list[str]]:
    """1.7: the non-sports ``fee_category`` dummies of the block K (LT11 ambiguity A9: the set is not fixed by the design; here every category holding at least
    0.5% of the frame's units except the most frequent one, which is the reference). Returns the frame with ``fc_<category>`` columns and their names."""
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
    """The control columns of one test that exist in ``df`` (the optional chg1d / chg1w pairs follow the pre-check) plus the fee-category dummies present."""
    base = [c for c in CONTROLS[test] if c in df.columns]
    return [*base, *[c for c in df.columns if c.startswith("fc_")], *(extra or [])]


# --- census helpers (7) ------------------------------------------------------------------------------------------------------------------


def _scale(days: float) -> float:
    return 21.0 / days if days and math.isfinite(days) and days > 0 else float("nan")


def g_eff(ev) -> float:
    """Kish effective event count ``(sum m_e)^2 / sum m_e^2`` (1.7, R1 should-fix 8)."""
    m = pd.Series(np.asarray(ev, dtype=object)).value_counts().to_numpy(float)
    return float(m.sum() ** 2 / (m**2).sum()) if len(m) else float("nan")


def f_mde_gate(mde_c: float, r_gate: float, design_c: float) -> dict:
    """7's F-MDE: ``max(design-based MDE of Delta in the arm model, MDE x sqrt(2 / (1 - max(0, r_gate))))`` (cents); NaN anywhere gives inf."""
    if not (np.isfinite(mde_c) and np.isfinite(r_gate) and r_gate < 1.0):
        return {"declared_c": float("inf"), "design_c": design_c, "f_mde_c": float("inf"), "r_gate": r_gate}
    dec = mde_c * math.sqrt(2.0 / (1.0 - max(0.0, r_gate)))
    return {"declared_c": dec, "design_c": design_c, "f_mde_c": float(max(dec, design_c)) if np.isfinite(design_c) else float("inf"), "r_gate": r_gate}


def r_gate11(U: pd.DataFrame, lead: str, twin: str, min_units: int) -> dict:
    """7: ``r_gate = max(r_w, r_pool)`` of the lead and the twin on census units with both; ``r_w`` within-market on expanding-past demeaned values over
    markets with at least ``min_units`` such units (the vendored ``wcorr``), ``r_pool`` pooled; NaN unless both are finite."""
    if U.empty or twin not in U or lead not in U:
        return {"r_w": float("nan"), "r_pool": float("nan"), "r_gate": float("nan"), "n": 0, "markets": 0}
    X = U[["market_id", "t_row", lead, twin]].replace([np.inf, -np.inf], np.nan).dropna()
    X = X[X.groupby("market_id")["market_id"].transform("size") >= min_units]
    r = b.wcorr(X, lead, twin) if len(X) else {"within": None, "pooled": None, "n": 0}
    rw = float(r["within"]) if r["within"] is not None else float("nan")
    rp = float(r["pooled"]) if r["pooled"] is not None else float("nan")
    return {"r_w": rw, "r_pool": rp, "r_gate": float(max(rw, rp)) if np.isfinite(rw) and np.isfinite(rp) else float("nan"), "n": int(r.get("n", 0)), "markets": int(X["market_id"].nunique())}


def slope_mde11(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float, gap: float) -> dict:
    """The slope MDE (cents) for a change of the tested term equal to ``gap`` (the census tercile gap): ``max(declared, design)``. Declared = ``t_sum x SD /
    sqrt(n_eff) x sqrt(DE_gate) x day x sqrt(max(1, VIF_w)) / SD(term) x gap`` at the census effective counts (markets with >= 2 units, projected); design =
    ``t_sum x day x SD x se_1 x gap`` (:func:`b.design_se`). NaN anywhere gives inf."""
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    pe = pop[eff] if len(pop) else pop
    dsg = b.design_ss(pe, term, controls) if len(pop) else {"n": 0, "ss_resid": float("nan"), "vif_w": float("nan")}
    n_eff = float(eff.sum()) * scale
    sd_t = float(np.nanstd(pe[term].to_numpy(float), ddof=1)) if len(pe) > 1 else float("nan")
    per_sd = b.mde_slope_declared(n_eff, sd, de_gate, a, dsg["vif_w"])
    declared = per_sd / sd_t * gap * 100.0 if np.isfinite(per_sd) and np.isfinite(sd_t) and sd_t > 0 and np.isfinite(gap) else float("inf")
    se = b.design_se(pe, [term], controls, {term: 1.0}, float(a["de_rho"]), scale) if len(pe) else float("nan")
    design = a["t_sum"] * a["day_factor"] * sd * se * gap * 100.0 if np.isfinite(se) and np.isfinite(gap) else float("inf")
    return {"design_ss": dsg, "n_eff_projected": n_eff, "sd_term": sd_t, "declared_c": declared, "design_c": design, "se_1": se, "mde_c": float(max(declared, design)) if np.isfinite(declared) else float("inf")}


def class_mde11(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float) -> dict:
    """CH232's class-contrast MDE (cents), ``max(declared, design)`` (the vendored :func:`b.class_mde8`)."""
    return b.class_mde8(pop, term, controls, scale, a, de_gate, sd)


def f_design_c(F: pd.DataFrame, term: str, twin: str, controls: list[str], scale_f: float, a: dict, sd: float, gap: float | None) -> float:
    """The design-based MDE (cents) of ``Delta = beta(lead) - beta(twin)`` in the arm model on the units with both (``gap`` None: a class contrast, gap 1)."""
    if F.empty:
        return float("inf")
    Fe = F[b._eff(F)]
    se = b.design_se(Fe, [term, twin], controls, {term: 1.0, twin: -1.0}, float(a["de_rho"]), scale_f) if len(Fe) else float("nan")
    g_ = 1.0 if gap is None else gap
    return a["t_sum"] * a["day_factor"] * sd * se * g_ * 100.0 if np.isfinite(se) and np.isfinite(g_) else float("inf")


def _gate_block(res: dict, gate: dict, name: str) -> dict:
    res[name] = b._gate(gate)
    res["status"] = "census_pass" if res[name]["pass"] else "census_dropped"
    return res


def _nan_gate(res: dict, name: str, why: str) -> dict:
    g = res.get(name, {})
    res[name] = {**{k_: False for k_ in g if k_ != "pass"}, why: False, "pass": False, "values_nan": True}
    res["status"] = "census_dropped"
    return res


def _add_twin(U: pd.DataFrame, kind: str, by_slot: dict, cf: dict, spec: dict, cache: dict | None = None) -> pd.DataFrame:
    """The census lag-slot loader step (7): for each origin slot group, the twin term of captures k + 2 and k + 3 ONLY (never a mid, a quote or a volume)."""
    col = {"dollarw": "xw_tw", "nrslack": "zcl_tw", "bandside": "xo_tw"}[kind]
    out = U.copy()
    out[col] = np.nan
    if U.empty:
        return out
    for k, grp in U.groupby("slot"):
        k = int(k)
        if (k + 2) in by_slot and (k + 3) in by_slot:
            da, db = by_slot[k + 2]["dir"], by_slot[k + 3]["dir"]
            mk = grp["market_id"].astype(str).to_numpy()
            key = (kind, k, hash(tuple(mk)), tuple(sorted((a_, round(float(v_), 12)) for a_, v_ in (cf.get("s_c") or {}).items())) if kind == "nrslack" else tuple(sorted((a_, round(float(v_), 12)) for a_, v_ in cf.items())))
            if cache is not None and key in cache:
                tw = cache[key]
            else:
                if kind == "dollarw":
                    tw = lag_twin_xw(da, db, mk, cf, spec)
                elif kind == "nrslack":
                    tw = lag_twin_zcl(da, db, mk, cf, spec)
                else:
                    tw = twin_flag_xo(da, db, mk, spec)
                if cache is not None:
                    cache[key] = tw
            out.loc[grp.index, col] = tw.reindex(pd.Index(mk)).to_numpy(float)
    return out


def _slot_share(df: pd.DataFrame) -> float:
    s_ = (df["slot"].to_numpy(int) % 12)
    return float(pd.Series(s_).value_counts().iloc[0] / len(s_)) if len(s_) else float("nan")


# --- CH234's census gate block (7 table, row 1) -----------------------------------------------------------------------------------------


def census_ch234(U: pd.DataFrame, tot: dict, spec: dict, covered_days: float, twin_days: float, n_origins: int, by_slot: dict, twin_cache: dict | None = None) -> dict:
    """CH234's gates. ``U`` = all units of the census origins (``in_scope`` 0 = the sports arm, ``ladder`` 1 = the ladder arm, ``vclass``). Every gate is
    computed here, after the coverage check has passed (the caller returns before this function otherwise)."""
    g, a = spec["census_gates"]["CH234"], b.mde_common(spec)
    scale, scale_f = _scale(covered_days), _scale(twin_days)
    res: dict = {"covered_days": covered_days, "twin_days": twin_days, "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    if U.empty:
        res["gate_CH234"] = {"units": False, "pass": False, "no_units": True}
        res["status"] = "census_dropped"
        return res
    P0 = U[U["in_scope"] == 1]
    Pm = P0[P0["ladder"] == 0].copy()
    T0 = P0[P0["vclass"] == "traded"]
    cap_share = float((T0["ladder"] == 0).mean()) if len(T0) else float("nan")
    Tm = Pm[Pm["vclass"] == "traded"]
    T, excl, top = b._fam(Tm, a["family_cap"])
    T = T.copy()
    Q = Pm[(Pm["vclass"] == "quote_only")]
    Q = (Q[Q["skey"].astype(str) != excl] if excl else Q).copy()
    wc, ws = b.standardise(T["w"])
    dc, ds_ = b.standardise(T["absd"])
    cf = {"w_centre": wc, "w_scale": ws, "absd_centre": dc, "absd_scale": ds_}
    for df_ in (T, Q, Pm):
        df_["xw"] = xw_term(df_["w"].to_numpy(float), df_["absd"].to_numpy(float), cf)
    T, fc_names = fee_dummies(T)
    controls = controls_for("CH234", T)
    t1, t2, gap = b.terciles(T["xw"])
    de = b._de(T, scale, g["de_floor"], a)
    unk = ~Pm["vclass"].isin(["traded", "quote_only"]).to_numpy()
    Pm["unk"] = unk.astype(float)
    unk_share = float(unk.mean()) if len(Pm) else float("nan")
    per_slot = Pm.assign(_u=unk).groupby("slot")["_u"].mean()
    unk_cap_frac = float((per_slot > g["unknown_capture_cut"]).sum() / n_origins) if n_origins else float("nan")
    corr_u = {"unk:xw": b.wcorr(Pm, "unk", "xw"), "unk:w": b.wcorr(Pm, "unk", "w")}
    md = T.groupby(["market_id", "day"])["w"].agg(["size", "std"])
    md = md[md["size"] >= g["w_sd_min_moves"]]
    w_sd_share = float((md["std"] >= g["w_sd_min"]).mean()) if len(md) else float("nan")
    ri = b.resid_iqr(T, "xw", [c for c in controls if c in T], int(g["resid_iqr_min_units"]), g["resid_iqr_min"])
    Te = T[b._eff(T)] if len(T) else T
    dsg = b.design_ss(Te, "xw", controls) if len(Te) else {"vif_w": float("nan")}
    corr_x = {x: b.wcorr(T, "xw", x) for x in ("log1p_liq", "log_rv24s", "d", "spread_c")}
    bm = b.block_min_units(covered_days)
    bs = b.block_share(T, bm)
    cfx = {"w_centre": wc, "w_scale": ws, "absd_centre": dc, "absd_scale": ds_}
    TW = _add_twin(T, "dollarw", by_slot, cfx, spec, twin_cache)
    F = TW[(TW["f_end_ok"] == 1) & np.isfinite(TW["xw_tw"].to_numpy(float))]
    rg = r_gate11(F, "xw", "xw_tw", int(g["pair_min_per_market"]))
    sm = slope_mde11(T, "xw", controls, scale, a, de["DE_gate"], a[g["sd"]], gap)
    fm = f_mde_gate(sm["mde_c"], rg["r_gate"], f_design_c(F, "xw", "xw_tw", controls, scale_f, a, a[g["sd"]], gap))
    proj_t, proj_q = float(len(T) * scale), float(len(Q) * scale)
    ev_n = int(T["event_id"].nunique()) if len(T) else 0
    ge = g_eff(T["event_id"]) if len(T) else float("nan")
    res.update({"traded_units_projected_21d": proj_t, "quote_only_units_projected_21d": proj_q, "unknown_share": unk_share, "unknown_capture_frac": unk_cap_frac, "corr_unknown": corr_u,
                "distinct_events_unprojected": ev_n, "g_event": ev_n, "g_eff": ge, "cap_share": cap_share, "exclude_family": excl, "top_family_share": top, "design_effect": de,
                "w_sd_share": w_sd_share, "mover_market_days_ge2": int(len(md)), "resid_iqr": ri, "vif_w": dsg["vif_w"], "corr_x": corr_x, "venue_clock": _slot_share(T) if len(T) else float("nan"),
                "block_min_units": bm, "block_share": bs, "r_gate": rg, "slope": sm, "F": fm, "xw": {"terciles": [t1, t2], "gap": gap, "centre_scale": cfx}, "fee_dummies": fc_names,
                "sports_arm_units": int((U["in_scope"] == 0).sum()), "ladder_arm_units": int((P0["ladder"] == 1).sum()),
                "class_counts": {k_: int(v_) for k_, v_ in P0[P0["ladder"] == 0]["vclass"].value_counts().items()},
                "unknown_subclasses_by_km1_capture": {k_: int(v_) for k_, v_ in Pm[unk]["vclass"].value_counts().items()},
                "by_bin": {str(i): {c_: int(((Pm["bin"] == i) & (Pm["vclass"] == c_)).sum()) for c_ in ("traded", "quote_only")} for i in range(4)},
                "winsorised_share": float(T["absd_wins"].mean()) if len(T) else float("nan"), "w_quantiles": b._q(T["w"]), "absd_quantiles": b._q(T["absd"]),
                "f_arm_units": int(len(F)), "events": b._events8(T.assign(day=T["day"]), scale, covered_days) if len(T) else {}, "per_market": b._per_market(T["market_id"]) if len(T) else {}})
    gate = {"traded_units": proj_t >= g["units_projected_min"], "quote_only_units": proj_q >= g["quote_only_projected_min"],
            "unknown_share": bool(np.isfinite(unk_share) and unk_share <= g["unknown_share_max"]), "unknown_captures": bool(np.isfinite(unk_cap_frac) and unk_cap_frac <= g["unknown_capture_frac_max"]),
            "corr_unknown_xw": b.corr_ok(corr_u["unk:xw"], g["unknown_corr_max"], both=True), "corr_unknown_w": b.corr_ok(corr_u["unk:w"], g["unknown_corr_max"], both=True),
            "distinct_events": ev_n >= g["distinct_events_min"], "g_eff": bool(np.isfinite(ge) and ge >= a["g_eff_min"]), "cap_share": bool(np.isfinite(cap_share) and cap_share >= g["cap_share_min"]),
            "w_sd": bool(np.isfinite(w_sd_share) and w_sd_share >= g["w_sd_share_min"]), "resid_iqr": b.iqr_ok(ri, g), "vif_w": bool(np.isfinite(dsg["vif_w"]) and dsg["vif_w"] <= g["vif_w_max"]),
            **{f"corr_xw_{x}": b.corr_ok(c_, g["corr_max"], both=True) for x, c_ in corr_x.items()},
            "venue_clock": bool(len(T) and _slot_share(T) <= g["venue_clock_max"]), "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]),
            "r_gate": bool(np.isfinite(rg["r_gate"]) and rg["r_gate"] <= g["r_gate_max"]), "slope_mde": bool(sm["mde_c"] <= a["mde_max_c"]["CH234"]), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max_c"]["CH234"])}
    res = _gate_block(res, gate, "gate_CH234")
    res["census_fixed"] = {"w_centre": wc, "w_scale": ws, "absd_centre": dc, "absd_scale": ds_, "xw_cuts": [t1, t2], "xw_gap": gap, "exclude_family": excl,
                           "q_unknown": max(unk_share, 0.15) if np.isfinite(unk_share) else None}
    return res


# --- CH233's census gate block (7 table, row 2) -----------------------------------------------------------------------------------------


def span_summary(spans) -> dict:
    """The receipt-span distribution of pair-complete event-capture pairs (7): quantiles q50 / q90 / q99 / max and the shares above 30, 60, 120 and 300 s."""
    v = np.asarray([x for x in spans if np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "q50": float(np.quantile(v, 0.5)), "q90": float(np.quantile(v, 0.9)), "q99": float(np.quantile(v, 0.99)), "max": float(v.max()),
            **{f"share_gt_{t}s": float((v > t).mean()) for t in (30, 60, 120, 300)}}


def census_ch233(U: pd.DataFrame, tot: dict, spans: list, spec: dict, covered_days: float, twin_days: float, by_slot: dict, twin_cache: dict | None = None) -> dict:
    """CH233's gates. ``U`` = all member units (``arm`` primary / size2 / ladder / augmented); ``tot`` the summed event-pair counts; ``spans`` the
    pair-complete pairs' larger receipt spans (seconds)."""
    g, a = spec["census_gates"]["CH233"], b.mde_common(spec)
    scale, scale_f = _scale(covered_days), _scale(twin_days)
    res: dict = {"covered_days": covered_days, "twin_days": twin_days, "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    den, num = tot.get("comp_den", 0), tot.get("comp_num", 0)
    completeness = num / den if den else float("nan")
    pc, so = tot.get("pair_complete_events", 0), tot.get("span_ok_events", 0)
    span_ok = so / pc if pc else float("nan")
    res.update({"completeness": completeness, "completeness_by_size": {sc_: (tot.get(f"comp_num_{sc_}", 0) / tot[f"comp_den_{sc_}"] if tot.get(f"comp_den_{sc_}") else float("nan")) for sc_ in ("3-5", "6-10")},
                "receipt_span_retention": span_ok, "receipt_span_row_share": (tot.get("span_ok_rows", 0) / tot["pair_complete_rows"] if tot.get("pair_complete_rows") else float("nan")),
                "receipt_span_distribution": span_summary(spans)})
    P0 = U[U["arm"] == "primary"] if len(U) else U
    if P0.empty:
        res["gate_CH233"] = {"units": False, "pass": False, "no_units": True}
        res["status"] = "census_dropped"
        return res
    P, excl, top = b._fam(P0, a["family_cap"])
    P = P.copy()
    s_c = {sc_: float(np.nanstd(P.loc[P["size_class"] == sc_, "cl_sib"].to_numpy(float), ddof=1)) if (P["size_class"] == sc_).sum() > 1 else float("nan") for sc_ in ("3-5", "6-10")}
    cfz = {"s_c": s_c}
    for df_ in (P, U):
        df_["zcl"] = zcl_term(df_["cl_sib"].to_numpy(float), df_["size_class"].to_numpy(object), cfz)
        df_["zca"] = zcl_term(df_["ca_sib"].to_numpy(float), df_["size_class"].to_numpy(object), cfz)
    P, fc_names = fee_dummies(P)
    controls = controls_for("CH233", P)
    t1, t2, gap = b.terciles(P["zcl"])
    de = b._de(P, scale, g["de_floor"], a)
    ev_units = P.groupby("event_id").size()
    ev_n = int(P["event_id"].nunique())
    ev48 = int((ev_units >= g["events_min_units"]).sum())
    ge = g_eff(P["event_id"])
    ecap = P.drop_duplicates(["event_id", "slot"])
    work_range = float(ecap["near_zero_k"].mean()) if len(ecap) else float("nan")
    big = P[P["event_id"].isin(ev_units[ev_units >= g["events_min_units"]].index)]
    sd_ev = big.groupby("event_id").apply(lambda d: float(np.nanstd(d["cl_sib"].to_numpy(float), ddof=1)) >= float(d["tick_e"].mean()) * 100.0 * g["event_sd_min_ticks"] - EPS, include_groups=False) if len(big) else pd.Series(dtype=bool)
    sd_share = float(sd_ev.mean()) if len(sd_ev) else float("nan")
    Pe = P[b._eff(P)]
    dsg = b.design_ss(Pe, "zcl", controls) if len(Pe) else {"vif_w": float("nan")}
    corr_x = {x: b.wcorr(P, "zcl", x) for x in ("d", "own_dbid_c", "own_dspread_c", "log1p_liq", "log_rv24s", "hb_km1")}
    zz = P[np.abs(P["zcl"].to_numpy(float)) >= 1.0]
    clock = _slot_share(zz) if len(zz) else float("nan")
    ncap = P.groupby("event_id")["slot"].nunique()
    bshare = float(P["event_id"].map(ncap).ge(g["block_min_captures"]).mean())
    cfx = {"s_c": s_c}
    TW = _add_twin(P, "nrslack", by_slot, cfx, spec, twin_cache)
    F = TW[(TW["f_end_ok"] == 1) & np.isfinite(TW["zcl_tw"].to_numpy(float))]
    rg = r_gate11(F, "zcl", "zcl_tw", int(g["pair_min_per_market"]))
    sm = slope_mde11(P, "zcl", controls, scale, a, de["DE_gate"], a[g["sd"]], gap)
    fm = f_mde_gate(sm["mde_c"], rg["r_gate"], f_design_c(F, "zcl", "zcl_tw", controls, scale_f, a, a[g["sd"]], gap))
    proj = float(len(P) * scale)
    both = P.dropna(subset=["zcl", "zca"])
    res.update({"primary_units_projected_21d": proj, "distinct_events_unprojected": ev_n, "events_ge48_units_unprojected": ev48, "g_eff": ge, "working_range_share": work_range,
                "event_sd_share": sd_share, "vif_w": dsg["vif_w"], "corr_x": corr_x, "venue_clock": clock, "block_share": bshare, "r_gate": rg, "slope": sm, "F": fm, "design_effect": de,
                "exclude_family": excl, "top_family_share": top, "s_c": s_c, "zcl": {"terciles": [t1, t2], "gap": gap}, "fee_dummies": fc_names,
                "arm_units": {k_: int(v_) for k_, v_ in U["arm"].value_counts().items()}, "hb_km1_quantiles": b._q(P["hb_km1"], (0.05, 0.5, 0.95)),
                "corr_zcl_zca": b.wcorr(both, "zcl", "zca") if len(both) else {}, "headroom_crossings": int(((P["hb_km1"] > 0) & (P["hb_k"] <= 0)).sum()),
                "rank_shares": {"favourite": float(P["fav"].mean())}, "f_arm_units": int(len(F)), "per_market": b._per_market(P["market_id"]),
                "events_proj": b._events8(P, scale, covered_days)})
    gate = {"completeness": bool(np.isfinite(completeness) and completeness >= g["completeness_min"]), "receipt_span": bool(np.isfinite(span_ok) and span_ok >= g["receipt_span_pairs_min"]),
            "units": proj >= g["units_projected_min"], "distinct_events": ev_n >= g["distinct_events_min"], "events_ge48": ev48 >= g["events_ge48_min"],
            "g_eff": bool(np.isfinite(ge) and ge >= a["g_eff_min"]), "working_range": bool(np.isfinite(work_range) and work_range >= g["working_range_min"]),
            "event_sd": bool(np.isfinite(sd_share) and sd_share >= g["event_sd_share_min"]), "vif_w": bool(np.isfinite(dsg["vif_w"]) and dsg["vif_w"] <= g["vif_w_max"]),
            **{f"corr_zcl_{x}": b.corr_ok(c_, g["corr_max"], both=True) for x, c_ in corr_x.items()},
            "venue_clock": bool(np.isfinite(clock) and clock <= g["venue_clock_max"]), "block_share": bool(np.isfinite(bshare) and bshare >= g["block_share_min"]),
            "r_gate": bool(np.isfinite(rg["r_gate"]) and rg["r_gate"] <= g["r_gate_max"]), "slope_mde": bool(sm["mde_c"] <= a["mde_max_c"]["CH233"]), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max_c"]["CH233"])}
    res = _gate_block(res, gate, "gate_CH233")
    res["census_fixed"] = {"s_c": s_c, "zcl_cuts": [t1, t2], "zcl_gap": gap, "exclude_family": excl}
    return res


# --- CH232's census gate block (7 table, row 3) -----------------------------------------------------------------------------------------


def band_unit_check(v_cents, spec: dict) -> dict:
    """7's band unit check: the median ``rewards_max_spread`` over carry-rewarded rows must lie in [0.5, 20] (cents), else every CH232 gate that uses ``v`` is NaN."""
    v = np.asarray(v_cents, float)
    v = v[np.isfinite(v)]
    med = float(np.median(v)) if len(v) else float("nan")
    lo, hi = spec["census_inputs"]["band_unit_check_cents"]
    return {"median_v_cents": med, "rows": int(len(v)), "ok": bool(np.isfinite(med) and lo <= med <= hi)}


def census_ch232(U: pd.DataFrame, tot: dict, spec: dict, covered_days: float, twin_days: float, band: dict, by_slot: dict, twin_cache: dict | None = None) -> dict:
    """CH232's gates on the arm-``out`` units; ``U`` = the units of every arm (S1 / S2 counted descriptively only)."""
    g, a = spec["census_gates"]["CH232"], b.mde_common(spec)
    scale, scale_f = _scale(covered_days), _scale(twin_days)
    res: dict = {"covered_days": covered_days, "twin_days": twin_days, "band_unit_check": band, "m1_side_reading": spec.get("m1_side_reading"),
                 "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    Oz = U[(U["arm"] == "out") & (U["in_scope"] == 1)] if len(U) else U
    if Oz.empty:
        res["gate_CH232"] = {"units": False, "pass": False, "no_units": True}
        res["status"] = "census_dropped"
        return res
    n_zone = len(Oz)
    finite_share = float(np.isfinite(Oz["rew"].to_numpy(float)).mean())
    Ok = Oz[np.isfinite(Oz["rew"].to_numpy(float))]
    cap_share = float((Ok[Ok["rew"] == 1]["ladder"] == 0).mean()) if (Ok["rew"] == 1).any() else float("nan")
    Oc = Ok[Ok["ladder"] == 0]
    Oc, _ = fix_panels11(Oc)
    R = Oc[Oc["panel"] == 1]
    C = Oc[Oc["panel"] == 0]
    R, excl, top = b._fam(R, a["family_cap"])
    R = R.copy()
    C = C[C["skey"].astype(str) != excl] if excl else C
    cross = R[R["xo"] == 1]
    ccross = C[C["xo"] == 1]
    R, fc_names = fee_dummies(R)
    controls = controls_for("CH232", R)
    de = b._de(cross, scale, g["de_floor"], a) if len(cross) else {"m_census": float("nan"), "m_21d": float("nan"), "DE": float("nan"), "DE_gate": float("nan")}
    ev_n = int(cross["event_id"].nunique()) if len(cross) else 0
    ge = g_eff(cross["event_id"]) if len(cross) else float("nan")
    md = pd.concat([R[R["xo"] + R["xr"] > 0]]).assign(_c=lambda d: d["xo"] + d["xr"]).groupby(["market_id", "day", "upper"])["_c"].sum()
    first_md = R[R["xo"] == 1].drop_duplicates(["market_id", "day", "upper"]).set_index(["market_id", "day", "upper"]).index
    md = md.reindex(first_md)
    recross3 = float((md >= 3).mean()) if len(md) else float("nan")
    recross2 = float((md >= 2).mean()) if len(md) else float("nan")
    Re = R[b._eff(R)] if len(R) else R
    dsg = b.design_ss(Re, "xo", controls) if len(Re) else {"vif_w": float("nan")}
    corr_x = {x: b.wcorr(R, "xo", x) for x in ("log1p_liq", "log_rv24s", "absd")}
    bm = b.block_min_units(covered_days)
    bs = b.block_share(R, bm)
    TW = _add_twin(R, "bandside", by_slot, {}, spec, twin_cache)
    F_cov = float(((TW["f_end_ok"] == 1) & np.isfinite(TW["xo_tw"].to_numpy(float))).mean()) if len(TW) else float("nan")
    F = TW[(TW["f_end_ok"] == 1) & np.isfinite(TW["xo_tw"].to_numpy(float))]
    rg = r_gate11(F, "xo", "xo_tw", int(g["pair_min_per_market"]))
    sm = class_mde11(R, "xo", controls, scale, a, de["DE_gate"], a[g["sd"]])
    fm = f_mde_gate(sm["mde_class_c"], rg["r_gate"], f_design_c(F, "xo", "xo_tw", controls, scale_f, a, a[g["sd"]], None))
    proj_c, proj_cc = float(len(cross) * scale), float(len(ccross) * scale)
    S1, S2 = U[U["arm"] == "in"], U[U["arm"] == "pseudo"]
    res.update({"zone_units": n_zone, "reward_status_finite_share": finite_share, "reward_crossings_projected_21d": proj_c, "control_crossings_projected_21d": proj_cc, "f_arm_coverage": F_cov,
                "recross_ge3_share": recross3, "recross_ge2_share": recross2, "distinct_events_unprojected": ev_n, "g_eff": ge, "cap_share": cap_share, "exclude_family": excl,
                "top_family_share": top, "venue_clock": _slot_share(cross) if len(cross) else float("nan"), "corr_x": corr_x, "vif_w": dsg["vif_w"], "block_min_units": bm, "block_share": bs,
                "r_gate": rg, "class": sm, "F": fm, "design_effect": de, "fee_dummies": fc_names, "reference_units": int((R["xo"] == 0).sum()), "reward_panel_units": int(len(R)),
                "control_panel_units": int(len(C)), "xr_units": int((R["xr"] == 1).sum()), "inward_S1_units": int(len(S1)), "inward_S1_crossings": int((S1["xo"] == 1).sum()),
                "pseudo_S2_units": int(len(S2)), "pseudo_S2_crossings": int((S2["xo"] == 1).sum()), "crossings_by_side": {"lower": int(((cross["upper"] == 0)).sum()), "upper": int(((cross["upper"] == 1)).sum())},
                "events_proj": b._events8(cross, scale, covered_days) if len(cross) else {}})
    gate = {"reward_finite": bool(finite_share >= g["reward_finite_min"]), "crossings": proj_c >= g["crossings_projected_min"], "control_crossings": proj_cc >= g["control_crossings_projected_min"],
            "f_arm_coverage": bool(np.isfinite(F_cov) and F_cov >= g["f_arm_coverage_min"]), "recross": bool(np.isfinite(recross3) and recross3 <= g["recross_ge3_max"]),
            "distinct_events": ev_n >= g["distinct_events_min"], "g_eff": bool(np.isfinite(ge) and ge >= a["g_eff_min"]), "cap_share": bool(np.isfinite(cap_share) and cap_share >= g["cap_share_min"]),
            "venue_clock": bool(len(cross) and _slot_share(cross) <= g["venue_clock_max"]), **{f"corr_xo_{x}": b.corr_ok(c_, g["corr_max"], both=True) for x, c_ in corr_x.items()},
            "vif_w": bool(np.isfinite(dsg["vif_w"]) and dsg["vif_w"] <= g["vif_w_max"]), "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]),
            "r_gate": bool(np.isfinite(rg["r_gate"]) and rg["r_gate"] <= g["r_gate_max"]), "class_mde": bool(sm["mde_class_c"] <= a["mde_max_c"]["CH232"]), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max_c"]["CH232"])}
    res = _gate_block(res, gate, "gate_CH232")
    if not band["ok"]:
        res = _nan_gate(res, "gate_CH232", "band_unit")
    res["census_fixed"] = {"exclude_family": excl}
    return res


# --- the LT11 seal (a fresh seal of the span's captures; 7, 8.4 step 4) -------------------------------------------------------------------


CENSUS_UNAVAILABLE = "census_unavailable (coverage)"
CENSUS_DROPPED = "census_dropped"
CENSUS_PASS = "census_pass"


def _span_slots(spec: dict) -> list[int]:
    ci = spec["census_inputs"]
    k0 = b.slot_of(epoch(ci["span"]["first_slot_utc"]), spec)
    k1 = b.slot_of(epoch(ci["span"]["last_slot_utc"]), spec)
    return list(range(k0, k1 + 1))


def seal_windows(spec: dict) -> dict:
    """The sealed slot range (7): captures from 12 slots before the span (look-back) to 3 slots after it (the twins' slots k + 1 .. k + 3 of the last origins)."""
    ci = spec["census_inputs"]
    sl = _span_slots(spec)
    return {"captures": (sl[0] - ci["lookback_capture_slots"], sl[-1] + ci["lag_slots_after"])}


def seal_inputs(*, snapshot_root, work: Path, spec: dict | None = None, unavailable=None, design_path: Path | None = None) -> dict:
    """The LT11 seal (7): every complete capture (rows, manifest, sidecar) in the sealed window found in the roots (host copies first, then restore trees),
    each hashed. A directory found in two roots with different bytes refuses (never substituted). Records the seal's own slot assignment, the frozen
    design-text sha256 (the seal is written only after the freeze), the spec's census blocks and the header pre-check result (``k_block``, which must already
    be filled from the committed pre-check). Missing slots are counted, never filled."""
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
    files, slots, conflicts = {}, {}, []

    def put(rel: str, p: Path, d: str, extra: dict) -> None:
        h = sha256_file(p)
        for r in b._roots(snapshot_root):
            q = Path(r) / d / p.name
            if q.exists() and q.parent != p.parent and sha256_file(q) != h:
                conflicts.append({"file": rel, "root_a": str(p), "root_b": str(q)})
        files[rel] = {"sha256": h, "root": str(p.parent.parent), "kind": "capture", **extra}

    caps_k = sorted(k for k in by_slot if win["captures"][0] <= k <= win["captures"][1])
    for k in caps_k:
        c = by_slot[k]
        if c["start"] >= bound:
            continue
        for rel, p in b.capture_files(c["dir"]):
            put(rel, p, c["id"], {"capture": c["id"]})
        slots[c["id"]] = iso(b.slot_time(k, spec))
    if conflicts:
        return {"error": "a sealed directory exists in two roots with different bytes: LT11 seal refused", "conflicts": conflicts[:50], "n_conflicts": len(conflicts)}
    bad = [d for d, s_ in slots.items() if epoch(s_) >= bound]
    if bad:
        return {"error": "a sealed slot is at or after the sealed bound: refused", "bad": bad[:20]}
    cap_need = range(win["captures"][0], win["captures"][1] + 1)
    miss_c = [iso(b.slot_time(k, spec)) for k in cap_need if k not in caps_k]
    unavail = sorted(b.load_unavailable(unavailable)) if unavailable else []
    return {"purpose": "LT11 census inputs (LIVE_TESTS_11.md section 7): every capture the census may open, each hashed; counts-only use", "written_utc": iso(b.now_ts()),
            "spec_sha256": sha256_file(SPEC_PATH), "design_text_sha256": design_text_sha(design_path), "spec_blocks_sha256": spec_blocks_sha(spec), "k_block": spec["k_block"],
            "span": spec["census_inputs"]["span"], "refuse_at_or_after_utc": spec["census_inputs"]["refuse_at_or_after_utc"], "windows": {k_: [v_[0], v_[1]] for k_, v_ in win.items()},
            "slots": dict(sorted(slots.items())), "needs": {"captures": len(caps_k)}, "span_slots": len(_span_slots(spec)), "missing": {"captures": miss_c}, "n_missing": {"captures": len(miss_c)},
            "unavailable_declared": unavail, "n_files": len(files), "files": dict(sorted(files.items()))}


def bound_violations(seal: dict, spec: dict) -> list[dict]:
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = [{"what": d, "value": s_, "error": "at or after the sealed bound"} for d, s_ in (seal.get("slots") or {}).items() if epoch(s_) >= bound]
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
    """7's minimum covered days, computed from the seal manifest BEFORE any row is read and identical for all three tests (it uses no test's filters): a
    covered origin is a span slot whose capture and the capture of the slot before it are both sealed with rows, sidecar and manifest; a covered twin
    origin also has the captures of slots k + 2 and k + 3. ``ok`` needs >= 7.0 covered days and >= 5.0 covered twin days."""
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
    return {"covered_origins": len(org), "covered_days": cd, "twin_origins": len(twin), "twin_days": td, "min_covered_days": mins["CC11"], "min_twin_days": mins["CC11_twins"],
            "ok": bool(cd >= mins["CC11"] and td >= mins["CC11_twins"]), "origins": org}


def _load_for_census(seal: Path, snapshot_root, work: Path, spec: dict, verify: bool = True, design_path: Path | None = None) -> dict:
    """The refusals every census runs first: the frozen design text, the seal's design hash, the sealed bound, the seal-time spec blocks, the reward rule, the
    header pre-check result, an empty work dir; then every sealed capture must be present locally with every sealed file hash-equal, and the scan must pick the
    sealed directory for each sealed slot (else refused, L3)."""
    seal_d = json.loads(Path(seal).read_text())
    if (derr := design_text_error(design_path)):
        return derr
    if seal_d.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        return {"error": "the seal was written against a different LIVE_TESTS_11.md: census refused", "seal_design_text_sha256": seal_d.get("design_text_sha256")}
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
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    return {"seal": seal_d, "by_slot": by_slot, "files_checked": files_checked}


def census_units(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True, design_path: Path | None = None) -> dict:
    """The data pass of CC11 (7): the refusals, the coverage check (FIRST: if it fails nothing else runs and no row is opened) and the streaming build of every
    test's units over the covered origins. Returns ``{"unavailable": result}`` on a coverage failure, ``{"error": ...}`` on a refusal, else the pieces
    :func:`census_gates` evaluates. Counts only: no target and no outcome is read."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    loaded = _load_for_census(seal, snapshot_root, work, spec, verify=verify, design_path=design_path)
    if "error" in loaded:
        return loaded
    cov = seal_coverage(loaded["seal"], spec)
    head = {"span": spec["census_inputs"]["span"], "inputs_verified": bool(verify), "files_checked": loaded["files_checked"], "design_text_sha256": DESIGN_TEXT_SHA256,
            "reward_null_rule": spec.get("reward_null_rule"), "k_block": spec.get("k_block"), "m1_side_reading": spec.get("m1_side_reading"),
            "coverage": {k_: v_ for k_, v_ in cov.items() if k_ != "origins"}}
    if not cov["ok"]:  # returns BEFORE any gate block is built and before a row is opened (R1 must-fix 7)
        return {"unavailable": {**head, "statuses": {t: CENSUS_UNAVAILABLE for t in TESTS},
                                **{t: {"status": CENSUS_UNAVAILABLE, "covered_days": cov["covered_days"], "twin_days": cov["twin_days"]} for t in TESTS}}}
    by_slot = loaded["by_slot"]
    ORG = sorted(cov["origins"])
    org_set = set(ORG)
    store = SlotStore(work, by_slot, spec, cache_slots=20)
    loop = sorted(s_ for s_ in by_slot if ORG[0] - 12 <= s_ <= ORG[-1])
    parts = {"CH234": [], "CH233": [], "CH232": []}
    tots: dict = {"CH234": {}, "CH233": {}, "CH232": {}}
    spans: list = []
    fee_counts: dict = {}
    v_rewarded: list[np.ndarray] = []
    for k in loop:
        cap = by_slot[k]
        write_series11(work, cap, spec)
        ser = store.ser(k)
        if ser is not None:
            b._fee_counts(ser, fee_counts)
        if k not in org_set:
            continue
        sc = carry_frame(store.carry(k), store.ser(k), k, b._utc_day(cap["start"]))
        rr = (sc["rewarded"].to_numpy(float) == 1.0) & (sc["sports"].to_numpy(int) == 0) & (sc["crypto7"].astype(str).to_numpy() == "non_crypto")
        v_rewarded.append(sc["rew_maxspread"].to_numpy(float)[rr])
        for test, fn in (("CH234", ch234_units), ("CH233", ch233_units), ("CH232", ch232_units)):
            u, cnt = fn(store, k, spec, stamp=False)
            spans.extend(cnt.pop("_spans", []))
            b._merge_counts(tots[test], cnt)
            if len(u):
                parts[test].append(u)
    return {"head": head, "cov": cov, "by_slot": by_slot, "ORG": ORG, "parts": parts, "tots": tots, "spans": spans, "fee_counts": fee_counts, "v_rewarded": v_rewarded}


def census_gates(cu: dict, spec: dict, twin_cache: dict | None = None) -> dict:
    """The gate blocks of CC11 on the output of :func:`census_units` (each block evaluated independently; a failing block never changes another)."""
    head, cov, by_slot, ORG = cu["head"], cu["cov"], cu["by_slot"], cu["ORG"]
    fs = b.crypto_failsafe(cu["fee_counts"])
    if not fs["classifier_shown_to_work"]:
        return {**head, "error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    U = {t: (pd.concat(p_, ignore_index=True) if p_ else pd.DataFrame()) for t, p_ in cu["parts"].items()}
    cd, td = cov["covered_days"], cov["twin_days"]
    band = band_unit_check(np.concatenate(cu["v_rewarded"]) if cu["v_rewarded"] else [], spec)
    out = {**head, "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"], "covered_origins": len(ORG),
           "expected_origins": spec["census_inputs"]["expected_origins"].get("CC11"),
           "CH234": census_ch234(U["CH234"], cu["tots"]["CH234"], spec, cd, td, len(ORG), by_slot, twin_cache),
           "CH233": census_ch233(U["CH233"], cu["tots"]["CH233"], cu["spans"], spec, cd, td, by_slot, twin_cache),
           "CH232": census_ch232(U["CH232"], cu["tots"]["CH232"], spec, cd, td, band, by_slot, twin_cache)}
    prim = {"CH234": U["CH234"][(U["CH234"]["in_scope"] == 1) & (U["CH234"]["vclass"] == "traded")] if len(U["CH234"]) else U["CH234"],
            "CH233": U["CH233"][U["CH233"]["arm"] == "primary"] if len(U["CH233"]) else U["CH233"],
            "CH232": U["CH232"][(U["CH232"]["arm"] == "out") & (U["CH232"]["xo"] == 1)] if len(U["CH232"]) else U["CH232"]}
    out["unit_overlaps"] = b.unit_overlaps(prim)
    out["statuses"] = {t: out[t]["status"] for t in TESTS}
    return out


def census_captures(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True, design_path: Path | None = None) -> dict:
    """CC11 (7): the three gate blocks on the sealed captures (counts only). The coverage check is evaluated FIRST, from the seal manifest: if it fails, NO
    row is opened, no gate of any test is computed or printed (only the coverage counts) and every test is recorded ``census_unavailable (coverage)``, a
    status distinct from ``census_dropped`` (a computed gate failed). The twins go through the lag-slot loaders only (7), after the units and their census
    scales exist."""
    spec = spec or load_spec(sha=None)
    cu = census_units(seal=seal, snapshot_root=snapshot_root, work=work, spec=spec, verify=verify, design_path=design_path)
    if "error" in cu:
        return cu
    if "unavailable" in cu:
        return cu["unavailable"]
    return census_gates(cu, spec)


def header_precheck(*, capture_dir: Path | None = None, spec: dict | None = None) -> dict:
    """7: the header pre-check (headers only, NO rows): which of the required row and sidecar fields one capture carries, and whether the optional ``chg_1d`` /
    ``chg_1w`` exist (they fix K's columns, 1.7). Its result is committed before the seal. A missing field makes the dependent gate NaN."""
    spec = spec or load_spec(sha=None)
    hp = spec["census_inputs"]["header_precheck"]
    out: dict = {"capture_dir": str(capture_dir) if capture_dir else None}
    if capture_dir is None:
        return out
    d = Path(capture_dir)
    rows = list(pd.read_csv(d / "rows.csv.gz", nrows=0).columns) if (d / "rows.csv.gz").exists() else None
    ext = list(pd.read_csv(d / "rows_ext.csv.gz", nrows=0).columns) if (d / "rows_ext.csv.gz").exists() else None
    out["rows_header"], out["sidecar_header"] = rows, ext
    out["rows_missing"] = [c for c in hp["rows"] if rows is not None and c not in rows]
    out["sidecar_missing"] = [c for c in hp["sidecar"] if ext is not None and c not in ext]
    out["chg_1d"] = bool(rows is not None and "chg_1d" in rows)
    out["chg_1w"] = bool(rows is not None and "chg_1w" in rows)
    out["manifest_has_state"] = bool((d / "manifest.json").exists() and "state" in json.loads((d / "manifest.json").read_text()))
    return out
