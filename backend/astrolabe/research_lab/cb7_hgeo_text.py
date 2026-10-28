# ruff: noqa: E501
"""CB7 h_geo text source (ruling reviews/CB7_HGEO_RULING_2026-10-28.md actions 2-3; CREATIVE_BATCH_7.md Reading 13a, DRAFT).

Capture rows carry no market text, so the section 2.1 geopolitics rule (``fee_category == "geopolitics"`` or ``topic_of(question, first event title,
slug, fee_category) == "geopolitics"``) cannot be applied to them alone. This module (a) pins and verifies the in-window captures, (b) lists the
candidate market ids (first row per market per capture: two-sided quote, YES mid in the h_geo band, ``fee_category`` not in ``FEE_FIRST``), (c) fetches
question, slug and first event title per id from public Gamma by id (net lane, allow-list parse: no outcome, price or volume field is ever kept),
and (d) writes ``text.csv.gz`` plus ``manifest.json`` with sha256 under ``<data-dumps>/research_lab/creative_batch7/h_geo_text``.

Exploratory, counts and text only. No spread is computed here. Not bound to T_seal (the captures it reads are after T_seal).
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from . import cb6_tail as c6
from . import cb7_common as cm
from . import history_backfill as hb
from .history_topics import FEE_FIRST

Refused, NotNow = cm.Refused, cm.NotNow

VERSION = "cb7-hgeo-text-v1"
TEXT_DIR_NAME = "h_geo_text"
TEXT_FILE = "text.csv.gz"
PIN_NAME = "cb7_hgeo_window_captures.sha256"
CAPTURE_FILES = ("rows.csv.gz", "rows_ext.csv.gz", "ext_manifest.json", "manifest.json")
TEXT_COLUMNS = ["market_id", "status", "question", "event_title", "slug", "source", "fetch_utc", "reason"]
PROGRESS_FILE = "progress.csv"
GAMMA_IDS_PER_REQUEST = 50
STATUS_OK, STATUS_UNAVAILABLE = "ok", "unavailable"
_CAPTURE_RE = re.compile(r"^(\d{8}T\d{6}Z)_[0-9a-f]+$")


def _sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _f(v) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else math.nan
    except (TypeError, ValueError):
        return math.nan


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- pins and captures -----------------------------------------------------------------------------------------------------------


def read_pins(pin_file: Path) -> dict[str, str]:
    """``{<capture>/<file>: sha256}`` from the pin file (``#`` comments and blanks skipped)."""
    pins: dict[str, str] = {}
    try:
        lines = Path(pin_file).read_text().splitlines()
    except OSError as exc:
        raise Refused(f"h_geo capture pin file {pin_file} unreadable: {exc}") from None
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = ln.split(None, 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
            raise Refused(f"h_geo capture pin file {pin_file}: malformed line {ln[:80]!r}")
        pins[parts[1].strip()] = parts[0]
    if not pins:
        raise Refused(f"h_geo capture pin file {pin_file} holds no pin")
    return pins


def window_dirs(snap_root: Path, window: tuple[str, str]) -> list[Path]:
    """Capture directories whose start lies in ``[window[0], window[1])`` (complete or not), sorted by name."""
    lo, hi = cm._ep(window[0]), cm._ep(window[1])
    out = []
    for d in sorted(Path(snap_root).iterdir() if Path(snap_root).exists() else []):
        m = _CAPTURE_RE.match(d.name)
        if not m or not d.is_dir():
            continue
        start = datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()
        if lo <= start < hi:
            out.append(d)
    return out


def verify_capture_pins(snap_root: Path, window: tuple[str, str], pin_file: Path) -> dict:
    """Every pinned file must exist and hash to its pin, and the in-window capture directories must be exactly the pinned ones. Any difference
    refuses (a capture added, removed or changed after the pin is a different data set)."""
    pins = read_pins(pin_file)
    dirs = window_dirs(snap_root, window)
    pinned_caps = {k.split("/", 1)[0] for k in pins}
    on_disk = {d.name for d in dirs}
    if pinned_caps != on_disk:
        raise Refused(f"h_geo capture pins: pinned captures differ from the in-window directories (only pinned {sorted(pinned_caps - on_disk)[:3]}, "
                      f"only on disk {sorted(on_disk - pinned_caps)[:3]}); refusing")
    for key, want in sorted(pins.items()):
        p = Path(snap_root) / key
        if not p.is_file():
            raise Refused(f"h_geo capture pins: {key} is missing; refusing")
        got = _sha_file(p)
        if got != want:
            raise Refused(f"h_geo capture pins: {key} sha256 {got[:12]} differs from the pin {want[:12]}; refusing")
    return {"pin_file_sha256": _sha_file(Path(pin_file)), "captures": len(pinned_caps), "files": len(pins)}


def complete_captures(snap_root: Path, window: tuple[str, str]) -> tuple[list[Path], int]:
    """(complete captures with a complete sidecar in the window, number skipped for sidecar). The sidecar status is read from
    ``ext_manifest.json`` (the host never writes it into ``manifest.json``)."""
    out, skipped = [], 0
    for d in window_dirs(snap_root, window):
        try:
            man = json.loads((d / "manifest.json").read_text())
        except (OSError, ValueError):
            continue
        if str(man.get("state")) != "complete":
            continue
        try:
            ext = json.loads((d / "ext_manifest.json").read_text())
        except (OSError, ValueError):
            ext = {}
        if str(ext.get("sidecar_status")) != "complete":
            skipped += 1
            continue
        out.append(d)
    return out, skipped


def _read_cols(path: Path, wanted: tuple[str, ...]):
    csv.field_size_limit(10**9)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd, [])
        idx = {c: head.index(c) for c in wanted if c in head}
        for row in rd:
            yield {c: row[i] for c, i in idx.items()}


def capture_observations(d: Path, mid_band: tuple[float, float]) -> list[tuple[str, float, str]]:
    """``(market_id, half_spread, fee_category)`` per market of one capture: FIRST row per market only, two-sided quote (``0 < bid < ask < 1``), YES mid
    in ``mid_band``. Reads only market_id, best_bid, best_ask (rows.csv.gz) and market_id, fee_category (rows_ext.csv.gz). ``fee_category`` is ``""``
    when the sidecar has no row for the market. Rows of ``FEE_FIRST`` categories are returned (the caller counts and drops them)."""
    fee: dict[str, str] = {}
    for r in _read_cols(d / "rows_ext.csv.gz", ("market_id", "fee_category")):
        fee.setdefault(r["market_id"], r.get("fee_category") or "")
    seen: set[str] = set()
    out: list[tuple[str, float, str]] = []
    for r in _read_cols(d / "rows.csv.gz", ("market_id", "best_bid", "best_ask")):
        mid_id = r["market_id"]
        if mid_id in seen:
            continue
        seen.add(mid_id)
        bid, ask = _f(r.get("best_bid")), _f(r.get("best_ask"))
        if not (math.isfinite(bid) and math.isfinite(ask)) or not (0.0 < bid < ask < 1.0):
            continue
        if not (mid_band[0] <= (bid + ask) / 2 <= mid_band[1]):
            continue
        out.append((mid_id, (ask - bid) / 2, fee.get(mid_id, "")))
    return out


def candidate_ids(snap_root: Path, window: tuple[str, str], mid_band: tuple[float, float]) -> tuple[list[str], dict]:
    """Sorted ids in the band with a two-sided quote in at least one complete capture and a fee category not in ``FEE_FIRST`` (exact drop)."""
    caps, skipped = complete_captures(snap_root, window)
    ids: set[str] = set()
    fee_first_ids: set[str] = set()
    n_obs = 0
    for d in caps:
        for mid_id, _h, fc in capture_observations(d, mid_band):
            n_obs += 1
            (fee_first_ids if fc in FEE_FIRST else ids).add(mid_id)
    fee_first_ids -= ids  # an id seen under both (cannot happen for one market) is kept as a candidate
    return sorted(ids), {"complete_captures": len(caps), "captures_skipped_sidecar_not_complete": skipped, "in_band_observations": n_obs,
                         "candidate_ids": len(ids), "dropped_fee_first_ids": len(fee_first_ids)}


# ---- Gamma parse (allow-list) ---------------------------------------------------------------------------------------------------


def parse_text(m: dict) -> dict:
    """Allow-list parse of one Gamma market: id, question, slug and the FIRST event's title. Nothing else is kept, so no outcome, price, volume or
    resolution field can reach disk."""
    ev = m.get("events") if isinstance(m.get("events"), list) else []
    et = ev[0].get("title") if ev and isinstance(ev[0], dict) else ""
    return {"market_id": str(m.get("id")), "question": str(m.get("question") or ""), "event_title": str(et or ""), "slug": str(m.get("slug") or "")}


def _fetch_batch(lim: hb.Limiter, ids: list[str], now: Callable[[], float]) -> tuple[dict[str, dict], dict[str, str]]:
    """(text per found id, reason per id that got a definitive non-200 answer). Open markets first, then ``closed=true`` for the rest. A network
    failure after retries raises :class:`NotNow` (transient)."""
    found: dict[str, dict] = {}
    reasons: dict[str, str] = {}
    for closed in (False, True):
        todo = [x for x in ids if x not in found and x not in reasons]
        if not todo:
            break
        params: dict = {"id": todo, "limit": GAMMA_IDS_PER_REQUEST}
        if closed:
            params["closed"] = "true"
        try:
            status, rows = lim.get(hb.GAMMA_MARKETS, params)
        except RuntimeError:
            raise NotNow("h_geo text: Gamma lookup failed after retries (network); resumable, retry later") from None
        if status != 200 or not isinstance(rows, list):
            if status in (400, 404, 422):  # definitive for this request: those ids are unavailable (counted), not a transient fault
                for x in todo:
                    reasons[x] = f"http_{status}"
                continue
            raise NotNow(f"h_geo text: Gamma lookup status {status}; resumable, retry later")
        fetch_utc = _iso(now())
        for m in rows:
            if isinstance(m, dict) and str(m.get("id")) in todo:
                found[str(m["id"])] = {**parse_text(m), "fetch_utc": fetch_utc}
    return found, reasons


# ---- the job -----------------------------------------------------------------------------------------------------------------------


def _load_progress(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    csv.field_size_limit(10**9)
    with path.open(newline="", encoding="utf-8") as fh:
        return {r["market_id"]: r for r in csv.DictReader(fh) if r.get("market_id")}


def _manifest(rdir: Path, budget: hb.DiskBudget, body: dict) -> dict:
    budget.cap += 10**7  # bookkeeping must stay writable at the cap
    budget.write(rdir / "manifest.json", json.dumps(body, indent=1, sort_keys=True, default=str).encode())
    return body


def hgeo_text_fetch(out_root: Path, transport, *, snap_root: Path, pin_file: Path, window: tuple[str, str], mid_band: tuple[float, float],
                    rps: float = 2.0, disk_cap: int = int(0.05 * 1024**3), budget_min: float | None = None, data_dumps: Path | None = None,
                    data_dumps_cap_gb: float = 50.0, live_check=None, sleep=time.sleep, wall_clock: Callable[[], float] = time.time,
                    should_stop: Callable[[], bool] | None = None) -> dict:
    """One resumable chunk. Refuses unless the captures match their pins; tempfails (exit 75) until the window has closed, on a data-dumps headroom
    refusal and on any transient Gamma failure; completes with ``text.csv.gz`` + ``manifest.json`` (``complete: true``, sha256 of the table).
    An id Gamma does not return, or answers 4xx for, is recorded ``unavailable`` with its reason and counted."""
    out_root = Path(out_root)
    cm.refuse_path(out_root)
    snap_root = Path(snap_root)
    if snap_root.name != "snapshots":
        raise Refused(f"h_geo text reads only a snapshots/ directory, not {snap_root}")
    if wall_clock() < cm._ep(window[1]):
        raise NotNow(f"h_geo window {window[0]}..{window[1]} is not closed yet")
    pinned = verify_capture_pins(snap_root, window, pin_file)
    if data_dumps is not None:
        c6.require_data_dumps_room(Path(data_dumps), data_dumps_cap_gb, disk_cap / 1024**3)
    ids, cand = candidate_ids(snap_root, window, mid_band)
    rdir = out_root / TEXT_DIR_NAME
    rdir.mkdir(parents=True, exist_ok=True)
    budget = hb.DiskBudget(rdir, disk_cap)
    lim = hb.Limiter(transport, rps=min(rps, 2.0), sleep=sleep, live_check=live_check)
    prog_path, final = rdir / PROGRESS_FILE, rdir / TEXT_FILE
    t0 = time.time()
    base = {"version": VERSION, "kind": "hgeo_text", "evidence_role": hb.EVIDENCE_ROLE, "git_commit": hb._git_commit(), "window": list(window),
            "mid_band": list(mid_band), "capture_pins": pinned, "candidates": cand, "gamma_ids_per_request": GAMMA_IDS_PER_REQUEST,
            "fields_kept": ["market_id", "question", "event_title(first event)", "slug"], "max_rps": min(rps, 2.0)}

    def manifest(stopped: str | None, extra: dict) -> dict:
        return _manifest(rdir, budget, {**base, "stopped": stopped, "requests_this_session": lim.requests, "retries": lim.retries,
                                         "updated_utc": _iso(wall_clock()), "complete": False, **extra})

    if final.exists():  # finished earlier: re-verify against the manifest, never refetch
        man = json.loads((rdir / "manifest.json").read_text()) if (rdir / "manifest.json").exists() else {}
        if man.get("complete") is True and man.get("text_sha256") == _sha_file(final) and man.get("capture_pins", {}).get("pin_file_sha256") == pinned["pin_file_sha256"]:
            return man
        raise Refused(f"{final} exists but does not match its manifest / pins; refusing to overwrite")
    done = _load_progress(prog_path)
    todo = [x for x in ids if x not in done]
    try:
        for i in range(0, len(todo), GAMMA_IDS_PER_REQUEST):
            if should_stop is not None and should_stop():
                return manifest("should_stop", {"transient": True, "status": "in_progress", "done_ids": len(done), "candidate_ids": len(ids)})
            if budget_min and time.time() - t0 >= budget_min * 60:
                return manifest("budget reached", {"transient": False, "status": "in_progress", "done_ids": len(done), "candidate_ids": len(ids)})
            batch = todo[i:i + GAMMA_IDS_PER_REQUEST]
            found, reasons = _fetch_batch(lim, batch, wall_clock)
            fetch_utc = _iso(wall_clock())
            lines = []
            for x in batch:
                if x in found:
                    r = {**found[x], "status": STATUS_OK, "source": "gamma_by_id", "reason": ""}
                else:
                    r = {"market_id": x, "status": STATUS_UNAVAILABLE, "question": "", "event_title": "", "slug": "", "source": "gamma_by_id",
                         "fetch_utc": fetch_utc, "reason": reasons.get(x, "not_returned")}
                done[x] = r
                lines.append(r)
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=TEXT_COLUMNS, lineterminator="\n")
            if not prog_path.exists():
                w.writeheader()
            w.writerows(lines)
            budget.write_append(prog_path, buf.getvalue())
    except NotNow as exc:
        return manifest(str(exc)[:200], {"transient": True, "status": "in_progress", "done_ids": len(done), "candidate_ids": len(ids)})
    except OSError as exc:
        return manifest(f"disk_budget: {exc}"[:200], {"status": cm.DISK_BUDGET_TOKEN, "done_ids": len(done), "candidate_ids": len(ids)})
    rows = [[done[x].get(c, "") for c in TEXT_COLUMNS] for x in ids]
    try:
        budget.write_gz_csv(final, TEXT_COLUMNS, rows)
    except OSError as exc:
        return manifest(f"disk_budget: {exc}"[:200], {"status": cm.DISK_BUDGET_TOKEN, "done_ids": len(done), "candidate_ids": len(ids)})
    n_ok = sum(1 for x in ids if done[x]["status"] == STATUS_OK)
    reasons_ct: dict[str, int] = {}
    for x in ids:
        if done[x]["status"] != STATUS_OK:
            reasons_ct[done[x]["reason"]] = reasons_ct.get(done[x]["reason"], 0) + 1
    return manifest(None, {"complete": True, "status": "hgeo_text_complete", "text_sha256": _sha_file(final), "text_file": TEXT_FILE,
                           "counts": {"candidate_ids": len(ids), "text_available": n_ok, "text_unavailable": len(ids) - n_ok, "unavailable_reasons": reasons_ct}})


def exit_code(m: dict) -> int:
    """0 complete or declared end state; 4 (disk budget) is handled by the runner; 75 on a transient stop; 1 on any other incomplete stop."""
    if m.get("complete") is True or m.get("stopped") is None:
        return 0
    if str(m.get("stopped")) == "budget reached":
        return 75
    return 75 if m.get("transient") else 1


# ---- reader (census) ---------------------------------------------------------------------------------------------------------------


def load_text_table(text_dir: Path, pin_file: Path) -> tuple[dict[str, dict], dict]:
    """Verify and read the text table: complete manifest, table sha256 equal to the manifest's, manifest bound to the CURRENT capture pin file. Any
    mismatch refuses. Returns ``({market_id: row}, manifest)``."""
    text_dir = Path(text_dir)
    mp, tp = text_dir / "manifest.json", text_dir / TEXT_FILE
    if not mp.exists() or not tp.exists():
        raise Refused(f"h_geo text table missing under {text_dir} (run the hgeo-text job first); refusing")
    try:
        man = json.loads(mp.read_text())
    except ValueError:
        raise Refused(f"{mp} is not valid JSON; refusing") from None
    if man.get("complete") is not True or man.get("version") != VERSION:
        raise Refused("h_geo text table manifest is not a complete current-version manifest; refusing")
    if _sha_file(tp) != man.get("text_sha256"):
        raise Refused("h_geo text table sha256 does not match its manifest pin; refusing")
    if (man.get("capture_pins") or {}).get("pin_file_sha256") != _sha_file(Path(pin_file)):
        raise Refused("h_geo text table was built against a different capture pin file; refusing")
    table = {r["market_id"]: r for r in cm.read_csv_gz(tp)}
    return table, man
