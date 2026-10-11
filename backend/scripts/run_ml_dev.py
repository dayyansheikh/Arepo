"""Multi-signal pipeline development runner (arms M0, M1, M2, M3_eb, placebo, sweep-gap, SHAP).

Design: ``docs/research_lab/MULTI_SIGNAL_PIPELINE_DESIGN.md`` sections 4, 6 and the pre-declared
sweep-gap diagnostic. Everything here is DEVELOPMENT/post-hoc: no edge, calibration or
profitability claim is ever made.

Usage::

    python backend/scripts/run_ml_dev.py --dry-run   # panel + folds only; fits and logs nothing
    python backend/scripts/run_ml_dev.py             # real run: refused below the 40-snapshot gate

Gate (design section 6): at least 40 *consecutive* complete snapshots with the sidecar present,
consecutive meaning every start-to-start gap lies in [1.5, 3.0] h (the ``ml_panel`` pairing rule).
Snapshots are only read, never modified. The panel is built period by period by
``ml_panel.build_panel`` (two snapshots and one sweep in memory at once) and cached as parquet
under ``data-dumps/research_lab/ml_cache/<panel hash>/``.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import resource
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

DUMPS = ROOT / "data-dumps" / "research_lab"
SNAPSHOT_ROOT = DUMPS / "snapshots"
SWEEP_ROOT = DUMPS / "book_sweeps"
CACHE_ROOT = DUMPS / "ml_cache"
OUT_DIR = ROOT / "docs" / "research_lab" / "ml_dev"

MIN_SNAPSHOTS = 40
CADENCE_H = 2.0
HASHED_MODULES = ("ml_panel", "panel", "features", "features_dev", "evaluate")


# ---------------------------------------------------------------------------------------------
# Discovery and the development gate
# ---------------------------------------------------------------------------------------------


def _start_epoch(cap: dict) -> float:
    return pd.Timestamp(cap["started_utc"]).timestamp()


def has_complete_sidecar(snapshot_dir: Path) -> bool:
    d = Path(snapshot_dir)
    mp = d / "ext_manifest.json"
    if not (d / "rows_ext.csv.gz").exists() or not mp.exists():
        return False
    try:
        return json.loads(mp.read_text()).get("sidecar_status") == "complete"
    except (OSError, ValueError):
        return False


def discover_captures(snapshot_root: Path) -> list[dict]:
    """Complete snapshots ordered by start. Reads manifests only."""
    caps = []
    for mp in Path(snapshot_root).glob("*/manifest.json"):
        man = json.loads(mp.read_text())
        if man.get("state") != "complete":
            continue
        caps.append({"capture_id": man["capture_id"], "started_utc": man["started_utc"],
                     "finished_utc": man.get("finished_utc"), "dir": str(mp.parent),
                     "sidecar": has_complete_sidecar(mp.parent)})
    return sorted(caps, key=_start_epoch)


def consecutive_runs(caps: list[dict]) -> list[list[dict]]:
    """Maximal runs of sidecar-complete snapshots with every start gap in [GAP_MIN_H, GAP_MAX_H]."""
    from astrolabe.research_lab import ml_panel

    runs: list[list[dict]] = []
    cur: list[dict] = []
    for c in caps:
        if not c["sidecar"]:
            if cur:
                runs.append(cur)
            cur = []
            continue
        if cur:
            gap_h = (_start_epoch(c) - _start_epoch(cur[-1])) / 3600.0
            if not (ml_panel.GAP_MIN_H <= gap_h <= ml_panel.GAP_MAX_H):
                runs.append(cur)
                cur = []
        cur.append(c)
    if cur:
        runs.append(cur)
    return runs


def gate_status(
    caps: list[dict], minimum: int = MIN_SNAPSHOTS, now: datetime | None = None
) -> dict:
    runs = consecutive_runs(caps)
    longest = max(runs, key=len) if runs else []
    trailing = runs[-1] if runs and caps and runs[-1][-1] is caps[-1] else []
    now = now or datetime.now(UTC)
    remaining = max(minimum - max(len(longest), len(trailing)), 0)
    anchor = datetime.fromtimestamp(_start_epoch(trailing[-1]), UTC) if trailing else now
    return {
        "minimum": minimum,
        "complete_snapshots": len(caps),
        "qualifying_with_sidecar": sum(c["sidecar"] for c in caps),
        "longest_consecutive_run": len(longest),
        "current_run": len(trailing),
        "met": len(longest) >= minimum,
        "remaining": remaining,
        "eta_utc": None if remaining == 0 else
        (anchor + timedelta(hours=CADENCE_H * remaining)).strftime("%Y-%m-%dT%H:%MZ"),
        "eta_assumption": f"{CADENCE_H:g}h cadence continuing from the latest qualifying snapshot",
        "run_capture_ids": [c["capture_id"] for c in longest],
    }


def usable_sweeps(sweep_root: Path, caps: list[dict]) -> tuple[dict, dict]:
    """Declared A sweeps (``ml_panel.pick_sweeps``) restricted to those ``build_period`` accepts:
    started at or after their snapshot's start and finished before the next snapshot starts."""
    from astrolabe.research_lab import ml_panel

    if not Path(sweep_root).exists():
        return {}, {"considered": 0, "used": 0}
    picked, report = ml_panel.pick_sweeps(sweep_root)
    out, dropped = {}, []
    for k, cap in enumerate(caps[:-1]):
        sw = picked.get(cap["capture_id"])
        if sw is None:
            continue
        if sw["started_epoch"] < _start_epoch(cap):
            dropped.append({"sweep_id": sw["sweep_id"], "reason": "started before its snapshot"})
        elif sw["receipt_epoch"] > _start_epoch(caps[k + 1]):
            dropped.append({"sweep_id": sw["sweep_id"], "reason": "finished after next snapshot"})
        else:
            out[cap["capture_id"]] = sw
    return out, {**report, "used": len(out), "dropped": dropped}


