# ruff: noqa: E501
"""Generate ``astrolabe/research_lab/live_tests9_base.py``: unmodified copies of the LT3/LT4/LT5/LT7/LT8 functions that LT9's code phase 1
(the fresh seal and the counts-only censuses CR9 / CC9 / CS9) uses (LIVE_TESTS_9.md 8.1: "vendored, not imported"; the same mechanism as
``vendor_lt7_base.py`` and ``vendor_lt8_base.py``).

Sources, each REFUSED unless its raw sha256 equals the pin below (LIVE_TESTS_9.md 8.1):
* ``live_tests7_base.py`` 2e8baa90... (flat: holds the unmodified, prefix-free LT3/LT4/LT5 copies; each name's original file and hash is carried as
  ``origin``) and ``live_tests7.py`` e1c5c0c6... (the 13.7 carry code: ``RewardCarry`` with its ``_status_array`` fix, ``listed_carry24h_v2``), the
  hashes the design names;
* ``live_tests8.py`` d1b252cf... (LT8 at 86e32dd3, the census-code-checked commit: amendment 13.7 and its erratum, re-check FIXES_OK_WITH_NOTES;
  LT8's census outputs q0622-q0623 have not run when this is written, so 8.1's fallback applies and the copies are re-verified against LT8's census
  outputs at LT9's freeze check: :func:`census_output_check` refuses when an LT8 census output records another ``live_tests8.py`` hash).
The only change to a copied source is the removal of the module prefix (``b.`` for ``live_tests7.py`` and ``live_tests8.py``, the alias of their
vendored bases, whose names are the same LT7 copies; nothing for ``live_tests7_base.py``). Provenance per name: the source file, its sha256 at copy
time, the prefix regex, the sha256 of the prefix-normalised source and the source commit; ``tests/unit/test_research_lab_live_tests9.py`` re-checks
them. Module-level constants a copied function reads are restated in the header and a unit test checks them against their sources.

Names of 8.1's list NOT vendored here (no phase-1 census needs them; phase 2 vendors them by the same script): ``status_codes``, ``is_late``, ``fit``,
``attrition``, ``lee_bounds``, ``paper_taker``, ``econ``, ``holm`` (``live_tests3*``, not hash-pinned for this vendoring). ``expanding_demean`` is
reached through the vendored ``demean`` (``bounce_decomp.expanding_demean``, a hashed dependency).

    LT9_VENDOR_SRC=<dir with the three pinned blobs> python scripts/vendor_lt9_base.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "astrolabe" / "research_lab"
OUT = HERE / "live_tests9_base.py"
SRC = Path(os.environ["LT9_VENDOR_SRC"]) if os.environ.get("LT9_VENDOR_SRC") else HERE
SOURCE_PINS = {
    "live_tests7_base.py": "2e8baa9007f60d4c7d3553932906e8e9bac60aa43f35368ba7f2c1ff498c7e20",
    "live_tests7.py": "e1c5c0c68f7c44d3d5038f9c28324008a4a8132e35f148721a33078d706766a0",
    "live_tests8.py": "d1b252cff35d50675f91cb7c85a30a93e14b5b0a45cbbe970e382d802399e6d0",
}
SOURCE_COMMIT = {"live_tests7_base.py": "8dd013b9", "live_tests7.py": "8dd013b9", "live_tests8.py": "86e32dd3"}
PREFIX = {"live_tests7_base.py": r"(?!)", "live_tests7.py": r"\bb\.", "live_tests8.py": r"\bb\."}

PICK = {
    "live_tests7_base.py": [
        "epoch", "iso", "now_ts", "sha256_file", "git_commit", "_json", "append_jsonl", "dir_bytes", "du_bytes", "_truthy", "grid0", "slot_of",
        "slot_time", "_manifest", "State", "scan_captures", "scan_sweeps", "fee_rates", "category_cols", "series_frame", "read_series", "_look", "_mid",
        "tight_arr", "classify", "move_join", "token0_map", "project_events", "_days_of", "write_once_csv", "sweep_frame", "verify_files",
        "capture_files", "sweep_files", "_eff", "_vif", "_ms", "_day", "design_effect", "block_anchor", "de_gate", "_family_rule", "_gate",
        "cleanup_census", "demean", "_partial", "wcorr", "corr_ok", "design_ss", "mde_class", "mde_slope_design", "mde_slope_declared",
        "_roots", "_scan", "_name_time", "sealed_dirs", "seal_completeness", "_read", "census_slots", "fold", "imbalance", "strata_of",
        "shift_plan", "offset_range", "circular_shift", "block_fl_gate",
    ],
    "live_tests7.py": [
        "_norm_cat", "crypto_class", "crypto_failsafe", "slot_in_day", "MidStore", "rv_from_matrix", "floored_rv", "_non_sports_ex_crypto", "_hte",
        "_own24", "_in_band", "exact_t_sum", "mde_common", "block_min_units", "block_share", "resid_iqr", "iqr_ok", "terciles", "standardise", "_de",
        "_gate_min_days", "_fam", "_per_market", "_events", "_tier_shares", "_share_by_tercile", "unit_overlaps", "_z", "_desc_splits",
        "pair_correlations", "_merge_counts", "_fee_counts", "load_unavailable", "_dir_slot", "sealed_sweep_slots", "_movers_join", "_common_cols",
        "_base_out", "_utc_day", "_mid12",
        # the 13.7 carry (listed_carry24h_v2) and its counts
        "_status_array", "_series_ids", "RewardCarry", "_reward_cols", "_in_band_carry_counts", "_carry_unit_cols", "_switch_distinct",
    ],
    "live_tests8.py": [
        # LT8's null taxonomy of clob_rewards (census-code check fix 7), the rw frame of EVERY sidecar row (13.7), the shared unit helpers and the
        # design-based MDE under a working covariance (LT8 census-code check)
        "reward_detail", "reward_status", "lt7_status", "clob_hash", "rw_frame", "read_rw8", "rw_slim", "_vol_cols", "_ft_both", "_drop_missing",
        "_rv24", "design_se", "class_mde8", "corr_pair", "corr_pair_ok", "_q", "_events8",
    ],
}

HEADER = '''# ruff: noqa: E501, F401
"""GENERATED by ``scripts/vendor_lt9_base.py``: do not edit by hand.

