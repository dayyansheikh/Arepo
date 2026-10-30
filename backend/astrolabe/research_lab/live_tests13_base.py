# ruff: noqa: E501
"""LT13 stage A (docs/research_lab/LIVE_TESTS_13.md, design text FROZEN at sha256 ae594aa1...; DRAFT until registered): the building blocks of the CH253 census
(the listing batch). Research tooling only; never trades; makes no network request.

Stage A (design 7, build order, R1 MUST 2 / R1-full MUST 2) is: the origin-side unit builders, the batch registry and join (1.4.4), the pseudo-batch rule
(1.4.4, rule 21), the twin-state loader (states only, no own target), the aliased-controls rule (3.3), the census, seal and restore paths. NOTHING of
stage B is here: no target reader (no k + 1 outcome of any unit), no worlds, no size check, no analysis, no state-shift gate. CH252 is withdrawn
(``withdrawn_pre_census (fee reading unresolved)``, 1.4.3 rule (b)): nothing is built for it beyond the name in the census output's lists.

Reuse (LT13 7.1 says "vendored, hash-pinned copies"): LT12's and the older helpers are IMPORTED from ``live_tests12`` / ``live_tests12_base`` (themselves
vendored copies with their own provenance pins) and ``population_map_ch251`` (``fee_class``), never edited; their normalised sha256 values are part of the
declaration (``DECLARED["imported_sha256"]``) and every seal and census refuses if one differs (stage A ambiguity A1 in ``reviews/LT13_CODE_NOTE_2026-10-30.md``).
No E026 frozen file is imported, copied or edited. No LT11 / LT12 *object* (``xw``, ``cl_sib``, ``xo``, ``zs_D``, ``shock x unrew``, their twins and
targets) is computed: only generic loaders and statistics are reused, and ``tests`` assert that no unit builder or census path calls ``ch245_units`` /
``ch244_units``.

Causality (1.3): a unit at capture k reads captures <= k only (``SlotStore13.limit`` raises :class:`Refused` on a later slot); the twin state over (k + 2,
k + 3] is the one later-slot quantity and is returned by :func:`lag_twin_state` as ONE number per unit and capture.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import forecast, panel
from . import live_tests12 as lt12
from . import live_tests12_base as b
from . import population_map_ch251 as pm251

VERSION = "live-tests13-v1"
ROOT = forecast.ROOT
SNAPSHOT_ROOT = forecast.SNAPSHOT_ROOT
CENSUS_ROOT = ROOT / "data-dumps" / "research_lab" / "live_tests13_census"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "live_tests13_v1.json"
DESIGN_PATH = ROOT / "docs" / "research_lab" / "LIVE_TESTS_13.md"
LEDGER_PATH = ROOT / "docs" / "research_lab" / "EXPERIMENT_LEDGER.md"
SEALS = ROOT / "docs" / "research_lab" / "seals"
DESIGN_TEXT_SHA256 = "ae594aa1a81aa93591d98f3210d907dff4df47ee3ad1dc0bbd44c5dccf59f738"  # LIVE_TESTS_13.md design-text freeze (ledger: "LT13 DESIGN TEXT FROZEN", commit d940c0ab)
LEDGER_FREEZE_MARKER = "LT13 DESIGN TEXT FROZEN"
TEMPFAIL = 75
EPS = 1e-9
TESTS = ("CH253",)
WITHDRAWN = {"CH252": "withdrawn_pre_census (fee reading unresolved)"}
CENSUS_UNAVAILABLE = "census_unavailable (coverage)"
CENSUS_DROPPED = "census_dropped"
CENSUS_PASS = "census_pass"
CHAIN_GAP_S = 120.0  # 1.4.4: a batch closes when the next creation is MORE than 120 s after the previous one
RECEIPT_SPAN_S = 120.0  # 1.3
DAY_S = 86400.0
FORBIDDEN_BLOCKS = ("CH252", "CH244", "CH245", "CH243", "target", "k+1", "outcome")  # 6: blocks the census refuses to compute

# --- the declaration: every constant of the census in ONE block, hashed into the seal and the census output (6, 1.4.4, 3.3) --------------------------------

DECLARED: dict = {
    "grid": {"grid0_utc": "2026-10-01T00:31:00Z", "grid_s": 7200, "slot_tol_s": 1800},
    "eligibility": {"spread_max": 0.1, "end_margin_h": 3, "f_end_margin_h": 7,
                    "rule": "1.4: binary, open, active, accepting_orders not false; two-sided (bid > 0, ask < 1) and tight (spread <= 0.10) at k - 1 and k; end unknown or > t + 3 h (F arm > t + 7 h); non-sports ex-crypto by cb17_census.is_sports_sidecar + the pinned crypto classifier (unknown counts as crypto); one row per condition_id; tick known and equal at k - 1 and k"},
    "crypto_rule": {"fee_type_prefix": "crypto", "slug_regex": "(?i)(bitcoin|ethereum|solana|xrp|dogecoin|crypto|^btc|^eth-|^sol-|^bnb|^hype)"},
    "reward_null_rule": "listed_carry24h_v2",
    "reward_carry_slots": 12,
    "receipt_span_s": 120.0,
    "rv": {"rv24_window": 12, "rv24_min_obs": 10, "rv_floor_ticks": 0.5},
    "tiers": {"cuts_usd": [1000, 10000, 100000]},
    "controls_own": ["own_ds_c", "cbar", "spread_km1_c", "thin", "thin_x_zs", "fee_on", "absd"],  # 3.3: the own innovation, cbar, spread_{i,k-1}, thin, thin x zs, fee class, |d|; K (lt12.K_COMMON, incl. spread_k, d, rewarded_k) is added
    "controls_note": "AS WRITTEN IN 3.3 + 1.7: K holds spread_k, 3.3 adds spread_{k-1} AND the own innovation spread_k - spread_{k-1}: the three are exactly collinear (stage A ambiguity A3, not resolved here)",
    "batch": {"chain_gap_s": 120.0, "min_markets": 3, "min_events": 2, "min_mates": 2, "max_mates": 30, "completeness_min": 0.6, "pseudo_min_age_days": 7.0, "pseudo_deciles": 10,
              "event_key": "neg_risk_market_id where present, else Gamma event_id, else m:<condition_id>",
              "category_reading": "verbatim sidecar fee_category (null-like -> the literal 'unknown'); other:zero_fees is a literal level; no topic is reconstructed (1.4.4, 1.7)"},
    "seeds": {"size_check": 20261797, "power_runs": {"CH253": 2026179752}, "world10_calibration": 2026179761,
              "rule": "declared for stage B; the stage A census draws nothing (no random number), and no test uses a registered seed"},
    "census_gates": {
        "mde_common": {"t_sum": 3.47, "t_sum_exact": 3.4725, "day_factor": 1.5, "sd_ds": 0.02, "de_rho": 0.02, "family_cap": 0.4, "g_eff_min": 15,
                       "mde_max_c": {"CH253": 1.0}, "f_mde_max_c": {"CH253": 1.0},
                       "rule": "every MDE gate is max(declared, design) (6); DE_gate = max(5.0, 1 + (m_21 - 1) x 0.02); t_sum = max(3.47, exact); F-MDE = max(design MDE of Delta, MDE x sqrt(2 / (1 - max(0, r_gate))))"},
        "CH253": {"coverage_min": 0.2, "completeness_min": 0.6, "units_projected_min": 217224, "batches_with_unit_min": 500, "batches_ge48_min": 100, "events_min_units": 48,
                  "same_slot_min_units": 24, "same_slot_abs_corr": 0.8, "same_slot_share_max": 0.5, "ident_nonzero_min": 3, "ident_share_min": 0.5, "leverage_top_frac": 0.01,
                  "leverage_top_share_max": 0.25, "leverage_batch_share_max": 0.05, "vif_w_max": 2.0, "corr_max": 0.5, "placebo_coverage_min": 0.9, "block_share_min": 0.5,
                  "block_min_captures": 16, "venue_clock_max": 0.5, "venue_clock_abs_z": 1.0, "r_gate_max": 0.3, "de_floor": 5.0, "sd": "sd_ds"},
    },
    "census_inputs": {
        "span": {"start_utc": "2026-11-07T00:00:00Z", "end_utc": "2026-11-17T00:00:00Z", "first_slot_utc": "2026-11-07T00:31:00Z", "last_slot_utc": "2026-11-16T22:31:00Z"},
        "lookback_capture_slots": 12, "lag_slots_after": 3, "refuse_at_or_after_utc": "2026-11-17T06:00:00Z", "expected_origins": {"CC13": 120},
        "min_covered_days": {"CC13": 7.0, "CC13_twins": 5.0},
        "feed_window": None, "feed_note": "no CLOB reward-feed capture is restored, sealed or read by the LT13 census (CH252 withdrawn; 6, R1-full SHOULD 1)",
        "header_precheck": {"rows": ["received_utc", "best_bid", "best_ask", "liquidity", "volume24hr", "chg_1h", "end_date", "event_id", "neg_risk", "neg_risk_market_id", "closed", "active"],
                            "sidecar": ["received_utc", "fee_type", "fee_category", "series_slugs", "order_price_min_tick_size", "clob_rewards", "fees_enabled", "fee_schedule",
                                        "created_at", "volume_num", "accepting_orders", "event_ids"],
                            "optional_rows": ["chg_1d", "chg_1w"]},
    },
    "imported_sha256": {  # normalised sha256 (SPEC_SHA256 line excluded) of the files whose helpers LT13 imports; a seal or census refuses on any difference
        "live_tests12.py": "2090b450ff10f7b1b939ecd77f759be48bb313bedc328050abb10b16d084a0b9", "live_tests12_base.py": "6f2212f2f5243ea656c179ae3b1a35646c9db4815e006e95bf2c9117cf19f75c", "population_map_ch251.py": "82db7a75995f0b637b469f4abc421ad9be430fdf38f0a4bad7ed5e9e43a55140"},
}
IMPORTED_FILES = ("live_tests12.py", "live_tests12_base.py", "population_map_ch251.py")
CODE_FILES = ("live_tests13.py", "live_tests13_base.py")


class Refused(RuntimeError):
    """A pin, seal, scope or causality check failed: nothing is computed or written."""


def _canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def file_sha(path: Path) -> str:
    """Normalised sha256 of a code file (the ``SPEC_SHA256 = ...`` line excluded, LT3 9.3's rule), as :func:`live_tests12.code_sha256`."""
    return lt12.code_sha256(path)


def imported_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: file_sha(here / n) for n in IMPORTED_FILES}


