"""E004: multi-period prospective test of the frozen reversal model plus an execution check.

Applies the E004 pre-registration in ``docs/research_lab/EXPERIMENT_LEDGER.md`` unchanged.
Panel semantics are E001's (``panel.build_pair``); clustering is by EVENT (market_id fallback,
counted). Nothing is refitted: ``dmid_hat = coef * chg_1h`` from the frozen E002 spec.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluate, forecast, panel

ROOT = forecast.ROOT
E004_DIR = ROOT / "data-dumps" / "research_lab" / "e004"
REGISTRATION_COMMIT = "3d7335e"
N_SNAPSHOTS = 12
MIN_POSITIVE_PERIODS = 8
BOOT_N = evaluate.BOOT_N
BOOT_SEED = evaluate.BOOT_SEED
CODE_PATH = Path(__file__).resolve()


def e002_capture_ids(captures: list[dict]) -> set[str]:
    """Captures used by E002 (its registered pair rule); the E004 registration excludes them."""
    pair = forecast.select_e002_pair(captures, forecast.registration_time())
    return {c["capture_id"] for c in pair} if pair else set()


def qualifying_captures(
    captures: list[dict],
    reg_time: datetime,
    n: int = N_SNAPSHOTS,
    exclude: set[str] | None = None,
) -> list[dict]:
    """Complete captures started after registration, minus E002's, first ``n`` by start time.

    If ``exclude`` is None the E002 pair is derived from ``captures`` by E002's own rule.
    """
    exclude = e002_capture_ids(captures) if exclude is None else exclude
    post = [
        c
        for c in captures
        if c.get("state") == "complete"
        and c["_start"] > reg_time
        and c["capture_id"] not in exclude
    ]
    return sorted(post, key=lambda c: c["_start"])[:n]


def event_clusters(pairs: pd.DataFrame) -> tuple[np.ndarray, int]:
    """Cluster key = event_id, falling back to market_id (prefixed); returns fallback count."""
    ev = pairs["event_id"]
    missing = (ev.isna() | ev.astype(str).str.strip().isin(["", "nan", "None"])).to_numpy()
    key = np.where(
        missing, "m:" + pairs["market_id"].astype(str), "e:" + ev.astype(str)
    )
    return key, int(missing.sum())


def verdict(
    r2: float, r2_ci: tuple[float, float], n_pos: int, slope: float, slope_ci: tuple[float, float]
) -> str:
    """Registered E004 verdict (all three conditions, else Not supported / Inconclusive)."""
    if r2 > 0 and r2_ci[0] > 0 and n_pos >= MIN_POSITIVE_PERIODS and slope < 0 and slope_ci[1] < 0:
        return "Supported (exploratory, prospective)"
    if not r2 > 0 or not slope < 0:
        return "Not supported"
    return "Inconclusive"


def trade_pnl(
    dmid_hat: np.ndarray,
    bid_i: np.ndarray,
    ask_i: np.ndarray,
    bid_j: np.ndarray,
    ask_j: np.ndarray,
    spread_i: np.ndarray,
) -> pd.DataFrame:
    """Per-1-share P&L for pairs with |dmid_hat| > spread_i/2 (touch-to-touch and mid exit)."""
    sel = np.abs(dmid_hat) > spread_i / 2
    up = dmid_hat > 0
    mid_j = (bid_j + ask_j) / 2
    touch = np.where(up, bid_j - ask_i, bid_i - ask_j)
    opt = np.where(up, mid_j - ask_i, bid_i - mid_j)
    return pd.DataFrame({"selected": sel, "pnl_touch": touch, "pnl_mid": opt})


def clustered_mean_ci(
    cluster: np.ndarray, v: np.ndarray, n: int = BOOT_N, seed: int = BOOT_SEED
) -> tuple[float, float]:
    codes, uniq = pd.factorize(cluster)
    k = len(uniq)
    cs = np.bincount(codes, weights=v, minlength=k)
    cn = np.bincount(codes, minlength=k).astype(float)
    rng = np.random.default_rng(seed)
    vals = np.empty(n)
    for b in range(n):
        idx = rng.integers(0, k, size=k)
        d = cn[idx].sum()
        vals[b] = cs[idx].sum() / d if d > 0 else np.nan
    lo, hi = np.nanpercentile(vals, [2.5, 97.5])
    return float(lo), float(hi)


def lost_selected(pairs: pd.DataFrame) -> dict:
    """Descriptive: pairs selected at origin (|dmid_hat| > spread_i/2) whose target is unavailable.

    Overall and per period. Uses only origin quantities, so it is defined for every pair.
    """
    hat = pairs["dmid_hat"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        sel = np.abs(hat) > pairs["spread"].to_numpy(float) / 2
    lost = sel & pairs["dmid"].isna().to_numpy()
    per = pairs["period"].to_numpy()
    return {
        "n_selected_trades_lost_to_target_unavailability": int(lost.sum()),
        "n_selected_at_origin": int(sel.sum()),
        "by_period": {
            int(p): {
                "lost": int((lost & (per == p)).sum()),
                "selected_at_origin": int((sel & (per == p)).sum()),
            }
            for p in sorted(np.unique(per))
        },
    }


def _exec_block(cl: np.ndarray, v: np.ndarray) -> dict:
    if len(v) == 0:
        return {"n_trades": 0, "mean_pnl": None, "ci": None, "hit_rate": None}
    lo, hi = clustered_mean_ci(cl, v)
    return {
        "n_trades": int(len(v)),
        "mean_pnl": float(v.mean()),
        "ci": [lo, hi],
        "hit_rate": float((v > 0).mean()),
    }


def build_panel(caps: list[dict], spec: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Consecutive pairs of the qualifying captures with touches attached."""
    frames, counts = [], []
    snaps = [forecast.load_snapshot(Path(c["dir"]))[0] for c in caps]
    for k in range(len(caps) - 1):
        j_sched = panel._epoch(pd.Series([caps[k + 1]["started_utc"]]))[0]
        pairs, cnt = panel.build_pair(snaps[k], snaps[k + 1], j_sched, k)
        oi = snaps[k].drop_duplicates("market_id").set_index("market_id")
        oj = snaps[k + 1].drop_duplicates("market_id").set_index("market_id")
        mk = pairs["market_id"]
        pairs["bid_i"] = oi["best_bid"].reindex(mk).to_numpy(float)
        pairs["ask_i"] = oi["best_ask"].reindex(mk).to_numpy(float)
        pairs["bid_j"] = oj["best_bid"].reindex(mk).to_numpy(float)
        pairs["ask_j"] = oj["best_ask"].reindex(mk).to_numpy(float)
        cnt.update({"capture_i": caps[k]["capture_id"], "capture_j": caps[k + 1]["capture_id"]})
        frames.append(pairs)
        counts.append(cnt)
    out = pd.concat(frames, ignore_index=True)
    out["dmid_hat"] = float(spec["coef"]) * out[spec["feature"]].to_numpy(float)
    return out, counts


