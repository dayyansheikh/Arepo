"""One reusable, leakage-safe model-comparison path for research-lab experiments.

Mirrors the frozen E001 protocol (``evaluate.walk_forward``): test periods after the first,
test rows binned by origin time, training pairs purged to labels known by the bin's earliest
origin time, ridge lambda chosen on an inner time split inside the purged training set only.
Reuses ``evaluate`` helpers and ``models.Ridge``. The metric is SSE-based R2_oos against a named
baseline; model-vs-model differences use an event-clustered paired bootstrap that draws one set
of resamples and applies it to every model.
"""

from __future__ import annotations

import hashlib
import itertools
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluate, features, provenance
from .models import LAMBDA_GRID, Ridge, choose_lambda, fit_origin_ols
from .panel import FEATURES_B2, FEATURES_B3

ESTIMATORS = ("zero", "ols_origin", "ridge")
KEY_COLS = ("period", "t_i", "t_j", "dmid")
HERE = Path(__file__).resolve()


@dataclass(frozen=True)
class ModelSpec:
    name: str
    features: tuple[str, ...] = ()  # feature names and/or "family:<name>" tokens
    estimator: str = "ridge"
    lam_grid: tuple[float, ...] = LAMBDA_GRID

    def __post_init__(self) -> None:
        if self.estimator not in ESTIMATORS:
            raise ValueError(f"unknown estimator {self.estimator!r}")
        if self.estimator != "zero" and not self.features:
            raise ValueError(f"model {self.name!r} needs features")


def e001_models() -> list[ModelSpec]:
    """B0..B3 exactly as E001 (feature order preserved)."""
    return [
        ModelSpec("B0", (), "zero"),
        ModelSpec("B1", ("chg_1d",), "ols_origin"),
        ModelSpec("B1h", ("chg_1h",), "ols_origin"),
        ModelSpec("B2", tuple(FEATURES_B2), "ridge"),
        ModelSpec("B3", tuple(FEATURES_B3), "ridge"),
    ]


def ablations(base: ModelSpec, families: list[str] | tuple[str, ...]) -> list[ModelSpec]:
    """Leave-one-family-out (``<base>-no_<fam>``) and add-one-family (``<base>+<fam>``) specs.

    Leaving a family out also drops features derived from its members (``depends_on``), so an
    interaction cannot smuggle the removed information back in. Families absent from the base
    yield no leave-out spec; families that add nothing new yield no add-one spec.
    """
    base_names = features.expand(base.features)
    out: list[ModelSpec] = []
    for fam in families:
        members = set(features.expand([f"family:{fam}"]))
        removed = set(members & set(base_names))
        if removed:
            changed = True
            while changed:
                changed = False
                for n in base_names:
                    s = features.REGISTRY[n]
                    if n not in removed and (set(s.depends_on) & removed):
                        removed.add(n)
                        changed = True
            keep = tuple(n for n in base_names if n not in removed)
            if keep:
                out.append(ModelSpec(f"{base.name}-no_{fam}", keep, base.estimator, base.lam_grid))
        new = [n for n in members if n not in base_names]
        if new:
            out.append(
                ModelSpec(
                    f"{base.name}+{fam}", tuple(base_names + new), base.estimator, base.lam_grid
                )
            )
    return out


