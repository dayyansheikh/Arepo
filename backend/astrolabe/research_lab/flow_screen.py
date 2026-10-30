"""DEVELOPMENT screen of order-flow features on trade-active samples (NOT confirmation).

Why: Data note D1 (docs/research_lab/EXPERIMENT_LEDGER.md) found that about half of quoted eligible
markets never trade, so flow research needs a trade-active frame and a probability sample with
recorded inclusion probabilities (``trade_sample``). This module pairs each trade sample with the
NEXT complete universe snapshot and asks, descriptively, whether any pre-listed flow feature adds
anything to the reversal baseline. Nothing here is evidence and no edge claim is made.

Pre-listed family (fixed before any run; every member is run and reported, whatever the sign):

    F1  signed_share: order-flow imbalance signed_volume_1h / volume_1h, added to reversal.
        Question: does recent net taker pressure predict continuation of dmid?
    F2a activity: log1p(n_trades_1h), trades_truncated, and log_n x chg_1h (reversal interaction).
    F2b activity: log1p(volume_1h), trades_truncated, and log_vol x chg_1h (reversal interaction).
    F3  staleness: log1p(time_since_last_trade_s), its missing flag, and log_tsl x chg_1h.
    F4  max_trade_size: log1p(max_trade_size_1h) and max_trade_size_1h / volume_1h.

Each is added to a reversal ridge (chg_1h plus the family's columns) and compared (paired
Delta R2 = R2(variant) - R2(base) against the no-change forecast, B0) with two bases: the FROZEN
reversal ``-0.331610 * chg_1h`` (E002 spec) and a development-fitted ridge on chg_1h alone, so the
add-one contrast isolates the features rather than the estimator. Predictions are cross-fitted by
event (deterministic hash folds; the held-out events never enter fitting or lambda choice).

Pairing (E001 panel semantics, ``panel.build_pair``): origin = the trade sample's source snapshot,
target = the next complete snapshot by start time; eligibility and every feature come from the
origin row (plus the target's scheduled start), the target defines dmid and target-availability
only. Flow features are the sample's origin-time features (trades strictly before the origin row's
received_utc). Missing flow data is dropped and counted, never imputed.

Estimates: population-weighted (weight 1/inclusion probability) and unweighted, event-clustered
bootstrap (1000, seed 116) reusing ``evaluate.clustered_bootstrap_r2``. Models are fitted
unweighted. Pooling samples weights each by its own 1/p, so larger frames weigh more; with one or
two sample periods every result is exploratory and sign consistency across periods is
uninformative. Power uses ``power.mde_delta_r2`` with ``sd_c`` backed out of the bootstrap CI and a
Bonferroni correction over the family size.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluate, features, forecast, models, panel, power

SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
SAMPLE_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "trade_samples"
OUT_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "flow_screen"
LABEL = "DEVELOPMENT flow screen"
FROZEN_COEF = -0.331610
N_FOLDS = 5
MIN_PAIRS = 50
MIN_EVENTS = 10
ORIGIN_TOL_S = 1.0
FLOW_COLS = (
    "log_n_trades_1h",
    "log_volume_1h",
    "signed_share",
    "log_max_trade_1h",
    "max_share",
    "log_tsl",
    "tsl_missing",
    "trades_truncated",
    "logn_x_chg1h",
    "logvol_x_chg1h",
    "logtsl_x_chg1h",
)
FAMILY: dict[str, dict] = {
    "F1_signed_share": {
        "question": "net taker pressure -> continuation",
        "features": ("signed_share",),
    },
    "F2a_activity_trades": {
        "question": "trade count, alone and moderating reversal",
        "features": ("log_n_trades_1h", "trades_truncated", "logn_x_chg1h"),
    },
    "F2b_activity_volume": {
        "question": "traded volume, alone and moderating reversal",
        "features": ("log_volume_1h", "trades_truncated", "logvol_x_chg1h"),
    },
    "F3_staleness": {
        "question": "time since last trade moderating reversal",
        "features": ("log_tsl", "tsl_missing", "logtsl_x_chg1h"),
    },
    "F4_max_trade": {
        "question": "largest trade, absolute and relative to volume",
        "features": ("log_max_trade_1h", "max_share"),
    },
}
RIDGE_BASE = ("chg_1h",)


def assert_origin_only(names) -> None:
    """Refuse any target-side column in a feature list."""
    bad = set(names) & features.LABEL_COLUMNS
    if bad:
        raise ValueError(f"target-side columns refused as features: {sorted(bad)}")


for _v in FAMILY.values():
    assert_origin_only(_v["features"])
    assert set(_v["features"]) <= set(FLOW_COLS)


# --- loading and pairing ----------------------------------------------------------------------


def list_samples(root: Path = SAMPLE_ROOT) -> list[Path]:
    out = []
    for m in sorted(Path(root).glob("*/manifest.json")):
        if json.loads(m.read_text()).get("state") == "complete":
            out.append(m.parent)
    return out


def next_complete_capture(captures: list[dict], source_id: str) -> dict | None:
    """First complete capture starting strictly after ``source_id`` (``captures`` ordered)."""
    ids = [c["capture_id"] for c in captures]
    if source_id not in ids:
        return None
    k = ids.index(source_id)
    return captures[k + 1] if k + 1 < len(captures) else None


def flow_columns(f: pd.DataFrame) -> pd.DataFrame:
    """Origin-time flow features from a trade sample's ``features.csv.gz`` (status ok only)."""
    f = f[f["status"] == "ok"]
    vol = f["volume_1h"].to_numpy(float)
    pos = vol > 0
    safe = np.where(pos, vol, 1.0)
    tsl = f["time_since_last_trade_s"].to_numpy(float)
    miss = np.isnan(tsl)
    mx = f["max_trade_size_1h"].to_numpy(float)
    out = pd.DataFrame({"market_id": f["market_id"].astype(str).to_numpy()})
    out["log_n_trades_1h"] = np.log1p(f["n_trades_1h"].to_numpy(float))
    out["log_volume_1h"] = np.log1p(vol)
    out["signed_share"] = np.where(pos, f["signed_volume_1h"].to_numpy(float) / safe, 0.0)
    out["log_max_trade_1h"] = np.log1p(mx)
    out["max_share"] = np.where(pos, mx / safe, 0.0)
    out["log_tsl"] = np.where(miss, 0.0, np.log1p(np.where(miss, 0.0, tsl)))
    out["tsl_missing"] = miss.astype(float)
    out["trades_truncated"] = f["trades_truncated"].astype(str).str.lower().eq("true").astype(float)
    out["origin_utc"] = f["origin_utc"].to_numpy()
    return out


