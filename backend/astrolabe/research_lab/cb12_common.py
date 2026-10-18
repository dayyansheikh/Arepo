# ruff: noqa: E501
"""CB12 shared parts (docs/research_lab/CREATIVE_BATCH_12.md sections 1.3, 1.4, 2.1-2.8, 10).

Everything that is common to the CB12 families lives here: refusal lists (outputs AND inputs), the disk guards (data-dumps cap AND root free disk, exit 75 =
"pending"), the guarded-file accessors (SCREEN and HOLDOUT outcome files separate; the HOLDOUT sha256 lives in the seal), the ``prices-history`` causal rule
(usable from stamp + max(600, 60 x fidelity) s), ``ceil_tick``, the transaction aggregator (hash -> row, hash discarded), the newest-first paged print fetch, the
fixed-k1 Holm helpers (k1 = 10, early-finisher rule at alpha / 10), the trial-line helpers, the freeze gate (one entry per family part) and the
per-part rules hashing.

**Per-part rules hashing (the CB11 whole-document-hash pitfall).** ``seals/cb12_rules.json`` holds one sha256 per part: ``common``, ``M``, ``E``, ``F``, ``X``,
``O``. A family part hashes ONLY (a) the common rule functions and constants of this module, and (b) the functions and UPPER_CASE constants of that family's own
module(s) (``FAMILY_MODULES``). Verifying part X imports ``cb12_x`` and nothing else: it never imports, and so never depends on, ``cb12_e`` / ``cb12_f`` /
``cb12_o`` / ``cb12_m``. A family module that does not exist yet leaves its part "not declared"; adding it later changes no other part's hash. Rule: nothing
family-specific may be added to this module after the first CB12 request (put it in the family module).
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
from zoneinfo import ZoneInfo

import numpy as np

from . import cb8_common as cm
from . import cb9_common as c9
from . import cb10_common as c10
from . import provenance

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

# ---- constants (hashed with this module: every UPPER_CASE JSON-able constant below is part of ``common``) ------------------------------------------------
RULES_VERSION = "cb12-rules-v1"
PARTS = ("common", "M", "E", "F", "X", "O")
FAMILY_PARTS = ("M", "E", "F", "X", "O")
FAMILY_MODULES = {"M": ("cb12_m",), "E": ("cb12_e",), "F": ("cb12_f",), "X": ("cb12_x",), "O": ("cb12_o",)}
FAMILY_TESTS = {"M": ("M1", "M2"), "E": ("E1",), "F": ("AL1", "AL2", "SH1", "SH2"), "X": ("X1",), "O": ("O1", "O2")}
FAMILY_REP_TESTS = {"M": ("M1", "M2"), "E": ("E1", "E2"), "F": ("AL1", "AL2", "SH1", "SH2"), "X": (), "O": ("O1", "O2")}
STAGE1_HOLM_FAMILY = ("M1", "M2", "E1", "AL1", "AL2", "SH1", "SH2", "X1", "O1", "O2")
BATCH_HOLM_K1 = len(STAGE1_HOLM_FAMILY)  # = 10, fixed
STAGE_ALPHA = 0.05  # Stage 1 batch Holm and Stage 2 Holm, one-sided
STAGE2_K_MAX = 10  # the largest possible Stage-2 count (early reps are judged against alpha / 10)
EARLY_ALPHA = STAGE_ALPHA / BATCH_HOLM_K1  # Holm's first step over the ten fixed tests: 0.005, never withdrawn
GATE_P = 0.01
BY_Q = 0.10
N_BOOT = 2000
SEED_BOOT = 1212
N_WILD = 9999
PLACEBO_DRAWS = 200
PLACEBO_MAX_ADVANCE = 0.015
PLACEBO_SEEDS = {"M1_copula": 12101, "M2_fill_calibrated": 12102, "X1_horizon_offset": 12108}
SEED_GMP = 12121
GMP_DRAWS = 500
MIN_UNITS = 100
MIN_CLUSTERS = 30
TOP_DROP = 5
AVAIL_MIN = 0.60  # available share of eligible units below this -> "not testable (availability)" (section 2.6 iv)
EVIDENCE_ROLE_HIST = "exploratory_historical"
MAX_UNVERIFIED_KEY_SHARE = 0.02
EXCLUSION_KEYS_COMPLETE = "exclusion_keys_complete"
UNVERIFIED = "disjointness_unverified"
PENDING = "pending"
PIN_UNSET = "TODO-COORDINATOR"  # a pin the coordinator fills from a read-only `sha256sum` on the host; the dependent job refuses (exit 2) while it is unset
T12_HIST_END = "2026-10-01T00:00:00Z"
T12_HIST_END_EPOCH = datetime(2026, 10, 1, tzinfo=UTC).timestamp()
T12_X_END = "2026-10-12T00:00:00Z"
T12_X_END_EPOCH = datetime(2026, 10, 12, tzinfo=UTC).timestamp()
X_MTIME_MAX_EPOCH = datetime(2026, 10, 13, tzinfo=UTC).timestamp()
T_SEAL = "2026-10-22T00:00:00Z"
CB12_SPORTS_IN_PRIMARY = False
SMOKE_VERSION = "cb12-smoke-v1"
DATA_DUMPS_CAP_GB = 40.0
FREE_DISK_MIN_GB = 4.5
HEARTBEAT_S = cm.HEARTBEAT_S
# prices-history (section 2.2): a point at fidelity f minutes is known from stamp + max(600, 60 f) s; the price at t is the last point known BEFORE t, age <= 24 h
PRICE_MIN_LAG_S = 600
PRICE_MAX_AGE_S = 86400.0
TICK = 0.01
PRICE_CAP = 0.99
# Data API paging (section 2.8): limit 10,000 at offsets 0 and 10,000 (the API caps offset at 10,000: the newest 20,000 prints are the reachable maximum)
DATA_PAGE_LIMIT = 10000
DATA_PAGES = 2
GAMMA_EVENTS = "https://gamma-api.polymarket.com/events"
GAMMA_PAGE = 100
GAMMA_OFFSET_CAP = 2000
LOOKUP_PER_REQUEST = 50
# Output roots CB12 writes under, and input roots it never reads (section 1.1 last rows, 1.3)
ALLOWED_OUTPUT_ROOT_PARTS = ("creative_batch12", "h12_say", "h12_quake", "h12_prints", "h12_quake_live", "h12_opt_live")
LIVE_ROOT_NAME = "cross_venue_live"
X_READABLE_ROOTS = ("cross_venue",)  # the sha256-pinned historical study files, read by CB12-X only (section 1.3)
EXTRA_REFUSED_ROOTS = ("creative_batch11", "creative_batch10", "creative_batch9", "snapshots", "trade_samples", "live_trades", "book_sweeps", "surprise_live", LIVE_ROOT_NAME,
                       "h9_flow", "h10_sign", "h10_dlad", "h10_brk", "h11_wprints", "h11_pol", "h11_attn", "h1_first", "h2_main", "h3_power", "h4_seal", "h5_cb1",
                       "h5_cb1_ladders", "h6_weather", "h7_cb4_era", "h7_cb4_series", "h8_tail", "h8_tail_b", "h8_text", "h8_geo")
EXTRACT_ROOT_RE = r"^cb\d+_extract$"
HOLDOUT_PART = "holdout"
SCREEN_JOBS = ("screen-M", "screen-E", "screen-F", "screen-X", "screen-O")
REP_JOBS = ("rep-M", "rep-E", "rep-F", "rep-O")
GUARDED_NAMES = ("outcomes_guarded_screen.csv.gz", "outcomes_guarded_holdout.csv.gz", "outcomes_guarded.csv.gz")
SEAL_NAME = "holdout_SEAL.json"
DROPS_FILE = "drops.csv.gz"
SERIES_DATES_NAME = "exclusion_series_dates.csv.gz"  # (series id, event id, startTime epoch) of each excluded event that belongs to a series, written by q0241
SERIES_DATES_COLUMNS = ["series_id", "event_id", "start_epoch"]
SERIES_DATES_RUN_FILE = "series_dates_report.json"
ACCESS_LOG = "ACCESS_LOG.jsonl"
OWN_SEAL_COPIES = ("cb12_say_holdout_SEAL.json", "cb12_prints_holdout_SEAL.json")
EXCLUSION_RUN = "exclusion_run12"
ID_SOURCES = (("h9_flow", "sample.csv.gz"), ("h10_sign", "sample.csv.gz"), ("h10_dlad", "frame.csv.gz"), ("h10_brk", "frame.csv.gz"), ("h11_wprints", "markets.csv.gz"),
              ("h11_pol", "frame.csv.gz"), ("h11_attn", "frame.csv.gz"))  # a missing file is recorded "absent at q0241" and re-read at the seal-time drops
NY = ZoneInfo("America/New_York")
DATA_DUMPS = cm.DATA_DUMPS
HIST_ROOT = cm.HIST_ROOT
CB12_DIR = DATA_DUMPS / "research_lab" / "creative_batch12"
CV_DIR = DATA_DUMPS / "research_lab" / "cross_venue"
CB11_KEYS_DEFAULT = DATA_DUMPS / "research_lab" / "creative_batch11" / "exclusion_keys.csv.gz"
SMOKE_DEFAULT = CB12_DIR / "smoke.json"
EXCLUSION_KEYS_DEFAULT = CB12_DIR / "exclusion_keys.csv.gz"

RULES_MACHINERY = ("rules_part_doc", "rules_part_file_doc", "rules_file_doc", "write_rules", "verify_rules", "family_modules", "common_funcs", "module_funcs",
                   "module_constants", "part_funcs", "_mods", "_jsonable")


# ---- small helpers -----------------------------------------------------------------------------------------------------------------------------


def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def rank(seed: str, key: str) -> str:
    return hashlib.sha256(f"{seed}|{key}".encode()).hexdigest()


def utc_day(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")


def iso_week_of(epoch: float) -> str:
    y, w, _ = datetime.fromtimestamp(epoch, UTC).isocalendar()
    return f"{y}-W{w:02d}"


def parse_iso(s) -> float:
    """Epoch seconds of an ISO-8601 string (``Z`` or offset; a naive value is UTC); NaN if unparseable."""
    if not s:
        return math.nan
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        return math.nan
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).timestamp()


def listish(v) -> list:
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except ValueError:
            return []
    return list(v) if isinstance(v, list) else []


def read_csv_gz(path: Path) -> Iterator[dict]:
    csv.field_size_limit(10**9)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        yield from csv.DictReader(fh)


def read_id_set(path: Path) -> set[str]:
    """Market ids (column ``market_id``) of a sampled / sealed set; ONLY the ids leave this function (id-column readers are field-restricted)."""
    p = Path(path)
    opener = gzip.open if p.name.endswith(".gz") else open
    csv.field_size_limit(10**9)
    with opener(p, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        if "market_id" not in (rd.fieldnames or []):
            raise Refused(f"{p} has no market_id column")
        return {str(r["market_id"]) for r in rd}


# ---- refusals ----------------------------------------------------------------------------------------------------------------------------------


def refused_names() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*c10.REFUSED_ROOTS, *c10.REFUSED_RUN_IDS, *EXTRA_REFUSED_ROOTS)))


def refuse_path(path: Path, *, allow: tuple[str, ...] = ()) -> Path:
    """Output AND input guard: refuse any path with a CB1-CB11 / sealed / live root among its parts, any ``cb<n>_extract`` directory, and anything under
    ``cross_venue_live`` (the E009 / E010 live store is never opened by any CB12 path). ``allow`` names roots a single reader may open (only X: ``X_READABLE_ROOTS``, the
    pinned historical ``cross_venue/`` files; the live root is never allowed)."""
    parts = Path(path).parts
    names = tuple(n for n in refused_names() if n not in allow)
    bad = [p for p in parts if p in names or re.match(EXTRACT_ROOT_RE, p) or LIVE_ROOT_NAME in p]
    if bad:
        raise Refused(f"path {path} is under a refused CB1-CB11 / sealed / live root ({bad[0]}); CB12 refuses it")
    return Path(path)


def refuse_read(path: Path) -> Path:
    return refuse_path(Path(path))


def require_output_root(path: Path) -> Path:
    """Data jobs write only under creative_batch12 / h12_*."""
    refuse_path(Path(path))
    if not any(p in ALLOWED_OUTPUT_ROOT_PARTS for p in Path(path).parts):
        raise Refused(f"CB12 writes only under {ALLOWED_OUTPUT_ROOT_PARTS}, not {path}")
    return Path(path)


def is_holdout_path(path: Path) -> bool:
    p = Path(path)
    return HOLDOUT_PART in p.parts or "holdout" in p.name


def guard_screen_path(path: Path) -> Path:
    """A SCREEN / census job refuses every ``holdout/`` path and every ``*holdout*`` file (the HOLDOUT is opened only by a rep after the seal check)."""
    if is_holdout_path(path):
        raise Refused(f"{path}: HOLDOUT paths are refused by screen and census jobs (sealed until the rep verifies the seal)")
    return Path(path)


def require_after(now: float, epoch: float, label: str) -> None:
    if now < epoch:
        raise NotNow(f"{label}: not before {datetime.fromtimestamp(epoch, UTC):%Y-%m-%dT%H:%MZ} (pending)")


def require_disk(data_dumps: Path | None, cap_gb: float, allowance_bytes: int, *, free_path: Path | None = None, free_min_gb: float = FREE_DISK_MIN_GB, free_fn=None) -> dict:
    """Exit 75 ("pending", never "not run") if data-dumps + the job's cap > ``cap_gb`` OR root free disk - the job's cap < ``free_min_gb``."""
    return c10.require_disk(data_dumps, cap_gb, allowance_bytes, free_path=free_path, free_min_gb=free_min_gb, free_fn=free_fn)


def wait_or_idle(rdir: Path, why: str, now: float) -> dict:
    """A job that must wait (an upstream fetch not finished, the freeze not committed yet...): ``NotNow`` (exit 75) except that at least every 10 h it returns a
    clean ``idle_heartbeat`` (exit 0), so the queue's 48-consecutive-tempfail cap never fires while it waits (as run_cb8.py)."""
    return cm.idle(Path(rdir), why, now)


