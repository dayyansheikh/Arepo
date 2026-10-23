# ruff: noqa: E501
"""Generate LT10's two vendored bases (LIVE_TESTS_10.md 8.1: "vendored, not imported"; the same mechanism as ``vendor_lt9_base.py``):

* ``astrolabe/research_lab/live_tests10_base.py``: unmodified copies of E009's ``two_sided_mid``, ``in_range``, ``lookup``, ``features``,
  ``round_trip_cost`` and ``predict`` (``cross_venue_live.py`` eac14e68..., last changed at 9beda37, E010's registration), of the LT3/LT4/LT5/LT7/LT9
  helpers LT10's seal, censuses and gates use (through ``live_tests9_base.py`` 03dd3be3..., which carries each name's original file and hash as
  ``origin``: ``de_gate``, ``block_fl_gate`` and its shift plan, ``demean`` (``bounce_decomp.expanding_demean``), the design and MDE helpers, the seal
  reader ``verify_files``, ``write_once_csv`` and the crypto classifier ``crypto_class``), and of the sports classifier
  ``cb17_census.is_sports_sidecar`` with its frozen lists (``cb13_label.py``);
* ``astrolabe/research_lab/xv_quotes_poller_base.py``: the fetch, parse, pair-refresh and matching parts of E009's poller (``cross_venue_live.py``
  eac14e68... and ``cross_venue.py`` 52640839...), for the route-1 quotes-only successor (8.1, 8.2).

Every source is REFUSED unless its raw sha256 equals the pin below. The only change to a copied source is the removal of a module prefix (``cv.`` in
``cross_venue_live.py`` for the successor base, whose ``cross_venue`` names are copied beside it; ``lab.`` in ``cb17_census.py``, whose ``cb13_label``
names are copied beside it). Provenance per name: the source file, its sha256 at copy time, the prefix regex, the sha256 of the prefix-normalised
source and the source commit (and, for names ``live_tests9_base.py`` itself vendored, the original file and hash as ``origin``);
``tests/unit/test_research_lab_live_tests10.py`` re-checks them. Module-level constants a copied function reads are restated in the header and a unit
test checks them against their sources.

Names of 8.1's list NOT vendored here (no phase-1 census, seal, gate or size-world code needs them; code phase 2 vendors them by this script for the
analysis): ``fit``, ``attrition``, ``lee_bounds``, ``paper_taker``, ``econ``, ``holm`` (``live_tests3*``).

    LT10_VENDOR_SRC=<dir with the pinned blobs> python scripts/vendor_lt10_base.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "astrolabe" / "research_lab"
OUT = HERE / "live_tests10_base.py"
OUT_POLLER = HERE / "xv_quotes_poller_base.py"
SRC = Path(os.environ["LT10_VENDOR_SRC"]) if os.environ.get("LT10_VENDOR_SRC") else HERE
SOURCE_PINS = {
    "cross_venue_live.py": "eac14e68dc7a9d60610d9ea5d2edfdc39be73afd0192d6b41cd3d5459e5ef581",
    "cross_venue.py": "5264083948a77679189f14471290c2f84bf71dac01fc9632cb0633fdb59ace99",
    "live_tests9_base.py": "03dd3be38f50ad12e00ed2487f189d0bf49299483720d499f5620c0023dc9d39",
    "cb17_census.py": "6b98bab8bde4238edbe56e32d5672c72a04acc04d662bec7b393e3cbf806a15a",
    "cb13_label.py": "2fbf4b91e3ee3db413098866a6d99b24bcdf5e0c97750820de8edbc6fc789380",
}
SOURCE_COMMIT = {"cross_venue_live.py": "9beda37e", "cross_venue.py": "86a41c20", "live_tests9_base.py": "60df6c47", "cb17_census.py": "80ff3858",
                 "cb13_label.py": "551cdc42"}
NONE = r"(?!)"

# (output, source file, prefix regex, names). Names may be functions, classes or module-level assignments.
PICK: list[tuple[str, str, str, list[str]]] = [
    ("base", "cross_venue_live.py", NONE, ["two_sided_mid", "in_range", "lookup", "features", "round_trip_cost", "predict"]),
    ("base", "live_tests9_base.py", NONE, [
        "epoch", "iso", "now_ts", "sha256_file", "git_commit", "_json", "append_jsonl", "dir_bytes", "du_bytes", "write_once_csv", "verify_files",
        "_eff", "_vif", "de_gate", "demean", "_partial", "wcorr", "corr_ok", "design_ss", "mde_class", "mde_slope_declared", "exact_t_sum",
        "mde_common", "shift_plan", "offset_range", "circular_shift", "block_fl_gate", "_norm_cat", "crypto_class",
    ]),
    ("base", "cb13_label.py", NONE, ["SPORTS_CATEGORIES", "SPORTS_SERIES_RE", "_norm", "first_series_slug"]),
    ("base", "cb17_census.py", r"\blab\.", ["is_sports_sidecar"]),
    ("poller", "cross_venue.py", NONE, [
        "MAX_DATE_GAP_S", "MIN_JACCARD", "MIN_SHARED", "MARGIN", "CONFLICT", "STOP", "MONTHS", "_NUM", "KALSHI_API", "MAX_K_SPREAD", "MID_RANGE",
        "_canon_num", "tokenize", "_epoch", "MatchPair", "k_text", "p_text", "_p_end", "match_markets",
    ]),
    ("poller", "cross_venue_live.py", r"\bcv\.", [
        "_num", "_clean", "utc_iso", "append_jsonl", "read_jsonl", "du_bytes", "rss_mb", "two_sided_mid", "in_range", "parse_kalshi_market",
        "parse_book", "kalshi_candidate", "YES_NO", "poly_candidate", "poly_candidates", "MatchPrefilter", "fetch_kalshi_open", "fetch_poly_open",
        "load_verified", "fee_rate", "LIVE_EXTRA_CONFLICT", "live_conflict", "select_live_pairs", "refresh_pairs", "gzip_old_quotes", "http_transport",
    ]),
]

HEADER_BASE = '''# ruff: noqa: E501, F401
"""GENERATED by ``scripts/vendor_lt10_base.py``: do not edit by hand.

