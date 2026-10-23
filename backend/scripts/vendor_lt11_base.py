# ruff: noqa: E501
"""Generate LT11's two vendored bases (LIVE_TESTS_11.md 8.1: "vendored, hash-pinned, unmodified copies"; the same mechanism as ``vendor_lt10_base.py``):

* ``astrolabe/research_lab/live_tests11_base.py``: unmodified copies of the LT3-LT9 pieces LT11 reuses, taken through ``live_tests9_base.py`` 03dd3be3...
  (which carries each name's original file and hash as ``origin``): the slot grid, the capture scan and the series frame (LT3), ``classify`` and
  ``move_join`` (LT3), the category columns, ``write_once_csv``, ``verify_files``, the seal helpers, the estimator helpers and the design/MDE helpers
  (LT4/LT5/LT7/LT8), LT5's ``block_fl_gate`` with its shift plan, LT7's ``RewardCarry`` with its ``_status_array`` fix and ``listed_carry24h_v2``
  readers (LT7 13.7 / LT8), ``MidStore`` and the 12-slot realised-volatility helpers, the crypto classifier, and the sports classifier
  ``cb17_census.is_sports_sidecar`` with its frozen lists (``cb13_label.py``);
* ``astrolabe/research_lab/live_tests11_analysis_base.py``: unmodified copies of LT3's ``fit``, ``attrition``, ``lee_bounds``, ``paper_taker`` and ``econ``
  (``live_tests3_analysis.py`` 224b5603...; ``holm`` is ``bounce_decomp.holm``, hashed beside the modules).

Every source is REFUSED unless its raw sha256 equals the pin below. The only change to a copied source is the removal of a module prefix (``lab.`` /
``cb17_census.`` in ``category_cols``; ``lab.`` in ``cb17_census.py``; ``lt.`` in ``live_tests3_analysis.py``). Provenance per name: the source file, its
sha256 at copy time, the prefix regex, the sha256 of the prefix-normalised source and the source commit (and, for names ``live_tests9_base.py`` itself
vendored, the original file and hash as ``origin``); ``tests/unit/test_research_lab_live_tests11.py`` re-checks them. No E026 frozen file is read.

    LT11_VENDOR_SRC=<dir with the pinned blobs> python scripts/vendor_lt11_base.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "astrolabe" / "research_lab"
OUT = HERE / "live_tests11_base.py"
OUT_ABASE = HERE / "live_tests11_analysis_base.py"
SRC = Path(os.environ["LT11_VENDOR_SRC"]) if os.environ.get("LT11_VENDOR_SRC") else HERE
SOURCE_PINS = {
    "live_tests9_base.py": "03dd3be38f50ad12e00ed2487f189d0bf49299483720d499f5620c0023dc9d39",
    "cb17_census.py": "6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a",
    "cb13_label.py": "2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380",
    "live_tests3_analysis.py": "224b56036f98a2cfe3f92ffb6778e80c6b1131223cf20a0f548ca95fffaec955",
}
SOURCE_COMMIT = {"live_tests9_base.py": "60df6c47", "cb17_census.py": "80ff3858", "cb13_label.py": "551cdc42", "live_tests3_analysis.py": "b48e1909"}
NONE = r"(?!)"

# (output, source file, prefix regex, names). Names may be functions, classes or module-level assignments.
PICK: list[tuple[str, str, str, list[str]]] = [
    ("base", "live_tests9_base.py", NONE, [
        "epoch", "iso", "now_ts", "sha256_file", "git_commit", "_json", "append_jsonl", "dir_bytes", "du_bytes", "_truthy", "grid0", "slot_of", "slot_time",
        "_manifest", "State", "scan_captures", "scan_sweeps", "sweep_frame", "sweep_files", "fee_rates", "series_frame", "read_series", "tight_arr", "classify", "move_join", "write_once_csv",
        "verify_files", "capture_files", "_eff", "_vif", "_ms", "_day", "design_effect", "block_anchor", "de_gate", "_family_rule", "_gate", "cleanup_census",
        "demean", "_partial", "wcorr", "corr_ok", "design_ss", "mde_class", "mde_slope_design", "mde_slope_declared", "_roots", "_scan", "_name_time",
        "sealed_dirs", "seal_completeness", "census_slots", "shift_plan", "offset_range", "circular_shift", "block_fl_gate", "_norm_cat", "crypto_class",
        "crypto_failsafe", "slot_in_day", "MidStore", "rv_from_matrix", "floored_rv", "_non_sports_ex_crypto", "_hte", "_own24", "exact_t_sum", "mde_common",
        "block_min_units", "block_share", "resid_iqr", "iqr_ok", "terciles", "standardise", "_de", "_gate_min_days", "_fam", "_per_market", "_events",
        "unit_overlaps", "_z", "_desc_splits", "_merge_counts", "_fee_counts", "load_unavailable", "_utc_day", "_status_array", "_series_ids", "RewardCarry",
        "_reward_cols", "_movers_join", "_common_cols", "_base_out", "_mid12", "_drop_missing", "_rv24", "design_se", "class_mde8", "corr_pair", "corr_pair_ok", "_q", "_events8", "reward_detail", "reward_status", "lt7_status", "clob_hash", "rw_frame", "read_rw8", "_vol_cols",
    ]),
    ("base", "live_tests9_base.py", r"\b(?:lab|cb17_census)\.", ["category_cols"]),
    ("base", "cb13_label.py", NONE, ["SPORTS_CATEGORIES", "SPORTS_SERIES_RE", "_norm", "first_series_slug"]),
    ("base", "cb17_census.py", r"\blab\.", ["is_sports_sidecar"]),
    ("abase", "live_tests3_analysis.py", r"\blt\.", ["N_BOOT", "demean", "fit", "attrition", "lee_bounds", "paper_taker", "econ"]),
]

HEADER_BASE = '''# ruff: noqa: E501, F401
"""GENERATED by ``scripts/vendor_lt11_base.py``: do not edit by hand.

