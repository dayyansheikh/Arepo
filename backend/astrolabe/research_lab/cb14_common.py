# ruff: noqa: E501
"""CB14 shared parts (docs/research_lab/CREATIVE_BATCH_14.md sections 1.2-1.4, 2.1-2.8, 5, 10).

Everything common to CB14-W (Wikipedia edit bursts) and CB14-S (intra-speech hazard decay) lives here: the refusal lists (outputs AND inputs; no live store, no CB1-CB13 root, no
``h12_say`` / ``h11_attn`` holdout, pageview or outcome file is ever opened; id-only readers are field restricted), the forbidden-field whitelist guards (``side``, wallets,
transaction hashes, user names, ``mw-reverted``, ``outcomePrices`` / ``closedTime`` outside a guarded file), the disk guards (data-dumps cap 40 and root free disk, exit 75 =
"pending"), the guarded outcome files, the fixed-k1 (= 4) Holm helpers (stage-2 early rule at alpha / 4), the clustered-inference helpers (CB10 small-G rule, seed 1414, with
parametrised testability minimums), the trial-line helpers (kinds ``cb14_test`` / ``cb14_replication`` / ``cb14_descriptive``), the shared exclusion-key job and the per-part
rules hashing.

**Per-part rules hashing (the CB11 whole-document-hash pitfall).** ``seals/cb14_rules.json`` holds one sha256 per part: ``common``, ``W``, ``S``. A family part hashes ONLY (a) the
common rule functions and constants of this module (plus, for ``common``, the smoke orchestrator), and (b) the functions and UPPER_CASE constants of that family's own module
(``FAMILY_MODULES``). Verifying part W imports ``cb14_w`` and nothing else; verifying part S imports ``cb14_s`` and nothing else. Rule: nothing family-specific may be added to this
module after the first CB14 job (put it in the family module).
"""

from __future__ import annotations

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
RULES_VERSION = "cb14-rules-v1"
PARTS = ("common", "W", "S")
FAMILY_PARTS = ("W", "S")
FREEZE_PARTS = ("W", "S")
FAMILY_MODULES = {"W": ("cb14_w",), "S": ("cb14_s",)}
FAMILY_TESTS = {"W": ("W1", "W2"), "S": ("S1", "S2")}
FAMILY_REP_TESTS = {"W": ("W1", "W2"), "S": ("S1", "S2")}
STAGE1_HOLM_FAMILY = ("W1", "W2", "S1", "S2")
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 4, fixed
STAGE_ALPHA = 0.05  # Stage 1 batch Holm and Stage 2 Holm, one-sided
STAGE2_K_MAX = 4  # W1-rep, W2-rep, S1-rep, S2-rep: the largest possible Stage-2 count
EARLY_ALPHA2 = STAGE_ALPHA / STAGE2_K_MAX  # a Stage-2 test that finishes before k2 is known is judged against alpha / 4 = 0.0125 (strict <, never withdrawn)
GATE_P = 0.01
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 1414
N_WILD = 9999
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
PLACEBO_SEEDS = {"W1_shift": 14101, "S1_signflip": 14102, "S2_calibrated": 14103}
PLACEBO_SEED_RANGE = (14101, 14120)
SEED_GSP = 14121
SEED_GS0 = 14122
GSP_DRAWS = 500
MDE_MULT = 3.16
MDE_INFLATE = 1.2
MIN_UNITS = 100
MIN_CLUSTERS = 30
TOP_DROP = 5
AVAIL_MIN = 0.60
EVIDENCE_ROLE_HIST = "exploratory_historical"
EVIDENCE_ROLE_PROSPECTIVE = "prospective"
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
PIN_UNSET = "TODO-COORDINATOR"
T_SEAL = "2026-10-22T00:00:00Z"
CB14_SPORTS_IN_PRIMARY = False
SMOKE_VERSION = "cb14-smoke-v1"
DATA_DUMPS_CAP_GB = 40.0
FREE_DISK_MIN_GB = 4.5
HEARTBEAT_S = cm.HEARTBEAT_S
T14_HIST_END = "2026-10-01T00:00:00Z"
CB14_OUTPUT_CAP_GB = 0.4
USER_AGENT = "arepo-research-lab/1 (read-only research; https://www.arepolabs.com)"
# Output roots CB14 writes under, and input roots it never reads (section 1.1 last rows, 1.3)
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch14", "h14_wiki", "h14_wiki_live", "h14_speech")
KEYS_RUN = "exclusion_run14"
KEYS_STATUS = EXCLUSION_KEYS_COMPLETE
KEYS_OUTPUT_CAP_GB = 0.01
HOLDOUT_PART = "holdout"
HOLDOUT_PARTS = ("holdout", "t_holdout")
GUARDED_NAMES = ("outcomes_guarded.csv.gz", "outcomes_guarded_p.csv.gz", "outcomes_guarded_n.csv.gz", "outcomes_guarded_s2.csv.gz")
ACCESS_LOG = "ACCESS_LOG.jsonl"
EXTRA_REFUSED_ROOTS = ("creative_batch13", "creative_batch12", "creative_batch11", "creative_batch10", "creative_batch9", "creative_batch8", "creative_batch7", "creative_batch6",
                       "creative_batch5", "creative_batch4", "creative_batch3", "creative_batch2", "creative_batch1", "snapshots", "trade_samples", "live_trades", "book_sweeps",
                       "surprise_live", "cross_venue_live", "cross_venue", "forecasts", "flow_screen", "h9_flow", "h10_sign", "h10_dlad", "h10_brk", "h11_wprints", "h11_pol",
                       "h11_attn", "h12_say", "h12_quake", "h12_prints", "h12_quake_live", "h12_opt_live", "h13_touch", "h13_binance", "h1_first", "h2_main", "h3_power",
                       "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era", "h7_cb4_series", "h8_tail", "h8_tail_b", "h8_text", "h8_geo", "cb3_followup",
                       "cb6_followup")
