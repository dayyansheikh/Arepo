# ruff: noqa: E501
"""M3 (CH274, "the wait") spec constant block, pins and pin refusals. Clause numbers refer to ``docs/research_lab/MEASUREMENT_M3_CH274.md`` (DRAFT until the design-text freeze).

``SPEC`` holds the declared constants of the text (dates, grid, near-certainty state, cells, bootstrap, coarse thresholds, fetch rule). ``spec_sha``:

* the REAL spec after the design-text freeze (``design_sha256`` set): the sha256 of the frozen design text (section 2: "the sha256 of this file at the registration commit");
* a spec whose ``design_sha256`` is still ``None`` (the DRAFT state of this code) or a dry-run spec: the sha256 of its own canonical JSON. A real (non-dry) J1 pass REFUSES while
  ``design_sha256`` is ``None`` (``check_real_run``), so nothing registered can run on the draft.

The design text (once pinned), every pinned class-setting module (section 12.5, eight files) and the rule lexicon (3.5, five patterns) are pins: ``check_pins`` refuses unless all
match. ``code_sha`` hashes the M3 code files (``CODE_FILES``; J2, J3 and the analysis join the list when written, which is what the code-freeze check lists).
Research tooling only; no network here. This module imports no other M3 module at import time (``m3_j1`` imports it), so it can be hashed and checked on its own.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

ROLE = "prospective_measurement"
VERSION = "m3-code-v1"
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
REPO = HERE.parents[2]
DESIGN_PATH = REPO / "docs" / "research_lab" / "MEASUREMENT_M3_CH274.md"

# 12.5: eight files (E5 and the sports reader, S10, S1's tier_of, the outcome parser, the fee lines / S9). E6's empty forms are copied, not imported.
PINNED_MODULES = ("boundary_map_ch240.py", "cb17_census.py", "cb13_label.py", "live_tests8_base.py", "population_map_ch251.py", "census_map_ch269.py", "calibration.py", "costs.py")

SPEC: dict = {
    "measurement": "M3_CH274", "version": VERSION, "role": ROLE,
    # section 2.1 (252 slots; 10.1 (a) rewrites the dates to 42 days / 504 slots before the freeze, if it fires)
    "registered_utc": "2026-11-24T00:00:00Z", "end_utc": "2026-12-15T00:00:00Z", "readout_utc": "2027-01-29T00:00:00Z",
    "close_after_end_s": 7 * 3600, "analysis_after_readout_s": 7 * 86400 + 12 * 3600, "registration_lead_s": 24 * 3600,
    "grid0_utc": "2026-10-01T00:31:00Z", "grid_s": 7200.0, "tol_s": 1800.0, "missing_after_grid_s": 6 * 3600,
    "lookback_slots": 84,
    "rules_first_day": "20261020",
    # section 3.2 - 3.3
    "scope": "nonsports_excrypto", "price_dp": 6, "near_ask": 0.95, "near_mid": 0.90, "one_sided_bid": 0.95, "one_sided_ask": 0.05,
    "min_end_s": 86400.0, "min_age_s": 86400.0,
    "empty_forms": ["", "[]", "nan", "none"],
    # section 4
    "followup_p_tokens": ["proposed", "disputed", "resolved"], "a99_ask": 0.99, "a99_within_s": 30 * 86400.0, "early_h_max_s": 43 * 86400.0,
    "early_on_time_before_s": 2 * 3600.0, "early_on_time_after_s": 24 * 3600.0,
    "horizons_s": {"24h": 86400.0, "72h": 3 * 86400.0, "7d": 7 * 86400.0, "30d": 30 * 86400.0}, "headline_horizon_s": 7 * 86400.0,
    "hazard_slots": 12,
    # section 6
    "capital_rate": 0.05, "hours_per_year": 8760.0, "fee_policy": "conservative",
    # section 8 (cell lists are fixed by rule; S13 has three week cells for the 21-day window, six under 10.1 (a))
    "cells": {
        "S1": ["lt1k", "1k-10k", "10k-100k", "ge100k", "tier_na"],
        "S2": ["scheduled", "barrier", "both", "consensus", "other", "no_rules", "rules_unresolved", "rules_gap"],
        "S3": ["1", "0", "na"],
        "S4": ["[1 d, 3 d)", "[3 d, 14 d)", "[14 d, 43 d)", ">= 43 d"],
        "S6": ["standalone", "member_yes", "member_no"],
        "S7": ["YES", "NO"],
        "S8": ["1", "2-5", "6+"],
        "S9": ["economics", "culture", "weather", "other", "finance", "politics", "mentions", "tech", "geopolitics", "unknown"],
        "S10": ["fee_free", "fee_on", "unknown"],
        "S11": ["[0.95,0.96)", "[0.96,0.97)", "[0.97,0.98)", "[0.98,0.99)", "[0.99,1)"],
        "S12": ["0.001", "0.01", "other_or_missing"],
        "S13": ["days 1-7", "days 8-14", "days 15-21"],
    },
    "thin": {"units": 30, "events": 10},
    # section 7
    "bootstrap": {"B": 10000, "seed": 20261126, "ci": 0.95, "chunk": 250},
    "bound": {"strata": ["1", "2-3", "4-9", "10+"], "alpha": 0.05},
    # section 9.4, 10.4, 11
    "coverage_floor": 0.95,
    "fetch": {"batch": 50, "attempts": 3, "attempt_gap_s": 3600.0, "extra_passes_after_readout_s": [3 * 86400.0, 7 * 86400.0]},
    "coarse": {"min_units": 1000, "max_headline_ci_width_ps": 0.10, "min_classed_share": 0.5, "min_slot_coverage": 0.75, "min_followup_slot_coverage": 0.75, "max_nonfinal_share": 0.10},
    "void_sha_mismatch_share": 0.01,
    # 10.1: J0's decision rule (a) (the only effect of J0): median full-day units below this extends the window to 42 days
    "j0": {"rule_a_units_below": 48, "rule_b_projected_21_day_units_below": 1008, "fold_captures": 12, "full_day_captures": 12},
    # the pins. design_sha256 stays None until the design-text freeze commit (a real J1 pass refuses while it is None).
    "design_sha256": None,
    "pinned_module_sha256": {
        "boundary_map_ch240.py": "2bc9ff9edb97b76990579c90929e55f22cb4cfe9fdec852395bd07f7d3bea09a",
        "calibration.py": "567cdbe9eab0a8fa5fccdf4350e44cb2fea0104d445e62188e3e363fba12dda1",
        "cb13_label.py": "2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380",
        "cb17_census.py": "6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a",
        "census_map_ch269.py": "3939f8fd3a3caf44f22076894a1a90ba2fcb9da8714b2cc25c89e9256ed16176",
        "costs.py": "258856fc360fbe70ce7a062a3f156b66d9d71fd50de56bf3669935c4227f844d",
        "live_tests8_base.py": "4b26756d4d1934c4da9a0b2b26d4ff3f2ac72f199bbc55d4ae6365b8ebc394e0",
        "population_map_ch251.py": "82db7a75995f0b637b469f4abc421ad9be430fdf38f0a4bad7ed5e9e43a55140",
    },
    "rule_lexicon_sha256": "8363ec0b4157b240ea781485a6c22c6ce6d0d0e5d64d0022c2e505f27f86e9a8",
}

# Host dry run (10, 20 step 8): the state is padded with inert synthetic records to the size it will have at the end of the window (about 66 days of near-seen set, ever-seen
# set and rule ledger), so the 600 MB cap is measured at end-of-window size (M2 final SHOULD 3). Planning figures (assumptions, over-stated on purpose): the rule ledger as
# M2's (800,000 records over 250,000 markets: 26,651 records a day over about 30 days), an ever-seen set of 600,000 market ids, a near-seen set of 150,000. Synthetic ids are
# negative, no real market has one. The pad never touches a real market and is refused outside a dry-run spec.
DRYRUN_LEDGER_PAD = (800_000, 250_000)
DRYRUN_SET_PAD = (600_000, 150_000)  # (ever_seen, near_seen)

CODE_FILES = (HERE / "m3_spec.py", HERE / "m3_j1.py", BACKEND / "scripts" / "run_m3.py")


class M3Refusal(RuntimeError):
    """A declared refusal (overwrite, order, state chain, date gate, pin, blinding)."""


class PinMismatch(RuntimeError):
    """A pinned module, the design text, the lexicon, the spec_sha or the code_sha differs from its pin; ``.record`` holds expected and actual."""

    def __init__(self, record: dict) -> None:
        super().__init__("M3 pin mismatch: " + json.dumps(record, sort_keys=True))
        self.record = record


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canonical(spec: dict) -> bytes:
    return json.dumps(spec, sort_keys=True, separators=(",", ":")).encode()


def spec_sha(spec: dict = SPEC) -> str:
    """The frozen real spec: the design text's sha256 (section 2). A dry-run spec or a draft spec (no ``design_sha256`` yet): the sha256 of its own canonical JSON."""
    if spec.get("dry_run") or not spec.get("design_sha256"):
        return sha256_bytes(canonical(spec))
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
    from . import m3_j1  # lazy: m3_j1 imports this module

    paths = module_paths() if paths is None else paths
    design = DESIGN_PATH if design is None else Path(design)
    mods = {}
    for n in PINNED_MODULES:
        exp = spec["pinned_module_sha256"][n]
        p = Path(paths[n])
        act = sha256_file(p) if p.exists() else None
        mods[n] = {"expected": exp, "actual": act, "ok": act == exp}
    dact = sha256_file(design) if design.exists() else None
    dexp = spec.get("design_sha256")
    d = {"expected": dexp, "actual": dact, "frozen": dexp is not None, "ok": dexp is None or dact == dexp}
    lact = m3_j1.lexicon_sha256() if lexicon is None else lexicon
    lx = {"expected": spec["rule_lexicon_sha256"], "actual": lact, "ok": lact == spec["rule_lexicon_sha256"]}
    return {"modules": mods, "design": d, "lexicon": lx, "ok": d["ok"] and lx["ok"] and all(m["ok"] for m in mods.values())}


