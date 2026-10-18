# ruff: noqa: E501
"""CB11 shared parts (docs/research_lab/CREATIVE_BATCH_11.md sections 1.3, 1.4, 2.3, 2.5, 2.8, CB11-F).

Constants and refusal lists (outputs AND inputs), the code-derived rules file ``seals/cb11_rules.json`` (function SOURCE hashed, committed before the first
read; no wallet field and no ``side`` field is read by any CB11 job), the disk guards (data-dumps cap AND root free disk, exit 75 = "pending"), the trial-line
helpers (``cb11_test`` / ``cb11_replication`` / ``cb11_descriptive`` are EXCLUDE in ``battery2.KIND_RULES``; the ``ml_explain`` count line carries
``n_tests``), the fixed-k batch-Holm label (k1 = 6), the freeze gate (W part and P/A part hashed separately), the guarded-file accessors, the
resumable exclusion-key build (q0221) and the CB11 stall vocabulary (shared with CB9/CB10). No outcome analysis lives here. Reuses
``cb8_common`` / ``cb9_common`` / ``cb10_common`` machinery.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib
import inspect
import json
import math
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import cb10_common as c10
from . import provenance

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

RULES_VERSION = "cb11-rules-v2"
SEALS_DIR = cm.SEALS_DIR
RULES_FILE = SEALS_DIR / "cb11_rules.json"
DATA_DUMPS = cm.DATA_DUMPS
CB11_DIR = DATA_DUMPS / "research_lab" / "creative_batch11"
HIST_ROOT = cm.HIST_ROOT
H11_WPRINTS = "h11_wprints"
H11_POL = "h11_pol"
H11_ATTN = "h11_attn"
SMOKE_DEFAULT = CB11_DIR / "smoke.json"
EXCLUSION_KEYS_DEFAULT = CB11_DIR / "exclusion_keys.csv.gz"
EXTERNAL_IDS_DIR = CB11_DIR / "external_ids"  # staged C1 / T5 id lists (market_id column), copied from the arepo-data release by the orchestrator (read-only)
FREEZE_SPEC = Path(__file__).resolve().parent / "model_specs" / "cb11_v1.json"
EXCLUSION_REPORT_NAME = c9.EXCLUSION_REPORT_NAME
T11_HIST_END = "2026-10-01T00:00:00Z"
T11_HIST_END_EPOCH = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
NY = ZoneInfo("America/New_York")
SMOKE_VERSION = "cb11-smoke-v1"

# Disk (design 2.8): data-dumps + the job's cap <= 40 GiB (ops convention) AND root free disk - the job's cap >= 4.5 GB.
DATA_DUMPS_CAP_GB = 40.0
FREE_DISK_MIN_GB = 4.5
TOTAL_OUTPUT_CAP_GB = 0.25

STAGE1_HOLM_FAMILY = ("W1", "W2", "P1", "P2", "A1", "A2")
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 6, fixed
BATCH_HOLM_ALPHA1 = 0.01
STAGE2_ALPHA = 0.05
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 1111
N_WILD = 9999
PLACEBO_SEEDS = {"W1_permute": 11101, "P1_copula": 11102, "A1_labelswap": 11103, "spare_4": 11104, "spare_5": 11105, "spare_6": 11106, "spare_7": 11107,
                 "spare_8": 11108, "spare_9": 11109, "spare_10": 11110, "spare_11": 11111, "spare_12": 11112}
SEED_GPP = 11120
SEED_GWC = 11121
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
GATE_P = 0.01
MIN_UNITS = 100
MIN_CLUSTERS = 30
TOP_DROP = 5
EVIDENCE_ROLE_HIST = "exploratory_historical"
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
OWN_SEAL_COPIES = ("cb11_w_hold_SEAL.json", "cb11_wprints_holdout_SEAL.json", "cb11_pol_holdout_SEAL.json", "cb11_attn_holdout_SEAL.json")
H8_TAIL_B_KEYS_SHA256 = "ce7fe2a4efca4320e1aa289075f19b06543215b5d089873147ae0d522a369a8d"  # history/h8_tail_b/exclusion_keys.csv.gz, read-only host inspection 2026-10-17
H2_FRAME_SHA256 = "fd0898f291f20ba1f219ecb89a9c3961cf2f94d8bc16e0a1544b38f3500674b8"  # history/h2_main/frame.csv.gz
H3_FRAME_SHA256 = "2267dbd496d918973c73ea2f17095cd1a462e5ef385c7f5a737652f7e312ab71"  # history/h3_power/frame.csv.gz
PENDING = "pending"
# Rules parts (design 1.4 as amended in section 11, item B1): ``cb11_rules.json`` (v2) carries part "W" = common + smoke + W rule functions, hashed and committed
# first. Part "PA" is NOT hashed here: P / A rules live in their own file (``cb11_pa_rules.json``, written by the P / A runner commands with their own
# declaration hash), so no P / A code is imported by, or can alter, any W verification.
RULE_PARTS = ("W", "PA")
W_RULE_MODULES = ("cb11_w", "cb11_smoke")
PA_RULES_FILE_NAME = "cb11_pa_rules.json"
PIN_UNSET = "TODO-COORDINATOR"  # a pin the coordinator fills from a read-only `sha256sum` on the host; q0221 refuses (exit 2) while a mandatory pin is unset
H2_SAMPLE_SHA256 = "77a15bd96bcd17c923e90e3e214874cad8df9ed4cd66eb6145cc8922c28954ec"  # history/h2_main/sample.csv.gz (mandatory exclusion source, B4)
H3_SAMPLE_SHA256 = "f8e1a7bbd16d57206fcd45c502263d2b7ceb40b22108e248c613d5148476004d"  # history/h3_power/sample.csv.gz (mandatory exclusion source, B4)
MANDATORY_SAMPLE_PINS = {"h2_main/sample.csv.gz": H2_SAMPLE_SHA256, "h3_power/sample.csv.gz": H3_SAMPLE_SHA256}

STALL_NOT_RUN_SOURCE = c9.STALL_NOT_RUN_SOURCE
STALL_DISJOINTNESS = c9.STALL_DISJOINTNESS
STALL_UPSTREAM = c9.STALL_UPSTREAM
STALL_STATUSES = c9.STALL_STATUSES
# Stage-1 results files and the tests each holds; each Stage-1 advance triggers exactly one Stage-2 test (its own "-rep").
STAGE1_RESULTS = {"results_W.json": ("W1", "W2"), "results_P.json": ("P1", "P2"), "results_A.json": ("A1", "A2")}
STAGE2_TESTS_PER_ADVANCE = {"W1": 1, "W2": 1, "P1": 1, "P2": 1, "A1": 1, "A2": 1}

# Inputs CB11 never reads (design 1.1 last three rows, 1.3). h2_main and h3_power are NOT in the plain refusal list of this module: their ``frame.csv.gz`` is the
# W population (metadata columns, sha256 pinned) and is opened only by ``cb11_w.read_frame_rows``; every other file under them stays refused.
REFUSED_RUN_IDS = tuple(r for r in c10.REFUSED_RUN_IDS if r not in ("h2_main", "h3_power")) + ("h10_dlad", "h10_brk", "dlad_frame", "brk_frame", "brk_prints", "deribit",
                                                                                              "exclusion_run10", "halfday")
FRAME_RUN_IDS = ("h2_main", "h3_power")
FRAME_ALLOWED_FILES = ("frame.csv.gz", "manifest.json", "frame_partial.jsonl", "frame_partial.jsonl.gz")
REFUSED_ROOTS = tuple(c10.REFUSED_ROOTS) + ("creative_batch10", "snapshots", "book_sweeps", "cb10_extract", "cb11_extract")
# Id-column readers (field-restricted, ids only) may open files under refused roots: the sampled / sealed sets named in design 1.3.
ID_SOURCES = (("h1_first", "sample.csv.gz"), ("h2_main", "sample.csv.gz"), ("h3_power", "sample.csv.gz"), ("h5_cb1", "sample.csv.gz"),
              ("h5_cb1_ladders", "events.jsonl.gz"), ("h6_weather", "events.jsonl.gz"), ("h7_cb4_era", "frame.csv.gz"), ("h7_cb4_series", "walk_events.jsonl.gz"),
              ("h8_tail", "sample.csv.gz"), ("h8_tail_b", "sample.csv.gz"), ("h8_text", "frame.csv.gz"), ("h8_geo", "frame.csv.gz"))
CB8_FRAME_GLOB = "*/frame.csv.gz"  # creative_batch8/<run>/frame.csv.gz, if any exists at q0221
EXTERNAL_ID_FILES = ("c1_sample_ids.csv.gz", "t5_frame_ids.csv.gz")
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch11", H11_WPRINTS, H11_POL, H11_ATTN)
GUARDED_ALLOWED_JOBS = ("screen-W", "rep-W", "screen-P", "rep-P")
LOOKUP_PER_REQUEST = 50
EXCLUSION_RUN = "exclusion_run11"


def _num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def rank(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


def utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def ny_clock(epoch: float) -> tuple[int, int]:
    """(hour, weekday Monday=0) of ``epoch`` in America/New_York (DST-aware)."""
    d = datetime.fromtimestamp(epoch, UTC).astimezone(NY)
    return d.hour, d.weekday()


# ---- refusals ----------------------------------------------------------------------------------------------------------------------------------


def refuse_run_id(run_id: str, allowed: str) -> str:
    if run_id in REFUSED_RUN_IDS or run_id in FRAME_RUN_IDS:
        raise Refused(f"run id {run_id!r} is sealed or belongs to another batch; CB11 refuses it")
    if run_id != allowed:
        raise Refused(f"this command writes only {allowed!r}, not {run_id!r}")
    return run_id


def refuse_path(path: Path) -> Path:
    """Output guard: refuse any path with a CB1-CB10 / sealed-run / live root among its parts (h2_main and h3_power included: nothing is ever written there)."""
    parts = Path(path).parts
    bad = [p for p in parts if p in REFUSED_ROOTS or p in REFUSED_RUN_IDS or p in FRAME_RUN_IDS]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB10 / sealed / live root ({bad[0]}); CB11 refuses it")
    return Path(path)


def refuse_read(path: Path) -> Path:
    """Input guard (plain readers): the same list. The W frame reader and the id-column readers are the only code that opens a refused-root file."""
    return refuse_path(Path(path))


def require_output_root(path: Path) -> Path:
    """Data jobs write only under creative_batch11 / h11_wprints / h11_pol / h11_attn."""
    refuse_path(Path(path))
    if not any(p in ALLOWED_OUTPUT_ROOT_PARTS for p in Path(path).parts):
        raise Refused(f"CB11 writes only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return Path(path)


def require_after(now: float, epoch: float, label: str) -> None:
    """A time gate: 'not yet' is exit 75 (NotNow, pending, no trials line), never exit 2."""
    if now < epoch:
        raise NotNow(f"{label}: not before {datetime.fromtimestamp(epoch, UTC):%Y-%m-%dT%H:%MZ} (pending)")


def require_disk(data_dumps: Path | None, cap_gb: float, allowance_bytes: int, *, free_path: Path | None = None, free_min_gb: float = FREE_DISK_MIN_GB, free_fn=None) -> dict:
    """Exit 75 ("pending", never "not run") if data-dumps + the job's cap > ``cap_gb`` OR root free disk - the job's cap < ``free_min_gb``."""
    return c10.require_disk(data_dumps, cap_gb, allowance_bytes, free_path=free_path, free_min_gb=free_min_gb, free_fn=free_fn)


def require_freeze(part: str, spec_path: Path | None = None, *, require_committed: bool = True) -> str:
    """Analysis jobs (screen, rep) refuse before the CB11 declaration hash is committed (``model_specs/cb11_v1.json``). The W part and the P/A part are
    hashed separately so the W freeze never waits on P/A data; returns the sha256 of the requested part."""
    if part not in ("W", "PA"):
        raise Refused(f"unknown freeze part {part!r}")
    p = Path(spec_path or FREEZE_SPEC)
    if not p.exists():
        raise Refused(f"CB11 freeze spec {p} not found: the screens refuse before the CB11 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB11 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"CB11 freeze spec {p} unreadable") from exc
    if not isinstance(doc, dict) or part not in doc:
        raise Refused(f"CB11 freeze spec {p} has no {part!r} part")
    return hashlib.sha256(json.dumps(doc[part], sort_keys=True, default=str).encode()).hexdigest()


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


def manifest_complete(rdir: Path, statuses: tuple[str, ...]) -> dict | None:
    """The manifest of a finished fetch (complete, not stopped, status in ``statuses``), else None. Census and screens refuse an incomplete one."""
    mp = Path(rdir) / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("stopped") is None and prior.get("status") in statuses:
        return prior
    return None


def require_complete(rdir: Path, statuses: tuple[str, ...], label: str) -> dict:
    m = manifest_complete(rdir, statuses)
    if m is None:
        raise NotNow(f"{label} is not finished (fetch manifest incomplete); pending, never analysed partially")
    return m


def verify_fetch(rdir: Path, statuses: tuple[str, ...], label: str) -> dict:
    """A finished fetch whose manifest is complete AND whose recorded files still hash to the manifest (N5: screens and reps re-check, not only the census).
    Extra files (the seal, drops, the access log) are tolerated here; ``seal_holdout`` / ``verify_holdout_seal`` own those checks."""
    from . import h5_seal  # noqa: PLC0415

    man = require_complete(rdir, statuses, label)
    want = man.get("file_sha256")
    if not isinstance(want, dict) or not want:
        raise Refused(f"{label}: manifest has no file_sha256; refusing")
    for rel, sha in sorted(want.items()):
        fp = Path(rdir) / rel
        if not fp.is_file():
            raise Refused(f"{label}: file missing at verification: {rel}")
        if h5_seal.sha256_file(fp) != sha:
            raise Refused(f"{label}: file sha256 differs from the manifest: {rel}")
    return man


def stage2_k(results_dir: Path, *, own: str | None = None) -> dict:
    """The Stage-2 Holm k derived from the CB11 Stage-1 results files. Every Stage-1 advance triggers exactly one Stage-2 test (its own ``-rep``).
    ``own=None``: all three files are required (k is fixed when the last Stage-1 result is final; else NotNow). ``own="W"|"P"|"A"`` (a family's rep job, N7): only
    that family's file is required; every test of a family whose file is not yet final is counted as advancing (``assumed_pending``) - k can only be too large,
    so the threshold alpha / k is at least as strict as the final one, and the rep stays judged at it (never loosened later)."""
    adv: list[str] = []
    assumed: list[str] = []
    for name, tests in STAGE1_RESULTS.items():
        p = Path(results_dir) / name
        fam = name.removeprefix("results_").removesuffix(".json")
        if not p.exists():
            if own is None or fam == own:
                raise NotNow(f"{name} not final: the Stage-2 k is fixed when the last Stage-1 result is final" if own is None else f"{name} (the family's own Stage-1 result) is not final")
            assumed += list(tests)
            continue
        d = json.loads(p.read_text())
        adv += [t for t in tests if isinstance(d.get(t), dict) and d[t].get("advance") is True]
    k = sum(STAGE2_TESTS_PER_ADVANCE.get(t, 1) for t in [*adv, *assumed])
    return {"k": k, "advanced": adv, "assumed_pending": assumed, "alpha_each": STAGE2_ALPHA / k if k else None}


def write_results_once(path: Path, doc: dict) -> str:
    return c9.write_results_once(Path(path), doc)


def batch_holm_label(pvals: dict[str, float | None], family: tuple[str, ...] = STAGE1_HOLM_FAMILY, alpha: float = BATCH_HOLM_ALPHA1) -> dict:
    """Stage-1 batch-Holm label at one-sided alpha 0.01 over the FIXED family (W1, W2, P1, P2, A1, A2; k1 = 6). Not run / not testable -> p = 1."""
    extra = [k for k in pvals if k not in family]
    if extra:
        raise Refused(f"batch-Holm: {extra} are not in the fixed Stage-1 family {family}")
    full = {k: (1.0 if pvals.get(k) is None else float(pvals[k])) for k in family}
    return {"k": len(family), "alpha": alpha, "tests": c9.holm(full, alpha), "not_run_as_p1": [k for k in family if pvals.get(k) is None]}


def p_ok(p: float, alpha: float, inclusive: bool = False) -> bool:
    """Stage 1: p < alpha. Stage 2 (Holm at alpha / k, B8): p <= alpha / k (``inclusive``)."""
    return bool(p <= alpha if inclusive else p < alpha)


def cluster_p(v, clusters: dict[str, Any], *, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared cluster ways (CB10 rule, CB11 seed 1111): >= 100 units, every way testable, >= 30 clusters."""
    return c10.cluster_p(v, clusters, seed=seed, n_wild=n_wild, alpha=alpha)


def cluster_p_week(v, clusters: dict[str, Any], week: Any, *, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None) -> dict:
    """P's p: the event way plus the ISO-week way under the CB10 small-G rule (G < 15 leaves the max; the leave-one-week-out sign rule binds)."""
    return c10.cluster_p_d(v, clusters, week, seed=seed, n_wild=n_wild, alpha=alpha)


def placebo_advance_rate(draw_ps: list[float | None], gate_p: float = GATE_P) -> dict:
    return c10.placebo_advance_rate(draw_ps, gate_p)


def one_sided_boot_p(draws: np.ndarray) -> float:
    """One-sided p for 'statistic > 0' from bootstrap draws: (1 + #{draw <= 0}) / (n + 1)."""
    d = np.asarray(draws, float)
    d = d[np.isfinite(d)]
    return float((1 + np.sum(d <= 0)) / (len(d) + 1)) if len(d) else 1.0


# ---- guarded files -----------------------------------------------------------------------------------------------------------------------------


def open_guarded(path: Path, job: str, names: tuple[str, ...]) -> list[dict]:
    """Guarded files (outcomes, status, targets) are opened ONLY by screen / rep jobs (the caller checked the freeze). Reads the whole file."""
    p = Path(path)
    if p.name not in names:
        raise Refused(f"{p.name} is not a guarded file of this family")
    if job not in GUARDED_ALLOWED_JOBS:
        raise Refused(f"guarded file {p.name} may be opened only by {GUARDED_ALLOWED_JOBS}, not {job!r}")
    with gzip.open(p, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def read_csv_gz(path: Path) -> Iterator[dict]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


# ---- id-column readers (field-restricted: ids only) --------------------------------------------------------------------------------------------


def _ids_from_json(obj: Any, out: set[str], depth: int = 0) -> None:
    if depth > 6:
        return
    if isinstance(obj, dict):
        if obj.get("market_id") is not None:
            out.add(str(obj["market_id"]))
        mk = obj.get("markets")
        if isinstance(mk, list):
            for m in mk:
                if isinstance(m, dict) and m.get("id") is not None:
                    out.add(str(m["id"]))
        for v in obj.values():
            if isinstance(v, (dict, list)):
                _ids_from_json(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, (dict, list)):
                _ids_from_json(v, out, depth + 1)


def read_id_set(path: Path) -> set[str]:
    """Market ids (column ``market_id``, or the market ids nested in a JSONL record) of a sampled / sealed set; ONLY the ids leave this function. Opening a
    file under a refused run id is allowed here and nowhere else (design 1.3: id-column readers use a field-restricted accessor)."""
    p = Path(path)
    opener = gzip.open if p.name.endswith(".gz") else open
    ids: set[str] = set()
    csv.field_size_limit(10**9)
    with opener(p, "rt", encoding="utf-8", newline="") as fh:
        if ".jsonl" in p.name:
            for line in fh:
                if line.strip():
                    _ids_from_json(json.loads(line), ids)
        else:
            rd = csv.DictReader(fh)
            if "market_id" not in (rd.fieldnames or []):
                raise Refused(f"{p} has no market_id column")
            ids = {str(r["market_id"]) for r in rd}
    return ids


# ---- Gamma key lookup, closed markets first (halves the requests of c6.lookup_keys for historical ids) ------------------------------------------


def lookup_keys_closed_first(lim, ids: list[str], *, per_request: int = LOOKUP_PER_REQUEST) -> tuple[dict[str, dict], int]:
    """Gamma lookup by market id (``closed=true`` first: the ids are historical; the rest retried without it). A non-200 reply raises ``ApiError``."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    found: dict[str, dict] = {}
    retried = 0

    def ask(batch: list[str], closed: bool) -> None:
        params: dict = {"id": list(batch), "limit": per_request}
        if closed:
            params["closed"] = "true"
        status, data = lim.get(hb.GAMMA_MARKETS, params)
        if status != 200 or not isinstance(data, list):
            raise ApiError(f"gamma markets lookup status {status}")
        for m in data:
            if isinstance(m, dict) and m.get("id") is not None and str(m["id"]) in batch:
                found[str(m["id"])] = c6.key_fields(m)

    for i in range(0, len(ids), per_request):
        batch = ids[i:i + per_request]
        ask(batch, True)
        missing = [x for x in batch if x not in found]
        if missing:
            ask(missing, False)
            retried += sum(1 for x in missing if x in found)
    return found, retried


def drop_by_keys_w(rows: list[dict], excl_ids: set[str], excl_event: set[str]) -> tuple[list[dict], dict]:
    """W key rule (design 1.3): drop by market id and event id only (the frames carry no negRiskMarketID and no series id)."""
    kept, n = [], {"kept": 0, "id": 0, "event": 0}
    for r in rows:
        if str(r["market_id"]) in excl_ids:
            n["id"] += 1
        elif r.get("event_id") and str(r["event_id"]) in excl_event:
            n["event"] += 1
        else:
            n["kept"] += 1
            kept.append(r)
    return kept, n


def load_exclusion_keys(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    """(ids, key sets, report, sha256) of the CB11 key file, verified against its report."""
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


def _exclusion_stage(fr, ids: set[str], should_stop: Callable[[], bool] | None = None) -> tuple[dict | None, str | None]:
    """Resumable Gamma lookup of ``ids`` (closed-first, <= 50 per request) -> ``exclusion_keys.csv.gz`` (+ report) in the run dir. Like
    ``cb6_tail.exclusion_stage`` with the closed-first lookup."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    rdir = fr.rdir
    rep_path, keys_path = rdir / "exclusion_report.json", rdir / "exclusion_keys.csv.gz"
    if rep_path.exists():
        return json.loads(rep_path.read_text()), None
    part = rdir / "exclusion_keys_partial.jsonl"
    todo = sorted(ids)
    done: dict[int, dict] = {}
    if part.exists():
        for line in part.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["batch"]] = rec
    per = LOOKUP_PER_REQUEST
    nb = math.ceil(len(todo) / per)
    for b in range(nb):
        if b in done:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            return None, why
        batch = todo[b * per:(b + 1) * per]
        found, retried = lookup_keys_closed_first(fr.lim, batch, per_request=per)
        rec = {"batch": b, "ids": len(batch), "retried_found": retried, "found": [found[x] for x in batch if x in found]}
        with part.open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        done[b] = rec
    rows: dict[str, dict] = {}
    retried = 0
    for rec in done.values():
        retried += rec["retried_found"]
        for k in rec["found"]:
            rows[k["market_id"]] = k
    out = [[x, int(x in rows), rows[x]["event_ids"] if x in rows else "", rows[x]["neg_risk_market_id"] if x in rows else "", rows[x]["series_ids"] if x in rows else ""]
           for x in todo]
    fr.budget.write_gz_csv(keys_path, c6.KEY_COLUMNS, out)
    n_missing = len(todo) - len(rows)
    share = n_missing / len(todo) if todo else 0.0
    rep = {"n_ids": len(todo), "n_found": len(rows), "n_missing": n_missing, "missing_share": share, "found_only_without_closed_filter": retried,
           "keys_sha256": h5_seal.sha256_file(keys_path)}
    fr.budget.write(rep_path, json.dumps(rep, indent=1, sort_keys=True).encode())  # last: marks the stage
    part.unlink(missing_ok=True)
    return rep, None


def _source_files(hist_root: Path, cb8_root: Path | None) -> list[tuple[str, Path]]:
    out = [(f"{run}/{fn}", Path(hist_root) / run / fn) for run, fn in ID_SOURCES]
    if cb8_root is not None and Path(cb8_root).is_dir():
        out += [(f"creative_batch8/{p.parent.name}/frame.csv.gz", p) for p in sorted(Path(cb8_root).glob(CB8_FRAME_GLOB))]
    return out


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, hist_root: Path, base_path: Path | None = None, base_sha256: str = H8_TAIL_B_KEYS_SHA256,
                   seals_dir: Path | None = None, external_dir: Path | None = None, cb8_root: Path | None = None, is_committed: Callable[[Path], bool] | None = None,
                   rps: float = 2.0, disk_cap: int = int(0.01 * 1024**3), budget_min: float | None = None, now: float | None = None, sleep=None, live_check=None,
                   should_stop: Callable[[], bool] | None = None, wall_clock: Callable[[], float] | None = None, snapshot_root: Path | None = None, health_check=None,
                   data_dumps: Path | None = None, data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB, free_fn=None, allow_absent_c1_t5: bool = False,
                   sample_pins: dict[str, str] | None = None) -> dict:
    """q0221. The h8_tail_b key file (sha256 pinned) plus, by closed-first Gamma id lookup (<= 50 ids per request, resumable), every market id of every
    sampled set on the host (``ID_SOURCES``), of every committed seal copy and of the staged C1 / T5 id lists (``external_dir``). The ``h2_main`` and
    ``h3_power`` ``sample.csv.gz`` are MANDATORY and sha256-pinned (``sample_pins``): absent, an unset pin or a mismatch is a refusal (exit 2); the other
    sampled sets are recorded 'absent' when missing. The staged C1 / T5 id lists are MANDATORY too (round 1 item 5): while either is missing the job is
    ``NotNow`` (exit 75, nothing written) unless ``allow_absent_c1_t5`` is set (an explicit, never-drafted flag), in which case ``c1_t5_status`` = absent is recorded
    permanently. More than 2% of ALL exclusion ids without metadata -> ``disjointness_unverified`` (P and A not testable, counted; the W key rule is
    market id + event id and W proceeds, design 1.3)."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    out_root, seals_dir = require_output_root(Path(out_root)), Path(seals_dir or SEALS_DIR)
    base_path = Path(base_path or (Path(hist_root) / "h8_tail_b" / "exclusion_keys.csv.gz"))
    got = h5_seal.sha256_file(base_path) if base_path.exists() else None
    if got != base_sha256:
        raise Refused(f"base key file {base_path} sha256 {got} != pinned {base_sha256}")
    base_ids = read_id_set(base_path)
    require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    set_ids: dict[str, int] = {}
    absent: list[str] = []
    new_ids: set[str] = set()
    pins = dict(MANDATORY_SAMPLE_PINS if sample_pins is None else sample_pins)
    for name, p in _source_files(Path(hist_root), cb8_root):
        if name in pins:
            pin = pins[name]
            if not p.exists():
                raise Refused(f"mandatory sampled set {name} is absent at {p}; refusing (exit 2), the exclusion keys would not cover it")
            if not pin or pin == PIN_UNSET:
                raise Refused(f"the sha256 pin of the mandatory sampled set {name} is unset ({PIN_UNSET}); the coordinator fills it from `sha256sum` on the host and regenerates the rules")
            got_s = h5_seal.sha256_file(p)
            if got_s != pin:
                raise Refused(f"mandatory sampled set {p} sha256 {got_s} != pinned {pin}")
        elif not p.exists():
            absent.append(name)
            continue
        ids = read_id_set(p)
        set_ids[name] = len(ids)
        new_ids |= ids
    seal_ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=OWN_SEAL_COPIES, is_committed=is_committed)
    new_ids |= seal_ids
    ext_status: dict[str, Any] = {}
    ext_dir = Path(external_dir or EXTERNAL_IDS_DIR)
    missing_ext = [fn for fn in EXTERNAL_ID_FILES if not (ext_dir / fn).exists()]
    if missing_ext and not allow_absent_c1_t5:
        raise NotNow(f"staged C1 / T5 id lists missing in {ext_dir}: {missing_ext}; stage them from the arepo-data release (pending, nothing written; --allow-absent-c1-t5 records them absent permanently)")
    for fn in EXTERNAL_ID_FILES:
        p = ext_dir / fn
        if p.exists():
            ids = read_id_set(p)
            new_ids |= ids
            ext_status[fn] = {"n_ids": len(ids), "sha256": h5_seal.sha256_file(p)}
        else:
            ext_status[fn] = "absent"
    c1_t5 = "retrieved" if all(isinstance(v, dict) for v in ext_status.values()) else "absent"
    new_ids -= base_ids
    fr = cm.open_run(out_root, EXCLUSION_RUN, transport, allowed_run_id=EXCLUSION_RUN, kind="cb11_exclusion_keys", label="CB11 exclusion keys",
                     params={"base_keys_sha256": base_sha256, "n_base_ids": len(base_ids), "n_new_ids": len(new_ids), "sets": set_ids, "sets_absent": absent,
                             "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "external": ext_status, "c1_t5_status": c1_t5,
                             "sample_pins": {k: v for k, v in sorted(pins.items())}, "allow_absent_c1_t5": bool(allow_absent_c1_t5), "evidence_role": EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep or time.sleep, live_check=live_check,
                     wall_clock=wall_clock or time.time, snapshot_root=snapshot_root, health_check=health_check)
    rep_new, stopped = _exclusion_stage(fr, new_ids, should_stop)
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep_new is not None
    rows = []
    with gzip.open(base_path, "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in csv.DictReader(fh)]
    with gzip.open(fr.rdir / "exclusion_keys.csv.gz", "rt", encoding="utf-8", newline="") as fh:
        rows += [[r[c] for c in c6.KEY_COLUMNS] for r in csv.DictReader(fh)]
    keys_out = out_root / "exclusion_keys.csv.gz"
    out_root.mkdir(parents=True, exist_ok=True)
    keys_out.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), sorted(rows)))
    base_rep = json.loads((base_path.with_name(EXCLUSION_REPORT_NAME)).read_text()) if base_path.with_name(EXCLUSION_REPORT_NAME).exists() else {}
    n_all = int(base_rep.get("n_ids", len(base_ids))) + rep_new["n_ids"]
    n_missing = int(base_rep.get("n_missing", 0)) + rep_new["n_missing"]
    share = n_missing / n_all if n_all else 1.0
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE,
           "disjointness": UNVERIFIED if share > MAX_UNVERIFIED_KEY_SHARE else "verified", "base_keys_sha256": base_sha256,
           "base_report": {k: base_rep.get(k) for k in ("n_ids", "n_missing", "disjointness")}, "new": rep_new, "sets": set_ids, "sets_absent": absent,
           "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "external": ext_status, "c1_t5_status": c1_t5,
           "sample_pins": {k: v for k, v in sorted(pins.items())}, "keys_sha256": h5_seal.sha256_file(keys_out), "built_utc": cm.iso(time.time())}
    (out_root / EXCLUSION_REPORT_NAME).write_text(json.dumps(rep, indent=1, sort_keys=True))
    status = UNVERIFIED if rep["disjointness"] == UNVERIFIED else EXCLUSION_KEYS_COMPLETE
    m = fr.manifest(None, {"exclusion_report": {k: rep[k] for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys_sha256", "c1_t5_status")},
                           "status": status, "complete": True})
    m["status"] = status
    return m


# ---- sealing (q0230) ---------------------------------------------------------------------------------------------------------------------------

SEAL_NAME = "holdout_SEAL.json"
DROPS_FILE = "drops.csv.gz"
ACCESS_LOG = "ACCESS_LOG.jsonl"


def seal_holdout(rdir: Path, *, family: str, statuses: tuple[str, ...], copy_name: str, rows: list[dict], rules_sha: str, transport=None, seals_dir: Path | None = None,
                 rps: float = 2.0, sleep=time.sleep, live_check=None, is_committed: Callable[[Path], bool] | None = None, holdout_prefix: str = "holdout/",
                 extra: dict | None = None) -> dict:
    """q0230 for one family. Refuses (NotNow) unless the fetch finished and every file matches its manifest. Seal-time drops (id and key, light Gamma lookup)
    of the sealed rows (``rows`` carry ``market_id`` and ``event_ids``, optionally ``neg_risk_market_id`` / ``series_ids``) against every committed seal copy
    except CB11's own, recorded as ``DROPPED_SEAL_COPIES`` rows (sealed files never edited); ``holdout_SEAL.json`` with the HOLDOUT listing sha256 and the
    committed copy ``seals/<copy_name>`` (never rewritten)."""
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    rdir = require_output_root(Path(rdir))
    seals_dir = Path(seals_dir or SEALS_DIR)
    st = stall_of(rdir)
    if st:
        return {**st, "sealed": False}
    sp = rdir / SEAL_NAME
    if sp.exists():
        doc = json.loads(sp.read_text())
        return {"status": f"{family}_sealed", "listing_sha256": doc["listing_sha256"], "already_sealed": True}
    man = json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}
    if not (man.get("complete") is True and not man.get("stopped") and man.get("status") in statuses):
        raise NotNow(f"{rdir.name} is not finished yet (status {man.get('status')}); pending")
    n_checked = cm.verify_manifest_files(rdir, man)
    ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=OWN_SEAL_COPIES, is_committed=is_committed)
    keys: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
    missing = 0
    if ids:
        if transport is None:
            raise Refused("seal copies exist but no transport was given for the key lookup")
        lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        found, _ = lookup_keys_closed_first(lim, sorted(ids))
        missing = len(ids) - len(found)
        for k in found.values():
            keys["event"].update(e for e in str(k.get("event_ids") or "").split(";") if e)
            if k.get("neg_risk_market_id"):
                keys["neg_risk_market"].add(k["neg_risk_market_id"])
            keys["series"].update(x for x in str(k.get("series_ids") or "").split(";") if x)
    unverified = bool(ids) and missing / len(ids) > MAX_UNVERIFIED_KEY_SHARE
    drop_rows, n = [], {"KEPT": 0, "DROPPED_SEAL_COPIES": 0}
    for r in rows:
        why = (["id"] if str(r["market_id"]) in ids else []) + c7.key_types_matched(r, keys)
        if why:
            n["DROPPED_SEAL_COPIES"] += 1
            drop_rows.append([r["market_id"], "DROPPED_SEAL_COPIES", "+".join(why)])
        else:
            n["KEPT"] += 1
    drop_rows.sort()
    (rdir / DROPS_FILE).write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], drop_rows))
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(holdout_prefix)}
    doc = {"seal_version": f"cb11-{family}-holdout-seal-v1", "family": family, "run_id": rdir.name, "sealed_utc": cm.iso(time.time()), "git_commit": hb._git_commit(), "rules_sha256": rules_sha,
           "listing_sha256": h5_seal.listing_sha256(holdout), "n_holdout_files": len(holdout), "files": dict(sorted(holdout.items())), "fetched_files_rehashed": n_checked,
           "drops": {"counts": n, "seal_copies_read": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "drop_ids": len(ids), "drop_ids_without_metadata": missing,
                     "disjointness": UNVERIFIED if unverified else "verified", "drops_sha256": h5_seal.sha256_file(rdir / DROPS_FILE)},
           "n_holdout_markets": len(rows),
           "read_rules": "verify the listing hash first; append every read to ACCESS_LOG.jsonl; holdout/ is not opened before the family's Stage-1 test advanced and its result is "
                         "committed; markets in DROPPED_* rows of drops.csv.gz are never analysed; the census reads HOLDOUT file and unit counts only", **(extra or {})}
    data = json.dumps(doc, indent=1, sort_keys=True).encode()
    dest = seals_dir / copy_name
    if dest.exists() and dest.read_bytes() != data:
        raise Refused(f"{dest} exists with different content; a seal is never rewritten")
    sp.write_bytes(data)
    (rdir / ACCESS_LOG).touch()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"status": f"{family}_sealed", "listing_sha256": doc["listing_sha256"], "committed_copy": str(dest), "drop_counts": n, "disjointness": doc["drops"]["disjointness"],
            "n_holdout_files": len(holdout)}


def dropped_market_ids(rdir: Path) -> set[str]:
    """Markets in seal-time ``DROPPED_*`` rows of ``drops.csv.gz`` (b1): never analysed. A sealed run without the file has no drops."""
    dp = Path(rdir) / DROPS_FILE
    if not dp.exists():
        return set()
    return {str(r["market_id"]) for r in read_csv_gz(dp) if str(r.get("block", "")).startswith("DROPPED")}


def verify_holdout_seal(rdir: Path, copy_name: str, seals_dir: Path | None = None, holdout_prefix: str = "holdout/", *, require_committed: bool = True) -> dict:
    """The run's seal equals the copy under ``seals/`` AND (N5) that copy is tracked by git and identical to HEAD (``require_committed``; tests and
    ``--allow-uncommitted-rules`` switch it off); then the HOLDOUT listing sha256 is re-verified."""

    from . import cb1_history as c1  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    rdir = Path(rdir)
    sp = rdir / SEAL_NAME
    if not sp.exists():
        raise Refused(f"{rdir.name} has no {SEAL_NAME}; run seal first")
    copy = Path(seals_dir or SEALS_DIR) / copy_name
    if not copy.exists() or copy.read_bytes() != sp.read_bytes():
        raise Refused(f"seal copy {copy} missing or different from {sp}")
    if require_committed and not c1.spec_committed(copy):
        raise Refused(f"seal copy {copy} is not committed (or differs from HEAD)")
    doc = json.loads(sp.read_text())
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(holdout_prefix)}
    if h5_seal.listing_sha256(holdout) != doc["listing_sha256"]:
        raise Refused("HOLDOUT listing sha256 differs from the seal; refusing")
    return doc


# ---- rules file --------------------------------------------------------------------------------------------------------------------------------


def _mods(names: tuple[str, ...]) -> list:
    return [importlib.import_module(f".{n}", __package__) for n in names]


def common_declared() -> dict:
    return {"t11_hist_end": T11_HIST_END, "t_seal_binding": "none (CB11 jobs yield to T_seal-bound jobs by priority only)",
            "stage1": {"gate_p": GATE_P, "holm_family": list(STAGE1_HOLM_FAMILY), "batch_holm_k1": BATCH_HOLM_K1, "batch_holm_alpha": BATCH_HOLM_ALPHA1, "by_q": BY_Q,
                       "by_family": "battery2.cumulative_count() at the run (triage only)"},
            "stage2": {"alpha": STAGE2_ALPHA, "rule": "one Holm over every CB11 test reaching Stage 2, each in its Stage-1 direction; k fixed when the last Stage-1 result is final; early finishers at alpha/k"},
            "uncertainty": {"n_boot": N_BOOT, "seed_boot": SEED_BOOT, "n_wild": N_WILD, "min_units": MIN_UNITS, "min_clusters": MIN_CLUSTERS, "top_drop": TOP_DROP,
                            "ways": {"W": ["UTC date of the scheduled end", "Gamma event"], "P": ["Gamma event", "ISO week of the scheduled end (CB10 small-G rule)"],
                                     "A": ["Gamma event", "UTC day X", "3-day blocks of the origin t"]},
                            "small_g": "cb2_weather.small_g_pvalue per way; p = max over the declared ways"},
            "placebos": {"seeds": PLACEBO_SEEDS, "draws": PLACEBO_DRAWS, "max_advance_rate": PLACEBO_MAX_ADVANCE, "gpp_seed": SEED_GPP, "gwc_seed": SEED_GWC},
            "counting": {"kinds": ["cb11_test", "cb11_replication", "cb11_descriptive"], "count_line": "ml_explain, source creative_batch_11:<W|P|A>, n_tests = 1 per test",
                         "not_testable": "counted with p = 1", "exit_75": "pending: no trials line", "stage2_tests_per_advance": 1},
            "pins": {"h8_tail_b_keys_sha256": H8_TAIL_B_KEYS_SHA256, "h2_frame_sha256": H2_FRAME_SHA256, "h3_frame_sha256": H3_FRAME_SHA256,
                     "h2_sample_sha256": H2_SAMPLE_SHA256, "h3_sample_sha256": H3_SAMPLE_SHA256, "pin_unset_token": PIN_UNSET},
            "refused_roots": list(REFUSED_ROOTS), "refused_run_ids": list(REFUSED_RUN_IDS), "frame_run_ids": list(FRAME_RUN_IDS), "frame_allowed_files": list(FRAME_ALLOWED_FILES),
            "output_roots": list(ALLOWED_OUTPUT_ROOT_PARTS),
            "exclusion": {"base": "h8_tail_b key file (sha256 pinned)", "id_sources": [list(x) for x in ID_SOURCES], "cb8_frame_glob": CB8_FRAME_GLOB,
                          "external_id_files": list(EXTERNAL_ID_FILES), "external_ids": "mandatory: exit 75 while missing unless --allow-absent-c1-t5 (never drafted)",
                          "mandatory_sampled_sets": sorted(MANDATORY_SAMPLE_PINS), "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE, "own_seal_copies": list(OWN_SEAL_COPIES),
                          "lookup": f"closed-first Gamma id lookup, {LOOKUP_PER_REQUEST} ids per request, resumable (deviation: about 14 requests per 1,000 new ids, not <= 400 total)",
                          "w_key_rule": "market id and event id only (frames carry no negRiskMarketID and no series id; section 11 N2); unverified disjointness stalls P and A only"},
            "stall": {"statuses": list(STALL_STATUSES), "exit": 0, "census": "copies the label", "screens": "p = 1, testable false", "results": "write-once"},
            "disk": {"data_dumps_cap_gb": DATA_DUMPS_CAP_GB, "free_disk_min_gb": FREE_DISK_MIN_GB, "total_output_cap_gb": TOTAL_OUTPUT_CAP_GB,
                     "exit_75": "pending (never 'not run')"},
            "wallet_and_side": "no CB11 job reads or stores a wallet field or the Data API side field"}


def common_rule_funcs() -> tuple:
    return (ny_clock, refuse_run_id, refuse_path, refuse_read, require_output_root, require_after, require_disk, upstream_stall, stage2_k, batch_holm_label, cluster_p,
            cluster_p_week, placebo_advance_rate, one_sided_boot_p, open_guarded, read_id_set, lookup_keys_closed_first, drop_by_keys_w, exclusion_keys,
            _exclusion_stage, seal_holdout, verify_holdout_seal, common_declared, c10.leave_one_out_sign, c9.holm, c9.top_k_drop_mask, c9.cluster_bootstrap_means)


def rules_part_doc(part: str) -> dict:
    """The declared document of rules part W: common + cb11_w + cb11_smoke. Part PA is declared elsewhere (``cb11_pa_rules.json``): here it is only a pointer."""
    if part not in RULE_PARTS:
        raise Refused(f"unknown rules part {part!r}")
    if part == "PA":
        return {"part": "PA", "part_declared": False, "rules_version": RULES_VERSION, "declared_by": PA_RULES_FILE_NAME,
                "note": "P and A rules are hashed in the separate file cb11_pa_rules.json before the first P / A request; this part never changes"}
    funcs = list(common_rule_funcs())
    declared: dict[str, Any] = {}
    for mod in _mods(W_RULE_MODULES):
        funcs += list(mod.rule_funcs())
        declared[mod.__name__.rsplit(".", 1)[-1]] = mod.declared()
    seen: set[int] = set()
    funcs = [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]
    src = "\n".join(inspect.getsource(f) for f in funcs)
    return {"part": part, "part_declared": True, "rules_version": RULES_VERSION, "declared": declared, "common": common_declared(),
            "disk": {"data_dumps_cap_gb_default": DATA_DUMPS_CAP_GB, "free_disk_min_gb": FREE_DISK_MIN_GB, "headroom_exit": cm.TEMPFAIL_EXIT,
                     "disk_budget_exit": cm.DISK_BUDGET_EXIT, "refusal_exit": cm.REFUSED_EXIT},
            "wallet": {"read": False, "note": "no CB11 job reads or stores a wallet field (no HMAC key needed) or the side field"},
            "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
            "func_sources_sha256": {f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}}


def rules_part_file_doc(part: str) -> dict:
    d = json.loads(json.dumps(rules_part_doc(part), sort_keys=True, default=str))
    if d.get("part_declared") is False:
        return {**d, "rules_sha256": None}
    return {**d, "rules_sha256": cm.sha_obj(d)}


def rules_file_doc(parts: tuple[str, ...] = RULE_PARTS) -> dict:
    """The v2 rules file: ``{"rules_version", "parts": {"W": {..., "rules_sha256"}, "PA": {...}}}``, one sha256 per part."""
    return {"rules_version": RULES_VERSION, "parts": {p: rules_part_file_doc(p) for p in parts}}


def write_rules(path: Path | None = None) -> Path:
    """Write the v2 rules file (part W hashed, part PA a static pointer). An existing file is never rewritten."""
    path = Path(path or RULES_FILE)
    want = rules_file_doc()
    if path.exists():
        if json.loads(path.read_text()) != want:
            raise Refused(f"{path} exists with different content; a rules file is never rewritten")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "W") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's. W jobs verify only part W (and the declared version): part PA is never read or imported.
    Part PA 'not declared' refuses a P / A job. Returns the part's ``rules_sha256``."""
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
    if doc.get("rules_version") != RULES_VERSION:
        raise Refused(f"rules file {path} has rules_version {doc.get('rules_version')!r} != {RULES_VERSION!r}")
    have = (doc.get("parts") or {}).get(part)
    if have is None:
        raise Refused(f"rules file {path} has no part {part!r}")
    if have.get("part_declared") is False:
        raise Refused(f"rules part {part} is not declared in {path}: P / A jobs verify {PA_RULES_FILE_NAME}")
    want = rules_part_file_doc(part)
    if have != want:
        raise Refused(f"rules hash mismatch (part {part}): file {have.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"]


