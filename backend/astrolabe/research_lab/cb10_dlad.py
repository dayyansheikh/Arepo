# ruff: noqa: E501
"""CB10-D: option-implied anchor for BTC / ETH daily strike ladders (docs/research_lab/CREATIVE_BATCH_10.md CB10-D, 1.2, 1.3, 1.4, 2.1-2.7,
CB10-F q0200 D part / q0202 / q0203 / q0207 D / q0208 / q0210 / q0211).

Frame: Gamma closed markets of the two ladder series walked by one-day ``endDate`` windows at 12:00 ET, the frozen question regex and rule-text flags,
the Gamma field whitelist (``cb10_common.whitelist_market``), the series-date exclusion. Polymarket prices: newest-first Data API prints aggregated by
transaction hash at fetch (YES terms, hash discarded), per-origin rows only (``p`` in ``[t - 30 min, t)``; ``p_reg`` from a SEPARATE earlier
transaction in ``[t - 180 min, t_p - 5 min)``; ``p_alt`` in ``[t - 180 min, t_reg - 5 min)``; the last transaction of any age; counts). Anchor: Deribit
option trades in ``[t - 120 min, t)`` (block, combo and liquidation rows excluded), ``iv / 100``, per-trade moneyness ``ln(K_opt / index_price)``, a
per-expiry WLS linear smile (ATM fallback), total variance interpolated to ``T``, the smile-adjusted digital ``q = Phi(d2) - (S/K) phi(d1) sqrt(tau) b``.
Outcome guard: Gamma ``outcomePrices`` go only to ``outcomes_guarded.csv.gz``; the settlement index only to ``settle_index_guarded.csv.gz``; both are
opened only by ``screen-D`` / ``rep-D``. EXPLORATORY; no edge, calibration or profitability claim.
"""

from __future__ import annotations

import csv
import gzip
import itertools
import json
import math
import re
import time
from collections.abc import Callable, Iterable, Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import cb8_common as cm
from . import cb10_common as c10
from . import history_backfill as hb

Refused = c10.Refused
NotNow = c10.NotNow
DAY = 86400.0
YEAR_S = 365.0 * DAY

# ---- frame (q0202) -------------------------------------------------------------------------------------------------------------------------------
ASSETS = ("BTC", "ETH")
ASSET_OF_NAME = {"Bitcoin": "BTC", "Ethereum": "ETH"}
SERIES_SLUGS = {"BTC": "btc-multi-strikes-weekly", "ETH": "ethereum-multi-strikes-weekly"}
QUESTION_RE = r"^Will the price of (Bitcoin|Ethereum) be above \$([\d,]+) on ([A-Z][a-z]+ \d{1,2})\?$"
FLAG_RES_COMMON = {"binance": r"Binance", "one_minute": r"\b1[ -]minute\b", "noon": r"12:00", "et": r"\bET\b", "close": r"(?i)\bclose\b"}
PAIR_RES = {"BTC": r"BTC/USDT", "ETH": r"ETH/USDT"}
FLAG_SOURCE = ("written 2026-10-17 from the live out-of-window ladders resolving 2026-10-20 12:00 ET (22 markets, 11 per asset, every flag present on every "
               "market; 3 keyless Gamma requests, booleans only)")
D_WINDOW = ("2025-10-01", "2026-10-01")
ORIGIN_LAGS = (5, 2)
OUTCOME_LABELS = ("Yes", "No")
FRAME_RUN = "dlad_frame"
DERIBIT_RUN = "deribit"
FRAME_OUTPUT_CAP_GB = 0.01
DERIBIT_OUTPUT_CAP_GB = 0.02
LIVE_OUTPUT_CAP_GB = 0.01
GAMMA_RPS = 2.0
SERIES_DATE_DAYS = 1
THINNED_SHARE = 0.30

# ---- Polymarket prices -----------------------------------------------------------------------------------------------------------------------------
FRESH_S = 1800
LATENCY_FRESH_S = 600
REG_LOOKBACK_S = 10800
REG_GAP_S = 300
TX6H_S = 21600
PRICE_BAND = (0.05, 0.95)
DATA_LIMIT = 10000
DATA_PAGES = 2  # offset <= 10,000: the newest 20,000 prints are reachable
TAKER_ONLY = "true"

# ---- Deribit -------------------------------------------------------------------------------------------------------------------------------------
DERIBIT_HISTORY = "https://history.deribit.com/api/v2/public/get_last_trades_by_currency_and_time"
DERIBIT_CHART = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
DERIBIT_DVOL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
DERIBIT_SUMMARY = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"
CLOB_BOOK = "https://clob.polymarket.com/book"
DERIBIT_RPS = 2.0
DERIBIT_COUNT = 1000
DERIBIT_MAX_PAGES = 30
ANCHOR_WINDOW_S = 7200
DERIBIT_FETCH_S = 10800  # [t - 180 min, t]: the smile uses [t - 120 min, t); q' needs the index at t_reg >= t - 180 min; the settlement index uses ts <= T
STORE_EXPIRY_MAX_S = 10 * DAY  # trade rows kept with their instrument only for expiries in (t, t + 10 d] (covers T = t + 2 d, t + 5 d, t + 7 d, each +- 3 d)
CHART_CHUNK_DAYS = 60
PERP = {"BTC": "BTC-PERPETUAL", "ETH": "ETH-PERPETUAL"}
RV_DAYS = 7
RV_MIN_RETURNS = 150  # of 167 consecutive hourly returns in [t - 7 d, t) (open item: the design does not state a minimum)
IV_RANGE = (1.0, 400.0)
IV_RANGE_SHARE = 0.99
SMILE_M_MAX = 0.15
SMILE_MIN = 6
SMILE_SIDE_MIN = 2
ATM_M_MAX = 0.05
ATM_MIN = 3
EXPIRY_HOUR_Z = 8
EXPIRY_MAX_S = 3 * DAY
Q_CLIP = (0.001, 0.999)
HAIRCUT_WINDOW = ("2025-07-01", "2025-10-01")
HAIRCUT_TAU_DAYS = 7
FLAG_BLOCK, FLAG_COMBO, FLAG_LIQ = 1, 2, 4
INSTRUMENT_RE = r"^(BTC|ETH)-(\d{1,2})([A-Z]{3})(\d{2})-(\d+(?:d\d+)?)-([CP])$"
MONTHS = {m: i + 1 for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"))}

# ---- tests, gates ----------------------------------------------------------------------------------------------------------------------------------
D1_FLOOR = 0.30
D2_EDGE = 0.04
D2_MIN_SIZE = 5.0
D2_FLOOR = 0.01
FEE_RATE_FLOOR = 0.07
COST_ROBUST = 0.005
SIZE_WEIGHT_CAP = 2000.0
DIRECTIONAL_MIN = 0.04
THIRDS = (("2025-10", "2026-01"), ("2026-02", "2026-05"), ("2026-06", "2026-09"))
GD = {"units": 1500, "dates": 100, "weeks": 30, "asset_share": 0.30, "near_expiry_units": 200}
AVAILABLE_MIN = 0.60
AUDIT_PASS = 0.90
GDP = {"draws": 500, "seed": c10.SEED_GDP, "rho": 0.8, "inflation": 1.2, "z_sum": 2.326 + 0.842, "max_mde": 1.0}
COR_ATTRIB_MAX = 0.9
SOURCE_MIN_ABS_LOGM = 0.005
SOURCE_DISAGREE_MAX = 0.02
STAGE2_DATES = 56
STAGE2_COLLECT_MAX_DAYS = 80
STAGE2_UNAVAILABLE_MAX = 0.20
STAGE2_RECEIPT_S = 600
STAGE2_WRONG_LINE_S = 3000
STAGE2_OUTCOME_GRACE_DAYS = 2

LABEL_TRUNC = "unavailable (source: Data API truncation)"
LABEL_DERIBIT = "unavailable (source: Deribit)"
LABEL_INACTIVE = "inactive (no fresh trade)"
ST_ELIGIBLE, ST_BAND, ST_NEVER, ST_UNDET = "eligible", "out_of_price_band", "never_traded_by_t", "undeterminable (Data API truncation)"

FRAME_COLUMNS = ["market_id", "condition_id", "asset", "strike", "d", "token_yes", "token_no", "yes_idx", "start_epoch", "end_epoch", "neg_risk", "neg_risk_market_id",
                 "event_id", "event_ids", "series_ids", "series_slugs", "fee_rate", "order_min_size", "desc_sha256", "resolution_source"]
OUTCOME_COLUMNS = ["market_id", "d", "outcome_labels", "outcome_prices"]
ORIGIN_COLUMNS = ["market_id", "asset", "d", "lag", "t", "strike", "status", "last_any_ts", "last_any_price", "truncated_for_t", "p", "t_p", "size_p", "p_reg", "t_reg",
                  "p_alt", "t_alt", "p10", "t_p10", "p_reg10", "t_reg10", "n_tx_6h", "oldest_ts", "truncated", "n_tx"]
TRADE_COLUMNS = ["currency", "origin_t", "ts_ms", "instrument", "iv", "index_price", "amount", "flags"]
DORIGIN_COLUMNS = ["currency", "origin_t", "status", "n_rows", "n_range_ok", "n_block", "n_combo", "n_liq", "pages", "range_share"]
BAR_COLUMNS = ["instrument", "o_ms", "open", "close"]
DVOL_COLUMNS = ["currency", "o_ms", "close"]
SETTLE_COLUMNS = ["currency", "d", "T", "ts_ms", "index_price"]
GUARDED_FILES = ("outcomes_guarded.csv.gz", "settle_index_guarded.csv.gz")
GUARDED_ALLOWED_JOBS = ("screen-D", "rep-D")
FORBIDDEN_CENSUS = ("y", "outcome", "outcome_prices", "settle", "settle_index", "s_t", "net", "pnl")


# =====================================================================================================================================
# Clocks and frame
# =====================================================================================================================================


def window_dates(window: tuple[str, str] = D_WINDOW) -> list[str]:
    return c10.days_between(*window)


def origins_of(d: str) -> list[tuple[int, float]]:
    """(lag, t) for the two origins of resolution date ``d``: 12:00 ET on d - 5 and d - 2."""
    return [(lag, c10.noon_et(c10.day_add(d, -lag))) for lag in ORIGIN_LAGS]


def gamma_end_window(d: str) -> tuple[str, str]:
    """endDate window ``[T - 1 min, T + 1 min]`` around ``T = d 12:00 ET`` (16:00Z EDT / 17:00Z EST)."""
    T = c10.noon_et(d)
    f = "%Y-%m-%dT%H:%M:%SZ"
    return datetime.fromtimestamp(T - 60, UTC).strftime(f), datetime.fromtimestamp(T + 60, UTC).strftime(f)


def flag_res(asset: str) -> dict[str, str]:
    return {**FLAG_RES_COMMON, "pair": PAIR_RES[asset]}


def parse_ladder_market(m: dict, d: str) -> tuple[dict | None, str, dict | None]:
    """(frame row, reason, guarded outcome row). Whitelist first (nothing else leaves the raw market), then: question regex, asset, two outcomes
    exactly Yes/No, not neg-risk, every frozen flag in the description, ``startDate <= (d - 5) 12:00 ET``, endDate at ``d`` 12:00 ET."""
    q = str(m.get("question") or "") if isinstance(m, dict) else ""
    mq = re.match(QUESTION_RE, q)
    if not mq:
        return None, "question_re", None
    asset = ASSET_OF_NAME[mq.group(1)]
    w = c10.whitelist_market(m, flag_res=flag_res(asset))
    if w is None:
        return None, "not_binary", None
    if sorted(json.loads(w["outcomes"])) != sorted(OUTCOME_LABELS):
        return None, "outcomes", None
    if w["neg_risk"]:
        return None, "neg_risk", None
    missing = [k for k in flag_res(asset) if not w.get(f"flag_{k}")]
    if missing:
        return None, "flags:" + "+".join(sorted(missing)), None
    T = c10.noon_et(d)
    if not (math.isfinite(w["end_epoch"]) and abs(w["end_epoch"] - T) <= 60):
        return None, "end_not_noon_et", None
    t5 = c10.noon_et(c10.day_add(d, -ORIGIN_LAGS[0]))
    if not (math.isfinite(w["start_epoch"]) and w["start_epoch"] <= t5):
        return None, "listed_after_d_minus_5", None
    strike = float(mq.group(2).replace(",", ""))
    row = {**{k: w[k] for k in w if not k.startswith("flag_")}, "asset": asset, "strike": strike, "d": d}
    return {c: row.get(c, "") for c in FRAME_COLUMNS}, "ok", {**c10.guarded_outcome_prices(m), "d": d}


def frame_day(lim: hb.Limiter, d: str) -> tuple[list[dict], list[dict], dict, list[dict]]:
    """Gamma closed markets with endDate in the day's 12:00 ET window (paged; a capped window is split; a failed request raises). Returns (frame rows,
    guarded outcome rows, reason counts, whitelisted raw rows for the smoke)."""
    from . import cb4_data as c4  # noqa: PLC0415

    a, b = gamma_end_window(d)
    rows, capped, failed = c4._paged_strict(lim, {"closed": "true", "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true"}, hb.GAMMA_OFFSET_CAP)
    if failed or capped:
        raise cm.ApiError(f"Gamma ladder frame {d}: {'failed' if failed else 'capped'}")
    out, outc, why, wl = [], [], {}, []
    for m in rows:
        if not isinstance(m, dict):
            continue
        r, reason, o = parse_ladder_market(m, d)
        why[reason] = why.get(reason, 0) + 1
        if r is None:
            continue
        out.append(r)
        outc.append(o)
        wl.append(c10.whitelist_market(m) or {})
    return out, outc, why, wl


# =====================================================================================================================================
# Series-date exclusion (design 1.3, a declared deviation)
# =====================================================================================================================================


def series_date_lookup(lim: hb.Limiter, ids: list[str], per_request: int = 50) -> tuple[dict[str, dict], int]:
    """Gamma lookup by id (<= 50 per request, ``closed=true`` retry) with a parse guard keeping ONLY id, the resolution date (ET date of ``endDate``)
    and the series ids. Returns ({id: {"d", "series_ids"}}, n missing)."""
    found: dict[str, dict] = {}

    def ask(batch: list[str], closed: bool) -> None:
        params: dict = {"id": list(batch), "limit": per_request}
        if closed:
            params["closed"] = "true"
        st, data = lim.get(hb.GAMMA_MARKETS, params)
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"series-date lookup status {st}")
        for m in data:
            if not isinstance(m, dict) or str(m.get("id")) not in batch:
                continue
            w = c10.whitelist_market(m) if m.get("conditionId") else None
            e = c10._epoch(m.get("endDate"))
            sids = w["series_ids"] if w else ""
            found[str(m["id"])] = {"d": datetime.fromtimestamp(e, c10.ET).date().isoformat() if math.isfinite(e) else "", "series_ids": sids}

    for i in range(0, len(ids), per_request):
        batch = ids[i:i + per_request]
        ask(batch, False)
        miss = [x for x in batch if x not in found]
        if miss:
            ask(miss, True)
    return found, sum(1 for x in ids if x not in found)


