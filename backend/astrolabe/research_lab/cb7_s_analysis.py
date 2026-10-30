# ruff: noqa: E501
"""CB7-S analysis (docs/research_lab/CREATIVE_BATCH_7.md CB7-S, 2.5, 2.7a): S1, the specificity discount. EXPLORATORY: no edge, calibration or profitability claim.

The census (q0147c, 2026-10-30) found gate GS FALSE (787 S1 units against 3,000; 329 event x week clusters against 1,000). Under 2.7 S1 is therefore "not testable", p = 1, and COUNTED
(2.5). This module implements only that declared consequence. It does NOT implement the S1 slope, the S placebos, the marker shuffle or S2: with GS false they are never run, the design
has no rescue for a failed GS (2.7a), and S2 / S1-rep are not run because Stage 2 is registered only if S1 advanced. If a census ever recorded GS true, ``screen_s`` refuses.

Dependency on q0156 (the text-edit audit) REMOVED: the text-stability gate (xi) can only block an advance and S1 cannot advance, so ``screen --family S`` writes the counted
line immediately (freeze check 2026-10-30 MUST 3; recorded in the result as ``dependency_removed``).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from . import cb7_astats as st
from . import cb7_common as cm

Refused = cm.Refused

TEST = "S1"
JOB = "q0148_cb7_screen_S"
DEPENDENCY_REMOVED = ("q0156_cb7_text_edit_audit: not required. S1 is not testable (GS failed), so the text-stability gate (xi), which can only block an advance, cannot change the outcome "
                      "(freeze check 2026-10-30, MUST 3; ledger entry of the same date)")


def screen_s(cb7_dir: Path, seals_dir: Path, *, freeze: dict, census: dict, trials_path: Path, wall_clock: Callable[[], float] = time.time) -> dict:
    """q0148: write the counted S1 line. Refuses unless the census records GS false (or a terminal state of the h8_text run)."""
    from . import cb7_declaration as D  # noqa: PLC0415

    s = census.get("S") or {}
    gs = (s.get("gate_GS") or {})
    if s.get("status") == "ok" and gs.get("GS") is not False:
        raise Refused("the census does not record GS false: the S1 slope analysis is not implemented (it was never needed); refusing")
    state = str(s.get("status"))
    if s.get("status") == "ok":
        label = "not testable (GS failed in the census)"
        why = {k: gs.get(k) for k in ("units", "event_week_clusters", "series_event_clusters", "within_cell_sd_c")}
    elif state == cm.NOT_RUN_TOKEN:
        label, why = "not run (deadline)", {"state": state}
    else:
        label, why = f"not testable ({state})", {"state": state}
    cum = st.cumulative(trials_path)
    res = st.not_testable_doc(label, cum, gate_GS=why, dependency_removed=DEPENDENCY_REMOVED, s2="not run: Stage 2 is registered only if S1 advanced",
                              s1_rep="not run (same reason)", text_edit_audit="not run (not required)", placebo={"skipped": label})
    header = {"inputs": {"census_json_sha256": freeze["spec"].get("census_json_sha256")}, "s1_mde_cents_from_census": s.get("s1_mde_per_marker_cents")}
    return st.finish(TEST, res, out_root=Path(cb7_dir), seals_dir=Path(seals_dir), freeze=freeze, declaration_sha=D.declaration_sha256(), trials_path=Path(trials_path),
                     placebo=None, descriptive={"gate_GS": why, "dependency_removed": DEPENDENCY_REMOVED}, header=header, wall_clock=wall_clock)
