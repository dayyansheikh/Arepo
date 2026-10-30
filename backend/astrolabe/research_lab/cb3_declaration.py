# ruff: noqa: E501
"""CB3 declaration (docs/research_lab/CREATIVE_BATCH_3.md, DRAFT-REVISED a767ab8 + challenger round 1 response).

Single source of every CB3 rule, band, floor, date, placebo and estimator. ``cb3_quote_vacuum`` (family A) and
``cb3_maker`` (family B) import their constants from here; ``declaration_sha256()`` hashes all of it, so changing any
of them changes the hash and the runner refuses to count until ``model_specs/cb3_v1.json`` is re-committed.

No threshold, formula or window here may be changed to obtain a pass. Frozen numeric cuts that only exist after the
census (RT decile cut, activity terciles) are NOT part of the hash; they live in the committed spec's ``frozen_cuts``.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from . import economics, provenance

VERSION = "cb3-v1"
LABEL = "EXPLORATORY CB3 quote-vacuum recovery and selective maker"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "cb3_v1.json"
REP_PIN_PATH = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb3_t_rep_start.json"
J4R_PIN_PATH = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "j4r_window.json"

KIND_TEST, KIND_REP, KIND_PROSPECTIVE, KIND_DESCRIPTIVE = "cb3_test", "cb3_replication", "cb3_prospective", "cb3_descriptive"
TRIAL_KINDS = (KIND_TEST, KIND_REP, KIND_PROSPECTIVE, KIND_DESCRIPTIVE)

# ---- seeds ------------------------------------------------------------------------------------------------------
SEED_BOOT = 316
SEED_PLACEBO = 317
SEED_RANDOM_FILTER = 318
N_BOOT = 2000
PLACEBO_DRAWS = 20
RANDOM_FILTER_DRAWS = 200

# ---- dates (UTC) ------------------------------------------------------------------------------------------------
DATES = {
    "T3_draft": "2026-10-16T04:18:00Z",
    "T3_A_dev_end": "2026-10-15T21:00:00Z",
    "T_J4R_start": "2026-10-16T00:00:00Z",
    "T3_dev_end": "2026-10-25T00:00:00Z",
    "T3_rep_start_floor": "2026-10-27T00:00:00Z",
    "T3_rep_len_d": 28,
    "T3_P_len_d": 28,
    "T3_mark_lag_h": 12,
    "T3_res_out_d": 30,
    "T3_rep_start_min_dev_gap_d": 2,
    "rotation_suspend_date": "2026-11-10",
}

# ---- stage rules ------------------------------------------------------------------------------------------------
ALPHA_STAGE1 = 0.01
ALPHA_STAGE2 = 0.05
BY_Q = 0.10
MIN_CLUSTERS = 30  # event-type cluster ways
MIN_UNITS = 100
A_MIN_ONSETS = 1000
A_MIN_CAPTURE_CLUSTERS = 30
G_NORMAL, G_MIN = 30, 15  # CB2 small-G rule for the UTC-day way (never the >= 30 rule)
TOP_CLUSTERS_DROPPED = 5
PLACEBO_BIAS_FRAC = 0.5
STAGE1_RANDOM_PCT, STAGE2_RANDOM_PCT = 99.0, 95.0
CATEGORY_SCOPE = "non_sports"

# ---- family A (CH35) --------------------------------------------------------------------------------------------
A = {
    "gap_h": [1.5, 3.0],
    "tight_spread_max": 0.10,
    "tight_mid_band": [0.02, 0.98],
    "onset_min": 0.05,
    "onset_other_side_max": 0.01,
    "recovery_horizon_captures": [2, 3, 4],
    "displacement_bands_c": [[5, 10], [10, 20], [20, 100]],
    "sweep_confirm_min": 0.03,
    "persist_far_min": 0.03,
    "persist_other_side_max": 0.01,
    "a3_vacuum_max_per_pass": 300,
    "a3_life_s": 7200,
    "a3_order_shares": 5.0,
    "a3_queue_ahead": 0.0,
    "clip": [0.001, 0.999],
    "unrecovered_coding": "m_T := m_(i+1); closed without valid payout := unrecovered",
    "closed_with_payout": "m_T := Y",
    "gap_break": "exclude (counted)",
    "unit": "(market, onset capture)",
    "placebo": "real onsets kept; mid rebuilt from i+1 as martingale of market-pooled mid increments drawn with replacement; observed half-spread path kept; T rule re-applied",
    "placebo_reading": "void check and bias rule on A1 (R); A2's placebo G is a construction check (expected negative), family status follows A1",
}
A_FLOORS = {"A1": 0.60, "A2": 0.005, "A3_net": 0.005, "A3_fill_rate": 0.02}  # price units (A2/A3: 0.50c)
A1_NULL = 0.50

# ---- shared paper maker (A3 and all B) --------------------------------------------------------------------------
MAKER = {
    "order_shares": 5.0,
    "life_s": 7200,
    "mark_s": 21600,
    "mark_secondary_s": 7200,
    "prospective_mark_next_pass_within_s": 14400,
    "spread_max": 0.10,
    "mid_band": [0.10, 0.90],
    "end_at_margin_s": 28800,
    "visible_prints": 500,
    "fill_rule_primary": "queue (displayed size at level + 5, all-or-nothing); touch rule must agree in sign",
    "maker_fee": 0.0,
    "rebate_share": dict(economics.REBATE_SHARE),
    "rebate_unknown_category": 0.0,
    "rebate_fee_policy_prospective": "income: minimum of the as-of schedule rate and the docs rate; unknown schedule, unknown category or fees disabled = 0",
    "rebate_formula": "rho_cat * r_cat * P * (1 - P) per filled share, pro rata",
    "rebate_halved_binding": True,
    "worst_case_unavailable": "only the side with the lower mark-out fills, far touch at mark time, no rebate; history far touch = mark -/+ entry half-spread",
    "worst_case_no_mark": "buy: value 0 (mo = -P); sell: value 1 (mo = -(1-P))",
    "history_pmxt_mark_check_s": 14400,
    "weights": "unweighted primary; design-weighted must agree in sign",
    "rewards_in_primary": False,
}

# ---- family B (CH39 / CH40 / CH41-narrow) -----------------------------------------------------------------------
B = {
    "large_order_pct": 90.0,
    "large_order_window_orders": 200,
    "large_order_min_prior": 50,
    "post_window_s": 1800,
    "w_sensitivity_min": [5, 15, 60],
    "lf_cut": 0.90,
    "rt_min_trades": 4,
    "rt_net_frac": 0.10,
    "rt_wallet_window_s": 86400,
    "rt_share_window_s": 21600,
    "rt_min_prints": 20,
    "rt_top_quantile": 0.90,
    "activity_window_s": 86400,
    "activity_terciles": 3,
    "depth_deciles": 10,
    "controls_mech": ["spread", "log1p_depth_own", "abs_chg_24h", "price_band_dummies", "side_dummy", "category_fe"],
    "controls_b5_extra": ["log1p_depth_both", "log1p_taker_notional_24h"],
    "b3_week_fe": True,
    "estimator": "expanding-past within-market slope (bounce_decomp.expanding_demean on regressor and controls, raw target, first row per market dropped)",
    "b5_unit": "quote opportunity, y = EV per quote (sum net x 5 / 10 shares-sides, 0 if unfilled)",
    "b1_placebo": "circular shift of each market's large-order time stream by a uniform offset in [1 d, span - 1 d]",
    "b3_placebo": "within-market permutation of life fraction across the market's fills",
    "b5_placebo": "within-market permutation of round-trip share across the market's opportunities",
    "b4_population": "opportunities with life fraction defined",
    "b2_population": "classifiable markets (>= 50 taker orders visible before t)",
    "b6_population": "opportunities with RT defined",
    "b2_cancel_rule": "cancel both sides at the first large order after posting; a fill at or before the cancel time counts",
    "random_filter": "same count per stratum; B2 offsets drawn from the real offsets of the stratum",
    "strata": ["spread_band", "price_band", "category", "activity_tercile"],
    "strata_b6_extra": ["depth_decile_1c"],
    "spread_bands": [0.02, 0.05, 0.10],
    "price_bands": [0.10, 0.30, 0.50, 0.70, 0.90],
    "orders_no_tx_group": ["ts", "wallet_hash", "side", "outcome_index"],
}
B_FLOORS = {"B1": -0.005, "B3": -0.010, "B5": 0.010, "B2": 0.0025, "B4": 0.0025, "B6": 0.0025}  # price units per filled share / per unit

# ---- hypotheses -------------------------------------------------------------------------------------------------
HYPOTHESES_CB3: dict[str, dict] = {
    "A1": {"family": "A", "kind": "mechanism", "hypothesis": "CH35", "unit": "onset", "statistic": "R = 1 - sum s(m_T - m_i) / sum |D|",
           "direction": "R > 0.50", "sign": 1, "floor": A_FLOORS["A1"], "null": A1_NULL, "estimator": "ratio of sums, delta-method CR1 per way, boot_ratio CI",
           "ways": ["event", "dep_group", "onset_capture"], "stage1": "dev captures < T3_A_dev_end", "stage2": "rep window", "robust": ["top5_clusters", "sweep_confirmed"]},
    "A2": {"family": "A", "kind": "mechanism", "hypothesis": "CH35", "unit": "onset", "statistic": "G = mean(q - m_T) (ask vacuum) | mean(m_T - q) (bid vacuum), cents",
           "direction": "G > 0", "sign": 1, "floor": A_FLOORS["A2"], "estimator": "mean, CR1 per way", "ways": ["event", "dep_group", "onset_capture"],
           "stage1": "dev captures < T3_A_dev_end", "stage2": "rep window", "robust": ["top5_clusters", "sweep_confirmed"]},
    "A3": {"family": "A", "kind": "economic", "hypothesis": "CH35", "unit": "filled re-quote", "statistic": "net = mo + rebate per filled share, B mark",
           "direction": "net > 0", "sign": 1, "floor": A_FLOORS["A3_net"], "fill_rate_floor": A_FLOORS["A3_fill_rate"], "stage1": "none (enters Stage 2 iff A1 advanced)",
           "stage2": "rep window", "stageP": "P window", "ways": ["event", "dep_group", "onset_capture"],
           "robust": ["top5_clusters", "weighted_sign", "touch_rule_sign", "rebate_halved", "worst_case_unavailable", "truncated_life"]},
    "B1": {"family": "B", "kind": "mechanism", "hypothesis": "CH39", "unit": "fill (classifiable markets)", "statistic": "expanding-past within-market slope of net on post-large-print",
           "direction": "beta39 < 0", "sign": -1, "floor": B_FLOORS["B1"], "ways": ["event", "dep_group", "utc_day"], "placebo": B["b1_placebo"]},
    "B2": {"family": "B", "kind": "economic", "hypothesis": "CH39", "unit": "fill of the retreat maker (classifiable markets)", "statistic": "mean net per filled share",
           "direction": "> 0", "sign": 1, "floor": B_FLOORS["B2"], "ways": ["event", "dep_group", "utc_day"], "filter": B["b2_cancel_rule"]},
    "B3": {"family": "B", "kind": "mechanism", "hypothesis": "CH40", "unit": "fill", "statistic": "expanding-past within-market slope of net on life fraction, calendar-week FE",
           "direction": "beta40 < 0", "sign": -1, "floor": B_FLOORS["B3"], "ways": ["event", "dep_group", "utc_day"], "placebo": B["b3_placebo"]},
    "B4": {"family": "B", "kind": "economic", "hypothesis": "CH40", "unit": "fill of the schedule maker", "statistic": "mean net per filled share",
           "direction": "> 0", "sign": 1, "floor": B_FLOORS["B4"], "ways": ["event", "dep_group", "utc_day"], "filter": "no quote with LF(t) >= 0.90"},
    "B5": {"family": "B", "kind": "mechanism", "hypothesis": "CH41-narrow", "unit": "quote opportunity (RT defined)", "statistic": "expanding-past within-market slope of EV per quote on RT",
           "direction": "beta41 > 0", "sign": 1, "floor": B_FLOORS["B5"], "ways": ["event", "dep_group", "utc_day"], "placebo": B["b5_placebo"]},
    "B6": {"family": "B", "kind": "economic", "hypothesis": "CH41-narrow", "unit": "fill of the top-decile maker", "statistic": "mean net per filled share",
           "direction": "> 0", "sign": 1, "floor": B_FLOORS["B6"], "ways": ["event", "dep_group", "utc_day"], "filter": "RT in the frozen top decile"},
}
FAMILY_TESTS = {"A": ("A1", "A2"), "B": ("B1", "B2", "B3", "B4", "B5", "B6")}
STAGE2_TESTS = {"A": ("A1", "A2", "A3"), "B": ("B1", "B2", "B3", "B4", "B5", "B6")}
STAGEP_TESTS = ("A3", "B2", "B4", "B6")
MECHANISM_TESTS = ("A1", "A2", "B1", "B3", "B5")
ECONOMIC_TESTS = ("A3", "B2", "B4", "B6")

REFUSED_RUN_IDS = ("h1_first", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather")
CENSUS_FORBIDDEN_COLUMNS = ("outcome_prices", "uma_status", "mark_6h", "mark_2h", "m_T", "mid_T", "mid_after", "net", "mo", "mark6", "mo6", "mo2", "net6", "net2",
                            "net6_half", "wc_mo", "mark_pmxt", "net_pmxt", "num", "g", "T_k")
CENSUS_NEVER_READS = "6h/2h marks, T-capture mids of A onsets, any price after a fill; outcome columns dropped before population code"


class Cb3Error(RuntimeError):
    """Base of every CB3 guard refusal."""


class DeclarationError(Cb3Error):
    pass


class RefusedRun(Cb3Error):
    pass


class WindowError(Cb3Error):
    pass


class TooEarly(Cb3Error):
    pass


def epoch(s: str) -> float:
    t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- hash --------------------------------------------------------------------------------------------------------


FOLLOWUP_CONSTANTS = {"frac": 0.5, "limit": 1000, "max_pages": 5, "vacuum_max": 300, "rps": 4.0, "budget_s": 540.0, "max_429": 50,
                      "backoff": [1.0, 30.0], "r429_window_s": 600.0, "r429_halve_frac": 0.01, "subsample": "sha256(seed|market_id)/2^256 < frac",
                      "order": "seeded permutation", "window": "(previous capture start, request time], start/end inclusive seconds"}

# (module, name) of imported rule-applying functions whose source is part of the declaration (freeze-check fix 3)
IMPORTED_RULE_FUNCTIONS = (
    ("cb1_history", "queue_fill"), ("cb1_history", "asof_quote"), ("cb1_history", "trade_condition_state"), ("cb1_history", "buys_longshot"),
    ("cb1_history", "open_at"), ("cb1_history", "oldest_or_inf"), ("cb1_history", "is_sports"), ("cb1_history", "iso_week"),
    ("bounce_decomp", "h_tight_mask"), ("bounce_decomp", "expanding_demean"), ("bounce_decomp", "_expanding_resid"), ("bounce_decomp", "_two_sided"),
    ("cb2_weather", "small_g_pvalue"), ("cb2_weather", "_cluster_sums"), ("economics", "fee_spec"), ("economics", "resolve_rate"),
    ("economics", "parse_fee_schedule"), ("economics", "boot_ratio"), ("battery", "_cr_var_of_sum"), ("wallet_sidecar", "hash_wallet"),
    # helpers called by hashed functions (re-check HOLD fix a)
    ("cb1_history", "load_sample"), ("cb1_history", "drop_outcome_columns"), ("cb1_history", "load_books"), ("history_backfill", "load_prices"),
)
CB3_RULE_MODULES = ("cb3_declaration", "cb3_common", "cb3_quote_vacuum", "cb3_maker", "cb3_followup", "cb3_quote_state")
RUNNER_PATH = provenance.REPO_ROOT / "backend" / "scripts" / "run_cb3.py"  # stage windows, origin_before, Holm k, census clamps: hashed as a file


def source_hashes() -> dict[str, str]:
    """sha256 of the source of every rule-applying function: all functions and classes defined in the cb3 analysis modules plus the
    imported ones in IMPORTED_RULE_FUNCTIONS (and the module-level constants they use are covered by the constants in the blob)."""
    import importlib
    import inspect

    out: dict[str, str] = {}
    for mod in CB3_RULE_MODULES:
        m = importlib.import_module(f"{__package__}.{mod}")
        for name, obj in sorted(vars(m).items()):
            if (inspect.isfunction(obj) or inspect.isclass(obj)) and getattr(obj, "__module__", None) == m.__name__:
                out[f"{mod}.{name}"] = hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()
    for mod, name in IMPORTED_RULE_FUNCTIONS:
        m = importlib.import_module(f"{__package__}.{mod}")
        out[f"{mod}.{name}"] = hashlib.sha256(inspect.getsource(getattr(m, name)).encode()).hexdigest()
    out["scripts/run_cb3.py"] = provenance.sha256_file(RUNNER_PATH)
    return out


def declaration_blob() -> dict:
    return {
        "sources": source_hashes(),
        "followup_constants": FOLLOWUP_CONSTANTS,
        "version": VERSION,
        "seeds": {"boot": SEED_BOOT, "placebo": SEED_PLACEBO, "random_filter": SEED_RANDOM_FILTER},
        "draws": {"n_boot": N_BOOT, "placebo": PLACEBO_DRAWS, "random_filter": RANDOM_FILTER_DRAWS},
        "dates": DATES,
        "stage": {"alpha1": ALPHA_STAGE1, "alpha2": ALPHA_STAGE2, "by_q": BY_Q, "min_clusters": MIN_CLUSTERS, "min_units": MIN_UNITS,
                  "a_min_onsets": A_MIN_ONSETS, "a_min_capture_clusters": A_MIN_CAPTURE_CLUSTERS, "g_normal": G_NORMAL, "g_min": G_MIN,
                  "top_clusters_dropped": TOP_CLUSTERS_DROPPED, "placebo_bias_frac": PLACEBO_BIAS_FRAC,
                  "random_pct": [STAGE1_RANDOM_PCT, STAGE2_RANDOM_PCT], "category_scope": CATEGORY_SCOPE},
        "A": A, "A_floors": A_FLOORS, "A1_null": A1_NULL,
        "maker": MAKER,
        "B": B, "B_floors": B_FLOORS,
        "hypotheses": {k: HYPOTHESES_CB3[k] for k in sorted(HYPOTHESES_CB3)},
        "families": {k: list(v) for k, v in FAMILY_TESTS.items()},
        "stage2_tests": {k: list(v) for k, v in STAGE2_TESTS.items()},
        "stageP_tests": list(STAGEP_TESTS),
        "refused_run_ids": list(REFUSED_RUN_IDS),
        "census_forbidden_columns": list(CENSUS_FORBIDDEN_COLUMNS),
        "fee_table": {"docs_rate": economics.DOCS_CATEGORY_RATE, "version": economics.FEE_TABLE_VERSION},
        "kinds": list(TRIAL_KINDS),
    }


def declaration_sha256() -> str:
    return hashlib.sha256(json.dumps(declaration_blob(), sort_keys=True, default=float).encode()).hexdigest()


def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=float).encode()).hexdigest()


def spec_payload(frozen_cuts: dict | None = None, census_sha256: str | None = None) -> dict:
    out = {"version": VERSION, "declaration_sha256": declaration_sha256()}
    if frozen_cuts is not None:
        out["frozen_cuts"] = frozen_cuts
        out["frozen_cuts_sha256"] = canonical_sha256(frozen_cuts)
    if census_sha256 is not None:
        out["census_sha256"] = census_sha256
    return out


def write_spec(path: Path = SPEC_PATH, frozen_cuts: dict | None = None, census_sha256: str | None = None) -> dict:
    """Write the CB3 freeze file (declaration hash, frozen cuts, their sha256 and the census.json sha256). Refuses to overwrite."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; a frozen declaration is never overwritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    p = spec_payload(frozen_cuts, census_sha256)
    path.write_text(json.dumps(p, indent=1, sort_keys=True) + "\n")
    return p