# ---------------------------------------------------------------------------------------------
# Panel (cached parquet keyed by panel hash)
# ---------------------------------------------------------------------------------------------


def panel_hash(caps: list[dict], sweeps: dict, policy: dict, delta: float) -> str:
    from astrolabe.research_lab import ml_panel, provenance

    here = Path(ml_panel.__file__).parent
    body = {
        "captures": [[c["capture_id"], c["started_utc"], bool(c["sidecar"])] for c in caps],
        "sweeps": {k: [v["sweep_id"], v["returned"], v["eligible"]]
                   for k, v in sorted(sweeps.items())},
        "policy": policy, "delta": delta,
        "features": ml_panel.extended_feature_versions(),
        "modules": {m: provenance.sha256_file(here / f"{m}.py") for m in HASHED_MODULES},
        "dep_underlying_date": ml_panel.DEP_GROUP_UNDERLYING,
    }
    blob = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _jsonable(o):
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (Path, datetime)):
        return str(o)
    raise TypeError(f"not serialisable: {type(o)}")


def _clean(o):
    """NaN/inf -> None so the output is strict JSON."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return _clean(o.tolist())
    if isinstance(o, np.generic):
        return _clean(o.item())
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def get_panel(caps, sweeps, policy, delta, cache_root: Path, rebuild: bool = False):
    """Returns (panel, counts, hash, cache_dir, from_cache). Snapshots are only read."""
    from astrolabe.research_lab import ml_panel

    h = panel_hash(caps, sweeps, policy, delta)
    cdir = Path(cache_root) / h
    pq, meta = cdir / "panel.parquet", cdir / "meta.json"
    if pq.exists() and meta.exists() and not rebuild:
        df = pd.read_parquet(pq)
        m = json.loads(meta.read_text())
        df.attrs["category_info"] = m["category_info"]
        return df, m["counts"], h, cdir, True
    df, counts = ml_panel.build_panel(caps, sweep_receipts=sweeps, delta=delta, policy=policy)
    cdir.mkdir(parents=True, exist_ok=True)
    tmp = cdir / "panel.parquet.tmp"
    df.to_parquet(tmp, index=False)
    tmp.replace(pq)
    meta.write_text(json.dumps(_clean({"counts": counts, "category_info": df.attrs["category_info"],
                                       "n_rows": len(df)}), default=_jsonable))
    return df, counts, h, cdir, False


def code_sha() -> str:
    from astrolabe.research_lab import provenance

    g = provenance.git_state()
    return g["git_head"] + ("+dirty" if g["git_dirty"] else "")


def plan(df: pd.DataFrame) -> tuple[dict | None, str | None]:
    """Fold manifest, or (manifest-or-None, reason) when the panel cannot support one."""
    from astrolabe.research_lab import ml_panel

    if not len(df):
        return None, "empty panel"
    try:
        man = ml_panel.plan_folds(ml_panel.period_table(df), code_sha=code_sha(),
                                  feature_vers=ml_panel.extended_feature_versions(),
                                  category_info=df.attrs.get("category_info"))
    except ValueError as e:
        return None, str(e)
    if not man["folds"]:
        need = ml_panel.MIN_TRAIN_PERIODS + ml_panel.BLOCK_PERIODS
        return man, f"no full fold: {len(man['periods'])} periods, need at least {need}"
    return man, None


# ---------------------------------------------------------------------------------------------
# Panel summaries (used by the dry run and the report)
# ---------------------------------------------------------------------------------------------


def panel_summary(df: pd.DataFrame) -> dict:
    from astrolabe.research_lab import ml_panel

    lab = ml_panel.labelled(df)
    per = []
    for p, g in df.groupby("period"):
        gl = g[g["target_available"]]
        per.append({"period": int(p), "capture_i": g["capture_i"].iloc[0], "n_rows": int(len(g)),
                    "n_labelled": int(len(gl)),
                    "class_shares": ml_panel.class_shares(gl["y_class"]) if len(gl) else None})
    feats = [c for c in ml_panel.EXTENDED_NAMES if c in df.columns]
    nan_rates = {c: float(df[c].isna().mean()) for c in feats} if len(df) else {}
    ev = lab["event_id"].where(lab["event_id"].notna(), "mkt:" + lab["market_id"].astype(str))
    series = {"event": ev, "dep_group": lab["dep_group"],
              "dep_group_season": lab["dep_group_season"]}
    return {
        "n_rows": int(len(df)), "n_labelled": int(len(lab)),
        "n_periods": int(df["period"].nunique()) if len(df) else 0,
        "rows_per_period": per,
        "class_shares_labelled": ml_panel.class_shares(lab["y_class"]) if len(lab) else None,
        "feature_nan_rates": nan_rates,
        "k_clusters_labelled": {k: int(s.nunique()) for k, s in series.items()},
        "largest_cluster_share_labelled": {
            k: float(s.value_counts(normalize=True).iloc[0]) if len(s) else None
            for k, s in series.items()},
        "sweep_gap_rows": int(df["rep_sw_gap"].notna().sum()) if "rep_sw_gap" in df else 0,
    }


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e6 if sys.platform == "darwin" else r / 1e3


# ---------------------------------------------------------------------------------------------
# Dry run: builds the panel and folds; fits nothing, logs nothing
# ---------------------------------------------------------------------------------------------


def dry_run(snapshot_root: Path, sweep_root: Path, cache_root: Path, policy: dict,
            delta: float, rebuild: bool = False) -> dict:
    t0 = time.perf_counter()
    caps = discover_captures(snapshot_root)
    gate = gate_status(caps)
    gate_pub = {k: v for k, v in gate.items() if k != "run_capture_ids"}
    if len(caps) < 2:
        return {"mode": "dry-run", "gate": gate_pub, "error": "fewer than 2 complete snapshots"}
    sweeps, sweep_report = usable_sweeps(sweep_root, caps)
    df, counts, h, cdir, cached = get_panel(caps, sweeps, policy, delta, cache_root, rebuild)
    man, why = plan(df)
    return {
        "mode": "dry-run (nothing fitted on real labels, nothing logged)",
        "gate": gate_pub, "panel_hash": h, "cache_dir": str(cdir), "from_cache": cached,
        "n_snapshots_used": len(caps), "sweeps": sweep_report,
        "periods_skipped": [c for c in counts if c.get("skipped")],
        "panel": panel_summary(df),
        "folds": {"n_folds": len(man["folds"]) if man else 0, "reason": why,
                  "manifest_sha256": man["manifest_sha256"] if man else None,
                  "periods": len(man["periods"]) if man else 0},
        "seconds": round(time.perf_counter() - t0, 1), "peak_rss_mb": round(peak_rss_mb(), 0),
    }


def print_dry(out: dict) -> None:
    g, p = out["gate"], out.get("panel")
    state = "MET" if g["met"] else f"NOT MET, ETA {g['eta_utc']}"
    print(f"[dry-run] gate: {g['qualifying_with_sidecar']} sidecar snapshots of "
          f"{g['complete_snapshots']} complete; longest consecutive run "
          f"{g['longest_consecutive_run']}/{g['minimum']}; {state} ({g['eta_assumption']})")
    if p is None:
        print(out.get("error"))
        return
    src = "cache" if out["from_cache"] else "built"
    print(f"[dry-run] panel {out['panel_hash'][:12]} ({src}): "
          f"{p['n_rows']} rows, {p['n_labelled']} labelled, {p['n_periods']} periods")
    print(f"[dry-run] class shares: {p['class_shares_labelled']}")
    share = {k: None if v is None else round(v, 3)
             for k, v in p["largest_cluster_share_labelled"].items()}
    print(f"[dry-run] K (labelled): {p['k_clusters_labelled']}  largest share: {share}")
    print(f"[dry-run] folds: {out['folds']['n_folds']} ({out['folds']['reason']})")
    hi = sorted(p["feature_nan_rates"].items(), key=lambda kv: -kv[1])[:8]
    print("[dry-run] highest NaN rates: " + ", ".join(f"{k}={v:.2f}" for k, v in hi))
    print(f"[dry-run] sweeps used {out['sweeps'].get('used')}, gap rows {p['sweep_gap_rows']}; "
          f"{out['seconds']}s, peak RSS {out['peak_rss_mb']:.0f} MB")


# ---------------------------------------------------------------------------------------------
# Probe arms (gap placebo and sweep-gap re-score): M0 logistic on declared column sets
# ---------------------------------------------------------------------------------------------


@contextlib.contextmanager
def _m0_columns(cols):
    """Run ``ml_models.fit_m0`` on a different column set without editing ml_models."""
    from astrolabe.research_lab import ml_models as mm

    old = mm.M0_FEATURES
    mm.M0_FEATURES = tuple(cols)
    try:
        yield
    finally:
        mm.M0_FEATURES = old


def fit_probe(name: str, cols, lab, manifest, sink, fn=None):
    from astrolabe.research_lab import ml_models as mm

    mm.ARMS[name] = fn or mm.fit_m0
    try:
        with _m0_columns(cols or mm.M0_FEATURES):
            return mm.run_arm(name, lab, manifest, sink=sink)
    finally:
        mm.ARMS.pop(name, None)


def run_gap_diagnostics(lab, manifest, results, sink) -> dict:
    """Gap placebo (M0 + gap, report-only), sweep-gap diagnostic and its re-score."""
    from astrolabe.research_lab import ml_models as mm
    from astrolabe.research_lab import ml_panel

    base = list(mm.M0_FEATURES)
    sw = list(ml_panel.SWEEP_NAMES)
    probes = {
        "M0_gap_placebo": [*base, "rep_sw_gap"],
        "M0_probe_sw": [*base, *sw],
        "M0_probe_sw_gap": [*base, *sw, "rep_sw_gap"],
    }
    fits = {n: fit_probe(n, c, lab, manifest, sink) for n, c in probes.items()}
    by_cols = {tuple(base): results["M0"], **{tuple(probes[n]): fits[n] for n in probes}}
    y = lab["y_class"].to_numpy(float)

    def score_fn(d: pd.DataFrame, cols: list[str]) -> float:
        r = by_cols[tuple(cols)]
        idx = d.index.to_numpy()
        idx = idx[r.test_mask[idx]]
        return float(mm.log_loss_rows(r.proba[idx], y[idx].astype(int)).mean())

    return {
        "status": "REPORT-ONLY, non-gating (gap placebo and sweep-gap diagnostic)",
        "correlations": ml_panel.sweep_gap_diagnostic(lab),
        "rescore": ml_panel.rescore_with_gap_control(lab, base, score_fn),
        "fits": fits,
    }


SHUFFLE_SEED = 116
LEAK_COLUMN = "dmid"  # the target-snapshot move itself: a deliberate leak


def shuffle_labels(lab: pd.DataFrame, seed: int = SHUFFLE_SEED) -> pd.DataFrame:
    """Labels permuted within period x event blocks (design section 4), seeded. Features and
    all timing columns are untouched, so the fold plan and purge are unchanged."""
    rng = np.random.default_rng(seed)
    out = lab.copy()
    y = out["y_class"].to_numpy(float).copy()
    ev = out["event_id"].where(out["event_id"].notna(), "mkt:" + out["market_id"].astype(str))
    key = out["period"].astype(str) + "|" + ev.astype(str)
    for idx in out.groupby(key, sort=True).indices.values():
        y[idx] = y[rng.permutation(idx)]
    out["y_class"] = y
    return out


def run_placebos(lab, manifest, results, clusters, sink) -> dict:
    """Report-only placebos, logged as placebo arms: shuffled labels (M0 and M1 refitted on the
    permuted labels), the target-snapshot leak positive control (M0 + dmid; it must win big) and
    the quote-age-only model (M0 + quote staleness). Never enters a verdict."""
    from astrolabe.research_lab import ml_models as mm

    base = list(mm.M0_FEATURES)
    shuf = shuffle_labels(lab)
    m0s = fit_probe("M0_placebo_shuffled", None, shuf, manifest, sink)
    m1s = fit_probe("M1_placebo_shuffled", None, shuf, manifest, sink, fn=mm.fit_m1)
    m0 = results["M0"]
    leak = fit_probe("M0_placebo_leak", [*base, LEAK_COLUMN], lab, manifest, sink)
    qage = fit_probe("M0_placebo_quote_age", [*base, "ml_quote_staleness_h"], lab, manifest, sink)
    out = {
        "status": "REPORT-ONLY placebos; never enter a verdict",
        "shuffled_labels": mm.score_arms(
            shuf, {"M0": m0s, "M1_placebo_shuffled": m1s}, clusters, sink=sink, manifest=manifest),
        "leak_positive_control": mm.score_arms(
            lab, {"M0": m0, "M0_placebo_leak": leak}, clusters, sink=sink, manifest=manifest),
        "quote_age_only": mm.score_arms(
            lab, {"M0": m0, "M0_placebo_quote_age": qage}, clusters, sink=sink, manifest=manifest),
    }
    return out


# ---------------------------------------------------------------------------------------------
# Real development run
# ---------------------------------------------------------------------------------------------


def _count_lines(path: Path) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    with open(p, encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def accounting(results: dict, probes: dict, trials_before: int, trials_path: Path) -> dict:
    n_fit = {a: len(r.folds) for a, r in {**results, **probes}.items()}
    configs = {a: sum(len(f.get("hyper_search", [])) for f in r.folds) for a, r in results.items()}
    after = _count_lines(trials_path)
    return {"fold_fits_per_arm": n_fit, "tuning_configs_evaluated_inside_folds": configs,
            "trial_lines_before": trials_before, "trial_lines_after": after,
            "trial_lines_written": after - trials_before}


def real_run(args, caps, gate, policy) -> dict:
    from astrolabe.research_lab import ml_models as mm
    from astrolabe.research_lab import ml_panel, provenance

    t0 = time.perf_counter()
    run_ids = set(gate["run_capture_ids"])
    run_caps = [c for c in caps if c["capture_id"] in run_ids]
    sweeps, sweep_report = usable_sweeps(args.sweep_root, run_caps)
    df, counts, h, cdir, cached = get_panel(run_caps, sweeps, policy, args.delta,
                                            args.cache_root, args.rebuild)
    man, why = plan(df)
    if man is None or why:
        raise SystemExit(f"cannot plan folds: {why}")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    stem = f"ml_dev_{stamp}_{man['manifest_sha256'][:8]}"
    # the manifest is written (and hashed) before any fit
    (out_dir / f"{stem}_fold_manifest.json").write_text(
        json.dumps(_clean(man), indent=1, default=_jsonable))
    lab = ml_panel.labelled(df)
    trials_path = Path(args.trials_path)
    before = _count_lines(trials_path)
    sink = mm.TrialSink(dataset=f"ml_dev panel {h[:12]}", path=trials_path)

    results = mm.run_arms(lab, man, mm.ARM_NAMES, sink=sink, collect_shap=True)
    clusters = mm.cluster_vectors(lab, lab["dep_group"].to_numpy())
    clusters["dep_group_season"] = lab["dep_group_season"].to_numpy()  # sensitivity S1
    score = mm.score_arms(lab, results, clusters, sink=sink, manifest=man)
    shap = mm.summarize_shap(lab, results["M2"])

    diag, probe_results = None, {}
    sweep_used = bool(
        len(lab) and lab[list(ml_panel.SWEEP_NAMES)].notna().any().any()
        and lab["rep_sw_gap"].notna().any())
    if sweep_used:
        diag = run_gap_diagnostics(lab, man, results, sink)
        probe_results = diag.pop("fits")
        diag["gap_placebo_vs_M0"] = mm.score_arms(
            lab, {"M0": results["M0"], "M0_gap_placebo": probe_results["M0_gap_placebo"]},
            clusters, sink=sink, manifest=man)
    placebos = run_placebos(lab, man, results, clusters, sink)
    report = {
        "placebos": placebos,
        "status": "DEVELOPMENT/post-hoc. Exploratory. No edge, calibration or profitability claim.",
        "utc": stamp, "panel_hash": h, "from_cache": cached, "cache_dir": str(cdir),
        "gate": {k: v for k, v in gate.items() if k != "run_capture_ids"},
        "capture_ids": [c["capture_id"] for c in run_caps], "sweeps": sweep_report,
        "manifest_sha256": man["manifest_sha256"], "n_folds": len(man["folds"]),
        "category_policy": man["category_policy"], "code_sha": man["code_sha"],
        "panel": panel_summary(df), "score": score, "shap": shap,
        "sweep_features_in_probe": sweep_used,
        "sweep_gap": diag if diag else {
            "status": "not run: no sweep features or sweep-minus-Gamma gap in the labelled panel"},
        "arms_use_sweep_features": False,
        "arm_fold_diagnostics": {a: r.folds for a, r in {**results, **probe_results}.items()},
        "accounting": accounting(results, probe_results, before, trials_path),
        "provenance": provenance.run_provenance(),
        "seconds": round(time.perf_counter() - t0, 1), "peak_rss_mb": round(peak_rss_mb(), 0),
    }
    report = _clean(report)
    jp, mp = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    jp.write_text(json.dumps(report, indent=1, default=_jsonable))
    mp.write_text(render_md(report))
    report["_paths"] = [str(jp), str(mp)]
    return report


def render_md(r: dict) -> str:
    def f(x, nd=4):
        return "n/a" if x is None else f"{x:.{nd}f}"

    sc, pn = r["score"], r["panel"]
    L = [f"# ML development run {r['utc']}", "", f"**{r['status']}**", "",
         f"- Panel `{r['panel_hash'][:12]}`: {pn['n_rows']} rows, {pn['n_labelled']} labelled, "
         f"{pn['n_periods']} periods, {r['n_folds']} folds; "
         f"manifest `{r['manifest_sha256'][:12]}`.",
         f"- Gate: longest consecutive sidecar run {r['gate']['longest_consecutive_run']} "
         f"(minimum {r['gate']['minimum']}).",
         f"- K (labelled rows): {pn['k_clusters_labelled']}; class shares "
         f"{pn['class_shares_labelled']}.",
         f"- Code `{r['code_sha']}`; {r['seconds']}s, peak RSS {r['peak_rss_mb']:.0f} MB.", ""]
    if sc["non_inferential"]:
        L += [f"**{sc['non_inferential_reason']}**", ""]
    L += ["## Out-of-fold scores", "", "| arm | log loss | Brier |", "|---|---|---|"]
    L += [f"| {a} | {f(v['log_loss'])} | {f(v['brier'])} |" for a, v in sc["arms"].items()]
    L += ["", "## Relative log-loss improvement vs M0 (95% clustered CI)", ""]
    names = {"event": "event (co-primary)",
             "dependence_group": "fixture-day dep_group (co-primary)",
             "dep_group_season": "season-level dep_group (sensitivity S1)"}
    for cname, blk in sc["bootstrap"].items():
        L += [f"### {names.get(cname, cname)}: K = {blk['n_clusters']}", "",
              "| arm | rel. improvement | CI95 |", "|---|---|---|"]
        for a, e in blk["log_loss"].items():
            ci = e["ci95"] or [None, None]
            L.append(f"| {a} | {f(e['rel_improvement'])} | [{f(ci[0])}, {f(ci[1])}] |")
        L.append("")
    L += ["A claim needs the CI to exclude 0 under BOTH co-primary clusterings; S1 is reported "
          "alongside. Development only.", "",
          "## Sweep-gap diagnostic and gap placebo (report-only, non-gating)", ""]
    sg = r["sweep_gap"]
    if "rescore" in sg:
        for tag, blk in sg["rescore"].items():
            L.append(f"- `{tag}`: sweep gain {f(blk['gain_sweep'], 5)}, with gap controlled "
                     f"{f(blk['gain_sweep_given_gap'], 5)} (log-loss units).")
        c = sg["correlations"]
        L.append(f"- share |gap| < 0.0025: {f(c['share_abs_gap_lt_0025'], 3)}; "
                 f"median |gap| {f(c['gap_abs_median'], 5)}.")
    else:
        L.append(sg["status"])
    for tag, key, arm in (("Shuffled labels (expect ~0)", "shuffled_labels", "M1_placebo_shuffled"),
                          ("Leak positive control (must win)", "leak_positive_control",
                           "M0_placebo_leak"),
                          ("Quote-age-only", "quote_age_only", "M0_placebo_quote_age")):
        blk = r["placebos"][key]["bootstrap"]["event"]["log_loss"][arm]
        L.append(f"- Placebo, {tag}: rel. log-loss improvement vs M0 "
                 f"{f(blk['rel_improvement'])} (event-cluster CI {blk['ci95']}).")
    L += ["", f"Arms M0-M3_eb use no sweep features (`arms_use_sweep_features = "
          f"{r['arms_use_sweep_features']}`); sweep features enter only the report-only probes.",
          "", "## SHAP (M2, out-of-fold, exploratory)", "",
          "Never evidence of edge or mechanism. Mean |SHAP| by family (up minus down):", ""]
    fam = r["shap"]["margins"]["up_minus_down"]["mean_abs_by_family"]
    L += [f"- {k}: {f(v)}" for k, v in sorted(fam.items(), key=lambda kv: -kv[1])]
    a = r["accounting"]
    L += ["", "## Search accounting", "",
          f"- Fold fits per arm: {a['fold_fits_per_arm']}",
          f"- Tuning configs evaluated inside folds: {a['tuning_configs_evaluated_inside_folds']}",
          f"- Trial lines written to trials.jsonl: {a['trial_lines_written']}", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    from astrolabe.research_lab import ml_panel, provenance

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot-root", type=Path, default=SNAPSHOT_ROOT)
    ap.add_argument("--sweep-root", type=Path, default=SWEEP_ROOT)
    ap.add_argument("--cache-root", type=Path, default=CACHE_ROOT)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--trials-path", type=Path, default=provenance.TRIALS_PATH)
    ap.add_argument("--delta", type=float, default=ml_panel.DELTA_PRIMARY)
    ap.add_argument("--category-mode", choices=ml_panel.CATEGORY_MODES, default="all")
    ap.add_argument("--categories", default="", help="comma-separated fee categories")
    ap.add_argument("--min-snapshots", type=int, default=MIN_SNAPSHOTS)
    ap.add_argument("--rebuild", action="store_true", help="ignore the parquet cache")
    args = ap.parse_args(argv)
    policy = ml_panel.category_policy(
        args.category_mode, [c for c in args.categories.split(",") if c])

    if args.dry_run:
        out = dry_run(args.snapshot_root, args.sweep_root, args.cache_root, policy, args.delta,
                      args.rebuild)
        print_dry(out)
        Path(args.cache_root).mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        path = Path(args.cache_root) / f"dry_run_{now}.json"
        path.write_text(json.dumps(_clean(out), indent=1, default=_jsonable))
        print(f"[dry-run] summary: {path}")
        return 0

    caps = discover_captures(args.snapshot_root)
    gate = gate_status(caps, args.min_snapshots)
    if not gate["met"]:
        print(f"REFUSED: development gate not met. {gate['longest_consecutive_run']} consecutive "
              f"sidecar-complete snapshots exist ({gate['qualifying_with_sidecar']} with sidecar, "
              f"{gate['complete_snapshots']} complete); {gate['minimum']} required.")
        print(f"ETA: {gate['eta_utc']} ({gate['eta_assumption']}). Use --dry-run to inspect.")
        return 2
    rep = real_run(args, caps, gate, policy)
    print("DEVELOPMENT RUN (not evidence). Reports: " + ", ".join(rep["_paths"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
