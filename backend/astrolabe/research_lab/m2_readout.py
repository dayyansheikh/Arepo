# ruff: noqa: E501
"""M2-J3 read-out resolution fetch (``MEASUREMENT_M2_CH264.md`` 9.4, 8.1, 8.3, 8.4). Refuses before ``READOUT_UTC``. Research tooling.

Gamma ``/markets?id=`` in batches of 50 with ``closed=true`` (the engine's call); ids not returned are fetched again without ``closed`` to separate
``pending`` (a record exists) from absence; an id absent in both passes is re-queried ALONE (``/markets?id=<id>``) both with and without
``closed=true``, and only two HTTP 200 answers without the record make it ``not_found`` (a failed single query leaves it ``unavailable_fetch``). Up to 3
attempts per request set, at least 1 h apart; remaining failures are ``unavailable_fetch``. Each record is parsed by ``calibration.parse_outcome`` (pinned).
A record that is not closed is ``pending`` whatever its outcome vector says (8.1, every final state; ``y`` is null when downgraded). The fetch covers every
unit's market and every ``no_favourite`` market (their coverage is printed separately). Write-once ``readout/readout.jsonl.gz`` and
``readout/readout_manifest.json``.
"""

from __future__ import annotations

import gzip
import io
import json
import time
from collections import Counter
from pathlib import Path

from . import boundary_map_ch240 as c240
from . import calibration
from . import m2_j2 as j2
from . import m2_spec as sp

CLASS_OF_REASON = {"split_50_50": "split_50_50", "not_resolved": "pending", "bad_prices": "unavailable_bad_prices", "other_price_vector": "unavailable_other_price_vector"}


def classify_record(m: dict) -> dict:
    y, why = calibration.parse_outcome(m)
    state = "resolved" if y is not None else CLASS_OF_REASON.get(why, f"unavailable_{why}")
    closed = c240._truthy(m.get("closed"))
    sub = None
    if state in ("resolved", "split_50_50") and not closed:
        state, why, y, sub = "pending", "not_closed", None, "not_closed"  # 8.1: not closed is pending for every final state; y is null when downgraded
    elif state == "pending":
        sub = "closed_not_uma_resolved" if closed else "not_closed"
    return {"state": state, "y": y, "parse_reason": why, "sub_class": sub, "closed": m.get("closed"), "closed_time": m.get("closedTime") or None,
            "end_date": m.get("endDate") or None, "uma": m.get("umaResolutionStatus")}


def _ids_in(store: Path, sub: str) -> set:
    ids: set = set()
    for p in sorted((Path(store) / sub).glob("*.jsonl.gz")):
        with gzip.open(p, "rt") as fh:
            for line in fh:
                if line.strip():
                    ids.add(int(json.loads(line)["market_id"]))
    return ids


def unit_market_ids(store: Path) -> list[int]:
    return sorted(_ids_in(store, "units"))


def no_favourite_market_ids(store: Path) -> list[int]:
    return sorted(_ids_in(store, "nofav"))


def fetch_rounds(reqs: dict, get, spec: dict, sleep, clock) -> tuple[dict, set, int]:
    """({key: (data, ts)} for answered requests (HTTP 200, a list), {failed keys}, requests). Rounds are at least ``attempt_gap_s`` apart."""
    f = spec["fetch"]
    todo = list(reqs)
    out: dict = {}
    n = 0
    last_try: dict = {}  # each request's own last attempt time (code-freeze check MUST 2)
    for rnd in range(f["attempts"]):
        if not todo:
            break
        if rnd:  # wait until EVERY request still to retry is at least attempt_gap_s past its own last attempt
            wait = max(last_try[k] for k in todo) + f["attempt_gap_s"] - clock()
            if wait > 0:
                sleep(wait)
        nxt = []
        for key in todo:
            n += 1
            last_try[key] = clock()
            data, _reason = get(reqs[key])
            if isinstance(data, list):
                out[key] = (data, clock())
            else:
                nxt.append(key)
        todo = nxt
    return out, set(todo), n


def _by_id(data: list) -> dict:
    return {int(m.get("id")): m for m in data if isinstance(m, dict) and str(m.get("id", "")).isdigit()}