def _rel(path: Path) -> str | None:
    try:
        return str(Path(path).resolve().relative_to(provenance.REPO_ROOT.resolve()))
    except ValueError:
        return None


def spec_committed(path: Path) -> bool:
    """True if the file is tracked by git and identical to HEAD."""
    rel = _rel(path)
    if rel is None:
        return False
    cwd = provenance.REPO_ROOT
    if provenance._git(["ls-files", "--error-unmatch", rel], cwd) is None:
        return False
    return provenance._git(["diff", "--quiet", "HEAD", "--", rel], cwd) is not None


def single_commit(path: Path) -> bool:
    """The blob has exactly one commit in its history: a frozen spec can never change after its first commit."""
    rel = _rel(path)
    if rel is None:
        return False
    out = provenance._git(["log", "--format=%H", "--follow", "--", rel], provenance.REPO_ROOT)
    return bool(out) and len([x for x in str(out).split() if x]) == 1


def require_declaration(path: Path | None = None, *, require_committed: bool = True) -> str:
    """Refuse unless the committed spec's hash equals this code's declaration hash. When committed it must also carry the cuts and
    census hashes and have exactly one commit in its history (immutable after its first commit)."""
    path = Path(path) if path is not None else SPEC_PATH
    if not path.exists():
        raise DeclarationError(f"no committed declaration at {path}; counted CB3 runs are refused (CB3 freeze not committed)")
    if require_committed:
        if not spec_committed(path):
            raise DeclarationError(f"declaration {path} is not committed (or differs from HEAD)")
        if not single_commit(path):
            raise DeclarationError(f"declaration {path} has more than one commit: a frozen spec never changes after its first commit")
    spec = json.loads(path.read_text())
    cur = declaration_sha256()
    if spec.get("declaration_sha256") != cur:
        raise DeclarationError(f"declaration hash mismatch: committed {spec.get('declaration_sha256')} != code {cur}")
    if require_committed:
        for k in ("frozen_cuts", "frozen_cuts_sha256", "census_sha256"):
            if not spec.get(k):
                raise DeclarationError(f"the committed spec lacks {k}")
    if spec.get("frozen_cuts") is not None and spec.get("frozen_cuts_sha256") != canonical_sha256(spec["frozen_cuts"]):
        raise DeclarationError("frozen_cuts_sha256 does not match frozen_cuts")
    return cur


