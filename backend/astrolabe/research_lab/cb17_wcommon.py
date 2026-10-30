# ruff: noqa: E501
"""CB17 rules part ``common`` (window side): docs/research_lab/CREATIVE_BATCH_17.md sections 1.1-1.4, 2.1-2.8, 11.

``cb17_common`` is frozen under part ``pre`` (its constants and functions are hashed there), so the window-side common rules live HERE (section 11.7, O5). Part ``common`` hashes
``cb17_common`` (unchanged) and this module: the branch record (T; family A withdrawn uncounted, q0400), the ``S_8`` rule and the two windows, the lookback floor and its
"unavailable (lookback floor)" label, the REP_8 refusal before the seal, the event-arm hash, seeds, cluster ways and the small-G rule, the Holm / BY settings (k1 = 3 under branch T,
Stage-2 early alpha / 8), materiality floors, the composition guard (conditional estimator + 3-of-200 within-strata permutation, the 50% informativeness rule), the circular-shift
calibration placebo, the power and availability gates, disk caps, the CB16 key-file rule, the cost-map citation (q0403, reported lines only), the smoke criteria, and the pinned sha256
of the CB13 and CB16 functions the window code calls.

Everything here is a declaration or a small pure rule. Readers, frames, estimators and the runner are window CODE, pinned separately at the code freeze (``CODE_FREEZE_NAME``); a code
fix never changes this part. Nothing here reads a file, a mark or an outcome.
"""

from __future__ import annotations

import hashlib
import inspect
import math
from datetime import UTC, datetime, timedelta

import numpy as np

from . import cb16_common as c16
from . import cb17_common as c17

Refused = c17.Refused
NotNow = c17.NotNow

COMMON_VERSION = "cb17-common-v1"

# ---- the branch record (section 11.1; q0400, part pre's rule, outcome-blind) ------------------------------------------------------------------------
BRANCH = "T"
BRANCH_RECORD = {"job": "q0400", "result": "creative_batch17/pre_census_A.json", "result_sha256": "9deedcf5a1aeb0e370796457cab3f933d8e4c6b59e6a5de302c9a70e82ec38cf",
                 "p1_reproduced": True, "agreement_k": 906, "agreement_n": 971, "wilson_lower": 0.915571, "rule_pass": False,
                 "failed_binding_cells": ["touch_age:0-20min", "touch_age:20-60min", "p_band:P[0.03,0.20)", "p_band:P[0.20,0.80]", "p_band:P(0.80,0.97]", "class:PATH-SETTLED",
                                          "class:SCHEDULED-EVENT", "class:UNSCHEDULED-NEWS"]}
A_WITHDRAWN = True
A_WITHDRAWAL = ("family A (CH144, open versus close) withdrawn uncounted before its part commit, as pre-declared (sections 2.5, 10.5): q0400 measured side agreement 906/971 = 93.3% "
                "(Wilson lower 0.915571) < 97% overall and in every binding cell, so branch T binds; part A is never committed; A1, A1-rep, A2 and GAS never run; no window job parses side")
PRE_RULES_SHA256 = "ddc0249b23eedf8cfe50b2b60e94378264804ca4791c82c01cf3993df54df6a7"
PRE_RESULTS_SHA256 = {"q0400": "9deedcf5a1aeb0e370796457cab3f933d8e4c6b59e6a5de302c9a70e82ec38cf", "q0401": "c3b8ae1b0f8d0bb7b54126193371e479c9175078591ebd46bb990d36ef063a1a",
                      "q0402": "442e99da3a7f806b05a76fa9de4e6a52bb8ded5516ff1ae2c67092a46812797d", "q0403": "43f28e02068094c9b7e45903f04525e44a30e4d1864c9077ccdbf5540eb629bf"}

# ---- counting (section 2.5; branch T) ---------------------------------------------------------------------------------------------------------------
COUNT_FAMILIES = ("B", "C")
FAMILY_TESTS = {"B": ("B1", "B2"), "C": ("C1",)}
FAMILY_REP_TESTS = {"B": ("B1-rep", "B1-econ", "B2-rep", "B2-econ"), "C": ("C1-rep", "C1-econ")}
TRIGGERS = {"B1": ("B1-rep", "B1-econ"), "B2": ("B2-rep", "B2-econ"), "C1": ("C1-rep", "C1-econ")}
TRIAL_KINDS = ("cb17_test", "cb17_replication", "cb17_descriptive")
K1 = 3  # branch T: B1, B2, C1 (fixed at the part commits)
K2_MAX = 6
STAGE_ALPHA = 0.05  # one-sided, Stage-1 batch Holm and the Stage-2 CB17-wide Holm
GATE_P = 0.01  # Stage-1 strict p
EARLY_ALPHA2_DIVISOR = 8  # a Stage-2 test finishing before k2 is known: alpha / 8 (kept at 8 under branch T, stricter than 6)
BY_Q = 0.10  # triage only, over the cumulative count at the run