def require_freeze(part: str, spec_path: Path | None = None, *, require_committed: bool = True) -> str:
    """Analysis jobs (screen, rep) refuse before the CB12 declaration is committed (``model_specs/cb12_v1.json``). One entry per family part, so a family
    freezes and screens without waiting on another's data; returns the sha256 of that part's entry."""
    if part not in FAMILY_PARTS:
        raise Refused(f"unknown freeze part {part!r}")
    p = Path(spec_path or (Path(__file__).resolve().parent / "model_specs" / "cb12_v1.json"))
    if not p.exists():
        raise Refused(f"CB12 freeze spec {p} not found: the screens refuse before the CB12 freeze")
    if require_committed:
        from . import cb1_history  # noqa: PLC0415

        if not cb1_history.spec_committed(p):
            raise Refused(f"CB12 freeze spec {p} is not committed (or differs from HEAD)")
    try:
        doc = json.loads(p.read_text())
    except ValueError as exc:
        raise Refused(f"CB12 freeze spec {p} unreadable") from exc
    if not isinstance(doc, dict) or part not in doc:
        raise Refused(f"CB12 freeze spec {p} has no {part!r} part")
    return hashlib.sha256(json.dumps(doc[part], sort_keys=True, default=str).encode()).hexdigest()


# ---- stalls and manifests ----------------------------------------------------------------------------------------------------------------------


