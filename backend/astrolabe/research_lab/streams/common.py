# ruff: noqa: E501
"""Shared machinery for the prospective streams: polite HTTP, disk guard, change-only JSONL log, runner.

File format (one file per UTC day, ``<stream dir>/YYYYMMDD.jsonl``, append-only, never rewritten):

* ``{"kind": "row", "slot", "key", "reason", "sha", "data", "src_ts"?}``: the value of one key, written when the
  key is ``new``, ``changed`` (sha256 of the canonical JSON of ``data`` differs from the last written one) or due
  a ``checkpoint`` (not written for ``checkpoint_s`` seconds, or the first poll of a new day file).
* ``{"kind": "hash", "slot", "key", "sha"}``: checkpoint in hash-only mode (large text values, e.g. rule text):
  the value is unchanged and equals the last full row with that sha.
* ``{"kind": "gone", "slot", "key"}``: the key was in the previous complete view of its scope and is absent now.
* ``{"kind": "poll", "slot", "ok": true, ...}``: the COMMIT line of a poll, written after its rows in one
  write + fsync. Rows of a slot without a following ``ok`` poll line are torn (crash) and must be ignored.
  A failed poll writes ``{"kind": "poll", "ok": false, "error"}`` and nothing else: missing stays missing.

Unchanged keys are not repeated, so the state of a key at time ``t`` is its last row at or before ``t`` in the
same day file (every day file starts with a full view of the keys seen that day). ``src_ts`` (a source clock)
is stored next to ``data`` and never enters the hash. Receipt times are the collector's UTC clock.
"""

from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "arepo-stream-v1"
EX_TEMPFAIL = 75  # queue/cron convention: "not now" (disk headroom), never "not run"
USER_AGENT = "arepo-research/1.0 (read-only public-data research; never trades)"
RETRY_STATUS = {429, 500, 502, 503, 504}
STATE_FILE = "state.json"  # archive_rotate excludes *state*.json (cursor files, not evidence)
DU_CACHE_FILE = "du_state.json"
LOCK_FILE = "stream.lock"
TAIL_SCAN_BYTES = 256 * 1024

Transport = Callable[[str, dict, float], tuple[int, dict, bytes]]


class NotNow(Exception):
    """Exit 75: headroom short or similar; nothing was written."""


class FetchError(Exception):
    pass


def utc_iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def slot_iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def day_of(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y%m%d")


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


# ---- HTTP -------------------------------------------------------------------------------------------------------


def urllib_transport(url: str, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https hosts)
            body = r.read()
            hdrs = {k.lower(): v for k, v in r.headers.items()}
            status = r.status
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"transport: {type(e).__name__}: {e}") from e
    if hdrs.get("content-encoding") == "gzip":
        body = gzip.decompress(body)
    return status, hdrs, body