# ---- materiality floors (section 2.4; unchanged) -----------------------------------------------------------------------------------------------------
FLOOR_C = 0.5  # B1, B2 (per SD), C1 and their reps: the point estimate must reach +0.5c
ECON_DIFF_FLOOR_C = -0.5  # B1-econ, B2-econ, C1-econ primary: flagged-minus-rest difference <= -0.5c
ECON_LEVEL_FLOOR_C = -1.0  # second component: the flagged group's net <= -1.0c

# ---- dates (section 1.2) -----------------------------------------------------------------------------------------------------------------------------
S8_EARLIEST = "2026-10-26T00:00:00Z"
S8_AFTER_RULES_S = 86400.0
WINDOW_S = 14 * 86400.0
FRAME_DELAY_S = 8 * 3600.0  # frames not before the window end + 8 h (the last units' marks exist)
MARK_TAIL_S = 8 * 3600.0
LEAD_S = {"sweeps_bc": 2 * 3600.0, "captures_bc": 6 * 3600.0, "captures_e": 3 * 3600.0}  # q0406 sweeps from S_8 - 2 h, captures from S_8 - 6 h; q0407 captures from S_8 - 3 h
REP_READ_LEAD_S = 7 * 86400.0  # q0410 reads from S_8 + 7 d (C trailing history and B previous passes of arm-1 events)
UNAVAILABLE_LOOKBACK = "unavailable (lookback floor)"
REP_THIN_LABEL = "REP_8 thinned by event overlap"

# ---- the event arm (section 1.2) ---------------------------------------------------------------------------------------------------------------------
ARM_SALT = "cb17-arm-v1|"
ARM_SCREEN, ARM_REP = 0, 1

# ---- inference (sections 2.3, 2.6) -------------------------------------------------------------------------------------------------------------------
WAYS = ("event", "path_x_block", "block6", "utc_hour")  # B and C; UTC day (G = 14) never enters the max (leave-one-day-out binds)
SMALL_G = {"cr1_min_G": 30, "cr2_min_G": 15, "cr2": "CR2 + t(G - 1) and the Webb wild bootstrap (larger p)", "below": "the way leaves the max; its leave-one-cluster-out sign rule binds"}
N_WILD = 9999
SEED_WILD = 1717  # the batch's bootstrap seed (section 2.3 names 1717); the design names no separate wild-bootstrap seed (O8: CB16 used its 1616 for both)
SEED_RANGE = (17101, 17140)
SEEDS = {"B1_composition": 17111, "B1_calibration": 17112, "B2_composition": 17121, "B2_calibration": 17122, "C1_composition": 17131, "C1_calibration": 17132}
PLACEBO_DRAWS = 200
PERM_MAX_REACH = 3  # the within-strata permutation holds iff at most 3 of 200 permuted coefficients reach the observed one (an uncomputable draw reaches)
PLACEBO_MAX_ADVANCE = 3  # the calibration placebo: at most 3 of 200 draws with one-sided p < 0.01 (1.5%)
COMPOSITION_HALF = 0.5  # the composition-conditional estimate keeps the sign and >= half of the primary
COMPOSITION_P = 0.05
ATTRIBUTION_HALF = 0.5
SPREAD_FREE_P = 0.05
INFORMATIVE_MIN = 0.50  # window informativeness rule (unchanged by the worn-data level selection)
AVAIL_MIN = 0.60
LOO_DAY_P = 0.05
TOP_DROP = 5
POWER_MDE_MAX_C = 1.0  # MDE = 3.80 x SE > 1.0c (2 x the floor) -> "not run (power)"

# ---- verdict labels ----------------------------------------------------------------------------------------------------------------------------------
NOT_RUN_POWER = "not run (power)"
NOT_TESTABLE_POP = "not testable (population)"
NOT_TESTABLE_SOURCE = "not testable (source)"
NOT_TESTABLE_AVAIL = "not testable (availability)"
NOT_TESTABLE_FIELD = "not testable (field)"
NOT_TESTABLE_SEMANTICS = "not testable (field semantics)"
UNINFORMATIVE = "composition guard uninformative"
LABEL_SCREEN = "L2 live window (SCREEN_8, post-rules), Stage-1 screen"
LABEL_REP = "later live window replication, event-disjoint (L2)"
LABEL_ECON = "recorded-touch round trip (L2)"

# ---- disk, refusals, whitelists (sections 1.1, 1.4, 2.8) ---------------------------------------------------------------------------------------------
DISK_CAP_GB = {"smoke": 0.01, "exclusion-keys": 0.01, "frame-screen-BC": 0.1, "frame-screen-AE": 0.05, "census": 0.01, "screen": 0.01, "frame-rep": 0.15, "rep": 0.01, "stage2-final": 0.01}
TOTAL_OUTPUT_CAP_GB = 0.3
FREE_DISK_MIN_GB = 4.5
WINDOW_REFUSED_ROOTS = ("surprise_live", "cross_venue_live", "cross_venue", "forecasts", "flow_screen", "trade_samples", "cb3_extract", "cb3_followup", "creative_batch16", "t_holdout")
WINDOW_PRINT_FIELDS = c17.PRINT_FIELDS  # branch T: side is never parsed by a window job; recv_ts never
WINDOW_FORBIDDEN_PRINT_FIELDS = ("side", "recv_ts", "key", "wallet_hash", "wallet", "proxyWallet", "ctx_chg_1h", "ctx_status", "chg_1h")

