# ruff: noqa: E501
"""CB18 rules part ``pre`` (docs/research_lab/CREATIVE_BATCH_18.md sections 1.2-1.4, 2.3-2.6, 3, 4.1, 4.5, 11, 12).

Part ``pre`` is committed BEFORE any census code runs on data (section 1.4 Order: ``pre`` -> censuses q0502-q0506 -> routing record -> ``common``, ``S``). It holds, as hashed
UPPER_CASE constants and pure rule functions: the census inputs (seal file name and the exact pin counts), the cut-offs, the field whitelists and the whitelist exception
(``chg_1h/1d/1w``, ``uma_resolution_statuses`` and ``event_comment_count`` as byte-equality flags only), refused roots, every census gate (GS1-GS5, GP1-GP6) and routing rule (RS-0..RS-3,
P's route) with its constants, the strata ladders and the 60% selection rule, the proxy-SE recipe, the quiet-thinning rule, the census-to-spec value list, J4R_DISCLOSURE (R2 finding 1)
and GP5_RULE (R2 finding 3), the pinned sha256 of every imported function the censuses call, and the result writer that refuses outcome keys.

Nothing here reads data. The census code (``cb18_common``, ``cb18_pre``, ``cb18_map``) imports these rules and never redefines them; each census output records the part ``pre``
``rules_sha256`` and the sha256 of the census code that produced it. Parts ``common`` and ``S`` stay undeclared (``part_declared: false``) until the routing record exists.

EXPLORATORY / METHODS ONLY. No edge, calibration, tradability or profitability claim. AREPO never trades.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from . import cb8_common as cm
from . import cb12_common as c12

Refused = cm.Refused
NotNow = cm.NotNow

# =====================================================================================================================================================
# constants (hashed: every UPPER_CASE JSON-able constant of this module is part ``pre``)
# =====================================================================================================================================================
RULES_VERSION = "cb18-rules-v1"
PARTS = ("pre", "common", "S")
EVIDENCE_ROLE_HIST = "exploratory_historical"
DESIGN_DOC = "docs/research_lab/CREATIVE_BATCH_18.md"

# ---- census inputs (L4) ------------------------------------------------------------------------------------------------------------------------------
CENSUS_INPUTS_SEAL = "cb18_census_inputs.json"  # under docs/research_lab/seals/; every sha256 copied from the releases' files.sha256, never hashed from disk
LT3_C2_SEAL = "lt3_census_inputs_C2.json"  # q0501's 92 files must equal this seal's 92 entries (paths and sha256)
ARCHIVE_PREFIX = "data-dumps/research_lab/"
EXPECTED_CAPTURES = 67  # complete captures [2026-10-11T22:31Z, 2026-10-17T22:31Z] minus the six unavailable ones
EXPECTED_CAPTURE_FILES = ("rows.csv.gz", "rows_ext.csv.gz", "manifest.json", "ext_manifest.json")
EXPECTED_SWEEP_DIRS = 48  # 24 passes of 2026-10-15/16 x sweeps 1 and 2
EXPECTED_SWEEP_FILES = ("rows.csv.gz", "manifest.json")
EXPECTED_SAMPLES = 23  # the LT3-C2-sealed active-frame samples of 2026-10-16/17
EXPECTED_SAMPLE_FILES = ("manifest.json", "plan.json", "features.csv.gz", "trades.csv.gz")
EXPECTED_FILES_Q0500 = 364
EXPECTED_FILES_Q0501 = 92
UNSEALED_SAMPLE = "20261017T044014Z_4439c7c6"  # the 24th sample of 10-16/17: not in the C2 seal, never used; the pass pairs needing it are unavailable (counted)
Q0500_RELEASES = ("data-20261015-dsheikh", "data-20261016-dsheikh", "data-20261017-dsheikh", "data-20261018-dsheikh", "data-20261018-dsheikh-2", "data-20261019-dsheikh")
Q0501_RELEASES = ("data-20261017-dsheikh", "data-20261018-dsheikh", "data-20261019-dsheikh")

# ---- clocks (section 2.1; LT3/LT4 slot grid) ---------------------------------------------------------------------------------------------------------
GRID0_UTC = "2026-10-01T00:31:00Z"
GRID_S = 7200.0
SLOT_TOL_S = 1800.0
CAPTURE_TIME_RULE = "a capture's time is the received_utc of its last page (the maximum received_utc over its rows); its slot is the LT3 slot of its start stamp (first complete capture of a slot wins)"
SWEEP1_RULE = "sweep 1 of pass k = the book_sweeps directory whose manifest has snapshot_id = capture k's id, series_index 0 and state complete; its time is the token row's batch_receipt_utc"
CLOCK_ANOMALY_S = -5.0  # book age a = batch_receipt_utc - book_timestamp / 1000 < -5 s: clock anomaly (excluded, counted)
UPDATED_AT_RECEIPT_TOL_S = 5.0  # updated_at(k) must be at or before received_utc(k) + 5 s

# ---- dates and cut-offs (sections 1.2, 3) ------------------------------------------------------------------------------------------------------------
CENSUS_CUTOFF_SLOT = "2026-10-17T22:31:00Z"  # the last admitted capture slot (captures, samples)
CENSUS_ROW_CUTOFF = "2026-10-17T23:01:00Z"  # = the cut-off slot + its 30 min tolerance: no file stamp and no row time after it is ever read by a census path (the 22:31Z capture's pages and the 22:40Z sample's pre-origin rows end before it)
MAP_CUTOFF = "2026-10-16T00:00:00Z"  # q0506: no file or row at or after it
MAP_START = "2026-10-12T00:31:00Z"
MAP_UNDETERMINED_AFTER = "2026-10-15T20:00:00Z"
CENSUS_DAYS_SF = ("2026-10-15", "2026-10-16")  # S and F census days (UTC)
SF_FIRST_PREV = "2026-10-14T22:31:00Z"  # slot k - 1 of the first S / F unit
S_LOOKBACK_START = "2026-10-14T12:31:00Z"  # S reads captures k - 12 .. k only
P_LOOKBACK_START = "2026-10-15T16:31:00Z"  # P's longest look-back is k - 4 (R2 finding 4)
PR_SAMPLE_DAYS = ("2026-10-16", "2026-10-17")
P_USABLE_PASS_PAIRS = 21
P_PROJECTION_PAIRS = 28 * 12  # "projected" for P = census count x (28 x 12) / 21
UNAVAILABLE_CAPTURE_SLOTS = ("2026-10-14T00:31:00Z", "2026-10-14T02:31:00Z", "2026-10-14T04:31:00Z", "2026-10-14T06:31:00Z", "2026-10-14T08:31:00Z", "2026-10-14T10:31:00Z")
UNAVAILABLE_RULE = "in no host copy and in no release (checked against the committed catalogues through data-20261020-dsheikh); never 0, never interpolated; the off-grid -val copy 20261013T231958Z_80e78ef1 is never used"
LOOKBACK_FLOOR = "2026-10-26T00:00:00Z"  # window paths (not the censuses) refuse any capture, sweep or row timed before it
J4R = ("2026-10-16T00:00:00Z", "2026-10-21T00:00:00Z")
HOLDOUT = ("2026-10-21T00:00:00Z", "2026-10-26T00:00:00Z")  # CB13-T HOLDOUT: untouched by every CB18 path
J4R_DISCLOSURE = ("R2 finding 1: the pre-censuses read inside J4-R [2026-10-16, 2026-10-21): census S and F read the complete captures of 2026-10-16 and sweep 1 of its passes; census P and the "
                  "race map read the 23 trade samples of 2026-10-16/17 and the captures of 2026-10-16/17. CB18 follows LT3's rule (J4-R is refused only for maker mark-out objects; "
                  "LIVE_TESTS_3.md:529). No census object is a mark-out: every census reads origin-side fields at or before each unit's decision time (captures k - 12 .. k, sweep 1 of pass k, "
                  "trade rows with ts at or before the pass k + 1 origin) and writes counts, shares and standard errors only; no forward price, target, mark or outcome is read or written (the "
                  "result writer refuses such keys). 'J4-R untouched' holds for window paths only. The CB13-T HOLDOUT [2026-10-21, 2026-10-26) is untouched by every CB18 path (census row "
                  "cut-off 2026-10-17T23:01Z, window floor 2026-10-26T00:00Z).")
LADDER_ANCHOR = "2026-10-01T00:00:00Z"  # block index = floor((t - anchor) / block length)

# ---- refused roots and outputs (section 1.1) ---------------------------------------------------------------------------------------------------------
REFUSED_ROOTS = ("live_trades", "cross_venue_live", "surprise_live", "live_tests2", "live_tests3", "live_tests4", "creative_batch16", "creative_batch17", "cb8_holders", "holders",
                 "forecasts", "flow_screen", "history", "wallets")
REFUSED_ROOT_RES = (r"^e00[1-7]", r"^h\d+", r".*holdout.*")  # e001-e007, every h* experiment root, any holdout path
ALLOWED_INPUT_ROOTS = ("snapshots", "book_sweeps", "trade_samples")
ALLOWED_OUTPUT_ROOT_PARTS = ("cb18_census",)
CAPTURE_DIR_RE = r"^(\d{8}T\d{6}Z)_[0-9a-f]+$"
SWEEP_DIR_RE = r"^(\d{8}T\d{6}Z)_[0-9a-f]+$"
SAMPLE_DIR_RE = r"^(\d{8}T\d{6}Z)_[0-9a-f]+$"
FORBIDDEN_SAMPLE_FILES = ("wallets.csv.gz", "wallets.jsonl", "raw")

# ---- field whitelists (section 1.1; the whitelist exception) -----------------------------------------------------------------------------------------
CAPTURE_FIELDS = ("market_id", "condition_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid", "best_ask", "spread", "last_trade_price", "liquidity", "volume24hr",
                  "end_date", "updated_at", "neg_risk", "clob_token_id_0")
SIDECAR_FIELDS = ("market_id", "clob_token_id_1", "event_id", "fee_type", "fee_category", "fees_enabled", "fee_schedule", "taker_base_fee", "order_price_min_tick_size", "order_min_size",
                  "rewards_min_size", "rewards_max_spread", "clob_rewards", "series_slugs", "neg_risk_market_id")
BYTE_FLAG_CAPTURE_FIELDS = ("chg_1h", "chg_1d", "chg_1w")  # whitelist exception: raw byte equality between two captures only (never parsed, never written)
BYTE_FLAG_SIDECAR_FIELDS = ("uma_resolution_statuses", "event_comment_count")  # uma: byte equality + the empty-literal test; comment count: byte equality only
WHITELIST_EXCEPTION_FIELDS = ("chg_1h", "chg_1d", "chg_1w", "uma_resolution_statuses")  # forbidden in cb13_common (FORBIDDEN_CAPTURE_COLUMNS :135, FORBIDDEN_SIDECAR_COLUMNS :137)
UMA_EMPTY_LITERAL = "[]"  # ext_sidecar.ext_row: _text(m.get("umaResolutionStatuses")) writes "[]" for an empty list (JSON list or Gamma's string "[]"); fixed from the writer code, never from data
UMA_MISSING_LITERAL = ""  # an absent value is written as an empty CSV field (ext_sidecar docstring: "Absent fields are empty (missing), never 0"): class 'missing', NOT the empty literal (fails (10))
UMA_LITERAL_RULE = ("(10) holds iff the raw bytes at k - 1 and k are equal AND the bytes at k equal UMA_EMPTY_LITERAL exactly; a missing value (empty field) is class 'missing' and fails (10) "
                    "(unknown never counts as met, L2); any other bytes are 'non_empty' and fail (10)")
EQ_CAPTURE_NUMERIC = ("best_bid", "best_ask", "spread", "last_trade_price", "volume24hr", "liquidity")  # equal after a float64 parse (missing equals missing only)
EQ_CAPTURE_TEXT = ("closed", "active", "neg_risk")  # raw bytes
EQ_END_FIELD = "end_date"  # raw bytes; a change is the end_date-change class (CH07), never silent
EQ_SIDECAR_NUMERIC = ("taker_base_fee", "order_price_min_tick_size", "order_min_size", "rewards_min_size", "rewards_max_spread")
EQ_SIDECAR_TEXT = ("fee_type", "fee_category", "fees_enabled", "fee_schedule", "clob_rewards")
SWEEP_FIELDS = ("token_id", "market_id", "batch_receipt_utc", "book_timestamp", "state")
TRADE_FIELDS_P = ("market_id", "ts", "side", "price", "size", "outcome_index", "asset")
TRADE_FIELDS_R = ("market_id", "ts", "side", "price", "size", "outcome_index", "asset", "tx_hash")  # tx_hash: race partner test in memory only, never written
FEATURE_FIELDS = ("market_id", "status", "origin_utc", "n_returned", "trades_truncated")
FORBIDDEN_READ_FIELDS = ("outcome_prices", "outcomePrices", "closed_time", "closedTime", "question", "description", "title", "wallet", "wallet_hash", "proxyWallet", "maker", "taker", "name",
                         "pseudonym", "umaResolutionStatus", "result", "settlement_value", "open_interest", "volume_num")
FORBIDDEN_OUTPUT_KEYS = ("side", "wallet", "wallet_hash", "proxyWallet", "tx_hash", "transactionHash", "hash", "chg_1h", "chg_1d", "chg_1w", "uma_resolution_statuses", "outcome_prices",
                         "outcomePrices", "closed_time", "closedTime", "result", "settlement_value", "mark", "mark_out", "beta", "est", "estimate", "coef", "effect", "pnl", "net", "target",
                         "y", "y_post", "mid_k12", "last_mid", "side_of_half", "upper_tail", "lower_tail")
OUTCOME_KEY_TOKENS = ("beta", "est", "estimate", "mark", "marks", "pnl", "net", "outcome", "outcomes", "coef", "effect", "slope", "target", "targets", "forward", "return", "returns",
                      "resolution", "resolved", "winner", "payout")  # a result key whose FIRST underscore token is one of these is refused ("markets_x" passes, "mark_x" does not)

# ---- CB18-S census (sections 3.1, 4.1) ---------------------------------------------------------------------------------------------------------------
S_SPREAD_MAX = 0.10
QUOTE_TOL = 1e-12
SPREAD_RULE = "spread = the capture's Gamma spread field if finite, else ask - bid; a band or cap edge is compared with a 1e-12 tolerance (spread <= 0.10 + 1e-12; mid in [0.02 - 1e-12, 0.98 + 1e-12])"
ARM_PROJECTION_RULE = "projected arm-0 count = census units whose Gamma event (else market) id hashes to arm 0 x W / census days; unsplit = all census units x W / census days"
P_EFFECTIVE_RULE = "effective = units in markets with >= 2 units of the tested population (fade or none) over the 21 usable pass pairs"
S_MID_RANGE = (0.02, 0.98)
S_END_MIN_H = 27.0  # as-of end_date unknown or more than 27 h after t_k
S_LOOKBACK_SLOTS = (3, 12)  # |mid_k - mid_{k-3}| and |mid_k - mid_{k-12}|; Y_pre = |mid_k - mid_{k-12}|
PRIOR_QUIET_CAP = 11  # the prior-quiet count reads intervals back to (k - 12, k - 11) at most (R1 finding 5)
PRIOR_QUIET_RULE = ("census control: consecutive prior intervals (k - j - 1, k - j), j = 1 .. 11, that are capture-quiet (both captures present and open, every (8) field incl. the chg_* byte "
                    "flags equal, (10) met, updated_at present and equal); the book-untouched rule is NOT applied to prior intervals in the census (sweeps of 2026-10-14 are not pinned); a "
                    "missing capture before the chain breaks or reaches 11 makes the count unknown -> lookback_unavailable (declared gap) or lookback_missing (other)")
DORMANCY_CAP_S = 86400.0  # dormancy = log book age at sweep 1 of pass k, capped at 24 h (log1p of seconds)
BURST_SHARE = 0.20  # a capture with > 20% of its otherwise eligible non-sports units silent is a burst capture (excluded, counted)
BURST_RULE = "denominator: non-sports units of the capture passing (1)-(10) whose class is silent or quiet; numerator: the silent ones; burst iff numerator > 0.20 x denominator"
S_CLASSES = ("silent", "quiet", "upd_earlier", "upd_after_receipt", "upd_missing")
CHG_FLAG_STATUS = ("none", "1h_only", "1d_or_1w_not_all", "all_three")  # mutually exclusive
GS1_MAX = 0.50
GS2_MAX = 0.50
GS3_MAX = 0.10
GS4_MIN_PER_DAY = 200.0
GS5_SHARE_MIN = 0.60
GS_DEFINITIONS = {
    "GS1": "updated_at changed (epoch ms differ) in <= 50% of non-sports intervals passing (1)-(9) (numerically unchanged incl. the chg_* byte flags, book untouched) with updated_at parseable at both",
    "GS2": "updated_at changed in <= 50% of non-sports intervals passing (1)-(7) with updated_at parseable at both",
    "GS3": "updated_at missing / unparseable / after received_utc + 5 s at k - 1 or k in <= 10% of intervals passing (1)-(7) (sports and non-sports)",
    "GS4": "silent non-sports units passing (1)-(11) (R1 definition: chg_* flags equal, uma empty literal at k) per census day >= 200 (count / 2 census days)",
    "GS5": "permutable share >= 60% at some ladder level on silent and quiet units thinned at the route's own q (GS5_CB at q_CB for RS-1, GS5_LT at q_LT for RS-2); fails at both -> RS-0",
}

# ---- planning MDE and routing (sections 2.4, 3.1, 3.2) -----------------------------------------------------------------------------------------------
M_CB = 3.80  # (z_0.99 + z_0.80) x 1.2
M_LT = 3.388
PESSIMISM = 1.5
DE_FLOOR = 3.0
ICC_EXAMPLE = 0.02  # an example value, not an estimate: the computed DE may only raise the floor of 3
W_ARM_DAYS = 14
W_LT_DAYS = 28
FLOOR_S_C = 1.0
FLOOR_P_C = 0.5
SD_S_FALLBACK_C = 6.0  # RS-1 / RS-2 NaN-SE fallback
SD_P_C = 5.0  # GP5 formula
THIN_RATES = (1.0, 0.5, 0.25, 0.125)
FRAME_MAX_ROWS = 1_500_000
DE_RULE = "DE_computed = 1 + (m_W - 1) x 0.02, m = sum n_e^2 / sum n_e by event, m_W = m x W / census days; DE_gate = max(3.0, DE_computed); NaN m -> NaN -> the gate fails"
S_DE_POPULATION = "silent non-sports units passing (1)-(11) (after the burst exclusion), by Gamma event id (else market id)"
RS_RULES = {
    "RS-0": "any of GS1-GS4 fails, or GS5 fails at both q_CB and q_LT -> CB18-S dropped uncounted (recorded with counts)",
    "RS-1": "gates pass (GS5 at q_CB) and MDE_RS1 = 3.80 x SE_proxy(q_CB) x sqrt(census days / 14) x sqrt(2) x sqrt(max(3, DE_W14 / DE_census)) x 1.5 <= 1.0c -> CB route (parts common, S); NaN SE -> section 2.4 formula (M 3.80, SD 6c, projected arm-0 silent n1, projected thinned arm-0 quiet n0, DE_gate, 1.5)",
    "RS-2": "else, gates pass (GS5 at q_LT) and MDE_RS2 = 3.388 x SE_proxy(q_LT) x sqrt(census days / 28) x sqrt(max(3, DE_W28 / DE_census)) x 1.5 <= 1.0c -> LT5 member; NaN SE -> formula with M 3.388 and unsplit 28-day counts",
    "RS-3": "else dropped uncounted",
    "both": "MDE_RS1 and MDE_RS2 are both written into the routing record whichever route is taken (Q5)",
}
THIN_RULE = ("quiet units kept iff int(sha256('cb18-thin-v1|' + market_id + '|' + slot_iso).hexdigest()[:8], 16) / 2^32 < q; q_CB = the largest of {1, 1/2, 1/4, 1/8} whose projected arm-0 "
             "14-day frame (silent + q x quiet, arm-0 share by the event-arm hash, x 14 / census days) is <= 1.5 M rows; q_LT the same on the unsplit 28-day frame; fixed from counts before "
             "its proxy SE; none qualifies -> q = null and the route's MDE is NaN (fails)")
THIN_PREFIX = "cb18-thin-v1|"
ARM_PREFIX = "cb18-arm-v1|"
FRAME_POPULATION = "silent and quiet non-sports units passing (1)-(12) whose look-back status is not lookback_missing (lookback_unavailable units are counted in the frame: the gap is a census artefact)"
PROXY_SE_RECIPE = ("SE only (no point estimate leaves the function): within-market fixed-effect OLS (cb17_pre.fe_cluster_se, pinned) of the pre-origin proxy on the tested label first plus the "
                   "declared controls; CR1 per way; the census SE is the MAX over the event way and the UTC 6 h block way whatever their G (no UTC-day or two-way way at G = 2; section 2.4); "
                   "units in cents. S: Y_pre = |mid_k - mid_{k-12}| x 100 on silent + quiet units thinned at q, controls = log1p volume24hr_k, spread_k, |mid_k - 0.5|, log hours to the as-of "
                   "end (capped at 30 d; 0 and an unknown flag if unknown), dormancy, prior-quiet count (cap 11), the event_comment_count change flag, UTC 6 h band dummies (the two |mid| "
                   "controls left out); lookback_unavailable and lookback_missing units are left out. P: c_pre = s x (mid_{k-2} - mid_{k-4}) x 100 on fade, follow and none units, regressors "
                   "1[fade], 1[follow], log |x|, spread_k, log1p volume24hr_k, pass k + 1 stratum dummies; the SE of the 1[fade] coefficient")
HOURS_TO_END_CAP_H = 30 * 24.0
SE_WAYS = ("event", "block6")
DORMANCY_TERCILE_RULE = "global tercile cut points (numpy 'linear' quantiles 1/3, 2/3) of dormancy over the S frame population (features only); a value <= the lower cut is tercile 0, <= the upper cut 1, else 2"

# ---- strata ladders and selection (section 2.3, 4.1 check (2)) ---------------------------------------------------------------------------------------
PERM_LADDER = {0: ("market", 1), 1: ("market", 2), 2: ("market", 7)}  # level: (unit, block days)
PERMUTABLE_MIN_UNITS = 4  # a stratum is permutable iff it holds >= 4 units AND both label values (binary) / a non-constant value (continuous)
SELECT_SHARE_MIN = 0.60  # finest level whose worn-data permutable share is >= 60%; none -> the test fails its census gate
COMP_LADDER = {0: ("band6", "dormancy_tercile", "spread_band"), 1: ("dormancy_tercile", "spread_band"), 2: ("dormancy_tercile",)}
COMP_SPREAD_EDGE = 0.02  # spread band {<= 2c, > 2c}
COMP_INFORMATIVE_RULE = "share of silent + quiet units in composition strata holding both labels; the finest level with share >= 60% (none -> null, reported)"

# ---- CB18-P census (section 3.2, 4.2) ----------------------------------------------------------------------------------------------------------------
P_MOVE = {"min_abs_x": 0.01, "ltp_tol": 1e-09, "vol_tol": 0.01, "parallel_min": 0.005, "parallel_max_diff": 0.005, "one_sided_max": 0.0005}  # LT3 spec 'move' (live_tests3_v1.json)
P_SPREAD_MAX = 0.10
P_MID_RANGE = (0.02, 0.98)
P_END_AFTER_NEXT_H = 9.0  # as-of end more than t_{k+1} + 9 h
P_ACTIVITY_WINDOW_S = 6 * 3600.0
P_CLASSES = ("fade", "follow", "none", "balanced")
GP1_MIN_28D = 2000.0
GP2_RANGE = (0.20, 0.80)
GP3_MAX = 0.10
GP4_MAX = 0.05
GP5_MAX_C = 0.5
GP6_SHARE_MIN = 0.60
GP5_RULE = ("R2 finding 3: GP5 holds iff MDE_GP5 = max(MDE_formula, MDE_proxy) <= 0.5c. MDE_formula = 3.388 x 5c x sqrt(1/n_fade + 1/n_none) x sqrt(DE_gate) x 1.5 on projected effective "
            "fades and projected effective none units (projected = census x 28 x 12 / 21; effective = units in markets with >= 2 units of the population), DE_gate = max(3.0, DE_computed with "
            "W = 28). MDE_proxy = 3.388 x SE_proxy x sqrt(21 / (28 x 12)) x sqrt(max(3, DE_W28 / DE_census)) x 1.5, SE_proxy = the 1[fade] coefficient's census SE on c_pre (max over the "
            "event and 6 h block ways). Both values are written. NaN proxy -> MDE_formula alone; NaN formula -> GP5 fails.")
GP_DEFINITIONS = {
    "GP1": "projected 28-day fades >= 2,000 in the routed population",
    "GP2": "fades between 20% and 80% of reacted (fade + follow) units",
    "GP3": "side unusable (not BUY/SELL, or outcome unknown) <= 10% of rows in the state windows",
    "GP4": "truncated <= 5% of otherwise eligible units",
    "GP5": GP5_RULE,
    "GP6": "permutable share (fade versus none) >= 60% at some ladder level",
}
P_ROUTE_RULE = "non-sports primary if GP1-GP6 hold on non-sports units; else all categories (sports split reported) if they hold on all categories; else dropped uncounted. A pass -> LT5 member. No 42-day branch."

# ---- CB18-R race map (section 3.3) -------------------------------------------------------------------------------------------------------------------
R_WINDOW_S = 6 * 3600.0
R_MIN_SIGNED_ROWS = 3
R_COVERAGE_RULE = "E016's rule: a sampled market (features status ok) is covered iff n_returned < 500 (trade_sample.TRADE_LIMIT) or its oldest row has ts <= origin - 6 h"
R_RACE_RULE = "a row is raced iff another row of the same market has the same ts and a different tx_hash (same ts and same tx_hash is not a race); a blank tx_hash never partners"
R_PRICE_BAND_EDGES = (0.10, 0.30, 0.70, 0.90)
R_GAP_HIST_S = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
R_QUANTISED_RULE = "ts is read as quantised at 2 s or coarser iff the gap histogram holds >= 100 gaps of 1-10 s and 1-s gaps are < 5% of them; then every 'same second' in the map reads 'same block'"
R_QUANTISED_MIN_GAPS = 100
R_QUANTISED_ONE_S_MAX = 0.05
R_DECILES = 10

# ---- CB18-F census (section 3.4) ---------------------------------------------------------------------------------------------------------------------
F_BREAKPOINTS = (10, 12, 20, 24, 50)
F_HALF_WIDTH = 10
F_SURGE = {"ratio": 3.0, "min_abs": 500.0}  # E017's S label (LT3 spec 'surge'): vol_k >= 3 vol_{k-1}, vol_k - vol_{k-1} >= 500, vol_{k-1} > 0
F_RULE = ("per capture k (with slot k - 1 present) and fee_type: non-sports active open markets grouped by Gamma event id (else market id); events ranked by the sum of members' volume24hr "
          "(descending, ties by event id); a rank position p in [max(1, B - 10), B + 10] changes hands iff the event at p differs between k - 1 and k; an entry across B is an event with "
          "rank <= B at k and > B (or absent) at k - 1, an exit the reverse; a crossing carries the surge label iff any member market has E017's S label at k. No price is read.")

# ---- CB18-M last-mid map (section 4.5) ---------------------------------------------------------------------------------------------------------------
M_BAND_TAIL = 0.49  # d = |mid - 0.5| > 0.49
M_BAND_NEAR = 0.45  # 0.45 <= d <= 0.49
M_BANDS = ("d_gt_0.49", "d_0.45_0.49", "d_lt_0.45", "no_two_sided")
M_FALLBACK_WINDOWS_H = (6.0, 24.0)
M_HORIZON_BINS = ("past_end", "0-2h", "2-24h", "gt24h", "unknown")
M_LAG_EDGES_H = (-24.0, -2.0, 0.0, 2.0, 6.0, 24.0, 72.0)
M_PROJECTION_DAYS = (21, 60, 90)
M_ARM_CLASSES = {"CH163": "non-sports standalone and neg-risk members", "CH164": "non-sports, all structures", "CH157_E017_carry": "non-sports, all structures", "CH62": "all categories"}
M_EXIT_RULE = ("exit = a market present in complete capture j and absent from the next two available complete captures of the map window; recorded at its last presence; last presence "
               "after 2026-10-15T20:00Z -> undetermined; exits recorded at 2026-10-13T22:31Z (the last capture before the declared gap) carry gap_adjacent; re-appearance after an exit counted")
M_FORBIDDEN = "no comparison of an earlier price with the last mid, no return, no P&L, no side of 0.5 (bands are folded d = |mid - 0.5|)"

# ---- census-to-spec values (section 1.4; the only census values a later part may carry) -------------------------------------------------------------
CENSUS_TO_SPEC = {"S": ("selected permutation strata level (at the route's q)", "q_CB", "q_LT", "dormancy tercile cut points", "composition strata level"),
                  "P": ("routed population (non-sports / all categories)", "selected permutation strata level"),
                  "R": (), "F": (), "M": ()}
CENSUS_JOBS = {"q0502": "census-s", "q0503": "census-p", "q0504": "map-race", "q0505": "census-f", "q0506": "map-lastmid"}
RESULT_NAMES = {"S": "S.json", "P": "P.json", "R": "R_map.json", "F": "F.json", "M": "M.json"}
DISK_CAP_GB = 20.0
DATA_DUMPS_CAP_GB = 40.0
MEM_MB = {"census-s": 380, "census-p": 380, "map-race": 390, "census-f": 300, "map-lastmid": 350}
TRIAL_KIND = "cb18_descriptive"
TEMPFAIL_MESSAGE = "restore byte for byte, hash-checked"

# ---- imported functions, pinned by source sha256 (section 6); a divergence refuses -------------------------------------------------------------------
PINNED_IMPORTS = {
    "live_tests3.classify": "e3162be24a254de2eb2194d46c1b871cd6029ea12b8aeb4b7d6dae6bfaea5997",
    "live_tests3.slot_of": "0f7a5b20e6c4b575f3bd805b31508ec14a8c96665e7b90e33a96fa4040c18ee3",
    "live_tests3.slot_time": "c940afefbe8faeedcc9ab534e5989872cde0ec87084e4e9db4264ce59f1441cd",
    "live_tests3.grid0": "f62b78369e86b67024ff28177c6f5ef88f6192f17788010181f5851a33cc2752",
    "live_tests3.signs": "5c0a6d57dbfe278fc02a04c367979223afca7237dcd8a019619b6c5d9c476aad",
    "cb17_census.is_sports_sidecar": "76fc0cd4ae9e4294d26ff567968959c4c118c6e78be87a179d494cf4daa8cb61",
    "cb17_pre.fe_cluster_se": "a2c90a6ad95b0be4fc0a057a8d6b8e32121889b3c09f9f272b601871ba1f3682",
    "cb17_pre._demean": "cedd32d423e5defb499fb5022f589bb1a50169ea6c0fbc8b79412281c472076a",
    "cb17_pre._codes": "df40c0455d0dba00d39a32e70e614f290840776ffc287fce81680c327a6f3115",
}
PIN_NOTE = ("live_tests3.* pinned at this commit from the merged integration branch (LT3's spec has no code pin yet); the cb17_* pins equal the CB17 part-pre func_sources_sha256 frozen in "
            "seals/cb17_rules.json and verify_pins checks them against that file too; a divergence refuses (never re-pinned silently)")

RULES_MACHINERY = ("rules_part_doc", "rules_part_file_doc", "rules_file_doc", "write_rules", "verify_rules", "part_funcs", "declared", "pinned_objects", "verify_pins")

# staging switches (lower-case: not hashed; declaring a later part edits only these lines)
_declared_parts = ("pre",)
_undeclared_reason = "part not declared yet: landed after the routing record, only if CB18-S routes to the batch (CREATIVE_BATCH_18.md section 1.4 Order)"


# =====================================================================================================================================================
# small helpers
# =====================================================================================================================================================


def ep(s: str) -> float:
    return c12.parse_iso(s)


def iso(t: float) -> str:
    return cm.iso(t)


def finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def fnum(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def block_index(t: float, days: int) -> int:
    return int((float(t) - ep(LADDER_ANCHOR)) // (86400.0 * days))


def band6(t: float) -> int:
    return int((float(t) % 86400.0) // 21600.0)


def block6(t: float) -> int:
    return int(float(t) // 21600.0)


def utc_day(t: float) -> str:
    return iso(t)[:10]


# =====================================================================================================================================================
# refusals: roots, cut-offs, floor, outputs
# =====================================================================================================================================================


def refuse_path(path: Path) -> Path:
    """Input AND output guard: never open a refused root (section 1.1), a holdout path, an e001-e007 or h* experiment root, or a sample's wallet / raw files."""
    p = Path(path)
    for part in p.parts:
        if part in REFUSED_ROOTS or any(re.match(rx, part) for rx in REFUSED_ROOT_RES):
            raise Refused(f"path {path} is under a refused root ({part}); CB18 never opens it")
    if p.name in FORBIDDEN_SAMPLE_FILES:
        raise Refused(f"{p.name}: wallet and raw sample files are never opened by CB18")
    return p