PAIR_CACHE_VERSION = 1


def _file_sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pair_cache_path(sample_dir: Path, captures: list[dict]) -> Path | None:
    """Cache file for one sample's pairs, named by a hash of the inputs that stay on the host after
    rotation (manifests, plan); None if the sample has no target snapshot yet."""
    sample_dir = Path(sample_dir)
    man = json.loads((sample_dir / "manifest.json").read_text())
    nxt = next_complete_capture(captures, man["snapshot_id"])
    src = next((c for c in captures if c["capture_id"] == man["snapshot_id"]), None)
    if nxt is None or src is None:
        return None
    key = "|".join([
        str(PAIR_CACHE_VERSION), man["sample_id"], _file_sha(sample_dir / "manifest.json"),
        _file_sha(sample_dir / "plan.json"), src["capture_id"],
        _file_sha(Path(src["dir"]) / "manifest.json"), nxt["capture_id"],
        _file_sha(Path(nxt["dir"]) / "manifest.json"),
    ])
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return sample_dir.parent.parent / "pair_cache" / f"{man['sample_id']}__{h}.pkl"


def build_sample_pairs(
    sample_dir: Path, captures: list[dict], period: int
) -> tuple[pd.DataFrame | None, dict]:
    """Pairs (market, source snapshot -> next complete snapshot) for one trade sample.

    While the raw inputs are on disk this computes exactly as before and also stores the result in
    ``pair_cache/`` (write-only side effect). If the nightly rotation removed the raw files after
    archiving them, the stored frame is returned instead (pickle, ``period`` re-stamped); with no
    cache it raises ``forecast.ArchivedDataError`` rather than silently skipping the sample."""
    sample_dir = Path(sample_dir)
    cp = pair_cache_path(sample_dir, captures)
    if cp is None:
        return _compute_sample_pairs(sample_dir, captures, period)
    man = json.loads((sample_dir / "manifest.json").read_text())
    src = next(c for c in captures if c["capture_id"] == man["snapshot_id"])
    nxt = next_complete_capture(captures, man["snapshot_id"])
    inputs = [Path(src["dir"]) / "rows.csv.gz", Path(nxt["dir"]) / "rows.csv.gz",
              sample_dir / "features.csv.gz"]
    if all(p.exists() for p in inputs):
        pairs, cnt = _compute_sample_pairs(sample_dir, captures, period)
        if pairs is not None and not cp.exists():
            try:
                cp.parent.mkdir(parents=True, exist_ok=True)
                tmp = cp.with_suffix(f".tmp{os.getpid()}")
                with open(tmp, "wb") as fh:
                    pickle.dump((pairs, cnt), fh, protocol=4)
                tmp.replace(cp)
            except OSError:
                pass  # optimisation for archived data; never fail a scoring pass over it
        return pairs, cnt
    if not cp.exists():
        forecast.require_local(next(p for p in inputs if not p.exists()))
    with open(cp, "rb") as fh:
        pairs, cnt = pickle.load(fh)
    pairs = pairs.copy()
    pairs["period"] = period
    cnt = dict(cnt)
    cnt["period"] = period
    return pairs, cnt


