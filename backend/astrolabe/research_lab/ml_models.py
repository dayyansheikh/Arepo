"""Multi-signal pipeline, Task 4: model-fitting harness (M0, M1, M2, M3), scoring and SHAP.

Design: ``docs/research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md`` (sections 3, 4, 7). It takes
``ml_panel`` rows plus the hashed fold manifest and returns **out-of-fold** class probabilities,
one row per test row, ordered (down, flat, up). Nothing here makes an edge, calibration or
profitability claim; every run is a development run.

Arms
----
* ``M0``  price + momentum multinomial logistic (a1 + a2 only), refitted per fold; only its
  temperature is fitted (inner split), so every arm is calibrated the same way.
* ``M1``  elastic-net multinomial logistic (scikit-learn, saga) on all tier-(a) features, natural
  spline expansion of ``logit(mid)``, ``chg_1h`` and ``log hours``, and the three pre-declared
  ``chg_1h`` interactions. Grid and temperature are tuned on the inner split only.
* ``M2``  LightGBM multiclass. 20-config seeded random search over ``LGB_SPACE``
  (``LGB_GRID``) with early stopping and temperature on the inner split only; the winner is
  refitted on the whole training fold with the early-stopping round count. Native NaN.
* ``M3``  Bayesian hierarchical multinomial logit (``M3_eb``), numpy + scipy, MAP via L-BFGS.
  N(0, 0.5^2) priors on standardised main effects. ``fee_category`` intercepts and the
  ``chg_1h`` / ``spread`` category slopes are **fixed effects** with N(0, 0.5^2) / N(0, 0.3^2)
  priors and sum-to-zero centring against the global terms (equivalent to fixing their SDs at the
  prior scale: with a dozen categories the SD is not identifiable, see amendment A1). **Event**
  intercepts are partially pooled: their SD is estimated by Laplace-EM (posterior variances from
  the diagonal Hessian, closed-form update under the half-normal(0, 0.5) prior, 5 fixed outer
  iterations). Unseen events and categories get the population value (zero effect). Temperature
  is fitted on the same inner split as every other arm. **Why not NumPyro/NUTS:** the design's M3
  (Task 5) needs jax (about 1 GB), MCMC diagnostics and a subsample; this is the lightest correct
  way to pool events over all rows, deterministically. Limits: a point estimate of the event SD,
  a diagonal (cross-class-ignoring) variance approximation, no posterior intervals.
  ``simulate_hierarchical_check`` reports recovery and coverage. It is named ``M3_eb`` in the
  logs so it is never confused with the NumPyro model.

Rules enforced here: tuning, early stopping and temperature use only training-fold rows (an
inner split of the last 25% of training periods with its own purge and embargo); test rows are
touched only by ``predict``. Every seed is fixed (116), LightGBM runs single-thread and
deterministic. SHAP is computed on out-of-fold test rows only and is labelled exploratory.
"""

from __future__ import annotations

import itertools
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize, minimize_scalar
from scipy.stats import spearmanr

from . import evaluate, features, ml_panel, power, provenance
from .compare import paired_bootstrap

SEED = 116
EPS = 1e-15
MAX_NULL_CLUSTER_FRACTION = 0.05
PROB_FLOOR = 1e-6
INNER_VAL_FRACTION = 0.25
N_CLASSES = 3
CLASS_NAMES = ("down", "flat", "up")

M0_FEATURES: tuple[str, ...] = (
    "ml_logit_mid", "ml_abs_mid_dev", "ml_chg_1h", "ml_chg_1d", "ml_chg_1w",
    "ml_chg_1h_missing", "ml_chg_1d_missing", "ml_chg_1w_missing",
)
SPLINE_FEATURES: tuple[str, ...] = ("ml_logit_mid", "ml_chg_1h", "ml_log_hours_to_end")
INTERACTION_PARTNERS: tuple[str, ...] = ("ml_spread", "ml_log1p_liq", "ml_log_hours_to_end")
BAYES_FEATURES: tuple[str, ...] = (
    "ml_logit_mid", "ml_abs_mid_dev", "ml_chg_1h", "ml_chg_1d", "ml_own_dmid_prev", "ml_own_vol",
    "ml_spread", "ml_log1p_liq", "ml_log1p_vol24", "ml_log_hours_to_end",
    "ml_quote_staleness_h", "ml_ltp_minus_mid",
)
BAYES_FLAG_FEATURES: tuple[str, ...] = ("ml_own_dmid_prev", "ml_own_vol")
BAYES_SLOPES: tuple[str, ...] = ("ml_chg_1h", "ml_spread")
CAT_SD_FIXED = 0.5  # category intercepts: fixed effects, N(0, 0.5^2), sum-to-zero (amendment A1)
SLOPE_SD_FIXED = 0.3  # category slopes: fixed effects, N(0, 0.3^2), sum-to-zero (amendment A1)

# Fixed search budgets, declared in code (design section 4: the budget is fixed and logged).
M1_GRID: tuple[dict, ...] = tuple(
    {"C": c, "l1_ratio": r} for c, r in itertools.product((0.01, 0.1, 1.0), (0.1, 0.5))
)
LGB_SPACE: dict[str, tuple] = {  # declared search space (design: 20-config random search)
    "num_leaves": (4, 7, 15, 31),
    "min_data_in_leaf": (20, 50, 100, 200, 400),
    "lambda_l2": (0.1, 1.0, 10.0, 30.0),
    "feature_fraction": (0.6, 0.8, 1.0),
}
LGB_N_CONFIGS = 20


def _sample_lgb_grid(seed: int = SEED, n: int = LGB_N_CONFIGS) -> tuple[dict, ...]:
    """20 distinct configs drawn without replacement with a fixed seed; identical on every run."""
    combos = list(itertools.product(*LGB_SPACE.values()))
    pick = np.random.default_rng(seed).choice(len(combos), size=n, replace=False)
    return tuple(dict(zip(LGB_SPACE, combos[i], strict=True)) for i in sorted(pick))


