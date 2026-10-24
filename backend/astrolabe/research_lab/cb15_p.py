# ruff: noqa: E501
"""CB15-P: the pair at birth (CH130; docs/research_lab/CREATIVE_BATCH_15.md CB15-P, sections 1.1-1.3, 2.1-2.8, 9-10). Rules part ``P``. Selected on lifetime volume.

On the audited C1 Kalshi-Polymarket pairs where Kalshi opened >= 24 h before Polymarket's FIRST PRINT, does the gap ``g_d`` = Kalshi mid - Polymarket's last print at ``t_d`` = first
print + 10 min predict Polymarket's move over the next 24 h (P1), and does trading toward Kalshi at recorded prints pay after fees (P2)? Stage 1 here: the birth-order census (q0347, no
network, gate GPB), the smoke helpers (q0348), the data fetch (q0349: Gamma metadata, Data API prints from the first transaction aggregated to transactions, Kalshi 1-minute candles,
``prices-history`` AFTER the first print only), the census (q0350: gates GP and GPP with the SE-only proxy) and the screen (q0351: P1, P2 with every binding check).

Stage 2: the birth watcher (q0352: causal selection, no volume filter, the frozen matcher, first-print polling, recorded books at ``t_d`` and ``t_d + 24 h``, weekly blind title-audit
batches) and the rep (q0353: P1-rep, P2-rep at recorded books; one Stage-2 Holm). ``part_unready()`` kept part P undeclared until the whole part was written. This module imports ``cb15_common`` and nothing from the E family. No P statistic reads a C1 series VALUE (the C1 reproduction
call is used for the pair list and the series window TIMES only); ``p_end`` is never read; no Gamma outcome, Kalshi ``result`` / ``settlement_value``, side, wallet or hash is stored.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import inspect
import io
import json
import math
import re
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
STAGE2_READY = True  # the Stage-2 watcher (q0352) and rep (q0353) are written: part P is declared
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
K_CANDLE_CHUNK_S = 4800 * 60  # <= 5000 one-minute candles per request (as cross_venue.CANDLE_CHUNK_S; copied so that it is hashed with part P)
PH_WINDOW_DAYS = 14  # as history_backfill.WINDOW_DAYS (30-day windows were rejected, HTTP 400)
PH_FIDELITY = 10  # prices-history fidelity in minutes (as history_backfill.FIDELITY_MIN)
CLOB_PRICES = "https://clob.polymarket.com/prices-history"
P_DATA_MAX_PAIRS = 150
P_DATA_STATUS = "p_data_complete"
P_DATA_PROGRESS = "p_data_in_progress"
DATA_RUN = "h15_birth"
DATA_FILES = {"meta": "meta.csv.gz", "tx": "tx.csv.gz", "kalshi": "kalshi.csv.gz", "prices": "prices.csv.gz", "volume": "volume_guarded.csv.gz", "work": "work.jsonl", "attempts": "attempts.jsonl"}
META_COLUMNS = ["k_ticker", "k_series", "k_cat", "p_market_id", "p_event_id", "k_open", "created", "start", "end_sched", "fee_rate", "yes_index", "t_birth", "t_birth_vwap", "reach",
                "print_pages", "n_tx", "ph_before_birth", "ph_first_seeded", "k_bool_provisional", "k_bool_close_early", "c1_win_start", "c1_win_end", "status", "key_drop"]
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
SMOKE_NEEDS = ("guards_fixture_P", "p_matches_reader", "p_hist_end_refusal", "p_birth_from_prints", "p_c1_reproduction", "p_first_tx_reach", "p_kalshi_candles", "p_kalshi_min_created", "p_kalshi_open_cache")
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


def reread_absent_frames(hist_root: Path, absent: list[str], ksrc: dict) -> tuple[dict, dict]:
    """P-7 (section 1.3): frames recorded "absent at q0340" are re-read now (id columns only, ``ID_READABLE`` files); each id found gets the source ``frame:<root>/<file>`` in a COPY of
    ``ksrc`` (so a C1 id also found there is no longer C1-only and drops). Returns (the extended key sources, a report: found per frame with id counts, still absent)."""
    out = {k: {i: set(v) for i, v in d.items()} for k, d in (ksrc or {}).items()}
    for kind in ("market", "event", "neg_risk_market", "series"):
        out.setdefault(kind, {})
    cols = {"market_id": "market", "event_id": "event", "neg_risk_market_id": "neg_risk_market", "negRiskMarketID": "neg_risk_market", "series_id": "series"}
    found, still = {}, []
    for rel in absent:
        path = c15.id_source_path(rel, hist_root)
        if not path.is_file():
            still.append(rel)
            continue
        ids = c15.read_id_columns(path)
        found[rel] = {c: len(v) for c, v in ids.items()}
        for col, kind in cols.items():
            for i in ids.get(col, set()):
                out[kind].setdefault(str(i), set()).add(f"frame:{rel}")
    return out, {"reread": found, "still_absent": still}


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


def truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def rule_booleans_differ(meta: dict) -> bool:
    """The design's rule-boolean exclusion (P-6, restated by P-20). Polymarket exposes no ``is_provisional`` / ``can_close_early`` flag at listing, so its side is declared UNKNOWN
    (``POLY_RULE_BOOLEANS``), not False (Polymarket markets can resolve early). The design says nothing for an unknown side; the declared conservative choice is to exclude every pair
    whose KALSHI flag is true (equality with a Polymarket contract cannot be shown) and to keep a pair whose Kalshi flags are false or missing (excluding all of them would empty the
    study); the residual early-resolution mismatch is bounded by the scheduled-end exclusion (P-16) and the unavailable (no order book at 24 h) label. A missing Kalshi flag is counted
    separately as unknown."""
    return truthy(meta.get("k_bool_provisional")) or truthy(meta.get("k_bool_close_early"))


def unit_features(meta: dict, txs: list[dict], candles: np.ndarray, *, td_off: float = T_D_OFFSET_S, kalshi_first_s: float = KALSHI_FIRST_S) -> dict:
    """Features at ``t_d`` only (what the census may read): the binding Kalshi-first rule (``t_birth - k_open >= 24 h``; exactly 24 h counts), the scheduled-end exclusion, ``p_d``
    (the last print at or before ``t_d``; the first print itself if none since), ``k_d``, ``g_d`` and the label."""
    if str(meta.get("status") or "").startswith(UNAVAILABLE_SOURCE):
        return {"label": UNAVAILABLE_SOURCE}  # P-17: counted in the labels and the denominators, never a unit
    tb = c15.num(meta.get("t_birth"))
    if not math.isfinite(tb):
        return {"label": "no birth print (uncovered)"}
    ko = c15.num(meta.get("k_open"))
    if not (math.isfinite(ko) and tb - ko >= kalshi_first_s):
        return {"label": "polymarket first (binding)", "t_birth": tb}
    if str(meta.get("key_drop") or ""):
        return {"label": "key drop (neg-risk / series / frame source)", "t_birth": tb}
    if rule_booleans_differ(meta):
        return {"label": KALSHI_FLAG_LABEL, "t_birth": tb}
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
    evs = [e for e in (m.get("events") if isinstance(m.get("events"), list) else []) if isinstance(e, dict)]
    eids = [str(e["id"]) for e in evs if e.get("id") is not None]
    sids = sorted({str(s["id"]) for e in evs for s in (e.get("series") if isinstance(e.get("series"), list) else []) if isinstance(s, dict) and s.get("id") is not None})
    return {"created": c15.parse_iso(m.get("createdAt")), "start": c15.parse_iso(m.get("startDate")), "end_sched": c15.parse_iso(m.get("endDate")), "fee_rate": c15.num(fs.get("rate")),
            "yes_index": labels.index("yes") if "yes" in labels else 0, "condition_id": str(m.get("conditionId") or ""), "tokens": [str(x) for x in c15.c12.listish(m.get("clobTokenIds"))],
            "volume": vol, "neg_risk_market_id": str(m.get("negRiskMarketID") or ""), "event_ids": ";".join(eids), "series_ids": ";".join(sids)}


class PairPending(Exception):
    """A read of a pair returned a non-200 status (or a malformed body): the pair is NOT finished; it stays pending and is retried (CB15-P amendment P-5)."""

    def __init__(self, statuses: dict[str, int], why: str = "non-200 read"):
        super().__init__(f"{why}: {statuses}")
        self.statuses = dict(statuses)


CANDLE_FIELDS = ("end_period_ts", "yes_bid", "yes_ask", "price")  # what cross_venue.parse_k_candles reads (volume is optional there)


def candle_has_fields(c) -> bool:
    """P-17: a fallback-endpoint candle is accepted only if it carries the same fields the frozen parser reads; anything else leaves the pair pending (never reinterpreted)."""
    return isinstance(c, dict) and all(k in c for k in CANDLE_FIELDS)


def fetch_k_candles_checked(klim, ticker: str, series: str, start: int, end: int, historical: bool, stat: Counter) -> np.ndarray:
    """Status-aware Kalshi 1-minute candles (the same request as ``cross_venue.fetch_k_candles``, which skips a non-200 silently and is left unchanged): every chunk's status is counted in
    ``stat`` (key ``kalshi_candles:<status>``); a non-200 chunk or a non-dict body raises ``PairPending`` after the loop (the pair is retried, never written finished)."""
    from . import cross_venue as cv  # noqa: PLC0415

    def path_of(hist: bool) -> str:
        return f"{KALSHI_API}/historical/markets/{ticker}/candlesticks" if hist else f"{KALSHI_API}/series/{series}/markets/{ticker}/candlesticks"

    raw: list[dict] = []
    bad = 0
    a = start
    while a < end:
        b = min(a + K_CANDLE_CHUNK_S, end)
        params = {"start_ts": a, "end_ts": b, "period_interval": 1}
        st, data = klim.get(path_of(historical), params)
        stat[f"kalshi_candles:{st}"] += 1
        if st == 404:  # P-17: the live / historical endpoint split (market archived or not yet archived): ONE try of the other endpoint for this chunk, same-fields only
            st2, data2 = klim.get(path_of(not historical), params)
            stat[f"kalshi_candles_fallback:{st2}"] += 1
            cs2 = data2.get("candlesticks") if isinstance(data2, dict) else None
            if st2 == 200 and isinstance(cs2, list) and cs2 and all(candle_has_fields(c) for c in cs2):  # P-24: a non-empty reply only
                st, data = st2, data2
        if st == 200 and isinstance(data, dict):
            raw.extend(data.get("candlesticks") or [])
        else:
            bad += 1
        a = b
    if bad:
        raise PairPending(dict(stat), "kalshi candles non-200")
    return cv.parse_k_candles(raw)


def fetch_prices_checked(lim, token: str, start: int, end: int, stat: Counter) -> list[tuple[int, float]]:
    """Status-aware ``prices-history`` at 10-minute fidelity (the same request as ``history_backfill.fetch_prices``, which skips a non-200 silently and is left unchanged); a non-200
    window raises ``PairPending`` after the loop."""
    pts: dict[int, float] = {}
    bad = 0
    a = start
    step = PH_WINDOW_DAYS * 86400
    while a < end:
        b = min(a + step, end)
        st, data = lim.get(CLOB_PRICES, {"market": token, "startTs": a, "endTs": b, "fidelity": PH_FIDELITY})
        stat[f"prices_history:{st}"] += 1
        if st == 200 and isinstance(data, dict):
            for h in data.get("history") or []:
                pts[int(h["t"])] = float(h["p"])
        else:
            bad += 1
        a = b
    if bad:
        raise PairPending(dict(stat), "prices-history non-200")
    return sorted(pts.items())


def fetch_pair(lim, klim, row: dict, gm: dict) -> dict:
    """One pair of q0349 (network): prints from the first transaction, Kalshi candles over ``[t_birth - 6 h, t_d + 25 h]`` and ``[t_L - 1 h, t_L + 25 h]``, ``prices-history`` after
    ``t_birth`` (points before it counted only). Rows at or after T15_hist_end are dropped at parse (never stored). Any non-200 candle or prices-history window raises
    ``PairPending`` (the pair stays pending); the request statuses are returned in ``req``."""
    hist_end = ep(T15_HIST_END)
    stat: Counter = Counter()
    prints, info = fetch_prints_from_birth(lim, gm["condition_id"])
    txs = [t for t in transactions(prints, gm["yes_index"]) if t["ts"] < hist_end]
    tb, tbv = birth_of(txs, info["reach"])
    out = {"meta": {"t_birth": tb, "t_birth_vwap": tbv, "reach": info["reach"], "print_pages": info["pages"], "n_tx": len(txs)}, "tx": [], "kalshi": [], "prices": [], "req": {}}
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
        c = fetch_k_candles_checked(klim, row["k_ticker"], row["k_series"], int(lo), int(hi), hist, stat)
        kc += [[float(r[0]), float(r[1]), float(r[2])] for r in c if r[0] < hist_end]
    out["kalshi"] = sorted({tuple(r) for r in kc})
    tok = gm["tokens"][gm["yes_index"]] if gm["tokens"] else ""
    pts_all: list[tuple[float, float]] = []
    for lo, hi in ((tb - PH_PRE_S, td + CANDLE_POST_S), (tl - CANDLE_L_PRE_S, tl + CANDLE_POST_S)):
        hi = min(hi, hist_end - 1)
        if hi <= lo or not tok:
            continue
        pts = fetch_prices_checked(lim, tok, int(lo), int(hi), stat)
        pts_all += [(float(s), float(p)) for s, p in pts if s < hist_end]
    before, seeded = seeded_flags(pts_all, tb)
    out["meta"].update(ph_before_birth=before, ph_first_seeded=seeded)
    out["prices"] = sorted({(s, p) for s, p in pts_all if s > tb})
    out["req"] = dict(stat)
    return out


def read_frame(path: Path) -> list[dict]:
    return list(c15.read_csv_gz(Path(path)))


def p_data(hist_root: Path, lim, klim, *, frame_path: Path, kalshi_bools: dict[str, dict] | None = None, budget_s: float | None = None, clock=time.time,
           gamma_lookup: Callable[[list[str]], dict[str, dict]] | None = None, ksrc: dict | None = None, min_gap_s: float = 0.0) -> dict:
    """q0349 (P-23: with ``min_gap_s`` > 0 a run that starts less than that after the previous run that left failed pairs ended raises ``NotNow`` (exit 75), because the queue worker re-starts a
    repeat run immediately; the P-17 terminal rule then always spans >= 3 runs spaced >= 15 min): per Kalshi-first proxy pair (``birth_frame.csv.gz`` of q0347, at most 150), resumable (``work.jsonl`` holds one line per finished pair; a torn tail line is re-fetched),
    budgeted (``in_progress`` with exit 0 when the budget is spent). A pair whose candle or prices-history read returned a non-200 stays PENDING (``attempts.jsonl`` holds the request
    statuses; the run ends ``in_progress`` and never completes with a pending pair). ``ksrc`` (the key sources, with the frames absent at q0340 re-read) gives each pair its
    ``key_drop`` from ALL its keys (market, events, ``negRiskMarketID``, series). On completion writes meta / tx / kalshi / prices / volume files and the manifest with ``p_data_complete``."""
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
    attempts = out_dir / DATA_FILES["attempts"]
    stamp = out_dir / RUN_STAMP
    if min_gap_s > 0 and stamp.is_file():
        last_end = float(_read_json(stamp, {}).get("ended") or 0.0)
        if 0 <= clock() - last_end < min_gap_s:
            raise cm.NotNow(f"p-data: the previous run with failed pairs ended {clock() - last_end:.0f} s ago (< {min_gap_s:.0f} s, P-23); not now")
    pending: dict[str, dict] = {}
    # P-17: the terminal rule. A pair with >= PAIR_FAIL_ATTEMPTS failed attempts in that many separate runs, first to last >= PAIR_FAIL_SPAN_S apart, becomes "unavailable (source)"
    # (a finished record: no data, counted in the labels and denominators). Declared before any failure was observed; the attempt log is the evidence.
    fails: dict[str, list[tuple[str, float]]] = {}
    for rec_a in c15.jsonl_iter(attempts):
        fails.setdefault(str(rec_a.get("k_ticker")), []).append((str(rec_a.get("run") or rec_a.get("t")), float(rec_a.get("t") or 0.0)))
    for kt, att in fails.items():
        runs, times = {x[0] for x in att}, [x[1] for x in att]
        if kt not in finished and len(runs) >= PAIR_FAIL_ATTEMPTS and max(times) - min(times) >= PAIR_FAIL_SPAN_S:
            rec_t = {"k_ticker": kt, "status": UNAVAILABLE_SOURCE, "attempts": len(att), "span_s": max(times) - min(times)}
            c15.jsonl_append(work, rec_t)
            finished[kt] = rec_t
    todo = [r for r in frame if r["k_ticker"] not in finished]
    run_id = f"{clock():.3f}"
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
            if pending:
                cm.write_json_atomic(stamp, {"ended": clock()})
            return {"status": P_DATA_PROGRESS, "complete": False, "done": len(finished), "todo": len(frame) - len(finished)}
        raw = gms.get(str(r["p_market_id"]))
        if raw is None:
            rec = {"k_ticker": r["k_ticker"], "status": "no gamma metadata"}
        else:
            gm = gamma_meta(raw)
            try:
                got = fetch_pair(lim, klim, r, gm)
            except PairPending as exc:
                c15.jsonl_append(attempts, {"k_ticker": r["k_ticker"], "t": clock(), "run": run_id, "statuses": exc.statuses, "why": str(exc)[:160]})
                pending[r["k_ticker"]] = exc.statuses
                continue
            kb = (kalshi_bools or {}).get(r["k_ticker"], {})
            kd = c15.drop_reason({"market_id": r["p_market_id"], "event_ids": gm["event_ids"] or r.get("p_event_id"), "neg_risk_market_id": gm["neg_risk_market_id"], "series_ids": gm["series_ids"]},
                                 ksrc, "P") if ksrc else ""
            rec = {"k_ticker": r["k_ticker"], "status": "ok", "gm": {k: v for k, v in gm.items() if k != "tokens"}, "row": r, **got, "key_drop": kd,
                   "k_bools": {"is_provisional": kb.get("is_provisional"), "can_close_early": kb.get("can_close_early")}}
        c15.jsonl_append(work, rec)
        finished[r["k_ticker"]] = rec
    if pending:
        cm.write_json_atomic(stamp, {"ended": clock()})
        return {"status": P_DATA_PROGRESS, "complete": False, "done": len(finished), "todo": len(frame) - len(finished), "pending_read_failures": sorted(pending),
                "note": "a pair with a non-200 read stays pending; statuses in attempts.jsonl"}
    files = write_data_files(out_dir, frame, finished)
    c15.write_dir_manifest(out_dir, P_DATA_STATUS, files, {"n_pairs": len(frame), "labels": dict(Counter(str(v.get("meta", {}).get("reach") or v.get("status")) for v in finished.values())),
                                                                  "unavailable_source": sum(1 for v in finished.values() if v.get("status") == UNAVAILABLE_SOURCE)})
    return {"status": P_DATA_STATUS, "complete": True, "n_pairs": len(frame)}


def write_data_files(out_dir: Path, frame: list[dict], finished: dict[str, dict]) -> list[Path]:
    meta_rows, tx_rows, k_rows, ph_rows, vol_rows = [], [], [], [], []
    for r in frame:
        rec = finished.get(r["k_ticker"]) or {}
        gm, m, kb = rec.get("gm") or {}, rec.get("meta") or {}, rec.get("k_bools") or {}
        meta_rows.append([r["k_ticker"], r["k_series"], r["k_cat"], r["p_market_id"], r["p_event_id"], c15.parse_iso(r["k_open"]), gm.get("created"), gm.get("start"), gm.get("end_sched"),
                          gm.get("fee_rate"), gm.get("yes_index"), m.get("t_birth"), m.get("t_birth_vwap"), m.get("reach"), m.get("print_pages"), m.get("n_tx"), m.get("ph_before_birth"),
                          m.get("ph_first_seeded"), kb.get("is_provisional"), kb.get("can_close_early"), r.get("c1_win_start"), r.get("c1_win_end"), rec.get("status", "missing"), rec.get("key_drop") or ""])
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


def target_availability(feats: list[dict], data: dict) -> dict:
    """Counts only (P-14): among the ``ok`` units, how many have a print in ``[t_d + 22 h, t_d + 24 h]`` (print target), only a usable post-birth ``prices-history`` point
    (history target) or neither (no target). Presence only: no price, change or ``Delta`` leaves this function."""
    out = Counter()
    for f in feats:
        if f.get("label") != "ok":
            continue
        txs, ph = data["tx"].get(f["p_market_id"], []), data["ph"].get(f["p_market_id"], [])
        t = f["t_d"] + HORIZON_S
        if print_in(txs, f["t_d"] + TARGET_PRINT_WINDOW_S[0], f["t_d"] + TARGET_PRINT_WINDOW_S[1]):
            out["print_target"] += 1
        elif math.isfinite(ph_at(ph, t, f["t_birth"])):
            out["history_target"] += 1
        else:
            out["no_target"] += 1
    return {"print_target": out["print_target"], "history_target": out["history_target"], "no_target": out["no_target"]}


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
                                                                                         "kalshi_unknown": sum(1 for m in meta if m.get("k_bool_provisional") in ("", None)),
                                                                                         "differ_excluded": sum(1 for m in meta if rule_booleans_differ(m)),
                                                                                         "polymarket": "declared UNKNOWN for both flags (P-6 ruling, P-27): only a true Kalshi flag excludes"},
            "key_drops": sum(1 for m in meta if str(m.get("key_drop") or "")),
            "targets": target_availability(feats, data),
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


def sign_checks(est_fn: Callable[[np.ndarray], float], n: int, ev: list[str], wk: list[str], tb: list[float], pv: np.ndarray, *, p_fn: Callable[[np.ndarray], dict | None], floor: float) -> dict:
    """Shared binding robustness: p and the floor without the top 5 clusters of each way (section 2.6 ii: the estimate on the kept units is >= ``floor`` AND the one-sided p of the
    kept units is < 0.01, ``p_fn(keep)``), each calendar half by birth date and every leave-one-quarter-out (sign; 2.6 iii). Declared (P-13b): a way with fewer than 15 clusters
    leaves the max and its leave-one-cluster-out sign rule binds instead (CB10 small-G rule, ``small_g`` check), so its top-5 drop is not applied (recorded); with a single calendar
    quarter, leave-one-quarter-out is not applicable (recorded) and the halves bind."""
    ev_a, wk_a, tb_a = np.asarray(ev), np.asarray(wk), np.asarray(tb, float)
    out = {}
    for name, cl in (("top5_event_drop", ev_a), ("top5_week_drop", wk_a)):
        G = len(set(cl.astype(str).tolist()))
        if G < c15.G_CR2:
            out[name] = {"skipped": f"G = {G} < {c15.G_CR2}: the way's leave-one-cluster-out sign rule binds (small_g)", "holds": True}
            continue
        keep = c15.top_k_drop_mask(pv, cl)
        e = est_fn(keep)
        r = p_fn(keep)
        out[name] = {"est": e, "p": None if r is None else r.get("p"), "floor": floor,
                     "holds": bool(math.isfinite(e) and e >= floor and c15.p_pass(r, c15.GATE_P))}
    med = float(np.median(tb_a)) if n else math.nan
    for name, keep in (("first_half", tb_a <= med), ("second_half", tb_a > med)):
        e = est_fn(keep) if keep.sum() >= 3 else math.nan
        out[name] = {"est": e, "holds": bool(math.isfinite(e) and e > 0)}
    qs = np.array([quarter_of(t) for t in tb_a])
    if len(set(qs.tolist())) < 2:
        out["leave_one_quarter_out"] = {"skipped": "one calendar quarter: not applicable (the halves bind)", "holds": bool(n)}
        return out
    loq = {q: est_fn(qs != q) for q in sorted(set(qs.tolist()))}
    out["leave_one_quarter_out"] = {"min": min((v for v in loq.values() if math.isfinite(v)), default=math.nan), "holds": all(math.isfinite(v) and v > 0 for v in loq.values())}
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
    eligible = sum(1 for f in feats if f.get("label") in ("ok", "no Kalshi quote", UNAVAILABLE_SOURCE))  # P-10 / P-17: a unit without a Kalshi quote at t_d, or whose source stayed unavailable, is eligible and unavailable
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
        for mo in sorted(set(months.tolist())):
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
    def p_on(keep: np.ndarray) -> dict | None:
        idx = np.flatnonzero(np.asarray(keep, bool))
        if len(idx) < 3:
            return None
        return slope_test(y[idx], x[idx], [ev[i] for i in idx], [wk[i] for i in idx])

    rob.update(sign_checks(est_on, len(units), ev, wk, tb, main["pv"], p_fn=p_on, floor=P1_FLOOR))
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
        if lab in ("no birth print (uncovered)", UNAVAILABLE_SOURCE):
            lost["uncovered" if lab != UNAVAILABLE_SOURCE else UNAVAILABLE_SOURCE] += 1  # P-17: the worst-case reach includes both at w*
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
    def p_on(keep: np.ndarray) -> dict | None:
        idx = np.flatnonzero(np.asarray(keep, bool))
        if len(idx) < 2:
            return None
        return mean_test(v[idx], [ev[i] for i in idx], [wk[i] for i in idx])

    rob.update(sign_checks(est_on, len(ok), ev, wk, tb, main["pv"], p_fn=p_on, floor=P2_FLOOR))
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


def cache_size_probe(klim, pages: int | None = None) -> dict:
    """P-19, counts only: up to ``pages`` pages of the open-market list through the cache's own parser; reports the records, the plain and gzip bytes per record, whether the listing was
    exhausted, and the projected upper bound at the page cap (``KALSHI_MAX_PAGES`` x ``KALSHI_PAGE``) against the declared cache-folder cap. No price or title leaves this function."""
    pages = SMOKE_CACHE_PAGES if pages is None else pages
    recs, cur, n_pages, status = [], None, 0, 200
    try:
        for _ in range(pages):
            r, cur = kalshi_page(klim, cur, None)
            recs += r
            n_pages += 1
            if cur is None:
                break
    except ApiError as exc:
        status = int(re.search(r"status (\d+)", str(exc)).group(1)) if re.search(r"status (\d+)", str(exc)) else 0
    plain = sum(len(json.dumps(r, sort_keys=True)) + 1 for r in recs)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as fh:
        for r in recs:
            fh.write((json.dumps(r, sort_keys=True) + "\n").encode())
    gz = len(buf.getvalue())
    per_plain, per_gz = (plain / len(recs), gz / len(recs)) if recs else (math.nan, math.nan)
    cap_records = KALSHI_MAX_PAGES * KALSHI_PAGE
    proj = per_plain * cap_records + per_gz * cap_records if recs else math.nan  # partial (plain) + cache (gzip) at the page cap
    return {"ok": bool(recs) and status == 200, "status": status, "pages": n_pages, "records": len(recs), "exhausted": cur is None and bool(recs), "plain_bytes": plain, "gzip_bytes": gz,
            "plain_per_record": per_plain, "gzip_per_record": per_gz, "projected_max_folder_bytes": proj, "cache_dir_cap_bytes": CACHE_DIR_CAP_BYTES,
            "within_cap": bool(math.isfinite(proj) and proj <= CACHE_DIR_CAP_BYTES)}


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
    res["p_kalshi_open_cache"] = _chk(**cache_size_probe(klim))
    total = lim.requests - r0 + ((klim.requests - k0) if klim is not lim else 0)
    res["_requests"] = {"pass": total <= SMOKE_MAX_REQUESTS, "requests": total}
    return res


def _src_sha(module: str, name: str) -> str:
    import importlib  # noqa: PLC0415

    return hashlib.sha256(inspect.getsource(getattr(importlib.import_module(f".{module}", __package__), name)).encode()).hexdigest()


def declared() -> dict:
    return {"family": "P", "label": LABEL_P, "stage2_ready": STAGE2_READY,
            "dates": {"hist_end": T15_HIST_END, "p2_start_min": T15_P2_START_MIN, "p2_cap": T15_P2_CAP},
            "population": {"c1_expected": C1_EXPECTED, "c1_call": "cb12_x.load_c1(root, expected=cb12_x.C1_EXPECTED) (pinned inputs and study source)", "c1_loader_sha256": c1_loader_sha(),
                           "fields": list(MATCH_FIELDS), "never_read": list(NEVER_READ_FIELDS), "sports_cat": SPORTS_CAT, "sports_in_primary": c15.CB15_SPORTS_IN_PRIMARY,
                           "kalshi_first_proxy": "p_start - k_open >= 24 h (census)", "kalshi_first_binding": "t_birth - k_open >= 24 h (exactly 24 h counts)", "gpb": GPB_MIN,
                           "rule_booleans": "P-6/P-20: Polymarket's is_provisional / can_close_early are declared UNKNOWN (no field at listing; Polymarket markets can resolve early); the design is silent for unknown, so the conservative choice: a pair whose Kalshi is_provisional or can_close_early is true (C1 universe rows; live: the Kalshi market record) is excluded, counted; Kalshi false or missing is kept (counted unknown); residual mismatch is bounded by the scheduled-end exclusion and the 24-h no-book label",
                           "polymarket_rule_booleans": POLY_RULE_BOOLEANS,
                           "p6_ruling": "P-27: Polymarket early-close flags are UNKNOWN and disclosed. The Kalshi true-flag exclusion (causal, from the Kalshi record at the match) is kept and labelled 'Kalshi early-close/provisional flag'. Units are NEVER excluded or labelled by when the Polymarket market actually closed (post-t0, outcome-linked); early-closing units stay in the denominators (Stage 2 'unavailable (no order book at 24 h)', Stage 1 'no target'); a count of them may be reported descriptively, never as a gate. Disclosure: Stage 1 reads Gamma endDate after the fact and it may have been edited to the actual close date (the scheduled-end exclusion, P-16, uses that value in Stage 1; in Stage 2 it is the value stored at the match)",
                           "key_rule": "P-7: q0347 re-reads the frames recorded absent at q0340; q0349 checks ALL keys of each pair (market, events, negRiskMarketID, series ids) by source (a C1-only key is kept)"},
            "clocks": {"t_d_offset_s": T_D_OFFSET_S, "t_l_offset_s": T_L_OFFSET_S, "print_max_age_s": PRINT_MAX_AGE_S, "target_print_window_s": list(TARGET_PRINT_WINDOW_S), "ph_lag_s": PH_LAG_S,
                       "ph_max_age_s": PH_MAX_AGE_S, "ph_after_birth_only": True, "k_max_age_s": K_MAX_AGE_S, "k_spread_max": K_SPREAD_MAX, "end_margin_s": END_MARGIN_S},
            "fetch": {"print_pages": PRINT_PAGES, "print_page_limit": PRINT_PAGE_LIMIT, "reach": "complete iff a non-full page is reached (newest-first offset paging)", "max_pairs": P_DATA_MAX_PAIRS,
                      "tx_windows": "[t_birth, t_birth + 25 h] and [t_L - 2 h, t_L + 24 h 30 min]", "candles": "[t_birth - 6 h, t_d + 25 h] and [t_L - 1 h, t_L + 25 h]",
                      "prices_history": "fidelity 10 after t_birth only; points before counted", "volume": "stored apart; opened only by the screen's tercile check",
                      "non_200": "P-5: status-aware candle and prices-history fetches in this module (the shared cross_venue / history_backfill fetchers skip a non-200 silently and are unchanged); any non-200 leaves the pair pending (attempts.jsonl), the run never completes with a pending pair",
                      "terminal_rule": {"P-17": f"a pair with >= {PAIR_FAIL_ATTEMPTS} failed attempts in that many separate runs, first to last >= {PAIR_FAIL_SPAN_S:.0f} s apart, becomes '{UNAVAILABLE_SOURCE}' (counted in labels and denominators; P2 worst case at w*)",
                                         "kalshi_fallback": f"a 404 on the frozen candle endpoint -> ONE try of the other endpoint (live/historical), accepted only if every candle carries {list(CANDLE_FIELDS)}; otherwise the chunk fails"},
                      "chunks": {"candle_chunk_s": K_CANDLE_CHUNK_S, "ph_window_days": PH_WINDOW_DAYS, "ph_fidelity": PH_FIDELITY, "clob_prices": CLOB_PRICES},
                      "shared_parser_sha256": {"cross_venue.parse_k_candles": _src_sha("cross_venue", "parse_k_candles")}},
            "p1": {"floor": P1_FLOOR, "min": P1_MIN, "ways": ["event", "birth_week"], "birth_contrast_p": BIRTH_CONTRAST_P, "paired_boot": {"draws": c15.N_BOOT, "seed": c15.SEED_PAIRED_BOOT},
                   "opening_control": {"p": OPENING_CONTROL_P, "share": OPENING_CONTROL_SHARE}, "tercile_min": TERCILE_MIN, "placebo": {"seed": c15.PLACEBO_SEEDS["P1_shuffle"], "draws": c15.PLACEBO_DRAWS,
                   "max_advance": c15.PLACEBO_MAX_ADVANCE}, "robust": {"kalshi_first_s": KALSHI_FIRST_ROBUST_S, "t_d_s": T_D_ROBUST_S, "stratum_min": STRATUM_MIN}},
            "p2": {"floor": P2_FLOOR, "min": P2_MIN, "gap_min": GAP_MIN, "entry_s": list(ENTRY_WINDOW_S), "exit_s": list(EXIT_WINDOW_S), "entry_robust_s": list(ENTRY_ROBUST_S),
                   "exit_robust_s": list(EXIT_ROBUST_S), "w_star": c15.W_STAR, "fee_floor": c15.FEE_FLOOR, "cost_robust": c15.COST_ROBUST_PER_SIDE},
            "gpp": {"p1_max_mde": GPP_P1_MAX, "p2_max_mde": GPP_P2_MAX, "mult": c15.MDE_MULT, "inflate": c15.MDE_INFLATE, "proxy": "SE only at t_L"},
            "smoke": {"needs": list(SMOKE_NEEDS), "max_requests": SMOKE_MAX_REQUESTS},
            "stage2": {"window": "T15_P2_start = max(P freeze + 1 d, 2026-11-04T00:00Z); stop at >= 60 eligible births with their 24-h read (births, never results); cap 2027-04-30",
                       "listing": {"lookback_s": LISTING_LOOKBACK_S, "every_s": LISTING_SCAN_EVERY_S, "max_pages": LISTING_MAX_PAGES},
                       "kalshi_cache": {"full_every_s": KALSHI_FULL_EVERY_S, "incremental": "min_created_ts, 1 h overlap"},
                       "matcher": "cross_venue.match_markets over the FULL Kalshi open-market cache (C1 mutual best, against the new listings: declared), then each pair's lead is checked (kalshi_first) and the r1 audit_conflict rule applied (flag -> excluded, counted); source sha256 = CB12-X's pinned cross_venue.py",
                       "eligible": "Kalshi-first (open_time <= listing - 24 h), no audit-conflict flag, no rule-boolean difference, Kalshi series category known and not Sports; only eligible pairs are polled",
                       "scheduled_end": "P-16: endDate stored at the match; at the first-print detection a pair with endDate < t_d + 25 h is 'ends early (scheduled)' (no reads, counted, outside the availability denominators); a missing endDate is not an exclusion (counted); a Polymarket 404 at the 24-h read is 'unavailable (no order book at 24 h)': never read as an empty book, counted in the availability denominators, in no estimate",
                       "legs": "P-18: only the legs the analysis uses are required (t_d: Polymarket YES + Kalshi, NO when g_d <= -5c; 24 h: YES, NO when the t_d read put P2 on NO; Kalshi is not read at 24 h)",
                       "cache_cap_rule": "P-25: the 0.25 GB cache cap is NOT changed after any size is seen (the smoke's within_cap projection is informative only). If the projection or the folder exceeds the cap, the cap binds: the cache stops adding pages (stale), this is logged, scans skipped for a stale cache are counted (cache_cap_scans_skipped), new listings with no cached match are counted as '" + UNAVAILABLE_CACHE_CAP + "' (cache_cap_unavailable_upper_bound: an UPPER bound, it also counts listings with no Kalshi counterpart; P-28: listings seen while the cache is stale under the cap are logged without prices, cache_cap_listings_unmatched; when the cap binds it ends enrolment of new pairs, a time-dependent rule, never outcome-dependent) and are never read",
                       "run_gap": "P-23: p-data exits 75 if the previous run that left failed pairs ended < PAIR_FAIL_SPAN_S ago (the queue worker re-starts a repeat run at once); q0349 repeat.max_runs 8 so the terminal rule (3 failing runs + a labelling run) is always reachable",
                       "candle_fallback": "P-24: the other-endpoint fallback needs a NON-EMPTY candlesticks reply with the parser's fields; else the chunk fails (pair pending -> unavailable (source))",
                       "no_side_404": "P-26: a NO-book 404 at 24 h drops the unit from P2 only (P1 uses the YES side only)",
                       "cache_folder": {"subdir": CACHE_SUBDIR, "cap_bytes": CACHE_DIR_CAP_BYTES, "files": CACHE_FILES, "live_cap": "live files <= live cap AND live files + cache folder <= live cap + cache cap (the cache is counted in the total)", "smoke_pages": SMOKE_CACHE_PAGES},
                       "shared_count": "P-19b: the cache writes the daily request count after every page and re-reads the watcher's before every page; the watcher writes after every batch and re-reads the cache's at every check",
                       "cadence": {"watcher": "cron every minute under flock, 55-s timeout: reads first, then eligible first-print polls (5 min), then the hourly listing scan against the cache; soft deadline 35 s", "cache": "separate job and lock (p_cache), hourly cron, 3,000-s timeout, resumable cursor, full pull daily, min_created_ts hourly, starts one day before T15_P2_start", "cache_daily_max": CACHE_DAILY_MAX,
                                   "read_reserve": READ_RESERVE, "read_max_requests": READ_MAX_REQUESTS, "live_dir_cap_bytes": LIVE_DIR_CAP_BYTES, "disk_check_every_s": DISK_CHECK_EVERY_S},
                       "first_print": {"poll_s": FIRST_PRINT_POLL_S, "page": FIRST_PRINT_PAGE, "give_up_s": FIRST_PRINT_GIVE_UP_S, "late": "detection after t_birth + 10 min -> late, excluded and counted"},
                       "reads": {"t_d_lag_s": READ_LAG_TD_S, "t_d_24h_lag_s": READ_LAG_TB_S, "books": "Polymarket YES and NO /book, Kalshi orderbook (YES ask = 1 - best NO bid)",
                                 "window": "a read counts only if due <= receipt <= due + lag (receipt after the response; first in-window read per pair and read); a failed HTTP read is retried inside the window, never stored, and is 'unavailable (read)'; a Polymarket 404 = empty book",
                                 "usable_birth": "stop rule: not late, both reads in their windows"},
                       "audit": {"batches": "weekly, titles only", "verdicts_dir": AUDIT_DIR_REL, "values": list(AUDIT_VALUES), "missing": "pending (the rep waits)"},
                       "daily_request_cap": DAILY_REQUEST_CAP, "rep_min": REP_MIN, "rep_quote": "t_d: Polymarket and Kalshi two-sided, spread <= 10c each (P-13a); t_d + 24 h Polymarket mid by the one-sided-bound rule (no ask -> 1, no bid -> 0), never dropped (P-3)",
                       "rep_availability": "available / eligible < 60% -> not testable (availability) (section 2.6 iv)",
                       "rep_checks": "floor, small-G, top-5 event / week drops (p < 0.01 AND the floor on the kept units), halves, leave-one-quarter-out; P2-rep +1c per side; no bid at t_d + 24 h -> w*",
                       "holm": "one Stage-2 Holm over the triggered tests; early alpha/2; the Holm only adds passes", "freeze_marker": P_FREEZE_MARKER}}


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


# =====================================================================================================================================================
# Stage 2 (q0352 birth watcher, q0353 rep): causal selection, no volume filter, recorded books
# =====================================================================================================================================================

LIVE_RUN = "h15_birth_live"
LIVE_FILES = {"state": "state.json", "series_cat": "series_cat.json", "listings": "listings.jsonl", "pairs": "pairs.jsonl",
              "first_prints": "first_prints.jsonl", "books": "books.jsonl", "gaps": "gaps.jsonl", "audit_dir": "audit_batches", "closed": "closed.json", "heartbeat": "heartbeat.json"}
# P-19: the Kalshi open-market cache has its OWN folder (a subfolder of the live run, allowed by the CB15 output-root rule) and its OWN cap, outside the 0.05 GB live-directory cap.
CACHE_SUBDIR = "kcache"
CACHE_FILES = {"cache": "kalshi_open.jsonl.gz", "partial": "kalshi_partial.jsonl", "state": "cache_state.json", "heartbeat": "cache_heartbeat.json", "gaps": "gaps.jsonl"}
CACHE_DIR_CAP_BYTES = int(0.25 * 1024**3)  # declared before any size is observed; the smoke measures the open-market count and the file sizes (counts only)
SMOKE_CACHE_PAGES = 3
PAIR_FAIL_ATTEMPTS = 3  # P-17: a pair with >= 3 failed q0349 attempts in 3 separate runs ...
PAIR_FAIL_SPAN_S = 15 * MINUTE  # ... spread over >= 15 minutes (first to last) becomes "unavailable (source)"
UNAVAILABLE_SOURCE = "unavailable (source)"
RUN_STAMP = "run_stamp.json"  # P-23: end time of the last p-data run that left failed pairs
UNAVAILABLE_CACHE_CAP = "unavailable (source: cache cap)"  # P-25
POLY_RULE_BOOLEANS = "unknown"  # P-20: Polymarket exposes no is_provisional / can_close_early flag at listing; declared unknown, not False
NO_BOOK_24H = "unavailable (no order book at 24 h)"  # P-16
NO_BOOK_24H_P2 = "ok (P1 only; NO book unavailable at 24 h)"  # P-26 / P-28: exclusive of "ok" (one label per unit; P1-usable, dropped from P2 only)
KALSHI_FLAG_LABEL = "Kalshi early-close/provisional flag (excluded)"  # P-27 (renamed from "rule booleans differ (excluded)")
LISTING_LOOKBACK_S = 2 * HOUR
LISTING_SCAN_EVERY_S = HOUR
LISTING_PAGE = 100
LISTING_MAX_PAGES = 10
KALSHI_FULL_EVERY_S = DAY
KALSHI_INCR_OVERLAP_S = HOUR
KALSHI_PAGE = 1000
KALSHI_MAX_PAGES = 400
FIRST_PRINT_POLL_S = 5 * MINUTE
FIRST_PRINT_PAGE = 500
FIRST_PRINT_GIVE_UP_S = 7 * DAY
READ_LAG_TD_S = 120.0  # the read at t_d: first successful read with receipt >= t_d within 2 min
READ_LAG_TB_S = 300.0  # the read at t_d + 24 h: within 5 min
DAILY_REQUEST_CAP = 3500
READ_MAX_REQUESTS = 3  # P-22: the most requests one recorded read can make (Polymarket YES, Kalshi, Polymarket NO)
READ_RESERVE = 300  # requests of the daily cap kept for the book reads: scans, polls and the cache stop 300 requests before the cap (reads are prioritised)
CACHE_DAILY_MAX = 1800  # the Kalshi cache job's own share of the day
CACHE_BUDGET_S = 2900.0  # one cache invocation (own lock, hourly cron, timeout 3,000 s); resumable by cursor
CACHE_WARMUP_S = DAY  # the cache job starts one day before T15_P2_start (public open-market list only; nothing is read for P)
CACHE_MAX_AGE_S = 4 * HOUR  # a listing scan with an older cache is skipped and logged
LIVE_SOFT_DEADLINE_S = 35.0  # the 55-s watcher starts no optional work (scan, polls) after this
LIVE_DIR_CAP_BYTES = int(0.05 * 1024**3)  # the declared 0.05 GB cap of q0352; over it the watcher takes no new pair (reads continue) and logs it
DISK_CHECK_EVERY_S = HOUR
POLY_NO_BOOK_STATUS = 404  # Polymarket /book answers 404 for a token with no order book: an EMPTY book (a recorded read), not a failed read
STAGE2_BIRTHS_STOP = 60  # T15_P2_end: >= 60 non-sports Kalshi-first births with their 24-h read (births, never results)
REP_MIN = {"P1": 60, "P2": 40}
NOT_RUN_POWER_REP = "not run (power)"
P_FREEZE_MARKER = "cb15-P-freeze"
CV_MODULE_REL = "backend/astrolabe/research_lab/cross_venue.py"
CLOB_BOOK = "https://clob.polymarket.com/book"
AUDIT_DIR_REL = "docs/research_lab/seals/cb15_p_audit"
AUDIT_VALUES = ("pass", "fail")
LIVE_STATUS_CLOSED = "p_live_closed"


def matcher_sha(repo_root: Path | None = None) -> str:
    """sha256 of ``cross_venue.py`` (the frozen matcher ``match_markets`` and the r1 ``audit_conflict`` rule); must equal CB12-X's pinned study source."""
    from . import provenance  # noqa: PLC0415

    return c15.sha256_file((Path(repo_root) if repo_root is not None else provenance.REPO_ROOT) / CV_MODULE_REL)


