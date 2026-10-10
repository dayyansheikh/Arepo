"""Run provenance and the append-only trial log for research-lab comparisons.

``run_provenance`` records what code and environment produced a result: git HEAD, a dirty-tree
flag (tracked files only), a sha256 per research_lab module actually used, and an environment
fingerprint. ``append_trial`` adds one JSON line to ``docs/research_lab/trials.jsonl``; existing
lines are never rewritten. Nothing here makes a scientific claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
REPO_ROOT = BACKEND.parent
TRIALS_PATH = REPO_ROOT / "docs" / "research_lab" / "trials.jsonl"
DEV_LABEL = "DEVELOPMENT/post-hoc"
CORE_MODULES = ("compare", "features", "panel", "evaluate", "models", "extract")
UNKNOWN = "unknown"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        r = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def git_state(cwd: Path = REPO_ROOT) -> dict:
    """HEAD sha and whether tracked files differ from HEAD (untracked files ignored)."""
    head = _git(["rev-parse", "HEAD"], cwd)
    status = _git(["status", "--porcelain", "--untracked-files=no"], cwd)
    return {
        "git_head": head.strip() if head and head.strip() else UNKNOWN,
        "git_dirty": None if status is None else bool(status.strip()),
    }


def imported_research_lab_files() -> list[Path]:
    """Files of every astrolabe.research_lab module loaded in this process, plus the core set."""
    found = {HERE / f"{n}.py" for n in CORE_MODULES}
    for name, mod in list(sys.modules.items()):
        if name.startswith("astrolabe.research_lab") and getattr(mod, "__file__", None):
            found.add(Path(mod.__file__).resolve())
    return sorted(p for p in found if p.is_file())


def _version(name: str) -> str:
    try:
        return __import__(name).__version__
    except Exception:  # any import problem is recorded as unknown
        return UNKNOWN


def environment() -> dict:
    reqs = {}
    for fname in ("requirements.txt", "requirements.lock"):
        p = BACKEND / fname
        reqs[fname] = sha256_file(p) if p.is_file() else None
    return {
        "python": platform.python_version(),
        "numpy": _version("numpy"),
        "pandas": _version("pandas"),
        "requirements_sha256": reqs,
        "platform": platform.platform(),
    }


def run_provenance(module_paths: list[Path] | None = None, *, repo_root: Path = REPO_ROOT) -> dict:
    paths = imported_research_lab_files() if module_paths is None else list(module_paths)
    return {
        **git_state(repo_root),
        "modules_sha256": {Path(p).name: sha256_file(Path(p)) for p in sorted(paths)},
        "env": environment(),
    }


def summarize_pooled(result: dict) -> dict:
    """Small per-model pooled metrics for the trial log."""
    keys = ("r2_oos", "ci_lo", "ci_hi", "mae")
    models = result.get("pooled", {}).get("models", {})

    def clean(x):
        return None if isinstance(x, float) and x != x else x  # NaN -> null (strict JSON)

    return {m: {k: clean(v.get(k)) for k in keys} for m, v in models.items()}


def append_trial(record: dict, path: Path = TRIALS_PATH) -> dict:
    """Append one JSON line (append mode, flushed and fsynced). Returns the full record."""
    full = {
        "trial_id": str(uuid.uuid4()),
        "utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": "comparison",
        "label": DEV_LABEL,
        **record,
    }
    line = json.dumps(full, sort_keys=True, default=float, allow_nan=True) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    return full