# ---- exclusion keys (q0405; section 1.3) -------------------------------------------------------------------------------------------------------------
CB16_KEYS = {"job": "q0380", "file": "creative_batch16/exclusion_keys.csv.gz", "columns": ("market_id", "found", "event_ids", "neg_risk_market_id", "series_ids", "sources"),
             "pin": "the sha256 recorded by q0380's manifest, set in q0405's job spec (CB16's q0380 --base-sha256 precedent); unset refuses; a q0380 stop record = keys absent (recorded)"}
KEY_RULE = ("a market or event is dropped only if it appears in a sealed historical set with a stored timestamp inside SCREEN_8 or REP_8 (none expected); drops are counted by source; "
            "CB16 frame ids are overlap counts once CB16 q0384 exists; live frames are collection overlap, never drops")

# ---- the cost-map citation (q0403; section 11.4; reported taker lines only, O4) ----------------------------------------------------------------------
COST_MAP = {"job": "q0403", "file": "creative_batch17/cost_lag_map.json", "sha256": "43f28e02068094c9b7e45903f04525e44a30e4d1864c9077ccdbf5540eb629bf",
            "cell": "sidecar fee category x decision-mid P band x liquidity band (part pre p_band / liq_band)", "sizes_usd": (1000, 5000), "printed": ("median", "p75", "not_executable_share"),
            "hurdles_c": (4.5, 1.8), "use": "reported next to each taker line and each econ line; never enters a decision", "median_receipt_lag_s": 480.0}

