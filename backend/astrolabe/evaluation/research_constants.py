"""Constants for the edge-research infrastructure (prompt sections 2-14).

Kept in one place so cadences, horizons, roles, execution assumptions, walk-forward windows and
the edge-acceptance minimums are documented and testable rather than scattered as magic values.
None of these are tuned to outcomes; they are declared up front (anti-drift, prompt section 17D).
"""
from __future__ import annotations

# --- Versions (prompt sections 3, 4) ----------------------------------------------------------
# Model version = the signal/direction/confidence/scoring logic; calculation version = the
# analytics pipeline. Both are frozen onto every cohort so a result can always be traced to the
# exact code that produced it, and a later model change starts a new, separable evidence stream.
MODEL_VERSION = "arepo-model-1"

# --- Cohort cadences (prompt section 3) -------------------------------------------------------
# Each cadence freezes an independent immutable cohort. A cadence is identified by this string and
# a cut-off timestamp snapped to the cadence boundary, so (cadence, cutoff_at) is a unique key.
CADENCE_6H = "6h"
CADENCE_DAILY = "daily"
CADENCE_WEEKLY = "weekly"
CADENCES = (CADENCE_6H, CADENCE_DAILY, CADENCE_WEEKLY)

# --- Entry roles (prompt section 2) -----------------------------------------------------------
# Every screened market/token is frozen with an explicit role, so the research sample is the FULL
# universe and the public top-N never restricts what is measured.
ROLE_PUBLIC = "public_selection"        # would be shown to users (top-N directional)
ROLE_SHADOW = "shadow_directional"      # directional but below the public cut
ROLE_OBSERVATION = "observation"        # non-directional but anomalous, kept for context
ROLE_ABSTENTION = "abstention_control"  # no directional view: a labelled control group
ROLES = (ROLE_PUBLIC, ROLE_SHADOW, ROLE_OBSERVATION, ROLE_ABSTENTION)

# How many directional entries are flagged public_selection (the visible product cut). Research
# freezes ALL of them regardless; this only sets the public/shadow label.
PUBLIC_SELECTION_SIZE = 10

# --- Outcome horizons (prompt section 5) ------------------------------------------------------
# Forward repricing is measured at each; final resolution is separate (prompt section 7).
HORIZON_1H = "1h"
HORIZON_6H = "6h"
HORIZON_24H = "24h"
HORIZON_7D = "7d"
RESEARCH_HORIZONS: dict[str, int] = {
    HORIZON_1H: 3_600,
    HORIZON_6H: 21_600,
    HORIZON_24H: 86_400,
    HORIZON_7D: 604_800,
}
# A forward observation is "exact" if within this tolerance of the target time, else "nearest".
NEAREST_TOLERANCE_SECONDS = 900  # 15 minutes

# --- Result states (prompt section 5) ---------------------------------------------------------
RESULT_CORRECT = "correct"
RESULT_INCORRECT = "incorrect"
RESULT_FLAT = "flat"
RESULT_PENDING = "pending"
RESULT_UNAVAILABLE = "unavailable"
RESULT_INVALID = "invalid"

# A forward move at or below this magnitude (probability points) is FLAT (shared with replay_stats
# so every predictor treats flats identically). Predeclared, not tuned.
FLAT_EPS = 0.01

# Prospective-Replay PRODUCT "no price change" threshold (refinement prompt sections 3, 6, 7). This
# answers a different, plainer question than the edge hit-rate: "did the stored midpoint move at all
# in Arepo's direction between the freeze and the horizon?" A market is "No price change" only when
# the midpoint did not move (a tiny float-comparison guard, NOT the 0.01 materiality floor). This is
# a display classification for the Replay table and the "did the market move as expected?" summary;
# it is never used for any edge verdict, calibration or baseline hit rate.
REPLAY_MOVE_EPS = 1e-6

# --- Universe degradation (prompt section 5) --------------------------------------------------
# A freeze with too few usable markets, or too many excluded ones, must not silently produce a
# misleading cohort. Below the minimum usable count OR above the maximum exclusion rate the freeze
# is REJECTED (no cohort created). A non-rejecting freeze that still excluded a notable share is
# recorded as DEGRADED so the research status can surface it honestly.
MIN_USABLE_UNIVERSE = 5          # fewer usable markets than this => reject the freeze
MAX_EXCLUSION_RATE = 0.6         # more than 60% of discovered markets excluded => reject
DEGRADED_EXCLUSION_RATE = 0.2    # more than 20% excluded (but not rejected) => mark degraded

# --- Prospective-timestamp lateness policy (causal-timing audit) ------------------------------
# A cohort's causal origin is ``frozen_at`` (WHEN the prediction was actually made), never its
# ``cutoff_at`` cadence-boundary LABEL. Lateness = frozen_at - cutoff_at. In production the freeze
# crons fire a few minutes after each boundary, so lateness is tiny; a large lateness means the run
# was missed/manual and its boundary label would be misleading.
LATENESS_WARN_SECONDS = 900       # frozen more than 15 min after the boundary => flag "late"
# Frozen this long after the boundary => "excessively late": still CAUSALLY VALID (horizons run from
# frozen_at), but excluded from comparable performance so a stale/backfilled run can't be presented
# as a genuine scheduled prediction.
LATENESS_MAX_SECONDS = 21_600     # 6 hours

# --- Execution model (prompt section 6) -------------------------------------------------------
STANDARD_STAKE = 100.0            # standard evaluation stake, in quote units
FEE_RATE = 0.0                    # Polymarket charges no protocol fee today; kept explicit
SPREAD_CROSS_FRACTION = 0.5       # entry crosses half the quoted spread
# Depth-aware slippage: consuming a fraction of near-mid depth moves the price. Slippage in
# probability points = SLIPPAGE_COEFF * (stake_at_risk / near_mid_depth), capped. When depth is
# missing it stays missing (executable performance is unavailable, never assumed infinite).
SLIPPAGE_COEFF = 0.5
SLIPPAGE_CAP = 0.10               # never model more than 10 probability points of slippage
MIN_PRICE = 0.01
MAX_PRICE = 0.99

# --- Walk-forward (prompt section 10) ---------------------------------------------------------
PARTITION_DEVELOPMENT = "development"     # earliest data; model/threshold design only
PARTITION_THRESHOLD = "threshold"         # threshold selection only; never reported as performance
PARTITION_HELDOUT = "heldout"             # reserved held-out evaluation
PARTITION_LIVE = "live"                   # genuine prospective, frozen before outcomes
PARTITIONS = (PARTITION_DEVELOPMENT, PARTITION_THRESHOLD, PARTITION_HELDOUT, PARTITION_LIVE)
# Minimum evaluable markets per walk-forward window before its result is anything but inconclusive.
MIN_WINDOW_SAMPLE = 30

# --- Edge acceptance + calibration (prompt sections 11, 14) -----------------------------------
MIN_PROSPECTIVE_SAMPLE = 100      # predeclared min evaluable prospective markets for an edge test
MIN_CALIBRATION_SAMPLE = 200      # predeclared min resolved predictions before calibration
CALIBRATION_UNAVAILABLE_MSG = (
    "Calibration unavailable. Arepo does not yet have enough real resolved predictions to estimate "
    "calibrated probabilities."
)
INCONCLUSIVE_MSG = (
    "Current results are inconclusive. Arepo has not yet demonstrated predictive advantage "
    "over the tested baselines."
)
NOT_ENOUGH_EVIDENCE_MSG = (
    "Arepo has not yet accumulated enough prospective evidence to determine whether it has an "
    "edge. The system is collecting frozen predictions automatically."
)
