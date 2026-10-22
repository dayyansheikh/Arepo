# ruff: noqa: E501
"""LIVE prospective tests LT7 (docs/research_lab/LIVE_TESTS_7.md, text-frozen; section 13 governs where earlier text differs).
DRAFT: nothing is registered; E-numbers are assigned at registration. Research tooling only; never trades; no network request.

CODE PHASE 1: the census input seal and the counts-only pre-registration censuses (design sections 1, 7, 8.1-8.3 as they apply
to the censuses and the seal):

* CH195 (resistance), CS7: ``resist_units`` on sweep 1 of passes k - 1 and k with captures k - 12, k - 1, k;
* CH191 (grind at the capture clock), CC7: ``path_units7`` on captures k - 12 .. k;
* CH197 (patient money), CS7: ``patient_units`` on sweep 1 of the 12:31Z pass, and the F-feasibility pairs (pass j, pass j + 13);
* CH193 (absorbed flow), CC7 + CV7: ``absorbed_units`` with the lag volume change over (k + 2, k + 3] read ONLY through
  :func:`lag_capture`; CV7 is the ``volume24hr`` semantic gate on the sealed active-frame samples;
* CH192 (implied against realised), CC7: ``ivr_units`` with the 84-slot look-back and the lag spread at k + 3 (:func:`lag_capture`).

Censuses read origin-side fields only: no target, no P&L; nothing after the classified slot except the declared lag columns, which
reach census code only through the lag-slot loaders (design 7, R1 should-fix; unit-tested). Every opened input file is checked
against the LT7 seal first (refused on any mismatch, L3). LT3/LT4/LT5 code is used only through the vendored copies in
``live_tests7_base`` (R1 must-fix 10); this module never imports ``live_tests3`` .. ``live_tests6``.

The reader, the single analysis, the size check and the RSS probe are CODE PHASE 2 (not in this file).
"""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import forecast, maker_rewards, panel, trade_sample
from . import live_tests7_base as b

VERSION = "live-tests7-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SAMPLE_ROOT = ROOT / "data-dumps" / "research_lab" / "trade_samples"
SWEEP_ROOT = ROOT / "data-dumps" / "research_lab" / "book_sweeps"
OUT_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests7"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests7_v1.json"
SPEC_SHA256: str | None = None  # DRAFT: filled at registration
REGISTERED_UTC = "2026-12-08T00:00:00Z"  # proposed (design 1.1); slides later with LT6's END_UTC
END_UTC = "2026-12-29T00:00:00Z"
ANALYSIS_NOT_BEFORE = "2026-12-30T12:00:00Z"
TEMPFAIL = 75
DAY_S = 86400.0
CODE_FILES = ("live_tests7.py", "live_tests7_analysis.py", "live_tests7_base.py", "bounce_decomp.py",
              # hashed dependencies (design 8.1) and the modules the vendored base imports
              "maker_rewards.py", "panel.py", "trade_sample.py", "cb17_census.py", "cb13_label.py", "economics.py", "forecast.py")
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)

SNAP_COLS = [*b.SNAP_COLS, "liquidity", "clob_token_id_0"]
EXT_COLS = [*b.EXT_COLS, "rewards_min_size", "rewards_max_spread", "clob_rewards", "order_min_size"]
# The lag-slot loaders (design 7): the ONLY way a slot later than a unit's origin is read by census code.
LAG_CAPTURE_COLUMNS = ("spread", "volume24hr")
LAG_SWEEP_COLUMNS = ("bid_size_1", "ask_size_1", "depth_bid_5c", "depth_ask_5c")
LAG_CAPTURE_KEYS = ("market_id",)
LAG_SWEEP_KEYS = ("market_id", "token_id", "clob_token_id_0")
CENSUS_TESTS = ("CH195", "CH191", "CH197", "CH193", "CH192")

epoch, iso, sha256_file, _json = b.epoch, b.iso, b.sha256_file, b._json


# --- pins and spec ---------------------------------------------------------------------------------------------------


def code_sha256(path: Path) -> str:
    """sha256 of a code file with its ``SPEC_SHA256 = ...`` line normalised (LT3 9.3's rule)."""
    import hashlib

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
        raise RuntimeError(f"live_tests7 spec sha256 mismatch: {got} != pinned {sha}")
    spec["_sha256"], spec["_pinned"] = got, sha is not None
    for key, val in (("registered_utc", REGISTERED_UTC), ("end_utc", END_UTC), ("analysis_not_before", ANALYSIS_NOT_BEFORE)):
        if spec.get(key) != val:
            raise RuntimeError(f"live_tests7 spec {key} {spec.get(key)!r} != module constant {val!r} (L6)")
    return spec


# --- the pinned crypto classifier (design 1.0; LT6 R1 re-check R2, copied by value) ------------------------------------------

_NULL_LIKE = {"", "nan", "none", "null"}


def _norm_cat(v) -> str | None:
    """``strip().casefold()`` of a fee_category; None when absent or null-like."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip().casefold()
    return None if s in _NULL_LIKE else s


def crypto_class(fee_category, sidecar_present: bool = True, sports: int = 0) -> str:
    """``crypto`` when the sidecar row exists and its fee_category contains ``crypto`` (after strip and casefold); ``non_crypto``
    when it exists, is non-empty and has no ``crypto``; ``unknown`` otherwise (sidecar missing, field absent / empty / null-like, or
    ``sports == -1``). Unknown is counted separately and treated as crypto: every primary keeps only ``non_crypto``."""
    if not sidecar_present or sports == -1:
        return "unknown"
    s = _norm_cat(fee_category)
    if s is None:
        return "unknown"
    return "crypto" if "crypto" in s else "non_crypto"


def crypto_failsafe(values) -> dict:
    """``values``: the distinct ``fee_category`` values (with counts) of the WHOLE sealed sidecar set. If none contains ``crypto``
    (strip, casefold) the classifier is not shown to work and every gate that depends on it is NaN (fails)."""
    cnt: dict[str, int] = {}
    it = values.items() if isinstance(values, dict) else ((v, 1) for v in values)
    for v, n in it:
        key = "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)
        cnt[key] = cnt.get(key, 0) + int(n)
    works = any((_norm_cat(v) or "").find("crypto") >= 0 for v in cnt)
    return {"classifier_shown_to_work": bool(works), "distinct_values": dict(sorted(cnt.items())), "gate_value": None if works else float("nan")}


# --- readers ---------------------------------------------------------------------------------------------------------------


def load_rows7(cap_dir: Path) -> pd.DataFrame:
    """Origin-side capture columns (LT3's plus Gamma ``liquidity``): one row per market_id and per condition_id."""
    rows = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=lambda c: c in set(SNAP_COLS),
                       dtype={"market_id": str, "condition_id": str, "event_id": str, "received_utc": "category",
                              "end_date": "category", "closed": str, "active": str, "neg_risk": str, "clob_token_id_0": str})
    if "liquidity" not in rows:
        rows["liquidity"] = np.nan
    rows = rows.drop_duplicates("market_id")
    cond = rows["condition_id"].fillna("")
    rows = rows[~(cond.ne("") & cond.duplicated()).to_numpy()].reset_index(drop=True)
    rows["t_row"] = panel._epoch(rows["received_utc"].astype(str))
    return rows


def load_ext7(cap_dir: Path) -> pd.DataFrame | None:
    p = Path(cap_dir) / "rows_ext.csv.gz"
    if not p.exists():
        return None
    ext = pd.read_csv(p, usecols=lambda c: c in set(EXT_COLS), dtype=str)
    for c in EXT_COLS:
        if c not in ext:
            ext[c] = None
    return ext.drop_duplicates("market_id").set_index("market_id")


REWARD_STATUSES = ("listed", "null", "malformed", "absent")


def reward_status(v, present: bool, day: str | None) -> tuple[str, float]:
    """The reward status and daily rate of one sidecar cell (ruling 13.6, rule ``null_as_unrewarded_v1``). ``present`` = the market has a sidecar ROW
    (not merely a non-NaN cell). ``absent``: no row (NaN rate, excluded and counted). ``null``: the row exists and ``clob_rewards`` is empty / NaN: Gamma
    lists no programme = unrewarded (rate 0.0). ``listed``: the strict local parse (``json.loads``) gives a list: rate = the named parser's summed daily
    rate active on ``day`` (0.0 when every programme is inactive that day). ``malformed``: a string that is not a JSON list (NaN rate, excluded and
    counted). ``maker_rewards.parse_daily_rate`` is not edited; it is only called on a string that parsed as a list."""
    if not present:
        return "absent", float("nan")
    if not isinstance(v, str) or not v.strip():
        return "null", 0.0
    try:
        ok = isinstance(json.loads(v), list)
    except (json.JSONDecodeError, ValueError):
        ok = False
    if not ok:
        return "malformed", float("nan")
    return "listed", float(maker_rewards.parse_daily_rate(v, day))


def series7_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, day: str) -> pd.DataFrame:
    """LT3's series (vendored) plus Gamma ``liq``, the reward fields (``rew_status`` in {listed, null, malformed, absent}, decided from sidecar ROW
    presence; ``rew_rate`` = summed daily rate active on the capture's UTC ``day`` for a listed programme, 0.0 for a null ``clob_rewards``, NaN for a
    malformed cell or an absent row: ruling 13.6 ``null_as_unrewarded_v1``; ``rew_min``; ``rew_maxspread`` in cents), the sidecar ``osz``
    (order_min_size), the raw ``fee_cat`` and the pinned ``crypto7`` class (``crypto`` / ``non_crypto`` / ``unknown``)."""
    ser, _ = b.series_frame(rows, ext, spec)
    mids = pd.Index(ser["market_id"].astype(str))
    ser["liq"] = rows.set_index(rows["market_id"].astype(str))["liquidity"].reindex(mids).to_numpy(float)
    if ext is not None:
        e = ext.reindex(mids)
        present = mids.isin(ext.index)
        st = [reward_status(v, bool(p), day) for v, p in zip(e["clob_rewards"], present, strict=True)]
        ser["rew_status"] = pd.Series([s_ for s_, _ in st], dtype=object).to_numpy()
        ser["rew_rate"] = np.array([r_ for _, r_ in st], float)
        ser["rew_min"] = pd.to_numeric(e["rewards_min_size"], errors="coerce").to_numpy(float)
        ser["rew_maxspread"] = pd.to_numeric(e["rewards_max_spread"], errors="coerce").to_numpy(float)
        ser["osz"] = pd.to_numeric(e["order_min_size"], errors="coerce").to_numpy(float)
        fc = e["fee_category"].where(e["fee_category"].notna(), None).tolist()
    else:
        present = np.zeros(len(mids), bool)
        ser["rew_status"] = "absent"
        ser["rew_rate"], ser["rew_min"], ser["rew_maxspread"], ser["osz"] = np.nan, np.nan, np.nan, np.nan
        fc = [None] * len(mids)
    sp = ser["sports"].to_numpy(int)
    ser["fee_cat"] = pd.Series(fc, dtype=object).to_numpy()
    ser["crypto7"] = [crypto_class(f, bool(p), int(s)) for f, p, s in zip(fc, present, sp, strict=True)]
    return ser


def _utc_day(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%d")


def write_series7(work: Path, cap: dict, spec: dict) -> None:
    p = Path(work) / "series" / f"{cap['id']}.csv.gz"
    if p.exists():
        return
    rows = load_rows7(cap["dir"])
    b.write_once_csv(p, series7_frame(rows, load_ext7(cap["dir"]), spec, _utc_day(cap["start"])))


# --- the lag-slot loaders (design 7, R1 should-fix): the only reader of a slot later than a unit's origin -----------------------


def lag_capture(cap_dir: Path, column: str) -> pd.Series:
    """A later capture's ``column`` by market_id, read with ``usecols = [market_id, column]``: only ``spread`` (CH192) or
    ``volume24hr`` (CH193) is allowed; no bid, ask, mid, last trade or any other column of a later slot is reachable."""
    if column not in LAG_CAPTURE_COLUMNS:
        raise ValueError(f"lag-slot loader: column {column!r} is not allowed (allowed: {LAG_CAPTURE_COLUMNS})")
    df = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=[*LAG_CAPTURE_KEYS, column], dtype={"market_id": str})
    df = df.drop_duplicates("market_id")
    return pd.to_numeric(df.set_index("market_id")[column], errors="coerce")


def lag_sweep(sweep_dir: Path, cap_dir: Path) -> pd.DataFrame:
    """A later pass's sweep 1 on the outcome-0 token, indexed by market_id, with ONLY ``bid_size_1``, ``ask_size_1``,
    ``depth_bid_5c`` and ``depth_ask_5c`` (CH197's F-feasibility pairs). The token key comes from the same pass's capture."""
    tok = pd.read_csv(forecast.require_local(Path(cap_dir) / "rows.csv.gz"), usecols=["market_id", "clob_token_id_0"], dtype=str).drop_duplicates("market_id")
    sw = pd.read_csv(Path(sweep_dir) / "rows.csv.gz", usecols=lambda c: c in {*LAG_SWEEP_KEYS, *LAG_SWEEP_COLUMNS}, dtype={"token_id": str, "market_id": str})
    for c in LAG_SWEEP_COLUMNS:
        if c not in sw:
            sw[c] = np.nan
    sw = sw.merge(tok, on="market_id", how="inner")
    sw = sw[sw["token_id"] == sw["clob_token_id_0"]].drop_duplicates("market_id").set_index("market_id")
    return sw[list(LAG_SWEEP_COLUMNS)].apply(pd.to_numeric, errors="coerce")


# --- slots, mids and realised volatility from the reader's own series (never from a later slot) -------------------------------


def slot_in_day(k: int) -> int:
    """Index of slot ``k`` within its UTC day on the 2 h grid (grid0 is 00:31Z, so 0 = 00:31Z, 6 = 12:31Z)."""
    return int(k) % 12


class MidStore:
    """Per-slot (mid, spread) of the two-sided quotes, kept as coded arrays (a few hundred KB a slot) so that the 84-slot
    look-back of CH192 and the 3-step paths of CH191 never hold 85 string indexes. Only slots <= the origin are asked for."""

    def __init__(self) -> None:
        self.code: dict[str, int] = {}
        self.slots: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    def add(self, k: int, ser: pd.DataFrame) -> None:
        ids = ser.index.astype(str)
        codes = np.fromiter((self.code.setdefault(m, len(self.code)) for m in ids), dtype=np.int64, count=len(ids))
        mid = ((ser["bid"].to_numpy(float) + ser["ask"].to_numpy(float)) / 2.0).astype(np.float64)
        self.slots[k] = (codes, mid, ser["spread"].to_numpy(float))

    def matrix(self, k: int, window: int, markets, what: str = "mid") -> np.ndarray:
        """(n_markets, window + 1) of ``mid`` or ``spread`` at slots k - window .. k; NaN where the slot or the market is absent."""
        idx = np.fromiter((self.code.get(str(m), -1) for m in markets), dtype=np.int64, count=len(markets))
        out = np.full((len(idx), window + 1), np.nan)
        ok = idx >= 0
        n = len(self.code)
        for i, j in enumerate(range(k - window, k + 1)):
            if j not in self.slots:
                continue
            codes, mid, spr = self.slots[j]
            arr = np.full(n, np.nan)
            arr[codes] = mid if what == "mid" else spr
            out[ok, i] = arr[idx[ok]]
        return out


def rv_from_matrix(M: np.ndarray, min_obs: int) -> tuple[np.ndarray, np.ndarray]:
    """rms of the consecutive-slot mid changes of the rows of ``M`` (observed = both mids present); NaN below ``min_obs`` changes."""
    d = M[:, 1:] - M[:, :-1]
    obs = np.isfinite(d)
    n = obs.sum(axis=1)
    ss = np.where(obs, d * d, 0.0).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        rv = np.where(n >= min_obs, np.sqrt(ss / np.maximum(n, 1)), np.nan)
    return rv, n


def floored_rv(rv: np.ndarray, tick: np.ndarray, floor_ticks: float) -> tuple[np.ndarray, np.ndarray]:
    """``rv* = max(rv, 0.5 x tick)`` and the flag ``rv_floor = 1[rv < 0.5 x tick]`` (6.B); NaN stays NaN."""
    fl = floor_ticks * np.asarray(tick, float)
    with np.errstate(invalid="ignore"):
        return np.maximum(rv, fl), np.where(np.isfinite(rv) & np.isfinite(fl), (rv < fl).astype(float), np.nan)


# --- shared unit machinery ---------------------------------------------------------------------------------------------------


def _movers_join(ser_k: pd.DataFrame, ser_p: pd.DataFrame, cap: dict, spec: dict, lo: float, hi: float, margin_h: float) -> tuple[pd.DataFrame, dict]:
    """1.4 items 1-7 (LT3's ``move_join``, vendored): two-sided and tight at k - 1 and k, ``mid_k`` in [lo, hi], as-of end unknown
    or > t + margin; adds ``mid``, ``x`` (the 2 h mid move), LT3's class and geometry. Each exclusion counted."""
    j, cnt = b.move_join(ser_k, ser_p, cap, spec, lo, hi, margin_h)
    mid = ((j["bid"] + j["ask"]) / 2.0).to_numpy(float)
    mid_p = ((j["bid_p"] + j["ask_p"]) / 2.0).to_numpy(float)
    cls, geom = b.classify(j["bid_p"], j["ask_p"], j["bid"], j["ask"], j["ltp_p"], j["ltp"], j["vol24_p"], j["vol24"], spec)
    return j.assign(mid=mid, mid_p=mid_p, x=mid - mid_p, cls=cls, geom=geom), cnt


def _non_sports_ex_crypto(j: pd.DataFrame, cnt: dict) -> pd.DataFrame:
    """The primaries' category rule: sidecar of k says non-sports (``sports == 0``) and the pinned classifier says non-crypto.
    Unknown (sidecar missing, ``sports == -1``) and crypto are counted and excluded; the sports and crypto arms are reported only."""
    cnt["sports_unknown"] = int((j["sports"] == -1).sum())
    cnt["sports"] = int((j["sports"] == 1).sum())
    j = j[j["sports"] == 0]
    cnt["crypto"] = int((j["crypto7"] == "crypto").sum())
    cnt["crypto_unknown"] = int((j["crypto7"] == "unknown").sum())
    return j[j["crypto7"] == "non_crypto"]


def _hte(end_ts, t_row) -> tuple[np.ndarray, np.ndarray]:
    """log hours-to-end with the declared indicator-pair exception: an unknown end enters as 0 with ``hte_unknown`` (1.5)."""
    hte = (np.asarray(end_ts, float) - np.asarray(t_row, float)) / 3600.0
    unk = ~np.isfinite(hte)
    with np.errstate(invalid="ignore", divide="ignore"):
        lh = np.log(np.clip(hte, 1.0, None))
    return np.where(unk, 0.0, lh), unk.astype(float)