def guard_census_time(t: float, what: str = "row", cutoff: str = CENSUS_ROW_CUTOFF) -> float:
    """A census path refuses any file stamp or row timed after its cut-off (strictly after; the map's cut-off is exclusive) and any unparseable time."""
    t = float(t)
    if not math.isfinite(t):
        raise Refused(f"{what}: unparseable time")
    lim = ep(cutoff)
    if (t >= lim) if cutoff == MAP_CUTOFF else (t > lim):
        raise Refused(f"{what} timed {iso(t)} is after the census cut-off {cutoff}")
    if ep(HOLDOUT[0]) <= t < ep(HOLDOUT[1]):
        raise Refused(f"{what} timed {iso(t)} lies in the CB13-T HOLDOUT {HOLDOUT}")
    return t


def guard_window_time(t: float, what: str = "row") -> float:
    """Window paths (parts common / S, later) refuse any capture, sweep or row timed before the lookback floor 2026-10-26T00:00Z."""
    t = float(t)
    if not (math.isfinite(t) and t >= ep(LOOKBACK_FLOOR)):
        raise Refused(f"{what} timed before the lookback floor {LOOKBACK_FLOOR} (a window path never reads it)")
    return t


def assert_clean_result(doc: Any, path: str = "$") -> None:
    """A census result holds counts, shares, standard errors and MDEs only: refuse a key naming a forbidden field, an outcome, a target, a mark or a point estimate (recursive)."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            ks = str(k)
            if ks in FORBIDDEN_OUTPUT_KEYS or ks.lower().split("_", 1)[0] in OUTCOME_KEY_TOKENS or ks.lower().startswith("wallet"):
                raise Refused(f"forbidden key {ks!r} at {path}: a CB18 census writes counts, shares and standard errors only")
            assert_clean_result(v, f"{path}.{ks}")
    elif isinstance(doc, (list, tuple)):
        for i, v in enumerate(doc):
            assert_clean_result(v, f"{path}[{i}]")


def require_output_root(path: Path) -> Path:
    p = refuse_path(Path(path))
    if not any(x in ALLOWED_OUTPUT_ROOT_PARTS for x in p.parts):
        raise Refused(f"CB18 censuses write only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return p


def write_result_once(path: Path, doc: dict) -> str:
    """Write-once JSON (clean keys only; NaN written as null). Returns the sha256 of the written file."""
    require_output_root(Path(path))
    assert_clean_result(doc)
    cm.write_once_json(Path(path), json.loads(json.dumps(doc, default=_json_default, allow_nan=True), parse_constant=lambda _c: None))
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_default(o):
    try:
        import numpy as np  # noqa: PLC0415

        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(o, (set, frozenset, tuple)):
        return list(o)
    return str(o)


# =====================================================================================================================================================
# hashes: event arm, quiet thinning
# =====================================================================================================================================================


def arm_of(event_id: str) -> int:
    return int(hashlib.sha256((ARM_PREFIX + str(event_id)).encode()).hexdigest()[0], 16) % 2


def thin_u(market_id: str, slot_iso: str) -> float:
    return int(hashlib.sha256((THIN_PREFIX + str(market_id) + "|" + str(slot_iso)).encode()).hexdigest()[:8], 16) / 2.0**32


def thin_keep(market_id: str, slot_iso: str, q: float | None) -> bool:
    """Quiet-unit thinning: independent of every feature and target (a hash of ids only). q = None keeps nothing (no admissible rate)."""
    if q is None or not finite(q):
        return False
    return thin_u(market_id, slot_iso) < float(q)


# =====================================================================================================================================================
# class rules (section 4.1)
# =====================================================================================================================================================


def s_class(upd_prev_ms: float, upd_k_ms: float, recv_k_ms: float) -> str:
    """silent: updated_at(k) != updated_at(k-1), updated_at(k) <= received_utc(k) + 5 s and not earlier than updated_at(k-1); quiet: equal; anything else excluded (named)."""
    if not (finite(upd_prev_ms) and finite(upd_k_ms) and finite(recv_k_ms)):
        return "upd_missing"
    if float(upd_k_ms) > float(recv_k_ms) + UPDATED_AT_RECEIPT_TOL_S * 1000.0:
        return "upd_after_receipt"
    if float(upd_k_ms) == float(upd_prev_ms):
        return "quiet"
    if float(upd_k_ms) < float(upd_prev_ms):
        return "upd_earlier"
    return "silent"


def chg_flag_status(eq_1h: bool, eq_1d: bool, eq_1w: bool) -> str:
    """Mutually exclusive split of the three chg_* byte-equality flags (True = bytes equal)."""
    ch = (not eq_1h, not eq_1d, not eq_1w)
    if not any(ch):
        return "none"
    if all(ch):
        return "all_three"
    if ch[0] and not ch[1] and not ch[2]:
        return "1h_only"
    return "1d_or_1w_not_all"


def book_untouched(stamp0_ms: float, stamp1_ms: float, t_prev: float) -> bool | None:
    """(9): both tokens' book_timestamp at or before t_{k-1}; outcome-0 only where the sweep holds no outcome-1 row (stamp1 NaN; the caller flags it). None if the outcome-0 stamp is missing."""
    if not finite(stamp0_ms):
        return None
    ok0 = float(stamp0_ms) / 1000.0 <= float(t_prev)
    if not finite(stamp1_ms):
        return ok0
    return ok0 and float(stamp1_ms) / 1000.0 <= float(t_prev)