def load_frozen_cuts(path: Path | None = None) -> dict:
    path = Path(path) if path is not None else SPEC_PATH
    spec = json.loads(Path(path).read_text()) if Path(path).exists() else {}
    cuts = spec.get("frozen_cuts")
    if not cuts:
        raise DeclarationError("the committed spec carries no frozen_cuts (RT top-decile cut, activity terciles); pin them at the freeze")
    if spec.get("frozen_cuts_sha256") != canonical_sha256(cuts):
        raise DeclarationError("frozen_cuts_sha256 does not match frozen_cuts")
    return cuts


def cuts_sha256(path: Path | None = None) -> str | None:
    spec = json.loads(Path(path if path is not None else SPEC_PATH).read_text())
    return spec.get("frozen_cuts_sha256")


def verify_cuts_against_census(spec_path: Path, census_path: Path) -> None:
    """The spec's census_sha256 must equal the sha256 of census.json, and the pinned cuts must equal that census's
    ``frozen_cuts_proposal`` (rt_top_decile_cut, activity_tercile_cuts)."""
    spec = json.loads(Path(spec_path).read_text())
    census_path = Path(census_path)
    if not census_path.exists():
        raise DeclarationError(f"{census_path} not found: the frozen cuts cannot be checked against the census")
    if provenance.sha256_file(census_path) != spec.get("census_sha256"):
        raise DeclarationError("census.json sha256 differs from the spec's census_sha256")
    census = json.loads(census_path.read_text())
    if not census.get("declaration_sha256") or census.get("declaration_sha256") != spec.get("declaration_sha256"):
        raise DeclarationError("census.json declaration_sha256 differs from the spec's declaration_sha256 (census made under another declaration)")
    prop = (census.get("B") or {}).get("frozen_cuts_proposal") or {}
    cuts = load_frozen_cuts(spec_path)
    for k in ("rt_top_decile_cut", "activity_tercile_cuts"):
        if prop.get(k) != cuts.get(k):
            raise DeclarationError(f"frozen cut {k} differs from the census proposal")