def _own24(sign, mid_k, mid_12) -> tuple[np.ndarray, np.ndarray]:
    """Own 24 h change ``sign x (mid_k - mid_{k-12})`` (sign 1 for unsigned use) with the missing-indicator pair (0 + flag)."""
    d = np.asarray(sign, float) * (np.asarray(mid_k, float) - np.asarray(mid_12, float))
    miss = ~np.isfinite(d)
    return np.where(miss, 0.0, d), miss.astype(float)


def _in_band(mid, spread, rewards_max_spread_cents, band) -> np.ndarray:
    """``in_band``: folded mid in the one-sided scoring band and spread <= ``rewards_max_spread`` (cents). A missing ``rewards_max_spread`` with the
    mid inside the band is NaN (excluded, counted), never 0 (1.5; census-code check must-fix 3); a mid outside the band is 0 whatever the field."""
    mid, sp, rms = (np.asarray(v, float) for v in (mid, spread, rewards_max_spread_cents))
    inside = (mid >= band[0] - 1e-12) & (mid <= band[1] + 1e-12)
    with np.errstate(invalid="ignore"):
        ok = (sp * 100.0 <= rms + 1e-9)
    known = np.isfinite(rms) & np.isfinite(sp)  # a missing field OR a missing spread inside the band is NaN, never 0
    return np.where(~inside, 0.0, np.where(known, ok.astype(float), np.nan))


def _reward_cols(j: pd.DataFrame, cnt: dict) -> tuple[np.ndarray, np.ndarray]:
    """``rew_rate`` and ``rewarded`` (1 if the rate is positive that UTC day, 0 for a null / listed-inactive programme, NaN only for a malformed or absent
    status) of the eligible units, with the four status counts (ruling 13.6, ``null_as_unrewarded_v1``). ``rewards_null_as_zero`` = null
    ``clob_rewards`` read as unrewarded; ``rewards_listed_inactive`` = a listed programme with rate 0 on the capture's day; ``reward_unparseable`` =
    malformed ONLY; ``reward_sidecar_absent`` = no sidecar row. Disjoint groups; the two unrewarded groups are pooled in ``rewarded`` but counted apart."""
    st = j["rew_status"].astype(str).to_numpy()
    rew = j["rew_rate"].to_numpy(float)
    cnt["rewards_null_as_zero"] = int((st == "null").sum())
    cnt["rewards_listed_inactive"] = int(((st == "listed") & np.isfinite(rew) & (rew == 0.0)).sum())
    cnt["reward_unparseable"] = int((st == "malformed").sum())
    cnt["reward_sidecar_absent"] = int((st == "absent").sum())
    return rew, np.where(np.isfinite(rew), (rew > 0).astype(float), np.nan)


def rewarded_x_in_band(U: pd.DataFrame) -> dict:
    """Counts of the four ``rewarded x in_band`` cells of a unit frame (ruling 13.6 point 8; descriptive only)."""
    if U.empty or "rewarded" not in U or "in_band" not in U:
        return {}
    r, i = U["rewarded"].to_numpy(float), U["in_band"].to_numpy(float)
    return {f"rewarded{int(a)}_in_band{int(c)}": int(((r == a) & (i == c)).sum()) for a in (0, 1) for c in (0, 1)}


def _mid12(store: MidStore | None, k: int, markets) -> np.ndarray:
    """Mid at slot k - 12 (the origin's own 24 h look-back) by market; NaN if the slot, the market or the store is absent."""
    mk = np.asarray([str(m) for m in markets])
    if store is None or not len(mk):
        return np.full(len(mk), np.nan)
    return store.matrix(k, 12, mk, "mid")[:, 0]