LGB_GRID: tuple[dict, ...] = _sample_lgb_grid()
LGB_MAX_ROUNDS = 300
LGB_EARLY_STOP = 20
LGB_LEARNING_RATE = 0.05

ARM_NAMES = ("M0", "M1", "M2", "M3_eb")
TEMP_SOURCE = (
    "fitted on inner-validation predictions of the model trained on the inner-train rows; "
    "applied unchanged to the model refitted on the whole training fold (rounds / config fixed)"
)
EXPLORATORY_NOTE = (
    "EXPLORATORY: out-of-fold SHAP on development folds. Descriptive only; never evidence of "
    "edge, causation or mechanism. Correlated features share credit arbitrarily; families are "
    "the unit of interpretation."
)


# ---------------------------------------------------------------------------------------------
# Small numerics
# ---------------------------------------------------------------------------------------------


def _xmat(df: pd.DataFrame, cols: tuple[str, ...] | list[str]) -> np.ndarray:
    x = df[list(cols)].to_numpy(float)
    return np.where(np.isfinite(x), x, np.nan)


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _finalise(p: np.ndarray) -> np.ndarray:
    """Floor and renormalise so no class has probability zero (a log loss of infinity)."""
    p = np.clip(np.asarray(p, float), PROB_FLOOR, None)
    return p / p.sum(axis=1, keepdims=True)


def _expand_classes(classes: np.ndarray, p: np.ndarray) -> np.ndarray:
    out = np.zeros((p.shape[0], N_CLASSES))
    out[:, np.asarray(classes, int)] = p
    return out