ALWAYS_REFUSED_ROOTS = ("surprise_live", "cross_venue_live", "trade_samples", "forecasts", "flow_screen", "live_trades", "snapshots", "book_sweeps")
LIVE_ROOT_NAME = "cross_venue_live"
EXTRACT_ROOT_RE = r"^cb\d+_extract$"
EXPERIMENT_ROOT_RE = r"^e0\d\d$"
# id-only readers (section 1.1 / q0302; section 11 fixes F16): the frame roots whose id columns feed the exclusion keys, and the files (paths relative to the root) each may open. Nothing
# else under them is opened. A HOLDOUT file is opened ONLY when it is named here explicitly (CB11-A's HOLDOUT frame, CB13-R's HOLDOUT barrier events, CB13-T's HOLDOUT fills), and then
# only its id columns leave the reader. ``creative_batch13`` lives under research_lab/, every other root under history/.
ID_READABLE = {"h11_attn": ("frame.csv.gz", "entities.csv.gz", "holdout/frame_hold.csv.gz"), "h11_pol": ("frame.csv.gz",), "h11_wprints": ("markets.csv.gz",),
               "h12_say": ("events.csv.gz", "members.csv.gz"), "h13_touch": ("events.csv.gz", "members.csv.gz", "holdout/events.csv.gz", "holdout/members.csv.gz"),
               "h12_quake": ("events.csv.gz", "members.csv.gz"), "h12_prints": ("markets.csv.gz",), "h12_quake_live": ("markets.csv.gz",), "h12_opt_live": ("markets.csv.gz",),
               "creative_batch13": ("t_screen/fills.csv.gz", "t_holdout/fills.csv.gz")}
ID_RESEARCH_ROOTS = ("creative_batch13",)
S_EXEMPT_ROOT = "h12_say"  # CB12-M's SCREEN frame (the root files; its HOLDOUT lives under holdout/ and is never opened): S keeps the ids that come ONLY from it for N
ID_COLUMNS = ("market_id", "event_id", "condition_id", "neg_risk_market_id", "negRiskMarketID", "series_id")
TERMINAL_NAME = "terminal_{family}.json"
TERMINAL_STATUS = "terminal_not_testable"
CB13_KEYS_FILE = "exclusion_keys.csv.gz"
# Fields: forbidden in any written output (a guarded outcome file may carry the outcome columns, nothing else)
FORBIDDEN_OUTPUT_COLUMNS = ("side", "wallet", "wallet_hash", "proxyWallet", "tx16", "transactionHash", "tx_hash", "name", "pseudonym", "user", "userid", "username", "user_name",
                            "comment", "mw-reverted", "reverted", "mw_reverted", "outcome_prices", "outcomePrices", "umaResolutionStatus", "umaResolutionStatuses", "uma_status",
                            "closedTime", "closed_time")
OUTCOME_COLUMNS = ("outcome_prices", "outcomePrices", "umaResolutionStatus", "umaResolutionStatuses", "uma_status", "closedTime", "closed_time")
PRINT_IN_MEMORY = ("timestamp", "price", "size", "outcomeIndex", "transactionHash")
TICK = 0.01
PRICE_CAP = 0.99
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
GAMMA_PAGE = 100
GAMMA_OFFSET_CAP = 2000
LOOKUP_PER_REQUEST = 50
DATA_PAGE_LIMIT = 10000
DATA_PAGES = 2
DATA_DUMPS = cm.DATA_DUMPS
HIST_ROOT = cm.HIST_ROOT
RESEARCH_ROOT = DATA_DUMPS / "research_lab"
CB14_DIR = RESEARCH_ROOT / "creative_batch14"
CB13_KEYS_DEFAULT = RESEARCH_ROOT / "creative_batch13" / CB13_KEYS_FILE
SEALS_DIR = cm.SEALS_DIR
SMOKE_W_DEFAULT = CB14_DIR / "smoke_W.json"
SMOKE_S_DEFAULT = CB14_DIR / "smoke_S.json"
FEE_FLOOR = 0.04  # W2 / W2-rep taker fee floor (politics convention; the current, not the point-in-time, schedule)
P90_ROUND_TRIP = -0.093  # EXECUTION_COSTS.md line 39

RULES_MACHINERY = ("rules_part_doc", "rules_part_file_doc", "rules_file_doc", "write_rules", "verify_rules", "family_modules", "common_funcs", "part_funcs", "shared_helper_sources",
                   "external_closure", "_code_names", "_helper_key")
# Cross-module helpers the CB14 rules call (section 11 fix F8): the sha256 of each one's source is part of EVERY part's rules doc, so a change to a shared CB2 / CB6 / CB8 / CB9 / CB10 /
# CB12 helper changes the CB14 rules shas (as CB13 ``SHARED_HELPERS``).
SHARED_HELPERS = (("cw", "small_g_pvalue"), ("c12", "holm"), ("c12", "cluster_se_mean"), ("c9", "top_k_drop_mask"), ("c10", "placebo_advance_rate"), ("c10", "leave_one_out_sign"),
                  ("c12", "aggregate_transactions"), ("c12", "fetch_prints_paged"), ("c12", "reach_ok"), ("c12", "listish"), ("c12", "parse_iso"), ("c12", "iso_week_of"),
                  ("c12", "ceil_tick"), ("c12", "read_csv_gz"), ("c12", "read_id_set"), ("c12", "load_exclusion_keys"), ("c12", "exclusion_stage"), ("c12", "lookup_keys_closed_first"),
                  ("c12", "load_series_dates"), ("c12", "manifest_complete"), ("c12", "require_complete"), ("c12", "verify_fetch"), ("c10", "require_disk"), ("c9", "write_stall"),
                  ("c9", "stall_of"), ("c9", "write_results_once"), ("c6", "load_key_sets"), ("bk", "seal_copy_ids_audited"))


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


def rank(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


def read_csv_gz(path: Path) -> Iterator[dict]:
    return c12.read_csv_gz(path)


def sha256_obj(obj) -> str:
    return cm.sha_obj(obj)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ceil_tick(x: float, tick: float = TICK) -> float:
    return c12.ceil_tick(x, tick)


def yes_price(price: float, outcome_index: int, yes_index: int) -> float:
    """YES-terms price of a print: the YES outcome keeps its price, the other maps to ``1 - price``."""
    return float(price) if int(outcome_index) == int(yes_index) else 1.0 - float(price)


def fee(rate: float, p: float) -> float:
    """Taker fee ``rate * p * (1 - p)`` per share."""
    return float(rate) * float(p) * (1.0 - float(p))


def taker_rate(fee_rate, floor: float = FEE_FLOOR) -> float:
    """``max(feeSchedule.rate, floor)``; a missing rate is the floor."""
    r = num(fee_rate)
    return float(max(r, floor)) if math.isfinite(r) else float(floor)


# ---- refusals ----------------------------------------------------------------------------------------------------------------------------------


def refused_names() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*c10.REFUSED_ROOTS, *c10.REFUSED_RUN_IDS, *EXTRA_REFUSED_ROOTS)))