Unmodified copies of the LT3/LT4/LT5/LT7/LT8 reader, census and analysis functions that LT9 uses (LIVE_TESTS_9.md 8.1), so that later
LT3-LT8 maintenance cannot void LT9 lines. Sources: ``live_tests7_base.py`` 2e8baa90... and ``live_tests7.py`` e1c5c0c6... (8dd013b9; the 13.7
carry ``RewardCarry`` / ``listed_carry24h_v2`` with its ``_status_array`` fix) and ``live_tests8.py`` d1b252cf... (86e32dd3, LT8's census-code-checked
commit; re-verified against LT8's census outputs at LT9's freeze check). The only change to each copy is the removal of the module prefix (``b.``
for the ``live_tests7.py`` / ``live_tests8.py`` sources). ``VENDORED`` records, per name, the source file, its sha256 at copy time, the prefix
regex, the sha256 of the prefix-normalised source and the source commit (and, for names that ``live_tests7_base.py`` itself vendored, the
original LT3/LT4/LT5 file and hash as ``origin``); ``tests/unit/test_research_lab_live_tests9.py`` re-checks them. No LT9 module imports
``live_tests3`` .. ``live_tests8``.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import cb13_label as lab
from . import cb17_census, economics, forecast, maker_rewards, panel, trade_sample

ROOT = forecast.ROOT
REWARD_CARRY_SLOTS = 12  # live_tests7.REWARD_CARRY_SLOTS (the 13.7 carry window [k - 11, k]; used by the copied RewardCarry)
GRID_S = 7200.0  # live_tests7_base.GRID_S
SLOT_TOL_S = 1800.0  # live_tests7_base.SLOT_TOL_S
DAY_S = 86400.0  # live_tests7_base.DAY_S
# live_tests7_base.SNAP_COLS / EXT_COLS / SWEEP_COLS (used by the copied loaders)
SNAP_COLS = ["market_id", "condition_id", "event_id", "received_utc", "closed", "active", "binary", "best_bid",
             "best_ask", "spread", "last_trade_price", "chg_1h", "chg_1d", "chg_1w", "volume24hr", "end_date",
             "neg_risk"]
EXT_COLS = ["market_id", "fee_type", "fee_category", "fees_enabled", "fee_schedule", "order_price_min_tick_size",
            "created_at", "series_slugs"]