def check_pins(spec: dict = SPEC, paths: dict | None = None, design: Path | None = None, lexicon: str | None = None) -> dict:
    """Refuse (raise ``PinMismatch`` with every expected and actual value) unless the pinned design text (once frozen), the lexicon and every pinned module match."""
    rec = pin_record(spec, paths, design, lexicon)
    if not rec["ok"]:
        raise PinMismatch(rec)
    return rec


def check_real_run(spec: dict) -> None:
    """A real (non-dry) J1 pass needs the frozen design text: ``design_sha256`` must be pinned."""
    if not spec.get("dry_run") and not spec.get("design_sha256"):
        raise M3Refusal("refuses: the design text is not frozen (SPEC['design_sha256'] is None); a registered J1 pass needs the design-text freeze and the registration commit pins")


def check_run_pins(pins: dict | None, spec: dict = SPEC) -> None:
    """The running ``spec_sha`` and ``code_sha`` must equal the registered pins (every pass of every job)."""
    if pins is None:
        return
    a, b = spec_sha(spec), code_sha()
    if pins.get("spec_sha") != a or pins.get("code_sha") != b:
        raise PinMismatch({"spec_sha": {"pin": pins.get("spec_sha"), "actual": a}, "code_sha": {"pin": pins.get("code_sha"), "actual": b}})


