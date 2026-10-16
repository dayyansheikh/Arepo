# ruff: noqa: E501
"""CB5 declaration (docs/research_lab/CREATIVE_BATCH_5.md, REVISED after challenger round 1).

Single source of every CB5 analysis rule, window, floor, gate, date, placebo and estimator, hashed by ``declaration_sha256()``.
The pattern mirrors ``cb4_declaration``: the hash covers the constants AND the source of every rule-applying function (the CB5
modules and the imported cost / statistics / grouper helpers), so a code change that alters a rule changes the hash and the runner
refuses to count until ``model_specs/cb5_v1.json`` is re-committed. The CDF grouper (``cb5_cdf.grouper_declaration()``, patterns,
period table, matching rule and the function sources) is part of the hash, so it is hashed before any title is read.

No threshold, formula or window here may be changed to obtain a pass.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

from . import cb3_declaration as _c3
from . import cb5_cdf, cb5_extract, cb5_hours, cb5_seed, cost_regimes, provenance

VERSION = "cb5-v1"
LABEL = "EXPLORATORY CB5 seed-anchor reversion, ladder-vs-bucket CDF consistency and hour-of-day moderation of the Kalshi lead"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "cb5_v1.json"
REP_PIN_PATH = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb5_t_rep_start.json"
CB1D_STOP_PATH = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb1_d_stopped.json"
GROUPER_SEAL_PATH = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb5_grouper_hash.json"

KIND_TEST, KIND_REP, KIND_MEASURE, KIND_DESCRIPTIVE = "cb5_test", "cb5_replication", "cb5_measurement", "cb5_descriptive"
TRIAL_KINDS = (KIND_TEST, KIND_REP, KIND_MEASURE, KIND_DESCRIPTIVE)
COUNT_SOURCES = ("creative_batch_5:G", "creative_batch_5:L", "creative_batch_5:K")


class DeclarationError(RuntimeError):
    """The committed CB5 declaration is missing, uncommitted, mutated or does not match the code."""


class WindowError(RuntimeError):
    """A date window or pin rule is violated."""


class RefusedRun(RuntimeError):
    """A sealed, reserved or retired run id or path."""


class TooEarly(RuntimeError):
    """A stage or outcome read that is not yet allowed."""


# ---- dates (section 1.2) ---------------------------------------------------------------------------------------------

DATES = {
    "T5_dev_start": "2026-10-11T12:00:00Z",
    "T5_dev_end": "2026-10-27T00:00:00Z",
    "T5_rep_start_floor": "2026-10-29T00:00:00Z",
    "T5_rep_start_min_gap_after_freeze_h": 2,
    "T5_G_rep_len_d": 21,
    "T5_G_read_after_end_h": 4 * 24 + 2,
    "T5_L_rep_len_d": 28,
    "T5_L_out_after_rep_end_d": 30,
    "T_h2_clock": "2026-10-11T23:00:33Z",
    "T_seal": "2026-10-22T00:00:00Z",
    "T_E9_unseal": "2026-11-03T00:00:00Z",
    "T_CB1D_rep": "2026-11-09T00:00:00Z",
    "T_J4R": cb5_hours.T_J4R,
    "census_cohort_listing_end": "T5_dev_end - 1d",
    "L_payoff_reread_latest": "2027-06-30",
}

# ---- statistics, stages, counting (sections 2.3-2.6) -----------------------------------------------------------------

SEED_BOOT = 516
N_BOOT, PLACEBO_DRAWS, WILD_DRAWS = 2000, 200, 9999
ALPHA_STAGE1_ROUTE, ALPHA_STAGE2, ALPHA_K, BY_Q = 0.01, 0.05, 0.05, 0.10
MIN_UNITS, MIN_CLUSTERS, G_NORMAL, G_MIN = 100, 30, 30, 15
PLACEBO_MAX_ADVANCE_RATE = 0.015
R_ANN_MIN = 0.10
COST_SENS_C = cb5_seed.BIND_COST
TOP_CLUSTERS_DROPPED = 5
ROUTE_STAGE2_K_MAX = 3

FLOORS = {"G1": -0.20, "G2": 0.010, "L1": 0.005, "K1": 0.10}
FLOOR_UNITS = {"G1": "slope (price per price)", "G2": "price per filled share", "L1": "price per pair", "K1": "asymmetry units (A10 + A20)"}
TESTS = {"G": ("G1", "G2"), "L": ("L1",), "K": ("K1",)}
STAGE2_ROUTE_TESTS = ("G1", "G2", "L1")
DIRECTIONS = {"G1": "< 0", "G2": "> 0", "L1": "> 0", "K1": "two-sided (CH58 predicts > 0)"}

# ---- family rules ----------------------------------------------------------------------------------------------------

G = {
    "population": {"binary": True, "token_ref": 0, "weather_excluded": True, "sports": "reported stratum", "negrisk_members_max": 2, "min_life_d": cb5_seed.MIN_LIFE_D,
                   "min_trades_pre_t1": cb5_seed.MIN_TRADES_PRE, "seed_range": list(cb5_seed.SEED_RANGE), "h2_clock_rule": "L + 4d + 1h <= T_h2_clock",
                   "as_of": "replication: end_at and member count at first sighting in listings/; h2: as of T_h2_clock (disclosed look-ahead)"},
    "seed": {"set": "points stamped s with L - 600 <= s and s + 600 <= t_ft", "sigma": "latest point of S", "template_tol": cb5_seed.TEMPLATE_TOL},
    "windows": {"t1_h": cb5_seed.T1_H, "t3_h": cb5_seed.T3_H, "entry": "P_A[t1, t1+6h)", "exit": "P_A[t3-6h, t3)", "feature": "VWAP1 over [t_ft, t1)"},
    "G1": {"stat": "OLS slope of y = X - E on d = VWAP1 - sigma, informative seeds", "ways": list(cb5_seed.WAYS), "floor": FLOORS["G1"]},
    "G2": {"d_min": cb5_seed.D_G2_MIN, "h_gen_min": cb5_seed.GEN_H_MIN, "quote_step": cb5_seed.G2_QUOTE_STEP, "fill": "strict trade-through in (t1, t1+24h]",
           "exit": "taker at t3 with h_gen; payout if closed before t3", "binding_cost": cb5_seed.BIND_COST, "floor": FLOORS["G2"], "r_ann_min": R_ANN_MIN},
    "placebo": {"seed_permutation": {"slope": "level_controlled", "within": "fee_category x listing ISO week", "draws": cb5_seed.PLACEBO_DRAWS, "seed": cb5_seed.SEED_PLACEBO,
                                      "max_rate": cb5_seed.PLACEBO_MAX_RATE, "raw_reported": True},
                "template_stratum": {"min_units": cb5_seed.STRATUM_MIN_UNITS, "range": [5, 95], "rule": "beta_residual <= beta_informative / 2"},
                "breakeven_g2": {"draws": cb5_seed.PLACEBO_DRAWS, "seed": cb5_seed.SEED_PLACEBO + 1, "max_rate": cb5_seed.PLACEBO_MAX_RATE}},
    "robustness": ["+0.75c on exit", "top-5 clusters dropped", "unweighted vs cluster-equal sign", "ask/bid/history targets sign", "beta_LC sign and half magnitude",
                   "truncation worst case", "era rule", "stratum-adjusted slope sign (h2)"],
    "carry_rule": "G1 advances, G2 not testable for size only with estimate >= 0",
    "census": {"g_ii_echo_stop": cb5_seed.ECHO_STOP_SHARE, "g_iv_min": cb5_seed.DETERMINISM_MIN, "g_v": {"min_checkable": cb5_seed.BOOK_MIN_CHECKABLE, "min_agree": cb5_seed.BOOK_MIN_AGREE,
               "spread_max": cb5_seed.BOOK_SPREAD_MAX, "tol": cb5_seed.BOOK_TOL}, "g_vi_min": cb5_seed.SIDE_AUDIT_MIN,
               "g56": {"units": cb5_seed.GATE_MIN_UNITS, "events": cb5_seed.GATE_MIN_EVENTS, "dates": cb5_seed.GATE_MIN_DATES},
               "window": "[L - 1h, min(first trade + 1h, L + 24h)]", "h2_exceptions": ["feature window for G-vi", "count-only window_count for G-vii"]},
    "labels": ["h2: beyond budget, L1 at most", "h2: seed semantics unverified for era"],
}

L = {
    "grouper": cb5_cdf.grouper_declaration(),
    "trigger_min": cb5_cdf.TRIGGER_MIN, "gap_h": list(cb5_cdf.GAP_H), "leg_spread_s": cb5_cdf.LEG_SPREAD_S, "depth_min_size": cb5_cdf.DEPTH_MIN_SIZE,
    "placebo": {"kind": "mismatched-family coherence", "draws": cb5_cdf.PLACEBO_DRAWS, "seed": cb5_cdf.SEED_PLACEBO, "max_rate": cb5_cdf.PLACEBO_MAX_ADVANCE_RATE,
                "min_families": cb5_cdf.PLACEBO_MIN_FAMILIES, "same": "granularity and boundary day D"},
    "gates": {"g59_families": cb5_cdf.G59_MIN_FAMILIES, "r_inc_min_families": cb5_cdf.RINC_MIN_FAMILIES, "wilson_z": cb5_cdf.Z95, "divergence": "mean(net') - 1.0 * r_inc_plus > 0",
              "payoff_max_short": cb5_cdf.PAYOFF_MAX_SHORT, "payoff_min_determined": cb5_cdf.PAYOFF_MIN_DETERMINED, "depth_min_family_clusters": 30,
              "unknown_or_inconclusive": "never counts as met; blocks crediting", "payoff_reread_latest": DATES["L_payoff_reread_latest"]},
    "audit": {"n": cb5_cdf.AUDIT_N, "max_bad": cb5_cdf.AUDIT_MAX_BAD, "revisions": 1},
    "frame": [cb5_cdf.FRAME_START, cb5_cdf.FRAME_END], "ways": ["family", "family_week"], "persist_steps": list(cb5_cdf.PERSIST_STEPS),
    "hold": "L screen refused before CB1-D replication results (or recorded stop) and before T_CB1D_rep", "sports_weather": "weather excluded; sports stratum",
}

K = {
    "buckets_ny": {"R": [cb5_hours.R_START_MIN, cb5_hours.R_END_MIN], "O": "complement", "assigned_by": "grid time t of the first mover"}, "lags_steps": list(cb5_hours.LAGS),
    "statistic": "K1 = [A_O(10)+A_O(20)] - [A_R(10)+A_R(20)]", "boot": {"n": cb5_hours.N_BOOT, "seed": cb5_hours.SEED_BOOT, "ways": ["event", "utc_date"]},
    "pseudo_split": {"draws_per_bucket": cb5_hours.PSEUDO_DRAWS, "seed": cb5_hours.SEED_PSEUDO, "max_reject": cb5_hours.PSEUDO_MAX_REJECT, "blocks": "pair x NY date x half-hour"},
    "controls": {"activity": {"deciles": cb5_hours.ACT_DECILES, "terciles": cb5_hours.ACT_TERCILES}, "within_pair_min_steps": cb5_hours.MIN_PAIR_STEPS},
    "c1_expected": list(cb5_hours.C1_EXPECTED), "primary": "non-sports C1 pairs", "j4": {"mid": list(cb5_hours.J4_MID), "wide": cb5_hours.HALF_SPREAD_J4, "label_pp": cb5_hours.J4_DIFF_LABEL},
    "live_root": "refused until 2026-11-03, committed K1-R spec and owner sign-off", "floor": cb5_hours.K1_FLOOR,
}

EXTRACT = {"version": cb5_extract.EXTRACTOR_VERSION, "listings_columns": cb5_extract.LISTINGS_COLUMNS, "cdf_columns": cb5_extract.CDF_COLUMNS,
           "lookback_h": cb5_extract.NEW_LISTING_LOOKBACK_H, "refuse_gb": cb5_extract.JOB_REFUSE_GB, "cap_gb": cb5_extract.DATA_DUMPS_MAX_GB}

REFUSED_RUN_IDS = ("h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era", "h7_cb4_series")
REFUSED_ROOTS = ("cb1_extract", "cb2_extract", "cb3_extract", "cb4_extract", "creative_batch1", "creative_batch2", "creative_batch3", "creative_batch4")
CENSUS_FORBIDDEN_COLUMNS = (
    "outcome", "outcome_prices", "outcomePrices", "outcomes", "Y", "y", "resolved", "winner", "closed_time", "closedTime", "net", "y0", "payout",
    "E", "X", "y_B", "y_H", "beta", "k1", "net_A", "net_B",
)
CENSUS_COUNTS = {
    "G": ["eligible_h2_markets", "valid_seed_share", "seed_echo_share", "template_share", "determinism_share", "seed_book_agreement", "side_audit_day0", "g56", "listings_per_day"],
    "L": ["families_by_category_granularity", "historical_vs_live", "grouper_audit", "eligible_pair_captures_per_family", "g59"],
    "K": ["pairs_events_by_category", "steps_clusters_per_bucket", "g_per_way", "pairs_ge30", "mde", "kalshi_spread_flat_by_bucket", "j4_wide_by_hour"],
}

HYPOTHESES_CB5 = {
    "G1": "After the first day's trades move a new market's price away from its pre-trade seeded quote, the price reverts toward the seed over days 1-3.",
    "G2": "A maker order on the seed side at +24h, exited at +72h as a taker, pays after costs.",
    "L1": "P(by D) = sum of P(bucket <= D) is violated at the touch by more than fees and the violation persists at the touch two hours later.",
    "K1": "The 10-20 minute Kalshi to Polymarket lead is larger in US overnight hours than in US day and evening hours.",
}

# (module, name) of imported rule-applying functions whose source is part of the declaration
IMPORTED_RULE_FUNCTIONS = (
    ("cb1_history", "is_sports"), ("cb1_history", "half_spread"), ("cb1_history", "fee_rate"), ("cb1_history", "iso_week"),
    ("cb2_weather", "small_g_pvalue"), ("cb2_weather", "_cluster_sums"), ("battery", "_cr_var_of_sum"),
    ("cb3_common", "mean_test"), ("cb3_common", "slope_test"), ("cb3_common", "testable"), ("cb3_common", "boot_ci_mean"), ("cb3_common", "top_clusters_mask"),
    ("cb3_common", "sign_agree"), ("cb3_common", "holm"), ("cb3_common", "batch_holm"), ("cb3_common", "write_new"), ("cb3_common", "_partial"),
    ("cost_regimes", "cost_regime"), ("cost_regimes", "era_window_start"), ("cost_regimes", "rollout_date"),
    ("cb3_declaration", "spec_committed"), ("cb3_declaration", "single_commit"), ("cb3_declaration", "canonical_sha256"),
    ("if_h2", "parse_deadline"), ("if_h2", "stem"), ("if_h2", "_tokens"),
    ("cross_venue", "tokenize"), ("cross_venue", "usable"), ("cross_venue", "lagged_diff"), ("cross_venue", "p_two_sided"), ("cross_venue", "p_one_sided"),
    ("cb4_data", "ReleaseCopies"), ("cb4_data", "Catalogue"),
)
CB5_RULE_MODULES = ("cb5_declaration", "cb5_extract", "cb5_seed", "cb5_cdf", "cb5_hours")
ABSENT = "ABSENT"


def source_hashes() -> dict[str, str]:
    """sha256 of every function and class defined in the CB5 rule modules plus the imported rule functions. A module that is not
    importable contributes ``<module>: ABSENT`` and blocks :func:`require_declaration`."""
    out: dict[str, str] = {}
    for mod in CB5_RULE_MODULES:
        try:
            m = importlib.import_module(f"{__package__}.{mod}")
        except ModuleNotFoundError as exc:
            if exc.name != f"{__package__}.{mod}":
                raise
            out[mod] = ABSENT
            continue
        for name, obj in sorted(vars(m).items()):
            if (inspect.isfunction(obj) or inspect.isclass(obj)) and getattr(obj, "__module__", None) == m.__name__:
                out[f"{mod}.{name}"] = hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()
    for mod, name in IMPORTED_RULE_FUNCTIONS:
        m = importlib.import_module(f"{__package__}.{mod}")
        out[f"{mod}.{name}"] = hashlib.sha256(inspect.getsource(getattr(m, name)).encode()).hexdigest()
    return out


def absent_modules() -> list[str]:
    return sorted(k for k, v in source_hashes().items() if v == ABSENT)


def _plain(v):
    """A JSON-able copy of a simple module constant, or ``_SKIP`` (paths, regexes, zone objects, callables are not constants)."""
    if isinstance(v, bool | int | float | str) or v is None:
        return v
    if isinstance(v, tuple | list):
        out = [_plain(x) for x in v]
        return _SKIP if any(x is _SKIP for x in out) else out
    if isinstance(v, frozenset | set):
        out = [_plain(x) for x in sorted(v, key=str)]
        return _SKIP if any(x is _SKIP for x in out) else out
    if isinstance(v, dict):
        out = {str(k): _plain(x) for k, x in v.items()}
        return _SKIP if any(x is _SKIP for x in out.values()) else out
    return _SKIP


_SKIP = object()


def module_constants() -> dict[str, dict]:
    """Every UPPER_CASE simple module constant of the CB5 rule modules (except this one), read at call time: a changed threshold,
    window, seed or word list changes the hash even where no function source changed."""
    import re

    out: dict[str, dict] = {}
    for mod in CB5_RULE_MODULES:
        if mod == "cb5_declaration":
            continue
        m = importlib.import_module(f"{__package__}.{mod}")
        c = {}
        for name, v in sorted(vars(m).items()):
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                pv = _plain(v)
                if pv is not _SKIP:
                    c[name] = pv
        out[mod] = c
    return out


def declaration_blob() -> dict:
    return {
        "sources": source_hashes(), "module_constants": module_constants(), "version": VERSION, "dates": DATES, "seeds": {"boot": SEED_BOOT},
        "draws": {"n_boot": N_BOOT, "placebo": PLACEBO_DRAWS, "wild": WILD_DRAWS},
        "stage": {"alpha1_route": ALPHA_STAGE1_ROUTE, "alpha2": ALPHA_STAGE2, "alpha_K": ALPHA_K, "by_q": BY_Q, "min_units": MIN_UNITS, "min_clusters": MIN_CLUSTERS,
                  "g_normal": G_NORMAL, "g_min": G_MIN, "placebo_max_advance_rate": PLACEBO_MAX_ADVANCE_RATE, "r_ann_min": R_ANN_MIN, "cost_sens": COST_SENS_C,
                  "top_clusters_dropped": TOP_CLUSTERS_DROPPED, "route_stage2_k_max": ROUTE_STAGE2_K_MAX},
        "floors": FLOORS, "floor_units": FLOOR_UNITS, "tests": {k: list(v) for k, v in TESTS.items()}, "stage2_route_tests": list(STAGE2_ROUTE_TESTS), "directions": DIRECTIONS,
        "G": G, "L": {**L, "grouper": cb5_cdf.grouper_declaration()}, "K": K, "extract": EXTRACT, "hypotheses": {k: HYPOTHESES_CB5[k] for k in sorted(HYPOTHESES_CB5)},
        "refused_run_ids": list(REFUSED_RUN_IDS), "refused_roots": list(REFUSED_ROOTS), "census_forbidden_columns": list(CENSUS_FORBIDDEN_COLUMNS),
        "census_counts": CENSUS_COUNTS, "kinds": list(TRIAL_KINDS), "count_sources": list(COUNT_SOURCES),
    }


def canonical_sha256(obj) -> str:
    return _c3.canonical_sha256(obj)


def declaration_sha256() -> str:
    return hashlib.sha256(json.dumps(declaration_blob(), sort_keys=True, default=_default).encode()).hexdigest()


def _default(o):
    if isinstance(o, float):
        return o
    return str(o)


# ---- spec (freeze file) ----------------------------------------------------------------------------------------------


def spec_payload(census_sha256: str | None = None) -> dict:
    out: dict = {"version": VERSION, "declaration_sha256": declaration_sha256()}
    if census_sha256 is not None:
        out["census_sha256"] = census_sha256
    return out


def write_spec(path: Path = SPEC_PATH, census_sha256: str | None = None) -> dict:
    """Write the CB5 freeze file. Refuses to overwrite and refuses while a rule module is absent."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; a frozen declaration is never overwritten")
    miss = absent_modules()
    if miss:
        raise DeclarationError(f"cannot freeze: rule modules not written yet: {miss}")
    path.parent.mkdir(parents=True, exist_ok=True)
    p = spec_payload(census_sha256)
    path.write_text(json.dumps(p, indent=1, sort_keys=True) + "\n")
    return p


