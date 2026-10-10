"""Read-only surface for the research lab's frozen-model forecast log and scores.

Serves what is on disk under the configured research-lab data root and nothing else: no fixtures, no
reconstruction, no fallback. A missing root, missing/malformed manifest, hash mismatch or unknown
model yields ``status: "unavailable"`` with a reason. Forecasts are experimental and unvalidated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Query

from ...config import get_settings

router = APIRouter(prefix="/api/research-lab", tags=["research-lab"])

MAX_TOP = 100
DEFAULT_TOP = 25
MAX_FORECAST_BYTES = 64 * 1024 * 1024  # compressed log file ceiling
MAX_RESULTS_BYTES = 256 * 1024
_REPO_DEV_ROOT = Path(__file__).resolve().parents[4] / "data-dumps" / "research_lab"

# Static, reviewed description of each frozen model. Unknown model ids are not served.
MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "e002_reversal_v1": {
        "spec": {
            "feature": "chg_1h",
            "coef": -0.331610,
            "target": "next-snapshot change in midpoint",
            "form": "dmid_hat = -0.331610 * oneHourPriceChange (missing = 0)",
        },
        "registered_commit": "58a13a6",
        "experimental": True,
        "validation_status": "E002 prospective test pending",
    }
}

_cache: dict[tuple[str, int, int], dict[str, Any]] = {}


def get_research_lab_root() -> Path | None:
    """Configured data root; local-dev default only outside production; else None."""
    s = get_settings()
    if s.research_lab_data_root:
        return Path(s.research_lab_data_root)
    if s.environment != "production":
        return _REPO_DEV_ROOT
    return None


def _unavailable(reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "reason": reason}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_latest(root: Path) -> dict[str, Any]:
    fdir = root / "forecasts"
    if not fdir.is_dir():
        return _unavailable("No forecast log has been recorded yet.")
    captures = sorted(d for d in fdir.iterdir() if d.is_dir())
    if not captures:
        return _unavailable("No forecast log has been recorded yet.")
    cap = captures[-1]  # newest capture id; an invalid newest log is NOT skipped silently
    mans = sorted(cap.glob("*.manifest.json"))
    if not mans:
        return _unavailable(f"Latest forecast capture {cap.name} has no manifest.")
    man_path = mans[-1]
    try:
        man = json.loads(man_path.read_text())
        model_id = man["model_id"]
        n_forecasts = int(man["n_forecasts"])
        created = man["prediction_created_utc"]
        sha = man["forecast_csv_sha256"]
        capture_id = man["snapshot_capture_id"]
    except (OSError, ValueError, KeyError, TypeError):
        return _unavailable(f"Forecast manifest for {cap.name} is malformed.")
    model = MODEL_REGISTRY.get(model_id)
    if model is None:
        return _unavailable(f"Forecast model '{model_id}' is not a registered model.")
    csv_path = cap / f"{model_id}.csv.gz"
    try:
        st = csv_path.stat()
    except OSError:
        return _unavailable("Forecast file referenced by the manifest is missing.")
    if st.st_size > MAX_FORECAST_BYTES:
        return _unavailable("Forecast file exceeds the serving size bound.")
    key = (str(csv_path), st.st_mtime_ns, st.st_size)
    if key not in _cache:
        if _sha256(csv_path) != sha:
            return _unavailable("Forecast file does not match its manifest hash.")
        try:
            df = pd.read_csv(
                csv_path,
                dtype={"market_id": str, "event_id": str},
                usecols=["market_id", "origin_receipt_utc", "mid", "spread", "chg_1h", "dmid_hat"],
            )
        except (OSError, ValueError, pd.errors.ParserError):
            return _unavailable("Forecast file could not be parsed.")
        if len(df) != n_forecasts:
            return _unavailable("Forecast row count does not match its manifest.")
        _cache.clear()
        _cache[key] = {"df": df, "man": man, "model": model, "capture_id": capture_id,
                       "model_id": model_id, "created": created}
    return {"status": "ok", **_cache[key]}


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _direction(dmid_hat: float) -> str | None:
    # Repo vocabulary values ("up"/"down"); the frontend renders them via directionLabel().
    if dmid_hat > 0:
        return "up"
    if dmid_hat < 0:
        return "down"
    return None


@router.get("/forecasts/latest")
def latest_forecasts(
    top: int = Query(DEFAULT_TOP, ge=1, le=MAX_TOP),
    root: Path | None = Depends(get_research_lab_root),
) -> dict[str, Any]:
    if root is None or not root.is_dir():
        return _unavailable("Research-lab forecast data is not available in this environment.")
    loaded = _load_latest(root)
    if loaded["status"] != "ok":
        return loaded
    df: pd.DataFrame = loaded["df"]
    big = df.assign(_abs=df["dmid_hat"].abs()).nlargest(top, "_abs", keep="first")
    rows = []
    for r in big.itertuples(index=False):
        d = _num(r.dmid_hat)
        if d is None or d == 0:
            continue  # zero predicted move carries no direction; do not list it as a "largest move"
        rows.append({
            "market_id": r.market_id,
            "mid": _num(r.mid),
            "spread": _num(r.spread),
            "chg_1h": _num(r.chg_1h),
            "dmid_hat": d,
            "direction": _direction(d),
        })
    model = loaded["model"]
    return {
        "status": "available",
        "model": {"model_id": loaded["model_id"], **model},
        "capture": {
            "capture_id": loaded["capture_id"],
            "origin_receipt_min_utc": str(df["origin_receipt_utc"].min()),
            "origin_receipt_max_utc": str(df["origin_receipt_utc"].max()),
        },
        "n_eligible": int(len(df)),
        "top": rows,
        "top_note": "Question text is not stored in the snapshot rows; markets are shown by id.",
        "created_utc": loaded["created"],
    }


@router.get("/forecasts/scores")
def forecast_scores(root: Path | None = Depends(get_research_lab_root)) -> dict[str, Any]:
    if root is None or not root.is_dir():
        return _unavailable("Research-lab score data is not available in this environment.")
    path = root / "e002" / "results.json"
    try:
        size = path.stat().st_size
    except OSError:
        return _unavailable("No scored results yet: the E002 prospective test is pending.")
    if size > MAX_RESULTS_BYTES:
        return _unavailable("Scored results exceed the serving size bound.")
    try:
        results = json.loads(path.read_text())
    except (OSError, ValueError):
        return _unavailable("Scored results file is malformed.")
    return {"status": "available", "experiment": "E002", "results": results}
