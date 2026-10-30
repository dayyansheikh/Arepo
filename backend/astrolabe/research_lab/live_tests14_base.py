# ruff: noqa: E501
"""LT14 census building blocks (docs/research_lab/LIVE_TESTS_14.md, design text FROZEN at sha256 f047c000...; DRAFT until registered). Research tooling only; never trades; makes no
network request.

Scope (section 3 and the census refusals / prints ONLY): the pinned model P, its input-clock audit (1.3), the declared constants in one hashed block, the refusals, the engine-store
readers (write-once files, read-only), the candidate set and its seven ordered exclusions (1.5), the |s| decile cut, tiers, outcome classes at k + 1 from ``st`` / ``t_off`` ONLY (1.6),
the fee-class split SUMMED across captures, and LT13's pivoted-QR aliasing rule (vendored) for M6's control design. NOTHING of the size check, the placebo, F, the analysis or the reader
is here, and no ``g`` is ever formed: the census reads no bid, ask or mid at k + 1 or later (:class:`EngineReader` raises :class:`Refused`).

Reuse: LT12 / LT13 / CB helpers are IMPORTED read-only and pinned by normalised sha256 (``DECLARED["imported_sha256"]``); every seal and census refuses if one differs. No E026 frozen file is
imported, copied or edited (``costs.py`` is not used by the census; M3's vendored formulas are analysis code). No signal-engine module is imported: the engine's stores are read as plain
parquet / json / jsonl files.
"""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import math
import os
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from . import bounce_decomp as bd
from . import cb13_label as lab
from . import cb17_census as c17
from . import forecast
from . import live_tests12_base as b
from . import population_map_ch251 as pm251

VERSION = "live-tests14-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
ENGINE_ROOT = ROOT / "data-dumps" / "research_lab" / "signal_engine"
SPEC_DIR = ROOT / "backend" / "astrolabe" / "signal_engine" / "specs"
CENSUS_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests14_census"
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_14.md"
LEDGER_PATH = ROOT / "docs" / "research_lab" / "EXPERIMENT_LEDGER.md"
SEALS = ROOT / "docs" / "research_lab" / "seals"
DESIGN_TEXT_SHA256 = "f047c00059ebffd0fe81dd76b6615969d0a127c593aacee0291971fd0e52f815"  # the design-text freeze (ledger "LT14 DESIGN TEXT FROZEN", commit 485c63dd)
LEDGER_FREEZE_MARKER = "LT14 DESIGN TEXT FROZEN"
LEDGER_P_MARKER = "Pinned `P`"
PINNED_MODEL = "se0_champion_lr_mm"
PINNED_SPEC_SHA256 = "19549cb403b41de6974a8f3e7acf7378baf433779b16cae46d367fe6fb5ff919"
TEMPFAIL = 75
TESTS = ("CH262",)
CENSUS_UNAVAILABLE = "census_unavailable (coverage)"
CENSUS_DROPPED = "census_dropped"
CENSUS_PASS = "census_pass"
WITHDRAWN_CLOCK = "withdrawn_pre_census (input clock)"
FORBIDDEN_BLOCKS = ("gross", "gbar", "target", "k+1", "outcome", "placebo", "twin", "lt11", "lt12", "lt13", "m1", "m2", "ch263", "ch264", "mid_next", "g ")
TIER_NAMES = ("lt1k", "1k-10k", "10k-100k", "ge100k")
PRIMARY_TIER = 2
LATER_SLOT_COLUMNS = frozenset({"market_id", "t_off", "st"})  # the ONLY columns of a quotes file at k + 1..k + 3 (3, "reads no later bid, ask or mid")
CLASSES = ("labelled", "unavailable_one_sided", "unavailable_closed", "unavailable_inactive", "unavailable_absent", "unavailable_missing_capture", "unavailable_timing", "unavailable_spec")
ST_CLASS = {3: "unavailable_one_sided", 1: "unavailable_closed", 2: "unavailable_inactive"}  # quotes ``st`` (0 open two-sided)

# --- the declaration: every constant of the census in ONE block, hashed into the seal and the census output (3, 1.5, 1.6, 9.1) ---------------------------------------------