def stall_of(rdir: Path) -> dict | None:
    return c9.stall_of(Path(rdir))


def write_stall(rdir: Path, status: str, reason: str, label: str | None = None) -> dict:
    return c9.write_stall(Path(rdir), status, reason, label)


def upstream_stall(rdir: Path, upstream: Path) -> dict | None:
    s = stall_of(upstream)
    if s is None:
        return None
    return write_stall(rdir, c9.STALL_UPSTREAM, f"upstream {Path(upstream).name}: {s['status']}", s.get("label"))


def manifest_complete(rdir: Path, statuses: tuple[str, ...]) -> dict | None:
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
    """A finished fetch whose manifest is complete AND whose recorded files still hash to the manifest (census, screen and rep each re-check)."""
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


def write_results_once(path: Path, doc: dict) -> str:
    return c9.write_results_once(Path(path), doc)


# ---- guarded files and the HOLDOUT seal --------------------------------------------------------------------------------------------------------


def log_access(rdir: Path, job: str, name: str) -> None:
    with (Path(rdir) / ACCESS_LOG).open("a") as fh:
        fh.write(json.dumps({"utc": cm.iso(time.time()), "job": job, "file": name}, sort_keys=True) + "\n")


def open_guarded(path: Path, job: str, seal: dict | None = None) -> list[dict]:
    """Outcome files are opened ONLY by screen (SCREEN file) and rep (HOLDOUT file) jobs. The HOLDOUT outcome file additionally needs the verified seal
    document (``verify_holdout_seal``) and its sha256 must equal the one recorded in the seal; a census opens nothing."""
    from . import h5_seal  # noqa: PLC0415

    p = Path(path)
    if p.name not in GUARDED_NAMES:
        raise Refused(f"{p.name} is not a guarded file of CB12")
    if is_holdout_path(p):
        if job not in REP_JOBS:
            raise Refused(f"HOLDOUT outcome file {p.name} may be opened only by {REP_JOBS}, not {job!r}")
        if not isinstance(seal, dict) or seal.get("verified") is not True:
            raise Refused("the HOLDOUT outcome file needs the verified seal document (verify_holdout_seal first)")
        want = (seal.get("holdout_outcome_file_sha256") or {}).get(p.name)
        if not want or h5_seal.sha256_file(p) != want:
            raise Refused(f"{p.name} sha256 differs from the seal (or is not recorded in it); refusing")
        log_access(p.parent.parent if p.parent.name == HOLDOUT_PART else p.parent, job, p.name)  # the access log lives in the run dir, never inside the sealed holdout/ listing
    elif job not in SCREEN_JOBS:
        raise Refused(f"guarded file {p.name} may be opened only by {SCREEN_JOBS}, not {job!r}")
    return list(read_csv_gz(p))


def seal_holdout(rdir: Path, *, family: str, statuses: tuple[str, ...], copy_name: str, rows: list[dict], rules_sha: str, transport=None, seals_dir: Path | None = None,
                 rps: float = 2.0, sleep=time.sleep, live_check=None, is_committed: Callable[[Path], bool] | None = None, holdout_prefix: str = "holdout/",
                 outcome_files: tuple[str, ...] = (), hist_root: Path | None = None, absent_sets: Iterable[str] = ()) -> dict:
    """Seal one family's HOLDOUT. Refuses (NotNow) unless the fetch finished and every file matches its manifest. Seal-time drops (id and key) of the sealed rows
    against every committed seal copy except CB12's own, as ``DROPPED_SEAL_COPIES`` rows (sealed files never edited); the id-source frames recorded "absent at q0241"
    (``absent_sets``, relative to ``hist_root``) are re-read here, their ids and keys dropped as ``DROPPED_ABSENT_AT_Q0241`` rows and their file sha256 recorded; ``holdout_SEAL.json`` with the HOLDOUT
    listing sha256 AND the sha256 of each HOLDOUT outcome file (``outcome_files``, relative to ``rdir``), and the committed copy ``seals/<copy_name>``."""
    from . import cb7_common as c7  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    rdir = require_output_root(Path(rdir))
    seals_dir = Path(seals_dir or cm.SEALS_DIR)
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
    late_ids: set[str] = set()
    reread: dict[str, dict] = {}
    for rel in sorted(set(absent_sets)):
        fp = Path(hist_root) / rel if hist_root is not None else None
        if fp is not None and fp.is_file():  # id columns only (as q0241: the refused roots are not opened for anything else)
            got = read_id_set(fp)
            late_ids |= got
            reread[rel] = {"now_present": True, "n_ids": len(got), "sha256": h5_seal.sha256_file(fp)}
        else:
            reread[rel] = {"now_present": False}
    late_ids -= ids
    lim = None

    def lookup(want: set[str]) -> tuple[dict[str, set[str]], int]:
        nonlocal lim
        out: dict[str, set[str]] = {"event": set(), "neg_risk_market": set(), "series": set()}
        if not want:
            return out, 0
        if transport is None:
            raise Refused("seal copies / re-read frames exist but no transport was given for the key lookup")
        lim = lim or hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
        found, _ = lookup_keys_closed_first(lim, sorted(want))
        for k in found.values():
            out["event"].update(e for e in str(k.get("event_ids") or "").split(";") if e)
            if k.get("neg_risk_market_id"):
                out["neg_risk_market"].add(k["neg_risk_market_id"])
            out["series"].update(x for x in str(k.get("series_ids") or "").split(";") if x)
        return out, len(want) - len(found)

    keys, missing = lookup(ids)
    late_keys, late_missing = lookup(late_ids)
    unverified = bool(ids) and missing / len(ids) > MAX_UNVERIFIED_KEY_SHARE
    late_unverified = bool(late_ids) and late_missing / len(late_ids) > MAX_UNVERIFIED_KEY_SHARE
    drop_rows, n = [], {"KEPT": 0, "DROPPED_SEAL_COPIES": 0, "DROPPED_ABSENT_AT_Q0241": 0}
    for r in rows:
        why = (["id"] if str(r["market_id"]) in ids else []) + c7.key_types_matched(r, keys)
        why_late = (["id"] if str(r["market_id"]) in late_ids else []) + c7.key_types_matched(r, late_keys)
        if why:
            n["DROPPED_SEAL_COPIES"] += 1
            drop_rows.append([r["market_id"], "DROPPED_SEAL_COPIES", "+".join(why)])
        elif why_late:
            n["DROPPED_ABSENT_AT_Q0241"] += 1
            drop_rows.append([r["market_id"], "DROPPED_ABSENT_AT_Q0241", "+".join(why_late)])
        else:
            n["KEPT"] += 1
    drop_rows.sort()
    (rdir / DROPS_FILE).write_bytes(hb._gz_csv_bytes(["market_id", "block", "reason"], drop_rows))
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(holdout_prefix)}
    out_sha = {}
    for rel in outcome_files:
        fp = rdir / rel
        if not fp.is_file():
            raise Refused(f"{family}: HOLDOUT outcome file {rel} missing at seal time; refusing")
        out_sha[Path(rel).name] = h5_seal.sha256_file(fp)
    doc = {"seal_version": f"cb12-{family}-holdout-seal-v1", "family": family, "run_id": rdir.name, "sealed_utc": cm.iso(time.time()), "git_commit": hb._git_commit(),
           "rules_sha256": rules_sha, "listing_sha256": h5_seal.listing_sha256(holdout), "n_holdout_files": len(holdout), "files": dict(sorted(holdout.items())),
           "holdout_outcome_file_sha256": out_sha, "fetched_files_rehashed": n_checked,
           "drops": {"counts": n, "seal_copies_read": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "drop_ids": len(ids), "drop_ids_without_metadata": missing,
                     "disjointness": UNVERIFIED if (unverified or late_unverified) else "verified", "absent_at_q0241_reread": reread,
                     "absent_drop_ids": len(late_ids), "absent_drop_ids_without_metadata": late_missing, "drops_sha256": h5_seal.sha256_file(rdir / DROPS_FILE)},
           "n_holdout_markets": len(rows),
           "read_rules": "verify the listing hash and the outcome-file hash first; append every read to ACCESS_LOG.jsonl; holdout/ is not opened before the family's Stage-1 "
                         "test advanced and its result is committed; markets in DROPPED_* rows of drops.csv.gz are never analysed; the census reads HOLDOUT counts only"}
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


