# ruff: noqa: E501
"""CB17 counts-only pre-censuses q0400-q0403 (docs/research_lab/CREATIVE_BATCH_17.md sections 0.1, 2.7, 4, 10.4). Rules part ``pre`` (with ``cb17_pre``).

Streaming, field-restricted readers of the host's WORN window ``[2026-10-12, 2026-10-16)`` and nothing else:
- q0400 ``pre_census_A``: the CB13-T SCREEN fill table (worn), the monitor prints (``side`` is read HERE ONLY: for the agreement count and to sign the side-signed population) and capture touches at or before a transaction (plus the
  static ``created_at`` of two pinned captures). No mark, no later capture, no outcome.
- q0401 ``pre_census_B``: sweeps and static sidecar attributes; the next-pass check reads token presence and the two-sided state only, never a price.
- q0402 ``pre_census_C``: captures ``k - 2 .. k`` only for every interval ``k``; no ``k + 1`` row is ever used.
- q0403 ``cost_lag_map``: sweep depth bands, the sidecar fee fields and the monitor ``recv_ts - ts`` (``recv_ts`` is read HERE ONLY).
Every reader refuses a file or directory outside the census window by name and skips (and counts) any row timed at or after 2026-10-16T00:00Z; results are write-once JSON of counts, shares
and standard errors (a key naming an outcome, a mark or a point estimate is refused by ``cb17_common.assert_clean_result``). A SCREEN_8 / REP_8 window, the CB13-T HOLDOUT and every other
batch's store are refused by path.
"""

from __future__ import annotations

import bisect
import csv
import gzip
import json
import math
import re
from array import array
from collections import Counter, defaultdict, deque
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from . import cb13_label as lab
from . import cb13_t as t13
from . import cb17_common as c17
from . import cb17_pre as pre

Refused = c17.Refused

CREATED_AT_CAPTURES = ("20261012T003103Z_2df48d64", "20261015T223102Z_2eae9aa6")  # the two captures probe P1 read static created_at from
STATE_TWO_SIDED = "two_sided"
RESULT_NAMES = {"A": "pre_census_A.json", "B": "pre_census_B.json", "C": "pre_census_C.json", "cost": "cost_lag_map.json"}
VERSIONS = {"A": "cb17-pre-census-A-v1", "B": "cb17-pre-census-B-v1", "C": "cb17-pre-census-C-v1", "cost": "cb17-cost-lag-map-v1"}
AGE_BIN_NAMES = ("clock_anomaly", "lt60s", "60-600s", "600-3600s", "gt3600s")
OLD_BINS = (3, 4)
FIRST_DAY_BINS = ("neg", "lt6h", "6-24h", "1-7d", "gt7d", "unknown")


# =====================================================================================================================================================
# field-restricted readers
# =====================================================================================================================================================

_EPC: dict[str, float] = {}


def ep_cached(s: str) -> float:
    v = _EPC.get(s)
    if v is None:
        if len(_EPC) > 4096:
            _EPC.clear()
        v = _EPC[s] = c17.ep(s) if s else math.nan
    return v


def is_true(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "t")


def is_sports_sidecar(fee_type, fee_category, series_slugs) -> bool:
    """The sidecar-only sports rule (sweeps and captures carry no title): fee type starting 'sports', a sports fee category, or the first series slug on the frozen sports series list."""
    slug = lab.first_series_slug(series_slugs)
    return str(fee_type or "").lower().startswith("sports") or str(fee_category or "").lower() in lab.SPORTS_CATEGORIES or bool(slug and lab.SPORTS_SERIES_RE.match(slug))


def iter_cols(path: Path, fields: tuple[str, ...], allowed: tuple[str, ...]) -> Iterator[tuple]:
    """Stream the requested columns of a csv.gz. A requested field outside ``allowed`` (the job's whitelist) is a refusal; every other column is never copied."""
    bad = [f for f in fields if f not in allowed]
    if bad:
        raise Refused(f"fields {bad} are not whitelisted for {Path(path).name}")
    csv.field_size_limit(10**9)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd, None)
        if head is None:
            return
        idx = [head.index(f) if f in head else -1 for f in fields]
        for row in rd:
            yield tuple(row[i] if 0 <= i < len(row) else "" for i in idx)


def iter_dir_cols(d: Path, name: str, fields: tuple[str, ...], allowed: tuple[str, ...], time_field: str, stats: Counter) -> Iterator[tuple]:
    """A capture / sweep file's columns with the time column first-parsed: rows at or after the census cut-off are skipped and counted, never yielded."""
    cut = c17.census_cutoff()
    n = len(fields)
    for row in iter_cols(Path(d) / name, (*fields, time_field), (*allowed, time_field)):
        t = ep_cached(row[n])
        if not math.isfinite(t) or t >= cut:
            stats["rows_at_or_after_cutoff_skipped"] += 1
            continue
        yield (*row[:n], t)


def list_stamped(root: Path, pattern: str, lo: str, stats: Counter) -> list[tuple[Path, float]]:
    """Directories whose start stamp lies in ``[lo, cut-off)``, oldest first. A directory at or after the cut-off is counted and never opened."""
    out: list[tuple[Path, float]] = []
    for d in sorted(Path(root).iterdir()):
        m = re.match(pattern, d.name)
        if not m or not d.is_dir():
            continue
        t = c17.stamp_epoch(m.group(1))
        if t >= c17.census_cutoff():
            stats["dirs_at_or_after_cutoff_not_opened"] += 1
            continue
        if t >= c17.ep(lo):
            out.append((d, t))
    return out


def iter_monitor(trades_dir: Path, stats: Counter, *, side: bool = False, lag: bool = False) -> Iterator[dict]:
    """Whitelisted prints of the census days, one line in memory. ``side`` is added for q0400 only, ``recv_ts`` for q0403 only; wallet, key and every other field are never copied.
    A print timed at or after the cut-off is skipped and counted."""
    cut = c17.census_cutoff()
    for day in c17.CENSUS_DAYS:
        p = c17.guard_monitor_file(Path(trades_dir) / f"trades-{day}.jsonl")
        if not p.exists():
            stats["monitor_days_missing"] += 1
            continue
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    stats["monitor_bad_lines"] += 1
                    continue
                if not isinstance(rec, dict):
                    continue
                ts, px, sz = c17.num(rec.get("ts")), c17.num(rec.get("price")), c17.num(rec.get("size"))
                try:
                    oi = int(rec.get("outcome_index"))
                except (TypeError, ValueError):
                    stats["monitor_unusable"] += 1
                    continue
                if not math.isfinite(ts) or oi not in (0, 1) or not rec.get("condition_id"):
                    stats["monitor_unusable"] += 1
                    continue
                if not (math.isfinite(px) and math.isfinite(sz)) or sz <= 0:
                    stats["monitor_prints_without_usable_price_or_size"] += 1  # kept: probe P1 resolved fills from condition_id, ts, tx16, outcome_index alone; consumers that need a price skip these
                if ts >= cut:
                    stats["prints_at_or_after_cutoff_skipped"] += 1
                    continue
                w = {k: rec.get(k) for k in c17.PRINT_FIELDS}
                w.update(ts=ts, price=px, size=sz, outcome_index=oi, cash=c17.num(rec.get("cash")), tx16=str(rec.get("tx16") or ""))
                if side:
                    w["side"] = str(rec.get("side") or "").upper()
                if lag:
                    w["recv_ts"] = c17.num(rec.get("recv_ts"))
                yield w