def dev_window_end(fu_start: float, j4r_end: float) -> float:
    """Prospective dev window end: T3_dev_end moved forward by whole UTC days until at least 3 full days lie in
    [max(fu_start, j4r_end), end)."""
    end = epoch(DATES["T3_dev_end"])
    start = max(fu_start, j4r_end)
    while end - start < 3 * 86400.0:
        end += 86400.0
    return end


# ---- guards ------------------------------------------------------------------------------------------------------


def refuse_run_id(run_id: str | None) -> None:
    if run_id is None:
        return
    if run_id in REFUSED_RUN_IDS or str(run_id).startswith("h4_seal"):
        raise RefusedRun(f"CB3 refuses run id {run_id!r} (sealed, reserved or retired data)")


def j4r_window(pin_path: Path | None = None) -> tuple[float, float]:
    """[T_J4R start, T_J4R_end) from the COMMITTED pin ``seals/j4r_window.json`` (derived from J4-R's frozen declaration, not from the
    mutable q0035 queue spec). While the pin is not ``final`` (J4-R has not run, its exit-3 rule may still move the end) the end is
    +inf: CB3 refuses every capture at or after the J4-R start. Fails closed: an unreadable or uncommitted pin is a refusal."""
    p = Path(pin_path) if pin_path is not None else J4R_PIN_PATH
    try:
        doc = json.loads(p.read_text())
        lo = epoch(doc["t_j4r_start"])
        hi = epoch(doc["t_j4r_end"])
        final = bool(doc.get("final", False))
    except (OSError, ValueError, KeyError) as exc:
        raise WindowError(f"cannot read the J4-R window pin {p}: {exc}") from exc
    if pin_path is None and not spec_committed(p):
        raise WindowError(f"{p} is not committed (or differs from HEAD); the J4-R window pin must be committed")
    if hi < epoch(doc.get("declared_end", doc["t_j4r_end"])):
        raise WindowError("pinned T_J4R_end is before the declared end")
    return lo, (hi if final else math.inf)