def pair_cache_status(sample_root: Path = SAMPLE_ROOT, snapshot_root: Path = SNAPSHOT_ROOT) -> dict:
    """Samples with a target snapshot vs cache files (all must be cached before raw files go)."""
    captures = forecast.list_complete_captures(snapshot_root)
    need = have = spans = n_samples = 0
    for sd in list_samples(sample_root):
        n_samples += 1
        sid = json.loads((sd / "manifest.json").read_text())["sample_id"]
        spans += int((sd.parent.parent / "pair_cache" / f"{sid}__sent_span.json").exists())
        cp = pair_cache_path(sd, captures)
        if cp is not None:
            need += 1
            have += int(cp.exists())
    return {"samples_with_target": need, "cached": have, "complete_samples": n_samples,
            "sent_spans_cached": spans, "complete": need == have and n_samples == spans}


def _compute_sample_pairs(
    sample_dir: Path, captures: list[dict], period: int
) -> tuple[pd.DataFrame | None, dict]:
    sample_dir = Path(sample_dir)
    man = json.loads((sample_dir / "manifest.json").read_text())
    plan = json.loads((sample_dir / "plan.json").read_text())
    cnt: dict = {"sample_id": man["sample_id"], "period": period,
                 "source_snapshot": man["snapshot_id"], "frame": plan.get("frame", "eligible")}
    nxt = next_complete_capture(captures, man["snapshot_id"])
    if nxt is None:
        cnt["skipped"] = "no subsequent complete snapshot"
        return None, cnt
    src = next(c for c in captures if c["capture_id"] == man["snapshot_id"])
    cnt["target_snapshot"] = nxt["capture_id"]
    wmap = {str(s["market_id"]): 1.0 / float(s["inclusion_float"]) for s in plan["sample"]}
    cnt["sampled"] = len(wmap)
    ids = forecast.ID_DTYPES
    snap_i = pd.read_csv(Path(src["dir"]) / "rows.csv.gz", dtype=ids)
    snap_j = pd.read_csv(Path(nxt["dir"]) / "rows.csv.gz", dtype=ids)
    snap_i = snap_i[snap_i["market_id"].isin(wmap)].drop_duplicates("market_id")
    snap_j = snap_j[snap_j["market_id"].isin(wmap)].drop_duplicates("market_id")
    cnt["sampled_in_source_snapshot"] = len(snap_i)
    j_sched = panel._epoch(pd.Series([nxt["started_utc"]]))[0]
    pairs, pc = panel.build_pair(snap_i, snap_j, j_sched, period)
    cnt.update({k: pc[k] for k in ("eligible", "target_available", "target_unavailable")})
    pairs = pairs[pairs["dmid"].notna()]
    flow = flow_columns(pd.read_csv(sample_dir / "features.csv.gz", dtype={"market_id": str}))
    cnt["flow_rows_ok"] = len(flow)
    pairs = pairs.merge(flow, on="market_id", how="inner")
    cnt["after_flow_merge"] = len(pairs)
    t_flow = panel._epoch(pairs["origin_utc"])
    bad = np.abs(t_flow - pairs["t_i"].to_numpy(float)) > ORIGIN_TOL_S
    cnt["dropped_origin_time_mismatch"] = int(bad.sum())
    pairs = pairs[~bad].drop(columns=["origin_utc"]).reset_index(drop=True)
    pairs["w"] = pairs["market_id"].map(wmap).to_numpy(float)
    c1 = pairs["chg_1h"].to_numpy(float)
    pairs["logn_x_chg1h"] = pairs["log_n_trades_1h"].to_numpy() * c1
    pairs["logvol_x_chg1h"] = pairs["log_volume_1h"].to_numpy() * c1
    pairs["logtsl_x_chg1h"] = pairs["log_tsl"].to_numpy() * c1
    pairs["sample_id"] = man["sample_id"]
    cnt["pairs"] = len(pairs)
    return pairs, cnt