def require_declaration(path: Path | None = None, *, require_committed: bool = True) -> str:
    """Refuse unless the committed spec's hash equals this code's declaration hash, every rule module exists, and (when committed) the
    spec carries the census hash and has exactly one commit in its history."""
    path = Path(path) if path is not None else SPEC_PATH
    if not path.exists():
        raise DeclarationError(f"no committed declaration at {path}; counted CB5 runs are refused (CB5 freeze not committed)")
    miss = absent_modules()
    if miss:
        raise DeclarationError(f"rule modules absent: {miss}")
    if require_committed:
        if not _c3.spec_committed(path):
            raise DeclarationError(f"declaration {path} is not committed (or differs from HEAD)")
        if not _c3.single_commit(path):
            raise DeclarationError(f"declaration {path} has more than one commit: a frozen spec never changes after its first commit")
    spec = json.loads(path.read_text())
    cur = declaration_sha256()
    if spec.get("declaration_sha256") != cur:
        raise DeclarationError(f"declaration hash mismatch: committed {spec.get('declaration_sha256')} != code {cur}")
    if require_committed and not spec.get("census_sha256"):
        raise DeclarationError("the committed spec lacks census_sha256")
    return cur


# ---- dates and guards ------------------------------------------------------------------------------------------------


def epoch(s) -> float:
    if isinstance(s, datetime):
        return s.timestamp()
    t = str(s).replace("Z", "+00:00")
    if len(t) == 10:
        t += "T00:00:00+00:00"
    d = datetime.fromisoformat(t)
    return (d if d.tzinfo else d.replace(tzinfo=UTC)).timestamp()


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def refuse_run_id(run_id: str | None) -> None:
    if run_id is not None and (run_id in REFUSED_RUN_IDS or run_id.startswith("h4_seal")):
        raise RefusedRun(f"CB5 refuses run id {run_id!r} (sealed, reserved or retired data)")


