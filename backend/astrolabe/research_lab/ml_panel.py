"""Multi-signal pipeline, Task 2: multi-period panel, tier-(a) features and the fold manifest.

Design: ``docs/research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md`` (sections 1, 2, 4, 7). No model is
fitted here and nothing is scored.

Rules enforced in this module:

* Pairs reuse ``panel.build_pair`` (eligibility, target validity). ``mid_i`` and ``mid_j`` are both
  the **Gamma** snapshot mid ``(bestBid + bestAsk) / 2``. A book sweep can only ever contribute
  features, never the target; a sweep also moves the origin cutoff ``t0 = max(row receipt, sweep
  receipt)``, and a target received before ``t0`` is target-unavailable.
* Every feature reads origin-side columns only, through the ``features`` registry (which refuses
  label columns). History enters only as ``hist_*_k`` columns for ``k`` in 1..6 (snapshots
  ``i-k``), built before the pair is formed; there is no way to ask for ``i+k``.
* Cumulative fields (``volume_num`` and the like) are used as the origin value or as the
  ``i-1 -> i`` difference, never taken from ``j``.
* Sidecar fields (``rows_ext.csv.gz``) are optional. Snapshots without a sidecar give NaN, never
  0, and NaN stays NaN in every derived feature.
* The target is three-class, ``|dmid| <= delta`` is flat (``delta`` 0.005 primary, 0.01
  sensitivity), and sweep-derived values are never part of it.
* The fold plan is an expanding window of 4-period test blocks (first test block after at least
  12 periods) with a 1-period embargo, and a row-level label-availability purge that calls
  ``evaluate.purged_train_mask``. The manifest is canonical JSON and carries its own sha256.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from astrolabe.research_panel import pairing

from . import evaluate, features, features_dev, panel
from .features import FeatureSpec

DELTA_PRIMARY = 0.005
DELTA_SENSITIVITY = 0.01
_DELTA_EPS = 1e-9  # tolerance so |dmid| == delta on the float grid counts as flat

CLASS_DOWN, CLASS_FLAT, CLASS_UP = 0, 1, 2

GAP_MIN_H, GAP_MAX_H = 1.5, 3.0  # source -> target snapshot start gap
HISTORY_MAX_GAP_H = 3.0  # a3/a4 chain breaks across a larger gap between snapshots
HISTORY_DEPTH = 6  # snapshots i-1 .. i-6

BLOCK_PERIODS = 4
MIN_TRAIN_PERIODS = 12
EMBARGO_PERIODS = 1
EMBARGO_S = 7200.0  # one nominal period (2h cadence)
SWEEP_MIN_COVERAGE = 0.99

FEATURE_SET_VERSION = "ml-tier-a-v1"
EXT_FEATURE_SET_VERSION = "ml-tier-a-ext-v1"  # sweep (a11) + sibling (a10) features
SWEEP_SERIES_INDEX = 0  # sweeps come in pairs (A, B): A (series_index 0) is the one joined
SWEEP_VERSION_OK = "book-sweep-v1"
DEP_GROUP_UNDERLYING = True  # D120 crypto rule: underlying x UTC date (design line 199)
UNDERLYING_DATE_PREFIX = "ud:"  # synthetic node injected as an event id (pairing has no date term)
FOLD_MANIFEST_VERSION = "ml-fold-manifest-v1"
HORIZONS = (1, 3, 12)  # target snapshots ahead (~2h, ~6h, ~24h); k = 1 is the confirmatory one
PRIMARY_HORIZON = 1
TARGET_FAMILIES = ("direction", "dmid", "absmove")  # y_class_h{k}, y_dmid_h{k}, y_absmove_h{k}
DEFAULT_MAP_VERSION = "fs2-fee-category-map-v1"
CATEGORY_MODES = ("all", "include", "exclude")

ID_DTYPES = {"market_id": str, "event_id": str, "capture_id": str}


# ---------------------------------------------------------------------------------------------
# Target
# ---------------------------------------------------------------------------------------------


def assign_class(dmid: np.ndarray | pd.Series, delta: float = DELTA_PRIMARY) -> np.ndarray:
    """3-class material direction of ``dmid``: 0 down, 1 flat (``|dmid| <= delta``), 2 up.

    Returns float with NaN where ``dmid`` is NaN (target unavailable is never imputed).
    """
    if not (delta > 0):
        raise ValueError("delta must be positive")
    d = np.asarray(dmid, dtype=float)
    out = np.full(d.shape, np.nan)
    ok = ~np.isnan(d)
    flat = np.abs(d) <= delta + _DELTA_EPS
    out[ok & flat] = CLASS_FLAT
    out[ok & ~flat & (d < 0)] = CLASS_DOWN
    out[ok & ~flat & (d > 0)] = CLASS_UP
    return out


def class_shares(y: np.ndarray | pd.Series) -> dict:
    v = np.asarray(y, dtype=float)
    v = v[~np.isnan(v)]
    n = len(v)
    return {
        "n": int(n),
        "down": float((v == CLASS_DOWN).mean()) if n else float("nan"),
        "flat": float((v == CLASS_FLAT).mean()) if n else float("nan"),
        "up": float((v == CLASS_UP).mean()) if n else float("nan"),
    }


# ---------------------------------------------------------------------------------------------
# Category policy
# ---------------------------------------------------------------------------------------------


def category_policy(
    mode: str = "all", categories: Iterable[str] = (), map_version: str = DEFAULT_MAP_VERSION
) -> dict:
    """The single config parameter that sets the population. Default: all categories."""
    if mode not in CATEGORY_MODES:
        raise ValueError(f"category mode must be one of {CATEGORY_MODES}, got {mode!r}")
    cats = sorted({str(c) for c in categories})
    if mode != "all" and not cats:
        raise ValueError(f"category mode {mode!r} needs a non-empty categories list")
    return {"mode": mode, "categories": cats, "map_version": map_version}


def apply_category_policy(
    df: pd.DataFrame, policy: dict | None = None, column: str = "fee_category"
) -> tuple[pd.DataFrame, dict]:
    """Filter rows by ``fee_category``. ``include`` keeps listed categories (missing is dropped);
    ``exclude`` drops listed categories (missing is kept: missing stays missing)."""
    policy = policy or category_policy()
    cats = policy["categories"]
    cat = df[column] if column in df.columns else pd.Series(np.nan, index=df.index, dtype=object)
    in_list = cat.isin(cats)
    if policy["mode"] == "all":
        keep = np.ones(len(df), bool)
    elif policy["mode"] == "include":
        keep = in_list.to_numpy()
    else:
        keep = ~in_list.to_numpy()
    info = {
        "policy": policy,
        "rows_in": int(len(df)),
        "rows_kept": int(keep.sum()),
        "rows_missing_category": int(cat.isna().sum()),
    }
    return df[keep].reset_index(drop=True), info


# ---------------------------------------------------------------------------------------------
# Feature registration (tier a). Lazy, idempotent, origin-side only.
# ---------------------------------------------------------------------------------------------

_HIST_RE = re.compile(r"^hist_(?:mid|t|vol)_([0-9]+)$")
# "rep_" = report-only columns (sweep-minus-Gamma gap), "dep_" = dependence-group ids (clustering).
_FORBIDDEN_PREFIX = (
    "j_", "next_", "fut_", "future_", "target_", "label_", "y_", "rep_", "dep_",
)
_FORBIDDEN_SUFFIX = ("_j", "_next", "_future")


def is_origin_side(col: str) -> bool:
    """True if ``col`` can be read by a feature: origin columns and history ``hist_*_k`` (1..6)."""
    if col in features.LABEL_COLUMNS or col.startswith(_FORBIDDEN_PREFIX):
        return False
    if col.endswith(_FORBIDDEN_SUFFIX):
        return False
    m = _HIST_RE.match(col)
    if col.startswith("hist_"):
        return bool(m) and 1 <= int(m.group(1)) <= HISTORY_DEPTH
    return True


def register_ml(spec: FeatureSpec) -> FeatureSpec:
    """``features.register`` plus the pipeline's origin-side check (no j/next/future columns,
    no history lag outside 1..6). Label columns are still refused by the registry itself."""
    bad = [c for c in spec.requires if not is_origin_side(c)]
    if bad:
        raise ValueError(f"feature {spec.name!r} reads non-origin columns {sorted(bad)}")
    if not spec.name.startswith("ml_") and not is_origin_side(spec.name):
        raise ValueError(f"feature name {spec.name!r} looks label-side")
    return features.register(spec)


def _num(o: pd.DataFrame, c: str) -> np.ndarray:
    return pd.to_numeric(o[c], errors="coerce").to_numpy(float)


def _mid(o: pd.DataFrame) -> np.ndarray:
    return (_num(o, "best_bid") + _num(o, "best_ask")) / 2


def _s(o: pd.DataFrame, v: np.ndarray) -> pd.Series:
    return pd.Series(v, index=o.index, dtype=float)


def _logit_mid(o):
    m = _mid(o)
    with np.errstate(divide="ignore", invalid="ignore"):
        return _s(o, np.log(m / (1 - m)))


def _abs_mid_dev(o):
    return _s(o, np.abs(_mid(o) - 0.5))


def _chg(name: str):
    return lambda o: _s(o, _num(o, name))


def _chg_missing(name: str):
    return lambda o: _s(o, np.isnan(_num(o, name)).astype(float))


def _own_dmid_prev(o):
    return _s(o, _mid(o) - _num(o, "hist_mid_1"))


def _own_prev_age_h(o):
    return _s(o, (_num(o, "t_i") - _num(o, "hist_t_1")) / 3600.0)


def _hist_mat(o: pd.DataFrame) -> np.ndarray:
    cols = [_mid(o)] + [_num(o, f"hist_mid_{k}") for k in range(1, HISTORY_DEPTH + 1)]
    return np.column_stack(cols)


def _own_vol(o):
    d = np.diff(_hist_mat(o), axis=1)
    ok = ~np.isnan(d)
    cnt = ok.sum(1)
    ss = np.where(ok, d, 0.0) ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        rms = np.sqrt(ss.sum(1) / cnt)
    return _s(o, np.where(cnt >= 2, rms, np.nan))


def _own_n_prior(o):
    return _s(o, (~np.isnan(_hist_mat(o)[:, 1:])).sum(1).astype(float))


def _spread(o):
    sp = _num(o, "spread")
    return _s(o, np.where(np.isnan(sp), _num(o, "best_ask") - _num(o, "best_bid"), sp))


def _spread_over_tick(o):
    sp = _spread(o).to_numpy()
    tick = _num(o, "order_price_min_tick_size")
    with np.errstate(divide="ignore", invalid="ignore"):
        return _s(o, np.where(tick > 0, sp / tick, np.nan))


def _ltp_minus_mid(o):
    return _s(o, _num(o, "last_trade_price") - _mid(o))


def _log1p_liq(o):
    return _s(o, np.log1p(np.clip(_num(o, "liquidity"), 0, None)))


def _log1p_vol(o):
    return _s(o, np.log1p(np.clip(_num(o, "volume24hr"), 0, None)))


def _turnover(o):
    liq, vol = _num(o, "liquidity"), _num(o, "volume24hr")
    with np.errstate(divide="ignore", invalid="ignore"):
        return _s(o, np.where(liq > 0, vol / liq, np.nan))


def _hours_to_end(o):
    end = panel._epoch(o["end_date"])
    return _s(o, np.log1p(np.clip((end - _num(o, "t_i")) / 3600.0, 0, None)))


def _end_unknown(o):
    return _s(o, np.isnan(panel._epoch(o["end_date"])).astype(float))


def _staleness_h(o):
    upd = panel._epoch(o["updated_at"])
    age = (_num(o, "t_i") - upd) / 3600.0
    return _s(o, np.where(age < 0, np.nan, age))  # updated_at after t_i: invalid, not clipped


def _passthrough(name: str):
    return lambda o: _s(o, _num(o, name))


def _market_age_h(o):
    created = panel._epoch(o["created_at"])
    return _s(o, np.clip((_num(o, "t_i") - created) / 3600.0, 0, None))


def _vol_num_delta(o):
    # cumulative field: origin value minus the i-1 value, never anything from j
    return _s(o, _num(o, "volume_num") - _num(o, "hist_vol_1"))


_HIST_MID = tuple(f"hist_mid_{k}" for k in range(1, HISTORY_DEPTH + 1))
_BIDASK = ("best_bid", "best_ask")

# (name, family, requires, function)
_TIER_A: list[tuple[str, str, tuple[str, ...], Callable[[pd.DataFrame], pd.Series]]] = [
    ("ml_logit_mid", "ml_price", _BIDASK, _logit_mid),
    ("ml_abs_mid_dev", "ml_price", _BIDASK, _abs_mid_dev),
    ("ml_chg_1h", "ml_momentum", ("chg_1h",), _chg("chg_1h")),
    ("ml_chg_1d", "ml_momentum", ("chg_1d",), _chg("chg_1d")),
    ("ml_chg_1w", "ml_momentum", ("chg_1w",), _chg("chg_1w")),
    ("ml_chg_1h_missing", "ml_momentum", ("chg_1h",), _chg_missing("chg_1h")),
    ("ml_chg_1d_missing", "ml_momentum", ("chg_1d",), _chg_missing("chg_1d")),
    ("ml_chg_1w_missing", "ml_momentum", ("chg_1w",), _chg_missing("chg_1w")),
    ("ml_own_dmid_prev", "ml_momentum", (*_BIDASK, "hist_mid_1"), _own_dmid_prev),
    ("ml_own_prev_age_h", "ml_momentum", ("t_i", "hist_t_1"), _own_prev_age_h),
    ("ml_own_vol", "ml_volatility", (*_BIDASK, *_HIST_MID), _own_vol),
    ("ml_own_n_prior", "ml_volatility", (*_BIDASK, *_HIST_MID), _own_n_prior),
    ("ml_spread", "ml_liquidity", (*_BIDASK, "spread"), _spread),
    (
        "ml_spread_over_tick",
        "ml_liquidity",
        (*_BIDASK, "spread", "order_price_min_tick_size"),
        _spread_over_tick,
    ),
    ("ml_ltp_minus_mid", "ml_liquidity", (*_BIDASK, "last_trade_price"), _ltp_minus_mid),
    ("ml_log1p_liq", "ml_liquidity", ("liquidity",), _log1p_liq),
    ("ml_log1p_vol24", "ml_liquidity", ("volume24hr",), _log1p_vol),
    ("ml_turnover", "ml_liquidity", ("liquidity", "volume24hr"), _turnover),
    ("ml_log_hours_to_end", "ml_time", ("end_date", "t_i"), _hours_to_end),
    ("ml_end_unknown", "ml_time", ("end_date",), _end_unknown),
    ("ml_quote_staleness_h", "ml_quality", ("updated_at", "t_i"), _staleness_h),
    ("ml_neg_risk", "ml_structure", ("neg_risk",), _passthrough("neg_risk")),
    ("ml_nr_member", "ml_structure", ("nr_member",), _passthrough("nr_member")),
    ("ml_nr_excess", "ml_structure", ("nr_excess",), _passthrough("nr_excess")),
    ("ml_tick_size", "ml_metadata", ("order_price_min_tick_size",),
     _passthrough("order_price_min_tick_size")),
    ("ml_order_min_size", "ml_metadata", ("order_min_size",), _passthrough("order_min_size")),
    ("ml_fees_enabled", "ml_metadata", ("fees_enabled",), _passthrough("fees_enabled")),
    ("ml_taker_base_fee", "ml_metadata", ("taker_base_fee",), _passthrough("taker_base_fee")),
    ("ml_accepting_orders", "ml_metadata", ("accepting_orders",),
     _passthrough("accepting_orders")),
    ("ml_market_age_h", "ml_metadata", ("created_at", "t_i"), _market_age_h),
    ("ml_volume_num", "ml_metadata", ("volume_num",), _passthrough("volume_num")),
    ("ml_volume_num_delta_prev", "ml_metadata", ("volume_num", "hist_vol_1"), _vol_num_delta),
    ("ml_event_open_interest", "ml_metadata", ("event_open_interest",),
     _passthrough("event_open_interest")),
]
TIER_A_NAMES: tuple[str, ...] = tuple(n for n, *_ in _TIER_A)

# ---------------------------------------------------------------------------------------------
# Extended features: book sweep (a11, features only) and sibling moves (a10). Origin-side only.
# ---------------------------------------------------------------------------------------------


def _sw(name: str):
    return lambda o: _s(o, _num(o, name))


def _sw_imbalance(bid: str, ask: str):
    def f(o):
        b, a = _num(o, bid), _num(o, ask)
        with np.errstate(divide="ignore", invalid="ignore"):
            return _s(o, np.where(b + a > 0, (b - a) / (b + a), np.nan))

    return f


def _sw_log_depth(name: str):
    return lambda o: _s(o, np.log1p(np.clip(_num(o, name), 0, None)))


def _sw_microprice_disp(o):
    # relative to the SWEEP's own mid, never to the Gamma mid
    bb, ba = _num(o, "sw_best_bid"), _num(o, "sw_best_ask")
    bs, as_ = _num(o, "sw_bid_size_1"), _num(o, "sw_ask_size_1")
    with np.errstate(divide="ignore", invalid="ignore"):
        micro = np.where(bs + as_ > 0, (ba * bs + bb * as_) / (bs + as_), np.nan)
    return _s(o, micro - (bb + ba) / 2)


def _sw_spread(o):
    return _s(o, _num(o, "sw_best_ask") - _num(o, "sw_best_bid"))


_SW_BOOK = ("sw_best_bid", "sw_best_ask", "sw_bid_size_1", "sw_ask_size_1")
_EXT: list[tuple[str, str, tuple[str, ...], Callable[[pd.DataFrame], pd.Series]]] = [
    ("ml_sw_imb_top", "book", ("sw_bid_size_1", "sw_ask_size_1"),
     _sw_imbalance("sw_bid_size_1", "sw_ask_size_1")),
    ("ml_sw_microprice_disp", "book", _SW_BOOK, _sw_microprice_disp),
    ("ml_sw_spread", "book", ("sw_best_bid", "sw_best_ask"), _sw_spread),
    ("ml_sw_log_depth_bid_1c", "book", ("sw_depth_bid_1c",), _sw_log_depth("sw_depth_bid_1c")),
    ("ml_sw_log_depth_ask_1c", "book", ("sw_depth_ask_1c",), _sw_log_depth("sw_depth_ask_1c")),
    ("ml_sw_log_depth_bid_5c", "book", ("sw_depth_bid_5c",), _sw_log_depth("sw_depth_bid_5c")),
    ("ml_sw_log_depth_ask_5c", "book", ("sw_depth_ask_5c",), _sw_log_depth("sw_depth_ask_5c")),
    ("ml_sw_imb_1c", "book", ("sw_depth_bid_1c", "sw_depth_ask_1c"),
     _sw_imbalance("sw_depth_bid_1c", "sw_depth_ask_1c")),
    ("ml_sw_imb_5c", "book", ("sw_depth_bid_5c", "sw_depth_ask_5c"),
     _sw_imbalance("sw_depth_bid_5c", "sw_depth_ask_5c")),
    ("ml_sw_n_bid_levels", "book", ("sw_n_bid_levels",), _sw("sw_n_bid_levels")),
    ("ml_sw_n_ask_levels", "book", ("sw_n_ask_levels",), _sw("sw_n_ask_levels")),
    ("ml_sw_book_age_s", "book", ("sw_book_age_s",), _sw("sw_book_age_s")),
    ("ml_sib_mean_abs_dmid", "ml_structure", ("sib_mean_abs_dmid",), _sw("sib_mean_abs_dmid")),
    ("ml_sib_max_abs_dmid", "ml_structure", ("sib_max_abs_dmid",), _sw("sib_max_abs_dmid")),
]
EXT_NAMES: tuple[str, ...] = tuple(n for n, *_ in _EXT)
SWEEP_NAMES: tuple[str, ...] = tuple(n for n in EXT_NAMES if n.startswith("ml_sw_"))
SIBLING_NAMES: tuple[str, ...] = tuple(n for n in EXT_NAMES if n.startswith("ml_sib_"))
EXTENDED_NAMES: tuple[str, ...] = (*TIER_A_NAMES, *EXT_NAMES)  # TIER_A_NAMES itself is unchanged
SW_COLUMNS = (
    "sw_best_bid", "sw_best_ask", "sw_bid_size_1", "sw_ask_size_1", "sw_depth_bid_1c",
    "sw_depth_ask_1c", "sw_depth_bid_5c", "sw_depth_ask_5c", "sw_n_bid_levels",
    "sw_n_ask_levels", "sw_book_age_s",
)


def register_extended() -> tuple[str, ...]:
    """Register the sweep and sibling features once (idempotent) through ``register_ml``."""
    for name, fam, req, fn in _EXT:
        cur = features.REGISTRY.get(name)
        if cur is not None:
            if cur.version != EXT_FEATURE_SET_VERSION or cur.requires != req:
                raise ValueError(f"feature {name!r} registered with a different definition")
            continue
        register_ml(FeatureSpec(name, fam, EXT_FEATURE_SET_VERSION, fn, req))
    return EXT_NAMES


def extended_feature_versions() -> dict:
    register_tier_a()
    register_extended()
    return features.versions(list(EXTENDED_NAMES))


def sweep_columns(market_ids: np.ndarray, sweep_rows: pd.DataFrame | None) -> pd.DataFrame:
    """Origin-side ``sw_*`` columns for ``market_ids`` from ONE sweep's rows (the declared A sweep).

    Missing sweep, a market not in the sweep, or ``missing_from_response`` gives NaN (never 0).
    Also returns ``sw_mid`` (two-sided books only) for the report-only gap placebo; it is never
    a feature column. ``sw_book_age_s`` is the batch receipt minus the book's own timestamp
    (negative: invalid, NaN).
    """
    n = len(market_ids)
    cols = {c: np.full(n, np.nan) for c in (*SW_COLUMNS, "sw_mid")}
    if sweep_rows is not None and len(sweep_rows):
        sw = sweep_rows.copy()
        sw["market_id"] = sw["market_id"].astype(str)
        sw = sw[sw["state"].isin(["two_sided", "one_sided", "empty"])]
        sw = sw.drop_duplicates("market_id").set_index("market_id").reindex(market_ids)
        src = {
            "sw_best_bid": "best_bid", "sw_best_ask": "best_ask", "sw_bid_size_1": "bid_size_1",
            "sw_ask_size_1": "ask_size_1", "sw_depth_bid_1c": "depth_bid_1c",
            "sw_depth_ask_1c": "depth_ask_1c", "sw_depth_bid_5c": "depth_bid_5c",
            "sw_depth_ask_5c": "depth_ask_5c", "sw_n_bid_levels": "n_bid_levels",
            "sw_n_ask_levels": "n_ask_levels",
        }
        for dst, c in src.items():
            cols[dst] = pd.to_numeric(sw[c], errors="coerce").to_numpy(float)
        two = (sw["state"] == "two_sided").to_numpy()
        cols["sw_mid"] = np.where(two, (cols["sw_best_bid"] + cols["sw_best_ask"]) / 2, np.nan)
        rec = panel._epoch(sw["batch_receipt_utc"])
        ts = pd.to_numeric(sw["book_timestamp"], errors="coerce").to_numpy(float) / 1000.0
        age = rec - ts
        cols["sw_book_age_s"] = np.where(age < 0, np.nan, age)
    return pd.DataFrame(cols)


def pick_sweeps(sweep_root: Path, min_coverage: float = SWEEP_MIN_COVERAGE) -> tuple[dict, dict]:
    """Declared sweep per snapshot: the **A** sweep (``series_index == 0``) of the earliest
    complete series for that ``snapshot_id`` (B is never used). Returns ``(usable, report)``;
    ``usable[capture_id] = {receipt_epoch, started_epoch, returned, eligible, dir, sweep_id}``
    where ``receipt_epoch`` is the sweep's ``finished_utc`` (>= every batch receipt). Sweeps that
    are incomplete or below ``min_coverage`` are listed in ``report`` and not usable. Reads
    manifests only.
    """
    usable: dict[str, dict] = {}
    report: dict = {"considered": 0, "not_a_sweep": 0, "not_complete": 0, "low_coverage": [],
                    "duplicate_a_for_snapshot": 0}
    for mp in sorted(Path(sweep_root).glob("*/manifest.json")):
        m = json.loads(mp.read_text())
        if m.get("series_index") != SWEEP_SERIES_INDEX:
            report["not_a_sweep"] += 1
            continue
        report["considered"] += 1
        if m.get("state") != "complete" or m.get("sweep_version") != SWEEP_VERSION_OK:
            report["not_complete"] += 1
            continue
        req, ret = int(m["tokens_requested"]), int(m["tokens_returned"])
        if req <= 0 or ret / req < min_coverage:
            report["low_coverage"].append(m["sweep_id"])
            continue
        started = float(panel._epoch(pd.Series([m["started_utc"]]))[0])
        rec = {
            "receipt_epoch": float(panel._epoch(pd.Series([m["finished_utc"]]))[0]),
            "started_epoch": started, "returned": ret, "eligible": req,
            "dir": str(mp.parent), "sweep_id": m["sweep_id"],
        }
        cid = m["snapshot_id"]
        if cid in usable:
            report["duplicate_a_for_snapshot"] += 1
            if usable[cid]["started_epoch"] <= started:
                continue
        usable[cid] = rec
    return usable, report


def load_sweep_rows(entry: dict) -> pd.DataFrame:
    """Slim rows of one declared sweep (ids as strings)."""
    use = ["market_id", "batch_receipt_utc", "book_timestamp", "best_bid", "best_ask",
           "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c",
           "depth_ask_5c", "n_bid_levels", "n_ask_levels", "state"]
    return pd.read_csv(Path(entry["dir"]) / "rows.csv.gz", usecols=use,
                       dtype={"market_id": str, "book_timestamp": str})


def sibling_moves(
    rows_i: pd.DataFrame, hist1: pd.DataFrame | None, market_ids: np.ndarray
) -> pd.DataFrame:
    """a10: mean and max ``|d mid|`` over ``i-1 -> i`` of the OTHER markets in the same group.

    Group = ``neg_risk_market_id`` when present, else ``event_id`` (origin snapshot rows only).
    A market never counts toward its own statistic. ``hist1`` is ``slim_history`` of snapshot
    i-1; a link older than ``HISTORY_MAX_GAP_H`` or an invalid quote gives NaN for that sibling,
    and a market without a valid sibling gets NaN (never 0). Nothing from j is read.
    """
    n = len(market_ids)
    nan = pd.DataFrame({"sib_mean_abs_dmid": np.full(n, np.nan),
                        "sib_max_abs_dmid": np.full(n, np.nan)})
    if hist1 is None or not len(rows_i):
        return nan
    r = rows_i.drop_duplicates("market_id").reset_index(drop=True)
    mid = np.where(panel.target_valid(r), (_num(r, "best_bid") + _num(r, "best_ask")) / 2, np.nan)
    t = panel._epoch(r["received_utc"])
    h = hist1.reindex(r["market_id"].to_numpy())
    gap = t - h["t"].to_numpy(float)
    link = (gap > 0) & (gap <= HISTORY_MAX_GAP_H * 3600)
    a = np.where(link, np.abs(mid - h["mid"].to_numpy(float)), np.nan)
    nr = r["neg_risk_market_id"] if "neg_risk_market_id" in r else pd.Series(np.nan, index=r.index)
    nr = nr.where(nr.astype(str).str.strip().ne(""))
    key = pd.Series(np.where(nr.notna(), "n:" + nr.astype(str), "e:" + r["event_id"].astype(str)),
                    index=r.index).where(nr.notna() | r["event_id"].notna())
    d = pd.DataFrame({"key": key, "a": a, "mkt": r["market_id"].to_numpy()})
    valid = d.dropna(subset=["key", "a"]).sort_values(["key", "a"], ascending=[True, False])
    rank = valid.groupby("key").cumcount()
    top1 = valid[rank == 0].set_index("key")["a"]
    top2 = valid[rank == 1].set_index("key")["a"]
    agg = valid.groupby("key")["a"].agg(["sum", "count"])
    k = d["key"]
    own = d["a"].to_numpy(float)
    has = ~np.isnan(own)
    cnt = agg["count"].reindex(k).to_numpy(float) - has
    tot = agg["sum"].reindex(k).to_numpy(float) - np.where(has, own, 0.0)
    t1, t2 = top1.reindex(k).to_numpy(float), top2.reindex(k).to_numpy(float)
    mx = np.where(has & (own >= t1), t2, t1)  # drop self when self is the group maximum
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(cnt > 0, tot / cnt, np.nan)
    mx = np.where(cnt > 0, mx, np.nan)
    out = pd.DataFrame({"sib_mean_abs_dmid": mean, "sib_max_abs_dmid": mx}, index=d["mkt"])
    return out.reindex(market_ids).reset_index(drop=True)


# ---------------------------------------------------------------------------------------------
# D120 dependence groups (clustering ids, never features)
# ---------------------------------------------------------------------------------------------


def _json_list(v) -> list[str]:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return []
    try:
        x = json.loads(v) if isinstance(v, str) else v
    except ValueError:
        return []
    return sorted({str(i) for i in x if i not in (None, "")}) if isinstance(x, list) else []


SERIES_DATE_PREFIX = "sd:"


def group_facts(rows_i: pd.DataFrame, underlying_date: bool = DEP_GROUP_UNDERLYING,
                mode: str = "season") -> tuple[dict, dict, dict]:
    """Per-market ``pairing.dependence_groups`` inputs from one origin snapshot, a
    ``market_id -> fallback`` map and a ``market_id -> no_parent`` map. A row with a sidecar
    (``ext_present`` and a ``fee_category``) uses ``event_ids``/``series_slugs``/
    ``neg_risk_market_id``; an older snapshot falls back to its single ``event_id`` (no series, no
    neg-risk link) and is flagged.

    ``underlying_date``: a market whose series slugs name an underlying (``pairing.underlyings``,
    the D120 token table) also gets the node ``ud:<underlying>|<UTC end date>``, injected as an
    extra event id, so same-underlying same-day markets share a group but different days do not.
    A market without an end date or without a named underlying gets no such node.

    ``mode``: ``"season"`` links the series slug itself (league-season; the original
    ``dep_group``). ``"fixture_day"`` (research_lab/DEPENDENCE_CLUSTERING_ANALYSIS.md) drops the
    season link and instead injects ``sd:<series slug>|<UTC end date>`` nodes (no node without an
    end date) and unions ``parentEventId`` (sidecar v3 ``parent_event_ids``). ``no_parent`` is True
    for a sidecar row that lacks the v3 column (parent links unavailable) or a fallback row.
    """
    if mode not in ("season", "fixture_day"):
        raise ValueError(f"unknown dependence-group mode {mode!r}")
    r = rows_i.drop_duplicates("market_id")
    ext = np.zeros(len(r), bool)
    if "ext_present" in r and "fee_category" in r:
        ext = (pd.to_numeric(r["ext_present"], errors="coerce").to_numpy(float) == 1) & (
            r["fee_category"].notna().to_numpy()
        )
    end = panel._epoch(r["end_date"]) if "end_date" in r else np.full(len(r), np.nan)
    facts: dict[str, dict] = {}
    fallback: dict[str, bool] = {}
    no_parent: dict[str, bool] = {}
    ev = r["event_id"].to_numpy()
    nrm = r["neg_risk_market_id"].to_numpy() if "neg_risk_market_id" in r else np.full(len(r), None)
    eids = r["event_ids"].to_numpy() if "event_ids" in r else np.full(len(r), None)
    sl = r["series_slugs"].to_numpy() if "series_slugs" in r else np.full(len(r), None)
    pids = r["parent_event_ids"].to_numpy() if "parent_event_ids" in r else np.full(len(r), None)
    for k, m in enumerate(r["market_id"].astype(str).to_numpy()):
        npar = True
        if ext[k]:
            neg = None if pd.isna(nrm[k]) or str(nrm[k]).strip() == "" else str(nrm[k])
            f = {"event_ids": _json_list(eids[k]), "series_slugs": _json_list(sl[k]),
                 "event_slugs": [], "neg_risk_market_id": neg}
            day = None if math.isnan(end[k]) else pd.Timestamp(
                end[k], unit="s", tz="UTC").strftime("%Y-%m-%d")
            if underlying_date and day:
                for u in pairing.underlyings(f):
                    f["event_ids"] = sorted({*f["event_ids"], f"{UNDERLYING_DATE_PREFIX}{u}|{day}"})
            if mode == "fixture_day":
                if day:
                    f["event_ids"] = sorted(
                        {*f["event_ids"], *(f"{SERIES_DATE_PREFIX}{x}|{day}"
                                            for x in f["series_slugs"])})
                f["series_slugs"] = []  # no season-level link
                npar = not (isinstance(pids[k], str) and pids[k].strip())
                f["parent_event_ids"] = [] if npar else _json_list(pids[k])
            facts[m] = f
        else:
            facts[m] = {"event_ids": [] if pd.isna(ev[k]) else [str(ev[k])], "series_slugs": [],
                        "event_slugs": [], "neg_risk_market_id": None}
        fallback[m] = not ext[k]
        no_parent[m] = npar
    return facts, fallback, no_parent


def dependence_group_ids(
    rows_i: pd.DataFrame, market_ids: np.ndarray, underlying_date: bool = DEP_GROUP_UNDERLYING
) -> pd.DataFrame:
    """``dep_group`` (fixture-day: event, parentEventId, negRisk, series x UTC end date,
    underlying x UTC date), ``dep_group_season`` (the former league-season grouping: D120
    ``fs2-dependence-groups-v1`` plus underlying x UTC date; pre-declared sensitivity),
    ``dep_group_fallback`` (1.0 = event-id fallback, no sidecar), ``dep_group_no_parent`` (1.0 =
    no ``parentEventId`` information: fixture-day group lacks parent links) and
    ``dep_group_unmatched`` (1.0 = market absent from the snapshot: singleton ``g:u:<id>``) per
    market, via ``pairing.dependence_groups`` (imported, not reimplemented). Never None."""
    mids = [str(m) for m in market_ids]
    out: dict = {}
    for col, mode in (("dep_group", "fixture_day"), ("dep_group_season", "season")):
        facts, fb, npar = group_facts(rows_i, underlying_date, mode)
        groups = pairing.dependence_groups(facts, underlying=False)  # underlying via date node
        out[col] = [groups.get(m, "g:u:" + m) for m in mids]
        if mode == "season":
            out["dep_group_fallback"] = [float(fb[m]) if m in fb else 1.0 for m in mids]
            out["dep_group_unmatched"] = [float(m not in groups) for m in mids]
        else:
            out["dep_group_no_parent"] = [float(npar[m]) if m in npar else 1.0 for m in mids]
    return pd.DataFrame(out)


def pool_dependence_groups(df: pd.DataFrame, col: str = "dep_group") -> pd.Series:
    """Connect per-period groups across periods. Each market's period-local groups become its
    ``event_ids`` for ``pairing.dependence_groups``, so a market seen in two periods merges them."""
    if not len(df):
        return pd.Series(dtype=object)
    loc = df.assign(_k=df["period"].astype(str) + "|" + df[col].astype(str))
    sets = loc.groupby(loc["market_id"].astype(str))["_k"].agg(lambda x: sorted(set(x)))
    facts = {m: {"event_ids": v, "series_slugs": [], "event_slugs": [], "neg_risk_market_id": None}
             for m, v in sets.items()}
    groups = pairing.dependence_groups(facts, underlying=False)
    ids = df["market_id"].astype(str)
    return pd.Series([groups.get(m, "g:u:" + m) for m in ids], index=df.index)



def register_tier_a() -> tuple[str, ...]:
    """Register the tier-(a) feature set once (idempotent). Returns the ordered names."""
    for name, fam, req, fn in _TIER_A:
        cur = features.REGISTRY.get(name)
        if cur is not None:
            if cur.version != FEATURE_SET_VERSION or cur.requires != req:
                raise ValueError(f"feature {name!r} registered with a different definition")
            continue
        register_ml(FeatureSpec(name, fam, FEATURE_SET_VERSION, fn, req))
    return TIER_A_NAMES


def feature_frame(origin: pd.DataFrame, names: Iterable[str] = ()) -> pd.DataFrame:
    """Compute tier-(a) features from an origin frame. NaN is kept (trees take it natively)."""
    register_tier_a()
    register_extended()
    names = list(names) or list(TIER_A_NAMES)
    out = {n: features.compute_origin(features.REGISTRY[n], origin) for n in names}
    return pd.DataFrame(out, index=origin.index)


def feature_versions() -> dict:
    register_tier_a()
    return features.versions(list(TIER_A_NAMES))


# ---------------------------------------------------------------------------------------------
# Snapshot loading (sidecar optional)
# ---------------------------------------------------------------------------------------------


def _ext_columns() -> list[str]:
    from .ext_sidecar import COLUMNS, KEYS

    return [c for c in COLUMNS if c not in KEYS]


def load_snapshot_rows(snapshot_dir: Path, with_ext: bool = True) -> pd.DataFrame:
    """One complete snapshot's rows, plus sidecar columns when a complete sidecar exists.

    Older snapshots have no sidecar: the sidecar columns are then all-NaN, never 0.
    """
    d = Path(snapshot_dir)
    rows = pd.read_csv(d / "rows.csv.gz", dtype=ID_DTYPES)
    ext_cols = _ext_columns()
    got = False
    if with_ext and (d / "rows_ext.csv.gz").exists() and (d / "ext_manifest.json").exists():
        man = json.loads((d / "ext_manifest.json").read_text())
        if man.get("sidecar_status") == "complete":
            ext = pd.read_csv(d / "rows_ext.csv.gz", dtype={"market_id": str, "event_id": str})
            keep = ["market_id", "received_utc"] + [
                c for c in ext_cols if c in ext.columns and c not in rows.columns
            ]
            ext = ext[keep].drop_duplicates(["market_id", "received_utc"])
            rows = rows.merge(ext, on=["market_id", "received_utc"], how="left")
            got = True
    return _ensure_ext_columns(rows, got)


def _ensure_ext_columns(rows: pd.DataFrame, has_ext: bool = False) -> pd.DataFrame:
    rows = rows.copy()
    for c in _ext_columns():
        if c not in rows.columns:
            rows[c] = np.nan
    rows["ext_present"] = float(has_ext)
    return rows


def slim_history(rows: pd.DataFrame) -> pd.DataFrame:
    """Per-market history record of one snapshot (indexed by market_id): mid, receipt, volume."""
    r = rows.drop_duplicates("market_id")
    valid = panel.target_valid(r)
    mid = (r["best_bid"].to_numpy(float) + r["best_ask"].to_numpy(float)) / 2
    vol = pd.to_numeric(r["volume_num"], errors="coerce").to_numpy(float) if (
        "volume_num" in r.columns
    ) else np.full(len(r), np.nan)
    return pd.DataFrame(
        {
            "mid": np.where(valid, mid, np.nan),
            "t": panel._epoch(r["received_utc"]),
            "vol": vol,
        },
        index=pd.Index(r["market_id"].to_numpy(), name="market_id"),
    )


def history_columns(
    market_ids: np.ndarray, t_i: np.ndarray, history: list[pd.DataFrame]
) -> pd.DataFrame:
    """``hist_mid_k``, ``hist_t_k`` (k = 1..6) and ``hist_vol_1`` from snapshots i-1 .. i-6.

    ``history[k-1]`` is snapshot ``i-k`` (nearest first); only earlier snapshots can be passed.
    A link broken by a gap above ``HISTORY_MAX_GAP_H`` (or a missing/invalid quote) makes every
    older lag NaN as well, so a3 is missing when ``i-1`` is more than 3h earlier.
    """
    if len(history) > HISTORY_DEPTH:
        raise ValueError(f"history deeper than {HISTORY_DEPTH} snapshots")
    n = len(market_ids)
    cols: dict[str, np.ndarray] = {}
    alive = np.ones(n, bool)
    prev_t = np.asarray(t_i, float)
    for k in range(1, HISTORY_DEPTH + 1):
        mid, ht, vol = np.full(n, np.nan), np.full(n, np.nan), np.full(n, np.nan)
        if k <= len(history):
            h = history[k - 1].reindex(market_ids)
            hm, hh, hv = h["mid"].to_numpy(float), h["t"].to_numpy(float), h["vol"].to_numpy(float)
            gap = prev_t - hh
            link = (gap > 0) & (gap <= HISTORY_MAX_GAP_H * 3600)
            ok = alive & ~np.isnan(hm) & ~np.isnan(hh) & link
            mid, ht = np.where(ok, hm, np.nan), np.where(ok, hh, np.nan)
            vol = np.where(ok, hv, np.nan)
            alive = ok
            prev_t = np.where(ok, hh, prev_t)
        else:
            alive = np.zeros(n, bool)
        cols[f"hist_mid_{k}"], cols[f"hist_t_{k}"] = mid, ht
        if k == 1:
            cols["hist_vol_1"] = vol
    return pd.DataFrame(cols)


# ---------------------------------------------------------------------------------------------
# Period builder
# ---------------------------------------------------------------------------------------------


def _start_epoch(cap: dict) -> float:
    return float(panel._epoch(pd.Series([cap["started_utc"]]))[0])


def assert_sweep_coverage(
    returned: int, eligible: int, minimum: float = SWEEP_MIN_COVERAGE
) -> float:
    """Origin sweep must have returned at least ``minimum`` of the eligible tokens."""
    if eligible <= 0:
        raise ValueError("sweep has no eligible tokens")
    cov = returned / eligible
    if cov < minimum:
        raise ValueError(f"sweep coverage {cov:.4f} below {minimum}")
    return cov


def leak_feature_frame(
    snap_i: pd.DataFrame, snap_j: pd.DataFrame, market_ids: np.ndarray, pairs: pd.DataFrame,
    period: int, history: list[pd.DataFrame], sweep_rows_j: pd.DataFrame | None,
) -> pd.DataFrame:
    """DELIBERATE LEAK (leakage-alarm positive control): every extended feature computed from the
    **target** snapshot j exactly as ``build_period`` computes it from the origin snapshot (j's
    rows, history shifted by one so ``hist_1`` is snapshot i, j's sibling moves and sweep).
    Returns ``leak_<name>`` columns. It is never part of any feature set."""
    hist_j = [slim_history(snap_i)] + list(history)[: HISTORY_DEPTH - 1]
    rj = snap_j.drop_duplicates("market_id").set_index("market_id").reindex(market_ids)
    rj = rj.rename_axis("market_id").reset_index()
    t_ij = panel._epoch(rj["received_utc"])
    hj = history_columns(market_ids, t_ij, hist_j)
    nrj = features_dev.add_negrisk_columns(pairs[["market_id", "period"]], {period: snap_j})
    sw = sweep_columns(market_ids, sweep_rows_j)
    sib = sibling_moves(snap_j, hist_j[0], market_ids)
    oj = pd.concat([rj, hj, pd.DataFrame({"t_i": t_ij})], axis=1)
    oj["nr_excess"] = nrj["nr_excess"].to_numpy()
    oj["nr_member"] = nrj["nr_member"].to_numpy()
    oj = pd.concat([oj, sw.drop(columns="sw_mid"), sib], axis=1)
    lf = feature_frame(oj, EXTENDED_NAMES)
    return lf.add_prefix("leak_")


def build_period(
    snap_i: pd.DataFrame,
    snap_j: pd.DataFrame,
    cap_i: dict,
    cap_j: dict,
    period: int,
    history: list[pd.DataFrame] | None = None,
    sweep_receipt_epoch: float | None = None,
    delta: float = DELTA_PRIMARY,
    delta_sens: float = DELTA_SENSITIVITY,
    sweep_returned: int | None = None,
    sweep_eligible: int | None = None,
    sweep_rows: pd.DataFrame | None = None,
    sweep_started_epoch: float | None = None,
    dep_underlying_date: bool = DEP_GROUP_UNDERLYING,
    with_leak: bool = False,
    leak_sweep_rows: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame | None, dict]:
    """Paired rows for one consecutive complete-snapshot couple, with features and labels.

    ``history`` holds slim records (``slim_history``) of snapshots i-1, i-2, ... (nearest first).
    ``sweep_receipt_epoch`` (optional) is the origin sweep's receipt time; it only moves ``t0``.
    ``sweep_rows`` (the declared A sweep of snapshot i, see ``pick_sweeps``) feeds the ``ml_sw_*``
    features only; it needs ``sweep_receipt_epoch`` and, when ``sweep_started_epoch`` is given, the
    sweep must start at or after snapshot i's start and finish by snapshot j's start. Sibling
    moves (``ml_sib_*``) use ``history[0]`` (snapshot i-1). ``dep_group`` and
    ``dep_group_fallback`` are clustering ids, not features.
    Returns (None, counts) when the source/target start gap is outside 1.5 - 3h.
    """
    register_tier_a()
    gap_h = (_start_epoch(cap_j) - _start_epoch(cap_i)) / 3600.0
    base = {"period": period, "capture_i": cap_i["capture_id"], "capture_j": cap_j["capture_id"],
            "gap_h": gap_h}
    if not (GAP_MIN_H <= gap_h <= GAP_MAX_H):
        return None, {**base, "skipped": f"gap {gap_h:.2f}h outside [{GAP_MIN_H}, {GAP_MAX_H}]h"}
    j_sched = _start_epoch(cap_j)
    pairs, counts = panel.build_pair(snap_i, snap_j, j_sched, period)
    counts.update(base)
    binary = snap_i[snap_i["binary"] == 1]
    o = binary[panel.eligibility_mask(binary, j_sched)].reset_index(drop=True)
    aligned = len(o) == len(pairs) and (
        o["market_id"].to_numpy() == pairs["market_id"].to_numpy()
    ).all()
    if not aligned:
        raise RuntimeError("origin rows are not aligned with build_pair output")
    o = _ensure_ext_columns(o, bool(snap_i["ext_present"].iloc[0]) if "ext_present" in snap_i
                            and len(snap_i) else False)

    t_i = pairs["t_i"].to_numpy(float)
    if sweep_rows is not None:
        if sweep_receipt_epoch is None:
            raise ValueError("sweep_rows needs sweep_receipt_epoch")
        if sweep_receipt_epoch > j_sched:
            raise ValueError("sweep finished after the target snapshot started")
        if sweep_started_epoch is not None and sweep_started_epoch < _start_epoch(cap_i):
            raise ValueError("sweep started before the origin snapshot")
    hist = history_columns(o["market_id"].to_numpy(), t_i, history or [])
    nr = features_dev.add_negrisk_columns(pairs[["market_id", "period"]], {period: snap_i})
    origin = pd.concat(
        [o.reset_index(drop=True), hist, pd.DataFrame({"t_i": t_i})], axis=1
    )
    origin["nr_excess"] = nr["nr_excess"].to_numpy()
    origin["nr_member"] = nr["nr_member"].to_numpy()
    mkt = o["market_id"].to_numpy()
    sw = sweep_columns(mkt, sweep_rows)
    sib = sibling_moves(snap_i, history[0] if history else None, mkt)
    origin = pd.concat([origin, sw.drop(columns="sw_mid"), sib], axis=1)
    dg = dependence_group_ids(snap_i, mkt, dep_underlying_date)
    feats = feature_frame(origin, EXTENDED_NAMES)
    leak = None
    if with_leak:  # placebo positive control only: columns ``leak_<feature>``, never features
        leak = leak_feature_frame(snap_i, snap_j, mkt, pairs, period, history or [],
                                  leak_sweep_rows)

    sweep_info = None
    if sweep_receipt_epoch is not None:
        if sweep_returned is None or sweep_eligible is None:
            raise ValueError("sweep_receipt_epoch needs sweep_returned and sweep_eligible")
        cov = assert_sweep_coverage(sweep_returned, sweep_eligible)
        sweep_info = {"returned": int(sweep_returned), "eligible": int(sweep_eligible),
                      "coverage": cov}
    t0 = t_i if sweep_receipt_epoch is None else np.maximum(t_i, float(sweep_receipt_epoch))
    t_j = pairs["t_j"].to_numpy(float)
    mid_j = pairs["mid_j"].to_numpy(float)
    early = ~np.isnan(t_j) & (t_j < t0)  # target received before the origin cutoff
    t_j, mid_j = np.where(early, np.nan, t_j), np.where(early, np.nan, mid_j)
    mid_i = pairs["mid"].to_numpy(float)  # Gamma mid at i
    dmid = mid_j - mid_i  # Gamma mid at j minus Gamma mid at i
    out = pd.DataFrame(
        {
            "market_id": pairs["market_id"].to_numpy(),
            "event_id": pairs["event_id"].to_numpy(),
            "period": period,
            "capture_i": cap_i["capture_id"],
            "capture_j": cap_j["capture_id"],
            "t_i": t_i,
            "t0": t0,
            "t_j": t_j,
            "mid_i": mid_i,
            "mid_j": mid_j,
            "dmid": dmid,
            "horizon_h": (t_j - t_i) / 3600.0,
            "y_class": assign_class(dmid, delta),
            "y_class_sens": assign_class(dmid, delta_sens),
            "target_available": ~np.isnan(dmid),
            "fee_category": origin["fee_category"].to_numpy(),
        }
    )
    out = pd.concat([out, feats.reset_index(drop=True)], axis=1)
    if leak is not None:
        out = pd.concat([out, leak.reset_index(drop=True)], axis=1)
    out["rep_sw_gap"] = sw["sw_mid"].to_numpy() - mid_i  # report-only gap placebo; not a feature
    out["dep_group"] = dg["dep_group"].to_numpy()
    out["dep_group_season"] = dg["dep_group_season"].to_numpy()
    out["dep_group_fallback"] = dg["dep_group_fallback"].to_numpy()
    out["dep_group_no_parent"] = dg["dep_group_no_parent"].to_numpy()
    out["dep_group_unmatched"] = dg["dep_group_unmatched"].to_numpy()
    # UMA exclusion (origin sidecar field only). Missing = unknown: kept and flagged.
    uma = origin["uma_resolution_statuses"]
    unknown = uma.isna().to_numpy()
    empty = uma.astype(str).str.strip().isin(["", "[]", "{}", "null"]).to_numpy()
    proposed = ~unknown & ~empty
    out["uma_unknown"] = unknown.astype(float)
    counts.update(
        uma_excluded=int(proposed.sum()),
        uma_unknown=int(unknown.sum()),
        stale_negative_age=int((panel._epoch(origin["updated_at"]) > t_i).sum()),
        sweep=sweep_info,
        sweep_book_rows=int(sw["sw_mid"].notna().sum()),
        sibling_rows=int(sib["sib_mean_abs_dmid"].notna().sum()),
        dep_group_fallback_rows=int(np.nansum(dg["dep_group_fallback"].to_numpy(float))),
    )
    out = out[~proposed].reset_index(drop=True)
    counts.update(
        target_before_t0=int(early.sum()),
        target_available_after_t0=int(out["target_available"].sum()),
        ext_present=bool(origin["ext_present"].iloc[0]) if len(origin) else False,
        delta=delta,
    )
    return out, counts


def build_panel(
    captures: list[dict],
    load: Callable[[dict], pd.DataFrame] | None = None,
    sweep_receipts: dict[str, float] | None = None,
    delta: float = DELTA_PRIMARY,
    policy: dict | None = None,
    sweep_loader: Callable[[dict], pd.DataFrame] | None = None,
    dep_underlying_date: bool = DEP_GROUP_UNDERLYING,
    with_leak: bool = False,
) -> tuple[pd.DataFrame, list[dict]]:
    """All consecutive complete-snapshot pairs. ``captures`` ordered by start (with ``dir``).

    Loads one snapshot at a time (plus the previous one) and keeps only slim history records, so
    at most two full snapshots are in memory at once. ``sweep_receipts[capture_id]`` is a dict
    ``{"receipt_epoch", "returned", "eligible"}`` (coverage is asserted); an entry with ``dir``
    (from ``pick_sweeps``, the declared A sweep) is also joined as ``ml_sw_*`` features via
    ``sweep_loader`` (default ``load_sweep_rows``), one sweep in memory at a time. Per-period
    ``dep_group`` ids are pooled across periods (``pool_dependence_groups``). ``policy`` is applied
    to the whole panel; the applied counts are in ``df.attrs["category_info"]`` and are passed to
    ``plan_folds(category_info=...)``.
    """
    load = load or (lambda cap: load_snapshot_rows(Path(cap["dir"])))
    sweep_receipts = sweep_receipts or {}
    frames: list[pd.DataFrame] = []
    counts: list[dict] = []
    hist: list[pd.DataFrame] = []  # nearest first
    cur = load(captures[0]) if captures else None
    for k in range(len(captures) - 1):
        nxt = load(captures[k + 1])
        sw = sweep_receipts.get(captures[k]["capture_id"])
        srows = None
        if sw is not None and sw.get("dir"):
            srows = (sweep_loader or load_sweep_rows)(sw)
        lsw = None
        nx = sweep_receipts.get(captures[k + 1]["capture_id"])
        if with_leak and nx is not None and nx.get("dir"):
            lsw = (sweep_loader or load_sweep_rows)(nx)
        out, c = build_period(
            cur, nxt, captures[k], captures[k + 1], k, hist,
            None if sw is None else sw["receipt_epoch"], delta,
            sweep_returned=None if sw is None else sw["returned"],
            sweep_eligible=None if sw is None else sw["eligible"],
            sweep_rows=srows, sweep_started_epoch=None if sw is None else sw.get("started_epoch"),
            dep_underlying_date=dep_underlying_date, with_leak=with_leak, leak_sweep_rows=lsw,
        )
        del srows, lsw
        counts.append(c)
        if out is not None:
            frames.append(out)
        hist = [slim_history(cur)] + hist[: HISTORY_DEPTH - 1]
        cur = nxt
    panel_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if len(panel_df):
        panel_df["dep_group_period"] = panel_df["dep_group"]
        panel_df["dep_group_season_period"] = panel_df["dep_group_season"]
        panel_df["dep_group"] = pool_dependence_groups(panel_df, "dep_group")
        panel_df["dep_group_season"] = pool_dependence_groups(panel_df, "dep_group_season")
    panel_df, info = apply_category_policy(panel_df, policy)
    panel_df.attrs["category_info"] = info
    return panel_df, counts


# ---------------------------------------------------------------------------------------------
# Multi-horizon targets (EXPLORATORY except k = 1 direction)
# ---------------------------------------------------------------------------------------------
# Resolution targets (T5, "eventual resolution") are deliberately NOT implemented here: they need
# resolved-outcome labels fetched after close (label available only at resolution time) and a
# separate evidence standard (design section 1, T5 / MC2). An "executable opportunity" target
# likewise needs its own registered design (costs, depth, fill). Neither is a column of this panel.

_LABEL_NAMES = ("t_j", "mid_j", "dmid", "y_class", "y_dmid", "y_absmove", "target_available")


def add_horizon_targets(
    df: pd.DataFrame, horizons: Iterable[int] = HORIZONS, delta: float = DELTA_PRIMARY
) -> pd.DataFrame:
    """Add k-step targets: origin snapshot i, target snapshot i+k (``*_h{k}`` columns).

    The target for the row (market, period p) is the Gamma mid at the target snapshot of the same
    market's row in period p+k-1 (its ``mid_j``), so the source is the Gamma mid at both ends. It is
    NaN (unavailable, never imputed) unless every period p..p+k-1 is in the panel with a
    contiguous capture chain (``capture_j`` of one period is ``capture_i`` of the next, so each
    step passed the 1.5-3h gap rule), the market row exists in period p+k-1, and the target
    quote was received at or after the origin cutoff ``t0``. The latter is also required of every
    intermediate hop (their own ``t0``), which is conservative. ``t_j_h{k}`` is the label
    availability time used by the purge. k = 1 reproduces ``t_j``, ``dmid`` and ``y_class``
    exactly. Rows removed by the origin-side UMA exclusion in period p+k-1 give an unavailable
    target (documented selection limitation; these targets are exploratory).

    Targets: ``y_class_h{k}`` (3-class, ``assign_class``), ``y_dmid_h{k}`` (signed Gamma-mid
    change) and ``y_absmove_h{k}`` (1 iff ``|dmid| > delta``, the complement of the flat class).
    """
    out = df.copy(deep=False)
    if not len(df):
        return out
    per = df["period"].to_numpy()
    ci = df.groupby("period")["capture_i"].first().to_dict()
    cj = df.groupby("period")["capture_j"].first().to_dict()
    key = pd.MultiIndex.from_arrays([df["market_id"].to_numpy(), per])
    mid_j_s = pd.Series(df["mid_j"].to_numpy(float), index=key)
    t_j_s = pd.Series(df["t_j"].to_numpy(float), index=key)
    mid_j_s = mid_j_s[~mid_j_s.index.duplicated()]
    t_j_s = t_j_s[~t_j_s.index.duplicated()]
    t0, mid_i = df["t0"].to_numpy(float), df["mid_i"].to_numpy(float)
    for k in horizons:
        if k < 1:
            raise ValueError("horizon must be >= 1")
        ok_p = {}  # period p is chain-complete when periods p..p+k-1 exist and are contiguous
        for p in ci:
            ok_p[p] = all(p + m in ci and ci[p + m] == cj[p + m - 1] for m in range(1, k))
        chain = pd.Series(per).map(ok_p).fillna(False).to_numpy(bool)
        tgt_key = pd.MultiIndex.from_arrays([df["market_id"].to_numpy(), per + (k - 1)])
        t_j = t_j_s.reindex(tgt_key).to_numpy(float)
        mid_j = mid_j_s.reindex(tgt_key).to_numpy(float)
        bad = ~chain | np.isnan(t_j) | np.isnan(mid_j) | (t_j < t0)
        t_j, mid_j = np.where(bad, np.nan, t_j), np.where(bad, np.nan, mid_j)
        dmid = mid_j - mid_i
        cls = assign_class(dmid, delta)
        out[f"t_j_h{k}"] = t_j
        out[f"mid_j_h{k}"] = mid_j
        out[f"dmid_h{k}"] = dmid
        out[f"y_class_h{k}"] = cls
        out[f"y_dmid_h{k}"] = dmid
        out[f"y_absmove_h{k}"] = np.where(np.isnan(cls), np.nan, (cls != CLASS_FLAT).astype(float))
        out[f"target_available_h{k}"] = ~np.isnan(dmid)
    out.attrs = dict(df.attrs)
    return out


def horizon_view(df: pd.DataFrame, k: int) -> pd.DataFrame:
    """The panel with the canonical label columns replaced by the horizon-k ones.

    ``t_j``, ``mid_j``, ``dmid``, ``y_class``, ``y_dmid``, ``y_absmove`` and ``target_available``
    now describe snapshot i+k, so ``period_table``, ``fold_masks``, ``inner_split`` and every arm
    purge on the label-availability time of the k-step target. For k = 1 the existing columns are
    kept (``y_dmid`` / ``y_absmove`` are derived if absent), so the confirmatory target is
    unchanged. Requires ``add_horizon_targets`` for k > 1.
    """
    v = df.copy(deep=False)
    if k == 1:
        if "y_dmid" not in v.columns:
            v["y_dmid"] = v["dmid"]
            cls = v["y_class"].to_numpy(float)
            v["y_absmove"] = np.where(np.isnan(cls), np.nan, (cls != CLASS_FLAT).astype(float))
    else:
        if f"y_class_h{k}" not in df.columns:
            raise ValueError(f"horizon {k} targets missing; call add_horizon_targets first")
        for n in _LABEL_NAMES:
            v[n] = df[f"{n}_h{k}"]
        v["horizon_h"] = (v["t_j"] - v["t_i"]) / 3600.0
    v.attrs = dict(df.attrs)
    return v


def labelled(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["target_available"]].reset_index(drop=True)


# ---------------------------------------------------------------------------------------------
# Fold plan
# ---------------------------------------------------------------------------------------------


def period_table(df: pd.DataFrame) -> list[dict]:
    """One record per qualifying period: earliest origin cutoff and latest label time."""
    rows = []
    for p, g in df.groupby("period"):
        tj = g["t_j"].to_numpy(float)
        rows.append(
            {
                "period": int(p),
                "t0_min": float(g["t0"].min()),
                "t_label_max": float(np.nanmax(tj)) if (~np.isnan(tj)).any() else None,
                "n_rows": int(len(g)),
                "n_labelled": int(g["target_available"].sum()),
            }
        )
    return sorted(rows, key=lambda r: (r["t0_min"], r["period"]))


def _floor3(x: float) -> float:
    return math.floor(float(x) * 1000.0) / 1000.0


def _r(x: float | None) -> float | None:
    return None if x is None else round(float(x), 3)


def plan_folds(
    table: list[dict],
    policy: dict | None = None,
    feature_vers: dict | None = None,
    code_sha: str | None = None,
    block: int = BLOCK_PERIODS,
    min_train: int | None = None,
    embargo_s: float | None = None,
    delta: float = DELTA_PRIMARY,
    delta_sens: float = DELTA_SENSITIVITY,
    category_info: dict | None = None,
    horizon: int = PRIMARY_HORIZON,
) -> dict:
    """Deterministic expanding-window fold manifest with a sha256 over its canonical JSON.

    Fold k tests ``block`` consecutive periods; the first test block starts after at least
    ``min_train`` periods. A training row is kept only if its label time is at most
    ``(earliest test t0) - embargo`` (``evaluate.purged_train_mask``). The embargo is fixed at one
    nominal period (``EMBARGO_S``); the observed median period spacing is recorded and must lie in
    [GAP_MIN_H, GAP_MAX_H] hours. For ``horizon`` k > 1 (the table must come from
    ``period_table(horizon_view(df, k))``, so ``t_label_max`` is the k-step label time) the
    default embargo scales to k nominal periods, the label-availability horizon, and the default
    minimum training span grows by 4(k-1) periods (the outer purge and the inner split each lose
    about 2k periods of recent labels; with too few periods no full fold is planned).
    ``category_info`` (from ``build_panel``) supplies the applied
    policy and counts. ``code_sha`` is required. Only full blocks are planned.
    """
    if not code_sha:
        raise ValueError("code_sha is required")
    pol = (category_info or {}).get("policy") or policy or category_policy()
    if category_info is not None and policy is not None and policy != pol:
        raise ValueError("policy differs from the policy actually applied in category_info")
    periods = sorted(table, key=lambda r: (r["t0_min"], r["period"]))
    t0s = np.array([r["t0_min"] for r in periods])
    spacing = float(np.median(np.diff(t0s))) if len(t0s) > 1 else None
    if spacing is not None and not (GAP_MIN_H * 3600 <= spacing <= GAP_MAX_H * 3600):
        raise ValueError(f"observed period spacing {spacing / 3600:.2f}h outside allowed range")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if embargo_s is None:
        embargo_s = EMBARGO_S * EMBARGO_PERIODS * horizon
    if min_train is None:
        min_train = MIN_TRAIN_PERIODS + 4 * (horizon - 1)
    folds = []
    s = min_train
    while s + block <= len(periods):
        test = periods[s : s + block]
        cutoff = min(r["t0_min"] for r in test) - embargo_s
        folds.append(
            {
                "fold": len(folds),
                "train_periods": [r["period"] for r in periods[:s]],
                "test_periods": [r["period"] for r in test],
                "test_t0_min": _r(min(r["t0_min"] for r in test)),
                "embargo_s": _r(embargo_s),
                "purge_cutoff_t": _floor3(cutoff),
            }
        )
        s += block
    body = {
        "manifest_version": FOLD_MANIFEST_VERSION,
        "scheme": "expanding_window_blocks",
        "block_periods": block,
        "min_train_periods": min_train,
        "embargo_periods": EMBARGO_PERIODS,
        "embargo_s": _r(embargo_s),
        "observed_period_spacing_s": _r(spacing),
        "purge_rule": "keep train row iff t_j <= test_t0_min - embargo_s "
        "(evaluate.purged_train_mask)",
        "delta": delta,
        "delta_sens": delta_sens,
        "category_policy": pol,
        "category_applied": category_info,
        "feature_set_version": FEATURE_SET_VERSION,
        "feature_versions": feature_vers if feature_vers is not None else feature_versions(),
        "code_sha": code_sha,
        "periods": [
            {**r, "t0_min": _r(r["t0_min"]), "t_label_max": _r(r["t_label_max"])} for r in periods
        ],
        "folds": folds,
        "unused_trailing_periods": [r["period"] for r in periods[s:]] if folds else [
            r["period"] for r in periods
        ],
    }
    if horizon != PRIMARY_HORIZON:  # k = 1 manifests stay byte-identical
        body["horizon_snapshots"] = horizon
        body["purge_rule"] += f"; k={horizon}-step labels, embargo scaled to {horizon} periods"
    body["manifest_sha256"] = manifest_hash(body)
    return body


def manifest_hash(body: dict) -> str:
    core = {k: v for k, v in body.items() if k != "manifest_sha256"}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def fold_masks(df: pd.DataFrame, fold: dict) -> tuple[np.ndarray, np.ndarray]:
    """Row masks (train, test) for one fold. Train rows are earlier periods whose label was
    known by ``purge_cutoff_t`` (calls ``evaluate.purged_train_mask``); unlabelled rows are out."""
    avail = df["target_available"].to_numpy(bool)
    per = df["period"].to_numpy()
    cand = np.isin(per, fold["train_periods"]) & avail
    t_j = df["t_j"].to_numpy(float)
    train = cand & evaluate.purged_train_mask(t_j, float(fold["purge_cutoff_t"]))
    test = np.isin(per, fold["test_periods"]) & avail
    return train, test


# ---------------------------------------------------------------------------------------------
# Pre-declared sweep-gap diagnostic (mandatory in any development report using ml_sw_* features)
# ---------------------------------------------------------------------------------------------


def sweep_gap_diagnostic(df: pd.DataFrame, names: Iterable[str] = SWEEP_NAMES) -> dict:
    """The sweep is observed inside the label window (about 7-8 min after snapshot i), so a book
    feature could carry the sweep-minus-Gamma gap (``rep_sw_gap``). Reports, per feature, the
    Pearson and Spearman correlation with the gap on rows where both exist, plus the gap's own
    size. Report-only; it never selects or removes a feature."""
    gap = pd.to_numeric(df["rep_sw_gap"], errors="coerce")
    out: dict = {"n_gap": int(gap.notna().sum()),
                 "gap_abs_median": float(gap.abs().median()) if gap.notna().any() else None,
                 "share_abs_gap_lt_0025": float(
                     (gap.abs() < 0.0025).sum() / max(gap.notna().sum(), 1)),
                 "features": {}}
    for n in names:
        x = pd.to_numeric(df[n], errors="coerce")
        ok = x.notna() & gap.notna()
        if ok.sum() < 3 or x[ok].nunique() < 2 or gap[ok].nunique() < 2:
            out["features"][n] = {"n": int(ok.sum()), "pearson": None, "spearman": None}
            continue
        out["features"][n] = {"n": int(ok.sum()), "pearson": float(x[ok].corr(gap[ok])),
                              "spearman": float(x[ok].corr(gap[ok], method="spearman"))}
    return out


def rescore_with_gap_control(
    df: pd.DataFrame, base_cols: list[str], score_fn: Callable[[pd.DataFrame, list[str]], float],
    sweep_cols: Iterable[str] = SWEEP_NAMES,
) -> dict:
    """Hook: re-score the sweep arm with the gap controlled. ``score_fn(df, cols)`` returns a loss
    (lower is better) for a model on ``cols`` (``rep_sw_gap`` may appear in ``cols`` here: this is
    the report-only arm). Returns the losses of base, base+sweep, base+gap, base+sweep+gap and
    the sweep arm's gain without and with the gap control, plus the same on rows with
    ``|gap| < 0.0025``."""
    sw = list(sweep_cols)

    def run(d: pd.DataFrame) -> dict:
        loss = {k: score_fn(d, c) for k, c in {
            "base": base_cols, "base_sweep": [*base_cols, *sw],
            "base_gap": [*base_cols, "rep_sw_gap"],
            "base_sweep_gap": [*base_cols, *sw, "rep_sw_gap"],
        }.items()}
        return {"loss": loss, "gain_sweep": loss["base"] - loss["base_sweep"],
                "gain_sweep_given_gap": loss["base_gap"] - loss["base_sweep_gap"]}

    small = df[pd.to_numeric(df["rep_sw_gap"], errors="coerce").abs() < 0.0025]
    return {"all": run(df), "abs_gap_lt_0025": run(small)}
