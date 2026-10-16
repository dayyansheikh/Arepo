"""Seal, verify and access log for the CB1 replication datasets ``h5_cb1`` / ``h5_cb1_ladders``
(``docs/research_lab/CREATIVE_BATCH_1.md`` CB1-F, section 1.3 SEALED-H5).

``seal_run`` freezes a finished history run directory: sorted per-file sha256, a listing sha256
over that table, file count and bytes, the manifest's request clock, the capped-window exclusion
counts, git commit and seal time, plus a declaration (``history_seal_declaration``) with its own
hash. ``verify_seal`` recomputes everything and refuses on any added, missing or modified file.
``require_sealed`` is the guard every CB1 h5 reader calls first; ``read_sealed`` also appends to
``ACCESS_LOG.jsonl`` (time, job, git commit, files or globs, declaration hash).

Committed seal copy (the ONE format): for each sealed run there is exactly one repo file
``docs/research_lab/seals/<run_id>_SEAL.json`` (``h5_cb1_SEAL.json``, ``h5_cb1_ladders_SEAL.json``),
a byte-for-byte copy of the run's ``SEAL.json``. Its top-level keys include ``run_id`` and
``listing_sha256`` (the sha256 over the sorted ``<sha>  <path>`` table, see ``listing_sha256``);
``require_sealed`` / ``read_sealed`` accept it as ``committed_seal`` and refuse when it is missing,
unreadable, names another run, or carries a different ``listing_sha256``. ``write_committed_copy``
produces it (the ``seal`` command of ``scripts/cb1_h5.py`` calls it); a Claude session commits it.
No other seal file name or layout is valid.

Sealing writes only ``SEAL.json`` and an empty ``ACCESS_LOG.jsonl`` (both outside the listing) and
never touches the sealed data. An existing seal is never overwritten.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

SEAL_NAME = "SEAL.json"
ACCESS_LOG_NAME = "ACCESS_LOG.jsonl"
SEAL_VERSION = "h5-seal-v1"
TRIAL_KIND = "history_seal_declaration"
UNLISTED = {SEAL_NAME, ACCESS_LOG_NAME}
DECLARATION = {
    "dataset_role": "frozen-definition replication data for CB1; not a screen, not prospective",
    "read_rules": "verify listing hash first; append every read to ACCESS_LOG.jsonl; at most one "
    "read per CB1 hypothesis family; no outcome columns before the CB1 freeze commit; no "
    "discovery or re-estimation on this data",
    "information_end": "manifest request_clock_now (T_fetch) < T_seal of h4_seal",
}


# Run ids the seal CLIs accept. ``seal_run`` itself is id-agnostic (tests seal scratch ids); the CLIs call
# :func:`check_run_id`. h6_weather (CB2-F) is sealed by ``scripts/run_cb2.py seal`` because its seal
# also records the time-ordered split (``D_split``) computed from ``end_at``, city and title date.
H5_RUN_IDS = ("h5_cb1", "h5_cb1_ladders")
H6_RUN_IDS = ("h6_weather",)
ALLOWED_RUN_IDS = H5_RUN_IDS + H6_RUN_IDS
DECLARATION_H6 = {
    "dataset_role": "CB2-W weather screen (SCREEN block) and development holdout (HOLDOUT block); not "
    "prospective, not an edge claim",
    "read_rules": "verify listing hash first; append every read to ACCESS_LOG.jsonl; SCREEN reads refuse "
    "HOLDOUT and embargo ids; HOLDOUT is read once, after the CB2 freeze, only for W tests that advanced; "
    "no outcome column is opened before the CB2 freeze commit; results are written outside this directory",
    "information_end": "manifest request_clock_now (T_fetch6); every price and trade row capped at "
    "min(T_fetch6, T_seal 2026-10-22T00:00Z)",
    "split": "time-ordered by end date; group key = earliest end_at UTC date of the city-day; D_split = "
    "smallest date leaving <= 40% of sampled events in the HOLDOUT; 2-day embargo dropped from both",
}


def check_run_id(run_id: str, allowed: tuple[str, ...] = ALLOWED_RUN_IDS) -> str:
    """Refuse a run id outside the allowlist (CLI guard)."""
    if run_id not in allowed:
        raise SealError(f"run id {run_id!r} is not sealable here (allowed: {', '.join(allowed)})")
    return run_id


SEALS_DIR = Path(__file__).resolve().parents[3] / "docs" / "research_lab" / "seals"


class SealError(RuntimeError):
    """Seal missing, malformed, or the files no longer match it."""


def _utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def list_files(run_dir: Path) -> dict[str, str]:
    """{relative posix path: sha256} for every file except the seal and the access log.
    Temporary ``*.tmp`` files are listed too (a leftover one means an unfinished write)."""
    run_dir = Path(run_dir)
    out: dict[str, str] = {}
    for p in sorted(run_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(run_dir).as_posix()
            if rel in UNLISTED:
                continue
            out[rel] = sha256_file(p)
    return out


def listing_sha256(files: dict[str, str]) -> str:
    text = "".join(f"{sha}  {rel}\n" for rel, sha in sorted(files.items()))
    return hashlib.sha256(text.encode()).hexdigest()


def declaration_sha256(declaration: dict) -> str:
    return hashlib.sha256(json.dumps(declaration, sort_keys=True).encode()).hexdigest()


def _git_commit() -> str:
    import subprocess

    try:
        o = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           timeout=10, cwd=Path(__file__).resolve().parent)
        return o.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _incomplete_reason(manifest: dict) -> str | None:
    """A run is sealable only when its fetch finished (no pending stop reason)."""
    if manifest.get("stopped"):
        return f"manifest stopped = {manifest['stopped']!r}"
    if manifest.get("complete") is False:
        return "manifest complete = false"
    return None


def seal_run(run_dir: Path, *, trials_path: Path | None = None, allow_incomplete: bool = False,
             declaration_base: dict | None = None, extra: dict | None = None,
             source: str = "creative_batch_1:cb1_f_seal") -> dict:
    """Write ``SEAL.json`` and an empty ``ACCESS_LOG.jsonl``; append one trial line.

    ``declaration_base`` (default :data:`DECLARATION`), ``extra`` (additional top-level seal keys, e.g.
    the h6 ``split`` record) and ``source`` are the CB2 generalisation; with the defaults the seal bytes
    and the trial line are exactly those of the h5 seal."""
    run_dir = Path(run_dir)
    seal_path = run_dir / SEAL_NAME
    if seal_path.exists():
        raise SealError(f"{seal_path} exists; a seal is never rewritten")
    mpath = run_dir / "manifest.json"
    if not mpath.exists():
        raise SealError(f"no manifest.json in {run_dir}")
    manifest = json.loads(mpath.read_text())
    why = _incomplete_reason(manifest)
    if why and not allow_incomplete:
        raise SealError(f"refusing to seal an unfinished run: {why}")
    files = list_files(run_dir)
    total = sum((run_dir / r).stat().st_size for r in files)
    frame_rep = manifest.get("frame_report") or {}
    base = DECLARATION if declaration_base is None else declaration_base
    declaration = {**base, "run_id": manifest.get("run_id", run_dir.name)}
    seal = {
        "seal_version": SEAL_VERSION, "run_id": manifest.get("run_id", run_dir.name),
        "sealed_utc": _utc(), "git_commit": _git_commit(),
        "n_files": len(files), "total_bytes": total,
        "listing_sha256": listing_sha256(files), "files": dict(sorted(files.items())),
        "request_clock_now": manifest.get("request_clock_now"),
        "manifest_sha256": files.get("manifest.json"),
        "capped_window_exclusions": {
            "windows_dropped_capped": frame_rep.get("windows_dropped_capped"),
            "rows_in_dropped_windows": frame_rep.get("rows_in_dropped_windows"),
            "dropped_capped_by_day": frame_rep.get("dropped_capped_by_day"),
        },
        "sealed_incomplete": bool(why),
        "declaration": declaration, "declaration_sha256": declaration_sha256(declaration),
    }
    if extra:
        clash = set(extra) & set(seal)
        if clash:
            raise SealError(f"extra seal keys clash with core keys: {sorted(clash)}")
        seal.update(extra)
    seal_path.write_text(json.dumps(seal, indent=1, sort_keys=True))
    (run_dir / ACCESS_LOG_NAME).touch()
    from . import provenance

    kw = {} if trials_path is None else {"path": trials_path}
    trial_extra = {}
    if extra and isinstance(extra.get("split"), dict):
        trial_extra = {"d_split": extra["split"].get("d_split")}
    provenance.append_trial({
        "kind": TRIAL_KIND, "evidence_role": "exploratory_historical",
        "source": source, "run_id": seal["run_id"],
        "listing_sha256": seal["listing_sha256"], "n_files": seal["n_files"],
        "total_bytes": seal["total_bytes"], "declaration_sha256": seal["declaration_sha256"],
        "request_clock_now": seal["request_clock_now"], "n_tests": 0, **trial_extra,
    }, **kw)
    return seal


def verify_seal(run_dir: Path) -> dict:
    """Recompute the listing and compare with ``SEAL.json``; raises ``SealError`` on any
    modified, missing or extra file, a malformed seal or a changed declaration."""
    run_dir = Path(run_dir)
    seal_path = run_dir / SEAL_NAME
    if not seal_path.exists():
        raise SealError(f"{run_dir.name}: not sealed (no {SEAL_NAME})")
    try:
        seal = json.loads(seal_path.read_text())
        sealed = dict(seal["files"])
        want = seal["listing_sha256"]
    except (ValueError, KeyError, TypeError) as exc:
        raise SealError(f"{run_dir.name}: malformed {SEAL_NAME}: {exc}") from exc
    if listing_sha256(sealed) != want:
        raise SealError(f"{run_dir.name}: SEAL.json file table does not match its listing hash")
    if declaration_sha256(seal.get("declaration", {})) != seal.get("declaration_sha256"):
        raise SealError(f"{run_dir.name}: declaration changed after sealing")
    now = list_files(run_dir)
    bad = sorted(r for r in sealed if r in now and now[r] != sealed[r])
    missing = sorted(set(sealed) - set(now))
    extra = sorted(set(now) - set(sealed))
    if bad or missing or extra:
        raise SealError(f"{run_dir.name}: seal verification failed: modified={bad[:5]} "
                        f"missing={missing[:5]} extra={extra[:5]} "
                        f"({len(bad)}/{len(missing)}/{len(extra)})")
    return seal


def committed_seal_path(run_id: str, seals_dir: Path | None = None) -> Path:
    """The only valid committed seal location: ``<seals_dir>/<run_id>_SEAL.json``."""
    return Path(SEALS_DIR if seals_dir is None else seals_dir) / f"{run_id}_SEAL.json"


def write_committed_copy(run_dir: Path, seals_dir: Path | None = None) -> Path:
    """Copy the run's ``SEAL.json`` byte-for-byte to :func:`committed_seal_path`. An existing copy
    must be identical (never overwritten with different content)."""
    run_dir = Path(run_dir)
    seal = verify_seal(run_dir)
    data = (run_dir / SEAL_NAME).read_bytes()
    dest = committed_seal_path(seal["run_id"], seals_dir)
    if dest.exists():
        if dest.read_bytes() != data:
            raise SealError(f"{dest} exists with different content; a seal is never rewritten")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def require_sealed(run_dir: Path, committed_seal: Path | None = None) -> dict:
    """The guard every CB1 h5 reader and screen job calls first: the run must be sealed, verify,
    and (if ``committed_seal`` is given) the committed repo copy must exist and carry the same
    listing hash."""
    seal = verify_seal(run_dir)
    if committed_seal is not None:
        cp = Path(committed_seal)
        if not cp.exists():
            raise SealError(f"committed seal copy missing: {cp}")
        try:
            doc = json.loads(cp.read_text())
            got = doc.get("listing_sha256")
        except (ValueError, AttributeError) as exc:
            raise SealError(f"committed seal copy unreadable: {cp}") from exc
        if doc.get("run_id") not in (None, seal["run_id"]):
            raise SealError(f"committed seal {cp.name} is for run {doc.get('run_id')!r}, "
                            f"not {seal['run_id']!r}")
        if got != seal["listing_sha256"]:
            raise SealError(f"committed seal {cp.name} does not match {run_dir.name}")
    return seal


def log_access(run_dir: Path, job: str, files: list[str], *, declaration_sha: str | None = None
               ) -> dict:
    """Append one access record (UTC time, job id, git commit, files or globs, declaration hash)."""
    run_dir = Path(run_dir)
    if declaration_sha is None:
        sp = run_dir / SEAL_NAME
        declaration_sha = json.loads(sp.read_text()).get("declaration_sha256") if sp.exists() \
            else None
    rec = {"utc": _utc(), "job": job, "git_commit": _git_commit(), "files": list(files),
           "declaration_sha256": declaration_sha}
    with open(run_dir / ACCESS_LOG_NAME, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return rec


def read_sealed(run_dir: Path, job: str, globs: list[str],
                committed_seal: Path | None = None) -> list[Path]:
    """Verify the seal, log the read, and return the matching paths. Refuses on a mismatch or when
    nothing matches (a listed-but-missing read must be loud)."""
    run_dir = Path(run_dir)
    seal = require_sealed(run_dir, committed_seal)
    paths = sorted({p for g in globs for p in run_dir.glob(g) if p.is_file()})
    if not paths:
        raise SealError(f"{run_dir.name}: no file matches {globs}")
    log_access(run_dir, job, globs, declaration_sha=seal["declaration_sha256"])
    return paths