def verify_matcher(repo_root: Path | None = None) -> str:
    from . import cb12_x  # noqa: PLC0415

    got, want = matcher_sha(repo_root), cb12_x.CV_SOURCE_PINS[CV_MODULE_REL]
    if got != want:
        raise Refused(f"cross_venue.py sha256 {got[:12]} != the pinned matcher {want[:12]}: the frozen matcher changed; refusing")
    return got


def p2_window(freeze_ts: float | None) -> tuple[float, float]:
    """``T15_P2_start = max(P freeze + 1 d, 2026-11-04T00:00Z)``; the cap ``T15_P2_cap = 2027-04-30``."""
    lo = ep(T15_P2_START_MIN)
    if freeze_ts is not None and math.isfinite(freeze_ts):
        lo = max(lo, float(freeze_ts) + DAY)
    return lo, ep(T15_P2_CAP)


def kalshi_record(m: dict) -> dict | None:
    """A whitelisted Kalshi market record for the matcher (``result`` / settlement fields discarded): ticker, event and series tickers, title, yes subtitle, scheduled close, open."""
    m = strip_kalshi(m)
    if not m.get("ticker") or m.get("market_type", "binary") != "binary":
        return None
    ev = str(m.get("event_ticker") or "")
    return {"ticker": str(m["ticker"]), "event_ticker": ev, "series": ev.split("-")[0] if ev else "", "title": str(m.get("title") or ""), "yes_sub": str(m.get("yes_sub_title") or ""),
            "close_time": m.get("close_time"), "open_time": m.get("open_time"), "is_provisional": m.get("is_provisional"), "can_close_early": m.get("can_close_early")}


