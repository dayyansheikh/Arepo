# ruff: noqa: E501
"""M2 (CH264) spec constant block, pins and pin refusals. Clause numbers refer to ``docs/research_lab/MEASUREMENT_M2_CH264.md`` (FROZEN).

``SPEC`` holds the declared constants of the text (dates, grid, cells, bootstrap, coarse thresholds, fetch rule). ``spec_sha`` of the real
spec is the sha256 of the frozen design text (section 2: "the sha256 of this file at the registration commit"); a dry-run spec (``dry_run``
key) hashes its own canonical JSON, so its ``spec_sha`` differs from the real one by construction. The design text and every pinned
class-setting module (section 5, eight files) plus the rule lexicon (3.5) are pins: ``check_pins`` refuses unless all match.
``code_sha`` hashes the M2 code files (``CODE_FILES``). Research tooling only; no network here. This module imports no other M2 module
at import time (``m2_j1`` imports it), so it can be hashed and checked on its own.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

ROLE = "prospective_measurement"
VERSION = "m2-code-v1"
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
REPO = HERE.parents[2]
DESIGN_PATH = REPO / "docs" / "research_lab" / "MEASUREMENT_M2_CH264.md"

PINNED_MODULES = ("boundary_map_ch240.py", "cb17_census.py", "live_tests11_base.py", "live_tests8_base.py", "population_map_ch251.py", "calibration.py", "costs.py",
                  "cb13_label.py")

SPEC: dict = {
    "measurement": "M2_CH264", "version": VERSION, "role": ROLE,
    # section 2
    "registered_utc": "2026-11-24T00:00:00Z", "end_utc": "2026-12-15T00:00:00Z", "readout_utc": "2027-01-29T00:00:00Z",
    "close_after_end_s": 6 * 3600, "analysis_after_readout_s": 12 * 3600,
    "grid0_utc": "2026-10-01T00:31:00Z", "grid_s": 7200.0, "tol_s": 1800.0, "missing_after_grid_s": 6 * 3600,
    "lookback_slots": 84,
    # section 3
    "scope": "nonsports_excrypto", "price_dp": 6, "mid_lo": 0.05, "mid_hi": 0.95, "overdue_s": 7200.0,
    # section 5
    "capital_rate": 0.05, "hours_per_year": 8760.0, "fee_policy": "conservative",
    # section 6 (cell lists are fixed; S10 has three week cells for the 21-day window)
    "cells": {
        "S1": ["low", "mid", "high", "na"],
        "S2": ["scheduled", "barrier", "both", "other", "no_rules", "rules_unresolved"],
        "S3": ["economics", "culture", "weather", "other", "finance", "politics", "mentions", "tech", "geopolitics", "unknown"],
        "S4": ["fee_free", "fee_on", "unknown"],
        "S5": ["YES", "NO"],
        "S6": ["(0.5,0.6]", "(0.6,0.7]", "(0.7,0.8]", "(0.8,0.9]", "(0.9,0.95]"],
        "S7": ["no", "yes"],
        "S8": ["1", "2-5", "6+"],
        "S9": ["0.001", "0.01", "other_or_missing"],
        "S10": ["days 1-7", "days 8-14", "days 15-21"],
        "S11": ["<=0.01", "(0.01,0.03]", "(0.03,0.10]", ">0.10"],
    },
    "thin": {"final_units": 30, "events": 10},
    # section 7
    "bootstrap": {"B": 10000, "seed": 20261125, "ci": 0.95, "chunk": 250},
    "bound": {"strata": ["1", "2-3", "4-9", "10+"], "alpha": 0.05},
    "hazard": {"cif_slots": {"6h": 3, "24h": 12, "72h": 36, "7d": 84, "30d": 360}, "hazard_slots": 12, "p_tokens": ["proposed", "disputed", "resolved"]},
    # section 8.4, 9.4, 10, 11
    "coverage_floor": 0.95,
    "backlog_share": 0.30,
    "coarse": {"min_final_units": 1500, "max_ci_half_width_ps": 0.03, "max_nonfinal_share": 0.10, "min_slot_coverage": 0.75, "min_followup_slot_coverage": 0.75},
    "void_sha_mismatch_share": 0.01,
    "fetch": {"batch": 50, "attempts": 3, "attempt_gap_s": 3600.0},
    "identity_tol": 1e-9,
    # the pins (design text, imported modules, rule lexicon)
    "design_sha256": "a7f30de2121a4c8817cca89a688f276ed72a449315b7dcbcc847b95ec3736e07",
    "pinned_module_sha256": {
        "boundary_map_ch240.py": "2bc9ff9edb97b76990579c90929e55f22cb4cfe9fdec852395bd07f7d3bea09a",
        "calibration.py": "567cdbe9eab0a8fa5fccdf4350e44cb2fea0104d445e62188e3e363fba12dda1",
        "cb13_label.py": "2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380",
        "cb17_census.py": "6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a",
        "costs.py": "258856fc360fbe70ce7a062a3f156b66d9d71fd50de56bf3669935c4227f844d",
        "live_tests11_base.py": "7f4d3db50311088bb6fbd1ee1eafb7f142fb58133ea1d7f6c684694eb75a9a68",
        "live_tests8_base.py": "4b26756d4d1934c4da9a0b2b26d4ff3f2ac72f199bbc55d4ae6365b8ebc394e0",
        "population_map_ch251.py": "82db7a75995f0b637b469f4abc421ad9be430fdf38f0a4bad7ed5e9e43a55140",
    },
    "rule_lexicon_sha256": "2209e0adc51fd0e48edd231574d37207a80b8f3ab34bca418cd910b7abe4b97e",
}

# Host dry run (code-freeze list, final verification SHOULD 3): the rule ledger is padded with inert synthetic records to the size it will have when J1 stops merging
# at the end of the window. Planning figures from M2-J0's counts (section 21): 109,264 row + 183,901 hash records committed over 11 day files = 26,651 records a
# day; the first pass reads about 8 retained days and the merge runs through the 21-day window, so about 30 days = 800,000 records, over a market set that grows
# beyond J0's 107,798 (250,000 assumed). Over-stating the size only makes the memory check stricter; it never touches a real market.
DRYRUN_LEDGER_PAD = (800_000, 250_000)

CODE_FILES = (
    HERE / "m2_spec.py", HERE / "m2_j1.py", HERE / "m2_j2.py", HERE / "m2_readout.py", HERE / "m2_analysis.py",
    BACKEND / "scripts" / "run_m2.py",
)


class M2Refusal(RuntimeError):
    """A declared refusal (overwrite, order, state chain, date gate, pin, blinding)."""


class PinMismatch(RuntimeError):
    """A pinned module, the design text, the lexicon, the spec_sha or the code_sha differs from its pin; ``.record`` holds expected and actual."""

    def __init__(self, record: dict) -> None:
        super().__init__("M2 pin mismatch: " + json.dumps(record, sort_keys=True))
        self.record = record


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def spec_sha(spec: dict = SPEC) -> str:
    """The real spec: the design text's sha256 (section 2). A dry-run spec: the sha256 of its canonical JSON (differs by construction)."""
    if spec.get("dry_run"):
        return sha256_bytes(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode())
    return spec["design_sha256"]


