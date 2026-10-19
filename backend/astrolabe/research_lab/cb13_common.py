# ruff: noqa: E501
"""CB13 shared parts (docs/research_lab/CREATIVE_BATCH_13.md sections 1.2-1.4, 2.1-2.8, 5, 10).

Everything common to CB13-T and CB13-R lives here: the dates and the J4-R pin (the T HOLDOUT window STARTS at the pin's ``t_j4r_end``), refusal lists (outputs AND inputs;
``surprise_live``, ``cross_venue_live``, ``e0xx``, ``trade_samples`` and the monitor's alert / score / outcome / wallet files are never opened), the field-whitelist readers for
monitor prints and capture rows (``side``, ``wallet_*``, every ``chg_*`` and the other forbidden fields are never parsed into any row), the disk guards (data-dumps cap 40 and
root free disk, exit 75 = "pending"), the CB3 hold on the T HOLDOUT mark-outs, the archive-restore hook, the guarded outcome files, the fixed-k1 (= 3) Holm helpers (stage-2
early rule at alpha / 5), the clustered-inference helpers (pseudo-value estimators, the max over cluster ways with the CB10 small-G rule, leave-one-group-out), the trial-line
helpers (kinds ``cb13_test`` / ``cb13_replication`` / ``cb13_descriptive``) and the per-part rules hashing.

**Per-part rules hashing (the CB11 whole-document-hash pitfall).** ``seals/cb13_rules.json`` holds one sha256 per part: ``common``, ``LABELLER``, ``T``, ``R``. A family part
hashes ONLY (a) the common rule functions and constants of this module, and (b) the functions and UPPER_CASE constants of that family's own module (``FAMILY_MODULES``).
Verifying part T imports ``cb13_t`` and nothing else (never ``cb13_r``, never ``cb13_label``); the T jobs verify ``LABELLER`` and ``T`` separately and the T freeze entry pins
both shas. Rule: nothing family-specific may be added to this module after the first CB13 job (put it in the family module).
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
RULES_VERSION = "cb13-rules-v1"
PARTS = ("common", "LABELLER", "T", "R")
FAMILY_PARTS = ("LABELLER", "T", "R")
FREEZE_PARTS = ("T", "R")
FAMILY_MODULES = {"LABELLER": ("cb13_label",), "T": ("cb13_t",), "R": ("cb13_r",)}
FAMILY_TESTS = {"T": ("T1", "T2"), "R": ("R1",)}
FAMILY_REP_TESTS = {"T": ("T1", "T2", "T3"), "R": ("R1", "R2")}
STAGE1_HOLM_FAMILY = ("T1", "T2", "R1")
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 3, fixed
STAGE_ALPHA = 0.05  # Stage 1 batch Holm and Stage 2 Holm, one-sided
STAGE2_K_MAX = 5  # T1-rep, T2-rep, T3, R1-rep, R2: the largest possible Stage-2 count
EARLY_ALPHA2 = STAGE_ALPHA / STAGE2_K_MAX  # a Stage-2 test that finishes before k2 is known is judged against alpha / 5 = 0.01
GATE_P = 0.01
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 1313
N_WILD = 9999
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
PLACEBO_SEEDS = {"T1_composition": 13101, "T2_signflip": 13102, "R1_signflip": 13103}
SEED_GL = (13121, 13122)
SEED_GRP = 13123
GRP_DRAWS = 500
MIN_UNITS = 100
MIN_CLUSTERS = 30
TOP_DROP = 5
AVAIL_MIN = 0.60
LOO_DAY_P = 0.05  # leave-one-day-out must keep p < 0.05 AND the sign (stricter than the A-C1 sign-only rule)
EVIDENCE_ROLE_HIST = "exploratory_historical"
EVIDENCE_ROLE_DEV = "exploratory_dev"
EVIDENCE_ROLE_PROSPECTIVE = "prospective"  # T Stage 2 per-test lines (design header); the ml_explain COUNT line keeps a role that provenance.EVIDENCE_ROLES validates
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
PIN_UNSET = "TODO-COORDINATOR"
T_SEAL = "2026-10-22T00:00:00Z"
CB13_SPORTS_IN_PRIMARY = False
SMOKE_VERSION = "cb13-smoke-v1"
DATA_DUMPS_CAP_GB = 40.0
FREE_DISK_MIN_GB = 4.5
HEARTBEAT_S = cm.HEARTBEAT_S
# dates (section 1.2; epochs derived below)
T_SCREEN = ("2026-10-12T00:00:00Z", "2026-10-16T00:00:00Z")  # fill venue time tau
T_SCREEN_CAPTURE_FROM = "2026-10-11T20:00:00Z"  # earliest capture start the SCREEN touches may use
T_HOLD_END = "2026-10-26T00:00:00Z"
T_HOLD_DEFAULT_START = "2026-10-21T00:00:00Z"  # = the J4-R pin's t_j4r_end while final is false; the live window follows the pin
T_SEAL_EARLIEST = "2026-10-26T08:00:00Z"
T13_HIST_END = "2026-10-01T00:00:00Z"
R_SCREEN_END = "2026-04-01T00:00:00Z"
R_HOLD_START = "2026-04-01T00:00:00Z"
R_FIRST_END = "2024-11-01T00:00:00Z"
J4R_PIN_NAME = "j4r_window.json"
CB3_FREEZE_NAME = "cb3_v1.json"
CB3_STOP_NAME = "cb3_stop.json"  # structured, committed stop record under seals/ (a ledger sentence that merely quotes the design never lifts the hold)
CB3_STOP_TOKEN = "CB3_STOPPED_WITHOUT_FREEZE"
# Output roots CB13 writes under, and input roots it never reads (section 1.1 last rows, 1.3)
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch13", "h13_touch", "h13_binance")
HOLDOUT_PART = "holdout"
HOLDOUT_PARTS = ("holdout", "t_holdout")
SCREEN_JOBS = ("screen-T", "screen-R", "gti-T")
REP_JOBS = ("rep-T", "rep-R")
GUARDED_NAMES = ("outcomes_guarded_screen.csv.gz", "outcomes_guarded_holdout.csv.gz")
SEAL_NAME_R = "holdout_SEAL.json"
SEAL_NAME_T = "t_holdout_SEAL.json"
COPY_NAME_R = "cb13_touch_holdout_SEAL.json"
COPY_NAME_T = "cb13_t_holdout_SEAL.json"
OWN_SEAL_COPIES = (COPY_NAME_R, COPY_NAME_T)
ACCESS_LOG = "ACCESS_LOG.jsonl"
DROPS_FILE = "drops.csv.gz"
EXTRA_REFUSED_ROOTS = ("creative_batch12", "creative_batch11", "creative_batch10", "creative_batch9", "creative_batch8", "creative_batch7", "creative_batch6", "creative_batch5", "creative_batch4",
                       "creative_batch3", "creative_batch2", "creative_batch1", "snapshots", "trade_samples", "live_trades", "book_sweeps", "surprise_live", "cross_venue_live", "cross_venue",
                       "forecasts", "flow_screen", "h9_flow", "h10_sign", "h10_dlad", "h10_brk", "h11_wprints", "h11_pol", "h11_attn", "h12_say", "h12_quake", "h12_prints",
                       "h12_quake_live", "h12_opt_live", "h1_first", "h2_main", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era", "h7_cb4_series",
                       "h8_tail", "h8_tail_b", "h8_text", "h8_geo", "cb3_followup", "cb6_followup")
ALWAYS_REFUSED_ROOTS = ("surprise_live", "cross_venue_live", "trade_samples", "forecasts", "flow_screen")
LIVE_ROOT_NAME = "cross_venue_live"
EXTRACT_ROOT_RE = r"^cb\d+_extract$"
EXPERIMENT_ROOT_RE = r"^e0\d\d$"
MONITOR_TRADES_RE = r"^trades-\d{8}\.jsonl$"
MONITOR_FORBIDDEN_FILES = ("alerts.jsonl", "outcomes.jsonl", "wallets.jsonl", "stats.jsonl", "state.json")
MONITOR_FORBIDDEN_RE = r"^scores-\d{8}\.jsonl$"
SNAPSHOT_FILES = ("rows.csv.gz", "rows_ext.csv.gz", "manifest.json")
# field whitelists (section 1.4). tx16 is read in memory only (transaction aggregation) and never written.
PRINT_FIELDS = ("ts", "condition_id", "token_id", "outcome_index", "price", "size", "cash", "title", "slug", "ctx_event_id", "ctx_market_id", "ctx_category", "ctx_fee_type")
PRINT_MEMORY_ONLY = ("tx16",)
FORBIDDEN_PRINT_FIELDS = ("side", "key", "recv_ts", "wallet_hash", "wallet", "proxyWallet", "ctx_chg_1h", "ctx_status")
CAPTURE_COLUMNS = ("capture_id", "capture_start_utc", "received_utc", "market_id", "condition_id", "event_id", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "end_date",
                   "clob_token_id_0", "neg_risk", "neg_risk_market_id")
FORBIDDEN_CAPTURE_COLUMNS = ("chg_1h", "chg_1d", "chg_1w", "last_trade_price", "volume24hr")
SIDECAR_COLUMNS = ("fee_type", "fee_category", "fees_enabled", "taker_base_fee", "fee_schedule", "series_slugs", "event_ids", "created_at", "order_price_min_tick_size", "rewards_min_size",
                   "rewards_max_spread", "clob_rewards", "accepting_orders")
FORBIDDEN_SIDECAR_COLUMNS = ("uma_resolution_statuses", "open_interest", "volume_num")
FORBIDDEN_OUTPUT_COLUMNS = ("side", "wallet", "wallet_hash", "proxyWallet", "tx16", "transactionHash", "chg_1h", "chg_1d", "chg_1w", "ctx_chg_1h", "uma_resolution_statuses", "outcome_prices",
                            "outcomePrices", "umaResolutionStatus", "closedTime")
CAPTURE_DIR_RE = r"^(\d{8}T\d{6}Z)_[0-9a-f]+$"
ID_COLUMNS = ("market_id", "event_id", "condition_id", "neg_risk_market_id", "negRiskMarketID", "series_id")
TS_COLUMNS = ("ts", "timestamp", "received_utc", "capture_start_utc", "fetch_utc", "fetched_utc", "recorded_utc", "start_epoch", "origin_ts", "t")
COLLECTOR_PASS_MINUTES = (31, 55)
TICK = 0.01
PRICE_CAP = 0.99
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
GAMMA_PAGE = 100
GAMMA_OFFSET_CAP = 2000
LOOKUP_PER_REQUEST = 50
NY = c12.NY
DATA_DUMPS = cm.DATA_DUMPS
HIST_ROOT = cm.HIST_ROOT
RESEARCH_ROOT = DATA_DUMPS / "research_lab"
CB13_DIR = RESEARCH_ROOT / "creative_batch13"
LIVE_TRADES_DIR = RESEARCH_ROOT / "live_trades"
SNAPSHOT_DIR = RESEARCH_ROOT / "snapshots"
SEALS_DIR = cm.SEALS_DIR
CB11_KEYS_DEFAULT = RESEARCH_ROOT / "creative_batch11" / "exclusion_keys.csv.gz"
SMOKE_T_DEFAULT = CB13_DIR / "smoke_T.json"
SMOKE_R_DEFAULT = CB13_DIR / "smoke_R.json"

RULES_MACHINERY = ("rules_part_doc", "rules_part_file_doc", "rules_file_doc", "write_rules", "verify_rules", "family_modules", "common_funcs", "part_funcs")


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


def block6(ts: float) -> int:
    """UTC 00 / 06 / 12 / 18 block index of an epoch (the cohort cadence)."""
    return int(ts // 21600)


def rank(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


def read_csv_gz(path: Path) -> Iterator[dict]:
    return c12.read_csv_gz(path)


def sha256_obj(obj) -> str:
    return cm.sha_obj(obj)


# ---- the J4-R pin and the windows --------------------------------------------------------------------------------------------------------------


def j4r_pin(path: Path | None = None, *, require_committed: bool = False) -> dict:
    """``{"start", "end", "final"}`` epochs from ``seals/j4r_window.json``. The END is the pin's raw ``t_j4r_end`` (the T HOLDOUT window starts there and follows the pin when it moves
    forward); ``start`` is ``t_j4r_start``. Fails closed on an unreadable pin."""
    p = Path(path) if path is not None else SEALS_DIR / J4R_PIN_NAME
    try:
        doc = json.loads(p.read_text())
        lo, hi = ep(doc["t_j4r_start"]), ep(doc["t_j4r_end"])
    except (OSError, ValueError, KeyError) as exc:
        raise Refused(f"cannot read the J4-R window pin {p}: {exc}") from exc
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"{p} is not committed (or differs from HEAD); the J4-R window pin must be committed")
    if hi < ep(doc.get("declared_end", doc["t_j4r_end"])):
        raise Refused("pinned t_j4r_end is before the declared end")
    return {"start": lo, "end": hi, "final": bool(doc.get("final", False))}


def in_j4r(t: float, pin: dict) -> bool:
    """True iff ``t`` lies in the J4-R window ``[start, end)`` (while ``final`` is false the end can only move forward: ``t >= end`` is then merely 'not yet known to be free')."""
    return pin["start"] <= float(t) < pin["end"]


def split_bounds(split: str, pin: dict) -> tuple[float, float]:
    """(lo, hi) of the fill-time window of a T split. SCREEN ends at the J4-R start; HOLDOUT starts at the J4-R end (the pin; it follows a moved end) and ends 2026-10-26T00Z."""
    if split == "screen":
        return ep(T_SCREEN[0]), min(ep(T_SCREEN[1]), pin["start"])
    if split == "holdout":
        return max(pin["end"], ep(T_HOLD_DEFAULT_START)), ep(T_HOLD_END)
    raise Refused(f"unknown split {split!r}")


def check_window(split: str, lo: float, hi: float, pin: dict) -> None:
    """A reader may only be asked for a window inside its split's bounds (and so never inside the J4-R window; both edges)."""
    blo, bhi = split_bounds(split, pin)
    if lo < blo or hi > bhi:
        raise Refused(f"window {iso(lo)}..{iso(hi)} lies outside the {split} bounds {iso(blo)}..{iso(bhi)} (J4-R window {iso(pin['start'])}..{iso(pin['end'])})")
    if lo < pin["end"] and hi > pin["start"]:
        raise Refused(f"window {iso(lo)}..{iso(hi)} overlaps the J4-R window; CB13 never reads it")


