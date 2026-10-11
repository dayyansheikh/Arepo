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
    "flow": ("flow_", "trade_", "ofi", "turnover"),
    "wallet": ("wallet_", "w_"),
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
        return {"mean": None, "ci": [None, None], "p_two_sided": None, "n_rows": 0, "n_clusters": 0}
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


def _all_boot(d: np.ndarray, clusters: dict[str, np.ndarray], n_boot: int, seed: int) -> dict:
    out = {name: cluster_boot(d, cl, n_boot, seed) for name, cl in clusters.items()}
    ps = [v["p_two_sided"] for v in out.values() if v["p_two_sided"] is not None]
    out["p_conservative"] = max(ps) if ps else None  # worst p over the cluster definitions
    return out


def ablation_study(
    X: pd.DataFrame,
    y: np.ndarray,
    folds: Sequence[Fold],
    family_map: dict[str, list[str]],
    baseline_features: Sequence[str],
    clusters: dict[str, np.ndarray],
    *,
    fit_fn: FitFn = lgb_fit,
    n_boot: int = 1000,
    seed: int = SEED,
) -> dict:
    """Refit with each family dropped, and with baseline + only that family.

    Differences are mean per-row out-of-fold log loss: positive ``drop_minus_full`` means removing
    the family hurts; negative ``only_minus_baseline`` means adding the family to the baseline
    helps. Cluster-bootstrap CI for every cluster definition in ``clusters`` (event, dep_group).
    """
    y = np.asarray(y)
    all_cols = [
        c for c in X.columns if c in set(sum(family_map.values(), [])) | set(baseline_features)
    ]
    base_cols = list(baseline_features)
    full = fit_oof(X, y, folds, all_cols, fit_fn)
    base = fit_oof(X, y, folds, base_cols, fit_fn)
    lf, lb = full.loss(y), base.loss(y)
    primary = next(iter(clusters))
    rep = {
        "baseline_features": base_cols,
        "all_features": all_cols,
        "full_vs_baseline": _all_boot(lb - lf, clusters, n_boot, seed),
        "mean_loss": {"full": float(np.nanmean(lf)), "baseline": float(np.nanmean(lb))},
        "families": {},
        "absent_families": [],
        "unassigned": family_map.get(UNASSIGNED, []),
    }
    sse = {"baseline": lb[full.mask], "full": lf[full.mask]}
    for fam, cols in family_map.items():
        cols = [c for c in cols if c in X.columns]
        if fam == UNASSIGNED:
            continue
        if not cols:
            rep["absent_families"].append(fam)
            continue
        rest = [c for c in all_cols if c not in cols]
        if not rest:
            rep["families"][fam] = {
                "features": cols,
                "skipped": "removing the family leaves no features",
            }
            continue
        only_cols = list(dict.fromkeys(base_cols + cols))
        drop = fit_oof(X, y, folds, rest, fit_fn)
        only = fit_oof(X, y, folds, only_cols, fit_fn)
        ld, lo = drop.loss(y), only.loss(y)
        sse[f"drop:{fam}"], sse[f"only:{fam}"] = ld[full.mask], lo[full.mask]
        rep["families"][fam] = {
            "features": cols,
            "mean_loss": {
                "drop": float(np.nanmean(ld)),
                "only_plus_baseline": float(np.nanmean(lo)),
            },
            "drop_minus_full": _all_boot(ld - lf, clusters, n_boot, seed),
            "only_minus_baseline": _all_boot(lo - lb, clusters, n_boot, seed),
            "only_minus_full": _all_boot(lo - lf, clusters, n_boot, seed),
        }
    rep["relative_improvement_vs_baseline"] = compare.paired_bootstrap(
        np.asarray(clusters[primary])[full.mask], sse, "baseline", n_boot=n_boot, seed=seed
    )["models"]
    rep["multiple_testing"] = {
        "drop_minus_full": holm(
            {
                f: v["drop_minus_full"]["p_conservative"]
                for f, v in rep["families"].items()
                if "drop_minus_full" in v and v["drop_minus_full"]["p_conservative"] is not None
            }
        ),
        "only_minus_baseline": holm(
            {
                f: v["only_minus_baseline"]["p_conservative"]
                for f, v in rep["families"].items()
                if "only_minus_baseline" in v
                and v["only_minus_baseline"]["p_conservative"] is not None
            }
        ),
        "note": "Holm within the declared family set; p = max over cluster definitions",
    }
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
        "note": "H^2 is not a significance test; confirm any interaction by a refit with the "
        "interaction removed on held-out data.",
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