def read_fills(tdir: Path, stats: Counter) -> list[dict]:
    """CB13-T SCREEN ``fills.csv.gz`` (worn): status 'fill' rows, whitelisted columns; a fill timed at or after the cut-off is a refusal (the SCREEN table must end before it)."""
    p = c17.guard_cb13_t_screen_file(Path(tdir) / "fills.csv.gz")
    out = []
    for row in iter_cols(p, c17.FILLS_FIELDS, c17.FILLS_FIELDS):
        r = dict(zip(c17.FILLS_FIELDS, row, strict=True))
        if r["status"] != "fill":
            stats["fills_not_fill_status"] += 1
            continue
        for k in ("tau", "tau_last"):
            v = r[k]
            try:
                r[k] = float(v)
            except ValueError:
                r[k] = c17.ep(v)
            c17.guard_census_time(r[k], f"fill {k}")
        for k in ("d", "P", "size", "cash", "spread0", "mid0", "prev_mid", "touch_age_s", "block"):
            r[k] = c17.num(r[k])
        out.append(r)
    return out


def band_counts(c: Counter) -> dict:
    return {str(k): int(v) for k, v in sorted(c.items(), key=lambda kv: str(kv[0]))}


# =====================================================================================================================================================
# static sidecar index (first seen wins, as CB13 load_quote_index) and capture loading
# =====================================================================================================================================================

STATIC_FIELDS = ("event", "end", "liq", "sports", "reward", "slug", "fee_cat", "fee_rate", "nrm")


def build_static(caps: list[tuple[Path, float]], stats: Counter) -> dict[str, tuple]:
    """market_id -> (event, end_epoch, liquidity, sports, reward, first series slug, fee category, fee rate, neg-risk market id), from the first worn capture that carries the market."""
    st: dict[str, tuple] = {}
    for cdir, _t in caps:
        c17.guard_capture_dir(cdir)
        base: dict[str, tuple] = {}
        for mid, ev, end, liq, _t1 in iter_dir_cols(cdir, "rows.csv.gz", ("market_id", "event_id", "end_date", "liquidity"), c17.CAPTURE_FIELDS, "received_utc", stats):
            if mid not in st and mid not in base:
                base[mid] = (ev, ep_cached(end) if end else math.nan, c17.num(liq))
        for mid, ft, fc, fs, rw, ss, nrm, _t2 in iter_dir_cols(cdir, "rows_ext.csv.gz", ("market_id", "fee_type", "fee_category", "fee_schedule", "clob_rewards", "series_slugs", "neg_risk_market_id"), c17.SIDECAR_FIELDS, "received_utc", stats):
            if mid in st or mid not in base:
                continue
            ev, end, liq = base[mid]
            st[mid] = (ev, end, liq, is_sports_sidecar(ft, fc, ss), 1 if str(rw or "") not in ("", "[]", "null") else 0, lab.first_series_slug(ss) or "", fc or "none", t13.fee_rate_of(fs), nrm or "")
    return st


def hour6_name(t: float) -> str:
    return f"h{c17.band6(t) * 6:02d}"


# =====================================================================================================================================================
# q0400: pre-census A / E
# =====================================================================================================================================================


def token_open(oi: int, d: int) -> bool:
    """The taker bought the traded token iff (outcome 0 and d = -1) or (outcome 1 and d = +1): d is the maker's YES-terms direction (CB13-T)."""
    return (oi == 0 and d == -1) or (oi == 1 and d == 1)


def age_bin_first_day(h: float) -> str:
    return "unknown" if h < 0 else "lt6h" if h < 6 else "6-24h" if h < 24 else "1-7d" if h < 168 else "gt7d"


def read_created_at(snap_dir: Path, names: tuple[str, ...], stats: Counter) -> dict[str, float]:
    """Static ``created_at`` per market from the pinned captures (market_id and created_at columns only)."""
    out: dict[str, float] = {}
    for nm in names:
        d = Path(snap_dir) / nm
        if not d.exists():
            stats["created_at_capture_missing"] += 1
            continue
        c17.guard_capture_dir(d)
        for mid, cr, _t in iter_dir_cols(d, "rows_ext.csv.gz", ("market_id", "created_at"), c17.SIDECAR_FIELDS, "received_utc", stats):
            if cr and mid not in out:
                try:
                    out[mid] = float(cr)
                except ValueError:
                    v = c17.ep(cr)
                    if math.isfinite(v):
                        out[mid] = v
    return out


def pop_report(family: str, units: list[dict]) -> dict:
    """Strata-level informativeness (features only) for a population of A units: cell = (market, d), label = open. The test is A1, which uses (market, d) cells holding BOTH labels
    (section CB17-A), so the units of the test, the denominator of the share, are the units in those cells (INFORMATIVENESS['binary'], item 3)."""
    cells: dict = defaultdict(int)
    for u in units:
        cells[(u["market"], u["d"])] |= 2 if u["open"] else 1
    test_units = [u for u in units if cells[(u["market"], u["d"])] == 3]
    rep = pre.level_report(family, test_units, lambda u: (u["market"], u["d"]), lambda u: u["open"])
    return {**rep, "units_eligible": len(units), "units_in_both_label_cells": len(test_units)}


def a1_se(units: list[dict], way_names: tuple[str, str]) -> dict:
    u = [x for x in units if math.isfinite(x["a_pre"])]
    ways = {"event": [x["event"] for x in u], way_names[0]: [(x[way_names[1]], c17.block6(x["ts"])) for x in u], "block6": [c17.block6(x["ts"]) for x in u]}
    return pre.fe_cluster_se([x["a_pre"] for x in u], [x["open"] for x in u], [(x["market"], x["d"]) for x in u], ways)


def first_day_se(units: list[dict], created: dict[str, float], way_names: tuple[str, str]) -> dict:
    u = [x for x in units if math.isfinite(x["a_pre"]) and x["market"] in created and x["ts"] >= created[x["market"]]]
    fd = [1.0 if x["ts"] - created[x["market"]] < pre.FIRST_DAY_S else 0.0 for x in u]
    ways = {"event": [x["event"] for x in u], way_names[0]: [(x[way_names[1]], c17.block6(x["ts"])) for x in u], "block6": [c17.block6(x["ts"]) for x in u]}
    return pre.fe_cluster_se([x["a_pre"] for x in u], fd, [x["market"] for x in u], ways)


def touch_ok(bid: float, ask: float, closed: bool, binary: bool, end: float, tau: float, ok_end_buffer: float = 3 * 3600.0) -> str | None:
    """None when the touch is eligible, else the reason (branch-S eligibility: two-sided, spread <= 10c, mid in [0.03, 0.97], open binary market, end >= tau + 3 h when known)."""
    if not t13.two_sided(bid, ask):
        return "touch_one_sided_or_crossed"
    if ask - bid > pre.MAX_SPREAD + 1e-12:
        return "touch_wide"
    mid = (bid + ask) / 2.0
    if not pre.MID_RANGE[0] <= mid <= pre.MID_RANGE[1]:
        return "touch_extreme_mid"
    if closed or not binary:
        return "touch_closed_or_not_binary"
    if math.isfinite(end) and end < tau + ok_end_buffer:
        return "touch_end_too_near"
    return None


