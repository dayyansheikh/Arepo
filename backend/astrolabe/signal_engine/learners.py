# ruff: noqa: E501
"""Design matrices, learners (regularised logistic regression; LightGBM with an inner time split and temperature
scaling) and portable artifacts. Prediction never needs scikit-learn: logistic artifacts are JSON coefficients and
LightGBM artifacts are the booster's text model.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from .aux import MODEL_FAMILY_COLUMNS

LOG1P_COLS = {"ms_stale_s", "ms_age_h", "bk_age_s", "xv_age_s"}
TTE_BASE = ("mo_chg_1h", "mo_d2h", "mo_chg_1d", "mo_d6h")
CAT_MIN_SHARE = 0.005


def raw_columns(spec: dict) -> list[str]:
    return [c for fam in spec["families"] for c in MODEL_FAMILY_COLUMNS[fam]]


def name_families(spec: dict) -> dict[str, str]:
    """Design-matrix column name -> feature family (derived sets map to their own token, e.g. ``tte``)."""
    out = {}
    for fam in spec["families"]:
        for c in MODEL_FAMILY_COLUMNS[fam]:
            for n in {"ms_hours_to_end": ("log_hours", "end_unknown"), "ms_mid": ("logit_mid", "abs_dev")}.get(c, (c,)):
                out[n] = fam
    if "tte" in spec["derived"]:
        for n in ["near24", "near72", "mo_chg_1h_x_loghours"] + [f"{c}_x_near{h}" for c in TTE_BASE for h in (24, 72)]:
            out[n] = "tte"
    return out


def _numeric_block(df: pd.DataFrame, spec: dict) -> tuple[np.ndarray, list[str]]:
    cols, names = [], []
    for c in raw_columns(spec):
        v = df[c].to_numpy(np.float32)
        if c == "ms_hours_to_end":
            with np.errstate(invalid="ignore"):
                cols.append(np.log1p(v))
            names.append("log_hours")
            cols.append(np.isnan(v).astype(np.float32))
            names.append("end_unknown")
            continue
        if c == "ms_mid":
            m = np.clip(v, 0.01, 0.99)
            cols.append(np.log(m / (1 - m)).astype(np.float32))
            names.append("logit_mid")
            cols.append(np.abs(v - 0.5).astype(np.float32))
            names.append("abs_dev")
            continue
        if c in LOG1P_COLS:
            with np.errstate(invalid="ignore"):
                v = np.log1p(np.clip(v, 0, None))
        cols.append(v.astype(np.float32))
        names.append(c)
    if "tte" in spec["derived"]:
        hours = df["ms_hours_to_end"].to_numpy(np.float32)
        with np.errstate(invalid="ignore"):
            near24 = np.where(np.isnan(hours), 0, hours < 24).astype(np.float32)
            near72 = np.where(np.isnan(hours), 0, hours < 72).astype(np.float32)
            lh = np.nan_to_num(np.log1p(hours), nan=0.0).astype(np.float32)
        cols += [near24, near72]
        names += ["near24", "near72"]
        for c in TTE_BASE:
            v = df[c].to_numpy(np.float32)
            cols += [v * near24, v * near72]
            names += [f"{c}_x_near24", f"{c}_x_near72"]
        cols.append(df["mo_chg_1h"].to_numpy(np.float32) * lh)
        names.append("mo_chg_1h_x_loghours")
    return np.column_stack(cols).astype(np.float32), names


def categories_of(df: pd.DataFrame) -> list[str]:
    vc = df["category"].astype(str).value_counts(normalize=True)
    return sorted(vc[vc >= CAT_MIN_SHARE].index.tolist())


# ---------------------------------------------------------------------------------------------- logistic


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def _lr_matrix(df: pd.DataFrame, spec: dict, art: dict) -> np.ndarray:
    X, names = _numeric_block(df, spec)
    assert names == art["numeric"], "design drift"
    med = np.asarray(art["median"], np.float32)
    nan = np.isnan(X)
    flags = nan[:, art["flag_idx"]].astype(np.float32) if art["flag_idx"] else np.zeros((len(X), 0), np.float32)
    X = np.where(nan, med, X)
    X = np.clip((X - np.asarray(art["mean"], np.float32)) / np.asarray(art["sd"], np.float32), -8, 8)
    cat = df["category"].astype(str).to_numpy()
    onehot = np.column_stack([(cat == c).astype(np.float32) for c in art["categories"]]) if art["categories"] \
        else np.zeros((len(X), 0), np.float32)
    return np.hstack([X, flags, onehot]).astype(np.float32)


def fit_logreg(df: pd.DataFrame, y: np.ndarray, spec: dict, n_classes: int) -> dict:
    from sklearn.linear_model import LogisticRegression

    X, names = _numeric_block(df, spec)
    nan = np.isnan(X)
    flag_idx = [i for i in range(X.shape[1]) if nan[:, i].any() and not nan[:, i].all()]
    med = np.nanmedian(np.where(nan.all(axis=0), 0.0, X), axis=0) if len(X) else np.zeros(X.shape[1])
    med = np.nan_to_num(med, nan=0.0)
    Xi = np.where(nan, med, X)
    mean, sd = Xi.mean(axis=0), Xi.std(axis=0)
    sd = np.where(sd > 1e-9, sd, 1.0)
    cats = categories_of(df) if "market_state" in spec["families"] else []
    art = {"learner": "logreg", "numeric": names, "flag_idx": flag_idx, "median": med.tolist(), "mean": mean.tolist(),
           "sd": sd.tolist(), "categories": cats, "n_classes": n_classes}
    M = _lr_matrix(df, spec, art)
    p = spec["params"]
    clf = LogisticRegression(C=float(p.get("C", 1.0)), max_iter=int(p.get("max_iter", 300)), tol=float(p.get("tol", 1e-4)))
    clf.fit(M, y)
    art["classes"] = [int(c) for c in clf.classes_]
    art["coef"] = clf.coef_.tolist()
    art["intercept"] = clf.intercept_.tolist()
    art["n_iter"] = int(np.max(clf.n_iter_))
    return art


def predict_logreg(art: dict, df: pd.DataFrame, spec: dict) -> np.ndarray:
    M = _lr_matrix(df, spec, art)
    coef, b = np.asarray(art["coef"], np.float64), np.asarray(art["intercept"], np.float64)
    z = M.astype(np.float64) @ coef.T + b
    k = art["n_classes"]
    if coef.shape[0] == 1:  # binary sklearn layout: P(class 1)
        p1 = 1.0 / (1.0 + np.exp(-z[:, 0]))
        part = np.column_stack([1 - p1, p1])
    else:
        part = _softmax(z)
    out = np.zeros((len(M), k))
    for j, c in enumerate(art["classes"]):
        out[:, c] = part[:, j]
    return out


# ---------------------------------------------------------------------------------------------- LightGBM


def _lgb_matrix(df: pd.DataFrame, spec: dict, art: dict) -> np.ndarray:
    X, names = _numeric_block(df, spec)
    assert names == art["numeric"], "design drift"
    cmap = {c: i for i, c in enumerate(art["categories"])}
    code = np.array([cmap.get(c, len(cmap)) for c in df["category"].astype(str).to_numpy()], np.float32)
    return np.hstack([X, code[:, None]])


def inner_split(otime: np.ndarray, ltime: np.ndarray, frac: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    """Validation = the last ``frac`` of origin times; training rows must have their label before the first one."""
    u = np.unique(otime)
    cut = u[int(math.floor(len(u) * (1 - frac)))] if len(u) >= 5 else np.inf
    val = otime >= cut
    tr = (~val) & (ltime < cut)
    return tr, val


def _nll(p: np.ndarray, y: np.ndarray) -> float:
    return float(-np.mean(np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1))))


def _temp_probs(raw: np.ndarray, T: float, k: int) -> np.ndarray:
    if k == 2:
        r = raw if raw.ndim == 1 else raw[:, 0]
        p1 = 1.0 / (1.0 + np.exp(-r / T))
        return np.column_stack([1 - p1, p1])
    return _softmax(raw / T)


def fit_lgbm(df: pd.DataFrame, y: np.ndarray, otime: np.ndarray, ltime: np.ndarray, spec: dict, n_classes: int,
             attribution: bool = True) -> dict:
    import lightgbm as lgb
    from scipy.optimize import minimize_scalar

    _, names = _numeric_block(df.iloc[:1], spec)
    art = {"learner": "lgbm", "numeric": names, "categories": categories_of(df), "n_classes": n_classes}
    X = _lgb_matrix(df, spec, art)
    tr, val = inner_split(otime, ltime, float(spec["params"].get("val_frac", 0.2)))
    if tr.sum() < 1000 or val.sum() < 500 or len(np.unique(y[tr])) < n_classes:
        raise ValueError(f"lgbm inner split too small (train {int(tr.sum())}, val {int(val.sum())})")
    p = dict(spec["params"]["lgb"])
    p.update({"objective": "multiclass" if n_classes > 2 else "binary", "verbose": -1, "num_threads": 1,
              "deterministic": True, "force_row_wise": True})
    if n_classes > 2:
        p["num_class"] = n_classes
    cat_idx = [X.shape[1] - 1]
    dtr = lgb.Dataset(X[tr], y[tr], categorical_feature=cat_idx, free_raw_data=True)
    dva = lgb.Dataset(X[val], y[val], categorical_feature=cat_idx, reference=dtr, free_raw_data=True)
    bst = lgb.train(p, dtr, num_boost_round=int(spec["params"].get("max_rounds", 300)), valid_sets=[dva],
                    callbacks=[lgb.early_stopping(int(spec["params"].get("early_stopping", 30)), verbose=False)])
    raw = bst.predict(X[val], raw_score=True, num_iteration=bst.best_iteration)
    yv = y[val]
    res = minimize_scalar(lambda T: _nll(_temp_probs(raw, T, n_classes), yv), bounds=(0.3, 5.0), method="bounded")
    art.update({"model": bst.model_to_string(num_iteration=bst.best_iteration), "best_iteration": int(bst.best_iteration),
                "temperature": float(res.x), "n_train_inner": int(tr.sum()), "n_val_inner": int(val.sum()),
                "val_nll": float(res.fun),
                # a development diagnostic: not computed while the spec is under an embargo (DESIGN_V1 section 8)
                "attribution": family_attribution(bst, X[val], names, spec, n_classes) if attribution else None})
    return art


ATTR_MAX_ROWS = 20000


def family_attribution(bst, Xv: np.ndarray, names: list[str], spec: dict, n_classes: int) -> dict:
    """Mean |SHAP| (LightGBM ``pred_contrib``, raw-score scale, summed over classes) per feature family on a seeded
    subsample of the inner validation block (development diagnostic of the fit; never a score)."""
    rng = np.random.default_rng(0)
    if len(Xv) > ATTR_MAX_ROWS:
        Xv = Xv[np.sort(rng.choice(len(Xv), ATTR_MAX_ROWS, replace=False))]
    c = np.asarray(bst.predict(Xv, pred_contrib=True, num_iteration=bst.best_iteration))
    width = len(names) + 2  # numeric columns + category code + bias
    k = 1 if n_classes == 2 else n_classes
    per = np.abs(c.reshape(len(Xv), k, width)).sum(axis=1).mean(axis=0)
    fam_of = name_families(spec)
    fams: dict[str, float] = {}
    for i, n in enumerate(names):
        f = fam_of.get(n, "other")
        fams[f] = fams.get(f, 0.0) + float(per[i])
    fams["category"] = float(per[len(names)])
    return {"method": "lgbm_pred_contrib_mean_abs", "block": "inner_validation", "rows": int(len(Xv)),
            "families": {f: round(v, 6) for f, v in sorted(fams.items())}}


def predict_lgbm(art: dict, df: pd.DataFrame, spec: dict) -> np.ndarray:
    import lightgbm as lgb

    bst = art.get("_booster")
    if bst is None:
        bst = art["_booster"] = lgb.Booster(model_str=art["model"])
    raw = bst.predict(_lgb_matrix(df, spec, art), raw_score=True)
    return _temp_probs(np.asarray(raw), art["temperature"], art["n_classes"])


# ---------------------------------------------------------------------------------------------- dispatch


def fit(spec: dict, df: pd.DataFrame, y: np.ndarray, otime: np.ndarray, ltime: np.ndarray, n_classes: int,
        attribution: bool = True) -> dict:
    if spec["learner"] == "logreg":
        return fit_logreg(df, y, spec, n_classes)
    return fit_lgbm(df, y, otime, ltime, spec, n_classes, attribution=attribution)


def predict(spec: dict, art: dict, df: pd.DataFrame) -> np.ndarray:
    if art["learner"] == "logreg":
        return predict_logreg(art, df, spec)
    return predict_lgbm(art, df, spec)


def dumps(art: dict) -> bytes:
    return json.dumps({k: v for k, v in art.items() if not k.startswith("_")}, sort_keys=True,
                      separators=(",", ":")).encode()