def analyse(pairs: pd.DataFrame, counts: list[dict]) -> dict:
    av = pairs[pairs["dmid"].notna()].reset_index(drop=True)
    cl, fallback = event_clusters(av)
    y, yh = av["dmid"].to_numpy(float), av["dmid_hat"].to_numpy(float)
    sse_m, sse_0 = (y - yh) ** 2, y**2
    r2 = evaluate.r2_oos(float(sse_m.sum()), float(sse_0.sum()))
    r2_ci = evaluate.clustered_bootstrap_r2(cl, sse_m, sse_0)
    x = av["chg_1h"].to_numpy(float)
    slope = evaluate.ols_origin_slope(x, y)
    slope_ci = evaluate.clustered_bootstrap_slope(cl, x, y)
    per_period = []
    for p, g in av.groupby("period"):
        gy, gh = g["dmid"].to_numpy(float), g["dmid_hat"].to_numpy(float)
        per_period.append(
            {
                "period": int(p),
                "n": int(len(g)),
                "r2_oos": evaluate.r2_oos(float(((gy - gh) ** 2).sum()), float((gy**2).sum())),
            }
        )
    n_pos = sum(1 for d in per_period if d["r2_oos"] > 0)
    tr = trade_pnl(
        yh,
        av["bid_i"].to_numpy(float),
        av["ask_i"].to_numpy(float),
        av["bid_j"].to_numpy(float),
        av["ask_j"].to_numpy(float),
        av["spread"].to_numpy(float),
    )
    sel = tr["selected"].to_numpy()
    touch = _exec_block(cl[sel], tr["pnl_touch"].to_numpy()[sel])
    mid = _exec_block(cl[sel], tr["pnl_mid"].to_numpy()[sel])
    by_period = []
    for p in sorted(av["period"].unique()):
        m = sel & (av["period"].to_numpy() == p)
        by_period.append(
            {
                "period": int(p),
                "n_trades": int(m.sum()),
                "mean_pnl_touch": float(tr["pnl_touch"].to_numpy()[m].mean()) if m.any() else None,
                "mean_pnl_mid": float(tr["pnl_mid"].to_numpy()[m].mean()) if m.any() else None,
            }
        )
    interesting = touch["ci"] is not None and touch["ci"][0] > 0
    return {
        "experiment": "E004",
        "counts": {
            "periods": counts,
            "pairs_eligible": int(len(pairs)),
            "pairs_target_available": int(len(av)),
            "pairs_target_unavailable_excluded": int(len(pairs) - len(av)),
            "markets": int(av["market_id"].nunique()),
            "events_clusters": int(len(set(cl.tolist()))),
            "event_id_fallback_to_market_rows": fallback,
        },
        "primary": {
            "r2_oos": r2,
            "r2_ci": list(r2_ci),
            "per_period": per_period,
            "n_periods_r2_positive": n_pos,
            "n_periods": len(per_period),
            "slope_through_origin": slope,
            "slope_ci": list(slope_ci),
            "verdict": verdict(r2, r2_ci, n_pos, slope, slope_ci),
        },
        "execution": {
            "rule": "|dmid_hat| > spread_i/2; 1 share; fees, depth, latency ignored",
            "touch_to_touch": touch,
            "optimistic_mid_exit": mid,
            "by_period": by_period,
            "lost_to_target_unavailability": lost_selected(pairs),
            "label": "economically interesting (exploratory)" if interesting else "not shown",
        },
    }