# ---- the CB13 and CB16 functions the window code calls, pinned by source sha256 (section 1.4) --------------------------------------------------------
CB13_PINS = {  # CB16's CB13 pins (identical at this commit) plus capture_meta; a divergence refuses
    "cb13_common.whitelist_print": "12950339a9210bc46d5f24cb466638570539229141148ad21ceb1a6295bf7c8f",
    "cb13_common.iter_capture_rows": "12b4e6b6cb5d7b109e91349add37f2d9fa7f1975a5e2059e16b0b1966d5e4fd5",
    "cb13_common.iter_sidecar_rows": "0f402eeae1be954e5ad009a58bf80d01d6b193e896d44137c7366713c8633d81",
    "cb13_common.capture_meta": "866e8e1d120f2dfcb0619d62073ed4bf734fbe168b48ed6781b669a3fe12b061",
    "cb13_t.yes_price": "2ce135e7489e799573c92668a400b8cf6895dfda7a8a0ab93a88407121b4362c",
    "cb13_t.build_transactions": "464be3b04fdf08db8d49fcc200b6181284594b33e54a947b2dd5d870489f286e",
    "cb13_t.classify_position": "d0ece510d787ea67aa1e6d6fea9a7a86fdc3897abb6f5f38432878ac0a51586a",
    "cb13_t.stale_variant": "8e722a30cd3b2c7144b5581d5e9667050ad195a11968b4c99154ec9f94a2face",
    "cb13_t.two_sided": "72495426a00ebbe012e8c1c798b804944ff9ab9d1fa61b59226f122f3b97ce48",
    "cb13_t.Q": "31bffc647a65f33892aec10cd87a2dbeb4e66f3f846ccfdf16f0a90dba20108e",
    "cb13_t.QuoteIndex": "8c6da5ba6632d22f9872936bf8fc8e27eecce1b761f0be20cf72d1e89cff752e",
    "cb13_t.MarkTable": "40a28befff88bf3cd30cf22f4ba2ea6429d6ac768da3080ab538639dee438ab9",
    "cb13_t.fee_rate_of": "97e6304d1acb5621d7f94485c43620097a47ccd8722b1b458c90e711f59968a0",
    "cb13_t.make_fills": "00da3417fd0f2d863e15ea8b96013518dbcb8c418060d22b096052d4d79863a6",
    "cb13_t.worst_value": "354deceb6a1936977c88368701fd4e369f4a7cd3caedc5e7f1975f3be72ba0a1",
    "cb13_t.adverse_value": "8868091f8f3776d2f3c7816606705f526758a4a62b1398ff06038ae4e98c5c68",
    "cb13_t.build_dataset": "32d69ce3e99b40ba723e59bbebd5fad7a173e3bd01a82a442ef8fff6fd5f8960",
    "cb13_t.gate_gti": "e5c7a389658b6bf6da34109f2da9a7e3eb574c4142b190a208ed06afce37b6de",
    "cb13_t.t3_values": "dea5843f46215c00f9d0a5bf5b3e447afd0b5f29d1fab61aef276f94d0a2d878",
    "cb13_t.drop_screen_events": "c34aa82c838a1c92d9e438739304458c0acb2796f23125d719933ac3c096cbb9",
    "cb13_label.classify": "d94d6645e05e07032fa0d73f63375849acbf3b92f1f83e64524e636d0203a0dc",
    "cb13_label.first_series_slug": "7bfcc9ce328d1f75f82774a57ad26aa933fbfb7085a9887ca003101f69e171d2",
    "cb13_label.underlying_of": "89d25064c2b8d141dbb60f5c95297a6ea0bf72ee629b5e90dda79cec2e5956a9",
    "cb13_label.audit_group": "86deaf8f1768141659b9a20308ff13d6c59dedea1aab4ad338048f5567366b24",
}
CB16_PINS = {
    "cb16_common.fe_demean": "9a8d6c47058f1e143f381841b7ea27819ed2ec1f98d51d14a9f1beb4076a1117",
    "cb16_common.fe_coef_pseudo": "ae3c618fbe67d32123d48fd1c2756fafd4afb90d6f5b2da3d9702ddbc659d13d",
    "cb16_common.cluster_p": "cf516bf7efd20c42ffa1da353fecde2d499ee84c6eaf63432ac11ca5e937ccb7",
    "cb16_common.p_pass": "4e029dd2fbfab1d14d9119aa8778fa559702d0086f17a8d1bf6c84455191e3ea",
    "cb16_common.sign_ok": "4215d155c50e056ad88483e383f2757581a6876f0446baffbe26179cf23d2a26",
    "cb16_common.leave_one_out_p": "2a41193ffc93eee725fb14e03d8dc1785e89c0c262b7158c515517da30d6b8e5",
    "cb16_common.top_k_drop_mask": "6582a115058255fc43f961c9c4e156af75be744d0ddbc3806df9af0d4a175d6b",
    "cb16_common.permute_within": "c1c908c40f5c91e1172067fd6fc5f6a141e2339327f19669f615efff961b76a6",
    "cb16_common.holm": "bc13d2e3180f887c3d592f02f5ddf23f33ac4ee417378f6e610f5aa298b65d69",
    "cb16_common.placebo_advance_rate": "dddafa6653cc29c6d9cfaac9f5cbf9b45bb978e4249f3b54b1f0854c7dcbe0ea",
    "cb16_common.availability": "5705ff910d9cede83871105c320022f7c599502a2bdaff946eb765a1d9948018",
    "cb16_common.in_election_night": "d78b3cf4eb2c08fe48494793d9d1435f398168ec43f1da3467d5758d1ac022a4",
    "cb16_common.require_disk": "66681a0d33bf0192436c44a5e343dfbc775a355bfe24fdfdfd809fb2c08f1ada",
    "cb16_common.collector_gap_ok": "a2024df3b0b73f7178e8583fb64c6250e11e05c5f6ca2b3511a56bd0f6a895ba",
    "cb16_common.write_dir_manifest": "9b435366ccfe2c7c633a98dc5fa0ddba16e1589934bbb0508f2456c4b2c31504",
    "cb16_common.guard_monitor_file": "db3b6039e74fe64a25830389561f44fe746d3fc6133d75ed217ef502c0de7fc4",
    "cb16_common.guard_capture_dir": "efdacc0d5c09767dced2c9c0cbe281bcc41b2f2ab24e05edee2e5b792ff9f925",
    "cb16_common.guard_floor": "ae1b4cda7945f8aca5725ff019490cb4bbb1c4a91230476bca9562b2477afb59",
    "cb16_common.refuse_path": "984c7b1020d07266c5a5d749572ed0d4042dbcd377bc2f1a3323cf608fbebbd9",
    "cb16_common.ensure_source_file": "5c02368fdb2dc28cbee40f487524fbe6da0afa5730b74e6148a5ff790cd12fe6",
    "cb16_common.e011_hold_lifted": "063f6342e70c49e908a76d1461dba30f1fd84c957a67eebddeb8fced413a9459",
    "cb16_common.cb3_hold_lifted": "05b88d5f9f9272854cb6bb18f4c0f16f3e45fdbf050f822ee4c36d5dc957967e",
    "cb16_common.committed_record": "5371a19751afa3afdf3988971e6853a04ad58d7fc3354f7bdb84c48e6263b26f",
    "cb16_common.read_keys_with_sources": "8fc3844432b94d96dd8e50df233960f88b0818bf1258dc9667b4857d64caa5b8",
    "cb16_q.list_captures": "0f101a92ea11d4284e8615a130a2445900e2c9445b6a581e349de51a99140878",
    "cb16_q.load_quote_index": "f627df5db45bd33143aae7d210289eb722729fb46e2307d4fbae0d7b38bd9687",
    "cb16_q.QuoteIndex16": "bc9049facfb96465cac5a33a9336dd87562f495687cce8f6d80952dc3231242c",
    "cb16_q.make_fills": "0c2098b01948d24777d9e92413de68b9c01014161f32c1d1364cfc294422b767",
    "cb16_q.trade_files": "4db22673cc0538736f5e3b677c5f8845675439449fb55acab4b2b3baf229df8a",
    "cb16_q.iter_prints": "9c495a96b3953f443d1d235757ca4b30b3877c4cd38587b72603398a039891fe",
}