def code_sha_parts(files=CODE_FILES) -> dict:
    missing = sorted(Path(p).name for p in files if not Path(p).exists())
    if missing:
        raise PinMismatch({"missing_code_files": missing})  # a missing code file must not silently shrink code_sha
    return {Path(p).name: sha256_file(Path(p)) for p in files}


def code_sha(files=CODE_FILES) -> str:
    parts = code_sha_parts(files)
    return sha256_bytes("\n".join(f"{k}:{parts[k]}" for k in sorted(parts)).encode())


def module_paths() -> dict:
    return {n: HERE / n for n in PINNED_MODULES}


def pin_record(spec: dict = SPEC, paths: dict | None = None, design: Path | None = None, lexicon: str | None = None) -> dict:
    from . import m2_j1  # lazy: m2_j1 imports this module

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
    lact = m2_j1.lexicon_sha256() if lexicon is None else lexicon
    lx = {"expected": spec["rule_lexicon_sha256"], "actual": lact, "ok": lact == spec["rule_lexicon_sha256"]}
    return {"modules": mods, "design": d, "lexicon": lx, "ok": d["ok"] and lx["ok"] and all(m["ok"] for m in mods.values())}


def check_pins(spec: dict = SPEC, paths: dict | None = None, design: Path | None = None, lexicon: str | None = None) -> dict:
    """Refuse (raise ``PinMismatch`` with every expected and actual value) unless the design text, the lexicon and every pinned module match."""
    rec = pin_record(spec, paths, design, lexicon)
    if not rec["ok"]:
        raise PinMismatch(rec)
    return rec


def check_run_pins(pins: dict | None, spec: dict = SPEC) -> None:
    """The running ``spec_sha`` and ``code_sha`` must equal the registered pins (every pass of every job)."""
    if pins is None:
        return
    a, b = spec_sha(spec), code_sha()
    if pins.get("spec_sha") != a or pins.get("code_sha") != b:
        raise PinMismatch({"spec_sha": {"pin": pins.get("spec_sha"), "actual": a}, "code_sha": {"pin": pins.get("code_sha"), "actual": b}})


def ts(spec: dict, key: str) -> float:
    return datetime.fromisoformat(str(spec[key]).replace("Z", "+00:00")).timestamp()


def grid0(spec: dict) -> float:
    return ts(spec, "grid0_utc")


def slot_of(spec: dict, t: float) -> tuple[int, bool]:
    s = int(round((t - grid0(spec)) / spec["grid_s"]))
    return s, abs(t - (grid0(spec) + s * spec["grid_s"])) <= spec["tol_s"]


def slot_time(spec: dict, s: int) -> float:
    return grid0(spec) + s * spec["grid_s"]


def slots_between(spec: dict, a: float, b: float) -> list[int]:
    """Grid slots whose grid time lies in [a, b)."""
    lo = math.ceil((a - grid0(spec)) / spec["grid_s"])
    hi = math.ceil((b - grid0(spec)) / spec["grid_s"])
    return list(range(lo, hi))


def window_slots(spec: dict) -> list[int]:
    """252 slots for the frozen 21-day window."""
    return slots_between(spec, ts(spec, "registered_utc"), ts(spec, "end_utc"))


def followup_slots(spec: dict) -> list[int]:
    """Grid slots from END_UTC up to (not including) READOUT_UTC: the follow-up recorder's span."""
    return slots_between(spec, ts(spec, "end_utc"), ts(spec, "readout_utc"))


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def dry_spec(registered_utc: float, end_utc: float) -> dict:
    """A dry-run spec: a short window derived from the newest captures. Its ``spec_sha`` differs from the real one by construction (it hashes its own JSON)."""
    import copy

    s = copy.deepcopy(SPEC)
    s["registered_utc"], s["end_utc"] = iso(registered_utc), iso(end_utc)
    s["readout_utc"] = iso(end_utc + 45 * 86400.0)
    s["measurement"] = "M2_CH264_DRYRUN"
    s["dry_run"] = True
    return s