def _common_cols(u: pd.DataFrame) -> pd.DataFrame:
    u = u.copy()
    mid = u["mid"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        u["logit_mid"] = np.log(mid / (1.0 - mid))
    u["abs_dev"] = np.abs(mid - 0.5)
    u["tick001"] = (np.abs(u["tick"].to_numpy(float) - 0.001) < 1e-9).astype(float)
    u["log_hte"], u["hte_unknown"] = _hte(u["end_ts"], u["t_row"])
    u["log1p_liq"] = np.log1p(u["liq"].clip(lower=0))
    return u


def _anatomy(u: pd.DataFrame) -> pd.DataFrame:
    """Anatomy dummies of 1.4 (traded, parallel, one_sided, spread_change; same-side-unequal the base)."""
    u = u.copy()
    u["a_traded"] = (u["cls"] == "traded").astype(float)
    for g in ("parallel", "one_sided", "spread_change"):
        u[f"a_{g}"] = (u["geom"] == g).astype(float)
    return u


def _base_out(j: pd.DataFrame, cap: dict, k: int) -> dict:
    return {"market_id": j["market_id"].astype(str).to_numpy(), "event_id": j["event_id"].astype(str).to_numpy(), "skey": j["skey"].astype(str).to_numpy(),
            "sports": j["sports"].to_numpy(int), "day": _utc_day(cap["start"]), "slot": k}


# --- CH195 resistance (design 2) --------------------------------------------------------------------------------------------------


def resist_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: MidStore | None, sw_k: pd.DataFrame | None, sw_p: pd.DataFrame | None, cap: dict, k: int,
                 spec: dict) -> tuple[pd.DataFrame, dict]:
    """CH195's units of pass k (section 2): non-sports ex-crypto traded or quote-only movers at k (1.4, ``|x| >= 0.01``, mid in
    [0.07, 0.93], end > t + 7 h) with sweep 1 of BOTH pass k - 1 and pass k two-sided on the outcome-0 token, tight (sweep spread
    <= 0.10), both 5c depths and the touch prices present, and the sweep move agreeing in sign with ``x``. ``sw_*`` are
    :func:`live_tests7_base.sweep_frame` outputs indexed by market_id (None = no sweep: ``.nosweep`` / ``.noprevsweep``, counted).
    The own 24 h change reads the mid at slot k - 12 from ``store`` (the origin's own look-back, never a later slot).
    State: ``D_hit = depth_hit_5c x touch_hit`` and ``D_away`` of the pass k - 1 book, ``R = log1p D_hit``, ``R_away = log1p D_away``."""
    c = spec["tests"]["CH195"]
    j, cnt = _movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = j[np.abs(j["x"]) >= c["min_abs_x"] - 1e-12]
    cnt["movers"] = len(j)
    j = j[j["cls"].isin(c["classes"])]
    cnt["traded_or_quote_only"] = len(j)
    j = _non_sports_ex_crypto(j.copy(), cnt)
    cnt["non_sports_ex_crypto_movers"] = len(j)
    if sw_k is None:
        cnt["nosweep"] = 1
        return pd.DataFrame(), cnt
    if sw_p is None:
        cnt["noprevsweep"] = 1
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    cols = ["sbid", "sask", "s_t", "s_two", "dbid5", "dask5"]
    a = sw_k.reindex(mk)[cols].reset_index(drop=True)
    p = sw_p.reindex(mk)[cols].reset_index(drop=True)
    j = j.reset_index(drop=True)
    for col in cols:
        j[f"{col}_k"], j[f"{col}_p"] = a[col].to_numpy(float), p[col].to_numpy(float)
    two = (j["s_two_k"] == 1) & (j["s_two_p"] == 1)
    dep = np.isfinite(j[["dbid5_k", "dask5_k", "dbid5_p", "dask5_p"]]).all(axis=1)
    touch = np.isfinite(j[["sbid_k", "sask_k", "sbid_p", "sask_p"]]).all(axis=1)
    cov = two & dep & touch
    cnt["no_both_sweeps"] = int((~two).sum())
    cnt["covered"] = int(cov.sum())
    j = j[cov].copy()
    cnt["covered_sign_agree"] = int((np.sign(((j["sbid_k"] + j["sask_k"]) / 2.0 - (j["sbid_p"] + j["sask_p"]) / 2.0).to_numpy(float)) == np.sign(j["x"].to_numpy(float))).sum())
    tight = ((j["sask_k"] - j["sbid_k"]) <= c["sweep_spread_max"] + 1e-12) & ((j["sask_p"] - j["sbid_p"]) <= c["sweep_spread_max"] + 1e-12)
    cnt["sweep_not_tight"] = int((~tight).sum())
    j = j[tight].copy()
    smid_k, smid_p = (j["sbid_k"] + j["sask_k"]) / 2.0, (j["sbid_p"] + j["sask_p"]) / 2.0
    agree = np.sign((smid_k - smid_p).to_numpy(float)) == np.sign(j["x"].to_numpy(float))
    cnt["sign_disagree"] = int((~agree).sum())
    j = j[agree].reset_index(drop=True)
    sx = np.sign(j["x"].to_numpy(float))
    d_hit = np.where(sx > 0, j["dask5_p"] * j["sask_p"], j["dbid5_p"] * j["sbid_p"])
    d_away = np.where(sx > 0, j["dbid5_p"] * j["sbid_p"], j["dask5_p"] * j["sask_p"])
    notional0 = (j["dbid5_k"] * j["sbid_k"] + j["dask5_k"] * j["sask_k"]).to_numpy(float)
    liq = j["liq"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        h0 = np.where(np.isfinite(notional0) & np.isfinite(liq) & (liq > 0), np.clip(1.0 - notional0 / liq, 0.0, 1.0), np.nan)
    m12 = _mid12(store, k, j["market_id"])
    d24, d24f = _own24(sx, j["mid"], m12)
    u = pd.DataFrame({**_base_out(j, cap, k), "t_row": j["s_t_k"].to_numpy(float), "x": j["x"].to_numpy(float), "sx": sx, "cls": j["cls"].to_numpy(),
                      "geom": j["geom"].to_numpy(), "mid": j["mid"].to_numpy(float), "tick": j["tick"].to_numpy(float), "liq": liq,
                      "end_ts": j["end_ts"].to_numpy(float), "vol24_p": j["vol24_p"].to_numpy(float), "spread_sw_k": (j["sask_k"] - j["sbid_k"]).to_numpy(float),
                      "spread_sw_p": (j["sask_p"] - j["sbid_p"]).to_numpy(float), "D_hit": d_hit, "D_away": d_away, "h0": h0, "d24": d24, "d24_flag": d24f})
    u["R"], u["R_away"] = np.log1p(u["D_hit"]), np.log1p(u["D_away"])
    u["v_prev"] = sx * b.imbalance(j["dbid5_p"], j["dask5_p"])  # LT6 V's pre-move skew (descriptive correlation only)
    u["log_abs_x"] = np.log(np.abs(u["x"]))
    u["log1p_vol_p"] = np.log1p(u["vol24_p"].clip(lower=0))
    u["traded"] = (u["cls"] == "traded").astype(float)
    u = _anatomy(_common_cols(u))
    cnt["units"] = len(u)
    return u, cnt


# --- CH191 grind at the capture clock (design 3, with R1 must-fix 11) ------------------------------------------------------------


def path_units7(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: MidStore, cap: dict, k: int, spec: dict) -> tuple[pd.DataFrame, dict]:
    """CH191's units of capture k (section 3): non-sports ex-crypto markets two-sided AND tight (<= 0.10) at k - 3 .. k, steps
    ``s_j = mid_{k-j+1} - mid_{k-j}`` (j = 1..3), ``x6 = s1 + s2 + s3`` with ``|x6| >= 0.02`` and ``|x6| >= 3`` ticks (sidecar tick
    at k), mid_k in [0.05, 0.95], 1.4 items 1-7 at k - 1 and k. ``pc = max|s_j| / sum|s_j|``. Grind = every ``|s_j| >= 1`` tick with
    the sign of ``x6`` and ``pc <= 0.5``; jump = ``pc >= 0.8``; else other. ``rv24*`` needs at least 10 of 12 observed changes."""
    c = spec["tests"]["CH191"]
    j, cnt = _movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    mk = j["market_id"].astype(str).to_numpy()
    M = store.matrix(k, 12, mk, "mid")
    S = store.matrix(k, 12, mk, "spread")
    sm = spec["eligibility"]["spread_max"]
    seen = np.isfinite(M[:, 9:13]).all(axis=1)  # slots k - 3 .. k all two-sided
    with np.errstate(invalid="ignore"):
        tight = np.isfinite(S[:, 9:13]).all(axis=1) & (S[:, 9:13] <= sm + 1e-12).all(axis=1)
    cnt["step_slot_missing"] = int((~seen).sum())
    cnt["step_slot_not_tight"] = int((seen & ~tight).sum())
    ok = seen & tight
    j, M = j[ok].copy(), M[ok]
    s1, s2, s3 = M[:, 12] - M[:, 11], M[:, 11] - M[:, 10], M[:, 10] - M[:, 9]
    x6 = s1 + s2 + s3
    tick = j["tick"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        big = (np.abs(x6) >= c["min_abs_x6"] - 1e-12) & (np.abs(x6) >= c["min_ticks_x6"] * tick - 1e-12)
    cnt["x6_below_threshold_or_tick_unknown"] = int((~big).sum())
    j, M, s1, s2, s3, x6, tick = j[big].copy(), M[big], s1[big], s2[big], s3[big], x6[big], tick[big]
    cnt["non_sports_filter_in"] = len(j)
    cat = _non_sports_ex_crypto(j.copy(), cnt)
    keep = j.index.isin(cat.index)
    j, M, s1, s2, s3, x6, tick = j[keep].copy(), M[keep], s1[keep], s2[keep], s3[keep], x6[keep], tick[keep]
    S3 = np.abs(np.column_stack([s1, s2, s3]))
    tot = S3.sum(axis=1)
    sgn = np.sign(x6)
    with np.errstate(invalid="ignore", divide="ignore"):
        pc = S3.max(axis=1) / tot
        sa = np.abs(x6) / tot
        every_step = (S3 >= c["grind_step_min_ticks"] * tick[:, None] - 1e-12).all(axis=1) & (np.sign(np.column_stack([s1, s2, s3])) == sgn[:, None]).all(axis=1)
    cls6 = np.where(every_step & (pc <= c["grind_pc_max"] + 1e-12), "grind", np.where(pc >= c["jump_pc_min"] - 1e-12, "jump", "other"))
    with np.errstate(invalid="ignore"):  # counts only: units the first draft's `sa >= 0.9` rule would have called a grind and the every-step rule does not
        cnt["every_step_rule_loss"] = int(((sa >= 0.9 - 1e-12) & (pc <= c["grind_pc_max"] + 1e-12) & (cls6 != "grind")).sum())
    # rv24*: at least 10 of the 12 changes k - 11 .. k observed, else NaN, excluded and counted
    rv, nobs = rv_from_matrix(M, c["rv_min_obs"])
    rvs, rvf = floored_rv(rv, tick, spec["tests"]["CH192"]["rv_floor_ticks"])
    undefined = ~np.isfinite(rvs)
    cnt["rv24_undefined"] = int(undefined.sum())
    cnt["movers_6h"] = int((~undefined).sum())
    first_move = np.abs(s1) >= c["min_abs_x_last_step"] - 1e-12
    last_cls = np.where(first_move, j["cls"].to_numpy(), "small_last_step")
    m12 = M[:, 0]
    d24, d24f = _own24(sgn, j["mid"].to_numpy(float), m12)
    u = pd.DataFrame({**_base_out(j, cap, k), "t_row": j["t_row"].to_numpy(float), "x6": x6, "sx": sgn, "s1": s1, "s2": s2, "s3": s3, "pc": pc, "sa": sa, "cls6": cls6,
                      "last_cls": last_cls, "mid": j["mid"].to_numpy(float), "spread": j["spread"].to_numpy(float), "tick": tick, "liq": j["liq"].to_numpy(float),
                      "end_ts": j["end_ts"].to_numpy(float), "vol24": j["vol24"].to_numpy(float), "rv24s": rvs, "rv_floor": rvf, "d24": d24, "d24_flag": d24f})
    u = u[~undefined].reset_index(drop=True)
    u["G"] = (u["cls6"] == "grind").astype(float)
    u["log_abs_x6"] = np.log(np.abs(u["x6"]))
    u["log_rv24s"] = np.log(u["rv24s"])
    u["log1p_vol"] = np.log1p(u["vol24"].clip(lower=0))
    u["traded_last"] = (u["last_cls"] == "traded").astype(float)
    for nm in ("traded", "quote_only", "ambiguous", "never_traded"):
        u[f"l_{nm}"] = (u["last_cls"] == nm).astype(float)
    u = _common_cols(u)
    cnt["units"] = len(u)
    cnt["by_class"] = {str(a_): int(v_) for a_, v_ in u["cls6"].value_counts().items()}
    return u, cnt


# --- CH197 patient money (design 5) ---------------------------------------------------------------------------------------------


def behind_touch(bsz1, asz1, dbid5, dask5) -> dict:
    """Touch and behind-touch imbalances of the outcome-0 book: ``bB = depth_bid_5c - bid_size_1`` (the 5c band includes the touch),
    ``imbT = (bT - aT) / (bT + aT)``, ``imbB = (bB - aB) / (bB + aB)``; NaN where an input is missing, ``bT + aT <= 0``,
    ``bB + aB <= 0`` (excluded, counted) or either behind-touch depth is negative (an inconsistent book, counted separately)."""
    bT, aT, d1, d2 = (np.asarray(v, float) for v in (bsz1, asz1, dbid5, dask5))
    bB, aB = d1 - bT, d2 - aT
    with np.errstate(invalid="ignore", divide="ignore"):
        imbT = np.where(np.isfinite(bT + aT) & ((bT + aT) > 0), (bT - aT) / (bT + aT), np.nan)
        neg = np.isfinite(bB) & np.isfinite(aB) & ((bB < 0) | (aB < 0))
        zero = np.isfinite(bB) & np.isfinite(aB) & ~neg & ((bB + aB) <= 0)
        imbB = np.where(np.isfinite(bB + aB) & ((bB + aB) > 0) & ~neg, (bB - aB) / (bB + aB), np.nan)
    return {"bT": bT, "aT": aT, "bB": bB, "aB": aB, "imbT": imbT, "imbB": imbB, "behind_negative": neg, "behind_zero": zero}


def patient_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: MidStore | None, sw_k: pd.DataFrame | None, cap: dict, k: int, spec: dict,
                  any_slot: bool = False) -> tuple[pd.DataFrame, dict]:
    """CH197's units at the 12:31Z pass k (section 5): non-sports ex-crypto two-sided markets (1.4 items 1-7 at k - 1 and k, mid_k in
    [0.07, 0.93], end > t + 27 h) with sweep 1 of pass k two-sided on the outcome-0 token, spread <= 0.05, ``bid_size_1`` /
    ``ask_size_1`` present, both 5c depths present and positive, ``bB + aB > 0`` and a parseable reward status. One unit per market
    per day by construction (one pass a day). ``books_in_band`` counts the eligible books (the covered-share denominator).
    ``any_slot=True`` lifts the 12:31Z restriction (only for the F-feasibility pairs j, j + 13 of the census, design 7)."""
    c = spec["tests"]["CH197"]
    cnt: dict = {}
    if not any_slot and slot_in_day(k) != c["slot_index_in_day"]:
        cnt["not_1231_pass"] = 1
        return pd.DataFrame(), cnt
    j, cnt = _movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = _non_sports_ex_crypto(j.copy(), cnt)
    cnt["books_in_band"] = len(j)
    if sw_k is None:
        cnt["nosweep"] = 1
        return pd.DataFrame(), cnt
    mk = j["market_id"].astype(str)
    cols = ["sbid", "sask", "s_t", "s_two", "bsz1", "asz1", "dbid5", "dask5", "dbid1", "dask1"]
    s = sw_k.reindex(mk)[cols].reset_index(drop=True)
    j = j.reset_index(drop=True)
    for col in cols:
        j[col] = s[col].to_numpy(float)
    two = j["s_two"] == 1
    tight = (j["sask"] - j["sbid"]) <= c["sweep_spread_max"] + 1e-12
    dep = np.isfinite(j[["dbid5", "dask5", "bsz1", "asz1"]]).all(axis=1) & (j["dbid5"] > 0) & (j["dask5"] > 0)
    cnt["no_sweep_two_sided"] = int((~two).sum())
    cnt["sweep_not_tight"] = int((two & ~tight).sum())
    cnt["depth_missing_or_zero"] = int((two & tight & ~dep).sum())
    j = j[two & tight & dep].copy().reset_index(drop=True)
    bt = behind_touch(j["bsz1"], j["asz1"], j["dbid5"], j["dask5"])
    cnt["behind_negative"] = int(bt["behind_negative"].sum())
    cnt["behind_zero_excluded"] = int(bt["behind_zero"].sum())
    okb = np.isfinite(bt["imbB"]) & np.isfinite(bt["imbT"])
    cnt["touch_zero_or_missing"] = int((~okb & ~bt["behind_negative"] & ~bt["behind_zero"]).sum())
    j = j[okb].copy().reset_index(drop=True)
    bt = {key: v[okb] for key, v in bt.items()}
    notional0 = (j["dbid5"] * j["sbid"] + j["dask5"] * j["sask"]).to_numpy(float)
    liq = j["liq"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        h0 = np.where(np.isfinite(liq) & (liq > 0), np.clip(1.0 - notional0 / liq, 0.0, 1.0), np.nan)
    rew, rewarded = _reward_cols(j, cnt)
    spread_sw = (j["sask"] - j["sbid"]).to_numpy(float)
    mid = j["mid"].to_numpy(float)
    rms = j["rew_maxspread"].to_numpy(float)
    in_band = _in_band(mid, spread_sw, rms, c["reward_band"])
    cnt["in_band_unknown"] = int(np.isnan(in_band).sum())
    m12 = _mid12(store, k, j["market_id"])
    d24, d24f = _own24(1.0, mid, m12)
    u = pd.DataFrame({**_base_out(j, cap, k), "t_row": j["s_t"].to_numpy(float), "imbT": bt["imbT"], "imbB": bt["imbB"], "bT": bt["bT"], "aT": bt["aT"], "bB": bt["bB"], "aB": bt["aB"],
                      "mid": mid, "tick": j["tick"].to_numpy(float), "liq": liq, "end_ts": j["end_ts"].to_numpy(float), "vol24": j["vol24"].to_numpy(float),
                      "spread_sw": spread_sw, "total5": (j["dbid5"] + j["dask5"]).to_numpy(float), "h0": h0, "d24": d24, "d24_flag": d24f,
                      "rewarded": rewarded, "in_band": in_band, "rew_status": j["rew_status"].astype(str).to_numpy(), "rew_min": j["rew_min"].to_numpy(float),
                      "osz": j["osz"].to_numpy(float)})
    u["dis"] = u["imbB"] - u["imbT"]
    u["imbT1"] = b.imbalance(j["dbid1"], j["dask1"])  # S4: the 1c-band form of the touch (descriptive correlation with the best-level form)
    u["log1p_total5"] = np.log1p(u["total5"])
    u["log1p_vol"] = np.log1p(u["vol24"].clip(lower=0))
    u = u[np.isfinite(u["rewarded"]) & np.isfinite(u["in_band"])].reset_index(drop=True)
    u = _common_cols(u)
    cnt["units"] = len(u)
    return u, cnt


# --- CH193 absorbed flow (design 6.A) ---------------------------------------------------------------------------------------------


def dv_tolerance(vol_prev, spec: dict | None = None, abs_tol: float = 10.0, rel_tol: float = 1e-4) -> np.ndarray:
    """``max($10, 1e-4 x volume24hr_{k-1})``: the engine's movetype tolerance (design 6.A)."""
    if spec is not None:
        g = spec["tests"]["CH193"]
        abs_tol, rel_tol = g["dv_abs"], g["dv_rel"]
    return np.maximum(abs_tol, rel_tol * np.asarray(vol_prev, float))


def lag_change(vol_k2: pd.Series | None, vol_k3: pd.Series | None, markets) -> tuple[np.ndarray, np.ndarray]:
    """``dV_lag = volume24hr_{k+3} - volume24hr_{k+2}`` by market (the (k + 2, k + 3] interval) from the lag loader's two Series and
    ``lag_rolloff = 1[dV_lag < 0]``; NaN (missing, never imputed) if either slot or either value is missing. A negative change is
    observed data: it enters as ``log1p(max(dV_lag, 0))`` with ``lag_rolloff`` (the arm's handling, 1.5 / 6.A)."""
    mk = pd.Index([str(m) for m in markets])
    if vol_k2 is None or vol_k3 is None:
        return np.full(len(mk), np.nan), np.full(len(mk), np.nan)
    d = vol_k3.reindex(mk).to_numpy(float) - vol_k2.reindex(mk).to_numpy(float)
    with np.errstate(invalid="ignore"):
        return d, np.where(np.isfinite(d), (d < 0).astype(float), np.nan)


def absorbed_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: MidStore, cap: dict, k: int, spec: dict,
                   lag_vol2: pd.Series | None = None, lag_vol3: pd.Series | None = None) -> tuple[pd.DataFrame, dict]:
    """CH193's units of capture k (section 6.A): non-sports ex-crypto markets (1.4 items 1-7 at k - 1 and k, mid_k in [0.02, 0.98],
    end > t + 7 h) with ``volume24hr`` present at k - 1 and k, ``dV = volume24hr_k - volume24hr_{k-1} > max($10, 1e-4 x
    volume24hr_{k-1})`` and ``|x| < 0.005``. The lag change over (k + 2, k + 3] comes ONLY from the lag loader's Series."""
    c = spec["tests"]["CH193"]
    j, cnt = _movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = _non_sports_ex_crypto(j.copy(), cnt)
    cnt["eligible"] = len(j)
    vol, vol_p = j["vol24"].to_numpy(float), j["vol24_p"].to_numpy(float)
    present = np.isfinite(vol) & np.isfinite(vol_p)
    cnt["volume_present"] = int(present.sum())
    j = j[present].copy()
    vol, vol_p = vol[present], vol_p[present]
    dv = vol - vol_p
    cnt["rolloff_negative_dv"] = int((dv < 0).sum())
    pos = dv > dv_tolerance(vol_p, spec)
    cnt["dv_not_above_tolerance"] = int((~pos).sum())
    nomove = np.abs(j["x"].to_numpy(float)) < c["abs_x_max"] - 1e-12
    cnt["moved"] = int((pos & ~nomove).sum())
    keep = pos & nomove
    j, dv, vol_p = j[keep].copy().reset_index(drop=True), dv[keep], vol_p[keep]
    cnt["traded_non_movers"] = len(j)
    mk = j["market_id"].astype(str).to_numpy()
    Mx = store.matrix(k, 12, mk, "mid")
    rv, _ = rv_from_matrix(Mx, spec["tests"]["CH191"]["rv_min_obs"])
    rvs, rvf = floored_rv(rv, j["tick"].to_numpy(float), spec["tests"]["CH192"]["rv_floor_ticks"])
    cnt["rv24_undefined"] = int((~np.isfinite(rvs)).sum())
    d24, d24f = _own24(1.0, j["mid"].to_numpy(float), Mx[:, 0])
    lag, rolloff = lag_change(lag_vol2, lag_vol3, mk)
    cnt["lag_missing"] = int((~np.isfinite(lag)).sum())
    cnt["lag_rolloff"] = int(np.nansum(rolloff))
    u = pd.DataFrame({**_base_out(j, cap, k), "t_row": j["t_row"].to_numpy(float), "x": j["x"].to_numpy(float), "mid": j["mid"].to_numpy(float), "spread": j["spread"].to_numpy(float),
                      "tick": j["tick"].to_numpy(float), "liq": j["liq"].to_numpy(float), "end_ts": j["end_ts"].to_numpy(float), "ltp": j["ltp"].to_numpy(float),
                      "ltp_present": np.isfinite(j["ltp"].to_numpy(float)).astype(float), "bid": j["bid"].to_numpy(float), "ask": j["ask"].to_numpy(float),
                      "vol24": j["vol24"].to_numpy(float), "vol24_p": vol_p, "dV": dv, "rv24s": rvs, "rv_floor": rvf, "d24": np.abs(d24), "d24_flag": d24f,
                      "dV_lag": lag, "lag_rolloff": rolloff})
    u = u[np.isfinite(u["rv24s"])].reset_index(drop=True)
    u["ldv"] = np.log1p(u["dV"])
    u["ldv_lag"] = np.log1p(np.maximum(u["dV_lag"], 0.0))
    u["log_rv24s"] = np.log(u["rv24s"])
    u["log1p_vol_p"] = np.log1p(u["vol24_p"].clip(lower=0))
    u = _common_cols(u)
    cnt["units"] = len(u)
    return u, cnt


# --- CH192 implied against realised (design 6.B) --------------------------------------------------------------------------------


def ivr_units(ser_k: pd.DataFrame, ser_p: pd.DataFrame, store: MidStore, cap: dict, k: int, spec: dict, lag_spread: pd.Series | None = None) -> tuple[pd.DataFrame, dict]:
    """CH192's units at the 00:31 / 06:31 / 12:31 / 18:31Z passes (section 6.B): non-sports ex-crypto two-sided tight markets
    (1.4 items 1-7 at k - 1 and k, mid_k in [0.02, 0.98], end > t + 7 h) with ``rv24`` (at least 10 of 12 changes) and ``rv7d``
    (at least 60 of 84) defined. ``rv24* = max(rv24, 0.5 tick)``, ``ivr = log(spread_k / rv24*)`` with ``spread_k = ask_k - bid_k``,
    and ``ivr_lag = log(spread_{k+3} / rv24*)`` over the SAME pre-target volatility, ``spread_{k+3}`` from the lag loader only."""
    c = spec["tests"]["CH192"]
    cnt: dict = {}
    if slot_in_day(k) not in c["slot_index_in_day"]:
        cnt["not_a_declared_slot"] = 1
        return pd.DataFrame(), cnt
    j, cnt = _movers_join(ser_k, ser_p, cap, spec, c["mid_lo"], c["mid_hi"], c["end_margin_h"])
    j = _non_sports_ex_crypto(j.copy(), cnt)
    cnt["eligible"] = len(j)
    mk = j["market_id"].astype(str).to_numpy()
    M24 = store.matrix(k, c["rv24_window"], mk, "mid")
    M7 = store.matrix(k, c["rv7d_window"], mk, "mid")
    rv24, _ = rv_from_matrix(M24, c["rv24_min_obs"])
    rv7, _ = rv_from_matrix(M7, c["rv7d_min_obs"])
    tick = j["tick"].to_numpy(float)
    rvs, rvf = floored_rv(rv24, tick, c["rv_floor_ticks"])
    cnt["rv24_undefined"] = int((~np.isfinite(rv24)).sum())
    cnt["rv7d_undefined"] = int((np.isfinite(rv24) & ~np.isfinite(rv7)).sum())
    ok = np.isfinite(rv24) & np.isfinite(rv7) & np.isfinite(tick)
    j = j[ok].copy().reset_index(drop=True)
    rv24, rv7, rvs, rvf, tick, mk = rv24[ok], rv7[ok], rvs[ok], rvf[ok], tick[ok], mk[ok]
    spread = (j["ask"] - j["bid"]).to_numpy(float)
    lag = lag_spread.reindex(pd.Index(mk)).to_numpy(float) if lag_spread is not None else np.full(len(j), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        ivr = np.log(spread / rvs)
        ivr_lag = np.where(np.isfinite(lag) & (lag > 0), np.log(lag / rvs), np.nan)
    cnt["lag_missing"] = int((~np.isfinite(ivr_lag)).sum())
    rew, rewarded = _reward_cols(j, cnt)
    rms = j["rew_maxspread"].to_numpy(float)
    mid = j["mid"].to_numpy(float)
    in_band = _in_band(mid, spread, rms, spec["tests"]["CH197"]["reward_band"])
    mover = np.abs(j["x"].to_numpy(float)) >= spec["move"]["min_abs_x"] - 1e-12
    anat = np.where(mover, j["cls"].to_numpy(), "non_mover")
    u = pd.DataFrame({**_base_out(j, cap, k), "t_row": j["t_row"].to_numpy(float), "mid": mid, "spread": spread, "tick": tick, "liq": j["liq"].to_numpy(float),
                      "end_ts": j["end_ts"].to_numpy(float), "vol24": j["vol24"].to_numpy(float), "rv24": rv24, "rv24s": rvs, "rv_floor": rvf, "rv7d": rv7, "ivr": ivr,
                      "ivr_lag": ivr_lag, "spread_g": j["spread"].to_numpy(float), "rewarded": rewarded, "in_band": in_band, "anat": anat,
                      "rew_status": j["rew_status"].astype(str).to_numpy(), "rew_min": j["rew_min"].to_numpy(float), "osz": j["osz"].to_numpy(float)})
    cnt["in_band_unknown"] = int(u["in_band"].isna().sum())
    u = u[np.isfinite(u["rewarded"]) & np.isfinite(u["in_band"])].reset_index(drop=True)
    u["rv7ds"], u["rv7d_floor"] = floored_rv(u["rv7d"].to_numpy(float), u["tick"].to_numpy(float), c["rv_floor_ticks"])  # "likewise": rv7d is floored at half a tick too
    with np.errstate(invalid="ignore", divide="ignore"):
        u["ivr_g"] = np.log(u["spread_g"] / u["rv24s"])  # the origin's other spread definition (Gamma's field, the one the lag loader exposes)
    u["log_rv24s"], u["log_rv7d"] = np.log(u["rv24s"]), np.log(u["rv7ds"])
    u["log1p_vol"] = np.log1p(u["vol24"].clip(lower=0))
    u["spread_eq_tick"] = (np.abs(u["spread"] - u["tick"]) < 1e-9).astype(float)
    for nm in ("traded", "quote_only", "ambiguous", "never_traded"):
        u[f"an_{nm}"] = (u["anat"] == nm).astype(float)
    u = _common_cols(u)
    cnt["units"] = len(u)
    return u, cnt


# =====================================================================================================================
# Census statistics (counts only; design 7). Every threshold comes from the spec; nothing is tuned here.
# =====================================================================================================================


def exact_t_sum() -> float:
    """``t_{20, 1 - 0.05/6} + t_{20, 0.8}`` computed exactly (design 1.9: "computed exactly in code")."""
    from scipy import stats

    return float(stats.t.ppf(1.0 - 0.05 / 6.0, 20) + stats.t.ppf(0.8, 20))


def mde_common(spec: dict) -> dict:
    """The spec's ``mde_common`` with ``t_sum = max(declared 3.47, exact)`` (census-code check should-fix: the declared 3.47 is ~0.07% below
    the exact 3.4725..., so the census takes the larger, the pessimistic one)."""
    a = dict(spec["census_gates"]["mde_common"])
    a["t_sum_declared"], a["t_sum_exact"] = a["t_sum"], exact_t_sum()
    a["t_sum"] = max(float(a["t_sum"]), a["t_sum_exact"])
    return a


def block_min_units(covered_days: float, full: int = 16, window: float = 21.0) -> float:
    """``ceil(16 x covered_days / 21)``: the block gate's minimum of 16 shiftable units over 21 days scaled to the census length
    (R1 re-check must-fix 1): 2 for two days, 6 for seven, 3 for 2.75. NaN covered days give +inf (the gate fails)."""
    if not (isinstance(covered_days, (int, float)) and np.isfinite(covered_days) and covered_days > 0):
        return float("inf")
    return float(max(1, math.ceil(full * covered_days / window - 1e-9)))


def block_share(pop: pd.DataFrame, min_units: float) -> float:
    """Share of the population's units in markets holding at least ``min_units`` units of that population (the block-gate
    recurrence proxy). NaN for an empty population."""
    if pop.empty or not np.isfinite(min_units):
        return float("nan")
    n = pop.groupby("market_id")["market_id"].transform("size")
    return float((n >= min_units).mean())


def resid_iqr(pop: pd.DataFrame, y: str, xcols: list[str], min_units: int, iqr_min: float) -> dict:
    """Identification gate of a continuous state (1.0: residual IQR, never the raw IQR): pooled OLS of ``y`` on ``xcols`` (with an
    intercept, finite rows), then each market's IQR of the residual over markets with at least ``min_units`` such rows. Returns
    the share of those markets with IQR >= ``iqr_min`` and their number. The raw IQR is printed beside it, never gated."""
    cols = [y, *xcols]
    d = pop[["market_id", *cols]].copy()
    d[cols] = d[cols].astype(float).replace([np.inf, -np.inf], np.nan)
    d = d.dropna()
    if len(d) < len(cols) + 10:
        return {"share": float("nan"), "markets": 0, "raw_share": float("nan"), "n": len(d)}
    X = np.column_stack([np.ones(len(d)), d[xcols].to_numpy()]) if xcols else np.ones((len(d), 1))
    beta, *_ = np.linalg.lstsq(X, d[y].to_numpy(), rcond=None)
    d["_res"] = d[y].to_numpy() - X @ beta
    g = d.groupby("market_id")
    cnt = g["_res"].transform("size")
    dd = d[cnt >= min_units]
    if dd.empty:
        return {"share": float("nan"), "markets": 0, "raw_share": float("nan"), "n": len(d)}

    def iqr(s: pd.Series) -> float:
        return float(np.quantile(s, 0.75) - np.quantile(s, 0.25))

    ri = dd.groupby("market_id")["_res"].agg(iqr)
    raw = dd.groupby("market_id")[y].agg(iqr)
    return {"share": float((ri >= iqr_min).mean()), "markets": int(len(ri)), "raw_share": float((raw >= iqr_min).mean()), "n": len(d)}


def iqr_ok(r: dict, g: dict) -> bool:
    return bool(np.isfinite(r["share"]) and r["share"] >= g["resid_iqr_share_min"] and r["markets"] >= g["resid_iqr_markets_min"])


def terciles(z) -> tuple[float, float, float]:
    """(lower cut, upper cut, tercile gap = mean of the top tercile minus mean of the bottom tercile) of a standardised state."""
    z = np.asarray(z, float)
    z = z[np.isfinite(z)]
    if len(z) < 3:
        return float("nan"), float("nan"), float("nan")
    t1, t2 = np.quantile(z, [1 / 3, 2 / 3])
    return float(t1), float(t2), float(z[z >= t2].mean() - z[z <= t1].mean())


def standardise(x) -> tuple[float, float]:
    """(centre, scale) = mean and sample SD of the finite values (the census-fixed scale of a state)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan"), float("nan")
    return float(x.mean()), float(x.std(ddof=1))


def _de(pop: pd.DataFrame, scale: float, floor: float, a: dict) -> dict:
    de = b.design_effect(pop["event_id"].astype(str), scale, float(a["de_rho"]))
    de["DE_gate"] = b.de_gate(de, float(floor))
    return de


def contrast_ss(df: pd.DataFrame, terms: list[str], controls: list[str], plus: str, minus: str) -> dict:
    """Design-based effective residual SS of the contrast ``beta(plus) - beta(minus)`` in the within-market (expanding-past
    demeaned) model of ``terms + controls``: ``1 / c'(X'X)^{-1}c`` with an intercept, ``c = e_plus - e_minus``."""
    cols = [*terms, *controls]
    d = df[["market_id", "t_row", *cols]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < len(cols) + 10:
        return {"n": len(d), "ss_contrast": float("nan")}
    X = b.demean(d, cols, "market_id", "t_row", "expanding").replace([np.inf, -np.inf], np.nan).dropna()
    if len(X) < len(cols) + 10:
        return {"n": len(X), "ss_contrast": float("nan")}
    A = np.column_stack([np.ones(len(X)), X[cols].to_numpy()])
    inv = np.linalg.pinv(A.T @ A)
    i, j = 1 + cols.index(plus), 1 + cols.index(minus)
    f = float(inv[i, i] + inv[j, j] - 2.0 * inv[i, j])
    return {"n": int(len(X)), "ss_contrast": 1.0 / f if f > 0 else float("nan")}


def slope_mde(pop: pd.DataFrame, term: str, controls: list[str], scale: float, a: dict, de_gate: float, sd: float, gap: float) -> dict:
    """Slope MDE at the census tercile gap: ``max(declared, design)`` per SD of the standardised ``term`` (LT5 census-code check 3)
    times the gap, in cents. NaN anywhere gives inf (the gate fails)."""
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    dsg = b.design_ss(pop[eff], term, controls) if len(pop) else {"n": 0, "ss_resid": float("nan"), "vif_w": float("nan")}
    n_eff = float(eff.sum()) * scale
    per_sd = max(b.mde_slope_design(dsg["ss_resid"], scale, sd, de_gate, a), b.mde_slope_declared(n_eff, sd, de_gate, a, dsg["vif_w"]))
    mde_c = per_sd * gap * 100.0 if np.isfinite(gap) and np.isfinite(per_sd) else float("inf")
    return {"design": dsg, "n_eff_projected": n_eff, "mde_per_sd_c": per_sd * 100.0 if np.isfinite(per_sd) else float("inf"), "mde_tercile_c": mde_c}


def f_mde(slope_c: float, r_w: float, a: dict, *, design_ss: float | None = None, scale: float = 1.0, sd: float = 0.0, de_gate: float = float("nan"),
          gap: float = float("nan")) -> dict:
    """F-MDE (7): ``max(declared, design)``. Declared = the gated slope MDE x ``sqrt(2 / (1 - max(0, r_w)))``. Design (when an arm model
    exists) = ``t_sum x SD / sqrt(ss_contrast x scale) x sqrt(DE) x day x gap`` for the contrast. CH197 has no design arm (declared only).
    NaN anywhere gives inf."""
    if not (np.isfinite(slope_c) and np.isfinite(r_w)):
        return {"declared_c": float("inf"), "design_c": None, "f_mde_c": float("inf"), "r_w": r_w}
    declared = slope_c * math.sqrt(2.0 / (1.0 - max(0.0, r_w))) if r_w < 1.0 else float("inf")  # r_w >= 1: the contrast is not identified
    design = None
    if design_ss is not None:
        design = float(b.mde_slope_design(design_ss, scale, sd, de_gate, a) * gap * 100.0) if np.isfinite(gap) else float("inf")
    vals = [declared] + ([design] if design is not None else [])
    return {"declared_c": declared, "design_c": design, "f_mde_c": float(max(vals)) if all(np.isfinite(v) for v in vals) else float("inf"), "r_w": r_w}


def _gate_min_days(res: dict, key: str, covered_days: float, minimum: float) -> dict:
    """Below its minimum covered days every gate of the census is NaN and fails (design 7)."""
    res["covered_days"], res["min_covered_days"] = covered_days, minimum
    if not (np.isfinite(covered_days) and covered_days >= minimum):
        g = res.get(key, {})
        res[key] = {**{k_: False for k_ in g if k_ != "pass"}, "covered_days": False, "pass": False, "values_nan": True}
    else:
        res[key]["covered_days"] = True
    return res


def _fam(pop: pd.DataFrame, cap: float) -> tuple[pd.DataFrame, str, float | None]:
    return b._family_rule(pop, float(cap)) if len(pop) else (pop, "", None)


def _per_market(market_ids: pd.Series) -> dict:
    per = market_ids.astype(str).value_counts()
    dist = per.value_counts().sort_index()
    return {"markets": int(len(per)), "units": int(per.sum()), "units_per_market_hist": {str(int(k_)): int(v) for k_, v in dist.items()},
            "share_in_markets_with_one": float(market_ids.astype(str).map(per).eq(1).mean()) if len(market_ids) else float("nan")}


def _events(pop: pd.DataFrame, scale: float, covered_days: float) -> dict:
    """Events and the projected 21-day events (design 7): ``E_2d + (E_2d - E_day1) x 19`` for a two-day census, else distinct events x
    21 / covered days."""
    if pop.empty:
        return {"events": 0, "events_projected_21d": float("nan"), "covered_days": covered_days}
    ev = pop["event_id"].astype(str)
    days = sorted(pop["day"].astype(str).unique()) if "day" in pop else []
    e_all = int(ev.nunique())
    if len(days) == 2:
        e1 = int(ev[pop["day"].astype(str) == days[0]].nunique())
        return {"events": e_all, "events_day1": e1, "events_projected_21d": float(e_all + (e_all - e1) * 19), "rule": "E_2d + (E_2d - E_day1) x 19", "covered_days": covered_days}
    return {"events": e_all, "events_projected_21d": float(e_all * scale) if np.isfinite(scale) else float("nan"), "rule": "events x 21 / covered days", "covered_days": covered_days}


def _tier_shares(pop: pd.DataFrame, value: str, top_of: str | None = None) -> dict:
    """Descriptive: by liquidity tier (terciles of ``log1p_liq``) the mean of ``value`` (a 0/1 class) or, with ``top_of``, the share of units in
    the top tercile of that standardised state."""
    if pop.empty or pop["log1p_liq"].nunique() < 3:
        return {}
    tier = pd.qcut(pop["log1p_liq"], 3, labels=["low", "mid", "high"], duplicates="drop")
    if top_of:
        cut = np.quantile(pop[top_of].dropna(), 2 / 3)
        v = (pop[top_of] >= cut).astype(float)
    else:
        v = pop[value].astype(float)
    return {str(k_): {"units": int((tier == k_).sum()), "share": float(v[tier == k_].mean())} for k_ in tier.cat.categories}


def _share_by_tercile(pop: pd.DataFrame, z: str, value: str) -> dict:
    """Descriptive: the mean of a 0/1 ``value`` by tercile of the state ``z`` (rewarded share by tercile)."""
    if pop.empty or pop[z].notna().sum() < 3:
        return {}
    t1, t2 = np.quantile(pop[z].dropna(), [1 / 3, 2 / 3])
    grp = np.where(pop[z] <= t1, "bottom", np.where(pop[z] >= t2, "top", "middle"))
    return {k_: float(pop.loc[grp == k_, value].mean()) for k_ in ("bottom", "middle", "top")}


def unit_overlaps(frames: dict) -> dict:
    """Pairwise overlap of the populations of one census by (market, slot) key (1.11; descriptive, no gate). Cross-census overlaps are not
    computed (each census runs once on its own inputs)."""
    keys = {k_: set(zip(f["market_id"].astype(str), f["slot"], strict=True)) for k_, f in frames.items() if len(f)}
    out = {}
    names = sorted(keys)
    for i, a_ in enumerate(names):
        for b_ in names[i + 1:]:
            n = len(keys[a_] & keys[b_])
            out[f"{a_}&{b_}"] = {"units": n, f"share_of_{a_}": n / len(keys[a_]) if keys[a_] else float("nan"), f"share_of_{b_}": n / len(keys[b_]) if keys[b_] else float("nan")}
    return out


def _both_finite(c1: dict, c2: dict) -> list:
    """Both within-market correlations, or [] when either is missing or not finite: NaN fails the gate (verification note 1,
    2026-10-22), so one undefined origin definition cannot be replaced by the other."""
    vals = [c.get("within") for c in (c1, c2)]
    return [float(v) for v in vals] if all(v is not None and np.isfinite(v) for v in vals) else []


def _larger_pos_corr(c1: dict, c2: dict) -> float:
    """``max over both of max(0, r)``: the F-MDE form is ``sqrt(2 / (1 - max(0, r)))``, so the larger signed correlation is the pessimistic one."""
    vals = _both_finite(c1, c2)
    return float(max(max(0.0, v) for v in vals)) if vals else float("nan")


def _larger_abs_corr(c1: dict, c2: dict) -> float:
    """The within-market correlation of larger magnitude of two candidate origin definitions (the pessimistic one for an F-feasibility cap)."""
    vals = _both_finite(c1, c2)
    return float(max(vals, key=abs)) if vals else float("nan")


def _z(x, c: float, s: float) -> np.ndarray:
    return (np.asarray(x, float) - c) / s if np.isfinite(s) and s > 0 else np.full(len(x), np.nan)


def _desc_splits(tot: dict) -> dict:
    keys = ("sports", "sports_unknown", "crypto", "crypto_unknown")
    return {k_: int(tot.get(k_, 0)) for k_ in keys}


def _gate(d: dict) -> dict:
    d["pass"] = all(d.values())
    return d


CONTROLS_195 = ["a_traded", "a_parallel", "a_one_sided", "a_spread_change", "log_abs_x", "spread_sw_k", "spread_sw_p", "zh0", "logit_mid", "abs_dev",
                "log1p_vol_p", "log1p_liq", "d24", "d24_flag", "tick001", "log_hte", "hte_unknown"]
CONTROLS_191 = ["l_traded", "l_quote_only", "l_ambiguous", "l_never_traded", "log_abs_x6", "spread", "logit_mid", "abs_dev", "log1p_vol", "d24", "d24_flag",
                "log_rv24s", "rv_floor", "tick001", "log_hte", "hte_unknown"]
CONTROLS_197 = ["zimbT", "log1p_total5", "zh0", "spread_sw", "logit_mid", "abs_dev", "log1p_vol", "d24", "d24_flag", "rewarded", "in_band", "tick001", "log_hte", "hte_unknown"]
CONTROLS_193 = ["log_rv24s", "rv_floor", "spread", "logit_mid", "abs_dev", "log1p_vol_p", "log1p_liq", "d24", "d24_flag", "ltp_present", "tick001", "log_hte", "hte_unknown"]
CONTROLS_192 = ["log_rv24s", "rv_floor", "log_rv7d", "log1p_liq", "logit_mid", "abs_dev", "log1p_vol", "spread_eq_tick", "tick001", "an_traded", "an_quote_only",
                "an_ambiguous", "an_never_traded", "rewarded", "in_band", "log_hte", "hte_unknown"]


# --- CH195 (CS7) --------------------------------------------------------------------------------------------------------------------


def census_ch195(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float) -> dict:
    g, a = spec["census_gates"]["CS7_CH195"], mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CS7_CH195"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_CH195": {"pass": False}}, "gate_CH195", covered_days, mind)
    pop, excl, top = _fam(U, a["family_cap"])
    pop = pop.copy()
    c, s = standardise(np.concatenate([pop["R"].to_numpy(float), pop["R_away"].to_numpy(float)]))
    pop["zR"], pop["zR_away"] = _z(pop["R"], c, s), _z(pop["R_away"], c, s)
    hc, hs = standardise(pop["h0"])
    pop["zh0"] = _z(pop["h0"], hc, hs)
    pop["zdiff"] = pop["zR"] - pop["zR_away"]
    pop["traded"] = (pop["cls"] == "traded").astype(float)
    t1, t2, gap = terciles(pop["zR"])
    de = _de(pop, scale, g["de_floor"], a)
    ctrl = [*CONTROLS_195, "zR_away"]
    sm = slope_mde(pop, "zR", ctrl, scale, a, de["DE_gate"], a[g["sd"]], gap)
    corr_ra = b.wcorr(pop, "zR", "zR_away")
    r_w = corr_ra["within"] if corr_ra["within"] is not None else float("nan")
    arm = contrast_ss(pop[b._eff(pop)], ["zR", "zR_away"], CONTROLS_195, "zR", "zR_away")
    fm = f_mde(sm["mde_tercile_c"], r_w, a, design_ss=arm["ss_contrast"], scale=scale, sd=a[g["sd"]], de_gate=de["DE_gate"], gap=gap)
    ri = resid_iqr(pop, "R", ["R_away"], int(g["resid_iqr_min_units"]), g["resid_iqr_min"])
    corr = {nm: b.wcorr(pop, "zdiff", col) for nm, col in (("zh0", "zh0"), ("log_abs_x", "log_abs_x"), ("traded", "traded"))}
    cl = b.wcorr(pop, "zdiff", "log1p_liq")
    corr_vprev = b.wcorr(pop, "zdiff", "v_prev")
    bm = block_min_units(covered_days)
    bs = block_share(pop, bm)
    movers = tot.get("non_sports_ex_crypto_movers", 0)
    covered = tot.get("covered", 0)
    cov = covered / movers if movers else float("nan")
    agree = tot.get("covered_sign_agree", 0) / covered if covered else float("nan")
    projected = float(len(U) * scale)
    res = {"units": len(U), "projected_units_21d": projected, "both_sweep_coverage": cov, "sweep_sign_agreement": agree, "exclude_family": excl, "top_family_share": top,
           "R_R_away": {"centre": c, "scale": s}, "zR": {"terciles": [t1, t2], "tercile_gap": gap}, "design_effect": de, "slope": sm, "arm": arm, "F": fm,
           "resid_iqr": ri, "corr_zR_zR_away": corr_ra, "corr": corr, "corr_liq": cl, "corr_v_prev_printed": corr_vprev, "block_min_units": bm, "block_share": bs,
           "projected_units_21d_after_family_exclusion": float(len(pop) * scale), "liquidity_tiers_top_zR_share": _tier_shares(pop, "", "zR"),
           "events": _events(pop, scale, covered_days), "t_sum_used": a["t_sum"], "splits": _desc_splits(tot), "per_market": _per_market(pop["market_id"]),
           "by_anatomy": {str(k_): int(v_) for k_, v_ in pop["cls"].value_counts().items()}, "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_CH195"] = _gate({
        "coverage": bool(np.isfinite(cov) and cov >= g["coverage_min"]), "sign_agreement": bool(np.isfinite(agree) and agree >= g["sign_agree_min"]),
        "units": projected >= g["units_projected_min"], "resid_iqr": iqr_ok(ri, g),
        "corr_zR_zR_away": bool(corr_ra["within"] is not None and np.isfinite(corr_ra["within"]) and abs(corr_ra["within"]) <= g["corr_zR_zRaway_max"]),
        **{f"corr_{nm}": b.corr_ok(c_, g["corr_max"]) for nm, c_ in corr.items()}, "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True),
        "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]),
        "slope_mde": bool(sm["mde_tercile_c"] <= a["mde_max"] * 100.0), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max"] * 100.0)})
    return _gate_min_days(res, "gate_CH195", covered_days, mind)


# --- CH191 (CC7) --------------------------------------------------------------------------------------------------------------------


def census_ch191(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float) -> dict:
    g, a = spec["census_gates"]["CC7_CH191"], mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CC7"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_CH191": {"pass": False}}, "gate_CH191", covered_days, mind)
    n_all = len(U)
    contrast = U[U["cls6"].isin(["grind", "jump"])]
    pop, excl, top = _fam(contrast, a["family_cap"])
    pop = pop.copy()
    pop["z_d24"] = _z(pop["d24"], *standardise(pop["d24"]))
    pop["z_log_abs_x6"] = _z(pop["log_abs_x6"], *standardise(pop["log_abs_x6"]))
    eff = b._eff(pop) if len(pop) else pd.Series(dtype=bool)
    n1 = float(((pop["G"] == 1) & eff).sum() * scale)
    n2 = float(((pop["G"] == 0) & eff).sum() * scale)
    de = _de(pop, scale, g["de_floor"], a)
    dsg = b.design_ss(pop[eff], "G", CONTROLS_191) if len(pop) else {"n": 0, "ss_resid": float("nan"), "vif_w": float("nan")}
    vif = dsg["vif_w"]
    mde = (b.mde_class(n1, n2, a[g["sd"]], de["DE_gate"], a, vif) * 100.0) if np.isfinite(vif) else float("inf")
    corr = {nm: b.wcorr(pop, "G", col) for nm, col in (("traded_last", "traded_last"), ("own24", "z_d24"), ("log_abs_x6", "z_log_abs_x6"))}
    cl = b.wcorr(pop, "G", "log1p_liq")
    bm = block_min_units(covered_days)
    bs = block_share(pop, bm)
    projected = float(n_all * scale)
    sh = U["cls6"].value_counts(normalize=True)
    grind_sh, jump_sh = float(sh.get("grind", 0.0)), float(sh.get("jump", 0.0))
    m_ = pop[["market_id", "slot", "G"]]
    j7 = m_.merge(m_.assign(slot=m_["slot"] - 7), on=["market_id", "slot"], suffixes=("", "_7"))
    lag7 = float(j7["G"].corr(j7["G_7"])) if len(j7) > 10 else float("nan")
    lag7_within = float((j7["G"] - j7.groupby("market_id")["G"].transform("mean")).corr(j7["G_7"] - j7.groupby("market_id")["G_7"].transform("mean"))) if len(j7) > 10 else float("nan")
    res = {"units_6h_movers": n_all, "projected_units_21d": projected, "grind_share": grind_sh, "jump_share": jump_sh, "contrast_units": len(pop),
           "exclude_family": excl, "top_family_share": top, "class_eff_21d": {"grind": n1, "jump": n2}, "design_effect": de, "design": dsg,
           "mde_class_c": mde, "corr": corr, "corr_liq": cl, "block_min_units": bm, "block_share": bs, "events": _events(pop, scale, covered_days), "t_sum_used": a["t_sum"],
           "projected_units_21d_after_family_exclusion": float(len(pop) * scale), "liquidity_tiers_grind_share": _tier_shares(pop, "G"),
           "splits": _desc_splits(tot), "per_market": _per_market(pop["market_id"]), "by_class": {str(k_): int(v_) for k_, v_ in U["cls6"].value_counts().items()},
           "pc_quantiles": [float(x) for x in np.quantile(U["pc"], [0.1, 0.5, 0.9])], "sa_quantiles": [float(x) for x in np.quantile(U["sa"], [0.1, 0.5, 0.9])],
           "lag7_label_autocorr_pooled": lag7, "lag7_label_autocorr_within": lag7_within,
           "lost_to_every_step_tick_rule_share": tot.get("every_step_rule_loss", 0) / tot["movers_6h"] if tot.get("movers_6h") else float("nan"), "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_CH191"] = _gate({
        "units": projected >= g["units_projected_min"], "grind_share": grind_sh >= g["class_share_min"], "jump_share": jump_sh >= g["class_share_min"],
        **{f"corr_{nm}": b.corr_ok(c_, g["corr_max"]) for nm, c_ in corr.items()}, "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True),
        "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]), "class_mde": bool(mde <= a["mde_max"] * 100.0)})
    return _gate_min_days(res, "gate_CH191", covered_days, mind)


# --- CH197 (CS7) --------------------------------------------------------------------------------------------------------------------


def pair_correlations(pairs: pd.DataFrame, min_pairs: int) -> dict:
    """``r_w`` and ``r_pool`` of CH197's F-feasibility (R1 must-fix 1, re-check must-fix 2): ``pairs`` has one row per (market, pass j)
    with ``imb_j`` and ``imb_j13`` (``imbB`` of pass j and of pass j + 13) and ``t_row`` of pass j. Markets with at least
    ``min_pairs`` pairs; each member expanding-past demeaned over the market's pairs ordered by pass j (the first pair drops) for
    ``r_w``; ``r_pool`` is the pooled correlation over the same pairs. ``r_gate = max(r_w, r_pool)``; both are printed."""
    if pairs.empty:
        return {"r_w": float("nan"), "r_pool": float("nan"), "r_gate": float("nan"), "n_pairs": 0, "markets": 0}
    n = pairs.groupby("market_id")["market_id"].transform("size")
    p = pairs[n >= min_pairs]
    w = b.wcorr(p, "imb_j", "imb_j13") if len(p) else {"pooled": None, "within": None, "n": 0}
    r_w = float(w["within"]) if w["within"] is not None else float("nan")
    r_pool = float(w["pooled"]) if w["pooled"] is not None else float("nan")
    r_gate = float(max(r_w, r_pool)) if np.isfinite(r_w) and np.isfinite(r_pool) else float("nan")
    return {"r_w": r_w, "r_pool": r_pool, "r_gate": r_gate, "n_pairs": int(len(p)), "markets": int(p["market_id"].nunique()), "pairs_all": int(len(pairs))}


def census_ch197(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float, pairs: pd.DataFrame) -> dict:
    g, a = spec["census_gates"]["CS7_CH197"], mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CS7_CH197"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_CH197": {"pass": False}}, "gate_CH197", covered_days, mind)
    pop, excl, top = _fam(U, a["family_cap"])
    pop = pop.copy()
    cb, sb = standardise(pop["imbB"])
    ct, st_ = standardise(pop["imbT"])
    pop["zimbB"], pop["zimbT"] = _z(pop["imbB"], cb, sb), _z(pop["imbT"], ct, st_)
    hc, hs = standardise(pop["h0"])
    pop["zh0"] = _z(pop["h0"], hc, hs)
    pop["z_d24"] = _z(pop["d24"], *standardise(pop["d24"]))
    t1, t2, gap = terciles(pop["zimbB"])
    de = _de(pop, scale, g["de_floor"], a)
    sm = slope_mde(pop, "zimbB", CONTROLS_197, scale, a, de["DE_gate"], a[g["sd"]], gap)
    pc = pair_correlations(pairs, int(g["r_min_pairs"]))
    fm = f_mde(sm["mde_tercile_c"], pc["r_gate"], a)
    corr_tb = b.wcorr(pop, "imbT", "imbB")
    corr_d24 = b.wcorr(pop, "zimbB", "z_d24")
    cl = b.wcorr(pop, "zimbB", "log1p_liq")
    nd = pop.groupby("market_id")["day"].transform("nunique")
    both = pop[nd >= 2]
    strata = float((nd >= 2).mean())
    if len(both):
        first = both.sort_values("t_row").groupby("market_id")["imbB"].first()
        last = both.sort_values("t_row").groupby("market_id")["imbB"].last()
        diff_share = float(((last - first).abs() >= g["day_diff_min"] - 1e-12).mean())
    else:
        diff_share = float("nan")
    books = tot.get("books_in_band", 0)
    covered_share = len(U) / books if books else float("nan")
    projected = float(len(U) * scale)
    res = {"units": len(U), "projected_units_21d": projected, "covered_share": covered_share, "exclude_family": excl, "top_family_share": top,
           "imbB": {"centre": cb, "scale": sb}, "imbT": {"centre": ct, "scale": st_}, "zimbB": {"terciles": [t1, t2], "tercile_gap": gap}, "design_effect": de, "slope": sm,
           "pairs": pc, "F": fm, "corr_imbT_imbB": corr_tb, "corr_imbT_1c_form_printed": b.wcorr(pop, "imbT", "imbT1"), "t_sum_used": a["t_sum"],
           "projected_units_21d_after_family_exclusion": float(len(pop) * scale), "liquidity_tiers_top_zimbB_share": _tier_shares(pop, "", "zimbB"),
           "rewarded_share_by_zimbB_tercile": _share_by_tercile(pop, "zimbB", "rewarded"), "corr_own24": corr_d24, "corr_liq": cl, "day_diff_share": diff_share, "market_strata_share": strata,
           "events": _events(pop, scale, covered_days), "splits": _desc_splits(tot), "per_market": _per_market(pop["market_id"]),
           "rewarded_share": float(pop["rewarded"].mean()), "rewarded_x_in_band": rewarded_x_in_band(pop), "imb_quantiles": {nm: [float(x) for x in np.quantile(pop[nm], [0.1, 0.5, 0.9])] for nm in ("imbT", "imbB", "dis")},
           "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_CH197"] = _gate({
        "covered_share": bool(np.isfinite(covered_share) and covered_share >= g["covered_share_min"]), "units": projected >= g["units_projected_min"],
        "corr_imbT_imbB": bool(corr_tb["within"] is not None and np.isfinite(corr_tb["within"]) and abs(corr_tb["within"]) <= g["corr_imbT_imbB_max"]),
        "day_diff_share": bool(np.isfinite(diff_share) and diff_share >= g["day_diff_share_min"]), "market_strata": strata >= g["market_strata_share_min"],
        "corr_own24": b.corr_ok(corr_d24, g["corr_max"]), "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True),
        "slope_mde": bool(sm["mde_tercile_c"] <= a["mde_max"] * 100.0), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max"] * 100.0),
        "r_gate": bool(np.isfinite(pc["r_gate"]) and pc["r_gate"] <= g["r_gate_max"])})
    return _gate_min_days(res, "gate_CH197", covered_days, mind)


# --- CH193 (CC7) --------------------------------------------------------------------------------------------------------------------


def census_ch193(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float) -> dict:
    """CC7's half of CH193's gate; the other half is CV7's semantic gate (``census_volsem``). CH193 survives only if both pass."""
    g, a = spec["census_gates"]["CC7_CH193"], mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CC7"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_CH193": {"pass": False}}, "gate_CH193", covered_days, mind)
    pop, excl, top = _fam(U, a["family_cap"])
    pop = pop.copy()
    c, s = standardise(pop["ldv"])
    pop["zldv"], pop["zldv_lag"] = _z(pop["ldv"], c, s), _z(pop["ldv_lag"], c, s)
    pop["z_log1p_vol_p"] = _z(pop["log1p_vol_p"], *standardise(pop["log1p_vol_p"]))
    pop["z_log_rv24s"] = _z(pop["log_rv24s"], *standardise(pop["log_rv24s"]))
    t1, t2, gap = terciles(pop["zldv"])
    de = _de(pop, scale, g["de_floor"], a)
    sm = slope_mde(pop, "zldv", CONTROLS_193, scale, a, de["DE_gate"], a[g["sd"]], gap)
    arm_pop = pop[np.isfinite(pop["zldv_lag"])].copy()
    corr_lag = b.wcorr(arm_pop, "zldv", "zldv_lag")
    r_w = corr_lag["within"] if corr_lag["within"] is not None else float("nan")
    arm = contrast_ss(arm_pop[b._eff(arm_pop)], ["zldv", "zldv_lag"], [*CONTROLS_193, "lag_rolloff"], "zldv", "zldv_lag") if len(arm_pop) else {"n": 0, "ss_contrast": float("nan")}
    fm = f_mde(sm["mde_tercile_c"], r_w, a, design_ss=arm["ss_contrast"], scale=scale, sd=a[g["sd"]], de_gate=de["DE_gate"], gap=gap)
    ri = resid_iqr(pop, "ldv", ["log_rv24s", "log1p_vol_p"], int(g["resid_iqr_min_units"]), g["resid_iqr_min"])
    corr = {"log1p_vol_p": b.wcorr(pop, "zldv", "z_log1p_vol_p"), "log_rv24s": b.wcorr(pop, "zldv", "z_log_rv24s")}
    cl = b.wcorr(pop, "zldv", "log1p_liq")
    bm = block_min_units(covered_days)
    bs = block_share(pop, bm)
    elig = tot.get("eligible", 0)
    vshare = tot.get("volume_present", 0) / elig if elig else float("nan")
    projected = float(len(U) * scale)
    lp = float(U["ltp_present"].mean())
    assign = float(((U["ltp"] == U["ask"]) | (U["ltp"] == U["bid"])).mean())
    with np.errstate(invalid="ignore"):
        rolloff_share = tot.get("rolloff_negative_dv", 0) / tot["volume_present"] if tot.get("volume_present") else float("nan")
    res = {"units": len(U), "traded_non_movers_projected_21d": projected, "volume_present_share": vshare, "exclude_family": excl, "top_family_share": top,
           "z_log1p_dV": {"centre": c, "scale": s, "terciles": [t1, t2], "tercile_gap": gap}, "design_effect": de, "slope": sm, "arm": arm, "arm_units": len(arm_pop),
           "arm_share": len(arm_pop) / len(pop) if len(pop) else float("nan"), "F": fm, "resid_iqr": ri, "corr": corr, "corr_liq": cl, "corr_lag": corr_lag,
           "block_min_units": bm, "block_share": bs, "events": _events(pop, scale, covered_days), "splits": _desc_splits(tot), "per_market": _per_market(pop["market_id"]),
           "t_sum_used": a["t_sum"], "projected_units_21d_after_family_exclusion": float(len(pop) * scale), "liquidity_tiers_top_zdV_share": _tier_shares(pop, "", "zldv"),
           "dV_quantiles": [float(x) for x in np.quantile(U["dV"], [0.1, 0.5, 0.9])], "rolloff_negative_dv_share": rolloff_share,
           "dV_lag_negative_share": float(np.nanmean(U["lag_rolloff"])) if U["lag_rolloff"].notna().any() else float("nan"),
           "dV_lag_missing_share": float(U["dV_lag"].isna().mean()), "last_print_present_share": lp, "last_print_assignable_share": assign,
           "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_CH193"] = _gate({
        "volume_present": bool(np.isfinite(vshare) and vshare >= g["volume_present_share_min"]), "units": projected >= g["units_projected_min"], "resid_iqr": iqr_ok(ri, g),
        **{f"corr_{nm}": b.corr_ok(c_, g["corr_max"]) for nm, c_ in corr.items()}, "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True),
        "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]), "slope_mde": bool(sm["mde_tercile_c"] <= a["mde_max"] * 100.0),
        "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max"] * 100.0),
        "corr_lag": bool(np.isfinite(r_w) and abs(r_w) <= g["lag_corr_max"])})
    res["requires"] = "CV7 gate_CH193_semantic must also pass"
    return _gate_min_days(res, "gate_CH193", covered_days, mind)


