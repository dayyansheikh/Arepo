"""Per-unit resumability for the MC1 development run (``scripts/run_ml_dev.py --resume-dir``).

A *unit* is one (arm, fold) out-of-fold fit: its test positions, probabilities, fold diagnostics
(including the per-fold hyper-parameter selection record) and, for M2, its SHAP block. After each
completed unit the run writes the unit atomically (tmp file + rename) and refreshes a small progress
manifest recording the identity of the run: fold-manifest sha256, panel hash, sha256 of the code
files and the argv. A restart with the same identity loads finished units instead of refitting
them; any differing identity field is refused (no silent mixing of slices). Nothing here changes
what is fitted: a loaded unit is the exact object the fit produced (pickle), so a resumed run is
bit-identical to an uninterrupted one given the seeds.

Development tooling only: no result, gate, threshold or formula is touched.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
import time
from pathlib import Path

PROGRESS = "progress.json"
TRIALS_MARKER = "trials_flush.json"
# flags that may differ between slices without changing the run
NON_IDENTITY_FLAGS = ("--time-budget-s", "--resume-dir")


class BudgetExhausted(Exception):
    """The slice's time budget is spent; stop at this unit boundary (exit 75, tempfail)."""


class ResumeMismatch(SystemExit):
    """The resume directory belongs to a different run (hash or argv differs)."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalise_argv(argv: list[str]) -> list[str]:
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in NON_IDENTITY_FLAGS:
            skip = True
            continue
        if any(a.startswith(f + "=") for f in NON_IDENTITY_FLAGS):
            continue
        out.append(a)
    return out


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", s)


class UnitStore:
    """Directory of completed units plus the identity-checking progress manifest."""

    def __init__(self, directory: Path, identity: dict, *, budget_s: float | None = None,
                 clock_start: float | None = None, clock=time.perf_counter):
        self.dir = Path(directory)
        self.identity = identity
        self.budget_s = budget_s
        self._clock = clock
        self._t0 = clock() if clock_start is None else clock_start
        self.fitted_this_slice = 0
        self.stamp: str | None = None
        self.fresh = False

    # -- identity / progress -------------------------------------------------------------------
    def open(self, stamp: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        pp = self.dir / PROGRESS
        if pp.exists():
            rec = json.loads(pp.read_text())
            bad = [k for k, v in self.identity.items() if rec.get("identity", {}).get(k) != v]
            if bad:
                raise ResumeMismatch(
                    f"REFUSED: resume dir {self.dir} was started by a different run; differing "
                    f"identity field(s): {bad}. Use a new --resume-dir (no mixing of slices).")
            self.stamp = rec["stamp"]
            return
        self.stamp = stamp
        self.fresh = True
        self._write_progress(units=[], slices=0)

    def _write_progress(self, units: list[str], slices: int | None = None) -> None:
        pp = self.dir / PROGRESS
        prev = json.loads(pp.read_text()) if pp.exists() else {}
        rec = {"identity": self.identity, "stamp": self.stamp, "units": units,
               "slices": prev.get("slices", 0) if slices is None else slices,
               "status": prev.get("status", "in_progress")}
        _atomic_write(pp, json.dumps(rec, indent=1, sort_keys=True).encode())

    def begin_slice(self) -> None:
        rec = json.loads((self.dir / PROGRESS).read_text())
        self._write_progress(rec["units"], rec.get("slices", 0) + 1)

    def mark_complete(self, paths: list[str]) -> None:
        pp = self.dir / PROGRESS
        rec = json.loads(pp.read_text())
        rec.update(status="complete", outputs=paths)
        _atomic_write(pp, json.dumps(rec, indent=1, sort_keys=True).encode())

    # -- units ---------------------------------------------------------------------------------
    def _path(self, arm: str, fold, collect_shap: bool) -> Path:
        return self.dir / f"unit__{_safe(arm)}__f{_safe(str(fold))}__s{int(bool(collect_shap))}.pkl"

    def load(self, arm: str, fold, collect_shap: bool) -> dict | None:
        p = self._path(arm, fold, collect_shap)
        if not p.exists():
            return None
        with open(p, "rb") as fh:
            unit = pickle.load(fh)  # trusted: written by this store
        if (unit["arm"], str(unit["fold"]), bool(unit["collect_shap"])) != (
                arm, str(fold), bool(collect_shap)):
            raise ResumeMismatch(f"REFUSED: unit file {p.name} does not match its key")
        return unit

    def save(self, arm: str, fold, collect_shap: bool, *, test_pos, proba, diag, shap) -> None:
        unit = {"arm": arm, "fold": fold, "collect_shap": bool(collect_shap),
                "test_pos": test_pos, "proba": proba, "diag": diag, "shap": shap}
        p = self._path(arm, fold, collect_shap)
        _atomic_write(p, pickle.dumps(unit, protocol=pickle.HIGHEST_PROTOCOL))
        rec = json.loads((self.dir / PROGRESS).read_text())
        if p.name not in rec["units"]:
            rec["units"].append(p.name)
        self._write_progress(rec["units"])
        self.fitted_this_slice += 1

    def checkpoint(self) -> None:
        """Called before fitting a not-yet-done unit: stop cleanly once the budget is spent.

        At least one unit is fitted per slice so every slice makes progress.
        """
        if (self.budget_s is not None and self.fitted_this_slice >= 1
                and self._clock() - self._t0 >= self.budget_s):
            raise BudgetExhausted(
                f"time budget {self.budget_s:g}s spent after {self.fitted_this_slice} unit(s)")

    # -- trials: written once, at final completion -----------------------------------------------
    def trials_marker(self) -> dict | None:
        p = self.dir / TRIALS_MARKER
        return json.loads(p.read_text()) if p.exists() else None

    def write_trials_marker(self, rec: dict) -> None:
        _atomic_write(self.dir / TRIALS_MARKER, json.dumps(rec, indent=1).encode())
