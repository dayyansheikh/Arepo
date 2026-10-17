# ruff: noqa: E501
"""CB10 shared parts (docs/research_lab/CREATIVE_BATCH_10.md sections 1.3, 1.4, 2.3, 2.5, 2.8, CB10-F).

Constants and refusal lists (outputs AND inputs), the code-derived rules file ``seals/cb10_rules.json`` (function SOURCE hashed, committed before
the first read; no wallet field is read by any CB10 job, so no key fingerprint is pinned), the Gamma field whitelist (round 1 item 6), the disk
guards (data-dumps cap AND root free disk, exit 75 = "pending", round 1 item 14), the trial-line helpers (counted through ``battery2.KIND_RULES``:
``cb10_test`` / ``cb10_replication`` / ``cb10_descriptive`` are EXCLUDE; the ``ml_explain`` count line carries ``n_tests``), the cluster p with
the CB10 ISO-week small-G rule, influence pseudo-values (slope and weighted contrasts), the fixed-k batch-Holm label (k1 = 3), the freeze gate
and the q0201 exclusion keys. Reuses ``cb8_common`` / ``cb9_common`` machinery. No outcome analysis lives here.
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
import shutil
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import provenance

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

RULES_VERSION = "cb10-rules-v1"
SEALS_DIR = cm.SEALS_DIR
RULES_FILE = SEALS_DIR / "cb10_rules.json"
DATA_DUMPS = cm.DATA_DUMPS
CB10_DIR = DATA_DUMPS / "research_lab" / "creative_batch10"
HIST_ROOT = cm.HIST_ROOT
H10_DLAD = "h10_dlad"
H10_BRK = "h10_brk"
SMOKE_DEFAULT = CB10_DIR / "smoke.json"
EXCLUSION_KEYS_DEFAULT = CB10_DIR / "exclusion_keys.csv.gz"
EXCLUSION_REPORT_NAME = c9.EXCLUSION_REPORT_NAME
CB9_KEYS_DEFAULT = c9.EXCLUSION_KEYS_DEFAULT
FREEZE_SPEC = Path(__file__).resolve().parent / "model_specs" / "cb10_v1.json"
T_SEAL = c9.T_SEAL
T_SEAL_EPOCH = c9.T_SEAL_EPOCH
T10_HIST_END = "2026-10-01T00:00:00Z"
J4R_WINDOW = ("2026-10-16", "2026-10-21")
ET = ZoneInfo("America/New_York")

# Disk (section 2.8): data-dumps + the job's cap <= 14 GiB AND root free disk - the job's cap >= 4.5 GB (4 GB collector guard + 0.5 GB margin).
DATA_DUMPS_CAP_GB = 40.0  # 2026-10-17 ops convention after the host disk was enlarged (the design text says 14; open item)
FREE_DISK_MIN_GB = 4.5
TOTAL_OUTPUT_CAP_GB = 0.12

STAGE1_HOLM_FAMILY = ("D1", "B1", "B2")
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 3, fixed
BATCH_HOLM_ALPHA1 = 0.01
STAGE2_ALPHA = 0.05
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 1010
N_WILD = 9999
PLACEBO_SEEDS = {"D1_signflip_week": 10101, "D1_signflip_date": 10102, "B1_swap_event": 10103, "B1_swap_day": 10104, "spare_5": 10105, "spare_6": 10106}
SEED_GDP = 10107
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
GATE_P = 0.01
MIN_UNITS = 100
MIN_CLUSTERS = 30
TOP_DROP = 5
G_CR1 = 30
G_CR2 = 15
EVIDENCE_ROLE_HIST = "exploratory_historical"
DATA_ROLE_PROSP = "prospective_post_freeze"
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
OWN_SEAL_COPIES = ("cb10_brk_holdout_SEAL.json",)
PENDING = "pending"

# Non-stalling dependency chains (CB9 freeze check M5, shared vocabulary in cb9_common): a smoke / disjointness / upstream failure writes a terminal
# manifest (complete, label) and exits 0; the census copies the label and the screens log the affected tests with p = 1, testable false.
STALL_NOT_RUN_SOURCE = c9.STALL_NOT_RUN_SOURCE
STALL_DISJOINTNESS = c9.STALL_DISJOINTNESS
STALL_UPSTREAM = c9.STALL_UPSTREAM
STALL_STATUSES = c9.STALL_STATUSES
STAGE1_RESULTS = {"results_D.json": ("D1",), "results_B.json": ("B1", "B2")}

# Inputs CB10 never reads and outputs it never writes under (design 1.1 last three rows, 1.3).
REFUSED_RUN_IDS = tuple(c9.REFUSED_RUN_IDS) + ("h10_sign", "exclusion_run9", "pyth_frame", "pyth", "kd_frame", "kd_books", "sign", "pyth_live", "halfday")
REFUSED_ROOTS = tuple(c9.REFUSED_ROOTS) + ("creative_batch9", "h10_sign", "cb9_extract", "cb10_extract")
# Inputs CB10 may read although they sit under a refused root: the CB7-CB9 exclusion key files and their reports (ids and keys only); frame id
# lists pinned by sha256 are read through ``read_ids_only`` (market ids only).
READ_ALLOWED_NAMES = ("exclusion_keys.csv.gz", EXCLUSION_REPORT_NAME)
READ_ALLOWED_PARENTS = ("creative_batch7", "creative_batch8", "creative_batch9")
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch10", H10_DLAD, H10_BRK)

# ---- Gamma field whitelist (design 1.4, round 1 item 6) ----------------------------------------------------------------------------------------
GAMMA_KEEP = ("id", "conditionId", "question", "slug", "clobTokenIds", "outcomes", "startDate", "endDate", "negRisk", "negRiskMarketID", "resolutionSource",
              "feeSchedule", "orderMinSize")
# Read in memory only (listing fields), never stored: the event / series ids and slugs (kept as derived key strings), the description (sha256 and the
# frozen flag booleans only), ``feeType`` and the first event title (derived category labels for B only), ``volumeNum`` (B's ``vol_ok`` boolean only).
GAMMA_FORBIDDEN = ("lastTradePrice", "bestBid", "bestAsk", "spread", "oneDayPriceChange", "oneHourPriceChange", "oneWeekPriceChange", "oneMonthPriceChange",
                   "oneYearPriceChange", "umaResolutionStatus", "umaResolutionStatuses", "closedTime", "outcomePrices", "volume", "volumeNum", "volume24hr",
                   "volume1wk", "volume1mo", "volume1yr", "volumeClob", "volume24hrClob", "liquidity", "liquidityNum", "liquidityClob", "description")
WHITELIST_OUTPUT = ("market_id", "condition_id", "question", "slug", "token_yes", "token_no", "yes_idx", "outcomes", "start_date", "end_date", "start_epoch", "end_epoch",
                    "neg_risk", "neg_risk_market_id", "event_id", "event_ids", "series_ids", "series_slugs", "resolution_source", "fee_rate", "fee_taker_only",
                    "order_min_size", "desc_sha256")


def _num(x) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return math.nan
    return v


def _epoch(s) -> float:
    if not s:
        return math.nan
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        return math.nan
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def _listish(v) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            x = json.loads(v)
        except ValueError:
            return []
        return x if isinstance(x, list) else []
    return []


def whitelist_market(m: dict, *, flag_res: dict[str, str] | None = None) -> dict | None:
    """The ONLY Gamma parser of the CB10 frames. Keeps the whitelisted keys (renamed), the event / series ids and slugs, the fee schedule rate, the
    description's sha256 and (if ``flag_res``) one boolean per frozen flag; every other field (``outcomePrices``, ``lastTradePrice``, ``bestBid`` /
    ``bestAsk``, ``closedTime``, ``umaResolutionStatus(es)``, ``volume*``, ``liquidity*``, price changes, the description text) is dropped here, before
    anything is written or logged. ``None`` unless the market has an id, a condition id, two outcomes and two token ids."""
    if not isinstance(m, dict) or m.get("id") is None or not m.get("conditionId"):
        return None
    labels = [str(x) for x in _listish(m.get("outcomes"))]
    toks = [str(x) for x in _listish(m.get("clobTokenIds"))]
    if len(labels) != 2 or len(toks) != 2:
        return None
    yes_idx = labels.index("Yes") if "Yes" in labels else 0
    evs = [e for e in (m.get("events") if isinstance(m.get("events"), list) else []) if isinstance(e, dict)]
    eids, sids, sslugs = [], [], []
    for e in evs:
        if e.get("id") is not None and str(e["id"]) not in eids:
            eids.append(str(e["id"]))
        for s in (e.get("series") if isinstance(e.get("series"), list) else []):
            if isinstance(s, dict):
                if s.get("id") is not None and str(s["id"]) not in sids:
                    sids.append(str(s["id"]))
                if s.get("slug") and str(s["slug"]) not in sslugs:
                    sslugs.append(str(s["slug"]))
    fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    desc = str(m.get("description") or "")
    out = {"market_id": str(m["id"]), "condition_id": str(m["conditionId"]), "question": str(m.get("question") or "")[:300], "slug": str(m.get("slug") or "")[:200],
           "token_yes": toks[yes_idx], "token_no": toks[1 - yes_idx], "yes_idx": yes_idx, "outcomes": json.dumps(labels), "start_date": str(m.get("startDate") or ""),
           "end_date": str(m.get("endDate") or ""), "start_epoch": _epoch(m.get("startDate")), "end_epoch": _epoch(m.get("endDate")), "neg_risk": int(bool(m.get("negRisk"))),
           "neg_risk_market_id": str(m.get("negRiskMarketID") or ""), "event_id": eids[0] if eids else "", "event_ids": ";".join(eids), "series_ids": ";".join(sids),
           "series_slugs": ";".join(sslugs), "resolution_source": str(m.get("resolutionSource") or "")[:200], "fee_rate": _num(fs.get("rate")),
           "fee_taker_only": int(bool(fs.get("takerOnly"))) if fs else "", "order_min_size": _num(m.get("orderMinSize")),
           "desc_sha256": hashlib.sha256(desc.encode()).hexdigest()}
    if flag_res:
        for k, rx in flag_res.items():
            out[f"flag_{k}"] = int(bool(re.search(rx, desc)))
    return out


def guarded_outcome_prices(m: dict) -> dict:
    """The separate accessor that routes ``outcomePrices`` (with the outcome labels) to D's guarded outcome file ONLY."""
    return {"market_id": str(m.get("id")), "outcome_labels": json.dumps([str(x) for x in _listish(m.get("outcomes"))]),
            "outcome_prices": json.dumps([str(x) for x in _listish(m.get("outcomePrices"))])}