def load_drops(rdir: Path, seal: dict) -> set[str]:
    """The market ids in ``DROPPED_*`` rows of ``drops.csv.gz`` (never analysed). The file must exist and its sha256 must equal the one recorded in the (verified) seal;
    otherwise ``Refused`` (exit 2)."""
    from . import h5_seal  # noqa: PLC0415

    p = Path(rdir) / DROPS_FILE
    want = ((seal or {}).get("drops") or {}).get("drops_sha256")
    if not p.is_file():
        raise Refused(f"{DROPS_FILE} is missing in {Path(rdir).name}; refusing (the seal-time drops must be applied)")
    if not want or h5_seal.sha256_file(p) != want:
        raise Refused(f"{DROPS_FILE} sha256 differs from the seal (or the seal records none); refusing")
    return {str(r["market_id"]) for r in read_csv_gz(p) if str(r.get("block", "")).startswith("DROPPED_")}


def verify_holdout_seal(rdir: Path, copy_name: str, seals_dir: Path | None = None, *, holdout_prefix: str = "holdout/", require_committed: bool = True) -> dict:
    """The run's seal equals the copy under ``seals/`` AND that copy is tracked by git and identical to HEAD; the HOLDOUT listing sha256 is re-verified. Returns
    the seal document with ``verified: True`` (the token ``open_guarded`` demands for the HOLDOUT outcome file)."""
    from . import cb1_history as c1  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    rdir = Path(rdir)
    sp = rdir / SEAL_NAME
    if not sp.exists():
        raise Refused(f"{rdir.name} has no {SEAL_NAME}; run seal first")
    copy = Path(seals_dir or cm.SEALS_DIR) / copy_name
    if not copy.exists() or copy.read_bytes() != sp.read_bytes():
        raise Refused(f"seal copy {copy} missing or different from {sp}")
    if require_committed and not c1.spec_committed(copy):
        raise Refused(f"seal copy {copy} is not committed (or differs from HEAD)")
    doc = json.loads(sp.read_text())
    holdout = {k: v for k, v in h5_seal.list_files(rdir).items() if k.startswith(holdout_prefix)}
    if h5_seal.listing_sha256(holdout) != doc["listing_sha256"]:
        raise Refused("HOLDOUT listing sha256 differs from the seal; refusing")
    return {**doc, "verified": True}


# ---- causal rules: prices-history, ticks, transactions ----------------------------------------------------------------------------------------


def known_lag_s(fidelity_min: int) -> float:
    """A ``prices-history`` point at fidelity f is known from stamp + max(600, 60 f) s (fidelity 10: +600 s; fidelity 60: +3,600 s), safe under either stamp convention."""
    return float(max(PRICE_MIN_LAG_S, 60 * int(fidelity_min)))


def price_at(points: Iterable[tuple[float, float]], t: float, fidelity_min: int, *, max_age_s: float = PRICE_MAX_AGE_S) -> float | None:
    """The price at ``t``: the last point with ``stamp + lag < t`` (strictly before ``t``) and ``t - stamp <= max_age_s``; None = "unavailable (no price)"."""
    lag = known_lag_s(fidelity_min)
    best = None
    for ts, p in points:
        if ts + lag < t and t - ts <= max_age_s and (best is None or ts > best[0]) and math.isfinite(p):
            best = (ts, p)
    return None if best is None else float(best[1])


def ceil_tick(x: float, tick: float = TICK) -> float:
    """The next 1c tick at or above ``x`` (a value on the grid is unchanged; float noise below 1e-9 does not push it up a tick)."""
    return round(math.ceil(x / tick - 1e-9) * tick, 10)


def aggregate_transactions(prints: Iterable[dict], yes_index: int) -> tuple[list[dict], dict]:
    """Data API prints -> one row per (market, transaction hash), the hash discarded: time (the latest fill), YES-terms VWAP (outcome ``yes_index`` prints keep their
    price, the other outcome's map to ``1 - price``), total size, notional ``sum(size x price)`` in the traded token's terms, fill count, max-fill notional and the
    fills (in memory only, for a family's own derived columns). A print without a hash is its own transaction (counted). Wallet, name and side are never read."""
    groups: dict[str, list[tuple[float, float, float, int]]] = {}
    n_nohash = 0
    for i, x in enumerate(prints):
        if not isinstance(x, dict):
            continue
        ts, px, sz = num(x.get("timestamp")), num(x.get("price")), num(x.get("size"))
        if not (math.isfinite(ts) and math.isfinite(px) and math.isfinite(sz)) or sz <= 0:
            continue
        oi = x.get("outcomeIndex")
        try:
            oi = int(oi)
        except (TypeError, ValueError):
            continue
        h = x.get("transactionHash")
        if not h:
            n_nohash += 1
            h = f"nohash:{i}"
        groups.setdefault(str(h), []).append((ts, px, sz, oi))
    rows = []
    for fills in groups.values():
        size = sum(f[2] for f in fills)
        yes_notional = sum(f[2] * (f[1] if f[3] == yes_index else 1.0 - f[1]) for f in fills)
        rows.append({"ts": max(f[0] for f in fills), "price": yes_notional / size, "size": size, "notional": sum(f[2] * f[1] for f in fills), "n_fills": len(fills),
                     "max_fill_notional": max(f[2] * f[1] for f in fills), "fills": [(f[0], f[1], f[2], f[3]) for f in fills]})
    rows.sort(key=lambda r: (r["ts"], r["price"], r["size"]))
    return rows, {"n_nohash": n_nohash, "n_tx": len(rows)}


