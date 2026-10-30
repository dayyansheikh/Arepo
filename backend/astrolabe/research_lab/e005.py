"""E005: cross-market consistency in neg-risk groups (arbitrage-band deviation).

Applies the E005 pre-registration in ``docs/research_lab/EXPERIMENT_LEDGER.md`` unchanged.
Groups and ``dev`` are built from ORIGIN rows only. ``b`` is fitted once on the development
captures (``fit_dev``), frozen in ``dev_fit.json`` and applied to the E004 confirmation snapshots
(``score``). The unit is E001-eligible members of valid groups; non-group markets are not in it.
Amendment v2: baseline R = a + s*spread - coef*chg_1h (a, s fitted on dev, frozen), clusters
event_id -> neg_risk_market_id -> market_id (counted), plus tight-group and dev-sign secondaries.
Missing ``event_neg_risk_augmented`` counts as ``!= 0`` (group excluded: cannot be verified);
missing ``neg_risk_other`` is not ``== 1``; missing ``received_utc`` excludes the group.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import e004, evaluate, forecast, panel

ROOT = forecast.ROOT
E005_DIR = ROOT / "data-dumps" / "research_lab" / "e005"
DEV_DIR = ROOT / "data-dumps" / "research_lab" / "dev_snapshots_v2"
CODE_PATH = Path(__file__).resolve()
MAX_SPAN_S = 120.0
MIN_DEV_PAIRS = 200
MIN_DEV_GROUPS = 30
MIN_POSITIVE_PERIODS = 8
N_PERIODS = 11
ID_DTYPES = {**forecast.ID_DTYPES, "neg_risk_market_id": str}


def group_members(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Valid neg-risk groups and band features from one capture's ORIGIN rows.

    Returns (members indexed by market_id with group/dev columns, group table, exclusion counts).
    """
    r = rows.drop_duplicates("market_id")
    nr = pd.to_numeric(r["neg_risk"], errors="coerce")
    r = r[(nr == 1) & r["neg_risk_market_id"].notna()].copy()
    r["gid"] = r["neg_risk_market_id"].astype(str)
    raw_bid = pd.to_numeric(r["best_bid"], errors="coerce")
    r["bid"] = raw_bid.fillna(0.0)  # no buyer -> 0
    r["ask"] = pd.to_numeric(r["best_ask"], errors="coerce")
    r["row_spread"] = (pd.to_numeric(r["best_ask"], errors="coerce") - raw_bid).to_numpy()
    r["t"] = panel._epoch(r["received_utc"])
    aug = pd.to_numeric(r["event_neg_risk_augmented"], errors="coerce")
    oth = pd.to_numeric(r["neg_risk_other"], errors="coerce")
    r["f_aug"] = (aug.isna() | (aug != 0)).to_numpy()
    r["f_oth"] = (oth == 1).to_numpy()
    r["f_noask"] = r["ask"].isna().to_numpy()
    g = r.groupby("gid")
    tab = pd.DataFrame(
        {
            "n": g["market_id"].size(),
            "aug": g["f_aug"].any(),
            "other": g["f_oth"].any(),
            "noask": g["f_noask"].any(),
            "span": g["t"].max() - g["t"].min(),
            "t_nan": g["t"].apply(lambda s: bool(s.isna().any())),
        }
    )
    tab["few"] = tab["n"] < 2
    tab["span_bad"] = tab["t_nan"] | (tab["span"] > MAX_SPAN_S)
    tab["valid"] = ~(tab[["aug", "other", "noask", "few", "span_bad"]].any(axis=1))
    excl = {
        "groups_total": int(len(tab)),
        "groups_valid": int(tab["valid"].sum()),
        **{
            f"excluded_{k}": int(tab[k].sum())
            for k in ("aug", "other", "few", "noask", "span_bad")
        },
    }
    m = r[r["gid"].isin(tab.index[tab["valid"]])].copy()
    s_ask = m.groupby("gid")["ask"].transform("sum")
    s_bid = m.groupby("gid")["bid"].transform("sum")
    m["sb"] = 1.0 - (s_ask - m["ask"])
    m["sa"] = 1.0 - (s_bid - m["bid"])
    mid = (m["bid"] + m["ask"]) / 2
    m["dev"] = np.maximum(0.0, m["sb"] - mid) - np.maximum(0.0, mid - m["sa"])
    m["width"] = m["sa"] - m["sb"]
    m["max_spread"] = m.groupby("gid")["row_spread"].transform("max")  # present spreads only
    m["A_g"], m["B_g"] = s_ask, s_bid
    m["N_g"] = m.groupby("gid")["ask"].transform("size")
    gt = m.groupby("gid").agg(N_g=("ask", "size"), A_g=("ask", "sum"), B_g=("bid", "sum"))
    gt["arb_ask_lt_1"], gt["arb_bid_gt_1"] = gt["A_g"] < 1, gt["B_g"] > 1
    cols = ["gid", "dev", "width", "N_g", "max_spread", "A_g", "B_g", "sb", "sa"]
    return m.set_index("market_id")[cols], gt, excl


