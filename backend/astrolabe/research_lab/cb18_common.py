# ruff: noqa: E501
"""CB18 census readers and helpers (docs/research_lab/CREATIVE_BATCH_18.md sections 1.1, 2.1, 2.6, 3, 6; rules in ``cb18_rules_pre``, part ``pre``).

Only what the pre-censuses q0502-q0506 need: the census-input seal (built from release metadata, never from disk) and its completeness check; pin-checked file access (an unpinned
or mismatched file refuses, exit 2; a missing pinned file exits 75 "restore byte for byte, hash-checked"); streaming, field-whitelisted readers for captures, sidecars, sweep 1 and
trade samples; the whitelist exception (``chg_1h/1d/1w``, ``uma_resolution_statuses``, ``event_comment_count`` are turned into opaque byte digests at read time and are reachable only
through ``bytes_equal`` / ``is_empty_literal``); slot helpers (LT3, pinned); exact float CSV I/O (L1); and the SE-only proxy wrapper around the pinned CR1 engine.

No reader returns an outcome, a target or a later-capture price; the censuses decide which captures they read (k - 12 .. k at most).
"""

from __future__ import annotations

import fnmatch
import hashlib
import importlib.util
import json
import math
import re
from collections.abc import Callable, Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from . import cb17_census as cc
from . import cb17_pre as cp
from . import cb18_rules_pre as r
from . import live_tests3 as l3
from . import provenance

Refused = r.Refused
NotNow = r.NotNow

SPEC_GRID = {"grid": {"grid0_utc": r.GRID0_UTC, "grid_s": r.GRID_S, "slot_tol_s": r.SLOT_TOL_S}}
CHUNK_ROWS = 25_000
FLAG_ALL = r.BYTE_FLAG_CAPTURE_FIELDS + r.BYTE_FLAG_SIDECAR_FIELDS


# =====================================================================================================================================================
# time and slots
# =====================================================================================================================================================


def epoch_s(values) -> np.ndarray:
    """ISO strings -> epoch seconds (float; NaN if unparseable)."""
    s = pd.Series(values, dtype=object)
    dt = pd.to_datetime(s, utc=True, errors="coerce", format="ISO8601")
    out = dt.astype("int64").to_numpy().astype(float) / 1e9
    out[dt.isna().to_numpy()] = np.nan
    return out


