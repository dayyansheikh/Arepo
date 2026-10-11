"""Model-interpretability for the AREPO ML dev lane. EXPLORATORY ONLY.

What this module is for: asking which feature families add out-of-sample predictive value, under
which regimes, and how features interact, WITHOUT over-reading SHAP. SHAP (and any other
fitted-model explanation) describes a fitted model; it does not establish independent predictive
value or causality. The value-added evidence here is the refit ablation (out-of-fold log-loss,
cluster-bootstrap CI), not the attributions.

Everything is computed on out-of-fold test rows only. Every run is appended to
``docs/research_lab/trials.jsonl`` (kind ``ml_explain``, label EXPLORATORY) so the search
accounting sees it. Thresholds found here are HYPOTHESES tied to the fold they were discovered
in; ``evaluate_threshold`` refuses to score them on the data they came from.

The module is model-agnostic through ``fit_fn(X, y, cols) -> model`` where ``model.predict_proba``
returns ``(n, K)``. The default is a fixed-configuration LightGBM (no tuning: the ablation must
compare like with like). It imports no ml_models/ml_panel state beyond ``folds_from_manifest``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import compare, provenance

LABEL = "EXPLORATORY"
KIND = "ml_explain"
MIN_CLUSTERS = 50  # a regime cell with fewer clusters is flagged uninformative
CORR_THRESHOLD = 0.7
EPS = 1e-15
SEED = 116
UNASSIGNED = "unassigned"
HYPOTHESIS = "HYPOTHESIS"
BY_Q = 0.10  # Benjamini-Yekutieli q (FEATURE_DISCOVERY_PROGRAMME triage rule)

# Declared mapping of feature name -> family. Families that do not exist yet are fine: a family
# with no present feature is reported as absent, and new features are mapped by adding to this
# dict (or passing a different mapping). Names here are prefixes/exact names; see assign_families.
FAMILY_NAMES = ("market_state", "book", "flow", "wallet", "relationships", "metadata", "external")
DEFAULT_FAMILY_PREFIXES: dict[str, tuple[str, ...]] = {
    "market_state": (
        "mid",
        "logit_mid",
        "abs_mid",
        "own_",
        "chg_",
        "hist_",
        "ltp_",
        "spread",
        "vol",
    ),
    "book": ("sw_", "depth", "imbalance", "microprice", "best_"),
    "flow": ("flow_", "ml_flow_", "trade_", "ofi", "turnover"),
    "wallet": ("wallet_", "ml_wlt_", "w_"),
    "relationships": ("sibling_", "rel_", "corr_"),
    "metadata": ("hours_to_end", "end_", "market_age", "liq", "category", "staleness"),
    "external": ("ext_", "ext"),
}


# ---------------------------------------------------------------------------------------------
# Families
# ---------------------------------------------------------------------------------------------


def assign_families(
    features: Sequence[str],
    mapping: dict[str, Sequence[str]] | None = None,
    exact: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Group ``features`` into families.

    ``exact`` (feature -> family) wins; otherwise the first family (in mapping order) with a
    matching prefix wins; otherwise ``unassigned``. Declared families with no features are kept as
    empty lists so callers can see they are absent rather than silently dropping them.
    """
    mapping = DEFAULT_FAMILY_PREFIXES if mapping is None else mapping
    out: dict[str, list[str]] = {f: [] for f in mapping}
    for c in features:
        fam = (exact or {}).get(c)
        if fam is None:
            fam = next(
                (f for f, pre in mapping.items() if any(c.startswith(p) for p in pre)), UNASSIGNED
            )
        out.setdefault(fam, []).append(c)
    return out


# ---------------------------------------------------------------------------------------------
# Loss, clusters, bootstrap
# ---------------------------------------------------------------------------------------------


def log_loss_rows(proba: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.asarray(proba, float)
    idx = np.asarray(y, int)
    return -np.log(np.clip(p[np.arange(len(idx)), idx], EPS, 1.0))


def score_from_proba(p: np.ndarray) -> np.ndarray:
    """Scalar directional score: P(up)-P(down) for 3 classes, else the last class probability."""
    return p[:, 2] - p[:, 0] if p.shape[1] == 3 else p[:, -1]


def cluster_boot(d: np.ndarray, cluster: np.ndarray, n_boot: int = 1000, seed: int = SEED) -> dict:
    """Cluster bootstrap of the mean of per-row values ``d`` (e.g. loss differences)."""
    d = np.asarray(d, float)
    ok = np.isfinite(d)
    d, cl = d[ok], np.asarray(cluster)[ok]
    if len(d) == 0:
        return {
            "mean": None,
            "ci": [None, None],
            "p_two_sided": None,
            "p_pos": None,
            "n_rows": 0,
            "n_clusters": 0,
        }
    codes, uniq = pd.factorize(cl)
    k = len(uniq)
    s = np.bincount(codes, weights=d, minlength=k)
    n = np.bincount(codes, minlength=k).astype(float)
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, k, size=k)
        means[i] = s[idx].sum() / n[idx].sum()
    lo, hi = np.percentile(means, [2.5, 97.5])
    p = 2.0 * min((means <= 0).mean(), (means >= 0).mean())
    p = float(min(1.0, max(p, 1.0 / (n_boot + 1))))
    return {
        "mean": float(d.mean()),
        "ci": [float(lo), float(hi)],
        "p_two_sided": p,
        "p_pos": float(max((means <= 0).mean(), 1.0 / (n_boot + 1))),  # one-sided, mean > 0
        "n_rows": int(len(d)),
        "n_clusters": int(k),
    }