def uma_class(raw: str | None) -> str:
    if raw is None or raw == UMA_MISSING_LITERAL:
        return "missing"
    return "empty_literal" if raw == UMA_EMPTY_LITERAL else "non_empty"


def p_state(f: float, n_rows: int, s: int) -> str:
    """CB18-P state of a unit: fade sign(f) = -s; follow sign(f) = s; none no row; balanced rows with f = 0."""
    if int(n_rows) == 0:
        return "none"
    if not finite(f) or float(f) == 0.0:
        return "balanced"
    return "fade" if (1 if f > 0 else -1) == -int(s) else "follow"


def fold_band(mid: float) -> str:
    """CB18-M folded band of a last two-sided mid (no side): d = |mid - 0.5|."""
    if not finite(mid):
        return "no_two_sided"
    d = round(abs(float(mid) - 0.5), 9)  # quotes sit on ticks: rounding removes float asymmetry (0.95 - 0.5 != 0.5 - 0.05), so no side leaks through a band edge
    if d > M_BAND_TAIL:
        return "d_gt_0.49"
    if d >= M_BAND_NEAR:
        return "d_0.45_0.49"
    return "d_lt_0.45"


def surge_label(vol_k: float, vol_prev: float) -> bool | None:
    """E017's S label (F's confound): None if either volume is unknown or vol_{k-1} <= 0."""
    if not (finite(vol_k) and finite(vol_prev)) or float(vol_prev) <= 0:
        return None
    return float(vol_k) >= F_SURGE["ratio"] * float(vol_prev) and float(vol_k) - float(vol_prev) >= F_SURGE["min_abs"]


