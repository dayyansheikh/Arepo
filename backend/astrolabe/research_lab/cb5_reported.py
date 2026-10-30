"""CB5 not-yet-implemented future paths, deliberately OUTSIDE the declaration hash (CB5 section 10).

K1-R (q0114, the live-pair replication of K1) needs the receipt-timed 2-minute grid mapping and the
E009/E010 owner sign-off. Its loader and grid mapping do not exist yet; this module will be sealed
(own hash, own committed spec) before K1-R runs. Until then run_k1r only enforces the
cross_venue_live/ refusal in cb5_hours (which IS hashed) and stops. Nothing here changes a declared
threshold, formula or population of the hashed CB5 modules.
"""
from __future__ import annotations

from . import cb5_hours

NOTE = "unsealed future path: K1-R loader and grid mapping not implemented; outside the CB5 hash"


def run_k1r() -> None:
    cb5_hours.refuse_path(cb5_hours.CV_ROOT.parent / cb5_hours.LIVE_ROOT_NAME)
    raise NotImplementedError(
        "K1-R needs the receipt-timed 2-minute grid mapping and the E009/E010 owner sign-off; "
        "declared in CB5-K, not implemented (cb5_reported.py, unsealed)"
    )