def refuse_path(path: Path, *, allow: tuple[str, ...] = ()) -> Path:
    """Output AND input guard: refuse any path with a CB1-CB13 / sealed / live root among its parts, any ``cb<n>_extract`` or ``e0xx`` directory, and anything under the always-refused live
    stores (``allow`` cannot lift those). ``allow`` names roots one reader may open (id-only readers: ``ID_READABLE``; the CB13 key file: ``creative_batch13``)."""
    parts = Path(path).parts
    names = tuple(n for n in refused_names() if n not in allow or n in ALWAYS_REFUSED_ROOTS)
    bad = [p for p in parts if p in names or re.match(EXTRACT_ROOT_RE, p) or re.match(EXPERIMENT_ROOT_RE, p) or LIVE_ROOT_NAME in p]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB13 / sealed / live root ({bad[0]}); CB14 refuses it")
    return Path(path)


def is_holdout_path(path: Path) -> bool:
    p = Path(path)
    return any(x in HOLDOUT_PARTS for x in p.parts) or "holdout" in p.name


def is_pageview_path(path: Path) -> bool:
    n = Path(path).name.lower()
    return "pageview" in n or n.startswith("pv") or "pageviews" in str(path).lower()


def guard_id_file(path: Path) -> Path:
    """The ONLY way a CB14 job reads another batch's frame: an id-only reader of one whitelisted file (``ID_READABLE``, matched by its path relative to the root). Pageview, outcome and
    guarded files are always refused; a ``holdout`` path only when ``ID_READABLE`` names it explicitly (ids only)."""
    p = Path(path)
    if is_pageview_path(p) or "guarded" in p.name or "outcome" in p.name.lower():
        raise Refused(f"{p}: pageview and outcome files are never opened by CB14 (id-only readers touch the frame id columns only)")
    idx = next((i for i, x in enumerate(p.parts) if x in ID_READABLE), None)
    if idx is None:
        raise Refused(f"{p}: not an id-only readable frame file {ID_READABLE}")
    root, rel = p.parts[idx], "/".join(p.parts[idx + 1:])
    if rel not in ID_READABLE[root]:
        raise Refused(f"{p}: not an id-only readable frame file of {root} {ID_READABLE[root]} (holdout files only when named explicitly)")
    refuse_path(p, allow=(root,))
    return p


def id_source_path(rel: str, hist_root: Path, research_root: Path | None = None) -> Path:
    """The absolute path of an id source ``<root>/<file>``: ``creative_batch13`` under research_lab/ (``research_root``, default ``hist_root``'s parent), every other root under history/."""
    root = rel.split("/", 1)[0]
    base = (Path(research_root) if research_root is not None else Path(hist_root).parent) if root in ID_RESEARCH_ROOTS else Path(hist_root)
    return base / rel


def read_id_columns(path: Path) -> dict[str, set[str]]:
    """Id columns (and the canonical-title column of an entity map) of one id-readable frame file; every other column is dropped at read."""
    p = guard_id_file(path)
    out: dict[str, set[str]] = {}
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        import csv as _csv  # noqa: PLC0415

        rdr = _csv.DictReader(fh)
        keep = [c for c in (rdr.fieldnames or []) if c in ID_COLUMNS or c in ("canonical", "canonical_title")]
        for row in rdr:
            for c in keep:
                if row.get(c):
                    out.setdefault(c, set()).add(str(row[c]))
    return out


def guard_input_path(path: Path) -> Path:
    """A generic input guard for non-id reads: refuse every refused root, holdout, pageview and outcome file."""
    p = Path(path)
    refuse_path(p)
    if is_holdout_path(p) or is_pageview_path(p):
        raise Refused(f"{p}: holdout and pageview paths are never opened by CB14")
    return p


