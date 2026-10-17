# ruff: noqa: E501
"""CB8 shared parts (docs/research_lab/CREATIVE_BATCH_8.md sections 1.4, 2.8, CB8-F and 5.1).

Strict wallet-key loader and fingerprint, the rules files (code-derived, function SOURCE hashed, committed before the first
read), the paged windowed print fetch, write-once smoke results, idle heartbeat for rolling jobs and the resumable chunk
object (``Cb8Run``). Data only: copies fields as the API returns them and computes no statistic. No outcome is read or
fetched here. Raw wallet addresses exist only in memory.
"""

from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import os
import platform
import socket
import stat
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import cb4_data as c4
from . import cb6_tail as c6
from . import h5_seal
from . import history_backfill as hb
from . import wallet_sidecar as ws

RULES_VERSION_HOLDERS = "cb8-holders-rules-v1"
RULES_VERSION_FLOW = "cb8-flow-rules-v1"
FETCH_VERSION = "cb8-fetch-v1"
KEY_FP_CONSTANT = b"arepo-cb8-wallet-key-fingerprint-v1"
KEY_FP_HEX = 16
WALLET_HASH_HEX = 32  # stored wallet hash = first 32 hex characters (128 bits) of the sidecar HMAC; declared in both rules files
SEALS_DIR = h5_seal.SEALS_DIR
HOLDERS_RULES_FILE = SEALS_DIR / "cb8_holders_rules.json"
FLOW_RULES_FILE = SEALS_DIR / "cb8_flow_rules.json"
DATA_DUMPS = c4.DATA_DUMPS
CB8_DIR = DATA_DUMPS / "research_lab" / "creative_batch8"
HIST_ROOT = c4.HIST_ROOT
DATA_DUMPS_FETCH_CAP_GB = 12.5
REFUSED_EXIT, DISK_BUDGET_EXIT, TEMPFAIL_EXIT = 2, 4, 75
DISK_BUDGET_TOKEN = "disk_budget"
NO_SEAL_EPOCH = 4102444800.0  # 2100-01-01: no CB8 fetch is T_seal-bound
HEARTBEAT_S = 10 * 3600.0  # a rolling job that is idle exits 0 at least this often so the queue's 48-tempfail count resets
MAX_ITEM_ATTEMPTS = 3
DAY = 86400.0
HOUR = 3600.0

Refused = c6.Refused
NotNow = c6.NotNow
ApiError = c4.ApiError
SealError = h5_seal.SealError

REFUSED_RUN_IDS = ("h1_first", "h2_main", "h3_power", "h4_seal", "h5_cb1", "h5_cb1_ladders", "h6_weather", "h7_cb4_era",
                   "h7_cb4_series", "h8_tail", "h8_text", "h8_geo")
REFUSED_ROOTS = ("cb1_extract", "cb2_extract", "cb3_extract", "cb4_extract", "cb5_extract", "cb6_extract", "cb7_extract",
                 "cb3_followup", "cb6_followup", "cross_venue", "cross_venue_live", "surprise_live", "live_trades", "trade_samples")


# ---- helpers -----------------------------------------------------------------------------------------------------------


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def ep(s: str) -> float:
    return c4._ep(s)


def sha_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def refuse_run_id(run_id: str, allowed: str) -> str:
    if run_id in REFUSED_RUN_IDS:
        raise Refused(f"run id {run_id!r} is sealed or belongs to another batch; CB8 refuses it")
    if run_id != allowed:
        raise Refused(f"this command writes only {allowed!r}, not {run_id!r}")
    return run_id


def refuse_path(path: Path) -> Path:
    if any(part in REFUSED_ROOTS for part in Path(path).parts):
        raise Refused(f"path {path} is under a refused CB1-CB7 / live root; CB8 refuses it")
    return Path(path)


def write_json_atomic(path: Path, doc: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=True, default=float))
    os.replace(tmp, path)