# ---- records the window jobs require (sections 1.2 T17_rules / T17_code, ruling 6) -------------------------------------------------------------------
T17_RECORD_NAME = "cb17_t17_rules.json"  # {"t17_rules_utc": ..., "rules_commit": ..., "parts": {part: sha}}: written by the orchestrator when the parts land (O2)
CODE_FREEZE_NAME = "cb17_code_freeze.json"  # {"code_sha256": ..., "rules_sha256": {...}, "frozen_utc": ..., "attestation_code_freeze": ...}
REP_SEAL_NAME = "cb17_rep_SEAL.json"
ATTESTATION_RULE = ("no agent working on CB17 (designer, implementer, reviewer, or the orchestrator acting for CB17) opened any SCREEN_8 or REP_8 raw file before q0406 ran; other "
                    "registered jobs' automated reads under their own rules are not CB17 reads; attested at the code freeze and again with q0406's commit (ruling 6)")

# ---- smoke criteria (q0404, section CB17-SM) ---------------------------------------------------------------------------------------------------------
SMOKE_CRITERIA = ("parts_verify", "pins_cb13", "pins_cb16", "refusals_roots", "refusals_lookback_floor", "refusals_rep_before_seal", "refusals_census_cutoff", "forbidden_fields",
                  "arm_hash", "age_parser", "shift_state", "interval_rule", "trailing_tercile", "b_no_mark_label", "strata_selection_60", "reproduce_P1", "reproduce_P2", "reproduce_P3")
SMOKE_NEEDS = {"B": ("parts_verify", "pins_cb13", "pins_cb16", "refusals_roots", "refusals_lookback_floor", "refusals_rep_before_seal", "refusals_census_cutoff", "forbidden_fields",
                     "arm_hash", "age_parser", "shift_state", "b_no_mark_label", "strata_selection_60", "reproduce_P2"),
               "C": ("parts_verify", "pins_cb13", "pins_cb16", "refusals_roots", "refusals_lookback_floor", "refusals_rep_before_seal", "refusals_census_cutoff", "forbidden_fields",
                     "arm_hash", "interval_rule", "trailing_tercile", "strata_selection_60", "reproduce_P3"),
               "E": ("parts_verify", "pins_cb13", "refusals_roots", "refusals_lookback_floor", "refusals_census_cutoff", "forbidden_fields", "reproduce_P1")}


# =====================================================================================================================================================
# dates and windows
# =====================================================================================================================================================


def s8_from_rules(t17_rules_epoch: float) -> float:
    """``S_8 = max(2026-10-26T00:00Z, the first 00:00Z at or after T17_rules + 24 h)``: it depends only on the rules commit time, never on data."""
    t = float(t17_rules_epoch) + S8_AFTER_RULES_S
    d = datetime.fromtimestamp(t, UTC)
    mid = d.replace(hour=0, minute=0, second=0, microsecond=0)
    if mid.timestamp() < t:
        mid = mid + timedelta(days=1)
    return max(c17.ep(S8_EARLIEST), mid.timestamp())


def windows8(s8: float) -> dict:
    """Epoch bounds: decision ranges of SCREEN_8 and REP_8, the read ranges of each frame (never before the lookback floor) and the earliest frame time."""
    s, floor = float(s8), c17.ep(c17.LOOKBACK_FLOOR)
    scr, rep = (s, s + WINDOW_S), (s + WINDOW_S, s + 2 * WINDOW_S)
    return {"screen": {"units": scr, "sweeps": (max(floor, s - LEAD_S["sweeps_bc"]), scr[1]), "captures_bc": (max(floor, s - LEAD_S["captures_bc"]), scr[1]),
                       "captures_e": (max(floor, s - LEAD_S["captures_e"]), scr[1]), "marks": (scr[0], scr[1] + MARK_TAIL_S), "frame_not_before": scr[1] + FRAME_DELAY_S},
            "rep": {"units": rep, "read": (max(floor, s + REP_READ_LEAD_S), rep[1] + MARK_TAIL_S), "marks": (rep[0], rep[1] + MARK_TAIL_S), "frame_not_before": rep[1] + FRAME_DELAY_S}}


def lookback_available(t_needed: float) -> bool:
    """A unit whose rule needs a row timed before the lookback floor is "unavailable (lookback floor)" (counted, never back-filled)."""
    return bool(math.isfinite(float(t_needed)) and float(t_needed) >= c17.ep(c17.LOOKBACK_FLOOR))


