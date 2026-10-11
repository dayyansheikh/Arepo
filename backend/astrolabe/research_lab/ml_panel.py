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
import re
from collections.abc import Callable, Iterable
from pathlib import Path

import numpy as np
import pandas as pd

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
SWEEP_MIN_COVERAGE = 0.99

FEATURE_SET_VERSION = "ml-tier-a-v1"
FOLD_MANIFEST_VERSION = "ml-fold-manifest-v1"
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
_FORBIDDEN_PREFIX = ("j_", "next_", "fut_", "future_", "target_", "label_", "y_")
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
    return _s(o, np.clip((_num(o, "t_i") - upd) / 3600.0, 0, None))


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
) -> tuple[pd.DataFrame | None, dict]:
    """Paired rows for one consecutive complete-snapshot couple, with features and labels.

    ``history`` holds slim records (``slim_history``) of snapshots i-1, i-2, ... (nearest first).
    ``sweep_receipt_epoch`` (optional) is the origin sweep's receipt time; it only moves ``t0``.
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
    hist = history_columns(o["market_id"].to_numpy(), t_i, history or [])
    nr = features_dev.add_negrisk_columns(pairs[["market_id", "period"]], {period: snap_i})
    origin = pd.concat(
        [o.reset_index(drop=True), hist, pd.DataFrame({"t_i": t_i})], axis=1
    )
    origin["nr_excess"] = nr["nr_excess"].to_numpy()
    origin["nr_member"] = nr["nr_member"].to_numpy()
    feats = feature_frame(origin)

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
) -> tuple[pd.DataFrame, list[dict]]:
    """All consecutive complete-snapshot pairs. ``captures`` ordered by start (with ``dir``).

    Loads one snapshot at a time (plus the previous one) and keeps only slim history records, so
    at most two full snapshots are in memory at once.
    """
    load = load or (lambda cap: load_snapshot_rows(Path(cap["dir"])))
    sweep_receipts = sweep_receipts or {}
    frames: list[pd.DataFrame] = []
    counts: list[dict] = []
    hist: list[pd.DataFrame] = []  # nearest first
    cur = load(captures[0]) if captures else None
    for k in range(len(captures) - 1):
        nxt = load(captures[k + 1])
        out, c = build_period(
            cur, nxt, captures[k], captures[k + 1], k, hist,
            sweep_receipts.get(captures[k]["capture_id"]), delta,
        )
        counts.append(c)
        if out is not None:
            frames.append(out)
        hist = [slim_history(cur)] + hist[: HISTORY_DEPTH - 1]
        cur = nxt
    panel_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return panel_df, counts


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


def _r(x: float | None) -> float | None:
    return None if x is None else round(float(x), 3)


def plan_folds(
    table: list[dict],
    policy: dict | None = None,
    feature_vers: dict | None = None,
    code_sha: str | None = None,
    block: int = BLOCK_PERIODS,
    min_train: int = MIN_TRAIN_PERIODS,
    embargo_s: float | None = None,
    delta: float = DELTA_PRIMARY,
) -> dict:
    """Deterministic expanding-window fold manifest with a sha256 over its canonical JSON.

    Fold k tests ``block`` consecutive periods; the first test block starts after at least
    ``min_train`` periods. A training row is kept only if its label time is at most
    ``(earliest test t0) - embargo`` (``evaluate.purged_train_mask``). The embargo defaults to the
    median spacing of period origin times (one period). Only full blocks are planned.
    """
    pol = policy or category_policy()
    periods = sorted(table, key=lambda r: (r["t0_min"], r["period"]))
    if embargo_s is None:
        t0s = np.array([r["t0_min"] for r in periods])
        embargo_s = float(np.median(np.diff(t0s))) * EMBARGO_PERIODS if len(t0s) > 1 else 0.0
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
                "purge_cutoff_t": _r(cutoff),
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
        "purge_rule": "keep train row iff t_j <= test_t0_min - embargo_s "
        "(evaluate.purged_train_mask)",
        "delta": delta,
        "category_policy": pol,
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