def build_pairs(snaps: list[pd.DataFrame], starts: list[str]) -> tuple[pd.DataFrame, list[dict]]:
    """Consecutive-capture pairs (E001 semantics): in-group eligible members, dev, touches."""
    frames, counts = [], []
    for k in range(len(snaps) - 1):
        si, sj = snaps[k], snaps[k + 1]
        j_sched = panel._epoch(pd.Series([starts[k + 1]]))[0]
        pairs, cnt = panel.build_pair(si, sj, j_sched, k)
        mem, gt, excl = group_members(si)
        oi = si.drop_duplicates("market_id").set_index("market_id")
        oj = sj.drop_duplicates("market_id").set_index("market_id")
        mk = pairs["market_id"]
        for col, src, side in (("bid_i", oi, "best_bid"), ("ask_i", oi, "best_ask"),
                               ("bid_j", oj, "best_bid"), ("ask_j", oj, "best_ask")):
            pairs[col] = src[side].reindex(mk).to_numpy(float)
        for col in ("gid", "dev", "width", "N_g", "max_spread"):
            pairs[col] = mem[col].reindex(mk).to_numpy()
        pairs["in_group"] = pairs["gid"].notna().to_numpy()
        cnt.update(excl)
        cnt["pairs_eligible_total"] = int(len(pairs))
        cnt["pairs_in_group"] = int(pairs["in_group"].sum())
        cnt["groups_with_arb_ask_lt_1"] = int(gt["arb_ask_lt_1"].sum())
        cnt["groups_with_arb_bid_gt_1"] = int(gt["arb_bid_gt_1"].sum())
        cnt["N_g_quartiles"] = [float(x) for x in gt["N_g"].quantile([0.25, 0.5, 0.75])] \
            if len(gt) else None
        frames.append(pairs[pairs["in_group"]])
        counts.append(cnt)
    return pd.concat(frames, ignore_index=True), counts


def base_hat(pairs: pd.DataFrame, spec: dict, a: float, sl: float) -> np.ndarray:
    """Baseline R = a + s*spread - 0.33161*chg_1h (reversal coefficient frozen; a, s from dev)."""
    return a + sl * pairs["spread"].to_numpy(float) + dev_hat(pairs, spec)


def dev_hat(pairs: pd.DataFrame, spec: dict) -> np.ndarray:
    """Frozen reversal term coef * feature (origin-only)."""
    return float(spec["coef"]) * pairs[spec["feature"]].to_numpy(float)


def fit_baseline(pairs: pd.DataFrame, spec: dict) -> tuple[float, float]:
    """OLS with intercept of (dmid - reversal term) on spread (dev only)."""
    av = pairs[pairs["dmid"].notna()]
    z = av["dmid"].to_numpy(float) - dev_hat(av, spec)
    x = np.column_stack([np.ones(len(av)), av["spread"].to_numpy(float)])
    beta, *_ = np.linalg.lstsq(x, z, rcond=None)
    return float(beta[0]), float(beta[1])