def guard_window_row(t: float, what: str = "row") -> float:
    """Every window reader refuses a row timed before the lookback floor (J4-R and CB13-T's HOLDOUT end there)."""
    return c17.guard_not_window(t, what)


def guard_rep_unit(t: float, s8: float, *, rep_open: bool) -> float:
    """A REP_8 unit (decision time in REP_8) is refused until the SCREEN_8 result file and the REP seal are committed and verify (``rep_open``)."""
    lo, hi = windows8(s8)["rep"]["units"]
    if lo <= float(t) < hi and not rep_open:
        raise Refused(f"unit timed {c17.iso(t)} lies in REP_8 [{c17.iso(lo)}, {c17.iso(hi)}): REP_8 rows are refused before the SCREEN_8 result and the REP seal")
    return float(t)


def require_after(now: float, epoch: float, label: str) -> None:
    if float(now) < float(epoch):
        raise NotNow(f"{label}: not before {c17.iso(epoch)} (pending)")


def in_election_night(t: float) -> bool:
    return c16.in_election_night(t)


# =====================================================================================================================================================
# the event arm and keys
# =====================================================================================================================================================


def event_key(event_id: str | None, market_id: str | None) -> str:
    """The Gamma event id, else the market id (section 1.2)."""
    return str(event_id or "") or str(market_id or "")


def arm(event_id: str) -> int:
    """``int(sha256("cb17-arm-v1|" + event_id).hexdigest()[0], 16) mod 2``: arm 0 screens (SCREEN_8), arm 1 replicates (REP_8). Fixed before data."""
    if not event_id:
        raise Refused("event arm: empty event id")
    return int(hashlib.sha256((ARM_SALT + str(event_id)).encode()).hexdigest()[0], 16) % 2


def path_key(first_series_slug: str | None, event: str) -> str:
    """B and C path key: the first ``series_slugs`` entry, else the event (section 2.3)."""
    return str(first_series_slug or "") or f"event:{event}"


# =====================================================================================================================================================
# decision rules (Holm, gates, guards, placebos)
# =====================================================================================================================================================


def stage1_holm(pvals: dict[str, float | None]) -> dict:
    """The Stage-1 step-down over the FIXED k1 = 3 tests (B1, B2, C1); a test not run, not testable or pending enters with p = 1. First step 0.05/3 > 0.01."""
    bad = [k for k in pvals if k not in ("B1", "B2", "C1")]
    if bad:
        raise Refused(f"stage-1 Holm: {bad} are not CB17 branch-T Stage-1 tests")
    full = {k: 1.0 for k in ("B1", "B2", "C1")}
    full.update({k: (1.0 if v is None else float(v)) for k, v in pvals.items()})
    return {"k1": K1, "alpha": STAGE_ALPHA, "tests": c16.holm(full, STAGE_ALPHA)}


def stage1_advance(p: float | None, checks_ok: bool) -> bool:
    """Every binding check, one-sided p < 0.01 (strict) and the batch Holm (any p < 0.01 passes the first step 0.0167)."""
    return bool(checks_ok and p is not None and p < GATE_P and p < STAGE_ALPHA / K1)


def early_stage2_ok(p: float | None) -> bool:
    return p is not None and bool(p < STAGE_ALPHA / EARLY_ALPHA2_DIVISOR)


