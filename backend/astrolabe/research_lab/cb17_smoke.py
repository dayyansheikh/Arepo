# ruff: noqa: E501
"""CB17 smoke (q0404; docs/research_lab/CREATIVE_BATCH_17.md section CB17-SM) and the q0405 exclusion keys.

Criteria (part ``common`` ``SMOKE_CRITERIA``): the rules parts and the CB13 / CB16 pins; refusals on fixtures (refused roots, the lookback floor including the q0406 / q0407 / q0410
lookback reads at S_8 - 2 / 3 / 6 h with the dependent unit labelled "unavailable (lookback floor)", REP_8 rows before the seal, census-path rows at or after 2026-10-16T00:00Z, forbidden
fields); the event-arm hash; the age parser edges; the shift state; the interval rule (gap 99 versus 100 min, dV = 0, member closed at k versus an unavailable mark at k + 1, capture
time = last page); the trailing-tercile rule (5 versus 6 prior, r_k never in its own cut points); the B no-mark label; the strata-level selection at the 60% edge; and the EXACT
reproduction of probes P1, P2 and P3 (section 0.3) from the worn files by faithful ports of the section 9 scripts (field-restricted readers; a different count is a FAIL, investigated,
never adjusted; a missing worn file is a refusal: restore it byte for byte first).
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb17_b as fb
from . import cb17_c as fc
from . import cb17_census as cen
from . import cb17_common as c17
from . import cb17_pre as pre
from . import cb17_rules_b as rb
from . import cb17_rules_c as rc
from . import cb17_wcommon as w
from . import cb17_win as win

Refused = c17.Refused
NotNow = c17.NotNow

SMOKE_VERSION = "cb17-smoke-v1"
P1_CAPTURES = ("20261012T003103Z_2df48d64", "20261015T223102Z_2eae9aa6")
P2_SPORTS_CAPTURE = "20261015T063101Z_9c518015"
P2_DAY = "20261015T"
P1_DAYS = ("12", "13", "14", "15")
# section 0.3, as printed by the probes (verbatim)
P1_EXPECTED = {"fills": 2931, "resolved": 2715, "ambiguous_tx": 216, "non_sports": 1006, "non_sports_resolved": 971, "open": 676, "close": 295,
               "class|UNSCHEDULED-NEWS|open": 259, "class|UNSCHEDULED-NEWS|close": 158, "class|SCHEDULED-EVENT|open": 297, "class|SCHEDULED-EVENT|close": 95,
               "class|PATH-SETTLED|open": 96, "class|PATH-SETTLED|close": 39, "class|PUBLIC-STATISTIC|open": 24, "class|PUBLIC-STATISTIC|close": 3, "sports_open": 1359, "sports_close": 385,
               "cells": 440, "cells_both": 44, "fills_in_both": 364, "markets_both": 34, "events_both": 26, "markets_both_any_d": 66, "fills_in_markets_both_any_d": 537,
               "age|<6h": 3, "age|6-24h": 27, "age|1-7d": 114, "age|>7d": 849, "age|unknown": 13, "markets_first_and_later": 7, "markets_any_first_day": 24}
P2_EXPECTED = {"sweeps": 24, "pairs": 12, "ns_tok": 205711, "sports_tok": 425003, "ns_pair": 205651, "hash_same": 65771, "hash_same_stamp_same": 65771, "hash_diff": 139880,
               "hash_diff_stamp_diff": 139880, "touch_same": 181701, "touch_same_hash_diff": 115930, "touch_same_shift_nonzero": 44896, "age|<60s": 131318, "age|60-600s": 35392,
               "age|600-3600s": 11930, "age|>3600s": 27071, "tokens_both": 1733, "tokens_seen": 24249, "ns_tok_pass": 187190, "next_pass_present": 174705}
P3_EXPECTED = {"captures": 12, "intervals": 11, "ns_traded": 16404, "oi_changed": 14271, "ns_not_traded": 32488, "ns_missing_oi_or_vol": 37516, "traded_single": 2280, "traded_multi_nr": 9470,
               "traded_multi_other": 4654, "traded_with_member_move": 9956, "events_ge6": 1226, "events_ge3": 2473, "events_any": 3537}


# =====================================================================================================================================================
# probe ports (section 9; the same counting, field-restricted readers, census cut-off)
# =====================================================================================================================================================


def _ep(s: str) -> float:
    try:
        return float(s)
    except ValueError:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _need(path: Path) -> Path:
    if not Path(path).exists():
        raise Refused(f"worn source {path} is missing: restore it byte for byte before the smoke (a missing file is never a FAIL)")
    return Path(path)


def probe_p1(fills_dir: Path, trades_dir: Path, snap_dir: Path) -> dict:
    """Probe P1 (section 9) on the worn files: fills -> token -> open / close; cells; market age bins."""
    fp = c17.guard_cb13_t_screen_file(_need(Path(fills_dir) / "fills.csv.gz"))
    fills = []
    for st, cid, mid, eid, label, tau, tl, d in cen.iter_cols(fp, ("status", "condition_id", "market_id", "event_id", "label", "tau", "tau_last", "d"), c17.FILLS_FIELDS):
        if st == "fill":
            fills.append((cid, mid, eid, label, int(c17.guard_census_time(_ep(tau), "fill tau")), int(_ep(tl)), int(float(d))))
    need = {x[0] for x in fills}
    pr: dict = defaultdict(set)
    hook = lambda kv: {k: v for k, v in kv if k in ("condition_id", "ts", "tx16", "outcome_index")}  # noqa: E731
    for day in P1_DAYS:
        p = c17.guard_monitor_file(_need(Path(trades_dir) / f"trades-202610{day}.jsonl"))
        with p.open() as f:
            for line in f:
                try:
                    d = json.loads(line, object_pairs_hook=hook)
                except Exception:  # noqa: BLE001 - the probe skipped any undecodable line
                    continue
                c = d.get("condition_id")
                if c in need and d.get("ts") is not None:
                    pr[(c, int(float(d["ts"])))].add((d.get("tx16"), d.get("outcome_index")))
    created: dict[str, float] = {}
    st_: Counter = Counter()
    for cap in P1_CAPTURES:
        cd = _need(Path(snap_dir) / cap)
        c17.guard_capture_dir(cd, c17.CAPTURE_LOOKBACK_START)
        for mid, cr, _t in cen.iter_dir_cols(cd, "rows_ext.csv.gz", ("market_id", "created_at"), c17.SIDECAR_FIELDS, "received_utc", st_):
            if cr:
                created.setdefault(mid, _ep(cr))
    res: Counter = Counter()
    lab_: dict[int, str] = {}
    for i, (c, _m, _e, _cl, t0, t1, d) in enumerate(fills):
        s: set = set()
        for t in range(t0, t1 + 1):
            s |= pr.get((c, t), set())
        txs = {a for a, _ in s}
        ois = {b for _, b in s}
        if not s:
            res["no_print"] += 1
            continue
        if len(txs) > 1:
            res["ambiguous_tx"] += 1
            continue
        if len(ois) != 1 or next(iter(ois)) not in (0, 1):
            res["mixed_or_unknown_token"] += 1
            continue
        oi = next(iter(ois))
        res["resolved"] += 1
        lab_[i] = "open" if (oi == 0 and d == -1) or (oi == 1 and d == 1) else "close"
    ns = [i for i, x in enumerate(fills) if x[3] != "SPORTS-FEED"]
    out: dict = {"fills": len(fills), "resolved": res["resolved"], "ambiguous_tx": res["ambiguous_tx"], "no_print": res["no_print"], "mixed_or_unknown_token": res["mixed_or_unknown_token"],
                 "non_sports": len(ns), "non_sports_resolved": sum(1 for i in ns if i in lab_)}
    lc = Counter(lab_[i] for i in ns if i in lab_)
    out.update(open=lc["open"], close=lc["close"])
    for (cl, lb), v in Counter((fills[i][3], lab_[i]) for i in ns if i in lab_).items():
        out[f"class|{cl}|{lb}"] = v
    sc = Counter(lab_[i] for i, x in enumerate(fills) if x[3] == "SPORTS-FEED" and i in lab_)
    out.update(sports_open=sc["open"], sports_close=sc["close"])
    cell: dict = defaultdict(Counter)
    for i in ns:
        if i in lab_:
            cell[(fills[i][1], fills[i][6])][lab_[i]] += 1
    both = {k for k, v in cell.items() if v["open"] and v["close"]}
    out.update(cells=len(cell), cells_both=len(both), fills_in_both=sum(sum(cell[k].values()) for k in both), markets_both=len({k[0] for k in both}),
               events_both=len({fills[i][2] for i in ns if i in lab_ and (fills[i][1], fills[i][6]) in both}))
    mk: dict = defaultdict(Counter)
    for i in ns:
        if i in lab_:
            mk[fills[i][1]][lab_[i]] += 1
    mb = [m for m, v in mk.items() if v["open"] and v["close"]]
    out.update(markets_both_any_d=len(mb), fills_in_markets_both_any_d=sum(sum(mk[m].values()) for m in mb))
    age: Counter = Counter()
    am: dict = defaultdict(set)
    for i in ns:
        _c, m, _e, _cl, t0, _t1, _d = fills[i]
        if m not in created:
            age["unknown"] += 1
            continue
        h = (t0 - created[m]) / 3600.0
        b = "neg" if h < 0 else "<6h" if h < 6 else "6-24h" if h < 24 else "1-7d" if h < 168 else ">7d"
        age[b] += 1
        am[m].add("first" if h < 24 else "later")
    for k, v in age.items():
        out[f"age|{k}"] = v
    out.update(markets_first_and_later=sum(1 for s in am.values() if s == {"first", "later"}), markets_any_first_day=sum(1 for s in am.values() if "first" in s),
               created_rows_at_or_after_cutoff_skipped=st_.get("rows_at_or_after_cutoff_skipped", 0))
    return out


def probe_p2(sweep_dir: Path, snap_dir: Path, sweeps: list[str] | None = None) -> dict:
    """Probe P2 (section 9) on the 24 worn sweeps of 2026-10-15."""
    st_: Counter = Counter()
    sports: set[str] = set()
    cd = _need(Path(snap_dir) / P2_SPORTS_CAPTURE)
    c17.guard_capture_dir(cd)
    for mid, ft, _t in cen.iter_dir_cols(cd, "rows_ext.csv.gz", ("market_id", "fee_type"), c17.SIDECAR_FIELDS, "received_utc", st_):
        if (ft or "").startswith("sports"):
            sports.add(mid)
    root = c17.refuse_path(Path(sweep_dir), allow=("book_sweeps",))
    sw = sorted(sweeps) if sweeps is not None else sorted(d for d in os.listdir(_need(root)) if d.startswith(P2_DAY))  # a pinned run uses exactly the pinned list
    if not sw:
        raise Refused(f"no worn {P2_DAY} sweeps under {root}: restore them byte for byte before the smoke")

    def load(s: str) -> dict:
        d = Path(root) / s
        c17.guard_sweep_dir(d)
        out = {}
        for r in cen.iter_cols(d / "rows.csv.gz", ("token_id", "market_id", "batch_receipt_utc", "book_timestamp", "book_hash", "best_bid", "best_ask", "depth_bid_1c", "depth_bid_5c",
                                                   "depth_ask_1c", "depth_ask_5c", "state"), c17.SWEEP_FIELDS):
            if r[2]:
                c17.guard_census_time(_ep_iso(r[2]), "sweep row")
            out[r[0]] = r[1:]
        return out

    def sid_t(s: str) -> float:
        return datetime.strptime(s[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).timestamp()

    t0 = [sid_t(s) for s in sw]
    pairs = [(i, i + 1) for i in range(len(sw) - 1) if t0[i + 1] - t0[i] < 1800]
    c: Counter = Counter()
    age: Counter = Counter()
    per_tok: dict = defaultdict(set)
    first = []
    for i, j in pairs:
        A, B = load(sw[i]), load(sw[j])
        first.append({tk for tk, a in A.items() if a[0] not in sports})
        for tk, a in A.items():
            if a[0] in sports:
                c["sports_tok"] += 1
                continue
            c["ns_tok"] += 1
            try:
                ag = _ep_iso(a[1]) - float(a[2]) / 1000.0
            except (ValueError, TypeError):
                age["unparseable"] += 1
                ag = None
            if ag is not None:
                b = "neg<-5s" if ag < -5 else "<60s" if ag < 60 else "60-600s" if ag < 600 else "600-3600s" if ag < 3600 else ">3600s"
                age[b] += 1
                if b == "<60s":
                    per_tok[tk].add("fresh")
                if b in ("600-3600s", ">3600s"):
                    per_tok[tk].add("old")
            b2 = B.get(tk)
            if b2 is None:
                c["ns_missing_in_2"] += 1
                continue
            if a[10] != "two_sided" or b2[10] != "two_sided":
                c["ns_not_two_sided"] += 1
                continue
            c["ns_pair"] += 1
            sh, stp, tu = a[3] == b2[3], a[2] == b2[2], a[4] == b2[4] and a[5] == b2[5]
            c["hash_same"] += sh
            c["hash_same_stamp_same"] += sh and stp
            c["hash_diff"] += not sh
            c["hash_diff_stamp_diff"] += (not sh) and (not stp)
            c["touch_same"] += tu
            c["touch_same_hash_diff"] += tu and not sh
            if tu:
                try:
                    sa = (float(b2[9]) - float(b2[8])) - (float(a[9]) - float(a[8]))
                    sb = (float(b2[7]) - float(b2[6])) - (float(a[7]) - float(a[6]))
                    c["touch_same_shift_nonzero"] += (sa - sb) != 0
                except (ValueError, TypeError):
                    c["touch_same_shift_unparseable"] += 1
    out = {"sweeps": len(sw), "pairs": len(pairs), **{k: int(v) for k, v in c.items()}, **{f"age|{k}": v for k, v in age.items()}}
    out["tokens_both"] = sum(1 for s in per_tok.values() if s == {"fresh", "old"})
    out["tokens_seen"] = len(per_tok)
    out["ns_tok_pass"] = sum(len(first[k]) for k in range(len(first) - 1))
    out["next_pass_present"] = sum(len(first[k] & first[k + 1]) for k in range(len(first) - 1))
    return out


def _ep_iso(s: str) -> float:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def probe_p3(snap_dir: Path, captures: list[str] | None = None) -> dict:
    """Probe P3 (section 9) on the 12 worn captures of 2026-10-15 (captures k - 1 and k only per interval)."""
    root = c17.refuse_path(Path(snap_dir), allow=("snapshots",))
    caps = sorted(captures) if captures is not None else sorted(d for d in os.listdir(_need(root)) if d.startswith(P2_DAY) and (Path(root) / d).is_dir())
    if not caps:
        raise Refused(f"no worn {P2_DAY} captures under {root}: restore them byte for byte before the smoke")
    st_: Counter = Counter()

    def num(x):
        try:
            return float(x) if x not in ("", "None") else None
        except ValueError:
            return None

    def load(cap: str):
        d = Path(root) / cap
        c17.guard_capture_dir(d)
        ev, mem, sp, nr = {}, defaultdict(list), set(), set()
        for e, oi, vol, mid, ft, nrm, _t in cen.iter_dir_cols(d, "rows_ext.csv.gz", ("event_id", "event_open_interest", "event_volume", "market_id", "fee_type", "neg_risk_market_id"),
                                                              c17.SIDECAR_FIELDS, "received_utc", st_):
            if not e:
                continue
            ev[e] = (num(oi), num(vol))
            mem[e].append(mid)
            if (ft or "").startswith("sports"):
                sp.add(e)
            if nrm:
                nr.add(e)
        mid_: dict = {}
        for m, bb, aa, _t in cen.iter_dir_cols(d, "rows.csv.gz", ("market_id", "best_bid", "best_ask"), c17.CAPTURE_FIELDS, "received_utc", st_):
            b, a = num(bb), num(aa)
            if b is not None and a is not None and 0 < b < a < 1 and a - b <= 0.10:
                mid_[m] = (a + b) / 2
        return ev, mem, sp, nr, mid_

    c: Counter = Counter()
    traded: Counter = Counter()
    prev = None
    for cap in caps:
        cur = load(cap)
        if prev is not None:
            ev0, _, _, _, mid0 = prev
            ev1, mem1, sp1, nr1, mid1 = cur
            for e, (oi1, v1) in ev1.items():
                if e in sp1 or e not in ev0:
                    continue
                oi0, v0 = ev0[e]
                if None in (oi0, oi1, v0, v1):
                    c["ns_missing_oi_or_vol"] += 1
                    continue
                if v1 - v0 <= 0:
                    c["ns_not_traded"] += 1
                    continue
                c["ns_traded"] += 1
                traded[e] += 1
                c["oi_changed"] += oi1 != oi0
                k = "single" if len(mem1[e]) == 1 else "multi_nr" if e in nr1 else "multi_other"
                c["traded_" + k] += 1
                c["traded_with_member_move"] += any(m in mid0 and m in mid1 and abs(mid1[m] - mid0[m]) >= 0.005 for m in mem1[e])
        prev = cur
    return {"captures": len(caps), "intervals": len(caps) - 1, **{k: int(v) for k, v in c.items()}, "events_ge6": sum(1 for v in traded.values() if v >= 6),
            "events_ge3": sum(1 for v in traded.values() if v >= 3), "events_any": len(traded), "rows_at_or_after_cutoff_skipped": st_.get("rows_at_or_after_cutoff_skipped", 0)}


def compare(observed: dict, expected: dict) -> dict:
    diffs = {k: {"expected": v, "observed": observed.get(k)} for k, v in expected.items() if observed.get(k) != v}
    return {"pass": not diffs, "differences": diffs, "observed": observed}


# =====================================================================================================================================================
# fixture checks
# =====================================================================================================================================================


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp(t: float) -> str:
    return f"{datetime.fromtimestamp(t, UTC):%Y%m%dT%H%M%SZ}_ab12cd34"


def _csv_gz(path: Path, cols: list[str], rows: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(cols)
        for r in rows:
            wr.writerow([r.get(c, "") for c in cols])


CAP_COLS = ["received_utc", "market_id", "condition_id", "event_id", "closed", "binary", "best_bid", "best_ask", "liquidity", "volume24hr", "end_date", "neg_risk_market_id", "chg_1h", "outcome_prices"]
EXT_COLS = ["received_utc", "market_id", "event_id", "fee_type", "fee_category", "clob_rewards", "series_slugs", "neg_risk_market_id", "event_open_interest", "event_volume", "created_at",
            "uma_resolution_statuses"]
SWEEP_COLS = list(c17.SWEEP_FIELDS) + ["batch_index"]


def fixture_capture(snap: Path, t0: float, quotes: list[dict]) -> Path:
    """A complete capture: quotes {mid, cid, eid, bid, ask, closed?, oi?, vol?}; rows stamped t0 + 1 .. t0 + 30 s (the last page = the capture's time). Forbidden fields carry values."""
    d = Path(snap) / _stamp(t0)
    rows, ext = [], []
    for i, q in enumerate(quotes):
        rec = _iso(t0 + 1 + 29 * i / max(len(quotes) - 1, 1))
        rows.append({"received_utc": rec, "market_id": q["mid"], "condition_id": q.get("cid", "c" + q["mid"]), "event_id": q["eid"], "closed": q.get("closed", "False"), "binary": "1",
                     "best_bid": q["bid"], "best_ask": q["ask"], "liquidity": "20000", "volume24hr": "5", "end_date": "2027-01-01T00:00:00Z", "neg_risk_market_id": "", "chg_1h": "0.9",
                     "outcome_prices": "SECRET"})
        ext.append({"received_utc": rec, "market_id": q["mid"], "event_id": q["eid"], "fee_type": "crypto_fees_v2", "fee_category": "crypto", "clob_rewards": "[]",
                    "series_slugs": '["s1"]', "neg_risk_market_id": "", "event_open_interest": q.get("oi", ""), "event_volume": q.get("vol", ""), "created_at": "2026-09-01T00:00:00Z",
                    "uma_resolution_statuses": "SECRET"})
    _csv_gz(d / "rows.csv.gz", CAP_COLS, rows)
    _csv_gz(d / "rows_ext.csv.gz", EXT_COLS, ext)
    (d / "manifest.json").write_text(json.dumps({"state": "complete"}))
    return d


def fixture_sweep(root: Path, t0: float, books: list[dict]) -> Path:
    d = Path(root) / _stamp(t0)
    rows = []
    for b in books:
        recv = b.get("recv", t0 + 5.0)
        rows.append({"sweep_id": d.name, "token_id": b["tok"], "market_id": b["mid"], "batch_receipt_utc": _iso(recv), "book_timestamp": b.get("ts", int((recv - 30) * 1000)),
                     "book_hash": b.get("hash", "h"), "best_bid": b["bid"], "best_ask": b["ask"], "bid_size_1": 100, "ask_size_1": 100, "depth_bid_1c": b.get("d1b", 500),
                     "depth_ask_1c": b.get("d1a", 500), "depth_bid_5c": b.get("d5b", 2000), "depth_ask_5c": b.get("d5a", 2000), "n_bid_levels": 5, "n_ask_levels": 5, "tick_size": "0.001",
                     "min_order_size": 5, "state": b.get("state", "two_sided"), "batch_index": 0})
    _csv_gz(d / "rows.csv.gz", SWEEP_COLS, rows)
    return d


def _raises(fn, exc=Refused) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:  # noqa: BLE001 - a different exception is a failed refusal check
        return False
    return False


def check_refusals(tmp: Path) -> dict:
    floor = c17.ep(c17.LOOKBACK_FLOOR)
    out = {}
    roots = [all(_raises(lambda r=r: win.refuse_window_path(tmp / "research_lab" / r / "x.csv", ())) for r in w.WINDOW_REFUSED_ROOTS),
             _raises(lambda: c17.refuse_path(tmp / "creative_batch13" / "t_holdout" / "f.csv.gz", allow=("creative_batch13",))),
             all(_raises(lambda n=n: c17.guard_monitor_file(tmp / "live_trades" / n)) for n in (*c17.MONITOR_FORBIDDEN_FILES, "scores-20261101.jsonl"))]
    out["refusals_roots"] = all(roots)
    s8 = floor
    W = w.windows8(s8)
    lb = [W["screen"]["sweeps"][0] == floor, W["screen"]["captures_bc"][0] == floor, W["screen"]["captures_e"][0] == floor, W["rep"]["read"][0] >= floor,
          _raises(lambda: win.list_window_dirs(tmp / "book_sweeps", "book_sweeps", c17.SWEEP_DIR_RE, s8 - 2 * 3600.0, s8, Counter())),
          _raises(lambda: win.list_window_dirs(tmp / "snapshots", "snapshots", c17.CAPTURE_DIR_RE, s8 - 6 * 3600.0, s8, Counter())),
          _raises(lambda: win.list_window_dirs(tmp / "snapshots", "snapshots", c17.CAPTURE_DIR_RE, s8 - 3 * 3600.0, s8, Counter())),
          not w.lookback_available(floor - 1.0) and w.lookback_available(floor)]
    # a B unit at S_8 (= the floor) whose previous pass would be at S_8 - 2 h: "unavailable (lookback floor)", counted
    sw, sn = tmp / "lb" / "book_sweeps", tmp / "lb" / "snapshots"
    fixture_capture(sn, floor + 60.0, [{"mid": "m1", "eid": "E1", "bid": "0.40", "ask": "0.42"}])
    fixture_sweep(sw, floor + 600.0, [{"tok": "t1", "mid": "m1", "bid": "0.40", "ask": "0.42"}])
    fixture_sweep(sw, floor + 720.0, [{"tok": "t1", "mid": "m1", "bid": "0.40", "ask": "0.42"}])
    a = w.arm(w.event_key("E1", "m1"))
    fr = fb.build_frame(sw, sn, None, units=(floor, floor + 86400.0), read_lo=floor, marks_hi=floor + 86400.0, arm=a)
    lb.append(any(k.startswith(w.UNAVAILABLE_LOOKBACK) for k in fr["exclusions"]))
    out["refusals_lookback_floor"] = all(lb)
    rep = [_raises(lambda: w.guard_rep_unit(W["rep"]["units"][0] + 10.0, s8, rep_open=False)), w.guard_rep_unit(W["rep"]["units"][0] + 10.0, s8, rep_open=True) > 0,
           _raises(lambda: win.require_results_copy(tmp / "creative_batch17", tmp / "seals", require_committed=False), NotNow)]
    out["refusals_rep_before_seal"] = all(rep)
    out["refusals_census_cutoff"] = _raises(lambda: c17.guard_census_time(c17.ep(c17.CENSUS_CUTOFF))) and not _raises(lambda: c17.guard_census_time(c17.ep(c17.CENSUS_CUTOFF) - 1))
    tr = tmp / "ff" / "live_trades"
    tr.mkdir(parents=True)
    day = datetime.fromtimestamp(floor + 100, UTC).strftime("%Y%m%d")
    (tr / f"trades-{day}.jsonl").write_text(json.dumps({"ts": floor + 100, "condition_id": "c1", "ctx_market_id": "m1", "side": "BUY", "wallet_hash": "W", "recv_ts": floor + 500,
                                                        "key": "K", "outcome_index": 0, "price": 0.4, "size": 10}) + "\n")
    (tr / f"trades-{datetime.fromtimestamp(floor + 100 + 86400.0, UTC):%Y%m%d}.jsonl").write_text("")  # readers also open the day after the window: a missing file is a pending restore
    got = list(win.iter_monitor(tr, floor, floor + 3600.0, Counter()))
    from . import cb17_e as fe  # noqa: PLC0415

    pr = list(fe.iter_prints(tr, floor, floor + 3600.0, Counter()))
    ff = [got == [(floor + 100, "c1", "m1")], bool(pr) and all(k not in pr[0] for k in ("side", "wallet_hash", "recv_ts", "key")),
          _raises(lambda: c17.assert_clean_result({"mark_x": 1})), _raises(lambda: win.write_arrays(tmp / "creative_batch17" / "x.npz", {"side": np.zeros(1)})),
          all(f not in c17.CAPTURE_FIELDS for f in c17.FORBIDDEN_CAPTURE_FIELDS)]
    out["forbidden_fields"] = all(ff)
    return out


def check_rules_fixtures(tmp: Path) -> dict:
    out = {}
    ids = [f"E{i}" for i in range(40)]
    arms = [w.arm(e) for e in ids]
    out["arm_hash"] = bool(arms == [w.arm(e) for e in ids] and set(arms) == {0, 1} and w.arm("12345") == int(__import__("hashlib").sha256(b"cb17-arm-v1|12345").hexdigest()[0], 16) % 2)
    rcv = 1_800_000_000.0
    ages = [rb.age_state(rb.book_age_s(rcv, (rcv - a) * 1000.0)) for a in (-5.01, -5.0, 59.99, 60.0, 599.99, 600.0)]
    out["age_parser"] = ages == [rb.STATE_ANOMALY, rb.STATE_FRESH, rb.STATE_FRESH, rb.STATE_MID, rb.STATE_MID, rb.STATE_OLD]
    s1 = {"bid_s": "0.40", "ask_s": "0.42", "db1": 100.0, "da1": 100.0, "db5": 500.0, "da5": 500.0}
    out["shift_state"] = bool(rb.shift_state(s1, {**s1, "ask_s": "0.43"}) is None and rb.shift_state(s1, dict(s1))["x"] == 0.0 and rb.shift_state(s1, {**s1, "da5": 400.0})["x"] > 0)
    # interval rule on fixture captures: gap edges, dV = 0, member closed at k excluded, member closed at k + 1 -> unavailable (mark), capture time = last page
    floor = c17.ep(c17.LOOKBACK_FLOOR)
    sn = tmp / "iv" / "snapshots"
    t = floor + 3600.0
    evs = [f"E{i}" for i in range(200) if w.arm(f"E{i}") == 0][:3]
    caps = []
    for k in range(9):
        qs = []
        for j, e in enumerate(evs):
            mid = 0.40 + 0.01 * (k % 3) + 0.002 * j
            qs.append({"mid": f"m{j}", "eid": e, "bid": f"{mid - 0.01:.3f}", "ask": f"{mid + 0.01:.3f}", "oi": str(1000 + 7 * k * (j + 1) + (k % 2)), "vol": str(5000 + 100 * k * (j + 1)) if not (j == 1 and k == 7) else str(5000 + 100 * 6 * 2),
                       "closed": "True" if (j == 2 and k == 8) else "False"})
        caps.append(fixture_capture(sn, t, qs))
        t += 100 * 60.0 if k < 8 else 140 * 60.0
    fr = fc.build_frame(sn, units=(floor, floor + 30 * 86400.0), read_lo=floor, marks_hi=floor + 30 * 86400.0, arm=0)
    U, M = fr["units"], fr["members"]
    unit_caps = {int(c) for c in U["cap"]}
    iv = [rc.interval_ok(100 * 60.0) and not rc.interval_ok(99 * 60.0) and rc.interval_ok(140 * 60.0) and not rc.interval_ok(141 * 60.0), rc.r_state(1, 2, 5, 5) is None,
          fr["exclusions"].get("not traded (dV <= 0)", 0) >= 1,
          all(abs(c["T"] - (fc.load_capture(caps[i])["T"])) < 1e-6 for i, c in enumerate(fr["captures"])),
          len(U["ev"]) > 0]
    # member closed at k + 1 (capture 8, event 2) -> its unit is kept and the member's k + 1 status is "member closed"
    ev2 = fr["vocab"]["ev"].index(evs[2]) if evs[2] in fr["vocab"]["ev"] else -1
    k1_closed = [int(M["st1"][i]) for i in range(len(M["unit"])) if int(U["ev"][M["unit"][i]]) == ev2 and int(U["cap"][M["unit"][i]]) == 7]
    iv.append(bool(k1_closed) and all(s == fc.REASON_CODE["member closed"] for s in k1_closed) and 7 in unit_caps)
    out["interval_rule"] = all(iv)
    prior5, prior6 = [0.1, 0.2, 0.3, 0.4, 0.5], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    out["trailing_tercile"] = bool(rc.classify(0.35, prior5) is None and rc.classify(0.35, prior6) == rc.CLASS_TRANSFER and rc.classify(9.0, prior6) == rc.CLASS_MINT
                                   and rc.classify(-1.0, prior6) == rc.CLASS_MERGE and all(int(U["cap"][u]) >= 6 for u in range(len(U["ev"]))))
    # B no-mark label: a token absent from the 2 h mark pass keeps its unit with status "no mark"
    sw, sb = tmp / "nm" / "book_sweeps", tmp / "nm" / "snapshots"
    t0 = floor + 3 * 3600.0
    fixture_capture(sb, floor + 60.0, [{"mid": "m1", "eid": evs[0], "bid": "0.40", "ask": "0.42"}, {"mid": "m2", "eid": evs[0], "bid": "0.50", "ask": "0.52"}])
    for p in range(4):
        books = [{"tok": "t1", "mid": "m1", "bid": "0.40", "ask": "0.42"}] + ([] if p == 3 else [{"tok": "t2", "mid": "m2", "bid": "0.50", "ask": "0.52"}])
        fixture_sweep(sw, t0 + p * 7200.0, books)
        fixture_sweep(sw, t0 + p * 7200.0 + 120.0, books)
    frb = fb.build_frame(sw, sb, None, units=(floor, floor + 86400.0), read_lo=floor, marks_hi=floor + 86400.0, arm=0)
    A = frb["arrays"]
    toks = frb["vocab"]["tok"]
    last_t2 = [int(A["st2_1"][u]) for u in range(len(A["tok"])) if toks[int(A["tok"][u])] == "t2" and A["t1"][u] > t0 + 7200.0 * 1.5]
    out["b_no_mark_label"] = bool(last_t2) and all(s == fb.ST_NO for s in last_t2) and any(int(A["st2_1"][u]) == fb.ST_OK for u in range(len(A["tok"])))
    out["strata_selection_60"] = bool(pre.select_level({0: 0.59, 1: 0.60, 2: 0.9})["selected_level"] == 1 and pre.select_level({0: 0.1, 1: 0.2, 2: 0.3})["selected_level"] == 2
                                      and pre.select_level({0: 0.1, 1: 0.2, 2: 0.3})["fallback"] is True and pre.select_level({0: 0.6, 1: 0.9, 2: 0.9})["selected_level"] == 0)
    return out


PINNED_COUNTS = {"captures": P3_EXPECTED["captures"], "sweeps": P2_EXPECTED["sweeps"]}  # the section 9 sets (the design lists no ids; the probes glob 20261015T*): a pinned run needs exactly these many
FILLS_KEY = "creative_batch13/t_screen/fills.csv.gz"
_KEY_RE = re.compile(r"^(?:creative_batch13/t_screen/fills\.csv\.gz|live_trades/trades-\d{8}\.jsonl|snapshots/[^/]+/rows(?:_ext)?\.csv\.gz|book_sweeps/[^/]+/rows\.csv\.gz)$")


def required_fixed_keys() -> list[str]:
    ks = [FILLS_KEY, *(f"live_trades/trades-202610{d}.jsonl" for d in P1_DAYS)]
    ks += [f"snapshots/{c}/rows_ext.csv.gz" for c in sorted({*P1_CAPTURES, P2_SPORTS_CAPTURE})]
    return ks


def _path_of(key: str, fills_dir: Path, trades_dir: Path, snap_dir: Path, sweep_dir: Path) -> Path:
    if not _KEY_RE.match(key):
        raise Refused(f"pinned key {key!r} is not an archive-relative worn-file path")
    if key == FILLS_KEY:
        return Path(fills_dir) / "fills.csv.gz"
    root, rest = key.split("/", 1)
    return {"live_trades": Path(trades_dir), "snapshots": Path(snap_dir), "book_sweeps": Path(sweep_dir)}[root] / rest


def worn_files(fills_dir: Path, trades_dir: Path, snap_dir: Path, sweep_dir: Path, pins: dict | None = None) -> list[tuple[str, Path]]:
    """Every worn input file the probes read, keyed by its ARCHIVE-RELATIVE path (``live_trades/trades-YYYYMMDD.jsonl``, ``snapshots/<capture>/rows[_ext].csv.gz``,
    ``book_sweeps/<sweep>/rows.csv.gz``, ``creative_batch13/t_screen/fills.csv.gz``), wherever the tree is rooted. A missing file is a refusal. WITHOUT ``pins`` (the ``worn-manifest`` helper) the
    P2 / P3 lists are found by glob; WITH ``pins`` the set is EXACTLY the pinned keys (nothing glob-dependent), each of which must exist on disk."""
    if pins is not None:
        missing_fixed = [k for k in required_fixed_keys() if k not in pins]
        caps = sorted({k.split("/")[1] for k in pins if k.startswith("snapshots/") and k.split("/")[1].startswith(P2_DAY)})
        sws = sorted({k.split("/")[1] for k in pins if k.startswith("book_sweeps/")})
        no_both = [c for c in caps if not all(f"snapshots/{c}/{nm}" in pins for nm in ("rows.csv.gz", "rows_ext.csv.gz"))]  # P3 reads both files of every 2026-10-15 capture
        bad_sets = []
        if len(caps) != PINNED_COUNTS["captures"] or P2_SPORTS_CAPTURE not in caps:
            bad_sets.append(f"P3 captures {len(caps)} != {PINNED_COUNTS['captures']} (incl. {P2_SPORTS_CAPTURE})")
        if len(sws) != PINNED_COUNTS["sweeps"]:
            bad_sets.append(f"P2 sweeps {len(sws)} != {PINNED_COUNTS['sweeps']}")
        if missing_fixed or no_both or bad_sets:
            raise Refused(f"required worn files are unpinned or the pinned sets are incomplete: fixed={missing_fixed[:5]} (n={len(missing_fixed)}), captures without both rows files={no_both[:3]} (n={len(no_both)}), {bad_sets}")
        out = [(k, _need(_path_of(k, fills_dir, trades_dir, snap_dir, sweep_dir))) for k in sorted(pins)]
        return out
    out = [(FILLS_KEY, _need(Path(fills_dir) / "fills.csv.gz"))]
    for day in P1_DAYS:
        out.append((f"live_trades/trades-202610{day}.jsonl", _need(Path(trades_dir) / f"trades-202610{day}.jsonl")))
    snap = Path(snap_dir)
    for cap in sorted({*P1_CAPTURES, P2_SPORTS_CAPTURE}):
        out.append((f"snapshots/{cap}/rows_ext.csv.gz", _need(snap / cap / "rows_ext.csv.gz")))
    caps = sorted(d for d in os.listdir(_need(snap)) if d.startswith(P2_DAY) and (snap / d).is_dir())
    for cap in caps:
        for nm in ("rows.csv.gz", "rows_ext.csv.gz"):
            out.append((f"snapshots/{cap}/{nm}", _need(snap / cap / nm)))
    sw = Path(sweep_dir)
    for d in sorted(x for x in os.listdir(_need(sw)) if x.startswith(P2_DAY)):
        out.append((f"book_sweeps/{d}/rows.csv.gz", _need(sw / d / "rows.csv.gz")))
    seen: dict[str, Path] = {}
    for k, p in out:
        seen.setdefault(k, p)
    return sorted(seen.items())


def worn_manifest(fills_dir: Path, trades_dir: Path, snap_dir: Path, sweep_dir: Path) -> dict[str, str]:
    """``{archive-relative path: sha256}`` of the worn input files ON DISK (a convenience helper only: the binding pins are copied from the archive releases' files.sha256)."""
    return {k: c17.sha256_file(p) for k, p in worn_files(fills_dir, trades_dir, snap_dir, sweep_dir)}


def release_map(files_sha256_paths: list[Path]) -> dict:
    """The worn-file sha256 map derived from archive releases' ``files.sha256`` files (lines ``<sha256>  <archive-relative path>``): only the files the smoke reads (P1 days and captures,
    the sports capture's ext, the 2026-10-15 P3 captures and P2 sweeps, the CB13-T SCREEN fills); a key listed twice with different hashes is a refusal. Returns ``{"worn_sha256", "missing_required"}``."""
    out: dict[str, str] = {}
    for fp in files_sha256_paths:
        p = Path(fp)
        if not p.is_file():
            raise Refused(f"files.sha256 {p} not found")
        for ln in p.read_text().splitlines():
            if "  " not in ln:
                continue
            h, rel = ln.rstrip("\n").split("  ", 1)
            rel = rel.strip().lstrip("./")
            m = re.search(r"(?:^|/)(creative_batch13/t_screen/fills\.csv\.gz|live_trades/trades-\d{8}\.jsonl|snapshots/[^/]+/rows(?:_ext)?\.csv\.gz|book_sweeps/[^/]+/rows\.csv\.gz)$", rel)
            if not m or not re.fullmatch(r"[0-9a-f]{64}", h):
                continue
            key = m.group(1)
            parts = key.split("/")
            if key.startswith("live_trades/") and key[len("live_trades/trades-"):][:8] not in {f"202610{d}" for d in P1_DAYS}:
                continue
            if key.startswith("snapshots/"):
                cap, nm = parts[1], parts[2]
                if cap in {*P1_CAPTURES, P2_SPORTS_CAPTURE} and nm != "rows_ext.csv.gz" and not cap.startswith(P2_DAY):
                    continue
                if cap not in {*P1_CAPTURES, P2_SPORTS_CAPTURE} and not cap.startswith(P2_DAY):
                    continue
            if key.startswith("book_sweeps/") and not parts[1].startswith(P2_DAY):
                continue
            if key in out and out[key] != h:
                raise Refused(f"{key}: two different sha256 in the given files.sha256 files")
            out[key] = h
    return {"worn_sha256": dict(sorted(out.items())), "missing_required": [k for k in required_fixed_keys() if k not in out]}


def load_pins(pin_path: Path) -> dict:
    pp = Path(pin_path)
    if not pp.is_file():
        raise Refused(f"--worn-sha256 file {pp} not found")
    try:
        pins = json.loads(pp.read_text())
    except ValueError as exc:
        raise Refused(f"--worn-sha256 file {pp.name} is not JSON") from exc
    if not isinstance(pins, dict) or not all(isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{64}", v) for v in pins.values()):
        raise Refused("--worn-sha256 file must be a JSON object {archive-relative path: sha256}")
    return pins


def check_worn_pins(pin_path: Path, fills_dir: Path, trades_dir: Path, snap_dir: Path, sweep_dir: Path) -> dict:
    """Refuse (exit 2) unless the worn files are EXACTLY the pinned set (every pinned key exists on disk, nothing is found by glob) and each hashes to its pin (a wrong restore would otherwise be a
    counted FAIL). Returns ``{"n_files", "pins_sha256", "captures", "sweeps"}``; the probes then read exactly those captures / sweeps."""
    pins = load_pins(pin_path)
    files = worn_files(fills_dir, trades_dir, snap_dir, sweep_dir, pins=pins)
    bad = sorted(k for k, p in files if c17.sha256_file(p) != pins[k].lower())
    if bad:
        raise Refused(f"worn files differ from the pins: sha256 mismatch={bad[:5]} (n={len(bad)}); restore byte for byte")
    return {"n_files": len(files), "pins_sha256": c17.sha256_file(Path(pin_path)), "captures": sorted({k.split("/")[1] for k, _ in files if k.startswith("snapshots/") and k.split("/")[1].startswith(P2_DAY)}),
            "sweeps": sorted({k.split("/")[1] for k, _ in files if k.startswith("book_sweeps/")})}


def collect_checks(ctx: dict) -> tuple[dict, dict]:
    """(criteria -> bool, detail). ``ctx``: rules (path), require_committed, fills_dir, trades_dir, snapshot_dir, sweep_dir (the worn sources)."""
    crit: dict[str, bool] = {}
    detail: dict = {}
    try:
        detail["rules_sha256"] = win.verify_parts(ctx.get("rules"), require_committed=ctx.get("require_committed", True))
        crit["parts_verify"] = True
    except Refused as exc:
        crit["parts_verify"] = False
        detail["parts_verify"] = str(exc)
    pins = w.pins_ok()
    crit["pins_cb13"] = not pins["diverged"]["cb13"]
    crit["pins_cb16"] = not pins["diverged"]["cb16"]
    detail["pins"] = pins
    with tempfile.TemporaryDirectory(prefix="cb17_smoke_") as td:
        tmp = Path(td)
        for name, fn in (("refusals", check_refusals), ("rules_fixtures", check_rules_fixtures)):
            try:
                crit.update(fn(tmp / name))
            except Exception as exc:  # noqa: BLE001 - a crashing fixture check is a FAIL of its criteria, recorded
                detail[f"{name}_error"] = f"{type(exc).__name__}: {exc}"[:300]
    for k in w.SMOKE_CRITERIA:
        if not k.startswith("reproduce_"):
            crit.setdefault(k, False)
    for key, fn, exp in (("reproduce_P1", lambda: probe_p1(ctx["fills_dir"], ctx["trades_dir"], ctx["snapshot_dir"]), P1_EXPECTED),
                         ("reproduce_P2", lambda: probe_p2(ctx["sweep_dir"], ctx["snapshot_dir"], ctx.get("pinned_sweeps")), P2_EXPECTED),
                         ("reproduce_P3", lambda: probe_p3(ctx["snapshot_dir"], ctx.get("pinned_captures")), P3_EXPECTED)):
        r = compare(fn(), exp)  # a missing worn source raises Refused (exit 2): never a FAIL
        crit[key] = r["pass"]
        detail[key] = {"differences": r["differences"], "observed": r["observed"]}
    return crit, detail


def per_family(crit: dict) -> dict:
    return {f: all(crit.get(k) is True for k in w.SMOKE_NEEDS[f]) for f in w.SMOKE_NEEDS}


# =====================================================================================================================================================
# q0405: exclusion keys (no network)
# =====================================================================================================================================================


ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?")


def _timestamps(obj) -> list[float]:
    out: list[float] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _timestamps(k) + _timestamps(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _timestamps(v)
    elif isinstance(obj, str):
        for m in ISO_RE.findall(obj):
            t = c17.ep(m)
            if math.isfinite(t):
                out.append(t)
    return out


def exclusion_keys(out_root: Path, *, s8: float, cb16_path: Path | None, cb16_sha256: str | None, cb16_stopped: bool, seals_dir: Path, is_committed) -> dict:
    """q0405 (section 1.3): the CB16 q0380 key file (sha256 pin MANDATORY unless q0380 has a stop record; its per-key sources kept) and every committed seal copy, as one source-attributed
    key universe (overlap counts). A market or event is DROPPED only if it appears in a sealed historical set with a stored timestamp inside SCREEN_8 or REP_8: a committed seal copy
    any of whose ISO timestamps lies in ``[S_8, S_8 + 28 d + 8 h)`` contributes its market ids as drop keys (source = the copy); the CB16 key rows carry no timestamps and are overlap
    only (none expected to drop)."""
    from . import cb4_data as c4  # noqa: PLC0415
    from . import cb8_books as bk  # noqa: PLC0415
    from . import cb16_common as c16  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    kd = c17.require_output_root(Path(out_root) / win.KEYS_DIR)
    rows: list[dict] = []
    src_note = None
    if cb16_stopped:
        src_note = "CB16 q0380 stopped (stop record): keys absent, recorded"
    else:
        if not cb16_sha256 or cb16_sha256 == win.PIN_UNSET:
            raise Refused(f"the sha256 pin of the CB16 q0380 key file (--cb16-keys-sha256) is unset ({win.PIN_UNSET}); the coordinator fills it from q0380's manifest")
        p = c17.refuse_path(Path(cb16_path), allow=("creative_batch16",))
        if not p.exists():
            raise NotNow(f"{p} missing (CB16 q0380 first, or its stop record); pending")
        got = c17.sha256_file(p)
        if got != cb16_sha256:
            raise Refused(f"CB16 key file sha256 {got} != pinned {cb16_sha256}")
        rows = c16.read_keys_with_sources(p)
    seal_ids, used, skipped, shas = bk.seal_copy_ids_audited(seals_dir, own=(), is_committed=is_committed)
    lo, hi = s8, s8 + 2 * w.WINDOW_S + w.MARK_TAIL_S
    drops: dict[str, str] = {}
    in_window: list[str] = []
    for name in used:
        pth = Path(seals_dir) / name
        try:
            ts = _timestamps(json.loads(pth.read_text()))
        except ValueError:
            continue
        if any(lo <= t < hi for t in ts):
            in_window.append(name)
            for m in c4._cb2w().seal_ids_from_copy(pth):
                drops.setdefault(f"market_id:{m}", f"seal:{name}")
    univ: dict[str, set[str]] = {}
    ev_of: dict[str, str] = {}
    for r in rows:
        univ.setdefault(str(r["market_id"]), set()).update({f"cb16:{s}" for s in r["sources"]} or {"cb16:base"})
        ev_of[str(r["market_id"])] = str(r.get("event_ids") or "")
    for i in seal_ids:
        univ.setdefault(str(i), set()).add("seal_copies")
    kd.mkdir(parents=True, exist_ok=True)
    keys_p = kd / win.KEYS_NAME
    drop_p = kd / win.DROP_KEYS_NAME
    for p in (keys_p, drop_p):
        if p.exists():
            raise Refused(f"{p} exists; the key files are written once")
    keys_p.write_bytes(hb._gz_csv_bytes(["market_id", "event_ids", "sources"], sorted([m, ev_of.get(m, ""), ";".join(sorted(s))] for m, s in univ.items())))
    drop_p.write_bytes(hb._gz_csv_bytes(["key", "source"], sorted([k, v] for k, v in drops.items())))
    report = {"cb16_keys_sha256": cb16_sha256 if not cb16_stopped else None, "cb16_rows": len(rows), "cb16_note": src_note, "seal_copies_used": used, "seal_copies_skipped": skipped,
              "seal_copies_sha256": shas, "seal_copies_with_in_window_timestamp": in_window, "n_universe": len(univ), "n_drop_keys": len(drops),
              "drops_by_source": dict(Counter(drops.values())), "window": [c17.iso(lo), c17.iso(hi)], "rule": w.KEY_RULE}
    rep_p = kd / "exclusion_report.json"
    rep_p.write_text(json.dumps(report, indent=1, sort_keys=True))
    c16.write_dir_manifest(kd, win.KEYS_STATUS, [keys_p, drop_p, rep_p], {"report": {k: report[k] for k in ("cb16_rows", "n_universe", "n_drop_keys", "drops_by_source")}})
    return report


def declared() -> dict:
    return {"version": SMOKE_VERSION, "criteria": list(w.SMOKE_CRITERIA), "p1_expected": P1_EXPECTED, "p2_expected": P2_EXPECTED, "p3_expected": P3_EXPECTED, "p1_captures": list(P1_CAPTURES),
            "p2_sports_capture": P2_SPORTS_CAPTURE}