def log_loss_rows(proba: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per-row multiclass log loss ``-log p[y]``."""
    p = np.asarray(proba, float)
    idx = np.asarray(y, int)
    return -np.log(np.clip(p[np.arange(len(idx)), idx], EPS, 1.0))


def brier_rows(proba: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Per-row 3-class Brier score ``sum_k (p_k - 1[y = k])^2``."""
    p = np.asarray(proba, float)
    onehot = np.eye(N_CLASSES)[np.asarray(y, int)]
    return ((p - onehot) ** 2).sum(axis=1)


def fit_temperature(proba: np.ndarray, y: np.ndarray) -> float:
    """Temperature T > 0 minimising log loss of ``softmax(log p / T)`` (T = 1 is identity)."""
    lp = np.log(np.clip(proba, EPS, 1.0))
    yi = np.asarray(y, int)

    def f(t: float) -> float:
        return float(log_loss_rows(_softmax(lp / t), yi).mean())

    res = minimize_scalar(f, bounds=(0.25, 4.0), method="bounded", options={"xatol": 1e-4})
    return float(res.x)


def apply_temperature(proba: np.ndarray, t: float) -> np.ndarray:
    return _finalise(_softmax(np.log(np.clip(proba, EPS, 1.0)) / t))


class _Prep:
    """Median imputation, winsorising and standardising, all fitted on training rows."""

    def __init__(self, cols: tuple[str, ...], winsor: tuple[float, float] = (0.01, 0.99)):
        self.cols, self.winsor = tuple(cols), winsor

    def fit(self, x: np.ndarray) -> _Prep:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN columns
            self.med = np.nan_to_num(np.nanmedian(x, axis=0), nan=0.0)
            lo, hi = np.nanquantile(x, self.winsor[0], axis=0), np.nanquantile(
                x, self.winsor[1], axis=0
            )
        self.lo, self.hi = np.nan_to_num(lo, nan=0.0), np.nan_to_num(hi, nan=0.0)
        z = self._clip(x)
        self.mu = z.mean(axis=0)
        sd = z.std(axis=0)
        self.sd = np.where(sd > 1e-12, sd, 1.0)
        return self

    def _clip(self, x: np.ndarray) -> np.ndarray:
        z = np.where(np.isnan(x), self.med, x)
        return np.clip(z, self.lo, self.hi)

    def transform(self, x: np.ndarray) -> np.ndarray:
        return (self._clip(x) - self.mu) / self.sd


# ---------------------------------------------------------------------------------------------
# Inner split (tuning happens only here, inside the training fold)
# ---------------------------------------------------------------------------------------------


def inner_split(
    df: pd.DataFrame, train_pos: np.ndarray, embargo_s: float, fraction: float = INNER_VAL_FRACTION
) -> tuple[np.ndarray, np.ndarray]:
    """(inner_train_pos, inner_val_pos): the last ``fraction`` of training periods validate.

    The inner training rows are purged: their label time must be at most the earliest inner
    validation ``t0`` minus the embargo. All positions are subsets of ``train_pos``.
    """
    sub = df.iloc[train_pos]
    per = sub["period"].to_numpy()
    first_t0 = sub.groupby("period")["t0"].min().sort_values(kind="stable")
    order = list(first_t0.index)
    if len(order) < 2:
        raise ValueError("inner split needs at least 2 training periods")
    n_val = max(1, int(round(fraction * len(order))))
    val_periods = order[-n_val:]
    val_mask = np.isin(per, val_periods)
    cutoff = float(first_t0.loc[val_periods].min()) - embargo_s
    keep = evaluate.purged_train_mask(sub["t_j"].to_numpy(float), cutoff)
    inner_train = ~val_mask & keep
    if not inner_train.any() or not val_mask.any():
        raise ValueError("inner split is empty after purge")
    return train_pos[inner_train], train_pos[val_mask]


# ---------------------------------------------------------------------------------------------
# Fold fit results and arms
# ---------------------------------------------------------------------------------------------


@dataclass
class FoldFit:
    proba: np.ndarray  # (n_test, 3), ordered (down, flat, up)
    diag: dict = field(default_factory=dict)
    shap: dict | None = None


def _y(df: pd.DataFrame, pos: np.ndarray) -> np.ndarray:
    return df["y_class"].to_numpy(float)[pos].astype(int)


def _quiet_fit(model, x, y):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        model.fit(x, y)
    return any("onverge" in str(i.message) for i in w)


def _m0_model():
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(C=1e4, max_iter=500, random_state=SEED)


def fit_m0(df, train_pos, test_pos, inner, **_) -> FoldFit:
    """Price + momentum logistic. Like every other arm, its temperature is fitted on the inner
    validation block using a model trained on the inner-train rows, then applied to the model
    refitted on the whole training fold."""
    itr, iva = inner
    cols = M0_FEATURES
    prep_in = _Prep(cols).fit(_xmat(df.iloc[itr], cols))
    m_in = _m0_model()
    _quiet_fit(m_in, prep_in.transform(_xmat(df.iloc[itr], cols)), _y(df, itr))
    p_va = _finalise(
        _expand_classes(
            m_in.classes_, m_in.predict_proba(prep_in.transform(_xmat(df.iloc[iva], cols)))
        )
    )
    temp = fit_temperature(p_va, _y(df, iva))
    xtr, xte = _xmat(df.iloc[train_pos], cols), _xmat(df.iloc[test_pos], cols)
    prep = _Prep(cols).fit(xtr)
    m = _m0_model()
    nonconv = _quiet_fit(m, prep.transform(xtr), _y(df, train_pos))
    p = _expand_classes(m.classes_, m.predict_proba(prep.transform(xte)))
    return FoldFit(
        apply_temperature(_finalise(p), temp),
        {"config": {"C": 1e4}, "temperature": temp, "temperature_source": TEMP_SOURCE,
         "nonconverged": nonconv},
    )


class _M1Design:
    """Standardised tier-(a) block + natural-style spline basis + declared interactions."""

    def __init__(self, cols: tuple[str, ...]):
        self.cols = tuple(cols)

    def fit(self, x: np.ndarray) -> _M1Design:
        from sklearn.preprocessing import SplineTransformer

        self.prep = _Prep(self.cols).fit(x)
        z = self.prep.transform(x)
        self.si = [self.cols.index(c) for c in SPLINE_FEATURES]
        self.ii = [self.cols.index(c) for c in INTERACTION_PARTNERS]
        self.ci = self.cols.index("ml_chg_1h")
        self.spl = SplineTransformer(
            n_knots=5, degree=3, knots="uniform", extrapolation="constant"
        ).fit(z[:, self.si])
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        z = self.prep.transform(x)
        inter = z[:, [self.ci]] * z[:, self.ii]
        return np.hstack([z, self.spl.transform(z[:, self.si]), inter])


def _m1_model(cfg: dict):
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(
        C=cfg["C"], l1_ratio=cfg["l1_ratio"], solver="saga", max_iter=300, tol=1e-3,
        random_state=SEED,
    )


def fit_m1(df, train_pos, test_pos, inner, **_) -> FoldFit:
    cols = ml_panel.TIER_A_NAMES
    itr, iva = inner
    xtr_all = _xmat(df.iloc[train_pos], cols)
    design_in = _M1Design(cols).fit(_xmat(df.iloc[itr], cols))
    xin, xva = design_in.transform(_xmat(df.iloc[itr], cols)), design_in.transform(
        _xmat(df.iloc[iva], cols)
    )
    yin, yva = _y(df, itr), _y(df, iva)
    search, best = [], None
    for cfg in M1_GRID:
        m = _m1_model(cfg)
        nonconv = _quiet_fit(m, xin, yin)
        p = _finalise(_expand_classes(m.classes_, m.predict_proba(xva)))
        loss = float(log_loss_rows(p, yva).mean())
        search.append({"config": cfg, "inner_val_log_loss": loss, "nonconverged": nonconv})
        if best is None or loss < best[0]:
            best = (loss, cfg, p)
    temp = fit_temperature(best[2], yva)
    design = _M1Design(cols).fit(xtr_all)
    m = _m1_model(best[1])
    nonconv = _quiet_fit(m, design.transform(xtr_all), _y(df, train_pos))
    xte = design.transform(_xmat(df.iloc[test_pos], cols))
    p = _expand_classes(m.classes_, m.predict_proba(xte))
    return FoldFit(
        apply_temperature(_finalise(p), temp),
        {"selected": best[1], "temperature": temp, "temperature_source": TEMP_SOURCE,
         "hyper_search": search, "nonconverged": nonconv},
    )


def _lgb_params(cfg: dict) -> dict:
    return {
        "objective": "multiclass", "num_class": N_CLASSES, "learning_rate": LGB_LEARNING_RATE,
        "num_leaves": cfg["num_leaves"], "min_data_in_leaf": cfg["min_data_in_leaf"],
        "lambda_l2": cfg["lambda_l2"], "feature_fraction": cfg["feature_fraction"],
        "bagging_fraction": 1.0,
        "seed": SEED, "deterministic": True, "force_row_wise": True, "num_threads": 1,
        "verbose": -1,
    }


def fit_m2(df, train_pos, test_pos, inner, *, collect_shap: bool = False, **_) -> FoldFit:
    import lightgbm as lgb

    cols = ml_panel.TIER_A_NAMES
    itr, iva = inner
    xin, xva = _xmat(df.iloc[itr], cols), _xmat(df.iloc[iva], cols)
    yin, yva = _y(df, itr), _y(df, iva)
    search, best = [], None
    for cfg in LGB_GRID:
        d_in = lgb.Dataset(xin, yin, free_raw_data=True)
        d_va = lgb.Dataset(xva, yva, reference=d_in, free_raw_data=True)
        b = lgb.train(
            _lgb_params(cfg), d_in, num_boost_round=LGB_MAX_ROUNDS, valid_sets=[d_va],
            callbacks=[lgb.early_stopping(LGB_EARLY_STOP, verbose=False)],
        )
        rounds = int(b.best_iteration or LGB_MAX_ROUNDS)
        p = _finalise(b.predict(xva, num_iteration=rounds))
        loss = float(log_loss_rows(p, yva).mean())
        search.append({"config": cfg, "inner_val_log_loss": loss, "rounds": rounds})
        if best is None or loss < best[0]:
            best = (loss, cfg, rounds, p)
    temp = fit_temperature(best[3], yva)
    xtr, xte = _xmat(df.iloc[train_pos], cols), _xmat(df.iloc[test_pos], cols)
    booster = lgb.train(
        _lgb_params(best[1]), lgb.Dataset(xtr, _y(df, train_pos)), num_boost_round=best[2]
    )
    p = apply_temperature(_finalise(booster.predict(xte)), temp)
    diag = {"selected": best[1], "rounds": best[2], "temperature": temp,
            "temperature_source": TEMP_SOURCE, "hyper_search": search}
    shap = None
    if collect_shap:
        shap = tree_shap(booster, xte, cols)
        diag["shap_additivity_max_abs_err"] = shap["additivity_max_abs_err"]
    return FoldFit(p, diag, shap)


def tree_shap(booster, x: np.ndarray, cols: tuple[str, ...] | list[str]) -> dict:
    """Exact TreeSHAP in raw-margin units via ``pred_contrib=True``.

    ``contrib`` is (n, 3, p) per class, ``bias`` is (n, 3). Per row and class,
    ``contrib.sum(p) + bias`` equals the raw margin; the maximum absolute error is returned.
    """
    n, p = x.shape
    raw = booster.predict(x, pred_contrib=True).reshape(n, N_CLASSES, p + 1)
    margin = booster.predict(x, raw_score=True).reshape(n, N_CLASSES)
    err = float(np.abs(raw.sum(axis=2) - margin).max()) if n else 0.0
    return {
        "contrib": raw[:, :, :p].astype(np.float32), "bias": raw[:, :, p].astype(np.float32),
        "features": tuple(cols), "additivity_max_abs_err": err,
    }


# ---- M3: empirical-Bayes hierarchical multinomial logit -------------------------------------


class _Groups:
    def __init__(self, labels: pd.Series):
        s = labels.astype(object).where(labels.notna(), "__missing__").astype(str)
        self.levels = pd.Index(sorted(s.unique()))
        self.idx = self.levels.get_indexer(s)

    def encode(self, labels: pd.Series) -> np.ndarray:
        s = labels.astype(object).where(labels.notna(), "__missing__").astype(str)
        return self.levels.get_indexer(s)  # -1 for unseen -> population value (zero effect)


class BayesHier:
    """See the module docstring. Classes (down, flat, up) with ``flat`` as the reference."""

    def __init__(self, n_outer: int = 5, main_sd: float = 0.5, hs_scale: float = 0.5,
                 intercept_sd: float = 5.0, maxiter: int = 150):
        self.n_outer, self.main_sd, self.hs_scale = n_outer, main_sd, hs_scale
        self.intercept_sd, self.maxiter = intercept_sd, maxiter

    # design ---------------------------------------------------------------------------------
    def _design(self, x: np.ndarray, fit: bool) -> tuple[np.ndarray, np.ndarray]:
        if fit:
            self.prep = _Prep(BAYES_FEATURES).fit(x)
        z = self.prep.transform(x)
        flags = [np.isnan(x[:, BAYES_FEATURES.index(c)]).astype(float) for c in BAYES_FLAG_FEATURES]
        zs = z[:, [BAYES_FEATURES.index(c) for c in BAYES_SLOPES]]
        return np.column_stack([z, *flags]), zs

    def _logits(self, th, z, zs, ci, ei):
        n = len(z)
        L = z @ th["B"] + th["a0"]
        ok = ci >= 0
        if ok.any():
            L[ok] += th["uc"][ci[ok]]
            for s in range(zs.shape[1]):
                L[ok] += th["S"][ci[ok], s, :] * zs[ok, s : s + 1]
        oe = ei >= 0
        if oe.any():
            L[oe] += th["ue"][ei[oe]]
        return L[:n]

    def _unpack(self, v):
        q, C, E, ns = self.q, self.C, self.E, len(BAYES_SLOPES)
        o = 0
        th = {}
        for name, shape in (("B", (q, 2)), ("a0", (2,)), ("uc", (C, 2)), ("S", (C, ns, 2)),
                            ("ue", (E, 2))):
            size = int(np.prod(shape))
            th[name] = v[o : o + size].reshape(shape)
            o += size
        # sum-to-zero centring across categories: the global intercept a0 / main effects carry
        # the mean, the category terms are deviations from it
        th["uc"] = th["uc"] - th["uc"].mean(axis=0, keepdims=True)
        th["S"] = th["S"] - th["S"].mean(axis=0, keepdims=True)
        return th

    def _pack(self, th):
        return np.concatenate([th[k].ravel() for k in ("B", "a0", "uc", "S", "ue")])

    def fit(self, x: np.ndarray, y: np.ndarray, cat: pd.Series, ev: pd.Series) -> BayesHier:
        z, zs = self._design(x, True)
        self.gc, self.ge = _Groups(cat), _Groups(ev)
        self.q, self.C, self.E = z.shape[1], len(self.gc.levels), len(self.ge.levels)
        ci, ei = self.gc.idx, self.ge.idx
        ns = len(BAYES_SLOPES)
        yi = np.asarray(y, int)
        G0 = np.zeros((len(yi), 2))
        G0[yi == 0, 0] = 1.0
        G0[yi == 2, 1] = 1.0
        self.sd = {"cat": CAT_SD_FIXED, "slope": SLOPE_SD_FIXED, "event": 0.5}
        v = np.zeros(self.q * 2 + 2 + self.C * 2 + self.C * ns * 2 + self.E * 2)
        self.sd_trace = []
        self.post_var: dict[str, np.ndarray] = {}

        def obj(v):
            th = self._unpack(v)
            L = self._logits(th, z, zs, ci, ei)
            p = _softmax(np.column_stack([L[:, 0], np.zeros(len(L)), L[:, 1]]))
            nll = -np.log(np.clip(p[np.arange(len(yi)), yi], EPS, 1.0)).sum()
            G = p[:, [0, 2]] - G0
            pen = (
                (th["B"] ** 2).sum() / (2 * self.main_sd**2)
                + (th["a0"] ** 2).sum() / (2 * self.intercept_sd**2)
                + (th["uc"] ** 2).sum() / (2 * self.sd["cat"] ** 2)
                + (th["S"] ** 2).sum() / (2 * self.sd["slope"] ** 2)
                + (th["ue"] ** 2).sum() / (2 * self.sd["event"] ** 2)
            )
            g = {
                "B": z.T @ G + th["B"] / self.main_sd**2,
                "a0": G.sum(0) + th["a0"] / self.intercept_sd**2,
                "uc": np.column_stack([np.bincount(ci, G[:, k], self.C) for k in (0, 1)])
                + th["uc"] / self.sd["cat"] ** 2,
                "S": np.stack(
                    [
                        np.column_stack(
                            [np.bincount(ci, G[:, k] * zs[:, s], self.C) for k in (0, 1)]
                        )
                        for s in range(ns)
                    ],
                    axis=1,
                )
                + th["S"] / self.sd["slope"] ** 2,
                "ue": np.column_stack([np.bincount(ei, G[:, k], self.E) for k in (0, 1)])
                + th["ue"] / self.sd["event"] ** 2,
            }
            for k in ("uc", "S"):  # gradient of the centred parameters w.r.t. the raw ones
                g[k] = g[k] - g[k].mean(axis=0, keepdims=True)
            return nll + pen, self._pack(g)

        for _ in range(self.n_outer):
            res = minimize(obj, v, jac=True, method="L-BFGS-B", options={"maxiter": self.maxiter})
            v = res.x
            th = self._unpack(v)
            L = self._logits(th, z, zs, ci, ei)
            p = _softmax(np.column_stack([L[:, 0], np.zeros(len(L)), L[:, 1]]))
            w = p[:, [0, 2]] * (1 - p[:, [0, 2]])  # diagonal Hessian weight per logit
            # Laplace posterior variance (diag) -> EM update of each group SD (half-normal prior)
            hc = np.column_stack([np.bincount(ci, w[:, k], self.C) for k in (0, 1)])
            he = np.column_stack([np.bincount(ei, w[:, k], self.E) for k in (0, 1)])
            hs = np.stack(
                [
                    np.column_stack(
                        [np.bincount(ci, w[:, k] * zs[:, s] ** 2, self.C) for k in (0, 1)]
                    )
                    for s in range(ns)
                ],
                axis=1,
            )
            groups = (("cat", th["uc"], hc), ("slope", th["S"], hs), ("event", th["ue"], he))
            for key, u, h in groups:
                var = 1.0 / (h + 1.0 / self.sd[key] ** 2)
                self.post_var[key] = var
                if key != "event":  # category and slope SDs are fixed at the declared prior scale
                    continue
                q_sum, n_par = float((u**2 + var).sum()), u.size
                s2 = self.hs_scale**2
                x2 = (-n_par + np.sqrt(n_par**2 + 4 * q_sum / s2)) * s2 / 2
                self.sd[key] = float(np.sqrt(max(x2, 1e-8)))
            self.sd_trace.append(dict(self.sd))
        self.theta = self._unpack(v)
        self.converged = bool(res.success)
        return self

    def predict_proba(self, x: np.ndarray, cat: pd.Series, ev: pd.Series) -> np.ndarray:
        z, zs = self._design(x, False)
        L = self._logits(self.theta, z, zs, self.gc.encode(cat), self.ge.encode(ev))
        return _finalise(_softmax(np.column_stack([L[:, 0], np.zeros(len(L)), L[:, 1]])))


def fit_m3(df, train_pos, test_pos, inner, **_) -> FoldFit:
    """Event-pooled hierarchical logit. Temperature: same inner-split rule as every other arm."""
    itr, iva = inner

    def fit_on(pos):
        d = df.iloc[pos]
        return BayesHier().fit(
            _xmat(d, BAYES_FEATURES), _y(df, pos), d["fee_category"], _event_or_market(d)
        )

    def predict(m, pos):
        d = df.iloc[pos]
        return m.predict_proba(_xmat(d, BAYES_FEATURES), d["fee_category"], _event_or_market(d))

    temp = fit_temperature(predict(fit_on(itr), iva), _y(df, iva))
    m = fit_on(train_pos)
    p = apply_temperature(predict(m, test_pos), temp)
    n_unseen = int((m.ge.encode(_event_or_market(df.iloc[test_pos])) < 0).sum())
    return FoldFit(
        p,
        {"group_sd": m.sd, "sd_trace": m.sd_trace, "n_categories": m.C, "n_events": m.E,
         "test_rows_unseen_event": n_unseen, "optimizer_converged": m.converged,
         "temperature": temp, "temperature_source": TEMP_SOURCE,
         "method": "empirical-Bayes Laplace-EM for event SD; category terms fixed-effect "
         "priors (not NUTS)"},
    )


def _event_or_market(d: pd.DataFrame) -> pd.Series:
    ev = d["event_id"]
    if "market_id" in d.columns:
        ev = ev.where(ev.notna(), "mkt:" + d["market_id"].astype(str))
    return ev


ARMS: dict[str, Callable[..., FoldFit]] = {
    "M0": fit_m0, "M1": fit_m1, "M2": fit_m2, "M3_eb": fit_m3,
}


# ---------------------------------------------------------------------------------------------
# Trial log (search accounting)
# ---------------------------------------------------------------------------------------------


@dataclass
class TrialSink:
    """Appends one line per fit or scoring run to ``trials.jsonl`` through ``provenance``."""

    dataset: str
    path: Path = provenance.TRIALS_PATH
    provenance_record: dict | None = None
    label: str = provenance.DEV_LABEL

    def write(self, record: dict) -> dict:
        if self.provenance_record is None:
            self.provenance_record = provenance.run_provenance()
            self.provenance_record["env"].update(_ml_versions())
        return provenance.append_trial(
            {"label": self.label, "dataset": self.dataset,
             "provenance": self.provenance_record, **record},
            self.path,
        )


def _libomp_info() -> dict:
    """Source path, sha256 and version of the libomp that lib_lightgbm actually loads."""
    import subprocess

    try:
        import importlib.util

        spec = importlib.util.find_spec("lightgbm")
        lib = Path(spec.origin).parent / "lib" / "lib_lightgbm.dylib"
        if not lib.exists():
            return {"libomp": "n/a (not a macOS dylib)"}
        out = subprocess.run(["otool", "-L", str(lib)], capture_output=True, text=True,
                             timeout=15, check=False).stdout
        line = next((x for x in out.splitlines() if "libomp" in x), "")
        rp = subprocess.run(["otool", "-l", str(lib)], capture_output=True, text=True,
                            timeout=15, check=False).stdout
        paths = [x.split("path ")[1].split(" (")[0] for x in rp.splitlines() if "path " in x]
        found = next((Path(r) / "libomp.dylib" for r in paths
                      if (Path(r) / "libomp.dylib").is_file()), None)
        if found is None:
            found = next((Path(r) for r in ("/opt/homebrew/opt/libomp/lib/libomp.dylib",
                                            "/usr/local/opt/libomp/lib/libomp.dylib")
                          if Path(r).is_file()), None)
        return {
            "libomp_link": line.strip(),
            "libomp_path": str(found) if found else UNKNOWN,
            "libomp_sha256": provenance.sha256_file(found) if found else UNKNOWN,
        }
    except Exception:  # provenance must never break a fit
        return {"libomp": UNKNOWN}


UNKNOWN = provenance.UNKNOWN


def _ml_versions() -> dict:
    out = {name: provenance._version(name) for name in ("sklearn", "lightgbm", "scipy")}
    out.update(_libomp_info())
    return out


def _trial_header(arm: str, manifest: dict) -> dict:
    return {
        "arm": arm,
        "feature_set_version": manifest["feature_set_version"],
        "delta": manifest["delta"],
        "tau": None,  # economic threshold: not chosen at this stage
        "tau_m0": None,
        "manifest_sha256": manifest["manifest_sha256"],
        "category_policy": manifest["category_policy"],
        "seed": SEED,
    }


# ---------------------------------------------------------------------------------------------
# Out-of-fold driver
# ---------------------------------------------------------------------------------------------


@dataclass
class ArmResult:
    arm: str
    proba: np.ndarray  # (n, 3); NaN where the row is in no test block
    test_mask: np.ndarray
    folds: list[dict]
    shap_folds: list[dict] = field(default_factory=list)  # {fold, test_pos, shap}


def fit_fold(arm: str, df: pd.DataFrame, fold: dict, embargo_s: float, *, collect_shap=False):
    """Fit one arm on one fold. Returns (FoldFit, train_pos, test_pos)."""
    ml_panel.register_tier_a()
    tr_mask, te_mask = ml_panel.fold_masks(df, fold)
    train_pos, test_pos = np.flatnonzero(tr_mask), np.flatnonzero(te_mask)
    if len(train_pos) == 0 or len(test_pos) == 0:
        raise ValueError(f"fold {fold['fold']}: empty train or test set")
    inner = inner_split(df, train_pos, embargo_s) if arm in ARMS else None
    if inner is not None and not set(np.concatenate(inner)).issubset(set(train_pos)):
        raise AssertionError("inner split leaked outside the training fold")
    kw = {"collect_shap": collect_shap} if arm == "M2" else {}
    ff = ARMS[arm](df, train_pos, test_pos, inner, **kw)
    ff.diag.update(n_train=int(len(train_pos)), n_test=int(len(test_pos)))
    if inner is not None:
        ff.diag.update(n_inner_train=int(len(inner[0])), n_inner_val=int(len(inner[1])))
    return ff, train_pos, test_pos


def run_arm(
    arm: str, df: pd.DataFrame, manifest: dict, *, sink: TrialSink | None,
    collect_shap: bool = False,
) -> ArmResult:
    """Out-of-fold probabilities for one arm over every fold in ``manifest``.

    ``df`` is the labelled ml_panel frame (``ml_panel.labelled``); ``sink=None`` writes no trial
    lines (smoke runs and unit tests only; development runs must pass a ``TrialSink``).
    """
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    df = df.reset_index(drop=True)
    proba = np.full((len(df), N_CLASSES), np.nan)
    mask = np.zeros(len(df), bool)
    folds, shap_folds = [], []
    for fold in manifest["folds"]:
        t_start = time.perf_counter()
        ff, _, test_pos = fit_fold(
            arm, df, fold, manifest["embargo_s"], collect_shap=collect_shap and arm == "M2"
        )
        proba[test_pos], mask[test_pos] = ff.proba, True
        diag = {**ff.diag, "fold": fold["fold"], "seconds": round(time.perf_counter() - t_start, 2)}
        folds.append(diag)
        if ff.shap is not None:
            shap_folds.append({"fold": fold["fold"], "test_pos": test_pos, "shap": ff.shap})
        if sink is not None:
            sink.write({"kind": "ml_fit", **_trial_header(arm, manifest), **diag})
    return ArmResult(arm, proba, mask, folds, shap_folds)


def run_arms(
    df: pd.DataFrame, manifest: dict, arms: tuple[str, ...] = ARM_NAMES, *,
    sink: TrialSink | None, collect_shap: bool = True,
) -> dict[str, ArmResult]:
    if "M0" not in arms:
        raise ValueError("the M0 baseline must be among the arms")
    return {
        a: run_arm(a, df, manifest, sink=sink, collect_shap=collect_shap) for a in arms
    }


# ---------------------------------------------------------------------------------------------
# Scoring and clustered paired bootstrap vs M0
# ---------------------------------------------------------------------------------------------


def cluster_vectors(df: pd.DataFrame, dependence_groups: np.ndarray | None = None) -> dict:
    """Co-primary cluster vectors: event (market id as the counted fallback) and, when given,
    the D120 dependence-group id."""
    ev = _event_or_market(df)
    fallback = int(df["event_id"].isna().sum())
    out = {"event": ev.to_numpy(), "_n_event_fallback_to_market": fallback}
    if dependence_groups is not None:
        out["dependence_group"] = np.asarray(dependence_groups)
    return out


def score_arms(
    df: pd.DataFrame, results: dict[str, ArmResult], clusters: dict, *, baseline: str = "M0",
    n_boot: int = evaluate.BOOT_N, seed: int = evaluate.BOOT_SEED, sink: TrialSink | None = None,
    manifest: dict | None = None,
) -> dict:
    """Per-row log loss and Brier, and the clustered paired bootstrap against ``baseline``.

    ``paired_bootstrap`` is reused with the per-row loss in place of SSE, so its output is the
    relative loss improvement ``1 - sum(loss_arm) / sum(loss_M0)`` per resample. Each draw
    resamples whole clusters across all periods together.
    """
    df = df.reset_index(drop=True)
    mask = results[baseline].test_mask.copy()
    for r in results.values():
        mask &= r.test_mask
    y = df["y_class"].to_numpy(float)[mask].astype(int)
    loss = {a: log_loss_rows(r.proba[mask], y) for a, r in results.items()}
    brier = {a: brier_rows(r.proba[mask], y) for a, r in results.items()}
    required = ("event", "dependence_group")
    reasons: list[str] = []
    prepared: dict[str, pd.Series] = {}
    for cname in required:
        if cname not in clusters:
            reasons.append(f"cluster definition {cname!r} not supplied")
            continue
        cl = pd.Series(np.asarray(clusters[cname], dtype=object)[mask])
        frac = float(cl.isna().mean()) if len(cl) else 1.0
        if frac >= 1.0:
            reasons.append(f"cluster definition {cname!r} is entirely null")
        elif frac > MAX_NULL_CLUSTER_FRACTION:
            reasons.append(
                f"cluster definition {cname!r} has {frac:.1%} null ids "
                f"(limit {MAX_NULL_CLUSTER_FRACTION:.0%})"
            )
        else:  # a few nulls: each null row is its own singleton cluster (counted)
            prepared[cname] = cl.where(cl.notna(), "__null_" + cl.index.astype(str))
    for cname in clusters:
        if not cname.startswith("_") and cname not in required and cname not in prepared:
            prepared[cname] = pd.Series(np.asarray(clusters[cname], dtype=object)[mask])
    missing = bool(reasons)
    summary = {
        "non_inferential": missing,
        "non_inferential_reason": (
            None if not missing else
            "NON-INFERENTIAL: " + "; ".join(reasons) + ". The design requires the CI to exclude "
            "0 under BOTH valid event and dependence-group clusters"
        ),
        "n_rows": int(mask.sum()),
        "status": "DEVELOPMENT out-of-fold scores; no performance or edge claim",
        "arms": {
            a: {"log_loss": float(loss[a].mean()), "brier": float(brier[a].mean())}
            for a in results
        },
        "bootstrap": {},
    }
    for cname, clser in prepared.items():
        cl = clser.to_numpy()
        block = {"n_clusters": int(pd.Series(cl).nunique()), "n_boot": n_boot, "seed": seed}
        for metric, rows in (("log_loss", loss), ("brier", brier)):
            bt = paired_bootstrap(cl, rows, baseline, n_boot=n_boot, seed=seed)
            base_total = float(rows[baseline].sum())
            entry = {}
            for a in results:
                if a == baseline:
                    continue
                d = rows[baseline] - rows[a]
                entry[a] = {
                    "rel_improvement": float(1 - rows[a].sum() / base_total),
                    "ci95": bt["models"][a],
                    "sd_c": power.cluster_contrib_sd(cl, d, base_total),
                }
            block[metric] = entry
        summary["bootstrap"][cname] = block
    if sink is not None and manifest is not None:
        sink.write({"kind": "ml_score", **_trial_header("all", manifest), "summary": summary})
    return summary


# ---------------------------------------------------------------------------------------------
# SHAP summary (exploratory)
# ---------------------------------------------------------------------------------------------


def shap_margins(contrib: np.ndarray) -> dict[str, np.ndarray]:
    """``up_minus_down`` (direction) and ``move_vs_flat`` (activity), both (n, p), in margin units.

    ``move_vs_flat`` is the mean of the up and down class margins minus the flat margin.
    """
    c = contrib.astype(float)
    return {
        "up_minus_down": c[:, 2] - c[:, 0],
        "move_vs_flat": 0.5 * (c[:, 2] + c[:, 0]) - c[:, 1],
    }


def summarize_shap(df: pd.DataFrame, res: ArmResult) -> dict:
    """Mean |SHAP| per feature, per family and per category from out-of-fold SHAP only."""
    if not res.shap_folds:
        raise ValueError("no SHAP collected; run the M2 arm with collect_shap=True")
    df = df.reset_index(drop=True)
    names = list(res.shap_folds[0]["shap"]["features"])
    fam = np.array([features.REGISTRY[n].family for n in names])
    fam_names = sorted(set(fam))
    cat = df["fee_category"].astype(object).where(df["fee_category"].notna(), "__missing__")
    out: dict = {
        "status": EXPLORATORY_NOTE, "arm": res.arm, "features": names,
        "families": {f: [n for n, g in zip(names, fam, strict=True) if g == f] for f in fam_names},
        "margins": {}, "additivity_max_abs_err": max(
            f["shap"]["additivity_max_abs_err"] for f in res.shap_folds
        ),
    }
    per_fold_vec: dict[str, list[np.ndarray]] = {"up_minus_down": [], "move_vs_flat": []}
    chunks: dict[str, list[np.ndarray]] = {"up_minus_down": [], "move_vs_flat": []}
    cats: list[np.ndarray] = []
    for f in res.shap_folds:
        mg = shap_margins(f["shap"]["contrib"])
        cats.append(cat.to_numpy()[f["test_pos"]])
        for k, v in mg.items():
            chunks[k].append(v)
            per_fold_vec[k].append(np.abs(v).mean(axis=0))
    allcat = np.concatenate(cats)
    for k in chunks:
        v = np.vstack(chunks[k])
        by_feat = np.abs(v).mean(axis=0)
        fam_sum = np.column_stack([v[:, fam == f].sum(axis=1) for f in fam_names])
        by_cat = {
            str(c): dict(zip(names, np.abs(v[allcat == c]).mean(axis=0).tolist(), strict=True))
            for c in sorted(set(allcat))
        }
        rho = float("nan")
        if len(per_fold_vec[k]) >= 2:
            rs = [
                spearmanr(a, b)[0]
                for a, b in itertools.combinations(per_fold_vec[k], 2)
            ]
            rho = float(np.nanmean(rs))
        out["margins"][k] = {
            "mean_abs_by_feature": dict(zip(names, by_feat.tolist(), strict=True)),
            "mean_abs_by_family": dict(
                zip(fam_names, np.abs(fam_sum).mean(axis=0).tolist(), strict=True)
            ),
            "mean_abs_by_category": by_cat,
            "fold_rank_spearman_mean": rho,
            "n_rows": int(len(v)),
        }
    return out


# ---------------------------------------------------------------------------------------------
# Simulation check of the partial-pooling estimator (amendment A1)
# ---------------------------------------------------------------------------------------------


def _cover(est_arr: np.ndarray, post_var: np.ndarray, truth: np.ndarray) -> float:
    return float(np.mean(np.abs(est_arr - truth) <= 1.96 * np.sqrt(post_var)))


def simulate_hierarchical_check(
    n_reps: int = 20, n: int = 6000, n_cat: int = 12, n_event: int = 150,
    sd_cat: float = 0.5, sd_event: float = 0.6, sd_slope: float = 0.3, seed: int = SEED,
) -> dict:
    """Fit ``BayesHier`` on synthetic hierarchical data with known group SDs.

    The event SD is estimated (Laplace-EM); the category and slope SDs are fixed at
    ``CAT_SD_FIXED`` / ``SLOPE_SD_FIXED``, so ``sd_cat`` / ``sd_slope`` here may be set away from
    those values to show the cost of a wrong prior scale. Reports the mean and spread of the
    estimated event SD, and the empirical coverage of nominal 95% Laplace intervals
    (estimate +/- 1.96 posterior SD) for the true (sum-to-zero centred) category intercepts, event
    intercepts and category slopes of the "up" logit. Nothing is tuned to make the numbers look
    good; they are reported as they come.
    """
    rng = np.random.default_rng(seed)
    q = len(BAYES_FEATURES)
    i_slope = [BAYES_FEATURES.index(c) for c in BAYES_SLOPES]
    est_event: list[float] = []
    hit = {"cat": [], "slope": [], "event": []}
    for _ in range(n_reps):
        uc = rng.normal(0, sd_cat, n_cat)
        ue = rng.normal(0, sd_event, n_event)
        sl = rng.normal(0, sd_slope, (n_cat, 2))
        beta = rng.normal(0, 0.3, q)
        x = rng.normal(size=(n, q))
        ci, ei = rng.integers(0, n_cat, n), rng.integers(0, n_event, n)
        eta = x @ beta + uc[ci] + ue[ei] + (sl[ci] * x[:, i_slope]).sum(1)
        # "up" logit = eta, "down" logit = -eta, flat = 0 (one shared latent, K-1 logits)
        p = _softmax(np.column_stack([-eta, np.zeros(n), eta]))
        u = rng.random(n)
        y = (u > p[:, 0]).astype(int) + (u > p[:, 0] + p[:, 1]).astype(int)
        m = BayesHier().fit(
            x, y, pd.Series([f"c{i}" for i in ci]), pd.Series([f"e{i}" for i in ei])
        )
        est_event.append(m.sd["event"])
        # slopes live on the standardised-feature scale: rescale the truth accordingly
        scale = m.prep.sd[i_slope]
        lv = {v: i for i, v in enumerate(m.gc.levels)}
        oc = [lv[f"c{i}"] for i in range(n_cat)]
        te = np.array([ue[int(v[1:])] for v in m.ge.levels])
        uc_c, sl_c = uc - uc.mean(), (sl - sl.mean(0)) * scale[None, :]
        hit["cat"].append(_cover(m.theta["uc"][oc, 1], m.post_var["cat"][oc, 1], uc_c))
        hit["event"].append(_cover(m.theta["ue"][:, 1], m.post_var["event"][:, 1], te))
        hit["slope"].append(_cover(m.theta["S"][oc, :, 1], m.post_var["slope"][oc, :, 1], sl_c))
    return {
        "n_reps": n_reps, "n": n, "n_categories": n_cat, "n_events": n_event,
        "truth_sd": {"cat": sd_cat, "slope": sd_slope, "event": sd_event},
        "fixed_prior_sd": {"cat": CAT_SD_FIXED, "slope": SLOPE_SD_FIXED},
        "estimated_event_sd_mean": float(np.mean(est_event)),
        "estimated_event_sd_std": float(np.std(est_event, ddof=1)),
        "coverage_95_mean": {k: float(np.mean(v)) for k, v in hit.items()},
        "note": "coverage uses diagonal Laplace posterior variances (cross-class and "
        "cross-parameter terms ignored); slope truth is on the standardised-feature scale",
    }
