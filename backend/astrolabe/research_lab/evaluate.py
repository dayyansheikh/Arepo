"""E001 walk-forward evaluation with label-availability purge and clustered bootstrap."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .models import choose_lambda, fit_predict_all
from .panel import FEATURES_B2, FEATURES_B3

MODELS = ["B0", "B1", "B1h", "B2", "B3"]
BOOT_N = 1000
BOOT_SEED = 116
MIN_TRAIN = 500  # minimum training pairs (and per inner-split side) to fit
BIN_SECONDS = 60.0  # test rows grouped by origin-time bin; purge uses the bin's earliest t_i
MOVER = 0.01


def rank_average(x: np.ndarray) -> np.ndarray:
    return pd.Series(x).rank(method="average").to_numpy()


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation (Pearson on average ranks); NaN if either side is constant."""
    if len(a) < 3:
        return float("nan")
    ra, rb = rank_average(a), rank_average(b)
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def r2_oos(sse_model: float, sse_b0: float) -> float:
    return float("nan") if sse_b0 <= 0 else 1.0 - sse_model / sse_b0


def purged_train_mask(t_j: np.ndarray, test_t_i_min: float) -> np.ndarray:
    """Train pairs are usable only if their label was known by the earliest test origin time."""
    return t_j <= test_t_i_min


def clustered_bootstrap_r2(
    cluster: np.ndarray,
    sse_m: np.ndarray,
    sse_0: np.ndarray,
    n: int = BOOT_N,
    seed: int = BOOT_SEED,
) -> tuple[float, float]:
    """Market-clustered bootstrap 95% CI for R2_oos = 1 - SSE_m/SSE_0 (resample clusters)."""
    codes, uniq = pd.factorize(cluster)
    k = len(uniq)
    cm = np.bincount(codes, weights=sse_m, minlength=k)
    c0 = np.bincount(codes, weights=sse_0, minlength=k)
    rng = np.random.default_rng(seed)
    vals = np.empty(n)
    for b in range(n):
        idx = rng.integers(0, k, size=k)
        s0 = c0[idx].sum()
        vals[b] = 1.0 - cm[idx].sum() / s0 if s0 > 0 else np.nan
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def _matrix(df: pd.DataFrame) -> dict:
    return {
        "y": df["dmid"].to_numpy(float),
        "chg_1d": df["chg_1d"].to_numpy(float),
        "chg_1h": df["chg_1h"].to_numpy(float),
        "X2": df[FEATURES_B2].to_numpy(float),
        "X3": df[FEATURES_B3].to_numpy(float),
    }


def _slice(m: dict, mask: np.ndarray) -> dict:
    return {k: v[mask] for k, v in m.items()}


def select_lambdas(period: np.ndarray, t_i: np.ndarray, m: dict) -> tuple[float, float, str]:
    """Inner split: fit on earlier periods, validate on the last training period.

    Fallback when that split leaves < MIN_TRAIN on a side (e.g. a single training period):
    validate on the latest 25% of training pairs by origin time.
    """
    last = period.max()
    fit_m, val_m = period < last, period == last
    how = "last_period"
    if fit_m.sum() < MIN_TRAIN or val_m.sum() < MIN_TRAIN:
        order = np.argsort(t_i)
        cut = int(len(order) * 0.75)
        fit_m = np.zeros(len(period), bool)
        fit_m[order[:cut]] = True
        val_m = ~fit_m
        how = "time_tail_25pct"
    f, v = _slice(m, fit_m), _slice(m, val_m)
    return (
        choose_lambda(f["X2"], f["y"], v["X2"], v["y"]),
        choose_lambda(f["X3"], f["y"], v["X3"], v["y"]),
        how,
    )