def in_j4r(start_epoch: float, window: tuple[float, float] | None = None) -> bool:
    lo, hi = window if window is not None else j4r_window()
    return lo <= float(start_epoch) < hi


def check_capture_allowed(start_epoch: float, *, purpose: str, window: tuple[float, float] | None = None) -> None:
    """No analysis or census row tied to a capture in T_J4R; A dev screens nothing at or after T3_A_dev_end."""
    if in_j4r(start_epoch, window):
        raise WindowError(f"capture at {iso(start_epoch)} lies in T_J4R; CB3 never reads it ({purpose})")
    if purpose == "screen_A" and start_epoch >= epoch(DATES["T3_A_dev_end"]):
        raise WindowError(f"capture at {iso(start_epoch)} is at or after T3_A_dev_end; the A screen refuses it")


def load_rep_pin(path: Path | None = None) -> dict:
    """The pinned T3_rep_start. The default pin must be committed and identical to HEAD."""
    p = Path(path) if path is not None else REP_PIN_PATH
    if not p.exists():
        raise WindowError(f"no pinned T3_rep_start at {p}")
    if path is None and not spec_committed(p):
        raise WindowError(f"{p} is not committed (or differs from HEAD)")
    doc = json.loads(p.read_text())
    if epoch(doc["t3_rep_start"]) < epoch(DATES["T3_rep_start_floor"]):
        raise WindowError("pinned T3_rep_start is before the declared floor")
    return doc