def capture_allowed(start_epoch: float, split: str, pin: dict) -> bool:
    """A touch or mark capture is usable iff its START lies in the split's capture range: SCREEN ``[T_SCREEN_CAPTURE_FROM, t_j4r_start)``; HOLDOUT ``[t_j4r_end, T_HOLD_END)``."""
    if in_j4r(start_epoch, pin):
        return False
    if split == "screen":
        return ep(T_SCREEN_CAPTURE_FROM) <= start_epoch < pin["start"]
    if split == "holdout":
        lo, hi = split_bounds("holdout", pin)
        return lo <= start_epoch < hi
    raise Refused(f"unknown split {split!r}")


def require_capture_allowed(start_epoch: float, split: str, pin: dict) -> None:
    if not capture_allowed(start_epoch, split, pin):
        raise Refused(f"capture starting {iso(start_epoch)} is outside the {split} capture range (J4-R window {iso(pin['start'])}..{iso(pin['end'])})")


# ---- the CB3 hold (section 1.2 T13_T_rep, round 1 item 3) --------------------------------------------------------------------------------------


def cb3_hold_lifted(spec_dir: Path | None = None, stop_path: Path | None = None, *, is_committed: Callable[[Path], bool] | None = None) -> dict:
    """The T HOLDOUT mark-outs wait for CB3's freeze commit (``model_specs/cb3_v1.json`` tracked and identical to HEAD) or for a STRUCTURED stop record: ``seals/cb3_stop.json`` (tracked,
    identical to HEAD) whose ``cb3_stop`` field equals ``CB3_STOP_TOKEN`` exactly (CB3 stopped / withdrawn WITHOUT a freeze). Free text in the ledger never lifts the hold. Returns the
    evidence; raises ``NotNow`` (exit 75, pending) while neither exists."""
    from . import cb1_history  # noqa: PLC0415

    sd = Path(spec_dir) if spec_dir is not None else Path(__file__).resolve().parent / "model_specs"
    spec = sd / CB3_FREEZE_NAME
    committed = is_committed or cb1_history.spec_committed
    if spec.exists() and committed(spec):
        return {"lifted_by": "cb3_freeze_commit", "path": str(spec)}
    sp = Path(stop_path) if stop_path is not None else SEALS_DIR / CB3_STOP_NAME
    if sp.exists() and committed(sp):
        try:
            doc = json.loads(sp.read_text())
        except ValueError:
            doc = None
        if isinstance(doc, dict) and doc.get("cb3_stop") == CB3_STOP_TOKEN:
            return {"lifted_by": "cb3_stop_record", "path": str(sp)}
    raise NotNow("CB3 hold: neither model_specs/cb3_v1.json (committed) nor a committed seals/cb3_stop.json stop record of CB3 exists; the T HOLDOUT mark-outs wait (pending)")


