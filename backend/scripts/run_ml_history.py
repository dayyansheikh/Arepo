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
WAGE_PREFIXES = ("ml_wage_", "ml_wa_", "nw_")  # history_sources.new_wallet_features: nw_*
HORIZON_FILES = {1: 2, 3: 6, 12: 24}  # k grid steps -> panel horizon hours
SW_COLS = tuple(ml_panel.SWEEP_NAMES)  # book family (joined from pmxt features when present)
STATE_COLS = tuple(c for c in ml_models.M12_FEATURES if c not in SW_COLS)
FLOW_COLS = hb.TF_NAMES
WALLET_COLS = hb.WLT_NAMES
ID_COLS = ["market_id", "event_id", "period", "t_i", "t0", "t_j", "mid_i", "mid_j", "dmid",
           "y_class", "y_dmid", "y_absmove", "target_available", "dep_group", "fee_category",
           "status", "traded_before_t", "price_unchanged_since_listing"]


LOCK_DIR = Path("/tmp/arepo_heavy.lock")  # ~/arepo_collector/heavy_lock.md
MIN_FREE_PCT = 20


def _free_pct() -> float:
    import re
    import subprocess

    try:
        out = subprocess.run(["memory_pressure"], capture_output=True, text=True,
                             timeout=30).stdout
        m = re.search(r"free percentage:\s*(\d+)%", out)
        return float(m.group(1)) if m else 100.0
    except (OSError, subprocess.SubprocessError):
        return 100.0


@contextlib.contextmanager
def heavy_lock(poll_s: float = 60.0):
    """Shared heavy-compute lock: mkdir /tmp/arepo_heavy.lock (retry every 60 s; a lock whose
    holder PID is dead is stale), require system free memory >= 20%, release on exit."""
    import os
    import shutil

    while True:
        try:
            LOCK_DIR.mkdir()
        except FileExistsError:
            try:
                pid = int((LOCK_DIR / "pid").read_text().strip())
                os.kill(pid, 0)
            except (OSError, ValueError):
                if (LOCK_DIR / "pid").exists():  # holder gone: stale lock
                    shutil.rmtree(LOCK_DIR, ignore_errors=True)
                    continue
            time.sleep(poll_s)
            continue
        (LOCK_DIR / "pid").write_text(str(os.getpid()))
        if _free_pct() >= MIN_FREE_PCT:
            break
        shutil.rmtree(LOCK_DIR, ignore_errors=True)
        log(f"free memory below {MIN_FREE_PCT}%: waiting")
        time.sleep(poll_s)
    try:
        yield
    finally:
        shutil.rmtree(LOCK_DIR, ignore_errors=True)


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
    cols = list(dict.fromkeys([*ID_COLS, *STATE_COLS, *FLOW_COLS, *WALLET_COLS,
                              *hb.HIST_EXTRA_NAMES]))
    if "sample_weight" in pd.read_csv(path, nrows=0).columns:
        cols.append("sample_weight")
    parts = []
    for ch in pd.read_csv(path, usecols=cols, dtype={"market_id": str, "event_id": str,
                                                      "dep_group": str},
                          chunksize=200_000, keep_default_na=True):
        parts.append(ch[ch["market_id"].isin(markets)])
    df = pd.concat(parts, ignore_index=True)
    df["event_id"] = df["event_id"].where(df["event_id"].fillna("").ne(""), np.nan)
    df["target_available"] = df["target_available"].astype(bool)
    return df.sort_values(["period", "market_id"], kind="stable").reset_index(drop=True)