def fetch_prints_paged(lim, cid: str, t_reach: float, *, limit: int = DATA_PAGE_LIMIT, pages: int = DATA_PAGES, url: str | None = None) -> tuple[list[dict], dict]:
    """Newest-first ``/trades`` pages (``limit`` 10,000 at offsets 0 and 10,000). A further page is requested only if the page just read was full AND its oldest print
    is after ``t_reach``. ``truncated`` iff the cap is reached on a full page whose oldest print is still after ``t_reach`` (or the API refuses a deep offset); the
    member is then "unavailable (source)" for any use that needs prints back to ``t_reach``. A non-200 first page raises."""
    from . import history_backfill as hb  # noqa: PLC0415

    rows: list[dict] = []
    info: dict[str, Any] = {"pages": 0, "truncated": False, "oldest_ts": math.nan}
    for page in range(pages):
        st, data = lim.get(url or hb.DATA_TRADES, {"market": cid, "limit": limit, "offset": page * limit})
        if st == 400 and page > 0:
            info["truncated"] = True
            break
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"trades status {st}")
        info["pages"] += 1
        got = [x for x in data if isinstance(x, dict)]
        rows.extend(got)
        ts = [num(x.get("timestamp")) for x in got]
        ts = [v for v in ts if math.isfinite(v)]
        oldest = min(ts) if ts else math.nan
        if ts:
            info["oldest_ts"] = min(oldest, info["oldest_ts"]) if math.isfinite(info["oldest_ts"]) else oldest
        if len(data) < limit or (ts and oldest <= t_reach):
            info["truncated"] = False
            break
        if page == pages - 1:
            info["truncated"] = True
    info["n_prints"] = len(rows)
    return rows, info


def reach_ok(info: dict, t_reach: float) -> bool:
    """True iff the fetched prints reach back to ``t_reach``: not truncated, or the oldest reachable print is at or before ``t_reach``."""
    if not info.get("truncated"):
        return True
    o = num(info.get("oldest_ts"))
    return bool(math.isfinite(o) and o <= t_reach)


# ---- statistics helpers ------------------------------------------------------------------------------------------------------------------------


def holm(pvals: dict[str, float], alpha: float) -> dict:
    """CB12-local STRICT Holm (reject iff p < alpha / (m - i) at every step so far); the shared ``c9.holm`` uses ``<=`` and is not changed. Every CB12 step-down uses this."""
    items = sorted(pvals.items(), key=lambda kv: (kv[1], kv[0]))
    m = len(items)
    out, running, rejecting = {}, 0.0, True
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        rejecting = rejecting and (p < alpha / (m - i))
        out[k] = {"p": p, "p_holm": running, "reject": bool(rejecting)}
    return out


def stage1_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA, family: tuple[str, ...] = STAGE1_HOLM_FAMILY) -> dict:
    """The full Stage-1 step-down at one-sided ``alpha`` over the FIXED ten tests (k1 = 10); a test not run / not testable / pending enters with p = 1."""
    extra = [k for k in pvals if k not in family]
    if extra:
        raise Refused(f"batch-Holm: {extra} are not in the fixed Stage-1 family {family}")
    full = {k: (1.0 if pvals.get(k) is None else float(pvals[k])) for k in family}
    return {"k": len(family), "alpha": alpha, "tests": holm(full, alpha), "not_run_as_p1": [k for k in family if pvals.get(k) is None]}


def early_stage1_ok(p: float | None) -> bool:
    """A test that finishes before the last Stage-1 result is judged against alpha / k1 = 0.005 (Holm's first step over all ten; never withdrawn)."""
    return p is not None and bool(p < EARLY_ALPHA)


def stage2_holm(pvals: dict[str, float | None], alpha: float = STAGE_ALPHA) -> dict:
    """One Holm at ``alpha`` over every CB12 test reaching Stage 2 (k2 = their number); not run -> p = 1."""
    full = {k: (1.0 if v is None else float(v)) for k, v in pvals.items()}
    return {"k": len(full), "alpha": alpha, "tests": holm(full, alpha) if full else {}}


def early_stage2_ok(p: float | None) -> bool:
    """A rep that finishes before k2 is known is judged against alpha / 10 (k = 10 is the largest possible count; never withdrawn). Strict ``<``, as Stage 1."""
    return p is not None and bool(p < STAGE_ALPHA / STAGE2_K_MAX)


def cluster_p(v, clusters: dict[str, Any], *, seed: int = SEED_BOOT, n_wild: int = N_WILD, alpha: float | None = None) -> dict:
    """One-sided p of mean(v) > 0 as the MAX over the declared cluster ways (CB10 small-G rule, CB12 seed 1212): >= 100 units, every way testable, >= 30 clusters."""
    return c10.cluster_p(v, clusters, seed=seed, n_wild=n_wild, alpha=alpha)


def cluster_se_mean(v, cl) -> float:
    """CR1 clustered standard error of mean(v) (cluster sums of centred values)."""
    v = np.asarray(v, float)
    n = len(v)
    if n < 2:
        return math.nan
    codes = {}
    idx = np.array([codes.setdefault(str(c), len(codes)) for c in cl])
    g = len(codes)
    if g < 2:
        return math.nan
    s = np.bincount(idx, weights=v - v.mean(), minlength=g)
    return float(math.sqrt(float((s**2).sum()) * g / (g - 1)) / n)


def one_sided_boot_p(draws: np.ndarray) -> float:
    d = np.asarray(draws, float)
    d = d[np.isfinite(d)]
    return float((1 + np.sum(d <= 0)) / (len(d) + 1)) if len(d) else 1.0


def placebo_advance_rate(draw_ps: list[float | None], gate_p: float = GATE_P) -> dict:
    return c10.placebo_advance_rate(draw_ps, gate_p)


def top_k_drop_mask(v, cl, k: int = TOP_DROP) -> np.ndarray:
    return c9.top_k_drop_mask(v, cl, k)


def mde(se: float, mult: float = 1.2) -> float:
    """(z_0.99 + z_0.80) x 1.2 x SE (the census MDE rule)."""
    return float((2.326 + 0.842) * mult * se)


# ---- Gamma key lookup, closed first, and the exclusion keys (q0241) ----------------------------------------------------------------------------


def lookup_keys_closed_first(lim, ids: list[str], *, per_request: int = LOOKUP_PER_REQUEST) -> tuple[dict[str, dict], int]:
    """Gamma lookup by market id (``closed=true`` first; the rest retried without it). A non-200 reply raises ``ApiError``."""
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