def pre_census_A(fills_dir: Path, trades_dir: Path, snap_dir: Path) -> dict:
    """q0400. Counts, shares and standard errors only (see the module docstring)."""
    stats: Counter = Counter()
    fills = read_fills(fills_dir, stats)
    need = {f["condition_id"] for f in fills}
    pr: dict[tuple, set] = defaultdict(set)  # (condition, ts) -> {(tx16, outcome_index, side)}
    groups: dict[tuple, list] = {}
    cls_cache: dict[str, str] = {}
    n_single = 0
    for p in iter_monitor(trades_dir, stats, side=True):
        c, oi = p["condition_id"], p["outcome_index"]
        if c in need:
            pr[(c, int(p["ts"]))].add((p["tx16"], oi, p["side"]))
        k = cls_cache.get(c)
        if k is None:
            k = cls_cache[c] = lab.classify(p["title"], p["slug"], p["ctx_fee_type"] or "", "", "", p["ctx_category"] or "")
        if k[0] == lab.SPORTS:
            stats["prints_sports_not_stored"] += 1
            continue
        if not (math.isfinite(p["price"]) and math.isfinite(p["size"]) and p["size"] > 0):
            stats["prints_without_price_or_size_not_in_s_population"] += 1
            continue
        k, under = k
        n_single += 0 if p["tx16"] else 1
        key = (p["tx16"], c) if p["tx16"] else (f"single:{n_single}", c)
        yes = p["price"] if oi == 0 else 1.0 - p["price"]
        cash = p["cash"] if math.isfinite(p["cash"]) else p["size"] * p["price"]
        g = groups.get(key)
        if g is None:
            groups[key] = [p["ts"], p["ts"], yes, yes, cash, {oi}, {p["side"]}, k, str(p["ctx_market_id"] or ""), str(p["ctx_event_id"] or ""), under or ""]
        else:
            g[0], g[1] = min(g[0], p["ts"]), max(g[1], p["ts"])
            g[2], g[3], g[4] = min(g[2], yes), max(g[3], yes), g[4] + cash
            g[5].add(oi)
            g[6].add(p["side"])
    created = read_created_at(snap_dir, CREATED_AT_CAPTURES, stats)

    # ---- the touch-consistent population (CB13-T SCREEN fills), as probe P1 ----
    res: Counter = Counter()
    lab_by_i: dict[int, tuple[str, int, int]] = {}  # fill index -> (open/close, outcome index, determinate side or "")
    for i, f in enumerate(fills):
        s: set = set()
        for t in range(int(f["tau"]), int(f["tau_last"]) + 1):
            s |= pr.get((f["condition_id"], t), set())
        if not s:
            res["no_print"] += 1
            continue
        if len({a for a, _, _ in s}) > 1:
            res["ambiguous_tx"] += 1
            continue
        ois = {b for _, b, _ in s}
        if len(ois) != 1:
            res["mixed_or_unknown_token"] += 1
            continue
        oi = next(iter(ois))
        sides = {c for _, _, c in s if c in (pre.SIDE_BUY, pre.SIDE_SELL)}
        res["resolved"] += 1
        lab_by_i[i] = ("open" if token_open(oi, int(f["d"])) else "close", oi, next(iter(sides)) if len(sides) == 1 else "")
    ns = [i for i, f in enumerate(fills) if f["label"] != lab.SPORTS]
    ns_res = [i for i in ns if i in lab_by_i]
    label_counts = Counter(lab_by_i[i][0] for i in ns_res)
    by_class = Counter((fills[i]["label"], lab_by_i[i][0]) for i in ns_res)
    by_pband = Counter((pre.p_band(fills[i]["P"]), lab_by_i[i][0]) for i in ns_res)
    cell: dict = defaultdict(Counter)
    for i in ns_res:
        cell[(fills[i]["market_id"], int(fills[i]["d"]))][lab_by_i[i][0]] += 1
    both = {k for k, v in cell.items() if v["open"] and v["close"]}
    both_fills = [i for i in ns_res if (fills[i]["market_id"], int(fills[i]["d"])) in both]

    # ---- side agreement (the branch rule's measurement) ----
    ag_all, ag_cells = Counter(), {"touch_age": defaultdict(Counter), "p_band": defaultdict(Counter), "class": defaultdict(Counter)}
    for i in ns_res:
        kind, _oi, sd = lab_by_i[i]
        if not sd:
            res["resolved_without_one_side"] += 1  # a missing or mixed side is NON-agreement, overall and in every cell (section 2.3: unknown never counts as met)
        f = fills[i]
        ok = int(sd == (pre.SIDE_BUY if kind == "open" else pre.SIDE_SELL)) if sd else 0
        ab, pb = pre.touch_age_band(f["touch_age_s"]), pre.p_band(f["P"])
        ag_all["n"] += 1
        ag_all["k"] += ok
        for dim, name in (("touch_age", pre.TOUCH_AGE_BAND_NAMES[ab] if ab is not None else "outside"), ("p_band", pre.P_BAND_NAMES[pb] if pb is not None else "outside"), ("class", f["label"])):
            ag_cells[dim][name]["n"] += 1
            ag_cells[dim][name]["k"] += ok
    ag_cells_d = {d: {n: dict(c) for n, c in v.items() if n != "outside"} for d, v in ag_cells.items()}
    branch = pre.branch_decision(dict(ag_all), ag_cells_d)

    # ---- touch-consistent (T) units and the A1 / first-day proxies ----
    t_units = [{"market": fills[i]["market_id"], "event": fills[i]["event_id"] or fills[i]["market_id"], "path": fills[i]["path_key"] or fills[i]["event_id"], "d": int(fills[i]["d"]),
                "open": 1 if lab_by_i[i][0] == "open" else 0, "p": fills[i]["P"], "size_usd": fills[i]["cash"], "ts": fills[i]["tau"], "spread": fills[i]["spread0"],
                "a_pre": fills[i]["d"] * (fills[i]["mid0"] - fills[i]["prev_mid"]) * 100.0 if math.isfinite(fills[i]["prev_mid"]) and math.isfinite(fills[i]["mid0"]) else math.nan}
               for i in ns_res if pre.p_band(fills[i]["P"]) is not None and math.isfinite(fills[i]["spread0"]) and math.isfinite(fills[i]["cash"])]

    # ---- the side-signed (S) population: non-sports transactions with one token and one side, touch from captures at or before tau ----
    wanted = {k[1] for k in groups}
    caps_by: dict[str, tuple[list[float], list[tuple]]] = {}
    for cdir, _t in list_stamped(snap_dir, c17.CAPTURE_DIR_RE, c17.CAPTURE_LOOKBACK_START, stats):
        c17.guard_capture_dir(cdir, c17.CAPTURE_LOOKBACK_START)
        rows = [r for r in iter_dir_cols(cdir, "rows.csv.gz", ("condition_id", "closed", "binary", "best_bid", "best_ask", "end_date"), c17.CAPTURE_FIELDS, "received_utc", stats)]
        if not rows:
            continue
        t_cap = max(r[-1] for r in rows)  # a capture's time is its LAST page's received_utc
        for cond, closed, binary, bid, ask, end, _t in rows:
            if cond in wanted:
                ts_l, ent = caps_by.setdefault(cond, ([], []))
                ts_l.append(t_cap)
                ent.append((c17.num(bid), c17.num(ask), is_true(closed), is_true(binary), ep_cached(end) if end else math.nan))
    s_reasons: Counter = Counter()
    s_units: list[dict] = []
    ns_tx = first_day_tx = 0
    fd_unsignable = Counter()
    for (_tx, cond), g in groups.items():
        tau, _tl, pmin, pmax, cash, ois, sides, klass, mkt, ev, under = g
        ns_tx += 1
        h = (tau - created[mkt]) / 3600.0 if mkt in created else math.nan
        is_fd = math.isfinite(h) and 0 <= h < 24
        first_day_tx += is_fd
        if len(ois) != 1:
            s_reasons["mixed_token"] += 1
            continue
        sd = {x for x in sides if x in (pre.SIDE_BUY, pre.SIDE_SELL)}
        if len(sd) != 1:
            s_reasons["no_or_mixed_side"] += 1
            continue
        oi, side = next(iter(ois)), next(iter(sd))
        ts_l, ent = caps_by.get(cond, ([], []))
        j = bisect.bisect_left(ts_l, tau) - 1
        why = None
        if j < 0:
            why = "no_touch_capture"
        elif tau - ts_l[j] > pre.TOUCH_AGE_MAX_S["S"]:
            why = "touch_older_than_135min"
        else:
            bid, ask, closed, binary, end = ent[j]
            why = touch_ok(bid, ask, closed, binary, end, tau)
        if why:
            s_reasons[why] += 1
            if is_fd:
                fd_unsignable[why] += 1
            continue
        tdir = 1 if (side == pre.SIDE_BUY) == (oi == 0) else -1
        d = -tdir
        p = pmin if d == -1 else pmax
        if pre.p_band(p) is None:
            s_reasons["P_outside_0.03_0.97"] += 1
            continue
        mid = (bid + ask) / 2.0
        a_pre = math.nan
        if j >= 1:
            b0, a0, *_ = ent[j - 1]
            if t13.two_sided(b0, a0):
                a_pre = d * (mid - (b0 + a0) / 2.0) * 100.0
        s_units.append({"market": mkt or cond, "event": ev or mkt or cond, "path": under if (klass == lab.PATH and under) else f"event:{ev or mkt or cond}", "d": d, "open": 1 if side == pre.SIDE_BUY else 0, "p": p, "size_usd": cash, "ts": tau, "spread": ask - bid,
                        "a_pre": a_pre, "created_h": h})
    fd_bins_t, fd_bins_s = Counter(), Counter()
    mk_t, mk_s = defaultdict(set), defaultdict(set)
    for u in t_units:
        hh = (u["ts"] - created[u["market"]]) / 3600.0 if u["market"] in created else math.nan
        b = age_bin_first_day(hh) if math.isfinite(hh) else "unknown"
        fd_bins_t[b] += 1
        if b in ("lt6h", "6-24h", "1-7d"):  # first day (< 24 h) versus later = 1-7 d; older and unknown ages are in neither (section CB17-E)
            mk_t[u["market"]].add("first" if b != "1-7d" else "later")
    for u in s_units:
        hh = u["created_h"]
        b = age_bin_first_day(hh) if math.isfinite(hh) else "unknown"
        fd_bins_s[b] += 1
        if b in ("lt6h", "6-24h", "1-7d"):
            mk_s[u["market"]].add("first" if b != "1-7d" else "later")
    first_later = lambda m: sorted(k for k, s in m.items() if s == {"first", "later"})  # noqa: E731

    p1 = pre.p1_reproduction({"fills": len(fills), "token_resolved": res["resolved"], "ambiguous_transaction": res["ambiguous_tx"], "non_sports": len(ns), "non_sports_resolved": len(ns_res),
                              "open": label_counts["open"], "close": label_counts["close"]})
    sel_pop = "S" if branch["branch"] == pre.BRANCH_S else "T"
    rep_t, rep_s = pop_report("A", t_units), pop_report("A", s_units)
    return {
        "version": VERSIONS["A"], "counts_only": True, "window": [c17.CENSUS_START, c17.CENSUS_CUTOFF],
        "input_stats": band_counts(stats), "fills": {"n": len(fills), "token_resolution": band_counts(res), "non_sports": len(ns), "non_sports_resolved": len(ns_res)},
        "labels": {"non_sports": band_counts(label_counts), "by_class": {f"{k[0]}|{k[1]}": v for k, v in sorted(by_class.items())},
                   "by_p_band": {f"{pre.P_BAND_NAMES[k[0]] if k[0] is not None else 'outside'}|{k[1]}": v for k, v in sorted(by_pband.items(), key=lambda kv: str(kv[0]))}},
        "both_label_cells": {"cells": len(cell), "with_both": len(both), "fills": len(both_fills), "markets": len({k[0] for k in both}), "events": len({fills[i]["event_id"] for i in both_fills})},
        "side_agreement": {"overall": dict(ag_all), "cells": ag_cells_d, "rule": branch},
        "p1_reproduction": p1, "branch_recorded": p1["matches"], "branch": branch["branch"], "a_withdrawn_uncounted": branch["branch"] == pre.BRANCH_T,
        "strata": {"selected_population": sel_pop, "selected_level": (rep_s if sel_pop == "S" else rep_t)["selected_level"], "touch_consistent_T": rep_t, "side_signed_S": rep_s},
        "side_signed_population": {"non_sports_transactions": ns_tx, "eligible_units": len(s_units), "open": sum(u["open"] for u in s_units), "excluded_by_reason": band_counts(s_reasons)},
        "first_day": {"pinned_captures": list(CREATED_AT_CAPTURES), "markets_with_created_at": len(created),
                      "T_units_by_age": band_counts(fd_bins_t), "S_units_by_age": band_counts(fd_bins_s), "T_markets_first_and_later": len(first_later(mk_t)), "S_markets_first_and_later": len(first_later(mk_s)),
                      "non_sports_transactions_first_day": first_day_tx, "first_day_unsignable_by_reason": band_counts(fd_unsignable)},
        "planning_se": {"A1_T_pre_fill_proxy": a1_se(t_units, ("path_x_block", "path")), "A1_S_pre_fill_proxy": a1_se(s_units, ("path_x_block", "path")),
                        "E_T_first_day_proxy": first_day_se(t_units, created, ("path_x_block", "path")), "E_S_first_day_proxy": first_day_se(s_units, created, ("path_x_block", "path")),
                        "recipe": pre.SE_RECIPE, "proxy": pre.PROXIES["A"]},
    }