def code_hashes() -> dict:
    here = Path(__file__).resolve().parent
    return {n: (file_sha(here / n) if (here / n).exists() else None) for n in CODE_FILES}


def declaration_sha256() -> str:
    """sha256 of the canonical JSON of :data:`DECLARED` (the module's declared constants, one block)."""
    return hashlib.sha256(_canon(DECLARED).encode("utf-8")).hexdigest()


def spec_blocks_sha(spec: dict) -> str:
    """sha256 of the canonical JSON of every declared block as the spec holds it (+ ``k_block``). The seal stores it; every census refuses a spec whose
    blocks differ from the seal-time ones. ``census_fixed`` (the values the census fills) is deliberately outside the hash."""
    blob = {k_: spec.get(k_) for k_ in sorted(DECLARED)}
    blob["k_block"] = spec.get("k_block")
    return hashlib.sha256(_canon(blob).encode("utf-8")).hexdigest()


def load_spec(path: Path = SPEC_PATH) -> dict:
    """The declared blocks + the JSON spec's mutable parts (the four lists, ``k_block``, ``census_fixed``). DRAFT: null placeholders allowed."""
    spec = copy.deepcopy(DECLARED)
    j = json.loads(Path(path).read_text())
    if j.get("design_text_sha256") != DESIGN_TEXT_SHA256:
        raise RuntimeError("live_tests13 spec design_text_sha256 differs from the module constant")
    for key in ("k_block", "k_tests", "dropped_tests", "census_unavailable", "withdrawn_pre_census", "census_fixed", "census_gate_values"):
        spec[key] = j.get(key)
    spec["_sha256"] = b.sha256_file(path)
    return spec


# --- refusals (6, "what the census code must refuse") -------------------------------------------------------------------------------------------------


def design_text_error(path: Path | None = None, ledger: Path | None = None) -> dict | None:
    """Refuse unless LIVE_TESTS_13.md hashes to the frozen constant AND the ledger records that hash on its ``LT13 DESIGN TEXT FROZEN`` line."""
    p = Path(path or DESIGN_PATH)
    got = b.sha256_file(p)
    if got != DESIGN_TEXT_SHA256:
        return {"error": "LIVE_TESTS_13.md differs from the text-frozen file (sha256 != the ledger's freeze hash): refused", "design_text_sha256": got, "frozen": DESIGN_TEXT_SHA256}
    led = Path(ledger or LEDGER_PATH)
    if not led.exists():
        return {"error": f"ledger {led} not found: the freeze hash cannot be checked against it: refused"}
    hit = [ln for ln in led.read_text().splitlines() if LEDGER_FREEZE_MARKER in ln and DESIGN_TEXT_SHA256 in ln]
    if not hit:
        return {"error": f"the ledger has no '{LEDGER_FREEZE_MARKER}' line carrying {DESIGN_TEXT_SHA256}: refused", "ledger": str(led)}
    return None


def check_blocks(requested) -> None:
    """Refuse to compute any CH252 block, any k + 1 target / outcome, or any LT11 / LT12 object (6)."""
    for r in requested:
        low = str(r).lower()
        if any(f.lower() in low for f in FORBIDDEN_BLOCKS) or re.search(r"lt1[12]|\bxw\b|cl_sib|\bxo\b|zs_d|shock", low):
            raise Refused(f"the LT13 census refuses to compute {r!r}: CH252 is withdrawn, no k + 1 target / outcome and no LT11 / LT12 object is computed (6)")
    unknown = [r for r in requested if r not in TESTS]
    if unknown:
        raise Refused(f"unknown census block(s) {unknown}")