Unmodified copies of the LT3-LT9 reader, census and estimator helpers that LT11 uses (LIVE_TESTS_11.md 8.1), taken through ``live_tests9_base.py``
03dd3be3... (each name's original file and hash carried as ``origin``), and of the sports classifier ``cb17_census.is_sports_sidecar`` with its frozen
lists (``cb13_label.py``), so that later maintenance of LT3-LT9 cannot void LT11 lines. The only change to each copy is the removal of a module prefix
(``lab.`` / ``cb17_census.`` in ``category_cols``; ``lab.`` in ``cb17_census.py``). ``VENDORED`` records, per name, the source file, its sha256 at copy
time, the prefix regex, the sha256 of the prefix-normalised source and the source commit; ``tests/unit/test_research_lab_live_tests11.py`` re-checks
them. No LT11 module imports ``live_tests3`` .. ``live_tests10``, and no E026 frozen file is read.
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
from . import economics, forecast, maker_rewards, panel

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

HEADER_ABASE = '''# ruff: noqa: E501, F401
"""GENERATED by ``scripts/vendor_lt11_base.py``: do not edit by hand.

Unmodified copies of LT3's analysis estimator and economics helpers (``live_tests3_analysis.py`` 224b5603..., commit b48e1909): ``fit`` (expanding-past
demeaning, CR1 on the event and the UTC day, one-sided p), ``attrition``, ``lee_bounds``, ``paper_taker`` and ``econ`` (LIVE_TESTS_11.md 8.1: "LT3's
``paper_taker`` and ``econ``"; ``holm`` is ``bounce_decomp.holm``, hashed beside this file). The only change is the removal of the ``lt.`` prefix
(``lt.economics`` -> ``economics``). ``VENDORED`` records each name's provenance; the unit tests re-check them. No LT11 module imports ``live_tests3``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import t as t_dist

from . import battery, economics
from . import bounce_decomp as bd

NAN = float("nan")
'''


def normalised_sha(src: str, prefix: str) -> str:
    return hashlib.sha256(re.sub(prefix, "", src).encode("utf-8")).hexdigest()


def top_nodes(tree: ast.Module) -> dict[str, ast.AST]:
    out: dict[str, ast.AST] = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            out[n.target.id] = n
    return out


def segment(text: str, node: ast.AST) -> str:
    """Source of a top-level node (``ast.get_source_segment``, the rule of ``vendor_lt9_base.py``; decorators included when present)."""
    if not getattr(node, "decorator_list", None):
        return ast.get_source_segment(text, node)
    lines = text.splitlines(keepends=True)
    start = min([node.lineno, *(d.lineno for d in getattr(node, "decorator_list", []))])
    return "".join(lines[start - 1:node.end_lineno]).rstrip("\n")


def main() -> None:
    texts, fshas = {}, {}
    for fname, want in SOURCE_PINS.items():
        raw = (SRC / fname).read_bytes()
        got = hashlib.sha256(raw).hexdigest()
        if got != want:
            raise SystemExit(f"refusing: {fname} sha256 {got} != the pinned {want} (LIVE_TESTS_11.md 8.1); nothing vendored")
        texts[fname], fshas[fname] = raw.decode("utf-8"), got
    lt9 = texts["live_tests9_base.py"]
    origin: dict = {}
    for node in ast.parse(lt9).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "VENDORED" for t in node.targets):
            origin = json.loads(ast.get_source_segment(lt9, node.value))
    parts = {"base": [HEADER_BASE], "abase": [HEADER_ABASE]}
    prov: dict[str, dict] = {"base": {}, "abase": {}}
    for out, fname, prefix, names in PICK:
        text = texts[fname]
        nodes = top_nodes(ast.parse(text))
        parts[out].append(f"\n\n# --- from {fname} (sha256 {fshas[fname][:16]}...) " + "-" * 40 + "\n")
        for name in names:
            if name not in nodes:
                raise SystemExit(f"{name} is not defined in {fname}")
            if name in prov[out]:
                raise SystemExit(f"duplicate vendored name {name} ({prov[out][name]['source']} and {fname})")
            src = segment(text, nodes[name])
            parts[out].append("\n\n" + re.sub(prefix, "", src) + "\n")
            prov[out][name] = {"source": fname, "source_sha256": fshas[fname], "prefix": prefix, "normalised_sha256": normalised_sha(src, prefix),
                               "source_commit": SOURCE_COMMIT[fname]}
            if fname == "live_tests9_base.py" and name in origin:
                o = origin[name]
                prov[out][name]["origin"] = {"source": o["source"], "source_sha256": o["source_sha256"], "normalised_sha256": o["normalised_sha256"],
                                             **({"origin": o["origin"]} if "origin" in o else {})}
    for out, path in (("base", OUT), ("abase", OUT_ABASE)):
        parts[out].append("\n\nVENDORED = " + json.dumps(prov[out], indent=1, sort_keys=True) + "\n")
        path.write_text("".join(parts[out]))
        print(f"wrote {path} ({len(prov[out])} names)")


if __name__ == "__main__":
    main()