def two_sided(bid: float, ask: float) -> bool:
    return finite(bid) and finite(ask) and 0.0 < float(bid) < float(ask) <= 1.0


# =====================================================================================================================================================
# strata ladders and selection (section 2.3)
# =====================================================================================================================================================


def perm_stratum(level: int, market_id: str, t: float) -> tuple:
    if level not in PERM_LADDER:
        raise Refused(f"strata level {level!r}: one of {tuple(PERM_LADDER)}")
    return (str(market_id), block_index(t, PERM_LADDER[level][1]))


def permutable_share(units: Iterable[tuple]) -> dict:
    """Units (stratum key, binary label); a unit is in a permutable stratum iff the stratum holds >= 4 units with both label values. Returns numerator, denominator, share (None if empty)."""
    cells: dict = {}
    for key, lab in units:
        n, mask = cells.get(key, (0, 0))
        cells[key] = (n + 1, mask | (2 if int(lab) else 1))
    den = sum(n for n, _ in cells.values())
    num = sum(n for n, m in cells.values() if n >= PERMUTABLE_MIN_UNITS and m == 3)
    return {"numerator": num, "denominator": den, "share": (num / den) if den else None}


def informative_share(units: Iterable[tuple]) -> dict:
    """Composition strata: share of units in strata holding both label values (no size minimum)."""
    cells: dict = {}
    for key, lab in units:
        n, mask = cells.get(key, (0, 0))
        cells[key] = (n + 1, mask | (2 if int(lab) else 1))
    den = sum(n for n, _ in cells.values())
    num = sum(n for n, m in cells.values() if m == 3)
    return {"numerator": num, "denominator": den, "share": (num / den) if den else None}