DECLARED: dict = {
    "pinned_model": {"model_id": PINNED_MODEL, "spec_sha256": PINNED_SPEC_SHA256, "features_version": "se-features-v1",
                     "audit": {"pass_families": ["market_state", "momentum"], "pass_derived": ["base"],
                               "fail_families": {"book": "sweep received about 7 min after the origin (DESIGN_V1 3, 21)", "flow": "trade sample fetched after the capture (designer reading; the audit rules)",
                                                 "wallet": "trade sample fetched after the capture (designer reading; the audit rules)"},
                               "unaudited_families": ["xvenue", "book0"],
                               "rule": "1.3: every family and derived set of P's spec must be in pass_families / pass_derived, isolates and require_sources empty; anything else (including xvenue / book0, audited on code at the freeze only for P = se0) -> P refused -> withdrawn_pre_census (input clock)"}},
    "grid": {"grid0_utc": "2026-10-01T00:31:00Z", "grid_s": 7200, "slot_tol_s": 1800},
    "columns": {"pred": ["elig", "dir_2h_dn", "dir_2h_up"], "pred_types": {"elig": "uint8", "dir_2h_dn": "uint16", "dir_2h_up": "uint16"},
                "quotes": ["market_id", "t_off", "bid", "ask", "st"], "quotes_types": {"bid": "float", "ask": "float"},
                "features": ["market_id", "event_id", "category", "t_row", "end_ts", "ms_mid", "ms_spread", "ms_log_liq", "ms_hours_to_end", "ms_rv24", "ms_tick", "ms_neg_risk", "mo_d2h"],
                "sidecar": ["market_id", "fee_type", "fee_category", "series_slugs", "fee_schedule", "fees_enabled"],
                "log_fields": ["capture_id", "model_id", "written_utc", "spec_sha256", "fit_id", "sha256"], "elig_bit_dir_2h": 1, "Q": 65535},
    "scope": {"name": "non_sports_ex_crypto", "sports": "cb17_census.is_sports_sidecar(fee_type, fee_category, series_slugs) on the capture's own sidecar row (post-fee-step values)",
              "crypto": "live_tests12_base.crypto_class(fee_category, sidecar_present=True, sports); only non_crypto stays (unknown counts as crypto)"},
    "exclusion_order": ["pred_file_absent_late_or_spec_mismatch", "not_dir2h_eligible", "duplicate_market", "sidecar_missing", "scope", "tier_na", "s_zero"],
    "decile": {"denominator": 10, "order": "|dir_2h_up - dir_2h_dn| (stored uint16 difference, integer) descending, ties market_id ascending, stable", "middle_deciles_positions": [3, 6],
               "family_exclusion_share": 0.40},
    "tiers": {"cuts_usd": [1000, 10000, 100000], "names": list(TIER_NAMES), "rule": "expm1(ms_log_liq as stored, float32 -> float64); lower edge inclusive"},
    "spread": "spread_k = ask_k - bid_k from quotes/<k> (float32 -> float64); ms_spread is not used",
    "horizon": {"h_s": 7200.0, "tol_s": 900.0, "rule": "start(k + 1) + t_off(k + 1) - t_row(k) in 2 h +/- 15 min, else unavailable_timing"},
    "mid_check": {"tol": 1e-6, "rule": "|(bid_k + ask_k) / 2 - ms_mid| <= 1e-6 on 100% of units (float32 storage); NaN fails"},
    "hurdle_formula": {"AS_c": 2.04, "rebates_c": 0.10, "h_from_mean_spread_c": 2.68, "H_c": 1.30, "tier_p50_half_spread_c": 0.75, "tier_spread_figure_c": 2.48,
                       "rule": "H = 2 x (AS - h) - rebates; the census recomputes h from its recorded touches (mean spread_k / 2; p50 spread_k / 2) and PRINTS both; they never replace H"},
    "mde": {"t_sum": 3.47, "day_factor": 1.5, "n_eff_frac": 0.8, "de_rho": 0.02, "de_floor": 5.0, "planning_r": 0.2, "sd_floor_c": 1.3, "mde_max_c": 0.5, "f_mde_max_c": 0.5, "g_eff_min": 15, "projection_days": 21.0,
            "rule": "DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02); MDE = 3.47 x 1.5 x SD_plan x sqrt(DE_gate / (0.8 n)); F-MDE = MDE x sqrt(2 / (1 - max(0, 0.2))); design MDE = 3.47 x 1.5 x max(se_event, se_twoway, se_day); the gate uses max(declared, design); design-effect cluster sizes are the census's UNSCALED unit counts per event, per event x UTC day and per UTC day (labelled units), n = projected labelled units; the 21 / covered-days scaled cluster sizes are print only"},
    "census_inputs": {
        "span": {"start_utc": "2026-11-07T00:00:00Z", "end_utc": "2026-11-17T00:00:00Z", "first_slot_utc": "2026-11-07T00:31:00Z", "last_slot_utc": "2026-11-16T22:31:00Z"},
        "lag_slots_after": 3, "lookback_capture_slots": 0, "tail_slots_utc": ["2026-11-17T00:31:00Z", "2026-11-17T02:31:00Z", "2026-11-17T04:31:00Z"],
        "expected_origins": 120, "min_covered_days": 7.0, "p_ontime_min": 0.90, "refuse_at_or_after_utc": "2026-11-17T06:00:00Z", "seal_not_before_utc": "2026-11-17T05:01:00Z",
        "rss_refuse_mb": 800.0, "rss_plan_mb": 500.0},
    "census_gates": {
        "units_median_min": 100, "units_projected_min": 25200, "nonstationarity_min": 0.25, "venue_clock_max": 0.5, "events_min": 300, "g_eff_min": 15, "unavailable_gap_max_points": 10.0,
        "tier_finite_min": 0.95, "mid_check_share_min": 1.0, "mde_max_c": 0.5, "f_mde_max_c": 0.5, "arm_ge100k_print": {"median_min": 10, "markets_min": 40}},
    "m6": {"controls": ["spread_c", "log1p_liq", "absmid", "log1p_hte", "hte_unknown", "zlog_rv", "rv_missing", "mo_d2h", *[f"sd{i}" for i in range(1, 12)]],
           "left_out": ["category", "ms_neg_risk", "ms_tick"], "slot_dummy_reference_slot_of_day": 0,
           "drop_order": ["sd11..sd1 (latest slot first)", "hte_unknown", "rv_missing", "log1p_hte", "absmid"], "stratum": "market x UTC day", "demean": "expanding-past (bounce_decomp.expanding_demean)",
           "rank": "column-pivoted QR, tolerance max(n, p) x eps x sigma_max; D never dropped; no pseudo-inverse"},
    "classes": list(CLASSES),
    "imported_sha256": {  # normalised sha256 (SPEC_SHA256 line excluded) of the files whose helpers LT14 imports; a seal or census refuses on any difference
        "live_tests12_base.py": "6f2212f2f5243ea656c179ae3b1a35646c9db4815e006e95bf2c9117cf19f75c", "population_map_ch251.py": "82db7a75995f0b637b469f4abc421ad9be430fdf38f0a4bad7ed5e9e43a55140",
        "cb17_census.py": "6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a", "cb13_label.py": "2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380",
        "bounce_decomp.py": "2caf0edc73fbac5b27054589afa495a2cf6844886e41a2f8eced5d9796a34c8a"},
    "seeds": {"size_check": 20261814, "rule": "declared for the later stage; the census draws nothing (no random number)"},
}
IMPORTED_FILES = tuple(DECLARED["imported_sha256"])
CODE_FILES = ("live_tests14.py", "live_tests14_base.py", "run_live_tests14.py")  # the runner lives in backend/scripts (code_hashes resolves it)
ALLOW_NONDECLARED_SPEC = False  # True only in tests: a seal / census run on a spec other than DECLARED would record hashes of parameters it did not use (code-freeze check SHOULD 1)
_PIN_LINE = re.compile(r"^SPEC_SHA256 = .*$", re.M)