# ---- trials ------------------------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb11_descriptive`` line (EXCLUDE, counts 0): smoke, census, gates, strata, variants."""
    rec = {"kind": "cb11_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_11:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_test(family: str, tid: str, result: dict, *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST,
             results_sha256: str = "", placebo: dict | None = None, data_role: str | None = None) -> None:
    """One ``cb11_test`` / ``cb11_replication`` line (EXCLUDE), one placebo line (counts 0) and the count line ``ml_explain`` (source
    ``creative_batch_11:<family>``, ``n_tests`` = 1). A test behind a failed or unknown gate is counted with p = 1. Exit 75 never reaches here."""
    if family not in ("W", "P", "A"):
        raise Refused(f"unknown CB11 count family {family!r}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb11_replication" if replication else "cb11_test"
    p = result.get("p", 1.0)
    if not result.get("testable", True) or p is None:
        p = 1.0
    base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_11", "hypothesis": tid, "family": family, "results_sha256": results_sha256,
            **({"data_role": data_role} if data_role else {})}
    provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                             "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
    if placebo:
        provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": placebo.get("note", "placebo"),
                                 "advance_rate": placebo.get("advance_rate"), "n_draws": placebo.get("n_draws"), "n_tests": 0}, tp)
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_11:{family}", "dataset": "creative_batch_11",
                             "n_tests": 1, "n_tests_by_family": {f"cb11_{family}": 1}, "hypothesis": tid, "replication": bool(replication),
                             "advanced": [tid] if result.get("advance") else [], "results_sha256": results_sha256, **({"data_role": data_role} if data_role else {}),
                             "note": "CB11 count line: one test (a test behind a failed gate is still counted, p = 1)"}, tp)


def sha256_obj(obj) -> str:
    return cm.sha_obj(obj)

