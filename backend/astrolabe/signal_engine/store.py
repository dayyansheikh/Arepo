# ruff: noqa: E501
"""Storage primitives: write-once files, append-only day logs, the capture index, locks and guards.

Every data file the engine writes is WRITE-ONCE (temp file, fsync, hard link; an existing file is never touched).
Logs are append-only and partitioned by UTC day (``logs/<kind>-YYYYMMDD.jsonl``) so a day file becomes idle and the
nightly archive rotation can release it. ``state/`` holds rebuildable caches only (never evidence).
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import math
import os
import resource
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from . import config as C


@dataclass(frozen=True)
class Paths:
    engine: Path = C.ENGINE_ROOT
    snapshots: Path = C.SNAPSHOT_ROOT
    sweeps: Path = C.SWEEP_ROOT
    samples: Path = C.SAMPLE_ROOT
    xv_quotes: Path = C.XV_QUOTES_ROOT
    spec_dir: Path = C.SPEC_DIR

    def sub(self, *parts: str) -> Path:
        return Path(self.engine).joinpath(*parts)

    def quotes(self, cap: str) -> Path:
        return self.sub("quotes", f"{cap}.parquet")

    def features(self, cap: str) -> Path:
        return self.sub("features", f"{cap}.parquet")

    def meta(self, cap: str) -> Path:
        return self.sub("meta", f"{cap}.json")

    def predictions(self, cap: str, model_id: str) -> Path:
        return self.sub("predictions", cap, f"{model_id}.parquet")


# ---------------------------------------------------------------------------------------------- time


def epoch(v) -> float:
    try:
        return float(datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return math.nan


def iso(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def iso_s(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_of(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%d")


def now_ts() -> float:
    return datetime.now(UTC).timestamp()


GRID0 = epoch(C.GRID0_UTC)


def slot_of(t: float) -> int | None:
    """2-hour slot of a capture start; None if the start is more than SLOT_TOL_S off the grid."""
    if not math.isfinite(t):
        return None
    k = int(round((t - GRID0) / C.GRID_S))
    return k if abs(t - (GRID0 + k * C.GRID_S)) <= C.SLOT_TOL_S else None


def slot_time(k: int) -> float:
    return GRID0 + k * C.GRID_S


# ---------------------------------------------------------------------------------------------- hashing / json


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        v = o.item()
        return None if isinstance(v, float) and not math.isfinite(v) else v
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    return str(o)


def clean_json(o):
    """Recursively replace non-finite floats with None (strict JSON)."""
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    if isinstance(o, (float, np.floating)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def canonical(obj) -> bytes:
    return json.dumps(clean_json(obj), sort_keys=True, separators=(",", ":"), default=_json_default).encode()


def canonical_sha256(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


# ---------------------------------------------------------------------------------------------- write-once


def _link_into_place(tmp: Path, path: Path) -> bool:
    with open(tmp, "rb") as fh:
        os.fsync(fh.fileno())
    try:
        os.link(tmp, path)
    except FileExistsError:
        return False
    finally:
        tmp.unlink(missing_ok=True)
    return True


def write_once_parquet(path: Path, df: pd.DataFrame, metadata: dict | None = None) -> bool:
    """Write ``df`` as zstd parquet only if ``path`` does not exist (atomic). Returns False if it existed."""
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    if metadata:
        meta = dict(table.schema.metadata or {})
        meta[b"signal_engine"] = canonical(metadata)
        table = table.replace_schema_metadata(meta)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    pq.write_table(table, tmp, compression="zstd", compression_level=9)
    return _link_into_place(tmp, path)


def parquet_meta(path: Path) -> dict:
    md = pq.read_schema(path).metadata or {}
    raw = md.get(b"signal_engine")
    return json.loads(raw) if raw else {}


def read_parquet(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    return pq.read_table(path, columns=columns).to_pandas()


def write_once_json(path: Path, obj) -> bool:
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(clean_json(obj), sort_keys=True, indent=1, default=_json_default))
    return _link_into_place(tmp, path)


def write_once_bytes(path: Path, data: bytes) -> bool:
    path = Path(path)
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    return _link_into_place(tmp, path)


def replace_json(path: Path, obj) -> None:
    """Rewritable convenience file (state caches, latest.json, dashboard.json): never evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(clean_json(obj), sort_keys=True, separators=(",", ":"), default=_json_default))
    os.replace(tmp, path)