def select_level(shares: dict) -> int | None:
    """The finest level (0 finest) whose share is >= 60%; None if none (or unknown): the test fails its census gate (L2)."""
    for lv in sorted(shares):
        s = shares.get(lv)
        if s is not None and finite(s) and float(s) >= SELECT_SHARE_MIN:
            return lv
    return None


def spread_band(spread: float) -> int:
    return 0 if float(spread) <= COMP_SPREAD_EDGE + 1e-12 else 1


def tercile_of(x: float, cuts: tuple[float, float]) -> int:
    return 0 if x <= cuts[0] else 1 if x <= cuts[1] else 2


def comp_stratum(level: int, t: float, dorm_tercile: int, spread: float) -> tuple:
    if level == 0:
        return (band6(t), int(dorm_tercile), spread_band(spread))
    if level == 1:
        return (int(dorm_tercile), spread_band(spread))
    if level == 2:
        return (int(dorm_tercile),)
    raise Refused(f"composition level {level!r}: one of 0, 1, 2")


# =====================================================================================================================================================
# design effect, planning MDE, gates and routes (sections 2.4, 3.1, 3.2); every value fails closed (NaN fails, L2)
# =====================================================================================================================================================


def m_by_event(sizes: Iterable[int]) -> float:
    """m = sum n_e^2 / sum n_e over event cluster sizes; NaN if empty."""
    s1 = s2 = 0.0
    for n in sizes:
        s1 += float(n)
        s2 += float(n) ** 2
    return s2 / s1 if s1 > 0 else math.nan