def poly_listing(m: dict) -> dict | None:
    """A whitelisted Gamma listing (binary Yes/No; outcome fields discarded): matcher fields, ids, tokens, createdAt, fee rate."""
    m = c15.strip_forbidden(m)
    outs = [str(x) for x in c15.c12.listish(m.get("outcomes"))]
    toks = [str(x) for x in c15.c12.listish(m.get("clobTokenIds"))]
    if outs != ["Yes", "No"] or len(toks) != 2 or m.get("id") is None:
        return None
    ev = m.get("events") if isinstance(m.get("events"), list) else []
    eid = str(ev[0].get("id")) if ev and isinstance(ev[0], dict) and ev[0].get("id") is not None else ""
    fs = m.get("feeSchedule") if isinstance(m.get("feeSchedule"), dict) else {}
    from . import cross_venue as cv  # noqa: PLC0415

    return {"market_id": str(m["id"]), "event_id": eid, "question": cv.p_text({"question": m.get("question") or "", "item": m.get("groupItemTitle") or ""}), "outcomes": ["Yes", "No"],
            "end": m.get("endDate"), "created": c15.parse_iso(m.get("createdAt")), "condition_id": str(m.get("conditionId") or ""), "token_yes": toks[0], "token_no": toks[1],
            "fee_rate": c15.num(fs.get("rate"))}