def apply_exclusions(frame: list[dict], excl_ids: set[str], excl_keys: dict[str, set[str]], excl_series_dates: dict[str, set[str]]) -> tuple[list[dict], dict]:
    """Drops by market id, event id and ``negRiskMarketID`` (the usual rule) and the SERIES-DATE key (an event is dropped if any excluded market of the
    same series resolves within +-1 day); counts by key type, and the drops the FULL series-key rule would have made (reported beside it)."""
    events: dict[str, list[dict]] = {}
    for r in frame:
        events.setdefault(r["event_id"] or f"m{r['market_id']}", []).append(r)
    n = {"events_in": len(events), "markets_in": len(frame), "id": 0, "event": 0, "neg_risk_market": 0, "series_date": 0, "events_dropped": 0,
         "full_series_rule_events_dropped": 0, "full_series_rule_markets_dropped": 0}
    kept = []
    for _ev, rows in sorted(events.items()):
        why = None
        for r in rows:
            if r["market_id"] in excl_ids:
                why = why or "id"
            elif any(e and e in excl_keys["event"] for e in str(r["event_ids"]).split(";")):
                why = why or "event"
            elif r.get("neg_risk_market_id") and r["neg_risk_market_id"] in excl_keys["neg_risk_market"]:
                why = why or "neg_risk_market"
        if why is None:
            d0 = date.fromisoformat(rows[0]["d"])
            for s in {s for r in rows for s in str(r["series_ids"]).split(";") if s}:
                if any(abs((date.fromisoformat(x) - d0).days) <= SERIES_DATE_DAYS for x in excl_series_dates.get(s, set()) if x):
                    why = "series_date"
                    break
        if any(s and s in excl_keys["series"] for r in rows for s in str(r["series_ids"]).split(";")):
            n["full_series_rule_events_dropped"] += 1
            n["full_series_rule_markets_dropped"] += len(rows)
        if why:
            n[why] += len(rows)
            n["events_dropped"] += 1
            continue
        kept.extend(rows)
    n["markets_kept"] = len(kept)
    n["events_dropped_share"] = n["events_dropped"] / n["events_in"] if n["events_in"] else 0.0
    n["label"] = "population thinned by exclusions" if n["events_dropped_share"] > THINNED_SHARE else None
    return kept, n


# =====================================================================================================================================
# Data API prints -> transactions (YES terms, hash discarded) -> per-origin rows
# =====================================================================================================================================


def aggregate_transactions(prints: Iterable[dict], yes_idx: int) -> list[tuple[float, float, float]]:
    """One row per transaction hash: (time = the latest print time of the hash, YES-terms VWAP, total size). Outcome-``1 - yes_idx`` prints map to
    ``1 - price``. A print without a hash is its own transaction (counted by the caller). The hash is not returned."""
    acc: dict[str, list[float]] = {}
    for i, x in enumerate(prints):
        try:
            ts, idx, price, size = float(x["timestamp"]), int(x["outcomeIndex"]), float(x["price"]), float(x["size"])
        except (KeyError, TypeError, ValueError):
            continue
        if idx not in (0, 1) or not (0.0 <= price <= 1.0) or size <= 0:
            continue
        yp = price if idx == yes_idx else 1.0 - price
        h = str(x.get("transactionHash") or "") or f"nohash:{i}"
        a = acc.setdefault(h, [0.0, 0.0, 0.0])
        a[0] = max(a[0], ts)
        a[1] += yp * size
        a[2] += size
    return sorted((a[0], a[1] / a[2], a[2]) for a in acc.values() if a[2] > 0)


def fetch_market_prints(lim: hb.Limiter, cid: str, *, limit: int = DATA_LIMIT, pages: int = DATA_PAGES) -> tuple[list[dict], dict]:
    """Newest-first ``/trades`` pages (``limit`` 10,000, ``offset`` <= 10,000). ``/trades`` is not windowed by time (probe 10): the caller filters
    locally. ``truncated`` iff the last allowed page is full or the API refuses the deep offset. A non-200 first page raises."""
    rows: list[dict] = []
    info = {"pages": 0, "truncated": False, "n_nohash": 0}
    for page in range(pages):
        st, data = lim.get(hb.DATA_TRADES, {"market": cid, "limit": limit, "offset": page * limit, "takerOnly": TAKER_ONLY})
        if st == 400 and page > 0:
            info["truncated"] = True
            break
        if st != 200 or not isinstance(data, list):
            raise cm.ApiError(f"trades status {st}")
        info["pages"] += 1
        rows.extend(x for x in data if isinstance(x, dict))
        if len(data) < limit:
            break
    else:
        info["truncated"] = True
    info["n_nohash"] = sum(1 for x in rows if not x.get("transactionHash"))
    ts = [float(x["timestamp"]) for x in rows if str(x.get("timestamp", "")).replace(".", "", 1).isdigit()]
    info["oldest_ts"] = min(ts) if ts else math.nan
    info["n_prints"] = len(rows)
    return rows, info


def _last_in(ts: np.ndarray, lo: float, hi: float) -> int | None:
    """Index of the last transaction with ``lo <= ts < hi`` (ts sorted ascending)."""
    j = int(np.searchsorted(ts, hi, side="left")) - 1
    return j if j >= 0 and ts[j] >= lo else None


def origin_row(tx: list[tuple[float, float, float]], t: float, *, oldest_ts: float, truncated: bool) -> dict:
    """Eligibility (last transaction before ``t`` of any age, price band, BEFORE freshness), the truncation flag, and the freshness prices: ``p`` =
    last transaction in ``[t - 30 min, t)``; ``p_reg`` = last transaction in ``[t - 180 min, t_p - 5 min)``; ``p_alt`` = last in ``[t - 180 min,
    t_reg - 5 min)``; latency variant ``p10`` in ``[t - 10 min, t)`` with its own ``p_reg10``. Every condition uses transactions with time < ``t``."""
    ts = np.array([x[0] for x in tx], float)
    pr = np.array([x[1] for x in tx], float)
    sz = np.array([x[2] for x in tx], float)
    out: dict[str, Any] = {c: "" for c in ORIGIN_COLUMNS}
    out.update(oldest_ts=oldest_ts, truncated=int(bool(truncated)), n_tx=int((ts < t).sum()))
    j = _last_in(ts, -math.inf, t)
    if j is None:
        out["status"] = ST_UNDET if truncated else ST_NEVER
        return out
    out.update(last_any_ts=ts[j], last_any_price=pr[j])
    out["status"] = ST_ELIGIBLE if PRICE_BAND[0] <= pr[j] <= PRICE_BAND[1] else ST_BAND
    out["truncated_for_t"] = int(bool(truncated and (t - REG_LOOKBACK_S) < oldest_ts))
    out["n_tx_6h"] = int(((ts >= t - TX6H_S) & (ts < t)).sum())

    def fresh(window_s: float) -> tuple[int | None, int | None]:
        a = _last_in(ts, t - window_s, t)
        b = _last_in(ts, t - REG_LOOKBACK_S, ts[a] - REG_GAP_S) if a is not None else None
        return a, b

    a, b = fresh(FRESH_S)
    if a is not None:
        out.update(p=pr[a], t_p=ts[a], size_p=sz[a])
    if b is not None:
        out.update(p_reg=pr[b], t_reg=ts[b])
        c = _last_in(ts, t - REG_LOOKBACK_S, ts[b] - REG_GAP_S)
        if c is not None:
            out.update(p_alt=pr[c], t_alt=ts[c])
    a10, b10 = fresh(LATENCY_FRESH_S)
    if a10 is not None:
        out.update(p10=pr[a10], t_p10=ts[a10])
    if b10 is not None:
        out.update(p_reg10=pr[b10], t_reg10=ts[b10])
    return out


# =====================================================================================================================================
# Deribit: trades, bars, DVOL (keyless; <= 2 rps)
# =====================================================================================================================================


def parse_trade(x: Any) -> dict | None:
    """Trade fields kept: timestamp (ms), instrument, iv (PERCENT, as Deribit reports it), index_price, amount, and the block / combo / liquidation
    flags (presence of ``block_trade_id``, ``combo_id`` or ``combo_trade_id``; a ``liquidation`` value other than empty / none)."""
    if not isinstance(x, dict):
        return None
    try:
        ts = int(x["timestamp"])
        inst = str(x["instrument_name"])
    except (KeyError, TypeError, ValueError):
        return None
    flags = (FLAG_BLOCK if x.get("block_trade_id") else 0) | (FLAG_COMBO if (x.get("combo_id") or x.get("combo_trade_id")) else 0)
    liq = x.get("liquidation")
    if liq not in (None, "", "none", False):
        flags |= FLAG_LIQ
    return {"ts_ms": ts, "instrument": inst, "iv": c10._num(x.get("iv")), "index_price": c10._num(x.get("index_price")), "amount": c10._num(x.get("amount")),
            "flags": flags, "trade_id": str(x.get("trade_id") or "")}


def deribit_trades(lim: hb.Limiter, currency: str, start_ms: int, end_ms: int, *, count: int = DERIBIT_COUNT, max_pages: int = DERIBIT_MAX_PAGES) -> tuple[list[dict], dict]:
    """Option trades of ``currency`` with ``start_ms <= timestamp <= end_ms`` from the keyless history endpoint, ascending, paged by ``has_more``
    (next page starts at the last timestamp; duplicates by ``trade_id`` dropped). A non-200 reply or a page that cannot advance raises."""
    out: dict[str, dict] = {}
    info = {"pages": 0, "dup": 0, "malformed": 0}
    start = int(start_ms)
    for _ in range(max_pages):
        st, doc = lim.get(DERIBIT_HISTORY, {"currency": currency, "kind": "option", "start_timestamp": start, "end_timestamp": int(end_ms), "count": count,
                                            "sorting": "asc"})
        res = doc.get("result") if isinstance(doc, dict) else None
        if st != 200 or not isinstance(res, dict) or not isinstance(res.get("trades"), list):
            raise cm.ApiError(f"deribit history status {st}")
        info["pages"] += 1
        last = start
        for x in res["trades"]:
            r = parse_trade(x)
            if r is None:
                info["malformed"] += 1
                continue
            key = r["trade_id"] or f"{r['ts_ms']}|{r['instrument']}|{r['amount']}|{r['iv']}"
            if key in out:
                info["dup"] += 1
                continue
            out[key] = r
            last = max(last, r["ts_ms"])
        if not res.get("has_more"):
            return sorted(out.values(), key=lambda r: (r["ts_ms"], r["trade_id"])), info
        if last <= start:
            raise cm.ApiError("deribit history paging cannot advance (one millisecond holds a full page)")
        start = last
    raise cm.ApiError("deribit history: page cap reached")


def range_ok(r: dict) -> bool:
    return bool(IV_RANGE[0] <= r["iv"] <= IV_RANGE[1] and r["index_price"] > 0)


def parse_instrument(name: str) -> dict | None:
    m = re.match(INSTRUMENT_RE, str(name))
    if not m:
        return None
    mon = MONTHS.get(m.group(3))
    if mon is None:
        return None
    try:
        e = datetime(2000 + int(m.group(4)), mon, int(m.group(2)), EXPIRY_HOUR_Z, tzinfo=UTC).timestamp()
    except ValueError:
        return None
    return {"asset": m.group(1), "expiry": e, "strike": float(m.group(5).replace("d", ".")), "cp": m.group(6)}


def origin_trade_rows(currency: str, t: float, trades: list[dict]) -> tuple[list[list], dict, dict | None]:
    """Stored rows of one origin fetch ``[t - 180 min, t]``: rows with ts < t; the instrument is kept only for ts >= t - 120 min and expiry in
    ``(t, t + 10 d]`` (otherwise an index-only row). Returns (rows, origin status counts, settlement row = the last trade at or before ``t`` for the
    guarded file when ``t`` is a resolution time)."""
    t_ms = int(round(t * 1000))
    rows = []
    n = {"n_rows": 0, "n_range_ok": 0, "n_block": 0, "n_combo": 0, "n_liq": 0}
    settle = None
    for r in trades:
        if r["ts_ms"] <= t_ms and r["index_price"] > 0:
            settle = r
        if r["ts_ms"] >= t_ms or r["ts_ms"] < t_ms - DERIBIT_FETCH_S * 1000:
            continue
        n["n_rows"] += 1
        n["n_range_ok"] += int(range_ok(r))
        n["n_block"] += int(bool(r["flags"] & FLAG_BLOCK))
        n["n_combo"] += int(bool(r["flags"] & FLAG_COMBO))
        n["n_liq"] += int(bool(r["flags"] & FLAG_LIQ))
        ins = parse_instrument(r["instrument"])
        keep = r["ts_ms"] >= t_ms - ANCHOR_WINDOW_S * 1000 and ins is not None and t < ins["expiry"] <= t + STORE_EXPIRY_MAX_S
        rows.append([currency, int(t), r["ts_ms"], r["instrument"] if keep else "", r["iv"] if keep else "", r["index_price"], r["amount"] if keep else "",
                     r["flags"] if keep else ""])
    n["range_share"] = n["n_range_ok"] / n["n_rows"] if n["n_rows"] else 0.0
    return rows, n, ({"ts_ms": settle["ts_ms"], "index_price": settle["index_price"]} if settle else None)


def chart_bars(lim: hb.Limiter, instrument: str, start_ms: int, end_ms: int) -> list[tuple[int, float, float]]:
    st, doc = lim.get(DERIBIT_CHART, {"instrument_name": instrument, "start_timestamp": int(start_ms), "end_timestamp": int(end_ms), "resolution": "60"})
    res = doc.get("result") if isinstance(doc, dict) else None
    if st != 200 or not isinstance(res, dict) or res.get("status") not in ("ok", "no_data"):
        raise cm.ApiError(f"deribit chart status {st}")
    ticks, op, cl = res.get("ticks") or [], res.get("open") or [], res.get("close") or []
    return [(int(a), float(b), float(c)) for a, b, c in zip(ticks, op, cl, strict=False)]


def dvol_rows(lim: hb.Limiter, currency: str, start_ms: int, end_ms: int, max_pages: int = 40) -> list[tuple[int, float]]:
    out: dict[int, float] = {}
    end = int(end_ms)
    for _ in range(max_pages):
        st, doc = lim.get(DERIBIT_DVOL, {"currency": currency, "start_timestamp": int(start_ms), "end_timestamp": end, "resolution": "3600"})
        res = doc.get("result") if isinstance(doc, dict) else None
        if st != 200 or not isinstance(res, dict):
            raise cm.ApiError(f"deribit dvol status {st}")
        for row in res.get("data") or []:
            out[int(row[0])] = float(row[4])
        cont = res.get("continuation")
        if not cont or int(cont) >= end:
            break
        end = int(cont)
    return sorted(out.items())


# =====================================================================================================================================
# Anchor: smile per expiry, interpolation, digital
# =====================================================================================================================================