# --- CH192 (CC7) --------------------------------------------------------------------------------------------------------------------


def census_ch192(U: pd.DataFrame, tot: dict, spec: dict, scale: float, covered_days: float) -> dict:
    g, a = spec["census_gates"]["CC7_CH192"], mde_common(spec)
    mind = spec["census_inputs"]["min_covered_days"]["CC7_CH192"]
    if U.empty:
        return _gate_min_days({"error": "no units", "gate_CH192": {"pass": False}}, "gate_CH192", covered_days, mind)
    pop, excl, top = _fam(U, a["family_cap"])
    pop = pop.copy()
    c, s = standardise(pop["ivr"])
    pop["zivr"], pop["zivr_lag"] = _z(pop["ivr"], c, s), _z(pop["ivr_lag"], c, s)
    pop["z_log_rv24s"] = _z(pop["log_rv24s"], *standardise(pop["log_rv24s"]))
    t1, t2, gap = terciles(pop["zivr"])
    de = _de(pop, scale, g["de_floor"], a)
    sm = slope_mde(pop, "zivr", CONTROLS_192, scale, a, de["DE_gate"], a[g["sd"]], gap)
    arm_pop = pop[np.isfinite(pop["zivr_lag"])].copy()
    corr_lag = b.wcorr(arm_pop, "ivr", "ivr_lag")
    corr_lag_g = b.wcorr(arm_pop, "ivr_g", "ivr_lag")  # the origin spread as Gamma's field, the lag's definition
    r_w = _larger_abs_corr(corr_lag, corr_lag_g)  # the GATE uses the larger |r| of the two origin definitions (census-code check should-fix)
    r_f = _larger_pos_corr(corr_lag, corr_lag_g)  # the F-MDE uses the larger SIGNED r: max over both of max(0, r), so it stays pessimistic
    agree = float((np.abs(U["spread"] - U["spread_g"]) < 1e-9).mean())
    arm = contrast_ss(arm_pop[b._eff(arm_pop)], ["zivr", "zivr_lag"], CONTROLS_192, "zivr", "zivr_lag") if len(arm_pop) else {"n": 0, "ss_contrast": float("nan")}
    fm = f_mde(sm["mde_tercile_c"], r_f, a, design_ss=arm["ss_contrast"], scale=scale, sd=a[g["sd"]], de_gate=de["DE_gate"], gap=gap)
    ri = resid_iqr(pop, "ivr", ["log_rv24s", "log_rv7d"], int(g["resid_iqr_min_units"]), g["resid_iqr_min"])
    corr_rv = b.wcorr(pop, "zivr", "z_log_rv24s")
    cl = b.wcorr(pop, "zivr", "log1p_liq")
    bm = block_min_units(covered_days)
    bs = block_share(pop, bm)
    floor_share = float(U["rv_floor"].mean())
    projected = float(len(U) * scale)
    res = {"units": len(U), "projected_units_21d": projected, "rv_floor_share": floor_share, "exclude_family": excl, "top_family_share": top,
           "zivr": {"centre": c, "scale": s, "terciles": [t1, t2], "tercile_gap": gap}, "design_effect": de, "slope": sm, "arm": arm, "arm_units": len(arm_pop),
           "arm_share": len(arm_pop) / len(pop) if len(pop) else float("nan"), "F": fm, "resid_iqr": ri, "corr_zivr_log_rv24": corr_rv, "corr_liq": cl, "corr_lag": corr_lag, "corr_lag_gamma_origin_spread": corr_lag_g, "r_w_used": r_w, "r_f_used": r_f,
           "origin_spread_definitions_agree_share": agree, "rv7d_floor_share": float(U["rv7d_floor"].mean()), "t_sum_used": a["t_sum"],
           "projected_units_21d_after_family_exclusion": float(len(pop) * scale), "rewarded_share_by_zivr_tercile": _share_by_tercile(pop, "zivr", "rewarded"),
           "liquidity_tiers_top_zivr_share": _tier_shares(pop, "", "zivr"), "block_min_units": bm, "block_share": bs, "events": _events(pop, scale, covered_days), "splits": _desc_splits(tot), "per_market": _per_market(pop["market_id"]),
           "ivr_quantiles": [float(x) for x in np.quantile(U["ivr"], [0.1, 0.5, 0.9])], "tick_floor_share": float(U["spread_eq_tick"].mean()),
           "rewarded_share": float(U["rewarded"].mean()), "rewarded_x_in_band": rewarded_x_in_band(U), "counts": {k_: v_ for k_, v_ in tot.items() if isinstance(v_, (int, float))}}
    res["gate_CH192"] = _gate({
        "units": projected >= g["units_projected_min"], "rv_floor_share": bool(np.isfinite(floor_share) and floor_share <= g["rv_floor_share_max"]), "resid_iqr": iqr_ok(ri, g),
        "corr_zivr_log_rv24": bool(corr_rv["within"] is not None and np.isfinite(corr_rv["within"]) and abs(corr_rv["within"]) <= g["corr_zivr_logrv_max"]),
        "corr_liq": b.corr_ok(cl, g["corr_liq_max"], both=True), "block_share": bool(np.isfinite(bs) and bs >= g["block_share_min"]),
        "slope_mde": bool(sm["mde_tercile_c"] <= a["mde_max"] * 100.0), "f_mde": bool(fm["f_mde_c"] <= a["f_mde_max"] * 100.0),
        "corr_lag": bool(np.isfinite(r_w) and abs(r_w) <= g["lag_corr_max"])})
    return _gate_min_days(res, "gate_CH192", covered_days, mind)


