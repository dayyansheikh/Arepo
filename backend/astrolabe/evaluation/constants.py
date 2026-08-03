"""Shared constants for the evaluation engine.

Kept in one place so the eligibility thresholds, horizons, provenance classes and
portfolio assumptions are documented once and referenced everywhere (and by the
docs). Changing a threshold here changes selection going forward only; it can never
alter an already-frozen cohort.
"""
from __future__ import annotations

# Calculation version stamped onto every snapshot. Bump when the analytics that
# produce a signal change in a way that affects selection, so old cohorts stay
# attributable to the exact method that produced them.
CALCULATION_VERSION = "arepo-eval-1"

# Provenance classes. Statistics aggregate PROSPECTIVE (and, only when explicitly
# requested, RECONSTRUCTED). SYNTHETIC is never mixed into real performance.
PROVENANCE_PROSPECTIVE = "prospective"
PROVENANCE_RECONSTRUCTED = "reconstructed"
PROVENANCE_SYNTHETIC = "synthetic"
PROVENANCE_CLASSES = (PROVENANCE_PROSPECTIVE, PROVENANCE_RECONSTRUCTED, PROVENANCE_SYNTHETIC)

# Weekly cohort target size and the fixed cut-off (Sunday 23:59:59 UTC).
COHORT_TARGET_SIZE = 10

# Eligibility thresholds (documented; applied only to NEW selection, never retroactive).
MIN_STRENGTH = 0.30           # a signal must be at least this strong to qualify
MIN_DATA_QUALITY_RANK = 1     # >= "limited" (poor=0, limited=1, good=2)
DATA_QUALITY_RANK = {"poor": 0, "limited": 1, "good": 2}

# Forward-price horizons (label -> seconds after the freeze timestamp).
HORIZON_1H = "1h"
HORIZON_24H = "24h"
HORIZON_7D = "7d"
HORIZON_CLOSE = "close"
FORWARD_HORIZONS = {
    HORIZON_1H: 3600,
    HORIZON_24H: 86_400,
    HORIZON_7D: 604_800,
}

# Portfolio simulation assumptions (a simulation, not trading advice).
DEFAULT_STAKE = 100.0         # fixed notional per signal
DEFAULT_FEE_RATE = 0.0        # proportion of stake charged per position (round trip)
# Entry crosses half the quoted spread (buy at midpoint + spread/2); documented so the
# simulation never assumes a fill better than what was quoted at the signal timestamp.
SPREAD_CROSS_FRACTION = 0.5
