# ruff: noqa: E501
"""CB15-P: the pair at birth (CH130; docs/research_lab/CREATIVE_BATCH_15.md CB15-P, sections 1.1-1.3, 2.1-2.8, 9-10). Rules part ``P``. Selected on lifetime volume.

On the audited C1 Kalshi-Polymarket pairs where Kalshi opened >= 24 h before Polymarket's FIRST PRINT, does the gap ``g_d`` = Kalshi mid - Polymarket's last print at ``t_d`` = first
print + 10 min predict Polymarket's move over the next 24 h (P1), and does trading toward Kalshi at recorded prints pay after fees (P2)? Stage 1 here: the birth-order census (q0347, no
network, gate GPB), the smoke helpers (q0348), the data fetch (q0349: Gamma metadata, Data API prints from the first transaction aggregated to transactions, Kalshi 1-minute candles,
``prices-history`` AFTER the first print only), the census (q0350: gates GP and GPP with the SE-only proxy) and the screen (q0351: P1, P2 with every binding check).

``part_unready()`` keeps part P UNDECLARED until the Stage-2 birth watcher (q0352) and rep (q0353) exist: the P rules are fixed only when the whole part is written, and no P job runs
before (``verify_rules`` refuses an undeclared part). This module imports ``cb15_common`` and nothing from the E family. No P statistic reads a C1 series VALUE (the C1 reproduction
call is used for the pair list and the series window TIMES only); ``p_end`` is never read; no Gamma outcome, Kalshi ``result`` / ``settlement_value``, side, wallet or hash is stored.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import inspect
import json
import math
import time
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import cb8_common as cm
from . import cb15_common as c15

Refused = cm.Refused
NotNow = cm.NotNow
ApiError = cm.ApiError

MINUTE = 60.0
HOUR = 3600.0
DAY = 86400.0
LABEL_P = "selected on lifetime volume (C1 universe: Polymarket event volume >= 20k, Kalshi >= 5,000 contracts, >= 200 usable steps near resolution); L1 worn set; only P-rep can lead to Stage P"
STAGE2_READY = False  # the Stage-2 watcher (q0352) and rep (q0353) are not written yet: part P stays undeclared
# ---- dates (section 1.2) --------------------------------------------------------------------------------------------------------------------------------
T15_HIST_END = "2026-10-12T00:00:00Z"  # every P historical row is before it (asserted; rows at or after are refused at parse)
T15_P2_START_MIN = "2026-11-04T00:00:00Z"
T15_P2_CAP = "2027-04-30T00:00:00Z"
# ---- population (q0347) ----------------------------------------------------------------------------------------------------------------------------------
C1_EXPECTED = {"pairs": 316, "events": 183}
MATCH_FIELDS = ("k_ticker", "k_series", "k_cat", "k_src", "k_open", "k_close", "p_market_id", "p_event_id", "p_start", "p_token0")  # k_src: the candle endpoint selector (declared)
NEVER_READ_FIELDS = ("p_end", "closed_time", "closedTime")
SPORTS_CAT = "Sports"
ELECTIONS_CAT = "Elections"
KALSHI_FIRST_S = 24 * HOUR
KALSHI_FIRST_ROBUST_S = 72 * HOUR
LEAD_BINS_H = (24, 72, 168, 720)
GPB_MIN = {"pairs": 60, "events": 30}
# ---- clocks and units (sections 2.2, CB15-P) ------------------------------------------------------------------------------------------------------------
T_D_OFFSET_S = 10 * MINUTE
T_D_ROBUST_S = 30 * MINUTE
T_L_OFFSET_S = 7 * DAY
HORIZON_S = 24 * HOUR
PRINT_MAX_AGE_S = 2 * HOUR
TARGET_PRINT_WINDOW_S = (22 * HOUR, 24 * HOUR)  # a print in [t_d + 22 h, t_d + 24 h], else the post-birth prices-history point ("history target")
PH_LAG_S = 600.0  # a fidelity-10 prices-history point is usable from stamp + 600 s
PH_MAX_AGE_S = 2 * HOUR
K_MAX_AGE_S = 60 * MINUTE
K_SPREAD_MAX = 0.10
END_MARGIN_S = 25 * HOUR  # scheduled endDate before t_d + 25 h -> excluded (scheduled, never closedTime)
GAP_MIN = 0.05
ENTRY_WINDOW_S = (60.0, 60 * MINUTE)
ENTRY_ROBUST_S = (3 * MINUTE, 60 * MINUTE)
EXIT_WINDOW_S = (24 * HOUR, 24 * HOUR + 30 * MINUTE)
EXIT_ROBUST_S = (12 * HOUR, 12 * HOUR + 30 * MINUTE)
SEEDED_MID = 0.50
SEEDED_TOL = 0.005
# ---- fetch (q0349) ---------------------------------------------------------------------------------------------------------------------------------------
PRINT_PAGES = 6
PRINT_PAGE_LIMIT = 10000
CANDLE_PRE_S = 6 * HOUR
CANDLE_POST_S = 25 * HOUR
CANDLE_L_PRE_S = 1 * HOUR
TX_STORE_S = 25 * HOUR  # prints kept over [t_birth, t_birth + 25 h] (covers the t_d + 30 min robustness exit) and [t_L - 2 h, t_L + 24 h 30 min]
TX_L_PRE_S = 2 * HOUR
TX_L_POST_S = 24 * HOUR + 30 * MINUTE
PH_PRE_S = 6 * HOUR  # requested before t_birth only to COUNT the points stamped before it (never stored)
P_DATA_MAX_PAIRS = 150
P_DATA_STATUS = "p_data_complete"
P_DATA_PROGRESS = "p_data_in_progress"
DATA_RUN = "h15_birth"
DATA_FILES = {"meta": "meta.csv.gz", "tx": "tx.csv.gz", "kalshi": "kalshi.csv.gz", "prices": "prices.csv.gz", "volume": "volume_guarded.csv.gz", "work": "work.jsonl"}
META_COLUMNS = ["k_ticker", "k_series", "k_cat", "p_market_id", "p_event_id", "k_open", "created", "start", "end_sched", "fee_rate", "yes_index", "t_birth", "t_birth_vwap", "reach",
                "print_pages", "n_tx", "ph_before_birth", "ph_first_seeded", "k_bool_provisional", "k_bool_close_early", "c1_win_start", "c1_win_end", "status"]
TX_COLUMNS = ["p_market_id", "ts", "vwap_yes", "min_yes", "max_yes", "size"]
K_COLUMNS = ["k_ticker", "end_ts", "bid", "ask"]
PH_COLUMNS = ["p_market_id", "t", "p"]
VOL_COLUMNS = ["p_market_id", "volume_lifetime"]
BIRTH_FRAME_NAME = "birth_frame.csv.gz"
BIRTH_FRAME_COLUMNS = ["k_ticker", "k_series", "k_cat", "k_src", "p_market_id", "p_event_id", "k_open", "p_start", "lead_h", "c1_win_start", "c1_win_end"]
# ---- tests, gates (sections 2.3-2.6) --------------------------------------------------------------------------------------------------------------------
P1_FLOOR = 0.30
P2_FLOOR = 0.01
P1_MIN = {"pairs": 60, "events": 30}
P2_MIN = {"pairs": 40, "events": 25}
TERCILE_MIN = 15
BIRTH_CONTRAST_P = 0.05
OPENING_CONTROL_P = 0.05
OPENING_CONTROL_SHARE = 0.5
STRATUM_MIN = 20
GPP_P1_MAX = 0.60
GPP_P2_MAX = 0.02
NOT_TESTABLE_POP = "not testable (population)"
NOT_TESTABLE_SOURCE = "not testable (source)"
NOT_TESTABLE_AVAIL = "not testable (availability)"
NOT_RUN_POWER = "not run (power)"
UNKNOWN = "unknown"
# ---- smoke (q0348) ---------------------------------------------------------------------------------------------------------------------------------------
SMOKE_NEEDS = ("guards_fixture_P", "p_matches_reader", "p_hist_end_refusal", "p_birth_from_prints", "p_c1_reproduction", "p_first_tx_reach", "p_kalshi_candles", "p_kalshi_min_created")
SMOKE_MAX_REQUESTS = 30
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
KALSHI_FORBIDDEN = ("result", "settlement_value", "expiration_value", "settlement_timer_seconds")


def part_unready() -> str | None:
    if not STAGE2_READY:
        return "CB15-P Stage-2 watcher (q0352) and rep (q0353) not implemented yet: part P stays undeclared until the whole part is written (no P job runs before)"
    return None


def ep(s: str) -> float:
    return c15.ep(s)


# =====================================================================================================================================================
# Guards: the matches reader, Kalshi parse, history-end refusal
# =====================================================================================================================================================


def refuse_hist_row(t: float, what: str = "row") -> None:
    """Every P historical row is before ``T15_HIST_END`` (2026-10-12T00:00Z): a row at or after it is refused (never stored, never used)."""
    if math.isfinite(t) and t >= ep(T15_HIST_END):
        raise Refused(f"P {what} at {datetime.fromtimestamp(t, UTC):%Y-%m-%dT%H:%MZ} is at or after T15_hist_end {T15_HIST_END}; refusing")


def read_matches(path: Path) -> dict[str, dict]:
    """``matches.json`` through a field-restricted reader: ``MATCH_FIELDS`` only (``p_end`` and every other field are dropped at read). Keyed by ``k_ticker``."""
    p = c15.refuse_path(Path(path), allow=("cross_venue",))
    if p.name != "matches.json":
        raise Refused(f"{p}: the C1 field reader opens matches.json only")
    rows = json.loads(p.read_text())
    out = {}
    for r in rows:
        if isinstance(r, dict) and r.get("k_ticker"):
            out[str(r["k_ticker"])] = {k: r.get(k) for k in MATCH_FIELDS}
    return out


def strip_kalshi(m: dict) -> dict:
    """Kalshi parse guard: ``result``, ``settlement_value`` and the other settlement fields are discarded at parse."""
    return {k: v for k, v in c15.strip_forbidden(m).items() if k not in KALSHI_FORBIDDEN}


def c1_frame(root: Path, *, loader: Callable[[Path], dict] | None = None) -> tuple[list[dict], dict]:
    """The C1 reproduction call (``cb12_x.load_c1`` with its pinned inputs and study source; asserts 316 pairs and 183 events, as CB5-K and CB12-X). Only the pair id (Kalshi ticker),
    the event, the category and the series window TIMES leave this function; no series value."""
    if loader is None:
        from . import cb12_x  # noqa: PLC0415

        def loader(r: Path) -> dict:
            return cb12_x.load_c1(r, expected=cb12_x.C1_EXPECTED)

    res = loader(Path(root))
    pairs = [{"k_ticker": str(p.pair_id), "event": str(p.event), "cat": str(p.cat), "win_start": float(np.min(p.t)) if len(p.t) else math.nan,
              "win_end": float(np.max(p.t)) if len(p.t) else math.nan} for p in res["pairs"]]
    got = {"pairs": len(pairs), "events": len({p["event"] for p in pairs})}
    if got != C1_EXPECTED:
        raise Refused(f"C1 reproduction: {got} != {C1_EXPECTED}")
    rep = {k: v for k, v in (res.get("report") or {}).items() if k in ("pairs", "events", "steps", "audit_rule_drops", "matched_rows", "inputs_sha256", "source_sha256")}
    return pairs, rep


def c1_loader_sha() -> str:
    """sha256 of the C1 reproduction call's source (``cb12_x.load_c1``): part of the P declaration, so a change to it changes the P rules sha."""
    from . import cb12_x  # noqa: PLC0415

    return hashlib.sha256(inspect.getsource(cb12_x.load_c1).encode()).hexdigest()


