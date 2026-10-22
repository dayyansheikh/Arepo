# ruff: noqa: E501
"""LIVE prospective tests LT8 (docs/research_lab/LIVE_TESTS_8.md, text-frozen; section 13 governs where earlier text differs).
DRAFT: nothing is registered; E-numbers are assigned at registration. Research tooling only; never trades; no network request.

CODE PHASE 1: the census input seal and the counts-only pre-registration censuses (design sections 1, 7, 8.1-8.3 as they apply to the
censuses and the seal):

* CH203 (the quiet book), CS8: ``quiet_units`` on sweep 1 of passes k - 2 and k - 1 with captures k - 12 .. k, and the F-feasibility
  pairs (the lag sweeps k + 5 and k + 6, read ONLY through :func:`lag_sweep8`: keys + ``depth_bid_5c`` / ``depth_ask_5c``);
* CH202 (the sweep clock), CS8: ``swclock_units`` on sweep 1 of pass k - 1 with captures k - 12, k - 1, k;
* CH204 (the market's own clock), CC8: ``sched_units`` on the 84-slot look-back of captures k - 84 .. k (a streaming slot store, no
  per-run whole-series cache); the target interval (k + 1, k + 2] is a calendar fact (``sigma(k + 2)``) and no capture after k is read.

Censuses read origin-side fields only: no target, no P&L. Every opened input file is checked against the LT8 seal first (refused on any
mismatch, L3). LT3-LT7 code is used only through the vendored copies in ``live_tests8_base`` (8.1); this module never imports
``live_tests3`` .. ``live_tests7``. New LT8 code (not vendored): the empty / null ``clob_rewards`` rule (:func:`reward_status`), the
LT8 lag-slot loader, the slot store, the unit builders, the design-based MDE under a working covariance, the gates and the seal.

The reader (``run_once``), ``backfill-series``, the single analysis, the size check and the RSS probe are CODE PHASE 2 (not in this file).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import forecast, panel
from . import live_tests8_base as b

VERSION = "live-tests8-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SWEEP_ROOT = ROOT / "data-dumps" / "research_lab" / "book_sweeps"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests8"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests8_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration
REGISTERED_UTC = "2026-12-30T00:00:00Z"  # proposed (design 1.1); slides later with LT7's END_UTC
END_UTC = "2027-01-20T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2027-01-21T12:00:00Z"
TEMPFAIL = 75
DAY_S = 86400.0
DESIGN_TEXT_SHA256 = "5e61c20b1282cef79c7caee68f08dceb506f845bc1a1325fe2fb9335c955cf48"  # LIVE_TESTS_8.md at the design-text freeze
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_8.md"
LT7_SEAL_SHA256 = "117e9b458931b7493f6b34e36ce68e7e4898c544fb5aa360956ea106de204137"
CODE_FILES = ("live_tests8.py", "live_tests8_analysis.py", "live_tests8_base.py", "bounce_decomp.py",
              # hashed dependencies (design 8.1) and the modules the vendored base imports
              "panel.py", "trade_sample.py", "cb17_census.py", "cb13_label.py", "economics.py", "forecast.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)

SNAP_COLS = [*b.SNAP_COLS, "liquidity"]
EXT_COLS = [*b.EXT_COLS, "rewards_min_size", "rewards_max_spread", "clob_rewards"]
# The lag-slot loader (design 7): the ONLY way a sweep later than a unit's origin is read by census code. Stricter than LT7's: no touch
# size, no price, no state column of a later slot is reachable; only the keys and the two 5c depths.
LAG_SWEEP_COLUMNS = ("depth_bid_5c", "depth_ask_5c")
LAG_SWEEP_KEYS = ("market_id", "token_id")
LAG_CAPTURE_KEY_COLUMNS = ("market_id", "clob_token_id_0")  # the same pass's capture: the outcome-0 token key only
# columns ops_stats may read (never a price, a move, a state value or a target; enforced by a unit test)
OPS_COLS = frozenset({"role", "cls", "geom", "klass", "sports", "crypto", "capflag", "scheduled", "status", "late", "lookback", "nosweep_km1", "nosweep_km2"})
KINDS = ("quiet", "swclock", "sched")
MARKERS = (".late.csv.gz", ".nosweep_km1.csv.gz", ".nosweep_km2.csv.gz")

epoch, iso, sha256_file, _json = b.epoch, b.iso, b.sha256_file, b._json
_NULL_LIKE = b._NULL_LIKE


# --- pins and spec ---------------------------------------------------------------------------------------------------


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LT3 9.3's rule)."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def code_hashes() -> dict:
    """Normalised hash of every code file; a file that does not exist yet (the analysis module, phase 2) maps to None."""
    here = Path(__file__).resolve().parent
    return {n: (code_sha256(here / n) if (here / n).exists() else None) for n in CODE_FILES}


def load_spec(path: Path = SPEC_PATH, sha: str | None = SPEC_SHA256) -> dict:
    """The spec as written. DRAFT (``sha is None``): null placeholders are allowed. Pinned: the hash must match and the spec's
    dates must equal the module constants (L6)."""
    spec = json.loads(Path(path).read_text())
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"live_tests8 spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests8 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    if spec.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        raise RuntimeError("live_tests8 spec design_text_sha256 differs from the module constant")
    return spec


SPEC_HASHED_BLOCKS = ("census_gates", "census_inputs", "tests", "move", "eligibility", "grid", "crypto_classifier", "sports_rule", "series_key_rule", "reward_rule", "member_cap")


def spec_blocks_sha(spec: dict) -> str:
    """sha256 of the canonical JSON of every spec block census code reads (``SPEC_HASHED_BLOCKS``). The seal stores it; every census
    refuses a spec whose blocks differ from the seal-time ones. ``census_fixed`` is deliberately outside the hash."""
    blob = json.dumps({k_: spec[k_] for k_ in SPEC_HASHED_BLOCKS}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def design_text_sha() -> str:
    """sha256 of ``docs/research_lab/LIVE_TESTS_8.md`` itself (computed, never copied from the spec)."""
    return sha256_file(DESIGN_PATH)


def design_text_error() -> dict | None:
    got = design_text_sha()
    return None if got == DESIGN_TEXT_SHA256 else {"error": "LIVE_TESTS_8.md differs from the text-frozen file: refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}


# --- the empty / null clob_rewards rule (NEW LT8 code; design 1.0 (iv), 2; unit tested) ----------------------------------------


def reward_status(v, day: str | None = None) -> tuple[float, str]:
    """``(daily rate, state)`` of a sidecar ``clob_rewards`` value. An empty / null field is UNREWARDED, not unknown (LT5 R and LT7
    parsed it as NaN and so removed the unrewarded class). States: ``unset`` (None, NaN, empty, whitespace or null-like text; rate 0.0),
    ``empty_list`` (a valid ``[]``; 0.0), ``zero`` (allocations summing to 0 on ``day``), ``rewarded`` (sum > 0) and ``malformed``
    (NON-NULL text that is not a JSON list of dict allocations, or an allocation whose ``rewardsDailyRate`` is non-numeric, boolean,
    negative or not finite; rate NaN: the unit is excluded and counted, never read as 0)."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return 0.0, "unset"
    s = str(v).strip()
    if s.casefold() in _NULL_LIKE:
        return 0.0, "unset"
    try:
        arr = json.loads(s)
    except (ValueError, TypeError):
        return float("nan"), "malformed"
    if arr is None:
        return 0.0, "unset"
    if not isinstance(arr, list):
        return float("nan"), "malformed"
    if not arr:
        return 0.0, "empty_list"
    tot = 0.0
    for a in arr:
        if not isinstance(a, dict):
            return float("nan"), "malformed"
        rate = a.get("rewardsDailyRate")
        if rate is None or (isinstance(rate, str) and rate.strip() == ""):
            r = 0.0
        else:
            if isinstance(rate, bool):
                return float("nan"), "malformed"
            try:
                r = float(rate)
            except (TypeError, ValueError):
                return float("nan"), "malformed"
            if not math.isfinite(r) or r < 0:
                return float("nan"), "malformed"
        if day is not None:
            sd, ed = str(a.get("startDate") or "")[:10], str(a.get("endDate") or "")[:10]
            if (sd and day < sd) or (ed and day > ed):
                continue
        tot += r
    return tot, ("rewarded" if tot > 0 else "zero")


def clob_hash(v) -> str:
    """Short stable hash of the normalised ``clob_rewards`` string (null / empty / null-like all normalise to the empty string)."""
    if v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip().casefold() in _NULL_LIKE:
        return ""
    return hashlib.blake2b(str(v).strip().encode("utf-8"), digest_size=8).hexdigest()


# --- readers ---------------------------------------------------------------------------------------------------------------