def stage2_final(pvals: dict[str, float | None]) -> dict:
    """ONE CB17-wide strict Holm at one-sided alpha 0.05 over every triggered Stage-2 test (<= 6 under branch T; econ tests enter with the max of their component p's; a triggered test
    that could not run enters with p = 1). Applied once; it can only add passes."""
    names = {t for v in FAMILY_REP_TESTS.values() for t in v}
    bad = [k for k in pvals if k not in names]
    if bad:
        raise Refused(f"stage-2 final Holm: {bad} are not CB17 Stage-2 tests")
    if len(pvals) > K2_MAX:
        raise Refused(f"stage-2 final Holm: {len(pvals)} tests > {K2_MAX}")
    full = {k: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k2": len(full), "alpha": STAGE_ALPHA, "tests": c16.holm(full, STAGE_ALPHA) if full else {}}


def stage2_pass(checks_ok: bool, p: float | None, final_holm_reject: bool = False) -> bool:
    return bool(checks_ok and (early_stage2_ok(p) or final_holm_reject))


def power_gate(se: float | None) -> dict:
    """``MDE = 3.80 x SE``; MDE > 1.0c -> "not run (power)". Only the SE and the MDE are written (never a proxy point estimate)."""
    if se is None or not math.isfinite(float(se)):
        return {"se": None, "mde": None, "run": False, "label": NOT_RUN_POWER, "reason": "no SE"}
    m = c17.MDE_FACTOR * float(se)
    return {"se": float(se), "mde": m, "run": bool(m <= POWER_MDE_MAX_C), "label": None if m <= POWER_MDE_MAX_C else NOT_RUN_POWER}


def availability(available: int, eligible: int) -> dict:
    """Available share < 60% of eligible -> "not testable (availability)"."""
    r = c16.availability(available, eligible)
    return {**r, "label": None if r["ok"] else NOT_TESTABLE_AVAIL}


def informative_ok(share: float | None) -> bool:
    return share is not None and math.isfinite(float(share)) and float(share) >= INFORMATIVE_MIN


def permutation_reach(observed: float, permuted: list[float | None], sign: float = 1.0) -> dict:
    """Within-strata permutation test (CB16 section 11 item 2's rule): a permuted coefficient REACHES the observed one if ``sign x b_perm >= sign x b_obs`` or it cannot be computed.
    Holds iff at most 3 of the 200 reach."""
    obs = float(observed)
    reach = sum(1 for b in permuted if b is None or not math.isfinite(float(b)) or not math.isfinite(obs) or sign * float(b) >= sign * obs)
    return {"n_draws": len(permuted), "reach": int(reach), "max_reach": PERM_MAX_REACH, "holds": bool(len(permuted) == PLACEBO_DRAWS and reach <= PERM_MAX_REACH)}


def composition_guard(primary_est: float, cond_est: float, cond_p: float | None, perm: dict, share: float | None, sign: float = 1.0) -> dict:
    """Binding composition guard (section 2.6 item 1): (a) the (unit x stratum) FE estimate keeps the sign and >= half of the primary with one-sided p < 0.05; (b) the within-strata
    permutation holds (<= 3 of 200 reach); both need the informativeness share >= 50%, else "uninformative" (the test cannot advance)."""
    informative = informative_ok(share)
    a = bool(math.isfinite(float(primary_est)) and math.isfinite(float(cond_est)) and sign * float(cond_est) > 0 and sign * float(cond_est) >= COMPOSITION_HALF * sign * float(primary_est)
             and cond_p is not None and float(cond_p) < COMPOSITION_P)
    b = bool(perm.get("holds"))
    return {"informative": informative, "share": share, "conditional_ok": a, "permutation_ok": b, "holds": bool(informative and a and b),
            "label": None if informative else UNINFORMATIVE}


def calibration_placebo(draw_ps: list[float | None]) -> dict:
    """Circular-shift calibration placebo (section 2.6 item 2): each of the 200 draws judged on one-sided p < 0.01 ALONE (no floor); holds iff at most 3 advance (1.5%). A draw that
    could not be computed does not advance (it is p = 1, as CB16's placebo_advance_rate)."""
    adv = sum(1 for p in draw_ps if p is not None and math.isfinite(float(p)) and float(p) < GATE_P)
    return {"n_draws": len(draw_ps), "advanced": int(adv), "max_advance": PLACEBO_MAX_ADVANCE, "rate": adv / len(draw_ps) if draw_ps else None,
            "holds": bool(len(draw_ps) == PLACEBO_DRAWS and adv <= PLACEBO_MAX_ADVANCE)}


def circular_shift(values: np.ndarray, unit_codes: np.ndarray, times: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One calibration draw: within each unit, order the units' rows by decision time and circularly shift the label/state by an offset drawn uniformly from {1, ..., n - 1}
    (units with n < 2 are left as they are). Keeps the label's own autocorrelation."""
    v = np.asarray(values).copy()
    u = np.asarray(unit_codes)
    t = np.asarray(times, float)
    order = np.lexsort((t, u))
    us = u[order]
    cuts = np.flatnonzero(us[1:] != us[:-1]) + 1
    for idx in np.split(order, cuts):
        n = len(idx)
        if n >= 2:
            k = int(rng.integers(1, n))
            v[idx] = np.roll(v[idx], k)
    return v


def econ_decision(diff: dict, level: dict) -> dict:
    """Two-component econ test (B1-econ, B2-econ, C1-econ): primary difference <= -0.5c (one-sided < 0) and the flagged group's net <= -1.0c; p = the max of the two component p's."""
    ps = [x.get("p") for x in (diff, level)]
    p = max(1.0 if v is None else float(v) for v in ps)
    floors = bool(diff.get("est") is not None and math.isfinite(float(diff["est"])) and float(diff["est"]) <= ECON_DIFF_FLOOR_C
                  and level.get("est") is not None and math.isfinite(float(level["est"])) and float(level["est"]) <= ECON_LEVEL_FLOOR_C)
    return {"p": p, "floors_ok": floors, "diff_floor": ECON_DIFF_FLOOR_C, "level_floor": ECON_LEVEL_FLOOR_C}


def pins_current(pins: dict[str, str]) -> dict[str, str]:
    """sha256 of the CURRENT source of every pinned function or class (``module.name``)."""
    from importlib import import_module  # noqa: PLC0415

    out = {}
    for key in pins:
        m, n = key.split(".", 1)
        obj = getattr(import_module(f"{__package__}.{m}"), n)
        out[key] = hashlib.sha256(inspect.getsource(obj).encode()).hexdigest()
    return out


def pins_ok() -> dict:
    """Every pinned CB13 and CB16 source equals its pin; a divergence is recorded and the dependent jobs refuse (exit 2)."""
    bad = {}
    for name, pins in (("cb13", CB13_PINS), ("cb16", CB16_PINS)):
        cur = pins_current(pins)
        bad[name] = sorted(k for k, v in pins.items() if cur.get(k) != v)
    return {"ok": not any(bad.values()), "diverged": bad, "n": len(CB13_PINS) + len(CB16_PINS)}


def declared() -> dict:
    return {"version": COMMON_VERSION, "branch": BRANCH, "branch_record": BRANCH_RECORD, "a_withdrawn": A_WITHDRAWN, "a_withdrawal": A_WITHDRAWAL,
            "pre": {"rules_sha256": PRE_RULES_SHA256, "results_sha256": PRE_RESULTS_SHA256},
            "counting": {"k1": K1, "k2_max": K2_MAX, "families": {f: list(t) for f, t in FAMILY_TESTS.items()}, "rep": {f: list(t) for f, t in FAMILY_REP_TESTS.items()},
                         "count_lines": {"creative_batch_17:B": 2, "creative_batch_17:C": 1}, "triggers": {k: list(v) for k, v in TRIGGERS.items()}, "kinds": list(TRIAL_KINDS),
                         "stage1": "p < 0.01 strict, the floor, every binding check, batch Holm one-sided 0.05 over k1 = 3", "stage2": "one CB17-wide strict Holm; early finishers alpha / 8",
                         "withdrawal": "A withdrawn uncounted (branch T) before any part commit; after a part commit every declared test is counted"},
            "dates": {"S_8": f"max({S8_EARLIEST}, the first 00:00Z at or after T17_rules + 24 h)", "window_days": 14, "frame_delay_h": 8, "leads_h": {k: v / 3600 for k, v in LEAD_S.items()},
                      "rep_read_lead_d": 7, "lookback_floor": c17.LOOKBACK_FLOOR, "election_night": list(c17.ELECTION_NIGHT), "t17_record": T17_RECORD_NAME},
            "arm": {"rule": "int(sha256('cb17-arm-v1|' + event_id).hexdigest()[0], 16) mod 2; event_id = Gamma event id else market id", "screen": ARM_SCREEN, "rep": ARM_REP},
            "inference": {"ways": list(WAYS), "small_g": SMALL_G, "n_wild": N_WILD, "seed_wild": SEED_WILD, "seeds": SEEDS, "seed_range": list(SEED_RANGE), "draws": PLACEBO_DRAWS,
                          "loo_day_p": LOO_DAY_P, "top_drop": TOP_DROP, "utc_day": "never in the max; leave-one-day-out keeps p < 0.05 and the sign"},
            "guards": {"composition": "(a) unit x stratum FE estimate keeps sign and >= half, p < 0.05; (b) within-strata permutation, <= 3 of 200 reach; informativeness >= 50% else uninformative",
                       "calibration": "circular shift within unit in time order, offset uniform on {1..n-1}; each draw judged on p < 0.01 alone; <= 3 of 200 advance",
                       "power": f"MDE = {c17.MDE_FACTOR} x SE > {POWER_MDE_MAX_C}c -> not run (power)", "availability": f"available < {AVAIL_MIN} of eligible -> not testable (availability)",
                       "robust": "p and the floor without the top 5 clusters of each way; leave-one-day-out"},
            "floors_c": {"stage1": FLOOR_C, "econ_diff": ECON_DIFF_FLOOR_C, "econ_level": ECON_LEVEL_FLOOR_C},
            "disk": {"caps_gb": DISK_CAP_GB, "total_gb": TOTAL_OUTPUT_CAP_GB, "free_min_gb": FREE_DISK_MIN_GB, "data_dumps_cap_gb": c17.DATA_DUMPS_CAP_GB},
            "refusals": {"roots": list(WINDOW_REFUSED_ROOTS), "prints_forbidden": list(WINDOW_FORBIDDEN_PRINT_FIELDS), "rep": "REP_8 units refused before the SCREEN_8 result and the REP seal"},
            "keys": {"cb16": CB16_KEYS, "rule": KEY_RULE}, "cost_map": COST_MAP, "pins": {"cb13": CB13_PINS, "cb16": CB16_PINS},
            "records": {"t17": T17_RECORD_NAME, "code_freeze": CODE_FREEZE_NAME, "rep_seal": REP_SEAL_NAME, "attestation": ATTESTATION_RULE},
            "smoke": {"criteria": list(SMOKE_CRITERIA), "needs": {k: list(v) for k, v in SMOKE_NEEDS.items()}, "consequence": "a failed criterion makes the dependent family terminal: not testable (source), counted once per declared test"},
            "labels": {"screen": LABEL_SCREEN, "rep": LABEL_REP, "econ": LABEL_ECON}}
