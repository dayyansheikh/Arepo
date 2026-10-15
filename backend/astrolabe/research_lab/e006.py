"""E006: moderation of the 1h reversal by liquidity (H1) and time-to-end (H2).

Implements the E006 section of ``docs/research_lab/EXPERIMENT_LEDGER.md`` (registered at
``32e6907``) unchanged. Centring constants (m_L, m_H, m_S) and the frozen moderator
magnitudes (b_2, b_4) are fitted once on the development captures (``fit_dev``) and frozen in
``dev_fit.json``; ``score`` applies them to the E004-qualifying confirmation snapshots.

Conventions fixed here where the ledger is silent (all disclosed in the results file):
- Dev "pairs" for the centring means and b_k are E001-semantics pairs with an available target.
- m_L is a mean over pairs with observed ``chg_1h`` and observed liquidity; m_H over pairs with
  observed ``chg_1h`` and a known end date; m_S over pairs with observed ``chg_1h``.
- The guard regression (both hypotheses) also excludes ``end_unknown`` pairs, because the
  centred ``log_hours_to_end`` term is meaningless for them.
- The Holm-level CI of the guard uses the two-sided level 1 - alpha_k, where alpha_k is the Holm
  threshold of the hypothesis' rank (alpha/2 for the smaller p-value, alpha for the larger).
- p-values are the two-sided bootstrap p: 2*min((1+#{b<=0})/(B+1), (1+#{b>=0})/(B+1)).
- "E004 unavailable" means an E004 results file exists whose verdict starts with "Unavailable".
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import e004, e005, evaluate, forecast, panel

ROOT = forecast.ROOT
E006_DIR = ROOT / "data-dumps" / "research_lab" / "e006"
E005_DIR = e005.E005_DIR
DEV_DIR = e005.DEV_DIR
CODE_PATH = Path(__file__).resolve()
REGISTRATION_COMMIT = "32e6907"
LEDGER_REL = "docs/research_lab/EXPERIMENT_LEDGER.md"
FROZEN_REVERSAL = -0.331610
ALPHA = 0.05
MIN_PERIODS_SIGN = 7
MIN_PERIODS_OBSERVED = 9
MIN_N_EFF = 2000
MIN_K_EFF = 500
BOOT_N = evaluate.BOOT_N
BOOT_SEED = evaluate.BOOT_SEED
HYPS = {"H1": {"k": "z2", "moderator": "log_liq"}, "H2": {"k": "z4", "moderator": "hours"}}
ID_DTYPES = e005.ID_DTYPES


# ---------------------------------------------------------------- spec hash
def ledger_section(text: str) -> str:
    """The E006 section of the ledger, from its heading through the Non-claims bullet."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith("## E006")), None)
    if start is None:
        return ""
    out = []
    for ln in lines[start:]:
        out.append(ln.rstrip())
        if ln.startswith("- **Non-claims:**"):
            break
    return "\n".join(out)


def _sha_text(s: str) -> str:
    import hashlib

    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def ledger_section_hashes() -> dict:
    """sha256 of the E006 ledger section at the registration commit and in the working tree."""
    reg = forecast._git("show", f"{REGISTRATION_COMMIT}:{LEDGER_REL}")
    work_path = ROOT / LEDGER_REL
    work = work_path.read_text() if work_path.exists() else ""
    sec_r, sec_w = ledger_section(reg), ledger_section(work)
    return {
        "registered": _sha_text(sec_r) if sec_r else None,
        "working_tree": _sha_text(sec_w) if sec_w else None,
    }


# ---------------------------------------------------------------- panel
def build_pairs(snaps: list[pd.DataFrame], starts: list[str]) -> tuple[pd.DataFrame, list[dict]]:
    """Consecutive-capture pairs (E001 semantics) plus origin liquidity-missing and chg flags."""
    frames, counts = [], []
    for k in range(len(snaps) - 1):
        j_sched = panel._epoch(pd.Series([starts[k + 1]]))[0]
        pairs, cnt = panel.build_pair(snaps[k], snaps[k + 1], j_sched, k)
        oi = snaps[k].drop_duplicates("market_id").set_index("market_id")
        liq = pd.to_numeric(oi["liquidity"], errors="coerce").reindex(pairs["market_id"])
        pairs["liq_missing"] = liq.isna().to_numpy().astype(float)
        frames.append(pairs)
        counts.append(cnt)
    return pd.concat(frames, ignore_index=True), counts