def scan_listings(lim, now: float, *, lookback_s: float = LISTING_LOOKBACK_S, max_pages: int = LISTING_MAX_PAGES) -> tuple[list[dict], dict]:
    """Gamma markets created in the last 2 h (open, newest id first, paged until a page holds a market created before the lookback); a capped scan is logged, never silent."""
    out, pages, capped = [], 0, True
    for page in range(max_pages):
        st, data = lim.get(c15.GAMMA_MARKETS, {"closed": "false", "order": "id", "ascending": "false", "limit": LISTING_PAGE, "offset": page * LISTING_PAGE})
        pages += 1
        if st != 200 or not isinstance(data, list):
            raise ApiError(f"gamma markets status {st}")
        old = False
        for m in data:
            if not isinstance(m, dict):
                continue
            c = c15.parse_iso(m.get("createdAt"))
            if math.isfinite(c) and c < now - lookback_s:
                old = True
                continue
            pl = poly_listing(m)
            if pl is not None and math.isfinite(pl["created"]):
                out.append(pl)
        if old or len(data) < LISTING_PAGE:
            capped = False
            break
    return out, {"pages": pages, "capped": capped}




def kalshi_page(klim, cursor: str | None, min_created_ts: int | None) -> tuple[list[dict], str | None]:
    """One page of open Kalshi markets (``/markets?status=open``, cursor paging; incremental with ``min_created_ts``). Records are whitelisted at parse. A non-200 raises ``ApiError``
    (the cache job keeps its cursor and retries); the returned cursor is None when the listing is exhausted."""
    params: dict = {"status": "open", "limit": KALSHI_PAGE, "mve_filter": "exclude"}
    if min_created_ts is not None:
        params["min_created_ts"] = int(min_created_ts)
    if cursor:
        params["cursor"] = cursor
    st, data = klim.get(f"{KALSHI_API}/markets", params)
    if st != 200 or not isinstance(data, dict):
        raise ApiError(f"kalshi markets status {st}")
    ms = data.get("markets") or []
    recs = [r for r in (kalshi_record(m) for m in ms if isinstance(m, dict)) if r]
    cur = data.get("cursor") or None
    return recs, (cur if ms else None)


