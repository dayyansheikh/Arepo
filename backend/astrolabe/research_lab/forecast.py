"""E002 prospective forecasting and scoring (frozen model, append-only forecast log).

``predict`` logs forecasts from one complete snapshot BEFORE any outcome exists. ``score`` applies
the E002 pre-registration (``docs/research_lab/EXPERIMENT_LEDGER.md``) unchanged: eligibility and
features from the origin rows only (j's scheduled start is the only j information used for
eligibility), target availability at j, market-clustered bootstrap (1,000 resamples, seed 116).
Forecast-time rule for the endDate eligibility term (no future capture is known yet):
``endDate unknown or > origin receipt time + 3h`` (``FORECAST_END_MARGIN_H``).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluate, panel

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT_ROOT = ROOT / "data-dumps" / "research_lab" / "snapshots"
FORECAST_ROOT = ROOT / "data-dumps" / "research_lab" / "forecasts"
E002_DIR = ROOT / "data-dumps" / "research_lab" / "e002"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "e002_reversal_v1.json"
REGISTRATION_COMMIT = "58a13a6"
MIN_GAP_H = 3.0
FORECAST_END_MARGIN_H = 3.0
ID_DTYPES = {"market_id": str, "event_id": str, "capture_id": str}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_spec(path: Path = SPEC_PATH) -> dict:
    spec = json.loads(Path(path).read_text())
    spec["_sha256"] = sha256_file(path)
    return spec


def _git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=15
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def load_snapshot(snapshot_dir: Path) -> tuple[pd.DataFrame, dict]:
    snapshot_dir = Path(snapshot_dir)
    manifest = json.loads((snapshot_dir / "manifest.json").read_text())
    if manifest.get("state") != "complete":
        raise ValueError(f"snapshot {snapshot_dir.name} is not complete: {manifest.get('state')}")
    rows = pd.read_csv(snapshot_dir / "rows.csv.gz", dtype=ID_DTYPES)
    return rows, manifest


def predict_frame(rows: pd.DataFrame, spec: dict) -> pd.DataFrame:
    """Forecasts for eligible markets, computed from the origin snapshot rows only."""
    binary = rows[rows["binary"] == 1].reset_index(drop=True)
    t_i_all = panel._epoch(binary["received_utc"])
    ok = panel.eligibility_mask(binary, t_i_all + FORECAST_END_MARGIN_H * 3600.0)
    o = binary[ok].reset_index(drop=True)
    feats = panel.compute_features(o, panel._epoch(o["received_utc"]))
    feature = spec["feature"]
    value = feats[feature].to_numpy(float)  # missing already mapped to 0 == spec["missing"]
    return pd.DataFrame(
        {
            "market_id": o["market_id"].to_numpy(),
            "event_id": o["event_id"].to_numpy(),
            "origin_receipt_utc": o["received_utc"].to_numpy(),
            "mid": feats["mid"].to_numpy(),
            "spread": feats["spread"].to_numpy(),
            feature: value,
            "dmid_hat": float(spec["coef"]) * value,
            "model_id": spec["model_id"],
        }
    )


def forecast_paths(snapshot_dir: Path, spec: dict, root: Path = FORECAST_ROOT) -> tuple[Path, Path]:
    d = Path(root) / Path(snapshot_dir).name
    return d / f"{spec['model_id']}.csv.gz", d / f"{spec['model_id']}.manifest.json"


def predict(
    snapshot_dir: Path, spec: dict | None = None, root: Path = FORECAST_ROOT
) -> tuple[pd.DataFrame, dict]:
    """Write the append-only forecast log for one complete snapshot; refuse to overwrite."""
    spec = spec or load_spec()
    snapshot_dir = Path(snapshot_dir)
    csv_path, man_path = forecast_paths(snapshot_dir, spec, root)
    if csv_path.exists() or man_path.exists():
        raise FileExistsError(f"forecast already logged (append-only): {csv_path}")
    rows, snap_manifest = load_snapshot(snapshot_dir)
    created = _utc_now()
    out = predict_frame(rows, spec)
    out["prediction_created_utc"] = created
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(csv_path, "xt", newline="", encoding="utf-8") as fh:
        out.to_csv(fh, index=False, float_format="%.17g")
    manifest = {
        "model_id": spec["model_id"],
        "spec_sha256": spec["_sha256"],
        "snapshot_capture_id": snap_manifest["capture_id"],
        "snapshot_manifest_sha256": sha256_file(snapshot_dir / "manifest.json"),
        "snapshot_rows_sha256": sha256_file(snapshot_dir / "rows.csv.gz"),
        "code_commit": _git("rev-parse", "HEAD") or "unknown",
        "code_dirty": bool(_git("status", "--porcelain", "--", "backend/astrolabe/research_lab")),
        "prediction_created_utc": created,
        "forecast_time_end_rule": f"endDate unknown or > origin receipt + {FORECAST_END_MARGIN_H}h",
        "n_origin_rows": int(len(rows)),
        "n_forecasts": int(len(out)),
        "forecast_csv_sha256": sha256_file(csv_path),
    }
    with open(man_path, "x") as fh:
        json.dump(manifest, fh, indent=1)
    return out, manifest


def list_complete_captures(root: Path = SNAPSHOT_ROOT) -> list[dict]:
    """Complete captures ordered by start time (manifest ``state == 'complete'`` only)."""
    caps = []
    for m in sorted(Path(root).glob("*/manifest.json")):
        man = json.loads(m.read_text())
        if man.get("state") == "complete":
            caps.append({**man, "dir": str(m.parent), "_start": _parse_ts(man["started_utc"])})
    return sorted(caps, key=lambda c: c["_start"])


def registration_time(commit: str = REGISTRATION_COMMIT) -> datetime:
    iso = _git("show", "-s", "--format=%cI", commit)
    if not iso:
        raise RuntimeError(f"cannot read commit time of {commit}")
    return _parse_ts(iso)


def select_e002_pair(
    captures: list[dict], reg_time: datetime, min_gap_h: float = MIN_GAP_H
) -> tuple[dict, dict] | None:
    """First complete capture after registration, then the first complete one >= 3h later.

    Depends only on capture start times and states, never on any market data.
    """
    post = [c for c in captures if c["_start"] > reg_time]
    if not post:
        return None
    first = post[0]
    for c in post[1:]:
        if c["_start"] - first["_start"] >= timedelta(hours=min_gap_h):
            return first, c
    return None


def _slope_block(sub: pd.DataFrame) -> dict:
    x, y = sub["chg_1h"].to_numpy(float), sub["dmid"].to_numpy(float)
    if len(sub) < 2 or not (x != 0).any():
        return {"n": int(len(sub)), "slope": None, "ci": None}
    lo, hi = evaluate.clustered_bootstrap_slope(sub["market_id"].to_numpy(), x, y)
    return {"n": int(len(sub)), "slope": evaluate.ols_origin_slope(x, y), "ci": [lo, hi]}


def _terciles(sub: pd.DataFrame, col: str) -> dict:
    qs = sub[col].quantile([1 / 3, 2 / 3]).to_numpy()
    grp = np.digitize(sub[col].to_numpy(float), qs, right=True)
    return {
        name: {**_slope_block(sub[grp == k]), "range": [
            float(sub[col][grp == k].min()), float(sub[col][grp == k].max())
        ]}
        for k, name in enumerate(("low", "mid", "high"))
        if (grp == k).any()
    }


def verdict(r2: float, r2_ci: tuple[float, float], slope: float, slope_ci: tuple[float, float]):
    """E002 verdict: Confirmed needs both CIs on the right side; a wrong-sign point fails."""
    if r2 > 0 and r2_ci[0] > 0 and slope < 0 and slope_ci[1] < 0:
        return "Confirmed (exploratory, prospective)"
    if not r2 > 0 or not slope < 0:
        return "Not confirmed"
    return "Inconclusive"


def score(
    origin_dir: Path,
    target_dir: Path,
    spec: dict | None = None,
    forecast_root: Path = FORECAST_ROOT,
) -> dict:
    """Score the frozen model on one origin->target capture pair under the E002 rules."""
    spec = spec or load_spec()
    snap_i, man_i = load_snapshot(origin_dir)
    snap_j, man_j = load_snapshot(target_dir)
    j_sched = panel._epoch(pd.Series([man_j["started_utc"]]))[0]
    pairs, counts = panel.build_pair(snap_i, snap_j, j_sched, 0)
    pairs["dmid_hat"] = float(spec["coef"]) * pairs[spec["feature"]].to_numpy(float)
    log_check = _check_logged_forecast(pairs, origin_dir, spec, forecast_root)
    av = pairs[pairs["dmid"].notna()].reset_index(drop=True)
    y, yh = av["dmid"].to_numpy(float), av["dmid_hat"].to_numpy(float)
    sse_m, sse_0 = (y - yh) ** 2, y**2
    mk = av["market_id"].to_numpy()
    r2 = evaluate.r2_oos(float(sse_m.sum()), float(sse_0.sum()))
    r2_ci = evaluate.clustered_bootstrap_r2(mk, sse_m, sse_0)
    prim = _slope_block(av)
    slope, slope_ci = prim["slope"], tuple(prim["ci"])
    half_spread = av["spread"].to_numpy(float) / 2
    allp = pairs["dmid_hat"].abs().to_numpy(float) > pairs["spread"].to_numpy(float) / 2
    return {
        "experiment": "E002",
        "model_id": spec["model_id"],
        "spec_sha256": spec["_sha256"],
        "captures": {
            "origin": man_i["capture_id"],
            "target": man_j["capture_id"],
            "origin_started_utc": man_i["started_utc"],
            "target_started_utc": man_j["started_utc"],
            "gap_h": (_parse_ts(man_j["started_utc"]) - _parse_ts(man_i["started_utc"]))
            .total_seconds() / 3600,
        },
        "logged_forecast_check": log_check,
        "counts": {
            **counts,
            "markets": int(av["market_id"].nunique()),
            "events": int(av["event_id"].nunique()),
            "median_horizon_h": float(av["horizon_h"].median()),
        },
        "primary": {
            "r2_oos": r2,
            "r2_ci": list(r2_ci),
            "slope_through_origin": slope,
            "slope_ci": list(slope_ci),
            "verdict": verdict(r2, r2_ci, slope, slope_ci),
        },
        "descriptive": {
            "slope_with_intercept": float(np.polyfit(av["chg_1h"], y, 1)[0])
            if len(av) > 2 and av["chg_1h"].std() > 0 else None,
            "spread_terciles": _terciles(av, "spread"),
            "log_liquidity_terciles": _terciles(av, "log_liq"),
            "share_abs_dmid_hat_gt_half_spread_target_available": float(
                (np.abs(yh) > half_spread).mean()
            ),
            "share_abs_dmid_hat_gt_half_spread_all_eligible": float(allp.mean()),
        },
    }


def _check_logged_forecast(
    pairs: pd.DataFrame, origin_dir: Path, spec: dict, forecast_root: Path
) -> dict:
    """Recomputed predictions must equal the logged forecast exactly (assert on the overlap)."""
    csv_path, man_path = forecast_paths(Path(origin_dir), spec, forecast_root)
    if not csv_path.exists():
        return {"logged": False}
    man = json.loads(man_path.read_text())
    if man["spec_sha256"] != spec["_sha256"]:
        raise AssertionError("logged forecast was made with a different model spec")
    if sha256_file(csv_path) != man["forecast_csv_sha256"]:
        raise AssertionError("forecast log file hash differs from its manifest")
    log_df = pd.read_csv(csv_path, dtype=ID_DTYPES, float_precision="round_trip")
    logged = log_df.set_index("market_id")["dmid_hat"]
    rec = pairs.set_index("market_id")["dmid_hat"]
    common = rec.index.intersection(logged.index)
    if not np.array_equal(rec.loc[common].to_numpy(), logged.loc[common].to_numpy()):
        raise AssertionError("recomputed predictions differ from the logged forecast")
    return {
        "logged": True,
        "n_compared": int(len(common)),
        "n_scored_without_logged_forecast": int(len(rec.index.difference(logged.index))),
        "n_logged_not_scored": int(len(logged.index.difference(rec.index))),
        "forecast_csv_sha256": man["forecast_csv_sha256"],
    }
