"""E003 short-horizon book imbalance / microprice test (H08/H09 cross-sectional variant).

Implements the binding pre-registration in ``docs/research_lab/EXPERIMENT_LEDGER.md`` (E003)
without altering it. Two subcommands in ``scripts/run_research_e003.py``: ``fit-s1`` freezes the
models on series S1 (development); ``score-s2`` applies them unchanged to series S2.

Interpretations the registration leaves open (recorded in the frozen fit and the results):

* M8 and M9 are OLS *through the origin* (consistent with R1); MC has an intercept.
* Gamma ``oneHourPriceChange`` is frequently absent; a missing ``chg_1h`` is set to 0.0 (the E001
  panel convention) and its share is reported. It does not exclude a row.
* A feature whose denominator (size sum) is not positive is NaN; such a row is excluded from every
  model and counted.
* Token two-sided in sweep A is the unit; mid = (best_bid + best_ask) / 2; targets use only the
  B (and C) mids, never A-side information beyond the A mid itself.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluate, forecast, panel

REGISTRATION_COMMIT = "0133fb9"
MIN_GAP_MIN = 60.0
SERIES_LEN = 3
SWEEP_ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "book_sweeps"
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
E003_DIR = forecast.ROOT / "data-dumps" / "research_lab" / "e003"
FEATURES = ["I1", "micro", "I5", "spread", "chg_1h"]
CHANGE_EPS = 1e-12
INTERPRETATIONS = {
    "M8_M9_intercept": "through-origin OLS (consistent with R1); MC has an intercept",
    "chg_1h_missing": "missing Gamma oneHourPriceChange set to 0.0 (E001 convention), counted",
    "zero_size_denominator": "feature NaN; row excluded from all models and counted",
}


# --- series selection -------------------------------------------------------------------------


def _ts(s: str):
    return forecast._parse_ts(s)


def list_series(root: Path = SWEEP_ROOT) -> list[dict]:
    """Complete 3-sweep series (indices 0,1,2, all complete, one snapshot), by start time."""
    by: dict[str, list[dict]] = {}
    for m in sorted(Path(root).glob("*/manifest.json")):
        man = json.loads(m.read_text())
        man["_dir"] = str(m.parent)
        by.setdefault(man.get("series_id", man["sweep_id"]), []).append(man)
    out = []
    for sid, ms in by.items():
        ms = sorted(ms, key=lambda m: m.get("series_index", 0))
        ok = (
            len(ms) == SERIES_LEN
            and [m.get("series_index") for m in ms] == list(range(SERIES_LEN))
            and all(m.get("state") == "complete" for m in ms)
            and all(m.get("series_length", SERIES_LEN) == SERIES_LEN for m in ms)
            and len({m.get("snapshot_id") for m in ms}) == 1
        )
        if ok:
            out.append({
                "series_id": sid, "sweeps": ms, "snapshot_id": ms[0]["snapshot_id"],
                "start": _ts(ms[0]["started_utc"]), "end": _ts(ms[-1]["finished_utc"]),
            })
    return sorted(out, key=lambda s: s["start"])


def select_series(series: list[dict], reg_time, min_gap_min: float = MIN_GAP_MIN):
    """(S1, S2): S1 first complete series started after registration; S2 first whose start is
    >= 60 min after S1's last sweep finished (None if not yet available)."""
    post = [s for s in series if s["start"] > reg_time]
    if not post:
        return None, None
    s1 = post[0]
    for s in post[1:]:
        if s["start"] - s1["end"] >= timedelta(minutes=min_gap_min):
            return s1, s
    return s1, None


# --- panel ------------------------------------------------------------------------------------


def _read_sweep(sweep: dict) -> pd.DataFrame:
    df = pd.read_csv(
        Path(sweep["_dir"]) / "rows.csv.gz", dtype={"token_id": str, "market_id": str}
    )
    df["_recv"] = panel._epoch(df["batch_receipt_utc"])
    return df.set_index("token_id")