def require_output_root(path: Path) -> Path:
    """Data jobs write only under creative_batch14 / h14_wiki / h14_wiki_live / h14_speech."""
    refuse_path(Path(path))
    if not any(p in ALLOWED_OUTPUT_ROOT_PARTS for p in Path(path).parts):
        raise Refused(f"CB14 writes only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return Path(path)


def assert_clean_columns(columns: Iterable[str], *, guarded: bool = False) -> None:
    """No written output carries a forbidden column (side, wallet, transaction hash, user name, ``mw-reverted``, outcome fields). A guarded outcome file may carry the outcome fields only."""
    cols = list(columns)
    allowed = OUTCOME_COLUMNS if guarded else ()
    bad = [c for c in cols if (c in FORBIDDEN_OUTPUT_COLUMNS and c not in allowed) or str(c).startswith("wallet")]
    if bad:
        raise Refused(f"forbidden columns in an output: {bad}")


def assert_clean_row(row: dict, *, guarded: bool = False) -> dict:
    assert_clean_columns(row.keys(), guarded=guarded)
    return row


def write_gz_csv(path: Path, header: list[str], rows: Iterable[list], *, guarded: bool = False) -> Path:
    """Write a gz csv (a clean-column check first). ``guarded`` only for ``GUARDED_NAMES`` files."""
    from . import history_backfill as hb  # noqa: PLC0415

    if guarded and Path(path).name not in GUARDED_NAMES:
        raise Refused(f"{Path(path).name} is not a guarded file name {GUARDED_NAMES}")
    assert_clean_columns(header, guarded=guarded)
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


def wait_or_idle(rdir: Path, why: str, now: float) -> dict:
    return cm.idle(Path(rdir), why, now)


FREEZE_PIN_KEYS = {"rules": "rules_sha256", "S_MODEL": "s_model_sha256", "S_MODEL_REBASED": "s_model_rebased_sha256"}


def require_freeze(part: str, spec_path: Path | None = None, *, require_committed: bool = True, rules_shas: dict[str, str] | None = None) -> str:
    """Analysis jobs (screen, rep, live, Stage-2 data) refuse before the CB14 declaration is committed (``model_specs/cb14_v1.json``). One entry per family part (W, S). The entry must PIN
    the code the job has just verified: ``rules_sha256`` equals the part's currently verified sha (``rules_shas[part]``) and, part S, ``s_model_sha256`` / ``s_model_rebased_sha256``
    equal the committed model pins (``rules_shas['S_MODEL']`` / ``['S_MODEL_REBASED']``) (``freeze-part`` prints exactly these). A freeze that pins other code is refused."""
    if part not in FREEZE_PARTS:
        raise Refused(f"unknown freeze part {part!r}")
    if not rules_shas or not rules_shas.get(part):
        raise Refused(f"require_freeze({part}) needs the currently verified rules sha of part {part}")
    if part == "S" and not (rules_shas.get("S_MODEL") and rules_shas.get("S_MODEL_REBASED")):
        raise Refused("require_freeze(S) needs the committed position-model pins")
    p = Path(spec_path or (Path(__file__).resolve().parent / "model_specs" / "cb14_v1.json"))
    if not p.exists():
        raise Refused(f"CB14 freeze spec {p} not found: the screens refuse before the CB14 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB14 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"CB14 freeze spec {p} unreadable") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get(part), dict):
        raise Refused(f"CB14 freeze spec {p} has no {part!r} part")
    entry = doc[part]
    need = {FREEZE_PIN_KEYS["rules"]: rules_shas[part]}
    if part == "S":
        need[FREEZE_PIN_KEYS["S_MODEL"]] = rules_shas["S_MODEL"]
        need[FREEZE_PIN_KEYS["S_MODEL_REBASED"]] = rules_shas["S_MODEL_REBASED"]
    for k, want in need.items():
        if entry.get(k) != want:
            raise Refused(f"CB14 freeze entry {part!r} pins {k} {str(entry.get(k))[:12]!r}, but the verified code / pin is {str(want)[:12]!r}: the freeze does not cover this code; refusing")
    return hashlib.sha256(json.dumps(entry, sort_keys=True, default=str).encode()).hexdigest()


# ---- text GET (Factbase HTML), T14_S_open --------------------------------------------------------------------------------------------------------


def get_text(lim, url: str, params: dict, max_retries: int | None = None) -> tuple[int, bytes]:
    """(status, body bytes) for 200/404 through the shared ``Limiter``'s pacing, collector yield and back-off (``Limiter.get`` parses JSON only; a Factbase transcript page is HTML).
    Raises ``RuntimeError`` after the retry limit, as ``Limiter.get``. Counts in the limiter's ``requests`` / ``retries`` / ``throttled``."""
    from . import history_backfill as hb  # noqa: PLC0415

    limit = hb.MAX_RETRIES if max_retries is None else max_retries
    for attempt in range(limit + 1):
        if lim.live_check is not None and lim.clock() - lim._last_live >= 2.0:
            lim.yielded_s += hb.yield_to_live(lim.live_check, lim.sleep)
            lim._last_live = lim.clock()
        wait = lim.min_gap - (lim.clock() - lim.last)
        if wait > 0:
            lim.sleep(wait)
        lim.last = lim.clock()
        lim.requests += 1
        try:
            status, body, headers = lim.transport(url, params)
        except Exception as exc:  # network error: back off and retry
            status, body, headers = 599, b"", {"error": type(exc).__name__}
        if status in (200, 404):
            return status, body
        if attempt == limit:
            break
        lim.retries += 1
        if status == 429:
            lim.throttled += 1
        ra = next((v for k, v in headers.items() if str(k).lower() == "retry-after"), None)
        delay = float(ra) if ra and str(ra).replace(".", "", 1).isdigit() else 2.0**attempt
        lim.sleep(min(delay, 60.0))
    raise RuntimeError(f"giving up after {limit} retries ({url})")


S_OPEN_COMMIT_RE = r"(?m)^\s*T14_S_OPEN:\s*cb12_m_stage1_commit=([0-9a-f]{7,40})\b"
S_OPEN_STOP_RE = r"(?m)^\s*T14_S_OPEN:\s*cb12_m_stopped\b"
LEDGER_REL = "docs/research_lab/EXPERIMENT_LEDGER.md"
RULES_REL = "docs/research_lab/seals/cb14_rules.json"


def s_open_status(ledger_path: Path | None = None, *, git: Callable[[list[str]], str | None] | None = None) -> dict:
    """``T14_S_open`` (section 1.2, 1.3): the commit of CB12-M's Stage-1 result or the ledger record that CB12-M stopped without a screen. The coordinator writes ONE ledger line:
    ``T14_S_OPEN: cb12_m_stage1_commit=<sha>`` (the commit must exist in this repository) or ``T14_S_OPEN: cb12_m_stopped``. Neither -> ``NotNow`` (exit 75, pending).
    Returns ``{"via", "commit", "commit_time"}``."""
    lp = Path(ledger_path) if ledger_path is not None else provenance.REPO_ROOT / LEDGER_REL
    text = lp.read_text(errors="replace") if lp.exists() else ""
    run = git or (lambda args: provenance._git(args, provenance.REPO_ROOT))
    m = re.search(S_OPEN_COMMIT_RE, text)
    if m:
        sha = m.group(1)
        if run(["cat-file", "-e", f"{sha}^{{commit}}"]) is None:
            raise NotNow(f"T14_S_open: ledger names commit {sha} but it is not a commit of this repository (pending)")
        ct = (run(["show", "-s", "--format=%ct", sha]) or "").strip()
        return {"via": "cb12_m_stage1_commit", "commit": sha, "commit_time": float(ct) if ct.isdigit() else math.nan}
    if re.search(S_OPEN_STOP_RE, text):
        return {"via": "cb12_m_stopped", "commit": None, "commit_time": math.nan}
    raise NotNow("T14_S_open: neither a ledger line 'T14_S_OPEN: cb12_m_stage1_commit=<sha>' nor 'T14_S_OPEN: cb12_m_stopped' exists; every N job waits (pending)")


def n_primary_status(open_status: dict, s_rules_sha: str, *, git: Callable[[list[str]], str | None] | None = None) -> dict:
    """Timing rule (section 1.3, round 1 item 6): if the commit that introduced the current part-S rules hash comes AFTER (or at the same second as) the Stage-1 result commit, N is
    reported-only. A CB12-M stop record leaves N primary (nothing left to protect). A rules hash that was never committed is reported-only (not provable)."""
    if open_status.get("via") == "cb12_m_stopped":
        return {"n_primary": True, "reason": "cb12_m_stopped"}
    run = git or (lambda args: provenance._git(args, provenance.REPO_ROOT))
    out = run(["log", "--format=%ct", "--reverse", f"-S{s_rules_sha}", "--", RULES_REL])
    times = [t for t in (out or "").split() if t.isdigit()]
    if not times:
        return {"n_primary": False, "reason": "part S rules hash not found in any commit of the rules file (reported-only)"}
    t_rules, t_open = float(times[0]), num(open_status.get("commit_time"))
    ok = bool(math.isfinite(t_open) and t_rules < t_open)
    return {"n_primary": ok, "reason": "rules part committed before the CB12-M Stage-1 result" if ok else "S rules part committed at/after the CB12-M Stage-1 result: N reported-only",
            "rules_commit_time": t_rules, "open_commit_time": t_open}


# ---- stalls, manifests, results, guarded files -----------------------------------------------------------------------------------------------


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


def terminal_path(root: Path, family: str) -> Path:
    if family not in FAMILY_TESTS:
        raise Refused(f"unknown CB14 family {family!r}")
    return Path(root) / TERMINAL_NAME.format(family=family)


def read_terminal(root: Path, family: str) -> dict | None:
    p = terminal_path(root, family)
    return json.loads(p.read_text()) if p.exists() else None


def record_terminal(root: Path, family: str, label: str, reason: str, *, trials_path: Path | None = None) -> dict:
    """A recorded stall (disjointness unverified, a source stall, an incomplete source walk) makes the family TERMINAL "not testable" (section 2.5): ONE write-once record
    ``terminal_<family>.json`` and, at that moment, the family's counted lines (each test p = 1). A second call returns the record and counts nothing. Downstream jobs read the record
    and end with exit 0 (never an endless exit 75)."""
    p = terminal_path(require_output_root(Path(root)), family)
    if p.exists():
        return {**json.loads(p.read_text()), "newly_counted": False}
    doc = {"family": family, "label": label, "reason": str(reason)[:300], "tests": list(FAMILY_TESTS[family]), "counted": True, "status": TERMINAL_STATUS, "written_utc": cm.iso(time.time())}
    cm.write_once_json(p, doc)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    log_family(family, {t: {"p": 1.0, "testable": False, "advance": False, "verdict": label} for t in FAMILY_TESTS[family]}, trials_path=trials_path, results_sha256=sha)
    return {**doc, "newly_counted": True}


def write_dir_manifest(rdir: Path, status: str, files: Iterable[Path], extra: dict | None = None) -> dict:
    """Manifest of a host-file job (no fetch): ``status``, ``complete`` true and the sha256 of every output file (relative paths); written once at the end of the job."""
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    rdir = Path(rdir)
    doc = {"status": status, "complete": True, "stopped": None, "written_utc": cm.iso(time.time()), "git_commit": hb._git_commit(),
           "file_sha256": {Path(f).relative_to(rdir).as_posix(): h5_seal.sha256_file(Path(f)) for f in files}, **(extra or {})}
    cm.write_json_atomic(rdir / "manifest.json", doc)
    return doc


def log_access(rdir: Path, job: str, name: str) -> None:
    with (Path(rdir) / ACCESS_LOG).open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "job": job, "file": name}, sort_keys=True) + "\n")