def _json_default(o: object) -> object:
    return o.item() if hasattr(o, "item") else str(o)


def status(
    snapshot_root: Path = forecast.SNAPSHOT_ROOT, reg_time: datetime | None = None
) -> dict:
    reg_time = reg_time or forecast.registration_time(REGISTRATION_COMMIT)
    caps = qualifying_captures(forecast.list_complete_captures(snapshot_root), reg_time)
    return {
        "registration_time_utc": reg_time.isoformat(),
        "qualifying": len(caps),
        "required": N_SNAPSHOTS,
        "ready": len(caps) >= N_SNAPSHOTS,
        "capture_ids": [c["capture_id"] for c in caps],
    }


def score(
    snapshot_root: Path = forecast.SNAPSHOT_ROOT,
    out_dir: Path = E004_DIR,
    reg_time: datetime | None = None,
    spec: dict | None = None,
) -> dict | None:
    """Score once 12 qualifying snapshots exist; refuse to overwrite; None if not ready."""
    spec = spec or forecast.load_spec()
    reg_time = reg_time or forecast.registration_time(REGISTRATION_COMMIT)
    caps = qualifying_captures(forecast.list_complete_captures(snapshot_root), reg_time)
    if len(caps) < N_SNAPSHOTS:
        return None
    out_path = Path(out_dir) / "results.json"
    if out_path.exists():
        raise FileExistsError(f"E004 results already written (append-only): {out_path}")
    pairs, counts = build_panel(caps, spec)
    res = analyse(pairs, counts)
    res["provenance"] = {
        "model_id": spec["model_id"],
        "spec_sha256": spec["_sha256"],
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "x") as fh:
        json.dump(res, fh, indent=1, default=_json_default)
    return res