# =====================================================================================================================================================
# q0347: birth-order census (no network) and gate GPB
# =====================================================================================================================================================


def lead_bin(lead_s: float) -> str:
    if not math.isfinite(lead_s):
        return "unknown"
    h = lead_s / HOUR
    for b in LEAD_BINS_H[::-1]:
        if h >= b:
            return f">={b}h"
    return "<24h" if h >= 0 else "polymarket_first"


def birth_census(pairs: list[dict], matches: dict[str, dict], ksrc: dict | None) -> tuple[list[list], dict]:
    """q0347, counts only: non-sports C1 pairs, key drops by source (the P rule: a key whose only source is C1 is kept), the Kalshi-first PROXY ``p_start - k_open >= 24 h`` by lead bin
    and category, and gate GPB (>= 60 pairs in >= 30 events). Returns (birth-frame rows of the proxy pairs, report). ``p_end`` is never read."""
    rows, by_cat, by_bin, drops = [], Counter(), Counter(), Counter()
    n_sports, n_nomatch, kept_ev, no_drop_pairs, no_drop_ev = 0, 0, set(), 0, set()
    for p in pairs:
        m = matches.get(p["k_ticker"])
        if m is None:
            n_nomatch += 1
            continue
        if not c15.CB15_SPORTS_IN_PRIMARY and str(m.get("k_cat")) == SPORTS_CAT:
            n_sports += 1
            continue
        lead = c15.parse_iso(m.get("p_start")) - c15.parse_iso(m.get("k_open"))
        proxy = bool(math.isfinite(lead) and lead >= KALSHI_FIRST_S)
        if proxy:
            no_drop_pairs += 1
            no_drop_ev.add(str(m.get("p_event_id")))
        why = c15.drop_reason({"market_id": m.get("p_market_id"), "event_id": m.get("p_event_id")}, ksrc, "P") if ksrc else ""
        if why:
            drops[why.split(":", 1)[1]] += 1
            continue
        by_bin[lead_bin(lead)] += 1
        if not proxy:
            continue
        by_cat[str(m.get("k_cat"))] += 1
        kept_ev.add(str(m.get("p_event_id")))
        rows.append([p["k_ticker"], m.get("k_series"), m.get("k_cat"), m.get("k_src"), m.get("p_market_id"), m.get("p_event_id"), m.get("k_open"), m.get("p_start"), round(lead / HOUR, 3),
                     p["win_start"], p["win_end"]])
    gpb = bool(len(rows) >= GPB_MIN["pairs"] and len(kept_ev) >= GPB_MIN["events"])
    rep = {"counts_only": True, "c1_pairs": len(pairs), "sports_excluded": n_sports, "no_matches_row": n_nomatch, "key_drops_by_source": dict(drops),
           "no_drop_counterfactual": {"pairs": no_drop_pairs, "events": len(no_drop_ev)}, "lead_bins": dict(by_bin), "kalshi_first_proxy": {"pairs": len(rows), "events": len(kept_ev),
           "by_category": dict(by_cat)}, "gpb": {"min": GPB_MIN, "pass": gpb}, "label": LABEL_P}
    return rows, rep


# =====================================================================================================================================================
# Prints, prices-history, Kalshi candles: parse and point-in-time rules
# =====================================================================================================================================================


def transactions(prints: Iterable[dict], yes_index: int) -> list[dict]:
    """Data API prints -> one row per transaction (hash discarded in memory): time (the latest fill), YES-terms VWAP, min and max YES-terms fill price, total size. Side, wallet, name
    and hash are never read into the result."""
    groups: dict[str, list[tuple[float, float, float]]] = {}
    for i, x in enumerate(prints):
        if not isinstance(x, dict):
            continue
        ts, px, sz = c15.num(x.get("timestamp")), c15.num(x.get("price")), c15.num(x.get("size"))
        try:
            oi = int(x.get("outcomeIndex"))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(ts) and math.isfinite(px) and math.isfinite(sz)) or sz <= 0:
            continue
        y = px if oi == int(yes_index) else 1.0 - px
        groups.setdefault(str(x.get("transactionHash") or f"nohash:{i}"), []).append((ts, y, sz))
    out = []
    for fills in groups.values():
        size = sum(f[2] for f in fills)
        out.append({"ts": max(f[0] for f in fills), "vwap_yes": sum(f[1] * f[2] for f in fills) / size, "min_yes": min(f[1] for f in fills), "max_yes": max(f[1] for f in fills), "size": size})
    out.sort(key=lambda r: r["ts"])
    return out


def fetch_prints_from_birth(lim, cid: str, *, pages: int = PRINT_PAGES, limit: int = PRINT_PAGE_LIMIT, url: str | None = None) -> tuple[list[dict], dict]:
    """Newest-first ``/trades`` pages (offset paging, at most ``pages``) until a page is not full: only then is the market's FIRST transaction reached (``reach = complete``). A deep
    offset refused by the API or the page cap on a full page leaves the birth uncovered (``reach = uncovered``; "no birth print (uncovered)", counted)."""
    from . import history_backfill as hb  # noqa: PLC0415

    rows: list[dict] = []
    info = {"pages": 0, "reach": "uncovered"}
    for page in range(pages):
        st, data = lim.get(url or hb.DATA_TRADES, {"market": cid, "limit": limit, "offset": page * limit})
        if st == 400 and page > 0:
            break
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"trades status {st}")
        info["pages"] += 1
        rows.extend({k: x.get(k) for k in ("timestamp", "price", "size", "outcomeIndex", "transactionHash")} for x in data if isinstance(x, dict))  # in memory only; the hash is dropped by ``transactions``
        if len(data) < limit:
            info["reach"] = "complete"
            break
    return rows, info


def birth_of(txs: list[dict], reach: str) -> tuple[float, float]:
    """(``t_birth``, VWAP of the first transaction): the time of the market's FIRST Data API transaction, only when the prints reach it; else (nan, nan) = "no birth print"."""
    if reach != "complete" or not txs:
        return math.nan, math.nan
    first = min(txs, key=lambda r: r["ts"])
    return float(first["ts"]), float(first["vwap_yes"])


def p_at(txs: list[dict], t: float, max_age: float = PRINT_MAX_AGE_S) -> float:
    """The YES-terms VWAP of the last transaction at or before ``t`` with age <= 2 h; NaN = "no print"."""
    best = None
    for r in txs:
        if r["ts"] <= t:
            best = r
        else:
            break
    return float(best["vwap_yes"]) if best is not None and t - best["ts"] <= max_age else math.nan


def print_in(txs: list[dict], lo: float, hi: float) -> list[dict]:
    return [r for r in txs if lo <= r["ts"] <= hi]


def ph_at(points: list[tuple[float, float]], t: float, t_birth: float, max_age: float = PH_MAX_AGE_S) -> float:
    """The last ``prices-history`` point stamped AFTER ``t_birth`` and usable by ``t`` (stamp + 600 s <= t), age <= 2 h; NaN otherwise. Points at or before ``t_birth`` are never used."""
    best = math.nan
    for s, p in points:
        if s <= t_birth:
            continue
        if s + PH_LAG_S <= t and t - s <= max_age + PH_LAG_S:
            best = p
    return float(best)