def holm(pvals: dict[str, float]) -> dict[str, dict]:
    """Holm step-down adjusted p-values within the declared family set."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, running, out = len(items), 0.0, {}
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[name] = {"p": float(p), "p_holm": float(running), "reject_5pct": bool(running < 0.05)}
    return out


# ---------------------------------------------------------------------------------------------
# Models and out-of-fold fitting
# ---------------------------------------------------------------------------------------------


@dataclass
class Fold:
    fold_id: str
    train_pos: np.ndarray
    test_pos: np.ndarray


def folds_from_manifest(df: pd.DataFrame, manifest: dict) -> list[Fold]:
    """Adapt an ml_panel fold manifest (uses ml_panel.fold_masks; imported lazily)."""
    from . import ml_panel

    out = []
    for f in manifest["folds"]:
        tr, te = ml_panel.fold_masks(df, f)
        out.append(Fold(str(f["fold"]), np.flatnonzero(tr), np.flatnonzero(te)))
    return out


@dataclass
class LGBModel:
    booster: object
    cols: tuple[str, ...]
    n_classes: int

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        p = self.booster.predict(np.asarray(x, float))
        if self.n_classes == 2:
            p = np.column_stack([1 - p, p])
        return np.clip(p, 1e-6, None) / np.clip(p, 1e-6, None).sum(axis=1, keepdims=True)

    def contrib(self, x: np.ndarray) -> np.ndarray:
        """Directional TreeSHAP in margin units, (n, p): up-minus-down (3 class) or class-1."""
        n, p = np.asarray(x).shape
        raw = self.booster.predict(np.asarray(x, float), pred_contrib=True)
        if self.n_classes == 2:
            return raw[:, :p]
        raw = raw.reshape(n, self.n_classes, p + 1)[:, :, :p]
        return raw[:, 2] - raw[:, 0] if self.n_classes == 3 else raw[:, -1]


def lgb_fit(x: np.ndarray, y: np.ndarray, cols: Sequence[str]) -> LGBModel:
    """Fixed-configuration LightGBM; deliberately untuned so ablations compare like with like."""
    return _lgb_fit(x, y, cols, None)


def make_lgb_fit(forbid_pair: tuple[str, str] | None = None) -> FitFn:
    """``lgb_fit`` optionally forbidding a feature pair from sharing any branch."""
    return lambda x, y, cols: _lgb_fit(x, y, cols, forbid_pair)


def _lgb_fit(x, y, cols, forbid_pair) -> LGBModel:
    import lightgbm as lgb

    k = int(max(2, np.max(y) + 1))
    params = {
        "objective": "binary" if k == 2 else "multiclass",
        "learning_rate": 0.1,
        "num_leaves": 15,
        "min_data_in_leaf": 20,
        "lambda_l2": 1.0,
        "feature_fraction": 1.0,
        "seed": SEED,
        "deterministic": True,
        "force_row_wise": True,
        "num_threads": 1,
        "verbose": -1,
    }
    if k > 2:
        params["num_class"] = k
    if forbid_pair is not None and all(c in cols for c in forbid_pair):
        a, b2 = (list(cols).index(c) for c in forbid_pair)
        allf = range(len(cols))
        params["interaction_constraints"] = [
            [i for i in allf if i != a],
            [i for i in allf if i != b2],
        ]
    b = lgb.train(
        params, lgb.Dataset(np.asarray(x, float), np.asarray(y, int)), num_boost_round=100
    )
    return LGBModel(b, tuple(cols), k)


FitFn = Callable[[np.ndarray, np.ndarray, Sequence[str]], object]


@dataclass
class OOF:
    proba: np.ndarray  # (n, K); NaN outside any test block
    mask: np.ndarray
    models: list = field(default_factory=list)  # (Fold, model) per fold
    cols: tuple[str, ...] = ()

    def loss(self, y: np.ndarray) -> np.ndarray:
        out = np.full(len(y), np.nan)
        out[self.mask] = log_loss_rows(self.proba[self.mask], np.asarray(y)[self.mask])
        return out


def fit_oof(
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Sequence[Fold],
    cols: Sequence[str],
    fit_fn: FitFn = lgb_fit,
    keep_models: bool = False,
    n_classes: int | None = None,
) -> OOF:
    k = n_classes or int(np.max(y) + 1)
    proba = np.full((len(y), k), np.nan)
    mask = np.zeros(len(y), bool)
    models = []
    xv = X[list(cols)].to_numpy(float)
    for f in folds:
        m = fit_fn(xv[f.train_pos], np.asarray(y)[f.train_pos], list(cols))
        proba[f.test_pos] = m.predict_proba(xv[f.test_pos])
        mask[f.test_pos] = True
        if keep_models:
            models.append((f, m))
    return OOF(proba, mask, models, tuple(cols))


# ---------------------------------------------------------------------------------------------
# 1. Feature-family ablations
# ---------------------------------------------------------------------------------------------


CO_PRIMARY_CLUSTERS = ("event", "dep_group", "dependence_group")


def _co_primary(names) -> list[str]:
    """Co-primary clusterings among ``names`` (event and dep_group). Sensitivities such as
    ``dep_group_season`` / ``dep_group_econ`` / ``dep_group_category_driver`` are reported but never
    enter the conservative combination; with no co-primary name present all names are used."""
    names = [
        n for n in names if not n.startswith("_") and n != "p_conservative" and n != "conservative"
    ]
    prim = [n for n in names if n in CO_PRIMARY_CLUSTERS]
    return prim or names


def _is_num(v) -> bool:
    return v is not None and not (isinstance(v, float) and np.isnan(v))


def _rank_key(v) -> float:
    """Descending-sort key: a real 0.0 is a value; only None/NaN (missing) sorts last."""
    return -float(v) if _is_num(v) else float("inf")


def conservative(boots: dict[str, dict]) -> dict:
    """Combine the co-primary cluster definitions pessimistically: the hull of the CIs and the
    larger p (sensitivity clusterings are reported alongside, not combined)."""
    keep = set(_co_primary(list(boots)))
    items = [
        v
        for k, v in boots.items()
        if k in keep and isinstance(v, dict) and v.get("mean") is not None
    ]
    if not items:
        return {"mean": None, "ci": [None, None], "p_pos": None, "n_clusters": 0}
    return {
        "mean": items[0]["mean"],
        "ci": [min(v["ci"][0] for v in items), max(v["ci"][1] for v in items)],
        "p_pos": max(v["p_pos"] for v in items),
        "n_clusters": min(v["n_clusters"] for v in items),
        "definition": "hull of CIs, max one-sided p over event and dep_group clusterings",
    }


def _all_boot(d: np.ndarray, clusters: dict[str, np.ndarray], n_boot: int, seed: int) -> dict:
    out = {name: cluster_boot(d, cl, n_boot, seed) for name, cl in clusters.items()}
    keep = set(_co_primary(list(out)))
    ps = [v["p_two_sided"] for k, v in out.items() if k in keep and v["p_two_sided"] is not None]
    out["p_conservative"] = max(ps) if ps else None  # worst two-sided p over co-primary clusterings
    out["sensitivities"] = sorted(
        k for k in out if k not in keep and not k.startswith("_") and k != "p_conservative"
    )
    out["conservative"] = conservative(out)
    return out


def benjamini_yekutieli(
    pvals: dict[str, float], m_total: int | None = None, q: float = BY_Q
) -> dict[str, dict]:
    """BY FDR (valid under dependence) with a cumulative denominator ``m_total`` >= len(pvals)."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    n = len(items)
    big = max(m_total or n, n)
    c = float(sum(1.0 / k for k in range(1, big + 1)))
    adj = np.empty(n)
    run = 1.0
    for i in range(n - 1, -1, -1):
        run = min(run, items[i][1] * big * c / (i + 1))
        adj[i] = min(1.0, run)
    return {
        name: {"p": float(p), "p_by": float(adj[i]), "pass_by": bool(adj[i] < q)}
        for i, (name, p) in enumerate(items)
    }


def later_blocks_ok(
    folds: Sequence[Fold], selection_ids: Sequence[str], judge_ids: Sequence[str]
) -> bool:
    """True if every judging block is strictly later than every block used to select."""
    if not selection_ids:
        return True
    order = {f.fold_id: i for i, f in enumerate(folds)}
    return bool(judge_ids) and min(order[j] for j in judge_ids) > max(
        order[s] for s in selection_ids
    )


def finalize_demonstration(
    entries: dict[str, dict], *, prior_tests: int = 0, q: float = BY_Q
) -> dict:
    """Attach BY and the ``demonstrated_incremental_value`` label to ``entries``.

    Each entry needs ``value`` (a ``conservative`` dict, positive = out-of-sample log-loss
    improvement), ``later_blocks_ok`` and optionally ``informative``. The label is True only if
    the conservative CI excludes 0 on the positive side AND BY at ``q`` over the cumulative set
    (this run's tests plus ``prior_tests``) passes AND the judging blocks are later than any
    block used to select. Everything else is ``descriptive_only``.
    """
    ps = {
        k: e["value"]["p_pos"]
        for k, e in entries.items()
        if e["value"].get("p_pos") is not None and e.get("informative", True)
    }
    by = benjamini_yekutieli(ps, len(ps) + prior_tests, q)
    for k, e in entries.items():
        b = by.get(k, {})
        lo = e["value"]["ci"][0]
        e["p_by"], e["pass_by"] = b.get("p_by"), bool(b.get("pass_by", False))
        e["ci_excludes_0"] = bool(lo is not None and lo > 0)
        ok = (
            e["ci_excludes_0"]
            and e["pass_by"]
            and bool(e.get("later_blocks_ok", False))
            and e.get("informative", True)
        )
        e["demonstrated_incremental_value"] = bool(ok)
        e["label"] = "demonstrated" if ok else "descriptive_only"
    return {
        "by_q": q,
        "m_tests": len(ps),
        "prior_tests": prior_tests,
        "m_total": len(ps) + prior_tests,
        "adjusted": by,
    }