def load_exclusion_keys(keys_path: Path) -> tuple[set[str], dict[str, set[str]], dict, str]:
    """(ids, key sets, report, sha256) of a key file, verified against its report."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415

    keys_path = refuse_path(Path(keys_path))
    rep_path = keys_path.with_name(c9.EXCLUSION_REPORT_NAME)
    if not keys_path.exists() or not rep_path.exists():
        raise Refused(f"exclusion key files {keys_path} / {rep_path.name} missing")
    rep = json.loads(rep_path.read_text())
    sha = h5_seal.sha256_file(keys_path)
    if rep.get("keys_sha256") != sha:
        raise Refused(f"{keys_path} sha256 {sha} != report {rep.get('keys_sha256')}; refusing")
    ids = {str(r["market_id"]) for r in read_csv_gz(keys_path)}
    return ids, c6.load_key_sets(keys_path), rep, sha


def load_series_dates(keys_path: Path, rep: dict) -> dict[str, list[float]]:
    """``{series id: [startTime epochs of its excluded events]}`` from ``exclusion_series_dates.csv.gz`` next to the key file. A missing file is ``NotNow`` (exit 75, the job
    waits: a frame must never be built with the series-date key silently off); a sha256 that differs from the report (or a report without it) is a refusal."""
    from . import h5_seal  # noqa: PLC0415

    p = Path(keys_path).with_name(SERIES_DATES_NAME)
    if not p.exists():
        raise NotNow(f"{p.name} is missing next to {Path(keys_path).name} (q0241 writes it); pending")
    want = rep.get("series_dates_sha256")
    if not want or h5_seal.sha256_file(p) != want:
        raise Refused(f"{p.name} sha256 differs from the exclusion report (or the report records none); refusing")
    out: dict[str, list[float]] = {}
    for r in read_csv_gz(p):
        v = num(r.get("start_epoch"))
        if math.isfinite(v):
            out.setdefault(str(r["series_id"]), []).append(v)
    return out


def series_dates_stage(fr, event_ids: list[str], should_stop: Callable[[], bool] | None = None) -> tuple[dict | None, str | None]:
    """Resumable Gamma ``/events?id=`` lookup (<= 50 ids per request) of the events named in the exclusion keys that belong to a series: one row (series id, event id,
    startTime epoch) per series of the event -> ``exclusion_series_dates.csv.gz`` (run dir) + ``series_dates_report.json``. Events the venue does not return, or without a
    ``startTime``, are counted in the report (they cannot enter the series-date key); closed events are asked first, the rest again without the filter. The caller gates the
    not-returned share against ``MAX_UNVERIFIED_KEY_SHARE``."""
    from . import h5_seal  # noqa: PLC0415

    rdir = fr.rdir
    rep_path, out_path = rdir / SERIES_DATES_RUN_FILE, rdir / SERIES_DATES_NAME
    if rep_path.exists():
        return json.loads(rep_path.read_text()), None
    part = rdir / "series_dates_partial.jsonl"
    todo = sorted(set(event_ids))
    done: dict[int, dict] = {}
    if part.exists():
        for line in part.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                done[rec["batch"]] = rec
    per = LOOKUP_PER_REQUEST
    for b in range(math.ceil(len(todo) / per)):
        if b in done:
            continue
        why = fr.stop_reason(should_stop)
        if why:
            return None, why
        batch = todo[b * per:(b + 1) * per]
        by_id: dict[str, dict] = {}
        retried_open = 0
        for closed in (True, False):  # closed first (as the market lookup does), the rest retried without the filter
            ask_ids = [x for x in batch if x not in by_id]
            if not ask_ids:
                break
            params: dict = {"id": list(ask_ids), "limit": per}
            if closed:
                params["closed"] = "true"
            status, data = fr.lim.get(GAMMA_EVENTS, params)
            if status != 200 or not isinstance(data, list):
                raise ApiError(f"gamma events lookup status {status}")
            for e in data:
                if isinstance(e, dict) and e.get("id") is not None and str(e["id"]) in ask_ids:
                    by_id[str(e["id"])] = e
                    retried_open += int(not closed)
        rows, returned, no_start, no_series = [], 0, 0, 0
        for e in by_id.values():
            returned += 1
            start = parse_iso(e.get("startTime"))
            sids = [str(s["id"]) for s in (e.get("series") if isinstance(e.get("series"), list) else []) if isinstance(s, dict) and s.get("id") is not None]
            if not sids:
                no_series += 1
            elif not math.isfinite(start):
                no_start += 1
            else:
                rows += [[s, str(e["id"]), start] for s in sids]
        rec = {"batch": b, "ids": len(batch), "returned": returned, "found_without_closed_filter": retried_open, "no_start": no_start, "no_series_in_reply": no_series, "rows": rows}
        with part.open("a") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
        done[b] = rec
    allrows = sorted({(r[0], r[1], r[2]) for rec in done.values() for r in rec["rows"]})
    fr.budget.write_gz_csv(out_path, SERIES_DATES_COLUMNS, [list(r) for r in allrows])
    returned = sum(rec["returned"] for rec in done.values())
    n_not = len(todo) - returned
    rep = {"n_events": len(todo), "n_returned": returned, "n_not_returned": n_not, "not_returned_share": n_not / len(todo) if todo else 0.0,
           "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE, "found_without_closed_filter": sum(rec.get("found_without_closed_filter", 0) for rec in done.values()), "n_without_start": sum(rec["no_start"] for rec in done.values()),
           "n_without_series_in_reply": sum(rec["no_series_in_reply"] for rec in done.values()), "n_rows": len(allrows), "series_dates_sha256": h5_seal.sha256_file(out_path)}
    fr.budget.write(rep_path, json.dumps(rep, indent=1, sort_keys=True).encode())
    part.unlink(missing_ok=True)
    return rep, None


def exclusion_stage(fr, ids: set[str], should_stop: Callable[[], bool] | None = None) -> tuple[dict | None, str | None]:
    """Resumable Gamma lookup of ``ids`` (closed first, <= 50 per request) -> ``exclusion_keys.csv.gz`` (+ report) in the run dir."""
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
    for b in range(math.ceil(len(todo) / per)):
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
    out = [[x, int(x in rows), rows[x]["event_ids"] if x in rows else "", rows[x]["neg_risk_market_id"] if x in rows else "", rows[x]["series_ids"] if x in rows else ""] for x in todo]
    fr.budget.write_gz_csv(keys_path, c6.KEY_COLUMNS, out)
    n_missing = len(todo) - len(rows)
    rep = {"n_ids": len(todo), "n_found": len(rows), "n_missing": n_missing, "missing_share": n_missing / len(todo) if todo else 0.0, "found_only_without_closed_filter": retried,
           "keys_sha256": h5_seal.sha256_file(keys_path)}
    fr.budget.write(rep_path, json.dumps(rep, indent=1, sort_keys=True).encode())
    part.unlink(missing_ok=True)
    return rep, None


def c1_market_ids(matches_path: Path) -> set[str]:
    """The Polymarket market ids of the C1 pairs (``matches.json``, ids only: no price, outcome or text leaves this function)."""
    rows = json.loads(Path(matches_path).read_text())
    return {str(r["p_market_id"]) for r in rows if isinstance(r, dict) and r.get("p_market_id") is not None}


def exclusion_keys(out_root: Path, transport, *, rules_sha: str, hist_root: Path, base_path: Path, base_sha256: str, seals_dir: Path | None = None,
                   matches_path: Path | None = None, is_committed: Callable[[Path], bool] | None = None, rps: float = 2.0, disk_cap: int = int(0.01 * 1024**3),
                   budget_min: float | None = None, now: float | None = None, sleep=None, live_check=None, should_stop: Callable[[], bool] | None = None,
                   wall_clock: Callable[[], float] | None = None, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                   data_dumps_cap_gb: float = DATA_DUMPS_CAP_GB, free_fn=None) -> dict:
    """q0241. CB11's q0221 key file (sha256 pinned; MANDATORY: absent or an unset / wrong pin is a refusal) plus, by closed-first Gamma id lookup (<= 50 ids per
    request, resumable), every market id of the id sources named in section 1.3 that exists on the host (a missing file is recorded "absent at q0241"), of every
    committed seal copy (CB12's own excluded) and of the C1 pairs. More than 2% of ALL exclusion ids without metadata -> ``disjointness_unverified``."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import h5_seal  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    out_root, seals_dir = require_output_root(Path(out_root)), Path(seals_dir or cm.SEALS_DIR)
    base_path = Path(base_path)
    if not base_sha256 or base_sha256 == PIN_UNSET:
        raise Refused(f"the sha256 pin of the CB11 key file (--base-sha256) is unset ({PIN_UNSET}); the coordinator fills it in the queue draft from `sha256sum` on the host")
    got = h5_seal.sha256_file(base_path) if base_path.exists() else None
    if got != base_sha256:
        raise Refused(f"base key file {base_path} sha256 {got} != pinned {base_sha256}")
    base_ids = read_id_set(base_path)
    require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    set_ids: dict[str, int] = {}
    absent: list[str] = []
    new_ids: set[str] = set()
    for run, fn in ID_SOURCES:
        p = Path(hist_root) / run / fn
        if not p.exists():
            absent.append(f"{run}/{fn}")
            continue
        ids = read_id_set(p)
        set_ids[f"{run}/{fn}"] = len(ids)
        new_ids |= ids
    seal_ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=OWN_SEAL_COPIES, is_committed=is_committed)
    new_ids |= seal_ids
    c1_ids: set[str] = set()
    if matches_path is not None and Path(matches_path).exists():
        c1_ids = c1_market_ids(Path(matches_path))
        new_ids |= c1_ids
    new_ids -= base_ids
    fr = cm.open_run(out_root, EXCLUSION_RUN, transport, allowed_run_id=EXCLUSION_RUN, kind="cb12_exclusion_keys", label="CB12 exclusion keys",
                     params={"base_keys_sha256": base_sha256, "n_base_ids": len(base_ids), "n_new_ids": len(new_ids), "sets": set_ids, "sets_absent_at_q0241": absent,
                             "seal_copies_used": used, "seal_copies_skipped": skipped, "n_c1_market_ids": len(c1_ids), "evidence_role": EVIDENCE_ROLE_HIST},
                     rules_sha=rules_sha, key_fp="", disk_cap=disk_cap, rps=rps, budget_min=budget_min, now=now, sleep=sleep or time.sleep, live_check=live_check,
                     wall_clock=wall_clock or time.time, snapshot_root=snapshot_root, health_check=health_check)
    try:
        rep_new, stopped = exclusion_stage(fr, new_ids, should_stop)
    except (ApiError, RuntimeError) as exc:  # transient; the partial files make the re-run resume
        stopped = f"gamma_failed: {exc}"[:200]
        rep_new = None
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
    ev_with_series = sorted({e for r in rows if r[4] for e in str(r[2]).split(";") if e})
    try:
        rep_sd, stopped = series_dates_stage(fr, ev_with_series, should_stop)
    except (ApiError, RuntimeError) as exc:
        stopped = f"gamma_failed: {exc}"[:200]
        rep_sd = None
    if stopped:
        m = fr.manifest(stopped, {"transient": True})
        m["status"] = "in_progress"
        return m
    assert rep_sd is not None
    keys_out = out_root / "exclusion_keys.csv.gz"
    out_root.mkdir(parents=True, exist_ok=True)
    keys_out.write_bytes(hb._gz_csv_bytes(list(c6.KEY_COLUMNS), sorted(rows)))
    sd_out = out_root / SERIES_DATES_NAME
    sd_out.write_bytes((fr.rdir / SERIES_DATES_NAME).read_bytes())
    base_rep_p = base_path.with_name(c9.EXCLUSION_REPORT_NAME)
    base_rep = json.loads(base_rep_p.read_text()) if base_rep_p.exists() else {}
    n_all = int(base_rep.get("n_ids", len(base_ids))) + rep_new["n_ids"]
    n_missing = int(base_rep.get("n_missing", 0)) + rep_new["n_missing"]
    share = n_missing / n_all if n_all else 1.0
    sd_share = float(rep_sd.get("not_returned_share", 0.0))
    unverified = bool(share > MAX_UNVERIFIED_KEY_SHARE or sd_share > MAX_UNVERIFIED_KEY_SHARE)
    rep = {"n_ids": n_all, "n_missing": n_missing, "missing_share": share, "max_unverified_key_share": MAX_UNVERIFIED_KEY_SHARE, "series_dates_not_returned_share": sd_share,
           "disjointness": UNVERIFIED if unverified else "verified", "base_keys_sha256": base_sha256, "new": rep_new, "sets": set_ids,
           "sets_absent_at_q0241": absent, "seal_copies_used": used, "seal_copies_sha256": shas, "seal_copies_skipped": skipped, "n_c1_market_ids": len(c1_ids),
           "keys_sha256": h5_seal.sha256_file(keys_out), "series_dates": rep_sd, "series_dates_sha256": h5_seal.sha256_file(sd_out), "built_utc": cm.iso(time.time())}
    (out_root / c9.EXCLUSION_REPORT_NAME).write_text(json.dumps(rep, indent=1, sort_keys=True))
    status = UNVERIFIED if rep["disjointness"] == UNVERIFIED else EXCLUSION_KEYS_COMPLETE
    m = fr.manifest(None, {"exclusion_report": {k: rep[k] for k in ("n_ids", "n_missing", "missing_share", "disjointness", "keys_sha256")}, "status": status, "complete": True})
    m["status"] = status
    return m