def seeded_flags(points_all: list[tuple[float, float]], t_birth: float) -> tuple[int, bool]:
    """(number of points stamped at or before ``t_birth``, whether the first point overall is 0.50 +- 0.005): the seeded-history disclosure. Counted only, never used."""
    before = sum(1 for s, _ in points_all if math.isfinite(t_birth) and s <= t_birth)
    first = min(points_all, key=lambda x: x[0])[1] if points_all else math.nan
    return before, bool(math.isfinite(first) and abs(first - SEEDED_MID) <= SEEDED_TOL)


def k_mid_at(candles: np.ndarray, t: float) -> float:
    """Kalshi mid at ``t``: (bid close + ask close) / 2 of the last usable 1-minute bar (``end_ts <= t``) with both sides, age <= 60 min and spread <= 10c; NaN = "no Kalshi quote"."""
    if candles is None or not len(candles):
        return math.nan
    a = np.asarray(candles, float)
    m = (a[:, 0] <= t) & np.isfinite(a[:, 1]) & np.isfinite(a[:, 2])
    if not m.any():
        return math.nan
    row = a[np.flatnonzero(m)[-1]]
    if t - row[0] > K_MAX_AGE_S or row[2] - row[1] > K_SPREAD_MAX + 1e-12:
        return math.nan
    return float((row[1] + row[2]) / 2.0)


# =====================================================================================================================================================
# Units (q0350 features; q0351 targets)
# =====================================================================================================================================================


def unit_features(meta: dict, txs: list[dict], candles: np.ndarray, *, td_off: float = T_D_OFFSET_S, kalshi_first_s: float = KALSHI_FIRST_S) -> dict:
    """Features at ``t_d`` only (what the census may read): the binding Kalshi-first rule (``t_birth - k_open >= 24 h``; exactly 24 h counts), the scheduled-end exclusion, ``p_d``
    (the last print at or before ``t_d``; the first print itself if none since), ``k_d``, ``g_d`` and the label."""
    tb = c15.num(meta.get("t_birth"))
    if not math.isfinite(tb):
        return {"label": "no birth print (uncovered)"}
    ko = c15.num(meta.get("k_open"))
    if not (math.isfinite(ko) and tb - ko >= kalshi_first_s):
        return {"label": "polymarket first (binding)", "t_birth": tb}
    td = tb + td_off
    end = c15.num(meta.get("end_sched"))
    if math.isfinite(end) and end < td + END_MARGIN_S:
        return {"label": "ends early (scheduled)", "t_birth": tb}
    if td + EXIT_WINDOW_S[1] >= ep(T15_HIST_END):
        return {"label": "after T15_hist_end", "t_birth": tb}
    pd = p_at(txs, td, max_age=math.inf)
    kd = k_mid_at(candles, td)
    if not math.isfinite(kd):
        return {"label": "no Kalshi quote", "t_birth": tb, "p_d": pd}
    return {"label": "ok", "t_birth": tb, "t_d": td, "p_d": pd, "k_d": kd, "g_d": kd - pd, "p_birth": c15.num(meta.get("t_birth_vwap"))}


def unit_target(f: dict, txs: list[dict], ph: list[tuple[float, float]]) -> dict:
    """The 24-h target from ``t_d`` (screen only): a print in ``[t_d + 22 h, t_d + 24 h]`` -> ``p(t_d + 24 h)``; else the usable post-birth ``prices-history`` point at ``t_d + 24 h``
    ("history target"); neither -> "no target"."""
    t = f["t_d"] + HORIZON_S
    if print_in(txs, f["t_d"] + TARGET_PRINT_WINDOW_S[0], f["t_d"] + TARGET_PRINT_WINDOW_S[1]):
        return {"delta": p_at(txs, t) - f["p_d"], "history_target": False}
    v = ph_at(ph, t, f["t_birth"])
    if math.isfinite(v):
        return {"delta": v - f["p_d"], "history_target": True}
    return {"delta": math.nan, "history_target": False, "label": "no target"}


def later_unit(f: dict, meta: dict, txs: list[dict], candles: np.ndarray, ph: list[tuple[float, float]]) -> dict:
    """The later-life comparator at ``t_L = t_d + 7 d`` (if the scheduled end is after ``t_L + 25 h`` and ``t_L + 24 h 30 min`` is before T15_hist_end): ``g_L``, ``Delta_L``."""
    tl = f["t_d"] + T_L_OFFSET_S
    end = c15.num(meta.get("end_sched"))
    if (math.isfinite(end) and end <= tl + END_MARGIN_S) or tl + EXIT_WINDOW_S[1] >= ep(T15_HIST_END):
        return {"ok": False}
    pl, kl = p_at(txs, tl), k_mid_at(candles, tl)
    if not (math.isfinite(pl) and math.isfinite(kl)):
        return {"ok": False}
    g = {"t_d": tl, "p_d": pl, "t_birth": f["t_birth"]}
    tg = unit_target(g, txs, ph)
    return {"ok": bool(math.isfinite(tg["delta"])), "t_L": tl, "g_L": kl - pl, "delta_L": tg["delta"], "p_L": pl}


def p2_net(f: dict, txs: list[dict], rate: float, *, entry_win: tuple[float, float] = ENTRY_WINDOW_S, exit_win: tuple[float, float] = EXIT_WINDOW_S, extra_per_side: float = 0.0,
           g: float | None = None) -> dict:
    """P2 at recorded prints: toward Kalshi (YES if g >= 5c, NO if g <= -5c); entry at the taker-adverse print in ``[t_d + 60 s, t_d + 60 min]`` (max YES-terms price buying YES; min
    buying NO, paying 1 - price); exit at the adverse print in ``[t_d + 24 h, t_d + 24 h 30 min]`` (min long YES; max long NO); none -> the last print after entry before the window end
    ("stale exit"); none after entry -> "no exit"; fee ``r e (1 - e) + r x (1 - x)``; size min(100, entry print size)."""
    gg = f["g_d"] if g is None else g
    if abs(gg) < GAP_MIN:
        return {"status": "below gap"}
    side = 1 if gg >= GAP_MIN else -1
    td = f["t_d"]
    ent = print_in(txs, td + entry_win[0], td + entry_win[1])
    if not ent:
        return {"status": "no entry print", "side": side}
    er = max(ent, key=lambda r: r["max_yes"]) if side == 1 else min(ent, key=lambda r: r["min_yes"])
    e = er["max_yes"] if side == 1 else 1.0 - er["min_yes"]
    ex = [r for r in print_in(txs, td + exit_win[0], td + exit_win[1]) if r["ts"] > er["ts"]]
    stale = False
    if ex:
        xr = min(ex, key=lambda r: r["min_yes"]) if side == 1 else max(ex, key=lambda r: r["max_yes"])
        x = xr["min_yes"] if side == 1 else 1.0 - xr["max_yes"]
    else:
        later = [r for r in txs if er["ts"] < r["ts"] < td + exit_win[1]]
        if not later:
            return {"status": "no exit", "side": side, "entry": e}
        xr = later[-1]
        x = xr["vwap_yes"] if side == 1 else 1.0 - xr["vwap_yes"]
        stale = True
    return {"status": "ok", "side": side, "entry": e, "exit": x, "stale": stale, "size": min(c15.PAPER_SIZE, er["size"]),
            "net": c15.round_trip_net(e, x, rate, extra_per_side)}


# =====================================================================================================================================================
# Fetch (q0349): resumable, budgeted, one pair at a time
# =====================================================================================================================================================


def gamma_meta(m: dict) -> dict:
    """Whitelisted Gamma market fields (outcome fields discarded at parse): ids, ``createdAt``, ``startDate``, scheduled ``endDate``, fee rate, YES index, condition id, tokens and the
    lifetime ``volume`` (stored apart, read only by the screen's tercile check)."""
    m = c15.strip_forbidden(m)
    labels = [str(x).strip().lower() for x in c15.c12.listish(m.get("outcomes"))]
    fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    vol = next((c15.num(m.get(k)) for k in ("volumeNum", "volume") if math.isfinite(c15.num(m.get(k)))), math.nan)
    return {"created": c15.parse_iso(m.get("createdAt")), "start": c15.parse_iso(m.get("startDate")), "end_sched": c15.parse_iso(m.get("endDate")), "fee_rate": c15.num(fs.get("rate")),
            "yes_index": labels.index("yes") if "yes" in labels else 0, "condition_id": str(m.get("conditionId") or ""), "tokens": [str(x) for x in c15.c12.listish(m.get("clobTokenIds"))],
            "volume": vol}


