# ruff: noqa: E501
"""CB16 shared parts (docs/research_lab/CREATIVE_BATCH_16.md sections 1.2-1.4, 2.1-2.8, 5, 9-10). Rules part ``common``.

Everything common to CB16-A (Q: quoter grain, CH131; U: relative large-print silence in active markets, CH132) and CB16-K (the Kalshi-absent census, counts only, k = 0) lives here:
the dates (the ``S_A`` rule, the lookback floor 2026-10-26T00Z that keeps every read outside J4-R and CB13-T's HOLDOUT, the election-night exclusion), refusal lists (outputs AND
inputs; ``surprise_live``, ``cross_venue_live``, ``e0xx``, ``trade_samples``, ``cb3_*``, every ``h15_*`` root except the two q0380 id files, and the monitor's alert / score / outcome /
wallet / stats / state files are never opened), the field whitelists (``side``, ``wallet_*``, ``recv_ts`` outside U2's lag check, every ``chg_*``, outcome and settlement fields never
reach a row), the disk guards (data-dumps cap 40 and root free disk, exit 75 = "pending"), the pinned sha256 of every CB13 function Q and U call (fill, touch consistency, marks,
the CB13-T3 round trip, the LABELLER), the fixed-k1 (= 2) Holm helpers (Stage-2 early rule at alpha / 4; the final Holm only adds passes), the clustered-inference helpers (market
fixed-effect pseudo-values, the max over cluster ways with the CB10 small-G rule), the terminal "not testable" records, the trial-line helpers (kinds ``cb16_test`` /
``cb16_replication`` / ``cb16_descriptive``), the q0380 exclusion keys and the per-part rules hashing.

**Per-part rules hashing.** ``seals/cb16_rules.json`` holds one sha256 per part: ``common``, ``A`` (Q and U: ``cb16_q``, ``cb16_u``, ``cb16_a``) and ``K`` (``cb16_k``). A family part hashes ONLY
(a) the common rule functions and constants of this module, (b) the functions and UPPER_CASE constants of that part's own modules, and (c) the source sha256 of every helper outside
CB16 that those functions reach, transitively (``external_closure``; a shared helper's own helpers are hashed too). Verifying part A imports ``cb16_q`` / ``cb16_u`` and never
``cb16_k``. Rule: nothing part-specific is added to this module after the first CB16 job.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib
import inspect
import json
import math
import re
import time
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import cb10_common as c10
from . import cb12_common as c12
from . import cb13_common as c13
from . import cb14_common as c14
from . import provenance

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

# ---- constants (hashed with this module: every UPPER_CASE JSON-able constant below is part of ``common``) ------------------------------------------------
RULES_VERSION = "cb16-rules-v1"
PARTS = ("common", "A", "K")
FAMILY_PARTS = ("A", "K")
FREEZE_PARTS = ("A",)  # K has no counted test and no freeze; it binds on its rules part alone
FAMILY_MODULES = {"A": ("cb16_q", "cb16_u", "cb16_a"), "K": ("cb16_k",)}
COUNT_FAMILIES = ("Q", "U")  # count lines creative_batch_16:Q (1) and creative_batch_16:U (1)
FAMILY_TESTS = {"Q": ("Q1",), "U": ("U1",)}
FAMILY_REP_TESTS = {"Q": ("Q1", "Q2"), "U": ("U1", "U2")}
STAGE1_HOLM_FAMILY = ("Q1", "U1")
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 2, fixed (round 1 item 17: the change from the draft comes only from the H withdrawal)
STAGE_ALPHA = 0.05  # Stage 1 batch Holm and Stage 2 Holm, one-sided
STAGE2_K_MAX = 4  # Q1-rep, Q2, U1-rep, U2: the largest possible Stage-2 count
EARLY_ALPHA2 = STAGE_ALPHA / STAGE2_K_MAX  # = 0.0125 (strict <, never withdrawn)
STAGE2_NAMES = {"Q1": "Q1-rep", "Q2": "Q2", "U1": "U1-rep", "U2": "U2"}
GATE_P = 0.01
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 1616
N_WILD = 9999
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
PLACEBO_SEED_RANGE = (16101, 16130)
PLACEBO_SEEDS = {"Q1_composition": 16101, "Q1_calibration": 16102, "U1_composition": 16111, "U1_calibration": 16112}
SEED_U_VALIDITY = 16131
SEED_K_AUDIT = 16141
MDE_FACTOR = 3.80  # (z_0.99 + z_0.80) x 1.2 (section 2.7)
G_CR2 = 15  # CB10 section 2.3: a way with fewer clusters leaves the max and its leave-one-cluster-out sign rule binds
TOP_DROP = 5
AVAIL_MIN = 0.60
LOO_DAY_P = 0.05  # leave-one-day-out must keep one-sided p < 0.05 AND the sign
EVIDENCE_ROLE_HIST = "exploratory_historical"
EVIDENCE_ROLE_DEV = "exploratory_dev"
EVIDENCE_ROLE_PROSPECTIVE = "prospective"
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
PIN_UNSET = "TODO-COORDINATOR"
CB16_SPORTS_IN_PRIMARY = False
SMOKE_VERSION = "cb16-smoke-v1"
DATA_DUMPS_CAP_GB = 40.0
FREE_DISK_MIN_GB = 4.5
CB16_OUTPUT_CAP_GB = 0.15
HEARTBEAT_S = cm.HEARTBEAT_S
USER_AGENT = "arepo-research-lab/1 (read-only research; https://www.arepolabs.com)"
STOP_RULE = "3 CPU-hours per family; a job failing twice for the same non-transient reason stops and is recorded; no re-screen of a failed CB16 test"
# dates (section 1.2)
T16_DRAFT = "2026-10-19T09:20:00Z"
T16_A_FREEZE_TARGET = "2026-11-01T00:00:00Z"
S_A_EARLIEST = "2026-11-02T00:00:00Z"
S_A_AFTER_FREEZE_S = 86400.0
WINDOW_S = 14 * 86400.0  # SCREEN_A and REP_A are 14 days each
LOOKBACK_FLOOR = "2026-10-26T00:00:00Z"  # no CB16 Q/U read before this (J4-R and CB13-T HOLDOUT end here)
LOOKBACK_S = 7 * 86400.0
LOOKBACK_ROBUST_S = 3 * 86400.0
ELECTION_NIGHT = ("2026-11-03T18:00:00Z", "2026-11-05T00:00:00Z")
J4R_WINDOW = ("2026-10-16T00:00:00Z", "2026-10-21T00:00:00Z")
CB13_T_HOLDOUT = ("2026-10-21T00:00:00Z", "2026-10-26T00:00:00Z")
CB13_T_SCREEN = ("2026-10-12T00:00:00Z", "2026-10-16T00:00:00Z")  # q0382 and the smoke reproduction only (CB13 readers, CB13 guards)
FRAME_DELAY_S = 8 * 3600.0  # q0384 not before S_A + 14 d + 8 h (the 6-8 h marks of the last fills exist)
MARK_TAIL_S = 8 * 3600.0
CAPTURE_LEAD_S = 5 * 3600.0  # touch (<= 60 min old) and the capture before it (pre-fill proxy)
E011_ANALYSIS_EARLIEST = "2026-11-11T13:00:00Z"
CB3_FREEZE_NAME = c13.CB3_FREEZE_NAME
CB3_STOP_NAME = c13.CB3_STOP_NAME
E011_ANALYSIS_NAME = "e011_analysis_commit.json"  # structured, committed record under seals/ (field ``e011_analysis_commit``); free ledger text never lifts the E011 hold
# roots CB16 writes under, and the input roots it never reads (section 1.1 last rows, 1.3)
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch16",)
KEYS_RUN = "exclusion_run16"
KEYS_STATUS = EXCLUSION_KEYS_COMPLETE
KEYS_OUTPUT_CAP_GB = 0.01
HOLDOUT_PARTS = ("holdout", "t_holdout")
EXTRA_REFUSED_ROOTS = ("creative_batch15", "creative_batch14", "creative_batch13", "creative_batch12", "creative_batch11", "creative_batch10", "creative_batch9", "creative_batch8",
                       "creative_batch7", "creative_batch6", "creative_batch5", "creative_batch4", "creative_batch3", "creative_batch2", "creative_batch1", "snapshots", "trade_samples",
                       "live_trades", "book_sweeps", "surprise_live", "cross_venue_live", "cross_venue", "forecasts", "flow_screen", "h9_flow", "h10_sign", "h10_dlad", "h10_brk",
                       "h11_wprints", "h11_pol", "h11_attn", "h12_say", "h12_quake", "h12_prints", "h12_quake_live", "h12_opt_live", "h13_touch", "h13_binance", "h14_wiki",
                       "h14_wiki_live", "h14_speech", "h15_elect_live", "h15_birth", "h15_birth_live", "h1_first", "h2_main", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders",
                       "h6_weather", "h7_cb4_era", "h7_cb4_series", "h8_tail", "h8_tail_b", "h8_text", "h8_geo", "cb3_followup", "cb6_followup")
ALWAYS_REFUSED_ROOTS = ("surprise_live", "cross_venue_live", "trade_samples", "forecasts", "flow_screen", "cb3_followup", "cb6_followup")
LIVE_ROOT_NAMES = ("cross_venue_live", "surprise_live")
EXTRACT_ROOT_RE = r"^cb\d+_extract$"
EXPERIMENT_ROOT_RE = r"^e0\d\d$"
H15_ROOT_RE = r"^h15_"
MONITOR_TRADES_RE = r"^trades-\d{8}\.jsonl$"
MONITOR_FORBIDDEN_FILES = ("alerts.jsonl", "outcomes.jsonl", "wallets.jsonl", "stats.jsonl", "state.json")
MONITOR_FORBIDDEN_RE = r"^scores-\d{8}\.jsonl$"
CAPTURE_DIR_RE = r"^(\d{8}T\d{6}Z)_[0-9a-f]+$"
# q0380: the CB15 id sources (CB15 section 1.3: E race map, P pairs, P Stage-2 pairs) read ids only; ``creative_batch15`` lives under research_lab/, the rest under history/
ID_READABLE = {"h15_elect_live": ("race_map.csv",), "creative_batch15": ("birth_frame.csv.gz",), "h15_birth_live": ("pairs.jsonl",)}
ID_RESEARCH_ROOTS = ("creative_batch15",)
ID_COLUMNS = ("market_id", "event_id", "condition_id", "neg_risk_market_id", "negRiskMarketID", "series_id", "p_market_id", "p_event_id")
KEY_COLUMNS = ("market_id", "found", "event_ids", "neg_risk_market_id", "series_ids", "sources")
BASE_SOURCE = "base:cb15_q0340"
CB15_KEYS_FILE = "exclusion_keys.csv.gz"
TERMINAL_NAME = "terminal_{family}.json"
TERMINAL_REP_NAME = "terminal_{family}_rep.json"
TERMINAL_STATUS = "terminal_not_testable"
# field whitelists (section 1.4)
PRINT_FIELDS = c13.PRINT_FIELDS
LOOKBACK_FIELDS = ("ts", "condition_id", "cash")  # the U lookback: tx16 in memory only (transaction aggregation)
FORBIDDEN_PRINT_FIELDS = ("side", "key", "recv_ts", "wallet_hash", "wallet", "proxyWallet", "ctx_chg_1h", "ctx_status", "chg_1h")
U2_LAG_FIELDS = ("ts", "condition_id", "recv_ts")  # recv_ts is whitelisted for U2's receipt-lag robustness ONLY (rep frame, wake-up transactions)
SWEEP_FIELDS = ("token_id", "batch_receipt_utc", "best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c", "n_bid_levels",
                "n_ask_levels")
DATA_API_FIELDS = ("timestamp", "price", "size", "conditionId")
FORBIDDEN_OUTPUT_COLUMNS = ("side", "wallet", "wallet_hash", "proxyWallet", "tx16", "transactionHash", "tx_hash", "hash", "name", "pseudonym", "recv_ts", "chg_1h", "chg_1d", "chg_1w",
                            "ctx_chg_1h", "uma_resolution_statuses", "outcome_prices", "outcomePrices", "umaResolutionStatus", "closedTime", "closed_time", "result",
                            "settlement_value", "p_end")
FORBIDDEN_PARSE_FIELDS = ("side", "proxyWallet", "outcome_prices", "outcomePrices", "umaResolutionStatus", "umaResolutionStatuses", "uma_resolution_statuses", "closedTime",
                          "closed_time", "result", "settlement_value", "transactionHash", "hash", "name", "pseudonym", "p_end", "recv_ts", "chg_1h", "ctx_chg_1h")
DATA_DUMPS = cm.DATA_DUMPS
HIST_ROOT = cm.HIST_ROOT
RESEARCH_ROOT = DATA_DUMPS / "research_lab"
CB16_DIR = RESEARCH_ROOT / "creative_batch16"
CB15_KEYS_DEFAULT = RESEARCH_ROOT / "creative_batch15" / CB15_KEYS_FILE
LIVE_TRADES_DIR = RESEARCH_ROOT / "live_trades"
SNAPSHOT_DIR = RESEARCH_ROOT / "snapshots"
SWEEP_DIR = RESEARCH_ROOT / "book_sweeps"
CROSS_VENUE_DIR = RESEARCH_ROOT / "cross_venue"
SEALS_DIR = cm.SEALS_DIR
SMOKE_DEFAULT = CB16_DIR / "smoke.json"
REP_SEAL_COPY = "cb16_a_rep_SEAL.json"
REP_SEAL_NAME = "a_rep_SEAL.json"
# The CB13 functions Q and U call, pinned by the sha256 of their source at CB16's rules commit (section 1.3): a different byte refuses (exit 2) before anything runs.
CB13_PINS = {
    "cb13_common.whitelist_print": "12950339a9210bc46d5f24cb466638570539229141148ad21ceb1a6295bf7c8f",
    "cb13_common.iter_capture_rows": "12b4e6b6cb5d7b109e91349add37f2d9fa7f1975a5e2059e16b0b1966d5e4fd5",
    "cb13_common.iter_sidecar_rows": "0f402eeae1be954e5ad009a58bf80d01d6b193e896d44137c7366713c8633d81",
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

RULES_MACHINERY = ("rules_part_doc", "rules_part_file_doc", "rules_file_doc", "write_rules", "verify_rules", "family_modules", "common_funcs", "part_funcs", "shared_helper_sources",
                   "external_closure", "_code_names", "_helper_key", "common_declared")
SHARED_HELPERS = (("cw", "small_g_pvalue"), ("cw", "_cluster_sums"), ("c12", "holm"), ("c12", "cluster_se_mean"), ("c9", "top_k_drop_mask"), ("c10", "placebo_advance_rate"),
                  ("c10", "leave_one_out_sign"), ("c14", "cluster_p"), ("c14", "wls_coef_pseudo"), ("c13", "leave_one_out_p"), ("c12", "exclusion_stage"),
                  ("c12", "lookup_keys_closed_first"), ("c12", "module_constants"), ("c12", "module_funcs"), ("c10", "require_disk"), ("c9", "write_stall"), ("c9", "stall_of"),
                  ("c9", "write_results_once"), ("bk", "seal_copy_ids_audited"), ("cm", "write_once_json"), ("cm", "write_json_atomic"), ("cm", "idle"))


# ---- small helpers -----------------------------------------------------------------------------------------------------------------------------


def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def ep(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s) -> float:
    return c12.parse_iso(s)


def utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def block6(ts: float) -> int:
    """UTC 00 / 06 / 12 / 18 block index of an epoch (the 6-hour-block way)."""
    return int(ts // 21600)


def hour_of_day(ts: float) -> int:
    return int(datetime.fromtimestamp(ts, UTC).hour)


def read_csv_gz(path: Path) -> Iterator[dict]:
    return c12.read_csv_gz(path)


def sha256_obj(obj) -> str:
    return cm.sha_obj(obj)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- windows (section 1.2) --------------------------------------------------------------------------------------------------------------------


def s_a_from_freeze(freeze_epoch: float) -> float:
    """``S_A = max(2026-11-02T00:00Z, the first 00:00Z at or after T16_A_freeze + 24 h)``: it depends only on the freeze time, never on data."""
    t = float(freeze_epoch) + S_A_AFTER_FREEZE_S
    d = datetime.fromtimestamp(t, UTC)
    mid = d.replace(hour=0, minute=0, second=0, microsecond=0)
    if mid.timestamp() < t:
        mid = mid + timedelta(days=1)
    return max(ep(S_A_EARLIEST), mid.timestamp())


def windows(s_a: float) -> dict:
    """Epoch bounds of the two windows. ``units``: the fill-time window; ``captures``: capture starts a reader may open (touch and pre-fill capture before, 6-8 h marks after);
    ``prints``: monitor prints read (the U lookback from ``max(start - 7 d, floor)``)."""
    s = float(s_a)
    floor = ep(LOOKBACK_FLOOR)
    out = {}
    for name, lo in (("screen", s), ("rep", s + WINDOW_S)):
        hi = lo + WINDOW_S
        out[name] = {"units": (lo, hi), "captures": (max(floor, lo - CAPTURE_LEAD_S), hi + MARK_TAIL_S), "prints": (max(floor, lo - LOOKBACK_S), hi),
                     "frame_not_before": hi + FRAME_DELAY_S}
    return out


def in_election_night(t: float) -> bool:
    return ep(ELECTION_NIGHT[0]) <= float(t) < ep(ELECTION_NIGHT[1])


def guard_floor(t: float, what: str = "row") -> float:
    """Q/U readers refuse every print, capture or sweep timed before the lookback floor (2026-10-26T00:00Z): J4-R and CB13-T's HOLDOUT are never read by a Q/U path. (The q0382
    census and the smoke's CB13 reproduction read CB13-T SCREEN files through CB13's own guarded readers, never through this one.)"""
    if not (math.isfinite(float(t)) and float(t) >= ep(LOOKBACK_FLOOR)):
        raise Refused(f"{what} timed {iso(t) if math.isfinite(float(t)) else t} is before the CB16 lookback floor {LOOKBACK_FLOOR} (J4-R / CB13-T HOLDOUT are never read)")
    return float(t)


def guard_rep_unit(t: float, s_a: float, *, rep_open: bool) -> float:
    """A REP_A unit (a transaction timed in REP_A) is refused unless the REP_A frame path is open (q0387 after the SCREEN_A result, q0388 after the verified seal)."""
    lo, hi = windows(s_a)["rep"]["units"]
    if lo <= float(t) < hi and not rep_open:
        raise Refused(f"transaction timed {iso(t)} lies in REP_A [{iso(lo)}, {iso(hi)}): REP_A rows are refused before the SCREEN_A result and the REP_A seal")
    return float(t)


# ---- refusals ----------------------------------------------------------------------------------------------------------------------------------


def refused_names() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*c10.REFUSED_ROOTS, *c10.REFUSED_RUN_IDS, *EXTRA_REFUSED_ROOTS)))


def refuse_path(path: Path, *, allow: tuple[str, ...] = ()) -> Path:
    """Output AND input guard: refuse any path with a CB1-CB15 / sealed / live root among its parts, any ``cb<n>_extract``, ``e0xx`` or ``h15_*`` directory, and anything under the
    always-refused stores (``allow`` cannot lift those). ``allow`` names roots one reader may open (live_trades, snapshots, book_sweeps, cross_venue, the q0380 id files)."""
    parts = Path(path).parts
    names = tuple(n for n in refused_names() if n not in allow or n in ALWAYS_REFUSED_ROOTS)
    bad = [p for p in parts if p in names or re.match(EXTRACT_ROOT_RE, p) or re.match(EXPERIMENT_ROOT_RE, p) or any(x in p for x in LIVE_ROOT_NAMES)
           or (re.match(H15_ROOT_RE, p) and p not in allow)]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB15 / sealed / live root ({bad[0]}); CB16 refuses it")
    return Path(path)


def guard_monitor_file(path: Path) -> Path:
    """The only monitor file CB16 opens is ``live_trades/trades-YYYYMMDD.jsonl``; ``alerts`` / ``scores-*`` / ``outcomes`` / ``wallets`` / ``stats`` / ``state`` are refused."""
    p = Path(path)
    if p.name in MONITOR_FORBIDDEN_FILES or re.match(MONITOR_FORBIDDEN_RE, p.name):
        raise Refused(f"{p.name}: the monitor's alert / score / outcome / wallet / stats / state files are never opened by CB16")
    if not re.match(MONITOR_TRADES_RE, p.name) or p.parent.name != "live_trades":
        raise Refused(f"{p}: CB16 opens only live_trades/trades-YYYYMMDD.jsonl")
    refuse_path(p, allow=("live_trades",))
    return p


def guard_capture_dir(cdir: Path) -> Path:
    d = Path(cdir)
    if not re.match(CAPTURE_DIR_RE, d.name) or d.parent.name != "snapshots":
        raise Refused(f"{d}: not a snapshots/<capture> directory")
    refuse_path(d, allow=("snapshots",))
    return d


def guard_sweep_file(path: Path) -> Path:
    p = Path(path)
    if p.name != "rows.csv.gz" or p.parent.parent.name != "book_sweeps":
        raise Refused(f"{p}: CB16 opens only book_sweeps/<sweep>/rows.csv.gz")
    refuse_path(p, allow=("book_sweeps",))
    return p


def guard_cross_venue_file(path: Path) -> Path:
    p = Path(path)
    ok = p.name in ("poly_markets.json", "matches_all.json", "audit_flags.json") or re.match(r"^kalshi_markets.*\.jsonl$", p.name)
    if not ok or p.parent.name != "cross_venue":
        raise Refused(f"{p}: K opens only cross_venue/{{poly_markets.json, kalshi_markets*.jsonl, matches_all.json, audit_flags.json}}")
    refuse_path(p, allow=("cross_venue",))
    return p


def require_output_root(path: Path) -> Path:
    """Data jobs write only under creative_batch16."""
    refuse_path(Path(path))
    if not any(p in ALLOWED_OUTPUT_ROOT_PARTS for p in Path(path).parts):
        raise Refused(f"CB16 writes only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return Path(path)


def is_holdout_path(path: Path) -> bool:
    p = Path(path)
    return any(x in HOLDOUT_PARTS for x in p.parts) or "holdout" in p.name


def assert_clean_columns(columns: Iterable[str]) -> None:
    bad = [c for c in columns if c in FORBIDDEN_OUTPUT_COLUMNS or str(c).startswith("wallet")]
    if bad:
        raise Refused(f"forbidden columns in an output: {bad}")


def strip_forbidden(rec: dict) -> dict:
    """Drop every forbidden parse field from a decoded record (used as a JSON ``object_pairs_hook`` filter: the value never reaches a row)."""
    return {k: v for k, v in rec.items() if k not in FORBIDDEN_PARSE_FIELDS and not str(k).startswith("wallet")}


def write_gz_csv(path: Path, header: list[str], rows: Iterable[list]) -> Path:
    from . import history_backfill as hb  # noqa: PLC0415

    assert_clean_columns(header)
    require_output_root(Path(path))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(hb._gz_csv_bytes(list(header), list(rows)))
    return Path(path)


def require_after(now: float, epoch: float, label: str) -> None:
    if now < epoch:
        raise NotNow(f"{label}: not before {datetime.fromtimestamp(epoch, UTC):%Y-%m-%dT%H:%MZ} (pending)")


def require_disk(data_dumps: Path | None, cap_gb: float, allowance_bytes: int, *, free_path: Path | None = None, free_min_gb: float = FREE_DISK_MIN_GB, free_fn=None) -> dict:
    """Exit 75 ("pending", never "not run") if data-dumps + the job's cap > ``cap_gb`` OR root free disk - the job's cap < ``free_min_gb``."""
    return c10.require_disk(data_dumps, cap_gb, allowance_bytes, free_path=free_path, free_min_gb=free_min_gb, free_fn=free_fn)


def collector_gap_ok(now: float, live_check: Callable[[], bool] | None = None) -> None:
    """Host-file jobs avoid the collector pass (minutes :31-:55 of even UTC hours) and yield while the pass lock is held (exit 75)."""
    return c13.collector_gap_ok(now, live_check)


def wait_or_idle(rdir: Path, why: str, now: float) -> dict:
    return cm.idle(Path(rdir), why, now)


def ensure_source_file(path: Path, expected_sha256: str | None = None, *, restore_fn: Callable[[Path], None] | None = None) -> Path:
    """Archive-restore hook (section 2.8): restored byte for byte by ``restore_fn`` and the sealed sha256 verified; never re-derived."""
    return c13.ensure_source_file(path, expected_sha256, restore_fn=restore_fn)


def committed_record(path: Path, field: str, *, is_committed: Callable[[Path], bool] | None = None) -> dict | None:
    """A structured, committed record under seals/ (tracked and identical to HEAD) whose ``field`` is set: the E011 analysis-commit hold and similar holds are lifted only by one."""
    from . import cb1_history  # noqa: PLC0415

    p = Path(path)
    committed = is_committed or cb1_history.spec_committed
    if not p.exists() or not committed(p):
        return None
    try:
        doc = json.loads(p.read_text())
    except ValueError:
        return None
    return doc if isinstance(doc, dict) and doc.get(field) else None


def e011_hold_lifted(path: Path | None = None, *, is_committed: Callable[[Path], bool] | None = None, now: float | None = None) -> dict:
    """q0386 refuses before E011's one-time analysis commit (section 1.3): a committed ``seals/e011_analysis_commit.json`` with ``e011_analysis_commit`` set, never before
    2026-11-11T13:00Z. Raises ``NotNow`` (pending) otherwise."""
    if (time.time() if now is None else now) < ep(E011_ANALYSIS_EARLIEST):
        raise NotNow(f"E011 is analysed once after {E011_ANALYSIS_EARLIEST}; q0386 waits (pending)")
    p = Path(path) if path is not None else SEALS_DIR / E011_ANALYSIS_NAME
    doc = committed_record(p, "e011_analysis_commit", is_committed=is_committed)
    if doc is None:
        raise NotNow(f"E011 hold: no committed {p.name} with e011_analysis_commit set; q0386 waits (pending)")
    return {"lifted_by": "e011_analysis_commit", "commit": doc["e011_analysis_commit"], "path": str(p)}


def cb3_hold_lifted(spec_dir: Path | None = None, stop_path: Path | None = None, *, is_committed: Callable[[Path], bool] | None = None) -> dict:
    """q0386 and q0388 wait for CB3's freeze commit or its structured stop record (as CB13 ``T13_T_rep``)."""
    return c13.cb3_hold_lifted(spec_dir, stop_path, is_committed=is_committed)


