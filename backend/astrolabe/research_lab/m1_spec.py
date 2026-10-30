# ruff: noqa: E501
"""M1 (CH263) spec constant block, pins and pin refusals. Clause numbers refer to ``docs/research_lab/MEASUREMENT_M1_CH263.md`` (frozen).

``SPEC`` is the constant block hashed into ``spec_sha``. It embeds the sha256 of the frozen design text and of every pinned class-setting
module (section 5, 11.5), so a changed module or design text makes ``check_pins`` refuse. ``code_sha`` hashes the M1 code files themselves
(``CODE_FILES``, which include ``m1_j0.py`` because its readers are imported). Research tooling only; no network here.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

ROLE = "prospective_measurement"
VERSION = "m1-code-v1"
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
REPO = HERE.parents[2]
DESIGN_PATH = REPO / "docs" / "research_lab" / "MEASUREMENT_M1_CH263.md"

PINNED_MODULES = ("boundary_map_ch240", "population_map_ch251", "census_map_ch269", "cb17_census", "cb13_label", "live_tests8_base", "calibration", "costs")

SPEC: dict = {
    "measurement": "M1_CH263", "version": VERSION, "role": ROLE,
    # section 2 (dates; the slide rule rewrites these in the registration commit only)
    "registered_utc": "2026-11-24T00:00:00Z", "end_utc": "2026-12-15T00:00:00Z", "readout_utc": "2027-01-15T00:00:00Z",
    "close_after_end_s": 6 * 3600, "analysis_after_readout_s": 12 * 3600,
    "grid0_utc": "2026-10-01T00:31:00Z", "grid_s": 7200.0, "tol_s": 1800.0, "missing_after_grid_s": 6 * 3600,
    "lookback_min_captures": 84,
    # section 3
    "fav": 0.90, "scope": "nonsports_excrypto", "price_dp": 6,
    # section 5
    "capital_rate": 0.05, "hours_per_year": 8760.0, "fee_policy": "conservative",
    # section 6 (cell lists are fixed)
    "cells": {
        "S1": ["lt1k", "1k-10k", "10k-100k", "ge100k", "tier_na"],
        "S2": ["economics", "culture", "weather", "other", "finance", "politics", "mentions", "tech", "geopolitics", "unknown"],
        "S3": ["standalone", "member_winner", "member_loser"],
        "S4": ["fee_free", "fee_on", "unknown"],
        "S5": ["YES", "NO"],
        "S6": ["c<=0.001", "(0.001,0.005]", "(0.005,0.01]", "(0.01,0.03]", "(0.03,0.10]", ">0.10"],
        "S7": ["future", "past<=24h", "past>24h", "missing"],
        "S8": ["1", "2-5", "6+"],
        "S9": ["0.001", "0.01", "other_or_missing"],
        "S10": ["days 1-7", "days 8-14", "days 15-21"],
    },
    "thin": {"final_units": 30, "events": 10},
    # section 7
    "bootstrap": {"B": 10000, "seed": 20261124, "ci": 0.95, "chunk": 250},
    "tu": {"strata": ["1", "2-3", "4-9", "10+"], "alpha": 0.05},
    # section 8.3 and 10 and 11 (cents-a-share thresholds written as dollars a share)
    "coverage_floor": 0.95,
    "coarse": {"min_final_units": 2000, "max_ci_half_width_ps": 0.003, "max_tu_ps": 0.003, "max_nonfinal_share": 0.02, "min_slot_coverage": 0.75},
    "void_sha_mismatch_share": 0.01,
    # section 9.4
    "fetch": {"batch": 50, "attempts": 3, "attempt_gap_s": 3600.0},
    "design_sha256": "7982f199edaf559fc4e6a5150709cc49d26b16984c869b6b75e2ef7dca107639",
    "pinned_module_sha256": {
        "boundary_map_ch240": "2bc9ff9edb97b76990579c90929e55f22cb4cfe9fdec852395bd07f7d3bea09a",
        "population_map_ch251": "82db7a75995f0b637b469f4abc421ad9be430fdf38f0a4bad7ed5e9e43a55140",
        "census_map_ch269": "3939f8fd3a3caf44f22076894a1a90ba2fcb9da8714b2cc25c89e9256ed16176",
        "cb17_census": "6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a",
        "cb13_label": "2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380",
        "live_tests8_base": "4b26756d4d1934c4da9a0b2b26d4ff3f2ac72f199bbc55d4ae6365b8ebc394e0",
        "calibration": "567cdbe9eab0a8fa5fccdf4350e44cb2fea0104d445e62188e3e363fba12dda1",
        "costs": "258856fc360fbe70ce7a062a3f156b66d9d71fd50de56bf3669935c4227f844d",
    },
}

CODE_FILES = (
    HERE / "m1_spec.py", HERE / "m1_extract.py", HERE / "m1_readout.py", HERE / "m1_analysis.py", HERE / "m1_j0.py",
    BACKEND / "scripts" / "run_m1.py",
)


class PinMismatch(RuntimeError):
    """A pinned module or the design text no longer hashes to its pin; ``.record`` holds the expected and actual values."""

    def __init__(self, record: dict) -> None:
        super().__init__("M1 pin mismatch: " + json.dumps(record, sort_keys=True))
        self.record = record


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def spec_sha(spec: dict = SPEC) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def code_sha_parts(files=CODE_FILES) -> dict:
    missing = sorted(Path(p).name for p in files if not Path(p).exists())
    if missing:
        raise PinMismatch({"missing_code_files": missing})  # a missing code file must not silently shrink code_sha
    return {Path(p).name: sha256_file(Path(p)) for p in files}


def code_sha(files=CODE_FILES) -> str:
    parts = code_sha_parts(files)
    return hashlib.sha256("\n".join(f"{k}:{parts[k]}" for k in sorted(parts)).encode()).hexdigest()


def module_paths() -> dict:
    return {n: Path(importlib.import_module(f"astrolabe.research_lab.{n}").__file__) for n in PINNED_MODULES}


def pin_record(spec: dict = SPEC, paths: dict | None = None, design: Path | None = None) -> dict:
    paths = module_paths() if paths is None else paths
    design = DESIGN_PATH if design is None else Path(design)
    mods = {}
    for n in PINNED_MODULES:
        exp = spec["pinned_module_sha256"][n]
        p = Path(paths[n])
        act = sha256_file(p) if p.exists() else None
        mods[n] = {"expected": exp, "actual": act, "ok": act == exp}
    dact = sha256_file(design) if design.exists() else None
    d = {"expected": spec["design_sha256"], "actual": dact, "ok": dact == spec["design_sha256"]}
    return {"modules": mods, "design": d, "ok": d["ok"] and all(m["ok"] for m in mods.values())}


def check_pins(spec: dict = SPEC, paths: dict | None = None, design: Path | None = None) -> dict:
    """Refuse (raise ``PinMismatch`` with every expected and actual value) unless the design text and every pinned module match."""
    rec = pin_record(spec, paths, design)
    if not rec["ok"]:
        raise PinMismatch(rec)
    return rec


def ts(spec: dict, key: str) -> float:
    return datetime.fromisoformat(str(spec[key]).replace("Z", "+00:00")).timestamp()


def grid0(spec: dict) -> float:
    return ts(spec, "grid0_utc")


def slot_of(spec: dict, t: float) -> tuple[int, bool]:
    s = int(round((t - grid0(spec)) / spec["grid_s"]))
    return s, abs(t - (grid0(spec) + s * spec["grid_s"])) <= spec["tol_s"]


def slot_time(spec: dict, s: int) -> float:
    return grid0(spec) + s * spec["grid_s"]


def window_slots(spec: dict) -> list[int]:
    """Grid slots whose grid time lies in [registered_utc, end_utc): 252 for the frozen 21-day window."""
    a = math.ceil((ts(spec, "registered_utc") - grid0(spec)) / spec["grid_s"])
    b = math.ceil((ts(spec, "end_utc") - grid0(spec)) / spec["grid_s"])
    return list(range(a, b))


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