def load_rows8(cap_dir: Path) -> pd.DataFrame:
    """Origin-side capture columns (LT3's plus Gamma ``liquidity``): one row per market_id and per condition_id, with the member
    count ``n_members`` (distinct markets of the Gamma event among the capture's binary, open and active rows, one-sided books
    included; a market without ``event_id`` is its own event with 1 member) and the event key ``ekey``."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(SNAP_COLS),
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category", "end_date": "category",
                              "closed": str, "active": str, "neg_risk": str})
    if "liquidity" not in rows:
        rows["liquidity"] = np.nan
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
    n_members = np.where((ev == "").to_numpy(), 1.0, ev.map(nm).fillna(1.0).to_numpy(float))
    rows["n_members"] = n_members
    rows["ekey"] = np.where((ev == "").to_numpy(), "m:" + mid.to_numpy(), ev.to_numpy())
    return rows


def load_ext8(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS), dtype=str)
    for c in EXT_COLS:
        if c not in ext:
            ext[c] = None
    return ext.drop_duplicates("market_id").set_index("market_id")


def series8_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, day: str) -> pd.DataFrame:
    """LT3's series (vendored) plus Gamma ``liq``, ``n_members``, the event key (``event_id`` = Gamma event, else ``m:<market>``), the
    reward fields (``rew_rate`` and ``rew_state`` by :func:`reward_status`: a null / empty ``clob_rewards`` is unrewarded 0.0, malformed
    text NaN, a market with no sidecar row ``no_sidecar`` NaN; ``rew_min``; ``rew_maxspread`` in cents), the raw ``fee_cat`` and the
    pinned ``crypto7`` class."""
    ser, _ = b.series_frame(rows, ext, spec)
    mids = pd.Index(ser["market_id"].astype(str))
    r = rows.set_index(rows["market_id"].astype(str))
    ser["liq"] = r["liquidity"].reindex(mids).to_numpy(float)
    ser["n_members"] = r["n_members"].reindex(mids).to_numpy(float)
    ser["event_id"] = r["ekey"].reindex(mids).to_numpy(object)
    if ext is not None:
        e = ext.reindex(mids)
        present = np.asarray(mids.isin(ext.index))
        st = [reward_status(v, day) if p else (float("nan"), "no_sidecar") for v, p in zip(e["clob_rewards"], present, strict=True)]
        ser["rew_rate"] = [x[0] for x in st]
        ser["rew_state"] = [x[1] for x in st]
        ser["rew_min"] = pd.to_numeric(e["rewards_min_size"], errors="coerce").to_numpy(float)
        ser["rew_maxspread"] = pd.to_numeric(e["rewards_max_spread"], errors="coerce").to_numpy(float)
        fc = e["fee_category"].where(e["fee_category"].notna(), None).tolist()
    else:
        present = np.zeros(len(mids), bool)
        ser["rew_rate"], ser["rew_state"], ser["rew_min"], ser["rew_maxspread"] = np.nan, "no_sidecar", np.nan, np.nan
        fc = [None] * len(mids)
    sp = ser["sports"].to_numpy(int)
    ser["fee_cat"] = pd.Series(fc, dtype=object).to_numpy()
    ser["crypto7"] = [b.crypto_class(f, bool(p), int(s)) for f, p, s in zip(fc, present, sp, strict=True)]
    return ser


def write_series8(work: Path, cap: dict, spec: dict) -> None:
    """Write-once ``series/<id>.csv.gz`` (two-sided quotes) and ``rw/<id>.csv.gz`` (the ``clob_rewards`` hash of EVERY sidecar row, so
    that ``rw_changed`` does not depend on the market having been two-sided at k - 2)."""
    p = Path(work) / "series" / f"{cap['id']}.csv.gz"
    if p.exists():
        return
    rows = load_rows8(cap["dir"])
    ext = load_ext8(cap["dir"])
    b.write_once_csv(p, series8_frame(rows, ext, spec, b._utc_day(cap["start"])))
    rw = pd.DataFrame({"market_id": ext.index.astype(str), "clob_h": [clob_hash(v) for v in ext["clob_rewards"]]}) if ext is not None else pd.DataFrame({"market_id": [], "clob_h": []})
    b.write_once_csv(Path(work) / "rw" / f"{cap['id']}.csv.gz", rw)


def read_rw(work: Path, cap_id: str | None) -> pd.Series | None:
    if cap_id is None:
        return None
    p = Path(work) / "rw" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    d = pd.read_csv(p, dtype={"market_id": str, "clob_h": str}, keep_default_na=False)
    return d.drop_duplicates("market_id").set_index("market_id")["clob_h"]


def lag_sweep8(sweep_dir: Path, cap_dir: Path) -> pd.DataFrame:
    """A later pass's sweep 1 on the outcome-0 token, indexed by market_id, with ONLY ``depth_bid_5c`` and ``depth_ask_5c`` (CH203's
    F-feasibility lag, design 7). Both files are read with ``usecols``: the sweep's keys and the two depths, and the same pass's
    capture's ``market_id`` / ``clob_token_id_0`` token key. No best bid or ask, touch size, state, receipt, last trade or other
    column of a later slot reaches census code."""
    tok = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=list(LAG_CAPTURE_KEY_COLUMNS), dtype=str).drop_duplicates("market_id")
    sw = pd.read_csv(Path(sweep_dir) / "rows.csv.gz", usecols=lambda c: c in {*LAG_SWEEP_KEYS, *LAG_SWEEP_COLUMNS}, dtype={"token_id": str, "market_id": str})
    for c in LAG_SWEEP_COLUMNS:
        if c not in sw:
            sw[c] = np.nan
    sw = sw.merge(tok, on="market_id", how="inner")
    sw = sw[sw["token_id"] == sw["clob_token_id_0"]].drop_duplicates("market_id").set_index("market_id")
    return sw[list(LAG_SWEEP_COLUMNS)].apply(pd.to_numeric, errors="coerce")


def sweep_levels8(sweep_dir: Path, cap_dir: Path) -> pd.DataFrame:
    """Origin-side level counts of a sweep 1 (outcome 0): ``nb`` / ``na`` = ``n_bid_levels`` / ``n_ask_levels`` (every level of the side,
    not the 5c band; descriptive ``dlev``). NaN columns when the sweep does not carry them."""
    tok = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=["market_id", "clob_token_id_0"], dtype=str).drop_duplicates("market_id")
    sw = pd.read_csv(Path(sweep_dir) / "rows.csv.gz", usecols=lambda c: c in {"market_id", "token_id", "n_bid_levels", "n_ask_levels"}, dtype={"token_id": str, "market_id": str})
    for c in ("n_bid_levels", "n_ask_levels"):
        if c not in sw:
            sw[c] = np.nan
    sw = sw.merge(tok, on="market_id", how="inner")
    sw = sw[sw["token_id"] == sw["clob_token_id_0"]].drop_duplicates("market_id").set_index("market_id")
    return pd.DataFrame({"nb": pd.to_numeric(sw["n_bid_levels"], errors="coerce"), "na": pd.to_numeric(sw["n_ask_levels"], errors="coerce")})


# --- the slot store (streaming; mids, spreads, last trades and volumes by slot, evicted by the census loop) --------------------


class SlotStore8(b.MidStore):
    """:class:`live_tests8_base.MidStore` plus the last trade and ``volume24hr`` of every slot (for CH204's look-back anatomy share).
    Slots are added in ascending order by the census loop and evicted with :meth:`evict`; only slots <= the origin are ever asked for."""

    def __init__(self) -> None:
        super().__init__()
        self.extra: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def add(self, k: int, ser: pd.DataFrame) -> None:
        super().add(k, ser)
        self.extra[k] = (ser["ltp"].to_numpy(float), ser["vol24"].to_numpy(float))

    def evict(self, below: int) -> None:
        for j in [s for s in self.slots if s < below]:
            self.slots.pop(j, None)
            self.extra.pop(j, None)

    def matrix(self, k: int, window: int, markets, what: str = "mid") -> np.ndarray:
        if what in ("mid", "spread"):
            return super().matrix(k, window, markets, what)
        col = {"ltp": 0, "vol": 1}[what]
        idx = np.fromiter((self.code.get(str(m), -1) for m in markets), dtype=np.int64, count=len(markets))
        out = np.full((len(idx), window + 1), np.nan)
        ok = idx >= 0
        n = len(self.code)
        for i, j in enumerate(range(k - window, k + 1)):
            if j not in self.slots:
                continue
            codes = self.slots[j][0]
            arr = np.full(n, np.nan)
            arr[codes] = self.extra[j][col]
            out[ok, i] = arr[idx[ok]]
        return out


# --- origins and covered days from the seal's own slot assignment (no row read) ---------------------------------------------


def origins_cs8(cap_slots: set[int], sweep_slots: set[int]) -> dict:
    """CS8 origins from the sealed slots. CH203: sweeps k - 2 and k - 1 and captures k - 1 and k sealed; CH202: sweep k - 1 and captures
    k - 1 and k sealed; CH203 F pairs: a CH203 origin whose lag sweeps k + 5 and k + 6 are also sealed."""
    cand = {s + d for s in sweep_slots for d in (1, 2)}
    o203 = sorted(k for k in cand if {k - 2, k - 1} <= sweep_slots and {k - 1, k} <= cap_slots)
    o202 = sorted(k for k in cand if (k - 1) in sweep_slots and {k - 1, k} <= cap_slots)
    pairs = sorted(k for k in o203 if {k + 5, k + 6} <= sweep_slots)
    return {"CH203": o203, "CH202": o202, "CH203_pairs": pairs}


def origins_cc8(cap_slots: set[int], spec: dict) -> list[int]:
    """CC8 origins: captures k - 1 and k sealed and at least ``min_observed_changes`` (70) of the 84 changes ``(i - 1, i]``, i = k - 83 .. k,
    observable from the sealed slots (both ends sealed)."""
    c = spec["tests"]["CH204"]
    out = []
    for k in sorted(cap_slots):
        if (k - 1) not in cap_slots:
            continue
        n = sum(1 for i in range(k - c["lookback_changes"] + 1, k + 1) if i in cap_slots and (i - 1) in cap_slots)
        if n >= c["min_observed_changes"]:
            out.append(k)
    return out


def block_of_origin(k: int, spec: dict) -> str | None:
    """The sweep block holding the slot of pass k - 1 (the latest sweep an origin needs)."""
    t = b.slot_time(k - 1, spec)
    for name, (lo, hi) in spec["census_inputs"]["sweep_blocks"].items():
        if epoch(lo) - 1.0 <= t <= epoch(hi) + 1.0:
            return name
    return None


def per_block_counts(origins: list[int], spec: dict) -> dict:
    names = list(spec["census_inputs"]["sweep_blocks"])
    cnt = dict.fromkeys(names, 0)
    other = 0
    for k in origins:
        n_ = block_of_origin(k, spec)
        if n_ is None:
            other += 1
        else:
            cnt[n_] += 1
    return {**cnt, "other": other}


def _gate_blocks(res: dict, key: str, counts: dict, spec: dict) -> dict:
    """Design 7 (R1 should-fix, Q14): at least ``min_origins_per_sweep_block`` origins of the test in EACH sweep block; below it every
    gate of the test's census is NaN and fails."""
    minimum = int(spec["census_inputs"]["min_origins_per_sweep_block"])
    ok = all(counts.get(n_, 0) >= minimum for n_ in spec["census_inputs"]["sweep_blocks"])
    res["per_block_origins"], res["per_block_minimum"], res["per_block_ok"] = counts, minimum, bool(ok)
    if not ok:
        g = res.get(key, {})
        res[key] = {**{k_: False for k_ in g if k_ != "pass"}, "per_block": False, "pass": False, "values_nan": True}
    else:
        res[key]["per_block"] = True
    return res


# --- shared unit machinery ---------------------------------------------------------------------------------------------------


_SW_COLS = ["sbid", "sask", "s_t", "s_two", "bsz1", "asz1", "dbid5", "dask5", "dbid1", "dask1"]
_Q_EPS = 1e-9


def _sw_take(sw: pd.DataFrame, mk: pd.Series, suffix: str, j: pd.DataFrame) -> None:
    a = sw.reindex(mk)[_SW_COLS].reset_index(drop=True)
    for col in _SW_COLS:
        j[f"{col}_{suffix}"] = a[col].to_numpy(float)


def _vol_cols(vol24) -> tuple[np.ndarray, np.ndarray]:
    """``log1p volume24hr`` with the declared indicator pair (1.5): a missing value enters as 0 with ``vol_missing``."""
    v = np.asarray(vol24, float)
    miss = ~np.isfinite(v)
    return np.where(miss, 0.0, np.log1p(np.clip(np.where(miss, 0.0, v), 0, None))), miss.astype(float)


def _rewards(j: pd.DataFrame, spread_sw, band) -> dict:
    """``rewarded`` (NaN when the reward text is malformed or the market has no sidecar row), ``in_band`` (0 for an unrewarded market;
    LT7 CH197's definition for a rewarded one) and the farmer touch ``ft_both`` pieces."""
    state = j["rew_state"].astype(str).to_numpy()
    rate = j["rew_rate"].to_numpy(float)
    unk = np.isin(state, ["malformed", "no_sidecar"]) | ~np.isfinite(rate)
    rewarded = np.where(unk, np.nan, (rate > 0).astype(float))
    ib = b._in_band(j["mid"].to_numpy(float), np.asarray(spread_sw, float), j["rew_maxspread"].to_numpy(float), band)
    in_band = np.where(unk, np.nan, np.where(rewarded == 0.0, 0.0, ib))
    return {"rewarded": rewarded, "in_band": in_band, "malformed": (state == "malformed")}


def _ft_both(rewarded, bsz, asz, rmin, factor) -> np.ndarray:
    """The farmer touch: rewarded and both touch sizes <= ``factor`` x ``rewards_min_size``; 0 when unrewarded; NaN when rewarded and a size
    or the minimum is missing, or the reward status itself is unknown."""
    rewarded, bsz, asz, rmin = (np.asarray(v, float) for v in (rewarded, bsz, asz, rmin))
    with np.errstate(invalid="ignore"):
        val = ((bsz <= factor * rmin) & (asz <= factor * rmin)).astype(float)
    known = np.isfinite(bsz) & np.isfinite(asz) & np.isfinite(rmin)
    return np.where(~np.isfinite(rewarded), np.nan, np.where(rewarded == 0.0, 0.0, np.where(known, val, np.nan)))


def _drop_missing(u: pd.DataFrame, cnt: dict, cols: dict[str, str]) -> pd.DataFrame:
    """Required controls (1.5): a missing control is NaN, EXCLUDED and counted (never 0); ``cols`` maps column -> count key."""
    for col, key in cols.items():
        ok = np.isfinite(u[col].to_numpy(float))
        cnt[key] = int((~ok).sum())
        u = u[ok]
    return u.reset_index(drop=True)


def _rv24(store, k: int, mk, tick, c: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    M = store.matrix(k, c["rv24_window"], mk, "mid")
    rv, _ = b.rv_from_matrix(M, c["rv24_min_obs"])
    rvs, rvf = b.floored_rv(rv, tick, c["rv_floor_ticks"])
    return rv, rvs, rvf


# --- CH203 the quiet book (design 2) -----------------------------------------------------------------------------------------


def quiet_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, ser_k2: pd.DataFrame | None, rw_k: pd.Series | None, rw_k2: pd.Series | None, store: b.MidStore,
                sw_k2: pd.DataFrame | None, sw_k1: pd.DataFrame | None, lv_k2: pd.DataFrame | None, lv_k1: pd.DataFrame | None, cap: dict, k: int,
                spec: dict) -> tuple[pd.DataFrame, dict]:
    """CH203's units of capture k (section 2): non-sports ex-crypto markets two-sided and tight at k - 1 and k (1.4 items 1-7, end > t + 7 h),
    ``mid_k`` in [0.07, 0.93], with sweep 1 of passes k - 2 AND k - 1 two-sided on the outcome-0 token, tight (sweep spread <= 0.10), both 5c
    depths positive at both and each received BEFORE capture k's start, QUIET (``|smid_{k-1} - smid_{k-2}| < 0.005`` and ``|mid_k -
    smid_{k-1}| < 0.005``). The returned frame keeps every ``n_members`` (the cap is applied by the census, which also needs the pre-cap
    count). State: ``dimb5 = imb5_{k-1} - imb5_{k-2}``. ``sw_*`` are :func:`live_tests8_base.sweep_frame` outputs indexed by market_id.
    A required control that is missing is excluded and counted (1.5), except the declared indicator pairs."""
    c = spec["tests"]["CH203"]
    j, cnt = b._movers_join(ser_k, ser_p, cap, spec, c["mid_lo_pre_band"], c["mid_hi_pre_band"], c["end_margin_h"])
    j = b._non_sports_ex_crypto(j.copy(), cnt)
    cnt["eligible_pre_band"] = len(j)
    if sw_k1 is None:
        cnt["nosweep_km1"] = 1
        return pd.DataFrame(), cnt
    if sw_k2 is None:
        cnt["nosweep_km2"] = 1
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    j = j.reset_index(drop=True)
    _sw_take(sw_k1, mk, "1", j)
    _sw_take(sw_k2, mk, "2", j)
    mid = j["mid"].to_numpy(float)
    in_band = (mid >= c["mid_lo"] - 1e-12) & (mid <= c["mid_hi"] + 1e-12)
    cnt["eligible_in_band"] = int(in_band.sum())
    two = (j["s_two_1"] == 1) & (j["s_two_2"] == 1)
    smax = c["sweep_spread_max"] + 1e-12
    tight = ((j["sask_1"] - j["sbid_1"]) <= smax) & ((j["sask_2"] - j["sbid_2"]) <= smax)
    d5 = j[["dbid5_1", "dask5_1", "dbid5_2", "dask5_2"]].to_numpy(float)
    dep = np.isfinite(d5).all(axis=1) & (d5 > 0).all(axis=1)
    struct = (two & tight & dep).to_numpy()
    start = float(cap["start"])
    t1, t2 = j["s_t_1"].to_numpy(float), j["s_t_2"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        recv = np.isfinite(t1) & np.isfinite(t2) & (t1 < start) & (t2 < start)
    cnt["covered_struct_in_band"] = int((struct & in_band).sum())
    cnt["sweep_after_origin"] = int((struct & ~recv & in_band).sum())
    cov = struct & recv
    cnt["covered_in_band"] = int((cov & in_band).sum())
    sm1 = ((j["sbid_1"] + j["sask_1"]) / 2.0).to_numpy(float)
    sm2 = ((j["sbid_2"] + j["sask_2"]) / 2.0).to_numpy(float)
    with np.errstate(invalid="ignore"):
        quiet = (np.abs(sm1 - sm2) < c["quiet_eps"] - _Q_EPS) & (np.abs(mid - sm1) < c["quiet_eps"] - _Q_EPS)
    cnt["covered_pre_band"] = int(cov.sum())
    cnt["quiet_covered_pre_band"] = int((cov & quiet).sum())
    keep = cov & quiet & in_band
    cnt["quiet_covered_in_band"] = int(keep.sum())
    cnt["quiet_covered_in_band_cap"] = int((keep & (j["n_members"].to_numpy(float) <= spec["member_cap"]["max_members"])).sum())
    cnt["quiet_covered_in_band_ladder"] = cnt["quiet_covered_in_band"] - cnt["quiet_covered_in_band_cap"]
    j = j[keep].reset_index(drop=True)
    if j.empty:
        return pd.DataFrame(), cnt
    mkj = j["market_id"].astype(str)
    imb1 = b.imbalance(j["dbid5_1"], j["dask5_1"])
    imb2 = b.imbalance(j["dbid5_2"], j["dask5_2"])
    tot1 = (j["dbid5_1"] + j["dask5_1"]).to_numpy(float)
    tot2 = (j["dbid5_2"] + j["dask5_2"]).to_numpy(float)
    dimb1 = b.imbalance(j["bsz1_1"], j["asz1_1"]) - b.imbalance(j["bsz1_2"], j["asz1_2"])
    if lv_k1 is not None and lv_k2 is not None:
        a1, a2 = lv_k1.reindex(mkj), lv_k2.reindex(mkj)
        dlev = (a1["nb"].to_numpy(float) - a2["nb"].to_numpy(float)) - (a1["na"].to_numpy(float) - a2["na"].to_numpy(float))
    else:
        dlev = np.full(len(j), np.nan)
    spread_sw = (j["sask_1"] - j["sbid_1"]).to_numpy(float)
    mid = j["mid"].to_numpy(float)
    vol_k, vol_kmiss = _vol_cols(j["vol24"])
    vol_p = j["vol24_p"].to_numpy(float)
    vol_k2 = ser_k2["vol24"].reindex(mkj).to_numpy(float) if ser_k2 is not None else np.full(len(j), np.nan)
    dv = vol_p - vol_k2
    dv_ok = np.isfinite(dv)
    dvp = np.where(dv_ok, np.log1p(np.clip(np.where(dv_ok, dv, 0.0), 0, None)), 0.0)
    with np.errstate(invalid="ignore"):
        silent = dv_ok & (dv <= np.maximum(c["silent_abs_tol"], c["silent_rel_tol"] * np.where(np.isfinite(vol_k2), vol_k2, 0.0)))
    m12 = b._mid12(store, k, j["market_id"])
    d24, d24f = b._own24(1.0, mid, m12)
    tick = j["tick"].to_numpy(float)
    rv, rvs, rvf = _rv24(store, k, mkj.to_numpy(), tick, c)
    rw = _rewards(j, spread_sw, c["reward_band"])
    ft = _ft_both(rw["rewarded"], j["bsz1_1"], j["asz1_1"], j["rew_min"], spec["reward_rule"]["ft_factor"])
    if rw_k is not None and rw_k2 is not None:
        hk, h2 = rw_k.reindex(mkj).to_numpy(object), rw_k2.reindex(mkj).to_numpy(object)
        rwc = np.where(pd.isna(hk) | pd.isna(h2), np.nan, (hk != h2).astype(float))
    else:
        rwc = np.full(len(j), np.nan)
    u = pd.DataFrame({**b._base_out(j, cap, k), "t_row": j["t_row"].to_numpy(float), "mid": mid, "tick": tick, "liq": j["liq"].to_numpy(float), "end_ts": j["end_ts"].to_numpy(float),
                      "vol24": j["vol24"].to_numpy(float), "n_members": j["n_members"].to_numpy(float), "imb5_km1": imb1, "imb5_km2": imb2, "dimb5": imb1 - imb2, "dimb1": dimb1,
                      "dlev": dlev, "total5_km1": tot1, "dlogD5": np.log1p(tot1) - np.log1p(tot2), "log1p_total5": np.log1p(tot1), "spread_sw": spread_sw,
                      "lag_s": (start - j["s_t_1"].to_numpy(float)) / 60.0, "log1p_vol": vol_k, "vol_missing": vol_kmiss, "dV_prev": dvp, "dvp_missing": (~dv_ok).astype(float),
                      "silent": silent.astype(float), "ltp_missing": (~np.isfinite(j["ltp"].to_numpy(float))).astype(float), "d24": d24, "d24_flag": d24f, "rv24": rv,
                      "rv24s": rvs, "rv_floor": rvf, "rewarded": rw["rewarded"], "in_band": rw["in_band"], "ft_both": ft, "rw_changed": rwc, "reward_malformed": rw["malformed"].astype(float),
                      "fee_cat": j["fee_cat"].to_numpy(object)})
    u = b._common_cols(u)
    u["log_rv24s"] = np.log(u["rv24s"])
    u = _drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "rewarded": "reward_unknown_or_malformed", "in_band": "in_band_unknown", "ft_both": "ft_both_unknown",
                               "rw_changed": "rw_changed_unknown", "tick": "tick_unknown", "imb5_km1": "imb_unknown", "dimb5": "dimb_unknown"})
    u["dimb5_lag"] = np.nan  # filled by the census for the F-feasibility origins (:func:`add_lag`)
    cnt["units_pre_cap"] = len(u)
    return u, cnt


