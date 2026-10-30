"""E007: order-flow continuation in trade-active markets (spec: EXPERIMENT_LEDGER.md, E007).

Frozen model: unweighted OLS fitted on development trade-active periods (``fit_dev``), written
once to ``data-dumps/research_lab/e007/dev_fit.json``. Confirmation (``score``) uses only samples
whose seed was sealed after the registration commit, one period per distinct source snapshot, and
pairs each with the next complete snapshot (``flow_screen.build_sample_pairs`` semantics). Primary:
WLS of the frozen-base residual on [period intercepts, chg_1h, signed_share] with weights 1/p and
an event-clustered bootstrap for the signed_share slope. Nothing here is a tradable-edge claim.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluate, flow_screen, forecast, provenance

REGISTRATION_COMMIT = "1e5efad"
CODE_PATH = Path(__file__).resolve()
LEDGER_PATH = forecast.ROOT / "docs" / "research_lab" / "EXPERIMENT_LEDGER.md"
E007_DIR = forecast.ROOT / "data-dumps" / "research_lab" / "e007"
SAMPLE_ROOT = flow_screen.SAMPLE_ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
DEV_SOURCES = (
    "20261011T022316Z_f3cab565",
    "20261011T042034Z_61d89e9e",
    "20261011T061923Z_af6fc26d",
    "20261011T081844Z_24399984",
)
N_PERIODS = 12
MIN_NONZERO = 150
MIN_TOTAL_NONZERO = 2000
MAX_GAP_H = 3.0
DEADLINE_DAYS = 7
MIN_CONSISTENT = 8
BASE_COLS = ("chg_1h",)
AUG_COLS = ("chg_1h", "signed_share")


# --- sample metadata and classification ---------------------------------------------------------


def _ts(s) -> datetime | None:
    if s is None or (isinstance(s, float) and np.isnan(s)) or s == "":
        return None
    return forecast._parse_ts(str(s))


def sample_meta(sample_dir: Path) -> dict:
    """Sealing time, state, frame, source and request-time span of one trade sample."""
    sample_dir = Path(sample_dir)
    man = json.loads((sample_dir / "manifest.json").read_text())
    sealed = _ts(man.get("started_utc"))
    first = last = None
    fp = sample_dir / "features.csv.gz"
    span_p = sample_dir.parent.parent / "pair_cache" / f"{man['sample_id']}__sent_span.json"
    complete = man.get("state") == "complete"
    if fp.exists():
        sent = pd.to_datetime(pd.read_csv(fp, usecols=["sent_utc"])["sent_utc"], utc=True,
                              errors="coerce", format="ISO8601").dropna()
        if len(sent):
            first, last = sent.min().to_pydatetime(), sent.max().to_pydatetime()
            # stored for every state (rewritten while growing, frozen once complete) so the span
            # survives archiving and removal of features.csv.gz (RETENTION.md)
            if not (complete and span_p.exists()):
                try:
                    span_p.parent.mkdir(parents=True, exist_ok=True)
                    span = {"first": first.isoformat(), "last": last.isoformat()}
                    span_p.write_text(json.dumps(span))
                except OSError:
                    pass
    elif span_p.exists():
        span = json.loads(span_p.read_text())
        first, last = _ts(span["first"]), _ts(span["last"])
    elif complete:
        forecast.require_local(fp)  # archived and no stored span: never fall back silently
    if last is None:
        last = _ts(man.get("finished_utc"))
    return {
        "sample_id": man["sample_id"],
        "dir": str(sample_dir),
        "snapshot_id": man.get("snapshot_id"),
        "frame": man.get("frame", "eligible"),
        "state": man.get("state"),
        "sealed_utc": sealed,
        "first_sent": first or sealed,
        "last_sent": last,
    }


def list_metas(sample_root: Path = SAMPLE_ROOT) -> list[dict]:
    return [sample_meta(m.parent) for m in sorted(Path(sample_root).glob("*/manifest.json"))]


def registration_time() -> datetime:
    return forecast.registration_time(REGISTRATION_COMMIT)


def classify(metas: list[dict], captures: list[dict], reg_time: datetime,
             max_gap_h: float = MAX_GAP_H) -> tuple[list[dict], dict]:
    """Apply the qualification rules that need no pair data.

    Returns (candidates in source-snapshot order, exclusions {reason: [sample_id, ...]}).
    """
    excl: dict[str, list[str]] = {}

    def drop(reason: str, m: dict) -> None:
        excl.setdefault(reason, []).append(m["sample_id"])

    post = []
    for m in metas:
        if m["sealed_utc"] is None or m["sealed_utc"] <= reg_time:
            drop("seed_sealed_before_registration", m)
        elif m["frame"] != "active":
            drop("not_active_frame", m)
        else:
            post.append(m)
    pre_sources = {m["snapshot_id"] for m in metas
                   if m["sealed_utc"] is None or m["sealed_utc"] <= reg_time}
    by_src: dict[str, list[dict]] = {}
    for m in sorted(post, key=lambda x: (x["first_sent"], x["sample_id"])):
        by_src.setdefault(m["snapshot_id"], []).append(m)
    ids = [c["capture_id"] for c in captures]
    out = []
    for src, group in by_src.items():
        for later in group[1:]:
            drop("duplicate_source_snapshot", later)
        m = group[0]
        if src in pre_sources:
            drop("source_has_pre_registration_sample", m)
        elif m["state"] != "complete":
            drop("unavailable_sample_not_complete", m)
        elif src not in ids or ids.index(src) + 1 >= len(ids):
            drop("unavailable_no_target_snapshot", m)
        else:
            s_cap, t_cap = captures[ids.index(src)], captures[ids.index(src) + 1]
            gap = (t_cap["_start"] - s_cap["_start"]).total_seconds() / 3600.0
            if gap > max_gap_h:
                drop("target_gap_over_3h", m)
            elif m["last_sent"] is None or m["last_sent"] >= t_cap["_start"]:
                drop("requests_not_before_target_start", m)
            else:
                out.append({**m, "source_start": s_cap["_start"], "target": t_cap["capture_id"],
                            "gap_h": gap})
    out.sort(key=lambda m: m["source_start"])
    return out, excl


# --- OLS / WLS ---------------------------------------------------------------------------------


def ols(X: np.ndarray, y: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    sw = np.ones(len(y)) if w is None else np.sqrt(w)
    return np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]


def _design(pairs: pd.DataFrame, cols: tuple[str, ...]) -> np.ndarray:
    return np.column_stack([np.ones(len(pairs)), pairs[list(cols)].to_numpy(float)])


def predict(pairs: pd.DataFrame, coef: dict, cols: tuple[str, ...]) -> np.ndarray:
    return coef["intercept"] + sum(coef[c] * pairs[c].to_numpy(float) for c in cols)


def _coefs(pairs: pd.DataFrame, cols: tuple[str, ...]) -> dict:
    b = ols(_design(pairs, cols), pairs["dmid"].to_numpy(float))
    return {"intercept": float(b[0]), **{c: float(v) for c, v in zip(cols, b[1:], strict=True)}}


# --- development fit ---------------------------------------------------------------------------


def dev_pairs(sample_root: Path, snapshot_root: Path, reg_time: datetime) -> tuple[
        pd.DataFrame, dict]:
    """Development periods 1-4 (+ duplicate-source markets merged into period 4)."""
    captures = forecast.list_complete_captures(snapshot_root)
    metas = [m for m in list_metas(sample_root)
             if m["sealed_utc"] is not None and m["sealed_utc"] <= reg_time]
    used: set[str] = set()
    frames, counts, merged = [], [], {}
    for k, src in enumerate(DEV_SOURCES):
        group = sorted((m for m in metas if m["snapshot_id"] == src and m["frame"] == "active"
                        and m["state"] == "complete"), key=lambda m: m["first_sent"])
        if not group:
            raise ValueError(f"no complete active development sample for source {src}")
        first, rest = group[0], group[1:]
        pairs, c = flow_screen.build_sample_pairs(Path(first["dir"]), captures, k)
        if pairs is None:
            raise ValueError(f"development sample {first['sample_id']} has no target")
        used.add(first["sample_id"])
        counts.append(c)
        have = set(pairs["market_id"])
        for extra in rest:
            more, ce = flow_screen.build_sample_pairs(Path(extra["dir"]), captures, k)
            new = more[~more["market_id"].isin(have)]
            merged[extra["sample_id"]] = {"period": k, "pairs_in_sample": int(len(more)),
                                          "markets_not_in_first_sample": int(len(new))}
            pairs = pd.concat([pairs, new], ignore_index=True)
            used.add(extra["sample_id"])
            counts.append({**ce, "merged_into_period": k})
        frames.append(pairs)
    excluded = []
    for m in list_metas(sample_root):
        if m["sample_id"] in used:
            continue
        why = ("eligible frame (not trade-active)" if m["frame"] != "active"
               else "excluded_dev_sample")
        if m["sealed_utc"] is not None and m["sealed_utc"] <= reg_time:
            excluded.append({"sample_id": m["sample_id"], "state": m["state"],
                             "source": m["snapshot_id"], "reason": why})
    return pd.concat(frames, ignore_index=True), {
        "sample_counts": counts, "merged_duplicates": merged, "excluded_dev_samples": excluded}


def _manifest_hashes(sample_root: Path, snapshot_root: Path, counts: list[dict]) -> dict:
    out: dict = {"trade_samples": {}, "snapshots": {}}
    for c in counts:
        sd = Path(sample_root) / c["sample_id"]
        out["trade_samples"][c["sample_id"]] = {
            n: forecast.sha256_file(sd / n) for n in ("manifest.json", "plan.json")
        }
        for cid in (c["source_snapshot"], c.get("target_snapshot")):
            if cid:
                out["snapshots"][cid] = forecast.sha256_file(Path(snapshot_root) / cid /
                                                              "manifest.json")
    return out


def fit_dev(sample_root: Path = SAMPLE_ROOT, snapshot_root: Path = SNAPSHOT_ROOT,
            out_dir: Path = E007_DIR, reg_time: datetime | None = None) -> dict:
    """Fit the frozen base and augmented OLS on development data; refuse to overwrite."""
    out_path = Path(out_dir) / "dev_fit.json"
    if out_path.exists():
        raise FileExistsError(f"E007 dev fit already written (frozen): {out_path}")
    reg_time = reg_time or registration_time()
    pairs, info = dev_pairs(sample_root, snapshot_root, reg_time)
    nz = pairs["signed_share"] != 0
    per = {
        str(int(p) + 1): {"n": int(len(g)), "nonzero_signed_share": int((g["signed_share"] != 0)
                                                                      .sum())}
        for p, g in pairs.groupby("period")
    }
    fit = {
        "label": "E007 frozen model (development fit; not evidence)",
        "registration_commit": REGISTRATION_COMMIT,
        "registration_time": reg_time.isoformat(),
        "dev_sources": list(DEV_SOURCES),
        "base": _coefs(pairs, BASE_COLS),
        "augmented": _coefs(pairs, AUG_COLS),
        "weighting": "unweighted OLS",
        "n_total": int(len(pairs)),
        "nonzero_signed_share_total": int(nz.sum()),
        "per_period": per,
        "ledger_note": "ledger cites 1,646 new markets in the duplicate sample; this build "
                       "counts markets absent from the first sample's pairs",
        **info,
        "input_manifest_sha256": _manifest_hashes(sample_root, snapshot_root,
                                                  info["sample_counts"]),
        "provenance": {
            "code_sha256": forecast.sha256_file(CODE_PATH),
            **provenance.git_state(),
        },
    }
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(flow_screen.clean(fit), indent=1, sort_keys=True))
    return fit


def ledger_line(fit: dict, sha: str) -> str:
    per = ", ".join(f"P{k}: n={v['n']}, nz={v['nonzero_signed_share']}"
                    for k, v in sorted(fit["per_period"].items()))
    return (f"E007 dev_fit.json sha256: {sha} (n={fit['n_total']}, "
            f"nonzero signed_share={fit['nonzero_signed_share_total']}; {per})")


# --- confirmation ------------------------------------------------------------------------------


def build_confirmation(sample_root: Path, snapshot_root: Path, reg_time: datetime,
                       min_nonzero: int | None = None) -> tuple[list[dict], pd.DataFrame, dict]:
    """Qualifying periods (pair-level rule applied) with their pairs and exclusion counts."""
    min_nz = MIN_NONZERO if min_nonzero is None else min_nonzero
    captures = forecast.list_complete_captures(snapshot_root)
    cands, excl = classify(list_metas(sample_root), captures, reg_time)
    qual, frames = [], []
    for m in cands:
        k = len(qual)
        pairs, c = flow_screen.build_sample_pairs(Path(m["dir"]), captures, k)
        nz = 0 if pairs is None else int((pairs["signed_share"] != 0).sum())
        if pairs is None or nz < min_nz:
            excl.setdefault("fewer_than_150_nonzero_pairs", []).append(m["sample_id"])
            continue
        qual.append({"period": k, "sample_id": m["sample_id"], "source": m["snapshot_id"],
                     "target": m["target"], "gap_h": m["gap_h"], "pairs": int(len(pairs)),
                     "nonzero": nz})
        frames.append(pairs)
    allp = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return qual, allp, excl


def status(sample_root: Path = SAMPLE_ROOT, snapshot_root: Path = SNAPSHOT_ROOT,
           out_dir: Path = E007_DIR, reg_time: datetime | None = None,
           now: datetime | None = None, min_nonzero: int | None = None) -> dict:
    reg_time = reg_time or registration_time()
    now = now or datetime.now(UTC)
    qual, _pairs, excl = build_confirmation(sample_root, snapshot_root, reg_time, min_nonzero)
    deadline = reg_time + timedelta(days=DEADLINE_DAYS)
    return {
        "experiment": "E007",
        "qualifying": len(qual),
        "required": N_PERIODS,
        "ready": len(qual) >= N_PERIODS,
        "deadline_utc": deadline.isoformat(),
        "past_deadline": now > deadline,
        "nonzero_total": int(sum(q["nonzero"] for q in qual)),
        "qualifying_periods": qual,
        "excluded": {k: {"count": len(v), "samples": v} for k, v in excl.items()},
        "dev_fit_exists": (Path(out_dir) / "dev_fit.json").exists(),
        "results_exist": (Path(out_dir) / "results.json").exists(),
    }


def wls_stats(X: np.ndarray, r: np.ndarray, w: np.ndarray, keys: np.ndarray, n_boot: int,
              seed: int, j: int) -> dict:
    """WLS coefficient j with an event-clustered bootstrap (resample clusters; same RNG use as
    ``evaluate.clustered_bootstrap_r2``)."""
    codes, uniq = pd.factorize(keys)
    k, p = len(uniq), X.shape[1]
    xx = (w[:, None, None] * X[:, :, None] * X[:, None, :]).reshape(len(r), p * p)
    xr = w[:, None] * X * r[:, None]
    ca = np.column_stack([np.bincount(codes, weights=xx[:, i], minlength=k)
                          for i in range(p * p)])
    cb = np.column_stack([np.bincount(codes, weights=xr[:, i], minlength=k) for i in range(p)])
    est = float(np.linalg.lstsq(ca.sum(0).reshape(p, p), cb.sum(0), rcond=None)[0][j])
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        cnt = np.bincount(rng.integers(0, k, size=k), minlength=k).astype(float)
        vals[b] = np.linalg.lstsq((cnt @ ca).reshape(p, p), cnt @ cb, rcond=None)[0][j]
    lo, hi = np.percentile(vals, [2.5, 97.5])
    p_two = min(1.0, 2.0 * min(float((vals <= 0).mean()), float((vals >= 0).mean())))
    return {"beta": est, "ci_lo": float(lo), "ci_hi": float(hi), "p_two_sided": p_two,
            "n_clusters": int(k), "n_boot": int(n_boot)}


def analyse(pairs: pd.DataFrame, fit: dict, n_boot: int = evaluate.BOOT_N,
            seed: int = evaluate.BOOT_SEED) -> dict:
    """Primary, consistency and secondary results for the qualifying pairs."""
    pairs = pairs.reset_index(drop=True)
    y = pairs["dmid"].to_numpy(float)
    w = pairs["w"].to_numpy(float)
    base = predict(pairs, fit["base"], BASE_COLS)
    aug = predict(pairs, fit["augmented"], AUG_COLS)
    r = y - base
    keys = flow_screen.event_keys(pairs)
    n_no_event = int(np.sum(pd.Series(keys).astype(str).str.startswith("m:")))
    per_ids = sorted(pairs["period"].unique())
    dummies = np.column_stack([(pairs["period"].to_numpy() == p).astype(float) for p in per_ids])
    X = np.column_stack([dummies, pairs["chg_1h"].to_numpy(float),
                         pairs["signed_share"].to_numpy(float)])
    prim = wls_stats(X, r, w, keys, n_boot, seed, X.shape[1] - 1)
    reject = prim["ci_lo"] > 0 or prim["ci_hi"] < 0
    per_beta = {}
    for p in per_ids:
        m = (pairs["period"] == p).to_numpy()
        Xp = _design(pairs[m], AUG_COLS)
        per_beta[int(p)] = float(ols(Xp, r[m], w[m])[-1])
    n_pos = sum(1 for v in per_beta.values() if v > 0)
    contrast = flow_screen.contrast(pairs, base, aug, n_boot, seed, 1)
    wt = contrast["weighted"]
    sec = {k: wt.get(k) for k in ("delta_r2", "ci_lo", "ci_hi", "mde", "sd_c")}
    sec["per_period"] = wt["per_period"]
    sec["unweighted_delta_r2"] = contrast["unweighted"]["delta_r2"]
    sec["n_events"] = contrast["n_events"]
    sec["r2_base_vs_no_change"] = 1 - float(np.sum(w * (y - base) ** 2) / np.sum(w * y**2))
    sec["r2_augmented_vs_no_change"] = 1 - float(np.sum(w * (y - aug) ** 2) / np.sum(w * y**2))
    consistent = n_pos >= MIN_CONSISTENT
    if reject and prim["beta"] > 0 and consistent:
        verdict = "Supported (exploratory, prospective)"
    elif reject and prim["beta"] < 0:
        verdict = "Contradicted"
    else:
        verdict = "Inconclusive"
    return {
        "primary": {**prim, "rejects_zero": bool(reject), "bootstrap_seed": seed},
        "consistency": {"per_period_beta_ss": per_beta, "n_positive": n_pos,
                        "required": MIN_CONSISTENT, "met": bool(consistent)},
        "secondary_descriptive": sec,
        "events_without_event_id_fallback_to_market_id": n_no_event,
        "verdict": verdict,
        "category": {"status": "unavailable", "reason": "no category field in pairs or snapshot"
                     " rows used by the screen"},
    }


def _ledger_has(sha: str, ledger_path: Path) -> bool:
    return ledger_path.exists() and f"E007 dev_fit.json sha256: {sha}" in ledger_path.read_text()


def score(sample_root: Path = SAMPLE_ROOT, snapshot_root: Path = SNAPSHOT_ROOT,
          out_dir: Path = E007_DIR, reg_time: datetime | None = None,
          now: datetime | None = None, min_nonzero: int | None = None,
          ledger_path: Path = LEDGER_PATH, n_boot: int = evaluate.BOOT_N) -> dict | None:
    """Score once 12 periods qualify (or mark Unavailable past the deadline); refuse overwrite."""
    reg_time = reg_time or registration_time()
    now = now or datetime.now(UTC)
    out_path = Path(out_dir) / "results.json"
    fit_path = Path(out_dir) / "dev_fit.json"
    qual, pairs, excl = build_confirmation(sample_root, snapshot_root, reg_time, min_nonzero)
    deadline = reg_time + timedelta(days=DEADLINE_DAYS)
    if len(qual) < N_PERIODS and now <= deadline:
        return None
    if not fit_path.exists():
        raise FileNotFoundError(f"E007 requires the frozen dev fit first: {fit_path}")
    if out_path.exists():
        raise FileExistsError(f"E007 results already written (append-only): {out_path}")
    fit = json.loads(fit_path.read_text())
    qual = qual[:N_PERIODS]
    if len(qual) and len(pairs):
        pairs = pairs[pairs["period"] < len(qual)]
    nz_total = int(sum(q["nonzero"] for q in qual))
    sha = forecast.sha256_file(fit_path)
    res: dict = {
        "experiment": "E007",
        "qualifying_periods": qual,
        "excluded": {k: {"count": len(v), "samples": v} for k, v in excl.items()},
        "nonzero_total": nz_total,
        "no_edge_claim": True,
    }
    if len(qual) < N_PERIODS:
        res["verdict"] = "Unavailable (fewer than 12 qualifying periods by the deadline)"
    elif nz_total < MIN_TOTAL_NONZERO:
        res["verdict"] = "Unavailable (fewer than 2,000 nonzero signed_share pairs)"
    else:
        res.update(analyse(pairs, fit, n_boot))
    res["provenance"] = {
        "dev_fit_sha256": sha,
        "dev_fit_sha256_recorded_in_ledger": _ledger_has(sha, ledger_path),
        "code_sha256": forecast.sha256_file(CODE_PATH),
        "registration_commit": REGISTRATION_COMMIT,
        "deadline_utc": deadline.isoformat(),
        **provenance.git_state(),
    }
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(flow_screen.clean(res), indent=1, sort_keys=True))
    return res