def open_guarded(path: Path, job: str, allowed_jobs: tuple[str, ...]) -> list[dict]:
    """A guarded outcome file is opened ONLY by the named analysis jobs (``screen`` / ``rep``); census, pregate, frame and fetch jobs never open one. Every open is logged."""
    p = Path(path)
    if p.name not in GUARDED_NAMES:
        raise Refused(f"{p.name} is not a guarded file of CB14")
    if job not in allowed_jobs:
        raise Refused(f"guarded file {p.name} may be opened only by {allowed_jobs}, not {job!r}")
    log_access(p.parent, job, p.name)
    return list(read_csv_gz(p))


# ---- statistics helpers ------------------------------------------------------------------------------------------------------------------------


def holm(pvals: dict[str, float], alpha: float) -> dict:
    return c12.holm(pvals, alpha)


def stage1_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA, family: tuple[str, ...] = STAGE1_HOLM_FAMILY) -> dict:
    """The Stage-1 step-down at one-sided ``alpha`` over the FIXED four tests (k1 = 4); a test not run / not testable / pending enters with p = 1. Holm's first step is alpha / 4 =
    0.0125, so any p < 0.01 passes it: the step can never withdraw an advance."""
    extra = [k for k in pvals if k not in family]
    if extra:
        raise Refused(f"batch-Holm: {extra} are not in the fixed Stage-1 family {family}")
    full = {k: (1.0 if pvals.get(k) is None else float(pvals[k])) for k in family}
    return {"k": len(family), "alpha": alpha, "tests": holm(full, alpha), "not_run_as_p1": [k for k in family if pvals.get(k) is None]}