# ---- trials ------------------------------------------------------------------------------------------------------------------------------------


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST) -> dict:
    """One ``cb12_descriptive`` line (EXCLUDE, counts 0): smoke, census, gates, strata, variants."""
    rec = {"kind": "cb12_descriptive", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_12:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)


def log_family(family: str, results: dict[str, dict], *, replication: bool = False, trials_path: Path | None = None, role: str = EVIDENCE_ROLE_HIST, results_sha256: str = "",
               placebos: dict[str, dict] | None = None, n_triggered: int | None = None) -> None:
    """Per-test ``cb12_test`` / ``cb12_replication`` lines (EXCLUDE, ``n_tests`` 0), placebo lines (0) and ONE count line ``ml_explain`` (source
    ``creative_batch_12:<family>[:rep]``) whose ``n_tests`` is the family's number of tests (Stage 1: all of them, a test behind a failed gate counted with p = 1) or
    the reps actually triggered (Stage 2). Exit 75 never reaches here."""
    if family not in FAMILY_PARTS:
        raise Refused(f"unknown CB12 count family {family!r}")
    allowed = FAMILY_REP_TESTS[family] if replication else FAMILY_TESTS[family]
    bad = [t for t in results if t not in allowed]
    if bad:
        raise Refused(f"{bad} are not CB12-{family} {'rep ' if replication else ''}tests {allowed}")
    tp = Path(trials_path) if trials_path else provenance.TRIALS_PATH
    kind = "cb12_replication" if replication else "cb12_test"
    for tid, result in results.items():
        p = result.get("p", 1.0)
        if not result.get("testable", True) or p is None:
            p = 1.0
        base = {"label": "EXPLORATORY", "evidence_role": role, "dataset": "creative_batch_12", "hypothesis": tid, "family": family, "results_sha256": results_sha256}
        provenance.append_trial({"kind": kind, **base, "p": p, "advance": bool(result.get("advance")), "testable": bool(result.get("testable", True)),
                                 "effect": result.get("effect"), "n": result.get("n"), "verdict": result.get("verdict"), "n_tests": 0}, tp)
        pl = (placebos or {}).get(tid)
        if pl:
            provenance.append_trial({"kind": kind, **{**base, "evidence_role": "placebo"}, "note": pl.get("note", "placebo"), "advance_rate": pl.get("advance_rate"),
                                     "n_draws": pl.get("n_draws"), "n_tests": 0}, tp)
    n = len(results) if n_triggered is None else int(n_triggered)
    provenance.append_trial({"kind": "ml_explain", "label": "EXPLORATORY", "evidence_role": role, "source": f"creative_batch_12:{family}{':rep' if replication else ''}",
                             "dataset": "creative_batch_12", "n_tests": n, "n_tests_by_family": {f"cb12_{family}{'_rep' if replication else ''}": n},
                             "hypotheses": sorted(results), "replication": bool(replication), "advanced": sorted(t for t, r in results.items() if r.get("advance")),
                             "results_sha256": results_sha256, "note": "CB12 count line: the family's tests (a test behind a failed gate is still counted, p = 1)"}, tp)