# =====================================================================================================================
# Sealed inputs and the census drivers (design 7: "the census refuses unless every input file it opens is named in the LT7 seal
# with an equal sha256, and refuses if a sealed file in a needed slot is absent")
# =====================================================================================================================


def _merge_counts(tot: dict, cnt: dict) -> None:
    for a_, v in cnt.items():
        if isinstance(v, dict):
            d = tot.setdefault(a_, {})
            for kk, vv in v.items():
                d[kk] = d.get(kk, 0) + vv
        elif isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
            tot[a_] = tot.get(a_, 0) + v


def _span(spec: dict) -> tuple[int, int]:
    sp = spec["census_inputs"]["cc7_span"]
    return b.slot_of(epoch(sp["first_slot_utc"]), spec), b.slot_of(epoch(sp["last_slot_utc"]), spec)


def cc7_slots(spec: dict) -> dict:
    """The slots CC7 opens (shared by the seal builder and the census). ``O7``: every grid slot of ``cc7_origin_days_utc`` (CH191, CH193);
    ``O192``: the four declared slots of ``ch192_days_utc``. ``full``: slots read in full (origins and their look-backs k - 12 .. k, and
    k - 84 .. k for CH192). ``lag``: slots read ONLY through the lag-slot loader (k + 2, k + 3). ``caps`` = full | lag, inside the span."""
    ci = spec["census_inputs"]
    first, last = _span(spec)
    o7 = [k for k in b.census_slots(ci["cc7_origin_days_utc"], spec) if first <= k <= last]
    o192 = [k for k in b.census_slots(ci["ch192_days_utc"], spec) if first <= k <= last and slot_in_day(k) in spec["tests"]["CH192"]["slot_index_in_day"]]
    full: set[int] = set()
    lag: set[int] = set()
    for k in o7:
        full |= set(range(k - 12, k + 1))
        lag |= {k + 2, k + 3}
    for k in o192:
        full |= set(range(k - 84, k + 1))
        lag |= {k + 3}
    full = {j for j in full if first <= j <= last}
    lag = {j for j in lag if first <= j <= last} - full
    return {"O7": sorted(o7), "O192": sorted(o192), "full": full, "lag": lag, "caps": full | lag}