def join_external(df: pd.DataFrame, book_path: Path | None, wage_path: Path | None,
                  ) -> tuple[pd.DataFrame, dict]:
    """Optional external tables keyed by (market_id, origin_ts == panel t_i). Missing stays NaN.
    ``book``: ``history_sources.load_book_features`` (ml_sw_* columns); rows are restricted to
    origins inside the pmxt window. ``wallet_age``: any numeric columns prefixed ml_wage_/ml_wa_."""
    info: dict = {"book": None, "wallet_age": None}
    df = df.copy()
    df["_ts"] = df["t_i"].astype(float)
    if book_path is not None and Path(book_path).exists():
        from astrolabe.research_lab import history_sources as hs

        bf = hs.load_book_features(book_path)
        cols = [c for c in bf.columns if c in SW_COLS]
        inwin = np.array([hs.origin_in_window(t) for t in df["_ts"].to_numpy()])
        df = df[inwin].reset_index(drop=True)
        bf = bf.drop_duplicates(["market_id", "origin_ts"])[["market_id", "origin_ts", *cols]]
        df = df.drop(columns=[c for c in cols if c in df.columns]).merge(
            bf, left_on=["market_id", "_ts"], right_on=["market_id", "origin_ts"], how="left")
        df = df.drop(columns=["origin_ts"])
        has = df[cols].notna().any(axis=1) if cols else pd.Series(False, index=df.index)
        info["book"] = {"path": str(book_path), "columns": cols, "rows_in_window": int(len(df)),
                        "rows_with_book": int(has.sum())}
    if wage_path is not None and Path(wage_path).exists():
        wa = pd.read_csv(wage_path, dtype={"market_id": str})
        wa["origin_ts"] = wa["origin_ts"].astype(float)
        cols = [c for c in wa.columns if c.startswith(WAGE_PREFIXES)]
        wa = wa.drop_duplicates(["market_id", "origin_ts"])[["market_id", "origin_ts", *cols]]
        df = df.merge(wa, left_on=["market_id", "_ts"], right_on=["market_id", "origin_ts"],
                      how="left").drop(columns=["origin_ts"])
        info["wallet_age"] = {"path": str(wage_path), "columns": cols,
                              "rows_with_value": int(df[cols].notna().any(axis=1).sum())
                              if cols else 0}
    return df.drop(columns=["_ts"]).reset_index(drop=True), info