def window_bounds(window: str, pin_path: Path | None = None) -> tuple[float, float]:
    """``rep`` and ``P`` windows from the committed pin; ``dev_A`` is everything before T3_A_dev_end."""
    if window == "dev_A":
        return 0.0, epoch(DATES["T3_A_dev_end"])
    pin = load_rep_pin(pin_path)
    r0 = epoch(pin["t3_rep_start"])
    r1 = r0 + DATES["T3_rep_len_d"] * 86400.0
    if window == "rep":
        return r0, r1
    if window == "P":
        return r1, r1 + DATES["T3_P_len_d"] * 86400.0
    raise WindowError(f"unknown window {window!r}")


def check_stage_allowed(stage: str, now: datetime | None = None, pin_path: Path | None = None) -> None:
    """``replicate`` refuses before T3_rep_end + mark lag; ``stagep`` before T3_P_end + mark lag; ``resolution`` before T3_res_out."""
    now_t = (now or datetime.now(UTC)).timestamp()
    lag = DATES["T3_mark_lag_h"] * 3600.0
    if stage == "replicate":
        need = window_bounds("rep", pin_path)[1] + lag
    elif stage == "stagep":
        need = window_bounds("P", pin_path)[1] + lag
    elif stage == "resolution":
        need = window_bounds("P", pin_path)[1] + DATES["T3_res_out_d"] * 86400.0
    else:
        return
    if now_t < need:
        raise TooEarly(f"{stage} is refused before {iso(need)}")