# ---- refusals ----------------------------------------------------------------------------------------------------------------------------------


def refused_names() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*c10.REFUSED_ROOTS, *c10.REFUSED_RUN_IDS, *EXTRA_REFUSED_ROOTS)))


def refuse_path(path: Path, *, allow: tuple[str, ...] = ()) -> Path:
    """Output AND input guard: refuse any path with a CB1-CB12 / sealed / live root among its parts, any ``cb<n>_extract`` or ``e0xx`` directory, and anything under
    ``cross_venue_live`` / ``surprise_live`` / ``trade_samples`` (ALWAYS refused, ``allow`` cannot lift them). ``allow`` names roots one reader may open."""
    parts = Path(path).parts
    names = tuple(n for n in refused_names() if n not in allow or n in ALWAYS_REFUSED_ROOTS)
    bad = [p for p in parts if p in names or re.match(EXTRACT_ROOT_RE, p) or re.match(EXPERIMENT_ROOT_RE, p) or LIVE_ROOT_NAME in p]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB12 / sealed / live root ({bad[0]}); CB13 refuses it")
    return Path(path)


def guard_monitor_file(path: Path) -> Path:
    """The only monitor file CB13 opens is ``live_trades/trades-YYYYMMDD.jsonl``; ``alerts`` / ``scores-*`` / ``outcomes`` / ``wallets`` / ``stats`` / ``state`` are refused."""
    p = Path(path)
    if p.name in MONITOR_FORBIDDEN_FILES or re.match(MONITOR_FORBIDDEN_RE, p.name):
        raise Refused(f"{p.name}: the monitor's alert / score / outcome / wallet / state files are never opened by CB13")
    if not re.match(MONITOR_TRADES_RE, p.name) or p.parent.name != "live_trades":
        raise Refused(f"{p}: CB13 opens only live_trades/trades-YYYYMMDD.jsonl")
    refuse_path(p, allow=("live_trades",))
    return p