# =====================================================================================================================================================
# q0401: pre-census B (sweeps)
# =====================================================================================================================================================

SWEEP_LOAD_FIELDS = ("token_id", "market_id", "book_timestamp", "book_hash", "best_bid", "best_ask", "bid_size_1", "ask_size_1", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c", "n_bid_levels", "n_ask_levels", "state")


def age_bin(a: float) -> int:
    e = pre.AGE_BIN_EDGES_S
    return 0 if a < e[0] else 1 if a < e[1] else 2 if a < e[2] else 3 if a < e[3] else 4


def load_sweep(sdir: Path, static: dict, stats: Counter) -> tuple[dict, int]:
    """Non-sports tokens of one sweep -> (market, receipt epoch, book age s, hash int, bid str, ask str, bid f, ask f, bs1, as1, db1, da1, db5, da5, levels, two_sided). Sports tokens are counted only."""
    out: dict[str, tuple] = {}
    n_sports = 0
    for row in iter_dir_cols(sdir, "rows.csv.gz", SWEEP_LOAD_FIELDS, c17.SWEEP_FIELDS, "batch_receipt_utc", stats):
        tk, mk, bts, bh, bid, ask, bs1, as1, db1, da1, db5, da5, nb, na, state, recv = row
        s = static.get(mk)
        if s is not None and s[3]:
            n_sports += 1
            continue
        if s is None:
            stats["tokens_without_sidecar_treated_non_sports"] += 1
        bt = c17.num(bts)
        out[tk] = (mk, recv, (recv - bt / 1000.0) if math.isfinite(bt) else math.nan, hash(bh), bid, ask, c17.num(bid), c17.num(ask), c17.num(bs1), c17.num(as1), c17.num(db1), c17.num(da1),
                   c17.num(db5), c17.num(da5), c17.num(nb) + c17.num(na), state == STATE_TWO_SIDED, hash(bts))
    return out, n_sports


def pair_passes(sweeps: list[tuple[Path, float]]) -> tuple[list[tuple[tuple[Path, float], tuple[Path, float]]], int]:
    """Two consecutive sweeps whose start stamps are < 30 min apart form a pass; a sweep with no partner is counted."""
    passes, lone, i = [], 0, 0
    while i < len(sweeps):
        if i + 1 < len(sweeps) and sweeps[i + 1][1] - sweeps[i][1] < pre.PASS_GAP_S:
            passes.append((sweeps[i], sweeps[i + 1]))
            i += 2
        else:
            lone += 1
            i += 1
    return passes, lone


def pre_census_B(sweep_dir: Path, snap_dir: Path) -> dict:
    """q0401. Counts, shares, cut points and standard errors only."""
    stats: Counter = Counter()
    sweeps = list_stamped(sweep_dir, c17.SWEEP_DIR_RE, c17.CENSUS_START, stats)
    caps = list_stamped(snap_dir, c17.CAPTURE_DIR_RE, c17.CENSUS_START, stats)
    static = build_static(caps, stats)
    passes, lone = pair_passes(sweeps)
    tok_idx: dict[str, int] = {}
    ev_idx: dict[str, int] = {}
    path_idx: dict[str, int] = {}
    c: Counter = Counter()
    age_tab: Counter = Counter()
    fresh_old: dict[int, set] = defaultdict(set)
    ev_fo: dict[str, set] = defaultdict(set)
    mark_tab: dict[int, Counter] = defaultdict(Counter)
    cross: Counter = Counter()
    dorm: dict[str, Counter] = {"levels": Counter(), "hour": Counter(), "reward": Counter()}
    hist: deque = deque(maxlen=4)  # (t, {token: hash})
    prev1 = prev2 = None  # (t, {token: (mid, bid, ask)})
    pending: list[tuple[float, dict[int, int]]] = []  # (pass t, {token idx: age bin}) awaiting the 2 h mark pass
    cols = {n: array(t) for n, t in (("tok", "i"), ("ev", "i"), ("path", "i"), ("ts", "d"), ("spread", "f"), ("act", "f"), ("imb", "f"), ("old", "b"), ("lpre", "f"), ("dmpre", "f"), ("x", "f"), ("reward", "b"))}
    for (d1, t1), (d2, _t2) in passes:
        c17.guard_sweep_dir(d1)
        c17.guard_sweep_dir(d2)
        s1, n_sp1 = load_sweep(d1, static, stats)
        s2, _ = load_sweep(d2, static, stats)
        c["sports_tokens_first_sweeps"] += n_sp1
        if not s1:
            continue
        c["passes"] += 1
        # resolve the pending marks whose 2 h pass this is (presence and two-sided state only; no price is read)
        keep = []
        for pt, bins in pending:
            gap = t1 - pt
            if pre.MARK_WINDOW_S[0] <= gap <= pre.MARK_WINDOW_S[1]:
                tk_names = {tok_idx[k]: v for k, v in s1.items() if k in tok_idx and v[15]}
                for ti, b in bins.items():
                    mark_tab[b]["present"] += ti in tk_names
                    mark_tab[b]["absent_at_next_pass"] += ti not in tk_names
            elif gap < pre.MARK_WINDOW_S[0]:
                keep.append((pt, bins))
            else:
                for b in bins.values():
                    mark_tab[b]["no_pass_in_window"] += 1
        pending = keep
        bins_now: dict[int, int] = {}
        gap1 = (t1 - prev1[0]) if prev1 else math.inf
        p1 = prev1[1] if prev1 and gap1 <= pre.PREV_PASS_MAX_GAP_S else None
        p2 = prev2[1] if p1 is not None and prev2 and (prev1[0] - prev2[0]) <= pre.PREV_PASS_MAX_GAP_S else None
        dormancy = {h: next((hh for tt, hh in reversed(hist) if abs((t1 - tt) - h * 3600.0) <= 600.0), None) for h in (2, 4, 6)}
        for tk, r in s1.items():
            mk, recv, age, hsh, bid_s, ask_s, bid, ask, bs1, as1, db1, da1, db5, da5, lv, two, _bt = r
            st = static.get(mk)
            ti = tok_idx.setdefault(tk, len(tok_idx))
            ab = age_bin(age) if math.isfinite(age) else -1
            liq = pre.liq_band(st[2]) if st else None
            if ab >= 0:
                age_tab[(AGE_BIN_NAMES[ab], hour6_name(recv), liq)] += 1
                c[f"age_{AGE_BIN_NAMES[ab]}"] += 1
                if ab == 1:
                    fresh_old[ti].add("fresh")
                    if st:
                        ev_fo[st[0]].add("fresh")
                if ab in OLD_BINS:
                    fresh_old[ti].add("old")
                    if st:
                        ev_fo[st[0]].add("old")
                if two:
                    bins_now[ti] = ab
                    sub = (bid_s and "." in bid_s and len(bid_s.split(".")[1].rstrip("0")) > 2) or (ask_s and "." in ask_s and len(ask_s.split(".")[1].rstrip("0")) > 2)
                    rnd = math.isfinite(bs1) and math.isfinite(as1) and bs1 % pre.ROUND_SIZE_MULTIPLE == 0 and as1 % pre.ROUND_SIZE_MULTIPLE == 0
                    cross[(AGE_BIN_NAMES[ab], "subcent" if sub else "cent", "round" if rnd else "other")] += 1
            # CH149 dormancy: hash unchanged 2 / 4 / 6 h earlier, by levels, hour band and reward programme
            lvb = 0 if lv <= pre.LEVEL_BAND_EDGES[0] else 1 if lv <= pre.LEVEL_BAND_EDGES[1] else 2
            for h, prev_h in dormancy.items():
                if prev_h is not None and tk in prev_h:
                    same = int(prev_h[tk] == hsh)
                    for tab, key in (("levels", f"{h}h|lv{lvb}"), ("hour", f"{h}h|{hour6_name(recv)}"), ("reward", f"{h}h|rw{st[4] if st else 'na'}")):
                        dorm[tab][key + "|n"] += 1
                        dorm[tab][key + "|unchanged"] += same
            if ab <= 0:  # clock anomaly (a < -5 s) or no usable stamp: excluded from every unit, cut point and B2 (section 2.2), counted
                c["unit_clock_anomaly_or_no_stamp"] += 1
                continue
            # the shared B frame: decision unit eligibility (two-sided, spread <= 10c, mid in range, end known-near excluded)
            if not two or not t13.two_sided(bid, ask):
                c["unit_not_two_sided"] += 1
                continue
            spread, mid = ask - bid, (ask + bid) / 2.0
            if spread > pre.MAX_SPREAD + 1e-12 or not pre.MID_RANGE[0] <= mid <= pre.MID_RANGE[1]:
                c["unit_wide_or_extreme"] += 1
                continue
            if st and math.isfinite(st[1]) and st[1] < recv + pre.B_END_BUFFER_S:
                c["unit_end_too_near"] += 1
                continue
            act = abs(mid - p1[tk][0]) * 100.0 if p1 is not None and tk in p1 else math.nan
            if not math.isfinite(act):
                c["unit_no_activity"] += 1
                continue
            lpre = dmpre = math.nan
            if p2 is not None and tk in p2 and tk in p1:
                m1, (_m2, b2, a2) = p1[tk][0], p2[tk]
                lpre = 100.0 * (max(0.0, m1 - a2) + max(0.0, b2 - m1))
            dmpre = (mid - p1[tk][0]) * 100.0
            x = imb = math.nan
            r2 = s2.get(tk)
            if r2 is not None:
                if abs(r2[1] - recv) > pre.SPLIT_PASS_S:
                    c["split_pass"] += 1
                elif r2[15]:
                    # GBT / GBS counts (non-sports two-sided pairs), as probe P2
                    c["pair_two_sided"] += 1
                    sh, stp = r[3] == r2[3], r[16] == r2[16]
                    c["hash_same"] += sh
                    c["hash_same_stamp_same"] += sh and stp
                    c["hash_changed"] += not sh
                    c["hash_changed_stamp_changed"] += (not sh) and (not stp)
                    if bid_s == r2[4] and ask_s == r2[5]:
                        c["touch_unchanged"] += 1
                        c["touch_unchanged_hash_changed"] += not sh
                        sa = (r2[13] - r2[11]) - (da5 - da1)
                        sb = (r2[12] - r2[10]) - (db5 - db1)
                        s_ = sa - sb
                        c["touch_unchanged_shifted"] += s_ != 0
                        d1_ = db5 + da5
                        if math.isfinite(s_) and d1_ > 0:
                            x = max(-1.0, min(1.0, -s_ / d1_))
                            imb = (r2[12] - r2[13]) / d1_  # (B5 - A5) / D1 at the SECOND sweep, D1 of the first sweep (section 3, B2 strata; B_IMBALANCE_RECIPE)
            slug = st[5] if st else ""
            old = 1 if ab in OLD_BINS else 0 if ab == 1 else -1
            cols["tok"].append(ti)
            cols["ev"].append(ev_idx.setdefault(st[0] if st and st[0] else mk, len(ev_idx)))
            cols["path"].append(path_idx.setdefault(slug or (st[0] if st and st[0] else mk), len(path_idx)))
            cols["ts"].append(recv)
            cols["spread"].append(spread)
            cols["act"].append(act)
            cols["imb"].append(imb)
            cols["old"].append(old)
            cols["lpre"].append(lpre)
            cols["dmpre"].append(dmpre)
            cols["x"].append(x)
            cols["reward"].append(st[4] if st else 0)
            c["units"] += 1
        pending.append((t1, bins_now))
        prev2, prev1 = prev1, (t1, {tk: ((r[7] + r[6]) / 2.0, r[6], r[7]) for tk, r in s1.items() if r[15] and t13.two_sided(r[6], r[7])})
        hist.append((t1, {tk: r[3] for tk, r in s1.items()}))
        s1 = s2 = None
    for _pt, bins in pending:
        for b in bins.values():
            mark_tab[b]["no_pass_in_window"] += 1
    # ---- global cut points (features only), strata levels and planning SEs ----
    a = {k: np.frombuffer(v, dtype={"i": np.int32, "d": np.float64, "f": np.float32, "b": np.int8}[v.typecode]) for k, v in cols.items()}
    n = len(a["tok"])
    act_cuts = pre.tercile_cuts(a["act"].tolist()) if n else None
    b2m = np.isfinite(a["x"])
    imb_cuts = pre.tercile_cuts(a["imb"][b2m].tolist()) if b2m.any() else None
    sd_x = float(np.std(a["x"][b2m])) if b2m.sum() > 1 else math.nan

    def unit_iter(mask: np.ndarray, family: str):
        idx = np.nonzero(mask)[0]
        for i in idx:
            u = {"tok": int(a["tok"][i]), "ts": float(a["ts"][i]), "spread": float(a["spread"][i]), "act": pre.tercile_of(float(a["act"][i]), act_cuts) if act_cuts else 0, "reward": int(a["reward"][i]),
                 "x": float(a["x"][i]), "old": int(a["old"][i])}
            if family == "B2":
                u["imb"] = pre.tercile_of(float(a["imb"][i]), imb_cuts) if imb_cuts else 0
            yield u

    b1m, b2m_ = a["old"] >= 0, b2m
    rep_b1 = pre.level_report("B1", lambda: unit_iter(b1m, "B1"), lambda u: u["tok"], lambda u: u["old"]) if b1m.any() and act_cuts else None
    rep_b2 = pre.level_report("B2", lambda: unit_iter(b2m_, "B2"), lambda u: u["tok"], lambda u: u["x"]) if b2m_.any() and act_cuts and imb_cuts else None

    def ways(mask: np.ndarray) -> dict:
        ev, pth, ts = a["ev"][mask].tolist(), a["path"][mask].tolist(), a["ts"][mask]
        blk = (ts // 21600).astype(np.int64).tolist()
        return {"event": ev, "path_x_block": list(zip(pth, blk, strict=True)), "block6": blk, "utc_hour": ((ts % 86400) // 3600).astype(np.int64).tolist()}

    m1 = b1m & np.isfinite(a["lpre"])
    se_b1 = pre.fe_cluster_se(a["lpre"][m1].tolist(), a["old"][m1].astype(float).tolist(), a["tok"][m1].tolist(), ways(m1)) if m1.any() else {"n": 0}
    m2 = b2m_ & np.isfinite(a["dmpre"]) & (sd_x > 0)
    se_b2 = pre.fe_cluster_se(a["dmpre"][m2].tolist(), (a["x"][m2] / sd_x).tolist(), a["tok"][m2].tolist(), ways(m2)) if m2.any() else {"n": 0}
    both_tokens = sum(1 for s in fresh_old.values() if s == {"fresh", "old"})
    both_events = sum(1 for s in ev_fo.values() if s == {"fresh", "old"})
    age_by: dict[str, dict] = {"hour": defaultdict(Counter), "liquidity": defaultdict(Counter)}
    for (nm, hr, lq), v in age_tab.items():
        age_by["hour"][hr][nm] += v
        age_by["liquidity"][f"liq{lq}"][nm] += v
    return {
        "version": VERSIONS["B"], "counts_only": True, "window": [c17.CENSUS_START, c17.CENSUS_CUTOFF], "input_stats": band_counts(stats),
        "sweeps": {"in_window": len(sweeps), "passes": len(passes), "lone_sweeps": lone, "markets_in_static_index": len(static)},
        "counts": band_counts(c), "age_bins": {k: v for k, v in sorted(c.items()) if k.startswith("age_")},
        "age_by_hour": {h: band_counts(v) for h, v in sorted(age_by["hour"].items())}, "age_by_liquidity": {h: band_counts(v) for h, v in sorted(age_by["liquidity"].items())},
        "tokens_with_both_fresh_and_old": both_tokens, "tokens_seen": len(fresh_old), "events_with_both_fresh_and_old": both_events,
        "stamp_semantics": {"hash_same": c["hash_same"], "hash_same_stamp_same": c["hash_same_stamp_same"], "hash_changed": c["hash_changed"], "hash_changed_stamp_changed": c["hash_changed_stamp_changed"]},
        "breathing_book": {"pairs_two_sided": c["pair_two_sided"], "touch_unchanged": c["touch_unchanged"], "touch_unchanged_hash_changed": c["touch_unchanged_hash_changed"],
                           "touch_unchanged_shifted_1to5c": c["touch_unchanged_shifted"],
                           "shifted_share_of_touch_unchanged": round(c["touch_unchanged_shifted"] / c["touch_unchanged"], 6) if c["touch_unchanged"] else None},
        "next_pass_no_mark_by_age_bin": {AGE_BIN_NAMES[b]: band_counts(v) for b, v in sorted(mark_tab.items()) if 0 <= b < len(AGE_BIN_NAMES)},
        "cut_points": {"activity_terciles_c": list(act_cuts) if act_cuts else None, "imbalance_terciles": list(imb_cuts) if imb_cuts else None, "units": n, "b2_units": int(b2m.sum()),
                       "sd_x": None if not math.isfinite(sd_x) else round(sd_x, 8), "recipe": [pre.B_ACTIVITY_RECIPE, pre.B_IMBALANCE_RECIPE]},
        "strata": {"B1": rep_b1, "B2": rep_b2},
        "dormancy_map_CH149": {t: band_counts(v) for t, v in dorm.items()},
        "age_x_grain_x_size_roundness_CH148": {"|".join(k): v for k, v in sorted(cross.items())},
        "planning_se": {"B1_L_pre": se_b1, "B2_dm_pre": se_b2, "recipe": pre.SE_RECIPE, "proxies": {"B1": pre.PROXIES["B1"], "B2": pre.PROXIES["B2"]}},
    }


# =====================================================================================================================================================
# q0402: pre-census C (captures, k - 2 .. k only)
# =====================================================================================================================================================

CAP_ROW_FIELDS = ("market_id", "closed", "best_bid", "best_ask", "end_date")
EXT_ROW_FIELDS = ("market_id", "event_id", "fee_type", "fee_category", "series_slugs", "neg_risk_market_id", "event_open_interest", "event_volume")


def load_capture_state(cdir: Path, stats: Counter) -> dict:
    """One capture -> {'T': last page receipt, 'mid': {market: mid or nan}, 'closed': set, 'end': {market: epoch}, 'ev': {event: (oi, vol, [markets], sports, neg_risk, slug)}}. Reads rows and sidecar
    of THIS capture only."""
    c17.guard_capture_dir(cdir)
    mid: dict[str, float] = {}
    closed: set[str] = set()
    end: dict[str, float] = {}
    t_max = -math.inf
    for mk, cl, bid, ask, ed, t in iter_dir_cols(cdir, "rows.csv.gz", CAP_ROW_FIELDS, c17.CAPTURE_FIELDS, "received_utc", stats):
        t_max = max(t_max, t)
        b, a = c17.num(bid), c17.num(ask)
        mid[mk] = (a + b) / 2.0 if t13.two_sided(b, a) and a - b <= pre.MAX_SPREAD + 1e-12 and pre.MID_RANGE[0] <= (a + b) / 2.0 <= pre.MID_RANGE[1] else math.nan
        if is_true(cl):
            closed.add(mk)
        if ed:
            end[mk] = ep_cached(ed)
    ev: dict[str, list] = {}
    for mk, e, ft, fc, ss, nrm, oi, vol, t in iter_dir_cols(cdir, "rows_ext.csv.gz", EXT_ROW_FIELDS, c17.SIDECAR_FIELDS, "received_utc", stats):
        t_max = max(t_max, t)
        if not e:
            continue
        rec = ev.get(e)
        if rec is None:
            rec = ev[e] = [c17.num(oi), c17.num(vol), [], False, False, lab.first_series_slug(ss) or ""]
        rec[2].append(mk)
        rec[3] = rec[3] or is_sports_sidecar(ft, fc, ss)
        rec[4] = rec[4] or bool(nrm)
    return {"T": t_max, "mid": mid, "closed": closed, "end": end, "ev": ev}


def pre_census_C(snap_dir: Path) -> dict:
    """q0402. Counts, shares and standard errors only; interval k uses captures k-2, k-1, k and nothing later."""
    stats: Counter = Counter()
    caps = list_stamped(snap_dir, c17.CAPTURE_DIR_RE, c17.CENSUS_START, stats)
    c: Counter = Counter()
    hist: dict[str, list[tuple[float, float]]] = defaultdict(list)  # event -> [(r, dV)] of earlier traded intervals
    splits: Counter = Counter()
    iqr: list[float] = []
    ev_with_units: set[str] = set()
    units: list[dict] = []
    states: deque = deque(maxlen=3)
    for cdir, _t in caps:
        cur = load_capture_state(cdir, stats)
        if not cur["ev"]:
            continue
        states.append(cur)
        c["captures_loaded"] += 1
        if len(states) < 2:
            continue
        prv = states[-2]
        gap = cur["T"] - prv["T"]
        if not (pre.CAP_GAP_S[0] <= gap <= pre.CAP_GAP_S[1]):
            c["interval_gap_outside_100_140min"] += 1
            continue
        c["intervals"] += 1
        pre2 = states[-3] if len(states) == 3 and pre.CAP_GAP_S[0] <= prv["T"] - states[-3]["T"] <= pre.CAP_GAP_S[1] else None
        for e, (oi1, v1, members, sports, nr, slug) in cur["ev"].items():
            r0 = prv["ev"].get(e)
            if sports or r0 is None:
                continue
            oi0, v0 = r0[0], r0[1]
            if not all(math.isfinite(x) for x in (oi0, oi1, v0, v1)):
                c["ns_missing_oi_or_vol"] += 1
                continue
            dv = v1 - v0
            if dv <= 0:
                c["ns_not_traded"] += 1
                continue
            c["ns_traded"] += 1
            c["oi_changed"] += oi1 != oi0
            kind = "single" if len(members) == 1 else "multi_neg_risk" if nr else "multi_other"
            splits[f"traded_{kind}"] += 1
            r = (oi1 - oi0) / dv
            prior = list(hist[e])  # a COPY taken before this interval is added: r_k and dV_k never enter their own cut points (finding 6)
            hist[e].append((r, dv))
            if any(m in prv["closed"] or m in cur["closed"] for m in members):
                c["excluded_member_closed"] += 1
                continue
            if any(cur["end"].get(m, math.inf) <= cur["T"] + pre.MEMBER_END_BUFFER_S for m in members):
                c["excluded_member_closing_within_3h"] += 1
                continue
            moves, c_pre = [], []
            for m in members:
                m0, m1 = prv["mid"].get(m, math.nan), cur["mid"].get(m, math.nan)
                if math.isfinite(m0) and math.isfinite(m1) and abs(m1 - m0) * 100.0 >= pre.MIN_MOVE_C - 1e-9:
                    moves.append((m, (m1 - m0) * 100.0, m0))
            if not moves:
                c["no_qualifying_member"] += 1
                continue
            c["eligible_units"] += 1
            splits[f"eligible_{kind}"] += 1
            if pre2 is not None:
                for m, dm, m0 in moves:
                    mm2 = pre2["mid"].get(m, math.nan)
                    if math.isfinite(mm2):
                        c_pre.append((1.0 if dm > 0 else -1.0) * (m0 - mm2) * 100.0)
            prior_r = [p[0] for p in prior]
            cuts = pre.trailing_cuts(prior_r)
            tdv = pre.trailing_dv([p[1] for p in prior], dv)
            if cuts is None or tdv is None:
                c["thin_history"] += 1
                continue
            cls = pre.c_class(r, cuts)
            c[f"class_{cls}"] += 1
            c["units_with_6_prior"] += 1
            ev_with_units.add(e)
            q1, q3 = np.quantile(prior_r, [0.25, 0.75])
            iqr.append(float(q3 - q1))
            units.append({"event": e, "slug": slug or e, "ts": cur["T"], "abs_dm_c": float(np.mean([abs(dm) for _, dm, _ in moves])), "dv_tercile": tdv[0], "dv_above": tdv[1], "n_moving": len(moves),
                          "cls": cls, "c_pre": float(np.mean(c_pre)) if c_pre else math.nan})
    rep = pre.level_report("C", units, lambda u: u["event"], lambda u: u["cls"]) if units else None
    u_pre = [u for u in units if math.isfinite(u["c_pre"])]
    ways = {"event": [u["event"] for u in u_pre], "path_x_block": [(u["slug"], c17.block6(u["ts"])) for u in u_pre], "block6": [c17.block6(u["ts"]) for u in u_pre],
            "utc_hour": [c17.utc_hour(u["ts"]) for u in u_pre]}
    x = [[1.0 if u["cls"] == pre.CLASS_TRANSFER else 0.0, 1.0 if u["cls"] == pre.CLASS_MERGE else 0.0] for u in u_pre]
    se = pre.fe_cluster_se([u["c_pre"] for u in u_pre], x, [u["event"] for u in u_pre], ways, coef=0) if u_pre else {"n": 0}
    return {
        "version": VERSIONS["C"], "counts_only": True, "window": [c17.CENSUS_START, c17.CENSUS_CUTOFF], "input_stats": band_counts(stats), "counts": band_counts(c),
        "oi_changed_share_of_traded": round(c["oi_changed"] / c["ns_traded"], 6) if c["ns_traded"] else None, "splits": band_counts(splits),
        "events_with_units_having_6_prior": len(ev_with_units),
        "within_event_iqr_of_r": ({"n": len(iqr), "quartiles": [round(float(v), 8) for v in np.quantile(iqr, [0.25, 0.5, 0.75])]} if iqr else None),
        "strata": rep, "planning_se": {"C1_C_pre": se, "recipe": pre.SE_RECIPE, "proxy": pre.PROXIES["C"]},
        "rule": "eligibility, classes, strata and the proxy use captures k-2, k-1 and k only; no k+1 row is read; a member closing or an end date within 3 h of k excludes the unit and is counted",
    }


# =====================================================================================================================================================
# q0403: cost and lag map
# =====================================================================================================================================================

COST_LOAD_FIELDS = ("market_id", "best_bid", "best_ask", "depth_bid_1c", "depth_ask_1c", "depth_bid_5c", "depth_ask_5c", "state")


def cost_lag_map(sweep_dir: Path, snap_dir: Path, trades_dir: Path) -> dict:
    """q0403. Descriptive tables of an upper-bound executable round trip (first sweep of each pass), the monitor receipt lag and the enrichment coverage."""
    stats: Counter = Counter()
    sweeps = list_stamped(sweep_dir, c17.SWEEP_DIR_RE, c17.CENSUS_START, stats)
    caps = list_stamped(snap_dir, c17.CAPTURE_DIR_RE, c17.CENSUS_START, stats)
    static = build_static(caps, stats)
    hists: dict[tuple, pre.Hist] = {}
    cnt: Counter = Counter()
    last_t = -math.inf
    for sdir, t in sweeps:
        first_of_pass = t - last_t >= pre.PASS_GAP_S
        last_t = t
        if not first_of_pass:
            continue
        c17.guard_sweep_dir(sdir)
        cnt["sweeps_used"] += 1
        for mk, bid_s, ask_s, db1, da1, db5, da5, state, _t in iter_dir_cols(sdir, "rows.csv.gz", COST_LOAD_FIELDS, c17.SWEEP_FIELDS, "batch_receipt_utc", stats):
            if state != STATE_TWO_SIDED:
                continue
            bid, ask = c17.num(bid_s), c17.num(ask_s)
            if not t13.two_sided(bid, ask):
                continue
            st = static.get(mk)
            pb, lb = pre.p_band((bid + ask) / 2.0), pre.liq_band(st[2]) if st else None
            cat = (st[6] if st else "no_sidecar") or "none"
            for usd in pre.COST_SIZES_USD:
                key = (cat, "p_out" if pb is None else pre.P_BAND_NAMES[pb], "liq_na" if lb is None else f"liq{lb}", int(usd))
                h = hists.get(key)
                if h is None:
                    h = hists[key] = pre.Hist(pre.COST_HIST_STEP_C, pre.COST_HIST_MAX_C)
                cost = pre.round_trip_cost_c(bid, ask, c17.num(da1), c17.num(da5), c17.num(db1), c17.num(db5), usd, st[7] if st else math.nan)
                cnt[(key, "books")] += 1
                if cost is None:
                    cnt[(key, "not_executable_within_5c")] += 1
                else:
                    h.add(cost)
    cost_tab = {"|".join(map(str, k)): {**h.summary(), "books": cnt[(k, "books")], "not_executable_within_5c": cnt[(k, "not_executable_within_5c")]} for k, h in sorted(hists.items(), key=lambda kv: str(kv[0]))}
    # ---- monitor receipt lag (recv_ts - ts) and enrichment coverage ----
    overall = pre.Hist(pre.LAG_HIST_STEP_S, pre.LAG_HIST_MAX_S)
    by_class: dict[str, pre.Hist] = {}
    by_hour: dict[int, pre.Hist] = {}
    by_day: dict[str, pre.Hist] = {}
    enrich: Counter = Counter()
    cls_cache: dict[str, str] = {}
    n_prints = n_over = 0
    for p in iter_monitor(trades_dir, stats, lag=True):
        n_prints += 1
        day = c17.iso(p["ts"])[:10]
        enrich[f"{day}|prints"] += 1
        enrich[f"{day}|with_market_id"] += bool(p["ctx_market_id"])
        enrich[f"{day}|with_event_id"] += bool(p["ctx_event_id"])
        enrich[f"{day}|with_fee_type"] += bool(p["ctx_fee_type"])
        lag = p["recv_ts"] - p["ts"]
        if not math.isfinite(lag):
            cnt["lag_missing"] += 1
            continue
        k = cls_cache.get(p["condition_id"])
        if k is None:
            k = cls_cache[p["condition_id"]] = lab.classify(p["title"], p["slug"], p["ctx_fee_type"] or "", "", "", p["ctx_category"] or "")[0]
        for tab, key in ((by_class, k), (by_hour, c17.utc_hour(p["ts"])), (by_day, day)):
            h = tab.get(key)
            if h is None:
                h = tab[key] = pre.Hist(pre.LAG_HIST_STEP_S, pre.LAG_HIST_MAX_S)
            h.add(lag)
        overall.add(lag)
        n_over += lag > pre.LAG_THRESHOLDS_S[2]
    lag_doc = {"prints": n_prints, "overall": overall.summary(), "share_gt_300s": overall.share_gt(pre.LAG_THRESHOLDS_S[0]), "share_gt_540s": overall.share_gt(pre.LAG_THRESHOLDS_S[1]),
               "share_gt_7200s": overall.share_gt(pre.LAG_THRESHOLDS_S[2]), "by_class": {k: v.summary() for k, v in sorted(by_class.items())}, "by_utc_hour": {f"h{k:02d}": v.summary() for k, v in sorted(by_hour.items())},
               "by_day": {k: v.summary() for k, v in sorted(by_day.items())}, "polling_note": "the monitor polls about every 5 min, so the lag has a 0-300 s component before any API delay"}
    return {"version": VERSIONS["cost"], "counts_only": True, "window": [c17.CENSUS_START, c17.CENSUS_CUTOFF], "input_stats": band_counts(stats),
            "sweeps": {"in_window": len(sweeps), "used_first_of_pass": cnt["sweeps_used"]}, "recipe": pre.COST_RECIPE, "sizes_usd": list(pre.COST_SIZES_USD),
            "cost_c_per_share": cost_tab, "receipt_lag_s": lag_doc, "enrichment_coverage": band_counts(enrich), "lag_missing": cnt["lag_missing"]}


def declared() -> dict:
    return {"jobs": {"q0400": "pre_census_A", "q0401": "pre_census_B", "q0402": "pre_census_C", "q0403": "cost_lag_map"}, "versions": dict(VERSIONS), "results": dict(RESULT_NAMES),
            "created_at_captures": list(CREATED_AT_CAPTURES),
            "never_read": ["mark or outcome fields", "any capture or sweep after a unit's decision time (the next-pass check reads presence and the two-sided state only)", "wallet fields", "the k+1 capture (C)"],
            "static_rule": "static sidecar attributes are taken from the first worn capture carrying the market (CB13 load_quote_index precedent)",
            "memory": "streaming: one capture, sweep or day file at a time; compact arrays for the B frame (q0401 <= 800 MB)"}