def reversal_hat(pairs: pd.DataFrame, a: float, s: float, coef: float) -> np.ndarray:
    """Baseline R_hat = a + s*spread + coef*chg_1h (missing chg_1h already coded 0)."""
    return a + s * pairs["spread"].to_numpy(float) + coef * pairs["chg_1h"].to_numpy(float)


def add_moderators(pairs: pd.DataFrame, m_l: float, m_h: float, m_s: float) -> pd.DataFrame:
    """Add z2, z4, centred spread/hours and the inclusion flags. Missing chg_1h gives z = 0."""
    p = pairs.copy()
    chg = p["chg_1h"].to_numpy(float)
    p["obs"] = (p["chg_1h_missing"].to_numpy(float) == 0).astype(float)
    p["z2"] = chg * (p["log_liq"].to_numpy(float) - m_l)
    p["z4"] = chg * (p["log_hours_to_end"].to_numpy(float) - m_h)
    p["spread_c"] = p["spread"].to_numpy(float) - m_s
    p["hours_c"] = p["log_hours_to_end"].to_numpy(float) - m_h
    p["in_H1"] = p["liq_missing"].to_numpy(float) == 0
    p["in_H2"] = p["end_unknown"].to_numpy(float) == 0
    return p


def six_sig(x: float) -> float:
    return float(f"{x:.6g}")