def fetch_pair(lim, klim, row: dict, gm: dict) -> dict:
    """One pair of q0349 (network): prints from the first transaction, Kalshi candles over ``[t_birth - 6 h, t_d + 25 h]`` and ``[t_L - 1 h, t_L + 25 h]``, ``prices-history`` after
    ``t_birth`` (points before it counted only). Rows at or after T15_hist_end are dropped at parse (never stored)."""
    from . import cross_venue as cv  # noqa: PLC0415
    from . import history_backfill as hb  # noqa: PLC0415

    hist_end = ep(T15_HIST_END)
    prints, info = fetch_prints_from_birth(lim, gm["condition_id"])
    txs = [t for t in transactions(prints, gm["yes_index"]) if t["ts"] < hist_end]
    tb, tbv = birth_of(txs, info["reach"])
    out = {"meta": {"t_birth": tb, "t_birth_vwap": tbv, "reach": info["reach"], "print_pages": info["pages"], "n_tx": len(txs)}, "tx": [], "kalshi": [], "prices": []}
    if not math.isfinite(tb):
        return out
    td = tb + T_D_OFFSET_S
    tl = td + T_L_OFFSET_S
    keep = [(tb, tb + TX_STORE_S), (tl - TX_L_PRE_S, tl + TX_L_POST_S)]
    out["tx"] = [t for t in txs if any(lo <= t["ts"] <= hi for lo, hi in keep)]
    hist = str(row.get("k_src") or "").startswith("/historical")
    kc = []
    for lo, hi in ((tb - CANDLE_PRE_S, td + CANDLE_POST_S), (tl - CANDLE_L_PRE_S, tl + CANDLE_POST_S)):
        hi = min(hi, hist_end - 1)
        if hi <= lo:
            continue
        c, _ = cv.fetch_k_candles(klim, row["k_ticker"], row["k_series"], int(lo), int(hi), hist)
        kc += [[float(r[0]), float(r[1]), float(r[2])] for r in c if r[0] < hist_end]
    out["kalshi"] = sorted({tuple(r) for r in kc})
    tok = gm["tokens"][gm["yes_index"]] if gm["tokens"] else ""
    pts_all: list[tuple[float, float]] = []
    for lo, hi in ((tb - PH_PRE_S, td + CANDLE_POST_S), (tl - CANDLE_L_PRE_S, tl + CANDLE_POST_S)):
        hi = min(hi, hist_end - 1)
        if hi <= lo or not tok:
            continue
        pts, _ = hb.fetch_prices(lim, tok, int(lo), int(hi))
        pts_all += [(float(s), float(p)) for s, p in pts if s < hist_end]
    before, seeded = seeded_flags(pts_all, tb)
    out["meta"].update(ph_before_birth=before, ph_first_seeded=seeded)
    out["prices"] = sorted({(s, p) for s, p in pts_all if s > tb})
    return out


def read_frame(path: Path) -> list[dict]:
    return list(c15.read_csv_gz(Path(path)))


def p_data(hist_root: Path, lim, klim, *, frame_path: Path, kalshi_bools: dict[str, dict] | None = None, budget_s: float | None = None, clock=time.time,
           gamma_lookup: Callable[[list[str]], dict[str, dict]] | None = None) -> dict:
    """q0349: per Kalshi-first proxy pair (``birth_frame.csv.gz`` of q0347, at most 150), resumable (``work.jsonl`` holds one line per finished pair; a torn tail line is re-fetched),
    budgeted (``in_progress`` with exit 0 when the budget is spent). On completion writes meta / tx / kalshi / prices / volume files and the manifest with ``p_data_complete``."""
    out_dir = c15.require_output_root(Path(hist_root) / DATA_RUN)
    out_dir.mkdir(parents=True, exist_ok=True)
    done = c15.manifest_complete(out_dir, (P_DATA_STATUS,))
    if done:
        return {"status": P_DATA_STATUS, "complete": True, "already_complete": True}
    frame = read_frame(frame_path)
    if len(frame) > P_DATA_MAX_PAIRS:
        raise Refused(f"{len(frame)} proxy pairs > the declared {P_DATA_MAX_PAIRS}")
    work = out_dir / DATA_FILES["work"]
    finished = {r["k_ticker"]: r for r in c15.jsonl_iter(work)}
    todo = [r for r in frame if r["k_ticker"] not in finished]
    t0 = clock()
    if todo:
        if gamma_lookup is None:
            def gamma_lookup(ids: list[str]) -> dict[str, dict]:
                got: dict[str, dict] = {}
                for i in range(0, len(ids), c15.LOOKUP_PER_REQUEST):
                    chunk = ids[i:i + c15.LOOKUP_PER_REQUEST]
                    for closed in ("true", None):
                        miss = [x for x in chunk if x not in got]
                        if not miss:
                            break
                        params = {"id": miss, "limit": len(miss)} | ({"closed": closed} if closed else {})
                        st, data = lim.get(c15.GAMMA_MARKETS, params)
                        if st != 200 or not isinstance(data, list):
                            raise ApiError(f"gamma markets status {st}")
                        got.update({str(m["id"]): m for m in data if isinstance(m, dict) and str(m.get("id")) in miss})
                return got
        gms = gamma_lookup([r["p_market_id"] for r in todo])
    for r in todo:
        if budget_s is not None and clock() - t0 > budget_s:
            return {"status": P_DATA_PROGRESS, "complete": False, "done": len(finished), "todo": len(frame) - len(finished)}
        raw = gms.get(str(r["p_market_id"]))
        if raw is None:
            rec = {"k_ticker": r["k_ticker"], "status": "no gamma metadata"}
        else:
            gm = gamma_meta(raw)
            got = fetch_pair(lim, klim, r, gm)
            kb = (kalshi_bools or {}).get(r["k_ticker"], {})
            rec = {"k_ticker": r["k_ticker"], "status": "ok", "gm": {k: v for k, v in gm.items() if k != "tokens"}, "row": r, **got,
                   "k_bools": {"is_provisional": kb.get("is_provisional"), "can_close_early": kb.get("can_close_early")}}
        c15.jsonl_append(work, rec)
        finished[r["k_ticker"]] = rec
    files = write_data_files(out_dir, frame, finished)
    c15.write_dir_manifest(out_dir, P_DATA_STATUS, files, {"n_pairs": len(frame), "labels": dict(Counter(str(v.get("meta", {}).get("reach") or v.get("status")) for v in finished.values()))})
    return {"status": P_DATA_STATUS, "complete": True, "n_pairs": len(frame)}


def write_data_files(out_dir: Path, frame: list[dict], finished: dict[str, dict]) -> list[Path]:
    meta_rows, tx_rows, k_rows, ph_rows, vol_rows = [], [], [], [], []
    for r in frame:
        rec = finished.get(r["k_ticker"]) or {}
        gm, m, kb = rec.get("gm") or {}, rec.get("meta") or {}, rec.get("k_bools") or {}
        meta_rows.append([r["k_ticker"], r["k_series"], r["k_cat"], r["p_market_id"], r["p_event_id"], c15.parse_iso(r["k_open"]), gm.get("created"), gm.get("start"), gm.get("end_sched"),
                          gm.get("fee_rate"), gm.get("yes_index"), m.get("t_birth"), m.get("t_birth_vwap"), m.get("reach"), m.get("print_pages"), m.get("n_tx"), m.get("ph_before_birth"),
                          m.get("ph_first_seeded"), kb.get("is_provisional"), kb.get("can_close_early"), r.get("c1_win_start"), r.get("c1_win_end"), rec.get("status", "missing")])
        tx_rows += [[r["p_market_id"], t["ts"], t["vwap_yes"], t["min_yes"], t["max_yes"], t["size"]] for t in rec.get("tx") or []]
        k_rows += [[r["k_ticker"], *k] for k in rec.get("kalshi") or []]
        ph_rows += [[r["p_market_id"], s, p] for s, p in rec.get("prices") or []]
        vol_rows.append([r["p_market_id"], gm.get("volume")])
    paths = []
    for key, cols, rows in (("meta", META_COLUMNS, meta_rows), ("tx", TX_COLUMNS, tx_rows), ("kalshi", K_COLUMNS, k_rows), ("prices", PH_COLUMNS, ph_rows), ("volume", VOL_COLUMNS, vol_rows)):
        paths.append(c15.write_gz_csv(Path(out_dir) / DATA_FILES[key], cols, rows))
    return paths


# =====================================================================================================================================================
# Loading the fetched data (field-restricted; volume guarded)
# =====================================================================================================================================================


def open_volume(data_dir: Path, caller: str) -> dict[str, float]:
    """Lifetime volume is opened ONLY by the screen's tercile check (``caller == 'screen-P'``)."""
    if caller != "screen-P":
        raise Refused(f"lifetime volume is opened only by the screen's tercile check, not by {caller!r}")
    return {r["p_market_id"]: c15.num(r["volume_lifetime"]) for r in c15.read_csv_gz(Path(data_dir) / DATA_FILES["volume"])}


def load_data(data_dir: Path) -> dict:
    d = Path(data_dir)
    meta = {r["k_ticker"]: r for r in c15.read_csv_gz(d / DATA_FILES["meta"])}
    tx: dict[str, list[dict]] = {}
    for r in c15.read_csv_gz(d / DATA_FILES["tx"]):
        tx.setdefault(r["p_market_id"], []).append({"ts": float(r["ts"]), "vwap_yes": float(r["vwap_yes"]), "min_yes": float(r["min_yes"]), "max_yes": float(r["max_yes"]), "size": float(r["size"])})
    for v in tx.values():
        v.sort(key=lambda x: x["ts"])
    kc: dict[str, list[list[float]]] = {}
    for r in c15.read_csv_gz(d / DATA_FILES["kalshi"]):
        kc.setdefault(r["k_ticker"], []).append([float(r["end_ts"]), c15.num(r["bid"]), c15.num(r["ask"])])
    ph: dict[str, list[tuple[float, float]]] = {}
    for r in c15.read_csv_gz(d / DATA_FILES["prices"]):
        ph.setdefault(r["p_market_id"], []).append((float(r["t"]), float(r["p"])))
    for k, v in list(tx.items()) + list(ph.items()):
        refuse_hist_row(max((x["ts"] if isinstance(x, dict) else x[0]) for x in v), f"stored row of {k}")
    return {"meta": meta, "tx": tx, "kc": {k: np.array(sorted(v), float) for k, v in kc.items()}, "ph": {k: sorted(v) for k, v in ph.items()}}