def guard_capture_file(path: Path) -> Path:
    p = Path(path)
    if p.name not in ("rows.csv.gz", "rows_ext.csv.gz", "manifest.json") or not re.match(CAPTURE_DIR_RE, p.parent.name) or p.parent.parent.name != "snapshots":
        raise Refused(f"{p}: CB13 opens only snapshots/<capture>/rows.csv.gz, rows_ext.csv.gz and manifest.json")
    refuse_path(p, allow=("snapshots",))
    return p


def require_output_root(path: Path) -> Path:
    """Data jobs write only under creative_batch13 / h13_*."""
    refuse_path(Path(path))
    if not any(p in ALLOWED_OUTPUT_ROOT_PARTS for p in Path(path).parts):
        raise Refused(f"CB13 writes only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return Path(path)


def is_holdout_path(path: Path) -> bool:
    p = Path(path)
    return any(x in HOLDOUT_PARTS for x in p.parts) or "holdout" in p.name


def guard_screen_path(path: Path) -> Path:
    """A SCREEN / census / pregate job refuses every ``holdout/`` path and every ``*holdout*`` file (opened only by a rep job after the seal check)."""
    if is_holdout_path(path):
        raise Refused(f"{path}: HOLDOUT paths are refused by screen and census jobs (sealed until the rep verifies the seal)")
    return Path(path)


def require_after(now: float, epoch: float, label: str) -> None:
    if now < epoch:
        raise NotNow(f"{label}: not before {datetime.fromtimestamp(epoch, UTC):%Y-%m-%dT%H:%MZ} (pending)")


def require_disk(data_dumps: Path | None, cap_gb: float, allowance_bytes: int, *, free_path: Path | None = None, free_min_gb: float = FREE_DISK_MIN_GB, free_fn=None) -> dict:
    """Exit 75 ("pending", never "not run") if data-dumps + the job's cap > ``cap_gb`` OR root free disk - the job's cap < ``free_min_gb``."""
    return c10.require_disk(data_dumps, cap_gb, allowance_bytes, free_path=free_path, free_min_gb=free_min_gb, free_fn=free_fn)


def collector_gap_ok(now: float, live_check: Callable[[], bool] | None = None) -> None:
    """T jobs (host files, no network) also avoid the collector pass: they start only outside minutes :31-:55 of even UTC hours, and yield (exit 75) while the pass lock is held."""
    d = datetime.fromtimestamp(now, UTC)
    if d.hour % 2 == 0 and COLLECTOR_PASS_MINUTES[0] <= d.minute < COLLECTOR_PASS_MINUTES[1]:
        raise NotNow(f"collector pass window (:{COLLECTOR_PASS_MINUTES[0]}-:{COLLECTOR_PASS_MINUTES[1]} of an even hour); pending")
    if live_check is not None and live_check():
        raise NotNow("the live collector pass is running; pending")


def wait_or_idle(rdir: Path, why: str, now: float) -> dict:
    return cm.idle(Path(rdir), why, now)


def ensure_source_file(path: Path, expected_sha256: str | None = None, *, restore_fn: Callable[[Path], None] | None = None) -> Path:
    """Archive-restore hook: a host source file that was archived and deleted is restored byte for byte by ``restore_fn`` (``restore_from_archive.py``) and its sha256 verified against
    the sealed hash; it is NEVER re-derived. Without a ``restore_fn`` a missing file is ``NotNow`` (pending)."""
    from . import h5_seal  # noqa: PLC0415

    p = Path(path)
    if not p.is_file():
        if restore_fn is None:
            raise NotNow(f"source file {p} is missing (archived?); restore it with restore_from_archive.py and verify the sealed sha256 (pending)")
        restore_fn(p)
        if not p.is_file():
            raise NotNow(f"restore did not recreate {p} (pending)")
    if expected_sha256 and h5_seal.sha256_file(p) != expected_sha256:
        raise Refused(f"{p} sha256 differs from the sealed hash; refusing (a missing or changed source is never re-derived)")
    return p


def require_freeze(part: str, spec_path: Path | None = None, *, require_committed: bool = True, rules_shas: dict[str, str] | None = None) -> str:
    """Analysis jobs (screen, rep) refuse before the CB13 declaration is committed (``model_specs/cb13_v1.json``). One entry per family part (T, R). The entry must PIN the rules shas the job
    has just verified: ``rules_sha256`` equals the part's currently verified sha, and (part T) ``labeller_rules_sha256`` equals the LABELLER sha (``freeze-part`` prints exactly these); a freeze that
    pins other code is refused. ``rules_shas`` ({part: sha}) is mandatory."""
    if part not in FREEZE_PARTS:
        raise Refused(f"unknown freeze part {part!r}")
    if not rules_shas or part not in rules_shas:
        raise Refused(f"require_freeze({part}) needs the currently verified rules shas")
    p = Path(spec_path or (Path(__file__).resolve().parent / "model_specs" / "cb13_v1.json"))
    if not p.exists():
        raise Refused(f"CB13 freeze spec {p} not found: the screens refuse before the CB13 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB13 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"CB13 freeze spec {p} unreadable") from exc
    if not isinstance(doc, dict) or part not in doc or not isinstance(doc[part], dict):
        raise Refused(f"CB13 freeze spec {p} has no {part!r} part")
    entry = doc[part]
    need = {"rules_sha256": rules_shas[part]}
    if part == "T":
        if "LABELLER" not in rules_shas:
            raise Refused("require_freeze(T) needs the verified LABELLER sha")
        need["labeller_rules_sha256"] = rules_shas["LABELLER"]
    for k, want in need.items():
        if entry.get(k) != want:
            raise Refused(f"CB13 freeze entry {part!r} pins {k} {str(entry.get(k))[:12]!r}, but the verified code is {want[:12]!r}: the freeze does not cover this code; refusing")
    return hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()


# ---- stalls, manifests, results ----------------------------------------------------------------------------------------------------------------


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


def write_dir_manifest(rdir: Path, status: str, files: Iterable[Path], extra: dict | None = None) -> dict:
    """Manifest of a host-file job (no fetch): ``status``, ``complete`` true and the sha256 of every output file (relative paths); written once at the end of the job."""
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    rdir = Path(rdir)
    doc = {"status": status, "complete": True, "stopped": None, "written_utc": cm.iso(time.time()), "git_commit": hb._git_commit(),
           "file_sha256": {Path(f).relative_to(rdir).as_posix(): h5_seal.sha256_file(Path(f)) for f in files}, **(extra or {})}
    cm.write_json_atomic(rdir / "manifest.json", doc)
    return doc


def verify_dir_manifest(rdir: Path, status: str, label: str) -> dict:
    """The job's manifest is complete with ``status`` AND every recorded file still hashes to it (each downstream job re-checks)."""
    return c12.verify_fetch(Path(rdir), (status,), label)


def log_access(rdir: Path, job: str, name: str) -> None:
    with (Path(rdir) / ACCESS_LOG).open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "job": job, "file": name}, sort_keys=True) + "\n")


