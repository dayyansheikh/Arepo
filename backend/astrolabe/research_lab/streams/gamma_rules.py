# ruff: noqa: E501
"""Polymarket rule-text change log (CH08 rule-edit events, CH63 specificity, CH64 rule-divergence twins, CH48).

Gamma serves only the CURRENT description; the on-chain UMA initialisation text holds only the listing-time text,
so the time at which a clarification appeared is lost unless it is recorded when it happens. The 2-hourly
snapshot keeps ``updated_at``, but that field moves for almost every traded market (116,940 of 246,961 changed
between two consecutive captures on 2026-10-19), so it cannot date an edit.

Frame (no extra request): the latest COMPLETE snapshot capture (``snapshots/<capture>/rows.csv.gz``), open
markets with ``volume24hr > 0``, ordered by ``volume24hr`` (desc, then id), at most ``FRAME_CAP``. Each hourly
poll reads the top ``top`` of the frame; polls at ``FULL_HOURS`` read the whole frame. Requests:
``GET https://gamma-api.polymarket.com/markets?id=..&id=..`` (``BATCH`` ids each).

Keys (change-only; daily checkpoint as ``hash`` lines, so the full text is written only when new or edited):

* ``m:<market id>`` = the rule-bearing fields ``M_FIELDS`` + ``event_ids``;
* ``e:<event id>`` = ``E_FIELDS`` of each event embedded in a market (neg-risk rule text often lives here).

No price, outcome or wallet field is stored. A requested id that Gamma does not return is counted in the poll
meta (``missing``), never written as a row.
"""

from __future__ import annotations

import csv
import gzip
import json
import re
from pathlib import Path
from typing import Any

from .common import FetchError, Http, NotNow, PollResult, StreamSpec, utc_iso

GAMMA = "https://gamma-api.polymarket.com/markets"
BATCH = 50
FRAME_CAP = 25_000
DEFAULT_TOP = 3000
FULL_HOURS = (0, 6, 12, 18)
CAPTURE_RE = re.compile(r"^\d{8}T\d{6}Z_[0-9a-f]{8}$")
M_FIELDS = ("question", "description", "resolutionSource", "endDate", "startDate", "outcomes",
            "groupItemTitle", "customLiveness", "umaBond", "umaReward", "resolvedBy", "hasReviewedDates",
            "fallbackResolutionType", "negRiskOther")
E_FIELDS = ("title", "description", "resolutionSource", "endDate", "startDate")


def latest_complete_capture(snap_root: Path, look_back: int = 8) -> tuple[str, Path] | None:
    if not snap_root.exists():
        return None
    caps = sorted((p for p in snap_root.iterdir() if p.is_dir() and CAPTURE_RE.match(p.name)), reverse=True)
    for p in caps[:look_back]:
        try:
            man = json.loads((p / "manifest.json").read_text())
        except (OSError, ValueError):
            continue
        if man.get("state") == "complete" and (p / "rows.csv.gz").exists():
            return p.name, p
    return None


def _num(x: str | None) -> float:
    try:
        return float(x) if x not in (None, "") else 0.0
    except ValueError:
        return 0.0


def build_frame(rows_gz: Path, cap: int = FRAME_CAP) -> list[str]:
    keep: list[tuple[float, int, str]] = []
    with gzip.open(rows_gz, "rt", newline="") as fh:
        r = csv.reader(fh)
        hdr = next(r)
        ix = {k: hdr.index(k) for k in ("market_id", "volume24hr", "closed")}
        for row in r:
            if str(row[ix["closed"]]).lower() == "true":
                continue
            v = _num(row[ix["volume24hr"]])
            if v > 0:
                mid = row[ix["market_id"]]
                keep.append((-v, int(mid) if mid.isdigit() else 0, mid))
    keep.sort()
    out, seen = [], set()
    for _v, _i, mid in keep:
        if mid not in seen:
            seen.add(mid)
            out.append(mid)
        if len(out) >= cap:
            break
    return out


def _txt(v: Any) -> Any:
    return v if v is None or isinstance(v, (str, int, float, bool)) else json.dumps(v, sort_keys=True)


def market_items(markets: list[dict]) -> dict[str, Any]:
    items: dict[str, Any] = {}
    for m in markets:
        if not isinstance(m, dict) or m.get("id") is None:
            continue
        evs = [e for e in (m.get("events") or []) if isinstance(e, dict) and e.get("id") is not None]
        items[f"m:{m['id']}"] = {**{k: _txt(m.get(k)) for k in M_FIELDS},
                                 "event_ids": sorted(str(e["id"]) for e in evs)}
        for e in evs:
            items[f"e:{e['id']}"] = {k: _txt(e.get(k)) for k in E_FIELDS}
    return items


def get_frame(extra: dict, snap_root: Path) -> tuple[str, list[str], bool]:
    found = latest_complete_capture(snap_root)
    if found is None:
        if extra.get("frame_ids"):
            return extra["frame_capture"], extra["frame_ids"], False
        raise NotNow("gamma_rules: no complete snapshot capture to build the frame from (pending)")
    cid, p = found
    if extra.get("frame_capture") == cid and extra.get("frame_ids"):
        return cid, extra["frame_ids"], False
    return cid, build_frame(p / "rows.csv.gz"), True


def poll(http: Http, extra: dict, *, t0: float, data_dumps: Path, top: int = DEFAULT_TOP,
         full: bool | None = None, snapshots: Path | None = None, **_: Any) -> PollResult:
    cid, frame, rebuilt = get_frame(extra, snapshots or data_dumps / "research_lab" / "snapshots")
    hour = int(utc_iso(t0)[11:13])
    is_full = (hour in FULL_HOURS) if full is None else full
    ids = frame if is_full else frame[:top]
    got: list[dict] = []
    failed = 0
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        try:
            d = http.get_json(GAMMA, [*(("id", x) for x in chunk), ("limit", str(len(chunk)))], tag="markets")
        except FetchError:
            failed += 1
            if http.mono() > http.deadline:
                break
            continue
        if isinstance(d, list):
            got += d
    if ids and not got:
        raise FetchError(f"gamma_rules: no batch succeeded ({failed} failed)")
    items = market_items(got)
    returned = {k[2:] for k in items if k.startswith("m:")}
    meta = {"frame_capture": cid, "frame_size": len(frame), "frame_rebuilt": rebuilt, "full": is_full,
            "requested": len(ids), "returned": len(returned), "missing": len(set(ids) - returned),
            "failed_batches": failed, "n_events": sum(k.startswith("e:") for k in items)}
    return PollResult(items=items, scopes=(), meta=meta,
                      extra_state={"frame_capture": cid, "frame_ids": frame})


SPEC = StreamSpec(name="gamma_rules", dirname="stream_gamma_rules", slot_s=3600, checkpoint_s=86400,
                  allowance_bytes=60_000_000, stream_cap_gb=3.0, rps=2.0, budget_s=840, poll=poll,
                  hash_checkpoint=True)