def walk_forward(pairs: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return a frame of test predictions (one column per model) and fit diagnostics."""
    pairs = pairs.reset_index(drop=True)
    m_all = _matrix(pairs)
    t_j = pairs["t_j"].to_numpy(float)
    t_i_all = pairs["t_i"].to_numpy(float)
    per_all = pairs["period"].to_numpy()
    periods = sorted(pairs["period"].unique())
    frames = []
    diag: dict = {"lambda_choice": [], "excluded_insufficient_train": {}}
    for p in periods[1:]:  # needs >= 1 prior training period
        te_idx = np.flatnonzero(per_all == p)
        binid = np.floor(t_i_all[te_idx] / BIN_SECONDS)
        for b in np.unique(binid):
            sel = te_idx[binid == b]
            trm = purged_train_mask(t_j, float(t_i_all[sel].min())) & (per_all < p)
            if trm.sum() < MIN_TRAIN:
                diag["excluded_insufficient_train"][int(p)] = diag[
                    "excluded_insufficient_train"
                ].get(int(p), 0) + len(sel)
                continue
            l2, l3, how = select_lambdas(per_all[trm], t_i_all[trm], _slice(m_all, trm))
            diag["lambda_choice"].append(
                {
                    "period": int(p),
                    "bin": int(b),
                    "n_train": int(trm.sum()),
                    "lam_B2": l2,
                    "lam_B3": l3,
                    "inner": how,
                }
            )
            tmask = np.zeros(len(pairs), bool)
            tmask[sel] = True
            preds = fit_predict_all(_slice(m_all, trm), _slice(m_all, tmask), l2, l3)
            f = pairs.loc[
                sel, ["market_id", "event_id", "period", "t_i", "dmid", "horizon_h"]
            ].copy()
            for k, v in preds.items():
                f[k] = v
            frames.append(f)
    return pd.concat(frames, ignore_index=True), diag


def label_for(per_period: list[dict], pooled_r2: float) -> str:
    """Pre-registered interpretation rule (strict majority of test periods)."""
    n = len(per_period)
    if n < 3:
        return "Inconclusive"
    maj = n // 2 + 1
    n_ci_pos = sum(1 for d in per_period if d["ci_lo"] > 0)
    n_nonpos = sum(1 for d in per_period if not (d["r2_oos"] > 0))
    if pooled_r2 > 0 and n_ci_pos >= maj:
        return "Indicative (exploratory)"
    if n_nonpos >= maj:
        return "Negative"
    return "Inconclusive"


def dir_acc(yh: np.ndarray, y: np.ndarray, sel: np.ndarray) -> tuple[float, float]:
    """(accuracy among movers with a non-zero prediction, accuracy counting zeros as wrong)."""
    if not sel.any():
        return float("nan"), float("nan")
    hit = np.sign(yh[sel]) == np.sign(y[sel])
    nz = yh[sel] != 0
    return (float(hit[nz].mean()) if nz.any() else float("nan")), float(hit.mean())


def summarise(preds: pd.DataFrame) -> dict:
    """Per model: pooled and per-period R2_oos (+CI), Spearman, directional accuracy, MAE."""
    y = preds["dmid"].to_numpy(float)
    res: dict = {}
    sse0_all = y**2
    nan2 = (float("nan"), float("nan"))
    mover = np.abs(y) >= MOVER
    for mdl in MODELS:
        yh = preds[mdl].to_numpy(float)
        sse_all = (y - yh) ** 2
        pooled = r2_oos(sse_all.sum(), sse0_all.sum())
        dir_pooled, dir_pooled_all = dir_acc(yh, y, mover)
        per = []
        for p in sorted(preds["period"].unique()):
            mk = (preds["period"] == p).to_numpy()
            lo, hi = (
                clustered_bootstrap_r2(
                    preds["market_id"].to_numpy()[mk], sse_all[mk], sse0_all[mk], seed=BOOT_SEED
                )
                if mdl != "B0"
                else nan2
            )
            mv = mk & mover
            d_nz, d_all = dir_acc(yh, y, mv)
            per.append(
                {
                    "period": int(p),
                    "n": int(mk.sum()),
                    "n_markets": int(preds.loc[mk, "market_id"].nunique()),
                    "r2_oos": r2_oos(sse_all[mk].sum(), sse0_all[mk].sum()),
                    "ci_lo": lo,
                    "ci_hi": hi,
                    "spearman": spearman(yh[mk], y[mk]) if mdl != "B0" else float("nan"),
                    "dir_acc": d_nz,
                    "dir_acc_zero_wrong": d_all,
                    "n_movers_directional": int((mv & (yh != 0)).sum()),
                    "n_movers": int(mv.sum()),
                    "mae": float(np.abs(y[mk] - yh[mk]).mean()),
                }
            )
        pooled_ci = (
            clustered_bootstrap_r2(preds["market_id"].to_numpy(), sse_all, sse0_all)
            if mdl != "B0"
            else nan2
        )
        res[mdl] = {
            "pooled_r2_oos": pooled,
            "pooled_ci": list(pooled_ci),
            "pooled_dir_acc": dir_pooled,
            "pooled_dir_acc_zero_wrong": dir_pooled_all,
            "pooled_mae": float(np.abs(y - yh).mean()),
            "per_period": per,
            "label": "baseline" if mdl == "B0" else label_for(per, pooled),
        }
    return res


def effective_sample(panel: pd.DataFrame, preds: pd.DataFrame) -> dict:
    avail = panel[panel["dmid"].notna()]
    return {
        "pairs_target_available": int(len(avail)),
        "distinct_markets_all_pairs": int(avail["market_id"].nunique()),
        "distinct_events_all_pairs": int(avail["event_id"].nunique()),
        "test_pairs": int(len(preds)),
        "test_distinct_markets": int(preds["market_id"].nunique()),
        "test_distinct_events": int(preds["event_id"].nunique()),
        "n_test_periods": int(preds["period"].nunique()),
        "per_period": [
            {
                "period": int(p),
                "pairs": int(len(g)),
                "markets": int(g["market_id"].nunique()),
                "events": int(g["event_id"].nunique()),
                "median_horizon_h": float(g["horizon_h"].median()),
            }
            for p, g in preds.groupby("period")
        ],
    }


def ols_origin_slope(x: np.ndarray, y: np.ndarray) -> float:
    """Slope of OLS through the origin, sum(xy)/sum(xx); NaN if x is all zero."""
    d = float(np.dot(x, x))
    return float(np.dot(x, y) / d) if d > 0 else float("nan")


def clustered_bootstrap_slope(
    cluster: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    n: int = BOOT_N,
    seed: int = BOOT_SEED,
) -> tuple[float, float]:
    """Market-clustered bootstrap 95% CI for the through-origin OLS slope of y on x."""
    codes, uniq = pd.factorize(cluster)
    k = len(uniq)
    cxy = np.bincount(codes, weights=x * y, minlength=k)
    cxx = np.bincount(codes, weights=x * x, minlength=k)
    rng = np.random.default_rng(seed)
    vals = np.empty(n)
    for b in range(n):
        idx = rng.integers(0, k, size=k)
        d = cxx[idx].sum()
        vals[b] = cxy[idx].sum() / d if d > 0 else np.nan
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)