def series_category(klim, series: str, cache: dict) -> str:
    """Kalshi series category (cached); unknown on failure (such pairs are excluded and counted: non-sports cannot be verified)."""
    if series in cache:
        return cache[series]
    st, data = klim.get(f"{KALSHI_API}/series/{series}", {})
    cat = str(((data or {}).get("series") or {}).get("category") or "unknown") if st == 200 and isinstance(data, dict) else "unknown"
    cache[series] = cat
    return cat


def match_new(kalshi: list[dict], listings: list[dict]) -> list[dict]:
    """The frozen matcher on the new listings: ``cross_venue.match_markets`` over the FULL Kalshi open-market cache (C1 mutual-best as frozen, P-8), then each pair's own lead is
    checked (``kalshi_first``) and the r1 ``audit_conflict`` rule applied (a flagged pair is dropped from eligibility, counted). Declared (P-21): the mutual-best step is taken over the
    NEW listings (the Kalshi side is the full cache), not the whole Polymarket universe, so a Kalshi market is matched to its best new listing, never compared with older listings. The
    listing's scheduled ``endDate`` is stored (``end_sched``) for the scheduled-end exclusion at the birth (P-16)."""
    from . import cross_venue as cv  # noqa: PLC0415

    if not listings:
        return []
    kb = {k["ticker"]: k for k in kalshi}
    pb = {x["market_id"]: x for x in listings}
    out = []
    for mp in cv.match_markets(list(kb.values()), listings):
        k, p = kb[mp.k_ticker], pb[mp.p_market_id]
        lead = p["created"] - c15.parse_iso(k.get("open_time"))
        flags = cv.audit_conflict(cv.k_text(k), cv.p_text(p))
        out.append({"k_ticker": k["ticker"], "k_series": k["series"], "k_open": c15.parse_iso(k.get("open_time")), "p_market_id": p["market_id"], "p_event_id": p["event_id"],
                    "condition_id": p["condition_id"], "token_yes": p["token_yes"], "token_no": p["token_no"], "listed": p["created"], "fee_rate": p["fee_rate"], "score": mp.score,
                    "end_sched": c15.parse_iso(p.get("end")),
                    "kalshi_first": bool(math.isfinite(lead) and lead >= KALSHI_FIRST_S), "audit_conflict": flags, "k_text": cv.k_text(k), "p_text": p["question"],
                    "rule_booleans_differ": rule_booleans_differ({"k_bool_provisional": k.get("is_provisional"), "k_bool_close_early": k.get("can_close_early")})})
    return out


def first_print_poll(lim, cid: str, yes_index: int = 0) -> tuple[float, str]:
    """One Data API poll (newest first, one page): (time of the first transaction, reach). Only a non-full page reaches the first transaction."""
    from . import history_backfill as hb  # noqa: PLC0415

    st, data = lim.get(hb.DATA_TRADES, {"market": cid, "limit": FIRST_PRINT_PAGE, "offset": 0})
    if st != 200 or not isinstance(data, list):
        raise ApiError(f"trades status {st}")
    if not data:
        return math.nan, "none"
    txs = transactions([{k: x.get(k) for k in ("timestamp", "price", "size", "outcomeIndex", "transactionHash")} for x in data if isinstance(x, dict)], yes_index)
    if len(data) >= FIRST_PRINT_PAGE:
        return math.nan, "uncovered"
    return (float(txs[0]["ts"]), "complete") if txs else (math.nan, "none")


def kalshi_book(data: dict) -> dict:
    """Kalshi orderbook -> YES best bid / ask (ask = 1 - best NO bid); dollars lists preferred, cents otherwise."""
    ob = (data or {}).get("orderbook") or (data or {}).get("orderbook_fp") or {}

    def best(side: str) -> float:
        for key, scale in ((f"{side}_dollars", 1.0), (side, 0.01)):
            lv = ob.get(key)
            if isinstance(lv, list) and lv:
                ps = [c15.num(x[0]) * scale for x in lv if isinstance(x, (list, tuple)) and len(x) >= 2 and c15.num(x[1]) > 0]
                ps = [x for x in ps if math.isfinite(x)]
                if ps:
                    return max(ps)
        return math.nan

    yb, nb = best("yes"), best("no")
    return {"k_bid": yb, "k_ask": (1.0 - nb) if math.isfinite(nb) else math.nan}


def poly_book(data: dict) -> dict:
    bids = [(c15.num(x.get("price")), c15.num(x.get("size"))) for x in ((data or {}).get("bids") or []) if isinstance(x, dict)]
    asks = [(c15.num(x.get("price")), c15.num(x.get("size"))) for x in ((data or {}).get("asks") or []) if isinstance(x, dict)]
    bids = [b for b in bids if math.isfinite(b[0]) and b[1] > 0]
    asks = [a for a in asks if math.isfinite(a[0]) and a[1] > 0]
    bb = max(bids, default=(math.nan, math.nan))
    ba = min(asks, default=(math.nan, math.nan))
    return {"bid": bb[0], "ask": ba[0], "bid_size": bb[1], "ask_size": ba[1]}


def p2_side(read: dict | None) -> str:
    """The side P2-rep trades from a ``t_d`` read: ``no`` iff ``g_d <= -5c`` (both quotes two-sided), else ``yes`` (as ``rep_p2_net``)."""
    if not read:
        return "yes"
    try:
        g = two_sided(read["kalshi"]["k_bid"], read["kalshi"]["k_ask"]) - two_sided(read["yes"]["bid"], read["yes"]["ask"])
    except (KeyError, TypeError):
        return "yes"
    return "no" if math.isfinite(g) and g <= -GAP_MIN else "yes"


def read_books(lim, klim, pair: dict, which: str = "t_d", td_read: dict | None = None) -> dict:
    """One recorded read. Only the legs the analysis USES are required (P-18): at ``t_d`` the Polymarket YES book and the Kalshi orderbook (and the NO book when ``g_d <= -5c``, the
    side P2-rep buys); at ``t_d + 24 h`` the YES book (and the NO book when the ``t_d`` read put P2 on the NO side). Kalshi is not read at 24 h at all (nothing uses it); a leg that is
    not needed is not fetched (statuses ``not requested``). ``http_ok`` is True only if every REQUIRED leg answered 200 (a Polymarket 404 = no order book = an EMPTY book, a recorded
    read, P-1; at 24 h the caller labels a 404 as ``unavailable (no order book at 24 h)``, P-16); any other status or a transport error on a required leg makes the read FAILED: the
    caller never stores it and retries inside the window. ``statuses`` lists the legs."""
    out: dict = {"statuses": {}}
    ok = True

    def poly(side: str, tok: str) -> bool:
        try:
            st, data = lim.get(CLOB_BOOK, {"token_id": tok})
        except (ApiError, RuntimeError):
            st, data = None, None
        out["statuses"][side] = st
        if st == 200 and isinstance(data, dict):
            out[side] = poly_book(data)
            return True
        out[side] = poly_book({})
        return st == POLY_NO_BOOK_STATUS

    ok &= poly("yes", pair["token_yes"])
    if which == "t_d":
        try:
            st, data = klim.get(f"{KALSHI_API}/markets/{pair['k_ticker']}/orderbook", {})
        except (ApiError, RuntimeError):
            st, data = None, None
        out["statuses"]["kalshi"] = st
        if st == 200 and isinstance(data, dict):
            out["kalshi"] = kalshi_book(data)
        else:
            ok = False
            out["kalshi"] = kalshi_book({})
        need_no = p2_side(out) == "no" if ok else False
    else:
        out["statuses"]["kalshi"] = "not requested"
        out["kalshi"] = kalshi_book({})
        need_no = p2_side(td_read) == "no"
    if need_no:
        ok &= poly("no", pair["token_no"])
    else:
        out["statuses"]["no"] = "not requested"
        out["no"] = poly_book({})
    out["http_ok"] = bool(ok)
    return out


