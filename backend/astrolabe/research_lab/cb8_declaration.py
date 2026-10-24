# ruff: noqa: E501
"""CB8 declaration (docs/research_lab/CREATIVE_BATCH_8.md 5.1, 8): the content of the CB8 freeze file ``model_specs/cb8_v1.json``.

DRAFT GENERATOR ONLY. The freeze file binds the test tables, so it is written exactly once, AT THE CB8 FREEZE (after the science-reviewer freeze check of
the analysis code and the committed census counts), by ``run_cb8.py write-spec``, and committed in its own commit. Until then ``screen`` and
``replicate`` refuse for every family. ``run_cb8.py write-spec --dry-run`` prints the would-be content without writing anything.

The spec carries, per family, the analysis-rules hash and the data-rules hash the screens check (B: ``b_*``; W: ``w_*``; H: ``h_*``), plus a
``declaration_sha256`` over those six hashes and the hypothesis table. Each rules hash already covers every population rule, threshold, cap, window, seed,
floor, gate and the source of every rule function of its family (the per-family rules files under ``docs/research_lab/seals/``).
"""

from __future__ import annotations

import json
from pathlib import Path

from . import cb8_common as cm

VERSION = "cb8-declaration-v1"
SPEC_PATH = Path(__file__).resolve().parent / "model_specs" / "cb8_v1.json"

HYPOTHESES_CB8 = {
    "B1": {"family": "B", "kind": "economic", "direction": "> 0", "unit": "(market-day, checkpoint) traded unit, SCREEN weeks (Stage 2: HOLDOUT weeks)",
           "statistic": "mean net per share = Y_fav - a - f(a) at the recorded pmxt best ask, |z| >= 3 in the last 5 minutes; day-unit tail gate binding"},
    "W1": {"family": "W", "kind": "economic", "direction": "< 0", "unit": "print in S (non-sports, SCREEN events; Stage 2: HOLDOUT events)",
           "statistic": "mean resting-maker mark-out at 2 h plus forgone rebate after a two-clip same-wallet footprint; route gate on kept fills"},
    "H1": {"family": "H", "kind": "mechanism with a binding economic route gate", "direction": "> 0",
           "unit": "matched (exit, control) pair, non-sports, window 1 (Stage 2: window 2, post-freeze)",
           "statistic": "mean mo(exit) - mo(control) of rank-1 holder exits with c >= 0.5; route gate mean mo(exit) >= +0.5c; a presence filter at most"},
}
COUNTING = {"fixed": ["B1", "W1", "H1"], "conditional": ["B1-rep", "W1-rep", "H1-rep"], "stage1_alpha": 0.01, "stage2": "Holm, one-sided alpha 0.05, k <= 3"}


def rule_hashes() -> dict[str, str]:
    """The six hashes the screens check, computed from the committed code (no file is read except through the modules' own code)."""
    from . import cb8_b_analysis as ba  # noqa: PLC0415
    from . import cb8_h_analysis as ha  # noqa: PLC0415
    from . import cb8_updown as u  # noqa: PLC0415
    from . import cb8_w_analysis as wa  # noqa: PLC0415

    return {"b_analysis_rules_sha256": ba.rules_file_doc()["rules_sha256"], "b_data_rules_sha256": u.rules_file_doc()["rules_sha256"],
            "w_analysis_rules_sha256": wa.rules_file_doc()["rules_sha256"], "w_data_rules_sha256": wa.data_rules_sha(),
            "h_analysis_rules_sha256": ha.rules_file_doc()["rules_sha256"], "h_data_rules_sha256": ha.data_rules_sha()}


def spec_payload() -> dict:
    hashes = rule_hashes()
    body = {"version": VERSION, **hashes, "hypotheses": HYPOTHESES_CB8, "counting": COUNTING}
    return {**body, "declaration_sha256": cm.sha_obj(body)}


def verify_rules_files_committed(*, require_committed: bool = True) -> dict[str, str]:
    """Refuse unless every family's analysis and data rules file exists (committed, when required) and equals the code: the freeze binds committed rules only."""
    from . import cb8_b_analysis as ba  # noqa: PLC0415
    from . import cb8_h_analysis as ha  # noqa: PLC0415
    from . import cb8_updown as u  # noqa: PLC0415
    from . import cb8_w_analysis as wa  # noqa: PLC0415

    out = {"b_analysis": ba.verify_analysis_rules(require_committed=require_committed), "b_data": u.verify_rules(u.RULES_FILE, require_committed=require_committed),
           "w_analysis": wa.verify_analysis_rules(require_committed=require_committed), "h_analysis": ha.verify_analysis_rules(require_committed=require_committed)}
    out["w_data"], _ = cm.verify_rules("flow", cm.FLOW_RULES_FILE, require_committed=require_committed)
    out["h_data"], _ = cm.verify_rules("holders", cm.HOLDERS_RULES_FILE, require_committed=require_committed)
    return out


def write_spec(path: Path | None = None, *, require_committed: bool = True) -> dict:
    """Write the CB8 freeze file. Refuses to overwrite and refuses unless every rules file is committed and equals the code. Run ONLY at the CB8 freeze."""
    path = Path(path or SPEC_PATH)
    if path.exists():
        raise cm.Refused(f"{path} exists; a frozen declaration is never overwritten")
    verify_rules_files_committed(require_committed=require_committed)
    p = spec_payload()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(p, indent=1, sort_keys=True) + "\n")
    return p