def features_table(data: dict, *, td_off: float = T_D_OFFSET_S, kalshi_first_s: float = KALSHI_FIRST_S) -> list[dict]:
    out = []
    for kt, m in sorted(data["meta"].items()):
        f = unit_features(m, data["tx"].get(m["p_market_id"], []), data["kc"].get(kt), td_off=td_off, kalshi_first_s=kalshi_first_s)
        out.append({"k_ticker": kt, "p_market_id": m["p_market_id"], "event": m["p_event_id"], "cat": m["k_cat"], "fee_rate": c15.num(m.get("fee_rate")), "meta": m, **f})
    return out


# =====================================================================================================================================================
# Census (q0350): gates GP and GPP (SE-only proxy)
# =====================================================================================================================================================


def event_weights(events: list[str]) -> np.ndarray:
    """Each event weight 1, split over its pairs."""
    c = Counter(events)
    return np.array([1.0 / c[e] for e in events], float)


def weeks_of(ts: Iterable[float]) -> list[str]:
    return [c15.iso_week_of(t) for t in ts]


def se_only_proxy(feats: list[dict], data: dict) -> dict:
    """GPP (SE only; unit-tested that no estimate leaves it): P1 - the clustered SE (max over the event and birth-week ways) of the event-weighted slope of ``Delta_L`` on ``g_d``;
    P2 - the clustered SE of the event-weighted mean net of the P2 rule applied at ``t_L`` (toward Kalshi when ``|g_L| >= 5c``). Only SEs and counts are returned."""
    ys, xs, ev, wk, nets, nev, nwk = [], [], [], [], [], [], []
    for f in feats:
        if f.get("label") != "ok":
            continue
        kt, mid = f["k_ticker"], f["p_market_id"]
        txs, kc, ph = data["tx"].get(mid, []), data["kc"].get(kt), data["ph"].get(mid, [])
        lu = later_unit(f, f["meta"], txs, kc, ph)
        if not lu.get("ok"):
            continue
        ys.append(lu["delta_L"])
        xs.append(f["g_d"])
        ev.append(f["event"])
        wk.append(c15.iso_week_of(f["t_birth"]))
        r = p2_net({"t_d": lu["t_L"], "g_d": lu["g_L"]}, txs, c15.taker_rate(f["fee_rate"]))
        if r["status"] == "ok":
            nets.append(r["net"])
            nev.append(f["event"])
            nwk.append(c15.iso_week_of(f["t_birth"]))
    out = {"p1": {"n": len(ys), "se": math.nan}, "p2": {"n": len(nets), "se": math.nan}}
    if len(ys) >= 3:
        w = event_weights(ev)
        pv, _b = c15.wls_coef_pseudo(np.array(ys), np.array(xs), w, 0)
        out["p1"]["se"] = c15.max_se_over_ways(pv, {"event": np.array(ev), "week": np.array(wk)})
    if len(nets) >= 2:
        w = event_weights(nev)
        v = np.array(nets) * w * len(w) / w.sum()
        out["p2"]["se"] = c15.max_se_over_ways(v, {"event": np.array(nev), "week": np.array(nwk)})
    return out


def census_p(data: dict) -> dict:
    """q0350, counts only: binding Kalshi-first, rule booleans, labels, seeded-history shares, the ``g_d`` distribution (features at ``t_d``), the ``|g_d| >= 5c`` count, gates GP
    (P1 >= 60 pairs in >= 30 events; P2 >= 40 pairs with |g_d| >= 5c in >= 25 events) and GPP (MDE_P1 = 3.16 x 1.2 x SE <= 0.60; MDE_P2 <= 2c). No slope, Delta or net."""
    feats = features_table(data)
    ok = [f for f in feats if f.get("label") == "ok"]
    big = [f for f in ok if abs(f["g_d"]) >= GAP_MIN]
    meta = list(data["meta"].values())
    seeded_any = [m for m in meta if c15.num(m.get("ph_before_birth")) > 0]
    seeded_mid = [m for m in meta if str(m.get("ph_first_seeded")) in ("True", "1", "true")]
    gp1 = bool(len(ok) >= P1_MIN["pairs"] and len({f["event"] for f in ok}) >= P1_MIN["events"])
    gp2 = bool(len(big) >= P2_MIN["pairs"] and len({f["event"] for f in big}) >= P2_MIN["events"])
    se = se_only_proxy(feats, data)
    mde1, mde2 = c15.mde(se["p1"]["se"]), c15.mde(se["p2"]["se"])
    g = np.array([f["g_d"] for f in ok], float)
    return {"counts_only": True, "label": LABEL_P, "pairs": len(meta), "labels": dict(Counter(f.get("label") for f in feats)),
            "reach": dict(Counter(str(m.get("reach")) for m in meta)), "rule_booleans": {"kalshi_present": sum(1 for m in meta if m.get("k_bool_provisional") not in ("", None)),
                                                                                         "polymarket": "no comparable Gamma booleans; check not applicable (reported)"},
            "seeded_history": {"share_points_before_birth": len(seeded_any) / len(meta) if meta else math.nan, "share_first_point_050": len(seeded_mid) / len(meta) if meta else math.nan},
            "g_d": {"n": len(g), "abs_ge_5c": len(big), "quantiles_abs": [float(np.quantile(np.abs(g), q)) for q in (0.25, 0.5, 0.75)] if len(g) else []},
            "gp": {"P1": {"pairs": len(ok), "events": len({f["event"] for f in ok}), "min": P1_MIN, "pass": gp1}, "P2": {"pairs": len(big), "events": len({f["event"] for f in big}), "min": P2_MIN, "pass": gp2}},
            "gpp": {"P1": {"se": se["p1"]["se"], "n": se["p1"]["n"], "mde": mde1, "max": GPP_P1_MAX, "pass": bool(math.isfinite(mde1) and mde1 <= GPP_P1_MAX)},
                    "P2": {"se": se["p2"]["se"], "n": se["p2"]["n"], "mde": mde2, "max": GPP_P2_MAX, "pass": bool(math.isfinite(mde2) and mde2 <= GPP_P2_MAX)}}}


# =====================================================================================================================================================
# Screen (q0351): P1, P2
# =====================================================================================================================================================


def nt(label: str, **extra) -> dict:
    return {"testable": False, "p": 1.0, "advance": False, "verdict": label, "est": None, "n": 0, **extra}