def _read_json(p: Path, default):
    return json.loads(Path(p).read_text()) if Path(p).is_file() else default


def _load_cache(p: Path) -> list[dict]:
    if not Path(p).is_file():
        return []
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def _save_cache(p: Path, rows: list[dict]) -> None:
    tmp = Path(str(p) + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    tmp.replace(p)


def _dir_bytes(d: Path, exclude: Path | None = None) -> int:
    """Bytes under ``d`` (the Kalshi cache folder, a subfolder of the live run with its own cap, is excluded from the live-directory cap: P-19)."""
    ex = Path(exclude).resolve() if exclude is not None else None
    return sum(f.stat().st_size for f in Path(d).rglob("*") if f.is_file() and not (ex is not None and ex in f.resolve().parents))


def _day_requests(path: Path, day: str) -> int:
    st = _read_json(path, {})
    return int(st.get("requests_day", 0)) if st.get("day") == day else 0


READ_LAGS = {"t_d": READ_LAG_TD_S, "t_d+24h": READ_LAG_TB_S}


def read_due(birth: dict, which: str) -> float:
    return float(birth["t_birth"]) + T_D_OFFSET_S + (HORIZON_S if which == "t_d+24h" else 0.0)


def valid_reads(live_dir: Path) -> tuple[dict[str, dict[str, dict]], Counter]:
    """The recorded reads that count (P-1, P-11): ``due <= receipt <= due + lag`` (2 min for the ``t_d`` read, 5 min for the 24-h read; ``due`` recomputed from the birth), the FIRST
    in-window read per pair and read. Out-of-window and duplicate reads are counted, never used."""
    births = {b["pair_id"]: b for b in c15.jsonl_iter(Path(live_dir) / LIVE_FILES["first_prints"])}
    out: dict[str, dict[str, dict]] = {}
    labels: Counter = Counter()
    for b in c15.jsonl_iter(Path(live_dir) / LIVE_FILES["books"]):
        bi, which = births.get(b.get("pair_id")), b.get("which")
        if bi is None or which not in READ_LAGS or not math.isfinite(c15.num(bi.get("t_birth"))):
            labels["read without a usable birth (discarded)"] += 1
            continue
        due, rc = read_due(bi, which), c15.num(b.get("receipt"))
        if not (math.isfinite(rc) and due <= rc <= due + READ_LAGS[which]):
            labels["read outside its window (discarded)"] += 1
            continue
        if which in out.setdefault(b["pair_id"], {}):
            labels["duplicate in-window read (first kept)"] += 1
            continue
        out[b["pair_id"]][which] = b
    return out, labels


def births_with_24h_read(live_dir: Path) -> int:
    """The stop rule counts USABLE births (P-9): eligible pairs (non-sports, Kalshi-first, audit-conflict and rule-boolean free), a first print that is not late, and BOTH reads in
    their windows. Births, never results."""
    pairs = {p["pair_id"]: p for p in c15.jsonl_iter(Path(live_dir) / LIVE_FILES["pairs"])}
    births = {b["pair_id"]: b for b in c15.jsonl_iter(Path(live_dir) / LIVE_FILES["first_prints"])}
    reads, _ = valid_reads(live_dir)
    return sum(1 for pid, rd in reads.items() if "t_d" in rd and "t_d+24h" in rd and pairs.get(pid, {}).get("eligible") and not births[pid].get("late") and not births[pid].get("ends_early"))


def p_cache(hist_root: Path, klim, *, now: float, freeze_ts: float | None, budget_s: float = CACHE_BUDGET_S, clock=time.time) -> dict:
    """q0354, ONE invocation of the Kalshi open-market cache job (own lock, hourly cron, never blocks the watcher's reads, P-2). Full pull daily, incremental hourly by
    ``min_created_ts`` (1 h overlap from the previous job's START); resumable by cursor (``cache_state.json`` + ``kalshi_partial.jsonl``): a failed page keeps the cursor and the next
    invocation continues. The cache file is replaced atomically only when a job is complete. Daily share <= 1,800 requests and nothing past the shared cap minus the read reserve."""
    live = c15.require_output_root(Path(hist_root) / LIVE_RUN)
    live.mkdir(parents=True, exist_ok=True)
    cdir = live / CACHE_SUBDIR  # P-19: its own folder and cap
    cdir.mkdir(parents=True, exist_ok=True)
    start, cap = p2_window(freeze_ts)
    hb_path = cdir / CACHE_FILES["heartbeat"]
    if now < start - CACHE_WARMUP_S or now >= cap or (live / LIVE_FILES["closed"]).is_file():
        cm.write_json_atomic(hb_path, {"epoch": now, "utc": cm.iso(now), "status": "idle"})
        return {"status": "p_cache_idle", "complete": False}
    cs_path, partial, cache_p, gp = cdir / CACHE_FILES["state"], cdir / CACHE_FILES["partial"], cdir / CACHE_FILES["cache"], cdir / CACHE_FILES["gaps"]
    cs = _read_json(cs_path, {"last_full": None, "last_incr": None, "job": None, "day": None, "requests_day": 0})
    day = c15.utc_day(now)
    if cs["day"] != day:
        cs.update(day=day, requests_day=0)
    base = cs["requests_day"]
    k0, t0 = klim.requests, clock()

    def room() -> bool:
        # P-4/P-18-style shared count: this job's requests are written to cache_state.json after EVERY page; the watcher's count is re-read from its state before every page.
        mine = base + (klim.requests - k0)
        return mine < CACHE_DAILY_MAX and mine + _day_requests(live / LIVE_FILES["state"], day) < DAILY_REQUEST_CAP - READ_RESERVE

    def disk_room() -> bool:
        if _dir_bytes(cdir) > CACHE_DIR_CAP_BYTES:
            c15.jsonl_append(gp, {"t": now, "why": f"kalshi cache folder over its {CACHE_DIR_CAP_BYTES} byte cap: no further page this invocation (the old cache stays)"})
            return False
        return True

    job = cs.get("job")
    if job is None:
        if cs["last_full"] is None or now - cs["last_full"] >= KALSHI_FULL_EVERY_S:
            job = {"mode": "full", "cursor": None, "pages": 0, "started": now, "min_created_ts": None}
        elif cs["last_incr"] is None or now - cs["last_incr"] >= LISTING_SCAN_EVERY_S:
            job = {"mode": "incr", "cursor": None, "pages": 0, "started": now, "min_created_ts": int(cs["last_incr"] - KALSHI_INCR_OVERLAP_S)}
        else:
            cm.write_json_atomic(hb_path, {"epoch": now, "utc": cm.iso(now), "status": "fresh"})
            return {"status": "p_cache_fresh", "complete": True}
        if partial.exists():
            partial.unlink()
        cs["job"] = job
    out = {"status": "p_cache_in_progress", "complete": False, "mode": job["mode"], "pages": 0}
    done = False
    try:
        while room() and clock() - t0 < budget_s and disk_room():
            recs, cur = kalshi_page(klim, job["cursor"], job["min_created_ts"])
            with open(partial, "a", encoding="utf-8") as fh:
                for r in recs:
                    fh.write(json.dumps(r, sort_keys=True) + "\n")
            job["cursor"], job["pages"] = cur, job["pages"] + 1
            out["pages"] += 1
            cs["job"], cs["requests_day"] = job, base + (klim.requests - k0)
            cm.write_json_atomic(cs_path, cs)  # the shared daily count and the cursor are on disk after every page
            if cur is None:
                done = True
                break
            if job["pages"] >= KALSHI_MAX_PAGES:
                c15.jsonl_append(gp, {"t": now, "why": f"kalshi {job['mode']} pull hit the page cap ({KALSHI_MAX_PAGES}); job discarded"})
                job = None
                break
    except (ApiError, RuntimeError) as exc:
        c15.jsonl_append(gp, {"t": now, "why": f"kalshi cache page failed (job resumes at its cursor): {str(exc)[:100]}"})
    if job is not None and done:
        rows = {r["ticker"]: r for r in (json.loads(x) for x in open(partial, encoding="utf-8") if x.strip())}
        if job["mode"] == "full":
            cache = rows
            cs["last_full"] = job["started"]
        else:
            cache = {r["ticker"]: r for r in _load_cache(cache_p)}
            cache.update(rows)
        _save_cache(cache_p, list(cache.values()))
        cs["last_incr"] = job["started"]
        partial.unlink()
        cs.update(job=None)
        out.update(status="p_cache_complete", complete=True, cached=len(cache))
    elif job is None:
        cs["job"] = None
        if partial.exists():
            partial.unlink()
    cs["requests_day"] = base + (klim.requests - k0)
    cm.write_json_atomic(cs_path, cs)
    cm.write_json_atomic(hb_path, {"epoch": now, "utc": cm.iso(now), "status": out["status"]})
    return out


def _gap(path: Path, rec: dict) -> None:
    c15.jsonl_append(path, rec)


def p_live(hist_root: Path, lim, klim, *, now: float, rules_sha: str, freeze_ts: float | None, clock=time.time, cap_bytes: int = LIVE_DIR_CAP_BYTES) -> dict:
    """q0352, ONE invocation (cron every minute under flock, 55-s timeout). Before ``T15_P2_start``: idle. After the stop (>= 60 USABLE births: not late, both reads in their windows)
    or the cap: closed (write-once). Order of work (P-2): (1) the book reads at ``t_d`` (window 2 min) and ``t_d + 24 h`` (5 min): a read counts only if ``due <= receipt <= due + lag``
    (receipt after the response), a failed HTTP read is never stored and is retried inside the window; (2) first-print polls of the ELIGIBLE pairs only, every 5 min (give up after
    7 d); (3) hourly, the Gamma listing scan against the Kalshi cache (kept fresh by the separate ``p_cache`` job; a missing or stale cache skips the scan and is logged); (4) the
    weekly blind title-audit batch. Never reads ``cross_venue_live/``. The 3,500/day cap is shared with the cache job; scans, polls and the cache stop 300 requests before it so the
    reads keep priority. Over the 0.05 GB cap no new pair is taken (reads continue)."""
    live = c15.require_output_root(Path(hist_root) / LIVE_RUN)
    live.mkdir(parents=True, exist_ok=True)
    start, cap = p2_window(freeze_ts)
    hb_path = live / LIVE_FILES["heartbeat"]
    if now < start:
        cm.write_json_atomic(hb_path, {"epoch": now, "utc": cm.iso(now), "status": f"before T15_P2_start {cm.iso(start)}"})
        return {"status": "p_live_idle", "complete": False, "start": cm.iso(start)}
    closed = _read_json(live / LIVE_FILES["closed"], None)
    if closed is None and (now >= cap or births_with_24h_read(live) >= STAGE2_BIRTHS_STOP):
        closed = {"closed_at": float(now), "by": "cap" if now >= cap else f"stop rule (>= {STAGE2_BIRTHS_STOP} usable births with both reads in their windows; births, never results)",
                  "written_utc": cm.iso(now)}
        cm.write_once_json(live / LIVE_FILES["closed"], closed)
    st = _read_json(live / LIVE_FILES["state"], {"last_scan": None, "day": None, "requests_day": 0, "polls": {}, "reads": {}, "last_log": {}})
    st.setdefault("last_log", {})
    day = c15.utc_day(now)
    if st["day"] != day:
        st.update(day=day, requests_day=0)
    r0, k0, t0 = lim.requests, klim.requests, clock()
    cdir = live / CACHE_SUBDIR
    cstate = cdir / CACHE_FILES["state"]
    base_req = st["requests_day"]
    gp = live / LIVE_FILES["gaps"]

    def mine() -> int:
        return base_req + (lim.requests - r0) + (klim.requests - k0)

    def flush() -> None:
        """The shared daily count is on disk after every batch of requests (the cache job re-reads it before every page)."""
        st["requests_day"] = mine()
        cm.write_json_atomic(live / LIVE_FILES["state"], st)

    def used() -> int:
        return mine() + _day_requests(cstate, day)  # the cache job's count is re-read from its state at every check, never held from the start of the run

    def reads_ok() -> bool:
        return used() + READ_MAX_REQUESTS <= DAILY_REQUEST_CAP  # P-22: a read needs room for ALL its legs (<= 3), so the 3,500 cap is never overshot by a read

    def other_ok() -> bool:
        return used() < DAILY_REQUEST_CAP - READ_RESERVE and clock() - t0 < LIVE_SOFT_DEADLINE_S

    def log_hourly(key: str, rec: dict) -> None:
        if now - (st["last_log"].get(key) or 0.0) >= HOUR:
            st["last_log"][key] = now
            _gap(gp, {"t": now, **rec})

    out = {"status": "p_live_polled", "complete": False, "matched": 0, "births": 0, "reads": 0, "read_failures": 0}
    pairs = {p["pair_id"]: p for p in c15.jsonl_iter(live / LIVE_FILES["pairs"])}
    births = {b["pair_id"]: b for b in c15.jsonl_iter(live / LIVE_FILES["first_prints"])}
    # (1) reads first
    for pid, b in births.items():
        pr = pairs.get(pid)
        if not pr or not pr.get("eligible") or b.get("late") or b.get("ends_early") or not math.isfinite(c15.num(b.get("t_birth"))):
            continue
        for which, lag in READ_LAGS.items():
            key, due = f"{pid}|{which}", read_due(b, which)
            if key in st["reads"]:
                continue
            t = clock()
            if t < due:
                continue
            if t > due + lag:
                st["reads"][key] = "missed"
                _gap(gp, {"t": t, "pair_id": pid, "which": which, "why": "unavailable (read): window missed"})
                continue
            if not reads_ok():
                log_hourly("cap_reads", {"why": "daily request cap reached: reads deferred (window may be missed)"})
                continue
            td_read = valid_reads(live)[0].get(pid, {}).get("t_d") if which == "t_d+24h" else None
            bk = read_books(lim, klim, pr, which, td_read)
            rcpt = clock()
            flush()
            if not bk["http_ok"]:
                out["read_failures"] += 1
                _gap(gp, {"t": rcpt, "pair_id": pid, "which": which, "why": "read failed (HTTP); retried inside the window", "statuses": bk["statuses"]})
                continue
            if rcpt > due + lag:
                st["reads"][key] = "missed"
                _gap(gp, {"t": rcpt, "pair_id": pid, "which": which, "why": "unavailable (read): receipt after the window"})
                continue
            c15.jsonl_append(live / LIVE_FILES["books"], {"pair_id": pid, "which": which, "due": due, "receipt": rcpt, **bk})
            st["reads"][key] = "done"
            out["reads"] += 1
    try:
        # (2) first-print polls: eligible pairs only
        for pid, pr in pairs.items():
            if closed is not None or not pr.get("eligible") or pid in births or not other_ok():
                continue
            last = st["polls"].get(pid)
            if now - pr["matched_at"] > FIRST_PRINT_GIVE_UP_S or (last is not None and now - last < FIRST_PRINT_POLL_S):
                continue
            tb, reach = first_print_poll(lim, pr["condition_id"])
            st["polls"][pid] = now
            flush()
            if reach in ("complete", "uncovered"):
                # P-16: the scheduled-end exclusion, from information available at t_d (the listing's endDate stored at the match; never closedTime): endDate < t_d + 25 h -> no reads
                end = c15.num(pr.get("end_sched"))
                rec = {"pair_id": pid, "t_birth": tb, "reach": reach, "detected": now, "late": bool(not math.isfinite(tb) or now > tb + T_D_OFFSET_S),
                       "ends_early": bool(math.isfinite(tb) and math.isfinite(end) and end < tb + T_D_OFFSET_S + END_MARGIN_S), "end_sched": end if math.isfinite(end) else None}
                c15.jsonl_append(live / LIVE_FILES["first_prints"], rec)
                births[pid] = rec
                out["births"] += 1
        # (3) hourly listing scan against the cache
        if closed is None and other_ok() and (st["last_scan"] is None or now - st["last_scan"] >= LISTING_SCAN_EVERY_S):
            cache_p = cdir / CACHE_FILES["cache"]
            cs = _read_json(cstate, {})
            if _dir_bytes(live, exclude=cdir) > cap_bytes or _dir_bytes(live) > cap_bytes + CACHE_DIR_CAP_BYTES:
                # P-19/P-22: the live files have their cap, and the TOTAL (live files + the Kalshi cache folder) is held to the live cap plus the cache's own cap, so the cache is counted
                log_hourly("disk_cap", {"why": f"live dir over its {cap_bytes} byte cap (cache folder counted in the total, cap + {CACHE_DIR_CAP_BYTES}): no new pair taken (reads continue)"})
            elif not cache_p.is_file() or cs.get("last_incr") is None or now - cs["last_incr"] > CACHE_MAX_AGE_S:
                if _dir_bytes(cdir) > CACHE_DIR_CAP_BYTES:  # P-25: the cap binds (never changed after seeing a size); the cache stopped adding pairs and is stale: counted
                    st["cache_cap_scans_skipped"] = st.get("cache_cap_scans_skipped", 0) + 1
                    # P-28: matching is skipped, but the Polymarket new listings (ids + listing time, no price) are still logged so the affected count is known
                    try:
                        listings_s, _ = scan_listings(lim, now)
                        seen_s = {p["p_market_id"] for p in pairs.values()}
                        logged_s = {x["market_id"] for x in c15.jsonl_iter(live / LIVE_FILES["listings"])}
                        for x in listings_s:
                            if x["market_id"] not in seen_s and x["market_id"] not in logged_s:
                                c15.jsonl_append(live / LIVE_FILES["listings"], {"t": now, "market_id": x["market_id"], "created": x["created"], "cache_cap_stale": True})
                                logged_s.add(x["market_id"])
                                st["cache_cap_listings_unmatched"] = st.get("cache_cap_listings_unmatched", 0) + 1
                    except (ApiError, RuntimeError):
                        pass
                log_hourly("cache_stale", {"why": "kalshi cache missing or older than 4 h: listing scan skipped (the 2-h lookback re-covers the listings)"})
            else:
                cache = _load_cache(cache_p)
                listings, linfo = scan_listings(lim, now)
                if linfo["capped"]:
                    c15.jsonl_append(gp, {"t": now, "why": "listing scan capped", "pages": linfo["pages"]})
                seen = {p["p_market_id"] for p in pairs.values()}
                logged = {x["market_id"] for x in c15.jsonl_iter(live / LIVE_FILES["listings"])}
                new = [x for x in listings if x["market_id"] not in seen]
                logged_before = set(logged)
                for x in new:
                    if x["market_id"] not in logged:
                        c15.jsonl_append(live / LIVE_FILES["listings"], {"t": now, "market_id": x["market_id"], "created": x["created"]})
                        logged.add(x["market_id"])
                cats = _read_json(live / LIVE_FILES["series_cat"], {})
                if _dir_bytes(cdir) > CACHE_DIR_CAP_BYTES:  # P-25: over the cache cap the cache no longer grows: a new listing with no match needs an uncached Kalshi read
                    matched_ids = {m_["p_market_id"] for m_ in match_new(cache, new)}
                    st["cache_cap_unavailable_upper_bound"] = st.get("cache_cap_unavailable_upper_bound", 0) + sum(1 for x in new if x["market_id"] not in matched_ids and x["market_id"] not in logged_before)
                    c15.jsonl_append(gp, {"t": now, "why": f"{UNAVAILABLE_CACHE_CAP}: kalshi cache folder over its cap, listings with no cached match are counted, not read"})
                for mrec in match_new(cache, new):
                    cat = series_category(klim, mrec["k_series"], cats)
                    pid = f"{mrec['k_ticker']}|{mrec['p_market_id']}"
                    elig = bool(mrec["kalshi_first"] and not mrec["audit_conflict"] and not mrec["rule_booleans_differ"] and cat not in (SPORTS_CAT, "unknown"))
                    rec = {**mrec, "pair_id": pid, "k_cat": cat, "matched_at": now, "eligible": elig}
                    if pid not in pairs:
                        c15.jsonl_append(live / LIVE_FILES["pairs"], rec)
                        pairs[pid] = rec
                        out["matched"] += 1
                cm.write_json_atomic(live / LIVE_FILES["series_cat"], cats)
                st["last_scan"] = now
                flush()
        # (4) weekly blind title-audit batches
        week = c15.iso_week_of(now)
        ap = live / LIVE_FILES["audit_dir"]
        ap.mkdir(exist_ok=True)
        prev = sorted({c15.iso_week_of(p["matched_at"]) for p in pairs.values()} - {week})
        for w in prev:
            f = ap / f"{w}.json"
            if not f.exists():
                cm.write_once_json(f, {"week": w, "blind": True, "note": "titles only; no price, book or outcome", "pairs": [{"pair_id": p["pair_id"], "k_text": p["k_text"], "p_text": p["p_text"]}
                                                                                                                         for p in pairs.values() if c15.iso_week_of(p["matched_at"]) == w]})
    except (ApiError, RuntimeError) as exc:
        c15.jsonl_append(gp, {"t": now, "why": f"request failed: {str(exc)[:100]}"})
    flush()
    cm.write_json_atomic(hb_path, {"epoch": now, "utc": cm.iso(now), "status": "closed" if closed else "watching", "rules_sha256": rules_sha})
    if closed is not None:
        out["status"] = LIVE_STATUS_CLOSED
        out["closed"] = closed
    return out


# ---- rep (q0353) ---------------------------------------------------------------------------------------------------------------------------------------


def read_audits(audit_dir: Path, weeks: set[str]) -> dict[str, str]:
    """The science-reviewer verdicts of every weekly batch (``<week>.json`` with ``{"pairs": {pair_id: "pass"|"fail"}}``); a missing week is pending (NotNow)."""
    out: dict[str, str] = {}
    miss = []
    for w in sorted(weeks):
        f = Path(audit_dir) / f"{w}.json"
        if not f.is_file():
            miss.append(w)
            continue
        for pid, v in (json.loads(f.read_text()).get("pairs") or {}).items():
            if v not in AUDIT_VALUES:
                raise Refused(f"audit {f.name}: verdict {v!r} not in {AUDIT_VALUES}")
            out[pid] = v
    if miss:
        raise NotNow(f"title audits pending for weeks {miss}")
    return out


def two_sided(bid: float, ask: float, spread_max: float = K_SPREAD_MAX) -> float:
    if not (math.isfinite(bid) and math.isfinite(ask)) or ask < bid or ask - bid > spread_max + 1e-12:
        return math.nan
    return (bid + ask) / 2.0


def mid_one_sided(bid: float, ask: float) -> float:
    """The mid at the 24-h read WHATEVER the spread, by the declared one-sided-bound rule of CB15-E (no ask -> 1, no bid -> 0; both missing -> 0.5) so that the P1-rep target never
    drops a unit after entry (P-3)."""
    b = bid if math.isfinite(bid) else 0.0
    a = ask if math.isfinite(ask) else 1.0
    return (b + a) / 2.0


def rep_units(live_dir: Path, audits: dict[str, str]) -> tuple[list[dict], dict]:
    """Stage-2 units: eligible pairs (non-sports, Kalshi-first, no audit-conflict flag, no rule-boolean difference), audit pass, not late, both reads recorded IN THEIR WINDOWS
    (``valid_reads``); ``g_d`` = Kalshi mid - Polymarket YES mid at the ``t_d`` read (both two-sided, spread <= 10c, declared P-13a); Delta = YES mid at ``t_d + 24 h`` by the
    one-sided-bound rule - YES mid at ``t_d``. A failed or missed read is "unavailable (read)", an empty or wide book at ``t_d`` is "no two-sided quote at t_d" (separate labels).
    The returned labels also carry ``eligible_for_availability`` (pairs through the audit with a usable birth) for the section 2.6 (iv) availability gate."""
    pairs = {p["pair_id"]: p for p in c15.jsonl_iter(Path(live_dir) / LIVE_FILES["pairs"])}
    births = {b["pair_id"]: b for b in c15.jsonl_iter(Path(live_dir) / LIVE_FILES["first_prints"])}
    reads, rlabels = valid_reads(live_dir)
    labels: Counter = Counter(rlabels)
    units = []
    for pid, pr in sorted(pairs.items()):
        if not pr.get("eligible"):
            labels["not eligible (sports / polymarket first / audit-conflict / Kalshi early-close/provisional flag / unknown category)"] += 1
            continue
        if audits.get(pid) != "pass":
            labels["audit fail" if audits.get(pid) == "fail" else "unaudited"] += 1
            continue
        b = births.get(pid)
        if b is None or not math.isfinite(c15.num(b.get("t_birth"))):
            labels["no first print"] += 1
            continue
        if b.get("ends_early"):
            labels["ends early (scheduled)"] += 1  # P-16: excluded before entry, as in Stage 1 (not in the availability denominators)
            continue
        if b.get("late"):
            labels["late detection"] += 1
            continue
        if not math.isfinite(c15.num(pr.get("end_sched"))):
            labels["scheduled end unknown (not excluded)"] += 1
        labels["eligible for availability"] += 1
        rd = reads.get(pid, {})
        if "t_d" not in rd or "t_d+24h" not in rd:
            labels["unavailable (read)"] += 1
            continue
        a, z = rd["t_d"], rd["t_d+24h"]
        ma = two_sided(a["yes"]["bid"], a["yes"]["ask"])
        mz = mid_one_sided(z["yes"]["bid"], z["yes"]["ask"])
        kd = two_sided(a["kalshi"]["k_bid"], a["kalshi"]["k_ask"])
        if not (math.isfinite(ma) and math.isfinite(kd)):
            labels["no two-sided quote at t_d"] += 1
            continue
        zs = z.get("statuses") or {}
        if zs.get("yes") == POLY_NO_BOOK_STATUS:
            # P-16: a Polymarket 404 at the 24-h read (no order book: the market closed or was emptied) is NOT read as an empty book (no mid is invented): the unit is "unavailable (no
            # order book at 24 h)", it stays in the availability denominators (P1: eligible; P2: the |g_d| >= 5c set, kept with delta = NaN) and is in neither estimate.
            labels[NO_BOOK_24H] += 1
            units.append({"pair_id": pid, "event": pr["p_event_id"] or pid, "t_birth": float(b["t_birth"]), "g_d": kd - ma, "delta": math.nan, "read_a": a, "read_z": z,
                          "fee_rate": c15.num(pr.get("fee_rate")), "unavailable_24h": True})
            continue
        u = {"pair_id": pid, "event": pr["p_event_id"] or pid, "t_birth": float(b["t_birth"]), "g_d": kd - ma, "delta": mz - ma, "read_a": a, "read_z": z, "fee_rate": c15.num(pr.get("fee_rate"))}
        if p2_side(a) == "no" and zs.get("no") == POLY_NO_BOOK_STATUS:
            # P-26: the NO book is used by P2 only; its 404 at 24 h drops the unit from P2 (denominator kept, no estimate) and leaves P1 (YES side only, P-18) untouched
            u["unavailable_24h_p2"] = True
            labels[NO_BOOK_24H_P2] += 1  # P-28: exclusive labels (a unit is counted once)
        else:
            labels["ok"] += 1
        units.append(u)
    return units, dict(labels)


def rep_p2_net(u: dict, extra_per_side: float = 0.0) -> float | None:
    """P2-rep: buy the side toward Kalshi at the recorded best ask of the ``t_d`` read; sell at the recorded best bid of the ``t_d + 24 h`` read (no bid -> w*)."""
    if u.get("unavailable_24h") or u.get("unavailable_24h_p2"):
        return None  # P-16 / P-26: no 24-h book (counted in the availability denominator, in no estimate)
    side = "yes" if u["g_d"] >= GAP_MIN else "no"
    e = u["read_a"][side]["ask"]
    if not math.isfinite(e):
        return None
    x = u["read_z"][side]["bid"]
    if not math.isfinite(x):
        return c15.W_STAR
    return c15.round_trip_net(e, x, c15.taker_rate(u["fee_rate"]), extra_per_side)


def avail(available: int, eligible: int) -> dict:
    return {"available": available, "eligible": eligible, "share": available / eligible if eligible else math.nan, "ok": bool(eligible and available / eligible >= c15.AVAIL_MIN)}


def rep_p(live_dir: Path, audits: dict[str, str], triggered: list[str]) -> dict:
    """q0353: the triggered tests only. P1-rep (slope of the book-mid Delta on g_d; >= 60 pairs; floor 0.30) and P2-rep (|g_d| >= 5c at recorded books; >= 40 units; floor +1.0c;
    binding +1c per side); each with the availability gate (< 60% of eligible -> "not testable (availability)"), the top-5 event / week drops (p < 0.01 AND the floor on the kept units)
    and the halves as sign checks; one Stage-2 Holm over the triggered tests (early alpha / 2 rule; the Holm only adds)."""
    units, labels = rep_units(live_dir, audits)
    cap_st = _read_json(Path(live_dir) / LIVE_FILES["state"], {})  # P-28: the cache-cap counters (state.json) are part of the report
    cache_cap = {k: int(cap_st.get(k, 0)) for k in ("cache_cap_scans_skipped", "cache_cap_listings_unmatched", "cache_cap_unavailable_upper_bound")}
    res: dict[str, dict] = {}
    n_elig = int(labels.get("eligible for availability", 0))
    if "P1" in triggered:
        uu = [u for u in units if math.isfinite(u["delta"])]
        av1 = avail(len(uu), n_elig)
        if len(uu) < REP_MIN["P1"]:
            res["P1"] = nt(NOT_RUN_POWER_REP, n=len(uu), availability=av1)
        elif not av1["ok"]:
            res["P1"] = nt(NOT_TESTABLE_AVAIL, n=len(uu), availability=av1)
        else:
            y, x, ev, tb = np.array([u["delta"] for u in uu]), np.array([u["g_d"] for u in uu]), [u["event"] for u in uu], [u["t_birth"] for u in uu]
            wk = weeks_of(tb)
            m = slope_test(y, x, ev, wk)

            def est1(keep: np.ndarray) -> float:
                keep = np.asarray(keep, bool)
                return c15.wls_coef_pseudo(y[keep], x[keep], event_weights([ev[i] for i in np.flatnonzero(keep)]), 0)[1] if keep.sum() >= 3 else math.nan

            def p1(keep: np.ndarray) -> dict | None:
                idx = np.flatnonzero(np.asarray(keep, bool))
                return slope_test(y[idx], x[idx], [ev[i] for i in idx], [wk[i] for i in idx]) if len(idx) >= 3 else None

            rob = sign_checks(est1, len(uu), ev, wk, tb, m["pv"], p_fn=p1, floor=P1_FLOOR)
            checks = {"floor": bool(math.isfinite(m["est"]) and m["est"] >= P1_FLOOR), "small_g": bool(m.get("small_g_rules_hold", True)), "robustness": all(v["holds"] for v in rob.values()),
                      "availability": av1["ok"]}
            res["P1"] = {"testable": bool(m.get("testable")), "p": float(m["p"] if m.get("testable") else 1.0), "est": m["est"], "n": len(uu), "checks": checks, "robustness": rob, "availability": av1}
    if "P2" in triggered:
        uu = [u for u in units if abs(u["g_d"]) >= GAP_MIN]
        nets = [(u, rep_p2_net(u)) for u in uu]
        nets = [(u, v) for u, v in nets if v is not None]
        av2 = avail(len(nets), len(uu))
        if len(nets) < REP_MIN["P2"]:
            res["P2"] = nt(NOT_RUN_POWER_REP, n=len(nets), availability=av2)
        elif not av2["ok"]:
            res["P2"] = nt(NOT_TESTABLE_AVAIL, n=len(nets), availability=av2)
        else:
            v = np.array([n for _, n in nets])
            ev, tb = [u["event"] for u, _ in nets], [u["t_birth"] for u, _ in nets]
            wk = weeks_of(tb)
            m = mean_test(v, ev, wk)

            def est2(keep: np.ndarray, vv: np.ndarray = v) -> float:
                keep = np.asarray(keep, bool)
                if keep.sum() < 2:
                    return math.nan
                w = event_weights([ev[i] for i in np.flatnonzero(keep)])
                return float(np.sum(vv[keep] * w) / w.sum())

            def p2(keep: np.ndarray) -> dict | None:
                idx = np.flatnonzero(np.asarray(keep, bool))
                return mean_test(v[idx], [ev[i] for i in idx], [wk[i] for i in idx]) if len(idx) >= 2 else None

            vc = np.array([rep_p2_net(u, c15.COST_ROBUST_PER_SIDE) for u, _ in nets], float)
            rob = sign_checks(est2, len(v), ev, wk, tb, m["pv"], p_fn=p2, floor=P2_FLOOR)
            ec = est2(np.ones(len(vc), bool), vc)
            rob["cost_plus_1c_per_side"] = {"est": ec, "holds": bool(math.isfinite(ec) and ec > 0)}
            checks = {"floor": bool(math.isfinite(m["est"]) and m["est"] >= P2_FLOOR), "small_g": bool(m.get("small_g_rules_hold", True)), "robustness": all(r["holds"] for r in rob.values()),
                      "availability": av2["ok"]}
            res["P2"] = {"testable": bool(m.get("testable")), "p": float(m["p"] if m.get("testable") else 1.0), "est": m["est"], "n": len(v), "checks": checks, "robustness": rob, "availability": av2}
    holm = c15.stage2_final({t: (r["p"] if r.get("testable") else None) for t, r in res.items()})
    for t, r in res.items():
        ok = all((r.get("checks") or {"x": False}).values()) and bool(r.get("testable"))
        rej = bool(((holm["tests"] or {}).get(c15.STAGE2_NAMES[t]) or {}).get("reject"))
        r["advance"] = c15.stage2_pass(ok, r.get("p") if r.get("testable") else None, rej)
        r.setdefault("verdict", "advance (Stage 2, recorded books, causal selection)" if r["advance"] else "not replicated at MDE")
        r.pop("pv", None)
    return {**res, "stage2_holm": holm, "labels": labels, "cache_cap": cache_cap, "evidence": "L2 prospective, causal selection, recorded books"}