def add_lag(Q: pd.DataFrame, lag5: pd.DataFrame | None, lag6: pd.DataFrame | None, spec: dict) -> pd.DataFrame:
    """CH203's falsification lag ``dimb5_lag = imb5_{k+6} - imb5_{k+5}`` from sweep 1 of passes k + 5 and k + 6, sizes only (both 5c depths
    finite and positive), for units whose end is unknown or later than ``t`` + 13 h; otherwise NaN (in the primary, out of the F arm)."""
    Q = Q.copy()
    if lag5 is None or lag6 is None or Q.empty:
        Q["dimb5_lag"] = np.nan
        return Q
    mk = Q["market_id"].astype(str)
    a, c = lag5.reindex(mk), lag6.reindex(mk)
    ok = np.isfinite(a.to_numpy(float)).all(axis=1) & np.isfinite(c.to_numpy(float)).all(axis=1) & (a.to_numpy(float) > 0).all(axis=1) & (c.to_numpy(float) > 0).all(axis=1)
    end = Q["end_ts"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        end_ok = np.isnan(end) | (end > Q["t_row"].to_numpy(float) + spec["tests"]["CH203"]["lag_end_margin_h"] * 3600.0)
    lag = b.imbalance(c["depth_bid_5c"], c["depth_ask_5c"]) - b.imbalance(a["depth_bid_5c"], a["depth_ask_5c"])
    Q["dimb5_lag"] = np.where(ok & end_ok, lag, np.nan)
    return Q


# --- CH202 the sweep clock (design 3) ------------------------------------------------------------------------------------------


def swclock_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: b.MidStore, sw_k1: pd.DataFrame | None, cap: dict, k: int, spec: dict) -> tuple[pd.DataFrame, dict]:
    """CH202's units of capture k (section 3): non-sports ex-crypto 2 h movers (1.4 items 1-7 at k - 1 and k, ``|x| >= 0.01``, ``mid_k`` in
    [0.05, 0.95], end > t + 7 h, all event sizes) with sweep 1 of pass k - 1 two-sided on the outcome-0 token, tight (<= 0.10) and received
    BEFORE capture k's start. ``early = sign(x) (smid_{k-1} - mid_{k-1})``, ``late = sign(x) (mid_k - smid_{k-1})``, ``early_share = early / |x|``
    clipped to [-0.5, 1.5]; held >= 0.75, fresh <= 0.25 (boundaries inclusive, float noise 1e-9), mixed the rest. The returned frame holds
    every covered mover (mixed included; the census contrasts held and fresh)."""
    c = spec["tests"]["CH202"]
    j, cnt = b._movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = j[np.abs(j["x"]) >= c["min_abs_x"] - 1e-12]
    cnt["movers_all_categories"] = len(j)
    j = b._non_sports_ex_crypto(j.copy(), cnt)
    cnt["movers_in_band"] = len(j)
    chg = j["chg_1h"].to_numpy(float)
    cnt["chg1h_present"] = int(np.isfinite(chg).sum())
    cnt["chg1h_exact_zero"] = int((np.isfinite(chg) & (chg == 0.0)).sum())
    if sw_k1 is None:
        cnt["nosweep_km1"] = 1
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    j = j.reset_index(drop=True)
    _sw_take(sw_k1, mk, "1", j)
    two = (j["s_two_1"] == 1).to_numpy()
    tight = ((j["sask_1"] - j["sbid_1"]) <= c["sweep_spread_max"] + 1e-12).to_numpy()
    t1 = j["s_t_1"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        recv = np.isfinite(t1) & (t1 < float(cap["start"]))
    cnt["no_sweep_two_sided"] = int((~two).sum())
    cnt["sweep_not_tight"] = int((two & ~tight).sum())
    cnt["sweep_after_origin"] = int((two & tight & ~recv).sum())
    cov = two & tight & recv
    cnt["covered"] = int(cov.sum())
    j = j[cov].reset_index(drop=True)
    if j.empty:
        return pd.DataFrame(), cnt
    mkj = j["market_id"].astype(str)
    x = j["x"].to_numpy(float)
    sx = np.sign(x)
    smid = ((j["sbid_1"] + j["sask_1"]) / 2.0).to_numpy(float)
    early = sx * (smid - j["mid_p"].to_numpy(float))
    late = sx * (j["mid"].to_numpy(float) - smid)
    share = np.clip(early / np.abs(x), c["share_clip"][0], c["share_clip"][1])
    tol = c["share_tol"]
    held = share >= c["held_min"] - tol
    fresh = share <= c["fresh_max"] + tol
    klass = np.where(held, "held", np.where(fresh, "fresh", "mixed"))
    for nm in ("held", "fresh", "mixed"):
        cnt[nm] = int((klass == nm).sum())
    m12 = b._mid12(store, k, j["market_id"])
    d24, d24f = b._own24(sx, j["mid"].to_numpy(float), m12)
    tick = j["tick"].to_numpy(float)
    rv, rvs, rvf = _rv24(store, k, mkj.to_numpy(), tick, c)
    vol_k, vol_kmiss = _vol_cols(j["vol24"])
    chg = j["chg_1h"].to_numpy(float)
    sxchg = sx * chg
    u = pd.DataFrame({**b._base_out(j, cap, k), "t_row": j["t_row"].to_numpy(float), "x": x, "sx": sx, "cls": j["cls"].to_numpy(), "geom": j["geom"].to_numpy(),
                      "mid": j["mid"].to_numpy(float), "tick": tick, "liq": j["liq"].to_numpy(float), "end_ts": j["end_ts"].to_numpy(float), "vol24": j["vol24"].to_numpy(float),
                      "n_members": j["n_members"].to_numpy(float), "early": early, "late": late, "early_share": share, "held": held.astype(float), "fresh": fresh.astype(float),
                      "klass": klass, "lag_s": (float(cap["start"]) - j["s_t_1"].to_numpy(float)) / 60.0,
                      "lag_g": (j["s_t_1"].to_numpy(float) - ser_p["t_row"].reindex(mkj).to_numpy(float)) / 60.0, "spread": j["spread"].to_numpy(float),
                      "spread_sw": (j["sask_1"] - j["sbid_1"]).to_numpy(float), "log1p_vol": vol_k, "vol_missing": vol_kmiss, "d24": d24, "d24_flag": d24f, "rv24s": rvs, "rv_floor": rvf,
                      "sx_chg1h": np.where(np.isfinite(sxchg), sxchg, 0.0), "chg1h_missing": (~np.isfinite(sxchg)).astype(float), "ltp_missing": (~np.isfinite(j["ltp"].to_numpy(float))).astype(float),
                      "x_ticks": np.abs(x) / tick, "fee_cat": j["fee_cat"].to_numpy(object)})
    u["log_abs_x"] = np.log(np.abs(u["x"]))
    u = b._anatomy(b._common_cols(u))
    u["log_rv24s"] = np.log(u["rv24s"])
    u = _drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "tick": "tick_unknown"})
    cnt["units_pre_exclusion_family"] = len(u)
    return u, cnt