def ablation_study(
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Sequence[Fold],
    family_map: dict[str, list[str]],
    baseline_features: Sequence[str],
    clusters: dict[str, np.ndarray],
    *,
    extra_units: dict[str, Sequence[str]] | None = None,
    eval_mask: np.ndarray | None = None,
    judge_fold_ids: Sequence[str] | None = None,
    selection_fold_ids: Sequence[str] = (),
    prior_tests: int = 0,
    fit_fn: FitFn = lgb_fit,
    n_boot: int = 1000,
    seed: int = SEED,
    cache: dict | None = None,
) -> dict:
    """Incremental out-of-sample value by refit: drop-one and add-one against baseline.

    Each unit (a declared family, or an ``extra_units`` single-feature unit) is refit without it
    (``drop_minus_full``) and as baseline + only it (``only_minus_baseline``), on mean per-row
    out-of-fold log loss. Positive ``delta_ll`` (= drop minus full) means the unit helps. The CI
    is the conservative hull over every clustering in ``clusters`` (event, dep_group). Only rows in
    ``eval_mask`` (default: rows of ``judge_fold_ids``, else every out-of-fold row) are judged.
    Families are declared a priori; ``extra_units`` are treated as selected on
    ``selection_fold_ids``, which must all precede ``judge_fold_ids`` to be demonstrable.
    ``rank`` orders units by ``delta_ll``; SHAP/permutation/ALE never enter the ranking.
    """
    y = np.asarray(y)
    cache = {} if cache is None else cache

    def oof_for(cols: Sequence[str]) -> OOF:
        key = tuple(cols)
        if key not in cache:
            cache[key] = fit_oof(X, y, folds, cols, fit_fn)
        return cache[key]

    in_map = set(sum(family_map.values(), []))
    all_cols = [c for c in X.columns if c in in_map | set(baseline_features)]
    base_cols = list(baseline_features)
    full, base = oof_for(all_cols), oof_for(base_cols)
    lf, lb = full.loss(y), base.loss(y)
    if eval_mask is None:
        eval_mask = np.zeros(len(y), bool)
        for f in folds:
            if judge_fold_ids is None or f.fold_id in judge_fold_ids:
                eval_mask[f.test_pos] = True
    ev = np.asarray(eval_mask, bool) & full.mask

    def masked(d: np.ndarray) -> np.ndarray:
        return np.where(ev, d, np.nan)

    judge = list(judge_fold_ids) if judge_fold_ids is not None else [f.fold_id for f in folds]
    fam_ok = True  # declared families: nothing was selected
    feat_ok = later_blocks_ok(folds, selection_fold_ids, judge)
    units: list[tuple[str, str, list[str]]] = []
    absent = []
    for fam, cols in family_map.items():
        cols = [c for c in cols if c in X.columns]
        if fam == UNASSIGNED:
            continue
        if not cols:
            absent.append(fam)
            continue
        units.append((fam, "family", cols))
    units += [
        (n, "feature", [c for c in cs if c in X.columns]) for n, cs in (extra_units or {}).items()
    ]
    rep: dict = {
        "baseline_features": base_cols,
        "all_features": all_cols,
        "full_vs_baseline": _all_boot(masked(lb - lf), clusters, n_boot, seed),
        "mean_loss": {
            "full": float(np.nanmean(masked(lf))),
            "baseline": float(np.nanmean(masked(lb))),
        },
        "families": {},
        "features": {},
        "absent_families": absent,
        "unassigned": family_map.get(UNASSIGNED, []),
        "judge_fold_ids": judge,
        "selection_fold_ids": list(selection_fold_ids),
    }
    entries: dict[str, dict] = {}
    sse = {"baseline": lb[ev], "full": lf[ev]}
    for name, kind, cols in units:
        rest = [c for c in all_cols if c not in cols]
        if not rest or not cols:
            continue
        ld = oof_for(rest).loss(y)
        lo = oof_for(list(dict.fromkeys(base_cols + cols))).loss(y)
        sse[f"drop:{name}"], sse[f"only:{name}"] = ld[ev], lo[ev]
        drop = _all_boot(masked(ld - lf), clusters, n_boot, seed)
        only = _all_boot(masked(lo - lb), clusters, n_boot, seed)
        e = {
            "kind": kind,
            "features": cols,
            "mean_loss": {
                "drop": float(np.nanmean(masked(ld))),
                "only_plus_baseline": float(np.nanmean(masked(lo))),
            },
            "drop_minus_full": drop,
            "only_minus_baseline": only,
            "value": drop["conservative"],
            "delta_ll": drop["conservative"]["mean"],
            "add_one_delta_ll": None
            if only["conservative"]["mean"] is None
            else -only["conservative"]["mean"],
            "later_blocks_ok": fam_ok if kind == "family" else feat_ok,
        }
        (rep["families"] if kind == "family" else rep["features"])[name] = e
        entries[name] = e
    rep["relative_improvement_vs_baseline"] = compare.paired_bootstrap(
        np.asarray(next(iter(clusters.values())))[ev], sse, "baseline", n_boot=n_boot, seed=seed
    )["models"]
    rep["multiple_testing"] = finalize_demonstration(entries, prior_tests=prior_tests)
    rep["multiple_testing"]["note"] = (
        "BY (q=0.10) over the cumulative test set; p = one-sided clustered-bootstrap p for "
        "delta_ll > 0, max over cluster definitions (FEATURE_DISCOVERY_PROGRAMME triage rule)"
    )
    ranked = sorted(entries.items(), key=lambda kv: _rank_key(kv[1]["delta_ll"]))
    rep["ranking"] = [
        {
            "rank": i + 1,
            "unit": n,
            "kind": e["kind"],
            "delta_ll": e["delta_ll"],
            "ci": e["value"]["ci"],
            "p_by": e["p_by"],
            "label": e["label"],
            "demonstrated_incremental_value": e["demonstrated_incremental_value"],
        }
        for i, (n, e) in enumerate(ranked)
    ]
    rep["_full_oof"], rep["_baseline_oof"] = full, base  # popped before serialisation
    return rep


# ---------------------------------------------------------------------------------------------
# 2. Conditional permutation importance
# ---------------------------------------------------------------------------------------------


def correlated_partners(
    train: pd.DataFrame, feature: str, threshold: float = CORR_THRESHOLD
) -> list[str]:
    """Features with |Spearman| > threshold vs ``feature`` (ordered most correlated first)."""
    c = train.corr(method="spearman")[feature].drop(feature).abs().dropna()
    return list(c[c > threshold].sort_values(ascending=False).index)