def de_computed(m: float, w_days: float, census_days: float) -> float:
    if not (finite(m) and float(m) > 0 and finite(w_days) and finite(census_days) and float(census_days) > 0):
        return math.nan
    m_w = float(m) * float(w_days) / float(census_days)
    return 1.0 + (m_w - 1.0) * ICC_EXAMPLE


def de_gate(m: float, w_days: float, census_days: float) -> float:
    """DE_gate = max(3.0, DE_computed); never below 3; NaN m -> NaN (fails)."""
    d = de_computed(m, w_days, census_days)
    return max(DE_FLOOR, d) if finite(d) else math.nan


def de_inflation(de_w: float, de_census: float) -> float:
    """sqrt(max(3, DE_W / DE_census)): never below sqrt(3); NaN on NaN or a non-positive denominator."""
    if not (finite(de_w) and finite(de_census) and float(de_census) > 0):
        return math.nan
    return math.sqrt(max(DE_FLOOR, float(de_w) / float(de_census)))


def mde_formula(M: float, sd_c: float, n1: float, n0: float, de_g: float) -> float:
    """Two-class pessimistic MDE (cents): M x SD x sqrt(1/n1 + 1/n0) x sqrt(DE_gate) x 1.5; both class terms always enter; NaN on a missing / non-positive input."""
    if not all(finite(v) for v in (M, sd_c, n1, n0, de_g)) or float(n1) <= 0 or float(n0) <= 0 or float(de_g) < DE_FLOOR:
        return math.nan
    return float(M) * float(sd_c) * math.sqrt(1.0 / float(n1) + 1.0 / float(n0)) * math.sqrt(float(de_g)) * PESSIMISM