def slope_test(y, x, ev, wk, *, controls=None) -> dict:
    """Event-weighted OLS slope (intercept) of ``y`` on ``x`` (plus ``controls``); one-sided p > 0 as the max over the event and birth-week ways (cluster pseudo-values)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    X = x[:, None] if controls is None else np.column_stack([x, *[np.asarray(c, float) for c in controls]])
    w = event_weights(list(ev))
    pv, b = c15.wls_coef_pseudo(y, X, w, 0)
    if not math.isfinite(b):
        return {"est": math.nan, "testable": False, "p": 1.0, "n": len(y)}
    r = c15.cluster_p(pv, {"event": np.asarray(ev), "week": np.asarray(wk)}, min_units=3)
    return {"est": b, **{k: r[k] for k in ("testable", "p", "ways", "small_g_rules_hold")}, "n": len(y), "pv": pv}


def mean_test(v, ev, wk) -> dict:
    v = np.asarray(v, float)
    w = event_weights(list(ev))
    pv = v * w * len(w) / w.sum()
    r = c15.cluster_p(pv, {"event": np.asarray(ev), "week": np.asarray(wk)}, min_units=2)
    return {"est": float(pv.mean()) if len(pv) else math.nan, **{k: r[k] for k in ("testable", "p", "ways", "small_g_rules_hold")}, "n": len(v), "pv": pv}


def paired_contrast(y1, x1, y2, x2, ev, *, draws: int = c15.N_BOOT, seed: int = c15.SEED_PAIRED_BOOT) -> dict:
    """``beta_birth - beta_later`` on pairs with both units; one-sided p of > 0 by the paired event-cluster bootstrap: ``p = (1 + #{diff* <= 0}) / (draws + 1)``."""
    y1, x1, y2, x2 = (np.asarray(a, float) for a in (y1, x1, y2, x2))
    ev = np.asarray(ev).astype(str)

    def diff(idx: np.ndarray) -> float:
        w = event_weights(list(ev[idx]))
        _, b1 = c15.wls_coef_pseudo(y1[idx], x1[idx], w, 0)
        _, b2 = c15.wls_coef_pseudo(y2[idx], x2[idx], w, 0)
        return b1 - b2

    if len(y1) < 4:
        return {"est": math.nan, "p": 1.0, "testable": False}
    d0 = diff(np.arange(len(y1)))
    groups = {e: np.flatnonzero(ev == e) for e in sorted(set(ev.tolist()))}
    keys = list(groups)
    rng = np.random.default_rng(seed)
    le = 0
    for _ in range(int(draws)):
        pick = rng.integers(0, len(keys), len(keys))
        idx = np.concatenate([groups[keys[i]] for i in pick])
        d = diff(idx)
        le += int(not (d > 0))
    return {"est": float(d0), "p": float((1 + le) / (draws + 1)), "testable": True, "n": len(y1)}


def lowest_tercile(vals: dict[str, float], keys: list[str]) -> list[int]:
    """Indices of the units in the lowest tercile of lifetime volume (among the given units); units without volume are outside every tercile."""
    v = np.array([vals.get(k, math.nan) for k in keys], float)
    ok = np.flatnonzero(np.isfinite(v))
    if not len(ok):
        return []
    cut = np.quantile(v[ok], 1.0 / 3.0)
    return [int(i) for i in ok if v[i] <= cut]


def quarter_of(t: float) -> str:
    d = datetime.fromtimestamp(t, UTC)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def month_of(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).strftime("%Y-%m")


def sign_checks(est_fn: Callable[[np.ndarray], float], n: int, ev: list[str], wk: list[str], tb: list[float], pv: np.ndarray) -> dict:
    """Shared binding sign robustness: top-5 event and week drops, each calendar half by birth date and every leave-one-quarter-out (section 2.6 ii-iii)."""
    ev_a, wk_a, tb_a = np.asarray(ev), np.asarray(wk), np.asarray(tb, float)
    out = {}
    for name, cl in (("top5_event_drop", ev_a), ("top5_week_drop", wk_a)):
        keep = c15.top_k_drop_mask(pv, cl)
        e = est_fn(keep)
        out[name] = {"est": e, "holds": bool(math.isfinite(e) and e > 0)}
    med = float(np.median(tb_a)) if n else math.nan
    for name, keep in (("first_half", tb_a <= med), ("second_half", tb_a > med)):
        e = est_fn(keep) if keep.sum() >= 3 else math.nan
        out[name] = {"est": e, "holds": bool(math.isfinite(e) and e > 0)}
    qs = np.array([quarter_of(t) for t in tb_a])
    loq = {q: est_fn(qs != q) for q in sorted(set(qs.tolist()))} if n else {}
    out["leave_one_quarter_out"] = {"min": min((v for v in loq.values() if math.isfinite(v)), default=math.nan), "holds": bool(loq) and all(math.isfinite(v) and v > 0 for v in loq.values())}
    return out


def p1_test(data: dict, vols: dict[str, float], *, draws_placebo: int = c15.PLACEBO_DRAWS, boot_draws: int = c15.N_BOOT) -> dict:
    feats = features_table(data)
    units = []
    for f in feats:
        if f.get("label") != "ok":
            continue
        tg = unit_target(f, data["tx"].get(f["p_market_id"], []), data["ph"].get(f["p_market_id"], []))
        if not math.isfinite(tg["delta"]):
            continue
        units.append({**f, **tg})
    eligible = sum(1 for f in feats if f.get("label") in ("ok",))
    av = {"available": len(units), "eligible": eligible, "share": len(units) / eligible if eligible else math.nan, "ok": bool(eligible and len(units) / eligible >= c15.AVAIL_MIN)}
    if len(units) < P1_MIN["pairs"] or len({u["event"] for u in units}) < P1_MIN["events"]:
        return nt(NOT_TESTABLE_POP, n=len(units), availability=av)
    if not av["ok"]:
        return nt(NOT_TESTABLE_AVAIL, n=len(units), availability=av)
    y = np.array([u["delta"] for u in units])
    x = np.array([u["g_d"] for u in units])
    ev = [u["event"] for u in units]
    tb = [u["t_birth"] for u in units]
    wk = weeks_of(tb)
    main = slope_test(y, x, ev, wk)

    def est_on(keep: np.ndarray) -> float:
        keep = np.asarray(keep, bool)
        if keep.sum() < 3:
            return math.nan
        _, b = c15.wls_coef_pseudo(y[keep], x[keep], event_weights([ev[i] for i in np.flatnonzero(keep)]), 0)
        return b

    # binding birth contrast (generic gap convergence)
    both = []
    for i, u in enumerate(units):
        lu = later_unit(u, u["meta"], data["tx"].get(u["p_market_id"], []), data["kc"].get(u["k_ticker"]), data["ph"].get(u["p_market_id"], []))
        if lu.get("ok"):
            both.append((i, lu))
    if both:
        idx = [i for i, _ in both]
        bc = paired_contrast(y[idx], x[idx], [lu["delta_L"] for _, lu in both], [lu["g_L"] for _, lu in both], [ev[i] for i in idx], draws=boot_draws)
    else:
        bc = {"est": math.nan, "p": 1.0, "testable": False}
    bc_ok = bool(bc.get("testable") and math.isfinite(bc["est"]) and bc["est"] > 0 and bc["p"] < BIRTH_CONTRAST_P)
    # binding opening-print control
    c1 = np.array([u["p_d"] - 0.5 for u in units])
    c2 = np.array([u["p_d"] - u["p_birth"] if math.isfinite(u["p_birth"]) else 0.0 for u in units])
    joint = slope_test(y, x, ev, wk, controls=[c1, c2])
    oc_ok = bool(c15.p_pass(joint, OPENING_CONTROL_P) and math.isfinite(joint["est"]) and math.isfinite(main["est"]) and joint["est"] >= OPENING_CONTROL_SHARE * main["est"])
    # binding volume tercile (lowest tercile keeps the sign; < 15 units -> unknown)
    low = lowest_tercile(vols, [u["p_market_id"] for u in units])
    if len(low) < TERCILE_MIN:
        vt = {"status": UNKNOWN, "n": len(low), "holds": False}
    else:
        m = np.zeros(len(units), bool)
        m[low] = True
        e = est_on(m)
        vt = {"status": "ok", "n": len(low), "est": e, "holds": bool(math.isfinite(e) and e > 0)}
    # binding calibration placebo: g_d shuffled across pairs within the birth month
    months = np.array([month_of(t) for t in tb])
    rng = np.random.default_rng(c15.PLACEBO_SEEDS["P1_shuffle"])
    pls = []
    for _ in range(int(draws_placebo)):
        xs = x.copy()
        for mo in set(months.tolist()):
            ii = np.flatnonzero(months == mo)
            xs[ii] = xs[ii][rng.permutation(len(ii))]
        r = slope_test(y, xs, ev, wk)
        pls.append(r["p"] if r.get("testable") else None)
    pl = c15.placebo_advance_rate(pls)
    pl_ok = bool(pl.get("advance_rate") is not None and pl["advance_rate"] <= c15.PLACEBO_MAX_ADVANCE)
    # robustness (binding; sign)
    rob = {}
    keep = np.array([not u["history_target"] for u in units])
    rob["history_target_dropped"] = {"est": est_on(keep), "holds": bool(math.isfinite(est_on(keep)) and est_on(keep) > 0)}
    worn = np.array([c15.num(u["meta"].get("c1_win_start")) <= u["t_birth"] and c15.num(u["meta"].get("c1_win_end")) >= u["t_d"] + HORIZON_S for u in units])
    rob["worn_window_dropped"] = {"n_dropped": int(worn.sum()), "est": est_on(~worn), "holds": bool(math.isfinite(est_on(~worn)) and est_on(~worn) > 0)}
    k72 = np.array([u["t_birth"] - c15.num(u["meta"].get("k_open")) >= KALSHI_FIRST_ROBUST_S for u in units])
    rob["kalshi_first_72h"] = {"est": est_on(k72), "holds": bool(math.isfinite(est_on(k72)) and est_on(k72) > 0)}
    alt = []
    for f in features_table(data, td_off=T_D_ROBUST_S):
        if f.get("label") != "ok":
            continue
        tg = unit_target(f, data["tx"].get(f["p_market_id"], []), data["ph"].get(f["p_market_id"], []))
        if math.isfinite(tg["delta"]):
            alt.append((tg["delta"], f["g_d"], f["event"]))
    if len(alt) >= 3:
        _, b30 = c15.wls_coef_pseudo(np.array([a[0] for a in alt]), np.array([a[1] for a in alt]), event_weights([a[2] for a in alt]), 0)
    else:
        b30 = math.nan
    rob["t_d_plus_30min"] = {"est": b30, "holds": bool(math.isfinite(b30) and b30 > 0)}
    el = np.array([u["cat"] == ELECTIONS_CAT for u in units])
    if el.sum() >= STRATUM_MIN and (~el).sum() >= STRATUM_MIN:
        e1, e2 = est_on(el), est_on(~el)
        rob["elections_and_rest"] = {"elections": e1, "rest": e2, "holds": bool(math.isfinite(e1) and e1 > 0 and math.isfinite(e2) and e2 > 0)}
    else:
        rob["elections_and_rest"] = {"skipped": f"fewer than {STRATUM_MIN} pairs in a stratum", "holds": True}
    rob.update(sign_checks(est_on, len(units), ev, wk, tb, main["pv"]))
    floor_ok = bool(math.isfinite(main["est"]) and main["est"] >= P1_FLOOR)
    checks = {"floor": floor_ok, "small_g": bool(main.get("small_g_rules_hold", True)), "birth_contrast": bc_ok, "opening_print_control": oc_ok, "volume_tercile": vt["holds"],
              "placebo": pl_ok, "robustness": all(v["holds"] for v in rob.values()), "availability": av["ok"]}
    checks_ok = all(checks.values())
    p = main["p"] if main.get("testable") else 1.0
    adv = c15.stage1_advance(p, checks_ok)
    reported = {"gap_closed_by_t_d_share": gap_closed_share(data), "history_target_share": float(np.mean([u["history_target"] for u in units])),
                "by_category": {c: est_on(np.array([u["cat"] == c for u in units])) for c in sorted({u["cat"] for u in units})}}
    return {"testable": bool(main.get("testable")), "p": float(p), "est": main["est"], "n": len(units), "events": len(set(ev)), "advance": adv, "checks": checks, "checks_ok": checks_ok,
            "verdict": "advance (Stage 1; selected on lifetime volume)" if adv else "not detected at MDE", "ways": main.get("ways"), "birth_contrast": bc, "opening_print_control":
            {k: joint.get(k) for k in ("est", "p", "testable")}, "volume_tercile": vt, "placebo": {**pl, "note": "g_d shuffled within the birth month", "n_draws": draws_placebo},
            "robustness": rob, "availability": av, "reported": reported, "label": LABEL_P}


def gap_closed_share(data: dict) -> float:
    """Reported (CH130's 10-minute kill): the share of ``|g(t_birth)|`` closed by ``t_d`` among units with both gaps."""
    xs = []
    for f in features_table(data):
        if f.get("label") != "ok" or not math.isfinite(f.get("p_birth", math.nan)):
            continue
        kb = k_mid_at(data["kc"].get(f["k_ticker"]), f["t_birth"])
        if not math.isfinite(kb):
            continue
        g0 = kb - f["p_birth"]
        if abs(g0) > 1e-9:
            xs.append(1.0 - abs(f["g_d"]) / abs(g0))
    return float(np.mean(xs)) if xs else math.nan


def p2_units(data: dict, *, entry_win=ENTRY_WINDOW_S, exit_win=EXIT_WINDOW_S, extra: float = 0.0) -> tuple[list[dict], dict]:
    feats = features_table(data)
    units, lost = [], Counter()
    for f in feats:
        lab = f.get("label")
        if lab == "no birth print (uncovered)":
            lost["uncovered"] += 1
            units.append({**f, "status": "uncovered", "event": f["event"], "t_birth": math.nan})
            continue
        if lab != "ok" or abs(f["g_d"]) < GAP_MIN:
            continue
        r = p2_net(f, data["tx"].get(f["p_market_id"], []), c15.taker_rate(f["fee_rate"]), entry_win=entry_win, exit_win=exit_win, extra_per_side=extra)
        if r["status"] != "ok":
            lost[r["status"]] += 1
        units.append({**f, **r})
    return units, dict(lost)


def p2_test(data: dict, vols: dict[str, float]) -> dict:
    units, lost = p2_units(data)
    ok = [u for u in units if u.get("status") == "ok"]
    eligible = sum(1 for u in units if u.get("status") != "uncovered")
    av = {"available": len(ok), "eligible": eligible, "share": len(ok) / eligible if eligible else math.nan, "ok": bool(eligible and len(ok) / eligible >= c15.AVAIL_MIN)}
    if len(ok) < P2_MIN["pairs"] or len({u["event"] for u in ok}) < P2_MIN["events"]:
        return nt(NOT_TESTABLE_POP, n=len(ok), lost=lost, availability=av)
    if not av["ok"]:
        return nt(NOT_TESTABLE_AVAIL, n=len(ok), lost=lost, availability=av)
    v = np.array([u["net"] for u in ok])
    ev = [u["event"] for u in ok]
    tb = [u["t_birth"] for u in ok]
    wk = weeks_of(tb)
    main = mean_test(v, ev, wk)

    def est_on(keep: np.ndarray) -> float:
        keep = np.asarray(keep, bool)
        if keep.sum() < 2:
            return math.nan
        w = event_weights([ev[i] for i in np.flatnonzero(keep)])
        return float(np.sum(v[keep] * w) / w.sum())

    # binding worst-case reach: lost units at w* (uncovered, no entry print, no exit)
    wc = [u for u in units if u.get("status") in ("ok", "uncovered", "no entry print", "no exit")]
    wv = np.array([u["net"] if u.get("status") == "ok" else c15.W_STAR for u in wc])
    wev = [u["event"] for u in wc]
    wtb = [u["t_birth"] if math.isfinite(u.get("t_birth", math.nan)) else c15.num(u["meta"].get("start")) for u in wc]
    wr = mean_test(wv, wev, weeks_of([t if math.isfinite(t) else 0.0 for t in wtb]))
    wr_ok = bool(c15.p_pass(wr, c15.GATE_P) and math.isfinite(wr["est"]) and wr["est"] >= P2_FLOOR)
    low = lowest_tercile(vols, [u["p_market_id"] for u in ok])
    if len(low) < TERCILE_MIN:
        vt = {"status": UNKNOWN, "n": len(low), "holds": False}
    else:
        m = np.zeros(len(ok), bool)
        m[low] = True
        e = est_on(m)
        vt = {"status": "ok", "n": len(low), "est": e, "holds": bool(math.isfinite(e) and e > 0)}
    rob = {}
    for name, kw in (("cost_plus_1c_per_side", {"extra": c15.COST_ROBUST_PER_SIDE}), ("entry_t_d_plus_3min", {"entry_win": ENTRY_ROBUST_S}), ("exit_t_d_plus_12h", {"exit_win": EXIT_ROBUST_S})):
        uu, _ = p2_units(data, **kw)
        oo = [u for u in uu if u.get("status") == "ok"]
        if len(oo) >= 2:
            w = event_weights([u["event"] for u in oo])
            e = float(np.sum(np.array([u["net"] for u in oo]) * w) / w.sum())
        else:
            e = math.nan
        rob[name] = {"est": e, "holds": bool(math.isfinite(e) and e > 0)}
    stale = np.array([bool(u.get("stale")) for u in ok])
    e = est_on(~stale)
    rob["stale_exits_dropped"] = {"n_stale": int(stale.sum()), "est": e, "holds": bool(math.isfinite(e) and e > 0)}
    rob.update(sign_checks(est_on, len(ok), ev, wk, tb, main["pv"]))
    floor_ok = bool(math.isfinite(main["est"]) and main["est"] >= P2_FLOOR)
    checks = {"floor": floor_ok, "small_g": bool(main.get("small_g_rules_hold", True)), "worst_case_reach": wr_ok, "volume_tercile": vt["holds"],
              "robustness": all(r["holds"] for r in rob.values()), "availability": av["ok"]}
    checks_ok = all(checks.values())
    p = main["p"] if main.get("testable") else 1.0
    adv = c15.stage1_advance(p, checks_ok)
    later = []
    for u in ok:
        lu = later_unit(u, u["meta"], data["tx"].get(u["p_market_id"], []), data["kc"].get(u["k_ticker"]), data["ph"].get(u["p_market_id"], []))
        if lu.get("ok"):
            r = p2_net({"t_d": lu["t_L"], "g_d": lu["g_L"]}, data["tx"].get(u["p_market_id"], []), c15.taker_rate(u["fee_rate"]))
            if r["status"] == "ok":
                later.append(r["net"])
    reported = {"rule_at_t_L_mean": float(np.mean(later)) if later else math.nan, "capacity_mean_size": float(np.mean([u["size"] for u in ok])), "lost": lost}
    return {"testable": bool(main.get("testable")), "p": float(p), "est": main["est"], "n": len(ok), "events": len(set(ev)), "advance": adv, "checks": checks, "checks_ok": checks_ok,
            "verdict": "advance (Stage 1; selected on lifetime volume)" if adv else "not detected at MDE", "ways": main.get("ways"), "worst_case_reach": {k: wr.get(k) for k in ("est", "p", "testable", "n")},
            "volume_tercile": vt, "robustness": rob, "availability": av, "reported": reported, "label": LABEL_P}


def screen_p(data_dir: Path, census: dict, *, draws_placebo: int = c15.PLACEBO_DRAWS, boot_draws: int = c15.N_BOOT) -> dict:
    """q0351: GP / GPP from the census decide which tests run; each failed gate makes that test "not testable (population)" / "not run (power)" (p = 1, counted by the screen)."""
    data = load_data(data_dir)
    vols = open_volume(data_dir, "screen-P")
    out = {}
    for t, fn in (("P1", lambda: p1_test(data, vols, draws_placebo=draws_placebo, boot_draws=boot_draws)), ("P2", lambda: p2_test(data, vols))):
        if not census["gp"][t]["pass"]:
            out[t] = nt(NOT_TESTABLE_POP)
        elif not census["gpp"][t]["pass"]:
            out[t] = nt(NOT_RUN_POWER, mde=census["gpp"][t]["mde"])
        else:
            out[t] = fn()
    for r in out.values():
        r.pop("pv", None)
    out["labels"] = [LABEL_P]
    return out


# =====================================================================================================================================================
# Smoke (q0348) and declaration
# =====================================================================================================================================================


def _chk(ok: bool, **detail) -> dict:
    return {"pass": bool(ok), **detail}


def smoke_offline(ctx: dict) -> dict:
    """Fixture checks (no network) plus the C1 reproduction call on the host (``ctx['c1_root']``)."""
    import tempfile  # noqa: PLC0415

    res: dict = {}
    k = strip_kalshi({"ticker": "X", "result": "yes", "settlement_value": 100, "open_time": "t"})
    tx = transactions([{"timestamp": 1, "price": 0.4, "size": 2, "outcomeIndex": 0, "transactionHash": "h", "side": "BUY", "proxyWallet": "0x", "name": "n"}], 0)
    clean = not ({"result", "settlement_value"} & set(k)) and set(tx[0]) == {"ts", "vwap_yes", "min_yes", "max_yes", "size"}
    refused = 0
    for bad in (Path("x/cross_venue_live/a"), Path("x/h11_pol/holdout/a"), Path("x/surprise_live/a")):
        try:
            c15.guard_input_path(bad)
        except Refused:
            refused += 1
    res["guards_fixture_P"] = _chk(clean and refused == 3, refused=refused)
    with tempfile.TemporaryDirectory() as td:
        mp = Path(td) / "cross_venue" / "matches.json"
        mp.parent.mkdir()
        mp.write_text(json.dumps([{"k_ticker": "K", "p_end": "2025-01-01", "p_market_id": "1", "k_open": "a", "p_start": "b"}]))
        r = read_matches(mp)
        res["p_matches_reader"] = _chk("p_end" not in r["K"] and r["K"]["p_market_id"] == "1")
    try:
        refuse_hist_row(ep(T15_HIST_END))
        hist_ok = False
    except Refused:
        hist_ok = True
    res["p_hist_end_refusal"] = _chk(hist_ok)
    txs = transactions([{"timestamp": 1000, "price": 0.3, "size": 1, "outcomeIndex": 0}, {"timestamp": 2000, "price": 0.4, "size": 1, "outcomeIndex": 0}], 0)
    tb, _ = birth_of(txs, "complete")
    res["p_birth_from_prints"] = _chk(tb == 1000 and math.isnan(ph_at([(900.0, 0.5)], 5000.0, tb)) and math.isnan(birth_of(txs, "uncovered")[0]))
    root = ctx.get("c1_root")
    if root:
        try:
            pairs, rep = c1_frame(Path(root), loader=ctx.get("c1_loader"))
            res["p_c1_reproduction"] = _chk(True, pairs=len(pairs), events=len({p["event"] for p in pairs}), inputs=bool(rep.get("inputs_sha256")))
        except (Refused, OSError, ValueError) as exc:
            res["p_c1_reproduction"] = _chk(False, error=str(exc)[:160])
    else:
        res["p_c1_reproduction"] = _chk(False, error="no C1 root given")
    return res


def smoke_online(lim, ctx: dict) -> dict:
    """<= 30 requests, counts only: the first-transaction reach of one out-of-frame 2025 market (newest-first paging, page count), Kalshi 1-minute candlesticks on one settled
    (historical endpoint) and one open market, Kalshi ``/markets`` with ``min_created_ts``. ``result`` is discarded at parse; no price is stored."""
    from . import cross_venue as cv  # noqa: PLC0415

    res: dict = {}
    r0 = lim.requests
    klim = ctx.get("klim") or lim
    k0 = klim.requests if klim is not lim else 0
    st, data = lim.get(c15.GAMMA_MARKETS, {"closed": "true", "end_date_min": "2025-03-01T00:00:00Z", "end_date_max": "2025-03-31T23:59:59Z", "order": "volumeNum", "ascending": "true",
                                           "volume_num_min": 1000, "limit": 1})
    m = data[0] if st == 200 and isinstance(data, list) and data else None
    if m is not None:
        gm = gamma_meta(m)
        _, info = fetch_prints_from_birth(lim, gm["condition_id"])
        res["p_first_tx_reach"] = _chk(info["reach"] == "complete", pages=info["pages"], method="newest-first offset paging")
    else:
        res["p_first_tx_reach"] = _chk(False, error=f"no out-of-frame market (status {st})")
    got = {}
    for status, hist in (("settled", True), ("open", False)):
        st, d = klim.get(f"{KALSHI_API}/{'historical/' if hist else ''}markets", {"status": status, "limit": 1} if not hist else {"limit": 1})
        ms = [strip_kalshi(x) for x in ((d or {}).get("markets") or [])] if st == 200 and isinstance(d, dict) else []
        if not ms:
            got[status] = {"ok": False, "status": st}
            continue
        mk = ms[0]
        end = int(c15.parse_iso(mk.get("close_time")) if hist else time.time())
        end = end if end > 0 else int(time.time())
        c, _ = cv.fetch_k_candles(klim, mk["ticker"], str(mk.get("series_ticker") or mk.get("event_ticker", "").split("-")[0]), end - 3600, end, hist)
        got[status] = {"ok": True, "candles": int(len(c))}
    res["p_kalshi_candles"] = _chk(all(v.get("ok") for v in got.values()), **got)
    st, d = klim.get(f"{KALSHI_API}/markets", {"min_created_ts": int(time.time()) - 86400, "limit": 5})
    res["p_kalshi_min_created"] = _chk(st == 200 and isinstance(d, dict) and "markets" in d, status=st)
    total = lim.requests - r0 + ((klim.requests - k0) if klim is not lim else 0)
    res["_requests"] = {"pass": total <= SMOKE_MAX_REQUESTS, "requests": total}
    return res


def declared() -> dict:
    return {"family": "P", "label": LABEL_P, "stage2_ready": STAGE2_READY,
            "dates": {"hist_end": T15_HIST_END, "p2_start_min": T15_P2_START_MIN, "p2_cap": T15_P2_CAP},
            "population": {"c1_expected": C1_EXPECTED, "c1_call": "cb12_x.load_c1(root, expected=cb12_x.C1_EXPECTED) (pinned inputs and study source)", "c1_loader_sha256": c1_loader_sha(),
                           "fields": list(MATCH_FIELDS), "never_read": list(NEVER_READ_FIELDS), "sports_cat": SPORTS_CAT, "sports_in_primary": c15.CB15_SPORTS_IN_PRIMARY,
                           "kalshi_first_proxy": "p_start - k_open >= 24 h (census)", "kalshi_first_binding": "t_birth - k_open >= 24 h (exactly 24 h counts)", "gpb": GPB_MIN,
                           "rule_booleans": "Kalshi is_provisional / can_close_early (C1 universe rows, if present) vs Polymarket: no comparable Gamma booleans -> not applicable, reported"},
            "clocks": {"t_d_offset_s": T_D_OFFSET_S, "t_l_offset_s": T_L_OFFSET_S, "print_max_age_s": PRINT_MAX_AGE_S, "target_print_window_s": list(TARGET_PRINT_WINDOW_S), "ph_lag_s": PH_LAG_S,
                       "ph_max_age_s": PH_MAX_AGE_S, "ph_after_birth_only": True, "k_max_age_s": K_MAX_AGE_S, "k_spread_max": K_SPREAD_MAX, "end_margin_s": END_MARGIN_S},
            "fetch": {"print_pages": PRINT_PAGES, "print_page_limit": PRINT_PAGE_LIMIT, "reach": "complete iff a non-full page is reached (newest-first offset paging)", "max_pairs": P_DATA_MAX_PAIRS,
                      "tx_windows": "[t_birth, t_birth + 25 h] and [t_L - 2 h, t_L + 24 h 30 min]", "candles": "[t_birth - 6 h, t_d + 25 h] and [t_L - 1 h, t_L + 25 h]",
                      "prices_history": "fidelity 10 after t_birth only; points before counted", "volume": "stored apart; opened only by the screen's tercile check"},
            "p1": {"floor": P1_FLOOR, "min": P1_MIN, "ways": ["event", "birth_week"], "birth_contrast_p": BIRTH_CONTRAST_P, "paired_boot": {"draws": c15.N_BOOT, "seed": c15.SEED_PAIRED_BOOT},
                   "opening_control": {"p": OPENING_CONTROL_P, "share": OPENING_CONTROL_SHARE}, "tercile_min": TERCILE_MIN, "placebo": {"seed": c15.PLACEBO_SEEDS["P1_shuffle"], "draws": c15.PLACEBO_DRAWS,
                   "max_advance": c15.PLACEBO_MAX_ADVANCE}, "robust": {"kalshi_first_s": KALSHI_FIRST_ROBUST_S, "t_d_s": T_D_ROBUST_S, "stratum_min": STRATUM_MIN}},
            "p2": {"floor": P2_FLOOR, "min": P2_MIN, "gap_min": GAP_MIN, "entry_s": list(ENTRY_WINDOW_S), "exit_s": list(EXIT_WINDOW_S), "entry_robust_s": list(ENTRY_ROBUST_S),
                   "exit_robust_s": list(EXIT_ROBUST_S), "w_star": c15.W_STAR, "fee_floor": c15.FEE_FLOOR, "cost_robust": c15.COST_ROBUST_PER_SIDE},
            "gpp": {"p1_max_mde": GPP_P1_MAX, "p2_max_mde": GPP_P2_MAX, "mult": c15.MDE_MULT, "inflate": c15.MDE_INFLATE, "proxy": "SE only at t_L"},
            "smoke": {"needs": list(SMOKE_NEEDS), "max_requests": SMOKE_MAX_REQUESTS}}


def kalshi_bools_from_universe(root: Path, tickers: set[str]) -> dict[str, dict]:
    """Kalshi ``is_provisional`` / ``can_close_early`` of the C1 tickers from the pinned universe rows (``kalshi_markets*.jsonl``; first occurrence wins), no fetch."""
    out: dict[str, dict] = {}
    r = c15.refuse_path(Path(root), allow=("cross_venue",))
    for f in sorted(r.glob("kalshi_markets*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                m = json.loads(line)
                t = m.get("ticker")
                if t in tickers and t not in out:
                    out[t] = {"is_provisional": m.get("is_provisional"), "can_close_early": m.get("can_close_early")}
    return out


def write_birth_frame(path: Path, rows: list[list]) -> Path:
    return c15.write_gz_csv(Path(path), BIRTH_FRAME_COLUMNS, rows)


def read_gz_rows(path: Path) -> list[dict]:
    with gzip.open(Path(path), "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