def cs7_slots(spec: dict, sweep_avail: set[int]) -> dict:
    """The slots CS7 opens. ``K``: grid slots of ``cs7_days_utc`` inside the span. Sweeps k - 1 and k of every pass; captures k - 12, k - 1, k
    (``full``). CH197's F-feasibility pairs: every pass j whose sweep AND pass j + 13's sweep are available (``sweep_avail``): the
    sweep of pass j (full), captures j - 1 and j (full), and pass j + 13's sweep and capture (``lag``: read only through
    :func:`lag_sweep`, whose token key comes from that pass's capture rows)."""
    first, last = _span(spec)
    K = [k for k in b.census_slots(spec["census_inputs"]["cs7_days_utc"], spec) if first <= k <= last]
    full: set[int] = set()
    sweeps: set[int] = set()
    lag: set[int] = set()
    for k in K:
        full |= {k - 12, k - 1, k}
        sweeps |= {k - 1, k}
    pairs = sorted(j for j in sweep_avail if (j + 13) in sweep_avail)
    for j in pairs:
        full |= {j - 1, j}
        sweeps |= {j, j + 13}
        lag |= {j + 13}
    full = {j for j in full if first <= j <= last}
    lag = {j for j in lag if first <= j <= last} - full
    return {"K": K, "pairs": pairs, "full": full, "lag": lag, "caps": full | lag, "sweeps": sweeps}


def bound_violations(seal: dict, spec: dict) -> list[dict]:
    """Refuse anything at or after the sealed bound (``census_inputs.refuse_at_or_after_utc``): the span itself, and every slot the seal
    assigns to a directory."""
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    bad = []
    last = epoch(spec["census_inputs"]["cc7_span"]["last_slot_utc"])
    if last >= bound:
        bad.append({"what": "span.last_slot_utc", "value": spec["census_inputs"]["cc7_span"]["last_slot_utc"], "error": "at or after the sealed bound"})
    for d, s in (seal.get("slots") or {}).items():
        if epoch(s) >= bound:
            bad.append({"what": d, "value": s, "error": "at or after the sealed bound"})
    if seal.get("written_utc") is None:
        bad.append({"what": "written_utc", "error": "seal not stamped"})
    return bad


def _src_hashes(source_seals: list[Path]) -> tuple[dict, list, dict]:
    """(rel path -> sha256, sample ids, seal shas) of the source seals; a file named with two different hashes is an error."""
    src: dict[str, str] = {}
    samples: list[str] = []
    shas: dict[str, str] = {}
    for pth in source_seals:
        d = json.loads(Path(pth).read_text())
        shas[str(pth)] = sha256_file(Path(pth))
        for rel, v in (d.get("files") or {}).items():
            sha = v["sha256"] if isinstance(v, dict) else v
            if rel in src and src[rel] != sha:
                raise ValueError(f"source seals name {rel} with two different hashes")
            src[rel] = sha
        samples += [s for s in d.get("samples", []) if s not in samples]
    return src, samples, shas


def _seal_scan(seal: dict, snapshot_root, sweep_root, work: Path, spec: dict) -> tuple[dict, dict]:
    """Complete captures and sweeps found locally, restricted to those the seal names (a local file the seal does not name is never
    opened: its slot counts as unsealed / missing)."""
    by_slot, sweeps = b._scan(Path(work), snapshot_root, sweep_root, spec)
    sealed = set(seal.get("slots", {}))
    by_slot = {k: c for k, c in by_slot.items() if c["id"] in sealed}
    sweeps = {sid: v for sid, v in sweeps.items() if Path(v["dir"]).name in sealed}
    return by_slot, sweeps


SAMPLE_FILES = ("features.csv.gz", "manifest.json", "trades.csv.gz")  # the files CV7 opens (plan.json is not opened)


def _sample_rels(sid: str) -> list[str]:
    return [f"data-dumps/research_lab/trade_samples/{sid}/{fn}" for fn in SAMPLE_FILES]


DESIGN_TEXT_SHA256 = "31baf5e5b5c1bec2518228618fc21ab7f111c0e673d6cb064583ce1363d20dd4"  # LIVE_TESTS_7.md with the 13.6 reward-null amendment (2026-10-22)
# Earlier design texts whose seals stay valid. The committed seal (seals/lt7_census_inputs.json, sha256 117e9b45...) records the text-freeze hash; section 13.6
# changes units and control coding, not the sealed inputs, so that seal is accepted and never re-written. Anything not listed here refuses.
DESIGN_TEXT_PREDECESSORS = {
    "840f4500cde37158f57f6cf6bf54a3535ee5b24f3e5dedfd9240b315eeb52899": "design text freeze (cedfd6be), superseded by the 13.6 reward-null amendment, 2026-10-22",
}
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_7.md"
SPEC_HASHED_BLOCKS = ("census_gates", "census_inputs", "tests", "move", "eligibility", "grid", "crypto_classifier", "sports_rule", "series_key_rule")