class Refused(RuntimeError):
    """A pin, seal, scope or causality check failed: nothing is computed or written."""


def _canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def file_sha(path: Path) -> str:
    """Normalised sha256 of a code file (the ``SPEC_SHA256 = ...`` line excluded, LT3 9.3's rule; vendored from ``live_tests12.code_sha256``)."""
    txt = Path(path).read_bytes().decode("utf-8")
    return hashlib.sha256(_PIN_LINE.sub("SPEC_SHA256 = <pin>", txt).encode("utf-8")).hexdigest()


def imported_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: file_sha(here / n) for n in IMPORTED_FILES}


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    scripts = here.parents[1] / "scripts"
    return {n: (file_sha(p) if (p := (scripts / n if n.startswith("run_") else here / n)).exists() else None) for n in CODE_FILES}


def declaration_sha256() -> str:
    return hashlib.sha256(_canon(DECLARED).encode("utf-8")).hexdigest()


def load_spec() -> dict:
    return copy.deepcopy(DECLARED)


def spec_hash(spec: dict) -> str:
    return hashlib.sha256(_canon(spec).encode("utf-8")).hexdigest()


def spec_error(spec: dict) -> dict | None:
    """SHOULD 1: the hashes written into the seal and the output describe DECLARED; a run on any other spec is refused (tests set ``ALLOW_NONDECLARED_SPEC``)."""
    if not ALLOW_NONDECLARED_SPEC and _canon(spec) != _canon(DECLARED):
        return {"error": "the spec in use differs from DECLARED: the recorded declaration_sha256 would describe parameters that were not used; refused"}
    return None


def imported_error() -> dict | None:
    got, want = imported_hashes(), DECLARED["imported_sha256"]
    bad = {k_: {"got": got[k_], "declared": want.get(k_)} for k_ in got if got[k_] != want.get(k_)}
    return {"error": "an imported helper file differs from its declared sha256 (helpers are pinned by hash): refused", "files": bad} if bad else None


# --- refusals (3, "Refusals") -----------------------------------------------------------------------------------------------------------------------