def open_guarded(path: Path, job: str, seal: dict | None = None) -> list[dict]:
    """R outcome files are opened ONLY by ``screen-R`` (SCREEN file) and ``rep-R`` (HOLDOUT file, after the verified seal and a matching sha256). Census jobs open nothing."""
    from . import h5_seal  # noqa: PLC0415

    p = Path(path)
    if p.name not in GUARDED_NAMES:
        raise Refused(f"{p.name} is not a guarded file of CB13")
    if is_holdout_path(p):
        if job != "rep-R":
            raise Refused(f"HOLDOUT outcome file {p.name} may be opened only by rep-R, not {job!r}")
        if not isinstance(seal, dict) or seal.get("verified") is not True:
            raise Refused("the HOLDOUT outcome file needs the verified seal document (verify_seal first)")
        want = (seal.get("holdout_outcome_file_sha256") or {}).get(p.name)
        if not want or h5_seal.sha256_file(p) != want:
            raise Refused(f"{p.name} sha256 differs from the seal (or is not recorded in it); refusing")
        log_access(p.parent.parent if p.parent.name == HOLDOUT_PART else p.parent, job, p.name)
    elif job != "screen-R":
        raise Refused(f"guarded file {p.name} may be opened only by screen-R, not {job!r}")
    return list(read_csv_gz(p))


def verify_seal(rdir: Path, copy_name: str, seal_name: str, seals_dir: Path | None = None, *, holdout_prefix: str = "holdout/", require_committed: bool = True) -> dict:
    """The run's seal equals the copy under ``seals/`` AND the copy is tracked by git and identical to HEAD; the HOLDOUT listing sha256 is re-verified."""
    from . import cb1_history as c1  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    rdir = Path(rdir)
    sp = rdir / seal_name
    if not sp.exists():
        raise Refused(f"{rdir.name} has no {seal_name}; run the seal job first")
    copy = Path(seals_dir or SEALS_DIR) / copy_name
    if not copy.exists() or copy.read_bytes() != sp.read_bytes():
        raise Refused(f"seal copy {copy} missing or different from {sp}")
    if require_committed and not c1.spec_committed(copy):
        raise Refused(f"seal copy {copy} is not committed (or differs from HEAD)")
    doc = json.loads(sp.read_text())
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(holdout_prefix)}
    if h5_seal.listing_sha256(holdout) != doc["listing_sha256"]:
        raise Refused("HOLDOUT listing sha256 differs from the seal; refusing")
    return {**doc, "verified": True}


# ---- field-whitelist readers -------------------------------------------------------------------------------------------------------------------


def assert_clean_columns(columns: Iterable[str]) -> None:
    bad = [c for c in columns if c in FORBIDDEN_OUTPUT_COLUMNS or str(c).startswith("wallet")]
    if bad:
        raise Refused(f"forbidden columns in an output: {bad}")


def whitelist_print(rec: dict) -> dict | None:
    """The whitelisted fields of one monitor line (plus ``tx16`` for in-memory transaction aggregation). Anything else (side, wallet_*, recv_ts, every other ctx_*) is not copied."""
    ts, px, sz = num(rec.get("ts")), num(rec.get("price")), num(rec.get("size"))
    try:
        oi = int(rec.get("outcome_index"))
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(ts) and math.isfinite(px) and math.isfinite(sz)) or sz <= 0 or oi not in (0, 1) or not rec.get("condition_id"):
        return None
    out = {k: rec.get(k) for k in PRINT_FIELDS}
    out.update(ts=ts, price=px, size=sz, outcome_index=oi, cash=num(rec.get("cash")), tx16=str(rec.get("tx16") or ""))
    return out


def iter_prints(path: Path, lo: float, hi: float) -> Iterator[dict]:
    """Stream whitelisted prints with venue ``ts`` in ``[lo, hi)`` from one ``trades-YYYYMMDD.jsonl`` (one line in memory). Window checks are the caller's (``check_window``)."""
    p = guard_monitor_file(path)
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            w = whitelist_print(rec) if isinstance(rec, dict) else None
            if w is not None and lo <= w["ts"] < hi:
                yield w


def capture_meta(cdir: Path) -> dict:
    """(capture id, start epoch, state) of a capture directory from its name and ``manifest.json`` (only ``capture_id``, ``started_utc`` and ``state`` are kept)."""
    d = Path(cdir)
    m = re.match(CAPTURE_DIR_RE, d.name)
    if not m or d.parent.name != "snapshots":
        raise Refused(f"{d}: not a snapshots/<capture> directory")
    refuse_path(d, allow=("snapshots",))
    doc = json.loads(guard_capture_file(d / "manifest.json").read_text())
    start = parse_iso(doc.get("started_utc"))
    if not math.isfinite(start):
        start = datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()
    return {"capture_id": str(doc.get("capture_id") or d.name), "start": start, "state": str(doc.get("state")), "dir": d}


def list_captures(snap_root: Path, split: str, pin: dict, *, only_complete: bool = True) -> list[dict]:
    """The complete captures whose START is allowed for ``split`` (J4-R-window captures are never opened beyond their directory name), oldest first."""
    root = Path(snap_root)
    refuse_path(root, allow=("snapshots",))
    out = []
    for d in sorted(root.iterdir() if root.exists() else []):
        m = re.match(CAPTURE_DIR_RE, d.name)
        if not m or not d.is_dir():
            continue
        nominal = datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()  # the name carries the start to the second: a capture in J4-R is never opened
        if not capture_allowed(nominal, split, pin):
            continue
        meta = capture_meta(d)
        if not capture_allowed(meta["start"], split, pin):
            continue
        if only_complete and meta["state"] != "complete":
            continue
        out.append(meta)
    return sorted(out, key=lambda m: m["start"])