def _ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """num/den, NaN where den is not strictly positive or any input is NaN."""
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)


def compute_features(a: pd.DataFrame) -> pd.DataFrame:
    """I1, micro, I5, spread from sweep-A two-sided rows (registered formulas)."""
    bid, ask = a["best_bid"].to_numpy(float), a["best_ask"].to_numpy(float)
    bs, as_ = a["bid_size_1"].to_numpy(float), a["ask_size_1"].to_numpy(float)
    db, da = a["depth_bid_5c"].to_numpy(float), a["depth_ask_5c"].to_numpy(float)
    mid = (bid + ask) / 2
    f = pd.DataFrame(index=a.index)
    f["I1"] = _ratio(bs - as_, bs + as_)
    f["micro"] = _ratio(ask * bs + bid * as_, bs + as_) - mid
    f["I5"] = _ratio(db - da, db + da)
    f["spread"] = ask - bid
    return f


def build_panel(series: dict, snapshot_root: Path = SNAPSHOT_ROOT) -> tuple[pd.DataFrame, dict]:
    """Token panel for one series plus counts (unavailable-by-reason, exclusions, fallbacks)."""
    sa, sb, sc = (_read_sweep(s) for s in series["sweeps"])
    a = sa[sa["state"] == "two_sided"]
    counts: dict = {
        "tokens_in_A": int(len(sa)),
        "A_state": {k: int(v) for k, v in sa["state"].value_counts().items()},
        "tokens_two_sided_A": int(len(a)),
    }
    snap = pd.read_csv(
        Path(snapshot_root) / series["snapshot_id"] / "rows.csv.gz",
        usecols=["market_id", "event_id", "chg_1h"], dtype={"market_id": str, "event_id": str},
    ).drop_duplicates("market_id").set_index("market_id")
    df = pd.DataFrame(index=a.index)
    df["market_id"] = a["market_id"]
    ev = df["market_id"].map(snap["event_id"])
    ev_missing = ev.isna() | (ev.astype(str).str.strip() == "")
    df["event_key"] = np.where(ev_missing, "m:" + df["market_id"], "e:" + ev.astype(str))
    chg = df["market_id"].map(snap["chg_1h"]).astype(float)
    df["chg_1h_missing"] = chg.isna().astype(float)
    df["chg_1h"] = chg.fillna(0.0)
    df["mid_A"] = (a["best_bid"] + a["best_ask"]) / 2
    for name, sx in (("B", sb), ("C", sc)):
        st = sx["state"].reindex(df.index)
        st = st.where(st.notna(), "missing_from_sweep")
        df[f"state_{name}"] = st
        two = (st == "two_sided").to_numpy()
        mid = ((sx["best_bid"] + sx["best_ask"]) / 2).reindex(df.index)
        df[f"mid_{name}"] = np.where(two, mid, np.nan)
        df[f"horizon_{name}_s"] = (sx["_recv"].reindex(df.index) - a["_recv"]).where(two)
        df[f"dmid_A{name}"] = df[f"mid_{name}"] - df["mid_A"]
        counts[f"target_unavailable_A{name}"] = {
            k: int(v) for k, v in st[~two].value_counts().items()
        }
    df = pd.concat([df, compute_features(a)], axis=1)
    df["feature_ok"] = df[FEATURES].notna().all(axis=1)
    counts["excluded_feature_nan"] = int((~df["feature_ok"]).sum())
    counts["excluded_feature_nan_by_feature"] = {
        c: int(df[c].isna().sum()) for c in FEATURES if df[c].isna().any()
    }
    counts["chg_1h_missing_share"] = float(df["chg_1h_missing"].mean()) if len(df) else None
    counts["event_id_fallback_to_market_id"] = int(ev_missing.sum())
    counts["n_events"] = int(df["event_key"].nunique())
    counts["horizon_AB_s_median"] = _med(df["horizon_B_s"])
    counts["horizon_AC_s_median"] = _med(df["horizon_C_s"])
    df = df.reset_index()
    return df, counts