DECLARED_REGIMES: tuple[RegimeSpec, ...] = (
    RegimeSpec("price_extremity", "mid", "edges", (0.1, 0.9), ("<0.1", "0.1-0.9", ">0.9")),
    RegimeSpec(
        "time_to_resolution",
        "hours_to_end",
        "edges",
        (24.0, 168.0, 720.0),
        ("<24h", "24h-7d", "7d-30d", ">30d"),
    ),
    RegimeSpec("liquidity", "liquidity", "quantile", (1 / 3, 2 / 3), ("low", "mid", "high")),
    RegimeSpec("category", "category", "categorical"),
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
    n_boot: int = 1000,
    seed: int = SEED,
    with_shap: bool = True,
) -> dict:
    """Performance (full minus baseline log loss) and family SHAP by pre-declared regime.

    ``frame`` carries the regime columns (aligned with ``y``); regimes with a missing column are
    reported as unavailable. Cells with fewer than ``MIN_CLUSTERS`` clusters (under ANY cluster
    definition) are flagged uninformative.
    """
    y = np.asarray(y)
    lf, lb = full.loss(y), base.loss(y)
    delta = lb - lf  # positive = full model better
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
    }
    for spec in specs:
        if spec.column not in frame.columns:
            out["regimes"][spec.name] = {"unavailable": f"column {spec.column!r} not in frame"}
            continue
        lab = assign_regime(spec, frame[spec.column]).to_numpy()
        cells = {}
        for level in pd.unique(lab):
            sel = (lab == level) & full.mask
            if not sel.any():
                continue
            ncl = {
                name: int(pd.Series(np.asarray(cl)[sel]).nunique()) for name, cl in clusters.items()
            }
            cell = {
                "n_rows": int(sel.sum()),
                "n_clusters": ncl,
                "informative": bool(min(ncl.values()) >= MIN_CLUSTERS),
                "mean_loss_full": float(lf[sel].mean()),
                "mean_loss_baseline": float(lb[sel].mean()),
                "baseline_minus_full": {
                    name: cluster_boot(delta[sel], np.asarray(cl)[sel], n_boot, seed)
                    for name, cl in clusters.items()
                },
            }
            if fam_abs is not None:
                cell["mean_abs_shap_by_family"] = {
                    f: float(v[sel].mean()) for f, v in fam_abs.items()
                }
            cells[str(level)] = cell
        out["regimes"][spec.name] = cells
    out["note"] = (
        "Regimes are declared in DECLARED_REGIMES before any result is seen. SHAP is "
        "descriptive of the fitted model. Cells flagged informative=false (<50 clusters) "
        "must not be interpreted."
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
    top_k: int = 5,
    n_boot: int = 1000,
    seed: int = SEED,
) -> tuple[dict, list[ThresholdHypothesis]]:
    """Run every analysis; returns (JSON-safe result, threshold hypotheses). Writes no file."""
    y = np.asarray(y)
    abl = ablation_study(
        X,
        y,
        folds,
        family_map,
        baseline_features,
        clusters,
        fit_fn=fit_fn,
        n_boot=n_boot,
        seed=seed,
    )
    full, base = abl.pop("_full_oof"), abl.pop("_baseline_oof")
    full = fit_oof(X, y, folds, full.cols, fit_fn, keep_models=True)
    cpi = conditional_permutation_importance(X, y, full, clusters, n_boot=n_boot, seed=seed)
    ranked = sorted(
        cpi["features"],
        key=lambda f: -(cpi["features"][f]["conditional"][next(iter(clusters))]["mean"] or 0.0),
    )
    top = ranked[:top_k]
    res = {
        "kind": KIND,
        "label": LABEL,
        "n_rows": int(len(y)),
        "n_folds": len(folds),
        "fold_ids": [f.fold_id for f in folds],
        "cluster_definitions": list(clusters),
        "ablation": abl,
        "conditional_permutation": cpi,
        "top_features": top,
        "ale": ale_study(X, full, top),
        "interactions": interaction_study(X, full, top, seed=seed),
    }
    if frame is not None:
        res["regimes"] = regime_study(
            frame, y, full, base, clusters, family_map, X, n_boot=n_boot, seed=seed
        )
    ids = np.arange(len(y)) if row_ids is None else row_ids
    hyps: list[ThresholdHypothesis] = []
    first = next(iter(clusters))
    for fold, model in full.models:
        if hasattr(model, "booster"):
            hyps += propose_gbm_thresholds(
                model, fold, ids, clusters[first], features=top, per_feature=1
            )
    res["threshold_hypotheses"] = [h.to_dict() for h in hyps]
    res["interpretation_caveat"] = (
        "SHAP/ALE/H2 describe fitted models. Value added is judged by the refit ablations only; "
        "all thresholds are hypotheses needing new held-out data; nothing here is an edge claim."
    )
    return res, hyps


def trial_record(result: dict) -> dict:
    """Compact trial-log record: family-level effects with Holm, top interactions, counts."""
    abl = result["ablation"]
    fams = {}
    for f, v in abl["families"].items():
        if "drop_minus_full" not in v:
            continue
        key = next(iter(c for c in result["cluster_definitions"]))
        fams[f] = {
            "drop_minus_full": v["drop_minus_full"][key]["mean"],
            "drop_minus_full_ci": v["drop_minus_full"][key]["ci"],
            "only_minus_baseline": v["only_minus_baseline"][key]["mean"],
            "only_minus_baseline_ci": v["only_minus_baseline"][key]["ci"],
            "n_clusters": v["drop_minus_full"][key]["n_clusters"],
        }
    return {
        "kind": KIND,
        "label": LABEL,
        "n_rows": result["n_rows"],
        "n_folds": result["n_folds"],
        "cluster_definitions": result["cluster_definitions"],
        "families": fams,
        "absent_families": abl["absent_families"],
        "multiple_testing": abl["multiple_testing"],
        "n_family_tests": len(fams),
        "top_features": result["top_features"],
        "top_interactions": [p["pair"] for p in result["interactions"]["top_pairs"][:3]],
        "n_threshold_hypotheses": len(result["threshold_hypotheses"]),
        "note": result["interpretation_caveat"],
    }


def log_trial(result: dict, path: Path = provenance.TRIALS_PATH, extra: dict | None = None) -> dict:
    """Append this explain run to the trial log (kind ml_explain, label EXPLORATORY)."""
    rec = {
        **trial_record(result),
        **(extra or {}),
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
    "log_trial",
    "propose_ale_changepoints",
    "propose_gbm_thresholds",
    "regime_study",
    "run_explain",
    "trial_record",
]