# --- CH204 the market's own clock (design 4) ---------------------------------------------------------------------------------------


def sched_state(M: np.ndarray, k: int, c: dict) -> dict:
    """The schedule state of CH204 (section 4) from ``M`` = (n_markets, 85) mids at slots k - 84 .. k (NaN where a slot or the market is
    absent). ``|Delta_i|`` is observed when both mids are; ``covered`` needs >= 70 of the 84 changes; ``m_s`` (slot of day s of interval i =
    ``i mod 12``) is NaN with fewer than 5 of its 7 intervals observed; ``sc_conc = max m_s / sum m_s`` and ``s* = argmax`` (ties: not
    scheduled); the 7 rolling days (intervals k - 12 d + 1 .. k - 12 (d - 1)) COUNT when their largest observed ``|Delta|`` >= 0.01 and carry an
    argmax slot (ties, and a day that does not count: none). **Scheduled** = covered, all twelve ``m_s`` defined, ``sc_conc >= 0.35`` (inclusive,
    float noise 1e-12), no tie, and the day argmax equals ``s*`` on >= 4 of the 7 days."""
    n = M.shape[0]
    L = c["lookback_changes"]
    A = np.abs(M[:, 1:] - M[:, :-1])
    obs = np.isfinite(A)
    n_obs = obs.sum(axis=1)
    covered = n_obs >= c["min_observed_changes"]
    sig = (k - (L - 1) + np.arange(L)) % 12  # slot of day of the interval ending at column c
    A0 = np.where(obs, A, 0.0)
    m = np.full((n, 12), np.nan)
    for s in range(12):
        cols = np.flatnonzero(sig == s)
        n_s = obs[:, cols].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            m[:, s] = np.where(n_s >= c["slot_min_obs_of_7"], A0[:, cols].sum(axis=1) / np.maximum(n_s, 1), np.nan)
    all12 = np.isfinite(m).all(axis=1)
    tot = np.where(all12, np.nansum(m, axis=1), np.nan)
    mx = np.where(all12, np.nanmax(np.where(np.isfinite(m), m, -np.inf), axis=1), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        conc = np.where(all12 & (tot > 0), mx / tot, np.nan)
    star = np.where(all12, np.argmax(np.where(np.isfinite(m), m, -np.inf), axis=1), -1)
    tie = all12 & ((np.abs(m - mx[:, None]) <= c["tie_tol"]).sum(axis=1) > 1)
    D = c["days"]
    Ad = np.where(obs, A, -np.inf).reshape(n, D, 12)
    dmax = Ad.max(axis=2)
    day_ok = np.isfinite(dmax) & (dmax >= c["day_move_min"] - 1e-12)
    with np.errstate(invalid="ignore"):
        dtie = (np.abs(Ad - dmax[:, :, None]) <= c["tie_tol"]).sum(axis=2) > 1
    dpos = Ad.argmax(axis=2)
    day_slot = sig.reshape(D, 12)[0][dpos]  # every day has the same position -> slot mapping (84 = 7 x 12)
    match = (day_ok & ~dtie & (day_slot == star[:, None])).sum(axis=1)
    sched = covered & all12 & np.isfinite(conc) & (conc >= c["sc_conc_min"] - 1e-12) & ~tie & (match >= c["argmax_days_min"])
    return {"n_obs": n_obs, "covered": covered, "m": m, "sc_conc": conc, "s_star": star, "tie": tie, "match_days": match, "scheduled": sched, "all12": all12}


def qo_share(store: SlotStore8, k: int, markets, spec: dict, chunk: int = 3000) -> np.ndarray:
    """The market's quote-only share of its look-back movers (E015's anatomy over the week): over the 84 intervals with ``|Delta| >= 0.01``,
    the share classed ``quote_only`` by LT3's ``classify`` (last trade and ``volume24hr`` only; the mid stands in for bid and ask). NaN with no
    mover."""
    c = spec["tests"]["CH204"]
    mk = np.asarray(markets)
    out = np.full(len(mk), np.nan)
    for s0 in range(0, len(mk), chunk):
        sl = mk[s0:s0 + chunk]
        mid = store.matrix(k, c["lookback_changes"], sl, "mid")
        ltp = store.matrix(k, c["lookback_changes"], sl, "ltp")
        vol = store.matrix(k, c["lookback_changes"], sl, "vol")
        d = mid[:, 1:] - mid[:, :-1]
        with np.errstate(invalid="ignore"):
            mover = np.isfinite(d) & (np.abs(d) >= c["qo_move_min"] - 1e-12)
        mp, mc = mid[:, :-1].ravel(), mid[:, 1:].ravel()
        cls, _ = b.classify(mp, mp, mc, mc, ltp[:, :-1].ravel(), ltp[:, 1:].ravel(), vol[:, :-1].ravel(), vol[:, 1:].ravel(), spec)
        qo = (np.asarray(cls).reshape(d.shape) == "quote_only") & mover
        nm = mover.sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[s0:s0 + chunk] = np.where(nm > 0, qo.sum(axis=1) / np.maximum(nm, 1), np.nan)
    return out


def sched_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: SlotStore8, cap: dict, k: int, spec: dict) -> tuple[pd.DataFrame, dict]:
    """CH204's scheduled markets of capture k (section 4), BEFORE the member cap (the census needs the pre-cap count): non-sports ex-crypto
    markets two-sided and tight at k - 1 and k (1.4 items 1-7, ``mid_k`` in [0.05, 0.95], end > t + 7 h) with at least 70 of the 84
    look-back changes observed and classed scheduled. ``sc_hot = 1[sigma(k + 2) = s*]`` and ``sc_rot`` are calendar facts of the target
    interval (k + 1, k + 2]; nothing of capture k + 1 or k + 2 is read. Counts: eligible, ``lookback_covered`` / ``lookback_missing``, ties,
    scheduled, the ``sc_conc`` histogram of covered markets."""
    c = spec["tests"]["CH204"]
    j, cnt = b._movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = b._non_sports_ex_crypto(j.copy(), cnt)
    cnt["eligible"] = len(j)
    mk = j["market_id"].astype(str).to_numpy()
    M = store.matrix(k, c["lookback_changes"], mk, "mid")
    st = sched_state(M, k, c)
    cnt["lookback_covered"] = int(st["covered"].sum())
    cnt["lookback_missing"] = int((~st["covered"]).sum())
    cnt["tie_not_scheduled"] = int((st["covered"] & st["tie"]).sum())
    hist: dict = {}
    for v in st["sc_conc"][st["covered"] & np.isfinite(st["sc_conc"])]:
        key = f"{min(int(v / 0.05), 19) * 0.05:.2f}"
        hist[key] = hist.get(key, 0) + 1
    cnt["sc_conc_hist"] = hist
    sel = st["scheduled"]
    cnt["scheduled"] = int(sel.sum())
    j = j[sel].reset_index(drop=True)
    if j.empty:
        return pd.DataFrame(), cnt
    Msel = M[sel]
    mkj = j["market_id"].astype(str).to_numpy()
    star = st["s_star"][sel]
    tgt = (k + 2) % 12
    hot = (star == tgt).astype(float)
    rot = (star == (tgt + 6) % 12).astype(float)
    tick = j["tick"].to_numpy(float)
    rv24, _ = b.rv_from_matrix(Msel[:, -(c["rv24_window"] + 1):], c["rv24_min_obs"])
    rvs, rvf = b.floored_rv(rv24, tick, c["rv_floor_ticks"])
    rv7, _ = b.rv_from_matrix(Msel, c["rv7d_min_obs"])
    rv7s, _ = b.floored_rv(rv7, tick, c["rv_floor_ticks"])
    vol_k, vol_kmiss = _vol_cols(j["vol24"])
    qo = qo_share(store, k, mkj, spec)
    mid = j["mid"].to_numpy(float)
    msel = st["m"][sel]
    u = pd.DataFrame({**b._base_out(j, cap, k), "t_row": j["t_row"].to_numpy(float), "mid": mid, "tick": tick, "liq": j["liq"].to_numpy(float), "end_ts": j["end_ts"].to_numpy(float),
                      "vol24": j["vol24"].to_numpy(float), "n_members": j["n_members"].to_numpy(float), "spread": j["spread"].to_numpy(float), "s_star": star.astype(float),
                      "sc_conc": st["sc_conc"][sel], "sc_hot": hot, "sc_rot": rot, "hot_m": msel[np.arange(len(star)), star], "log1p_vol": vol_k, "vol_missing": vol_kmiss,
                      "rv24s": rvs, "rv_floor": rvf, "rv7ds": rv7s, "qo_share": qo, "ltp_missing": (~np.isfinite(j["ltp"].to_numpy(float))).astype(float),
                      "fee_cat": j["fee_cat"].to_numpy(object), "target_slot_of_day": float(tgt)})
    for s in range(1, 12):  # the 11 slot-of-day dummies of sigma(k + 2) (slot 0 the base)
        u[f"sd{s}"] = float(tgt == s)
    u = b._common_cols(u)
    u["log_rv24s"], u["log_rv7d"] = np.log(u["rv24s"]), np.log(u["rv7ds"])
    u = _drop_missing(u, cnt, {"log_rv24s": "rv24_undefined", "log_rv7d": "rv7d_undefined", "tick": "tick_unknown", "qo_share": "qo_share_undefined"})
    cnt["scheduled_units_pre_cap"] = len(u)
    return u, cnt


# --- design-based MDEs under a working covariance (design 7, R1 should-fix "define declared") --------------------------------------


