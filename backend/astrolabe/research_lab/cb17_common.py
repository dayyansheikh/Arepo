# ruff: noqa: E501
"""CB17 shared parts (docs/research_lab/CREATIVE_BATCH_17.md sections 1.2-1.4, 10.4). Rules part ``common`` (declared now) and the per-part rules machinery.

Only part ``pre`` is declared at this commit (section 1.4 Order: part ``pre`` is committed first, before q0400 runs); ``common``, ``A``, ``B``, ``C`` and ``E`` stay undeclared
(``part_declared: false``) until their own commits, after q0400-q0403 have chosen the branch, the strata levels and the cut points. Part ``pre`` hashes THIS module (every UPPER_CASE
constant and every function except the rules machinery listed in ``RULES_MACHINERY``), ``cb17_pre`` and ``cb17_census``: after the ``pre`` commit these three files are frozen, and the later
parts add NEW modules (window readers, estimators, family code) instead of editing them. The staging switches (which parts are declared, which modules a part hashes) are lower-case on
purpose: they are not hashed, so declaring a later part never changes part ``pre``'s hash. This module holds what every CB17 job shares: the census window and its hard cut-off (no row at or after 2026-10-16T00:00Z is
ever read by a census path), the lookback floor (2026-10-26T00:00Z, J4-R and CB13-T HOLDOUT end there), refused roots, field whitelists (``side`` only in q0400, ``recv_ts`` only in q0403,
wallet and outcome fields never), write-once outputs under ``creative_batch17/``, the ``cb17_descriptive`` trial line, and the per-part sha256 of declared constants plus function
sources (``verify_rules`` refuses, exit 2, on any mismatch).
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from . import cb8_common as cm
from . import cb12_common as c12
from . import cb16_common as c16
from . import provenance

Refused = cm.Refused
NotNow = cm.NotNow

# ---- constants (hashed with this module: every UPPER_CASE JSON-able constant below is part of ``common``) ------------------------------------------------
RULES_VERSION = "cb17-rules-v1"
PARTS = ("common", "pre", "A", "B", "C", "E")
EVIDENCE_ROLE_HIST = "exploratory_historical"
EVIDENCE_ROLE_DEV = "exploratory_dev"
MDE_FACTOR = 3.80  # (z_0.99 + z_0.80) x 1.2 (section 2.7)
CB17_SPORTS_IN_PRIMARY = False

# census window: the worn CB13-T SCREEN days. A census path never reads a row timed at or after CENSUS_CUTOFF (section 10.4 item 1).
CENSUS_START = "2026-10-12T00:00:00Z"
CENSUS_CUTOFF = "2026-10-16T00:00:00Z"
CENSUS_DAYS = ("20261012", "20261013", "20261014", "20261015")
CAPTURE_LOOKBACK_START = "2026-10-11T22:00:00Z"  # q0400 only: the touch capture of a transaction in the first hours of 2026-10-12
LOOKBACK_FLOOR = "2026-10-26T00:00:00Z"  # window readers (not the census) refuse any row before this (finding 5)
ELECTION_NIGHT = ("2026-11-03T18:00:00Z", "2026-11-05T00:00:00Z")
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch17",)
CB13_T_SCREEN_FILES = ("fills.csv.gz", "labels.csv.gz")  # the only creative_batch13 files a census may open (worn SCREEN tables)
HOLDOUT_PARTS = ("holdout", "t_holdout")
EXTRA_REFUSED_ROOTS = ("creative_batch16",)
MONITOR_TRADES_RE = r"^trades-(\d{8})\.jsonl$"
MONITOR_FORBIDDEN_FILES = ("alerts.jsonl", "outcomes.jsonl", "wallets.jsonl", "stats.jsonl", "state.json")
MONITOR_FORBIDDEN_RE = r"^scores-\d{8}\.jsonl$"
CAPTURE_DIR_RE = r"^(\d{8}T\d{6}Z)_[0-9a-f]+$"
SWEEP_DIR_RE = r"^(\d{8}T\d{6}Z)_?[0-9a-f]*$"

# field whitelists (section 1.4). ``side`` is parsed by q0400 only, ``recv_ts`` by q0403 only; wallet, key and outcome fields never.
PRINT_FIELDS = ("ts", "condition_id", "token_id", "outcome_index", "price", "size", "cash", "title", "slug", "ctx_event_id", "ctx_market_id", "ctx_category", "ctx_fee_type")
PRINT_MEMORY_ONLY = ("tx16",)
PRINT_SIDE_FIELDS = ("side",)  # q0400 only
PRINT_LAG_FIELDS = ("recv_ts",)  # q0403 only
FORBIDDEN_PRINT_FIELDS = ("key", "wallet_hash", "wallet", "proxyWallet", "ctx_chg_1h", "ctx_status", "chg_1h")
CAPTURE_FIELDS = ("capture_id", "received_utc", "market_id", "condition_id", "event_id", "closed", "active", "binary", "best_bid", "best_ask", "liquidity", "volume24hr", "end_date",
                  "clob_token_id_0", "neg_risk", "neg_risk_market_id")  # section 1.4 whitelist; the pre-censuses read no volume24hr
SIDECAR_FIELDS = ("market_id", "event_id", "fee_type", "fee_category", "fee_schedule", "order_price_min_tick_size", "clob_rewards", "created_at", "event_open_interest", "event_volume",
                  "series_slugs", "neg_risk_market_id", "accepting_orders")
FORBIDDEN_CAPTURE_FIELDS = ("chg_1h", "chg_1d", "chg_1w", "last_trade_price", "open_interest", "volume_num", "uma_resolution_statuses", "outcome_prices", "closed_time")
SWEEP_FIELDS = ("sweep_id", "token_id", "market_id", "batch_receipt_utc", "book_timestamp", "book_hash", "best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c",
                "depth_bid_5c", "depth_ask_5c", "n_bid_levels", "n_ask_levels", "tick_size", "min_order_size", "state")  # every ROW_COLUMNS field except batch_index
FILLS_FIELDS = ("status", "condition_id", "market_id", "event_id", "label", "path_key", "tau", "tau_last", "d", "P", "size", "cash", "spread0", "mid0", "prev_mid", "touch_age_s", "block", "day")
LABELS_FIELDS = ("condition_id", "label")
FORBIDDEN_OUTPUT_COLUMNS = ("side", "wallet", "wallet_hash", "proxyWallet", "tx16", "transactionHash", "tx_hash", "hash", "name", "pseudonym", "recv_ts", "chg_1h", "chg_1d", "chg_1w",
                            "ctx_chg_1h", "uma_resolution_statuses", "outcome_prices", "outcomePrices", "umaResolutionStatus", "closedTime", "closed_time", "result", "settlement_value", "p_end",
                            "mark", "mark_out", "m_h", "beta", "est", "estimate", "coef", "effect", "pnl", "net")
OUTCOME_KEY_TOKENS = ("beta", "est", "estimate", "mark", "marks", "pnl", "net", "outcome", "outcomes", "coef", "effect", "slope")  # a census result key whose FIRST underscore token is one of these is refused ("markets_x" is fine, "mark_x" is not)
DISK_CAP_GB = 0.01
DATA_DUMPS_CAP_GB = 40.0
STOP_RULE = "3 CPU-hours per family; a job failing twice for the same non-transient reason stops and is recorded; no re-screen of a failed CB17 test"

DATA_DUMPS = cm.DATA_DUMPS
RESEARCH_ROOT = DATA_DUMPS / "research_lab"
CB17_DIR = RESEARCH_ROOT / "creative_batch17"
CB13_T_SCREEN_DIR = RESEARCH_ROOT / "creative_batch13" / "t_screen"
LIVE_TRADES_DIR = RESEARCH_ROOT / "live_trades"
SNAPSHOT_DIR = RESEARCH_ROOT / "snapshots"
SWEEP_DIR = RESEARCH_ROOT / "book_sweeps"
SEALS_DIR = cm.SEALS_DIR

# staging switches: lower-case = not part of any rules hash (see the module docstring). Declaring a later part edits these lines only.
_declared_parts = ("pre",)
_family_parts = ("pre",)
_family_modules = {"pre": ("cb17_pre", "cb17_census")}
_undeclared_reason = "part not declared yet: committed after q0400-q0403 have chosen the branch, the strata levels and the cut points (CREATIVE_BATCH_17.md section 1.4 Order)"

RULES_MACHINERY = ("rules_part_doc", "rules_part_file_doc", "rules_file_doc", "write_rules", "verify_rules", "family_modules", "common_funcs", "part_funcs", "shared_helper_sources",
                   "external_closure", "_code_names", "_helper_key", "common_declared")
SHARED_HELPERS = (("cm", "write_once_json"), ("cm", "sha_obj"), ("cm", "iso"), ("c12", "parse_iso"), ("c12", "read_csv_gz"), ("c16", "refuse_path"), ("c16", "num"))


# ---- small helpers -----------------------------------------------------------------------------------------------------------------------------


def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def ep(s: str) -> float:
    return c12.parse_iso(s)


def iso(t: float) -> str:
    return cm.iso(t)


def sha256_obj(obj) -> str:
    return cm.sha_obj(obj)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def block6(ts: float) -> int:
    """UTC 6-hour block index of an epoch (the 6-hour-block way)."""
    return int(ts // 21600)


def utc_hour(ts: float) -> int:
    return int((ts % 86400) // 3600)


def band6(ts: float) -> int:
    """UTC 6 h band 0-3 (00-06, 06-12, 12-18, 18-24)."""
    return utc_hour(ts) // 6


# ---- census refusals (section 10.4 item 1) ------------------------------------------------------------------------------------------------------


def census_cutoff() -> float:
    return ep(CENSUS_CUTOFF)


def guard_census_time(t: float, what: str = "row") -> float:
    """A census path refuses any row timed at or after 2026-10-16T00:00Z (SCREEN_8, REP_8 and CB13-T's HOLDOUT lie far after it) and any unparseable time."""
    t = float(t)
    if not math.isfinite(t):
        raise Refused(f"{what}: unparseable time")
    if t >= census_cutoff():
        raise Refused(f"{what} timed {iso(t)} is at or after the census cut-off {CENSUS_CUTOFF} (SCREEN_8 / REP_8 / HOLDOUT rows are never read by a census path)")
    return t


def guard_not_window(t: float, what: str = "row") -> float:
    """Window-side mirror (used by the window parts later): refuse a time before the lookback floor."""
    t = float(t)
    if not (math.isfinite(t) and t >= ep(LOOKBACK_FLOOR)):
        raise Refused(f"{what} timed before the lookback floor {LOOKBACK_FLOOR}")
    return t


def refuse_path(path: Path, *, allow: tuple[str, ...] = ()) -> Path:
    """Input AND output guard: CB16's list plus ``creative_batch16``; a path under any holdout part is refused whatever ``allow`` says."""
    p = Path(path)
    if any(x in HOLDOUT_PARTS for x in p.parts) or "holdout" in p.name:
        raise Refused(f"path {path} is a HOLDOUT path (CB13-T's sealed HOLDOUT is never read)")
    bad = [x for x in p.parts if x in EXTRA_REFUSED_ROOTS and x not in allow]
    if bad:
        raise Refused(f"path {path} is under a refused root ({bad[0]}); CB17 never opens another batch's store")
    c16.refuse_path(p, allow=allow)
    return p


def guard_monitor_file(path: Path) -> Path:
    """Only ``live_trades/trades-YYYYMMDD.jsonl`` of a census day."""
    p = Path(path)
    if p.name in MONITOR_FORBIDDEN_FILES or re.match(MONITOR_FORBIDDEN_RE, p.name):
        raise Refused(f"{p.name}: the monitor's alert / score / outcome / wallet / stats / state files are never opened by CB17")
    m = re.match(MONITOR_TRADES_RE, p.name)
    if not m or p.parent.name != "live_trades":
        raise Refused(f"{p}: CB17 opens only live_trades/trades-YYYYMMDD.jsonl")
    if m.group(1) not in CENSUS_DAYS:
        raise Refused(f"{p.name}: not a census day {CENSUS_DAYS}")
    refuse_path(p, allow=("live_trades",))
    return p


def stamp_epoch(stamp: str) -> float:
    return ep(f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z")


def guard_stamped_dir(d: Path, root_name: str, pattern: str, lo: str | None = None) -> tuple[Path, float]:
    """A ``snapshots/<capture>`` or ``book_sweeps/<sweep>`` directory whose start stamp lies inside the census window (``lo`` overrides the window start, q0400's touch lookback);
    returns (dir, start epoch)."""
    d = Path(d)
    m = re.match(pattern, d.name)
    if not m or d.parent.name != root_name:
        raise Refused(f"{d}: not a {root_name}/<stamp> directory")
    refuse_path(d, allow=(root_name,))
    t = stamp_epoch(m.group(1))
    if t < ep(lo or CENSUS_START):
        raise Refused(f"{d.name} starts before the census window {lo or CENSUS_START}")
    guard_census_time(t, d.name)
    return d, t


def guard_capture_dir(d: Path, lo: str | None = None) -> tuple[Path, float]:
    return guard_stamped_dir(d, "snapshots", CAPTURE_DIR_RE, lo)


def guard_sweep_dir(d: Path) -> tuple[Path, float]:
    return guard_stamped_dir(d, "book_sweeps", SWEEP_DIR_RE)


def guard_cb13_t_screen_file(path: Path) -> Path:
    """The only creative_batch13 files a census opens: ``creative_batch13/t_screen/{fills,labels}.csv.gz`` (worn SCREEN tables). The HOLDOUT and every other file are refused."""
    p = Path(path)
    if p.name not in CB13_T_SCREEN_FILES or p.parent.name != "t_screen" or p.parent.parent.name != "creative_batch13":
        raise Refused(f"{p}: a CB17 census opens only creative_batch13/t_screen/{{{', '.join(CB13_T_SCREEN_FILES)}}}")
    refuse_path(p, allow=("creative_batch13",))
    return p


def require_output_root(path: Path) -> Path:
    """Data jobs write only under creative_batch17."""
    refuse_path(Path(path))
    if not any(p in ALLOWED_OUTPUT_ROOT_PARTS for p in Path(path).parts):
        raise Refused(f"CB17 writes only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return Path(path)


def assert_clean_result(doc: Any, path: str = "$") -> None:
    """A census result is counts and SEs only: refuse any key that names a forbidden column, an outcome or a point estimate (recursive)."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            ks = str(k)
            if ks in FORBIDDEN_OUTPUT_COLUMNS or ks.lower().split("_", 1)[0] in OUTCOME_KEY_TOKENS or ks.startswith("wallet"):
                raise Refused(f"forbidden key {ks!r} at {path}: a CB17 census writes counts and standard errors only")
            assert_clean_result(v, f"{path}.{ks}")
    elif isinstance(doc, (list, tuple)):
        for i, v in enumerate(doc):
            assert_clean_result(v, f"{path}[{i}]")


def write_result_once(path: Path, doc: dict) -> str:
    """Write-once JSON under creative_batch17 (clean keys only). Returns the sha256 of the written document."""
    require_output_root(Path(path))
    assert_clean_result(doc)
    cm.write_once_json(Path(path), doc)
    return sha256_file(Path(path))


def require_disk(data_dumps: Path | None, cap_gb: float, allowance_bytes: int, *, free_path: Path | None = None, free_fn=None) -> dict:
    """Exit 75 ("pending") if data-dumps + the job's cap exceed ``cap_gb`` or root free disk is too low."""
    return c16.require_disk(data_dumps, cap_gb, allowance_bytes, free_path=free_path, free_fn=free_fn)


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb17_descriptive`` line (EXCLUDE, counts 0): pre-censuses, smoke, gates, the branch decision, maps. Never a test."""
    assert_clean_result(payload)
    rec = {"kind": "cb17_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_17:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


# =====================================================================================================================================================
# Per-part rules hashing. Everything below is machinery (not hashed); the hashed content is the module-level functions, classes and UPPER_CASE constants.
# =====================================================================================================================================================


def common_funcs() -> list:
    return c12.module_funcs(importlib.import_module(__name__), exclude=RULES_MACHINERY)


def family_modules(part: str) -> list:
    if part not in _family_parts:
        raise Refused(f"unknown rules part {part!r}")
    return c12._mods(_family_modules[part])


def part_funcs(part: str) -> list:
    """The functions hashed for ``part``: the common ones, plus (part ``pre``) the pre modules' own."""
    funcs = list(common_funcs())
    if part != "common":
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
    """Every function / class OUTSIDE the CB17 modules (``astrolabe.*`` only) that ``roots`` reach, transitively. CB17 functions are traversed, not recorded (their sources are in the part's
    own ``func_sources_sha256``)."""
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
        if not mod.startswith(__package__ + ".cb17"):
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
    """sha256 of the source of every shared helper the CB17 rules of ``part`` call (declared roots and everything reached transitively, including the CB13 LABELLER and fee functions)."""
    mods = {"cm": cm, "c12": c12, "c16": c16}
    roots = [getattr(mods[m], n) for m, n in SHARED_HELPERS] + list(part_funcs(part))
    return {k: hashlib.sha256(inspect.getsource(v).encode()).hexdigest() for k, v in external_closure(roots).items()}


def common_declared() -> dict:
    return {"census": {"start": CENSUS_START, "cutoff": CENSUS_CUTOFF, "days": list(CENSUS_DAYS), "rule": "no census path reads a row at or after the cut-off; a file or directory outside the window is refused"},
            "lookback_floor": LOOKBACK_FLOOR, "election_night": list(ELECTION_NIGHT), "output_roots": list(ALLOWED_OUTPUT_ROOT_PARTS),
            "holdout": "CB13-T HOLDOUT paths are refused; only creative_batch13/t_screen/{fills,labels}.csv.gz may be opened by a census",
            "field_whitelists": {"prints": list(PRINT_FIELDS), "side_q0400_only": list(PRINT_SIDE_FIELDS), "recv_ts_q0403_only": list(PRINT_LAG_FIELDS), "forbidden_prints": list(FORBIDDEN_PRINT_FIELDS),
                                 "captures": list(CAPTURE_FIELDS), "sidecar": list(SIDECAR_FIELDS), "forbidden_captures": list(FORBIDDEN_CAPTURE_FIELDS), "sweeps": list(SWEEP_FIELDS),
                                 "fills": list(FILLS_FIELDS), "labels": list(LABELS_FIELDS), "forbidden_output": list(FORBIDDEN_OUTPUT_COLUMNS)},
            "result_rule": "counts, shares and standard errors only; a result with a key naming an outcome, a mark, a point estimate or a forbidden column is refused",
            "mde": f"{MDE_FACTOR} x SE", "stop_rule": STOP_RULE, "sports_in_primary": CB17_SPORTS_IN_PRIMARY, "refused_extra": list(EXTRA_REFUSED_ROOTS)}


def rules_part_doc(part: str) -> dict:
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    if part not in _declared_parts:
        return {"part": part, "part_declared": False, "rules_version": RULES_VERSION, "reason": _undeclared_reason}
    this = importlib.import_module(__name__)
    consts = {"cb17_common": c12.module_constants(this)}
    declared: dict[str, Any] = {"common": common_declared()}
    if part != "common":
        mods = family_modules(part)
        if len(mods) != len(_family_modules[part]):
            return {"part": part, "part_declared": False, "rules_version": RULES_VERSION, "reason": f"family modules {_family_modules[part]} not all present yet"}
        for mod in mods:
            name = mod.__name__.rsplit(".", 1)[-1]
            consts[name] = c12.module_constants(mod)
            declared[name] = mod.declared()
    funcs = part_funcs(part)
    src = {f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}
    return {"part": part, "part_declared": True, "rules_version": RULES_VERSION, "modules": ["cb17_common", *_family_modules.get(part, ())], "constants": consts, "declared": declared,
            "wallet": {"read": False, "note": "no CB17 job reads or stores a wallet field or a transaction hash (tx16 is aggregated in memory and discarded); the Data API side field is read by q0400 only (an agreement count)"},
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
    """Write the rules file. An existing file's DECLARED part must equal the code's (a declared part is never rewritten); an undeclared part may be declared later."""
    path = Path(path or (SEALS_DIR / "cb17_rules.json"))
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


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "pre") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's. Returns the part's ``rules_sha256``."""
    path = Path(path or (SEALS_DIR / "cb17_rules.json"))
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
