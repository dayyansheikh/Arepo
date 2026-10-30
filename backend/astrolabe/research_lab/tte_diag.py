"""J8 C-TTE descriptive diagnostics (q0100). NOT counted tests; no verdict or gate changes.

The frozen C-TTE contrast (``time_to_resolution``: "<24h" minus ">30d") is built from
``ml_log_hours_to_end``, which comes from the Gamma ``endDate`` fetched AFTER the fact, clipped at
0 hours (so post-end, pre-resolution origins land in the "<24h" bin). This module re-reads the same
frozen out-of-fold per-row ``delta`` (baseline loss minus full loss) under declared alternative
row sets and clusterings. Nothing is refitted and no cut is re-estimated.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from astrolabe.research_lab import ml_explain as mx

# Declared BEFORE the first run (challenger 2026-10-16): a market is "end ~ close" when its Gamma
# endDate is within this many seconds of its closedTime (either side).
NEAR_END_TOL_S = 3600.0
# Same definition as run_ml_history.lookahead_markets: closed more than 24h before endDate.
LOOKAHEAD_S = 24 * 3600.0
REGIME = "time_to_resolution"
CONTRAST = "C-TTE"
LABEL = "descriptive_diagnostic_not_counted"


def _contrast(delta: np.ndarray, judge: np.ndarray, plus: np.ndarray, minus: np.ndarray,
              clusters: Mapping[str, np.ndarray], n_boot: int, seed: int) -> dict:
    """Contrast g(plus) - g(minus) on ``judge`` rows with a cluster bootstrap per clustering.
    ``hull`` combines only the co-primary clusterings (event, dep_group) exactly as the frozen
    test did; any other clustering (utc_day) is reported alongside, never combined."""
    d = np.where(judge, delta, np.nan)
    by = {n: mx._contrast_boot(d, np.asarray(cl), plus, minus, n_boot, seed)
          for n, cl in clusters.items()}
    out = {"n_rows": [int((judge & plus).sum()), int((judge & minus).sum())], "by_cluster": by,
           "hull_event_dep_group": mx._combine_contrast(
               {n: v for n, v in by.items() if n in mx.CO_PRIMARY_CLUSTERS}),
           "label": LABEL}
    out["n_clusters_plus_minus"] = {
        n: [int(pd.Series(np.asarray(cl)[judge & m]).nunique()) for m in (plus, minus)]
        for n, cl in clusters.items()}
    return out


def market_flags(frame: pd.DataFrame) -> pd.DataFrame:
    """Per-market ``lookahead`` (closed > 24h before endDate) and ``near_end`` (|end - close| <=
    NEAR_END_TOL_S). Missing end or close epoch is never flagged (and is counted by the caller)."""
    f = frame[["market_id", "end_epoch", "close_epoch"]].drop_duplicates("market_id").copy()
    f["market_id"] = f["market_id"].astype(str)
    e, c = f["end_epoch"].astype(float), f["close_epoch"].astype(float)
    both = e.notna() & c.notna()
    f["lookahead"] = both & (c < e - LOOKAHEAD_S)
    f["near_end"] = both & ((c - e).abs() <= NEAR_END_TOL_S)
    return f.set_index("market_id")


def tte_diagnostics(
    lab: pd.DataFrame,
    delta: np.ndarray,
    clusters: Mapping[str, np.ndarray],
    frame: pd.DataFrame,
    cuts: Mapping[str, Sequence[float]] | None = None,
    *,
    n_boot: int = 1000,
    seed: int = mx.SEED,
) -> dict:
    """Descriptive C-TTE diagnostics. ``lab`` needs market_id, t_i, ml_log_hours_to_end;
    ``delta`` is the frozen per-row LL_baseline - LL_full (NaN outside the test blocks);
    ``clusters`` the event / dep_group vectors (a UTC-day clustering is added here from t_i)."""
    delta = np.asarray(delta, float)
    judge = np.isfinite(delta)
    spec = next(s for s in mx.HISTORY_REGIMES if s.name == REGIME)
    regime = mx.assign_regime(spec, lab[spec.column], (cuts or {}).get(REGIME)).to_numpy()
    plus, minus = np.isin(regime, ["<24h"]), np.isin(regime, [">30d"])

    fl = market_flags(frame)
    mk = lab["market_id"].astype(str)
    ep = fl.reindex(mk.to_numpy())
    end = ep["end_epoch"].astype(float).to_numpy()
    t_i = lab["t_i"].astype(float).to_numpy()
    lookahead = ep["lookahead"].fillna(False).astype(bool).to_numpy()
    near_end = ep["near_end"].fillna(False).astype(bool).to_numpy()
    post_end = np.isfinite(end) & (t_i > end)
    pre_end = np.isfinite(end) & ~post_end

    # consistency of the frame's endDate with the panel feature (clip at 0 reproduces the bin)
    with np.errstate(invalid="ignore"):
        rebuilt = np.log1p(np.clip((end - t_i) / 3600.0, 0, None))
    feat = lab["ml_log_hours_to_end"].astype(float).to_numpy()
    both = np.isfinite(rebuilt) & np.isfinite(feat)
    mismatch = int((both & (np.abs(rebuilt - feat) > 1e-6)).sum())

    cl = dict(clusters)
    cl["utc_day"] = np.floor(t_i / 86400.0).astype(np.int64)

    def run(excl: np.ndarray | None = None, plus_only: np.ndarray | None = None) -> dict:
        j = judge if excl is None else judge & ~excl
        p = plus if plus_only is None else plus & plus_only
        return _contrast(delta, j, p, minus, cl, n_boot, seed)

    lt = plus & judge
    split = {}
    for nm, m in (("pre_end", pre_end), ("post_end", post_end),
                  ("end_unknown", ~np.isfinite(end))):
        sel = lt & m
        split[nm] = {"n_rows": int(sel.sum()),
                     "n_markets": int(mk[sel].nunique()),
                     "mean_delta": float(delta[sel].mean()) if sel.any() else None}
    return {
        "label": LABEL,
        "note": "descriptive diagnostics of the frozen C-TTE contrast; not counted tests",
        "declared": {"near_end_tol_s": NEAR_END_TOL_S, "lookahead_s": LOOKAHEAD_S,
                     "regime": REGIME, "contrast": CONTRAST,
                     "post_end": "t_i > frame end_epoch (hours clipped at 0 in the feature)"},
        "end_epoch_vs_feature_mismatch_rows": mismatch,
        "markets": {"n": int(mk.nunique()),
                    "n_lookahead": int(mk[lookahead].nunique()),
                    "n_near_end": int(mk[near_end].nunique()),
                    "n_missing_end_or_close": int(
                        mk[~np.isfinite(end) | ep["close_epoch"].isna().to_numpy()].nunique())},
        "bin_lt24h_split": split,
        "contrasts": {
            "as_replicated": run(),
            "lookahead_excluded": run(excl=lookahead),
            "plus_pre_end_only": run(plus_only=pre_end),
            "plus_post_end_only": run(plus_only=post_end),
            "near_end_markets_excluded": run(excl=near_end),
        },
    }


def check_base_cols(frozen: Mapping, m0v: Sequence[str]) -> dict:
    """Confirm the frozen baseline is exactly M0V (order-sensitive and as a set)."""
    base = list(frozen.get("base_cols") or [])
    return {"base_cols_equal_m0v": base == list(m0v),
            "same_set": set(base) == set(m0v), "n_base_cols": len(base),
            "m0v_includes_ml_log_hours_to_end": "ml_log_hours_to_end" in m0v,
            "base_includes_ml_log_hours_to_end": "ml_log_hours_to_end" in base}