def stage2_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    full = {k: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


STAGE2_NAMES = {"W1": "W1-rep", "W2": "W2-rep", "S1": "S1-rep", "S2": "S2-rep"}


def stage2_final(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    """The final CB14-wide Stage-2 step (section 2.3): ONE strict Holm over every CB14 Stage-2 test that was triggered (W1-rep, W2-rep, S1-rep, S2-rep; a triggered test that could not run
    enters with p = 1) at one-sided ``alpha``. Applied once, after every triggered test is final; it can only ADD passes to the early alpha / 4 decisions. Other names are refused."""
    extra = [k for k in pvals if k not in STAGE2_NAMES]
    if extra:
        raise Refused(f"stage-2 final Holm: {extra} are not CB14 Stage-2 tests {tuple(STAGE2_NAMES)}")
    full = {STAGE2_NAMES[k]: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


def stage2_k_min(own_triggered: int, other_results: dict | None, other_tests: tuple[str, ...]) -> int:
    """The smallest admissible Stage-2 count k2 for a rep run: this family's triggered tests plus the other family's (a family whose Stage-1 results are not final yet is assumed to
    trigger all its tests, so k2 can only be too large and alpha / k2 at least as strict as the final step)."""
    if other_results is None:
        return int(own_triggered + len(other_tests))
    return int(own_triggered + sum(1 for t in other_tests if (other_results.get(t) or {}).get("advance") is True))


def early_stage2_ok(p: float | None) -> bool:
    """A rep that finishes before k2 is known is judged against alpha / 4 (strict ``<``; Holm's first step, never withdrawn by the later full Holm)."""
    return p is not None and bool(p < EARLY_ALPHA2)


def mde(se: float, mult: float = MDE_MULT, inflate: float = MDE_INFLATE) -> float:
    """``3.16 x 1.2 x SE`` (z_0.99 + z_0.80, inflated 20%)."""
    return float(mult * inflate * se) if math.isfinite(se) else math.nan


def cluster_se_mean(v, cl) -> float:
    return c12.cluster_se_mean(v, cl)


def max_se_over_ways(v, ways: dict[str, Any]) -> float:
    """The largest CR1 clustered SE of mean(v) over the declared cluster ways (what the power gates write; no point estimate is ever written)."""
    ses = [cluster_se_mean(v, cl) for cl in ways.values()]
    ses = [s for s in ses if math.isfinite(s)]
    return float(max(ses)) if ses else math.nan


def placebo_advance_rate(draw_ps: list[float | None], gate_p: float = GATE_P) -> dict:
    return c10.placebo_advance_rate(draw_ps, gate_p)


def top_k_drop_mask(v, cl, k: int = TOP_DROP) -> np.ndarray:
    return c9.top_k_drop_mask(v, cl, k)


G_CR2 = 15  # CB10 section 2.3: a way with fewer clusters leaves the max and its leave-one-cluster-out sign rule binds


def cluster_p(v, clusters: dict[str, Any], *, min_units: int = MIN_UNITS, min_first_clusters: int = MIN_CLUSTERS, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None,
              min_clusters_by_way: dict[str, int] | None = None, estimator: Callable[[np.ndarray], float] | None = None, sign: float = 1.0) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared cluster ways under the CB10 small-G rule (section 2.3, as CB10 ``cluster_p_d`` / CB13 ``cluster_p_block``), per way:
    G >= 30 CR1; 15 <= G < 30 CR2 + t(G - 1) with the Webb wild bootstrap; G < 15 the way LEAVES the max and its leave-one-cluster-out sign rule binds (every leave-one-out estimate
    keeps the tested sign; ``estimator`` re-estimates on a keep-mask, default the mean of ``v``). ``small_g_rules_hold`` carries those binding sign rules (an advance needs it; a
    calibration placebo is judged on p alone). Testable needs ``min_units`` units, ``min_first_clusters`` clusters in the first declared way, ``min_clusters_by_way`` (W1's 15 ISO
    weeks) and at least one way in the max."""
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
    by_way_ok = all(ways[k]["G"] >= g for k, g in (min_clusters_by_way or {}).items() if k in ways)
    testable = bool(len(v) >= min_units and first is not None and first["G"] >= min_first_clusters and by_way_ok and in_max)
    p = max(in_max) if testable else 1.0
    return {"n": int(len(v)), "mean": float(v.mean()), "testable": testable, "p": float(p), "ways": ways, "small_g_rules_hold": bool(rules_hold)}


def p_pass(r: dict | None, alpha: float) -> bool:
    """The p part of an advance / binding check: testable, every small-G leave-one-cluster-out sign rule holds, and one-sided p < ``alpha`` (strict)."""
    return bool(r and r.get("testable") and r.get("small_g_rules_hold", True) and r.get("p") is not None and r["p"] < alpha)


def wls_coef_pseudo(y, X, w, j: int) -> tuple[np.ndarray, float]:
    """(pseudo-values, coefficient) of regressor ``j`` in the WLS of ``y`` on ``X`` (intercept added) with weights ``w`` (Frisch-Waugh); mean(v) = b_j, the cluster sandwich of b_j is the
    clustered variance of v."""
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


def sign_ok(est, ref) -> bool:
    """True iff ``est`` is finite, non-zero and has the sign of ``ref``."""
    return bool(est is not None and math.isfinite(est) and est != 0 and ref is not None and math.isfinite(ref) and np.sign(est) == np.sign(ref))


def halves_and_quarters(times: Iterable[float]) -> tuple[list[int], list[str]]:
    """(half index 0/1 by the median of ``times``, calendar-quarter label) per unit time: the sign-by-period checks."""
    t = list(times)
    if not t:
        return [], []
    med = float(np.median(t))
    halves = [int(x > med) for x in t]
    quarters = [f"{datetime.fromtimestamp(x, UTC).year}Q{(datetime.fromtimestamp(x, UTC).month - 1) // 3 + 1}" for x in t]
    return halves, quarters


# ---- trials ------------------------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb14_descriptive`` line (EXCLUDE, counts 0): smoke, audit, census, gates, strata, variants."""
    rec = {"kind": "cb14_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_14:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_family(family: str, results: dict[str, dict], *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST, results_sha256: str = "",
               placebos: dict[str, dict] | None = None, n_triggered: int | None = None) -> None:
    """Per-test ``cb14_test`` / ``cb14_replication`` lines (EXCLUDE, ``n_tests`` 0), placebo lines (0) and ONE count line ``ml_explain`` (source ``creative_batch_14:<family>[:rep]``) whose
    ``n_tests`` is the family's number of tests (Stage 1: W 2, S 2, a test behind a failed gate counted with p = 1) or the reps actually triggered (Stage 2)."""
    if family not in FAMILY_TESTS:
        raise Refused(f"unknown CB14 count family {family!r}")
    allowed = FAMILY_REP_TESTS[family] if replication else FAMILY_TESTS[family]
    bad = [t for t in results if t not in allowed]
    if bad:
        raise Refused(f"{bad} are not CB14-{family} {'rep ' if replication else ''}tests {allowed}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb14_replication" if replication else "cb14_test"
    for tid, result in results.items():
        p = result.get("p", 1.0)
        if not result.get("testable", True) or p is None:
            p = 1.0
        base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_14", "hypothesis": tid, "family": family, "results_sha256": results_sha256}
        provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                                 "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
        pl = (placebos or {}).get(tid)
        if pl:
            provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": pl.get("note", "placebo"), "advance_rate": pl.get("advance_rate"),
                                     "n_draws": pl.get("n_draws"), "n_tests": 0}, tp)
    n = len(results) if n_triggered is None else int(n_triggered)
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_14:{family}{':rep' if replication else ''}",
                             "dataset": "creative_batch_14", "n_tests": n, "n_tests_by_family": {f"cb14_{family}{'_rep' if replication else ''}": n},
                             "hypotheses": sorted(results), "replication": bool(replication), "advanced": sorted(t for t, r in results.items() if r.get("advance")),
                             "results_sha256": results_sha256, "note": "CB14 count line: the family's tests (a test behind a failed gate is still counted, p = 1)"}, tp)


# ---- shared exclusion-key job (q0302) -----------------------------------------------------------------------------------------------------------