def write_once_json(path: Path, doc: dict) -> None:
    """Exclusive create. Raises :class:`Refused` if the file exists (smoke results are write-once)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x") as fh:
            fh.write(json.dumps(doc, indent=1, sort_keys=True, default=float))
    except FileExistsError:
        raise Refused(f"{path} already exists; it is write-once") from None


# ---- wallet key: strict loader, fingerprint, hash --------------------------------------------------------------------------


def key_fingerprint(key: bytes) -> str:
    """First 16 hex characters of HMAC-SHA256(key, fixed constant). Not the key."""
    return hmac.new(key, KEY_FP_CONSTANT, hashlib.sha256).hexdigest()[:KEY_FP_HEX]


def load_wallet_key_strict(path: Path | None = None, pinned_fp: str | None = None) -> bytes:
    """Read the HMAC key WITHOUT ever creating it. Refuses (:class:`Refused`, exit 2) if the file is missing, unreadable, empty
    or group/world-accessible, or if ``pinned_fp`` is given and the key's fingerprint differs."""
    p = Path(path) if path else ws.key_path()
    try:
        st = p.stat()
    except OSError:
        raise Refused(f"wallet hash key {p} is missing or unreadable; CB8 never creates a key") from None
    if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077:
        raise Refused(f"wallet hash key {p} is not a regular file with mode 600")
    try:
        key = p.read_bytes()
    except OSError:
        raise Refused(f"wallet hash key {p} is unreadable") from None
    if not key:
        raise Refused(f"wallet hash key {p} is empty")
    if pinned_fp is not None and key_fingerprint(key) != pinned_fp:
        raise Refused("wallet hash key fingerprint differs from the pinned wallet_key_fingerprint; refusing (hashes would not join)")
    return key


def hash_wallet(key: bytes, address: object) -> str | None:
    """The sidecar HMAC (lower-cased address) truncated to ``WALLET_HASH_HEX`` characters; ``None`` for a blank address."""
    h = ws.hash_wallet(key, address)
    return h[:WALLET_HASH_HEX] if h else None


# ---- rules files -------------------------------------------------------------------------------------------------------------


def _kind_module(kind: str):
    if kind == "holders":
        from . import cb8_holders as mod  # noqa: PLC0415
    elif kind == "flow":
        from . import cb8_flow as mod  # noqa: PLC0415
    else:
        raise Refused(f"unknown rules kind {kind!r}")
    return mod


def rules_doc(kind: str) -> dict:
    """Code-derived rules (without fingerprint and own hash). The SOURCE of every rule function is hashed, so a changed rule
    function invalidates the committed file."""
    mod = _kind_module(kind)
    funcs = list(mod.rule_funcs()) + [load_wallet_key_strict, key_fingerprint, hash_wallet, windowed_prints, _parse_print]
    src = "\n".join(inspect.getsource(f) for f in funcs)
    return {
        "rules_version": RULES_VERSION_HOLDERS if kind == "holders" else RULES_VERSION_FLOW,
        "declared": mod.declared(),
        "wallet": {"hash": f"HMAC-SHA256(key, lower-cased proxyWallet), first {WALLET_HASH_HEX} hex characters",
                   "key_file": "~/.arepo/wallet_hash_key (or AREPO_WALLET_HASH_KEY_PATH), mode 600, never created by CB8",
                   "fingerprint": f"first {KEY_FP_HEX} hex of HMAC-SHA256(key, {KEY_FP_CONSTANT.decode()!r})",
                   "raw_addresses_stored": False},
        "disk": {"data_dumps_fetch_cap_gb": DATA_DUMPS_FETCH_CAP_GB, "headroom_exit": TEMPFAIL_EXIT, "disk_budget_exit": DISK_BUDGET_EXIT},
        "funcs_sha256": hashlib.sha256(src.encode()).hexdigest(),
        "func_sources_sha256": {f.__qualname__: hashlib.sha256(inspect.getsource(f).encode()).hexdigest() for f in funcs},
    }