FREEZE_PIN_KEYS = {"rules": "rules_sha256", "common": "common_rules_sha256", "frozen": "frozen_utc"}


def require_freeze(part: str, spec_path: Path | None = None, *, require_committed: bool = True, rules_shas: dict[str, str] | None = None) -> dict:
    """Analysis jobs refuse before the CB16 declaration is committed (``model_specs/cb16_v1.json``). The ``A`` entry must PIN the shas the job has just verified (``rules_sha256`` =
    part A, ``common_rules_sha256`` = common) and carry ``frozen_utc`` (the freeze time: ``S_A`` follows from it). Returns ``{"sha256", "frozen_epoch", "s_a"}``."""
    if part not in FREEZE_PARTS:
        raise Refused(f"unknown freeze part {part!r} (only A is frozen; K has no counted test)")
    if not rules_shas or part not in rules_shas or "common" not in rules_shas:
        raise Refused(f"require_freeze({part}) needs the currently verified part and common rules shas")
    p = Path(spec_path or (Path(__file__).resolve().parent / "model_specs" / "cb16_v1.json"))
    if not p.exists():
        raise Refused(f"CB16 freeze spec {p} not found: the analysis jobs refuse before the CB16 part-{part} freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB16 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"CB16 freeze spec {p} unreadable") from exc
    entry = doc.get(part) if isinstance(doc, dict) else None
    if not isinstance(entry, dict):
        raise Refused(f"CB16 freeze spec {p} has no {part!r} part")
    for key, want in ((FREEZE_PIN_KEYS["rules"], rules_shas[part]), (FREEZE_PIN_KEYS["common"], rules_shas["common"])):
        if entry.get(key) != want:
            raise Refused(f"CB16 freeze entry {part!r} pins {key} {str(entry.get(key))[:12]!r}, but the verified code is {want[:12]!r}: the freeze does not cover this code; refusing")
    fz = parse_iso(entry.get(FREEZE_PIN_KEYS["frozen"]))
    if not math.isfinite(fz):
        raise Refused(f"CB16 freeze entry {part!r} has no readable frozen_utc")
    return {"sha256": hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest(), "frozen_epoch": fz, "s_a": s_a_from_freeze(fz)}


# ---- the CB13 pins (section 1.3) ---------------------------------------------------------------------------------------------------------------


def cb13_pin_current() -> dict[str, str]:
    """The sha256 of the CURRENT source of every pinned CB13 function / class."""
    from . import cb13_label as lab  # noqa: PLC0415
    from . import cb13_t as t13  # noqa: PLC0415

    mods = {"cb13_common": c13, "cb13_t": t13, "cb13_label": lab}
    out = {}
    for key in CB13_PINS:
        m, n = key.split(".", 1)
        out[key] = hashlib.sha256(inspect.getsource(getattr(mods[m], n)).encode()).hexdigest()
    return out


def cb13_pins_ok() -> dict:
    """Every pinned CB13 source equals its pin (``CB13_PINS``). A divergence is recorded and the dependent jobs refuse (exit 2)."""
    cur = cb13_pin_current()
    bad = sorted(k for k, v in CB13_PINS.items() if cur.get(k) != v)
    return {"ok": not bad, "diverged": bad, "n": len(CB13_PINS)}


def require_cb13_pins() -> None:
    r = cb13_pins_ok()
    if not r["ok"]:
        raise Refused(f"pinned CB13 functions changed since CB16's rules commit: {r['diverged']}; CB16 records the divergence and refuses")


# ---- stalls, manifests, results, terminal records ----------------------------------------------------------------------------------------------


def stall_of(rdir: Path) -> dict | None:
    return c9.stall_of(Path(rdir))


def write_stall(rdir: Path, status: str, reason: str, label: str | None = None) -> dict:
    return c9.write_stall(Path(rdir), status, reason, label)


def manifest_complete(rdir: Path, statuses: tuple[str, ...]) -> dict | None:
    return c12.manifest_complete(rdir, statuses)


def verify_dir_manifest(rdir: Path, status: str, label: str) -> dict:
    """The job's manifest is complete with ``status`` AND every recorded file still hashes to it."""
    return c12.verify_fetch(Path(rdir), (status,), label)


def write_results_once(path: Path, doc: dict) -> str:
    return c9.write_results_once(Path(path), doc)


def write_dir_manifest(rdir: Path, status: str, files: Iterable[Path], extra: dict | None = None) -> dict:
    """Manifest of a host-file job: ``status``, ``complete``, the sha256 of every output file (relative paths), plus data-dumps size and free disk when given in ``extra``."""
    from . import history_backfill as hb  # noqa: PLC0415

    rdir = Path(rdir)
    doc = {"status": status, "complete": True, "stopped": None, "written_utc": cm.iso(time.time()), "git_commit": hb._git_commit(),
           "file_sha256": {Path(f).relative_to(rdir).as_posix(): sha256_file(Path(f)) for f in files}, **(extra or {})}
    cm.write_json_atomic(rdir / "manifest.json", doc)
    return doc


def terminal_path(root: Path, family: str, *, rep: bool = False) -> Path:
    if family not in FAMILY_TESTS:
        raise Refused(f"unknown CB16 count family {family!r}")
    return Path(root) / (TERMINAL_REP_NAME if rep else TERMINAL_NAME).format(family=family)


def read_terminal(root: Path, family: str, *, rep: bool = False) -> dict | None:
    p = terminal_path(root, family, rep=rep)
    return json.loads(p.read_text()) if p.exists() else None


def record_terminal(root: Path, family: str, label: str, reason: str, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_DEV, rep_tests: tuple[str, ...] | None = None) -> dict:
    """A failed smoke, gate (GQG), a stall or an unrecoverable source makes the family TERMINAL (section 2.5): ONE write-once record and, at that moment, the family's counted
    lines (each test p = 1). With ``rep_tests`` the record is the Stage-2 one (the triggered reps counted once, p = 1). A second call returns the record and counts nothing; downstream
    jobs read it and end with exit 0 (never an endless exit 75)."""
    rep = rep_tests is not None
    p = terminal_path(require_output_root(Path(root)), family, rep=rep)
    if p.exists():
        return {**json.loads(p.read_text()), "newly_counted": False}
    tests = list(rep_tests) if rep else list(FAMILY_TESTS[family])
    doc = {"family": family, "label": label, "reason": str(reason)[:300], "tests": tests, "replication": rep, "counted": True, "status": TERMINAL_STATUS, "written_utc": cm.iso(time.time())}
    cm.write_once_json(p, doc)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    log_family(family, {t: {"p": 1.0, "testable": False, "advance": False, "verdict": label} for t in tests}, replication=rep, trials_path=trials_path, results_sha256=sha, role=role,
               n_triggered=len(tests) if rep else None)
    return {**doc, "newly_counted": True}


# ---- statistics helpers ------------------------------------------------------------------------------------------------------------------------


def holm(pvals: dict[str, float], alpha: float) -> dict:
    """STRICT Holm (reject iff p < alpha / (m - i) at every step so far), as CB12-CB15."""
    return c12.holm(pvals, alpha)


def stage1_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    """The Stage-1 step-down over the FIXED two tests (k1 = 2); a test not run / not testable / pending enters with p = 1. Holm's first step is 0.025 > 0.01: the step never
    withdraws an advance."""
    return c13.stage1_holm(pvals, alpha, STAGE1_HOLM_FAMILY)


def stage1_advance(p: float | None, checks_ok: bool, final_holm_reject: bool = False) -> bool:
    """Stage-1 advance: every binding check, one-sided p < 0.01 (strict) and the batch Holm (a p < 0.01 always passes its first step 0.025)."""
    return bool(checks_ok and p is not None and p < GATE_P and (final_holm_reject or p < STAGE_ALPHA / BATCH_HOLM_K1))


def stage2_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    full = {k: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


def stage2_final(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    """The final CB16-wide Stage-2 step (section 2.3): ONE strict Holm over every triggered Stage-2 test (Q1-rep, Q2, U1-rep, U2; U2 enters with the max of its two component p's; a
    triggered test that could not run enters with p = 1). Applied once; it can only ADD passes to the early alpha / 4 decisions. Other names are refused."""
    extra = [k for k in pvals if k not in STAGE2_NAMES]
    if extra:
        raise Refused(f"stage-2 final Holm: {extra} are not CB16 Stage-2 tests {tuple(STAGE2_NAMES)}")
    full = {STAGE2_NAMES[k]: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


def early_stage2_ok(p: float | None) -> bool:
    """A Stage-2 test finishing before k2 is known is judged against alpha / 4 (strict; never withdrawn)."""
    return p is not None and bool(p < EARLY_ALPHA2)


def stage2_pass(checks_ok: bool, p: float | None, final_holm_reject: bool = False) -> bool:
    """``checks_ok and (p < alpha / 4 early or the final Holm rejects)``."""
    return bool(checks_ok and (early_stage2_ok(p) or final_holm_reject))


def mde(se: float) -> float:
    """``3.80 x SE`` (section 2.7)."""
    return float(MDE_FACTOR * se) if math.isfinite(se) else math.nan


def availability(available: int, eligible: int) -> dict:
    """Section 2.6 (iv): below 60% of eligible units available the test is "not testable (availability)"; zero eligible is not testable."""
    share = (available / eligible) if eligible > 0 else math.nan
    return {"available": int(available), "eligible": int(eligible), "share": share, "min": AVAIL_MIN, "ok": bool(eligible > 0 and share >= AVAIL_MIN)}


AVAILABILITY_LABEL = "not testable (availability)"
SOURCE_NOT_TESTABLE = "not testable (source)"


def placebo_advance_rate(draw_ps: list[float | None], gate_p: float = GATE_P) -> dict:
    return c10.placebo_advance_rate(draw_ps, gate_p)


def top_k_drop_mask(v, cl, k: int = TOP_DROP) -> np.ndarray:
    return c9.top_k_drop_mask(v, cl, k)


def cluster_se_mean(v, cl) -> float:
    return c12.cluster_se_mean(v, cl)


def max_se_over_ways(v, ways: dict[str, Any]) -> float:
    """The largest CR1 clustered SE of mean(v) over the declared ways (what GQP / GUP write; no point estimate is ever written)."""
    ses = [cluster_se_mean(v, cl) for cl in ways.values()]
    ses = [s for s in ses if math.isfinite(s)]
    return float(max(ses)) if ses else math.nan


def cluster_p(v, clusters: dict[str, Any], *, estimator: Callable[[np.ndarray], float] | None = None, alpha: float | None = None, sign: float = 1.0) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared ways under the CB10 small-G rule (CB14's engine; CB16 seed 1616): G >= 30 CR1; 15 <= G < 30 CR2 + t(G - 1) with the
    Webb wild bootstrap; G < 15 the way LEAVES the max and its leave-one-cluster-out sign rule binds (``small_g_rules_hold``)."""
    return c14.cluster_p(v, clusters, min_units=2, min_first_clusters=1, seed=SEED_BOOT, n_wild=N_WILD, alpha=alpha, estimator=estimator, sign=sign)


def p_pass(r: dict | None, alpha: float) -> bool:
    return c14.p_pass(r, alpha)


def sign_ok(est, ref) -> bool:
    return c14.sign_ok(est, ref)


def leave_one_out_p(groups, stat_fn, p_fn, sign: float = 1.0, p_max: float = LOO_DAY_P) -> dict:
    return c13.leave_one_out_p(groups, stat_fn, p_fn, sign=sign, p_max=p_max)


def fe_demean(values, groups, w=None) -> np.ndarray:
    """Within-group (market fixed-effect) demeaning of one column or a 2-D array (weighted means with ``w``)."""
    x = np.asarray(values, float)
    g = np.asarray(groups).astype(str)
    wt = np.ones(len(g)) if w is None else np.asarray(w, float)
    out = np.array(x, dtype=float, copy=True)
    _, codes = np.unique(g, return_inverse=True)
    k = int(codes.max()) + 1 if len(codes) else 0
    sw = np.bincount(codes, weights=wt, minlength=k)
    if x.ndim == 1:
        m = np.bincount(codes, weights=wt * x, minlength=k) / np.where(sw > 0, sw, 1.0)
        return out - m[codes]
    for j in range(x.shape[1]):
        m = np.bincount(codes, weights=wt * x[:, j], minlength=k) / np.where(sw > 0, sw, 1.0)
        out[:, j] = x[:, j] - m[codes]
    return out


def fe_coef_pseudo(y, X, groups, j: int = 0, w=None) -> tuple[np.ndarray, float]:
    """(pseudo-values, coefficient) of regressor ``j`` in the market fixed-effect OLS of ``y`` on ``X`` (``groups`` = market; weighted with ``w``): both sides are demeaned within market
    and CB14's Frisch-Waugh pseudo-values give mean(v) = b_j with the cluster sandwich of b_j as the clustered variance of v."""
    y = np.asarray(y, float)
    Xa = np.asarray(X, float)
    if Xa.ndim == 1:
        Xa = Xa[:, None]
    yd = fe_demean(y, groups, w)
    Xd = fe_demean(Xa, groups, w)
    if len(y) < Xd.shape[1] + 2 or not np.isfinite(yd).all() or not np.isfinite(Xd).all() or float((Xd[:, j] ** 2).sum()) <= 0:
        return np.full(len(y), math.nan), math.nan
    return c14.wls_coef_pseudo(yd, Xd, w, j)


def fe_ols(y, X, groups) -> np.ndarray:
    """Market fixed-effect OLS coefficients of ``X``'s columns (no intercept: absorbed)."""
    yd = fe_demean(np.asarray(y, float), groups)
    Xd = fe_demean(np.asarray(X, float), groups)
    beta, *_ = np.linalg.lstsq(Xd, yd, rcond=None)
    return beta


def permute_within(values, strata, rng: np.random.Generator) -> np.ndarray:
    """One draw: ``values`` permuted among each stratum's units (a value never moves across strata)."""
    v = np.asarray(values).copy()
    st = np.asarray(strata).astype(str)
    order = np.argsort(st, kind="stable")
    s_sorted = st[order]
    cuts = np.flatnonzero(s_sorted[1:] != s_sorted[:-1]) + 1
    for idx in np.split(order, cuts):
        if len(idx) > 1:
            v[idx] = v[idx][rng.permutation(len(idx))]
    return v


# ---- trials ------------------------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_DEV) -> dict:
    """One ``cb16_descriptive`` line (EXCLUDE, counts 0): smoke, censuses (all of K), gates, strata, sports arms, shape, validity, tables, the H withdrawal record."""
    rec = {"kind": "cb16_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_16:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_family(family: str, results: dict[str, dict], *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_DEV, results_sha256: str = "",
               placebos: dict[str, dict] | None = None, n_triggered: int | None = None) -> None:
    """Per-test ``cb16_test`` / ``cb16_replication`` lines (EXCLUDE, ``n_tests`` 0), placebo lines (0) and ONE count line ``ml_explain`` (source ``creative_batch_16:<family>[:rep]``)
    whose ``n_tests`` is the family's number of tests (Stage 1: Q 1, U 1; a test behind a failed gate counted with p = 1) or the reps actually triggered (Stage 2: <= 2 each)."""
    if family not in FAMILY_TESTS:
        raise Refused(f"unknown CB16 count family {family!r}")
    allowed = FAMILY_REP_TESTS[family] if replication else FAMILY_TESTS[family]
    bad = [t for t in results if t not in allowed]
    if bad:
        raise Refused(f"{bad} are not CB16-{family} {'rep ' if replication else ''}tests {allowed}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb16_replication" if replication else "cb16_test"
    for tid, result in results.items():
        p = result.get("p", 1.0)
        if not result.get("testable", True) or p is None:
            p = 1.0
        base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_16", "hypothesis": tid, "family": family, "results_sha256": results_sha256}
        provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                                 "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
        pl = (placebos or {}).get(tid)
        if pl:
            provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": pl.get("note", "placebo"), "advance_rate": pl.get("advance_rate"),
                                     "n_draws": pl.get("n_draws"), "n_tests": 0}, tp)
    n = len(results) if n_triggered is None else int(n_triggered)
    count_role = role if role in provenance.EVIDENCE_ROLES else EVIDENCE_ROLE_DEV  # the count line is bookkeeping; the validated roles do not include "prospective"
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": count_role, "source": f"creative_batch_16:{family}{':rep' if replication else ''}",
                             "dataset": "creative_batch_16", "n_tests": n, "n_tests_by_family": {f"cb16_{family}{'_rep' if replication else ''}": n},
                             "hypotheses": sorted(results), "replication": bool(replication), "advanced": sorted(t for t, r in results.items() if r.get("advance")),
                             "results_sha256": results_sha256, "note": "CB16 count line: the family's tests (a test behind a failed gate is still counted, p = 1)"}, tp)


# ---- q0380: exclusion keys with per-key source attribution (section 1.3) ------------------------------------------------------------------------


def id_source_path(rel: str, hist_root: Path, research_root: Path | None = None) -> Path:
    root = rel.split("/", 1)[0]
    base = (Path(research_root) if research_root is not None else Path(hist_root).parent) if root in ID_RESEARCH_ROOTS else Path(hist_root)
    return base / rel


def guard_id_file(path: Path) -> Path:
    """The ONLY way a CB16 job reads a CB15 frame: an id-only reader of one whitelisted file (``ID_READABLE``). Outcome, guarded and holdout files are refused."""
    p = Path(path)
    if "guarded" in p.name or "outcome" in p.name.lower() or is_holdout_path(p):
        raise Refused(f"{p}: outcome, guarded and holdout files are never opened by CB16")
    idx = next((i for i, x in enumerate(p.parts) if x in ID_READABLE), None)
    if idx is None or "/".join(p.parts[idx + 1:]) not in ID_READABLE[p.parts[idx]]:
        raise Refused(f"{p}: not an id-only readable CB15 frame file {ID_READABLE}")
    refuse_path(p, allow=(p.parts[idx],))
    return p


def read_id_columns(path: Path) -> dict[str, set[str]]:
    """Id columns of one id-readable file (csv, csv.gz or jsonl); every other field is dropped at read."""
    p = guard_id_file(path)
    out: dict[str, set[str]] = {}
    if p.name.endswith(".jsonl"):
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rec = json.loads(line, object_pairs_hook=lambda kv: {k: v for k, v in kv if k in ID_COLUMNS})
                except ValueError:
                    continue
                if isinstance(rec, dict):
                    for c, v in rec.items():
                        if v not in (None, ""):
                            out.setdefault(c, set()).add(str(v))
        return out
    opener = gzip.open if p.name.endswith(".gz") else open
    csv.field_size_limit(10**9)
    with opener(p, "rt", encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        keep = [c for c in (rdr.fieldnames or []) if c in ID_COLUMNS]
        for row in rdr:
            for c in keep:
                if row.get(c):
                    out.setdefault(c, set()).add(str(row[c]))
    return out


def market_ids_of(cols: dict[str, set[str]]) -> set[str]:
    return set(cols.get("market_id", set())) | set(cols.get("p_market_id", set()))


def frame_ids(hist_root: Path, research_root: Path | None = None) -> tuple[dict[str, set[str]], list[str]]:
    """Market ids per CB15 id source (``ID_READABLE``); a file that does not exist yet is 'absent at q0380' (recorded)."""
    found: dict[str, set[str]] = {}
    absent: list[str] = []
    for root, files in ID_READABLE.items():
        for name in files:
            p = id_source_path(f"{root}/{name}", hist_root, research_root)
            if p.is_file():
                found.setdefault(root, set()).update(market_ids_of(read_id_columns(p)))
            else:
                absent.append(f"{root}/{name}")
    return found, absent


def read_keys_with_sources(path: Path) -> list[dict]:
    """The CB15 q0340 key file (``KEY_COLUMNS`` with the per-key ``sources`` column) as rows; refused without attribution."""
    p = Path(path)
    rows = []
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        if "sources" not in (rdr.fieldnames or []):
            raise Refused(f"{p}: no per-key source attribution (the CB15 q0340 file carries a sources column)")
        for r in rdr:
            rows.append({**{c: r.get(c, "") for c in KEY_COLUMNS[:-1]}, "sources": {x for x in str(r.get("sources") or "").split(";") if x}})
    return rows


def attribute_sources(base_rows: list[dict], frames: dict[str, set[str]], seal_ids: set[str]) -> dict[str, set[str]]:
    """Per market id, every source that carries it: the CB15 file's own attribution (prefixed ``cb15:``; none -> ``base:cb15_q0340``), ``frame:<root>`` and ``seal_copies``."""
    out: dict[str, set[str]] = {}
    for r in base_rows:
        out.setdefault(str(r["market_id"]), set()).update({f"cb15:{s}" for s in r["sources"]} or {BASE_SOURCE})
    for root, ids in frames.items():
        for i in ids:
            out.setdefault(i, set()).add(f"frame:{root}")
    for i in seal_ids:
        out.setdefault(i, set()).add("seal_copies")
    return out


def key_sources(rows: list[dict]) -> dict[str, dict[str, set[str]]]:
    """Per key type (market, event, neg_risk_market, series), the union of the sources of every market carrying the key."""
    out: dict[str, dict[str, set[str]]] = {"market": {}, "event": {}, "neg_risk_market": {}, "series": {}}
    for r in rows:
        src = set(r.get("sources") or {BASE_SOURCE})
        out["market"].setdefault(str(r["market_id"]), set()).update(src)
        for e in str(r.get("event_ids") or "").split(";"):
            if e:
                out["event"].setdefault(e, set()).update(src)
        if r.get("neg_risk_market_id"):
            out["neg_risk_market"].setdefault(str(r["neg_risk_market_id"]), set()).update(src)
        for s in str(r.get("series_ids") or "").split(";"):
            if s:
                out["series"].setdefault(s, set()).update(src)
    return out


def load_keys(path: Path) -> tuple[list[dict], dict[str, dict[str, set[str]]], str]:
    """(rows, key sources, sha256) of the CB16 q0380 key file."""
    p = Path(path)
    rows = read_keys_with_sources(p)
    return rows, key_sources(rows), sha256_file(p)


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, hist_root: Path, base_path: Path, base_sha256: str, seals_dir: Path | None = None, is_committed=None, rps: float = 2.0,
                   disk_cap: int = int(KEYS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, now: float | None = None, sleep=None, live_check=None, should_stop=None,
                   wall_clock=None, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB,
                   free_fn=None, research_root: Path | None = None) -> dict:
    """q0380. CB15 q0340's key file (sha256 pin MANDATORY; its per-key sources kept) plus, by closed-first Gamma id lookup (<= 50 per request, resumable), every market id of the CB15
    frames (E race map, P pairs, P Stage-2 pairs; ids only; a missing one is 'absent at q0380') and of every committed seal copy. Every row carries its source(s). More than 2% of ALL
    ids without metadata -> ``disjointness_unverified`` (recorded; Q/U keep their in-window rule, K reports overlap counts only). CB17 must add CB16's frame ids."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    out_root, seals_dir = require_output_root(Path(out_root)), Path(seals_dir or cm.SEALS_DIR)
    base_path = Path(base_path)
    if not base_sha256 or base_sha256 == PIN_UNSET:
        raise Refused(f"the sha256 pin of the CB15 key file (--base-sha256) is unset ({PIN_UNSET}); the coordinator fills it from `sha256sum` on the host after CB15 q0340")
    refuse_path(base_path, allow=("creative_batch15",))
    got = sha256_file(base_path) if base_path.exists() else None
    if got != base_sha256:
        raise Refused(f"base key file {base_path} sha256 {got} != pinned {base_sha256}")
    base_rows = read_keys_with_sources(base_path)
    base_ids = {str(r["market_id"]) for r in base_rows}
    require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    frames, absent = frame_ids(Path(hist_root), research_root)
    seal_all, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, is_committed=is_committed, own=())
    msrc = attribute_sources(base_rows, frames, set(seal_all))
    lookup = set(msrc) - base_ids
    fr = cm.open_run(out_root, KEYS_RUN, transport, allowed_run_id=KEYS_RUN, kind="cb16_exclusion_keys", label="CB16 exclusion keys",
                     params={"base_keys_sha256": base_sha256, "n_base_ids": len(base_ids), "n_lookup_ids": len(lookup), "frames": {k: len(v) for k, v in frames.items()},
                             "sets_absent_at_q0380": absent, "seal_copies_used": used, "seal_copies_skipped": skipped, "evidence_role": EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep or time.sleep, live_check=live_check,
                     wall_clock=wall_clock or time.time, snapshot_root=snapshot_root, health_check=health_check)
    rep_new, stopped = c12.exclusion_stage(fr, lookup, should_stop)
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep_new is not None
    rows: list[list[str]] = []
    seen: set[str] = set()
    for r in base_rows:
        mid = str(r["market_id"])
        seen.add(mid)
        rows.append([*(r[c] for c in c6.KEY_COLUMNS), ";".join(sorted(msrc.get(mid, {BASE_SOURCE})))])
    with gzip.open(fr.rdir / "exclusion_keys.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            mid = str(r[c6.KEY_COLUMNS[0]])
            if mid in seen:
                continue
            seen.add(mid)
            rows.append([*(r[c] for c in c6.KEY_COLUMNS), ";".join(sorted(msrc.get(mid, {BASE_SOURCE})))])
    keys_out = out_root / "exclusion_keys.csv.gz"
    out_root.mkdir(parents=True, exist_ok=True)
    keys_out.write_bytes(hb._gz_csv_bytes(list(KEY_COLUMNS), sorted(rows)))
    base_rep_p = base_path.with_name(c9.EXCLUSION_REPORT_NAME)
    base_rep = json.loads(base_rep_p.read_text()) if base_rep_p.exists() else {}
    n_all = int(base_rep.get("n_ids", len(base_ids))) + len(lookup)
    n_missing = int(base_rep.get("n_missing", 0)) + rep_new["n_missing"]
    share = n_missing / n_all if n_all else 1.0
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": UNVERIFIED if share > MAX_UNVERIFIED_KEY_SHARE else "verified", "base_keys_sha256": base_sha256, "new": rep_new, "frames": {k: len(v) for k, v in frames.items()},
           "sets_absent_at_q0380": absent, "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "keys_sha256": sha256_file(keys_out),
           "sources": {"cb15_attribution_kept": True, "frame_roots": sorted(frames), "rule": "each key carries its source(s); Q/U drop only in-window sealed ids (section 1.3); K counts overlaps"},
           "built_utc": cm.iso(time.time())}
    (out_root / c9.EXCLUSION_REPORT_NAME).write_text(json.dumps(rep, indent=1, sort_keys=True))
    status = UNVERIFIED if rep["disjointness"] == UNVERIFIED else KEYS_STATUS
    m = fr.manifest(None, {"exclusion_report": {k: rep[k] for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys_sha256")}, "status": status, "complete": True})
    m["status"] = status
    return m


# =====================================================================================================================================================
# Per-part rules hashing. Everything below is machinery (not hashed); the hashed content is the module-level functions, classes and UPPER_CASE constants.
# =====================================================================================================================================================


def common_funcs() -> list:
    return c12.module_funcs(importlib.import_module(__name__), exclude=RULES_MACHINERY)


def family_modules(part: str) -> list:
    if part not in FAMILY_PARTS:
        raise Refused(f"unknown rules part {part!r}")
    return c12._mods(FAMILY_MODULES[part])


def part_funcs(part: str) -> list:
    """The functions hashed for ``part``: the common ones, plus (family parts) that part's own module(s) only (common: the smoke orchestrator)."""
    funcs = list(common_funcs())
    if part == "common":
        funcs += c12.module_funcs(importlib.import_module(".cb16_smoke", __package__))
    else:
        for mod in family_modules(part):
            funcs += c12.module_funcs(mod)
    seen: set[int] = set()
    return [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]


def _code_names(obj) -> tuple[set[str], dict]:
    names: set[str] = set()
    glb: dict = {}
    funcs = [obj] if inspect.isfunction(obj) else []
    if inspect.isclass(obj):
        for v in vars(obj).values():
            v = getattr(v, "__func__", v)
            if isinstance(v, property):
                funcs += [x for x in (v.fget, v.fset, v.fdel) if x is not None]
            elif inspect.isfunction(v):
                funcs.append(v)
    for fn in funcs:
        glb = fn.__globals__
        stack = [fn.__code__]
        while stack:
            co = stack.pop()
            names.update(co.co_names)
            stack += [c for c in co.co_consts if inspect.iscode(c)]
    return names, glb


def _helper_key(obj) -> str:
    return f"{obj.__module__.rsplit('.', 1)[-1]}.{obj.__qualname__}"


def external_closure(roots: Iterable) -> dict[str, Any]:
    """Every function / class OUTSIDE the CB16 modules (``astrolabe.*`` only) that ``roots`` reach, transitively (CB14 section 11 fix F8: a shared helper's own helpers are hashed too).
    A name resolves through the referencing function's globals: a function or class directly, or, for a module, every attribute name the function uses that is a function / class of
    that module (over-inclusive, never under-inclusive). CB16 functions are traversed, not recorded (their sources are in the part's own ``func_sources_sha256``)."""
    out: dict[str, Any] = {}
    seen: set[int] = set()
    stack = list(roots)
    while stack:
        obj = stack.pop()
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        mod = getattr(obj, "__module__", "") or ""
        if not mod.startswith("astrolabe."):
            continue
        if not mod.startswith(__package__ + ".cb16"):
            out[_helper_key(obj)] = obj
        names, glb = _code_names(obj)
        for n in names:
            g = glb.get(n)
            if inspect.isfunction(g) or inspect.isclass(g):
                stack.append(g)
            elif inspect.ismodule(g) and g.__name__.startswith("astrolabe."):
                stack += [a for a in (getattr(g, x, None) for x in names) if (inspect.isfunction(a) or inspect.isclass(a)) and getattr(a, "__module__", None) == g.__name__]
    return dict(sorted(out.items()))


def shared_helper_sources(part: str = "common") -> dict[str, str]:
    """sha256 of the source of every shared helper the CB16 rules of ``part`` call: the declared roots (``SHARED_HELPERS``) and every helper reached transitively from them and from the
    part's own functions (``external_closure``); this includes the pinned CB13 functions."""
    from . import cb2_weather as cw  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415

    mods = {"c12": c12, "c10": c10, "c9": c9, "cw": cw, "c13": c13, "c14": c14, "bk": bk, "cm": cm}
    roots = [getattr(mods[m], n) for m, n in SHARED_HELPERS] + list(part_funcs(part))
    return {k: hashlib.sha256(inspect.getsource(v).encode()).hexdigest() for k, v in external_closure(roots).items()}


def common_declared() -> dict:
    return {"refused_roots": list(EXTRA_REFUSED_ROOTS), "always_refused": list(ALWAYS_REFUSED_ROOTS), "h15_rule": "every h15_* root refused except the q0380 id files",
            "id_readable": {k: list(v) for k, v in ID_READABLE.items()}, "output_roots": list(ALLOWED_OUTPUT_ROOT_PARTS),
            "seeds": {"boot": SEED_BOOT, "placebo": PLACEBO_SEEDS, "placebo_range": list(PLACEBO_SEED_RANGE), "u_validity": SEED_U_VALIDITY, "k_audit": SEED_K_AUDIT},
            "bootstrap": {"n_boot": N_BOOT, "n_wild": N_WILD, "small_g": "G>=30 CR1; 15<=G<30 CR2 t(G-1) + Webb wild; G<15 the way leaves the max and its leave-one-cluster-out sign rule binds (CB10 2.3, A-C1)"},
            "holm": {"k1": BATCH_HOLM_K1, "family": list(STAGE1_HOLM_FAMILY), "alpha": STAGE_ALPHA, "stage2_k_max": STAGE2_K_MAX, "stage2_early_alpha": EARLY_ALPHA2, "strict": True,
                     "stage2_final": "one CB16-wide strict Holm over the triggered Stage-2 tests; U2 enters with the max of its two component p's; adds passes only"},
            "disk": {"data_dumps_cap_gb": DATA_DUMPS_CAP_GB, "free_min_gb": FREE_DISK_MIN_GB, "output_cap_gb": CB16_OUTPUT_CAP_GB},
            "field_whitelists": {"prints": list(PRINT_FIELDS), "lookback": list(LOOKBACK_FIELDS), "forbidden_prints": list(FORBIDDEN_PRINT_FIELDS), "u2_lag_only": list(U2_LAG_FIELDS),
                                 "sweeps": list(SWEEP_FIELDS), "data_api": list(DATA_API_FIELDS), "forbidden_output": list(FORBIDDEN_OUTPUT_COLUMNS), "forbidden_parse": list(FORBIDDEN_PARSE_FIELDS)},
            "dates": {"s_a_rule": "max(2026-11-02T00Z, first 00:00Z at or after T16_A_freeze + 24 h)", "lookback_floor": LOOKBACK_FLOOR, "election_night": list(ELECTION_NIGHT),
                      "window_days": WINDOW_S / 86400, "frame_delay_h": FRAME_DELAY_S / 3600, "e011_earliest": E011_ANALYSIS_EARLIEST},
            "key_rule": "Q/U drop a market / event id only if a sealed historical set holds it with a stored timestamp inside SCREEN_A or REP_A (live stages are collection overlap); K counts overlaps",
            "cb13_pins": dict(CB13_PINS), "mde": f"{MDE_FACTOR} x SE", "stop_rule": STOP_RULE, "sports_in_primary": CB16_SPORTS_IN_PRIMARY}


def rules_part_doc(part: str) -> dict:
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    this = importlib.import_module(__name__)
    consts = {"cb16_common": c12.module_constants(this)}
    declared: dict[str, Any] = {}
    if part == "common":
        smoke = importlib.import_module(".cb16_smoke", __package__)
        consts["cb16_smoke"] = c12.module_constants(smoke)
        declared["smoke"] = smoke.declared()
        declared["common"] = common_declared()
    else:
        mods = family_modules(part)
        if len(mods) != len(FAMILY_MODULES[part]):
            return {"part": part, "part_declared": False, "rules_version": RULES_VERSION, "reason": f"family modules {FAMILY_MODULES[part]} not all present yet"}
        for mod in mods:
            unready = getattr(mod, "part_unready", lambda: None)()
            if unready:
                return {"part": part, "part_declared": False, "rules_version": RULES_VERSION, "reason": str(unready)}
            name = mod.__name__.rsplit(".", 1)[-1]
            consts[name] = c12.module_constants(mod)
            declared[name] = mod.declared()
    funcs = part_funcs(part)
    src = {f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}
    return {"part": part, "part_declared": True, "rules_version": RULES_VERSION, "constants": consts, "declared": declared,
            "wallet": {"read": False, "note": "no CB16 job reads or stores a wallet field, a transaction hash (tx16 is aggregated in memory and discarded), the monitor's or the Data API's side field"},
            "shared_helper_sources_sha256": shared_helper_sources(part),
            "funcs_sha256": hashlib.sha256("\n".join(src[k] for k in sorted(src)).encode()).hexdigest(), "func_sources_sha256": dict(sorted(src.items()))}


def rules_part_file_doc(part: str) -> dict:
    d = json.loads(json.dumps(rules_part_doc(part), sort_keys=True, default=str))
    if d.get("part_declared") is False:
        return {**d, "rules_sha256": None}
    return {**d, "rules_sha256": cm.sha_obj(d)}


def rules_file_doc(parts: tuple[str, ...] = PARTS) -> dict:
    return {"rules_version": RULES_VERSION, "parts": {p: rules_part_file_doc(p) for p in parts}}


def write_rules(path: Path | None = None) -> Path:
    """Write the rules file. An existing file's DECLARED part must equal the code's (a declared part is never rewritten)."""
    path = Path(path or (SEALS_DIR / "cb16_rules.json"))
    want = rules_file_doc()
    if path.exists():
        have = json.loads(path.read_text())
        if have.get("rules_version") != RULES_VERSION:
            raise Refused(f"{path} exists with rules_version {have.get('rules_version')}; a rules file is never rewritten")
        hp = have.get("parts") or {}
        for p in PARTS:
            h = hp.get(p)
            if h is not None and h.get("part_declared") is not False and h != want["parts"][p]:
                raise Refused(f"{path} exists with a different, already declared part {p}; a rules file is never rewritten")
        if hp == want["parts"]:
            return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "A") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's. Only that part's modules are imported. Returns the part's ``rules_sha256``."""
    path = Path(path or (SEALS_DIR / "cb16_rules.json"))
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
    if have is None:
        raise Refused(f"rules file {path} has no part {part!r}")
    if have.get("part_declared") is False:
        raise Refused(f"rules part {part} is not declared in {path}: {have.get('reason', '')}")
    want = rules_part_file_doc(part)
    if want.get("part_declared") is False:
        raise Refused(f"rules part {part} is not declared in the code: {want.get('reason', '')}")
    if have != want:
        raise Refused(f"rules hash mismatch (part {part}): file {have.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]