def frame_ids(hist_root: Path, research_root: Path | None = None) -> tuple[dict[str, dict[str, set[str]]], list[str]]:
    """Id columns (field restricted, ``ID_READABLE`` files only, never an outcome / pageview file; a holdout file only when named there) of every other batch's frame; a file that
    does not exist yet is 'absent at q0302' (recorded, re-read by the census)."""
    found: dict[str, dict[str, set[str]]] = {}
    absent: list[str] = []
    for root, files in ID_READABLE.items():
        for name in files:
            p = id_source_path(f"{root}/{name}", hist_root, research_root)
            if p.is_file():
                found.setdefault(root, {})
                for col, ids in read_id_columns(p).items():
                    found[root].setdefault(col, set()).update(ids)
            else:
                absent.append(f"{root}/{name}")
    return found, absent


def split_key_sets(found: dict[str, dict[str, set[str]]], seal_ids: set[str], base_ids: set[str]) -> dict:
    """The q0302 id sets (section 1.3 and section 11 fix F4). ``s_exempt`` = the market ids of CB12-M's SCREEN frame (``S_EXEMPT_ROOT``) that come from NO other direct source (another
    id-readable frame or a seal copy), REGARDLESS of whether the CB13 base key file already holds them (it does: q0276 unions the CB12 frames). ``lookup`` = every direct id not in
    the base file plus every exempt id (their key rows are rebuilt by lookup so the exemption file can carry them)."""
    other: set[str] = set(seal_ids)
    say: set[str] = set()
    per_root: dict[str, int] = {}
    for root, cols in found.items():
        ids = set(cols.get("market_id", set()))
        per_root[root] = len(ids)
        (say if root == S_EXEMPT_ROOT else other).update(ids)
    s_exempt = say - other
    lookup = ((other | say) - set(base_ids)) | s_exempt
    return {"s_exempt": s_exempt, "lookup": lookup, "new_ids": (other | say) - set(base_ids), "sets": per_root}