def design_se(df: pd.DataFrame, terms: list[str], controls: list[str], contrast: dict, rho: float, scale: float) -> float:
    """Standard error of a linear combination (``contrast``: column -> weight) of the tested coefficients in the primary model fitted on the
    census units' expanding-past-demeaned regressors (controls included, intercept), computed from the regressors alone under a working
    covariance of the errors with unit variance, within-event equicorrelation ``rho`` and independence across events, projected to the
    21-day window with events recurring (every count and cluster size multiplied by ``scale``): ``Var = (1 - rho) / scale x (X'X)^-1 + rho x
    (X'X)^-1 S (X'X)^-1`` with ``S`` the sum over events of the outer product of the event's regressor sums. No target is read. NaN when
    the design cannot be formed."""
    cols = [*terms, *controls]
    d = df[["market_id", "event_id", "t_row", *cols]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < len(cols) + 10:
        return float("nan")
    X = b.demean(d, cols, "market_id", "t_row", "expanding").replace([np.inf, -np.inf], np.nan).dropna()
    if len(X) < len(cols) + 10:
        return float("nan")
    A = np.column_stack([np.ones(len(X)), X[cols].to_numpy()])
    inv = np.linalg.pinv(A.T @ A)
    codes, _ = pd.factorize(d.loc[X.index, "event_id"].astype(str).to_numpy())
    C = np.zeros((int(codes.max()) + 1, A.shape[1]))
    np.add.at(C, codes, A)
    S = C.T @ C
    V = (1.0 - rho) / scale * inv + rho * (inv @ S @ inv)
    cvec = np.zeros(A.shape[1])
    for name, w in contrast.items():
        cvec[1 + cols.index(name)] = w
    var = float(cvec @ V @ cvec)
    return math.sqrt(var) if var > 0 else float("nan")


def slope_mde8(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float, gap: float) -> dict:
    """Slope MDE at the census tercile gap, cents: ``max(declared, design)`` per SD of the standardised ``term`` times the gap. *declared* =
    the closed formula at the census's own ``n_eff``, ``DE_gate``, ``VIF_w`` and the declared SD; *design* = ``t_sum x day_factor x SD x
    se_1`` (:func:`design_se`). NaN anywhere gives inf (the gate fails)."""
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    pe = pop[eff] if len(pop) else pop
    dsg = b.design_ss(pe, term, controls) if len(pop) else {"n": 0, "ss_resid": float("nan"), "vif_w": float("nan")}
    n_eff = float(eff.sum()) * scale
    declared = b.mde_slope_declared(n_eff, sd, de_gate, a, dsg["vif_w"])
    se = design_se(pe, [term], controls, {term: 1.0}, float(a["de_rho"]), scale) if len(pop) else float("nan")
    design = a["t_sum"] * a["day_factor"] * sd * se if np.isfinite(se) else float("inf")
    per_sd = max(declared, design) if np.isfinite(declared) else float("inf")
    mde_c = per_sd * gap * 100.0 if np.isfinite(gap) and np.isfinite(per_sd) else float("inf")
    return {"design_ss": dsg, "n_eff_projected": n_eff, "declared_per_sd_c": declared * 100.0 if np.isfinite(declared) else float("inf"),
            "design_per_sd_c": design * 100.0 if np.isfinite(design) else float("inf"), "se_1": se, "mde_per_sd_c": per_sd * 100.0 if np.isfinite(per_sd) else float("inf"),
            "mde_tercile_c": mde_c}


def class_mde8(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float) -> dict:
    """Class-contrast MDE, cents: ``max(declared, design)``. *declared* = ``3.47 x SD x sqrt(1/n1 + 1/n2) x sqrt(DE_gate) x 1.5 x sqrt(max(1,
    VIF_w))`` on the projected effective class counts; *design* = ``t_sum x day_factor x SD x se_1`` of the class coefficient."""
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    pe = pop[eff] if len(pop) else pop
    g = pe[term].to_numpy(float) if len(pop) else np.array([])
    n1, n2 = float((g == 1).sum()) * scale, float((g == 0).sum()) * scale
    dsg = b.design_ss(pe, term, controls) if len(pop) else {"n": 0, "ss_resid": float("nan"), "vif_w": float("nan")}
    vif = dsg["vif_w"]
    declared = b.mde_class(n1, n2, sd, de_gate, a, vif) * 100.0 if np.isfinite(vif) else float("inf")
    se = design_se(pe, [term], controls, {term: 1.0}, float(a["de_rho"]), scale) if len(pop) else float("nan")
    design = a["t_sum"] * a["day_factor"] * sd * se * 100.0 if np.isfinite(se) else float("inf")
    return {"design_ss": dsg, "n1_eff_projected": n1, "n2_eff_projected": n2, "declared_c": declared, "design_c": design, "se_1": se,
            "mde_class_c": float(max(declared, design)) if np.isfinite(declared) else float("inf")}


def f_mde8(slope_c: float, r_gate: float, a: dict, *, pop: pd.DataFrame | None = None, controls: list[str] | None = None, scale_f: float = float("nan"),
           sd: float = 0.0, gap: float = float("nan")) -> dict:
    """CH203's F-MDE (design 7): ``max(declared, design)``. Declared = the gated slope MDE x ``sqrt(2 / (1 - max(0, r_gate)))``. Design = ``t_sum x
    day_factor x SD x se(Delta) x gap`` with ``Delta = beta(zdimb5) - beta(zdimb5_lag)`` in the arm model fitted on the units that carry the lag,
    projected with the pairs' own scale ``scale_f``. NaN anywhere gives inf."""
    if not (np.isfinite(slope_c) and np.isfinite(r_gate)):
        return {"declared_c": float("inf"), "design_c": float("inf"), "f_mde_c": float("inf"), "r_gate": r_gate}
    declared = slope_c * math.sqrt(2.0 / (1.0 - max(0.0, r_gate))) if r_gate < 1.0 else float("inf")
    design = float("inf")
    if pop is not None and len(pop) and np.isfinite(scale_f) and np.isfinite(gap):
        eff = b._eff(pop)
        se = design_se(pop[eff], ["zdimb5", "zdimb5_lag"], controls or [], {"zdimb5": 1.0, "zdimb5_lag": -1.0}, float(a["de_rho"]), scale_f)
        design = a["t_sum"] * a["day_factor"] * sd * se * gap * 100.0 if np.isfinite(se) else float("inf")
    return {"declared_c": declared, "design_c": design, "f_mde_c": float(max(declared, design)) if np.isfinite(design) else float("inf"), "r_gate": r_gate}


# --- censuses (counts only; the gates exactly as written in section 7) -------------------------------------------------------------


CONTROLS_203 = ["zimb5_km1", "log1p_total5", "dlogD5", "spread_sw", "lag_s", "logit_mid", "abs_dev", "log1p_vol", "vol_missing", "dV_prev", "dvp_missing", "d24", "d24_flag",
                "log_rv24s", "rv_floor", "tick001", "log_hte", "hte_unknown", "rewarded", "in_band", "ft_both", "rw_changed"]
CONTROLS_202 = ["a_traded", "a_parallel", "a_one_sided", "a_spread_change", "log_abs_x", "sx_chg1h", "chg1h_missing", "spread", "spread_sw", "lag_s", "logit_mid", "abs_dev",
                "log1p_vol", "vol_missing", "d24", "d24_flag", "log_rv24s", "rv_floor", "tick001", "log_hte", "hte_unknown"]
CONTROLS_204 = [*(f"sd{s}" for s in range(1, 12)), "log_rv24s", "rv_floor", "log_rv7d", "spread", "logit_mid", "abs_dev", "log1p_vol", "vol_missing", "log_hte", "hte_unknown",
                "qo_share", "tick001"]


def _q(x, qs=(0.1, 0.5, 0.9)) -> list:
    v = np.asarray(x, float)
    v = v[np.isfinite(v)]
    return [float(t) for t in np.quantile(v, qs)] if len(v) else []


def _events8(pop: pd.DataFrame, scale: float, covered_days: float) -> dict:
    """Distinct events and the two projections of design 7: ``events x 21 / covered days`` (gated) and ``E_all + (E_all - E_day1) x (21 -
    covered_days)`` (printed)."""
    if pop.empty:
        return {"events": 0, "events_projected_21d": float("nan"), "events_projected_21d_second_form": float("nan"), "covered_days": covered_days}
    ev = pop["event_id"].astype(str)
    days = sorted(pop["day"].astype(str).unique())
    e_all = int(ev.nunique())
    e1 = int(ev[pop["day"].astype(str) == days[0]].nunique())
    second = float(e_all + (e_all - e1) * (21.0 - covered_days)) if np.isfinite(covered_days) else float("nan")
    return {"events": e_all, "events_day1": e1, "events_projected_21d": float(e_all * scale) if np.isfinite(scale) else float("nan"),
            "events_projected_21d_second_form": second, "covered_days": covered_days}


def _ev_share(pop: pd.DataFrame) -> dict:
    """Descriptive: the vol_missing share and its 2 x 2 table against a missing last_trade_price (R1 must-fix 8)."""
    if pop.empty:
        return {}
    vm, lm = pop["vol_missing"].to_numpy(float) == 1, pop["ltp_missing"].to_numpy(float) == 1
    return {"vol_missing_share": float(vm.mean()), "table_vol_missing_x_ltp_missing": {"vm1_lm1": int((vm & lm).sum()), "vm1_lm0": int((vm & ~lm).sum()), "vm0_lm1": int((~vm & lm).sum()),
                                                                                        "vm0_lm0": int((~vm & ~lm).sum())}}


def census_ch203(Q: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, pair_days: float, per_block: dict) -> dict:
    """CH203's census gate (design 7 table). ``Q`` = the quiet covered in-band units with their members (cap not yet applied)."""
    g, a = spec["census_gates"]["CS8_CH203"], b.mde_common(spec)
    ci = spec["census_inputs"]
    mind = ci["min_covered_days"]["CS8_CH203"]
    fail = {"error": "no units", "gate_CH203": {"pass": False}}
    if Q.empty:
        return _gate_blocks(b._gate_min_days(fail, "gate_CH203", covered_days, mind), "gate_CH203", per_block, spec)
    cap_n = spec["member_cap"]["max_members"]
    elig, cov = tot.get("eligible_in_band", 0), tot.get("covered_in_band", 0)
    struct = tot.get("covered_struct_in_band", 0)
    coverage = cov / elig if elig else float("nan")
    received = cov / struct if struct else float("nan")
    quiet_n = tot.get("quiet_covered_in_band", 0)
    quiet_share = quiet_n / cov if cov else float("nan")
    quiet_pre = tot.get("quiet_covered_pre_band", 0) * scale
    cap_share = tot.get("quiet_covered_in_band_cap", 0) / quiet_n if quiet_n else float("nan")
    P = Q[Q["n_members"] <= cap_n]
    pop, excl, top = b._fam(P, a["family_cap"])
    pop = pop.copy()
    c_d, s_d = b.standardise(pop["dimb5"])
    c_i, s_i = b.standardise(pop["imb5_km1"])
    pop["zdimb5"], pop["zdimb5_lag"] = b._z(pop["dimb5"], c_d, s_d), b._z(pop["dimb5_lag"], c_d, s_d)
    pop["zimb5_km1"] = b._z(pop["imb5_km1"], c_i, s_i)
    pop["z_d24"] = b._z(pop["d24"], *b.standardise(pop["d24"]))
    pop["z_dV"] = b._z(pop["dV_prev"], *b.standardise(pop["dV_prev"]))
    t1, t2, gap = b.terciles(pop["zdimb5"])
    de = b._de(pop, scale, g["de_floor"], a)
    sm = slope_mde8(pop, "zdimb5", CONTROLS_203, scale, a, de["DE_gate"], a[g["sd"]], gap)
    vif = sm["design_ss"]["vif_w"]
    ri = b.resid_iqr(pop, "dimb5", ["imb5_km1"], int(g["resid_iqr_min_units"]), g["resid_iqr_min"])
    corr = {nm: b.wcorr(pop, "zdimb5", col) for nm, col in (("own24", "z_d24"), ("dlogD5", "dlogD5"), ("ft_both", "ft_both"), ("dV_prev", "z_dV"))}
    cl = b.wcorr(pop, "zdimb5", "log1p_liq")
    bm = b.block_min_units(covered_days)
    bs = b.block_share(pop, bm)
    F = pop[np.isfinite(pop["dimb5_lag"].to_numpy(float))]
    pr = pd.DataFrame({"market_id": F["market_id"].to_numpy(), "t_row": F["t_row"].to_numpy(float), "imb_j": F["dimb5"].to_numpy(float), "imb_j13": F["dimb5_lag"].to_numpy(float)})
    pc = b.pair_correlations(pr, int(g["pair_min_per_market"]))
    scale_f = 21.0 / pair_days if pair_days else float("nan")
    fm = f_mde8(sm["mde_tercile_c"], pc["r_gate"], a, pop=F, controls=CONTROLS_203, scale_f=scale_f, sd=a[g["sd"]], gap=gap)
    projected_pre = float(len(P) * scale)
    projected = float(len(pop) * scale)
    pair_ok = bool(np.isfinite(pair_days) and pair_days >= g["pair_min_days"] and pc["markets"] >= g["pair_markets_min"] and np.isfinite(pc["r_gate"]) and pc["r_gate"] <= g["r_gate_max"])
    res = {"units_pre_cap": len(Q), "units_primary": len(P), "projected_units_21d": projected_pre, "projected_units_21d_after_family_exclusion": projected,
           "sweep_coverage": coverage, "received_before_origin_share": received, "quiet_share": quiet_share, "projected_quiet_covered_pre_band": quiet_pre, "cap_share": cap_share,
           "exclude_family": excl, "top_family_share": top, "dimb5": {"centre": c_d, "scale": s_d}, "imb5_km1": {"centre": c_i, "scale": s_i}, "zdimb5": {"terciles": [t1, t2], "tercile_gap": gap},
           "design_effect": de, "slope": sm, "F": fm, "pairs": pc, "pair_days": pair_days, "resid_iqr": ri, "vif_w": vif, "corr": corr, "corr_liq": cl, "block_min_units": bm, "block_share": bs,
           "events": _events8(pop, scale, covered_days), "t_sum_used": a["t_sum"], "splits": b._desc_splits(tot), "per_market": b._per_market(pop["market_id"]),
           "vol_missing": _ev_share(pop), "liquidity_tiers_top_zdimb5_share": b._tier_shares(pop, "", "zdimb5"),
           "rewarded_share": float(pop["rewarded"].mean()), "ft_both_share": float(pop["ft_both"].mean()), "silent_arm_share": float(pop["silent"].mean()),
           "n_members_dist": {str(int(v_)): int(n_) for v_, n_ in Q["n_members"].clip(upper=11).value_counts().sort_index().items()}, "ladder_loss": 1.0 - cap_share if np.isfinite(cap_share) else float("nan"),
           "quantiles": {nm: _q(pop[nm]) for nm in ("imb5_km1", "dimb5", "dimb1", "dlev", "lag_s")}, "pairs_per_market_hist": b._per_market(F["market_id"])["units_per_market_hist"] if len(F) else {},
           "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_CH203"] = b._gate({
        "coverage": bool(np.isfinite(coverage) and coverage >= g["coverage_min"]), "received_before": bool(np.isfinite(received) and received >= g["received_before_min"]),
        "quiet_share": bool(np.isfinite(quiet_share) and quiet_share >= g["quiet_share_min"]), "quiet_covered_projected": bool(quiet_pre >= g["quiet_covered_projected_min"]),
        "units": bool(projected >= g["units_projected_min"]), "cap_share": bool(np.isfinite(cap_share) and cap_share >= g["cap_share_min"]), "resid_iqr": b.iqr_ok(ri, g),
        "vif_w": bool(np.isfinite(vif) and vif <= g["vif_w_max"]), **{f"corr_{nm}": b.corr_ok(c_, g["corr_max"]) for nm, c_ in corr.items()},
        "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True), "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]), "r_gate": pair_ok,
        "slope_mde": bool(sm["mde_tercile_c"] <= a["mde_max"] * 100.0), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max"] * 100.0)})
    res = b._gate_min_days(res, "gate_CH203", covered_days, mind)
    return _gate_blocks(res, "gate_CH203", per_block, spec)


def census_ch202(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, per_block: dict) -> dict:
    """CH202's census gate (design 7 table). ``U`` = every covered mover (held, fresh and mixed)."""
    g, a = spec["census_gates"]["CS8_CH202"], b.mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CS8_CH202"]
    fail = {"error": "no units", "gate_CH202": {"pass": False}}
    if U.empty:
        return _gate_blocks(b._gate_min_days(fail, "gate_CH202", covered_days, mind), "gate_CH202", per_block, spec)
    movers = tot.get("movers_in_band", 0)
    covered = tot.get("covered", 0)
    coverage = covered / movers if movers else float("nan")
    held_share = tot.get("held", 0) / movers if movers else float("nan")
    fresh_share = tot.get("fresh", 0) / movers if movers else float("nan")
    chg_present = tot.get("chg1h_present", 0) / movers if movers else float("nan")
    contrast = U[U["klass"].isin(["held", "fresh"])]
    pop, excl, top = b._fam(contrast, a["family_cap"])
    pop = pop.copy()
    pop["z_log_abs_x"] = b._z(pop["log_abs_x"], *b.standardise(pop["log_abs_x"]))
    pop["z_d24"] = b._z(pop["d24"], *b.standardise(pop["d24"]))
    pop["z_sx_chg1h"] = b._z(pop["sx_chg1h"], *b.standardise(pop["sx_chg1h"]))
    de = b._de(pop, scale, g["de_floor"], a)
    cm = class_mde8(pop, "held", CONTROLS_202, scale, a, de["DE_gate"], a[g["sd"]])
    corr = {nm: b.wcorr(pop, "held", col) for nm, col in (("parallel", "a_parallel"), ("traded", "a_traded"), ("log_abs_x", "z_log_abs_x"), ("own24", "z_d24"))}
    corr_chg = b.wcorr(pop, "held", "z_sx_chg1h")
    cl = b.wcorr(pop, "held", "log1p_liq")
    bm = b.block_min_units(covered_days)
    bs = b.block_share(pop, bm)
    projected = float(len(pop) * scale)
    res = {"movers_in_band": movers, "covered_movers": covered, "contrasted_units": len(contrast), "projected_contrasted_units_21d": float(len(contrast) * scale),
           "projected_units_21d_after_family_exclusion": projected, "sweep_coverage": coverage, "held_share_of_movers": held_share, "fresh_share_of_movers": fresh_share,
           "held_share_of_covered": tot.get("held", 0) / covered if covered else float("nan"), "fresh_share_of_covered": tot.get("fresh", 0) / covered if covered else float("nan"),
           "chg1h_present_share": chg_present, "exclude_family": excl, "top_family_share": top, "design_effect": de, "class_mde": cm, "corr": corr, "corr_chg1h": corr_chg, "corr_liq": cl,
           "block_min_units": bm, "block_share": bs, "events": _events8(pop, scale, covered_days), "t_sum_used": a["t_sum"], "splits": b._desc_splits(tot),
           "per_market": b._per_market(pop["market_id"]), "vol_missing": _ev_share(pop), "liquidity_tiers_held_share": b._tier_shares(pop, "held"),
           "early_share_quantiles": _q(U["early_share"]), "early_share_mass": {"at_0": float((U["early_share"].abs() < 1e-9).mean()), "at_half": float(((U["early_share"] - 0.5).abs() < 1e-9).mean()),
                                                                                    "at_1": float(((U["early_share"] - 1.0).abs() < 1e-9).mean())},
           "class_by_anatomy": {f"{k_}:{c_}": int(n_) for (k_, c_), n_ in U.groupby(["klass", "cls"]).size().items()}, "class_by_tick": {f"{k_}:{t_}": int(n_) for (k_, t_), n_ in U.groupby(["klass", "tick"]).size().items()},
           "two_tick_share": float((U["x_ticks"] >= 2.0 - 1e-9).mean()), "lag_g_quantiles": _q(U["lag_g"]), "lag_g_over_10min_share": float((U["lag_g"] > spec["tests"]["CH202"]["lag_g_fresh_minutes"]).mean()),
           "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_CH202"] = b._gate({
        "coverage": bool(np.isfinite(coverage) and coverage >= g["coverage_min"]), "units": bool(projected >= g["units_projected_min"]),
        "held_share": bool(np.isfinite(held_share) and held_share >= g["class_share_min"]), "fresh_share": bool(np.isfinite(fresh_share) and fresh_share >= g["class_share_min"]),
        **{f"corr_{nm}": b.corr_ok(c_, g["corr_max"]) for nm, c_ in corr.items()}, "corr_chg1h": b.corr_ok(corr_chg, g["corr_chg1h_max"]),
        "chg1h_present": bool(np.isfinite(chg_present) and chg_present >= g["chg1h_present_min"]), "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True),
        "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]), "class_mde": bool(cm["mde_class_c"] <= a["mde_max"] * 100.0)})
    res = b._gate_min_days(res, "gate_CH202", covered_days, mind)
    return _gate_blocks(res, "gate_CH202", per_block, spec)


def _norm_fee_cat(v) -> str:
    s = b._norm_cat(v)
    return "unknown" if s is None else s


def census_ch204(S: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, n_origins: int) -> dict:
    """CH204's census gate (design 7 table). ``S`` = every scheduled market of every covered origin BEFORE the member cap."""
    g, a = spec["census_gates"]["CC8_CH204"], b.mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CC8"]
    if S.empty:
        return b._gate_min_days({"error": "no units", "gate_CH204": {"pass": False}}, "gate_CH204", covered_days, mind)
    cap_n = spec["member_cap"]["max_members"]
    elig, cov = tot.get("eligible", 0), tot.get("lookback_covered", 0)
    lb = cov / elig if elig else float("nan")
    sched_per_capture = len(S) / n_origins if n_origins else float("nan")
    U = S[S["n_members"] <= cap_n]
    cap_share = len(U) / len(S)
    pop, excl, top = b._fam(U, a["family_cap"])
    pop = pop.copy()
    hot_pre = float(U["sc_hot"].sum() * scale)
    hot = float(pop["sc_hot"].sum() * scale)
    ev = _events8(S, scale, covered_days)
    star_top = float(S["s_star"].value_counts(normalize=True).iloc[0])
    cats = U["fee_cat"].map(_norm_fee_cat).value_counts(normalize=True)
    cat_top = float(cats.iloc[0]) if len(cats) else float("nan")
    de = b._de(pop, scale, g["de_floor"], a)
    cm = class_mde8(pop, "sc_hot", CONTROLS_204, scale, a, de["DE_gate"], a[g["sd"]])
    corr_rv = b.wcorr(pop, "sc_hot", "log_rv24s")
    cl = b.wcorr(pop, "sc_hot", "log1p_liq")
    bm = b.block_min_units(covered_days)
    bs = b.block_share(pop, bm)
    k_ = S["slot"].to_numpy(int)
    later = S[["market_id", "slot", "s_star"]].assign(slot=S["slot"] - 12)
    again = S[["market_id", "slot", "s_star"]].merge(later, on=["market_id", "slot"], suffixes=("", "_12"))
    persist = float((again["s_star"] == again["s_star_12"]).mean()) if len(again) else float("nan")
    res = {"origins": n_origins, "eligible": elig, "lookback_covered": cov, "lookback_coverage": lb, "scheduled_markets": len(S), "scheduled_per_capture": sched_per_capture,
           "scheduled_units_pre_family": len(U), "cap_share": cap_share, "projected_hot_units_21d_pre_family": hot_pre, "projected_hot_units_21d": hot,
           "projected_units_21d": float(len(pop) * scale), "exclude_family": excl, "top_family_share": top, "events": ev, "venue_clock_top_share": star_top,
           "category_top_share": cat_top, "category_arms_triggered": bool(np.isfinite(cat_top) and cat_top > g["category_arms_trigger"]),
           "category_shares": {str(k2): float(v2) for k2, v2 in cats.head(10).items()}, "design_effect": de, "class_mde": cm, "corr_rv24": corr_rv, "corr_liq": cl,
           "block_min_units": bm, "block_share": bs, "t_sum_used": a["t_sum"], "splits": b._desc_splits(tot), "per_market": b._per_market(pop["market_id"]), "vol_missing": _ev_share(pop),
           "sc_conc_quantiles": _q(S["sc_conc"]), "sc_conc_hist_covered": tot.get("sc_conc_hist", {}), "scheduled_share_of_covered": len(S) / cov if cov else float("nan"),
           "s_star_distribution": {str(int(k2)): int(v2) for k2, v2 in S["s_star"].value_counts().sort_index().items()},
           "s_star_1231_share": float((S["s_star"] == 6).mean()), "still_scheduled_same_s_star_12_origins_later": persist, "hot_slot_mean_move_share": float(S["sc_conc"].mean()),
           "liquidity_tiers_hot_share": b._tier_shares(pop, "sc_hot"), "counts": {k2: v2 for k2, v2 in tot.items() if isinstance(v2, (int, float))}}
    del k_
    res["gate_CH204"] = b._gate({
        "lookback_coverage": bool(np.isfinite(lb) and lb >= g["lookback_coverage_min"]), "scheduled_per_capture": bool(np.isfinite(sched_per_capture) and sched_per_capture >= g["scheduled_per_capture_min"]),
        "hot_units": hot >= g["hot_units_projected_min"], "events": bool(np.isfinite(ev["events_projected_21d"]) and ev["events_projected_21d"] >= g["events_projected_min"]),
        "cap_share": cap_share >= g["cap_share_min"], "venue_clock": star_top <= g["venue_clock_max"], "category": bool(np.isfinite(cat_top) and cat_top <= g["category_max"]),
        "corr_rv24": b.corr_ok(corr_rv, g["corr_max"]), "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True), "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]),
        "class_mde": bool(cm["mde_class_c"] <= a["mde_max"] * 100.0)})
    return b._gate_min_days(res, "gate_CH204", covered_days, mind)


# --- the LT8 seal (derived from LT7's seal; design 7 and 8.1) -----------------------------------------------------------------------


def _lt7_seal_path(spec: dict) -> Path:
    p = Path(spec["census_inputs"]["lt7_seal"])
    return p if p.is_absolute() else ROOT / p


def bound_violations8(seal: dict, spec: dict) -> list[dict]:
    """Refuse anything at or after the sealed bound (``census_inputs.refuse_at_or_after_utc``): the span itself and every slot the seal assigns."""
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = []
    if epoch(spec["census_inputs"]["span"]["last_slot_utc"]) >= bound:
        bad.append({"what": "span.last_slot_utc", "error": "at or after the sealed bound"})
    for d, s in (seal.get("slots") or {}).items():
        if epoch(s) >= bound:
            bad.append({"what": d, "value": s, "error": "at or after the sealed bound"})
    if seal.get("written_utc") is None:
        bad.append({"what": "written_utc", "error": "seal not stamped"})
    return bad


def read_lt7_seal(spec: dict) -> tuple[dict | None, dict | None]:
    """(seal, error): the LT7 seal at its pinned sha256 with the structure the LT8 seal derives from (112 captures, 47 sweeps, 159 slots, 430
    needed files). Anything else refuses."""
    p = _lt7_seal_path(spec)
    if not p.exists():
        return None, {"error": f"LT7 source seal {p} is absent: refused"}
    got, want = sha256_file(p), spec["census_inputs"]["lt7_seal_sha256"]
    if got != want:
        return None, {"error": "LT7 source seal sha256 differs from the pinned one: refused", "got": got, "pinned": want}
    s7 = json.loads(p.read_text())
    ex = spec["census_inputs"]["expected"]
    caps, sws = b.sealed_dirs(s7, "snapshots"), b.sealed_dirs(s7, "book_sweeps")
    n_files = sum(len(v) for v in caps.values()) + sum(len(v) for v in sws.values())
    got_counts = {"captures": len(caps), "sweeps": len(sws), "slots": len(s7.get("slots", {})), "needed_files": n_files}
    if any(got_counts[k_] != ex[k_] for k_ in got_counts) or set(s7.get("slots", {})) != set(caps) | set(sws):
        return None, {"error": "LT7 source seal does not have the 112 captures / 47 sweeps / 159 slots / 430 files the design names (7): refused", "got": got_counts, "expected": {k_: ex[k_] for k_ in got_counts}}
    return s7, None


def resolve_inputs(s7: dict, snapshot_roots, sweep_roots, unavailable: set[str]) -> dict:
    """Per sealed directory (capture or sweep 1) of LT7's seal: the first root in which EVERY sealed file of the directory exists (host
    copies first, then restore trees). Each file is hashed against LT7's sha256 (a mismatch refuses). A directory with a file absent from
    every root refuses unless the path is listed in ``unavailable`` (a restore report says no release holds it): then the directory is not
    selected (counted missing, never substituted). Hashes bytes only."""
    out = {"files": {}, "absent": [], "mismatch": [], "unavailable_used": [], "missing_dirs": [], "ok_dirs": []}
    cache: dict[str, str] = {}

    def hsha(p: Path) -> str:
        key = str(p)
        if key not in cache:
            cache[key] = sha256_file(p)
        return cache[key]

    for sub, roots in (("snapshots", b._roots(snapshot_roots)), ("book_sweeps", b._roots(sweep_roots))):
        for d, rels in sorted(b.sealed_dirs(s7, sub).items()):
            home = next((r for r in roots if all((r / d / rel.rsplit("/", 1)[1]).exists() for rel in rels)), None)
            if home is None:
                gone = [rel for rel in rels if not any((r / d / rel.rsplit("/", 1)[1]).exists() for r in roots)]
                if not gone:  # every file exists somewhere but no root holds the whole directory: a split directory is refused
                    out["absent"].extend(rels)
                for rel in gone:
                    (out["unavailable_used"] if rel in unavailable else out["absent"]).append(rel)
                out["missing_dirs"].append(d)
                continue
            bad = False
            for rel in rels:
                want = s7["files"][rel]["sha256"]
                got = hsha(home / d / rel.rsplit("/", 1)[1])
                if got != want:
                    out["mismatch"].append({"file": rel, "want": want, "got": got})
                    bad = True
            if bad:
                continue
            if any(rel in unavailable for rel in rels):  # listed unavailable yet present: the report is stale; the files are verified, so they are used
                pass
            for rel in rels:
                e = {"sha256": s7["files"][rel]["sha256"], "root": str(home)}
                if "capture" in s7["files"][rel]:
                    e["capture"] = s7["files"][rel]["capture"]
                out["files"][rel] = e
            out["ok_dirs"].append(d)
    return out


def seal_inputs(*, snapshot_root, sweep_root, work: Path | None = None, spec: dict | None = None, unavailable=None) -> dict:
    """The LT8 seal (design 7): LT7's seal (pinned sha256 117e9b45...) narrowed to the 430 files the censuses open (112 captures x 3, 47 sweeps
    x 2; the 69 trade-sample files are not used), each re-hashed in the host copy or restore tree and required to equal LT7's sha256. Refuses
    unless the frozen LT8 design text is intact. A sealed file absent from every root refuses the seal unless it is listed in ``unavailable`` (the
    restore report's ``missing`` list). Records LT7's 159-entry ``slots`` map exactly, the frozen design hash and the spec's census blocks."""
    spec = spec or load_spec(sha=None)
    if (derr := design_text_error()):
        return derr
    s7, err = read_lt7_seal(spec)
    if err:
        return err
    viol = bound_violations8(s7, spec)
    if viol:
        return {"error": "LT7 seal violates the sealed bound: LT8 seal refused", "bad": viol[:20]}
    unavail = b.load_unavailable(unavailable) if not isinstance(unavailable, set) else unavailable
    res = resolve_inputs(s7, snapshot_root, sweep_root, unavail)
    if res["mismatch"]:
        return {"error": "hash mismatch against the LT7 seal: LT8 seal refused", "mismatches": res["mismatch"][:50], "n_mismatches": len(res["mismatch"])}
    if res["absent"]:
        return {"error": "a sealed file is absent from every root: LT8 seal refused (restore it, or list it with --unavailable from q0620's restore report)",
                "absent": sorted(set(res["absent"]))[:50], "n_absent": len(set(res["absent"]))}
    caps, sws = b.sealed_dirs(s7, "snapshots"), b.sealed_dirs(s7, "book_sweeps")
    miss_caps = [s7["slots"][d] for d in sorted(caps) if d in res["missing_dirs"]]
    miss_sws = [s7["slots"][d] for d in sorted(sws) if d in res["missing_dirs"]]
    slots = dict(s7["slots"])
    if slots != s7["slots"] or len(slots) != spec["census_inputs"]["expected"]["slots"]:
        return {"error": "the slots map differs from LT7's 159 entries: refused"}
    return {"purpose": "LT8 census inputs (LIVE_TESTS_8.md section 7): exactly the files the censuses open, each named in LT7's seal with an equal sha256; counts-only use",
            "written_utc": iso(b.now_ts()), "spec_sha256": sha256_file(SPEC_PATH), "design_text_sha256": design_text_sha(), "spec_blocks_sha256": spec_blocks_sha(spec),
            "source_seal": {"path": str(spec["census_inputs"]["lt7_seal"]), "sha256": sha256_file(_lt7_seal_path(spec)), "written_utc": s7.get("written_utc"), "design_text_sha256": s7.get("design_text_sha256"),
                            "n_files": s7.get("n_files"), "code_sha256": s7.get("code_sha256")},
            "span": spec["census_inputs"]["span"], "refuse_at_or_after_utc": spec["census_inputs"]["refuse_at_or_after_utc"], "slots": slots,
            "needs": {"captures": len(caps), "sweeps": len(sws), "files": sum(len(v) for v in caps.values()) + sum(len(v) for v in sws.values())},
            "unavailable_used": sorted(set(res["unavailable_used"])), "missing": {"captures": miss_caps, "sweeps": miss_sws}, "n_missing": {"captures": len(miss_caps), "sweeps": len(miss_sws)},
            "n_files": len(res["files"]), "files": dict(sorted(res["files"].items()))}


def restore_plan(*, snapshot_root, sweep_root, spec: dict | None = None) -> dict:
    """Which of the 430 needed files exist, hash-equal, in the given roots (host copies first), which are absent (to be restored by q0620) and
    which mismatch. Hashes bytes only; writes nothing."""
    spec = spec or load_spec(sha=None)
    s7, err = read_lt7_seal(spec)
    if err:
        return err
    res = resolve_inputs(s7, snapshot_root, sweep_root, set())
    need = sorted(set(res["absent"]) | {r for d in res["missing_dirs"] for sub in ("snapshots", "book_sweeps") for r in b.sealed_dirs(s7, sub).get(d, [])})
    return {"n_ok_dirs": len(res["ok_dirs"]), "n_missing_dirs": len(res["missing_dirs"]), "mismatch": res["mismatch"], "restore_paths": need, "n_restore_paths": len(need),
            "restore_dirs": sorted(res["missing_dirs"])}


def sealed_complete(seal: dict) -> tuple[set[str], set[str]]:
    """(capture directory names, sweep directory names) for which the seal names every file (rows, manifest, sidecar / rows, manifest)."""
    caps = {d for d, rels in b.sealed_dirs(seal, "snapshots").items() if len(rels) >= 3}
    sws = {d for d, rels in b.sealed_dirs(seal, "book_sweeps").items() if len(rels) >= 2}
    return caps, sws


def _seal_scan8(seal: dict, snapshot_root, sweep_root, work: Path, spec: dict) -> tuple[dict, dict]:
    """Complete captures and sweeps found locally, restricted to directories the seal names with all their files (a local directory the seal
    does not name, or names only in part because it was listed unavailable, is never opened: its slot counts as missing)."""
    by_slot, sweeps = b._scan(Path(work), snapshot_root, sweep_root, spec)
    caps, sws = sealed_complete(seal)
    by_slot = {k: c for k, c in by_slot.items() if c["id"] in caps}
    sweeps = {sid: v for sid, v in sweeps.items() if Path(v["dir"]).name in sws}
    return by_slot, sweeps


def _load_for_census(seal: Path, snapshot_root, sweep_root, work: Path, spec: dict):
    seal_d = json.loads(Path(seal).read_text())
    if (derr := design_text_error()) or seal_d.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        return seal_d, None, None, derr or {"error": "the seal was written against a different LIVE_TESTS_8.md: census refused", "seal_design_text_sha256": seal_d.get("design_text_sha256")}
    viol = bound_violations8(seal_d, spec)
    if viol:
        return seal_d, None, None, {"error": "sealed bound violated: census refused", "bad": viol, "n_bad": len(viol)}
    if seal_d.get("spec_blocks_sha256") != spec_blocks_sha(spec):
        return seal_d, None, None, {"error": "the spec's census blocks differ from those at seal time: census refused", "seal_blocks_sha256": seal_d.get("spec_blocks_sha256"), "spec_blocks_sha256": spec_blocks_sha(spec)}
    s7, err = read_lt7_seal(spec)
    if err:
        return seal_d, None, None, err
    if seal_d.get("slots") != s7["slots"]:
        return seal_d, None, None, {"error": "the seal's slots map differs from LT7's 159 entries: census refused"}
    if (seal_d.get("source_seal") or {}).get("sha256") != sha256_file(_lt7_seal_path(spec)):
        return seal_d, None, None, {"error": "the seal records a different LT7 source seal: census refused"}
    w = Path(work)
    if w.exists() and any(w.iterdir()):
        return seal_d, None, None, {"error": f"work directory {w} is not empty: a stale series file would be reused (census refused)"}
    by_slot, sweeps = _seal_scan8(seal_d, snapshot_root, sweep_root, Path(work), spec)
    return seal_d, by_slot, sweeps, None


def _sealed_sweep_slots(seal: dict, spec: dict) -> set[int]:
    return b.sealed_sweep_slots(seal, spec)


def _check_complete(seal_d: dict, by_slot: dict, sweeps: dict, caps: set[int], sws: set[int], spec: dict, sweep_root, verify: bool) -> dict:
    if not verify:
        return {"bad": [], "missing_slots": [], "n_missing_slots": 0, "files_checked": 0}
    if not (caps | sws):
        return {"bad": [], "missing_slots": [], "n_missing_slots": 0, "files_checked": 0}
    return b.seal_completeness(seal_d, by_slot, sweeps, caps, sws, spec, sweep_root)


def _ccf(L) -> pd.DataFrame:
    return pd.concat(L, ignore_index=True) if L else pd.DataFrame()


def census_captures(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CC8: CH204 (the market's own clock) on the sealed captures. Before anything is parsed: the design, bound, spec-block and source-seal
    checks, then every sealed capture in a needed slot must be present with every sealed file and every opened file must be sealed with an
    equal sha256, else the census is refused (L3). Slots with no sealed capture are counted as missing. Streaming: one capture at a time, a
    slot store of the last 85 slots (evicted), no per-run series cache. No sweep and no capture after the origin is read."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    seal_d, by_slot, _, err = _load_for_census(seal, snapshot_root, [], work, spec)
    if err:
        return err
    cap_slots = set(by_slot)
    ORG = origins_cc8(cap_slots, spec)
    L = spec["tests"]["CH204"]["lookback_changes"]
    need = {j for k in ORG for j in range(k - L, k + 1)} & cap_slots
    comp = _check_complete(seal_d, by_slot, {}, need, set(), spec, None, verify)
    if verify and comp["bad"]:
        return {"error": "input identity check failed (L3): census refused", "bad": comp["bad"][:50], "n_bad": len(comp["bad"])}
    store = SlotStore8()
    frames: dict[int, pd.DataFrame] = {}
    fee_counts: dict = {}
    S, tot = [], {}
    per_capture = []
    Oset = set(ORG)
    for k in sorted(need):
        cap = by_slot[k]
        write_series8(work, cap, spec)
        ser = b.read_series(work, cap["id"])
        store.add(k, ser)
        b._fee_counts(ser, fee_counts)
        frames[k] = ser
        for old in [s_ for s_ in frames if s_ < k - 1]:
            frames.pop(old)
        rec = {"capture": cap["id"]}
        if k in Oset:
            u, cnt = sched_units(ser, frames[k - 1], store, cap, k, spec)
            b._merge_counts(tot, cnt)
            if len(u):
                S.append(u)
            rec["CH204"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
        store.evict(k - L)
        per_capture.append(rec)
    fs = b.crypto_failsafe(fee_counts)
    if not fs["classifier_shown_to_work"]:
        return {"error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    days = len(ORG) / 12.0
    scale = 21.0 / days if days else float("nan")
    return {"span": spec["census_inputs"]["span"], "n_captures": len(by_slot), "inputs_verified": bool(verify), "missing_slots": comp.get("missing_slots"), "n_missing_slots": comp.get("n_missing_slots"),
            "files_checked": comp.get("files_checked"), "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"],
            "covered_origins": {"CH204": len(ORG)}, "expected_origins_from_file_list": spec["census_inputs"]["expected_origins_from_file_list"]["CC8"],
            "origins_differ_from_design": len(ORG) != spec["census_inputs"]["expected_origins_from_file_list"]["CC8"], "per_capture": per_capture,
            "CH204": census_ch204(_ccf(S), tot, spec, scale, days, len(ORG))}


def census_sweeps(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, sweep_root=SWEEP_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CS8: CH203 (the quiet book) and CH202 (the sweep clock) on the sealed sweeps and their captures. CH203's F-feasibility pairs read passes
    k + 5 and k + 6 ONLY through :func:`lag_sweep8` (keys + the two 5c depths). Per-market slot sums are not kept; the 13-slot slot store and
    the 3-slot series / sweep windows are evicted as the loop advances."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    seal_d, by_slot, sweeps, err = _load_for_census(seal, snapshot_root, sweep_root, work, spec)
    if err:
        return err
    cap_slots = set(by_slot)
    sw_slots = {k for k, c in by_slot.items() if c["id"] in sweeps} & _sealed_sweep_slots(seal_d, spec)
    org = origins_cs8(cap_slots, sw_slots)
    O203, O202, PAIRS = set(org["CH203"]), set(org["CH202"]), set(org["CH203_pairs"])
    full = {j for k in O203 | O202 for j in range(k - 12, k + 1)} & cap_slots
    lag_caps = {j for k in PAIRS for j in (k + 5, k + 6)} & cap_slots
    sweep_need = {j for k in O203 for j in (k - 2, k - 1)} | {k - 1 for k in O202} | {j for k in PAIRS for j in (k + 5, k + 6)}
    comp = _check_complete(seal_d, by_slot, sweeps, full | lag_caps, sweep_need & sw_slots, spec, sweep_root, verify)
    if verify and comp["bad"]:
        return {"error": "input identity check failed (L3): census refused", "bad": comp["bad"][:50], "n_bad": len(comp["bad"])}
    store = b.MidStore()
    frames: dict[int, pd.DataFrame] = {}
    rws: dict[int, pd.Series | None] = {}
    fee_counts: dict = {}
    sweep_cache: dict[int, pd.DataFrame] = {}
    lvl_cache: dict[int, pd.DataFrame] = {}
    Q203, U202, tot203, tot202 = [], [], {}, {}
    per_pass = []

    def sw_of(j: int) -> pd.DataFrame | None:
        if j not in by_slot or by_slot[j]["id"] not in sweeps:
            return None
        if j not in sweep_cache:
            sweep_cache[j] = b.sweep_frame(sweeps[by_slot[j]["id"]]["dir"], by_slot[j]["dir"]).set_index("market_id")
        return sweep_cache[j]

    def lv_of(j: int) -> pd.DataFrame | None:
        if j not in by_slot or by_slot[j]["id"] not in sweeps:
            return None
        if j not in lvl_cache:
            lvl_cache[j] = sweep_levels8(sweeps[by_slot[j]["id"]]["dir"], by_slot[j]["dir"])
        return lvl_cache[j]

    def lag_of(j: int) -> pd.DataFrame | None:
        if j not in by_slot or j not in sw_slots or by_slot[j]["id"] not in sweeps:
            return None
        return lag_sweep8(sweeps[by_slot[j]["id"]]["dir"], by_slot[j]["dir"])

    for k in sorted(full):
        cap = by_slot[k]
        write_series8(work, cap, spec)
        ser = b.read_series(work, cap["id"])
        store.add(k, ser)
        rws[k] = read_rw(work, cap["id"])
        b._fee_counts(ser, fee_counts)
        frames[k] = ser
        for old in [s_ for s_ in frames if s_ < k - 2]:
            frames.pop(old)
            rws.pop(old, None)
        for old in [s_ for s_ in store.slots if s_ < k - 12]:
            store.slots.pop(old)
        for old in [s_ for s_ in sweep_cache if s_ < k - 2]:
            sweep_cache.pop(old)
        for old in [s_ for s_ in lvl_cache if s_ < k - 2]:
            lvl_cache.pop(old)
        rec = {"capture": cap["id"]}
        if (k - 1) in frames and (k in O203 or k in O202):
            ser_p = frames[k - 1]
            if k in O203:
                q, cnt = quiet_units(ser, ser_p, frames.get(k - 2), rws.get(k), rws.get(k - 2), store, sw_of(k - 2), sw_of(k - 1), lv_of(k - 2), lv_of(k - 1), cap, k, spec)
                if k in PAIRS and len(q):
                    q = add_lag(q, lag_of(k + 5), lag_of(k + 6), spec)
                b._merge_counts(tot203, cnt)
                if len(q):
                    Q203.append(q)
                rec["CH203"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
            if k in O202:
                u, cnt = swclock_units(ser, ser_p, store, sw_of(k - 1), cap, k, spec)
                b._merge_counts(tot202, cnt)
                if len(u):
                    U202.append(u)
                rec["CH202"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
        per_pass.append(rec)
    fs = b.crypto_failsafe(fee_counts)
    if not fs["classifier_shown_to_work"]:
        return {"error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    d203, d202, dpair = len(O203) / 12.0, len(O202) / 12.0, len(PAIRS) / 12.0
    sc = lambda d: 21.0 / d if d else float("nan")  # noqa: E731
    Q, U = _ccf(Q203), _ccf(U202)
    exp = spec["census_inputs"]["expected_origins_from_file_list"]
    return {"inputs_verified": bool(verify), "missing_slots": comp.get("missing_slots"), "n_missing_slots": comp.get("n_missing_slots"), "files_checked": comp.get("files_checked"),
            "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"],
            "covered_origins": {"CH203": len(O203), "CH203_F_pairs": len(PAIRS), "CH202": len(O202)}, "expected_origins_from_file_list": {k_: exp[k_] for k_ in ("CH203", "CH203_F_pairs", "CH202")},
            "origins_differ_from_design": [len(O203), len(PAIRS), len(O202)] != [exp["CH203"], exp["CH203_F_pairs"], exp["CH202"]],
            "per_block_origins_pairs_printed": per_block_counts(sorted(PAIRS), spec), "per_pass": per_pass,
            "unit_overlaps": b.unit_overlaps({"CH203": Q[Q["n_members"] <= spec["member_cap"]["max_members"]] if len(Q) else Q, "CH202": U[U["klass"].isin(["held", "fresh"])] if len(U) else U}),
            "CH203": census_ch203(Q, tot203, spec, sc(d203), d203, dpair, per_block_counts(sorted(O203), spec)),
            "CH202": census_ch202(U, tot202, spec, sc(d202), d202, per_block_counts(sorted(O202), spec))}


# --- operational counts (never reads a price, a move, a state value or a target) ----------------------------------------------------


def _read_ops(path: Path, cols: list[str]) -> pd.DataFrame:
    bad = [c for c in cols if c not in OPS_COLS]
    if bad:
        raise ValueError(f"ops_stats may not read {bad}")
    head = pd.read_csv(path, nrows=0).columns
    use = [c for c in cols if c in head]
    return pd.read_csv(path, usecols=use) if use else pd.DataFrame()


def ops_stats(root: Path = OUT_ROOT) -> dict:
    """File, line, role, class and status counts of ``live_tests8/`` (design 1.6: the only thing that may run before the analysis date). The
    reader (phase 2) writes the files; this reads only the ``OPS_COLS`` columns, never a price, a move, a state value or a target."""
    root = Path(root)
    out: dict = {"root": str(root), "bytes": b.dir_bytes(root) if root.exists() else 0}
    for sub in ("series", "status", "sweeps", *(f"{k}/frozen" for k in KINDS), *(f"{k}/outcomes" for k in KINDS)):
        d = root / sub
        files = sorted(d.glob("*.csv.gz")) if d.exists() else []
        out[sub] = {"files": len([f for f in files if not f.name.endswith(MARKERS)]), **{s.split(".")[1]: len([f for f in files if f.name.endswith(s)]) for s in MARKERS}}
    counts, status = {}, {}
    cols = {"quiet": ["role", "sports", "crypto", "capflag", "lookback"], "swclock": ["role", "klass", "cls", "geom", "sports", "crypto"], "sched": ["role", "sports", "crypto", "capflag", "scheduled", "lookback"]}
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