def placeholder_report(df: pd.DataFrame) -> dict:
    """Rows without a prior trade carry placeholder/listing prices (challenger rule): described
    separately from the primary analysis. ``traded_before_t`` NaN = unknown (truncated history)."""
    def desc(d: pd.DataFrame) -> dict:
        lab = d[d["target_available"]]
        am = lab["dmid"].abs()
        return {"rows": int(len(d)), "labelled": int(len(lab)),
                "flat_share": float((am <= ml_panel.DELTA_PRIMARY + 1e-9).mean()) if len(lab)
                else None,
                "mean_abs_dmid": float(am.mean()) if len(lab) else None,
                "mean_mid_i": float(d["mid_i"].mean()) if len(d) else None,
                "share_mid_within_0.02_of_0.5": float((d["mid_i"] - 0.5).abs().lt(0.02).mean())
                if len(d) else None}

    tb = df["traded_before_t"]
    un = df["price_unchanged_since_listing"]
    return {
        "rule": "primary analysis excludes traded_before_t == 0; unknown (NaN) rows are kept",
        "traded_before_t": {"yes": int((tb == 1).sum()), "no": int((tb == 0).sum()),
                            "unknown": int(tb.isna().sum())},
        "price_unchanged_since_listing": {"yes": int((un == 1).sum()), "no": int((un == 0).sum()),
                                          "undefined": int(un.isna().sum())},
        "unchanged_and_untraded": int(((un == 1) & (tb == 0)).sum()),
        "unchanged_but_traded": int(((un == 1) & (tb != 0)).sum()),
        "excluded_no_prior_trade": desc(df[tb == 0]),
        "unchanged_since_listing_rows": desc(df[un == 1]),
        "included_primary": desc(df[tb != 0]),
    }


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
           clusters, n_boot: int, n_classes: int, eval_mask=None) -> dict:
    cols = list(dict.fromkeys([*base_cols, *sum(families.values(), [])]))
    X = lab[cols].reset_index(drop=True)
    y = lab[ycol].to_numpy(float).astype(int)
    rep = ml_explain.ablation_study(
        X, y, folds, families, base_cols, clusters, n_boot=n_boot, eval_mask=eval_mask,
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


M0V = (*ml_models.M0_FEATURES, "ml_own_vol", "ml_rv_2h", "ml_rv_6h", "ml_rv_1d", "ml_rv_7d",
       "ml_log_hours_to_end", "ml_dist_01", "ml_tf_n_24h", "ml_tf_log_notional_24h")
ACTIVITY = ("ml_tf_n_24h", "ml_tf_log_notional_24h")  # trading-activity level lives in M0v
KINDS = {"direction": ("y_class", 3, "direction"), "absmove": ("y_absmove", 2, "absmove"),
         "updown": ("y_absmove", 2, "absmove")}  # updown: moved rows only, y_absmove := up
SHUFFLE_COLS = ["y_class", "y_absmove"]


@contextlib.contextmanager
def patched(m0=None, m12=None):
    """Temporarily set the M0 and/or M1/M2 feature tuples that ml_models reads as globals."""
    old = (ml_models.M0_FEATURES, ml_models.M12_FEATURES)
    if m0 is not None:
        ml_models.M0_FEATURES = tuple(m0)
    if m12 is not None:
        ml_models.M12_FEATURES = tuple(m12)
    try:
        yield
    finally:
        ml_models.M0_FEATURES, ml_models.M12_FEATURES = old


def fit_arms(kind: str, lab, manifest, sink, specs: dict) -> dict:
    """``specs``: name -> (base arm, M0 feature tuple or None, M1/M2 feature tuple or None)."""
    target = KINDS[kind][2]
    out = {}
    for name, (arm, m0, m12) in specs.items():
        t0 = time.perf_counter()
        sink.extra["variant"] = name
        with patched(m0, m12):
            if target == "direction":
                out[name] = ml_models.run_arm(arm, lab, manifest, sink=sink)
            else:
                out[name] = ml_models.run_target_arm(target, arm, lab, manifest, sink=sink)
        log(f"      fitted {kind}/{name} in {time.perf_counter() - t0:.0f}s")
    sink.extra.pop("variant", None)
    return out


def score_two(kind, lab, fits, clusters, n_boot, sink, manifest) -> dict:
    """Score against M0v (simple reference) and against M2v (same learner, reference features)."""
    out = {}
    target = KINDS[kind][2]
    for base in ("M0v", "M2v"):
        if base not in fits:
            continue
        if target == "direction":
            sc = ml_models.score_arms(lab, fits, clusters, baseline=base, n_boot=n_boot,
                                      sink=sink, manifest=manifest)
            out[f"vs_{base}"] = summarise(sc)
        else:
            out[f"vs_{base}"] = ml_models.score_target(
                lab, fits, clusters, target, baseline=base, n_boot=n_boot, sink=sink,
                manifest=manifest)
    return out


def weighted_scores(kind: str, lab: pd.DataFrame, fits: dict, baselines=("M0v", "M2v"),
                    n_boot: int = 1000, seed: int = 11) -> dict | None:
    """Sample-weighted out-of-fold comparison: weights are the inverse inclusion probabilities of
    the stratified (topic-oversampled) market sample. Weighted mean log loss per arm and relative
    improvement over each baseline, with a weighted cluster bootstrap (event clusters). Weights
    enter the evaluation only; models are fitted unweighted."""
    if "sample_weight" not in lab.columns:
        return None
    mask = np.ones(len(lab), bool)
    for r in fits.values():
        mask &= r.test_mask
    w = lab["sample_weight"].to_numpy(float)[mask]
    ycol = KINDS[kind][0]
    y = lab[ycol].to_numpy(float)[mask]
    loss = {}
    for a, r in fits.items():
        p = r.proba[mask]
        loss[a] = (ml_models.log_loss_rows(p, y.astype(int)) if kind == "direction"
                   else ml_models.binary_log_loss_rows(p, y))
    cl = pd.factorize(ml_models._event_or_market(lab).to_numpy()[mask])[0]
    ncl = cl.max() + 1
    rng = np.random.default_rng(seed)
    wl = {a: np.bincount(cl, weights=w * v, minlength=ncl) for a, v in loss.items()}
    sw = np.bincount(cl, weights=w, minlength=ncl)
    out = {"n_rows": int(mask.sum()), "n_clusters": int(ncl),
           "weight_sum_ratio_max_min": float(w.max() / w.min()),
           "effective_n": float(w.sum() ** 2 / (w ** 2).sum()),
           "weighted_loss": {a: float(wl[a].sum() / sw.sum()) for a in loss}, "vs": {}}
    draws = rng.integers(0, ncl, size=(n_boot, ncl))
    for b in baselines:
        if b not in loss:
            continue
        ent = {}
        for a in loss:
            if a == b:
                continue
            rel = 1 - wl[a].sum() / wl[b].sum()
            boot = 1 - wl[a][draws].sum(1) / wl[b][draws].sum(1)
            ent[a] = {"rel_improvement": float(rel),
                      "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]}
        out["vs"][b] = ent
    return out


def shuffle_labels(lab: pd.DataFrame, mode: str, seed: int) -> pd.DataFrame:
    """Permute label columns together. ``global``: across all rows (the null: nothing but the label
    marginal survives); ``period``: within period (keeps period class mix); ``market``: within
    market (keeps each market's class mix)."""
    rng = np.random.default_rng(seed)
    out = lab.copy()
    cols = [c for c in SHUFFLE_COLS if c in lab.columns]
    groups = {"global": {0: np.arange(len(lab))},
              "period": lab.groupby("period").indices,
              "market": lab.groupby("market_id").indices}[mode]
    for idx in groups.values():
        perm = rng.permutation(idx)
        for c in cols:
            out.iloc[idx, out.columns.get_loc(c)] = lab[c].to_numpy()[perm]
    return out


def placebo_arm_flags(sc: dict, kind: str) -> tuple[list[str], list[str]]:
    """(all, gated) arms that beat a baseline with a 95% CI above 0 on a shuffled-label run.

    Gated = same-learner pairs only (M2* against M2v; M0*/M1* against M0v). M2 against the
    unregularised logistic M0v on pure noise is a learner asymmetry (the logistic overfits noise,
    the early-stopped, temperature-scaled GBM stays at the base rate), not family value; it is
    reported but does not gate."""
    allf, gated = [], []
    for bkey, blk in sc.items():
        base = bkey.removeprefix("vs_")
        pairs = []
        if kind == "direction":
            for a, v in blk["arms"].items():
                for k_, ci in v.items():
                    if k_.startswith("ci95[") and a != base and ci[0] > 0:
                        pairs.append((a, f"{a}>{base}{k_[4:]}"))
        else:
            for cname, b in blk["bootstrap"].items():
                for a, e in b["log_loss"].items():
                    if e["ci95"][0] > 0:
                        pairs.append((a, f"{a}>{base}[{cname}]"))
        for a, label in pairs:
            allf.append(label)
            if (a.startswith("M2") and base == "M2v") or (not a.startswith("M2") and base == "M0v"):
                gated.append(label)
    return sorted(set(allf)), sorted(set(gated))


def apply_gate(cell: dict, gate_modes: list[str]) -> None:
    """If any gated placebo beats a baseline (arm CI above 0) or any family is 'demonstrated' on
    shuffled labels, no result in the cell may be labelled demonstrated."""
    fails = []
    for mode in gate_modes:
        pl = cell.get("placebo", {}).get(mode)
        if not pl:
            continue
        fails += [f"{mode}:arm {x}" for x in pl.get("arms_beating_baseline_same_learner", [])]
        fails += [f"{mode}:family {r['unit']}" for r in pl["ablation"]["ranking"]
                  if r["label"] == "demonstrated"]
    cell["placebo_gate"] = {"modes": gate_modes, "passed": not fails, "failures": fails}
    if fails:
        for r in cell["ablation"]["ranking"]:
            if r["label"] == "demonstrated":
                r["label_before_gate"] = "demonstrated"
                r["label"] = "descriptive_only (placebo_gate)"


def run_kind(kind, lab, manifest, k, hours, args, sink, placebo_sink, run_dir, ext, parts) -> dict:
    ycol, ncls, target = KINDS[kind]
    state_ext, flow, wallet, extra_cols, book = parts
    clusters = ml_models.cluster_vectors(lab, dependence_groups=lab["dep_group"].to_numpy())
    clusters_x = {"event": ml_models._event_or_market(lab).to_numpy(),
                  "dep_group": lab["dep_group"].to_numpy()}
    folds = ml_explain.folds_from_manifest(lab, manifest)
    eval_mask = (lab[list(book)].notna().any(axis=1).to_numpy() if book else None)
    full = (*state_ext, *flow, *wallet)
    specs = {"M0": ("M0", None, None), "M0v": ("M0", M0V, None), "M2v": ("M2", None, M0V),
             "M1": ("M1", None, state_ext), "M2": ("M2", None, state_ext),
             "M2F": ("M2", None, full)}
    if extra_cols:
        specs["M2FX"] = ("M2", None, (*full, *extra_cols))
    if args.skip_arms:
        specs = {n: specs[n] for n in ("M0", "M0v", "M2v")}
    cell: dict = {"n_rows": int(len(lab)), "n_folds": len(manifest["folds"]),
                  "manifest_sha256": manifest["manifest_sha256"]}
    sink.extra.update(history_target=kind)
    placebo_sink.extra.update(history_target=kind)
    fits = fit_arms(kind, lab, manifest, sink, specs)
    cell["scores"] = score_two(kind, lab, fits, clusters, args.n_boot, sink, manifest)
    cell["weighted"] = weighted_scores(kind, lab, fits)
    base_cols = list(M0V)
    extra_state = [c for c in state_ext if c not in M0V and lab[c].notna().mean() >= 0.05]
    fams = {"state_extra": extra_state, "flow": [c for c in flow if c not in ACTIVITY],
            "wallet": list(wallet)}
    if book:
        fams["book"] = list(book)
    wage = [c for c in extra_cols if c not in book]
    if wage:
        fams["wallet_age"] = wage
    if args.drill_flow:  # split flow into mechanisms: staleness-prone, signed flow, intensity
        fl = [c for c in flow if c not in ACTIVITY]
        stale = [c for c in fl if c in ("ml_tf_ltp_minus_mid", "ml_tf_last_age_h")]
        signed = [c for c in fl if "signed_vol" in c or "buy_share" in c]
        fams.pop("flow", None)
        fams.update({"flow_last_trade_vs_price": stale, "flow_signed": signed,
                     "flow_intensity": [c for c in fl if c not in stale and c not in signed]})
    fams = {f: v for f, v in fams.items() if v}
    hdr = {"target_family": target, "history_target": kind, "horizon_snapshots_k": k,
           "horizon_hours": hours, "n_rows": int(len(lab)), "baseline": "M0v",
           "manifest_sha256": manifest["manifest_sha256"], "dataset": f"history:{run_dir.name}"}
    t0 = time.perf_counter()
    rep = ablate(lab, ycol, folds, base_cols, fams, clusters_x, args.n_boot_abl, ncls, eval_mask)
    log(f"      ablation vs M0v {time.perf_counter() - t0:.0f}s: "
        + ", ".join(f"{r['unit']}={r['delta_ll']:.5f}({r['label']})" for r in rep["ranking"]))
    cell["ablation"] = compact_ablation(rep)
    ablation_trial(rep, hdr, ROLE, args.trials_path,
                   {"data_provenance": hb.PROVENANCE, "revision": args.revision})
    if args.placebo:
        cell["placebo"] = {}
        modes = ["global"] + (["period", "market"] if (args.placebo_diag_all or k == 1) else [])
        for mode in modes:
            shuf = shuffle_labels(lab, mode, args.seed + 17 * k)
            pspecs = {n: specs[n] for n in ("M0v", "M2v", "M2F") if n in specs}
            pf = fit_arms(kind, shuf, manifest, placebo_sink, pspecs)
            psc = score_two(kind, shuf, pf, clusters, args.n_boot, placebo_sink, manifest)
            prep = ablate(shuf, ycol, folds, base_cols, fams, clusters_x, args.n_boot_abl, ncls,
                          eval_mask)
            allf, gated = placebo_arm_flags(psc, kind)
            entry = {"arms": psc, "arms_beating_baseline_any": allf,
                     "arms_beating_baseline_same_learner": gated,
                     "ablation": compact_ablation(prep)}
            cell["placebo"][mode] = entry
            log(f"      placebo[{mode}] any={allf} same-learner={gated}; "
                + ", ".join(f"{r['unit']}={r['delta_ll']:.4f}" for r in prep["ranking"]))
            ablation_trial(prep, {**hdr, "placebo": f"shuffled_labels_{mode}"}, "placebo",
                           args.trials_path, {"source_evidence_role": ROLE,
                                              "data_provenance": hb.PROVENANCE,
                                              "revision": args.revision})
        lk = lab.copy()
        lk["leak_future_move"] = leak_column(lab, args.seed + 100 + k)
        lrep = ablate(lk, ycol, folds, base_cols, {**fams, "leak": ["leak_future_move"]},
                      clusters_x, args.n_boot_abl, ncls, eval_mask)
        cell["leak_positive_control"] = compact_ablation(lrep)
        ablation_trial(lrep, {**hdr, "placebo": "leak_positive_control"}, "placebo",
                       args.trials_path, {"source_evidence_role": ROLE,
                                          "data_provenance": hb.PROVENANCE,
                                          "revision": args.revision})
        apply_gate(cell, args.gate_modes)
    return cell


def run_horizon(k: int, args, markets: set[str], sink, placebo_sink, results: dict, run_dir: Path):
    hours = HORIZON_FILES[k]
    log(f"horizon k={k} ({hours}h): loading panel")
    df = load_panel(run_dir / f"panel_H{hours}h.csv.gz", markets)
    df, ext = join_external(df, args.book_table, args.wallet_age_table)
    placeholder = placeholder_report(df)
    if not args.include_untraded:
        df = df[df["traded_before_t"] != 0].reset_index(drop=True)
    sha = provenance.git_state().get("git_head", "unknown")

    def plan(frame):
        return ml_panel.plan_folds(
            ml_panel.period_table(frame), policy=ml_panel.category_policy(), feature_vers={},
            code_sha=sha, block=args.block_periods, min_train=args.min_train_periods,
            embargo_s=k * hb.GRID_S, horizon=k)

    manifest = plan(df)
    res: dict = {"panel": {"rows": int(len(df)), "labelled": int(df["target_available"].sum()),
                           "periods": len(manifest["periods"]),
                           "n_folds": len(manifest["folds"]),
                           "markets": int(df["market_id"].nunique())},
                 "external": ext, "placeholder_price_rule": placeholder,
                 "primary_excludes_untraded": not args.include_untraded, "m0v": list(M0V)}
    if len(manifest["folds"]) < 2:
        res["error"] = "fewer than 2 folds; not run"
        results[str(k)] = res
        return
    lab = ml_panel.labelled(df).reset_index(drop=True)
    del df
    state_ext = tuple(c for c in (*STATE_COLS, *hb.HIST_EXTRA_NAMES) if c in lab.columns)
    flow = tuple(usable(FLOW_COLS, lab))
    wallet = tuple(usable(WALLET_COLS, lab))
    book = tuple(usable(SW_COLS, lab, 0.01)) if ext["book"] else ()
    wage = tuple(usable([c for c in lab.columns if c.startswith(WAGE_PREFIXES)], lab,
                        0.01)) if ext["wallet_age"] else ()
    parts = (state_ext, flow, wallet, (*book, *wage), book)
    res["coverage"] = {c: float(lab[c].notna().mean())
                       for c in (*FLOW_COLS, *WALLET_COLS, *hb.HIST_EXTRA_NAMES,
                                 "ml_log_hours_to_end")}
    sink.extra.update(horizon_snapshots_k=k, horizon_hours=hours, baseline="M0v",
                      primary_excludes_untraded=not args.include_untraded)
    placebo_sink.extra.update(horizon_snapshots_k=k, horizon_hours=hours, baseline="M0v")
    for kind in args.kinds:
        log(f"  kind {kind}")
        if kind == "updown":
            moved = lab[lab["y_class"] != ml_panel.CLASS_FLAT].reset_index(drop=True).copy()
            moved["y_absmove"] = (moved["y_class"] == ml_panel.CLASS_UP).astype(float)
            try:
                man_u = plan(moved)
            except ValueError as exc:
                res[kind] = {"error": str(exc)}
                continue
            if len(man_u["folds"]) < 2:
                res[kind] = {"error": "fewer than 2 folds on moved rows"}
                continue
            res[kind] = run_kind(kind, moved, man_u, k, hours, args, sink, placebo_sink,
                                 run_dir, ext, parts)
            res[kind]["moved_up_share"] = float(moved["y_absmove"].mean())
        else:
            res[kind] = run_kind(kind, lab, manifest, k, hours, args, sink, placebo_sink,
                                 run_dir, ext, parts)
        results[str(k)] = res
        (run_dir / f"ml_history_results_{args.revision}.json").write_text(
            json.dumps(results, indent=1, default=float))
    results[str(k)] = res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--root", type=Path, default=HIST_ROOT)
    ap.add_argument("--max-rows", type=int, default=150_000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--horizons", default="1,3,12")
    ap.add_argument("--targets", default="direction,absmove,updown",
                    help="direction (3-class), absmove (will it move), updown (up vs down given a "
                    "move, fitted on moved rows only)")
    ap.add_argument("--gate-modes", default="global",
                    help="shuffle modes whose failure blocks every 'demonstrated' label")
    ap.add_argument("--placebo-diag-all", action="store_true",
                    help="run the period/market shuffle diagnostics at every horizon")
    ap.add_argument("--block-periods", type=int, default=240, help="test block, 2h periods")
    ap.add_argument("--min-train-periods", type=int, default=480)
    ap.add_argument("--n-boot", type=int, default=500)
    ap.add_argument("--n-boot-ablation", type=int, default=None,
                    help="bootstrap draws for the ablation p-values (BY needs p resolution: with "
                    "m_total tests the smallest passable p is about q / (m_total * H(m_total)))")
    ap.add_argument("--lgb-configs", type=int, default=6,
                    help="nested-tuning budget: first N of the declared LightGBM grid")
    ap.add_argument("--no-placebo", dest="placebo", action="store_false")
    ap.add_argument("--placebo-all", action="store_true")
    ap.add_argument("--skip-arms", action="store_true", help="ablation only")
    ap.add_argument("--book-table", type=Path, default=None,
                    help="optional pmxt book_features.csv.gz (history_sources.load_book_features)")
    ap.add_argument("--wallet-age-table", type=Path, default=None,
                    help="optional (market_id, origin_ts, ml_wage_*) table")
    ap.add_argument("--include-untraded", action="store_true",
                    help="sensitivity only: keep rows with no prior trade (placeholder prices)")
    ap.add_argument("--keep-subset", action="store_true",
                    help="with external tables: add their markets to the seeded subset instead of "
                    "restricting to them")
    ap.add_argument("--drill-flow", action="store_true",
                    help="split the flow family into last-trade-vs-price, signed flow, intensity")
    ap.add_argument("--revision", default="r0_no_external",
                    help="separate governance revision label stamped on every trial line")
    ap.add_argument("--trials-path", type=Path, default=provenance.TRIALS_PATH)
    a = ap.parse_args(argv)
    a.kinds = [t for t in a.targets.split(",") if t]
    a.gate_modes = [m for m in a.gate_modes.split(",") if m]
    a.n_boot_abl = a.n_boot_ablation or a.n_boot
    run_dir = a.root / a.run_id
    ml_models.LGB_GRID = ml_models.LGB_GRID[: a.lgb_configs]
    ml_panel.register_tier_a()
    ml_panel.register_extended()
    first = run_dir / f"panel_H{HORIZON_FILES[1]}h.csv.gz"
    markets, rows = pick_markets(first, a.max_rows, a.seed)
    for tab in (a.book_table,):  # sparse table: use its markets (wallet_age covers every origin)
        if tab is not None and Path(tab).exists():
            ids = set(pd.read_csv(tab, usecols=["market_id"], dtype=str)["market_id"])
            markets = markets | ids if a.keep_subset else ids
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
        "features": {"m0v": list(M0V), "state": list(STATE_COLS), "flow": list(FLOW_COLS),
                     "wallet": list(WALLET_COLS)},
    }
    sink = ml_models.TrialSink(dataset=f"history:{a.run_id}", path=a.trials_path,
                               evidence_role=ROLE,
                               extra={"data_provenance": hb.PROVENANCE, "revision": a.revision})
    placebo_sink = ml_models.TrialSink(
        dataset=f"history:{a.run_id}", path=a.trials_path, evidence_role="placebo",
        extra={"data_provenance": hb.PROVENANCE, "source_evidence_role": ROLE,
               "placebo": "shuffled_labels_within_period", "revision": a.revision})
    for k in [int(x) for x in a.horizons.split(",")]:
        with heavy_lock():
            run_horizon(k, a, markets, sink, placebo_sink, results, run_dir)
    (run_dir / f"ml_history_results_{a.revision}.json").write_text(
        json.dumps(results, indent=1, default=float))
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