def _drift_design(pairs: pd.DataFrame) -> np.ndarray:
    return np.column_stack(
        [np.ones(len(pairs)), pairs["spread"].to_numpy(float), pairs["mid"].to_numpy(float)]
    )


def fit_drift(pairs: pd.DataFrame) -> list[float]:
    """OLS with intercept of dmid on spread and mid (secondary baseline, fitted on dev only)."""
    av = pairs[pairs["dmid"].notna()]
    beta, *_ = np.linalg.lstsq(_drift_design(av), av["dmid"].to_numpy(float), rcond=None)
    return [float(x) for x in beta]


def n_groups_nonzero(av: pd.DataFrame) -> int:
    nz = av[av["dev"].to_numpy(float) != 0]
    return int(nz["gid"].nunique())


def fit_b(pairs: pd.DataFrame, spec: dict, a: float, sl: float) -> tuple[float, dict]:
    """b = OLS through origin of (dmid - R_hat) on dev, over in-group pairs with a target."""
    av = pairs[pairs["dmid"].notna()].reset_index(drop=True)
    resid = av["dmid"].to_numpy(float) - base_hat(av, spec, a, sl)
    dev = av["dev"].to_numpy(float)
    b = evaluate.ols_origin_slope(dev, resid)
    nz = dev != 0
    per = [
        {"period": int(p), "pairs": int(len(g)), "pairs_dev_nonzero": int((g["dev"] != 0).sum())}
        for p, g in av.groupby("period")
    ]
    sse_r, sse_rc = float((resid**2).sum()), float(((resid - b * dev) ** 2).sum())
    desc = {
        "label": "DEVELOPMENT (in-sample; not evidence)",
        "n_pairs_in_group_with_target": int(len(av)),
        "share_dev_nonzero": float(nz.mean()) if len(av) else None,
        "share_dev_positive": float((dev > 0).mean()) if len(av) else None,
        "share_dev_negative": float((dev < 0).mean()) if len(av) else None,
        "abs_dev_quantiles_nonzero": [
            float(x) for x in np.quantile(np.abs(dev[nz]), [0.1, 0.5, 0.9, 0.99])
        ]
        if nz.any()
        else None,
        "in_sample_incremental_r2": evaluate.r2_oos(sse_rc, sse_r),
        "r2_R_vs_b0": evaluate.r2_oos(sse_r, float((av["dmid"].to_numpy(float) ** 2).sum())),
        "n_groups_all": int(av["gid"].nunique()),
        "N_g_quartiles": [float(x) for x in av["N_g"].quantile([0.25, 0.5, 0.75])]
        if len(av)
        else None,
    }
    info = {
        "n_pairs": int(len(av)),
        "n_pairs_dev_nonzero": int(nz.sum()),
        "n_groups_dev_nonzero": n_groups_nonzero(av),
        "per_period": per,
    }
    return b, {**info, "descriptives": desc}


def _read_dev(dev_dir: Path) -> tuple[list[pd.DataFrame], list[str], dict]:
    man = json.loads((Path(dev_dir) / "manifest.json").read_text())
    allrows = pd.read_csv(Path(dev_dir) / "snapshots.csv.gz", dtype=ID_DTYPES)
    caps = sorted(man["captures"], key=lambda c: c["start_utc"])
    by = {cid: g.reset_index(drop=True) for cid, g in allrows.groupby("capture_id")}
    return [by[c["capture_id"]] for c in caps], [c["start_utc"] for c in caps], man