def phi(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def Phi(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def digital(S: float, K: float, sigma: float, tau: float, b: float) -> float:
    """Undiscounted digital ``-dC/dK`` with zero rates and forward = S on a linear smile ``sigma(m) = a + b m``, ``m = ln(K/S)``:
    ``Phi(d2) - (S/K) phi(d1) sqrt(tau) b``, clipped to [0.001, 0.999]."""
    if not (S > 0 and K > 0 and sigma > 0 and tau > 0):
        return math.nan
    sq = sigma * math.sqrt(tau)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * tau) / sq
    d2 = d1 - sq
    q = Phi(d2) - (S / K) * phi(d1) * math.sqrt(tau) * b
    return min(max(q, Q_CLIP[0]), Q_CLIP[1])


def bs_call(S: float, K: float, sigma: float, tau: float) -> float:
    sq = sigma * math.sqrt(tau)
    d1 = (math.log(S / K) + 0.5 * sigma * sigma * tau) / sq
    return S * Phi(d1) - K * Phi(d1 - sq)


def usable_trades(rows: list[dict], t: float, *, include_flagged: bool = False) -> list[dict]:
    """Trades with an instrument and ``ts`` in ``[t - 120 min, t)``, range-checked (1 <= iv <= 400, index > 0); block / combo / liquidation rows
    excluded unless ``include_flagged`` (reported variant)."""
    t_ms = t * 1000
    out = []
    for r in rows:
        if not r.get("instrument") or not (t_ms - ANCHOR_WINDOW_S * 1000 <= r["ts_ms"] < t_ms):
            continue
        if not range_ok(r) or (r["flags"] and not include_flagged):
            continue
        ins = parse_instrument(r["instrument"])
        if ins is None:
            continue
        out.append({**r, **ins, "m": math.log(ins["strike"] / r["index_price"]), "iv_dec": r["iv"] / 100.0})
    return out


def smile_fit(trades: list[dict]) -> dict:
    """Per expiry: WLS of ``iv_dec`` on ``m`` over trades with ``|m| <= 0.15``, weights = amount, needs >= 6 trades with >= 2 at m < 0 and >= 2 at
    m > 0 (m = 0 counts on neither side) -> ``sigma(m) = a + b m``; else ATM fallback (median iv_dec of ``|m| <= 0.05`` trades, >= 3, ``b = 0``);
    else unusable."""
    sel = [x for x in trades if abs(x["m"]) <= SMILE_M_MAX and x["amount"] > 0]
    neg, pos = sum(1 for x in sel if x["m"] < 0), sum(1 for x in sel if x["m"] > 0)
    if len(sel) >= SMILE_MIN and neg >= SMILE_SIDE_MIN and pos >= SMILE_SIDE_MIN:
        m = np.array([x["m"] for x in sel])
        v = np.array([x["iv_dec"] for x in sel])
        w = np.array([x["amount"] for x in sel])
        mw, vw = (w * m).sum() / w.sum(), (w * v).sum() / w.sum()
        sxx = float((w * (m - mw) ** 2).sum())
        if sxx > 0:
            b = float((w * (m - mw) * (v - vw)).sum() / sxx)
            return {"kind": "smile", "a": float(vw - b * mw), "b": b, "n": len(sel)}
    atm = [x["iv_dec"] for x in trades if abs(x["m"]) <= ATM_M_MAX]
    if len(atm) >= ATM_MIN:
        return {"kind": "atm", "a": float(np.median(atm)), "b": 0.0, "n": len(atm)}
    return {"kind": None, "n": len(sel)}


def expiry_fits(trades: list[dict]) -> dict[float, dict]:
    by: dict[float, list[dict]] = {}
    for x in trades:
        by.setdefault(x["expiry"], []).append(x)
    return {e: smile_fit(v) for e, v in sorted(by.items())}


def anchor_q(fits: dict[float, dict], S: float, K: float, t: float, T: float, *, flat: bool = False, sigma_scale: float = 1.0) -> dict:
    """Digital at strike ``K`` for resolution ``T`` from usable expiry fits: nearest usable ``e1 <= T < e2`` both within 3 days of ``T`` and after
    ``t``; total variance ``sigma_e(m_K)^2 tau_e`` and ``b`` interpolated linearly in time; one side only -> flat sigma and b from that expiry; none
    -> unavailable. ``flat`` = flat-smile variant (sigma_e = a_e, b = 0); ``sigma_scale`` = the reported haircut variant."""
    tau_T = (T - t) / YEAR_S
    if not (S > 0 and tau_T > 0):
        return {"status": "no_spot", "q": math.nan}
    mk = math.log(K / S)
    ok = {e: f for e, f in fits.items() if f.get("kind") and e > t and abs(e - T) <= EXPIRY_MAX_S}
    lo = [e for e in ok if e <= T]
    hi = [e for e in ok if e > T]
    e1, e2 = (max(lo) if lo else None), (min(hi) if hi else None)
    if e1 is None and e2 is None:
        return {"status": "no_expiry_within_3d", "q": math.nan}

    def sb(e: float) -> tuple[float, float]:
        f = ok[e]
        return (f["a"], 0.0) if flat else (f["a"] + f["b"] * mk, f["b"])

    kinds = [ok[e]["kind"] for e in (e1, e2) if e is not None]
    if e1 is not None and e2 is not None:
        (s1, b1), (s2, b2) = sb(e1), sb(e2)
        if s1 <= 0 or s2 <= 0:
            return {"status": "nonpositive_sigma", "q": math.nan}
        t1, t2 = (e1 - t) / YEAR_S, (e2 - t) / YEAR_S
        lam = (tau_T - t1) / (t2 - t1)
        w = s1 * s1 * t1 + (s2 * s2 * t2 - s1 * s1 * t1) * lam
        b = b1 + (b2 - b1) * lam
        if w <= 0:
            return {"status": "nonpositive_variance", "q": math.nan}
        sigma = math.sqrt(w / tau_T)
    else:
        e = e1 if e1 is not None else e2
        sigma, b = sb(e)
        if sigma <= 0:
            return {"status": "nonpositive_sigma", "q": math.nan}
    sigma *= sigma_scale
    dist = min(abs(e - T) for e in (e1, e2) if e is not None)
    return {"status": "ok", "q": digital(S, K, sigma, tau_T, b), "sigma": sigma, "b": b, "sides": 2 if (e1 is not None and e2 is not None) else 1,
            "fit_kinds": kinds, "expiry_dist_s": dist}


def last_index(rows: list[dict], t_ms: float, *, require_instrument: bool = False) -> float:
    """``index_price`` of the last trade row at or before ``t_ms`` (any row, range-checked index > 0)."""
    best = None
    for r in rows:
        if r["ts_ms"] <= t_ms and r["index_price"] > 0 and (r.get("instrument") or not require_instrument):
            if best is None or r["ts_ms"] >= best["ts_ms"]:
                best = r
    return best["index_price"] if best else math.nan


def spot_at_origin(rows: list[dict], t: float) -> float:
    """``S`` = ``index_price`` of the last REMAINING (usable, unflagged) trade before ``t``."""
    u = usable_trades(rows, t)
    return u[-1]["index_price"] if u else math.nan


def rv_sigma(bars: list[tuple[int, float, float]], t: float) -> float:
    """Annualised 7-day realised volatility of the perpetual's consecutive hourly log returns (closes) over bars with ``o >= t - 7 d`` and ``o + 1 h
    <= t``; ``sqrt(8760)`` scaling; needs >= 150 returns (else NaN)."""
    t_ms = t * 1000
    sel = [b for b in bars if b[0] >= t_ms - RV_DAYS * DAY * 1000 and b[0] + 3_600_000 <= t_ms and b[2] > 0]
    sel.sort()
    r = [math.log(sel[i][2] / sel[i - 1][2]) for i in range(1, len(sel)) if sel[i][0] - sel[i - 1][0] == 3_600_000]
    if len(r) < RV_MIN_RETURNS:
        return math.nan
    return float(np.std(r, ddof=1) * math.sqrt(24 * 365))


def dvol_sigma(dvol: list[tuple[int, float]], t: float) -> float:
    t_ms = t * 1000
    sel = [c for o, c in dvol if o + 3_600_000 <= t_ms]
    return sel[-1] / 100.0 if sel else math.nan


def haircut_h(samples: list[tuple[float, float]]) -> dict:
    """Reported variant only: ``h = 1 - median(RV_7d / ATM IV_7d)`` over the pre-window sample points (Deribit data in [2025-07-01, 2025-10-01) only;
    both assets pooled; open item). ``samples`` = [(rv, atm_iv)]."""
    ratios = [rv / iv for rv, iv in samples if math.isfinite(rv) and math.isfinite(iv) and iv > 0]
    return {"n": len(ratios), "h": float(1 - np.median(ratios)) if ratios else math.nan}


# =====================================================================================================================================
# Guarded files
# =====================================================================================================================================


def open_guarded(path: Path, job: str) -> list[dict]:
    """Guarded files (outcomes, settlement index) are opened ONLY by screen-D / rep-D (the caller checked the freeze)."""
    from . import cb7_common as c7  # noqa: PLC0415

    p = Path(path)
    if p.name not in GUARDED_FILES:
        raise Refused(f"{p.name} is not a guarded file")
    if job not in GUARDED_ALLOWED_JOBS:
        raise Refused(f"guarded file {p.name} may be opened only by {GUARDED_ALLOWED_JOBS}, not {job!r}")
    return list(c7.read_csv_gz(p))


def outcome_y(labels: list[str], prices: list) -> float | None:
    """YES settlement value from the guarded Gamma outcome (0.5 on a 50-50); None if unresolved or malformed."""
    try:
        y = float(prices[[str(x) for x in labels].index("Yes")])
    except (ValueError, IndexError, TypeError):
        return None
    return y if y in (0.0, 0.5, 1.0) else None


# =====================================================================================================================================
# q0202 / q0203 runners (resumable)
# =====================================================================================================================================


def _manifest_done(rdir: Path, statuses: tuple[str, ...]) -> dict | None:
    mp = Path(rdir) / "manifest.json"
    prior = json.loads(mp.read_text()) if mp.exists() else {}
    if prior.get("complete") is True and prior.get("stopped") is None and prior.get("status") in statuses:
        return prior
    return None


def _in_progress(fr: cm.Cb8Run, why: str) -> dict:
    m = fr.manifest(why, {"transient": True})
    m["status"] = "in_progress"
    return m


def dlad_frame(root: Path, transport, *, rules_sha: str, smoke_path: Path, exclusion_keys_path: Path, now: float, rps: float = GAMMA_RPS,
               disk_cap: int = int(FRAME_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None,
               wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
               data_dumps_cap_gb: float = c10.DATA_DUMPS_CAP_GB, free_fn=None, window: tuple[str, str] = D_WINDOW, t_seal_epoch: float = c10.T_SEAL_EPOCH) -> dict:
    """q0202, one resumable chunk: the frame per resolution date (resumable by date), the series-date exclusion (light Gamma lookup of excluded ids
    of the ladder series), then per market the newest-first prints -> per-origin rows (one market in memory at a time). Outcomes to the guarded file."""
    from . import cb6_tail as c6  # noqa: PLC0415

    c10.require_after_t_seal(now, "dlad-frame", t_seal_epoch)
    root = c10.refuse_path(Path(root))
    rdir = root / FRAME_RUN
    st = c10.stall_of(rdir)
    if st:
        return st
    done = _manifest_done(rdir, ("dlad_frame_complete",))
    if done:
        return {"stopped": None, "status": done["status"], "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    bad = smoke_failures(smoke_path, ("ladder_frame", "live_flags", "data_api_paging", "tx_aggregation", "whitelist"))
    if bad:
        return c10.write_stall(rdir, c10.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    ids, keys, krep, ksha = c10.load_exclusion_keys(Path(exclusion_keys_path))
    if krep.get("disjointness") == c10.UNVERIFIED:
        return c10.write_stall(rdir, c10.STALL_DISJOINTNESS, "q0201: > 2% of exclusion ids without metadata (design 1.3)")
    c10.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(root, FRAME_RUN, transport, allowed_run_id=FRAME_RUN, kind="cb10_dlad_frame", label="CB10-D frame",
                     params={"window": list(window), "exclusion_keys_sha256": ksha, "evidence_role": c10.EVIDENCE_ROLE_HIST}, rules_sha=rules_sha, key_fp="",
                     disk_cap=disk_cap, rps=min(rps, GAMMA_RPS), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check)
    try:
        pf = rdir / "frame_partial.jsonl.gz"
        have = {rec["d"] for rec in c6.iter_partial(pf)}
        for d in window_dates(window):
            if d in have:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return _in_progress(fr, why)
            try:
                rows, outc, reasons, _ = frame_day(fr.lim, d)
            except (cm.ApiError, RuntimeError) as exc:
                return _in_progress(fr, f"frame_day_failed {d}: {exc}"[:200])
            from . import cb7_common as c7  # noqa: PLC0415

            c7.append_member(fr, pf, {"d": d, "rows": rows, "outcomes": outc, "reasons": reasons})
        recs = list(c6.iter_partial(pf))
        frame = [r for rec in recs for r in rec["rows"]]
        if not (rdir / "series_dates.json").exists():
            ladder_series = {s for r in frame for s in str(r["series_ids"]).split(";") if s}
            cand = sorted(r["market_id"] for r in c10.key_rows(Path(exclusion_keys_path))
                          if any(s in ladder_series for s in str(r.get("series_ids") or "").split(";") if s))
            try:
                found, n_missing = series_date_lookup(fr.lim, cand)
            except (cm.ApiError, RuntimeError) as exc:
                return _in_progress(fr, f"series_date_lookup_failed: {exc}"[:200])
            sd: dict[str, list[str]] = {}
            for v in found.values():
                for s in str(v["series_ids"]).split(";"):
                    if s in ladder_series and v["d"]:
                        sd.setdefault(s, []).append(v["d"])
            doc = {"ladder_series_ids": sorted(ladder_series), "n_candidates": len(cand), "n_missing": n_missing,
                   "missing_share": n_missing / len(cand) if cand else 0.0, "series_dates": {k: sorted(set(v)) for k, v in sorted(sd.items())}}
            fr.budget.write(rdir / "series_dates.json", json.dumps(doc, indent=1, sort_keys=True).encode())
        sdoc = json.loads((rdir / "series_dates.json").read_text())
        kept, drops = apply_exclusions(frame, ids, keys, {k: set(v) for k, v in sdoc["series_dates"].items()})
        drops["series_date_lookup"] = {k: sdoc[k] for k in ("n_candidates", "n_missing", "missing_share")}
        sd_unverified = sdoc["missing_share"] > c10.MAX_UNVERIFIED_KEY_SHARE
        op = rdir / "origins_partial.jsonl.gz"
        done_m = {rec["market_id"] for rec in c6.iter_partial(op)}
        for r in sorted(kept, key=lambda x: (x["d"], x["market_id"])):
            if r["market_id"] in done_m:
                continue
            why = fr.stop_reason(should_stop)
            if why:
                return _in_progress(fr, why)
            try:
                prints, info = fetch_market_prints(fr.lim, r["condition_id"])
            except (cm.ApiError, RuntimeError) as exc:
                return _in_progress(fr, f"prints_failed {r['market_id']}: {exc}"[:200])
            tx = aggregate_transactions(prints, int(r["yes_idx"]))
            del prints
            orows = []
            for lag, t in origins_of(r["d"]):
                o = origin_row(tx, t, oldest_ts=info["oldest_ts"], truncated=info["truncated"])
                o.update(market_id=r["market_id"], asset=r["asset"], d=r["d"], lag=lag, t=t, strike=r["strike"])
                orows.append([o[c] for c in ORIGIN_COLUMNS])
            from . import cb7_common as c7  # noqa: PLC0415

            c7.append_member(fr, op, {"market_id": r["market_id"], "rows": orows, "info": {k: info[k] for k in ("pages", "truncated", "n_nohash", "n_prints")}})
            fr.counts["markets_done"] = fr.counts.get("markets_done", 0) + 1
        oprec = list(c6.iter_partial(op))
        outcomes = [o for rec in recs for o in rec["outcomes"] if o["market_id"] in {r["market_id"] for r in kept}]
        reasons: dict[str, int] = {}
        for rec in recs:
            for k, v in rec["reasons"].items():
                reasons[k] = reasons.get(k, 0) + v
        fr.budget.write_gz_csv(rdir / "frame_all.csv.gz", FRAME_COLUMNS, ([r[c] for c in FRAME_COLUMNS] for r in frame))
        fr.budget.write_gz_csv(rdir / "frame.csv.gz", FRAME_COLUMNS, ([r[c] for c in FRAME_COLUMNS] for r in kept))
        fr.budget.write_gz_csv(rdir / "origins.csv.gz", ORIGIN_COLUMNS, (row for rec in oprec for row in rec["rows"]))
        fr.budget.write_gz_csv(rdir / "outcomes_guarded.csv.gz", OUTCOME_COLUMNS, ([o[c] for c in OUTCOME_COLUMNS] for o in outcomes))
        for name in ("frame_all.csv.gz", "frame.csv.gz", "origins.csv.gz", "outcomes_guarded.csv.gz", "series_dates.json"):
            fr.record_file(rdir / name)
        pinfo = {"truncated_markets": sum(1 for rec in oprec if rec["info"]["truncated"]), "n_nohash": sum(rec["info"]["n_nohash"] for rec in oprec),
                 "markets": len(oprec)}
        pf.unlink(missing_ok=True)
        op.unlink(missing_ok=True)
        fr.counts.update(frame=len(frame), kept=len(kept), origins=2 * len(oprec))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": "dlad_frame_complete", "reasons": reasons, "drops": drops, "prints": pinfo,
                           "series_date_disjointness": c10.UNVERIFIED if sd_unverified else "verified"})
    m["status"] = "dlad_frame_complete"
    if sd_unverified:  # files kept (hashed) for the record; the chain stalls: D1 not testable (disjointness unverified), counted
        return c10.write_stall(rdir, c10.STALL_DISJOINTNESS, f"series-date lookup: {sdoc['n_missing']} of {sdoc['n_candidates']} ids without metadata (> 2%)")
    return m


def deribit_days(window: tuple[str, str] = D_WINDOW) -> list[str]:
    """Calendar days whose 12:00 ET is an origin (d - 5, d - 2) or a resolution time (d) of a window date; plus the pre-window haircut days."""
    s = set()
    for d in window_dates(window):
        s.update({c10.day_add(d, -5), c10.day_add(d, -2), d})
    s.update(c10.days_between(*HAIRCUT_WINDOW))
    return sorted(s)


def deribit_fetch(root: Path, transport, *, rules_sha: str, smoke_path: Path, frame_dir: Path, now: float, rps: float = DERIBIT_RPS,
                  disk_cap: int = int(DERIBIT_OUTPUT_CAP_GB * 1024**3), budget_min: float | None = None, sleep=time.sleep, live_check=None, should_stop=None,
                  wall_clock=time.time, snapshot_root: Path | None = None, health_check=None, data_dumps: Path | None = None,
                  data_dumps_cap_gb: float = c10.DATA_DUMPS_CAP_GB, free_fn=None, window: tuple[str, str] = D_WINDOW, t_seal_epoch: float = c10.T_SEAL_EPOCH) -> dict:
    """q0203, one resumable chunk. Origin times come from the calendar (``deribit_days``) after the D frame finished; no Polymarket field is read.
    Per (currency, day): option trades of ``[t - 180 min, t]`` -> stored rows (``origin_trade_rows``), the origin status (range check share, flags),
    and for resolution days the settlement index row -> ``settle_index_guarded.csv.gz``. Perpetual hourly bars (60-day chunks) and DVOL hourly
    (reported variant)."""
    from . import cb6_tail as c6  # noqa: PLC0415
    from . import cb7_common as c7  # noqa: PLC0415

    c10.require_after_t_seal(now, "deribit-trades", t_seal_epoch)
    root = c10.refuse_path(Path(root))
    rdir = root / DERIBIT_RUN
    st = c10.stall_of(rdir)
    if st:
        return st
    up = c10.upstream_stall(rdir, Path(frame_dir))
    if up:
        return up
    if not _manifest_done(Path(frame_dir), ("dlad_frame_complete",)):
        raise NotNow("q0203 waits for q0202 (dlad_frame) to finish")
    bad = smoke_failures(smoke_path, ("deribit",))
    if bad:
        return c10.write_stall(rdir, c10.STALL_NOT_RUN_SOURCE, f"smoke criteria not met: {bad}")
    done = _manifest_done(rdir, ("deribit_complete",))
    if done:
        return {"stopped": None, "status": "deribit_complete", "complete": True, "counts": done.get("counts")}
    term = cm.prior_terminal(rdir)
    if term:
        return term
    c10.require_disk(data_dumps, data_dumps_cap_gb, disk_cap, free_fn=free_fn)
    fr = cm.open_run(root, DERIBIT_RUN, transport, allowed_run_id=DERIBIT_RUN, kind="cb10_deribit", label="CB10-D Deribit",
                     params={"window": list(window), "haircut_window": list(HAIRCUT_WINDOW), "evidence_role": c10.EVIDENCE_ROLE_HIST}, rules_sha=rules_sha, key_fp="",
                     disk_cap=disk_cap, rps=min(rps, DERIBIT_RPS), budget_min=budget_min, now=now, sleep=sleep, live_check=live_check, wall_clock=wall_clock,
                     snapshot_root=snapshot_root, health_check=health_check)
    res_days = set(window_dates(window))
    try:
        tp = rdir / "trades_partial.jsonl.gz"
        have = {(rec["currency"], rec["day"]) for rec in c6.iter_partial(tp)}
        for day in deribit_days(window):
            for cur in ASSETS:
                if (cur, day) in have:
                    continue
                why = fr.stop_reason(should_stop)
                if why:
                    return _in_progress(fr, why)
                t = c10.noon_et(day)
                try:
                    trades, info = deribit_trades(fr.lim, cur, int((t - DERIBIT_FETCH_S) * 1000), int(t * 1000))
                    rows, n, settle = origin_trade_rows(cur, t, trades)
                    status = "ok"
                except (cm.ApiError, RuntimeError) as exc:
                    fails = fr.extra_state.setdefault("fails", {})
                    k = f"{cur}|{day}"
                    fails[k] = fails.get(k, 0) + 1
                    if fails[k] < cm.MAX_ITEM_ATTEMPTS:
                        return _in_progress(fr, f"deribit_failed {k}: {exc}"[:200])
                    rows, n, settle, info, status = [], {"n_rows": 0, "n_range_ok": 0, "n_block": 0, "n_combo": 0, "n_liq": 0, "range_share": 0.0}, None, {"pages": 0}, "fetch_failed"
                if status == "ok" and n["range_share"] < IV_RANGE_SHARE:
                    status = "range_check_failed"
                c7.append_member(fr, tp, {"currency": cur, "day": day, "t": t, "rows": rows, "status": status, "n": n, "pages": info.get("pages", 0),
                                          "settle": settle if day in res_days else None})
        if not (rdir / "perp_bars.csv.gz").exists():
            start = int((c10.noon_et(HAIRCUT_WINDOW[0]) - (RV_DAYS + 1) * DAY) * 1000)
            end = int(cm.ep(c10.T10_HIST_END) * 1000)
            bars = []
            for cur in ASSETS:
                a = start
                while a < end:
                    b = min(a + CHART_CHUNK_DAYS * int(DAY) * 1000, end)
                    try:
                        bars += [[PERP[cur], o, op_, c] for o, op_, c in chart_bars(fr.lim, PERP[cur], a, b) if o + 3_600_000 <= end]
                    except (cm.ApiError, RuntimeError) as exc:
                        return _in_progress(fr, f"chart_failed {cur}: {exc}"[:200])
                    a = b
            dv = []
            for cur in ASSETS:
                try:
                    dv += [[cur, o, c] for o, c in dvol_rows(fr.lim, cur, start, end) if o + 3_600_000 <= end]
                except (cm.ApiError, RuntimeError) as exc:
                    return _in_progress(fr, f"dvol_failed {cur}: {exc}"[:200])
            uniq = {(r[0], r[1]): r for r in bars}
            fr.budget.write_gz_csv(rdir / "perp_bars.csv.gz", BAR_COLUMNS, [uniq[k] for k in sorted(uniq)])
            fr.budget.write_gz_csv(rdir / "dvol.csv.gz", DVOL_COLUMNS, sorted({(r[0], r[1]): r for r in dv}.values()))
        recs = sorted(c6.iter_partial(tp), key=lambda r: (r["currency"], r["t"]))
        fr.budget.write_gz_csv(rdir / "trades.csv.gz", TRADE_COLUMNS, (row for rec in recs for row in rec["rows"]))
        fr.budget.write_gz_csv(rdir / "deribit_origins.csv.gz", DORIGIN_COLUMNS,
                               ([rec["currency"], int(rec["t"]), rec["status"], rec["n"]["n_rows"], rec["n"]["n_range_ok"], rec["n"]["n_block"], rec["n"]["n_combo"],
                                 rec["n"]["n_liq"], rec["pages"], rec["n"]["range_share"]] for rec in recs))
        fr.budget.write_gz_csv(rdir / "settle_index_guarded.csv.gz", SETTLE_COLUMNS,
                               ([rec["currency"], rec["day"], int(rec["t"]), rec["settle"]["ts_ms"], rec["settle"]["index_price"]] for rec in recs if rec.get("settle")))
        for name in ("trades.csv.gz", "deribit_origins.csv.gz", "settle_index_guarded.csv.gz", "perp_bars.csv.gz", "dvol.csv.gz"):
            fr.record_file(rdir / name)
        tp.unlink(missing_ok=True)
        fr.counts.update(origin_fetches=len(recs), failed=sum(1 for r in recs if r["status"] != "ok"))
    except OSError as exc:
        return cm.disk_budget_end(fr, exc)
    m = fr.manifest(None, {"complete": True, "status": "deribit_complete"})
    m["status"] = "deribit_complete"
    return m


# =====================================================================================================================================
# Units (census, screen): one origin time at a time
# =====================================================================================================================================


def _f(x) -> float:
    if x in (None, ""):
        return math.nan
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def iter_trade_groups(path: Path) -> Iterator[tuple[tuple[str, int], list[dict]]]:
    """Stream ``trades.csv.gz`` (sorted by currency, origin time) one (currency, origin_t) group at a time."""
    with gzip.open(Path(path), "rt", encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        for key, grp in itertools.groupby(rd, key=lambda r: (r["currency"], int(r["origin_t"]))):
            rows = []
            for r in grp:
                rows.append({"ts_ms": int(r["ts_ms"]), "instrument": r["instrument"], "iv": _f(r["iv"]), "index_price": _f(r["index_price"]),
                             "amount": _f(r["amount"]), "flags": int(r["flags"]) if r["flags"] not in ("", None) else 0})
            yield key, rows


def load_bars(path: Path) -> dict[str, list[tuple[int, float, float]]]:
    from . import cb7_common as c7  # noqa: PLC0415

    out: dict[str, list[tuple[int, float, float]]] = {}
    if Path(path).exists():
        for r in c7.read_csv_gz(path):
            out.setdefault(r["instrument"], []).append((int(r["o_ms"]), float(r["open"]), float(r["close"])))
    return {k: sorted(v) for k, v in out.items()}


def load_dvol(path: Path) -> dict[str, list[tuple[int, float]]]:
    from . import cb7_common as c7  # noqa: PLC0415

    out: dict[str, list[tuple[int, float]]] = {}
    if Path(path).exists():
        for r in c7.read_csv_gz(path):
            out.setdefault(r["currency"], []).append((int(r["o_ms"]), float(r["close"])))
    return {k: sorted(v) for k, v in out.items()}


def unit_features(o: dict, rows: list[dict], fits: dict, fits_all: dict, *, sigma_rv: float, sigma_dvol: float, h: float | None = None) -> dict:
    """Anchor features of one origin row (no outcome): S, q, q_RV, q' (spot at t_reg), and the reported variants (flat smile, with block / combo,
    DVOL-flat, haircut). Returns the Deribit availability status."""
    t, T, K = float(o["t"]), c10.noon_et(o["d"]), float(o["strike"])
    S = spot_at_origin(rows, t)
    a = anchor_q(fits, S, K, t, T)
    out = {"S": S, "q": a["q"], "anchor_status": a["status"], "sigma": a.get("sigma", math.nan), "b": a.get("b", math.nan), "sides": a.get("sides"),
           "fit_kinds": a.get("fit_kinds"), "expiry_dist_s": a.get("expiry_dist_s", math.nan), "m_K": math.log(K / S) if S > 0 else math.nan}
    tau = (T - t) / YEAR_S
    out["q_rv"] = digital(S, K, sigma_rv, tau, 0.0) if math.isfinite(sigma_rv) and S > 0 else math.nan
    t_reg = _f(o.get("t_reg"))
    s_reg = last_index(rows, t_reg * 1000) if math.isfinite(t_reg) else math.nan
    out["q_prime"] = anchor_q(fits, s_reg, K, t, T)["q"] if s_reg > 0 else math.nan
    out["q_flat"] = anchor_q(fits, S, K, t, T, flat=True)["q"]
    out["q_with_flagged"] = anchor_q(fits_all, spot_at_origin_all(rows, t), K, t, T)["q"]
    out["q_dvol"] = digital(S, K, sigma_dvol, tau, 0.0) if math.isfinite(sigma_dvol) and S > 0 else math.nan
    out["q_haircut"] = anchor_q(fits, S, K, t, T, sigma_scale=1 - h)["q"] if h is not None and math.isfinite(h) else math.nan
    return out


def spot_at_origin_all(rows: list[dict], t: float) -> float:
    u = usable_trades(rows, t, include_flagged=True)
    return u[-1]["index_price"] if u else math.nan


def build_units(frame_dir: Path, deribit_dir: Path, *, h: float | None = None) -> tuple[list[dict], dict]:
    """Every origin row of ``origins.csv.gz`` with its eligibility status and, for eligible units, exactly one label in the fixed order (truncation,
    Deribit, inactive) or ``available``; anchor features from the Deribit group of its origin time. No outcome file is opened here."""
    from . import cb7_common as c7  # noqa: PLC0415

    origins = list(c7.read_csv_gz(Path(frame_dir) / "origins.csv.gz"))
    dstat = {(r["currency"], int(r["origin_t"])): r["status"] for r in c7.read_csv_gz(Path(deribit_dir) / "deribit_origins.csv.gz")}
    bars = load_bars(Path(deribit_dir) / "perp_bars.csv.gz")
    dvol = load_dvol(Path(deribit_dir) / "dvol.csv.gz")
    by_key: dict[tuple[str, int], list[dict]] = {}
    for o in origins:
        by_key.setdefault((o["asset"], int(float(o["t"]))), []).append(o)
    units: list[dict] = []
    fit_counts = {"smile": 0, "atm": 0, "none": 0}
    seen: set[tuple[str, int]] = set()
    for key, rows in iter_trade_groups(Path(deribit_dir) / "trades.csv.gz"):
        seen.add(key)
        group = by_key.get(key)
        if not group:
            continue
        t = float(key[1])
        fits = expiry_fits(usable_trades(rows, t))
        fits_all = expiry_fits(usable_trades(rows, t, include_flagged=True))
        for f in fits.values():
            fit_counts[f["kind"] or "none"] += 1
        srv = rv_sigma(bars.get(PERP[key[0]], []), t)
        sdv = dvol_sigma(dvol.get(key[0], []), t)
        for o in group:
            units.append(_label_unit(o, dstat.get(key), unit_features(o, rows, fits, fits_all, sigma_rv=srv, sigma_dvol=sdv, h=h)))
    for key, group in by_key.items():
        if key not in seen:
            for o in group:
                units.append(_label_unit(o, dstat.get(key), None))
    return units, {"fit_counts": fit_counts, "n_origin_rows": len(origins)}


def _label_unit(o: dict, dstatus: str | None, feat: dict | None) -> dict:
    u = {"market_id": o["market_id"], "asset": o["asset"], "d": o["d"], "lag": int(o["lag"]), "t": float(o["t"]), "strike": float(o["strike"]), "status": o["status"],
         "week": c10.iso_week(o["d"]), "weekday": date.fromisoformat(o["d"]).strftime("%a"), "month": o["d"][:7]}
    for k in ("p", "t_p", "size_p", "p_reg", "t_reg", "p_alt", "t_alt", "p10", "t_p10", "p_reg10", "t_reg10", "last_any_price"):
        u[k] = _f(o.get(k))
    if feat:
        u.update(feat)
    else:
        u.update(q=math.nan, anchor_status="no_deribit_rows")
    if o["status"] != ST_ELIGIBLE:
        u["label"] = None
        return u
    if str(o.get("truncated_for_t")) in ("1", "True"):
        u["label"] = LABEL_TRUNC
    elif dstatus != "ok" or not math.isfinite(u.get("q", math.nan)):
        u["label"] = LABEL_DERIBIT
    elif not (math.isfinite(u["p"]) and math.isfinite(u["p_reg"])):
        u["label"] = LABEL_INACTIVE
    else:
        u["label"] = "available"
    return u


# =====================================================================================================================================
# Census (q0207 D): counts only; GD, GDP, coverage audit
# =====================================================================================================================================


def gdp_mde(units: list[dict], *, draws: int = GDP["draws"], seed: int = GDP["seed"]) -> dict:
    """Feature-only power gate: per asset x resolution date one uniform (BTC/ETH of a date joined by a Gaussian copula, rho = 0.8), every strike's
    simulated outcome ``Y* = 1{U < pbar}`` (``pbar`` = the market's mean available p over its origins), the D1 estimator on the real ``x = q - p_reg``
    and target ``Y* - p``; ``MDE = (z_0.99 + z_0.80) x 1.2 x SD(beta*)``; MDE > 1.0 -> D1 "not run (power)". No outcome is read."""
    av = [u for u in units if u.get("label") == "available"]
    if len(av) < 3:
        return {"n": len(av), "sd_beta": math.nan, "mde": math.nan, "pass": False}
    pbar: dict[str, list[float]] = {}
    for u in av:
        pbar.setdefault(u["market_id"], []).append(u["p"])
    pb = np.array([float(np.mean(pbar[u["market_id"]])) for u in av])
    p = np.array([u["p"] for u in av])
    x = np.array([u["q"] - u["p_reg"] for u in av])
    dates = sorted({u["d"] for u in av})
    di = np.array([dates.index(u["d"]) for u in av])
    ai = np.array([ASSETS.index(u["asset"]) for u in av])
    rng = np.random.default_rng(seed)
    rho = GDP["rho"]
    betas = []
    from scipy.stats import norm  # noqa: PLC0415

    for _ in range(draws):
        z1 = rng.standard_normal(len(dates))
        z2 = rho * z1 + math.sqrt(1 - rho * rho) * rng.standard_normal(len(dates))
        U = np.vstack([norm.cdf(z1), norm.cdf(z2)])
        ystar = (U[ai, di] < pb).astype(float)
        betas.append(c10.ols_slope(ystar - p, x))
    sd = float(np.nanstd(betas, ddof=1))
    mde = GDP["z_sum"] * GDP["inflation"] * sd
    return {"n": len(av), "draws": draws, "seed": seed, "rho": rho, "inflation": GDP["inflation"], "sd_beta": sd, "mde": mde, "max_mde": GDP["max_mde"],
            "pass": bool(math.isfinite(mde) and mde <= GDP["max_mde"])}


def census_d(units: list[dict], frame_info: dict) -> dict:
    """D census, counts and features only (no Y, no settlement index, no slope of Y): eligibility statuses and labels by asset, origin and weekday,
    the 60% availability rule with the dominant-label naming, the D coverage audit (>= 90% source-available), gate GD, the GDP power gate, the
    feature distributions, ``cor(q - p_reg, q_RV - p_reg)`` (> 0.9 -> attribution not identifiable)."""
    for u in units:
        if any(k in u for k in FORBIDDEN_CENSUS):
            raise Refused("census received an outcome / settlement field")
    elig = [u for u in units if u["status"] == ST_ELIGIBLE]
    undet = [u for u in units if u["status"] == ST_UNDET]
    lab: dict[str, int] = {}
    by: dict[str, dict[str, int]] = {}
    for u in elig:
        lab[u["label"]] = lab.get(u["label"], 0) + 1
        for dim in (f"asset={u['asset']}", f"lag={u['lag']}", f"weekday={u['weekday']}"):
            by.setdefault(dim, {}).setdefault(u["label"], 0)
            by[dim][u["label"]] += 1
    n_el = len(elig)
    av = [u for u in elig if u["label"] == "available"]
    src_missing = lab.get(LABEL_TRUNC, 0) + lab.get(LABEL_DERIBIT, 0)
    inactive = lab.get(LABEL_INACTIVE, 0)
    avail_share = len(av) / n_el if n_el else 0.0
    # Undeterminable (truncation) units count as source-unavailable in the audit denominator (conservative; open item).
    audit_den = n_el + len(undet)
    audit_share = (n_el - src_missing) / audit_den if audit_den else 0.0
    audit_pass = bool(audit_den) and audit_share >= AUDIT_PASS
    rule60 = {"share": avail_share, "pass": avail_share >= AVAILABLE_MIN,
              "label": None if avail_share >= AVAILABLE_MIN else ("not testable (source unavailable)" if src_missing >= inactive else "not testable (inactivity)")}
    near = [u for u in av if math.isfinite(u.get("expiry_dist_s", math.nan)) and u["expiry_dist_s"] <= EXPIRY_MAX_S]
    n_btc = sum(1 for u in av if u["asset"] == "BTC")
    gd = {"units": len(av), "dates": len({u["d"] for u in av}), "weeks": len({u["week"] for u in av}),
          "btc_share": n_btc / len(av) if av else 0.0, "eth_share": 1 - n_btc / len(av) if av else 0.0, "near_expiry_units": len(near)}
    gd_ok = (gd["units"] >= GD["units"] and gd["dates"] >= GD["dates"] and gd["weeks"] >= GD["weeks"] and min(gd["btc_share"], gd["eth_share"]) >= GD["asset_share"]
             and gd["near_expiry_units"] >= GD["near_expiry_units"])
    x = np.array([u["q"] - u["p_reg"] for u in av]) if av else np.array([])
    xr = [(u["q"] - u["p_reg"], u["q_rv"] - u["p_reg"]) for u in av if math.isfinite(u.get("q_rv", math.nan))]
    cor = float(np.corrcoef(np.array(xr).T)[0, 1]) if len(xr) >= 3 else math.nan
    gdp = gdp_mde(units)
    dist = [u["expiry_dist_s"] / 3600 for u in av if math.isfinite(u.get("expiry_dist_s", math.nan))]
    label_d1 = None
    if not audit_pass:
        label_d1 = "not testable (source unavailable)"
    elif not rule60["pass"]:
        label_d1 = rule60["label"]
    elif not gd_ok:
        label_d1 = "not testable (gate GD)"
    elif not gdp["pass"]:
        label_d1 = f"not run (power): MDE {gdp['mde']:.3f} > {GDP['max_mde']}"
    return {"frame": frame_info, "n_units": len(units), "status_counts": {s: sum(1 for u in units if u["status"] == s) for s in (ST_ELIGIBLE, ST_BAND, ST_NEVER, ST_UNDET)},
            "labels": lab, "labels_by": by, "availability_rule_60": rule60,
            "coverage_audit": {"eligible": n_el, "undeterminable_truncation": len(undet), "source_missing": src_missing, "share": audit_share, "pass": audit_pass,
                               "threshold": AUDIT_PASS},
            "gate_GD": gd, "gate_GD_pass": gd_ok, "gate_GDP": gdp,
            "features": {"abs_gap_share_ge_4c": float(np.mean(np.abs(x) >= DIRECTIONAL_MIN)) if len(x) else math.nan, "sd_gap": float(np.std(x, ddof=1)) if len(x) > 1 else math.nan,
                         "cor_gap_rv": cor, "attribution_identifiable": bool(math.isfinite(cor) and cor <= COR_ATTRIB_MAX),
                         "expiry_dist_hours_quantiles": [float(np.quantile(dist, q)) for q in (0.1, 0.5, 0.9)] if dist else [],
                         "anchor_status": {s: sum(1 for u in elig if u.get("anchor_status") == s) for s in sorted({u.get("anchor_status") for u in elig if u.get("anchor_status")})}},
            "d1_runs": label_d1 is None, "label_D1": label_d1}


# =====================================================================================================================================
# Screen (q0208): D1 with placebos and binding robustness; source check
# =====================================================================================================================================


def source_check(units: list[dict], settle: dict[tuple[str, str], float], y_of: Callable[[dict], float | None]) -> dict:
    """On market-dates with ``|ln(S_T / K)| > 0.5%``: the index-implied outcome (S_T > K) vs the Gamma outcome; disagreement > 2% -> D not testable
    (source). Disagreeing units stay in (the Gamma outcome is what pays)."""
    seen, n, dis = set(), 0, 0
    for u in units:
        k = (u["market_id"], u["d"])
        if k in seen:
            continue
        seen.add(k)
        s = settle.get((u["asset"], u["d"]))
        y = y_of(u)
        if s is None or y is None or y == 0.5 or not (s > 0):
            continue
        if abs(math.log(s / u["strike"])) <= SOURCE_MIN_ABS_LOGM:
            continue
        n += 1
        dis += int((s > u["strike"]) != (y == 1.0))
    share = dis / n if n else 1.0
    return {"n": n, "disagree": dis, "share": share, "pass": bool(n > 0 and share <= SOURCE_DISAGREE_MAX)}


def _ways(us: list[dict]) -> tuple[dict[str, np.ndarray], np.ndarray]:
    return ({"date": np.array([u["d"] for u in us]), "asset_date": np.array([f"{u['asset']}|{u['d']}" for u in us])}, np.array([u["week"] for u in us]))


def slope_test(y: np.ndarray, x: np.ndarray, us: list[dict], *, w=None, alpha: float | None = None) -> dict:
    v, b = c10.slope_pseudo(y, x, w)
    if not math.isfinite(b):
        return {"beta": b, "p": 1.0, "testable": False, "n": len(y)}
    cl, wk = _ways(us)
    r = c10.cluster_p_d(v, cl, wk, estimator=lambda keep: c10.ols_slope(y, x, keep), alpha=alpha)
    return {"beta": b, "p": r["p"], "testable": bool(r["testable"] and r.get("week_rule_holds", True)), "n": len(y), "ways": r.get("ways"), "week": r.get("week"),
            "week_rule_holds": r.get("week_rule_holds", True)}


def d1_stat(units: list[dict], y_of: Callable[[dict], float | None], *, cor_identifiable: bool = True, n_draws: int = c10.PLACEBO_DRAWS) -> dict:
    """D1: OLS slope of ``Y - p`` on ``q - p_reg`` (intercept, unweighted) on available units; one-sided p = max over the date, asset-date and ISO-week
    ways (week small-G rule); floor 0.30. Binding: week (and date) sign-flip calibration, the independent-price placebo (``p_alt``), the spot-staleness
    control (``q'``), top-5 drops, size weighting, period / asset signs, the 10-minute latency rule. Option attribution labels only."""
    av = [u for u in units if u.get("label") == "available"]
    ys = [y_of(u) for u in av]
    us = [u for u, y in zip(av, ys, strict=True) if y is not None]
    Y = np.array([y for y in ys if y is not None])
    res: dict[str, Any] = {"n_available": len(av), "n_unresolved": len(av) - len(us)}
    if len(us) < 3:
        return {**res, "n": len(us), "testable": False, "p": 1.0, "advance": False, "verdict": "not testable"}
    p = np.array([u["p"] for u in us])
    x = np.array([u["q"] - u["p_reg"] for u in us])
    y = Y - p
    base = slope_test(y, x, us)
    b = base["beta"]
    res.update(n=len(us), beta=b, p=base["p"], testable=base["testable"], ways=base.get("ways"), week=base.get("week"))
    if not base["testable"]:
        return {**res, "advance": False, "verdict": "not testable"}
    # sign-flip calibration placebos (week coin; date coin)
    pls = {}
    for name, key in (("week", "week"), ("date", "d")):
        rng = np.random.default_rng(c10.PLACEBO_SEEDS[f"D1_signflip_{name}"])
        groups = sorted({u[key] for u in us})
        gi = np.array([groups.index(u[key]) for u in us])
        ps = []
        for _ in range(n_draws):
            sg = np.where(rng.random(len(groups)) < 0.5, -1.0, 1.0)
            ps.append(slope_test(y, x * sg[gi], us, alpha=c10.GATE_P)["p"])
        pls[name] = c10.placebo_advance_rate(ps)
    # independent-price placebo
    ia = [i for i, u in enumerate(us) if math.isfinite(u["p_alt"])]
    if len(ia) >= 3:
        sub = [us[i] for i in ia]
        xa = np.array([u["p_alt"] - u["p_reg"] for u in sub])
        ta = slope_test(y[ia], xa, sub)
        b_sub = c10.ols_slope(y[ia], x[ia])
        diff = min(b - ta["beta"], b_sub - ta["beta"]) if math.isfinite(ta["beta"]) else -math.inf
        indep = {"n": len(ia), "n_dropped": len(us) - len(ia), "beta_alt": ta["beta"], "p_alt": ta["p"], "beta_q_subset": b_sub, "min_diff": diff,
                 "holds": bool(ta["p"] >= c10.GATE_P and diff >= D1_FLOOR)}
    else:
        indep = {"n": len(ia), "holds": False, "note": "too few units with p_alt"}
    # spot staleness q'
    js = [i for i, u in enumerate(us) if math.isfinite(u.get("q_prime", math.nan))]
    bs = c10.ols_slope(y[js], np.array([us[i]["q_prime"] - us[i]["p_reg"] for i in js])) if len(js) >= 3 else math.nan
    stale = {"n": len(js), "beta": bs, "holds": bool(math.isfinite(bs) and np.sign(bs) == np.sign(b) and abs(bs) >= abs(b) / 2)}
    # attribution
    jr = [i for i, u in enumerate(us) if math.isfinite(u.get("q_rv", math.nan))]
    attrib: dict[str, Any] = {"n": len(jr), "identifiable": cor_identifiable}
    if len(jr) >= 4:
        X = np.column_stack([np.ones(len(jr)), x[jr], np.array([us[i]["q_rv"] - us[i]["p_reg"] for i in jr])])
        coef, *_ = np.linalg.lstsq(X, y[jr], rcond=None)
        solo = c10.ols_slope(y[jr], x[jr])
        attrib.update(joint_beta_q=float(coef[1]), joint_beta_rv=float(coef[2]), solo_beta_q=solo,
                      credit_option_implied=bool(cor_identifiable and math.isfinite(solo) and coef[1] >= solo / 2))
    # robustness
    cl, wk = _ways(us)
    allways = {**cl, "week": wk}
    drops = {}
    for way, c in allways.items():
        keep = c9_top_k(v_of(y, x), c)
        kept = [us[i] for i in np.flatnonzero(keep)]
        r = slope_test(y[keep], x[keep], kept)
        drops[way] = {"beta": r["beta"], "p": r["p"], "holds": bool(r["testable"] and r["p"] < c10.GATE_P and r["beta"] >= D1_FLOOR)}
    rob_ii = all(d["holds"] for d in drops.values())
    w = np.minimum(np.array([u["size_p"] for u in us]), SIZE_WEIGHT_CAP)
    bw = c10.slope_pseudo(y, x, w)[1]
    rob_iii = bool(math.isfinite(bw) and np.sign(bw) == np.sign(b))
    per = {}
    for a, z in THIRDS:
        keep = np.array([a <= u["month"] <= z for u in us])
        per[f"{a}..{z}"] = c10.ols_slope(y, x, keep) if keep.sum() >= 3 else math.nan
    for asset in ASSETS:
        keep = np.array([u["asset"] == asset for u in us])
        per[asset] = c10.ols_slope(y, x, keep) if keep.sum() >= 3 else math.nan
    rob_iv = all(math.isfinite(v) and np.sign(v) == np.sign(b) for v in per.values())
    jl = [i for i, u in enumerate(us) if math.isfinite(u["p10"]) and math.isfinite(u["p_reg10"])]
    bl = c10.ols_slope(Y[jl] - np.array([us[i]["p10"] for i in jl]), np.array([us[i]["q"] - us[i]["p_reg10"] for i in jl])) if len(jl) >= 3 else math.nan
    rob_vi = bool(math.isfinite(bl) and np.sign(bl) == np.sign(b) and abs(bl) >= abs(b) / 2)
    robust = rob_ii and rob_iii and rob_iv and rob_vi
    placebo_ok = all(x_["holds"] for x_ in pls.values())
    adv = bool(base["p"] < c10.GATE_P and b >= D1_FLOOR and placebo_ok and indep["holds"] and stale["holds"] and robust)
    label = None
    if adv:
        if not cor_identifiable:
            label = "option attribution not identifiable (cor > 0.9)"
        elif not attrib.get("credit_option_implied"):
            label = "a spot-plus-realised-vol digital explains it (CH30-type); options add nothing measurable"
    return {**res, "floor": D1_FLOOR, "placebo_signflip": pls, "independent_price_placebo": indep, "spot_staleness": stale, "option_attribution": attrib,
            "robustness": {"ii_top5": drops, "iii_size_weighted_beta": bw, "iii_holds": rob_iii, "iv_period_asset": per, "iv_holds": rob_iv,
                           "v_unavailable": "excluded and counted, never imputed (census labels)", "vi_latency_beta": bl, "vi_holds": rob_vi},
            "advance": adv, "label": label,
            "verdict": "advance" if adv else ("not detected at MDE" if base["p"] >= c10.GATE_P else "fails floor / placebo / robustness"),
            "reported": d1_reported(us, Y)}


def v_of(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    v, b = c10.slope_pseudo(y, x)
    return v - b


def c9_top_k(v: np.ndarray, c: np.ndarray) -> np.ndarray:
    return c10.c9.top_k_drop_mask(v, c)


def d1_reported(us: list[dict], Y: np.ndarray) -> dict:
    """Descriptive only: log-loss and Brier of q and p, the same-transaction slope (shared-noise bias), the directional excess, the slope by
    moneyness tercile, origin and asset, and the variants (flat smile, with block / combo, DVOL-flat, haircut)."""
    p = np.array([u["p"] for u in us])
    q = np.array([u["q"] for u in us])
    pr = np.array([u["p_reg"] for u in us])
    y = Y - p

    def ll(f):
        f = np.clip(f, 1e-6, 1 - 1e-6)
        return float(-np.mean(Y * np.log(f) + (1 - Y) * np.log(1 - f)))

    out = {"logloss_q": ll(q), "logloss_p": ll(p), "brier_q": float(np.mean((q - Y) ** 2)), "brier_p": float(np.mean((p - Y) ** 2)),
           "same_transaction_slope": c10.ols_slope(y, q - p)}
    x = q - pr
    big = np.abs(x) >= DIRECTIONAL_MIN
    out["directional_excess"] = float(np.mean(y[big] * np.sign(x[big]))) if big.any() else None
    mk = np.array([u.get("m_K", math.nan) for u in us])
    if np.isfinite(mk).sum() >= 9:
        cuts = np.nanquantile(mk, [1 / 3, 2 / 3])
        terc = np.digitize(mk, cuts)
        out["beta_by_moneyness_tercile"] = {int(k): c10.ols_slope(y, x, terc == k) for k in (0, 1, 2)}
    out["beta_by_lag"] = {lag: c10.ols_slope(y, x, np.array([u["lag"] == lag for u in us])) for lag in ORIGIN_LAGS}
    out["beta_by_asset"] = {a: c10.ols_slope(y, x, np.array([u["asset"] == a for u in us])) for a in ASSETS}
    for var in ("q_flat", "q_with_flagged", "q_dvol", "q_haircut"):
        j = [i for i, u in enumerate(us) if math.isfinite(u.get(var, math.nan))]
        out[f"beta_{var}"] = c10.ols_slope(y[j], np.array([us[i][var] - us[i]["p_reg"] for i in j])) if len(j) >= 3 else None
    return out


# =====================================================================================================================================
# Stage 2 (q0210 collection, q0211 D1-rep and D2)
# =====================================================================================================================================


def t10_d2_start(max_commit_epoch: float) -> str:
    """First resolution date whose d - 5 origin is >= max(freeze commit, D1 result commit) + 1 day."""
    d = datetime.fromtimestamp(max_commit_epoch, c10.ET).date().isoformat()
    while c10.noon_et(c10.day_add(d, -ORIGIN_LAGS[0])) < max_commit_epoch + DAY:
        d = c10.day_add(d, 1)
    return d


def stage2_dates(start: str) -> list[str]:
    return [c10.day_add(start, i) for i in range(STAGE2_DATES)]


def origin_day_of(now: float) -> tuple[str, float]:
    day = datetime.fromtimestamp(now, c10.ET).date().isoformat()
    return day, c10.noon_et(day)


def origin_due(now: float) -> dict:
    """The cron lines run at 16:00Z and 17:00Z; a run acts only for the 12:00 America/New_York origin of today: ``0 <= now - t <= 600 s`` -> act;
    ``|now - t| >= 3000 s`` -> the other cron line (exit 0, nothing recorded); otherwise the origin is "unavailable (scheduling)" (late start)."""
    day, t = origin_day_of(now)
    dt = now - t
    if abs(dt) >= STAGE2_WRONG_LINE_S:
        return {"action": "wrong_line", "day": day, "t": t}
    if 0 <= dt <= STAGE2_RECEIPT_S:
        return {"action": "collect", "day": day, "t": t}
    return {"action": "late", "day": day, "t": t}


def stage2_targets(origin_day: str, dates: list[str]) -> list[tuple[str, int]]:
    """(resolution date, lag) pairs whose d - 5 or d - 2 origin is ``origin_day``, inside the Stage-2 date set."""
    ds = set(dates)
    return [(c10.day_add(origin_day, lag), lag) for lag in ORIGIN_LAGS if c10.day_add(origin_day, lag) in ds]


def clob_book_state(doc: Any) -> dict | None:
    """Best bid / ask and the size at the best ask of a CLOB ``/book`` reply (receipt-timed by the caller); crossed books are ineligible."""
    if not isinstance(doc, dict):
        return None

    def lv(key: str) -> dict[float, float]:
        out: dict[float, float] = {}
        for x in doc.get(key) or []:
            try:
                p, s = float(x["price"]), float(x["size"])
            except (KeyError, TypeError, ValueError):
                continue
            if s > 0:
                out[p] = out.get(p, 0.0) + s
        return out

    bids, asks = lv("bids"), lv("asks")
    bb, ba = (max(bids) if bids else None), (min(asks) if asks else None)
    return {"best_bid": bb, "best_ask": ba, "ask_size": asks.get(ba) if ba is not None else None, "crossed": bool(bb is not None and ba is not None and bb >= ba)}


def dlad_live_tick(root: Path, *, now: float, dates: list[str], frame_markets: Callable[[str], list[dict]], book_get: Callable[[str], tuple[Any, float]],
                   deribit_get: Callable[[str, int, int], tuple[list[dict], float]], summary_get: Callable[[str], tuple[Any, float]] | None,
                   prints_get: Callable[[str], tuple[list[dict], dict]], disk_ok: Callable[[], None], clock: Callable[[], float] = time.time) -> dict:
    """One cron run (q0210, outside the queue lanes). At the 12:00 ET origin ``t``: the ladder frame (frozen rule) of the Stage-2 dates whose d - 5 or
    d - 2 origin this is, CLOB books of both tokens of every strike, Deribit trades ``[t - 180 min, t]`` and the live book summary (variant); every
    receipt must lie in ``[t, t + 10 min]``; then the prints (filtered to time < t) -> origin rows. Labels: unavailable (scheduling / host disk /
    source), never refilled. Writes ``<root>/<origin_day>/``."""
    due = origin_due(now)
    if due["action"] == "wrong_line":
        return {"status": "not_this_line", "requests": 0}
    day, t = due["day"], due["t"]
    targets = stage2_targets(day, dates)
    if not targets:
        return {"status": "no_stage2_origin_today", "requests": 0}
    odir = Path(root) / day
    if (odir / "status.json").exists():
        return {"status": "already_recorded", "day": day}
    odir.mkdir(parents=True, exist_ok=True)

    def finish(label: str, extra: dict | None = None) -> dict:
        doc = {"day": day, "t": t, "label": label, "targets": targets, "run_started": now, "run_finished": clock(), **(extra or {})}
        (odir / "status.json").write_text(json.dumps(doc, indent=1, sort_keys=True, default=float))
        return {"status": "recorded", **doc}

    if due["action"] == "late":
        return finish("unavailable (scheduling)")
    try:
        disk_ok()
    except NotNow:
        return finish("unavailable (host disk)")
    receipts: list[float] = []
    try:
        markets = []
        for d, lag in targets:
            for m in frame_markets(d):
                markets.append({**m, "lag": lag})
        (odir / "frame.json").write_text(json.dumps(markets, sort_keys=True, default=float))
        books = []
        for m in markets:
            for tok in (m["token_yes"], m["token_no"]):
                doc, rt = book_get(tok)
                receipts.append(rt)
                books.append({"market_id": m["market_id"], "token": tok, "receipt": rt, **(clob_book_state(doc) or {"best_ask": None})})
        (odir / "books.json").write_text(json.dumps(books, sort_keys=True, default=float))
        drows = []
        settle = {}
        for cur in ASSETS:
            trades, rt = deribit_get(cur, int((t - DERIBIT_FETCH_S) * 1000), int(t * 1000))
            receipts.append(rt)
            rows, n, s = origin_trade_rows(cur, t, trades)
            drows += rows
            settle[cur] = s
            if n["range_share"] < IV_RANGE_SHARE:
                return finish("unavailable (source)", {"why": f"deribit range check {cur}"})
        with gzip.open(odir / "deribit.csv.gz", "wt", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(TRADE_COLUMNS)
            w.writerows(drows)
        if summary_get is not None:
            summ = {}
            for cur in ASSETS:
                doc, rt = summary_get(cur)
                summ[cur] = {"receipt": rt, "rows": [{k: x.get(k) for k in ("instrument_name", "mark_iv", "underlying_price", "bid_price", "ask_price")}
                                                     for x in ((doc or {}).get("result") or []) if isinstance(x, dict)]}
            (odir / "book_summary.json").write_text(json.dumps(summ, sort_keys=True, default=float))
    except (cm.ApiError, RuntimeError) as exc:
        return finish("unavailable (source)", {"why": str(exc)[:200]})
    if receipts and (min(receipts) < t or max(receipts) > t + STAGE2_RECEIPT_S):
        return finish("unavailable (scheduling)", {"why": "a receipt outside [t, t + 10 min]"})
    orows = []
    for m in markets:
        try:
            prints, info = prints_get(m["condition_id"])
        except (cm.ApiError, RuntimeError):
            orows.append({"market_id": m["market_id"], "status": "prints_unavailable"})
            continue
        tx = aggregate_transactions(prints, int(m["yes_idx"]))
        o = origin_row(tx, t, oldest_ts=info["oldest_ts"], truncated=info["truncated"])
        o.update(market_id=m["market_id"], asset=m["asset"], d=m["d"], lag=m["lag"], t=t, strike=m["strike"])
        orows.append(o)
    (odir / "origins.json").write_text(json.dumps(orows, sort_keys=True, default=float))
    return finish("ok", {"n_markets": len(markets), "n_books": len(books)})


def outcome_sweep(root: Path, *, now: float, dates: list[str], frames: Callable[[], list[dict]], lookup: Callable[[list[str]], list[dict]],
                  deribit_get: Callable[[str, int, int], tuple[list[dict], float]]) -> dict:
    """After each Stage-2 resolution time T has passed: outcome prices (Gamma by id, closed) -> ``outcomes_guarded.csv.gz`` and the settlement index
    (last option trade at or before T) -> ``settle_index_guarded.csv.gz``. Written, never opened here. Runs until ``T10_D2_end`` + 2 days."""
    from . import cb7_common as c7  # noqa: PLC0415

    root = Path(root)
    op, sp = root / "outcomes_guarded.csv.gz", root / "settle_index_guarded.csv.gz"
    have_o = {r["market_id"] for r in c7.read_csv_gz(op)} if op.exists() else set()
    have_s = {(r["currency"], r["d"]) for r in c7.read_csv_gz(sp)} if sp.exists() else set()
    due = [d for d in dates if c10.noon_et(d) + 3600 <= now]
    want = [m for m in frames() if m["d"] in due and m["market_id"] not in have_o]
    new_o = []
    if want:
        raw = {str(m.get("id")): m for m in lookup(sorted({m["market_id"] for m in want})) if isinstance(m, dict)}
        for m in want:
            r = raw.get(m["market_id"])
            if r is None or not r.get("closed"):
                continue
            g = c10.guarded_outcome_prices(r)
            if not json.loads(g["outcome_prices"]):
                continue
            new_o.append([g["market_id"], m["d"], g["outcome_labels"], g["outcome_prices"]])
    new_s = []
    for d in due:
        T = c10.noon_et(d)
        for cur in ASSETS:
            if (cur, d) in have_s:
                continue
            trades, _ = deribit_get(cur, int((T - 3600) * 1000), int(T * 1000))
            s = [r for r in trades if r["ts_ms"] <= T * 1000 and r["index_price"] > 0]
            if s:
                new_s.append([cur, d, int(T), s[-1]["ts_ms"], s[-1]["index_price"]])
    for path, cols, rows in ((op, OUTCOME_COLUMNS, new_o), (sp, SETTLE_COLUMNS, new_s)):
        if rows:
            old = [[r[c] for c in cols] for r in c7.read_csv_gz(path)] if path.exists() else []
            path.write_bytes(hb._gz_csv_bytes(cols, old + rows))
    return {"outcomes_added": len(new_o), "settle_added": len(new_s)}


def stage2_availability(statuses: dict[str, str], origin_days: list[str]) -> dict:
    """Every Stage-2 origin day carries ``ok`` or one of the three labels (a missing status.json = "unavailable (scheduling)"); > 20% unavailable ->
    D1-rep and D2 not testable with the dominant label."""
    labs: dict[str, int] = {}
    for d in origin_days:
        lab = statuses.get(d) or "unavailable (scheduling)"
        labs[lab] = labs.get(lab, 0) + 1
    n = len(origin_days)
    un = n - labs.get("ok", 0)
    share = un / n if n else 1.0
    dom = max((k for k in labs if k != "ok"), key=lambda k: labs[k], default=None)
    return {"n_origins": n, "labels": labs, "unavailable_share": share, "testable": bool(n and share <= STAGE2_UNAVAILABLE_MAX),
            "label": None if share <= STAGE2_UNAVAILABLE_MAX else f"not testable ({dom})"}


def fee_rate(recorded: float) -> float:
    return max(recorded if math.isfinite(recorded) else 0.0, FEE_RATE_FLOOR)


def taker_fee(a: float, rate: float) -> float:
    return rate * a * (1.0 - a)


def d2_trade(q: float, books: dict[str, dict], rate: float, *, cost_add: float = 0.0) -> dict | None:
    """On YES (q) and NO (1 - q): edge = q_tok - a - f(a) >= 0.04 with size at a >= 5 shares at a fresh, uncrossed recorded ask; both -> the larger."""
    best = None
    for tok, qt in (("yes", q), ("no", 1.0 - q)):
        bk = books.get(tok) or {}
        a = bk.get("best_ask")
        if a is None or bk.get("crossed") or not (bk.get("ask_size") or 0) >= D2_MIN_SIZE:
            continue
        a = float(a) + cost_add
        edge = qt - a - taker_fee(a, rate)
        if edge >= D2_EDGE and (best is None or edge > best["edge"]):
            best = {"token": tok, "a": a, "fee": taker_fee(a, rate), "edge": edge}
    return best


def d2_stat(units: list[dict], y_of: Callable[[dict], float | None]) -> dict:
    """D2 (Stage 2): mean ``Y_tok - a - f(a)`` (cents per share) over traded market-origins; date and asset-date ways, week leave-one-out sign rule;
    floor +1.0c; binding +0.5c on ``a`` keeps net > 0."""
    rows = []
    for u in units:
        if not u.get("d2"):
            continue
        y = y_of(u)
        if y is None:
            continue
        yt = y if u["d2"]["token"] == "yes" else 1.0 - y
        rob = u.get("d2_cost")
        rows.append((u, yt - u["d2"]["a"] - u["d2"]["fee"], (yt - rob["a"] - rob["fee"]) if rob else None))
    if len(rows) < 2:
        return {"n": len(rows), "testable": False, "p": 1.0, "advance": False, "verdict": "not testable"}
    us = [r[0] for r in rows]
    net = np.array([r[1] for r in rows])
    cl, wk = _ways(us)
    r = c10.cluster_p_d(net, cl, wk)
    mean = float(net.mean())
    rob = [r_[2] for r_ in rows if r_[2] is not None]
    rob_ok = bool(rob and np.mean(rob) > 0)
    testable = bool(r["testable"] and r.get("week_rule_holds", True))
    return {"n": len(rows), "mean_cents": mean * 100, "p": r["p"] if testable else 1.0, "testable": testable, "ways": r.get("ways"), "week": r.get("week"),
            "floor_cents": D2_FLOOR * 100, "cost_robustness_cents": float(np.mean(rob) * 100) if rob else None, "cost_robustness_holds": rob_ok,
            "pass_floor": mean >= D2_FLOOR}


def live_frame_markets(lim: hb.Limiter, d: str, excl_ids: set[str], excl_keys: dict[str, set[str]]) -> list[dict]:
    """Stage 2: the frozen frame rule on ACTIVE markets ending at d 12:00 ET (whitelisted; the live ``outcomePrices`` are dropped, never stored);
    id / event / neg-risk drops."""
    from . import cb4_data as c4  # noqa: PLC0415

    a, b = gamma_end_window(d)
    rows, capped, failed = c4._paged_strict(lim, {"closed": "false", "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true"}, hb.GAMMA_OFFSET_CAP)
    if failed or capped:
        raise cm.ApiError(f"Gamma live ladder frame {d}: {'failed' if failed else 'capped'}")
    out = [r for r in (parse_ladder_market(m, d)[0] for m in rows if isinstance(m, dict)) if r is not None]
    kept, _ = c10.drop_by_keys(out, excl_ids, excl_keys, use_series=False)
    return kept


def haircut_from_deribit(deribit_dir: Path) -> dict:
    """Reported variant constant: over the 12:00 ET points of [2025-07-01, 2025-10-01), ATM IV_7d (the anchor's sigma at K = S, T = t + 7 d) and RV_7d
    (perpetual); ``h = 1 - median(RV / IV)``. Deribit data only; frozen in the census output."""
    bars = load_bars(Path(deribit_dir) / "perp_bars.csv.gz")
    hw = set(c10.days_between(*HAIRCUT_WINDOW))
    samples = []
    for (cur, t), rows in iter_trade_groups(Path(deribit_dir) / "trades.csv.gz"):
        if datetime.fromtimestamp(t, c10.ET).date().isoformat() not in hw:
            continue
        S = spot_at_origin(rows, float(t))
        a = anchor_q(expiry_fits(usable_trades(rows, float(t))), S, S, float(t), float(t) + HAIRCUT_TAU_DAYS * DAY) if S > 0 else {"status": "no_spot"}
        samples.append((rv_sigma(bars.get(PERP[cur], []), float(t)), a.get("sigma", math.nan)))
    return haircut_h(samples)


def live_units(ldir: Path, origin_days: list[str]) -> tuple[list[dict], dict[str, str]]:
    """Stage-2 units from the per-origin directories (status ``ok`` only): the Stage-1 price and label rules, the anchor q from the recorded Deribit
    rows, and the D2 trade at the recorded asks."""
    from . import cb7_common as c7  # noqa: PLC0415

    statuses: dict[str, str] = {}
    units: list[dict] = []
    for day in origin_days:
        sp = Path(ldir) / day / "status.json"
        if not sp.exists():
            continue
        st = json.loads(sp.read_text())
        statuses[day] = st["label"]
        if st["label"] != "ok":
            continue
        odir = Path(ldir) / day
        frame = {m["market_id"]: m for m in json.loads((odir / "frame.json").read_text())}
        books: dict[str, dict[str, dict]] = {}
        for b in json.loads((odir / "books.json").read_text()):
            m = frame.get(b["market_id"])
            if m:
                books.setdefault(b["market_id"], {})["yes" if b["token"] == m["token_yes"] else "no"] = b
        drows = {}
        for r in c7.read_csv_gz(odir / "deribit.csv.gz"):
            drows.setdefault(r["currency"], []).append({"ts_ms": int(r["ts_ms"]), "instrument": r["instrument"], "iv": _f(r["iv"]), "index_price": _f(r["index_price"]),
                                                        "amount": _f(r["amount"]), "flags": int(r["flags"]) if r["flags"] not in ("", None) else 0})
        fits = {cur: expiry_fits(usable_trades(rows, st["t"])) for cur, rows in drows.items()}
        for o in json.loads((odir / "origins.json").read_text()):
            if o.get("status") == "prints_unavailable":
                continue
            m = frame[o["market_id"]]
            rows = drows.get(m["asset"], [])
            S = spot_at_origin(rows, float(o["t"]))
            a = anchor_q(fits.get(m["asset"], {}), S, float(m["strike"]), float(o["t"]), c10.noon_et(m["d"]))
            orow = {**{c: o.get(c, "") for c in ORIGIN_COLUMNS}, "truncated_for_t": o.get("truncated_for_t", 0)}
            u = _label_unit(orow, "ok", {"S": S, "q": a["q"], "anchor_status": a["status"], "expiry_dist_s": a.get("expiry_dist_s", math.nan)})
            q = a["q"]
            if math.isfinite(q) and u.get("label") == "available":
                rate = fee_rate(_f(m.get("fee_rate")))
                bk = books.get(o["market_id"], {})
                u["d2"] = d2_trade(q, bk, rate)
                u["d2_cost"] = d2_trade(q, bk, rate, cost_add=COST_ROBUST) if u["d2"] else None
            units.append(u)
    return units, statuses


def rep_d_doc(units: list[dict], statuses: dict[str, str], origin_days: list[str], y_of: Callable[[dict], float | None], k: int) -> dict:
    """D1-rep (slope; date and asset-date ways, every leave-one-week-out estimate keeps the sign) and D2 (net > 0) on post-freeze dates; > 20% of
    origins unavailable -> not testable with the dominant label."""
    avail = stage2_availability(statuses, origin_days)
    out: dict[str, Any] = {"availability": avail, "stage2_k": k, "alpha_each_early": c10.STAGE2_ALPHA / k if k else None,
                           "labels": {"D1_rep": "out-of-time replication on post-freeze resolution dates (L2)", "D2": "prospective economic check at recorded asks (L2)"}}
    if not avail["testable"]:
        for tid in ("D1_rep", "D2"):
            out[tid] = {"testable": False, "p": 1.0, "advance": False, "verdict": avail["label"]}
        return out
    av = [u for u in units if u.get("label") == "available"]
    ys = [y_of(u) for u in av]
    us = [u for u, y in zip(av, ys, strict=True) if y is not None]
    if len(us) >= 3:
        Y = np.array([y_of(u) for u in us])
        y = Y - np.array([u["p"] for u in us])
        x = np.array([u["q"] - u["p_reg"] for u in us])
        r = slope_test(y, x, us)
        thr = c10.STAGE2_ALPHA / k if k else 0.0
        out["D1_rep"] = {**r, "advance": bool(r["testable"] and r["p"] <= thr and r["beta"] > 0), "verdict": "replicated" if (r["testable"] and r["p"] <= thr and r["beta"] > 0) else "not replicated"}
    else:
        out["D1_rep"] = {"testable": False, "p": 1.0, "advance": False, "verdict": "not testable"}
    d2 = d2_stat(units, y_of)
    thr = c10.STAGE2_ALPHA / k if k else 0.0
    d2["advance"] = bool(d2.get("testable") and d2["p"] <= thr and (d2.get("mean_cents") or 0) > 0 and d2.get("pass_floor") and d2.get("cost_robustness_holds"))
    d2["verdict"] = "pass" if d2["advance"] else "fail / not detected"
    out["D2"] = d2
    return out


# =====================================================================================================================================
# Smoke (q0200 D part)
# =====================================================================================================================================

SMOKE_VERSION = "cb10-smoke-v1"
SMOKE_DERIBIT_HOURS = ("2026-10-02T10:00:00Z", "2026-10-03T16:00:00Z")
SMOKE_LADDER_DATES = ("2026-10-06", "2026-10-13")
SMOKE_SEED = "arepo-cb10-smoke"
SMOKE_TX_FIXTURE = [{"timestamp": 100, "outcomeIndex": 0, "price": 0.40, "size": 10, "transactionHash": "0xa"},
                    {"timestamp": 100, "outcomeIndex": 1, "price": 0.58, "size": 10, "transactionHash": "0xa"},
                    {"timestamp": 160, "outcomeIndex": 0, "price": 0.45, "size": 5, "transactionHash": "0xb"}]


def smoke_deribit(lim: hb.Limiter, hours: tuple[str, ...] = SMOKE_DERIBIT_HOURS) -> dict:
    """Per hour and currency: two repeat history walks of ``[h, h + 1 h)``; same trade count and id set; ``iv`` and ``index_price`` present on >= 99%;
    >= 99% of rows with 1 <= iv <= 400 (percent) and index > 0; counts of block / combo / liquidation rows. Counts only."""
    per = {}
    for h in hours:
        s = int(cm.ep(h) * 1000)
        for cur in ASSETS:
            walks = [deribit_trades(lim, cur, s, s + 3_600_000 - 1)[0] for _ in range(2)]
            r = walks[0]
            n = len(r)
            pres = sum(1 for x in r if math.isfinite(x["iv"]) and math.isfinite(x["index_price"]))
            rng = sum(1 for x in r if range_ok(x))
            per[f"{h}|{cur}"] = {"n_first": n, "n_second": len(walks[1]), "same": n == len(walks[1]) and {x["trade_id"] for x in r} == {x["trade_id"] for x in walks[1]},
                                 "present_share": pres / n if n else 0.0, "range_share": rng / n if n else 0.0,
                                 "n_block": sum(1 for x in r if x["flags"] & FLAG_BLOCK), "n_combo": sum(1 for x in r if x["flags"] & FLAG_COMBO),
                                 "n_liq": sum(1 for x in r if x["flags"] & FLAG_LIQ), "n_instrument_unparsed": sum(1 for x in r if parse_instrument(x["instrument"]) is None)}
    ok = all(v["same"] and v["n_first"] > 0 and v["present_share"] >= IV_RANGE_SHARE and v["range_share"] >= IV_RANGE_SHARE for v in per.values())
    return {"per": per, "pass": ok}


def smoke_ladders(lim: hb.Limiter, dates: tuple[str, ...] = SMOKE_LADDER_DATES) -> dict:
    """Per out-of-window date: the frame walker finds 11 strikes per asset with every flag present and the strike regex parsing every question; the
    whitelist parser keeps only whitelisted keys on two raw closed markets. Returns counts and two condition ids for the Data API check."""
    per, cids, wl_ok = {}, [], True
    for d in dates:
        rows, _outc, reasons, wl = frame_day(lim, d)
        by = {a: sum(1 for r in rows if r["asset"] == a) for a in ASSETS}
        per[d] = {"by_asset": by, "reasons": reasons, "ok": all(by[a] == 11 for a in ASSETS)}
        for w in wl[:1]:
            try:
                c10.assert_whitelisted(w)
            except Refused:
                wl_ok = False
        cids += [r["condition_id"] + "|" + str(r["yes_idx"]) for r in rows]
    pick = sorted(cids, key=lambda c: c10.rank(SMOKE_SEED, c))[:2]
    return {"per": per, "pass": all(v["ok"] for v in per.values()), "whitelist_pass": bool(wl_ok and cids), "data_api_cids": pick}


def smoke_data_api(lim: hb.Limiter, cids: list[str]) -> dict:
    out = {}
    for c in cids:
        cid, yi = c.split("|")
        prints, info = fetch_market_prints(lim, cid)
        tx = aggregate_transactions(prints, int(yi))
        out[cid[:10]] = {"n_prints": info["n_prints"], "n_tx": len(tx), "truncated": info["truncated"], "pages": info["pages"]}
    return {"per": out, "pass": bool(out) and all(not v["truncated"] and v["n_prints"] > 0 for v in out.values())}


def smoke_tx_fixture() -> dict:
    tx = aggregate_transactions(SMOKE_TX_FIXTURE, 0)
    ok = len(tx) == 2 and abs(tx[0][1] - 0.41) < 1e-9 and abs(tx[0][2] - 20) < 1e-9
    return {"n_tx": len(tx), "pass": ok}


def smoke_live_flags(lim: hb.Limiter, now: float) -> dict:
    """Rule-text flags on the two nearest live ladder dates (d >= today + 3 in ET, so both are out of every window): 11 strikes per asset pass the
    frozen rule (regex + every flag). Booleans and counts only."""
    from . import cb4_data as c4  # noqa: PLC0415

    today = datetime.fromtimestamp(now, c10.ET).date().isoformat()
    per = {}
    for d in (c10.day_add(today, 3), c10.day_add(today, 4)):
        a, b = gamma_end_window(d)
        rows, capped, failed = c4._paged_strict(lim, {"closed": "false", "end_date_min": a, "end_date_max": b, "order": "id", "ascending": "true"}, hb.GAMMA_OFFSET_CAP)
        if failed or capped:
            raise cm.ApiError(f"live flags {d}: {'failed' if failed else 'capped'}")
        why: dict[str, int] = {}
        ok_by = dict.fromkeys(ASSETS, 0)
        for m in rows:
            r, reason, _ = parse_ladder_market(m, d) if isinstance(m, dict) else (None, "bad", None)
            if re.match(QUESTION_RE, str((m or {}).get("question") or "")):
                why[reason] = why.get(reason, 0) + 1
            if r is not None:
                ok_by[r["asset"]] += 1
        per[d] = {"ok_by_asset": ok_by, "reasons_on_ladder_questions": why, "ok": all(v == 11 for v in ok_by.values())}
    return {"per": per, "pass": all(v["ok"] for v in per.values())}


def smoke_failures(path: Path, need: tuple[str, ...]) -> list[str]:
    """Unmet smoke criteria (empty = all met). A missing or foreign smoke file is a refusal (the job was committed before q0200 ran)."""
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found (q0200 first)")
    doc = json.loads(p.read_text())
    if doc.get("smoke_version") != SMOKE_VERSION:
        raise Refused(f"smoke version {doc.get('smoke_version')} != {SMOKE_VERSION}")
    return [k for k in need if not (doc.get("criteria") or {}).get(k)]


def smoke_ok(path: Path, need: tuple[str, ...]) -> dict:
    p = Path(path)
    if not p.exists():
        raise Refused(f"smoke result {p} not found (q0200 first)")
    doc = json.loads(p.read_text())
    if doc.get("smoke_version") != SMOKE_VERSION:
        raise Refused(f"smoke version {doc.get('smoke_version')} != {SMOKE_VERSION}")
    bad = [k for k in need if not (doc.get("criteria") or {}).get(k)]
    if bad:
        raise Refused(f"smoke criteria not met: {bad} (the dependent family is not testable (source), counted)")
    return doc


# =====================================================================================================================================
# Rules
# =====================================================================================================================================


def declared() -> dict:
    return {
        "family": "CB10-D (CH89), CREATIVE_BATCH_10.md CB10-D",
        "population": {"series_slugs": SERIES_SLUGS, "question_re": QUESTION_RE, "flags_common": FLAG_RES_COMMON, "flags_pair": PAIR_RES, "flag_source": FLAG_SOURCE,
                       "window": list(D_WINDOW), "walk": "one-day endDate windows [T - 1 min, T + 1 min] at T = d 12:00 America/New_York, closed=true, paged (capped -> retry; never by slug)",
                       "outcomes": list(OUTCOME_LABELS), "neg_risk": "excluded", "listed": "startDate <= (d - 5) 12:00 ET",
                       "exclusion": "market id, event id, negRiskMarketID; the SERIES-DATE key (an event drops if any excluded market of the same series resolves within +-1 day; "
                                    "excluded ids of the ladder series are looked up for their endDate at q0202, parse guard id/endDate/series only; > 2% missing -> disjointness unverified); "
                                    "the full series-key rule's drops reported beside it; > 30% events dropped -> label 'population thinned by exclusions'"},
        "clock": {"origins": "t = 12:00 ET on d - 5 and d - 2", "resolution": "T = d 12:00 ET", "et_zone": "America/New_York (DST from zoneinfo)"},
        "prices": {"aggregation": "prints aggregated by transactionHash at fetch: time = latest print time of the hash, YES-terms VWAP (outcome 1 - yes_idx -> 1 - price), total size; hash discarded; a print without a hash is its own transaction (counted)",
                   "data_api": {"limit": DATA_LIMIT, "pages": DATA_PAGES, "takerOnly": TAKER_ONLY, "truncated": "the last allowed page is full or the deep offset is refused"},
                   "eligibility": f"last transaction before t of any age inside the covered span with YES price in {list(PRICE_BAND)}; none before t -> never traded by t (or undeterminable if truncated)",
                   "p": f"last transaction in [t - {FRESH_S} s, t)", "p_reg": f"last transaction in [t - {REG_LOOKBACK_S} s, t_p - {REG_GAP_S} s)",
                   "p_alt": f"last transaction in [t - {REG_LOOKBACK_S} s, t_reg - {REG_GAP_S} s)", "latency": f"p10 in [t - {LATENCY_FRESH_S} s, t) with its own p_reg rule",
                   "labels_in_order": [LABEL_TRUNC + ": t - 180 min before the oldest reachable print of a truncated market", LABEL_DERIBIT + ": fetch failed after retries, origin range check failed, or no usable expiry within 3 days / no spot",
                                       LABEL_INACTIVE + ": no p or no p_reg"]},
        "anchor": {"history": DERIBIT_HISTORY, "fetch_window_s": DERIBIT_FETCH_S, "smile_window_s": ANCHOR_WINDOW_S, "store_expiry_max_s": STORE_EXPIRY_MAX_S,
                   "exclude_flags": "block_trade_id, combo_id / combo_trade_id, liquidation (variant with them reported)", "iv_units": "percent; iv_dec = iv / 100",
                   "range_check": {"iv": list(IV_RANGE), "index_price": "> 0", "origin_share": IV_RANGE_SHARE},
                   "moneyness": "m = ln(K_opt / index_price of that trade); strike m_K = ln(K / S)", "spot": "S = index_price of the last remaining trade before t",
                   "tau": "ACT/365 from t; expiries at 08:00Z", "smile": {"m_max": SMILE_M_MAX, "min_trades": SMILE_MIN, "min_each_side": SMILE_SIDE_MIN, "weights": "amount"},
                   "atm_fallback": {"m_max": ATM_M_MAX, "min_trades": ATM_MIN, "b": 0}, "expiry_max_s": EXPIRY_MAX_S,
                   "interpolation": "total variance and b linear in time between the nearest usable e1 <= T < e2 (both after t, within 3 days); one side -> flat sigma and b of that expiry; sigma <= 0 -> unavailable",
                   "digital": "q = Phi(d2) - (S/K) phi(d1) sqrt(tau) b, zero rates, forward = S", "clip": list(Q_CLIP),
                   "q_rv": f"flat digital with the 7-day realised vol of the perpetual's consecutive hourly log returns (closes) over [t - 7 d, t), sqrt(8760), >= {RV_MIN_RETURNS} returns",
                   "q_prime": "the same fits with S = index_price of the last Deribit trade at or before t_reg",
                   "variants_reported": {"flat_smile": "sigma_e = a_e, b = 0", "with_flagged": "block / combo / liquidation rows included", "dvol_flat": "DVOL close of the last complete hour / 100, b = 0",
                                         "haircut": f"sigma x (1 - h), h = 1 - median(RV_7d / ATM IV_7d) over 12:00 ET points of {list(HAIRCUT_WINDOW)} (Deribit only; both assets pooled)"},
                   "chart": {"chunk_days": CHART_CHUNK_DAYS, "instruments": PERP}, "rps": DERIBIT_RPS, "page_count": DERIBIT_COUNT, "max_pages": DERIBIT_MAX_PAGES},
        "guarded": {"files": list(GUARDED_FILES), "jobs": list(GUARDED_ALLOWED_JOBS),
                    "settlement": "index_price of the last option trade at or before T (from the T-day fetch [T - 180 min, T])",
                    "disclosed": "trades.csv.gz for origin time noon(d) carries index prices up to T - 1 ms of ladder d; no census path joins a ladder's strikes with its own T"},
        "d1": {"statistic": "OLS slope of Y - p on q - p_reg with intercept, unweighted; tested as the clustered mean of influence pseudo-values", "floor": D1_FLOOR,
               "ways": ["date", "asset_date", "iso_week (small-G)"],
               "placebos": {"signflip": "one coin per ISO week, and one per date; 200 draws each; both must hold", "independent_price": "p_alt - p_reg in place of q - p_reg: holds iff its p >= 0.01 and min(beta - beta_alt, beta_subset - beta_alt) >= 0.30"},
               "spot_staleness": "q' slope keeps the sign and >= half", "attribution": "joint OLS with q_RV - p_reg; credit iff joint coef >= half the solo slope (same units) and cor <= 0.9",
               "robustness": {"ii": "top-5 drops per way (date, asset_date, week): p < 0.01 and beta >= 0.30", "iii": f"WLS by size at p capped at {SIZE_WEIGHT_CAP}: same sign",
                              "iv": f"sign in each third {THIRDS} and each asset", "v": "unavailable units excluded and counted", "vi": "p from [t - 10 min, t) with its own p_reg: sign and >= half"}},
        "d2": {"edge": D2_EDGE, "min_size": D2_MIN_SIZE, "fee": "r a (1 - a), r = max(feeSchedule.rate at frame time, 0.07)", "fee_floor": FEE_RATE_FLOOR, "floor": D2_FLOOR,
               "cost_robustness": COST_ROBUST, "unit": "traded market-origin (both edges -> the larger)"},
        "source_check": {"min_abs_logm": SOURCE_MIN_ABS_LOGM, "max_disagree": SOURCE_DISAGREE_MAX},
        "census": {"gate_GD": GD, "available_min": AVAILABLE_MIN, "audit_pass": AUDIT_PASS, "gdp": GDP, "cor_attrib_max": COR_ATTRIB_MAX,
                   "audit_denominator": "eligible units + units whose eligibility is undeterminable because of truncation (counted as source-unavailable)"},
        "stage2": {"dates": STAGE2_DATES, "collect_max_days": STAGE2_COLLECT_MAX_DAYS, "unavailable_max": STAGE2_UNAVAILABLE_MAX, "receipt_window_s": STAGE2_RECEIPT_S,
                   "cron": "0 16 * * * and 0 17 * * * UTC; acts iff 0 <= now - 12:00 ET <= 600 s; |now - t| >= 3000 s -> the other line (exit 0); otherwise unavailable (scheduling)",
                   "labels": ["unavailable (scheduling)", "unavailable (host disk)", "unavailable (source)"], "outcome_sweep_grace_days": STAGE2_OUTCOME_GRACE_DAYS,
                   "start": "first d whose (d - 5) 12:00 ET >= max(freeze commit, D1 result commit) + 1 day"},
        "smoke": {"version": SMOKE_VERSION, "deribit_hours": list(SMOKE_DERIBIT_HOURS), "ladder_dates": list(SMOKE_LADDER_DATES), "seed": SMOKE_SEED,
                  "criteria": ["deribit", "ladder_frame", "data_api_paging", "tx_aggregation", "whitelist", "live_flags"]},
    }


def rule_funcs() -> tuple:
    from . import cb4_data as c4  # noqa: PLC0415

    return (declared, window_dates, origins_of, gamma_end_window, flag_res, parse_ladder_market, frame_day, series_date_lookup, apply_exclusions, aggregate_transactions,
            fetch_market_prints, _last_in, origin_row, parse_trade, deribit_trades, range_ok, parse_instrument, origin_trade_rows, chart_bars, dvol_rows, digital,
            usable_trades, smile_fit, expiry_fits, anchor_q, last_index, spot_at_origin, spot_at_origin_all, rv_sigma, dvol_sigma, haircut_h, open_guarded, outcome_y,
            dlad_frame, deribit_days, deribit_fetch, unit_features, build_units, _label_unit, gdp_mde, census_d, source_check, _ways, slope_test, d1_stat, v_of, c9_top_k,
            d1_reported, t10_d2_start, stage2_dates, origin_due, stage2_targets, clob_book_state, dlad_live_tick, outcome_sweep, stage2_availability, fee_rate, taker_fee,
            d2_trade, d2_stat, live_frame_markets, haircut_from_deribit, live_units, rep_d_doc, smoke_deribit, smoke_ladders, smoke_data_api, smoke_tx_fixture,
            smoke_live_flags, smoke_failures, smoke_ok, c4._paged_strict)