def build_all(
    sample_root: Path = SAMPLE_ROOT, snapshot_root: Path = SNAPSHOT_ROOT
) -> tuple[pd.DataFrame, list[dict]]:
    captures = forecast.list_complete_captures(snapshot_root)
    frames, counts = [], []
    for k, sd in enumerate(list_samples(sample_root)):
        pairs, c = build_sample_pairs(sd, captures, k)
        counts.append(c)
        if pairs is not None and len(pairs):
            frames.append(pairs)
    if not frames:
        return pd.DataFrame(), counts
    return pd.concat(frames, ignore_index=True), counts


# --- cross-fitting ----------------------------------------------------------------------------


def event_keys(pairs: pd.DataFrame) -> np.ndarray:
    ev = pairs["event_id"]
    bad = ev.isna() | ev.astype(str).isin(["", "nan"])
    return np.where(bad, "m:" + pairs["market_id"].astype(str), ev.astype(str)).astype(object)


def _bucket(keys: np.ndarray, mod: int, tag: str) -> np.ndarray:
    return np.array([zlib.crc32(f"{tag}|{k}".encode()) % mod for k in keys])


def crossfit_ridge(
    pairs: pd.DataFrame, cols: tuple[str, ...], seed: int = evaluate.BOOT_SEED
) -> np.ndarray:
    """Out-of-fold ridge predictions; folds by event hash, lambda by an inner event split."""
    assert_origin_only(cols)
    keys = event_keys(pairs)
    fold = _bucket(keys, N_FOLDS, f"outer{seed}")
    inner = _bucket(keys, 4, f"inner{seed}") == 0
    X = pairs[list(cols)].to_numpy(float)
    y = pairs["dmid"].to_numpy(float)
    out = np.full(len(pairs), np.nan)
    for f in range(N_FOLDS):
        te = fold == f
        tr = ~te
        if te.sum() == 0:
            continue
        fit, val = tr & ~inner, tr & inner
        if fit.sum() < MIN_PAIRS or val.sum() < MIN_PAIRS:
            lam = models.LAMBDA_GRID[2]
        else:
            lam = models.choose_lambda(X[fit], y[fit], X[val], y[val])
        out[te] = models.Ridge(lam).fit(X[tr], y[tr]).predict(X[te])
    return out


# --- contrasts --------------------------------------------------------------------------------


def delta_r2(y: np.ndarray, yb: np.ndarray, yv: np.ndarray, w: np.ndarray) -> float:
    den = float(np.sum(w * y**2))
    return float(np.sum(w * ((y - yb) ** 2 - (y - yv) ** 2)) / den) if den > 0 else float("nan")