def _write_new(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x") as fh:
        json.dump(obj, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def fit_dev(
    dev_dir: Path = DEV_DIR, out_dir: Path = E005_DIR, spec: dict | None = None
) -> dict:
    """Fit and freeze b (and the drift baseline) on the development captures; refuse overwrite."""
    spec = spec or forecast.load_spec()
    out_path = Path(out_dir) / "dev_fit.json"
    if out_path.exists():
        raise FileExistsError(f"E005 dev fit already written (append-only): {out_path}")
    snaps, starts, _ = _read_dev(dev_dir)
    pairs, counts = build_pairs(snaps, starts)
    a, sl = fit_baseline(pairs, spec)
    b, info = fit_b(pairs, spec, a, sl)
    if not np.isfinite(b):
        raise ValueError("dev is zero everywhere; b is undefined")
    fit = {
        "experiment": "E005",
        "b": b,
        "baseline": {
            "form": "R = a + s*spread - coef*chg_1h; (a,s) OLS w/ intercept on dev, target "
            "dmid - coef*chg_1h",
            "a": a,
            "s": sl,
            "coef": float(spec["coef"]),
        },
        **{k: info[k] for k in ("n_pairs", "n_pairs_dev_nonzero", "n_groups_dev_nonzero")},
        "per_period": info["per_period"],
        "drift_baseline": {
            "form": "descriptive secondary: dmid = c0 + c1*spread + c2*mid (OLS, intercept; dev)",
            "coef": fit_drift(pairs),
        },
        "descriptives": info["descriptives"],
        "capture_counts": counts,
        "provenance": {
            "model_id": spec["model_id"],
            "spec_sha256": spec["_sha256"],
            "dev_manifest_sha256": forecast.sha256_file(Path(dev_dir) / "manifest.json"),
            "dev_snapshots_sha256": forecast.sha256_file(Path(dev_dir) / "snapshots.csv.gz"),
            "code_sha256": forecast.sha256_file(CODE_PATH),
            "git_head": forecast._git("rev-parse", "HEAD") or "unknown",
        },
    }
    _write_new(out_path, fit)
    return fit


def verdict(
    n_pairs_nz: int,
    n_groups_nz: int,
    r2: float,
    r2_ci: tuple[float, float],
    n_pos: int,
    slope: float,
    slope_ci: tuple[float, float],
) -> str:
    """Registered E005 verdict."""
    if n_pairs_nz < MIN_DEV_PAIRS or n_groups_nz < MIN_DEV_GROUPS:
        return "Unavailable (no verdict)"
    if r2 > 0 and r2_ci[0] > 0 and slope > 0 and slope_ci[0] > 0 and n_pos >= MIN_POSITIVE_PERIODS:
        return "Supported (exploratory)"
    if not r2 > 0 or not slope > 0:
        return "Not supported"
    return "Inconclusive"


def _incr(y: np.ndarray, r: np.ndarray, rc: np.ndarray) -> float:
    return evaluate.r2_oos(float(((y - rc) ** 2).sum()), float(((y - r) ** 2).sum()))


def _block(av: pd.DataFrame, m: np.ndarray, y, r, rc, cl) -> dict:
    dev, res = av["dev"].to_numpy(float)[m], (y - r)[m]
    nz = int((dev != 0).sum())
    return {
        "n": int(m.sum()),
        "n_dev_nonzero": nz,
        "incremental_r2": _incr(y[m], r[m], rc[m]) if m.any() else None,
        "slope": evaluate.ols_origin_slope(dev, res) if nz else None,
        "slope_ci": list(evaluate.clustered_bootstrap_slope(cl[m], dev, res)) if nz else None,
    }


def cluster_keys(av: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """event_id -> neg_risk_market_id -> market_id fallbacks; each level counted."""
    ev = av["event_id"].astype(str).str.strip()
    no_ev = (av["event_id"].isna() | ev.isin(["", "nan", "None"])).to_numpy()
    gid = av["gid"].astype(str)
    no_g = (av["gid"].isna() | gid.isin(["", "nan", "None"])).to_numpy()
    key = np.where(
        ~no_ev,
        "e:" + ev,
        np.where(~no_g, "g:" + gid, "m:" + av["market_id"].astype(str)),
    )
    return key, {
        "cluster_fallback_to_neg_risk_market_id_rows": int((no_ev & ~no_g).sum()),
        "cluster_fallback_to_market_id_rows": int((no_ev & no_g).sum()),
    }


def _tercile_blocks(av: pd.DataFrame, col: str, y, r, rc, cl) -> dict:
    v = av[col].to_numpy(float)
    qs = np.quantile(v, [1 / 3, 2 / 3])
    grp = np.digitize(v, qs, right=True)
    out = {}
    for k, name in enumerate(("low", "mid", "high")):
        m = grp == k
        if not m.any():
            continue
        dev, res = av["dev"].to_numpy(float)[m], (y - r)[m]
        nz = int((dev != 0).sum())
        out[name] = {
            "range": [float(v[m].min()), float(v[m].max())],
            "n": int(m.sum()),
            "n_dev_nonzero": nz,
            "incremental_r2": _incr(y[m], r[m], rc[m]),
            "slope": evaluate.ols_origin_slope(dev, res) if nz else None,
            "slope_ci": list(evaluate.clustered_bootstrap_slope(cl[m], dev, res)) if nz else None,
        }
    return out


def analyse(pairs: pd.DataFrame, counts: list[dict], fit: dict, spec: dict) -> dict:
    b = float(fit["b"])
    pairs = pairs.copy()
    pairs["R"] = base_hat(pairs, spec, float(fit["baseline"]["a"]), float(fit["baseline"]["s"]))
    pairs["dmid_hat"] = pairs["R"] + b * pairs["dev"].to_numpy(float)
    av = pairs[pairs["dmid"].notna()].reset_index(drop=True)
    cl, fallback = cluster_keys(av)
    y, r = av["dmid"].to_numpy(float), av["R"].to_numpy(float)
    dev = av["dev"].to_numpy(float)
    rc = av["dmid_hat"].to_numpy(float)
    sse_rc, sse_r = (y - rc) ** 2, (y - r) ** 2
    r2 = evaluate.r2_oos(float(sse_rc.sum()), float(sse_r.sum()))
    r2_ci = evaluate.clustered_bootstrap_r2(cl, sse_rc, sse_r)
    resid = y - r
    slope = evaluate.ols_origin_slope(dev, resid)
    slope_ci = evaluate.clustered_bootstrap_slope(cl, dev, resid)
    per_period = []
    for p in sorted(av["period"].unique()):
        m = av["period"].to_numpy() == p
        per_period.append(
            {
                "period": int(p),
                "n": int(m.sum()),
                "n_dev_nonzero": int((dev[m] != 0).sum()),
                "incremental_r2": _incr(y[m], r[m], rc[m]),
            }
        )
    n_pos = sum(1 for d in per_period if d["incremental_r2"] > 0)
    nz = dev != 0
    n_nz, n_gnz = int(nz.sum()), n_groups_nonzero(av)
    g_hat = b * dev
    sse_g, sse_0 = (y - g_hat) ** 2, y**2
    drift = _drift_design(av) @ np.asarray(fit["drift_baseline"]["coef"])
    sse_d = (y - drift) ** 2
    tr = e004.trade_pnl(
        rc,
        av["bid_i"].to_numpy(float),
        av["ask_i"].to_numpy(float),
        av["bid_j"].to_numpy(float),
        av["ask_j"].to_numpy(float),
        av["spread"].to_numpy(float),
    )
    sel = tr["selected"].to_numpy()
    return {
        "experiment": "E005",
        "b_frozen": b,
        "counts": {
            "periods": counts,
            "pairs_in_group": int(len(pairs)),
            "pairs_target_available": int(len(av)),
            "pairs_target_unavailable_excluded": int(len(pairs) - len(av)),
            "pairs_dev_nonzero": n_nz,
            "groups_dev_nonzero": n_gnz,
            "event_clusters": int(len(set(cl.tolist()))),
            **fallback,
        },
        "primary": {
            "incremental_r2_pooled": r2,
            "incremental_r2_ci": list(r2_ci),
            "slope_resid_on_dev": slope,
            "slope_ci": list(slope_ci),
            "per_period": per_period,
            "n_periods_positive": n_pos,
            "n_periods": len(per_period),
            "verdict": verdict(n_nz, n_gnz, r2, r2_ci, n_pos, slope, slope_ci),
        },
        "secondary": {
            "label": "descriptive",
            "g_only_vs_b0": {
                "r2": evaluate.r2_oos(float(sse_g.sum()), float(sse_0.sum())),
                "ci": list(evaluate.clustered_bootstrap_r2(cl, sse_g, sse_0)),
            },
            "r_vs_b0": evaluate.r2_oos(float(sse_r.sum()), float(sse_0.sum())),
            "rc_vs_b0": evaluate.r2_oos(float(sse_rc.sum()), float(sse_0.sum())),
            "drift_baseline_vs_b0": evaluate.r2_oos(float(sse_d.sum()), float(sse_0.sum())),
            "rc_vs_drift_baseline": evaluate.r2_oos(float(sse_rc.sum()), float(sse_d.sum())),
            "terciles_N_g": _tercile_blocks(av, "N_g", y, r, rc, cl),
            "terciles_band_width": _tercile_blocks(av, "width", y, r, rc, cl),
            "tight_groups_max_spread_le_0.03": _block(
                av, av["max_spread"].to_numpy(float) <= 0.03, y, r, rc, cl
            ),
            "dev_positive_only": _block(av, dev > 0, y, r, rc, cl),
            "dev_negative_only": _block(av, dev < 0, y, r, rc, cl),
        },
        "execution": {
            "rule": "|R + b*dev| > spread_i/2; 1 share; fees, depth, latency ignored",
            "touch_to_touch": e004._exec_block(cl[sel], tr["pnl_touch"].to_numpy()[sel]),
            "optimistic_mid_exit": e004._exec_block(cl[sel], tr["pnl_mid"].to_numpy()[sel]),
            "lost_to_target_unavailability": e004.lost_selected(pairs),
        },
        "disclosures": [
            "Group completeness cannot be verified (unlisted, inactive or placeholder siblings).",
            "Fees and depth are absent.",
            "Data are shared with E004; results are correlated with it, not independent.",
        ],
    }


def status(
    snapshot_root: Path = forecast.SNAPSHOT_ROOT,
    out_dir: Path = E005_DIR,
    reg_time: datetime | None = None,
) -> dict:
    st = e004.status(snapshot_root, reg_time)
    st["experiment"] = "E005"
    st["dev_fit_exists"] = (Path(out_dir) / "dev_fit.json").exists()
    st["results_exist"] = (Path(out_dir) / "results.json").exists()
    return st


def score(
    snapshot_root: Path = forecast.SNAPSHOT_ROOT,
    out_dir: Path = E005_DIR,
    reg_time: datetime | None = None,
    spec: dict | None = None,
) -> dict | None:
    """Score once 12 qualifying snapshots exist; requires dev_fit.json; refuse overwrite."""
    spec = spec or forecast.load_spec()
    reg_time = reg_time or forecast.registration_time(e004.REGISTRATION_COMMIT)
    caps = e004.qualifying_captures(forecast.list_complete_captures(snapshot_root), reg_time)
    if len(caps) < e004.N_SNAPSHOTS:
        return None
    fit_path, out_path = Path(out_dir) / "dev_fit.json", Path(out_dir) / "results.json"
    if not fit_path.exists():
        raise FileNotFoundError(f"E005 requires the frozen dev fit first: {fit_path}")
    if out_path.exists():
        raise FileExistsError(f"E005 results already written (append-only): {out_path}")
    fit = json.loads(fit_path.read_text())
    if fit["provenance"]["spec_sha256"] != spec["_sha256"]:
        raise ValueError("model spec differs from the one b was fitted against")
    snaps = [forecast.load_snapshot(Path(c["dir"]))[0] for c in caps]
    pairs, counts = build_pairs(snaps, [c["started_utc"] for c in caps])
    res = analyse(pairs, counts, fit, spec)
    res["provenance"] = {
        "model_id": spec["model_id"],
        "spec_sha256": spec["_sha256"],
        "dev_fit_sha256": forecast.sha256_file(fit_path),
        "code_sha256": forecast.sha256_file(CODE_PATH),
        "git_head": forecast._git("rev-parse", "HEAD") or "unknown",
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