def check_registration_lead(pins: dict | None, spec: dict) -> None:
    """12.6: the window may not start before the registration commit plus 24 h. Real runs only: ``pins`` must carry ``registration_commit_utc``."""
    if spec.get("dry_run"):
        return
    rc = (pins or {}).get("registration_commit_utc")
    t = ts_str(rc) if rc else math.nan
    if not math.isfinite(t):
        raise M3Refusal("refuses: the pins file lacks a parseable registration_commit_utc")
    if ts(spec, "registered_utc") - t < spec["registration_lead_s"]:
        raise M3Refusal("refuses: REGISTERED_UTC is less than 24 h after the registration commit (void 12.6; apply the slide rule of 2.1 first)")


def ts_str(v) -> float:
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return math.nan


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
    """252 slots for the 21-day window (504 under 10.1 (a))."""
    return slots_between(spec, ts(spec, "registered_utc"), ts(spec, "end_utc"))


def followup_slots(spec: dict) -> list[int]:
    """Grid slots from END_UTC up to (not including) READOUT_UTC: the follow-up recorder's span after the window."""
    return slots_between(spec, ts(spec, "end_utc"), ts(spec, "readout_utc"))


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def dry_spec(registered_utc: float, end_utc: float) -> dict:
    """A dry-run spec: a short window derived from the newest captures. Its ``spec_sha`` differs from the real one by construction (it hashes its own JSON)."""
    import copy

    s = copy.deepcopy(SPEC)
    s["registered_utc"], s["end_utc"] = iso(registered_utc), iso(end_utc)
    s["readout_utc"] = iso(end_utc + 45 * 86400.0)
    s["measurement"] = "M3_CH274_DRYRUN"
    s["dry_run"] = True
    return s