def refuse_path(path: Path | str, **kw) -> None:
    """Refuse any path under a reserved CB1-CB4 root, and any path under ``cross_venue_live/`` (E009/E010 seal)."""
    parts = set(Path(path).parts)
    for r in REFUSED_ROOTS:
        if r in parts:
            raise RefusedRun(f"CB5 never reads {r}/")
    try:
        cb5_hours.refuse_path(path, **kw)
    except cb5_hours.RefusedPath as exc:
        raise RefusedRun(str(exc)) from exc


def load_rep_pin(path: Path | None = None) -> dict:
    p = Path(path) if path is not None else REP_PIN_PATH
    if not p.exists():
        raise WindowError(f"no pinned T5_rep_start at {p}")
    if path is None and not _c3.spec_committed(p):
        raise WindowError(f"{p} is not committed (or differs from HEAD)")
    doc = json.loads(p.read_text())
    if epoch(doc["t5_rep_start"]) < epoch(DATES["T5_rep_start_floor"]):
        raise WindowError("pinned T5_rep_start is before the declared floor")
    return doc


def rep_dates(path: Path | None = None) -> dict[str, float]:
    s = epoch(load_rep_pin(path)["t5_rep_start"])
    g_end = s + DATES["T5_G_rep_len_d"] * 86400.0
    l_end = s + DATES["T5_L_rep_len_d"] * 86400.0
    return {"rep_start": s, "G_rep_end": g_end, "G_read": g_end + DATES["T5_G_read_after_end_h"] * 3600.0, "L_rep_end": l_end,
            "L_out": l_end + DATES["T5_L_out_after_rep_end_d"] * 86400.0}