def _strata(x_test: pd.DataFrame, partner: str | None, n_bins: int) -> np.ndarray:
    if partner is None:
        return np.zeros(len(x_test), int)
    v = x_test[partner]
    return (
        pd.qcut(v.rank(method="first"), q=min(n_bins, max(1, len(v) // 10)), labels=False)
        .fillna(-1)
        .to_numpy(int)
    )


def _permute_within(x: np.ndarray, strata: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    out = x.copy()
    for s in np.unique(strata):
        idx = np.flatnonzero(strata == s)
        out[idx] = x[rng.permutation(idx)]
    return out


def conditional_permutation_importance(
    X: pd.DataFrame,
    y: np.ndarray,
    oof: OOF,
    clusters: dict[str, np.ndarray],
    *,
    features: Sequence[str] | None = None,
    n_bins: int = 8,
    n_repeats: int = 3,
    n_boot: int = 1000,
    seed: int = SEED,
) -> dict:
    """Increase in out-of-fold log loss when a feature is permuted within strata of its
    correlated partners (conditional) versus globally (marginal). Test folds only.
    """
    y = np.asarray(y)
    cols = list(oof.cols)
    feats = list(features) if features is not None else cols
    n = len(y)
    cond = {f: np.full(n, np.nan) for f in feats}
    marg = {f: np.full(n, np.nan) for f in feats}
    partners_used: dict[str, list[str]] = {}
    rng = np.random.default_rng(seed)
    for fold, model in oof.models:
        tr_sub = X.iloc[fold.train_pos][cols]
        if len(tr_sub) > 5000:
            tr_sub = tr_sub.sample(5000, random_state=seed)
        xt = X.iloc[fold.test_pos][cols].reset_index(drop=True)
        yt = y[fold.test_pos]
        base_loss = log_loss_rows(model.predict_proba(xt.to_numpy(float)), yt)
        for f in feats:
            partners = correlated_partners(tr_sub, f)
            partners_used.setdefault(f, partners)
            strata = _strata(xt, partners[0] if partners else None, n_bins)
            xv = xt[f].to_numpy(float)
            for store, st in ((cond, strata), (marg, np.zeros(len(xt), int))):
                acc = np.zeros(len(xt))
                for _ in range(n_repeats):
                    xp = xt.copy()
                    xp[f] = _permute_within(xv, st, rng)
                    acc += log_loss_rows(model.predict_proba(xp.to_numpy(float)), yt) - base_loss
                store[f][fold.test_pos] = acc / n_repeats
    out = {}
    for f in feats:
        out[f] = {
            "partners_over_threshold": partners_used.get(f, []),
            "conditional": _all_boot(cond[f], clusters, n_boot, seed),
            "marginal": _all_boot(marg[f], clusters, n_boot, seed),
        }
    return {
        "features": out,
        "corr_threshold": CORR_THRESHOLD,
        "n_bins": n_bins,
        "n_repeats": n_repeats,
        "note": "drop in out-of-fold log loss; conditional = permuted within strata of the "
        "most correlated partner. Marginal is shown only to expose redundancy.",
    }


# ---------------------------------------------------------------------------------------------
# 3. ALE
# ---------------------------------------------------------------------------------------------


def ale_edges(values: np.ndarray, n_bins: int = 20) -> np.ndarray:
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    e = np.unique(np.quantile(v, np.linspace(0, 1, n_bins + 1)))
    return e if len(e) >= 2 else np.array([e[0] - 0.5, e[0] + 0.5])


def _ale_local(
    model, x: pd.DataFrame, feature: str, edges: np.ndarray, score
) -> tuple[np.ndarray, np.ndarray]:
    nb = len(edges) - 1
    v = x[feature].to_numpy(float)
    ok = np.isfinite(v)
    b = np.clip(np.searchsorted(edges, v, side="right") - 1, 0, nb - 1)
    sums, counts = np.zeros(nb), np.zeros(nb)
    for k in range(nb):
        rows = np.flatnonzero(ok & (b == k))
        if len(rows) == 0:
            continue
        lo, hi = x.iloc[rows].copy(), x.iloc[rows].copy()
        lo[feature], hi[feature] = edges[k], edges[k + 1]
        d = score(model.predict_proba(hi.to_numpy(float))) - score(
            model.predict_proba(lo.to_numpy(float))
        )
        sums[k], counts[k] = d.sum(), len(rows)
    return sums, counts


def _ale_curve(sums: np.ndarray, counts: np.ndarray) -> np.ndarray:
    eff = np.divide(sums, counts, out=np.zeros_like(sums), where=counts > 0)
    acc = np.concatenate([[0.0], np.cumsum(eff)])
    mid = 0.5 * (acc[:-1] + acc[1:])
    return acc - (mid * counts).sum() / max(counts.sum(), 1.0)


def ale_study(
    X: pd.DataFrame,
    oof: OOF,
    features: Sequence[str],
    *,
    n_bins: int = 20,
    score: Callable[[np.ndarray], np.ndarray] = score_from_proba,
) -> dict:
    """First-order ALE curves (as data) pooled over fold models on their own test rows."""
    out = {}
    cols = list(oof.cols)
    for f in features:
        edges = ale_edges(X.iloc[np.flatnonzero(oof.mask)][f].to_numpy(float), n_bins)
        tot_s, tot_c, folds = np.zeros(len(edges) - 1), np.zeros(len(edges) - 1), {}
        for fold, model in oof.models:
            s, c = _ale_local(
                model, X.iloc[fold.test_pos][cols].reset_index(drop=True), f, edges, score
            )
            tot_s += s
            tot_c += c
            folds[fold.fold_id] = [float(v) for v in _ale_curve(s, c)]
        curve = _ale_curve(tot_s, tot_c)
        out[f] = {
            "edges": [float(e) for e in edges],
            "ale": [float(v) for v in curve],
            "counts": [int(c) for c in tot_c],
            "range": float(curve.max() - curve.min()),
            "fold_curves": folds,
        }
    return {
        "features": out,
        "score": "P(up)-P(down) for 3 classes, else P(class 1)",
        "note": "ALE is preferred to PDP for correlated features; still a description of the "
        "fitted model, not a causal effect.",
    }


# ---------------------------------------------------------------------------------------------
# 4. Interactions
# ---------------------------------------------------------------------------------------------


def _h2(model, xb: np.ndarray, j: int, k: int, m: int, score) -> float:
    """Friedman H^2 for the pair (j, k) from partial dependence on an m-row background."""
    xs = xb[:m]
    n = len(xs)

    def pd_grid(cols: tuple[int, ...]) -> np.ndarray:
        # PD at each sample point i (values of ``cols`` from row i), averaged over background rows
        out = np.empty(n)
        for i in range(n):
            z = xs.copy()
            z[:, list(cols)] = xs[i, list(cols)]
            out[i] = score(model.predict_proba(z)).mean()
        return out

    pj, pk, pjk = pd_grid((j,)), pd_grid((k,)), pd_grid((j, k))
    pj, pk, pjk = pj - pj.mean(), pk - pk.mean(), pjk - pjk.mean()
    den = float((pjk**2).sum())
    return float(((pjk - pj - pk) ** 2).sum() / den) if den > 0 else 0.0


def interaction_study(
    X: pd.DataFrame,
    oof: OOF,
    features: Sequence[str],
    *,
    m: int = 60,
    top_pairs: int = 10,
    score: Callable[[np.ndarray], np.ndarray] = score_from_proba,
    seed: int = SEED,
    fold_ids: Sequence[str] | None = None,
) -> dict:
    """Pairwise interaction strength on out-of-fold test rows.

    LightGBM exposes no interaction pred_contrib and ``shap`` is only used if installed, so the
    primary measure is Friedman's H^2 on the fold models (share of the pair's joint partial
    dependence not explained by the two main effects). H^2 is a model-based, uncalibrated
    ranking: a high pair is a lead to test, not a finding. ``shap_available`` is reported.
    """
    cols = list(oof.cols)
    idx = {c: i for i, c in enumerate(cols)}
    rng = np.random.default_rng(seed)
    pairs: dict[tuple[str, str], list[float]] = {}
    for fold, model in oof.models:
        if fold_ids is not None and fold.fold_id not in fold_ids:
            continue
        xt = X.iloc[fold.test_pos][cols].to_numpy(float)
        xb = xt[rng.permutation(len(xt))[:m]]
        for a in range(len(features)):
            for b in range(a + 1, len(features)):
                fa, fb = features[a], features[b]
                pairs.setdefault((fa, fb), []).append(_h2(model, xb, idx[fa], idx[fb], m, score))
    ranked = sorted(((float(np.mean(v)), p, v) for p, v in pairs.items()), reverse=True)[:top_pairs]
    return {
        "method": "friedman_h2_on_fold_models",
        "background_rows": m,
        "shap_available": importlib.util.find_spec("shap") is not None,
        "top_pairs": [
            {"pair": list(p), "h2_mean": mean, "h2_by_fold": [float(x) for x in v]}
            for mean, p, v in ranked
        ],
        "fold_ids": None if fold_ids is None else list(fold_ids),
        "note": "H^2 is a discovery lead only (descriptive). An interaction counts as "
        "demonstrated only via interaction_validation on later blocks.",
    }


# ---------------------------------------------------------------------------------------------
# 5. Regimes (declared up front)
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RegimeSpec:
    name: str
    column: str
    kind: str  # "edges" | "quantile" | "categorical"
    edges: tuple[float, ...] = ()
    labels: tuple[str, ...] = ()


# Real ml_panel column names: ``mid_i`` (panel origin mid), ``ml_log_hours_to_end`` (log1p of
# hours to end_date), ``ml_log1p_liq`` (log1p liquidity; tercile cuts are rank-based so the log
# is immaterial) and ``fee_category``. Edges for hours are log1p(24, 168, 720).
DECLARED_REGIMES: tuple[RegimeSpec, ...] = (
    RegimeSpec("price_extremity", "mid_i", "edges", (0.1, 0.9), ("<0.1", "0.1-0.9", ">0.9")),
    RegimeSpec(
        "time_to_resolution",
        "ml_log_hours_to_end",
        "edges",
        (float(np.log1p(24.0)), float(np.log1p(168.0)), float(np.log1p(720.0))),
        ("<24h", "24h-7d", "7d-30d", ">30d"),
    ),
    RegimeSpec("liquidity", "ml_log1p_liq", "quantile", (1 / 3, 2 / 3), ("low", "mid", "high")),
    RegimeSpec("category", "fee_category", "categorical"),
)


def regime_declaration_hash(specs: Sequence[RegimeSpec] = DECLARED_REGIMES) -> str:
    blob = json.dumps([[s.name, s.column, s.kind, list(s.edges), list(s.labels)] for s in specs])
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def assign_regime(spec: RegimeSpec, values: pd.Series) -> pd.Series:
    """Label rows. Edge bins are right-open at the upper edge: [lo, hi). Missing -> 'missing'."""
    if spec.kind == "categorical":
        return values.astype("object").where(values.notna(), "missing").astype(str)
    v = values.astype(float)
    if spec.kind == "quantile":
        cuts = np.nanquantile(v, spec.edges)
    else:
        cuts = np.asarray(spec.edges, float)
    # (-inf, c0): 0 ; [c0, c1): 1 ; ...
    code = np.searchsorted(cuts, v.to_numpy(), side="right")
    lab = np.asarray(spec.labels, object)[np.clip(code, 0, len(spec.labels) - 1)]
    return pd.Series(np.where(v.isna(), "missing", lab), index=values.index)


def regime_study(
    frame: pd.DataFrame,
    y: np.ndarray,
    full: OOF,
    base: OOF,
    clusters: dict[str, np.ndarray],
    family_map: dict[str, list[str]],
    X: pd.DataFrame,
    *,
    specs: Sequence[RegimeSpec] = DECLARED_REGIMES,
    discovery_mask: np.ndarray | None = None,
    judge_mask: np.ndarray | None = None,
    later_ok: bool = False,
    prior_tests: int = 0,
    n_boot: int = 1000,
    seed: int = SEED,
    with_shap: bool = True,
) -> dict:
    """Value of the full model over baseline by pre-declared regime: discover early, judge late.

    ``baseline_minus_full`` log loss is computed per cell on ``judge_mask`` rows (later blocks);
    the same cell on ``discovery_mask`` rows gives ``early_mean`` and a sign-stability check. A
    cell is ``demonstrated`` only if informative (>= 50 clusters under every clustering on the
    judging rows), its conservative CI excludes 0, the early sign agrees, it passes BY over the
    cumulative cell set, and ``later_ok`` (judging blocks later than discovery blocks) holds.
    Without a declared split (``later_ok`` False) nothing can be demonstrated. SHAP by family is a
    descriptive column only.
    """
    y = np.asarray(y)
    lf, lb = full.loss(y), base.loss(y)
    delta = lb - lf  # positive = full model better
    judge = full.mask if judge_mask is None else (np.asarray(judge_mask, bool) & full.mask)
    early = (
        np.zeros(len(y), bool) if discovery_mask is None else np.asarray(discovery_mask, bool)
    ) & full.mask
    fam_abs = None
    if with_shap and full.models and hasattr(full.models[0][1], "contrib"):
        cols = list(full.cols)
        fam_abs = {}
        mat = np.full((len(y), len(cols)), np.nan)
        for fold, model in full.models:
            mat[fold.test_pos] = np.abs(model.contrib(X.iloc[fold.test_pos][cols].to_numpy(float)))
        for fam, fc in family_map.items():
            ix = [cols.index(c) for c in fc if c in cols]
            if ix:
                fam_abs[fam] = mat[:, ix].sum(axis=1)
    out: dict = {
        "declaration_hash": regime_declaration_hash(specs),
        "regimes": {},
        "min_clusters": MIN_CLUSTERS,
        "later_blocks_ok": bool(later_ok),
    }
    entries: dict[str, dict] = {}
    for spec in specs:
        if spec.column not in frame.columns:
            out["regimes"][spec.name] = {"unavailable": f"column {spec.column!r} not in frame"}
            continue
        lab = assign_regime(spec, frame[spec.column]).to_numpy()
        cells = {}
        for level in pd.unique(lab):
            sel = (lab == level) & judge
            if not sel.any():
                continue
            ncl = {n: int(pd.Series(np.asarray(c)[sel]).nunique()) for n, c in clusters.items()}
            d_j = np.where(sel, delta, np.nan)
            boots = {n: cluster_boot(d_j, c, n_boot, seed) for n, c in clusters.items()}
            cons = conservative(boots)
            e_sel = (lab == level) & early
            early_mean = float(delta[e_sel].mean()) if e_sel.any() else None
            cell = {
                "n_rows": int(sel.sum()),
                "n_clusters": ncl,
                "informative": bool(min(ncl.values()) >= MIN_CLUSTERS),
                "mean_loss_full": float(lf[sel].mean()),
                "mean_loss_baseline": float(lb[sel].mean()),
                "baseline_minus_full": boots,
                "value": cons,
                "early_mean": early_mean,
                "sign_stable": bool(
                    early_mean is not None
                    and cons["mean"] is not None
                    and np.sign(early_mean) == np.sign(cons["mean"])
                    and early_mean > 0
                ),
                "later_blocks_ok": bool(later_ok),
            }
            if fam_abs is not None:
                cell["descriptive_mean_abs_shap_by_family"] = {
                    f: float(v[sel].mean()) for f, v in fam_abs.items()
                }
            cells[str(level)] = cell
            entries[f"{spec.name}={level}"] = cell
        out["regimes"][spec.name] = cells
    # sign stability is an extra gate on top of finalize_demonstration
    out["multiple_testing"] = finalize_demonstration(entries, prior_tests=prior_tests)
    for e in entries.values():
        if not e["sign_stable"]:
            e["demonstrated_incremental_value"], e["label"] = False, "descriptive_only"
    out["note"] = (
        "Regimes are declared in DECLARED_REGIMES before any result is seen. Cells with fewer "
        "than 50 clusters are uninformative and never demonstrated. A cell is demonstrated only "
        "when the full model beats the baseline on later blocks with the early sign agreeing."
    )
    return out


# ---------------------------------------------------------------------------------------------
# 6. Threshold hypotheses (discovery is separate from confirmation)
# ---------------------------------------------------------------------------------------------


class ThresholdReuseError(RuntimeError):
    """Raised when a threshold is evaluated on data it was discovered in."""


@dataclass(frozen=True)
class ThresholdHypothesis:
    feature: str
    value: float
    source: str  # "gbm_split" | "ale_changepoint"
    discovered_in: str  # fold id (development fold)
    discovery_row_ids: frozenset = field(repr=False, default=frozenset())
    discovery_clusters: frozenset = field(repr=False, default=frozenset())
    weight: float = 0.0
    status: str = HYPOTHESIS

    def to_dict(self) -> dict:
        ids = sorted(map(str, self.discovery_row_ids))
        return {
            "status": self.status,
            "feature": self.feature,
            "value": self.value,
            "source": self.source,
            "discovered_in": self.discovered_in,
            "weight": self.weight,
            "n_discovery_rows": len(ids),
            "discovery_rows_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest()[:16],
            "confirmation_requires": "new held-out data disjoint in rows and clusters",
        }


def _fold_rows(row_ids: np.ndarray, clusters: np.ndarray | None, pos: np.ndarray):
    rid = frozenset(np.asarray(row_ids)[pos].tolist())
    cl = frozenset(np.asarray(clusters)[pos].tolist()) if clusters is not None else frozenset()
    return rid, cl


def propose_gbm_thresholds(
    model: LGBModel,
    fold: Fold,
    row_ids: np.ndarray,
    cluster: np.ndarray | None = None,
    *,
    features: Sequence[str] | None = None,
    per_feature: int = 2,
    n_bins: int = 20,
) -> list[ThresholdHypothesis]:
    """Gain-weighted split-point clusters of a development-fold GBM, as HYPOTHESES."""
    t = model.booster.trees_to_dataframe()
    t = t[t["split_feature"].notna()].copy()
    # lightgbm names columns Column_i when fitted on a bare array
    t["split_feature"] = [
        model.cols[int(s.split("_")[-1])] if s.startswith("Column_") else s
        for s in t["split_feature"]
    ]
    rid, cl = _fold_rows(row_ids, cluster, np.concatenate([fold.train_pos, fold.test_pos]))
    out = []
    for f in features if features is not None else sorted(t["split_feature"].unique()):
        sub = t[t["split_feature"] == f]
        thr, gain = sub["threshold"].to_numpy(float), sub["split_gain"].to_numpy(float)
        if len(thr) == 0:
            continue
        lo, hi = thr.min(), thr.max()
        b = (
            np.zeros(len(thr), int)
            if hi == lo
            else np.minimum(((thr - lo) / (hi - lo) * n_bins).astype(int), n_bins - 1)
        )
        agg = [
            (gain[b == k].sum(), float(np.average(thr[b == k], weights=gain[b == k] + 1e-12)))
            for k in np.unique(b)
        ]
        total = sum(g for g, _ in agg) or 1.0
        for g, v in sorted(agg, reverse=True)[:per_feature]:
            out.append(
                ThresholdHypothesis(str(f), v, "gbm_split", fold.fold_id, rid, cl, float(g / total))
            )
    return out


def propose_ale_changepoints(
    ale: dict,
    feature: str,
    fold: Fold,
    row_ids: np.ndarray,
    cluster: np.ndarray | None = None,
    *,
    top: int = 1,
) -> list[ThresholdHypothesis]:
    """Edges where the ALE slope changes most (second difference), as HYPOTHESES."""
    e, a = np.asarray(ale["edges"], float), np.asarray(ale["ale"], float)
    if len(e) < 4:
        return []
    slope = np.diff(a) / np.maximum(np.diff(e), 1e-12)
    curv = np.abs(np.diff(slope))
    rid, cl = _fold_rows(row_ids, cluster, np.concatenate([fold.train_pos, fold.test_pos]))
    order = np.argsort(curv)[::-1][:top]
    tot = curv.sum() or 1.0
    return [
        ThresholdHypothesis(
            feature, float(e[i + 1]), "ale_changepoint", fold.fold_id, rid, cl, float(curv[i] / tot)
        )
        for i in order
    ]


def evaluate_threshold(
    h: ThresholdHypothesis,
    x: np.ndarray,
    target: np.ndarray,
    row_ids: np.ndarray,
    clusters: np.ndarray,
    *,
    eval_label: str,
    n_boot: int = 1000,
    seed: int = SEED,
) -> dict:
    """Confirmatory contrast of ``target`` above vs below ``h.value`` on NEW held-out data.

    Refuses (``ThresholdReuseError``) if the evaluation label equals the discovery fold, if any
    evaluation row was part of the discovery fold, or if any evaluation cluster (event /
    dependence group) appeared in the discovery fold.
    """
    if eval_label == h.discovered_in:
        raise ThresholdReuseError(
            f"threshold discovered in {h.discovered_in!r}; cannot evaluate in it"
        )
    rows = set(np.asarray(row_ids).tolist())
    if rows & h.discovery_row_ids:
        raise ThresholdReuseError(
            f"{len(rows & h.discovery_row_ids)} evaluation rows overlap the discovery fold"
        )
    cl = set(np.asarray(clusters).tolist())
    if cl & h.discovery_clusters:
        raise ThresholdReuseError(
            f"{len(cl & h.discovery_clusters)} evaluation clusters overlap the discovery fold"
        )
    x, target = np.asarray(x, float), np.asarray(target, float)
    above = x > h.value
    ok = np.isfinite(x) & np.isfinite(target)
    # difference of means via a per-row centred contrast: mean(target|above) - mean(target|below)
    a, b = ok & above, ok & ~above
    if not a.any() or not b.any():
        return {"status": "uninformative", "reason": "one side empty", "hypothesis": h.to_dict()}
    codes, uniq = pd.factorize(np.asarray(clusters)[ok])
    k = len(uniq)
    t, ab = target[ok], above[ok]
    sa = np.bincount(codes, weights=t * ab, minlength=k)
    na = np.bincount(codes, weights=ab.astype(float), minlength=k)
    sb = np.bincount(codes, weights=t * ~ab, minlength=k)
    nb = np.bincount(codes, weights=(~ab).astype(float), minlength=k)
    rng = np.random.default_rng(seed)
    diffs = []
    for _ in range(n_boot):
        i = rng.integers(0, k, size=k)
        if na[i].sum() > 0 and nb[i].sum() > 0:
            diffs.append(sa[i].sum() / na[i].sum() - sb[i].sum() / nb[i].sum())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "status": "confirmatory_evaluation",
        "eval_label": eval_label,
        "hypothesis": h.to_dict(),
        "diff_above_minus_below": float(target[a].mean() - target[b].mean()),
        "ci": [float(lo), float(hi)],
        "n_above": int(a.sum()),
        "n_below": int(b.sum()),
        "n_clusters": int(k),
    }


# ---------------------------------------------------------------------------------------------
# Orchestration and search accounting
# ---------------------------------------------------------------------------------------------


def interaction_validation(
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Sequence[Fold],
    cols: Sequence[str],
    pairs: Sequence[Sequence[str]],
    clusters: dict[str, np.ndarray],
    *,
    discovery_fold_ids: Sequence[str],
    judge_fold_ids: Sequence[str],
    prior_tests: int = 0,
    n_boot: int = 1000,
    seed: int = SEED,
    cache: dict | None = None,
) -> dict:
    """Judge pairs found on early blocks by later-block out-of-sample value.

    Compares a GBM forbidden from using the pair together in any branch (LightGBM
    ``interaction_constraints``) against the unconstrained GBM, refit per fold. ``delta_ll`` is
    constrained minus free log loss on judging rows: positive means allowing the interaction
    helps. A pair is demonstrated only if the conservative CI excludes 0, BY passes over the
    cumulative set, and the judging blocks are later than the discovery blocks.
    """
    y = np.asarray(y)
    cache = {} if cache is None else cache
    key = tuple(cols)
    if key not in cache:
        cache[key] = fit_oof(X, y, folds, cols)
    free = cache[key]
    ev = np.zeros(len(y), bool)
    for f in folds:
        if f.fold_id in judge_fold_ids:
            ev[f.test_pos] = True
    ev &= free.mask
    ok = later_blocks_ok(folds, discovery_fold_ids, judge_fold_ids)
    lf = free.loss(y)
    entries = {}
    for a, b in pairs:
        con = fit_oof(X, y, folds, cols, make_lgb_fit(forbid_pair=(a, b)))
        d = np.where(ev, con.loss(y) - lf, np.nan)
        boots = _all_boot(d, clusters, n_boot, seed)
        entries[f"{a}x{b}"] = {
            "pair": [a, b],
            "value": boots["conservative"],
            "delta_ll": boots["conservative"]["mean"],
            "by_cluster": {k: v for k, v in boots.items() if k in clusters},
            "later_blocks_ok": ok,
            "test": "constrained GBM (pair forbidden) vs free GBM, later blocks",
        }
    mt = finalize_demonstration(entries, prior_tests=prior_tests)
    return {
        "pairs": entries,
        "multiple_testing": mt,
        "discovery_fold_ids": list(discovery_fold_ids),
        "judge_fold_ids": list(judge_fold_ids),
    }


def threshold_value(
    h: ThresholdHypothesis,
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Sequence[Fold],
    cols: Sequence[str],
    clusters: dict[str, np.ndarray],
    *,
    judge_fold_ids: Sequence[str],
    row_ids: np.ndarray,
    n_boot: int = 1000,
    seed: int = SEED,
) -> dict:
    """Later-block out-of-sample ΔLL from adding the indicator ``X[feature] > value``.

    Refuses to value a threshold on its discovery fold or on rows it was discovered in; rows whose
    event/cluster appeared in the discovery fold are dropped (counted) rather than reused.
    """
    y = np.asarray(y)
    if h.discovered_in in judge_fold_ids:
        raise ThresholdReuseError(
            f"threshold discovered in {h.discovered_in!r}; cannot judge in it"
        )
    ev = np.zeros(len(y), bool)
    for f in folds:
        if f.fold_id in judge_fold_ids:
            ev[f.test_pos] = True
    if set(np.asarray(row_ids)[ev].tolist()) & h.discovery_row_ids:
        raise ThresholdReuseError("evaluation rows overlap the discovery fold")
    first = np.asarray(next(iter(clusters.values())))
    overlap = (
        np.isin(first, list(h.discovery_clusters))
        if h.discovery_clusters
        else np.zeros(len(y), bool)
    )
    n_excl = int((ev & overlap).sum())
    ev &= ~overlap
    xi = X.copy()
    name = f"thr:{h.feature}>{h.value:.6g}"
    v = xi[h.feature].to_numpy(float)
    xi[name] = np.where(np.isnan(v), np.nan, (v > h.value).astype(float))
    base = fit_oof(xi, y, folds, list(cols))
    with_t = fit_oof(xi, y, folds, [*cols, name])
    d = np.where(ev & base.mask, base.loss(y) - with_t.loss(y), np.nan)
    boots = _all_boot(d, clusters, n_boot, seed)
    return {
        "hypothesis": h.to_dict(),
        "value": boots["conservative"],
        "delta_ll": boots["conservative"]["mean"],
        "n_rows_excluded_cluster_overlap": n_excl,
        "judge_fold_ids": list(judge_fold_ids),
        "later_blocks_ok": True,
    }


def _mean_abs_shap(X: pd.DataFrame, full: OOF) -> dict[str, float]:
    cols = list(full.cols)
    acc, n = np.zeros(len(cols)), 0
    for fold, model in full.models:
        if not hasattr(model, "contrib"):
            return {}
        acc += np.abs(model.contrib(X.iloc[fold.test_pos][cols].to_numpy(float))).sum(axis=0)
        n += len(fold.test_pos)
    return {c: float(a / max(n, 1)) for c, a in zip(cols, acc, strict=True)}


def run_explain(
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Sequence[Fold],
    family_map: dict[str, list[str]],
    baseline_features: Sequence[str],
    clusters: dict[str, np.ndarray],
    *,
    frame: pd.DataFrame | None = None,
    row_ids: np.ndarray | None = None,
    fit_fn: FitFn = lgb_fit,
    top_k: int = 4,
    max_pairs: int = 5,
    max_feature_units: int = 20,
    prior_tests: int | None = None,
    n_boot: int = 1000,
    seed: int = SEED,
) -> tuple[dict, list[ThresholdHypothesis]]:
    """Run every analysis, judged by incremental out-of-sample log-loss value.

    Folds are split in time: the first half is DISCOVERY (families screened, features,
    interaction pairs and thresholds proposed), the later half is JUDGING (their ΔLL with
    cluster-bootstrap CI and BY over the cumulative set). Rankings use ΔLL only; SHAP, conditional
    permutation importance and ALE are attached as ``descriptive`` columns. Returns the JSON-safe
    result and the threshold hypotheses. Writes no file.
    """
    y = np.asarray(y)
    if len(folds) < 2:
        raise ValueError("need at least 2 folds to split discovery from judging")
    if prior_tests is None:
        prior_tests = prior_ml_explain_tests()
    h = max(1, len(folds) // 2)
    early, late = list(folds[:h]), list(folds[h:])
    eids, lids = [f.fold_id for f in early], [f.fold_id for f in late]
    cache: dict = {}
    # discovery: families, then single features inside surviving families, on early blocks
    d_fam = ablation_study(
        X,
        y,
        early and folds,
        family_map,
        baseline_features,
        clusters,
        judge_fold_ids=eids,
        fit_fn=fit_fn,
        n_boot=n_boot,
        seed=seed,
        cache=cache,
    )
    d_fam.pop("_full_oof"), d_fam.pop("_baseline_oof")
    surv = [
        f
        for f, e in d_fam["families"].items()
        if e["value"]["ci"][0] is not None and e["value"]["ci"][0] > 0
    ]
    cand = [
        c for f in surv for c in family_map[f] if c in X.columns and c not in baseline_features
    ][:max_feature_units]
    extra = {c: [c] for c in cand}
    d_feat = ablation_study(
        X,
        y,
        folds,
        family_map,
        baseline_features,
        clusters,
        extra_units=extra,
        judge_fold_ids=eids,
        fit_fn=fit_fn,
        n_boot=n_boot,
        seed=seed,
        cache=cache,
    )
    d_feat.pop("_full_oof"), d_feat.pop("_baseline_oof")
    top = [
        c
        for c in sorted(cand, key=lambda c: _rank_key(d_feat["features"][c]["delta_ll"]))
        if _is_num(d_feat["features"][c]["delta_ll"]) and d_feat["features"][c]["delta_ll"] > 0
    ][:top_k]
    # judging: later blocks only
    abl = ablation_study(
        X,
        y,
        folds,
        family_map,
        baseline_features,
        clusters,
        extra_units=extra,
        judge_fold_ids=lids,
        selection_fold_ids=eids,
        prior_tests=prior_tests,
        fit_fn=fit_fn,
        n_boot=n_boot,
        seed=seed,
        cache=cache,
    )
    full, base = abl.pop("_full_oof"), abl.pop("_baseline_oof")
    full = fit_oof(X, y, folds, full.cols, fit_fn, keep_models=True)
    cache[tuple(full.cols)] = full
    cpi = conditional_permutation_importance(
        X, y, full, clusters, features=cand or None, n_boot=n_boot, seed=seed
    )
    shap = _mean_abs_shap(X, full)
    ale = ale_study(X, full, top) if top else {"features": {}}
    first = next(iter(clusters))
    for r in abl["ranking"]:
        c = r["unit"]
        fam_cols = family_map.get(c) or [c]
        r["descriptive"] = {
            "mean_abs_shap": float(sum(shap.get(k, 0.0) for k in fam_cols)) if shap else None,
            "conditional_permutation": (
                cpi["features"].get(c, {}).get("conditional", {}).get(first, {}).get("mean")
            ),
            "ale_range": ale["features"].get(c, {}).get("range"),
            "note": "descriptive only; not used for ranking or labelling",
        }
    hyps: list[ThresholdHypothesis] = []
    interactions = {"discovery": None, "validation": None}
    thresholds = []
    if len(top) >= 2:
        disc = interaction_study(X, full, top, seed=seed, fold_ids=eids)
        pairs = [p["pair"] for p in disc["top_pairs"][:max_pairs]]
        interactions = {
            "discovery": disc,
            "validation": interaction_validation(
                X,
                y,
                folds,
                list(full.cols),
                pairs,
                clusters,
                discovery_fold_ids=eids,
                judge_fold_ids=lids,
                prior_tests=prior_tests,
                n_boot=n_boot,
                seed=seed,
                cache=cache,
            ),
        }
    ids = np.arange(len(y)) if row_ids is None else np.asarray(row_ids)
    for fold, model in full.models:
        if fold.fold_id in eids and hasattr(model, "booster") and top:
            hyps += propose_gbm_thresholds(
                model, fold, ids, clusters[first], features=top, per_feature=1
            )
    entries = {}
    for hy in hyps:
        tv = threshold_value(
            hy,
            X,
            y,
            folds,
            list(full.cols),
            clusters,
            judge_fold_ids=lids,
            row_ids=ids,
            n_boot=n_boot,
            seed=seed,
        )
        entries[f"{hy.feature}@{hy.value:.4g}#{hy.discovered_in}"] = tv
    thr_mt = finalize_demonstration(entries, prior_tests=prior_tests) if entries else None
    thresholds = {"values": entries, "multiple_testing": thr_mt}
    n_tests = (
        len(abl["ranking"])
        + len(d_fam["families"])
        + len(d_feat["features"])
        + len((interactions["validation"] or {}).get("pairs", {}))
        + len(entries)
    )
    res = {
        "kind": KIND,
        "label": LABEL,
        "n_rows": int(len(y)),
        "n_folds": len(folds),
        "fold_ids": [f.fold_id for f in folds],
        "discovery_fold_ids": eids,
        "judge_fold_ids": lids,
        "cluster_definitions": list(clusters),
        "ranking_key": "incremental out-of-sample delta log loss (refit), conservative CI",
        "ablation": abl,
        "discovery_ablation": {"families": d_fam["ranking"], "features": d_feat["ranking"]},
        "top_features": top,
        "descriptive": {"conditional_permutation": cpi, "ale": ale, "mean_abs_shap": shap},
        "interactions": interactions,
        "thresholds": thresholds,
        "threshold_hypotheses": [x.to_dict() for x in hyps],
        "n_tests": int(n_tests),
        "prior_tests": int(prior_tests),
    }
    if frame is not None:
        mask_e, mask_l = np.zeros(len(y), bool), np.zeros(len(y), bool)
        for f in early:
            mask_e[f.test_pos] = True
        for f in late:
            mask_l[f.test_pos] = True
        res["regimes"] = regime_study(
            frame,
            y,
            full,
            base,
            clusters,
            family_map,
            X,
            discovery_mask=mask_e,
            judge_mask=mask_l,
            later_ok=True,
            prior_tests=prior_tests,
            n_boot=n_boot,
            seed=seed,
        )
        res["n_tests"] += len(res["regimes"]["multiple_testing"]["adjusted"])
    res["n_tests_by_family"] = tests_by_family(res, family_map)
    res["interpretation_caveat"] = (
        "Only entries labelled demonstrated have shown incremental out-of-sample value on later "
        "blocks (CI excludes 0, BY q=0.10 over the cumulative set). SHAP, permutation importance "
        "and ALE describe the fitted model and never rank or label. Thresholds are hypotheses; "
        "nothing here is an edge claim."
    )
    return res, hyps


def prior_ml_explain_tests(path: Path = provenance.TRIALS_PATH) -> int:
    """Cumulative number of tests already logged by ml_explain runs (BY denominator carry-over),
    the sum of ``provenance.cumulative_tests_by_family``."""
    return int(sum(provenance.cumulative_tests_by_family(path, KIND).values()))


def tests_by_family(res: dict, family_map: dict[str, list[str]]) -> dict[str, int]:
    """Attribute this run's ``n_tests`` to families (sums exactly to ``n_tests``).

    Family and feature units go to their family; interactions, thresholds and regimes go to
    ``interaction`` / ``threshold:<family>`` / ``regime``.
    """
    inv = {c: f for f, cols in family_map.items() for c in cols}
    out: dict[str, int] = {}

    def add(k: str, n: int = 1) -> None:
        if n:
            out[k] = out.get(k, 0) + n

    def of(unit: str) -> str:
        return unit if unit in family_map else inv.get(unit, UNASSIGNED)

    for r in res["ablation"]["ranking"]:
        add(of(r["unit"]))
    for u in res["discovery_ablation"]["families"]:  # rankings; count by their own kind
        if u.get("kind", "family") == "family":
            add(of(u["unit"]))
    for u in res["discovery_ablation"]["features"]:
        if u.get("kind", "feature") == "feature":
            add(of(u["unit"]))
    add("interaction", len((res["interactions"].get("validation") or {}).get("pairs", {})))
    for k in res["thresholds"]["values"]:
        add("threshold:" + of(k.split("@")[0]))
    reg = (res.get("regimes") or {}).get("multiple_testing", {}).get("adjusted", {})
    add("regime", len(reg))
    drift = res["n_tests"] - sum(out.values())
    add("_other", drift) if drift > 0 else None
    return out


def trial_record(result: dict) -> dict:
    """Compact trial-log record: ΔLL ranking with labels, interactions, counts."""
    abl = result["ablation"]
    inter = (result["interactions"] or {}).get("validation") or {}
    return {
        "kind": KIND,
        "label": LABEL,
        "n_rows": result["n_rows"],
        "n_folds": result["n_folds"],
        "discovery_fold_ids": result["discovery_fold_ids"],
        "judge_fold_ids": result["judge_fold_ids"],
        "cluster_definitions": result["cluster_definitions"],
        "ranking": [
            {k: r[k] for k in ("rank", "unit", "kind", "delta_ll", "ci", "p_by", "label")}
            for r in abl["ranking"]
        ],
        "absent_families": abl["absent_families"],
        "multiple_testing": {
            k: abl["multiple_testing"][k] for k in ("by_q", "m_tests", "prior_tests", "m_total")
        },
        "n_tests": result["n_tests"],
        "n_tests_by_family": result.get("n_tests_by_family") or {},
        "top_features": result["top_features"],
        "interaction_labels": {k: v["label"] for k, v in inter.get("pairs", {}).items()},
        "n_threshold_hypotheses": len(result["threshold_hypotheses"]),
        "note": result["interpretation_caveat"],
    }


def log_trial(
    result: dict,
    path: Path = provenance.TRIALS_PATH,
    extra: dict | None = None,
    evidence_role: str | None = None,
) -> dict:
    """Append this explain run to the trial log (kind ml_explain, label EXPLORATORY)."""
    rec = {
        **trial_record(result),
        **(extra or {}),
        "evidence_role": evidence_role,  # required for kind ml_explain (provenance validates)
        "provenance": provenance.run_provenance([Path(__file__)]),
    }
    return provenance.append_trial(rec, path=path)


__all__ = [
    "Fold",
    "OOF",
    "RegimeSpec",
    "ThresholdHypothesis",
    "ThresholdReuseError",
    "ablation_study",
    "ale_study",
    "assign_families",
    "assign_regime",
    "cluster_boot",
    "conditional_permutation_importance",
    "evaluate_threshold",
    "fit_oof",
    "folds_from_manifest",
    "holm",
    "interaction_study",
    "interaction_validation",
    "threshold_value",
    "benjamini_yekutieli",
    "finalize_demonstration",
    "make_lgb_fit",
    "prior_ml_explain_tests",
    "tests_by_family",
    "log_trial",
    "propose_ale_changepoints",
    "propose_gbm_thresholds",
    "regime_study",
    "run_explain",
    "trial_record",
]