def rules_file_doc(kind: str, fingerprint: str) -> dict:
    d = rules_doc(kind)
    d["wallet_key_fingerprint"] = fingerprint
    return {**d, "rules_sha256": sha_obj(d)}


def write_rules(kind: str, path: Path, fingerprint: str) -> Path:
    path = Path(path)
    want = rules_file_doc(kind, fingerprint)
    if path.exists() and json.loads(path.read_text()) != want:
        raise Refused(f"{path} exists with different content; a rules file is never rewritten")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(want, indent=1, sort_keys=True) + "\n")
    return path


def verify_rules(kind: str, path: Path, *, require_committed: bool = True) -> tuple[str, str]:
    """Refuse (exit 2) unless the rules file equals the code's. Returns (``rules_sha256``, pinned ``wallet_key_fingerprint``)."""
    path = Path(path)
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
    fp = doc.get("wallet_key_fingerprint")
    if not isinstance(fp, str) or len(fp) != KEY_FP_HEX:
        raise Refused(f"rules file {path} has no valid wallet_key_fingerprint")
    want = rules_file_doc(kind, fp)
    if doc != want:
        raise Refused(f"rules hash mismatch: file {doc.get('rules_sha256')} != code {want['rules_sha256']}")
    return want["rules_sha256"], fp


# ---- disk / idle ---------------------------------------------------------------------------------------------------------------


def require_room(data_dumps: Path | None, cap_gb: float, allowance_bytes: int) -> None:
    if data_dumps is not None:
        c6.require_data_dumps_room(Path(data_dumps), cap_gb, allowance_bytes / 1024**3)


def idle(rdir: Path, why: str, now: float, heartbeat_s: float = HEARTBEAT_S, kind: str = "waiting") -> dict:
    """A rolling job with nothing to do now. Normally ``NotNow`` (exit 75: the queue waits 30 minutes). At least every
    ``heartbeat_s`` it instead returns a clean result (exit 0, ``status: idle_heartbeat``) so the queue's count of consecutive
    tempfails (limit 48, about 24 h) resets and the job is never marked failed while it waits."""
    rdir = Path(rdir)
    rdir.mkdir(parents=True, exist_ok=True)
    hp = rdir / "heartbeat.json"
    last = json.loads(hp.read_text()).get("epoch", 0.0) if hp.exists() else 0.0
    if now - last >= heartbeat_s:
        write_json_atomic(hp, {"epoch": now, "utc": iso(now), "idle": why, "idle_kind": kind})
        return {"status": "idle_heartbeat", "idle": why, "idle_kind": kind, "complete": False, "stopped": None}
    raise NotNow(why)


def room_or_idle(rdir: Path, data_dumps: Path | None, cap_gb: float, allowance_bytes: int, now: float) -> dict | None:
    """Headroom check for a rolling job: ``None`` if there is room, else the idle result (``idle_kind`` = ``headroom``, a heartbeat at
    least every 10 h) so a long shortage never exhausts the queue's 48-tempfail limit."""
    try:
        require_room(data_dumps, cap_gb, allowance_bytes)
    except NotNow as exc:
        return idle(rdir, str(exc), now, kind="headroom")
    return None


# ---- paged print fetch -----------------------------------------------------------------------------------------------------------


def _parse_print(x: Any, key: bytes) -> dict | None:
    try:
        ts, idx = int(x["timestamp"]), int(x["outcomeIndex"])
        size, price = float(x["size"]), float(x["price"])
        side = str(x["side"]).upper()
        if idx not in (0, 1) or side not in ("BUY", "SELL") or not (size >= 0 and 0.0 <= price <= 1.0):
            return None
    except (KeyError, TypeError, ValueError):
        return None
    return {"ts": ts, "idx": idx, "side": 1 if side == "BUY" else -1, "price": price, "size": size,
            "yes_price": price if idx == 0 else 1.0 - price, "yes_side": 1 if (side == "BUY") == (idx == 0) else -1,
            "wallet": hash_wallet(key, x.get("proxyWallet")), "tx": str(x.get("transactionHash") or "")}