def assert_whitelisted(row: dict, extra: tuple[str, ...] = ()) -> None:
    bad = [k for k in row if k not in WHITELIST_OUTPUT and k not in extra and not k.startswith("flag_")]
    if bad:
        raise Refused(f"non-whitelisted Gamma fields {bad} in a CB10 frame row")


# ---- ET clock -----------------------------------------------------------------------------------------------------------------------------


def noon_et(day: str) -> float:
    """Epoch of 12:00 America/New_York on ``day`` (16:00Z in EDT, 17:00Z in EST)."""
    y, mth, d = map(int, day.split("-"))
    return datetime(y, mth, d, 12, 0, tzinfo=ET).timestamp()


def day_add(day: str, n: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def days_between(a: str, b: str) -> list[str]:
    """Calendar days in ``[a, b)``."""
    d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
    return [(d0 + timedelta(days=i)).isoformat() for i in range((d1 - d0).days)]


def iso_week(day: str) -> str:
    y, w, _ = date.fromisoformat(day).isocalendar()
    return f"{y}-W{w:02d}"


def utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


# ---- refusals ----------------------------------------------------------------------------------------------------------------------------------


def refuse_run_id(run_id: str, allowed: str) -> str:
    if run_id in REFUSED_RUN_IDS:
        raise Refused(f"run id {run_id!r} is sealed or belongs to another batch; CB10 refuses it")
    if run_id != allowed:
        raise Refused(f"this command writes only {allowed!r}, not {run_id!r}")
    return run_id


def refuse_path(path: Path) -> Path:
    """Output guard: refuse any path with a CB1-CB9 / sealed-run / live root among its parts."""
    parts = Path(path).parts
    bad = [p for p in parts if p in REFUSED_ROOTS or p in REFUSED_RUN_IDS]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB9 / sealed / live root ({bad[0]}); CB10 refuses it")
    return Path(path)


def refuse_read(path: Path) -> Path:
    """Input guard: CB10 never reads a refused root, except the CB7-CB9 exclusion key files and their reports (ids and keys only)."""
    p = Path(path)
    if p.name in READ_ALLOWED_NAMES and p.parent.name in READ_ALLOWED_PARENTS:
        return p
    return refuse_path(p)


def read_ids_only(path: Path, sha256: str) -> set[str]:
    """Market ids (column ``market_id``) of a sha256-pinned frame / id list, possibly under a refused root (the CB9 P and K/D frame id lists): the
    pin is verified first, only the id column leaves this function."""
    from . import h5_seal  # noqa: PLC0415

    p = Path(path)
    if h5_seal.sha256_file(p) != sha256:
        raise Refused(f"pinned id list {p} sha256 differs from the pin")
    opener = gzip.open if p.name.endswith(".gz") else open
    with opener(p, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        if "market_id" not in (rd.fieldnames or []):
            raise Refused(f"{p} has no market_id column")
        return {str(r["market_id"]) for r in rd}


def require_after_t_seal(now: float, label: str, t_seal_epoch: float = T_SEAL_EPOCH) -> None:
    """No CB10 net-lane job before T_seal (2026-10-22T00:00Z). A refusal (exit 2): the spec must not be committed earlier."""
    if now < t_seal_epoch:
        raise Refused(f"{label}: refuses before T_seal {T_SEAL} (net lane only after T_seal)")


def require_disk(data_dumps: Path | None, cap_gb: float, allowance_bytes: int, *, free_path: Path | None = None, free_min_gb: float = FREE_DISK_MIN_GB,
                 free_fn: Callable[[Path], int] | None = None) -> dict:
    """Exit 75 ("pending", never "not run") if data-dumps + the job's cap > ``cap_gb`` OR root free disk - the job's cap < ``free_min_gb``. Never
    changes retention."""
    out: dict[str, Any] = {"cap_gb": cap_gb, "allowance_gb": allowance_bytes / 1024**3, "free_min_gb": free_min_gb}
    if data_dumps is not None:
        out["data_dumps_gb"] = cm.c6.require_data_dumps_room(Path(data_dumps), cap_gb, allowance_bytes / 1024**3)
    fp = Path(free_path) if free_path is not None else (Path(data_dumps) if data_dumps is not None else None)
    if fp is not None:
        probe = fp
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        free = (free_fn or (lambda q: shutil.disk_usage(q).free))(probe)
        out["free_gb"] = free / 1e9
        if (free - allowance_bytes) / 1e9 < free_min_gb:
            raise NotNow(f"root free disk {free / 1e9:.2f} GB - cap {allowance_bytes / 1e9:.3f} GB < {free_min_gb} GB (free-disk guard; pending)")
    return out


def require_freeze(spec_path: Path | None = None, *, require_committed: bool = True) -> str:
    """Analysis jobs (screen, rep) refuse before the CB10 declaration hash is committed (``model_specs/cb10_v1.json``)."""
    p = Path(spec_path or FREEZE_SPEC)
    if not p.exists():
        raise Refused(f"CB10 freeze spec {p} not found: the screens refuse before the CB10 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB10 freeze spec {p} is not committed (or differs from HEAD)")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stall_of(rdir: Path) -> dict | None:
    return c9.stall_of(Path(rdir))


def write_stall(rdir: Path, status: str, reason: str, label: str | None = None) -> dict:
    return c9.write_stall(Path(rdir), status, reason, label)


def upstream_stall(rdir: Path, upstream: Path) -> dict | None:
    """If ``upstream`` ended in a stall, write an ``upstream_not_testable`` stall here (label copied) and return it."""
    s = stall_of(upstream)
    if s is None:
        return None
    return write_stall(rdir, STALL_UPSTREAM, f"upstream {Path(upstream).name}: {s['status']}", s.get("label"))


def stage2_k(results_dir: Path) -> dict:
    """The Stage-2 Holm k derived from the CB10 Stage-1 results files (both required: k is fixed when the last Stage-1 result is final; else NotNow)."""
    adv = []
    for name, tests in STAGE1_RESULTS.items():
        p = Path(results_dir) / name
        if not p.exists():
            raise NotNow(f"{name} not final: the Stage-2 k is fixed when the last Stage-1 result is final")
        d = json.loads(p.read_text())
        adv += [t for t in tests if isinstance(d.get(t), dict) and d[t].get("advance") is True]
    k = len(adv)
    return {"k": k, "advanced": adv, "alpha_each": STAGE2_ALPHA / k if k else None}


def write_results_once(path: Path, doc: dict) -> str:
    return c9.write_results_once(Path(path), doc)


# ---- rules file --------------------------------------------------------------------------------------------------------------------------------


def _mods():
    return [importlib.import_module(f".{n}", __package__) for n in ("cb10_dlad", "cb10_brk")]


def common_declared() -> dict:
    return {"t_seal": T_SEAL, "t10_hist_end": T10_HIST_END, "j4r_window": list(J4R_WINDOW),
            "stage1": {"gate_p": GATE_P, "holm_family": list(STAGE1_HOLM_FAMILY), "batch_holm_k1": BATCH_HOLM_K1, "batch_holm_alpha": BATCH_HOLM_ALPHA1, "by_q": BY_Q,
                       "by_family": "battery2.cumulative_count() at the run (triage only)"},
            "stage2": {"alpha": STAGE2_ALPHA, "rule": "one Holm over every CB10 test reaching Stage 2, each in its Stage-1 direction (D2 net > 0); k fixed when the last Stage-1 result is final; early finishers at alpha/k"},
            "uncertainty": {"n_boot": N_BOOT, "seed_boot": SEED_BOOT, "n_wild": N_WILD, "min_units": MIN_UNITS, "min_clusters": MIN_CLUSTERS, "top_drop": TOP_DROP,
                            "small_g": f"cb2_weather.small_g_pvalue per way (G >= {G_CR1} CR1 normal; {G_CR2} <= G < {G_CR1} CR2 t(G-1) and Webb wild); p = max over the declared ways",
                            "week_way": f"ISO week of the resolution date; G < {G_CR2} -> the week way leaves the max and the leave-one-week-out sign rule binds",
                            "estimators": "slopes and weighted contrasts are tested as the clustered mean of their influence pseudo-values (v_i = estimate + IF_i), which reproduces the cluster sandwich"},
            "placebos": {"seeds": PLACEBO_SEEDS, "draws": PLACEBO_DRAWS, "max_advance_rate": PLACEBO_MAX_ADVANCE, "gdp_seed": SEED_GDP},
            "counting": {"kinds": ["cb10_test", "cb10_replication", "cb10_descriptive"], "count_line": "ml_explain, source creative_batch_10:<D|B>, n_tests = 1 per test",
                         "not_testable": "counted with p = 1", "exit_75": "pending: no trials line"},
            "refused_roots": list(REFUSED_ROOTS), "refused_run_ids": list(REFUSED_RUN_IDS), "read_allowed_names": list(READ_ALLOWED_NAMES),
            "read_allowed_parents": list(READ_ALLOWED_PARENTS), "output_roots": list(ALLOWED_OUTPUT_ROOT_PARTS),
            "exclusion": {"base": "CB9 q0182 exclusion_keys.csv.gz (sha256 pinned)", "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE, "own_seal_copies": list(OWN_SEAL_COPIES),
                          "absent_pins": "a pinned frame / seal copy not present at q0201 is recorded 'absent at q0201'"},
            "gamma_whitelist": {"keep": list(GAMMA_KEEP), "forbidden": list(GAMMA_FORBIDDEN), "output_columns": list(WHITELIST_OUTPUT),
                                "outcome_prices": "routed by guarded_outcome_prices() to D's outcomes_guarded.csv.gz only"},
            "stall": {"statuses": list(STALL_STATUSES), "exit": 0, "census": "copies the label", "screens": "p = 1, testable false", "results": "write-once"},
            "stage2_k": {"results": {k: list(v) for k, v in STAGE1_RESULTS.items()}, "rule": "k = number of Stage-1 advances, derived from both results files"},
            "disk": {"data_dumps_cap_gb": DATA_DUMPS_CAP_GB, "free_disk_min_gb": FREE_DISK_MIN_GB, "total_output_cap_gb": TOTAL_OUTPUT_CAP_GB,
                     "exit_75": "pending (never 'not run'); the queue's 48-tempfail failure is re-queued under a new id"}}


def common_rule_funcs() -> tuple:
    return (whitelist_market, guarded_outcome_prices, assert_whitelisted, noon_et, iso_week, refuse_run_id, refuse_path, refuse_read, read_ids_only,
            require_after_t_seal, require_disk, upstream_stall, stage2_k, batch_holm_label, cluster_p, cluster_p_d, leave_one_out_sign, slope_pseudo, ols_slope, contrast_pseudo,
            placebo_advance_rate, exclusion_keys, drop_by_keys, common_declared, c9.holm, c9.top_k_drop_mask, c9.cluster_bootstrap_means)


def rules_doc() -> dict:
    funcs = list(common_rule_funcs())
    declared = {}
    for mod in _mods():
        funcs += list(mod.rule_funcs())
        declared[mod.__name__.rsplit(".", 1)[-1]] = mod.declared()
    seen: set[int] = set()
    funcs = [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]
    src = "\n".join(inspect.getsource(f) for f in funcs)
    return {"rules_version": RULES_VERSION, "declared": declared, "common": common_declared(),
            "disk": {"data_dumps_cap_gb_default": DATA_DUMPS_CAP_GB, "free_disk_min_gb": FREE_DISK_MIN_GB, "headroom_exit": cm.TEMPFAIL_EXIT,
                     "disk_budget_exit": cm.DISK_BUDGET_EXIT, "refusal_exit": cm.REFUSED_EXIT},
            "wallet": {"read": False, "note": "no CB10 job reads or stores a wallet field (no HMAC key needed)"},
            "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
            "func_sources_sha256": {f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}}


def rules_file_doc() -> dict:
    d = json.loads(json.dumps(rules_doc(), sort_keys=True, default=str))
    return {**d, "rules_sha256": cm.sha_obj(d)}


def write_rules(path: Path | None = None) -> Path:
    path = Path(path or RULES_FILE)
    want = rules_file_doc()
    if path.exists() and json.loads(path.read_text()) != want:
        raise Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(path: Path | None = None, *, require_committed: bool = True) -> str:
    """Refuse (exit 2) unless the rules file equals the code's. Returns ``rules_sha256``."""
    path = Path(path or RULES_FILE)
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
    want = rules_file_doc()
    if doc != want:
        raise Refused(f"rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]


# ---- trials ------------------------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb10_descriptive`` line (EXCLUDE, counts 0): smoke, census, gates, strata, variants."""
    rec = {"kind": "cb10_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_10:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_test(family: str, tid: str, result: dict, *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST,
             results_sha256: str = "", placebo: dict | None = None, data_role: str | None = None) -> None:
    """One ``cb10_test`` / ``cb10_replication`` line (EXCLUDE), one placebo line (counts 0) and the count line ``ml_explain`` (source
    ``creative_batch_10:<family>``, ``n_tests`` = 1). A test behind a failed or unknown gate is counted with p = 1. Exit 75 never reaches here."""
    if family not in ("D", "B"):
        raise Refused(f"unknown CB10 count family {family!r}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb10_replication" if replication else "cb10_test"
    p = result.get("p", 1.0)
    if not result.get("testable", True) or p is None:
        p = 1.0
    base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_10", "hypothesis": tid, "family": family, "results_sha256": results_sha256,
            **({"data_role": data_role} if data_role else {})}
    provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                             "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
    if placebo:
        provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": placebo.get("note", "placebo"),
                                 "advance_rate": placebo.get("advance_rate"), "n_draws": placebo.get("n_draws"), "n_tests": 0}, tp)
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_10:{family}", "dataset": "creative_batch_10",
                             "n_tests": 1, "n_tests_by_family": {f"cb10_{family}": 1}, "hypothesis": tid, "replication": bool(replication),
                             "advanced": [tid] if result.get("advance") else [], "results_sha256": results_sha256, **({"data_role": data_role} if data_role else {}),
                             "note": "CB10 count line: one test (a test behind a failed gate is still counted, p = 1)"}, tp)