def pin_rep_start(freeze_commit: str, freeze_commit_time: str, first_capture_after: str, t5_rep_start: str, path: Path | None = None) -> dict:
    """Write the T5_rep_start pin once: max(2026-10-29, first complete capture >= freeze commit time + 2h)."""
    path = Path(path) if path is not None else REP_PIN_PATH
    if path.exists():
        raise WindowError(f"{path} exists; T5_rep_start is pinned once")
    sha = str(freeze_commit).strip().lower()
    if not (7 <= len(sha) <= 64) or any(c not in "0123456789abcdef" for c in sha):
        raise WindowError(f"not a commit sha: {freeze_commit!r}")
    if epoch(first_capture_after) < epoch(freeze_commit_time) + DATES["T5_rep_start_min_gap_after_freeze_h"] * 3600.0:
        raise WindowError("the first capture must be at least 2h after the freeze commit")
    expected = max(epoch(DATES["T5_rep_start_floor"]), epoch(first_capture_after))
    if abs(epoch(t5_rep_start) - expected) > 1.0:
        raise WindowError(f"T5_rep_start {t5_rep_start} is not the max rule value {iso(expected)}")
    doc = {"version": VERSION, "freeze_commit": sha, "t5_rep_start": iso(expected)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return doc


def check_G_screen_allowed(register_path: Path | None = None) -> None:
    """``screen --family G`` refuses until cost_regimes_v1.json is committed (the era rule must be known first)."""
    p = Path(register_path) if register_path is not None else cost_regimes.REGISTER_PATH
    if not p.exists():
        raise DeclarationError(f"{p} is not written: G1/G2 are refused until the cost register is committed")
    if not _c3.spec_committed(p):
        raise DeclarationError(f"{p} is not committed (or differs from HEAD)")


def check_L_screen_allowed(now: datetime | None = None, *, cb1d_rep_results: Path | None = None, cb1d_stop: Path | None = None) -> None:
    """``screen --family L`` (q0109) refuses before ``T_CB1D_rep`` (2026-11-09) and until CB1-D's replication results are committed or
    CB1-D is recorded as stopped (CB5-L overlap hold, challenger round 1 item 11)."""
    now = now or datetime.now(UTC)
    if now.timestamp() < epoch(DATES["T_CB1D_rep"]):
        raise TooEarly(f"the CB5-L screen is refused before {DATES['T_CB1D_rep']} (CB1-D sealed replication window)")
    res = Path(cb1d_rep_results) if cb1d_rep_results is not None else _cb1d_results()
    stop = Path(cb1d_stop) if cb1d_stop is not None else CB1D_STOP_PATH
    if not (res.exists() or stop.exists()):
        raise TooEarly("the CB5-L screen needs CB1-D's replication results or its recorded stop (seals/cb1_d_stopped.json)")


def _cb1d_results() -> Path:
    from . import forecast

    return forecast.ROOT / "data-dumps" / "research_lab" / "creative_batch1" / "D_rep" / "results.json"


def check_rep_allowed(family: str, now: datetime | None = None, pin_path: Path | None = None) -> None:
    """``replicate --family G`` refuses before T5_G_read; ``--family L`` before T5_L_rep_end."""
    now = now or datetime.now(UTC)
    d = rep_dates(pin_path)
    need = d["G_read"] if family == "G" else d["L_rep_end"]
    if now.timestamp() < need:
        raise TooEarly(f"replicate --family {family} is refused before {iso(need)}")


def check_outcome_allowed(family: str, now: datetime | None = None, pin_path: Path | None = None) -> None:
    """``fetch-outcomes --family L`` refuses before T5_L_out; ``--family G`` before T5_G_read + 30 d."""
    now = now or datetime.now(UTC)
    d = rep_dates(pin_path)
    need = d["L_out"] if family == "L" else d["G_read"] + 30 * 86400.0
    if now.timestamp() < need:
        raise TooEarly(f"outcomes for {family} are refused before {iso(need)}")


# ---- grouper hash (must be committed before q0104 reads any title) ----------------------------------------------------


def grouper_sha256() -> str:
    """sha256 of the CDF grouper: its declared rule text and the source of every function defined in ``cb5_cdf``."""
    src = {}
    for name, obj in sorted(vars(cb5_cdf).items()):
        if (inspect.isfunction(obj) or inspect.isclass(obj)) and getattr(obj, "__module__", None) == cb5_cdf.__name__:
            src[name] = hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()
    return hashlib.sha256(json.dumps({"declaration": cb5_cdf.grouper_declaration(), "sources": src}, sort_keys=True, default=str).encode()).hexdigest()


def write_grouper_seal(path: Path | None = None) -> dict:
    p = Path(path) if path is not None else GROUPER_SEAL_PATH
    if p.exists():
        raise FileExistsError(f"{p} exists; the grouper hash is sealed once (a revision after a failed audit is a new seal file)")
    doc = {"version": VERSION, "grouper": cb5_cdf.GROUPER_VERSION, "grouper_sha256": grouper_sha256()}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return doc


def check_grouper_committed(path: Path | None = None, *, require_committed: bool = True) -> str:
    """``cdf-frame`` refuses until the committed seal equals this code's grouper hash."""
    p = Path(path) if path is not None else GROUPER_SEAL_PATH
    if not p.exists():
        raise DeclarationError(f"no grouper seal at {p}: cdf-frame is refused until the grouper hash is committed")
    if require_committed and not _c3.spec_committed(p):
        raise DeclarationError(f"{p} is not committed (or differs from HEAD)")
    want, got = json.loads(p.read_text()).get("grouper_sha256"), grouper_sha256()
    if want != got:
        raise DeclarationError(f"grouper hash mismatch: sealed {want} != code {got}")
    return got