SWEEP_COLS = ["token_id", "market_id", "batch_receipt_utc", "best_bid", "best_ask", "state", "bid_size_1", "ask_size_1",
              "depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c", "min_order_size"]
_NULL_LIKE = {"", "nan", "none", "null"}  # live_tests7._NULL_LIKE == live_tests8._NULL_LIKE
# live_tests8.LT7_STATUS / RW_COLS (read by the copied lt7_status, rw_frame and read_rw8)
LT7_STATUS = {"unset": "null", "empty_list": "listed", "zero": "listed", "rewarded": "listed", "malformed": "malformed", "no_sidecar": "absent", "no_column": "no_column"}
RW_COLS = ["market_id", "clob_h", "rew_status", "rew_raw", "rew_min", "rew_maxspread"]
'''


def normalised_sha(src: str, prefix: str) -> str:
    return hashlib.sha256(re.sub(prefix, "", src).encode("utf-8")).hexdigest()


def census_output_check() -> None:
    """LIVE_TESTS_9.md 8.1: LT9 vendors LT8's code from the hash LT8's census outputs record, else from the census-code-checked commit. If an LT8
    census output (``CC8*`` / ``CS8*`` .json in data-dumps/research_lab/live_tests8_census/, when present; only its ``code_sha256`` key is read)
    records a ``live_tests8.py`` hash other than the pin, refuse: re-vendor from that hash first."""
    d = HERE.parents[2] / "data-dumps" / "research_lab" / "live_tests8_census"
    if not d.exists():
        return
    for pat in ("CC8*.json", "CS8*.json"):
        for f in sorted(d.glob(pat)):
            try:
                ch = json.loads(f.read_text()).get("code_sha256") or {}
            except (OSError, ValueError, AttributeError):
                raise SystemExit(f"refusing: LT8 census output {f.name} is unreadable JSON; its code hash cannot be checked") from None
            got = ch.get("live_tests8.py")
            if got and got != SOURCE_PINS["live_tests8.py"]:
                raise SystemExit(f"refusing: LT8 census output {f.name} ran on live_tests8.py {got}, not the vendored {SOURCE_PINS['live_tests8.py']}; re-vendor from that hash first (LIVE_TESTS_9.md 8.1)")


def main() -> None:
    census_output_check()
    texts, fshas = {}, {}
    for fname, want in SOURCE_PINS.items():
        raw = (SRC / fname).read_bytes()
        got = hashlib.sha256(raw).hexdigest()
        if got != want:
            raise SystemExit(f"refusing: {fname} sha256 {got} != the pinned {want} (LIVE_TESTS_9.md 8.1); nothing vendored")
        texts[fname], fshas[fname] = raw.decode("utf-8"), got
    base_tree = ast.parse(texts["live_tests7_base.py"])
    origin: dict = {}
    for node in base_tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "VENDORED" for t in node.targets):
            origin = json.loads(ast.get_source_segment(texts["live_tests7_base.py"], node.value))
    parts, prov = [HEADER], {}
    for fname, names in PICK.items():
        text = texts[fname]
        tree = ast.parse(text)
        nodes = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        parts.append(f"\n\n# --- from {fname} (sha256 {fshas[fname][:16]}...) " + "-" * 40 + "\n")
        for name in names:
            if name not in nodes:
                raise SystemExit(f"{name} is not defined in {fname}")
            if name in prov:
                raise SystemExit(f"duplicate vendored name {name} ({prov[name]['source']} and {fname})")
            src = ast.get_source_segment(text, nodes[name])
            parts.append("\n\n" + re.sub(PREFIX[fname], "", src) + "\n")
            prov[name] = {"source": fname, "source_sha256": fshas[fname], "prefix": PREFIX[fname], "normalised_sha256": normalised_sha(src, PREFIX[fname]),
                          "source_commit": SOURCE_COMMIT[fname]}
            if fname == "live_tests7_base.py" and name in origin:
                prov[name]["origin"] = {"source": origin[name]["source"], "source_sha256": origin[name]["source_sha256"], "normalised_sha256": origin[name]["normalised_sha256"]}
    parts.append("\n\nVENDORED = " + json.dumps(prov, indent=1, sort_keys=True) + "\n")
    OUT.write_text("".join(parts))
    print(f"wrote {OUT} ({len(prov)} names)")


if __name__ == "__main__":
    main()