def windowed_prints(lim: hb.Limiter, cid: str, start: int, end: int, max_pages: int, key: bytes, *, limit: int = 1000
                    ) -> tuple[list[dict], dict]:
    """All taker prints of one condition id with ``start <= ts <= end`` (venue timestamp), offset-paged, newest first.
    A non-200 reply raises :class:`ApiError` (a failed request is never "no data"). A window that still has a full last page
    after ``max_pages`` pages is ``capped``: the caller must treat it as unavailable. Rows outside the window, malformed rows and
    duplicate fingerprints are dropped and counted; the order is verified (``order_ok``). The raw address is hashed on parse
    and is not kept."""
    rows: list[dict] = []
    seen: set[tuple] = set()
    info = {"pages": 0, "n_raw": 0, "malformed": 0, "duplicates": 0, "out_of_window": 0, "capped": False, "order_ok": True,
            "missing_wallet": 0}
    prev_ts: int | None = None
    for page in range(max_pages):
        status, data = lim.get(hb.DATA_TRADES, {"market": cid, "start": int(start), "end": int(end), "takerOnly": "true",
                                                "limit": limit, "offset": page * limit})
        if status == 400 and page > 0:  # the API refuses a deep offset: the window is capped (unavailable), not a failed request
            info["capped"] = True
            info["offset_cap_status"] = 400
            return rows, info
        if status != 200 or not isinstance(data, list):
            raise ApiError(f"trades status {status}")
        info["pages"] += 1
        info["n_raw"] += len(data)
        for x in data:
            r = _parse_print(x, key)
            if r is None:
                info["malformed"] += 1
                continue
            if prev_ts is not None and r["ts"] > prev_ts:
                info["order_ok"] = False
            prev_ts = r["ts"]
            if not (start <= r["ts"] <= end):
                info["out_of_window"] += 1
                continue
            fp = (r["ts"], r["idx"], r["side"], r["price"], r["size"], r["wallet"], r["tx"])
            if fp in seen:
                info["duplicates"] += 1
                continue
            seen.add(fp)
            if r["wallet"] is None:
                info["missing_wallet"] += 1
            rows.append(r)
        if len(data) < limit:
            return rows, info
    info["capped"] = True
    return rows, info


# ---- the resumable chunk object --------------------------------------------------------------------------------------------------


class Cb8Run(c4.FetchRun):
    """``cb4_data.FetchRun`` with a CB8 manifest: rules hash, key fingerprint, per-file sha256 table, run location. Not bound to
    T_seal."""

    rules_sha256 = ""
    key_fp = ""
    label = "CB8"

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.counts = dict(self.prior.get("counts") or {})
        self.file_sha256: dict[str, str] = dict(self.prior.get("file_sha256") or {})
        self.extra_state: dict = dict(self.prior.get("state") or {})

    def manifest(self, stopped: str | None, extra: dict | None = None) -> dict:
        m = {
            "provenance": hb.PROVENANCE, "evidence_role": self.params.get("evidence_role", hb.EVIDENCE_ROLE), "version": FETCH_VERSION,
            "run_id": self.run_id, "kind": self.kind, "purpose": f"{self.label} data; not an edge claim",
            "git_commit": hb._git_commit(), "rules_sha256": self.rules_sha256, "wallet_key_fingerprint": self.key_fp,
            "run_location": {"host": socket.gethostname(), "platform": sys.platform, "python": platform.python_version()},
            "params": {**self.params, "cap_utc": iso(self.cap_epoch), "max_rps": self.rps, "disk_cap_bytes": self.disk_cap,
                       "budget_min": self.budget_min},
            "started_utc": self.prior.get("started_utc", iso(self.t_start)), "updated_utc": iso(time.time()),
            "request_clock_now": self.prior.get("request_clock_now", iso(self.now)),
            "requests": {"total_this_session": self.lim.requests, "retries": self.lim.retries, "http_429": self.pol.n429,
                         "yielded_to_live_s": self.lim.yielded_s, "rps_halved": self.pol.halved},
            "stopped": stopped, "disk_bytes": self.budget.scan(), "elapsed_s_this_session": round(time.time() - self.t_start, 1),
            "counts": dict(self.counts), "file_sha256": dict(sorted(self.file_sha256.items())),
            "state": self.extra_state, **(extra or {}),
        }
        m.setdefault("complete", False)
        self.budget.cap += 10**7  # manifest bookkeeping must stay writable at the cap
        self.budget.write(self.mpath, json.dumps(m, indent=1, sort_keys=True, default=float).encode())
        return m

    def record_file(self, path: Path) -> None:
        self.file_sha256[Path(path).relative_to(self.rdir).as_posix()] = h5_seal.sha256_file(path)