def design_text_error(path: Path | None = None, ledger: Path | None = None) -> dict | None:
    """Refuse unless LIVE_TESTS_14.md hashes to the frozen constant AND the ledger has a ``LT14 DESIGN TEXT FROZEN`` line carrying that sha256 AND a ``Pinned `P``` line carrying P's
    model id and spec_sha256 (3: "a seal whose design-text sha is not the ledger's")."""
    p = Path(path or DESIGN_PATH)
    got = b.sha256_file(p)
    if got != DESIGN_TEXT_SHA256:
        return {"error": "LIVE_TESTS_14.md differs from the text-frozen file (sha256 != the ledger's freeze hash): refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}
    led = Path(ledger or LEDGER_PATH)
    if not led.exists():
        return {"error": f"ledger {led} not found: the freeze hash cannot be checked against it: refused"}
    lines = led.read_text().splitlines()
    if not [ln for ln in lines if LEDGER_FREEZE_MARKER in ln and DESIGN_TEXT_SHA256 in ln]:
        return {"error": f"the ledger has no '{LEDGER_FREEZE_MARKER}' line carrying {DESIGN_TEXT_SHA256}: refused", "ledger": str(led)}
    if not [ln for ln in lines if LEDGER_P_MARKER in ln and PINNED_MODEL in ln and PINNED_SPEC_SHA256 in ln]:
        return {"error": f"the ledger has no '{LEDGER_P_MARKER}' line carrying {PINNED_MODEL} and {PINNED_SPEC_SHA256}: refused", "ledger": str(led)}
    return None


def check_blocks(requested) -> None:
    """Refuse to compute any ``g`` / gross / k + 1 target, any placebo / twin, or any LT11-LT13 or M1 / M2 object (3)."""
    for r in requested:
        low = str(r).lower()
        if any(f in low for f in FORBIDDEN_BLOCKS):
            raise Refused(f"the LT14 census refuses to compute {r!r}: no g, no later-slot price, no LT11-LT13 or M1 / M2 object (3)")
    unknown = [r for r in requested if r not in TESTS]
    if unknown:
        raise Refused(f"unknown census block(s) {unknown}")


def _spec_canonical_sha(spec: dict) -> str:
    """The engine's ``specs.spec_sha256`` re-implemented (sha256 of the canonical JSON of the spec without ``_`` keys; sorted keys, compact separators)."""
    d = {k_: v for k_, v in spec.items() if not str(k_).startswith("_")}
    return hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def audit_input_clock(spec_dir: Path | None = None, declared: dict | None = None) -> dict:
    """1.3, the input-clock audit RE-RUN at the start of every seal and census. Reads ``registry.json`` and ``<P>.json`` (file names only; no value). Passes iff: P is in the registry with
    the pinned ``spec_sha256``; the spec file's canonical sha256 equals it; ``features_version`` is the pinned one; the spec's families are inside ``pass_families`` and its derived sets inside
    ``pass_derived``; ``isolates`` and ``train.require_sources`` are empty. Any other family is a failure (xvenue / book0 are 'audited on their code' at the freeze, for P = se0 only; flow,
    wallet and book fail by construction / by the designer's reading). Never re-pins to another model."""
    d = declared or DECLARED["pinned_model"]
    sd = Path(spec_dir or SPEC_DIR)
    out = {"model_id": d["model_id"], "spec_sha256": d["spec_sha256"], "pass": False, "reasons": []}
    try:
        reg = json.loads((sd / "registry.json").read_text())
        ent = next((m for m in reg["models"] if m["model_id"] == d["model_id"]), None)
        out["registry_sha256"] = b.sha256_file(sd / "registry.json")
    except (OSError, ValueError, KeyError) as e:
        out["reasons"].append(f"registry unreadable: {e}")
        return out
    if ent is None:
        out["reasons"].append("P is not in the registry")
        return out
    out["registry_entry"] = {k_: ent.get(k_) for k_ in ("model_id", "spec_sha256", "status", "added_utc")}
    if ent.get("spec_sha256") != d["spec_sha256"]:
        out["reasons"].append("registry spec_sha256 differs from the pin")
    try:
        sp = json.loads((sd / ent["file"]).read_text())
    except (OSError, ValueError, KeyError) as e:
        out["reasons"].append(f"spec file unreadable: {e}")
        return out
    out["spec_canonical_sha256"] = _spec_canonical_sha(sp)
    if _spec_canonical_sha(sp) != d["spec_sha256"]:
        out["reasons"].append("the spec file's canonical sha256 differs from the pin")
    if sp.get("features_version") != d["features_version"]:
        out["reasons"].append("FEATURES_VERSION differs from the pin")
    au = d["audit"]
    fam = list(sp.get("families") or [])
    out["families"], out["derived"] = fam, list(sp.get("derived") or [])
    for f_ in fam:
        if f_ in au["fail_families"]:
            out["reasons"].append(f"family {f_}: {au['fail_families'][f_]}")
        elif f_ not in au["pass_families"]:
            out["reasons"].append(f"family {f_} is not audited as received at or before t_row(i) ({'xvenue / book0 are audited on code' if f_ in au['unaudited_families'] else 'unknown'}): refused")
    for dv in sp.get("derived") or []:
        if dv not in au["pass_derived"]:
            out["reasons"].append(f"derived set {dv} is not audited: refused")
    if sp.get("isolates"):
        out["reasons"].append(f"spec isolates {sp.get('isolates')}: refused")
    if (sp.get("train") or {}).get("require_sources"):
        out["reasons"].append(f"spec requires sources {sp['train']['require_sources']}: refused")
    out["pass"] = not out["reasons"]
    return out


# --- columns / schema (headers only; 6 job 1) -------------------------------------------------------------------------------------------------------


def schema_problems(path: Path, want: list[str], types: dict | None = None) -> list[str]:
    """Column names and types of a parquet file from its schema ONLY (no value is read)."""
    sch = pq.read_schema(path)
    names = set(sch.names)
    bad = [f"missing column {c}" for c in want if c not in names]
    for c, t_ in (types or {}).items():
        if c in names and not str(sch.field(c).type).startswith(t_):
            bad.append(f"column {c} is {sch.field(c).type}, declared {t_}")
    return bad


def read_cols(path: Path, columns: list[str]) -> pd.DataFrame:
    return pq.read_table(path, columns=columns).to_pandas()


def parquet_meta(path: Path) -> dict:
    md = pq.read_schema(path).metadata or {}
    raw = md.get(b"signal_engine")
    return json.loads(raw) if raw else {}


def slot_of(t: float) -> int | None:
    return b.slot_of(t, DECLARED)


def slot_time(k: int) -> float:
    return b.slot_time(k, DECLARED)


def span_slots(spec: dict | None = None) -> list[int]:
    ci = (spec or DECLARED)["census_inputs"]["span"]
    return list(range(slot_of(b.epoch(ci["first_slot_utc"])), slot_of(b.epoch(ci["last_slot_utc"])) + 1))


def tail_slots(spec: dict | None = None) -> list[int]:
    last = span_slots(spec)[-1]
    return [last + i for i in range(1, int((spec or DECLARED)["census_inputs"]["lag_slots_after"]) + 1)]


# --- the engine's stores, read-only, with the later-slot guard ---------------------------------------------------------------------------------------


class EngineReader:
    """Read-only access to ``<engine>/{meta,quotes,features,predictions}`` by capture id and to the sidecar under the snapshot roots. ``quotes(origin, slot, cols)`` is the ONLY quotes
    reader: for ``slot > origin`` it refuses any column outside ``market_id`` / ``t_off`` / ``st`` (3: the census reads no later bid, ask or mid)."""

    def __init__(self, engine_root: Path, snapshot_roots, slots: dict[int, str], allowed: set | None = None, absent: set | None = None) -> None:
        self.allowed = allowed  # the seal's file names; a read of any other file is refused (3: "an input not in the seal")
        self.absent = set(absent or ())  # files the seal recorded as ABSENT at seal time: never opened, read as missing (MUST 2), whatever is on disk now
        self.root = Path(engine_root)
        self.snaps = [Path(r) for r in (snapshot_roots if isinstance(snapshot_roots, (list, tuple)) else [snapshot_roots])]
        self.slots = slots

    def cap(self, k: int) -> str | None:
        return self.slots.get(int(k))

    def _chk(self, rel: str) -> bool:
        """True if ``rel`` may be read; False if the seal recorded it as absent; raises if it is in neither list."""
        if rel in self.absent:
            return False
        if self.allowed is not None and rel not in self.allowed:
            raise Refused(f"{rel} is not in the seal: refused (3)")
        return True

    def meta(self, k: int) -> dict | None:
        c = self.cap(k)
        p = self.root / "meta" / f"{c}.json" if c else None
        if p and not self._chk(f"meta/{c}.json"):
            return None
        return json.loads(p.read_text()) if p and p.exists() else None

    def quotes(self, origin: int, slot: int, columns: list[str]) -> pd.DataFrame | None:
        if slot > origin and not set(columns) <= LATER_SLOT_COLUMNS:
            raise Refused(f"a later-slot quotes read of columns {sorted(set(columns) - LATER_SLOT_COLUMNS)} (slot {slot} > origin {origin}) is refused: the census reads st / t_off only (3)")
        c = self.cap(slot)
        p = self.root / "quotes" / f"{c}.parquet" if c else None
        if p and not self._chk(f"quotes/{c}.parquet"):
            return None
        return read_cols(p, columns) if p and p.exists() else None

    def features(self, k: int, columns: list[str]) -> pd.DataFrame | None:
        c = self.cap(k)
        p = self.root / "features" / f"{c}.parquet" if c else None
        if p and not self._chk(f"features/{c}.parquet"):
            return None
        return read_cols(p, columns) if p and p.exists() else None

    def pred_path(self, k: int, model_id: str) -> Path | None:
        c = self.cap(k)
        if c:
            self._chk(f"predictions/{c}/{model_id}.parquet")
        return self.root / "predictions" / c / f"{model_id}.parquet" if c else None

    def sidecar_path(self, k: int) -> Path | None:
        c = self.cap(k)
        for r in self.snaps:
            p = r / c / "rows_ext.csv.gz" if c else None
            if p and p.exists():
                if not self._chk(f"snapshots/{c}/rows_ext.csv.gz"):
                    return None
                return p
        return None


def load_sidecar(path: Path | None) -> pd.DataFrame | None:
    """The scope / fee fields by integer ``market_id`` (first row wins); ``attrs['has_fees_enabled']`` from the header (a sidecar WITHOUT the column says nothing about the fee class)."""
    if path is None or not Path(path).exists():
        return None
    want = set(DECLARED["columns"]["sidecar"])
    hdr = list(pd.read_csv(path, nrows=0).columns)
    ext = pd.read_csv(path, usecols=lambda c: c in want, dtype=str)
    for c in want:
        if c not in ext:
            ext[c] = None
    ext["market_id"] = pd.to_numeric(ext["market_id"], errors="coerce")
    ext = ext.dropna(subset=["market_id"]).astype({"market_id": np.int64}).drop_duplicates("market_id").set_index("market_id")
    ext.attrs["has_fees_enabled"] = "fees_enabled" in hdr
    return ext


def _s(v) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


# --- tiers, the candidate set and the decile cut (1.5) -----------------------------------------------------------------------------------------------


def tier_codes(log_liq) -> np.ndarray:
    """Tier 0..3 on ``expm1(ms_log_liq)`` (stored float32 -> float64), -1 where non-finite (``tier_na``)."""
    liq = np.expm1(np.asarray(log_liq, dtype=np.float64))
    t = np.digitize(liq, DECLARED["tiers"]["cuts_usd"], right=False).astype(np.int8)
    return np.where(np.isfinite(liq), t, np.int8(-1))


def scope_classes(ext: pd.DataFrame, ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(sports bool, crypto class str) per market id from the sidecar row at k (sidecar rows exist: step 4 ran first)."""
    e = ext.reindex(ids)
    ft, fc, ss = (e[c].tolist() for c in ("fee_type", "fee_category", "series_slugs"))
    sports = np.array([bool(c17.is_sports_sidecar(_s(a), _s(b_), _s(c))) for a, b_, c in zip(ft, fc, ss, strict=True)], bool)
    cls = np.array([b.crypto_class(_s(f) or None, True, int(sp)) for f, sp in zip(fc, sports, strict=True)], dtype=object)
    return sports, cls


def candidates(feat: pd.DataFrame, pred: pd.DataFrame, quo: pd.DataFrame | None, ext: pd.DataFrame | None, scope: str | None = None) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """1.5: the candidate set C_k after exclusions 2-7 in order (step 1, P's file, is the caller's), each counted. ``feat`` and ``pred`` are row-aligned (same order); ``scope`` is the
    parameter (``non_sports_ex_crypto`` at the freeze; ``sports`` and ``crypto`` for the arms). Returns (C, steps, pre_scope) where ``pre_scope`` holds the rows entering step 5 with their
    tier, engine category and pinned classifier label (the confusion table)."""
    scope = scope or DECLARED["scope"]["name"]
    df = feat.reset_index(drop=True).copy()
    df["elig"] = pred["elig"].to_numpy().astype(np.int64)
    df["dn"], df["up"] = pred["dir_2h_dn"].to_numpy().astype(np.int64), pred["dir_2h_up"].to_numpy().astype(np.int64)
    steps: dict[str, int] = {"rows": int(len(df))}
    keep = (df["elig"].to_numpy() & DECLARED["columns"]["elig_bit_dir_2h"]) > 0
    steps["not_dir2h_eligible"] = int((~keep).sum())
    df = df[keep]
    dup = df["market_id"].duplicated(keep="first").to_numpy()
    steps["duplicate_market"] = int(dup.sum())
    df = df[~dup]
    present = df["market_id"].isin(ext.index).to_numpy() if ext is not None else np.zeros(len(df), bool)
    steps["sidecar_missing"] = int((~present).sum())
    df = df[present].copy()
    ids = df["market_id"].to_numpy(np.int64)
    if ext is not None and len(df):
        sports, cclass = scope_classes(ext, ids)
    else:
        sports, cclass = np.zeros(0, bool), np.zeros(0, dtype=object)
    tier = tier_codes(df["ms_log_liq"].to_numpy())
    lab_ = np.where(sports, "sports", cclass)
    pre = pd.DataFrame({"tier": [TIER_NAMES[t] if t >= 0 else "tier_na" for t in tier], "category": df["category"].astype(str).to_numpy(), "label": lab_})
    if scope == "non_sports_ex_crypto":
        in_scope = ~sports & (cclass == "non_crypto")
        steps["scope_sports"] = int(sports.sum())
        steps["scope_crypto_or_unknown"] = int((~sports & (cclass != "non_crypto")).sum())
    elif scope == "sports":
        in_scope = sports
        steps["scope_out"] = int((~in_scope).sum())
    elif scope == "crypto":
        in_scope = ~sports & (cclass != "non_crypto")
        steps["scope_out"] = int((~in_scope).sum())
    else:
        raise Refused(f"unknown scope {scope!r}")
    df, sports, cclass, tier = df[in_scope].copy(), sports[in_scope], cclass[in_scope], tier[in_scope]
    steps["in_scope"] = int(len(df))
    steps["tier_na"] = int((tier < 0).sum())
    ok = tier >= 0
    df, sports, cclass, tier = df[ok].copy(), sports[ok], cclass[ok], tier[ok]
    df["tier"] = tier
    df["s_int"] = df["up"].to_numpy() - df["dn"].to_numpy()
    z = df["s_int"].to_numpy() == 0
    steps["s_zero"] = int(z.sum())
    df = df[~z].copy()
    steps["candidates"] = int(len(df))
    # origin-side quote fields (quotes/<k> as written; spread_k = ask - bid) and the fee class (served rate, sidecar of the same capture)
    if quo is not None and len(df):
        # the kept features row is the FIRST row of its market among the engine's two-sided rows (features are a subset of quotes with st = 0): take the first quotes row with st = 0 (SHOULD 7)
        qs = quo[quo["st"] == 0] if "st" in quo else quo
        q = qs.drop_duplicates("market_id").set_index("market_id").reindex(df["market_id"].to_numpy())
        df["bid_k"], df["ask_k"] = q["bid"].to_numpy(np.float64), q["ask"].to_numpy(np.float64)
        df["t_off_k"] = q["t_off"].to_numpy(np.float64)
    else:
        df["bid_k"] = df["ask_k"] = df["t_off_k"] = np.nan
    df["mid_k"] = (df["bid_k"] + df["ask_k"]) / 2.0
    df["spread_c"] = 100.0 * (df["ask_k"] - df["bid_k"])
    if ext is not None and len(df):
        e = ext.reindex(df["market_id"].to_numpy())
        has_fe = bool(ext.attrs.get("has_fees_enabled", True))
        df["fee_class"] = [pm251.fee_class(_s(f), has_fe, _s(s_))[0] for f, s_ in zip(e["fees_enabled"].tolist(), e["fee_schedule"].tolist(), strict=True)]
        df["slug1"] = [lab.first_series_slug(s_) for s_ in e["series_slugs"].tolist()]
    else:
        df["fee_class"], df["slug1"] = "unknown", ""
    df["fam"] = [s_.strip().casefold() or f"none:{m}" for s_, m in zip(df["slug1"].tolist(), df["market_id"].tolist(), strict=True)]
    df["ekey"] = np.where(df["event_id"].to_numpy() >= 0, df["event_id"].astype(np.int64).astype(str), "m" + df["market_id"].astype(str))
    return df.reset_index(drop=True), steps, pre


def decile_positions(C: pd.DataFrame, signed: bool = False) -> np.ndarray:
    """1.5: positions (into ``C``) sorted by ``|s|`` descending (the integer |up - dn|), ties ``market_id`` ascending (np.lexsort is stable). ``signed`` orders by s descending (the map's object)."""
    s = C["s_int"].to_numpy(np.int64)
    key = -s if signed else -np.abs(s)
    return np.lexsort((C["market_id"].to_numpy(np.int64), key))


def top_count(n: int) -> int:
    return int(math.ceil(n / float(DECLARED["decile"]["denominator"])))


def deciles(C: pd.DataFrame, signed: bool = False) -> dict:
    """{top: positions of the first ceil(n / 10); middle: positions [3 x nt, 6 x nt) (deciles 4-6, M6); rest: the others}."""
    order = decile_positions(C, signed)
    nt = top_count(len(C))
    lo, hi = DECLARED["decile"]["middle_deciles_positions"]
    return {"top": order[:nt], "middle": order[lo * nt: hi * nt], "rest": order[nt:], "n_top": nt}


def classify_next(ids: np.ndarray, t_row_k: np.ndarray, nxt: pd.DataFrame | None, start_next: float | None) -> np.ndarray:
    """1.6: the outcome class at k + 1 from the quotes file's ``st`` and ``t_off`` ONLY (the horizon rule uses ``start(k + 1) + t_off(k + 1) - t_row(k)``). ``nxt`` None is a missing
    capture. A price is never read here (the frame carries no bid / ask column: :class:`EngineReader` refuses them)."""
    n = len(ids)
    if nxt is None or start_next is None:
        return np.full(n, "unavailable_missing_capture", dtype=object)
    bad = set(nxt.columns) - LATER_SLOT_COLUMNS
    if bad:
        raise Refused(f"classify_next was given price columns {sorted(bad)}")
    q = nxt.drop_duplicates("market_id").set_index("market_id").reindex(ids)
    st = q["st"].to_numpy(np.float64)
    off = q["t_off"].to_numpy(np.float64)
    absent = np.isnan(st)
    dt = start_next + off - t_row_k
    tol = DECLARED["horizon"]["tol_s"]
    h_ok = np.abs(dt - DECLARED["horizon"]["h_s"]) <= tol
    out = np.full(n, "unavailable_timing", dtype=object)
    out[np.where(absent, False, st == 0) & h_ok] = "labelled"
    for code, name in ST_CLASS.items():
        out[np.where(absent, False, st == code)] = name
    out[absent] = "unavailable_absent"
    return out


# --- the fee-class split SUMMED across captures (3: the CH269 defect, R1 MUST 5) -----------------------------------------------------------------------


def fee_split(C: pd.DataFrame, positions: np.ndarray) -> Counter:
    """One capture's counts of tier x fee class among ``positions`` of C_k."""
    sub = C.iloc[positions]
    return Counter(f"{TIER_NAMES[t]}/{f}" for t, f in zip(sub["tier"].to_numpy(), sub["fee_class"].to_numpy(), strict=True))


def sum_fee_splits(per_capture: list[Counter]) -> dict[str, int]:
    """The total over captures. ``Counter.update`` ADDS; a dict comprehension over the captures (``{k: v for row in rows for k, v in row.items()}``) would keep only the LAST capture's value
    per key (census_map_ch269.py:951-952). A unit test feeds two captures and asserts the sum."""
    tot: Counter = Counter()
    for c in per_capture:
        tot.update(c)
    return dict(tot)


# --- LT13's pivoted-QR aliasing rule, vendored with LT14's drop order (1.11 M6) ---------------------------------------------------------------------------


def _qr_rank(R: np.ndarray, cols: list[int], n_rows: int) -> int:
    """Rank of the columns ``cols`` of A from its triangular factor ``R``: column-pivoted QR, tolerance ``max(n, p) x eps x the largest singular value`` (vendored from LT13)."""
    import scipy.linalg as sla

    if not cols:
        return 0
    M = R[:, cols]
    s = np.linalg.svd(M, compute_uv=False)
    tol = max(n_rows, M.shape[1]) * np.finfo(float).eps * (float(s[0]) if len(s) else 0.0)
    _, r2, _ = sla.qr(M, mode="economic", pivoting=True)
    return int((np.abs(np.diag(r2)) > tol).sum())


def drop_order14(columns: list[str]) -> list[str]:
    """1.11 M6: (1) slot-of-day dummies, latest slot first; (2) ``hte_unknown``, ``rv_missing``; (3) ``log1p_hte``; (4) ``absmid``. Nothing else is ever dropped, and never ``D``."""
    g1 = sorted((c for c in columns if re.fullmatch(r"sd\d+", c)), key=lambda c: int(c[2:]), reverse=True)
    return [*g1, *[c for c in ("hte_unknown", "rv_missing", "log1p_hte", "absmid") if c in columns]]


def resolve_aliased_controls14(D: pd.DataFrame, term: str, controls: list[str]) -> dict:
    """LT13's rule: on the demeaned control matrix WITHOUT ``term`` (rows with a non-finite value dropped), rank by column-pivoted QR; if below the column count, in the fixed order of
    :func:`drop_order14` drop a column only if it lies in the span of the OTHER RETAINED columns (removing it leaves the rank unchanged); never ``term``. Still rank-deficient, or ``term`` in
    the span of the retained controls: the fit is NaN (``status = "unavailable"``; no pseudo-inverse). Zero-variance demeaned columns are removed before the rank and reported (LT13's
    clause (b), vendored; ambiguity A3 in the code note). Returns kept / dropped columns (in order), rank, column count and status."""
    cols = [c for c in controls if c != term]
    d = D[[term, *cols]].replace([np.inf, -np.inf], np.nan).dropna()
    n = len(d)
    zero = [c for c in cols if n and float(d[c].std(ddof=0)) <= 0.0]
    cols = [c for c in cols if c not in zero]
    base = {"n": int(n), "zero_variance_dropped": zero, "dropped": [], "term_aliased": False}
    if n == 0 or not cols:
        return {**base, "keep": cols, "n_cols": len(cols), "rank": 0, "status": "unavailable" if n == 0 else "ok", "reason": "no rows" if n == 0 else None}
    A = d[cols].to_numpy(float)
    R = np.linalg.qr(A, mode="r") if n >= len(cols) else np.linalg.qr(np.vstack([A, np.zeros((len(cols) - n, len(cols)))]), mode="r")
    keep = list(range(len(cols)))
    rank = _qr_rank(R, keep, n)
    dropped: list[str] = []
    for c in drop_order14(cols):
        if rank >= len(keep):
            break
        j = cols.index(c)
        if j not in keep:
            continue
        rest = [x for x in keep if x != j]
        if _qr_rank(R, rest, n) == rank:
            keep, dropped = rest, [*dropped, c]
            rank = _qr_rank(R, keep, n)
    kept = [cols[j] for j in keep]
    res = {**base, "keep": kept, "dropped": dropped, "n_cols": len(kept), "n_cols_before": len(cols), "rank": rank}
    if rank < len(kept):
        return {**res, "status": "unavailable", "reason": "controls still rank-deficient after the drop groups"}
    Az = np.column_stack([d[kept].to_numpy(float), d[term].to_numpy(float)]) if kept else d[[term]].to_numpy(float)
    Rz = np.linalg.qr(Az, mode="r") if n >= Az.shape[1] else np.linalg.qr(np.vstack([Az, np.zeros((Az.shape[1] - n, Az.shape[1]))]), mode="r")
    if _qr_rank(Rz, list(range(Az.shape[1])), n) == rank:
        return {**res, "term_aliased": True, "status": "unavailable", "reason": f"{term} lies in the span of the retained controls"}
    return {**res, "status": "ok", "reason": None}


def m6_design(M: pd.DataFrame) -> pd.DataFrame:
    """The census design of M6 (no target): controls built from origin-side fields and demeaned by expanding-past market x UTC-day strata (bounce_decomp.expanding_demean; the first row of a
    stratum is NaN and drops). ``M`` carries ``D``, ``stratum``, ``t_row`` and the raw fields; the z of log ms_rv24 is over the design rows."""
    X = pd.DataFrame({"stratum": M["stratum"].to_numpy(), "t_row": M["t_row"].to_numpy(float), "D": M["D"].to_numpy(float)})
    X["spread_c"] = M["spread_c"].to_numpy(float)
    X["log1p_liq"] = np.log1p(np.clip(np.expm1(M["ms_log_liq"].to_numpy(np.float64)), 0, None))
    X["absmid"] = np.abs(M["ms_mid"].to_numpy(float) - 0.5)
    hte = M["ms_hours_to_end"].to_numpy(float)
    X["hte_unknown"] = (~np.isfinite(hte)).astype(float)
    X["log1p_hte"] = np.where(np.isfinite(hte), np.log1p(np.clip(hte, 0, None)), 0.0)
    rv = M["ms_rv24"].to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        lr = np.log(rv)
    okr = np.isfinite(lr)
    X["rv_missing"] = (~okr).astype(float)
    mu, sd = (float(np.mean(lr[okr])), float(np.std(lr[okr]))) if okr.any() else (0.0, 0.0)
    X["zlog_rv"] = np.where(okr, (lr - mu) / sd if sd > 0 else 0.0, 0.0)
    X["mo_d2h"] = M["mo_d2h"].to_numpy(float)
    sod = M["sod"].to_numpy(int)
    for i in range(1, 12):
        X[f"sd{i}"] = (sod == i).astype(float)
    cols = ["D", *DECLARED["m6"]["controls"]]
    return bd.expanding_demean(X, cols, "stratum", "t_row")[cols]


def vif_of(D: pd.DataFrame, term: str, keep: list[str]) -> float:
    """VIF of ``term`` on the retained controls (1 / (1 - R^2) from least squares on complete rows; inf if R^2 = 1; NaN if not computable)."""
    d = D[[term, *keep]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(d) < len(keep) + 2 or not keep:
        return math.nan
    y, X = d[term].to_numpy(float), d[keep].to_numpy(float)
    if float(np.var(y)) <= 0:
        return math.nan
    beta, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(d)), X]), y, rcond=None)
    res = y - np.column_stack([np.ones(len(d)), X]) @ beta
    r2 = 1.0 - float(res @ res) / float(((y - y.mean()) ** 2).sum())
    return math.inf if r2 >= 1.0 - 1e-12 else 1.0 / (1.0 - r2)


