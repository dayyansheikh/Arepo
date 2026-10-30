# ruff: noqa: E501
"""M1-J3 read-out resolution fetch (``MEASUREMENT_M1_CH263.md`` 9.4, 8.1, 8.3). Refuses before ``READOUT_UTC``. Research tooling.

Gamma ``/markets?id=`` in batches of 50 with ``closed=true`` (the engine's call, ``labels.fetch_resolutions``); ids not returned are fetched
again without ``closed`` to separate ``pending`` (record present, not closed or not resolved) from ``not_found`` (no record). Up to 3 attempts
per batch at least 1 h apart; remaining failures are ``unavailable (fetch)``. Each record is parsed by ``calibration.parse_outcome``
(pinned). Write-once ``readout/readout.jsonl.gz`` plus ``readout/readout_manifest.json``.
"""

from __future__ import annotations

import gzip
import json
import time
from collections import Counter
from pathlib import Path

from . import calibration
from . import m1_extract as ex
from . import m1_spec as sp

CLASS_OF_REASON = {"split_50_50": "split_50_50", "not_resolved": "pending", "bad_prices": "unavailable_bad_prices", "other_price_vector": "unavailable_other_price_vector"}


def classify_record(m: dict) -> dict:
    y, why = calibration.parse_outcome(m)
    state = "resolved" if y is not None else CLASS_OF_REASON.get(why, f"unavailable_{why}")
    return {"state": state, "y": y, "parse_reason": why, "closed": m.get("closed"), "closed_time": m.get("closedTime") or None, "uma": m.get("umaResolutionStatus")}


def unit_market_ids(store: Path) -> list[int]:
    ids: set = set()
    for p in sorted((Path(store) / "units").glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            for line in fh:
                if line.strip():
                    ids.add(int(json.loads(line)["market_id"]))
    return sorted(ids)


def fetch_batches(ids: list[int], closed: bool, get, spec: dict, sleep, clock) -> tuple[dict, dict, int]:
    """({id: (market record or None, fetched ts)} for ids in answered batches, {id: attempts} for failed ids, requests). Rounds at least ``attempt_gap_s`` apart."""
    f = spec["fetch"]
    batches = [ids[i:i + f["batch"]] for i in range(0, len(ids), f["batch"])]
    todo = list(range(len(batches)))
    out: dict = {}
    requests = 0
    round_start = clock()
    for rnd in range(f["attempts"]):
        if not todo:
            break
        if rnd:
            sleep(max(0.0, round_start + f["attempt_gap_s"] - clock()))
        round_start = clock()
        nxt = []
        for bi in todo:
            params = [("id", str(x)) for x in batches[bi]] + [("limit", str(f["batch"]))] + ([("closed", "true")] if closed else [])
            requests += 1
            data, _reason = get(params)
            if not isinstance(data, list):
                nxt.append(bi)
                continue
            got = {int(m.get("id")): m for m in data if str(m.get("id", "")).isdigit()}
            t = clock()
            for x in batches[bi]:
                out[x] = (got.get(x), t)
        todo = nxt
    failed = {x: f["attempts"] for bi in todo for x in batches[bi]}
    return out, failed, requests


def run_j3(store: Path, get, spec: dict = sp.SPEC, now: float | None = None, sleep=time.sleep, clock=time.time, paths: dict | None = None, design: Path | None = None) -> dict:
    sp.check_pins(spec, paths, design)
    now = clock() if now is None else now
    if now < sp.ts(spec, "readout_utc"):
        raise ex.M1Refusal("read-out fetch refuses before READOUT_UTC")
    store = Path(store)
    if not (store / "manifest.json").exists():
        raise ex.M1Refusal("read-out fetch refuses: no J2 window manifest (the unit set is not closed)")
    out_p = store / "readout" / "readout.jsonl.gz"
    if out_p.exists():
        raise ex.M1Refusal("refuses to overwrite the read-out")
    ids = unit_market_ids(store)
    first, failed1, req1 = fetch_batches(ids, True, get, spec, sleep, clock)
    recs: dict = {}
    for x, (m, t) in first.items():
        if m is not None:
            recs[x] = classify_record(m) | {"fetch_pass": "closed_true", "fetched_utc": sp.iso(t)}
    second_ids = [x for x in ids if x in first and first[x][0] is None]
    second, failed2, req2 = fetch_batches(second_ids, False, get, spec, sleep, clock) if second_ids else ({}, {}, 0)
    for x in second_ids:
        if x in second:
            m, t = second[x]
            recs[x] = (classify_record(m) | {"fetch_pass": "no_closed_filter"}) if m is not None else {"state": "not_found", "y": None, "fetch_pass": "no_closed_filter"}
            recs[x]["fetched_utc"] = sp.iso(t)
    for x in list(failed1) + list(failed2):
        recs[x] = {"state": "unavailable_fetch", "y": None, "fetch_pass": "closed_true" if x in failed1 else "no_closed_filter", "attempts": spec["fetch"]["attempts"], "fetched_utc": sp.iso(clock())}
    rows = [{"market_id": x} | recs[x] for x in ids]
    body = "\n".join(ex.dumps(r) for r in rows) + "\n"
    gb = ex.gz_bytes(body)
    ex._write_once(out_p, gb, ex._same_gz)
    counts = Counter(r["state"] for r in rows)
    man = {"kind": "M1-J3 read-out", "markets": len(ids), "counts": dict(sorted(counts.items())), "requests": req1 + req2, "readout_sha256": ex.sha_bytes(gb),
           "calibration_sha256": sp.sha256_file(Path(calibration.__file__)), "spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(), "role": sp.ROLE, "fetch": spec["fetch"]}
    ex._write_once(store / "readout" / "readout_manifest.json", ex.dumps(man).encode(), ex._same_json)
    return man


def default_get():
    """The engine's polite fetcher against Gamma ``/markets`` (network)."""
    f = calibration.PoliteFetcher(delay=0.3, max_requests=100000)
    return lambda params: f.get_json(calibration.GAMMA + "/markets", params)