def append_log(paths: Paths, kind: str, rows: list[dict], at: float | None = None) -> Path:
    """Append rows to ``logs/<kind>-YYYYMMDD.jsonl`` (UTC day of ``at``), fsynced."""
    at = now_ts() if at is None else at
    p = paths.sub("logs", f"{kind}-{datetime.fromtimestamp(at, UTC):%Y%m%d}.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(clean_json(r), sort_keys=True, default=_json_default) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return p


def read_logs(paths: Paths, kind: str, since: float | None = None) -> list[dict]:
    out: list[dict] = []
    d = paths.sub("logs")
    if not d.exists():
        return out
    cutoff = None if since is None else datetime.fromtimestamp(since, UTC).strftime("%Y%m%d")
    for p in sorted(d.glob(f"{kind}-*.jsonl")):
        if cutoff is not None and p.stem.rsplit("-", 1)[-1] < cutoff:
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue  # a torn last line is ignored
    return out


# ---------------------------------------------------------------------------------------------- captures


def _manifest_head(path: Path) -> dict | None:
    try:
        m = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return {k: m.get(k) for k in ("state", "started_utc", "finished_utc", "capture_id", "snapshot_id", "sample_id",
                                  "sweep_id", "frame", "series_index")}


def discover_captures(paths: Paths, state: dict) -> list[dict]:
    """Complete snapshot captures on a grid slot, ordered by start. Manifests are parsed once (``state`` cache)."""
    seen = state.setdefault("captures", {})
    for mp in sorted(Path(paths.snapshots).glob("*/manifest.json")):
        cid = mp.parent.name
        if cid in seen:
            continue
        m = _manifest_head(mp)
        if not m or m.get("state") != "complete":
            continue  # an incomplete capture is re-checked next run
        t = epoch(m["started_utc"])
        seen[cid] = {"start": t, "finished": epoch(m.get("finished_utc")), "slot": slot_of(t)}
    caps, used = [], set()
    for cid, c in sorted(seen.items(), key=lambda kv: kv[1]["start"]):
        if c["slot"] is None or c["slot"] in used:
            continue  # off-grid or a second capture of a slot: the first complete one wins
        used.add(c["slot"])
        caps.append({"id": cid, **c, "dir": Path(paths.snapshots) / cid})
    return caps


def load_index(paths: Paths) -> dict[int, dict]:
    """Processed captures by slot, from the write-once ``meta/<capture>.json`` files (the engine's ground truth)."""
    out: dict[int, dict] = {}
    d = paths.sub("meta")
    if not d.exists():
        return out
    for p in sorted(d.glob("*.json")):
        try:
            m = json.loads(p.read_text())
        except (OSError, ValueError):
            continue
        out.setdefault(int(m["slot"]), m)
    return out


def load_state(paths: Paths, name: str = "state") -> dict:
    p = paths.sub("state", f"{name}.json")
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def save_state(paths: Paths, st: dict, name: str = "state") -> None:
    replace_json(paths.sub("state", f"{name}.json"), st)


# ---------------------------------------------------------------------------------------------- guards


@contextlib.contextmanager
def lock(paths: Paths, name: str):
    """Non-blocking exclusive lock; raises BlockingIOError if another run holds it."""
    p = paths.sub("state", f"{name}.lock")
    p.parent.mkdir(parents=True, exist_ok=True)
    fh = open(p, "w")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


def du_bytes(path: Path) -> int:
    path = Path(path)
    if not path.exists():
        return 0
    try:
        out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=300)
        return int(out.stdout.split()[0]) * 1024
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def disk_ok(paths: Paths, data_dumps_cap_gb: float | None) -> tuple[bool, str]:
    eng = du_bytes(paths.engine)
    if eng > C.ENGINE_DISK_CAP_GB * 1e9:
        return False, f"engine dir {eng / 1e9:.2f} GB > cap {C.ENGINE_DISK_CAP_GB} GB"
    if data_dumps_cap_gb:
        dd = du_bytes(Path(paths.engine).parent.parent)
        if dd > data_dumps_cap_gb * 2**30:
            return False, f"data-dumps {dd / 2**30:.1f} GiB > cap {data_dumps_cap_gb} GiB"
    return True, "ok"


def peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(r / (1024 * 1024) if sys.platform == "darwin" else r / 1024, 1)


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.ROOT, capture_output=True, text=True, timeout=15)
        return out.stdout.strip()[:12] or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"