def pin_rep_start(freeze_commit: str, freeze_commit_time: str, first_capture_after: str, rotation_verified_day: str, t3_rep_start: str,
                  path: Path | None = None, *, verify_git: bool = True) -> dict:
    """Write the T3_rep_start pin once. Checks the max rule of section 1.2: max(floor, first complete capture >= freeze commit time + 2h,
    T3_dev_end + 2 d, first UTC day with verified rotation) and that the freeze commit exists and holds the spec."""
    path = Path(path) if path is not None else REP_PIN_PATH
    if path.exists():
        raise WindowError(f"{path} exists; T3_rep_start is pinned once")
    sha = str(freeze_commit).strip().lower()
    if not (7 <= len(sha) <= 64) or any(c not in "0123456789abcdef" for c in sha):
        raise WindowError(f"not a commit sha: {freeze_commit!r}")
    if epoch(first_capture_after) < epoch(freeze_commit_time) + 7200.0:
        raise WindowError("the first capture must be at least 2h after the freeze commit")
    expected = max(epoch(DATES["T3_rep_start_floor"]), epoch(first_capture_after), epoch(DATES["T3_dev_end"]) + DATES["T3_rep_start_min_dev_gap_d"] * 86400.0,
                   epoch(rotation_verified_day))
    if abs(epoch(t3_rep_start) - expected) > 1.0:
        raise WindowError(f"T3_rep_start {t3_rep_start} is not the max rule value {iso(expected)}")
    if verify_git:
        rel = _rel(SPEC_PATH)
        if provenance._git(["cat-file", "-e", f"{sha}^{{commit}}"], provenance.REPO_ROOT) is None or provenance._git(["show", f"{sha}:{rel}"], provenance.REPO_ROOT) is None:
            raise WindowError("the freeze commit does not exist or does not contain the committed spec")
    doc = {"version": VERSION, "freeze_commit": sha, "freeze_commit_time": freeze_commit_time, "first_capture_after": first_capture_after,
           "rotation_verified_day": rotation_verified_day, "t3_rep_start": iso(expected), "t3_rep_end": iso(expected + DATES["T3_rep_len_d"] * 86400.0),
           "rule": "max(floor, first complete capture >= freeze commit + 2h, T3_dev_end + 2d, first UTC day with verified rotation)"}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return doc
