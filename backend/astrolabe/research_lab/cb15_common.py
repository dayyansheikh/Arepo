# ruff: noqa: E501
"""CB15 shared parts (docs/research_lab/CREATIVE_BATCH_15.md sections 1.3-1.4, 2.1-2.8, 5, 9-10).

Everything common to CB15-E (election-night reporting-order drift, one night, one cluster) and CB15-P (the pair at birth) lives here: the refusal lists (outputs AND inputs; no live
store, no CB1-CB14 root other than through the id-only readers, no ``holdout`` path), the forbidden-field guards (``side``, wallets, transaction hashes, ``outcomePrices``,
``umaResolutionStatus(es)``, ``closedTime``, Kalshi ``result`` / ``settlement_value``), the disk guards (data-dumps cap 40 and root free disk, exit 75 = "pending" outside the E night
window), the fixed-k1 (= 4) Holm helpers (E judged when it runs at ``p < min(0.01, alpha / k1)``, strict; Stage-2 early rule at alpha / 2), the clustered-inference helpers (CB10
small-G rule, seed 1515), the within-stratum state-label permutation (seed 15101, 9,999 draws), the trial-line helpers (kinds ``cb15_test`` / ``cb15_replication`` /
``cb15_descriptive``), the source-attributed exclusion-key union (q0340) with the per-family key rules, the terminal not-testable records and the per-part rules hashing.

**Per-part rules hashing (the CB11 whole-document-hash pitfall).** ``seals/cb15_rules.json`` holds one sha256 per part: ``common``, ``E``, ``P``. A family part hashes ONLY (a) the
common rule functions and constants of this module (plus, for ``common``, the smoke orchestrator), and (b) the functions and UPPER_CASE constants of that family's own module. Every
part also carries the sha256 of every shared cross-module helper the CB15 rules call (``SHARED_HELPERS``). Verifying part E imports ``cb15_e`` and nothing else; part P imports
``cb15_p`` only. E can therefore freeze on its calendar without waiting for P, and no rule of one part changes after the other part's read. Rule: nothing family-specific may be added
to this module after the first CB15 job.
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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import cb10_common as c10
from . import cb12_common as c12
from . import provenance

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

# ---- constants (hashed with this module: every UPPER_CASE JSON-able constant below is part of ``common``) ------------------------------------------------
RULES_VERSION = "cb15-rules-v1"
PARTS = ("common", "E", "P")
FAMILY_PARTS = ("E", "P")
FREEZE_PARTS = ("E", "P")
FAMILY_MODULES = {"E": ("cb15_e",), "P": ("cb15_p",)}
FAMILY_TESTS = {"E": ("E1", "E2"), "P": ("P1", "P2")}
FAMILY_REP_TESTS = {"E": (), "P": ("P1", "P2")}  # E has no Stage 2 in CB15
STAGE1_HOLM_FAMILY = ("E1", "E2", "P1", "P2")
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 4, fixed now (round 1 item L: the change from 6 comes from the CH125 withdrawal, not from Holm power)
STAGE_ALPHA = 0.05  # Stage 1 batch Holm and Stage 2 Holm, one-sided
GATE_P = 0.01
E_JUDGE_ALPHA = min(GATE_P, STAGE_ALPHA / BATCH_HOLM_K1)  # = 0.01: E is judged when it runs, strictly, never withdrawn (round 1 item 7)
STAGE2_K_MAX = 2  # P1-rep, P2-rep: the largest possible Stage-2 count
EARLY_ALPHA2 = STAGE_ALPHA / STAGE2_K_MAX  # a Stage-2 test that finishes before k2 is known is judged against alpha / 2 = 0.025 (strict)
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 1515
N_WILD = 9999
PERM_DRAWS = 9999
SEED_PERM = 15101
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
PLACEBO_SEED_RANGE = (15101, 15130)
PLACEBO_SEEDS = {"P1_shuffle": 15111, "P2_shuffle": 15112}
SEED_PAIRED_BOOT = 15121
MDE_MULT = 3.16
MDE_INFLATE = 1.2
G_CR2 = 15  # CB10 section 2.3: a way with fewer clusters leaves the max and its leave-one-cluster-out sign rule binds
TOP_DROP = 5
AVAIL_MIN = 0.60
EVIDENCE_ROLE_HIST = "exploratory_historical"
EVIDENCE_ROLE_DEV = "exploratory_dev"
EVIDENCE_ROLE_PROSPECTIVE = "prospective"  # per-test lines of E and of P Stage 2; the ml_explain COUNT line keeps a role that provenance.EVIDENCE_ROLES validates
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
PIN_UNSET = "TODO-COORDINATOR"
CB15_SPORTS_IN_PRIMARY = False
SMOKE_VERSION = "cb15-smoke-v1"
DATA_DUMPS_CAP_GB = 40.0
FREE_DISK_MIN_GB = 4.5
CB15_OUTPUT_CAP_GB = 1.2
HEARTBEAT_S = cm.HEARTBEAT_S
USER_AGENT = "arepo-research-probe/1.0 (read-only counts; https://www.arepolabs.com)"
FEE_FLOOR = 0.04  # E2 / P2 taker fee floor (politics; the current, not the point-in-time, schedule, so the floor is conservative)
W_STAR = -0.093  # EXECUTION_COSTS.md line 39: the p90 round trip; no bid at exit / lost units in the reach check
COST_ROBUST_PER_SIDE = 0.01
PAPER_SIZE = 100.0
# Output roots CB15 writes under, and input roots it never reads (section 1.1 last rows, 1.3)
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch15", "h15_elect_live", "h15_birth", "h15_birth_live")
KEYS_RUN = "exclusion_run15"
KEYS_STATUS = EXCLUSION_KEYS_COMPLETE
KEYS_OUTPUT_CAP_GB = 0.01
HOLDOUT_PARTS = ("holdout", "t_holdout")
EXTRA_REFUSED_ROOTS = ("creative_batch14", "creative_batch13", "creative_batch12", "creative_batch11", "creative_batch10", "creative_batch9", "creative_batch8", "creative_batch7",
                       "creative_batch6", "creative_batch5", "creative_batch4", "creative_batch3", "creative_batch2", "creative_batch1", "snapshots", "trade_samples", "live_trades",
                       "book_sweeps", "surprise_live", "cross_venue_live", "cross_venue", "forecasts", "flow_screen", "h9_flow", "h10_sign", "h10_dlad", "h10_brk", "h11_wprints",
                       "h11_pol", "h11_attn", "h12_say", "h12_quake", "h12_prints", "h12_quake_live", "h12_opt_live", "h13_touch", "h13_binance", "h14_wiki", "h14_wiki_live",
                       "h14_speech", "h1_first", "h2_main", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era", "h7_cb4_series", "h8_tail", "h8_tail_b",
                       "h8_text", "h8_geo", "cb3_followup", "cb6_followup")
ALWAYS_REFUSED_ROOTS = ("surprise_live", "cross_venue_live", "trade_samples", "forecasts", "flow_screen", "live_trades", "snapshots", "book_sweeps")
LIVE_ROOT_NAMES = ("cross_venue_live", "surprise_live")
EXTRACT_ROOT_RE = r"^cb\d+_extract$"
EXPERIMENT_ROOT_RE = r"^e0\d\d$"
# id-only readers (q0340): the frame roots whose id columns feed the exclusion keys, and the files (relative to the root) each may open. Nothing else under them is opened. A HOLDOUT
# file is opened ONLY when named here, and then only its id columns leave the reader. ``creative_batch13`` lives under research_lab/, every other root under history/.
ID_READABLE = {"h11_attn": ("frame.csv.gz", "entities.csv.gz", "holdout/frame_hold.csv.gz"), "h11_pol": ("frame.csv.gz",), "h11_wprints": ("markets.csv.gz",),
               "h12_say": ("events.csv.gz", "members.csv.gz"), "h13_touch": ("events.csv.gz", "members.csv.gz", "holdout/events.csv.gz", "holdout/members.csv.gz"),
               "h12_quake": ("events.csv.gz", "members.csv.gz"), "h12_prints": ("markets.csv.gz",), "h12_quake_live": ("markets.csv.gz",), "h12_opt_live": ("markets.csv.gz",),
               "creative_batch13": ("t_screen/fills.csv.gz", "t_holdout/fills.csv.gz"),
               "h14_wiki": ("frame.csv.gz",), "h14_wiki_live": ("frame_ids.csv.gz",), "h14_speech": ("events_p.csv.gz", "events_n.csv.gz", "events_s2.csv.gz", "members.csv.gz")}
ID_RESEARCH_ROOTS = ("creative_batch13",)
ID_COLUMNS = ("market_id", "event_id", "condition_id", "neg_risk_market_id", "negRiskMarketID", "series_id")
KEY_COLUMNS = ("market_id", "found", "event_ids", "neg_risk_market_id", "series_ids", "sources")
C1_SOURCE = "c1"  # the C1 set (matches.json; CB5-K, CB12-X and E009's design sample use the same pairs): P's population (declared deviation, round 1 item 11)
BASE_SOURCE = "base:cb14_q0302"
CB14_KEYS_FILE = "exclusion_keys.csv.gz"
TERMINAL_NAME = "terminal_{family}.json"
TERMINAL_STATUS = "terminal_not_testable"
# Fields: forbidden in any written output
FORBIDDEN_OUTPUT_COLUMNS = ("side", "wallet", "wallet_hash", "proxyWallet", "tx16", "transactionHash", "tx_hash", "hash", "name", "pseudonym", "user", "userid", "username",
                            "outcome_prices", "outcomePrices", "umaResolutionStatus", "umaResolutionStatuses", "uma_status", "closedTime", "closed_time", "result", "settlement_value",
                            "p_end")
FORBIDDEN_PARSE_FIELDS = ("side", "proxyWallet", "outcomePrices", "umaResolutionStatus", "umaResolutionStatuses", "closedTime", "result", "settlement_value", "transactionHash", "hash",
                          "name", "pseudonym", "p_end")
TICK = 0.01
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
GAMMA_MARKETS = "https://gamma-api.polymarket.com/markets"
GAMMA_SEARCH = "https://gamma-api.polymarket.com/public-search"
GAMMA_PAGE = 100
GAMMA_OFFSET_CAP = 2000
LOOKUP_PER_REQUEST = 50
DATA_DUMPS = cm.DATA_DUMPS
HIST_ROOT = cm.HIST_ROOT
RESEARCH_ROOT = DATA_DUMPS / "research_lab"
CB15_DIR = RESEARCH_ROOT / "creative_batch15"
CB14_KEYS_DEFAULT = RESEARCH_ROOT / "creative_batch14" / CB14_KEYS_FILE
SEALS_DIR = cm.SEALS_DIR
SMOKE_E_DEFAULT = CB15_DIR / "smoke_E.json"
SMOKE_P_DEFAULT = CB15_DIR / "smoke_P.json"

RULES_MACHINERY = ("rules_part_doc", "rules_part_file_doc", "rules_file_doc", "write_rules", "verify_rules", "family_modules", "common_funcs", "part_funcs", "shared_helper_sources",
                   "common_declared")
# Cross-module helpers the CB15 rules call: the sha256 of each one's source is part of EVERY part's rules doc, so a change to a shared CB2 / CB6 / CB8 / CB9 / CB10 / CB12 helper
# changes the CB15 rules shas.
SHARED_HELPERS = (("cw", "small_g_pvalue"), ("cw", "_cluster_sums"), ("c12", "holm"), ("c12", "cluster_se_mean"), ("c9", "top_k_drop_mask"), ("c10", "placebo_advance_rate"),
                  ("c10", "leave_one_out_sign"), ("c12", "aggregate_transactions"), ("c12", "fetch_prints_paged"), ("c12", "reach_ok"), ("c12", "listish"), ("c12", "parse_iso"),
                  ("c12", "iso_week_of"), ("c12", "read_csv_gz"), ("c12", "read_id_set"), ("c12", "exclusion_stage"), ("c12", "lookup_keys_closed_first"), ("c12", "manifest_complete"),
                  ("c12", "require_complete"), ("c12", "verify_fetch"), ("c12", "c1_market_ids"), ("c12", "module_constants"), ("c12", "module_funcs"), ("c10", "require_disk"),
                  ("c9", "write_stall"), ("c9", "stall_of"), ("c9", "write_results_once"), ("c6", "KEY_COLUMNS_SRC"), ("bk", "seal_copy_ids_audited"), ("cm", "write_once_json"),
                  ("cm", "write_json_atomic"), ("cm", "idle"))


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


def iso_week_of(epoch: float) -> str:
    return c12.iso_week_of(epoch)


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


def fee(rate: float, p: float) -> float:
    """Taker fee ``rate * p * (1 - p)`` per share."""
    return float(rate) * float(p) * (1.0 - float(p))


def taker_rate(fee_rate, floor: float = FEE_FLOOR) -> float:
    """``max(feeSchedule.rate, floor)``; a missing rate is the floor."""
    r = num(fee_rate)
    return float(max(r, floor)) if math.isfinite(r) else float(floor)


def round_trip_net(entry: float, exit_: float, rate: float, extra_per_side: float = 0.0) -> float:
    """Net per share of buying a token at ``entry`` and selling it at ``exit_``: ``x - e - fee(e) - fee(x) - 2 * extra``."""
    return float(exit_ - entry - fee(rate, entry) - fee(rate, exit_) - 2.0 * extra_per_side)


def yes_price(price: float, outcome_index: int, yes_index: int) -> float:
    return float(price) if int(outcome_index) == int(yes_index) else 1.0 - float(price)


# ---- refusals ----------------------------------------------------------------------------------------------------------------------------------


def refused_names() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*c10.REFUSED_ROOTS, *c10.REFUSED_RUN_IDS, *EXTRA_REFUSED_ROOTS)))


def refuse_path(path: Path, *, allow: tuple[str, ...] = ()) -> Path:
    """Output AND input guard: refuse any path with a CB1-CB14 / sealed / live root among its parts, any ``cb<n>_extract`` or ``e0xx`` directory, and anything under the always-refused
    live stores (``allow`` cannot lift those). ``allow`` names roots one reader may open (id-only readers, the C1 files ``cross_venue``)."""
    parts = Path(path).parts
    names = tuple(n for n in refused_names() if n not in allow or n in ALWAYS_REFUSED_ROOTS)
    bad = [p for p in parts if p in names or re.match(EXTRACT_ROOT_RE, p) or re.match(EXPERIMENT_ROOT_RE, p) or any(L in p for L in LIVE_ROOT_NAMES)]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB14 / sealed / live root ({bad[0]}); CB15 refuses it")
    return Path(path)


def is_holdout_path(path: Path) -> bool:
    p = Path(path)
    return any(x in HOLDOUT_PARTS for x in p.parts) or "holdout" in p.name


def guard_input_path(path: Path, *, allow: tuple[str, ...] = ()) -> Path:
    """A generic input guard for non-id reads: every refused root, every holdout path (CB15 never opens a holdout except through the id-only readers)."""
    p = Path(path)
    refuse_path(p, allow=allow)
    if is_holdout_path(p):
        raise Refused(f"{p}: holdout paths are never opened by CB15 (ids only, through the id-only readers)")
    return p


def guard_id_file(path: Path) -> Path:
    """The ONLY way a CB15 job reads another batch's frame: an id-only reader of one whitelisted file (``ID_READABLE``). Outcome and guarded files are always refused."""
    p = Path(path)
    if "guarded" in p.name or "outcome" in p.name.lower() or "pageview" in p.name.lower():
        raise Refused(f"{p}: outcome / guarded / pageview files are never opened by CB15")
    idx = next((i for i, x in enumerate(p.parts) if x in ID_READABLE), None)
    if idx is None:
        raise Refused(f"{p}: not an id-only readable frame file")
    root, rel = p.parts[idx], "/".join(p.parts[idx + 1:])
    if rel not in ID_READABLE[root]:
        raise Refused(f"{p}: not an id-only readable frame file of {root} {ID_READABLE[root]}")
    refuse_path(p, allow=(root,))
    return p