def mde_rs1(se_c: float, census_days: float, de_w14: float, de_census: float) -> float:
    if not (finite(se_c) and float(se_c) > 0 and finite(census_days) and float(census_days) > 0):
        return math.nan
    inf = de_inflation(de_w14, de_census)
    if not finite(inf):
        return math.nan
    return M_CB * float(se_c) * math.sqrt(float(census_days) / W_ARM_DAYS) * math.sqrt(2.0) * inf * PESSIMISM


def mde_rs2(se_c: float, census_days: float, de_w28: float, de_census: float) -> float:
    if not (finite(se_c) and float(se_c) > 0 and finite(census_days) and float(census_days) > 0):
        return math.nan
    inf = de_inflation(de_w28, de_census)
    if not finite(inf):
        return math.nan
    return M_LT * float(se_c) * math.sqrt(float(census_days) / W_LT_DAYS) * inf * PESSIMISM


def mde_gp5_proxy(se_c: float, de_w28: float, de_census: float) -> float:
    if not (finite(se_c) and float(se_c) > 0):
        return math.nan
    inf = de_inflation(de_w28, de_census)
    if not finite(inf):
        return math.nan
    return M_LT * float(se_c) * math.sqrt(P_USABLE_PASS_PAIRS / P_PROJECTION_PAIRS) * inf * PESSIMISM


def mde_gp5(mde_form: float, mde_proxy: float) -> float:
    """GP5_RULE: max(formula, proxy); NaN proxy -> formula alone; NaN formula -> NaN (fails)."""
    if not finite(mde_form):
        return math.nan
    if not finite(mde_proxy):
        return float(mde_form)
    return max(float(mde_form), float(mde_proxy))


def gate_le(value, limit: float) -> bool:
    return finite(value) and float(value) <= float(limit)


def gate_ge(value, limit: float) -> bool:
    return finite(value) and float(value) >= float(limit)


def gate_in(value, lo: float, hi: float) -> bool:
    return finite(value) and float(lo) <= float(value) <= float(hi)


def thin_rate(silent_arm: float, quiet_arm: float, census_days: float, w_days: float) -> float | None:
    """The largest q in {1, 1/2, 1/4, 1/8} whose projected frame (silent + q x quiet) x W / census days is <= 1.5 M rows; None if none qualifies or a count is unknown."""
    if not (finite(silent_arm) and finite(quiet_arm) and finite(census_days) and float(census_days) > 0):
        return None
    for q in THIN_RATES:
        if (float(silent_arm) + q * float(quiet_arm)) * float(w_days) / float(census_days) <= FRAME_MAX_ROWS:
            return q
    return None


def gs_gates(c: dict) -> dict:
    """GS1-GS5 from the census counts (shares and per-day counts); only True passes."""
    return {"GS1": gate_le(c.get("gs1_share"), GS1_MAX), "GS2": gate_le(c.get("gs2_share"), GS2_MAX), "GS3": gate_le(c.get("gs3_share"), GS3_MAX),
            "GS4": gate_ge(c.get("gs4_silent_per_day"), GS4_MIN_PER_DAY), "GS5_CB": c.get("gs5_level_cb") is not None, "GS5_LT": c.get("gs5_level_lt") is not None}


def route_s(gates: dict, mde1: float, mde2: float) -> dict:
    """RS-0..RS-3 by section 3.1 (counts only). Both MDEs are returned whatever the route."""
    base = all(gates.get(g) is True for g in ("GS1", "GS2", "GS3", "GS4"))
    rec = {"mde_rs1_c": mde1 if finite(mde1) else None, "mde_rs2_c": mde2 if finite(mde2) else None, "gates": dict(gates)}
    if not base or not (gates.get("GS5_CB") is True or gates.get("GS5_LT") is True):
        return {**rec, "route": "RS-0", "meaning": "dropped uncounted at the census gates"}
    if gates.get("GS5_CB") is True and gate_le(mde1, FLOOR_S_C):
        return {**rec, "route": "RS-1", "meaning": "CB route (parts common, S)"}
    if gates.get("GS5_LT") is True and gate_le(mde2, FLOOR_S_C):
        return {**rec, "route": "RS-2", "meaning": "LT5 member"}
    return {**rec, "route": "RS-3", "meaning": "dropped uncounted (power)"}