# ---- statistics --------------------------------------------------------------------------------------------------------------------------------


def batch_holm_label(pvals: dict[str, float | None], family: tuple[str, ...] = STAGE1_HOLM_FAMILY, alpha: float = BATCH_HOLM_ALPHA1) -> dict:
    """Stage-1 batch-Holm label at one-sided alpha 0.01 over the FIXED family (D1, B1, B2; k1 = 3). Not run / not testable -> p = 1."""
    extra = [k for k in pvals if k not in family]
    if extra:
        raise Refused(f"batch-Holm: {extra} are not in the fixed Stage-1 family {family}")
    full = {k: (1.0 if pvals.get(k) is None else float(pvals[k])) for k in family}
    return {"k": len(family), "alpha": alpha, "tests": c9.holm(full, alpha), "not_run_as_p1": [k for k in family if pvals.get(k) is None]}


def cluster_p(v, clusters: dict[str, Any], *, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared ways (CB9 small-G rule per way: G < 15 not testable, 15-29 CR2 + Webb). Testable needs
    >= 100 units, every way testable, and >= 30 clusters in the finest declared way (the design's ">= 30 clusters"; open item)."""
    from . import cb2_weather as w  # noqa: PLC0415

    v = np.asarray(v, float)
    if len(v) < 2:
        return {"n": int(len(v)), "mean": float(v.mean()) if len(v) else math.nan, "testable": False, "p": 1.0, "ways": {}}
    ways = {name: w.small_g_pvalue(v, np.asarray(cl).astype(str), sign=1, n_wild=n_wild, seed=seed, alpha=alpha) for name, cl in clusters.items()}
    testable = bool(len(v) >= MIN_UNITS and all(r["testable"] for r in ways.values()) and max((r["G"] for r in ways.values()), default=0) >= MIN_CLUSTERS)
    p = max((r["p"] for r in ways.values()), default=1.0) if testable else 1.0
    return {"n": int(len(v)), "mean": float(v.mean()), "testable": testable, "p": float(p), "ways": {k: {"G": r["G"], "p": r["p"], "method": r["method"]} for k, r in ways.items()}}


def leave_one_out_sign(groups: np.ndarray, estimator: Callable[[np.ndarray], float], sign: float) -> dict:
    """Leave-one-group-out estimates (``estimator`` takes a keep-mask); holds iff every estimate is finite and keeps ``sign``."""
    g = np.asarray(groups).astype(str)
    est = {}
    for k in sorted(set(g.tolist())):
        est[k] = float(estimator(g != k))
    holds = bool(est) and all(math.isfinite(x) and np.sign(x) == np.sign(sign) and x != 0 for x in est.values())
    return {"n_groups": len(est), "min": min(est.values()) if est else None, "max": max(est.values()) if est else None, "holds": holds}


def cluster_p_d(v, clusters: dict[str, Any], week: Any, estimator: Callable[[np.ndarray], float] | None = None, *, seed: int = SEED_BOOT, n_wild: int = N_WILD,
                alpha: float | None = None) -> dict:
    """D's p: the max over the date and asset-date ways (CB9 small-G rule) and the ISO-week way under the CB10 rule: G >= 30 CR1; 15 <= G < 30
    CR2 + Webb; G < 15 the week way leaves the max and the leave-one-week-out sign rule binds (``estimator`` re-estimates on a keep-mask; default
    the mean of ``v``)."""
    from . import cb2_weather as w  # noqa: PLC0415

    v = np.asarray(v, float)
    base = cluster_p(v, clusters, seed=seed, n_wild=n_wild, alpha=alpha)
    wk = np.asarray(week).astype(str)
    G = len(set(wk.tolist()))
    est = estimator or (lambda keep: float(v[keep].mean()) if keep.any() else math.nan)
    if G >= G_CR2 and len(v) >= 2:
        r = w.small_g_pvalue(v, wk, sign=1, n_wild=n_wild, seed=seed, alpha=alpha)
        p = max(base["p"], r["p"]) if base["testable"] and r["testable"] else 1.0
        return {**base, "testable": bool(base["testable"] and r["testable"]), "p": float(p), "week": {"G": G, "p": r["p"], "method": r["method"], "in_max": True},
                "week_rule_holds": True}
    loo = leave_one_out_sign(wk, est, est(np.ones(len(v), bool)) if len(v) else 0.0) if len(v) else {"holds": False}
    return {**base, "week": {"G": G, "in_max": False, "rule": "G < 15: leave-one-week-out sign rule binds", "leave_one_week_out": loo}, "week_rule_holds": bool(loo.get("holds"))}


def ols_slope(y, x, keep=None) -> float:
    y, x = np.asarray(y, float), np.asarray(x, float)
    if keep is not None:
        y, x = y[keep], x[keep]
    if len(x) < 3:
        return math.nan
    xc = x - x.mean()
    sxx = float((xc * xc).sum())
    return float((xc * (y - y.mean())).sum() / sxx) if sxx > 0 else math.nan


def slope_pseudo(y, x, w=None) -> tuple[np.ndarray, float]:
    """(pseudo-values, slope) of the OLS slope of ``y`` on ``x`` with intercept (optionally WLS with weights ``w``): v_i = b + n w_i (x_i - x_w) e_i /
    S_xx, so mean(v) = b and the clustered variance of v is the cluster sandwich of b."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    wt = np.ones_like(x) if w is None else np.asarray(w, float)
    n = len(x)
    if n < 3 or wt.sum() <= 0:
        return np.full(n, math.nan), math.nan
    xm, ym = (wt * x).sum() / wt.sum(), (wt * y).sum() / wt.sum()
    xc = x - xm
    sxx = float((wt * xc * xc).sum())
    if sxx <= 0:
        return np.full(n, math.nan), math.nan
    b = float((wt * xc * (y - ym)).sum() / sxx)
    e = (y - ym) - b * xc
    return b + n * wt * xc * e / sxx, b


def contrast_pseudo(values, arm: list[str], pair: list[Any], weights: dict[Any, float]) -> tuple[np.ndarray, float, dict]:
    """(pseudo-values, estimate, per-pair contrasts) of ``sum_L w_L (mean real_L - mean pseudo_L)`` over units with ``arm`` in {real, pseudo} and pair
    ``L``; units of pairs with ``w_L = 0`` (or missing) get pseudo-value equal to the estimate (no influence) and are reported, not dropped here."""
    vals = np.asarray(values, float)
    arm_a, pair_a = np.asarray(arm).astype(str), np.asarray(pair, dtype=object)
    n = len(vals)
    cl, est = {}, 0.0
    groups = {}
    for L, wl in weights.items():
        if not wl:
            continue
        r = (pair_a == L) & (arm_a == "real")
        q = (pair_a == L) & (arm_a == "pseudo")
        if r.sum() == 0 or q.sum() == 0:
            cl[L] = None
            continue
        mr, mq = float(vals[r].mean()), float(vals[q].mean())
        cl[L] = mr - mq
        est += wl * (mr - mq)
        groups[L] = (r, q, mr, mq, wl)
    v = np.full(n, est)
    for _L, (r, q, mr, mq, wl) in groups.items():
        v[r] += wl * n / r.sum() * (vals[r] - mr)
        v[q] -= wl * n / q.sum() * (vals[q] - mq)
    return v, float(est), cl


def placebo_advance_rate(draw_ps: list[float], gate_p: float = GATE_P) -> dict:
    n = len(draw_ps)
    adv = sum(1 for p in draw_ps if p is not None and p < gate_p)
    rate = adv / n if n else 1.0
    return {"n_draws": n, "n_advance": adv, "advance_rate": rate, "holds": bool(n > 0 and rate <= PLACEBO_MAX_ADVANCE)}


def rank(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


# ---- q0201 exclusion keys ----------------------------------------------------------------------------------------------------------------------


def drop_by_keys(rows: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]], *, use_series: bool = True) -> tuple[list[dict], dict]:
    """Drop rows whose id or any key (event ids, neg-risk market id, and series ids unless ``use_series`` is False) is excluded."""
    kept, n = [], {"kept": 0, "id": 0, "event": 0, "neg_risk_market": 0, "series": 0}
    for r in rows:
        if str(r["market_id"]) in excl_ids:
            n["id"] += 1
            continue
        hit = None
        if any(e and e in excl_keys["event"] for e in str(r.get("event_ids", "")).split(";")):
            hit = "event"
        elif r.get("neg_risk_market_id") and r["neg_risk_market_id"] in excl_keys["neg_risk_market"]:
            hit = "neg_risk_market"
        elif use_series and any(s and s in excl_keys["series"] for s in str(r.get("series_ids", "")).split(";")):
            hit = "series"
        if hit:
            n[hit] += 1
            continue
        n["kept"] += 1
        kept.append(r)
    return kept, n


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, cb9_keys_path: Path, cb9_keys_sha256: str, seals_dir: Path | None = None,
                   extra_pins: list[dict] | None = None, is_committed: Callable[[Path], bool] | None = None, rps: float = 2.0,
                   disk_cap: int = int(0.005 * 1024**3), budget_min: float | None = None, now: float | None = None, sleep=None, live_check=None,
                   should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] | None = None, snapshot_root: Path | None = None,
                   health_check=None, data_dumps: Path | None = None, data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0201. CB9 q0182's key file (sha256 pinned) plus, by Gamma id lookup (<= 50 ids per request, ``closed=true`` retry, parse guard keeping ids and
    keys only), every id in the pinned CB9 P and K/D frame id lists (``extra_pins`` ``{"name","path","sha256"}``; a pin whose file is absent is
    recorded "absent at q0201") and in every seal copy committed now that q0182 did not read (CB10's own copy excluded). More than 2% of ALL exclusion
    ids without metadata -> ``disjointness_unverified`` (D1, B1, B2 not testable, counted)."""
    import time  # noqa: PLC0415

    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    out_root, seals_dir = refuse_path(Path(out_root)), Path(seals_dir or SEALS_DIR)
    got = h5_seal.sha256_file(refuse_read(Path(cb9_keys_path))) if Path(cb9_keys_path).exists() else None
    if got != cb9_keys_sha256:
        raise Refused(f"CB9 key file {cb9_keys_path} sha256 {got} != pinned {cb9_keys_sha256}")
    cb9_ids, _sets, cb9_rep, _ = c9.load_exclusion_keys(Path(cb9_keys_path))
    require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    read_by_cb9 = {(n, s) for n, s in (cb9_rep.get("seal_copies_sha256") or {}).items()}
    seal_ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=OWN_SEAL_COPIES, is_committed=is_committed)
    new_from_seals = sorted(n for n, s in shas.items() if (n, s) not in read_by_cb9)
    extra_ids: set[str] = set()
    pins_used, pins_absent = [], []
    for pin in extra_pins or []:
        p = Path(pin["path"])
        if not p.exists():
            pins_absent.append({"name": pin["name"], "status": "absent at q0201"})
            continue
        extra_ids |= read_ids_only(p, pin["sha256"])
        pins_used.append({"name": pin["name"], "sha256": pin["sha256"]})
    new_ids = (seal_ids | extra_ids) - cb9_ids
    fr = cm.open_run(out_root, "exclusion_run10", transport, allowed_run_id="exclusion_run10", kind="cb10_exclusion_keys", label="CB10 exclusion keys",
                     params={"cb9_keys_sha256": cb9_keys_sha256, "n_cb9_ids": len(cb9_ids), "n_new_ids": len(new_ids), "seal_copies_used": used, "seal_copies_sha256": shas,
                             "seal_copies_not_in_cb9": new_from_seals, "seal_copies_skipped": skipped, "extra_pins": pins_used, "pins_absent": pins_absent,
                             "evidence_role": EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep or time.sleep,
                     live_check=live_check, wall_clock=wall_clock or time.time, snapshot_root=snapshot_root, health_check=health_check)
    rep_new, stopped = c6.exclusion_stage(fr, new_ids, should_stop)
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep_new is not None
    rows = []
    with gzip.open(Path(cb9_keys_path), "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in csv.DictReader(fh)]
    with gzip.open(fr.rdir / "exclusion_keys.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in csv.DictReader(fh)]
    out_dir = Path(out_root)
    keys_out = out_dir / "exclusion_keys.csv.gz"
    out_dir.mkdir(parents=True, exist_ok=True)
    keys_out.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), sorted(rows)))
    n_all = int(cb9_rep.get("n_ids", len(cb9_ids))) + rep_new["n_ids"]
    n_missing = int(cb9_rep.get("n_missing", 0)) + rep_new["n_missing"]
    share = n_missing / n_all if n_all else 1.0
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": UNVERIFIED if share > MAX_UNVERIFIED_KEY_SHARE else "verified", "cb9_keys_sha256": cb9_keys_sha256,
           "cb9_report": {k: cb9_rep.get(k) for k in ("n_ids", "n_missing", "disjointness")}, "new": rep_new, "seal_copies_used": used, "seal_copies_sha256": shas,
           "seal_copies_not_in_cb9": new_from_seals, "seal_copies_skipped": skipped, "extra_pins": pins_used, "pins_absent": pins_absent,
           "keys_sha256": h5_seal.sha256_file(keys_out), "built_utc": cm.iso(time.time())}
    (out_dir / EXCLUSION_REPORT_NAME).write_text(json.dumps(rep, indent=1, sort_keys=True))
    status = UNVERIFIED if rep["disjointness"] == UNVERIFIED else EXCLUSION_KEYS_COMPLETE
    m = fr.manifest(None, {"exclusion_report": {k: rep[k] for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys_sha256")}, "status": status, "complete": True})
    m["status"] = status
    return m


def load_exclusion_keys(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    """(ids, key sets, report, sha256) of the CB10 key file (or a CB7-CB9 one), verified against its report."""
    return c9.load_exclusion_keys(Path(keys_path)) if Path(keys_path).parent.name in READ_ALLOWED_PARENTS else _load_own_keys(Path(keys_path))


def _load_own_keys(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    keys_path = refuse_path(Path(keys_path))
    rep_path = keys_path.with_name(EXCLUSION_REPORT_NAME)
    if not keys_path.exists() or not rep_path.exists():
        raise Refused(f"exclusion key files {keys_path} / {rep_path.name} missing")
    rep = json.loads(rep_path.read_text())
    sha = h5_seal.sha256_file(keys_path)
    if rep.get("keys_sha256") != sha:
        raise Refused(f"{keys_path} sha256 {sha} != report {rep.get('keys_sha256')}; refusing")
    ids: set[str] = set()
    with gzip.open(keys_path, "rt", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            ids.add(str(r["market_id"]))
    return ids, c6.load_key_sets(keys_path), rep, sha


def key_rows(keys_path: Path) -> list[dict]:
    """Rows of a key file (id, found, event ids, neg-risk id, series ids): used by D's series-date rule to find excluded ids of the ladder series."""
    with gzip.open(Path(keys_path), "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