def id_source_path(rel: str, hist_root: Path, research_root: Path | None = None) -> Path:
    root = rel.split("/", 1)[0]
    base = (Path(research_root) if research_root is not None else Path(hist_root).parent) if root in ID_RESEARCH_ROOTS else Path(hist_root)
    return base / rel


def read_id_columns(path: Path) -> dict[str, set[str]]:
    """Id columns of one id-readable frame file; every other column is dropped at read."""
    p = guard_id_file(path)
    out: dict[str, set[str]] = {}
    csv.field_size_limit(10**9)
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        keep = [c for c in (rdr.fieldnames or []) if c in ID_COLUMNS]
        for row in rdr:
            for c in keep:
                if row.get(c):
                    out.setdefault(c, set()).add(str(row[c]))
    return out


def require_output_root(path: Path) -> Path:
    """Data jobs write only under creative_batch15 / h15_elect_live / h15_birth / h15_birth_live."""
    refuse_path(Path(path))
    if not any(p in ALLOWED_OUTPUT_ROOT_PARTS for p in Path(path).parts):
        raise Refused(f"CB15 writes only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return Path(path)


def assert_clean_columns(columns: Iterable[str]) -> None:
    bad = [c for c in columns if c in FORBIDDEN_OUTPUT_COLUMNS or str(c).startswith("wallet")]
    if bad:
        raise Refused(f"forbidden columns in an output: {bad}")


def strip_forbidden(rec: dict) -> dict:
    """A copy of ``rec`` without any forbidden parse field (outcome fields, side, wallets, hashes): the outcome guard applied at parse."""
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
    """Exit 75 ("pending", never "not run") if data-dumps + the job's cap > ``cap_gb`` OR root free disk - the job's cap < ``free_min_gb``. Never used by the E collector inside
    its window (no exit-75 path on the night, round 1 item 8)."""
    return c10.require_disk(data_dumps, cap_gb, allowance_bytes, free_path=free_path, free_min_gb=free_min_gb, free_fn=free_fn)


def wait_or_idle(rdir: Path, why: str, now: float) -> dict:
    return cm.idle(Path(rdir), why, now)


FREEZE_PIN_KEYS = {"rules": "rules_sha256", "common": "common_rules_sha256"}
E_FREEZE_PINS = ("sign_table_sha256", "poll_close_sha256", "party_map_sha256", "cross_table_sha256", "source_manifest_sha256", "race_map_sha256", "disk_cap_gb")


def require_freeze(part: str, spec_path: Path | None = None, *, require_committed: bool = True, rules_shas: dict[str, str] | None = None, pins: dict[str, Any] | None = None) -> dict:
    """Analysis and live jobs refuse before the CB15 declaration is committed (``model_specs/cb15_v1.json``). One entry per family part (E, P). The entry must PIN the code the job
    has just verified: ``rules_sha256`` equals the part's currently verified sha and ``common_rules_sha256`` the common part's; part E also pins every GE0 file sha256, the race map
    sha256 and the collector disk cap (``pins``; ``freeze-part`` prints exactly these). A freeze that pins other code or other files is refused. Returns the entry (with its sha256)."""
    if part not in FREEZE_PARTS:
        raise Refused(f"unknown freeze part {part!r}")
    if not rules_shas or not rules_shas.get(part) or not rules_shas.get("common"):
        raise Refused(f"require_freeze({part}) needs the currently verified rules shas of part {part} and of common")
    p = Path(spec_path or (Path(__file__).resolve().parent / "model_specs" / "cb15_v1.json"))
    if not p.exists():
        raise Refused(f"CB15 freeze spec {p} not found: the jobs refuse before the CB15 part-{part} freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB15 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"CB15 freeze spec {p} unreadable") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get(part), dict):
        raise Refused(f"CB15 freeze spec {p} has no {part!r} part")
    entry = doc[part]
    need: dict[str, Any] = {FREEZE_PIN_KEYS["rules"]: rules_shas[part], FREEZE_PIN_KEYS["common"]: rules_shas["common"], **(pins or {})}
    for k, want in need.items():
        if entry.get(k) != want:
            raise Refused(f"CB15 freeze entry {part!r} pins {k} {str(entry.get(k))[:12]!r}, but the verified code / file is {str(want)[:12]!r}: the freeze does not cover it; refusing")
    if part == "E":
        missing = [k for k in E_FREEZE_PINS if k not in entry]
        if missing:
            raise Refused(f"CB15 freeze entry E lacks {missing}: part E freezes with every GE0 file, the race map and the collector cap")
    return {**entry, "entry_sha256": hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()}


# ---- stalls, manifests, results, terminal records ---------------------------------------------------------------------------------------------


def stall_of(rdir: Path) -> dict | None:
    return c9.stall_of(Path(rdir))


def write_stall(rdir: Path, status: str, reason: str, label: str | None = None) -> dict:
    return c9.write_stall(Path(rdir), status, reason, label)


def manifest_complete(rdir: Path, statuses: tuple[str, ...]) -> dict | None:
    return c12.manifest_complete(rdir, statuses)


def require_complete(rdir: Path, statuses: tuple[str, ...], label: str) -> dict:
    return c12.require_complete(rdir, statuses, label)


def verify_fetch(rdir: Path, statuses: tuple[str, ...], label: str) -> dict:
    return c12.verify_fetch(rdir, statuses, label)


def write_results_once(path: Path, doc: dict) -> str:
    return c9.write_results_once(Path(path), doc)


def write_dir_manifest(rdir: Path, status: str, files: Iterable[Path], extra: dict | None = None, *, complete: bool = True) -> dict:
    """Manifest of a job directory: ``status``, ``complete`` and the sha256 of every output file (relative paths)."""
    from . import history_backfill as hb  # noqa: PLC0415

    rdir = Path(rdir)
    doc = {"status": status, "complete": bool(complete), "stopped": None, "written_utc": cm.iso(time.time()), "git_commit": hb._git_commit(),
           "file_sha256": {Path(f).relative_to(rdir).as_posix(): sha256_file(Path(f)) for f in files}, **(extra or {})}
    cm.write_json_atomic(rdir / "manifest.json", doc)
    return doc


def terminal_path(root: Path, family: str) -> Path:
    if family not in FAMILY_TESTS:
        raise Refused(f"unknown CB15 family {family!r}")
    return Path(root) / TERMINAL_NAME.format(family=family)


def read_terminal(root: Path, family: str) -> dict | None:
    p = terminal_path(root, family)
    return json.loads(p.read_text()) if p.exists() else None


def record_terminal(root: Path, family: str, label: str, reason: str, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """A failed smoke, gate, identifiability, calendar deadline or stall makes the family TERMINAL (section 2.5): ONE write-once record ``terminal_<family>.json`` and, at that moment,
    the family's counted lines (each test p = 1). A second call returns the record and counts nothing. Downstream jobs read the record and end with exit 0 (never an endless exit 75)."""
    p = terminal_path(require_output_root(Path(root)), family)
    if p.exists():
        return {**json.loads(p.read_text()), "newly_counted": False}
    doc = {"family": family, "label": label, "reason": str(reason)[:300], "tests": list(FAMILY_TESTS[family]), "counted": True, "status": TERMINAL_STATUS, "written_utc": cm.iso(time.time())}
    cm.write_once_json(p, doc)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    log_family(family, {t: {"p": 1.0, "testable": False, "advance": False, "verdict": label} for t in FAMILY_TESTS[family]}, trials_path=trials_path, results_sha256=sha, role=role)
    return {**doc, "newly_counted": True}


def jsonl_append(path: Path, rec: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True, default=float) + "\n")


def jsonl_iter(path: Path) -> Iterator[dict]:
    p = Path(path)
    if not p.is_file():
        return
    opener = gzip.open if p.name.endswith(".gz") else open
    with opener(p, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue  # a torn tail line (a killed writer) is skipped, never repaired into data
            if isinstance(rec, dict):
                yield rec


# ---- statistics helpers ------------------------------------------------------------------------------------------------------------------------


def holm(pvals: dict[str, float], alpha: float) -> dict:
    """STRICT Holm (reject iff p < alpha / (m - i) at every step so far), as CB12-CB14."""
    return c12.holm(pvals, alpha)


def stage1_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA, family: tuple[str, ...] = STAGE1_HOLM_FAMILY) -> dict:
    """The Stage-1 step-down at one-sided ``alpha`` over the FIXED four tests (k1 = 4); a test not run / not testable / pending enters with p = 1. Holm's first step is alpha / 4 =
    0.0125, so any p < 0.01 passes it: the step never withdraws an advance."""
    extra = [k for k in pvals if k not in family]
    if extra:
        raise Refused(f"batch-Holm: {extra} are not in the fixed Stage-1 family {family}")
    full = {k: (1.0 if pvals.get(k) is None else float(pvals[k])) for k in family}
    return {"k": len(family), "alpha": alpha, "tests": holm(full, alpha), "not_run_as_p1": [k for k in family if pvals.get(k) is None]}


def e_judged(p: float | None, checks_ok: bool) -> bool:
    """E is judged when it runs (round 1 item 7): advance iff every binding check holds and one-sided p < min(0.01, alpha / k1) = 0.01, STRICT. Never withdrawn."""
    return bool(checks_ok and p is not None and p < E_JUDGE_ALPHA)


def stage1_advance(p: float | None, checks_ok: bool, final_holm_reject: bool = False) -> bool:
    """Stage-1 advance: every binding check, one-sided p < 0.01 (strict) and the batch Holm. Since Holm's first step is 0.0125 > 0.01, a p < 0.01 always passes it; the final Holm
    can only add passes (``final_holm_reject`` with p < 0.01), never withdraw one."""
    return bool(checks_ok and p is not None and p < GATE_P and (final_holm_reject or p < STAGE_ALPHA / BATCH_HOLM_K1))


def stage2_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    full = {k: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


STAGE2_NAMES = {"P1": "P1-rep", "P2": "P2-rep"}


def stage2_final(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    """The final CB15 Stage-2 step: ONE strict Holm over every triggered Stage-2 test (P1-rep, P2-rep; a triggered test that could not run enters with p = 1). Applied once, after
    every triggered test is final; it can only ADD passes to the early alpha / 2 decisions."""
    extra = [k for k in pvals if k not in STAGE2_NAMES]
    if extra:
        raise Refused(f"stage-2 final Holm: {extra} are not CB15 Stage-2 tests {tuple(STAGE2_NAMES)}")
    full = {STAGE2_NAMES[k]: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


def early_stage2_ok(p: float | None) -> bool:
    """A rep that finishes before k2 is known is judged against alpha / 2 (strict ``<``; never withdrawn by the later full Holm)."""
    return p is not None and bool(p < EARLY_ALPHA2)


def stage2_pass(checks_ok: bool, p: float | None, final_holm_reject: bool = False) -> bool:
    """Stage-2 rule: ``checks_ok and (p < alpha / 2 early or the final Holm rejects)``; the final Holm can add passes."""
    return bool(checks_ok and (early_stage2_ok(p) or final_holm_reject))


def mde(se: float, mult: float = MDE_MULT, inflate: float = MDE_INFLATE) -> float:
    """``3.16 x 1.2 x SE`` (z_0.99 + z_0.80, inflated 20%)."""
    return float(mult * inflate * se) if math.isfinite(se) else math.nan


def cluster_se_mean(v, cl) -> float:
    return c12.cluster_se_mean(v, cl)


def max_se_over_ways(v, ways: dict[str, Any]) -> float:
    ses = [cluster_se_mean(v, cl) for cl in ways.values()]
    ses = [s for s in ses if math.isfinite(s)]
    return float(max(ses)) if ses else math.nan


def placebo_advance_rate(draw_ps: list[float | None], gate_p: float = GATE_P) -> dict:
    return c10.placebo_advance_rate(draw_ps, gate_p)


def top_k_drop_mask(v, cl, k: int = TOP_DROP) -> np.ndarray:
    return c9.top_k_drop_mask(v, cl, k)


def cluster_p(v, clusters: dict[str, Any], *, min_units: int = 2, min_first_clusters: int = 1, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None,
              estimator: Callable[[np.ndarray], float] | None = None, sign: float = 1.0) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared cluster ways under the CB10 small-G rule, per way: G >= 30 CR1; 15 <= G < 30 CR2 + t(G - 1) with the Webb wild
    bootstrap; G < 15 the way LEAVES the max and its leave-one-cluster-out sign rule binds (``small_g_rules_hold``). A way with too few clusters never makes the whole test untestable
    by itself; testable needs ``min_units`` units, ``min_first_clusters`` clusters in the first way and at least one way in the max."""
    from . import cb2_weather as w  # noqa: PLC0415

    v = np.asarray(v, float)
    if len(v) < 2:
        return {"n": int(len(v)), "mean": float(v.mean()) if len(v) else math.nan, "testable": False, "p": 1.0, "ways": {}, "small_g_rules_hold": False}
    est = estimator or (lambda keep: float(v[keep].mean()) if keep.any() else math.nan)
    ways: dict[str, dict] = {}
    in_max: list[float] = []
    rules_hold = True
    for name, cl in clusters.items():
        c = np.asarray(cl).astype(str)
        G = len(set(c.tolist()))
        if G >= G_CR2:
            r = w.small_g_pvalue(v, c, sign=1, n_wild=n_wild, seed=seed, alpha=alpha)
            ways[name] = {"G": int(r["G"]), "p": float(r["p"]), "method": r["method"], "in_max": True}
            in_max.append(float(r["p"]))
        else:
            loo = c10.leave_one_out_sign(c, est, sign)
            ways[name] = {"G": int(G), "p": None, "method": "leave_one_cluster_out_sign (G < 15)", "in_max": False, "leave_one_out": loo}
            rules_hold = rules_hold and bool(loo.get("holds"))
    first = next(iter(ways.values()), None)
    testable = bool(len(v) >= min_units and first is not None and first["G"] >= min_first_clusters and in_max)
    p = max(in_max) if testable else 1.0
    return {"n": int(len(v)), "mean": float(v.mean()), "testable": testable, "p": float(p), "ways": ways, "small_g_rules_hold": bool(rules_hold)}


def p_pass(r: dict | None, alpha: float) -> bool:
    """The p part of an advance / binding check: testable, every small-G leave-one-cluster-out sign rule holds, and one-sided p < ``alpha`` (strict)."""
    return bool(r and r.get("testable") and r.get("small_g_rules_hold", True) and r.get("p") is not None and r["p"] < alpha)


def wls_coef_pseudo(y, X, w, j: int) -> tuple[np.ndarray, float]:
    """(pseudo-values, coefficient) of regressor ``j`` in the WLS of ``y`` on ``X`` (intercept added) with weights ``w`` (Frisch-Waugh); mean(v) = b_j and the cluster sandwich of b_j
    is the clustered variance of v."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    n = len(y)
    wt = np.ones(n) if w is None else np.asarray(w, float)
    if n < X.shape[1] + 2 or wt.sum() <= 0:
        return np.full(n, math.nan), math.nan
    A = np.column_stack([np.ones(n), X])
    sw = np.sqrt(wt)
    beta, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    e = y - A @ beta
    jj = j + 1
    others = [k for k in range(A.shape[1]) if k != jj]
    g, *_ = np.linalg.lstsq(A[:, others] * sw[:, None], A[:, jj] * sw, rcond=None)
    r = A[:, jj] - A[:, others] @ g
    srr = float((wt * r * r).sum())
    if srr <= 0:
        return np.full(n, math.nan), math.nan
    b = float(beta[jj])
    return b + n * wt * r * e / srr, b


def sign_ok(est, ref) -> bool:
    return bool(est is not None and ref is not None and math.isfinite(est) and math.isfinite(ref) and est != 0 and np.sign(est) == np.sign(ref))


# ---- the within-stratum state-label permutation (E; section 2.3) ------------------------------------------------------------------------------------


def stratum_weights(labels, strata) -> dict:
    """Per stratum: ``n_plus``, ``n_minus``, identified (both signs present), ``m_h = n+ n- / (n+ + n-)``; ``w_h = m_h / sum m_h`` over identified strata (round 1 item 1, the
    inverse-variance weight of a two-group contrast). Labels are +1 / -1; a 0 label is not a state of E."""
    lab = np.asarray(labels, int)
    st = np.asarray(strata).astype(str)
    out: dict[str, dict] = {}
    for h in sorted(set(st.tolist())):
        m = st == h
        npos, nneg = int((lab[m] == 1).sum()), int((lab[m] == -1).sum())
        ident = npos >= 1 and nneg >= 1
        out[h] = {"n_plus": npos, "n_minus": nneg, "identified": bool(ident), "m_h": (npos * nneg / (npos + nneg)) if ident else 0.0}
    tot = sum(v["m_h"] for v in out.values())
    for v in out.values():
        v["w_h"] = (v["m_h"] / tot) if tot > 0 else 0.0
    return out


def stratified_balanced(v_plus, v_minus, labels, strata) -> float:
    """``T = sum_h w_h (1/2 mean_{s=+1,h} v_plus + 1/2 mean_{s=-1,h} v_minus)`` over identified strata (both signs present). For E1, ``v_plus = d_g`` and ``v_minus = -d_g`` give
    ``sum_h w_h (1/2 mean_+ d - 1/2 mean_- d)``; for E2 ``v_plus`` / ``v_minus`` are the state's net when the predicted side is D / R. NaN when no stratum is identified."""
    vp, vm = np.asarray(v_plus, float), np.asarray(v_minus, float)
    lab = np.asarray(labels, int)
    st = np.asarray(strata).astype(str)
    W = stratum_weights(lab, st)
    tot = 0.0
    any_ident = False
    for h, d in W.items():
        if not d["identified"]:
            continue
        any_ident = True
        m = st == h
        tot += d["w_h"] * (0.5 * float(vp[m & (lab == 1)].mean()) + 0.5 * float(vm[m & (lab == -1)].mean()))
    return float(tot) if any_ident else math.nan


def stratified_sign_share(v_plus, v_minus, labels, strata) -> float:
    """The stratified balanced share of states whose value has the predicted sign: ``sum_h w_h (1/2 share_{+,h}(v_plus > 0) + 1/2 share_{-,h}(v_minus > 0))``."""
    vp, vm = np.asarray(v_plus, float), np.asarray(v_minus, float)
    return stratified_balanced((vp > 0).astype(float), (vm > 0).astype(float), labels, strata)


def permute_within_strata(labels, strata, rng: np.random.Generator) -> np.ndarray:
    """One draw: the sign labels permuted among each stratum's states (group sizes per stratum fixed). A label never moves across strata."""
    lab = np.asarray(labels, int).copy()
    st = np.asarray(strata).astype(str)
    for h in sorted(set(st.tolist())):
        idx = np.flatnonzero(st == h)
        lab[idx] = lab[idx][rng.permutation(len(idx))]
    return lab


def perm_p_within_strata(v_plus, v_minus, labels, strata, *, draws: int = PERM_DRAWS, seed: int = SEED_PERM) -> dict:
    """One-sided p of T > 0 by the state-label permutation WITHIN closing-hour strata: ``p = (1 + #{T* >= T}) / (draws + 1)``. Only identified strata enter (an unidentified
    stratum carries weight 0 under every draw because its group sizes are fixed)."""
    lab = np.asarray(labels, int)
    st = np.asarray(strata).astype(str)
    T = stratified_balanced(v_plus, v_minus, lab, st)
    if not math.isfinite(T):
        return {"T": math.nan, "p": 1.0, "draws": 0, "testable": False}
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(int(draws)):
        t = stratified_balanced(v_plus, v_minus, permute_within_strata(lab, st, rng), st)
        ge += int(t >= T - 1e-15)
    return {"T": float(T), "p": float((1 + ge) / (draws + 1)), "draws": int(draws), "testable": True}


# ---- trials ------------------------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb15_descriptive`` line (EXCLUDE, counts 0): smoke, GE0, audit, census, gates, strata, tiers, logs, the CH125 withdrawal."""
    rec = {"kind": "cb15_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_15:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_family(family: str, results: dict[str, dict], *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST, results_sha256: str = "",
               placebos: dict[str, dict] | None = None, n_triggered: int | None = None) -> None:
    """Per-test ``cb15_test`` / ``cb15_replication`` lines (EXCLUDE, ``n_tests`` 0), placebo lines (0) and ONE count line ``ml_explain`` (source ``creative_batch_15:<family>[:rep]``)
    whose ``n_tests`` is the family's number of tests (Stage 1: E 2, P 2; a test behind a failed gate counted with p = 1) or the reps actually triggered (Stage 2)."""
    if family not in FAMILY_TESTS:
        raise Refused(f"unknown CB15 count family {family!r}")
    allowed = FAMILY_REP_TESTS[family] if replication else FAMILY_TESTS[family]
    bad = [t for t in results if t not in allowed]
    if bad or (replication and not allowed):
        raise Refused(f"{bad or list(results)} are not CB15-{family} {'rep ' if replication else ''}tests {allowed}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb15_replication" if replication else "cb15_test"
    for tid, result in results.items():
        p = result.get("p", 1.0)
        if not result.get("testable", True) or p is None:
            p = 1.0
        base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_15", "hypothesis": tid, "family": family, "results_sha256": results_sha256}
        provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                                 "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
        pl = (placebos or {}).get(tid)
        if pl:
            provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": pl.get("note", "placebo"), "advance_rate": pl.get("advance_rate"),
                                     "n_draws": pl.get("n_draws"), "n_tests": 0}, tp)
    n = len(results) if n_triggered is None else int(n_triggered)
    count_role = role if role in provenance.EVIDENCE_ROLES else EVIDENCE_ROLE_DEV  # the count line is bookkeeping; the validated roles do not include "prospective"
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": count_role, "source": f"creative_batch_15:{family}{':rep' if replication else ''}",
                             "dataset": "creative_batch_15", "n_tests": n, "n_tests_by_family": {f"cb15_{family}{'_rep' if replication else ''}": n},
                             "hypotheses": sorted(results), "replication": bool(replication), "advanced": sorted(t for t, r in results.items() if r.get("advance")),
                             "results_sha256": results_sha256, "note": "CB15 count line: the family's tests (a test behind a failed gate is still counted, p = 1)"}, tp)


# ---- source-attributed exclusion keys (q0340; section 1.3) ------------------------------------------------------------------------------------


def frame_ids(hist_root: Path, research_root: Path | None = None) -> tuple[dict[str, set[str]], list[str]]:
    """Market ids per id-readable frame root (field restricted, ``ID_READABLE`` only); a file that does not exist yet is 'absent at q0340' (recorded, re-read by the census)."""
    found: dict[str, set[str]] = {}
    absent: list[str] = []
    for root, files in ID_READABLE.items():
        for name in files:
            p = id_source_path(f"{root}/{name}", hist_root, research_root)
            if p.is_file():
                found.setdefault(root, set()).update(read_id_columns(p).get("market_id", set()))
            else:
                absent.append(f"{root}/{name}")
    return found, absent


def attribute_sources(base_ids: set[str], c1_ids: set[str], frames: dict[str, set[str]], seal_ids: dict[str, set[str]]) -> dict[str, set[str]]:
    """Per market id, the set of sources that carry it (section 1.3: each key carries its source(s)). The inherited CB14 q0302 file has no attribution, so the union is rebuilt from
    its readable sources: an id read directly from the C1 file, a frame or a seal copy carries those labels; a base id found in no direct source carries ``BASE_SOURCE`` (an
    unattributed inherited source, never C1-only). A base id that IS a C1 id but found in no other direct source carries ``c1`` only (the C1 set entered the chain through CB12
    q0241's C1 union; declared, the count is reported)."""
    out: dict[str, set[str]] = {}
    for i in c1_ids:
        out.setdefault(i, set()).add(C1_SOURCE)
    for root, ids in frames.items():
        for i in ids:
            out.setdefault(i, set()).add(f"frame:{root}")
    for name, ids in seal_ids.items():
        for i in ids:
            out.setdefault(i, set()).add(f"seal:{name}")
    for i in base_ids:
        if i not in out:
            out[i] = {BASE_SOURCE}
    return out


def key_sources(rows: list[dict], market_sources: dict[str, set[str]]) -> dict[str, dict[str, set[str]]]:
    """Per key type (``market``, ``event``, ``neg_risk_market``, ``series``), the union of the sources of every market that carries the key: an event shared by a C1 market and a
    CB11-P market carries both sources."""
    out: dict[str, dict[str, set[str]]] = {"market": {}, "event": {}, "neg_risk_market": {}, "series": {}}
    for r in rows:
        src = market_sources.get(str(r["market_id"]), {BASE_SOURCE})
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


def drop_reason(unit: dict, ksrc: dict[str, dict[str, set[str]]], family: str) -> str:
    """The per-family key rule (section 1.3, declared deviations accepted in round 1 item 11). ``unit`` carries ``market_id`` and optional ``event_ids`` / ``neg_risk_market_id`` /
    ``series_ids``. P drops a unit if ANY of its keys has a source other than C1 (a key whose only source is C1 is kept; C1 + any other source is dropped). E keeps every unit
    (calendar disjointness); its robustness drops a unit with any key of any source (the return value is then the key-overlap reason). '' = no key matched."""
    if family not in FAMILY_PARTS:
        raise Refused(f"unknown family {family!r}")
    keys = [("market", str(unit.get("market_id") or ""))]
    keys += [("event", e) for e in str(unit.get("event_ids") or unit.get("event_id") or "").split(";") if e]
    if unit.get("neg_risk_market_id"):
        keys.append(("neg_risk_market", str(unit["neg_risk_market_id"])))
    keys += [("series", s) for s in str(unit.get("series_ids") or unit.get("series_id") or "").split(";") if s]
    for kind, k in keys:
        src = ksrc.get(kind, {}).get(k)
        if not src:
            continue
        if family == "P" and src == {C1_SOURCE}:
            continue
        return f"{kind}:{'+'.join(sorted(src))}"
    return ""


def read_keys_with_sources(path: Path) -> tuple[list[dict], dict]:
    """The CB15 key file (``KEY_COLUMNS``) as rows with a ``sources`` set, plus its sha256. Refused if the file lacks the ``sources`` column (no attribution, no CB15 key rule)."""
    p = Path(path)
    rows = []
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        rdr = csv.DictReader(fh)
        if "sources" not in (rdr.fieldnames or []):
            raise Refused(f"{p}: no per-key source attribution; the CB15 key rule cannot be applied")
        for r in rdr:
            rows.append({**r, "sources": set(x for x in str(r.get("sources") or "").split(";") if x)})
    return rows, {"sha256": sha256_file(p), "n_rows": len(rows)}


def ksrc_of(rows: list[dict]) -> dict[str, dict[str, set[str]]]:
    return key_sources(rows, {str(r["market_id"]): set(r["sources"]) for r in rows})


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, hist_root: Path, base_path: Path, base_sha256: str, matches_path: Path, seals_dir: Path | None = None,
                   is_committed=None, rps: float = 2.0, disk_cap: int = int(KEYS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, now: float | None = None, sleep=None,
                   live_check=None, should_stop=None, wall_clock=None, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                   data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0340. CB14 q0302's key file (sha256 pin MANDATORY) plus, by closed-first Gamma id lookup (<= 50 per request, resumable), every market id of the C1 file (``matches.json``,
    ids only), of every id-readable frame (a missing one is 'absent at q0340') and of every committed seal copy. Every row carries its source(s) (``sources``). More than 2% of
    ALL ids without metadata -> ``disjointness_unverified`` (the affected family is "not testable (disjointness)", counted). CB16 must add CB15's frame ids."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    out_root, seals_dir = require_output_root(Path(out_root)), Path(seals_dir or cm.SEALS_DIR)
    base_path = Path(base_path)
    if not base_sha256 or base_sha256 == PIN_UNSET:
        raise Refused(f"the sha256 pin of the CB14 key file (--base-sha256) is unset ({PIN_UNSET}); the coordinator fills it in the queue draft from `sha256sum` on the host")
    refuse_path(base_path, allow=("creative_batch14",))
    got = sha256_file(base_path) if base_path.exists() else None
    if got != base_sha256:
        raise Refused(f"base key file {base_path} sha256 {got} != pinned {base_sha256}")
    refuse_path(Path(matches_path), allow=("cross_venue",))
    if Path(matches_path).name != "matches.json":
        raise Refused(f"{matches_path}: the C1 id source is matches.json")
    base_ids = c12.read_id_set(base_path)
    c1_ids = c12.c1_market_ids(Path(matches_path))
    require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    frames, absent = frame_ids(Path(hist_root))
    seal_all, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, is_committed=is_committed, own=())
    seal_ids = {"seal_copies": set(seal_all)}
    msrc = attribute_sources(base_ids, c1_ids, frames, seal_ids)
    lookup = set(msrc) - base_ids
    fr = cm.open_run(out_root, KEYS_RUN, transport, allowed_run_id=KEYS_RUN, kind="cb15_exclusion_keys", label="CB15 exclusion keys",
                     params={"base_keys_sha256": base_sha256, "n_base_ids": len(base_ids), "n_c1_ids": len(c1_ids), "n_lookup_ids": len(lookup), "frames": {k: len(v) for k, v in frames.items()},
                             "sets_absent_at_q0340": absent, "seal_copies_used": used, "seal_copies_skipped": skipped, "evidence_role": EVIDENCE_ROLE_HIST},
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
    for path in (base_path, fr.rdir / "exclusion_keys.csv.gz"):
        with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
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
    c1_only_via_base = sum(1 for i in c1_ids & base_ids if msrc.get(i) == {C1_SOURCE})
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": UNVERIFIED if share > MAX_UNVERIFIED_KEY_SHARE else "verified", "base_keys_sha256": base_sha256, "new": rep_new, "frames": {k: len(v) for k, v in frames.items()},
           "sets_absent_at_q0340": absent, "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "keys_sha256": sha256_file(keys_out),
           "attribution": {"rebuilt_from_readable_sources": True, "unattributed_base_ids": sum(1 for s in msrc.values() if s == {BASE_SOURCE}), "c1_only_ids": sum(1 for s in msrc.values() if s == {C1_SOURCE}),
                           "c1_ids_in_base_attributed_c1_only": c1_only_via_base,
                           "rule": "a base id in no direct source is 'base:cb14_q0302' (never C1-only); a C1 id in no other readable source is C1-only (declared)"},
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
    """The functions hashed for ``part``: the common ones, plus (family parts) that family's own module(s) only."""
    funcs = list(common_funcs())
    if part == "common":
        funcs += c12.module_funcs(importlib.import_module(".cb15_smoke", __package__))
    else:
        for mod in family_modules(part):
            funcs += c12.module_funcs(mod)
    seen: set[int] = set()
    return [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]


def shared_helper_sources() -> dict[str, str]:
    """sha256 of the source of every shared helper the CB15 rules call (``SHARED_HELPERS``); a constant tuple is hashed by its repr."""
    from . import cb2_weather as cw  # noqa: PLC0415  (small_g_pvalue: the p engine of cluster_p)
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415

    mods = {"c12": c12, "c10": c10, "c9": c9, "cw": cw, "c6": c6, "bk": bk, "cm": cm}
    out = {}
    for m, n in SHARED_HELPERS:
        if n == "KEY_COLUMNS_SRC":
            out[f"{m}.KEY_COLUMNS"] = hashlib.sha256(repr(tuple(c6.KEY_COLUMNS)).encode()).hexdigest()
            continue
        out[f"{m}.{n}"] = hashlib.sha256(inspect.getsource(getattr(mods[m], n)).encode()).hexdigest()
    return out


def common_declared() -> dict:
    return {"refused_roots": list(EXTRA_REFUSED_ROOTS), "always_refused": list(ALWAYS_REFUSED_ROOTS), "id_readable": {k: list(v) for k, v in ID_READABLE.items()},
            "output_roots": list(ALLOWED_OUTPUT_ROOT_PARTS), "seeds": {"boot": SEED_BOOT, "perm": SEED_PERM, "placebo": PLACEBO_SEEDS, "placebo_range": list(PLACEBO_SEED_RANGE),
                                                                         "paired_boot": SEED_PAIRED_BOOT},
            "bootstrap": {"n_boot": N_BOOT, "n_wild": N_WILD, "perm_draws": PERM_DRAWS,
                          "small_g": "G>=30 CR1; 15<=G<30 CR2 t(G-1) + Webb wild; G<15 the way leaves the max and its leave-one-cluster-out sign rule binds (CB10 2.3, A-C1)"},
            "holm": {"k1": BATCH_HOLM_K1, "alpha": STAGE_ALPHA, "gate_p": GATE_P, "e_judge_alpha": E_JUDGE_ALPHA, "stage2_k_max": STAGE2_K_MAX, "stage2_early_alpha": EARLY_ALPHA2, "strict": True,
                     "stage2_rule": "checks_ok and (p < alpha/2 early or the final Stage-2 Holm rejects)"},
            "disk": {"data_dumps_cap_gb": DATA_DUMPS_CAP_GB, "free_min_gb": FREE_DISK_MIN_GB, "output_cap_gb": CB15_OUTPUT_CAP_GB},
            "field_whitelists": {"forbidden_output_columns": list(FORBIDDEN_OUTPUT_COLUMNS), "forbidden_parse_fields": list(FORBIDDEN_PARSE_FIELDS)},
            "key_rule": {"P": "drop a unit if any key has a source other than C1 (a C1-only key is kept)", "E": "calendar disjointness; keys as binding robustness (any source drops)",
                         "sources": "rebuilt from readable sources; unattributed inherited ids are never C1-only"},
            "costs": {"fee_floor": FEE_FLOOR, "w_star": W_STAR, "cost_robust_per_side": COST_ROBUST_PER_SIDE, "paper_size": PAPER_SIZE},
            "stop_rule": "3 CPU-hours per family; a job failing twice for the same non-transient reason stops; no re-screen of a failed CB15 test"}


def rules_part_doc(part: str) -> dict:
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    this = importlib.import_module(__name__)
    consts = {"cb15_common": c12.module_constants(this)}
    declared: dict[str, Any] = {}
    if part == "common":
        smoke = importlib.import_module(".cb15_smoke", __package__)
        consts["cb15_smoke"] = c12.module_constants(smoke)
        declared["smoke"] = smoke.declared()
        declared["common"] = common_declared()
    else:
        mods = family_modules(part)
        if not mods:
            return {"part": part, "part_declared": False, "rules_version": RULES_VERSION, "reason": f"family module {FAMILY_MODULES[part]} not present yet"}
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
            "wallet": {"read": False, "note": "no CB15 job reads or stores a wallet field, a transaction hash (aggregated in memory and discarded) or the Data API side field"},
            "shared_helper_sources_sha256": shared_helper_sources(),
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
    path = Path(path or (SEALS_DIR / "cb15_rules.json"))
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


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "E") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's. Only that part's modules are imported. Returns the part's ``rules_sha256``."""
    path = Path(path or (SEALS_DIR / "cb15_rules.json"))
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