def contrast(
    pairs: pd.DataFrame, yb: np.ndarray, yv: np.ndarray, n_boot: int, seed: int, n_tests: int
) -> dict:
    """Paired Delta R2 (variant minus base, vs B0), weighted and unweighted, with event CIs.

    The clustered CI reuses ``evaluate.clustered_bootstrap_r2`` with per-row
    sse_m' = sse_var - sse_base + sse_0, so 1 - sum(m')/sum(sse_0) = Delta R2.
    """
    y = pairs["dmid"].to_numpy(float)
    keys = event_keys(pairs)
    per = pairs["period"].to_numpy()
    k_events = int(len(set(keys)))
    sse0, sb, sv = y**2, (y - yb) ** 2, (y - yv) ** 2
    out: dict = {"n_events": k_events}
    for mode, w in (("weighted", pairs["w"].to_numpy(float)), ("unweighted", np.ones(len(y)))):
        d = delta_r2(y, yb, yv, w)
        lo, hi = evaluate.clustered_bootstrap_r2(keys, w * (sv - sb + sse0), w * sse0, n_boot, seed)
        block = {
            "delta_r2": d,
            "ci_lo": lo,
            "ci_hi": hi,
            "per_period": {
                int(p): delta_r2(y[per == p], yb[per == p], yv[per == p], w[per == p])
                for p in sorted(set(per))
            },
        }
        if k_events >= 2 and np.isfinite(lo) and np.isfinite(hi):
            sd_c = power.sd_from_ci(lo, hi, k_events)
            block["sd_c"] = sd_c
            block["mde"] = power.mde_delta_r2(k_events, sd_c, n_tests=n_tests)
        out[mode] = block
    return out


def run_screen(pairs: pd.DataFrame, n_boot: int = evaluate.BOOT_N,
               seed: int = evaluate.BOOT_SEED) -> dict:
    """Run every family member against both bases (all reported)."""
    y = pairs["dmid"].to_numpy(float)
    w = pairs["w"].to_numpy(float)
    frozen = FROZEN_COEF * pairs["chg_1h"].to_numpy(float)
    ridge_base = crossfit_ridge(pairs, RIDGE_BASE, seed)
    n_tests = len(FAMILY)
    res: dict = {
        "label": LABEL,
        "status": "DEVELOPMENT screening - not evidence",
        "no_edge_claim": True,
        "effective_sample": effective_sample(pairs),
        "base_r2_vs_B0": {
            "frozen": {"weighted": 1 - float(np.sum(w * (y - frozen) ** 2) / np.sum(w * y**2)),
                       "unweighted": 1 - float(np.sum((y - frozen) ** 2) / np.sum(y**2))},
            "ridge_chg_1h": {
                "weighted": 1 - float(np.sum(w * (y - ridge_base) ** 2) / np.sum(w * y**2)),
                "unweighted": 1 - float(np.sum((y - ridge_base) ** 2) / np.sum(y**2)),
            },
        },
        "n_tests_for_mde": n_tests,
        "variants": {},
    }
    for name, spec in FAMILY.items():
        cols = (*RIDGE_BASE, *spec["features"])
        yv = crossfit_ridge(pairs, cols, seed)
        res["variants"][name] = {
            "question": spec["question"],
            "features": list(spec["features"]),
            "vs_frozen": contrast(pairs, frozen, yv, n_boot, seed, n_tests),
            "vs_ridge": contrast(pairs, ridge_base, yv, n_boot, seed, n_tests),
        }
    return res


def effective_sample(pairs: pd.DataFrame) -> dict:
    keys = event_keys(pairs)
    return {
        "pairs": int(len(pairs)),
        "markets": int(pairs["market_id"].nunique()),
        "events": int(len(set(keys))),
        "sample_periods": int(pairs["period"].nunique()),
        "median_horizon_h": float(pairs["horizon_h"].median()),
        "share_zero_dmid": float((pairs["dmid"] == 0).mean()),
        "sum_weights": float(pairs["w"].sum()),
        "per_period": [
            {"period": int(p), "sample_id": str(g["sample_id"].iloc[0]), "pairs": int(len(g)),
             "markets": int(g["market_id"].nunique()),
             "events": int(len(set(event_keys(g))))}
            for p, g in pairs.groupby("period")
        ],
        "note": "1-2 sample periods: everything here is exploratory",
    }


def clean(o):
    """NaN/inf -> None so the JSON is strict."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    return o