def iter_capture_rows(cdir: Path, wanted: set[str] | None = None) -> Iterator[dict]:
    """Stream the whitelisted ``rows.csv.gz`` columns of one capture (only ``CAPTURE_COLUMNS`` are extracted; ``chg_*``, ``last_trade_price`` and ``volume24hr`` are never read into a row).
    ``wanted`` filters to a set of condition ids."""
    p = guard_capture_file(Path(cdir) / "rows.csv.gz")
    csv.field_size_limit(10**9)
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        idx = {c: head.index(c) for c in CAPTURE_COLUMNS if c in head}
        ci = idx["condition_id"]
        for row in rd:
            if wanted is not None and row[ci] not in wanted:
                continue
            yield {c: row[i] for c, i in idx.items()}


def iter_sidecar_rows(cdir: Path, wanted: set[str] | None = None) -> Iterator[dict]:
    """Stream the whitelisted ``rows_ext.csv.gz`` columns (``market_id``, ``condition_id`` + ``SIDECAR_COLUMNS``); ``uma_resolution_statuses``, ``open_interest`` and ``volume_num`` are not read."""
    p = guard_capture_file(Path(cdir) / "rows_ext.csv.gz")
    csv.field_size_limit(10**9)
    keep = ("market_id", "condition_id", *SIDECAR_COLUMNS)
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        idx = {c: head.index(c) for c in keep if c in head}
        ci = idx["condition_id"]
        for row in rd:
            if wanted is not None and row[ci] not in wanted:
                continue
            yield {c: row[i] for c, i in idx.items()}


def read_id_ts_columns(path: Path, window: tuple[float, float] | None = None) -> tuple[set[str], set[str], dict]:
    """Field-restricted accessor for the exclusion-key sources (sealed historical sets): ONLY id columns (``ID_COLUMNS``) and timestamp columns (``TS_COLUMNS``) are read. Returns
    ``(ids_with_ts_in_window, ids_all, info)``; a file with no timestamp column puts every id in the second set only (``info['no_ts']``)."""
    p = Path(path)
    opener = gzip.open if p.name.endswith(".gz") else open
    csv.field_size_limit(10**9)
    in_win: set[str] = set()
    every: set[str] = set()
    with opener(p, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd, [])
        ids = [(c, head.index(c)) for c in ID_COLUMNS if c in head]
        tss = [head.index(c) for c in TS_COLUMNS if c in head]
        for row in rd:
            keys = [f"{c}:{row[i]}" for c, i in ids if i < len(row) and row[i] not in ("", "None")]
            every.update(keys)
            if window is not None and tss:
                for i in tss:
                    v = row[i] if i < len(row) else ""
                    t = num(v)
                    if not math.isfinite(t):
                        t = parse_iso(v)
                    if t > 1e12:  # milliseconds
                        t /= 1000.0
                    if math.isfinite(t) and window[0] <= t < window[1]:
                        in_win.update(keys)
                        break
    return in_win, every, {"no_ts": not tss, "id_columns": [c for c, _ in ids], "ts_columns": [head[i] for i in tss]}


# ---- statistics helpers ------------------------------------------------------------------------------------------------------------------------


def holm(pvals: dict[str, float], alpha: float) -> dict:
    """STRICT Holm (reject iff p < alpha / (m - i) at every step so far), as CB12 (``c12.holm``); the shared ``c9.holm`` uses ``<=`` and is not used."""
    return c12.holm(pvals, alpha)


def availability(available: int, eligible: int) -> dict:
    """Section 2.6 (iv): the available share of eligible units; below ``AVAIL_MIN`` (60%) the test is "not testable (availability)" (counted, p = 1). Zero eligible units is not testable."""
    share = (available / eligible) if eligible > 0 else math.nan
    return {"available": int(available), "eligible": int(eligible), "share": share, "min": AVAIL_MIN, "ok": bool(eligible > 0 and share >= AVAIL_MIN)}


AVAILABILITY_LABEL = "not testable (availability)"
SOURCE_NOT_TESTABLE = "not testable (source)"


