"""EXPLORATORY historical ML development run (evidence_role ``exploratory_historical``).

Runs the existing ML development machinery (``ml_panel`` folds, ``ml_models`` arms, ``ml_explain``
incremental ablation) on the history-backfill panels (``history_backfill.build_panel``). Nothing
here is prospective, nothing is a confirmation, and no edge/calibration/profitability claim is
ever made: the panels are reconstructed after the fact, have no book features and come from a
sampled, survivorship-affected frame (see the run manifest).

Arms: M0 (price + momentum), M1 (elastic net), M2 (LightGBM, nested tuning) on the market-state
set, plus M1F/M2F that add the trade-flow and wallet families. Targets: direction (3-class) and
|move| (binary) at horizons 1, 3, 12 grid steps (2h, 6h, 24h). Incremental family value comes from
``ml_explain.ablation_study`` (drop-one / add-one out-of-fold log-loss, cluster-bootstrap CI, BY).
Placebos: shuffled labels (within period) and a leak positive control (a feature built from the
target). Every fit/score/ablation line is appended to ``trials.jsonl``.

Usage::

    python backend/scripts/run_ml_history.py --run-id h2_main --max-rows 150000
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from astrolabe.research_lab import (  # noqa: E402
    history_backfill as hb,
)
from astrolabe.research_lab import (  # noqa: E402
    ml_explain,
    ml_models,
    ml_panel,
    provenance,
)

HIST_ROOT = ROOT / "data-dumps" / "research_lab" / "history"
ROLE = "exploratory_historical"
HORIZON_FILES = {1: 2, 3: 6, 12: 24}  # k grid steps -> panel horizon hours
STATE_COLS = tuple(c for c in ml_models.M12_FEATURES)
FLOW_COLS = hb.TF_NAMES
WALLET_COLS = hb.WLT_NAMES
ID_COLS = ["market_id", "event_id", "period", "t_i", "t0", "t_j", "mid_i", "mid_j", "dmid",
           "y_class", "y_dmid", "y_absmove", "target_available", "dep_group", "fee_category",
           "status"]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------


def pick_markets(path: Path, max_rows: int, seed: int) -> tuple[set[str], int]:
    """Seeded market subset whose total row count stays below ``max_rows`` (memory-light: only the
    market_id column is read). Subsampling markets keeps the 2h period axis intact."""
    ids = pd.read_csv(path, usecols=["market_id"], dtype=str)["market_id"]
    counts = ids.value_counts()
    order = np.random.default_rng(seed).permutation(len(counts))
    chosen, total = set(), 0
    for i in order:
        c = int(counts.iloc[i])
        if total + c > max_rows:
            continue
        chosen.add(counts.index[i])
        total += c
    return chosen, total


def load_panel(path: Path, markets: set[str]) -> pd.DataFrame:
    cols = list(dict.fromkeys([*ID_COLS, *STATE_COLS, *FLOW_COLS, *WALLET_COLS]))
    parts = []
    for ch in pd.read_csv(path, usecols=cols, dtype={"market_id": str, "event_id": str,
                                                      "dep_group": str},
                          chunksize=200_000, keep_default_na=True):
        parts.append(ch[ch["market_id"].isin(markets)])
    df = pd.concat(parts, ignore_index=True)
    df["event_id"] = df["event_id"].where(df["event_id"].fillna("").ne(""), np.nan)
    df["target_available"] = df["target_available"].astype(bool)
    return df.sort_values(["period", "market_id"], kind="stable").reset_index(drop=True)


def usable(cols, lab: pd.DataFrame, min_non_nan: float = 0.05) -> list[str]:
    return [c for c in cols if c in lab.columns and lab[c].notna().mean() >= min_non_nan]


@contextlib.contextmanager
def feature_set(cols: tuple[str, ...]):
    """Temporarily make ``cols`` the M1/M2 feature set (ml_models reads the module global)."""
    old = ml_models.M12_FEATURES
    ml_models.M12_FEATURES = tuple(cols)
    try:
        yield
    finally:
        ml_models.M12_FEATURES = old


# ---------------------------------------------------------------------------------------------
# Fits and scores
# ---------------------------------------------------------------------------------------------


def run_variants(target: str, lab: pd.DataFrame, manifest: dict, sink, arms: dict[str, tuple],
                 ) -> dict[str, ml_models.ArmResult]:
    """``arms``: result name -> (base arm name, feature tuple or None for the module default)."""
    out = {}
    for name, (arm, cols) in arms.items():
        t0 = time.perf_counter()
        sink.extra["variant"] = name
        ctx = feature_set(cols) if cols is not None else contextlib.nullcontext()
        with ctx:
            if target == "direction":
                out[name] = ml_models.run_arm(arm, lab, manifest, sink=sink)
            else:
                out[name] = ml_models.run_target_arm(target, arm, lab, manifest, sink=sink)
        log(f"    fitted {target}/{name} in {time.perf_counter() - t0:.0f}s")
    sink.extra.pop("variant", None)
    return out


def summarise(score: dict) -> dict:
    """Compact per-arm table: log loss, relative improvement vs M0 with both cluster CIs."""
    rows = {}
    for a, m in score["arms"].items():
        rows[a] = {"loss": m.get("log_loss"), "brier": m.get("brier")}
    for cname, blk in score["bootstrap"].items():
        for a, e in blk["log_loss"].items():
            rows[a][f"rel_improvement_ll[{cname}]"] = e["rel_improvement"]
            rows[a][f"ci95[{cname}]"] = e["ci95"]
    return {"n_rows": score["n_rows"], "non_inferential": score["non_inferential"], "arms": rows}


def score_target_generic(target, lab, results, clusters, n_boot, sink, manifest):
    if target == "direction":
        return ml_models.score_arms(lab, results, clusters, n_boot=n_boot, sink=sink,
                                    manifest=manifest)
    return ml_models.score_target(lab, results, clusters, target, n_boot=n_boot, sink=sink,
                                  manifest=manifest)


def ablate(lab: pd.DataFrame, ycol: str, folds, base_cols, families: dict[str, list[str]],
           clusters, n_boot: int, n_classes: int) -> dict:
    cols = list(dict.fromkeys([*base_cols, *sum(families.values(), [])]))
    X = lab[cols].reset_index(drop=True)
    y = lab[ycol].to_numpy(float).astype(int)
    rep = ml_explain.ablation_study(
        X, y, folds, families, base_cols, clusters, n_boot=n_boot,
        prior_tests=ml_explain.prior_ml_explain_tests(),
    )
    rep.pop("_full_oof", None)
    rep.pop("_baseline_oof", None)
    return rep


def ablation_trial(rep: dict, header: dict, role: str, sink_path: Path, extra: dict) -> None:
    prov = provenance.run_provenance([Path(ml_explain.__file__)])
    provenance.append_trial({
        "kind": "ml_explain", "label": ml_explain.LABEL, "evidence_role": role,
        "ranking": [{k: r[k] for k in ("rank", "unit", "kind", "delta_ll", "ci", "p_by", "label")}
                    for r in rep["ranking"]],
        "absent_families": rep["absent_families"],
        "multiple_testing": {k: rep["multiple_testing"][k]
                             for k in ("by_q", "m_tests", "prior_tests", "m_total")},
        "provenance": prov, **header, **extra,
    }, sink_path)


def compact_ablation(rep: dict) -> dict:
    return {"ranking": [{k: r[k] for k in ("unit", "delta_ll", "ci", "p_by", "label")}
                        for r in rep["ranking"]],
            "mean_loss": rep["mean_loss"], "multiple_testing": {
                k: rep["multiple_testing"][k] for k in ("m_tests", "prior_tests", "m_total")},
            "absent_families": rep["absent_families"]}


def leak_column(lab: pd.DataFrame, seed: int) -> np.ndarray:
    """Positive control: a noisy copy of the realised move. Must be detected as valuable."""
    rng = np.random.default_rng(seed)
    return lab["y_dmid"].to_numpy(float) + rng.normal(0, 0.02, len(lab))


def shuffle_within_period(lab: pd.DataFrame, cols: list[str], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = lab.copy()
    for _, idx in out.groupby("period").indices.items():
        perm = rng.permutation(idx)
        for c in cols:
            out.iloc[idx, out.columns.get_loc(c)] = lab[c].to_numpy()[perm]
    return out


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------


def run_horizon(k: int, args, markets: set[str], sink, placebo_sink, results: dict, run_dir: Path):
    hours = HORIZON_FILES[k]
    log(f"horizon k={k} ({hours}h): loading panel")
    df = load_panel(run_dir / f"panel_H{hours}h.csv.gz", markets)
    table = ml_panel.period_table(df)
    sha = provenance.git_state().get("git_head", "unknown")
    manifest = ml_panel.plan_folds(
        table, policy=ml_panel.category_policy(), feature_vers={}, code_sha=sha,
        block=args.block_periods, min_train=args.min_train_periods, embargo_s=k * hb.GRID_S,
        horizon=k)
    info = {"rows": int(len(df)), "labelled": int(df["target_available"].sum()),
            "periods": len(table), "n_folds": len(manifest["folds"]),
            "manifest_sha256": manifest["manifest_sha256"], "embargo_s": manifest["embargo_s"],
            "markets": int(df["market_id"].nunique())}
    log(f"  {info}")
    res: dict = {"panel": info}
    if len(manifest["folds"]) < 2:
        res["error"] = "fewer than 2 folds; not run"
        results[str(k)] = res
        return
    lab = ml_panel.labelled(df).reset_index(drop=True)
    del df
    lab["_dep"] = lab["dep_group"].to_numpy()
    clusters = ml_models.cluster_vectors(lab, dependence_groups=lab["_dep"].to_numpy())
    clusters_x = {"event": ml_models._event_or_market(lab).to_numpy(),
                  "dep_group": lab["_dep"].to_numpy()}
    folds = ml_explain.folds_from_manifest(lab, manifest)
    state = tuple(STATE_COLS)
    flow = tuple(usable(FLOW_COLS, lab))
    wallet = tuple(usable(WALLET_COLS, lab))
    res["coverage"] = {c: float(lab[c].notna().mean()) for c in (*FLOW_COLS, *WALLET_COLS)}
    res["state_cols_non_nan"] = [c for c in state if lab[c].notna().mean() >= 0.05]
    sink.extra.update(horizon_snapshots_k=k, horizon_hours=hours)
    placebo_sink.extra.update(horizon_snapshots_k=k, horizon_hours=hours)
    for target in args.targets:
        tag = f"{target}"
        log(f"  target {target}")
        arms = {"M0": ("M0", None), "M1": ("M1", None), "M2": ("M2", None),
                "M1F": ("M1", (*state, *flow, *wallet)),
                "M2F": ("M2", (*state, *flow, *wallet))}
        if args.skip_arms:
            arms = {"M0": arms["M0"]}
        fits = run_variants(target, lab, manifest, sink, arms)
        sc = score_target_generic(target, lab, fits, clusters, args.n_boot, sink, manifest)
        res[tag] = {"arms": summarise(sc) if target == "direction" else sc}
        ycol = "y_class" if target == "direction" else "y_absmove"
        ncls = 3 if target == "direction" else 2
        fams = {"market_state_extra": [c for c in res["state_cols_non_nan"]
                                       if c not in ml_models.M0_FEATURES],
                "flow": list(flow), "wallet": list(wallet)}
        fams = {f: v for f, v in fams.items() if v}
        base = [c for c in ml_models.M0_FEATURES]
        t0 = time.perf_counter()
        rep = ablate(lab, ycol, folds, base, fams, clusters_x, args.n_boot, ncls)
        log(f"    ablation {time.perf_counter() - t0:.0f}s: "
            + ", ".join(f"{r['unit']}={r['delta_ll']:.5f}({r['label']})" for r in rep["ranking"]))
        res[tag]["ablation"] = compact_ablation(rep)
        hdr = {"target_family": target, "horizon_snapshots_k": k, "horizon_hours": hours,
               "n_rows": int(len(lab)), "manifest_sha256": manifest["manifest_sha256"],
               "dataset": f"history:{run_dir.name}"}
        ablation_trial(rep, hdr, ROLE, args.trials_path,
                       {"data_provenance": hb.PROVENANCE, "evidence_role_note": ROLE})
        if args.placebo and (args.placebo_all or k == 1):
            shuf = shuffle_within_period(lab, ["y_class", "y_absmove"], args.seed + k)
            prep = ablate(shuf, ycol, folds, base, fams, clusters_x, args.n_boot, ncls)
            res[tag]["placebo_shuffled_ablation"] = compact_ablation(prep)
            ablation_trial(prep, {**hdr, "placebo": "shuffled_labels_within_period"},
                           "placebo", args.trials_path, {"source_evidence_role": ROLE,
                                                         "data_provenance": hb.PROVENANCE})
            lk = lab.copy()
            lk["leak_future_move"] = leak_column(lab, args.seed + 100 + k)
            lrep = ablate(lk, ycol, folds, base, {**fams, "leak": ["leak_future_move"]},
                          clusters_x, args.n_boot, ncls)
            res[tag]["leak_positive_control_ablation"] = compact_ablation(lrep)
            ablation_trial(lrep, {**hdr, "placebo": "leak_positive_control"}, "placebo",
                           args.trials_path, {"source_evidence_role": ROLE,
                                              "data_provenance": hb.PROVENANCE})
            if target == "direction" and not args.skip_arms:
                sf = run_variants(target, shuf, manifest, placebo_sink,
                                  {"M0": ("M0", None), "M2F": ("M2", (*state, *flow, *wallet))})
                res[tag]["placebo_shuffled_arms"] = summarise(
                    ml_models.score_arms(shuf, sf, clusters, n_boot=args.n_boot,
                                         sink=placebo_sink, manifest=manifest))
        results[str(k)] = res
        (run_dir / "ml_history_results.json").write_text(json.dumps(results, indent=1,
                                                                    default=float))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--root", type=Path, default=HIST_ROOT)
    ap.add_argument("--max-rows", type=int, default=150_000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--horizons", default="1,3,12")
    ap.add_argument("--targets", default="direction,absmove")
    ap.add_argument("--block-periods", type=int, default=240, help="test block, 2h periods")
    ap.add_argument("--min-train-periods", type=int, default=480)
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--lgb-configs", type=int, default=6,
                    help="nested-tuning budget: first N of the declared LightGBM grid")
    ap.add_argument("--no-placebo", dest="placebo", action="store_false")
    ap.add_argument("--placebo-all", action="store_true")
    ap.add_argument("--skip-arms", action="store_true", help="ablation only")
    ap.add_argument("--trials-path", type=Path, default=provenance.TRIALS_PATH)
    a = ap.parse_args(argv)
    a.targets = [t for t in a.targets.split(",") if t]
    run_dir = a.root / a.run_id
    ml_models.LGB_GRID = ml_models.LGB_GRID[: a.lgb_configs]
    ml_panel.register_tier_a()
    ml_panel.register_extended()
    first = run_dir / f"panel_H{HORIZON_FILES[1]}h.csv.gz"
    markets, rows = pick_markets(first, a.max_rows, a.seed)
    log(f"market subset: {len(markets)} markets, {rows} origin rows (cap {a.max_rows})")
    hist = json.loads((run_dir / "manifest.json").read_text())
    results: dict = {
        "evidence_role": ROLE, "provenance": hb.PROVENANCE,
        "note": "EXPLORATORY historical development run. No edge, calibration or profitability "
        "claim. Book features absent. Frame is sampled and survivorship-affected.",
        "args": {k: str(v) for k, v in vars(a).items()}, "lgb_configs_used": a.lgb_configs,
        "market_subset": {"n_markets": len(markets), "n_rows": rows, "seed": a.seed},
        "history_manifest": {k: hist.get(k) for k in ("run_id", "stratification", "frame_report",
                                                       "evidence_notes", "counts")},
        "features": {"state": list(STATE_COLS), "flow": list(FLOW_COLS),
                     "wallet": list(WALLET_COLS)},
    }
    sink = ml_models.TrialSink(dataset=f"history:{a.run_id}", path=a.trials_path,
                               evidence_role=ROLE,
                               extra={"data_provenance": hb.PROVENANCE})
    placebo_sink = ml_models.TrialSink(
        dataset=f"history:{a.run_id}", path=a.trials_path, evidence_role="placebo",
        extra={"data_provenance": hb.PROVENANCE, "source_evidence_role": ROLE,
               "placebo": "shuffled_labels_within_period"})
    for k in [int(x) for x in a.horizons.split(",")]:
        run_horizon(k, a, markets, sink, placebo_sink, results, run_dir)
    (run_dir / "ml_history_results.json").write_text(json.dumps(results, indent=1, default=float))
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