def _inner_split(period: np.ndarray, t_i: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit on earlier training periods / validate on the last; else latest 25% by origin time."""
    last = period.max()
    fit_m, val_m = period < last, period == last
    if fit_m.sum() < evaluate.MIN_TRAIN or val_m.sum() < evaluate.MIN_TRAIN:
        order = np.argsort(t_i)
        fit_m = np.zeros(len(period), bool)
        fit_m[order[: int(len(order) * 0.75)]] = True
        val_m = ~fit_m
    return fit_m, val_m


def walk_forward_generic(
    pairs: pd.DataFrame, specs: list[ModelSpec], cluster: str
) -> tuple[pd.DataFrame, dict]:
    """Test predictions (one column per model) and diagnostics; same protocol as E001."""
    pairs = pairs.reset_index(drop=True)
    names = {s.name: features.expand(list(s.features), pairs) for s in specs}
    X = {s.name: features.feature_matrix(pairs, names[s.name]) for s in specs}
    y = pairs["dmid"].to_numpy(float)
    t_j = pairs["t_j"].to_numpy(float)
    t_i = pairs["t_i"].to_numpy(float)
    per = pairs["period"].to_numpy()
    keep_cols = list(dict.fromkeys(["market_id", "event_id", cluster, *KEY_COLS, "horizon_h"]))
    frames, diag = [], {"lambda_choice": [], "excluded_insufficient_train": {}}
    for p in sorted(pairs["period"].unique())[1:]:
        te_idx = np.flatnonzero(per == p)
        binid = np.floor(t_i[te_idx] / evaluate.BIN_SECONDS)
        for b in np.unique(binid):
            sel = te_idx[binid == b]
            trm = evaluate.purged_train_mask(t_j, float(t_i[sel].min())) & (per < p)
            if trm.sum() < evaluate.MIN_TRAIN:
                ex = diag["excluded_insufficient_train"]
                ex[int(p)] = ex.get(int(p), 0) + len(sel)
                continue
            fit_m, val_m = _inner_split(per[trm], t_i[trm])
            ytr = y[trm]
            f = pairs.loc[sel, [c for c in keep_cols if c in pairs.columns]].copy()
            lams: dict[str, float] = {}
            for s in specs:
                if s.estimator == "zero":
                    f[s.name] = 0.0
                    continue
                Xtr, Xte = X[s.name][trm], X[s.name][sel]
                if s.estimator == "ols_origin":
                    if Xtr.shape[1] != 1:
                        raise ValueError(f"{s.name}: ols_origin needs exactly one feature")
                    f[s.name] = fit_origin_ols(Xtr[:, 0], ytr) * Xte[:, 0]
                    continue
                lam = choose_lambda(Xtr[fit_m], ytr[fit_m], Xtr[val_m], ytr[val_m], s.lam_grid)
                lams[s.name] = lam
                f[s.name] = Ridge(lam).fit(Xtr, ytr).predict(Xte)
            diag["lambda_choice"].append(
                {"period": int(p), "bin": int(b), "n_train": int(trm.sum()), "lams": lams}
            )
            frames.append(f)
    if not frames:
        raise ValueError("no test rows: insufficient periods or training pairs")
    return pd.concat(frames, ignore_index=True), diag


def paired_bootstrap(
    cluster: np.ndarray,
    sse: dict[str, np.ndarray],
    baseline: str,
    n_boot: int = evaluate.BOOT_N,
    seed: int = evaluate.BOOT_SEED,
) -> dict:
    """Clustered bootstrap with ONE set of resamples shared by every model.

    Returns per-model R2 vs baseline CI and, for every ordered-by-name model pair (a, b), the CI
    of R2_a - R2_b where both use the same resampled clusters.
    """
    codes, uniq = pd.factorize(cluster)
    k = len(uniq)
    names = list(sse)
    C = np.column_stack([np.bincount(codes, weights=sse[m], minlength=k) for m in names])
    bi = names.index(baseline)
    rng = np.random.default_rng(seed)
    r2 = np.empty((n_boot, len(names)))
    for i in range(n_boot):
        tot = C[rng.integers(0, k, size=k)].sum(axis=0)
        r2[i] = 1.0 - tot / tot[bi] if tot[bi] > 0 else np.nan

    def q(v: np.ndarray) -> list[float]:
        return [float(x) for x in np.nanpercentile(v, [2.5, 97.5])]

    models = {m: q(r2[:, j]) for j, m in enumerate(names) if m != baseline}
    diffs = {}
    for a, b in itertools.combinations(names, 2):
        if baseline in (a, b):
            continue
        diffs[f"{a}|{b}"] = q(r2[:, names.index(a)] - r2[:, names.index(b)])
    return {"models": models, "diffs": diffs}


def _metrics(y: np.ndarray, yh: np.ndarray) -> dict:
    return {
        "mae": float(np.abs(y - yh).mean()),
        "spearman": evaluate.spearman(yh, y),
    }


def _block(df: pd.DataFrame, names: list[str], baseline: str, cluster: str, n_boot, seed) -> dict:
    y = df["dmid"].to_numpy(float)
    sse = {m: (y - df[m].to_numpy(float)) ** 2 for m in names}
    boot = paired_bootstrap(df[cluster].to_numpy(), sse, baseline, n_boot, seed)
    s0 = sse[baseline].sum()
    out = {"n": int(len(df)), "n_clusters": int(df[cluster].nunique()), "models": {}, "diffs": {}}
    r2 = {m: evaluate.r2_oos(sse[m].sum(), s0) for m in names}
    for m in names:
        ci = boot["models"].get(m, [float("nan")] * 2)
        out["models"][m] = {
            "r2_oos": r2[m],
            "ci_lo": ci[0],
            "ci_hi": ci[1],
            **_metrics(y, df[m].to_numpy(float)),
        }
        if m == baseline:
            out["models"][m]["spearman"] = float("nan")
    for key, ci in boot["diffs"].items():
        a, b = key.split("|")
        out["diffs"][key] = {"diff_r2": r2[a] - r2[b], "ci_lo": ci[0], "ci_hi": ci[1]}
    return out


def code_sha256() -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (HERE, HERE.parent / "features.py")
    }


def git_head() -> str | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=HERE.parent,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def run_comparison(
    pairs_df: pd.DataFrame,
    model_specs: list[ModelSpec],
    *,
    split: str = "walk_forward_by_period",
    purge: str = "label_availability",
    cluster: str = "event_id",
    n_boot: int = evaluate.BOOT_N,
    seed: int = evaluate.BOOT_SEED,
    baseline: str | None = None,
    manifest_path: Path | None = None,
) -> dict:
    """Walk-forward comparison of ``model_specs``; baseline defaults to the first 'zero' model."""
    if split != "walk_forward_by_period":
        raise ValueError(f"unsupported split {split!r}")
    if purge != "label_availability":
        raise ValueError(f"unsupported purge {purge!r}")
    if cluster not in pairs_df.columns:
        raise KeyError(f"cluster column {cluster!r} not in pairs")
    if len({s.name for s in model_specs}) != len(model_specs):
        raise ValueError("duplicate model names")
    if baseline is None:
        baseline = next((s.name for s in model_specs if s.estimator == "zero"), None)
    if baseline not in {s.name for s in model_specs}:
        raise ValueError("baseline must be one of the model specs")
    preds, diag = walk_forward_generic(pairs_df, model_specs, cluster)
    names = [s.name for s in model_specs]
    per_period = {
        int(p): _block(g, names, baseline, cluster, n_boot, seed)
        for p, g in preds.groupby("period")
    }
    used = sorted({n for s in model_specs for n in features.expand(list(s.features), pairs_df)})
    manifest_hash = (
        hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest() if manifest_path else None
    )
    return {
        "config": {
            "split": split,
            "purge": purge,
            "cluster": cluster,
            "n_boot": n_boot,
            "seed": seed,
            "baseline": baseline,
            "models": [
                {
                    "name": s.name,
                    "estimator": s.estimator,
                    "features": features.expand(list(s.features), pairs_df),
                    "lam_grid": list(s.lam_grid),
                }
                for s in model_specs
            ],
        },
        "pooled": _block(preds, names, baseline, cluster, n_boot, seed),
        "per_period": per_period,
        "excluded_insufficient_train": diag["excluded_insufficient_train"],
        "lambda_choice": diag["lambda_choice"],
        "provenance": {
            "data_manifest_sha256": manifest_hash,
            "pairs_content_hash": int(
                pd.util.hash_pandas_object(pairs_df[["period", "t_i", "dmid"]]).sum() % 2**63
            ),
            "n_pairs": int(len(pairs_df)),
            "feature_versions": features.versions(used),
            "code_sha256": code_sha256(),
            "git_head": git_head(),
            "seed": seed,
        },
        "provenance_v2": provenance.run_provenance(),
    }


def write_new_json(out_dir: Path, result: dict) -> Path:
    """Write ``results.json`` into a new directory; refuse to touch an existing run."""
    import json

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)  # FileExistsError if the run id is taken
    path = out_dir / "results.json"
    path.write_text(json.dumps(result, indent=1, default=float))
    return path