def gp_gates(c: dict) -> dict:
    return {"GP1": gate_ge(c.get("fades_28d_projected"), GP1_MIN_28D), "GP2": gate_in(c.get("fade_share_of_reacted"), *GP2_RANGE), "GP3": gate_le(c.get("side_unusable_share"), GP3_MAX),
            "GP4": gate_le(c.get("truncated_share"), GP4_MAX), "GP5": gate_le(c.get("mde_gp5_c"), GP5_MAX_C), "GP6": c.get("gp6_level") is not None}


def route_p(nonsports: dict, allcat: dict) -> dict:
    if all(v is True for v in nonsports.values()) and nonsports:
        return {"route": "LT5 member", "population": "non-sports"}
    if all(v is True for v in allcat.values()) and allcat:
        return {"route": "LT5 member", "population": "all categories (sports split reported)"}
    return {"route": "dropped uncounted", "population": None}


# =====================================================================================================================================================
# rules machinery (not hashed): part documents, the rules file, verification, pinned imports
# =====================================================================================================================================================


def declared() -> dict:
    return {"design": DESIGN_DOC, "order": "pre -> censuses q0502-q0506 -> routing record -> common, S (CB route only) -> T18_rules", "j4r_disclosure": J4R_DISCLOSURE,
            "gp5_rule": GP5_RULE, "gs": GS_DEFINITIONS, "rs": RS_RULES, "gp": GP_DEFINITIONS, "p_route": P_ROUTE_RULE, "thin": THIN_RULE, "proxy_se": PROXY_SE_RECIPE,
            "uma": UMA_LITERAL_RULE, "prior_quiet": PRIOR_QUIET_RULE, "burst": BURST_RULE, "de": DE_RULE, "unavailable": UNAVAILABLE_RULE, "race": R_RACE_RULE, "coverage": R_COVERAGE_RULE,
            "quantised": R_QUANTISED_RULE, "front_page": F_RULE, "exit": M_EXIT_RULE, "map_forbidden": M_FORBIDDEN, "capture_time": CAPTURE_TIME_RULE, "sweep1": SWEEP1_RULE,
            "frame_population": FRAME_POPULATION, "spread": SPREAD_RULE, "arm_projection": ARM_PROJECTION_RULE, "p_effective": P_EFFECTIVE_RULE, "dormancy_terciles": DORMANCY_TERCILE_RULE, "composition": COMP_INFORMATIVE_RULE, "pins": PIN_NOTE,
            "wallet": "no CB18 census reads or writes a wallet field; tx_hash is used in memory by the race map only and never written"}


def pinned_objects() -> dict:
    from . import cb17_census, cb17_pre, live_tests3  # noqa: PLC0415

    mods = {"live_tests3": live_tests3, "cb17_census": cb17_census, "cb17_pre": cb17_pre}
    return {k: getattr(mods[k.split(".", 1)[0]], k.split(".", 1)[1]) for k in PINNED_IMPORTS}


def verify_pins(cb17_rules_path: Path | None = None) -> dict:
    """Refuse unless every imported function's source sha256 equals its pin; the cb17_* pins are also checked against CB17's frozen part pre."""
    got = {k: hashlib.sha256(inspect.getsource(v).encode()).hexdigest() for k, v in pinned_objects().items()}
    bad = {k: got[k] for k, want in PINNED_IMPORTS.items() if got[k] != want}
    if bad:
        raise Refused(f"pinned import changed (sha256 of source): {sorted(bad)}; CB18 refuses (never re-pinned silently)")
    p = Path(cb17_rules_path or (cm.SEALS_DIR / "cb17_rules.json"))
    if p.exists():
        frozen = (json.loads(p.read_text()).get("parts", {}).get("pre", {}) or {}).get("func_sources_sha256", {})
        for k in PINNED_IMPORTS:
            if k.startswith("cb17_") and frozen.get(k) != got[k]:
                raise Refused(f"pinned import {k} differs from CB17's frozen part pre ({p.name})")
    return got


def part_funcs() -> list:
    this = importlib.import_module(__name__)
    return c12.module_funcs(this, exclude=RULES_MACHINERY)


def rules_part_doc(part: str) -> dict:
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    if part not in _declared_parts:
        return {"part": part, "part_declared": False, "rules_version": RULES_VERSION, "reason": _undeclared_reason}
    this = importlib.import_module(__name__)
    src = {f"cb18_rules_pre.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in part_funcs()}
    return {"part": part, "part_declared": True, "rules_version": RULES_VERSION, "modules": ["cb18_rules_pre"], "constants": {"cb18_rules_pre": c12.module_constants(this)},
            "declared": declared(), "pinned_imports_sha256": verify_pins(),
            "funcs_sha256": hashlib.sha256("\n".join(src[k] for k in sorted(src)).encode()).hexdigest(), "func_sources_sha256": dict(sorted(src.items()))}


def rules_part_file_doc(part: str) -> dict:
    d = json.loads(json.dumps(rules_part_doc(part), sort_keys=True, default=str))
    if d.get("part_declared") is False:
        return {**d, "rules_sha256": None}
    return {**d, "rules_sha256": cm.sha_obj(d)}


def rules_file_doc() -> dict:
    return {"rules_version": RULES_VERSION, "parts": {p: rules_part_file_doc(p) for p in PARTS}}


def write_rules(path: Path | None = None) -> Path:
    """Write seals/cb18_rules.json. A declared part is never rewritten; an undeclared part may be declared later."""
    path = Path(path or (cm.SEALS_DIR / "cb18_rules.json"))
    want = rules_file_doc()
    if path.exists():
        have = json.loads(path.read_text())
        if have.get("rules_version") != RULES_VERSION:
            raise Refused(f"{path} exists with rules_version {have.get('rules_version')}; a rules file is never rewritten")
        for p in PARTS:
            h = (have.get("parts") or {}).get(p)
            if h is not None and h.get("part_declared") is not False and h != want["parts"][p]:
                raise Refused(f"{path} exists with a different, already declared part {p}; a rules file is never rewritten")
        if (have.get("parts") or {}) == want["parts"]:
            return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "pre") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's (and the file is committed). Returns the part's ``rules_sha256``."""
    path = Path(path or (cm.SEALS_DIR / "cb18_rules.json"))
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    if not path.exists():
        raise Refused(f"rules file {path} not found")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(path):
            raise Refused(f"rules file {path} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(path.read_text())
    except ValueError as exc:
        raise Refused(f"rules file {path} unreadable") from exc
    if doc.get("rules_version") != RULES_VERSION:
        raise Refused(f"rules file {path} has rules_version {doc.get('rules_version')!r} != {RULES_VERSION!r}")
    have = (doc.get("parts") or {}).get(part)
    if have is None or have.get("part_declared") is False:
        raise Refused(f"rules part {part} is not declared in {path}")
    want = rules_part_file_doc(part)
    if have != want:
        raise Refused(f"rules hash mismatch (part {part}): file {have.get('rules_sha256')} != code {want.get('rules_sha256')}")
    return want["rules_sha256"]