def epoch_ms(values) -> np.ndarray:
    """ISO strings -> epoch milliseconds (float, floor to ms; NaN if missing or unparseable)."""
    s = pd.Series(values, dtype=object)
    dt = pd.to_datetime(s, utc=True, errors="coerce", format="ISO8601")
    ns = dt.astype("int64").to_numpy()
    out = (ns // 1_000_000).astype(float)
    out[dt.isna().to_numpy()] = np.nan
    return out


def stamp_epoch(dir_name: str) -> float:
    m = re.match(r"^(\d{8})T(\d{6})Z", dir_name)
    if not m:
        raise Refused(f"{dir_name}: no start stamp")
    d, t = m.group(1), m.group(2)
    return r.ep(f"{d[:4]}-{d[4:6]}-{d[6:8]}T{t[:2]}:{t[2:4]}:{t[4:6]}Z")


def slot_of(t: float) -> int | None:
    return l3.slot_of(t, SPEC_GRID)


def slot_time(k: int) -> float:
    return l3.slot_time(k, SPEC_GRID)


def slot_iso(k: int) -> str:
    return r.iso(slot_time(k))


def unavailable_slots() -> set[int]:
    return {slot_of(r.ep(s)) for s in r.UNAVAILABLE_CAPTURE_SLOTS}


# =====================================================================================================================================================
# the census-input seal (L4): built from release metadata only
# =====================================================================================================================================================


def _restore_module():
    p = Path(__file__).resolve().parents[2] / "scripts" / "restore_from_archive.py"
    spec = importlib.util.spec_from_file_location("cb18_restore_from_archive", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def draft_selection(draft: dict) -> tuple[list[str], list[str]]:
    """(tags, path globs) of a restore draft's argv."""
    a = list(draft["argv"])
    tags = [a[i + 1] for i, x in enumerate(a) if x == "--tag"]
    globs = [a[i + 1] for i, x in enumerate(a) if x == "--path-glob"]
    return tags, globs


def read_hashes(path: Path) -> dict[str, str]:
    out = {}
    for ln in Path(path).read_text().splitlines():
        if ln.strip():
            h, n = ln.split("  ", 1)
            out[n] = h
    return out


def select_release(tag: str, meta_dir: Path, globs: list[str], catalogue: Path) -> tuple[dict[str, str], str]:
    """The paths a restore draft selects from one release ({path: sha256 from files.sha256}) and the sha256 of files.sha256 (checked against MANIFEST.sha256)."""
    md = Path(meta_dir) / tag
    man = read_hashes(md / "MANIFEST.sha256")
    fsha = hashlib.sha256((md / "files.sha256").read_bytes()).hexdigest()
    if man.get("files.sha256") != fsha:
        raise Refused(f"{tag}: files.sha256 does not match MANIFEST.sha256")
    files = read_hashes(md / "files.sha256")
    rest = _restore_module()

    class _A:
        experiment = dir = since = until = None
        path_glob = globs

    paths, cat_sha = rest.select_paths(tag, files, str(catalogue), _A())
    missing = [p for p in paths if p not in files]
    if missing:
        raise Refused(f"{tag}: catalogue lists {len(missing)} paths not in files.sha256")
    bad = [p for p in paths if p in cat_sha and cat_sha[p] != files[p]]
    if bad:
        raise Refused(f"{tag}: catalogue sha256 differs from files.sha256 for {len(bad)} paths")
    sel = {p: files[p] for p in paths if any(fnmatch.fnmatch(p, g) for g in globs)}
    return sel, fsha


def build_census_seal(meta_dir: Path, drafts_dir: Path, c2_seal: Path, catalogue: Path) -> dict:
    """seals/cb18_census_inputs.json from the q0500 / q0501 drafts' tags and globs and the releases' files.sha256 (never from disk). Checks: each capture from exactly one release,
    the exact counts of section 3, q0501 == the LT3 C2 seal (paths, per-file sha256 and the releases' files_sha256_sha256)."""
    out_files: dict[str, dict] = {}
    releases: dict[str, dict] = {}
    jobs = {}
    for job, name in (("q0500", "q0500_cb18_census_restore_captures.json"), ("q0501", "q0501_cb18_census_restore_samples.json")):
        draft = json.loads((Path(drafts_dir) / name).read_text())
        tags, globs = draft_selection(draft)
        n = 0
        per_tag = {}
        for tag in tags:
            sel, fsha = select_release(tag, meta_dir, globs, catalogue)
            releases.setdefault(tag, {"files_sha256_sha256": fsha})
            per_tag[tag] = len(sel)
            for p, h in sel.items():
                if p in out_files and out_files[p]["release"] != tag:
                    raise Refused(f"{p} is selected from two releases ({out_files[p]['release']}, {tag}); each file must come from exactly one release")
                out_files[p] = {"sha256": h, "release": tag, "job": job}
                n += 1
        jobs[job] = {"tags": tags, "globs": globs, "files": n, "per_tag": per_tag}
    caps = sorted({p.split("/")[3] for p in out_files if p.startswith(r.ARCHIVE_PREFIX + "snapshots/")})
    for cid in caps:
        dup = [p for p in out_files if f"/snapshots/{cid}/" in p]
        if len({out_files[p]["release"] for p in dup}) != 1:
            raise Refused(f"capture {cid} spans releases")
    c2 = json.loads(Path(c2_seal).read_text())
    q1 = {p: v["sha256"] for p, v in out_files.items() if v["job"] == "q0501"}
    if set(q1) != set(c2["files"]) or any(q1[p] != c2["files"][p]["sha256"] for p in q1):
        raise Refused("q0501 does not select exactly the files (and sha256) of the LT3 C2 seal")
    for tag, v in c2["releases"].items():
        if releases.get(tag, {}).get("files_sha256_sha256") != v["files_sha256_sha256"]:
            raise Refused(f"release {tag}: files.sha256 hash differs from the LT3 C2 seal")
    doc = {"purpose": ("CB18 pre-census inputs (CREATIVE_BATCH_18.md L4, sections 3, 5): the q0500 captures and sweeps and the q0501 samples (= seals/lt3_census_inputs_C2.json). Every sha256 "
                       "is copied from the release's files.sha256 (whose own sha256 is checked against the release MANIFEST.sha256); nothing was hashed from disk. Written before any CB18 "
                       "census ran; counts-only use."),
           "rules_version": r.RULES_VERSION, "releases": releases, "jobs": jobs, "files": dict(sorted(out_files.items()))}
    check_completeness(doc)
    return doc


def seal_inventory(seal: dict) -> dict:
    caps: dict[str, set] = {}
    sweeps: dict[str, set] = {}
    samples: dict[str, set] = {}
    for p in seal["files"]:
        parts = p.split("/")
        if len(parts) != 5 or not p.startswith(r.ARCHIVE_PREFIX):
            raise Refused(f"unexpected seal path {p}")
        root, ident, fn = parts[2], parts[3], parts[4]
        {"snapshots": caps, "book_sweeps": sweeps, "trade_samples": samples}.get(root, {}).setdefault(ident, set()).add(fn)
        if root not in ("snapshots", "book_sweeps", "trade_samples"):
            raise Refused(f"seal path under an unexpected root: {p}")
    return {"captures": caps, "sweeps": sweeps, "samples": samples}


def check_completeness(seal: dict) -> dict:
    """The pin set's completeness (section 3): 67 captures x 4 files on the expected slots, 48 sweep directories x 2 files of 10-15/16, 23 samples x 4 files (= the C2 list). Refuses otherwise."""
    inv = seal_inventory(seal)
    caps, sweeps, samples = inv["captures"], inv["sweeps"], inv["samples"]
    errs = []
    if len(caps) != r.EXPECTED_CAPTURES:
        errs.append(f"{len(caps)} captures != {r.EXPECTED_CAPTURES}")
    if any(v != set(r.EXPECTED_CAPTURE_FILES) for v in caps.values()):
        errs.append("a capture lacks one of " + ",".join(r.EXPECTED_CAPTURE_FILES))
    slots = sorted(slot_of(stamp_epoch(c)) for c in caps)
    lo, hi = slot_of(r.ep("2026-10-11T22:31:00Z")), slot_of(r.ep(r.CENSUS_CUTOFF_SLOT))
    want = sorted(set(range(lo, hi + 1)) - unavailable_slots())
    if slots != want:
        errs.append("capture slots differ from [2026-10-11T22:31Z, 2026-10-17T22:31Z] minus the six unavailable slots")
    if len(sweeps) != r.EXPECTED_SWEEP_DIRS or any(v != set(r.EXPECTED_SWEEP_FILES) for v in sweeps.values()):
        errs.append(f"{len(sweeps)} sweep directories (want {r.EXPECTED_SWEEP_DIRS} x {r.EXPECTED_SWEEP_FILES})")
    if any(r.utc_day(stamp_epoch(s)) not in r.CENSUS_DAYS_SF for s in sweeps):
        errs.append("a sweep outside the 2026-10-15/16 passes")
    if len(samples) != r.EXPECTED_SAMPLES or any(v != set(r.EXPECTED_SAMPLE_FILES) for v in samples.values()):
        errs.append(f"{len(samples)} samples (want {r.EXPECTED_SAMPLES} x {r.EXPECTED_SAMPLE_FILES})")
    if r.UNSEALED_SAMPLE in samples:
        errs.append(f"the unsealed sample {r.UNSEALED_SAMPLE} is pinned")
    if len(seal["files"]) != r.EXPECTED_FILES_Q0500 + r.EXPECTED_FILES_Q0501:
        errs.append(f"{len(seal['files'])} files != {r.EXPECTED_FILES_Q0500 + r.EXPECTED_FILES_Q0501}")
    if errs:
        raise Refused("census-input seal incomplete or wrong: " + "; ".join(errs))
    return {"captures": len(caps), "sweeps": len(sweeps), "samples": len(samples), "files": len(seal["files"])}


def load_seal(path: Path) -> dict:
    p = Path(path)
    if p.name != r.CENSUS_INPUTS_SEAL:
        raise Refused(f"the census seal is {r.CENSUS_INPUTS_SEAL}, not {p.name}")
    if not p.exists():
        raise Refused(f"census seal {p} not found")
    doc = json.loads(p.read_text())
    check_completeness(doc)
    return doc


# =====================================================================================================================================================
# pin-checked file access
# =====================================================================================================================================================


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class PinnedTree:
    """Resolves archive paths to the restore tree and checks every file against the seal before it is opened. Unpinned or mismatched -> Refused (exit 2); missing -> NotNow (exit 75)."""

    def __init__(self, seal: dict, *, snapshot_root: Path | None = None, sweep_root: Path | None = None, sample_root: Path | None = None, verify: bool = True):
        self.seal = seal
        self.roots = {"snapshots": snapshot_root, "book_sweeps": sweep_root, "trade_samples": sample_root}
        for k, v in self.roots.items():
            if v is not None:
                r.refuse_path(Path(v))
                if Path(v).name != k:
                    raise Refused(f"--{k} root must be a directory named {k!r} (the archive layout), not {Path(v).name!r}")
        self.verify = verify
        self.checked: dict[str, str] = {}

    def path(self, root: str, ident: str, fn: str) -> Path:
        rel = f"{r.ARCHIVE_PREFIX}{root}/{ident}/{fn}"
        pin = (self.seal["files"].get(rel) or {}).get("sha256")
        if pin is None:
            raise Refused(f"{rel} is not pinned in {r.CENSUS_INPUTS_SEAL}; a census opens pinned files only")
        base = self.roots.get(root)
        if base is None:
            raise Refused(f"no root given for {root}")
        p = r.refuse_path(Path(base) / ident / fn)
        if not p.exists():
            raise NotNow(f"missing input {rel}: {r.TEMPFAIL_MESSAGE}")
        if self.verify and rel not in self.checked:
            got = sha256_file(p)
            if got != pin:
                raise Refused(f"{rel}: sha256 {got[:12]} != pinned {pin[:12]}")
            self.checked[rel] = got
        return p

    def ids(self, root: str) -> list[str]:
        return sorted(seal_inventory(self.seal)[{"snapshots": "captures", "book_sweeps": "sweeps", "trade_samples": "samples"}[root]])


# =====================================================================================================================================================
# the whitelist exception: opaque byte digests
# =====================================================================================================================================================


class ByteFlag:
    """The raw bytes of a whitelist-exception column, reduced at read time to a 64-bit digest per row (pandas hash_array of the string as written; never parsed, never stored). Only
    ``bytes_equal`` and ``is_empty_literal`` read it; no attribute exposes a value."""

    __slots__ = ("_d", "_empty", "_missing", "_field")

    def __init__(self, field: str, raw: Iterable[str]):
        if field not in FLAG_ALL:
            raise Refused(f"{field} is not a byte-flag field")
        a = np.asarray(list(raw), dtype=object)
        self._field = field
        self._d = pd.util.hash_array(a) if len(a) else np.zeros(0, np.uint64)
        self._missing = a == r.UMA_MISSING_LITERAL if len(a) else np.zeros(0, bool)
        self._empty = (a == r.UMA_EMPTY_LITERAL) if field == "uma_resolution_statuses" and len(a) else None

    def __getattribute__(self, name):  # any access other than these raises
        if name in ("take", "__len__", "__repr__", "__class__", "__init__", "__slots__"):
            return object.__getattribute__(self, name)
        raise Refused(f"ByteFlag {name!r}: the whitelist exception allows bytes_equal / is_empty_literal only")

    def __len__(self) -> int:
        return len(object.__getattribute__(self, "_d"))

    def __repr__(self) -> str:
        return f"ByteFlag({object.__getattribute__(self, '_field')}, n={len(self)})"

    def take(self, idx) -> ByteFlag:
        g = object.__getattribute__
        out = ByteFlag.__new__(ByteFlag)
        e = g(self, "_empty")
        object.__setattr__(out, "_field", g(self, "_field"))
        object.__setattr__(out, "_d", g(self, "_d")[idx])
        object.__setattr__(out, "_missing", g(self, "_missing")[idx])
        object.__setattr__(out, "_empty", None if e is None else e[idx])
        return out


def bytes_equal(a: ByteFlag, b: ByteFlag) -> np.ndarray:
    """Row-wise raw byte equality of two aligned ByteFlag columns of the same field (an empty field equals only an empty field)."""
    if not (isinstance(a, ByteFlag) and isinstance(b, ByteFlag)) or object.__getattribute__(a, "_field") != object.__getattribute__(b, "_field"):
        raise Refused("bytes_equal: two ByteFlag columns of the same field")
    return object.__getattribute__(a, "_d") == object.__getattribute__(b, "_d")


def is_empty_literal(x: ByteFlag) -> np.ndarray:
    """uma_resolution_statuses only: the bytes equal the writer's empty literal exactly (UMA_EMPTY_LITERAL); an empty field is 'missing' (False)."""
    e = object.__getattribute__(x, "_empty")
    if e is None:
        raise Refused("is_empty_literal applies to uma_resolution_statuses only")
    return e.copy()


def is_missing(x: ByteFlag) -> np.ndarray:
    return object.__getattribute__(x, "_missing").copy()


# =====================================================================================================================================================
# streaming, whitelisted readers
# =====================================================================================================================================================


def _check_fields(fields: Iterable[str], allowed: tuple[str, ...], what: str) -> list[str]:
    fs = list(fields)
    bad = [f for f in fs if f in r.FORBIDDEN_READ_FIELDS or (f not in allowed)]
    if bad:
        raise Refused(f"{what}: field(s) {bad} are not on the CB18 whitelist")
    return fs


def iter_chunks(path: Path, fields: list[str]):
    """Stream whitelisted raw-string chunks of a gzip CSV (bytes as written; no NA conversion). Missing columns are refused."""
    head = pd.read_csv(path, nrows=0)
    miss = [c_ for c_ in fields if c_ not in head.columns]
    if miss:
        raise Refused(f"{Path(path).name}: columns {miss} absent")
    yield from pd.read_csv(path, usecols=fields, dtype=str, keep_default_na=False, chunksize=CHUNK_ROWS)


def read_table(path: Path, fields: list[str], flags: list[str], *, keep: Callable[[pd.DataFrame], np.ndarray] | None = None, max_col: str | None = None, stats: dict | None = None) -> tuple[pd.DataFrame, dict[str, ByteFlag]]:
    """Stream a gzip CSV in chunks as raw strings (no NA conversion: bytes as written), keep rows passing ``keep`` and turn ``flags`` columns into ByteFlags. Missing columns are
    refused (a header without a whitelisted field is a schema change, never imputed)."""
    head = pd.read_csv(path, nrows=0)
    miss = [c for c in fields + flags if c not in head.columns]
    if miss:
        raise Refused(f"{Path(path).name}: columns {miss} absent")
    parts, fparts = [], {f: [] for f in flags}
    for ch in pd.read_csv(path, usecols=fields + flags, dtype=str, keep_default_na=False, chunksize=CHUNK_ROWS):
        if max_col is not None and stats is not None and len(ch):  # max over ALL rows, before any filter (the sealed capture-time rule)
            v = epoch_s(ch[max_col].to_numpy())
            if np.isfinite(v).any():
                stats["max"] = max(stats.get("max", -math.inf), float(np.nanmax(v)))
        if keep is not None:
            ch = ch[keep(ch)]
        for f in flags:
            fparts[f].append(ch[f].to_numpy(dtype=object))
        parts.append(ch[fields])
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=fields)
    fl = {f: ByteFlag(f, np.concatenate(v) if v else np.zeros(0, dtype=object)) for f, v in fparts.items()}
    return df, fl


def read_capture(tree: PinnedTree, cap_id: str, fields: Iterable[str], flags: Iterable[str] = (), *, keep=None, cutoff: str = r.CENSUS_ROW_CUTOFF) -> tuple[pd.DataFrame, dict[str, ByteFlag], dict]:
    """Capture rows (whitelisted fields; byte-flag fields as ByteFlags), one row per market_id and per condition_id (first in page order; counted). Refuses a capture whose stamp or
    whose last-page receipt lies after the cut-off. Returns (rows, flags, meta) with meta = {"t": last-page receipt, "start", "slot", "dup_market_id", "dup_condition_id"}."""
    fields = _check_fields(fields, r.CAPTURE_FIELDS, "capture")
    flags = _check_fields(flags, r.BYTE_FLAG_CAPTURE_FIELDS, "capture flags")
    for need in ("market_id", "condition_id", "received_utc"):
        if need not in fields:
            fields.append(need)
    start = r.guard_census_time(stamp_epoch(cap_id), f"capture {cap_id}", cutoff)
    man = json.loads(tree.path("snapshots", cap_id, "manifest.json").read_text())
    if man.get("state") != "complete":
        raise Refused(f"capture {cap_id} is not complete ({man.get('state')})")
    stats: dict = {}
    df, fl = read_table(tree.path("snapshots", cap_id, "rows.csv.gz"), fields, flags, keep=keep, max_col="received_utc", stats=stats)
    n0 = len(df)
    first = np.flatnonzero(~df["market_id"].duplicated().to_numpy())
    cond = df["condition_id"].iloc[first]
    dupc = (cond.ne("") & cond.duplicated()).to_numpy()
    keep_idx = first[~dupc]
    df = df.iloc[keep_idx].reset_index(drop=True)
    fl = {k: v.take(keep_idx) for k, v in fl.items()}
    t = float(stats["max"]) if "max" in stats else math.nan  # last page's receipt over all rows read, not only the kept ones
    r.guard_census_time(t, f"capture {cap_id} last page", cutoff)
    meta = {"t": t, "start": start, "slot": slot_of(start), "rows_kept": len(df), "dup_market_id": n0 - len(first), "dup_condition_id": int(dupc.sum()), "rows_read": n0}
    return df, fl, meta


def read_sidecar(tree: PinnedTree, cap_id: str, fields: Iterable[str], flags: Iterable[str] = (), *, market_ids: set | None = None) -> tuple[pd.DataFrame, dict[str, ByteFlag], dict]:
    """Sidecar rows of a capture (whitelisted fields; uma / comment count as ByteFlags), restricted to ``market_ids`` if given; one row per market_id. ``meta['status']``: the
    ext_manifest sidecar_status (a missing or partial sidecar makes its fields unknown for every market, never 0)."""
    fields = _check_fields(fields, r.SIDECAR_FIELDS, "sidecar")
    flags = _check_fields(flags, r.BYTE_FLAG_SIDECAR_FIELDS, "sidecar flags")
    if "market_id" not in fields:
        fields.append("market_id")
    em = json.loads(tree.path("snapshots", cap_id, "ext_manifest.json").read_text())
    status = em.get("sidecar_status")
    if status != "complete":
        return pd.DataFrame(columns=fields), {f: ByteFlag(f, []) for f in flags}, {"status": status}
    keep = None if market_ids is None else (lambda ch: ch["market_id"].isin(market_ids).to_numpy())
    df, fl = read_table(tree.path("snapshots", cap_id, "rows_ext.csv.gz"), fields, flags, keep=keep)
    first = np.flatnonzero(~df["market_id"].duplicated().to_numpy())
    df = df.iloc[first].reset_index(drop=True)
    fl = {k: v.take(first) for k, v in fl.items()}
    return df, fl, {"status": status}


def sweep_manifest(tree: PinnedTree, sweep_id: str) -> dict:
    r.guard_census_time(stamp_epoch(sweep_id), f"sweep {sweep_id}")
    return json.loads(tree.path("book_sweeps", sweep_id, "manifest.json").read_text())


def sweep1_by_capture(tree: PinnedTree) -> dict[str, str]:
    """{capture id: sweep-1 id} over the pinned sweeps (series_index 0, state complete)."""
    out: dict[str, str] = {}
    for sid in tree.ids("book_sweeps"):
        m = sweep_manifest(tree, sid)
        if m.get("series_index") == 0 and m.get("state") == "complete" and m.get("snapshot_id"):
            out.setdefault(str(m["snapshot_id"]), sid)
    return out


def read_sweep1(tree: PinnedTree, sweep_id: str) -> pd.DataFrame:
    """Sweep-1 token rows: token_id, market_id, receipt (epoch s), stamp_ms (book_timestamp, ms; NaN if missing), state."""
    df, _ = read_table(tree.path("book_sweeps", sweep_id, "rows.csv.gz"), list(r.SWEEP_FIELDS), [])
    rec = epoch_s(df["batch_receipt_utc"].to_numpy())
    if len(rec) and np.isfinite(rec).any():
        r.guard_census_time(float(np.nanmax(rec)), f"sweep {sweep_id}")
    out = pd.DataFrame({"token_id": df["token_id"].astype(str), "market_id": df["market_id"].astype(str), "receipt": rec,
                        "stamp_ms": pd.to_numeric(df["book_timestamp"], errors="coerce").to_numpy(float), "state": df["state"].astype(str)})
    return out.drop_duplicates("token_id").reset_index(drop=True)


def read_sample(tree: PinnedTree, sample_id: str, trade_fields: tuple[str, ...]) -> dict:
    """A sealed active-frame sample: manifest (snapshot_id, frame), plan members (market_id -> stratum), features (status, origin, n_returned, truncation) and the whitelisted
    trade columns. Wallet files are never opened; rows timed after the cut-off are refused."""
    if sample_id == r.UNSEALED_SAMPLE:
        raise Refused(f"{sample_id} is not in the C2 seal and is never used")
    r.guard_census_time(stamp_epoch(sample_id), f"sample {sample_id}")
    man = json.loads(tree.path("trade_samples", sample_id, "manifest.json").read_text())
    plan = json.loads(tree.path("trade_samples", sample_id, "plan.json").read_text())
    feat, _ = read_table(tree.path("trade_samples", sample_id, "features.csv.gz"), _check_fields(r.FEATURE_FIELDS, r.FEATURE_FIELDS, "features"), [])
    allowed = r.TRADE_FIELDS_R if "tx_hash" in trade_fields else r.TRADE_FIELDS_P
    tr, _ = read_table(tree.path("trade_samples", sample_id, "trades.csv.gz"), _check_fields(trade_fields, allowed, "trades"), [])
    ts = pd.to_numeric(tr["ts"], errors="coerce").to_numpy(float)
    if len(ts) and np.isfinite(ts).any():
        r.guard_census_time(float(np.nanmax(ts)), f"sample {sample_id} trade rows")
    members = {str(m["market_id"]): m.get("stratum") for m in plan.get("sample", [])}
    return {"manifest": {"snapshot_id": man.get("snapshot_id"), "frame": man.get("frame"), "state": man.get("state")}, "members": members, "features": feat, "trades": tr, "ts": ts}


# =====================================================================================================================================================
# categories, numbers, exact float I/O (L1), SE-only proxy
# =====================================================================================================================================================


def sports_flags(fee_type, fee_category, series_slugs) -> np.ndarray:
    return np.array([cc.is_sports_sidecar(a, b, c) for a, b, c in zip(fee_type, fee_category, series_slugs, strict=True)], dtype=bool)


def to_f64(values) -> np.ndarray:
    """Raw strings -> float64 (empty / unparseable -> NaN). Quotes, mids and spreads are always float64 (CB17 window fix 3)."""
    return pd.to_numeric(pd.Series(values, dtype=object), errors="coerce").to_numpy(dtype=np.float64)


def eq_f64(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Byte-equal after a float64 round-trip parse: equal values, or both missing."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    return (a == b) | (np.isnan(a) & np.isnan(b))


def write_csv_exact(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, float_format="%.17g")


def read_csv_exact(path: Path, **kw) -> pd.DataFrame:
    return pd.read_csv(path, float_precision="round_trip", **kw)


def proxy_se(y_c: np.ndarray, X: np.ndarray, fe: list, ways: dict[str, list]) -> dict:
    """SE only: the pinned CR1 engine (cb17_pre.fe_cluster_se, which never returns a point estimate) on y (cents) with the tested label in column 0; the census SE is the max over the
    event and 6 h block ways whatever their G (section 2.4); NaN if either way is not computable."""
    res = cp.fe_cluster_se(y_c, X, fe, ways, coef=0)
    by = res.get("se_by_way") or {}
    vals = [by.get(w) for w in r.SE_WAYS]
    se = max(vals) if all(v is not None and math.isfinite(v) and v > 0 for v in vals) else math.nan
    return {"n": res.get("n"), "se_c": se, "se_by_way_c": by, "g_by_way": res.get("g_by_way"), "note": res.get("note")}


def code_sha256() -> dict:
    here = Path(__file__).resolve().parent
    out = {}
    for name in ("cb18_rules_pre.py", "cb18_common.py", "cb18_pre.py", "cb18_map.py"):
        p = here / name
        if p.exists():
            out[name] = sha256_file(p)
    return out


def log_descriptive(label: str, payload: dict, *, trials_path: Path | None = None) -> dict:
    """One ``cb18_descriptive`` trials line (EXCLUDE, n_tests 0): pre-censuses, maps, the routing record. Never a test."""
    r.assert_clean_result(payload)
    rec = {"kind": r.TRIAL_KIND, "label": "EXPLORATORY", "evidence_role": r.EVIDENCE_ROLE_HIST, "source": f"creative_batch_18:{label}", "n_tests": 0, **payload}
    return provenance.append_trial(rec, Path(trials_path) if trials_path else provenance.TRIALS_PATH)