def fetch_markets(ids: list[int], get, spec: dict, sleep, clock) -> tuple[dict, dict]:
    """{id: record dict (state, fetch_pass, fetched_utc, ...)} and the request counts. Implements the three passes of 9.4."""
    b = spec["fetch"]["batch"]
    recs: dict = {}
    req_n = Counter()

    def batches(xs, closed):
        return {i: ([("id", str(x)) for x in xs[i:i + b]] + [("limit", str(b))] + ([("closed", "true")] if closed else [])) for i in range(0, len(xs), b)}

    # pass 1: closed=true
    r1 = batches(ids, True)
    ans1, fail1, n1 = fetch_rounds(r1, get, spec, sleep, clock)
    req_n["closed_true"] = n1
    absent: list = []
    for i, (data, t) in ans1.items():
        got = _by_id(data)
        for x in ids[i:i + b]:
            if x in got:
                recs[x] = classify_record(got[x]) | {"fetch_pass": "closed_true", "fetched_utc": sp.iso(t)}
            else:
                absent.append(x)
    for i in fail1:
        for x in ids[i:i + b]:
            recs[x] = {"state": "unavailable_fetch", "y": None, "fetch_pass": "closed_true", "attempts": spec["fetch"]["attempts"], "fetched_utc": sp.iso(clock())}
    absent.sort()
    # pass 2: no closed filter
    still: list = []
    if absent:
        r2 = batches(absent, False)
        ans2, fail2, n2 = fetch_rounds(r2, get, spec, sleep, clock)
        req_n["no_closed_filter"] = n2
        for i, (data, t) in ans2.items():
            got = _by_id(data)
            for x in absent[i:i + b]:
                if x in got:
                    recs[x] = classify_record(got[x]) | {"fetch_pass": "no_closed_filter", "fetched_utc": sp.iso(t)}
                else:
                    still.append(x)
        for i in fail2:
            for x in absent[i:i + b]:
                recs[x] = {"state": "unavailable_fetch", "y": None, "fetch_pass": "no_closed_filter", "attempts": spec["fetch"]["attempts"], "fetched_utc": sp.iso(clock())}
    # pass 3: single-id re-query, with and without closed=true; only two HTTP 200 answers without the record make not_found
    if still:
        r3 = {}
        for x in still:
            r3[(x, "closed")] = [("id", str(x)), ("limit", "1"), ("closed", "true")]
            r3[(x, "open")] = [("id", str(x)), ("limit", "1")]
        ans3, fail3, n3 = fetch_rounds(r3, get, spec, sleep, clock)
        req_n["single_id"] = n3
        for x in sorted(still):
            hit = None
            for v in ("closed", "open"):
                if (x, v) in ans3:
                    m = _by_id(ans3[(x, v)][0]).get(x)
                    if m is not None:
                        hit = (m, ans3[(x, v)][1], v)
                        break
            if hit is not None:
                recs[x] = classify_record(hit[0]) | {"fetch_pass": f"single_id_{hit[2]}", "fetched_utc": sp.iso(hit[1])}
            elif (x, "closed") in ans3 and (x, "open") in ans3:
                recs[x] = {"state": "not_found", "y": None, "fetch_pass": "single_id_both_empty", "fetched_utc": sp.iso(max(ans3[(x, "closed")][1], ans3[(x, "open")][1]))}
            else:
                recs[x] = {"state": "unavailable_fetch", "y": None, "fetch_pass": "single_id_failed", "attempts": spec["fetch"]["attempts"], "fetched_utc": sp.iso(clock())}
        del fail3  # a failed single query is read through the answers it lacks
    return recs, dict(req_n)


def run_j3(store: Path, get, spec: dict = sp.SPEC, now: float | None = None, sleep=time.sleep, clock=time.time, paths: dict | None = None, design: Path | None = None,
           pins: dict | None = None) -> dict:
    sp.check_pins(spec, paths, design)
    sp.check_run_pins(pins, spec)
    now = clock() if now is None else now
    if now < sp.ts(spec, "readout_utc"):
        raise sp.M2Refusal("read-out fetch refuses before READOUT_UTC")
    store = Path(store)
    if not (store / "manifest.json").exists():
        raise sp.M2Refusal("read-out fetch refuses: no J2 unit manifest (the unit set is not closed)")
    out_p = store / "readout" / "readout.jsonl.gz"
    if out_p.exists():
        raise sp.M2Refusal("refuses to overwrite the read-out")
    u_ids, n_ids = unit_market_ids(store), no_favourite_market_ids(store)
    ids = sorted(set(u_ids) | set(n_ids))
    recs, req = fetch_markets(ids, get, spec, sleep, clock)
    rows = [{"market_id": x, "group": "unit" if x in set(u_ids) else "no_favourite"} | recs[x] for x in ids]
    body = "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(body.encode())
    gb = buf.getvalue()
    j2.write_once(out_p, gb)
    counts = Counter(r["state"] for r in rows if r["group"] == "unit")
    man = {"kind": "M2-J3 read-out", "markets": len(ids), "unit_markets": len(u_ids), "no_favourite_markets": len(n_ids), "counts_units": dict(sorted(counts.items())),
           "counts_no_favourite": dict(sorted(Counter(r["state"] for r in rows if r["group"] == "no_favourite").items())), "requests": req,
           "readout_sha256": sp.sha256_bytes(gb), "calibration_sha256": sp.sha256_file(Path(calibration.__file__)), "spec_sha": sp.spec_sha(spec), "code_sha": sp.code_sha(),
           "role": sp.ROLE, "fetch": spec["fetch"]}
    j2.write_once(store / "readout" / "readout_manifest.json", json.dumps(man, sort_keys=True, separators=(",", ":")).encode())
    return man


def default_get():
    """The engine's polite fetcher against Gamma ``/markets`` (network)."""
    f = calibration.PoliteFetcher(delay=0.3, max_requests=100000)
    return lambda params: f.get_json(calibration.GAMMA + "/markets", params)