def _med(s: pd.Series):
    s = s.dropna()
    return float(s.median()) if len(s) else None


def usable(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Rows with valid features and an available target (``AB`` or ``AC``)."""
    return df[df["feature_ok"] & df[f"dmid_{target}"].notna()].reset_index(drop=True)


# --- models -----------------------------------------------------------------------------------


def _origin_coef(x: np.ndarray, y: np.ndarray) -> float:
    """Through-origin OLS slope; a degenerate all-zero regressor gives 0.0 (no signal)."""
    c = evaluate.ols_origin_slope(x, y)
    return 0.0 if not np.isfinite(c) else c


def fit_models(d: pd.DataFrame) -> dict:
    """Fit R1, M8, M9 (through origin) and MC (intercept) on the AB target of ``d``."""
    y = d["dmid_AB"].to_numpy(float)
    x = np.column_stack([np.ones(len(d)), d[FEATURES].to_numpy(float)])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    return {
        "R1": {"chg_1h": _origin_coef(d["chg_1h"].to_numpy(float), y)},
        "M8": {"I1": _origin_coef(d["I1"].to_numpy(float), y)},
        "M9": {"micro": _origin_coef(d["micro"].to_numpy(float), y)},
        "MC": {"intercept": float(beta[0]),
               **{f: float(b) for f, b in zip(FEATURES, beta[1:], strict=True)}},
    }


def predict(fit: dict, d: pd.DataFrame) -> dict[str, np.ndarray]:
    """Frozen-coefficient predictions; R0 is zero."""
    out = {"R0": np.zeros(len(d))}
    for name, coefs in fit.items():
        p = np.full(len(d), coefs.get("intercept", 0.0))
        for f, b in coefs.items():
            if f != "intercept":
                p = p + b * d[f].to_numpy(float)
        out[name] = p
    return out


def _r2(sse: np.ndarray, base: np.ndarray) -> float:
    return evaluate.r2_oos(float(sse.sum()), float(base.sum()))


def describe_in_sample(d: pd.DataFrame, fit: dict) -> dict:
    y = d["dmid_AB"].to_numpy(float)
    p = predict(fit, d)
    sse = {k: (y - v) ** 2 for k, v in p.items()}
    return {
        "label": "DEVELOPMENT / IN-SAMPLE (S1) - not evidence",
        "n": int(len(d)),
        "r2_in_sample_vs_R0": {m: _r2(sse[m], sse["R0"]) for m in ("R1", "M8", "M9", "MC")},
        "r2_in_sample_MC_vs_R1": _r2(sse["MC"], sse["R1"]),
        "coef_signs": {
            m: {k: int(np.sign(v)) for k, v in c.items()} for m, c in fit.items()
        },
    }


def changed_share(d: pd.DataFrame, col: str) -> dict:
    v = d[col].dropna().to_numpy(float)
    return {"n": int(len(v)), "share_changed": float((np.abs(v) > CHANGE_EPS).mean())
            if len(v) else None}


# --- bootstrap and verdicts -------------------------------------------------------------------


def paired_diff_ci(
    cluster: np.ndarray, sse_a: np.ndarray, sse_b: np.ndarray, sse_0: np.ndarray,
    n: int = evaluate.BOOT_N, seed: int = evaluate.BOOT_SEED,
) -> tuple[float, float]:
    """Cluster-bootstrap 95% CI of R2(model b) - R2(model a) vs baseline 0, same resamples."""
    codes, uniq = pd.factorize(cluster)
    k = len(uniq)
    ca, cb, c0 = (np.bincount(codes, weights=w, minlength=k) for w in (sse_a, sse_b, sse_0))
    rng = np.random.default_rng(seed)
    vals = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, k, size=k)
        s0 = c0[idx].sum()
        vals[i] = (ca[idx].sum() - cb[idx].sum()) / s0 if s0 > 0 else np.nan
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def _sign(v: float) -> int:
    return 0 if v is None or not np.isfinite(v) else int(np.sign(v))


def verdict(r2: float, ci: tuple[float, float], s2_sign: int, s1_sign: int) -> str:
    """supported (exploratory) / wrong sign / inconclusive (registered rule)."""
    if s1_sign == 0 or s2_sign == 0:
        return "inconclusive"
    if s2_sign != s1_sign:
        return "wrong sign"
    if r2 > 0 and ci[0] > 0:
        return "supported (exploratory)"
    return "inconclusive"


def _tests(d: pd.DataFrame, fit: dict, target: str, with_ci: bool = True) -> dict:
    y = d[f"dmid_{target}"].to_numpy(float)
    p = predict(fit, d)
    sse = {k: (y - v) ** 2 for k, v in p.items()}
    cl = d["event_key"].to_numpy()
    out: dict = {"target": target, "n": int(len(d)), "n_events": int(d["event_key"].nunique())}

    def one(model: str, base: str, feat: str | None):
        r2 = _r2(sse[model], sse[base])
        ci = (evaluate.clustered_bootstrap_r2(cl, sse[model], sse[base])
              if with_ci and len(d) else (float("nan"),) * 2)
        res = {"r2_oos": r2, "ci": list(ci), "baseline": base}
        if feat is not None:
            slope = _origin_coef(d[feat].to_numpy(float), y)
            s1 = _sign(fit[model][feat])
            res.update(s2_slope=slope, s1_coef=fit[model][feat],
                       verdict=verdict(r2, ci, _sign(slope), s1))
        else:
            res["verdict"] = verdict(r2, ci, _sign(r2), 1)
        return res

    out["a_M8_vs_R0"] = one("M8", "R0", "I1")
    out["b_M9_vs_R0"] = one("M9", "R0", "micro")
    out["c_MC_vs_R1"] = one("MC", "R1", None)
    if with_ci and len(d):
        lo, hi = paired_diff_ci(cl, sse["M8"], sse["M9"], sse["R0"])
        diff = out["b_M9_vs_R0"]["r2_oos"] - out["a_M8_vs_R0"]["r2_oos"]
        out["H09_beyond_H08"] = {
            "r2_diff": diff, "ci": [lo, hi], "adds_beyond": bool(diff > 0 and lo > 0)}
    return out


def score_series(d_all: pd.DataFrame, fit: dict) -> dict:
    """Registered primary tests (AB), secondary AC tests, spread terciles, changed-mid share."""
    ab, ac = usable(d_all, "AB"), usable(d_all, "AC")
    res = {"primary_AB": _tests(ab, fit, "AB"), "secondary_AC": _tests(ac, fit, "AC"),
           "share_changed_AB": changed_share(ab, "dmid_AB"),
           "share_changed_AC": changed_share(ac, "dmid_AC")}
    terc: dict = {}
    if len(ab) >= 3:
        qs = ab["spread"].quantile([1 / 3, 2 / 3]).to_numpy()
        grp = np.digitize(ab["spread"].to_numpy(float), qs, right=True)
        for k, name in enumerate(("low", "mid", "high")):
            sub = ab[grp == k].reset_index(drop=True)
            if len(sub):
                t = _tests(sub, fit, "AB", with_ci=False)
                terc[name] = {
                    "n": t["n"], "spread_range": [float(sub["spread"].min()),
                                                  float(sub["spread"].max())],
                    "r2_M8": t["a_M8_vs_R0"]["r2_oos"], "r2_M9": t["b_M9_vs_R0"]["r2_oos"],
                    "r2_MC_vs_R1": t["c_MC_vs_R1"]["r2_oos"],
                    "share_changed": changed_share(sub, "dmid_AB")["share_changed"],
                }
    res["spread_terciles_AB_descriptive"] = terc
    return res


# --- commands ---------------------------------------------------------------------------------


def _git_head() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=forecast.ROOT,
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _code_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def _write_new(path: Path, obj: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:  # 'x' refuses to overwrite
        json.dump(_clean(obj), fh, indent=1, allow_nan=False)


def _select(sweep_root, reg_time):
    return select_series(list_series(sweep_root), reg_time)


def fit_s1(sweep_root: Path = SWEEP_ROOT, snapshot_root: Path = SNAPSHOT_ROOT,
           out_dir: Path = E003_DIR, reg_time=None) -> dict:
    out = Path(out_dir) / "s1_fit.json"
    if out.exists():
        raise FileExistsError(f"{out} exists; the S1 fit is frozen and never overwritten")
    reg_time = reg_time or forecast.registration_time(REGISTRATION_COMMIT)
    s1, _ = _select(sweep_root, reg_time)
    if s1 is None:
        raise RuntimeError("no complete S1 series after registration")
    df, counts = build_panel(s1, snapshot_root)
    d = usable(df, "AB")
    fit = fit_models(d)
    desc = describe_in_sample(d, fit)
    desc["share_changed_AB"] = changed_share(usable(df, "AB"), "dmid_AB")
    desc["share_changed_AC"] = changed_share(usable(df, "AC"), "dmid_AC")
    payload = {
        "experiment": "E003", "registration_commit": REGISTRATION_COMMIT,
        "series_id": s1["series_id"], "snapshot_id": s1["snapshot_id"],
        "sweep_ids": [m["sweep_id"] for m in s1["sweeps"]],
        "series_end_utc": s1["sweeps"][-1]["finished_utc"],
        "n_fit": int(len(d)), "fit": fit, "features": FEATURES,
        "interpretations": INTERPRETATIONS, "panel_counts": counts, "in_sample": desc,
        "code_commit": _git_head(), "code_sha256": _code_sha(),
        "fitted_utc": forecast._utc_now(),
    }
    _write_new(out, payload)
    return payload


def score_s2(sweep_root: Path = SWEEP_ROOT, snapshot_root: Path = SNAPSHOT_ROOT,
             out_dir: Path = E003_DIR, reg_time=None) -> dict:
    out = Path(out_dir) / "s2_results.json"
    if out.exists():
        raise FileExistsError(f"{out} exists; S2 results are never overwritten")
    fit_path = Path(out_dir) / "s1_fit.json"
    if not fit_path.exists():
        raise RuntimeError("s1_fit.json missing; run fit-s1 first")
    frozen = json.loads(fit_path.read_text())
    reg_time = reg_time or forecast.registration_time(REGISTRATION_COMMIT)
    s1, s2 = _select(sweep_root, reg_time)
    if s1 is None or s1["series_id"] != frozen["series_id"]:
        raise RuntimeError("S1 selected now differs from the series in the frozen fit")
    if s2 is None:
        raise RuntimeError("no qualifying S2 yet (complete series >= 60 min after S1 end)")
    df, counts = build_panel(s2, snapshot_root)
    res = score_series(df, frozen["fit"])  # frozen coefficients; nothing is refit
    payload = {
        "experiment": "E003", "registration_commit": REGISTRATION_COMMIT,
        "s1_fit_sha256": hashlib.sha256(fit_path.read_bytes()).hexdigest(),
        "s1_series_id": frozen["series_id"], "s2_series_id": s2["series_id"],
        "s2_snapshot_id": s2["snapshot_id"],
        "s2_sweep_ids": [m["sweep_id"] for m in s2["sweeps"]],
        "gap_min": (s2["start"] - s1["end"]).total_seconds() / 60.0,
        "bootstrap": {"n": evaluate.BOOT_N, "seed": evaluate.BOOT_SEED, "cluster": "event"},
        "interpretations": INTERPRETATIONS, "panel_counts": counts, **res,
        "code_commit": _git_head(), "code_sha256": _code_sha(),
        "scored_utc": forecast._utc_now(),
    }
    _write_new(out, payload)
    return payload