# ---------------------------------------------------------------- regression
def ols(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Least squares through the origin; NaN vector if the design is singular or empty."""
    p = x.shape[1]
    if len(y) == 0:
        return np.full(p, np.nan)
    g = x.T @ x
    if np.linalg.matrix_rank(g) < p:
        return np.full(p, np.nan)
    return np.linalg.solve(g, x.T @ y)


def boot_coefs(
    cluster: np.ndarray, x: np.ndarray, y: np.ndarray, n: int = BOOT_N, seed: int = BOOT_SEED
) -> np.ndarray:
    """Cluster-bootstrap draws of the through-origin OLS coefficients, shape (n, p)."""
    codes, uniq = pd.factorize(cluster)
    k, p = len(uniq), x.shape[1]
    xtx = np.empty((k, p, p))
    xty = np.empty((k, p))
    for i in range(p):
        xty[:, i] = np.bincount(codes, weights=x[:, i] * y, minlength=k)
        for j in range(p):
            xtx[:, i, j] = np.bincount(codes, weights=x[:, i] * x[:, j], minlength=k)
    rng = np.random.default_rng(seed)
    out = np.full((n, p), np.nan)
    for b in range(n):
        idx = rng.integers(0, k, size=k)
        g, v = xtx[idx].sum(0), xty[idx].sum(0)
        if np.linalg.matrix_rank(g) == p:
            out[b] = np.linalg.solve(g, v)
    return out


def boot_p(draws: np.ndarray) -> float:
    """Two-sided bootstrap p-value for a coefficient being zero."""
    d = draws[np.isfinite(draws)]
    if len(d) == 0:
        return float("nan")
    lo = (1 + int((d <= 0).sum())) / (len(d) + 1)
    hi = (1 + int((d >= 0).sum())) / (len(d) + 1)
    return float(min(1.0, 2 * min(lo, hi)))


def boot_ci(draws: np.ndarray, alpha: float = ALPHA) -> list[float]:
    d = draws[np.isfinite(draws)]
    if len(d) == 0:
        return [float("nan"), float("nan")]
    lo, hi = np.percentile(d, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return [float(lo), float(hi)]


def holm(pvals: dict[str, float], alpha: float = ALPHA) -> dict[str, dict]:
    """Holm step-down. NaN p counts as 1. Returns rejected flag, adjusted level per key."""
    m = len(pvals)
    order = sorted(pvals, key=lambda h: (1.0 if not np.isfinite(pvals[h]) else pvals[h], h))
    out, stopped = {}, False
    for r, h in enumerate(order, start=1):
        thr = alpha / (m - r + 1)
        p = 1.0 if not np.isfinite(pvals[h]) else pvals[h]
        rej = (not stopped) and p < thr
        stopped = stopped or not rej
        out[h] = {"p": pvals[h], "threshold": thr, "rank": r, "rejected": bool(rej)}
    return out


# ---------------------------------------------------------------- development fit
def fit_dev_frame(
    pairs: pd.DataFrame, a: float, s: float, coef: float
) -> tuple[dict, pd.DataFrame]:
    """Centring constants, b_2, b_4 and counts from development pairs."""
    use = pairs[pairs["dmid"].notna()].reset_index(drop=True)
    obs = use["chg_1h_missing"].to_numpy(float) == 0
    ll, hh = use["log_liq"].to_numpy(float), use["log_hours_to_end"].to_numpy(float)
    liq_ok = use["liq_missing"].to_numpy(float) == 0
    end_ok = use["end_unknown"].to_numpy(float) == 0
    m_l = six_sig(float(ll[obs & liq_ok].mean()))
    m_h = six_sig(float(hh[obs & end_ok].mean()))
    m_s = six_sig(float(use["spread"].to_numpy(float)[obs].mean()))
    z = add_moderators(use, m_l, m_h, m_s)
    resid = use["dmid"].to_numpy(float) - reversal_hat(use, a, s, coef)
    chg = use["chg_1h"].to_numpy(float)
    info: dict = {"n_pairs_with_target": int(len(use)), "n_chg_1h_observed": int(obs.sum())}
    for h, (zc, flag) in {"H1": ("z2", liq_ok), "H2": ("z4", end_ok)}.items():
        zk = z[zc].to_numpy(float)
        b = evaluate.ols_origin_slope(zk[flag], resid[flag])
        both = flag & obs
        corr = float(np.corrcoef(chg[both], zk[both])[0, 1]) if both.sum() > 2 else None
        info[h] = {
            "z": zc,
            "b": float(b),
            "n_pairs_used": int(flag.sum()),
            "n_excluded": int((~flag).sum()),
            "n_chg_1h_observed_used": int(both.sum()),
            "corr_chg_1h_zk": corr,
        }
    ok = obs & liq_ok
    info["corr_log_liq_spread"] = float(
        np.corrcoef(ll[ok], use["spread"].to_numpy(float)[ok])[0, 1]
    )
    info["m_L"], info["m_H"], info["m_S"] = m_l, m_h, m_s
    return info, z


def _write_new(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x") as fh:
        json.dump(obj, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def fit_dev(
    dev_dir: Path = DEV_DIR,
    out_dir: Path = E006_DIR,
    e005_dir: Path = E005_DIR,
    reversal: float = FROZEN_REVERSAL,
) -> dict:
    """Fit and freeze m_L, m_H, m_S, b_2, b_4 on development captures; refuse overwrite."""
    out_path = Path(out_dir) / "dev_fit.json"
    if out_path.exists():
        raise FileExistsError(f"E006 dev fit already written (append-only): {out_path}")
    e5_path = Path(e005_dir) / "dev_fit.json"
    e5 = json.loads(e5_path.read_text())["baseline"]
    if abs(float(e5["coef"]) - reversal) > 1e-9:
        raise ValueError(f"E005 baseline reversal {e5['coef']} != frozen {reversal}")
    a, s = float(e5["a"]), float(e5["s"])
    snaps, starts, _ = e005._read_dev(dev_dir)
    pairs, counts = build_pairs(snaps, starts)
    info, _ = fit_dev_frame(pairs, a, s, reversal)
    fit = {
        "experiment": "E006",
        "label": "DEVELOPMENT (in-sample; not evidence)",
        "registration_commit": REGISTRATION_COMMIT,
        "m_L": info["m_L"],
        "m_H": info["m_H"],
        "m_S": info["m_S"],
        "b_2": info["H1"]["b"],
        "b_4": info["H2"]["b"],
        "baseline": {"a": a, "s": s, "coef": reversal},
        "counts": {
            k: info[k] for k in ("n_pairs_with_target", "n_chg_1h_observed", "H1", "H2")
        },
        "corr_log_liq_spread": info["corr_log_liq_spread"],
        "capture_counts": counts,
        "provenance": {
            "e005_dev_fit_sha256": forecast.sha256_file(e5_path),
            "dev_manifest_sha256": forecast.sha256_file(Path(dev_dir) / "manifest.json"),
            "dev_snapshots_sha256": forecast.sha256_file(Path(dev_dir) / "snapshots.csv.gz"),
            "ledger_section_sha256": ledger_section_hashes()["registered"],
            "code_sha256": forecast.sha256_file(CODE_PATH),
            "git_head": forecast._git("rev-parse", "HEAD") or "unknown",
        },
    }
    _write_new(out_path, fit)
    return fit


# ---------------------------------------------------------------- verdicts
def verdict(
    reason: str | None,
    rejected: bool,
    theta: float,
    b: float,
    consistent: bool,
    guard_ok: bool | None,
    s1_lo: float | None,
) -> str:
    """Registered per-hypothesis verdict. ``guard_ok`` is None for H1 (no guard requirement)."""
    if reason:
        return "Unavailable (no verdict)"
    sgn = float(np.sign(b))
    if sgn * theta > 0 and rejected and consistent and guard_ok is not False:
        if s1_lo is not None and s1_lo > 0:
            return "Supported and transferable"
        return "Supported (exploratory, prospective)"
    if not sgn * theta > 0:
        return "Not supported"
    return "Inconclusive"


def _design(av: pd.DataFrame, zc: str, guard: bool) -> np.ndarray:
    cols = [av["chg_1h"].to_numpy(float), av[zc].to_numpy(float)]
    if guard:
        cols += [av["chg_1h"].to_numpy(float) * av["spread_c"].to_numpy(float)]
        cols += [av["hours_c"].to_numpy(float)]
    return np.column_stack(cols)


def _period_signs(av: pd.DataFrame, y: np.ndarray, zc: str, b: float) -> dict:
    x = _design(av, zc, False)
    per, ok = [], 0
    for p in sorted(av["period"].unique()):
        m = av["period"].to_numpy() == p
        th = ols(x[m], y[m])[1] if m.sum() >= 3 else float("nan")
        good = bool(np.isfinite(th) and np.sign(b) * th > 0)
        ok += good
        per.append(
            {
                "period": int(p),
                "n": int(m.sum()),
                "n_chg_1h_observed": int(av["obs"].to_numpy()[m].sum()),
                "theta": float(th),
                "predicted_sign": good,
            }
        )
    return {"per_period": per, "n_periods": len(per), "n_predicted_sign": int(ok)}


def analyse_hyp(pairs: pd.DataFrame, h: str, b: float, fit: dict) -> tuple[dict, dict]:
    """One hypothesis on the confirmation pairs; returns (serialisable result, bootstrap draws)."""
    zc, flag = HYPS[h]["k"], f"in_{h}"
    a, s, coef = (float(fit["baseline"][k]) for k in ("a", "s", "coef"))
    elig = pairs[pairs["dmid"].notna()]
    av = elig[elig[flag]].reset_index(drop=True)
    cl, fb = e004.event_clusters(av) if len(av) else (np.array([]), 0)
    n_eff = int(av["obs"].sum())
    k_eff = int(len(set(cl[av["obs"].to_numpy() == 1].tolist()))) if len(av) else 0
    res: dict = {
        "z": zc,
        "b_frozen": b,
        "n_pairs_target_available": int(len(elig)),
        "n_excluded_by_missing_rule": int(len(elig) - len(av)),
        "n_eff": n_eff,
        "K_eff": k_eff,
        "event_clusters_all": int(len(set(cl.tolist()))),
        "cluster_fallback_to_market_id_rows": int(fb),
    }
    draws: dict = {"theta": np.array([]), "guard": np.array([])}
    if len(av) < 10 or n_eff == 0:
        return res, draws
    y = av["dmid"].to_numpy(float) - reversal_hat(av, a, s, coef)
    x = _design(av, zc, False)
    beta = ols(x, y)
    bs = boot_coefs(cl, x, y)
    draws["theta"] = bs[:, 1]
    res["gamma_residual"] = float(beta[0])  # chg_1h coefficient on dmid - R_hat
    res["gamma"] = float(coef + beta[0])  # implied total reversal coefficient at this horizon
    res["theta"] = float(beta[1])
    res["theta_ci95"] = boot_ci(bs[:, 1])
    res["p_two_sided"] = boot_p(bs[:, 1])
    res["n_boot_finite"] = int(np.isfinite(bs[:, 1]).sum())
    res["consistency"] = _period_signs(av, y, zc, b)
    zk = av[zc].to_numpy(float)
    sse_r, sse_m = y**2, (y - b * zk) ** 2
    res["S1_delta_r2"] = {
        "value": evaluate.r2_oos(float(sse_m.sum()), float(sse_r.sum())),
        "ci95": list(evaluate.clustered_bootstrap_r2(cl, sse_m, sse_r)),
    }
    ratio = bs[:, 1] / (coef + bs[:, 0])
    res["S2_theta_over_gamma"] = {
        "note": "gamma = frozen reversal + fitted chg_1h coefficient (total reversal)",
        "value": float(beta[1] / (coef + beta[0])) if coef + beta[0] != 0 else None,
        "ci95_percentile": boot_ci(ratio),
        "reference_frozen_b_over_reversal": float(b / coef),
    }
    g = av[av["end_unknown"].to_numpy(float) == 0].reset_index(drop=True)
    if len(g) >= 10:
        gcl, _ = e004.event_clusters(g)
        gy = g["dmid"].to_numpy(float) - reversal_hat(g, a, s, coef)
        gx = _design(g, zc, True)
        gb = ols(gx, gy)
        gdraws = boot_coefs(gcl, gx, gy)
        draws["guard"] = gdraws[:, 1]
        res["guard"] = {
            "regressors": ["chg_1h", zc, "chg_1h*(spread-m_S)", "log_hours_to_end-m_H"],
            "n": int(len(g)),
            "coefs": [float(v) for v in gb],
            "theta": float(gb[1]),
            "ci95": boot_ci(gdraws[:, 1]),
            "required_for_verdict": h == "H2",
        }
    return res, draws


def unavailable_reason(res: dict) -> str | None:
    if res["n_eff"] < MIN_N_EFF:
        return f"n_eff {res['n_eff']} < {MIN_N_EFF}"
    if res["K_eff"] < MIN_K_EFF:
        return f"K_eff {res['K_eff']} < {MIN_K_EFF}"
    return None


def finalise(
    results: dict[str, dict],
    draws: dict[str, dict],
    global_reason: str | None,
) -> dict[str, dict]:
    """Holm, guard CI at the Holm level and the per-hypothesis verdicts (mutates ``results``)."""
    pv = {h: results[h].get("p_two_sided", float("nan")) for h in results}
    hm = holm(pv)
    for h, r in results.items():
        r["holm"] = hm[h]
        b = r["b_frozen"]
        reason = global_reason or unavailable_reason(r)
        if "theta" not in r:
            reason = reason or "no estimable regression"
        guard_ok = None
        if h == "H2":
            gd = r.get("guard")
            if gd is not None:
                ci = boot_ci(draws[h]["guard"], hm[h]["threshold"])
                gd["ci_holm_level"] = ci
                gd["holm_level_alpha"] = hm[h]["threshold"]
                ok = np.sign(b) * gd["theta"] > 0 and (ci[0] > 0 if b > 0 else ci[1] < 0)
                gd["passes"] = bool(ok)
                guard_ok = bool(ok)
            else:
                guard_ok = False
        elif r.get("guard") is not None:
            r["guard"]["ci_holm_level"] = boot_ci(draws[h]["guard"], hm[h]["threshold"])
            r["guard"]["note"] = "disclosed secondary; not required for H1 verdict"
        cons = r.get("consistency", {"n_predicted_sign": 0})
        r["consistency_met"] = cons["n_predicted_sign"] >= MIN_PERIODS_SIGN
        s1 = r.get("S1_delta_r2", {}).get("ci95", [None])[0]
        r["verdict"] = verdict(
            reason,
            hm[h]["rejected"],
            r.get("theta", float("nan")),
            b,
            r["consistency_met"],
            guard_ok,
            s1,
        )
        r["unavailable_reason"] = reason
    return results


def target_unavailable_by_liquidity(pairs: pd.DataFrame) -> dict:
    """S3: target-unavailable rate by liquidity tercile (eligible pairs with observed liquidity)."""
    d = pairs[pairs["liq_missing"].to_numpy(float) == 0]
    out: dict = {"n_missing_liquidity_pairs": int(len(pairs) - len(d)), "terciles": {}}
    if len(d) < 3:
        return out
    v = d["log_liq"].to_numpy(float)
    grp = np.digitize(v, np.quantile(v, [1 / 3, 2 / 3]), right=True)
    for i, name in enumerate(("low", "mid", "high")):
        m = grp == i
        un = int(d["dmid"].isna().to_numpy()[m].sum())
        out["terciles"][name] = {
            "log_liq_range": [float(v[m].min()), float(v[m].max())] if m.any() else None,
            "n": int(m.sum()),
            "target_unavailable": un,
            "rate": float(un / m.sum()) if m.any() else None,
        }
    return out


def analyse(
    pairs: pd.DataFrame,
    counts: list[dict],
    fit: dict,
    spec_ok: bool,
    e004_unavailable: bool,
) -> dict:
    p = add_moderators(pairs, fit["m_L"], fit["m_H"], fit["m_S"])
    usable = p[p["dmid"].notna()]
    obs_periods = int(usable.loc[usable["obs"] == 1, "period"].nunique())
    reason = None
    if e004_unavailable:
        reason = "E004 unavailable"
    elif obs_periods < MIN_PERIODS_OBSERVED:
        reason = f"only {obs_periods} periods with observed chg_1h (< {MIN_PERIODS_OBSERVED})"
    elif not spec_ok:
        reason = "frozen spec hash differs from the registration commit"
    results, draws = {}, {}
    for h, bk in (("H1", fit["b_2"]), ("H2", fit["b_4"])):
        results[h], draws[h] = analyse_hyp(p, h, float(bk), fit)
    finalise(results, draws, reason)
    return {
        "experiment": "E006",
        "frozen": {k: fit[k] for k in ("m_L", "m_H", "m_S", "b_2", "b_4", "baseline")},
        "counts": {
            "periods": counts,
            "pairs_eligible": int(len(p)),
            "pairs_target_available": int(len(usable)),
            "pairs_chg_1h_observed": int(usable["obs"].sum()),
            "periods_with_observed_chg_1h": obs_periods,
            "missing_liquidity_pairs": int((usable["liq_missing"] == 1).sum()),
            "end_unknown_pairs": int((usable["end_unknown"] == 1).sum()),
        },
        "global_unavailable_reason": reason,
        "hypotheses": results,
        "S3_target_unavailable_by_liquidity": target_unavailable_by_liquidity(p),
        "disclosures": [
            "Exploratory moderation test; dev effects are winner's-curse inflated.",
            "Data are shared with E004/E005; results are correlated with them.",
            "11 consecutive ~2h periods span 1-2 independent time blocks; the bootstrap does "
            "not capture day-wide shocks. Period consistency is a check, not a test.",
            "Non-claims: no edge, profitability, calibration or causal claim.",
        ],
    }


def status(
    snapshot_root: Path = forecast.SNAPSHOT_ROOT,
    out_dir: Path = E006_DIR,
    reg_time: datetime | None = None,
) -> dict:
    st = e004.status(snapshot_root, reg_time)
    st["experiment"] = "E006"
    st["dev_fit_exists"] = (Path(out_dir) / "dev_fit.json").exists()
    st["results_exist"] = (Path(out_dir) / "results.json").exists()
    st["state"] = "Pending" if not st["ready"] else "ready to score"
    return st


def _e004_unavailable(e004_dir: Path) -> bool:
    path = Path(e004_dir) / "results.json"
    if not path.exists():
        return False
    v = json.loads(path.read_text()).get("primary", {}).get("verdict", "")
    return str(v).startswith("Unavailable")


def score(
    snapshot_root: Path = forecast.SNAPSHOT_ROOT,
    out_dir: Path = E006_DIR,
    reg_time: datetime | None = None,
    e004_dir: Path = e004.E004_DIR,
) -> dict | None:
    """Score once 12 qualifying snapshots exist; requires dev_fit.json; refuse overwrite."""
    reg_time = reg_time or forecast.registration_time(e004.REGISTRATION_COMMIT)
    caps = e004.qualifying_captures(forecast.list_complete_captures(snapshot_root), reg_time)
    if len(caps) < e004.N_SNAPSHOTS:
        return None
    fit_path, out_path = Path(out_dir) / "dev_fit.json", Path(out_dir) / "results.json"
    if not fit_path.exists():
        raise FileNotFoundError(f"E006 requires the frozen dev fit first: {fit_path}")
    if out_path.exists():
        raise FileExistsError(f"E006 results already written (append-only): {out_path}")
    fit = json.loads(fit_path.read_text())
    hashes = ledger_section_hashes()
    frozen = fit["provenance"]["ledger_section_sha256"]
    spec_ok = frozen is not None and all(
        hashes[k] == frozen for k in ("registered", "working_tree")
    )
    snaps = [forecast.load_snapshot(Path(c["dir"]))[0] for c in caps]
    pairs, counts = build_pairs(snaps, [c["started_utc"] for c in caps])
    res = analyse(pairs, counts, fit, spec_ok, _e004_unavailable(e004_dir))
    res["provenance"] = {
        "dev_fit_sha256": forecast.sha256_file(fit_path),
        "ledger_section_sha256": {"frozen": frozen, **hashes},
        "code_sha256": forecast.sha256_file(CODE_PATH),
        "git_head": forecast._git("rev-parse", "HEAD") or "unknown",
        "registration_commit": REGISTRATION_COMMIT,
        "registration_time_utc": reg_time.isoformat(),
        "snapshots": [
            {
                "capture_id": c["capture_id"],
                "started_utc": c["started_utc"],
                "manifest_sha256": forecast.sha256_file(Path(c["dir"]) / "manifest.json"),
            }
            for c in caps
        ],
    }
    _write_new(out_path, res)
    return res