Unmodified copies of E009's validity, look-up, feature, cost and prediction functions (``cross_venue_live.py`` eac14e68..., last changed at 9beda37,
E010's registration), of the LT3/LT4/LT5/LT7/LT9 helpers LT10 uses (through ``live_tests9_base.py`` 03dd3be3..., each name's original file and hash
carried as ``origin``) and of the sports classifier ``cb17_census.is_sports_sidecar`` with its frozen lists (``cb13_label.py``) (LIVE_TESTS_10.md
8.1), so that later maintenance of E009 or LT3-LT9 cannot void LT10 lines. The only change to each copy is the removal of a module prefix (``lab.``
for ``cb17_census.py``). ``VENDORED`` records, per name, the source file, its sha256 at copy time, the prefix regex, the sha256 of the
prefix-normalised source and the source commit; ``tests/unit/test_research_lab_live_tests10.py`` re-checks them. No LT10 module imports
``cross_venue_live*`` or ``live_tests3`` .. ``live_tests9``.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import bounce_decomp as bd
from . import economics as econ
from . import forecast

ROOT = forecast.ROOT
NAN = float("nan")
# cross_venue_live.py constants read by the copied functions (a unit test checks each against its source)
MAX_SPREAD = 0.10  # cross_venue_live.MAX_SPREAD = cross_venue.MAX_K_SPREAD
MID_RANGE = (0.03, 0.97)  # cross_venue_live.MID_RANGE = cross_venue.MID_RANGE
LOOKBACK_TOL_S = 240  # cross_venue_live.LOOKBACK_TOL_S
OUTCOME_TOL_S = 120  # cross_venue_live.OUTCOME_TOL_S
MAX_RECV_LAG_S = 60  # cross_venue_live.MAX_RECV_LAG_S
OUTCOME_GRID_S = 600  # cross_venue_live.OUTCOME_GRID_S
CYCLE_S = 120  # cross_venue_live.CYCLE_S
RETIRE_KEEP_S = 6 * 3600 + 1200  # cross_venue_live.RETIRE_KEEP_S (22,800 s)
FEATURES = ("r1", "r6", "lvl", "lvl2", "gap", "dk1", "dk6")  # cross_venue_live.FEATURES
_NULL_LIKE = {"", "nan", "none", "null"}  # live_tests7._NULL_LIKE (read by the copied _norm_cat)
'''

HEADER_POLLER = '''# ruff: noqa: E501, F401
"""GENERATED by ``scripts/vendor_lt10_base.py``: do not edit by hand.

The fetch, parse, pair-refresh and matching parts of E009's poller (``cross_venue_live.py`` eac14e68... and ``cross_venue.py`` 52640839...), copied
unmodified for LT10's route-1 quotes-only successor (``xv_quotes_poller.py``; LIVE_TESTS_10.md 8.1, 8.2). The only change is the removal of the
``cv.`` prefix (the ``cross_venue`` names are copied beside them). ``VENDORED`` records each name's provenance. Same endpoints, ``CHUNK``,
``MAX_PAIRS``, pacing hooks and pair-refresh rule as E009; the pair records written by this copy carry ``version = xv-quotes-v1``.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import math
import os
import re
import subprocess
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import economics as econ
from . import forecast

log = logging.getLogger(__name__)
VERSION = "xv-quotes-v1"
ROOT = forecast.ROOT / "data-dumps" / "research_lab" / "xv_quotes"
VERIFIED_PATH = Path(__file__).resolve().parent / "model_specs" / "cross_venue_live_verified.json"  # E009's frozen hand verdicts (sha256 1d6f942a...)
# cross_venue_live.py constants read by the copied functions (a unit test checks each against its source)
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
CYCLE_S = 120
MAX_PAIRS = 200
POLY_PAGE = 100
CHUNK = 100
RETIRE_KEEP_S = 6 * 3600 + 1200
REFRESH_EVERY_S = 86400
NAN = float("nan")
'''

TRAILER_POLLER = '''

# cross_venue_live.py names that alias cross_venue names (KALSHI = cv.KALSHI_API, MAX_SPREAD = cv.MAX_K_SPREAD, MID_RANGE = cv.MID_RANGE)
KALSHI = KALSHI_API
MAX_SPREAD = MAX_K_SPREAD
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
            raise SystemExit(f"refusing: {fname} sha256 {got} != the pinned {want} (LIVE_TESTS_10.md 8.1); nothing vendored")
        texts[fname], fshas[fname] = raw.decode("utf-8"), got
    lt9 = texts["live_tests9_base.py"]
    origin: dict = {}
    for node in ast.parse(lt9).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "VENDORED" for t in node.targets):
            origin = json.loads(ast.get_source_segment(lt9, node.value))
    parts = {"base": [HEADER_BASE], "poller": [HEADER_POLLER]}
    prov: dict[str, dict] = {"base": {}, "poller": {}}
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
    parts["poller"].append(TRAILER_POLLER)
    for out, path in (("base", OUT), ("poller", OUT_POLLER)):
        parts[out].append("\n\nVENDORED = " + json.dumps(prov[out], indent=1, sort_keys=True) + "\n")
        path.write_text("".join(parts[out]))
        print(f"wrote {path} ({len(prov[out])} names)")


if __name__ == "__main__":
    main()