def stage2_final(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    """The final CB13-wide Stage-2 step (section 2.3): ONE strict Holm over every CB13 Stage-2 test that was triggered (T1-rep, T2-rep, T3, R1-rep, R2; a test that could not run enters with p = 1)
    at one-sided ``alpha``. It is applied once, after every triggered test is final, and can only ADD passes to the early alpha / 5 decisions. Names outside the five are refused."""
    allowed = {"T1": "T1-rep", "T2": "T2-rep", "T3": "T3", "R1": "R1-rep", "R2": "R2"}
    extra = [k for k in pvals if k not in allowed]
    if extra:
        raise Refused(f"stage-2 final Holm: {extra} are not CB13 Stage-2 tests {tuple(allowed)}")
    full = {allowed[k]: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


def stage1_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA, family: tuple[str, ...] = STAGE1_HOLM_FAMILY) -> dict:
    """The Stage-1 step-down at one-sided ``alpha`` over the FIXED three tests (k1 = 3); a test not run / not testable / pending enters with p = 1. Holm's first step is alpha / 3 =
    0.0167, so any p < 0.01 passes it: the step can never withdraw an advance."""
    extra = [k for k in pvals if k not in family]
    if extra:
        raise Refused(f"batch-Holm: {extra} are not in the fixed Stage-1 family {family}")
    full = {k: (1.0 if pvals.get(k) is None else float(pvals[k])) for k in family}
    return {"k": len(family), "alpha": alpha, "tests": holm(full, alpha), "not_run_as_p1": [k for k in family if pvals.get(k) is None]}


def stage2_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    full = {k: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


def early_stage2_ok(p: float | None) -> bool:
    """A rep that finishes before k2 is known is judged against alpha / 5 (strict; never withdrawn by the later full Holm)."""
    return p is not None and bool(p < EARLY_ALPHA2)


def mde(se: float, mult: float = 1.2) -> float:
    return c12.mde(se, mult)


def cluster_se_mean(v, cl) -> float:
    return c12.cluster_se_mean(v, cl)


def placebo_advance_rate(draw_ps: list[float | None], gate_p: float = GATE_P) -> dict:
    return c10.placebo_advance_rate(draw_ps, gate_p)


def top_k_drop_mask(v, cl, k: int = TOP_DROP) -> np.ndarray:
    return c9.top_k_drop_mask(v, cl, k)


def max_se_over_ways(v, ways: dict[str, Any]) -> float:
    """The largest CR1 clustered SE of mean(v) over the declared cluster ways (what GTP / GRP write; no point estimate is ever written)."""
    ses = [cluster_se_mean(v, cl) for cl in ways.values()]
    ses = [s for s in ses if math.isfinite(s)]
    return float(max(ses)) if ses else math.nan


def diff_pseudo(values, in_a, in_b) -> tuple[np.ndarray, float]:
    """(pseudo-values over ALL units, estimate) of ``mean(values[a]) - mean(values[b])`` such that mean(pseudo) over the A and B units equals the difference and the cluster-robust SE of the
    pseudo-values' mean is the cluster sandwich SE of the difference. Units in neither arm get the estimate (no influence); callers pass only A and B units."""
    x = np.asarray(values, float)
    a, b = np.asarray(in_a, bool), np.asarray(in_b, bool)
    n = len(x)
    if a.sum() == 0 or b.sum() == 0:
        return np.full(n, math.nan), math.nan
    ma, mb = float(x[a].mean()), float(x[b].mean())
    est = ma - mb
    v = np.full(n, est)
    v[a] += n / a.sum() * (x[a] - ma)
    v[b] -= n / b.sum() * (x[b] - mb)
    return v, est


def wls_coef_pseudo(y, X, w, j: int) -> tuple[np.ndarray, float]:
    """(pseudo-values, coefficient) of regressor ``j`` in the WLS of ``y`` on ``X`` (columns, intercept added) with weights ``w``: Frisch-Waugh residualisation of column ``j`` on the others, so
    v_i = b_j + n w_i r_ij e_i / sum(w r_j^2) and mean(v) = b_j with the cluster sandwich of b_j as the clustered variance of v. Equals ``c10.slope_pseudo`` for one regressor."""
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


def ols_coef(y, X, w=None) -> np.ndarray:
    """Plain (weighted) least-squares coefficients with an intercept first."""
    y = np.asarray(y, float)
    X = np.asarray(X, float)
    if X.ndim == 1:
        X = X[:, None]
    wt = np.ones(len(y)) if w is None else np.asarray(w, float)
    A = np.column_stack([np.ones(len(y)), X])
    sw = np.sqrt(wt)
    beta, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    return beta


def cluster_p(v, clusters: dict[str, Any], *, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared cluster ways (CB10 small-G rule, CB13 seed 1313)."""
    return c10.cluster_p(v, clusters, seed=seed, n_wild=n_wild, alpha=alpha)


def cluster_p_block(v, clusters: dict[str, Any], block, estimator: Callable[[np.ndarray], float] | None = None, *, seed: int = SEED_BOOT, n_wild: int = N_WILD,
                    alpha: float | None = None) -> dict:
    """T's p: the max over ``clusters`` (event; path key x 6 h block) plus the 6-hour-block way under the CB10 rule (G >= 15 enters the max with CR2 + Webb; G < 15 the way leaves the
    max and its leave-one-block-out sign rule binds)."""
    return c10.cluster_p_d(v, clusters, block, estimator, seed=seed, n_wild=n_wild, alpha=alpha)


def leave_one_out_p(groups, stat_fn: Callable[[np.ndarray], tuple[np.ndarray, float]], p_fn: Callable[[np.ndarray, np.ndarray], float], sign: float = 1.0, p_max: float = LOO_DAY_P) -> dict:
    """Leave-one-group-out: for each group, ``stat_fn(keep)`` gives (pseudo-values over the kept units, estimate) and ``p_fn(v, keep)`` the p of that sample. Holds iff every sample keeps the
    sign of ``sign`` AND p < ``p_max`` (the binding leave-one-day-out rule; ``p_max`` 1.0 gives the sign-only A-C1 rule)."""
    g = np.asarray(groups).astype(str)
    out, ok = {}, True
    for k in sorted(set(g.tolist())):
        keep = g != k
        v, est = stat_fn(keep)
        p = p_fn(v, keep) if np.isfinite(est) else 1.0
        out[k] = {"est": float(est) if math.isfinite(est) else None, "p": float(p)}
        ok = ok and math.isfinite(est) and np.sign(est) == np.sign(sign) and est != 0 and p < p_max
    return {"n_groups": len(out), "holds": bool(out) and ok, "per_group": out}


def sign_flip_p_draws(n_draws: int, seed: int, flip_clusters, base_fn: Callable[[np.ndarray], float | None]) -> list[float | None]:
    """Draw ``n_draws`` coin vectors (one coin per cluster in ``flip_clusters``; +1/-1 per unit) and return ``base_fn(signs)`` (a p or None) for each. Deterministic in ``seed``."""
    cl = np.asarray(flip_clusters).astype(str)
    uniq, codes = np.unique(cl, return_inverse=True)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_draws):
        coin = rng.integers(0, 2, len(uniq)) * 2 - 1
        out.append(base_fn(coin[codes].astype(float)))
    return out


def adv_label(p, floor_ok: bool) -> bool:
    return bool(p is not None and p < GATE_P and floor_ok)


# ---- Gamma key lookup and seal-time drops (R) --------------------------------------------------------------------------------------------------


def seal_listing(rdir: Path, extra_roots: dict[str, Path] | None = None, holdout_prefix: str = "holdout/") -> dict:
    """sha256 listing of every HOLDOUT file under ``rdir`` (and of ``extra_roots`` = {label: dir}, e.g. the Binance holdout months)."""
    from . import h5_seal  # noqa: PLC0415

    files = {f"{rdir.name}/{k}": v for k, v in h5_seal.list_files(Path(rdir)).items() if k.startswith(holdout_prefix)}
    for label, d in (extra_roots or {}).items():
        files.update({f"{label}/{k}": v for k, v in h5_seal.list_files(Path(d)).items() if k.startswith(holdout_prefix)})
    return {"files": dict(sorted(files.items())), "listing_sha256": h5_seal.listing_sha256(dict(sorted(files.items())))}


def seal_drops(rows: list[dict], *, transport, seals_dir: Path | None, is_committed, absent_sets: Iterable[str] = (), hist_root: Path | None = None,
               rps: float = 2.0, sleep=time.sleep, live_check=None, own: tuple[str, ...] = OWN_SEAL_COPIES) -> tuple[list[list[str]], dict]:
    """Seal-time drops of ``rows`` (each with ``market_id`` and ``event_ids``; plus optional ``neg_risk_market_id`` and ``series_ids``) against every committed seal copy except CB13's own and
    against the id-source frames that were absent when the exclusion keys were built (re-read here, ids only). Returns (drop rows ``[market_id, block, reason]``, report). Sealed files
    are never edited; the drops are rows of ``drops.csv.gz`` (``DROPPED_*`` blocks)."""
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    seals_dir = Path(seals_dir or SEALS_DIR)
    ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=own, is_committed=is_committed)
    late: set[str] = set()
    reread: dict[str, dict] = {}
    for rel in sorted(set(absent_sets)):
        fp = Path(hist_root) / rel if hist_root is not None else None
        if fp is not None and fp.is_file():
            got = c12.read_id_set(fp)
            late |= got
            reread[rel] = {"now_present": True, "n_ids": len(got)}
        else:
            reread[rel] = {"now_present": False}
    late -= ids
    lim = None

    def lookup(want: set[str]) -> tuple[dict[str, set[str]], int]:
        nonlocal lim
        out: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
        if not want:
            return out, 0
        if transport is None:
            raise Refused("seal copies / re-read frames exist but no transport was given for the key lookup")
        lim = lim or hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        found, _ = c12.lookup_keys_closed_first(lim, sorted(want))
        for k in found.values():
            out["event"].update(e for e in str(k.get("event_ids") or "").split(";") if e)
            if k.get("neg_risk_market_id"):
                out["neg_risk_market"].add(k["neg_risk_market_id"])
            out["series"].update(x for x in str(k.get("series_ids") or "").split(";") if x)
        return out, len(want) - len(found)

    keys, missing = lookup(ids)
    lkeys, lmissing = lookup(late)
    out: list[list[str]] = []
    n = {"KEPT": 0, "DROPPED_SEAL_COPIES": 0, "DROPPED_ABSENT_AT_Q0276": 0}
    for r in rows:
        why = (["id"] if str(r["market_id"]) in ids else []) + c7.key_types_matched(r, keys)
        why_late = (["id"] if str(r["market_id"]) in late else []) + c7.key_types_matched(r, lkeys)
        if why:
            n["DROPPED_SEAL_COPIES"] += 1
            out.append([r["market_id"], "DROPPED_SEAL_COPIES", "+".join(why)])
        elif why_late:
            n["DROPPED_ABSENT_AT_Q0276"] += 1
            out.append([r["market_id"], "DROPPED_ABSENT_AT_Q0276", "+".join(why_late)])
        else:
            n["KEPT"] += 1
    out.sort()
    unver = (bool(ids) and missing / len(ids) > MAX_UNVERIFIED_KEY_SHARE) or (bool(late) and lmissing / len(late) > MAX_UNVERIFIED_KEY_SHARE)
    return out, {"counts": n, "seal_copies_read": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "drop_ids": len(ids), "drop_ids_without_metadata": missing,
                 "absent_reread": reread, "absent_drop_ids": len(late), "absent_drop_ids_without_metadata": lmissing, "disjointness": UNVERIFIED if unver else "verified"}


def load_drops(rdir: Path, seal: dict) -> set[str]:
    """The market ids in ``DROPPED_*`` rows of ``drops.csv.gz`` (never analysed); the file's sha256 must equal the one in the (verified) seal."""
    return c12.load_drops(rdir, seal)


# ---- trials ------------------------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb13_descriptive`` line (EXCLUDE, counts 0): smoke, audit, census, gates, strata, variants."""
    rec = {"kind": "cb13_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_13:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_family(family: str, results: dict[str, dict], *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST, results_sha256: str = "",
               placebos: dict[str, dict] | None = None, n_triggered: int | None = None) -> None:
    """Per-test ``cb13_test`` / ``cb13_replication`` lines (EXCLUDE, ``n_tests`` 0), placebo lines (0) and ONE count line ``ml_explain`` (source ``creative_batch_13:<family>[:rep]``) whose
    ``n_tests`` is the family's number of tests (Stage 1: T 2, R 1, a test behind a failed gate counted with p = 1) or the reps actually triggered (Stage 2)."""
    if family not in FAMILY_TESTS:
        raise Refused(f"unknown CB13 count family {family!r}")
    allowed = FAMILY_REP_TESTS[family] if replication else FAMILY_TESTS[family]
    bad = [t for t in results if t not in allowed]
    if bad:
        raise Refused(f"{bad} are not CB13-{family} {'rep ' if replication else ''}tests {allowed}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb13_replication" if replication else "cb13_test"
    for tid, result in results.items():
        p = result.get("p", 1.0)
        if not result.get("testable", True) or p is None:
            p = 1.0
        base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_13", "hypothesis": tid, "family": family, "results_sha256": results_sha256}
        provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                                 "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
        pl = (placebos or {}).get(tid)
        if pl:
            provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": pl.get("note", "placebo"), "advance_rate": pl.get("advance_rate"),
                                     "n_draws": pl.get("n_draws"), "n_tests": 0}, tp)
    n = len(results) if n_triggered is None else int(n_triggered)
    count_role = role if role in provenance.EVIDENCE_ROLES else EVIDENCE_ROLE_DEV  # the count line is bookkeeping; the validated roles do not include "prospective"
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": count_role, "source": f"creative_batch_13:{family}{':rep' if replication else ''}",
                             "dataset": "creative_batch_13", "n_tests": n, "n_tests_by_family": {f"cb13_{family}{'_rep' if replication else ''}": n},
                             "hypotheses": sorted(results), "replication": bool(replication), "advanced": sorted(t for t, r in results.items() if r.get("advance")),
                             "results_sha256": results_sha256, "note": "CB13 count line: the family's tests (a test behind a failed gate is still counted, p = 1)"}, tp)


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
        funcs += c12.module_funcs(importlib.import_module(".cb13_smoke", __package__))
    else:
        for mod in family_modules(part):
            funcs += c12.module_funcs(mod)
    seen: set[int] = set()
    return [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]


def rules_part_doc(part: str) -> dict:
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    this = importlib.import_module(__name__)
    consts = {"cb13_common": c12.module_constants(this)}
    declared: dict[str, Any] = {}
    if part == "common":
        smoke = importlib.import_module(".cb13_smoke", __package__)
        consts["cb13_smoke"] = c12.module_constants(smoke)
        declared["smoke"] = smoke.declared()
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
            "wallet": {"read": False, "note": "no CB13 job reads or stores a wallet field, a transaction hash (tx16 is aggregated in memory and discarded) or the monitor's side field"},
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
    path = Path(path or (SEALS_DIR / "cb13_rules.json"))
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


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "T") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's. Only that part's modules are imported. Returns the part's ``rules_sha256``."""
    path = Path(path or (SEALS_DIR / "cb13_rules.json"))
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
