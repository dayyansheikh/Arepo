# ruff: noqa: E501
"""CB4 declaration (docs/research_lab/CREATIVE_BATCH_4.md, DRAFT + challenger round 1 + data freeze checks).

Single source of every CB4 analysis rule, window, band, margin, floor, gate, date, placebo and estimator, hashed by
``declaration_sha256()``. The pattern mirrors ``cb3_declaration``: the hash covers the constants AND the source of every
rule-applying function (the CB4 analysis modules, the CB4 data rule functions and the imported cost/statistics helpers), so a
code change that alters a rule changes the hash and the runner refuses to count until ``model_specs/cb4_v1.json`` is
re-committed. A rule module that does not exist yet is recorded as ``ABSENT`` and :func:`require_declaration` refuses while any is
absent: the freeze cannot be committed before the analysis code exists.

No threshold, formula or window here may be changed to obtain a pass. Quantities that only exist after the census (the
``H`` hour count, ``rho`` if the venue page differs, the extended UMA status set) live in the committed spec's
``census_pins`` and are bound by ``census_sha256``; the floors are never revised from the census.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

from . import cb3_declaration as _c3
from . import cb4_data, cost_regimes, economics, provenance

VERSION = "cb4-v1"
LABEL = "EXPLORATORY CB4 pre-close dump, series roll, taker-tier and fee-era measurements"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "cb4_v1.json"
REP_PIN_PATH = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "cb4_t_rep_start.json"
H5_SEAL_COPY = provenance.REPO_ROOT / "docs" / "research_lab" / "seals" / "h5_cb1_SEAL.json"

KIND_TEST, KIND_REP, KIND_MEASURE, KIND_DESCRIPTIVE = "cb4_test", "cb4_replication", "cb4_measurement", "cb4_descriptive"
TRIAL_KINDS = (KIND_TEST, KIND_REP, KIND_MEASURE, KIND_DESCRIPTIVE)
COUNT_SOURCES = ("creative_batch_4:C", "creative_batch_4:S", "creative_batch_4:M")


class DeclarationError(RuntimeError):
    """The committed CB4 declaration is missing, uncommitted, mutated or does not match the code."""


class WindowError(RuntimeError):
    """A date window or pin rule is violated."""


class RefusedRun(RuntimeError):
    """A sealed, reserved or retired run id or path."""


# ---- dates (section 1.2) -----------------------------------------------------------------------------------------

DATES = {
    "T4_dev_start": "2026-10-11T12:00:00Z",
    "T4_dev_end": "2026-10-25T00:00:00Z",
    "T4_dev_out": "2026-11-08T00:00:00Z",
    "T4_rep_start_floor": "2026-10-27T00:00:00Z",
    "T4_rep_start_min_gap_after_freeze_h": 2,
    "T4_rep_len_d": 28,
    "T4_rep_out_after_rep_end_d": 21,
    "T_seal": cb4_data.T_SEAL,
    "D_tier": "2026-05-28",
    "W_pre_N": ["2026-04-30T00:00:00Z", "2026-05-28T00:00:00Z"],
    "W_post_N": [["2026-05-30T00:00:00Z", "2026-06-12T00:00:00Z"], ["2026-06-18T00:00:00Z", "2026-07-02T00:00:00Z"]],
    "W_pilot_N": ["2026-07-12T00:00:00Z", "2026-08-10T00:00:00Z"],
    "pmxt_window": list(cost_regimes.PMXT_WINDOW),
    "D_fee_S": cost_regimes.FEE_ERAS["sports"], "D_fee_O": cost_regimes.FEE_ERAS["other"],
    "periods": [list(p) for p in cb4_data.ERA_PERIODS],
    "era_post_buffer_d": cost_regimes.ERA_BUFFER_D,
    "L_E_h": 72, "D_pl_E": "2026-01-15",
    "R_from": cb4_data.SERIES_ROLL_FROM, "R_to": "min(T_fetch7 - 3d, T_seal) - 2d",
    "D_split4_rule": "smallest UTC date d with |{r: date(t0_r) >= d}| <= 0.40 |U|; embargo 3 days before d",
}

# ---- statistics, stages, counting (sections 2.3-2.6) --------------------------------------------------------------

SEED_BOOT, SEED_PLACEBO = 416, 417
N_BOOT, PLACEBO_DRAWS, WILD_DRAWS = 2000, 200, 9999
ALPHA_STAGE1_ROUTE, ALPHA_STAGE2, ALPHA_M, BY_Q = 0.01, 0.05, 0.05, 0.10
MIN_UNITS, MIN_CLUSTERS, G_NORMAL, G_MIN = 100, 30, 30, 15
PLACEBO_MAX_ADVANCE_RATE = 0.015
PLACEBO_PSEUDO_P_MIN = 0.05
R_ANN_MIN = 0.10
COST_SENS_C = 0.0075  # +0.75c on every bought leg (binding)
TOP_CLUSTERS_DROPPED = 5
FAMILY_M_K = 4
ROUTE_STAGE2_K_MAX = 4

FLOORS = {"C1": 0.010, "C2": 0.010, "S2": 0.0050, "S3": 0.0050, "N1": 0.0050, "N2": 0.050, "E1": 0.10, "E2": 0.25}
FLOOR_UNITS = {"C1": "price", "C2": "price per filled share", "S2": "price", "S3": "price per filled share",
               "N1": "share of eligible event-minutes", "N2": "share (5-minute persistence)", "E1": "cents per pooled SD of flow", "E2": "cents per print"}
TESTS = {"C": ("C1", "C2"), "S": ("S2", "S3"), "M": ("N1", "N2", "E1", "E2")}
STAGE2_ROUTE_TESTS = ("C1", "C2", "S2", "S3")
DIRECTIONS = {"C1": "> 0", "C2": "> 0", "S2": "> 0", "S3": "> 0", "N1": "two-sided (expected < 0)", "N2": "two-sided (expected < 0)",
              "E1": "two-sided (expected > 0)", "E2": "two-sided (expected > 0)"}

# ---- CH46 / CB4-C --------------------------------------------------------------------------------------------------

C = {
    "tau0_delay_min": 10, "end_within_h": 2, "min_life_h": 24, "window_before_h": cb4_data.WINDOW_BEFORE_H, "window_after_h": cb4_data.WINDOW_AFTER_H,
    "gap_h": [1.5, 3.0], "W_F_h": [2, 0], "W_B_h": [26, 24], "paper_size": 10, "max_trades": 10000,
    "uma_block_tokens": ["proposed", "disputed", "resolved"], "uma_extension": "once, at the census, by status strings only",
    "strata": ["S", "E", "L", "P", "N", "U", "unknown"],
    "fill": "first taker-sell print strictly below q in [tau0, e)", "optimistic_fill": "sell print <= q (reported)",
    "side_audit_min_share": 0.80, "side_audit_window_min": 10,
    "g46_c1_units_per_week": 50, "g46_c1_events": 30, "g46_c2_units_per_week": 100,
    "censored_sensitive_share": 0.05, "truncation_worst_case": {"C1": "10th percentile of observed delta", "C2": "filled loser net = -q"},
    "matched_cell": "fee_category x UTC date of e x 6h block of e", "matched_ci": 0.90,
    "clusters": {"C1": ["event", "utc_day_of_e"], "C2": ["event", "utc_day_of_closed_time_or_censoring_mark"]}, "dev_lodo": True,
    "amendment_A_C1": ("time way = UTC day (was ISO week, never testable: 2-5 weeks < 15); it enters the p max under the section 2.3 small-G rule iff "
                       "G_day >= 15, else the leave-one-day-out sign rule is binding at that stage; top-5 robustness drops 5 events and 5 days; "
                       "sign by ISO week reported only; alphas, floors, k and Holm unchanged; re-check M3: wherever LODO binds, C2 needs it by the closing day AND by the day of e; a top-5-dropped branch whose remaining days fall below 15 needs LODO too; lag-1 autocorrelation of daily means reported"),
    "outcomes_read": {"dev": "T4_dev_out", "rep": "T4_rep_out"}, "weather_excluded": True, "sports": "reported stratum",
}

# ---- CH50 / CB4-S --------------------------------------------------------------------------------------------------

S = {
    "cadence_bounds_s": {k: list(v) for k, v in cb4_data.CADENCE_BOUNDS.items()}, "horizons_h": cb4_data.HORIZONS,
    "successor_created_lag_h": cb4_data.SUCC_CREATED_LAG_H, "pseudo_gap_h": cb4_data.PSEUDO_GAP_H,
    "alt_origin": "endDate(e_k) + 1h", "series_n": cb4_data.SERIES_N, "series_n_sports": cb4_data.SERIES_N_SPORTS, "members": cb4_data.SERIES_MEMBERS,
    "print_series": {"P_A": "VWAP of taker-buy prints on the rolled-into token in [tau-60min, tau)", "P_B": "taker sells (sign check)", "p": "history price (usable rule)"},
    "S2": "mean of -(P_A(V_end) - P_A(t0 + |M|))", "S1": "reported only",
    "S3": {"post_min": 10, "q": "min(p(t0) + h(p(t0)) + 1c, 0.99)", "fill": "taker-buy print strictly above q in (t0+10min, t0+|M|]",
           "exit": "buy back at V_end at a_x = min(p_x + h(p_x), 0.999)", "net": "q - a_x - f(a_x)", "capital": "1 - q", "hold_days": "max((V_end - t_fill)/1d, 1)"},
    "pseudo_roll_credit": "mean(-v_r) - mean(-v_t0') >= 0.5 mean(-v_r), on units with both origins",
    "pseudo_min_units": 100, "pseudo_min_series": 30,
    "publicity_min_share": 0.95, "publicity_converged_within": 0.02, "publicity_after_min": 10,
    "h7_side_audit_min_share": 0.75, "g50_series": 30, "g50_units": 300,
    "clusters": ["series", "series_x_iso_week_of_t0"], "era_rule": "post-rollout subset must have the declared sign; S3 pre-rollout fills carry -a_AS",
    "split": {"holdout_frac": cb4_data.SPLIT_HOLDOUT_FRAC, "embargo_d": cb4_data.SPLIT_EMBARGO_D},
    "weather_excluded": True, "alt_origin_sign_binding": True, "print_series_sign_binding": True,
}

# ---- CH52 / CB4-N and CH53 / CB4-E ---------------------------------------------------------------------------------

N = {
    "seed": "arepo-cb4-pmxt", "members": [2, 10], "negRiskAugmented": False, "other_placeholder_excluded": True, "open_lead_h": 1,
    "vwap_shares": 10, "margin": 0.005, "rho": 0.50, "rho_report": 0.25, "stale_min": 60, "min_eligible_minutes": 30, "onset_max_minute": 54, "persist_min": 5,
    "events_per_hour": 15, "members_per_hour": 90, "H_grid": [84, 168, 252, 336], "H_rule": "min(H_mde, H_cap)",
    "H_cap_rule": "largest H with 1.2 * H * g <= 150 GB", "H_mde_rule": "smallest H with N1 MDE <= 1.0pp (two-sided Holm first step 0.0125, power 0.8, deff>=1.5); 336 if none",
    "ingress_cap_gb": {"pilot": 15, "measure": 150}, "pilot_hours": 24, "stop_eligible_events_per_hour": 5, "stop_missing_hour_share": 0.30,
    "pseudo_bands": {"k": [-3, -2, -1, 0, 1], "width": "rho * F0", "x": "G - F0 - mu"}, "pseudo_p": 0.05,
    "in_time_placebo_breaks": ["2026-05-14", "2026-06-18"], "clusters": ["event", "calendar_day"], "tests": {"N1": "stacked DiD mid vs lo shares", "N2": "stacked DiD onset persistence"},
    "weather_excluded": True, "CB4_SPORTS_IN_PRIMARY": False,
}
E = {
    "seed": cb4_data.ERA_SEED, "per_cell": cb4_data.ERA_PER_CELL, "min_life_d": cb4_data.ERA_MIN_LIFE_D, "origin_grid_h": 2, "origin_window_h": cb4_data.ERA_ORIGIN_H,
    "buckets_h": [[0, 24], [24, 48], [48, 72]], "E1_feature": "f_net_6h = net signed taker notional over 6h, winsorised at pooled 1/99 pct, / pooled SD",
    "E1_target": "6h history-price change d", "E2": "m_i = s_i (p(ts + 2h) - price_YES_i), cents; AS = -m; print-equal cell means",
    "E2_components": ["spread", "drift"], "delta": "(delta_S + delta_O)/2", "delta_S": "(b_S,P1 - b_S,P0) - (b_O,P1 - b_O,P0)", "delta_O": "(b_O,P2 - b_O,P1) - (b_S,P2 - b_S,P1)",
    "sign_agreement_binding": True, "min_clusters_per_cell": 30, "min_rows_per_cell": 1000, "placebo": "P0 split at D_pl_E (sports vs others)",
    "clusters": ["event", "calendar_day"], "winsor": [0.01, 0.99],
}

REGISTER_RULES = {
    "path": "model_specs/cost_regimes_v1.json", "version": cost_regimes.VERSION, "label": cost_regimes.LABEL, "R0": "can only add cost terms or narrow windows",
    "a_AS": "upper 95% bound of E2 delta if E2 adopted with positive sign else 0", "era_rule_values": [cost_regimes.ERA_RULE_POOLED, cost_regimes.ERA_RULE_POST],
    "adoption": ["Holm over family M (alpha 0.05, k=4)", "floor", "in-time placebo p >= 0.05", "pseudo-band check (N)", "delta_S/delta_O sign agreement (E)", "top-5 robustness"],
    "excluded_regime_dates": cost_regimes.EXCLUDED_REGIME_DATES, "band_map_planning_only": True,
}

REFUSED_RUN_IDS = tuple(cb4_data.REFUSED_RUN_IDS)
REFUSED_ROOTS = tuple(cb4_data.REFUSED_ROOTS)
# columns the pre-freeze census must never carry (outcome guard, CB1 section 2.9)
CENSUS_FORBIDDEN_COLUMNS = (
    "outcome", "outcome_prices", "outcomePrices", "Y", "y", "resolved", "winner", "closed_time", "closedTime", "net", "mark_out", "markout",
    "delta", "C1", "C2", "S2", "S3", "pred_winner_key", "pred_outcome_prices", "pred_closed_time",
    "delta_w", "mark", "AS", "d6h", "f_net_6h", "neg_v", "s3_net",  # freeze-check fix 8: value columns of the shared helpers
)
CENSUS_COUNTS = {
    "C": ["c2_units_per_week", "flip_strata", "c1_units_class_S_N", "matched_cells", "uma_statuses_observed", "truncation_counts", "side_audit_two_sided", "g46", "clusters"],
    "S": ["series_by_cadence_category", "roll_units", "print_availability", "pseudo_roll_missing_by_cadence", "g_per_way", "g50", "match_rate", "t0_publicity", "h7_side_audit"],
    "E": ["markets_rows_prints_per_cell", "halves_of_P0", "event_day_clusters", "truncation_per_cell", "predicted_mdes"],
    "N": ["eligible_events_per_hour", "missing_corrupt_hours", "pilot_ingress_per_hour", "H", "venue_rho_check"],
}

HYPOTHESES_CB4 = {
    "C1": "Same-token sell prices fall from 24h before to the final 2h before the scheduled end in markets whose order book then stops (matched S - N contrast).",
    "C2": "A resting bid at the recorded touch 2h before the scheduled end, filled only on a trade-through, earns a positive net held to resolution.",
    "S2": "The rolled-into side of a recurring series successor falls back over the hours after the predecessor resolves.",
    "S3": "A maker ask posted into the roll, exited later as a taker, pays after costs.",
    "N1": "Gaps harvestable only by a top-tier taker became rarer after the 2026-05-28 rebate tiers relative to maker-only gaps.",
    "N2": "Such gaps became shorter lived (5-minute persistence).",
    "E1": "6h flow continuation per unit of signed net notional rose after the fee rollout.",
    "E2": "Adverse selection against makers per print rose after the fee rollout.",
}

# (module, name) of imported rule-applying functions whose source is part of the declaration
IMPORTED_RULE_FUNCTIONS = (
    ("cb1_history", "queue_fill"), ("cb1_history", "asof_quote"), ("cb1_history", "trade_condition_state"), ("cb1_history", "is_sports"),
    ("cb1_history", "iso_week"), ("cb1_history", "fee_rate"), ("cb1_history", "half_spread"),
    ("cb2_weather", "small_g_pvalue"), ("cb2_weather", "_cluster_sums"), ("economics", "fee_spec"), ("economics", "resolve_rate"),
    ("economics", "sweep_fill"), ("economics", "boot_ratio"), ("battery", "_cr_var_of_sum"), ("wallet_sidecar", "hash_wallet"),
    ("cb3_common", "mean_test"), ("cb3_common", "testable"), ("cb3_common", "boot_ci_mean"), ("cb3_common", "top_clusters_mask"), ("cb3_common", "sign_agree"),
    ("cb3_common", "holm"), ("cb3_common", "batch_holm"), ("cb3_common", "write_new"), ("cost_regimes", "cost_regime"),
    ("cb3_declaration", "spec_committed"), ("cb3_declaration", "single_commit"), ("cb3_declaration", "canonical_sha256"),
    ("cb1_history", "oldest_or_inf"), ("cb1_history", "taker_fee_ps"), ("cb1_history", "parse_outcome0"),
    ("history_backfill", "_asof"), ("history_sources", "rebuild_book"),
    # freeze-check fix 6
    ("cb3_common", "_codes"), ("cb3_common", "n_clusters"), ("cb3_common", "_p_from_z"),
    ("history_backfill", "load_trades"), ("history_backfill", "load_prices"), ("history_backfill", "fee_category"),
)
# modules hashed whole (every function and class: pure rule or statistic code)
WHOLE_MODULE_HASH = ("cb4_declaration", "cost_regimes", "cb4_rules", "cb4_measure")
# modules hashed by an explicit list of rule functions: run_closewin, the release/restore I/O, the fetch plumbing, the census, the pilot and the
# command wrappers are not rule code and may change without invalidating the frozen declaration
EXPLICIT_RULE_FUNCTIONS = {
    "cb4_data": (
        "_ep", "_parse_ts", "refuse_run_id", "refuse_path", "declaration_h7", "is_weather_text", "is_weather_market", "norm_label", "cadence_class",
        "horizon_for", "pick_successor", "_price_pair", "winner_of", "match_side", "winner_market", "series_roll_to", "series_rules_doc", "with_ladders_copy",
        "require_series_rules", "require_group_s_amendment", "require_h5_seal_copy", "_history_ids", "_h5_ids", "_json_list", "slim_event", "walk_series_events",
        "_modal", "assemble_units", "union_window", "fetch_unit_series", "series_frame_counts", "split_h7s", "drop_era_overlap", "ids_sha256", "split_record",
        "_era_market_ids", "parse_periods", "era_days", "era_period_of", "apply_era_rules", "draw_era_sample", "walk_era_frame", "_main_row", "_outcome_row",
        "build_capture", "_sidecar_facts", "flag_off", "seal_h7_run", "verify_h7", "Refused",
    ),
    "cb4_analysis": (
        "load_captures", "load_trades_dir", "fetch_market_outcomes", "load_era", "era_frames", "load_series", "c_inputs", "c_run", "_read_hours", "_rates",
        "_events_meta", "_pins", "_measure_n", "_measure_e", "_measure_commit", "_fetch_outcomes", "_screen", "_replicate", "stage2_expected", "_series_dir",
        "_guard_s_register", "_gate", "_census_path", "census_gates", "gate_failed_tests", "_census_gates", "load_guarded_outcomes", "_uma_extra",
        "census_frame", "census_forbidden_keys", "pilot_h", "outcome_status",
    ),
}


def rule_constants() -> dict:
    """Module constants that are rules (hashed with the declaration; a function's source does not cover a constant it reads)."""
    from . import cb1_history, cb2_weather, cb4_analysis, cb4_measure, cb4_rules  # noqa: PLC0415
    from . import cb3_declaration as c3  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    return {"MAX_QUOTE_AGE_S": hb.MAX_QUOTE_AGE_S, "GRID_S": hb.GRID_S, "C_SMALL_G": list(cb4_rules.C_SMALL_G), "S_SMALL_G": list(cb4_rules.S_SMALL_G),
            "C_TIME_WAY": cb4_rules.C_TIME_WAY, "H_UNAVAILABLE": cb4_analysis.H_UNAVAILABLE, "PLACEBO_MIN_CLUSTERS": dict(cb4_measure.PLACEBO_MIN_CLUSTERS),
            "CENSUS_KEEP": {k: list(v) for k, v in cb4_analysis.CENSUS_KEEP.items()},
            "INTERPRETATIONS": {"cb4_rules": list(cb4_rules.INTERPRETATIONS), "cb4_measure": list(cb4_measure.INTERPRETATIONS)},
            "FEE_ERAS": dict(cost_regimes.FEE_ERAS), "ERA_BUFFER_D": cost_regimes.ERA_BUFFER_D,
            # freeze-check fix 6: constants read by imported rule functions (a function's source does not cover them)
            "HALF_SPREAD": [list(x) for x in cb1_history.HALF_SPREAD], "MAX_DOCS_RATE": economics.MAX_DOCS_RATE,
            "cb2_small_g": {"G_NORMAL": cb2_weather.G_NORMAL, "G_MIN": cb2_weather.G_MIN, "N_WILD": cb2_weather.N_WILD, "SEED": cb2_weather.SEED,
                            "WEBB": [float(x) for x in cb2_weather._WEBB]},
            "cb3_common_defaults": {"G_NORMAL": c3.G_NORMAL, "G_MIN": c3.G_MIN, "MIN_UNITS": c3.MIN_UNITS, "MIN_CLUSTERS": c3.MIN_CLUSTERS,
                                    "TOP_CLUSTERS_DROPPED": c3.TOP_CLUSTERS_DROPPED, "N_BOOT": c3.N_BOOT, "SEED_BOOT": c3.SEED_BOOT}}


CB4_RULE_MODULES = ("cb4_declaration", "cost_regimes", "cb4_data", "cb4_rules", "cb4_measure", "cb4_analysis")
ABSENT = "ABSENT"


def source_hashes() -> dict[str, str]:
    """sha256 of every function and class in the whole-hashed rule modules (``WHOLE_MODULE_HASH``), the explicit rule functions of ``cb4_data`` and
    ``cb4_analysis`` (``EXPLICIT_RULE_FUNCTIONS``) and the imported rule functions. A module that is not
    importable (not written yet) contributes ``<module>: ABSENT`` and blocks :func:`require_declaration`."""
    out: dict[str, str] = {}
    for mod in CB4_RULE_MODULES:
        try:
            m = importlib.import_module(f"{__package__}.{mod}")
        except ModuleNotFoundError as exc:
            if exc.name != f"{__package__}.{mod}":
                raise
            out[mod] = ABSENT
            continue
        if mod in EXPLICIT_RULE_FUNCTIONS:
            for name in EXPLICIT_RULE_FUNCTIONS[mod]:
                obj = getattr(m, name)  # a renamed or removed rule function is an error, never a silent omission
                out[f"{mod}.{name}"] = hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()
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


def declaration_blob() -> dict:
    return {
        "sources": source_hashes(), "version": VERSION, "dates": DATES,
        "seeds": {"boot": SEED_BOOT, "placebo": SEED_PLACEBO},
        "draws": {"n_boot": N_BOOT, "placebo": PLACEBO_DRAWS, "wild": WILD_DRAWS},
        "stage": {"alpha1_route": ALPHA_STAGE1_ROUTE, "alpha2": ALPHA_STAGE2, "alpha_M": ALPHA_M, "by_q": BY_Q, "min_units": MIN_UNITS, "min_clusters": MIN_CLUSTERS,
                  "g_normal": G_NORMAL, "g_min": G_MIN, "placebo_max_advance_rate": PLACEBO_MAX_ADVANCE_RATE, "placebo_pseudo_p_min": PLACEBO_PSEUDO_P_MIN,
                  "r_ann_min": R_ANN_MIN, "cost_sens": COST_SENS_C, "top_clusters_dropped": TOP_CLUSTERS_DROPPED, "family_m_k": FAMILY_M_K,
                  "route_stage2_k_max": ROUTE_STAGE2_K_MAX},
        "floors": FLOORS, "floor_units": FLOOR_UNITS, "tests": {k: list(v) for k, v in TESTS.items()}, "stage2_route_tests": list(STAGE2_ROUTE_TESTS), "directions": DIRECTIONS,
        "C": C, "S": S, "N": N, "E": E, "register": REGISTER_RULES,
        "hypotheses": {k: HYPOTHESES_CB4[k] for k in sorted(HYPOTHESES_CB4)},
        "refused_run_ids": list(REFUSED_RUN_IDS), "refused_roots": list(REFUSED_ROOTS), "census_forbidden_columns": list(CENSUS_FORBIDDEN_COLUMNS),
        "census_counts": CENSUS_COUNTS, "fee_table": {"docs_rate": economics.DOCS_CATEGORY_RATE, "version": economics.FEE_TABLE_VERSION},
        "series_rules_doc": cb4_data.series_rules_doc(), "h7": cb4_data.declaration_h7(), "rule_constants": rule_constants(),
        "kinds": list(TRIAL_KINDS), "count_sources": list(COUNT_SOURCES),
    }


def canonical_sha256(obj) -> str:
    return _c3.canonical_sha256(obj)


def declaration_sha256() -> str:
    return hashlib.sha256(json.dumps(declaration_blob(), sort_keys=True, default=float).encode()).hexdigest()


# ---- spec (freeze file) ----------------------------------------------------------------------------------------


def spec_payload(census_pins: dict | None = None, census_sha256: str | None = None) -> dict:
    """The freeze file: declaration hash and, after the census, the pinned census quantities (H, rho, extended UMA statuses) with the
    census.json sha256. Floors are never part of the pins."""
    out: dict = {"version": VERSION, "declaration_sha256": declaration_sha256()}
    if census_pins is not None:
        bad = sorted(k for k in census_pins if k not in ALLOWED_PINS)
        if bad:
            raise DeclarationError(f"census pins may only be {ALLOWED_PINS}; got {bad}")
        out["census_pins"] = census_pins
        out["census_pins_sha256"] = canonical_sha256(census_pins)
    if census_sha256 is not None:
        out["census_sha256"] = census_sha256
    return out


ALLOWED_PINS = ("H", "rho", "uma_extra_statuses", "stop")


def write_spec(path: Path = SPEC_PATH, census_pins: dict | None = None, census_sha256: str | None = None) -> dict:
    """Write the CB4 freeze file. Refuses to overwrite and refuses while a rule module is absent."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; a frozen declaration is never overwritten")
    miss = absent_modules()
    if miss:
        raise DeclarationError(f"cannot freeze: rule modules not written yet: {miss}")
    path.parent.mkdir(parents=True, exist_ok=True)
    p = spec_payload(census_pins, census_sha256)
    path.write_text(json.dumps(p, indent=1, sort_keys=True) + "\n")
    return p


def require_declaration(path: Path | None = None, *, require_committed: bool = True) -> str:
    """Refuse unless the committed spec's hash equals this code's declaration hash, every rule module exists, and (when committed) the
    spec carries the census pins and census hash and has exactly one commit in its history."""
    path = Path(path) if path is not None else SPEC_PATH
    if not path.exists():
        raise DeclarationError(f"no committed declaration at {path}; counted CB4 runs are refused (CB4 freeze not committed)")
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
    if require_committed:
        for k in ("census_pins", "census_pins_sha256", "census_sha256"):
            if not spec.get(k):
                raise DeclarationError(f"the committed spec lacks {k}")
    if spec.get("census_pins") is not None:
        if spec.get("census_pins_sha256") != canonical_sha256(spec["census_pins"]):
            raise DeclarationError("census_pins_sha256 does not match census_pins")
        bad = sorted(k for k in spec["census_pins"] if k not in ALLOWED_PINS)
        if bad:
            raise DeclarationError(f"census pins may only be {ALLOWED_PINS}; got {bad}")
    return cur


def check_pins(pins: dict) -> None:
    """Freeze-check fix 3: the pins must all be present and well formed. ``H`` an integer >= 0, or ``"unavailable"`` when the pilot failed or is missing (re-check M1); ``rho`` in (0, 1] (the venue's top-tier rebate share);
    ``uma_extra_statuses`` a list of lower-case status tokens (the once-only extension of the UMA block set, status strings only)."""
    import re  # noqa: PLC0415

    miss = [k for k in ALLOWED_PINS if k not in pins]
    if miss:
        raise DeclarationError(f"census pins lack {miss}")
    h = pins["H"]
    if h != "unavailable" and (isinstance(h, bool) or not isinstance(h, int) or h < 0):
        raise DeclarationError(f"pin H must be an integer >= 0 or 'unavailable' (pilot failed or missing), got {h!r}")
    r = pins["rho"]
    if isinstance(r, bool) or not isinstance(r, int | float) or not (0.0 < float(r) <= 1.0):
        raise DeclarationError(f"pin rho must be in (0, 1], got {r!r}")
    sp = pins["stop"]
    if sp != "unavailable" and not isinstance(sp, bool):
        raise DeclarationError(f"pin stop must be a bool (the pilot's frozen stop-rule verdict) or 'unavailable', got {sp!r}")
    u = pins["uma_extra_statuses"]
    if not isinstance(u, list) or any(not isinstance(x, str) or not re.fullmatch(r"[a-z_]+", x) for x in u):
        raise DeclarationError(f"pin uma_extra_statuses must be a list of lower-case status tokens, got {u!r}")


def load_pins(path: Path | None = None) -> dict:
    spec = json.loads(Path(path if path is not None else SPEC_PATH).read_text())
    pins = spec.get("census_pins")
    if not pins:
        raise DeclarationError("the committed spec carries no census_pins (H, rho, extended UMA statuses, stop)")
    if spec.get("census_pins_sha256") != canonical_sha256(pins):
        raise DeclarationError("census_pins_sha256 does not match census_pins")
    check_pins(pins)
    return pins


def pins_sha256(path: Path | None = None) -> str | None:
    return json.loads(Path(path if path is not None else SPEC_PATH).read_text()).get("census_pins_sha256")


def verify_pins_against_census(spec_path: Path, census_path: Path) -> None:
    """The spec's census_sha256 must equal the sha256 of census.json and the pins must equal that census's ``pin_proposal``."""
    spec = json.loads(Path(spec_path).read_text())
    census_path = Path(census_path)
    if not census_path.exists():
        raise DeclarationError(f"{census_path} not found: the pins cannot be checked against the census")
    if provenance.sha256_file(census_path) != spec.get("census_sha256"):
        raise DeclarationError("census.json sha256 differs from the spec's census_sha256")
    prop = json.loads(census_path.read_text()).get("pin_proposal") or {}
    pins = load_pins(spec_path)
    for k in ALLOWED_PINS:
        if k in pins and prop.get(k) != pins[k]:
            raise DeclarationError(f"pin {k} differs from the census proposal")


# ---- dates and guards ------------------------------------------------------------------------------------------


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
    if run_id is not None and run_id in REFUSED_RUN_IDS:
        raise RefusedRun(f"CB4 refuses run id {run_id!r} (sealed, reserved or retired data)")


def refuse_path(path: Path | str) -> None:
    parts = set(Path(path).parts)
    for r in REFUSED_ROOTS:
        if r in parts:
            raise RefusedRun(f"CB4 never reads {r}/")


def in_pmxt_window(start: str, end: str) -> bool:
    return epoch(start) < epoch(DATES["pmxt_window"][1]) + 86400.0 and epoch(end) > epoch(DATES["pmxt_window"][0])


def load_rep_pin(path: Path | None = None) -> dict:
    p = Path(path) if path is not None else REP_PIN_PATH
    if not p.exists():
        raise WindowError(f"no pinned T4_rep_start at {p}")
    if path is None and not _c3.spec_committed(p):
        raise WindowError(f"{p} is not committed (or differs from HEAD)")
    doc = json.loads(p.read_text())
    if epoch(doc["t4_rep_start"]) < epoch(DATES["T4_rep_start_floor"]):
        raise WindowError("pinned T4_rep_start is before the declared floor")
    return doc


def rep_window(path: Path | None = None) -> tuple[float, float]:
    doc = load_rep_pin(path)
    s = epoch(doc["t4_rep_start"])
    return s, s + DATES["T4_rep_len_d"] * 86400.0


def rep_out(path: Path | None = None) -> float:
    return rep_window(path)[1] + DATES["T4_rep_out_after_rep_end_d"] * 86400.0


def pin_rep_start(freeze_commit: str, freeze_commit_time: str, first_capture_after: str, t4_rep_start: str, path: Path | None = None) -> dict:
    """Write the T4_rep_start pin once: max(floor, first complete capture >= freeze commit time + 2h)."""
    path = Path(path) if path is not None else REP_PIN_PATH
    if path.exists():
        raise WindowError(f"{path} exists; T4_rep_start is pinned once")
    sha = str(freeze_commit).strip().lower()
    if not (7 <= len(sha) <= 64) or any(c not in "0123456789abcdef" for c in sha):
        raise WindowError(f"not a commit sha: {freeze_commit!r}")
    if epoch(first_capture_after) < epoch(freeze_commit_time) + DATES["T4_rep_start_min_gap_after_freeze_h"] * 3600.0:
        raise WindowError("the first capture must be at least 2h after the freeze commit")
    expected = max(epoch(DATES["T4_rep_start_floor"]), epoch(first_capture_after))
    if abs(epoch(t4_rep_start) - expected) > 1.0:
        raise WindowError(f"T4_rep_start {t4_rep_start} is not the max rule value {iso(expected)}")
    doc = {"version": VERSION, "freeze_commit": sha, "t4_rep_start": iso(expected), "t4_rep_end": iso(expected + DATES["T4_rep_len_d"] * 86400.0),
           "t4_rep_out": iso(expected + (DATES["T4_rep_len_d"] + DATES["T4_rep_out_after_rep_end_d"]) * 86400.0)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return doc


class TooEarly(RuntimeError):
    """An outcome read or stage that is not yet allowed."""


def check_outcome_allowed(window: str, now: datetime | None = None, pin_path: Path | None = None) -> None:
    """``fetch-outcomes --window dev`` refuses before T4_dev_out; ``--window rep`` before T4_rep_out."""
    now = now or datetime.now(UTC)
    if window == "dev":
        need = epoch(DATES["T4_dev_out"])
    elif window == "rep":
        need = rep_out(pin_path)
    else:
        raise WindowError(f"unknown window {window!r}")
    if now.timestamp() < need:
        raise TooEarly(f"outcomes for {window} are refused before {iso(need)}")


def check_series_screen_allowed(register_path: Path | None = None) -> None:
    """``screen --family S`` refuses until cost_regimes_v1.json is committed (era rule known first)."""
    p = Path(register_path) if register_path is not None else cost_regimes.REGISTER_PATH
    if not p.exists():
        raise DeclarationError(f"{p} is not written: S2/S3 are refused until the cost register is committed")
    if not _c3.spec_committed(p):
        raise DeclarationError(f"{p} is not committed (or differs from HEAD)")