def scope_error(spec: dict) -> dict | None:
    """CH252 may appear ONLY under ``withdrawn_pre_census``; the four lists are mutually exclusive (7.3)."""
    lists = {k_: spec.get(k_) for k_ in ("k_tests", "dropped_tests", "census_unavailable", "withdrawn_pre_census")}
    wd = lists["withdrawn_pre_census"]
    if wd is not None and sorted(wd) != ["CH252"]:
        return {"error": "the spec's withdrawn_pre_census must be exactly [CH252] (1.4.3 rule (b))", "withdrawn_pre_census": wd}
    seen: dict[str, str] = {}
    for k_, v in lists.items():
        for t in v or []:
            if t in seen:
                return {"error": f"{t} is in two of the four lists ({seen[t]}, {k_}): refused"}
            seen[t] = k_
    for k_ in ("k_tests", "dropped_tests", "census_unavailable"):
        if "CH252" in (lists[k_] or []):
            return {"error": f"CH252 is withdrawn_pre_census and may not be in {k_}: refused"}
    return None


def k_block_error(spec: dict) -> dict | None:
    kb = spec.get("k_block") or {}
    if not isinstance(kb.get("chg_1d"), bool) or not isinstance(kb.get("chg_1w"), bool):
        return {"error": "the spec's k_block (chg_1d, chg_1w) is not filled from the committed header pre-check: refused (6)", "k_block": kb}
    return None


def reward_rule_error(spec: dict) -> dict | None:
    if spec.get("reward_null_rule") != "listed_carry24h_v2" or spec.get("reward_carry_slots") != b.REWARD_CARRY_SLOTS:
        return {"error": "the spec does not declare the reward-null rule listed_carry24h_v2 with reward_carry_slots 12: refused"}
    return None


# --- sidecar / series (1.2): the per-capture files the census reads ----------------------------------------------------------------------------------


def load_ext13(cap_dir: Path) -> pd.DataFrame | None:
    """The sidecar by market_id (LT12's loader), plus ``attrs['has_fees_enabled']`` from the header (a sidecar WITHOUT the column says nothing about the fee class)."""
    ext = lt12.load_ext12(cap_dir)
    if ext is None:
        return None
    hdr = list(pd.read_csv(Path(cap_dir) / "rows_ext.csv.gz", nrows=0).columns)
    ext.attrs["has_fees_enabled"] = "fees_enabled" in hdr
    return ext


def _clean(s: pd.Series) -> pd.Series:
    s = s.fillna("").astype(str).str.strip()
    return s.where(~s.str.casefold().isin(b._NULL_LIKE), "")


def event_keys(nr_market_id, event_id, condition_id) -> np.ndarray:
    """1.4.4: event key = ``neg_risk_market_id`` where present, else Gamma ``event_id``, else ``m:<condition_id>``."""
    nk, ev, cd = _clean(pd.Series(nr_market_id)), _clean(pd.Series(event_id)), _clean(pd.Series(condition_id))
    return np.where(nk != "", nk, np.where(ev != "", ev, "m:" + cd)).astype(object)


def cat_verbatim(v) -> str:
    """1.4.4 / 1.7: the verbatim sidecar ``fee_category``; a null-like value is the literal ``unknown`` (a missing ``feeType``); nothing else is normalised."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "unknown"
    s = str(v)
    return "unknown" if s.strip().casefold() in b._NULL_LIKE else s


def series13_frame(rows: pd.DataFrame, ext: pd.DataFrame | None, spec: dict, day: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(series, status) of a capture: LT12's series (two-sided open active binary rows; ``ask == 1`` moved to the status file) plus ``ekey``, ``fee_type``, ``slug1`` (first
    series slug), ``fam`` (series family), ``fclass`` (the vendored ``population_map_ch251.fee_class``), ``acc`` (accepting_orders 1 / 0 / NaN)."""
    ser, st = lt12.series12_frame(rows, ext, spec, day)
    mids = pd.Index(ser["market_id"].astype(str))
    r = rows.set_index(rows["market_id"].astype(str)).reindex(mids)
    ek = event_keys(r["neg_risk_market_id"].to_numpy(), r["event_id"].to_numpy(), r["condition_id"].to_numpy())
    ser["ekey"] = ek
    n = len(ser)
    if ext is not None and n:
        e = ext.reindex(mids)
        has_fe = bool(ext.attrs.get("has_fees_enabled", True))
        slugs = e["series_slugs"].tolist()
        fe = ["" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v) for v in e["fees_enabled"].tolist()]
        ser["fee_type"] = e["fee_type"].fillna("").astype(str).to_numpy(object)
        ser["slug1"] = [b.first_series_slug(s_) for s_ in slugs]
        ser["fam"] = [lt12.series_family(s_, k_) for s_, k_ in zip(slugs, ek, strict=True)]
        ser["fclass"] = [pm251.fee_class(f_, has_fe, s_)[0] for f_, s_ in zip(fe, e["fee_schedule"].tolist(), strict=True)]
        ser["acc"] = [lt12._flag_num(v) for v in e["accepting_orders"].tolist()]
    else:
        ser["fee_type"], ser["slug1"], ser["fam"], ser["fclass"] = "", "", [f"none:{k_}" for k_ in ek], "unknown"
        ser["acc"] = np.nan
    return ser, st


def reg_frame(rows: pd.DataFrame, ext: pd.DataFrame | None) -> pd.DataFrame:
    """The registry rows of a capture (1.4.4): EVERY row with a sidecar ``created_at`` that parses (all categories, open or not), ``market_id``, ``condition_id``,
    ``created`` (epoch s), ``ekey``."""
    cols = ["market_id", "condition_id", "created", "ekey"]
    if ext is None or rows.empty:
        return pd.DataFrame({c: [] for c in cols})
    mids = rows["market_id"].astype(str)
    created = panel._epoch(ext["created_at"].reindex(pd.Index(mids)).astype(str))
    ek = event_keys(rows["neg_risk_market_id"].to_numpy(), rows["event_id"].to_numpy(), rows["condition_id"].to_numpy())
    out = pd.DataFrame({"market_id": mids.to_numpy(), "condition_id": rows["condition_id"].fillna("").astype(str).to_numpy(), "created": created, "ekey": ek})
    out = out[np.isfinite(out["created"].to_numpy(float)) & (out["condition_id"] != "")]
    return out.reset_index(drop=True)


def write_series13(work: Path, cap: dict, spec: dict) -> dict:
    """Write-once ``series/<id>.csv.gz`` (two-sided quotes + LT13 columns), ``status/``, ``rw/`` (reward status inputs) and ``reg/`` (registry rows)."""
    work = Path(work)
    cid = cap["id"]
    paths = [work / sub / f"{cid}.csv.gz" for sub in ("series", "status", "rw", "reg")]
    if all(p.exists() for p in paths):
        return {"written": False}
    rows = lt12.load_rows12(cap["dir"])
    ext = load_ext13(cap["dir"])
    day = b._utc_day(cap["start"])
    ser, st = series13_frame(rows, ext, spec, day)
    reg = reg_frame(rows, ext)
    w = [b.write_once_csv(paths[0], ser), b.write_once_csv(paths[1], st), b.write_once_csv(paths[2], b.rw_frame(ext, day)), b.write_once_csv(paths[3], reg)]
    return {"written": any(w), "rows": len(ser), "status_rows": len(st), "registry_rows": len(reg), "sidecar": ext is not None}


_STR_COLS = {"market_id": str, "event_id": str, "skey": str, "condition_id": str, "ekey": str, "fam": str, "slug1": str, "fee_type": str, "fclass": str, "fee_cat": str, "crypto7": str}