def sha256_obj(obj) -> str:
    return cm.sha_obj(obj)


# =====================================================================================================================================================
# Per-part rules hashing. Everything below is machinery (not hashed); the hashed content is the module-level functions, classes and UPPER_CASE constants.
# =====================================================================================================================================================


def _jsonable(v):
    """JSON form of a module constant, or the sentinel ``_jsonable`` itself if the value is not part of the declaration (paths, modules, callables)."""
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else str(v)
    if isinstance(v, re.Pattern):
        return {"regex": v.pattern, "flags": int(v.flags)}
    if isinstance(v, (tuple, list)):
        out = [_jsonable(x) for x in v]
        return _jsonable if any(x is _jsonable for x in out) else out
    if isinstance(v, dict):
        out = {str(k): _jsonable(x) for k, x in v.items()}
        return _jsonable if any(x is _jsonable for x in out.values()) else out
    return _jsonable


def module_constants(mod) -> dict:
    out = {}
    for name, val in sorted(vars(mod).items()):
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            j = _jsonable(val)
            if j is not _jsonable:
                out[name] = j
    return out


def module_funcs(mod, exclude: tuple[str, ...] = ()) -> list:
    """Every function and class DEFINED in ``mod`` (imports excluded), by name, minus ``exclude``."""
    members = [m for _, m in inspect.getmembers(mod) if (inspect.isfunction(m) or inspect.isclass(m)) and getattr(m, "__module__", None) == mod.__name__
               and m.__name__ not in exclude]
    return sorted(members, key=lambda f: f.__qualname__)


def common_funcs() -> list:
    return module_funcs(importlib.import_module(__name__), exclude=RULES_MACHINERY)


def _mods(names: tuple[str, ...]) -> list:
    """Import the named family modules. A missing module is skipped only if it is that module itself that is absent (``ModuleNotFoundError.name``)."""
    out = []
    for n in names:
        try:
            out.append(importlib.import_module(f".{n}", __package__))
        except ModuleNotFoundError as exc:
            if exc.name != f"{__package__}.{n}":
                raise
    return out


def family_modules(part: str) -> list:
    if part not in FAMILY_PARTS:
        raise Refused(f"unknown rules part {part!r}")
    return _mods(FAMILY_MODULES[part])


def part_funcs(part: str) -> list:
    """The functions hashed for ``part``: the common ones, plus (family parts) that family's own module(s) only."""
    funcs = list(common_funcs())
    if part == "common":
        smoke = importlib.import_module(".cb12_smoke", __package__)
        funcs += module_funcs(smoke)
    else:
        for mod in family_modules(part):
            funcs += module_funcs(mod)
    seen: set[int] = set()
    return [f for f in funcs if not (id(f) in seen or seen.add(id(f)))]


def rules_part_doc(part: str) -> dict:
    """The declared document of one rules part (no ``rules_sha256`` yet). ``common``: this module + the smoke orchestrator. A family part: this module's common
    rules + that family's module(s); ``part_declared: False`` while its module is absent or reports unmet pins (``part_unready()``)."""
    if part not in PARTS:
        raise Refused(f"unknown rules part {part!r}")
    this = importlib.import_module(__name__)
    consts = {"cb12_common": module_constants(this)}
    declared: dict[str, Any] = {}
    if part == "common":
        smoke = importlib.import_module(".cb12_smoke", __package__)
        consts["cb12_smoke"] = module_constants(smoke)
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
            consts[name] = module_constants(mod)
            declared[name] = mod.declared()
    funcs = part_funcs(part)
    src = {f"{f.__module__.rsplit('.', 1)[-1]}.{f.__qualname__}": hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs}
    return {"part": part, "part_declared": True, "rules_version": RULES_VERSION, "constants": consts, "declared": declared,
            "wallet": {"read": False, "note": "no CB12 job reads or stores a wallet field, a transaction hash, or the Data API side field"},
            "funcs_sha256": hashlib.sha256("\n".join(src[k] for k in sorted(src)).encode()).hexdigest(), "func_sources_sha256": dict(sorted(src.items()))}


def rules_part_file_doc(part: str) -> dict:
    d = json.loads(json.dumps(rules_part_doc(part), sort_keys=True, default=str))
    if d.get("part_declared") is False:
        return {**d, "rules_sha256": None}
    return {**d, "rules_sha256": cm.sha_obj(d)}


def rules_file_doc(parts: tuple[str, ...] = PARTS) -> dict:
    """The rules file: ``{"rules_version", "parts": {"common": {..., "rules_sha256"}, "M": {...}, ...}}``, one sha256 per part."""
    return {"rules_version": RULES_VERSION, "parts": {p: rules_part_file_doc(p) for p in parts}}


def write_rules(path: Path | None = None) -> Path:
    """Write the rules file. An existing file's DECLARED part must equal the code's (a declared part is never rewritten); a part that was "not declared" may become
    declared later (adding family E, F or O changes no other part). Regenerate with ``python scripts/run_cb12.py rules``."""
    path = Path(path or (cm.SEALS_DIR / "cb12_rules.json"))
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


def verify_rules(path: Path | None = None, *, require_committed: bool = True, part: str = "M") -> str:
    """Refuse (exit 2) unless the file's ``part`` equals the code's. Only that part's modules are imported (X never touches E / F / O / M). A part "not declared"
    refuses its job. Returns the part's ``rules_sha256``."""
    path = Path(path or (cm.SEALS_DIR / "cb12_rules.json"))
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