def open_run(root: Path, run_id: str, transport, *, allowed_run_id: str, kind: str, label: str, params: dict, rules_sha: str, key_fp: str,
             disk_cap: int, rps: float, budget_min: float | None, now: float | None, sleep: Callable[[float], None], live_check,
             wall_clock: Callable[[], float], snapshot_root: Path | None, health_every_s: float = 600.0, health_check=None,
             cap_at: str = "2100-01-01T00:00Z") -> Cb8Run:
    root = refuse_path(Path(root))
    refuse_run_id(run_id, allowed_run_id)
    fr = Cb8Run(root, run_id, transport, kind=kind, params=params, rps=rps, disk_cap=disk_cap, budget_min=budget_min, now=now,
                sleep=sleep, live_check=live_check, wall_clock=wall_clock, t_seal_epoch=NO_SEAL_EPOCH, snapshot_root=snapshot_root,
                health_every_s=health_every_s, health_check=health_check, cap_at=cap_at, key=b"cb8-no-raw-wallets")
    fr.rules_sha256, fr.key_fp, fr.label = rules_sha, key_fp, label
    prior_fp = fr.prior.get("wallet_key_fingerprint")
    if prior_fp and prior_fp != key_fp:
        raise Refused(f"{run_id} manifest fingerprint {prior_fp} differs from the pinned {key_fp}; refusing")
    return fr


def disk_budget_end(fr: Cb8Run, exc_or_reason, extra: dict | None = None) -> dict:
    m = fr.manifest(f"disk_budget: {exc_or_reason}"[:200], {**(extra or {}), "status": DISK_BUDGET_TOKEN})
    m["status"] = DISK_BUDGET_TOKEN
    return m


def prior_terminal(rdir: Path) -> dict | None:
    """A declared end state is sticky: disk_budget is never retried."""
    mp = Path(rdir) / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("status") == DISK_BUDGET_TOKEN:
        return {"stopped": prior.get("stopped"), "status": DISK_BUDGET_TOKEN, "complete": False, "counts": prior.get("counts")}
    return None


def verify_manifest_files(rdir: Path, manifest: dict) -> int:
    """Re-hash every file named in the manifest; any missing or changed file, and any file not in the table, is a refusal."""
    want = manifest.get("file_sha256")
    if not isinstance(want, dict) or not want:
        raise Refused(f"{rdir.name} manifest has no file_sha256; refusing")
    for rel, sha in sorted(want.items()):
        fp = Path(rdir) / rel
        if not fp.is_file():
            raise Refused(f"file missing at verification: {rel}")
        if h5_seal.sha256_file(fp) != sha:
            raise Refused(f"file sha256 differs from the manifest: {rel}")
    skip = {"manifest.json", "request_clock.json", "progress.jsonl", "heartbeat.json"}
    extra = sorted(f for f in set(h5_seal.list_files(Path(rdir))) - set(want) - skip if not f.startswith("drops"))
    if extra:
        raise Refused(f"files not in the manifest: {extra[:5]}")
    return len(want)