def read_series13(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    if cap_id is None:
        return None
    p = Path(work) / "series" / f"{cap_id}.csv.gz"
    if not p.exists():
        return None
    return pd.read_csv(p, dtype=_STR_COLS).set_index("market_id")


def read_reg13(work: Path, cap_id: str | None) -> pd.DataFrame | None:
    p = Path(work) / "reg" / f"{cap_id}.csv.gz"
    if cap_id is None or not p.exists():
        return None
    return pd.read_csv(p, dtype={"market_id": str, "condition_id": str, "ekey": str})


class SlotStore13(lt12.SlotStore):
    """:class:`live_tests12.SlotStore` with LT13's series reader and a HARD causality guard: ``limit`` (set by the unit builder to k) makes any read of a later slot
    raise :class:`Refused` (6: "any later-slot price or spread outside the twin term"). The LT12 member tables are not used (no LT12 object)."""

    limit: int | None = None

    def _guard(self, j: int) -> None:
        if self.limit is not None and j > self.limit:
            raise Refused(f"causality: a unit builder of origin {self.limit} tried to read slot {j} (> k): refused (1.3, 6)")

    def ser(self, j: int) -> pd.DataFrame | None:
        self._guard(j)
        return self._get("ser", j, lambda s: read_series13(self.work, self.by_slot[s]["id"]))

    def status(self, j: int):
        self._guard(j)
        return super().status(j)

    def rw(self, j: int):
        self._guard(j)
        return super().rw(j)

    def t_dec(self, j: int) -> float:
        self._guard(j)
        return super().t_dec(j)

    def members(self, j: int):
        raise Refused("LT12 member tables are not an LT13 object: refused")


# --- the batch registry and join (1.4.4); the sha256 of this code is pinned in the seal ----------------------------------------------------------------


class Registry:
    """1.4.4: every market seen in any sealed capture (up to the current origin) with a finite sidecar ``created_at``, all categories. It never forgets a market; an
    ``ekey`` is refreshed from the latest sighting."""

    def __init__(self) -> None:
        self.df = pd.DataFrame({"condition_id": pd.Series(dtype=object), "created": pd.Series(dtype=float), "ekey": pd.Series(dtype=object)}, index=pd.Index([], name="market_id"))

    def add(self, reg: pd.DataFrame | None) -> None:
        if reg is None or reg.empty:
            return
        r = reg.drop_duplicates("market_id").set_index("market_id")[["condition_id", "created", "ekey"]]
        known = r.index.intersection(self.df.index)
        if len(known):
            self.df.loc[known, "ekey"] = r.loc[known, "ekey"].to_numpy(object)
        new = r.loc[r.index.difference(self.df.index)]
        if len(new):
            self.df = pd.concat([self.df, new]) if len(self.df) else new.copy()

    def __len__(self) -> int:
        return len(self.df)

    def batches(self) -> BatchTable:
        return BatchTable(self.df)


class BatchTable:
    """1.4.4: the registry sorted by (``created``, ``condition_id``); a batch closes when the next creation is more than 120 s after the previous one. **Batch key** = (``created``
    of the earliest member, the smallest ``condition_id`` among members with that ``created``) = the first row of the sorted batch. A batch is **cross-event** if its members span >= 2
    event keys and it holds >= 3 markets."""

    def __init__(self, reg: pd.DataFrame, gap_s: float = CHAIN_GAP_S, min_markets: int = 3, min_events: int = 2) -> None:
        d = reg.reset_index().sort_values(["created", "condition_id", "market_id"], kind="mergesort").reset_index(drop=True)
        self.ids = d["market_id"].astype(str).to_numpy(object)
        n = len(d)
        created = d["created"].to_numpy(float)
        if n:
            new = np.r_[True, np.diff(created) > gap_s]
        else:
            new = np.zeros(0, bool)
        self.bid = np.cumsum(new) - 1 if n else np.zeros(0, int)
        self.start = np.flatnonzero(new)
        self.size = np.bincount(self.bid) if n else np.zeros(0, int)
        ek = pd.factorize(d["ekey"].astype(str))[0] if n else np.zeros(0, int)
        self.ekey = d["ekey"].astype(str).to_numpy(object) if n else np.zeros(0, object)
        m = int(ek.max()) + 1 if n else 1
        nev = np.bincount(np.unique(self.bid.astype(np.int64) * m + ek) // m, minlength=len(self.start)) if n else np.zeros(0, int)
        self.n_events = nev
        self.created = created
        self.cond = d["condition_id"].astype(str).to_numpy(object) if n else np.zeros(0, object)
        self.first_created = created[self.start] if n else np.zeros(0)
        self.key = [f"{b.iso(float(created[i]))}|{d['condition_id'].iloc[i]}" for i in self.start]
        self.cross = (self.size >= min_markets) & (nev >= min_events)
        self.batch_of = pd.Series(self.bid, index=pd.Index(self.ids, name="market_id")) if n else pd.Series(dtype=int)

    def members(self, j: int) -> np.ndarray:
        return self.ids[self.start[j]: self.start[j] + self.size[j]]

    def position(self, market_ids) -> np.ndarray:
        """Row of each market in the sorted registry (-1 = not registered)."""
        s = pd.Series(np.arange(len(self.ids)), index=pd.Index(self.ids))
        return s.reindex(pd.Index(np.asarray(market_ids, dtype=str))).fillna(-1).to_numpy(int)


def quote_flags(J: pd.DataFrame, P: pd.DataFrame, spec: dict) -> np.ndarray:
    """1.4.4 / 1.4 quote rules shared by units and mates: a series row (two-sided, ``ask < 1``) at k - 1 AND k, tight (spread <= 0.10) at both, tick known and equal, the pinned crypto
    classifier ``non_crypto`` (unknown counts as crypto) and a sidecar row. ``J`` / ``P`` are the series at k and k - 1 on a common index."""
    sm = spec["eligibility"]["spread_max"]
    present = J["bid"].notna().to_numpy() & P["bid"].notna().to_numpy()
    tight = b.tight_arr(J["bid"], J["ask"], J["ask"] - J["bid"], sm) & b.tight_arr(P["bid"], P["ask"], P["ask"] - P["bid"], sm)
    tk, tp = J["tick"].to_numpy(float), P["tick"].to_numpy(float)
    tick_ok = np.isfinite(tk) & np.isfinite(tp) & (np.abs(tk - tp) <= 1e-12)
    c7 = J["crypto7"].astype(str).to_numpy() if "crypto7" in J else np.full(len(J), "unknown")
    side = J["side"].to_numpy(float) if "side" in J else np.zeros(len(J))
    return present & tight & tick_ok & (c7 == "non_crypto") & (np.nan_to_num(side) == 1)


def mate_state(ser_k: pd.DataFrame, ser_p: pd.DataFrame, bt: BatchTable, spec: dict) -> dict:
    """The mate rules of 1.4.4 on the sorted registry rows of ``bt`` (arrays aligned to ``bt.ids``): ``base_ok`` = :func:`quote_flags` (sports mates ARE allowed); ``recv_ok`` = the row's
    receipt within 120 s of the batch's median receipt at k AND at k - 1 (the median over the batch's members with a series row at that capture); ``complete`` = both; ``innov`` = the
    spread change over (k - 1, k] in cents."""
    ids = pd.Index(bt.ids)
    J, P = ser_k.reindex(ids), ser_p.reindex(ids)
    base_ok = quote_flags(J, P, spec)
    trk, trp = J["t_row"].to_numpy(float), P["t_row"].to_numpy(float)
    g = bt.bid
    med_k = pd.Series(trk).groupby(g).transform("median").to_numpy(float) if len(g) else np.zeros(0)
    med_p = pd.Series(trp).groupby(g).transform("median").to_numpy(float) if len(g) else np.zeros(0)
    span = float(spec.get("receipt_span_s", RECEIPT_SPAN_S))
    with np.errstate(invalid="ignore"):
        recv_ok = (np.abs(trk - med_k) <= span) & (np.abs(trp - med_p) <= span) & np.isfinite(trk) & np.isfinite(trp)
    innov = np.round(((J["ask"] - J["bid"]) - (P["ask"] - P["bid"])).to_numpy(float) * 100.0, 10)
    return {"J": J, "P": P, "base_ok": base_ok, "recv_ok": recv_ok, "complete": base_ok & recv_ok, "innov": innov,
            "sports": J["sports"].to_numpy(float) if "sports" in J else np.full(len(ids), np.nan)}


def _sha_order(cond_ids, capture_id: str) -> np.ndarray:
    """Rule 21: the order of ``sha256(condition_id || capture_id)`` (hex digest), ascending."""
    keys = [hashlib.sha256((str(c) + str(capture_id)).encode("utf-8")).hexdigest() for c in cond_ids]
    return np.argsort(np.array(keys, dtype=object), kind="mergesort")


def assign_pseudo_batch(EL: pd.DataFrame, rows: np.ndarray, m: np.ndarray, capture_id: str, min_age_days: float = 7.0, deciles: int = 10) -> dict:
    """Rule 21, verbatim (1.4.4): for unit i with ``m`` complete mates at k the pseudo-mates are the first m eligible complete units at capture k, in the order of ``sha256(condition_id ||
    capture_id)``, that (i) share i's sidecar category (the verbatim ``fee_category``), (ii) lie in i's ``created_at`` decile (deciles over capture k's eligible complete units),
    (iii) were created >= 7 days before or after i, (iv) are not in i's batch, event key or series family (``none:<event key>`` singletons included). Fewer than m qualify: NaN
    (``placebo_none``). ``EL`` = capture k's eligible complete units with columns ``condition_id``, ``cat``, ``created``, ``ekey``, ``fam``, ``batch`` and ``innov``; ``rows`` the
    positions in ``EL`` of the units, ``m`` their mate counts. Reads capture k - 1 and k fields only (``innov`` is the k - 1 -> k change). Returns ``mbar_pb`` (the pseudo-mates'
    mean innovation, cents), ``decile`` of each unit and the ``none`` flags."""
    n = len(EL)
    rows = np.asarray(rows, int)
    out = np.full(len(rows), np.nan)
    dec_u = np.full(len(rows), -1, int)
    if n == 0 or len(rows) == 0:
        return {"mbar_pb": out, "decile": dec_u, "none": np.ones(len(rows), bool) if len(rows) else np.zeros(0, bool)}
    created = EL["created"].to_numpy(float)
    fin = np.isfinite(created)
    cuts = np.quantile(created[fin], [i / deciles for i in range(1, deciles)]) if fin.any() else np.array([])
    dec = np.where(fin, np.searchsorted(cuts, created, side="right"), -1)
    order = _sha_order(EL["condition_id"].to_numpy(object), capture_id)
    cat = EL["cat"].to_numpy(object)
    ekey, fam, bat = EL["ekey"].to_numpy(object), EL["fam"].to_numpy(object), EL["batch"].to_numpy(object)
    innov = EL["innov"].to_numpy(float)
    pools: dict[tuple, np.ndarray] = {}
    for pos in order:
        if dec[pos] >= 0:
            pools.setdefault((cat[pos], int(dec[pos])), []).append(pos)  # type: ignore[arg-type]
    pools = {k_: np.array(v, int) for k_, v in pools.items()}
    age = min_age_days * DAY_S
    for u, (r, mm) in enumerate(zip(rows, m, strict=True)):
        dec_u[u] = dec[r]
        pool = pools.get((cat[r], int(dec[r]))) if dec[r] >= 0 else None
        if pool is None or mm <= 0:
            continue
        ok = (np.abs(created[pool] - created[r]) >= age - 1e-6) & (ekey[pool] != ekey[r]) & (fam[pool] != fam[r]) & (bat[pool] != bat[r])
        hit = pool[ok][: int(mm)]
        if len(hit) >= int(mm):
            out[u] = float(np.mean(innov[hit]))
    return {"mbar_pb": out, "decile": dec_u, "none": ~np.isfinite(out)}


# --- the origin-side unit builder (3.2-3.3); reads slots <= k only ------------------------------------------------------------------------------------


def _c(x) -> float:
    return lt12._c(x)


def units13(store: SlotStore13, bt: BatchTable, k: int, spec: dict, role: str = "census", commit: str = "unknown") -> tuple[pd.DataFrame, dict]:
    """CH253's lines of origin k (3.2-3.3), states only, NO target. Returns (units, counts + ``_extras``). A unit is a non-sports ex-crypto market x capture passing 1.4, in a cross-event
    batch (1.4.4) with 2 <= complete cross-event mates <= 30, its batch-capture >= 60% complete and its own receipt within 120 s of the batch median; units with > 30 complete mates are
    the reported arm ``gt30``. Columns: ``mbar`` (the mates' mean spread innovation over (k - 1, k], cents), ``own_ds_c``, ``cbar`` (the category x slot factor: mean innovation over (k - 1, k]
    of capture k's eligible complete units of the unit's verbatim ``fee_category`` outside the unit's batch), ``thin``, ``mbar_pb`` (rule 21), K (reads <= k), ``fee_on``. ``store.limit``
    is set to k: a read of a later slot raises :class:`Refused`. All arrays below are aligned to the sorted registry ``bt.ids`` (``lines`` = registry rows of the units)."""
    store.limit = k
    cnt: dict = {}
    cap = store.by_slot[k]
    ser_k, ser_p = store.ser(k), store.ser(k - 1)
    t_dec = store.t_dec(k)
    if ser_k is None or ser_p is None or not math.isfinite(t_dec) or len(bt.ids) == 0:
        return pd.DataFrame(), {"no_prev": 1}
    bcfg = spec["batch"]
    elg = spec["eligibility"]
    ms = mate_state(ser_k, ser_p, bt, spec)
    J, P = ms["J"], ms["P"]
    n_reg = len(bt.ids)
    sports = ms["sports"]

    def end_flags(JJ: pd.DataFrame, margin_h: float) -> np.ndarray:
        end = JJ["end_ts"].to_numpy(float)
        with np.errstate(invalid="ignore"):
            return np.isnan(end) | (end > t_dec + margin_h * 3600.0)

    end_ok, f_end_ok = end_flags(J, elg["end_margin_h"]), end_flags(J, elg["f_end_margin_h"])
    acc_ok = ~(J["acc"].to_numpy(float) == 0.0) if "acc" in J else np.ones(n_reg, bool)
    base_ok, comp, innov = ms["base_ok"], ms["complete"], ms["innov"]
    cand = base_ok & end_ok & acc_ok & np.isin(sports, [0.0, 1.0])
    elig = cand & (sports == 0.0)  # non-sports ex-crypto, registered (has a created_at), 1.4
    # series rows without a registry row (no parseable created_at) are eligible rows that can never be in a batch: counted for the coverage denominator
    unreg = ser_k.index.difference(pd.Index(bt.ids))
    cnt["series_not_registered"] = int(len(unreg))
    if len(unreg):
        Ju, Pu = ser_k.reindex(unreg), ser_p.reindex(unreg)
        e_u = quote_flags(Ju, Pu, spec) & end_flags(Ju, elg["end_margin_h"]) & ~(Ju["acc"].to_numpy(float) == 0.0) & (Ju["sports"].to_numpy(float) == 0.0)
        cnt["elig_unregistered"] = int(e_u.sum())
    else:
        cnt["elig_unregistered"] = 0
    cnt["sidecar_missing"] = int((J["side"].to_numpy(float) == 0).sum()) + int((ser_k.reindex(unreg)["side"].to_numpy(float) == 0).sum()) if len(unreg) else int((J["side"].to_numpy(float) == 0).sum())
    cnt["eligible_registered"] = int(elig.sum())
    cnt["sports_candidates"] = int((cand & (sports == 1.0)).sum())
    g, nb = bt.bid, len(bt.start)
    n_comp = np.bincount(g, weights=comp.astype(float), minlength=nb)
    share = n_comp / np.maximum(bt.size, 1)
    ekc = pd.factorize(bt.ekey)[0]
    w_s = np.where(comp, np.nan_to_num(innov), 0.0)
    be = pd.DataFrame({"b": g, "e": ekc, "s": w_s, "n": comp.astype(float), "sp": (comp & (sports == 1.0)).astype(float), "m": 1.0})
    sums = be.groupby(["b", "e"])[["s", "n", "sp", "m"]].sum()
    kbe = pd.MultiIndex.from_arrays([g, ekc])
    S_be, N_be, SP_be, M_be = (sums[c].reindex(kbe).to_numpy(float) for c in ("s", "n", "sp", "m"))
    S_b = np.bincount(g, weights=w_s, minlength=nb)
    SP_b = np.bincount(g, weights=(comp & (sports == 1.0)).astype(float), minlength=nb)
    N_mates, S_mates, SP_mates = n_comp[g] - N_be, S_b[g] - S_be, SP_b[g] - SP_be
    cross = bt.cross[g]
    el_rows = np.flatnonzero(elig)
    cnt["elig_in_cross_batch"] = int(cross[el_rows].sum())
    bs_with = np.unique(g[el_rows[cross[el_rows]]]) if len(el_rows) else np.zeros(0, int)  # 6: pooled over cross-event batch-captures with an eligible member
    cnt["bc_members"], cnt["bc_complete"], cnt["bc_batches"] = int(bt.size[bs_with].sum()), int(n_comp[bs_with].sum()), int(len(bs_with))
    cnt["bc_incomplete_batches"] = int((share[bs_with] < bcfg["completeness_min"] - 1e-12).sum())
    lines = el_rows[cross[el_rows]]
    inc = share[g[lines]] < bcfg["completeness_min"] - 1e-12
    cnt["batch_incomplete_units"] = int(inc.sum())
    lines = lines[~inc]
    cnt["receipt_span_units"] = int((~comp[lines]).sum())  # eligible and in a complete batch-capture, but its own receipt is outside 120 s of the batch median (1.3)
    lines = lines[comp[lines]]
    cnt["mates_lt2_units"] = int((N_mates[lines] < bcfg["min_mates"]).sum())
    lines = lines[N_mates[lines] >= bcfg["min_mates"]]
    nm = N_mates[lines]
    arm = np.where(nm > bcfg["max_mates"], "gt30", "primary")
    cnt["gt30_units"] = int((arm == "gt30").sum())
    cnt["gt30_units_registry_mates"] = int(((bt.size[g[lines]] - M_be[lines]) > bcfg["max_mates"]).sum())  # 1.4.4's wording (the batch holds > 30 cross-event mates), printed beside 3.2's
    # the sports arm (reported, uncounted): sports candidates that would be units under the same rules
    sp_ok = cand & (sports == 1.0) & cross & (share[g] >= bcfg["completeness_min"] - 1e-12) & comp & (N_mates >= bcfg["min_mates"])
    cnt["sports_arm_units"] = int(sp_ok.sum())
    extras: dict = {"elig": _elig_tallies(J, elig), "qual_all": _qual_cells(J, base_ok)}
    if len(lines) == 0:
        cnt["_extras"] = {**extras, "gaps": (np.zeros(0, object), np.zeros(0)), "batches": {}}
        return pd.DataFrame(), cnt
    cond = J["condition_id"].fillna("").astype(str).to_numpy(object)
    cat_all = np.array([cat_verbatim(v) for v in J["fee_cat"].to_numpy(object)], dtype=object)
    EL_pos = el_rows[comp[el_rows]]
    EL = pd.DataFrame({"condition_id": cond[EL_pos], "cat": cat_all[EL_pos], "created": bt.created[EL_pos], "ekey": bt.ekey[EL_pos], "fam": J["fam"].to_numpy(object)[EL_pos],
                       "batch": g[EL_pos].astype(str).astype(object), "innov": innov[EL_pos]})
    cs = EL.assign(b=g[EL_pos])
    S_cat, N_cat = cs.groupby("cat")["innov"].sum(), cs.groupby("cat")["innov"].count()
    S_cb, N_cb = cs.groupby(["cat", "b"])["innov"].sum(), cs.groupby(["cat", "b"])["innov"].count()
    ucat = cat_all[lines]
    kcb = pd.MultiIndex.from_arrays([ucat, g[lines]])
    num = S_cat.reindex(ucat).to_numpy(float) - S_cb.reindex(kcb).fillna(0.0).to_numpy(float)
    den = N_cat.reindex(ucat).to_numpy(float) - N_cb.reindex(kcb).fillna(0.0).to_numpy(float)
    cbar = np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)
    row_in_el = pd.Series(np.arange(len(EL_pos)), index=EL_pos).reindex(lines).to_numpy().astype(int)
    pb = assign_pseudo_batch(EL, row_in_el, nm, cap["id"], bcfg["pseudo_min_age_days"], bcfg["pseudo_deciles"])
    trk = J["t_row"].to_numpy(float)
    spk1 = np.round((P["ask"] - P["bid"]).to_numpy(float) * 100.0, 10)
    thin = np.full(len(lines), np.nan)
    gap_mk, gap_val = [], []
    mk = bt.ids[lines]
    cache: dict[int, tuple] = {}
    for u, r in enumerate(lines):
        if arm[u] != "primary":
            continue
        j = int(g[r])
        if j not in cache:
            cm = np.flatnonzero(comp[bt.start[j]: bt.start[j] + bt.size[j]]) + bt.start[j]
            cache[j] = (cm, ekc[cm])
        cm, ec = cache[j]
        mates = cm[ec != ekc[r]]
        thin[u] = float(spk1[r] > np.median(spk1[mates]))
        gap_mk.append(np.full(len(mates), mk[u], dtype=object))
        gap_val.append(np.abs(trk[r] - trk[mates]))
    K = lt12.k_block(store, k, mk, t_dec, spec)
    fclass = J["fclass"].to_numpy(object)[lines] if "fclass" in J else np.full(len(lines), "unknown", dtype=object)
    slug1 = J["slug1"].fillna("").astype(str).to_numpy(object)[lines] if "slug1" in J else np.full(len(lines), "", dtype=object)
    out = pd.DataFrame({
        "market_id": mk, "condition_id": cond[lines], "batch_id": [bt.key[int(j)] for j in g[lines]], "ekey": bt.ekey[lines], "fam": J["fam"].to_numpy(object)[lines], "cat": ucat,
        "fee_type": J["fee_type"].fillna("").astype(str).to_numpy(object)[lines] if "fee_type" in J else "",
        "slug_sports": [bool(s_ and b.SPORTS_SERIES_RE.match(s_)) for s_ in slug1], "fee_on": (fclass == "fee_on").astype(float), "fclass": fclass, "arm": arm, "n_mates": nm,
        "n_sports_mates": SP_mates[lines], "batch_members": bt.size[g[lines]], "batch_complete_share": share[g[lines]], "batch_age_days": (t_dec - bt.first_created[g[lines]]) / DAY_S,
        "own_ds_c": innov[lines], "mbar": S_mates[lines] / nm, "cbar": cbar, "spread_km1_c": spk1[lines], "thin": thin, "mbar_pb": pb["mbar_pb"], "age_decile": pb["decile"],
        "f_end_ok": f_end_ok[lines].astype(float), "t_row_unit": trk[lines]})
    out = pd.concat([out.reset_index(drop=True), K.reset_index(drop=True)], axis=1)
    out["absd"] = np.abs(out["d"].to_numpy(float))
    out["day"] = b._utc_day(cap["start"])
    out["slot"], out["t_row"], out["role"], out["code_commit"] = k, t_dec, role, commit
    out = b._drop_missing(out, cnt, {"log_rv24s": "rv24_undefined", "rewarded": "reward_status_nan", "tk1": "tier_missing"})
    cnt["units_primary"] = int((out["arm"] == "primary").sum())
    cnt["placebo_none"] = int(((out["arm"] == "primary") & ~np.isfinite(out["mbar_pb"].to_numpy(float))).sum())
    bats = {int(j): (bt.members(int(j)), bt.ekey[bt.start[int(j)]: bt.start[int(j)] + bt.size[int(j)]]) for j in np.unique(g[lines])}
    cnt["_extras"] = {**extras, "gaps": (np.concatenate(gap_mk) if gap_mk else np.zeros(0, object), np.concatenate(gap_val) if gap_val else np.zeros(0)), "batches": {bt.key[j]: v for j, v in bats.items()}}
    return out, cnt


def _qual_cells(J: pd.DataFrame, base_ok: np.ndarray) -> dict:
    """1.4 print: rows that pass every quote / crypto rule but NOT yet the sports filter, by verbatim ``fee_type`` x first-series-slug-on-the-sports-list (yes / no) x the sports result
    (the 1,800-market classifier shift of q0717 is read here)."""
    if not base_ok.any():
        return {"cells": {}}
    ft = J["fee_type"].fillna("").astype(str).to_numpy(object)[base_ok] if "fee_type" in J else np.full(int(base_ok.sum()), "", dtype=object)
    sl = J["slug1"].fillna("").astype(str).to_numpy(object)[base_ok] if "slug1" in J else np.full(int(base_ok.sum()), "", dtype=object)
    sp = J["sports"].to_numpy(float)[base_ok]
    keys = [f"{a}|slug_sports={'yes' if (s_ and b.SPORTS_SERIES_RE.match(s_)) else 'no'}|sports={int(x) if np.isfinite(x) else -1}" for a, s_, x in zip(ft, sl, sp, strict=True)]
    return {"cells": {k_: int(v) for k_, v in pd.Series(keys).value_counts().items()}}


def _elig_tallies(J: pd.DataFrame, elig: np.ndarray) -> dict:
    """Descriptive tallies of the eligible rows by verbatim ``fee_type`` x ``fee_category`` (1.4.3 rule (a) prints), keyed ``fee_type|fee_category``."""
    if not elig.any():
        return {"cells": {}}
    ft = J["fee_type"].fillna("").astype(str).to_numpy(object)[elig] if "fee_type" in J else np.full(int(elig.sum()), "", dtype=object)
    fc = np.array([cat_verbatim(v) for v in J["fee_cat"].to_numpy(object)[elig]], dtype=object)
    cells = pd.Series([f"{a}|{c_}" for a, c_ in zip(ft, fc, strict=True)]).value_counts()
    return {"cells": {k_: int(v) for k_, v in cells.items()}}


# --- the twin-state loader (states only; the ONLY later-slot reader of the census; 6 "Twin-state detail") --------------------------------------------


_TWIN_CACHE: dict[str, pd.DataFrame] = {}


def _twin_frame(cap_dir: Path, spec: dict) -> pd.DataFrame:
    """Two-sided series rows of capture ``cap_dir`` (the SAME function that writes the per-capture series), indexed by market_id. INTERNAL to the loader: it never leaves it."""
    key = str(cap_dir)
    if key not in _TWIN_CACHE:
        if len(_TWIN_CACHE) > 6:
            _TWIN_CACHE.pop(next(iter(_TWIN_CACHE)))
        ser, _ = series13_frame(lt12.load_rows12(cap_dir), load_ext13(cap_dir), spec, "")
        _TWIN_CACHE[key] = ser.set_index("market_id")
    return _TWIN_CACHE[key]


def lag_twin_state(dir_a: Path, dir_b: Path, units: pd.DataFrame, batches: dict, spec: dict) -> np.ndarray:
    """The CENSUS lag-slot loader of CH253 (6): ONLY the twin STATE for each unit, as ONE number: the mean, over the unit's mates (the batch's members outside the unit's event key, with the
    batch and event partition of origin k), of their spread changes (cents) between origins k + 2 (``dir_a``) and k + 3 (``dir_b``), NaN unless: >= 2 and <= 30 mates are two-sided and
    tight at both, tick unchanged, non-crypto, within the receipt rule (120 s of the batch's median at both), and >= 60% of the batch's members are complete there. The caller divides by ``s_bt``.
    No bid, ask, spread level, volume or own target leaves this function; ``units`` needs ``batch_id`` (a key of ``batches``) and ``ekey`` (stage A ambiguity A6: the unit's own book is not required)."""
    n = len(units)
    out = np.full(n, np.nan)
    if n == 0:
        return out
    A, B = _twin_frame(Path(dir_a), spec), _twin_frame(Path(dir_b), spec)
    sm = spec["eligibility"]["spread_max"]
    span = float(spec.get("receipt_span_s", RECEIPT_SPAN_S))
    bcfg = spec["batch"]
    cache: dict = {}
    for i, (bj, ek) in enumerate(zip(units["batch_id"].tolist(), units["ekey"].tolist(), strict=True)):
        if bj not in batches:
            continue
        if bj not in cache:
            ids, eks = batches[bj]
            ids = pd.Index(np.asarray(ids, dtype=str))
            a, bb = A.reindex(ids), B.reindex(ids)
            ok = a["bid"].notna().to_numpy() & bb["bid"].notna().to_numpy()
            tight = b.tight_arr(a["bid"], a["ask"], a["ask"] - a["bid"], sm) & b.tight_arr(bb["bid"], bb["ask"], bb["ask"] - bb["bid"], sm)
            ta, tb = a["tick"].to_numpy(float), bb["tick"].to_numpy(float)
            tick_ok = np.isfinite(ta) & np.isfinite(tb) & (np.abs(ta - tb) <= 1e-12)
            c7 = (a["crypto7"].astype(str).to_numpy() == "non_crypto") & (bb["crypto7"].astype(str).to_numpy() == "non_crypto") & (np.nan_to_num(a["side"].to_numpy(float)) == 1) & (np.nan_to_num(bb["side"].to_numpy(float)) == 1)
            tra, trb = a["t_row"].to_numpy(float), bb["t_row"].to_numpy(float)
            with np.errstate(invalid="ignore"):
                rc = (np.abs(tra - np.nanmedian(tra)) <= span) & (np.abs(trb - np.nanmedian(trb)) <= span) if np.isfinite(tra).any() and np.isfinite(trb).any() else np.zeros(len(ids), bool)
            comp = ok & tight & tick_ok & c7 & rc
            inn = np.round(((bb["ask"] - bb["bid"]) - (a["ask"] - a["bid"])).to_numpy(float) * 100.0, 10)
            cache[bj] = (comp, inn, np.asarray(eks, dtype=object), float(comp.sum() / max(len(ids), 1)))
        comp, inn, eks, shr = cache[bj]
        if shr < bcfg["completeness_min"] - 1e-12:
            continue
        mates = comp & (eks != ek)
        nm = int(mates.sum())
        if bcfg["min_mates"] <= nm <= bcfg["max_mates"]:
            out[i] = float(np.mean(inn[mates]))
    return out


# --- aliased or collinear controls (3.3, R1-full SHOULD 4) -----------------------------------------------------------------------------------------


def _qr_rank(R: np.ndarray, cols: list[int], n_rows: int) -> int:
    """Rank of the columns ``cols`` of A, from A's triangular factor ``R`` (A[:, cols] = Q R[:, cols]): column-pivoted QR, tolerance ``max(n, p) x eps x the largest singular value``."""
    import scipy.linalg as sla

    if not cols:
        return 0
    M = R[:, cols]
    s = np.linalg.svd(M, compute_uv=False)
    tol = max(n_rows, M.shape[1]) * np.finfo(float).eps * (float(s[0]) if len(s) else 0.0)
    _, r2, _ = sla.qr(M, mode="economic", pivoting=True)
    return int((np.abs(np.diag(r2)) > tol).sum())


def drop_order(columns: list[str], fc_levels: dict[str, str], fee_class_col: str = "fee_on") -> list[str]:
    """3.3: the fixed order in which a span-redundant control may be dropped: (1) the ``fee_category`` dummies, LAST LEVEL FIRST in lexicographic order of the verbatim string; (2) the fee-class dummy;
    (3) the slot-of-day dummies, LATEST SLOT FIRST (``sd11`` .. ``sd1``). Never ``zs_bt``."""
    g1 = sorted((c for c in columns if c in fc_levels), key=lambda c: fc_levels[c], reverse=True)
    g2 = [c for c in columns if c == fee_class_col]
    g3 = sorted((c for c in columns if re.fullmatch(r"sd\d+", c)), key=lambda c: int(c[2:]), reverse=True)
    return [*g1, *g2, *g3]


def resolve_aliased_controls(D: pd.DataFrame, term: str, controls: list[str], fc_levels: dict[str, str]) -> dict:
    """3.3, the deterministic rule: on the demeaned control matrix WITHOUT ``zs_bt`` (``D`` holds demeaned columns; rows with a non-finite value are dropped), compute the rank by
    column-pivoted QR (tolerance ``max(n, p) x eps x sigma_max``); if it is below the number of columns, in the fixed order of :func:`drop_order` drop a column only if it lies in the span of
    the OTHER RETAINED columns (removing it leaves the rank unchanged), otherwise keep it and test the next; never ``zs_bt``. Still rank-deficient after groups (1)-(3), or ``zs_bt`` in the span
    of the retained controls: the fit is NaN, ``status = "unavailable"`` (pseudo-inverse / minimum-norm solutions are NOT used). Zero-variance columns are removed before the rank (stage A
    ambiguity A4: LT12's fits drop them the same way) and reported. Returns kept columns, dropped columns (in order), rank, number of columns and the status."""
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
    for c in drop_order(cols, fc_levels):
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
        return {**res, "status": "unavailable", "reason": "controls still rank-deficient after groups (1)-(3)"}
    Az = np.column_stack([d[kept].to_numpy(float), d[term].to_numpy(float)]) if kept else d[[term]].to_numpy(float)
    Rz = np.linalg.qr(Az, mode="r") if n >= Az.shape[1] else np.linalg.qr(np.vstack([Az, np.zeros((Az.shape[1] - n, Az.shape[1]))]), mode="r")
    r_all = _qr_rank(Rz, list(range(Az.shape[1])), n)
    if r_all == rank:
        return {**res, "term_aliased": True, "status": "unavailable", "reason": f"{term} lies in the span of the retained controls"}
    return {**res, "status": "ok", "reason": None}


def fee_cat_dummies(df: pd.DataFrame, min_share: float = 0.005) -> tuple[pd.DataFrame, list[str], dict[str, str]]:
    """1.7: the non-sports ``fee_category`` dummies of K on the VERBATIM string (``other:zero_fees`` and ``unknown`` literal levels): every level holding at least 0.5% of the frame's units
    except the most frequent (the reference), as LT12's A12. Returns (frame, dummy names, {name: level})."""
    cat = df["cat"].astype(str)
    share = cat.value_counts(normalize=True)
    out = df.copy()
    names: list[str] = []
    lev: dict[str, str] = {}
    for i, c in enumerate(share.index[1:]):
        if share[c] < min_share:
            continue
        nm = f"fc_{i}_" + re.sub(r"[^a-z0-9]+", "_", c.casefold())
        out[nm] = (cat == c).astype(float)
        names.append(nm)
        lev[nm] = c
    return out, names, lev


def controls13(df: pd.DataFrame, fc_names: list[str], spec: dict | None = None) -> list[str]:
    """3.3 / 1.7: the declared own controls, then K (``live_tests12.K_COMMON``), then the verbatim ``fee_category`` dummies; only columns present, de-duplicated, in this order."""
    own = (spec or DECLARED)["controls_own"]
    seen: list[str] = []
    for c in [*own, *lt12.K_COMMON, *fc_names]:
        if c in df.columns and c not in seen:
            seen.append(c)
    return seen


# --- the pinned join code (6: "a batch-join code sha256 not pinned in the seal") -----------------------------------------------------------------------


def batch_join_symbols():
    return (event_keys, Registry, BatchTable, mate_state, _sha_order, assign_pseudo_batch, lag_twin_state, cat_verbatim)


def batch_join_sha() -> str:
    """sha256 of the source text of the batch join (registry, chain, batch key, cross-event rule, mate state and completeness, receipt rule, rule-21 pseudo-batch, the twin mate rule). The seal
    pins it; the census refuses a seal without it or with another value."""
    txt = "\n".join("\n".join(ln.rstrip() for ln in inspect.getsource(o).splitlines()) for o in batch_join_symbols())
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()
