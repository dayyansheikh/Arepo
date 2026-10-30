"""Read-only surface for the research lab's frozen-model forecast log and scores.

Serves what is on disk under the configured research-lab data root and nothing else: no fixtures, no
reconstruction, no fallback. A missing root, missing/malformed manifest, hash mismatch or unknown
model yields ``status: "unavailable"`` with a reason. Forecasts are experimental and unvalidated.
"""
from __future__ import annotations

import hashlib
import json
import re
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


# --- Open lab notebook: experiment list and trial log ---

_REPO_ROOT = Path(__file__).resolve().parents[4]
LEDGER_REL = Path("docs") / "research_lab" / "EXPERIMENT_LEDGER.md"
TRIALS_REL = Path("docs") / "research_lab" / "trials.jsonl"
MAX_LEDGER_BYTES = 512 * 1024
MAX_TRIALS_BYTES = 16 * 1024 * 1024
MAX_TRIALS = 200
DEFAULT_TRIALS = 20
MAX_EXPERIMENTS = 50
MAX_METRICS = 12
MAX_TEXT = 600
# Result files per experiment, relative to the data root. First existing file wins.
RESULT_FILES: dict[str, tuple[str, ...]] = {
    "E002": ("e002/results.json",),
    "E003": ("e003/s2_results.json", "e003/results.json"),
    "E004": ("e004/results.json",),
    "E005": ("e005/results.json",),
}
_ROW_ID = re.compile(r"^E\d{3}$")
_METRIC_KEYS = ("r2_oos", "r2_diff")
_SCALAR_KEYS = ("experiment", "verdict", "label", "n", "n_pairs", "n_events", "scored_utc")


def get_ledger_path() -> Path:
    return _REPO_ROOT / LEDGER_REL


def get_trials_path() -> Path:
    return _REPO_ROOT / TRIALS_REL


def _clip(v: Any) -> str:
    return str(v).strip()[:MAX_TEXT]


def _status_chip(raw: str) -> str:
    t = raw.upper()
    if t.startswith("COMPLETE"):
        return "complete"
    if t.startswith("REGISTERED"):
        return "registered"
    return "unknown"


def parse_ledger_table(text: str) -> list[dict[str, str]]:
    """Rows of the ledger summary table; malformed or non-experiment rows are skipped."""
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 4 or not _ROW_ID.match(cells[0]):
            continue
        rows.append({
            "id": cells[0],
            "status_raw": _clip(cells[1]),
            "status": _status_chip(cells[1]),
            "question": _clip(cells[2]),
            "result_summary": _clip(cells[3]),
        })
        if len(rows) >= MAX_EXPERIMENTS:
            break
    return rows


def _scalar(v: Any) -> Any:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v if v == v and abs(v) != float("inf") else None
    if isinstance(v, str):
        return v[:120]
    return None


def _collect_metrics(node: Any, path: str, depth: int, out: list[dict[str, Any]]) -> None:
    if depth > 4 or len(out) >= MAX_METRICS or not isinstance(node, dict):
        return
    key = next((k for k in _METRIC_KEYS if _num(node.get(k)) is not None), None)
    if key is not None:
        ci = node.get("ci")
        ci_out = None
        if isinstance(ci, list) and len(ci) == 2 and all(_num(c) is not None for c in ci):
            ci_out = [float(ci[0]), float(ci[1])]
        out.append({
            "name": path[:80],
            "metric": key,
            "value": _num(node[key]),
            "ci": ci_out,
            "n": _scalar(node.get("n")),
            "baseline": _scalar(node.get("baseline")),
            "verdict": _scalar(node.get("verdict")),
        })
    for k, v in node.items():
        if isinstance(v, dict):
            _collect_metrics(v, f"{path}.{k}" if path else str(k), depth + 1, out)


def summarize_result(data: Any) -> dict[str, Any]:
    """Whitelisted, bounded summary of a result file. Everything else is dropped."""
    if not isinstance(data, dict):
        return {"fields": {}, "metrics": []}
    fields = {k: _scalar(data.get(k)) for k in _SCALAR_KEYS if _scalar(data.get(k)) is not None}
    metrics: list[dict[str, Any]] = []
    _collect_metrics(data, "", 0, metrics)
    return {"fields": fields, "metrics": metrics}


def _result_for(root: Path | None, exp_id: str) -> dict[str, Any]:
    files = RESULT_FILES.get(exp_id)
    if not files:
        return {"status": "no_result_file_defined"}
    if root is None or not root.is_dir():
        return {"status": "unavailable", "reason": "Result data root is not available."}
    for rel in files:
        path = root / rel
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_RESULTS_BYTES:
            return {"status": "unavailable", "reason": "Result file exceeds the size bound."}
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            return {"status": "unavailable", "reason": "Result file is malformed."}
        return {"status": "available", **summarize_result(data)}
    return {"status": "pending", "reason": "No result file has been produced."}


@router.get("/experiments")
def experiments(
    root: Path | None = Depends(get_research_lab_root),
    ledger: Path = Depends(get_ledger_path),
) -> dict[str, Any]:
    try:
        if ledger.stat().st_size > MAX_LEDGER_BYTES:
            return _unavailable("Experiment ledger exceeds the serving size bound.")
        text = ledger.read_text()
    except (OSError, UnicodeDecodeError):
        return _unavailable("Experiment ledger is not available in this environment.")
    rows = parse_ledger_table(text)
    if not rows:
        return _unavailable("Experiment ledger has no parseable experiment rows.")
    for r in rows:
        r["result"] = _result_for(root, r["id"])
    return {"status": "available", "experiments": rows,
            "source": "docs/research_lab/EXPERIMENT_LEDGER.md"}


def _trial_summary(t: dict[str, Any]) -> dict[str, Any]:
    summ = t.get("summary")
    n_models = len(summ) if isinstance(summ, dict) else None
    return {
        "trial_id": _scalar(t.get("trial_id")),
        "utc": _scalar(t.get("utc")),
        "dataset": _scalar(t.get("dataset")),
        "kind": _scalar(t.get("kind")),
        "label": _scalar(t.get("label")),
        "preset": _scalar(t.get("preset")),
        "run_id": _scalar(t.get("run_id")),
        "status": _scalar(t.get("status")),
        "n_models_summarised": n_models,
    }


@router.get("/trials")
def trials(
    limit: int = Query(DEFAULT_TRIALS, ge=1, le=MAX_TRIALS),
    path: Path = Depends(get_trials_path),
) -> dict[str, Any]:
    try:
        if path.stat().st_size > MAX_TRIALS_BYTES:
            return _unavailable("Trial log exceeds the serving size bound.")
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return _unavailable("Trial log is not available in this environment.")
    parsed: list[dict[str, Any]] = []
    malformed = 0
    for ln in lines:
        if not ln.strip():
            continue
        try:
            obj = json.loads(ln)
        except ValueError:
            malformed += 1
            continue
        if isinstance(obj, dict):
            parsed.append(obj)
        else:
            malformed += 1
    return {
        "status": "available",
        "total": len(parsed),
        "malformed_lines": malformed,
        "trials": [_trial_summary(t) for t in parsed[-limit:]][::-1],
    }