class Throttle:
    """At most ``rps`` requests per second: the next request waits until ``1 / rps`` after the previous one."""

    def __init__(self, rps: float, mono: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        if rps <= 0:
            raise ValueError("rps must be > 0")
        self.gap = 1.0 / rps
        self.mono, self.sleep = mono, sleep
        self.last: float | None = None

    def wait(self) -> None:
        if self.last is not None:
            dt = self.last + self.gap - self.mono()
            if dt > 0:
                self.sleep(dt)
        self.last = self.mono()


@dataclass
class Http:
    transport: Transport = urllib_transport
    rps: float = 1.0
    max_attempts: int = 3
    timeout: float = 20.0
    budget_s: float = 300.0
    clock: Callable[[], float] = time.time
    mono: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    requests: int = 0
    fetches: list = field(default_factory=list)

    def __post_init__(self) -> None:
        self.throttle = Throttle(self.rps, self.mono, self.sleep)
        self.deadline = self.mono() + self.budget_s

    def get_json(self, url: str, params: Iterable[tuple[str, Any]] | dict | None = None,
                 tag: str = "") -> Any:
        if params:
            url = f"{url}?{urllib.parse.urlencode(list(params.items()) if isinstance(params, dict) else list(params))}"
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json", "Accept-Encoding": "gzip"}
        last = ""
        for attempt in range(self.max_attempts):
            if self.mono() > self.deadline:
                raise FetchError(f"budget {self.budget_s:.0f}s exhausted ({tag})")
            self.throttle.wait()
            sent = self.clock()
            self.requests += 1
            try:
                status, hdrs, body = self.transport(url, headers, self.timeout)
            except FetchError as e:
                status, hdrs, body, last = None, {}, b"", str(e)
            recv = self.clock()
            rec = {"tag": tag, "status": status, "sent_utc": utc_iso(sent), "recv_utc": utc_iso(recv),
                   "bytes": len(body), "attempt": attempt + 1}
            if status == 200:
                try:
                    data = json.loads(body)
                except ValueError as e:
                    rec["error"] = "json"
                    self.fetches.append(rec)
                    raise FetchError(f"{tag}: invalid JSON") from e
                rec["sha256"] = hashlib.sha256(body).hexdigest()
                self.fetches.append(rec)
                return data
            self.fetches.append(rec)
            if status is not None and status not in RETRY_STATUS:
                raise FetchError(f"{tag}: HTTP {status}")
            last = last or f"HTTP {status}"
            if attempt + 1 < self.max_attempts:
                ra = hdrs.get("retry-after")
                try:
                    wait = min(60.0, float(ra)) if ra is not None else 2.0 * 4**attempt
                except ValueError:
                    wait = 2.0 * 4**attempt
                self.sleep(wait)
        raise FetchError(f"{tag}: gave up after {self.max_attempts} attempts ({last})")


# ---- disk guard -------------------------------------------------------------------------------------------------


def tree_bytes(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def du_bytes(path: Path) -> int:
    """``du -sk`` (fast on the host: about 0.2 s for 140k files); Python walk as the fallback."""
    try:
        out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True, timeout=60)
        if out.returncode == 0 and out.stdout.split():
            return int(out.stdout.split()[0]) * 1024
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return tree_bytes(path)


@dataclass
class DiskGuard:
    """Refuse (``NotNow``, exit 75) before writing when any headroom is short. Never deletes anything.

    * root free disk minus the poll's allowance must stay >= ``free_min_gb`` (the pass uses 4 GB);
    * ``data-dumps`` + allowance must stay <= ``cap_gb`` (the collector's cap is 45 GiB; jobs use 40);
      measured with ``du`` at most every ``du_ttl_s`` seconds (cached in the stream dir);
    * the stream's own directory must stay below ``stream_cap_gb``.
    """

    data_dumps: Path
    stream_dir: Path
    cap_gb: float = 40.0
    free_min_gb: float = 4.0
    stream_cap_gb: float = 2.0
    du_ttl_s: float = 900.0
    free_fn: Callable[[Path], int] | None = None
    du_fn: Callable[[Path], int] | None = None
    clock: Callable[[], float] = time.time

    def _data_dumps_bytes(self) -> int:
        cache = self.stream_dir / DU_CACHE_FILE
        now = self.clock()
        try:
            c = json.loads(cache.read_text())
            if now - float(c["t"]) < self.du_ttl_s and c.get("path") == str(self.data_dumps):
                return int(c["bytes"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
        b = (self.du_fn or du_bytes)(self.data_dumps)
        atomic_write(cache, json.dumps({"t": now, "path": str(self.data_dumps), "bytes": b}))
        return b

    def check(self, allowance_bytes: int) -> dict:
        probe = self.data_dumps
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        free = (self.free_fn or (lambda p: shutil.disk_usage(p).free))(probe)
        out = {"free_gb": round(free / 1e9, 3)}
        if (free - allowance_bytes) / 1e9 < self.free_min_gb:
            raise NotNow(f"root free disk {free / 1e9:.2f} GB - allowance < {self.free_min_gb} GB")
        used = self._data_dumps_bytes()
        out["data_dumps_gb"] = round(used / 1024**3, 3)
        if (used + allowance_bytes) / 1024**3 > self.cap_gb:
            raise NotNow(f"data-dumps {used / 1024**3:.2f} GiB + allowance > cap {self.cap_gb} GiB")
        mine = tree_bytes(self.stream_dir) if self.stream_dir.exists() else 0
        out["stream_gb"] = round(mine / 1024**3, 4)
        if (mine + allowance_bytes) / 1024**3 > self.stream_cap_gb:
            raise NotNow(f"stream dir {mine / 1024**3:.3f} GiB + allowance > stream cap {self.stream_cap_gb} GiB")
        return out


# ---- change-only log --------------------------------------------------------------------------------------------


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _repair_tail(path: Path) -> bool:
    """A crash can leave a torn last line; terminate it so the next line stays parseable. True if repaired."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    with open(path, "rb") as fh:
        fh.seek(-1, os.SEEK_END)
        if fh.read(1) == b"\n":
            return False
    with open(path, "ab") as fh:
        fh.write(b"\n")
        fh.flush()
        os.fsync(fh.fileno())
    return True


def committed_slots(path: Path, tail_bytes: int = TAIL_SCAN_BYTES) -> set[str]:
    """Slots with an ``ok`` poll line in the last ``tail_bytes`` of a day file (idempotency after a lost state)."""
    if not path.exists():
        return set()
    size = path.stat().st_size
    with open(path, "rb") as fh:
        fh.seek(max(0, size - tail_bytes))
        chunk = fh.read()
    out = set()
    for line in chunk.split(b"\n"):
        if b'"kind":"poll"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("ok"):
            out.add(rec.get("slot"))
    return out


@dataclass
class PollResult:
    items: dict[str, Any]
    scopes: tuple[str, ...] = ()  # key prefixes whose view is COMPLETE in this poll (gone detection)
    src_ts: dict[str, Any] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    extra_state: dict | None = None  # stream cache to persist (catalogue, frame); None keeps the old one


class ChangeLog:
    def __init__(self, stream_dir: Path, stream: str, checkpoint_s: float, *, hash_checkpoint: bool = False,
                 clock: Callable[[], float] = time.time):
        self.dir = Path(stream_dir)
        self.stream = stream
        self.checkpoint_s = checkpoint_s
        self.hash_checkpoint = hash_checkpoint
        self.clock = clock
        self.state_reset = False
        self.state = self._load_state()

    def _load_state(self) -> dict:
        p = self.dir / STATE_FILE
        if not p.exists():
            return {"keys": {}, "extra": {}}
        try:
            st = json.loads(p.read_text())
            if not isinstance(st.get("keys"), dict):
                raise ValueError("keys")
            st.setdefault("extra", {})
            return st
        except (OSError, ValueError, AttributeError):
            self.state_reset = True  # every key is re-written in full at the next commit
            return {"keys": {}, "extra": {}}

    @property
    def extra(self) -> dict:
        return self.state.setdefault("extra", {})

    def day_path(self, t: float) -> Path:
        return self.dir / f"{day_of(t)}.jsonl"

    def already_done(self, slot: str, t: float) -> bool:
        return slot == self.state.get("last_slot") or slot in committed_slots(self.day_path(t))

    def _append(self, path: Path, lines: list[str]) -> int:
        self.dir.mkdir(parents=True, exist_ok=True)
        _repair_tail(path)
        blob = ("\n".join(lines) + "\n").encode()
        with open(path, "ab") as fh:
            fh.write(blob)
            fh.flush()
            os.fsync(fh.fileno())
        return len(blob)

    def fail(self, slot: str, t0: float, error: str, meta: dict | None = None) -> dict:
        rec = {"kind": "poll", "schema": SCHEMA, "stream": self.stream, "slot": slot, "ok": False,
               "started_utc": utc_iso(t0), "finished_utc": utc_iso(self.clock()), "error": error[:500],
               **(meta or {})}
        self._append(self.day_path(t0), [canon(rec)])
        return rec

    def commit(self, slot: str, t0: float, res: PollResult, meta: dict | None = None) -> dict:
        now = self.clock()
        path = self.day_path(t0)
        new_file = not path.exists() or path.stat().st_size == 0
        keys: dict = self.state.setdefault("keys", {})
        lines: list[str] = []
        n = {"new": 0, "changed": 0, "checkpoint": 0, "gone": 0}
        for key in sorted(res.items):
            data = res.items[key]
            h = sha(data)
            prev = keys.get(key)
            if prev is None:
                reason = "new"
            elif prev[0] != h:
                reason = "changed"
            elif new_file or self.state_reset or now - float(prev[1]) >= self.checkpoint_s:
                reason = "checkpoint"
            else:
                continue
            n[reason] += 1
            if reason == "checkpoint" and self.hash_checkpoint:
                rec = {"kind": "hash", "slot": slot, "key": key, "sha": h}
            else:
                rec = {"kind": "row", "slot": slot, "key": key, "reason": reason, "sha": h, "data": data}
                if key in res.src_ts:
                    rec["src_ts"] = res.src_ts[key]
            lines.append(canon(rec))
            keys[key] = [h, now]
        for scope in res.scopes:
            for key in sorted(k for k in keys if k.startswith(scope) and k not in res.items):
                lines.append(canon({"kind": "gone", "slot": slot, "key": key}))
                del keys[key]
                n["gone"] += 1
        poll = {"kind": "poll", "schema": SCHEMA, "stream": self.stream, "slot": slot, "ok": True,
                "started_utc": utc_iso(t0), "finished_utc": utc_iso(now), "n_keys": len(res.items),
                **{f"n_{k}": v for k, v in n.items()}, "new_file": new_file, "state_reset": self.state_reset,
                "scopes": list(res.scopes), **(meta or {}), "meta": res.meta}
        lines.append(canon(poll))
        nbytes = self._append(path, lines)
        self.state.update({"schema": SCHEMA, "stream": self.stream, "last_slot": slot, "last_commit_utc": utc_iso(now)})
        if res.extra_state is not None:
            self.state["extra"] = res.extra_state
        atomic_write(self.dir / STATE_FILE, canon(self.state))
        self.state_reset = False
        return {**{k: v for k, v in poll.items() if k not in ("meta", "fetches")}, "bytes_written": nbytes}


# ---- runner -----------------------------------------------------------------------------------------------------


@dataclass
class StreamSpec:
    name: str
    dirname: str
    slot_s: int
    checkpoint_s: float
    allowance_bytes: int  # largest plausible write of one poll (disk-guard allowance)
    stream_cap_gb: float
    rps: float
    budget_s: float
    poll: Callable[..., PollResult]
    hash_checkpoint: bool = False


class _Lock:
    def __init__(self, path: Path):
        self.path = path
        self.fh = None

    def __enter__(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = open(self.path, "w")  # noqa: SIM115
        try:
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            return False

    def __exit__(self, *exc) -> None:
        if self.fh:
            self.fh.close()


def run_stream(spec: StreamSpec, data_dumps: Path, *, cap_gb: float = 40.0, free_min_gb: float = 4.0,
               stream_cap_gb: float | None = None, rps: float | None = None, budget_s: float | None = None,
               transport: Transport = urllib_transport, clock: Callable[[], float] = time.time,
               sleep: Callable[[float], None] = time.sleep, mono: Callable[[], float] = time.monotonic,
               free_fn=None, du_fn=None, poll_kwargs: dict | None = None) -> tuple[int, dict]:
    """One poll of one stream. Returns (exit code, summary). 0 = committed or nothing to do; 75 = headroom
    refusal (nothing written); 1 = the poll failed (an ``ok: false`` poll line was written)."""
    sdir = Path(data_dumps) / "research_lab" / spec.dirname
    sdir.mkdir(parents=True, exist_ok=True)
    with _Lock(sdir / LOCK_FILE) as got:
        if not got:
            return 0, {"stream": spec.name, "status": "busy"}
        t0 = clock()
        slot = slot_iso(t0 - t0 % spec.slot_s)
        log = ChangeLog(sdir, spec.name, spec.checkpoint_s, hash_checkpoint=spec.hash_checkpoint, clock=clock)
        if log.already_done(slot, t0):
            return 0, {"stream": spec.name, "status": "slot_done", "slot": slot}
        guard = DiskGuard(Path(data_dumps), sdir, cap_gb=cap_gb, free_min_gb=free_min_gb,
                          stream_cap_gb=stream_cap_gb if stream_cap_gb is not None else spec.stream_cap_gb,
                          free_fn=free_fn, du_fn=du_fn, clock=clock)
        try:
            g = guard.check(spec.allowance_bytes)
        except NotNow as e:
            return EX_TEMPFAIL, {"stream": spec.name, "status": "headroom", "slot": slot, "reason": str(e)}
        http = Http(transport=transport, rps=rps or spec.rps, budget_s=budget_s or spec.budget_s,
                    clock=clock, mono=mono, sleep=sleep)
        try:
            res = spec.poll(http, log.extra, t0=t0, data_dumps=Path(data_dumps), **(poll_kwargs or {}))
        except (FetchError, NotNow) as e:
            log.fail(slot, t0, str(e), {"requests": http.requests, "fetches": http.fetches, "guard": g})
            code = EX_TEMPFAIL if isinstance(e, NotNow) else 1
            return code, {"stream": spec.name, "status": "failed", "slot": slot, "error": str(e),
                          "requests": http.requests}
        summary = log.commit(slot, t0, res, {"requests": http.requests, "fetches": http.fetches, "guard": g})
        return 0, {"status": "committed", **summary, "requests": http.requests}