def exempt_rows(s_rows: list[list[str]], other_rows: list[list[str]]) -> list[list[str]]:
    """The exemption file's rows (KEY_COLUMNS: market_id, found, event_ids, neg_risk_market_id, series_ids) with every event / neg-risk / series key that a NON-exempt row also carries
    removed: an exempt market never lifts a key that another source requires (the stricter reading)."""
    oe, on, os_ = set(), set(), set()
    for r in other_rows:
        oe.update(e for e in str(r[2]).split(";") if e)
        if r[3]:
            on.add(str(r[3]))
        os_.update(s for s in str(r[4]).split(";") if s)
    out = []
    for r in s_rows:
        out.append([r[0], r[1], ";".join(e for e in str(r[2]).split(";") if e and e not in oe), "" if str(r[3]) in on else r[3], ";".join(s for s in str(r[4]).split(";") if s and s not in os_)])
    return out


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, hist_root: Path, base_path: Path, base_sha256: str, seals_dir: Path | None = None, is_committed=None, rps: float = 2.0,
                   disk_cap: int = int(KEYS_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, now: float | None = None, sleep=None, live_check=None, should_stop=None,
                   wall_clock=None, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0302. CB13 q0276's key file (sha256 pin MANDATORY) plus, by closed-first Gamma id lookup (<= 50 per request, resumable), the market ids of every id-readable frame (``ID_READABLE``;
    a missing one is 'absent at q0302') and of every committed seal copy. Writes ``exclusion_keys.csv.gz`` (all keys, for W) and ``s_exempt_ids.csv.gz`` (the ids that come ONLY from
    CB12-M's SCREEN frame ``h12_say``: S keeps them for N by the declared deviation) and ``attn_entities.csv.gz`` (CB11-A's canonical titles). More than 2% of ALL ids without
    metadata -> ``disjointness_unverified``."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    out_root, seals_dir = require_output_root(Path(out_root)), Path(seals_dir or cm.SEALS_DIR)
    base_path = Path(base_path)
    if not base_sha256 or base_sha256 == PIN_UNSET:
        raise Refused(f"the sha256 pin of the CB13 key file (--base-sha256) is unset ({PIN_UNSET}); the coordinator fills it in the queue draft from `sha256sum` on the host")
    refuse_path(base_path, allow=("creative_batch13",))
    got = h5_seal.sha256_file(base_path) if base_path.exists() else None
    if got != base_sha256:
        raise Refused(f"base key file {base_path} sha256 {got} != pinned {base_sha256}")
    base_ids = c12.read_id_set(base_path)
    require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    found, absent = frame_ids(Path(hist_root))
    seal_ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, is_committed=is_committed, own=())
    ks = split_key_sets(found, seal_ids, base_ids)
    s_only, lookup, set_ids = ks["s_exempt"], ks["lookup"], ks["sets"]
    titles = sorted(found.get("h11_attn", {}).get("canonical", set()) | found.get("h11_attn", {}).get("canonical_title", set()))
    fr = cm.open_run(out_root, KEYS_RUN, transport, allowed_run_id=KEYS_RUN, kind="cb14_exclusion_keys", label="CB14 exclusion keys",
                     params={"base_keys_sha256": base_sha256, "n_base_ids": len(base_ids), "n_new_ids": len(ks["new_ids"]), "n_s_exempt_ids": len(s_only), "n_lookup_ids": len(lookup),
                             "sets": set_ids, "sets_absent_at_q0302": absent, "seal_copies_used": used, "seal_copies_skipped": skipped, "evidence_role": EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep or time.sleep, live_check=live_check,
                     wall_clock=wall_clock or time.time, snapshot_root=snapshot_root, health_check=health_check)
    rep_new, stopped = c12.exclusion_stage(fr, lookup, should_stop)
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep_new is not None
    import csv as _csv  # noqa: PLC0415

    rows: list[list[str]] = []
    with gzip.open(base_path, "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in _csv.DictReader(fh) if r[c6.KEY_COLUMNS[0]] not in s_only]  # exempt ids come back from the lookup rows below
    s_rows: list[list[str]] = []
    with gzip.open(fr.rdir / "exclusion_keys.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        for r in _csv.DictReader(fh):
            (s_rows if r[c6.KEY_COLUMNS[0]] in s_only else rows).append([r[c] for c in c6.KEY_COLUMNS])
    keys_out = out_root / "exclusion_keys.csv.gz"
    out_root.mkdir(parents=True, exist_ok=True)
    keys_out.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), sorted(rows + s_rows)))
    (out_root / "s_exempt_ids.csv.gz").write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), sorted(exempt_rows(s_rows, rows))))
    (out_root / "attn_entities.csv.gz").write_bytes(hb._gz_csv_bytes(["canonical_title"], [[t] for t in titles]))
    base_rep_p = base_path.with_name(c9.EXCLUSION_REPORT_NAME)
    base_rep = json.loads(base_rep_p.read_text()) if base_rep_p.exists() else {}
    n_all = int(base_rep.get("n_ids", len(base_ids))) + len(lookup - base_ids)
    n_missing = int(base_rep.get("n_missing", 0)) + rep_new["n_missing"]  # an exempt id missing in both counts twice (conservative)
    share = n_missing / n_all if n_all else 1.0
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": UNVERIFIED if share > MAX_UNVERIFIED_KEY_SHARE else "verified", "base_keys_sha256": base_sha256, "new": rep_new, "sets": set_ids,
           "sets_absent_at_q0302": absent, "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "keys_sha256": h5_seal.sha256_file(keys_out),
           "s_exempt_ids": len(s_only), "built_utc": cm.iso(time.time())}
    (out_root / c9.EXCLUSION_REPORT_NAME).write_text(json.dumps(rep, indent=1, sort_keys=True))
    status = UNVERIFIED if rep["disjointness"] == UNVERIFIED else KEYS_STATUS
    m = fr.manifest(None, {"exclusion_report": {k: rep[k] for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys_sha256")}, "status": status, "complete": True})
    m["status"] = status
    return m


def load_keys(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    """(market ids, {event, neg_risk_market, series} id sets, report, sha256) of a CB14 key file (same layout as CB13's)."""
    return c12.load_exclusion_keys(Path(keys_path))


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
        funcs += c12.module_funcs(importlib.import_module(".cb14_smoke", __package__))
    else:
        for mod in family_modules(part):
            funcs += c12.module_funcs(mod)
    seen: set[int] = set()
    return [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]


def _code_names(obj) -> tuple[set[str], dict]:
    """The global / attribute names a function (with its nested functions, lambdas and comprehensions) or a class's methods reference, and the globals they resolve in."""
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
    """Every function / class OUTSIDE the CB14 modules (``astrolabe.*`` only) that ``roots`` reach, transitively (section 11 fix F8, review of 515d68d: a shared helper's own helpers,
    e.g. ``cb2_weather._cluster_sums`` under ``small_g_pvalue``, are hashed too). A name resolves through the referencing function's globals: a function or class directly, or, for a
    module, every attribute name the function uses that is a function / class of that module (over-inclusive, never under-inclusive). CB14 functions are traversed, not recorded (their
    sources are in the part's own ``func_sources_sha256``)."""
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
        if not mod.startswith(__package__ + ".cb14"):
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
    """sha256 of the source of every shared helper the CB14 rules of ``part`` call: the declared roots (``SHARED_HELPERS``) and every helper reached transitively from them and from the
    part's own functions (``external_closure``)."""
    from . import cb2_weather as cw  # noqa: PLC0415  (small_g_pvalue: the p engine of cluster_p)
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415

    mods = {"c12": c12, "c10": c10, "c9": c9, "cw": cw, "c6": c6, "bk": bk}
    roots = [getattr(mods[m], n) for m, n in SHARED_HELPERS] + list(part_funcs(part))
    return {k: hashlib.sha256(inspect.getsource(v).encode()).hexdigest() for k, v in external_closure(roots).items()}


def rules_part_doc(part: str) -> dict:
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    this = importlib.import_module(__name__)
    consts = {"cb14_common": c12.module_constants(this)}
    declared: dict[str, Any] = {}
    if part == "common":
        smoke = importlib.import_module(".cb14_smoke", __package__)
        consts["cb14_smoke"] = c12.module_constants(smoke)
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
            "wallet": {"read": False, "note": "no CB14 job reads or stores a wallet field, a transaction hash (aggregated in memory and discarded), the Data API side field, or a Wikipedia user name"},
            "shared_helper_sources_sha256": shared_helper_sources(part),
            "funcs_sha256": hashlib.sha256("\n".join(src[k] for k in sorted(src)).encode()).hexdigest(), "func_sources_sha256": dict(sorted(src.items()))}


def common_declared() -> dict:
    return {"refused_roots": list(EXTRA_REFUSED_ROOTS), "always_refused": list(ALWAYS_REFUSED_ROOTS), "id_readable": {k: list(v) for k, v in ID_READABLE.items()},
            "output_roots": list(ALLOWED_OUTPUT_ROOT_PARTS), "seeds": {"boot": SEED_BOOT, "placebo": PLACEBO_SEEDS, "gsp": SEED_GSP, "gs0": SEED_GS0},
            "bootstrap": {"n_boot": N_BOOT, "n_wild": N_WILD, "small_g": "G>=30 CR1; 15<=G<30 CR2 t(G-1) + Webb wild; G<15 the way leaves the max and its leave-one-cluster-out sign rule binds (CB10 2.3)"},
            "holm": {"k1": BATCH_HOLM_K1, "alpha": STAGE_ALPHA, "stage2_early_alpha": EARLY_ALPHA2, "strict": True}, "disk": {"data_dumps_cap_gb": DATA_DUMPS_CAP_GB, "free_min_gb": FREE_DISK_MIN_GB,
                                                                                                                                    "output_cap_gb": CB14_OUTPUT_CAP_GB},
            "field_whitelists": {"forbidden_output_columns": list(FORBIDDEN_OUTPUT_COLUMNS), "print_in_memory": list(PRINT_IN_MEMORY)},
            "user_name_rule": "MediaWiki user names are read in memory only (bot flag, per-page distinct-user index) and never written; revision-deleted names are unknown",
            "stop_rule": "5 CPU-hours per family; no re-screen of a failed CB14 test"}


def rules_part_file_doc(part: str) -> dict:
    d = json.loads(json.dumps(rules_part_doc(part), sort_keys=True, default=str))
    if d.get("part_declared") is False:
        return {**d, "rules_sha256": None}
    return {**d, "rules_sha256": cm.sha_obj(d)}


def rules_file_doc(parts: tuple[str, ...] = PARTS) -> dict:
    return {"rules_version": RULES_VERSION, "parts": {p: rules_part_file_doc(p) for p in parts}}


def write_rules(path: Path | None = None) -> Path:
    """Write the rules file. An existing file's DECLARED part must equal the code's (a declared part is never rewritten)."""
    path = Path(path or (SEALS_DIR / "cb14_rules.json"))
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


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "W") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's. Only that part's modules are imported. Returns the part's ``rules_sha256``."""
    path = Path(path or (SEALS_DIR / "cb14_rules.json"))
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