def spec_blocks_sha(spec: dict) -> str:
    """sha256 of the canonical JSON of every spec block census code reads (``SPEC_HASHED_BLOCKS``: census_gates, census_inputs, tests, move,
    eligibility, grid, crypto_classifier, sports_rule, series_key_rule). The seal stores it; every census refuses a spec whose blocks differ
    from the seal-time ones (must-fix 2 and its follow-up). ``census_fixed`` is deliberately outside the hash."""
    import hashlib

    blob = json.dumps({k_: spec[k_] for k_ in SPEC_HASHED_BLOCKS}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def design_text_sha() -> str:
    """sha256 of ``docs/research_lab/LIVE_TESTS_7.md`` itself (computed, never copied from the spec)."""
    return sha256_file(DESIGN_PATH)


def seal_design_accepted(seal_design_sha: str | None) -> bool:
    """A seal is accepted iff the design hash it records is the current one or a declared predecessor (``DESIGN_TEXT_PREDECESSORS``)."""
    return seal_design_sha == DESIGN_TEXT_SHA256 or seal_design_sha in DESIGN_TEXT_PREDECESSORS


def design_text_error() -> dict | None:
    got = design_text_sha()
    return None if got == DESIGN_TEXT_SHA256 else {"error": "LIVE_TESTS_7.md differs from the text-frozen file: refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}


def load_unavailable(items) -> set[str]:
    """The explicit ``--unavailable`` list (census-code check must-fix 1): archive paths (``data-dumps/research_lab/...``) that q0600's restore
    report says no release holds. Each item is a JSON file (a list of paths, or a restore report whose ``missing`` / ``unavailable`` /
    ``not_found`` list names them) or a plain archive path."""
    out: set[str] = set()
    for it in items or []:
        p = Path(str(it))
        if p.is_file():
            d = json.loads(p.read_text())
            lists = [d] if isinstance(d, list) else [d.get(k_) or [] for k_ in ("missing", "unavailable", "not_found")]
            for lst in lists:
                out |= {str(x["path"] if isinstance(x, dict) else x) for x in lst}
        else:
            out.add(str(it))
    return out


def _dir_slot(name: str, spec: dict) -> int | None:
    t = b._name_time(name)
    return b.slot_of(t, spec) if np.isfinite(t) else None


def _find(roots, name: str, fn: str) -> Path | None:
    return next((Path(r) / name / fn for r in roots if (Path(r) / name / fn).exists()), None)


def _series_index(d: Path):
    """``series_index`` from a sweep directory's manifest (None if unreadable)."""
    try:
        return b._manifest(Path(d) / "manifest.json").get("series_index")
    except (OSError, ValueError):
        return None


def seal_inputs(*, snapshot_root, sweep_root, sample_root, work: Path, source_seals: list[Path], spec: dict | None = None, unavailable=None) -> dict:
    """The LT7 seal (design 7). Selection rule: a capture (every file the source seals name for its directory: rows, manifest and the sidecar),
    a sweep 1 or a sample is selected only if EVERY such file exists locally and is named in a source seal (LT5's capture seal, LT3's C2 sample
    seal, LT4's capture seal) with an equal sha256, and its slot is one the censuses open (:func:`cc7_slots`, :func:`cs7_slots`, CV7's k - 1 and
    k of each sample). A mismatch refuses the seal. **A source-sealed file that is absent locally in a needed slot refuses the seal** (must-fix 1:
    a sidecar that was not restored must not turn a capture into a quiet ``sports = -1`` one) unless the path is listed in ``unavailable`` (the
    q0600 restore report says no release holds it): then its directory is not selected and the slot is counted missing, listed under
    ``unavailable_used``. A slot with nothing sealed is genuinely missing (counted per census, never substituted). Hashes bytes only; parses no
    rows (the sample and capture manifests are read for the slot assignment); nothing at or after the bound is hashed."""
    spec = spec or load_spec(sha=None)
    if (derr := design_text_error()):
        return derr
    unavail = load_unavailable(unavailable) if not isinstance(unavailable, set) else unavailable
    src, samples, shas = _src_hashes(list(source_seals))
    ss = spec["census_inputs"].get("source_seals") or {}
    pin = ss.get("lt5_capture_seal_sha256")
    if not pin:
        return {"error": "spec census_inputs.source_seals.lt5_capture_seal_sha256 is null: the LT7 seal is refused until the LT5 capture seal's sha256 is pinned"}
    cap_rel = ss.get("captures")
    cap_abs = (ROOT / cap_rel) if cap_rel else None
    named = {k_: v_ for k_, v_ in shas.items() if cap_rel and (Path(k_) == cap_abs or Path(k_).as_posix().endswith(Path(cap_rel).as_posix()))}
    if not named:
        return {"error": "no source seal given is the file named by census_inputs.source_seals.captures: LT7 seal refused", "captures": cap_rel, "given": shas}
    if pin not in named.values():
        return {"error": "the source seal census_inputs.source_seals.captures does not have the pinned lt5_capture_seal_sha256: LT7 seal refused", "pinned": pin, "given": named}
    smp_roots = b._roots(sample_root)
    by_slot, sweeps = b._scan(Path(work), snapshot_root, sweep_root, spec)
    bound = epoch(spec["census_inputs"]["refuse_at_or_after_utc"])
    sha_cache: dict[str, str] = {}
    mism: list[dict] = []
    not_sel: list[dict] = []
    absent: list[str] = []
    unavail_used: list[str] = []
    bad_dirs: set[str] = set()  # directories with a file the restore report lists as unavailable: never selected

    def hsha(pth: Path) -> str:
        key = str(pth)
        if key not in sha_cache:
            sha_cache[key] = sha256_file(pth)
        return sha_cache[key]

    def dir_rels(sub: str, name: str) -> list[str]:
        pre = f"data-dumps/research_lab/{sub}/{name}/"
        return sorted(r for r in src if r.startswith(pre))

    def audit(name: str, chosen: Path | None, rels: list[str]) -> None:
        """Every source-sealed file of directory ``name`` must exist in the directory the scan CHOSE (``chosen``: the one the census would open),
        unless the restore report lists it as unavailable. A directory split across roots (rows in one, the sidecar in another) is therefore
        refused here, not quietly counted missing; no chosen directory means every file is absent."""
        for rel in rels:
            if rel in unavail:
                unavail_used.append(rel)
                bad_dirs.add(name)
            elif chosen is None or not (Path(chosen) / rel.rsplit("/", 1)[1]).exists():
                absent.append(rel)

    def check(rels: list[tuple[str, Path]]) -> tuple[bool, dict, list, list]:
        ok, got, mm, ns = True, {}, [], []
        for rel, pth in rels:
            want = src.get(rel)
            if want is None:
                ns.append({"file": rel, "reason": "not named in any source seal"})
                ok = False
                continue
            if not Path(pth).exists():
                ns.append({"file": rel, "reason": "absent locally"})
                ok = False
                continue
            sha = hsha(Path(pth))
            if sha != want:
                mm.append({"file": rel, "want": want, "got": sha})
                ok = False
                continue
            got[rel] = sha
        return ok, got, mm, ns

    def rel_list(sub: str, d: Path, fallback: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
        """The local capture's own files plus every file the source seals name for the directory (a sealed sidecar is never dropped)."""
        out = {rel: pth for rel, pth in fallback}
        for rel in dir_rels(sub, d.name):
            out.setdefault(rel, d / rel.rsplit("/", 1)[1])
        return sorted(out.items())

    sweep_dirs = {Path(v["dir"]).name: Path(v["dir"]) for v in sweeps.values()}
    first, last = _span(spec)
    src_sweep_slots = {k for k in (_dir_slot(d, spec) for d in b.sealed_dirs({"files": src}, "book_sweeps")) if k is not None and first <= k <= last}
    # --- sweeps: which passes have a selectable sweep 1 (a dry check; only the needed ones are committed below)
    sweep_ok: dict[int, tuple[Path, dict]] = {}
    for k in range(first, last + 1):
        c = by_slot.get(k)
        if c is None or c["start"] >= bound or c["id"] not in sweeps:
            continue
        sd = Path(sweeps[c["id"]]["dir"])
        ok, got, mm, ns = check(rel_list("book_sweeps", sd, b.sweep_files(sd)))
        mism += mm
        if ok:
            sweep_ok[k] = (sd, got)
        else:
            not_sel += ns
    avail = set(sweep_ok) | src_sweep_slots
    c7, s7 = cc7_slots(spec), cs7_slots(spec, avail)
    # --- CV7: samples and the captures k - 1, k of each (the slot comes from the sample manifest's snapshot id, so a capture that is not
    # local cannot make a sample silently disappear)
    days = {d.replace("-", "") for d in spec["census_inputs"]["cv7_sample_days_utc"]}
    used_samples: list[str] = []
    sample_slot: dict[str, int] = {}
    sample_files: dict[str, dict] = {}
    for sid in samples:
        if sid[:8] not in days:
            continue
        rels = _sample_rels(sid)
        sdir = next((r / sid for r in smp_roots if (r / sid / "trades.csv.gz").exists()), None)
        audit(sid, sdir, rels)
        if sdir is None or sid in bad_dirs:
            not_sel.append({"sample": sid, "reason": "absent locally or listed unavailable by the restore report"})
            continue
        ok, got, mm, ns = check([(rel, sdir / rel.rsplit("/", 1)[1]) for rel in rels])
        mism += mm
        if not ok:
            not_sel += ns
            continue
        k = _dir_slot(str(b._manifest(sdir / "manifest.json").get("snapshot_id")), spec)
        if k is None:
            not_sel.append({"sample": sid, "reason": "its snapshot id is on no grid slot"})
            continue
        used_samples.append(sid)
        sample_slot[sid] = k
        sample_files[sid] = {rel: {"sha256": sha, "root": str(sdir.parent)} for rel, sha in got.items()}
    cv_caps = {j for k in sample_slot.values() for j in (k - 1, k)}
    need_caps = c7["caps"] | s7["caps"] | cv_caps
    # --- the absence audit (must-fix 1): every source-sealed file of a needed slot exists locally or is listed unavailable
    for d in b.sealed_dirs({"files": src}, "snapshots"):
        k = _dir_slot(d, spec)
        if k is not None and k in need_caps:
            c_ = by_slot.get(k)
            audit(d, Path(c_["dir"]) if c_ is not None and Path(c_["dir"]).name == d else None, dir_rels("snapshots", d))
    sw_roots = b._roots(sweep_root)
    for d in b.sealed_dirs({"files": src}, "book_sweeps"):
        k = _dir_slot(d, spec)
        if k is not None and k in s7["sweeps"]:
            # a sweep 1 is audited in the directory the scan chose; any other sealed sweep of the pass (sweep 2, never opened by
            # LT7) in the first root that holds it, as the vendored ``seal_completeness`` does (fix 2026-10-22: q0601 refused
            # because sweep-2 directories, absent from the sweep-1 map, were all reported absent although present locally)
            home = sweep_dirs.get(d)
            if home is None:
                alt = next((Path(r) / d for r in sw_roots if (Path(r) / d).is_dir()), None)
                # only a sweep 2 may be found this way; a sweep 1 the scan skipped (e.g. incomplete) stays absent (review 2026-10-22)
                if alt is not None and _series_index(alt) not in (None, 0):
                    home = alt
            audit(d, home, dir_rels("book_sweeps", d))
    if absent:
        return {"error": "a source-sealed file is absent locally in a needed slot: LT7 seal refused (restore it, or list it with --unavailable from q0600's restore report)",
                "absent": sorted(set(absent))[:50], "n_absent": len(set(absent))}
    files: dict[str, dict] = {}
    slots: dict[str, str] = {}
    sel_caps: set[int] = set()
    for k in sorted(need_caps):
        c = by_slot.get(k)
        if c is None or c["start"] >= bound or Path(c["dir"]).name in bad_dirs:
            continue
        ok, got, mm, ns = check(rel_list("snapshots", Path(c["dir"]), b.capture_files(c["dir"])))
        mism += mm
        if ok:
            for rel, sha in got.items():
                files[rel] = {"sha256": sha, "root": str(Path(c["dir"]).parent)}
            slots[c["id"]] = iso(b.slot_time(k, spec))
            sel_caps.add(k)
        else:
            not_sel += ns
    for k in sorted(s7["sweeps"]):
        if k in sweep_ok and k in sel_caps and sweep_ok[k][0].name not in bad_dirs:
            sd, got = sweep_ok[k]
            for rel, sha in got.items():
                files[rel] = {"sha256": sha, "root": str(sd.parent), "capture": by_slot[k]["id"]}
            slots[sd.name] = iso(b.slot_time(k, spec))
    for sid in used_samples:
        files.update(sample_files[sid])
    if mism:
        return {"error": "hash mismatch against a source seal: LT7 seal refused", "mismatches": mism[:50], "n_mismatches": len(mism)}
    sel_sweeps = {k for k in s7["sweeps"] if k in sweep_ok and sweep_ok[k][0].name in slots and sweep_ok[k][0].name not in bad_dirs}
    miss = {
        "CC7_full": [iso(b.slot_time(k, spec)) for k in sorted(c7["full"]) if k not in sel_caps],
        "CC7_lag": [iso(b.slot_time(k, spec)) for k in sorted(c7["lag"]) if k not in sel_caps],
        "CS7_captures": [iso(b.slot_time(k, spec)) for k in sorted(s7["caps"]) if k not in sel_caps],
        "CS7_sweeps": [iso(b.slot_time(k, spec)) for k in sorted(s7["sweeps"]) if k not in sel_sweeps],
        "CV7_samples": [s for s in samples if s[:8] in days and s not in used_samples]}
    return {"purpose": "LT7 census inputs (LIVE_TESTS_7.md section 7): exactly the files the censuses open, each named in a source seal with an equal sha256; counts-only use",
            "written_utc": iso(b.now_ts()), "spec_sha256": sha256_file(SPEC_PATH), "design_text_sha256": design_text_sha(), "spec_blocks_sha256": spec_blocks_sha(spec),
            "source_seals": shas, "span": spec["census_inputs"]["cc7_span"],
            "refuse_at_or_after_utc": spec["census_inputs"]["refuse_at_or_after_utc"], "slots": slots, "samples": used_samples,
            "sample_slots": {sid: iso(b.slot_time(k, spec)) for sid, k in sample_slot.items()},
            "needs": {"CC7_full": len(c7["full"]), "CC7_lag": len(c7["lag"]), "CS7_captures": len(s7["caps"]), "CS7_sweeps": len(s7["sweeps"]), "CS7_pairs": len(s7["pairs"]),
                      "CV7_captures": len(cv_caps)},
            "unavailable_used": sorted(set(unavail_used)), "missing": miss, "n_missing": {k_: len(v_) for k_, v_ in miss.items()},
            "not_selected": not_sel[:100], "n_not_selected": len(not_sel), "n_files": len(files), "files": dict(sorted(files.items()))}


def sealed_sweep_slots(seal: dict, spec: dict) -> set[int]:
    """Slots whose sweep 1 the seal names (the seal's own slot assignment)."""
    out = set()
    for d in b.sealed_dirs(seal, "book_sweeps"):
        if d in seal.get("slots", {}):
            k = b.slot_of(epoch(seal["slots"][d]), spec)
        else:
            t = b._name_time(d)
            k = b.slot_of(t, spec) if np.isfinite(t) else None
        if k is not None:
            out.add(k)
    return out


def _fee_counts(ser: pd.DataFrame, acc: dict) -> None:
    vc = ser["fee_cat"].where(ser["fee_cat"].notna(), None).value_counts(dropna=False)
    for kk, vv in vc.items():
        key = "" if kk is None or (isinstance(kk, float) and np.isnan(kk)) else str(kk)
        acc[key] = acc.get(key, 0) + int(vv)


def _load_for_census(seal: Path, snapshot_root, sweep_root, work: Path, spec: dict):
    seal_d = json.loads(Path(seal).read_text())
    if (derr := design_text_error()) or not seal_design_accepted(seal_d.get("design_text_sha256")):
        return seal_d, None, None, derr or {"error": "the seal was written against a different LIVE_TESTS_7.md: census refused", "seal_design_text_sha256": seal_d.get("design_text_sha256")}
    viol = bound_violations(seal_d, spec)
    if viol:
        return seal_d, None, None, {"error": "sealed bound violated: census refused", "bad": viol, "n_bad": len(viol)}
    if seal_d.get("spec_blocks_sha256") != spec_blocks_sha(spec):
        return seal_d, None, None, {"error": "the spec's census_gates / census_inputs differ from those at seal time (census-code check must-fix 2): census refused",
                                    "seal_blocks_sha256": seal_d.get("spec_blocks_sha256"), "spec_blocks_sha256": spec_blocks_sha(spec)}
    w = Path(work)
    if w.exists() and any(w.iterdir()):
        return seal_d, None, None, {"error": f"work directory {w} is not empty: a stale series file would be reused (census refused)"}
    by_slot, sweeps = _seal_scan(seal_d, snapshot_root, sweep_root, Path(work), spec)
    return seal_d, by_slot, sweeps, None


def census_captures(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CC7: CH191 (grind), CH193 (absorbed flow; CC7's half) and CH192 (implied against realised) on the sealed captures. Before anything is
    parsed: the bound check, then every sealed capture in a needed slot must be present with every sealed file and every opened file
    must be sealed with an equal sha256, else the census is refused (L3). Slots with no sealed capture are counted as missing. Slots after
    an origin are read ONLY through :func:`lag_capture` (``volume24hr`` for CH193 at k + 2 / k + 3, ``spread`` for CH192 at k + 3)."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    seal_d, by_slot, _, err = _load_for_census(seal, snapshot_root, [], work, spec)
    if err:
        return err
    sl = cc7_slots(spec)
    comp = b.seal_completeness(seal_d, by_slot, {}, sl["caps"], set(), spec) if verify else {"bad": [], "missing_slots": [], "n_missing_slots": 0, "files_checked": 0}
    if verify and comp["bad"]:
        return {"error": "input identity check failed (L3): census refused", "bad": comp["bad"][:50], "n_bad": len(comp["bad"])}
    store = MidStore()
    frames: dict[int, pd.DataFrame] = {}
    fee_counts: dict = {}
    O7, O192 = set(sl["O7"]), set(sl["O192"])
    U191, U193, U192 = [], [], []
    t191: dict = {}
    t193: dict = {}
    t192: dict = {}
    cov191 = cov193 = cov192 = 0
    per_capture = []
    for k in sorted(sl["full"]):
        if k not in by_slot:
            continue
        cap = by_slot[k]
        write_series7(work, cap, spec)
        ser = b.read_series(work, cap["id"])
        store.add(k, ser)
        _fee_counts(ser, fee_counts)
        frames[k] = ser
        for old in [s_ for s_ in frames if s_ < k - 1]:
            frames.pop(old)
        rec = {"capture": cap["id"]}
        if k - 1 in frames and k in O7:
            ser_p = frames[k - 1]
            if all((k - i) in by_slot for i in range(4)):
                u, cnt = path_units7(ser, ser_p, store, cap, k, spec)
                cov191 += 1
                _merge_counts(t191, cnt)
                if len(u):
                    U191.append(u)
                rec["CH191"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
            else:
                t191["origin_step_slot_missing"] = t191.get("origin_step_slot_missing", 0) + 1
            v2 = lag_capture(by_slot[k + 2]["dir"], "volume24hr") if (k + 2) in by_slot else None
            v3 = lag_capture(by_slot[k + 3]["dir"], "volume24hr") if (k + 3) in by_slot else None
            u, cnt = absorbed_units(ser, ser_p, store, cap, k, spec, v2, v3)
            cov193 += 1
            _merge_counts(t193, cnt)
            if len(u):
                U193.append(u)
            rec["CH193"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
        if k - 1 in frames and k in O192:
            sp3 = lag_capture(by_slot[k + 3]["dir"], "spread") if (k + 3) in by_slot else None
            u, cnt = ivr_units(ser, frames[k - 1], store, cap, k, spec, sp3)
            cov192 += 1
            _merge_counts(t192, cnt)
            if len(u):
                U192.append(u)
            rec["CH192"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
        per_capture.append(rec)
    fs = crypto_failsafe(fee_counts)
    if not fs["classifier_shown_to_work"]:
        return {"error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    d191, d193, d192 = cov191 / 12.0, cov193 / 12.0, cov192 / 4.0
    sc = lambda d: 21.0 / d if d else float("nan")  # noqa: E731
    cat = lambda L: pd.concat(L, ignore_index=True) if L else pd.DataFrame()  # noqa: E731
    return {"span": spec["census_inputs"]["cc7_span"], "n_captures": len(by_slot), "inputs_verified": bool(verify), "missing_slots": comp.get("missing_slots"),
            "n_missing_slots": comp.get("n_missing_slots"), "files_checked": comp.get("files_checked"), "fee_category_values": fs["distinct_values"],
            "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"], "covered_origins": {"CH191": cov191, "CH193": cov193, "CH192": cov192},
            "per_capture": per_capture, "unit_overlaps": unit_overlaps({"CH191": cat(U191), "CH193": cat(U193), "CH192": cat(U192)}),
            "CH191": census_ch191(cat(U191), t191, spec, sc(d191), d191), "CH193": census_ch193(cat(U193), t193, spec, sc(d193), d193),
            "CH192": census_ch192(cat(U192), t192, spec, sc(d192), d192)}


def census_sweeps(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, sweep_root=SWEEP_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CS7: CH195 (resistance) and CH197 (patient money) on the sealed sweeps and their captures. CH197's F-feasibility pairs (pass j, pass
    j + 13) read pass j + 13 ONLY through :func:`lag_sweep` (the four size columns)."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    seal_d, by_slot, sweeps, err = _load_for_census(seal, snapshot_root, sweep_root, work, spec)
    if err:
        return err
    avail = {k for k, c in by_slot.items() if c["id"] in sweeps} & sealed_sweep_slots(seal_d, spec)
    sl = cs7_slots(spec, avail)
    comp = b.seal_completeness(seal_d, by_slot, sweeps, sl["caps"], sl["sweeps"], spec, sweep_root) if verify else {"bad": [], "missing_slots": [], "n_missing_slots": 0, "files_checked": 0}
    if verify and comp["bad"]:
        return {"error": "input identity check failed (L3): census refused", "bad": comp["bad"][:50], "n_bad": len(comp["bad"])}
    store = MidStore()
    frames: dict[int, pd.DataFrame] = {}
    fee_counts: dict = {}
    K, P = set(sl["K"]), set(sl["pairs"])
    U195, U197, PR = [], [], []
    t195: dict = {}
    t197: dict = {}
    cov195 = cov197 = 0
    per_pass = []
    sweep_cache: dict[int, pd.DataFrame] = {}

    def sw_of(j: int) -> pd.DataFrame | None:
        if j not in by_slot or by_slot[j]["id"] not in sweeps:
            return None
        if j not in sweep_cache:
            sweep_cache[j] = b.sweep_frame(sweeps[by_slot[j]["id"]]["dir"], by_slot[j]["dir"]).set_index("market_id")
        return sweep_cache[j]

    for k in sorted(sl["full"]):
        if k not in by_slot:
            continue
        cap = by_slot[k]
        write_series7(work, cap, spec)
        ser = b.read_series(work, cap["id"])
        store.add(k, ser)
        _fee_counts(ser, fee_counts)
        frames[k] = ser
        for old in [s_ for s_ in frames if s_ < k - 1]:
            frames.pop(old)
        for old in [s_ for s_ in sweep_cache if s_ < k - 1]:
            sweep_cache.pop(old)
        rec = {"capture": cap["id"]}
        if k - 1 in frames and (k in K or k in P):
            ser_p = frames[k - 1]
            sw_k, sw_p = sw_of(k), sw_of(k - 1)
            if k in K:
                u, cnt = resist_units(ser, ser_p, store, sw_k, sw_p, cap, k, spec)
                if sw_k is not None and sw_p is not None:
                    cov195 += 1
                _merge_counts(t195, cnt)
                if len(u):
                    U195.append(u)
                rec["CH195"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
                if slot_in_day(k) == spec["tests"]["CH197"]["slot_index_in_day"]:
                    u, cnt = patient_units(ser, ser_p, store, sw_k, cap, k, spec)
                    if sw_k is not None:
                        cov197 += 1
                    _merge_counts(t197, cnt)
                    if len(u):
                        U197.append(u)
                    rec["CH197"] = {a_: v for a_, v in cnt.items() if isinstance(v, (int, float))}
            if k in P and sw_k is not None and (k + 13) in by_slot and (k + 13) in avail:
                u, cnt = patient_units(ser, ser_p, store, sw_k, cap, k, spec, any_slot=True)
                if len(u):
                    lagsw = lag_sweep(sweeps[by_slot[k + 13]["id"]]["dir"], by_slot[k + 13]["dir"])
                    lt_ = lagsw.reindex(u["market_id"].astype(str))
                    imb13 = behind_touch(lt_["bid_size_1"], lt_["ask_size_1"], lt_["depth_bid_5c"], lt_["depth_ask_5c"])["imbB"]
                    pr = pd.DataFrame({"market_id": u["market_id"].to_numpy(), "t_row": u["t_row"].to_numpy(float), "imb_j": u["imbB"].to_numpy(float), "imb_j13": imb13})
                    PR.append(pr[np.isfinite(pr["imb_j13"])])
                rec["pair_units"] = len(u)
        per_pass.append(rec)
    fs = crypto_failsafe(fee_counts)
    if not fs["classifier_shown_to_work"]:
        return {"error": "crypto classifier not shown to work on the sealed sidecar set: every gate NaN", "fee_category_values": fs["distinct_values"]}
    d195, d197 = cov195 / 12.0, float(cov197)
    sc = lambda d: 21.0 / d if d else float("nan")  # noqa: E731
    cat = lambda L: pd.concat(L, ignore_index=True) if L else pd.DataFrame()  # noqa: E731
    pairs = cat(PR)
    return {"inputs_verified": bool(verify), "missing_slots": comp.get("missing_slots"), "n_missing_slots": comp.get("n_missing_slots"), "files_checked": comp.get("files_checked"),
            "fee_category_values": fs["distinct_values"], "crypto_classifier_shown_to_work": fs["classifier_shown_to_work"], "covered_passes": {"CH195": cov195, "CH197": cov197},
            "n_pair_passes": len(sl["pairs"]), "per_pass": per_pass, "unit_overlaps": unit_overlaps({"CH195": cat(U195), "CH197": cat(U197)}),
            "CH195": census_ch195(cat(U195), t195, spec, sc(d195), d195), "CH197": census_ch197(cat(U197), t197, spec, sc(d197), d197, pairs)}


# --- CV7: the volume24hr semantic gate -------------------------------------------------------------------------------------------


def load_sample7(sdir: Path, markets=None, before: float | None = None, chunksize: int = 200_000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """features (status ok) and the print rows CV7 reads: ``market_id``, ``ts``, ``price``, ``size`` only (``side`` and every wallet field
    are NEVER read). With ``markets`` and ``before`` (the latest decision time) only rows of those markets with ``ts < before`` are held."""
    feat = pd.read_csv(Path(sdir) / "features.csv.gz", dtype={"market_id": str, "condition_id": str})
    feat = feat[feat["status"] == "ok"].drop_duplicates("market_id").reset_index(drop=True)
    keep = None if markets is None else {str(m) for m in markets}
    parts = []
    for ch in pd.read_csv(Path(sdir) / "trades.csv.gz", usecols=["market_id", "ts", "price", "size"], dtype=str, chunksize=chunksize):
        if keep is not None:
            ch = ch[ch["market_id"].isin(keep)]
        if before is not None and len(ch):
            ch = ch[pd.to_numeric(ch["ts"], errors="coerce") < before]
        if len(ch):
            parts.append(ch)
    tr = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame({c: pd.Series(dtype=str) for c in ("market_id", "ts", "price", "size")})
    return feat, tr


def semantic_rows(ser_k: pd.DataFrame, ser_p: pd.DataFrame, feat: pd.DataFrame, tr: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """One row per sampled non-sports market two-sided at k - 1 and k (the interval (t_{k-1}, t_k] of the market's own row receipts): the
    sampled prints in the interval (``t_p < ts < t_k``, nothing at or after ``t_k`` is held), their notional (price x size), whether the
    page covers the interval (a page below the 500-row limit, or its oldest held row at or before ``t_p``), ``dV`` and the tolerance
    flag, whether every print falls in the last 30 minutes, and the 24 h-earlier interval's print count where the page covers it."""
    g = spec["census_gates"]["CV7_CH193"]
    j = ser_k[["vol24", "t_row", "sports"]].join(ser_p[["vol24", "t_row"]].rename(columns=lambda c: c + "_p"), how="inner")
    j = j[j["sports"] == 0]
    f = feat.drop_duplicates("market_id").set_index(feat.drop_duplicates("market_id")["market_id"].astype(str))
    j = j[j.index.astype(str).isin(f.index)].copy()
    mk = j.index.astype(str)
    j["n_returned"] = pd.to_numeric(f["n_returned"], errors="coerce").reindex(mk).to_numpy(float)
    tr = tr[tr["market_id"].astype(str).isin(set(mk))].copy()
    tr["ts"] = pd.to_numeric(tr["ts"], errors="coerce")
    tr["notional"] = pd.to_numeric(tr["price"], errors="coerce") * pd.to_numeric(tr["size"], errors="coerce")
    tr = tr[np.isfinite(tr["ts"]) & np.isfinite(tr["notional"])]
    tk = j["t_row"].astype(float)
    tp = j["t_row_p"].astype(float)
    tr["t_k"] = tr["market_id"].astype(str).map(pd.Series(tk.to_numpy(), index=mk)).astype(float)
    tr["t_p"] = tr["market_id"].astype(str).map(pd.Series(tp.to_numpy(), index=mk)).astype(float)
    tr = tr[tr["ts"] < tr["t_k"]]
    inw = tr[tr["ts"] > tr["t_p"]]  # (t_{k-1}, t_k]: open at t_{k-1}; nothing at or after t_k is ever held
    prev = tr[(tr["ts"] > tr["t_p"] - 86400.0) & (tr["ts"] <= tr["t_k"] - 86400.0)]
    ag = inw.groupby(inw["market_id"].astype(str)).agg(n_int=("ts", "size"), notional=("notional", "sum"), ts_min=("ts", "min"))
    oldest = tr.groupby(tr["market_id"].astype(str))["ts"].min()
    n_prev = prev.groupby(prev["market_id"].astype(str))["ts"].size()
    out = pd.DataFrame(index=mk)
    out["n_int"] = ag["n_int"].reindex(mk).fillna(0).to_numpy(float)
    out["notional"] = ag["notional"].reindex(mk).fillna(0.0).to_numpy(float)
    out["ts_min"] = ag["ts_min"].reindex(mk).to_numpy(float)
    out["oldest"] = oldest.reindex(mk).to_numpy(float)
    out["n_prev24"] = n_prev.reindex(mk).fillna(0).to_numpy(float)
    full = j["n_returned"].to_numpy(float) >= trade_sample.TRADE_LIMIT
    with np.errstate(invalid="ignore"):
        cov = ~full | (out["oldest"].to_numpy(float) <= tp.to_numpy(float))
        cov24 = ~full | (out["oldest"].to_numpy(float) <= tp.to_numpy(float) - 86400.0)
    out["covered"], out["covered24"] = cov, cov24
    vol, vol_p = j["vol24"].to_numpy(float), j["vol24_p"].to_numpy(float)
    dv = vol - vol_p
    out["vol_present"] = np.isfinite(vol) & np.isfinite(vol_p)
    out["dV"] = dv
    with np.errstate(invalid="ignore"):
        out["above"] = dv > dv_tolerance(vol_p, abs_tol=g["dv_abs"], rel_tol=g["dv_rel"])
        out["recent"] = out["ts_min"].to_numpy(float) > tk.to_numpy(float) - g["latency_window_s"]
    return out


def semantic_gate(R: pd.DataFrame, spec: dict) -> dict:
    """CV7's CH193 semantic gate over the pooled per-market rows (design 7): among sampled non-sports traded intervals with complete page
    coverage and sample notional > $10, the share with ``dV`` above tolerance >= 70%; among sampled markets with complete coverage and no
    print in the interval, that share <= 30%; the Spearman rank correlation of ``dV`` with the sampled notional on the traded intervals
    >= 0.5; the latency check (traded intervals whose prints all fall in the last 30 minutes: share >= 70%, NaN with fewer than 30).
    Printed, not gated: the roll-off-free share (traded intervals whose 24 h-earlier interval had no sampled print where the page
    allows it)."""
    g = spec["census_gates"]["CV7_CH193"]
    ok = R["vol_present"].to_numpy(bool) & R["covered"].to_numpy(bool)
    traded = ok & (R["n_int"].to_numpy(float) >= 1) & (R["notional"].to_numpy(float) > g["min_sample_notional"])
    untraded = ok & (R["n_int"].to_numpy(float) == 0)
    above = R["above"].to_numpy(bool)
    lat = traded & R["recent"].to_numpy(bool)
    rof = traded & R["covered24"].to_numpy(bool) & (R["n_prev24"].to_numpy(float) == 0)

    def share(m: np.ndarray) -> float:
        return float(above[m].mean()) if m.sum() else float("nan")

    if traded.sum() >= 3:
        sp = float(pd.Series(R["dV"].to_numpy(float)[traded]).rank().corr(pd.Series(R["notional"].to_numpy(float)[traded]).rank()))
    else:
        sp = float("nan")
    n_lat = int(lat.sum())
    lat_share = share(lat) if n_lat >= g["latency_min_intervals"] else float("nan")
    s_tr, s_un = share(traded), share(untraded)
    rolloff = R["dV"].to_numpy(float)[traded] < 0
    res = {"traded_intervals": int(traded.sum()), "untraded_intervals": int(untraded.sum()), "traded_share_above": s_tr, "untraded_share_above": s_un, "spearman_dV_notional": sp,
           "latency_intervals": n_lat, "latency_share_above": lat_share, "rolloff_free_share_above_printed": share(rof), "rolloff_free_intervals": int(rof.sum()),
           "traded_negative_dV_share": float(rolloff.mean()) if len(rolloff) else float("nan")}
    res["gate_CH193_semantic"] = _gate({
        "traded_share": bool(np.isfinite(s_tr) and s_tr >= g["traded_share_min"]), "untraded_share": bool(np.isfinite(s_un) and s_un <= g["untraded_share_max"]),
        "spearman": bool(np.isfinite(sp) and sp >= g["spearman_min"]), "latency": bool(np.isfinite(lat_share) and lat_share >= g["latency_share_min"])})
    return res


def census_volsem(*, seal: Path, sample_roots: list[Path], snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """CV7 (CH193's semantic gate) on the sealed active-frame samples of ``cv7_sample_days_utc`` with their captures k - 1 and k; refused on
    any mismatch or on the bound. Trade rows with ``ts < t_k`` only; ``side`` is never read."""
    spec = spec or load_spec(sha=None)
    work = Path(work)
    seal_d, by_slot, _, err = _load_for_census(seal, snapshot_root, [], work, spec)
    if err:
        return err
    slot_by_id = {c["id"]: k for k, c in by_slot.items()}
    bad, found = [], {}
    for sid in seal_d.get("samples", []):
        sdir = next((Path(r) / sid for r in sample_roots if (Path(r) / sid / "trades.csv.gz").exists()), None)
        if sdir is None:
            bad.append({"sample": sid, "error": "not found"})
            continue
        if verify:
            bad += [{"sample": sid, **x} for x in b.verify_files(seal_d, [(rel, sdir / rel.rsplit("/", 1)[1]) for rel in _sample_rels(sid)])]
        k = slot_by_id.get(b._manifest(sdir / "manifest.json").get("snapshot_id"))
        if k is None:
            bad.append({"sample": sid, "error": "capture not found among the sealed captures"})
            continue
        found[sid] = (sdir, k)
    cap_slots = {j for _, k in found.values() for j in (k - 1, k)}
    comp = b.seal_completeness(seal_d, by_slot, {}, cap_slots, set(), spec) if verify and cap_slots else {"bad": [], "missing_slots": [], "n_missing_slots": 0, "files_checked": 0}
    bad += comp.get("bad", [])
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    parts, per, used = [], [], 0
    for sid, (sdir, k) in found.items():
        if k - 1 not in by_slot:
            per.append({"sample": sid, "skipped": "no previous slot"})
            continue
        for j in (k - 1, k):
            write_series7(work, by_slot[j], spec)
        ser_k, ser_p = b.read_series(work, by_slot[k]["id"]), b.read_series(work, by_slot[k - 1]["id"])
        both = ser_k.index.intersection(ser_p.index)
        t_max = float(ser_k["t_row"].max()) + 1.0
        feat, tr = load_sample7(sdir, markets=both, before=t_max)
        R = semantic_rows(ser_k, ser_p, feat, tr, spec)
        R["sample"] = sid
        parts.append(R)
        used += 1
        per.append({"sample": sid, "markets": len(R), "traded_prints_markets": int((R["n_int"] > 0).sum())})
    covered_days = used / 12.0
    mind = spec["census_inputs"]["min_covered_days"]["CV7"]
    R = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    res = {"seal": str(seal), "inputs_verified": bool(verify), "samples": used, "missing_capture_slots": comp.get("missing_slots"), "per_sample": per}
    if R.empty:
        res.update({"error": "no units", "gate_CH193_semantic": {"pass": False}})
    else:
        res.update(semantic_gate(R, spec))
    return _gate_min_days(res, "gate_CH193_semantic", covered_days, mind)


RN_COMMON_THRESHOLD = 0.05  # orchestrator pre-declaration (before any count): "common" = share above 5% on either census day


def rewards_null_share(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """Counts-only null-share check of the sealed sidecars (census-code check must-fix 3): reads ONLY the sidecar columns (``EXT_COLS``) of
    every sealed ``rows_ext.csv.gz`` (no price, no outcome, no target; the category columns are there to apply the non-sports ex-crypto rule) and prints, per field,
    the share that is null, the share of ``clob_rewards`` that is the empty list ``[]`` (parsed 0.0 by the named parser: not rewarded) and the
    share that parses to a zero rate. A CSV-empty cell reads as null, so a null ``clob_rewards`` is what the censuses EXCLUDE (a unit with no
    reward status): if nulls are common, CH197 and CH192 silently shrink to a rewarded subset and the question goes to the challenger BEFORE
    CC7 / CS7 run (each census runs once). Every opened file is checked against the seal first."""
    spec = spec or load_spec(sha=None)
    seal_d, by_slot, _, err = _load_for_census(seal, snapshot_root, [], Path(work), spec)
    if err:
        return err
    files = seal_d.get("files", {})
    bad, todo = [], []
    for k, c in sorted(by_slot.items()):
        rel = f"data-dumps/research_lab/snapshots/{c['id']}/rows_ext.csv.gz"
        if rel in files:
            pth = Path(c["dir"]) / "rows_ext.csv.gz"
            if verify:
                bad += b.verify_files(seal_d, [(rel, pth)])
            todo.append((k, c, pth))
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    tot = {"rows": 0, "clob_null": 0, "clob_empty_list": 0, "clob_nonempty": 0, "clob_nonempty_zero_rate": 0, "max_spread_null": 0, "max_spread_zero": 0, "min_size_null": 0}
    per_day: dict[str, dict] = {}
    for _k, c, pth in todo:
        e = pd.read_csv(pth, usecols=lambda col: col in set(EXT_COLS), dtype=str)  # sidecar columns only (EXT_COLS holds no price)
        for col in EXT_COLS:
            if col not in e:
                e[col] = None
        e = e.drop_duplicates("market_id")
        # the pre-declared "common" rule counts the sealed market-captures that are non-sports AND ex-crypto (the primaries' category rule)
        cat = b.category_cols(e.set_index("market_id"), e["market_id"].astype(str), e["market_id"].astype(str), spec)
        keep = np.array([s_ == 0 and crypto_class(f_, True, int(s_)) == "non_crypto" for s_, f_ in zip(cat["sports"], e["fee_category"].where(e["fee_category"].notna(), None), strict=True)], bool)
        e = e[keep].reset_index(drop=True)
        cr = e["clob_rewards"]
        isnull = cr.isna()
        empty = cr.fillna("").str.strip().eq("[]")
        nonempty = ~isnull & ~empty
        zero = np.array([nonempty.iloc[i] and maker_rewards.parse_daily_rate(v, None) == 0.0 for i, v in enumerate(cr)], bool) if nonempty.any() else np.zeros(len(e), bool)
        ms = pd.to_numeric(e["rewards_max_spread"], errors="coerce")
        d = _utc_day(c["start"])
        rec = {"rows": len(e), "clob_null": int(isnull.sum()), "clob_empty_list": int(empty.sum()), "clob_nonempty": int(nonempty.sum()), "clob_nonempty_zero_rate": int(zero.sum()),
               "max_spread_null": int(ms.isna().sum()), "max_spread_zero": int((ms == 0).sum()), "min_size_null": int(pd.to_numeric(e["rewards_min_size"], errors="coerce").isna().sum())}
        for tgt in (tot, per_day.setdefault(d, dict.fromkeys(tot, 0))):
            for key_, v in rec.items():
                tgt[key_] += v
    n = tot["rows"]
    sh = lambda x: (x / n if n else float("nan"))  # noqa: E731
    thr = RN_COMMON_THRESHOLD
    day_common = {}
    for d, v in per_day.items():
        r_ = v["rows"]
        day_common[d] = bool(r_ > 0 and ((v["clob_null"] + v["clob_empty_list"]) / r_ > thr or v["max_spread_null"] / r_ > thr))
    common = bool(any(day_common.values()))
    return {"common": common, "common_rule": f"the empty-or-null share of clob_rewards OR the null share of rewards_max_spread exceeds {thr} of sealed non-sports ex-crypto market-captures on either census day",
            "common_by_day": day_common, "sidecars": len(todo), "captures_without_sealed_sidecar": len(by_slot) - len(todo), "inputs_verified": bool(verify), "totals": tot,
            "shares": {"clob_rewards_null": sh(tot["clob_null"]), "clob_rewards_empty_list": sh(tot["clob_empty_list"]), "clob_rewards_nonempty": sh(tot["clob_nonempty"]),
                       "clob_rewards_nonempty_zero_rate": sh(tot["clob_nonempty_zero_rate"]), "rewards_max_spread_null": sh(tot["max_spread_null"]),
                       "rewards_max_spread_zero": sh(tot["max_spread_zero"]), "rewards_min_size_null": sh(tot["min_size_null"])},
            "per_day": {d: {**v, "clob_empty_or_null_share": (v["clob_null"] + v["clob_empty_list"]) / v["rows"] if v["rows"] else float("nan"), "clob_null_share": v["clob_null"] / v["rows"] if v["rows"] else float("nan"), "clob_empty_list_share": v["clob_empty_list"] / v["rows"] if v["rows"] else float("nan")}
                        for d, v in sorted(per_day.items())},
            "note": "null clob_rewards = no reward status = EXCLUDED by CH197 / CH192 (1.5); '[]' parses to 0.0 = not rewarded. If nulls are common, ask the challenger before CC7 / CS7."}


def rewards_probe(*, seal: Path, snapshot_root=SNAPSHOT_ROOT, work: Path, spec: dict | None = None, verify: bool = True) -> dict:
    """Counts-only probe of the sealed sidecars before CC7 / CS7 (ruling 13.6, "Before CC7"). Reads ONLY the sidecar columns (``EXT_COLS``: no price, no
    outcome, no target; the category columns apply the non-sports ex-crypto rule) of every sealed ``rows_ext.csv.gz`` (each opened file is checked against
    the seal first). Per census day and in total, among non-sports ex-crypto market-captures: the share of LISTED programmes whose summed rate is zero on the
    capture's UTC day; the null share of ``order_min_size``; the share of markets whose ``clob_rewards`` switches between null and non-null across the
    captures of one UTC day (among markets seen at least twice that day); and the count of malformed ``clob_rewards``."""
    spec = spec or load_spec(sha=None)
    seal_d, by_slot, _, err = _load_for_census(seal, snapshot_root, [], Path(work), spec)
    if err:
        return err
    files = seal_d.get("files", {})
    bad, todo = [], []
    for k, c in sorted(by_slot.items()):
        rel = f"data-dumps/research_lab/snapshots/{c['id']}/rows_ext.csv.gz"
        if rel in files:
            pth = Path(c["dir"]) / "rows_ext.csv.gz"
            if verify:
                bad += b.verify_files(seal_d, [(rel, pth)])
            todo.append((k, c, pth))
    if bad:
        return {"error": "input identity check failed (L3): census refused", "bad": bad[:50], "n_bad": len(bad)}
    zero = {"rows": 0, "listed": 0, "listed_zero_rate_on_day": 0, "null": 0, "malformed": 0, "osz_null": 0}
    per_day: dict[str, dict] = {}
    seen: dict[str, dict[str, list[int]]] = {}  # day -> market_id -> [captures, null captures, listed captures]
    for _k, c, pth in todo:
        e = pd.read_csv(pth, usecols=lambda col: col in set(EXT_COLS), dtype=str)  # sidecar columns only (EXT_COLS holds no price)
        for col in EXT_COLS:
            if col not in e:
                e[col] = None
        e = e.drop_duplicates("market_id")
        cat = b.category_cols(e.set_index("market_id"), e["market_id"].astype(str), e["market_id"].astype(str), spec)
        keep = np.array([s_ == 0 and crypto_class(f_, True, int(s_)) == "non_crypto" for s_, f_ in zip(cat["sports"], e["fee_category"].where(e["fee_category"].notna(), None), strict=True)], bool)
        e = e[keep].reset_index(drop=True)
        d = _utc_day(c["start"])
        st_rate = [reward_status(v, True, d) for v in e["clob_rewards"]]
        st = np.array([s_ for s_, _ in st_rate], dtype=object)
        rate = np.array([r_ for _, r_ in st_rate], float)
        rec = {"rows": len(e), "listed": int((st == "listed").sum()), "listed_zero_rate_on_day": int(((st == "listed") & (rate == 0.0)).sum()), "null": int((st == "null").sum()),
               "malformed": int((st == "malformed").sum()), "osz_null": int(pd.to_numeric(e["order_min_size"], errors="coerce").isna().sum())}
        day_seen = seen.setdefault(d, {})
        for m_, s_ in zip(e["market_id"].astype(str).to_numpy(), st, strict=True):
            if s_ in ("null", "listed"):
                row = day_seen.setdefault(m_, [0, 0, 0])
                row[0] += 1
                row[1 if s_ == "null" else 2] += 1
        for tgt in (zero, per_day.setdefault(d, dict.fromkeys(zero, 0))):
            for key_, v in rec.items():
                tgt[key_] += v
    sh = lambda x, n: (x / n if n else float("nan"))  # noqa: E731
    sw_tot = {"markets_seen_2plus": 0, "markets_switching": 0}
    for d, ms in seen.items():
        two = [r_ for r_ in ms.values() if r_[0] >= 2]
        sw = sum(1 for r_ in two if r_[1] > 0 and r_[2] > 0)
        per_day[d]["markets_seen_2plus"], per_day[d]["markets_switching"] = len(two), sw
        sw_tot["markets_seen_2plus"] += len(two)
        sw_tot["markets_switching"] += sw
    for v in per_day.values():
        v["listed_zero_rate_share"] = sh(v["listed_zero_rate_on_day"], v["listed"])
        v["order_min_size_null_share"] = sh(v["osz_null"], v["rows"])
        v["null_nonnull_switch_share"] = sh(v["markets_switching"], v["markets_seen_2plus"])
    return {"sidecars": len(todo), "captures_without_sealed_sidecar": len(by_slot) - len(todo), "inputs_verified": bool(verify),
            "reward_null_rule": spec.get("reward_null_rule"), "totals": {**zero, **sw_tot},
            "shares": {"listed_zero_rate_on_day": sh(zero["listed_zero_rate_on_day"], zero["listed"]), "order_min_size_null": sh(zero["osz_null"], zero["rows"]),
                       "null_nonnull_switch_within_day": sh(sw_tot["markets_switching"], sw_tot["markets_seen_2plus"]), "clob_rewards_null": sh(zero["null"], zero["rows"])},
            "malformed_clob_rewards": zero["malformed"], "per_day": dict(sorted(per_day.items())),
            "note": "counts only; non-sports ex-crypto market-captures; no price, outcome or target read. A market is a switcher if, among its captures of one UTC day, clob_rewards is null in at least one and listed in at least one."}


def cleanup_census(work: Path) -> None:
    b.cleanup_census(work)