# --- statistics of the gates --------------------------------------------------------------------------------------------------------------------------


def dist(vals) -> dict:
    a = np.asarray(list(vals), dtype=float)
    if not len(a):
        return {"n": 0, "min": None, "p25": None, "median": None, "mean": None, "max": None}
    return {"n": int(len(a)), "min": float(a.min()), "p25": float(np.percentile(a, 25)), "median": float(np.median(a)), "mean": float(a.mean()), "max": float(a.max())}


def kish(sizes) -> float:
    a = np.asarray(list(sizes), dtype=float)
    return float(a.sum() ** 2 / (a ** 2).sum()) if len(a) and (a ** 2).sum() > 0 else math.nan


def de_cluster(sizes, f: float, rho: float) -> float:
    """1 + (m_bar - 1) x rho with m_bar = sum m^2 / sum m (size-weighted mean cluster size). The gate passes ``f = 1`` (the census's own, unscaled sizes: a 21-day window has more
    days, not more units per day; code-freeze check MUST 3); ``f = 21 / covered days`` gives the scaled, print-only values."""
    a = np.asarray(list(sizes), dtype=float) * f
    if not len(a) or a.sum() <= 0:
        return math.nan
    return float(1.0 + ((a ** 2).sum() / a.sum() - 1.0) * rho)


def design_se(n: float, sd: float, de: float) -> float:
    return float(sd * math.sqrt(de / n)) if n > 0 and math.isfinite(de) else math.nan


def finite(x) -> bool:
    return x is not None and isinstance(x, (int, float)) and math.isfinite(float(x))


def gate(value, ok_fn) -> dict:
    """A gate line: ``pass`` is False for a NaN / missing value (NaN fails)."""
    return {"value": value if finite(value) else None, "pass": bool(finite(value) and ok_fn(float(value)))}


def write_once_marker(m: Path, payload: dict) -> str | None:
    try:
        fd = os.open(m, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as e:
        if e.errno == errno.EEXIST:
            return f"the LT14 census already ran on this seal ({m}): a second run is refused (3, write-once)"
        raise
    with os.fdopen(fd, "w") as fh:
        fh.write(json.dumps({"ran_utc": b.iso(b.now_ts()), **payload}, sort_keys=True))
    return None
